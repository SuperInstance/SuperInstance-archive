"""
Swarm Intelligence SDK - Client Implementation
"""

import httpx
import asyncio
import websockets
import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

from .models import (
    Swarm, Agent, Task, Metrics, SwarmConfig,
    SwarmStatus, AgentType, TaskStatus, Priority
)
from .exceptions import (
    SwarmCreationError, TaskSubmissionError,
    AuthenticationError, RateLimitError
)


class AsyncSwarmClient:
    """
    Async client for Swarm Intelligence Platform

    Example:
        async with AsyncSwarmClient(api_key="your-key") as client:
            swarm = await client.create_swarm(
                name="my-swarm",
                agent_count=10
            )
            task = await swarm.submit_task(
                type="process",
                payload={"data": "example"}
            )
            result = await task.wait_for_completion()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.swarm.dev",
        timeout: int = 30
    ):
        """
        Initialize async swarm client

        Args:
            api_key: Your API key for authentication
            base_url: Base URL of the API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=timeout
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def create_swarm(
        self,
        name: str,
        agent_count: int = 10,
        agent_type: AgentType = AgentType.WORKER,
        config: Optional[SwarmConfig] = None
    ) -> Swarm:
        """
        Create a new swarm

        Args:
            name: Name for the swarm
            agent_count: Number of agents to spawn
            agent_type: Type of agents
            config: Optional configuration object

        Returns:
            Swarm object for further operations

        Raises:
            SwarmCreationError: If swarm creation fails
            AuthenticationError: If API key is invalid
            RateLimitError: If rate limit is exceeded
        """
        payload = {
            "name": name,
            "agent_count": agent_count,
            "agent_type": agent_type.value,
            "config": config.dict() if config else None
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/swarms",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            return Swarm(client=self, **data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            else:
                raise SwarmCreationError(f"Failed to create swarm: {e}")

    async def get_swarm(self, swarm_id: str) -> Swarm:
        """Retrieve an existing swarm by ID"""
        response = await self.client.get(
            f"{self.base_url}/api/v1/swarms/{swarm_id}"
        )
        response.raise_for_status()
        data = response.json()

        return Swarm(client=self, **data)

    async def list_swarms(
        self,
        status: Optional[SwarmStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Swarm]:
        """List all swarms with optional filtering"""
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status.value

        response = await self.client.get(
            f"{self.base_url}/api/v1/swarms",
            params=params
        )
        response.raise_for_status()
        data = response.json()

        return [Swarm(client=self, **swarm) for swarm in data["swarms"]]

    async def get_task(self, task_id: str) -> Task:
        """Get task by ID"""
        response = await self.client.get(
            f"{self.base_url}/api/v1/tasks/{task_id}"
        )
        response.raise_for_status()
        data = response.json()

        return Task(client=self, **data)


class SwarmClient:
    """
    Synchronous client for Swarm Intelligence Platform

    Example:
        client = SwarmClient(api_key="your-key")
        swarm = client.create_swarm(name="my-swarm", agent_count=5)
        task = swarm.submit_task(type="process", payload={"data": "example"})
        result = task.wait_for_completion()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.swarm.dev",
        timeout: int = 30
    ):
        """
        Initialize swarm client

        Args:
            api_key: Your API key for authentication
            base_url: Base URL of the API
            timeout: Request timeout in seconds
        """
        self.async_client = AsyncSwarmClient(api_key, base_url, timeout)
        self._loop = None

    def _get_loop(self):
        """Get or create event loop"""
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def _run_async(self, coro):
        """Run async coroutine in sync context"""
        loop = self._get_loop()
        return loop.run_until_complete(coro)

    def create_swarm(
        self,
        name: str,
        agent_count: int = 10,
        agent_type: AgentType = AgentType.WORKER,
        config: Optional[SwarmConfig] = None
    ) -> Swarm:
        """Create a new swarm (synchronous)"""
        return self._run_async(
            self.async_client.create_swarm(name, agent_count, agent_type, config)
        )

    def get_swarm(self, swarm_id: str) -> Swarm:
        """Get swarm by ID (synchronous)"""
        return self._run_async(self.async_client.get_swarm(swarm_id))

    def list_swarms(
        self,
        status: Optional[SwarmStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Swarm]:
        """List swarms (synchronous)"""
        return self._run_async(
            self.async_client.list_swarms(status, limit, offset)
        )

    def get_task(self, task_id: str) -> Task:
        """Get task by ID (synchronous)"""
        return self._run_async(self.async_client.get_task(task_id))

    def close(self):
        """Close client"""
        self._run_async(self.async_client.close())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
