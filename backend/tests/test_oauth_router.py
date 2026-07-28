"""Tests for the OAuth authorize/callback endpoints on the auth router.

A fake ``OAuthClient`` is injected via the ``get_oauth_client`` dependency
override (mirroring ``test_search.py``'s ``get_places_client`` pattern), so no
real Google/GitHub calls happen. The unknown/unconfigured cases deliberately do
**not** override the client, so the real injector runs and maps the library's
errors to 400/503.

Unlike the shared ``client`` fixture, this module's ``db_client`` does not force
a current user, so the OAuth-issued JWT can be exercised against ``/me``.
"""

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.domains.auth.models import OAuthAccount, User
from app.domains.auth.oauth import OAuthError, OAuthUserInfo
from app.domains.auth.router import get_oauth_client
from app.domains.billing import plans
from app.domains.billing.models import Subscription
from app.main import app

AUTH = "/api/v1/auth"


class FakeOAuthClient:
    """A stand-in OAuth client returning a canned identity.

    Records call arguments so tests can assert the server-derived redirect URI
    and state are forwarded to the client.
    """

    def __init__(self, info: OAuthUserInfo | None = None, exchange_error: bool = False):
        self._info = info
        self._exchange_error = exchange_error
        self.authorize_calls: list[tuple[str, str]] = []
        self.exchange_calls: list[tuple[str, str]] = []

    def build_authorize_url(self, redirect_uri: str, state: str) -> str:
        self.authorize_calls.append((redirect_uri, state))
        return f"https://provider.example/authorize?redirect_uri={redirect_uri}&state={state}"

    def exchange_code(self, code: str, redirect_uri: str) -> str:
        self.exchange_calls.append((code, redirect_uri))
        if self._exchange_error:
            raise OAuthError("exchange failed")
        return "fake-provider-token"

    def fetch_user_info(self, access_token: str) -> OAuthUserInfo:
        return self._info


@pytest.fixture
def db_client(db_session):
    """A TestClient wired to the in-memory DB, WITHOUT a forced current user.

    Only ``get_db`` is overridden (not ``get_verified_user``), so authenticated
    endpoints require a real Bearer token — letting us prove an OAuth-issued
    token is a valid session.
    """

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def use_oauth_client():
    """Install a fake OAuth client and yield a setter that returns the fake."""
    holder = {}

    def _set(fake: FakeOAuthClient) -> FakeOAuthClient:
        holder["client"] = fake
        return fake

    app.dependency_overrides[get_oauth_client] = lambda: holder["client"]
    yield _set
    app.dependency_overrides.pop(get_oauth_client, None)


def _info(provider_account_id="acc-1", email="new@example.com", name="New User"):
    return OAuthUserInfo(
        provider_account_id=provider_account_id,
        email=email,
        email_verified=True,
        name=name,
    )


@pytest.mark.parametrize("provider", ["google", "github"])
def test_authorize_returns_url_and_state(db_client, use_oauth_client, provider):
    fake = use_oauth_client(FakeOAuthClient())

    response = db_client.get(f"{AUTH}/oauth/{provider}/authorize")
    assert response.status_code == 200
    body = response.json()
    assert body["authorization_url"]
    assert body["state"]

    # The redirect URI is derived server-side and the state is forwarded verbatim.
    redirect_uri, state = fake.authorize_calls[0]
    assert redirect_uri.endswith(f"/api/auth/oauth/{provider}/callback")
    assert state == body["state"]


def test_authorize_unknown_provider_returns_400(db_client):
    # No client override -> the real injector runs and rejects the provider.
    assert db_client.get(f"{AUTH}/oauth/microsoft/authorize").status_code == 400


def test_authorize_unconfigured_provider_returns_503(db_client):
    # Credentials are empty in tests and the client is not overridden.
    assert db_client.get(f"{AUTH}/oauth/google/authorize").status_code == 503


def test_callback_unknown_provider_returns_400(db_client):
    response = db_client.post(
        f"{AUTH}/oauth/microsoft/callback", json={"code": "c", "state": None}
    )
    assert response.status_code == 400


def test_callback_new_user_creates_rows(db_client, use_oauth_client, db_session):
    use_oauth_client(FakeOAuthClient(info=_info("g-123", "new@example.com")))

    response = db_client.post(
        f"{AUTH}/oauth/google/callback", json={"code": "abc", "state": "s"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "new@example.com"

    # A verified, password-less user was created, linked, and given a trial.
    user = db_session.query(User).filter(User.email == "new@example.com").one()
    assert user.hashed_password is None
    assert user.is_verified is True

    account = (
        db_session.query(OAuthAccount)
        .filter(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_account_id == "g-123",
        )
        .one()
    )
    assert account.user_id == user.id

    subscription = (
        db_session.query(Subscription).filter(Subscription.user_id == user.id).one()
    )
    assert subscription.plan == plans.PLAN_TRIAL


def test_callback_existing_link_returns_same_user_without_new_rows(
    db_client, use_oauth_client, db_session
):
    user = User(
        name="Linked",
        email="linked@example.com",
        hashed_password=None,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.add(
        OAuthAccount(user_id=user.id, provider="github", provider_account_id="gh-9")
    )
    db_session.commit()

    users_before = db_session.query(User).count()
    accounts_before = db_session.query(OAuthAccount).count()

    use_oauth_client(FakeOAuthClient(info=_info("gh-9", "linked@example.com")))
    response = db_client.post(
        f"{AUTH}/oauth/github/callback", json={"code": "c", "state": None}
    )
    assert response.status_code == 200
    assert response.json()["user"]["id"] == user.id

    assert db_session.query(User).count() == users_before
    assert db_session.query(OAuthAccount).count() == accounts_before


def test_callback_exchange_failure_returns_502(db_client, use_oauth_client):
    use_oauth_client(FakeOAuthClient(exchange_error=True))
    response = db_client.post(
        f"{AUTH}/oauth/google/callback", json={"code": "bad", "state": None}
    )
    assert response.status_code == 502


def test_issued_token_authorizes_me(db_client, use_oauth_client):
    use_oauth_client(FakeOAuthClient(info=_info("g-777", "me@example.com", "Me")))
    token = (
        db_client.post(
            f"{AUTH}/oauth/google/callback", json={"code": "c", "state": None}
        )
        .json()["access_token"]
    )

    response = db_client.get(
        f"{AUTH}/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
