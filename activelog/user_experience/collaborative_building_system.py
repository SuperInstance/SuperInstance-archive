"""
Real-time Collaborative Building System for SuperInstance
Enables multiple developers to work together on app assembly in real-time
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
import threading
from datetime import datetime

class CollaborationEventType(Enum):
    COMPONENT_ADD = "component_add"
    COMPONENT_REMOVE = "component_remove"
    COMPONENT_MODIFY = "component_modify"
    COMPONENT_MOVE = "component_move"
    CONNECTION_ADD = "connection_add"
    CONNECTION_REMOVE = "connection_remove"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    CHAT_MESSAGE = "chat_message"
    BUILD_START = "build_start"
    BUILD_COMPLETE = "build_complete"

@dataclass
class CollaborationEvent:
    event_type: CollaborationEventType
    user_id: str
    user_name: str
    timestamp: float
    data: Dict[str, Any]
    session_id: str

@dataclass
class ActiveUser:
    user_id: str
    user_name: str
    color: str
    cursor_position: Dict[str, float]
    selected_components: List[str]
    last_activity: float
    permissions: Set[str]

class ConflictResolutionStrategy(Enum):
    TIMESTAMP_WINS = "timestamp_wins"
    USER_PRIORITY = "user_priority"
    MERGE_CHANGES = "merge_changes"
    MANUAL_RESOLUTION = "manual_resolution"

class CollaborativeSession:
    def __init__(self, session_id: str, project_name: str):
        self.session_id = session_id
        self.project_name = project_name
        self.active_users: Dict[str, ActiveUser] = {}
        self.event_history: List[CollaborationEvent] = []
        self.current_state: Dict[str, Any] = {
            "components": {},
            "connections": {},
            "configuration": {}
        }
        self.locks: Dict[str, str] = {}  # component_id -> user_id
        self.websocket_connections: Dict[str, Any] = {}
        self.conflict_queue: List[Dict[str, Any]] = []
        
    async def add_user(self, user_id: str, user_name: str, websocket):
        """Add a new user to the collaborative session"""
        color = self._generate_user_color(user_id)
        user = ActiveUser(
            user_id=user_id,
            user_name=user_name,
            color=color,
            cursor_position={"x": 0, "y": 0},
            selected_components=[],
            last_activity=time.time(),
            permissions={"read", "write", "comment"}
        )
        
        self.active_users[user_id] = user
        self.websocket_connections[user_id] = websocket
        
        # Send current state to new user
        await self._send_to_user(user_id, {
            "type": "initial_state",
            "state": self.current_state,
            "active_users": {uid: asdict(u) for uid, u in self.active_users.items()},
            "your_user_id": user_id
        })
        
        # Notify other users
        await self._broadcast_event(CollaborationEvent(
            event_type=CollaborationEventType.CURSOR_MOVE,
            user_id="system",
            user_name="System",
            timestamp=time.time(),
            data={"user_joined": user_name, "user_id": user_id},
            session_id=self.session_id
        ), exclude_user=user_id)
    
    async def remove_user(self, user_id: str):
        """Remove user from session and release their locks"""
        if user_id in self.active_users:
            # Release all locks held by this user
            locks_to_release = [comp_id for comp_id, lock_user in self.locks.items() if lock_user == user_id]
            for comp_id in locks_to_release:
                del self.locks[comp_id]
            
            user_name = self.active_users[user_id].user_name
            del self.active_users[user_id]
            if user_id in self.websocket_connections:
                del self.websocket_connections[user_id]
            
            # Notify remaining users
            await self._broadcast_event(CollaborationEvent(
                event_type=CollaborationEventType.CURSOR_MOVE,
                user_id="system",
                user_name="System",
                timestamp=time.time(),
                data={"user_left": user_name, "user_id": user_id, "released_locks": locks_to_release},
                session_id=self.session_id
            ))
    
    async def handle_event(self, event: CollaborationEvent) -> bool:
        """Process collaboration event and apply to session state"""
        # Check permissions
        if not self._has_permission(event.user_id, "write") and event.event_type not in [CollaborationEventType.CURSOR_MOVE, CollaborationEventType.CHAT_MESSAGE]:
            return False
        
        # Check for conflicts
        conflict = self._detect_conflict(event)
        if conflict:
            await self._handle_conflict(event, conflict)
            return False
        
        # Apply event to state
        success = await self._apply_event_to_state(event)
        if success:
            self.event_history.append(event)
            await self._broadcast_event(event)
            self._update_user_activity(event.user_id)
        
        return success
    
    def _detect_conflict(self, event: CollaborationEvent) -> Optional[Dict[str, Any]]:
        """Detect if event conflicts with current state or other users' actions"""
        if event.event_type in [CollaborationEventType.COMPONENT_MODIFY, CollaborationEventType.COMPONENT_REMOVE]:
            component_id = event.data.get("component_id")
            if component_id and component_id in self.locks:
                if self.locks[component_id] != event.user_id:
                    return {
                        "type": "component_locked",
                        "component_id": component_id,
                        "locked_by": self.locks[component_id]
                    }
        
        # Check for simultaneous modifications
        recent_events = [e for e in self.event_history[-10:] if time.time() - e.timestamp < 2.0]
        for recent_event in recent_events:
            if (recent_event.user_id != event.user_id and 
                recent_event.event_type == event.event_type and
                recent_event.data.get("component_id") == event.data.get("component_id")):
                return {
                    "type": "simultaneous_modification",
                    "conflicting_event": recent_event
                }
        
        return None
    
    async def _handle_conflict(self, event: CollaborationEvent, conflict: Dict[str, Any]):
        """Handle detected conflicts based on resolution strategy"""
        self.conflict_queue.append({
            "event": event,
            "conflict": conflict,
            "timestamp": time.time()
        })
        
        # Notify users about conflict
        await self._send_to_user(event.user_id, {
            "type": "conflict_detected",
            "conflict": conflict,
            "event": asdict(event)
        })
        
        # Auto-resolve based on strategy
        if conflict["type"] == "component_locked":
            await self._send_to_user(event.user_id, {
                "type": "action_blocked",
                "reason": f"Component is being edited by {self.active_users.get(conflict['locked_by'], {}).get('user_name', 'another user')}"
            })
    
    async def _apply_event_to_state(self, event: CollaborationEvent) -> bool:
        """Apply the event to the session state"""
        try:
            if event.event_type == CollaborationEventType.COMPONENT_ADD:
                component_id = event.data["component_id"]
                self.current_state["components"][component_id] = event.data["component"]
                self.locks[component_id] = event.user_id
                
            elif event.event_type == CollaborationEventType.COMPONENT_REMOVE:
                component_id = event.data["component_id"]
                if component_id in self.current_state["components"]:
                    del self.current_state["components"][component_id]
                if component_id in self.locks:
                    del self.locks[component_id]
                    
            elif event.event_type == CollaborationEventType.COMPONENT_MODIFY:
                component_id = event.data["component_id"]
                if component_id in self.current_state["components"]:
                    self.current_state["components"][component_id].update(event.data["changes"])
                    
            elif event.event_type == CollaborationEventType.COMPONENT_MOVE:
                component_id = event.data["component_id"]
                if component_id in self.current_state["components"]:
                    self.current_state["components"][component_id]["position"] = event.data["new_position"]
                    
            elif event.event_type == CollaborationEventType.CONNECTION_ADD:
                connection_id = event.data["connection_id"]
                self.current_state["connections"][connection_id] = event.data["connection"]
                
            elif event.event_type == CollaborationEventType.CONNECTION_REMOVE:
                connection_id = event.data["connection_id"]
                if connection_id in self.current_state["connections"]:
                    del self.current_state["connections"][connection_id]
                    
            elif event.event_type == CollaborationEventType.CURSOR_MOVE:
                if event.user_id in self.active_users:
                    self.active_users[event.user_id].cursor_position = event.data["position"]
                    
            elif event.event_type == CollaborationEventType.SELECTION_CHANGE:
                if event.user_id in self.active_users:
                    self.active_users[event.user_id].selected_components = event.data["selected_components"]
            
            return True
            
        except Exception as e:
            print(f"Error applying event: {e}")
            return False
    
    async def _broadcast_event(self, event: CollaborationEvent, exclude_user: Optional[str] = None):
        """Broadcast event to all connected users"""
        message = {
            "type": "collaboration_event",
            "event": asdict(event),
            "active_users": {uid: asdict(u) for uid, u in self.active_users.items()}
        }
        
        for user_id, websocket in self.websocket_connections.items():
            if user_id != exclude_user:
                try:
                    await websocket.send(json.dumps(message))
                except:
                    # Connection lost, remove user
                    asyncio.create_task(self.remove_user(user_id))
    
    async def _send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if user_id in self.websocket_connections:
            try:
                await self.websocket_connections[user_id].send(json.dumps(message))
            except:
                asyncio.create_task(self.remove_user(user_id))
    
    def _generate_user_color(self, user_id: str) -> str:
        """Generate consistent color for user"""
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"]
        return colors[hash(user_id) % len(colors)]
    
    def _has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission"""
        if user_id in self.active_users:
            return permission in self.active_users[user_id].permissions
        return False
    
    def _update_user_activity(self, user_id: str):
        """Update user's last activity timestamp"""
        if user_id in self.active_users:
            self.active_users[user_id].last_activity = time.time()

class CollaborativeBuildingSystem:
    def __init__(self):
        self.active_sessions: Dict[str, CollaborativeSession] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.websocket_server = None
        
    async def create_session(self, session_id: str, project_name: str, creator_id: str) -> CollaborativeSession:
        """Create new collaborative session"""
        session = CollaborativeSession(session_id, project_name)
        self.active_sessions[session_id] = session
        return session
    
    async def join_session(self, session_id: str, user_id: str, user_name: str, websocket) -> bool:
        """Join existing collaborative session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        await session.add_user(user_id, user_name, websocket)
        self.user_sessions[user_id] = session_id
        return True
    
    async def leave_session(self, user_id: str):
        """Leave current collaborative session"""
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            if session_id in self.active_sessions:
                await self.active_sessions[session_id].remove_user(user_id)
            del self.user_sessions[user_id]
    
    async def handle_websocket_message(self, websocket, message: str):
        """Handle incoming websocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "join_session":
                success = await self.join_session(
                    data["session_id"],
                    data["user_id"],
                    data["user_name"],
                    websocket
                )
                await websocket.send(json.dumps({
                    "type": "join_result",
                    "success": success
                }))
                
            elif message_type == "collaboration_event":
                user_id = data["user_id"]
                if user_id in self.user_sessions:
                    session_id = self.user_sessions[user_id]
                    if session_id in self.active_sessions:
                        event = CollaborationEvent(**data["event"])
                        await self.active_sessions[session_id].handle_event(event)
                        
        except Exception as e:
            print(f"Error handling websocket message: {e}")
    
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start the collaboration websocket server"""
        async def handle_client(websocket, path):
            try:
                async for message in websocket:
                    await self.handle_websocket_message(websocket, message)
            except websockets.exceptions.ConnectionClosed:
                # Find user by websocket and remove them
                for user_id, session_id in list(self.user_sessions.items()):
                    if session_id in self.active_sessions:
                        session = self.active_sessions[session_id]
                        if user_id in session.websocket_connections and session.websocket_connections[user_id] == websocket:
                            await self.leave_session(user_id)
                            break
        
        print(f"Starting collaboration server on {host}:{port}")
        self.websocket_server = await websockets.serve(handle_client, host, port)
        return self.websocket_server

# Example usage and integration
class CollaborationIntegration:
    """Integration layer for collaborative building with existing systems"""
    
    def __init__(self, collaboration_system: CollaborativeBuildingSystem):
        self.collaboration_system = collaboration_system
    
    async def integrate_with_visual_assembly(self, visual_assembly_engine):
        """Integrate with visual assembly interface"""
        def on_component_change(component_id, component_data, user_id):
            event = CollaborationEvent(
                event_type=CollaborationEventType.COMPONENT_MODIFY,
                user_id=user_id,
                user_name=self._get_user_name(user_id),
                timestamp=time.time(),
                data={
                    "component_id": component_id,
                    "changes": component_data
                },
                session_id=self._get_session_id(user_id)
            )
            asyncio.create_task(self._handle_event(event))
        
        visual_assembly_engine.on_component_change = on_component_change
    
    async def integrate_with_conversational_builder(self, conversational_builder):
        """Integrate with conversational app builder"""
        def on_conversation_action(action, user_id, data):
            event_type_map = {
                "add_component": CollaborationEventType.COMPONENT_ADD,
                "remove_component": CollaborationEventType.COMPONENT_REMOVE,
                "modify_component": CollaborationEventType.COMPONENT_MODIFY
            }
            
            if action in event_type_map:
                event = CollaborationEvent(
                    event_type=event_type_map[action],
                    user_id=user_id,
                    user_name=self._get_user_name(user_id),
                    timestamp=time.time(),
                    data=data,
                    session_id=self._get_session_id(user_id)
                )
                asyncio.create_task(self._handle_event(event))
        
        conversational_builder.on_action = on_conversation_action
    
    def _get_user_name(self, user_id: str) -> str:
        """Get user name from user ID"""
        for session in self.collaboration_system.active_sessions.values():
            if user_id in session.active_users:
                return session.active_users[user_id].user_name
        return f"User_{user_id[:8]}"
    
    def _get_session_id(self, user_id: str) -> str:
        """Get session ID for user"""
        return self.collaboration_system.user_sessions.get(user_id, "")
    
    async def _handle_event(self, event: CollaborationEvent):
        """Handle collaboration event"""
        session_id = event.session_id
        if session_id in self.collaboration_system.active_sessions:
            await self.collaboration_system.active_sessions[session_id].handle_event(event)

if __name__ == "__main__":
    # Example usage
    async def main():
        collaboration_system = CollaborativeBuildingSystem()
        
        # Create a session
        session = await collaboration_system.create_session("project_123", "My App", "user_1")
        
        # Start the server
        server = await collaboration_system.start_server("localhost", 8765)
        
        # Keep server running
        await server.wait_closed()
    
    # Run with: python -m asyncio collaborative_building_system.main