"""
Tests for Workflow Executor.

This module contains comprehensive tests for workflow executor functionality
including DAG execution, node processing, checkpointing, and error handling.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.models.workflow_model import (
    Workflow, WorkflowNode, WorkflowExecution,
    NodeType, NodeStatus, ExecutionStatus
)
from app.repositories.workflow_repository import (
    WorkflowRepository, WorkflowNodeRepository, WorkflowExecutionRepository
)
from app.services.workflow_executor import (
    WorkflowExecutor, ExecutionError, NodeExecutionError, WorkflowTimeoutError
)


@pytest.fixture
def workflow_repo(test_db_session):
    """Create workflow repository fixture."""
    return WorkflowRepository(test_db_session)


@pytest.fixture
def node_repo(test_db_session):
    """Create workflow node repository fixture."""
    return WorkflowNodeRepository(test_db_session)


@pytest.fixture
def execution_repo(test_db_session):
    """Create workflow execution repository fixture."""
    return WorkflowExecutionRepository(test_db_session)


@pytest.fixture
def workflow_executor(workflow_repo, node_repo, execution_repo):
    """Create workflow executor fixture."""
    return WorkflowExecutor(
        workflow_repo=workflow_repo,
        node_repo=node_repo,
        execution_repo=execution_repo,
        max_concurrent_nodes=3,
        checkpoint_interval=2,
        default_timeout=60
    )


@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    workflow = Workflow(
        name="Test Workflow",
        description="A test workflow for executor testing",
        version="1.0.0",
        status="active",
        definition={
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": NodeType.TRIGGER.value,
                    "name": "Start Trigger"
                },
                {
                    "id": "agent_1",
                    "type": NodeType.AGENT_TASK.value,
                    "name": "Process Data"
                },
                {
                    "id": "decision_1",
                    "type": NodeType.DECISION.value,
                    "name": "Check Result"
                },
                {
                    "id": "sink_1",
                    "type": NodeType.SINK.value,
                    "name": "End Workflow"
                }
            ],
            "edges": [
                {"source": "trigger_1", "target": "agent_1"},
                {"source": "agent_1", "target": "decision_1"},
                {"source": "decision_1", "target": "sink_1"}
            ]
        }
    )
    return workflow


@pytest.fixture
def sample_nodes():
    """Create sample workflow nodes."""
    nodes = [
        WorkflowNode(
            node_id="trigger_1",
            name="Start Trigger",
            description="Workflow start trigger",
            node_type=NodeType.TRIGGER.value,
            position_x=100,
            position_y=100
        ),
        WorkflowNode(
            node_id="agent_1",
            name="Process Data",
            description="Agent task to process data",
            node_type=NodeType.AGENT_TASK.value,
            config={"agent_id": "test_agent"},
            timeout_seconds=30,
            max_retries=2,
            position_x=300,
            position_y=100
        ),
        WorkflowNode(
            node_id="decision_1",
            name="Check Result",
            description="Decision node for routing",
            node_type=NodeType.DECISION.value,
            config={"condition": "True"},
            position_x=500,
            position_y=100
        ),
        WorkflowNode(
            node_id="sink_1",
            name="End Workflow",
            description="Workflow end sink",
            node_type=NodeType.SINK.value,
            position_x=700,
            position_y=100
        )
    ]
    return nodes


class TestWorkflowExecutor:
    """Test cases for Workflow Executor."""

    @pytest.mark.asyncio
    async def test_build_execution_graph(
        self,
        workflow_executor,
        sample_nodes
    ):
        """Test building execution graph from nodes and edges."""
        edges = [
            {"source": "trigger_1", "target": "agent_1"},
            {"source": "agent_1", "target": "decision_1"},
            {"source": "decision_1", "target": "sink_1"}
        ]

        graph = workflow_executor._build_execution_graph(sample_nodes, edges)

        # Check graph structure
        assert len(graph) == 4

        # Check trigger node (no dependencies)
        assert len(graph["trigger_1"]["dependencies"]) == 0
        assert len(graph["trigger_1"]["dependents"]) == 1
        assert "agent_1" in graph["trigger_1"]["dependents"]

        # Check agent node
        assert len(graph["agent_1"]["dependencies"]) == 1
        assert "trigger_1" in graph["agent_1"]["dependencies"]
        assert len(graph["agent_1"]["dependents"]) == 1
        assert "decision_1" in graph["agent_1"]["dependents"]

        # Check decision node
        assert len(graph["decision_1"]["dependencies"]) == 1
        assert "agent_1" in graph["decision_1"]["dependencies"]
        assert len(graph["decision_1"]["dependents"]) == 1
        assert "sink_1" in graph["decision_1"]["dependents"]

        # Check sink node (no dependents)
        assert len(graph["sink_1"]["dependencies"]) == 1
        assert "decision_1" in graph["sink_1"]["dependencies"]
        assert len(graph["sink_1"]["dependents"]) == 0

    @pytest.mark.asyncio
    async def test_prepare_node_input(
        self,
        workflow_executor,
        sample_nodes
    ):
        """Test preparing node input from context."""
        edges = [
            {"source": "trigger_1", "target": "agent_1"},
            {"source": "agent_1", "target": "decision_1"}
        ]

        graph = workflow_executor._build_execution_graph(sample_nodes, edges)

        context = {
            "input_data": {"test_key": "test_value"},
            "variables": {"var1": "value1"},
            "node_results": {
                "trigger_1": {"triggered": True, "data": "sample"}
            }
        }

        # Prepare input for agent_1 (depends on trigger_1)
        node_input = workflow_executor._prepare_node_input("agent_1", graph, context)

        assert node_input["input_data"] == {"test_key": "test_value"}
        assert node_input["variables"] == {"var1": "value1"}
        assert "trigger_1" in node_input["dependency_results"]
        assert node_input["dependency_results"]["trigger_1"] == {"triggered": True, "data": "sample"}

    @pytest.mark.asyncio
    async def test_execute_trigger_node(
        self,
        workflow_executor,
        sample_nodes
    ):
        """Test executing a trigger node."""
        trigger_node = sample_nodes[0]  # trigger_1
        input_data = {
            "input_data": {"test": "data"},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        result = await workflow_executor._execute_trigger_node(
            trigger_node,
            input_data,
            context
        )

        assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_execute_agent_task_node(
        self,
        workflow_executor,
        sample_nodes
    ):
        """Test executing an agent task node."""
        agent_node = sample_nodes[1]  # agent_1
        input_data = {
            "input_data": {"task": "process"},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        result = await workflow_executor._execute_agent_task_node(
            agent_node,
            input_data,
            context
        )

        assert result is not None
        assert "agent_result" in result
        assert "input_processed" in result
        assert result["input_processed"] is True

    @pytest.mark.asyncio
    async def test_execute_decision_node(
        self,
        workflow_executor,
        sample_nodes
    ):
        """Test executing a decision node."""
        decision_node = sample_nodes[2]  # decision_1
        decision_node.config = {"condition": "True"}

        input_data = {
            "input_data": {"value": 10},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        result = await workflow_executor._execute_decision_node(
            decision_node,
            input_data,
            context
        )

        assert result is not None
        assert "decision" in result
        assert "condition" in result
        assert "path" in result
        assert result["decision"] is True
        assert result["path"] == "true"

    @pytest.mark.asyncio
    async def test_execute_decision_node_false_condition(
        self,
        workflow_executor,
        sample_nodes
    ):
        """Test executing a decision node with false condition."""
        decision_node = sample_nodes[2]  # decision_1
        decision_node.config = {"condition": "False"}

        input_data = {
            "input_data": {"value": 10},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        result = await workflow_executor._execute_decision_node(
            decision_node,
            input_data,
            context
        )

        assert result["decision"] is False
        assert result["path"] == "false"

    @pytest.mark.asyncio
    async def test_execute_parallel_node(
        self,
        workflow_executor,
        sample_nodes
    ):
        """Test executing a parallel node."""
        parallel_node = WorkflowNode(
            node_id="parallel_1",
            name="Parallel Tasks",
            node_type=NodeType.PARALLEL.value,
            config={
                "tasks": [
                    {"task_id": "task1", "data": "data1"},
                    {"task_id": "task2", "data": "data2"},
                    {"task_id": "task3", "data": "data3"}
                ]
            }
        )

        input_data = {
            "input_data": {"parallel": "test"},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        result = await workflow_executor._execute_parallel_node(
            parallel_node,
            input_data,
            context
        )

        assert result is not None
        assert "successful_tasks" in result
        assert "failed_tasks" in result
        assert "total_tasks" in result
        assert "success_count" in result
        assert "failure_count" in result
        assert result["total_tasks"] == 3
        assert result["success_count"] == 3
        assert result["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_sink_node(
        self,
        workflow_executor,
        sample_nodes
    ):
        """Test executing a sink node."""
        sink_node = sample_nodes[3]  # sink_1

        input_data = {
            "input_data": {"final": "result"},
            "variables": {},
            "dependency_results": {
                "agent_1": {"processed": True}
            }
        }
        context = {}

        result = await workflow_executor._execute_sink_node(
            sink_node,
            input_data,
            context
        )

        assert result is not None
        assert "final_result" in result
        assert "node_results" in result
        assert "execution_summary" in result
        assert result["final_result"] == {"final": "result"}
        assert context["output_data"] == result

    @pytest.mark.asyncio
    async def test_execute_delay_node(
        self,
        workflow_executor
    ):
        """Test executing a delay node."""
        delay_node = WorkflowNode(
            node_id="delay_1",
            name="Delay Node",
            node_type=NodeType.DELAY.value,
            config={"delay_seconds": 1}
        )

        input_data = {
            "input_data": {"test": "data"},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        start_time = datetime.now(timezone.utc)
        result = await workflow_executor._execute_delay_node(
            delay_node,
            input_data,
            context
        )
        end_time = datetime.now(timezone.utc)

        assert result is not None
        assert "delayed" in result
        assert "delay_seconds" in result
        assert "completed_at" in result
        assert result["delayed"] is True
        assert result["delay_seconds"] == 1

        # Check that delay actually occurred
        duration = (end_time - start_time).total_seconds()
        assert duration >= 1.0

    @pytest.mark.asyncio
    async def test_execute_webhook_node(
        self,
        workflow_executor
    ):
        """Test executing a webhook node."""
        webhook_node = WorkflowNode(
            node_id="webhook_1",
            name="Webhook Node",
            node_type=NodeType.WEBHOOK.value,
            config={
                "url": "https://example.com/webhook",
                "method": "POST"
            }
        )

        input_data = {
            "input_data": {"webhook_data": "test"},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        result = await workflow_executor._execute_webhook_node(
            webhook_node,
            input_data,
            context
        )

        assert result is not None
        assert "webhook_called" in result
        assert "url" in result
        assert "method" in result
        assert "response" in result
        assert result["webhook_called"] is True
        assert result["url"] == "https://example.com/webhook"
        assert result["method"] == "POST"

    @pytest.mark.asyncio
    async def test_execute_script_node(
        self,
        workflow_executor
    ):
        """Test executing a script node."""
        script_node = WorkflowNode(
            node_id="script_1",
            name="Script Node",
            node_type=NodeType.SCRIPT.value,
            config={"script": "print('Hello, World!')"}
        )

        input_data = {
            "input_data": {"script_input": "test"},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        result = await workflow_executor._execute_script_node(
            script_node,
            input_data,
            context
        )

        assert result is not None
        assert "script_executed" in result
        assert "result" in result
        assert result["script_executed"] is True

    @pytest.mark.asyncio
    async def test_node_retry_mechanism(
        self,
        workflow_executor,
        node_repo,
        test_db_session
    ):
        """Test node retry mechanism."""
        # Create a node that will fail
        failing_node = WorkflowNode(
            node_id="failing_node",
            name="Failing Node",
            node_type=NodeType.AGENT_TASK.value,
            max_retries=2,
            retry_count=0
        )

        # Mock the agent task handler to fail
        original_handler = workflow_executor._execute_agent_task_node

        async def failing_handler(node, input_data, context):
            if node.retry_count < node.max_retries:
                raise Exception("Simulated node failure")
            return {"success": True, "retry_count": node.retry_count}

        workflow_executor._execute_agent_task_node = failing_handler

        try:
            # Execute node (should retry and eventually succeed)
            input_data = {
                "input_data": {"test": "retry"},
                "variables": {},
                "dependency_results": {}
            }
            context = {}

            result = await workflow_executor._execute_node(
                "failing_node",
                {"failing_node": {"node": failing_node}},
                context,
                None  # execution not needed for this test
            )

            assert result is not None
            assert result["success"] is True
            assert failing_node.retry_count > 0  # Should have retried

        finally:
            # Restore original handler
            workflow_executor._execute_agent_task_node = original_handler

    @pytest.mark.asyncio
    async def test_node_timeout(
        self,
        workflow_executor
    ):
        """Test node timeout handling."""
        slow_node = WorkflowNode(
            node_id="slow_node",
            name="Slow Node",
            node_type=NodeType.DELAY.value,
            config={"delay_seconds": 10},  # 10 second delay
            timeout_seconds=1  # 1 second timeout
        )

        input_data = {
            "input_data": {"test": "timeout"},
            "variables": {},
            "dependency_results": {}
        }
        context = {}

        # Should timeout after 1 second
        with pytest.raises(NodeExecutionError, match="timed out"):
            await workflow_executor._execute_node(
                "slow_node",
                {"slow_node": {"node": slow_node}},
                context,
                None
            )

    @pytest.mark.asyncio
    async def test_create_checkpoint(
        self,
        workflow_executor,
        execution_repo,
        test_db_session
    ):
        """Test checkpoint creation."""
        # Create execution
        execution = await execution_repo.create(
            obj_in={
                "workflow_id": uuid4(),
                "execution_id": "test_execution",
                "status": ExecutionStatus.RUNNING.value,
                "input_data": {"test": "data"}
            }
        )

        context = {
            "input_data": {"checkpoint": "test"},
            "variables": {"var1": "value1"},
            "node_results": {"node1": {"result": "success"}}
        }
        executed_nodes = {"node1"}

        # Create checkpoint
        await workflow_executor._create_checkpoint(
            execution,
            context,
            executed_nodes
        )

        # Check checkpoint was created
        updated_execution = await execution_repo.get(execution.id)
        assert updated_execution.checkpoint_data is not None
        assert updated_execution.last_checkpoint_at is not None

        checkpoint_data = updated_execution.checkpoint_data
        assert checkpoint_data["input_data"] == {"checkpoint": "test"}
        assert checkpoint_data["variables"] == {"var1": "value1"}
        assert checkpoint_data["executed_nodes"] == ["node1"]

    @pytest.mark.asyncio
    async def test_cancel_execution(
        self,
        workflow_executor,
        execution_repo,
        test_db_session
    ):
        """Test cancelling an execution."""
        # Create execution
        execution = await execution_repo.create(
            obj_in={
                "workflow_id": uuid4(),
                "execution_id": "test_cancel_execution",
                "status": ExecutionStatus.RUNNING.value,
                "input_data": {"test": "data"}
            }
        )

        # Mock active execution
        workflow_executor.active_executions["test_cancel_execution"] = asyncio.create_task(
            asyncio.sleep(10)  # Long-running task
        )

        # Cancel execution
        result = await workflow_executor.cancel_execution("test_cancel_execution")

        assert result is True

        # Check execution status
        updated_execution = await execution_repo.get_execution_by_id("test_cancel_execution")
        assert updated_execution.status == ExecutionStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_pause_and_resume_execution(
        self,
        workflow_executor,
        execution_repo,
        test_db_session
    ):
        """Test pausing and resuming an execution."""
        # Create execution
        execution = await execution_repo.create(
            obj_in={
                "workflow_id": uuid4(),
                "execution_id": "test_pause_resume",
                "status": ExecutionStatus.RUNNING.value,
                "input_data": {"test": "data"}
            }
        )

        # Pause execution
        pause_result = await workflow_executor.pause_execution("test_pause_resume")
        assert pause_result is True

        # Check execution is paused
        paused_execution = await execution_repo.get_execution_by_id("test_pause_resume")
        assert paused_execution.status == ExecutionStatus.PAUSED.value

        # Resume execution (this will try to execute, but we'll catch the error)
        # Note: In a real scenario, you'd have a valid workflow to resume
        with pytest.raises(Exception):  # Expected to fail since no valid workflow
            await workflow_executor.resume_execution("test_pause_resume")

    @pytest.mark.asyncio
    async def test_get_active_executions(self, workflow_executor):
        """Test getting active executions."""
        # Initially no active executions
        active = workflow_executor.get_active_executions()
        assert len(active) == 0

        # Mock an active execution
        workflow_executor.active_executions["test_active"] = asyncio.create_task(
            asyncio.sleep(1)
        )

        active = workflow_executor.get_active_executions()
        assert len(active) == 1
        assert "test_active" in active

        # Clean up
        workflow_executor.active_executions["test_active"].cancel()
        workflow_executor.active_executions.clear()

    @pytest.mark.asyncio
    async def test_get_execution_status(
        self,
        workflow_executor,
        execution_repo,
        test_db_session
    ):
        """Test getting execution status."""
        # Create execution
        execution = await execution_repo.create(
            obj_in={
                "workflow_id": uuid4(),
                "execution_id": "test_status",
                "status": ExecutionStatus.RUNNING.value,
                "input_data": {"test": "data"}
            }
        )

        # Get status
        status = await workflow_executor.get_execution_status("test_status")
        assert status == ExecutionStatus.RUNNING.value

        # Test non-existent execution
        status = await workflow_executor.get_execution_status("non_existent")
        assert status is None


class TestWorkflowExecutorIntegration:
    """Integration tests for workflow executor."""

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(
        self,
        workflow_executor,
        workflow_repo,
        node_repo,
        execution_repo,
        test_db_session,
        sample_workflow,
        sample_nodes
    ):
        """Test executing a simple workflow end-to-end."""
        # Save workflow and nodes
        saved_workflow = await workflow_repo.create(obj_in={
            "name": sample_workflow.name,
            "description": sample_workflow.description,
            "version": sample_workflow.version,
            "status": "active",
            "definition": sample_workflow.definition
        })

        # Save nodes
        for node in sample_nodes:
            node.workflow_id = saved_workflow.id
        saved_nodes = await node_repo.bulk_create_nodes(saved_workflow.id, [
            {
                "node_id": node.node_id,
                "name": node.name,
                "description": node.description,
                "node_type": node.node_type,
                "config": node.config,
                "timeout_seconds": node.timeout_seconds,
                "max_retries": node.max_retries,
                "position_x": node.position_x,
                "position_y": node.position_y
            }
            for node in sample_nodes
        ])

        # Execute workflow
        execution_id = await workflow_executor.execute_workflow(
            workflow_id=saved_workflow.id,
            input_data={"test_input": "test_value"},
            triggered_by="integration_test"
        )

        assert execution_id is not None

        # Wait a bit for execution to complete or cancel it
        await asyncio.sleep(0.5)

        # Cancel to clean up
        await workflow_executor.cancel_execution(execution_id)

        # Check execution record exists
        execution = await execution_repo.get_execution_by_id(execution_id)
        assert execution is not None
        assert execution.workflow_id == saved_workflow.id
        assert execution.execution_id == execution_id