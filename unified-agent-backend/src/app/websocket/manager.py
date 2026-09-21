"""
Main WebSocket manager that coordinates connection and room management.

This module provides the main WebSocket manager that integrates connection management,
room subscriptions, message broadcasting, and authentication into a single interface.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from .connection_manager import ConnectionManager, ConnectionInfo
from .room_manager import RoomManager
from .auth import WebSocketAuth
from app.core.logging import get_logger
from app.exceptions import WebSocketError, UnauthorizedError, ForbiddenError

logger = get_logger(__name__)


class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: str
    data: Dict[str, Any]
    timestamp: Optional[float] = None
    room_id: Optional[str] = None
    connection_id: Optional[str] = None


class WebSocketManager:
    """
    Main WebSocket manager coordinating all WebSocket functionality.

    This class integrates connection management, room subscriptions, and message
    broadcasting into a single interface for easy use throughout the application.
    """

    def __init__(self, require_auth: bool = True):
        """
        Initialize WebSocket manager.

        Args:
            require_auth: Whether to require authentication for connections
        """
        self.connection_manager = ConnectionManager()
        self.room_manager = RoomManager()
        self.auth = WebSocketAuth()
        self.require_auth = require_auth
        self._started = False

    async def start(self) -> None:
        """Start the WebSocket manager and background tasks."""
        if self._started:
            return

        logger.info("Starting WebSocket manager...")
        await self.room_manager.start_cleanup_task()
        self._started = True
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager and clean up resources."""
        logger.info("Stopping WebSocket manager...")

        await self.connection_manager.shutdown()
        await self.room_manager.shutdown()

        self._started = False
        logger.info("WebSocket manager stopped")

    async def handle_connection(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> Optional[ConnectionInfo]:
        """
        Handle a new WebSocket connection.

        Args:
            websocket: WebSocket connection instance
            token: JWT authentication token
            api_key: API key for authentication
            **kwargs: Additional connection parameters

        Returns:
            ConnectionInfo if connection successful, None otherwise
        """
        try:
            # Extract authentication info from query parameters and headers
            query_params = dict(websocket.query_params)
            headers = dict(websocket.headers)

            # Authenticate connection
            user_info = None
            if self.require_auth:
                user_info = await self.auth.authenticate_connection(
                    token=token,
                    api_key=api_key,
                    query_params=query_params,
                    headers=headers
                )
                if not user_info:
                    await websocket.close(code=4001, reason="Authentication required")
                    return None
            else:
                # Create mock user info for unauthenticated connections
                user_info = {
                    "id": f"anon_{query_params.get('client_id', 'unknown')}",
                    "email": "anonymous@example.com",
                    "is_active": True,
                    "is_admin": False,
                    "auth_method": "anonymous"
                }

            # Establish connection
            connection_info = await self.connection_manager.connect(
                websocket=websocket,
                user_id=user_info["id"],
                client_info={
                    "user_agent": headers.get("user-agent", "unknown"),
                    "origin": headers.get("origin", "unknown"),
                    "query_params": query_params,
                    "headers": headers,
                    **kwargs
                },
                authenticate=not self.require_auth or user_info is not None
            )

            # Send welcome message
            await self.send_message_to_connection(
                connection_info.connection_id,
                {
                    "type": "welcome",
                    "message": "Connected to WebSocket server",
                    "user_info": user_info,
                    "connection_id": connection_info.connection_id
                }
            )

            # Subscribe to user-specific room if authenticated
            if user_info:
                await self.room_manager.subscribe_connection(
                    connection_info.connection_id,
                    f"user:{user_info['id']}",
                    "user",
                    {"user_id": user_info["id"]}
                )

            logger.info(f"WebSocket connection established: {connection_info.connection_id}")
            return connection_info

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected during handshake")
            return None
        except UnauthorizedError as e:
            await websocket.close(code=4001, reason=str(e))
            return None
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {str(e)}")
            try:
                await websocket.close(code=4000, reason="Internal server error")
            except:
                pass
            return None

    async def handle_message(
        self,
        connection_id: str,
        message: str
    ) -> bool:
        """
        Handle a message from a WebSocket connection.

        Args:
            connection_id: Connection ID
            message: Message content

        Returns:
            bool: True if message was handled successfully
        """
        try:
            # Parse message
            try:
                message_data = json.loads(message)
            except json.JSONDecodeError:
                await self.send_error_to_connection(
                    connection_id,
                    "Invalid JSON message format"
                )
                return False

            # Validate message structure
            if not isinstance(message_data, dict) or "type" not in message_data:
                await self.send_error_to_connection(
                    connection_id,
                    "Message must be a JSON object with 'type' field"
                )
                return False

            message_type = message_data.get("type")
            message_content = message_data.get("data", {})

            # Handle different message types
            if message_type == "subscribe":
                return await self._handle_subscribe(connection_id, message_content)
            elif message_type == "unsubscribe":
                return await self._handle_unsubscribe(connection_id, message_content)
            elif message_type == "ping":
                return await self._handle_ping(connection_id, message_content)
            elif message_type == "get_rooms":
                return await self._handle_get_rooms(connection_id, message_content)
            else:
                await self.send_error_to_connection(
                    connection_id,
                    f"Unknown message type: {message_type}"
                )
                return False

        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {str(e)}")
            await self.send_error_to_connection(
                connection_id,
                f"Error processing message: {str(e)}"
            )
            return False

    async def handle_disconnect(self, connection_id: str, reason: str = "disconnect") -> None:
        """
        Handle WebSocket disconnection.

        Args:
            connection_id: Connection ID
            reason: Reason for disconnection
        """
        try:
            # Unsubscribe from all rooms
            await self.room_manager.unsubscribe_connection_from_all_rooms(connection_id)

            # Disconnect connection
            await self.connection_manager.disconnect(connection_id, reason)

            logger.info(f"WebSocket disconnected: {connection_id} ({reason})")

        except Exception as e:
            logger.error(f"Error handling WebSocket disconnect: {str(e)}")

    async def _handle_subscribe(self, connection_id: str, data: Dict[str, Any]) -> bool:
        """Handle subscription message."""
        try:
            room_id = data.get("room_id")
            room_type = data.get("room_type")
            resource_id = data.get("resource_id")

            if not room_id or not room_type:
                await self.send_error_to_connection(
                    connection_id,
                    "Subscription requires 'room_id' and 'room_type'"
                )
                return False

            # Get connection info for authorization
            connection_info = self.connection_manager.get_connection(connection_id)
            if not connection_info:
                return False

            # Check authorization if required
            if self.require_auth and connection_info.is_authenticated:
                user_info = {"id": connection_info.user_id}
                if not await self.auth.authorize_subscription(
                    user_info, room_id, room_type, resource_id
                ):
                    await self.send_error_to_connection(
                        connection_id,
                        f"Not authorized to subscribe to room: {room_id}"
                    )
                    return False

            # Subscribe to room
            success = await self.room_manager.subscribe_connection(
                connection_id, room_id, room_type, {"resource_id": resource_id}
            )

            if success:
                await self.send_message_to_connection(
                    connection_id,
                    {
                        "type": "subscription_confirmed",
                        "room_id": room_id,
                        "room_type": room_type,
                        "resource_id": resource_id
                    }
                )

            return success

        except Exception as e:
            logger.error(f"Error handling subscription: {str(e)}")
            return False

    async def _handle_unsubscribe(self, connection_id: str, data: Dict[str, Any]) -> bool:
        """Handle unsubscription message."""
        try:
            room_id = data.get("room_id")
            if not room_id:
                await self.send_error_to_connection(
                    connection_id,
                    "Unsubscription requires 'room_id'"
                )
                return False

            success = await self.room_manager.unsubscribe_connection(connection_id, room_id)

            if success:
                await self.send_message_to_connection(
                    connection_id,
                    {
                        "type": "unsubscription_confirmed",
                        "room_id": room_id
                    }
                )

            return success

        except Exception as e:
            logger.error(f"Error handling unsubscription: {str(e)}")
            return False

    async def _handle_ping(self, connection_id: str, data: Dict[str, Any]) -> bool:
        """Handle ping message."""
        await self.send_message_to_connection(
            connection_id,
            {
                "type": "pong",
                "timestamp": asyncio.get_event_loop().time(),
                "ping_data": data
            }
        )
        return True

    async def _handle_get_rooms(self, connection_id: str, data: Dict[str, Any]) -> bool:
        """Handle get_rooms message."""
        try:
            connection_rooms = self.room_manager.get_connection_rooms(connection_id)
            room_list = [
                {
                    "room_id": room.room_id,
                    "room_type": room.room_type,
                    "metadata": room.metadata,
                    "connection_count": room.connection_count
                }
                for room in connection_rooms
            ]

            await self.send_message_to_connection(
                connection_id,
                {
                    "type": "rooms_list",
                    "rooms": room_list
                }
            )
            return True

        except Exception as e:
            logger.error(f"Error handling get_rooms: {str(e)}")
            return False

    async def send_message_to_connection(
        self,
        connection_id: str,
        message: Dict[str, Any],
        message_type: str = "message"
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Connection ID
            message: Message content
            message_type: Type of message

        Returns:
            bool: True if message was sent successfully
        """
        return await self.connection_manager.send_message(connection_id, message, message_type)

    async def send_message_to_user(
        self,
        user_id: str,
        message: Dict[str, Any],
        message_type: str = "message"
    ) -> int:
        """
        Send a message to all connections for a user.

        Args:
            user_id: User ID
            message: Message content
            message_type: Type of message

        Returns:
            int: Number of connections message was sent to
        """
        return await self.connection_manager.send_message_to_user(user_id, message, message_type)

    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        message_type: str = "broadcast"
    ) -> int:
        """
        Broadcast a message to all connections in a room.

        Args:
            room_id: Room ID
            message: Message content
            message_type: Type of message

        Returns:
            int: Number of connections message was sent to
        """
        return await self.room_manager.broadcast_to_room(
            room_id, message, message_type, self.connection_manager
        )

    async def broadcast_to_room_type(
        self,
        room_type: str,
        message: Dict[str, Any],
        message_type: str = "broadcast"
    ) -> int:
        """
        Broadcast a message to all rooms of a specific type.

        Args:
            room_type: Type of room
            message: Message content
            message_type: Type of message

        Returns:
            int: Total number of connections message was sent to
        """
        rooms = self.room_manager.get_rooms_by_type(room_type)
        total_sent = 0

        for room in rooms:
            sent = await self.broadcast_to_room(room.room_id, message, message_type)
            total_sent += sent

        return total_sent

    async def send_error_to_connection(
        self,
        connection_id: str,
        error_message: str,
        error_code: str = "error"
    ) -> bool:
        """
        Send an error message to a connection.

        Args:
            connection_id: Connection ID
            error_message: Error message
            error_code: Error code

        Returns:
            bool: True if error message was sent successfully
        """
        return await self.send_message_to_connection(
            connection_id,
            {
                "type": "error",
                "error": error_message,
                "error_code": error_code,
                "timestamp": asyncio.get_event_loop().time()
            },
            "error"
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket manager statistics.

        Returns:
            Dictionary with manager statistics
        """
        return {
            "connection_stats": self.connection_manager.get_connection_stats(),
            "room_stats": self.room_manager.get_room_stats(),
            "started": self._started
        }

    async def create_room(
        self,
        room_id: str,
        room_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new room.

        Args:
            room_id: Room ID
            room_type: Type of room
            metadata: Optional room metadata

        Returns:
            bool: True if room was created successfully
        """
        try:
            self.room_manager.create_room(room_id, room_type, metadata)
            return True
        except ValueError:
            return False

    def get_room(self, room_id: str) -> Optional[Any]:
        """Get room information."""
        return self.room_manager.get_room(room_id)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()