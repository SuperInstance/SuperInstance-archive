"""
Exception handling module.

This module provides comprehensive exception handling for the FastAPI application,
including custom exception classes, handlers, and response models.
"""

from app.exceptions.custom import (
    BaseAPIException,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    RateLimitError,
    ServiceUnavailableError,
    DatabaseError,
    ConfigurationError,
    ExternalServiceError,
    AgentError,
    WorkflowError,
    ExecutionError,
    TimeoutError,
    FileSizeExceededError,
    UnsupportedFileTypeError,
    WebSocketError,
)

from app.exceptions.handlers import (
    api_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler,
    setup_exception_handlers,
)

from app.exceptions.models import (
    ErrorDetail,
    ErrorResponse,
    ValidationErrorResponse,
    HealthCheckResponse,
    DetailedHealthCheckResponse,
    PaginationInfo,
    PaginatedResponse,
    SuccessResponse,
    CreatedResponse,
    UpdatedResponse,
    DeletedResponse,
)

__all__ = [
    # Custom exceptions
    "BaseAPIException",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "RateLimitError",
    "ServiceUnavailableError",
    "DatabaseError",
    "ConfigurationError",
    "ExternalServiceError",
    "AgentError",
    "WorkflowError",
    "ExecutionError",
    "TimeoutError",
    "FileSizeExceededError",
    "UnsupportedFileTypeError",
    "WebSocketError",

    # Exception handlers
    "api_exception_handler",
    "validation_exception_handler",
    "http_exception_handler",
    "sqlalchemy_exception_handler",
    "general_exception_handler",
    "setup_exception_handlers",

    # Response models
    "ErrorDetail",
    "ErrorResponse",
    "ValidationErrorResponse",
    "HealthCheckResponse",
    "DetailedHealthCheckResponse",
    "PaginationInfo",
    "PaginatedResponse",
    "SuccessResponse",
    "CreatedResponse",
    "UpdatedResponse",
    "DeletedResponse",
]