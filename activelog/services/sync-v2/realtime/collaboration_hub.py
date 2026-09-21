#!/usr/bin/env python3
"""
ActiveLog.ai Real-time Collaboration Hub

Operational transforms, presence management, and live collaborative editing.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import websockets
import weakref

class OperationType(Enum):
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"
    REPLACE = "replace"
    MOVE = "move"
    FORMAT = "format"

class CursorType(Enum):
    TEXT = "text"
    SELECTION = "selection"
    POINTER = "pointer"

@dataclass
class Operation:
    """Single operation in operational transform"""
    op_id: str
    op_type: OperationType
    position: int
    content: Optional[str] = None
    length: Optional[int] = None
    attributes: Optional[Dict[str, Any]] = None
    timestamp: str = None
    author_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class OperationBatch:
    """Batch of operations that should be applied atomically"""
    batch_id: str
    operations: List[Operation]
    document_id: str
    author_id: str
    timestamp: str
    base_revision: int
    target_revision: int

@dataclass
class CursorPosition:
    """User cursor/selection position"""
    user_id: str
    cursor_type: CursorType
    position: int
    selection_end: Optional[int] = None
    attributes: Optional[Dict[str, Any]] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class UserPresence:
    """User presence information"""
    user_id: str
    user_name: str
    user_avatar: Optional[str]
    color: str
    is_active: bool
    last_seen: str
    cursor_position: Optional[CursorPosition] = None
    connection_id: Optional[str] = None
    device_info: Optional[Dict[str, str]] = None

@dataclass
class CollaborationSession:
    """Active collaboration session"""
    session_id: str
    document_id: str
    created_at: str
    participants: Dict[str, UserPresence]
    current_revision: int = 0
    operation_history: List[OperationBatch] = None
    
    def __post_init__(self):
        if self.operation_history is None:
            self.operation_history = []

class OperationalTransform:
    """Operational Transform implementation for conflict-free collaboration"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def transform_operation(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent operations"""
        # Create copies to avoid modifying originals
        transformed_op1 = self._copy_operation(op1)
        transformed_op2 = self._copy_operation(op2)
        
        # Transform based on operation types
        if op1.op_type == OperationType.INSERT and op2.op_type == OperationType.INSERT:
            transformed_op1, transformed_op2 = self._transform_insert_insert(op1, op2)
        
        elif op1.op_type == OperationType.INSERT and op2.op_type == OperationType.DELETE:
            transformed_op1, transformed_op2 = self._transform_insert_delete(op1, op2)
        
        elif op1.op_type == OperationType.DELETE and op2.op_type == OperationType.INSERT:
            transformed_op2, transformed_op1 = self._transform_insert_delete(op2, op1)
        
        elif op1.op_type == OperationType.DELETE and op2.op_type == OperationType.DELETE:
            transformed_op1, transformed_op2 = self._transform_delete_delete(op1, op2)
        
        elif op1.op_type == OperationType.REPLACE and op2.op_type == OperationType.REPLACE:
            transformed_op1, transformed_op2 = self._transform_replace_replace(op1, op2)
        
        else:
            # For other combinations, use position-based transformation
            transformed_op1, transformed_op2 = self._transform_by_position(op1, op2)
        
        return transformed_op1, transformed_op2
    
    def _transform_insert_insert(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent insert operations"""
        pos1, pos2 = op1.position, op2.position
        
        if pos1 <= pos2:
            # op1 comes before op2, adjust op2's position
            new_op1 = self._copy_operation(op1)
            new_op2 = self._copy_operation(op2)
            new_op2.position = pos2 + len(op1.content or "")
        else:
            # op2 comes before op1, adjust op1's position
            new_op1 = self._copy_operation(op1)
            new_op2 = self._copy_operation(op2)
            new_op1.position = pos1 + len(op2.content or "")
        
        return new_op1, new_op2
    
    def _transform_insert_delete(self, insert_op: Operation, delete_op: Operation) -> Tuple[Operation, Operation]:
        """Transform insert and delete operations"""
        insert_pos = insert_op.position
        delete_pos = delete_op.position
        delete_len = delete_op.length or 0
        
        new_insert = self._copy_operation(insert_op)
        new_delete = self._copy_operation(delete_op)
        
        if insert_pos <= delete_pos:
            # Insert comes before delete, adjust delete position
            new_delete.position = delete_pos + len(insert_op.content or "")
        elif insert_pos >= delete_pos + delete_len:
            # Insert comes after delete, adjust insert position
            new_insert.position = insert_pos - delete_len
        else:
            # Insert is within delete range, split delete
            # This is a complex case that might need special handling
            new_delete.position = delete_pos
            new_insert.position = delete_pos
        
        return new_insert, new_delete
    
    def _transform_delete_delete(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent delete operations"""
        pos1, len1 = op1.position, op1.length or 0
        pos2, len2 = op2.position, op2.length or 0
        
        new_op1 = self._copy_operation(op1)
        new_op2 = self._copy_operation(op2)
        
        # Check for overlap
        end1 = pos1 + len1
        end2 = pos2 + len2
        
        if end1 <= pos2:
            # op1 comes completely before op2
            new_op2.position = pos2 - len1
        elif end2 <= pos1:
            # op2 comes completely before op1
            new_op1.position = pos1 - len2
        else:
            # Overlapping deletes - need to handle carefully
            overlap_start = max(pos1, pos2)
            overlap_end = min(end1, end2)
            overlap_len = max(0, overlap_end - overlap_start)
            
            if pos1 <= pos2:
                new_op1.length = len1 - overlap_len
                new_op2.position = pos1 + new_op1.length
                new_op2.length = len2 - overlap_len
            else:
                new_op2.length = len2 - overlap_len
                new_op1.position = pos2 + new_op2.length
                new_op1.length = len1 - overlap_len
        
        return new_op1, new_op2
    
    def _transform_replace_replace(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent replace operations"""
        # For overlapping replaces, the later one wins (by timestamp)
        if op1.timestamp and op2.timestamp:
            if op1.timestamp > op2.timestamp:
                # op1 wins, op2 becomes no-op
                return self._copy_operation(op1), self._create_noop(op2)
            else:
                # op2 wins, op1 becomes no-op
                return self._create_noop(op1), self._copy_operation(op2)
        
        # If no timestamps, use position to decide
        return self._transform_by_position(op1, op2)
    
    def _transform_by_position(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Generic position-based transformation"""
        # Simplified transformation based on position
        new_op1 = self._copy_operation(op1)
        new_op2 = self._copy_operation(op2)
        
        # Adjust positions based on the other operation's effect
        if op1.position > op2.position:
            effect = self._calculate_position_effect(op2)
            new_op1.position += effect
        
        if op2.position > op1.position:
            effect = self._calculate_position_effect(op1)
            new_op2.position += effect
        
        return new_op1, new_op2
    
    def _calculate_position_effect(self, op: Operation) -> int:
        """Calculate how an operation affects positions after it"""
        if op.op_type == OperationType.INSERT:
            return len(op.content or "")
        elif op.op_type == OperationType.DELETE:
            return -(op.length or 0)
        elif op.op_type == OperationType.REPLACE:
            return len(op.content or "") - (op.length or 0)
        else:
            return 0
    
    def _copy_operation(self, op: Operation) -> Operation:
        """Create a copy of an operation"""
        return Operation(
            op_id=op.op_id,
            op_type=op.op_type,
            position=op.position,
            content=op.content,
            length=op.length,
            attributes=op.attributes.copy() if op.attributes else None,
            timestamp=op.timestamp,
            author_id=op.author_id
        )
    
    def _create_noop(self, original_op: Operation) -> Operation:
        """Create a no-op operation"""
        return Operation(
            op_id=original_op.op_id,
            op_type=OperationType.RETAIN,
            position=original_op.position,
            length=0,
            timestamp=original_op.timestamp,
            author_id=original_op.author_id
        )
    
    def transform_batch(self, batch1: OperationBatch, batch2: OperationBatch) -> Tuple[OperationBatch, OperationBatch]:
        """Transform two operation batches"""
        if batch1.document_id != batch2.document_id:
            # Different documents, no transformation needed
            return batch1, batch2
        
        # Transform each operation in batch1 against all operations in batch2
        transformed_ops1 = []
        transformed_ops2 = list(batch2.operations)
        
        for op1 in batch1.operations:
            current_op1 = op1
            new_transformed_ops2 = []
            
            for i, op2 in enumerate(transformed_ops2):
                transformed_op1, transformed_op2 = self.transform_operation(current_op1, op2)
                current_op1 = transformed_op1
                new_transformed_ops2.append(transformed_op2)
            
            transformed_ops1.append(current_op1)
            transformed_ops2 = new_transformed_ops2
        
        # Create new batches
        new_batch1 = OperationBatch(
            batch_id=batch1.batch_id,
            operations=transformed_ops1,
            document_id=batch1.document_id,
            author_id=batch1.author_id,
            timestamp=batch1.timestamp,
            base_revision=batch1.base_revision,
            target_revision=batch1.target_revision
        )
        
        new_batch2 = OperationBatch(
            batch_id=batch2.batch_id,
            operations=transformed_ops2,
            document_id=batch2.document_id,
            author_id=batch2.author_id,
            timestamp=batch2.timestamp,
            base_revision=batch2.base_revision,
            target_revision=batch2.target_revision
        )
        
        return new_batch1, new_batch2

class PresenceManager:
    """Manage user presence and cursor positions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user_sessions: Dict[str, UserPresence] = {}
        self.document_sessions: Dict[str, Set[str]] = {}  # document_id -> set of user_ids
        self.presence_callbacks: List[Callable] = []
    
    def add_user(self, session_id: str, user_presence: UserPresence):
        """Add user to presence tracking"""
        self.user_sessions[session_id] = user_presence
        
        # Update document sessions
        for doc_id in user_presence.device_info.get('active_documents', []):
            if doc_id not in self.document_sessions:
                self.document_sessions[doc_id] = set()
            self.document_sessions[doc_id].add(session_id)
        
        self._notify_presence_change('user_joined', user_presence)
        self.logger.info(f"User {user_presence.user_name} joined session {session_id}")
    
    def remove_user(self, session_id: str):
        """Remove user from presence tracking"""
        if session_id in self.user_sessions:
            user_presence = self.user_sessions[session_id]
            
            # Remove from document sessions
            for doc_sessions in self.document_sessions.values():
                doc_sessions.discard(session_id)
            
            del self.user_sessions[session_id]
            
            self._notify_presence_change('user_left', user_presence)
            self.logger.info(f"User {user_presence.user_name} left session {session_id}")
    
    def update_cursor(self, session_id: str, cursor_position: CursorPosition):
        """Update user cursor position"""
        if session_id in self.user_sessions:
            user_presence = self.user_sessions[session_id]
            user_presence.cursor_position = cursor_position
            user_presence.last_seen = datetime.now().isoformat()
            
            self._notify_presence_change('cursor_updated', user_presence)
    
    def update_activity(self, session_id: str, is_active: bool = True):
        """Update user activity status"""
        if session_id in self.user_sessions:
            user_presence = self.user_sessions[session_id]
            user_presence.is_active = is_active
            user_presence.last_seen = datetime.now().isoformat()
            
            self._notify_presence_change('activity_updated', user_presence)
    
    def get_document_participants(self, document_id: str) -> List[UserPresence]:
        """Get all users currently viewing/editing a document"""
        if document_id not in self.document_sessions:
            return []
        
        participants = []
        for session_id in self.document_sessions[document_id]:
            if session_id in self.user_sessions:
                participants.append(self.user_sessions[session_id])
        
        return participants
    
    def get_user_presence(self, session_id: str) -> Optional[UserPresence]:
        """Get presence information for a user"""
        return self.user_sessions.get(session_id)
    
    def cleanup_stale_sessions(self, timeout_minutes: int = 5):
        """Remove stale user sessions"""
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        stale_sessions = []
        
        for session_id, presence in self.user_sessions.items():
            last_seen = datetime.fromisoformat(presence.last_seen)
            if last_seen < cutoff_time:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            self.remove_user(session_id)
    
    def on_presence_change(self, callback: Callable):
        """Register callback for presence changes"""
        self.presence_callbacks.append(callback)
    
    def _notify_presence_change(self, event_type: str, user_presence: UserPresence):
        """Notify all callbacks of presence changes"""
        for callback in self.presence_callbacks:
            try:
                callback(event_type, user_presence)
            except Exception as e:
                self.logger.error(f"Presence callback error: {e}")

class CollaborationHub:
    """Central hub for real-time collaboration"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.operational_transform = OperationalTransform()
        self.presence_manager = PresenceManager()
        
        # Active sessions
        self.collaboration_sessions: Dict[str, CollaborationSession] = {}
        self.websocket_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Operation queues for each document
        self.operation_queues: Dict[str, List[OperationBatch]] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Configuration
        self.max_operation_history = self.config.get('max_operation_history', 1000)
        self.presence_timeout_minutes = self.config.get('presence_timeout_minutes', 5)
        
        # Setup presence callbacks
        self.presence_manager.on_presence_change(self._handle_presence_change)
    
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start WebSocket server for real-time collaboration"""
        self.logger.info(f"Starting collaboration server on {host}:{port}")
        
        async def handle_client(websocket, path):
            await self._handle_websocket_connection(websocket, path)
        
        server = await websockets.serve(handle_client, host, port)
        
        # Start background tasks
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        try:
            await server.wait_closed()
        finally:
            cleanup_task.cancel()
    
    async def _handle_websocket_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        self.websocket_connections[connection_id] = websocket
        
        try:
            await websocket.send(json.dumps({
                "type": "connection_established",
                "connection_id": connection_id
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_websocket_message(connection_id, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
                except Exception as e:
                    self.logger.error(f"Message handling error: {e}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Cleanup connection
            if connection_id in self.websocket_connections:
                del self.websocket_connections[connection_id]
            
            # Remove user presence
            self.presence_manager.remove_user(connection_id)
    
    async def _handle_websocket_message(self, connection_id: str, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        message_type = data.get('type')
        
        if message_type == 'join_session':
            await self._handle_join_session(connection_id, data)
        
        elif message_type == 'leave_session':
            await self._handle_leave_session(connection_id, data)
        
        elif message_type == 'operation_batch':
            await self._handle_operation_batch(connection_id, data)
        
        elif message_type == 'cursor_update':
            await self._handle_cursor_update(connection_id, data)
        
        elif message_type == 'presence_update':
            await self._handle_presence_update(connection_id, data)
        
        else:
            await self._send_to_connection(connection_id, {
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })
    
    async def _handle_join_session(self, connection_id: str, data: Dict[str, Any]):
        """Handle user joining collaboration session"""
        document_id = data.get('document_id')
        user_info = data.get('user_info', {})
        
        if not document_id:
            await self._send_to_connection(connection_id, {
                "type": "error",
                "message": "document_id required"
            })
            return
        
        # Create or get collaboration session
        session = await self._get_or_create_session(document_id)
        
        # Create user presence
        user_presence = UserPresence(
            user_id=user_info.get('user_id', f'anonymous_{connection_id}'),
            user_name=user_info.get('user_name', 'Anonymous'),
            user_avatar=user_info.get('user_avatar'),
            color=user_info.get('color', '#007AFF'),
            is_active=True,
            last_seen=datetime.now().isoformat(),
            connection_id=connection_id,
            device_info=user_info.get('device_info', {})
        )
        
        # Add to session and presence manager
        session.participants[connection_id] = user_presence
        self.presence_manager.add_user(connection_id, user_presence)
        
        # Send session info to user
        await self._send_to_connection(connection_id, {
            "type": "session_joined",
            "session_id": session.session_id,
            "document_id": document_id,
            "current_revision": session.current_revision,
            "participants": [asdict(p) for p in session.participants.values()]
        })
        
        # Notify other participants
        await self._broadcast_to_session(session.session_id, {
            "type": "user_joined",
            "user": asdict(user_presence)
        }, exclude_connection=connection_id)
    
    async def _handle_leave_session(self, connection_id: str, data: Dict[str, Any]):
        """Handle user leaving collaboration session"""
        session_id = data.get('session_id')
        
        if session_id and session_id in self.collaboration_sessions:
            session = self.collaboration_sessions[session_id]
            
            if connection_id in session.participants:
                user_presence = session.participants[connection_id]
                del session.participants[connection_id]
                
                # Notify other participants
                await self._broadcast_to_session(session_id, {
                    "type": "user_left",
                    "user": asdict(user_presence)
                }, exclude_connection=connection_id)
                
                # Remove empty sessions
                if not session.participants:
                    del self.collaboration_sessions[session_id]
        
        # Remove from presence manager
        self.presence_manager.remove_user(connection_id)
    
    async def _handle_operation_batch(self, connection_id: str, data: Dict[str, Any]):
        """Handle operation batch from client"""
        try:
            # Parse operation batch
            batch_data = data.get('batch')
            if not batch_data:
                raise ValueError("Missing operation batch")
            
            # Create operation batch object
            operations = []
            for op_data in batch_data.get('operations', []):
                operation = Operation(
                    op_id=op_data['op_id'],
                    op_type=OperationType(op_data['op_type']),
                    position=op_data['position'],
                    content=op_data.get('content'),
                    length=op_data.get('length'),
                    attributes=op_data.get('attributes'),
                    timestamp=op_data.get('timestamp'),
                    author_id=op_data.get('author_id')
                )
                operations.append(operation)
            
            batch = OperationBatch(
                batch_id=batch_data['batch_id'],
                operations=operations,
                document_id=batch_data['document_id'],
                author_id=batch_data['author_id'],
                timestamp=batch_data['timestamp'],
                base_revision=batch_data['base_revision'],
                target_revision=batch_data['target_revision']
            )
            
            # Process the batch
            await self._process_operation_batch(batch, connection_id)
            
        except Exception as e:
            self.logger.error(f"Operation batch processing error: {e}")
            await self._send_to_connection(connection_id, {
                "type": "operation_error",
                "message": str(e)
            })
    
    async def _process_operation_batch(self, batch: OperationBatch, source_connection: str):
        """Process operation batch with operational transform"""
        document_id = batch.document_id
        
        # Get or create operation queue for document
        if document_id not in self.operation_queues:
            self.operation_queues[document_id] = []
        
        operation_queue = self.operation_queues[document_id]
        
        # Transform against concurrent operations
        transformed_batch = batch
        for queued_batch in operation_queue:
            if queued_batch.author_id != batch.author_id:
                transformed_batch, _ = self.operational_transform.transform_batch(
                    transformed_batch, queued_batch
                )
        
        # Add to queue
        operation_queue.append(transformed_batch)
        
        # Update session revision
        session = await self._get_or_create_session(document_id)
        session.current_revision += 1
        transformed_batch.target_revision = session.current_revision
        
        # Add to session history
        session.operation_history.append(transformed_batch)
        
        # Limit history size
        if len(session.operation_history) > self.max_operation_history:
            session.operation_history.pop(0)
        
        # Broadcast to all participants except sender
        await self._broadcast_to_session(session.session_id, {
            "type": "operation_batch",
            "batch": {
                "batch_id": transformed_batch.batch_id,
                "operations": [asdict(op) for op in transformed_batch.operations],
                "document_id": transformed_batch.document_id,
                "author_id": transformed_batch.author_id,
                "timestamp": transformed_batch.timestamp,
                "base_revision": transformed_batch.base_revision,
                "target_revision": transformed_batch.target_revision
            }
        }, exclude_connection=source_connection)
        
        # Send acknowledgment to sender
        await self._send_to_connection(source_connection, {
            "type": "operation_acknowledged",
            "batch_id": transformed_batch.batch_id,
            "new_revision": transformed_batch.target_revision
        })
    
    async def _handle_cursor_update(self, connection_id: str, data: Dict[str, Any]):
        """Handle cursor position update"""
        cursor_data = data.get('cursor')
        if cursor_data:
            cursor_position = CursorPosition(
                user_id=cursor_data['user_id'],
                cursor_type=CursorType(cursor_data['cursor_type']),
                position=cursor_data['position'],
                selection_end=cursor_data.get('selection_end'),
                attributes=cursor_data.get('attributes')
            )
            
            # Update presence
            self.presence_manager.update_cursor(connection_id, cursor_position)
            
            # Find session and broadcast to other participants
            for session in self.collaboration_sessions.values():
                if connection_id in session.participants:
                    await self._broadcast_to_session(session.session_id, {
                        "type": "cursor_update",
                        "cursor": asdict(cursor_position)
                    }, exclude_connection=connection_id)
                    break
    
    async def _handle_presence_update(self, connection_id: str, data: Dict[str, Any]):
        """Handle presence status update"""
        is_active = data.get('is_active', True)
        self.presence_manager.update_activity(connection_id, is_active)
    
    async def _get_or_create_session(self, document_id: str) -> CollaborationSession:
        """Get existing or create new collaboration session"""
        session_id = f"session_{document_id}"
        
        if session_id not in self.collaboration_sessions:
            session = CollaborationSession(
                session_id=session_id,
                document_id=document_id,
                created_at=datetime.now().isoformat(),
                participants={}
            )
            self.collaboration_sessions[session_id] = session
        
        return self.collaboration_sessions[session_id]
    
    async def _broadcast_to_session(self, session_id: str, message: Dict[str, Any],
                                   exclude_connection: str = None):
        """Broadcast message to all participants in session"""
        if session_id not in self.collaboration_sessions:
            return
        
        session = self.collaboration_sessions[session_id]
        
        for connection_id in session.participants:
            if connection_id != exclude_connection:
                await self._send_to_connection(connection_id, message)
    
    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send message to specific connection"""
        if connection_id in self.websocket_connections:
            try:
                websocket = self.websocket_connections[connection_id]
                await websocket.send(json.dumps(message))
            except Exception as e:
                self.logger.error(f"Failed to send message to {connection_id}: {e}")
                # Remove dead connection
                if connection_id in self.websocket_connections:
                    del self.websocket_connections[connection_id]
                self.presence_manager.remove_user(connection_id)
    
    def _handle_presence_change(self, event_type: str, user_presence: UserPresence):
        """Handle presence change events"""
        # Find session and broadcast presence update
        for session in self.collaboration_sessions.values():
            if user_presence.connection_id in session.participants:
                asyncio.create_task(self._broadcast_to_session(session.session_id, {
                    "type": "presence_update",
                    "event": event_type,
                    "user": asdict(user_presence)
                }))
                break
    
    async def _cleanup_loop(self):
        """Background cleanup of stale sessions and connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Cleanup stale presence sessions
                self.presence_manager.cleanup_stale_sessions(self.presence_timeout_minutes)
                
                # Cleanup empty collaboration sessions
                empty_sessions = [
                    session_id for session_id, session in self.collaboration_sessions.items()
                    if not session.participants
                ]
                
                for session_id in empty_sessions:
                    del self.collaboration_sessions[session_id]
                    if session_id in self.operation_queues:
                        del self.operation_queues[session_id]
                
                # Cleanup operation queues (keep only recent operations)
                cutoff_time = datetime.now() - timedelta(hours=1)
                for doc_id in self.operation_queues:
                    queue = self.operation_queues[doc_id]
                    self.operation_queues[doc_id] = [
                        batch for batch in queue
                        if datetime.fromisoformat(batch.timestamp) > cutoff_time
                    ]
                
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get collaboration statistics"""
        total_participants = sum(len(session.participants) for session in self.collaboration_sessions.values())
        
        return {
            "active_sessions": len(self.collaboration_sessions),
            "total_participants": total_participants,
            "websocket_connections": len(self.websocket_connections),
            "operation_queues": len(self.operation_queues),
            "sessions": [
                {
                    "session_id": session.session_id,
                    "document_id": session.document_id,
                    "participants": len(session.participants),
                    "current_revision": session.current_revision,
                    "operation_history_size": len(session.operation_history)
                }
                for session in self.collaboration_sessions.values()
            ]
        }

async def main():
    """Example usage of collaboration hub"""
    # Create collaboration hub
    hub = CollaborationHub({
        'max_operation_history': 500,
        'presence_timeout_minutes': 3
    })
    
    # Start server
    print("Starting collaboration server on localhost:8765")
    await hub.start_server("localhost", 8765)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())