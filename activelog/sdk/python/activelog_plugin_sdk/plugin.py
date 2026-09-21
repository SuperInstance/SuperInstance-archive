"""
ActiveLog Plugin SDK - Base Plugin Class for Python
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime

from .types import (
    PluginInterface,
    PluginContext,
    PluginManifest,
    TriggerEvent,
    TriggerResult,
    UserContext,
    OrganizationContext,
    FileEvent,
    PluginError,
)


class Plugin(PluginInterface):
    """
    Base Plugin class that all Python plugins should inherit from
    """

    def __init__(self):
        self._context: Optional[PluginContext] = None
        self._is_active = False
        self._is_loaded = False
        self._logger = logging.getLogger(self.__class__.__name__)

    def _set_context(self, context: PluginContext) -> None:
        """Internal method to set the plugin context"""
        self._context = context

    def _get_context(self) -> PluginContext:
        """Get the current plugin context"""
        if not self._context:
            raise PluginError("Plugin context not available. Plugin may not be loaded.")
        return self._context

    @property
    def is_active(self) -> bool:
        """Check if the plugin is currently active"""
        return self._is_active

    @property
    def is_loaded(self) -> bool:
        """Check if the plugin is currently loaded"""
        return self._is_loaded

    # Plugin lifecycle methods - override as needed

    async def on_load(self, context: PluginContext) -> None:
        """Called when the plugin is first loaded"""
        self._context = context
        self._is_loaded = True
        self.log('info', 'Plugin loaded')

    async def on_activate(self, context: PluginContext) -> None:
        """Called when the plugin is activated"""
        self._is_active = True
        self.log('info', 'Plugin activated')

    async def on_deactivate(self, context: PluginContext) -> None:
        """Called when the plugin is deactivated"""
        self._is_active = False
        self.log('info', 'Plugin deactivated')

    async def on_unload(self, context: PluginContext) -> None:
        """Called when the plugin is unloaded"""
        self._is_loaded = False
        self._is_active = False
        self.log('info', 'Plugin unloaded')

    async def on_config_change(self, config: Dict[str, Any], context: PluginContext) -> None:
        """Called when configuration changes"""
        self.log('info', f'Configuration changed: {config}')

    async def on_trigger(self, event: TriggerEvent, context: PluginContext) -> TriggerResult:
        """Called when a trigger event occurs"""
        self.log('info', f'Trigger event received: {event.type}')
        return TriggerResult(success=True)

    async def handle_api(self, path: str, method: str, data: Any, context: PluginContext) -> Any:
        """Called for API endpoint handlers"""
        raise PluginError(f"API endpoint not implemented: {method} {path}")

    # Utility methods for plugin developers

    def log(self, level: str, message: str, *args: Any) -> None:
        """Log a message using the plugin logger"""
        context = self._get_context()
        logger = context.logger

        if level == 'debug':
            logger.debug(message, *args)
        elif level == 'info':
            logger.info(message, *args)
        elif level == 'warn':
            logger.warn(message, *args)
        elif level == 'error':
            error = args[0] if args and isinstance(args[0], Exception) else None
            logger.error(message, error, *args[1:] if len(args) > 1 else [])

    def get_config(self, key: Optional[str] = None) -> Any:
        """Get plugin configuration"""
        context = self._get_context()
        if key:
            return context.config.get(key)
        return context.config

    async def set_storage(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store data in plugin storage"""
        context = self._get_context()
        await context.storage.set(key, value, ttl)

    async def get_storage(self, key: str) -> Any:
        """Retrieve data from plugin storage"""
        context = self._get_context()
        return await context.storage.get(key)

    async def delete_storage(self, key: str) -> None:
        """Delete data from plugin storage"""
        context = self._get_context()
        await context.storage.delete(key)

    async def http_request(
        self,
        method: str,
        url: str,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """Make an HTTP request"""
        context = self._get_context()
        http = context.http

        options = {
            'headers': headers or {},
            'timeout': timeout
        }

        if method.upper() == 'GET':
            return await http.get(url, options)
        elif method.upper() == 'POST':
            return await http.post(url, data, options)
        elif method.upper() == 'PUT':
            return await http.put(url, data, options)
        elif method.upper() == 'DELETE':
            return await http.delete(url, options)
        elif method.upper() == 'PATCH':
            return await http.patch(url, data, options)
        else:
            raise PluginError(f"Unsupported HTTP method: {method}")

    async def db_query(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        """Query the database"""
        context = self._get_context()
        return await context.database.query(sql, params)

    def get_current_user(self) -> UserContext:
        """Get current user context"""
        context = self._get_context()
        return context.user

    def get_organization(self) -> OrganizationContext:
        """Get organization context"""
        context = self._get_context()
        return context.organization

    def emit_event(self, event: str, *args: Any) -> None:
        """Emit an event"""
        context = self._get_context()
        context.events.emit(event, *args)

    def on_event(self, event: str, listener: Callable[..., None]) -> None:
        """Listen to an event"""
        context = self._get_context()
        context.events.on(event, listener)

    def off_event(self, event: str, listener: Callable[..., None]) -> None:
        """Remove event listener"""
        context = self._get_context()
        context.events.off(event, listener)

    async def send_notification(
        self,
        type: str,
        recipient: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send a notification"""
        context = self._get_context()
        from .types import NotificationRequest
        
        notification = NotificationRequest(
            type=type,
            recipient=recipient,
            title=title,
            message=message,
            data=data or {}
        )
        
        return await context.services.notifications.send(notification)

    async def track_event(self, event: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Track an analytics event"""
        context = self._get_context()
        await context.services.analytics.track(event, properties)

    async def search_files(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Any:
        """Search files and metadata"""
        context = self._get_context()
        return await context.services.metadata.search(query, filters)

    async def watch_files(
        self,
        path: str,
        callback: Callable[[FileEvent], Awaitable[None]]
    ) -> str:
        """Watch for file changes"""
        context = self._get_context()
        return await context.services.file_sync.watch(path, callback)

    async def unwatch_files(self, watch_id: str) -> None:
        """Stop watching files"""
        context = self._get_context()
        await context.services.file_sync.unwatch(watch_id)

    def validate_config(self, config: Any) -> bool:
        """Validate plugin configuration against schema"""
        manifest = self.get_manifest()
        if not manifest.config or not manifest.config.schema:
            return True

        try:
            # Basic validation - in a real implementation, use jsonschema
            # import jsonschema
            # jsonschema.validate(config, manifest.config.schema)
            return True
        except Exception as error:
            self.log('error', 'Configuration validation failed', error)
            return False

    def schedule_task(
        self,
        name: str,
        schedule: str,
        task: Callable[[], Awaitable[None]]
    ) -> None:
        """Schedule a recurring task"""
        # This would integrate with the plugin runtime's scheduler
        self.log('info', f'Scheduling task: {name} with schedule: {schedule}')

    def cancel_task(self, name: str) -> None:
        """Cancel a scheduled task"""
        self.log('info', f'Canceling task: {name}')

    def get_plugin_info(self) -> Dict[str, Any]:
        """Get plugin metadata"""
        context = self._get_context()
        manifest = self.get_manifest()
        
        return {
            'name': manifest.name,
            'version': manifest.version,
            'display_name': manifest.display_name,
            'description': manifest.description,
            'author': manifest.author,
            'is_active': self._is_active,
            'is_loaded': self._is_loaded,
            'config': context.config
        }

    # Async context manager support
    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._is_loaded:
            if self._context:
                await self.on_unload(self._context)

    # Helper methods for common patterns

    async def run_with_retry(
        self,
        func: Callable[[], Awaitable[Any]],
        max_retries: int = 3,
        delay: float = 1.0
    ) -> Any:
        """Run a function with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries:
                    raise
                self.log('warn', f'Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}')
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

    async def batch_process(
        self,
        items: List[Any],
        processor: Callable[[Any], Awaitable[Any]],
        batch_size: int = 10,
        max_concurrent: int = 3
    ) -> List[Any]:
        """Process items in batches with concurrency control"""
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_item(item):
            async with semaphore:
                return await processor(item)
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_tasks = [process_item(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    self.log('error', f'Failed to process item {i + j}', result)
                else:
                    results.append(result)
        
        return results

    async def cache_with_ttl(
        self,
        key: str,
        func: Callable[[], Awaitable[Any]],
        ttl: int = 300
    ) -> Any:
        """Cache function result with TTL"""
        # Check cache first
        cached_value = await self.get_storage(f"cache:{key}")
        if cached_value is not None:
            return cached_value
        
        # Compute and cache
        value = await func()
        await self.set_storage(f"cache:{key}", value, ttl)
        return value

    def create_webhook_handler(
        self,
        path: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> None:
        """Register a webhook handler"""
        # This would register the handler with the plugin runtime
        self.log('info', f'Registering webhook handler for path: {path}')

    async def make_authenticated_request(
        self,
        method: str,
        url: str,
        data: Optional[Any] = None,
        use_user_token: bool = True
    ) -> Any:
        """Make an authenticated HTTP request"""
        headers = {}
        
        if use_user_token:
            # In a real implementation, get the user's auth token
            # headers['Authorization'] = f'Bearer {user_token}'
            pass
        
        return await self.http_request(method, url, data, headers)

    async def process_file_upload(
        self,
        file_path: str,
        processor: Callable[[str], Awaitable[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Process an uploaded file with error handling"""
        try:
            self.log('info', f'Processing uploaded file: {file_path}')
            
            # Process the file
            result = await processor(file_path)
            
            # Track the event
            await self.track_event('file_processed', {
                'file_path': file_path,
                'success': True,
                'plugin': self.get_manifest().name
            })
            
            return result
            
        except Exception as e:
            self.log('error', f'Failed to process file: {file_path}', e)
            
            await self.track_event('file_processed', {
                'file_path': file_path,
                'success': False,
                'error': str(e),
                'plugin': self.get_manifest().name
            })
            
            raise

    def create_progress_tracker(self) -> 'ProgressTracker':
        """Create a progress tracker for long-running operations"""
        return ProgressTracker(self)


class ProgressTracker:
    """Helper class for tracking operation progress"""
    
    def __init__(self, plugin: Plugin):
        self.plugin = plugin
        self.total = 0
        self.current = 0
        self.status = "idle"
        self.start_time: Optional[datetime] = None
    
    def start(self, total: int, status: str = "processing") -> None:
        """Start progress tracking"""
        self.total = total
        self.current = 0
        self.status = status
        self.start_time = datetime.utcnow()
        
        self.plugin.emit_event('progress:start', {
            'total': total,
            'status': status
        })
    
    def update(self, current: int, status: Optional[str] = None) -> None:
        """Update progress"""
        self.current = current
        if status:
            self.status = status
            
        progress_percent = (current / self.total * 100) if self.total > 0 else 0
        
        self.plugin.emit_event('progress:update', {
            'current': current,
            'total': self.total,
            'percent': progress_percent,
            'status': self.status
        })
    
    def complete(self, status: str = "completed") -> None:
        """Mark progress as complete"""
        self.current = self.total
        self.status = status
        
        duration = None
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        self.plugin.emit_event('progress:complete', {
            'total': self.total,
            'status': status,
            'duration': duration
        })
    
    def fail(self, error: str, status: str = "failed") -> None:
        """Mark progress as failed"""
        self.status = status
        
        self.plugin.emit_event('progress:failed', {
            'current': self.current,
            'total': self.total,
            'status': status,
            'error': error
        })