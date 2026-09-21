"""
Workflow Service with CRUD operations, validation, and execution management.

This module provides high-level workflow management operations including:
- Workflow CRUD operations
- Workflow validation and testing
- Execution management and monitoring
- Template support and management
- Performance analytics
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.models.workflow_model import (
    Workflow, WorkflowNode, WorkflowExecution,
    WorkflowStatus, NodeType, ExecutionStatus
)
from app.repositories.workflow_repository import (
    WorkflowRepository, WorkflowNodeRepository, WorkflowExecutionRepository
)
from app.services.workflow_executor import WorkflowExecutor, ExecutionError
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowValidationError(Exception):
    """Exception for workflow validation errors."""
    pass


class WorkflowService:
    """
    Service for managing workflows with comprehensive CRUD operations,
    validation, and execution management.
    """

    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        node_repo: WorkflowNodeRepository,
        execution_repo: WorkflowExecutionRepository,
        executor: WorkflowExecutor
    ):
        """
        Initialize workflow service.

        Args:
            workflow_repo: Workflow repository
            node_repo: Workflow node repository
            execution_repo: Workflow execution repository
            executor: Workflow executor
        """
        self.workflow_repo = workflow_repo
        self.node_repo = node_repo
        self.execution_repo = execution_repo
        self.executor = executor

    # Workflow CRUD operations
    async def create_workflow(
        self,
        workflow_data: Dict[str, Any],
        *,
        created_by: Optional[UUID] = None
    ) -> Workflow:
        """
        Create a new workflow.

        Args:
            workflow_data: Workflow data
            created_by: Creator user ID

        Returns:
            Created workflow
        """
        try:
            # Validate workflow data
            await self._validate_workflow_data(workflow_data)

            # Create workflow
            workflow = await self.workflow_repo.create(
                obj_in=workflow_data,
                created_by=created_by
            )

            logger.info(f"Created workflow {workflow.id} ({workflow.name})")
            return workflow

        except Exception as e:
            logger.error(f"Failed to create workflow: {str(e)}")
            raise

    async def get_workflow(
        self,
        workflow_id: Union[UUID, str],
        *,
        include_nodes: bool = True,
        include_executions: bool = False
    ) -> Optional[Workflow]:
        """
        Get a workflow by ID.

        Args:
            workflow_id: Workflow ID
            include_nodes: Whether to include nodes
            include_executions: Whether to include executions

        Returns:
            Workflow or None if not found
        """
        try:
            if include_nodes:
                return await self.workflow_repo.get_with_nodes(
                    workflow_id=workflow_id,
                    include_executions=include_executions
                )
            else:
                return await self.workflow_repo.get(id=workflow_id)

        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_id}: {str(e)}")
            raise

    async def update_workflow(
        self,
        workflow_id: Union[UUID, str],
        update_data: Dict[str, Any]
    ) -> Optional[Workflow]:
        """
        Update a workflow.

        Args:
            workflow_id: Workflow ID
            update_data: Update data

        Returns:
            Updated workflow or None if not found
        """
        try:
            workflow = await self.workflow_repo.get(id=workflow_id)
            if not workflow:
                return None

            # Validate update data
            if "definition" in update_data:
                # Create temporary workflow to validate new definition
                temp_workflow = Workflow(**update_data)
                temp_workflow.definition = update_data["definition"]
                errors = temp_workflow.validate_definition()
                if errors:
                    raise WorkflowValidationError(f"Invalid workflow definition: {errors}")

            # Update workflow
            updated_workflow = await self.workflow_repo.update(
                db_obj=workflow,
                obj_in=update_data
            )

            logger.info(f"Updated workflow {workflow_id}")
            return updated_workflow

        except Exception as e:
            logger.error(f"Failed to update workflow {workflow_id}: {str(e)}")
            raise

    async def delete_workflow(
        self,
        workflow_id: Union[UUID, str],
        *,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete a workflow.

        Args:
            workflow_id: Workflow ID
            hard_delete: Whether to hard delete (default: soft delete)

        Returns:
            True if deletion was successful
        """
        try:
            workflow = await self.workflow_repo.get(id=workflow_id)
            if not workflow:
                return False

            if hard_delete:
                await self.workflow_repo.delete(id=workflow_id)
                logger.info(f"Hard deleted workflow {workflow_id}")
            else:
                workflow.archive()
                await self.workflow_repo.update(
                    db_obj=workflow,
                    obj_in={"status": WorkflowStatus.ARCHIVED.value}
                )
                logger.info(f"Soft deleted workflow {workflow_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {str(e)}")
            raise

    async def list_workflows(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[List[str]] = None,
        created_by: Optional[UUID] = None,
        include_templates: bool = True,
        search_query: Optional[str] = None
    ) -> List[Workflow]:
        """
        List workflows with filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status_filter: Optional status filter
            created_by: Optional creator filter
            include_templates: Whether to include templates
            search_query: Optional search query

        Returns:
            List of workflows
        """
        try:
            if search_query:
                return await self.workflow_repo.search_workflows(
                    query=search_query,
                    skip=skip,
                    limit=limit,
                    status_filter=status_filter,
                    created_by=created_by
                )
            else:
                filters = {}
                if status_filter:
                    # Note: This would need enhancement in base repository for multiple status filter
                    filters["status"] = status_filter[0] if status_filter else None
                if created_by:
                    filters["created_by"] = created_by

                workflows = await self.workflow_repo.get_multi(
                    skip=skip,
                    limit=limit,
                    filters=filters,
                    order_by="updated_at"
                )

                # Filter templates if needed
                if not include_templates:
                    workflows = [w for w in workflows if not w.is_template]

                return workflows

        except Exception as e:
            logger.error(f"Failed to list workflows: {str(e)}")
            raise

    # Workflow validation and testing
    async def validate_workflow(self, workflow_id: Union[UUID, str]) -> List[str]:
        """
        Validate a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of validation errors (empty if valid)
        """
        try:
            workflow = await self.get_workflow(workflow_id, include_nodes=True)
            if not workflow:
                return ["Workflow not found"]

            return workflow.validate_definition()

        except Exception as e:
            logger.error(f"Failed to validate workflow {workflow_id}: {str(e)}")
            return [f"Validation error: {str(e)}"]

    async def test_workflow(
        self,
        workflow_id: Union[UUID, str],
        test_input: Dict[str, Any],
        *,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Test a workflow execution.

        Args:
            workflow_id: Workflow ID
            test_input: Test input data
            dry_run: Whether to run as dry run (doesn't persist execution)

        Returns:
            Test execution results
        """
        try:
            workflow = await self.get_workflow(workflow_id, include_nodes=True)
            if not workflow:
                raise WorkflowValidationError("Workflow not found")

            # Validate workflow first
            validation_errors = await self.validate_workflow(workflow_id)
            if validation_errors:
                raise WorkflowValidationError(f"Workflow validation failed: {validation_errors}")

            if dry_run:
                # Simulate execution without actually running
                return await self._dry_run_workflow(workflow, test_input)
            else:
                # Execute with test data
                execution_id = await self.executor.execute_workflow(
                    workflow_id=workflow_id,
                    input_data=test_input,
                    triggered_by="test"
                )

                # Wait for execution to complete (with timeout)
                max_wait_time = 60  # 60 seconds
                waited_time = 0
                check_interval = 1

                while waited_time < max_wait_time:
                    execution = await self.execution_repo.get_execution_by_id(execution_id)
                    if execution and execution.is_completed():
                        return {
                            "execution_id": execution_id,
                            "status": execution.status,
                            "output_data": execution.output_data,
                            "duration_seconds": execution.duration_seconds,
                            "error_message": execution.error_message
                        }

                    await asyncio.sleep(check_interval)
                    waited_time += check_interval

                # Timeout reached
                await self.executor.cancel_execution(execution_id)
                return {
                    "execution_id": execution_id,
                    "status": "timeout",
                    "error_message": f"Test execution timed out after {max_wait_time} seconds"
                }

        except Exception as e:
            logger.error(f"Failed to test workflow {workflow_id}: {str(e)}")
            raise

    async def _dry_run_workflow(
        self,
        workflow: Workflow,
        test_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform a dry run of workflow execution.

        Args:
            workflow: Workflow model
            test_input: Test input data

        Returns:
            Dry run results
        """
        try:
            # Build execution graph
            graph = self.executor._build_execution_graph(
                workflow.nodes,
                workflow.definition.get("edges", [])
            )

            # Simulate execution without actually running nodes
            simulated_results = {}
            execution_order = []

            # Simple topological sort for simulation
            executed_nodes = set()
            ready_nodes = [
                node_id for node_id, node_data in graph.items()
                if not node_data["dependencies"]
            ]

            while ready_nodes:
                current_batch = ready_nodes[:self.executor.max_concurrent_nodes]
                ready_nodes = ready_nodes[self.executor.max_concurrent_nodes:]

                for node_id in current_batch:
                    node = graph[node_id]["node"]
                    execution_order.append({
                        "node_id": node_id,
                        "node_type": node.node_type,
                        "node_name": node.name
                    })

                    # Simulate node result
                    simulated_results[node_id] = {
                        "status": "completed",
                        "result": f"Simulated result for {node.node_type} node",
                        "processing_time": 0.1
                    }

                    executed_nodes.add(node_id)

                    # Find new ready nodes
                    for dependent_id in graph[node_id]["dependents"]:
                        dependencies = graph[dependent_id]["dependencies"]
                        if dependencies.issubset(executed_nodes):
                            ready_nodes.append(dependent_id)

            return {
                "dry_run": True,
                "workflow_id": str(workflow.id),
                "workflow_name": workflow.name,
                "execution_order": execution_order,
                "simulated_results": simulated_results,
                "total_nodes": len(workflow.nodes),
                "executed_nodes": len(executed_nodes)
            }

        except Exception as e:
            logger.error(f"Failed to dry run workflow: {str(e)}")
            raise

    # Workflow execution management
    async def execute_workflow(
        self,
        workflow_id: Union[UUID, str],
        input_data: Dict[str, Any],
        *,
        triggered_by: Optional[str] = None,
        asynchronous: bool = True
    ) -> Union[str, Dict[str, Any]]:
        """
        Execute a workflow.

        Args:
            workflow_id: Workflow ID
            input_data: Input data for execution
            triggered_by: What triggered this execution
            asynchronous: Whether to execute asynchronously

        Returns:
            Execution ID (if async) or execution results (if sync)
        """
        try:
            workflow = await self.get_workflow(workflow_id)
            if not workflow:
                raise WorkflowValidationError("Workflow not found")

            if workflow.status != WorkflowStatus.ACTIVE.value:
                raise WorkflowValidationError(f"Workflow is not active (status: {workflow.status})")

            # Validate workflow
            validation_errors = await self.validate_workflow(workflow_id)
            if validation_errors:
                raise WorkflowValidationError(f"Workflow validation failed: {validation_errors}")

            execution_id = await self.executor.execute_workflow(
                workflow_id=workflow_id,
                input_data=input_data,
                triggered_by=triggered_by
            )

            if asynchronous:
                return execution_id
            else:
                # Wait for completion and return results
                return await self._wait_for_execution_completion(execution_id)

        except Exception as e:
            logger.error(f"Failed to execute workflow {workflow_id}: {str(e)}")
            raise

    async def _wait_for_execution_completion(
        self,
        execution_id: str,
        timeout: int = 3600
    ) -> Dict[str, Any]:
        """
        Wait for execution completion.

        Args:
            execution_id: Execution ID
            timeout: Timeout in seconds

        Returns:
            Execution results
        """
        try:
            waited_time = 0
            check_interval = 5

            while waited_time < timeout:
                execution = await self.execution_repo.get_execution_by_id(execution_id)
                if not execution:
                    raise ExecutionError(f"Execution {execution_id} not found")

                if execution.is_completed():
                    return {
                        "execution_id": execution_id,
                        "status": execution.status,
                        "output_data": execution.output_data,
                        "duration_seconds": execution.duration_seconds,
                        "error_message": execution.error_message,
                        "error_details": execution.error_details
                    }

                await asyncio.sleep(check_interval)
                waited_time += check_interval

            # Timeout reached
            await self.executor.cancel_execution(execution_id)
            raise ExecutionError(f"Execution {execution_id} timed out after {timeout} seconds")

        except Exception as e:
            logger.error(f"Failed to wait for execution completion {execution_id}: {str(e)}")
            raise

    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a workflow execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if cancellation was successful
        """
        return await self.executor.cancel_execution(execution_id)

    async def pause_execution(self, execution_id: str) -> bool:
        """
        Pause a workflow execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if pause was successful
        """
        return await self.executor.pause_execution(execution_id)

    async def resume_execution(self, execution_id: str) -> bool:
        """
        Resume a paused workflow execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if resume was successful
        """
        return await self.executor.resume_execution(execution_id)

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution status and details.

        Args:
            execution_id: Execution ID

        Returns:
            Execution status and details
        """
        try:
            execution = await self.execution_repo.get_execution_by_id(execution_id)
            if not execution:
                return None

            return {
                "execution_id": execution.execution_id,
                "workflow_id": str(execution.workflow_id),
                "status": execution.status,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "duration_seconds": execution.duration_seconds,
                "error_message": execution.error_message,
                "input_data": execution.input_data,
                "output_data": execution.output_data,
                "variables": execution.variables
            }

        except Exception as e:
            logger.error(f"Failed to get execution status {execution_id}: {str(e)}")
            raise

    async def list_executions(
        self,
        workflow_id: Optional[Union[UUID, str]] = None,
        *,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List workflow executions.

        Args:
            workflow_id: Optional workflow ID filter
            status_filter: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of execution details
        """
        try:
            executions = await self.execution_repo.get_executions_by_workflow(
                workflow_id=workflow_id,
                status=status_filter,
                skip=skip,
                limit=limit
            )

            return [
                {
                    "execution_id": execution.execution_id,
                    "workflow_id": str(execution.workflow_id),
                    "status": execution.status,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "duration_seconds": execution.duration_seconds,
                    "triggered_by": execution.triggered_by,
                    "error_message": execution.error_message
                }
                for execution in executions
            ]

        except Exception as e:
            logger.error(f"Failed to list executions: {str(e)}")
            raise

    # Template management
    async def create_template(
        self,
        workflow_data: Dict[str, Any],
        category: str,
        tags: Optional[List[str]] = None,
        *,
        created_by: Optional[UUID] = None
    ) -> Workflow:
        """
        Create a workflow template.

        Args:
            workflow_data: Workflow data
            category: Template category
            tags: Template tags
            created_by: Creator user ID

        Returns:
            Created template workflow
        """
        try:
            # Set template-specific fields
            workflow_data.update({
                "is_template": True,
                "template_category": category,
                "template_tags": tags or [],
                "status": WorkflowStatus.ACTIVE.value
            })

            return await self.create_workflow(workflow_data, created_by=created_by)

        except Exception as e:
            logger.error(f"Failed to create template: {str(e)}")
            raise

    async def get_templates(
        self,
        *,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Workflow]:
        """
        Get workflow templates.

        Args:
            category: Optional category filter
            tags: Optional tags filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of template workflows
        """
        return await self.workflow_repo.get_template_workflows(
            category=category,
            tags=tags,
            skip=skip,
            limit=limit
        )

    async def create_workflow_from_template(
        self,
        template_id: Union[UUID, str],
        workflow_name: str,
        *,
        created_by: Optional[UUID] = None,
        customizations: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """
        Create a workflow from a template.

        Args:
            template_id: Template workflow ID
            workflow_name: Name for the new workflow
            created_by: Creator user ID
            customizations: Custom configuration overrides

        Returns:
            Created workflow
        """
        try:
            template = await self.get_workflow(template_id, include_nodes=True)
            if not template or not template.is_template:
                raise WorkflowValidationError("Template not found")

            # Prepare workflow data from template
            workflow_data = {
                "name": workflow_name,
                "description": f"Created from template: {template.name}",
                "version": "1.0.0",
                "definition": template.definition.copy(),
                "config": template.config.copy() if template.config else {},
                "variables": template.variables.copy() if template.variables else {},
                "timeout_seconds": template.timeout_seconds,
                "max_retries": template.max_retries,
                "tags": template.tags.copy() if template.tags else [],
                "is_template": False,
                "template_category": None,
                "template_tags": [],
                "status": WorkflowStatus.DRAFT.value
            }

            # Apply customizations
            if customizations:
                workflow_data.update(customizations)

            # Create workflow
            workflow = await self.create_workflow(workflow_data, created_by=created_by)

            # Create nodes from template
            if template.nodes:
                nodes_data = []
                for template_node in template.nodes:
                    node_data = {
                        "node_id": template_node.node_id,
                        "name": template_node.name,
                        "description": template_node.description,
                        "node_type": template_node.node_type,
                        "config": template_node.config.copy() if template_node.config else {},
                        "input_schema": template_node.input_schema.copy() if template_node.input_schema else {},
                        "output_schema": template_node.output_schema.copy() if template_node.output_schema else {},
                        "timeout_seconds": template_node.timeout_seconds,
                        "max_retries": template_node.max_retries,
                        "position_x": template_node.position_x,
                        "position_y": template_node.position_y
                    }
                    nodes_data.append(node_data)

                await self.node_repo.bulk_create_nodes(workflow.id, nodes_data)

            logger.info(f"Created workflow {workflow.id} from template {template_id}")
            return workflow

        except Exception as e:
            logger.error(f"Failed to create workflow from template {template_id}: {str(e)}")
            raise

    # Analytics and monitoring
    async def get_workflow_analytics(
        self,
        workflow_id: Optional[Union[UUID, str]] = None,
        *,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get workflow analytics and statistics.

        Args:
            workflow_id: Optional workflow ID filter
            days: Number of days to analyze

        Returns:
            Analytics data
        """
        try:
            # Get workflow statistics
            workflow_stats = await self.workflow_repo.get_workflow_statistics(created_by=None)

            # Get execution statistics
            execution_stats = await self.execution_repo.get_execution_statistics(
                workflow_id=workflow_id,
                days=days
            )

            # Get recent executions
            recent_executions = await self.list_executions(
                workflow_id=workflow_id,
                skip=0,
                limit=10
            )

            # Get active executions
            active_executions = self.executor.get_active_executions()

            analytics = {
                "workflow_statistics": workflow_stats,
                "execution_statistics": execution_stats,
                "recent_executions": recent_executions,
                "active_executions": {
                    "count": len(active_executions),
                    "execution_ids": active_executions
                },
                "period_days": days
            }

            return analytics

        except Exception as e:
            logger.error(f"Failed to get workflow analytics: {str(e)}")
            raise

    # Helper methods
    async def _validate_workflow_data(self, workflow_data: Dict[str, Any]) -> None:
        """
        Validate workflow data before creation.

        Args:
            workflow_data: Workflow data to validate
        """
        # Check required fields
        required_fields = ["name"]
        for field in required_fields:
            if field not in workflow_data or not workflow_data[field]:
                raise WorkflowValidationError(f"Required field '{field}' is missing or empty")

        # Validate definition if provided
        if "definition" in workflow_data:
            temp_workflow = Workflow(**workflow_data)
            errors = temp_workflow.validate_definition()
            if errors:
                raise WorkflowValidationError(f"Invalid workflow definition: {errors}")

    async def cleanup_old_data(self, *, days: int = 90) -> Dict[str, int]:
        """
        Clean up old workflow data.

        Args:
            days: Number of days to keep data

        Returns:
            Dictionary with cleanup counts
        """
        try:
            # Clean up old executions
            deleted_executions = await self.execution_repo.cleanup_old_executions(days=days)

            logger.info(f"Cleaned up old workflow data: {deleted_executions} executions")
            return {"deleted_executions": deleted_executions}

        except Exception as e:
            logger.error(f"Failed to cleanup old workflow data: {str(e)}")
            raise