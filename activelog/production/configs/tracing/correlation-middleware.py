"""
Correlation ID and Distributed Tracing Middleware for ActiveLog Production

This middleware ensures all requests have correlation IDs and implements
comprehensive distributed tracing across all services.
"""

import uuid
import time
import logging
import json
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from threading import local
import asyncio
from functools import wraps

# Thread-local storage for correlation context
_context = local()

class CorrelationContext:
    """Manages correlation IDs and tracing context across service calls."""
    
    def __init__(self):
        self.correlation_id: Optional[str] = None
        self.trace_id: Optional[str] = None
        self.span_id: Optional[str] = None
        self.parent_span_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.request_start_time: Optional[float] = None
        self.service_name: str = "unknown"
        self.operation_name: str = "unknown"
        self.tags: Dict[str, Any] = {}
        self.baggage: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging/transmission."""
        return {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_start_time": self.request_start_time,
            "service_name": self.service_name,
            "operation_name": self.operation_name,
            "tags": self.tags,
            "baggage": self.baggage,
        }

    def to_headers(self) -> Dict[str, str]:
        """Convert context to HTTP headers for service-to-service calls."""
        headers = {}
        if self.correlation_id:
            headers["X-Correlation-ID"] = self.correlation_id
        if self.trace_id:
            headers["X-Trace-ID"] = self.trace_id
        if self.span_id:
            headers["X-Span-ID"] = self.span_id
        if self.parent_span_id:
            headers["X-Parent-Span-ID"] = self.parent_span_id
        if self.user_id:
            headers["X-User-ID"] = self.user_id
        if self.session_id:
            headers["X-Session-ID"] = self.session_id
        
        # Add baggage as headers
        for key, value in self.baggage.items():
            headers[f"X-Baggage-{key}"] = value
            
        return headers

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "CorrelationContext":
        """Create context from HTTP headers."""
        context = cls()
        
        # Standard tracing headers
        context.correlation_id = headers.get("X-Correlation-ID") or headers.get("x-correlation-id")
        context.trace_id = headers.get("X-Trace-ID") or headers.get("x-trace-id")
        context.span_id = headers.get("X-Span-ID") or headers.get("x-span-id") 
        context.parent_span_id = headers.get("X-Parent-Span-ID") or headers.get("x-parent-span-id")
        context.user_id = headers.get("X-User-ID") or headers.get("x-user-id")
        context.session_id = headers.get("X-Session-ID") or headers.get("x-session-id")
        
        # Extract baggage
        for key, value in headers.items():
            if key.lower().startswith("x-baggage-"):
                baggage_key = key[10:].lower()  # Remove "x-baggage-" prefix
                context.baggage[baggage_key] = value
        
        return context


def get_correlation_context() -> Optional[CorrelationContext]:
    """Get current correlation context from thread-local storage."""
    return getattr(_context, "correlation_context", None)


def set_correlation_context(context: CorrelationContext) -> None:
    """Set correlation context in thread-local storage."""
    _context.correlation_context = context


@contextmanager
def correlation_context(context: CorrelationContext):
    """Context manager for setting correlation context."""
    old_context = get_correlation_context()
    set_correlation_context(context)
    try:
        yield context
    finally:
        set_correlation_context(old_context)


def generate_correlation_id() -> str:
    """Generate a new UUID v4 correlation ID."""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate a new span ID."""
    return uuid.uuid4().hex[:16]


def extract_user_info(request) -> tuple:
    """Extract user and session information from request."""
    user_id = None
    session_id = None
    
    # Try to extract from JWT token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            import jwt
            token = auth_header[7:]
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub") or payload.get("user_id")
            session_id = payload.get("session_id")
        except Exception:
            pass
    
    # Fallback to headers
    user_id = user_id or request.headers.get("X-User-ID")
    session_id = session_id or request.headers.get("X-Session-ID")
    
    return user_id, session_id


class CorrelationMiddleware:
    """Flask/FastAPI middleware for correlation ID and distributed tracing."""
    
    def __init__(self, app=None, service_name: str = "unknown"):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{service_name}.tracing")
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        if hasattr(app, "before_request"):
            # Flask
            app.before_request(self.before_request)
            app.after_request(self.after_request)
        else:
            # FastAPI or other ASGI
            app.middleware("http")(self.asgi_middleware)
    
    def before_request(self):
        """Flask before_request handler."""
        from flask import request, g
        
        # Create context from headers
        context = CorrelationContext.from_headers(dict(request.headers))
        
        # Generate IDs if missing
        if not context.correlation_id:
            context.correlation_id = generate_correlation_id()
        
        if not context.trace_id:
            context.trace_id = context.correlation_id.split("-")[0]
            
        if not context.span_id:
            context.span_id = generate_span_id()
        
        # Extract user information
        context.user_id, context.session_id = extract_user_info(request)
        
        # Set service and operation info
        context.service_name = self.service_name
        context.operation_name = f"{request.method} {request.path}"
        context.request_start_time = time.time()
        
        # Add request tags
        context.tags.update({
            "http.method": request.method,
            "http.url": request.url,
            "http.path": request.path,
            "http.user_agent": request.headers.get("User-Agent", ""),
            "client.ip": request.remote_addr or request.headers.get("X-Forwarded-For", ""),
        })
        
        # Store in Flask's g and thread-local
        g.correlation_context = context
        set_correlation_context(context)
        
        # Log request start
        self.logger.info("Request started", extra={
            "event": "request_start",
            "correlation_id": context.correlation_id,
            "trace_id": context.trace_id,
            "span_id": context.span_id,
            "operation": context.operation_name,
            "tags": context.tags
        })
    
    def after_request(self, response):
        """Flask after_request handler."""
        from flask import g
        
        context = getattr(g, "correlation_context", None)
        if not context:
            return response
        
        # Calculate response time
        response_time = time.time() - context.request_start_time
        
        # Add response headers
        response.headers["X-Correlation-ID"] = context.correlation_id
        response.headers["X-Trace-ID"] = context.trace_id
        response.headers["X-Span-ID"] = context.span_id
        response.headers["X-Response-Time"] = str(int(response_time * 1000))
        
        # Log request completion
        self.logger.info("Request completed", extra={
            "event": "request_complete",
            "correlation_id": context.correlation_id,
            "trace_id": context.trace_id,
            "span_id": context.span_id,
            "operation": context.operation_name,
            "response_time_ms": int(response_time * 1000),
            "status_code": response.status_code,
            "tags": context.tags
        })
        
        return response
    
    async def asgi_middleware(self, request, call_next):
        """ASGI middleware for FastAPI."""
        # Create context from headers
        context = CorrelationContext.from_headers(dict(request.headers))
        
        # Generate IDs if missing
        if not context.correlation_id:
            context.correlation_id = generate_correlation_id()
        
        if not context.trace_id:
            context.trace_id = context.correlation_id.split("-")[0]
            
        if not context.span_id:
            context.span_id = generate_span_id()
        
        # Extract user information
        context.user_id, context.session_id = extract_user_info(request)
        
        # Set service and operation info
        context.service_name = self.service_name
        context.operation_name = f"{request.method} {request.url.path}"
        context.request_start_time = time.time()
        
        # Add request tags
        context.tags.update({
            "http.method": request.method,
            "http.url": str(request.url),
            "http.path": request.url.path,
            "http.user_agent": request.headers.get("user-agent", ""),
            "client.ip": request.client.host if request.client else "",
        })
        
        # Set context
        set_correlation_context(context)
        
        # Log request start
        self.logger.info("Request started", extra={
            "event": "request_start",
            "correlation_id": context.correlation_id,
            "trace_id": context.trace_id,
            "span_id": context.span_id,
            "operation": context.operation_name,
            "tags": context.tags
        })
        
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - context.request_start_time
            
            # Add response headers
            response.headers["X-Correlation-ID"] = context.correlation_id
            response.headers["X-Trace-ID"] = context.trace_id
            response.headers["X-Span-ID"] = context.span_id
            response.headers["X-Response-Time"] = str(int(response_time * 1000))
            
            # Log request completion
            self.logger.info("Request completed", extra={
                "event": "request_complete",
                "correlation_id": context.correlation_id,
                "trace_id": context.trace_id,
                "span_id": context.span_id,
                "operation": context.operation_name,
                "response_time_ms": int(response_time * 1000),
                "status_code": response.status_code,
                "tags": context.tags
            })
            
            return response
            
        except Exception as e:
            # Log error with context
            self.logger.error("Request failed", extra={
                "event": "request_error",
                "correlation_id": context.correlation_id,
                "trace_id": context.trace_id,
                "span_id": context.span_id,
                "operation": context.operation_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "tags": context.tags
            })
            raise


def trace_function(operation_name: str = None):
    """Decorator to trace function calls with span information."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = get_correlation_context()
            if not context:
                return func(*args, **kwargs)
            
            # Create child span
            parent_span_id = context.span_id
            span_id = generate_span_id()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            logger = logging.getLogger(f"{context.service_name}.tracing")
            
            # Log span start
            logger.debug("Span started", extra={
                "event": "span_start",
                "correlation_id": context.correlation_id,
                "trace_id": context.trace_id,
                "span_id": span_id,
                "parent_span_id": parent_span_id,
                "operation": op_name,
                "function": func.__name__,
                "module": func.__module__
            })
            
            start_time = time.time()
            
            try:
                # Update context for this span
                old_span_id = context.span_id
                old_parent_span_id = context.parent_span_id
                old_operation_name = context.operation_name
                
                context.span_id = span_id
                context.parent_span_id = parent_span_id
                context.operation_name = op_name
                
                result = func(*args, **kwargs)
                
                # Log span completion
                duration = time.time() - start_time
                logger.debug("Span completed", extra={
                    "event": "span_complete",
                    "correlation_id": context.correlation_id,
                    "trace_id": context.trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "operation": op_name,
                    "duration_ms": int(duration * 1000),
                    "function": func.__name__
                })
                
                return result
                
            except Exception as e:
                # Log span error
                duration = time.time() - start_time
                logger.error("Span failed", extra={
                    "event": "span_error",
                    "correlation_id": context.correlation_id,
                    "trace_id": context.trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "operation": op_name,
                    "duration_ms": int(duration * 1000),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__
                })
                raise
            finally:
                # Restore context
                context.span_id = old_span_id
                context.parent_span_id = old_parent_span_id
                context.operation_name = old_operation_name
        
        return wrapper
    return decorator


async def trace_async_function(operation_name: str = None):
    """Decorator to trace async function calls with span information."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = get_correlation_context()
            if not context:
                return await func(*args, **kwargs)
            
            # Create child span
            parent_span_id = context.span_id
            span_id = generate_span_id()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            logger = logging.getLogger(f"{context.service_name}.tracing")
            
            # Log span start
            logger.debug("Async span started", extra={
                "event": "async_span_start",
                "correlation_id": context.correlation_id,
                "trace_id": context.trace_id,
                "span_id": span_id,
                "parent_span_id": parent_span_id,
                "operation": op_name,
                "function": func.__name__,
                "module": func.__module__
            })
            
            start_time = time.time()
            
            try:
                # Update context for this span
                old_span_id = context.span_id
                old_parent_span_id = context.parent_span_id
                old_operation_name = context.operation_name
                
                context.span_id = span_id
                context.parent_span_id = parent_span_id
                context.operation_name = op_name
                
                result = await func(*args, **kwargs)
                
                # Log span completion
                duration = time.time() - start_time
                logger.debug("Async span completed", extra={
                    "event": "async_span_complete",
                    "correlation_id": context.correlation_id,
                    "trace_id": context.trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "operation": op_name,
                    "duration_ms": int(duration * 1000),
                    "function": func.__name__
                })
                
                return result
                
            except Exception as e:
                # Log span error
                duration = time.time() - start_time
                logger.error("Async span failed", extra={
                    "event": "async_span_error",
                    "correlation_id": context.correlation_id,
                    "trace_id": context.trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "operation": op_name,
                    "duration_ms": int(duration * 1000),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__
                })
                raise
            finally:
                # Restore context
                context.span_id = old_span_id
                context.parent_span_id = old_parent_span_id
                context.operation_name = old_operation_name
        
        return wrapper
    return decorator


class TracingHTTPClient:
    """HTTP client that propagates correlation context to downstream services."""
    
    def __init__(self, base_url: str = "", timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        import requests
        self.session = requests.Session()
    
    def _add_tracing_headers(self, headers: Dict[str, str] = None) -> Dict[str, str]:
        """Add tracing headers to outgoing requests."""
        if headers is None:
            headers = {}
        
        context = get_correlation_context()
        if context:
            headers.update(context.to_headers())
        
        return headers
    
    def get(self, url: str, headers: Dict[str, str] = None, **kwargs):
        """GET request with tracing headers."""
        headers = self._add_tracing_headers(headers)
        return self.session.get(f"{self.base_url}{url}", headers=headers, timeout=self.timeout, **kwargs)
    
    def post(self, url: str, headers: Dict[str, str] = None, **kwargs):
        """POST request with tracing headers."""
        headers = self._add_tracing_headers(headers)
        return self.session.post(f"{self.base_url}{url}", headers=headers, timeout=self.timeout, **kwargs)
    
    def put(self, url: str, headers: Dict[str, str] = None, **kwargs):
        """PUT request with tracing headers."""
        headers = self._add_tracing_headers(headers)
        return self.session.put(f"{self.base_url}{url}", headers=headers, timeout=self.timeout, **kwargs)
    
    def delete(self, url: str, headers: Dict[str, str] = None, **kwargs):
        """DELETE request with tracing headers."""
        headers = self._add_tracing_headers(headers)
        return self.session.delete(f"{self.base_url}{url}", headers=headers, timeout=self.timeout, **kwargs)


# Configure structured logging with correlation context
class CorrelationFormatter(logging.Formatter):
    """Custom formatter that includes correlation context in log records."""
    
    def format(self, record):
        # Add correlation context to log record
        context = get_correlation_context()
        if context:
            record.correlation_id = context.correlation_id
            record.trace_id = context.trace_id
            record.span_id = context.span_id
            record.parent_span_id = context.parent_span_id
            record.user_id = context.user_id
            record.session_id = context.session_id
            record.service_name = context.service_name
            record.operation_name = context.operation_name
        else:
            record.correlation_id = None
            record.trace_id = None
            record.span_id = None
            record.parent_span_id = None
            record.user_id = None
            record.session_id = None
            record.service_name = "unknown"
            record.operation_name = "unknown"
        
        return super().format(record)


def setup_correlation_logging(service_name: str, log_level: str = "INFO"):
    """Setup structured logging with correlation context."""
    
    # Create JSON formatter with correlation fields
    json_formatter = CorrelationFormatter(json.dumps({
        "timestamp": "%(asctime)s",
        "level": "%(levelname)s",
        "service": "%(service_name)s",
        "operation": "%(operation_name)s",
        "correlation_id": "%(correlation_id)s",
        "trace_id": "%(trace_id)s",
        "span_id": "%(span_id)s",
        "parent_span_id": "%(parent_span_id)s",
        "user_id": "%(user_id)s",
        "session_id": "%(session_id)s",
        "logger": "%(name)s",
        "message": "%(message)s",
        "module": "%(module)s",
        "function": "%(funcName)s",
        "line": "%(lineno)d",
        "thread": "%(thread)d",
        "process": "%(process)d"
    }))
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)
    
    # Service-specific logger
    service_logger = logging.getLogger(service_name)
    service_logger.setLevel(getattr(logging, log_level.upper()))
    
    return service_logger