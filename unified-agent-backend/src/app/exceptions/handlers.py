"""
Exception handlers for FastAPI application.

This module provides exception handlers that convert various types of exceptions
into standardized HTTP responses with proper error formatting and logging.
"""

import logging
import traceback
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.core.logging import get_logger
from app.exceptions.custom import (
    BaseAPIException,
    ValidationError,
    DatabaseError,
    NotFoundError,
)

logger = get_logger(__name__)


async def api_exception_handler(
    request: Request, exc: BaseAPIException
) -> JSONResponse:
    """
    Handler for custom API exceptions.

    Args:
        request: FastAPI request object
        exc: BaseAPIException instance

    Returns:
        JSONResponse with standardized error format
    """
    # Log the error
    logger.error(
        f"API Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True if exc.status_code >= 500 else False,
    )

    # Prepare error response
    error_response = {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
        "path": request.url.path,
        "method": request.method,
        "timestamp": logger.get_timestamp() if hasattr(logger, 'get_timestamp') else None,
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for FastAPI validation exceptions.

    Args:
        request: FastAPI request object
        exc: RequestValidationError instance

    Returns:
        JSONResponse with validation error details
    """
    # Format validation errors
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        })

    error_message = "Validation failed"
    if errors:
        error_message += f" for field(s): {', '.join(error['field'] for error in errors)}"

    logger.warning(
        f"Validation error: {error_message}",
        extra={
            "errors": errors,
            "path": request.url.path,
            "method": request.method,
        },
    )

    error_response = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": error_message,
            "details": {
                "validation_errors": errors,
            },
        },
        "path": request.url.path,
        "method": request.method,
        "timestamp": logger.get_timestamp() if hasattr(logger, 'get_timestamp') else None,
    }

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handler for HTTP exceptions.

    Args:
        request: FastAPI request object
        exc: StarletteHTTPException instance

    Returns:
        JSONResponse with HTTP error details
    """
    logger.warning(
        f"HTTP error: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    error_response = {
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail or "HTTP error occurred",
        },
        "path": request.url.path,
        "method": request.method,
        "timestamp": logger.get_timestamp() if hasattr(logger, 'get_timestamp') else None,
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Handler for SQLAlchemy exceptions.

    Args:
        request: FastAPI request object
        exc: SQLAlchemyError instance

    Returns:
        JSONResponse with database error details
    """
    # Log the full error for debugging
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    # Handle specific database errors
    if isinstance(exc, IntegrityError):
        error_message = "Database integrity constraint violation"
        error_code = "INTEGRITY_ERROR"
        status_code = status.HTTP_409_CONFLICT
    else:
        error_message = "Database operation failed"
        error_code = "DATABASE_ERROR"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    error_response = {
        "error": {
            "code": error_code,
            "message": error_message,
        },
        "path": request.url.path,
        "method": request.method,
        "timestamp": logger.get_timestamp() if hasattr(logger, 'get_timestamp') else None,
    }

    return JSONResponse(
        status_code=status_code,
        content=error_response,
    )


async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handler for all other unhandled exceptions.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSONResponse with generic error details
    """
    # Log the full error for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    # Don't expose internal error details in production
    from app.core.config.settings import get_settings
    settings = get_settings()

    if settings.is_production:
        error_message = "An internal server error occurred"
        error_details = {}
    else:
        error_message = f"Internal server error: {str(exc)}"
        error_details = {
            "error_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        }

    error_response = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": error_message,
            "details": error_details,
        },
        "path": request.url.path,
        "method": request.method,
        "timestamp": logger.get_timestamp() if hasattr(logger, 'get_timestamp') else None,
    }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Custom API exceptions
    app.add_exception_handler(BaseAPIException, api_exception_handler)

    # FastAPI/Starlette built-in exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Database exceptions
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # Catch-all handler for any other exceptions
    app.add_exception_handler(Exception, general_exception_handler)