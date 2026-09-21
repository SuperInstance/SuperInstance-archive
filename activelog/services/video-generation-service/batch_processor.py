#!/usr/bin/env python3
"""
Advanced Batch Video Processing System
Efficient batch processing with intelligent workload distribution and optimization
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import concurrent.futures
from dataclasses import dataclass
from enum import Enum
import sqlite3

logger = logging.getLogger(__name__)


class BatchJobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    batch_id: str
    user_id: str
    requests: List[Dict]
    status: BatchJobStatus
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_videos: int = 0
    completed_videos: int = 0
    failed_videos: int = 0
    results: List[Dict] = None
    error_message: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    total_cost: float = 0.0


class BatchVideoProcessor:
    """Advanced batch processing system for video generation"""
    
    def __init__(self, video_service, max_concurrent_jobs: int = 3):
        self.video_service = video_service
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_concurrent_per_user = 2
        
        # Active job tracking
        self.active_jobs: Dict[str, BatchJob] = {}
        self.job_queue: List[BatchJob] = []
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_jobs)
        
        # Performance tracking
        self.processing_stats = {
            "total_batches_processed": 0,
            "total_videos_generated": 0,
            "average_batch_time": 0.0,
            "success_rate": 0.0,
            "cost_efficiency": 0.0
        }
        
        # Database connection
        self.db_path = video_service.db_path
        
        # Start background processing
        self.processing_task = None
        self.is_running = False
    
    async def start_processing(self):
        """Start the batch processing loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self.processing_task = asyncio.create_task(self._process_queue())
        logger.info("🚀 Batch processing system started")
    
    async def stop_processing(self):
        """Stop the batch processing loop"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Batch processing system stopped")
    
    async def submit_batch_job(self, batch_request: Dict) -> Dict:
        """Submit a new batch job for processing"""
        
        batch_id = str(uuid.uuid4())
        user_id = batch_request.get("user_id", "default")
        requests = batch_request.get("requests", [])
        priority = batch_request.get("priority", 5)
        
        # Validate batch request
        if not requests:
            raise ValueError("Batch request must contain at least one video request")
        
        if len(requests) > 50:  # Reasonable limit
            raise ValueError("Batch size exceeds maximum limit of 50 videos")
        
        # Check user's active jobs
        user_active_jobs = sum(1 for job in self.active_jobs.values() 
                             if job.user_id == user_id and job.status == BatchJobStatus.PROCESSING)
        
        if user_active_jobs >= self.max_concurrent_per_user:
            raise ValueError(f"User has too many active batch jobs ({user_active_jobs})")
        
        # Create batch job
        batch_job = BatchJob(
            batch_id=batch_id,
            user_id=user_id,
            requests=requests,
            status=BatchJobStatus.PENDING,
            priority=priority,
            created_at=datetime.now(),
            total_videos=len(requests),
            results=[]
        )
        
        # Estimate completion time
        batch_job.estimated_completion = self._estimate_completion_time(batch_job)
        
        # Store in database
        await self._store_batch_job(batch_job)
        
        # Add to queue with priority sorting
        self.job_queue.append(batch_job)
        self.job_queue.sort(key=lambda x: (-x.priority, x.created_at))
        
        self.active_jobs[batch_id] = batch_job
        
        logger.info(f"📦 Batch job {batch_id} submitted with {len(requests)} videos")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "status": batch_job.status.value,
            "total_videos": batch_job.total_videos,
            "estimated_completion": batch_job.estimated_completion.isoformat() if batch_job.estimated_completion else None,
            "queue_position": self._get_queue_position(batch_id),
            "estimated_cost": self._estimate_batch_cost(batch_job)
        }
    
    async def get_batch_status(self, batch_id: str) -> Dict:
        """Get status of a batch job"""
        
        if batch_id not in self.active_jobs:
            # Check database for completed jobs
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT status, total_videos, completed_videos, failed_videos, 
                       total_cost, completed_at
                FROM batch_jobs WHERE batch_id = ?
            ''', (batch_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    "batch_id": batch_id,
                    "status": result[0],
                    "total_videos": result[1],
                    "completed_videos": result[2],
                    "failed_videos": result[3],
                    "total_cost": result[4],
                    "completed_at": result[5],
                    "progress_percentage": (result[2] / result[1] * 100) if result[1] > 0 else 0
                }
            else:
                raise ValueError(f"Batch job {batch_id} not found")
        
        batch_job = self.active_jobs[batch_id]
        
        return {
            "batch_id": batch_id,
            "status": batch_job.status.value,
            "total_videos": batch_job.total_videos,
            "completed_videos": batch_job.completed_videos,
            "failed_videos": batch_job.failed_videos,
            "progress_percentage": (batch_job.completed_videos / batch_job.total_videos * 100) if batch_job.total_videos > 0 else 0,
            "created_at": batch_job.created_at.isoformat(),
            "started_at": batch_job.started_at.isoformat() if batch_job.started_at else None,
            "estimated_completion": batch_job.estimated_completion.isoformat() if batch_job.estimated_completion else None,
            "queue_position": self._get_queue_position(batch_id) if batch_job.status == BatchJobStatus.PENDING else None,
            "current_cost": batch_job.total_cost,
            "error_message": batch_job.error_message
        }
    
    async def cancel_batch_job(self, batch_id: str, user_id: str) -> Dict:
        """Cancel a batch job"""
        
        if batch_id not in self.active_jobs:
            raise ValueError(f"Batch job {batch_id} not found or already completed")
        
        batch_job = self.active_jobs[batch_id]
        
        if batch_job.user_id != user_id:
            raise ValueError("Unauthorized to cancel this batch job")
        
        if batch_job.status == BatchJobStatus.COMPLETED:
            raise ValueError("Cannot cancel completed batch job")
        
        batch_job.status = BatchJobStatus.CANCELLED
        batch_job.completed_at = datetime.now()
        
        # Remove from queue if pending
        if batch_job in self.job_queue:
            self.job_queue.remove(batch_job)
        
        # Update database
        await self._update_batch_job_status(batch_job)
        
        logger.info(f"❌ Batch job {batch_id} cancelled by user {user_id}")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "status": "cancelled",
            "videos_completed": batch_job.completed_videos,
            "videos_cancelled": batch_job.total_videos - batch_job.completed_videos - batch_job.failed_videos
        }
    
    async def _process_queue(self):
        """Main processing loop for batch jobs"""
        
        while self.is_running:
            try:
                # Get next job from queue
                if not self.job_queue:
                    await asyncio.sleep(5)  # Check every 5 seconds
                    continue
                
                # Check if we can start a new job
                async with self.processing_semaphore:
                    if not self.job_queue:
                        continue
                    
                    # Get highest priority job
                    batch_job = self.job_queue.pop(0)
                    
                    # Start processing the batch
                    await self._process_batch_job(batch_job)
                
            except Exception as e:
                logger.error(f"Error in batch processing loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _process_batch_job(self, batch_job: BatchJob):
        """Process a single batch job"""
        
        batch_job.status = BatchJobStatus.PROCESSING
        batch_job.started_at = datetime.now()
        
        logger.info(f"🎬 Starting batch job {batch_job.batch_id} with {batch_job.total_videos} videos")
        
        try:
            # Update database
            await self._update_batch_job_status(batch_job)
            
            # Process videos with controlled concurrency
            video_semaphore = asyncio.Semaphore(3)  # Max 3 videos at once
            
            async def process_single_video(video_request: Dict, index: int):
                async with video_semaphore:
                    try:
                        # Convert dict to VideoGenerationRequest
                        from main import VideoGenerationRequest
                        request = VideoGenerationRequest(**video_request)
                        
                        # Generate video
                        result = await self.video_service.generate_video(request)
                        
                        # Update batch job
                        batch_job.results.append({
                            "index": index,
                            "request": video_request,
                            "result": result
                        })
                        
                        if result.get("success"):
                            batch_job.completed_videos += 1
                            batch_job.total_cost += result.get("cost", 0.0)
                        else:
                            batch_job.failed_videos += 1
                        
                        logger.debug(f"Batch {batch_job.batch_id}: Video {index + 1}/{batch_job.total_videos} completed")
                        
                    except Exception as e:
                        logger.error(f"Failed to process video {index} in batch {batch_job.batch_id}: {e}")
                        batch_job.failed_videos += 1
                        batch_job.results.append({
                            "index": index,
                            "request": video_request,
                            "result": {"success": False, "error": str(e)}
                        })
            
            # Process all videos concurrently
            tasks = []
            for i, video_request in enumerate(batch_job.requests):
                task = asyncio.create_task(process_single_video(video_request, i))
                tasks.append(task)
            
            # Wait for all videos to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Create compilation video if requested
            if batch_job.requests[0].get("create_compilation", False):
                compilation_result = await self._create_compilation_video(batch_job)
                batch_job.results.append({
                    "type": "compilation",
                    "result": compilation_result
                })
            
            # Mark as completed
            batch_job.status = BatchJobStatus.COMPLETED
            batch_job.completed_at = datetime.now()
            
            # Update statistics
            self._update_processing_stats(batch_job)
            
            logger.info(f"✅ Batch job {batch_job.batch_id} completed: {batch_job.completed_videos} successful, {batch_job.failed_videos} failed")
            
        except Exception as e:
            batch_job.status = BatchJobStatus.FAILED
            batch_job.error_message = str(e)
            batch_job.completed_at = datetime.now()
            
            logger.error(f"❌ Batch job {batch_job.batch_id} failed: {e}")
        
        finally:
            # Update database
            await self._update_batch_job_status(batch_job)
            
            # Clean up from active jobs after some time
            asyncio.create_task(self._cleanup_completed_job(batch_job.batch_id))
    
    async def _create_compilation_video(self, batch_job: BatchJob) -> Dict:
        """Create a compilation video from successful batch results"""
        
        try:
            # Get successful video paths
            successful_videos = []
            for result_item in batch_job.results:
                result = result_item.get("result", {})
                if result.get("success") and result.get("file_path"):
                    successful_videos.append(result["file_path"])
            
            if len(successful_videos) < 2:
                return {"success": False, "error": "Not enough successful videos for compilation"}
            
            # Use video editor to merge videos
            from video_editor import AdvancedVideoEditor
            editor = AdvancedVideoEditor()
            
            merge_params = {
                "transition": "fade",
                "transition_duration": 1.0,
                "fps": 24
            }
            
            compilation_result = await editor.merge_videos(successful_videos, merge_params)
            
            if compilation_result.get("success"):
                logger.info(f"📽️ Created compilation video for batch {batch_job.batch_id}")
            
            return compilation_result
            
        except Exception as e:
            logger.error(f"Failed to create compilation video: {e}")
            return {"success": False, "error": str(e)}
    
    def _estimate_completion_time(self, batch_job: BatchJob) -> datetime:
        """Estimate when the batch job will be completed"""
        
        # Base processing time per video (in seconds)
        base_time_per_video = 20  # Average generation time
        
        # Factor in queue position
        queue_position = len([job for job in self.job_queue if job.priority > batch_job.priority])
        queue_delay = queue_position * 10  # 10 seconds delay per job ahead
        
        # Factor in complexity
        complexity_multiplier = 1.0
        for request in batch_job.requests:
            duration = request.get("duration", 5)
            quality = request.get("quality", "standard")
            
            if duration > 10:
                complexity_multiplier *= 1.5
            if quality in ["high", "professional"]:
                complexity_multiplier *= 1.3
        
        total_time = (base_time_per_video * batch_job.total_videos * complexity_multiplier) + queue_delay
        
        return datetime.now() + timedelta(seconds=total_time)
    
    def _estimate_batch_cost(self, batch_job: BatchJob) -> float:
        """Estimate total cost for batch job"""
        
        total_cost = 0.0
        
        for request in batch_job.requests:
            # Simulate cost calculation (would use actual pricing)
            model = request.get("model_preference", "runway-ml")
            duration = request.get("duration", 5)
            quality = request.get("quality", "standard")
            
            base_costs = {"runway-ml": 0.50, "stable-video": 0.0, "luma-ai": 0.30}
            quality_multipliers = {"draft": 0.5, "standard": 1.0, "high": 1.5, "professional": 2.0}
            
            cost = base_costs.get(model, 0.5) * duration * quality_multipliers.get(quality, 1.0)
            total_cost += cost
        
        return round(total_cost, 2)
    
    def _get_queue_position(self, batch_id: str) -> int:
        """Get position of batch job in queue"""
        
        for i, job in enumerate(self.job_queue):
            if job.batch_id == batch_id:
                return i + 1
        
        return 0  # Not in queue (processing or completed)
    
    def _update_processing_stats(self, batch_job: BatchJob):
        """Update processing statistics"""
        
        self.processing_stats["total_batches_processed"] += 1
        self.processing_stats["total_videos_generated"] += batch_job.completed_videos
        
        # Update success rate
        total_videos = self.processing_stats["total_videos_generated"] + batch_job.failed_videos
        successful_videos = self.processing_stats["total_videos_generated"]
        self.processing_stats["success_rate"] = successful_videos / max(total_videos, 1)
        
        # Update average batch time
        if batch_job.started_at and batch_job.completed_at:
            batch_time = (batch_job.completed_at - batch_job.started_at).total_seconds()
            current_avg = self.processing_stats["average_batch_time"]
            total_batches = self.processing_stats["total_batches_processed"]
            
            new_avg = ((current_avg * (total_batches - 1)) + batch_time) / total_batches
            self.processing_stats["average_batch_time"] = new_avg
    
    async def _store_batch_job(self, batch_job: BatchJob):
        """Store batch job in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO batch_jobs 
                (batch_id, user_id, total_videos, completed_videos, failed_videos, 
                 status, created_at, total_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                batch_job.batch_id,
                batch_job.user_id,
                batch_job.total_videos,
                batch_job.completed_videos,
                batch_job.failed_videos,
                batch_job.status.value,
                batch_job.created_at.isoformat(),
                batch_job.total_cost
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store batch job: {e}")
    
    async def _update_batch_job_status(self, batch_job: BatchJob):
        """Update batch job status in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE batch_jobs 
                SET status = ?, completed_videos = ?, failed_videos = ?, 
                    total_cost = ?, completed_at = ?
                WHERE batch_id = ?
            ''', (
                batch_job.status.value,
                batch_job.completed_videos,
                batch_job.failed_videos,
                batch_job.total_cost,
                batch_job.completed_at.isoformat() if batch_job.completed_at else None,
                batch_job.batch_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update batch job status: {e}")
    
    async def _cleanup_completed_job(self, batch_id: str, delay_hours: int = 24):
        """Clean up completed job from memory after delay"""
        
        # Wait for specified delay
        await asyncio.sleep(delay_hours * 3600)
        
        # Remove from active jobs
        if batch_id in self.active_jobs:
            del self.active_jobs[batch_id]
            logger.debug(f"Cleaned up completed batch job {batch_id}")
    
    def get_processing_statistics(self) -> Dict:
        """Get batch processing statistics"""
        
        return {
            "processing_stats": self.processing_stats,
            "active_jobs": len(self.active_jobs),
            "queued_jobs": len(self.job_queue),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "system_status": "running" if self.is_running else "stopped",
            "current_load": {
                "processing": len([job for job in self.active_jobs.values() 
                                if job.status == BatchJobStatus.PROCESSING]),
                "pending": len([job for job in self.active_jobs.values() 
                              if job.status == BatchJobStatus.PENDING])
            }
        }
    
    async def get_user_batch_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get batch job history for a user"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT batch_id, total_videos, completed_videos, failed_videos,
                       status, created_at, completed_at, total_cost
                FROM batch_jobs 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            history = []
            for result in results:
                history.append({
                    "batch_id": result[0],
                    "total_videos": result[1],
                    "completed_videos": result[2],
                    "failed_videos": result[3],
                    "status": result[4],
                    "created_at": result[5],
                    "completed_at": result[6],
                    "total_cost": result[7],
                    "success_rate": (result[2] / result[1] * 100) if result[1] > 0 else 0
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get user batch history: {e}")
            return []