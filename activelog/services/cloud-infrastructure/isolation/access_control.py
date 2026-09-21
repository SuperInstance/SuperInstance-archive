"""
Fine-Grained Access Control System
Provides role-based access control and permission management for cloud resources
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

from core.models import (
    User, UserTier, APIKey, current_timestamp, generate_id
)

class Permission(str, Enum):
    # Instance permissions
    INSTANCE_CREATE = "instance:create"
    INSTANCE_READ = "instance:read"
    INSTANCE_UPDATE = "instance:update"
    INSTANCE_DELETE = "instance:delete"
    INSTANCE_START = "instance:start"
    INSTANCE_STOP = "instance:stop"
    INSTANCE_REBOOT = "instance:reboot"
    
    # Billing permissions
    BILLING_READ = "billing:read"
    BILLING_ADMIN = "billing:admin"
    
    # Scaling permissions
    SCALING_READ = "scaling:read"
    SCALING_CONFIG = "scaling:config"
    SCALING_MANUAL = "scaling:manual"
    
    # Administrative permissions
    ADMIN_USER_MANAGE = "admin:user:manage"
    ADMIN_SYSTEM_CONFIG = "admin:system:config"
    ADMIN_METRICS_READ = "admin:metrics:read"
    ADMIN_AUDIT_READ = "admin:audit:read"
    
    # API permissions
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"

class Role(str, Enum):
    # User roles
    USER_BASIC = "user_basic"
    USER_PREMIUM = "user_premium"
    USER_ENTERPRISE = "user_enterprise"
    
    # Administrative roles
    ADMIN_SUPPORT = "admin_support"
    ADMIN_BILLING = "admin_billing"
    ADMIN_SYSTEM = "admin_system"
    ADMIN_SUPER = "admin_super"
    
    # Service roles
    SERVICE_PROVISIONER = "service_provisioner"
    SERVICE_BILLING = "service_billing"
    SERVICE_SCALER = "service_scaler"

@dataclass
class AccessPolicy:
    """Access policy definition"""
    policy_id: str
    name: str
    description: str
    permissions: List[Permission]
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=current_timestamp)
    active: bool = True

@dataclass
class AccessRequest:
    """Access request for audit logging"""
    request_id: str
    user_id: str
    resource_type: str
    resource_id: str
    action: str
    permissions_required: List[Permission]
    granted: bool
    reason: str
    timestamp: datetime = field(default_factory=current_timestamp)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AccessControlManager:
    """Comprehensive access control and permission management"""
    
    def __init__(self, config: Dict[str, Any], database_manager):
        self.config = config
        self.db = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Access control configuration
        self.rbac_enabled = self.config.get('isolation', {}).get('enable_rbac', True)
        
        # Permission cache for performance
        self.user_permissions_cache = {}
        self.policy_cache = {}
        
        # Audit logging
        self.audit_enabled = self.config.get('security', {}).get('enable_audit_logging', True)
        
        # Initialize default policies
        self.default_policies = self._create_default_policies()
    
    def _create_default_policies(self) -> Dict[Role, AccessPolicy]:
        """Create default access policies for different roles"""
        policies = {}
        
        # Basic user policy
        policies[Role.USER_BASIC] = AccessPolicy(
            policy_id="policy-user-basic",
            name="Basic User Policy",
            description="Basic permissions for standard users",
            permissions=[
                Permission.INSTANCE_CREATE,
                Permission.INSTANCE_READ,
                Permission.INSTANCE_START,
                Permission.INSTANCE_STOP,
                Permission.INSTANCE_REBOOT,
                Permission.BILLING_READ,
                Permission.SCALING_READ,
                Permission.API_READ
            ],
            conditions={
                "max_instances": 5,
                "allowed_instance_types": ["t3.nano", "t3.micro", "t3.small"],
                "resource_owner_only": True
            }
        )
        
        # Premium user policy
        policies[Role.USER_PREMIUM] = AccessPolicy(
            policy_id="policy-user-premium",
            name="Premium User Policy", 
            description="Enhanced permissions for premium users",
            permissions=[
                Permission.INSTANCE_CREATE,
                Permission.INSTANCE_READ,
                Permission.INSTANCE_UPDATE,
                Permission.INSTANCE_START,
                Permission.INSTANCE_STOP,
                Permission.INSTANCE_REBOOT,
                Permission.BILLING_READ,
                Permission.SCALING_READ,
                Permission.SCALING_CONFIG,
                Permission.API_READ,
                Permission.API_WRITE
            ],
            conditions={
                "max_instances": 15,
                "allowed_instance_types": ["t3.nano", "t3.micro", "t3.small", "t3.medium", "t3.large", "c5.large"],
                "resource_owner_only": True
            }
        )
        
        # Enterprise user policy
        policies[Role.USER_ENTERPRISE] = AccessPolicy(
            policy_id="policy-user-enterprise",
            name="Enterprise User Policy",
            description="Full permissions for enterprise users",
            permissions=[
                Permission.INSTANCE_CREATE,
                Permission.INSTANCE_READ,
                Permission.INSTANCE_UPDATE,
                Permission.INSTANCE_DELETE,
                Permission.INSTANCE_START,
                Permission.INSTANCE_STOP,
                Permission.INSTANCE_REBOOT,
                Permission.BILLING_READ,
                Permission.SCALING_READ,
                Permission.SCALING_CONFIG,
                Permission.SCALING_MANUAL,
                Permission.API_READ,
                Permission.API_WRITE
            ],
            conditions={
                "max_instances": 50,
                "allowed_instance_types": ["*"],  # All instance types
                "resource_owner_only": True
            }
        )
        
        # Support admin policy
        policies[Role.ADMIN_SUPPORT] = AccessPolicy(
            policy_id="policy-admin-support",
            name="Support Admin Policy",
            description="Support team permissions",
            permissions=[
                Permission.INSTANCE_READ,
                Permission.BILLING_READ,
                Permission.SCALING_READ,
                Permission.ADMIN_METRICS_READ,
                Permission.API_READ
            ],
            conditions={
                "resource_owner_only": False,  # Can view all users' resources
                "read_only": True
            }
        )
        
        # System admin policy
        policies[Role.ADMIN_SYSTEM] = AccessPolicy(
            policy_id="policy-admin-system",
            name="System Admin Policy",
            description="Full system administration permissions",
            permissions=[perm for perm in Permission],  # All permissions
            conditions={
                "resource_owner_only": False,
                "unrestricted": True
            }
        )
        
        # Service provisioner policy
        policies[Role.SERVICE_PROVISIONER] = AccessPolicy(
            policy_id="policy-service-provisioner",
            name="Service Provisioner Policy",
            description="Permissions for provisioning service",
            permissions=[
                Permission.INSTANCE_CREATE,
                Permission.INSTANCE_READ,
                Permission.INSTANCE_UPDATE,
                Permission.INSTANCE_DELETE,
                Permission.INSTANCE_START,
                Permission.INSTANCE_STOP
            ],
            conditions={
                "service_account": True,
                "resource_owner_only": False
            }
        )
        
        return policies
    
    async def check_permission(self, user_id: str, permission: Permission,
                             resource_type: str = None, resource_id: str = None,
                             context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Check if user has permission to perform an action"""
        try:
            # Get user permissions
            user_permissions = await self.get_user_permissions(user_id)
            
            # Check if permission is granted
            if permission not in user_permissions:
                reason = f"Permission {permission.value} not granted to user {user_id}"
                await self._log_access_attempt(
                    user_id, resource_type, resource_id, permission.value,
                    [permission], False, reason, context
                )
                return False, reason
            
            # Check conditional permissions
            user = await self.db.get_user(user_id)
            if not user:
                reason = f"User {user_id} not found"
                await self._log_access_attempt(
                    user_id, resource_type, resource_id, permission.value,
                    [permission], False, reason, context
                )
                return False, reason
            
            # Get user's policy for condition checking
            user_policy = await self.get_user_policy(user)
            
            # Check resource ownership if required
            if (user_policy.conditions.get("resource_owner_only", False) and
                resource_id and resource_type):
                
                owns_resource = await self._check_resource_ownership(
                    user_id, resource_type, resource_id
                )
                if not owns_resource:
                    reason = f"User {user_id} does not own {resource_type} {resource_id}"
                    await self._log_access_attempt(
                        user_id, resource_type, resource_id, permission.value,
                        [permission], False, reason, context
                    )
                    return False, reason
            
            # Check instance limits for creation
            if permission == Permission.INSTANCE_CREATE:
                limit_check, limit_reason = await self._check_instance_limits(user, context)
                if not limit_check:
                    await self._log_access_attempt(
                        user_id, resource_type, resource_id, permission.value,
                        [permission], False, limit_reason, context
                    )
                    return False, limit_reason
            
            # Permission granted
            await self._log_access_attempt(
                user_id, resource_type, resource_id, permission.value,
                [permission], True, "Permission granted", context
            )
            return True, "Permission granted"
            
        except Exception as e:
            self.logger.error(f"Error checking permission for user {user_id}: {e}")
            reason = f"Permission check failed: {e}"
            await self._log_access_attempt(
                user_id, resource_type, resource_id, permission.value,
                [permission], False, reason, context
            )
            return False, reason
    
    async def check_multiple_permissions(self, user_id: str, permissions: List[Permission],
                                       resource_type: str = None, resource_id: str = None,
                                       context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Check if user has multiple permissions (all must be granted)"""
        try:
            for permission in permissions:
                has_permission, reason = await self.check_permission(
                    user_id, permission, resource_type, resource_id, context
                )
                if not has_permission:
                    return False, reason
            
            return True, "All permissions granted"
            
        except Exception as e:
            self.logger.error(f"Error checking multiple permissions for user {user_id}: {e}")
            return False, f"Permission check failed: {e}"
    
    async def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user"""
        try:
            # Check cache first
            if user_id in self.user_permissions_cache:
                cache_entry = self.user_permissions_cache[user_id]
                if cache_entry['expires'] > current_timestamp():
                    return cache_entry['permissions']
            
            # Get user
            user = await self.db.get_user(user_id)
            if not user:
                return set()
            
            # Get user's policy
            policy = await self.get_user_policy(user)
            permissions = set(policy.permissions)
            
            # Cache permissions for 5 minutes
            self.user_permissions_cache[user_id] = {
                'permissions': permissions,
                'expires': current_timestamp() + timedelta(minutes=5)
            }
            
            return permissions
            
        except Exception as e:
            self.logger.error(f"Error getting user permissions for {user_id}: {e}")
            return set()
    
    async def get_user_policy(self, user: User) -> AccessPolicy:
        """Get access policy for a user based on their tier"""
        try:
            # Map user tier to role
            tier_role_mapping = {
                UserTier.FREE: Role.USER_BASIC,
                UserTier.BASIC: Role.USER_BASIC,
                UserTier.PREMIUM: Role.USER_PREMIUM,
                UserTier.ENTERPRISE: Role.USER_ENTERPRISE
            }
            
            role = tier_role_mapping.get(user.tier, Role.USER_BASIC)
            
            # Get policy from cache or default
            if role in self.policy_cache:
                return self.policy_cache[role]
            
            # Load from database or use default
            policy = await self.db.get_access_policy(role.value)
            if not policy:
                policy = self.default_policies.get(role)
            
            if policy:
                self.policy_cache[role] = policy
                return policy
            
            # Fallback to basic user policy
            return self.default_policies[Role.USER_BASIC]
            
        except Exception as e:
            self.logger.error(f"Error getting user policy: {e}")
            return self.default_policies[Role.USER_BASIC]
    
    async def _check_resource_ownership(self, user_id: str, resource_type: str,
                                      resource_id: str) -> bool:
        """Check if user owns a specific resource"""
        try:
            if resource_type == "instance":
                instance = await self.db.get_instance(resource_id)
                return instance and instance.user_id == user_id
            elif resource_type == "billing_record":
                record = await self.db.get_billing_record(resource_id)
                return record and record.user_id == user_id
            elif resource_type == "scaling_event":
                event = await self.db.get_scaling_event(resource_id)
                return event and event.user_id == user_id
            else:
                self.logger.warning(f"Unknown resource type for ownership check: {resource_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking resource ownership: {e}")
            return False
    
    async def _check_instance_limits(self, user: User, context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Check if user can create more instances"""
        try:
            # Get user's policy
            policy = await self.get_user_policy(user)
            
            # Check max instances limit
            max_instances = policy.conditions.get("max_instances", 5)
            current_instances = await self.db.count_user_instances(user.user_id)
            
            if current_instances >= max_instances:
                return False, f"Maximum instances limit reached ({current_instances}/{max_instances})"
            
            # Check allowed instance types
            allowed_types = policy.conditions.get("allowed_instance_types", [])
            if context and "instance_type" in context and allowed_types != ["*"]:
                requested_type = context["instance_type"]
                if requested_type not in allowed_types:
                    return False, f"Instance type {requested_type} not allowed"
            
            return True, "Instance limits check passed"
            
        except Exception as e:
            self.logger.error(f"Error checking instance limits: {e}")
            return False, f"Instance limits check failed: {e}"
    
    async def _log_access_attempt(self, user_id: str, resource_type: str, resource_id: str,
                                action: str, permissions_required: List[Permission],
                                granted: bool, reason: str, context: Dict[str, Any] = None):
        """Log access attempt for audit purposes"""
        if not self.audit_enabled:
            return
        
        try:
            access_request = AccessRequest(
                request_id=generate_id("access"),
                user_id=user_id,
                resource_type=resource_type or "unknown",
                resource_id=resource_id or "unknown",
                action=action,
                permissions_required=permissions_required,
                granted=granted,
                reason=reason,
                ip_address=context.get("ip_address") if context else None,
                user_agent=context.get("user_agent") if context else None
            )
            
            # Save to audit log
            await self.db.create_access_log(access_request)
            
            if not granted:
                self.logger.warning(
                    f"Access denied for user {user_id}: {action} on {resource_type} {resource_id} - {reason}"
                )
            
        except Exception as e:
            self.logger.error(f"Error logging access attempt: {e}")
    
    async def create_api_key(self, user_id: str, name: str, permissions: List[Permission],
                           expires_in_days: int = 30) -> APIKey:
        """Create API key with specific permissions"""
        try:
            # Validate user exists
            user = await self.db.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Validate permissions - user must have all requested permissions
            user_permissions = await self.get_user_permissions(user_id)
            for permission in permissions:
                if permission not in user_permissions:
                    raise ValueError(f"User does not have permission: {permission.value}")
            
            # Generate API key
            import secrets
            api_key_string = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(api_key_string.encode()).hexdigest()
            
            # Create API key record
            api_key = APIKey(
                key_id=generate_id("key"),
                user_id=user_id,
                key_hash=key_hash,
                name=name,
                permissions=[perm.value for perm in permissions],
                created_at=current_timestamp(),
                expires_at=current_timestamp() + timedelta(days=expires_in_days)
            )
            
            # Save to database
            await self.db.create_api_key(api_key)
            
            self.logger.info(f"Created API key '{name}' for user {user_id}")
            
            # Return API key with the actual key string (only time it's shown)
            api_key_dict = api_key.dict()
            api_key_dict['api_key'] = api_key_string
            
            return api_key_dict
            
        except Exception as e:
            self.logger.error(f"Error creating API key: {e}")
            raise
    
    async def validate_api_key(self, api_key_string: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return associated user and permissions"""
        try:
            # Hash the provided key
            key_hash = hashlib.sha256(api_key_string.encode()).hexdigest()
            
            # Look up API key
            api_key = await self.db.get_api_key_by_hash(key_hash)
            if not api_key:
                return None
            
            # Check if key is active and not expired
            if not api_key.active:
                return None
            
            if api_key.expires_at and api_key.expires_at < current_timestamp():
                return None
            
            # Update last used timestamp
            api_key.last_used_at = current_timestamp()
            await self.db.update_api_key(api_key)
            
            # Return user and permissions info
            return {
                'user_id': api_key.user_id,
                'key_id': api_key.key_id,
                'permissions': [Permission(perm) for perm in api_key.permissions],
                'name': api_key.name
            }
            
        except Exception as e:
            self.logger.error(f"Error validating API key: {e}")
            return None
    
    async def revoke_api_key(self, user_id: str, key_id: str) -> bool:
        """Revoke an API key"""
        try:
            api_key = await self.db.get_api_key(key_id)
            if not api_key or api_key.user_id != user_id:
                return False
            
            api_key.active = False
            await self.db.update_api_key(api_key)
            
            self.logger.info(f"Revoked API key {key_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error revoking API key: {e}")
            return False
    
    async def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all API keys for a user (without the actual keys)"""
        try:
            api_keys = await self.db.get_user_api_keys(user_id)
            
            return [
                {
                    'key_id': key.key_id,
                    'name': key.name,
                    'permissions': key.permissions,
                    'created_at': key.created_at.isoformat(),
                    'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                    'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
                    'active': key.active
                }
                for key in api_keys
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting user API keys: {e}")
            return []
    
    async def get_access_audit_log(self, user_id: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get access audit log"""
        try:
            start_time = current_timestamp() - timedelta(hours=hours)
            access_logs = await self.db.get_access_logs(user_id, start_time)
            
            return [
                {
                    'request_id': log.request_id,
                    'user_id': log.user_id,
                    'resource_type': log.resource_type,
                    'resource_id': log.resource_id,
                    'action': log.action,
                    'permissions_required': [perm.value for perm in log.permissions_required],
                    'granted': log.granted,
                    'reason': log.reason,
                    'timestamp': log.timestamp.isoformat(),
                    'ip_address': log.ip_address,
                    'user_agent': log.user_agent
                }
                for log in access_logs
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting access audit log: {e}")
            return []
    
    async def get_user_access_summary(self, user_id: str) -> Dict[str, Any]:
        """Get access control summary for a user"""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return {'error': 'User not found'}
            
            # Get user permissions
            permissions = await self.get_user_permissions(user_id)
            
            # Get user policy
            policy = await self.get_user_policy(user)
            
            # Get API keys
            api_keys = await self.get_user_api_keys(user_id)
            
            # Get recent access attempts
            recent_access = await self.get_access_audit_log(user_id, 24)
            
            return {
                'user_id': user_id,
                'user_tier': user.tier.value,
                'permissions_count': len(permissions),
                'permissions': [perm.value for perm in permissions],
                'policy': {
                    'policy_id': policy.policy_id,
                    'name': policy.name,
                    'conditions': policy.conditions
                },
                'api_keys_count': len(api_keys),
                'active_api_keys': len([key for key in api_keys if key['active']]),
                'recent_access_attempts': len(recent_access),
                'denied_attempts_24h': len([log for log in recent_access if not log['granted']]),
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user access summary: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    def clear_permission_cache(self, user_id: str = None):
        """Clear permission cache"""
        if user_id:
            if user_id in self.user_permissions_cache:
                del self.user_permissions_cache[user_id]
        else:
            self.user_permissions_cache.clear()
            self.policy_cache.clear()
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for access control manager"""
        try:
            # Test permission check
            test_passed = True
            error_message = None
            
            try:
                # Test basic permission check
                has_perm, reason = await self.check_permission(
                    "health-check-test", Permission.INSTANCE_READ
                )
                # Should fail gracefully for non-existent user
            except Exception as e:
                test_passed = False
                error_message = f"Permission check test failed: {e}"
            
            # Cache statistics
            cached_users = len(self.user_permissions_cache)
            cached_policies = len(self.policy_cache)
            
            return {
                'service': 'access_control_manager',
                'healthy': test_passed,
                'error': error_message,
                'rbac_enabled': self.rbac_enabled,
                'audit_enabled': self.audit_enabled,
                'cached_user_permissions': cached_users,
                'cached_policies': cached_policies,
                'default_policies_loaded': len(self.default_policies),
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Access control manager health check failed: {e}")
            return {
                'service': 'access_control_manager',
                'healthy': False,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }