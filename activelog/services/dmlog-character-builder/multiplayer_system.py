"""
World-Class Real-Time Collaborative Multiplayer Character Creation System
Enterprise-grade real-time synchronization with conflict resolution,
operational transforms, and seamless collaboration features
"""

import asyncio
import websockets
import json
import uuid
import time
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
import threading
from collections import defaultdict
import queue
from abc import ABC, abstractmethod

class OperationType(Enum):
    INSERT = "insert"
    DELETE = "delete" 
    RETAIN = "retain"
    REPLACE = "replace"
    MOVE = "move"

class ConflictStrategy(Enum):
    LAST_WRITER_WINS = "last_writer_wins"
    MERGE_AUTOMATIC = "merge_automatic"
    MERGE_MANUAL = "merge_manual"
    VERSION_FORK = "version_fork"

class UserRole(Enum):
    OWNER = "owner"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"
    MODERATOR = "moderator"

class SessionState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    LOCKED = "locked"

@dataclass
class Operation:
    """Operational Transform operation"""
    op_type: OperationType
    path: List[str]  # JSON path to the field
    value: Any = None
    old_value: Any = None
    position: int = 0
    length: int = 0
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "op_type": self.op_type.value,
            "path": self.path,
            "value": self.value,
            "old_value": self.old_value,
            "position": self.position,
            "length": self.length,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "operation_id": self.operation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Operation':
        return cls(
            op_type=OperationType(data["op_type"]),
            path=data["path"],
            value=data.get("value"),
            old_value=data.get("old_value"),
            position=data.get("position", 0),
            length=data.get("length", 0),
            timestamp=data.get("timestamp", time.time()),
            user_id=data.get("user_id", ""),
            operation_id=data.get("operation_id", str(uuid.uuid4()))
        )

@dataclass
class User:
    """Collaborative session user"""
    user_id: str
    username: str
    role: UserRole
    cursor_position: Dict[str, Any] = field(default_factory=dict)
    selection: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    is_online: bool = True
    avatar_url: str = ""
    color: str = field(default_factory=lambda: f"#{uuid.uuid4().hex[:6]}")

@dataclass
class CollaborativeSession:
    """Real-time collaborative character creation session"""
    session_id: str
    character_id: str
    owner_id: str
    participants: Dict[str, User] = field(default_factory=dict)
    character_data: Dict[str, Any] = field(default_factory=dict)
    operation_history: List[Operation] = field(default_factory=list)
    current_version: int = 0
    state: SessionState = SessionState.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    conflict_strategy: ConflictStrategy = ConflictStrategy.MERGE_AUTOMATIC
    
    # Real-time features
    active_cursors: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    live_selections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    voice_channels: Dict[str, bool] = field(default_factory=dict)
    screen_sharing: Dict[str, str] = field(default_factory=dict)

class OperationalTransform:
    """Advanced Operational Transform engine for conflict-free collaboration"""
    
    def __init__(self):
        self.operation_queue = queue.PriorityQueue()
        self.pending_operations = {}
        self.acknowledged_operations = set()
        
    def transform_operation(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent operations for consistency"""
        
        # If operations affect different paths, no transformation needed
        if not self._paths_intersect(op1.path, op2.path):
            return op1, op2
        
        # Transform based on operation types
        if op1.op_type == OperationType.INSERT and op2.op_type == OperationType.INSERT:
            return self._transform_insert_insert(op1, op2)
        elif op1.op_type == OperationType.DELETE and op2.op_type == OperationType.DELETE:
            return self._transform_delete_delete(op1, op2)
        elif op1.op_type == OperationType.INSERT and op2.op_type == OperationType.DELETE:
            return self._transform_insert_delete(op1, op2)
        elif op1.op_type == OperationType.DELETE and op2.op_type == OperationType.INSERT:
            op2_transformed, op1_transformed = self._transform_insert_delete(op2, op1)
            return op1_transformed, op2_transformed
        elif op1.op_type == OperationType.REPLACE and op2.op_type == OperationType.REPLACE:
            return self._transform_replace_replace(op1, op2)
        else:
            # Generic transformation
            return self._transform_generic(op1, op2)
    
    def _paths_intersect(self, path1: List[str], path2: List[str]) -> bool:
        """Check if two JSON paths intersect"""
        min_len = min(len(path1), len(path2))
        for i in range(min_len):
            if path1[i] != path2[i]:
                return False
        return True
    
    def _transform_insert_insert(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent insert operations"""
        
        if op1.path == op2.path:
            # Same path - adjust positions based on timestamp
            if op1.timestamp < op2.timestamp:
                # op1 happened first, op2 position needs adjustment
                op2_transformed = Operation(
                    op_type=op2.op_type,
                    path=op2.path,
                    value=op2.value,
                    position=op2.position + len(str(op1.value)),
                    timestamp=op2.timestamp,
                    user_id=op2.user_id,
                    operation_id=op2.operation_id
                )
                return op1, op2_transformed
            else:
                # op2 happened first, op1 position needs adjustment
                op1_transformed = Operation(
                    op_type=op1.op_type,
                    path=op1.path,
                    value=op1.value,
                    position=op1.position + len(str(op2.value)),
                    timestamp=op1.timestamp,
                    user_id=op1.user_id,
                    operation_id=op1.operation_id
                )
                return op1_transformed, op2
        
        return op1, op2
    
    def _transform_delete_delete(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent delete operations"""
        
        if op1.path == op2.path:
            # Check for overlapping deletions
            op1_end = op1.position + op1.length
            op2_end = op2.position + op2.length
            
            # If ranges overlap, resolve conflict
            if (op1.position <= op2.position < op1_end) or (op2.position <= op1.position < op2_end):
                # Merge deletions
                start_pos = min(op1.position, op2.position)
                end_pos = max(op1_end, op2_end)
                
                merged_op = Operation(
                    op_type=OperationType.DELETE,
                    path=op1.path,
                    position=start_pos,
                    length=end_pos - start_pos,
                    timestamp=min(op1.timestamp, op2.timestamp),
                    user_id=op1.user_id if op1.timestamp < op2.timestamp else op2.user_id,
                    operation_id=f"merged_{op1.operation_id}_{op2.operation_id}"
                )
                
                # Return merged operation and null operation
                null_op = Operation(
                    op_type=OperationType.RETAIN,
                    path=[],
                    length=0
                )
                
                return merged_op, null_op
        
        return op1, op2
    
    def _transform_insert_delete(self, insert_op: Operation, delete_op: Operation) -> Tuple[Operation, Operation]:
        """Transform insert vs delete operations"""
        
        if insert_op.path == delete_op.path:
            # Adjust delete position if insert happens before it
            if insert_op.position <= delete_op.position:
                delete_transformed = Operation(
                    op_type=delete_op.op_type,
                    path=delete_op.path,
                    position=delete_op.position + len(str(insert_op.value)),
                    length=delete_op.length,
                    timestamp=delete_op.timestamp,
                    user_id=delete_op.user_id,
                    operation_id=delete_op.operation_id
                )
                return insert_op, delete_transformed
        
        return insert_op, delete_op
    
    def _transform_replace_replace(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent replace operations"""
        
        if op1.path == op2.path:
            # Conflict resolution based on timestamp or user priority
            if op1.timestamp < op2.timestamp:
                # op1 wins, op2 becomes no-op
                null_op = Operation(
                    op_type=OperationType.RETAIN,
                    path=op2.path,
                    length=0
                )
                return op1, null_op
            else:
                # op2 wins, op1 becomes no-op
                null_op = Operation(
                    op_type=OperationType.RETAIN,
                    path=op1.path,
                    length=0
                )
                return null_op, op2
        
        return op1, op2
    
    def _transform_generic(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Generic transformation for other operation combinations"""
        
        # For operations on different paths, no transformation needed
        if op1.path != op2.path:
            return op1, op2
        
        # For same path, use timestamp-based precedence
        if op1.timestamp <= op2.timestamp:
            return op1, op2
        else:
            return op2, op1
    
    def apply_operation(self, document: Dict[str, Any], operation: Operation) -> Dict[str, Any]:
        """Apply operation to document"""
        
        result = document.copy()
        
        if operation.op_type == OperationType.REPLACE:
            self._set_nested_value(result, operation.path, operation.value)
        elif operation.op_type == OperationType.DELETE:
            self._delete_nested_value(result, operation.path)
        elif operation.op_type == OperationType.INSERT:
            self._insert_nested_value(result, operation.path, operation.value, operation.position)
        elif operation.op_type == OperationType.MOVE:
            value = self._get_nested_value(result, operation.path)
            self._delete_nested_value(result, operation.path)
            # Move operation would have target path in value
            if isinstance(operation.value, dict) and "target_path" in operation.value:
                self._set_nested_value(result, operation.value["target_path"], value)
        
        return result
    
    def _get_nested_value(self, document: Dict[str, Any], path: List[str]) -> Any:
        """Get nested value from document using path"""
        current = document
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
                current = current[int(key)]
            else:
                return None
        return current
    
    def _set_nested_value(self, document: Dict[str, Any], path: List[str], value: Any):
        """Set nested value in document using path"""
        current = document
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        if path:
            current[path[-1]] = value
    
    def _delete_nested_value(self, document: Dict[str, Any], path: List[str]):
        """Delete nested value from document using path"""
        current = document
        for key in path[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return
        
        if path and isinstance(current, dict) and path[-1] in current:
            del current[path[-1]]
    
    def _insert_nested_value(self, document: Dict[str, Any], path: List[str], 
                           value: Any, position: int):
        """Insert value into nested structure"""
        current = self._get_nested_value(document, path)
        
        if isinstance(current, str):
            # Insert into string
            new_value = current[:position] + str(value) + current[position:]
            self._set_nested_value(document, path, new_value)
        elif isinstance(current, list):
            # Insert into list
            current.insert(position, value)

class ConflictResolver:
    """Advanced conflict resolution system"""
    
    def __init__(self):
        self.resolution_strategies = {
            ConflictStrategy.LAST_WRITER_WINS: self._resolve_last_writer_wins,
            ConflictStrategy.MERGE_AUTOMATIC: self._resolve_automatic_merge,
            ConflictStrategy.MERGE_MANUAL: self._resolve_manual_merge,
            ConflictStrategy.VERSION_FORK: self._resolve_version_fork
        }
    
    def resolve_conflict(self, conflict_data: Dict[str, Any], 
                        strategy: ConflictStrategy) -> Dict[str, Any]:
        """Resolve conflict using specified strategy"""
        
        resolver = self.resolution_strategies.get(strategy, self._resolve_last_writer_wins)
        return resolver(conflict_data)
    
    def _resolve_last_writer_wins(self, conflict_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple last-writer-wins resolution"""
        
        operations = conflict_data.get("operations", [])
        if not operations:
            return conflict_data
        
        # Find operation with latest timestamp
        latest_op = max(operations, key=lambda op: op.get("timestamp", 0))
        
        return {
            "resolution": "last_writer_wins",
            "winning_operation": latest_op,
            "discarded_operations": [op for op in operations if op != latest_op]
        }
    
    def _resolve_automatic_merge(self, conflict_data: Dict[str, Any]) -> Dict[str, Any]:
        """Intelligent automatic merge resolution"""
        
        operations = conflict_data.get("operations", [])
        path = conflict_data.get("path", [])
        
        # For different types of fields, use different merge strategies
        field_type = self._determine_field_type(path)
        
        if field_type == "ability_scores":
            return self._merge_ability_scores(operations)
        elif field_type == "feats":
            return self._merge_lists(operations)
        elif field_type == "equipment":
            return self._merge_equipment(operations)
        else:
            return self._merge_generic(operations)
    
    def _resolve_manual_merge(self, conflict_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mark for manual resolution"""
        
        return {
            "resolution": "manual_required",
            "conflict_id": str(uuid.uuid4()),
            "operations": conflict_data.get("operations", []),
            "requires_user_input": True,
            "merge_options": self._generate_merge_options(conflict_data)
        }
    
    def _resolve_version_fork(self, conflict_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create version fork for conflicting changes"""
        
        operations = conflict_data.get("operations", [])
        
        # Create separate versions for each conflicting operation
        versions = []
        for i, op in enumerate(operations):
            version = {
                "version_id": str(uuid.uuid4()),
                "user_id": op.get("user_id"),
                "timestamp": op.get("timestamp"),
                "operation": op,
                "branch_name": f"version_{i+1}_{op.get('user_id', 'unknown')[:8]}"
            }
            versions.append(version)
        
        return {
            "resolution": "version_fork",
            "versions": versions,
            "merge_required": True
        }
    
    def _determine_field_type(self, path: List[str]) -> str:
        """Determine the type of field being modified"""
        
        if not path:
            return "unknown"
        
        field_mappings = {
            "ability_scores": "ability_scores",
            "feats": "feats",
            "equipment": "equipment",
            "spells": "spells",
            "skills": "skills",
            "name": "text",
            "description": "text",
            "backstory": "text"
        }
        
        for key in path:
            if key in field_mappings:
                return field_mappings[key]
        
        return "generic"
    
    def _merge_ability_scores(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge ability score changes intelligently"""
        
        # For ability scores, average the values if reasonable
        values = [op.get("value", 10) for op in operations if isinstance(op.get("value"), (int, float))]
        
        if values:
            # Use weighted average based on timestamps
            total_weight = 0
            weighted_sum = 0
            
            for op in operations:
                if isinstance(op.get("value"), (int, float)):
                    weight = 1.0 / (time.time() - op.get("timestamp", 0) + 1)  # More recent = higher weight
                    weighted_sum += op["value"] * weight
                    total_weight += weight
            
            merged_value = int(weighted_sum / total_weight) if total_weight > 0 else 10
            
            return {
                "resolution": "automatic_merge",
                "merged_value": max(8, min(20, merged_value)),  # Clamp to valid range
                "merge_method": "weighted_average"
            }
        
        return self._resolve_last_writer_wins({"operations": operations})
    
    def _merge_lists(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge list operations (feats, skills, etc.)"""
        
        merged_list = []
        seen_items = set()
        
        for op in sorted(operations, key=lambda x: x.get("timestamp", 0)):
            value = op.get("value")
            
            if isinstance(value, list):
                for item in value:
                    if item not in seen_items:
                        merged_list.append(item)
                        seen_items.add(item)
            elif value and value not in seen_items:
                merged_list.append(value)
                seen_items.add(value)
        
        return {
            "resolution": "automatic_merge",
            "merged_value": merged_list,
            "merge_method": "union"
        }
    
    def _merge_equipment(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge equipment changes"""
        
        merged_equipment = {}
        
        for op in sorted(operations, key=lambda x: x.get("timestamp", 0)):
            value = op.get("value")
            
            if isinstance(value, dict):
                merged_equipment.update(value)
        
        return {
            "resolution": "automatic_merge",
            "merged_value": merged_equipment,
            "merge_method": "dictionary_merge"
        }
    
    def _merge_generic(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generic merge for unknown field types"""
        
        return self._resolve_last_writer_wins({"operations": operations})
    
    def _generate_merge_options(self, conflict_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate merge options for manual resolution"""
        
        operations = conflict_data.get("operations", [])
        options = []
        
        # Option 1: Accept each individual operation
        for i, op in enumerate(operations):
            options.append({
                "option_id": f"accept_{i}",
                "description": f"Accept changes from {op.get('user_id', 'unknown')}",
                "value": op.get("value"),
                "user_id": op.get("user_id")
            })
        
        # Option 2: Custom merge
        options.append({
            "option_id": "custom",
            "description": "Create custom merged value",
            "value": None,
            "requires_input": True
        })
        
        return options

class RealtimeSync:
    """Real-time synchronization engine"""
    
    def __init__(self):
        self.connected_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.sessions: Dict[str, CollaborativeSession] = {}
        self.operational_transform = OperationalTransform()
        self.conflict_resolver = ConflictResolver()
        self.message_queue = queue.Queue()
        self.heartbeat_interval = 30  # seconds
        
        # Start background tasks
        self.heartbeat_task = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_task.start()
        
        logger = logging.getLogger(__name__)
        logger.info("Real-time sync engine initialized")
    
    async def handle_client_connection(self, websocket, path):
        """Handle new client connection"""
        
        client_id = str(uuid.uuid4())
        self.connected_clients[client_id] = websocket
        
        logger = logging.getLogger(__name__)
        logger.info(f"Client connected: {client_id}")
        
        try:
            await self._handle_client_messages(websocket, client_id)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        finally:
            # Cleanup
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            
            # Remove from active sessions
            for session in self.sessions.values():
                if client_id in session.participants:
                    session.participants[client_id].is_online = False
                    await self._broadcast_user_status_update(session.session_id, client_id, False)
    
    async def _handle_client_messages(self, websocket, client_id: str):
        """Handle messages from connected client"""
        
        async for message in websocket:
            try:
                data = json.loads(message)
                await self._process_client_message(websocket, client_id, data)
            except json.JSONDecodeError as e:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Invalid JSON: {str(e)}"
                }))
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing client message: {str(e)}")
                await websocket.send(json.dumps({
                    "type": "error", 
                    "message": "Internal server error"
                }))
    
    async def _process_client_message(self, websocket, client_id: str, data: Dict[str, Any]):
        """Process individual client message"""
        
        message_type = data.get("type")
        
        if message_type == "join_session":
            await self._handle_join_session(websocket, client_id, data)
        elif message_type == "leave_session":
            await self._handle_leave_session(client_id, data)
        elif message_type == "operation":
            await self._handle_operation(client_id, data)
        elif message_type == "cursor_update":
            await self._handle_cursor_update(client_id, data)
        elif message_type == "voice_toggle":
            await self._handle_voice_toggle(client_id, data)
        elif message_type == "screen_share":
            await self._handle_screen_share(client_id, data)
        elif message_type == "chat_message":
            await self._handle_chat_message(client_id, data)
        elif message_type == "heartbeat":
            await self._handle_heartbeat(websocket, client_id)
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }))
    
    async def _handle_join_session(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle client joining collaborative session"""
        
        session_id = data.get("session_id")
        user_info = data.get("user", {})
        
        if not session_id:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Session ID required"
            }))
            return
        
        # Get or create session
        if session_id not in self.sessions:
            # Create new session
            self.sessions[session_id] = CollaborativeSession(
                session_id=session_id,
                character_id=data.get("character_id", str(uuid.uuid4())),
                owner_id=client_id
            )
        
        session = self.sessions[session_id]
        
        # Create user object
        user = User(
            user_id=client_id,
            username=user_info.get("username", f"User_{client_id[:8]}"),
            role=UserRole.OWNER if client_id == session.owner_id else UserRole.COLLABORATOR,
            avatar_url=user_info.get("avatar_url", ""),
            color=user_info.get("color", f"#{uuid.uuid4().hex[:6]}")
        )
        
        # Add user to session
        session.participants[client_id] = user
        
        # Send session state to new participant
        await websocket.send(json.dumps({
            "type": "session_joined",
            "session_id": session_id,
            "character_data": session.character_data,
            "participants": {uid: asdict(user) for uid, user in session.participants.items()},
            "your_user_id": client_id,
            "session_state": session.state.value
        }))
        
        # Notify other participants
        await self._broadcast_to_session(session_id, {
            "type": "user_joined",
            "user": asdict(user)
        }, exclude_client=client_id)
        
        logger = logging.getLogger(__name__)
        logger.info(f"User {user.username} joined session {session_id}")
    
    async def _handle_leave_session(self, client_id: str, data: Dict[str, Any]):
        """Handle client leaving session"""
        
        session_id = data.get("session_id")
        
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            if client_id in session.participants:
                user = session.participants[client_id]
                del session.participants[client_id]
                
                # Notify other participants
                await self._broadcast_to_session(session_id, {
                    "type": "user_left",
                    "user_id": client_id,
                    "username": user.username
                })
                
                # If session is empty, mark for cleanup
                if not session.participants:
                    session.state = SessionState.ARCHIVED
                
                logger = logging.getLogger(__name__)
                logger.info(f"User {user.username} left session {session_id}")
    
    async def _handle_operation(self, client_id: str, data: Dict[str, Any]):
        """Handle character modification operation"""
        
        session_id = data.get("session_id")
        operation_data = data.get("operation", {})
        
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        # Create operation object
        operation = Operation.from_dict(operation_data)
        operation.user_id = client_id
        
        # Apply operational transform
        transformed_ops = []
        for existing_op in reversed(session.operation_history[-10:]):  # Check last 10 ops
            if existing_op.timestamp > operation.timestamp - 5:  # Within 5 seconds
                operation, existing_transformed = self.operational_transform.transform_operation(
                    operation, existing_op
                )
                transformed_ops.append(existing_transformed)
        
        # Apply operation to character data
        try:
            session.character_data = self.operational_transform.apply_operation(
                session.character_data, operation
            )
            
            # Add to operation history
            session.operation_history.append(operation)
            session.current_version += 1
            session.updated_at = time.time()
            
            # Broadcast operation to other participants
            await self._broadcast_to_session(session_id, {
                "type": "operation_applied",
                "operation": operation.to_dict(),
                "version": session.current_version,
                "character_data": session.character_data
            }, exclude_client=client_id)
            
            logger = logging.getLogger(__name__)
            logger.info(f"Operation applied in session {session_id}: {operation.op_type.value}")
            
        except Exception as e:
            # Operation failed - send error to client
            await self._send_to_client(client_id, {
                "type": "operation_failed",
                "operation_id": operation.operation_id,
                "error": str(e)
            })
    
    async def _handle_cursor_update(self, client_id: str, data: Dict[str, Any]):
        """Handle cursor position update"""
        
        session_id = data.get("session_id")
        cursor_data = data.get("cursor", {})
        
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        if client_id in session.participants:
            # Update cursor position
            session.active_cursors[client_id] = cursor_data
            session.participants[client_id].cursor_position = cursor_data
            session.participants[client_id].last_seen = time.time()
            
            # Broadcast cursor update to other participants
            await self._broadcast_to_session(session_id, {
                "type": "cursor_update",
                "user_id": client_id,
                "cursor": cursor_data
            }, exclude_client=client_id)
    
    async def _handle_voice_toggle(self, client_id: str, data: Dict[str, Any]):
        """Handle voice chat toggle"""
        
        session_id = data.get("session_id")
        voice_enabled = data.get("enabled", False)
        
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        session.voice_channels[client_id] = voice_enabled
        
        # Notify other participants about voice status change
        await self._broadcast_to_session(session_id, {
            "type": "voice_status_changed",
            "user_id": client_id,
            "enabled": voice_enabled
        }, exclude_client=client_id)
    
    async def _handle_screen_share(self, client_id: str, data: Dict[str, Any]):
        """Handle screen sharing"""
        
        session_id = data.get("session_id")
        sharing_enabled = data.get("enabled", False)
        stream_id = data.get("stream_id", "")
        
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        if sharing_enabled:
            session.screen_sharing[client_id] = stream_id
        elif client_id in session.screen_sharing:
            del session.screen_sharing[client_id]
        
        # Notify other participants about screen sharing change
        await self._broadcast_to_session(session_id, {
            "type": "screen_share_changed",
            "user_id": client_id,
            "enabled": sharing_enabled,
            "stream_id": stream_id
        }, exclude_client=client_id)
    
    async def _handle_chat_message(self, client_id: str, data: Dict[str, Any]):
        """Handle chat message"""
        
        session_id = data.get("session_id")
        message = data.get("message", "")
        
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        if client_id in session.participants:
            user = session.participants[client_id]
            
            chat_message = {
                "type": "chat_message",
                "user_id": client_id,
                "username": user.username,
                "message": message,
                "timestamp": time.time(),
                "color": user.color
            }
            
            # Broadcast chat message to all participants
            await self._broadcast_to_session(session_id, chat_message)
    
    async def _handle_heartbeat(self, websocket, client_id: str):
        """Handle heartbeat from client"""
        
        # Update last seen time for user
        for session in self.sessions.values():
            if client_id in session.participants:
                session.participants[client_id].last_seen = time.time()
        
        # Send heartbeat response
        await websocket.send(json.dumps({
            "type": "heartbeat_ack",
            "timestamp": time.time()
        }))
    
    async def _broadcast_to_session(self, session_id: str, message: Dict[str, Any], 
                                  exclude_client: str = None):
        """Broadcast message to all participants in session"""
        
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        message_json = json.dumps(message)
        
        for client_id in session.participants:
            if client_id != exclude_client and client_id in self.connected_clients:
                try:
                    websocket = self.connected_clients[client_id]
                    await websocket.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    # Mark user as offline
                    session.participants[client_id].is_online = False
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending message to client {client_id}: {str(e)}")
    
    async def _send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        
        if client_id in self.connected_clients:
            try:
                websocket = self.connected_clients[client_id]
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                # Remove disconnected client
                if client_id in self.connected_clients:
                    del self.connected_clients[client_id]
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending message to client {client_id}: {str(e)}")
    
    async def _broadcast_user_status_update(self, session_id: str, user_id: str, is_online: bool):
        """Broadcast user online/offline status update"""
        
        await self._broadcast_to_session(session_id, {
            "type": "user_status_changed",
            "user_id": user_id,
            "is_online": is_online,
            "timestamp": time.time()
        })
    
    def _heartbeat_loop(self):
        """Background heartbeat loop to detect disconnected clients"""
        
        while True:
            try:
                current_time = time.time()
                
                # Check for inactive users
                for session in list(self.sessions.values()):
                    for client_id, user in list(session.participants.items()):
                        if current_time - user.last_seen > self.heartbeat_interval * 2:
                            # Mark user as offline
                            if user.is_online:
                                user.is_online = False
                                asyncio.run(self._broadcast_user_status_update(
                                    session.session_id, client_id, False
                                ))
                
                # Cleanup empty sessions
                empty_sessions = [
                    sid for sid, session in self.sessions.items()
                    if not any(user.is_online for user in session.participants.values())
                ]
                
                for session_id in empty_sessions:
                    if self.sessions[session_id].state == SessionState.ACTIVE:
                        self.sessions[session_id].state = SessionState.ARCHIVED
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error in heartbeat loop: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get real-time session statistics"""
        
        total_sessions = len(self.sessions)
        active_sessions = len([s for s in self.sessions.values() if s.state == SessionState.ACTIVE])
        total_participants = sum(len(s.participants) for s in self.sessions.values())
        online_participants = sum(
            len([u for u in s.participants.values() if u.is_online]) 
            for s in self.sessions.values()
        )
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "archived_sessions": total_sessions - active_sessions,
            "total_participants": total_participants,
            "online_participants": online_participants,
            "connected_clients": len(self.connected_clients),
            "average_session_size": total_participants / max(total_sessions, 1),
            "operation_stats": {
                "total_operations": sum(len(s.operation_history) for s in self.sessions.values()),
                "recent_operations": sum(
                    len([op for op in s.operation_history if time.time() - op.timestamp < 300])
                    for s in self.sessions.values()
                )
            }
        }

class MultiplayerCharacterBuilder:
    """Main multiplayer character builder orchestrator"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.sync_engine = RealtimeSync()
        self.server = None
        
        logger = logging.getLogger(__name__)
        logger.info(f"Multiplayer character builder initialized on port {port}")
    
    async def start_server(self):
        """Start the WebSocket server"""
        
        logger = logging.getLogger(__name__)
        logger.info(f"Starting multiplayer server on port {self.port}")
        
        self.server = await websockets.serve(
            self.sync_engine.handle_client_connection,
            "localhost",
            self.port,
            ping_interval=30,
            ping_timeout=10
        )
        
        logger.info(f"Multiplayer server started on ws://localhost:{self.port}")
        
        # Keep server running
        await self.server.wait_closed()
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
            logger = logging.getLogger(__name__)
            logger.info("Multiplayer server stopped")
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get server status and statistics"""
        
        stats = self.sync_engine.get_session_statistics()
        
        return {
            "server_running": self.server is not None,
            "port": self.port,
            "uptime": time.time(),  # Would track actual uptime
            "sessions": stats
        }

# Export main classes
__all__ = [
    "MultiplayerCharacterBuilder", 
    "RealtimeSync", 
    "OperationalTransform",
    "ConflictResolver",
    "CollaborativeSession",
    "User",
    "Operation"
]