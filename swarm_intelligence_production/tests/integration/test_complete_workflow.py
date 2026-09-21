"""
Integration Test: Complete User Journey
Tests end-to-end workflow from user registration to swarm deployment and task completion
"""

import pytest
import asyncio
import time
import json
from typing import Dict, Any
import httpx
import websockets

from api.sdks.python.swarm_intelligence import AsyncSwarmClient, SwarmClient
from api.sdks.python.swarm_intelligence.models import AgentType, Priority, TaskStatus, SwarmStatus
from api.sdks.python.swarm_intelligence.exceptions import SwarmCreationError, AuthenticationError


# Test Configuration
API_BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"
TEST_USER_EMAIL = "test@swarmplatform.io"
TEST_USER_PASSWORD = "SecurePassword123!"


class TestCompleteUserJourney:
    """End-to-end test suite for complete user workflow"""

    @pytest.fixture
    async def authenticated_client(self):
        """Setup authenticated client for testing"""
        # Step 1: User Registration/Authentication
        async with httpx.AsyncClient() as http_client:
            # Register or login user
            auth_response = await http_client.post(
                f"{API_BASE_URL}/api/v1/auth/token",
                data={
                    "username": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD
                }
            )
            assert auth_response.status_code == 200, "Authentication failed"

            auth_data = auth_response.json()
            api_key = auth_data["access_token"]

            # Create authenticated swarm client
            client = AsyncSwarmClient(
                api_key=api_key,
                base_url=API_BASE_URL
            )

            yield client

            # Cleanup
            await client.close()

    @pytest.mark.asyncio
    async def test_complete_user_journey(self, authenticated_client):
        """
        Test complete user journey:
        1. User registration via API
        2. Create first swarm
        3. Deploy agents
        4. Submit creative task
        5. Monitor real-time updates via WebSocket
        6. Receive and validate results
        7. Check billing and usage
        """
        client = authenticated_client

        # STEP 1: User Registration - Already done in fixture
        print("Step 1: User authenticated successfully")

        # STEP 2: Create first swarm
        print("Step 2: Creating first swarm...")
        swarm = await client.create_swarm(
            name="test-creative-swarm",
            agent_count=100,
            agent_type=AgentType.WORKER,
            config={
                "behavior": "creative_exploration",
                "collaboration": True,
                "pheromone_enabled": True
            }
        )

        assert swarm.swarm_id is not None
        assert swarm.name == "test-creative-swarm"
        assert swarm.agent_count == 100
        print(f"Swarm created: {swarm.swarm_id}")

        # STEP 3: Wait for swarm deployment
        print("Step 3: Waiting for swarm deployment...")
        max_wait = 30  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            swarm_status = await client.get_swarm(swarm.swarm_id)
            if swarm_status.status == SwarmStatus.RUNNING:
                print("Swarm is running!")
                break
            await asyncio.sleep(1)

        assert swarm_status.status == SwarmStatus.RUNNING, "Swarm failed to start"

        # STEP 4: Submit creative task
        print("Step 4: Submitting creative task...")
        task = await swarm.submit_task(
            task_type="creative_generation",
            payload={
                "type": "music_composition",
                "genre": "ambient",
                "duration": 30,
                "mood": "calm",
                "complexity": "medium"
            },
            priority=Priority.HIGH,
            timeout=60
        )

        assert task.task_id is not None
        assert task.status == TaskStatus.QUEUED
        print(f"Task submitted: {task.task_id}")

        # STEP 5: Monitor real-time updates via WebSocket
        print("Step 5: Monitoring task via WebSocket...")
        task_completed = False
        task_result = None

        async with websockets.connect(
            f"{WS_BASE_URL}/ws/{swarm.swarm_id}"
        ) as websocket:
            # Authenticate WebSocket
            await websocket.send(json.dumps({
                "type": "auth",
                "api_key": client.api_key
            }))

            # Subscribe to task updates
            await websocket.send(json.dumps({
                "type": "subscribe",
                "events": ["task_progress", "task_completed", "agent_status"]
            }))

            # Monitor for 60 seconds max
            start_time = time.time()
            while time.time() - start_time < 60:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )

                    event = json.loads(message)
                    print(f"WebSocket event: {event['type']}")

                    if event["type"] == "task_completed":
                        if event.get("task_id") == task.task_id:
                            task_completed = True
                            task_result = event.get("result")
                            break

                    elif event["type"] == "task_progress":
                        if event.get("task_id") == task.task_id:
                            progress = event.get("progress", 0)
                            print(f"Task progress: {progress}%")

                except asyncio.TimeoutError:
                    # Check task status via API
                    task_status = await client.get_task(task.task_id)
                    if task_status.status == TaskStatus.COMPLETED:
                        task_completed = True
                        task_result = task_status.result
                        break

        # STEP 6: Receive and validate results
        print("Step 6: Validating task results...")
        assert task_completed, "Task did not complete in time"
        assert task_result is not None, "Task result is empty"

        # Validate result structure
        if isinstance(task_result, dict):
            assert "output" in task_result or "data" in task_result
            print(f"Task result received: {len(str(task_result))} bytes")

        # STEP 7: Check billing and usage
        print("Step 7: Checking billing and usage...")
        metrics = await swarm.get_metrics(window="LAST_HOUR")

        assert metrics is not None
        assert "tasks_completed" in metrics.metrics
        assert metrics.metrics["tasks_completed"] >= 1

        # Verify resource usage
        assert "agent_utilization" in metrics.metrics
        assert 0 <= metrics.metrics["agent_utilization"] <= 1.0

        print("User journey test completed successfully!")

        # Cleanup
        await swarm.terminate()

    @pytest.mark.asyncio
    async def test_concurrent_swarm_operations(self, authenticated_client):
        """Test multiple swarms running concurrently"""
        client = authenticated_client

        # Create multiple swarms
        swarms = []
        for i in range(5):
            swarm = await client.create_swarm(
                name=f"concurrent-swarm-{i}",
                agent_count=50,
                agent_type=AgentType.WORKER
            )
            swarms.append(swarm)

        # Wait for all to be running
        await asyncio.sleep(5)

        # Submit tasks to all swarms
        tasks = []
        for swarm in swarms:
            task = await swarm.submit_task(
                task_type="compute",
                payload={"operation": "matrix_multiply", "size": 100}
            )
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.sleep(10)

        # Verify all tasks completed
        completed_count = 0
        for task in tasks:
            task_status = await client.get_task(task.task_id)
            if task_status.status == TaskStatus.COMPLETED:
                completed_count += 1

        assert completed_count >= 4, f"Only {completed_count}/5 tasks completed"

        # Cleanup
        for swarm in swarms:
            await swarm.terminate()

    @pytest.mark.asyncio
    async def test_swarm_scaling(self, authenticated_client):
        """Test dynamic swarm scaling under load"""
        client = authenticated_client

        # Create swarm with initial size
        swarm = await client.create_swarm(
            name="scaling-test-swarm",
            agent_count=50
        )

        await asyncio.sleep(3)

        # Scale up to 200 agents
        await swarm.scale(agent_count=200)
        await asyncio.sleep(5)

        swarm_status = await client.get_swarm(swarm.swarm_id)
        assert swarm_status.agent_count == 200

        # Submit high-load task
        task = await swarm.submit_task(
            task_type="batch_process",
            payload={"items": list(range(1000))}
        )

        # Scale down while task is running
        await asyncio.sleep(2)
        await swarm.scale(agent_count=100)

        # Wait for task completion
        await asyncio.sleep(10)

        task_status = await client.get_task(task.task_id)
        assert task_status.status in [TaskStatus.COMPLETED, TaskStatus.RUNNING]

        # Cleanup
        await swarm.terminate()

    @pytest.mark.asyncio
    async def test_error_recovery(self, authenticated_client):
        """Test system recovery from errors"""
        client = authenticated_client

        # Create swarm
        swarm = await client.create_swarm(
            name="error-recovery-swarm",
            agent_count=100
        )

        await asyncio.sleep(3)

        # Submit task that will fail
        task = await swarm.submit_task(
            task_type="intentional_failure",
            payload={"error_type": "timeout"}
        )

        # Wait for failure
        await asyncio.sleep(15)

        task_status = await client.get_task(task.task_id)
        assert task_status.status == TaskStatus.FAILED

        # Verify swarm is still operational
        swarm_status = await client.get_swarm(swarm.swarm_id)
        assert swarm_status.status == SwarmStatus.RUNNING

        # Submit new successful task
        task2 = await swarm.submit_task(
            task_type="simple_compute",
            payload={"operation": "add", "values": [1, 2, 3]}
        )

        await asyncio.sleep(5)

        task2_status = await client.get_task(task2.task_id)
        assert task2_status.status == TaskStatus.COMPLETED

        # Cleanup
        await swarm.terminate()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, authenticated_client):
        """Test rate limiting enforcement"""
        client = authenticated_client

        # Create swarm
        swarm = await client.create_swarm(
            name="rate-limit-test",
            agent_count=10
        )

        await asyncio.sleep(2)

        # Submit tasks rapidly to trigger rate limit
        rate_limit_hit = False
        task_count = 0

        for i in range(100):
            try:
                task = await swarm.submit_task(
                    task_type="quick_compute",
                    payload={"value": i}
                )
                task_count += 1
            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    rate_limit_hit = True
                    break

        # Should have hit rate limit before 100 tasks
        assert rate_limit_hit or task_count < 100, "Rate limiting not enforced"

        # Cleanup
        await swarm.terminate()


class TestSyncClient:
    """Test synchronous client operations"""

    def test_sync_client_workflow(self):
        """Test synchronous client for blocking operations"""
        # Authenticate
        with httpx.Client() as http_client:
            auth_response = http_client.post(
                f"{API_BASE_URL}/api/v1/auth/token",
                data={
                    "username": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD
                }
            )
            api_key = auth_response.json()["access_token"]

        # Use sync client
        with SwarmClient(api_key=api_key, base_url=API_BASE_URL) as client:
            # Create swarm
            swarm = client.create_swarm(
                name="sync-test-swarm",
                agent_count=20
            )

            assert swarm.swarm_id is not None

            # Submit task
            time.sleep(3)
            task = swarm.submit_task(
                task_type="compute",
                payload={"operation": "factorial", "n": 10}
            )

            assert task.task_id is not None

            # Wait for completion
            time.sleep(10)
            task_status = client.get_task(task.task_id)
            assert task_status.status in [TaskStatus.COMPLETED, TaskStatus.RUNNING]

            # Cleanup
            swarm.terminate()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
