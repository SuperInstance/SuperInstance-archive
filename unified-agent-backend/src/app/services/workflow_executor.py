"""
Workflow Executor with DAG-based execution, checkpointing, and error handling.

This module implements the core workflow execution engine with support for:
- DAG-based workflow execution
- Sequential node processing
- State passing between nodes
- Checkpointing and recovery
- Error handling and retries
- Parallel execution support
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union
from uuid import UUID, uuid4

from app.models.workflow_model import (
    Workflow, WorkflowNode, WorkflowExecution,
    NodeType, NodeStatus, ExecutionStatus
)
from app.repositories.workflow_repository import (
    WorkflowRepository, WorkflowNodeRepository, WorkflowExecutionRepository
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionError(Exception):
    """Base exception for workflow execution errors."""
    pass


class NodeExecutionError(ExecutionError):
    """Exception for node execution errors."""
    pass


class WorkflowTimeoutError(ExecutionError):
    """Exception for workflow timeout errors."""
    pass


class WorkflowExecutor:
    """
    Workflow executor with DAG-based execution and comprehensive error handling.

    This class provides the core workflow execution engine with support for
    sequential processing, parallel execution, state management, and recovery.
    """

    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        node_repo: WorkflowNodeRepository,
        execution_repo: WorkflowExecutionRepository,
        *,
        max_concurrent_nodes: int = 10,
        checkpoint_interval: int = 5,
        default_timeout: int = 3600
    ):
        """
        Initialize workflow executor.

        Args:
            workflow_repo: Workflow repository
            node_repo: Workflow node repository
            execution_repo: Workflow execution repository
            max_concurrent_nodes: Maximum concurrent nodes execution
            checkpoint_interval: Checkpoint interval in nodes
            default_timeout: Default workflow timeout in seconds
        """
        self.workflow_repo = workflow_repo
        self.node_repo = node_repo
        self.execution_repo = execution_repo
        self.max_concurrent_nodes = max_concurrent_nodes
        self.checkpoint_interval = checkpoint_interval
        self.default_timeout = default_timeout

        # Node execution handlers
        self.node_handlers: Dict[str, Callable] = {
            NodeType.TRIGGER.value: self._execute_trigger_node,
            NodeType.AGENT_TASK.value: self._execute_agent_task_node,
            NodeType.DECISION.value: self._execute_decision_node,
            NodeType.PARALLEL.value: self._execute_parallel_node,
            NodeType.SINK.value: self._execute_sink_node,
            NodeType.DELAY.value: self._execute_delay_node,
            NodeType.WEBHOOK.value: self._execute_webhook_node,
            NodeType.SCRIPT.value: self._execute_script_node,
        }

        # Active executions tracking
        self.active_executions: Dict[str, asyncio.Task] = {}

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
        Execute a workflow.

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

        # Check if execution is already running
        if execution_id in self.active_executions:
            raise ExecutionError(f"Execution {execution_id} is already running")

        # Create execution task
        task = asyncio.create_task(
            self._execute_workflow_internal(
                workflow_id=workflow_id,
                execution_id=execution_id,
                input_data=input_data or {},
                triggered_by=triggered_by,
                resume_from_checkpoint=resume_from_checkpoint
            )
        )

        self.active_executions[execution_id] = task

        try:
            await task
        except Exception as e:
            logger.error(f"Workflow execution {execution_id} failed: {str(e)}")
            raise
        finally:
            self.active_executions.pop(execution_id, None)

        return execution_id

    async def _execute_workflow_internal(
        self,
        workflow_id: Union[UUID, str],
        execution_id: str,
        input_data: Dict[str, Any],
        triggered_by: Optional[str],
        resume_from_checkpoint: bool
    ) -> None:
        """
        Internal workflow execution logic.

        Args:
            workflow_id: Workflow ID
            execution_id: Execution ID
            input_data: Input data
            triggered_by: Trigger source
            resume_from_checkpoint: Whether to resume from checkpoint
        """
        execution = None
        try:
            # Get workflow with nodes
            workflow = await self.workflow_repo.get_with_nodes(workflow_id)
            if not workflow:
                raise ExecutionError(f"Workflow {workflow_id} not found")

            # Validate workflow
            validation_errors = workflow.validate_definition()
            if validation_errors:
                raise ExecutionError(f"Workflow validation failed: {validation_errors}")

            # Create or get execution record
            if resume_from_checkpoint:
                execution = await self.execution_repo.get_execution_by_id(execution_id)
                if not execution:
                    raise ExecutionError(f"Execution {execution_id} not found for resume")

                # Restore from checkpoint
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

            # Start execution
            execution.start()
            await self.execution_repo.update(db_obj=execution, obj_in={"status": ExecutionStatus.RUNNING.value})

            # Build execution graph
            graph = self._build_execution_graph(workflow.nodes, workflow.definition.get("edges", []))

            # Initialize execution context
            context = {
                "input_data": input_data,
                "variables": execution.variables.copy() or {},
                "node_results": {},
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "started_at": datetime.now(timezone.utc)
            }

            # Execute workflow graph
            await self._execute_graph(
                graph=graph,
                context=context,
                execution=execution,
                workflow=workflow,
                resume_from_checkpoint=resume_from_checkpoint
            )

            # Complete execution
            execution.complete(output_data=context.get("output_data", {}))
            await self.execution_repo.update(db_obj=execution, obj_in={
                "status": ExecutionStatus.COMPLETED.value,
                "output_data": context.get("output_data", {}),
                "variables": context.get("variables", {})
            })

            # Update workflow statistics
            execution_time = (datetime.now(timezone.utc) - context["started_at"]).total_seconds()
            await self.workflow_repo.update_execution_stats(workflow_id, execution_time, True)

            logger.info(f"Workflow execution {execution_id} completed successfully")

        except Exception as e:
            error_message = str(e)
            error_details = {"type": type(e).__name__, "message": error_message}

            if execution:
                execution.fail(error_message, error_details)
                await self.execution_repo.update(db_obj=execution, obj_in={
                    "status": ExecutionStatus.FAILED.value,
                    "error_message": error_message,
                    "error_details": error_details
                })

                # Update workflow statistics
                execution_time = (datetime.now(timezone.utc) - context.get("started_at", datetime.now(timezone.utc))).total_seconds()
                await self.workflow_repo.update_execution_stats(workflow_id, execution_time, False)

            logger.error(f"Workflow execution {execution_id} failed: {error_message}")
            raise ExecutionError(error_message) from e

    def _build_execution_graph(
        self,
        nodes: List[WorkflowNode],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build execution graph from nodes and edges.

        Args:
            nodes: List of workflow nodes
            edges: List of edges between nodes

        Returns:
            Execution graph dictionary
        """
        graph = {}

        # Initialize nodes
        for node in nodes:
            graph[node.node_id] = {
                "node": node,
                "dependencies": set(),
                "dependents": set(),
                "status": NodeStatus.PENDING.value,
                "result": None
            }

        # Add edges
        for edge in edges:
            source_id = edge.get("source")
            target_id = edge.get("target")

            if source_id in graph and target_id in graph:
                graph[target_id]["dependencies"].add(source_id)
                graph[source_id]["dependents"].add(target_id)

        return graph

    async def _execute_graph(
        self,
        graph: Dict[str, Dict[str, Any]],
        context: Dict[str, Any],
        execution: WorkflowExecution,
        workflow: Workflow,
        resume_from_checkpoint: bool
    ) -> None:
        """
        Execute workflow graph using topological sorting.

        Args:
            graph: Execution graph
            context: Execution context
            execution: Execution record
            workflow: Workflow model
            resume_from_checkpoint: Whether resuming from checkpoint
        """
        executed_nodes = set()
        checkpoint_counter = 0

        # Find trigger nodes (no dependencies)
        ready_nodes = [
            node_id for node_id, node_data in graph.items()
            if not node_data["dependencies"] and node_data["node"].node_type == NodeType.TRIGGER.value
        ]

        if not ready_nodes:
            raise ExecutionError("No trigger nodes found in workflow")

        # Process nodes in topological order
        while ready_nodes:
            # Check for workflow timeout
            if workflow.timeout_seconds:
                elapsed = (datetime.now(timezone.utc) - context["started_at"]).total_seconds()
                if elapsed > workflow.timeout_seconds:
                    raise WorkflowTimeoutError(f"Workflow execution timed out after {elapsed:.2f} seconds")

            # Process ready nodes (limit concurrency)
            batch_size = min(self.max_concurrent_nodes, len(ready_nodes))
            current_batch = ready_nodes[:batch_size]
            ready_nodes = ready_nodes[batch_size:]

            # Execute current batch
            await self._execute_node_batch(
                node_ids=current_batch,
                graph=graph,
                context=context,
                execution=execution
            )

            # Mark nodes as executed
            executed_nodes.update(current_batch)

            # Create checkpoint if needed
            checkpoint_counter += len(current_batch)
            if checkpoint_counter >= self.checkpoint_interval:
                await self._create_checkpoint(execution, context, executed_nodes)
                checkpoint_counter = 0

            # Find new ready nodes
            for node_id in current_batch:
                for dependent_id in graph[node_id]["dependents"]:
                    # Check if all dependencies are satisfied
                    dependencies = graph[dependent_id]["dependencies"]
                    if dependencies.issubset(executed_nodes):
                        ready_nodes.append(dependent_id)

        # Check if all nodes were executed
        if len(executed_nodes) != len(graph):
            unexecuted = set(graph.keys()) - executed_nodes
            raise ExecutionError(f"Circular dependency detected or unreachable nodes: {unexecuted}")

    async def _execute_node_batch(
        self,
        node_ids: List[str],
        graph: Dict[str, Dict[str, Any]],
        context: Dict[str, Any],
        execution: WorkflowExecution
    ) -> None:
        """
        Execute a batch of nodes concurrently.

        Args:
            node_ids: List of node IDs to execute
            graph: Execution graph
            context: Execution context
            execution: Execution record
        """
        # Execute nodes concurrently
        tasks = []
        for node_id in node_ids:
            task = asyncio.create_task(
                self._execute_node(node_id, graph, context, execution)
            )
            tasks.append(task)

        # Wait for all nodes to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                node_id = node_ids[i]
                raise NodeExecutionError(f"Node {node_id} failed: {str(result)}") from result

    async def _execute_node(
        self,
        node_id: str,
        graph: Dict[str, Dict[str, Any]],
        context: Dict[str, Any],
        execution: WorkflowExecution
    ) -> Any:
        """
        Execute a single node.

        Args:
            node_id: Node ID
            graph: Execution graph
            context: Execution context
            execution: Execution record

        Returns:
            Node execution result
        """
        node_data = graph[node_id]
        node = node_data["node"]

        try:
            logger.debug(f"Executing node {node_id} ({node.node_type})")

            # Update node status
            node_data["status"] = NodeStatus.RUNNING.value

            # Get node handler
            handler = self.node_handlers.get(node.node_type)
            if not handler:
                raise NodeExecutionError(f"No handler for node type: {node.node_type}")

            # Prepare node input
            node_input = self._prepare_node_input(node_id, graph, context)

            # Execute node with timeout
            timeout = node.timeout_seconds or 300  # Default 5 minutes
            result = await asyncio.wait_for(
                handler(node, node_input, context),
                timeout=timeout
            )

            # Store result
            node_data["result"] = result
            node_data["status"] = NodeStatus.COMPLETED.value
            context["node_results"][node_id] = result

            logger.debug(f"Node {node_id} completed successfully")
            return result

        except asyncio.TimeoutError:
            node_data["status"] = NodeStatus.FAILED.value
            raise NodeExecutionError(f"Node {node_id} timed out after {timeout} seconds")

        except Exception as e:
            node_data["status"] = NodeStatus.FAILED.value

            # Handle retries
            if node.can_execute():
                node.increment_retry()
                logger.warning(f"Node {node_id} failed, retrying ({node.retry_count}/{node.max_retries}): {str(e)}")

                # Wait before retry
                await asyncio.sleep(min(2 ** node.retry_count, 30))  # Exponential backoff

                # Retry execution
                return await self._execute_node(node_id, graph, context, execution)
            else:
                logger.error(f"Node {node_id} failed after {node.max_retries} retries: {str(e)}")
                raise NodeExecutionError(f"Node {node_id} failed: {str(e)}") from e

    def _prepare_node_input(
        self,
        node_id: str,
        graph: Dict[str, Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare input data for a node based on its dependencies.

        Args:
            node_id: Node ID
            graph: Execution graph
            context: Execution context

        Returns:
            Node input data
        """
        node_data = graph[node_id]
        dependencies = node_data["dependencies"]

        node_input = {
            "input_data": context.get("input_data", {}),
            "variables": context.get("variables", {}),
            "dependency_results": {}
        }

        # Add results from dependencies
        for dep_id in dependencies:
            if dep_id in context["node_results"]:
                node_input["dependency_results"][dep_id] = context["node_results"][dep_id]

        return node_input

    async def _create_checkpoint(
        self,
        execution: WorkflowExecution,
        context: Dict[str, Any],
        executed_nodes: Set[str]
    ) -> None:
        """
        Create a checkpoint for recovery.

        Args:
            execution: Execution record
            context: Execution context
            executed_nodes: Set of executed node IDs
        """
        try:
            checkpoint_data = {
                "input_data": context.get("input_data", {}),
                "variables": context.get("variables", {}),
                "node_results": {node_id: context["node_results"][node_id] for node_id in executed_nodes},
                "executed_nodes": list(executed_nodes),
                "checkpoint_at": datetime.now(timezone.utc).isoformat()
            }

            execution.create_checkpoint(checkpoint_data)
            await self.execution_repo.update(db_obj=execution, obj_in={
                "checkpoint_data": checkpoint_data
            })

            logger.debug(f"Created checkpoint for execution {execution.execution_id}")

        except Exception as e:
            logger.error(f"Failed to create checkpoint for execution {execution.execution_id}: {str(e)}")
            # Don't fail execution if checkpoint creation fails

    # Node execution handlers
    async def _execute_trigger_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute trigger node."""
        # Trigger nodes typically just pass through input data
        logger.info(f"Trigger node {node.node_id} activated")
        return input_data.get("input_data", {})

    async def _execute_agent_task_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute agent task node."""
        # This would integrate with the agent service
        # For now, simulate agent execution
        config = node.config or {}

        logger.info(f"Executing agent task node {node.node_id}")

        # Simulate processing time
        await asyncio.sleep(1)

        # Return processed result
        return {
            "agent_result": f"Processed by agent with config: {config}",
            "input_processed": True
        }

    async def _execute_decision_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute decision node."""
        config = node.config or {}
        condition = config.get("condition", "True")

        logger.info(f"Executing decision node {node.node_id} with condition: {condition}")

        # Simple condition evaluation (in real implementation, use safer evaluation)
        try:
            # This is a simplified evaluation - in production, use a proper expression engine
            result = eval(condition, {"__builtins__": {}}, {
                "input": input_data.get("input_data", {}),
                "variables": input_data.get("variables", {}),
                "dependencies": input_data.get("dependency_results", {})
            })

            return {
                "decision": result,
                "condition": condition,
                "path": "true" if result else "false"
            }
        except Exception as e:
            raise NodeExecutionError(f"Decision evaluation failed: {str(e)}")

    async def _execute_parallel_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute parallel node."""
        config = node.config or {}
        parallel_tasks = config.get("tasks", [])

        logger.info(f"Executing parallel node {node.node_id} with {len(parallel_tasks)} tasks")

        # Execute parallel tasks
        tasks = []
        for task in parallel_tasks:
            task_coro = self._execute_parallel_task(task, input_data)
            tasks.append(asyncio.create_task(task_coro))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        successful_results = []
        failed_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({"task_index": i, "error": str(result)})
            else:
                successful_results.append({"task_index": i, "result": result})

        return {
            "successful_tasks": successful_results,
            "failed_tasks": failed_results,
            "total_tasks": len(parallel_tasks),
            "success_count": len(successful_results),
            "failure_count": len(failed_results)
        }

    async def _execute_parallel_task(
        self,
        task: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Any:
        """Execute a single parallel task."""
        # Simulate task execution
        await asyncio.sleep(0.5)
        return {"task_data": task, "processed": True}

    async def _execute_sink_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute sink node."""
        config = node.config or {}
        output_format = config.get("output_format", "raw")

        logger.info(f"Executing sink node {node.node_id} with format: {output_format}")

        # Prepare final output
        output = {
            "final_result": input_data.get("input_data", {}),
            "node_results": input_data.get("dependency_results", {}),
            "execution_summary": {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "output_format": output_format
            }
        }

        # Update context with final output
        context["output_data"] = output

        return output

    async def _execute_delay_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute delay node."""
        config = node.config or {}
        delay_seconds = config.get("delay_seconds", 1)

        logger.info(f"Executing delay node {node.node_id} for {delay_seconds} seconds")

        await asyncio.sleep(delay_seconds)

        return {
            "delayed": True,
            "delay_seconds": delay_seconds,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }

    async def _execute_webhook_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute webhook node."""
        config = node.config or {}
        url = config.get("url")
        method = config.get("method", "POST")

        logger.info(f"Executing webhook node {node.node_id} - {method} {url}")

        # In a real implementation, make HTTP request here
        # For now, simulate webhook call
        await asyncio.sleep(0.5)

        return {
            "webhook_called": True,
            "url": url,
            "method": method,
            "response": {"status": "success", "message": "Webhook executed"}
        }

    async def _execute_script_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute script node."""
        config = node.config or {}
        script = config.get("script", "")

        logger.info(f"Executing script node {node.node_id}")

        # In a real implementation, use a secure script execution environment
        # For now, simulate script execution
        await asyncio.sleep(1)

        return {
            "script_executed": True,
            "result": f"Script execution result for: {script[:50]}..."
        }

    # Execution management methods
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if cancellation was successful
        """
        try:
            # Check if execution is running
            if execution_id not in self.active_executions:
                return False

            # Cancel the task
            task = self.active_executions[execution_id]
            task.cancel()

            # Update execution record
            execution = await self.execution_repo.get_execution_by_id(execution_id)
            if execution:
                execution.cancel()
                await self.execution_repo.update(db_obj=execution, obj_in={
                    "status": ExecutionStatus.CANCELLED.value
                })

            logger.info(f"Cancelled workflow execution {execution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {str(e)}")
            return False

    async def pause_execution(self, execution_id: str) -> bool:
        """
        Pause a running execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if pause was successful
        """
        try:
            execution = await self.execution_repo.get_execution_by_id(execution_id)
            if not execution or execution.status != ExecutionStatus.RUNNING.value:
                return False

            execution.pause()
            await self.execution_repo.update(db_obj=execution, obj_in={
                "status": ExecutionStatus.PAUSED.value
            })

            logger.info(f"Paused workflow execution {execution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to pause execution {execution_id}: {str(e)}")
            return False

    async def resume_execution(self, execution_id: str) -> bool:
        """
        Resume a paused execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if resume was successful
        """
        try:
            execution = await self.execution_repo.get_execution_by_id(execution_id)
            if not execution or execution.status != ExecutionStatus.PAUSED.value:
                return False

            # Resume execution from checkpoint
            await self.execute_workflow(
                workflow_id=execution.workflow_id,
                input_data=execution.input_data,
                execution_id=execution_id,
                triggered_by=execution.triggered_by,
                resume_from_checkpoint=True
            )

            logger.info(f"Resumed workflow execution {execution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to resume execution {execution_id}: {str(e)}")
            return False

    def get_active_executions(self) -> List[str]:
        """
        Get list of active execution IDs.

        Returns:
            List of active execution IDs
        """
        return list(self.active_executions.keys())

    async def get_execution_status(self, execution_id: str) -> Optional[str]:
        """
        Get execution status.

        Args:
            execution_id: Execution ID

        Returns:
            Execution status or None if not found
        """
        try:
            execution = await self.execution_repo.get_execution_by_id(execution_id)
            return execution.status if execution else None

        except Exception as e:
            logger.error(f"Failed to get execution status for {execution_id}: {str(e)}")
            return None