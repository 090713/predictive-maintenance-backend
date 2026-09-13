"""
Authentication routes - login, logout, register, me, bootstrap admin.
"""
from datetime import timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer
from pydantic import EmailStr

from backend.config import settings
from backend.models.user import (
    UserRole, UserCreate, UserResponse, Token, LoginRequest, RegisterRequest, BootstrapAdminRequest
)
from backend.services.auth import (
    verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies,
    get_user_by_email, create_user, get_current_user,
    require_admin, require_supervisor_or_admin,
    ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from backend.db.mongodb import get_collection
from bson import ObjectId


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    current_user: UserResponse = Depends(require_admin)
):
    """
    Register a new user (admin only).
    Creates a user with specified role and assigned missions.
    """
    # Check if email already exists
    existing = await get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate assigned missions exist
    if user_data.assigned_mission_ids:
        missions_collection = get_collection("missions")
        existing_missions = await missions_collection.find(
            {"mission_id": {"$in": user_data.assigned_mission_ids}}
        ).to_list(length=None)
        if len(existing_missions) != len(user_data.assigned_mission_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more mission_ids do not exist",
            )

    user = await create_user(user_data.model_dump())
    return UserResponse.from_db(user)


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    credentials: LoginRequest
):
    """
    Login with email and password.
    Sets httpOnly cookies for access and refresh tokens.
    """
    user = await get_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    # Create tokens
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
    }

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if credentials.remember_me:
        access_token_expires = timedelta(days=7)

    access_token = create_access_token(token_data, access_token_expires)
    refresh_token = create_refresh_token(token_data)

    # Set cookies
    set_auth_cookies(response, access_token, refresh_token, credentials.remember_me)

    return Token(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout - clear authentication cookies."""
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user


@router.post("/bootstrap-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap_admin(request: BootstrapAdminRequest):
    """
    Bootstrap the first admin user.
    Only works if no admin exists and secret matches environment variable.
    """
    # Check secret
    if not settings.BOOTSTRAP_ADMIN_SECRET or request.secret != settings.BOOTSTRAP_ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bootstrap secret",
        )

    # Check if any admin exists
    users_collection = get_collection("users")
    admin_exists = await users_collection.find_one({"role": UserRole.ADMIN.value})
    if admin_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin user already exists",
        )

    # Create admin user
    admin_data = {
        "email": request.email.lower(),
        "password": request.password,
        "role": UserRole.ADMIN,
        "assigned_mission_ids": [],
    }
    admin = await create_user(admin_data)
    return UserResponse.from_db(admin)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    role: Optional[UserRole] = None,
    current_user: UserResponse = Depends(require_admin)
):
    """List all users (admin only)."""
    users_collection = get_collection("users")
    query = {}
    if role:
        query["role"] = role.value

    cursor = users_collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
    users = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        users.append(UserResponse.from_db(UserInDB(**doc)))
    return users


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: dict,
    current_user: UserResponse = Depends(require_admin)
):
    """Update a user (admin only)."""
    users_collection = get_collection("users")

    # Prevent self-demotion
    if str(current_user.id) == user_id and "role" in update_data:
        if update_data["role"] != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own admin role",
            )

    # Validate missions if provided
    if "assigned_mission_ids" in update_data:
        missions_collection = get_collection("missions")
        existing = await missions_collection.find(
            {"mission_id": {"$in": update_data["assigned_mission_ids"]}}
        ).to_list(length=None)
        if len(existing) != len(update_data["assigned_mission_ids"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more mission_ids do not exist",
            )

    update_data["updated_at"] = datetime.now(timezone.utc)
    result = await users_collection.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
        return_document=True
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result["_id"] = str(result["_id"])
    return UserResponse.from_db(UserInDB(**result))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserResponse = Depends(require_admin)
):
    """Delete a user (admin only)."""
    # Prevent self-deletion
    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    users_collection = get_collection("users")
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"message": "User deleted successfully"}