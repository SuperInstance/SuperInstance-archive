"""
Database management for Batch Import Service
"""

import asyncio
import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime

from .config import settings
from .logging import logger


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=settings.DATABASE_POOL_MIN,
                max_size=settings.DATABASE_POOL_MAX
            )
            
            # Create tables if they don't exist
            await self._create_tables()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connections closed")
    
    async def _create_tables(self):
        """Create necessary tables for batch import tracking"""
        
        create_import_batches_sql = """
        CREATE TABLE IF NOT EXISTS import_batches (
            batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            total_files INTEGER NOT NULL DEFAULT 0,
            processed_files INTEGER NOT NULL DEFAULT 0,
            successful_files INTEGER NOT NULL DEFAULT 0,
            failed_files INTEGER NOT NULL DEFAULT 0,
            duplicate_files INTEGER NOT NULL DEFAULT 0,
            start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            end_time TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        create_import_files_sql = """
        CREATE TABLE IF NOT EXISTS import_files (
            file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            batch_id UUID REFERENCES import_batches(batch_id) ON DELETE CASCADE,
            original_path TEXT NOT NULL,
            filename VARCHAR(255) NOT NULL,
            file_size BIGINT NOT NULL,
            file_hash VARCHAR(64),
            mime_type VARCHAR(100),
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            minio_path TEXT,
            metadata JSONB,
            thumbnails JSONB,
            error_message TEXT,
            processing_start TIMESTAMP WITH TIME ZONE,
            processing_end TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        create_file_hashes_sql = """
        CREATE TABLE IF NOT EXISTS file_hashes (
            hash_value VARCHAR(64) PRIMARY KEY,
            file_id UUID REFERENCES import_files(file_id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            file_size BIGINT NOT NULL,
            minio_path TEXT NOT NULL,
            first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        create_indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_import_batches_status ON import_batches(status);",
            "CREATE INDEX IF NOT EXISTS idx_import_batches_created ON import_batches(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_import_files_batch ON import_files(batch_id);",
            "CREATE INDEX IF NOT EXISTS idx_import_files_status ON import_files(status);",
            "CREATE INDEX IF NOT EXISTS idx_import_files_hash ON import_files(file_hash);",
            "CREATE INDEX IF NOT EXISTS idx_file_hashes_hash ON file_hashes(hash_value);"
        ]
        
        async with self.pool.acquire() as conn:
            await conn.execute(create_import_batches_sql)
            await conn.execute(create_import_files_sql)
            await conn.execute(create_file_hashes_sql)
            
            for index_sql in create_indexes_sql:
                await conn.execute(index_sql)
                
        logger.info("Database tables created successfully")
    
    async def create_batch(self, total_files: int) -> str:
        """Create a new import batch"""
        async with self.pool.acquire() as conn:
            batch_id = await conn.fetchval("""
                INSERT INTO import_batches (total_files, status)
                VALUES ($1, 'processing') 
                RETURNING batch_id
            """, total_files)
            
        logger.info("Created import batch", batch_id=str(batch_id), total_files=total_files)
        return str(batch_id)
    
    async def add_file_to_batch(self, batch_id: str, file_path: str, filename: str, 
                               file_size: int, file_hash: str, mime_type: str) -> str:
        """Add a file to an import batch"""
        async with self.pool.acquire() as conn:
            file_id = await conn.fetchval("""
                INSERT INTO import_files (
                    batch_id, original_path, filename, file_size, file_hash, mime_type
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING file_id
            """, batch_id, file_path, filename, file_size, file_hash, mime_type)
            
        return str(file_id)
    
    async def update_file_status(self, file_id: str, status: str, 
                                minio_path: Optional[str] = None,
                                metadata: Optional[Dict] = None,
                                thumbnails: Optional[Dict] = None,
                                error_message: Optional[str] = None):
        """Update file processing status"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE import_files 
                SET status = $1, minio_path = $2, metadata = $3, thumbnails = $4,
                    error_message = $5, processing_end = NOW(), updated_at = NOW()
                WHERE file_id = $6
            """, status, minio_path, metadata, thumbnails, error_message, file_id)
    
    async def start_file_processing(self, file_id: str):
        """Mark file as started processing"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE import_files 
                SET status = 'processing', processing_start = NOW(), updated_at = NOW()
                WHERE file_id = $1
            """, file_id)
    
    async def update_batch_stats(self, batch_id: str):
        """Update batch statistics from file statuses"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as processed,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'duplicate' THEN 1 END) as duplicate
                FROM import_files 
                WHERE batch_id = $1 AND status IN ('completed', 'failed', 'duplicate')
            """, batch_id)
            
            await conn.execute("""
                UPDATE import_batches 
                SET processed_files = $1, successful_files = $2, 
                    failed_files = $3, duplicate_files = $4, updated_at = NOW()
                WHERE batch_id = $5
            """, stats['processed'], stats['successful'], stats['failed'], 
                stats['duplicate'], batch_id)
    
    async def complete_batch(self, batch_id: str, status: str = 'completed'):
        """Mark batch as completed"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE import_batches 
                SET status = $1, end_time = NOW(), updated_at = NOW()
                WHERE batch_id = $2
            """, status, batch_id)
    
    async def check_file_hash(self, file_hash: str) -> Optional[Dict]:
        """Check if file hash already exists"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT hash_value, filename, file_size, minio_path, first_seen
                FROM file_hashes 
                WHERE hash_value = $1
            """, file_hash)
            
            return dict(result) if result else None
    
    async def record_file_hash(self, file_hash: str, file_id: str, filename: str,
                              file_size: int, minio_path: str):
        """Record file hash for duplicate detection"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO file_hashes (hash_value, file_id, filename, file_size, minio_path)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (hash_value) DO NOTHING
            """, file_hash, file_id, filename, file_size, minio_path)
    
    async def get_batch_report(self, batch_id: str) -> Optional[Dict]:
        """Get detailed batch report"""
        async with self.pool.acquire() as conn:
            batch_info = await conn.fetchrow("""
                SELECT * FROM import_batches WHERE batch_id = $1
            """, batch_id)
            
            if not batch_info:
                return None
            
            files = await conn.fetch("""
                SELECT file_id, filename, file_size, status, minio_path, 
                       error_message, processing_start, processing_end
                FROM import_files 
                WHERE batch_id = $1
                ORDER BY created_at
            """, batch_id)
            
            return {
                "batch": dict(batch_info),
                "files": [dict(file) for file in files]
            }
    
    async def get_recent_batches(self, limit: int = 10) -> List[Dict]:
        """Get recent import batches"""
        async with self.pool.acquire() as conn:
            batches = await conn.fetch("""
                SELECT batch_id, status, total_files, processed_files, 
                       successful_files, failed_files, duplicate_files,
                       start_time, end_time
                FROM import_batches 
                ORDER BY created_at DESC 
                LIMIT $1
            """, limit)
            
            return [dict(batch) for batch in batches]


# Global database manager instance
db_manager = DatabaseManager()