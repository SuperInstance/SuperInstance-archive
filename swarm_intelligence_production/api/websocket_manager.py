"""
WebSocket connection manager for real-time swarm updates
"""

from fastapi import WebSocket
from typing import Dict, List, Set
import asyncio
import json
import uuid


class WebSocketManager:
    """Manage WebSocket connections and broadcasting"""

    def __init__(self):
        # Map of connection_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Map of swarm_id -> List[connection_id]
        self.swarm_subscriptions: Dict[str, Set[str]] = {}
        # Map of connection_id -> Set[event_types]
        self.event_subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, swarm_id: str, websocket: WebSocket) -> str:
        """Register new WebSocket connection"""
        connection_id = f"conn_{uuid.uuid4().hex[:12]}"

        self.active_connections[connection_id] = websocket

        # Subscribe to swarm
        if swarm_id not in self.swarm_subscriptions:
            self.swarm_subscriptions[swarm_id] = set()
        self.swarm_subscriptions[swarm_id].add(connection_id)

        # Default event subscriptions (all events)
        self.event_subscriptions[connection_id] = {
            "agent_status",
            "task_progress",
            "metrics",
            "errors"
        }

        await self.send_to_connection(connection_id, {
            "type": "connected",
            "connection_id": connection_id,
            "swarm_id": swarm_id
        })

        return connection_id

    async def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # Remove from swarm subscriptions
        for swarm_subscriptions in self.swarm_subscriptions.values():
            swarm_subscriptions.discard(connection_id)

        # Remove event subscriptions
        if connection_id in self.event_subscriptions:
            del self.event_subscriptions[connection_id]

    async def disconnect_all(self):
        """Disconnect all WebSocket connections"""
        for connection_id in list(self.active_connections.keys()):
            await self.disconnect(connection_id)

    async def subscribe(self, connection_id: str, events: List[str]):
        """Update event subscriptions for connection"""
        if connection_id in self.event_subscriptions:
            self.event_subscriptions[connection_id] = set(events)

    async def send_to_connection(self, connection_id: str, message: Dict):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error sending to connection {connection_id}: {e}")
                await self.disconnect(connection_id)

    async def broadcast_to_swarm(self, swarm_id: str, message: Dict):
        """Broadcast message to all connections subscribed to swarm"""
        if swarm_id not in self.swarm_subscriptions:
            return

        event_type = message.get("type", "")

        for connection_id in list(self.swarm_subscriptions[swarm_id]):
            # Check if connection is subscribed to this event type
            if connection_id in self.event_subscriptions:
                subscribed_events = self.event_subscriptions[connection_id]
                if event_type in subscribed_events or "*" in subscribed_events:
                    await self.send_to_connection(connection_id, message)

    async def broadcast_to_all(self, message: Dict):
        """Broadcast message to all active connections"""
        for connection_id in list(self.active_connections.keys()):
            await self.send_to_connection(connection_id, message)

    async def send_agent_status(self, swarm_id: str, agent_id: str, status: str):
        """Send agent status update"""
        await self.broadcast_to_swarm(swarm_id, {
            "type": "agent_status",
            "swarm_id": swarm_id,
            "agent_id": agent_id,
            "status": status,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def send_task_progress(self, swarm_id: str, task_id: str, progress: float):
        """Send task progress update"""
        await self.broadcast_to_swarm(swarm_id, {
            "type": "task_progress",
            "swarm_id": swarm_id,
            "task_id": task_id,
            "progress": progress,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def send_metrics(self, swarm_id: str, metrics: Dict):
        """Send metrics update"""
        await self.broadcast_to_swarm(swarm_id, {
            "type": "metrics",
            "swarm_id": swarm_id,
            "metrics": metrics,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def send_error(self, swarm_id: str, error: str):
        """Send error notification"""
        await self.broadcast_to_swarm(swarm_id, {
            "type": "error",
            "swarm_id": swarm_id,
            "error": error,
            "timestamp": asyncio.get_event_loop().time()
        })

    def get_connection_count(self, swarm_id: str = None) -> int:
        """Get number of active connections"""
        if swarm_id:
            return len(self.swarm_subscriptions.get(swarm_id, set()))
        return len(self.active_connections)
