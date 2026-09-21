"""
Tests for WebSocket connection manager.

This module tests the connection management functionality including
connection lifecycle, authentication, and cleanup.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.websocket.connection_manager import ConnectionManager, ConnectionInfo
from app.exceptions import UnauthorizedError, WebSocketError


@pytest.fixture
def connection_manager():
    """Create a connection manager for testing."""
    return ConnectionManager(ping_interval=1, max_connection_age=10)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.close = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.receive_text = AsyncMock()
    return websocket


@pytest.fixture
def mock_websocket_disconnect():
    """Create a mock WebSocketDisconnect exception."""
    from fastapi import WebSocketDisconnect
    return WebSocketDisconnect(code=1000)


class TestConnectionInfo:
    """Test ConnectionInfo class."""

    def test_connection_info_creation(self):
        """Test ConnectionInfo creation."""
        websocket = MagicMock()
        connection_info = ConnectionInfo(websocket, "test-conn-id", "test-user")

        assert connection_info.websocket == websocket
        assert connection_info.connection_id == "test-conn-id"
        assert connection_info.user_id == "test-user"
        assert connection_info.connected_at > 0
        assert connection_info.last_ping > 0
        assert connection_info.subscriptions == set()
        assert connection_info.is_authenticated is False

    def test_connection_info_age(self):
        """Test ConnectionInfo age calculation."""
        websocket = MagicMock()
        connection_info = ConnectionInfo(websocket)

        # Should be very recent
        assert 0 <= connection_info.age_seconds < 1

    def test_connection_info_unauthenticated_by_default(self):
        """Test ConnectionInfo is unauthenticated by default."""
        websocket = MagicMock()
        connection_info = ConnectionInfo(websocket)

        assert connection_info.is_authenticated is False

    def test_connection_info_authenticated_with_user_id(self):
        """Test ConnectionInfo is authenticated when user_id provided."""
        websocket = MagicMock()
        connection_info = ConnectionInfo(websocket, user_id="test-user")

        assert connection_info.is_authenticated is True


class TestConnectionManager:
    """Test ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_connect_success(self, connection_manager, mock_websocket):
        """Test successful WebSocket connection."""
        connection_info = await connection_manager.connect(
            mock_websocket,
            user_id="test-user",
            client_info={"user_agent": "test-agent"},
            authenticate=False
        )

        assert connection_info is not None
        assert connection_info.user_id == "test-user"
        assert connection_info.is_authenticated is False
        assert connection_info.connection_id in connection_manager.active_connections
        assert "test-user" in connection_manager.user_connections
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_authentication(self, connection_manager, mock_websocket):
        """Test WebSocket connection with authentication."""
        connection_info = await connection_manager.connect(
            mock_websocket,
            user_id="test-user",
            authenticate=True
        )

        assert connection_info is not None
        assert connection_info.is_authenticated is True
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_websocket_error(self, connection_manager):
        """Test connection failure due to WebSocket error."""
        mock_websocket = AsyncMock()
        mock_websocket.accept.side_effect = Exception("Connection failed")

        with pytest.raises(WebSocketError):
            await connection_manager.connect(mock_websocket)

        assert len(connection_manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_disconnect_success(self, connection_manager, mock_websocket):
        """Test successful WebSocket disconnection."""
        # First connect
        connection_info = await connection_manager.connect(
            mock_websocket,
            user_id="test-user"
        )
        connection_id = connection_info.connection_id

        # Then disconnect
        await connection_manager.disconnect(connection_id)

        assert connection_id not in connection_manager.active_connections
        assert connection_id not in connection_manager.user_connections.get("test-user", set())
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self, connection_manager):
        """Test disconnecting a non-existent connection."""
        # Should not raise an error
        await connection_manager.disconnect("non-existent-id")

    @pytest.mark.asyncio
    async def test_send_message_success(self, connection_manager, mock_websocket):
        """Test successful message sending."""
        # Connect first
        connection_info = await connection_manager.connect(mock_websocket)
        connection_id = connection_info.connection_id

        # Send message
        message = {"type": "test", "data": "hello"}
        success = await connection_manager.send_message(connection_id, message)

        assert success is True
        mock_websocket.send_text.assert_called_once()

        # Check sent message format
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "message"
        assert sent_data["data"] == message
        assert "timestamp" in sent_data
        assert sent_data["connection_id"] == connection_id

    @pytest.mark.asyncio
    async def test_send_message_nonexistent_connection(self, connection_manager):
        """Test sending message to non-existent connection."""
        success = await connection_manager.send_message("non-existent-id", {"test": "data"})
        assert success is False

    @pytest.mark.asyncio
    async def test_send_message_connection_error(self, connection_manager, mock_websocket):
        """Test sending message when connection fails."""
        # Connect first
        connection_info = await connection_manager.connect(mock_websocket)
        connection_id = connection_info.connection_id

        # Make send_text fail
        mock_websocket.send_text.side_effect = Exception("Connection lost")

        # Send message
        success = await connection_manager.send_message(connection_id, {"test": "data"})

        assert success is False
        assert connection_id not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_send_message_to_user(self, connection_manager):
        """Test sending message to all connections for a user."""
        # Create multiple connections for the same user
        mock_websocket1 = AsyncMock()
        mock_websocket1.accept = AsyncMock()
        mock_websocket1.send_text = AsyncMock()

        mock_websocket2 = AsyncMock()
        mock_websocket2.accept = AsyncMock()
        mock_websocket2.send_text = AsyncMock()

        # Connect both websockets for the same user
        conn1 = await connection_manager.connect(mock_websocket1, user_id="test-user")
        conn2 = await connection_manager.connect(mock_websocket2, user_id="test-user")

        # Send message to user
        message = {"type": "notification", "data": "hello user"}
        sent_count = await connection_manager.send_message_to_user("test-user", message)

        assert sent_count == 2
        mock_websocket1.send_text.assert_called_once()
        mock_websocket2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection(self, connection_manager, mock_websocket):
        """Test getting connection info."""
        # Connect first
        connection_info = await connection_manager.connect(mock_websocket)
        connection_id = connection_info.connection_id

        # Get connection
        retrieved_info = connection_manager.get_connection(connection_id)

        assert retrieved_info is connection_info

    @pytest.mark.asyncio
    async def test_get_connection_nonexistent(self, connection_manager):
        """Test getting non-existent connection."""
        retrieved_info = connection_manager.get_connection("non-existent")
        assert retrieved_info is None

    @pytest.mark.asyncio
    async def test_get_user_connections(self, connection_manager):
        """Test getting all connections for a user."""
        mock_websocket1 = AsyncMock()
        mock_websocket1.accept = AsyncMock()
        mock_websocket2 = AsyncMock()
        mock_websocket2.accept = AsyncMock()

        # Connect multiple websockets for the same user
        conn1 = await connection_manager.connect(mock_websocket1, user_id="test-user")
        conn2 = await connection_manager.connect(mock_websocket2, user_id="test-user")

        # Get user connections
        user_connections = connection_manager.get_user_connections("test-user")

        assert len(user_connections) == 2
        assert conn1 in user_connections
        assert conn2 in user_connections

    def test_get_connection_stats(self, connection_manager):
        """Test getting connection statistics."""
        stats = connection_manager.get_connection_stats()

        assert "total_connections" in stats
        assert "authenticated_connections" in stats
        assert "anonymous_connections" in stats
        assert "unique_users" in stats
        assert "average_connection_age" in stats

        # Initially should be empty
        assert stats["total_connections"] == 0
        assert stats["authenticated_connections"] == 0
        assert stats["unique_users"] == 0

    @pytest.mark.asyncio
    async def test_ping_loop_cleanup(self, connection_manager, mock_websocket):
        """Test ping loop cleanup of stale connections."""
        # Connect a websocket
        connection_info = await connection_manager.connect(mock_websocket)
        connection_id = connection_info.connection_id

        # Manually set old ping time to trigger cleanup
        connection_info.last_ping = 0  # Very old timestamp

        # Wait for ping loop to run (interval is 1 second in fixture)
        await asyncio.sleep(1.5)

        # Connection should be cleaned up
        assert connection_id not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_shutdown(self, connection_manager, mock_websocket):
        """Test connection manager shutdown."""
        # Connect a websocket
        connection_info = await connection_manager.connect(mock_websocket)

        # Shutdown manager
        await connection_manager.shutdown()

        # Connection should be closed and cleaned up
        assert len(connection_manager.active_connections) == 0
        mock_websocket.close.assert_called_once_with(code=1000, reason="shutdown")


@pytest.mark.asyncio
async def test_connection_manager_concurrent_connections():
    """Test connection manager with multiple concurrent connections."""
    manager = ConnectionManager()

    # Create multiple mock websockets
    websockets = []
    for i in range(5):
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        websockets.append(ws)

    # Connect all concurrently
    tasks = []
    for i, ws in enumerate(websockets):
        task = manager.connect(ws, user_id=f"user-{i}")
        tasks.append(task)

    connection_infos = await asyncio.gather(*tasks)

    assert len(connection_infos) == 5
    assert len(manager.active_connections) == 5
    assert len(manager.user_connections) == 5

    # Send messages to all connections concurrently
    message_tasks = []
    for conn_info in connection_infos:
        task = manager.send_message(conn_info.connection_id, {"test": "concurrent"})
        message_tasks.append(task)

    results = await asyncio.gather(*message_tasks)
    assert all(results)  # All should succeed

    # Disconnect all concurrently
    disconnect_tasks = []
    for conn_info in connection_infos:
        task = manager.disconnect(conn_info.connection_id)
        disconnect_tasks.append(task)

    await asyncio.gather(*disconnect_tasks)

    assert len(manager.active_connections) == 0
    assert len(manager.user_connections) == 0