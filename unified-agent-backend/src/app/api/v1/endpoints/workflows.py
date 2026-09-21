"""
Workflow management endpoints.

This module provides endpoints for creating, reading, updating, and managing workflows
in the system.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_database_session,
    get_workflow_service,
    get_pagination_params,
    get_search_params,
    get_current_user,
    validate_workflow_exists,
    PaginationParams,
    SearchParams
)
from app.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.exceptions.models import (
    PaginatedResponse,
    SuccessResponse,
    CreatedResponse,
    UpdatedResponse,
    DeletedResponse
)
from app.models.workflow_model import Workflow, WorkflowStatus, NodeType
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowExecuteRequest
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse, summary="List workflows")
async def list_workflows(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: SearchParams = Depends(get_search_params),
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> PaginatedResponse:
    """
    List workflows with pagination and filtering.

    Returns a paginated list of workflows with optional filtering by status,
    creator, and other parameters.
    """
    try:
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if is_active is not None:
            filters["is_active"] = is_active
        if created_by:
            filters["created_by"] = created_by

        # If not admin, only show user's workflows
        if not current_user.get("is_admin", False):
            filters["created_by"] = current_user["id"]

        # Get workflows
        workflows, total = await workflow_service.list_workflows(
            page=pagination.page,
            size=pagination.size,
            search=search.search,
            sort_by=search.sort_by,
            sort_order=search.sort_order,
            filters=filters
        )

        # Convert to response format
        workflow_responses = [WorkflowResponse.from_orm(workflow) for workflow in workflows]

        # Calculate pagination info
        pages = (total + pagination.size - 1) // pagination.size
        pagination_info = {
            "page": pagination.page,
            "size": pagination.size,
            "total": total,
            "pages": pages,
            "has_next": pagination.page < pages,
            "has_prev": pagination.page > 1,
        }

        return PaginatedResponse(
            data=workflow_responses,
            pagination=pagination_info
        )

    except Exception as e:
        logger.error(f"Error listing workflows: {str(e)}")
        raise


@router.get("/{workflow_id}", response_model=WorkflowResponse, summary="Get workflow")
async def get_workflow(
    workflow: Dict[str, Any] = Depends(validate_workflow_exists),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> WorkflowResponse:
    """
    Get detailed information about a specific workflow.

    Returns comprehensive information about the specified workflow,
    including nodes, edges, and execution history.
    """
    try:
        # Check permissions
        if not _can_access_workflow(workflow, current_user):
            raise ForbiddenError("You don't have permission to access this workflow")

        return WorkflowResponse.from_orm(workflow)
    except Exception as e:
        logger.error(f"Error getting workflow {workflow.id}: {str(e)}")
        raise


@router.post("/", response_model=CreatedResponse, status_code=201, summary="Create workflow")
async def create_workflow(
    workflow_data: WorkflowCreate,
    db: AsyncSession = Depends(get_database_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> CreatedResponse:
    """
    Create a new workflow.

    Creates a new workflow with the specified nodes, edges, and configuration.
    The creator will be set as the owner of the workflow.
    """
    try:
        # Create workflow
        workflow = await workflow_service.create_workflow(
            workflow_data=workflow_data,
            created_by=current_user["id"]
        )

        logger.info(f"Created workflow {workflow.id} by user {current_user['id']}")

        return CreatedResponse(
            message="Workflow created successfully",
            data=WorkflowResponse.from_orm(workflow),
            id=str(workflow.id)
        )

    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Error creating workflow: {str(e)}")
        raise


@router.put("/{workflow_id}", response_model=UpdatedResponse, summary="Update workflow")
async def update_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    workflow_data: WorkflowUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> UpdatedResponse:
    """
    Update an existing workflow.

    Updates the configuration, nodes, or edges of an existing workflow.
    Only the owner or admins can update workflows.
    """
    try:
        # Check permissions
        workflow = await workflow_service.get_workflow_by_id(str(workflow_id))
        if not workflow:
            raise NotFoundError("Workflow not found", resource_type="workflow", resource_id=str(workflow_id))

        if not _can_update_workflow(workflow, current_user):
            raise ForbiddenError("You don't have permission to update this workflow")

        # Update workflow
        updated_workflow = await workflow_service.update_workflow(
            workflow_id=str(workflow_id),
            workflow_data=workflow_data
        )

        logger.info(f"Updated workflow {workflow_id} by user {current_user['id']}")

        return UpdatedResponse(
            message="Workflow updated successfully",
            data=WorkflowResponse.from_orm(updated_workflow)
        )

    except (NotFoundError, ForbiddenError):
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Error updating workflow {workflow_id}: {str(e)}")
        raise


@router.delete("/{workflow_id}", response_model=DeletedResponse, status_code=204, summary="Delete workflow")
async def delete_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> DeletedResponse:
    """
    Delete a workflow.

    Soft deletes a workflow by marking it as archived.
    Only the owner or admins can delete workflows.
    """
    try:
        # Check permissions
        workflow = await workflow_service.get_workflow_by_id(str(workflow_id))
        if not workflow:
            raise NotFoundError("Workflow not found", resource_type="workflow", resource_id=str(workflow_id))

        if not _can_delete_workflow(workflow, current_user):
            raise ForbiddenError("You don't have permission to delete this workflow")

        # Delete workflow
        await workflow_service.delete_workflow(str(workflow_id))

        logger.info(f"Deleted workflow {workflow_id} by user {current_user['id']}")

        return DeletedResponse(
            message="Workflow deleted successfully"
        )

    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow {workflow_id}: {str(e)}")
        raise


@router.post("/{workflow_id}/execute", response_model=CreatedResponse, status_code=202, summary="Execute workflow")
async def execute_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    execute_request: Optional[WorkflowExecuteRequest] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service),
    workflow_executor = Depends(get_workflow_executor)
) -> CreatedResponse:
    """
    Execute a workflow.

    Starts execution of the specified workflow with optional input parameters.
    Returns the execution ID for tracking the execution progress.
    """
    try:
        # Check permissions
        workflow = await workflow_service.get_workflow_by_id(str(workflow_id))
        if not workflow:
            raise NotFoundError("Workflow not found", resource_type="workflow", resource_id=str(workflow_id))

        if not _can_execute_workflow(workflow, current_user):
            raise ForbiddenError("You don't have permission to execute this workflow")

        # Execute workflow
        execution = await workflow_executor.execute_workflow(
            workflow_id=str(workflow_id),
            input_data=execute_request.input_data if execute_request else {},
            execution_context={
                "user_id": current_user["id"],
                "request_id": getattr(current_user, "request_id", None),
            }
        )

        logger.info(f"Started execution {execution.id} for workflow {workflow_id} by user {current_user['id']}")

        return CreatedResponse(
            message="Workflow execution started successfully",
            data={
                "execution_id": execution.id,
                "workflow_id": workflow_id,
                "status": execution.status,
                "started_at": execution.started_at,
            },
            id=str(execution.id)
        )

    except (NotFoundError, ForbiddenError):
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Error executing workflow {workflow_id}: {str(e)}")
        raise


@router.post("/{workflow_id}/validate", response_model=SuccessResponse, summary="Validate workflow")
async def validate_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> SuccessResponse:
    """
    Validate a workflow.

    Validates the workflow structure, nodes, edges, and configuration
    to ensure it can be executed properly.
    """
    try:
        # Check permissions
        workflow = await workflow_service.get_workflow_by_id(str(workflow_id))
        if not workflow:
            raise NotFoundError("Workflow not found", resource_type="workflow", resource_id=str(workflow_id))

        if not _can_access_workflow(workflow, current_user):
            raise ForbiddenError("You don't have permission to access this workflow")

        # Validate workflow
        validation_result = await workflow_service.validate_workflow(str(workflow_id))

        if validation_result["is_valid"]:
            return SuccessResponse(
                message="Workflow is valid",
                data=validation_result
            )
        else:
            raise ValidationError(
                "Workflow validation failed",
                details={"errors": validation_result["errors"]}
            )

    except (NotFoundError, ForbiddenError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error validating workflow {workflow_id}: {str(e)}")
        raise


@router.get("/{workflow_id}/executions", summary="Get workflow executions")
async def get_workflow_executions(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> Dict[str, Any]:
    """
    Get execution history for a workflow.

    Returns a paginated list of executions for the specified workflow.
    """
    try:
        # Check permissions
        workflow = await workflow_service.get_workflow_by_id(str(workflow_id))
        if not workflow:
            raise NotFoundError("Workflow not found", resource_type="workflow", resource_id=str(workflow_id))

        if not _can_access_workflow(workflow, current_user):
            raise ForbiddenError("You don't have permission to access this workflow")

        # Get executions
        filters = {"workflow_id": str(workflow_id)}
        if status:
            filters["status"] = status

        executions, total = await workflow_service.get_workflow_executions(
            page=pagination.page,
            size=pagination.size,
            filters=filters
        )

        # Calculate pagination info
        pages = (total + pagination.size - 1) // pagination.size

        return {
            "executions": executions,
            "pagination": {
                "page": pagination.page,
                "size": pagination.size,
                "total": total,
                "pages": pages,
                "has_next": pagination.page < pages,
                "has_prev": pagination.page > 1,
            }
        }

    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Error getting executions for workflow {workflow_id}: {str(e)}")
        raise


@router.post("/{workflow_id}/clone", response_model=CreatedResponse, status_code=201, summary="Clone workflow")
async def clone_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    name: str = Query(..., description="Name for the cloned workflow"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> CreatedResponse:
    """
    Clone a workflow.

    Creates a copy of an existing workflow with a new name.
    The cloned workflow will be owned by the current user.
    """
    try:
        # Check permissions
        workflow = await workflow_service.get_workflow_by_id(str(workflow_id))
        if not workflow:
            raise NotFoundError("Workflow not found", resource_type="workflow", resource_id=str(workflow_id))

        if not _can_access_workflow(workflow, current_user):
            raise ForbiddenError("You don't have permission to access this workflow")

        # Clone workflow
        cloned_workflow = await workflow_service.clone_workflow(
            workflow_id=str(workflow_id),
            name=name,
            created_by=current_user["id"]
        )

        logger.info(f"Cloned workflow {workflow_id} to {cloned_workflow.id} by user {current_user['id']}")

        return CreatedResponse(
            message="Workflow cloned successfully",
            data=WorkflowResponse.from_orm(cloned_workflow),
            id=str(cloned_workflow.id)
        )

    except (NotFoundError, ForbiddenError):
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Error cloning workflow {workflow_id}: {str(e)}")
        raise


# Helper functions
def _can_access_workflow(workflow: Any, current_user: Dict[str, Any]) -> bool:
    """Check if user can access the workflow."""
    # Admins can access any workflow
    if current_user.get("is_admin", False):
        return True

    # Users can access their own workflows
    if str(workflow.created_by) == current_user["id"]:
        return True

    # Users can access public workflows
    if workflow.is_public:
        return True

    return False


def _can_update_workflow(workflow: Any, current_user: Dict[str, Any]) -> bool:
    """Check if user can update the workflow."""
    # Admins can update any workflow
    if current_user.get("is_admin", False):
        return True

    # Users can update their own workflows
    if str(workflow.created_by) == current_user["id"]:
        return True

    return False


def _can_delete_workflow(workflow: Any, current_user: Dict[str, Any]) -> bool:
    """Check if user can delete the workflow."""
    # Admins can delete any workflow
    if current_user.get("is_admin", False):
        return True

    # Users can delete their own workflows
    if str(workflow.created_by) == current_user["id"]:
        return True

    return False


def _can_execute_workflow(workflow: Any, current_user: Dict[str, Any]) -> bool:
    """Check if user can execute the workflow."""
    # Admins can execute any workflow
    if current_user.get("is_admin", False):
        return True

    # Users can execute their own workflows
    if str(workflow.created_by) == current_user["id"]:
        return True

    # Users can execute public workflows
    if workflow.is_public:
        return True

    return False