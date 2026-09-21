"""
Test configuration for Hatchery Management service.
Generated on 2025-08-25
"""

import pytest
import asyncio
from unittest.mock import Mock
from hatchery_management.database import get_database


@pytest.fixture
def mock_db():
    """Mock database fixture."""
    return Mock()


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def override_dependencies(mock_db):
    """Override dependencies for testing."""
    from hatchery_management.main import app
    
    app.dependency_overrides[get_database] = lambda: mock_db
    yield
    app.dependency_overrides.clear()
