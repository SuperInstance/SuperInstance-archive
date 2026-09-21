import asyncio
import logging
import time
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from datetime import datetime, timedelta
import heapq
import threading

logger = logging.getLogger(__name__)

class QueuePriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3

@dataclass
class QueuedTask:
    id: str
    priority: QueuePriority
    estimated_duration: int
    dependencies: Set[str] = field(default_factory=set)
    resources_required: Dict[str, int] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    submitted_at: datetime = field(default_factory=datetime.now)
    attempts: int = 0
    max_attempts: int = 3
    
    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority.value < other.priority.value
        if self.deadline and other.deadline:
            return self.deadline < other.deadline
        return self.submitted_at < other.submitted_at

class ResourcePool:
    def __init__(self):
        self.resources = {
            "cpu_cores": 8,
            "memory_gb": 32,
            "gpu_memory": 16,
            "api_tokens": 100000,
            "concurrent_requests": 50
        }
        self.allocated = defaultdict(int)
        self.reservations = {}
        self.lock = threading.Lock()
    
    def can_allocate(self, task_id: str, requirements: Dict[str, int]) -> bool:
        """Check if resources can be allocated for a task"""
        with self.lock:
            for resource, amount in requirements.items():
                available = self.resources.get(resource, 0) - self.allocated[resource]
                if available < amount:
                    return False
            return True
    
    def allocate(self, task_id: str, requirements: Dict[str, int]) -> bool:
        """Allocate resources for a task"""
        with self.lock:
            if not self.can_allocate(task_id, requirements):
                return False
            
            for resource, amount in requirements.items():
                self.allocated[resource] += amount
            
            self.reservations[task_id] = requirements.copy()
            logger.debug(f"Allocated resources for task {task_id}: {requirements}")
            return True
    
    def release(self, task_id: str):
        """Release resources allocated to a task"""
        with self.lock:
            if task_id in self.reservations:
                for resource, amount in self.reservations[task_id].items():
                    self.allocated[resource] = max(0, self.allocated[resource] - amount)
                del self.reservations[task_id]
                logger.debug(f"Released resources for task {task_id}")
    
    def get_utilization(self) -> Dict[str, float]:
        """Get current resource utilization percentages"""
        with self.lock:
            utilization = {}
            for resource, total in self.resources.items():
                used = self.allocated[resource]
                utilization[resource] = (used / total * 100) if total > 0 else 0
            return utilization

class DependencyResolver:
    def __init__(self):
        self.dependency_graph = defaultdict(set)
        self.reverse_graph = defaultdict(set)
        self.completed_tasks = set()
        self.failed_tasks = set()
    
    def add_dependency(self, task_id: str, depends_on: str):
        """Add a dependency relationship"""
        self.dependency_graph[task_id].add(depends_on)
        self.reverse_graph[depends_on].add(task_id)
    
    def remove_dependency(self, task_id: str, depends_on: str):
        """Remove a dependency relationship"""
        self.dependency_graph[task_id].discard(depends_on)
        self.reverse_graph[depends_on].discard(task_id)
    
    def is_ready(self, task_id: str) -> bool:
        """Check if a task's dependencies are satisfied"""
        dependencies = self.dependency_graph.get(task_id, set())
        return all(dep in self.completed_tasks for dep in dependencies)
    
    def get_ready_tasks(self, pending_tasks: Set[str]) -> Set[str]:
        """Get all tasks whose dependencies are satisfied"""
        ready = set()
        for task_id in pending_tasks:
            if task_id not in self.failed_tasks and self.is_ready(task_id):
                ready.add(task_id)
        return ready
    
    def mark_completed(self, task_id: str) -> Set[str]:
        """Mark a task as completed and return newly ready tasks"""
        self.completed_tasks.add(task_id)
        self.failed_tasks.discard(task_id)
        
        newly_ready = set()
        for dependent in self.reverse_graph.get(task_id, set()):
            if self.is_ready(dependent) and dependent not in self.completed_tasks:
                newly_ready.add(dependent)
        
        return newly_ready
    
    def mark_failed(self, task_id: str) -> Set[str]:
        """Mark a task as failed and return affected dependent tasks"""
        self.failed_tasks.add(task_id)
        
        # Find all tasks that depend on this failed task (directly or indirectly)
        affected = set()
        to_check = {task_id}
        
        while to_check:
            current = to_check.pop()
            for dependent in self.reverse_graph.get(current, set()):
                if dependent not in affected and dependent not in self.completed_tasks:
                    affected.add(dependent)
                    to_check.add(dependent)
        
        # Mark affected tasks as failed
        for task in affected:
            self.failed_tasks.add(task)
        
        return affected
    
    def detect_cycles(self, task_ids: Set[str]) -> List[List[str]]:
        """Detect dependency cycles using DFS"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependency_graph.get(node, set()):
                if neighbor in task_ids and dfs(neighbor):
                    return True
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        for task_id in task_ids:
            if task_id not in visited:
                dfs(task_id)
        
        return cycles

class TaskQueue:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.priority_queue = []
        self.task_lookup = {}
        self.pending_tasks = set()
        self.in_progress_tasks = set()
        self.completed_tasks = set()
        self.failed_tasks = set()
        
        self.resource_pool = ResourcePool()
        self.dependency_resolver = DependencyResolver()
        
        self.queue_lock = asyncio.Lock()
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "average_wait_time": 0.0,
            "average_execution_time": 0.0
        }
        
        # Deadlock detection
        self.deadlock_check_interval = 60  # seconds
        self.last_deadlock_check = datetime.now()
    
    async def submit(self, task: QueuedTask) -> bool:
        """Submit a task to the queue"""
        async with self.queue_lock:
            if len(self.priority_queue) >= self.max_size:
                logger.warning("Queue is full, rejecting task")
                return False
            
            # Check for dependency cycles before adding
            test_dependencies = self.dependency_resolver.dependency_graph.copy()
            for dep in task.dependencies:
                test_dependencies[task.id].add(dep)
            
            cycles = self.dependency_resolver.detect_cycles({task.id} | task.dependencies)
            if cycles:
                logger.error(f"Task {task.id} would create dependency cycles: {cycles}")
                return False
            
            # Add task to queue
            heapq.heappush(self.priority_queue, task)
            self.task_lookup[task.id] = task
            self.pending_tasks.add(task.id)
            
            # Add dependencies
            for dep in task.dependencies:
                self.dependency_resolver.add_dependency(task.id, dep)
            
            self.stats["total_submitted"] += 1
            logger.info(f"Task {task.id} submitted to queue")
            return True
    
    async def get_next_ready_task(self) -> Optional[QueuedTask]:
        """Get the next task that's ready to execute"""
        async with self.queue_lock:
            ready_tasks = self.dependency_resolver.get_ready_tasks(self.pending_tasks)
            
            # Find the highest priority ready task
            best_task = None
            best_index = -1
            
            for i, task in enumerate(self.priority_queue):
                if task.id in ready_tasks and self.resource_pool.can_allocate(
                    task.id, task.resources_required
                ):
                    if best_task is None or task < best_task:
                        best_task = task
                        best_index = i
            
            if best_task:
                # Remove from priority queue
                self.priority_queue[best_index] = self.priority_queue[-1]
                self.priority_queue.pop()
                if self.priority_queue:
                    heapq.heapify(self.priority_queue)
                
                # Allocate resources
                if self.resource_pool.allocate(best_task.id, best_task.resources_required):
                    self.pending_tasks.remove(best_task.id)
                    self.in_progress_tasks.add(best_task.id)
                    return best_task
                else:
                    # Put back if allocation failed
                    heapq.heappush(self.priority_queue, best_task)
            
            return None
    
    async def mark_completed(self, task_id: str):
        """Mark a task as completed"""
        async with self.queue_lock:
            if task_id in self.in_progress_tasks:
                self.in_progress_tasks.remove(task_id)
                self.completed_tasks.add(task_id)
                self.resource_pool.release(task_id)
                
                # Update dependency resolver
                newly_ready = self.dependency_resolver.mark_completed(task_id)
                
                # Update statistics
                self.stats["total_completed"] += 1
                
                if task_id in self.task_lookup:
                    task = self.task_lookup[task_id]
                    wait_time = (datetime.now() - task.submitted_at).total_seconds()
                    self._update_average_wait_time(wait_time)
                
                logger.info(f"Task {task_id} completed, {len(newly_ready)} tasks now ready")
    
    async def mark_failed(self, task_id: str, reason: str = ""):
        """Mark a task as failed"""
        async with self.queue_lock:
            if task_id in self.in_progress_tasks:
                self.in_progress_tasks.remove(task_id)
                self.failed_tasks.add(task_id)
                self.resource_pool.release(task_id)
                
                # Handle dependent tasks
                affected_tasks = self.dependency_resolver.mark_failed(task_id)
                
                # Update statistics
                self.stats["total_failed"] += 1 + len(affected_tasks)
                
                logger.error(f"Task {task_id} failed: {reason}, {len(affected_tasks)} dependent tasks affected")
    
    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        async with self.queue_lock:
            if task_id not in self.task_lookup:
                return False
            
            task = self.task_lookup[task_id]
            if task.attempts >= task.max_attempts:
                logger.warning(f"Task {task_id} exceeded max retry attempts")
                return False
            
            task.attempts += 1
            
            # Move back to pending
            if task_id in self.failed_tasks:
                self.failed_tasks.remove(task_id)
                self.pending_tasks.add(task_id)
                heapq.heappush(self.priority_queue, task)
                
                logger.info(f"Task {task_id} queued for retry (attempt {task.attempts})")
                return True
            
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or in-progress task"""
        async with self.queue_lock:
            if task_id in self.pending_tasks:
                self.pending_tasks.remove(task_id)
                # Remove from priority queue
                self.priority_queue = [t for t in self.priority_queue if t.id != task_id]
                heapq.heapify(self.priority_queue)
                
            elif task_id in self.in_progress_tasks:
                self.in_progress_tasks.remove(task_id)
                self.resource_pool.release(task_id)
            
            if task_id in self.task_lookup:
                del self.task_lookup[task_id]
                logger.info(f"Task {task_id} cancelled")
                return True
            
            return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics"""
        async with self.queue_lock:
            return {
                "queue_size": len(self.priority_queue),
                "pending_tasks": len(self.pending_tasks),
                "in_progress_tasks": len(self.in_progress_tasks),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "resource_utilization": self.resource_pool.get_utilization(),
                "statistics": self.stats.copy()
            }
    
    async def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific task"""
        async with self.queue_lock:
            if task_id not in self.task_lookup:
                return None
            
            task = self.task_lookup[task_id]
            
            status = "unknown"
            if task_id in self.pending_tasks:
                status = "pending"
            elif task_id in self.in_progress_tasks:
                status = "in_progress"
            elif task_id in self.completed_tasks:
                status = "completed"
            elif task_id in self.failed_tasks:
                status = "failed"
            
            return {
                "id": task.id,
                "status": status,
                "priority": task.priority.name,
                "estimated_duration": task.estimated_duration,
                "dependencies": list(task.dependencies),
                "resources_required": task.resources_required,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "submitted_at": task.submitted_at.isoformat(),
                "attempts": task.attempts,
                "max_attempts": task.max_attempts,
                "dependencies_ready": self.dependency_resolver.is_ready(task_id)
            }
    
    async def detect_deadlocks(self) -> List[Dict[str, Any]]:
        """Detect potential deadlocks in the task queue"""
        now = datetime.now()
        if (now - self.last_deadlock_check).total_seconds() < self.deadlock_check_interval:
            return []
        
        self.last_deadlock_check = now
        
        async with self.queue_lock:
            # Look for tasks that have been waiting too long
            deadlocks = []
            
            # Check for dependency cycles
            cycles = self.dependency_resolver.detect_cycles(self.pending_tasks)
            for cycle in cycles:
                deadlocks.append({
                    "type": "dependency_cycle",
                    "tasks": cycle,
                    "description": f"Circular dependency detected: {' -> '.join(cycle)}"
                })
            
            # Check for resource deadlocks
            waiting_too_long = []
            for task_id in self.pending_tasks:
                task = self.task_lookup[task_id]
                wait_time = (now - task.submitted_at).total_seconds()
                
                if wait_time > 300:  # 5 minutes
                    if self.dependency_resolver.is_ready(task_id):
                        if not self.resource_pool.can_allocate(task_id, task.resources_required):
                            waiting_too_long.append({
                                "task_id": task_id,
                                "wait_time": wait_time,
                                "required_resources": task.resources_required
                            })
            
            if waiting_too_long:
                deadlocks.append({
                    "type": "resource_starvation",
                    "tasks": waiting_too_long,
                    "description": f"{len(waiting_too_long)} tasks waiting for resources"
                })
            
            return deadlocks
    
    async def optimize_queue(self):
        """Optimize queue ordering based on current conditions"""
        async with self.queue_lock:
            # Rebalance priorities based on waiting time and deadlines
            current_time = datetime.now()
            
            for task in self.priority_queue:
                wait_time = (current_time - task.submitted_at).total_seconds()
                
                # Boost priority for tasks waiting too long
                if wait_time > 180:  # 3 minutes
                    if task.priority.value > 0:
                        task.priority = QueuePriority(task.priority.value - 1)
                
                # Boost priority for tasks approaching deadline
                if task.deadline:
                    time_to_deadline = (task.deadline - current_time).total_seconds()
                    if time_to_deadline < 600:  # 10 minutes
                        task.priority = QueuePriority.CRITICAL
            
            # Re-heapify to maintain priority order
            heapq.heapify(self.priority_queue)
    
    def _update_average_wait_time(self, new_wait_time: float):
        """Update running average of wait times"""
        if self.stats["total_completed"] == 1:
            self.stats["average_wait_time"] = new_wait_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats["average_wait_time"] = (
                alpha * new_wait_time + 
                (1 - alpha) * self.stats["average_wait_time"]
            )

class TaskQueueManager:
    def __init__(self, num_queues: int = 3):
        self.queues = {
            "critical": TaskQueue(max_size=100),
            "high": TaskQueue(max_size=300),
            "normal": TaskQueue(max_size=600)
        }
        self.routing_rules = {
            QueuePriority.CRITICAL: "critical",
            QueuePriority.HIGH: "critical",
            QueuePriority.MEDIUM: "high",
            QueuePriority.LOW: "normal"
        }
        self.background_tasks = []
        self.running = False
    
    async def start(self):
        """Start background optimization tasks"""
        self.running = True
        
        # Start optimization tasks
        self.background_tasks.append(
            asyncio.create_task(self._optimization_loop())
        )
        self.background_tasks.append(
            asyncio.create_task(self._deadlock_detection_loop())
        )
        
        logger.info("Task Queue Manager started")
    
    async def stop(self):
        """Stop background tasks"""
        self.running = False
        
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        logger.info("Task Queue Manager stopped")
    
    async def submit_task(self, task: QueuedTask) -> bool:
        """Submit task to appropriate queue"""
        queue_name = self.routing_rules.get(task.priority, "normal")
        queue = self.queues[queue_name]
        return await queue.submit(task)
    
    async def get_next_task(self) -> Optional[Tuple[str, QueuedTask]]:
        """Get next ready task from any queue (priority order)"""
        for queue_name in ["critical", "high", "normal"]:
            queue = self.queues[queue_name]
            task = await queue.get_next_ready_task()
            if task:
                return queue_name, task
        return None
    
    async def mark_task_completed(self, task_id: str):
        """Mark task as completed in all queues"""
        for queue in self.queues.values():
            await queue.mark_completed(task_id)
    
    async def mark_task_failed(self, task_id: str, reason: str = ""):
        """Mark task as failed in all queues"""
        for queue in self.queues.values():
            await queue.mark_failed(task_id, reason)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get status across all queues"""
        status = {}
        total_stats = {
            "total_pending": 0,
            "total_in_progress": 0,
            "total_completed": 0,
            "total_failed": 0
        }
        
        for queue_name, queue in self.queues.items():
            queue_status = await queue.get_queue_status()
            status[queue_name] = queue_status
            
            total_stats["total_pending"] += queue_status["pending_tasks"]
            total_stats["total_in_progress"] += queue_status["in_progress_tasks"]
            total_stats["total_completed"] += queue_status["completed_tasks"]
            total_stats["total_failed"] += queue_status["failed_tasks"]
        
        status["totals"] = total_stats
        return status
    
    async def _optimization_loop(self):
        """Background task to optimize queues"""
        while self.running:
            try:
                for queue in self.queues.values():
                    await queue.optimize_queue()
                await asyncio.sleep(30)  # Optimize every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue optimization error: {e}")
                await asyncio.sleep(60)
    
    async def _deadlock_detection_loop(self):
        """Background task to detect deadlocks"""
        while self.running:
            try:
                all_deadlocks = []
                for queue_name, queue in self.queues.items():
                    deadlocks = await queue.detect_deadlocks()
                    for deadlock in deadlocks:
                        deadlock["queue"] = queue_name
                    all_deadlocks.extend(deadlocks)
                
                if all_deadlocks:
                    logger.warning(f"Detected {len(all_deadlocks)} potential deadlocks")
                    for deadlock in all_deadlocks:
                        logger.warning(f"Deadlock in {deadlock['queue']}: {deadlock['description']}")
                
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Deadlock detection error: {e}")
                await asyncio.sleep(120)