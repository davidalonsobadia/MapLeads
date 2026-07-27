from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    String,
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
    hashed_password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    # Preferred UI language. Allowed set: en | es.
    language = Column(String(2), nullable=False, server_default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
