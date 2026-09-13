"""
User model and related types for authentication and authorization.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    WORKER = "worker"


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    role: UserRole = UserRole.WORKER
    assigned_mission_ids: List[str] = Field(default_factory=list)


class UserCreate(UserBase):
    """Model for creating a new user."""
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Model for updating a user."""
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    assigned_mission_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """User model as stored in database."""
    id: str = Field(alias="_id")
    password_hash: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class UserResponse(UserBase):
    """User model for API responses (no password hash)."""
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, user: UserInDB) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            assigned_mission_ids=user.assigned_mission_ids,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Decoded JWT token data."""
    sub: str  # user_id
    email: str
    role: UserRole
    exp: int
    iat: int


class LoginRequest(BaseModel):
    """Login request payload."""
    email: EmailStr
    password: str
    remember_me: bool = False


class RegisterRequest(UserCreate):
    """Registration request payload (admin only)."""
    pass


class BootstrapAdminRequest(BaseModel):
    """Bootstrap admin request."""
    email: EmailStr
    password: str = Field(min_length=8)
    secret: str  # One-time secret from env