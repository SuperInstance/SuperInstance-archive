"""
Workspace membership and invitation management
"""

import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4

from core.database import db_manager, workspace_members, workspaces, notifications
from core.database import WorkspaceRole

logger = logging.getLogger(__name__)

class MembershipManager:
    def __init__(self):
        self.pending_invitations = {}  # Cache for pending invitations
        self.invitation_tokens = {}    # Cache for invitation tokens
        
    async def initialize(self):
        """Initialize membership manager"""
        logger.info("Initializing membership manager")
        await self._load_pending_invitations()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up membership manager")
        self.pending_invitations.clear()
        self.invitation_tokens.clear()
        
    async def _load_pending_invitations(self):
        """Load pending invitations into cache"""
        try:
            # Load pending invitations (not yet joined)
            query = f"""
                SELECT wm.*, w.name as workspace_name
                FROM {workspace_members.name} wm
                JOIN {workspaces.name} w ON wm.workspace_id = w.id
                WHERE wm.is_active = true 
                AND wm.joined_at IS NULL
                AND wm.invited_at > NOW() - INTERVAL '7 days'
                ORDER BY wm.invited_at DESC
                LIMIT 1000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            for invitation in results:
                inv_dict = dict(invitation)
                user_id = inv_dict["user_id"]
                
                if user_id not in self.pending_invitations:
                    self.pending_invitations[user_id] = []
                    
                self.pending_invitations[user_id].append(inv_dict)
                
            logger.info(f"Loaded {len(results)} pending invitations")
            
        except Exception as e:
            logger.error(f"Failed to load pending invitations: {e}")
            
    async def send_invitation(self, workspace_id: str, user_id: str, 
                            role: WorkspaceRole, invited_by: str,
                            invitation_message: str = "") -> Dict[str, Any]:
        """Send workspace invitation to a user"""
        try:
            # Check if workspace exists
            workspace_query = workspaces.select().where(workspaces.c.id == workspace_id)
            workspace_result = await db_manager.database.fetch_one(workspace_query)
            
            if not workspace_result:
                raise ValueError(f"Workspace {workspace_id} not found")
                
            workspace = dict(workspace_result)
            
            # Check if inviter has permission
            inviter_query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.user_id == invited_by) &
                (workspace_members.c.is_active == True)
            )
            inviter_result = await db_manager.database.fetch_one(inviter_query)
            
            if not inviter_result:
                raise PermissionError("User is not a member of the workspace")
                
            inviter_role = WorkspaceRole(inviter_result["role"])
            if inviter_role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionError("Only workspace owner or admin can send invitations")
            
            # Check if user is already a member or has pending invitation
            existing_query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.user_id == user_id) &
                (workspace_members.c.is_active == True)
            )
            existing_result = await db_manager.database.fetch_one(existing_query)
            
            if existing_result:
                if existing_result["joined_at"]:
                    raise ValueError(f"User {user_id} is already a member of workspace")
                else:
                    raise ValueError(f"User {user_id} already has a pending invitation")
            
            # Generate invitation token
            invitation_token = secrets.token_urlsafe(32)
            
            # Create invitation record
            invitation_data = {
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
            
            query = workspace_members.insert().values(**invitation_data)
            await db_manager.database.execute(query)
            
            # Cache invitation token
            self.invitation_tokens[invitation_token] = {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "role": role.value,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=7)
            }
            
            # Add to pending invitations cache
            if user_id not in self.pending_invitations:
                self.pending_invitations[user_id] = []
                
            invitation_data["workspace_name"] = workspace["name"]
            invitation_data["invitation_token"] = invitation_token
            self.pending_invitations[user_id].append(invitation_data)
            
            # Create notification
            notification_data = {
                "recipient_id": user_id,
                "workspace_id": workspace_id,
                "notification_type": "workspace_invitation",
                "title": f"Invitation to join {workspace['name']}",
                "message": f"{invited_by} invited you to join workspace '{workspace['name']}' as {role.value}." + 
                          (f" Message: {invitation_message}" if invitation_message else ""),
                "metadata": {
                    "invitation_token": invitation_token,
                    "workspace_name": workspace["name"],
                    "invited_by": invited_by,
                    "role": role.value
                },
                "created_at": datetime.now(timezone.utc)
            }
            
            notification_query = notifications.insert().values(**notification_data)
            await db_manager.database.execute(notification_query)
            
            logger.info(f"Sent workspace invitation to {user_id} for workspace {workspace_id}")
            return invitation_data
            
        except Exception as e:
            logger.error(f"Failed to send invitation: {e}")
            raise
            
    async def accept_invitation(self, invitation_token: str, user_id: str) -> Dict[str, Any]:
        """Accept a workspace invitation"""
        try:
            # Validate invitation token
            if invitation_token not in self.invitation_tokens:
                raise ValueError("Invalid or expired invitation token")
            
            token_data = self.invitation_tokens[invitation_token]
            
            # Check if token expired
            if datetime.now(timezone.utc) > token_data["expires_at"]:
                del self.invitation_tokens[invitation_token]
                raise ValueError("Invitation token has expired")
            
            # Verify user matches invitation
            if token_data["user_id"] != user_id:
                raise ValueError("Invitation token is not for this user")
            
            workspace_id = token_data["workspace_id"]
            role = WorkspaceRole(token_data["role"])
            
            # Update membership record
            update_data = {
                "joined_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            query = (workspace_members.update()
                    .where(
                        (workspace_members.c.workspace_id == workspace_id) &
                        (workspace_members.c.user_id == user_id) &
                        (workspace_members.c.is_active == True) &
                        (workspace_members.c.joined_at.is_(None))
                    )
                    .values(**update_data))
            
            result = await db_manager.database.execute(query)
            
            if not result:
                raise ValueError("No pending invitation found")
            
            # Remove from pending invitations cache
            if user_id in self.pending_invitations:
                self.pending_invitations[user_id] = [
                    inv for inv in self.pending_invitations[user_id]
                    if inv["workspace_id"] != workspace_id
                ]
                
            # Remove invitation token
            del self.invitation_tokens[invitation_token]
            
            # Get updated membership info
            member_query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.user_id == user_id) &
                (workspace_members.c.is_active == True)
            )
            member_result = await db_manager.database.fetch_one(member_query)
            
            logger.info(f"User {user_id} accepted invitation to workspace {workspace_id}")
            return dict(member_result)
            
        except Exception as e:
            logger.error(f"Failed to accept invitation: {e}")
            raise
            
    async def decline_invitation(self, invitation_token: str, user_id: str) -> bool:
        """Decline a workspace invitation"""
        try:
            # Validate invitation token
            if invitation_token not in self.invitation_tokens:
                raise ValueError("Invalid or expired invitation token")
            
            token_data = self.invitation_tokens[invitation_token]
            
            # Verify user matches invitation
            if token_data["user_id"] != user_id:
                raise ValueError("Invitation token is not for this user")
            
            workspace_id = token_data["workspace_id"]
            
            # Remove invitation record
            delete_query = workspace_members.delete().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.user_id == user_id) &
                (workspace_members.c.is_active == True) &
                (workspace_members.c.joined_at.is_(None))
            )
            await db_manager.database.execute(delete_query)
            
            # Remove from pending invitations cache
            if user_id in self.pending_invitations:
                self.pending_invitations[user_id] = [
                    inv for inv in self.pending_invitations[user_id]
                    if inv["workspace_id"] != workspace_id
                ]
                
            # Remove invitation token
            del self.invitation_tokens[invitation_token]
            
            logger.info(f"User {user_id} declined invitation to workspace {workspace_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to decline invitation: {e}")
            raise
            
    async def cancel_invitation(self, workspace_id: str, user_id: str, 
                              cancelled_by: str) -> bool:
        """Cancel a pending workspace invitation"""
        try:
            # Check if canceller has permission
            canceller_query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.user_id == cancelled_by) &
                (workspace_members.c.is_active == True)
            )
            canceller_result = await db_manager.database.fetch_one(canceller_query)
            
            if not canceller_result:
                raise PermissionError("User is not a member of the workspace")
                
            canceller_role = WorkspaceRole(canceller_result["role"])
            if canceller_role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionError("Only workspace owner or admin can cancel invitations")
            
            # Remove invitation record
            delete_query = workspace_members.delete().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.user_id == user_id) &
                (workspace_members.c.is_active == True) &
                (workspace_members.c.joined_at.is_(None))
            )
            result = await db_manager.database.execute(delete_query)
            
            if not result:
                raise ValueError("No pending invitation found")
            
            # Remove from pending invitations cache
            if user_id in self.pending_invitations:
                self.pending_invitations[user_id] = [
                    inv for inv in self.pending_invitations[user_id]
                    if inv["workspace_id"] != workspace_id
                ]
                
            # Remove any associated invitation tokens
            tokens_to_remove = []
            for token, token_data in self.invitation_tokens.items():
                if (token_data["workspace_id"] == workspace_id and 
                    token_data["user_id"] == user_id):
                    tokens_to_remove.append(token)
                    
            for token in tokens_to_remove:
                del self.invitation_tokens[token]
            
            logger.info(f"Cancelled invitation for {user_id} to workspace {workspace_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel invitation: {e}")
            raise
            
    async def get_user_invitations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending invitations for a user"""
        try:
            # Check cache first
            if user_id in self.pending_invitations:
                return self.pending_invitations[user_id]
            
            # Query database
            query = f"""
                SELECT wm.*, w.name as workspace_name, w.description as workspace_description
                FROM {workspace_members.name} wm
                JOIN {workspaces.name} w ON wm.workspace_id = w.id
                WHERE wm.user_id = :user_id 
                AND wm.is_active = true 
                AND wm.joined_at IS NULL
                AND w.is_active = true
                ORDER BY wm.invited_at DESC
            """
            
            results = await db_manager.database.fetch_all(query, {"user_id": user_id})
            invitations = [dict(row) for row in results]
            
            # Update cache
            self.pending_invitations[user_id] = invitations
            
            return invitations
            
        except Exception as e:
            logger.error(f"Failed to get invitations for user {user_id}: {e}")
            return []
            
    async def get_workspace_invitations(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all pending invitations for a workspace"""
        try:
            query = workspace_members.select().where(
                (workspace_members.c.workspace_id == workspace_id) &
                (workspace_members.c.is_active == True) &
                (workspace_members.c.joined_at.is_(None))
            ).order_by(workspace_members.c.invited_at.desc())
            
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get invitations for workspace {workspace_id}: {e}")
            return []
            
    async def bulk_invite_users(self, workspace_id: str, user_invitations: List[Dict[str, Any]], 
                              invited_by: str) -> List[Dict[str, Any]]:
        """Send invitations to multiple users"""
        try:
            results = []
            
            for invitation in user_invitations:
                try:
                    user_id = invitation["user_id"]
                    role = WorkspaceRole(invitation.get("role", WorkspaceRole.MEMBER))
                    message = invitation.get("message", "")
                    
                    result = await self.send_invitation(
                        workspace_id, user_id, role, invited_by, message
                    )
                    results.append({
                        "user_id": user_id,
                        "success": True,
                        "invitation": result
                    })
                    
                except Exception as e:
                    results.append({
                        "user_id": invitation.get("user_id", "unknown"),
                        "success": False,
                        "error": str(e)
                    })
                    
            logger.info(f"Bulk invited {len(user_invitations)} users to workspace {workspace_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to bulk invite users: {e}")
            raise
            
    async def cleanup_expired_invitations(self) -> int:
        """Clean up expired invitations"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Delete expired invitations
            delete_query = workspace_members.delete().where(
                (workspace_members.c.invited_at < cutoff_date) &
                (workspace_members.c.joined_at.is_(None))
            )
            
            result = await db_manager.database.execute(delete_query)
            
            # Clean up cached tokens
            expired_tokens = []
            for token, token_data in self.invitation_tokens.items():
                if datetime.now(timezone.utc) > token_data["expires_at"]:
                    expired_tokens.append(token)
                    
            for token in expired_tokens:
                del self.invitation_tokens[token]
            
            # Clean up pending invitations cache
            for user_id in list(self.pending_invitations.keys()):
                self.pending_invitations[user_id] = [
                    inv for inv in self.pending_invitations[user_id]
                    if inv["invited_at"] >= cutoff_date
                ]
                
                if not self.pending_invitations[user_id]:
                    del self.pending_invitations[user_id]
            
            logger.info(f"Cleaned up {result} expired invitations and {len(expired_tokens)} expired tokens")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired invitations: {e}")
            return 0
            
    async def get_invitation_statistics(self, workspace_id: str) -> Dict[str, Any]:
        """Get invitation statistics for a workspace"""
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_invitations,
                    COUNT(CASE WHEN joined_at IS NOT NULL THEN 1 END) as accepted_invitations,
                    COUNT(CASE WHEN joined_at IS NULL THEN 1 END) as pending_invitations,
                    AVG(EXTRACT(EPOCH FROM (joined_at - invited_at))/3600) as avg_acceptance_time_hours
                FROM {workspace_members.name}
                WHERE workspace_id = :workspace_id
            """
            
            result = await db_manager.database.fetch_one(query, {"workspace_id": workspace_id})
            stats = dict(result) if result else {}
            
            # Calculate acceptance rate
            if stats.get("total_invitations", 0) > 0:
                stats["acceptance_rate"] = (stats.get("accepted_invitations", 0) / 
                                          stats["total_invitations"]) * 100
            else:
                stats["acceptance_rate"] = 0
                
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get invitation statistics: {e}")
            return {}
            
    def generate_invitation_link(self, invitation_token: str, base_url: str = "") -> str:
        """Generate invitation link for sharing"""
        return f"{base_url}/invite/{invitation_token}"