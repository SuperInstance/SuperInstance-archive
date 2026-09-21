"""
Agent repository with specialized database operations.

Provides efficient queries for agent management, including capability filtering,
health monitoring, and performance metrics tracking.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import and_, or_, func, desc, asc, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import expression

from app.repositories.base import BaseRepository
from app.models.agent_model import Agent, AgentStatus, AgentType, HealthStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentRepository(BaseRepository[Agent, Dict[str, Any], Dict[str, Any]]):
    """
    Repository for Agent model with specialized operations.

    Provides efficient queries for agent management, capability filtering,
    health monitoring, and performance analysis.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize agent repository.

        Args:
            db_session: Async database session
        """
        super().__init__(Agent, db_session)

    # Basic CRUD operations with specialized queries
    async def get_by_name(
        self,
        name: str,
        *,
        include_deleted: bool = False
    ) -> Optional[Agent]:
        """
        Get agent by name.

        Args:
            name: Agent name
            include_deleted: Whether to include soft-deleted agents

        Returns:
            Agent instance or None if not found
        """
        try:
            query = select(Agent).where(Agent.name == name)

            if not include_deleted:
                query = query.where(Agent.deleted_at.is_(None))

            result = await self.db_session.execute(query)
            agent = result.scalar_one_or_none()

            if agent:
                self.logger.debug(f"Retrieved agent by name: {name}")

            return agent

        except Exception as e:
            self.logger.error(f"Failed to get agent by name {name}: {str(e)}")
            raise

    async def get_by_endpoint_url(self, endpoint_url: str) -> Optional[Agent]:
        """
        Get agent by endpoint URL.

        Args:
            endpoint_url: Agent endpoint URL

        Returns:
            Agent instance or None if not found
        """
        try:
            query = select(Agent).where(
                and_(
                    Agent.endpoint_url == endpoint_url,
                    Agent.deleted_at.is_(None)
                )
            )

            result = await self.db_session.execute(query)
            agent = result.scalar_one_or_none()

            if agent:
                self.logger.debug(f"Retrieved agent by endpoint URL: {endpoint_url}")

            return agent

        except Exception as e:
            self.logger.error(f"Failed to get agent by endpoint URL {endpoint_url}: {str(e)}")
            raise

    # Agent discovery and filtering
    async def find_available_agents(
        self,
        *,
        capabilities: Optional[List[str]] = None,
        agent_type: Optional[AgentType] = None,
        max_response_time: Optional[float] = None,
        min_success_rate: Optional[float] = None,
        limit: int = 50,
        order_by_performance: bool = True
    ) -> List[Agent]:
        """
        Find agents that are available for new tasks.

        Args:
            capabilities: Required capabilities
            agent_type: Filter by agent type
            max_response_time: Maximum average response time in ms
            min_success_rate: Minimum success rate percentage
            limit: Maximum number of agents to return
            order_by_performance: Whether to order by performance metrics

        Returns:
            List of available agents
        """
        try:
            # Base query for available agents
            query = select(Agent).where(
                and_(
                    Agent.is_active == True,
                    Agent.status.in_([AgentStatus.ACTIVE.value, AgentStatus.IDLE.value]),
                    Agent.health_status == HealthStatus.HEALTHY.value,
                    Agent.deleted_at.is_(None)
                )
            )

            # Apply capability filter
            if capabilities:
                capability_conditions = [
                    Agent.capabilities.contains([cap]) for cap in capabilities
                ]
                query = query.where(or_(*capability_conditions))

            # Apply agent type filter
            if agent_type:
                query = query.where(Agent.agent_type == agent_type.value)

            # Apply performance filters
            if max_response_time:
                query = query.where(
                    or_(
                        Agent.response_time_avg <= max_response_time,
                        Agent.response_time_avg.is_(None)
                    )
                )

            if min_success_rate:
                query = query.where(
                    or_(
                        Agent.success_rate >= min_success_rate,
                        Agent.success_rate.is_(None)
                    )
                )

            # Apply ordering
            if order_by_performance:
                query = query.order_by(
                    desc(Agent.success_rate),
                    asc(Agent.response_time_avg),
                    desc(Agent.last_heartbeat)
                )
            else:
                query = query.order_by(desc(Agent.last_heartbeat))

            # Apply limit
            query = query.limit(limit)

            result = await self.db_session.execute(query)
            agents = result.scalars().all()

            self.logger.debug(f"Found {len(agents)} available agents with filters: "
                            f"capabilities={capabilities}, type={agent_type}")

            return list(agents)

        except Exception as e:
            self.logger.error(f"Failed to find available agents: {str(e)}")
            raise

    async def search_agents(
        self,
        *,
        query: Optional[str] = None,
        status: Optional[List[AgentStatus]] = None,
        agent_type: Optional[AgentType] = None,
        capabilities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[UUID] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Agent], int]:
        """
        Search agents with multiple filters.

        Args:
            query: Search query for name and description
            status: Filter by status list
            agent_type: Filter by agent type
            capabilities: Filter by capabilities
            tags: Filter by tags
            created_by: Filter by creator
            is_public: Filter by public status
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field to order by
            order_desc: Whether to order descending

        Returns:
            Tuple of (agents list, total count)
        """
        try:
            # Build the main query
            main_query = select(Agent).where(Agent.deleted_at.is_(None))
            count_query = select(func.count(Agent.id)).where(Agent.deleted_at.is_(None))

            # Apply search query
            if query:
                search_condition = or_(
                    Agent.name.ilike(f"%{query}%"),
                    Agent.description.ilike(f"%{query}%")
                )
                main_query = main_query.where(search_condition)
                count_query = count_query.where(search_condition)

            # Apply status filter
            if status:
                status_values = [s.value if isinstance(s, AgentStatus) else s for s in status]
                main_query = main_query.where(Agent.status.in_(status_values))
                count_query = count_query.where(Agent.status.in_(status_values))

            # Apply agent type filter
            if agent_type:
                main_query = main_query.where(Agent.agent_type == agent_type.value)
                count_query = count_query.where(Agent.agent_type == agent_type.value)

            # Apply capabilities filter
            if capabilities:
                capability_conditions = [
                    Agent.capabilities.contains([cap]) for cap in capabilities
                ]
                main_query = main_query.where(or_(*capability_conditions))
                count_query = count_query.where(or_(*capability_conditions))

            # Apply tags filter
            if tags:
                tag_conditions = [
                    Agent.tags.contains([tag]) for tag in tags
                ]
                main_query = main_query.where(or_(*tag_conditions))
                count_query = count_query.where(or_(*tag_conditions))

            # Apply creator filter
            if created_by:
                main_query = main_query.where(Agent.created_by == created_by)
                count_query = count_query.where(Agent.created_by == created_by)

            # Apply public filter
            if is_public is not None:
                main_query = main_query.where(Agent.is_public == is_public)
                count_query = count_query.where(Agent.is_public == is_public)

            # Apply ordering
            if hasattr(Agent, order_by):
                order_column = getattr(Agent, order_by)
                main_query = main_query.order_by(
                    desc(order_column) if order_desc else asc(order_column)
                )

            # Get total count
            count_result = await self.db_session.execute(count_query)
            total_count = count_result.scalar()

            # Apply pagination
            main_query = main_query.offset(skip).limit(limit)

            # Execute main query
            result = await self.db_session.execute(main_query)
            agents = result.scalars().all()

            self.logger.debug(f"Searched agents: found {len(agents)} of {total_count} total")

            return list(agents), total_count

        except Exception as e:
            self.logger.error(f"Failed to search agents: {str(e)}")
            raise

    # Health monitoring methods
    async def get_agents_needing_health_check(
        self,
        minutes_since_last_check: int = 5
    ) -> List[Agent]:
        """
        Get agents that need health status updates.

        Args:
            minutes_since_last_check: Minutes since last heartbeat

        Returns:
            List of agents needing health check
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_since_last_check)

            query = select(Agent).where(
                and_(
                    Agent.is_active == True,
                    Agent.deleted_at.is_(None),
                    or_(
                        Agent.last_heartbeat < cutoff_time,
                        Agent.last_heartbeat.is_(None)
                    )
                )
            )

            result = await self.db_session.execute(query)
            agents = result.scalars().all()

            self.logger.debug(f"Found {len(agents)} agents needing health check")
            return list(agents)

        except Exception as e:
            self.logger.error(f"Failed to get agents needing health check: {str(e)}")
            raise

    async def update_agent_heartbeat(self, agent_id: UUID) -> bool:
        """
        Update agent heartbeat timestamp.

        Args:
            agent_id: Agent ID

        Returns:
            True if update was successful
        """
        try:
            stmt = (
                update(Agent)
                .where(Agent.id == agent_id)
                .values(last_heartbeat=datetime.utcnow())
                .returning(Agent.id)
            )

            result = await self.db_session.execute(stmt)
            updated_id = result.scalar_one_or_none()

            if updated_id:
                self.logger.debug(f"Updated heartbeat for agent {agent_id}")
                return True
            else:
                self.logger.warning(f"Agent {agent_id} not found for heartbeat update")
                return False

        except Exception as e:
            self.logger.error(f"Failed to update heartbeat for agent {agent_id}: {str(e)}")
            raise

    # Performance metrics methods
    async def get_top_performing_agents(
        self,
        *,
        metric: str = "success_rate",
        limit: int = 10,
        min_tasks: int = 10
    ) -> List[Agent]:
        """
        Get top performing agents by a specific metric.

        Args:
            metric: Metric to sort by (success_rate, response_time_avg, total_tasks)
            limit: Maximum number of agents to return
            min_tasks: Minimum number of tasks to be considered

        Returns:
            List of top performing agents
        """
        try:
            query = select(Agent).where(
                and_(
                    Agent.is_active == True,
                    Agent.total_tasks >= min_tasks,
                    Agent.deleted_at.is_(None)
                )
            )

            # Apply ordering based on metric
            if metric == "success_rate":
                query = query.order_by(desc(Agent.success_rate))
            elif metric == "response_time_avg":
                query = query.order_by(asc(Agent.response_time_avg))
            elif metric == "total_tasks":
                query = query.order_by(desc(Agent.total_tasks))
            else:
                raise ValueError(f"Invalid metric: {metric}")

            query = query.limit(limit)

            result = await self.db_session.execute(query)
            agents = result.scalars().all()

            self.logger.debug(f"Retrieved top {len(agents)} agents by {metric}")
            return list(agents)

        except Exception as e:
            self.logger.error(f"Failed to get top performing agents by {metric}: {str(e)}")
            raise

    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get overall performance statistics for all agents.

        Returns:
            Dictionary with performance statistics
        """
        try:
            # Get basic stats
            total_agents = await self.count(filters={"is_active": True, "deleted_at": None})
            healthy_agents = await self.count(filters={
                "is_active": True,
                "health_status": HealthStatus.HEALTHY.value,
                "deleted_at": None
            })
            active_agents = await self.count(filters={
                "is_active": True,
                "status": AgentStatus.ACTIVE.value,
                "deleted_at": None
            })

            # Get performance aggregates
            performance_query = select(
                func.count(Agent.id).label("total"),
                func.avg(Agent.success_rate).label("avg_success_rate"),
                func.avg(Agent.response_time_avg).label("avg_response_time"),
                func.sum(Agent.total_tasks).label("total_tasks"),
                func.sum(Agent.failed_tasks).label("total_failed")
            ).where(
                and_(
                    Agent.is_active == True,
                    Agent.deleted_at.is_(None)
                )
            )

            result = await self.db_session.execute(performance_query)
            stats = result.first()

            # Get agent type distribution
            type_query = select(
                Agent.agent_type,
                func.count(Agent.id).label("count")
            ).where(
                and_(
                    Agent.is_active == True,
                    Agent.deleted_at.is_(None)
                )
            ).group_by(Agent.agent_type)

            type_result = await self.db_session.execute(type_query)
            type_distribution = {row.agent_type: row.count for row in type_result}

            return {
                "total_agents": total_agents,
                "healthy_agents": healthy_agents,
                "active_agents": active_agents,
                "avg_success_rate": round(float(stats.avg_success_rate or 0), 2),
                "avg_response_time": round(float(stats.avg_response_time or 0), 2),
                "total_tasks_processed": int(stats.total_tasks or 0),
                "total_tasks_failed": int(stats.total_failed or 0),
                "type_distribution": type_distribution,
                "health_percentage": round((healthy_agents / total_agents * 100) if total_agents > 0 else 0, 2)
            }

        except Exception as e:
            self.logger.error(f"Failed to get performance stats: {str(e)}")
            raise

    # Bulk operations
    async def bulk_update_status(
        self,
        agent_ids: List[UUID],
        new_status: AgentStatus,
        reason: Optional[str] = None
    ) -> int:
        """
        Update status for multiple agents.

        Args:
            agent_ids: List of agent IDs to update
            new_status: New status to set
            reason: Optional reason for status change

        Returns:
            Number of agents updated
        """
        try:
            stmt = (
                update(Agent)
                .where(Agent.id.in_(agent_ids))
                .values(status=new_status.value)
                .returning(Agent.id)
            )

            result = await self.db_session.execute(stmt)
            updated_ids = result.scalars().all()

            self.logger.info(f"Bulk updated status to {new_status.value} for {len(updated_ids)} agents. "
                           f"Reason: {reason}")

            return len(updated_ids)

        except Exception as e:
            self.logger.error(f"Failed to bulk update agent status: {str(e)}")
            raise

    async def cleanup_old_agents(
        self,
        days_inactive: int = 30
    ) -> int:
        """
        Soft delete agents that have been inactive for too long.

        Args:
            days_inactive: Number of days of inactivity before cleanup

        Returns:
            Number of agents cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)

            stmt = (
                update(Agent)
                .where(
                    and_(
                        Agent.is_active == False,
                        or_(
                            Agent.last_heartbeat < cutoff_date,
                            and_(
                                Agent.last_heartbeat.is_(None),
                                Agent.created_at < cutoff_date
                            )
                        ),
                        Agent.deleted_at.is_(None)
                    )
                )
                .values(deleted_at=datetime.utcnow())
                .returning(Agent.id)
            )

            result = await self.db_session.execute(stmt)
            deleted_ids = result.scalars().all()

            self.logger.info(f"Cleaned up {len(deleted_ids)} inactive agents (older than {days_inactive} days)")

            return len(deleted_ids)

        except Exception as e:
            self.logger.error(f"Failed to cleanup old agents: {str(e)}")
            raise

    # Utility methods
    async def get_agent_capabilities_summary(self) -> Dict[str, int]:
        """
        Get summary of agent capabilities usage.

        Returns:
            Dictionary mapping capability to agent count
        """
        try:
            # This would typically use PostgreSQL's unnest function for arrays
            # For now, we'll implement a simpler version
            query = select(Agent.capabilities).where(
                and_(
                    Agent.is_active == True,
                    Agent.deleted_at.is_(None),
                    Agent.capabilities.isnot(None)
                )
            )

            result = await self.db_session.execute(query)
            agents = result.scalars().all()

            capability_counts = {}
            for agent in agents:
                if agent.capabilities:
                    for capability in agent.capabilities:
                        capability_counts[capability] = capability_counts.get(capability, 0) + 1

            self.logger.debug(f"Retrieved capabilities summary for {len(capability_counts)} capabilities")
            return capability_counts

        except Exception as e:
            self.logger.error(f"Failed to get capabilities summary: {str(e)}")
            raise

    async def check_name_availability(self, name: str, exclude_id: Optional[UUID] = None) -> bool:
        """
        Check if an agent name is available.

        Args:
            name: Agent name to check
            exclude_id: Optional agent ID to exclude from check

        Returns:
            True if name is available
        """
        try:
            query = select(Agent).where(
                and_(
                    Agent.name == name,
                    Agent.deleted_at.is_(None)
                )
            )

            if exclude_id:
                query = query.where(Agent.id != exclude_id)

            result = await self.db_session.execute(query)
            existing = result.scalar_one_or_none()

            return existing is None

        except Exception as e:
            self.logger.error(f"Failed to check name availability for '{name}': {str(e)}")
            raise