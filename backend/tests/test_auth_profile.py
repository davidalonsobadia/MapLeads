"""Tests for the profile read/update surface of the auth domain.

Covers ``GET /api/v1/auth/me`` (now including ``language``) and the new
``PATCH /api/v1/auth/me`` endpoint that updates the current user's name and/or
language.
"""

from app.domains.auth.utils import get_verified_user
from app.main import app

ME = "/api/v1/auth/me"


def test_me_includes_language_default(client):
    """A freshly seeded user reports the default language 'en'."""
    resp = client.get(ME)
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "en"


def test_update_profile_name(client, test_user, db_session):
    resp = client.patch(ME, json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"

    db_session.refresh(test_user)
    assert test_user.name == "New Name"


def test_update_profile_language(client, test_user, db_session):
    resp = client.patch(ME, json={"language": "es"})
    assert resp.status_code == 200
    assert resp.json()["language"] == "es"

    # Persisted and echoed back by /me.
    db_session.refresh(test_user)
    assert test_user.language == "es"
    assert client.get(ME).json()["language"] == "es"


def test_update_profile_invalid_language(client):
    resp = client.patch(ME, json={"language": "fr"})
    assert resp.status_code == 422


def test_update_profile_null_language(client, test_user, db_session):
    """An explicit null language is rejected with 422, not a 500."""
    resp = client.patch(ME, json={"language": None})
    assert resp.status_code == 422

    db_session.refresh(test_user)
    assert test_user.language == "en"


def test_update_profile_blank_name(client):
    resp = client.patch(ME, json={"name": "   "})
    assert resp.status_code == 422


def test_update_profile_partial_preserves_other(client, test_user, db_session):
    """Sending only one field must not clear the other."""
    # Seed a non-default language first.
    client.patch(ME, json={"language": "es"})

    # Update only the name; language must stay 'es'.
    resp = client.patch(ME, json={"name": "Only Name"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Only Name"
    assert body["language"] == "es"

    db_session.refresh(test_user)
    assert test_user.language == "es"
    assert test_user.name == "Only Name"


def test_update_profile_requires_auth(client):
    """An unauthenticated PATCH is rejected (401/403), consistent with GET /me."""
    # Drop the seeded-user override so the real dependency runs with no creds.
    app.dependency_overrides.pop(get_verified_user, None)
    resp = client.patch(ME, json={"name": "Nope"})
    assert resp.status_code in (401, 403)
