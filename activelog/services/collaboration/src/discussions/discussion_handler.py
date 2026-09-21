"""
Real-time discussion handler for comments and threads
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
from uuid import UUID

import socketio
from socketio import AsyncNamespace

from .comment_manager import CommentManager

logger = logging.getLogger(__name__)

class DiscussionHandler(AsyncNamespace):
    """WebSocket handler for real-time discussions and comments"""
    
    def __init__(self, comment_manager: CommentManager):
        super().__init__(namespace="/discussions")
        self.comment_manager = comment_manager
        self.discussion_rooms: Dict[str, Set[str]] = {}  # document_id -> session_ids
        self.session_users: Dict[str, str] = {}  # session_id -> user_id
        self.active_typers: Dict[str, Dict[str, Dict[str, Any]]] = {}  # document_id -> annotation_id -> user_typing_data
        
    async def on_connect(self, sid: str, environ: Dict[str, Any]):
        """Handle client connection"""
        try:
            # Extract user info from connection
            user_id = environ.get("user_id")
            if not user_id:
                logger.warning(f"Discussion connection {sid} rejected: no user_id")
                return False
                
            self.session_users[sid] = user_id
            logger.info(f"User {user_id} connected to discussions with session {sid}")
            
            # Send welcome message
            await self.emit("connected", {
                "message": "Connected to discussion service",
                "features": ["real_time_comments", "mention_notifications", "typing_indicators"]
            }, room=sid)
            
        except Exception as e:
            logger.error(f"Discussion connection error for {sid}: {e}")
            return False
            
    async def on_disconnect(self, sid: str):
        """Handle client disconnection"""
        try:
            user_id = self.session_users.get(sid)
            if user_id:
                # Remove from all discussion rooms
                rooms_to_leave = []
                for document_id, sessions in self.discussion_rooms.items():
                    if sid in sessions:
                        rooms_to_leave.append(document_id)
                        
                for document_id in rooms_to_leave:
                    await self._leave_discussion_room(sid, document_id, user_id)
                
                # Clean up session data
                del self.session_users[sid]
                
                logger.info(f"User {user_id} disconnected from discussions session {sid}")
                
        except Exception as e:
            logger.error(f"Discussion disconnect error for {sid}: {e}")
            
    async def on_join_discussion(self, sid: str, data: Dict[str, Any]):
        """Join a document discussion room"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
                
            document_id = data.get("document_id")
            if not document_id:
                await self.emit("error", {"message": "document_id required"}, room=sid)
                return
            
            # TODO: Verify user has access to document
            
            # Join room
            await self.enter_room(sid, f"discussion_{document_id}")
            
            # Track in discussion rooms
            if document_id not in self.discussion_rooms:
                self.discussion_rooms[document_id] = set()
                self.active_typers[document_id] = {}
            self.discussion_rooms[document_id].add(sid)
            
            # Load recent comments
            recent_comments = await self.comment_manager.get_document_comments(
                document_id, limit=50
            )
            
            # Get comment statistics
            stats = await self.comment_manager.get_comment_statistics(document_id)
            
            # Send initial data
            await self.emit("discussion_joined", {
                "document_id": document_id,
                "recent_comments": recent_comments,
                "statistics": stats,
                "active_users": list(self._get_discussion_users(document_id)),
                "user_id": user_id
            }, room=sid)
            
            # Notify other users
            await self.emit("user_joined_discussion", {
                "document_id": document_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"discussion_{document_id}", skip_sid=sid)
            
            logger.info(f"User {user_id} joined discussion for document {document_id}")
            
        except Exception as e:
            logger.error(f"Join discussion error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to join discussion"}, room=sid)
            
    async def on_leave_discussion(self, sid: str, data: Dict[str, Any]):
        """Leave a document discussion room"""
        try:
            user_id = self.session_users.get(sid)
            document_id = data.get("document_id")
            
            if user_id and document_id:
                await self._leave_discussion_room(sid, document_id, user_id)
                
        except Exception as e:
            logger.error(f"Leave discussion error for {sid}: {e}")
            
    async def _leave_discussion_room(self, sid: str, document_id: str, user_id: str):
        """Helper to leave discussion room"""
        try:
            # Leave WebSocket room
            await self.leave_room(sid, f"discussion_{document_id}")
            
            # Remove from tracking
            if document_id in self.discussion_rooms and sid in self.discussion_rooms[document_id]:
                self.discussion_rooms[document_id].remove(sid)
                
                # Clean up if no more sessions
                if not self.discussion_rooms[document_id]:
                    del self.discussion_rooms[document_id]
                    if document_id in self.active_typers:
                        del self.active_typers[document_id]
                        
            # Remove from typing indicators
            if document_id in self.active_typers:
                for annotation_id in self.active_typers[document_id]:
                    if user_id in self.active_typers[document_id][annotation_id]:
                        del self.active_typers[document_id][annotation_id][user_id]
            
            # Notify other users
            await self.emit("user_left_discussion", {
                "document_id": document_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"discussion_{document_id}")
            
            logger.info(f"User {user_id} left discussion for document {document_id}")
            
        except Exception as e:
            logger.error(f"Leave discussion room error: {e}")
            
    async def on_create_comment(self, sid: str, data: Dict[str, Any]):
        """Handle real-time comment creation"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
            
            # Create comment
            comment = await self.comment_manager.create_comment(data, user_id)
            document_id = str(comment["document_id"])
            
            # Broadcast to all users in discussion
            await self.emit("comment_created", {
                "comment": comment,
                "created_by": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"discussion_{document_id}")
            
            # Send mention notifications if any
            if comment.get("mentions"):
                await self._handle_mention_notifications(comment, user_id)
            
            logger.info(f"Real-time comment created {comment['id']} by {user_id}")
            
        except Exception as e:
            logger.error(f"Create comment error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to create comment"}, room=sid)
            
    async def on_update_comment(self, sid: str, data: Dict[str, Any]):
        """Handle real-time comment updates"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
            
            comment_id = data.get("comment_id")
            updates = data.get("updates", {})
            
            if not comment_id:
                await self.emit("error", {"message": "comment_id required"}, room=sid)
                return
            
            # Update comment
            comment = await self.comment_manager.update_comment(
                comment_id, updates, user_id
            )
            document_id = str(comment["document_id"])
            
            # Broadcast to all users in discussion
            await self.emit("comment_updated", {
                "comment": comment,
                "updated_by": user_id,
                "updates": updates,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"discussion_{document_id}")
            
            logger.info(f"Real-time comment updated {comment_id} by {user_id}")
            
        except Exception as e:
            logger.error(f"Update comment error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to update comment"}, room=sid)
            
    async def on_delete_comment(self, sid: str, data: Dict[str, Any]):
        """Handle real-time comment deletion"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
            
            comment_id = data.get("comment_id")
            if not comment_id:
                await self.emit("error", {"message": "comment_id required"}, room=sid)
                return
            
            # Get comment before deletion for document_id
            comment = await self.comment_manager.get_comment(comment_id)
            if not comment:
                await self.emit("error", {"message": "Comment not found"}, room=sid)
                return
                
            document_id = str(comment["document_id"])
            
            # Delete comment
            await self.comment_manager.delete_comment(comment_id, user_id)
            
            # Broadcast to all users in discussion
            await self.emit("comment_deleted", {
                "comment_id": comment_id,
                "document_id": document_id,
                "annotation_id": comment.get("annotation_id"),
                "deleted_by": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"discussion_{document_id}")
            
            logger.info(f"Real-time comment deleted {comment_id} by {user_id}")
            
        except Exception as e:
            logger.error(f"Delete comment error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to delete comment"}, room=sid)
            
    async def on_start_typing(self, sid: str, data: Dict[str, Any]):
        """Handle typing start indicators"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                return
                
            document_id = data.get("document_id")
            annotation_id = data.get("annotation_id", "general")  # "general" for document-level comments
            
            if document_id and document_id in self.active_typers:
                # Track typing user
                if annotation_id not in self.active_typers[document_id]:
                    self.active_typers[document_id][annotation_id] = {}
                    
                self.active_typers[document_id][annotation_id][user_id] = {
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "session_id": sid
                }
                
                # Broadcast typing indicator
                await self.emit("user_typing", {
                    "document_id": document_id,
                    "annotation_id": annotation_id,
                    "user_id": user_id,
                    "is_typing": True,
                    "typing_users": list(self.active_typers[document_id][annotation_id].keys())
                }, room=f"discussion_{document_id}", skip_sid=sid)
                
        except Exception as e:
            logger.error(f"Start typing error for {sid}: {e}")
            
    async def on_stop_typing(self, sid: str, data: Dict[str, Any]):
        """Handle typing stop indicators"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                return
                
            document_id = data.get("document_id")
            annotation_id = data.get("annotation_id", "general")
            
            if (document_id and document_id in self.active_typers and 
                annotation_id in self.active_typers[document_id] and
                user_id in self.active_typers[document_id][annotation_id]):
                
                # Remove typing user
                del self.active_typers[document_id][annotation_id][user_id]
                
                # Broadcast stop typing
                await self.emit("user_typing", {
                    "document_id": document_id,
                    "annotation_id": annotation_id,
                    "user_id": user_id,
                    "is_typing": False,
                    "typing_users": list(self.active_typers[document_id][annotation_id].keys())
                }, room=f"discussion_{document_id}", skip_sid=sid)
                
        except Exception as e:
            logger.error(f"Stop typing error for {sid}: {e}")
            
    async def on_get_comment_thread(self, sid: str, data: Dict[str, Any]):
        """Get comments for a specific thread"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
                
            parent_comment_id = data.get("parent_comment_id")
            if not parent_comment_id:
                await self.emit("error", {"message": "parent_comment_id required"}, room=sid)
                return
            
            # Get thread comments
            thread_comments = await self.comment_manager.get_comment_thread(parent_comment_id)
            
            await self.emit("comment_thread", {
                "parent_comment_id": parent_comment_id,
                "thread_comments": thread_comments
            }, room=sid)
            
        except Exception as e:
            logger.error(f"Get comment thread error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to get comment thread"}, room=sid)
            
    async def on_search_comments(self, sid: str, data: Dict[str, Any]):
        """Search comments in a document"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
                
            document_id = data.get("document_id")
            search_query = data.get("search_query")
            
            if not document_id or not search_query:
                await self.emit("error", {"message": "document_id and search_query required"}, room=sid)
                return
            
            # Search comments
            search_results = await self.comment_manager.search_comments(
                document_id, search_query, limit=data.get("limit", 50)
            )
            
            await self.emit("search_results", {
                "document_id": document_id,
                "search_query": search_query,
                "results": search_results,
                "total_results": len(search_results)
            }, room=sid)
            
        except Exception as e:
            logger.error(f"Search comments error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to search comments"}, room=sid)
            
    async def on_get_user_mentions(self, sid: str, data: Dict[str, Any]):
        """Get mentions for the current user"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
            
            document_id = data.get("document_id")  # Optional, can get mentions across all documents
            
            # Get mentions
            mentions = await self.comment_manager.get_user_mentions(
                user_id, document_id, 
                limit=data.get("limit", 50),
                offset=data.get("offset", 0)
            )
            
            await self.emit("user_mentions", {
                "mentions": mentions,
                "total_mentions": len(mentions)
            }, room=sid)
            
        except Exception as e:
            logger.error(f"Get user mentions error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to get mentions"}, room=sid)
            
    async def _handle_mention_notifications(self, comment: Dict[str, Any], mentioner_id: str):
        """Handle real-time mention notifications"""
        try:
            if not comment.get("mentions"):
                return
                
            document_id = str(comment["document_id"])
            
            # Send real-time notifications to mentioned users who are online
            for mentioned_user in comment["mentions"]:
                if mentioned_user == mentioner_id:  # Skip self
                    continue
                    
                # Find sessions for mentioned user
                mentioned_sessions = [
                    sid for sid, uid in self.session_users.items() 
                    if uid == mentioned_user
                ]
                
                # Send notification to all their sessions
                for session_id in mentioned_sessions:
                    await self.emit("mention_notification", {
                        "comment": comment,
                        "mentioner_id": mentioner_id,
                        "mentioned_user": mentioned_user,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }, room=session_id)
                    
        except Exception as e:
            logger.error(f"Handle mention notifications error: {e}")
            
    def _get_discussion_users(self, document_id: str) -> Set[str]:
        """Get active users in a document discussion"""
        users = set()
        if document_id in self.discussion_rooms:
            for session_id in self.discussion_rooms[document_id]:
                if session_id in self.session_users:
                    users.add(self.session_users[session_id])
        return users
        
    async def broadcast_comment_event(self, document_id: str, event_type: str, 
                                    event_data: Dict[str, Any]):
        """Broadcast comment event to all users in document discussion"""
        try:
            await self.emit(event_type, event_data, room=f"discussion_{document_id}")
            
        except Exception as e:
            logger.error(f"Broadcast comment event error: {e}")
            
    def get_discussion_stats(self, document_id: str) -> Dict[str, Any]:
        """Get real-time discussion statistics"""
        return {
            "active_users": list(self._get_discussion_users(document_id)),
            "total_sessions": len(self.discussion_rooms.get(document_id, set())),
            "typing_indicators": self.active_typers.get(document_id, {}),
            "active_threads": len([
                annotation_id for annotation_id, typers in self.active_typers.get(document_id, {}).items()
                if typers
            ])
        }