"""
WebSocket-enabled workflow executor.

This module extends the workflow executor with WebSocket notifications for real-time updates.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from app.services.workflow_executor import WorkflowExecutor as BaseWorkflowExecutor
from app.repositories.workflow_repository import (
    WorkflowRepository, WorkflowNodeRepository, WorkflowExecutionRepository
)
from app.websocket.integrations import WorkflowExecutorWebSocketIntegration
from app.models.workflow_model import ExecutionStatus, NodeStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowExecutor(BaseWorkflowExecutor):
    """
    WebSocket-enabled workflow executor.

    Extends the base workflow executor with real-time WebSocket notifications
    for execution events, progress updates, and node status changes.
    """

    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        node_repo: WorkflowNodeRepository,
        execution_repo: WorkflowExecutionRepository,
        **kwargs
    ):
        """
        Initialize WebSocket-enabled workflow executor.

        Args:
            workflow_repo: Workflow repository
            node_repo: Workflow node repository
            execution_repo: Workflow execution repository
            **kwargs: Additional arguments passed to base executor
        """
        super().__init__(workflow_repo, node_repo, execution_repo, **kwargs)
        self.ws_integration = WorkflowExecutorWebSocketIntegration()

    async def execute_workflow(
        self,
        workflow_id: Union[UUID, str],
        input_data: Optional[Dict[str, Any]] = None,
        *,
        execution_id: Optional[str] = None,
        triggered_by: Optional[str] = None,
        resume_from_checkpoint: bool = False
    ) -> str:
        """
        Execute a workflow with WebSocket notifications.

        Args:
            workflow_id: Workflow ID
            input_data: Input data for execution
            execution_id: Optional custom execution ID
            triggered_by: What triggered this execution
            resume_from_checkpoint: Whether to resume from checkpoint

        Returns:
            Execution ID
        """
        # Generate execution ID if not provided
        if not execution_id:
            execution_id = str(uuid4())

        # Get workflow info for WebSocket notifications
        workflow = await self.workflow_repo.get_with_nodes(workflow_id)
        if not workflow:
            raise Exception(f"Workflow {workflow_id} not found")

        # Notify execution started
        if not resume_from_checkpoint:
            await self.ws_integration.notify_execution_started(
                execution_id=str(workflow_id),
                workflow_id=str(workflow_id),
                user_id=triggered_by or "system",
                input_data=input_data or {}
            )

        try:
            # Execute workflow with monitoring
            result_execution_id = await super().execute_workflow(
                workflow_id=workflow_id,
                input_data=input_data,
                execution_id=execution_id,
                triggered_by=triggered_by,
                resume_from_checkpoint=resume_from_checkpoint
            )

            return result_execution_id

        except Exception as e:
            # Notify execution failed
            await self.ws_integration.notify_execution_failed(
                execution_id=execution_id,
                workflow_id=str(workflow_id),
                error_message=str(e),
                error_type=type(e).__name__,
                user_id=triggered_by
            )
            raise

    async def _execute_workflow_internal(
        self,
        workflow_id: Union[UUID, str],
        execution_id: str,
        input_data: Dict[str, Any],
        triggered_by: Optional[str],
        resume_from_checkpoint: bool
    ) -> None:
        """
        Internal workflow execution with WebSocket progress notifications.

        Args:
            workflow_id: Workflow ID
            execution_id: Execution ID
            input_data: Input data
            triggered_by: Trigger source
            resume_from_checkpoint: Whether to resume from checkpoint
        """
        execution = None
        start_time = datetime.utcnow()

        try:
            # Get workflow with nodes
            workflow = await self.workflow_repo.get_with_nodes(workflow_id)
            if not workflow:
                raise Exception(f"Workflow {workflow_id} not found")

            # Validate workflow
            validation_errors = workflow.validate_definition()
            if validation_errors:
                raise Exception(f"Workflow validation failed: {validation_errors}")

            # Create or get execution record
            if resume_from_checkpoint:
                execution = await self.execution_repo.get_execution_by_id(execution_id)
                if not execution:
                    raise Exception(f"Execution {execution_id} not found for resume")
                checkpoint_data = execution.restore_from_checkpoint()
                if checkpoint_data:
                    input_data.update(checkpoint_data.get("input_data", {}))
            else:
                execution = await self.execution_repo.create(
                    obj_in={
                        "workflow_id": workflow_id,
                        "execution_id": execution_id,
                        "status": ExecutionStatus.PENDING.value,
                        "input_data": input_data,
                        "triggered_by": triggered_by,
                        "variables": workflow.variables or {}
                    }
                )

            # Update execution status to running
            await self.execution_repo.update_status(
                execution_id, ExecutionStatus.RUNNING.value
            )

            # Execute nodes with progress tracking
            nodes = workflow.nodes
            total_nodes = len(nodes)
            completed_nodes = 0

            for node in nodes:
                try:
                    # Notify node started
                    await self.ws_integration.notify_node_started(
                        execution_id=execution_id,
                        node_id=node.id,
                        node_type=node.node_type,
                        input_data=input_data
                    )

                    # Get node handler and execute
                    handler = self.node_handlers.get(node.node_type)
                    if not handler:
                        raise Exception(f"No handler for node type: {node.node_type}")

                    node_start_time = datetime.utcnow()
                    node_output = await handler(node, input_data, execution)
                    node_duration = (datetime.utcnow() - node_start_time).total_seconds()

                    # Update input data for next nodes
                    input_data.update(node_output)

                    # Notify node completed
                    await self.ws_integration.notify_node_completed(
                        execution_id=execution_id,
                        node_id=node.id,
                        duration_seconds=node_duration,
                        output_data=node_output,
                        metrics={"node_type": node.node_type}
                    )

                    completed_nodes += 1

                    # Calculate and notify progress
                    progress_percentage = (completed_nodes / total_nodes) * 100
                    await self.ws_integration.notify_execution_progress(
                        execution_id=execution_id,
                        workflow_id=str(workflow_id),
                        progress_percentage=progress_percentage,
                        current_node_id=node.id,
                        completed_nodes=completed_nodes,
                        total_nodes=total_nodes,
                        estimated_remaining_seconds=(
                            (total_nodes - completed_nodes) * node_duration if node_duration > 0 else None
                        )
                    )

                except Exception as e:
                    # Notify node failed
                    await self.ws_integration.notify_node_failed(
                        execution_id=execution_id,
                        node_id=node.id,
                        error_message=str(e),
                        error_type=type(e).__name__,
                        stack_trace=getattr(e, '__traceback__', None)
                    )
                    raise

            # Mark execution as completed
            duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            await self.execution_repo.update(
                execution_id,
                {
                    "status": ExecutionStatus.COMPLETED.value,
                    "output_data": input_data,
                    "duration_seconds": duration_seconds,
                    "completed_at": datetime.utcnow()
                }
            )

            # Notify execution completed
            await self.ws_integration.notify_execution_completed(
                execution_id=execution_id,
                workflow_id=str(workflow_id),
                status=ExecutionStatus.COMPLETED,
                duration_seconds=duration_seconds,
                output_data=input_data,
                metrics={"total_nodes": total_nodes},
                user_id=triggered_by or "system"
            )

        except Exception as e:
            # Mark execution as failed
            duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            await self.execution_repo.update(
                execution_id,
                {
                    "status": ExecutionStatus.FAILED.value,
                    "error_message": str(e),
                    "duration_seconds": duration_seconds,
                    "completed_at": datetime.utcnow()
                }
            )
            raise

    async def _execute_agent_task_node(
        self,
        node,
        input_data: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """
        Execute agent task node with WebSocket notifications.

        Args:
            node: Node to execute
            input_data: Input data for node
            execution: Execution context

        Returns:
            Node output data
        """
        try:
            # This would integrate with your agent service
            # For now, return mock data
            logger.info(f"Executing agent task node {node.id} with input: {input_data}")

            # Simulate some processing time
            await asyncio.sleep(1)

            # Return mock output
            return {
                "node_id": node.id,
                "result": "Agent task completed successfully",
                "processed_data": input_data
            }

        except Exception as e:
            logger.error(f"Agent task node {node.id} failed: {str(e)}")
            raise

    async def _execute_trigger_node(
        self,
        node,
        input_data: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """Execute trigger node."""
        logger.info(f"Executing trigger node {node.id}")
        return {"triggered": True, "node_id": node.id}

    async def _execute_decision_node(
        self,
        node,
        input_data: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """Execute decision node."""
        logger.info(f"Executing decision node {node.id}")
        return {"decision": "proceed", "node_id": node.id}

    async def _execute_parallel_node(
        self,
        node,
        input_data: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """Execute parallel node."""
        logger.info(f"Executing parallel node {node.id}")
        return {"parallel_results": [], "node_id": node.id}

    async def _execute_sink_node(
        self,
        node,
        input_data: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """Execute sink node."""
        logger.info(f"Executing sink node {node.id}")
        return {"sink_completed": True, "node_id": node.id}

    async def _execute_delay_node(
        self,
        node,
        input_data: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """Execute delay node."""
        delay_seconds = node.config.get("delay_seconds", 1)
        logger.info(f"Executing delay node {node.id} with {delay_seconds}s delay")
        await asyncio.sleep(delay_seconds)
        return {"delay_completed": True, "node_id": node.id}

    async def _execute_webhook_node(
        self,
        node,
        input_data: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """Execute webhook node."""
        logger.info(f"Executing webhook node {node.id}")
        return {"webhook_sent": True, "node_id": node.id}

    async def _execute_script_node(
        self,
        node,
        input_data: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """Execute script node."""
        logger.info(f"Executing script node {node.id}")
        return {"script_executed": True, "node_id": node.id}