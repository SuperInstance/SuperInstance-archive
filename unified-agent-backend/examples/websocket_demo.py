#!/usr/bin/env python3
"""
WebSocket Demo for unified-agent-backend.

This script demonstrates the WebSocket functionality including:
- Connection management
- Room-based subscriptions
- Real-time message broadcasting
- Integration with workflow execution

Run this script to see WebSocket functionality in action.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any

# Add the src directory to the path so we can import app modules
sys.path.insert(0, '/home/activeloguser/unified-agent-backend/src')

from app.websocket.manager import WebSocketManager
from app.websocket.integrations import (
    WorkflowExecutorWebSocketIntegration,
    AgentServiceWebSocketIntegration,
    NotificationServiceWebSocketIntegration
)
from app.schemas.websocket import create_execution_started_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockWebSocket:
    """Mock WebSocket connection for demonstration."""

    def __init__(self, connection_id: str, user_id: str = "demo-user"):
        self.connection_id = connection_id
        self.user_id = user_id
        self.messages = []
        self.accepted = False
        self.closed = False
        self.query_params = {}
        self.headers = {}
        self.client = {"host": "localhost", "port": 8000}

    async def accept(self):
        """Accept the WebSocket connection."""
        self.accepted = True
        logger.info(f"WebSocket {self.connection_id} accepted")

    async def send_text(self, message: str):
        """Send a text message."""
        try:
            message_data = json.loads(message)
            self.messages.append(message_data)
            logger.info(f"WebSocket {self.connection_id} received: {message_data.get('type', 'unknown')}")

            # Print nicely formatted message
            if message_data.get('type') == 'welcome':
                print(f"\n✅ {self.connection_id}: Connected successfully!")
            elif message_data.get('type') == 'subscription_confirmed':
                room_id = message_data.get('data', {}).get('room_id', 'unknown')
                print(f"✅ {self.connection_id}: Subscribed to {room_id}")
            elif message_data.get('type') in ['execution_started', 'execution_progress', 'execution_completed']:
                exec_data = message_data.get('data', {})
                print(f"🔄 {self.connection_id}: {message_data.get('type')} - {exec_data.get('execution_id', 'unknown')}")
            elif message_data.get('type') == 'notification':
                notif_data = message_data.get('data', {})
                print(f"🔔 {self.connection_id}: {notif_data.get('title', 'Notification')}")
            else:
                print(f"📨 {self.connection_id}: {message_data.get('type', 'message')}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message: {message}")

    async def close(self, code: int = 1000, reason: str = ""):
        """Close the WebSocket connection."""
        self.closed = True
        logger.info(f"WebSocket {self.connection_id} closed: {reason}")


async def demo_basic_connection():
    """Demonstrate basic WebSocket connection and messaging."""
    print("\n" + "="*60)
    print("🚀 DEMO 1: Basic WebSocket Connection")
    print("="*60)

    manager = WebSocketManager(require_auth=False)
    await manager.start()

    try:
        # Create mock WebSocket
        websocket = MockWebSocket("client-1", "demo-user")

        # Connect to WebSocket
        print("Connecting client...")
        connection_info = await manager.handle_connection(websocket)

        if connection_info:
            print(f"✅ Connected! Connection ID: {connection_info.connection_id}")

            # Send a direct message
            print("Sending direct message...")
            await manager.send_message_to_connection(
                connection_info.connection_id,
                {"type": "greeting", "message": "Hello from WebSocket manager!"}
            )

            # Wait a moment to see the messages
            await asyncio.sleep(1)

        else:
            print("❌ Connection failed")

    finally:
        await manager.stop()


async def demo_room_subscriptions():
    """Demonstrate room-based subscriptions."""
    print("\n" + "="*60)
    print("🚀 DEMO 2: Room-Based Subscriptions")
    print("="*60)

    manager = WebSocketManager(require_auth=False)
    await manager.start()

    try:
        # Create multiple clients
        clients = []
        connection_infos = []

        for i, (client_name, user_id) in enumerate([
            ("execution-client", "workflow-user"),
            ("agent-monitor", "devops-user"),
            ("general-client", "regular-user")
        ]):
            websocket = MockWebSocket(client_name, user_id)
            connection_info = await manager.handle_connection(websocket)

            if connection_info:
                clients.append(websocket)
                connection_infos.append(connection_info)
                print(f"✅ {client_name} connected")

        # Subscribe clients to different rooms
        print("\nSubscribing clients to rooms...")

        # Execution client subscribes to execution updates
        await manager.room_manager.subscribe_connection(
            connection_infos[0].connection_id,
            "execution:demo-execution-123",
            "execution",
            {"execution_id": "demo-execution-123"}
        )

        # Agent monitor subscribes to agent updates
        await manager.room_manager.subscribe_connection(
            connection_infos[1].connection_id,
            "agent:demo-agent-456",
            "agent",
            {"agent_id": "demo-agent-456"}
        )

        # General client subscribes to multiple rooms
        await manager.room_manager.subscribe_connection(
            connection_infos[2].connection_id,
            "execution:demo-execution-123",
            "execution"
        )
        await manager.room_manager.subscribe_connection(
            connection_infos[2].connection_id,
            "agent:demo-agent-456",
            "agent"
        )

        await asyncio.sleep(1)

        # Broadcast messages to different rooms
        print("\nBroadcasting messages to rooms...")

        # Execution update
        execution_message = {
            "type": "execution_progress",
            "data": {
                "execution_id": "demo-execution-123",
                "progress_percentage": 45.0,
                "current_node_id": "data-processor",
                "status": "Running data processing step..."
            }
        }
        await manager.broadcast_to_room("execution:demo-execution-123", execution_message)
        await asyncio.sleep(0.5)

        # Agent update
        agent_message = {
            "type": "agent_status_changed",
            "data": {
                "agent_id": "demo-agent-456",
                "old_status": "idle",
                "new_status": "busy",
                "reason": "Processing workflow task"
            }
        }
        await manager.broadcast_to_room("agent:demo-agent-456", agent_message)
        await asyncio.sleep(0.5)

        # Send notification to specific user
        await manager.send_message_to_user(
            "workflow-user",
            {
                "type": "notification",
                "title": "Execution Update",
                "message": "Your workflow execution is 45% complete",
                "level": "info"
            }
        )

        await asyncio.sleep(1)

        # Show statistics
        stats = manager.get_stats()
        print(f"\n📊 WebSocket Statistics:")
        print(f"   Total Connections: {stats['connection_stats']['total_connections']}")
        print(f"   Total Rooms: {stats['room_stats']['total_rooms']}")
        print(f"   Total Subscriptions: {stats['room_stats']['total_subscriptions']}")

    finally:
        await manager.stop()


async def demo_workflow_integration():
    """Demonstrate workflow execution integration."""
    print("\n" + "="*60)
    print("🚀 DEMO 3: Workflow Execution Integration")
    print("="*60)

    manager = WebSocketManager(require_auth=False)
    await manager.start()

    try:
        # Create workflow client
        websocket = MockWebSocket("workflow-client", "workflow-user")
        connection_info = await manager.handle_connection(websocket)

        if not connection_info:
            print("❌ Failed to connect workflow client")
            return

        # Subscribe to execution updates
        await manager.room_manager.subscribe_connection(
            connection_info.connection_id,
            "execution:workflow-demo-123",
            "execution",
            {"execution_id": "workflow-demo-123"}
        )

        # Create workflow executor integration
        workflow_integration = WorkflowExecutorWebSocketIntegration(manager)

        print("\n🔄 Simulating workflow execution...")

        # Notify execution started
        await workflow_integration.notify_execution_started(
            execution_id="workflow-demo-123",
            workflow_id="demo-workflow-456",
            user_id="workflow-user",
            input_data={"query": "process customer data", "limit": 100}
        )
        await asyncio.sleep(0.5)

        # Notify node started
        await workflow_integration.notify_node_started(
            execution_id="workflow-demo-123",
            node_id="node-1",
            node_type="data_fetcher",
            input_data={"query": "process customer data"}
        )
        await asyncio.sleep(0.5)

        # Notify progress
        await workflow_integration.notify_execution_progress(
            execution_id="workflow-demo-123",
            workflow_id="demo-workflow-456",
            progress_percentage=25.0,
            current_node_id="node-1",
            completed_nodes=0,
            total_nodes=4
        )
        await asyncio.sleep(0.5)

        # Notify node completed
        await workflow_integration.notify_node_completed(
            execution_id="workflow-demo-123",
            node_id="node-1",
            duration_seconds=2.5,
            output_data={"records_fetched": 150},
            metrics={"efficiency": 0.95}
        )
        await asyncio.sleep(0.5)

        # Notify more progress
        await workflow_integration.notify_execution_progress(
            execution_id="workflow-demo-123",
            workflow_id="demo-workflow-456",
            progress_percentage=50.0,
            current_node_id="node-2",
            completed_nodes=1,
            total_nodes=4
        )
        await asyncio.sleep(0.5)

        # Notify execution completed
        await workflow_integration.notify_execution_completed(
            execution_id="workflow-demo-123",
            workflow_id="demo-workflow-456",
            status="completed",
            duration_seconds=8.7,
            output_data={"processed_records": 150, "result": "success"},
            metrics={"total_nodes": 4, "efficiency": 0.92},
            user_id="workflow-user"
        )

        await asyncio.sleep(1)

    finally:
        await manager.stop()


async def demo_agent_monitoring():
    """Demonstrate agent monitoring integration."""
    print("\n" + "="*60)
    print("🚀 DEMO 4: Agent Monitoring Integration")
    print("="*60)

    manager = WebSocketManager(require_auth=False)
    await manager.start()

    try:
        # Create monitoring client
        websocket = MockWebSocket("monitor-client", "devops-user")
        connection_info = await manager.handle_connection(websocket)

        if not connection_info:
            print("❌ Failed to connect monitoring client")
            return

        # Subscribe to agent updates
        await manager.room_manager.subscribe_connection(
            connection_info.connection_id,
            "agent:demo-agent-789",
            "agent",
            {"agent_id": "demo-agent-789"}
        )

        # Create agent service integration
        agent_integration = AgentServiceWebSocketIntegration(manager)

        print("\n🤖 Simulating agent activity...")

        # Notify agent status change
        await agent_integration.notify_agent_status_changed(
            agent_id="demo-agent-789",
            old_status="offline",
            new_status="idle",
            reason="Agent started successfully"
        )
        await asyncio.sleep(0.5)

        # Notify health update
        await agent_integration.notify_agent_health_update(
            agent_id="demo-agent-789",
            health_status="healthy",
            cpu_usage=12.5,
            memory_usage=45.2,
            disk_usage=23.8,
            active_tasks=0
        )
        await asyncio.sleep(0.5)

        # Notify task assignment
        await agent_integration.notify_agent_task_assigned(
            agent_id="demo-agent-789",
            task_id="task-456",
            task_type="data_processing",
            priority="normal",
            estimated_duration=30.0
        )
        await asyncio.sleep(0.5)

        # Notify status change to busy
        await agent_integration.notify_agent_status_changed(
            agent_id="demo-agent-789",
            old_status="idle",
            new_status="busy",
            reason="Processing assigned task"
        )
        await asyncio.sleep(0.5)

        # Notify task completed
        await agent_integration.notify_agent_task_completed(
            agent_id="demo-agent-789",
            task_id="task-456",
            status="completed",
            result={"processed_items": 500, "errors": 0},
            duration_seconds=28.3
        )
        await asyncio.sleep(0.5)

        # Notify status change back to idle
        await agent_integration.notify_agent_status_changed(
            agent_id="demo-agent-789",
            old_status="busy",
            new_status="idle",
            reason="Task completed successfully"
        )

        await asyncio.sleep(1)

    finally:
        await manager.stop()


async def main():
    """Run all WebSocket demonstrations."""
    print("🎯 WebSocket Functionality Demo")
    print("=" * 60)
    print("This demo showcases the WebSocket implementation including:")
    print("- Connection management")
    print("- Room-based subscriptions")
    print("- Real-time message broadcasting")
    print("- Workflow execution integration")
    print("- Agent monitoring integration")
    print("\nStarting demonstrations...")

    try:
        await demo_basic_connection()
        await asyncio.sleep(1)

        await demo_room_subscriptions()
        await asyncio.sleep(1)

        await demo_workflow_integration()
        await asyncio.sleep(1)

        await demo_agent_monitoring()

        print("\n" + "="*60)
        print("🎉 All demonstrations completed successfully!")
        print("="*60)
        print("\nThe WebSocket implementation provides:")
        print("✅ Real-time connection management")
        print("✅ Room-based subscription system")
        print("✅ Message broadcasting to targeted audiences")
        print("✅ Integration with workflow execution")
        print("✅ Agent health and task monitoring")
        print("✅ User notification system")
        print("✅ Production-ready error handling")
        print("✅ Comprehensive logging and monitoring")

    except Exception as e:
        logger.error(f"Demonstration failed: {str(e)}")
        print(f"\n❌ Demo failed with error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)