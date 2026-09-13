"""
Authentication service - JWT handling, password hashing, and role-based dependencies.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from enum import Enum

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import EmailStr

from backend.config import settings
from backend.models.user import UserRole, UserInDB, UserResponse, TokenData, Token
from backend.db.mongodb import get_collection


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# Cookie names
ACCESS_TOKEN_COOKIE = "fathom_access_token"
REFRESH_TOKEN_COOKIE = "fathom_refresh_token"

# HTTP Bearer for Swagger UI
security = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """Authentication error."""
    pass


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return TokenData(
            sub=payload.get("sub"),
            email=payload.get("email"),
            role=UserRole(payload.get("role")),
            exp=payload.get("exp"),
            iat=payload.get("iat"),
        )
    except JWTError as e:
        raise AuthError(f"Invalid token: {str(e)}")


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, remember_me: bool = False) -> None:
    """Set authentication cookies on response."""
    # Access token cookie
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    # Refresh token cookie (longer expiry)
    refresh_max_age = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    if not remember_me:
        refresh_max_age = 24 * 60 * 60  # 1 day if not remember me
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=refresh_max_age,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/", secure=settings.ENVIRONMENT == "production", samesite="lax")
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path="/", secure=settings.ENVIRONMENT == "production", samesite="lax")


async def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Get user by email from database."""
    collection = get_collection("users")
    doc = await collection.find_one({"email": email.lower()})
    if doc:
        doc["_id"] = str(doc["_id"])
        return UserInDB(**doc)
    return None


async def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Get user by ID from database."""
    from bson import ObjectId
    collection = get_collection("users")
    doc = await collection.find_one({"_id": ObjectId(user_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
        return UserInDB(**doc)
    return None


async def create_user(user_data: dict) -> UserInDB:
    """Create a new user in database."""
    collection = get_collection("users")
    user_data["email"] = user_data["email"].lower()
    user_data["password_hash"] = hash_password(user_data.pop("password"))
    user_data["created_at"] = datetime.now(timezone.utc)
    user_data["updated_at"] = datetime.now(timezone.utc)
    user_data["is_active"] = True

    result = await collection.insert_one(user_data)
    user_data["_id"] = str(result.inserted_id)
    return UserInDB(**user_data)


async def get_current_user_from_cookie(request: Request) -> Optional[UserInDB]:
    """Extract current user from cookie (for browser clients)."""
    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not access_token:
        return None

    try:
        token_data = decode_token(access_token)
        user = await get_user_by_id(token_data.sub)
        if user and user.is_active:
            return user
    except AuthError:
        pass
    return None


async def get_current_user_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserInDB]:
    """Extract current user from Authorization header (for API clients/Swagger)."""
    if not credentials:
        return None

    try:
        token_data = decode_token(credentials.credentials)
        user = await get_user_by_id(token_data.sub)
        if user and user.is_active:
            return user
    except AuthError:
        pass
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserInDB:
    """Get current authenticated user (cookie or header)."""
    # Try cookie first (browser)
    user = await get_current_user_from_cookie(request)
    if user:
        return user

    # Try header (API clients)
    user = await get_current_user_from_header(credentials)
    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(allowed_roles: List[UserRole]):
    """Dependency factory for role-based access control."""
    async def role_checker(user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}",
            )
        return user
    return role_checker


# Pre-defined role dependencies
require_admin = require_role([UserRole.ADMIN])
require_supervisor_or_admin = require_role([UserRole.SUPERVISOR, UserRole.ADMIN])
require_any_role = require_role([UserRole.WORKER, UserRole.SUPERVISOR, UserRole.ADMIN])


def get_current_user_response(user: UserInDB = Depends(get_current_user)) -> UserResponse:
    """Get current user as response model."""
    return UserResponse.from_db(user)