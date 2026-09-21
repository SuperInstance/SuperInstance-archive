#!/usr/bin/env python3
"""
Jaeger Tracing Middleware for ActiveLog Services

Provides OpenTracing instrumentation for Python services including:
- Automatic span creation for HTTP requests
- Database query tracing
- External service call tracing
- Custom span annotations
- Correlation ID propagation
- Performance metrics collection
"""

import functools
import logging
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlparse

import opentracing
from jaeger_client import Config
from opentracing.ext import tags
from opentracing.propagation import Format
from flask import Flask, request, g
from aiohttp import web, ClientSession
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JaegerTracingConfig:
    """Jaeger tracing configuration"""
    
    def __init__(self, service_name: str, jaeger_host: str = "localhost", jaeger_port: int = 6831):
        self.service_name = service_name
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        
        # Jaeger configuration
        self.config = {
            'sampler': {
                'type': 'probabilistic',
                'param': 1.0,  # Sample all traces in development
            },
            'reporter': {
                'batch_size': 1,
                'queue_size': 100,
            },
            'logging': True,
            'reporter_batch_size': 1,
            'local_agent': {
                'reporting_host': jaeger_host,
                'reporting_port': jaeger_port,
            },
        }
    
    def initialize_tracer(self):
        """Initialize Jaeger tracer"""
        config = Config(
            config=self.config,
            service_name=self.service_name,
            validate=True,
        )
        
        tracer = config.initialize_tracer()
        opentracing.set_global_tracer(tracer)
        
        logger.info(f"Jaeger tracer initialized for service: {self.service_name}")
        return tracer

class ActiveLogTracer:
    """ActiveLog-specific tracing utilities"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.tracer = opentracing.global_tracer()
    
    def start_span(self, operation_name: str, child_of=None, **kwargs):
        """Start a new span"""
        return self.tracer.start_span(
            operation_name=operation_name,
            child_of=child_of,
            tags={
                tags.COMPONENT: self.service_name,
                **kwargs
            }
        )
    
    def start_child_span(self, parent_span, operation_name: str, **kwargs):
        """Start a child span"""
        return self.tracer.start_span(
            operation_name=operation_name,
            child_of=parent_span,
            tags={
                tags.COMPONENT: self.service_name,
                **kwargs
            }
        )
    
    @contextmanager
    def trace_operation(self, operation_name: str, parent_span=None, **span_tags):
        """Context manager for tracing operations"""
        span = self.start_span(operation_name, child_of=parent_span, **span_tags)
        
        try:
            yield span
        except Exception as e:
            span.set_tag(tags.ERROR, True)
            span.log_kv({
                'event': 'error',
                'error.object': e,
                'error.kind': type(e).__name__,
                'message': str(e),
            })
            raise
        finally:
            span.finish()
    
    def inject_span_context(self, span, carrier):
        """Inject span context into carrier (e.g., HTTP headers)"""
        self.tracer.inject(
            span_context=span.context,
            format=Format.HTTP_HEADERS,
            carrier=carrier
        )
    
    def extract_span_context(self, carrier):
        """Extract span context from carrier"""
        return self.tracer.extract(
            format=Format.HTTP_HEADERS,
            carrier=carrier
        )

class FlaskTracingMiddleware:
    """Flask middleware for automatic request tracing"""
    
    def __init__(self, app: Flask, tracer: ActiveLogTracer):
        self.app = app
        self.tracer = tracer
        self._setup_middleware()
    
    def _setup_middleware(self):
        """Setup Flask middleware hooks"""
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)
        self.app.teardown_request(self._teardown_request)
    
    def _before_request(self):
        """Before request hook - start tracing"""
        # Extract parent span context from headers
        parent_span_ctx = self.tracer.extract_span_context(dict(request.headers))
        
        # Create span for request
        span = self.tracer.start_span(
            operation_name=f"{request.method} {request.endpoint or request.path}",
            child_of=parent_span_ctx,
            **{
                tags.HTTP_METHOD: request.method,
                tags.HTTP_URL: request.url,
                tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER,
                'http.route': request.endpoint or 'unknown',
                'user.id': getattr(request, 'user_id', None),
                'request.id': request.headers.get('X-Request-ID'),
            }
        )
        
        # Store span in request context
        g.current_span = span
        g.request_start_time = time.time()
    
    def _after_request(self, response):
        """After request hook - add response information"""
        if hasattr(g, 'current_span'):
            span = g.current_span
            
            # Add response information
            span.set_tag(tags.HTTP_STATUS_CODE, response.status_code)
            
            if response.status_code >= 400:
                span.set_tag(tags.ERROR, True)
                span.log_kv({
                    'event': 'http_error',
                    'status_code': response.status_code,
                })
            
            # Add timing information
            if hasattr(g, 'request_start_time'):
                duration = time.time() - g.request_start_time
                span.log_kv({
                    'event': 'request_completed',
                    'duration_ms': duration * 1000,
                })
        
        return response
    
    def _teardown_request(self, exception=None):
        """Teardown hook - finish span"""
        if hasattr(g, 'current_span'):
            span = g.current_span
            
            if exception:
                span.set_tag(tags.ERROR, True)
                span.log_kv({
                    'event': 'error',
                    'error.object': exception,
                    'error.kind': type(exception).__name__,
                    'message': str(exception),
                })
            
            span.finish()

class AioHttpTracingMiddleware:
    """aiohttp middleware for automatic request tracing"""
    
    def __init__(self, tracer: ActiveLogTracer):
        self.tracer = tracer
    
    def create_middleware(self):
        """Create aiohttp middleware"""
        @web.middleware
        async def tracing_middleware(request, handler):
            # Extract parent span context
            parent_span_ctx = self.tracer.extract_span_context(dict(request.headers))
            
            # Create span for request
            span = self.tracer.start_span(
                operation_name=f"{request.method} {request.path}",
                child_of=parent_span_ctx,
                **{
                    tags.HTTP_METHOD: request.method,
                    tags.HTTP_URL: str(request.url),
                    tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER,
                    'request.id': request.headers.get('X-Request-ID'),
                }
            )
            
            # Store span in request
            request['tracing_span'] = span
            start_time = time.time()
            
            try:
                response = await handler(request)
                
                # Add response information
                span.set_tag(tags.HTTP_STATUS_CODE, response.status)
                
                if response.status >= 400:
                    span.set_tag(tags.ERROR, True)
                    span.log_kv({
                        'event': 'http_error',
                        'status_code': response.status,
                    })
                
                # Add timing
                duration = time.time() - start_time
                span.log_kv({
                    'event': 'request_completed',
                    'duration_ms': duration * 1000,
                })
                
                return response
                
            except Exception as e:
                span.set_tag(tags.ERROR, True)
                span.log_kv({
                    'event': 'error',
                    'error.object': e,
                    'error.kind': type(e).__name__,
                    'message': str(e),
                })
                raise
            finally:
                span.finish()
        
        return tracing_middleware

class DatabaseTracingMixin:
    """Mixin for tracing database operations"""
    
    def __init__(self, tracer: ActiveLogTracer):
        self.tracer = tracer
    
    def trace_db_operation(self, operation: str, table: str = None, query: str = None):
        """Decorator for tracing database operations"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.tracer.trace_operation(
                    operation_name=f"db.{operation}",
                    **{
                        tags.DATABASE_TYPE: 'postgresql',
                        tags.DATABASE_STATEMENT: query,
                        'db.table': table,
                        'db.operation': operation,
                    }
                ) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.log_kv({'event': 'db.query.success'})
                        return result
                    except Exception as e:
                        span.log_kv({
                            'event': 'db.query.error',
                            'error': str(e)
                        })
                        raise
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.tracer.trace_operation(
                    operation_name=f"db.{operation}",
                    **{
                        tags.DATABASE_TYPE: 'postgresql',
                        tags.DATABASE_STATEMENT: query,
                        'db.table': table,
                        'db.operation': operation,
                    }
                ) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.log_kv({'event': 'db.query.success'})
                        return result
                    except Exception as e:
                        span.log_kv({
                            'event': 'db.query.error',
                            'error': str(e)
                        })
                        raise
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator

class HttpClientTracing:
    """HTTP client tracing utilities"""
    
    def __init__(self, tracer: ActiveLogTracer):
        self.tracer = tracer
    
    async def trace_http_request(self, method: str, url: str, **kwargs):
        """Trace HTTP client request"""
        parsed_url = urlparse(url)
        
        with self.tracer.trace_operation(
            operation_name=f"http.{method.lower()}",
            **{
                tags.HTTP_METHOD: method,
                tags.HTTP_URL: url,
                tags.SPAN_KIND: tags.SPAN_KIND_RPC_CLIENT,
                'http.host': parsed_url.netloc,
                'http.path': parsed_url.path,
            }
        ) as span:
            
            # Inject tracing headers
            headers = kwargs.get('headers', {})
            self.tracer.inject_span_context(span, headers)
            kwargs['headers'] = headers
            
            try:
                async with ClientSession() as session:
                    async with session.request(method, url, **kwargs) as response:
                        span.set_tag(tags.HTTP_STATUS_CODE, response.status)
                        
                        if response.status >= 400:
                            span.set_tag(tags.ERROR, True)
                            span.log_kv({
                                'event': 'http_error',
                                'status_code': response.status,
                            })
                        
                        return response
                        
            except Exception as e:
                span.set_tag(tags.ERROR, True)
                span.log_kv({
                    'event': 'http_error',
                    'error.object': e,
                    'error.kind': type(e).__name__,
                    'message': str(e),
                })
                raise

class BusinessMetricsTracing:
    """Business metrics tracing for ActiveLog"""
    
    def __init__(self, tracer: ActiveLogTracer):
        self.tracer = tracer
    
    def trace_user_action(self, action: str, user_id: str, **metadata):
        """Trace user action"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.tracer.trace_operation(
                    operation_name=f"user.{action}",
                    **{
                        'user.id': user_id,
                        'user.action': action,
                        'business.event': True,
                        **metadata
                    }
                ) as span:
                    result = await func(*args, **kwargs)
                    
                    # Add business context
                    if hasattr(result, 'get'):
                        if 'plan_type' in result:
                            span.set_tag('user.plan_type', result['plan_type'])
                        if 'revenue' in result:
                            span.set_tag('business.revenue', result['revenue'])
                    
                    return result
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.tracer.trace_operation(
                    operation_name=f"user.{action}",
                    **{
                        'user.id': user_id,
                        'user.action': action,
                        'business.event': True,
                        **metadata
                    }
                ) as span:
                    result = func(*args, **kwargs)
                    
                    # Add business context
                    if hasattr(result, 'get'):
                        if 'plan_type' in result:
                            span.set_tag('user.plan_type', result['plan_type'])
                        if 'revenue' in result:
                            span.set_tag('business.revenue', result['revenue'])
                    
                    return result
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def trace_payment_processing(self, payment_method: str, amount: int):
        """Trace payment processing"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                with self.tracer.trace_operation(
                    operation_name="payment.process",
                    **{
                        'payment.method': payment_method,
                        'payment.amount': amount,
                        'business.critical': True,
                        tags.SPAN_KIND: tags.SPAN_KIND_RPC_CLIENT,
                    }
                ) as span:
                    try:
                        result = await func(*args, **kwargs)
                        
                        span.log_kv({
                            'event': 'payment.success',
                            'transaction_id': result.get('transaction_id'),
                        })
                        
                        return result
                    except Exception as e:
                        span.log_kv({
                            'event': 'payment.failed',
                            'error': str(e),
                        })
                        raise
            
            return wrapper
        return decorator

# Factory functions
def create_flask_tracing(app: Flask, service_name: str, jaeger_host: str = "localhost") -> ActiveLogTracer:
    """Create Flask tracing setup"""
    # Initialize Jaeger
    jaeger_config = JaegerTracingConfig(service_name, jaeger_host)
    jaeger_config.initialize_tracer()
    
    # Create tracer
    tracer = ActiveLogTracer(service_name)
    
    # Setup middleware
    FlaskTracingMiddleware(app, tracer)
    
    return tracer

def create_aiohttp_tracing(service_name: str, jaeger_host: str = "localhost") -> tuple:
    """Create aiohttp tracing setup"""
    # Initialize Jaeger
    jaeger_config = JaegerTracingConfig(service_name, jaeger_host)
    jaeger_config.initialize_tracer()
    
    # Create tracer and middleware
    tracer = ActiveLogTracer(service_name)
    middleware = AioHttpTracingMiddleware(tracer)
    
    return tracer, middleware.create_middleware()

# Example usage
if __name__ == "__main__":
    # Example Flask usage
    from flask import Flask
    
    app = Flask(__name__)
    tracer = create_flask_tracing(app, "activelog-api")
    
    @app.route("/users/<user_id>")
    def get_user(user_id):
        # This will be automatically traced
        with tracer.trace_operation("get_user_details") as span:
            span.set_tag("user.id", user_id)
            # Simulate database call
            time.sleep(0.1)
            return {"user_id": user_id, "name": "Test User"}
    
    app.run(debug=True)