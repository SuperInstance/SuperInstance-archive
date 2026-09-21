# src/orchestrator/task_manager.py

import asyncio
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from enum import Enum


class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    HELP_NEEDED = "help_needed"


@dataclass
class Task:
    task_id: str
    bot_type: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    assigned_to: str = None
    completed_at: datetime = None
    result: Any = None
    error: str = None
    user_id: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """Manages task queue and distribution"""

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.queue: Dict[TaskPriority, List[Task]] = {
            priority: [] for priority in TaskPriority
        }
        self.lock = asyncio.Lock()

    async def create_task(self, bot_type: str, description: str,
                          priority: str = "medium", **kwargs) -> Dict[str, Any]:
        """Create a new task"""
        async with self.lock:
            task = Task(
                task_id=str(uuid.uuid4()),
                bot_type=bot_type,
                description=description,
                priority=TaskPriority[priority.upper()],
                status=TaskStatus.QUEUED,
                created_at=datetime.now(),
                **kwargs
            )

            self.tasks[task.task_id] = task
            self.queue[task.priority].append(task)

            return self._task_to_dict(task)

    async def get_next_task(self, bot_type: str = None) -> Dict[str, Any]:
        """Get next task from queue, optionally filtered by bot type"""
        async with self.lock:
            # Check queues from highest to lowest priority
            for priority in sorted(TaskPriority, key=lambda x: x.value, reverse=True):
                queue = self.queue[priority]

                for task in queue:
                    if task.status == TaskStatus.QUEUED:
                        if bot_type is None or task.bot_type == bot_type:
                            task.status = TaskStatus.ASSIGNED
                            return self._task_to_dict(task)

            return None

    async def update_task_status(self, task_id: str, status: TaskStatus,
                                 assigned_to: str = None, result: Any = None,
                                 error: str = None):
        """Update task status"""
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = status

                if assigned_to:
                    task.assigned_to = assigned_to
                if result:
                    task.result = result
                if error:
                    task.error = error
                if status == TaskStatus.COMPLETED:
                    task.completed_at = datetime.now()

    def get_queue_status(self) -> Dict[str, Any]:
        """Get status of all queues"""
        return {
            priority.name: {
                'queued': len([t for t in queue if t.status == TaskStatus.QUEUED]),
                'assigned': len([t for t in queue if t.status == TaskStatus.ASSIGNED]),
                'in_progress': len([t for t in queue if t.status == TaskStatus.IN_PROGRESS]),
                'help_needed': len([t for t in queue if t.status == TaskStatus.HELP_NEEDED])
            }
            for priority, queue in self.queue.items()
        }

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            'task_id': task.task_id,
            'bot_type': task.bot_type,
            'description': task.description,
            'priority': task.priority.name,
            'status': task.status.value,
            'assigned_to': task.assigned_to,
            'created_at': task.created_at.isoformat(),
            'metadata': task.metadata
        }
