"""
Metadata Caching System
Handles caching of frequently accessed file metadata, search results, and analytics data
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from .redis_client import get_redis_client, RedisClient, cache_result

logger = logging.getLogger(__name__)


class MetadataCache:
    """Manages caching of file metadata and related data"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()
        
        # TTL settings (in seconds)
        self.ttl_settings = {
            'file_metadata': 3600 * 6,      # 6 hours
            'file_content': 3600 * 2,       # 2 hours  
            'file_tags': 3600 * 4,          # 4 hours
            'file_permissions': 3600,       # 1 hour
            'search_results': 1800,         # 30 minutes
            'file_relationships': 3600 * 8, # 8 hours
            'user_files': 3600 * 2,         # 2 hours
            'file_analytics': 3600,         # 1 hour
            'embedding_cache': 3600 * 24    # 24 hours
        }
    
    def cache_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """Cache complete file metadata"""
        try:
            # Add cache timestamp
            metadata['cached_at'] = datetime.utcnow().isoformat()
            
            # Cache main metadata
            result = self.redis.set('metadata', f"file:{file_id}", metadata, 
                                  self.ttl_settings['file_metadata'])
            
            # Cache searchable fields separately for quick lookup
            searchable_data = {
                'file_id': file_id,
                'name': metadata.get('name'),
                'path': metadata.get('path'),
                'file_type': metadata.get('file_type'),
                'mime_type': metadata.get('mime_type'),
                'size': metadata.get('size'),
                'user_id': metadata.get('user_id'),
                'modified_at': metadata.get('modified_at'),
                'sync_status': metadata.get('sync_status')
            }
            
            # Index by user for quick user file queries
            user_id = metadata.get('user_id')
            if user_id:
                self.add_file_to_user_index(user_id, file_id, searchable_data)
            
            # Index by file type
            file_type = metadata.get('file_type')
            if file_type:
                self.add_file_to_type_index(file_type, file_id, searchable_data)
            
            logger.debug(f"Cached metadata for file {file_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cache file metadata {file_id}: {e}")
            return False
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get cached file metadata"""
        return self.redis.get('metadata', f"file:{file_id}")
    
    def get_multiple_file_metadata(self, file_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get metadata for multiple files efficiently"""
        keys = [f"file:{file_id}" for file_id in file_ids]
        return self.redis.mget('metadata', keys)
    
    def cache_file_content_preview(self, file_id: str, content_preview: str, 
                                 content_type: str = 'text') -> bool:
        """Cache file content preview for quick display"""
        try:
            content_data = {
                'preview': content_preview,
                'content_type': content_type,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            return self.redis.set('metadata', f"content:{file_id}", content_data,
                                self.ttl_settings['file_content'])
        except Exception as e:
            logger.error(f"Failed to cache content preview {file_id}: {e}")
            return False
    
    def get_file_content_preview(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get cached file content preview"""
        return self.redis.get('metadata', f"content:{file_id}")
    
    def cache_file_tags(self, file_id: str, tags: List[Dict[str, Any]]) -> bool:
        """Cache file tags"""
        try:
            tag_data = {
                'tags': tags,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            # Cache tags
            result = self.redis.set('metadata', f"tags:{file_id}", tag_data,
                                  self.ttl_settings['file_tags'])
            
            # Index tags for search
            for tag in tags:
                tag_name = tag.get('name', '').lower()
                if tag_name:
                    self.redis.sadd('metadata', f"tag_files:{tag_name}", file_id)
                    self.redis.expire('metadata', f"tag_files:{tag_name}", 
                                    self.ttl_settings['file_tags'])
            
            return result
        except Exception as e:
            logger.error(f"Failed to cache file tags {file_id}: {e}")
            return False
    
    def get_file_tags(self, file_id: str) -> List[Dict[str, Any]]:
        """Get cached file tags"""
        tag_data = self.redis.get('metadata', f"tags:{file_id}")
        if tag_data:
            return tag_data.get('tags', [])
        return []
    
    def get_files_by_tag(self, tag_name: str) -> List[str]:
        """Get file IDs associated with a tag"""
        tag_key = tag_name.lower()
        file_ids = self.redis.smembers('metadata', f"tag_files:{tag_key}")
        return list(file_ids) if file_ids else []
    
    def cache_file_permissions(self, file_id: str, permissions: Dict[str, Any]) -> bool:
        """Cache file permissions"""
        try:
            permission_data = {
                'permissions': permissions,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            return self.redis.set('metadata', f"perms:{file_id}", permission_data,
                                self.ttl_settings['file_permissions'])
        except Exception as e:
            logger.error(f"Failed to cache file permissions {file_id}: {e}")
            return False
    
    def get_file_permissions(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get cached file permissions"""
        perm_data = self.redis.get('metadata', f"perms:{file_id}")
        if perm_data:
            return perm_data.get('permissions')
        return None
    
    def add_file_to_user_index(self, user_id: str, file_id: str, 
                              file_data: Dict[str, Any]) -> bool:
        """Add file to user's file index"""
        try:
            # Store in sorted set by modification time for chronological ordering
            modified_at = file_data.get('modified_at')
            score = 0
            
            if modified_at:
                try:
                    dt = datetime.fromisoformat(modified_at.replace('Z', '+00:00'))
                    score = dt.timestamp()
                except (ValueError, AttributeError):
                    score = datetime.utcnow().timestamp()
            
            # Add to user's file list
            self.redis.client.zadd(f"{self.redis.prefixes['metadata']}user_files:{user_id}", 
                                 {file_id: score})
            self.redis.expire('metadata', f"user_files:{user_id}", 
                            self.ttl_settings['user_files'])
            
            # Cache file summary data
            return self.redis.hset('metadata', f"user_file_data:{user_id}", 
                                 file_id, file_data, self.ttl_settings['user_files'])
        except Exception as e:
            logger.error(f"Failed to add file {file_id} to user index {user_id}: {e}")
            return False
    
    def add_file_to_type_index(self, file_type: str, file_id: str, 
                              file_data: Dict[str, Any]) -> bool:
        """Add file to file type index"""
        try:
            self.redis.sadd('metadata', f"type_files:{file_type}", file_id)
            self.redis.expire('metadata', f"type_files:{file_type}", 
                            self.ttl_settings['user_files'])
            
            return self.redis.hset('metadata', f"type_file_data:{file_type}", 
                                 file_id, file_data, self.ttl_settings['user_files'])
        except Exception as e:
            logger.error(f"Failed to add file {file_id} to type index {file_type}: {e}")
            return False
    
    def get_user_files(self, user_id: str, limit: int = 100, 
                      offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's files with pagination"""
        try:
            # Get file IDs from sorted set (most recent first)
            file_ids = self.redis.client.zrevrange(
                f"{self.redis.prefixes['metadata']}user_files:{user_id}",
                offset, offset + limit - 1
            )
            
            if not file_ids:
                return []
            
            # Get file data
            file_data = self.redis.hgetall('metadata', f"user_file_data:{user_id}")
            
            result = []
            for file_id in file_ids:
                if file_id in file_data:
                    result.append(file_data[file_id])
            
            return result
        except Exception as e:
            logger.error(f"Failed to get user files {user_id}: {e}")
            return []
    
    def get_files_by_type(self, file_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get files by type"""
        try:
            file_ids = list(self.redis.smembers('metadata', f"type_files:{file_type}"))[:limit]
            
            if not file_ids:
                return []
            
            file_data = self.redis.hgetall('metadata', f"type_file_data:{file_type}")
            
            result = []
            for file_id in file_ids:
                if file_id in file_data:
                    result.append(file_data[file_id])
            
            return result
        except Exception as e:
            logger.error(f"Failed to get files by type {file_type}: {e}")
            return []
    
    def remove_file_from_cache(self, file_id: str) -> bool:
        """Remove file from all caches"""
        try:
            # Get file metadata to extract indexing info
            metadata = self.get_file_metadata(file_id)
            
            # Remove main metadata
            self.redis.delete('metadata', f"file:{file_id}")
            self.redis.delete('metadata', f"content:{file_id}")
            self.redis.delete('metadata', f"tags:{file_id}")
            self.redis.delete('metadata', f"perms:{file_id}")
            
            if metadata:
                user_id = metadata.get('user_id')
                file_type = metadata.get('file_type')
                
                # Remove from user index
                if user_id:
                    self.redis.client.zrem(f"{self.redis.prefixes['metadata']}user_files:{user_id}", file_id)
                    self.redis.hdel('metadata', f"user_file_data:{user_id}", file_id)
                
                # Remove from type index
                if file_type:
                    self.redis.srem('metadata', f"type_files:{file_type}", file_id)
                    self.redis.hdel('metadata', f"type_file_data:{file_type}", file_id)
                
                # Remove from tag indexes
                tags = self.get_file_tags(file_id)
                for tag in tags:
                    tag_name = tag.get('name', '').lower()
                    if tag_name:
                        self.redis.srem('metadata', f"tag_files:{tag_name}", file_id)
            
            logger.debug(f"Removed file {file_id} from cache")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove file {file_id} from cache: {e}")
            return False
    
    def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate all cached data for a user"""
        try:
            # Remove user file indexes
            self.redis.delete('metadata', f"user_files:{user_id}")
            self.redis.delete('metadata', f"user_file_data:{user_id}")
            
            logger.debug(f"Invalidated cache for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate user cache {user_id}: {e}")
            return False


class SearchCache:
    """Manages caching of search results and related data"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()
        self.search_ttl = 1800  # 30 minutes
        self.popular_searches_ttl = 3600 * 6  # 6 hours
    
    def cache_search_results(self, query_hash: str, results: List[Dict[str, Any]], 
                           search_params: Dict[str, Any]) -> bool:
        """Cache search results"""
        try:
            search_data = {
                'results': results,
                'search_params': search_params,
                'result_count': len(results),
                'cached_at': datetime.utcnow().isoformat()
            }
            
            return self.redis.set('search', query_hash, search_data, self.search_ttl)
        except Exception as e:
            logger.error(f"Failed to cache search results {query_hash}: {e}")
            return False
    
    def get_cached_search_results(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached search results"""
        return self.redis.get('search', query_hash)
    
    def generate_query_hash(self, query: str, filters: Dict[str, Any] = None, 
                          user_id: str = None) -> str:
        """Generate consistent hash for search query"""
        hash_input = {
            'query': query.lower().strip(),
            'filters': filters or {},
            'user_id': user_id
        }
        
        hash_string = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]
    
    def track_popular_search(self, query: str, user_id: str = None) -> bool:
        """Track popular searches"""
        try:
            # Increment search count
            search_key = query.lower().strip()
            self.redis.client.zincrby(f"{self.redis.prefixes['search']}popular", 1, search_key)
            self.redis.expire('search', 'popular', self.popular_searches_ttl)
            
            # Track user-specific popular searches
            if user_id:
                self.redis.client.zincrby(f"{self.redis.prefixes['search']}user_popular:{user_id}", 1, search_key)
                self.redis.expire('search', f'user_popular:{user_id}', self.popular_searches_ttl)
            
            return True
        except Exception as e:
            logger.error(f"Failed to track popular search '{query}': {e}")
            return False
    
    def get_popular_searches(self, limit: int = 10, user_id: str = None) -> List[Tuple[str, float]]:
        """Get popular searches"""
        try:
            if user_id:
                key = f"{self.redis.prefixes['search']}user_popular:{user_id}"
            else:
                key = f"{self.redis.prefixes['search']}popular"
            
            # Get top searches with scores
            results = self.redis.client.zrevrange(key, 0, limit - 1, withscores=True)
            return [(search.decode() if isinstance(search, bytes) else search, score) 
                   for search, score in results]
        except Exception as e:
            logger.error(f"Failed to get popular searches: {e}")
            return []
    
    def invalidate_search_cache(self, pattern: str = None) -> int:
        """Invalidate search cache"""
        if pattern:
            cache_pattern = f"{self.redis.prefixes['search']}{pattern}*"
        else:
            cache_pattern = f"{self.redis.prefixes['search']}*"
        
        return self.redis.delete_pattern(cache_pattern)


class AnalyticsCache:
    """Manages caching of analytics and aggregated data"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()
        self.analytics_ttl = 3600  # 1 hour
    
    def cache_user_analytics(self, user_id: str, analytics_data: Dict[str, Any]) -> bool:
        """Cache user analytics data"""
        try:
            analytics_data['cached_at'] = datetime.utcnow().isoformat()
            return self.redis.set('analytics', f"user:{user_id}", analytics_data, self.analytics_ttl)
        except Exception as e:
            logger.error(f"Failed to cache user analytics {user_id}: {e}")
            return False
    
    def get_user_analytics(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user analytics"""
        return self.redis.get('analytics', f"user:{user_id}")
    
    def cache_system_analytics(self, analytics_data: Dict[str, Any]) -> bool:
        """Cache system-wide analytics"""
        try:
            analytics_data['cached_at'] = datetime.utcnow().isoformat()
            return self.redis.set('analytics', 'system', analytics_data, self.analytics_ttl)
        except Exception as e:
            logger.error(f"Failed to cache system analytics: {e}")
            return False
    
    def get_system_analytics(self) -> Optional[Dict[str, Any]]:
        """Get cached system analytics"""
        return self.redis.get('analytics', 'system')
    
    def cache_file_analytics(self, file_id: str, analytics_data: Dict[str, Any]) -> bool:
        """Cache file-specific analytics"""
        try:
            analytics_data['cached_at'] = datetime.utcnow().isoformat()
            return self.redis.set('analytics', f"file:{file_id}", analytics_data, self.analytics_ttl)
        except Exception as e:
            logger.error(f"Failed to cache file analytics {file_id}: {e}")
            return False
    
    def get_file_analytics(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get cached file analytics"""
        return self.redis.get('analytics', f"file:{file_id}")


# Global instances
metadata_cache = None
search_cache = None
analytics_cache = None


def get_metadata_cache() -> MetadataCache:
    """Get global metadata cache instance"""
    global metadata_cache
    if metadata_cache is None:
        metadata_cache = MetadataCache()
    return metadata_cache


def get_search_cache() -> SearchCache:
    """Get global search cache instance"""
    global search_cache
    if search_cache is None:
        search_cache = SearchCache()
    return search_cache


def get_analytics_cache() -> AnalyticsCache:
    """Get global analytics cache instance"""
    global analytics_cache
    if analytics_cache is None:
        analytics_cache = AnalyticsCache()
    return analytics_cache


# Decorator for caching function results with automatic key generation
def cache_metadata(cache_type: str = 'metadata', ttl: int = None):
    """Decorator for caching metadata-related function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            redis = get_redis_client()
            cached_result = redis.get(cache_type, cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                redis.set(cache_type, cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator