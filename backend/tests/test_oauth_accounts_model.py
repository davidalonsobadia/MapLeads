"""Tests for the OAuth data foundation: nullable user password and the
``OAuthAccount`` link table with its unique provider-identity constraint."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.auth.models import OAuthAccount, User


def _make_user(db_session, email="oauth@example.com", hashed_password=None) -> User:
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
    """A user with ``hashed_password=None`` round-trips through the DB."""
    user = _make_user(db_session, hashed_password=None)

    reloaded = db_session.query(User).filter_by(id=user.id).one()
    assert reloaded.hashed_password is None
    assert reloaded.email == "oauth@example.com"


def test_oauth_account_links_to_user(db_session):
    """An OAuthAccount created with a valid ``user_id`` persists and links back."""
    user = _make_user(db_session)

    account = OAuthAccount(
        user_id=user.id,
        provider="google",
        provider_account_id="google-123",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    assert account.id is not None
    assert account.user_id == user.id
    assert account.provider == "google"
    assert account.provider_account_id == "google-123"
    assert account.created_at is not None


def test_oauth_account_unique_provider_identity(db_session):
    """Two OAuthAccount rows with the same (provider, provider_account_id)
    violate the unique constraint."""
    user = _make_user(db_session)

    db_session.add(
        OAuthAccount(
            user_id=user.id,
            provider="github",
            provider_account_id="gh-42",
        )
    )
    db_session.commit()

    db_session.add(
        OAuthAccount(
            user_id=user.id,
            provider="github",
            provider_account_id="gh-42",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
