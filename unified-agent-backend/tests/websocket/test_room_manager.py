"""
Tests for WebSocket room manager.

This module tests the room subscription and broadcasting functionality including
room creation, subscription management, and message broadcasting.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock

from app.websocket.room_manager import RoomManager, Room


@pytest.fixture
def room_manager():
    """Create a room manager for testing."""
    return RoomManager(cleanup_interval=1)


class TestRoom:
    """Test Room class."""

    def test_room_creation(self):
        """Test room creation."""
        room = Room("test-room", "execution", {"execution_id": "123"})

        assert room.room_id == "test-room"
        assert room.room_type == "execution"
        assert room.metadata == {"execution_id": "123"}
        assert room.created_at > 0
        assert room.message_count == 0
        assert len(room.connections) == 0
        assert room.is_empty is True
        assert room.connection_count == 0

    def test_add_connection(self):
        """Test adding connection to room."""
        room = Room("test-room", "execution")
        room.add_connection("conn-1")

        assert "conn-1" in room.connections
        assert room.connection_count == 1
        assert room.is_empty is False
        assert room.has_connection("conn-1") is True

    def test_remove_connection(self):
        """Test removing connection from room."""
        room = Room("test-room", "execution")
        room.add_connection("conn-1")
        room.add_connection("conn-2")

        room.remove_connection("conn-1")

        assert "conn-1" not in room.connections
        assert "conn-2" in room.connections
        assert room.connection_count == 1
        assert room.is_empty is False

    def test_remove_nonexistent_connection(self):
        """Test removing non-existent connection."""
        room = Room("test-room", "execution")
        room.remove_connection("non-existent")  # Should not raise error

    def test_has_connection(self):
        """Test checking if connection exists in room."""
        room = Room("test-room", "execution")
        room.add_connection("conn-1")

        assert room.has_connection("conn-1") is True
        assert room.has_connection("conn-2") is False

    def test_is_empty(self):
        """Test checking if room is empty."""
        room = Room("test-room", "execution")
        assert room.is_empty is True

        room.add_connection("conn-1")
        assert room.is_empty is False

        room.remove_connection("conn-1")
        assert room.is_empty is True


class TestRoomManager:
    """Test RoomManager class."""

    def test_create_room(self, room_manager):
        """Test creating a room."""
        room = room_manager.create_room(
            "test-room",
            "execution",
            {"execution_id": "123"}
        )

        assert isinstance(room, Room)
        assert room.room_id == "test-room"
        assert room.room_type == "execution"
        assert room.metadata == {"execution_id": "123"}
        assert "test-room" in room_manager.rooms

    def test_create_room_overwrite(self, room_manager):
        """Test creating a room with overwrite."""
        # Create initial room
        room1 = room_manager.create_room("test-room", "execution")
        room1.metadata["initial"] = True

        # Create room with overwrite=False (should fail)
        with pytest.raises(ValueError):
            room_manager.create_room("test-room", "workflow", overwrite=False)

        # Create room with overwrite=True (should succeed)
        room2 = room_manager.create_room("test-room", "workflow", overwrite=True)
        assert room2.room_type == "workflow"
        assert "initial" not in room2.metadata

    def test_get_room(self, room_manager):
        """Test getting a room."""
        # Create a room
        created_room = room_manager.create_room("test-room", "execution")

        # Get the room
        retrieved_room = room_manager.get_room("test-room")
        assert retrieved_room is created_room

        # Get non-existent room
        non_existent = room_manager.get_room("non-existent")
        assert non_existent is None

    def test_delete_room(self, room_manager):
        """Test deleting a room."""
        # Create a room
        room = room_manager.create_room("test-room", "execution")
        room.add_connection("conn-1")
        room.add_connection("conn-2")

        # Delete the room
        room_manager.delete_room("test-room")

        assert "test-room" not in room_manager.rooms
        # Connections should also be cleaned up from tracking
        assert "test-room" not in room_manager.connection_rooms

    def test_delete_nonexistent_room(self, room_manager):
        """Test deleting a non-existent room."""
        room_manager.delete_room("non-existent")  # Should not raise error

    @pytest.mark.asyncio
    async def test_subscribe_connection(self, room_manager):
        """Test subscribing a connection to a room."""
        # Subscribe connection to room
        success = await room_manager.subscribe_connection(
            "conn-1",
            "test-room",
            "execution",
            {"execution_id": "123"}
        )

        assert success is True

        # Check room was created and connection added
        room = room_manager.get_room("test-room")
        assert room is not None
        assert room.has_connection("conn-1") is True

        # Check connection tracking
        assert "conn-1" in room_manager.connection_rooms
        assert "test-room" in room_manager.connection_rooms["conn-1"]

    @pytest.mark.asyncio
    async def test_subscribe_existing_room(self, room_manager):
        """Test subscribing to an existing room."""
        # Create room first
        room_manager.create_room("test-room", "execution")

        # Subscribe connection
        success = await room_manager.subscribe_connection(
            "conn-1",
            "test-room",
            "execution"
        )

        assert success is True

        room = room_manager.get_room("test-room")
        assert room.has_connection("conn-1") is True

    @pytest.mark.asyncio
    async def test_unsubscribe_connection(self, room_manager):
        """Test unsubscribing a connection from a room."""
        # Subscribe first
        await room_manager.subscribe_connection("conn-1", "test-room", "execution")

        # Unsubscribe
        success = await room_manager.unsubscribe_connection("conn-1", "test-room")
        assert success is True

        # Check connection removed from room
        room = room_manager.get_room("test-room")
        assert not room.has_connection("conn-1")

        # Check connection tracking updated
        assert "test-room" not in room_manager.connection_rooms.get("conn-1", set())

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_connection(self, room_manager):
        """Test unsubscribing a non-existent connection."""
        success = await room_manager.unsubscribe_connection("conn-1", "test-room")
        assert success is False

    @pytest.mark.asyncio
    async def test_unsubscribe_from_all_rooms(self, room_manager):
        """Test unsubscribing a connection from all rooms."""
        # Subscribe to multiple rooms
        await room_manager.subscribe_connection("conn-1", "room-1", "execution")
        await room_manager.subscribe_connection("conn-1", "room-2", "agent")
        await room_manager.subscribe_connection("conn-1", "room-3", "workflow")

        # Unsubscribe from all
        unsubscribed_count = await room_manager.unsubscribe_connection_from_all_rooms("conn-1")
        assert unsubscribed_count == 3

        # Check connection removed from all rooms
        assert "conn-1" not in room_manager.connection_rooms
        for room_id in ["room-1", "room-2", "room-3"]:
            room = room_manager.get_room(room_id)
            assert not room.has_connection("conn-1")

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, room_manager):
        """Test broadcasting message to a room."""
        # Mock connection manager
        mock_connection_manager = AsyncMock()
        mock_connection_manager.send_message.return_value = True

        # Subscribe connections to room
        await room_manager.subscribe_connection("conn-1", "test-room", "execution")
        await room_manager.subscribe_connection("conn-2", "test-room", "execution")

        # Broadcast message
        message = {"type": "test", "data": "hello room"}
        sent_count = await room_manager.broadcast_to_room(
            "test-room",
            message,
            "broadcast",
            mock_connection_manager
        )

        assert sent_count == 2
        assert mock_connection_manager.send_message.call_count == 2

        # Check message format
        for call in mock_connection_manager.send_message.call_args_list:
            args, kwargs = call
            sent_message = args[1]
            assert sent_message["room_id"] == "test-room"
            assert sent_message["room_type"] == "execution"
            assert sent_message["type"] == "test"
            assert sent_message["data"] == "hello room"

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_room(self, room_manager):
        """Test broadcasting to an empty room."""
        mock_connection_manager = AsyncMock()

        # Create room but don't subscribe any connections
        room_manager.create_room("empty-room", "execution")

        # Broadcast message
        message = {"type": "test", "data": "hello empty room"}
        sent_count = await room_manager.broadcast_to_room(
            "empty-room",
            message,
            "broadcast",
            mock_connection_manager
        )

        assert sent_count == 0
        mock_connection_manager.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_room(self, room_manager):
        """Test broadcasting to a non-existent room."""
        mock_connection_manager = AsyncMock()

        message = {"type": "test", "data": "hello nonexistent"}
        sent_count = await room_manager.broadcast_to_room(
            "nonexistent-room",
            message,
            "broadcast",
            mock_connection_manager
        )

        assert sent_count == 0
        mock_connection_manager.send_message.assert_not_called()

    def test_get_connection_rooms(self, room_manager):
        """Test getting all rooms for a connection."""
        # Subscribe connection to multiple rooms
        room_manager.create_room("room-1", "execution")
        room_manager.create_room("room-2", "agent")
        room_manager.create_room("room-3", "workflow")

        # Manually add connections (simulating subscription)
        room_manager.rooms["room-1"].add_connection("conn-1")
        room_manager.rooms["room-2"].add_connection("conn-1")
        room_manager.rooms["room-3"].add_connection("conn-2")  # Different connection

        room_manager.connection_rooms["conn-1"] = {"room-1", "room-2"}
        room_manager.connection_rooms["conn-2"] = {"room-3"}

        # Get connection rooms
        conn1_rooms = room_manager.get_connection_rooms("conn-1")
        conn2_rooms = room_manager.get_connection_rooms("conn-2")

        assert len(conn1_rooms) == 2
        assert len(conn2_rooms) == 1

        conn1_room_ids = [room.room_id for room in conn1_rooms]
        assert "room-1" in conn1_room_ids
        assert "room-2" in conn1_room_ids
        assert "room-3" not in conn1_room_ids

    def test_get_rooms_by_type(self, room_manager):
        """Test getting rooms by type."""
        # Create rooms of different types
        room_manager.create_room("exec-1", "execution")
        room_manager.create_room("exec-2", "execution")
        room_manager.create_room("agent-1", "agent")
        room_manager.create_room("workflow-1", "workflow")

        # Get rooms by type
        execution_rooms = room_manager.get_rooms_by_type("execution")
        agent_rooms = room_manager.get_rooms_by_type("agent")
        workflow_rooms = room_manager.get_rooms_by_type("workflow")

        assert len(execution_rooms) == 2
        assert len(agent_rooms) == 1
        assert len(workflow_rooms) == 1

        exec_room_ids = [room.room_id for room in execution_rooms]
        assert "exec-1" in exec_room_ids
        assert "exec-2" in exec_room_ids

    def test_get_room_stats(self, room_manager):
        """Test getting room statistics."""
        # Create some rooms
        room1 = room_manager.create_room("room-1", "execution")
        room2 = room_manager.create_room("room-2", "agent")
        room3 = room_manager.create_room("room-3", "execution")

        # Add some connections
        room1.add_connection("conn-1")
        room1.add_connection("conn-2")
        room2.add_connection("conn-3")
        room3.add_connection("conn-4")
        room3.add_connection("conn-5")
        room3.add_connection("conn-6")

        # Increment message counts
        room1.message_count = 10
        room2.message_count = 5
        room3.message_count = 15

        stats = room_manager.get_room_stats()

        assert stats["total_rooms"] == 3
        assert stats["total_subscriptions"] == 6  # Total connections across all rooms
        assert stats["average_connections_per_room"] == 2.0

        # Check rooms by type
        assert "rooms_by_type" in stats
        assert stats["rooms_by_type"]["execution"]["count"] == 2
        assert stats["rooms_by_type"]["execution"]["connections"] == 5  # room1 (2) + room3 (3)
        assert stats["rooms_by_type"]["execution"]["messages"] == 25  # room1 (10) + room3 (15)
        assert stats["rooms_by_type"]["agent"]["count"] == 1
        assert stats["rooms_by_type"]["agent"]["connections"] == 1
        assert stats["rooms_by_type"]["agent"]["messages"] == 5

    @pytest.mark.asyncio
    async def test_cleanup_empty_rooms(self, room_manager):
        """Test cleanup of empty rooms."""
        # Create rooms
        room1 = room_manager.create_room("room-1", "execution")
        room2 = room_manager.create_room("room-2", "agent")

        # Add connection to one room
        room1.add_connection("conn-1")

        # Trigger cleanup (wait a bit for cleanup delay)
        await asyncio.sleep(0.1)
        await room_manager._maybe_cleanup_room("room-2")

        # Empty room should be deleted
        assert room_manager.get_room("room-2") is None
        assert "room-2" not in room_manager.rooms

        # Non-empty room should remain
        assert room_manager.get_room("room-1") is not None

    @pytest.mark.asyncio
    async def test_shutdown(self, room_manager):
        """Test room manager shutdown."""
        # Create some rooms and connections
        room_manager.create_room("room-1", "execution")
        room_manager.create_room("room-2", "agent")
        room_manager.connection_rooms["conn-1"] = {"room-1"}
        room_manager.connection_rooms["conn-2"] = {"room-2"}

        # Shutdown
        await room_manager.shutdown()

        # Everything should be cleared
        assert len(room_manager.rooms) == 0
        assert len(room_manager.connection_rooms) == 0


@pytest.mark.asyncio
async def test_room_manager_concurrent_operations():
    """Test room manager with concurrent operations."""
    manager = RoomManager()

    # Concurrent subscriptions
    subscription_tasks = []
    for i in range(10):
        task = manager.subscribe_connection(
            f"conn-{i}",
            f"room-{i % 3}",  # 3 rooms, connections distributed
            "execution"
        )
        subscription_tasks.append(task)

    await asyncio.gather(*subscription_tasks)

    # Check all connections subscribed
    assert len(manager.connection_rooms) == 10
    assert len(manager.rooms) == 3

    # Check room populations
    for room_id in ["room-0", "room-1", "room-2"]:
        room = manager.get_room(room_id)
        assert room.connection_count > 0

    # Concurrent unsubscriptions
    unsubscription_tasks = []
    for i in range(10):
        task = manager.unsubscribe_connection(
            f"conn-{i}",
            f"room-{i % 3}"
        )
        unsubscription_tasks.append(task)

    await asyncio.gather(*unsubscription_tasks)

    # All should be unsubscribed
    assert len(manager.connection_rooms) == 0
    for room_id in ["room-0", "room-1", "room-2"]:
        room = manager.get_room(room_id)
        assert room.is_empty