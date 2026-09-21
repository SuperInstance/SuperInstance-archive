"""
Advanced Progress Reporting System
Provides comprehensive real-time progress tracking and reporting for multi-bot orchestration
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid

from ..director.claude_director import Task, TaskPriority, TaskStatus
from ..engines.task_decomposition_engine import TaskComplexity, TaskCategory, Subtask, DecompositionResult
from ..engines.bot_allocation_intelligence import AllocationDecision, BotCapabilities

logger = logging.getLogger(__name__)

class ProgressEventType(Enum):
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress" 
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    SUBTASK_CREATED = "subtask_created"
    SUBTASK_COMPLETED = "subtask_completed"
    BOT_ALLOCATED = "bot_allocated"
    BOT_RELEASED = "bot_released"
    MILESTONE_REACHED = "milestone_reached"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_ALERT = "system_alert"

class ReportType(Enum):
    REAL_TIME = "real_time"
    SUMMARY = "summary"
    DETAILED = "detailed"
    EXECUTIVE = "executive"
    PERFORMANCE = "performance"
    COST_ANALYSIS = "cost_analysis"

@dataclass
class ProgressEvent:
    """Individual progress event"""
    event_id: str
    event_type: ProgressEventType
    timestamp: datetime
    task_id: str
    message: str
    details: Dict[str, Any]
    severity: str = "info"  # info, warning, error, critical
    progress_percentage: Optional[float] = None
    estimated_completion: Optional[datetime] = None

@dataclass
class TaskProgress:
    """Comprehensive task progress tracking"""
    task_id: str
    task_description: str
    status: TaskStatus
    progress_percentage: float
    
    # Timing information
    created_at: datetime
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    
    # Execution details
    allocated_bot: Optional[str] = None
    subtasks: List[str] = None
    completed_subtasks: int = 0
    total_subtasks: int = 0
    
    # Performance metrics
    cost_incurred: float = 0.0
    estimated_cost: float = 0.0
    tokens_used: int = 0
    estimated_tokens: int = 0
    
    # Quality metrics
    success_probability: float = 0.8
    quality_score: Optional[float] = None
    error_count: int = 0
    retry_count: int = 0
    
    # Events and milestones
    recent_events: List[ProgressEvent] = None
    milestones: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []
        if self.recent_events is None:
            self.recent_events = []
        if self.milestones is None:
            self.milestones = []

@dataclass
class SystemMetrics:
    """Overall system performance metrics"""
    timestamp: datetime
    
    # Task metrics
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    
    # Bot utilization
    total_bots: int
    available_bots: int
    busy_bots: int
    average_bot_utilization: float
    
    # Performance metrics
    average_task_completion_time: float
    success_rate: float
    cost_efficiency: float
    throughput_tasks_per_hour: float
    
    # Resource usage
    total_tokens_processed: int
    total_cost: float
    cost_per_task: float
    
    # Queue metrics
    pending_tasks: int
    queue_depth: int
    estimated_queue_wait_time: float

class ProgressReporter:
    """Advanced progress reporting and analytics system"""
    
    def __init__(self):
        self.task_progress: Dict[str, TaskProgress] = {}
        self.event_history: List[ProgressEvent] = []
        self.system_metrics_history: List[SystemMetrics] = []
        
        # Configuration
        self.max_events_per_task = 50
        self.max_history_hours = 168  # 1 week
        self.report_refresh_interval = 5  # seconds
        
        # Real-time subscribers
        self.subscribers: Dict[str, asyncio.Queue] = {}
        
        # Analytics data
        self.performance_trends = {}
        self.cost_trends = {}
        self.bottleneck_analysis = {}
        
        # Milestone templates
        self.milestone_templates = {
            TaskComplexity.TRIVIAL: [
                {"name": "Task Started", "percentage": 0},
                {"name": "Task Completed", "percentage": 100}
            ],
            TaskComplexity.SIMPLE: [
                {"name": "Task Started", "percentage": 0},
                {"name": "Midpoint Reached", "percentage": 50},
                {"name": "Task Completed", "percentage": 100}
            ],
            TaskComplexity.MODERATE: [
                {"name": "Planning Phase", "percentage": 0},
                {"name": "Execution Started", "percentage": 20},
                {"name": "Halfway Complete", "percentage": 50},
                {"name": "Final Phase", "percentage": 80},
                {"name": "Task Completed", "percentage": 100}
            ],
            TaskComplexity.COMPLEX: [
                {"name": "Task Analysis", "percentage": 0},
                {"name": "Decomposition Complete", "percentage": 15},
                {"name": "First Phase", "percentage": 25},
                {"name": "Mid-execution", "percentage": 50},
                {"name": "Final Phase", "percentage": 75},
                {"name": "Quality Check", "percentage": 90},
                {"name": "Task Completed", "percentage": 100}
            ]
        }
    
    async def track_task(self, task: Task, decomposition_result: Optional[DecompositionResult] = None):
        """Start tracking a new task"""
        # Infer complexity for milestone creation
        complexity = self._infer_task_complexity(task)
        
        progress = TaskProgress(
            task_id=task.id,
            task_description=task.description,
            status=task.status,
            progress_percentage=0.0,
            created_at=task.created_at or datetime.now(),
            estimated_tokens=task.estimated_tokens,
            milestones=self._create_milestones(complexity)
        )
        
        # Add decomposition details if available
        if decomposition_result:
            progress.subtasks = [st.id for st in decomposition_result.subtasks]
            progress.total_subtasks = len(decomposition_result.subtasks)
            progress.estimated_cost = decomposition_result.total_estimated_cost
            progress.estimated_completion = datetime.now() + timedelta(
                minutes=decomposition_result.total_estimated_time
            )
        
        self.task_progress[task.id] = progress
        
        # Create initial event
        await self.add_event(
            task_id=task.id,
            event_type=ProgressEventType.TASK_CREATED,
            message=f"Task created: {task.description[:50]}...",
            details={
                "priority": task.priority.name,
                "estimated_tokens": task.estimated_tokens,
                "complexity": complexity.name if isinstance(complexity, TaskComplexity) else "unknown"
            }
        )
    
    async def update_task_status(self, task_id: str, status: TaskStatus, details: Optional[Dict[str, Any]] = None):
        """Update task status and trigger events"""
        progress = self.task_progress.get(task_id)
        if not progress:
            logger.warning(f"Task {task_id} not found in progress tracking")
            return
        
        old_status = progress.status
        progress.status = status
        
        # Update progress percentage based on status
        if status == TaskStatus.IN_PROGRESS and old_status == TaskStatus.PENDING:
            progress.progress_percentage = 5.0
            progress.started_at = datetime.now()
            event_type = ProgressEventType.TASK_STARTED
            message = "Task execution started"
        elif status == TaskStatus.COMPLETED:
            progress.progress_percentage = 100.0
            progress.actual_completion = datetime.now()
            event_type = ProgressEventType.TASK_COMPLETED
            message = "Task completed successfully"
        elif status == TaskStatus.FAILED:
            progress.error_count += 1
            event_type = ProgressEventType.TASK_FAILED
            message = "Task execution failed"
        elif status == TaskStatus.CANCELLED:
            event_type = ProgressEventType.TASK_CANCELLED
            message = "Task cancelled"
        else:
            event_type = ProgressEventType.TASK_PROGRESS
            message = f"Task status updated to {status.value}"
        
        await self.add_event(
            task_id=task_id,
            event_type=event_type,
            message=message,
            details=details or {}
        )
    
    async def update_task_progress(self, task_id: str, progress_percentage: float, details: Optional[Dict[str, Any]] = None):
        """Update task progress percentage"""
        progress = self.task_progress.get(task_id)
        if not progress:
            return
        
        old_percentage = progress.progress_percentage
        progress.progress_percentage = min(100.0, max(0.0, progress_percentage))
        
        # Check for milestone achievements
        await self._check_milestones(task_id, old_percentage, progress.progress_percentage)
        
        # Update completion estimate
        if progress.started_at and progress_percentage > 0:
            elapsed = (datetime.now() - progress.started_at).total_seconds()
            total_estimated = elapsed * (100.0 / progress_percentage)
            progress.estimated_completion = progress.started_at + timedelta(seconds=total_estimated)
        
        await self.add_event(
            task_id=task_id,
            event_type=ProgressEventType.TASK_PROGRESS,
            message=f"Progress updated: {progress_percentage:.1f}%",
            details=details or {},
            progress_percentage=progress_percentage,
            estimated_completion=progress.estimated_completion
        )
    
    async def track_subtask_completion(self, task_id: str, subtask_id: str):
        """Track completion of a subtask"""
        progress = self.task_progress.get(task_id)
        if not progress:
            return
        
        progress.completed_subtasks += 1
        
        # Update overall progress based on subtask completion
        if progress.total_subtasks > 0:
            subtask_progress = (progress.completed_subtasks / progress.total_subtasks) * 100
            await self.update_task_progress(task_id, subtask_progress, {
                "completed_subtasks": progress.completed_subtasks,
                "total_subtasks": progress.total_subtasks,
                "subtask_id": subtask_id
            })
        
        await self.add_event(
            task_id=task_id,
            event_type=ProgressEventType.SUBTASK_COMPLETED,
            message=f"Subtask completed: {subtask_id}",
            details={"subtask_id": subtask_id}
        )
    
    async def track_bot_allocation(self, task_id: str, allocation: AllocationDecision):
        """Track bot allocation for a task"""
        progress = self.task_progress.get(task_id)
        if not progress:
            return
        
        progress.allocated_bot = allocation.allocated_bot_id
        progress.estimated_cost = allocation.expected_cost
        
        await self.add_event(
            task_id=task_id,
            event_type=ProgressEventType.BOT_ALLOCATED,
            message=f"Bot allocated: {allocation.allocated_bot_id}",
            details={
                "bot_id": allocation.allocated_bot_id,
                "confidence": allocation.confidence_score,
                "expected_cost": allocation.expected_cost,
                "expected_latency": allocation.expected_latency_ms,
                "strategy": allocation.allocation_strategy
            }
        )
    
    async def track_performance_metrics(self, task_id: str, metrics: Dict[str, Any]):
        """Track task performance metrics"""
        progress = self.task_progress.get(task_id)
        if not progress:
            return
        
        # Update metrics
        if "cost" in metrics:
            progress.cost_incurred = metrics["cost"]
        if "tokens_used" in metrics:
            progress.tokens_used = metrics["tokens_used"]
        if "quality_score" in metrics:
            progress.quality_score = metrics["quality_score"]
        if "retry_count" in metrics:
            progress.retry_count = metrics["retry_count"]
        
        await self.add_event(
            task_id=task_id,
            event_type=ProgressEventType.TASK_PROGRESS,
            message="Performance metrics updated",
            details=metrics
        )
    
    async def add_event(
        self,
        task_id: str,
        event_type: ProgressEventType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        progress_percentage: Optional[float] = None,
        estimated_completion: Optional[datetime] = None
    ):
        """Add a new progress event"""
        event = ProgressEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            task_id=task_id,
            message=message,
            details=details or {},
            severity=severity,
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion
        )
        
        # Add to global history
        self.event_history.append(event)
        
        # Add to task-specific events
        progress = self.task_progress.get(task_id)
        if progress:
            progress.recent_events.append(event)
            # Keep only recent events
            if len(progress.recent_events) > self.max_events_per_task:
                progress.recent_events = progress.recent_events[-self.max_events_per_task:]
        
        # Notify subscribers
        await self._notify_subscribers(event)
        
        # Cleanup old events
        await self._cleanup_old_events()
    
    async def subscribe_to_progress(self, subscriber_id: str) -> asyncio.Queue:
        """Subscribe to real-time progress updates"""
        queue = asyncio.Queue(maxsize=1000)
        self.subscribers[subscriber_id] = queue
        return queue
    
    async def unsubscribe_from_progress(self, subscriber_id: str):
        """Unsubscribe from progress updates"""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
    
    async def generate_report(self, report_type: ReportType, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate various types of progress reports"""
        if report_type == ReportType.REAL_TIME:
            return await self._generate_real_time_report(task_ids)
        elif report_type == ReportType.SUMMARY:
            return await self._generate_summary_report(task_ids)
        elif report_type == ReportType.DETAILED:
            return await self._generate_detailed_report(task_ids)
        elif report_type == ReportType.EXECUTIVE:
            return await self._generate_executive_report()
        elif report_type == ReportType.PERFORMANCE:
            return await self._generate_performance_report()
        elif report_type == ReportType.COST_ANALYSIS:
            return await self._generate_cost_report()
        else:
            return {"error": f"Unknown report type: {report_type}"}
    
    async def _generate_real_time_report(self, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate real-time status report"""
        tasks_to_report = task_ids or list(self.task_progress.keys())
        
        active_tasks = []
        for task_id in tasks_to_report:
            progress = self.task_progress.get(task_id)
            if progress and progress.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                active_tasks.append({
                    "task_id": task_id,
                    "description": progress.task_description,
                    "status": progress.status.value,
                    "progress_percentage": progress.progress_percentage,
                    "allocated_bot": progress.allocated_bot,
                    "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
                    "cost_incurred": progress.cost_incurred,
                    "recent_events": [
                        {
                            "type": event.event_type.value,
                            "message": event.message,
                            "timestamp": event.timestamp.isoformat()
                        }
                        for event in progress.recent_events[-5:]  # Last 5 events
                    ]
                })
        
        return {
            "report_type": "real_time",
            "timestamp": datetime.now().isoformat(),
            "active_tasks": active_tasks,
            "total_active": len(active_tasks)
        }
    
    async def _generate_summary_report(self, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate summary progress report"""
        tasks_to_report = task_ids or list(self.task_progress.keys())
        
        stats = {
            "total_tasks": len(tasks_to_report),
            "completed": 0,
            "in_progress": 0,
            "failed": 0,
            "pending": 0,
            "total_cost": 0.0,
            "avg_progress": 0.0
        }
        
        for task_id in tasks_to_report:
            progress = self.task_progress.get(task_id)
            if progress:
                if progress.status == TaskStatus.COMPLETED:
                    stats["completed"] += 1
                elif progress.status == TaskStatus.IN_PROGRESS:
                    stats["in_progress"] += 1
                elif progress.status == TaskStatus.FAILED:
                    stats["failed"] += 1
                else:
                    stats["pending"] += 1
                
                stats["total_cost"] += progress.cost_incurred
                stats["avg_progress"] += progress.progress_percentage
        
        if stats["total_tasks"] > 0:
            stats["avg_progress"] /= stats["total_tasks"]
            stats["completion_rate"] = stats["completed"] / stats["total_tasks"]
            stats["success_rate"] = stats["completed"] / max(1, stats["completed"] + stats["failed"])
        
        return {
            "report_type": "summary",
            "timestamp": datetime.now().isoformat(),
            "statistics": stats
        }
    
    async def _generate_detailed_report(self, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate detailed progress report"""
        tasks_to_report = task_ids or list(self.task_progress.keys())
        
        detailed_tasks = []
        for task_id in tasks_to_report:
            progress = self.task_progress.get(task_id)
            if progress:
                task_detail = {
                    "task_id": task_id,
                    "description": progress.task_description,
                    "status": progress.status.value,
                    "progress_percentage": progress.progress_percentage,
                    "created_at": progress.created_at.isoformat(),
                    "started_at": progress.started_at.isoformat() if progress.started_at else None,
                    "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
                    "actual_completion": progress.actual_completion.isoformat() if progress.actual_completion else None,
                    "allocated_bot": progress.allocated_bot,
                    "subtasks": {
                        "total": progress.total_subtasks,
                        "completed": progress.completed_subtasks,
                        "remaining": progress.total_subtasks - progress.completed_subtasks
                    },
                    "performance": {
                        "cost_incurred": progress.cost_incurred,
                        "estimated_cost": progress.estimated_cost,
                        "tokens_used": progress.tokens_used,
                        "estimated_tokens": progress.estimated_tokens,
                        "quality_score": progress.quality_score,
                        "error_count": progress.error_count,
                        "retry_count": progress.retry_count
                    },
                    "milestones": progress.milestones,
                    "events": [
                        {
                            "type": event.event_type.value,
                            "message": event.message,
                            "timestamp": event.timestamp.isoformat(),
                            "severity": event.severity,
                            "details": event.details
                        }
                        for event in progress.recent_events
                    ]
                }
                detailed_tasks.append(task_detail)
        
        return {
            "report_type": "detailed",
            "timestamp": datetime.now().isoformat(),
            "tasks": detailed_tasks
        }
    
    async def _generate_executive_report(self) -> Dict[str, Any]:
        """Generate executive summary report"""
        now = datetime.now()
        day_ago = now - timedelta(hours=24)
        week_ago = now - timedelta(weeks=1)
        
        # Overall metrics
        total_tasks = len(self.task_progress)
        completed_today = sum(1 for p in self.task_progress.values() 
                             if p.actual_completion and p.actual_completion > day_ago)
        completed_this_week = sum(1 for p in self.task_progress.values() 
                                 if p.actual_completion and p.actual_completion > week_ago)
        
        # Cost analysis
        cost_today = sum(p.cost_incurred for p in self.task_progress.values() 
                        if p.actual_completion and p.actual_completion > day_ago)
        cost_this_week = sum(p.cost_incurred for p in self.task_progress.values() 
                            if p.actual_completion and p.actual_completion > week_ago)
        
        # Success rate
        completed_tasks = [p for p in self.task_progress.values() if p.status == TaskStatus.COMPLETED]
        failed_tasks = [p for p in self.task_progress.values() if p.status == TaskStatus.FAILED]
        success_rate = len(completed_tasks) / max(1, len(completed_tasks) + len(failed_tasks))
        
        # Average completion time
        completion_times = []
        for progress in self.task_progress.values():
            if progress.started_at and progress.actual_completion:
                duration = (progress.actual_completion - progress.started_at).total_seconds() / 3600
                completion_times.append(duration)
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        return {
            "report_type": "executive",
            "timestamp": now.isoformat(),
            "summary": {
                "total_tasks_managed": total_tasks,
                "completed_today": completed_today,
                "completed_this_week": completed_this_week,
                "success_rate": round(success_rate * 100, 1),
                "avg_completion_time_hours": round(avg_completion_time, 2),
                "cost_today": round(cost_today, 2),
                "cost_this_week": round(cost_this_week, 2)
            },
            "trends": {
                "daily_completion_rate": completed_today,
                "weekly_completion_rate": completed_this_week / 7,
                "cost_efficiency": round(cost_this_week / max(1, completed_this_week), 4)
            },
            "alerts": self._generate_alerts()
        }
    
    async def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate performance analysis report"""
        # Analyze performance trends
        completed_tasks = [p for p in self.task_progress.values() if p.status == TaskStatus.COMPLETED]
        
        performance_metrics = {
            "total_completed_tasks": len(completed_tasks),
            "average_quality_score": 0.0,
            "average_cost_per_task": 0.0,
            "average_tokens_per_task": 0.0,
            "bot_performance": {},
            "category_performance": {}
        }
        
        if completed_tasks:
            # Overall averages
            quality_scores = [p.quality_score for p in completed_tasks if p.quality_score]
            if quality_scores:
                performance_metrics["average_quality_score"] = sum(quality_scores) / len(quality_scores)
            
            performance_metrics["average_cost_per_task"] = sum(p.cost_incurred for p in completed_tasks) / len(completed_tasks)
            performance_metrics["average_tokens_per_task"] = sum(p.tokens_used for p in completed_tasks) / len(completed_tasks)
            
            # Bot performance breakdown
            bot_performance = {}
            for task in completed_tasks:
                if task.allocated_bot:
                    if task.allocated_bot not in bot_performance:
                        bot_performance[task.allocated_bot] = {"count": 0, "total_cost": 0, "total_quality": 0, "quality_count": 0}
                    
                    bot_performance[task.allocated_bot]["count"] += 1
                    bot_performance[task.allocated_bot]["total_cost"] += task.cost_incurred
                    if task.quality_score:
                        bot_performance[task.allocated_bot]["total_quality"] += task.quality_score
                        bot_performance[task.allocated_bot]["quality_count"] += 1
            
            # Calculate averages for each bot
            for bot_id, stats in bot_performance.items():
                performance_metrics["bot_performance"][bot_id] = {
                    "tasks_completed": stats["count"],
                    "avg_cost_per_task": stats["total_cost"] / stats["count"],
                    "avg_quality": stats["total_quality"] / max(1, stats["quality_count"])
                }
        
        return {
            "report_type": "performance",
            "timestamp": datetime.now().isoformat(),
            "metrics": performance_metrics
        }
    
    async def _generate_cost_report(self) -> Dict[str, Any]:
        """Generate cost analysis report"""
        now = datetime.now()
        costs_by_day = {}
        costs_by_bot = {}
        costs_by_complexity = {}
        
        for progress in self.task_progress.values():
            if progress.actual_completion:
                day_key = progress.actual_completion.date().isoformat()
                costs_by_day[day_key] = costs_by_day.get(day_key, 0) + progress.cost_incurred
                
                if progress.allocated_bot:
                    costs_by_bot[progress.allocated_bot] = costs_by_bot.get(progress.allocated_bot, 0) + progress.cost_incurred
                
                # Estimate complexity for cost breakdown
                complexity = self._infer_task_complexity_from_progress(progress)
                costs_by_complexity[complexity] = costs_by_complexity.get(complexity, 0) + progress.cost_incurred
        
        total_cost = sum(costs_by_day.values())
        total_tasks = len([p for p in self.task_progress.values() if p.actual_completion])
        
        return {
            "report_type": "cost_analysis",
            "timestamp": now.isoformat(),
            "summary": {
                "total_cost": round(total_cost, 2),
                "total_tasks": total_tasks,
                "average_cost_per_task": round(total_cost / max(1, total_tasks), 4),
                "costs_by_day": costs_by_day,
                "costs_by_bot": costs_by_bot,
                "costs_by_complexity": costs_by_complexity
            },
            "optimization_suggestions": self._generate_cost_optimization_suggestions()
        }
    
    def _generate_alerts(self) -> List[Dict[str, Any]]:
        """Generate system alerts based on current state"""
        alerts = []
        
        # Check for high failure rate
        recent_tasks = [p for p in self.task_progress.values() 
                       if p.created_at > datetime.now() - timedelta(hours=2)]
        if recent_tasks:
            failed_count = sum(1 for p in recent_tasks if p.status == TaskStatus.FAILED)
            failure_rate = failed_count / len(recent_tasks)
            if failure_rate > 0.2:  # 20% failure rate
                alerts.append({
                    "level": "warning",
                    "message": f"High failure rate detected: {failure_rate:.1%} in last 2 hours",
                    "category": "performance"
                })
        
        # Check for high costs
        daily_cost = sum(p.cost_incurred for p in self.task_progress.values()
                        if p.actual_completion and p.actual_completion.date() == datetime.now().date())
        if daily_cost > 50.0:  # $50 threshold
            alerts.append({
                "level": "warning", 
                "message": f"High daily cost: ${daily_cost:.2f}",
                "category": "cost"
            })
        
        # Check for slow tasks
        slow_tasks = [p for p in self.task_progress.values()
                     if p.status == TaskStatus.IN_PROGRESS and
                     p.started_at and 
                     (datetime.now() - p.started_at).total_seconds() > 3600]  # 1 hour
        if slow_tasks:
            alerts.append({
                "level": "info",
                "message": f"{len(slow_tasks)} tasks running longer than 1 hour",
                "category": "performance"
            })
        
        return alerts
    
    def _generate_cost_optimization_suggestions(self) -> List[str]:
        """Generate cost optimization suggestions"""
        suggestions = []
        
        # Analyze bot usage costs
        bot_costs = {}
        for progress in self.task_progress.values():
            if progress.allocated_bot and progress.cost_incurred > 0:
                if progress.allocated_bot not in bot_costs:
                    bot_costs[progress.allocated_bot] = {"cost": 0, "count": 0}
                bot_costs[progress.allocated_bot]["cost"] += progress.cost_incurred
                bot_costs[progress.allocated_bot]["count"] += 1
        
        # Find expensive bots with low utilization
        for bot_id, stats in bot_costs.items():
            avg_cost = stats["cost"] / stats["count"]
            if avg_cost > 0.05 and stats["count"] < 5:  # High cost, low usage
                suggestions.append(f"Consider reducing usage of {bot_id} (avg ${avg_cost:.3f}/task, {stats['count']} tasks)")
        
        # Suggest local LLM usage
        local_usage = sum(1 for p in self.task_progress.values() 
                         if p.allocated_bot == "local-llm-pool")
        total_usage = len([p for p in self.task_progress.values() if p.allocated_bot])
        
        if total_usage > 0 and local_usage / total_usage < 0.3:
            suggestions.append("Consider increasing local LLM usage for simple tasks to reduce costs")
        
        return suggestions
    
    async def _check_milestones(self, task_id: str, old_percentage: float, new_percentage: float):
        """Check if any milestones have been reached"""
        progress = self.task_progress.get(task_id)
        if not progress:
            return
        
        for milestone in progress.milestones:
            milestone_percent = milestone["percentage"]
            if old_percentage < milestone_percent <= new_percentage:
                milestone["reached_at"] = datetime.now().isoformat()
                
                await self.add_event(
                    task_id=task_id,
                    event_type=ProgressEventType.MILESTONE_REACHED,
                    message=f"Milestone reached: {milestone['name']}",
                    details={
                        "milestone_name": milestone["name"],
                        "milestone_percentage": milestone_percent
                    }
                )
    
    def _create_milestones(self, complexity: TaskComplexity) -> List[Dict[str, Any]]:
        """Create milestones based on task complexity"""
        template = self.milestone_templates.get(complexity, self.milestone_templates[TaskComplexity.SIMPLE])
        return [milestone.copy() for milestone in template]
    
    def _infer_task_complexity(self, task: Task) -> TaskComplexity:
        """Infer task complexity from task properties"""
        if task.estimated_tokens < 500:
            return TaskComplexity.TRIVIAL
        elif task.estimated_tokens < 1500:
            return TaskComplexity.SIMPLE
        elif task.estimated_tokens < 5000:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.COMPLEX
    
    def _infer_task_complexity_from_progress(self, progress: TaskProgress) -> str:
        """Infer complexity from progress data for reporting"""
        if progress.estimated_tokens < 500:
            return "trivial"
        elif progress.estimated_tokens < 1500:
            return "simple"
        elif progress.estimated_tokens < 5000:
            return "moderate"
        else:
            return "complex"
    
    async def _notify_subscribers(self, event: ProgressEvent):
        """Notify all subscribers of new events"""
        disconnected_subscribers = []
        
        for subscriber_id, queue in self.subscribers.items():
            try:
                if queue.full():
                    # Remove oldest item to make space
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                
                await queue.put(asdict(event))
            except Exception as e:
                logger.warning(f"Failed to notify subscriber {subscriber_id}: {e}")
                disconnected_subscribers.append(subscriber_id)
        
        # Clean up disconnected subscribers
        for subscriber_id in disconnected_subscribers:
            del self.subscribers[subscriber_id]
    
    async def _cleanup_old_events(self):
        """Clean up old events to prevent memory growth"""
        cutoff_time = datetime.now() - timedelta(hours=self.max_history_hours)
        
        # Clean global event history
        self.event_history = [
            event for event in self.event_history 
            if event.timestamp > cutoff_time
        ]
        
        # Clean task-specific events
        for progress in self.task_progress.values():
            progress.recent_events = [
                event for event in progress.recent_events
                if event.timestamp > cutoff_time
            ]
    
    def get_progress_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a quick progress summary for a specific task"""
        progress = self.task_progress.get(task_id)
        if not progress:
            return None
        
        return {
            "task_id": task_id,
            "status": progress.status.value,
            "progress_percentage": progress.progress_percentage,
            "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
            "cost_incurred": progress.cost_incurred,
            "allocated_bot": progress.allocated_bot,
            "last_event": progress.recent_events[-1].message if progress.recent_events else None
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get high-level system overview"""
        active_tasks = sum(1 for p in self.task_progress.values() 
                          if p.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
        completed_tasks = sum(1 for p in self.task_progress.values() 
                             if p.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for p in self.task_progress.values() 
                          if p.status == TaskStatus.FAILED)
        
        total_cost = sum(p.cost_incurred for p in self.task_progress.values())
        
        return {
            "timestamp": datetime.now().isoformat(),
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": completed_tasks / max(1, completed_tasks + failed_tasks),
            "total_cost": round(total_cost, 2),
            "recent_events": len([e for e in self.event_history 
                                 if e.timestamp > datetime.now() - timedelta(minutes=30)])
        }