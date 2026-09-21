"""
Connection manager for WebSocket connections.

This module provides connection management for handling multiple WebSocket clients,
including connection lifecycle management, authentication, and client tracking.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Set, Any
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import get_logger
from app.exceptions import UnauthorizedError, WebSocketError

logger = get_logger(__name__)


class ConnectionInfo:
    """Information about a WebSocket connection."""

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: Optional[str] = None,
        user_id: Optional[str] = None,
        client_info: Optional[Dict[str, Any]] = None
    ):
        self.websocket = websocket
        self.connection_id = connection_id or str(uuid4())
        self.user_id = user_id
        self.client_info = client_info or {}
        self.connected_at = time.time()
        self.last_ping = time.time()
        self.subscriptions: Set[str] = set()
        self.is_authenticated = False

    @property
    def age_seconds(self) -> float:
        """Get connection age in seconds."""
        return time.time() - self.connected_at

    @property
    def seconds_since_ping(self) -> float:
        """Get seconds since last ping."""
        return time.time() - self.last_ping


class ConnectionManager:
    """
    Manages WebSocket connections with lifecycle handling.

    Provides connection management for multiple WebSocket clients including
    authentication, connection tracking, and cleanup of stale connections.
    """

    def __init__(self, ping_interval: int = 30, max_connection_age: int = 3600):
        """
        Initialize connection manager.

        Args:
            ping_interval: Interval in seconds for sending ping messages
            max_connection_age: Maximum connection age in seconds
        """
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.ping_interval = ping_interval
        self.max_connection_age = max_connection_age
        self._ping_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        client_info: Optional[Dict[str, Any]] = None,
        authenticate: bool = True
    ) -> ConnectionInfo:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection instance
            user_id: Optional user ID for authenticated connections
            client_info: Optional client information
            authenticate: Whether to require authentication

        Returns:
            ConnectionInfo: Information about the connected client

        Raises:
            UnauthorizedError: If authentication is required but fails
            WebSocketError: If connection cannot be established
        """
        try:
            # Accept the WebSocket connection
            await websocket.accept()

            # Create connection info
            connection_info = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                client_info=client_info
            )

            # Mark as authenticated if user_id is provided or authentication not required
            connection_info.is_authenticated = not authenticate or user_id is not None

            # Register connection
            self.active_connections[connection_info.connection_id] = connection_info

            # Track user connections if authenticated
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_info.connection_id)

            logger.info(
                f"WebSocket connected: {connection_info.connection_id} "
                f"(user: {user_id}, authenticated: {connection_info.is_authenticated})"
            )

            # Start background tasks if not already running
            if not self._ping_task or self._ping_task.done():
                self._ping_task = asyncio.create_task(self._ping_loop())
            if not self._cleanup_task or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            return connection_info

        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {str(e)}")
            raise WebSocketError(f"Connection failed: {str(e)}")

    async def disconnect(self, connection_id: str, reason: str = "disconnect") -> None:
        """
        Disconnect and clean up a WebSocket connection.

        Args:
            connection_id: Connection ID to disconnect
            reason: Reason for disconnection
        """
        connection_info = self.active_connections.get(connection_id)
        if not connection_info:
            return

        try:
            # Remove from active connections
            del self.active_connections[connection_id]

            # Remove from user connections
            if connection_info.user_id:
                user_conns = self.user_connections.get(connection_info.user_id)
                if user_conns:
                    user_conns.discard(connection_id)
                    if not user_conns:
                        del self.user_connections[connection_info.user_id]

            # Try to close the WebSocket gracefully
            try:
                await connection_info.websocket.close(code=1000, reason=reason)
            except Exception:
                pass  # Connection might already be closed

            logger.info(f"WebSocket disconnected: {connection_id} ({reason})")

        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {str(e)}")

    async def send_message(
        self,
        connection_id: str,
        message: Dict[str, Any],
        message_type: str = "message"
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection ID
            message: Message content
            message_type: Type of message

        Returns:
            bool: True if message was sent successfully
        """
        connection_info = self.active_connections.get(connection_id)
        if not connection_info:
            return False

        try:
            message_data = {
                "type": message_type,
                "timestamp": time.time(),
                "connection_id": connection_id,
                **message
            }

            await connection_info.websocket.send_text(json.dumps(message_data))
            return True

        except Exception as e:
            logger.warning(f"Failed to send message to {connection_id}: {str(e)}")
            # Connection might be dead, schedule cleanup
            asyncio.create_task(self.disconnect(connection_id, "send_error"))
            return False

    async def send_message_to_user(
        self,
        user_id: str,
        message: Dict[str, Any],
        message_type: str = "message"
    ) -> int:
        """
        Send a message to all connections for a user.

        Args:
            user_id: Target user ID
            message: Message content
            message_type: Type of message

        Returns:
            int: Number of connections message was sent to
        """
        connection_ids = self.user_connections.get(user_id, set())
        sent_count = 0

        for connection_id in list(connection_ids):  # Copy to avoid modification during iteration
            if await self.send_message(connection_id, message, message_type):
                sent_count += 1

        return sent_count

    def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """
        Get connection information by ID.

        Args:
            connection_id: Connection ID

        Returns:
            ConnectionInfo or None if not found
        """
        return self.active_connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> List[ConnectionInfo]:
        """
        Get all connections for a user.

        Args:
            user_id: User ID

        Returns:
            List of ConnectionInfo objects
        """
        connection_ids = self.user_connections.get(user_id, set())
        return [
            self.active_connections[conn_id]
            for conn_id in connection_ids
            if conn_id in self.active_connections
        ]

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.

        Returns:
            Dictionary with connection statistics
        """
        total_connections = len(self.active_connections)
        authenticated_connections = sum(
            1 for conn in self.active_connections.values()
            if conn.is_authenticated
        )
        unique_users = len(self.user_connections)

        return {
            "total_connections": total_connections,
            "authenticated_connections": authenticated_connections,
            "anonymous_connections": total_connections - authenticated_connections,
            "unique_users": unique_users,
            "average_connection_age": (
                sum(conn.age_seconds for conn in self.active_connections.values()) /
                total_connections if total_connections > 0 else 0
            )
        }

    async def _ping_loop(self) -> None:
        """Background task to send ping messages to all connections."""
        while self.active_connections:
            try:
                current_time = time.time()
                dead_connections = []

                for connection_id, connection_info in list(self.active_connections.items()):
                    # Check if connection is too old or hasn't responded to ping
                    if (
                        current_time - connection_info.connected_at > self.max_connection_age or
                        current_time - connection_info.last_ping > self.ping_interval * 2
                    ):
                        dead_connections.append(connection_id)
                    elif current_time - connection_info.last_ping > self.ping_interval:
                        # Send ping
                        ping_message = {
                            "type": "ping",
                            "timestamp": current_time
                        }
                        if await self.send_message(connection_id, ping_message, "ping"):
                            connection_info.last_ping = current_time
                        else:
                            dead_connections.append(connection_id)

                # Clean up dead connections
                for connection_id in dead_connections:
                    await self.disconnect(connection_id, "ping_timeout")

                await asyncio.sleep(self.ping_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ping loop: {str(e)}")
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _cleanup_loop(self) -> None:
        """Background task to clean up stale connections."""
        while self.active_connections:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute

                current_time = time.time()
                stale_connections = []

                for connection_id, connection_info in self.active_connections.items():
                    # Check for very old connections
                    if current_time - connection_info.connected_at > self.max_connection_age * 2:
                        stale_connections.append(connection_id)

                # Clean up stale connections
                for connection_id in stale_connections:
                    await self.disconnect(connection_id, "cleanup")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")

    async def shutdown(self) -> None:
        """Shutdown the connection manager and close all connections."""
        logger.info("Shutting down connection manager...")

        # Cancel background tasks
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

        # Close all connections
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id, "shutdown")

        logger.info("Connection manager shutdown complete")