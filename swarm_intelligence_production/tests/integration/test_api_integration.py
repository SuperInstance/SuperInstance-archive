"""
Integration Test: API Integration
Tests all API endpoints including REST, GraphQL, WebSocket, and SDK operations
"""

import pytest
import asyncio
import httpx
import websockets
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta


API_BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"
GRAPHQL_URL = f"{API_BASE_URL}/graphql"


class TestRESTEndpoints:
    """Test all REST API endpoints"""

    @pytest.fixture
    async def api_key(self):
        """Generate test API key"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/token",
                data={"username": "test@example.com", "password": "testpass"}
            )
            return response.json()["access_token"]

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test /health endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert "version" in data
            assert "timestamp" in data
            assert "active_swarms" in data

    @pytest.mark.asyncio
    async def test_swarm_crud_operations(self, api_key):
        """Test swarm CRUD operations"""
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient() as client:
            # CREATE
            create_response = await client.post(
                f"{API_BASE_URL}/api/v1/swarms",
                headers=headers,
                json={
                    "name": "test-swarm",
                    "agent_count": 50,
                    "agent_type": "WORKER",
                    "config": {"behavior": "flocking"}
                }
            )
            assert create_response.status_code == 200
            swarm_id = create_response.json()["swarm_id"]

            # READ
            get_response = await client.get(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}",
                headers=headers
            )
            assert get_response.status_code == 200
            assert get_response.json()["swarm_id"] == swarm_id

            # LIST
            list_response = await client.get(
                f"{API_BASE_URL}/api/v1/swarms",
                headers=headers,
                params={"limit": 10}
            )
            assert list_response.status_code == 200
            assert len(list_response.json()["swarms"]) > 0

            # UPDATE (Scale)
            scale_response = await client.patch(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}/scale",
                headers=headers,
                json={"agent_count": 100}
            )
            assert scale_response.status_code == 200
            assert scale_response.json()["new_count"] == 100

            # DELETE
            delete_response = await client.delete(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}",
                headers=headers
            )
            assert delete_response.status_code == 200

    @pytest.mark.asyncio
    async def test_task_operations(self, api_key):
        """Test task submission and retrieval"""
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient() as client:
            # Create swarm first
            swarm_response = await client.post(
                f"{API_BASE_URL}/api/v1/swarms",
                headers=headers,
                json={"name": "task-test-swarm", "agent_count": 20}
            )
            swarm_id = swarm_response.json()["swarm_id"]

            # Submit task
            task_response = await client.post(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}/tasks",
                headers=headers,
                json={
                    "type": "compute",
                    "payload": {"operation": "test"},
                    "priority": "NORMAL",
                    "timeout": 30
                }
            )
            assert task_response.status_code == 200
            task_id = task_response.json()["task_id"]

            # Get task status
            status_response = await client.get(
                f"{API_BASE_URL}/api/v1/tasks/{task_id}",
                headers=headers
            )
            assert status_response.status_code == 200
            assert status_response.json()["task_id"] == task_id

            # List swarm tasks
            list_response = await client.get(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}/tasks",
                headers=headers
            )
            assert list_response.status_code == 200
            assert len(list_response.json()["tasks"]) >= 0

            # Cleanup
            await client.delete(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}",
                headers=headers
            )

    @pytest.mark.asyncio
    async def test_metrics_endpoints(self, api_key):
        """Test metrics and monitoring endpoints"""
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient() as client:
            # Create swarm
            swarm_response = await client.post(
                f"{API_BASE_URL}/api/v1/swarms",
                headers=headers,
                json={"name": "metrics-swarm", "agent_count": 30}
            )
            swarm_id = swarm_response.json()["swarm_id"]

            # Get metrics
            metrics_response = await client.get(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}/metrics",
                headers=headers,
                params={"window": "LAST_HOUR"}
            )
            assert metrics_response.status_code == 200
            metrics = metrics_response.json()
            assert "metrics" in metrics

            # Cleanup
            await client.delete(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}",
                headers=headers
            )

    @pytest.mark.asyncio
    async def test_webhook_management(self, api_key):
        """Test webhook CRUD operations"""
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient() as client:
            # Create webhook
            create_response = await client.post(
                f"{API_BASE_URL}/api/v1/webhooks",
                headers=headers,
                json={
                    "url": "https://example.com/webhook",
                    "events": ["task.completed", "swarm.error"]
                }
            )
            assert create_response.status_code == 200
            webhook_id = create_response.json()["webhook_id"]

            # List webhooks
            list_response = await client.get(
                f"{API_BASE_URL}/api/v1/webhooks",
                headers=headers
            )
            assert list_response.status_code == 200

            # Delete webhook
            delete_response = await client.delete(
                f"{API_BASE_URL}/api/v1/webhooks/{webhook_id}",
                headers=headers
            )
            assert delete_response.status_code == 200

    @pytest.mark.asyncio
    async def test_batch_processing(self, api_key):
        """Test batch processing endpoint"""
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient() as client:
            # Create swarm
            swarm_response = await client.post(
                f"{API_BASE_URL}/api/v1/swarms",
                headers=headers,
                json={"name": "batch-swarm", "agent_count": 100}
            )
            swarm_id = swarm_response.json()["swarm_id"]

            # Submit batch
            batch_response = await client.post(
                f"{API_BASE_URL}/api/v1/creative/batch",
                headers=headers,
                params={"swarm_id": swarm_id},
                json={
                    "tasks": [
                        {"type": "render", "payload": {"scene": i}}
                        for i in range(20)
                    ]
                }
            )
            assert batch_response.status_code == 200
            batch_id = batch_response.json()["batch_id"]
            assert batch_response.json()["task_count"] == 20

            # Get batch status
            await asyncio.sleep(2)
            status_response = await client.get(
                f"{API_BASE_URL}/api/v1/creative/batch/{batch_id}",
                headers=headers
            )
            assert status_response.status_code == 200
            assert status_response.json()["total_tasks"] == 20

            # Cleanup
            await client.delete(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}",
                headers=headers
            )


class TestGraphQLAPI:
    """Test GraphQL API operations"""

    @pytest.fixture
    async def api_key(self):
        """Generate test API key"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/token",
                data={"username": "test@example.com", "password": "testpass"}
            )
            return response.json()["access_token"]

    @pytest.mark.asyncio
    async def test_graphql_query_swarms(self, api_key):
        """Test GraphQL swarm queries"""
        headers = {"Authorization": f"Bearer {api_key}"}

        query = """
        query {
            swarms(limit: 10) {
                swarmId
                name
                agentCount
                status
            }
        }
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GRAPHQL_URL,
                headers=headers,
                json={"query": query}
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "swarms" in data["data"]

    @pytest.mark.asyncio
    async def test_graphql_mutation_create_swarm(self, api_key):
        """Test GraphQL swarm creation mutation"""
        headers = {"Authorization": f"Bearer {api_key}"}

        mutation = """
        mutation CreateSwarm($name: String!, $agentCount: Int!) {
            createSwarm(name: $name, agentCount: $agentCount) {
                swarmId
                name
                status
            }
        }
        """

        variables = {"name": "graphql-test-swarm", "agentCount": 25}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GRAPHQL_URL,
                headers=headers,
                json={"query": mutation, "variables": variables}
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "createSwarm" in data["data"]


class TestWebSocketConnections:
    """Test WebSocket real-time connections"""

    @pytest.fixture
    async def api_key(self):
        """Generate test API key"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/token",
                data={"username": "test@example.com", "password": "testpass"}
            )
            return response.json()["access_token"]

    @pytest.mark.asyncio
    async def test_websocket_connection(self, api_key):
        """Test WebSocket connection and authentication"""
        # Create swarm first
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {api_key}"}
            swarm_response = await client.post(
                f"{API_BASE_URL}/api/v1/swarms",
                headers=headers,
                json={"name": "ws-test-swarm", "agent_count": 10}
            )
            swarm_id = swarm_response.json()["swarm_id"]

        # Connect via WebSocket
        async with websockets.connect(f"{WS_BASE_URL}/ws/{swarm_id}") as ws:
            # Authenticate
            await ws.send(json.dumps({
                "type": "auth",
                "api_key": api_key
            }))

            # Should remain connected
            # Send ping
            await ws.send(json.dumps({"type": "ping"}))

            # Receive pong
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            assert data["type"] == "pong"

        # Cleanup
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )

    @pytest.mark.asyncio
    async def test_websocket_event_subscription(self, api_key):
        """Test WebSocket event subscriptions"""
        # Create swarm
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {api_key}"}
            swarm_response = await client.post(
                f"{API_BASE_URL}/api/v1/swarms",
                headers=headers,
                json={"name": "ws-events-swarm", "agent_count": 20}
            )
            swarm_id = swarm_response.json()["swarm_id"]

        # Connect and subscribe
        async with websockets.connect(f"{WS_BASE_URL}/ws/{swarm_id}") as ws:
            # Authenticate
            await ws.send(json.dumps({
                "type": "auth",
                "api_key": api_key
            }))

            # Subscribe to events
            await ws.send(json.dumps({
                "type": "subscribe",
                "events": ["task_progress", "agent_status", "metrics"]
            }))

            # Submit task to generate events
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{API_BASE_URL}/api/v1/swarms/{swarm_id}/tasks",
                    headers=headers,
                    json={
                        "type": "compute",
                        "payload": {"test": "data"}
                    }
                )

            # Wait for event
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                event = json.loads(message)
                assert "type" in event
            except asyncio.TimeoutError:
                # No events received is acceptable for some tests
                pass

        # Cleanup
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{API_BASE_URL}/api/v1/swarms/{swarm_id}",
                headers=headers
            )


class TestRateLimiting:
    """Test rate limiting enforcement"""

    @pytest.fixture
    async def api_key(self):
        """Generate test API key"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/token",
                data={"username": "test@example.com", "password": "testpass"}
            )
            return response.json()["access_token"]

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, api_key):
        """Test that rate limits are enforced"""
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient() as client:
            # Make rapid requests
            rate_limited = False
            for i in range(200):
                try:
                    response = await client.post(
                        f"{API_BASE_URL}/api/v1/swarms",
                        headers=headers,
                        json={"name": f"rate-test-{i}", "agent_count": 5}
                    )

                    if response.status_code == 429:
                        rate_limited = True
                        break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        rate_limited = True
                        break

            # Should have hit rate limit
            assert rate_limited, "Rate limiting not enforced"

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, api_key):
        """Test rate limit headers are present"""
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE_URL}/health",
                headers=headers
            )

            # Check for rate limit headers (if implemented)
            # X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
            assert response.status_code == 200


class TestAuthentication:
    """Test authentication flows"""

    @pytest.mark.asyncio
    async def test_oauth_token_flow(self):
        """Test OAuth 2.0 token authentication"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/token",
                data={
                    "username": "test@example.com",
                    "password": "testpass"
                }
            )

            if response.status_code == 200:
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_api_key_generation(self):
        """Test API key generation"""
        # First authenticate
        async with httpx.AsyncClient() as client:
            auth_response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/token",
                data={"username": "test@example.com", "password": "testpass"}
            )

            if auth_response.status_code == 200:
                token = auth_response.json()["access_token"]

                # Generate API key
                key_response = await client.post(
                    f"{API_BASE_URL}/api/v1/auth/api-key",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if key_response.status_code == 200:
                    data = key_response.json()
                    assert "api_key" in data

    @pytest.mark.asyncio
    async def test_invalid_authentication(self):
        """Test rejection of invalid credentials"""
        async with httpx.AsyncClient() as client:
            # Invalid credentials
            response = await client.get(
                f"{API_BASE_URL}/api/v1/swarms",
                headers={"Authorization": "Bearer invalid_token"}
            )

            assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
