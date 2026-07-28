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
    # Nullable: OAuth-only users authenticate through a provider and have no password.
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
    """Provider identity (Google/GitHub) linked to a MapLeads user."""

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        # One provider identity maps to at most one MapLeads user.
        UniqueConstraint(
            "provider",
            "provider_account_id",
            name="uq_oauth_accounts_provider_identity",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider = Column(String, nullable=False)
    provider_account_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
