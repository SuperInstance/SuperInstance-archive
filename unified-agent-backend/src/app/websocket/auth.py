"""
WebSocket authentication utilities.

This module provides authentication and authorization for WebSocket connections,
including token validation, user verification, and permission checking.
"""

import json
from typing import Dict, Any, Optional

from app.core.logging import get_logger
from app.exceptions import UnauthorizedError, ForbiddenError

logger = get_logger(__name__)


class WebSocketAuth:
    """
    Handles WebSocket authentication and authorization.

    Provides methods for validating authentication tokens, checking user permissions,
    and managing WebSocket security.
    """

    def __init__(self):
        """Initialize WebSocket authentication handler."""
        # In a real implementation, you might inject JWT handlers, user services, etc.
        pass

    async def authenticate_connection(
        self,
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        query_params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a WebSocket connection.

        Args:
            token: JWT authentication token
            api_key: API key for authentication
            query_params: WebSocket query parameters
            headers: WebSocket headers

        Returns:
            User information dict if authentication succeeds, None otherwise

        Raises:
            UnauthorizedError: If authentication fails
        """
        try:
            # Try different authentication methods in order of preference

            # 1. JWT Token (from query params or headers)
            if token:
                user_info = await self._validate_jwt_token(token)
                if user_info:
                    return user_info

            # 2. API Key (from query params or headers)
            if api_key:
                user_info = await self._validate_api_key(api_key)
                if user_info:
                    return user_info

            # 3. Check query params for auth info
            if query_params:
                token_param = query_params.get("token")
                api_key_param = query_params.get("api_key")
                user_id_param = query_params.get("user_id")

                if token_param:
                    user_info = await self._validate_jwt_token(token_param)
                    if user_info:
                        return user_info

                if api_key_param:
                    user_info = await self._validate_api_key(api_key_param)
                    if user_info:
                        return user_info

                # For development, allow user_id param (should be removed in production)
                if user_id_param and self._is_development_mode():
                    return {
                        "id": user_id_param,
                        "email": f"{user_id_param}@dev.local",
                        "is_active": True,
                        "is_admin": False,
                        "auth_method": "dev_param"
                    }

            # 4. Check headers for auth info
            if headers:
                auth_header = headers.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    user_info = await self._validate_jwt_token(token)
                    if user_info:
                        return user_info

                api_key_header = headers.get("x-api-key")
                if api_key_header:
                    user_info = await self._validate_api_key(api_key_header)
                    if user_info:
                        return user_info

            # No valid authentication found
            return None

        except Exception as e:
            logger.warning(f"Authentication error: {str(e)}")
            raise UnauthorizedError(f"Authentication failed: {str(e)}")

    async def authorize_subscription(
        self,
        user_info: Dict[str, Any],
        room_id: str,
        room_type: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Authorize a user to subscribe to a specific room.

        Args:
            user_info: User information from authentication
            room_id: Room ID to subscribe to
            room_type: Type of room
            resource_id: Optional resource ID (execution_id, agent_id, etc.)

        Returns:
            bool: True if user is authorized to subscribe

        Raises:
            ForbiddenError: If user is not authorized
        """
        try:
            user_id = user_info.get("id")
            is_admin = user_info.get("is_admin", False)

            # Admins can subscribe to any room
            if is_admin:
                return True

            # Check authorization based on room type
            if room_type == "execution":
                return await self._authorize_execution_subscription(user_id, resource_id)
            elif room_type == "agent":
                return await self._authorize_agent_subscription(user_id, resource_id)
            elif room_type == "workflow":
                return await self._authorize_workflow_subscription(user_id, resource_id)
            elif room_type == "user":
                return await self._authorize_user_subscription(user_id, resource_id)
            elif room_type == "global":
                # Global rooms are typically open to all authenticated users
                return True
            else:
                # Unknown room type - deny by default
                logger.warning(f"Unknown room type for authorization: {room_type}")
                return False

        except Exception as e:
            logger.error(f"Authorization error for room {room_id}: {str(e)}")
            return False

    async def _validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and return user information.

        Args:
            token: JWT token string

        Returns:
            User information dictionary or None if invalid

        Raises:
            UnauthorizedError: If token is invalid
        """
        # TODO: Implement actual JWT token validation
        # This is a placeholder implementation

        try:
            # In development mode, accept any token and return a mock user
            if self._is_development_mode():
                return {
                    "id": "dev-user-id",
                    "email": "dev@example.com",
                    "is_active": True,
                    "is_admin": True,
                    "auth_method": "dev_jwt"
                }

            # In production, implement proper JWT validation
            # Example using python-jose:
            # from jose import JWTError, jwt
            #
            # try:
            #     payload = jwt.decode(
            #         token,
            #         settings.SECRET_KEY,
            #         algorithms=[settings.ALGORITHM]
            #     )
            #     user_id = payload.get("sub")
            #     if user_id is None:
            #         return None
            #
            #     # Fetch user from database and return info
            #     return await self._get_user_info(user_id)
            #
            # except JWTError:
            #     return None

            raise UnauthorizedError("JWT validation not implemented")

        except Exception as e:
            logger.warning(f"JWT validation failed: {str(e)}")
            return None

    async def _validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return user information.

        Args:
            api_key: API key string

        Returns:
            User information dictionary or None if invalid
        """
        # TODO: Implement actual API key validation
        # This is a placeholder implementation

        try:
            # In development mode, accept any API key
            if self._is_development_mode():
                return {
                    "id": "dev-api-user",
                    "email": "api@example.com",
                    "is_active": True,
                    "is_admin": False,
                    "auth_method": "dev_api_key"
                }

            # In production, implement proper API key validation
            # Example:
            # api_key_record = await self.api_key_service.validate_key(api_key)
            # if api_key_record:
            #     return await self._get_user_info(api_key_record.user_id)
            # return None

            return None

        except Exception as e:
            logger.warning(f"API key validation failed: {str(e)}")
            return None

    async def _authorize_execution_subscription(
        self,
        user_id: str,
        execution_id: Optional[str]
    ) -> bool:
        """
        Authorize user to subscribe to execution updates.

        Args:
            user_id: User ID
            execution_id: Execution ID

        Returns:
            bool: True if authorized
        """
        if not execution_id:
            return False

        # TODO: Implement actual authorization logic
        # Check if user owns the execution or has access to the workflow
        # Example:
        # execution = await self.execution_service.get_execution(execution_id)
        # if not execution:
        #     return False
        # return execution.user_id == user_id or \
        #        await self.workflow_service.has_user_access(execution.workflow_id, user_id)

        # For now, allow all authenticated users in development
        return self._is_development_mode()

    async def _authorize_agent_subscription(
        self,
        user_id: str,
        agent_id: Optional[str]
    ) -> bool:
        """
        Authorize user to subscribe to agent updates.

        Args:
            user_id: User ID
            agent_id: Agent ID

        Returns:
            bool: True if authorized
        """
        if not agent_id:
            return False

        # TODO: Implement actual authorization logic
        # Check if user owns the agent or has permission to monitor it
        # Example:
        # agent = await self.agent_service.get_agent(agent_id)
        # if not agent:
        #     return False
        # return agent.owner_id == user_id or \
        #        await self.agent_service.has_user_permission(agent_id, user_id, "read")

        # For now, allow all authenticated users in development
        return self._is_development_mode()

    async def _authorize_workflow_subscription(
        self,
        user_id: str,
        workflow_id: Optional[str]
    ) -> bool:
        """
        Authorize user to subscribe to workflow updates.

        Args:
            user_id: User ID
            workflow_id: Workflow ID

        Returns:
            bool: True if authorized
        """
        if not workflow_id:
            return False

        # TODO: Implement actual authorization logic
        # Check if user owns the workflow or has access to it
        # Example:
        # workflow = await self.workflow_service.get_workflow(workflow_id)
        # if not workflow:
        #     return False
        # return workflow.owner_id == user_id or \
        #        await self.workflow_service.has_user_access(workflow_id, user_id)

        # For now, allow all authenticated users in development
        return self._is_development_mode()

    async def _authorize_user_subscription(
        self,
        user_id: str,
        target_user_id: Optional[str]
    ) -> bool:
        """
        Authorize user to subscribe to user-specific updates.

        Args:
            user_id: Current user ID
            target_user_id: Target user ID for updates

        Returns:
            bool: True if authorized
        """
        # Users can only subscribe to their own user updates
        return user_id == target_user_id

    def _is_development_mode(self) -> bool:
        """
        Check if the application is in development mode.

        Returns:
            bool: True if in development mode
        """
        # TODO: Implement actual development mode check
        # Example: return settings.is_development
        return True

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from user ID.

        Args:
            user_id: User ID

        Returns:
            User information dictionary or None if not found
        """
        # TODO: Implement actual user lookup
        # This would typically query your user service or database
        # Example:
        # user = await self.user_service.get_user(user_id)
        # if user:
        #     return {
        #         "id": user.id,
        #         "email": user.email,
        #         "is_active": user.is_active,
        #         "is_admin": user.is_admin,
        #         "roles": [role.name for role in user.roles]
        #     }
        # return None

        # Mock implementation for development
        if self._is_development_mode():
            return {
                "id": user_id,
                "email": f"{user_id}@example.com",
                "is_active": True,
                "is_admin": False,
                "roles": ["user"]
            }

        return None