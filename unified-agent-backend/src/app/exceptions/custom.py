"""
Custom exception classes for the application.

This module defines custom exception classes that are used throughout the application
to provide consistent error handling and meaningful error messages.
"""

from typing import Any, Dict, Optional


class BaseAPIException(Exception):
    """
    Base exception class for all API exceptions.

    This class provides a common interface for all custom exceptions
    and includes methods for generating standardized error responses.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize base API exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
            headers: Additional response headers
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary representation.

        Returns:
            Dictionary with error information
        """
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationError(BaseAPIException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class NotFoundError(BaseAPIException):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            details=details,
        )


class ConflictError(BaseAPIException):
    """Exception raised when a conflict occurs."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details,
        )


class UnauthorizedError(BaseAPIException):
    """Exception raised for unauthorized access."""

    def __init__(
        self,
        message: str = "Unauthorized",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=401,
            details=details,
        )


class ForbiddenError(BaseAPIException):
    """Exception raised for forbidden access."""

    def __init__(
        self,
        message: str = "Forbidden",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=403,
            details=details,
        )


class RateLimitError(BaseAPIException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> None:
        details = {}
        if limit:
            details["limit"] = limit
        if window:
            details["window_seconds"] = window
        if retry_after:
            details["retry_after_seconds"] = retry_after

        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            headers=headers,
        )


class ServiceUnavailableError(BaseAPIException):
    """Exception raised when a service is unavailable."""

    def __init__(
        self,
        message: str = "Service unavailable",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = {}
        if service_name:
            error_details["service_name"] = service_name
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
            details=error_details,
        )


class DatabaseError(BaseAPIException):
    """Exception raised for database-related errors."""

    def __init__(
        self,
        message: str = "Database error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details,
        )


class ConfigurationError(BaseAPIException):
    """Exception raised for configuration errors."""

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = {}
        if config_key:
            error_details["config_key"] = config_key
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=error_details,
        )


class ExternalServiceError(BaseAPIException):
    """Exception raised for external service errors."""

    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = {}
        if service_name:
            error_details["service_name"] = service_name
        if status_code:
            error_details["status_code"] = status_code
        if response_body:
            error_details["response_body"] = response_body
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=error_details,
        )


class AgentError(BaseAPIException):
    """Exception raised for agent-related errors."""

    def __init__(
        self,
        message: str = "Agent error",
        agent_id: Optional[str] = None,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = {}
        if agent_id:
            error_details["agent_id"] = agent_id
        if error_type:
            error_details["error_type"] = error_type
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            error_code="AGENT_ERROR",
            status_code=500,
            details=error_details,
        )


class WorkflowError(BaseAPIException):
    """Exception raised for workflow-related errors."""

    def __init__(
        self,
        message: str = "Workflow error",
        workflow_id: Optional[str] = None,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = {}
        if workflow_id:
            error_details["workflow_id"] = workflow_id
        if error_type:
            error_details["error_type"] = error_type
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            error_code="WORKFLOW_ERROR",
            status_code=500,
            details=error_details,
        )


class ExecutionError(BaseAPIException):
    """Exception raised for execution-related errors."""

    def __init__(
        self,
        message: str = "Execution error",
        execution_id: Optional[str] = None,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = {}
        if execution_id:
            error_details["execution_id"] = execution_id
        if error_type:
            error_details["error_type"] = error_type
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            error_code="EXECUTION_ERROR",
            status_code=500,
            details=error_details,
        )


class TimeoutError(BaseAPIException):
    """Exception raised when an operation times out."""

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[int] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = {}
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds
        if operation:
            error_details["operation"] = operation
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            error_code="TIMEOUT",
            status_code=504,
            details=error_details,
        )


class FileSizeExceededError(BaseAPIException):
    """Exception raised when file size exceeds limits."""

    def __init__(
        self,
        message: str = "File size exceeded",
        file_size: Optional[int] = None,
        max_size: Optional[int] = None,
        filename: Optional[str] = None,
    ) -> None:
        details = {}
        if file_size:
            details["file_size_bytes"] = file_size
        if max_size:
            details["max_size_bytes"] = max_size
        if filename:
            details["filename"] = filename

        super().__init__(
            message=message,
            error_code="FILE_SIZE_EXCEEDED",
            status_code=413,
            details=details,
        )


class UnsupportedFileTypeError(BaseAPIException):
    """Exception raised for unsupported file types."""

    def __init__(
        self,
        message: str = "Unsupported file type",
        file_type: Optional[str] = None,
        allowed_types: Optional[list] = None,
        filename: Optional[str] = None,
    ) -> None:
        details = {}
        if file_type:
            details["file_type"] = file_type
        if allowed_types:
            details["allowed_types"] = allowed_types
        if filename:
            details["filename"] = filename

        super().__init__(
            message=message,
            error_code="UNSUPPORTED_FILE_TYPE",
            status_code=415,
            details=details,
        )


class WebSocketError(BaseAPIException):
    """Exception raised for WebSocket-related errors."""

    def __init__(
        self,
        message: str = "WebSocket error",
        connection_id: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = {}
        if connection_id:
            error_details["connection_id"] = connection_id
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            error_code=error_code or "WEBSOCKET_ERROR",
            status_code=400,
            details=error_details,
        )