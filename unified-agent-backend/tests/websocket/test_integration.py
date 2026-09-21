"""
Integration tests for WebSocket functionality.

This module tests the complete WebSocket implementation including
managers, endpoints, and integrations working together.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.websocket.manager import WebSocketManager
from app.websocket.integrations import (
    WorkflowExecutorWebSocketIntegration,
    AgentServiceWebSocketIntegration,
    NotificationServiceWebSocketIntegration
)
from app.schemas.websocket import (
    MessageType, ExecutionStartedMessage, AgentStatusChangedMessage,
    NotificationMessage, create_execution_started_message
)


@pytest.fixture
def websocket_manager():
    """Create a WebSocket manager for testing."""
    return WebSocketManager(require_auth=False)  # No auth for testing


@pytest.fixture
def mock_connection():
    """Create a mock WebSocket connection."""
    connection = AsyncMock()
    connection.accept = AsyncMock()
    connection.send_text = AsyncMock()
    connection.close = AsyncMock()
    return connection


class TestWebSocketIntegration:
    """Test WebSocket integration functionality."""

    @pytest.mark.asyncio
    async def test_complete_execution_flow(self, websocket_manager):
        """Test complete workflow execution WebSocket flow."""
        # Start the manager
        await websocket_manager.start()

        try:
            # Simulate execution start
            execution_id = "test-execution-123"
            workflow_id = "test-workflow-456"
            user_id = "test-user-789"

            # Create execution started message
            execution_message = create_execution_started_message(
                execution_id=execution_id,
                workflow_id=workflow_id,
                user_id=user_id,
                input_data={"param1": "value1"}
            )

            # Broadcast to execution room
            sent_count = await websocket_manager.broadcast_to_room(
                f"execution:{execution_id}",
                execution_message.dict(),
                "execution_started"
            )
            assert sent_count == 0  # No connections yet

            # Simulate a client connecting to execution updates
            mock_connection = AsyncMock()
            mock_connection.accept = AsyncMock()
            mock_connection.send_text = AsyncMock()

            connection_info = await websocket_manager.handle_connection(
                mock_connection,
                execution_id=execution_id
            )
            assert connection_info is not None

            # Subscribe to execution room
            success = await websocket_manager.room_manager.subscribe_connection(
                connection_info.connection_id,
                f"execution:{execution_id}",
                "execution",
                {"execution_id": execution_id}
            )
            assert success is True

            # Broadcast again - should reach the client
            sent_count = await websocket_manager.broadcast_to_room(
                f"execution:{execution_id}",
                execution_message.dict(),
                "execution_started"
            )
            assert sent_count == 1

            # Send progress update
            progress_message = {
                "type": "execution_progress",
                "data": {
                    "execution_id": execution_id,
                    "progress_percentage": 25.0,
                    "current_node_id": "node-1",
                    "completed_nodes": 1,
                    "total_nodes": 4
                }
            }
            sent_count = await websocket_manager.broadcast_to_room(
                f"execution:{execution_id}",
                progress_message,
                "execution_progress"
            )
            assert sent_count == 1

            # Send completion message
            completion_message = {
                "type": "execution_completed",
                "data": {
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": "completed",
                    "duration_seconds": 45.5,
                    "output_data": {"result": "success"}
                }
            }
            sent_count = await websocket_manager.broadcast_to_room(
                f"execution:{execution_id}",
                completion_message,
                "execution_completed"
            )
            assert sent_count == 1

            # Verify messages were sent to client
            assert mock_connection.send_text.call_count >= 3  # welcome + updates

        finally:
            await websocket_manager.stop()

    @pytest.mark.asyncio
    async def test_agent_monitoring_flow(self, websocket_manager):
        """Test agent monitoring WebSocket flow."""
        await websocket_manager.start()

        try:
            agent_id = "test-agent-123"

            # Create agent WebSocket integration
            agent_integration = AgentServiceWebSocketIntegration(websocket_manager)

            # Client connects to agent monitoring
            mock_connection = AsyncMock()
            mock_connection.accept = AsyncMock()
            mock_connection.send_text = AsyncMock()

            connection_info = await websocket_manager.handle_connection(mock_connection)

            # Subscribe to agent updates
            await websocket_manager.room_manager.subscribe_connection(
                connection_info.connection_id,
                f"agent:{agent_id}",
                "agent",
                {"agent_id": agent_id}
            )

            # Send agent status change
            await agent_integration.notify_agent_status_changed(
                agent_id=agent_id,
                old_status="idle",
                new_status="busy",
                reason="Task assigned"
            )

            # Send health update
            await agent_integration.notify_agent_health_update(
                agent_id=agent_id,
                health_status="healthy",
                cpu_usage=65.5,
                memory_usage=78.2,
                active_tasks=2
            )

            # Send task assignment
            await agent_integration.notify_agent_task_assigned(
                agent_id=agent_id,
                task_id="task-456",
                task_type="data_processing",
                priority="high",
                estimated_duration=120.0
            )

            # Send task completion
            await agent_integration.notify_agent_task_completed(
                agent_id=agent_id,
                task_id="task-456",
                status="completed",
                result={"processed_records": 1000},
                duration_seconds=115.3
            )

            # Verify messages were sent
            assert mock_connection.send_text.call_count >= 5  # welcome + updates

        finally:
            await websocket_manager.stop()

    @pytest.mark.asyncio
    async def test_notification_flow(self, websocket_manager):
        """Test notification WebSocket flow."""
        await websocket_manager.start()

        try:
            user_id = "test-user-789"

            # Create notification integration
            notification_integration = NotificationServiceWebSocketIntegration(websocket_manager)

            # Client connects
            mock_connection = AsyncMock()
            mock_connection.accept = AsyncMock()
            mock_connection.send_text = AsyncMock()

            connection_info = await websocket_manager.handle_connection(
                mock_connection,
                user_id=user_id
            )

            # Send user notification (should be auto-subscribed to user room)
            await notification_integration.send_user_notification(
                user_id=user_id,
                title="Execution Complete",
                message="Your workflow execution has completed successfully",
                level="success",
                action_url="/executions/123"
            )

            # Send another notification
            await notification_integration.send_user_notification(
                user_id=user_id,
                title="System Maintenance",
                message="Scheduled maintenance in 1 hour",
                level="warning"
            )

            # Verify notifications were sent
            assert mock_connection.send_text.call_count >= 3  # welcome + notifications

        finally:
            await websocket_manager.stop()

    @pytest.mark.asyncio
    async def test_multiple_clients_same_room(self, websocket_manager):
        """Test multiple clients subscribed to the same room."""
        await websocket_manager.start()

        try:
            room_id = "execution:multi-test"
            execution_id = "multi-execution-123"

            # Create multiple client connections
            connections = []
            connection_infos = []

            for i in range(3):
                mock_connection = AsyncMock()
                mock_connection.accept = AsyncMock()
                mock_connection.send_text = AsyncMock()

                connection_info = await websocket_manager.handle_connection(mock_connection)
                connections.append(mock_connection)
                connection_infos.append(connection_info)

                # Subscribe each to the same execution room
                await websocket_manager.room_manager.subscribe_connection(
                    connection_info.connection_id,
                    room_id,
                    "execution",
                    {"execution_id": execution_id}
                )

            # Broadcast a message
            test_message = {
                "type": "test_broadcast",
                "data": {"execution_id": execution_id, "message": "Hello all clients!"}
            }

            sent_count = await websocket_manager.broadcast_to_room(
                room_id,
                test_message,
                "test_broadcast"
            )

            # Should reach all 3 clients
            assert sent_count == 3

            # Verify each client received the message
            for mock_connection in connections:
                # Each should have welcome + broadcast message
                assert mock_connection.send_text.call_count >= 2

        finally:
            await websocket_manager.stop()

    @pytest.mark.asyncio
    async def test_room_management_integration(self, websocket_manager):
        """Test room management with real connections."""
        await websocket_manager.start()

        try:
            # Create connection
            mock_connection = AsyncMock()
            mock_connection.accept = AsyncMock()
            mock_connection.send_text = AsyncMock()
            mock_connection.receive_text = AsyncMock(
                side_effect=[
                    # Subscribe to execution room
                    json.dumps({
                        "type": "subscribe",
                        "data": {
                            "room_id": "execution:test-123",
                            "room_type": "execution"
                        }
                    }),
                    # Subscribe to agent room
                    json.dumps({
                        "type": "subscribe",
                        "data": {
                            "room_id": "agent:agent-456",
                            "room_type": "agent"
                        }
                    }),
                    # Get rooms list
                    json.dumps({
                        "type": "get_rooms",
                        "data": {}
                    }),
                    # Unsubscribe from one room
                    json.dumps({
                        "type": "unsubscribe",
                        "data": {
                            "room_id": "execution:test-123"
                        }
                    }),
                    # End connection
                    Exception("Connection closed")
                ]
            )

            connection_info = await websocket_manager.handle_connection(mock_connection)
            assert connection_info is not None

            # Process messages
            try:
                while True:
                    message = await mock_connection.receive_text()
                    await websocket_manager.handle_message(connection_info.connection_id, message)
            except Exception:
                pass  # Expected end of connection

            # Verify subscriptions and unsubscriptions worked
            rooms = websocket_manager.room_manager.get_connection_rooms(connection_info.connection_id)
            # Should only have agent room remaining (execution was unsubscribed)
            assert len(rooms) == 1
            assert rooms[0].room_id == "agent:agent-456"

            # Check room stats
            stats = websocket_manager.get_stats()
            assert stats["room_stats"]["total_rooms"] >= 1
            assert stats["connection_stats"]["total_connections"] == 1

        finally:
            await websocket_manager.stop()

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, websocket_manager):
        """Test error handling in WebSocket integration."""
        await websocket_manager.start()

        try:
            # Create connection that will fail on message sending
            mock_connection = AsyncMock()
            mock_connection.accept = AsyncMock()
            mock_connection.send_text = AsyncMock(side_effect=Exception("Connection lost"))

            connection_info = await websocket_manager.handle_connection(mock_connection)

            # Try to send message - should handle the error gracefully
            success = await websocket_manager.send_message_to_connection(
                connection_info.connection_id,
                {"type": "test", "data": "message"}
            )

            # Should return False due to error
            assert success is False

            # Connection should be cleaned up
            assert connection_info.connection_id not in websocket_manager.connection_manager.active_connections

        finally:
            await websocket_manager.stop()

    def test_message_schema_validation(self):
        """Test WebSocket message schema validation."""
        # Test valid message
        message = ExecutionStartedMessage(
            execution_id="test-123",
            workflow_id="workflow-456",
            user_id="user-789",
            started_at="2024-01-01T12:00:00",
            input_data={"param": "value"}
        )

        assert message.type == MessageType.EXECUTION_STARTED
        assert message.execution_id == "test-123"

        # Test message serialization
        message_dict = message.dict()
        assert "type" in message_dict
        assert "execution_id" in message_dict
        assert message_dict["type"] == "execution_started"

        # Test notification message
        notification = NotificationMessage(
            title="Test Title",
            message="Test message",
            level="info",
            user_id="user-123"
        )

        assert notification.type == MessageType.NOTIFICATION
        assert notification.title == "Test Title"

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, websocket_manager):
        """Test handling multiple concurrent connections."""
        await websocket_manager.start()

        try:
            # Create multiple concurrent connections
            connection_tasks = []
            for i in range(5):
                mock_connection = AsyncMock()
                mock_connection.accept = AsyncMock()
                mock_connection.send_text = AsyncMock()

                task = websocket_manager.handle_connection(mock_connection)
                connection_tasks.append(task)

            # Wait for all connections to be established
            connection_infos = await asyncio.gather(*connection_tasks)

            assert len(connection_infos) == 5
            assert len(websocket_manager.connection_manager.active_connections) == 5

            # Broadcast to all connections via user room (if they have same user_id)
            # For this test, we'll use a general broadcast
            await websocket_manager.create_room("global-room", "global")

            # Subscribe all connections to global room
            subscribe_tasks = []
            for conn_info in connection_infos:
                task = websocket_manager.room_manager.subscribe_connection(
                    conn_info.connection_id,
                    "global-room",
                    "global"
                )
                subscribe_tasks.append(task)

            await asyncio.gather(*subscribe_tasks)

            # Broadcast message
            message = {"type": "broadcast", "data": {"message": "Hello everyone!"}}
            sent_count = await websocket_manager.broadcast_to_room("global-room", message, "broadcast")

            # Should reach all 5 connections
            assert sent_count == 5

        finally:
            await websocket_manager.stop()