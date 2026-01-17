"""JWT Authentication module with bcrypt password hashing."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import (
    JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, REFRESH_TOKEN_EXPIRE_DAYS,
    AUTH_BYPASS, DUMMY_USER_EMAIL, DUMMY_USER_NAME
)
from workspace_store import WorkspaceStore

# HTTP Bearer security scheme
security = HTTPBearer()

# Global store reference (will be set from main.py)
_store: Optional[WorkspaceStore] = None


def init_auth(store: WorkspaceStore) -> None:
    """Initialize auth module with workspace store."""
    global _store
    _store = store
    
    # Create dummy user for bypass mode if it doesn't exist
    if AUTH_BYPASS:
        existing = store.get_user_by_email(DUMMY_USER_EMAIL)
        if not existing:
            store.create_user(
                email=DUMMY_USER_EMAIL,
                hashed_password=hash_password("bypass"),
                name=DUMMY_USER_NAME,
            )
            print(f"[AUTH BYPASS] Created dummy user: {DUMMY_USER_EMAIL}")
        else:
            print(f"[AUTH BYPASS] Using existing dummy user: {DUMMY_USER_EMAIL}")


def get_store() -> WorkspaceStore:
    """Get the workspace store instance."""
    if _store is None:
        raise RuntimeError("Auth module not initialized. Call init_auth() first.")
    return _store


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt (non-blocking alternative to bcrypt)."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        salt, stored_hash = hashed_password.split('$')
        hash_obj = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000)
        return hash_obj.hex() == stored_hash
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_tokens(user_id: str) -> Dict[str, str]:
    """Create both access and refresh tokens."""
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_dummy_user() -> Optional[Dict[str, Any]]:
    """Get the dummy user for bypass mode."""
    store = get_store()
    return store.get_user_by_email(DUMMY_USER_EMAIL)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Dict[str, Any]:
    """Dependency to get current authenticated user from JWT token."""
    # Bypass mode - return dummy user
    if AUTH_BYPASS:
        user = get_dummy_user()
        if user:
            return user
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if credentials is None:
        raise credentials_exception
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    store = get_store()
    user = store.get_user_by_id(user_id)
    
    if user is None:
        raise credentials_exception
    
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[Dict[str, Any]]:
    """Optional dependency - returns user if authenticated, None otherwise."""
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None or payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if user_id is None:
        return None
    
    store = get_store()
    user = store.get_user_by_id(user_id)
    
    if user is None or not user.get("is_active", False):
        return None
    
    return user


def validate_refresh_token(token: str) -> Optional[str]:
    """Validate refresh token and return user_id if valid."""
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    if payload.get("type") != "refresh":
        return None
    
    user_id = payload.get("sub")
    if user_id is None:
        return None
    
    store = get_store()
    user = store.get_user_by_id(user_id)
    
    if user is None or not user.get("is_active", False):
        return None
    
    return user_id
