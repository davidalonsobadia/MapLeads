"""Signed, stateless token that marks an anonymous visitor's free search as used.

The anonymous "try a search" funnel gives each visitor exactly one free search.
Rather than tracking visitors server-side, we hand back a signed token the client
persists and replays; its presence (and validity) means "the free search is
already spent". The token is a JWT signed with ``settings.SECRET_KEY`` carrying a
distinct ``scope: "anon_search"`` claim so it is disjoint from the auth access
token and can never authenticate a user via ``get_current_user`` (which requires
``sub``). It is stateless by design: no DB row, no migration.
"""

from datetime import datetime, timedelta

from jose import JWTError, jwt

from app.core.config import settings

# Distinct scope so this token can never be mistaken for an auth access token.
ANON_SEARCH_SCOPE = "anon_search"


def issue_token() -> str:
    """Issue a signed anon-search token whose presence means the free search is spent."""
    expire = datetime.utcnow() + timedelta(days=settings.ANONYMOUS_SEARCH_TOKEN_TTL_DAYS)
    payload = {"scope": ANON_SEARCH_SCOPE, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(raw: str | None) -> bool:
    """Return True iff ``raw`` is a valid, unexpired anon-search token.

    Any problem — missing, malformed, expired, wrong signature or wrong scope —
    is treated as "not a valid token" (False). Never raises to the caller.
    """
    if not raw:
        return False
    try:
        payload = jwt.decode(raw, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return False
    return payload.get("scope") == ANON_SEARCH_SCOPE
