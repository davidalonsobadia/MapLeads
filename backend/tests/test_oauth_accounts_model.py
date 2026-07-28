"""Tests for the OAuth data foundation: nullable password + oauth_accounts."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.auth.models import OAuthAccount, User


def _make_user(db_session, email="oauth@example.com", hashed_password=None):
    user = User(
        name="OAuth User",
        email=email,
        hashed_password=hashed_password,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_user_without_password_persists(db_session):
    """A User with hashed_password=None round-trips through the database."""
    user = _make_user(db_session)

    reloaded = db_session.query(User).filter(User.id == user.id).first()
    assert reloaded is not None
    assert reloaded.hashed_password is None


def test_oauth_account_unique_provider_identity(db_session):
    """A duplicate (provider, provider_account_id) pair raises IntegrityError."""
    user = _make_user(db_session)

    db_session.add(
        OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_account_id="prov-123",
        )
    )
    db_session.commit()

    db_session.add(
        OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_account_id="prov-123",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_oauth_account_links_to_user(db_session):
    """An OAuthAccount created with a valid user_id persists and links back."""
    user = _make_user(db_session)

    account = OAuthAccount(
        user_id=user.id,
        provider="github",
        provider_account_id="gh-999",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    assert account.id is not None
    assert account.user_id == user.id


def test_login_oauth_only_user_returns_401_not_500(client, db_session):
    """Logging in as an OAuth-only user (no password) returns 401, not a 500."""
    _make_user(db_session, email="oauthlogin@example.com", hashed_password=None)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "oauthlogin@example.com", "password": "whatever"},
    )

    assert response.status_code == 401
