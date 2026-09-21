"""
Tests for Home Power Sharing service main module.
Generated on 2025-08-25
"""

import pytest
from fastapi.testclient import TestClient
from home_power_sharing.main import app


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
    assert data["service_name"] == "home_power_sharing"
    assert "version" in data
