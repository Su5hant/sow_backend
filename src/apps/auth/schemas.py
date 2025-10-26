from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


# Base User schema
class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# User creation schema
class UserCreate(UserBase):
    password: str


# User response schema
class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# Login schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# Password change schemas
class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# Email verification schemas
class EmailVerification(BaseModel):
    token: str


# Response schemas
class MessageResponse(BaseModel):
    message: str


class UserLoginResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Refresh token schema
class RefreshToken(BaseModel):
    refresh_token: str