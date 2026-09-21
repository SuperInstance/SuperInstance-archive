"""
WebSocket test configuration and fixtures.

This module provides common fixtures and configuration for WebSocket tests.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def sample_execution_data():
    """Sample execution data for testing."""
    return {
        "execution_id": "test-execution-123",
        "workflow_id": "test-workflow-456",
        "user_id": "test-user-789",
        "input_data": {"param1": "value1", "param2": "value2"},
        "status": "running",
        "started_at": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing."""
    return {
        "agent_id": "test-agent-123",
        "status": "busy",
        "health_status": "healthy",
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "active_tasks": 3,
        "last_heartbeat": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "workflow_id": "test-workflow-456",
        "name": "Test Workflow",
        "description": "A test workflow for WebSocket testing",
        "version": "1.0.0",
        "updated_by": "test-user-789",
        "changes": ["Updated node configuration", "Added new trigger"]
    }