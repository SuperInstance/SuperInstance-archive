"""
Team permissions and access control management
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4

from core.database import db_manager, document_permissions, workspace_members, documents, workspaces
from core.database import DocumentPermission, WorkspaceRole, ActivityType

logger = logging.getLogger(__name__)

class PermissionManager:
    def __init__(self):
        self.permission_cache = {}  # Cache for user permissions
        self.role_permissions = {
            WorkspaceRole.OWNER: {
                DocumentPermission.READ, DocumentPermission.WRITE, 
                DocumentPermission.COMMENT, DocumentPermission.ADMIN
            },
            WorkspaceRole.ADMIN: {
                DocumentPermission.READ, DocumentPermission.WRITE, 
                DocumentPermission.COMMENT, DocumentPermission.ADMIN
            },
            WorkspaceRole.MEMBER: {
                DocumentPermission.READ, DocumentPermission.WRITE, DocumentPermission.COMMENT
            },
            WorkspaceRole.VIEWER: {
                DocumentPermission.READ, DocumentPermission.COMMENT
            }
        }
        
    async def initialize(self):
        """Initialize permission manager"""
        logger.info("Initializing permission manager")
        await self._load_active_permissions()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up permission manager")
        self.permission_cache.clear()
        
    async def _load_active_permissions(self):
        """Load active permissions into cache"""
        try:
            # Load recent document permissions
            query = f"""
                SELECT dp.*, d.workspace_id, d.name as document_name
                FROM {document_permissions.name} dp
                JOIN {documents.name} d ON dp.document_id = d.id
                WHERE dp.is_active = true
                AND (dp.expires_at IS NULL OR dp.expires_at > NOW())
                ORDER BY dp.created_at DESC
                LIMIT 10000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            for permission in results:
                perm_dict = dict(permission)
                user_id = perm_dict["user_id"]
                document_id = str(perm_dict["document_id"])
                
                cache_key = f"{user_id}:{document_id}"
                self.permission_cache[cache_key] = perm_dict
                
            logger.info(f"Loaded {len(results)} active permissions")
            
        except Exception as e:
            logger.error(f"Failed to load active permissions: {e}")
            
    async def check_document_permission(self, user_id: str, document_id: str, 
                                      required_permission: DocumentPermission) -> bool:
        """Check if user has specific permission for a document"""
        try:
            # Get user's effective permissions for the document
            user_permissions = await self.get_user_document_permissions(user_id, document_id)
            
            # Check if user has the required permission
            return required_permission in user_permissions
            
        except Exception as e:
            logger.error(f"Failed to check document permission: {e}")
            return False
            
    async def get_user_document_permissions(self, user_id: str, document_id: str) -> Set[DocumentPermission]:
        """Get all permissions a user has for a document"""
        try:
            permissions = set()
            
            # Check cache first
            cache_key = f"{user_id}:{document_id}"
            if cache_key in self.permission_cache:
                cached_perm = self.permission_cache[cache_key]
                if (cached_perm["is_active"] and 
                    (not cached_perm["expires_at"] or cached_perm["expires_at"] > datetime.now(timezone.utc))):
                    permissions.add(DocumentPermission(cached_perm["permission"]))
            
            # Get document and workspace info
            doc_query = f"""
                SELECT d.*, w.owner_id as workspace_owner
                FROM {documents.name} d
                JOIN {workspaces.name} w ON d.workspace_id = w.id
                WHERE d.id = :document_id
            """
            doc_result = await db_manager.database.fetch_one(doc_query, {"document_id": document_id})
            
            if not doc_result:
                return permissions
                
            document = dict(doc_result)
            workspace_id = str(document["workspace_id"])
            
            # Document owner has all permissions
            if document["owner_id"] == user_id:
                return {DocumentPermission.READ, DocumentPermission.WRITE, 
                       DocumentPermission.COMMENT, DocumentPermission.ADMIN}
            
            # Workspace owner has all permissions
            if document["workspace_owner"] == user_id:
                return {DocumentPermission.READ, DocumentPermission.WRITE, 
                       DocumentPermission.COMMENT, DocumentPermission.ADMIN}
            
            # Get workspace role-based permissions
            workspace_role = await self.get_user_workspace_role(user_id, workspace_id)
            if workspace_role and workspace_role in self.role_permissions:
                permissions.update(self.role_permissions[workspace_role])
            
            # Get explicit document permissions
            explicit_permissions = await self.get_explicit_document_permissions(user_id, document_id)
            permissions.update(explicit_permissions)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get user document permissions: {e}")
            return set()
            
    async def get_explicit_document_permissions(self, user_id: str, document_id: str) -> Set[DocumentPermission]:
        """Get explicit document permissions for a user"""
        try:
            query = document_permissions.select().where(
                (document_permissions.c.document_id == document_id) &
                (document_permissions.c.user_id == user_id) &
                (document_permissions.c.is_active == True) &
                ((document_permissions.c.expires_at.is_(None)) |
                 (document_permissions.c.expires_at > datetime.now(timezone.utc)))
            )
            
            results = await db_manager.database.fetch_all(query)
            permissions = set()
            
            for result in results:
                permissions.add(DocumentPermission(result["permission"]))
                
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get explicit document permissions: {e}")
            return set()
            
    async def get_user_workspace_role(self, user_id: str, workspace_id: str) -> Optional[WorkspaceRole]:
        """Get user's role in a workspace"""
        try:
            query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.user_id == user_id) &
                (workspace_members.c.is_active == True)
            )
            
            result = await db_manager.database.fetch_one(query)
            
            if result:
                return WorkspaceRole(result["role"])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user workspace role: {e}")
            return None
            
    async def grant_document_permission(self, document_id: str, user_id: str, 
                                      permission: DocumentPermission, 
                                      granted_by: str,
                                      expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Grant explicit permission to a user for a document"""
        try:
            # Check if granter has admin permission
            granter_permissions = await self.get_user_document_permissions(granted_by, document_id)
            if DocumentPermission.ADMIN not in granter_permissions:
                raise PermissionError("Only users with admin permission can grant permissions")
            
            # Check if permission already exists
            existing_perms = await self.get_explicit_document_permissions(user_id, document_id)
            if permission in existing_perms:
                raise ValueError(f"User already has {permission.value} permission")
            
            # Create permission record
            permission_data = {
                "id": str(uuid4()),
                "document_id": document_id,
                "user_id": user_id,
                "permission": permission.value,
                "granted_by": granted_by,
                "granted_at": datetime.now(timezone.utc),
                "expires_at": expires_at,
                "is_active": True,
                "created_at": datetime.now(timezone.utc)
            }
            
            query = document_permissions.insert().values(**permission_data)
            await db_manager.database.execute(query)
            
            # Update cache
            cache_key = f"{user_id}:{document_id}"
            self.permission_cache[cache_key] = permission_data
            
            # Log activity
            await self._log_permission_activity(
                document_id=document_id,
                user_id=granted_by,
                activity_type="permission_granted",
                details={
                    "target_user": user_id,
                    "permission": permission.value,
                    "expires_at": expires_at.isoformat() if expires_at else None
                }
            )
            
            logger.info(f"Granted {permission.value} permission to {user_id} for document {document_id}")
            return permission_data
            
        except Exception as e:
            logger.error(f"Failed to grant document permission: {e}")
            raise
            
    async def revoke_document_permission(self, document_id: str, user_id: str, 
                                       permission: DocumentPermission, 
                                       revoked_by: str) -> bool:
        """Revoke explicit permission from a user for a document"""
        try:
            # Check if revoker has admin permission
            revoker_permissions = await self.get_user_document_permissions(revoked_by, document_id)
            if DocumentPermission.ADMIN not in revoker_permissions:
                raise PermissionError("Only users with admin permission can revoke permissions")
            
            # Revoke permission (soft delete)
            update_data = {
                "is_active": False,
                "metadata": {"revoked_by": revoked_by, "revoked_at": datetime.now(timezone.utc).isoformat()}
            }
            
            query = (document_permissions.update()
                    .where(
                        (document_permissions.c.document_id == document_id) &
                        (document_permissions.c.user_id == user_id) &
                        (document_permissions.c.permission == permission.value) &
                        (document_permissions.c.is_active == True)
                    )
                    .values(**update_data))
            
            result = await db_manager.database.execute(query)
            
            if not result:
                raise ValueError(f"No active {permission.value} permission found for user")
            
            # Remove from cache
            cache_key = f"{user_id}:{document_id}"
            if cache_key in self.permission_cache:
                del self.permission_cache[cache_key]
            
            # Log activity
            await self._log_permission_activity(
                document_id=document_id,
                user_id=revoked_by,
                activity_type="permission_revoked",
                details={
                    "target_user": user_id,
                    "permission": permission.value
                }
            )
            
            logger.info(f"Revoked {permission.value} permission from {user_id} for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke document permission: {e}")
            raise
            
    async def update_document_permission(self, document_id: str, user_id: str,
                                       old_permission: DocumentPermission,
                                       new_permission: DocumentPermission,
                                       updated_by: str,
                                       expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Update a user's permission for a document"""
        try:
            # Check if updater has admin permission
            updater_permissions = await self.get_user_document_permissions(updated_by, document_id)
            if DocumentPermission.ADMIN not in updater_permissions:
                raise PermissionError("Only users with admin permission can update permissions")
            
            # Update permission
            update_data = {
                "permission": new_permission.value,
                "expires_at": expires_at,
                "metadata": {"updated_by": updated_by, "updated_at": datetime.now(timezone.utc).isoformat()}
            }
            
            query = (document_permissions.update()
                    .where(
                        (document_permissions.c.document_id == document_id) &
                        (document_permissions.c.user_id == user_id) &
                        (document_permissions.c.permission == old_permission.value) &
                        (document_permissions.c.is_active == True)
                    )
                    .values(**update_data))
            
            result = await db_manager.database.execute(query)
            
            if not result:
                raise ValueError(f"No active {old_permission.value} permission found for user")
            
            # Update cache
            cache_key = f"{user_id}:{document_id}"
            if cache_key in self.permission_cache:
                self.permission_cache[cache_key].update(update_data)
            
            # Get updated permission
            perm_query = document_permissions.select().where(
                (document_permissions.c.document_id == document_id) &
                (document_permissions.c.user_id == user_id) &
                (document_permissions.c.permission == new_permission.value) &
                (document_permissions.c.is_active == True)
            )
            updated_result = await db_manager.database.fetch_one(perm_query)
            
            # Log activity
            await self._log_permission_activity(
                document_id=document_id,
                user_id=updated_by,
                activity_type="permission_updated",
                details={
                    "target_user": user_id,
                    "old_permission": old_permission.value,
                    "new_permission": new_permission.value,
                    "expires_at": expires_at.isoformat() if expires_at else None
                }
            )
            
            logger.info(f"Updated permission for {user_id} on document {document_id} from {old_permission.value} to {new_permission.value}")
            return dict(updated_result)
            
        except Exception as e:
            logger.error(f"Failed to update document permission: {e}")
            raise
            
    async def get_document_permissions(self, document_id: str, 
                                     include_inherited: bool = True) -> List[Dict[str, Any]]:
        """Get all permissions for a document"""
        try:
            permissions = []
            
            # Get explicit permissions
            explicit_query = document_permissions.select().where(
                (document_permissions.c.document_id == document_id) &
                (document_permissions.c.is_active == True) &
                ((document_permissions.c.expires_at.is_(None)) |
                 (document_permissions.c.expires_at > datetime.now(timezone.utc)))
            )
            
            explicit_results = await db_manager.database.fetch_all(explicit_query)
            
            for result in explicit_results:
                perm_dict = dict(result)
                perm_dict["permission_type"] = "explicit"
                permissions.append(perm_dict)
            
            # Get inherited permissions from workspace roles if requested
            if include_inherited:
                inherited_perms = await self._get_inherited_permissions(document_id)
                permissions.extend(inherited_perms)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get document permissions: {e}")
            return []
            
    async def _get_inherited_permissions(self, document_id: str) -> List[Dict[str, Any]]:
        """Get permissions inherited from workspace roles"""
        try:
            # Get document workspace
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                return []
                
            workspace_id = str(doc_result["workspace_id"])
            
            # Get workspace members and their roles
            members_query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.is_active == True)
            )
            
            members = await db_manager.database.fetch_all(members_query)
            inherited_permissions = []
            
            for member in members:
                member_dict = dict(member)
                user_id = member_dict["user_id"]
                role = WorkspaceRole(member_dict["role"])
                
                # Get permissions for this role
                role_permissions = self.role_permissions.get(role, set())
                
                for permission in role_permissions:
                    inherited_permissions.append({
                        "user_id": user_id,
                        "permission": permission.value,
                        "permission_type": "inherited",
                        "source": f"workspace_role:{role.value}",
                        "workspace_role": role.value,
                        "granted_at": member_dict["joined_at"],
                        "is_active": True
                    })
            
            return inherited_permissions
            
        except Exception as e:
            logger.error(f"Failed to get inherited permissions: {e}")
            return []
            
    async def get_user_accessible_documents(self, user_id: str, workspace_id: str,
                                          required_permission: DocumentPermission = DocumentPermission.READ,
                                          limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get documents user can access with specified permission"""
        try:
            # Get user's workspace role
            workspace_role = await self.get_user_workspace_role(user_id, workspace_id)
            
            # Base query for documents in workspace
            base_conditions = [f"d.workspace_id = '{workspace_id}'"]
            
            # Add permission-based conditions
            permission_conditions = []
            
            # Documents owned by user
            permission_conditions.append(f"d.owner_id = '{user_id}'")
            
            # Documents with role-based access
            if workspace_role and workspace_role in self.role_permissions:
                role_perms = self.role_permissions[workspace_role]
                if required_permission in role_perms:
                    permission_conditions.append("TRUE")  # Has access through role
            
            # Documents with explicit permissions
            permission_conditions.append(f"""
                EXISTS (
                    SELECT 1 FROM {document_permissions.name} dp
                    WHERE dp.document_id = d.id
                    AND dp.user_id = '{user_id}'
                    AND dp.permission = '{required_permission.value}'
                    AND dp.is_active = true
                    AND (dp.expires_at IS NULL OR dp.expires_at > NOW())
                )
            """)
            
            # Combine conditions
            where_clause = f"({' AND '.join(base_conditions)}) AND ({' OR '.join(permission_conditions)})"
            
            query = f"""
                SELECT d.*, 
                       COUNT(DISTINCT a.id) as annotation_count,
                       COUNT(DISTINCT c.id) as comment_count
                FROM {documents.name} d
                LEFT JOIN annotations a ON d.id = a.document_id
                LEFT JOIN comments c ON d.id = c.document_id AND c.is_deleted = false
                WHERE {where_clause}
                GROUP BY d.id
                ORDER BY d.updated_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            results = await db_manager.database.fetch_all(query, {
                "limit": limit,
                "offset": offset
            })
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get user accessible documents: {e}")
            return []
            
    async def bulk_grant_permissions(self, document_id: str, user_permissions: List[Dict[str, Any]],
                                   granted_by: str) -> List[Dict[str, Any]]:
        """Grant permissions to multiple users"""
        try:
            # Check if granter has admin permission
            granter_permissions = await self.get_user_document_permissions(granted_by, document_id)
            if DocumentPermission.ADMIN not in granter_permissions:
                raise PermissionError("Only users with admin permission can grant permissions")
            
            results = []
            
            for user_perm in user_permissions:
                try:
                    user_id = user_perm["user_id"]
                    permission = DocumentPermission(user_perm["permission"])
                    expires_at = user_perm.get("expires_at")
                    
                    if isinstance(expires_at, str):
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    
                    result = await self.grant_document_permission(
                        document_id, user_id, permission, granted_by, expires_at
                    )
                    
                    results.append({
                        "user_id": user_id,
                        "permission": permission.value,
                        "success": True,
                        "permission_data": result
                    })
                    
                except Exception as e:
                    results.append({
                        "user_id": user_perm.get("user_id", "unknown"),
                        "permission": user_perm.get("permission", "unknown"),
                        "success": False,
                        "error": str(e)
                    })
            
            logger.info(f"Bulk granted permissions for document {document_id} to {len(user_permissions)} users")
            return results
            
        except Exception as e:
            logger.error(f"Failed to bulk grant permissions: {e}")
            raise
            
    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired permissions"""
        try:
            # Deactivate expired permissions
            update_query = (document_permissions.update()
                           .where(
                               (document_permissions.c.expires_at <= datetime.now(timezone.utc)) &
                               (document_permissions.c.is_active == True)
                           )
                           .values(is_active=False))
            
            result = await db_manager.database.execute(update_query)
            
            # Clean up cache
            expired_keys = []
            for cache_key, perm_data in self.permission_cache.items():
                if (perm_data.get("expires_at") and 
                    perm_data["expires_at"] <= datetime.now(timezone.utc)):
                    expired_keys.append(cache_key)
                    
            for key in expired_keys:
                del self.permission_cache[key]
                
            logger.info(f"Cleaned up {result} expired permissions")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired permissions: {e}")
            return 0
            
    async def _log_permission_activity(self, document_id: str, user_id: str,
                                     activity_type: str, details: Dict[str, Any] = None):
        """Log permission-related activity"""
        try:
            # Get document workspace
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                return
                
            workspace_id = str(doc_result["workspace_id"])
            
            from core.database import activity_feed
            activity_data = {
                "workspace_id": workspace_id,
                "document_id": document_id,
                "actor_id": user_id,
                "activity_type": "permission_change",  # Custom activity type
                "target_type": "permission",
                "details": details or {},
                "metadata": {"action": activity_type},
                "created_at": datetime.now(timezone.utc)
            }
            
            query = activity_feed.insert().values(**activity_data)
            await db_manager.database.execute(query)
            
        except Exception as e:
            logger.warning(f"Failed to log permission activity: {e}")
            
    async def get_permission_audit_log(self, document_id: str, 
                                     days_back: int = 30) -> List[Dict[str, Any]]:
        """Get permission change audit log for a document"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            from core.database import activity_feed
            query = activity_feed.select().where(
                (activity_feed.c.document_id == document_id) &
                (activity_feed.c.activity_type == "permission_change") &
                (activity_feed.c.created_at >= start_date)
            ).order_by(activity_feed.c.created_at.desc())
            
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get permission audit log: {e}")
            return []
            
    async def get_permission_statistics(self, workspace_id: str) -> Dict[str, Any]:
        """Get permission statistics for a workspace"""
        try:
            query = f"""
                SELECT 
                    COUNT(DISTINCT dp.document_id) as documents_with_permissions,
                    COUNT(DISTINCT dp.user_id) as users_with_permissions,
                    COUNT(*) as total_permissions,
                    COUNT(CASE WHEN dp.permission = 'read' THEN 1 END) as read_permissions,
                    COUNT(CASE WHEN dp.permission = 'write' THEN 1 END) as write_permissions,
                    COUNT(CASE WHEN dp.permission = 'comment' THEN 1 END) as comment_permissions,
                    COUNT(CASE WHEN dp.permission = 'admin' THEN 1 END) as admin_permissions,
                    COUNT(CASE WHEN dp.expires_at IS NOT NULL THEN 1 END) as temporary_permissions
                FROM {document_permissions.name} dp
                JOIN {documents.name} d ON dp.document_id = d.id
                WHERE d.workspace_id = :workspace_id
                AND dp.is_active = true
            """
            
            result = await db_manager.database.fetch_one(query, {"workspace_id": workspace_id})
            return dict(result) if result else {}
            
        except Exception as e:
            logger.error(f"Failed to get permission statistics: {e}")
            return {}