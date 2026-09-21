"""
Progress tracking and reporting for bulk export operations
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ProgressStatus(str, Enum):
    """Progress tracking status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"  
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ProgressSnapshot:
    """Snapshot of progress at a point in time"""
    timestamp: datetime
    current: int
    total: int
    percentage: float
    operation: str
    estimated_completion: Optional[datetime]
    speed_items_per_second: float

class ProgressTracker:
    """Advanced progress tracking with ETA and performance metrics"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = ProgressStatus.NOT_STARTED
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Progress data
        self.current = 0
        self.total = 0
        self.current_operation = ""
        self.error_message: Optional[str] = None
        
        # Performance tracking
        self.snapshots: List[ProgressSnapshot] = []
        self.max_snapshots = 100  # Keep last 100 snapshots
        
        # Callbacks
        self.callbacks: List[Callable] = []
        
    def start(self, total_items: int = 0, operation: str = "Processing"):
        """Start progress tracking"""
        
        self.status = ProgressStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.total = total_items
        self.current = 0
        self.current_operation = operation
        
        logger.info(f"Progress tracker started for job {self.job_id}: {total_items} items")
    
    def update(self, current: int, total: Optional[int] = None, operation: Optional[str] = None):
        """Update progress"""
        
        if self.status != ProgressStatus.IN_PROGRESS:
            return
        
        self.current = current
        if total is not None:
            self.total = total
        if operation is not None:
            self.current_operation = operation
        
        # Create snapshot
        snapshot = self._create_snapshot()
        self._add_snapshot(snapshot)
        
        # Notify callbacks
        self._notify_callbacks()
        
        logger.debug(f"Progress updated for job {self.job_id}: {current}/{self.total} ({snapshot.percentage:.1f}%)")
    
    def complete(self):
        """Mark as completed"""
        
        self.status = ProgressStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.current = self.total
        
        # Final snapshot
        snapshot = self._create_snapshot()
        self._add_snapshot(snapshot)
        
        # Notify callbacks
        self._notify_callbacks()
        
        logger.info(f"Progress completed for job {self.job_id}")
    
    def fail(self, error_message: str):
        """Mark as failed"""
        
        self.status = ProgressStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        
        # Final snapshot
        snapshot = self._create_snapshot()
        self._add_snapshot(snapshot)
        
        # Notify callbacks
        self._notify_callbacks()
        
        logger.error(f"Progress failed for job {self.job_id}: {error_message}")
    
    def cancel(self):
        """Mark as cancelled"""
        
        self.status = ProgressStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        
        # Final snapshot
        snapshot = self._create_snapshot()
        self._add_snapshot(snapshot)
        
        # Notify callbacks
        self._notify_callbacks()
        
        logger.info(f"Progress cancelled for job {self.job_id}")
    
    def _create_snapshot(self) -> ProgressSnapshot:
        """Create progress snapshot"""
        
        now = datetime.utcnow()
        percentage = (self.current / self.total * 100) if self.total > 0 else 0
        
        # Calculate speed and ETA
        speed, eta = self._calculate_performance_metrics()
        
        return ProgressSnapshot(
            timestamp=now,
            current=self.current,
            total=self.total,
            percentage=percentage,
            operation=self.current_operation,
            estimated_completion=eta,
            speed_items_per_second=speed
        )
    
    def _add_snapshot(self, snapshot: ProgressSnapshot):
        """Add snapshot and maintain size limit"""
        
        self.snapshots.append(snapshot)
        
        # Maintain max snapshots
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]
    
    def _calculate_performance_metrics(self) -> tuple[float, Optional[datetime]]:
        """Calculate processing speed and estimated completion time"""
        
        if len(self.snapshots) < 2 or not self.started_at:
            return 0.0, None
        
        # Calculate speed based on recent snapshots
        recent_snapshots = self.snapshots[-10:]  # Last 10 snapshots
        if len(recent_snapshots) < 2:
            return 0.0, None
        
        # Time and items processed in recent period
        time_span = (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds()
        items_processed = recent_snapshots[-1].current - recent_snapshots[0].current
        
        if time_span <= 0:
            return 0.0, None
        
        # Items per second
        speed = items_processed / time_span
        
        # Estimated completion time
        remaining_items = self.total - self.current
        if speed > 0 and remaining_items > 0:
            remaining_seconds = remaining_items / speed
            eta = datetime.utcnow() + timedelta(seconds=remaining_seconds)
        else:
            eta = None
        
        return speed, eta
    
    def get_estimated_completion(self) -> Optional[datetime]:
        """Get estimated completion time"""
        
        if self.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]:
            return self.completed_at
        
        if not self.snapshots:
            return None
        
        return self.snapshots[-1].estimated_completion
    
    def get_progress_percentage(self) -> float:
        """Get current progress percentage"""
        
        if self.total <= 0:
            return 0.0
        
        return (self.current / self.total) * 100
    
    def get_elapsed_time(self) -> Optional[timedelta]:
        """Get elapsed time"""
        
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return end_time - self.started_at
    
    def get_estimated_remaining_time(self) -> Optional[timedelta]:
        """Get estimated remaining time"""
        
        if self.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]:
            return timedelta(0)
        
        eta = self.get_estimated_completion()
        if eta:
            return eta - datetime.utcnow()
        
        return None
    
    def get_average_speed(self) -> float:
        """Get average processing speed (items per second)"""
        
        elapsed = self.get_elapsed_time()
        if not elapsed or elapsed.total_seconds() <= 0:
            return 0.0
        
        return self.current / elapsed.total_seconds()
    
    def get_current_speed(self) -> float:
        """Get current processing speed (items per second)"""
        
        if not self.snapshots:
            return 0.0
        
        return self.snapshots[-1].speed_items_per_second
    
    def get_progress_data(self) -> Dict[str, Any]:
        """Get comprehensive progress data"""
        
        return {
            "job_id": self.job_id,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "percentage": self.get_progress_percentage(),
            "operation": self.current_operation,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_completion": self.get_estimated_completion().isoformat() if self.get_estimated_completion() else None,
            "elapsed_time_seconds": self.get_elapsed_time().total_seconds() if self.get_elapsed_time() else None,
            "estimated_remaining_seconds": self.get_estimated_remaining_time().total_seconds() if self.get_estimated_remaining_time() else None,
            "average_speed": self.get_average_speed(),
            "current_speed": self.get_current_speed(),
            "error_message": self.error_message
        }
    
    def get_performance_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get performance history snapshots"""
        
        recent_snapshots = self.snapshots[-limit:]
        
        return [
            {
                "timestamp": snapshot.timestamp.isoformat(),
                "current": snapshot.current,
                "total": snapshot.total,
                "percentage": snapshot.percentage,
                "operation": snapshot.operation,
                "speed": snapshot.speed_items_per_second
            }
            for snapshot in recent_snapshots
        ]
    
    def add_callback(self, callback: Callable):
        """Add progress update callback"""
        
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove progress update callback"""
        
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Notify all registered callbacks"""
        
        progress_data = self.get_progress_data()
        
        for callback in self.callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

class BulkProgressTracker:
    """Track progress across multiple concurrent operations"""
    
    def __init__(self):
        self.trackers: Dict[str, ProgressTracker] = {}
        self.global_callbacks: List[Callable] = []
    
    def create_tracker(self, job_id: str) -> ProgressTracker:
        """Create a new progress tracker"""
        
        tracker = ProgressTracker(job_id)
        
        # Add global callback to track overall progress
        tracker.add_callback(self._on_tracker_update)
        
        self.trackers[job_id] = tracker
        return tracker
    
    def get_tracker(self, job_id: str) -> Optional[ProgressTracker]:
        """Get existing progress tracker"""
        
        return self.trackers.get(job_id)
    
    def remove_tracker(self, job_id: str):
        """Remove completed/failed tracker"""
        
        if job_id in self.trackers:
            del self.trackers[job_id]
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """Get overall progress across all active trackers"""
        
        active_trackers = [
            tracker for tracker in self.trackers.values()
            if tracker.status == ProgressStatus.IN_PROGRESS
        ]
        
        if not active_trackers:
            return {
                "active_jobs": 0,
                "overall_progress": 100.0,
                "status": "idle"
            }
        
        # Calculate overall progress
        total_items = sum(tracker.total for tracker in active_trackers)
        current_items = sum(tracker.current for tracker in active_trackers)
        
        overall_percentage = (current_items / total_items * 100) if total_items > 0 else 0
        
        # Find slowest operation
        slowest_job = min(active_trackers, key=lambda t: t.get_progress_percentage())
        
        return {
            "active_jobs": len(active_trackers),
            "overall_progress": overall_percentage,
            "total_items": total_items,
            "current_items": current_items,
            "slowest_job": {
                "job_id": slowest_job.job_id,
                "progress": slowest_job.get_progress_percentage(),
                "operation": slowest_job.current_operation
            },
            "status": "processing"
        }
    
    def get_all_progress(self) -> Dict[str, Dict[str, Any]]:
        """Get progress data for all trackers"""
        
        return {
            job_id: tracker.get_progress_data()
            for job_id, tracker in self.trackers.items()
        }
    
    def add_global_callback(self, callback: Callable):
        """Add callback for overall progress updates"""
        
        self.global_callbacks.append(callback)
    
    def _on_tracker_update(self, progress_data: Dict[str, Any]):
        """Handle individual tracker updates"""
        
        overall_progress = self.get_overall_progress()
        
        # Notify global callbacks
        for callback in self.global_callbacks:
            try:
                callback(overall_progress)
            except Exception as e:
                logger.warning(f"Global progress callback failed: {e}")
    
    def cleanup_completed_trackers(self, max_age_hours: int = 24):
        """Clean up old completed/failed trackers"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for job_id, tracker in self.trackers.items():
            if (tracker.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED] and
                tracker.completed_at and tracker.completed_at < cutoff_time):
                to_remove.append(job_id)
        
        for job_id in to_remove:
            self.remove_tracker(job_id)
            logger.info(f"Cleaned up completed tracker: {job_id}")

# Global bulk progress tracker instance
bulk_progress_tracker = BulkProgressTracker()

def create_progress_tracker(job_id: str) -> ProgressTracker:
    """Create a new progress tracker"""
    return bulk_progress_tracker.create_tracker(job_id)

def get_progress_tracker(job_id: str) -> Optional[ProgressTracker]:
    """Get existing progress tracker"""
    return bulk_progress_tracker.get_tracker(job_id)

def get_overall_progress() -> Dict[str, Any]:
    """Get overall progress across all jobs"""
    return bulk_progress_tracker.get_overall_progress()

def get_all_progress() -> Dict[str, Dict[str, Any]]:
    """Get progress for all active jobs"""
    return bulk_progress_tracker.get_all_progress()