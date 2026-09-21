"""
Workflow Coordination System for Integration Controller

Provides comprehensive workflow orchestration capabilities including:
- Multi-service workflow execution
- Dependency management and resolution
- Parallel and sequential task execution
- Conditional workflows and branching
- Error handling and rollback mechanisms
- Workflow monitoring and progress tracking
- State persistence and recovery
"""

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"

@dataclass
class WorkflowTask:
    """Individual task within a workflow"""
    task_id: str
    name: str
    service_name: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 3
    retry_delay: int = 5
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    condition: Optional[str] = None
    on_success: Optional[List[str]] = field(default_factory=list)
    on_failure: Optional[List[str]] = field(default_factory=list)

@dataclass
class Workflow:
    """Workflow definition and execution state"""
    workflow_id: str
    name: str
    description: str
    tasks: List[WorkflowTask] = field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_parallel_tasks: int = 5
    timeout: int = 3600
    auto_rollback: bool = True
    rollback_tasks: List[str] = field(default_factory=list)

class WorkflowStorage:
    """Persistent storage for workflow definitions and execution state"""
    
    def __init__(self, db_path: str = "workflow_storage.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Workflows table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                execution_mode TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                metadata TEXT,
                max_parallel_tasks INTEGER,
                timeout INTEGER,
                auto_rollback BOOLEAN,
                rollback_tasks TEXT
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_tasks (
                task_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                name TEXT,
                service_name TEXT,
                action TEXT,
                parameters TEXT,
                dependencies TEXT,
                timeout INTEGER,
                retry_count INTEGER,
                retry_delay INTEGER,
                status TEXT,
                error_message TEXT,
                start_time TEXT,
                end_time TEXT,
                result TEXT,
                condition TEXT,
                on_success TEXT,
                on_failure TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows (workflow_id)
            )
        ''')
        
        # Execution history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT,
                task_id TEXT,
                event TEXT,
                timestamp TEXT,
                details TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows (workflow_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_workflow(self, workflow: Workflow):
        """Save workflow to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO workflows 
            (workflow_id, name, description, execution_mode, status, created_at,
             started_at, completed_at, error_message, metadata, max_parallel_tasks,
             timeout, auto_rollback, rollback_tasks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            workflow.workflow_id, workflow.name, workflow.description,
            workflow.execution_mode.value, workflow.status.value,
            workflow.created_at.isoformat() if workflow.created_at else None,
            workflow.started_at.isoformat() if workflow.started_at else None,
            workflow.completed_at.isoformat() if workflow.completed_at else None,
            workflow.error_message, json.dumps(workflow.metadata),
            workflow.max_parallel_tasks, workflow.timeout, workflow.auto_rollback,
            json.dumps(workflow.rollback_tasks)
        ))
        
        # Save tasks
        cursor.execute('DELETE FROM workflow_tasks WHERE workflow_id = ?', (workflow.workflow_id,))
        for task in workflow.tasks:
            cursor.execute('''
                INSERT INTO workflow_tasks 
                (task_id, workflow_id, name, service_name, action, parameters,
                 dependencies, timeout, retry_count, retry_delay, status,
                 error_message, start_time, end_time, result, condition,
                 on_success, on_failure)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.task_id, workflow.workflow_id, task.name, task.service_name,
                task.action, json.dumps(task.parameters), json.dumps(task.dependencies),
                task.timeout, task.retry_count, task.retry_delay, task.status.value,
                task.error_message,
                task.start_time.isoformat() if task.start_time else None,
                task.end_time.isoformat() if task.end_time else None,
                json.dumps(task.result) if task.result else None,
                task.condition, json.dumps(task.on_success), json.dumps(task.on_failure)
            ))
        
        conn.commit()
        conn.close()
    
    def load_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Load workflow from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM workflows WHERE workflow_id = ?', (workflow_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # Load workflow
        workflow = Workflow(
            workflow_id=row[0],
            name=row[1],
            description=row[2],
            execution_mode=ExecutionMode(row[3]),
            status=WorkflowStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
            started_at=datetime.fromisoformat(row[6]) if row[6] else None,
            completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
            error_message=row[8],
            metadata=json.loads(row[9]) if row[9] else {},
            max_parallel_tasks=row[10],
            timeout=row[11],
            auto_rollback=bool(row[12]),
            rollback_tasks=json.loads(row[13]) if row[13] else []
        )
        
        # Load tasks
        cursor.execute('SELECT * FROM workflow_tasks WHERE workflow_id = ?', (workflow_id,))
        task_rows = cursor.fetchall()
        
        for task_row in task_rows:
            task = WorkflowTask(
                task_id=task_row[0],
                name=task_row[2],
                service_name=task_row[3],
                action=task_row[4],
                parameters=json.loads(task_row[5]) if task_row[5] else {},
                dependencies=json.loads(task_row[6]) if task_row[6] else [],
                timeout=task_row[7],
                retry_count=task_row[8],
                retry_delay=task_row[9],
                status=TaskStatus(task_row[10]),
                error_message=task_row[11],
                start_time=datetime.fromisoformat(task_row[12]) if task_row[12] else None,
                end_time=datetime.fromisoformat(task_row[13]) if task_row[13] else None,
                result=json.loads(task_row[14]) if task_row[14] else None,
                condition=task_row[15],
                on_success=json.loads(task_row[16]) if task_row[16] else [],
                on_failure=json.loads(task_row[17]) if task_row[17] else []
            )
            workflow.tasks.append(task)
        
        conn.close()
        return workflow
    
    def log_event(self, workflow_id: str, task_id: Optional[str], event: str, details: Dict[str, Any]):
        """Log workflow execution event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO workflow_history (workflow_id, task_id, event, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (workflow_id, task_id, event, datetime.now().isoformat(), json.dumps(details)))
        
        conn.commit()
        conn.close()

class DependencyResolver:
    """Resolves task dependencies and determines execution order"""
    
    @staticmethod
    def resolve_dependencies(tasks: List[WorkflowTask]) -> List[List[str]]:
        """Resolve task dependencies and return execution levels"""
        task_map = {task.task_id: task for task in tasks}
        levels = []
        completed = set()
        remaining = set(task.task_id for task in tasks)
        
        while remaining:
            ready_tasks = []
            for task_id in remaining:
                task = task_map[task_id]
                if all(dep in completed for dep in task.dependencies):
                    ready_tasks.append(task_id)
            
            if not ready_tasks:
                # Circular dependency or missing dependency
                raise ValueError(f"Circular dependency detected or missing dependencies: {remaining}")
            
            levels.append(ready_tasks)
            completed.update(ready_tasks)
            remaining -= set(ready_tasks)
        
        return levels
    
    @staticmethod
    def validate_dependencies(tasks: List[WorkflowTask]) -> List[str]:
        """Validate task dependencies and return any issues"""
        issues = []
        task_ids = {task.task_id for task in tasks}
        
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    issues.append(f"Task {task.task_id} depends on non-existent task {dep}")
        
        return issues

class ConditionEvaluator:
    """Evaluates conditional logic for workflow tasks"""
    
    @staticmethod
    def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string against context"""
        if not condition:
            return True
        
        try:
            # Simple condition evaluation (can be extended)
            # Supports: task.status == 'completed', task.result.code == 200, etc.
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False

class WorkflowExecutor:
    """Executes workflow tasks with proper orchestration"""
    
    def __init__(self, service_orchestrator):
        self.service_orchestrator = service_orchestrator
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
    
    async def execute_task(self, task: WorkflowTask, context: Dict[str, Any]) -> bool:
        """Execute a single workflow task"""
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        
        try:
            # Check condition if specified
            if task.condition and not ConditionEvaluator.evaluate_condition(task.condition, context):
                task.status = TaskStatus.SKIPPED
                task.end_time = datetime.now()
                logger.info(f"Task {task.task_id} skipped due to condition")
                return True
            
            # Execute task with retries
            for attempt in range(task.retry_count + 1):
                try:
                    # Execute task through service orchestrator
                    result = await self.service_orchestrator.execute_action(
                        task.service_name, task.action, task.parameters
                    )
                    
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.end_time = datetime.now()
                    
                    logger.info(f"Task {task.task_id} completed successfully")
                    return True
                    
                except Exception as e:
                    if attempt < task.retry_count:
                        logger.warning(f"Task {task.task_id} failed (attempt {attempt + 1}), retrying in {task.retry_delay}s: {e}")
                        await asyncio.sleep(task.retry_delay)
                    else:
                        raise e
        
        except Exception as e:
            task.error_message = str(e)
            task.status = TaskStatus.FAILED
            task.end_time = datetime.now()
            logger.error(f"Task {task.task_id} failed: {e}")
            return False

class WorkflowCoordinator:
    """Main workflow coordination system"""
    
    def __init__(self, service_orchestrator):
        self.service_orchestrator = service_orchestrator
        self.storage = WorkflowStorage()
        self.executor = WorkflowExecutor(service_orchestrator)
        self.active_workflows: Dict[str, Workflow] = {}
        self.running = False
        self._coordination_task = None
    
    async def start(self):
        """Start the workflow coordinator"""
        self.running = True
        self._coordination_task = asyncio.create_task(self._coordination_loop())
        logger.info("Workflow coordinator started")
    
    async def stop(self):
        """Stop the workflow coordinator"""
        self.running = False
        if self._coordination_task:
            self._coordination_task.cancel()
        logger.info("Workflow coordinator stopped")
    
    def create_workflow(self, name: str, description: str = "", **kwargs) -> str:
        """Create a new workflow"""
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            **kwargs
        )
        
        self.storage.save_workflow(workflow)
        self.storage.log_event(workflow_id, None, "created", {
            "name": name,
            "description": description
        })
        
        logger.info(f"Created workflow {workflow_id}: {name}")
        return workflow_id
    
    def add_task(self, workflow_id: str, task: WorkflowTask):
        """Add a task to a workflow"""
        workflow = self.storage.load_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Cannot add task to workflow in {workflow.status.value} state")
        
        workflow.tasks.append(task)
        self.storage.save_workflow(workflow)
        
        self.storage.log_event(workflow_id, task.task_id, "task_added", {
            "task_name": task.name,
            "service": task.service_name,
            "action": task.action
        })
        
        logger.info(f"Added task {task.task_id} to workflow {workflow_id}")
    
    def validate_workflow(self, workflow_id: str) -> List[str]:
        """Validate workflow before execution"""
        workflow = self.storage.load_workflow(workflow_id)
        if not workflow:
            return [f"Workflow {workflow_id} not found"]
        
        issues = []
        
        # Check for tasks
        if not workflow.tasks:
            issues.append("Workflow has no tasks")
        
        # Validate dependencies
        dep_issues = DependencyResolver.validate_dependencies(workflow.tasks)
        issues.extend(dep_issues)
        
        # Check for duplicate task IDs
        task_ids = [task.task_id for task in workflow.tasks]
        if len(task_ids) != len(set(task_ids)):
            issues.append("Duplicate task IDs found")
        
        return issues
    
    async def execute_workflow(self, workflow_id: str) -> bool:
        """Execute a workflow"""
        workflow = self.storage.load_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Workflow is in {workflow.status.value} state")
        
        # Validate workflow
        issues = self.validate_workflow(workflow_id)
        if issues:
            raise ValueError(f"Workflow validation failed: {', '.join(issues)}")
        
        # Start execution
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        self.active_workflows[workflow_id] = workflow
        
        self.storage.save_workflow(workflow)
        self.storage.log_event(workflow_id, None, "started", {})
        
        try:
            success = await self._execute_workflow_tasks(workflow)
            
            if success:
                workflow.status = WorkflowStatus.COMPLETED
                logger.info(f"Workflow {workflow_id} completed successfully")
            else:
                workflow.status = WorkflowStatus.FAILED
                
                # Auto-rollback if enabled
                if workflow.auto_rollback:
                    await self._rollback_workflow(workflow)
                
                logger.error(f"Workflow {workflow_id} failed")
            
            workflow.completed_at = datetime.now()
            self.storage.save_workflow(workflow)
            
            return success
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = str(e)
            workflow.completed_at = datetime.now()
            self.storage.save_workflow(workflow)
            
            self.storage.log_event(workflow_id, None, "failed", {"error": str(e)})
            logger.error(f"Workflow {workflow_id} failed with exception: {e}")
            
            return False
        
        finally:
            self.active_workflows.pop(workflow_id, None)
    
    async def _execute_workflow_tasks(self, workflow: Workflow) -> bool:
        """Execute all tasks in a workflow according to execution mode"""
        if workflow.execution_mode == ExecutionMode.SEQUENTIAL:
            return await self._execute_sequential(workflow)
        elif workflow.execution_mode == ExecutionMode.PARALLEL:
            return await self._execute_parallel(workflow)
        elif workflow.execution_mode == ExecutionMode.CONDITIONAL:
            return await self._execute_conditional(workflow)
        else:
            raise ValueError(f"Unknown execution mode: {workflow.execution_mode}")
    
    async def _execute_sequential(self, workflow: Workflow) -> bool:
        """Execute tasks sequentially based on dependencies"""
        levels = DependencyResolver.resolve_dependencies(workflow.tasks)
        context = self._build_context(workflow)
        
        for level in levels:
            # Execute tasks in current level (can be parallel within level)
            tasks_to_run = [task for task in workflow.tasks if task.task_id in level]
            
            if len(tasks_to_run) == 1:
                # Single task - execute directly
                success = await self.executor.execute_task(tasks_to_run[0], context)
                if not success and not self._should_continue_on_failure(workflow, tasks_to_run[0]):
                    return False
            else:
                # Multiple tasks in level - execute in parallel
                tasks = [self.executor.execute_task(task, context) for task in tasks_to_run]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception) or not result:
                        if not self._should_continue_on_failure(workflow, tasks_to_run[i]):
                            return False
            
            # Update context with completed tasks
            context = self._build_context(workflow)
        
        return True
    
    async def _execute_parallel(self, workflow: Workflow) -> bool:
        """Execute all tasks in parallel (respecting dependencies)"""
        context = self._build_context(workflow)
        semaphore = asyncio.Semaphore(workflow.max_parallel_tasks)
        
        async def execute_with_semaphore(task):
            async with semaphore:
                return await self.executor.execute_task(task, context)
        
        # Group tasks by dependency levels
        levels = DependencyResolver.resolve_dependencies(workflow.tasks)
        
        for level in levels:
            tasks_to_run = [task for task in workflow.tasks if task.task_id in level]
            
            # Execute all tasks in current level in parallel
            tasks = [execute_with_semaphore(task) for task in tasks_to_run]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            for i, result in enumerate(results):
                if isinstance(result, Exception) or not result:
                    if not self._should_continue_on_failure(workflow, tasks_to_run[i]):
                        return False
            
            # Update context for next level
            context = self._build_context(workflow)
        
        return True
    
    async def _execute_conditional(self, workflow: Workflow) -> bool:
        """Execute tasks based on conditional logic"""
        context = self._build_context(workflow)
        executed_tasks = set()
        
        while len(executed_tasks) < len(workflow.tasks):
            ready_tasks = []
            
            for task in workflow.tasks:
                if (task.task_id not in executed_tasks and
                    all(dep in executed_tasks for dep in task.dependencies)):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # No more tasks can be executed
                break
            
            # Execute ready tasks
            for task in ready_tasks:
                success = await self.executor.execute_task(task, context)
                executed_tasks.add(task.task_id)
                
                if success:
                    # Execute on_success tasks
                    for next_task_id in task.on_success:
                        if next_task_id not in executed_tasks:
                            next_task = next((t for t in workflow.tasks if t.task_id == next_task_id), None)
                            if next_task:
                                success = await self.executor.execute_task(next_task, context)
                                executed_tasks.add(next_task_id)
                else:
                    # Execute on_failure tasks
                    for next_task_id in task.on_failure:
                        if next_task_id not in executed_tasks:
                            next_task = next((t for t in workflow.tasks if t.task_id == next_task_id), None)
                            if next_task:
                                await self.executor.execute_task(next_task, context)
                                executed_tasks.add(next_task_id)
                    
                    if not self._should_continue_on_failure(workflow, task):
                        return False
                
                # Update context
                context = self._build_context(workflow)
        
        return True
    
    def _build_context(self, workflow: Workflow) -> Dict[str, Any]:
        """Build execution context from completed tasks"""
        context = {
            "workflow": {
                "id": workflow.workflow_id,
                "name": workflow.name,
                "metadata": workflow.metadata
            },
            "tasks": {}
        }
        
        for task in workflow.tasks:
            context["tasks"][task.task_id] = {
                "status": task.status.value,
                "result": task.result,
                "error": task.error_message
            }
        
        return context
    
    def _should_continue_on_failure(self, workflow: Workflow, task: WorkflowTask) -> bool:
        """Determine if workflow should continue after task failure"""
        # Check if task has failure handlers
        if task.on_failure:
            return True
        
        # Check workflow-level failure policy
        return workflow.metadata.get("continue_on_failure", False)
    
    async def _rollback_workflow(self, workflow: Workflow):
        """Rollback workflow by executing rollback tasks"""
        if not workflow.rollback_tasks:
            return
        
        logger.info(f"Rolling back workflow {workflow.workflow_id}")
        
        for task_id in reversed(workflow.rollback_tasks):
            task = next((t for t in workflow.tasks if t.task_id == task_id), None)
            if task and task.status == TaskStatus.COMPLETED:
                try:
                    # Execute rollback action
                    rollback_action = f"rollback_{task.action}"
                    await self.service_orchestrator.execute_action(
                        task.service_name, rollback_action, task.parameters
                    )
                    logger.info(f"Rolled back task {task_id}")
                except Exception as e:
                    logger.error(f"Failed to rollback task {task_id}: {e}")
    
    async def cancel_workflow(self, workflow_id: str):
        """Cancel a running workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.CANCELLED
            self.storage.save_workflow(workflow)
            self.storage.log_event(workflow_id, None, "cancelled", {})
            logger.info(f"Cancelled workflow {workflow_id}")
    
    async def pause_workflow(self, workflow_id: str):
        """Pause a running workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.PAUSED
            self.storage.save_workflow(workflow)
            self.storage.log_event(workflow_id, None, "paused", {})
            logger.info(f"Paused workflow {workflow_id}")
    
    async def resume_workflow(self, workflow_id: str):
        """Resume a paused workflow"""
        workflow = self.storage.load_workflow(workflow_id)
        if workflow and workflow.status == WorkflowStatus.PAUSED:
            workflow.status = WorkflowStatus.RUNNING
            self.active_workflows[workflow_id] = workflow
            self.storage.save_workflow(workflow)
            self.storage.log_event(workflow_id, None, "resumed", {})
            logger.info(f"Resumed workflow {workflow_id}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status and progress"""
        workflow = self.storage.load_workflow(workflow_id)
        if not workflow:
            return None
        
        completed_tasks = sum(1 for task in workflow.tasks if task.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for task in workflow.tasks if task.status == TaskStatus.FAILED)
        running_tasks = sum(1 for task in workflow.tasks if task.status == TaskStatus.RUNNING)
        
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "progress": {
                "total_tasks": len(workflow.tasks),
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "running_tasks": running_tasks,
                "percentage": (completed_tasks / len(workflow.tasks)) * 100 if workflow.tasks else 0
            },
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "error_message": workflow.error_message,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "name": task.name,
                    "status": task.status.value,
                    "start_time": task.start_time.isoformat() if task.start_time else None,
                    "end_time": task.end_time.isoformat() if task.end_time else None,
                    "error_message": task.error_message
                }
                for task in workflow.tasks
            ]
        }
    
    async def _coordination_loop(self):
        """Main coordination loop for managing active workflows"""
        while self.running:
            try:
                # Check for timed-out workflows
                current_time = datetime.now()
                for workflow_id, workflow in list(self.active_workflows.items()):
                    if (workflow.started_at and 
                        (current_time - workflow.started_at).total_seconds() > workflow.timeout):
                        
                        workflow.status = WorkflowStatus.FAILED
                        workflow.error_message = "Workflow timed out"
                        workflow.completed_at = current_time
                        
                        self.storage.save_workflow(workflow)
                        self.storage.log_event(workflow_id, None, "timeout", {})
                        
                        self.active_workflows.pop(workflow_id)
                        logger.warning(f"Workflow {workflow_id} timed out")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(5)

# Factory function
def create_workflow_coordinator(service_orchestrator) -> WorkflowCoordinator:
    """Create and return a workflow coordinator instance"""
    return WorkflowCoordinator(service_orchestrator)

# Helper functions for common workflow patterns
def create_deployment_workflow(service_name: str, version: str) -> Tuple[str, List[WorkflowTask]]:
    """Create a standard deployment workflow"""
    workflow_id = str(uuid.uuid4())
    
    tasks = [
        WorkflowTask(
            task_id=f"health_check_{service_name}",
            name=f"Pre-deployment health check for {service_name}",
            service_name=service_name,
            action="health_check",
            parameters={}
        ),
        WorkflowTask(
            task_id=f"backup_{service_name}",
            name=f"Backup current version of {service_name}",
            service_name=service_name,
            action="backup",
            parameters={"version": version},
            dependencies=[f"health_check_{service_name}"]
        ),
        WorkflowTask(
            task_id=f"deploy_{service_name}",
            name=f"Deploy {service_name} version {version}",
            service_name=service_name,
            action="deploy",
            parameters={"version": version},
            dependencies=[f"backup_{service_name}"]
        ),
        WorkflowTask(
            task_id=f"verify_{service_name}",
            name=f"Verify deployment of {service_name}",
            service_name=service_name,
            action="verify",
            parameters={"version": version},
            dependencies=[f"deploy_{service_name}"]
        )
    ]
    
    return workflow_id, tasks