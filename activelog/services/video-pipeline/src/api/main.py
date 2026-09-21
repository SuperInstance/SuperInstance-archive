"""
Main FastAPI application for video processing pipeline
"""
import asyncio
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import (
    FastAPI, HTTPException, Depends, UploadFile, File, 
    Form, BackgroundTasks, Request, Response
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from config.settings import settings
from core.database import init_db, close_db, get_db
from services.storage import storage_service
from services.validation import validation_service
from services.message_queue import mq_service
from services.external_apis import external_api_service
from processors.transcoding import transcoding_service
from processors.analysis import analysis_service
from utils.monitoring import system_monitor, job_monitor, health_checker, get_prometheus_metrics
from models import Video, VideoStatus, ProcessingJob, JobType, JobStatus

logger = structlog.get_logger()

# Pydantic models for API
class VideoUploadRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    enable_transcoding: bool = True
    enable_analysis: bool = True
    analysis_options: Dict[str, Any] = {}
    transcode_options: Dict[str, Any] = {}


class VideoProcessingStatus(BaseModel):
    video_id: str
    status: VideoStatus
    progress: float = 0.0
    current_operation: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None


class TranscodeRequest(BaseModel):
    video_id: str
    formats: List[str] = ["mp4"]
    resolutions: List[str] = ["720p"]
    quality: str = "medium"
    priority: int = 0


class AnalysisRequest(BaseModel):
    video_id: str
    analysis_types: List[str] = ["comprehensive"]
    options: Dict[str, Any] = {}
    priority: int = 0


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float


# Create FastAPI app
app = FastAPI(
    title="ActiveLog Video Processing Pipeline",
    description="Comprehensive video processing, analysis, and management service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize database
        await init_db()
        
        # Initialize storage service
        await storage_service.initialize()
        
        # Connect to message queue
        await mq_service.connect()
        
        # Initialize external API service
        await external_api_service.initialize()
        
        # Start monitoring
        if settings.enable_metrics:
            await system_monitor.start_monitoring()
        
        # Set up message queue subscribers
        await _setup_message_queue_subscribers()
        
        logger.info("Video pipeline service started successfully")
        
    except Exception as e:
        logger.error("Failed to start video pipeline service", error=str(e))
        raise


@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        # Stop monitoring
        await system_monitor.stop_monitoring()
        
        # Close external API connections
        await external_api_service.close()
        
        # Disconnect from message queue
        await mq_service.disconnect()
        
        # Close database connections
        await close_db()
        
        logger.info("Video pipeline service shutdown completed")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Health and monitoring endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    uptime = (datetime.utcnow() - system_monitor.start_time).total_seconds()
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        uptime_seconds=uptime
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check"""
    return await health_checker.comprehensive_health_check()


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    metrics = get_prometheus_metrics()
    return Response(content=metrics, media_type="text/plain")


@app.get("/api/status")
async def service_status():
    """Get service status and statistics"""
    return {
        "service": "video-pipeline",
        "version": "1.0.0",
        "status": "running",
        "active_jobs": job_monitor.get_active_jobs(),
        "job_statistics": job_monitor.get_job_statistics(duration_hours=24),
        "system_health": system_monitor.get_system_health(),
        "timestamp": datetime.utcnow().isoformat()
    }


# Video upload and management endpoints
@app.post("/api/videos/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: str = Form("[]"),  # JSON string
    enable_transcoding: bool = Form(True),
    enable_analysis: bool = Form(True),
    user_id: str = Form(...),  # In production, this would come from auth middleware
    db=Depends(get_db)
):
    """Upload and process a video file"""
    try:
        # Validate file
        if not video_file.content_type or not video_file.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="Invalid file type. Only video files are allowed.")
        
        # Generate video ID
        video_id = str(uuid4())
        
        # Save uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{video_file.filename}")
        content = await video_file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Start job monitoring
        job_monitor.start_job(video_id, "video_upload", {
            "filename": video_file.filename,
            "size": len(content),
            "user_id": user_id
        })
        
        try:
            # Validate video file
            validation_result = await validation_service.validate_video_file(
                temp_file.name,
                video_file.filename
            )
            
            if not validation_result["is_valid"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid video file: {'; '.join(validation_result['issues'])}"
                )
            
            # Upload to storage
            object_name = f"uploads/{user_id}/{video_id}/{video_file.filename}"
            storage_result = await storage_service.upload_file(
                file_path=temp_file.name,
                object_name=object_name,
                bucket_type="videos",
                metadata={
                    "user_id": user_id,
                    "video_id": video_id,
                    "original_filename": video_file.filename
                }
            )
            
            # Parse tags
            import json as json_lib
            try:
                parsed_tags = json_lib.loads(tags) if tags != "[]" else []
            except:
                parsed_tags = []
            
            # Create video record
            video = Video(
                id=video_id,
                original_filename=video_file.filename,
                title=title or video_file.filename,
                description=description,
                file_size=len(content),
                mime_type=video_file.content_type,
                file_hash=validation_result["file_info"]["hash"],
                original_path=storage_result["object_name"],
                duration=validation_result["video_metadata"].get("format_info", {}).get("duration"),
                width=validation_result["video_metadata"].get("video", {}).get("width"),
                height=validation_result["video_metadata"].get("video", {}).get("height"),
                fps=validation_result["video_metadata"].get("video", {}).get("fps"),
                codec=validation_result["video_metadata"].get("video", {}).get("codec"),
                status=VideoStatus.UPLOADED,
                metadata=validation_result["video_metadata"],
                tags=parsed_tags,
                user_id=user_id
            )
            
            db.add(video)
            await db.commit()
            
            # Publish video uploaded event
            await mq_service.publish_video_uploaded(
                video_id=video_id,
                video_path=storage_result["object_name"],
                user_id=user_id,
                metadata={
                    "enable_transcoding": enable_transcoding,
                    "enable_analysis": enable_analysis,
                    "validation_result": validation_result
                }
            )
            
            # Complete job monitoring
            job_monitor.complete_job(video_id, success=True, result={
                "video_id": video_id,
                "storage_url": storage_result["url"]
            })
            
            return {
                "video_id": video_id,
                "status": "uploaded",
                "message": "Video uploaded successfully and queued for processing",
                "storage_url": storage_result["url"],
                "validation_result": validation_result,
                "processing_options": {
                    "transcoding_enabled": enable_transcoding,
                    "analysis_enabled": enable_analysis
                }
            }
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
    except HTTPException:
        job_monitor.complete_job(video_id, success=False, error="HTTP error during upload")
        raise
    except Exception as e:
        job_monitor.complete_job(video_id, success=False, error=str(e))
        logger.error("Video upload failed", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str, db=Depends(get_db)):
    """Get video information"""
    try:
        video = await db.get(Video, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return {
            "video_id": str(video.id),
            "title": video.title,
            "description": video.description,
            "status": video.status,
            "progress": video.processing_progress,
            "duration": video.duration,
            "resolution": f"{video.width}x{video.height}" if video.width and video.height else None,
            "file_size": video.file_size,
            "created_at": video.created_at,
            "updated_at": video.updated_at,
            "metadata": video.metadata,
            "tags": video.tags
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve video")


@app.get("/api/videos/{video_id}/status")
async def get_video_status(video_id: str, db=Depends(get_db)):
    """Get detailed video processing status"""
    try:
        video = await db.get(Video, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Get active processing jobs
        from sqlalchemy import select
        stmt = select(ProcessingJob).where(
            ProcessingJob.video_id == video_id,
            ProcessingJob.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
        )
        result = await db.execute(stmt)
        active_jobs = result.scalars().all()
        
        current_operation = None
        if active_jobs:
            current_operation = active_jobs[0].job_type.value
        
        return VideoProcessingStatus(
            video_id=video_id,
            status=video.status,
            progress=video.processing_progress,
            current_operation=current_operation,
            error_message=video.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video status", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get video status")


@app.get("/api/videos")
async def list_videos(
    user_id: Optional[str] = None,
    status: Optional[VideoStatus] = None,
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db)
):
    """List videos with filtering"""
    try:
        from sqlalchemy import select
        
        stmt = select(Video).offset(offset).limit(limit).order_by(Video.created_at.desc())
        
        if user_id:
            stmt = stmt.where(Video.user_id == user_id)
        if status:
            stmt = stmt.where(Video.status == status)
            
        result = await db.execute(stmt)
        videos = result.scalars().all()
        
        return {
            "videos": [
                {
                    "video_id": str(video.id),
                    "title": video.title,
                    "status": video.status,
                    "duration": video.duration,
                    "created_at": video.created_at,
                    "file_size": video.file_size
                }
                for video in videos
            ],
            "total": len(videos),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error("Failed to list videos", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list videos")


# Processing endpoints
@app.post("/api/videos/{video_id}/transcode")
async def request_transcoding(
    video_id: str,
    request: TranscodeRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Request video transcoding"""
    try:
        video = await db.get(Video, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if video.status != VideoStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Video is not ready for transcoding")
        
        # Create transcoding job
        job_id = await mq_service.publish_transcode_request(
            video_id=video_id,
            input_path=video.original_path,
            output_config={
                "formats": request.formats,
                "resolutions": request.resolutions,
                "quality": request.quality
            },
            priority=request.priority
        )
        
        # Create job record
        job = ProcessingJob(
            id=job_id,
            job_type=JobType.TRANSCODING,
            video_id=video_id,
            job_config={
                "formats": request.formats,
                "resolutions": request.resolutions,
                "quality": request.quality
            },
            priority=request.priority
        )
        
        db.add(job)
        await db.commit()
        
        return {
            "job_id": job_id,
            "message": "Transcoding job queued successfully",
            "estimated_duration_minutes": len(request.formats) * len(request.resolutions) * 5
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to request transcoding", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue transcoding job")


@app.post("/api/videos/{video_id}/analyze")
async def request_analysis(
    video_id: str,
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Request video analysis"""
    try:
        video = await db.get(Video, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Get video file path
        if not video.original_path:
            raise HTTPException(status_code=400, detail="Video file not available")
        
        # Download video for analysis (if needed)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        await storage_service.download_file(
            video.original_path,
            temp_file.name,
            bucket_type="videos"
        )
        
        # Create analysis job
        job_id = await mq_service.publish_analysis_request(
            video_id=video_id,
            video_path=temp_file.name,
            analysis_config={
                "analysis_types": request.analysis_types,
                "options": request.options
            },
            priority=request.priority
        )
        
        # Create job record
        job = ProcessingJob(
            id=job_id,
            job_type=JobType.AI_ANALYSIS,
            video_id=video_id,
            job_config={
                "analysis_types": request.analysis_types,
                "options": request.options,
                "temp_file_path": temp_file.name
            },
            priority=request.priority
        )
        
        db.add(job)
        await db.commit()
        
        return {
            "job_id": job_id,
            "message": "Analysis job queued successfully",
            "analysis_types": request.analysis_types
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to request analysis", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue analysis job")


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str, db=Depends(get_db)):
    """Get processing job status"""
    try:
        job = await db.get(ProcessingJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "result": job.result,
            "error_message": job.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get job status")


# Callback endpoints for external services
@app.post("/api/ai-callback")
async def ai_analysis_callback(request: Request, db=Depends(get_db)):
    """Callback endpoint for AI orchestrator results"""
    try:
        data = await request.json()
        
        job_id = data.get("job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="Missing job_id")
        
        job = await db.get(ProcessingJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Update job with results
        job.status = JobStatus.COMPLETED if data.get("success") else JobStatus.FAILED
        job.completed_at = datetime.utcnow()
        job.result = data.get("result")
        job.error_message = data.get("error")
        
        await db.commit()
        
        return {"message": "Callback processed successfully"}
        
    except Exception as e:
        logger.error("AI callback processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Callback processing failed")


# Message queue event handlers
async def _setup_message_queue_subscribers():
    """Set up message queue subscribers"""
    
    async def handle_video_uploaded(message: Dict[str, Any]):
        """Handle video uploaded event"""
        try:
            video_id = message["video_id"]
            video_path = message["video_path"]
            metadata = message.get("metadata", {})
            
            logger.info("Processing uploaded video", video_id=video_id)
            
            # Start processing based on metadata options
            if metadata.get("enable_transcoding", True):
                # Queue transcoding job
                await mq_service.publish_transcode_request(
                    video_id=video_id,
                    input_path=video_path,
                    output_config={
                        "formats": ["mp4", "webm"],
                        "resolutions": ["720p", "1080p"],
                        "quality": "medium"
                    }
                )
            
            if metadata.get("enable_analysis", True):
                # Queue analysis job
                await mq_service.publish_analysis_request(
                    video_id=video_id,
                    video_path=video_path,
                    analysis_config={
                        "analysis_types": ["comprehensive"]
                    }
                )
                
        except Exception as e:
            logger.error("Failed to handle video uploaded event", error=str(e))
    
    async def handle_transcode_request(message: Dict[str, Any]):
        """Handle transcoding request"""
        try:
            job_id = message["job_id"]
            video_id = message["video_id"]
            input_path = message["input_path"]
            output_config = message["output_config"]
            
            job_monitor.start_job(job_id, "transcoding")
            
            # Download input file
            temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            await storage_service.download_file(
                input_path,
                temp_input.name,
                bucket_type="videos"
            )
            
            # Process transcoding variants
            variants = []
            for format_type in output_config["formats"]:
                for resolution in output_config["resolutions"]:
                    variants.append({
                        "format": format_type,
                        "resolution": resolution,
                        "quality": output_config.get("quality", "medium")
                    })
            
            # Run transcoding
            temp_output_dir = tempfile.mkdtemp()
            result = await transcoding_service.transcode_multiple_variants(
                input_path=temp_input.name,
                output_dir=temp_output_dir,
                variants=variants
            )
            
            # Upload results to storage
            if result["success"]:
                for variant_result in result["results"]:
                    output_path = variant_result["output_path"]
                    object_name = f"transcoded/{video_id}/{os.path.basename(output_path)}"
                    
                    await storage_service.upload_file(
                        file_path=output_path,
                        object_name=object_name,
                        bucket_type="processed"
                    )
            
            job_monitor.complete_job(job_id, success=result["success"], result=result)
            
            # Cleanup
            os.unlink(temp_input.name)
            import shutil
            shutil.rmtree(temp_output_dir)
            
        except Exception as e:
            job_monitor.complete_job(job_id, success=False, error=str(e))
            logger.error("Transcoding job failed", job_id=job_id, error=str(e))
    
    async def handle_analysis_request(message: Dict[str, Any]):
        """Handle analysis request"""
        try:
            job_id = message["job_id"]
            video_id = message["video_id"]
            video_path = message["video_path"]
            analysis_config = message["analysis_config"]
            
            job_monitor.start_job(job_id, "analysis")
            
            # Run comprehensive analysis
            result = await analysis_service.analyze_video_comprehensive(video_path)
            
            # Store results in database and search index
            # This would involve updating video analysis models
            
            job_monitor.complete_job(job_id, success=True, result=result)
            
        except Exception as e:
            job_monitor.complete_job(job_id, success=False, error=str(e))
            logger.error("Analysis job failed", job_id=job_id, error=str(e))
    
    # Subscribe to message queue topics
    await mq_service.subscribe_video_uploaded(handle_video_uploaded)
    await mq_service.subscribe_transcode_requests(handle_transcode_request)
    await mq_service.subscribe_analysis_requests(handle_analysis_request)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )