"""
Lazy loading optimizations for ActiveLog.
Implements efficient lazy loading patterns for large datasets and related objects.
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable, AsyncIterator, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import weakref
import logging
from functools import wraps, lru_cache
import json

logger = logging.getLogger(__name__)


@dataclass
class LazyField:
    """Represents a lazily loaded field."""
    loader: Callable
    loaded: bool = False
    value: Any = None
    error: Optional[Exception] = None


class LazyLoadingMixin:
    """Mixin class to add lazy loading capabilities to data models."""
    
    def __init__(self):
        self._lazy_fields: Dict[str, LazyField] = {}
        self._loading_locks: Dict[str, asyncio.Lock] = {}
    
    def add_lazy_field(self, field_name: str, loader: Callable):
        """Add a lazy field to the object."""
        self._lazy_fields[field_name] = LazyField(loader=loader)
        self._loading_locks[field_name] = asyncio.Lock()
    
    async def load_field(self, field_name: str) -> Any:
        """Load a specific lazy field."""
        if field_name not in self._lazy_fields:
            raise AttributeError(f"No lazy field named '{field_name}'")
        
        lazy_field = self._lazy_fields[field_name]
        
        if lazy_field.loaded:
            if lazy_field.error:
                raise lazy_field.error
            return lazy_field.value
        
        async with self._loading_locks[field_name]:
            # Double-check after acquiring lock
            if lazy_field.loaded:
                if lazy_field.error:
                    raise lazy_field.error
                return lazy_field.value
            
            try:
                lazy_field.value = await lazy_field.loader()
                lazy_field.loaded = True
                logger.debug(f"Lazy loaded field: {field_name}")
                return lazy_field.value
            except Exception as e:
                lazy_field.error = e
                lazy_field.loaded = True
                logger.error(f"Failed to lazy load field {field_name}: {e}")
                raise
    
    async def load_all_fields(self):
        """Load all lazy fields concurrently."""
        tasks = []
        for field_name in self._lazy_fields:
            if not self._lazy_fields[field_name].loaded:
                tasks.append(self.load_field(field_name))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def is_field_loaded(self, field_name: str) -> bool:
        """Check if a lazy field is loaded."""
        return self._lazy_fields.get(field_name, LazyField(None)).loaded


class LazyFile(LazyLoadingMixin):
    """File model with lazy loading capabilities."""
    
    def __init__(self, file_data: Dict[str, Any], db_connection):
        super().__init__()
        self.id = file_data['id']
        self.name = file_data['name']
        self.user_id = file_data['user_id']
        self.size = file_data['size']
        self.content_type = file_data['content_type']
        self.created_at = file_data['created_at']
        self.updated_at = file_data['updated_at']
        
        self._db_connection = db_connection
        
        # Set up lazy fields
        self.add_lazy_field('metadata', self._load_metadata)
        self.add_lazy_field('versions', self._load_versions)
        self.add_lazy_field('shares', self._load_shares)
        self.add_lazy_field('ai_analysis', self._load_ai_analysis)
        self.add_lazy_field('content_preview', self._load_content_preview)
        self.add_lazy_field('access_logs', self._load_access_logs)
    
    async def _load_metadata(self) -> Optional[Dict[str, Any]]:
        """Lazy load file metadata."""
        query = "SELECT metadata FROM file_metadata WHERE file_id = $1"
        row = await self._db_connection.fetchrow(query, self.id)
        return row['metadata'] if row else None
    
    async def _load_versions(self) -> List[Dict[str, Any]]:
        """Lazy load file versions."""
        query = """
            SELECT id, version_number, size, checksum, created_at, created_by
            FROM file_versions 
            WHERE file_id = $1 
            ORDER BY version_number DESC
        """
        rows = await self._db_connection.fetch(query, self.id)
        return [dict(row) for row in rows]
    
    async def _load_shares(self) -> List[Dict[str, Any]]:
        """Lazy load file shares."""
        query = """
            SELECT fs.*, u.name as shared_with_name
            FROM file_shares fs
            LEFT JOIN users u ON fs.shared_with = u.id
            WHERE fs.file_id = $1 AND fs.deleted_at IS NULL
            ORDER BY fs.created_at DESC
        """
        rows = await self._db_connection.fetch(query, self.id)
        return [dict(row) for row in rows]
    
    async def _load_ai_analysis(self) -> List[Dict[str, Any]]:
        """Lazy load AI analysis results."""
        query = """
            SELECT analysis_type, result, confidence, created_at
            FROM ai_analysis 
            WHERE file_id = $1 AND status = 'completed'
            ORDER BY created_at DESC
        """
        rows = await self._db_connection.fetch(query, self.id)
        return [dict(row) for row in rows]
    
    async def _load_content_preview(self) -> Optional[str]:
        """Lazy load content preview for text files."""
        if not self.content_type.startswith('text/'):
            return None
        
        # This would typically load from object storage
        # For now, return a placeholder
        return f"Preview of {self.name} (first 1000 chars)"
    
    async def _load_access_logs(self) -> List[Dict[str, Any]]:
        """Lazy load recent access logs."""
        query = """
            SELECT al.action, al.created_at, u.name as user_name
            FROM activity_logs al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE al.resource_id = $1 
              AND al.resource_type = 'file'
              AND al.created_at > NOW() - INTERVAL '30 days'
            ORDER BY al.created_at DESC
            LIMIT 50
        """
        rows = await self._db_connection.fetch(query, self.id)
        return [dict(row) for row in rows]
    
    async def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Get file metadata (lazy loaded)."""
        return await self.load_field('metadata')
    
    async def get_versions(self) -> List[Dict[str, Any]]:
        """Get file versions (lazy loaded)."""
        return await self.load_field('versions')
    
    async def get_shares(self) -> List[Dict[str, Any]]:
        """Get file shares (lazy loaded)."""
        return await self.load_field('shares')
    
    async def get_ai_analysis(self) -> List[Dict[str, Any]]:
        """Get AI analysis (lazy loaded)."""
        return await self.load_field('ai_analysis')


class LazyUser(LazyLoadingMixin):
    """User model with lazy loading capabilities."""
    
    def __init__(self, user_data: Dict[str, Any], db_connection):
        super().__init__()
        self.id = user_data['id']
        self.email = user_data['email']
        self.name = user_data['name']
        self.created_at = user_data['created_at']
        self.updated_at = user_data['updated_at']
        
        self._db_connection = db_connection
        
        # Set up lazy fields
        self.add_lazy_field('preferences', self._load_preferences)
        self.add_lazy_field('storage_stats', self._load_storage_stats)
        self.add_lazy_field('recent_files', self._load_recent_files)
        self.add_lazy_field('shared_files', self._load_shared_files)
        self.add_lazy_field('activity_summary', self._load_activity_summary)
    
    async def _load_preferences(self) -> Dict[str, Any]:
        """Lazy load user preferences."""
        query = "SELECT preferences FROM user_preferences WHERE user_id = $1"
        row = await self._db_connection.fetchrow(query, self.id)
        return row['preferences'] if row else {}
    
    async def _load_storage_stats(self) -> Dict[str, Any]:
        """Lazy load user storage statistics."""
        query = """
            SELECT 
                COUNT(*) as total_files,
                SUM(size) as total_size,
                COUNT(DISTINCT content_type) as file_types,
                MAX(updated_at) as last_activity
            FROM files 
            WHERE user_id = $1 AND deleted_at IS NULL
        """
        row = await self._db_connection.fetchrow(query, self.id)
        return dict(row) if row else {}
    
    async def _load_recent_files(self) -> List[Dict[str, Any]]:
        """Lazy load recent files."""
        query = """
            SELECT id, name, size, content_type, updated_at
            FROM files 
            WHERE user_id = $1 AND deleted_at IS NULL
            ORDER BY updated_at DESC 
            LIMIT 10
        """
        rows = await self._db_connection.fetch(query, self.id)
        return [dict(row) for row in rows]
    
    async def _load_shared_files(self) -> List[Dict[str, Any]]:
        """Lazy load files shared with this user."""
        query = """
            SELECT f.id, f.name, f.size, fs.permissions, 
                   u.name as shared_by_name, fs.created_at as shared_at
            FROM file_shares fs
            JOIN files f ON fs.file_id = f.id
            JOIN users u ON fs.shared_by = u.id
            WHERE fs.shared_with = $1 AND fs.deleted_at IS NULL
            ORDER BY fs.created_at DESC
            LIMIT 20
        """
        rows = await self._db_connection.fetch(query, self.id)
        return [dict(row) for row in rows]
    
    async def _load_activity_summary(self) -> Dict[str, Any]:
        """Lazy load user activity summary."""
        query = """
            SELECT 
                action,
                COUNT(*) as count,
                MAX(created_at) as last_occurrence
            FROM activity_logs 
            WHERE user_id = $1 
              AND created_at > NOW() - INTERVAL '7 days'
            GROUP BY action
            ORDER BY count DESC
        """
        rows = await self._db_connection.fetch(query, self.id)
        return {row['action']: {'count': row['count'], 'last': row['last_occurrence']} 
                for row in rows}


class LazyCollection:
    """Collection with lazy loading and pagination support."""
    
    def __init__(
        self,
        loader: Callable,
        total_count_loader: Optional[Callable] = None,
        page_size: int = 50
    ):
        self.loader = loader
        self.total_count_loader = total_count_loader
        self.page_size = page_size
        self._pages: Dict[int, List[Any]] = {}
        self._total_count: Optional[int] = None
        self._loading_locks: Dict[int, asyncio.Lock] = {}
    
    async def get_page(self, page: int) -> List[Any]:
        """Get a specific page of data."""
        if page in self._pages:
            return self._pages[page]
        
        if page not in self._loading_locks:
            self._loading_locks[page] = asyncio.Lock()
        
        async with self._loading_locks[page]:
            # Double-check after acquiring lock
            if page in self._pages:
                return self._pages[page]
            
            offset = page * self.page_size
            items = await self.loader(limit=self.page_size, offset=offset)
            self._pages[page] = items
            logger.debug(f"Lazy loaded page {page} with {len(items)} items")
            return items
    
    async def get_total_count(self) -> int:
        """Get total count of items."""
        if self._total_count is not None:
            return self._total_count
        
        if self.total_count_loader:
            self._total_count = await self.total_count_loader()
        else:
            # Estimate based on loaded pages
            max_page = max(self._pages.keys()) if self._pages else 0
            items_in_last_page = len(self._pages.get(max_page, []))
            self._total_count = max_page * self.page_size + items_in_last_page
        
        return self._total_count
    
    async def iterate_all(self) -> AsyncIterator[Any]:
        """Iterate through all items lazily."""
        page = 0
        while True:
            items = await self.get_page(page)
            if not items:
                break
            
            for item in items:
                yield item
            
            if len(items) < self.page_size:
                break
            
            page += 1
    
    async def preload_pages(self, start_page: int = 0, num_pages: int = 3):
        """Preload multiple pages concurrently."""
        tasks = []
        for page in range(start_page, start_page + num_pages):
            if page not in self._pages:
                tasks.append(self.get_page(page))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


class LazyLoadingService:
    """Service for managing lazy loading across the application."""
    
    def __init__(self, db_connection_manager):
        self.db_manager = db_connection_manager
        self._object_cache = weakref.WeakValueDictionary()
    
    async def get_lazy_file(self, file_id: str) -> LazyFile:
        """Get a lazy file object."""
        cache_key = f"file_{file_id}"
        
        if cache_key in self._object_cache:
            return self._object_cache[cache_key]
        
        async with self.db_manager.get_postgres_connection() as conn:
            query = """
                SELECT id, name, user_id, size, content_type, created_at, updated_at
                FROM files 
                WHERE id = $1 AND deleted_at IS NULL
            """
            row = await conn.fetchrow(query, file_id)
            
            if not row:
                raise ValueError(f"File {file_id} not found")
            
            lazy_file = LazyFile(dict(row), conn)
            self._object_cache[cache_key] = lazy_file
            return lazy_file
    
    async def get_lazy_user(self, user_id: str) -> LazyUser:
        """Get a lazy user object."""
        cache_key = f"user_{user_id}"
        
        if cache_key in self._object_cache:
            return self._object_cache[cache_key]
        
        async with self.db_manager.get_postgres_connection() as conn:
            query = """
                SELECT id, email, name, created_at, updated_at
                FROM users 
                WHERE id = $1 AND deleted_at IS NULL
            """
            row = await conn.fetchrow(query, user_id)
            
            if not row:
                raise ValueError(f"User {user_id} not found")
            
            lazy_user = LazyUser(dict(row), conn)
            self._object_cache[cache_key] = lazy_user
            return lazy_user
    
    def create_lazy_collection(
        self,
        query: str,
        params: List[Any],
        count_query: Optional[str] = None,
        page_size: int = 50
    ) -> LazyCollection:
        """Create a lazy collection for paginated data."""
        
        async def loader(limit: int, offset: int) -> List[Dict[str, Any]]:
            async with self.db_manager.get_postgres_connection() as conn:
                paginated_query = f"{query} LIMIT {limit} OFFSET {offset}"
                rows = await conn.fetch(paginated_query, *params)
                return [dict(row) for row in rows]
        
        async def count_loader() -> int:
            if count_query:
                async with self.db_manager.get_postgres_connection() as conn:
                    row = await conn.fetchrow(count_query, *params)
                    return row['count'] if row else 0
            return 0
        
        return LazyCollection(
            loader=loader,
            total_count_loader=count_loader if count_query else None,
            page_size=page_size
        )


def lazy_property(func):
    """Decorator for creating lazy properties."""
    attr_name = f'_lazy_{func.__name__}'
    
    @wraps(func)
    async def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, await func(self))
        return getattr(self, attr_name)
    
    return property(wrapper)


# Global service instance
lazy_loading_service = None


async def initialize_lazy_loading_service(db_connection_manager):
    """Initialize the global lazy loading service."""
    global lazy_loading_service
    lazy_loading_service = LazyLoadingService(db_connection_manager)
    return lazy_loading_service


def get_lazy_loading_service() -> LazyLoadingService:
    """Get the global lazy loading service."""
    if lazy_loading_service is None:
        raise RuntimeError("Lazy loading service not initialized")
    return lazy_loading_service