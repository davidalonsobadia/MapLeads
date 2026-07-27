from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


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

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
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
