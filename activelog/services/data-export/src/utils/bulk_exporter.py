"""
Bulk Export Manager with queue processing and resource management
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
import psutil

from .progress_tracker import ProgressTracker, ProgressStatus, create_progress_tracker
from ..core.config import settings
from ..core.database import db_manager, ExportStatus, ExportType

logger = logging.getLogger(__name__)

class BulkExportPriority(str, Enum):
    """Export priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class BulkExportRequest:
    """Bulk export request configuration"""
    user_id: str
    export_configs: List[Dict[str, Any]]  # Multiple export configurations
    priority: BulkExportPriority = BulkExportPriority.NORMAL
    callback_url: Optional[str] = None
    email_notification: Optional[str] = None
    max_concurrent_exports: int = 3
    retry_failed: bool = True
    combine_results: bool = False  # Combine all exports into single archive

@dataclass  
class BulkExportStatus:
    """Status of bulk export operation"""
    bulk_id: str
    status: ExportStatus
    total_exports: int
    completed_exports: int
    failed_exports: int
    current_operations: List[str]
    started_at: datetime
    estimated_completion: Optional[datetime] = None
    errors: List[Dict[str, Any]] = None

class ResourceManager:
    """Manage system resources for bulk exports"""
    
    def __init__(self):
        self.max_cpu_usage = 80.0  # Maximum CPU usage percentage
        self.max_memory_usage = 80.0  # Maximum memory usage percentage
        self.min_disk_space_gb = 5.0  # Minimum free disk space
        
    def can_start_export(self) -> tuple[bool, str]:
        """Check if system can handle another export"""
        
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.max_cpu_usage:
                return False, f"High CPU usage: {cpu_percent:.1f}%"
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > self.max_memory_usage:
                return False, f"High memory usage: {memory.percent:.1f}%"
            
            # Check disk space
            disk = psutil.disk_usage(settings.EXPORT_OUTPUT_DIR)
            free_gb = disk.free / (1024**3)
            if free_gb < self.min_disk_space_gb:
                return False, f"Low disk space: {free_gb:.1f}GB available"
            
            return True, "Resources available"
            
        except Exception as e:
            logger.warning(f"Resource check failed: {e}")
            return False, "Resource check failed"
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource status"""
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(settings.EXPORT_OUTPUT_DIR)
            
            return {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "disk_total_gb": disk.total / (1024**3),
                "can_start_export": self.can_start_export()[0]
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource status: {e}")
            return {"error": str(e)}

class BulkExportQueue:
    """Queue manager for bulk export operations"""
    
    def __init__(self):
        self.queues = {
            BulkExportPriority.URGENT: asyncio.Queue(),
            BulkExportPriority.HIGH: asyncio.Queue(),
            BulkExportPriority.NORMAL: asyncio.Queue(),
            BulkExportPriority.LOW: asyncio.Queue()
        }
        
        self.active_exports: Dict[str, Dict[str, Any]] = {}
        self.max_concurrent = settings.workers
        
    async def add_bulk_request(self, request: BulkExportRequest) -> str:
        """Add bulk export request to queue"""
        
        bulk_id = f"bulk_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create queue item
        queue_item = {
            "bulk_id": bulk_id,
            "request": request,
            "queued_at": datetime.utcnow()
        }
        
        # Add to appropriate priority queue
        await self.queues[request.priority].put(queue_item)
        
        logger.info(f"Added bulk export {bulk_id} to {request.priority} priority queue")
        return bulk_id
    
    async def get_next_request(self) -> Optional[Dict[str, Any]]:
        """Get next request from highest priority non-empty queue"""
        
        # Check if we can start more exports
        if len(self.active_exports) >= self.max_concurrent:
            return None
        
        # Check queues in priority order
        for priority in [BulkExportPriority.URGENT, BulkExportPriority.HIGH,
                        BulkExportPriority.NORMAL, BulkExportPriority.LOW]:
            
            queue = self.queues[priority]
            
            if not queue.empty():
                try:
                    return await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
        
        return None
    
    def add_active_export(self, bulk_id: str, export_info: Dict[str, Any]):
        """Add export to active list"""
        self.active_exports[bulk_id] = export_info
    
    def remove_active_export(self, bulk_id: str):
        """Remove export from active list"""
        if bulk_id in self.active_exports:
            del self.active_exports[bulk_id]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        
        return {
            "active_exports": len(self.active_exports),
            "max_concurrent": self.max_concurrent,
            "queue_sizes": {
                priority.value: self.queues[priority].qsize()
                for priority in BulkExportPriority
            },
            "total_queued": sum(queue.qsize() for queue in self.queues.values())
        }

class BulkExportManager:
    """Main bulk export management system"""
    
    def __init__(self):
        self.queue = BulkExportQueue()
        self.resource_manager = ResourceManager()
        self.bulk_status: Dict[str, BulkExportStatus] = {}
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self.running = False
        
    async def start(self):
        """Start the bulk export manager"""
        
        if self.running:
            return
        
        self.running = True
        logger.info("Starting bulk export manager")
        
        # Start worker tasks
        workers = []
        for i in range(settings.workers):
            worker = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            workers.append(worker)
        
        # Start monitoring task
        monitor = asyncio.create_task(self._monitor_loop())
        
        # Wait for shutdown
        try:
            await asyncio.gather(*workers, monitor)
        except asyncio.CancelledError:
            logger.info("Bulk export manager stopped")
    
    async def stop(self):
        """Stop the bulk export manager"""
        
        self.running = False
        logger.info("Stopping bulk export manager")
    
    async def submit_bulk_export(self, request: BulkExportRequest) -> str:
        """Submit bulk export request"""
        
        # Validate request
        if not request.export_configs:
            raise ValueError("No export configurations provided")
        
        if not request.user_id:
            raise ValueError("User ID required")
        
        # Add to queue
        bulk_id = await self.queue.add_bulk_request(request)
        
        # Initialize status tracking
        self.bulk_status[bulk_id] = BulkExportStatus(
            bulk_id=bulk_id,
            status=ExportStatus.PENDING,
            total_exports=len(request.export_configs),
            completed_exports=0,
            failed_exports=0,
            current_operations=[],
            started_at=datetime.utcnow(),
            errors=[]
        )
        
        # Create progress tracker
        tracker = create_progress_tracker(bulk_id)
        tracker.start(len(request.export_configs), "Bulk export queued")
        self.progress_trackers[bulk_id] = tracker
        
        logger.info(f"Submitted bulk export {bulk_id} with {len(request.export_configs)} exports")
        return bulk_id
    
    async def _worker_loop(self, worker_name: str):
        """Main worker loop for processing export requests"""
        
        logger.info(f"Started export worker: {worker_name}")
        
        while self.running:
            try:
                # Check system resources
                can_start, reason = self.resource_manager.can_start_export()
                if not can_start:
                    logger.debug(f"Worker {worker_name} waiting: {reason}")
                    await asyncio.sleep(30)  # Wait before checking again
                    continue
                
                # Get next request
                queue_item = await self.queue.get_next_request()
                if not queue_item:
                    await asyncio.sleep(5)  # No requests available
                    continue
                
                # Process bulk request
                await self._process_bulk_request(worker_name, queue_item)
                
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}", exc_info=True)
                await asyncio.sleep(10)  # Error recovery delay
        
        logger.info(f"Stopped export worker: {worker_name}")
    
    async def _process_bulk_request(self, worker_name: str, queue_item: Dict[str, Any]):
        """Process a bulk export request"""
        
        bulk_id = queue_item["bulk_id"]
        request: BulkExportRequest = queue_item["request"]
        
        logger.info(f"Worker {worker_name} processing bulk export {bulk_id}")
        
        try:
            # Mark as active
            self.queue.add_active_export(bulk_id, {
                "worker": worker_name,
                "started_at": datetime.utcnow(),
                "request": request
            })
            
            # Update status
            self.bulk_status[bulk_id].status = ExportStatus.PROCESSING
            
            # Get progress tracker
            tracker = self.progress_trackers.get(bulk_id)
            if tracker:
                tracker.update(0, len(request.export_configs), "Starting bulk export")
            
            # Process each export in the bulk request
            export_results = []
            semaphore = asyncio.Semaphore(request.max_concurrent_exports)
            
            async def process_single_export(config: Dict[str, Any], index: int):
                async with semaphore:
                    return await self._process_single_export(bulk_id, config, index, tracker)
            
            # Create tasks for all exports
            tasks = []
            for i, config in enumerate(request.export_configs):
                task = asyncio.create_task(process_single_export(config, i))
                tasks.append(task)
            
            # Wait for all exports to complete
            export_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(export_results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "index": i,
                        "config": request.export_configs[i],
                        "error": str(result)
                    })
                elif result and result.get("success"):
                    successful_results.append(result)
                else:
                    failed_results.append({
                        "index": i,
                        "config": request.export_configs[i], 
                        "error": result.get("error", "Unknown error")
                    })
            
            # Update final status
            self.bulk_status[bulk_id].completed_exports = len(successful_results)
            self.bulk_status[bulk_id].failed_exports = len(failed_results)
            self.bulk_status[bulk_id].errors = failed_results
            
            if failed_results and not successful_results:
                self.bulk_status[bulk_id].status = ExportStatus.FAILED
                if tracker:
                    tracker.fail(f"All {len(failed_results)} exports failed")
            elif failed_results:
                self.bulk_status[bulk_id].status = ExportStatus.COMPLETED
                if tracker:
                    tracker.complete()
                logger.warning(f"Bulk export {bulk_id} completed with {len(failed_results)} failures")
            else:
                self.bulk_status[bulk_id].status = ExportStatus.COMPLETED
                if tracker:
                    tracker.complete()
                logger.info(f"Bulk export {bulk_id} completed successfully")
            
            # Combine results if requested
            if request.combine_results and successful_results:
                await self._combine_export_results(bulk_id, successful_results, request)
            
            # Send notifications
            await self._send_bulk_completion_notification(bulk_id, request)
            
        except Exception as e:
            logger.error(f"Bulk export {bulk_id} failed: {e}", exc_info=True)
            self.bulk_status[bulk_id].status = ExportStatus.FAILED
            if tracker:
                tracker.fail(str(e))
            
        finally:
            # Clean up
            self.queue.remove_active_export(bulk_id)
    
    async def _process_single_export(self, bulk_id: str, config: Dict[str, Any], 
                                   index: int, tracker: Optional[ProgressTracker]) -> Dict[str, Any]:
        """Process a single export within a bulk request"""
        
        try:
            export_type = config.get("type", "zip")
            
            # Import the export manager (avoid circular import)
            from ..core.export_manager import ExportManager
            
            # Create temporary export manager instance
            export_manager = ExportManager()
            await export_manager.initialize()
            
            # Progress callback for this export
            def progress_callback(current: int, total: int, operation: str):
                if tracker:
                    # Update with weighted progress for this export
                    overall_current = tracker.current + (current / total)
                    tracker.update(int(overall_current), tracker.total, f"Export {index + 1}: {operation}")
            
            # Create export job
            job_id = await export_manager.create_export(
                user_id=config["user_id"],
                export_type=export_type,
                config=config.get("config", {}),
                filters=config.get("filters", {})
            )
            
            # Wait for completion (simplified - in production, use async monitoring)
            max_wait_time = config.get("timeout_minutes", 60) * 60  # Convert to seconds
            start_time = datetime.utcnow()
            
            while True:
                job_progress = await export_manager.get_export_progress(job_id)
                if not job_progress:
                    break
                
                status = job_progress.get("status")
                if status == ExportStatus.COMPLETED:
                    # Get file path
                    file_path = await export_manager.get_export_file_path(job_id)
                    return {
                        "success": True,
                        "job_id": job_id,
                        "export_type": export_type,
                        "file_path": file_path,
                        "index": index
                    }
                elif status == ExportStatus.FAILED:
                    return {
                        "success": False,
                        "job_id": job_id,
                        "error": "Export failed",
                        "index": index
                    }
                elif status == ExportStatus.CANCELLED:
                    return {
                        "success": False,
                        "job_id": job_id,
                        "error": "Export cancelled",
                        "index": index
                    }
                
                # Check timeout
                if (datetime.utcnow() - start_time).total_seconds() > max_wait_time:
                    await export_manager.cancel_export(job_id)
                    return {
                        "success": False,
                        "job_id": job_id,
                        "error": "Export timeout",
                        "index": index
                    }
                
                # Update progress
                if job_progress.get("progress_percentage"):
                    progress_callback(
                        int(job_progress["progress_percentage"]),
                        100,
                        job_progress.get("current_operation", "Processing")
                    )
                
                await asyncio.sleep(5)  # Check every 5 seconds
            
            return {
                "success": False,
                "job_id": job_id,
                "error": "Export monitoring failed",
                "index": index
            }
            
        except Exception as e:
            logger.error(f"Single export failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "index": index
            }
    
    async def _combine_export_results(self, bulk_id: str, results: List[Dict[str, Any]],
                                    request: BulkExportRequest):
        """Combine multiple export results into single archive"""
        
        try:
            import zipfile
            
            # Create combined archive
            output_dir = Path(settings.EXPORT_OUTPUT_DIR) / bulk_id
            output_dir.mkdir(exist_ok=True)
            
            combined_path = output_dir / f"combined_export_{bulk_id}.zip"
            
            with zipfile.ZipFile(combined_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for i, result in enumerate(results):
                    file_path = result.get("file_path")
                    if file_path and os.path.exists(file_path):
                        # Add file to combined archive
                        arc_name = f"export_{i+1}_{os.path.basename(file_path)}"
                        zipf.write(file_path, arc_name)
                
                # Add metadata
                metadata = {
                    "bulk_id": bulk_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "total_exports": len(results),
                    "user_id": request.user_id,
                    "export_types": [r.get("export_type") for r in results]
                }
                
                zipf.writestr("bulk_export_metadata.json", 
                            json.dumps(metadata, indent=2))
            
            # Update status with combined file
            self.bulk_status[bulk_id].combined_file_path = str(combined_path)
            
            logger.info(f"Created combined archive for bulk export {bulk_id}")
            
        except Exception as e:
            logger.error(f"Failed to combine export results: {e}")
    
    async def _send_bulk_completion_notification(self, bulk_id: str, request: BulkExportRequest):
        """Send completion notification for bulk export"""
        
        try:
            status = self.bulk_status[bulk_id]
            
            # Webhook notification
            if request.callback_url:
                notification_data = {
                    "bulk_id": bulk_id,
                    "status": status.status,
                    "completed_exports": status.completed_exports,
                    "failed_exports": status.failed_exports,
                    "total_exports": status.total_exports,
                    "completed_at": datetime.utcnow().isoformat()
                }
                
                # Send webhook (implement actual HTTP request)
                logger.info(f"Would send webhook notification to {request.callback_url}")
            
            # Email notification
            if request.email_notification:
                logger.info(f"Would send email notification to {request.email_notification}")
            
        except Exception as e:
            logger.error(f"Failed to send bulk completion notification: {e}")
    
    async def _monitor_loop(self):
        """Monitor system health and clean up old exports"""
        
        while self.running:
            try:
                # Clean up old status records
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                to_remove = []
                for bulk_id, status in self.bulk_status.items():
                    if (status.status in [ExportStatus.COMPLETED, ExportStatus.FAILED] and 
                        status.started_at < cutoff_time):
                        to_remove.append(bulk_id)
                
                for bulk_id in to_remove:
                    del self.bulk_status[bulk_id]
                    if bulk_id in self.progress_trackers:
                        del self.progress_trackers[bulk_id]
                
                if to_remove:
                    logger.info(f"Cleaned up {len(to_remove)} old bulk export records")
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    def get_bulk_status(self, bulk_id: str) -> Optional[Dict[str, Any]]:
        """Get status of bulk export"""
        
        status = self.bulk_status.get(bulk_id)
        if not status:
            return None
        
        # Get progress tracker data if available
        progress_data = {}
        if bulk_id in self.progress_trackers:
            progress_data = self.progress_trackers[bulk_id].get_progress_data()
        
        return {
            **asdict(status),
            "progress": progress_data
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        
        return {
            "queue_status": self.queue.get_queue_status(),
            "resource_status": self.resource_manager.get_resource_status(),
            "active_bulk_exports": len([
                s for s in self.bulk_status.values() 
                if s.status == ExportStatus.PROCESSING
            ]),
            "total_bulk_exports": len(self.bulk_status),
            "running": self.running
        }

# Global bulk export manager
bulk_export_manager = BulkExportManager()