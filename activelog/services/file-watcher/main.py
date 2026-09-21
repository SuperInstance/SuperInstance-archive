"""
Main application for file watcher service
"""
import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from config import WatcherConfig
from watcher import FileWatcher
from event_queue import EventQueue, SyncEngineClient
from ignore_patterns import SmartIgnoreManager
from batch_importer import BatchImporter, ThrottledBatchProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
watcher: FileWatcher = None
event_queue: EventQueue = None
sync_client: SyncEngineClient = None
config: WatcherConfig = None
batch_importer: BatchImporter = None
throttle_processor: ThrottledBatchProcessor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global watcher, event_queue, sync_client, config, batch_importer, throttle_processor
    
    try:
        # Load configuration
        config = WatcherConfig.from_env()
        
        # Validate configuration
        errors = config.validate()
        if errors:
            logger.error(f"Configuration errors: {errors}")
            sys.exit(1)
        
        # Create missing directories
        created_dirs = config.create_directories()
        if created_dirs:
            logger.info(f"Created directories: {created_dirs}")
        
        # Initialize event queue
        event_queue = EventQueue(config)
        await event_queue.initialize()
        
        # Initialize sync client
        sync_client = SyncEngineClient(config)
        
        # Initialize batch processing components
        batch_importer = BatchImporter(SmartIgnoreManager(), config.batch_size)
        throttle_processor = ThrottledBatchProcessor(
            max_batches_per_second=config.max_events_per_second / config.batch_size,
            max_events_per_second=config.max_events_per_second
        )
        
        # Initialize and start file watcher
        watcher = FileWatcher(config)
        
        # Connect watcher to event queue
        watcher.event_batcher.add_callback(process_event_batch)
        
        # Start the watcher
        await watcher.start()
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("File watcher service started successfully")
        
        yield
        
    finally:
        await shutdown()

async def shutdown():
    """Graceful shutdown"""
    global watcher, event_queue
    
    logger.info("Shutting down file watcher service...")
    
    try:
        if watcher:
            await watcher.stop()
        
        if event_queue:
            await event_queue.close()
        
        logger.info("File watcher service stopped")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

async def process_event_batch(events: List[Dict[str, Any]]):
    """Process a batch of events"""
    try:
        logger.info(f"Processing batch of {len(events)} events")
        
        # Queue events to external systems
        if event_queue:
            result = await event_queue.queue_batch(events)
            logger.debug(f"Batch queue result: {result}")
        
        # Notify sync engine
        if sync_client and config.enable_sync_queue:
            await sync_client.notify_batch(events)
        
    except Exception as e:
        logger.error(f"Error processing event batch: {e}")

# Pydantic models
class WatchDirectoryRequest(BaseModel):
    path: str = Field(..., description="Directory path to watch")
    recursive: bool = Field(True, description="Watch subdirectories")

class IgnorePatternRequest(BaseModel):
    pattern: str = Field(..., description="Ignore pattern (.gitignore style)")
    directory: str = Field(None, description="Directory for pattern (global if None)")

class ForceRescanRequest(BaseModel):
    directory: str = Field(None, description="Directory to rescan (all if None)")

class BatchImportRequest(BaseModel):
    directory: str = Field(..., description="Directory to import")
    recursive: bool = Field(True, description="Import subdirectories")
    include_patterns: List[str] = Field(None, description="Include patterns")
    max_file_size: int = Field(None, description="Maximum file size in bytes")

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    version: str = "1.0.0"

class StatsResponse(BaseModel):
    watcher_stats: Dict[str, Any]
    queue_stats: Dict[str, Any]
    ignore_stats: Dict[str, Any]

# Create FastAPI app
app = FastAPI(
    title="ActiveLog File Watcher",
    description="File system monitoring service for ActiveLog",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    global watcher
    
    if not watcher or not watcher._running:
        raise HTTPException(status_code=503, detail="Service not running")
    
    stats = watcher.get_stats()
    
    return HealthResponse(
        status="healthy" if watcher._running else "unhealthy",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=stats.get('uptime_seconds', 0)
    )

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get service statistics"""
    global watcher, event_queue
    
    watcher_stats = watcher.get_stats() if watcher else {}
    queue_stats = await event_queue.get_queue_stats() if event_queue else {}
    ignore_stats = watcher.ignore_manager.pattern_matcher.get_statistics() if watcher else {}
    
    return StatsResponse(
        watcher_stats=watcher_stats,
        queue_stats=queue_stats,
        ignore_stats=ignore_stats
    )

@app.get("/config")
async def get_config():
    """Get current configuration (sensitive data hidden)"""
    global config
    
    if not config:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "watch_directories": config.watch_directories,
        "watch_recursive": config.watch_recursive,
        "batch_size": config.batch_size,
        "batch_timeout": config.batch_timeout,
        "debounce_delay": config.debounce_delay,
        "max_events_per_second": config.max_events_per_second,
        "enable_sync_queue": config.enable_sync_queue,
        "enable_metrics": config.enable_metrics
    }

@app.post("/watch/add")
async def add_watch_directory(request: WatchDirectoryRequest):
    """Add a directory to watch"""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        await watcher.add_watch_directory(request.path)
        return {"message": f"Added watch directory: {request.path}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/watch/remove")
async def remove_watch_directory(path: str):
    """Remove a directory from watching"""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        await watcher.remove_watch_directory(path)
        return {"message": f"Removed watch directory: {path}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/watch/directories")
async def list_watch_directories():
    """List all watched directories"""
    global config
    
    if not config:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {"directories": config.watch_directories}

@app.post("/ignore/add")
async def add_ignore_pattern(request: IgnorePatternRequest):
    """Add an ignore pattern"""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        if request.directory:
            watcher.ignore_manager.pattern_matcher.add_pattern_for_directory(
                request.directory, request.pattern
            )
        else:
            watcher.ignore_manager.pattern_matcher.add_global_pattern(request.pattern)
        
        return {"message": f"Added ignore pattern: {request.pattern}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/ignore/remove")
async def remove_ignore_pattern(pattern: str, directory: str = None):
    """Remove an ignore pattern"""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        if directory:
            watcher.ignore_manager.pattern_matcher.remove_pattern_for_directory(
                directory, pattern
            )
        else:
            # Remove from global patterns (would need to implement this method)
            raise HTTPException(status_code=400, detail="Global pattern removal not implemented")
        
        return {"message": f"Removed ignore pattern: {pattern}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/ignore/patterns")
async def list_ignore_patterns():
    """List all ignore patterns"""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    patterns = {
        "global_patterns": watcher.ignore_manager.pattern_matcher.global_patterns,
        "directory_patterns": watcher.ignore_manager.pattern_matcher.directory_patterns
    }
    
    return patterns

@app.post("/rescan")
async def force_rescan(request: ForceRescanRequest, background_tasks: BackgroundTasks):
    """Force a rescan of directories"""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Add rescan task to background
    background_tasks.add_task(watcher.force_scan, request.directory)
    
    return {"message": f"Started rescan of {request.directory or 'all directories'}"}

@app.post("/queue/flush")
async def flush_queue():
    """Flush local event queue"""
    global event_queue
    
    if not event_queue:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    flushed_count = await event_queue.flush_local_queue()
    
    return {"message": f"Flushed {flushed_count} events from local queue"}

@app.post("/queue/reconnect")
async def reconnect_queue():
    """Reconnect to external queue systems"""
    global event_queue
    
    if not event_queue:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    await event_queue.reconnect()
    stats = await event_queue.get_queue_stats()
    
    return {"message": "Reconnection attempted", "stats": stats}

@app.get("/metrics")
async def get_metrics():
    """Get Prometheus-style metrics"""
    global watcher, event_queue
    
    if not watcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    stats = watcher.get_stats()
    queue_stats = await event_queue.get_queue_stats() if event_queue else {}
    
    metrics = []
    
    # Watcher metrics
    metrics.append(f"file_watcher_events_processed_total {stats.get('events_processed', 0)}")
    metrics.append(f"file_watcher_events_ignored_total {stats.get('events_ignored', 0)}")
    metrics.append(f"file_watcher_events_debounced_total {stats.get('events_debounced', 0)}")
    metrics.append(f"file_watcher_batches_processed_total {stats.get('batches_processed', 0)}")
    metrics.append(f"file_watcher_events_per_second {stats.get('events_per_second', 0)}")
    metrics.append(f"file_watcher_pending_events {stats.get('pending_events', 0)}")
    metrics.append(f"file_watcher_uptime_seconds {stats.get('uptime_seconds', 0)}")
    metrics.append(f"file_watcher_watched_directories {stats.get('watched_directories', 0)}")
    metrics.append(f"file_watcher_running {1 if stats.get('is_running') else 0}")
    
    # Queue metrics
    metrics.append(f"file_watcher_nats_connected {1 if queue_stats.get('nats_connected') else 0}")
    metrics.append(f"file_watcher_redis_connected {1 if queue_stats.get('redis_connected') else 0}")
    metrics.append(f"file_watcher_local_queue_size {queue_stats.get('local_queue_size', 0)}")
    metrics.append(f"file_watcher_redis_queue_size {queue_stats.get('redis_queue_size', 0)}")
    
    return "\n".join(metrics)

@app.post("/import/batch")
async def batch_import_directory(request: BatchImportRequest, background_tasks: BackgroundTasks):
    """Start a batch import of a directory"""
    global batch_importer, throttle_processor
    
    if not batch_importer or not throttle_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    if not os.path.exists(request.directory):
        raise HTTPException(status_code=400, detail=f"Directory does not exist: {request.directory}")
    
    # Start batch import in background
    background_tasks.add_task(
        _run_batch_import, 
        request.directory, 
        request.recursive,
        request.include_patterns,
        request.max_file_size
    )
    
    return {"message": f"Started batch import of {request.directory}"}

async def _run_batch_import(directory: str, recursive: bool, 
                           include_patterns: Optional[List[str]], 
                           max_file_size: Optional[int]):
    """Run batch import in background"""
    try:
        logger.info(f"Starting batch import of {directory}")
        
        # Reset stats
        batch_importer.reset_stats()
        throttle_processor.reset_stats()
        
        # Process batches
        async for batch in batch_importer.scan_directory(
            directory, recursive, include_patterns, max_file_size
        ):
            # Process batch with throttling
            await throttle_processor.process_batch(batch, process_event_batch)
        
        # Log final stats
        import_stats = batch_importer.get_stats()
        throttle_stats = throttle_processor.get_stats()
        
        logger.info(f"Batch import completed: {import_stats}")
        logger.info(f"Throttle stats: {throttle_stats}")
        
    except Exception as e:
        logger.error(f"Batch import failed: {e}")

@app.get("/import/stats")
async def get_import_stats():
    """Get batch import statistics"""
    global batch_importer, throttle_processor
    
    if not batch_importer or not throttle_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "import_stats": batch_importer.get_stats(),
        "throttle_stats": throttle_processor.get_stats()
    }

@app.get("/monitoring/detailed")
async def get_detailed_monitoring():
    """Get detailed monitoring information"""
    global watcher, event_queue, batch_importer, throttle_processor
    
    if not watcher:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Collect comprehensive stats
    monitoring_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": {
            "name": "file-watcher",
            "version": "1.0.0",
            "status": "running" if watcher._running else "stopped"
        },
        "watcher": watcher.get_stats(),
        "queue": await event_queue.get_queue_stats() if event_queue else {},
        "ignore_patterns": watcher.ignore_manager.pattern_matcher.get_statistics() if watcher else {},
        "batch_import": batch_importer.get_stats() if batch_importer else {},
        "throttling": throttle_processor.get_stats() if throttle_processor else {},
        "configuration": {
            "watch_directories": config.watch_directories if config else [],
            "batch_size": config.batch_size if config else 0,
            "debounce_delay": config.debounce_delay if config else 0,
            "max_events_per_second": config.max_events_per_second if config else 0
        }
    }
    
    return monitoring_data

@app.get("/monitoring/health-check")
async def detailed_health_check():
    """Detailed health check with component status"""
    global watcher, event_queue, config
    
    health_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "healthy",
        "components": {}
    }
    
    # Check watcher
    if watcher and watcher._running:
        health_data["components"]["watcher"] = {
            "status": "healthy",
            "uptime_seconds": watcher.get_stats().get("uptime_seconds", 0),
            "pending_events": len(watcher.pending_events)
        }
    else:
        health_data["components"]["watcher"] = {"status": "unhealthy"}
        health_data["overall_status"] = "unhealthy"
    
    # Check event queue
    if event_queue:
        queue_stats = await event_queue.get_queue_stats()
        queue_status = "healthy"
        
        if not queue_stats.get("nats_connected") and not queue_stats.get("redis_connected"):
            queue_status = "degraded"
            if health_data["overall_status"] == "healthy":
                health_data["overall_status"] = "degraded"
        
        health_data["components"]["event_queue"] = {
            "status": queue_status,
            "nats_connected": queue_stats.get("nats_connected", False),
            "redis_connected": queue_stats.get("redis_connected", False),
            "local_queue_size": queue_stats.get("local_queue_size", 0)
        }
    else:
        health_data["components"]["event_queue"] = {"status": "unhealthy"}
        health_data["overall_status"] = "unhealthy"
    
    # Check watched directories
    if config:
        missing_dirs = [d for d in config.watch_directories if not os.path.exists(d)]
        
        health_data["components"]["watched_directories"] = {
            "status": "healthy" if not missing_dirs else "degraded",
            "total_directories": len(config.watch_directories),
            "missing_directories": missing_dirs
        }
        
        if missing_dirs and health_data["overall_status"] == "healthy":
            health_data["overall_status"] = "degraded"
    
    return health_data

@app.get("/monitoring/system")
async def get_system_metrics():
    """Get system-level metrics"""
    try:
        import psutil
        
        # Get process info
        process = psutil.Process()
        
        system_metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "process": {
                "pid": process.pid,
                "memory_usage_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        }
        
        return system_metrics
        
    except ImportError:
        raise HTTPException(status_code=501, detail="psutil not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting system metrics: {e}")

@app.post("/monitoring/reset-stats")
async def reset_statistics():
    """Reset all statistics counters"""
    global watcher, batch_importer, throttle_processor
    
    # Reset watcher stats
    if watcher:
        watcher.stats = {
            'events_processed': 0,
            'events_ignored': 0,
            'events_debounced': 0,
            'batches_processed': 0,
            'start_time': datetime.utcnow()
        }
    
    # Reset batch import stats
    if batch_importer:
        batch_importer.reset_stats()
    
    # Reset throttle stats
    if throttle_processor:
        throttle_processor.reset_stats()
    
    return {"message": "Statistics reset successfully"}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import os
    
    # Set default environment if not specified
    os.environ.setdefault('WATCH_DIRECTORIES', '/tmp/activelog-test')
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        log_level="info",
        reload=False
    )