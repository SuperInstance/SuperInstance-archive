"""
Request ID middleware.

This module provides middleware for adding unique request IDs to HTTP requests
to help with tracing and debugging.
"""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Request ID middleware.

    This middleware adds a unique request ID to each incoming request
    and includes it in response headers for tracing and debugging.
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID",
        generator: Callable = None,
        trust_incoming: bool = True,
    ) -> None:
        """
        Initialize request ID middleware.

        Args:
            app: ASGI application
            header_name: Name of the request ID header
            generator: Function to generate request IDs (defaults to UUID4)
            trust_incoming: Whether to trust incoming request ID headers
        """
        super().__init__(app)
        self.header_name = header_name
        self.generator = generator or (lambda: str(uuid.uuid4()))
        self.trust_incoming = trust_incoming

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add request ID.

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response with request ID header
        """
        # Get existing request ID from headers or generate new one
        request_id = self._get_or_generate_request_id(request)

        # Store request ID in request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        return response

    def _get_or_generate_request_id(self, request: Request) -> str:
        """
        Get existing request ID from headers or generate new one.

        Args:
            request: FastAPI request object

        Returns:
            Request ID string
        """
        if self.trust_incoming:
            # Try to get request ID from incoming headers
            incoming_request_id = request.headers.get(self.header_name)
            if incoming_request_id and self._is_valid_request_id(incoming_request_id):
                return incoming_request_id

        # Generate new request ID
        return self.generator()

    def _is_valid_request_id(self, request_id: str) -> bool:
        """
        Validate request ID format.

        Args:
            request_id: Request ID string to validate

        Returns:
            True if request ID is valid
        """
        # Basic validation - should be a non-empty string
        if not request_id or not isinstance(request_id, str):
            return False

        # Length check (reasonable limits)
        if len(request_id) < 1 or len(request_id) > 100:
            return False

        # You could add more specific validation here if needed
        # For example, checking for specific formats like UUID

        return True