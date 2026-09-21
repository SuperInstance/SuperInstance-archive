"""
Authentication and authorization middleware
"""

from fastapi import Header, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

from ..models import User, RateLimitTier


# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Mock API key database (replace with actual database)
api_keys_db = {}
users_db = {}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_api_key(authorization: str = Header(None)) -> str:
    """
    Verify API key from Authorization header

    Format: Authorization: Bearer YOUR_API_KEY
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, api_key = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate API key (check against database)
    if not await validate_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return api_key


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        tier: str = payload.get("tier", RateLimitTier.FREE)

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Fetch user from database
    user = await get_user(username)
    if user is None:
        raise credentials_exception

    return user


async def validate_api_key(api_key: str) -> bool:
    """Validate API key against database"""
    # Implementation: Check database for API key
    # For now, accept any non-empty key
    return bool(api_key)


async def get_user(username: str) -> Optional[User]:
    """Fetch user from database"""
    # Implementation: Fetch from database
    # Mock user for demonstration
    if username in users_db:
        return users_db[username]

    return User(
        id="user_123",
        username=username,
        email=f"{username}@example.com",
        tier=RateLimitTier.FREE,
        created_at=datetime.utcnow()
    )


async def get_api_key_tier(api_key: str) -> RateLimitTier:
    """Get rate limit tier for API key"""
    # Implementation: Fetch from database
    if api_key in api_keys_db:
        return api_keys_db[api_key].tier
    return RateLimitTier.FREE


def require_tier(required_tier: RateLimitTier):
    """Dependency to require minimum tier"""
    async def tier_dependency(api_key: str = Depends(verify_api_key)):
        tier = await get_api_key_tier(api_key)
        tier_levels = {
            RateLimitTier.FREE: 0,
            RateLimitTier.PRO: 1,
            RateLimitTier.TEAM: 2,
            RateLimitTier.ENTERPRISE: 3
        }

        if tier_levels[tier] < tier_levels[required_tier]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {required_tier} tier or higher"
            )

        return api_key

    return tier_dependency
