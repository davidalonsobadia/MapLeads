"""Tests for the profile fields and the PATCH /auth/me endpoint.

The ``client`` fixture is authenticated as ``test_user`` (see ``conftest.py``).
The auth-requirement test builds a separate client that overrides only
``get_db``, so the real ``get_verified_user`` dependency runs and rejects the
unauthenticated request.
"""

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app

ME = "/api/v1/auth/me"


def test_me_includes_language_default(client, test_user):
    """A freshly created user reports the default language 'en'."""
    response = client.get(ME)
    assert response.status_code == 200
    assert response.json()["language"] == "en"


def test_update_profile_name(client, db_session, test_user):
    """PATCH name -> 200 and the change is persisted."""
    response = client.patch(ME, json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"

    db_session.refresh(test_user)
    assert test_user.name == "New Name"


def test_update_profile_language(client, db_session, test_user):
    """PATCH language 'es' is persisted and echoed by GET /me."""
    response = client.patch(ME, json={"language": "es"})
    assert response.status_code == 200
    assert response.json()["language"] == "es"

    db_session.refresh(test_user)
    assert test_user.language == "es"

    assert client.get(ME).json()["language"] == "es"


def test_update_profile_invalid_language(client):
    """An unsupported language is rejected with 422."""
    response = client.patch(ME, json={"language": "fr"})
    assert response.status_code == 422


def test_update_profile_partial_does_not_clear_other_fields(
    client, db_session, test_user
):
    """Sending only name leaves language untouched, and vice versa."""
    client.patch(ME, json={"language": "es"})

    response = client.patch(ME, json={"name": "Only Name"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Only Name"
    assert body["language"] == "es"

    db_session.refresh(test_user)
    assert test_user.name == "Only Name"
    assert test_user.language == "es"


def test_update_profile_blank_name_rejected(client):
    """A blank name is rejected with 422."""
    response = client.patch(ME, json={"name": "   "})
    assert response.status_code == 422


def test_update_profile_requires_auth(db_session):
    """An unauthenticated PATCH is rejected (no verified user)."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as unauth_client:
            response = unauth_client.patch(ME, json={"name": "Nope"})
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()
