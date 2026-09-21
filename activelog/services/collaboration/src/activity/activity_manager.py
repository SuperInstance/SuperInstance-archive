"""
Activity feed management and aggregation
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4

from core.database import db_manager, activity_feed, notifications, workspaces, documents
from core.database import ActivityType
from core.config import settings
from .timeline_builder import TimelineBuilder

logger = logging.getLogger(__name__)

class ActivityManager:
    def __init__(self):
        self.recent_activities = {}  # Cache for recent activities
        self.activity_subscriptions = {}  # User subscriptions to activities
        self.timeline_builder = TimelineBuilder()
        
    async def initialize(self):
        """Initialize activity manager"""
        logger.info("Initializing activity manager")
        await self.timeline_builder.initialize()
        await self._load_recent_activities()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up activity manager")
        self.recent_activities.clear()
        self.activity_subscriptions.clear()
        await self.timeline_builder.cleanup()
        
    async def _load_recent_activities(self):
        """Load recent activities into cache"""
        try:
            # Load activities from last 24 hours
            query = f"""
                SELECT af.*, w.name as workspace_name, d.name as document_name
                FROM {activity_feed.name} af
                LEFT JOIN {workspaces.name} w ON af.workspace_id = w.id
                LEFT JOIN {documents.name} d ON af.document_id = d.id
                WHERE af.created_at > NOW() - INTERVAL '24 hours'
                ORDER BY af.created_at DESC
                LIMIT 5000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            for activity in results:
                activity_dict = dict(activity)
                workspace_id = str(activity_dict["workspace_id"])
                
                if workspace_id not in self.recent_activities:
                    self.recent_activities[workspace_id] = []
                    
                self.recent_activities[workspace_id].append(activity_dict)
                
            logger.info(f"Loaded {len(results)} recent activities")
            
        except Exception as e:
            logger.error(f"Failed to load recent activities: {e}")
            
    async def log_activity(self, activity_data: Dict[str, Any]) -> str:
        """Log a new activity"""
        try:
            # Validate required fields
            required_fields = ["workspace_id", "actor_id", "activity_type"]
            for field in required_fields:
                if field not in activity_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate activity type
            try:
                activity_type = ActivityType(activity_data["activity_type"])
            except ValueError:
                raise ValueError(f"Invalid activity type: {activity_data['activity_type']}")
            
            # Generate activity ID
            activity_id = str(uuid4())
            
            # Prepare activity data
            act_data = {
                "id": activity_id,
                "workspace_id": activity_data["workspace_id"],
                "document_id": activity_data.get("document_id"),
                "actor_id": activity_data["actor_id"],
                "activity_type": activity_type.value,
                "target_id": activity_data.get("target_id"),
                "target_type": activity_data.get("target_type"),
                "details": activity_data.get("details", {}),
                "metadata": activity_data.get("metadata", {}),
                "created_at": datetime.now(timezone.utc)
            }
            
            # Insert into database
            query = activity_feed.insert().values(**act_data)
            await db_manager.database.execute(query)
            
            # Add to cache
            workspace_id = str(activity_data["workspace_id"])
            if workspace_id not in self.recent_activities:
                self.recent_activities[workspace_id] = []
                
            # Get additional info for cache
            act_data["workspace_name"] = await self._get_workspace_name(workspace_id)
            if activity_data.get("document_id"):
                act_data["document_name"] = await self._get_document_name(activity_data["document_id"])
                
            self.recent_activities[workspace_id].insert(0, act_data)
            
            # Keep cache size manageable
            if len(self.recent_activities[workspace_id]) > 1000:
                self.recent_activities[workspace_id] = self.recent_activities[workspace_id][:500]
            
            # Create notifications for relevant users
            await self._create_activity_notifications(act_data)
            
            # Update workspace last activity
            await self._update_workspace_activity(workspace_id)
            
            logger.debug(f"Logged activity {activity_id}: {activity_type.value}")
            return activity_id
            
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            raise
            
    async def get_workspace_activities(self, workspace_id: str, user_id: str,
                                     limit: int = 50, offset: int = 0,
                                     activity_types: Optional[List[str]] = None,
                                     start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get activities for a workspace"""
        try:
            # TODO: Check if user has access to workspace
            
            # Build query conditions
            conditions = [f"af.workspace_id = '{workspace_id}'"]
            params = {"workspace_id": workspace_id, "limit": limit, "offset": offset}
            
            if activity_types:
                type_conditions = [f"'{t}'" for t in activity_types if t in [at.value for at in ActivityType]]
                if type_conditions:
                    conditions.append(f"af.activity_type IN ({','.join(type_conditions)})")
            
            if start_date:
                conditions.append("af.created_at >= :start_date")
                params["start_date"] = start_date
                
            if end_date:
                conditions.append("af.created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions)
            
            # Query with user and resource names
            query = f"""
                SELECT af.*, 
                       w.name as workspace_name,
                       d.name as document_name
                FROM {activity_feed.name} af
                LEFT JOIN {workspaces.name} w ON af.workspace_id = w.id
                LEFT JOIN {documents.name} d ON af.document_id = d.id
                WHERE {where_clause}
                ORDER BY af.created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            results = await db_manager.database.fetch_all(query, params)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get workspace activities: {e}")
            return []
            
    async def get_document_activities(self, document_id: str, user_id: str,
                                    limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get activities for a specific document"""
        try:
            # TODO: Check if user has access to document
            
            query = f"""
                SELECT af.*, 
                       w.name as workspace_name,
                       d.name as document_name
                FROM {activity_feed.name} af
                LEFT JOIN {workspaces.name} w ON af.workspace_id = w.id
                LEFT JOIN {documents.name} d ON af.document_id = d.id
                WHERE af.document_id = :document_id
                ORDER BY af.created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            results = await db_manager.database.fetch_all(query, {
                "document_id": document_id,
                "limit": limit,
                "offset": offset
            })
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get document activities: {e}")
            return []
            
    async def get_user_activities(self, user_id: str, workspace_ids: Optional[List[str]] = None,
                                limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get activities across workspaces where user is a member"""
        try:
            # If no workspace_ids provided, get all workspaces where user is a member
            if not workspace_ids:
                workspace_query = f"""
                    SELECT DISTINCT workspace_id 
                    FROM workspace_members 
                    WHERE user_id = :user_id AND is_active = true
                """
                workspace_results = await db_manager.database.fetch_all(workspace_query, {"user_id": user_id})
                workspace_ids = [str(row[0]) for row in workspace_results]
            
            if not workspace_ids:
                return []
            
            # Build workspace condition
            workspace_conditions = [f"'{ws_id}'" for ws_id in workspace_ids]
            workspace_clause = f"af.workspace_id IN ({','.join(workspace_conditions)})"
            
            query = f"""
                SELECT af.*, 
                       w.name as workspace_name,
                       d.name as document_name
                FROM {activity_feed.name} af
                LEFT JOIN {workspaces.name} w ON af.workspace_id = w.id
                LEFT JOIN {documents.name} d ON af.document_id = d.id
                WHERE {workspace_clause}
                ORDER BY af.created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            results = await db_manager.database.fetch_all(query, {
                "limit": limit,
                "offset": offset
            })
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get user activities: {e}")
            return []
            
    async def get_activity_timeline(self, workspace_id: str, user_id: str,
                                  days_back: int = 7) -> Dict[str, Any]:
        """Get structured activity timeline"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            activities = await self.get_workspace_activities(
                workspace_id=workspace_id,
                user_id=user_id,
                limit=1000,
                start_date=start_date
            )
            
            timeline = await self.timeline_builder.build_timeline(activities, days_back)
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to get activity timeline: {e}")
            return {}
            
    async def subscribe_to_activities(self, user_id: str, workspace_id: str,
                                    activity_types: Optional[List[str]] = None):
        """Subscribe user to activity notifications"""
        try:
            if user_id not in self.activity_subscriptions:
                self.activity_subscriptions[user_id] = {}
                
            self.activity_subscriptions[user_id][workspace_id] = {
                "activity_types": activity_types or [t.value for t in ActivityType],
                "subscribed_at": datetime.now(timezone.utc)
            }
            
            logger.info(f"User {user_id} subscribed to activities in workspace {workspace_id}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to activities: {e}")
            
    async def unsubscribe_from_activities(self, user_id: str, workspace_id: str):
        """Unsubscribe user from activity notifications"""
        try:
            if (user_id in self.activity_subscriptions and 
                workspace_id in self.activity_subscriptions[user_id]):
                
                del self.activity_subscriptions[user_id][workspace_id]
                
                if not self.activity_subscriptions[user_id]:
                    del self.activity_subscriptions[user_id]
                    
                logger.info(f"User {user_id} unsubscribed from activities in workspace {workspace_id}")
                
        except Exception as e:
            logger.error(f"Failed to unsubscribe from activities: {e}")
            
    async def get_activity_summary(self, workspace_id: str, days_back: int = 7) -> Dict[str, Any]:
        """Get activity summary for a workspace"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            query = f"""
                SELECT 
                    activity_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT actor_id) as unique_actors,
                    COUNT(DISTINCT document_id) as documents_affected,
                    MIN(created_at) as first_activity,
                    MAX(created_at) as latest_activity
                FROM {activity_feed.name}
                WHERE workspace_id = :workspace_id
                AND created_at >= :start_date
                GROUP BY activity_type
                ORDER BY count DESC
            """
            
            results = await db_manager.database.fetch_all(query, {
                "workspace_id": workspace_id,
                "start_date": start_date
            })
            
            summary = {
                "period_days": days_back,
                "start_date": start_date.isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat(),
                "activity_types": [dict(row) for row in results],
                "total_activities": sum(row["count"] for row in results),
                "total_unique_actors": len(set(row["unique_actors"] for row in results if row["unique_actors"])),
                "total_documents_affected": len(set(row["documents_affected"] for row in results if row["documents_affected"]))
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get activity summary: {e}")
            return {}
            
    async def get_most_active_users(self, workspace_id: str, days_back: int = 7,
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """Get most active users in a workspace"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            query = f"""
                SELECT 
                    actor_id,
                    COUNT(*) as activity_count,
                    COUNT(DISTINCT activity_type) as activity_types,
                    COUNT(DISTINCT document_id) as documents_touched,
                    MIN(created_at) as first_activity,
                    MAX(created_at) as latest_activity
                FROM {activity_feed.name}
                WHERE workspace_id = :workspace_id
                AND created_at >= :start_date
                GROUP BY actor_id
                ORDER BY activity_count DESC
                LIMIT :limit
            """
            
            results = await db_manager.database.fetch_all(query, {
                "workspace_id": workspace_id,
                "start_date": start_date,
                "limit": limit
            })
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get most active users: {e}")
            return []
            
    async def _create_activity_notifications(self, activity: Dict[str, Any]):
        """Create notifications for relevant users based on activity"""
        try:
            workspace_id = activity["workspace_id"]
            actor_id = activity["actor_id"]
            activity_type = activity["activity_type"]
            
            # Get workspace members who should be notified
            members_query = f"""
                SELECT user_id, role
                FROM workspace_members
                WHERE workspace_id = :workspace_id
                AND is_active = true
                AND joined_at IS NOT NULL
                AND user_id != :actor_id
            """
            
            members = await db_manager.database.fetch_all(members_query, {
                "workspace_id": workspace_id,
                "actor_id": actor_id
            })
            
            # Check subscriptions and create notifications
            for member in members:
                user_id = member["user_id"]
                
                # Check if user is subscribed to this activity type
                if (user_id in self.activity_subscriptions and
                    workspace_id in self.activity_subscriptions[user_id] and
                    activity_type in self.activity_subscriptions[user_id][workspace_id]["activity_types"]):
                    
                    # Create notification
                    notification_data = {
                        "recipient_id": user_id,
                        "workspace_id": workspace_id,
                        "document_id": activity.get("document_id"),
                        "activity_id": activity["id"],
                        "notification_type": "activity",
                        "title": self._generate_activity_title(activity),
                        "message": self._generate_activity_message(activity),
                        "metadata": {
                            "activity_type": activity_type,
                            "actor_id": actor_id,
                            "target_type": activity.get("target_type"),
                            "target_id": activity.get("target_id")
                        },
                        "created_at": datetime.now(timezone.utc)
                    }
                    
                    query = notifications.insert().values(**notification_data)
                    await db_manager.database.execute(query)
                    
        except Exception as e:
            logger.warning(f"Failed to create activity notifications: {e}")
            
    def _generate_activity_title(self, activity: Dict[str, Any]) -> str:
        """Generate notification title for activity"""
        activity_type = activity["activity_type"]
        actor_id = activity["actor_id"]
        document_name = activity.get("document_name", "a document")
        
        titles = {
            ActivityType.DOCUMENT_CREATED.value: f"{actor_id} created {document_name}",
            ActivityType.DOCUMENT_UPDATED.value: f"{actor_id} updated {document_name}",
            ActivityType.ANNOTATION_ADDED.value: f"{actor_id} added an annotation",
            ActivityType.COMMENT_ADDED.value: f"{actor_id} added a comment",
            ActivityType.USER_JOINED.value: f"{actor_id} joined the workspace",
            ActivityType.VERSION_CREATED.value: f"{actor_id} created a new version"
        }
        
        return titles.get(activity_type, f"New activity: {activity_type}")
        
    def _generate_activity_message(self, activity: Dict[str, Any]) -> str:
        """Generate notification message for activity"""
        activity_type = activity["activity_type"]
        details = activity.get("details", {})
        document_name = activity.get("document_name", "document")
        
        messages = {
            ActivityType.DOCUMENT_CREATED.value: f"A new document '{document_name}' was created",
            ActivityType.DOCUMENT_UPDATED.value: f"Document '{document_name}' was modified",
            ActivityType.ANNOTATION_ADDED.value: f"New annotation added to '{document_name}'",
            ActivityType.COMMENT_ADDED.value: f"New comment added to '{document_name}'",
            ActivityType.USER_JOINED.value: f"New member joined the workspace",
            ActivityType.VERSION_CREATED.value: f"New version of '{document_name}' is available"
        }
        
        return messages.get(activity_type, f"Activity: {activity_type}")
        
    async def _get_workspace_name(self, workspace_id: str) -> Optional[str]:
        """Get workspace name by ID"""
        try:
            query = workspaces.select().where(workspaces.c.id == workspace_id)
            result = await db_manager.database.fetch_one(query)
            return result["name"] if result else None
        except Exception:
            return None
            
    async def _get_document_name(self, document_id: str) -> Optional[str]:
        """Get document name by ID"""
        try:
            query = documents.select().where(documents.c.id == document_id)
            result = await db_manager.database.fetch_one(query)
            return result["name"] if result else None
        except Exception:
            return None
            
    async def _update_workspace_activity(self, workspace_id: str):
        """Update workspace last activity timestamp"""
        try:
            query = (workspaces.update()
                    .where(workspaces.c.id == workspace_id)
                    .values(last_activity_at=datetime.now(timezone.utc)))
            await db_manager.database.execute(query)
            
        except Exception as e:
            logger.warning(f"Failed to update workspace activity: {e}")
            
    async def cleanup_old_activities(self, days_to_keep: int = 90) -> int:
        """Clean up old activities beyond retention period"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Delete old activities
            delete_query = activity_feed.delete().where(
                activity_feed.c.created_at < cutoff_date
            )
            
            result = await db_manager.database.execute(delete_query)
            
            # Clean up cache
            for workspace_id in list(self.recent_activities.keys()):
                self.recent_activities[workspace_id] = [
                    activity for activity in self.recent_activities[workspace_id]
                    if activity["created_at"] >= cutoff_date
                ]
                
                if not self.recent_activities[workspace_id]:
                    del self.recent_activities[workspace_id]
                    
            logger.info(f"Cleaned up {result} old activities")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup old activities: {e}")
            return 0