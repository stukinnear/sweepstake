
from datetime import datetime
from enum import Enum
from typing import Optional, ClassVar, List, TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func
from sqlmodel import SQLModel, Field
from sqlalchemy.orm import relationship as sa_relationship
from pydantic import EmailStr


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"

if TYPE_CHECKING:
    from .models import User  # type: ignore  # for forward reference

class Session(SQLModel, table=True):
    """Database model for user sessions."""
    __tablename__ = "sessions"

    id: str = Field(primary_key=True, index=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked: bool = Field(default=False)
    last_refresh: Optional[datetime] = Field(default=None)

    # SQLAlchemy ORM relationship to User
    user: ClassVar["User"] = sa_relationship("User", back_populates="sessions")


# Database model
class User(SQLModel, table=True):
    """Database model for users."""
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    email: str = Field(unique=True, index=True, nullable=False, description="User's email address")
    hashed_password: str = Field(nullable=False, description="Bcrypt-hashed password")
    first_name: str = Field(nullable=False, description="User's first name")
    last_name: Optional[str] = Field(default=None, nullable=True, description="User's last name")
    user_name: Optional[str] = Field(default=None, nullable=True, description="User's public display name")
    gender: Optional[Gender] = Field(default=None, nullable=True, description="User's gender")
    is_active: bool = Field(default=True, nullable=False, description="User account status")
    is_superuser: bool = Field(default=False, nullable=False, description="Superuser privileges flag")
    created_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False),
        description="Account creation timestamp"
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False),
        description="Last update timestamp"
    )
    password_reset_token: Optional[str] = Field(default=None, nullable=True, description="Single-use password reset token (contains embedded expiry)")

    # SQLAlchemy ORM relationship for sessions (for DB session model)
    sessions: ClassVar[List["Session"]] = sa_relationship("Session", back_populates="user")


# Request/Response schemas
class UserBase(SQLModel):
    """Shared fields for user schemas."""
    email: EmailStr = Field(..., description="User's email address")
    first_name: str = Field(..., max_length=30, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=60, description="User's last name")
    user_name: Optional[str] = Field(None, max_length=40, description="User's display name")
    gender: Optional[str] = Field(None, description="User's gender")


class UserCreate(UserBase):
    """User registration payload."""
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")


class UserLogin(SQLModel):
    """User login credentials."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserRead(UserBase):
    """User information (response model)."""
    id: int = Field(..., description="Unique user identifier")
    is_active: bool = Field(default=True, description="Whether the user account is active")
    is_superuser: bool = Field(default=False, description="Whether the user has superuser privileges")
    created_at: datetime = Field(..., description="User account creation timestamp")
    updated_at: datetime = Field(..., description="User account last update timestamp")


class UserUpdate(SQLModel):
    """Partial user update payload."""
    email: Optional[EmailStr] = Field(None, description="New email address")
    first_name: Optional[str] = Field(None, max_length=30, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=60, description="User's last name")
    user_name: Optional[str] = Field(None, max_length=40, description="User's display name")
    gender: Optional[str] = Field(None, description="User's gender")
    is_active: Optional[bool] = Field(None, description="User account status")
    is_superuser: Optional[bool] = Field(None, description="Superuser permission status")


class ChangePasswordRequest(SQLModel):
    """Request payload for password change."""
    current_password: str = Field(..., description="User's current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class TokenResponse(SQLModel):
    """Successful authentication response."""
    # access_token: str = Field(..., description="JWT access token for authenticated requests")
    # token_type: str = Field(default="bearer", description="Token authentication type")
    user: UserRead = Field(..., description="Authenticated user information")


class ForgotPasswordRequest(SQLModel):
    """Request payload for initiating a password reset."""
    email: EmailStr = Field(..., description="Email address of the account to reset")


class ResetPasswordRequest(SQLModel):
    """Request payload for completing a password reset."""
    token: str = Field(..., description="Password reset token from the email link")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")
