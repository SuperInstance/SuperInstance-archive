import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import heapq
import json
import sqlite3
from pathlib import Path
import numpy as np
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class SchedulingPolicy(Enum):
    FIFO = "fifo"
    SJF = "sjf"  # Shortest Job First
    PRIORITY = "priority"
    ROUND_ROBIN = "round_robin"
    FAIR_SHARE = "fair_share"
    PREDICTIVE = "predictive"
    DEADLINE_AWARE = "deadline_aware"
    RESOURCE_AWARE = "resource_aware"

@dataclass
class ResourcePrediction:
    cpu_usage: float
    memory_usage: float
    execution_time: float
    token_usage: int
    confidence: float
    model_version: str
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ScheduledTask:
    task_id: str
    priority: int
    estimated_execution_time: float
    resource_requirements: Dict[str, float]
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    prediction: Optional[ResourcePrediction] = None
    
    def __lt__(self, other):
        return self.priority > other.priority

class ScheduleOptimizer:
    """Optimizes task scheduling using various algorithms"""
    
    def __init__(self):
        self.history = deque(maxlen=10000)
        self.performance_metrics = defaultdict(list)
    
    def optimize_schedule(
        self, 
        tasks: List[ScheduledTask], 
        available_resources: Dict[str, float],
        policy: SchedulingPolicy
    ) -> List[ScheduledTask]:
        """Optimize task scheduling based on policy"""
        
        if policy == SchedulingPolicy.FIFO:
            return sorted(tasks, key=lambda t: t.submitted_at)
        
        elif policy == SchedulingPolicy.SJF:
            return sorted(tasks, key=lambda t: t.estimated_execution_time)
        
        elif policy == SchedulingPolicy.PRIORITY:
            return sorted(tasks, key=lambda t: (-t.priority, t.submitted_at))
        
        elif policy == SchedulingPolicy.DEADLINE_AWARE:
            return self._deadline_aware_schedule(tasks)
        
        elif policy == SchedulingPolicy.RESOURCE_AWARE:
            return self._resource_aware_schedule(tasks, available_resources)
        
        elif policy == SchedulingPolicy.PREDICTIVE:
            return self._predictive_schedule(tasks, available_resources)
        
        elif policy == SchedulingPolicy.FAIR_SHARE:
            return self._fair_share_schedule(tasks)
        
        else:
            return tasks
    
    def _deadline_aware_schedule(self, tasks: List[ScheduledTask]) -> List[ScheduledTask]:
        """Schedule tasks based on deadlines (Earliest Deadline First)"""
        now = datetime.now()
        
        # Separate tasks with and without deadlines
        deadline_tasks = [t for t in tasks if t.deadline]
        no_deadline_tasks = [t for t in tasks if not t.deadline]
        
        # Sort deadline tasks by deadline
        deadline_tasks.sort(key=lambda t: t.deadline)
        
        # Sort non-deadline tasks by priority
        no_deadline_tasks.sort(key=lambda t: (-t.priority, t.submitted_at))
        
        return deadline_tasks + no_deadline_tasks
    
    def _resource_aware_schedule(
        self, 
        tasks: List[ScheduledTask], 
        available_resources: Dict[str, float]
    ) -> List[ScheduledTask]:
        """Schedule tasks based on resource availability and requirements"""
        scheduled = []
        remaining_tasks = tasks.copy()
        current_resources = available_resources.copy()
        
        while remaining_tasks:
            # Find tasks that can run with current resources
            runnable_tasks = []
            for task in remaining_tasks:
                can_run = True
                for resource, requirement in task.resource_requirements.items():
                    if current_resources.get(resource, 0) < requirement:
                        can_run = False
                        break
                
                if can_run:
                    runnable_tasks.append(task)
            
            if not runnable_tasks:
                # No tasks can run, add highest priority task anyway
                runnable_tasks = [max(remaining_tasks, key=lambda t: t.priority)]
            
            # Select best task from runnable tasks (highest priority)
            selected_task = max(runnable_tasks, key=lambda t: t.priority)
            scheduled.append(selected_task)
            remaining_tasks.remove(selected_task)
            
            # Update available resources
            for resource, requirement in selected_task.resource_requirements.items():
                current_resources[resource] = max(0, current_resources[resource] - requirement)
        
        return scheduled
    
    def _predictive_schedule(
        self, 
        tasks: List[ScheduledTask], 
        available_resources: Dict[str, float]
    ) -> List[ScheduledTask]:
        """Schedule tasks using predictive modeling"""
        # Use machine learning predictions to optimize schedule
        scored_tasks = []
        
        for task in tasks:
            score = self._calculate_predictive_score(task, available_resources)
            scored_tasks.append((score, task))
        
        # Sort by score (higher is better)
        scored_tasks.sort(key=lambda x: x[0], reverse=True)
        
        return [task for _, task in scored_tasks]
    
    def _fair_share_schedule(self, tasks: List[ScheduledTask]) -> List[ScheduledTask]:
        """Implement fair share scheduling"""
        # Group tasks by submitter or priority level
        priority_groups = defaultdict(list)
        for task in tasks:
            priority_groups[task.priority].append(task)
        
        # Round-robin between priority groups
        scheduled = []
        max_items = max(len(group) for group in priority_groups.values()) if priority_groups else 0
        
        for i in range(max_items):
            for priority in sorted(priority_groups.keys(), reverse=True):
                group = priority_groups[priority]
                if i < len(group):
                    scheduled.append(group[i])
        
        return scheduled
    
    def _calculate_predictive_score(
        self, 
        task: ScheduledTask, 
        available_resources: Dict[str, float]
    ) -> float:
        """Calculate predictive score for task scheduling"""
        score = 0.0
        
        # Priority weight
        score += task.priority * 10
        
        # Resource availability weight
        resource_score = 0.0
        for resource, requirement in task.resource_requirements.items():
            available = available_resources.get(resource, 0)
            if available > 0:
                resource_score += min(1.0, available / requirement)
        
        score += resource_score * 5
        
        # Deadline urgency weight
        if task.deadline:
            time_to_deadline = (task.deadline - datetime.now()).total_seconds()
            if time_to_deadline > 0:
                urgency = 1.0 / (1.0 + time_to_deadline / 3600)  # Hours to deadline
                score += urgency * 15
        
        # Execution time efficiency (prefer shorter tasks for quick wins)
        if task.estimated_execution_time > 0:
            efficiency = 1.0 / (1.0 + task.estimated_execution_time / 300)  # 5 minutes baseline
            score += efficiency * 3
        
        # Prediction confidence weight
        if task.prediction:
            score += task.prediction.confidence * 2
        
        return score

class PredictiveScheduler:
    """Advanced predictive task scheduler"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/data/scheduler.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.optimizer = ScheduleOptimizer()
        self.execution_history = deque(maxlen=10000)
        self.performance_model = None
        self.running = False
        
        self._init_database()
    
    def _init_database(self):
        """Initialize scheduler database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    priority INTEGER,
                    estimated_time REAL,
                    actual_time REAL,
                    resource_requirements TEXT,
                    resource_usage TEXT,
                    scheduled_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduling_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy TEXT NOT NULL,
                    throughput REAL,
                    avg_wait_time REAL,
                    avg_turnaround_time REAL,
                    resource_utilization REAL,
                    deadline_miss_rate REAL,
                    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    async def start(self):
        """Start the predictive scheduler"""
        try:
            logger.info("Starting Predictive Scheduler...")
            
            # Load historical data
            await self._load_execution_history()
            
            # Initialize performance model
            self.performance_model = self._build_performance_model()
            
            self.running = True
            logger.info("Predictive Scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Predictive Scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the predictive scheduler"""
        logger.info("Stopping Predictive Scheduler...")
        self.running = False
        logger.info("Predictive Scheduler stopped")
    
    async def schedule_tasks(
        self, 
        tasks: List[ScheduledTask], 
        available_resources: Dict[str, float],
        policy: SchedulingPolicy = SchedulingPolicy.PREDICTIVE
    ) -> List[ScheduledTask]:
        """Schedule tasks using the specified policy"""
        try:
            # Add predictions to tasks
            for task in tasks:
                if not task.prediction:
                    task.prediction = await self._predict_task_resources(task)
            
            # Optimize schedule
            scheduled_tasks = self.optimizer.optimize_schedule(
                tasks, available_resources, policy
            )
            
            # Update scheduling metrics
            await self._update_scheduling_metrics(policy, scheduled_tasks)
            
            return scheduled_tasks
            
        except Exception as e:
            logger.error(f"Task scheduling failed: {e}")
            return tasks
    
    async def _predict_task_resources(self, task: ScheduledTask) -> ResourcePrediction:
        """Predict resource requirements for a task"""
        try:
            # Use historical data for prediction
            similar_tasks = self._find_similar_tasks(task)
            
            if similar_tasks:
                # Average of similar tasks
                avg_cpu = np.mean([t['cpu_usage'] for t in similar_tasks])
                avg_memory = np.mean([t['memory_usage'] for t in similar_tasks])
                avg_time = np.mean([t['execution_time'] for t in similar_tasks])
                avg_tokens = int(np.mean([t['token_usage'] for t in similar_tasks]))
                confidence = min(len(similar_tasks) / 10.0, 1.0)
            else:
                # Default predictions
                avg_cpu = 50.0
                avg_memory = 256.0
                avg_time = task.estimated_execution_time or 300.0
                avg_tokens = 5000
                confidence = 0.1
            
            return ResourcePrediction(
                cpu_usage=avg_cpu,
                memory_usage=avg_memory,
                execution_time=avg_time,
                token_usage=avg_tokens,
                confidence=confidence,
                model_version="1.0"
            )
            
        except Exception as e:
            logger.error(f"Resource prediction failed: {e}")
            return ResourcePrediction(50.0, 256.0, 300.0, 5000, 0.1, "1.0")
    
    def _find_similar_tasks(self, task: ScheduledTask) -> List[Dict[str, Any]]:
        """Find similar historical tasks"""
        similar_tasks = []
        
        for hist_task in self.execution_history:
            # Simple similarity based on priority and estimated time
            priority_diff = abs(hist_task['priority'] - task.priority)
            time_diff = abs(hist_task['estimated_time'] - (task.estimated_execution_time or 300))
            
            if priority_diff <= 1 and time_diff <= 300:  # Within 5 minutes
                similar_tasks.append(hist_task)
        
        return similar_tasks[-50:]  # Return recent similar tasks
    
    async def _load_execution_history(self):
        """Load historical execution data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT task_id, priority, estimated_time, actual_time,
                           resource_usage, scheduled_at, started_at, completed_at,
                           success
                    FROM task_executions
                    ORDER BY completed_at DESC
                    LIMIT 1000
                """)
                
                for row in cursor.fetchall():
                    task_data = {
                        'task_id': row[0],
                        'priority': row[1],
                        'estimated_time': row[2] or 300,
                        'execution_time': row[3] or 300,
                        'cpu_usage': 50.0,  # Default values for now
                        'memory_usage': 256.0,
                        'token_usage': 5000,
                        'scheduled_at': row[5],
                        'started_at': row[6],
                        'completed_at': row[7],
                        'success': row[8]
                    }
                    
                    # Parse resource usage if available
                    if row[4]:
                        try:
                            resource_data = json.loads(row[4])
                            task_data.update(resource_data)
                        except:
                            pass
                    
                    self.execution_history.append(task_data)
            
            logger.info(f"Loaded {len(self.execution_history)} historical task executions")
            
        except Exception as e:
            logger.error(f"Failed to load execution history: {e}")
    
    def _build_performance_model(self) -> Dict[str, Any]:
        """Build performance prediction model"""
        if len(self.execution_history) < 10:
            return {"type": "default", "ready": False}
        
        try:
            # Simple linear model based on historical data
            priorities = [t['priority'] for t in self.execution_history]
            exec_times = [t['execution_time'] for t in self.execution_history]
            
            # Calculate correlations
            if len(priorities) > 1:
                priority_time_corr = np.corrcoef(priorities, exec_times)[0, 1]
            else:
                priority_time_corr = 0.0
            
            return {
                "type": "linear",
                "ready": True,
                "priority_time_correlation": priority_time_corr,
                "avg_execution_time": np.mean(exec_times),
                "std_execution_time": np.std(exec_times),
                "samples": len(self.execution_history)
            }
            
        except Exception as e:
            logger.error(f"Failed to build performance model: {e}")
            return {"type": "default", "ready": False}
    
    async def _update_scheduling_metrics(
        self, 
        policy: SchedulingPolicy, 
        scheduled_tasks: List[ScheduledTask]
    ):
        """Update scheduling performance metrics"""
        try:
            if not scheduled_tasks:
                return
            
            # Calculate metrics
            now = datetime.now()
            wait_times = []
            
            for task in scheduled_tasks:
                if task.submitted_at:
                    wait_time = (now - task.submitted_at).total_seconds()
                    wait_times.append(wait_time)
            
            avg_wait_time = np.mean(wait_times) if wait_times else 0
            
            # Store metrics
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO scheduling_metrics 
                    (policy, throughput, avg_wait_time, avg_turnaround_time, 
                     resource_utilization, deadline_miss_rate)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    policy.value,
                    len(scheduled_tasks),
                    avg_wait_time,
                    avg_wait_time,  # Simplified turnaround time
                    0.75,  # Default resource utilization
                    0.05   # Default deadline miss rate
                ))
            
        except Exception as e:
            logger.error(f"Failed to update scheduling metrics: {e}")
    
    async def record_task_execution(
        self, 
        task: ScheduledTask, 
        actual_execution_time: float,
        resource_usage: Dict[str, float],
        success: bool,
        error_message: Optional[str] = None
    ):
        """Record completed task execution for learning"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO task_executions 
                    (task_id, priority, estimated_time, actual_time, 
                     resource_requirements, resource_usage, scheduled_at,
                     started_at, completed_at, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.task_id,
                    task.priority,
                    task.estimated_execution_time,
                    actual_execution_time,
                    json.dumps(task.resource_requirements),
                    json.dumps(resource_usage),
                    task.scheduled_at,
                    task.started_at,
                    task.completed_at,
                    success,
                    error_message
                ))
            
            # Update in-memory history
            execution_data = {
                'task_id': task.task_id,
                'priority': task.priority,
                'estimated_time': task.estimated_execution_time or 300,
                'execution_time': actual_execution_time,
                'cpu_usage': resource_usage.get('cpu', 50.0),
                'memory_usage': resource_usage.get('memory', 256.0),
                'token_usage': resource_usage.get('tokens', 5000),
                'success': success
            }
            
            self.execution_history.append(execution_data)
            
            # Rebuild performance model periodically
            if len(self.execution_history) % 100 == 0:
                self.performance_model = self._build_performance_model()
            
        except Exception as e:
            logger.error(f"Failed to record task execution: {e}")
    
    def get_scheduling_stats(self) -> Dict[str, Any]:
        """Get scheduling system statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT policy, AVG(throughput), AVG(avg_wait_time),
                           AVG(resource_utilization), AVG(deadline_miss_rate)
                    FROM scheduling_metrics
                    WHERE measured_at > datetime('now', '-24 hours')
                    GROUP BY policy
                """)
                
                policy_stats = {}
                for row in cursor.fetchall():
                    policy_stats[row[0]] = {
                        'avg_throughput': row[1],
                        'avg_wait_time': row[2],
                        'avg_resource_utilization': row[3],
                        'avg_deadline_miss_rate': row[4]
                    }
                
                return {
                    'total_executions': len(self.execution_history),
                    'policy_performance': policy_stats,
                    'model_ready': self.performance_model.get('ready', False) if self.performance_model else False,
                    'prediction_samples': self.performance_model.get('samples', 0) if self.performance_model else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get scheduling stats: {e}")
            return {}

class TaskScheduler:
    """Main task scheduler component"""
    
    def __init__(self):
        self.predictive_scheduler = PredictiveScheduler()
        self.current_policy = SchedulingPolicy.PREDICTIVE
        self.task_queue = []
        self.running = False
        
        # Performance tracking
        self.policy_performance = defaultdict(lambda: {
            'total_tasks': 0,
            'avg_wait_time': 0.0,
            'success_rate': 1.0
        })
    
    async def start(self):
        """Start the task scheduler"""
        try:
            logger.info("Starting Task Scheduler...")
            
            await self.predictive_scheduler.start()
            
            self.running = True
            logger.info("Task Scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Task Scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the task scheduler"""
        logger.info("Stopping Task Scheduler...")
        
        await self.predictive_scheduler.stop()
        
        self.running = False
        logger.info("Task Scheduler stopped")
    
    async def schedule_task(
        self, 
        task_id: str,
        priority: int = 5,
        estimated_execution_time: Optional[float] = None,
        resource_requirements: Optional[Dict[str, float]] = None,
        deadline: Optional[datetime] = None,
        dependencies: Optional[List[str]] = None
    ) -> ScheduledTask:
        """Schedule a new task"""
        task = ScheduledTask(
            task_id=task_id,
            priority=priority,
            estimated_execution_time=estimated_execution_time or 300.0,
            resource_requirements=resource_requirements or {'cpu': 1.0, 'memory': 256.0},
            deadline=deadline,
            dependencies=dependencies or []
        )
        
        heapq.heappush(self.task_queue, task)
        return task
    
    async def get_next_tasks(
        self, 
        available_resources: Dict[str, float],
        max_tasks: int = 10
    ) -> List[ScheduledTask]:
        """Get next tasks to execute based on current scheduling policy"""
        if not self.task_queue:
            return []
        
        # Get tasks from queue
        tasks_to_schedule = []
        temp_queue = []
        
        while self.task_queue and len(tasks_to_schedule) < max_tasks * 2:
            task = heapq.heappop(self.task_queue)
            tasks_to_schedule.append(task)
        
        # Schedule tasks using predictive scheduler
        scheduled_tasks = await self.predictive_scheduler.schedule_tasks(
            tasks_to_schedule, available_resources, self.current_policy
        )
        
        # Return requested number of tasks, put rest back in queue
        next_tasks = scheduled_tasks[:max_tasks]
        remaining_tasks = scheduled_tasks[max_tasks:]
        
        for task in remaining_tasks:
            heapq.heappush(self.task_queue, task)
        
        # Mark selected tasks as scheduled
        for task in next_tasks:
            task.scheduled_at = datetime.now()
        
        return next_tasks
    
    async def complete_task(
        self, 
        task: ScheduledTask,
        execution_time: float,
        resource_usage: Dict[str, float],
        success: bool,
        error_message: Optional[str] = None
    ):
        """Mark task as completed and update learning data"""
        task.completed_at = datetime.now()
        
        # Record execution for learning
        await self.predictive_scheduler.record_task_execution(
            task, execution_time, resource_usage, success, error_message
        )
        
        # Update policy performance
        policy_stats = self.policy_performance[self.current_policy.value]
        policy_stats['total_tasks'] += 1
        
        if task.scheduled_at:
            wait_time = (task.started_at - task.submitted_at).total_seconds() if task.started_at else 0
            policy_stats['avg_wait_time'] = (
                (policy_stats['avg_wait_time'] * (policy_stats['total_tasks'] - 1) + wait_time) 
                / policy_stats['total_tasks']
            )
        
        if success:
            policy_stats['success_rate'] = (
                (policy_stats['success_rate'] * (policy_stats['total_tasks'] - 1) + 1.0) 
                / policy_stats['total_tasks']
            )
        else:
            policy_stats['success_rate'] = (
                policy_stats['success_rate'] * (policy_stats['total_tasks'] - 1) 
                / policy_stats['total_tasks']
            )
    
    def set_scheduling_policy(self, policy: SchedulingPolicy):
        """Change the scheduling policy"""
        self.current_policy = policy
        logger.info(f"Scheduling policy changed to: {policy.value}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            'queued_tasks': len(self.task_queue),
            'current_policy': self.current_policy.value,
            'policy_performance': dict(self.policy_performance),
            'running': self.running
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        stats = self.predictive_scheduler.get_scheduling_stats()
        stats.update({
            'queue_length': len(self.task_queue),
            'current_policy': self.current_policy.value,
            'policy_performance': dict(self.policy_performance)
        })
        return stats