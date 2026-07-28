"""Tests for the OAuthAccount model, nullable user password and the login
guard that keeps password auth safe for OAuth-only users."""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domains.auth.models import OAuthAccount, User


def _make_user(session, email="owner@example.com", hashed_password="x"):
    user = User(
        name="Owner",
        email=email,
        hashed_password=hashed_password,
        is_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def fk_session():
    """A SQLite session with foreign-key enforcement ON, so ON DELETE CASCADE
    actually fires (SQLite disables FK enforcement by default)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_user_without_password_persists(db_session):
    """A User with hashed_password=None round-trips."""
    user = User(
        name="OAuth User",
        email="oauth@example.com",
        hashed_password=None,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    reloaded = db_session.query(User).filter(User.id == user.id).first()
    assert reloaded is not None
    assert reloaded.hashed_password is None


def test_oauth_account_unique_provider_identity(db_session):
    """Two OAuthAccount rows with the same (provider, provider_account_id)
    violate the unique constraint."""
    user = _make_user(db_session)

    db_session.add(
        OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_account_id="google-123",
        )
    )
    db_session.commit()

    db_session.add(
        OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_account_id="google-123",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_oauth_account_links_to_user(db_session):
    """An OAuthAccount created with a valid user_id persists and matches."""
    user = _make_user(db_session)

    account = OAuthAccount(
        user_id=user.id,
        provider="github",
        provider_account_id="github-456",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    assert account.id is not None
    assert account.user_id == user.id
    assert account.created_at is not None


def test_oauth_account_cascade_deletes_with_user(fk_session):
    """Deleting a User removes its OAuthAccount rows via ON DELETE CASCADE."""
    user = _make_user(fk_session)
    account = OAuthAccount(
        user_id=user.id,
        provider="google",
        provider_account_id="google-789",
    )
    fk_session.add(account)
    fk_session.commit()
    account_id = account.id

    fk_session.delete(user)
    fk_session.commit()

    assert (
        fk_session.query(OAuthAccount)
        .filter(OAuthAccount.id == account_id)
        .first()
        is None
    )


def test_login_oauth_only_user_returns_401_not_500(client, db_session):
    """Password login against an OAuth-only user (no hashed_password) returns
    401, not a 500 from verify_password choking on a None hash."""
    db_session.add(
        User(
            name="OAuth Only",
            email="oauth-only@example.com",
            hashed_password=None,
            is_verified=True,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "oauth-only@example.com", "password": "whatever"},
    )

    assert response.status_code == 401


def test_forgot_password_noop_for_oauth_only_user(db_session, monkeypatch):
    """forgot_password does not mint a reset token (or send mail) for an
    OAuth-only user, so a password credential cannot be bootstrapped."""
    sent = []
    monkeypatch.setattr(
        "app.domains.auth.service.send_password_reset_email_task.delay",
        lambda *args, **kwargs: sent.append(kwargs),
    )

    from app.domains.auth.service import AuthService

    user = _make_user(
        db_session, email="oauth-forgot@example.com", hashed_password=None
    )

    AuthService(db_session).forgot_password(user.email)
    db_session.refresh(user)

    assert user.reset_token is None
    assert sent == []
