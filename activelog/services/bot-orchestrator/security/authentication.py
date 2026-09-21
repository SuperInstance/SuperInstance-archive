import asyncio
import logging
import hashlib
import secrets
import time
import jwt
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import threading
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import pyotp
import qrcode
import io
import base64
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class UserRole(Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    BOT = "bot"
    SERVICE = "service"

class Permission(Enum):
    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_VIEW = "system:view"
    SYSTEM_CONFIG = "system:config"
    
    # Task permissions
    TASK_CREATE = "task:create"
    TASK_EXECUTE = "task:execute"
    TASK_VIEW = "task:view"
    TASK_DELETE = "task:delete"
    
    # Bot permissions
    BOT_REGISTER = "bot:register"
    BOT_MANAGE = "bot:manage"
    BOT_VIEW = "bot:view"
    
    # Context permissions
    CONTEXT_CREATE = "context:create"
    CONTEXT_VIEW = "context:view"
    CONTEXT_DELETE = "context:delete"
    
    # Information sharing permissions
    INFO_SHARE = "info:share"
    INFO_VIEW = "info:view"
    INFO_MANAGE = "info:manage"
    
    # Monitoring permissions
    MONITORING_VIEW = "monitoring:view"
    MONITORING_CONFIG = "monitoring:config"
    ALERTS_MANAGE = "alerts:manage"

@dataclass
class User:
    id: str
    username: str
    email: str
    password_hash: str
    roles: Set[UserRole] = field(default_factory=set)
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    is_verified: bool = False
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    login_count: int = 0
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "roles": [role.value for role in self.roles],
            "permissions": [perm.value for perm in self.permissions],
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "mfa_enabled": self.mfa_enabled,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count,
            "metadata": self.metadata
        }
        
        if include_sensitive:
            data.update({
                "password_hash": self.password_hash,
                "mfa_secret": self.mfa_secret,
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None
            })
        
        return data
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def is_locked(self) -> bool:
        """Check if account is locked"""
        return self.locked_until and datetime.now() < self.locked_until

@dataclass
class APIKey:
    id: str
    key_hash: str
    name: str
    user_id: str
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    ip_restrictions: List[str] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if API key is expired"""
        return self.expires_at and datetime.now() > self.expires_at

@dataclass
class Session:
    id: str
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at

class PasswordManager:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.min_length = 8
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_symbols = True
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(password, hashed)
    
    def validate_password_strength(self, password: str) -> tuple[bool, List[str]]:
        """Validate password strength"""
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.require_symbols and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one symbol")
        
        return len(errors) == 0, errors
    
    def generate_password(self, length: int = 12) -> str:
        """Generate a secure password"""
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

class MFAManager:
    def __init__(self):
        self.issuer_name = "Bot Orchestrator"
    
    def generate_secret(self) -> str:
        """Generate a new MFA secret"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user: User, secret: str) -> str:
        """Generate QR code for MFA setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=self.issuer_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, secret: str, token: str) -> bool:
        """Verify MFA token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 1 window (30 seconds) tolerance

class TokenManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "roles": [role.value for role in user.roles],
            "permissions": [perm.value for perm in user.permissions],
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user.id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

class SecurityAuditLogger:
    def __init__(self):
        self.audit_log = []
        self.max_log_size = 10000
        self.lock = threading.Lock()
    
    def log_event(self, event_type: str, user_id: str = None, ip_address: str = None, 
                  details: Dict[str, Any] = None):
        """Log security event"""
        with self.lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "ip_address": ip_address,
                "details": details or {}
            }
            
            self.audit_log.append(event)
            
            # Keep log size manageable
            if len(self.audit_log) > self.max_log_size:
                self.audit_log = self.audit_log[-self.max_log_size//2:]
            
            logger.info(f"Security audit: {event_type} - User: {user_id} - IP: {ip_address}")
    
    def get_recent_events(self, limit: int = 100, event_type: str = None,
                         user_id: str = None) -> List[Dict[str, Any]]:
        """Get recent security events"""
        with self.lock:
            events = self.audit_log[-limit:]
            
            # Filter by event type
            if event_type:
                events = [e for e in events if e["event_type"] == event_type]
            
            # Filter by user ID
            if user_id:
                events = [e for e in events if e["user_id"] == user_id]
            
            return events

class AuthenticationManager:
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or Fernet.generate_key().decode()
        self.users = {}
        self.api_keys = {}
        self.sessions = {}
        
        # Managers
        self.password_manager = PasswordManager()
        self.mfa_manager = MFAManager()
        self.token_manager = TokenManager(self.secret_key)
        self.audit_logger = SecurityAuditLogger()
        
        # Security settings
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 30
        self.session_timeout_minutes = 60
        
        # Default roles and permissions
        self._initialize_default_roles()
        
        self.lock = threading.RLock()
    
    def _initialize_default_roles(self):
        """Initialize default role-permission mappings"""
        self.default_role_permissions = {
            UserRole.ADMIN: {
                Permission.SYSTEM_ADMIN,
                Permission.SYSTEM_VIEW,
                Permission.SYSTEM_CONFIG,
                Permission.TASK_CREATE,
                Permission.TASK_EXECUTE,
                Permission.TASK_VIEW,
                Permission.TASK_DELETE,
                Permission.BOT_REGISTER,
                Permission.BOT_MANAGE,
                Permission.BOT_VIEW,
                Permission.CONTEXT_CREATE,
                Permission.CONTEXT_VIEW,
                Permission.CONTEXT_DELETE,
                Permission.INFO_SHARE,
                Permission.INFO_VIEW,
                Permission.INFO_MANAGE,
                Permission.MONITORING_VIEW,
                Permission.MONITORING_CONFIG,
                Permission.ALERTS_MANAGE
            },
            UserRole.OPERATOR: {
                Permission.SYSTEM_VIEW,
                Permission.TASK_CREATE,
                Permission.TASK_EXECUTE,
                Permission.TASK_VIEW,
                Permission.BOT_VIEW,
                Permission.CONTEXT_CREATE,
                Permission.CONTEXT_VIEW,
                Permission.INFO_SHARE,
                Permission.INFO_VIEW,
                Permission.MONITORING_VIEW
            },
            UserRole.VIEWER: {
                Permission.SYSTEM_VIEW,
                Permission.TASK_VIEW,
                Permission.BOT_VIEW,
                Permission.CONTEXT_VIEW,
                Permission.INFO_VIEW,
                Permission.MONITORING_VIEW
            },
            UserRole.BOT: {
                Permission.TASK_EXECUTE,
                Permission.CONTEXT_CREATE,
                Permission.CONTEXT_VIEW,
                Permission.INFO_SHARE,
                Permission.INFO_VIEW
            },
            UserRole.SERVICE: {
                Permission.SYSTEM_VIEW,
                Permission.TASK_CREATE,
                Permission.TASK_VIEW,
                Permission.INFO_VIEW
            }
        }
    
    async def create_user(self, username: str, email: str, password: str, 
                         roles: Set[UserRole] = None) -> User:
        """Create a new user"""
        with self.lock:
            # Validate password
            is_valid, errors = self.password_manager.validate_password_strength(password)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Password validation failed: {'; '.join(errors)}"
                )
            
            # Check if user already exists
            for user in self.users.values():
                if user.username == username or user.email == email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User with this username or email already exists"
                    )
            
            user_id = f"user_{secrets.token_hex(8)}"
            password_hash = self.password_manager.hash_password(password)
            
            # Assign default permissions based on roles
            user_roles = roles or {UserRole.VIEWER}
            permissions = set()
            for role in user_roles:
                permissions.update(self.default_role_permissions.get(role, set()))
            
            user = User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                roles=user_roles,
                permissions=permissions
            )
            
            self.users[user_id] = user
            
            self.audit_logger.log_event(
                "user_created",
                user_id=user_id,
                details={"username": username, "email": email, "roles": [r.value for r in user_roles]}
            )
            
            logger.info(f"User created: {username} ({user_id})")
            return user
    
    async def authenticate_user(self, username: str, password: str, mfa_token: str = None,
                              ip_address: str = None) -> tuple[User, str, str]:
        """Authenticate user and return access/refresh tokens"""
        with self.lock:
            # Find user
            user = None
            for u in self.users.values():
                if u.username == username or u.email == username:
                    user = u
                    break
            
            if not user:
                self.audit_logger.log_event(
                    "login_failed",
                    details={"reason": "user_not_found", "username": username},
                    ip_address=ip_address
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            # Check if account is locked
            if user.is_locked():
                self.audit_logger.log_event(
                    "login_blocked",
                    user_id=user.id,
                    details={"reason": "account_locked"},
                    ip_address=ip_address
                )
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is temporarily locked"
                )
            
            # Check if account is active
            if not user.is_active:
                self.audit_logger.log_event(
                    "login_blocked",
                    user_id=user.id,
                    details={"reason": "account_inactive"},
                    ip_address=ip_address
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is inactive"
                )
            
            # Verify password
            if not self.password_manager.verify_password(password, user.password_hash):
                user.failed_login_attempts += 1
                
                if user.failed_login_attempts >= self.max_login_attempts:
                    user.locked_until = datetime.now() + timedelta(minutes=self.lockout_duration_minutes)
                    logger.warning(f"User account locked due to too many failed attempts: {user.username}")
                
                self.audit_logger.log_event(
                    "login_failed",
                    user_id=user.id,
                    details={"reason": "invalid_password", "attempts": user.failed_login_attempts},
                    ip_address=ip_address
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            # Check MFA if enabled
            if user.mfa_enabled:
                if not mfa_token:
                    raise HTTPException(
                        status_code=status.HTTP_200_OK,
                        detail="MFA token required",
                        headers={"X-MFA-Required": "true"}
                    )
                
                if not self.mfa_manager.verify_token(user.mfa_secret, mfa_token):
                    self.audit_logger.log_event(
                        "login_failed",
                        user_id=user.id,
                        details={"reason": "invalid_mfa_token"},
                        ip_address=ip_address
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid MFA token"
                    )
            
            # Successful authentication
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.now()
            user.login_count += 1
            
            # Generate tokens
            access_token = self.token_manager.create_access_token(user)
            refresh_token = self.token_manager.create_refresh_token(user)
            
            self.audit_logger.log_event(
                "login_success",
                user_id=user.id,
                ip_address=ip_address,
                details={"login_count": user.login_count}
            )
            
            logger.info(f"User authenticated: {user.username}")
            return user, access_token, refresh_token
    
    async def create_api_key(self, user_id: str, name: str, permissions: Set[Permission] = None,
                           expires_days: int = None) -> tuple[APIKey, str]:
        """Create API key for user"""
        with self.lock:
            if user_id not in self.users:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Generate API key
            raw_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            
            expires_at = None
            if expires_days:
                expires_at = datetime.now() + timedelta(days=expires_days)
            
            api_key_id = f"key_{secrets.token_hex(8)}"
            
            api_key = APIKey(
                id=api_key_id,
                key_hash=key_hash,
                name=name,
                user_id=user_id,
                permissions=permissions or set(),
                expires_at=expires_at
            )
            
            self.api_keys[api_key_id] = api_key
            
            self.audit_logger.log_event(
                "api_key_created",
                user_id=user_id,
                details={"key_id": api_key_id, "name": name, "expires_at": expires_at.isoformat() if expires_at else None}
            )
            
            return api_key, raw_key
    
    async def verify_api_key(self, raw_key: str, ip_address: str = None) -> tuple[User, APIKey]:
        """Verify API key and return associated user"""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        with self.lock:
            # Find API key
            api_key = None
            for key in self.api_keys.values():
                if key.key_hash == key_hash:
                    api_key = key
                    break
            
            if not api_key:
                self.audit_logger.log_event(
                    "api_key_invalid",
                    details={"key_hash": key_hash[:8]},
                    ip_address=ip_address
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            
            # Check if key is active and not expired
            if not api_key.is_active or api_key.is_expired():
                self.audit_logger.log_event(
                    "api_key_inactive",
                    user_id=api_key.user_id,
                    details={"key_id": api_key.id, "reason": "inactive" if not api_key.is_active else "expired"},
                    ip_address=ip_address
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key is inactive or expired"
                )
            
            # Get associated user
            user = self.users.get(api_key.user_id)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is inactive"
                )
            
            # Update usage statistics
            api_key.last_used = datetime.now()
            api_key.usage_count += 1
            
            return user, api_key
    
    async def setup_mfa(self, user_id: str) -> tuple[str, str]:
        """Setup MFA for user and return secret and QR code"""
        with self.lock:
            user = self.users.get(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Generate MFA secret
            secret = self.mfa_manager.generate_secret()
            qr_code = self.mfa_manager.generate_qr_code(user, secret)
            
            # Store secret (not enabled yet)
            user.mfa_secret = secret
            
            self.audit_logger.log_event(
                "mfa_setup_initiated",
                user_id=user_id
            )
            
            return secret, qr_code
    
    async def enable_mfa(self, user_id: str, mfa_token: str) -> bool:
        """Enable MFA for user after verifying token"""
        with self.lock:
            user = self.users.get(user_id)
            if not user or not user.mfa_secret:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MFA not set up for this user"
                )
            
            # Verify token
            if not self.mfa_manager.verify_token(user.mfa_secret, mfa_token):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid MFA token"
                )
            
            user.mfa_enabled = True
            
            self.audit_logger.log_event(
                "mfa_enabled",
                user_id=user_id
            )
            
            logger.info(f"MFA enabled for user: {user.username}")
            return True
    
    def require_permission(self, required_permission: Permission):
        """Decorator to require specific permission"""
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                # Get current user from context (this would be set by authentication middleware)
                current_user = kwargs.get('current_user')
                if not current_user or not current_user.has_permission(required_permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required: {required_permission.value}"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_role(self, required_role: UserRole):
        """Decorator to require specific role"""
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                current_user = kwargs.get('current_user')
                if not current_user or not current_user.has_role(required_role):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient role. Required: {required_role.value}"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user management statistics"""
        with self.lock:
            total_users = len(self.users)
            active_users = sum(1 for user in self.users.values() if user.is_active)
            mfa_enabled_users = sum(1 for user in self.users.values() if user.mfa_enabled)
            locked_users = sum(1 for user in self.users.values() if user.is_locked())
            
            role_counts = {}
            for role in UserRole:
                role_counts[role.value] = sum(1 for user in self.users.values() if role in user.roles)
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "mfa_enabled_users": mfa_enabled_users,
                "locked_users": locked_users,
                "role_counts": role_counts,
                "total_api_keys": len(self.api_keys),
                "active_api_keys": sum(1 for key in self.api_keys.values() if key.is_active and not key.is_expired())
            }

class BearerTokenAuth(HTTPBearer):
    def __init__(self, auth_manager: AuthenticationManager):
        super().__init__(auto_error=False)
        self.auth_manager = auth_manager
    
    async def __call__(self, request) -> Optional[User]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            return None
        
        token = credentials.credentials
        ip_address = request.client.host if hasattr(request, 'client') else None
        
        try:
            # Try JWT token first
            payload = self.auth_manager.token_manager.verify_token(token)
            user_id = payload.get("sub")
            
            if user_id in self.auth_manager.users:
                user = self.auth_manager.users[user_id]
                if user.is_active:
                    return user
        
        except HTTPException:
            # Try API key
            try:
                user, api_key = await self.auth_manager.verify_api_key(token, ip_address)
                return user
            except HTTPException:
                pass
        
        return None