from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_verified: bool
    language: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    """Partial update for the current user's profile.

    Both fields are optional; only the fields explicitly present in the request
    body are applied (see ``AuthService.update_profile``). ``language`` is
    validated against the supported set here, so an unsupported value (or an
    explicit ``null``) is rejected with 422 before reaching the service.
    """

    name: Optional[str] = None
    language: Optional[Literal["en", "es"]] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class VerifyEmail(BaseModel):
    token: str

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str

class MessageResponse(BaseModel):
    message: str
