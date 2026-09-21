#!/usr/bin/env python3
"""
Basic test to verify workflow engine functionality without pytest dependencies.
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.models.workflow_model import (
    Workflow, WorkflowNode, WorkflowExecution,
    WorkflowStatus, NodeType, ExecutionStatus
)


def test_workflow_creation():
    """Test basic workflow creation."""
    print("Testing workflow creation...")

    workflow = Workflow(
        name="Test Workflow",
        description="A test workflow for basic testing",
        version="1.0.0",
        status=WorkflowStatus.DRAFT.value,
        definition={
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": NodeType.TRIGGER.value,
                    "name": "Start Trigger"
                },
                {
                    "id": "sink_1",
                    "type": NodeType.SINK.value,
                    "name": "End Sink"
                }
            ],
            "edges": [
                {"source": "trigger_1", "target": "sink_1"}
            ]
        }
    )

    assert workflow.name == "Test Workflow"
    assert workflow.description == "A test workflow for basic testing"
    assert workflow.version == "1.0.0"
    assert workflow.status == WorkflowStatus.DRAFT.value
    assert workflow.is_active is True
    assert workflow.is_template is False

    print("✓ Workflow creation test passed")


def test_workflow_validation():
    """Test workflow validation."""
    print("Testing workflow validation...")

    # Test valid workflow
    valid_workflow = Workflow(
        name="Valid Workflow",
        definition={
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": NodeType.TRIGGER.value,
                    "name": "Start Trigger"
                },
                {
                    "id": "sink_1",
                    "type": NodeType.SINK.value,
                    "name": "End Sink"
                }
            ],
            "edges": [
                {"source": "trigger_1", "target": "sink_1"}
            ]
        }
    )

    errors = valid_workflow.validate_definition()
    assert len(errors) == 0, f"Valid workflow should have no errors, got: {errors}"

    # Test invalid workflow (no trigger)
    invalid_workflow = Workflow(
        name="Invalid Workflow",
        definition={
            "nodes": [
                {
                    "id": "sink_1",
                    "type": NodeType.SINK.value,
                    "name": "End Sink"
                }
            ],
            "edges": []
        }
    )

    errors = invalid_workflow.validate_definition()
    assert len(errors) > 0, "Invalid workflow should have validation errors"
    assert any("trigger" in error.lower() for error in errors)

    print("✓ Workflow validation test passed")


def test_workflow_lifecycle():
    """Test workflow lifecycle management."""
    print("Testing workflow lifecycle...")

    workflow = Workflow(
        name="Lifecycle Test Workflow",
        status=WorkflowStatus.DRAFT.value
    )

    # Test activation
    result = workflow.activate()
    assert result is True
    assert workflow.status == WorkflowStatus.ACTIVE.value
    assert workflow.is_active is True

    # Test pausing
    result = workflow.pause()
    assert result is True
    assert workflow.status == WorkflowStatus.PAUSED.value

    # Test resuming
    result = workflow.resume()
    assert result is True
    assert workflow.status == WorkflowStatus.ACTIVE.value

    # Test cancelling
    result = workflow.cancel()
    assert result is True
    assert workflow.status == WorkflowStatus.CANCELLED.value

    # Test archiving
    result = workflow.archive()
    assert result is True
    assert workflow.status == WorkflowStatus.ARCHIVED.value
    assert workflow.is_active is False

    print("✓ Workflow lifecycle test passed")


def test_workflow_execution_stats():
    """Test workflow execution statistics."""
    print("Testing workflow execution statistics...")

    workflow = Workflow(
        name="Stats Test Workflow",
        total_executions=10,
        successful_executions=8,
        failed_executions=2,
        average_execution_time=30.0
    )

    # Test success rate
    success_rate = workflow.get_success_rate()
    assert success_rate == 80.0, f"Expected 80.0, got {success_rate}"

    # Test execution summary
    summary = workflow.get_execution_summary()
    assert "total_executions" in summary
    assert "successful_executions" in summary
    assert "failed_executions" in summary
    assert "success_rate" in summary
    assert summary["total_executions"] == 10
    assert summary["success_rate"] == 80.0

    # Test updating stats
    workflow.update_execution_stats(execution_time=25.0, success=True)
    assert workflow.total_executions == 11
    assert workflow.successful_executions == 9

    workflow.update_execution_stats(execution_time=45.0, success=False)
    assert workflow.total_executions == 12
    assert workflow.failed_executions == 3

    print("✓ Workflow execution stats test passed")


def test_workflow_node_creation():
    """Test workflow node creation."""
    print("Testing workflow node creation...")

    node = WorkflowNode(
        workflow_id=uuid4(),
        node_id="test_node",
        name="Test Node",
        description="A test node",
        node_type=NodeType.AGENT_TASK.value,
        config={"param": "value"},
        timeout_seconds=60,
        max_retries=3
    )

    assert node.node_id == "test_node"
    assert node.name == "Test Node"
    assert node.node_type == NodeType.AGENT_TASK.value
    assert node.config == {"param": "value"}
    assert node.timeout_seconds == 60
    assert node.max_retries == 3
    assert node.retry_count == 0

    # Test retry logic
    assert node.can_execute() is True
    node.increment_retry()
    assert node.retry_count == 1
    assert node.can_execute() is True

    node.retry_count = 3  # Max retries
    assert node.can_execute() is False

    node.reset_retry()
    assert node.retry_count == 0
    assert node.can_execute() is True

    print("✓ Workflow node creation test passed")


def test_workflow_execution_creation():
    """Test workflow execution creation."""
    print("Testing workflow execution creation...")

    execution = WorkflowExecution(
        workflow_id=uuid4(),
        execution_id="test_execution_123",
        status=ExecutionStatus.PENDING.value,
        input_data={"test": "data"},
        triggered_by="test_trigger"
    )

    assert execution.execution_id == "test_execution_123"
    assert execution.status == ExecutionStatus.PENDING.value
    assert execution.input_data == {"test": "data"}
    assert execution.triggered_by == "test_trigger"
    assert execution.started_at is None
    assert execution.completed_at is None

    # Test execution lifecycle
    execution.start()
    assert execution.status == ExecutionStatus.RUNNING.value
    assert execution.started_at is not None

    output_data = {"result": "success"}
    execution.complete(output_data=output_data)
    assert execution.status == ExecutionStatus.COMPLETED.value
    assert execution.completed_at is not None
    assert execution.output_data == output_data
    assert execution.duration_seconds is not None

    # Test state checks
    assert execution.is_running() is False
    assert execution.is_completed() is True

    print("✓ Workflow execution creation test passed")


def test_cycle_detection():
    """Test cycle detection in workflow graphs."""
    print("Testing cycle detection...")

    workflow = Workflow(name="Cycle Test Workflow")

    # Test linear workflow (no cycles)
    linear_nodes = [
        {"id": "trigger_1", "type": "trigger"},
        {"id": "agent_1", "type": "agent_task"},
        {"id": "sink_1", "type": "sink"}
    ]
    linear_edges = [
        {"source": "trigger_1", "target": "agent_1"},
        {"source": "agent_1", "target": "sink_1"}
    ]

    has_cycles = workflow._has_cycles(linear_nodes, linear_edges)
    assert has_cycles is False, "Linear workflow should not have cycles"

    # Test workflow with cycle
    cyclical_nodes = [
        {"id": "node_1", "type": "agent_task"},
        {"id": "node_2", "type": "agent_task"},
        {"id": "node_3", "type": "agent_task"}
    ]
    cyclical_edges = [
        {"source": "node_1", "target": "node_2"},
        {"source": "node_2", "target": "node_3"},
        {"source": "node_3", "target": "node_1"}  # Creates cycle
    ]

    has_cycles = workflow._has_cycles(cyclical_nodes, cyclical_edges)
    assert has_cycles is True, "Cyclical workflow should be detected"

    print("✓ Cycle detection test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("RUNNING WORKFLOW ENGINE BASIC TESTS")
    print("=" * 60)

    try:
        test_workflow_creation()
        test_workflow_validation()
        test_workflow_lifecycle()
        test_workflow_execution_stats()
        test_workflow_node_creation()
        test_workflow_execution_creation()
        test_cycle_detection()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("Workflow Engine is working correctly!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()