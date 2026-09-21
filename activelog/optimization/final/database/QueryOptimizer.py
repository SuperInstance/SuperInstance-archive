"""
Advanced Database Query Optimization System
Provides connection pooling, query caching, and performance monitoring
"""

import asyncio
import asyncpg
import redis
import hashlib
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager
from functools import wraps

@dataclass
class QueryStats:
    query_hash: str
    execution_time: float
    cache_hit: bool
    rows_returned: int
    timestamp: float

@dataclass
class ConnectionPoolConfig:
    min_size: int = 5
    max_size: int 20
    max_queries: int = 50000
    max_inactive_connection_lifetime: int = 300

class QueryOptimizer:
    def __init__(self, 
                 database_url: str, 
                 redis_url: str = None,
                 pool_config: ConnectionPoolConfig = None,
                 enable_caching: bool = True,
                 cache_ttl: int = 300):
        
        self.database_url = database_url
        self.redis_url = redis_url
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self.pool_config = pool_config or ConnectionPoolConfig()
        
        self.pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.query_stats: Dict[str, QueryStats] = {}
        self.prepared_statements: Dict[str, str] = {}
        
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize connection pool and cache"""
        # Initialize PostgreSQL connection pool
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=self.pool_config.min_size,
            max_size=self.pool_config.max_size,
            max_queries=self.pool_config.max_queries,
            max_inactive_connection_lifetime=self.pool_config.max_inactive_connection_lifetime,
            init=self._init_connection
        )
        
        # Initialize Redis cache if URL provided
        if self.redis_url and self.enable_caching:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
        self.logger.info("✅ Database query optimizer initialized")

    async def _init_connection(self, conn):
        """Initialize each new connection"""
        # Set optimal connection parameters
        await conn.execute("SET statement_timeout = '30s'")
        await conn.execute("SET lock_timeout = '10s'")
        await conn.execute("SET idle_in_transaction_session_timeout = '5min'")
        
        # Enable query planning optimizations
        await conn.execute("SET enable_seqscan = off")  # Prefer index scans
        await conn.execute("SET random_page_cost = 1.1")  # SSD optimization
        await conn.execute("SET effective_cache_size = '4GB'")

    def _hash_query(self, query: str, params: tuple = None) -> str:
        """Generate hash for query caching"""
        query_string = f"{query}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.md5(query_string.encode()).hexdigest()

    async def _get_cached_result(self, query_hash: str) -> Optional[List[Dict]]:
        """Get cached query result"""
        if not self.redis_client:
            return None
            
        try:
            cached = await self.redis_client.get(f"query:{query_hash}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            self.logger.warning(f"Cache read error: {e}")
        
        return None

    async def _cache_result(self, query_hash: str, result: List[Dict]):
        """Cache query result"""
        if not self.redis_client:
            return
            
        try:
            await self.redis_client.setex(
                f"query:{query_hash}", 
                self.cache_ttl, 
                json.dumps(result, default=str)
            )
        except Exception as e:
            self.logger.warning(f"Cache write error: {e}")

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")
        
        async with self.pool.acquire() as connection:
            yield connection

    async def execute_query(self, 
                          query: str, 
                          params: tuple = None,
                          cache: bool = True,
                          fetch_all: bool = True) -> Tuple[List[Dict], QueryStats]:
        """Execute optimized query with caching and monitoring"""
        start_time = time.time()
        query_hash = self._hash_query(query, params)
        cache_hit = False
        result = []
        
        # Try cache first
        if cache and self.enable_caching:
            cached_result = await self._get_cached_result(query_hash)
            if cached_result is not None:
                cache_hit = True
                result = cached_result
        
        # Execute query if not cached
        if not cache_hit:
            async with self.get_connection() as conn:
                if params:
                    if fetch_all:
                        rows = await conn.fetch(query, *params)
                    else:
                        row = await conn.fetchrow(query, *params)
                        rows = [row] if row else []
                else:
                    if fetch_all:
                        rows = await conn.fetch(query)
                    else:
                        row = await conn.fetchrow(query)
                        rows = [row] if row else []
                
                # Convert to dictionaries
                result = [dict(row) for row in rows] if rows else []
                
                # Cache result if enabled
                if cache and self.enable_caching and result:
                    await self._cache_result(query_hash, result)
        
        # Record statistics
        execution_time = time.time() - start_time
        stats = QueryStats(
            query_hash=query_hash,
            execution_time=execution_time,
            cache_hit=cache_hit,
            rows_returned=len(result),
            timestamp=time.time()
        )
        
        self.query_stats[query_hash] = stats
        
        return result, stats

    async def execute_batch(self, queries: List[Tuple[str, tuple]]) -> List[Tuple[List[Dict], QueryStats]]:
        """Execute multiple queries in batch for better performance"""
        results = []
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                for query, params in queries:
                    result, stats = await self.execute_query(query, params, cache=False)
                    results.append((result, stats))
        
        return results

    async def prepare_statement(self, name: str, query: str):
        """Prepare frequently used statements for better performance"""
        async with self.get_connection() as conn:
            await conn.prepare(query)
            self.prepared_statements[name] = query

    async def execute_prepared(self, name: str, params: tuple = None) -> Tuple[List[Dict], QueryStats]:
        """Execute prepared statement"""
        if name not in self.prepared_statements:
            raise ValueError(f"Prepared statement '{name}' not found")
        
        query = self.prepared_statements[name]
        return await self.execute_query(query, params, cache=True)

    # Specialized query methods for common patterns
    
    async def find_by_id(self, table: str, id_value: Any, id_column: str = 'id') -> Optional[Dict]:
        """Optimized single record lookup"""
        query = f"SELECT * FROM {table} WHERE {id_column} = $1 LIMIT 1"
        result, _ = await self.execute_query(query, (id_value,), fetch_all=False)
        return result[0] if result else None

    async def paginated_query(self, 
                            base_query: str, 
                            params: tuple = None,
                            page: int = 1, 
                            page_size: int = 20,
                            order_by: str = "id DESC") -> Dict[str, Any]:
        """Execute paginated query with count"""
        offset = (page - 1) * page_size
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subq"
        count_result, _ = await self.execute_query(count_query, params)
        total = count_result[0]['total'] if count_result else 0
        
        # Get paginated results
        paginated_query = f"""
            {base_query} 
            ORDER BY {order_by} 
            LIMIT {page_size} OFFSET {offset}
        """
        results, stats = await self.execute_query(paginated_query, params)
        
        return {
            'data': results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'pages': (total + page_size - 1) // page_size
            },
            'stats': stats
        }

    async def bulk_insert(self, table: str, records: List[Dict], chunk_size: int = 1000):
        """Optimized bulk insert using COPY"""
        if not records:
            return
        
        columns = list(records[0].keys())
        
        async with self.get_connection() as conn:
            # Process in chunks to avoid memory issues
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                
                # Prepare data for COPY
                data = []
                for record in chunk:
                    row = [record.get(col) for col in columns]
                    data.append(row)
                
                # Use COPY for maximum performance
                await conn.copy_records_to_table(table, records=data, columns=columns)

    async def upsert(self, table: str, record: Dict, conflict_columns: List[str]):
        """Optimized upsert using ON CONFLICT"""
        columns = list(record.keys())
        values_placeholder = ', '.join([f'${i+1}' for i in range(len(columns))])
        conflict_cols = ', '.join(conflict_columns)
        
        update_clause = ', '.join([
            f"{col} = EXCLUDED.{col}" 
            for col in columns if col not in conflict_columns
        ])
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)}) 
            VALUES ({values_placeholder})
            ON CONFLICT ({conflict_cols}) 
            DO UPDATE SET {update_clause}
            RETURNING *
        """
        
        params = tuple(record[col] for col in columns)
        return await self.execute_query(query, params, fetch_all=False)

    # Analytics and monitoring methods
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query statistics"""
        if not self.query_stats:
            return {}
        
        stats = list(self.query_stats.values())
        
        return {
            'total_queries': len(stats),
            'cache_hit_rate': sum(1 for s in stats if s.cache_hit) / len(stats),
            'average_execution_time': sum(s.execution_time for s in stats) / len(stats),
            'slowest_queries': sorted(stats, key=lambda s: s.execution_time, reverse=True)[:5],
            'most_frequent_queries': self._get_most_frequent_queries()
        }

    def _get_most_frequent_queries(self) -> List[Dict]:
        """Get most frequently executed queries"""
        query_counts = {}
        for stat in self.query_stats.values():
            query_counts[stat.query_hash] = query_counts.get(stat.query_hash, 0) + 1
        
        return sorted(
            [{'query_hash': qh, 'count': count} for qh, count in query_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]

    async def analyze_slow_queries(self, min_duration: float = 1.0) -> List[Dict]:
        """Analyze slow queries for optimization opportunities"""
        slow_queries = []
        
        async with self.get_connection() as conn:
            # Get slow queries from pg_stat_statements if available
            slow_query_sql = """
                SELECT query, calls, total_time, mean_time, rows
                FROM pg_stat_statements 
                WHERE mean_time > $1
                ORDER BY mean_time DESC
                LIMIT 20
            """
            
            try:
                result = await conn.fetch(slow_query_sql, min_duration * 1000)  # Convert to ms
                slow_queries = [dict(row) for row in result]
            except Exception:
                # pg_stat_statements not available, use our internal stats
                for stats in self.query_stats.values():
                    if stats.execution_time > min_duration:
                        slow_queries.append({
                            'query_hash': stats.query_hash,
                            'execution_time': stats.execution_time,
                            'cache_hit': stats.cache_hit
                        })
        
        return slow_queries

    async def optimize_table(self, table_name: str):
        """Run optimization operations on a table"""
        async with self.get_connection() as conn:
            # Update statistics
            await conn.execute(f"ANALYZE {table_name}")
            
            # Vacuum if needed
            await conn.execute(f"VACUUM (ANALYZE) {table_name}")
            
            self.logger.info(f"✅ Optimized table: {table_name}")

    async def create_missing_indexes(self, suggestions: List[Dict]):
        """Create indexes based on query analysis"""
        async with self.get_connection() as conn:
            for suggestion in suggestions:
                try:
                    await conn.execute(suggestion['create_sql'])
                    self.logger.info(f"✅ Created index: {suggestion['index_name']}")
                except Exception as e:
                    self.logger.error(f"❌ Failed to create index: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        if self.pool:
            await self.pool.close()
        
        if self.redis_client:
            await self.redis_client.close()

# Decorator for automatic query optimization
def optimized_query(cache=True, timeout=30):
    """Decorator to automatically optimize database queries"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Implementation would depend on the specific ORM/database library
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Example usage and integration
class DatabaseService:
    def __init__(self, optimizer: QueryOptimizer):
        self.optimizer = optimizer

    @optimized_query(cache=True)
    async def get_user_profile(self, user_id: int) -> Optional[Dict]:
        return await self.optimizer.find_by_id('users', user_id)

    @optimized_query(cache=True)
    async def get_recent_files(self, user_id: int, limit: int = 20) -> List[Dict]:
        query = """
            SELECT f.*, u.username 
            FROM files f 
            JOIN users u ON f.user_id = u.id 
            WHERE f.user_id = $1 
            ORDER BY f.created_at DESC 
            LIMIT $2
        """
        result, _ = await self.optimizer.execute_query(query, (user_id, limit))
        return result

    async def search_files(self, 
                          query: str, 
                          user_id: int, 
                          page: int = 1, 
                          page_size: int = 20) -> Dict:
        search_query = """
            SELECT f.*, ts_rank(search_vector, plainto_tsquery($1)) as rank
            FROM files f
            WHERE f.user_id = $2 
            AND search_vector @@ plainto_tsquery($1)
        """
        
        return await self.optimizer.paginated_query(
            search_query, 
            (query, user_id), 
            page, 
            page_size,
            order_by="rank DESC, created_at DESC"
        )