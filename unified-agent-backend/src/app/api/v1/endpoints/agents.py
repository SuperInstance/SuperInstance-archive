"""
Agent management endpoints.

This module provides endpoints for creating, reading, updating, and managing agents
in the system.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_database_session,
    get_agent_service,
    get_pagination_params,
    get_search_params,
    get_current_user,
    validate_agent_exists,
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
from app.models.agent_model import Agent, AgentStatus, AgentType, AgentCapability
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
    AgentStatusUpdate,
    AgentCapabilitiesUpdate
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse, summary="List agents")
async def list_agents(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: SearchParams = Depends(get_search_params),
    status: Optional[str] = Query(None, description="Filter by agent status"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> PaginatedResponse:
    """
    List agents with pagination and filtering.

    Returns a paginated list of agents with optional filtering by status,
    type, capability, and other parameters.
    """
    try:
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if agent_type:
            filters["agent_type"] = agent_type
        if capability:
            filters["capability"] = capability
        if is_active is not None:
            filters["is_active"] = is_active

        # Get agents
        agents, total = await agent_service.list_agents(
            page=pagination.page,
            size=pagination.size,
            search=search.search,
            sort_by=search.sort_by,
            sort_order=search.sort_order,
            filters=filters
        )

        # Convert to response format
        agent_responses = [AgentResponse.from_orm(agent) for agent in agents]

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
            data=agent_responses,
            pagination=pagination_info
        )

    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise


@router.get("/{agent_id}", response_model=AgentResponse, summary="Get agent")
async def get_agent(
    agent: Dict[str, Any] = Depends(validate_agent_exists),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AgentResponse:
    """
    Get detailed information about a specific agent.

    Returns comprehensive information about the specified agent,
    including configuration, capabilities, and performance metrics.
    """
    try:
        return AgentResponse.from_orm(agent)
    except Exception as e:
        logger.error(f"Error getting agent {agent.id}: {str(e)}")
        raise


@router.post("/", response_model=CreatedResponse, status_code=201, summary="Create agent")
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_database_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> CreatedResponse:
    """
    Create a new agent.

    Creates a new agent with the specified configuration, capabilities,
    and settings. The creator will be set as the owner of the agent.
    """
    try:
        # Create agent
        agent = await agent_service.create_agent(
            agent_data=agent_data,
            created_by=current_user["id"]
        )

        logger.info(f"Created agent {agent.id} by user {current_user['id']}")

        return CreatedResponse(
            message="Agent created successfully",
            data=AgentResponse.from_orm(agent),
            id=str(agent.id)
        )

    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise


@router.put("/{agent_id}", response_model=UpdatedResponse, summary="Update agent")
async def update_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    agent_data: AgentUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> UpdatedResponse:
    """
    Update an existing agent.

    Updates the configuration, capabilities, or settings of an existing agent.
    Only the owner or admins can update agents.
    """
    try:
        # Check permissions
        agent = await agent_service.get_agent_by_id(str(agent_id))
        if not agent:
            raise NotFoundError("Agent not found", resource_type="agent", resource_id=str(agent_id))

        if not _can_update_agent(agent, current_user):
            raise ForbiddenError("You don't have permission to update this agent")

        # Update agent
        updated_agent = await agent_service.update_agent(
            agent_id=str(agent_id),
            agent_data=agent_data
        )

        logger.info(f"Updated agent {agent_id} by user {current_user['id']}")

        return UpdatedResponse(
            message="Agent updated successfully",
            data=AgentResponse.from_orm(updated_agent)
        )

    except (NotFoundError, ForbiddenError):
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {str(e)}")
        raise


@router.delete("/{agent_id}", response_model=DeletedResponse, status_code=204, summary="Delete agent")
async def delete_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> DeletedResponse:
    """
    Delete an agent.

    Soft deletes an agent by marking it as decommissioned.
    Only the owner or admins can delete agents.
    """
    try:
        # Check permissions
        agent = await agent_service.get_agent_by_id(str(agent_id))
        if not agent:
            raise NotFoundError("Agent not found", resource_type="agent", resource_id=str(agent_id))

        if not _can_delete_agent(agent, current_user):
            raise ForbiddenError("You don't have permission to delete this agent")

        # Delete agent
        await agent_service.delete_agent(str(agent_id))

        logger.info(f"Deleted agent {agent_id} by user {current_user['id']}")

        return DeletedResponse(
            message="Agent deleted successfully"
        )

    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {str(e)}")
        raise


@router.post("/{agent_id}/activate", response_model=SuccessResponse, summary="Activate agent")
async def activate_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> SuccessResponse:
    """
    Activate an agent.

    Changes the agent status to active, allowing it to accept and process tasks.
    """
    try:
        await agent_service.activate_agent(str(agent_id))
        logger.info(f"Activated agent {agent_id} by user {current_user['id']}")

        return SuccessResponse(
            message="Agent activated successfully"
        )

    except Exception as e:
        logger.error(f"Error activating agent {agent_id}: {str(e)}")
        raise


@router.post("/{agent_id}/deactivate", response_model=SuccessResponse, summary="Deactivate agent")
async def deactivate_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    reason: Optional[str] = Query(None, description="Reason for deactivation"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> SuccessResponse:
    """
    Deactivate an agent.

    Changes the agent status to idle, preventing it from accepting new tasks.
    """
    try:
        await agent_service.deactivate_agent(str(agent_id), reason)
        logger.info(f"Deactivated agent {agent_id} by user {current_user['id']}, reason: {reason}")

        return SuccessResponse(
            message="Agent deactivated successfully"
        )

    except Exception as e:
        logger.error(f"Error deactivating agent {agent_id}: {str(e)}")
        raise


@router.post("/{agent_id}/heartbeat", response_model=SuccessResponse, summary="Update agent heartbeat")
async def update_heartbeat(
    agent_id: UUID = Path(..., description="Agent ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> SuccessResponse:
    """
    Update agent heartbeat.

    Updates the last heartbeat timestamp for the agent.
    Used by agents to report their status.
    """
    try:
        await agent_service.update_heartbeat(str(agent_id))
        return SuccessResponse(message="Heartbeat updated successfully")
    except Exception as e:
        logger.error(f"Error updating heartbeat for agent {agent_id}: {str(e)}")
        raise


@router.get("/{agent_id}/metrics", summary="Get agent metrics")
async def get_agent_metrics(
    agent_id: UUID = Path(..., description="Agent ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> Dict[str, Any]:
    """
    Get performance metrics for an agent.

    Returns detailed performance metrics including response times,
    success rates, task counts, and health status.
    """
    try:
        metrics = await agent_service.get_agent_metrics(str(agent_id))
        return metrics
    except Exception as e:
        logger.error(f"Error getting metrics for agent {agent_id}: {str(e)}")
        raise


@router.post("/{agent_id}/capabilities", response_model=SuccessResponse, summary="Add capability")
async def add_capability(
    agent_id: UUID = Path(..., description="Agent ID"),
    capability_data: AgentCapabilitiesUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> SuccessResponse:
    """
    Add capabilities to an agent.

    Adds new capabilities to the agent's capability list.
    """
    try:
        await agent_service.add_capabilities(str(agent_id), capability_data.capabilities)
        return SuccessResponse(message="Capabilities added successfully")
    except Exception as e:
        logger.error(f"Error adding capabilities to agent {agent_id}: {str(e)}")
        raise


@router.delete("/{agent_id}/capabilities/{capability}", response_model=SuccessResponse, summary="Remove capability")
async def remove_capability(
    agent_id: UUID = Path(..., description="Agent ID"),
    capability: str = Path(..., description="Capability to remove"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service = Depends(get_agent_service)
) -> SuccessResponse:
    """
    Remove a capability from an agent.

    Removes a specific capability from the agent's capability list.
    """
    try:
        await agent_service.remove_capability(str(agent_id), capability)
        return SuccessResponse(message="Capability removed successfully")
    except Exception as e:
        logger.error(f"Error removing capability from agent {agent_id}: {str(e)}")
        raise


# Helper functions
def _can_update_agent(agent: Any, current_user: Dict[str, Any]) -> bool:
    """Check if user can update the agent."""
    # Admins can update any agent
    if current_user.get("is_admin", False):
        return True

    # Users can update their own agents
    if str(agent.created_by) == current_user["id"]:
        return True

    return False


def _can_delete_agent(agent: Any, current_user: Dict[str, Any]) -> bool:
    """Check if user can delete the agent."""
    # Admins can delete any agent
    if current_user.get("is_admin", False):
        return True

    # Users can delete their own agents
    if str(agent.created_by) == current_user["id"]:
        return True

    return False