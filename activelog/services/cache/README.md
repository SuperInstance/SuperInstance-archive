# ActiveLog Redis Caching System

A comprehensive Redis-based caching solution for the ActiveLog file management system, providing session management, metadata caching, response caching, cache invalidation, and distributed locking.

## Features

### 🚀 **Core Caching Capabilities**
- **Session Management**: User sessions and permissions with automatic expiration
- **Metadata Caching**: File metadata, tags, and relationships with intelligent indexing
- **Search Result Caching**: Query results with popularity tracking and optimization
- **API Response Caching**: HTTP response caching with ETags, compression, and cache headers
- **Analytics Caching**: Dashboard data and statistics with time-based invalidation

### 🔄 **Advanced Invalidation Strategies**
- **Immediate Invalidation**: Real-time cache clearing for critical updates
- **Lazy Invalidation**: Deferred invalidation for performance optimization
- **Dependency-Based**: Intelligent invalidation based on data relationships
- **Time-Based**: TTL management with smart expiration policies
- **Pattern-Based**: Bulk invalidation using Redis patterns

### 🔒 **Distributed Locking**
- **Exclusive Locks**: Prevent concurrent modifications
- **Shared Locks**: Allow concurrent reads
- **Reentrant Locks**: Support for nested lock acquisition
- **Lock Extension**: Dynamic timeout management
- **Sync Coordination**: File synchronization across distributed systems

### ⚡ **Performance Optimizations**
- **Connection Pooling**: Efficient Redis connection management
- **Compression**: Automatic compression for large responses
- **Batch Operations**: Bulk cache operations for better performance
- **Async Support**: Full async/await compatibility
- **Memory Optimization**: Smart memory usage with configurable limits

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from cache import (
    get_redis_client,
    get_session_cache,
    get_metadata_cache,
    get_api_cache,
    get_distributed_lock
)

# Initialize Redis connection
redis = get_redis_client()

# Session management
session_cache = get_session_cache()
tokens = session_cache.create_session(
    user_id="user123",
    user_data={"name": "John Doe", "email": "john@example.com"},
    permissions=["read", "write"]
)

# Metadata caching
metadata_cache = get_metadata_cache()
metadata_cache.cache_file_metadata("file123", {
    "name": "document.pdf",
    "size": 1024000,
    "user_id": "user123"
})

# Distributed locking
lock = get_distributed_lock()
with lock.lock("file:123", timeout=60) as lock_id:
    # Perform file operation safely
    print(f"Acquired lock: {lock_id}")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from cache import create_cache_middleware, get_api_cache

app = FastAPI()

# Add caching middleware
app.add_middleware(create_cache_middleware())

@app.get("/files/{file_id}")
async def get_file(file_id: str):
    # Response will be automatically cached
    return {"file_id": file_id, "data": "..."}

# Manual cache management
api_cache = get_api_cache()
api_cache.invalidate_cache(paths=["/files"])
```

## Configuration

### Redis Configuration

```python
from cache import RedisClient

redis = RedisClient(
    host="localhost",
    port=6379,
    db=0,
    password="your_password",
    max_connections=20
)
```

### Cache TTL Settings

```python
# Default TTL values (in seconds)
TTL_SETTINGS = {
    'session': 3600 * 24,      # 24 hours
    'user': 3600 * 2,          # 2 hours
    'permissions': 3600,       # 1 hour
    'metadata': 3600 * 6,      # 6 hours
    'search': 1800,            # 30 minutes
    'api_response': 300,       # 5 minutes
    'analytics': 3600          # 1 hour
}
```

### API Response Cache Configuration

```python
CACHE_CONFIG = {
    '/metadata/files': {
        'ttl': 300,
        'cache_methods': ['GET'],
        'cache_by_user': True,
        'compress': True,
        'vary_headers': ['Accept', 'Accept-Encoding']
    },
    '/analytics/dashboard': {
        'ttl': 3600,
        'cache_methods': ['GET'],
        'cache_by_user': True,
        'compress': True
    }
}
```

## API Reference

### Session Management

```python
from cache import SessionCache

session_cache = SessionCache()

# Create session
tokens = session_cache.create_session(
    user_id="user123",
    user_data={"name": "John", "role": "admin"},
    permissions=["read", "write", "admin"]
)

# Get session
session = session_cache.get_session(tokens['access_token'])

# Refresh session
new_tokens = session_cache.refresh_session(tokens['refresh_token'])

# Invalidate session
session_cache.invalidate_session(tokens['session_id'])
```

### Metadata Caching

```python
from cache import MetadataCache

metadata_cache = MetadataCache()

# Cache file metadata
metadata_cache.cache_file_metadata("file123", {
    "name": "document.pdf",
    "size": 1024000,
    "user_id": "user123",
    "tags": ["important", "work"]
})

# Get cached metadata
metadata = metadata_cache.get_file_metadata("file123")

# Cache file tags
metadata_cache.cache_file_tags("file123", [
    {"name": "important", "color": "#ff0000"},
    {"name": "work", "color": "#0000ff"}
])

# Get user files
user_files = metadata_cache.get_user_files("user123", limit=50)
```

### Search Caching

```python
from cache import SearchCache

search_cache = SearchCache()

# Cache search results
query_hash = search_cache.generate_query_hash(
    query="important documents",
    filters={"file_type": "pdf"},
    user_id="user123"
)

search_cache.cache_search_results(query_hash, results, search_params)

# Get cached results
cached_results = search_cache.get_cached_search_results(query_hash)

# Track popular searches
search_cache.track_popular_search("important documents", "user123")

# Get popular searches
popular = search_cache.get_popular_searches(limit=10, user_id="user123")
```

### Cache Invalidation

```python
from cache import get_invalidation_manager, InvalidationType, InvalidationRule

manager = get_invalidation_manager()

# Register custom invalidation rule
rule = InvalidationRule(
    cache_type='metadata',
    invalidation_type=InvalidationType.IMMEDIATE,
    dependencies=['file_metadata', 'user_files', 'search_results']
)
manager.register_rule('file_update', rule)

# Trigger invalidation
manager.invalidate('file_update', {
    'file_id': 'file123',
    'user_id': 'user123'
})

# Process lazy invalidations
processed = manager.process_lazy_invalidation_queue()
```

### Distributed Locking

```python
from cache import DistributedLock, LockType

lock = DistributedLock()

# Acquire exclusive lock
lock_id = lock.acquire(
    resource="file:123",
    timeout=60,
    lock_type=LockType.EXCLUSIVE
)

# Use context manager
with lock.lock("file:123", timeout=60) as lock_id:
    # Safe operations
    pass

# Async locking
from cache import AsyncDistributedLock

async_lock = AsyncDistributedLock()

async with async_lock.lock("file:123") as lock_id:
    # Async operations
    pass
```

### Sync Coordination

```python
from cache import SyncCoordinator

coordinator = SyncCoordinator()

# Coordinate file sync
with coordinator.sync_file("file123", "file_upload", "user123") as lock_id:
    # Perform upload operation
    pass

# Resolve conflicts
with coordinator.resolve_conflict("file123", "user123", conflict_data) as lock_id:
    # Handle conflict resolution
    pass

# Get active operations
active_ops = coordinator.get_active_sync_operations("user123")
```

## Monitoring and Statistics

### Cache Statistics

```python
from cache import get_api_cache, get_redis_client

# API cache stats
api_cache = get_api_cache()
stats = api_cache.get_cache_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")

# Redis info
redis = get_redis_client()
info = redis.get_info()
print(f"Used memory: {info['used_memory_human']}")

# Invalidation stats
from cache import get_invalidation_manager
manager = get_invalidation_manager()
inv_stats = manager.get_invalidation_stats()
```

### Health Checks

```python
# Redis health check
redis = get_redis_client()
is_healthy = redis.health_check()

# Lock manager stats
lock = get_distributed_lock()
lock_stats = lock.get_stats()
print(f"Active locks: {lock_stats['active_locks']}")
```

## Performance Tuning

### Memory Optimization

```python
# Cleanup expired locks
lock = get_distributed_lock()
cleaned = lock.cleanup_expired_locks()

# Clear old cache entries
redis = get_redis_client()
cleared = redis.delete_pattern("old_prefix:*")
```

### Compression Settings

```python
# Enable compression for large responses
CACHE_CONFIG = {
    '/large-data-endpoint': {
        'compress': True,
        'ttl': 3600
    }
}
```

### Connection Pool Tuning

```python
redis = RedisClient(
    host="localhost",
    port=6379,
    max_connections=50,  # Increase for high traffic
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5
)
```

## Best Practices

### 1. Cache Key Design
- Use consistent naming conventions
- Include version information for schema changes
- Consider key length and Redis memory usage

### 2. TTL Management
- Set appropriate TTL values based on data volatility
- Use longer TTLs for static data
- Implement smart refresh strategies

### 3. Invalidation Strategy
- Use immediate invalidation for critical data
- Implement lazy invalidation for performance
- Set up dependency-based invalidation

### 4. Lock Management
- Keep lock duration minimal
- Use appropriate lock types (exclusive vs shared)
- Implement proper timeout handling

### 5. Error Handling
- Always handle Redis connection failures gracefully
- Implement fallback mechanisms
- Use circuit breakers for Redis operations

## Troubleshooting

### Common Issues

**Redis Connection Failures**
```python
# Check Redis connectivity
redis = get_redis_client()
if not redis.health_check():
    print("Redis is not available")
```

**Lock Acquisition Timeouts**
```python
# Increase timeout or use non-blocking acquisition
try:
    with lock.lock("resource", timeout=120) as lock_id:
        # operations
        pass
except LockAcquisitionError:
    # Handle timeout
    pass
```

**Cache Miss Performance**
```python
# Implement cache warming
api_cache = get_api_cache()
api_cache.warm_cache([
    {
        'path': '/popular-endpoint',
        'response_data': {...},
        'ttl': 3600
    }
])
```

**Memory Usage**
```python
# Monitor memory usage
redis = get_redis_client()
info = redis.get_info()
memory_usage = info['used_memory']
```

## Integration Examples

### With Authentication Service

```python
from cache import get_session_cache

def authenticate_user(access_token: str):
    session_cache = get_session_cache()
    session = session_cache.get_session(access_token)
    
    if not session:
        raise AuthenticationError("Invalid token")
    
    return session
```

### With File Service

```python
from cache import get_metadata_cache, invalidate_cache

def update_file_metadata(file_id: str, metadata: dict):
    # Update database
    database.update_file(file_id, metadata)
    
    # Update cache
    metadata_cache = get_metadata_cache()
    metadata_cache.cache_file_metadata(file_id, metadata)
    
    # Invalidate related caches
    invalidate_cache('file_update', file_id=file_id, user_id=metadata['user_id'])
```

### With Search Service

```python
from cache import get_search_cache

def search_files(query: str, user_id: str, filters: dict):
    search_cache = get_search_cache()
    
    # Generate cache key
    query_hash = search_cache.generate_query_hash(query, filters, user_id)
    
    # Try cache first
    cached_results = search_cache.get_cached_search_results(query_hash)
    if cached_results:
        return cached_results['results']
    
    # Perform search
    results = elasticsearch.search(query, filters, user_id)
    
    # Cache results
    search_cache.cache_search_results(query_hash, results, {
        'query': query,
        'filters': filters,
        'user_id': user_id
    })
    
    # Track popularity
    search_cache.track_popular_search(query, user_id)
    
    return results
```

## Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Consider performance implications
5. Test with realistic data volumes

## License

This caching system is part of the ActiveLog project and follows the same licensing terms.