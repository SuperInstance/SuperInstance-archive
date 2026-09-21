"""
Workflow repository with specialized CRUD operations for workflow management.

This module implements the repository pattern with async support for workflows,
workflow nodes, and executions, providing comprehensive database operations.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.workflow_model import Workflow, WorkflowNode, WorkflowExecution, WorkflowStatus, ExecutionStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowRepository(BaseRepository[Workflow, Dict[str, Any], Dict[str, Any]]):
    """
    Repository for Workflow model with specialized operations.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize workflow repository."""
        super().__init__(Workflow, db_session)

    async def get_with_nodes(
        self,
        workflow_id: Union[UUID, str],
        *,
        include_executions: bool = False
    ) -> Optional[Workflow]:
        """
        Get workflow with its nodes and optionally executions.

        Args:
            workflow_id: Workflow ID
            include_executions: Whether to include execution history

        Returns:
            Workflow with loaded relationships
        """
        try:
            options = [selectinload(Workflow.nodes)]

            if include_executions:
                options.append(selectinload(Workflow.executions))

            return await self.get(id=workflow_id, options=options)

        except Exception as e:
            self.logger.error(f"Failed to get workflow {workflow_id} with nodes: {str(e)}")
            raise

    async def get_active_workflows(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        created_by: Optional[UUID] = None
    ) -> List[Workflow]:
        """
        Get active workflows.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            created_by: Optional creator filter

        Returns:
            List of active workflows
        """
        try:
            filters = {
                "is_active": True,
                "status": WorkflowStatus.ACTIVE.value
            }

            if created_by:
                filters["created_by"] = created_by

            return await self.get_multi(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by="created_at"
            )

        except Exception as e:
            self.logger.error(f"Failed to get active workflows: {str(e)}")
            raise

    async def get_template_workflows(
        self,
        *,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Workflow]:
        """
        Get template workflows.

        Args:
            category: Optional category filter
            tags: Optional tags filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of template workflows
        """
        try:
            query = select(Workflow).where(
                and_(
                    Workflow.is_template == True,
                    Workflow.is_active == True,
                    Workflow.status != WorkflowStatus.ARCHIVED.value
                )
            )

            # Apply category filter
            if category:
                query = query.where(Workflow.template_category == category)

            # Apply tags filter
            if tags:
                for tag in tags:
                    query = query.where(Workflow.tags.contains([tag]))

            # Apply pagination and ordering
            query = query.order_by(desc(Workflow.created_at)).offset(skip).limit(limit)

            result = await self.db_session.execute(query)
            workflows = result.scalars().all()

            self.logger.debug(f"Retrieved {len(workflows)} template workflows")
            return list(workflows)

        except Exception as e:
            self.logger.error(f"Failed to get template workflows: {str(e)}")
            raise

    async def search_workflows(
        self,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[List[str]] = None,
        created_by: Optional[UUID] = None
    ) -> List[Workflow]:
        """
        Search workflows by name, description, or tags.

        Args:
            query: Search query
            skip: Number of records to skip
            limit: Maximum number of records to return
            status_filter: Optional status filter
            created_by: Optional creator filter

        Returns:
            List of matching workflows
        """
        try:
            db_query = select(Workflow).where(
                and_(
                    Workflow.deleted_at.is_(None),
                    or_(
                        Workflow.name.ilike(f"%{query}%"),
                        Workflow.description.ilike(f"%{query}%"),
                        Workflow.tags.any(query) if hasattr(Workflow.tags, 'any') else False
                    )
                )
            )

            # Apply status filter
            if status_filter:
                db_query = db_query.where(Workflow.status.in_(status_filter))

            # Apply creator filter
            if created_by:
                db_query = db_query.where(Workflow.created_by == created_by)

            # Apply pagination and ordering
            db_query = db_query.order_by(desc(Workflow.updated_at)).offset(skip).limit(limit)

            result = await self.db_session.execute(db_query)
            workflows = result.scalars().all()

            self.logger.debug(f"Search for '{query}' returned {len(workflows)} workflows")
            return list(workflows)

        except Exception as e:
            self.logger.error(f"Failed to search workflows: {str(e)}")
            raise

    async def get_workflow_statistics(
        self,
        *,
        created_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get workflow statistics.

        Args:
            created_by: Optional creator filter

        Returns:
            Dictionary with workflow statistics
        """
        try:
            base_query = select(Workflow).where(Workflow.deleted_at.is_(None))

            if created_by:
                base_query = base_query.where(Workflow.created_by == created_by)

            # Count by status
            status_counts = {}
            for status in WorkflowStatus:
                status_query = select(func.count(Workflow.id)).where(
                    and_(
                        base_query.whereclause,
                        Workflow.status == status.value
                    )
                )
                result = await self.db_session.execute(status_query)
                status_counts[status.value] = result.scalar()

            # Count templates vs regular workflows
            template_query = select(func.count(Workflow.id)).where(
                and_(base_query.whereclause, Workflow.is_template == True)
            )
            regular_query = select(func.count(Workflow.id)).where(
                and_(base_query.whereclause, Workflow.is_template == False)
            )

            template_result = await self.db_session.execute(template_query)
            regular_result = await self.db_session.execute(regular_query)

            template_count = template_result.scalar()
            regular_count = regular_result.scalar()

            # Get execution statistics
            execution_stats_query = select(
                func.sum(Workflow.total_executions).label('total_executions'),
                func.sum(Workflow.successful_executions).label('successful_executions'),
                func.sum(Workflow.failed_executions).label('failed_executions'),
                func.avg(Workflow.average_execution_time).label('avg_execution_time')
            ).where(base_query.whereclause)

            execution_result = await self.db_session.execute(execution_stats_query)
            execution_stats = execution_result.first()

            statistics = {
                "status_counts": status_counts,
                "template_count": template_count,
                "regular_count": regular_count,
                "total_workflows": template_count + regular_count,
                "execution_stats": {
                    "total_executions": execution_stats.total_executions or 0,
                    "successful_executions": execution_stats.successful_executions or 0,
                    "failed_executions": execution_stats.failed_executions or 0,
                    "average_execution_time": float(execution_stats.avg_execution_time or 0),
                }
            }

            self.logger.debug(f"Retrieved workflow statistics: {statistics}")
            return statistics

        except Exception as e:
            self.logger.error(f"Failed to get workflow statistics: {str(e)}")
            raise

    async def update_execution_stats(
        self,
        workflow_id: Union[UUID, str],
        execution_time: float,
        success: bool
    ) -> None:
        """
        Update workflow execution statistics.

        Args:
            workflow_id: Workflow ID
            execution_time: Execution time in seconds
            success: Whether execution was successful
        """
        try:
            workflow = await self.get(id=workflow_id)
            if workflow:
                workflow.update_execution_stats(execution_time, success)
                await self.db_session.flush()
                self.logger.debug(f"Updated execution stats for workflow {workflow_id}")

        except Exception as e:
            self.logger.error(f"Failed to update execution stats for workflow {workflow_id}: {str(e)}")
            raise


class WorkflowNodeRepository(BaseRepository[WorkflowNode, Dict[str, Any], Dict[str, Any]]):
    """
    Repository for WorkflowNode model with specialized operations.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize workflow node repository."""
        super().__init__(WorkflowNode, db_session)

    async def get_nodes_by_workflow(
        self,
        workflow_id: Union[UUID, str],
        *,
        node_type: Optional[str] = None
    ) -> List[WorkflowNode]:
        """
        Get nodes for a specific workflow.

        Args:
            workflow_id: Workflow ID
            node_type: Optional node type filter

        Returns:
            List of workflow nodes
        """
        try:
            filters = {"workflow_id": workflow_id}

            if node_type:
                filters["node_type"] = node_type

            return await self.get_multi(
                filters=filters,
                order_by="created_at"
            )

        except Exception as e:
            self.logger.error(f"Failed to get nodes for workflow {workflow_id}: {str(e)}")
            raise

    async def get_node_by_workflow_and_id(
        self,
        workflow_id: Union[UUID, str],
        node_id: str
    ) -> Optional[WorkflowNode]:
        """
        Get a specific node by workflow and node ID.

        Args:
            workflow_id: Workflow ID
            node_id: Node ID within workflow

        Returns:
            Workflow node or None if not found
        """
        try:
            query = select(WorkflowNode).where(
                and_(
                    WorkflowNode.workflow_id == workflow_id,
                    WorkflowNode.node_id == node_id
                )
            )

            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Failed to get node {node_id} for workflow {workflow_id}: {str(e)}")
            raise

    async def get_nodes_by_type(
        self,
        workflow_id: Union[UUID, str],
        node_types: List[str]
    ) -> List[WorkflowNode]:
        """
        Get nodes by type for a workflow.

        Args:
            workflow_id: Workflow ID
            node_types: List of node types to retrieve

        Returns:
            List of workflow nodes
        """
        try:
            query = select(WorkflowNode).where(
                and_(
                    WorkflowNode.workflow_id == workflow_id,
                    WorkflowNode.node_type.in_(node_types)
                )
            )

            result = await self.db_session.execute(query)
            nodes = result.scalars().all()

            return list(nodes)

        except Exception as e:
            self.logger.error(f"Failed to get nodes by type for workflow {workflow_id}: {str(e)}")
            raise

    async def bulk_create_nodes(
        self,
        workflow_id: Union[UUID, str],
        nodes_data: List[Dict[str, Any]]
    ) -> List[WorkflowNode]:
        """
        Create multiple nodes for a workflow.

        Args:
            workflow_id: Workflow ID
            nodes_data: List of node data

        Returns:
            List of created workflow nodes
        """
        try:
            db_nodes = []
            for node_data in nodes_data:
                node_data["workflow_id"] = workflow_id
                db_nodes.append(WorkflowNode(**node_data))

            self.db_session.add_all(db_nodes)
            await self.db_session.flush()

            # Refresh all objects to get their IDs
            for node in db_nodes:
                await self.db_session.refresh(node)

            self.logger.info(f"Bulk created {len(db_nodes)} nodes for workflow {workflow_id}")
            return db_nodes

        except Exception as e:
            self.logger.error(f"Failed to bulk create nodes for workflow {workflow_id}: {str(e)}")
            await self.db_session.rollback()
            raise

    async def reset_retry_counts(
        self,
        workflow_id: Union[UUID, str]
    ) -> None:
        """
        Reset retry counts for all nodes in a workflow.

        Args:
            workflow_id: Workflow ID
        """
        try:
            query = update(WorkflowNode).where(
                WorkflowNode.workflow_id == workflow_id
            ).values(retry_count=0)

            await self.db_session.execute(query)
            await self.db_session.flush()

            self.logger.debug(f"Reset retry counts for all nodes in workflow {workflow_id}")

        except Exception as e:
            self.logger.error(f"Failed to reset retry counts for workflow {workflow_id}: {str(e)}")
            raise


class WorkflowExecutionRepository(BaseRepository[WorkflowExecution, Dict[str, Any], Dict[str, Any]]):
    """
    Repository for WorkflowExecution model with specialized operations.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize workflow execution repository."""
        super().__init__(WorkflowExecution, db_session)

    async def get_executions_by_workflow(
        self,
        workflow_id: Union[UUID, str],
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[WorkflowExecution]:
        """
        Get executions for a specific workflow.

        Args:
            workflow_id: Workflow ID
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of workflow executions
        """
        try:
            filters = {"workflow_id": workflow_id}

            if status:
                filters["status"] = status

            return await self.get_multi(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by="created_at"
            )

        except Exception as e:
            self.logger.error(f"Failed to get executions for workflow {workflow_id}: {str(e)}")
            raise

    async def get_execution_by_id(
        self,
        execution_id: str
    ) -> Optional[WorkflowExecution]:
        """
        Get execution by execution ID.

        Args:
            execution_id: Execution ID

        Returns:
            Workflow execution or None if not found
        """
        try:
            return await self.get_by_field(
                field_name="execution_id",
                field_value=execution_id
            )

        except Exception as e:
            self.logger.error(f"Failed to get execution {execution_id}: {str(e)}")
            raise

    async def get_running_executions(
        self,
        *,
        workflow_id: Optional[Union[UUID, str]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[WorkflowExecution]:
        """
        Get currently running executions.

        Args:
            workflow_id: Optional workflow ID filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of running executions
        """
        try:
            filters = {"status": ExecutionStatus.RUNNING.value}

            if workflow_id:
                filters["workflow_id"] = workflow_id

            return await self.get_multi(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by="started_at"
            )

        except Exception as e:
            self.logger.error(f"Failed to get running executions: {str(e)}")
            raise

    async def get_execution_statistics(
        self,
        *,
        workflow_id: Optional[Union[UUID, str]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get execution statistics.

        Args:
            workflow_id: Optional workflow ID filter
            days: Number of days to look back

        Returns:
            Dictionary with execution statistics
        """
        try:
            from datetime import datetime, timedelta

            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            base_query = select(WorkflowExecution).where(
                WorkflowExecution.created_at >= threshold_date
            )

            if workflow_id:
                base_query = base_query.where(WorkflowExecution.workflow_id == workflow_id)

            # Count by status
            status_counts = {}
            for status in ExecutionStatus:
                status_query = select(func.count(WorkflowExecution.id)).where(
                    and_(base_query.whereclause, WorkflowExecution.status == status.value)
                )
                result = await self.db_session.execute(status_query)
                status_counts[status.value] = result.scalar()

            # Get duration statistics
            duration_query = select(
                func.avg(WorkflowExecution.duration_seconds).label('avg_duration'),
                func.min(WorkflowExecution.duration_seconds).label('min_duration'),
                func.max(WorkflowExecution.duration_seconds).label('max_duration')
            ).where(
                and_(
                    base_query.whereclause,
                    WorkflowExecution.duration_seconds.is_not(None)
                )
            )

            duration_result = await self.db_session.execute(duration_query)
            duration_stats = duration_result.first()

            # Get success rate
            completed_query = select(func.count(WorkflowExecution.id)).where(
                and_(
                    base_query.whereclause,
                    WorkflowExecution.status == ExecutionStatus.COMPLETED.value
                )
            )
            total_query = select(func.count(WorkflowExecution.id)).where(base_query.whereclause)

            completed_result = await self.db_session.execute(completed_query)
            total_result = await self.db_session.execute(total_query)

            completed_count = completed_result.scalar()
            total_count = total_result.scalar()

            success_rate = (completed_count / total_count * 100) if total_count > 0 else 0

            statistics = {
                "status_counts": status_counts,
                "duration_stats": {
                    "average": float(duration_stats.avg_duration or 0),
                    "minimum": float(duration_stats.min_duration or 0),
                    "maximum": float(duration_stats.max_duration or 0),
                },
                "success_rate": round(success_rate, 2),
                "total_executions": total_count,
                "successful_executions": completed_count,
                "period_days": days,
            }

            self.logger.debug(f"Retrieved execution statistics: {statistics}")
            return statistics

        except Exception as e:
            self.logger.error(f"Failed to get execution statistics: {str(e)}")
            raise

    async def cleanup_old_executions(
        self,
        *,
        days: int = 90,
        keep_successful: bool = True
    ) -> int:
        """
        Clean up old executions.

        Args:
            days: Number of days to keep executions
            keep_successful: Whether to keep successful executions

        Returns:
            Number of deleted executions
        """
        try:
            from datetime import datetime, timedelta

            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = delete(WorkflowExecution).where(
                WorkflowExecution.created_at < threshold_date
            )

            if keep_successful:
                query = query.where(
                    WorkflowExecution.status != ExecutionStatus.COMPLETED.value
                )

            result = await self.db_session.execute(query)
            deleted_count = result.rowcount

            self.logger.info(f"Cleaned up {deleted_count} old executions")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup old executions: {str(e)}")
            raise