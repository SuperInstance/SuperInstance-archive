"""
WebSocket package for real-time updates.

This package provides WebSocket functionality for real-time communication
including connection management, room-based subscriptions, and message broadcasting.
"""

from .manager import WebSocketManager
from .connection_manager import ConnectionManager
from .room_manager import RoomManager
from .auth import WebSocketAuth

__all__ = [
    "WebSocketManager",
    "ConnectionManager",
    "RoomManager",
    "WebSocketAuth",
]