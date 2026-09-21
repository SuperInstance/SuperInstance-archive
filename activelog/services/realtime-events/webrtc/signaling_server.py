#!/usr/bin/env python3
"""
ActiveLog Real-Time Event System - WebRTC Signaling Server
Handles WebRTC signaling for P2P connections
"""

import asyncio
import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

class SignalingMessageType(Enum):
    """Types of WebRTC signaling messages"""
    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice_candidate"
    ROOM_JOIN = "room_join"
    ROOM_LEAVE = "room_leave"
    PEER_JOINED = "peer_joined"
    PEER_LEFT = "peer_left"
    ERROR = "error"

class ConnectionState(Enum):
    """P2P connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"

@dataclass
class SignalingMessage:
    """WebRTC signaling message"""
    id: str
    type: SignalingMessageType
    from_peer: str
    to_peer: Optional[str] = None
    room_id: Optional[str] = None
    data: Dict[str, Any] = None
    timestamp: float = 0
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.timestamp == 0:
            self.timestamp = time.time()

@dataclass
class Peer:
    """WebRTC peer information"""
    id: str
    user_id: str
    room_id: str
    connection_id: str  # WebSocket connection ID
    state: ConnectionState = ConnectionState.CONNECTING
    joined_at: float = 0
    capabilities: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = {}
        if self.metadata is None:
            self.metadata = {}
        if self.joined_at == 0:
            self.joined_at = time.time()

@dataclass
class Room:
    """WebRTC room for P2P connections"""
    id: str
    name: str
    namespace: str = "default"
    max_peers: int = 10
    created_at: float = 0
    created_by: str = ""
    peers: Dict[str, Peer] = None
    room_type: str = "mesh"  # "mesh", "sfu", "mcu"
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.peers is None:
            self.peers = {}
        if self.settings is None:
            self.settings = {}
        if self.created_at == 0:
            self.created_at = time.time()

class WebRTCSignalingServer:
    """WebRTC signaling server for P2P communication"""
    
    def __init__(self):
        # Room management
        self.rooms: Dict[str, Room] = {}
        self.peer_rooms: Dict[str, str] = {}  # peer_id -> room_id
        self.connection_peers: Dict[str, str] = {}  # connection_id -> peer_id
        
        # Message routing
        self.message_handlers: Dict[SignalingMessageType, Callable] = {
            SignalingMessageType.ROOM_JOIN: self._handle_room_join,
            SignalingMessageType.ROOM_LEAVE: self._handle_room_leave,
            SignalingMessageType.OFFER: self._handle_offer,
            SignalingMessageType.ANSWER: self._handle_answer,
            SignalingMessageType.ICE_CANDIDATE: self._handle_ice_candidate,
        }
        
        # Connection tracking
        self.websocket_hub = None  # Will be set by main server
        
        # Statistics
        self.stats = {
            "rooms_created": 0,
            "peers_connected": 0,
            "messages_processed": 0,
            "connections_established": 0,
            "connections_failed": 0
        }
        
        # Background tasks
        self.cleanup_task = None
        self.start_background_tasks()
    
    def set_websocket_hub(self, hub):
        """Set reference to WebSocket hub for message routing"""
        self.websocket_hub = hub
    
    def start_background_tasks(self):
        """Start background tasks"""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_stale_rooms())
    
    async def handle_signaling_message(self, connection_id: str, message_data: Dict[str, Any]):
        """Handle incoming signaling message"""
        try:
            msg_type = SignalingMessageType(message_data.get("type"))
            
            message = SignalingMessage(
                id=message_data.get("id", str(uuid.uuid4())),
                type=msg_type,
                from_peer=message_data.get("from_peer"),
                to_peer=message_data.get("to_peer"),
                room_id=message_data.get("room_id"),
                data=message_data.get("data", {})
            )
            
            # Route to appropriate handler
            handler = self.message_handlers.get(msg_type)
            if handler:
                await handler(connection_id, message)
            else:
                logger.warning(f"No handler for message type: {msg_type}")
            
            self.stats["messages_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error handling signaling message: {e}")
            await self._send_error(connection_id, f"Failed to process message: {e}")
    
    async def _handle_room_join(self, connection_id: str, message: SignalingMessage):
        """Handle room join request"""
        room_id = message.data.get("room_id")
        user_id = message.data.get("user_id")
        peer_capabilities = message.data.get("capabilities", {})
        peer_metadata = message.data.get("metadata", {})
        
        if not room_id or not user_id:
            await self._send_error(connection_id, "room_id and user_id required")
            return
        
        # Create room if it doesn't exist
        if room_id not in self.rooms:
            room = Room(
                id=room_id,
                name=message.data.get("room_name", room_id),
                namespace=message.data.get("namespace", "default"),
                max_peers=message.data.get("max_peers", 10),
                created_by=user_id,
                room_type=message.data.get("room_type", "mesh"),
                settings=message.data.get("room_settings", {})
            )
            self.rooms[room_id] = room
            self.stats["rooms_created"] += 1
            logger.info(f"Created WebRTC room: {room_id}")
        else:
            room = self.rooms[room_id]
        
        # Check if room is full
        if len(room.peers) >= room.max_peers:
            await self._send_error(connection_id, "Room is full")
            return
        
        # Create peer
        peer_id = str(uuid.uuid4())
        peer = Peer(
            id=peer_id,
            user_id=user_id,
            room_id=room_id,
            connection_id=connection_id,
            capabilities=peer_capabilities,
            metadata=peer_metadata
        )
        
        # Add peer to room
        room.peers[peer_id] = peer
        self.peer_rooms[peer_id] = room_id
        self.connection_peers[connection_id] = peer_id
        
        # Notify existing peers about new peer
        await self._broadcast_to_room(room_id, SignalingMessage(
            id=str(uuid.uuid4()),
            type=SignalingMessageType.PEER_JOINED,
            from_peer=peer_id,
            data={
                "peer_id": peer_id,
                "user_id": user_id,
                "capabilities": peer_capabilities,
                "metadata": peer_metadata
            }
        ), exclude_peer=peer_id)
        
        # Send room state to new peer
        existing_peers = [
            {
                "peer_id": p.id,
                "user_id": p.user_id,
                "capabilities": p.capabilities,
                "metadata": p.metadata,
                "state": p.state.value
            }
            for p in room.peers.values() if p.id != peer_id
        ]
        
        await self._send_to_connection(connection_id, SignalingMessage(
            id=str(uuid.uuid4()),
            type=SignalingMessageType.ROOM_JOIN,
            from_peer="server",
            data={
                "success": True,
                "peer_id": peer_id,
                "room_id": room_id,
                "existing_peers": existing_peers,
                "room_settings": room.settings
            }
        ))
        
        self.stats["peers_connected"] += 1
        logger.info(f"Peer {peer_id} joined room {room_id}")
    
    async def _handle_room_leave(self, connection_id: str, message: SignalingMessage):
        """Handle room leave request"""
        peer_id = self.connection_peers.get(connection_id)
        if not peer_id:
            return
        
        await self._remove_peer(peer_id)
    
    async def _handle_offer(self, connection_id: str, message: SignalingMessage):
        """Handle WebRTC offer"""
        await self._relay_message(message)
    
    async def _handle_answer(self, connection_id: str, message: SignalingMessage):
        """Handle WebRTC answer"""
        await self._relay_message(message)
    
    async def _handle_ice_candidate(self, connection_id: str, message: SignalingMessage):
        """Handle ICE candidate"""
        await self._relay_message(message)
    
    async def _relay_message(self, message: SignalingMessage):
        """Relay message to target peer"""
        if not message.to_peer:
            logger.warning("No target peer specified for relay message")
            return
        
        # Find target peer
        room_id = self.peer_rooms.get(message.to_peer)
        if not room_id:
            logger.warning(f"Target peer {message.to_peer} not found")
            return
        
        room = self.rooms.get(room_id)
        if not room:
            logger.warning(f"Room {room_id} not found")
            return
        
        target_peer = room.peers.get(message.to_peer)
        if not target_peer:
            logger.warning(f"Target peer {message.to_peer} not in room")
            return
        
        # Send message to target peer
        await self._send_to_connection(target_peer.connection_id, message)
    
    async def _broadcast_to_room(self, room_id: str, message: SignalingMessage, exclude_peer: str = None):
        """Broadcast message to all peers in room"""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        for peer in room.peers.values():
            if exclude_peer and peer.id == exclude_peer:
                continue
            
            await self._send_to_connection(peer.connection_id, message)
    
    async def _send_to_connection(self, connection_id: str, message: SignalingMessage):
        """Send message to WebSocket connection"""
        if not self.websocket_hub:
            logger.error("WebSocket hub not set")
            return
        
        # Convert message to WebSocket event
        from websocket.websocket_hub import Event
        event = Event(
            id=message.id,
            type="webrtc.signaling",
            namespace="webrtc",
            data={
                "signaling_type": message.type.value,
                "from_peer": message.from_peer,
                "to_peer": message.to_peer,
                "room_id": message.room_id,
                "data": message.data
            },
            timestamp=message.timestamp
        )
        
        await self.websocket_hub.send_to_connection(connection_id, event)
    
    async def _send_error(self, connection_id: str, error_message: str):
        """Send error message to connection"""
        await self._send_to_connection(connection_id, SignalingMessage(
            id=str(uuid.uuid4()),
            type=SignalingMessageType.ERROR,
            from_peer="server",
            data={"error": error_message}
        ))
    
    async def _remove_peer(self, peer_id: str):
        """Remove peer from room"""
        room_id = self.peer_rooms.get(peer_id)
        if not room_id:
            return
        
        room = self.rooms.get(room_id)
        if not room:
            return
        
        peer = room.peers.get(peer_id)
        if not peer:
            return
        
        # Remove peer from tracking
        del room.peers[peer_id]
        del self.peer_rooms[peer_id]
        if peer.connection_id in self.connection_peers:
            del self.connection_peers[peer.connection_id]
        
        # Notify other peers
        await self._broadcast_to_room(room_id, SignalingMessage(
            id=str(uuid.uuid4()),
            type=SignalingMessageType.PEER_LEFT,
            from_peer=peer_id,
            data={
                "peer_id": peer_id,
                "user_id": peer.user_id
            }
        ))
        
        # Clean up empty room
        if not room.peers:
            del self.rooms[room_id]
            logger.info(f"Removed empty WebRTC room: {room_id}")
        
        logger.info(f"Peer {peer_id} left room {room_id}")
    
    async def handle_connection_closed(self, connection_id: str):
        """Handle WebSocket connection closed"""
        peer_id = self.connection_peers.get(connection_id)
        if peer_id:
            await self._remove_peer(peer_id)
    
    def create_room(self, room_id: str, created_by: str, settings: Dict[str, Any] = None) -> Room:
        """Create a new WebRTC room"""
        room = Room(
            id=room_id,
            name=settings.get("name", room_id) if settings else room_id,
            namespace=settings.get("namespace", "default") if settings else "default",
            max_peers=settings.get("max_peers", 10) if settings else 10,
            created_by=created_by,
            room_type=settings.get("room_type", "mesh") if settings else "mesh",
            settings=settings or {}
        )
        
        self.rooms[room_id] = room
        self.stats["rooms_created"] += 1
        
        logger.info(f"Created WebRTC room: {room_id}")
        return room
    
    def get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get room information"""
        room = self.rooms.get(room_id)
        if not room:
            return None
        
        return {
            "id": room.id,
            "name": room.name,
            "namespace": room.namespace,
            "max_peers": room.max_peers,
            "current_peers": len(room.peers),
            "created_at": room.created_at,
            "created_by": room.created_by,
            "room_type": room.room_type,
            "settings": room.settings,
            "peers": [
                {
                    "id": peer.id,
                    "user_id": peer.user_id,
                    "state": peer.state.value,
                    "joined_at": peer.joined_at,
                    "capabilities": peer.capabilities,
                    "metadata": peer.metadata
                }
                for peer in room.peers.values()
            ]
        }
    
    def list_rooms(self, namespace: str = None) -> List[Dict[str, Any]]:
        """List available rooms"""
        rooms = []
        
        for room in self.rooms.values():
            if namespace and room.namespace != namespace:
                continue
            
            rooms.append({
                "id": room.id,
                "name": room.name,
                "namespace": room.namespace,
                "peer_count": len(room.peers),
                "max_peers": room.max_peers,
                "created_at": room.created_at,
                "room_type": room.room_type
            })
        
        return rooms
    
    def get_peer_info(self, peer_id: str) -> Optional[Dict[str, Any]]:
        """Get peer information"""
        room_id = self.peer_rooms.get(peer_id)
        if not room_id:
            return None
        
        room = self.rooms.get(room_id)
        if not room:
            return None
        
        peer = room.peers.get(peer_id)
        if not peer:
            return None
        
        return {
            "id": peer.id,
            "user_id": peer.user_id,
            "room_id": peer.room_id,
            "state": peer.state.value,
            "joined_at": peer.joined_at,
            "capabilities": peer.capabilities,
            "metadata": peer.metadata
        }
    
    async def _cleanup_stale_rooms(self):
        """Background task to clean up stale rooms"""
        while True:
            try:
                current_time = time.time()
                stale_rooms = []
                
                for room_id, room in self.rooms.items():
                    # Remove rooms that have been empty for 1 hour
                    if not room.peers and current_time - room.created_at > 3600:
                        stale_rooms.append(room_id)
                
                for room_id in stale_rooms:
                    del self.rooms[room_id]
                    logger.info(f"Cleaned up stale room: {room_id}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in room cleanup task: {e}")
                await asyncio.sleep(300)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get signaling server statistics"""
        total_peers = sum(len(room.peers) for room in self.rooms.values())
        
        room_types = defaultdict(int)
        for room in self.rooms.values():
            room_types[room.room_type] += 1
        
        return {
            **self.stats,
            "active_rooms": len(self.rooms),
            "total_peers": total_peers,
            "room_types": dict(room_types),
            "average_peers_per_room": total_peers / len(self.rooms) if self.rooms else 0
        }