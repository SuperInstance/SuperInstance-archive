"""
Advanced Authentication and Authorization System
JWT-based auth with role-based access control and API key support
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import hashlib
import secrets

from api.models import UserPermissions, APIKey
from utils.config import Config

logger = logging.getLogger(__name__)

# Security configuration
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration
SECRET_KEY = "your-secret-key-here-change-in-production"  # Should be from config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# In-memory storage (should be database in production)
users_db: Dict[str, Dict[str, Any]] = {
    "admin": {
        "user_id": "admin",
        "username": "admin",
        "email": "admin@hardware-abstraction.local",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "admin"
        "permissions": [
            "device:read", "device:write", "device:control", "device:discover",
            "system:read", "system:configure", "system:admin",
            "maintenance:predict", "analytics:read", "health:read"
        ],
        "roles": ["admin", "operator"],
        "is_active": True,
        "created_at": datetime.now()
    },
    "operator": {
        "user_id": "operator",
        "username": "operator", 
        "email": "operator@hardware-abstraction.local",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "operator"
        "permissions": [
            "device:read", "device:control", "device:discover",
            "analytics:read", "health:read"
        ],
        "roles": ["operator"],
        "is_active": True,
        "created_at": datetime.now()
    },
    "viewer": {
        "user_id": "viewer",
        "username": "viewer",
        "email": "viewer@hardware-abstraction.local", 
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "viewer"
        "permissions": ["device:read", "analytics:read", "health:read"],
        "roles": ["viewer"],
        "is_active": True,
        "created_at": datetime.now()
    }
}

api_keys_db: Dict[str, APIKey] = {
    "ha-key-admin-001": APIKey(
        key_id="ha-key-admin-001",
        name="Admin API Key",
        permissions=[
            "device:read", "device:write", "device:control", "device:discover",
            "system:read", "system:configure", "system:admin",
            "maintenance:predict", "analytics:read", "health:read"
        ],
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=365),
        is_active=True
    ),
    "ha-key-readonly-001": APIKey(
        key_id="ha-key-readonly-001", 
        name="Read-Only API Key",
        permissions=["device:read", "analytics:read", "health:read"],
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=90),
        is_active=True
    )
}

# Permission definitions with hierarchical structure
PERMISSION_HIERARCHY = {
    "device": {
        "read": "Read device information and status",
        "write": "Create, update, and delete devices", 
        "control": "Execute commands on devices",
        "discover": "Discover new devices"
    },
    "system": {
        "read": "Read system configuration and status",
        "configure": "Modify system configuration",
        "admin": "Full system administration access"
    },
    "maintenance": {
        "predict": "Access predictive maintenance features",
        "schedule": "Schedule maintenance operations",
        "execute": "Execute maintenance operations"
    },
    "analytics": {
        "read": "Access analytics and reporting",
        "export": "Export analytics data"
    },
    "health": {
        "read": "Read health monitoring data",
        "configure": "Configure health monitoring settings"
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username/password"""
    user = users_db.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    if not user.get("is_active", False):
        return None
    return user

async def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = users_db.get(username)
    if user is None:
        raise credentials_exception
    
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    return user

async def get_current_user_from_api_key(api_key: Optional[str] = Depends(api_key_header)) -> Optional[Dict[str, Any]]:
    """Get current user from API key"""
    if not api_key:
        return None
    
    key_data = api_keys_db.get(api_key)
    if not key_data:
        return None
    
    if not key_data.is_active:
        return None
    
    if key_data.expires_at and datetime.now() > key_data.expires_at:
        return None
    
    # Update last used timestamp
    key_data.last_used = datetime.now()
    
    # Return user-like object for API key
    return {
        "user_id": f"api_key_{key_data.key_id}",
        "username": f"api_key_{key_data.name}",
        "permissions": key_data.permissions,
        "roles": ["api_user"],
        "is_api_key": True,
        "api_key_id": key_data.key_id
    }

async def get_current_user(
    token_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_token),
    api_key_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_api_key)
) -> Dict[str, Any]:
    """Get current user from either token or API key"""
    # Prefer token authentication
    if token_user:
        return token_user
    
    # Fall back to API key
    if api_key_user:
        return api_key_user
    
    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )

def check_permission(user: Dict[str, Any], required_permission: str) -> bool:
    """Check if user has required permission"""
    user_permissions = user.get("permissions", [])
    
    # Admin users have all permissions
    if "system:admin" in user_permissions:
        return True
    
    # Check exact permission match
    if required_permission in user_permissions:
        return True
    
    # Check wildcard permissions
    permission_parts = required_permission.split(":")
    if len(permission_parts) == 2:
        category, action = permission_parts
        wildcard_permission = f"{category}:*"
        if wildcard_permission in user_permissions:
            return True
    
    return False

def require_permissions(required_permissions: List[str]):
    """Dependency factory for requiring specific permissions"""
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        for permission in required_permissions:
            if not check_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission}"
                )
        return current_user
    return permission_checker

def require_roles(required_roles: List[str]):
    """Dependency factory for requiring specific roles"""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = current_user.get("roles", [])
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        return current_user
    return role_checker

async def create_api_key(
    name: str,
    permissions: List[str],
    expires_in_days: Optional[int] = None,
    user: Dict[str, Any] = None
) -> APIKey:
    """Create new API key"""
    if user and not check_permission(user, "system:admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create API keys"
        )
    
    # Validate permissions
    valid_permissions = []
    for category, perms in PERMISSION_HIERARCHY.items():
        for perm in perms.keys():
            valid_permissions.append(f"{category}:{perm}")
    
    invalid_perms = [p for p in permissions if p not in valid_permissions and not p.endswith(":*")]
    if invalid_perms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permissions: {invalid_perms}"
        )
    
    # Generate API key
    key_id = f"ha-key-{secrets.token_hex(8)}"
    
    # Set expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now() + timedelta(days=expires_in_days)
    
    api_key = APIKey(
        key_id=key_id,
        name=name,
        permissions=permissions,
        created_at=datetime.now(),
        expires_at=expires_at,
        is_active=True
    )
    
    api_keys_db[key_id] = api_key
    logger.info(f"Created API key: {key_id} for {name}")
    
    return api_key

async def revoke_api_key(key_id: str, user: Dict[str, Any]) -> bool:
    """Revoke API key"""
    if not check_permission(user, "system:admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to revoke API keys"
        )
    
    if key_id not in api_keys_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_keys_db[key_id].is_active = False
    logger.info(f"Revoked API key: {key_id}")
    return True

async def list_api_keys(user: Dict[str, Any]) -> List[APIKey]:
    """List all API keys (admin only)"""
    if not check_permission(user, "system:admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list API keys"
        )
    
    return list(api_keys_db.values())

async def get_user_permissions(user: Dict[str, Any]) -> UserPermissions:
    """Get user permissions and roles"""
    return UserPermissions(
        user_id=user["user_id"],
        permissions=user.get("permissions", []),
        roles=user.get("roles", [])
    )

def get_available_permissions() -> Dict[str, Dict[str, str]]:
    """Get all available permissions with descriptions"""
    return PERMISSION_HIERARCHY

# Security utility functions
def generate_secure_key() -> str:
    """Generate cryptographically secure API key"""
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def rate_limit_key(user_id: str, endpoint: str) -> str:
    """Generate rate limiting key"""
    return f"rate_limit:{user_id}:{endpoint}"

# Session management
active_sessions: Dict[str, Dict[str, Any]] = {}

async def create_session(user: Dict[str, Any]) -> str:
    """Create user session"""
    session_id = secrets.token_urlsafe(32)
    active_sessions[session_id] = {
        "user_id": user["user_id"],
        "created_at": datetime.now(),
        "last_activity": datetime.now(),
        "permissions": user.get("permissions", []),
        "roles": user.get("roles", [])
    }
    return session_id

async def invalidate_session(session_id: str) -> bool:
    """Invalidate user session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return True
    return False

async def get_active_sessions() -> List[Dict[str, Any]]:
    """Get all active sessions"""
    return list(active_sessions.values())

# Audit logging
audit_log: List[Dict[str, Any]] = []

async def log_security_event(
    event_type: str,
    user_id: str,
    details: Dict[str, Any],
    success: bool = True
) -> None:
    """Log security-related events"""
    audit_log.append({
        "timestamp": datetime.now(),
        "event_type": event_type,
        "user_id": user_id,
        "success": success,
        "details": details
    })
    
    # Keep only last 1000 entries
    if len(audit_log) > 1000:
        audit_log.pop(0)
    
    logger.info(f"Security event: {event_type} by {user_id} - {'Success' if success else 'Failed'}")

async def get_security_config() -> Dict[str, Any]:
    """Get security configuration"""
    return {
        "jwt_expiry_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
        "password_policy": {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True, 
            "require_numbers": True,
            "require_special": True
        },
        "session_timeout_minutes": 60,
        "max_failed_attempts": 5,
        "lockout_duration_minutes": 15
    }