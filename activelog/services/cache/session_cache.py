"""
Session and User Permission Caching
Handles user session management and permission caching in Redis
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
import jwt
import logging
from .redis_client import get_redis_client, RedisClient

logger = logging.getLogger(__name__)


class SessionCache:
    """Manages user sessions in Redis cache"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()
        self.session_ttl = 3600 * 24  # 24 hours
        self.refresh_token_ttl = 3600 * 24 * 30  # 30 days
        self.permission_ttl = 3600  # 1 hour
    
    def create_session(self, user_id: str, user_data: Dict[str, Any], 
                      permissions: List[str], device_info: Dict[str, Any] = None) -> Dict[str, str]:
        """Create new user session with tokens"""
        session_id = str(uuid.uuid4())
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        
        # Session data
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'created_at': datetime.utcnow().isoformat(),
            'last_accessed': datetime.utcnow().isoformat(),
            'device_info': device_info or {},
            'is_active': True,
            'permissions': permissions
        }
        
        # Store session by session_id
        self.redis.set('session', session_id, session_data, self.session_ttl)
        
        # Store session by access_token for quick lookup
        self.redis.set('session', f"token:{access_token}", {
            'session_id': session_id,
            'user_id': user_id
        }, self.session_ttl)
        
        # Store refresh token
        self.redis.set('session', f"refresh:{refresh_token}", {
            'session_id': session_id,
            'user_id': user_id
        }, self.refresh_token_ttl)
        
        # Add to user's active sessions
        self.redis.sadd('session', f"user_sessions:{user_id}", session_id)
        self.redis.expire('session', f"user_sessions:{user_id}", self.session_ttl)
        
        # Cache user data
        self.cache_user_data(user_id, user_data)
        
        # Cache permissions
        self.cache_user_permissions(user_id, permissions)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        
        return {
            'session_id': session_id,
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    
    def get_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get session data by access token"""
        # Get session reference from token
        token_data = self.redis.get('session', f"token:{access_token}")
        if not token_data:
            return None
        
        session_id = token_data.get('session_id')
        if not session_id:
            return None
        
        # Get full session data
        session_data = self.redis.get('session', session_id)
        if not session_data or not session_data.get('is_active'):
            return None
        
        # Update last accessed time
        session_data['last_accessed'] = datetime.utcnow().isoformat()
        self.redis.set('session', session_id, session_data, self.session_ttl)
        
        return session_data
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID"""
        return self.redis.get('session', session_id)
    
    def refresh_session(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Refresh session using refresh token"""
        # Get session reference from refresh token
        refresh_data = self.redis.get('session', f"refresh:{refresh_token}")
        if not refresh_data:
            return None
        
        session_id = refresh_data.get('session_id')
        user_id = refresh_data.get('user_id')
        
        if not session_id or not user_id:
            return None
        
        # Get session data
        session_data = self.redis.get('session', session_id)
        if not session_data or not session_data.get('is_active'):
            return None
        
        # Generate new access token
        new_access_token = str(uuid.uuid4())
        
        # Update session with new access token
        old_access_token = session_data.get('access_token')
        session_data['access_token'] = new_access_token
        session_data['last_accessed'] = datetime.utcnow().isoformat()
        
        # Store updated session
        self.redis.set('session', session_id, session_data, self.session_ttl)
        
        # Store new token mapping
        self.redis.set('session', f"token:{new_access_token}", {
            'session_id': session_id,
            'user_id': user_id
        }, self.session_ttl)
        
        # Remove old token mapping
        if old_access_token:
            self.redis.delete('session', f"token:{old_access_token}")
        
        logger.info(f"Refreshed session {session_id} for user {user_id}")
        
        return {
            'session_id': session_id,
            'access_token': new_access_token,
            'refresh_token': refresh_token
        }
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a specific session"""
        session_data = self.redis.get('session', session_id)
        if not session_data:
            return False
        
        user_id = session_data.get('user_id')
        access_token = session_data.get('access_token')
        refresh_token = session_data.get('refresh_token')
        
        # Mark session as inactive
        session_data['is_active'] = False
        session_data['invalidated_at'] = datetime.utcnow().isoformat()
        self.redis.set('session', session_id, session_data, 300)  # Keep for 5 minutes for logging
        
        # Remove token mappings
        if access_token:
            self.redis.delete('session', f"token:{access_token}")
        if refresh_token:
            self.redis.delete('session', f"refresh:{refresh_token}")
        
        # Remove from user's active sessions
        if user_id:
            self.redis.srem('session', f"user_sessions:{user_id}", session_id)
        
        logger.info(f"Invalidated session {session_id}")
        return True
    
    def invalidate_user_sessions(self, user_id: str, except_session_id: str = None) -> int:
        """Invalidate all sessions for a user"""
        session_ids = self.redis.smembers('session', f"user_sessions:{user_id}")
        invalidated_count = 0
        
        for session_id in session_ids:
            if except_session_id and session_id == except_session_id:
                continue
            
            if self.invalidate_session(session_id):
                invalidated_count += 1
        
        logger.info(f"Invalidated {invalidated_count} sessions for user {user_id}")
        return invalidated_count
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        session_ids = self.redis.smembers('session', f"user_sessions:{user_id}")
        sessions = []
        
        for session_id in session_ids:
            session_data = self.redis.get('session', session_id)
            if session_data and session_data.get('is_active'):
                # Remove sensitive data
                safe_session = {
                    'session_id': session_data.get('session_id'),
                    'created_at': session_data.get('created_at'),
                    'last_accessed': session_data.get('last_accessed'),
                    'device_info': session_data.get('device_info', {})
                }
                sessions.append(safe_session)
        
        return sessions
    
    def cache_user_data(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Cache user profile data"""
        # Remove sensitive fields
        safe_user_data = user_data.copy()
        safe_user_data.pop('password', None)
        safe_user_data.pop('password_hash', None)
        
        return self.redis.set('user', user_id, safe_user_data, 3600 * 2)  # 2 hours
    
    def get_cached_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user profile data"""
        return self.redis.get('user', user_id)
    
    def cache_user_permissions(self, user_id: str, permissions: List[str]) -> bool:
        """Cache user permissions"""
        permission_data = {
            'permissions': permissions,
            'cached_at': datetime.utcnow().isoformat()
        }
        return self.redis.set('permissions', user_id, permission_data, self.permission_ttl)
    
    def get_cached_user_permissions(self, user_id: str) -> Optional[List[str]]:
        """Get cached user permissions"""
        permission_data = self.redis.get('permissions', user_id)
        if permission_data:
            return permission_data.get('permissions', [])
        return None
    
    def invalidate_user_permissions(self, user_id: str) -> bool:
        """Invalidate cached user permissions"""
        return self.redis.delete('permissions', user_id)
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission"""
        permissions = self.get_cached_user_permissions(user_id)
        if permissions is None:
            return False
        
        return permission in permissions or 'admin' in permissions
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        # This is a simplified version - in production you'd want more efficient counting
        active_sessions = 0
        total_users_with_sessions = 0
        
        # Count active sessions (this could be expensive with many sessions)
        session_keys = self.redis.client.keys(f"{self.redis.prefixes['session']}*")
        
        for key in session_keys:
            if not key.startswith(f"{self.redis.prefixes['session']}token:") and \
               not key.startswith(f"{self.redis.prefixes['session']}refresh:") and \
               not key.startswith(f"{self.redis.prefixes['session']}user_sessions:"):
                session_data = self.redis.client.get(key)
                if session_data:
                    try:
                        data = json.loads(session_data)
                        if data.get('is_active'):
                            active_sessions += 1
                    except (json.JSONDecodeError, AttributeError):
                        pass
        
        # Count users with active sessions
        user_session_keys = self.redis.client.keys(f"{self.redis.prefixes['session']}user_sessions:*")
        total_users_with_sessions = len(user_session_keys)
        
        return {
            'active_sessions': active_sessions,
            'users_with_sessions': total_users_with_sessions,
            'session_ttl': self.session_ttl,
            'permission_ttl': self.permission_ttl
        }


class PermissionCache:
    """Advanced permission caching with role-based access control"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()
        self.role_ttl = 3600 * 12  # 12 hours
        self.permission_ttl = 3600  # 1 hour
    
    def cache_role_permissions(self, role: str, permissions: List[str]) -> bool:
        """Cache permissions for a role"""
        role_data = {
            'permissions': permissions,
            'cached_at': datetime.utcnow().isoformat()
        }
        return self.redis.set('permissions', f"role:{role}", role_data, self.role_ttl)
    
    def get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a role"""
        role_data = self.redis.get('permissions', f"role:{role}")
        if role_data:
            return role_data.get('permissions', [])
        return []
    
    def cache_user_roles(self, user_id: str, roles: List[str]) -> bool:
        """Cache user roles"""
        role_data = {
            'roles': roles,
            'cached_at': datetime.utcnow().isoformat()
        }
        return self.redis.set('permissions', f"user_roles:{user_id}", role_data, self.permission_ttl)
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get user roles"""
        role_data = self.redis.get('permissions', f"user_roles:{user_id}")
        if role_data:
            return role_data.get('roles', [])
        return []
    
    def get_user_permissions_from_roles(self, user_id: str) -> Set[str]:
        """Get all user permissions from their roles"""
        roles = self.get_user_roles(user_id)
        all_permissions = set()
        
        for role in roles:
            role_permissions = self.get_role_permissions(role)
            all_permissions.update(role_permissions)
        
        return all_permissions
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has permission (including through roles)"""
        # Check direct permissions first
        session_cache = SessionCache(self.redis)
        direct_permissions = session_cache.get_cached_user_permissions(user_id) or []
        
        if permission in direct_permissions or 'admin' in direct_permissions:
            return True
        
        # Check role-based permissions
        role_permissions = self.get_user_permissions_from_roles(user_id)
        return permission in role_permissions or 'admin' in role_permissions
    
    def invalidate_role_cache(self, role: str) -> bool:
        """Invalidate cached role permissions"""
        return self.redis.delete('permissions', f"role:{role}")
    
    def invalidate_user_roles(self, user_id: str) -> bool:
        """Invalidate cached user roles"""
        return self.redis.delete('permissions', f"user_roles:{user_id}")


# Global instances
session_cache = None
permission_cache = None


def get_session_cache() -> SessionCache:
    """Get global session cache instance"""
    global session_cache
    if session_cache is None:
        session_cache = SessionCache()
    return session_cache


def get_permission_cache() -> PermissionCache:
    """Get global permission cache instance"""
    global permission_cache
    if permission_cache is None:
        permission_cache = PermissionCache()
    return permission_cache