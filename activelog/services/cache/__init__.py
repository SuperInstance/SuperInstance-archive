"""
ActiveLog Redis Caching System
Comprehensive caching implementation for improved performance and distributed coordination
"""

from .redis_client import (
    RedisClient,
    get_redis_client,
    cache_result,
    async_cache_result
)

from .session_cache import (
    SessionCache,
    PermissionCache,
    get_session_cache,
    get_permission_cache
)

from .metadata_cache import (
    MetadataCache,
    SearchCache,
    AnalyticsCache,
    get_metadata_cache,
    get_search_cache,
    get_analytics_cache,
    cache_metadata
)

from .invalidation import (
    CacheInvalidationManager,
    SmartCacheInvalidator,
    InvalidationType,
    InvalidationRule,
    get_invalidation_manager,
    invalidate_cache,
    register_invalidation_rule
)

from .api_cache import (
    APIResponseCache,
    CacheMiddleware,
    get_api_cache,
    create_cache_middleware,
    cache_api_response,
    invalidate_api_cache
)

from .distributed_locks import (
    DistributedLock,
    AsyncDistributedLock,
    SyncCoordinator,
    LockType,
    LockInfo,
    LockAcquisitionError,
    LockTimeoutError,
    get_distributed_lock,
    get_async_distributed_lock,
    get_sync_coordinator,
    acquire_sync_lock,
    release_sync_lock
)

__version__ = "1.0.0"

__all__ = [
    # Redis Client
    'RedisClient',
    'get_redis_client',
    'cache_result',
    'async_cache_result',
    
    # Session Management
    'SessionCache',
    'PermissionCache',
    'get_session_cache',
    'get_permission_cache',
    
    # Metadata Caching
    'MetadataCache',
    'SearchCache',
    'AnalyticsCache',
    'get_metadata_cache',
    'get_search_cache',
    'get_analytics_cache',
    'cache_metadata',
    
    # Cache Invalidation
    'CacheInvalidationManager',
    'SmartCacheInvalidator',
    'InvalidationType',
    'InvalidationRule',
    'get_invalidation_manager',
    'invalidate_cache',
    'register_invalidation_rule',
    
    # API Response Caching
    'APIResponseCache',
    'CacheMiddleware',
    'get_api_cache',
    'create_cache_middleware',
    'cache_api_response',
    'invalidate_api_cache',
    
    # Distributed Locks
    'DistributedLock',
    'AsyncDistributedLock',
    'SyncCoordinator',
    'LockType',
    'LockInfo',
    'LockAcquisitionError',
    'LockTimeoutError',
    'get_distributed_lock',
    'get_async_distributed_lock',
    'get_sync_coordinator',
    'acquire_sync_lock',
    'release_sync_lock'
]