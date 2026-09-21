"""
API Routes for Batch Import Service
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel

from core.config import settings
from main import get_batch_processor, get_report_service, get_import_monitor

logger = logging.getLogger(__name__)

router = APIRouter()

# Response models
class ServiceStatus(BaseModel):
    service: str
    status: str
    uptime_seconds: float
    is_monitoring: bool

class BatchStatus(BaseModel):
    batch_id: str
    files_processed: int
    files_succeeded: int
    files_failed: int
    processing_time: float
    timestamp: str

class FileInfo(BaseModel):
    path: str
    event_type: str
    timestamp: str
    size: Optional[int]
    is_stable: bool

class ProcessingStats(BaseModel):
    files_detected: int
    files_processed: int
    files_succeeded: int
    files_failed: int
    duplicates_found: int
    batches_created: int
    total_size_processed: int
    uptime_seconds: float

@router.get("/status", response_model=ServiceStatus)
async def get_service_status(
    monitor = Depends(get_import_monitor),
    processor = Depends(get_batch_processor)
):
    """Get current service status"""
    try:
        monitor_stats = monitor.get_stats()
        
        return ServiceStatus(
            service="batch-import",
            status="running" if monitor.is_running() else "stopped",
            uptime_seconds=monitor_stats.get("uptime_seconds", 0),
            is_monitoring=monitor.is_running()
        )
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=ProcessingStats)
async def get_processing_stats(
    monitor = Depends(get_import_monitor),
    processor = Depends(get_batch_processor)
):
    """Get detailed processing statistics"""
    try:
        monitor_stats = monitor.get_stats()
        processor_stats = processor.get_stats()
        
        return ProcessingStats(
            files_detected=monitor_stats.get("files_detected", 0),
            files_processed=processor_stats.get("files_processed", 0),
            files_succeeded=processor_stats.get("files_succeeded", 0),
            files_failed=processor_stats.get("files_failed", 0),
            duplicates_found=processor_stats.get("duplicates_found", 0),
            batches_created=monitor_stats.get("batches_created", 0),
            total_size_processed=processor_stats.get("total_size_processed", 0),
            uptime_seconds=monitor_stats.get("uptime_seconds", 0)
        )
    except Exception as e:
        logger.error(f"Error getting processing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending-files")
async def get_pending_files(monitor = Depends(get_import_monitor)):
    """Get list of files pending processing"""
    try:
        pending_files = monitor.get_pending_files()
        return {
            "count": len(pending_files),
            "files": [FileInfo(**file_data) for file_data in pending_files]
        }
    except Exception as e:
        logger.error(f"Error getting pending files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active-batches")
async def get_active_batches(processor = Depends(get_batch_processor)):
    """Get list of currently active batch IDs"""
    try:
        active_batches = processor.get_active_batches()
        return {
            "count": len(active_batches),
            "batch_ids": active_batches
        }
    except Exception as e:
        logger.error(f"Error getting active batches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger-scan")
async def trigger_manual_scan(
    background_tasks: BackgroundTasks,
    monitor = Depends(get_import_monitor)
):
    """Manually trigger a scan of the import directory"""
    try:
        if not monitor.is_running():
            raise HTTPException(status_code=503, detail="Monitor is not running")
        
        # Trigger scan in background
        background_tasks.add_task(monitor._scan_existing_files)
        
        return {
            "message": "Manual scan triggered",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering manual scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-batch")
async def process_batch_manual(
    file_paths: List[str],
    background_tasks: BackgroundTasks,
    processor = Depends(get_batch_processor)
):
    """Manually process a batch of files"""
    try:
        # Validate file paths
        valid_paths = []
        for file_path in file_paths:
            path = Path(file_path)
            if path.exists() and path.is_file():
                valid_paths.append(str(path))
        
        if not valid_paths:
            raise HTTPException(status_code=400, detail="No valid file paths provided")
        
        # Process batch in background
        batch_task = background_tasks.add_task(processor.process_batch, valid_paths)
        
        return {
            "message": f"Processing batch of {len(valid_paths)} files",
            "file_count": len(valid_paths),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing manual batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports")
async def list_reports(
    limit: int = Query(default=10, ge=1, le=100),
    report_service = Depends(get_report_service)
):
    """List recent batch reports"""
    try:
        recent_batches = report_service.get_recent_batches(limit)
        
        return {
            "count": len(recent_batches),
            "reports": [BatchStatus(**batch) for batch in recent_batches]
        }
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/daily")
async def generate_daily_report(
    date: Optional[str] = None,
    background_tasks: BackgroundTasks,
    report_service = Depends(get_report_service)
):
    """Generate a daily summary report"""
    try:
        # Parse date if provided
        report_date = None
        if date:
            try:
                report_date = datetime.fromisoformat(date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Generate report in background
        background_tasks.add_task(report_service.generate_daily_summary, report_date)
        
        return {
            "message": "Daily report generation started",
            "date": report_date.isoformat() if report_date else datetime.now().date().isoformat(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/weekly")
async def generate_weekly_report(
    start_date: Optional[str] = None,
    background_tasks: BackgroundTasks,
    report_service = Depends(get_report_service)
):
    """Generate a weekly summary report"""
    try:
        # Parse start date if provided
        week_start = None
        if start_date:
            try:
                week_start = datetime.fromisoformat(start_date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Generate report in background
        background_tasks.add_task(report_service.generate_weekly_summary, week_start)
        
        return {
            "message": "Weekly report generation started",
            "start_date": week_start.isoformat() if week_start else "current_week",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health-report")
async def get_health_report(report_service = Depends(get_report_service)):
    """Get system health report"""
    try:
        health_report = await report_service.get_system_health_report()
        return health_report
    except Exception as e:
        logger.error(f"Error getting health report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup-reports")
async def cleanup_old_reports(
    days_to_keep: int = Query(default=30, ge=1, le=365),
    background_tasks: BackgroundTasks,
    report_service = Depends(get_report_service)
):
    """Clean up old report files"""
    try:
        background_tasks.add_task(report_service.cleanup_old_reports, days_to_keep)
        
        return {
            "message": f"Cleanup started for reports older than {days_to_keep} days",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting report cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/directories")
async def get_directory_info():
    """Get information about service directories"""
    try:
        directories = {
            "import_queue": {
                "path": settings.IMPORT_QUEUE_PATH,
                "exists": Path(settings.IMPORT_QUEUE_PATH).exists(),
                "file_count": len(list(Path(settings.IMPORT_QUEUE_PATH).glob("*"))) if Path(settings.IMPORT_QUEUE_PATH).exists() else 0
            },
            "processing": {
                "path": settings.PROCESSING_PATH,
                "exists": Path(settings.PROCESSING_PATH).exists(),
                "file_count": len(list(Path(settings.PROCESSING_PATH).glob("*"))) if Path(settings.PROCESSING_PATH).exists() else 0
            },
            "completed": {
                "path": settings.COMPLETED_PATH,
                "exists": Path(settings.COMPLETED_PATH).exists(),
                "file_count": len(list(Path(settings.COMPLETED_PATH).glob("*"))) if Path(settings.COMPLETED_PATH).exists() else 0
            },
            "failed": {
                "path": settings.FAILED_PATH,
                "exists": Path(settings.FAILED_PATH).exists(),
                "file_count": len(list(Path(settings.FAILED_PATH).glob("*"))) if Path(settings.FAILED_PATH).exists() else 0
            },
            "reports": {
                "path": settings.REPORTS_PATH,
                "exists": Path(settings.REPORTS_PATH).exists(),
                "file_count": len(list(Path(settings.REPORTS_PATH).glob("*.json"))) if Path(settings.REPORTS_PATH).exists() else 0
            },
            "thumbnails": {
                "path": settings.THUMBNAILS_PATH,
                "exists": Path(settings.THUMBNAILS_PATH).exists(),
                "file_count": len(list(Path(settings.THUMBNAILS_PATH).rglob("*"))) if Path(settings.THUMBNAILS_PATH).exists() else 0
            }
        }
        
        return directories
    except Exception as e:
        logger.error(f"Error getting directory info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "image_formats": settings.SUPPORTED_IMAGE_FORMATS,
        "video_formats": settings.SUPPORTED_VIDEO_FORMATS,
        "audio_formats": settings.SUPPORTED_AUDIO_FORMATS,
        "document_formats": settings.SUPPORTED_DOCUMENT_FORMATS,
        "all_formats": settings.all_supported_formats
    }

@router.get("/configuration")
async def get_configuration():
    """Get current service configuration (non-sensitive values)"""
    return {
        "service_name": settings.SERVICE_NAME,
        "port": settings.PORT,
        "batch_size": settings.BATCH_SIZE,
        "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
        "monitor_interval": settings.MONITOR_INTERVAL,
        "max_file_size": settings.MAX_FILE_SIZE,
        "chunk_size": settings.CHUNK_SIZE,
        "thumbnail_sizes": settings.THUMBNAIL_SIZES,
        "thumbnail_quality": settings.THUMBNAIL_QUALITY,
        "hash_algorithm": settings.HASH_ALGORITHM,
        "duplicate_action": settings.DUPLICATE_ACTION,
        "worker_threads": settings.WORKER_THREADS,
        "io_threads": settings.IO_THREADS
    }