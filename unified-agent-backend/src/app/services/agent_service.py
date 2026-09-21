"""
Agent service providing comprehensive agent management functionality.

This service handles agent CRUD operations, capability management, health monitoring,
tool assignment, and agent discovery with proper error handling and logging.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException, status

from app.repositories.agent_repository import AgentRepository
from app.models.agent_model import (
    Agent, AgentStatus, AgentType, AgentCapability, HealthStatus
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentCreate(BaseModel):
    """Schema for agent creation."""
    name: str
    description: Optional[str] = None
    agent_type: str = AgentType.CHAT.value
    version: str = "1.0.0"
    config: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    tools: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None
    max_concurrent_tasks: int = 1
    timeout_seconds: int = 300
    is_public: bool = False
    tags: Optional[List[str]] = None
    created_by: Optional[UUID] = None


class AgentUpdate(BaseModel):
    """Schema for agent updates."""
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    version: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    tools: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None
    max_concurrent_tasks: Optional[int] = None
    timeout_seconds: Optional[int] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None


class AgentSearchFilters(BaseModel):
    """Schema for agent search filters."""
    query: Optional[str] = None
    status: Optional[List[str]] = None
    agent_type: Optional[str] = None
    capabilities: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    created_by: Optional[UUID] = None
    is_public: Optional[bool] = None


class AgentService:
    """
    Service for managing agents with comprehensive functionality.

    Provides high-level operations for agent management, including CRUD operations,
    capability management, health monitoring, tool assignment, and discovery.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize agent service.

        Args:
            db_session: Async database session
        """
        self.db_session = db_session
        self.repository = AgentRepository(db_session)
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    # CRUD Operations
    async def create_agent(self, agent_data: AgentCreate) -> Agent:
        """
        Create a new agent.

        Args:
            agent_data: Agent creation data

        Returns:
            Created agent

        Raises:
            HTTPException: If agent name already exists or validation fails
        """
        try:
            # Validate agent name uniqueness
            if not await self.repository.check_name_availability(agent_data.name):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Agent with name '{agent_data.name}' already exists"
                )

            # Validate agent type
            if agent_data.agent_type not in [t.value for t in AgentType]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid agent type: {agent_data.agent_type}"
                )

            # Validate capabilities
            if agent_data.capabilities:
                valid_capabilities = [c.value for c in AgentCapability]
                invalid_caps = [cap for cap in agent_data.capabilities
                              if cap not in valid_capabilities]
                if invalid_caps:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid capabilities: {invalid_caps}. "
                              f"Valid capabilities: {valid_capabilities}"
                    )

            # Create agent
            agent_dict = agent_data.model_dump(exclude_unset=True)
            agent = await self.repository.create(obj_in=agent_dict)

            # Set initial status
            agent.status = AgentStatus.PENDING.value
            await self.db_session.commit()

            self.logger.info(f"Created agent: {agent.name} (ID: {agent.id})")
            return agent

        except HTTPException:
            raise
        except ValidationError as e:
            self.logger.error(f"Validation error creating agent: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Failed to create agent: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create agent"
            )

    async def get_agent(self, agent_id: UUID, include_sensitive: bool = False) -> Agent:
        """
        Get an agent by ID.

        Args:
            agent_id: Agent ID
            include_sensitive: Whether to include sensitive information

        Returns:
            Agent instance

        Raises:
            HTTPException: If agent not found
        """
        try:
            agent = await self.repository.get(id=agent_id)
            if not agent or agent.deleted_at:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )

            self.logger.debug(f"Retrieved agent: {agent.name} (ID: {agent.id})")
            return agent

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get agent {agent_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve agent"
            )

    async def update_agent(self, agent_id: UUID, update_data: AgentUpdate) -> Agent:
        """
        Update an agent.

        Args:
            agent_id: Agent ID
            update_data: Update data

        Returns:
            Updated agent

        Raises:
            HTTPException: If agent not found or validation fails
        """
        try:
            # Get existing agent
            agent = await self.get_agent(agent_id)

            # Validate name uniqueness if changing
            if update_data.name and update_data.name != agent.name:
                if not await self.repository.check_name_availability(
                    update_data.name, exclude_id=agent_id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Agent with name '{update_data.name}' already exists"
                    )

            # Validate agent type if changing
            if update_data.agent_type:
                if update_data.agent_type not in [t.value for t in AgentType]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid agent type: {update_data.agent_type}"
                    )

            # Validate capabilities if changing
            if update_data.capabilities:
                valid_capabilities = [c.value for c in AgentCapability]
                invalid_caps = [cap for cap in update_data.capabilities
                              if cap not in valid_capabilities]
                if invalid_caps:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid capabilities: {invalid_caps}"
                    )

            # Update agent
            update_dict = update_data.model_dump(exclude_unset=True)
            updated_agent = await self.repository.update(db_obj=agent, obj_in=update_dict)
            await self.db_session.commit()

            self.logger.info(f"Updated agent: {updated_agent.name} (ID: {updated_agent.id})")
            return updated_agent

        except HTTPException:
            raise
        except ValidationError as e:
            self.logger.error(f"Validation error updating agent {agent_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Failed to update agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update agent"
            )

    async def delete_agent(self, agent_id: UUID, hard_delete: bool = False) -> bool:
        """
        Delete an agent.

        Args:
            agent_id: Agent ID
            hard_delete: Whether to permanently delete (vs soft delete)

        Returns:
            True if deletion was successful

        Raises:
            HTTPException: If agent not found or deletion fails
        """
        try:
            if hard_delete:
                # Get agent first for logging
                agent = await self.get_agent(agent_id)

                # Perform hard delete
                await self.db_session.delete(agent)
                await self.db_session.commit()

                self.logger.info(f"Hard deleted agent: {agent.name} (ID: {agent.id})")
            else:
                # Soft delete
                agent = await self.get_agent(agent_id)
                agent.deleted_at = datetime.utcnow()
                agent.is_active = False
                await self.db_session.commit()

                self.logger.info(f"Soft deleted agent: {agent.name} (ID: {agent.id})")

            return True

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to delete agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete agent"
            )

    # Agent Lifecycle Management
    async def activate_agent(self, agent_id: UUID) -> Agent:
        """
        Activate an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Updated agent

        Raises:
            HTTPException: If activation fails
        """
        try:
            agent = await self.get_agent(agent_id)

            if not agent.activate():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot activate agent in {agent.status} status"
                )

            await self.db_session.commit()
            self.logger.info(f"Activated agent: {agent.name} (ID: {agent.id})")
            return agent

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to activate agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to activate agent"
            )

    async def deactivate_agent(self, agent_id: UUID, reason: Optional[str] = None) -> Agent:
        """
        Deactivate an agent.

        Args:
            agent_id: Agent ID
            reason: Optional reason for deactivation

        Returns:
            Updated agent

        Raises:
            HTTPException: If deactivation fails
        """
        try:
            agent = await self.get_agent(agent_id)

            if not agent.deactivate(reason):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot deactivate agent in {agent.status} status"
                )

            await self.db_session.commit()
            self.logger.info(f"Deactivated agent: {agent.name} (ID: {agent.id}). Reason: {reason}")
            return agent

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to deactivate agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate agent"
            )

    # Capability Management
    async def add_capability(self, agent_id: UUID, capability: str) -> Agent:
        """
        Add a capability to an agent.

        Args:
            agent_id: Agent ID
            capability: Capability to add

        Returns:
            Updated agent

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Validate capability
            if capability not in [c.value for c in AgentCapability]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid capability: {capability}"
                )

            agent = await self.get_agent(agent_id)

            if not agent.add_capability(capability):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Agent already has capability: {capability}"
                )

            await self.db_session.commit()
            self.logger.info(f"Added capability '{capability}' to agent: {agent.name} (ID: {agent.id})")
            return agent

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to add capability to agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add capability"
            )

    async def remove_capability(self, agent_id: UUID, capability: str) -> Agent:
        """
        Remove a capability from an agent.

        Args:
            agent_id: Agent ID
            capability: Capability to remove

        Returns:
            Updated agent

        Raises:
            HTTPException: If operation fails
        """
        try:
            agent = await self.get_agent(agent_id)

            if not agent.remove_capability(capability):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent does not have capability: {capability}"
                )

            await self.db_session.commit()
            self.logger.info(f"Removed capability '{capability}' from agent: {agent.name} (ID: {agent.id})")
            return agent

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to remove capability from agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove capability"
            )

    # Health Monitoring
    async def update_agent_health(
        self,
        agent_id: UUID,
        health_status: HealthStatus,
        reason: Optional[str] = None
    ) -> Agent:
        """
        Update agent health status.

        Args:
            agent_id: Agent ID
            health_status: New health status
            reason: Optional reason for health change

        Returns:
            Updated agent

        Raises:
            HTTPException: If operation fails
        """
        try:
            agent = await self.get_agent(agent_id)
            agent.update_health_status(health_status, reason)
            await self.db_session.commit()

            self.logger.info(f"Updated health status for agent {agent.name} (ID: {agent.id}) "
                           f"to {health_status.value}. Reason: {reason}")
            return agent

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to update health for agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update agent health"
            )

    async def record_agent_heartbeat(self, agent_id: UUID) -> bool:
        """
        Record agent heartbeat.

        Args:
            agent_id: Agent ID

        Returns:
            True if heartbeat was recorded

        Raises:
            HTTPException: If operation fails
        """
        try:
            success = await self.repository.update_agent_heartbeat(agent_id)
            await self.db_session.commit()

            if success:
                self.logger.debug(f"Recorded heartbeat for agent {agent_id}")
            else:
                self.logger.warning(f"Failed to record heartbeat for agent {agent_id}: agent not found")

            return success

        except Exception as e:
            self.logger.error(f"Failed to record heartbeat for agent {agent_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record agent heartbeat"
            )

    async def update_performance_metrics(
        self,
        agent_id: UUID,
        response_time_ms: Optional[float] = None,
        success: Optional[bool] = None
    ) -> Agent:
        """
        Update agent performance metrics.

        Args:
            agent_id: Agent ID
            response_time_ms: Response time in milliseconds
            success: Whether the task was successful

        Returns:
            Updated agent

        Raises:
            HTTPException: If operation fails
        """
        try:
            agent = await self.get_agent(agent_id)
            agent.update_performance_metrics(response_time_ms, success)
            await self.db_session.commit()

            self.logger.debug(f"Updated performance metrics for agent {agent.name} (ID: {agent.id})")
            return agent

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to update performance metrics for agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update performance metrics"
            )

    # Agent Discovery and Search
    async def find_available_agents(
        self,
        capabilities: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
        max_response_time: Optional[float] = None,
        min_success_rate: Optional[float] = None,
        limit: int = 50
    ) -> List[Agent]:
        """
        Find agents that are available for new tasks.

        Args:
            capabilities: Required capabilities
            agent_type: Filter by agent type
            max_response_time: Maximum average response time in ms
            min_success_rate: Minimum success rate percentage
            limit: Maximum number of agents to return

        Returns:
            List of available agents

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Validate agent type if provided
            agent_type_enum = None
            if agent_type:
                if agent_type not in [t.value for t in AgentType]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid agent type: {agent_type}"
                    )
                agent_type_enum = AgentType(agent_type)

            agents = await self.repository.find_available_agents(
                capabilities=capabilities,
                agent_type=agent_type_enum,
                max_response_time=max_response_time,
                min_success_rate=min_success_rate,
                limit=limit
            )

            self.logger.info(f"Found {len(agents)} available agents")
            return agents

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to find available agents: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to find available agents"
            )

    async def search_agents(
        self,
        filters: AgentSearchFilters,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Agent], int]:
        """
        Search agents with multiple filters.

        Args:
            filters: Search filters
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field to order by
            order_desc: Whether to order descending

        Returns:
            Tuple of (agents list, total count)

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Validate agent type if provided
            agent_type_enum = None
            if filters.agent_type:
                if filters.agent_type not in [t.value for t in AgentType]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid agent type: {filters.agent_type}"
                    )
                agent_type_enum = AgentType(filters.agent_type)

            # Convert status strings to enums if provided
            status_enums = None
            if filters.status:
                status_enums = []
                for status in filters.status:
                    if status not in [s.value for s in AgentStatus]:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid agent status: {status}"
                        )
                    status_enums.append(AgentStatus(status))

            agents, total_count = await self.repository.search_agents(
                query=filters.query,
                status=status_enums,
                agent_type=agent_type_enum,
                capabilities=filters.capabilities,
                tags=filters.tags,
                created_by=filters.created_by,
                is_public=filters.is_public,
                skip=skip,
                limit=limit,
                order_by=order_by,
                order_desc=order_desc
            )

            self.logger.info(f"Searched agents: found {len(agents)} of {total_count} total")
            return agents, total_count

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to search agents: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search agents"
            )

    # Tool Management
    async def assign_tools(self, agent_id: UUID, tools: Dict[str, Any]) -> Agent:
        """
        Assign tools to an agent.

        Args:
            agent_id: Agent ID
            tools: Tools configuration

        Returns:
            Updated agent

        Raises:
            HTTPException: If operation fails
        """
        try:
            agent = await self.get_agent(agent_id)
            agent.tools = tools
            await self.db_session.commit()

            self.logger.info(f"Assigned tools to agent {agent.name} (ID: {agent.id})")
            return agent

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to assign tools to agent {agent_id}: {str(e)}")
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign tools"
            )

    async def get_agent_tools(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Get tools assigned to an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Tools configuration

        Raises:
            HTTPException: If agent not found
        """
        try:
            agent = await self.get_agent(agent_id)
            tools = agent.tools or {}

            self.logger.debug(f"Retrieved tools for agent {agent.name} (ID: {agent.id})")
            return tools

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get tools for agent {agent_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve agent tools"
            )

    # Analytics and Monitoring
    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get overall performance statistics.

        Returns:
            Performance statistics

        Raises:
            HTTPException: If operation fails
        """
        try:
            stats = await self.repository.get_performance_stats()
            self.logger.info("Retrieved performance statistics")
            return stats

        except Exception as e:
            self.logger.error(f"Failed to get performance stats: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve performance statistics"
            )

    async def get_top_performing_agents(
        self,
        metric: str = "success_rate",
        limit: int = 10
    ) -> List[Agent]:
        """
        Get top performing agents by metric.

        Args:
            metric: Performance metric
            limit: Maximum number of agents

        Returns:
            List of top performing agents

        Raises:
            HTTPException: If operation fails
        """
        try:
            agents = await self.repository.get_top_performing_agents(
                metric=metric,
                limit=limit
            )

            self.logger.info(f"Retrieved top {len(agents)} agents by {metric}")
            return agents

        except Exception as e:
            self.logger.error(f"Failed to get top performing agents: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve top performing agents"
            )

    # Maintenance Operations
    async def perform_health_check(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Perform health check on an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Health check results

        Raises:
            HTTPException: If agent not found
        """
        try:
            agent = await self.get_agent(agent_id)

            # Perform basic health checks
            is_healthy = agent.is_healthy()
            performance_summary = agent.get_performance_summary()

            # Determine health status
            if is_healthy:
                health_status = HealthStatus.HEALTHY
            elif agent.last_heartbeat and (datetime.utcnow() - agent.last_heartbeat).seconds < 300:
                health_status = HealthStatus.DEGRADED
            else:
                health_status = HealthStatus.UNHEALTHY

            # Update agent health status
            agent.update_health_status(health_status)
            await self.db_session.commit()

            results = {
                "agent_id": str(agent_id),
                "agent_name": agent.name,
                "is_healthy": is_healthy,
                "health_status": health_status.value,
                "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                "performance": performance_summary,
                "can_accept_tasks": agent.can_accept_task(),
                "checked_at": datetime.utcnow().isoformat()
            }

            self.logger.info(f"Health check completed for agent {agent.name} (ID: {agent.id}): "
                           f"{health_status.value}")
            return results

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to perform health check on agent {agent_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to perform health check"
            )