"""
Core Permission Management System
Comprehensive permission control with granular settings and security features
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission access levels"""
    NONE = "none"
    READ = "read" 
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    OWNER = "owner"


class ResourceType(Enum):
    """Types of resources that can have permissions"""
    FILE = "file"
    DIRECTORY = "directory"
    DATABASE = "database"
    SERVICE = "service"
    API = "api"
    DEVICE = "device"
    NETWORK = "network"
    APPLICATION = "application"
    SYSTEM = "system"


class PermissionStatus(Enum):
    """Status of permission grants"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DENIED = "denied"
    REVOKED = "revoked"


@dataclass
class PermissionGrant:
    """Individual permission grant"""
    grant_id: str
    user_id: str
    resource_id: str
    resource_type: ResourceType
    permission_level: PermissionLevel
    granted_by: str
    granted_at: datetime
    expires_at: Optional[datetime]
    device_restrictions: List[str]
    conditions: Dict[str, Any]
    justification: str
    status: PermissionStatus
    metadata: Dict[str, Any]


@dataclass
class Role:
    """Role-based permission template"""
    role_id: str
    name: str
    description: str
    permissions: List[Dict[str, Any]]
    inherits_from: List[str]
    restrictions: Dict[str, Any]
    created_by: str
    created_at: datetime
    is_system_role: bool


@dataclass
class User:
    """User with assigned roles and permissions"""
    user_id: str
    username: str
    email: str
    roles: List[str]
    direct_permissions: List[str]
    profile: Dict[str, Any]
    restrictions: Dict[str, Any]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


class PermissionManager:
    """Core permission management system with granular controls"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # In-memory caches
        self.permissions: Dict[str, PermissionGrant] = {}
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        
        # Security settings
        self.default_deny = True
        self.require_justification = True
        self.auto_expire_days = 90
        self.audit_enabled = True
        
        # Permission cache for performance
        self.permission_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("PermissionManager initialized with default deny stance")
    
    async def initialize_system(self):
        """Initialize the permission system with default roles"""
        try:
            # Create system roles
            await self._create_system_roles()
            
            # Create admin user if none exists
            if not self.users:
                await self._create_default_admin()
            
            # Load existing data
            await self.load_data()
            
            logger.info("Permission system initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing permission system: {e}")
            raise
    
    async def _create_system_roles(self):
        """Create default system roles"""
        system_roles = [
            {
                "role_id": "system_admin",
                "name": "System Administrator",
                "description": "Full system access with all permissions",
                "permissions": [
                    {"resource_type": "*", "permission_level": "owner", "conditions": {}}
                ],
                "inherits_from": [],
                "restrictions": {"requires_mfa": True, "session_timeout": 3600},
                "is_system_role": True
            },
            {
                "role_id": "user_admin", 
                "name": "User Administrator",
                "description": "Manage users and basic permissions",
                "permissions": [
                    {"resource_type": "user", "permission_level": "admin", "conditions": {}},
                    {"resource_type": "role", "permission_level": "write", "conditions": {}}
                ],
                "inherits_from": [],
                "restrictions": {"requires_approval": True},
                "is_system_role": True
            },
            {
                "role_id": "standard_user",
                "name": "Standard User",
                "description": "Basic user with limited permissions",
                "permissions": [
                    {"resource_type": "file", "permission_level": "read", "conditions": {"own_files_only": True}},
                    {"resource_type": "application", "permission_level": "read", "conditions": {"approved_apps_only": True}}
                ],
                "inherits_from": [],
                "restrictions": {"session_timeout": 7200},
                "is_system_role": True
            },
            {
                "role_id": "guest",
                "name": "Guest User", 
                "description": "Minimal access guest account",
                "permissions": [
                    {"resource_type": "application", "permission_level": "read", "conditions": {"public_apps_only": True}}
                ],
                "inherits_from": [],
                "restrictions": {"session_timeout": 1800, "requires_supervision": True},
                "is_system_role": True
            }
        ]
        
        for role_data in system_roles:
            role = Role(
                role_id=role_data["role_id"],
                name=role_data["name"],
                description=role_data["description"],
                permissions=role_data["permissions"],
                inherits_from=role_data["inherits_from"],
                restrictions=role_data["restrictions"],
                created_by="system",
                created_at=datetime.now(timezone.utc),
                is_system_role=role_data["is_system_role"]
            )
            self.roles[role.role_id] = role
    
    async def _create_default_admin(self):
        """Create default admin user"""
        admin_user = User(
            user_id="admin_001",
            username="admin",
            email="admin@activelog.local", 
            roles=["system_admin"],
            direct_permissions=[],
            profile={
                "full_name": "System Administrator",
                "department": "IT Security",
                "created_by": "system"
            },
            restrictions={
                "requires_mfa": True,
                "password_policy": "strong"
            },
            is_active=True,
            created_at=datetime.now(timezone.utc),
            last_login=None
        )
        self.users[admin_user.user_id] = admin_user
        logger.info("Created default admin user")
    
    async def check_permission(
        self, 
        user_id: str, 
        resource_id: str, 
        resource_type: ResourceType,
        permission_level: PermissionLevel,
        device_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Check if user has permission for resource
        Returns (is_allowed, reason)
        """
        try:
            # Check cache first
            cache_key = f"{user_id}:{resource_id}:{resource_type.value}:{permission_level.value}:{device_id}"
            cached_result = self._get_cached_permission(cache_key)
            if cached_result:
                return cached_result
            
            # Default deny stance
            if self.default_deny and not await self._has_explicit_permission(
                user_id, resource_id, resource_type, permission_level, device_id, context
            ):
                reason = "Access denied - no explicit permission granted (default deny policy)"
                self._cache_permission(cache_key, (False, reason))
                return False, reason
            
            # Check user exists and is active
            user = self.users.get(user_id)
            if not user or not user.is_active:
                reason = "Access denied - user not found or inactive"
                self._cache_permission(cache_key, (False, reason))
                return False, reason
            
            # Check device restrictions
            if device_id and not await self._check_device_permission(user_id, device_id):
                reason = f"Access denied - device {device_id} not authorized"
                self._cache_permission(cache_key, (False, reason))
                return False, reason
            
            # Check role-based permissions
            role_allowed, role_reason = await self._check_role_permissions(
                user, resource_id, resource_type, permission_level, context
            )
            
            if role_allowed:
                self._cache_permission(cache_key, (True, "Access granted via role permissions"))
                return True, "Access granted via role permissions"
            
            # Check direct permissions
            direct_allowed, direct_reason = await self._check_direct_permissions(
                user_id, resource_id, resource_type, permission_level, device_id, context
            )
            
            if direct_allowed:
                self._cache_permission(cache_key, (True, "Access granted via direct permission"))
                return True, "Access granted via direct permission"
            
            # Final denial
            reason = f"Access denied - {role_reason or direct_reason or 'insufficient permissions'}"
            self._cache_permission(cache_key, (False, reason))
            return False, reason
            
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False, f"Access denied - permission check failed: {str(e)}"
    
    async def _has_explicit_permission(
        self, 
        user_id: str, 
        resource_id: str,
        resource_type: ResourceType, 
        permission_level: PermissionLevel,
        device_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if user has explicit permission (not default allow)"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        # Check direct permissions
        for grant_id in user.direct_permissions:
            grant = self.permissions.get(grant_id)
            if (grant and 
                grant.resource_id == resource_id and 
                grant.resource_type == resource_type and
                grant.status == PermissionStatus.ACTIVE and
                await self._permission_level_sufficient(grant.permission_level, permission_level)):
                return True
        
        # Check role permissions
        for role_id in user.roles:
            role = self.roles.get(role_id)
            if role:
                for perm in role.permissions:
                    if (perm.get("resource_type") == resource_type.value or perm.get("resource_type") == "*"):
                        perm_level = PermissionLevel(perm.get("permission_level", "none"))
                        if await self._permission_level_sufficient(perm_level, permission_level):
                            return True
        
        return False
    
    async def _check_role_permissions(
        self,
        user: User,
        resource_id: str,
        resource_type: ResourceType,
        permission_level: PermissionLevel,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """Check permissions via user roles"""
        for role_id in user.roles:
            role = self.roles.get(role_id)
            if not role:
                continue
                
            # Check inherited roles first
            for inherited_role_id in role.inherits_from:
                inherited_user = User(
                    user_id=user.user_id,
                    username=user.username,
                    email=user.email,
                    roles=[inherited_role_id],
                    direct_permissions=[],
                    profile=user.profile,
                    restrictions=user.restrictions,
                    is_active=user.is_active,
                    created_at=user.created_at,
                    last_login=user.last_login
                )
                
                inherited_allowed, _ = await self._check_role_permissions(
                    inherited_user, resource_id, resource_type, permission_level, context
                )
                if inherited_allowed:
                    return True, f"Access granted via inherited role {inherited_role_id}"
            
            # Check role permissions
            for perm in role.permissions:
                if (perm.get("resource_type") == resource_type.value or 
                    perm.get("resource_type") == "*"):
                    
                    perm_level = PermissionLevel(perm.get("permission_level", "none"))
                    if await self._permission_level_sufficient(perm_level, permission_level):
                        
                        # Check conditions
                        conditions = perm.get("conditions", {})
                        if await self._check_conditions(conditions, user, resource_id, context):
                            return True, f"Access granted via role {role_id}"
        
        return False, "No role permissions match"
    
    async def _check_direct_permissions(
        self,
        user_id: str,
        resource_id: str, 
        resource_type: ResourceType,
        permission_level: PermissionLevel,
        device_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """Check direct user permissions"""
        user = self.users.get(user_id)
        if not user:
            return False, "User not found"
        
        for grant_id in user.direct_permissions:
            grant = self.permissions.get(grant_id)
            if not grant:
                continue
                
            # Check if grant matches request
            if (grant.resource_id == resource_id and
                grant.resource_type == resource_type and
                grant.status == PermissionStatus.ACTIVE):
                
                # Check permission level
                if await self._permission_level_sufficient(grant.permission_level, permission_level):
                    
                    # Check expiration
                    if grant.expires_at and grant.expires_at < datetime.now(timezone.utc):
                        await self._expire_permission(grant_id)
                        continue
                    
                    # Check device restrictions
                    if device_id and grant.device_restrictions:
                        if device_id not in grant.device_restrictions:
                            continue
                    
                    # Check conditions
                    if await self._check_conditions(grant.conditions, user, resource_id, context):
                        return True, f"Direct permission grant {grant_id}"
        
        return False, "No direct permissions match"
    
    async def _permission_level_sufficient(
        self,
        granted_level: PermissionLevel,
        required_level: PermissionLevel
    ) -> bool:
        """Check if granted permission level is sufficient for required level"""
        level_hierarchy = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.DELETE: 3,
            PermissionLevel.ADMIN: 4,
            PermissionLevel.OWNER: 5
        }
        
        return level_hierarchy[granted_level] >= level_hierarchy[required_level]
    
    async def _check_conditions(
        self,
        conditions: Dict[str, Any],
        user: User,
        resource_id: str,
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if permission conditions are met"""
        try:
            # Time-based conditions
            if "time_range" in conditions:
                time_range = conditions["time_range"]
                current_hour = datetime.now().hour
                if not (time_range["start"] <= current_hour <= time_range["end"]):
                    return False
            
            # IP address restrictions
            if "allowed_ips" in conditions and context:
                user_ip = context.get("ip_address")
                if user_ip and user_ip not in conditions["allowed_ips"]:
                    return False
            
            # Own files only condition
            if conditions.get("own_files_only") and context:
                file_owner = context.get("file_owner") 
                if file_owner != user.user_id:
                    return False
            
            # Approved apps only
            if conditions.get("approved_apps_only") and context:
                app_id = context.get("app_id")
                approved_apps = context.get("approved_apps", [])
                if app_id and app_id not in approved_apps:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking conditions: {e}")
            return False
    
    async def _check_device_permission(self, user_id: str, device_id: str) -> bool:
        """Check if user has permission to access from specific device"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        # Check user restrictions
        device_restrictions = user.restrictions.get("allowed_devices", [])
        if device_restrictions and device_id not in device_restrictions:
            return False
        
        # Check for device-specific permissions
        for grant_id in user.direct_permissions:
            grant = self.permissions.get(grant_id)
            if (grant and 
                grant.status == PermissionStatus.ACTIVE and
                grant.device_restrictions and 
                device_id in grant.device_restrictions):
                return True
        
        # If no device restrictions, allow
        return not device_restrictions
    
    def _get_cached_permission(self, cache_key: str) -> Optional[Tuple[bool, str]]:
        """Get cached permission result"""
        cache_entry = self.permission_cache.get(cache_key)
        if cache_entry:
            if cache_entry["expires_at"] > datetime.now():
                return cache_entry["result"]
            else:
                del self.permission_cache[cache_key]
        return None
    
    def _cache_permission(self, cache_key: str, result: Tuple[bool, str]):
        """Cache permission result"""
        self.permission_cache[cache_key] = {
            "result": result,
            "expires_at": datetime.now() + timedelta(seconds=self.cache_ttl)
        }
    
    async def _expire_permission(self, grant_id: str):
        """Mark permission as expired"""
        grant = self.permissions.get(grant_id)
        if grant:
            grant.status = PermissionStatus.EXPIRED
            logger.info(f"Permission {grant_id} expired")
    
    async def grant_permission(
        self,
        user_id: str,
        resource_id: str,
        resource_type: ResourceType,
        permission_level: PermissionLevel,
        granted_by: str,
        justification: str,
        expires_in_days: Optional[int] = None,
        device_restrictions: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> str:
        """Grant permission to user"""
        try:
            if self.require_justification and not justification:
                raise ValueError("Justification required for permission grant")
            
            grant_id = f"perm_{uuid.uuid4().hex[:12]}"
            expires_at = None
            
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            elif self.auto_expire_days > 0:
                expires_at = datetime.now(timezone.utc) + timedelta(days=self.auto_expire_days)
            
            grant = PermissionGrant(
                grant_id=grant_id,
                user_id=user_id,
                resource_id=resource_id,
                resource_type=resource_type,
                permission_level=permission_level,
                granted_by=granted_by,
                granted_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                device_restrictions=device_restrictions or [],
                conditions=conditions or {},
                justification=justification,
                status=PermissionStatus.ACTIVE,
                metadata={}
            )
            
            self.permissions[grant_id] = grant
            
            # Add to user's direct permissions
            user = self.users.get(user_id)
            if user:
                user.direct_permissions.append(grant_id)
            
            # Clear cache
            self._clear_user_cache(user_id)
            
            logger.info(f"Granted permission {grant_id} to user {user_id}")
            return grant_id
            
        except Exception as e:
            logger.error(f"Error granting permission: {e}")
            raise
    
    async def revoke_permission(self, grant_id: str, revoked_by: str, reason: str):
        """Revoke a permission grant"""
        try:
            grant = self.permissions.get(grant_id)
            if not grant:
                raise ValueError(f"Permission grant {grant_id} not found")
            
            grant.status = PermissionStatus.REVOKED
            grant.metadata["revoked_by"] = revoked_by
            grant.metadata["revoked_at"] = datetime.now(timezone.utc).isoformat()
            grant.metadata["revocation_reason"] = reason
            
            # Remove from user's direct permissions
            user = self.users.get(grant.user_id)
            if user and grant_id in user.direct_permissions:
                user.direct_permissions.remove(grant_id)
            
            # Clear cache
            self._clear_user_cache(grant.user_id)
            
            logger.info(f"Revoked permission {grant_id}")
            
        except Exception as e:
            logger.error(f"Error revoking permission: {e}")
            raise
    
    def _clear_user_cache(self, user_id: str):
        """Clear cached permissions for user"""
        keys_to_remove = [k for k in self.permission_cache.keys() if k.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self.permission_cache[key]
    
    async def load_data(self):
        """Load permissions data from disk"""
        try:
            # Load permissions
            perm_file = self.data_dir / "permissions.json"
            if perm_file.exists():
                with open(perm_file, 'r') as f:
                    data = json.load(f)
                    for grant_data in data:
                        grant = PermissionGrant(**grant_data)
                        self.permissions[grant.grant_id] = grant
            
            # Load roles
            roles_file = self.data_dir / "roles.json" 
            if roles_file.exists():
                with open(roles_file, 'r') as f:
                    data = json.load(f)
                    for role_data in data:
                        role = Role(**role_data)
                        self.roles[role.role_id] = role
            
            # Load users
            users_file = self.data_dir / "users.json"
            if users_file.exists():
                with open(users_file, 'r') as f:
                    data = json.load(f)
                    for user_data in data:
                        user = User(**user_data)
                        self.users[user.user_id] = user
            
            logger.info("Loaded permissions data from disk")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    async def save_data(self):
        """Save permissions data to disk"""
        try:
            # Save permissions
            perm_file = self.data_dir / "permissions.json"
            with open(perm_file, 'w') as f:
                data = [asdict(grant) for grant in self.permissions.values()]
                json.dump(data, f, indent=2, default=str)
            
            # Save roles
            roles_file = self.data_dir / "roles.json"
            with open(roles_file, 'w') as f:
                data = [asdict(role) for role in self.roles.values()]
                json.dump(data, f, indent=2, default=str)
            
            # Save users
            users_file = self.data_dir / "users.json"
            with open(users_file, 'w') as f:
                data = [asdict(user) for user in self.users.values()]
                json.dump(data, f, indent=2, default=str)
            
            logger.info("Saved permissions data to disk")
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")