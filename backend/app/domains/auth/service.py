from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.billing import plans
from app.domains.billing.models import Subscription

from . import models, schemas, utils
from .oauth import OAuthUserInfo
from .tasks import (
    send_password_reset_email_task,
    send_verification_email_task,
    send_welcome_email_task,
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, payload: schemas.UserRegister) -> models.User:
        """Register a new user"""
        # Check if user exists
        existing_user = self.db.query(models.User).filter(
            models.User.email == payload.email
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        verification_token = utils.generate_verification_token()
        hashed_password = utils.get_password_hash(payload.password)

        db_user = models.User(
            name=payload.name,
            email=payload.email,
            hashed_password=hashed_password,
            verification_token=verification_token,
            is_verified=False
        )

        self.db.add(db_user)
        # Flush (not commit) so db_user.id is assigned without ending the
        # transaction; this lets the user and its subscription be committed
        # atomically below.
        self.db.flush()
        self.db.refresh(db_user)

        # Provision the shared trial subscription, then commit user + trial
        # together (single commit: both persist or neither does).
        self._provision_trial(db_user.id)
        self.db.commit()
        self.db.refresh(db_user)

        # Send verification email asynchronously via Celery
        send_verification_email_task.delay(
            email=payload.email,
            name=payload.name,
            verification_token=verification_token
        )

        return db_user

    def _provision_trial(self, user_id: int) -> Subscription:
        """Add a 15-day, no-credit-card trial subscription for ``user_id``.

        The subscription is added to the session but **not** committed, so the
        caller controls the transaction boundary and can persist the user and
        its trial in a single atomic commit. Exactly one subscription per user;
        the trial spans the full trial window.
        """
        now = datetime.utcnow()
        trial_ends_at = now + timedelta(days=plans.TRIAL_PERIOD_DAYS)
        subscription = Subscription(
            user_id=user_id,
            plan=plans.PLAN_TRIAL,
            status=plans.STATUS_TRIALING,
            monthly_lead_quota=plans.TRIAL_LEAD_QUOTA,
            leads_used_this_period=0,
            period_start=now,
            period_end=trial_ends_at,
            trial_ends_at=trial_ends_at,
            read_only=False,
        )
        self.db.add(subscription)
        return subscription

    def login_or_create_oauth_user(
        self, provider: str, info: OAuthUserInfo
    ) -> models.User:
        """Resolve a normalized provider identity to a MapLeads user.

        Implements the epic's link-or-create rules:

        1. An existing ``OAuthAccount`` for ``(provider, provider_account_id)``
           logs the linked user straight in.
        2. A verified provider email that matches an existing user links a new
           ``OAuthAccount`` to that user (no duplicate user).
        3. A verified provider email with no matching user creates a new
           OAuth-only user (``hashed_password=None``, ``is_verified=True``), its
           ``OAuthAccount`` and a trial subscription, all in one commit.
        4. An unverified (or missing) provider email is rejected with 400; no
           user/account/subscription is written.

        This method is HTTP-free apart from that 400: the router mints the JWT.
        """
        # 1. Existing link -> straight login.
        existing_account = self.db.query(models.OAuthAccount).filter(
            models.OAuthAccount.provider == provider,
            models.OAuthAccount.provider_account_id == info.provider_account_id,
        ).first()
        if existing_account:
            return self.db.query(models.User).filter(
                models.User.id == existing_account.user_id
            ).first()

        # The provider must vouch for the email before we link or create; an
        # unverified email could be attacker-controlled and hijack an account.
        if not info.email_verified or not info.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Your {provider} email is not verified; verify it with "
                    f"{provider} and try again."
                ),
            )

        # 2. Verified email matching an existing user -> link that user.
        existing_user = self.db.query(models.User).filter(
            models.User.email == info.email
        ).first()
        if existing_user:
            oauth_account = models.OAuthAccount(
                user_id=existing_user.id,
                provider=provider,
                provider_account_id=info.provider_account_id,
            )
            self.db.add(oauth_account)
            self.db.commit()
            self.db.refresh(existing_user)
            return existing_user

        # 3. Verified email, no existing user -> create user + link + trial.
        db_user = models.User(
            name=info.name,
            email=info.email,
            hashed_password=None,
            is_verified=True,
        )
        self.db.add(db_user)
        # Flush so the generated id is available for the OAuthAccount and the
        # trial subscription; the single commit below keeps them atomic.
        self.db.flush()
        self.db.refresh(db_user)

        oauth_account = models.OAuthAccount(
            user_id=db_user.id,
            provider=provider,
            provider_account_id=info.provider_account_id,
        )
        self.db.add(oauth_account)
        self._provision_trial(db_user.id)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def login_user(self, payload: schemas.UserLogin) -> dict:
        """Login user and return JWT token"""
        user = self.db.query(models.User).filter(
            models.User.email == payload.email
        ).first()

        # ``hashed_password`` is nullable (OAuth-only users). Guard against None
        # so password login returns 401 rather than crashing verify_password.
        if (
            not user
            or not user.hashed_password
            or not utils.verify_password(payload.password, user.hashed_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in"
            )

        access_token = utils.create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

    def verify_email(self, token: str) -> models.User:
        """Verify user email with token"""
        user = self.db.query(models.User).filter(
            models.User.verification_token == token
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )

        user.is_verified = True
        user.verification_token = None
        self.db.commit()
        self.db.refresh(user)

        # Send welcome email asynchronously via Celery
        send_welcome_email_task.delay(
            email=user.email,
            name=user.name
        )

        return user

    def forgot_password(self, email: str) -> None:
        """Request password reset"""
        user: Optional[models.User] = self.db.query(models.User).filter(
            models.User.email == email
        ).first()

        if not user:
            # Don't reveal if email exists
            return

        # OAuth-only users have no local password to reset. Return silently so
        # forgot-password cannot bootstrap a parallel password credential (and
        # doesn't leak that the address is registered).
        if not user.hashed_password:
            return

        reset_token = utils.generate_reset_token()
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)

        self.db.commit()

        # Send password reset email asynchronously via Celery
        send_password_reset_email_task.delay(
            email=email,
            name=user.name,
            reset_token=reset_token
        )

    def reset_password(self, token: str, new_password: str) -> models.User:
        """Reset password with token"""
        user = self.db.query(models.User).filter(
            models.User.reset_token == token
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )

        if user.reset_token_expires < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )

        user.hashed_password = utils.get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None

        self.db.commit()
        self.db.refresh(user)

        return user

    def update_profile(
        self, user: models.User, payload: schemas.ProfileUpdate
    ) -> models.User:
        """Update the current user's profile (name and/or language).

        Only fields explicitly present in the request are applied, so a partial
        update never clears the omitted field. Ownership is implicit: the
        service operates on the already-resolved current user.
        """
        updates = payload.model_dump(exclude_unset=True)

        if "name" in updates:
            name = updates["name"]
            if name is None or not name.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Name cannot be empty",
                )
            user.name = name.strip()

        if "language" in updates:
            language = updates["language"]
            # The column is NOT NULL; an explicit ``null`` would otherwise blow
            # up as an IntegrityError (500) at commit time.
            if language is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Language cannot be null",
                )
            user.language = language

        self.db.commit()
        self.db.refresh(user)

        return user
