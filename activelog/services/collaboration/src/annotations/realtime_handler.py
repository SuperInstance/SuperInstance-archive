"""
Real-time annotation handler using WebSockets
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Set, Optional
from uuid import UUID

import socketio
from socketio import AsyncNamespace

from core.config import settings
from .annotation_manager import AnnotationManager

logger = logging.getLogger(__name__)

class RealtimeAnnotationHandler(AsyncNamespace):
    """WebSocket handler for real-time collaborative annotations"""
    
    def __init__(self, annotation_manager: AnnotationManager):
        super().__init__(namespace="/annotations")
        self.annotation_manager = annotation_manager
        self.document_rooms: Dict[str, Set[str]] = {}  # document_id -> set of session_ids
        self.session_users: Dict[str, str] = {}  # session_id -> user_id
        self.user_cursors: Dict[str, Dict[str, Any]] = {}  # document_id -> user_cursors
        self.active_selections: Dict[str, Dict[str, Any]] = {}  # document_id -> user_selections
        
    async def on_connect(self, sid: str, environ: Dict[str, Any]):
        """Handle client connection"""
        try:
            # Extract user info from connection
            user_id = environ.get("user_id")
            if not user_id:
                logger.warning(f"Connection {sid} rejected: no user_id")
                return False
                
            self.session_users[sid] = user_id
            logger.info(f"User {user_id} connected with session {sid}")
            
            # Send welcome message
            await self.emit("connected", {"message": "Connected to annotation service"}, room=sid)
            
        except Exception as e:
            logger.error(f"Connection error for {sid}: {e}")
            return False
            
    async def on_disconnect(self, sid: str):
        """Handle client disconnection"""
        try:
            user_id = self.session_users.get(sid)
            if user_id:
                # Remove from all document rooms
                rooms_to_leave = []
                for document_id, sessions in self.document_rooms.items():
                    if sid in sessions:
                        rooms_to_leave.append(document_id)
                        
                for document_id in rooms_to_leave:
                    await self._leave_document_room(sid, document_id, user_id)
                
                # Clean up session data
                del self.session_users[sid]
                
                logger.info(f"User {user_id} disconnected from session {sid}")
                
        except Exception as e:
            logger.error(f"Disconnect error for {sid}: {e}")
            
    async def on_join_document(self, sid: str, data: Dict[str, Any]):
        """Join a document room for real-time collaboration"""
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
            await self.enter_room(sid, f"doc_{document_id}")
            
            # Track in document rooms
            if document_id not in self.document_rooms:
                self.document_rooms[document_id] = set()
            self.document_rooms[document_id].add(sid)
            
            # Initialize cursor tracking
            if document_id not in self.user_cursors:
                self.user_cursors[document_id] = {}
            if document_id not in self.active_selections:
                self.active_selections[document_id] = {}
                
            # Load existing annotations
            annotations = await self.annotation_manager.get_document_annotations(
                document_id, user_id
            )
            
            # Send initial data
            await self.emit("document_joined", {
                "document_id": document_id,
                "annotations": annotations,
                "active_users": list(self.user_cursors[document_id].keys()),
                "user_id": user_id
            }, room=sid)
            
            # Notify other users
            await self.emit("user_joined", {
                "document_id": document_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"doc_{document_id}", skip_sid=sid)
            
            logger.info(f"User {user_id} joined document {document_id}")
            
        except Exception as e:
            logger.error(f"Join document error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to join document"}, room=sid)
            
    async def on_leave_document(self, sid: str, data: Dict[str, Any]):
        """Leave a document room"""
        try:
            user_id = self.session_users.get(sid)
            document_id = data.get("document_id")
            
            if user_id and document_id:
                await self._leave_document_room(sid, document_id, user_id)
                
        except Exception as e:
            logger.error(f"Leave document error for {sid}: {e}")
            
    async def _leave_document_room(self, sid: str, document_id: str, user_id: str):
        """Helper to leave document room"""
        try:
            # Leave WebSocket room
            await self.leave_room(sid, f"doc_{document_id}")
            
            # Remove from tracking
            if document_id in self.document_rooms and sid in self.document_rooms[document_id]:
                self.document_rooms[document_id].remove(sid)
                
                # Clean up if no more sessions
                if not self.document_rooms[document_id]:
                    del self.document_rooms[document_id]
                    if document_id in self.user_cursors:
                        del self.user_cursors[document_id]
                    if document_id in self.active_selections:
                        del self.active_selections[document_id]
                        
            # Remove user cursor
            if document_id in self.user_cursors and user_id in self.user_cursors[document_id]:
                del self.user_cursors[document_id][user_id]
                
            # Remove active selection
            if document_id in self.active_selections and user_id in self.active_selections[document_id]:
                del self.active_selections[document_id][user_id]
            
            # Notify other users
            await self.emit("user_left", {
                "document_id": document_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"doc_{document_id}")
            
            logger.info(f"User {user_id} left document {document_id}")
            
        except Exception as e:
            logger.error(f"Leave document room error: {e}")
            
    async def on_create_annotation(self, sid: str, data: Dict[str, Any]):
        """Handle real-time annotation creation"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
            
            # Create annotation
            annotation = await self.annotation_manager.create_annotation(data, user_id)
            document_id = str(annotation["document_id"])
            
            # Broadcast to all users in document
            await self.emit("annotation_created", {
                "annotation": annotation,
                "created_by": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"doc_{document_id}")
            
            logger.info(f"Real-time annotation created {annotation['id']} by {user_id}")
            
        except Exception as e:
            logger.error(f"Create annotation error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to create annotation"}, room=sid)
            
    async def on_update_annotation(self, sid: str, data: Dict[str, Any]):
        """Handle real-time annotation updates"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
            
            annotation_id = data.get("annotation_id")
            updates = data.get("updates", {})
            
            if not annotation_id:
                await self.emit("error", {"message": "annotation_id required"}, room=sid)
                return
            
            # Update annotation
            annotation = await self.annotation_manager.update_annotation(
                annotation_id, updates, user_id
            )
            document_id = str(annotation["document_id"])
            
            # Broadcast to all users in document
            await self.emit("annotation_updated", {
                "annotation": annotation,
                "updated_by": user_id,
                "updates": updates,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"doc_{document_id}")
            
            logger.info(f"Real-time annotation updated {annotation_id} by {user_id}")
            
        except Exception as e:
            logger.error(f"Update annotation error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to update annotation"}, room=sid)
            
    async def on_delete_annotation(self, sid: str, data: Dict[str, Any]):
        """Handle real-time annotation deletion"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                await self.emit("error", {"message": "User not authenticated"}, room=sid)
                return
            
            annotation_id = data.get("annotation_id")
            if not annotation_id:
                await self.emit("error", {"message": "annotation_id required"}, room=sid)
                return
            
            # Get annotation before deletion for document_id
            annotation = await self.annotation_manager.get_annotation(annotation_id)
            if not annotation:
                await self.emit("error", {"message": "Annotation not found"}, room=sid)
                return
                
            document_id = str(annotation["document_id"])
            
            # Delete annotation
            await self.annotation_manager.delete_annotation(annotation_id, user_id)
            
            # Broadcast to all users in document
            await self.emit("annotation_deleted", {
                "annotation_id": annotation_id,
                "document_id": document_id,
                "deleted_by": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, room=f"doc_{document_id}")
            
            logger.info(f"Real-time annotation deleted {annotation_id} by {user_id}")
            
        except Exception as e:
            logger.error(f"Delete annotation error for {sid}: {e}")
            await self.emit("error", {"message": "Failed to delete annotation"}, room=sid)
            
    async def on_cursor_move(self, sid: str, data: Dict[str, Any]):
        """Handle cursor movement for presence awareness"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                return
                
            document_id = data.get("document_id")
            cursor_data = data.get("cursor_data", {})
            
            if document_id and document_id in self.user_cursors:
                # Update cursor position
                self.user_cursors[document_id][user_id] = {
                    "position": cursor_data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Broadcast cursor position to other users
                await self.emit("cursor_moved", {
                    "document_id": document_id,
                    "user_id": user_id,
                    "cursor_data": cursor_data
                }, room=f"doc_{document_id}", skip_sid=sid)
                
        except Exception as e:
            logger.error(f"Cursor move error for {sid}: {e}")
            
    async def on_text_selection(self, sid: str, data: Dict[str, Any]):
        """Handle text selection for presence awareness"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                return
                
            document_id = data.get("document_id")
            selection_data = data.get("selection_data", {})
            
            if document_id and document_id in self.active_selections:
                # Update selection
                if selection_data:  # Active selection
                    self.active_selections[document_id][user_id] = {
                        "selection": selection_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:  # Clear selection
                    if user_id in self.active_selections[document_id]:
                        del self.active_selections[document_id][user_id]
                
                # Broadcast selection to other users
                await self.emit("selection_changed", {
                    "document_id": document_id,
                    "user_id": user_id,
                    "selection_data": selection_data
                }, room=f"doc_{document_id}", skip_sid=sid)
                
        except Exception as e:
            logger.error(f"Text selection error for {sid}: {e}")
            
    async def on_typing_start(self, sid: str, data: Dict[str, Any]):
        """Handle typing indicators"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                return
                
            document_id = data.get("document_id")
            annotation_id = data.get("annotation_id")  # For annotation comments
            
            # Broadcast typing indicator
            await self.emit("user_typing", {
                "document_id": document_id,
                "annotation_id": annotation_id,
                "user_id": user_id,
                "is_typing": True
            }, room=f"doc_{document_id}", skip_sid=sid)
            
        except Exception as e:
            logger.error(f"Typing start error for {sid}: {e}")
            
    async def on_typing_stop(self, sid: str, data: Dict[str, Any]):
        """Handle end of typing"""
        try:
            user_id = self.session_users.get(sid)
            if not user_id:
                return
                
            document_id = data.get("document_id")
            annotation_id = data.get("annotation_id")
            
            # Broadcast stop typing
            await self.emit("user_typing", {
                "document_id": document_id,
                "annotation_id": annotation_id,
                "user_id": user_id,
                "is_typing": False
            }, room=f"doc_{document_id}", skip_sid=sid)
            
        except Exception as e:
            logger.error(f"Typing stop error for {sid}: {e}")
            
    async def broadcast_annotation_event(self, document_id: str, event_type: str, 
                                       event_data: Dict[str, Any]):
        """Broadcast annotation event to all users in document"""
        try:
            await self.emit(event_type, event_data, room=f"doc_{document_id}")
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            
    def get_document_users(self, document_id: str) -> Set[str]:
        """Get active users in a document"""
        users = set()
        if document_id in self.document_rooms:
            for session_id in self.document_rooms[document_id]:
                if session_id in self.session_users:
                    users.add(self.session_users[session_id])
        return users
        
    def get_user_presence_info(self, document_id: str) -> Dict[str, Any]:
        """Get presence information for a document"""
        return {
            "active_users": list(self.get_document_users(document_id)),
            "cursors": self.user_cursors.get(document_id, {}),
            "selections": self.active_selections.get(document_id, {}),
            "total_sessions": len(self.document_rooms.get(document_id, set()))
        }