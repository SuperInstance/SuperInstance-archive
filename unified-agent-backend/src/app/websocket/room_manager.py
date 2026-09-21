"""
Room manager for WebSocket subscriptions.

This module provides room-based subscription management for WebSocket connections,
allowing clients to subscribe to specific topics and receive targeted updates.
"""

import asyncio
from typing import Dict, List, Set, Any, Optional
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class Room:
    """
    Represents a subscription room for WebSocket connections.

    A room groups connections that are interested in the same topic,
    such as workflow executions, agent updates, or workflow status.
    """

    def __init__(self, room_id: str, room_type: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a room.

        Args:
            room_id: Unique room identifier
            room_type: Type of room (execution, agent, workflow, etc.)
            metadata: Optional room metadata
        """
        self.room_id = room_id
        self.room_type = room_type
        self.metadata = metadata or {}
        self.connections: Set[str] = set()  # connection_ids
        self.created_at = asyncio.get_event_loop().time()
        self.message_count = 0

    def add_connection(self, connection_id: str) -> None:
        """Add a connection to this room."""
        self.connections.add(connection_id)

    def remove_connection(self, connection_id: str) -> None:
        """Remove a connection from this room."""
        self.connections.discard(connection_id)

    def has_connection(self, connection_id: str) -> bool:
        """Check if a connection is in this room."""
        return connection_id in self.connections

    @property
    def connection_count(self) -> int:
        """Get the number of connections in this room."""
        return len(self.connections)

    @property
    def is_empty(self) -> bool:
        """Check if the room has no connections."""
        return len(self.connections) == 0


class RoomManager:
    """
    Manages WebSocket room subscriptions and message broadcasting.

    Provides room-based subscription management allowing clients to subscribe
    to specific topics and receive targeted updates.
    """

    def __init__(self, cleanup_interval: int = 300):
        """
        Initialize room manager.

        Args:
            cleanup_interval: Interval in seconds for cleaning up empty rooms
        """
        self.rooms: Dict[str, Room] = {}
        self.connection_rooms: Dict[str, Set[str]] = {}  # connection_id -> room_ids
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_room(
        self,
        room_id: str,
        room_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False
    ) -> Room:
        """
        Create a new room.

        Args:
            room_id: Unique room identifier
            room_type: Type of room
            metadata: Optional room metadata
            overwrite: Whether to overwrite existing room

        Returns:
            Room: Created room instance

        Raises:
            ValueError: If room already exists and overwrite is False
        """
        if room_id in self.rooms and not overwrite:
            raise ValueError(f"Room {room_id} already exists")

        room = Room(room_id, room_type, metadata)
        self.rooms[room_id] = room
        logger.info(f"Created room: {room_id} (type: {room_type})")
        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        """
        Get a room by ID.

        Args:
            room_id: Room ID

        Returns:
            Room or None if not found
        """
        return self.rooms.get(room_id)

    def delete_room(self, room_id: str) -> None:
        """
        Delete a room and remove all connections from it.

        Args:
            room_id: Room ID to delete
        """
        room = self.rooms.get(room_id)
        if not room:
            return

        # Remove room from all connections
        for connection_id in room.connections:
            conn_rooms = self.connection_rooms.get(connection_id, set())
            conn_rooms.discard(room_id)
            if not conn_rooms:
                del self.connection_rooms[connection_id]

        # Delete room
        del self.rooms[room_id]
        logger.info(f"Deleted room: {room_id}")

    async def subscribe_connection(
        self,
        connection_id: str,
        room_id: str,
        room_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Subscribe a connection to a room.

        Args:
            connection_id: Connection ID
            room_id: Room ID
            room_type: Type of room
            metadata: Optional room metadata

        Returns:
            bool: True if subscription was successful
        """
        try:
            # Create room if it doesn't exist
            if room_id not in self.rooms:
                self.create_room(room_id, room_type, metadata)

            # Add connection to room
            room = self.rooms[room_id]
            room.add_connection(connection_id)

            # Track room for connection
            if connection_id not in self.connection_rooms:
                self.connection_rooms[connection_id] = set()
            self.connection_rooms[connection_id].add(room_id)

            logger.debug(f"Connection {connection_id} subscribed to room {room_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe connection {connection_id} to room {room_id}: {str(e)}")
            return False

    async def unsubscribe_connection(self, connection_id: str, room_id: str) -> bool:
        """
        Unsubscribe a connection from a room.

        Args:
            connection_id: Connection ID
            room_id: Room ID

        Returns:
            bool: True if unsubscription was successful
        """
        try:
            room = self.rooms.get(room_id)
            if not room:
                return False

            # Remove connection from room
            room.remove_connection(connection_id)

            # Remove room from connection tracking
            conn_rooms = self.connection_rooms.get(connection_id)
            if conn_rooms:
                conn_rooms.discard(room_id)
                if not conn_rooms:
                    del self.connection_rooms[connection_id]

            # Log room stats
            logger.debug(f"Connection {connection_id} unsubscribed from room {room_id}")
            logger.debug(f"Room {room_id} now has {room.connection_count} connections")

            # Schedule room cleanup if empty
            if room.is_empty:
                asyncio.create_task(self._maybe_cleanup_room(room_id))

            return True

        except Exception as e:
            logger.error(f"Failed to unsubscribe connection {connection_id} from room {room_id}: {str(e)}")
            return False

    async def unsubscribe_connection_from_all_rooms(self, connection_id: str) -> int:
        """
        Unsubscribe a connection from all rooms.

        Args:
            connection_id: Connection ID

        Returns:
            int: Number of rooms unsubscribed from
        """
        room_ids = list(self.connection_rooms.get(connection_id, set()))
        unsubscribed_count = 0

        for room_id in room_ids:
            if await self.unsubscribe_connection(connection_id, room_id):
                unsubscribed_count += 1

        return unsubscribed_count

    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        message_type: str = "broadcast",
        connection_manager = None
    ) -> int:
        """
        Broadcast a message to all connections in a room.

        Args:
            room_id: Room ID to broadcast to
            message: Message content
            message_type: Type of message
            connection_manager: Connection manager for sending messages

        Returns:
            int: Number of connections message was sent to
        """
        room = self.rooms.get(room_id)
        if not room or room.is_empty:
            return 0

        sent_count = 0
        room.message_count += 1

        # Broadcast to all connections in the room
        if connection_manager:
            for connection_id in list(room.connections):  # Copy to avoid modification during iteration
                message_data = {
                    "room_id": room_id,
                    "room_type": room.room_type,
                    "room_metadata": room.metadata,
                    **message
                }
                if await connection_manager.send_message(connection_id, message_data, message_type):
                    sent_count += 1

        logger.debug(f"Broadcast message to {sent_count} connections in room {room_id}")
        return sent_count

    def get_connection_rooms(self, connection_id: str) -> List[Room]:
        """
        Get all rooms a connection is subscribed to.

        Args:
            connection_id: Connection ID

        Returns:
            List of Room objects
        """
        room_ids = self.connection_rooms.get(connection_id, set())
        return [self.rooms[room_id] for room_id in room_ids if room_id in self.rooms]

    def get_rooms_by_type(self, room_type: str) -> List[Room]:
        """
        Get all rooms of a specific type.

        Args:
            room_type: Type of room

        Returns:
            List of Room objects
        """
        return [room for room in self.rooms.values() if room.room_type == room_type]

    def get_room_stats(self) -> Dict[str, Any]:
        """
        Get room statistics.

        Returns:
            Dictionary with room statistics
        """
        total_rooms = len(self.rooms)
        total_subscriptions = sum(room.connection_count for room in self.rooms.values())
        rooms_by_type = {}

        for room in self.rooms.values():
            room_type = room.room_type
            if room_type not in rooms_by_type:
                rooms_by_type[room_type] = {"count": 0, "connections": 0, "messages": 0}
            rooms_by_type[room_type]["count"] += 1
            rooms_by_type[room_type]["connections"] += room.connection_count
            rooms_by_type[room_type]["messages"] += room.message_count

        return {
            "total_rooms": total_rooms,
            "total_subscriptions": total_subscriptions,
            "rooms_by_type": rooms_by_type,
            "average_connections_per_room": total_subscriptions / total_rooms if total_rooms > 0 else 0
        }

    async def _maybe_cleanup_room(self, room_id: str) -> None:
        """
        Clean up a room if it's empty and old enough.

        Args:
            room_id: Room ID to potentially clean up
        """
        # Wait a bit before cleanup to avoid race conditions
        await asyncio.sleep(5)

        room = self.rooms.get(room_id)
        if room and room.is_empty:
            logger.info(f"Cleaning up empty room: {room_id}")
            self.delete_room(room_id)

    async def cleanup_loop(self) -> None:
        """Background task to clean up empty rooms."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)

                empty_rooms = [
                    room_id for room_id, room in self.rooms.items()
                    if room.is_empty
                ]

                for room_id in empty_rooms:
                    self.delete_room(room_id)

                if empty_rooms:
                    logger.info(f"Cleaned up {len(empty_rooms)} empty rooms")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in room cleanup loop: {str(e)}")

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self.cleanup_loop())

    async def shutdown(self) -> None:
        """Shutdown the room manager."""
        logger.info("Shutting down room manager...")

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

        # Clear all rooms and connections
        self.rooms.clear()
        self.connection_rooms.clear()

        logger.info("Room manager shutdown complete")