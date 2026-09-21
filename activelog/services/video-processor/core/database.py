"""
Database manager for video processor service
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from .config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations for video processor service"""
    
    def __init__(self):
        self.pool = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': 'activelog_video_processor'
                }
            )
            
            # Create video processing specific tables
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
    
    async def _create_tables(self):
        """Create video processing specific tables"""
        
        async with self.get_connection() as conn:
            
            # Video processing jobs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS video_processing_jobs (
                    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(100),
                    tenant_id VARCHAR(100),
                    original_filename VARCHAR(500) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size BIGINT NOT NULL,
                    mime_type VARCHAR(100),
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_seconds INTEGER,
                    error_message TEXT,
                    processing_options JSONB,
                    results JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Video metadata table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS video_metadata (
                    metadata_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id) ON DELETE CASCADE,
                    duration_seconds FLOAT,
                    width INTEGER,
                    height INTEGER,
                    fps FLOAT,
                    bitrate INTEGER,
                    codec VARCHAR(50),
                    audio_codec VARCHAR(50),
                    audio_channels INTEGER,
                    audio_sample_rate INTEGER,
                    file_format VARCHAR(50),
                    creation_time TIMESTAMP,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Keyframes table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS video_keyframes (
                    keyframe_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id) ON DELETE CASCADE,
                    timestamp_seconds FLOAT NOT NULL,
                    frame_number INTEGER,
                    file_path TEXT NOT NULL,
                    thumbnail_path TEXT,
                    width INTEGER,
                    height INTEGER,
                    confidence_score FLOAT,
                    scene_id UUID,
                    features JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Scenes table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS video_scenes (
                    scene_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id) ON DELETE CASCADE,
                    start_time_seconds FLOAT NOT NULL,
                    end_time_seconds FLOAT NOT NULL,
                    duration_seconds FLOAT NOT NULL,
                    confidence_score FLOAT,
                    description TEXT,
                    dominant_colors JSONB,
                    motion_intensity FLOAT,
                    audio_features JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # OCR results table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ocr_results (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id) ON DELETE CASCADE,
                    video_path TEXT NOT NULL,
                    total_frames_processed INTEGER,
                    text_instances_found INTEGER,
                    unique_texts_count INTEGER,
                    average_confidence FLOAT,
                    processing_settings JSONB,
                    results_json JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(job_id)
                )
            """)
            
            # Video text timeline table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS video_text_timeline (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id) ON DELETE CASCADE,
                    timestamp FLOAT NOT NULL,
                    text_content TEXT NOT NULL,
                    confidence INTEGER,
                    bbox_x INTEGER,
                    bbox_y INTEGER,
                    bbox_width INTEGER,
                    bbox_height INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(job_id, timestamp, text_content)
                )
            """)
            
            # Video summaries table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS video_summaries (
                    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id) ON DELETE CASCADE,
                    summary_type VARCHAR(50) NOT NULL, -- 'ai_generated', 'scene_based', 'ocr_based'
                    summary_text TEXT NOT NULL,
                    confidence_score FLOAT,
                    key_topics JSONB,
                    sentiment_score FLOAT,
                    language VARCHAR(10),
                    word_count INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Subtitles table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS video_subtitles (
                    subtitle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id) ON DELETE CASCADE,
                    subtitle_type VARCHAR(50) NOT NULL, -- 'extracted', 'generated', 'uploaded'
                    language VARCHAR(10) NOT NULL,
                    format VARCHAR(10) NOT NULL, -- 'srt', 'vtt', 'ass'
                    file_path TEXT,
                    content TEXT,
                    entry_count INTEGER,
                    confidence_score FLOAT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Subtitle entries table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS subtitle_entries (
                    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    subtitle_id UUID REFERENCES video_subtitles(subtitle_id) ON DELETE CASCADE,
                    start_time_seconds FLOAT NOT NULL,
                    end_time_seconds FLOAT NOT NULL,
                    text_content TEXT NOT NULL,
                    confidence_score FLOAT,
                    speaker_id VARCHAR(50),
                    entry_index INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Video thumbnails table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS video_thumbnails (
                    thumbnail_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id) ON DELETE CASCADE,
                    thumbnail_type VARCHAR(50) NOT NULL, -- 'poster', 'preview', 'timeline'
                    timestamp_seconds FLOAT,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    quality INTEGER,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Streaming sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS streaming_sessions (
                    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID REFERENCES video_processing_jobs(job_id),
                    user_id VARCHAR(100),
                    session_type VARCHAR(50) NOT NULL, -- 'live_analysis', 'progress_stream'
                    status VARCHAR(50) NOT NULL DEFAULT 'active',
                    start_time TIMESTAMP DEFAULT NOW(),
                    end_time TIMESTAMP,
                    bytes_streamed BIGINT DEFAULT 0,
                    last_activity TIMESTAMP DEFAULT NOW(),
                    client_info JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_processing_jobs(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_video_jobs_user_id ON video_processing_jobs(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_video_jobs_created_at ON video_processing_jobs(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_keyframes_job_id ON video_keyframes(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_keyframes_timestamp ON video_keyframes(timestamp_seconds)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_scenes_job_id ON video_scenes(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_scenes_time_range ON video_scenes(start_time_seconds, end_time_seconds)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_results_job_id ON ocr_results(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_video_text_timeline_job_id ON video_text_timeline(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_video_text_timeline_timestamp ON video_text_timeline(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_video_text_timeline_text ON video_text_timeline USING GIN (to_tsvector('english', text_content))")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_subtitles_job_id ON video_subtitles(job_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_entries_time ON subtitle_entries(start_time_seconds, end_time_seconds)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_streaming_sessions_status ON streaming_sessions(status)")
            
            logger.info("Video processor database tables created/verified")
    
    # Video processing job methods
    async def create_video_job(self, user_id: str, tenant_id: str, filename: str, 
                              file_path: str, file_size: int, mime_type: str,
                              processing_options: Dict = None) -> str:
        """Create a new video processing job"""
        job_id = await self.execute_scalar("""
            INSERT INTO video_processing_jobs 
            (user_id, tenant_id, original_filename, file_path, file_size, mime_type, processing_options)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING job_id
        """, user_id, tenant_id, filename, file_path, file_size, mime_type, processing_options or {})
        
        return str(job_id)
    
    async def update_job_status(self, job_id: str, status: str, progress: int = None,
                               error_message: str = None, results: Dict = None):
        """Update video processing job status"""
        if progress is not None:
            await self.execute_command("""
                UPDATE video_processing_jobs 
                SET status = $1, progress = $2, error_message = $3, results = $4,
                    updated_at = NOW(),
                    end_time = CASE WHEN $1 IN ('completed', 'failed') THEN NOW() ELSE end_time END
                WHERE job_id = $5
            """, status, progress, error_message, results, job_id)
        else:
            await self.execute_command("""
                UPDATE video_processing_jobs 
                SET status = $1, error_message = $2, results = $3,
                    updated_at = NOW(),
                    end_time = CASE WHEN $1 IN ('completed', 'failed') THEN NOW() ELSE end_time END
                WHERE job_id = $4
            """, status, error_message, results, job_id)
    
    async def start_job(self, job_id: str):
        """Mark job as started"""
        await self.execute_command("""
            UPDATE video_processing_jobs 
            SET status = 'processing', start_time = NOW(), updated_at = NOW()
            WHERE job_id = $1
        """, job_id)
    
    # Metadata methods
    async def save_video_metadata(self, job_id: str, metadata: Dict) -> str:
        """Save video metadata"""
        metadata_id = await self.execute_scalar("""
            INSERT INTO video_metadata 
            (job_id, duration_seconds, width, height, fps, bitrate, codec, 
             audio_codec, audio_channels, audio_sample_rate, file_format, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING metadata_id
        """, 
            job_id, metadata.get('duration'), metadata.get('width'), metadata.get('height'),
            metadata.get('fps'), metadata.get('bitrate'), metadata.get('codec'),
            metadata.get('audio_codec'), metadata.get('audio_channels'), 
            metadata.get('audio_sample_rate'), metadata.get('format'), metadata
        )
        
        return str(metadata_id)
    
    # Keyframe methods
    async def save_keyframe(self, job_id: str, timestamp: float, frame_number: int,
                           file_path: str, thumbnail_path: str = None, 
                           width: int = None, height: int = None,
                           confidence: float = None, scene_id: str = None,
                           features: Dict = None) -> str:
        """Save keyframe information"""
        keyframe_id = await self.execute_scalar("""
            INSERT INTO video_keyframes 
            (job_id, timestamp_seconds, frame_number, file_path, thumbnail_path,
             width, height, confidence_score, scene_id, features)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING keyframe_id
        """, job_id, timestamp, frame_number, file_path, thumbnail_path,
             width, height, confidence, scene_id, features or {})
        
        return str(keyframe_id)
    
    # Scene methods
    async def save_scene(self, job_id: str, start_time: float, end_time: float,
                        confidence: float = None, description: str = None,
                        dominant_colors: List = None, motion_intensity: float = None,
                        audio_features: Dict = None) -> str:
        """Save scene information"""
        duration = end_time - start_time
        scene_id = await self.execute_scalar("""
            INSERT INTO video_scenes 
            (job_id, start_time_seconds, end_time_seconds, duration_seconds,
             confidence_score, description, dominant_colors, motion_intensity, audio_features)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING scene_id
        """, job_id, start_time, end_time, duration, confidence, description,
             dominant_colors, motion_intensity, audio_features or {})
        
        return str(scene_id)
    
    # OCR methods
    async def save_ocr_result(self, job_id: str, keyframe_id: str, timestamp: float,
                             text_content: str, confidence: int, language: str = "eng",
                             bounding_boxes: List = None) -> str:
        """Save OCR result"""
        word_count = len(text_content.split()) if text_content else 0
        ocr_id = await self.execute_scalar("""
            INSERT INTO video_ocr_results 
            (job_id, keyframe_id, timestamp_seconds, text_content, confidence,
             language, bounding_boxes, word_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING ocr_id
        """, job_id, keyframe_id, timestamp, text_content, confidence,
             language, bounding_boxes or [], word_count)
        
        return str(ocr_id)
    
    async def update_job_progress(self, job_id: str, progress: float):
        """Update job progress percentage"""
        await self.execute_command("""
            UPDATE video_processing_jobs 
            SET progress = $1, updated_at = NOW()
            WHERE job_id = $2
        """, int(progress), job_id)
    
    async def fetch_all(self, query: str, *args) -> List:
        """Fetch all rows from query"""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)
    
    # Summary methods
    async def save_video_summary(self, job_id: str, summary_type: str, summary_text: str,
                                confidence: float = None, key_topics: List = None,
                                sentiment: float = None, language: str = "en") -> str:
        """Save video summary"""
        word_count = len(summary_text.split()) if summary_text else 0
        summary_id = await self.execute_scalar("""
            INSERT INTO video_summaries 
            (job_id, summary_type, summary_text, confidence_score, key_topics,
             sentiment_score, language, word_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING summary_id
        """, job_id, summary_type, summary_text, confidence, key_topics or [],
             sentiment, language, word_count)
        
        return str(summary_id)
    
    # Subtitle methods
    async def save_subtitles(self, job_id: str, subtitle_type: str, language: str,
                            format_type: str, file_path: str = None, content: str = None,
                            confidence: float = None) -> str:
        """Save subtitle information"""
        subtitle_id = await self.execute_scalar("""
            INSERT INTO video_subtitles 
            (job_id, subtitle_type, language, format, file_path, content, confidence_score)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING subtitle_id
        """, job_id, subtitle_type, language, format_type, file_path, content, confidence)
        
        return str(subtitle_id)
    
    async def save_subtitle_entry(self, subtitle_id: str, start_time: float, end_time: float,
                                 text_content: str, confidence: float = None,
                                 speaker_id: str = None, entry_index: int = None) -> str:
        """Save individual subtitle entry"""
        entry_id = await self.execute_scalar("""
            INSERT INTO subtitle_entries 
            (subtitle_id, start_time_seconds, end_time_seconds, text_content,
             confidence_score, speaker_id, entry_index)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING entry_id
        """, subtitle_id, start_time, end_time, text_content, confidence, speaker_id, entry_index)
        
        return str(entry_id)
    
    # Query methods
    async def get_job_details(self, job_id: str) -> Optional[Dict]:
        """Get complete job details"""
        jobs = await self.execute_query("""
            SELECT * FROM video_processing_jobs WHERE job_id = $1
        """, job_id)
        
        return jobs[0] if jobs else None
    
    async def get_job_keyframes(self, job_id: str) -> List[Dict]:
        """Get all keyframes for a job"""
        return await self.execute_query("""
            SELECT * FROM video_keyframes 
            WHERE job_id = $1 
            ORDER BY timestamp_seconds
        """, job_id)
    
    async def get_job_scenes(self, job_id: str) -> List[Dict]:
        """Get all scenes for a job"""
        return await self.execute_query("""
            SELECT * FROM video_scenes 
            WHERE job_id = $1 
            ORDER BY start_time_seconds
        """, job_id)
    
    async def get_job_ocr_results(self, job_id: str) -> List[Dict]:
        """Get all OCR results for a job"""
        return await self.execute_query("""
            SELECT * FROM video_ocr_results 
            WHERE job_id = $1 
            ORDER BY timestamp_seconds
        """, job_id)
    
    async def search_videos_by_text(self, search_text: str, user_id: str = None,
                                   limit: int = 50) -> List[Dict]:
        """Search videos by OCR text content"""
        query = """
            SELECT DISTINCT vpj.*, vom.text_content, vom.timestamp_seconds
            FROM video_processing_jobs vpj
            JOIN video_ocr_results vom ON vpj.job_id = vom.job_id
            WHERE vom.text_content ILIKE $1
        """
        params = [f"%{search_text}%"]
        
        if user_id:
            query += " AND vpj.user_id = $2"
            params.append(user_id)
        
        query += " ORDER BY vpj.created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        return await self.execute_query(query, *params)
    
    # Statistics
    async def get_processing_statistics(self, days: int = 30) -> Dict:
        """Get video processing statistics"""
        stats = {}
        
        # Job statistics
        job_stats = await self.execute_query("""
            SELECT 
                status,
                COUNT(*) as count,
                AVG(duration_seconds) as avg_duration,
                SUM(file_size) as total_size
            FROM video_processing_jobs 
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY status
        """, days)
        
        stats['jobs'] = job_stats
        
        # Processing volume
        volume_stats = await self.execute_query("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as jobs_count,
                SUM(file_size) as total_size,
                AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_processing_time
            FROM video_processing_jobs 
            WHERE created_at >= NOW() - INTERVAL '%s days'
            AND status = 'completed'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, days)
        
        stats['daily_volume'] = volume_stats
        
        return stats