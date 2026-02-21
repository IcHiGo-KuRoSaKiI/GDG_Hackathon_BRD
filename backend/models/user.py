"""
User data models.
Represents authenticated users in the system.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=100)


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class User(BaseModel):
    """Complete user model."""
    user_id: str  # Firebase UID
    email: str
    display_name: str
    created_at: datetime
    last_login: Optional[datetime] = None
    project_count: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserResponse(BaseModel):
    """API response model for user operations."""
    user_id: str
    email: str
    display_name: str
    created_at: datetime
    project_count: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuthToken(BaseModel):
    """Authentication token response."""
    token: str
    user: UserResponse
    expires_in: int = 3600  # 1 hour
