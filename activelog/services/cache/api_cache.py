"""
API Gateway Response Caching
Implements comprehensive response caching for the API Gateway
"""

import json
import hashlib
import time
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging
from .redis_client import get_redis_client, RedisClient

logger = logging.getLogger(__name__)


class APIResponseCache:
    """Handles caching of API responses with intelligent cache strategies"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()
        
        # Cache configuration by endpoint pattern
        self.cache_config = {
            # File operations
            '/metadata/files': {
                'ttl': 300,  # 5 minutes
                'cache_methods': ['GET'],
                'cache_by_user': True,
                'compress': True,
                'vary_headers': ['Accept', 'Accept-Encoding']
            },
            '/metadata/files/{file_id}': {
                'ttl': 600,  # 10 minutes
                'cache_methods': ['GET'],
                'cache_by_user': True,
                'compress': True,
                'etag': True
            },
            '/metadata/search': {
                'ttl': 1800,  # 30 minutes
                'cache_methods': ['GET', 'POST'],
                'cache_by_user': True,
                'compress': True,
                'vary_headers': ['Accept']
            },
            
            # User operations
            '/auth/me': {
                'ttl': 300,  # 5 minutes
                'cache_methods': ['GET'],
                'cache_by_user': True,
                'private': True
            },
            '/metadata/tags': {
                'ttl': 900,  # 15 minutes
                'cache_methods': ['GET'],
                'cache_by_user': True,
                'compress': True
            },
            
            # Analytics (longer cache)
            '/analytics/dashboard': {
                'ttl': 3600,  # 1 hour
                'cache_methods': ['GET'],
                'cache_by_user': True,
                'compress': True
            },
            '/analytics/stats': {
                'ttl': 1800,  # 30 minutes
                'cache_methods': ['GET'],
                'cache_by_user': True,
                'compress': True
            },
            
            # System endpoints (public cache)
            '/health': {
                'ttl': 60,  # 1 minute
                'cache_methods': ['GET'],
                'cache_by_user': False,
                'public': True
            },
            '/version': {
                'ttl': 3600,  # 1 hour
                'cache_methods': ['GET'],
                'cache_by_user': False,
                'public': True
            }
        }
        
        # Default cache settings
        self.default_config = {
            'ttl': 300,
            'cache_methods': ['GET'],
            'cache_by_user': False,
            'compress': False,
            'etag': False,
            'private': False,
            'public': False,
            'vary_headers': []
        }
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'invalidations': 0
        }
    
    def _get_endpoint_config(self, path: str) -> Dict[str, Any]:
        """Get cache configuration for endpoint"""
        # Try exact match first
        if path in self.cache_config:
            return {**self.default_config, **self.cache_config[path]}
        
        # Try pattern matching
        for pattern, config in self.cache_config.items():
            if self._match_path_pattern(path, pattern):
                return {**self.default_config, **config}
        
        return self.default_config
    
    def _match_path_pattern(self, path: str, pattern: str) -> bool:
        """Match path against pattern with placeholders"""
        path_parts = path.strip('/').split('/')
        pattern_parts = pattern.strip('/').split('/')
        
        if len(path_parts) != len(pattern_parts):
            return False
        
        for path_part, pattern_part in zip(path_parts, pattern_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                continue  # Placeholder matches anything
            elif path_part != pattern_part:
                return False
        
        return True
    
    def _generate_cache_key(self, request: Request, config: Dict[str, Any]) -> str:
        """Generate unique cache key for request"""
        key_parts = [
            'api_response',
            request.method,
            request.url.path
        ]
        
        # Add query parameters (sorted for consistency)
        if request.query_params:
            query_parts = []
            for key, value in sorted(request.query_params.items()):
                query_parts.append(f"{key}={value}")
            key_parts.append("?" + "&".join(query_parts))
        
        # Add user ID if caching by user
        if config.get('cache_by_user') and hasattr(request.state, 'user_id'):
            key_parts.append(f"user:{request.state.user_id}")
        
        # Add request body hash for POST requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            body_hash = getattr(request.state, 'body_hash', '')
            if body_hash:
                key_parts.append(f"body:{body_hash}")
        
        # Add vary headers
        vary_headers = config.get('vary_headers', [])
        for header in vary_headers:
            header_value = request.headers.get(header.lower(), '')
            if header_value:
                key_parts.append(f"{header.lower()}:{header_value}")
        
        # Generate final cache key
        cache_key = ":".join(key_parts)
        return hashlib.sha256(cache_key.encode()).hexdigest()
    
    def _compress_response(self, data: bytes) -> bytes:
        """Compress response data"""
        return gzip.compress(data)
    
    def _decompress_response(self, data: bytes) -> bytes:
        """Decompress response data"""
        return gzip.decompress(data)
    
    def _serialize_response(self, response_data: Dict[str, Any], 
                          compressed: bool = False) -> str:
        """Serialize response for cache storage"""
        if compressed and 'body' in response_data:
            # Compress body if it's large enough
            body_bytes = response_data['body'].encode('utf-8')
            if len(body_bytes) > 1024:  # Only compress if > 1KB
                response_data['body'] = self._compress_response(body_bytes).hex()
                response_data['compressed'] = True
        
        return json.dumps(response_data)
    
    def _deserialize_response(self, cached_data: str) -> Dict[str, Any]:
        """Deserialize response from cache"""
        try:
            response_data = json.loads(cached_data)
            
            # Decompress if needed
            if response_data.get('compressed'):
                compressed_body = bytes.fromhex(response_data['body'])
                response_data['body'] = self._decompress_response(compressed_body).decode('utf-8')
                response_data.pop('compressed', None)
            
            return response_data
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to deserialize cached response: {e}")
            return None
    
    def _generate_etag(self, content: str) -> str:
        """Generate ETag for response"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_cached_response(self, request: Request) -> Optional[Response]:
        """Get cached response if available"""
        config = self._get_endpoint_config(request.url.path)
        
        # Check if method is cacheable
        if request.method not in config['cache_methods']:
            return None
        
        # Generate cache key
        cache_key = self._generate_cache_key(request, config)
        
        # Try to get from cache
        cached_data = self.redis.get('api_response', cache_key)
        
        if cached_data is None:
            self.stats['misses'] += 1
            return None
        
        # Deserialize response
        response_data = self._deserialize_response(cached_data)
        if not response_data:
            self.stats['misses'] += 1
            return None
        
        # Check ETag if supported
        if config.get('etag') and 'etag' in response_data:
            client_etag = request.headers.get('if-none-match')
            if client_etag == response_data['etag']:
                self.stats['hits'] += 1
                return Response(status_code=304)  # Not Modified
        
        # Create response from cached data
        response = JSONResponse(
            content=json.loads(response_data['body']),
            status_code=response_data.get('status_code', 200),
            headers=response_data.get('headers', {})
        )
        
        # Add cache headers
        response.headers['X-Cache'] = 'HIT'
        response.headers['X-Cache-Key'] = cache_key[:16]  # Shortened for debugging
        
        if 'cached_at' in response_data:
            response.headers['X-Cache-Date'] = response_data['cached_at']
        
        self.stats['hits'] += 1
        return response
    
    def cache_response(self, request: Request, response: Response) -> bool:
        """Cache response if appropriate"""
        config = self._get_endpoint_config(request.url.path)
        
        # Check if method is cacheable
        if request.method not in config['cache_methods']:
            return False
        
        # Check if status code is cacheable
        if response.status_code not in [200, 201, 204, 300, 301, 302, 304, 404, 410]:
            return False
        
        # Generate cache key
        cache_key = self._generate_cache_key(request, config)
        
        try:
            # Extract response data
            if hasattr(response, 'body'):
                body = response.body.decode('utf-8')
            else:
                # For streaming responses, we might not want to cache
                return False
            
            # Prepare response data for caching
            response_data = {
                'body': body,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'cached_at': datetime.utcnow().isoformat(),
                'ttl': config['ttl']
            }
            
            # Generate ETag if configured
            if config.get('etag'):
                etag = self._generate_etag(body)
                response_data['etag'] = etag
                response.headers['ETag'] = etag
            
            # Add cache control headers
            if config.get('public'):
                response.headers['Cache-Control'] = f"public, max-age={config['ttl']}"
            elif config.get('private'):
                response.headers['Cache-Control'] = f"private, max-age={config['ttl']}"
            else:
                response.headers['Cache-Control'] = f"max-age={config['ttl']}"
            
            # Add Vary headers
            vary_headers = config.get('vary_headers', [])
            if vary_headers:
                response.headers['Vary'] = ', '.join(vary_headers)
            
            # Serialize and store
            serialized_data = self._serialize_response(response_data, config.get('compress', False))
            
            success = self.redis.set('api_response', cache_key, serialized_data, config['ttl'])
            
            if success:
                self.stats['sets'] += 1
                # Add cache info headers
                response.headers['X-Cache'] = 'MISS'
                response.headers['X-Cache-Key'] = cache_key[:16]
                logger.debug(f"Cached response for {request.method} {request.url.path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache response for {request.url.path}: {e}")
            return False
    
    def invalidate_cache(self, pattern: str = None, paths: List[str] = None, 
                        user_id: str = None) -> int:
        """Invalidate cached responses"""
        invalidated_count = 0
        
        if pattern:
            # Invalidate by pattern
            cache_pattern = f"{self.redis.prefixes['api_response']}{pattern}*"
            invalidated_count += self.redis.delete_pattern(cache_pattern)
        
        elif paths:
            # Invalidate specific paths
            for path in paths:
                if user_id:
                    # Invalidate user-specific cache
                    cache_pattern = f"{self.redis.prefixes['api_response']}*{path}*user:{user_id}*"
                else:
                    # Invalidate all caches for path
                    cache_pattern = f"{self.redis.prefixes['api_response']}*{path}*"
                
                invalidated_count += self.redis.delete_pattern(cache_pattern)
        
        elif user_id:
            # Invalidate all user caches
            cache_pattern = f"{self.redis.prefixes['api_response']}*user:{user_id}*"
            invalidated_count += self.redis.delete_pattern(cache_pattern)
        
        else:
            # Clear all API response cache
            invalidated_count += self.redis.clear_prefix('api_response')
        
        self.stats['invalidations'] += invalidated_count
        logger.debug(f"Invalidated {invalidated_count} cached responses")
        
        return invalidated_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests
        }
    
    def clear_stats(self):
        """Clear cache statistics"""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'invalidations': 0
        }
    
    def warm_cache(self, endpoints: List[Dict[str, Any]]) -> int:
        """Warm cache with pre-computed responses"""
        warmed_count = 0
        
        for endpoint in endpoints:
            try:
                path = endpoint['path']
                method = endpoint.get('method', 'GET')
                response_data = endpoint['response_data']
                ttl = endpoint.get('ttl', 300)
                
                # Create mock request for cache key generation
                mock_request = type('MockRequest', (), {
                    'method': method,
                    'url': type('MockURL', (), {'path': path})(),
                    'query_params': endpoint.get('query_params', {}),
                    'headers': endpoint.get('headers', {}),
                    'state': type('MockState', (), endpoint.get('state', {}))()
                })()
                
                config = self._get_endpoint_config(path)
                cache_key = self._generate_cache_key(mock_request, config)
                
                # Store pre-computed response
                cache_data = {
                    'body': json.dumps(response_data),
                    'status_code': 200,
                    'headers': {},
                    'cached_at': datetime.utcnow().isoformat(),
                    'ttl': ttl
                }
                
                serialized_data = self._serialize_response(cache_data, config.get('compress', False))
                
                if self.redis.set('api_response', cache_key, serialized_data, ttl):
                    warmed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to warm cache for endpoint {endpoint}: {e}")
        
        logger.info(f"Warmed {warmed_count} cache entries")
        return warmed_count


class CacheMiddleware:
    """FastAPI middleware for automatic response caching"""
    
    def __init__(self, cache: APIResponseCache):
        self.cache = cache
    
    async def __call__(self, request: Request, call_next):
        # Hash request body for POST requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            body = await request.body()
            if body:
                request.state.body_hash = hashlib.sha256(body).hexdigest()
        
        # Try to get cached response
        cached_response = self.cache.get_cached_response(request)
        if cached_response:
            return cached_response
        
        # Process request
        response = await call_next(request)
        
        # Cache response if appropriate
        self.cache.cache_response(request, response)
        
        return response


# Global cache instance
api_cache = None


def get_api_cache() -> APIResponseCache:
    """Get global API response cache instance"""
    global api_cache
    if api_cache is None:
        api_cache = APIResponseCache()
    return api_cache


def create_cache_middleware() -> CacheMiddleware:
    """Create cache middleware instance"""
    return CacheMiddleware(get_api_cache())


# Convenience functions for manual cache management
def cache_api_response(path: str, response_data: Any, ttl: int = None, user_id: str = None):
    """Manually cache API response"""
    cache = get_api_cache()
    
    # Create mock request
    mock_request = type('MockRequest', (), {
        'method': 'GET',
        'url': type('MockURL', (), {'path': path})(),
        'query_params': {},
        'headers': {},
        'state': type('MockState', (), {'user_id': user_id} if user_id else {})()
    })()
    
    config = cache._get_endpoint_config(path)
    if ttl:
        config['ttl'] = ttl
    
    cache_key = cache._generate_cache_key(mock_request, config)
    
    cache_data = {
        'body': json.dumps(response_data),
        'status_code': 200,
        'headers': {},
        'cached_at': datetime.utcnow().isoformat(),
        'ttl': config['ttl']
    }
    
    serialized_data = cache._serialize_response(cache_data, config.get('compress', False))
    return cache.redis.set('api_response', cache_key, serialized_data, config['ttl'])


def invalidate_api_cache(paths: List[str] = None, user_id: str = None):
    """Invalidate API response cache"""
    cache = get_api_cache()
    return cache.invalidate_cache(paths=paths, user_id=user_id)