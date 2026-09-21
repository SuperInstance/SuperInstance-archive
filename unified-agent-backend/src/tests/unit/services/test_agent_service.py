"""
Unit tests for Agent Service.

This module provides comprehensive test coverage for the AgentService class,
including CRUD operations, lifecycle management, capability management,
health monitoring, and search functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_service import (
    AgentService, AgentCreate, AgentUpdate, AgentSearchFilters
)
from app.models.agent_model import (
    Agent, AgentStatus, AgentType, AgentCapability, HealthStatus
)
from app.repositories.agent_repository import AgentRepository


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_agent_repository():
    """Create a mock agent repository."""
    repo = AsyncMock(spec=AgentRepository)
    return repo


@pytest.fixture
def agent_service(mock_db_session, mock_agent_repository):
    """Create an agent service instance with mocked dependencies."""
    service = AgentService(mock_db_session)
    service.repository = mock_agent_repository
    return service


@pytest.fixture
def sample_agent():
    """Create a sample agent instance."""
    agent = Agent(
        id=uuid4(),
        name="test-agent",
        description="Test agent for unit testing",
        agent_type=AgentType.CHAT.value,
        version="1.0.0",
        status=AgentStatus.PENDING.value,
        health_status=HealthStatus.HEALTHY.value,
        is_active=True,
        capabilities=[AgentCapability.TEXT_GENERATION.value],
        config={"model": "gpt-4"},
        max_concurrent_tasks=1,
        timeout_seconds=300,
        created_by=uuid4()
    )
    return agent


@pytest.fixture
def sample_agent_create():
    """Create sample agent creation data."""
    return AgentCreate(
        name="new-test-agent",
        description="New test agent",
        agent_type=AgentType.CHAT.value,
        version="1.0.0",
        capabilities=[AgentCapability.TEXT_GENERATION.value],
        config={"model": "gpt-4"},
        max_concurrent_tasks=1,
        timeout_seconds=300,
        is_public=False
    )


@pytest.fixture
def sample_agent_update():
    """Create sample agent update data."""
    return AgentUpdate(
        name="updated-agent",
        description="Updated description",
        capabilities=[AgentCapability.TEXT_GENERATION.value, AgentCapability.CODE_GENERATION.value]
    )


class TestAgentServiceCRUD:
    """Test cases for agent CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_agent_success(self, agent_service, mock_agent_repository, sample_agent_create):
        """Test successful agent creation."""
        # Arrange
        created_agent = Agent(
            id=uuid4(),
            name=sample_agent_create.name,
            description=sample_agent_create.description,
            agent_type=sample_agent_create.agent_type,
            version=sample_agent_create.version,
            status=AgentStatus.PENDING.value,
            health_status=HealthStatus.HEALTHY.value,
            is_active=True,
            capabilities=sample_agent_create.capabilities,
            config=sample_agent_create.config,
            max_concurrent_tasks=sample_agent_create.max_concurrent_tasks,
            timeout_seconds=sample_agent_create.timeout_seconds,
            is_public=sample_agent_create.is_public
        )

        mock_agent_repository.check_name_availability.return_value = True
        mock_agent_repository.create.return_value = created_agent

        # Act
        result = await agent_service.create_agent(sample_agent_create)

        # Assert
        assert result.name == sample_agent_create.name
        assert result.agent_type == sample_agent_create.agent_type
        assert result.status == AgentStatus.PENDING.value
        mock_agent_repository.check_name_availability.assert_called_once_with(sample_agent_create.name)
        mock_agent_repository.create.assert_called_once()
        agent_service.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_duplicate_name(self, agent_service, mock_agent_repository, sample_agent_create):
        """Test agent creation with duplicate name."""
        # Arrange
        mock_agent_repository.check_name_availability.return_value = False

        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await agent_service.create_agent(sample_agent_create)

        assert exc_info.value.status_code == 409
        assert "already exists" in str(exc_info.value.detail)
        mock_agent_repository.check_name_availability.assert_called_once_with(sample_agent_create.name)
        mock_agent_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_agent_invalid_type(self, agent_service, mock_agent_repository, sample_agent_create):
        """Test agent creation with invalid agent type."""
        # Arrange
        sample_agent_create.agent_type = "invalid_type"
        mock_agent_repository.check_name_availability.return_value = True

        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await agent_service.create_agent(sample_agent_create)

        assert exc_info.value.status_code == 400
        assert "Invalid agent type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_agent_success(self, agent_service, mock_agent_repository, sample_agent):
        """Test successful agent retrieval."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent

        # Act
        result = await agent_service.get_agent(sample_agent.id)

        # Assert
        assert result.id == sample_agent.id
        assert result.name == sample_agent.name
        mock_agent_repository.get.assert_called_once_with(id=sample_agent.id)

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, agent_service, mock_agent_repository):
        """Test agent retrieval when not found."""
        # Arrange
        agent_id = uuid4()
        mock_agent_repository.get.return_value = None

        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await agent_service.get_agent(agent_id)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_agent_success(self, agent_service, mock_agent_repository, sample_agent, sample_agent_update):
        """Test successful agent update."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent
        mock_agent_repository.check_name_availability.return_value = True
        mock_agent_repository.update.return_value = sample_agent

        # Act
        result = await agent_service.update_agent(sample_agent.id, sample_agent_update)

        # Assert
        mock_agent_repository.update.assert_called_once()
        agent_service.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_agent_soft(self, agent_service, mock_agent_repository, sample_agent):
        """Test soft delete of agent."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent

        # Act
        result = await agent_service.delete_agent(sample_agent.id, hard_delete=False)

        # Assert
        assert result is True
        assert sample_agent.deleted_at is not None
        assert sample_agent.is_active is False
        agent_service.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_agent_hard(self, agent_service, mock_db_session, sample_agent):
        """Test hard delete of agent."""
        # Arrange
        agent_service = AgentService(mock_db_session)
        with patch.object(agent_service, 'get_agent', return_value=sample_agent):
            # Act
            result = await agent_service.delete_agent(sample_agent.id, hard_delete=True)

            # Assert
            assert result is True
            mock_db_session.delete.assert_called_once_with(sample_agent)
            mock_db_session.commit.assert_called_once()


class TestAgentLifecycleManagement:
    """Test cases for agent lifecycle management."""

    @pytest.mark.asyncio
    async def test_activate_agent_success(self, agent_service, mock_agent_repository, sample_agent):
        """Test successful agent activation."""
        # Arrange
        sample_agent.status = AgentStatus.IDLE.value
        mock_agent_repository.get.return_value = sample_agent

        # Act
        result = await agent_service.activate_agent(sample_agent.id)

        # Assert
        assert result.status == AgentStatus.ACTIVE.value
        assert result.is_active is True
        agent_service.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_agent_success(self, agent_service, mock_agent_repository, sample_agent):
        """Test successful agent deactivation."""
        # Arrange
        sample_agent.status = AgentStatus.ACTIVE.value
        mock_agent_repository.get.return_value = sample_agent

        # Act
        result = await agent_service.deactivate_agent(sample_agent.id, reason="Maintenance")

        # Assert
        assert result.status == AgentStatus.IDLE.value
        assert result.is_active is False
        agent_service.db_session.commit.assert_called_once()


class TestCapabilityManagement:
    """Test cases for agent capability management."""

    @pytest.mark.asyncio
    async def test_add_capability_success(self, agent_service, mock_agent_repository, sample_agent):
        """Test successful capability addition."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent
        new_capability = AgentCapability.CODE_GENERATION.value

        # Act
        result = await agent_service.add_capability(sample_agent.id, new_capability)

        # Assert
        assert new_capability in result.capabilities
        agent_service.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_capability_invalid(self, agent_service, mock_agent_repository, sample_agent):
        """Test adding invalid capability."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent
        invalid_capability = "invalid_capability"

        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await agent_service.add_capability(sample_agent.id, invalid_capability)

        assert exc_info.value.status_code == 400
        assert "Invalid capability" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_remove_capability_success(self, agent_service, mock_agent_repository, sample_agent):
        """Test successful capability removal."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent
        capability_to_remove = sample_agent.capabilities[0]

        # Act
        result = await agent_service.remove_capability(sample_agent.id, capability_to_remove)

        # Assert
        assert capability_to_remove not in result.capabilities
        agent_service.db_session.commit.assert_called_once()


class TestHealthMonitoring:
    """Test cases for agent health monitoring."""

    @pytest.mark.asyncio
    async def test_update_agent_health(self, agent_service, mock_agent_repository, sample_agent):
        """Test updating agent health status."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent
        new_health = HealthStatus.DEGRADED
        reason = "High response time"

        # Act
        result = await agent_service.update_agent_health(sample_agent.id, new_health, reason)

        # Assert
        assert result.health_status == new_health.value
        agent_service.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_heartbeat_success(self, agent_service, mock_agent_repository):
        """Test successful heartbeat recording."""
        # Arrange
        agent_id = uuid4()
        mock_agent_repository.update_agent_heartbeat.return_value = True

        # Act
        result = await agent_service.record_agent_heartbeat(agent_id)

        # Assert
        assert result is True
        mock_agent_repository.update_agent_heartbeat.assert_called_once_with(agent_id)
        agent_service.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_performance_metrics(self, agent_service, mock_agent_repository, sample_agent):
        """Test updating performance metrics."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent
        response_time = 150.5
        success = True

        # Act
        result = await agent_service.update_performance_metrics(
            sample_agent.id, response_time, success
        )

        # Assert
        assert result.total_tasks > 0
        agent_service.db_session.commit.assert_called_once()


class TestAgentDiscovery:
    """Test cases for agent discovery and search."""

    @pytest.mark.asyncio
    async def test_find_available_agents(self, agent_service, mock_agent_repository, sample_agent):
        """Test finding available agents."""
        # Arrange
        capabilities = [AgentCapability.TEXT_GENERATION.value]
        mock_agent_repository.find_available_agents.return_value = [sample_agent]

        # Act
        result = await agent_service.find_available_agents(
            capabilities=capabilities, limit=10
        )

        # Assert
        assert len(result) == 1
        assert result[0].id == sample_agent.id
        mock_agent_repository.find_available_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_agents(self, agent_service, mock_agent_repository, sample_agent):
        """Test searching agents with filters."""
        # Arrange
        filters = AgentSearchFilters(
            query="test",
            agent_type=AgentType.CHAT.value
        )
        mock_agent_repository.search_agents.return_value = ([sample_agent], 1)

        # Act
        result, total = await agent_service.search_agents(filters)

        # Assert
        assert len(result) == 1
        assert total == 1
        mock_agent_repository.search_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_agents_invalid_type(self, agent_service, mock_agent_repository):
        """Test searching agents with invalid type."""
        # Arrange
        filters = AgentSearchFilters(agent_type="invalid_type")

        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await agent_service.search_agents(filters)

        assert exc_info.value.status_code == 400
        assert "Invalid agent type" in str(exc_info.value.detail)


class TestToolManagement:
    """Test cases for agent tool management."""

    @pytest.mark.asyncio
    async def test_assign_tools(self, agent_service, mock_agent_repository, sample_agent):
        """Test assigning tools to agent."""
        # Arrange
        mock_agent_repository.get.return_value = sample_agent
        tools = {"web_search": {"enabled": True}, "database": {"enabled": False}}

        # Act
        result = await agent_service.assign_tools(sample_agent.id, tools)

        # Assert
        assert result.tools == tools
        agent_service.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_agent_tools(self, agent_service, mock_agent_repository, sample_agent):
        """Test getting agent tools."""
        # Arrange
        sample_agent.tools = {"web_search": {"enabled": True}}
        mock_agent_repository.get.return_value = sample_agent

        # Act
        result = await agent_service.get_agent_tools(sample_agent.id)

        # Assert
        assert result == sample_agent.tools


class TestAnalytics:
    """Test cases for analytics and monitoring."""

    @pytest.mark.asyncio
    async def test_get_performance_stats(self, agent_service, mock_agent_repository):
        """Test getting performance statistics."""
        # Arrange
        expected_stats = {
            "total_agents": 10,
            "healthy_agents": 8,
            "active_agents": 6,
            "avg_success_rate": 95.5,
            "avg_response_time": 150.2,
            "total_tasks_processed": 1000,
            "total_tasks_failed": 50,
            "type_distribution": {"chat": 6, "workflow": 4},
            "health_percentage": 80.0
        }
        mock_agent_repository.get_performance_stats.return_value = expected_stats

        # Act
        result = await agent_service.get_performance_stats()

        # Assert
        assert result == expected_stats
        mock_agent_repository.get_performance_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_top_performing_agents(self, agent_service, mock_agent_repository, sample_agent):
        """Test getting top performing agents."""
        # Arrange
        mock_agent_repository.get_top_performing_agents.return_value = [sample_agent]

        # Act
        result = await agent_service.get_top_performing_agents(metric="success_rate", limit=5)

        # Assert
        assert len(result) == 1
        assert result[0].id == sample_agent.id
        mock_agent_repository.get_top_performing_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_health_check(self, agent_service, mock_agent_repository, sample_agent):
        """Test performing health check on agent."""
        # Arrange
        sample_agent.last_heartbeat = datetime.now(timezone.utc)
        sample_agent.success_rate = 95.0
        sample_agent.response_time_avg = 150.0
        mock_agent_repository.get.return_value = sample_agent

        # Act
        result = await agent_service.perform_health_check(sample_agent.id)

        # Assert
        assert result["agent_id"] == str(sample_agent.id)
        assert result["agent_name"] == sample_agent.name
        assert result["is_healthy"] is True
        assert result["health_status"] == HealthStatus.HEALTHY.value
        assert "performance" in result
        assert "checked_at" in result
        agent_service.db_session.commit.assert_called_once()


class TestErrorHandling:
    """Test cases for error handling."""

    @pytest.mark.asyncio
    async def test_create_agent_validation_error(self, agent_service, mock_agent_repository):
        """Test handling of validation errors during agent creation."""
        # Arrange
        invalid_data = AgentCreate(name="")  # Empty name should fail validation
        mock_agent_repository.check_name_availability.return_value = True

        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await agent_service.create_agent(invalid_data)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_repository_exception_handling(self, agent_service, mock_agent_repository):
        """Test handling of repository exceptions."""
        # Arrange
        agent_id = uuid4()
        mock_agent_repository.get.side_effect = Exception("Database error")

        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await agent_service.get_agent(agent_id)

        assert exc_info.value.status_code == 500
        agent_service.db_session.rollback.assert_called_once()


class TestIntegration:
    """Integration test cases for agent service."""

    @pytest.mark.asyncio
    async def test_full_agent_lifecycle(self, agent_service, mock_agent_repository):
        """Test complete agent lifecycle from creation to deactivation."""
        # Arrange
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="lifecycle-test-agent",
            agent_type=AgentType.CHAT.value,
            status=AgentStatus.PENDING.value,
            health_status=HealthStatus.HEALTHY.value,
            is_active=True
        )

        mock_agent_repository.check_name_availability.return_value = True
        mock_agent_repository.create.return_value = agent
        mock_agent_repository.get.return_value = agent

        # Create agent
        agent_create = AgentCreate(
            name="lifecycle-test-agent",
            agent_type=AgentType.CHAT.value
        )
        created_agent = await agent_service.create_agent(agent_create)
        assert created_agent.status == AgentStatus.PENDING.value

        # Activate agent
        activated_agent = await agent_service.activate_agent(agent_id)
        assert activated_agent.status == AgentStatus.ACTIVE.value

        # Add capability
        updated_agent = await agent_service.add_capability(
            agent_id, AgentCapability.TEXT_GENERATION.value
        )
        assert AgentCapability.TEXT_GENERATION.value in updated_agent.capabilities

        # Update health
        healthy_agent = await agent_service.update_agent_health(
            agent_id, HealthStatus.HEALTHY, "All systems operational"
        )
        assert healthy_agent.health_status == HealthStatus.HEALTHY.value

        # Record performance
        await agent_service.update_performance_metrics(agent_id, 100.0, True)

        # Deactivate agent
        deactivated_agent = await agent_service.deactivate_agent(agent_id, "End of test")
        assert deactivated_agent.status == AgentStatus.IDLE.value

        # Verify all operations were called
        assert mock_agent_repository.create.called
        assert mock_agent_repository.update.called
        assert agent_service.db_session.commit.call_count == 6  # One for each operation