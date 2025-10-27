from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from apps.auth.models import User
from apps.auth.schemas import (
    UserCreate, UserResponse, UserLogin, UserLoginResponse,
    PasswordChange, PasswordReset, PasswordResetConfirm,
    EmailVerification, MessageResponse, RefreshToken, Token
)
from apps.auth.utils import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, create_email_verification_token,
    create_reset_token, verify_token, send_verification_email,
    send_password_reset_email
)

auth_router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    email = verify_token(token, "access")
    
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


@auth_router.post("/register", response_model=MessageResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with email verification."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create verification token
    verification_token = create_email_verification_token(user_data.email)
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        verification_token=verification_token
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send verification email
    email_sent = send_verification_email(user_data.email, verification_token)
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )
    
    return MessageResponse(
        message="User registered successfully. Please check your email to verify your account."
    )


@auth_router.post("/login", response_model=UserLoginResponse)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return tokens."""
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is deactivated"
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified. Please check your email and verify your account."
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return UserLoginResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token
    )


@auth_router.post("/refresh", response_model=Token)
async def refresh_access_token(refresh_data: RefreshToken, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    email = verify_token(refresh_data.refresh_token, "refresh")
    
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    new_access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.email})
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )


@auth_router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """Send password reset email."""
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    if not user:
        # Don't reveal if email exists or not for security
        return MessageResponse(
            message="If the email exists in our system, you will receive a password reset link."
        )
    
    # Generate reset token and set expiration
    reset_token = create_reset_token()
    reset_expires = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiration
    
    # Update user with reset token
    user.reset_token = reset_token
    user.reset_token_expires = reset_expires
    db.commit()
    
    # Send reset email
    email_sent = send_password_reset_email(reset_data.email, reset_token)
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )
    
    return MessageResponse(
        message="If the email exists in our system, you will receive a password reset link."
    )


@auth_router.post("/reset-password", response_model=MessageResponse)
async def reset_password(reset_data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password using reset token."""
    user = db.query(User).filter(User.reset_token == reset_data.token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    # Check if token has expired
    if user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Update password and clear reset token
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return MessageResponse(message="Password reset successfully")


@auth_router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return MessageResponse(message="Password changed successfully")


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@auth_router.post("/verify-email", response_model=MessageResponse)
async def verify_email(verification_data: EmailVerification, db: Session = Depends(get_db)):
    """Verify user email using verification token."""
    email = verify_token(verification_data.token, "email_verification")
    
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        return MessageResponse(message="Email already verified")
    
    # Mark user as verified
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return MessageResponse(message="Email verified successfully")


@auth_router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification_email(email_data: PasswordReset, db: Session = Depends(get_db)):
    """Resend email verification."""
    user = db.query(User).filter(User.email == email_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        return MessageResponse(message="Email already verified")
    
    # Create new verification token
    verification_token = create_email_verification_token(user.email)
    user.verification_token = verification_token
    db.commit()
    
    # Send verification email
    email_sent = send_verification_email(user.email, verification_token)
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )
    
    return MessageResponse(message="Verification email sent successfully")
