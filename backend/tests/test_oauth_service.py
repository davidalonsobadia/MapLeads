"""Tests for the OAuth link-or-create service (``AuthService``).

Covers ``login_or_create_oauth_user`` (the heart of social login) and the
OAuth-only hardening of ``login_user``. These exercise the service directly
against a SQLite ``db_session``; no provider HTTP is involved because the
method takes an already-normalized :class:`OAuthUserInfo`.
"""

import pytest
from fastapi import HTTPException

from app.domains.auth import utils
from app.domains.auth.models import OAuthAccount, User
from app.domains.auth.oauth import GOOGLE, OAuthUserInfo
from app.domains.auth.schemas import UserLogin
from app.domains.auth.service import AuthService
from app.domains.billing import plans
from app.domains.billing.models import Subscription


def _info(**overrides) -> OAuthUserInfo:
    """A verified Google identity with sensible defaults for tests."""
    base = {
        "provider_account_id": "google-sub-123",
        "email": "oauth@example.com",
        "email_verified": True,
        "name": "OAuth User",
    }
    base.update(overrides)
    return OAuthUserInfo(**base)


def test_creates_user_and_trial_on_first_login(db_session):
    service = AuthService(db_session)

    user = service.login_or_create_oauth_user(GOOGLE, _info())

    assert user.id is not None
    assert user.email == "oauth@example.com"
    assert user.name == "OAuth User"
    # OAuth-only user: no local password, and the provider verified the email.
    assert user.hashed_password is None
    assert user.is_verified is True

    assert db_session.query(User).count() == 1

    accounts = db_session.query(OAuthAccount).all()
    assert len(accounts) == 1
    assert accounts[0].provider == GOOGLE
    assert accounts[0].provider_account_id == "google-sub-123"
    assert accounts[0].user_id == user.id

    subs = db_session.query(Subscription).filter(
        Subscription.user_id == user.id
    ).all()
    assert len(subs) == 1
    assert subs[0].plan == plans.PLAN_TRIAL
    assert subs[0].status == plans.STATUS_TRIALING


def test_links_existing_password_user_by_verified_email(db_session):
    existing = User(
        name="Password User",
        email="oauth@example.com",
        hashed_password=utils.get_password_hash("secret"),
        is_verified=True,
    )
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    service = AuthService(db_session)
    user = service.login_or_create_oauth_user(GOOGLE, _info())

    # Same user returned, no duplicate created.
    assert user.id == existing.id
    assert db_session.query(User).count() == 1

    accounts = db_session.query(OAuthAccount).all()
    assert len(accounts) == 1
    assert accounts[0].user_id == existing.id

    # Linking must not provision a second (trial) subscription for a user who
    # already had an account without one.
    assert db_session.query(Subscription).count() == 0


def test_existing_link_logs_in_without_duplicates(db_session):
    service = AuthService(db_session)

    first = service.login_or_create_oauth_user(GOOGLE, _info())
    users_after_first = db_session.query(User).count()
    accounts_after_first = db_session.query(OAuthAccount).count()
    subs_after_first = db_session.query(Subscription).count()

    second = service.login_or_create_oauth_user(GOOGLE, _info())

    assert second.id == first.id
    assert db_session.query(User).count() == users_after_first
    assert db_session.query(OAuthAccount).count() == accounts_after_first
    assert db_session.query(Subscription).count() == subs_after_first


def test_unverified_email_rejected(db_session):
    service = AuthService(db_session)

    with pytest.raises(HTTPException) as exc:
        service.login_or_create_oauth_user(
            GOOGLE, _info(email_verified=False)
        )

    assert exc.value.status_code == 400
    # Nothing written.
    assert db_session.query(User).count() == 0
    assert db_session.query(OAuthAccount).count() == 0
    assert db_session.query(Subscription).count() == 0


def test_missing_email_rejected(db_session):
    service = AuthService(db_session)

    with pytest.raises(HTTPException) as exc:
        service.login_or_create_oauth_user(
            GOOGLE, _info(email=None, email_verified=True)
        )

    assert exc.value.status_code == 400
    assert db_session.query(User).count() == 0
    assert db_session.query(OAuthAccount).count() == 0
    assert db_session.query(Subscription).count() == 0


def test_login_user_rejects_oauth_only_account(db_session):
    user = User(
        name="OAuth Only",
        email="oauth-only@example.com",
        hashed_password=None,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    service = AuthService(db_session)

    with pytest.raises(HTTPException) as exc:
        service.login_user(
            UserLogin(email="oauth-only@example.com", password="whatever")
        )

    # 401 (not 500): an OAuth-only account has no password to verify.
    assert exc.value.status_code == 401
