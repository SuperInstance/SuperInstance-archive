"""
Dependency injection for FastAPI application.

This module provides dependency functions for database sessions, authentication,
services, pagination, and other commonly used dependencies.
"""

from typing import AsyncGenerator, Optional, Type, TypeVar, Generic, Dict, Any

from fastapi import Depends, HTTPException, Query, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import get_settings
from app.core.logging import get_logger
from app.db import get_db_session
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.services.workflow_executor import WorkflowExecutor
from app.repositories.agent_repository import AgentRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.repositories.base import BaseRepository
from app.exceptions import UnauthorizedError, ForbiddenError, NotFoundError

logger = get_logger(__name__)

# Generic type for repositories
ModelType = TypeVar("ModelType", bound=BaseRepository)

# Security scheme for Bearer token authentication
security = HTTPBearer(auto_error=False)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.

    Yields:
        AsyncSession: Database session
    """
    async for session in get_db_session():
        yield session


async def get_settings_dependency() -> "Settings":
    """
    Get application settings dependency.

    Returns:
        Settings: Application settings
    """
    return get_settings()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user from token (optional).

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        User information or None if not authenticated

    Raises:
        UnauthorizedError: If token is invalid
    """
    if not credentials:
        return None

    try:
        # TODO: Implement actual JWT token validation
        # This is a placeholder implementation
        user_info = await _validate_token(credentials.credentials)
        return user_info

    except Exception as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise UnauthorizedError("Invalid authentication token")


async def get_current_user(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get current user (required authentication).

    Args:
        current_user: Optional current user from previous dependency

    Returns:
        User information

    Raises:
        UnauthorizedError: If user is not authenticated
    """
    if not current_user:
        raise UnauthorizedError("Authentication required")

    return current_user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current active user.

    Args:
        current_user: Current user

    Returns:
        Active user information

    Raises:
        ForbiddenError: If user is not active
    """
    if not current_user.get("is_active", False):
        raise ForbiddenError("User account is not active")

    return current_user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get current admin user.

    Args:
        current_user: Current active user

    Returns:
        Admin user information

    Raises:
        ForbiddenError: If user is not an admin
    """
    if not current_user.get("is_admin", False):
        raise ForbiddenError("Admin access required")

    return current_user


def get_repository(RepositoryClass: Type[ModelType]) -> callable:
    """
    Factory function to create repository dependencies.

    Args:
        RepositoryClass: Repository class to instantiate

    Returns:
        Dependency function that returns repository instance
    """
    async def _get_repository(
        db: AsyncSession = Depends(get_database_session)
    ) -> ModelType:
        """Get repository instance."""
        return RepositoryClass(db)

    return _get_repository


# Specific repository dependencies
get_agent_repository = get_repository(AgentRepository)
get_workflow_repository = get_repository(WorkflowRepository)


# Service dependencies
async def get_agent_service(
    db: AsyncSession = Depends(get_database_session),
    agent_repo: AgentRepository = Depends(get_agent_repository)
) -> AgentService:
    """
    Get agent service dependency.

    Args:
        db: Database session
        agent_repo: Agent repository

    Returns:
        AgentService instance
    """
    return AgentService(db, agent_repo)


async def get_workflow_service(
    db: AsyncSession = Depends(get_database_session),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    agent_service: AgentService = Depends(get_agent_service)
) -> WorkflowService:
    """
    Get workflow service dependency.

    Args:
        db: Database session
        workflow_repo: Workflow repository
        agent_service: Agent service

    Returns:
        WorkflowService instance
    """
    return WorkflowService(db, workflow_repo, agent_service)


async def get_workflow_executor(
    workflow_service: WorkflowService = Depends(get_workflow_service),
    agent_service: AgentService = Depends(get_agent_service)
) -> WorkflowExecutor:
    """
    Get workflow executor dependency.

    Args:
        workflow_service: Workflow service
        agent_service: Agent service

    Returns:
        WorkflowExecutor instance
    """
    return WorkflowExecutor(workflow_service, agent_service)


# Pagination dependencies
class PaginationParams:
    """Pagination parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        size: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    ) -> None:
        self.page = page
        self.size = size
        self.offset = (page - 1) * size

    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.size


async def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
) -> PaginationParams:
    """
    Get pagination parameters.

    Args:
        page: Page number
        size: Page size

    Returns:
        PaginationParams instance
    """
    return PaginationParams(page=page, size=size)


# Filter dependencies
class SearchParams:
    """Search parameters."""

    def __init__(
        self,
        search: Optional[str] = Query(None, description="Search query"),
        sort_by: Optional[str] = Query(None, description="Sort field"),
        sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    ) -> None:
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() == "desc"


async def get_search_params(
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort order"),
) -> SearchParams:
    """
    Get search parameters.

    Args:
        search: Search query
        sort_by: Sort field
        sort_order: Sort order

    Returns:
        SearchParams instance
    """
    return SearchParams(search=search, sort_by=sort_by, sort_order=sort_order)


# Resource validation dependencies
async def validate_agent_exists(
    agent_id: str,
    agent_repo: AgentRepository = Depends(get_agent_repository)
) -> Dict[str, Any]:
    """
    Validate that an agent exists.

    Args:
        agent_id: Agent ID
        agent_repo: Agent repository

    Returns:
        Agent data

    Raises:
        NotFoundError: If agent does not exist
    """
    agent = await agent_repo.get_by_id(agent_id)
    if not agent:
        raise NotFoundError(f"Agent not found", resource_type="agent", resource_id=agent_id)

    return agent


async def validate_workflow_exists(
    workflow_id: str,
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository)
) -> Dict[str, Any]:
    """
    Validate that a workflow exists.

    Args:
        workflow_id: Workflow ID
        workflow_repo: Workflow repository

    Returns:
        Workflow data

    Raises:
        NotFoundError: If workflow does not exist
    """
    workflow = await workflow_repo.get_by_id(workflow_id)
    if not workflow:
        raise NotFoundError(f"Workflow not found", resource_type="workflow", resource_id=workflow_id)

    return workflow


# Helper functions
async def _validate_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token and return user information.

    Args:
        token: JWT token string

    Returns:
        User information dictionary

    Raises:
        UnauthorizedError: If token is invalid
    """
    # TODO: Implement actual JWT token validation
    # This is a placeholder implementation that should be replaced
    # with proper JWT validation using your preferred library

    settings = get_settings()

    # For now, just return a mock user for development
    if settings.is_development:
        return {
            "id": "dev-user-id",
            "email": "dev@example.com",
            "is_active": True,
            "is_admin": True,
        }

    # In production, implement proper JWT validation
    raise UnauthorizedError("Token validation not implemented")


# Rate limiting dependencies
async def check_rate_limit(
    request,  # FastAPI Request object
    limit: int = 100,
    window: int = 60,
) -> None:
    """
    Check rate limit for a request.

    Args:
        request: FastAPI request object
        limit: Number of requests allowed
        window: Time window in seconds

    Raises:
        RateLimitError: If rate limit is exceeded
    """
    # TODO: Implement actual rate limiting logic
    # This would typically involve Redis or similar storage
    pass