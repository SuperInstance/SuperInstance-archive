"""
Request logging middleware.

This module provides middleware for logging HTTP requests and responses,
including request timing, status codes, and other relevant information.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    This middleware logs detailed information about each request and response,
    including timing, status codes, request IDs, and other relevant data.
    """

    def __init__(
        self,
        app: ASGIApp,
        log_requests: bool = True,
        log_responses: bool = True,
        skip_paths: list = None,
        log_body: bool = False,
    ) -> None:
        """
        Initialize request logging middleware.

        Args:
            app: ASGI application
            log_requests: Whether to log requests
            log_responses: Whether to log responses
            skip_paths: List of paths to skip logging
            log_body: Whether to log request/response body
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.skip_paths = set(skip_paths or [])
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log information.

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response from next middleware
        """
        # Skip logging for specified paths
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # Generate request ID if not already present
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Record start time
        start_time = time.time()

        # Log request
        if self.log_requests:
            await self._log_request(request, request_id)

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            logger.error(
                f"Request processing error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": self._get_client_ip(request),
                },
                exc_info=True,
            )
            raise

        # Calculate processing time
        process_time = time.time() - start_time

        # Add timing information to response headers
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        response.headers["X-Request-ID"] = request_id

        # Log response
        if self.log_responses:
            await self._log_response(request, response, request_id, process_time)

        return response

    async def _log_request(self, request: Request, request_id: str) -> None:
        """
        Log request information.

        Args:
            request: FastAPI request object
            request_id: Unique request identifier
        """
        # Prepare log data
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
        }

        # Add request body if enabled and available
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body and len(body) < 10000:  # Limit body size for logging
                    log_data["request_body"] = body.decode("utf-8", errors="ignore")
            except Exception:
                # Don't fail logging if body reading fails
                pass

        # Log request
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra=log_data,
        )

    async def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        process_time: float,
    ) -> None:
        """
        Log response information.

        Args:
            request: FastAPI request object
            response: FastAPI response object
            request_id: Unique request identifier
            process_time: Request processing time in seconds
        """
        # Prepare log data
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "response_size": response.headers.get("content-length"),
            "content_type": response.headers.get("content-type"),
        }

        # Determine log level based on status code
        status_code = response.status_code
        if status_code >= 500:
            log_level = "error"
        elif status_code >= 400:
            log_level = "warning"
        else:
            log_level = "info"

        # Log response
        getattr(logger, log_level)(
            f"Request completed: {request.method} {request.url.path} - "
            f"{status_code} in {log_data['process_time_ms']}ms",
            extra=log_data,
        )

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to client IP
        return request.client.host if request.client else "unknown"