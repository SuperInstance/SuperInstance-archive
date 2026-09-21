"""
Tests for Workflow Service.

This module contains comprehensive tests for workflow service functionality
including CRUD operations, validation, execution management, and templates.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.workflow_model import (
    Workflow, WorkflowNode, WorkflowExecution,
    WorkflowStatus, NodeType, ExecutionStatus
)
from app.repositories.workflow_repository import (
    WorkflowRepository, WorkflowNodeRepository, WorkflowExecutionRepository
)
from app.services.workflow_service import WorkflowService, WorkflowValidationError
from app.services.workflow_executor import WorkflowExecutor


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
        max_concurrent_nodes=5,
        checkpoint_interval=2
    )


@pytest.fixture
def workflow_service(workflow_repo, node_repo, execution_repo, workflow_executor):
    """Create workflow service fixture."""
    return WorkflowService(
        workflow_repo=workflow_repo,
        node_repo=node_repo,
        execution_repo=execution_repo,
        executor=workflow_executor
    )


@pytest.fixture
def sample_workflow_definition():
    """Sample workflow definition for testing."""
    return {
        "nodes": [
            {
                "id": "trigger_1",
                "type": NodeType.TRIGGER.value,
                "name": "Start Trigger",
                "description": "Workflow start trigger"
            },
            {
                "id": "agent_1",
                "type": NodeType.AGENT_TASK.value,
                "name": "Process Data",
                "description": "Agent task to process data"
            },
            {
                "id": "decision_1",
                "type": NodeType.DECISION.value,
                "name": "Check Result",
                "description": "Decision node for routing"
            },
            {
                "id": "sink_1",
                "type": NodeType.SINK.value,
                "name": "End Workflow",
                "description": "Workflow end sink"
            }
        ],
        "edges": [
            {"source": "trigger_1", "target": "agent_1"},
            {"source": "agent_1", "target": "decision_1"},
            {"source": "decision_1", "target": "sink_1"}
        ]
    }


@pytest.fixture
def sample_workflow_data(sample_workflow_definition):
    """Sample workflow data for testing."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow for unit testing",
        "version": "1.0.0",
        "definition": sample_workflow_definition,
        "config": {"timeout": 300},
        "variables": {"input_var": "string", "output_var": "string"},
        "timeout_seconds": 600,
        "max_retries": 3,
        "tags": ["test", "sample"]
    }


class TestWorkflowService:
    """Test cases for Workflow Service."""

    @pytest.mark.asyncio
    async def test_create_workflow(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test workflow creation."""
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        assert workflow is not None
        assert workflow.id is not None
        assert workflow.name == sample_workflow_data["name"]
        assert workflow.description == sample_workflow_data["description"]
        assert workflow.status == WorkflowStatus.DRAFT.value
        assert workflow.created_by == sample_user_id
        assert workflow.tags == sample_workflow_data["tags"]

    @pytest.mark.asyncio
    async def test_create_workflow_validation_error(
        self,
        workflow_service
    ):
        """Test workflow creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "description": "Invalid workflow"
        }

        with pytest.raises(WorkflowValidationError):
            await workflow_service.create_workflow(invalid_data)

    @pytest.mark.asyncio
    async def test_get_workflow(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test getting a workflow."""
        # Create workflow
        created_workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        # Get workflow
        retrieved_workflow = await workflow_service.get_workflow(created_workflow.id)

        assert retrieved_workflow is not None
        assert retrieved_workflow.id == created_workflow.id
        assert retrieved_workflow.name == created_workflow.name

    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, workflow_service):
        """Test getting a non-existent workflow."""
        non_existent_id = uuid4()
        workflow = await workflow_service.get_workflow(non_existent_id)
        assert workflow is None

    @pytest.mark.asyncio
    async def test_update_workflow(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test updating a workflow."""
        # Create workflow
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        # Update workflow
        update_data = {
            "name": "Updated Workflow Name",
            "description": "Updated description",
            "status": WorkflowStatus.ACTIVE.value
        }

        updated_workflow = await workflow_service.update_workflow(
            workflow.id,
            update_data
        )

        assert updated_workflow is not None
        assert updated_workflow.name == "Updated Workflow Name"
        assert updated_workflow.description == "Updated description"
        assert updated_workflow.status == WorkflowStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_update_workflow_not_found(self, workflow_service):
        """Test updating a non-existent workflow."""
        non_existent_id = uuid4()
        update_data = {"name": "Updated Name"}

        result = await workflow_service.update_workflow(non_existent_id, update_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_workflow_soft(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test soft deleting a workflow."""
        # Create workflow
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        # Soft delete
        result = await workflow_service.delete_workflow(workflow.id, hard_delete=False)
        assert result is True

        # Check workflow is archived
        deleted_workflow = await workflow_service.get_workflow(workflow.id)
        assert deleted_workflow.status == WorkflowStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_delete_workflow_hard(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test hard deleting a workflow."""
        # Create workflow
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        # Hard delete
        result = await workflow_service.delete_workflow(workflow.id, hard_delete=True)
        assert result is True

        # Check workflow is completely deleted
        deleted_workflow = await workflow_service.get_workflow(workflow.id)
        assert deleted_workflow is None

    @pytest.mark.asyncio
    async def test_list_workflows(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test listing workflows."""
        # Create multiple workflows
        workflow_count = 5
        workflows = []

        for i in range(workflow_count):
            data = sample_workflow_data.copy()
            data["name"] = f"Test Workflow {i+1}"
            workflow = await workflow_service.create_workflow(
                data,
                created_by=sample_user_id
            )
            workflows.append(workflow)

        # List workflows
        listed_workflows = await workflow_service.list_workflows(limit=10)

        assert len(listed_workflows) >= workflow_count
        workflow_names = [w.name for w in listed_workflows]
        for i in range(workflow_count):
            assert f"Test Workflow {i+1}" in workflow_names

    @pytest.mark.asyncio
    async def test_validate_workflow_valid(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test validating a valid workflow."""
        # Create workflow
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        # Validate workflow
        errors = await workflow_service.validate_workflow(workflow.id)
        assert len(errors) == 0  # No errors for valid workflow

    @pytest.mark.asyncio
    async def test_validate_workflow_invalid(
        self,
        workflow_service,
        sample_user_id
    ):
        """Test validating an invalid workflow."""
        # Create invalid workflow (no trigger node)
        invalid_definition = {
            "nodes": [
                {
                    "id": "sink_1",
                    "type": NodeType.SINK.value,
                    "name": "End Workflow"
                }
            ],
            "edges": []
        }

        invalid_data = {
            "name": "Invalid Workflow",
            "description": "A workflow with invalid structure",
            "definition": invalid_definition
        }

        workflow = await workflow_service.create_workflow(
            invalid_data,
            created_by=sample_user_id
        )

        # Validate workflow
        errors = await workflow_service.validate_workflow(workflow.id)
        assert len(errors) > 0  # Should have validation errors
        assert any("trigger" in error.lower() for error in errors)

    @pytest.mark.asyncio
    async def test_test_workflow_dry_run(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test dry run workflow execution."""
        # Create workflow
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        # Test workflow with dry run
        test_input = {"test_data": "sample_input"}
        result = await workflow_service.test_workflow(
            workflow.id,
            test_input,
            dry_run=True
        )

        assert result is not None
        assert result["dry_run"] is True
        assert "execution_order" in result
        assert "simulated_results" in result
        assert len(result["execution_order"]) > 0

    @pytest.mark.asyncio
    async def test_create_template(
        self,
        workflow_service,
        sample_workflow_definition,
        sample_user_id
    ):
        """Test creating a workflow template."""
        template_data = {
            "name": "Test Template",
            "description": "A test workflow template",
            "definition": sample_workflow_definition,
            "version": "1.0.0"
        }

        category = "test_category"
        tags = ["template", "test"]

        template = await workflow_service.create_template(
            template_data,
            category=category,
            tags=tags,
            created_by=sample_user_id
        )

        assert template is not None
        assert template.is_template is True
        assert template.template_category == category
        assert template.template_tags == tags
        assert template.status == WorkflowStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_get_templates(
        self,
        workflow_service,
        sample_workflow_definition,
        sample_user_id
    ):
        """Test getting workflow templates."""
        # Create multiple templates
        templates_count = 3
        for i in range(templates_count):
            template_data = {
                "name": f"Template {i+1}",
                "description": f"Test template {i+1}",
                "definition": sample_workflow_definition,
                "version": "1.0.0"
            }
            await workflow_service.create_template(
                template_data,
                category="test",
                tags=["test", f"template_{i+1}"],
                created_by=sample_user_id
            )

        # Get templates
        templates = await workflow_service.get_templates()

        assert len(templates) >= templates_count
        for template in templates:
            assert template.is_template is True

    @pytest.mark.asyncio
    async def test_create_workflow_from_template(
        self,
        workflow_service,
        sample_workflow_definition,
        sample_user_id
    ):
        """Test creating a workflow from a template."""
        # Create template first
        template_data = {
            "name": "Source Template",
            "description": "Template for workflow creation",
            "definition": sample_workflow_definition,
            "config": {"template_config": "value"},
            "variables": {"template_var": "string"}
        }

        template = await workflow_service.create_template(
            template_data,
            category="test",
            created_by=sample_user_id
        )

        # Create workflow from template
        new_workflow_name = "Workflow from Template"
        customizations = {
            "description": "Custom description",
            "tags": ["custom", "from_template"]
        }

        workflow = await workflow_service.create_workflow_from_template(
            template.id,
            new_workflow_name,
            created_by=sample_user_id,
            customizations=customizations
        )

        assert workflow is not None
        assert workflow.name == new_workflow_name
        assert workflow.description == "Custom description"
        assert workflow.is_template is False
        assert workflow.tags == ["custom", "from_template"]
        assert workflow.definition == template.definition
        assert workflow.config == {"template_config": "value"}

    @pytest.mark.asyncio
    async def test_get_workflow_analytics(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test getting workflow analytics."""
        # Create workflow
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        # Get analytics
        analytics = await workflow_service.get_workflow_analytics()

        assert analytics is not None
        assert "workflow_statistics" in analytics
        assert "execution_statistics" in analytics
        assert "recent_executions" in analytics
        assert "active_executions" in analytics
        assert "period_days" in analytics

    @pytest.mark.asyncio
    async def test_execute_workflow_asynchronous(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test asynchronous workflow execution."""
        # Create and activate workflow
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )
        await workflow_service.update_workflow(
            workflow.id,
            {"status": WorkflowStatus.ACTIVE.value}
        )

        # Execute workflow asynchronously
        input_data = {"test_input": "test_value"}
        execution_id = await workflow_service.execute_workflow(
            workflow.id,
            input_data,
            triggered_by="test",
            asynchronous=True
        )

        assert execution_id is not None
        assert isinstance(execution_id, str)

        # Clean up - cancel execution
        await workflow_service.cancel_execution(execution_id)

    @pytest.mark.asyncio
    async def test_cleanup_old_data(
        self,
        workflow_service
    ):
        """Test cleaning up old data."""
        # Test cleanup (should not fail even with no old data)
        cleanup_result = await workflow_service.cleanup_old_data(days=1)

        assert "deleted_executions" in cleanup_result
        assert isinstance(cleanup_result["deleted_executions"], int)


class TestWorkflowValidation:
    """Test cases for workflow validation."""

    @pytest.mark.asyncio
    async def test_validate_workflow_with_cycles(self, workflow_service, sample_user_id):
        """Test validating workflow with cycles."""
        # Create workflow with cycle
        cyclical_definition = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": NodeType.TRIGGER.value,
                    "name": "Start"
                },
                {
                    "id": "agent_1",
                    "type": NodeType.AGENT_TASK.value,
                    "name": "Process"
                },
                {
                    "id": "sink_1",
                    "type": NodeType.SINK.value,
                    "name": "End"
                }
            ],
            "edges": [
                {"source": "trigger_1", "target": "agent_1"},
                {"source": "agent_1", "target": "sink_1"},
                {"source": "sink_1", "target": "trigger_1"}  # Creates cycle
            ]
        }

        workflow_data = {
            "name": "Cyclical Workflow",
            "description": "Workflow with cycle",
            "definition": cyclical_definition
        }

        workflow = await workflow_service.create_workflow(
            workflow_data,
            created_by=sample_user_id
        )

        # Should detect cycle
        errors = await workflow_service.validate_workflow(workflow.id)
        assert len(errors) > 0
        assert any("cycle" in error.lower() for error in errors)

    @pytest.mark.asyncio
    async def test_validate_workflow_with_invalid_edges(self, workflow_service, sample_user_id):
        """Test validating workflow with invalid edges."""
        # Create workflow with invalid edges
        invalid_definition = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": NodeType.TRIGGER.value,
                    "name": "Start"
                },
                {
                    "id": "sink_1",
                    "type": NodeType.SINK.value,
                    "name": "End"
                }
            ],
            "edges": [
                {"source": "trigger_1", "target": "non_existent_node"},  # Invalid target
                {"source": "another_non_existent", "target": "sink_1"}  # Invalid source
            ]
        }

        workflow_data = {
            "name": "Invalid Edges Workflow",
            "description": "Workflow with invalid edges",
            "definition": invalid_definition
        }

        workflow = await workflow_service.create_workflow(
            workflow_data,
            created_by=sample_user_id
        )

        # Should detect invalid edges
        errors = await workflow_service.validate_workflow(workflow.id)
        assert len(errors) > 0
        assert any("not found" in error.lower() for error in errors)


class TestWorkflowExecution:
    """Test cases for workflow execution."""

    @pytest.mark.asyncio
    async def test_execution_lifecycle(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test complete execution lifecycle."""
        # Create and activate workflow
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )
        await workflow_service.update_workflow(
            workflow.id,
            {"status": WorkflowStatus.ACTIVE.value}
        )

        # Start execution
        input_data = {"test_data": "sample"}
        execution_id = await workflow_service.execute_workflow(
            workflow.id,
            input_data,
            triggered_by="test"
        )

        # Get execution status
        status = await workflow_service.get_execution_status(execution_id)
        assert status is not None
        assert status["execution_id"] == execution_id
        assert status["workflow_id"] == str(workflow.id)

        # List executions
        executions = await workflow_service.list_executions(workflow.id)
        execution_ids = [e["execution_id"] for e in executions]
        assert execution_id in execution_ids

        # Cancel execution
        cancel_result = await workflow_service.cancel_execution(execution_id)
        assert cancel_result is True

    @pytest.mark.asyncio
    async def test_execution_with_inactive_workflow(
        self,
        workflow_service,
        sample_workflow_data,
        sample_user_id
    ):
        """Test execution with inactive workflow."""
        # Create workflow but don't activate
        workflow = await workflow_service.create_workflow(
            sample_workflow_data,
            created_by=sample_user_id
        )

        # Try to execute inactive workflow
        input_data = {"test_data": "sample"}

        with pytest.raises(WorkflowValidationError):
            await workflow_service.execute_workflow(workflow.id, input_data)

    @pytest.mark.asyncio
    async def test_execution_with_nonexistent_workflow(self, workflow_service):
        """Test execution with non-existent workflow."""
        non_existent_id = uuid4()
        input_data = {"test_data": "sample"}

        with pytest.raises(WorkflowValidationError):
            await workflow_service.execute_workflow(non_existent_id, input_data)