"""
ActiveLog Plugin SDK - Decorators for Python
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints
from .types import PluginError, ValidationError


def api_endpoint(path: str, method: str = "GET", description: Optional[str] = None):
    """Decorator to mark a method as an API endpoint"""
    def decorator(func: Callable) -> Callable:
        func._api_endpoint = {
            'path': path,
            'method': method.upper(),
            'description': description
        }
        return func
    return decorator


def trigger_handler(trigger_type: str, description: Optional[str] = None):
    """Decorator to mark a method as a trigger handler"""
    def decorator(func: Callable) -> Callable:
        func._trigger_handler = {
            'type': trigger_type,
            'description': description
        }
        return func
    return decorator


def validate_params(**param_schemas: Dict[str, Any]):
    """Decorator to validate function parameters against schemas"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get type hints for validation
            type_hints = get_type_hints(func)
            
            # Validate each parameter
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for param_name, value in bound_args.arguments.items():
                if param_name in param_schemas:
                    schema = param_schemas[param_name]
                    if not _validate_value(value, schema):
                        raise ValidationError(param_name, f"Value {value} does not match schema {schema}")
            
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def requires_permission(permission: str):
    """Decorator to require specific permissions for a method"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            context = self._get_context()
            
            # Check if plugin has required permission
            if not _has_permission(context, permission):
                raise PermissionError(permission)
            
            if asyncio.iscoroutinefunction(func):
                return await func(self, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


def rate_limit(calls_per_minute: int = 60):
    """Decorator to rate limit method calls"""
    def decorator(func: Callable) -> Callable:
        call_times = []
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            now = time.time()
            
            # Remove calls older than 1 minute
            call_times[:] = [t for t in call_times if now - t < 60]
            
            if len(call_times) >= calls_per_minute:
                raise PluginError(
                    f"Rate limit exceeded: {calls_per_minute} calls per minute",
                    "RATE_LIMIT_EXCEEDED"
                )
            
            call_times.append(now)
            
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def cache(ttl: int = 300, key_func: Optional[Callable] = None):
    """Decorator to cache method results"""
    def decorator(func: Callable) -> Callable:
        cache_data = {}
        
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            import time
            import hashlib
            import json
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_data = {
                    'func': func.__name__,
                    'args': str(args[1:]),  # Skip self
                    'kwargs': json.dumps(kwargs, sort_keys=True)
                }
                cache_key = hashlib.md5(json.dumps(key_data).encode()).hexdigest()
            
            now = time.time()
            
            # Check cache
            if cache_key in cache_data:
                cached_value, timestamp = cache_data[cache_key]
                if now - timestamp < ttl:
                    return cached_value
            
            # Call function and cache result
            if asyncio.iscoroutinefunction(func):
                result = await func(self, *args, **kwargs)
            else:
                result = func(self, *args, **kwargs)
            
            cache_data[cache_key] = (result, now)
            return result
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry failed method calls"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise e
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator


def measure_performance(track_memory: bool = False):
    """Decorator to measure method performance"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            import time
            import tracemalloc
            
            start_time = time.time()
            
            if track_memory:
                tracemalloc.start()
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(self, *args, **kwargs)
                else:
                    result = func(self, *args, **kwargs)
                
                end_time = time.time()
                duration = end_time - start_time
                
                metrics = {
                    'function': func.__name__,
                    'duration': duration,
                    'success': True
                }
                
                if track_memory and tracemalloc.is_tracing():
                    current, peak = tracemalloc.get_traced_memory()
                    metrics.update({
                        'memory_current': current,
                        'memory_peak': peak
                    })
                    tracemalloc.stop()
                
                # Log performance metrics
                self.emit_event('performance_metrics', metrics)
                
                return result
                
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                
                self.emit_event('performance_metrics', {
                    'function': func.__name__,
                    'duration': duration,
                    'success': False,
                    'error': str(e)
                })
                
                if track_memory and tracemalloc.is_tracing():
                    tracemalloc.stop()
                
                raise
        
        return wrapper
    return decorator


def config_required(*config_keys: str):
    """Decorator to ensure required configuration keys are present"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            config = self.get_config()
            
            missing_keys = []
            for key in config_keys:
                if key not in config:
                    missing_keys.append(key)
            
            if missing_keys:
                raise PluginError(
                    f"Missing required configuration keys: {', '.join(missing_keys)}",
                    "MISSING_CONFIG"
                )
            
            if asyncio.iscoroutinefunction(func):
                return await func(self, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


def event_listener(event_name: str):
    """Decorator to register a method as an event listener"""
    def decorator(func: Callable) -> Callable:
        func._event_listener = {
            'event': event_name
        }
        return func
    return decorator


def scheduled_task(schedule: str):
    """Decorator to mark a method as a scheduled task"""
    def decorator(func: Callable) -> Callable:
        func._scheduled_task = {
            'schedule': schedule
        }
        return func
    return decorator


def webhook_handler(path: str, methods: Optional[List[str]] = None):
    """Decorator to register a webhook handler"""
    def decorator(func: Callable) -> Callable:
        func._webhook_handler = {
            'path': path,
            'methods': methods or ['POST']
        }
        return func
    return decorator


# Helper functions
def _validate_value(value: Any, schema: Dict[str, Any]) -> bool:
    """Basic schema validation - in production, use jsonschema"""
    if 'type' in schema:
        expected_type = schema['type']
        if expected_type == 'string' and not isinstance(value, str):
            return False
        elif expected_type == 'number' and not isinstance(value, (int, float)):
            return False
        elif expected_type == 'boolean' and not isinstance(value, bool):
            return False
        elif expected_type == 'array' and not isinstance(value, list):
            return False
        elif expected_type == 'object' and not isinstance(value, dict):
            return False
    
    if 'required' in schema and schema['required'] and value is None:
        return False
    
    if 'minLength' in schema and isinstance(value, str) and len(value) < schema['minLength']:
        return False
    
    if 'maxLength' in schema and isinstance(value, str) and len(value) > schema['maxLength']:
        return False
    
    return True


def _has_permission(context, permission: str) -> bool:
    """Check if the plugin context has the required permission"""
    # This would integrate with the actual permission system
    # For now, we'll do a basic check against the manifest permissions
    manifest = context.manifest
    permissions = manifest.permissions
    
    if permission.startswith('network'):
        return permissions.network and permissions.network.enabled
    elif permission.startswith('database'):
        action = permission.split(':')[1] if ':' in permission else 'read'
        return getattr(permissions.database, action, False) if permissions.database else False
    elif permission.startswith('filesystem'):
        action = permission.split(':')[1] if ':' in permission else 'read'
        return bool(getattr(permissions.filesystem, action, [])) if permissions.filesystem else False
    
    return False