"""Dependencies that gate the internal-only promotions endpoints.

Promo-code creation/listing is a staff/machine call, not a customer action, so
it is guarded by a dedicated internal secret (``settings.INTERNAL_API_KEY``)
read from the ``x-internal-key`` header — deliberately **separate** from the
customer-facing ``x-api-key`` gateway, which every frontend request already
carries and therefore cannot serve as the gate.

We intentionally did *not* introduce an ``is_staff`` flag on ``users`` to model
this: that would mean a users-table migration and a larger auth surface for a
single internal endpoint. A shared internal secret is the minimal fit. These
endpoints still sit under ``/api/v1`` and so remain behind the ``x-api-key``
middleware in production, giving defense in depth.

The header value is never logged.
"""

import secrets

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_internal_key(
    x_internal_key: str | None = Header(default=None),
) -> None:
    """Allow the request only when a correct ``x-internal-key`` is presented.

    * Unconfigured (``INTERNAL_API_KEY == ""``) → 503, so the endpoint is never
      open by default.
    * Missing or mismatched header → 403.
    * Correct key → allowed.
    """
    if settings.INTERNAL_API_KEY == "":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API is not configured.",
        )
    if x_internal_key is None or not secrets.compare_digest(
        x_internal_key, settings.INTERNAL_API_KEY
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key.",
        )
