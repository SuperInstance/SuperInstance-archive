"""
Execution management endpoints.

This module provides endpoints for managing workflow executions, including
starting, stopping, monitoring, and retrieving execution results.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_database_session,
    get_workflow_service,
    get_workflow_executor,
    get_pagination_params,
    get_search_params,
    get_current_user,
    PaginationParams,
    SearchParams
)
from app.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.exceptions.models import (
    PaginatedResponse,
    SuccessResponse,
    DeletedResponse
)
from app.models.execution_model import Execution, ExecutionStatus
from app.schemas.execution import (
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionUpdate,
    ExecutionLogResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# WebSocket connection manager for real-time execution updates
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, execution_id: str):
        """Connect a WebSocket to an execution."""
        await websocket.accept()
        if execution_id not in self.active_connections:
            self.active_connections[execution_id] = []
        self.active_connections[execution_id].append(websocket)
        logger.info(f"WebSocket connected for execution {execution_id}")

    def disconnect(self, websocket: WebSocket, execution_id: str):
        """Disconnect a WebSocket from an execution."""
        if execution_id in self.active_connections:
            if websocket in self.active_connections[execution_id]:
                self.active_connections[execution_id].remove(websocket)
            if not self.active_connections[execution_id]:
                del self.active_connections[execution_id]
        logger.info(f"WebSocket disconnected for execution {execution_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        await websocket.send_text(message)

    async def broadcast_to_execution(self, message: str, execution_id: str):
        """Broadcast a message to all connections for an execution."""
        if execution_id in self.active_connections:
            for connection in self.active_connections[execution_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Connection might be closed, remove it
                    self.active_connections[execution_id].remove(connection)


manager = ConnectionManager()


@router.get("/", response_model=PaginatedResponse, summary="List executions")
async def list_executions(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: SearchParams = Depends(get_search_params),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> PaginatedResponse:
    """
    List executions with pagination and filtering.

    Returns a paginated list of executions with optional filtering by status,
    workflow, creator, and other parameters.
    """
    try:
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if workflow_id:
            filters["workflow_id"] = workflow_id
        if created_by:
            filters["created_by"] = created_by

        # If not admin, only show user's executions
        if not current_user.get("is_admin", False):
            filters["created_by"] = current_user["id"]

        # Get executions
        executions, total = await workflow_service.list_executions(
            page=pagination.page,
            size=pagination.size,
            search=search.search,
            sort_by=search.sort_by,
            sort_order=search.sort_order,
            filters=filters
        )

        # Convert to response format
        execution_responses = [ExecutionResponse.from_orm(execution) for execution in executions]

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
            data=execution_responses,
            pagination=pagination_info
        )

    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}")
        raise


@router.get("/{execution_id}", response_model=ExecutionResponse, summary="Get execution")
async def get_execution(
    execution_id: UUID = Path(..., description="Execution ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> ExecutionResponse:
    """
    Get detailed information about a specific execution.

    Returns comprehensive information about the specified execution,
    including status, progress, logs, and results.
    """
    try:
        execution = await workflow_service.get_execution_by_id(str(execution_id))
        if not execution:
            raise NotFoundError("Execution not found", resource_type="execution", resource_id=str(execution_id))

        # Check permissions
        if not _can_access_execution(execution, current_user):
            raise ForbiddenError("You don't have permission to access this execution")

        return ExecutionResponse.from_orm(execution)
    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Error getting execution {execution_id}: {str(e)}")
        raise


@router.post("/{execution_id}/stop", response_model=SuccessResponse, summary="Stop execution")
async def stop_execution(
    execution_id: UUID = Path(..., description="Execution ID"),
    force: bool = Query(False, description="Force stop the execution"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_executor = Depends(get_workflow_executor)
) -> SuccessResponse:
    """
    Stop a running execution.

    Stops the specified execution gracefully or forcefully.
    Only the owner or admins can stop executions.
    """
    try:
        execution = await workflow_service.get_execution_by_id(str(execution_id))
        if not execution:
            raise NotFoundError("Execution not found", resource_type="execution", resource_id=str(execution_id))

        # Check permissions
        if not _can_stop_execution(execution, current_user):
            raise ForbiddenError("You don't have permission to stop this execution")

        # Stop execution
        await workflow_executor.stop_execution(str(execution_id), force=force)

        logger.info(f"Stopped execution {execution_id} by user {current_user['id']} (force: {force})")

        return SuccessResponse(
            message="Execution stopped successfully"
        )

    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Error stopping execution {execution_id}: {str(e)}")
        raise


@router.post("/{execution_id}/pause", response_model=SuccessResponse, summary="Pause execution")
async def pause_execution(
    execution_id: UUID = Path(..., description="Execution ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_executor = Depends(get_workflow_executor)
) -> SuccessResponse:
    """
    Pause a running execution.

    Pauses the specified execution, allowing it to be resumed later.
    Only the owner or admins can pause executions.
    """
    try:
        execution = await workflow_service.get_execution_by_id(str(execution_id))
        if not execution:
            raise NotFoundError("Execution not found", resource_type="execution", resource_id=str(execution_id))

        # Check permissions
        if not _can_stop_execution(execution, current_user):
            raise ForbiddenError("You don't have permission to pause this execution")

        # Pause execution
        await workflow_executor.pause_execution(str(execution_id))

        logger.info(f"Paused execution {execution_id} by user {current_user['id']}")

        return SuccessResponse(
            message="Execution paused successfully"
        )

    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Error pausing execution {execution_id}: {str(e)}")
        raise


@router.post("/{execution_id}/resume", response_model=SuccessResponse, summary="Resume execution")
async def resume_execution(
    execution_id: UUID = Path(..., description="Execution ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_executor = Depends(get_workflow_executor)
) -> SuccessResponse:
    """
    Resume a paused execution.

    Resumes the specified execution from where it was paused.
    Only the owner or admins can resume executions.
    """
    try:
        execution = await workflow_service.get_execution_by_id(str(execution_id))
        if not execution:
            raise NotFoundError("Execution not found", resource_type="execution", resource_id=str(execution_id))

        # Check permissions
        if not _can_stop_execution(execution, current_user):
            raise ForbiddenError("You don't have permission to resume this execution")

        # Resume execution
        await workflow_executor.resume_execution(str(execution_id))

        logger.info(f"Resumed execution {execution_id} by user {current_user['id']}")

        return SuccessResponse(
            message="Execution resumed successfully"
        )

    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Error resuming execution {execution_id}: {str(e)}")
        raise


@router.get("/{execution_id}/logs", summary="Get execution logs")
async def get_execution_logs(
    execution_id: UUID = Path(..., description="Execution ID"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> Dict[str, Any]:
    """
    Get logs for a specific execution.

    Returns paginated logs for the specified execution with optional filtering.
    """
    try:
        execution = await workflow_service.get_execution_by_id(str(execution_id))
        if not execution:
            raise NotFoundError("Execution not found", resource_type="execution", resource_id=str(execution_id))

        # Check permissions
        if not _can_access_execution(execution, current_user):
            raise ForbiddenError("You don't have permission to access this execution")

        # Get logs
        filters = {"execution_id": str(execution_id)}
        if level:
            filters["level"] = level
        if node_id:
            filters["node_id"] = node_id

        logs, total = await workflow_service.get_execution_logs(
            page=pagination.page,
            size=pagination.size,
            filters=filters
        )

        # Calculate pagination info
        pages = (total + pagination.size - 1) // pagination.size

        return {
            "logs": logs,
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
        logger.error(f"Error getting logs for execution {execution_id}: {str(e)}")
        raise


@router.get("/{execution_id}/results", summary="Get execution results")
async def get_execution_results(
    execution_id: UUID = Path(..., description="Execution ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> Dict[str, Any]:
    """
    Get results for a completed execution.

    Returns the final results and output data for the specified execution.
    """
    try:
        execution = await workflow_service.get_execution_by_id(str(execution_id))
        if not execution:
            raise NotFoundError("Execution not found", resource_type="execution", resource_id=str(execution_id))

        # Check permissions
        if not _can_access_execution(execution, current_user):
            raise ForbiddenError("You don't have permission to access this execution")

        # Get results
        results = await workflow_service.get_execution_results(str(execution_id))

        return results

    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Error getting results for execution {execution_id}: {str(e)}")
        raise


@router.websocket("/{execution_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    execution_id: str,
) -> None:
    """
    WebSocket endpoint for real-time execution updates.

    Provides real-time updates about execution progress, logs, and status changes.
    """
    await manager.connect(websocket, execution_id)
    try:
        while True:
            # Wait for messages from client (ping/pong, etc.)
            data = await websocket.receive_text()

            # Echo back or handle client messages
            await manager.send_personal_message(f"Echo: {data}", websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, execution_id)


@router.get("/{execution_id}/nodes/{node_id}/logs", summary="Get node execution logs")
async def get_node_execution_logs(
    execution_id: UUID = Path(..., description="Execution ID"),
    node_id: str = Path(..., description="Node ID"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service)
) -> Dict[str, Any]:
    """
    Get logs for a specific node within an execution.

    Returns paginated logs for the specified node execution.
    """
    try:
        execution = await workflow_service.get_execution_by_id(str(execution_id))
        if not execution:
            raise NotFoundError("Execution not found", resource_type="execution", resource_id=str(execution_id))

        # Check permissions
        if not _can_access_execution(execution, current_user):
            raise ForbiddenError("You don't have permission to access this execution")

        # Get node logs
        filters = {
            "execution_id": str(execution_id),
            "node_id": node_id
        }
        if level:
            filters["level"] = level

        logs, total = await workflow_service.get_execution_logs(
            page=pagination.page,
            size=pagination.size,
            filters=filters
        )

        # Calculate pagination info
        pages = (total + pagination.size - 1) // pagination.size

        return {
            "logs": logs,
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
        logger.error(f"Error getting node logs for execution {execution_id}, node {node_id}: {str(e)}")
        raise


@router.post("/{execution_id}/retry", response_model=CreatedResponse, status_code=202, summary="Retry execution")
async def retry_execution(
    execution_id: UUID = Path(..., description="Execution ID"),
    retry_from_node: Optional[str] = Query(None, description="Node ID to retry from"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow_service = Depends(get_workflow_service),
    workflow_executor = Depends(get_workflow_executor)
) -> CreatedResponse:
    """
    Retry a failed execution.

    Retries the specified execution, optionally from a specific node.
    Only the owner or admins can retry executions.
    """
    try:
        execution = await workflow_service.get_execution_by_id(str(execution_id))
        if not execution:
            raise NotFoundError("Execution not found", resource_type="execution", resource_id=str(execution_id))

        # Check permissions
        if not _can_stop_execution(execution, current_user):
            raise ForbiddenError("You don't have permission to retry this execution")

        # Retry execution
        new_execution = await workflow_executor.retry_execution(
            execution_id=str(execution_id),
            retry_from_node=retry_from_node
        )

        logger.info(f"Retried execution {execution_id} as {new_execution.id} by user {current_user['id']}")

        return CreatedResponse(
            message="Execution retry started successfully",
            data={
                "execution_id": new_execution.id,
                "original_execution_id": execution_id,
                "status": new_execution.status,
                "started_at": new_execution.started_at,
            },
            id=str(new_execution.id)
        )

    except (NotFoundError, ForbiddenError):
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Error retrying execution {execution_id}: {str(e)}")
        raise


# Helper functions
def _can_access_execution(execution: Any, current_user: Dict[str, Any]) -> bool:
    """Check if user can access the execution."""
    # Admins can access any execution
    if current_user.get("is_admin", False):
        return True

    # Users can access their own executions
    if str(execution.created_by) == current_user["id"]:
        return True

    # Check if user can access the workflow
    # This would require checking the workflow permissions
    # For now, assume they can if they created the execution
    return False


def _can_stop_execution(execution: Any, current_user: Dict[str, Any]) -> bool:
    """Check if user can stop/pause/resume the execution."""
    # Admins can stop any execution
    if current_user.get("is_admin", False):
        return True

    # Users can stop their own executions
    if str(execution.created_by) == current_user["id"]:
        return True

    return False