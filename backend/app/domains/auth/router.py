from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

from . import models, oauth, schemas, service, utils
from .oauth import OAuthClient, OAuthError, OAuthUnconfiguredError

router = APIRouter(prefix="/auth", tags=["auth"])


def get_oauth_client(provider: str) -> OAuthClient:
    """Resolve the real OAuth client for ``provider``.

    This is the seam tests override (mirrors ``get_places_client`` in the search
    domain): tests install a fake via ``app.dependency_overrides``. The library's
    errors are mapped to HTTP here so both OAuth endpoints share the behavior —
    an unknown provider is a 400 and an unconfigured one a 503 (mirroring the
    Stripe-unconfigured response).
    """
    try:
        return oauth.get_oauth_client(provider)
    except OAuthUnconfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth provider '{provider}' is not configured.",
        ) from exc
    except OAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown OAuth provider '{provider}'.",
        ) from exc


def _oauth_redirect_uri(provider: str) -> str:
    """Derive the callback URL server-side.

    Never trust a client-supplied redirect (open-redirect risk); it is always
    ``{FRONTEND_URL}/api/auth/oauth/{provider}/callback``.
    """
    return f"{settings.FRONTEND_URL}/api/auth/oauth/{provider}/callback"


@router.post("/register", response_model=schemas.MessageResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user. Sends verification email.
    """
    auth_service = service.AuthService(db)
    user = auth_service.register_user(user_data)
    return {"message": f"Registration successful. Please check {user.email} for verification link."}


@router.post("/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    """
    Login user and return JWT token. Requires verified email.
    """
    auth_service = service.AuthService(db)
    token_data = auth_service.login_user(user_data)

    # Set HTTP-only cookie (optional, for additional security)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token_data['access_token']}",
        httponly=True,
        secure=True,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=1800  # 30 minutes
    )

    return token_data


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(response: Response):
    """
    Logout user by clearing the cookie.
    """
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(utils.get_verified_user)):
    """
    Get current authenticated user information.
    """
    return current_user


@router.patch("/me", response_model=schemas.UserResponse)
def update_me(
    payload: schemas.ProfileUpdate,
    current_user: models.User = Depends(utils.get_verified_user),
    db: Session = Depends(get_db),
):
    """
    Update the current authenticated user's profile (name and/or language).
    """
    auth_service = service.AuthService(db)
    return auth_service.update_profile(current_user, payload)


@router.post("/verify-email", response_model=schemas.MessageResponse)
def verify_email(data: schemas.VerifyEmail, db: Session = Depends(get_db)):
    """
    Verify user email with token sent via email.
    """
    auth_service = service.AuthService(db)
    auth_service.verify_email(data.token)
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/forgot-password", response_model=schemas.MessageResponse)
def forgot_password(data: schemas.ForgotPassword, db: Session = Depends(get_db)):
    """
    Request password reset. Sends reset link to email.
    """
    auth_service = service.AuthService(db)
    auth_service.forgot_password(data.email)
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password", response_model=schemas.MessageResponse)
def reset_password(data: schemas.ResetPassword, db: Session = Depends(get_db)):
    """
    Reset password using token from email.
    """
    auth_service = service.AuthService(db)
    auth_service.reset_password(data.token, data.new_password)
    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.get(
    "/oauth/{provider}/authorize",
    response_model=schemas.OAuthAuthorizeResponse,
)
def oauth_authorize(
    provider: str,
    oauth_client: OAuthClient = Depends(get_oauth_client),
):
    """Start the OAuth flow: build the provider authorization URL and signed state.

    ``provider`` is validated (and its client resolved) by ``get_oauth_client``:
    unknown -> 400, unconfigured -> 503. The redirect URI is derived server-side.
    """
    redirect_uri = _oauth_redirect_uri(provider)
    state = utils.create_oauth_state(provider)
    authorization_url = oauth_client.build_authorize_url(redirect_uri, state)
    return schemas.OAuthAuthorizeResponse(
        authorization_url=authorization_url, state=state
    )


@router.post(
    "/oauth/{provider}/callback",
    response_model=schemas.OAuthTokenResponse,
)
def oauth_callback(
    provider: str,
    data: schemas.OAuthCallbackRequest,
    db: Session = Depends(get_db),
    oauth_client: OAuthClient = Depends(get_oauth_client),
):
    """Complete the OAuth flow: exchange the code, link/create the user, issue our JWT.

    Provider/transport failures from the client surface as 502; the link-or-create
    rules (and the 400 for an unverified provider email) live in the service.
    """
    redirect_uri = _oauth_redirect_uri(provider)
    try:
        access_token = oauth_client.exchange_code(data.code, redirect_uri)
        info = oauth_client.fetch_user_info(access_token)
    except OAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="provider authentication failed",
        ) from exc

    auth_service = service.AuthService(db)
    user = auth_service.login_or_create_oauth_user(provider, info)
    session_token = utils.create_access_token(data={"sub": str(user.id)})
    return schemas.OAuthTokenResponse(
        access_token=session_token,
        token_type="bearer",
        user=schemas.UserResponse.model_validate(user),
    )
