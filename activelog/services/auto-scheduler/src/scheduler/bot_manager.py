import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    THROTTLED = "throttled"

@dataclass
class Task:
    id: str
    name: str
    priority: TaskPriority
    estimated_duration: float  # hours
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    bot_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Bot:
    id: str
    name: str
    daily_limit_hours: float = 5.0
    used_hours_today: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)
    current_task: Optional[str] = None
    is_active: bool = True
    capabilities: List[str] = field(default_factory=list)
    performance_score: float = 1.0

class BotManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bots: Dict[str, Bot] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []
        self.running_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.failed_tasks: Dict[str, Task] = {}
        self.maintenance_windows: List[Dict[str, Any]] = []
        self.resource_reservations: Dict[str, Any] = {}
        
        # Night acceleration settings
        self.night_start_hour = config.get('night_start_hour', 22)  # 10 PM
        self.night_end_hour = config.get('night_end_hour', 6)      # 6 AM
        self.night_acceleration_hour = config.get('night_acceleration_hour', 3)  # 3 AM
        self.night_multiplier = config.get('night_multiplier', 2.0)
        
        # Initialize default bots
        self._initialize_bots()
    
    def _initialize_bots(self):
        """Initialize default bot configurations"""
        default_bots = [
            {"id": "scheduler-bot-1", "name": "Primary Scheduler", "capabilities": ["scheduling", "backup", "monitoring"]},
            {"id": "backup-bot-1", "name": "Backup Specialist", "capabilities": ["backup", "archival", "verification"]},
            {"id": "analytics-bot-1", "name": "Analytics Engine", "capabilities": ["analytics", "reporting", "optimization"]},
            {"id": "maintenance-bot-1", "name": "System Maintenance", "capabilities": ["maintenance", "cleanup", "health-check"]}
        ]
        
        for bot_config in default_bots:
            bot = Bot(**bot_config)
            self.bots[bot.id] = bot
    
    def reset_daily_limits(self):
        """Reset daily bot usage limits"""
        now = datetime.now()
        for bot in self.bots.values():
            if now.date() > bot.last_reset.date():
                bot.used_hours_today = 0.0
                bot.last_reset = now
                logger.info(f"Reset daily limit for bot {bot.id}")
    
    def get_available_capacity(self, bot_id: str) -> float:
        """Get remaining available hours for a bot today"""
        if bot_id not in self.bots:
            return 0.0
        
        bot = self.bots[bot_id]
        self.reset_daily_limits()
        
        # Apply night acceleration
        multiplier = self._get_time_multiplier()
        effective_limit = bot.daily_limit_hours * multiplier
        
        return max(0.0, effective_limit - bot.used_hours_today)
    
    def _get_time_multiplier(self) -> float:
        """Get time multiplier based on current hour"""
        current_hour = datetime.now().hour
        
        # Night acceleration between 10 PM and 6 AM, peak at 3 AM
        if (current_hour >= self.night_start_hour or 
            current_hour <= self.night_end_hour):
            
            if current_hour == self.night_acceleration_hour:
                return self.night_multiplier
            else:
                # Gradual increase/decrease around 3 AM
                distance_from_peak = min(
                    abs(current_hour - self.night_acceleration_hour),
                    abs(current_hour + 24 - self.night_acceleration_hour) if current_hour < 12 else 24
                )
                factor = max(0, (4 - distance_from_peak) / 4)  # Ramp over 4 hours
                return 1.0 + (self.night_multiplier - 1.0) * factor
        
        return 1.0
    
    def should_throttle_bot(self, bot_id: str, task_duration: float) -> bool:
        """Check if bot should be throttled based on remaining capacity"""
        available = self.get_available_capacity(bot_id)
        threshold = self.config.get('throttle_threshold', 0.5)  # Hours
        
        # Smart throttling based on time of day and task priority
        current_hour = datetime.now().hour
        multiplier = self._get_time_multiplier()
        
        # Less aggressive throttling during night hours when capacity is higher
        adjusted_threshold = threshold / multiplier if multiplier > 1.0 else threshold
        
        return available < (task_duration + adjusted_threshold)
    
    def add_task(self, task: Task) -> bool:
        """Add a new task to the queue"""
        if task.id in self.tasks:
            logger.warning(f"Task {task.id} already exists")
            return False
        
        self.tasks[task.id] = task
        self._insert_task_by_priority(task.id)
        logger.info(f"Added task {task.id} with priority {task.priority}")
        return True
    
    def _insert_task_by_priority(self, task_id: str):
        """Insert task in queue based on priority and deadline"""
        task = self.tasks[task_id]
        
        # Find insertion point based on priority and deadline
        insert_pos = len(self.task_queue)
        for i, existing_id in enumerate(self.task_queue):
            existing_task = self.tasks[existing_id]
            
            # Higher priority (lower number) goes first
            if task.priority.value < existing_task.priority.value:
                insert_pos = i
                break
            
            # Same priority, check deadline
            if (task.priority.value == existing_task.priority.value and 
                task.deadline and existing_task.deadline):
                if task.deadline < existing_task.deadline:
                    insert_pos = i
                    break
        
        self.task_queue.insert(insert_pos, task_id)
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next task to execute with intelligent deadline management"""
        while self.task_queue:
            task_id = self.task_queue[0]
            task = self.tasks[task_id]
            
            # Check if dependencies are met
            if not self._dependencies_met(task):
                # Move to end of queue and try next
                self.task_queue.pop(0)
                self.task_queue.append(task_id)
                continue
            
            # Check deadline urgency - override maintenance if critical
            if task.deadline:
                time_to_deadline = (task.deadline - datetime.now()).total_seconds() / 3600
                if time_to_deadline <= task.estimated_duration * 1.5:  # Less than 1.5x estimated time
                    logger.warning(f"Task {task_id} approaching deadline, bypassing maintenance window")
                    return task
            
            # Check if in maintenance window
            if self._in_maintenance_window():
                # Allow high priority tasks during maintenance
                if task.priority.value <= 2:  # CRITICAL or HIGH
                    logger.info(f"Allowing high priority task {task_id} during maintenance")
                    return task
                else:
                    logger.info("In maintenance window, deferring non-critical tasks")
                    return None
            
            return task
        
        return None
    
    def _dependencies_met(self, task: Task) -> bool:
        """Check if all task dependencies are completed"""
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
        return True
    
    def _in_maintenance_window(self) -> bool:
        """Check if current time is in a maintenance window"""
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()  # 0 = Monday
        
        for window in self.maintenance_windows:
            if (window.get('day') == current_day and
                window.get('start_time') <= current_time <= window.get('end_time')):
                return True
        return False
    
    def assign_task_to_bot(self, task_id: str) -> Optional[str]:
        """Assign task to the best available bot with smart throttling"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        best_bot = None
        best_score = -1
        throttled_bots = []
        
        for bot_id, bot in self.bots.items():
            if not bot.is_active or bot.current_task:
                continue
            
            # Check if bot has required capabilities
            if (task.resource_requirements.get('capabilities') and
                not all(cap in bot.capabilities for cap in task.resource_requirements['capabilities'])):
                continue
            
            # Check if bot should be throttled
            if self.should_throttle_bot(bot_id, task.estimated_duration):
                throttled_bots.append(bot_id)
                continue
            
            # Calculate assignment score
            score = self._calculate_assignment_score(bot, task)
            if score > best_score:
                best_score = score
                best_bot = bot_id
        
        # If no bot available but task is critical/urgent, try throttled bots
        if not best_bot and (task.priority.value <= 2 or self._is_task_urgent(task)):
            logger.warning(f"No available bots for urgent task {task_id}, checking throttled bots")
            for bot_id in throttled_bots:
                bot = self.bots[bot_id]
                available = self.get_available_capacity(bot_id)
                if available >= task.estimated_duration * 0.8:  # Allow if at least 80% capacity
                    best_bot = bot_id
                    logger.info(f"Assigned urgent task {task_id} to throttled bot {bot_id}")
                    break
        
        if best_bot:
            self._assign_task(task_id, best_bot)
            return best_bot
        else:
            task.status = TaskStatus.THROTTLED
            return None
    
    def _is_task_urgent(self, task: Task) -> bool:
        """Check if a task is urgent based on deadline"""
        if not task.deadline:
            return False
        
        time_to_deadline = (task.deadline - datetime.now()).total_seconds() / 3600
        return time_to_deadline <= task.estimated_duration * 2.0
    
    def _calculate_assignment_score(self, bot: Bot, task: Task) -> float:
        """Calculate how well a bot fits a task"""
        score = bot.performance_score
        
        # Bonus for matching capabilities
        if task.resource_requirements.get('capabilities'):
            matches = sum(1 for cap in task.resource_requirements['capabilities'] 
                         if cap in bot.capabilities)
            total_required = len(task.resource_requirements['capabilities'])
            score += (matches / total_required) * 0.5
        
        # Penalty for high usage
        usage_ratio = bot.used_hours_today / bot.daily_limit_hours
        score -= usage_ratio * 0.3
        
        # Bonus for available capacity
        available = self.get_available_capacity(bot.id)
        if available >= task.estimated_duration:
            score += min(available / task.estimated_duration, 2.0) * 0.2
        
        return score
    
    def _assign_task(self, task_id: str, bot_id: str):
        """Assign a task to a bot"""
        task = self.tasks[task_id]
        bot = self.bots[bot_id]
        
        task.bot_id = bot_id
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        bot.current_task = task_id
        
        self.running_tasks[task_id] = task
        self.task_queue.remove(task_id)
        
        logger.info(f"Assigned task {task_id} to bot {bot_id}")
    
    def complete_task(self, task_id: str, success: bool = True):
        """Mark a task as completed or failed"""
        if task_id not in self.running_tasks:
            return
        
        task = self.running_tasks[task_id]
        bot = self.bots[task.bot_id]
        
        task.completed_at = datetime.now()
        duration = (task.completed_at - task.started_at).total_seconds() / 3600
        
        # Update bot usage
        bot.used_hours_today += duration
        bot.current_task = None
        
        # Update performance score
        if success:
            task.status = TaskStatus.COMPLETED
            self.completed_tasks[task_id] = task
            bot.performance_score = min(2.0, bot.performance_score + 0.01)
            logger.info(f"Task {task_id} completed successfully by {task.bot_id}")
        else:
            task.status = TaskStatus.FAILED
            self.failed_tasks[task_id] = task
            bot.performance_score = max(0.1, bot.performance_score - 0.05)
            logger.warning(f"Task {task_id} failed on {task.bot_id}")
        
        del self.running_tasks[task_id]
    
    def add_maintenance_window(self, day: int, start_time: str, end_time: str, description: str = ""):
        """Add a maintenance window (day: 0=Monday, time: HH:MM format)"""
        from datetime import time
        
        window = {
            'day': day,
            'start_time': time.fromisoformat(start_time),
            'end_time': time.fromisoformat(end_time),
            'description': description
        }
        self.maintenance_windows.append(window)
        logger.info(f"Added maintenance window: {description}")
    
    def reserve_resources(self, resource_type: str, amount: Any, duration: timedelta, task_id: str):
        """Reserve resources for a task"""
        if resource_type not in self.resource_reservations:
            self.resource_reservations[resource_type] = {}
        
        reservation = {
            'amount': amount,
            'expires_at': datetime.now() + duration,
            'task_id': task_id
        }
        
        self.resource_reservations[resource_type][task_id] = reservation
        logger.info(f"Reserved {amount} {resource_type} for task {task_id}")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current system status summary"""
        self.reset_daily_limits()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'bots': {
                'total': len(self.bots),
                'active': sum(1 for bot in self.bots.values() if bot.is_active),
                'busy': sum(1 for bot in self.bots.values() if bot.current_task),
                'details': [
                    {
                        'id': bot.id,
                        'name': bot.name,
                        'used_hours': bot.used_hours_today,
                        'available_hours': self.get_available_capacity(bot.id),
                        'current_task': bot.current_task,
                        'performance': bot.performance_score
                    }
                    for bot in self.bots.values()
                ]
            },
            'tasks': {
                'queued': len(self.task_queue),
                'running': len(self.running_tasks),
                'completed': len(self.completed_tasks),
                'failed': len(self.failed_tasks),
                'throttled': sum(1 for task in self.tasks.values() 
                               if task.status == TaskStatus.THROTTLED)
            },
            'time_multiplier': self._get_time_multiplier(),
            'in_maintenance': self._in_maintenance_window()
        }