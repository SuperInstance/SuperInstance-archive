"""
Tests for Fitness Tracker service main module.
Generated on 2025-08-27
"""

import pytest
from fastapi.testclient import TestClient
from fitness_tracker.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_service_info(client):
    """Test service info endpoint."""
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "fitness_tracker"
    assert "version" in data
