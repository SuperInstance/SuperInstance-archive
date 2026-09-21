"""
Multi-Frontend User Management System
Comprehensive user management across multiple frontend properties and platforms
"""

from typing import Dict, List, Optional, Any, Union, Set
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import json
import sqlite3
import hashlib
import bcrypt
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"        # Platform super admin
    PLATFORM_ADMIN = "platform_admin"  # Platform administrator
    FRONTEND_OWNER = "frontend_owner"   # Owns frontend properties
    FRONTEND_ADMIN = "frontend_admin"   # Manages specific frontend
    DEVELOPER = "developer"             # Development team member
    CONTENT_MANAGER = "content_manager" # Content management
    ANALYST = "analyst"                 # Analytics and reporting
    SUPPORT = "support"                 # Customer support
    USER = "user"                       # Regular user
    GUEST = "guest"                     # Guest access

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    LOCKED = "locked"

class PermissionScope(str, Enum):
    GLOBAL = "global"              # Platform-wide permissions
    FRONTEND = "frontend"          # Specific frontend permissions
    FEATURE = "feature"            # Feature-specific permissions
    DATA = "data"                  # Data access permissions

class Permission(BaseModel):
    id: str
    name: str
    description: str
    scope: PermissionScope
    resource: str = "*"  # Specific resource or * for all
    actions: List[str] = ["read"]  # read, write, delete, admin
    
    # Conditional permissions
    conditions: Dict[str, Any] = {}  # Time-based, IP-based, etc.
    
    created_at: datetime
    updated_at: datetime

class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    password_hash: str
    
    # Personal information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Status and verification
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    email_verified: bool = False
    phone_verified: bool = False
    
    # Security
    two_factor_enabled: bool = False
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    
    # Profile metadata
    timezone: str = "UTC"
    language: str = "en"
    theme: str = "default"
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_activity: Optional[datetime] = None

class FrontendAccess(BaseModel):
    id: str
    user_id: str
    frontend_id: str
    
    # Access details
    role: UserRole
    permissions: List[str] = []
    custom_permissions: List[Permission] = []
    
    # Access control
    granted_by: str
    granted_at: datetime
    expires_at: Optional[datetime] = None
    revoked: bool = False
    revoked_by: Optional[str] = None
    revoked_at: Optional[datetime] = None
    
    # Usage tracking
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    
    # Metadata
    access_reason: str = ""
    notes: str = ""

class UserSession(BaseModel):
    id: str
    user_id: str
    frontend_id: Optional[str] = None
    
    # Session details
    token: str
    refresh_token: Optional[str] = None
    device_info: Dict[str, str] = {}
    ip_address: str = ""
    user_agent: str = ""
    
    # Lifecycle
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    active: bool = True
    
    # Security
    login_method: str = "password"  # password, sso, api_key
    mfa_verified: bool = False

class UserGroup(BaseModel):
    id: str
    name: str
    description: str
    
    # Group properties
    frontend_id: Optional[str] = None  # Global group if None
    default_permissions: List[str] = []
    auto_assign: bool = False
    
    # Metadata
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    # Members
    member_count: int = 0

class ActivityLog(BaseModel):
    id: str
    user_id: str
    frontend_id: Optional[str] = None
    
    # Activity details
    action: str
    resource: str
    details: Dict[str, Any] = {}
    
    # Context
    ip_address: str = ""
    user_agent: str = ""
    session_id: Optional[str] = None
    
    # Metadata
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None

class MultiUserManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/frontend-market/data/user_management.db"
        self.init_database()
        
        # Default permissions by role
        self.role_permissions = {
            UserRole.SUPER_ADMIN: ["*:*"],
            UserRole.PLATFORM_ADMIN: ["platform:*", "frontend:*", "user:*"],
            UserRole.FRONTEND_OWNER: ["frontend:admin", "frontend:analytics", "user:manage"],
            UserRole.FRONTEND_ADMIN: ["frontend:admin", "content:*", "user:view"],
            UserRole.DEVELOPER: ["frontend:develop", "content:edit", "analytics:view"],
            UserRole.CONTENT_MANAGER: ["content:*", "media:*"],
            UserRole.ANALYST: ["analytics:*", "reports:*"],
            UserRole.SUPPORT: ["user:support", "tickets:*"],
            UserRole.USER: ["content:view", "profile:edit"],
            UserRole.GUEST: ["content:view"]
        }
        
        # Session management
        self.active_sessions: Dict[str, UserSession] = {}
    
    def init_database(self):
        """Initialize user management database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT DEFAULT 'pending_verification',
                email_verified BOOLEAN DEFAULT FALSE,
                two_factor_enabled BOOLEAN DEFAULT FALSE,
                failed_login_attempts INTEGER DEFAULT 0,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Frontend access table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS frontend_access (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                frontend_id TEXT NOT NULL,
                role TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                revoked BOOLEAN DEFAULT FALSE,
                data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, frontend_id)
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                frontend_id TEXT,
                token TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Permissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS permissions (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                scope TEXT NOT NULL,
                resource TEXT DEFAULT '*',
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User groups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                frontend_id TEXT,
                auto_assign BOOLEAN DEFAULT FALSE,
                created_by TEXT NOT NULL,
                member_count INTEGER DEFAULT 0,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Group memberships table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_memberships (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                added_by TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES user_groups (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(group_id, user_id)
            )
        ''')
        
        # Activity log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                frontend_id TEXT,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                ip_address TEXT,
                success BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def _create_default_permissions(self):
        """Create default system permissions"""
        
        default_permissions = [
            {
                "name": "platform:admin",
                "description": "Full platform administration",
                "scope": PermissionScope.GLOBAL,
                "resource": "platform",
                "actions": ["read", "write", "delete", "admin"]
            },
            {
                "name": "frontend:admin",
                "description": "Frontend administration",
                "scope": PermissionScope.FRONTEND,
                "resource": "frontend",
                "actions": ["read", "write", "delete", "admin"]
            },
            {
                "name": "frontend:develop",
                "description": "Frontend development access",
                "scope": PermissionScope.FRONTEND,
                "resource": "frontend",
                "actions": ["read", "write"]
            },
            {
                "name": "content:manage",
                "description": "Content management",
                "scope": PermissionScope.FEATURE,
                "resource": "content",
                "actions": ["read", "write", "delete"]
            },
            {
                "name": "analytics:view",
                "description": "View analytics data",
                "scope": PermissionScope.DATA,
                "resource": "analytics",
                "actions": ["read"]
            },
            {
                "name": "user:manage",
                "description": "User management",
                "scope": PermissionScope.FRONTEND,
                "resource": "users",
                "actions": ["read", "write", "delete"]
            }
        ]
        
        for perm_data in default_permissions:
            try:
                await self.create_permission(perm_data)
            except:
                pass  # Permission might already exist
    
    async def create_user(self, user_data: Dict[str, Any]) -> UserProfile:
        """Create a new user"""
        
        # Validate unique constraints
        if await self._user_exists(user_data["email"], user_data["username"]):
            raise ValueError("User with this email or username already exists")
        
        user_id = f"USER_{uuid.uuid4().hex[:8].upper()}"
        
        # Hash password
        password_hash = bcrypt.hashpw(
            user_data["password"].encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Create user profile
        user = UserProfile(
            id=user_id,
            username=user_data["username"],
            email=user_data["email"],
            password_hash=password_hash,
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            display_name=user_data.get("display_name", user_data["username"]),
            bio=user_data.get("bio"),
            timezone=user_data.get("timezone", "UTC"),
            language=user_data.get("language", "en"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users 
            (id, username, email, password_hash, status, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user.id, user.username, user.email, user.password_hash,
            user.status.value, user.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        # Log activity
        await self._log_activity(user_id, "user_created", "users", {"created_by": "system"})
        
        logger.info(f"Created user {user_id}: {user.username}")
        return user
    
    async def authenticate_user(self, login: str, password: str, 
                              frontend_id: Optional[str] = None) -> Optional[UserProfile]:
        """Authenticate user and return profile"""
        
        # Get user by email or username
        user = await self.get_user_by_login(login)
        if not user:
            return None
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now():
            raise ValueError(f"Account locked until {user.locked_until}")
        
        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            # Increment failed attempts
            await self._increment_failed_login(user.id)
            return None
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.now()
        user.last_activity = datetime.now()
        
        # Update user in database
        await self._update_user(user)
        
        # Check frontend access if specified
        if frontend_id:
            access = await self.get_frontend_access(user.id, frontend_id)
            if not access or access.revoked:
                raise ValueError("No access to specified frontend")
        
        # Log successful login
        await self._log_activity(user.id, "user_login", "auth", {
            "frontend_id": frontend_id,
            "success": True
        })
        
        return user
    
    async def create_session(self, user_id: str, frontend_id: Optional[str] = None,
                           device_info: Dict[str, str] = None,
                           ip_address: str = "") -> UserSession:
        """Create new user session"""
        
        session_id = f"SESSION_{uuid.uuid4().hex[:8].upper()}"
        token = hashlib.sha256(f"{session_id}{datetime.now()}".encode()).hexdigest()
        
        session = UserSession(
            id=session_id,
            user_id=user_id,
            frontend_id=frontend_id,
            token=token,
            device_info=device_info or {},
            ip_address=ip_address,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24)  # 24 hour session
        )
        
        # Store session
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_sessions 
            (id, user_id, frontend_id, token, ip_address, expires_at, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.id, session.user_id, session.frontend_id,
            session.token, session.ip_address,
            session.expires_at.isoformat(), session.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        # Cache session
        self.active_sessions[session.token] = session
        
        return session
    
    async def validate_session(self, token: str) -> Optional[UserSession]:
        """Validate session token"""
        
        # Check cached sessions first
        if token in self.active_sessions:
            session = self.active_sessions[token]
            if session.expires_at > datetime.now() and session.active:
                # Update last activity
                session.last_activity = datetime.now()
                return session
            else:
                # Remove expired session
                del self.active_sessions[token]
        
        # Check database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM user_sessions 
            WHERE token = ? AND active = TRUE AND expires_at > datetime('now')
        ''', (token,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            session_data = json.loads(result[0])
            session = UserSession(**session_data)
            session.last_activity = datetime.now()
            
            # Cache session
            self.active_sessions[token] = session
            return session
        
        return None
    
    async def grant_frontend_access(self, user_id: str, frontend_id: str,
                                  role: UserRole, granted_by: str,
                                  expires_at: Optional[datetime] = None,
                                  custom_permissions: List[str] = None) -> FrontendAccess:
        """Grant user access to a frontend"""
        
        access_id = f"ACCESS_{uuid.uuid4().hex[:8].upper()}"
        
        # Get default permissions for role
        default_permissions = self.role_permissions.get(role, [])
        all_permissions = list(set(default_permissions + (custom_permissions or [])))
        
        access = FrontendAccess(
            id=access_id,
            user_id=user_id,
            frontend_id=frontend_id,
            role=role,
            permissions=all_permissions,
            granted_by=granted_by,
            granted_at=datetime.now(),
            expires_at=expires_at
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use INSERT OR REPLACE to handle existing access
        cursor.execute('''
            INSERT OR REPLACE INTO frontend_access 
            (id, user_id, frontend_id, role, granted_by, granted_at, expires_at, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            access.id, access.user_id, access.frontend_id,
            access.role.value, access.granted_by,
            access.granted_at.isoformat(),
            access.expires_at.isoformat() if access.expires_at else None,
            access.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        # Log activity
        await self._log_activity(user_id, "access_granted", "frontend_access", {
            "frontend_id": frontend_id,
            "role": role.value,
            "granted_by": granted_by
        })
        
        logger.info(f"Granted {role.value} access to frontend {frontend_id} for user {user_id}")
        return access
    
    async def revoke_frontend_access(self, user_id: str, frontend_id: str,
                                   revoked_by: str, reason: str = "") -> bool:
        """Revoke user access to a frontend"""
        
        access = await self.get_frontend_access(user_id, frontend_id)
        if not access:
            return False
        
        # Mark as revoked
        access.revoked = True
        access.revoked_by = revoked_by
        access.revoked_at = datetime.now()
        
        # Update in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE frontend_access 
            SET revoked = TRUE, data = ?
            WHERE user_id = ? AND frontend_id = ?
        ''', (access.model_dump_json(), user_id, frontend_id))
        
        conn.commit()
        conn.close()
        
        # Invalidate related sessions
        await self._invalidate_frontend_sessions(user_id, frontend_id)
        
        # Log activity
        await self._log_activity(user_id, "access_revoked", "frontend_access", {
            "frontend_id": frontend_id,
            "revoked_by": revoked_by,
            "reason": reason
        })
        
        return True
    
    async def get_frontend_access(self, user_id: str, frontend_id: str) -> Optional[FrontendAccess]:
        """Get user's access to a frontend"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM frontend_access 
            WHERE user_id = ? AND frontend_id = ? AND revoked = FALSE
        ''', (user_id, frontend_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            access_data = json.loads(result[0])
            access = FrontendAccess(**access_data)
            
            # Check if expired
            if access.expires_at and access.expires_at < datetime.now():
                return None
            
            return access
        
        return None
    
    async def check_permission(self, user_id: str, frontend_id: Optional[str],
                             permission: str, resource: str = "*") -> bool:
        """Check if user has specific permission"""
        
        # Get user's access
        if frontend_id:
            access = await self.get_frontend_access(user_id, frontend_id)
            if not access:
                return False
            permissions = access.permissions
        else:
            # Check global permissions
            user = await self.get_user(user_id)
            if not user:
                return False
            # For simplicity, assume global permissions are stored in user profile
            permissions = []  # Would be loaded from user's global roles
        
        # Check permissions
        for perm in permissions:
            if perm == "*:*" or perm == f"{permission}:*" or perm == f"{permission}:{resource}":
                return True
        
        return False
    
    async def create_user_group(self, group_data: Dict[str, Any], created_by: str) -> UserGroup:
        """Create a new user group"""
        
        group_id = f"GROUP_{uuid.uuid4().hex[:8].upper()}"
        
        group = UserGroup(
            id=group_id,
            name=group_data["name"],
            description=group_data.get("description", ""),
            frontend_id=group_data.get("frontend_id"),
            default_permissions=group_data.get("default_permissions", []),
            auto_assign=group_data.get("auto_assign", False),
            created_by=created_by,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_groups 
            (id, name, frontend_id, auto_assign, created_by, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            group.id, group.name, group.frontend_id,
            group.auto_assign, group.created_by, group.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        return group
    
    async def add_user_to_group(self, group_id: str, user_id: str, added_by: str) -> bool:
        """Add user to group"""
        
        membership_id = f"MEMBERSHIP_{uuid.uuid4().hex[:8].upper()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO group_memberships 
                (id, group_id, user_id, added_by)
                VALUES (?, ?, ?, ?)
            ''', (membership_id, group_id, user_id, added_by))
            
            # Update member count
            cursor.execute('''
                UPDATE user_groups 
                SET member_count = member_count + 1
                WHERE id = ?
            ''', (group_id,))
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            # User already in group
            return False
        finally:
            conn.close()
    
    async def get_user_frontends(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all frontends a user has access to"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT frontend_id, role, data FROM frontend_access 
            WHERE user_id = ? AND revoked = FALSE
            AND (expires_at IS NULL OR expires_at > datetime('now'))
        ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        frontends = []
        for row in results:
            access_data = json.loads(row[2])
            access = FrontendAccess(**access_data)
            
            frontends.append({
                "frontend_id": row[0],
                "role": row[1],
                "permissions": access.permissions,
                "granted_at": access.granted_at.isoformat(),
                "last_accessed": access.last_accessed.isoformat() if access.last_accessed else None
            })
        
        return frontends
    
    async def get_frontend_users(self, frontend_id: str, role: Optional[UserRole] = None) -> List[Dict[str, Any]]:
        """Get all users with access to a frontend"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT u.id, u.username, u.email, u.status, fa.role, fa.data as access_data, u.data as user_data
            FROM users u
            JOIN frontend_access fa ON u.id = fa.user_id
            WHERE fa.frontend_id = ? AND fa.revoked = FALSE
            AND (fa.expires_at IS NULL OR fa.expires_at > datetime('now'))
        '''
        params = [frontend_id]
        
        if role:
            query += " AND fa.role = ?"
            params.append(role.value)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        users = []
        for row in results:
            access_data = json.loads(row[5])
            user_data = json.loads(row[6])
            
            users.append({
                "user_id": row[0],
                "username": row[1],
                "email": row[2],
                "status": row[3],
                "role": row[4],
                "display_name": user_data.get("display_name", row[1]),
                "last_login": user_data.get("last_login"),
                "last_accessed": access_data.get("last_accessed")
            })
        
        return users
    
    async def get_user_activity(self, user_id: str, frontend_id: Optional[str] = None,
                              limit: int = 100) -> List[ActivityLog]:
        """Get user activity logs"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT data FROM activity_logs 
            WHERE user_id = ?
        '''
        params = [user_id]
        
        if frontend_id:
            query += " AND frontend_id = ?"
            params.append(frontend_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [ActivityLog(**json.loads(result[0])) for result in results]
    
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user by ID"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_data = json.loads(result[0])
            return UserProfile(**user_data)
        
        return None
    
    async def get_user_by_login(self, login: str) -> Optional[UserProfile]:
        """Get user by email or username"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM users 
            WHERE email = ? OR username = ?
        ''', (login, login))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_data = json.loads(result[0])
            return UserProfile(**user_data)
        
        return None
    
    async def create_permission(self, permission_data: Dict[str, Any]) -> Permission:
        """Create a new permission"""
        
        permission_id = f"PERM_{uuid.uuid4().hex[:8].upper()}"
        
        permission = Permission(
            id=permission_id,
            name=permission_data["name"],
            description=permission_data.get("description", ""),
            scope=PermissionScope(permission_data["scope"]),
            resource=permission_data.get("resource", "*"),
            actions=permission_data.get("actions", ["read"]),
            conditions=permission_data.get("conditions", {}),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO permissions 
            (id, name, description, scope, resource, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            permission.id, permission.name, permission.description,
            permission.scope.value, permission.resource, permission.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        return permission
    
    async def _user_exists(self, email: str, username: str) -> bool:
        """Check if user already exists"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE email = ? OR username = ?
        ''', (email, username))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    async def _increment_failed_login(self, user_id: str):
        """Increment failed login attempts"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET failed_login_attempts = failed_login_attempts + 1
            WHERE id = ?
        ''', (user_id,))
        
        # Lock account after 5 failed attempts
        cursor.execute('''
            UPDATE users 
            SET locked_until = datetime('now', '+1 hour')
            WHERE id = ? AND failed_login_attempts >= 5
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    async def _update_user(self, user: UserProfile):
        """Update user in database"""
        
        user.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET failed_login_attempts = ?, data = ?, updated_at = ?
            WHERE id = ?
        ''', (
            user.failed_login_attempts, user.model_dump_json(),
            user.updated_at.isoformat(), user.id
        ))
        
        conn.commit()
        conn.close()
    
    async def _invalidate_frontend_sessions(self, user_id: str, frontend_id: str):
        """Invalidate all sessions for user on specific frontend"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_sessions 
            SET active = FALSE
            WHERE user_id = ? AND frontend_id = ?
        ''', (user_id, frontend_id))
        
        conn.commit()
        conn.close()
        
        # Remove from cache
        to_remove = []
        for token, session in self.active_sessions.items():
            if session.user_id == user_id and session.frontend_id == frontend_id:
                to_remove.append(token)
        
        for token in to_remove:
            del self.active_sessions[token]
    
    async def _log_activity(self, user_id: str, action: str, resource: str, 
                           details: Dict[str, Any], success: bool = True,
                           ip_address: str = ""):
        """Log user activity"""
        
        activity_id = f"ACTIVITY_{uuid.uuid4().hex[:8].upper()}"
        
        activity = ActivityLog(
            id=activity_id,
            user_id=user_id,
            frontend_id=details.get("frontend_id"),
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.now(),
            success=success
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO activity_logs 
            (id, user_id, frontend_id, action, resource, ip_address, success, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            activity.id, activity.user_id, activity.frontend_id,
            activity.action, activity.resource, activity.ip_address,
            activity.success, activity.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
    
    async def get_platform_statistics(self) -> Dict[str, Any]:
        """Get platform user statistics"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total users by status
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM users 
            GROUP BY status
        ''')
        user_status_counts = dict(cursor.fetchall())
        
        # Active sessions
        cursor.execute('''
            SELECT COUNT(*) 
            FROM user_sessions 
            WHERE active = TRUE AND expires_at > datetime('now')
        ''')
        active_sessions_count = cursor.fetchone()[0]
        
        # Frontend access counts
        cursor.execute('''
            SELECT frontend_id, COUNT(*) 
            FROM frontend_access 
            WHERE revoked = FALSE
            GROUP BY frontend_id
        ''')
        frontend_user_counts = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_users": sum(user_status_counts.values()),
            "user_status_breakdown": user_status_counts,
            "active_sessions": active_sessions_count,
            "frontend_user_counts": frontend_user_counts,
            "cached_sessions": len(self.active_sessions)
        }

# Global instance
multi_frontend_user_manager = MultiUserManager()