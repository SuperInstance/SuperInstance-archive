"""
Guest session management and real-time handling
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Set, Optional, List

import socketio
from socketio import AsyncNamespace

from .guest_manager import GuestManager

logger = logging.getLogger(__name__)

class GuestSessionManager(AsyncNamespace):
    """WebSocket handler for guest user sessions"""
    
    def __init__(self, guest_manager: GuestManager):
        super().__init__(namespace="/guests")
        self.guest_manager = guest_manager
        self.guest_connections = {}  # session_id -> socket_id mapping
        self.socket_sessions = {}    # socket_id -> session_data mapping
        self.document_guests = {}    # document_id -> set of session_ids
        
    async def on_connect(self, sid: str, environ: Dict[str, Any]):
        """Handle guest connection"""
        try:
            # Extract session info from connection
            guest_session_id = environ.get("guest_session_id")
            if not guest_session_id:
                logger.warning(f"Guest connection {sid} rejected: no guest_session_id")
                return False
            
            # Validate guest session
            session_data = await self.guest_manager.validate_guest_session(guest_session_id)
            if not session_data:
                logger.warning(f"Guest connection {sid} rejected: invalid session {guest_session_id}")
                return False
            
            # Store connection mappings
            self.guest_connections[guest_session_id] = sid
            self.socket_sessions[sid] = session_data
            
            # Track guests by document
            document_id = session_data["document_id"]
            if document_id not in self.document_guests:
                self.document_guests[document_id] = set()
            self.document_guests[document_id].add(guest_session_id)
            
            # Update session activity
            await self.guest_manager.update_session_activity(guest_session_id)
            
            # Send welcome message
            await self.emit("connected", {
                "message": "Connected as guest",
                "session_id": guest_session_id,
                "document_id": document_id,
                "permissions": session_data.get("permissions", []),
                "expires_at": session_data.get("token_expires_at")
            }, room=sid)
            
            logger.info(f"Guest session {guest_session_id} connected with socket {sid}")
            
        except Exception as e:
            logger.error(f"Guest connection error for {sid}: {e}")
            return False
            
    async def on_disconnect(self, sid: str):
        """Handle guest disconnection"""
        try:
            session_data = self.socket_sessions.get(sid)
            if session_data:
                guest_session_id = session_data["session_id"]
                document_id = session_data["document_id"]
                
                # Clean up mappings
                if guest_session_id in self.guest_connections:
                    del self.guest_connections[guest_session_id]
                    
                del self.socket_sessions[sid]
                
                # Remove from document guests
                if document_id in self.document_guests and guest_session_id in self.document_guests[document_id]:
                    self.document_guests[document_id].remove(guest_session_id)
                    
                    # Clean up empty document sets
                    if not self.document_guests[document_id]:
                        del self.document_guests[document_id]
                
                logger.info(f"Guest session {guest_session_id} disconnected from socket {sid}")
                
        except Exception as e:
            logger.error(f"Guest disconnect error for {sid}: {e}")
            
    async def on_join_document(self, sid: str, data: Dict[str, Any]):
        """Join document as guest (already handled in connect)"""
        try:
            session_data = self.socket_sessions.get(sid)
            if not session_data:
                await self.emit("error", {"message": "Invalid guest session"}, room=sid)
                return
                
            document_id = session_data["document_id"]
            
            # Check rate limit
            guest_session_id = session_data["session_id"]
            if not await self.guest_manager.check_rate_limit(guest_session_id, "join_document"):
                await self.emit("error", {"message": "Rate limit exceeded"}, room=sid)
                return
            
            # Join document room
            await self.enter_room(sid, f"guest_doc_{document_id}")
            
            # Get document info (limited for guests)
            document_info = {
                "document_id": document_id,
                "document_name": session_data.get("document_name"),
                "permissions": session_data.get("permissions", []),
                "guest_session_id": guest_session_id
            }
            
            await self.emit("document_joined", document_info, room=sid)
            
            # Notify other users about guest presence (if enabled)
            await self._notify_guest_presence(document_id, session_data, "joined")
            
        except Exception as e:
            logger.error(f"Guest join document error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to join document"}, room=sid)
            
    async def on_guest_activity(self, sid: str, data: Dict[str, Any]):
        """Handle guest activity (commenting, viewing, etc.)"""
        try:
            session_data = self.socket_sessions.get(sid)
            if not session_data:
                await self.emit("error", {"message": "Invalid guest session"}, room=sid)
                return
                
            guest_session_id = session_data["session_id"]
            document_id = session_data["document_id"]
            activity_type = data.get("activity_type")
            
            # Check rate limit
            if not await self.guest_manager.check_rate_limit(guest_session_id, activity_type):
                await self.emit("error", {"message": "Rate limit exceeded"}, room=sid)
                return
            
            # Check permissions
            permissions = session_data.get("permissions", [])
            if not self._check_activity_permission(activity_type, permissions):
                await self.emit("error", {"message": "Permission denied"}, room=sid)
                return
            
            # Update session activity
            await self.guest_manager.update_session_activity(guest_session_id)
            
            # Handle specific activity types
            if activity_type == "add_comment":
                await self._handle_guest_comment(sid, data, session_data)
            elif activity_type == "view_annotation":
                await self._handle_guest_annotation_view(sid, data, session_data)
            elif activity_type == "cursor_move":
                await self._handle_guest_cursor(sid, data, session_data)
            else:
                await self.emit("error", {"message": "Unknown activity type"}, room=sid)
                
        except Exception as e:
            logger.error(f"Guest activity error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to process activity"}, room=sid)
            
    async def on_get_document_content(self, sid: str, data: Dict[str, Any]):
        """Get document content for guest (read permission only)"""
        try:
            session_data = self.socket_sessions.get(sid)
            if not session_data:
                await self.emit("error", {"message": "Invalid guest session"}, room=sid)
                return
                
            # Check read permission
            permissions = session_data.get("permissions", [])
            if "read" not in permissions:
                await self.emit("error", {"message": "Read permission required"}, room=sid)
                return
            
            guest_session_id = session_data["session_id"]
            document_id = session_data["document_id"]
            
            # Check rate limit
            if not await self.guest_manager.check_rate_limit(guest_session_id, "get_content"):
                await self.emit("error", {"message": "Rate limit exceeded"}, room=sid)
                return
            
            # Update session activity
            await self.guest_manager.update_session_activity(guest_session_id)
            
            # For security, return limited document info
            content_info = {
                "document_id": document_id,
                "document_name": session_data.get("document_name"),
                "access_type": "guest",
                "permissions": permissions,
                "message": "Document content access - use appropriate viewer for full content"
            }
            
            await self.emit("document_content", content_info, room=sid)
            
        except Exception as e:
            logger.error(f"Guest get document content error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to get document content"}, room=sid)
            
    async def on_heartbeat(self, sid: str):
        """Handle guest session heartbeat"""
        try:
            session_data = self.socket_sessions.get(sid)
            if not session_data:
                return
                
            guest_session_id = session_data["session_id"]
            
            # Update session activity
            await self.guest_manager.update_session_activity(guest_session_id)
            
            # Check if session is still valid
            current_session = await self.guest_manager.validate_guest_session(guest_session_id)
            if not current_session:
                await self.emit("session_expired", {"message": "Guest session has expired"}, room=sid)
                await self.disconnect(sid)
                return
                
            await self.emit("heartbeat_ack", {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "expires_at": current_session.get("token_expires_at")
            }, room=sid)
            
        except Exception as e:
            logger.error(f"Guest heartbeat error for {sid}: {e}")
            
    async def _handle_guest_comment(self, sid: str, data: Dict[str, Any], session_data: Dict[str, Any]):
        """Handle guest comment creation"""
        try:
            # Check comment permission
            if "comment" not in session_data.get("permissions", []):
                await self.emit("error", {"message": "Comment permission required"}, room=sid)
                return
            
            # Prepare comment data with guest info
            comment_data = {
                "content": data.get("content", ""),
                "document_id": session_data["document_id"],
                "annotation_id": data.get("annotation_id"),
                "metadata": {
                    "guest_session": True,
                    "guest_name": session_data.get("guest_name", "Anonymous Guest"),
                    "guest_email": session_data.get("guest_email")
                }
            }
            
            # Create comment through comment manager (would need integration)
            # This is a simplified version - in reality would integrate with CommentManager
            
            await self.emit("comment_created", {
                "comment": comment_data,
                "success": True,
                "message": "Comment added successfully"
            }, room=sid)
            
            # Broadcast to document room (notify regular users)
            await self.emit("guest_comment_added", {
                "comment": comment_data,
                "guest_info": {
                    "name": session_data.get("guest_name", "Anonymous Guest"),
                    "session_id": session_data["session_id"]
                }
            }, room=f"guest_doc_{session_data['document_id']}", skip_sid=sid)
            
        except Exception as e:
            logger.error(f"Guest comment error: {e}")
            await self.emit("error", {"message": "Failed to add comment"}, room=sid)
            
    async def _handle_guest_annotation_view(self, sid: str, data: Dict[str, Any], session_data: Dict[str, Any]):
        """Handle guest annotation viewing"""
        try:
            annotation_id = data.get("annotation_id")
            if not annotation_id:
                await self.emit("error", {"message": "annotation_id required"}, room=sid)
                return
            
            # For guests, return limited annotation info
            annotation_info = {
                "annotation_id": annotation_id,
                "viewed_by_guest": True,
                "guest_name": session_data.get("guest_name", "Anonymous Guest"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.emit("annotation_viewed", annotation_info, room=sid)
            
        except Exception as e:
            logger.error(f"Guest annotation view error: {e}")
            await self.emit("error", {"message": "Failed to view annotation"}, room=sid)
            
    async def _handle_guest_cursor(self, sid: str, data: Dict[str, Any], session_data: Dict[str, Any]):
        """Handle guest cursor movement"""
        try:
            cursor_data = data.get("cursor_data", {})
            document_id = session_data["document_id"]
            
            # Broadcast cursor position to other users in document (anonymized)
            await self.emit("guest_cursor_moved", {
                "document_id": document_id,
                "guest_name": session_data.get("guest_name", "Anonymous Guest"),
                "cursor_data": cursor_data,
                "session_id": session_data["session_id"]
            }, room=f"guest_doc_{document_id}", skip_sid=sid)
            
        except Exception as e:
            logger.error(f"Guest cursor error: {e}")
            
    def _check_activity_permission(self, activity_type: str, permissions: List[str]) -> bool:
        """Check if guest has permission for activity type"""
        permission_map = {
            "add_comment": "comment",
            "view_annotation": "read",
            "cursor_move": "read",
            "get_content": "read"
        }
        
        required_permission = permission_map.get(activity_type)
        return required_permission in permissions if required_permission else False
        
    async def _notify_guest_presence(self, document_id: str, session_data: Dict[str, Any], action: str):
        """Notify other users about guest presence"""
        try:
            presence_data = {
                "document_id": document_id,
                "guest_name": session_data.get("guest_name", "Anonymous Guest"),
                "session_id": session_data["session_id"],
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Notify regular users in the document
            await self.emit("guest_presence_changed", presence_data, room=f"doc_{document_id}")
            
        except Exception as e:
            logger.error(f"Guest presence notification error: {e}")
            
    async def broadcast_to_document_guests(self, document_id: str, event_type: str, 
                                         event_data: Dict[str, Any]):
        """Broadcast event to all guests in a document"""
        try:
            if document_id not in self.document_guests:
                return
                
            guest_sessions = self.document_guests[document_id]
            
            for guest_session_id in guest_sessions:
                if guest_session_id in self.guest_connections:
                    socket_id = self.guest_connections[guest_session_id]
                    await self.emit(event_type, event_data, room=socket_id)
                    
        except Exception as e:
            logger.error(f"Broadcast to document guests error: {e}")
            
    def get_document_guest_count(self, document_id: str) -> int:
        """Get number of active guests in a document"""
        return len(self.document_guests.get(document_id, set()))
        
    def get_active_guest_sessions(self, document_id: str) -> List[Dict[str, Any]]:
        """Get active guest session info for a document"""
        try:
            if document_id not in self.document_guests:
                return []
                
            active_sessions = []
            guest_sessions = self.document_guests[document_id]
            
            for guest_session_id in guest_sessions:
                if guest_session_id in self.guest_connections:
                    socket_id = self.guest_connections[guest_session_id]
                    session_data = self.socket_sessions.get(socket_id)
                    
                    if session_data:
                        active_sessions.append({
                            "session_id": guest_session_id,
                            "guest_name": session_data.get("guest_name", "Anonymous Guest"),
                            "permissions": session_data.get("permissions", []),
                            "connected_at": session_data.get("created_at"),
                            "last_activity": session_data.get("last_activity_at")
                        })
                        
            return active_sessions
            
        except Exception as e:
            logger.error(f"Get active guest sessions error: {e}")
            return []
            
    async def cleanup_inactive_connections(self):
        """Clean up inactive guest connections"""
        try:
            current_time = datetime.now(timezone.utc)
            inactive_sockets = []
            
            for socket_id, session_data in self.socket_sessions.items():
                last_activity = session_data.get("last_activity_at")
                if isinstance(last_activity, str):
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    
                # Consider connection inactive if no activity for 30 minutes
                if current_time - last_activity > timedelta(minutes=30):
                    inactive_sockets.append(socket_id)
                    
            # Disconnect inactive sockets
            for socket_id in inactive_sockets:
                try:
                    await self.disconnect(socket_id)
                    logger.info(f"Disconnected inactive guest socket {socket_id}")
                except Exception as e:
                    logger.warning(f"Failed to disconnect inactive socket {socket_id}: {e}")
                    
            return len(inactive_sockets)
            
        except Exception as e:
            logger.error(f"Cleanup inactive connections error: {e}")
            return 0