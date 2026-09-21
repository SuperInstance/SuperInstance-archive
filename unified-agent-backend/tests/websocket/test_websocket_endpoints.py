"""
Tests for WebSocket endpoints.

This module tests the WebSocket API endpoints including connection handling,
message processing, and subscription management.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import WebSocket

from app.main import create_application
from app.websocket.manager import WebSocketManager


@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    return create_application()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager."""
    manager = AsyncMock()
    manager.handle_connection = AsyncMock()
    manager.handle_message = AsyncMock()
    manager.handle_disconnect = AsyncMock()
    manager._started = True
    return manager


class TestWebSocketEndpoints:
    """Test WebSocket endpoints."""

    @pytest.mark.asyncio
    async def test_websocket_endpoint_success(self, mock_websocket_manager):
        """Test successful WebSocket connection."""
        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import websocket_endpoint

            # Mock WebSocket
            mock_websocket = AsyncMock()
            mock_websocket.receive_text = AsyncMock(side_effect=["{}"])  # Empty message
            mock_websocket.accept = AsyncMock()

            # Mock connection info
            mock_connection_info = MagicMock()
            mock_connection_info.connection_id = "test-conn-id"
            mock_websocket_manager.handle_connection.return_value = mock_connection_info

            # Should not raise an exception
            try:
                # This will loop until receive_text raises an exception
                # For testing, we'll just run one iteration
                await websocket_endpoint(mock_websocket)
            except Exception:
                pass  # Expected when receive_text is exhausted

            mock_websocket_manager.handle_connection.assert_called_once()
            mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_endpoint_connection_failure(self, mock_websocket_manager):
        """Test WebSocket connection failure."""
        mock_websocket_manager.handle_connection.return_value = None

        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import websocket_endpoint

            mock_websocket = AsyncMock()
            mock_websocket.close = AsyncMock()

            # Should return early when connection fails
            await websocket_endpoint(mock_websocket)

            mock_websocket.close.assert_not_called()  # Already handled in handle_connection

    @pytest.mark.asyncio
    async def test_websocket_endpoint_message_handling(self, mock_websocket_manager):
        """Test WebSocket message handling."""
        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import websocket_endpoint

            mock_websocket = AsyncMock()
            mock_websocket.receive_text = AsyncMock(
                side_effect=[
                    '{"type": "ping"}',  # First message
                    Exception("Connection closed")  # Simulate connection close
                ]
            )
            mock_websocket.accept = AsyncMock()

            mock_connection_info = MagicMock()
            mock_connection_info.connection_id = "test-conn-id"
            mock_websocket_manager.handle_connection.return_value = mock_connection_info

            try:
                await websocket_endpoint(mock_websocket)
            except Exception:
                pass

            # Should handle the message
            mock_websocket_manager.handle_message.assert_called_once()
            call_args = mock_websocket_manager.handle_message.call_args
            assert call_args[0][0] == "test-conn-id"  # connection_id
            assert call_args[0][1] == '{"type": "ping"}'  # message

    @pytest.mark.asyncio
    async def test_execution_websocket_endpoint(self, mock_websocket_manager):
        """Test execution-specific WebSocket endpoint."""
        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import execution_websocket

            mock_websocket = AsyncMock()
            mock_websocket.receive_text = AsyncMock(side_effect=[Exception("Done")])
            mock_websocket.accept = AsyncMock()

            mock_connection_info = MagicMock()
            mock_connection_info.connection_id = "test-conn-id"
            mock_websocket_manager.handle_connection.return_value = mock_connection_info

            mock_websocket_manager.room_manager = AsyncMock()
            mock_websocket_manager.room_manager.subscribe_connection.return_value = True

            try:
                await execution_websocket(mock_websocket, "test-execution-id")
            except Exception:
                pass

            # Should subscribe to execution room
            mock_websocket_manager.room_manager.subscribe_connection.assert_called_once()
            call_args = mock_websocket_manager.room_manager.subscribe_connection.call_args
            assert call_args[0][0] == "test-conn-id"  # connection_id
            assert call_args[0][1] == "execution:test-execution-id"  # room_id
            assert call_args[0][2] == "execution"  # room_type

    @pytest.mark.asyncio
    async def test_agent_websocket_endpoint(self, mock_websocket_manager):
        """Test agent-specific WebSocket endpoint."""
        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import agent_websocket

            mock_websocket = AsyncMock()
            mock_websocket.receive_text = AsyncMock(side_effect=[Exception("Done")])
            mock_websocket.accept = AsyncMock()

            mock_connection_info = MagicMock()
            mock_connection_info.connection_id = "test-conn-id"
            mock_websocket_manager.handle_connection.return_value = mock_connection_info

            mock_websocket_manager.room_manager = AsyncMock()
            mock_websocket_manager.room_manager.subscribe_connection.return_value = True

            try:
                await agent_websocket(mock_websocket, "test-agent-id")
            except Exception:
                pass

            # Should subscribe to agent room
            mock_websocket_manager.room_manager.subscribe_connection.assert_called_once()
            call_args = mock_websocket_manager.room_manager.subscribe_connection.call_args
            assert call_args[0][1] == "agent:test-agent-id"  # room_id
            assert call_args[0][2] == "agent"  # room_type

    @pytest.mark.asyncio
    async def test_workflow_websocket_endpoint(self, mock_websocket_manager):
        """Test workflow-specific WebSocket endpoint."""
        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import workflow_websocket

            mock_websocket = AsyncMock()
            mock_websocket.receive_text = AsyncMock(side_effect=[Exception("Done")])
            mock_websocket.accept = AsyncMock()

            mock_connection_info = MagicMock()
            mock_connection_info.connection_id = "test-conn-id"
            mock_websocket_manager.handle_connection.return_value = mock_connection_info

            mock_websocket_manager.room_manager = AsyncMock()
            mock_websocket_manager.room_manager.subscribe_connection.return_value = True

            try:
                await workflow_websocket(mock_websocket, "test-workflow-id")
            except Exception:
                pass

            # Should subscribe to workflow room
            mock_websocket_manager.room_manager.subscribe_connection.assert_called_once()
            call_args = mock_websocket_manager.room_manager.subscribe_connection.call_args
            assert call_args[0][1] == "workflow:test-workflow-id"  # room_id
            assert call_args[0][2] == "workflow"  # room_type

    @pytest.mark.asyncio
    async def test_execution_websocket_subscription_failure(self, mock_websocket_manager):
        """Test execution WebSocket endpoint subscription failure."""
        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import execution_websocket

            mock_websocket = AsyncMock()
            mock_websocket.close = AsyncMock()

            mock_connection_info = MagicMock()
            mock_connection_info.connection_id = "test-conn-id"
            mock_websocket_manager.handle_connection.return_value = mock_connection_info

            mock_websocket_manager.room_manager = AsyncMock()
            mock_websocket_manager.room_manager.subscribe_connection.return_value = False

            await execution_websocket(mock_websocket, "test-execution-id")

            # Should close connection on subscription failure
            mock_websocket.close.assert_called_once_with(code=4003, reason="Failed to subscribe to execution updates")

    @pytest.mark.asyncio
    async def test_get_websocket_stats(self, mock_websocket_manager):
        """Test getting WebSocket statistics."""
        mock_websocket_manager.get_stats.return_value = {
            "connection_stats": {"total_connections": 5},
            "room_stats": {"total_rooms": 3},
            "started": True
        }

        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import get_websocket_stats

            stats = await get_websocket_stats(mock_websocket_manager)

            assert stats["connection_stats"]["total_connections"] == 5
            assert stats["room_stats"]["total_rooms"] == 3
            assert stats["started"] is True

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, mock_websocket_manager):
        """Test broadcasting message to room."""
        mock_websocket_manager.broadcast_to_room.return_value = 3

        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import broadcast_to_room

            result = await broadcast_to_room(
                "test-room",
                {"type": "notification", "message": "Hello"},
                mock_websocket_manager
            )

            assert result["success"] is True
            assert result["room_id"] == "test-room"
            assert result["sent_count"] == 3
            mock_websocket_manager.broadcast_to_room.assert_called_once_with(
                "test-room",
                {"type": "notification", "message": "Hello"}
            )

    @pytest.mark.asyncio
    async def test_broadcast_to_room_failure(self, mock_websocket_manager):
        """Test broadcasting message to room with failure."""
        mock_websocket_manager.broadcast_to_room.side_effect = Exception("Broadcast failed")

        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import broadcast_to_room
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await broadcast_to_room("test-room", {"test": "data"}, mock_websocket_manager)

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_notify_user(self, mock_websocket_manager):
        """Test notifying a user."""
        mock_websocket_manager.send_message_to_user.return_value = 2

        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import notify_user

            result = await notify_user(
                "test-user",
                {"title": "Test", "message": "Hello"},
                mock_websocket_manager
            )

            assert result["success"] is True
            assert result["user_id"] == "test-user"
            assert result["sent_count"] == 2

            # Check that the message includes notification type
            call_args = mock_websocket_manager.send_message_to_user.call_args
            sent_message = call_args[0][1]
            assert sent_message["type"] == "notification"
            assert sent_message["title"] == "Test"
            assert sent_message["message"] == "Hello"
            assert sent_message["user_id"] == "test-user"

    @pytest.mark.asyncio
    async def test_notify_user_failure(self, mock_websocket_manager):
        """Test notifying user with failure."""
        mock_websocket_manager.send_message_to_user.side_effect = Exception("Notification failed")

        with patch('app.api.v1.websocket.endpoints.websocket_manager', mock_websocket_manager):
            from app.api.v1.websocket.endpoints import notify_user
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await notify_user("test-user", {"test": "data"}, mock_websocket_manager)

            assert exc_info.value.status_code == 500


class TestWebSocketMessageHandling:
    """Test WebSocket message handling."""

    @pytest.mark.asyncio
    async def test_subscribe_message(self, mock_websocket_manager):
        """Test handling subscription message."""
        from app.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        manager.room_manager = AsyncMock()
        manager.room_manager.subscribe_connection.return_value = True
        manager.send_message_to_connection = AsyncMock(return_value=True)

        # Mock connection info
        manager.connection_manager = AsyncMock()
        mock_connection_info = MagicMock()
        mock_connection_info.is_authenticated = True
        mock_connection_info.user_id = "test-user"
        manager.connection_manager.get_connection.return_value = mock_connection_info

        message = json.dumps({
            "type": "subscribe",
            "data": {
                "room_id": "test-room",
                "room_type": "execution",
                "resource_id": "test-execution"
            }
        })

        result = await manager.handle_message("test-conn-id", message)

        assert result is True
        manager.room_manager.subscribe_connection.assert_called_once()
        manager.send_message_to_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_message(self, mock_websocket_manager):
        """Test handling unsubscription message."""
        from app.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        manager.room_manager = AsyncMock()
        manager.room_manager.unsubscribe_connection.return_value = True
        manager.send_message_to_connection = AsyncMock(return_value=True)

        message = json.dumps({
            "type": "unsubscribe",
            "data": {
                "room_id": "test-room"
            }
        })

        result = await manager.handle_message("test-conn-id", message)

        assert result is True
        manager.room_manager.unsubscribe_connection.assert_called_once_with("test-conn-id", "test-room")

    @pytest.mark.asyncio
    async def test_ping_message(self, mock_websocket_manager):
        """Test handling ping message."""
        from app.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        manager.send_message_to_connection = AsyncMock(return_value=True)

        message = json.dumps({
            "type": "ping",
            "data": {"timestamp": 1234567890}
        })

        result = await manager.handle_message("test-conn-id", message)

        assert result is True
        manager.send_message_to_connection.assert_called_once()

        # Check pong message
        call_args = manager.send_message_to_connection.call_args
        sent_message = call_args[0][1]
        assert sent_message["type"] == "pong"
        assert "timestamp" in sent_message

    @pytest.mark.asyncio
    async def test_invalid_json_message(self, mock_websocket_manager):
        """Test handling invalid JSON message."""
        from app.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        manager.send_error_to_connection = AsyncMock(return_value=True)

        result = await manager.handle_message("test-conn-id", "invalid json")

        assert result is False
        manager.send_error_to_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_message_type(self, mock_websocket_manager):
        """Test handling message without type."""
        from app.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        manager.send_error_to_connection = AsyncMock(return_value=True)

        message = json.dumps({"data": "test"})

        result = await manager.handle_message("test-conn-id", message)

        assert result is False
        manager.send_error_to_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_message_type(self, mock_websocket_manager):
        """Test handling unknown message type."""
        from app.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        manager.send_error_to_connection = AsyncMock(return_value=True)

        message = json.dumps({
            "type": "unknown_type",
            "data": {}
        })

        result = await manager.handle_message("test-conn-id", message)

        assert result is False
        manager.send_error_to_connection.assert_called_once()