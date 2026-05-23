"""
Authentication utilities: password hashing, token management, and verification.
Implements Argon2 password hashing (like Django) and JWT tokens with secure cookies.
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from src.config import settings

# Password hashing context using Argon2 (secure, slow, salt-based like Django)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,        # 3 iterations
    argon2__parallelism=4,      # 4 threads
)

# Token settings
SECRET_KEY = settings.secret_key
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2.
    
    Args:
        password: Plaintext password string
    
    Returns:
        Hashed password (includes salt and algorithm identifier)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.
    
    Args:
        plain_password: Plaintext password from user input
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        data: Dictionary of claims to encode (e.g., {"uid": "user_id"})
        expires_delta: Optional custom expiration timedelta (default: ACCESS_TOKEN_EXPIRE_MINUTES)

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        data: Dictionary of claims to encode (e.g., {"uid": "user_id"})
        expires_delta: Optional custom expiration timedelta (default: REFRESH_TOKEN_EXPIRE_DAYS)

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: Optional[str] = None) -> Optional[dict]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh"). If provided,
                    the token's "type" claim must match or None is returned.

    Returns:
        Decoded token payload as dict, or None if invalid/expired/wrong type
    """
    try:
        # jwt.decode checks if token is expired and raises error if so
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if token_type is not None and payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None
