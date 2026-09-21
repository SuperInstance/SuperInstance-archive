"""
Comment and discussion management for collaborative documents
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4

from core.database import db_manager, comments, notifications, activity_feed
from core.database import ActivityType

logger = logging.getLogger(__name__)

class CommentManager:
    def __init__(self):
        self.comment_threads = {}  # Cache for comment threads
        self.mention_pattern = re.compile(r'@(\w+)', re.IGNORECASE)
        
    async def initialize(self):
        """Initialize comment manager"""
        logger.info("Initializing comment manager")
        await self._load_recent_threads()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up comment manager")
        self.comment_threads.clear()
        
    async def _load_recent_threads(self):
        """Load recent comment threads into cache"""
        try:
            # Load comments from last 7 days
            query = f"""
                SELECT id, document_id, annotation_id, parent_comment_id, 
                       created_by, content, mentions, is_edited, is_deleted,
                       created_at, updated_at
                FROM {comments.name}
                WHERE created_at > NOW() - INTERVAL '7 days'
                AND is_deleted = false
                ORDER BY created_at ASC
                LIMIT 5000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            # Group by document and annotation
            for comment in results:
                comment_dict = dict(comment)
                document_id = str(comment_dict["document_id"])
                annotation_id = str(comment_dict["annotation_id"]) if comment_dict["annotation_id"] else "general"
                
                if document_id not in self.comment_threads:
                    self.comment_threads[document_id] = {}
                    
                if annotation_id not in self.comment_threads[document_id]:
                    self.comment_threads[document_id][annotation_id] = []
                    
                self.comment_threads[document_id][annotation_id].append(comment_dict)
                
            logger.info(f"Loaded {len(results)} recent comments")
            
        except Exception as e:
            logger.error(f"Failed to load recent threads: {e}")
            
    async def create_comment(self, comment_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Create a new comment"""
        try:
            # Validate required fields
            required_fields = ["document_id", "content"]
            for field in required_fields:
                if field not in comment_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Generate comment ID
            comment_id = str(uuid4())
            
            # Extract mentions from content
            mentions = self._extract_mentions(comment_data["content"])
            
            # Prepare comment data
            comm_data = {
                "id": comment_id,
                "document_id": comment_data["document_id"],
                "annotation_id": comment_data.get("annotation_id"),
                "parent_comment_id": comment_data.get("parent_comment_id"),
                "created_by": user_id,
                "content": comment_data["content"],
                "mentions": mentions,
                "metadata": comment_data.get("metadata", {}),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Insert into database
            query = comments.insert().values(**comm_data)
            await db_manager.database.execute(query)
            
            # Update cache
            document_id = str(comment_data["document_id"])
            annotation_id = str(comment_data.get("annotation_id", "general"))
            
            if document_id not in self.comment_threads:
                self.comment_threads[document_id] = {}
            if annotation_id not in self.comment_threads[document_id]:
                self.comment_threads[document_id][annotation_id] = []
                
            self.comment_threads[document_id][annotation_id].append(comm_data)
            
            # Create notifications for mentions
            await self._create_mention_notifications(comment_id, mentions, user_id, comment_data["document_id"])
            
            # Log activity
            await self._log_comment_activity(
                document_id=document_id,
                comment_id=comment_id,
                user_id=user_id,
                activity_type=ActivityType.COMMENT_ADDED,
                details={"annotation_id": comment_data.get("annotation_id")}
            )
            
            logger.info(f"Created comment {comment_id} by {user_id}")
            return comm_data
            
        except Exception as e:
            logger.error(f"Failed to create comment: {e}")
            raise
            
    async def update_comment(self, comment_id: str, updates: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Update an existing comment"""
        try:
            # Get existing comment
            comment = await self.get_comment(comment_id)
            if not comment:
                raise ValueError(f"Comment {comment_id} not found")
            
            # Check permissions (owner or admin)
            if comment["created_by"] != user_id:
                # TODO: Check admin permissions
                raise PermissionError("Only comment owner can edit")
            
            # Prepare update data
            update_data = {
                "updated_at": datetime.now(timezone.utc),
                "is_edited": True,
                "edited_at": datetime.now(timezone.utc)
            }
            
            # Handle content update
            if "content" in updates:
                update_data["content"] = updates["content"]
                update_data["mentions"] = self._extract_mentions(updates["content"])
                
                # Create notifications for new mentions
                existing_mentions = set(comment.get("mentions", []))
                new_mentions = set(update_data["mentions"])
                added_mentions = new_mentions - existing_mentions
                
                if added_mentions:
                    await self._create_mention_notifications(
                        comment_id, list(added_mentions), user_id, comment["document_id"]
                    )
            
            # Update metadata if provided
            if "metadata" in updates:
                current_metadata = comment.get("metadata", {})
                current_metadata.update(updates["metadata"])
                update_data["metadata"] = current_metadata
            
            # Update in database
            query = (comments.update()
                    .where(comments.c.id == comment_id)
                    .values(**update_data))
            await db_manager.database.execute(query)
            
            # Update cache
            document_id = str(comment["document_id"])
            annotation_id = str(comment.get("annotation_id", "general"))
            
            if (document_id in self.comment_threads and 
                annotation_id in self.comment_threads[document_id]):
                
                for i, cached_comment in enumerate(self.comment_threads[document_id][annotation_id]):
                    if cached_comment["id"] == comment_id:
                        self.comment_threads[document_id][annotation_id][i].update(update_data)
                        break
            
            # Get updated comment
            updated_comment = await self.get_comment(comment_id)
            
            # Log activity
            await self._log_comment_activity(
                document_id=document_id,
                comment_id=comment_id,
                user_id=user_id,
                activity_type=ActivityType.COMMENT_UPDATED,
                details={"updated_fields": list(updates.keys())}
            )
            
            logger.info(f"Updated comment {comment_id} by {user_id}")
            return updated_comment
            
        except Exception as e:
            logger.error(f"Failed to update comment {comment_id}: {e}")
            raise
            
    async def delete_comment(self, comment_id: str, user_id: str) -> bool:
        """Soft delete a comment"""
        try:
            # Get existing comment
            comment = await self.get_comment(comment_id)
            if not comment:
                raise ValueError(f"Comment {comment_id} not found")
            
            # Check permissions (owner or admin)
            if comment["created_by"] != user_id:
                # TODO: Check admin permissions
                raise PermissionError("Only comment owner can delete")
            
            # Soft delete
            update_data = {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            query = (comments.update()
                    .where(comments.c.id == comment_id)
                    .values(**update_data))
            await db_manager.database.execute(query)
            
            # Remove from cache
            document_id = str(comment["document_id"])
            annotation_id = str(comment.get("annotation_id", "general"))
            
            if (document_id in self.comment_threads and 
                annotation_id in self.comment_threads[document_id]):
                
                self.comment_threads[document_id][annotation_id] = [
                    c for c in self.comment_threads[document_id][annotation_id] 
                    if c["id"] != comment_id
                ]
            
            # Log activity
            await self._log_comment_activity(
                document_id=document_id,
                comment_id=comment_id,
                user_id=user_id,
                activity_type=ActivityType.COMMENT_DELETED,
                details={"annotation_id": comment.get("annotation_id")}
            )
            
            logger.info(f"Deleted comment {comment_id} by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete comment {comment_id}: {e}")
            raise
            
    async def get_comment(self, comment_id: str) -> Optional[Dict[str, Any]]:
        """Get comment by ID"""
        try:
            # Check cache first
            for document_id, doc_threads in self.comment_threads.items():
                for annotation_id, thread_comments in doc_threads.items():
                    for comment in thread_comments:
                        if comment["id"] == comment_id:
                            return comment
            
            # Query database
            query = (comments.select()
                    .where(comments.c.id == comment_id)
                    .where(comments.c.is_deleted == False))
            result = await db_manager.database.fetch_one(query)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get comment {comment_id}: {e}")
            return None
            
    async def get_document_comments(self, document_id: str, annotation_id: Optional[str] = None, 
                                   limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get comments for a document or specific annotation"""
        try:
            # Build query conditions
            conditions = [
                comments.c.document_id == document_id,
                comments.c.is_deleted == False
            ]
            
            if annotation_id:
                conditions.append(comments.c.annotation_id == annotation_id)
            
            # Query database
            query = (comments.select()
                    .where(*conditions)
                    .order_by(comments.c.created_at.asc())
                    .limit(limit)
                    .offset(offset))
            
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get comments for document {document_id}: {e}")
            return []
            
    async def get_comment_thread(self, parent_comment_id: str) -> List[Dict[str, Any]]:
        """Get comment thread (replies to a comment)"""
        try:
            query = (comments.select()
                    .where(comments.c.parent_comment_id == parent_comment_id)
                    .where(comments.c.is_deleted == False)
                    .order_by(comments.c.created_at.asc()))
            
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get comment thread for {parent_comment_id}: {e}")
            return []
            
    async def get_user_mentions(self, user_id: str, document_id: Optional[str] = None, 
                               limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get comments where user is mentioned"""
        try:
            # Build query conditions
            conditions = [
                comments.c.mentions.op('@>')([user_id]),  # PostgreSQL array contains
                comments.c.is_deleted == False
            ]
            
            if document_id:
                conditions.append(comments.c.document_id == document_id)
            
            query = (comments.select()
                    .where(*conditions)
                    .order_by(comments.c.created_at.desc())
                    .limit(limit)
                    .offset(offset))
            
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get mentions for user {user_id}: {e}")
            return []
            
    def _extract_mentions(self, content: str) -> List[str]:
        """Extract @mentions from comment content"""
        try:
            matches = self.mention_pattern.findall(content)
            return list(set(matches))  # Remove duplicates
        except Exception:
            return []
            
    async def _create_mention_notifications(self, comment_id: str, mentions: List[str], 
                                          mentioner_id: str, document_id: str):
        """Create notifications for mentioned users"""
        try:
            if not mentions:
                return
                
            # Get comment details
            comment = await self.get_comment(comment_id)
            if not comment:
                return
            
            # Get workspace ID from document
            from core.database import documents
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                return
                
            workspace_id = str(doc_result["workspace_id"])
            
            # Create notifications for each mentioned user
            for mentioned_user in mentions:
                if mentioned_user == mentioner_id:  # Don't notify self
                    continue
                    
                notification_data = {
                    "recipient_id": mentioned_user,
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "notification_type": "mention",
                    "title": f"You were mentioned in a comment",
                    "message": f"{mentioner_id} mentioned you: {comment['content'][:100]}{'...' if len(comment['content']) > 100 else ''}",
                    "metadata": {
                        "comment_id": comment_id,
                        "mentioner_id": mentioner_id,
                        "annotation_id": comment.get("annotation_id")
                    },
                    "created_at": datetime.now(timezone.utc)
                }
                
                query = notifications.insert().values(**notification_data)
                await db_manager.database.execute(query)
                
            logger.info(f"Created mention notifications for {len(mentions)} users")
            
        except Exception as e:
            logger.error(f"Failed to create mention notifications: {e}")
            
    async def _log_comment_activity(self, document_id: str, comment_id: str, 
                                  user_id: str, activity_type: ActivityType, 
                                  details: Dict[str, Any] = None):
        """Log comment activity"""
        try:
            # Get workspace from document
            from core.database import documents
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                return
                
            workspace_id = str(doc_result["workspace_id"])
            
            activity_data = {
                "workspace_id": workspace_id,
                "document_id": document_id,
                "actor_id": user_id,
                "activity_type": activity_type.value,
                "target_id": comment_id,
                "target_type": "comment",
                "details": details or {},
                "created_at": datetime.now(timezone.utc)
            }
            
            query = activity_feed.insert().values(**activity_data)
            await db_manager.database.execute(query)
            
        except Exception as e:
            logger.warning(f"Failed to log comment activity: {e}")
            
    async def get_comment_statistics(self, document_id: str) -> Dict[str, Any]:
        """Get comment statistics for a document"""
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_comments,
                    COUNT(DISTINCT created_by) as unique_commenters,
                    COUNT(CASE WHEN parent_comment_id IS NOT NULL THEN 1 END) as replies,
                    COUNT(CASE WHEN annotation_id IS NOT NULL THEN 1 END) as annotation_comments,
                    COUNT(CASE WHEN annotation_id IS NULL THEN 1 END) as general_comments,
                    COUNT(CASE WHEN is_edited = true THEN 1 END) as edited_comments,
                    COUNT(CASE WHEN array_length(mentions, 1) > 0 THEN 1 END) as comments_with_mentions
                FROM {comments.name}
                WHERE document_id = :document_id 
                AND is_deleted = false
            """
            
            result = await db_manager.database.fetch_one(query, {"document_id": document_id})
            return dict(result) if result else {}
            
        except Exception as e:
            logger.error(f"Failed to get comment statistics: {e}")
            return {}
            
    async def search_comments(self, document_id: str, search_query: str, 
                             limit: int = 50) -> List[Dict[str, Any]]:
        """Search comments by content"""
        try:
            # Use PostgreSQL full-text search
            query = f"""
                SELECT * FROM {comments.name}
                WHERE document_id = :document_id
                AND is_deleted = false
                AND to_tsvector('english', content) @@ plainto_tsquery('english', :search_query)
                ORDER BY ts_rank(to_tsvector('english', content), plainto_tsquery('english', :search_query)) DESC
                LIMIT :limit
            """
            
            results = await db_manager.database.fetch_all(query, {
                "document_id": document_id,
                "search_query": search_query,
                "limit": limit
            })
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to search comments: {e}")
            return []