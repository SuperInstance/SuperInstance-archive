"""
Workflow Engine - Core execution engine for IFTTT-style workflows

Handles:
- Workflow execution orchestration
- Trigger and action processing
- Context management and variable passing
- Error handling and retries
- Conditional logic and branching
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from core.database import db_manager, ExecutionStatus, ActionType, TriggerType
from .triggers import TriggerRegistry
from .actions import ActionRegistry
from .context import ExecutionContext
from .conditions import ConditionEvaluator

logger = logging.getLogger(__name__)

class ExecutionMode(Enum):
    SYNC = "sync"
    ASYNC = "async"
    PARALLEL = "parallel"

@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    id: str
    name: str
    type: str  # action type
    config: Dict[str, Any]
    condition: Optional[Dict[str, Any]] = None
    retry_config: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    depends_on: List[str] = field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.SYNC

@dataclass
class ExecutionResult:
    """Result of a step execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class WorkflowExecution:
    """Manages the execution of a single workflow instance"""
    
    def __init__(self, workflow_id: str, execution_id: str, workflow_config: Dict[str, Any],
                 trigger_data: Dict[str, Any] = None):
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.workflow_config = workflow_config
        self.trigger_data = trigger_data or {}
        
        self.context = ExecutionContext(execution_id)
        self.status = ExecutionStatus.PENDING
        self.steps: List[WorkflowStep] = []
        self.step_results: Dict[str, ExecutionResult] = {}
        
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        
        # Parse workflow configuration
        self._parse_workflow_config()
    
    def _parse_workflow_config(self):
        """Parse workflow configuration into steps"""
        actions = self.workflow_config.get("actions", [])
        
        for i, action_config in enumerate(actions):
            step = WorkflowStep(
                id=action_config.get("id", f"step_{i}"),
                name=action_config.get("name", f"Step {i+1}"),
                type=action_config.get("type", "unknown"),
                config=action_config.get("config", {}),
                condition=action_config.get("condition"),
                retry_config=action_config.get("retry", {}),
                timeout_seconds=action_config.get("timeout_seconds"),
                depends_on=action_config.get("depends_on", []),
                execution_mode=ExecutionMode(action_config.get("execution_mode", "sync"))
            )
            self.steps.append(step)
    
    async def execute(self, workflow_engine: 'WorkflowEngine') -> ExecutionResult:
        """Execute the workflow"""
        self.started_at = datetime.utcnow()
        self.status = ExecutionStatus.RUNNING
        
        # Set initial context variables
        self.context.set_variable("trigger_data", self.trigger_data)
        self.context.set_variable("workflow_id", self.workflow_id)
        self.context.set_variable("execution_id", self.execution_id)
        
        try:
            # Execute steps in order, respecting dependencies
            await self._execute_steps(workflow_engine)
            
            self.status = ExecutionStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            
            return ExecutionResult(
                success=True,
                data=self.context.get_all_variables(),
                duration_ms=int((self.completed_at - self.started_at).total_seconds() * 1000)
            )
            
        except Exception as e:
            self.status = ExecutionStatus.FAILED
            self.completed_at = datetime.utcnow()
            self.error_message = str(e)
            
            logger.error(f"Workflow execution {self.execution_id} failed: {e}")
            
            return ExecutionResult(
                success=False,
                error=str(e),
                duration_ms=int((self.completed_at - self.started_at).total_seconds() * 1000) if self.completed_at else 0
            )
    
    async def _execute_steps(self, workflow_engine: 'WorkflowEngine'):
        """Execute workflow steps with dependency management"""
        completed_steps = set()
        pending_steps = {step.id: step for step in self.steps}
        
        while pending_steps:
            # Find steps that can be executed (dependencies satisfied)
            ready_steps = []
            for step_id, step in pending_steps.items():
                if all(dep in completed_steps for dep in step.depends_on):
                    ready_steps.append(step)
            
            if not ready_steps:
                # Circular dependency or missing step
                remaining = list(pending_steps.keys())
                raise Exception(f"Cannot resolve step dependencies: {remaining}")
            
            # Group steps by execution mode
            sync_steps = [s for s in ready_steps if s.execution_mode == ExecutionMode.SYNC]
            async_steps = [s for s in ready_steps if s.execution_mode == ExecutionMode.ASYNC]
            parallel_steps = [s for s in ready_steps if s.execution_mode == ExecutionMode.PARALLEL]
            
            # Execute sync steps sequentially
            for step in sync_steps:
                await self._execute_step(step, workflow_engine)
                completed_steps.add(step.id)
                pending_steps.pop(step.id)
            
            # Execute async steps (fire and forget)
            for step in async_steps:
                asyncio.create_task(self._execute_step(step, workflow_engine))
                completed_steps.add(step.id)  # Mark as completed immediately
                pending_steps.pop(step.id)
            
            # Execute parallel steps concurrently
            if parallel_steps:
                tasks = [self._execute_step(step, workflow_engine) for step in parallel_steps]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                for step in parallel_steps:
                    completed_steps.add(step.id)
                    pending_steps.pop(step.id)
    
    async def _execute_step(self, step: WorkflowStep, workflow_engine: 'WorkflowEngine') -> ExecutionResult:
        """Execute a single workflow step"""
        step_start = time.time()
        
        try:
            # Check condition if present
            if step.condition and not await self._evaluate_condition(step.condition):
                result = ExecutionResult(
                    success=True,
                    data=None,
                    metadata={"skipped": True, "reason": "condition_not_met"}
                )
                self.step_results[step.id] = result
                return result
            
            # Execute action with retries
            result = await self._execute_action_with_retries(step, workflow_engine)
            
            # Store result in context
            self.context.set_variable(f"step_{step.id}_result", result.data)
            self.step_results[step.id] = result
            
            # Update database
            await self._save_step_result(step, result, int((time.time() - step_start) * 1000))
            
            return result
            
        except Exception as e:
            error_result = ExecutionResult(
                success=False,
                error=str(e),
                duration_ms=int((time.time() - step_start) * 1000)
            )
            self.step_results[step.id] = error_result
            
            # Update database
            await self._save_step_result(step, error_result, int((time.time() - step_start) * 1000))
            
            # Re-raise exception to stop workflow if step is critical
            if not step.config.get("continue_on_error", False):
                raise
            
            return error_result
    
    async def _execute_action_with_retries(self, step: WorkflowStep, workflow_engine: 'WorkflowEngine') -> ExecutionResult:
        """Execute action with retry logic"""
        retry_config = step.retry_config or {}
        max_retries = retry_config.get("max_retries", 0)
        retry_delay = retry_config.get("delay_seconds", 1)
        backoff_factor = retry_config.get("backoff_factor", 2)
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Set timeout if specified
                if step.timeout_seconds:
                    result = await asyncio.wait_for(
                        workflow_engine.execute_action(step, self.context),
                        timeout=step.timeout_seconds
                    )
                else:
                    result = await workflow_engine.execute_action(step, self.context)
                
                return result
                
            except Exception as e:
                last_error = e
                
                if attempt < max_retries:
                    delay = retry_delay * (backoff_factor ** attempt)
                    logger.warning(f"Step {step.id} failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Step {step.id} failed after {max_retries + 1} attempts: {e}")
        
        raise last_error
    
    async def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """Evaluate step condition"""
        evaluator = ConditionEvaluator(self.context)
        return await evaluator.evaluate(condition)
    
    async def _save_step_result(self, step: WorkflowStep, result: ExecutionResult, duration_ms: int):
        """Save step execution result to database"""
        try:
            from core.database import db_manager
            
            query = """
            INSERT INTO execution_steps (id, execution_id, step_name, step_type, step_config,
                                       sequence_number, status, started_at, completed_at,
                                       duration_ms, input_data, output_data, error_message)
            VALUES (:id, :execution_id, :step_name, :step_type, :step_config,
                    :sequence_number, :status, :started_at, :completed_at,
                    :duration_ms, :input_data, :output_data, :error_message)
            """
            
            values = {
                "id": str(uuid.uuid4()),
                "execution_id": self.execution_id,
                "step_name": step.name,
                "step_type": step.type,
                "step_config": json.dumps(step.config),
                "sequence_number": next(i for i, s in enumerate(self.steps) if s.id == step.id),
                "status": ExecutionStatus.COMPLETED.value if result.success else ExecutionStatus.FAILED.value,
                "started_at": datetime.utcnow() - timedelta(milliseconds=duration_ms),
                "completed_at": datetime.utcnow(),
                "duration_ms": duration_ms,
                "input_data": json.dumps(step.config),
                "output_data": json.dumps(result.data),
                "error_message": result.error
            }
            
            await db_manager.database.execute(query, values)
            
        except Exception as e:
            logger.error(f"Failed to save step result: {e}")

class WorkflowEngine:
    """Main workflow execution engine"""
    
    def __init__(self):
        self.trigger_registry = TriggerRegistry()
        self.action_registry = ActionRegistry()
        self.condition_evaluator = ConditionEvaluator()
        
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_duration_ms": 0
        }
    
    async def initialize(self):
        """Initialize workflow engine"""
        
        # Initialize registries
        await self.trigger_registry.initialize()
        await self.action_registry.initialize()
        
        logger.info("Workflow engine initialized")
    
    async def execute_workflow(self, workflow_id: str, trigger_data: Dict[str, Any] = None) -> str:
        """Execute a workflow"""
        
        # Get workflow configuration
        workflow = await db_manager.get_workflow(workflow_id)
        if not workflow:
            raise Exception(f"Workflow {workflow_id} not found")
        
        # Create execution record
        execution_id = await db_manager.create_execution({
            "workflow_id": workflow_id,
            "trigger_data": trigger_data,
            "context": {}
        })
        
        # Create workflow execution instance
        workflow_execution = WorkflowExecution(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_config={
                "actions": json.loads(workflow["actions"]) if isinstance(workflow["actions"], str) else workflow["actions"],
                "timeout_seconds": workflow["timeout_seconds"],
                "max_retries": workflow["max_retries"]
            },
            trigger_data=trigger_data
        )
        
        # Store active execution
        self.active_executions[execution_id] = workflow_execution
        
        # Execute workflow asynchronously
        asyncio.create_task(self._run_workflow_execution(workflow_execution))
        
        return execution_id
    
    async def _run_workflow_execution(self, workflow_execution: WorkflowExecution):
        """Run workflow execution and handle cleanup"""
        try:
            # Execute workflow
            result = await workflow_execution.execute(self)
            
            # Update execution record
            await db_manager.update_execution(workflow_execution.execution_id, {
                "status": ExecutionStatus.COMPLETED.value if result.success else ExecutionStatus.FAILED.value,
                "started_at": workflow_execution.started_at,
                "completed_at": workflow_execution.completed_at,
                "duration_ms": result.duration_ms,
                "result": result.data,
                "error_message": result.error
            })
            
            # Update statistics
            self.execution_stats["total_executions"] += 1
            if result.success:
                self.execution_stats["successful_executions"] += 1
            else:
                self.execution_stats["failed_executions"] += 1
            
            # Update average duration
            if result.duration_ms > 0:
                current_avg = self.execution_stats["average_duration_ms"]
                total = self.execution_stats["total_executions"]
                self.execution_stats["average_duration_ms"] = (current_avg * (total - 1) + result.duration_ms) / total
            
        except Exception as e:
            logger.error(f"Workflow execution {workflow_execution.execution_id} failed: {e}")
            
            # Update execution record with error
            await db_manager.update_execution(workflow_execution.execution_id, {
                "status": ExecutionStatus.FAILED.value,
                "completed_at": datetime.utcnow(),
                "error_message": str(e)
            })
        
        finally:
            # Clean up active execution
            self.active_executions.pop(workflow_execution.execution_id, None)
    
    async def execute_action(self, step: WorkflowStep, context: ExecutionContext) -> ExecutionResult:
        """Execute a single action"""
        
        # Get action executor
        action_executor = self.action_registry.get_action(step.type)
        if not action_executor:
            raise Exception(f"Unknown action type: {step.type}")
        
        # Execute action
        return await action_executor.execute(step.config, context)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running workflow execution"""
        
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
            execution.status = ExecutionStatus.CANCELLED
            
            # Update database
            await db_manager.update_execution(execution_id, {
                "status": ExecutionStatus.CANCELLED.value,
                "completed_at": datetime.utcnow()
            })
            
            # Remove from active executions
            self.active_executions.pop(execution_id, None)
            
            return True
        
        return False
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status and progress"""
        
        # Check if execution is active
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
            
            return {
                "execution_id": execution_id,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "steps_completed": len([s for s in execution.step_results.values() if s.success]),
                "total_steps": len(execution.steps),
                "current_step": self._get_current_step(execution),
                "progress_percentage": self._calculate_progress(execution)
            }
        
        # Get from database
        execution_data = await db_manager.get_execution(execution_id)
        if execution_data:
            return {
                "execution_id": execution_id,
                "status": execution_data["status"],
                "started_at": execution_data["started_at"].isoformat() if execution_data["started_at"] else None,
                "completed_at": execution_data["completed_at"].isoformat() if execution_data["completed_at"] else None,
                "duration_ms": execution_data["duration_ms"],
                "result": json.loads(execution_data["result"]) if execution_data["result"] else None,
                "error_message": execution_data["error_message"]
            }
        
        return {"execution_id": execution_id, "status": "not_found"}
    
    def _get_current_step(self, execution: WorkflowExecution) -> Optional[str]:
        """Get currently executing step"""
        for step in execution.steps:
            if step.id not in execution.step_results:
                return step.name
        return None
    
    def _calculate_progress(self, execution: WorkflowExecution) -> int:
        """Calculate execution progress percentage"""
        if not execution.steps:
            return 0
        
        completed = len(execution.step_results)
        total = len(execution.steps)
        return int((completed / total) * 100)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get workflow engine metrics"""
        return {
            "workflow_engine": {
                "active_executions": len(self.active_executions),
                "total_executions": self.execution_stats["total_executions"],
                "successful_executions": self.execution_stats["successful_executions"],
                "failed_executions": self.execution_stats["failed_executions"],
                "success_rate": (
                    self.execution_stats["successful_executions"] / max(1, self.execution_stats["total_executions"])
                ) * 100,
                "average_duration_ms": self.execution_stats["average_duration_ms"],
                "registered_actions": len(self.action_registry.actions),
                "registered_triggers": len(self.trigger_registry.triggers)
            }
        }
    
    async def cleanup(self):
        """Clean up workflow engine"""
        
        # Cancel all active executions
        for execution_id in list(self.active_executions.keys()):
            await self.cancel_execution(execution_id)
        
        # Clean up registries
        await self.action_registry.cleanup()
        await self.trigger_registry.cleanup()
        
        logger.info("Workflow engine cleaned up")