"""
Workspace management for collaborative teams
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4

from core.database import db_manager, workspaces, workspace_members, documents, activity_feed
from core.database import WorkspaceRole, ActivityType
from core.config import settings

logger = logging.getLogger(__name__)

class WorkspaceManager:
    def __init__(self):
        self.active_workspaces = {}  # Cache for active workspace data
        self.workspace_locks = {}    # Prevent concurrent modifications
        
    async def initialize(self):
        """Initialize workspace manager"""
        logger.info("Initializing workspace manager")
        await self._load_active_workspaces()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up workspace manager")
        self.active_workspaces.clear()
        self.workspace_locks.clear()
        
    async def _load_active_workspaces(self):
        """Load active workspaces into cache"""
        try:
            # Load workspaces with recent activity (last 30 days)
            query = f"""
                SELECT w.*, 
                       COUNT(wm.id) as member_count,
                       COUNT(d.id) as document_count
                FROM {workspaces.name} w
                LEFT JOIN {workspace_members.name} wm ON w.id = wm.workspace_id AND wm.is_active = true
                LEFT JOIN {documents.name} d ON w.id = d.workspace_id
                WHERE w.is_active = true 
                AND w.last_activity_at > NOW() - INTERVAL '30 days'
                GROUP BY w.id
                ORDER BY w.last_activity_at DESC
                LIMIT 1000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            for workspace in results:
                ws_dict = dict(workspace)
                self.active_workspaces[str(ws_dict["id"])] = ws_dict
                
            logger.info(f"Loaded {len(results)} active workspaces")
            
        except Exception as e:
            logger.error(f"Failed to load active workspaces: {e}")
            
    async def create_workspace(self, workspace_data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """Create a new workspace"""
        try:
            # Validate workspace data
            required_fields = ["name"]
            for field in required_fields:
                if field not in workspace_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Check if user has reached workspace limit
            user_workspaces_count = await self.get_user_workspaces_count(owner_id)
            if user_workspaces_count >= settings.MAX_WORKSPACES_PER_USER:
                raise ValueError(f"User has reached maximum workspace limit ({settings.MAX_WORKSPACES_PER_USER})")
            
            # Generate workspace ID
            workspace_id = str(uuid4())
            
            # Prepare workspace data
            ws_data = {
                "id": workspace_id,
                "name": workspace_data["name"],
                "description": workspace_data.get("description", ""),
                "owner_id": owner_id,
                "settings": workspace_data.get("settings", {}),
                "is_active": True,
                "last_activity_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Insert workspace into database
            workspace_query = workspaces.insert().values(**ws_data)
            await db_manager.database.execute(workspace_query)
            
            # Add owner as workspace member
            member_data = {
                "id": str(uuid4()),
                "workspace_id": workspace_id,
                "user_id": owner_id,
                "role": WorkspaceRole.OWNER,
                "invited_by": owner_id,
                "invited_at": datetime.now(timezone.utc),
                "joined_at": datetime.now(timezone.utc),
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            member_query = workspace_members.insert().values(**member_data)
            await db_manager.database.execute(member_query)
            
            # Add to cache
            ws_data["member_count"] = 1
            ws_data["document_count"] = 0
            self.active_workspaces[workspace_id] = ws_data
            
            # Log activity
            await self._log_workspace_activity(
                workspace_id=workspace_id,
                user_id=owner_id,
                activity_type=ActivityType.USER_JOINED,  # Using closest available
                details={"action": "workspace_created", "workspace_name": workspace_data["name"]}
            )
            
            logger.info(f"Created workspace {workspace_id} for user {owner_id}")
            return ws_data
            
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")
            raise
            
    async def update_workspace(self, workspace_id: str, updates: Dict[str, Any], 
                             user_id: str) -> Dict[str, Any]:
        """Update workspace information"""
        try:
            # Check if workspace exists and user has permission
            workspace = await self.get_workspace(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace {workspace_id} not found")
            
            # Check permissions (owner or admin)
            user_role = await self.get_user_role(workspace_id, user_id)
            if user_role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionError("Only workspace owner or admin can update workspace")
            
            # Acquire lock
            if workspace_id in self.workspace_locks:
                raise ValueError("Workspace is currently being modified")
                
            self.workspace_locks[workspace_id] = user_id
            
            try:
                # Prepare update data
                update_data = {
                    "updated_at": datetime.now(timezone.utc),
                    "last_activity_at": datetime.now(timezone.utc)
                }
                
                # Allow updates to specific fields
                allowed_fields = ["name", "description", "settings"]
                for field in allowed_fields:
                    if field in updates:
                        update_data[field] = updates[field]
                
                # Update in database
                query = (workspaces.update()
                        .where(workspaces.c.id == workspace_id)
                        .values(**update_data))
                await db_manager.database.execute(query)
                
                # Update cache
                if workspace_id in self.active_workspaces:
                    self.active_workspaces[workspace_id].update(update_data)
                
                # Get updated workspace
                updated_workspace = await self.get_workspace(workspace_id)
                
                # Log activity
                await self._log_workspace_activity(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    activity_type=ActivityType.USER_JOINED,  # Using closest available
                    details={"action": "workspace_updated", "updated_fields": list(updates.keys())}
                )
                
                logger.info(f"Updated workspace {workspace_id} by user {user_id}")
                return updated_workspace
                
            finally:
                # Release lock
                if workspace_id in self.workspace_locks:
                    del self.workspace_locks[workspace_id]
                    
        except Exception as e:
            logger.error(f"Failed to update workspace {workspace_id}: {e}")
            raise
            
    async def delete_workspace(self, workspace_id: str, user_id: str) -> bool:
        """Delete a workspace (soft delete)"""
        try:
            # Check if workspace exists and user has permission
            workspace = await self.get_workspace(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace {workspace_id} not found")
            
            # Only owner can delete workspace
            if workspace["owner_id"] != user_id:
                raise PermissionError("Only workspace owner can delete workspace")
            
            # Soft delete workspace
            update_data = {
                "is_active": False,
                "updated_at": datetime.now(timezone.utc)
            }
            
            query = (workspaces.update()
                    .where(workspaces.c.id == workspace_id)
                    .values(**update_data))
            await db_manager.database.execute(query)
            
            # Remove from cache
            if workspace_id in self.active_workspaces:
                del self.active_workspaces[workspace_id]
            
            # Log activity
            await self._log_workspace_activity(
                workspace_id=workspace_id,
                user_id=user_id,
                activity_type=ActivityType.USER_LEFT,  # Using closest available
                details={"action": "workspace_deleted", "workspace_name": workspace["name"]}
            )
            
            logger.info(f"Deleted workspace {workspace_id} by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete workspace {workspace_id}: {e}")
            raise
            
    async def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace by ID"""
        try:
            # Check cache first
            if workspace_id in self.active_workspaces:
                return self.active_workspaces[workspace_id]
            
            # Query database with member and document counts
            query = f"""
                SELECT w.*, 
                       COUNT(DISTINCT wm.id) as member_count,
                       COUNT(DISTINCT d.id) as document_count
                FROM {workspaces.name} w
                LEFT JOIN {workspace_members.name} wm ON w.id = wm.workspace_id AND wm.is_active = true
                LEFT JOIN {documents.name} d ON w.id = d.workspace_id
                WHERE w.id = :workspace_id AND w.is_active = true
                GROUP BY w.id
            """
            
            result = await db_manager.database.fetch_one(query, {"workspace_id": workspace_id})
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get workspace {workspace_id}: {e}")
            return None
            
    async def get_user_workspaces(self, user_id: str, limit: int = 50, 
                                offset: int = 0) -> List[Dict[str, Any]]:
        """Get workspaces where user is a member"""
        try:
            query = f"""
                SELECT w.*, wm.role, wm.joined_at,
                       COUNT(DISTINCT wm2.id) as member_count,
                       COUNT(DISTINCT d.id) as document_count
                FROM {workspaces.name} w
                JOIN {workspace_members.name} wm ON w.id = wm.workspace_id
                LEFT JOIN {workspace_members.name} wm2 ON w.id = wm2.workspace_id AND wm2.is_active = true
                LEFT JOIN {documents.name} d ON w.id = d.workspace_id
                WHERE wm.user_id = :user_id 
                AND wm.is_active = true 
                AND w.is_active = true
                GROUP BY w.id, wm.role, wm.joined_at
                ORDER BY w.last_activity_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            results = await db_manager.database.fetch_all(query, {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            })
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get workspaces for user {user_id}: {e}")
            return []
            
    async def get_user_workspaces_count(self, user_id: str) -> int:
        """Get count of workspaces where user is a member"""
        try:
            query = f"""
                SELECT COUNT(DISTINCT w.id)
                FROM {workspaces.name} w
                JOIN {workspace_members.name} wm ON w.id = wm.workspace_id
                WHERE wm.user_id = :user_id 
                AND wm.is_active = true 
                AND w.is_active = true
            """
            
            result = await db_manager.database.fetch_one(query, {"user_id": user_id})
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get workspace count for user {user_id}: {e}")
            return 0
            
    async def get_workspace_members(self, workspace_id: str, 
                                  limit: int = None) -> List[Dict[str, Any]]:
        """Get all members of a workspace"""
        try:
            query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.is_active == True)
            ).order_by(workspace_members.c.joined_at.asc())
            
            if limit:
                query = query.limit(limit)
                
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get members for workspace {workspace_id}: {e}")
            return []
            
    async def get_user_role(self, workspace_id: str, user_id: str) -> Optional[WorkspaceRole]:
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
            logger.error(f"Failed to get user role for {user_id} in workspace {workspace_id}: {e}")
            return None
            
    async def add_member(self, workspace_id: str, user_id: str, role: WorkspaceRole, 
                        invited_by: str) -> Dict[str, Any]:
        """Add a member to a workspace"""
        try:
            # Check if workspace exists
            workspace = await self.get_workspace(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace {workspace_id} not found")
            
            # Check if inviter has permission
            inviter_role = await self.get_user_role(workspace_id, invited_by)
            if inviter_role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionError("Only workspace owner or admin can add members")
            
            # Check if user is already a member
            existing_role = await self.get_user_role(workspace_id, user_id)
            if existing_role:
                raise ValueError(f"User {user_id} is already a member of workspace {workspace_id}")
            
            # Check workspace member limit
            current_members = await self.get_workspace_members(workspace_id)
            if len(current_members) >= settings.MAX_MEMBERS_PER_WORKSPACE:
                raise ValueError(f"Workspace has reached maximum member limit ({settings.MAX_MEMBERS_PER_WORKSPACE})")
            
            # Add member
            member_data = {
                "id": str(uuid4()),
                "workspace_id": workspace_id,
                "user_id": user_id,
                "role": role.value,
                "invited_by": invited_by,
                "invited_at": datetime.now(timezone.utc),
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            query = workspace_members.insert().values(**member_data)
            await db_manager.database.execute(query)
            
            # Update workspace activity
            await self._update_workspace_activity(workspace_id)
            
            # Update cache member count
            if workspace_id in self.active_workspaces:
                self.active_workspaces[workspace_id]["member_count"] = len(current_members) + 1
            
            # Log activity
            await self._log_workspace_activity(
                workspace_id=workspace_id,
                user_id=invited_by,
                activity_type=ActivityType.USER_JOINED,
                details={
                    "action": "member_added",
                    "new_member": user_id,
                    "role": role.value
                }
            )
            
            logger.info(f"Added member {user_id} to workspace {workspace_id} with role {role.value}")
            return member_data
            
        except Exception as e:
            logger.error(f"Failed to add member to workspace: {e}")
            raise
            
    async def remove_member(self, workspace_id: str, user_id: str, 
                          removed_by: str) -> bool:
        """Remove a member from a workspace"""
        try:
            # Check permissions
            remover_role = await self.get_user_role(workspace_id, removed_by)
            target_role = await self.get_user_role(workspace_id, user_id)
            
            if not target_role:
                raise ValueError(f"User {user_id} is not a member of workspace {workspace_id}")
            
            # Owners cannot be removed, and only owners can remove admins
            if target_role == WorkspaceRole.OWNER:
                raise ValueError("Workspace owner cannot be removed")
            
            if target_role == WorkspaceRole.ADMIN and remover_role != WorkspaceRole.OWNER:
                raise PermissionError("Only workspace owner can remove admins")
            
            if remover_role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN] and removed_by != user_id:
                raise PermissionError("Only workspace owner, admin, or the user themselves can remove membership")
            
            # Remove member (soft delete)
            update_data = {
                "is_active": False,
                "updated_at": datetime.now(timezone.utc)
            }
            
            query = (workspace_members.update()
                    .where(
                        (workspace_members.c.workspace_id == workspace_id) &
                        (workspace_members.c.user_id == user_id)
                    )
                    .values(**update_data))
            await db_manager.database.execute(query)
            
            # Update workspace activity
            await self._update_workspace_activity(workspace_id)
            
            # Update cache member count
            if workspace_id in self.active_workspaces:
                current_count = self.active_workspaces[workspace_id].get("member_count", 0)
                self.active_workspaces[workspace_id]["member_count"] = max(0, current_count - 1)
            
            # Log activity
            await self._log_workspace_activity(
                workspace_id=workspace_id,
                user_id=removed_by,
                activity_type=ActivityType.USER_LEFT,
                details={
                    "action": "member_removed",
                    "removed_member": user_id,
                    "role": target_role.value
                }
            )
            
            logger.info(f"Removed member {user_id} from workspace {workspace_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove member from workspace: {e}")
            raise
            
    async def update_member_role(self, workspace_id: str, user_id: str, 
                               new_role: WorkspaceRole, updated_by: str) -> Dict[str, Any]:
        """Update a member's role in a workspace"""
        try:
            # Check permissions
            updater_role = await self.get_user_role(workspace_id, updated_by)
            current_role = await self.get_user_role(workspace_id, user_id)
            
            if not current_role:
                raise ValueError(f"User {user_id} is not a member of workspace {workspace_id}")
            
            # Only owners can change roles, and owner role cannot be changed
            if updater_role != WorkspaceRole.OWNER:
                raise PermissionError("Only workspace owner can update member roles")
            
            if current_role == WorkspaceRole.OWNER or new_role == WorkspaceRole.OWNER:
                raise ValueError("Owner role cannot be changed")
            
            # Update role
            update_data = {
                "role": new_role.value,
                "updated_at": datetime.now(timezone.utc)
            }
            
            query = (workspace_members.update()
                    .where(
                        (workspace_members.c.workspace_id == workspace_id) &
                        (workspace_members.c.user_id == user_id) &
                        (workspace_members.c.is_active == True)
                    )
                    .values(**update_data))
            await db_manager.database.execute(query)
            
            # Get updated member info
            member_query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.user_id == user_id) &
                (workspace_members.c.is_active == True)
            )
            result = await db_manager.database.fetch_one(member_query)
            
            # Log activity
            await self._log_workspace_activity(
                workspace_id=workspace_id,
                user_id=updated_by,
                activity_type=ActivityType.USER_JOINED,  # Using closest available
                details={
                    "action": "role_updated",
                    "target_member": user_id,
                    "old_role": current_role.value,
                    "new_role": new_role.value
                }
            )
            
            logger.info(f"Updated role for {user_id} in workspace {workspace_id} from {current_role.value} to {new_role.value}")
            return dict(result)
            
        except Exception as e:
            logger.error(f"Failed to update member role: {e}")
            raise
            
    async def _update_workspace_activity(self, workspace_id: str):
        """Update workspace last activity timestamp"""
        try:
            query = (workspaces.update()
                    .where(workspaces.c.id == workspace_id)
                    .values(last_activity_at=datetime.now(timezone.utc)))
            await db_manager.database.execute(query)
            
            # Update cache
            if workspace_id in self.active_workspaces:
                self.active_workspaces[workspace_id]["last_activity_at"] = datetime.now(timezone.utc)
                
        except Exception as e:
            logger.warning(f"Failed to update workspace activity: {e}")
            
    async def _log_workspace_activity(self, workspace_id: str, user_id: str, 
                                    activity_type: ActivityType, 
                                    details: Dict[str, Any] = None):
        """Log workspace activity"""
        try:
            activity_data = {
                "workspace_id": workspace_id,
                "actor_id": user_id,
                "activity_type": activity_type.value,
                "target_type": "workspace",
                "details": details or {},
                "created_at": datetime.now(timezone.utc)
            }
            
            query = activity_feed.insert().values(**activity_data)
            await db_manager.database.execute(query)
            
        except Exception as e:
            logger.warning(f"Failed to log workspace activity: {e}")
            
    async def cleanup_inactive_workspaces(self):
        """Cleanup workspaces that have been inactive for too long"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.WORKSPACE_INACTIVITY_DAYS)
            
            # Find inactive workspaces
            query = f"""
                SELECT id, name, owner_id, last_activity_at
                FROM {workspaces.name}
                WHERE is_active = true 
                AND last_activity_at < :cutoff_date
                LIMIT 100
            """
            
            inactive_workspaces = await db_manager.database.fetch_all(query, {"cutoff_date": cutoff_date})
            
            for workspace in inactive_workspaces:
                workspace_id = str(workspace["id"])
                
                # Mark as inactive
                update_query = (workspaces.update()
                               .where(workspaces.c.id == workspace_id)
                               .values(is_active=False, updated_at=datetime.now(timezone.utc)))
                await db_manager.database.execute(update_query)
                
                # Remove from cache
                if workspace_id in self.active_workspaces:
                    del self.active_workspaces[workspace_id]
                
                logger.info(f"Marked inactive workspace {workspace_id} as inactive")
                
            return len(inactive_workspaces)
            
        except Exception as e:
            logger.error(f"Failed to cleanup inactive workspaces: {e}")
            return 0
            
    async def get_workspace_statistics(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace statistics"""
        try:
            # Basic stats
            query = f"""
                SELECT 
                    COUNT(DISTINCT wm.user_id) as total_members,
                    COUNT(DISTINCT d.id) as total_documents,
                    COUNT(DISTINCT a.id) as total_annotations,
                    COUNT(DISTINCT c.id) as total_comments,
                    COUNT(DISTINCT af.id) as total_activities
                FROM {workspaces.name} w
                LEFT JOIN {workspace_members.name} wm ON w.id = wm.workspace_id AND wm.is_active = true
                LEFT JOIN {documents.name} d ON w.id = d.workspace_id
                LEFT JOIN annotations a ON d.id = a.document_id
                LEFT JOIN comments c ON d.id = c.document_id AND c.is_deleted = false
                LEFT JOIN {activity_feed.name} af ON w.id = af.workspace_id
                WHERE w.id = :workspace_id
                GROUP BY w.id
            """
            
            result = await db_manager.database.fetch_one(query, {"workspace_id": workspace_id})
            stats = dict(result) if result else {}
            
            # Recent activity count (last 7 days)
            recent_activity_query = f"""
                SELECT COUNT(*) as recent_activities
                FROM {activity_feed.name}
                WHERE workspace_id = :workspace_id
                AND created_at > NOW() - INTERVAL '7 days'
            """
            
            recent_result = await db_manager.database.fetch_one(recent_activity_query, {"workspace_id": workspace_id})
            if recent_result:
                stats["recent_activities"] = recent_result[0]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get workspace statistics: {e}")
            return {}