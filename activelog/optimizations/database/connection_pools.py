"""
Database connection pooling optimizations for ActiveLog.
Provides optimized connection pool configurations for PostgreSQL, Redis, and Elasticsearch.
"""
import asyncio
from typing import Dict, Any, Optional
import asyncpg
import aioredis
from elasticsearch import AsyncElasticsearch
from contextlib import asynccontextmanager
import logging
from functools import lru_cache
import time

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """Manages optimized database connections with connection pooling."""
    
    def __init__(self):
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis_pool: Optional[aioredis.ConnectionPool] = None
        self.es_client: Optional[AsyncElasticsearch] = None
        self._pool_stats = {
            'postgres': {'connections': 0, 'queries': 0, 'avg_time': 0},
            'redis': {'connections': 0, 'operations': 0, 'avg_time': 0},
            'elasticsearch': {'connections': 0, 'requests': 0, 'avg_time': 0}
        }
    
    async def initialize_postgres_pool(
        self,
        database_url: str,
        min_connections: int = 10,
        max_connections: int = 50,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0,
        timeout: float = 60.0
    ) -> asyncpg.Pool:
        """Initialize optimized PostgreSQL connection pool."""
        try:
            self.pg_pool = await asyncpg.create_pool(
                database_url,
                min_size=min_connections,
                max_size=max_connections,
                max_queries=max_queries,
                max_inactive_connection_lifetime=max_inactive_connection_lifetime,
                timeout=timeout,
                command_timeout=30,
                server_settings={
                    'jit': 'off',  # Disable JIT for better predictable performance
                    'application_name': 'activelog_optimized',
                    'tcp_keepalives_idle': '300',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3'
                }
            )
            self._pool_stats['postgres']['connections'] = max_connections
            logger.info(f"PostgreSQL pool initialized with {min_connections}-{max_connections} connections")
            return self.pg_pool
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise
    
    async def initialize_redis_pool(
        self,
        redis_url: str,
        max_connections: int = 20,
        retry_on_timeout: bool = True,
        socket_keepalive: bool = True,
        socket_keepalive_options: Optional[Dict[str, int]] = None
    ) -> aioredis.ConnectionPool:
        """Initialize optimized Redis connection pool."""
        try:
            if socket_keepalive_options is None:
                socket_keepalive_options = {
                    'TCP_KEEPIDLE': 300,
                    'TCP_KEEPINTVL': 30,
                    'TCP_KEEPCNT': 3
                }
            
            self.redis_pool = aioredis.ConnectionPool.from_url(
                redis_url,
                max_connections=max_connections,
                retry_on_timeout=retry_on_timeout,
                socket_keepalive=socket_keepalive,
                socket_keepalive_options=socket_keepalive_options,
                socket_connect_timeout=10,
                socket_timeout=30,
                encoding='utf-8',
                decode_responses=True
            )
            
            self._pool_stats['redis']['connections'] = max_connections
            logger.info(f"Redis pool initialized with {max_connections} connections")
            return self.redis_pool
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
            raise
    
    async def initialize_elasticsearch_client(
        self,
        hosts: list,
        max_connections: int = 10,
        timeout: int = 30,
        retry_on_timeout: bool = True
    ) -> AsyncElasticsearch:
        """Initialize optimized Elasticsearch client."""
        try:
            self.es_client = AsyncElasticsearch(
                hosts,
                max_retries=3,
                retry_on_timeout=retry_on_timeout,
                timeout=timeout,
                maxsize=max_connections,
                verify_certs=False,  # Configure based on your security requirements
                request_timeout=timeout
            )
            
            # Test connection
            info = await self.es_client.info()
            self._pool_stats['elasticsearch']['connections'] = max_connections
            logger.info(f"Elasticsearch client initialized: {info['version']['number']}")
            return self.es_client
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch client: {e}")
            raise
    
    @asynccontextmanager
    async def get_postgres_connection(self):
        """Get PostgreSQL connection from pool with automatic cleanup."""
        if not self.pg_pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        start_time = time.time()
        connection = None
        try:
            connection = await self.pg_pool.acquire(timeout=10.0)
            yield connection
        except Exception as e:
            logger.error(f"PostgreSQL connection error: {e}")
            raise
        finally:
            if connection:
                await self.pg_pool.release(connection)
                query_time = time.time() - start_time
                self._update_stats('postgres', 'queries', query_time)
    
    @asynccontextmanager
    async def get_redis_connection(self):
        """Get Redis connection from pool with automatic cleanup."""
        if not self.redis_pool:
            raise RuntimeError("Redis pool not initialized")
        
        start_time = time.time()
        redis_client = None
        try:
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            yield redis_client
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            raise
        finally:
            if redis_client:
                await redis_client.close()
                operation_time = time.time() - start_time
                self._update_stats('redis', 'operations', operation_time)
    
    def get_elasticsearch_client(self) -> AsyncElasticsearch:
        """Get Elasticsearch client."""
        if not self.es_client:
            raise RuntimeError("Elasticsearch client not initialized")
        return self.es_client
    
    def _update_stats(self, db_type: str, operation_key: str, execution_time: float):
        """Update connection pool statistics."""
        stats = self._pool_stats[db_type]
        stats[operation_key] += 1
        # Calculate rolling average
        current_avg = stats.get('avg_time', 0)
        count = stats[operation_key]
        stats['avg_time'] = (current_avg * (count - 1) + execution_time) / count
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return self._pool_stats.copy()
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connections."""
        health = {}
        
        # PostgreSQL health check
        try:
            async with self.get_postgres_connection() as conn:
                await conn.fetchval("SELECT 1")
                health['postgres'] = True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            health['postgres'] = False
        
        # Redis health check
        try:
            async with self.get_redis_connection() as redis:
                await redis.ping()
                health['redis'] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health['redis'] = False
        
        # Elasticsearch health check
        try:
            es_client = self.get_elasticsearch_client()
            await es_client.ping()
            health['elasticsearch'] = True
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            health['elasticsearch'] = False
        
        return health
    
    async def close_all_connections(self):
        """Close all connection pools and clients."""
        if self.pg_pool:
            await self.pg_pool.close()
            logger.info("PostgreSQL pool closed")
        
        if self.redis_pool:
            await self.redis_pool.disconnect()
            logger.info("Redis pool closed")
        
        if self.es_client:
            await self.es_client.close()
            logger.info("Elasticsearch client closed")


class OptimizedDatabaseQueries:
    """Optimized database query patterns for better performance."""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.conn_manager = connection_manager
    
    @lru_cache(maxsize=1000)
    def _get_prepared_query(self, query_key: str) -> str:
        """Cache prepared queries to reduce parsing overhead."""
        queries = {
            'get_user_files': """
                SELECT f.id, f.name, f.size, f.created_at, f.updated_at
                FROM files f
                WHERE f.user_id = $1 AND f.deleted_at IS NULL
                ORDER BY f.updated_at DESC
                LIMIT $2 OFFSET $3
            """,
            'get_file_with_metadata': """
                SELECT f.*, fm.metadata
                FROM files f
                LEFT JOIN file_metadata fm ON f.id = fm.file_id
                WHERE f.id = $1 AND f.deleted_at IS NULL
            """,
            'bulk_insert_files': """
                INSERT INTO files (id, name, user_id, size, content_type, created_at)
                SELECT * FROM unnest($1::uuid[], $2::text[], $3::uuid[], $4::bigint[], $5::text[], $6::timestamptz[])
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    size = EXCLUDED.size,
                    updated_at = NOW()
                RETURNING id
            """
        }
        return queries.get(query_key, "")
    
    async def get_user_files_optimized(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list:
        """Optimized query to get user files with pagination."""
        query = self._get_prepared_query('get_user_files')
        
        async with self.conn_manager.get_postgres_connection() as conn:
            # Use prepared statement for better performance
            stmt = await conn.prepare(query)
            rows = await stmt.fetch(user_id, limit, offset)
            return [dict(row) for row in rows]
    
    async def bulk_cache_user_data(self, user_id: str, cache_duration: int = 3600):
        """Cache frequently accessed user data in Redis."""
        async with self.conn_manager.get_redis_connection() as redis:
            # Cache user's recent files
            files = await self.get_user_files_optimized(user_id, limit=20)
            await redis.setex(
                f"user_files:{user_id}",
                cache_duration,
                str(files)  # In production, use proper serialization
            )
            
            # Cache user preferences
            async with self.conn_manager.get_postgres_connection() as conn:
                preferences = await conn.fetchrow(
                    "SELECT * FROM user_preferences WHERE user_id = $1",
                    user_id
                )
                if preferences:
                    await redis.setex(
                        f"user_prefs:{user_id}",
                        cache_duration,
                        str(dict(preferences))
                    )


# Global connection manager instance
db_manager = DatabaseConnectionManager()


async def initialize_all_connections(
    postgres_url: str,
    redis_url: str,
    elasticsearch_hosts: list
):
    """Initialize all database connections with optimized settings."""
    await db_manager.initialize_postgres_pool(postgres_url)
    await db_manager.initialize_redis_pool(redis_url)
    await db_manager.initialize_elasticsearch_client(elasticsearch_hosts)
    
    logger.info("All database connections initialized successfully")
    return db_manager


async def get_connection_manager() -> DatabaseConnectionManager:
    """Get the global connection manager instance."""
    return db_manager