"""
Central export management and orchestration
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor
import uuid

from .config import settings
from .database import db_manager, ExportStatus, ExportType
from ..exporters.pdf_exporter import PDFExporter
from ..exporters.archive_exporter import ArchiveExporter
from ..exporters.gdpr_exporter import GDPRExporter
from ..generators.website_generator import WebsiteGenerator
from ..generators.photobook_generator import PhotoBookGenerator
from ..utils.progress_tracker import ProgressTracker
from ..cloud.cloud_providers import CloudProviderManager

logger = logging.getLogger(__name__)

class ExportManager:
    """Central export job management and orchestration"""
    
    def __init__(self):
        self.active_exports: Dict[str, Dict[str, Any]] = {}
        self.exporters: Dict[str, Any] = {}
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=settings.workers)
        self.cloud_manager = CloudProviderManager()
        
    async def initialize(self):
        """Initialize export manager and components"""
        
        # Initialize exporters
        self.exporters = {
            ExportType.PDF: PDFExporter(),
            ExportType.ZIP: ArchiveExporter(),
            ExportType.TAR_GZ: ArchiveExporter(),
            ExportType.WEBSITE: WebsiteGenerator(), 
            ExportType.PHOTOBOOK: PhotoBookGenerator(),
            ExportType.GDPR: GDPRExporter(),
        }
        
        # Initialize each exporter
        for exporter in self.exporters.values():
            if hasattr(exporter, 'initialize'):
                await exporter.initialize()
        
        # Initialize cloud providers
        await self.cloud_manager.initialize()
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_task())
        
        logger.info("Export manager initialized successfully")
    
    async def create_export(self, user_id: str, export_type: str, 
                          config: Dict[str, Any], 
                          filters: Optional[Dict[str, Any]] = None) -> str:
        """
        Create and start a new export job
        
        Args:
            user_id: User requesting the export
            export_type: Type of export (pdf, zip, etc.)
            config: Export configuration
            filters: Optional filters for content selection
            
        Returns:
            Export job ID
        """
        
        # Validate export type
        if export_type not in self.exporters:
            raise ValueError(f"Unsupported export type: {export_type}")
        
        # Create database record
        job_id = await db_manager.create_export_job(
            user_id=user_id,
            export_type=export_type,
            config=config,
            filters=filters
        )
        
        # Create progress tracker
        self.progress_trackers[job_id] = ProgressTracker(job_id)
        
        # Start export processing in background
        asyncio.create_task(self._process_export(job_id))
        
        logger.info(f"Created export job {job_id} for user {user_id}")
        return job_id
    
    async def _process_export(self, job_id: str):
        """Process export job asynchronously"""
        
        try:
            # Mark as active
            self.active_exports[job_id] = {
                "status": ExportStatus.PROCESSING,
                "started_at": datetime.utcnow()
            }
            
            # Update database status
            await db_manager.update_export_job(job_id, {
                "status": ExportStatus.PROCESSING,
                "started_at": datetime.utcnow()
            })
            
            # Get job details
            job = await db_manager.get_export_job(job_id)
            if not job:
                raise Exception("Export job not found")
            
            export_type = job["export_type"]
            config = job["config"]
            filters = job.get("filters", {})
            
            # Get the appropriate exporter
            exporter = self.exporters[export_type]
            progress_tracker = self.progress_trackers[job_id]
            
            # Start progress tracking
            progress_tracker.start()
            
            # Set up progress callback
            def progress_callback(current: int, total: int, operation: str):
                asyncio.create_task(
                    self._update_progress(job_id, current, total, operation)
                )
            
            # Execute export
            result = await self._execute_export(
                exporter=exporter,
                job_id=job_id,
                config=config,
                filters=filters,
                progress_callback=progress_callback
            )
            
            # Handle result
            if result["success"]:
                await self._complete_export(job_id, result)
            else:
                await self._fail_export(job_id, result.get("error", "Unknown error"))
                
        except Exception as e:
            logger.error(f"Export job {job_id} failed: {e}", exc_info=True)
            await self._fail_export(job_id, str(e))
        finally:
            # Clean up
            if job_id in self.active_exports:
                del self.active_exports[job_id]
            if job_id in self.progress_trackers:
                del self.progress_trackers[job_id]
    
    async def _execute_export(self, exporter: Any, job_id: str, 
                            config: Dict[str, Any], filters: Dict[str, Any],
                            progress_callback: Callable) -> Dict[str, Any]:
        """Execute the actual export operation"""
        
        try:
            # Prepare output directory
            output_dir = Path(settings.EXPORT_OUTPUT_DIR) / job_id
            output_dir.mkdir(exist_ok=True)
            
            # Run export in thread pool for CPU-intensive operations
            result = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool,
                self._run_export_sync,
                exporter,
                job_id,
                config,
                filters,
                str(output_dir),
                progress_callback
            )
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_export_sync(self, exporter: Any, job_id: str, 
                        config: Dict[str, Any], filters: Dict[str, Any],
                        output_dir: str, progress_callback: Callable) -> Dict[str, Any]:
        """Run export synchronously in thread pool"""
        
        try:
            # Call the exporter's export method
            result = exporter.export(
                job_id=job_id,
                config=config,
                filters=filters,
                output_dir=output_dir,
                progress_callback=progress_callback
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Sync export failed for job {job_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _update_progress(self, job_id: str, current: int, total: int, operation: str):
        """Update export progress"""
        
        try:
            progress_percentage = (current / total * 100) if total > 0 else 0
            
            # Update database
            await db_manager.update_export_job(job_id, {
                "processed_items": current,
                "total_items": total,
                "progress_percentage": progress_percentage,
                "current_operation": operation
            })
            
            # Update progress tracker
            if job_id in self.progress_trackers:
                self.progress_trackers[job_id].update(current, total, operation)
            
        except Exception as e:
            logger.error(f"Failed to update progress for job {job_id}: {e}")
    
    async def _complete_export(self, job_id: str, result: Dict[str, Any]):
        """Complete export job successfully"""
        
        try:
            output_path = result.get("output_path")
            file_size = 0
            
            if output_path and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
            
            # Calculate expiry date
            expires_at = datetime.utcnow() + timedelta(days=settings.security.data_retention_days)
            
            # Update database
            await db_manager.update_export_job(job_id, {
                "status": ExportStatus.COMPLETED,
                "completed_at": datetime.utcnow(),
                "expires_at": expires_at,
                "output_path": output_path,
                "output_filename": result.get("filename"),
                "file_size": file_size
            })
            
            # Upload to cloud if configured
            await self._handle_cloud_upload(job_id, result)
            
            # Send completion notification
            await self._send_completion_notification(job_id, True)
            
            logger.info(f"Export job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to complete export job {job_id}: {e}")
            await self._fail_export(job_id, f"Completion error: {str(e)}")
    
    async def _fail_export(self, job_id: str, error_message: str):
        """Fail export job with error"""
        
        try:
            await db_manager.update_export_job(job_id, {
                "status": ExportStatus.FAILED,
                "completed_at": datetime.utcnow(),
                "error_message": error_message
            })
            
            # Send failure notification
            await self._send_completion_notification(job_id, False, error_message)
            
            logger.error(f"Export job {job_id} failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to update failed export job {job_id}: {e}")
    
    async def _handle_cloud_upload(self, job_id: str, result: Dict[str, Any]):
        """Handle cloud upload if configured"""
        
        try:
            job = await db_manager.get_export_job(job_id)
            if not job:
                return
            
            config = job.get("config", {})
            cloud_provider = config.get("cloud_provider")
            
            if not cloud_provider or not result.get("output_path"):
                return
            
            # Upload to cloud
            upload_result = await self.cloud_manager.upload_file(
                provider=cloud_provider,
                local_path=result["output_path"],
                remote_path=f"exports/{job_id}/{result.get('filename', 'export')}",
                user_id=job["user_id"]
            )
            
            if upload_result.get("success"):
                # Update job with cloud info
                await db_manager.update_export_job(job_id, {
                    "cloud_provider": cloud_provider,
                    "cloud_path": upload_result.get("path"),
                    "cloud_share_url": upload_result.get("share_url")
                })
                
                logger.info(f"Export {job_id} uploaded to {cloud_provider}")
            
        except Exception as e:
            logger.error(f"Cloud upload failed for export {job_id}: {e}")
    
    async def _send_completion_notification(self, job_id: str, success: bool, 
                                          error_message: Optional[str] = None):
        """Send completion notification to user"""
        
        try:
            # TODO: Implement notification service integration
            # This would send email, webhook, or push notification
            # based on user preferences
            
            job = await db_manager.get_export_job(job_id)
            if not job:
                return
            
            user_id = job["user_id"]
            export_type = job["export_type"]
            
            if success:
                logger.info(f"Export {job_id} completed for user {user_id}")
            else:
                logger.error(f"Export {job_id} failed for user {user_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to send notification for export {job_id}: {e}")
    
    async def cancel_export(self, job_id: str) -> bool:
        """Cancel a running export"""
        
        try:
            if job_id in self.active_exports:
                # Mark as cancelled
                await db_manager.update_export_job(job_id, {
                    "status": ExportStatus.CANCELLED,
                    "completed_at": datetime.utcnow()
                })
                
                # Clean up
                if job_id in self.active_exports:
                    del self.active_exports[job_id]
                if job_id in self.progress_trackers:
                    del self.progress_trackers[job_id]
                
                logger.info(f"Export job {job_id} cancelled")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel export {job_id}: {e}")
            return False
    
    async def get_export_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress of export job"""
        
        try:
            job = await db_manager.get_export_job(job_id)
            if not job:
                return None
            
            progress_data = {
                "job_id": job_id,
                "status": job["status"],
                "progress_percentage": job.get("progress_percentage", 0),
                "processed_items": job.get("processed_items", 0),
                "total_items": job.get("total_items", 0),
                "current_operation": job.get("current_operation"),
                "started_at": job.get("started_at"),
                "estimated_completion": None
            }
            
            # Add estimated completion if available
            if job_id in self.progress_trackers:
                tracker = self.progress_trackers[job_id]
                progress_data["estimated_completion"] = tracker.get_estimated_completion()
            
            return progress_data
            
        except Exception as e:
            logger.error(f"Failed to get progress for export {job_id}: {e}")
            return None
    
    async def get_export_file_path(self, job_id: str) -> Optional[str]:
        """Get file path for completed export"""
        
        try:
            job = await db_manager.get_export_job(job_id)
            if not job or job["status"] != ExportStatus.COMPLETED:
                return None
            
            output_path = job.get("output_path")
            if output_path and os.path.exists(output_path):
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file path for export {job_id}: {e}")
            return None
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get export service metrics"""
        
        try:
            # Get job counts by status
            status_counts = {}
            for status in ExportStatus:
                count = await db_manager.database.fetch_val(
                    "SELECT COUNT(*) FROM export_jobs WHERE status = :status",
                    values={"status": status}
                )
                status_counts[status] = count or 0
            
            # Get active exports
            active_count = len(self.active_exports)
            
            # Get disk usage
            output_dir_size = self._get_directory_size(settings.EXPORT_OUTPUT_DIR)
            temp_dir_size = self._get_directory_size(settings.EXPORT_TEMP_DIR)
            
            return {
                "active_exports": active_count,
                "job_counts": status_counts,
                "disk_usage": {
                    "output_dir_mb": output_dir_size / 1024 / 1024,
                    "temp_dir_mb": temp_dir_size / 1024 / 1024
                },
                "available_exporters": list(self.exporters.keys()),
                "cloud_providers": self.cloud_manager.get_available_providers()
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {"error": str(e)}
    
    def _get_directory_size(self, directory: str) -> int:
        """Get total size of directory in bytes"""
        
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
            return total_size
        except Exception:
            return 0
    
    async def _cleanup_task(self):
        """Background task for cleaning up expired exports"""
        
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up database
                cleaned_count = await db_manager.cleanup_expired_jobs()
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired export jobs")
                
                # Clean up files
                await self._cleanup_expired_files()
                
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    async def _cleanup_expired_files(self):
        """Clean up expired export files"""
        
        try:
            output_dir = Path(settings.EXPORT_OUTPUT_DIR)
            cutoff_time = datetime.utcnow() - timedelta(days=settings.security.data_retention_days)
            
            for item in output_dir.iterdir():
                if item.is_dir():
                    # Check if directory is old
                    if datetime.fromtimestamp(item.stat().st_mtime) < cutoff_time:
                        shutil.rmtree(item)
                        logger.info(f"Cleaned up expired export directory: {item}")
                elif item.is_file():
                    # Check if file is old
                    if datetime.fromtimestamp(item.stat().st_mtime) < cutoff_time:
                        item.unlink()
                        logger.info(f"Cleaned up expired export file: {item}")
            
        except Exception as e:
            logger.error(f"File cleanup error: {e}")
    
    async def cleanup(self):
        """Clean up export manager resources"""
        
        # Cancel all active exports
        for job_id in list(self.active_exports.keys()):
            await self.cancel_export(job_id)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        # Clean up cloud manager
        await self.cloud_manager.cleanup()
        
        logger.info("Export manager cleaned up")