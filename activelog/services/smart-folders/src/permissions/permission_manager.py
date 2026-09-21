"""Permission management for folder sharing"""

import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple

from ..core.database import db_manager

logger = logging.getLogger(__name__)

class PermissionType(Enum):
    READ = "read"
    WRITE = "write" 
    DELETE = "delete"
    ADMIN = "admin"
    SHARE = "share"  # Can share folder with others

class ShareType(Enum):
    PUBLIC_LINK = "public_link"
    DIRECT_USER = "direct_user"
    GROUP = "group"
    ORGANIZATION = "organization"

class FolderShare:
    """Represents a folder share with permissions and metadata"""
    
    def __init__(self, share_id: str, folder_id: str, owner_id: str, 
                 share_type: ShareType, permissions: Set[PermissionType],
                 config: Dict[str, Any] = None):
        self.share_id = share_id
        self.folder_id = folder_id
        self.owner_id = owner_id
        self.share_type = share_type
        self.permissions = permissions
        self.config = config or {}
        self.created_at = datetime.utcnow()
        self.expires_at = None
        self.is_active = True
        self.access_count = 0
        self.last_accessed = None
        
        # Set expiration if configured
        if "expires_hours" in self.config:
            self.expires_at = self.created_at + timedelta(hours=self.config["expires_hours"])
    
    def is_expired(self) -> bool:
        """Check if share is expired"""
        return self.expires_at is not None and datetime.utcnow() > self.expires_at
    
    def record_access(self, user_id: str = None):
        """Record access to this share"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        if user_id:
            self.config.setdefault("accessed_by", set()).add(user_id)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "share_id": self.share_id,
            "folder_id": self.folder_id,
            "owner_id": self.owner_id,
            "share_type": self.share_type.value,
            "permissions": [p.value for p in self.permissions],
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }

class PermissionManager:
    """Comprehensive permission manager for folder sharing"""
    
    def __init__(self):
        self.permissions: Dict[str, Dict[str, Set[PermissionType]]] = {}  # folder_id -> user_id -> permissions
        self.shares: Dict[str, FolderShare] = {}  # share_id -> FolderShare
        self.folder_shares: Dict[str, Set[str]] = {}  # folder_id -> set of share_ids
        self.user_shares: Dict[str, Set[str]] = {}  # user_id -> set of share_ids (as recipient)
        
        self.stats = {
            "permissions_granted": 0,
            "permissions_revoked": 0,
            "permission_checks": 0,
            "shares_created": 0,
            "shares_accessed": 0,
            "shares_expired": 0
        }
    
    async def initialize(self):
        """Initialize permission manager"""
        
        # Load existing permissions and shares from database
        await self._load_permissions()
        await self._load_shares()
        
        logger.info(f"Permission manager initialized with {len(self.permissions)} folder permissions and {len(self.shares)} shares")
    
    def grant_permission(self, folder_id: str, user_id: str, permission: PermissionType):
        """Grant permission to user for folder"""
        if folder_id not in self.permissions:
            self.permissions[folder_id] = {}
        
        if user_id not in self.permissions[folder_id]:
            self.permissions[folder_id][user_id] = set()
        
        self.permissions[folder_id][user_id].add(permission)
        self.stats["permissions_granted"] += 1
        
        logger.info(f"Granted {permission.value} permission to user {user_id} for folder {folder_id}")
    
    def revoke_permission(self, folder_id: str, user_id: str, permission: PermissionType) -> bool:
        """Revoke permission from user for folder"""
        if (folder_id in self.permissions and 
            user_id in self.permissions[folder_id] and
            permission in self.permissions[folder_id][user_id]):
            
            self.permissions[folder_id][user_id].remove(permission)
            self.stats["permissions_revoked"] += 1
            
            # Clean up empty permission sets
            if not self.permissions[folder_id][user_id]:
                del self.permissions[folder_id][user_id]
            
            if not self.permissions[folder_id]:
                del self.permissions[folder_id]
            
            logger.info(f"Revoked {permission.value} permission from user {user_id} for folder {folder_id}")
            return True
        
        return False
    
    def has_permission(self, folder_id: str, user_id: str, permission: PermissionType) -> bool:
        """Check if user has specific permission for folder"""
        self.stats["permission_checks"] += 1
        
        if folder_id not in self.permissions:
            return False
        
        if user_id not in self.permissions[folder_id]:
            return False
        
        # Admin permission grants all permissions
        user_permissions = self.permissions[folder_id][user_id]
        return permission in user_permissions or PermissionType.ADMIN in user_permissions
    
    def get_user_permissions(self, folder_id: str, user_id: str) -> Set[PermissionType]:
        """Get all permissions for user on folder"""
        if (folder_id in self.permissions and 
            user_id in self.permissions[folder_id]):
            return self.permissions[folder_id][user_id].copy()
        
        return set()
    
    def get_folder_permissions(self, folder_id: str) -> Dict[str, Set[PermissionType]]:
        """Get all permissions for folder"""
        if folder_id in self.permissions:
            return {
                user_id: perms.copy() 
                for user_id, perms in self.permissions[folder_id].items()
            }
        return {}
    
    async def _load_permissions(self):
        """Load permissions from database"""
        try:
            # This would load from a folder_permissions table
            # For now, we'll skip this as the database schema would need extension
            pass
        except Exception as e:
            logger.error(f"Error loading permissions: {e}")
    
    async def _load_shares(self):
        """Load shares from database"""
        try:
            # This would load from a folder_shares table
            # For now, we'll skip this as the database schema would need extension
            pass
        except Exception as e:
            logger.error(f"Error loading shares: {e}")
    
    async def create_folder_share(self, folder_id: str, owner_id: str, 
                                share_type: ShareType, permissions: List[str],
                                config: Dict[str, Any] = None) -> FolderShare:
        """Create a new folder share"""
        
        try:
            share_id = str(uuid.uuid4())
            permission_set = set()
            
            # Convert permission strings to PermissionType
            for perm_str in permissions:
                try:
                    permission_set.add(PermissionType(perm_str))
                except ValueError:
                    logger.warning(f"Invalid permission type: {perm_str}")
            
            if not permission_set:
                permission_set.add(PermissionType.READ)  # Default to read
            
            share = FolderShare(share_id, folder_id, owner_id, share_type, permission_set, config)
            
            # Store share
            self.shares[share_id] = share
            
            # Update indexes
            if folder_id not in self.folder_shares:
                self.folder_shares[folder_id] = set()
            self.folder_shares[folder_id].add(share_id)
            
            # If direct user share, add to user shares
            if share_type == ShareType.DIRECT_USER and "target_user_id" in config:
                target_user = config["target_user_id"]
                if target_user not in self.user_shares:
                    self.user_shares[target_user] = set()
                self.user_shares[target_user].add(share_id)
            
            # Save to database (would need implementation)
            # await self._save_share(share)
            
            self.stats["shares_created"] += 1
            
            logger.info(f"Created folder share {share_id} for folder {folder_id}")
            
            return share
            
        except Exception as e:
            logger.error(f"Error creating folder share: {e}")
            raise
    
    async def get_folder_share(self, share_id: str) -> Optional[FolderShare]:
        """Get folder share by ID"""
        
        share = self.shares.get(share_id)
        
        if share and share.is_expired():
            # Mark as expired and remove
            share.is_active = False
            self.stats["shares_expired"] += 1
            return None
        
        return share
    
    async def access_folder_share(self, share_id: str, user_id: str = None) -> Optional[FolderShare]:
        """Access folder share and record usage"""
        
        share = await self.get_folder_share(share_id)
        
        if share and share.is_active:
            share.record_access(user_id)
            self.stats["shares_accessed"] += 1
            
            # Update database access stats (would need implementation)
            # await self._update_share_access(share)
            
            return share
        
        return None
    
    async def revoke_folder_share(self, share_id: str, user_id: str) -> bool:
        """Revoke folder share (only owner or admin can revoke)"""
        
        try:
            share = self.shares.get(share_id)
            
            if not share:
                return False
            
            # Check if user can revoke (owner or has admin permission)
            if (user_id != share.owner_id and 
                not self.has_permission(share.folder_id, user_id, PermissionType.ADMIN)):
                return False
            
            # Deactivate share
            share.is_active = False
            
            # Remove from indexes
            if share.folder_id in self.folder_shares:
                self.folder_shares[share.folder_id].discard(share_id)
            
            # Remove from user shares if applicable
            if share.share_type == ShareType.DIRECT_USER and "target_user_id" in share.config:
                target_user = share.config["target_user_id"]
                if target_user in self.user_shares:
                    self.user_shares[target_user].discard(share_id)
            
            # Update database (would need implementation)
            # await self._deactivate_share(share_id)
            
            logger.info(f"Revoked folder share {share_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking folder share: {e}")
            return False
    
    def get_folder_shares(self, folder_id: str) -> List[FolderShare]:
        """Get all active shares for a folder"""
        
        share_ids = self.folder_shares.get(folder_id, set())
        shares = []
        
        for share_id in share_ids:
            share = self.shares.get(share_id)
            
            if share and share.is_active and not share.is_expired():
                shares.append(share)
            elif share and share.is_expired():
                # Clean up expired share
                share.is_active = False
                self.stats["shares_expired"] += 1
        
        return shares
    
    def get_user_shared_folders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all folders shared with a user"""
        
        shared_folders = []
        share_ids = self.user_shares.get(user_id, set())
        
        for share_id in share_ids:
            share = self.shares.get(share_id)
            
            if share and share.is_active and not share.is_expired():
                shared_folders.append({
                    "share_id": share_id,
                    "folder_id": share.folder_id,
                    "owner_id": share.owner_id,
                    "permissions": [p.value for p in share.permissions],
                    "shared_at": share.created_at.isoformat(),
                    "expires_at": share.expires_at.isoformat() if share.expires_at else None
                })
        
        return shared_folders
    
    def check_share_permission(self, share_id: str, user_id: str, 
                              permission: PermissionType) -> bool:
        """Check if user has specific permission through share"""
        
        share = self.shares.get(share_id)
        
        if not share or not share.is_active or share.is_expired():
            return False
        
        # Check if this share applies to the user
        if share.share_type == ShareType.DIRECT_USER:
            target_user = share.config.get("target_user_id")
            if target_user != user_id:
                return False
        elif share.share_type == ShareType.PUBLIC_LINK:
            # Public link allows anyone with the link
            pass
        
        # Check if share has the required permission
        return (permission in share.permissions or 
                PermissionType.ADMIN in share.permissions)
    
    def has_permission_via_share(self, folder_id: str, user_id: str, 
                                permission: PermissionType) -> Tuple[bool, Optional[str]]:
        """Check if user has permission via any share for folder"""
        
        share_ids = self.folder_shares.get(folder_id, set())
        
        for share_id in share_ids:
            if self.check_share_permission(share_id, user_id, permission):
                return True, share_id
        
        return False, None
    
    def has_permission_extended(self, folder_id: str, user_id: str, 
                              permission: PermissionType) -> Tuple[bool, str]:
        """Extended permission check including shares"""
        
        self.stats["permission_checks"] += 1
        
        # Check direct permissions first
        if self.has_permission(folder_id, user_id, permission):
            return True, "direct"
        
        # Check share-based permissions
        has_perm, share_id = self.has_permission_via_share(folder_id, user_id, permission)
        if has_perm:
            return True, f"share:{share_id}"
        
        return False, "none"
    
    async def cleanup_expired_shares(self) -> int:
        """Clean up expired shares"""
        
        expired_count = 0
        expired_share_ids = []
        
        for share_id, share in self.shares.items():
            if share.is_expired():
                share.is_active = False
                expired_share_ids.append(share_id)
                expired_count += 1
        
        # Clean up indexes
        for share_id in expired_share_ids:
            share = self.shares[share_id]
            
            # Remove from folder shares
            if share.folder_id in self.folder_shares:
                self.folder_shares[share.folder_id].discard(share_id)
            
            # Remove from user shares
            if share.share_type == ShareType.DIRECT_USER and "target_user_id" in share.config:
                target_user = share.config["target_user_id"]
                if target_user in self.user_shares:
                    self.user_shares[target_user].discard(share_id)
        
        # Update database (would need implementation)
        # await self._cleanup_expired_shares(expired_share_ids)
        
        self.stats["shares_expired"] += expired_count
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired shares")
        
        return expired_count
    
    def generate_public_share_url(self, share_id: str, base_url: str = "https://app.activelog.com") -> str:
        """Generate public share URL"""
        return f"{base_url}/shared/{share_id}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get permission manager statistics"""
        stats = self.stats.copy()
        
        # Add current counts
        stats.update({
            "total_folders_with_permissions": len(self.permissions),
            "total_permissions": sum(
                len(user_perms) 
                for folder_perms in self.permissions.values()
                for user_perms in folder_perms.values()
            ),
            "total_active_shares": sum(1 for share in self.shares.values() if share.is_active),
            "total_expired_shares": sum(1 for share in self.shares.values() if share.is_expired()),
            "shares_by_type": {},
            "shares_by_permissions": {}
        })
        
        # Analyze shares by type
        for share in self.shares.values():
            if share.is_active:
                share_type = share.share_type.value
                stats["shares_by_type"][share_type] = stats["shares_by_type"].get(share_type, 0) + 1
                
                # Count permission combinations
                perm_combo = ",".join(sorted([p.value for p in share.permissions]))
                stats["shares_by_permissions"][perm_combo] = stats["shares_by_permissions"].get(perm_combo, 0) + 1
        
        return stats