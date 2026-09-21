"""
FastAPI main application for video processor service
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiofiles
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn

from core.config import settings
from core.database import DatabaseManager
from core.logging import setup_logging
from processors.keyframe_extractor import KeyframeExtractor
from processors.scene_detector import SceneDetector
from processors.thumbnail_generator import ThumbnailGenerator
from processors.ocr_processor import OCRProcessor
from processors.ai_summarizer import VideoSummarizer
from processors.subtitle_processor import SubtitleProcessor
from streaming.stream_processor import StreamingVideoProcessor

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Global instances
db_manager = None
keyframe_extractor = None
scene_detector = None
thumbnail_generator = None
ocr_processor = None
ai_summarizer = None
subtitle_processor = None
streaming_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager, keyframe_extractor, scene_detector, thumbnail_generator
    global ocr_processor, ai_summarizer, subtitle_processor, streaming_processor
    
    try:
        logger.info("Starting video processor service...")
        
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Initialize processors
        keyframe_extractor = KeyframeExtractor(db_manager)
        scene_detector = SceneDetector(db_manager)
        thumbnail_generator = ThumbnailGenerator(db_manager)
        ocr_processor = OCRProcessor(db_manager)
        ai_summarizer = VideoSummarizer(db_manager)
        subtitle_processor = SubtitleProcessor(db_manager)
        streaming_processor = StreamingVideoProcessor(db_manager)
        
        logger.info("Video processor service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start video processor service: {str(e)}")
        raise
    
    finally:
        logger.info("Shutting down video processor service...")
        
        # Stop streaming sessions
        if streaming_processor:
            for session_id in list(streaming_processor.active_sessions.keys()):
                await streaming_processor.stop_stream_session(session_id)
        
        # Close database connections
        if db_manager:
            await db_manager.close()
        
        logger.info("Video processor service stopped")

# Create FastAPI application
app = FastAPI(
    title="Video Processor Service",
    description="Advanced video processing and analysis service",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic models
class VideoUploadResponse(BaseModel):
    job_id: str
    filename: str
    file_size: int
    status: str
    message: str

class VideoProcessingRequest(BaseModel):
    extract_keyframes: bool = True
    generate_thumbnails: bool = True
    detect_scenes: bool = True
    extract_text: bool = True
    generate_summaries: bool = True
    extract_subtitles: bool = True
    keyframe_interval: Optional[float] = None
    thumbnail_sizes: List[Dict[str, int]] = Field(default=[{"width": 320, "height": 240}])
    ocr_languages: str = "eng"
    summary_types: List[str] = Field(default=["comprehensive", "scene_based", "text_based"])

class StreamingSessionRequest(BaseModel):
    stream_source: str
    analysis_types: List[str] = Field(default=["keyframes", "ocr", "scene_detection"])
    callback_url: Optional[str] = None
    websocket_url: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    search_type: str = Field(default="all", description="all, text, summaries, subtitles")
    language: Optional[str] = None
    limit: int = Field(default=50, le=200)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        db_healthy = await db_manager.health_check() if db_manager else False
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "healthy" if db_healthy else "unhealthy",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "version": "1.0.0"
        }

# Video upload endpoint
@app.post("/videos/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = "default",
    tenant_id: str = "default"
):
    """Upload a video file for processing"""
    
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Create upload directory
        upload_dir = os.path.join(settings.TEMP_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(upload_dir, file.filename)
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        file_size = len(content)
        
        # Create processing job
        job_id = await db_manager.create_video_job(
            user_id=user_id,
            tenant_id=tenant_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type
        )
        
        logger.info(f"Video uploaded: {file.filename} (Job: {job_id})")
        
        return VideoUploadResponse(
            job_id=job_id,
            filename=file.filename,
            file_size=file_size,
            status="uploaded",
            message="Video uploaded successfully"
        )
        
    except Exception as e:
        logger.error(f"Video upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Video processing endpoint
@app.post("/videos/{job_id}/process")
async def process_video(
    job_id: str,
    background_tasks: BackgroundTasks,
    processing_options: VideoProcessingRequest = VideoProcessingRequest()
):
    """Start video processing for an uploaded video"""
    
    try:
        # Get job details
        job = await db_manager.get_job_details(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] not in ['pending', 'failed']:
            raise HTTPException(status_code=400, detail=f"Job already {job['status']}")
        
        # Start processing in background
        background_tasks.add_task(
            _process_video_background, 
            job_id, 
            job['file_path'],
            processing_options
        )
        
        # Mark job as started
        await db_manager.start_job(job_id)
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Video processing started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start video processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _process_video_background(job_id: str, video_path: str, options: VideoProcessingRequest):
    """Background video processing task"""
    
    try:
        logger.info(f"Starting background processing for job {job_id}")
        
        # Process keyframes
        if options.extract_keyframes:
            await keyframe_extractor.extract_keyframes(
                job_id, video_path, 
                interval_seconds=options.keyframe_interval or settings.KEYFRAME_INTERVAL_SECONDS
            )
        
        # Generate thumbnails
        if options.generate_thumbnails:
            await thumbnail_generator.generate_thumbnails(
                job_id, video_path,
                sizes=options.thumbnail_sizes
            )
        
        # Detect scenes
        if options.detect_scenes:
            await scene_detector.detect_scenes(job_id, video_path)
        
        # Extract text via OCR
        if options.extract_text:
            await ocr_processor.process_video_ocr(
                job_id, video_path,
                languages=options.ocr_languages
            )
        
        # Generate AI summaries
        if options.generate_summaries:
            await ai_summarizer.generate_video_summary(
                job_id, video_path,
                summary_types=options.summary_types
            )
        
        # Extract subtitles
        if options.extract_subtitles:
            await subtitle_processor.process_video_subtitles(
                job_id, video_path,
                extract_embedded=True,
                generate_auto_subtitles=False
            )
        
        # Final completion
        await db_manager.update_job_status(job_id, 'completed', None, None, {
            'processing_options': options.dict(),
            'completed_at': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Video processing completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Video processing failed for job {job_id}: {str(e)}")
        await db_manager.update_job_status(job_id, 'failed', None, str(e))

# Job status endpoint
@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get processing job status"""
    
    try:
        job = await db_manager.get_job_details(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job_id,
            "status": job['status'],
            "progress": job['progress'],
            "start_time": job['start_time'].isoformat() if job['start_time'] else None,
            "end_time": job['end_time'].isoformat() if job['end_time'] else None,
            "error_message": job['error_message']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get processing results
@app.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """Get complete processing results for a job"""
    
    try:
        job = await db_manager.get_job_details(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get all processing results
        results = {
            "job_id": job_id,
            "status": job['status'],
            "video_info": {
                "filename": job['original_filename'],
                "file_size": job['file_size'],
                "duration": job['duration_seconds']
            },
            "keyframes": await db_manager.get_job_keyframes(job_id),
            "scenes": await db_manager.get_job_scenes(job_id),
            "ocr_results": await db_manager.get_job_ocr_results(job_id),
            "summaries": await ai_summarizer.get_video_summaries(job_id),
            "subtitles": await subtitle_processor.get_video_subtitles(job_id)
        }
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Search endpoints
@app.post("/search")
async def search_videos(search_request: SearchRequest):
    """Search videos by various criteria"""
    
    try:
        results = {"videos": [], "total": 0}
        
        if search_request.search_type in ["all", "text"]:
            # Search by OCR text
            text_results = await ocr_processor.search_video_text(
                search_request.query, 
                limit=search_request.limit
            )
            results["videos"].extend(text_results)
        
        if search_request.search_type in ["all", "summaries"]:
            # Search by summaries
            summary_results = await ai_summarizer.search_videos_by_summary(
                search_request.query,
                limit=search_request.limit
            )
            results["videos"].extend(summary_results)
        
        if search_request.search_type in ["all", "subtitles"]:
            # Search by subtitles
            subtitle_results = await subtitle_processor.search_subtitles(
                search_request.query,
                language=search_request.language,
                limit=search_request.limit
            )
            results["videos"].extend(subtitle_results)
        
        results["total"] = len(results["videos"])
        return results
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Streaming endpoints
@app.post("/streaming/sessions")
async def start_streaming_session(request: StreamingSessionRequest):
    """Start a new streaming processing session"""
    
    try:
        session_id = f"stream_{int(datetime.utcnow().timestamp())}"
        
        result = await streaming_processor.start_stream_session(
            session_id=session_id,
            stream_source=request.stream_source,
            analysis_types=request.analysis_types,
            callback_url=request.callback_url,
            websocket_url=request.websocket_url
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to start streaming session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/streaming/sessions/{session_id}")
async def stop_streaming_session(session_id: str):
    """Stop a streaming processing session"""
    
    try:
        result = await streaming_processor.stop_stream_session(session_id)
        return result
        
    except Exception as e:
        logger.error(f"Failed to stop streaming session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/streaming/sessions")
async def list_streaming_sessions():
    """List all active streaming sessions"""
    
    try:
        sessions = await streaming_processor.list_active_sessions()
        return {"sessions": sessions, "total": len(sessions)}
        
    except Exception as e:
        logger.error(f"Failed to list streaming sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/streaming/sessions/{session_id}")
async def get_streaming_session_status(session_id: str):
    """Get status of a streaming session"""
    
    try:
        status = await streaming_processor.get_stream_status(session_id)
        if not status:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get streaming session status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for streaming
@app.websocket("/streaming/sessions/{session_id}/ws")
async def streaming_websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time streaming results"""
    
    await websocket.accept()
    
    try:
        await streaming_processor.connect_websocket(session_id, websocket)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
        await websocket.close()

# Statistics endpoint
@app.get("/statistics")
async def get_statistics():
    """Get processing statistics"""
    
    try:
        stats = await db_manager.get_processing_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# File serving endpoints
@app.get("/files/thumbnails/{job_id}/{filename}")
async def serve_thumbnail(job_id: str, filename: str):
    """Serve thumbnail files"""
    
    # This would serve generated thumbnail files
    # Implementation depends on file storage strategy
    raise HTTPException(status_code=501, detail="Not implemented")

@app.get("/files/keyframes/{job_id}/{filename}")
async def serve_keyframe(job_id: str, filename: str):
    """Serve keyframe files"""
    
    # This would serve extracted keyframe files
    # Implementation depends on file storage strategy
    raise HTTPException(status_code=501, detail="Not implemented")

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_config=None  # We handle logging ourselves
    )