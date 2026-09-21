import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import concurrent.futures
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

class ExecutionStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    MAP_REDUCE = "map_reduce"

class ResourceType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    NETWORK = "network"
    API_QUOTA = "api_quota"

@dataclass
class ResourceRequirement:
    resource_type: ResourceType
    amount: float
    max_amount: Optional[float] = None
    priority: int = 1

@dataclass
class ExecutionPlan:
    id: str
    tasks: List[str]
    strategy: ExecutionStrategy
    dependencies: Dict[str, Set[str]] = field(default_factory=dict)
    resource_requirements: Dict[str, List[ResourceRequirement]] = field(default_factory=dict)
    max_parallel_tasks: int = 10
    timeout: int = 3600
    created_at: datetime = field(default_factory=datetime.now)
    estimated_duration: int = 0

class WorkerBot:
    def __init__(self, bot_id: str, capabilities: Dict[str, Any], max_concurrent: int = 3):
        self.bot_id = bot_id
        self.capabilities = capabilities
        self.max_concurrent = max_concurrent
        self.current_tasks = set()
        self.completed_tasks = []
        self.failed_tasks = []
        self.total_execution_time = 0
        self.is_healthy = True
        self.last_health_check = datetime.now()
        self.performance_metrics = {
            "avg_task_time": 0,
            "success_rate": 100,
            "throughput": 0,
            "error_count": 0
        }
        self.lock = threading.Lock()
    
    def can_accept_task(self, task_id: str, requirements: List[ResourceRequirement]) -> bool:
        """Check if bot can accept a new task"""
        with self.lock:
            if len(self.current_tasks) >= self.max_concurrent:
                return False
            
            if not self.is_healthy:
                return False
            
            # Check capability matching
            for req in requirements:
                capability_key = f"{req.resource_type.value}_capacity"
                if capability_key not in self.capabilities:
                    return False
                
                if self.capabilities[capability_key] < req.amount:
                    return False
            
            return True
    
    def assign_task(self, task_id: str) -> bool:
        """Assign a task to this bot"""
        with self.lock:
            if len(self.current_tasks) >= self.max_concurrent:
                return False
            
            self.current_tasks.add(task_id)
            return True
    
    def complete_task(self, task_id: str, execution_time: float, success: bool):
        """Mark a task as completed"""
        with self.lock:
            if task_id in self.current_tasks:
                self.current_tasks.remove(task_id)
                
                if success:
                    self.completed_tasks.append({
                        "task_id": task_id,
                        "execution_time": execution_time,
                        "completed_at": datetime.now()
                    })
                else:
                    self.failed_tasks.append({
                        "task_id": task_id,
                        "execution_time": execution_time,
                        "failed_at": datetime.now()
                    })
                
                self._update_metrics(execution_time, success)
    
    def _update_metrics(self, execution_time: float, success: bool):
        """Update performance metrics"""
        self.total_execution_time += execution_time
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        
        if total_tasks > 0:
            self.performance_metrics["avg_task_time"] = self.total_execution_time / total_tasks
            self.performance_metrics["success_rate"] = (
                len(self.completed_tasks) / total_tasks * 100
            )
            self.performance_metrics["throughput"] = total_tasks / max(1, 
                (datetime.now() - self.last_health_check).total_seconds() / 3600
            )
        
        if not success:
            self.performance_metrics["error_count"] += 1
    
    def get_load_factor(self) -> float:
        """Get current load factor (0.0 to 1.0)"""
        with self.lock:
            return len(self.current_tasks) / self.max_concurrent

class ResourceManager:
    def __init__(self):
        self.global_resources = {
            ResourceType.CPU: 16.0,
            ResourceType.MEMORY: 64.0,
            ResourceType.GPU: 8.0,
            ResourceType.NETWORK: 1000.0,
            ResourceType.API_QUOTA: 100000.0
        }
        self.allocated_resources = defaultdict(float)
        self.resource_reservations = {}
        self.lock = threading.Lock()
    
    def can_allocate(self, task_id: str, requirements: List[ResourceRequirement]) -> bool:
        """Check if resources can be allocated"""
        with self.lock:
            for req in requirements:
                available = self.global_resources[req.resource_type] - self.allocated_resources[req.resource_type]
                if available < req.amount:
                    return False
            return True
    
    def allocate_resources(self, task_id: str, requirements: List[ResourceRequirement]) -> bool:
        """Allocate resources for a task"""
        with self.lock:
            if not self.can_allocate(task_id, requirements):
                return False
            
            allocated = {}
            for req in requirements:
                self.allocated_resources[req.resource_type] += req.amount
                allocated[req.resource_type] = req.amount
            
            self.resource_reservations[task_id] = allocated
            return True
    
    def release_resources(self, task_id: str):
        """Release resources allocated to a task"""
        with self.lock:
            if task_id in self.resource_reservations:
                for resource_type, amount in self.resource_reservations[task_id].items():
                    self.allocated_resources[resource_type] -= amount
                    self.allocated_resources[resource_type] = max(0, self.allocated_resources[resource_type])
                
                del self.resource_reservations[task_id]
    
    def get_resource_utilization(self) -> Dict[ResourceType, float]:
        """Get current resource utilization"""
        with self.lock:
            utilization = {}
            for resource_type, total in self.global_resources.items():
                used = self.allocated_resources[resource_type]
                utilization[resource_type] = (used / total * 100) if total > 0 else 0
            return utilization

class LoadBalancer:
    def __init__(self, bots: Dict[str, WorkerBot], resource_manager: ResourceManager):
        self.bots = bots
        self.resource_manager = resource_manager
        self.task_assignments = {}
        self.load_balancing_strategies = {
            "round_robin": self._round_robin_assign,
            "least_loaded": self._least_loaded_assign,
            "capability_based": self._capability_based_assign,
            "performance_weighted": self._performance_weighted_assign
        }
        self.current_strategy = "performance_weighted"
        self.assignment_history = []
    
    def assign_task(self, task_id: str, requirements: List[ResourceRequirement]) -> Optional[str]:
        """Assign a task to the best available bot"""
        strategy_func = self.load_balancing_strategies[self.current_strategy]
        bot_id = strategy_func(task_id, requirements)
        
        if bot_id and bot_id in self.bots:
            bot = self.bots[bot_id]
            if bot.assign_task(task_id):
                if self.resource_manager.allocate_resources(task_id, requirements):
                    self.task_assignments[task_id] = bot_id
                    self.assignment_history.append({
                        "task_id": task_id,
                        "bot_id": bot_id,
                        "assigned_at": datetime.now(),
                        "strategy": self.current_strategy
                    })
                    return bot_id
                else:
                    bot.current_tasks.discard(task_id)
        
        return None
    
    def _round_robin_assign(self, task_id: str, requirements: List[ResourceRequirement]) -> Optional[str]:
        """Round-robin assignment"""
        bot_ids = list(self.bots.keys())
        start_index = len(self.assignment_history) % len(bot_ids)
        
        for i in range(len(bot_ids)):
            bot_id = bot_ids[(start_index + i) % len(bot_ids)]
            bot = self.bots[bot_id]
            if bot.can_accept_task(task_id, requirements):
                return bot_id
        
        return None
    
    def _least_loaded_assign(self, task_id: str, requirements: List[ResourceRequirement]) -> Optional[str]:
        """Assign to least loaded bot"""
        best_bot = None
        min_load = float('inf')
        
        for bot_id, bot in self.bots.items():
            if bot.can_accept_task(task_id, requirements):
                load = bot.get_load_factor()
                if load < min_load:
                    min_load = load
                    best_bot = bot_id
        
        return best_bot
    
    def _capability_based_assign(self, task_id: str, requirements: List[ResourceRequirement]) -> Optional[str]:
        """Assign based on capability matching"""
        best_bot = None
        best_score = -1
        
        for bot_id, bot in self.bots.items():
            if bot.can_accept_task(task_id, requirements):
                score = self._calculate_capability_score(bot, requirements)
                if score > best_score:
                    best_score = score
                    best_bot = bot_id
        
        return best_bot
    
    def _performance_weighted_assign(self, task_id: str, requirements: List[ResourceRequirement]) -> Optional[str]:
        """Assign based on performance metrics and load"""
        best_bot = None
        best_score = -1
        
        for bot_id, bot in self.bots.items():
            if bot.can_accept_task(task_id, requirements):
                # Composite score based on performance, load, and capabilities
                performance_score = bot.performance_metrics["success_rate"] / 100.0
                load_score = 1.0 - bot.get_load_factor()
                capability_score = self._calculate_capability_score(bot, requirements) / 100.0
                
                composite_score = (
                    0.4 * performance_score +
                    0.3 * load_score +
                    0.3 * capability_score
                )
                
                if composite_score > best_score:
                    best_score = composite_score
                    best_bot = bot_id
        
        return best_bot
    
    def _calculate_capability_score(self, bot: WorkerBot, requirements: List[ResourceRequirement]) -> float:
        """Calculate how well a bot matches the requirements"""
        if not requirements:
            return 100.0
        
        total_score = 0
        for req in requirements:
            capability_key = f"{req.resource_type.value}_capacity"
            if capability_key in bot.capabilities:
                capacity = bot.capabilities[capability_key]
                if capacity >= req.amount:
                    # Score based on how much capacity exceeds requirement
                    excess_capacity = (capacity - req.amount) / req.amount
                    score = min(100, 80 + excess_capacity * 20)
                    total_score += score
                else:
                    total_score += 0  # Can't meet requirement
            else:
                total_score += 0  # No capability
        
        return total_score / len(requirements)
    
    def release_task(self, task_id: str):
        """Release a task from its assigned bot"""
        if task_id in self.task_assignments:
            bot_id = self.task_assignments[task_id]
            if bot_id in self.bots:
                self.bots[bot_id].current_tasks.discard(task_id)
            self.resource_manager.release_resources(task_id)
            del self.task_assignments[task_id]

class WorkStealingManager:
    def __init__(self, bots: Dict[str, WorkerBot], load_balancer: LoadBalancer):
        self.bots = bots
        self.load_balancer = load_balancer
        self.steal_threshold = 0.3  # Steal if load difference > 30%
        self.last_rebalance = datetime.now()
        self.rebalance_interval = 60  # seconds
    
    def should_rebalance(self) -> bool:
        """Check if work stealing/rebalancing is needed"""
        now = datetime.now()
        if (now - self.last_rebalance).total_seconds() < self.rebalance_interval:
            return False
        
        loads = [(bot_id, bot.get_load_factor()) for bot_id, bot in self.bots.items()]
        if not loads:
            return False
        
        max_load = max(loads, key=lambda x: x[1])[1]
        min_load = min(loads, key=lambda x: x[1])[1]
        
        return (max_load - min_load) > self.steal_threshold
    
    def rebalance_work(self) -> int:
        """Perform work stealing to balance loads"""
        if not self.should_rebalance():
            return 0
        
        self.last_rebalance = datetime.now()
        
        # Find overloaded and underloaded bots
        bot_loads = [(bot_id, bot.get_load_factor(), bot) for bot_id, bot in self.bots.items()]
        bot_loads.sort(key=lambda x: x[1])  # Sort by load
        
        underloaded = [item for item in bot_loads if item[1] < 0.5]
        overloaded = [item for item in bot_loads if item[1] > 0.8]
        
        if not underloaded or not overloaded:
            return 0
        
        tasks_moved = 0
        
        for overloaded_bot_id, overloaded_load, overloaded_bot in overloaded:
            if not underloaded:
                break
            
            # Find tasks that can be moved
            movable_tasks = list(overloaded_bot.current_tasks)
            
            for task_id in movable_tasks[:min(2, len(movable_tasks))]:  # Move at most 2 tasks
                # Find best underloaded bot for this task
                target_bot_id, target_load, target_bot = underloaded[0]
                
                if target_load < 0.7:  # Don't overload the target
                    # Move the task
                    if self._move_task(task_id, overloaded_bot_id, target_bot_id):
                        tasks_moved += 1
                        
                        # Update loads
                        new_target_load = target_bot.get_load_factor()
                        underloaded[0] = (target_bot_id, new_target_load, target_bot)
                        
                        # Re-sort underloaded bots
                        underloaded.sort(key=lambda x: x[1])
                        
                        # Remove from underloaded if it's getting too loaded
                        if new_target_load > 0.7:
                            underloaded.pop(0)
        
        logger.info(f"Work rebalancing moved {tasks_moved} tasks")
        return tasks_moved
    
    def _move_task(self, task_id: str, from_bot_id: str, to_bot_id: str) -> bool:
        """Move a task from one bot to another"""
        try:
            from_bot = self.bots[from_bot_id]
            to_bot = self.bots[to_bot_id]
            
            # Check if target bot can accept the task
            if len(to_bot.current_tasks) >= to_bot.max_concurrent:
                return False
            
            # Move the task
            from_bot.current_tasks.discard(task_id)
            to_bot.current_tasks.add(task_id)
            
            # Update assignment tracking
            self.load_balancer.task_assignments[task_id] = to_bot_id
            
            logger.debug(f"Moved task {task_id} from {from_bot_id} to {to_bot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move task {task_id}: {e}")
            return False

class ParallelExecutor:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.bots = {}
        self.resource_manager = ResourceManager()
        self.load_balancer = None
        self.work_stealing_manager = None
        
        self.execution_plans = {}
        self.active_executions = {}
        self.completed_executions = {}
        
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        
        # Performance tracking
        self.metrics = {
            "total_tasks_executed": 0,
            "total_execution_time": 0,
            "average_parallelism": 0,
            "resource_efficiency": 0
        }
    
    async def start(self):
        """Start the parallel executor"""
        self.running = True
        self.load_balancer = LoadBalancer(self.bots, self.resource_manager)
        self.work_stealing_manager = WorkStealingManager(self.bots, self.load_balancer)
        
        # Start background tasks
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._rebalancing_loop())
        
        logger.info("Parallel Executor started")
    
    async def stop(self):
        """Stop the parallel executor"""
        self.running = False
        self.thread_pool.shutdown(wait=True)
        logger.info("Parallel Executor stopped")
    
    def register_bot(self, bot_id: str, capabilities: Dict[str, Any], max_concurrent: int = 3):
        """Register a worker bot"""
        self.bots[bot_id] = WorkerBot(bot_id, capabilities, max_concurrent)
        logger.info(f"Registered bot {bot_id} with capabilities: {capabilities}")
    
    def unregister_bot(self, bot_id: str):
        """Unregister a worker bot"""
        if bot_id in self.bots:
            bot = self.bots[bot_id]
            # Reassign any current tasks
            for task_id in list(bot.current_tasks):
                self.load_balancer.release_task(task_id)
            del self.bots[bot_id]
            logger.info(f"Unregistered bot {bot_id}")
    
    async def execute_plan(self, plan: ExecutionPlan, task_executor: Callable) -> Dict[str, Any]:
        """Execute an execution plan"""
        execution_id = f"exec_{int(time.time() * 1000)}"
        
        execution_state = {
            "plan": plan,
            "status": "running",
            "started_at": datetime.now(),
            "completed_tasks": set(),
            "failed_tasks": set(),
            "active_tasks": set(),
            "results": {},
            "errors": {}
        }
        
        self.active_executions[execution_id] = execution_state
        
        try:
            if plan.strategy == ExecutionStrategy.SEQUENTIAL:
                result = await self._execute_sequential(plan, task_executor, execution_state)
            elif plan.strategy == ExecutionStrategy.PARALLEL:
                result = await self._execute_parallel(plan, task_executor, execution_state)
            elif plan.strategy == ExecutionStrategy.PIPELINE:
                result = await self._execute_pipeline(plan, task_executor, execution_state)
            elif plan.strategy == ExecutionStrategy.MAP_REDUCE:
                result = await self._execute_map_reduce(plan, task_executor, execution_state)
            else:
                raise ValueError(f"Unknown execution strategy: {plan.strategy}")
            
            execution_state["status"] = "completed"
            execution_state["completed_at"] = datetime.now()
            execution_state["result"] = result
            
            self.completed_executions[execution_id] = execution_state
            del self.active_executions[execution_id]
            
            return {
                "execution_id": execution_id,
                "status": "completed",
                "result": result,
                "stats": self._calculate_execution_stats(execution_state)
            }
            
        except Exception as e:
            execution_state["status"] = "failed"
            execution_state["error"] = str(e)
            
            logger.error(f"Execution {execution_id} failed: {e}")
            
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": str(e)
            }
    
    async def _execute_sequential(self, plan: ExecutionPlan, task_executor: Callable, 
                                execution_state: Dict) -> Dict[str, Any]:
        """Execute tasks sequentially"""
        results = {}
        
        for task_id in plan.tasks:
            if not self._check_dependencies_satisfied(task_id, plan.dependencies, 
                                                   execution_state["completed_tasks"]):
                continue
            
            execution_state["active_tasks"].add(task_id)
            
            try:
                result = await self._execute_single_task(task_id, plan, task_executor)
                results[task_id] = result
                execution_state["results"][task_id] = result
                execution_state["completed_tasks"].add(task_id)
                
            except Exception as e:
                execution_state["errors"][task_id] = str(e)
                execution_state["failed_tasks"].add(task_id)
                logger.error(f"Task {task_id} failed: {e}")
            
            execution_state["active_tasks"].discard(task_id)
        
        return results
    
    async def _execute_parallel(self, plan: ExecutionPlan, task_executor: Callable, 
                              execution_state: Dict) -> Dict[str, Any]:
        """Execute tasks in parallel with dependency resolution"""
        results = {}
        semaphore = asyncio.Semaphore(plan.max_parallel_tasks)
        
        async def execute_task_with_deps(task_id: str):
            # Wait for dependencies
            while not self._check_dependencies_satisfied(task_id, plan.dependencies, 
                                                       execution_state["completed_tasks"]):
                await asyncio.sleep(0.1)
            
            async with semaphore:
                execution_state["active_tasks"].add(task_id)
                
                try:
                    result = await self._execute_single_task(task_id, plan, task_executor)
                    results[task_id] = result
                    execution_state["results"][task_id] = result
                    execution_state["completed_tasks"].add(task_id)
                    
                except Exception as e:
                    execution_state["errors"][task_id] = str(e)
                    execution_state["failed_tasks"].add(task_id)
                    logger.error(f"Task {task_id} failed: {e}")
                
                execution_state["active_tasks"].discard(task_id)
        
        # Start all tasks
        tasks = [asyncio.create_task(execute_task_with_deps(task_id)) 
                for task_id in plan.tasks]
        
        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _execute_pipeline(self, plan: ExecutionPlan, task_executor: Callable, 
                              execution_state: Dict) -> Dict[str, Any]:
        """Execute tasks in pipeline stages"""
        # Group tasks by dependency level
        stages = self._create_pipeline_stages(plan.tasks, plan.dependencies)
        results = {}
        
        for stage_num, stage_tasks in enumerate(stages):
            logger.info(f"Executing pipeline stage {stage_num} with {len(stage_tasks)} tasks")
            
            stage_semaphore = asyncio.Semaphore(min(len(stage_tasks), plan.max_parallel_tasks))
            
            async def execute_stage_task(task_id: str):
                async with stage_semaphore:
                    execution_state["active_tasks"].add(task_id)
                    
                    try:
                        result = await self._execute_single_task(task_id, plan, task_executor)
                        results[task_id] = result
                        execution_state["results"][task_id] = result
                        execution_state["completed_tasks"].add(task_id)
                        
                    except Exception as e:
                        execution_state["errors"][task_id] = str(e)
                        execution_state["failed_tasks"].add(task_id)
                        logger.error(f"Task {task_id} failed: {e}")
                    
                    execution_state["active_tasks"].discard(task_id)
            
            # Execute all tasks in current stage
            stage_task_objects = [asyncio.create_task(execute_stage_task(task_id)) 
                                for task_id in stage_tasks]
            
            await asyncio.gather(*stage_task_objects, return_exceptions=True)
        
        return results
    
    async def _execute_map_reduce(self, plan: ExecutionPlan, task_executor: Callable, 
                                execution_state: Dict) -> Dict[str, Any]:
        """Execute tasks using map-reduce pattern"""
        # Separate map and reduce tasks
        map_tasks = [t for t in plan.tasks if t.startswith("map_")]
        reduce_tasks = [t for t in plan.tasks if t.startswith("reduce_")]
        
        # Execute map phase
        map_results = {}
        map_semaphore = asyncio.Semaphore(plan.max_parallel_tasks)
        
        async def execute_map_task(task_id: str):
            async with map_semaphore:
                execution_state["active_tasks"].add(task_id)
                
                try:
                    result = await self._execute_single_task(task_id, plan, task_executor)
                    map_results[task_id] = result
                    execution_state["results"][task_id] = result
                    execution_state["completed_tasks"].add(task_id)
                    
                except Exception as e:
                    execution_state["errors"][task_id] = str(e)
                    execution_state["failed_tasks"].add(task_id)
                
                execution_state["active_tasks"].discard(task_id)
        
        map_task_objects = [asyncio.create_task(execute_map_task(task_id)) 
                          for task_id in map_tasks]
        
        await asyncio.gather(*map_task_objects, return_exceptions=True)
        
        # Execute reduce phase
        reduce_results = {}
        
        for task_id in reduce_tasks:
            execution_state["active_tasks"].add(task_id)
            
            try:
                # Pass map results to reduce tasks
                result = await self._execute_single_task(task_id, plan, task_executor, 
                                                       context={"map_results": map_results})
                reduce_results[task_id] = result
                execution_state["results"][task_id] = result
                execution_state["completed_tasks"].add(task_id)
                
            except Exception as e:
                execution_state["errors"][task_id] = str(e)
                execution_state["failed_tasks"].add(task_id)
            
            execution_state["active_tasks"].discard(task_id)
        
        # Combine results
        all_results = {**map_results, **reduce_results}
        return all_results
    
    async def _execute_single_task(self, task_id: str, plan: ExecutionPlan, 
                                 task_executor: Callable, context: Dict = None) -> Any:
        """Execute a single task using load balancer"""
        requirements = plan.resource_requirements.get(task_id, [])
        
        # Assign bot
        bot_id = self.load_balancer.assign_task(task_id, requirements)
        if not bot_id:
            raise Exception(f"No available bot for task {task_id}")
        
        start_time = time.time()
        
        try:
            # Execute task
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                lambda: task_executor(task_id, context or {})
            )
            
            execution_time = time.time() - start_time
            self.bots[bot_id].complete_task(task_id, execution_time, True)
            self.metrics["total_tasks_executed"] += 1
            self.metrics["total_execution_time"] += execution_time
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.bots[bot_id].complete_task(task_id, execution_time, False)
            raise e
        
        finally:
            self.load_balancer.release_task(task_id)
    
    def _check_dependencies_satisfied(self, task_id: str, dependencies: Dict[str, Set[str]], 
                                    completed_tasks: Set[str]) -> bool:
        """Check if a task's dependencies are satisfied"""
        task_deps = dependencies.get(task_id, set())
        return all(dep in completed_tasks for dep in task_deps)
    
    def _create_pipeline_stages(self, tasks: List[str], 
                              dependencies: Dict[str, Set[str]]) -> List[List[str]]:
        """Create pipeline stages based on dependencies"""
        stages = []
        remaining_tasks = set(tasks)
        completed_tasks = set()
        
        while remaining_tasks:
            current_stage = []
            
            # Find tasks with no remaining dependencies
            for task_id in list(remaining_tasks):
                task_deps = dependencies.get(task_id, set())
                if all(dep in completed_tasks for dep in task_deps):
                    current_stage.append(task_id)
                    remaining_tasks.remove(task_id)
            
            if not current_stage:
                # Circular dependency detected
                logger.warning(f"Circular dependencies detected in tasks: {remaining_tasks}")
                current_stage = list(remaining_tasks)
                remaining_tasks.clear()
            
            stages.append(current_stage)
            completed_tasks.update(current_stage)
        
        return stages
    
    def _calculate_execution_stats(self, execution_state: Dict) -> Dict[str, Any]:
        """Calculate execution statistics"""
        total_tasks = len(execution_state["plan"].tasks)
        completed_tasks = len(execution_state["completed_tasks"])
        failed_tasks = len(execution_state["failed_tasks"])
        
        duration = 0
        if "completed_at" in execution_state:
            duration = (execution_state["completed_at"] - execution_state["started_at"]).total_seconds()
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "duration_seconds": duration,
            "average_task_time": duration / total_tasks if total_tasks > 0 else 0
        }
    
    async def _monitoring_loop(self):
        """Monitor bot health and performance"""
        while self.running:
            try:
                for bot_id, bot in self.bots.items():
                    # Update bot health status
                    if bot.performance_metrics["error_count"] > 10:
                        bot.is_healthy = False
                        logger.warning(f"Bot {bot_id} marked as unhealthy due to high error count")
                    elif bot.performance_metrics["success_rate"] < 50:
                        bot.is_healthy = False
                        logger.warning(f"Bot {bot_id} marked as unhealthy due to low success rate")
                    else:
                        bot.is_healthy = True
                    
                    bot.last_health_check = datetime.now()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _rebalancing_loop(self):
        """Periodic work rebalancing"""
        while self.running:
            try:
                if self.work_stealing_manager:
                    moved_tasks = self.work_stealing_manager.rebalance_work()
                    if moved_tasks > 0:
                        logger.info(f"Rebalanced {moved_tasks} tasks across bots")
                
                await asyncio.sleep(60)  # Rebalance every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rebalancing loop error: {e}")
                await asyncio.sleep(120)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        bot_status = {}
        for bot_id, bot in self.bots.items():
            bot_status[bot_id] = {
                "is_healthy": bot.is_healthy,
                "current_tasks": len(bot.current_tasks),
                "max_concurrent": bot.max_concurrent,
                "load_factor": bot.get_load_factor(),
                "performance_metrics": bot.performance_metrics,
                "total_completed": len(bot.completed_tasks),
                "total_failed": len(bot.failed_tasks)
            }
        
        return {
            "bots": bot_status,
            "resource_utilization": self.resource_manager.get_resource_utilization(),
            "active_executions": len(self.active_executions),
            "completed_executions": len(self.completed_executions),
            "system_metrics": self.metrics
        }