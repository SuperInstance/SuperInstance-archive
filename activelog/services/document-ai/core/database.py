"""
Database manager for document AI service
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import json

from .config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations for document AI service"""
    
    def __init__(self):
        self.pool = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.database.url,
                min_size=2,
                max_size=settings.database.pool_size,
                command_timeout=60,
                server_settings={
                    'application_name': 'activelog_document_ai'
                }
            )
            
            # Create document processing specific tables
            await self._create_tables()
            
            self._initialized = True
            logger.info("Database connection pool initialized")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            if not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, *args) -> List[Dict]:
        """Execute a query and return results as list of dicts"""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_scalar(self, query: str, *args) -> Any:
        """Execute a query and return single value"""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute_command(self, query: str, *args) -> str:
        """Execute a command (INSERT, UPDATE, DELETE) and return status"""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_all(self, query: str, *args) -> List:
        """Fetch all rows from query"""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)
    
    async def _create_tables(self):
        """Create document processing specific tables"""
        
        async with self.get_connection() as conn:
            
            # Document processing jobs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_processing_jobs (
                    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(100),
                    tenant_id VARCHAR(100),
                    original_filename VARCHAR(500) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size BIGINT NOT NULL,
                    mime_type VARCHAR(100),
                    file_hash VARCHAR(64),
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    error_message TEXT,
                    processing_options JSONB,
                    results JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Document metadata table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_metadata (
                    metadata_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    page_count INTEGER,
                    word_count INTEGER,
                    character_count INTEGER,
                    language VARCHAR(10),
                    detected_languages JSONB,
                    document_type VARCHAR(50),
                    confidence_score FLOAT,
                    creation_date TIMESTAMP,
                    modification_date TIMESTAMP,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Document classification results table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_classifications (
                    classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    document_type VARCHAR(50) NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    classification_method VARCHAR(50),
                    features_used JSONB,
                    model_version VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Named entity extraction results table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS named_entities (
                    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    entity_text TEXT NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    start_position INTEGER,
                    end_position INTEGER,
                    confidence_score FLOAT,
                    page_number INTEGER,
                    context_text TEXT,
                    normalized_value TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Document summaries table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_summaries (
                    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    summary_type VARCHAR(50) NOT NULL, -- 'extractive', 'abstractive', 'key_points'
                    summary_text TEXT NOT NULL,
                    key_points JSONB,
                    word_count INTEGER,
                    compression_ratio FLOAT,
                    model_used VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Extracted text table (page-by-page)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS extracted_text (
                    text_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    page_number INTEGER NOT NULL,
                    extraction_method VARCHAR(50), -- 'pypdf2', 'tesseract', 'combined'
                    raw_text TEXT,
                    cleaned_text TEXT,
                    confidence_score FLOAT,
                    language VARCHAR(10),
                    word_count INTEGER,
                    bounding_boxes JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Tables extracted from documents
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS extracted_tables (
                    table_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    page_number INTEGER NOT NULL,
                    table_index INTEGER NOT NULL,
                    extraction_method VARCHAR(50),
                    raw_table_data JSONB,
                    structured_data JSONB,
                    column_headers JSONB,
                    row_count INTEGER,
                    column_count INTEGER,
                    confidence_score FLOAT,
                    bounding_box JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Vector embeddings table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_embeddings (
                    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    chunk_id INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding_vector VECTOR(384), -- Adjust dimension based on model
                    embedding_model VARCHAR(100),
                    page_number INTEGER,
                    start_position INTEGER,
                    end_position INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Semantic search results cache
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_search_cache (
                    cache_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    query_hash VARCHAR(64) NOT NULL,
                    query_text TEXT NOT NULL,
                    results JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours'
                )
            """)
            
            # Document relationships (for linked documents)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_relationships (
                    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    source_job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    target_job_id UUID REFERENCES document_processing_jobs(job_id) ON DELETE CASCADE,
                    relationship_type VARCHAR(50), -- 'similar', 'referenced', 'version', 'template'
                    confidence_score FLOAT,
                    similarity_score FLOAT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Processing statistics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_statistics (
                    stat_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    date DATE NOT NULL,
                    document_type VARCHAR(50),
                    processing_method VARCHAR(50),
                    documents_processed INTEGER DEFAULT 0,
                    avg_processing_time FLOAT,
                    success_rate FLOAT,
                    error_count INTEGER DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(date, document_type, processing_method)
                )
            """)
            
            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_jobs_status ON document_processing_jobs(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_jobs_user_id ON document_processing_jobs(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_jobs_created_at ON document_processing_jobs(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_jobs_file_hash ON document_processing_jobs(file_hash)")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_metadata_job_id ON document_metadata(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_metadata_doc_type ON document_metadata(document_type)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_metadata_language ON document_metadata(language)")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_classifications_job_id ON document_classifications(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_classifications_type ON document_classifications(document_type)")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_named_entities_job_id ON named_entities(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_named_entities_type ON named_entities(entity_type)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_named_entities_text ON named_entities USING GIN (to_tsvector('english', entity_text))")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_summaries_job_id ON document_summaries(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_summaries_type ON document_summaries(summary_type)")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_extracted_text_job_id ON extracted_text(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_extracted_text_page ON extracted_text(page_number)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_extracted_text_content ON extracted_text USING GIN (to_tsvector('english', cleaned_text))")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_extracted_tables_job_id ON extracted_tables(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_extracted_tables_page ON extracted_tables(page_number)")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_embeddings_job_id ON document_embeddings(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_embeddings_chunk ON document_embeddings(chunk_id)")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_cache_hash ON semantic_search_cache(query_hash)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_cache_expires ON semantic_search_cache(expires_at)")
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_relationships_source ON document_relationships(source_job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_relationships_target ON document_relationships(target_job_id)")
            
            logger.info("Document AI database tables created/verified")
    
    # Document processing job methods
    async def create_document_job(self, user_id: str, tenant_id: str, filename: str, 
                                file_path: str, file_size: int, mime_type: str,
                                file_hash: str, processing_options: Dict = None) -> str:
        """Create a new document processing job"""
        job_id = await self.execute_scalar("""
            INSERT INTO document_processing_jobs 
            (user_id, tenant_id, original_filename, file_path, file_size, mime_type, file_hash, processing_options)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING job_id
        """, user_id, tenant_id, filename, file_path, file_size, mime_type, file_hash, processing_options or {})
        
        return str(job_id)
    
    async def update_job_status(self, job_id: str, status: str, progress: int = None,
                               error_message: str = None, results: Dict = None):
        """Update document processing job status"""
        if progress is not None:
            await self.execute_command("""
                UPDATE document_processing_jobs 
                SET status = $1, progress = $2, error_message = $3, results = $4,
                    updated_at = NOW(),
                    end_time = CASE WHEN $1 IN ('completed', 'failed') THEN NOW() ELSE end_time END
                WHERE job_id = $5
            """, status, progress, error_message, results, job_id)
        else:
            await self.execute_command("""
                UPDATE document_processing_jobs 
                SET status = $1, error_message = $2, results = $3,
                    updated_at = NOW(),
                    end_time = CASE WHEN $1 IN ('completed', 'failed') THEN NOW() ELSE end_time END
                WHERE job_id = $4
            """, status, error_message, results, job_id)
    
    async def start_job(self, job_id: str):
        """Mark job as started"""
        await self.execute_command("""
            UPDATE document_processing_jobs 
            SET status = 'processing', start_time = NOW(), updated_at = NOW()
            WHERE job_id = $1
        """, job_id)
    
    async def update_job_progress(self, job_id: str, progress: float):
        """Update job progress percentage"""
        await self.execute_command("""
            UPDATE document_processing_jobs 
            SET progress = $1, updated_at = NOW()
            WHERE job_id = $2
        """, int(progress), job_id)
    
    # Metadata methods
    async def save_document_metadata(self, job_id: str, metadata: Dict) -> str:
        """Save document metadata"""
        metadata_id = await self.execute_scalar("""
            INSERT INTO document_metadata 
            (job_id, page_count, word_count, character_count, language, 
             detected_languages, document_type, confidence_score, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING metadata_id
        """, 
        job_id, metadata.get('page_count'), metadata.get('word_count'), 
        metadata.get('character_count'), metadata.get('language'),
        metadata.get('detected_languages'), metadata.get('document_type'),
        metadata.get('confidence_score'), metadata)
        
        return str(metadata_id)
    
    # Classification methods
    async def save_classification(self, job_id: str, document_type: str, confidence: float,
                                method: str, features: Dict = None, model_version: str = None) -> str:
        """Save document classification result"""
        classification_id = await self.execute_scalar("""
            INSERT INTO document_classifications 
            (job_id, document_type, confidence_score, classification_method, features_used, model_version)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING classification_id
        """, job_id, document_type, confidence, method, features or {}, model_version)
        
        return str(classification_id)
    
    # Named entity methods
    async def save_named_entity(self, job_id: str, entity_text: str, entity_type: str,
                               start_pos: int = None, end_pos: int = None, confidence: float = None,
                               page_number: int = None, context: str = None,
                               normalized_value: str = None) -> str:
        """Save named entity"""
        entity_id = await self.execute_scalar("""
            INSERT INTO named_entities 
            (job_id, entity_text, entity_type, start_position, end_position,
             confidence_score, page_number, context_text, normalized_value)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING entity_id
        """, job_id, entity_text, entity_type, start_pos, end_pos, confidence,
             page_number, context, normalized_value)
        
        return str(entity_id)
    
    # Summary methods
    async def save_document_summary(self, job_id: str, summary_type: str, summary_text: str,
                                  key_points: List = None, word_count: int = None,
                                  compression_ratio: float = None, model_used: str = None) -> str:
        """Save document summary"""
        summary_id = await self.execute_scalar("""
            INSERT INTO document_summaries 
            (job_id, summary_type, summary_text, key_points, word_count, 
             compression_ratio, model_used)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING summary_id
        """, job_id, summary_type, summary_text, key_points or [], word_count,
             compression_ratio, model_used)
        
        return str(summary_id)
    
    # Text extraction methods
    async def save_extracted_text(self, job_id: str, page_number: int, method: str,
                                raw_text: str, cleaned_text: str = None, confidence: float = None,
                                language: str = None, word_count: int = None,
                                bounding_boxes: List = None) -> str:
        """Save extracted text"""
        text_id = await self.execute_scalar("""
            INSERT INTO extracted_text 
            (job_id, page_number, extraction_method, raw_text, cleaned_text,
             confidence_score, language, word_count, bounding_boxes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING text_id
        """, job_id, page_number, method, raw_text, cleaned_text or raw_text,
             confidence, language, word_count, bounding_boxes or [])
        
        return str(text_id)
    
    # Table extraction methods
    async def save_extracted_table(self, job_id: str, page_number: int, table_index: int,
                                 method: str, raw_data: Dict, structured_data: Dict,
                                 headers: List = None, row_count: int = None,
                                 column_count: int = None, confidence: float = None,
                                 bounding_box: Dict = None) -> str:
        """Save extracted table"""
        table_id = await self.execute_scalar("""
            INSERT INTO extracted_tables 
            (job_id, page_number, table_index, extraction_method, raw_table_data,
             structured_data, column_headers, row_count, column_count,
             confidence_score, bounding_box)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING table_id
        """, job_id, page_number, table_index, method, raw_data, structured_data,
             headers or [], row_count, column_count, confidence, bounding_box or {})
        
        return str(table_id)
    
    # Query methods
    async def get_job_details(self, job_id: str) -> Optional[Dict]:
        """Get complete job details"""
        jobs = await self.execute_query("""
            SELECT * FROM document_processing_jobs WHERE job_id = $1
        """, job_id)
        
        return jobs[0] if jobs else None
    
    async def get_job_metadata(self, job_id: str) -> Optional[Dict]:
        """Get job metadata"""
        results = await self.execute_query("""
            SELECT * FROM document_metadata WHERE job_id = $1
        """, job_id)
        
        return results[0] if results else None
    
    async def get_job_classifications(self, job_id: str) -> List[Dict]:
        """Get job classifications"""
        return await self.execute_query("""
            SELECT * FROM document_classifications WHERE job_id = $1
            ORDER BY confidence_score DESC
        """, job_id)
    
    async def get_job_entities(self, job_id: str) -> List[Dict]:
        """Get named entities for a job"""
        return await self.execute_query("""
            SELECT * FROM named_entities WHERE job_id = $1
            ORDER BY page_number, start_position
        """, job_id)
    
    async def get_job_summaries(self, job_id: str) -> List[Dict]:
        """Get summaries for a job"""
        return await self.execute_query("""
            SELECT * FROM document_summaries WHERE job_id = $1
            ORDER BY summary_type
        """, job_id)
    
    async def get_job_extracted_text(self, job_id: str) -> List[Dict]:
        """Get extracted text for a job"""
        return await self.execute_query("""
            SELECT * FROM extracted_text WHERE job_id = $1
            ORDER BY page_number
        """, job_id)
    
    async def get_job_tables(self, job_id: str) -> List[Dict]:
        """Get extracted tables for a job"""
        return await self.execute_query("""
            SELECT * FROM extracted_tables WHERE job_id = $1
            ORDER BY page_number, table_index
        """, job_id)
    
    # Search methods
    async def search_documents_by_content(self, query: str, document_type: str = None,
                                        user_id: str = None, limit: int = 50) -> List[Dict]:
        """Search documents by text content"""
        base_query = """
            SELECT DISTINCT dpj.job_id, dpj.original_filename, dpj.created_at,
                   dm.document_type, dm.confidence_score, et.page_number,
                   ts_headline('english', et.cleaned_text, plainto_tsquery($1)) as highlight
            FROM document_processing_jobs dpj
            JOIN document_metadata dm ON dpj.job_id = dm.job_id
            JOIN extracted_text et ON dpj.job_id = et.job_id
            WHERE to_tsvector('english', et.cleaned_text) @@ plainto_tsquery($1)
        """
        
        params = [query]
        param_count = 1
        
        if document_type:
            param_count += 1
            base_query += f" AND dm.document_type = ${param_count}"
            params.append(document_type)
        
        if user_id:
            param_count += 1
            base_query += f" AND dpj.user_id = ${param_count}"
            params.append(user_id)
        
        param_count += 1
        base_query += f" ORDER BY dpj.created_at DESC LIMIT ${param_count}"
        params.append(limit)
        
        return await self.execute_query(base_query, *params)
    
    async def search_entities(self, entity_text: str = None, entity_type: str = None,
                            limit: int = 50) -> List[Dict]:
        """Search named entities"""
        base_query = """
            SELECT ne.*, dpj.original_filename, dpj.created_at
            FROM named_entities ne
            JOIN document_processing_jobs dpj ON ne.job_id = dpj.job_id
            WHERE 1=1
        """
        
        params = []
        param_count = 0
        
        if entity_text:
            param_count += 1
            base_query += f" AND ne.entity_text ILIKE ${param_count}"
            params.append(f"%{entity_text}%")
        
        if entity_type:
            param_count += 1
            base_query += f" AND ne.entity_type = ${param_count}"
            params.append(entity_type)
        
        param_count += 1
        base_query += f" ORDER BY ne.confidence_score DESC LIMIT ${param_count}"
        params.append(limit)
        
        return await self.execute_query(base_query, *params)
    
    # Statistics
    async def get_processing_statistics(self, days: int = 30) -> Dict:
        """Get document processing statistics"""
        stats = {}
        
        # Job statistics
        job_stats = await self.execute_query("""
            SELECT 
                status,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_processing_time
            FROM document_processing_jobs 
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY status
        """, days)
        
        stats['jobs'] = job_stats
        
        # Document type distribution
        type_stats = await self.execute_query("""
            SELECT 
                dm.document_type,
                COUNT(*) as count,
                AVG(dm.confidence_score) as avg_confidence
            FROM document_metadata dm
            JOIN document_processing_jobs dpj ON dm.job_id = dpj.job_id
            WHERE dpj.created_at >= NOW() - INTERVAL '%s days'
            GROUP BY dm.document_type
            ORDER BY count DESC
        """, days)
        
        stats['document_types'] = type_stats
        
        # Daily processing volume
        daily_stats = await self.execute_query("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as documents_processed,
                AVG(file_size) as avg_file_size
            FROM document_processing_jobs 
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, days)
        
        stats['daily_volume'] = daily_stats
        
        return stats