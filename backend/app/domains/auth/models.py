from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Enforce the supported UI languages at the database layer, mirroring
        # the leads/subscriptions domain convention.
        CheckConstraint(
            "language IN ('en', 'es')",
            name="ck_users_language",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    # Nullable so OAuth-only users (Google/GitHub) can exist without a password.
    hashed_password = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    # Preferred UI language. Allowed set: en | es.
    language = Column(String(2), nullable=False, server_default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class OAuthAccount(Base):
    """A provider identity (Google/GitHub) linked to a MapLeads user.

    Each row maps one external provider account to a single ``users`` row. The
    unique constraint on ``(provider, provider_account_id)`` guarantees that a
    given provider identity resolves to at most one MapLeads user. A user may
    have several rows here (one per provider they signed in with).

    This is the data foundation only — the service layer that consumes these
    links (sign-in, account linking) is implemented in follow-up tasks.
    """

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_account_id",
            name="uq_oauth_accounts_provider_identity",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    # Provider slug, e.g. "google" / "github".
    provider = Column(String, nullable=False)
    # The provider's stable user id for this account.
    provider_account_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
