#!/usr/bin/env python3
"""
ActiveLog Real-Time Event System - WebSocket Hub
Supports 10,000+ concurrent connections with event namespacing
"""

import asyncio
import json
import logging
import time
import weakref
from typing import Dict, Set, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict
import uuid
import websockets
import websockets.server
from websockets.exceptions import ConnectionClosed, WebSocketException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ClientConnection:
    """Represents a connected client"""
    id: str
    websocket: Any
    user_id: Optional[str] = None
    namespaces: Set[str] = None
    rooms: Set[str] = None
    last_activity: float = 0
    bandwidth_profile: str = "medium"  # low, medium, high
    cursor_position: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.namespaces is None:
            self.namespaces = set()
        if self.rooms is None:
            self.rooms = set()
        if self.cursor_position is None:
            self.cursor_position = {}
        self.last_activity = time.time()

@dataclass 
class Event:
    """Real-time event structure"""
    id: str
    type: str
    namespace: str
    room: Optional[str] = None
    data: Dict[str, Any] = None
    sender_id: Optional[str] = None
    timestamp: float = 0
    priority: int = 1  # 1=high, 2=medium, 3=low
    persistent: bool = False
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.timestamp == 0:
            self.timestamp = time.time()

class WebSocketHub:
    """High-performance WebSocket hub for real-time events"""
    
    def __init__(self, host: str = "localhost", port: int = 8101):
        self.host = host
        self.port = port
        
        # Connection management
        self.connections: Dict[str, ClientConnection] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        self.namespace_connections: Dict[str, Set[str]] = defaultdict(set)
        self.room_connections: Dict[str, Set[str]] = defaultdict(set)
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Performance tracking
        self.stats = {
            "connections_active": 0,
            "connections_total": 0,
            "events_sent": 0,
            "events_received": 0,
            "bandwidth_usage": 0,
            "start_time": time.time()
        }
        
        # Connection limits and throttling
        self.max_connections = 12000
        self.rate_limits = {
            "default": {"messages": 100, "window": 60},
            "premium": {"messages": 500, "window": 60}
        }
        
        # Weak references for cleanup
        self._cleanup_refs = weakref.WeakSet()
        
        logger.info(f"WebSocket Hub initialized for {host}:{port}")
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"🚀 Starting WebSocket Hub on {self.host}:{self.port}")
        logger.info("📡 Supporting 10,000+ concurrent connections")
        
        # Start background tasks
        asyncio.create_task(self._cleanup_stale_connections())
        asyncio.create_task(self._performance_monitor())
        
        # Start WebSocket server with optimized settings
        server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            max_size=2**16,  # 64KB max message size
            max_queue=2**8,   # 256 message queue
            compression=None, # Disable compression for speed
            ping_interval=30,
            ping_timeout=10,
            close_timeout=10
        )
        
        logger.info("✅ WebSocket Hub is running")
        await server.wait_closed()
    
    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        
        # Check connection limits
        if len(self.connections) >= self.max_connections:
            await websocket.close(code=1013, reason="Server overloaded")
            return
        
        # Create connection
        connection = ClientConnection(
            id=connection_id,
            websocket=websocket
        )
        
        self.connections[connection_id] = connection
        self.stats["connections_active"] += 1
        self.stats["connections_total"] += 1
        
        logger.info(f"New connection: {connection_id} (Total: {len(self.connections)})")
        
        try:
            # Send welcome message
            await self.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="connection.welcome",
                namespace="system",
                data={
                    "connection_id": connection_id,
                    "server_time": time.time(),
                    "features": [
                        "namespacing", "presence", "collaboration", 
                        "cursor_tracking", "activity_feeds", "notifications",
                        "event_replay", "adaptive_streaming", "webrtc"
                    ]
                }
            ))
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(connection_id, message)
                
        except ConnectionClosed:
            logger.info(f"Connection closed: {connection_id}")
        except WebSocketException as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error for {connection_id}: {e}")
        finally:
            await self._cleanup_connection(connection_id)
    
    async def _handle_message(self, connection_id: str, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            connection = self.connections.get(connection_id)
            
            if not connection:
                return
            
            connection.last_activity = time.time()
            self.stats["events_received"] += 1
            
            event_type = data.get("type")
            
            # Handle different message types
            if event_type == "join_namespace":
                await self._handle_join_namespace(connection_id, data)
            elif event_type == "join_room":
                await self._handle_join_room(connection_id, data)
            elif event_type == "leave_room":
                await self._handle_leave_room(connection_id, data)
            elif event_type == "authenticate":
                await self._handle_authentication(connection_id, data)
            elif event_type == "cursor_update":
                await self._handle_cursor_update(connection_id, data)
            elif event_type == "bandwidth_profile":
                await self._handle_bandwidth_profile(connection_id, data)
            else:
                # Forward to event handlers
                await self._dispatch_event(connection_id, data)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {connection_id}")
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
    
    async def _handle_join_namespace(self, connection_id: str, data: Dict[str, Any]):
        """Handle namespace join request"""
        namespace = data.get("namespace")
        if not namespace:
            return
        
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        connection.namespaces.add(namespace)
        self.namespace_connections[namespace].add(connection_id)
        
        logger.info(f"Connection {connection_id} joined namespace: {namespace}")
        
        # Send confirmation
        await self.send_to_connection(connection_id, Event(
            id=str(uuid.uuid4()),
            type="namespace.joined",
            namespace=namespace,
            data={"namespace": namespace}
        ))
    
    async def _handle_join_room(self, connection_id: str, data: Dict[str, Any]):
        """Handle room join request"""
        room = data.get("room")
        namespace = data.get("namespace", "default")
        
        if not room:
            return
        
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        room_key = f"{namespace}:{room}"
        connection.rooms.add(room_key)
        self.room_connections[room_key].add(connection_id)
        
        logger.info(f"Connection {connection_id} joined room: {room_key}")
        
        # Notify others in room
        await self.broadcast_to_room(namespace, room, Event(
            id=str(uuid.uuid4()),
            type="user.joined_room",
            namespace=namespace,
            room=room,
            data={
                "user_id": connection.user_id,
                "connection_id": connection_id
            }
        ), exclude=[connection_id])
    
    async def _handle_leave_room(self, connection_id: str, data: Dict[str, Any]):
        """Handle room leave request"""
        room = data.get("room")
        namespace = data.get("namespace", "default")
        
        if not room:
            return
        
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        room_key = f"{namespace}:{room}"
        
        if room_key in connection.rooms:
            connection.rooms.remove(room_key)
            self.room_connections[room_key].discard(connection_id)
            
            # Notify others in room
            await self.broadcast_to_room(namespace, room, Event(
                id=str(uuid.uuid4()),
                type="user.left_room",
                namespace=namespace,
                room=room,
                data={
                    "user_id": connection.user_id,
                    "connection_id": connection_id
                }
            ), exclude=[connection_id])
    
    async def _handle_authentication(self, connection_id: str, data: Dict[str, Any]):
        """Handle user authentication"""
        user_id = data.get("user_id")
        token = data.get("token")
        
        if not user_id:
            return
        
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        # In production, validate token here
        connection.user_id = user_id
        self.user_connections[user_id].add(connection_id)
        
        logger.info(f"Connection {connection_id} authenticated as user: {user_id}")
        
        # Send authentication success
        await self.send_to_connection(connection_id, Event(
            id=str(uuid.uuid4()),
            type="auth.success",
            namespace="system",
            data={"user_id": user_id}
        ))
    
    async def _handle_cursor_update(self, connection_id: str, data: Dict[str, Any]):
        """Handle cursor position update"""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        cursor_data = data.get("cursor", {})
        document_id = data.get("document_id")
        namespace = data.get("namespace", "default")
        
        connection.cursor_position = cursor_data
        
        # Broadcast cursor update to others in same document
        if document_id:
            room = f"document:{document_id}"
            await self.broadcast_to_room(namespace, room, Event(
                id=str(uuid.uuid4()),
                type="cursor.update",
                namespace=namespace,
                room=room,
                data={
                    "user_id": connection.user_id,
                    "cursor": cursor_data,
                    "document_id": document_id
                },
                sender_id=connection_id
            ), exclude=[connection_id])
    
    async def _handle_bandwidth_profile(self, connection_id: str, data: Dict[str, Any]):
        """Handle bandwidth profile update"""
        profile = data.get("profile", "medium")
        
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        if profile in ["low", "medium", "high"]:
            connection.bandwidth_profile = profile
            logger.info(f"Connection {connection_id} set bandwidth profile: {profile}")
    
    async def _dispatch_event(self, connection_id: str, data: Dict[str, Any]):
        """Dispatch event to registered handlers"""
        event_type = data.get("type")
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler(connection_id, data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        self.event_handlers[event_type].append(handler)
    
    async def send_to_connection(self, connection_id: str, event: Event):
        """Send event to specific connection"""
        connection = self.connections.get(connection_id)
        if not connection:
            return False
        
        try:
            message = json.dumps(asdict(event))
            await connection.websocket.send(message)
            self.stats["events_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Error sending to {connection_id}: {e}")
            return False
    
    async def send_to_user(self, user_id: str, event: Event):
        """Send event to all connections for a user"""
        connection_ids = list(self.user_connections.get(user_id, []))
        
        tasks = []
        for conn_id in connection_ids:
            tasks.append(self.send_to_connection(conn_id, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_namespace(self, namespace: str, event: Event, exclude: List[str] = None):
        """Broadcast event to all connections in namespace"""
        exclude = exclude or []
        connection_ids = [
            conn_id for conn_id in self.namespace_connections.get(namespace, [])
            if conn_id not in exclude
        ]
        
        tasks = []
        for conn_id in connection_ids:
            tasks.append(self.send_to_connection(conn_id, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_room(self, namespace: str, room: str, event: Event, exclude: List[str] = None):
        """Broadcast event to all connections in room"""
        exclude = exclude or []
        room_key = f"{namespace}:{room}"
        connection_ids = [
            conn_id for conn_id in self.room_connections.get(room_key, [])
            if conn_id not in exclude
        ]
        
        tasks = []
        for conn_id in connection_ids:
            tasks.append(self.send_to_connection(conn_id, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_presence_info(self, namespace: str = None, room: str = None) -> Dict[str, Any]:
        """Get presence information"""
        if room and namespace:
            room_key = f"{namespace}:{room}"
            connection_ids = self.room_connections.get(room_key, set())
        elif namespace:
            connection_ids = self.namespace_connections.get(namespace, set())
        else:
            connection_ids = set(self.connections.keys())
        
        users_online = []
        for conn_id in connection_ids:
            connection = self.connections.get(conn_id)
            if connection and connection.user_id:
                users_online.append({
                    "user_id": connection.user_id,
                    "connection_id": conn_id,
                    "last_activity": connection.last_activity,
                    "cursor_position": connection.cursor_position
                })
        
        return {
            "users_online": users_online,
            "total_connections": len(connection_ids),
            "timestamp": time.time()
        }
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection resources"""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        # Remove from all tracking structures
        if connection.user_id:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]
        
        for namespace in connection.namespaces:
            self.namespace_connections[namespace].discard(connection_id)
            if not self.namespace_connections[namespace]:
                del self.namespace_connections[namespace]
        
        for room in connection.rooms:
            self.room_connections[room].discard(connection_id)
            if not self.room_connections[room]:
                del self.room_connections[room]
        
        # Remove connection
        del self.connections[connection_id]
        self.stats["connections_active"] -= 1
        
        logger.info(f"Cleaned up connection: {connection_id}")
    
    async def _cleanup_stale_connections(self):
        """Background task to clean up stale connections"""
        while True:
            try:
                current_time = time.time()
                stale_connections = []
                
                for conn_id, connection in self.connections.items():
                    # Mark as stale if no activity for 5 minutes
                    if current_time - connection.last_activity > 300:
                        stale_connections.append(conn_id)
                
                for conn_id in stale_connections:
                    try:
                        connection = self.connections[conn_id]
                        await connection.websocket.close()
                        await self._cleanup_connection(conn_id)
                        logger.info(f"Cleaned up stale connection: {conn_id}")
                    except Exception as e:
                        logger.error(f"Error cleaning up stale connection {conn_id}: {e}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
    
    async def _performance_monitor(self):
        """Background task to monitor performance"""
        while True:
            try:
                current_time = time.time()
                uptime = current_time - self.stats["start_time"]
                
                logger.info(f"📊 Performance Stats - "
                          f"Active: {self.stats['connections_active']}, "
                          f"Total: {self.stats['connections_total']}, "
                          f"Events Sent: {self.stats['events_sent']}, "
                          f"Events Received: {self.stats['events_received']}, "
                          f"Uptime: {uptime:.1f}s")
                
                await asyncio.sleep(30)  # Report every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    hub = WebSocketHub(port=8101)
    asyncio.run(hub.start_server())