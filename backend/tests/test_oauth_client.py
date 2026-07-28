"""Tests for the injectable OAuth provider clients (Google and GitHub).

All HTTP is mocked with :class:`httpx.MockTransport` - there are no real network
calls. We assert authorize-URL contents for both providers, token-exchange
parsing, Google user-info normalization (incl. ``email_verified``), GitHub
primary-verified-email resolution, and the (un)configured registry behavior.
"""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.core.config import settings
from app.domains.auth import oauth
from app.domains.auth.oauth import (
    GITHUB,
    GOOGLE,
    OAuthClient,
    OAuthError,
    OAuthUnconfiguredError,
    OAuthUserInfo,
    get_oauth_client,
    is_configured,
)


@pytest.fixture
def oauth_env(monkeypatch):
    """Configure both providers with dummy credentials for the test."""
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "google-id", raising=False)
    monkeypatch.setattr(
        settings, "GOOGLE_OAUTH_CLIENT_SECRET", "google-secret", raising=False
    )
    monkeypatch.setattr(settings, "GITHUB_OAUTH_CLIENT_ID", "github-id", raising=False)
    monkeypatch.setattr(
        settings, "GITHUB_OAUTH_CLIENT_SECRET", "github-secret", raising=False
    )


def _client(provider: str, handler) -> OAuthClient:
    transport = httpx.MockTransport(handler)
    spec = oauth.get_provider_spec(provider)
    return OAuthClient(spec, http_client=httpx.Client(transport=transport))


# -- authorize URL ---------------------------------------------------------


def test_google_authorize_url_contents(oauth_env):
    def handler(request):  # pragma: no cover - not called
        raise AssertionError("build_authorize_url makes no HTTP call")

    client = _client(GOOGLE, handler)
    url = client.build_authorize_url("https://app.example.com/cb", "state-123")

    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert parsed.path == "/o/oauth2/v2/auth"
    assert params["client_id"] == "google-id"
    assert params["redirect_uri"] == "https://app.example.com/cb"
    assert params["response_type"] == "code"
    assert params["scope"] == "openid email profile"
    assert params["state"] == "state-123"


def test_github_authorize_url_contents(oauth_env):
    client = _client(GITHUB, lambda r: httpx.Response(200))
    url = client.build_authorize_url("https://app.example.com/cb", "xyz")

    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    assert params["client_id"] == "github-id"
    assert params["redirect_uri"] == "https://app.example.com/cb"
    assert params["response_type"] == "code"
    assert params["scope"] == "read:user user:email"
    assert params["state"] == "xyz"


# -- token exchange --------------------------------------------------------


def test_google_exchange_code_posts_and_parses(oauth_env):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["accept"] = request.headers.get("Accept")
        captured["body"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(200, json={"access_token": "google-token", "scope": "..."})

    client = _client(GOOGLE, handler)
    token = client.exchange_code("the-code", "https://app.example.com/cb")

    assert token == "google-token"
    assert captured["method"] == "POST"
    assert captured["url"] == "https://oauth2.googleapis.com/token"
    assert captured["accept"] == "application/json"
    assert captured["body"] == {
        "client_id": "google-id",
        "client_secret": "google-secret",
        "code": "the-code",
        "redirect_uri": "https://app.example.com/cb",
        "grant_type": "authorization_code",
    }


def test_github_exchange_code_sends_accept_json(oauth_env):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["accept"] = request.headers.get("Accept")
        return httpx.Response(200, json={"access_token": "gh-token"})

    client = _client(GITHUB, handler)
    token = client.exchange_code("code", "https://app.example.com/cb")

    assert token == "gh-token"
    assert captured["url"] == "https://github.com/login/oauth/access_token"
    assert captured["accept"] == "application/json"


def test_exchange_code_without_token_raises(oauth_env):
    client = _client(GOOGLE, lambda r: httpx.Response(200, json={"error": "bad"}))
    with pytest.raises(OAuthError, match="access_token"):
        client.exchange_code("code", "https://app.example.com/cb")


# -- user info -------------------------------------------------------------


def test_google_fetch_user_info_normalizes(oauth_env):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={
                "sub": "1234567890",
                "email": "alice@example.com",
                "email_verified": True,
                "name": "Alice",
            },
        )

    client = _client(GOOGLE, handler)
    info = client.fetch_user_info("access-abc")

    assert captured["url"] == "https://openidconnect.googleapis.com/v1/userinfo"
    assert captured["auth"] == "Bearer access-abc"
    assert info == OAuthUserInfo(
        provider_account_id="1234567890",
        email="alice@example.com",
        email_verified=True,
        name="Alice",
    )


def test_google_email_verified_false_is_respected(oauth_env):
    client = _client(
        GOOGLE,
        lambda r: httpx.Response(
            200,
            json={"sub": "9", "email": "bob@example.com", "email_verified": False,
                  "name": "Bob"},
        ),
    )
    info = client.fetch_user_info("tok")
    assert info.email_verified is False


def test_github_fetch_user_info_picks_primary_verified_email(oauth_env):
    def handler(request):
        path = urlparse(str(request.url)).path
        if path == "/user":
            return httpx.Response(
                200, json={"id": 42, "login": "octocat", "name": "The Octocat",
                           "email": None}
            )
        if path == "/user/emails":
            return httpx.Response(
                200,
                json=[
                    {"email": "secondary@example.com", "primary": False,
                     "verified": True},
                    {"email": "octocat@example.com", "primary": True,
                     "verified": True},
                    {"email": "old@example.com", "primary": False,
                     "verified": False},
                ],
            )
        raise AssertionError(f"unexpected path {path}")

    client = _client(GITHUB, handler)
    info = client.fetch_user_info("gh-token")

    assert info == OAuthUserInfo(
        provider_account_id="42",
        email="octocat@example.com",
        email_verified=True,
        name="The Octocat",
    )


def test_github_unverified_primary_email_sets_flag_false(oauth_env):
    def handler(request):
        path = urlparse(str(request.url)).path
        if path == "/user":
            return httpx.Response(200, json={"id": 7, "login": "ghost", "name": None})
        return httpx.Response(
            200,
            json=[{"email": "ghost@example.com", "primary": True, "verified": False}],
        )

    client = _client(GITHUB, handler)
    info = client.fetch_user_info("tok")

    assert info.provider_account_id == "7"
    assert info.email == "ghost@example.com"
    assert info.email_verified is False
    assert info.name == "ghost"  # falls back to login when name is null


# -- registry / configuration ---------------------------------------------


def test_is_configured_reflects_settings(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "", raising=False)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "", raising=False)
    assert is_configured(GOOGLE) is False

    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "id", raising=False)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "secret", raising=False)
    assert is_configured(GOOGLE) is True


def test_is_configured_false_for_unknown_provider():
    assert is_configured("gitlab") is False


def test_get_oauth_client_unconfigured_raises(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_OAUTH_CLIENT_ID", "", raising=False)
    monkeypatch.setattr(settings, "GITHUB_OAUTH_CLIENT_SECRET", "", raising=False)
    with pytest.raises(OAuthUnconfiguredError, match="not configured"):
        get_oauth_client(GITHUB)


def test_get_oauth_client_unknown_provider_raises():
    with pytest.raises(OAuthError, match="Unknown OAuth provider"):
        get_oauth_client("facebook")


def test_get_oauth_client_returns_client_when_configured(oauth_env):
    client = get_oauth_client(GOOGLE)
    assert isinstance(client, OAuthClient)
    assert client.spec.provider == GOOGLE
    client.close()


# -- lifecycle -------------------------------------------------------------


def test_context_manager_closes_owned_client(oauth_env):
    with get_oauth_client(GOOGLE) as client:
        http_client = client._client
        assert not http_client.is_closed
    assert http_client.is_closed
    assert client._http_client is None


def test_close_does_not_close_injected_client(oauth_env):
    injected = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    client = OAuthClient(oauth.get_provider_spec(GOOGLE), http_client=injected)
    client.close()
    assert not injected.is_closed
    injected.close()
