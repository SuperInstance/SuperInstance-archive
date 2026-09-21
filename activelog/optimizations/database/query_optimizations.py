"""
Advanced database query optimizations for ActiveLog.
Includes query patterns, indexing strategies, and performance monitoring.
"""
import asyncio
from typing import Dict, List, Any, Optional, Union
import asyncpg
import time
import json
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class QueryPerformanceMetrics:
    query_type: QueryType
    execution_time: float
    rows_affected: int
    query_hash: str
    timestamp: float


class QueryOptimizer:
    """Advanced query optimization and performance monitoring."""
    
    def __init__(self):
        self.query_cache = {}
        self.performance_metrics: List[QueryPerformanceMetrics] = []
        self.slow_query_threshold = 1.0  # seconds
    
    def get_optimized_indexes(self) -> List[str]:
        """Return SQL statements for creating optimized indexes."""
        return [
            # User-related indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active ON users(email) WHERE deleted_at IS NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at DESC);",
            
            # File-related indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_user_id_active ON files(user_id) WHERE deleted_at IS NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_user_updated ON files(user_id, updated_at DESC) WHERE deleted_at IS NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_content_type ON files(content_type) WHERE deleted_at IS NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_size ON files(size DESC) WHERE deleted_at IS NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_search ON files USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));",
            
            # File versions indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_versions_file_id ON file_versions(file_id, version_number DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_versions_created ON file_versions(created_at DESC);",
            
            # Metadata indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_metadata_file_id ON file_metadata(file_id);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_metadata_gin ON file_metadata USING gin(metadata);",
            
            # Activity logs indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_logs_user_time ON activity_logs(user_id, created_at DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_logs_action ON activity_logs(action, created_at DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_logs_resource ON activity_logs(resource_type, resource_id);",
            
            # Sync sessions indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_sessions_user_device ON sync_sessions(user_id, device_id);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_sessions_status ON sync_sessions(status) WHERE status IN ('active', 'syncing');",
            
            # AI analysis indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_analysis_file_id ON ai_analysis(file_id);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_analysis_type_status ON ai_analysis(analysis_type, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_analysis_created ON ai_analysis(created_at DESC);",
            
            # Sharing indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_shares_file_id ON file_shares(file_id) WHERE deleted_at IS NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_shares_shared_with ON file_shares(shared_with) WHERE deleted_at IS NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_shares_expires ON file_shares(expires_at) WHERE expires_at IS NOT NULL;",
            
            # Partial indexes for common queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_recent_active ON files(updated_at DESC, user_id) WHERE deleted_at IS NULL AND updated_at > NOW() - INTERVAL '30 days';",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_large_files ON files(size DESC, user_id) WHERE size > 10485760 AND deleted_at IS NULL;", # > 10MB
        ]
    
    def get_optimized_queries(self) -> Dict[str, str]:
        """Return collection of optimized query patterns."""
        return {
            # Optimized file listing with metadata
            'list_files_with_metadata': """
                WITH file_stats AS (
                    SELECT 
                        f.id, f.name, f.size, f.content_type,
                        f.created_at, f.updated_at,
                        fm.metadata,
                        COUNT(fv.id) as version_count,
                        MAX(fv.created_at) as last_version_date
                    FROM files f
                    LEFT JOIN file_metadata fm ON f.id = fm.file_id
                    LEFT JOIN file_versions fv ON f.id = fv.file_id
                    WHERE f.user_id = $1 AND f.deleted_at IS NULL
                    GROUP BY f.id, f.name, f.size, f.content_type, 
                             f.created_at, f.updated_at, fm.metadata
                    ORDER BY f.updated_at DESC
                    LIMIT $2 OFFSET $3
                )
                SELECT * FROM file_stats;
            """,
            
            # Optimized search with full-text search
            'search_files_fulltext': """
                SELECT f.id, f.name, f.size, f.content_type, f.updated_at,
                       ts_rank(to_tsvector('english', f.name || ' ' || COALESCE(f.description, '')), 
                               plainto_tsquery('english', $2)) as relevance
                FROM files f
                WHERE f.user_id = $1 
                  AND f.deleted_at IS NULL
                  AND to_tsvector('english', f.name || ' ' || COALESCE(f.description, '')) 
                      @@ plainto_tsquery('english', $2)
                ORDER BY relevance DESC, f.updated_at DESC
                LIMIT $3 OFFSET $4;
            """,
            
            # Optimized user dashboard data
            'user_dashboard_summary': """
                WITH user_stats AS (
                    SELECT 
                        COUNT(*) as total_files,
                        SUM(size) as total_size,
                        COUNT(*) FILTER (WHERE updated_at > NOW() - INTERVAL '7 days') as recent_files,
                        COUNT(DISTINCT content_type) as file_types
                    FROM files
                    WHERE user_id = $1 AND deleted_at IS NULL
                ),
                recent_activity AS (
                    SELECT action, COUNT(*) as count
                    FROM activity_logs
                    WHERE user_id = $1 AND created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY action
                    ORDER BY count DESC
                    LIMIT 5
                ),
                storage_by_type AS (
                    SELECT content_type, SUM(size) as size_used, COUNT(*) as count
                    FROM files
                    WHERE user_id = $1 AND deleted_at IS NULL
                    GROUP BY content_type
                    ORDER BY size_used DESC
                    LIMIT 10
                )
                SELECT 
                    (SELECT row_to_json(user_stats) FROM user_stats) as stats,
                    (SELECT json_agg(recent_activity) FROM recent_activity) as recent_activity,
                    (SELECT json_agg(storage_by_type) FROM storage_by_type) as storage_breakdown;
            """,
            
            # Optimized batch file operations
            'batch_update_file_metadata': """
                UPDATE files 
                SET metadata = data_table.metadata,
                    updated_at = NOW()
                FROM (
                    SELECT unnest($1::uuid[]) as id,
                           unnest($2::jsonb[]) as metadata
                ) as data_table
                WHERE files.id = data_table.id
                  AND files.user_id = $3
                  AND files.deleted_at IS NULL
                RETURNING files.id, files.updated_at;
            """,
            
            # Optimized file sharing queries
            'get_shared_files': """
                SELECT f.id, f.name, f.size, f.content_type, f.updated_at,
                       fs.permissions, fs.shared_by, fs.expires_at,
                       u.name as shared_by_name
                FROM file_shares fs
                JOIN files f ON fs.file_id = f.id
                JOIN users u ON fs.shared_by = u.id
                WHERE fs.shared_with = $1 
                  AND fs.deleted_at IS NULL
                  AND f.deleted_at IS NULL
                  AND (fs.expires_at IS NULL OR fs.expires_at > NOW())
                ORDER BY fs.created_at DESC
                LIMIT $2 OFFSET $3;
            """,
            
            # Optimized analytics queries
            'file_access_analytics': """
                WITH daily_access AS (
                    SELECT 
                        DATE(al.created_at) as access_date,
                        COUNT(*) as access_count,
                        COUNT(DISTINCT al.user_id) as unique_users
                    FROM activity_logs al
                    WHERE al.resource_id = $1
                      AND al.action IN ('file_view', 'file_download')
                      AND al.created_at >= $2
                    GROUP BY DATE(al.created_at)
                    ORDER BY access_date DESC
                )
                SELECT 
                    json_agg(daily_access ORDER BY access_date DESC) as daily_stats,
                    (SELECT COUNT(*) FROM daily_access) as total_days,
                    (SELECT SUM(access_count) FROM daily_access) as total_access,
                    (SELECT AVG(access_count) FROM daily_access) as avg_daily_access;
            """
        }
    
    async def execute_with_monitoring(
        self,
        connection: asyncpg.Connection,
        query: str,
        *args,
        query_type: QueryType = QueryType.SELECT
    ) -> Any:
        """Execute query with performance monitoring."""
        start_time = time.time()
        query_hash = str(hash(query))
        
        try:
            if query_type == QueryType.SELECT:
                result = await connection.fetch(query, *args)
                rows_affected = len(result) if result else 0
            else:
                result = await connection.execute(query, *args)
                rows_affected = int(result.split()[-1]) if result else 0
            
            execution_time = time.time() - start_time
            
            # Record metrics
            metrics = QueryPerformanceMetrics(
                query_type=query_type,
                execution_time=execution_time,
                rows_affected=rows_affected,
                query_hash=query_hash,
                timestamp=start_time
            )
            self.performance_metrics.append(metrics)
            
            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning(
                    f"Slow query detected: {execution_time:.3f}s, "
                    f"rows: {rows_affected}, hash: {query_hash}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def create_optimized_indexes(self, connection: asyncpg.Connection):
        """Create all optimized indexes."""
        indexes = self.get_optimized_indexes()
        
        for index_sql in indexes:
            try:
                await connection.execute(index_sql)
                logger.info(f"Created index: {index_sql[:50]}...")
            except Exception as e:
                if "already exists" in str(e):
                    logger.debug(f"Index already exists: {index_sql[:50]}...")
                else:
                    logger.error(f"Failed to create index: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report from collected metrics."""
        if not self.performance_metrics:
            return {"message": "No metrics collected"}
        
        total_queries = len(self.performance_metrics)
        avg_time = sum(m.execution_time for m in self.performance_metrics) / total_queries
        slow_queries = [m for m in self.performance_metrics if m.execution_time > self.slow_query_threshold]
        
        query_type_stats = {}
        for metric in self.performance_metrics:
            qt = metric.query_type.value
            if qt not in query_type_stats:
                query_type_stats[qt] = {'count': 0, 'total_time': 0, 'avg_time': 0}
            
            query_type_stats[qt]['count'] += 1
            query_type_stats[qt]['total_time'] += metric.execution_time
            query_type_stats[qt]['avg_time'] = query_type_stats[qt]['total_time'] / query_type_stats[qt]['count']
        
        return {
            'total_queries': total_queries,
            'average_execution_time': round(avg_time, 3),
            'slow_queries_count': len(slow_queries),
            'slow_queries_threshold': self.slow_query_threshold,
            'query_type_breakdown': query_type_stats,
            'slowest_queries': sorted(
                [{'time': m.execution_time, 'hash': m.query_hash} for m in slow_queries],
                key=lambda x: x['time'],
                reverse=True
            )[:10]
        }
    
    def clear_metrics(self):
        """Clear collected performance metrics."""
        self.performance_metrics.clear()


class BulkOperationOptimizer:
    """Optimizations for bulk database operations."""
    
    @staticmethod
    async def bulk_insert_files(
        connection: asyncpg.Connection,
        files_data: List[Dict[str, Any]]
    ) -> List[str]:
        """Optimized bulk file insertion."""
        if not files_data:
            return []
        
        # Prepare data for bulk insert
        ids = [f['id'] for f in files_data]
        names = [f['name'] for f in files_data]
        user_ids = [f['user_id'] for f in files_data]
        sizes = [f['size'] for f in files_data]
        content_types = [f['content_type'] for f in files_data]
        created_ats = [f.get('created_at', 'NOW()') for f in files_data]
        
        query = """
            INSERT INTO files (id, name, user_id, size, content_type, created_at)
            SELECT * FROM unnest($1::uuid[], $2::text[], $3::uuid[], 
                                $4::bigint[], $5::text[], $6::timestamptz[])
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                size = EXCLUDED.size,
                updated_at = NOW()
            RETURNING id;
        """
        
        result = await connection.fetch(
            query, ids, names, user_ids, sizes, content_types, created_ats
        )
        return [str(row['id']) for row in result]
    
    @staticmethod
    async def bulk_update_file_access_time(
        connection: asyncpg.Connection,
        file_ids: List[str],
        user_id: str
    ):
        """Bulk update file access times efficiently."""
        if not file_ids:
            return
        
        query = """
            UPDATE files 
            SET last_accessed_at = NOW()
            WHERE id = ANY($1::uuid[]) 
              AND user_id = $2 
              AND deleted_at IS NULL;
        """
        
        await connection.execute(query, file_ids, user_id)


# Global optimizer instance
query_optimizer = QueryOptimizer()


def get_query_optimizer() -> QueryOptimizer:
    """Get the global query optimizer instance."""
    return query_optimizer