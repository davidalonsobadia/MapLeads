"""Injectable OAuth provider clients for social login (Google and GitHub).

This module exposes :class:`OAuthClient`, a small, testable HTTP client that
speaks the OAuth 2.0 authorization-code flow for the two providers MapLeads
supports. It mirrors how ``PlacesClient`` is structured for the search domain:
a plain library with an optionally injected :class:`httpx.Client`, so tests can
stub transport and later tasks can fake the provider instead of calling
Google/GitHub.

No FastAPI routes, dependency wiring, or persistence live here - that is
intentionally out of scope for this task (see epic #88). The redirect URI is
derived from ``FRONTEND_URL`` by callers and passed into the methods below; no
extra setting is needed for it.

A client is parameterized by a :class:`ProviderSpec` (endpoints, scope, and the
settings keys holding its credentials). Use :func:`get_oauth_client` to obtain a
configured client from the registry keyed by ``"google"`` / ``"github"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app import logger
from app.core.config import settings

# Provider registry keys.
GOOGLE = "google"
GITHUB = "github"

# Default request timeout in seconds.
DEFAULT_TIMEOUT = 30.0


class OAuthError(RuntimeError):
    """Raised when an OAuth provider request fails or returns unexpected data."""


class OAuthUnconfiguredError(OAuthError):
    """Raised when a provider is requested but its client id/secret is empty."""


@dataclass(frozen=True)
class OAuthUserInfo:
    """Normalized user profile returned by every provider.

    ``provider_account_id`` is the provider's stable, immutable account id (the
    Google ``sub`` claim, the GitHub numeric ``id`` as a string). ``email`` may be
    ``None`` when the provider does not expose one.
    """

    provider_account_id: str
    email: str | None
    email_verified: bool
    name: str


@dataclass(frozen=True)
class ProviderSpec:
    """Static description of an OAuth provider.

    ``client_id_key`` / ``client_secret_key`` name the :class:`Settings` fields
    holding the credentials; they are read lazily so an unconfigured provider can
    still be described in the registry. ``emails_url`` is provider-specific
    (GitHub exposes verified emails on a separate endpoint).
    """

    provider: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str
    client_id_key: str
    client_secret_key: str
    emails_url: str | None = None


# Endpoints, scopes, and credential keys per provider. See the epic for the
# provider-specifics these encode.
_PROVIDERS: dict[str, ProviderSpec] = {
    GOOGLE: ProviderSpec(
        provider=GOOGLE,
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scope="openid email profile",
        client_id_key="GOOGLE_OAUTH_CLIENT_ID",
        client_secret_key="GOOGLE_OAUTH_CLIENT_SECRET",
    ),
    GITHUB: ProviderSpec(
        provider=GITHUB,
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        userinfo_url="https://api.github.com/user",
        emails_url="https://api.github.com/user/emails",
        scope="read:user user:email",
        client_id_key="GITHUB_OAUTH_CLIENT_ID",
        client_secret_key="GITHUB_OAUTH_CLIENT_SECRET",
    ),
}


def is_configured(provider: str) -> bool:
    """Return ``True`` when ``provider`` is known and has both credentials set."""
    spec = _PROVIDERS.get(provider)
    if spec is None:
        return False
    return bool(
        getattr(settings, spec.client_id_key)
        and getattr(settings, spec.client_secret_key)
    )


def get_provider_spec(provider: str) -> ProviderSpec:
    """Return the :class:`ProviderSpec` for ``provider`` or raise a clear error."""
    spec = _PROVIDERS.get(provider)
    if spec is None:
        supported = ", ".join(sorted(_PROVIDERS))
        raise OAuthError(
            f"Unknown OAuth provider '{provider}'. Supported providers: {supported}."
        )
    return spec


def get_oauth_client(
    provider: str,
    http_client: httpx.Client | None = None,
) -> OAuthClient:
    """Return an :class:`OAuthClient` for ``provider``.

    Raises :class:`OAuthError` for an unknown provider key and
    :class:`OAuthUnconfiguredError` when the provider's credentials are empty.
    """
    spec = get_provider_spec(provider)
    if not is_configured(provider):
        raise OAuthUnconfiguredError(
            f"OAuth provider '{provider}' is not configured; set "
            f"{spec.client_id_key} and {spec.client_secret_key} in the environment."
        )
    return OAuthClient(spec, http_client=http_client)


class OAuthClient:
    """OAuth 2.0 authorization-code client for a single provider.

    Parameters
    ----------
    spec:
        The provider description (endpoints, scope, credential keys).
    http_client:
        Optional pre-built :class:`httpx.Client` (useful for tests). When not
        supplied, a client is created lazily and owned by this instance.
    """

    def __init__(
        self,
        spec: ProviderSpec,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.spec = spec
        self._http_client = http_client
        self._owns_client = http_client is None

    # -- credentials --------------------------------------------------------

    @property
    def client_id(self) -> str:
        return getattr(settings, self.spec.client_id_key)

    @property
    def client_secret(self) -> str:
        return getattr(settings, self.spec.client_secret_key)

    # -- public API ---------------------------------------------------------

    def build_authorize_url(self, redirect_uri: str, state: str) -> str:
        """Return the provider authorize URL the browser should be sent to."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.spec.scope,
            "state": state,
        }
        return f"{self.spec.authorize_url}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> str:
        """Exchange an authorization ``code`` for a provider access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        # GitHub only returns JSON when asked; Google always does. Sending the
        # header for both is harmless.
        payload = self._post_form(
            self.spec.token_url, data, headers={"Accept": "application/json"}
        )
        token = payload.get("access_token")
        if not token or not isinstance(token, str):
            raise OAuthError(
                f"{self.spec.provider} token response did not contain an access_token."
            )
        return token

    def fetch_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch and normalize the user's profile from the provider."""
        if self.spec.provider == GOOGLE:
            return self._fetch_google_user_info(access_token)
        if self.spec.provider == GITHUB:
            return self._fetch_github_user_info(access_token)
        # Unreachable via the registry, but keep the failure explicit.
        raise OAuthError(
            f"fetch_user_info is not implemented for provider '{self.spec.provider}'."
        )

    # -- provider-specific normalization ------------------------------------

    def _fetch_google_user_info(self, access_token: str) -> OAuthUserInfo:
        data = self._get_json(self.spec.userinfo_url, access_token)
        return OAuthUserInfo(
            provider_account_id=str(data.get("sub", "")),
            email=data.get("email"),
            email_verified=bool(data.get("email_verified", False)),
            name=data.get("name") or "",
        )

    def _fetch_github_user_info(self, access_token: str) -> OAuthUserInfo:
        user = self._get_json(
            self.spec.userinfo_url,
            access_token,
            accept="application/vnd.github+json",
        )
        primary = None
        if self.spec.emails_url:
            emails = self._get_json(
                self.spec.emails_url,
                access_token,
                accept="application/vnd.github+json",
            )
            primary = _select_github_primary_email(emails)

        if primary is not None:
            email = primary.get("email")
            email_verified = bool(primary.get("verified", False))
        else:
            # Fall back to the (possibly public) email on the user record.
            email = user.get("email")
            email_verified = False

        return OAuthUserInfo(
            provider_account_id=str(user.get("id", "")),
            email=email,
            email_verified=email_verified,
            name=user.get("name") or user.get("login") or "",
        )

    # -- HTTP internals -----------------------------------------------------

    def _post_form(
        self,
        url: str,
        data: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.post(url, data=data, headers=headers)
        except httpx.HTTPError as exc:  # network/transport failure
            logger.error("%s OAuth request failed: %s", self.spec.provider, exc)
            raise OAuthError(
                f"{self.spec.provider} OAuth request failed: {exc}"
            ) from exc
        return self._parse(response)

    def _get_json(
        self,
        url: str,
        access_token: str,
        accept: str = "application/json",
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": accept,
        }
        try:
            response = self._client.get(url, headers=headers)
        except httpx.HTTPError as exc:  # network/transport failure
            logger.error("%s OAuth request failed: %s", self.spec.provider, exc)
            raise OAuthError(
                f"{self.spec.provider} OAuth request failed: {exc}"
            ) from exc
        return self._parse(response)

    def _parse(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            detail = response.text or "unknown error"
            logger.error(
                "%s OAuth returned %s: %s",
                self.spec.provider,
                response.status_code,
                detail,
            )
            raise OAuthError(
                f"{self.spec.provider} OAuth error {response.status_code}: {detail}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise OAuthError(
                f"{self.spec.provider} OAuth returned a non-JSON response."
            ) from exc

    @property
    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=DEFAULT_TIMEOUT)
        return self._http_client

    def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> OAuthClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _select_github_primary_email(emails: Any) -> dict[str, Any] | None:
    """Pick the primary email entry from GitHub's ``/user/emails`` response.

    Prefers the entry flagged ``primary``; falls back to the first entry so a
    single-email account still resolves. Returns ``None`` for an empty list.
    """
    if not isinstance(emails, list):
        return None
    entries = [e for e in emails if isinstance(e, dict)]
    if not entries:
        return None
    for entry in entries:
        if entry.get("primary"):
            return entry
    return entries[0]
