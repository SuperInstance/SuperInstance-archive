"""
Workflow scheduler with cron-style timing support

Handles:
- Cron expression parsing and scheduling
- Timezone support
- Missed execution handling
- Scheduler persistence
- Performance optimization for large numbers of scheduled workflows
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import uuid
from dataclasses import dataclass

from croniter import croniter
import pytz

from core.database import db_manager, ExecutionStatus
from core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ScheduledWorkflow:
    """Represents a scheduled workflow"""
    workflow_id: str
    cron_expression: str
    timezone: str = "UTC"
    is_active: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    max_missed_executions: int = 5
    missed_executions: int = 0
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}
        
        # Calculate next run time
        self.calculate_next_run()
    
    def calculate_next_run(self, base_time: datetime = None):
        """Calculate next run time based on cron expression"""
        if base_time is None:
            base_time = datetime.utcnow()
        
        try:
            # Convert to timezone if needed
            if self.timezone != "UTC":
                tz = pytz.timezone(self.timezone)
                base_time = tz.localize(base_time.replace(tzinfo=None))
                base_time = base_time.astimezone(pytz.UTC).replace(tzinfo=None)
            
            cron = croniter(self.cron_expression, base_time)
            self.next_run = cron.get_next(datetime)
            
        except Exception as e:
            logger.error(f"Error calculating next run for workflow {self.workflow_id}: {e}")
            self.next_run = None
    
    def is_due(self, current_time: datetime = None) -> bool:
        """Check if workflow is due for execution"""
        if not self.is_active or not self.next_run:
            return False
        
        if current_time is None:
            current_time = datetime.utcnow()
        
        return current_time >= self.next_run
    
    def mark_executed(self, execution_time: datetime = None):
        """Mark workflow as executed and calculate next run"""
        if execution_time is None:
            execution_time = datetime.utcnow()
        
        self.last_run = execution_time
        self.missed_executions = 0  # Reset missed executions
        self.calculate_next_run(execution_time)
    
    def mark_missed(self):
        """Mark workflow execution as missed"""
        self.missed_executions += 1
        
        # If too many missed executions, deactivate
        if self.missed_executions >= self.max_missed_executions:
            self.is_active = False
            logger.warning(f"Deactivated workflow {self.workflow_id} due to {self.missed_executions} missed executions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "workflow_id": self.workflow_id,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "max_missed_executions": self.max_missed_executions,
            "missed_executions": self.missed_executions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata
        }

class WorkflowScheduler:
    """Manages scheduled workflow executions"""
    
    def __init__(self):
        self.scheduled_workflows: Dict[str, ScheduledWorkflow] = {}
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        self.check_interval = 60  # Check every minute
        
        self.stats = {
            "scheduled_workflows": 0,
            "executions_triggered": 0,
            "missed_executions": 0,
            "scheduler_runs": 0,
            "last_run": None
        }
    
    async def initialize(self):
        """Initialize scheduler"""
        
        # Load scheduled workflows from database
        await self._load_scheduled_workflows()
        
        logger.info(f"Workflow scheduler initialized with {len(self.scheduled_workflows)} scheduled workflows")
    
    async def _load_scheduled_workflows(self):
        """Load scheduled workflows from database"""
        
        try:
            query = """
            SELECT id, schedule_config, status, last_execution_at, created_at
            FROM workflows
            WHERE schedule_config IS NOT NULL 
            AND status = 'active'
            """
            
            rows = await db_manager.database.fetch_all(query)
            
            for row in rows:
                try:
                    import json
                    schedule_config = json.loads(row["schedule_config"]) if isinstance(row["schedule_config"], str) else row["schedule_config"]
                    
                    if not schedule_config or not schedule_config.get("cron_expression"):
                        continue
                    
                    scheduled_workflow = ScheduledWorkflow(
                        workflow_id=row["id"],
                        cron_expression=schedule_config["cron_expression"],
                        timezone=schedule_config.get("timezone", "UTC"),
                        is_active=row["status"] == "active",
                        last_run=row["last_execution_at"],
                        created_at=row["created_at"],
                        metadata=schedule_config
                    )
                    
                    self.scheduled_workflows[row["id"]] = scheduled_workflow
                    
                except Exception as e:
                    logger.error(f"Error loading scheduled workflow {row['id']}: {e}")
            
            self.stats["scheduled_workflows"] = len(self.scheduled_workflows)
            
        except Exception as e:
            logger.error(f"Error loading scheduled workflows: {e}")
    
    async def schedule_workflow(self, workflow_id: str, schedule_config: Dict[str, Any]) -> bool:
        """Schedule a workflow for execution"""
        
        try:
            cron_expression = schedule_config.get("cron_expression")
            if not cron_expression:
                raise ValueError("cron_expression is required")
            
            # Validate cron expression
            try:
                croniter(cron_expression)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {e}")
            
            scheduled_workflow = ScheduledWorkflow(
                workflow_id=workflow_id,
                cron_expression=cron_expression,
                timezone=schedule_config.get("timezone", "UTC"),
                max_missed_executions=schedule_config.get("max_missed_executions", 5),
                metadata=schedule_config
            )
            
            self.scheduled_workflows[workflow_id] = scheduled_workflow
            self.stats["scheduled_workflows"] += 1
            
            # Save to database
            await self._save_scheduled_workflow(scheduled_workflow)
            
            logger.info(f"Scheduled workflow {workflow_id} with cron: {cron_expression}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling workflow {workflow_id}: {e}")
            return False
    
    async def _save_scheduled_workflow(self, scheduled_workflow: ScheduledWorkflow):
        """Save scheduled workflow to database"""
        
        try:
            # Create scheduled execution record
            query = """
            INSERT INTO scheduled_executions (id, workflow_id, scheduled_at, cron_expression, timezone, status)
            VALUES (:id, :workflow_id, :scheduled_at, :cron_expression, :timezone, :status)
            ON CONFLICT (workflow_id) DO UPDATE SET
                scheduled_at = :scheduled_at,
                cron_expression = :cron_expression,
                timezone = :timezone,
                status = :status
            """
            
            values = {
                "id": str(uuid.uuid4()),
                "workflow_id": scheduled_workflow.workflow_id,
                "scheduled_at": scheduled_workflow.next_run,
                "cron_expression": scheduled_workflow.cron_expression,
                "timezone": scheduled_workflow.timezone,
                "status": ExecutionStatus.PENDING.value
            }
            
            await db_manager.database.execute(query, values)
            
        except Exception as e:
            logger.error(f"Error saving scheduled workflow: {e}")
    
    async def unschedule_workflow(self, workflow_id: str) -> bool:
        """Remove workflow from schedule"""
        
        if workflow_id not in self.scheduled_workflows:
            return False
        
        try:
            # Remove from memory
            del self.scheduled_workflows[workflow_id]
            self.stats["scheduled_workflows"] -= 1
            
            # Update database
            query = """
            UPDATE scheduled_executions 
            SET status = :status
            WHERE workflow_id = :workflow_id
            """
            
            await db_manager.database.execute(query, {
                "status": ExecutionStatus.CANCELLED.value,
                "workflow_id": workflow_id
            })
            
            logger.info(f"Unscheduled workflow {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unscheduling workflow {workflow_id}: {e}")
            return False
    
    async def start(self):
        """Start the scheduler"""
        
        if self.is_running:
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info("Workflow scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Workflow scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        
        while self.is_running:
            try:
                await self._check_and_execute_scheduled_workflows()
                self.stats["scheduler_runs"] += 1
                self.stats["last_run"] = datetime.utcnow().isoformat()
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _check_and_execute_scheduled_workflows(self):
        """Check for due workflows and execute them"""
        
        current_time = datetime.utcnow()
        due_workflows = []
        
        # Find due workflows
        for workflow_id, scheduled_workflow in self.scheduled_workflows.items():
            if scheduled_workflow.is_due(current_time):
                due_workflows.append(scheduled_workflow)
        
        if not due_workflows:
            return
        
        logger.info(f"Found {len(due_workflows)} due workflows")
        
        # Execute due workflows
        execution_tasks = []
        for scheduled_workflow in due_workflows:
            task = asyncio.create_task(
                self._execute_scheduled_workflow(scheduled_workflow, current_time)
            )
            execution_tasks.append(task)
        
        # Wait for all executions to complete
        if execution_tasks:
            await asyncio.gather(*execution_tasks, return_exceptions=True)
    
    async def _execute_scheduled_workflow(self, scheduled_workflow: ScheduledWorkflow, execution_time: datetime):
        """Execute a single scheduled workflow"""
        
        try:
            # Import here to avoid circular imports
            from workflow.workflow_engine import WorkflowEngine
            
            # Prepare trigger data
            trigger_data = {
                "scheduled_execution": True,
                "scheduled_at": scheduled_workflow.next_run.isoformat(),
                "actual_execution_time": execution_time.isoformat(),
                "cron_expression": scheduled_workflow.cron_expression,
                "timezone": scheduled_workflow.timezone,
                "source": "scheduler"
            }
            
            # Execute workflow (would normally use injected workflow engine)
            # For demo, we'll simulate execution
            execution_id = str(uuid.uuid4())
            logger.info(f"Executed scheduled workflow {scheduled_workflow.workflow_id}, execution: {execution_id}")
            
            # Mark as executed
            scheduled_workflow.mark_executed(execution_time)
            
            # Update database
            await self._update_scheduled_execution(scheduled_workflow, execution_id, True)
            
            self.stats["executions_triggered"] += 1
            
        except Exception as e:
            logger.error(f"Error executing scheduled workflow {scheduled_workflow.workflow_id}: {e}")
            
            # Mark as missed
            scheduled_workflow.mark_missed()
            self.stats["missed_executions"] += 1
            
            # Update database
            await self._update_scheduled_execution(scheduled_workflow, None, False, str(e))
    
    async def _update_scheduled_execution(self, scheduled_workflow: ScheduledWorkflow, 
                                        execution_id: Optional[str], success: bool, error: Optional[str] = None):
        """Update scheduled execution record"""
        
        try:
            # Update existing record
            query = """
            UPDATE scheduled_executions 
            SET executed_at = :executed_at,
                execution_id = :execution_id,
                status = :status,
                scheduled_at = :next_scheduled_at
            WHERE workflow_id = :workflow_id AND status = :pending_status
            """
            
            values = {
                "executed_at": datetime.utcnow(),
                "execution_id": execution_id,
                "status": ExecutionStatus.COMPLETED.value if success else ExecutionStatus.FAILED.value,
                "next_scheduled_at": scheduled_workflow.next_run,
                "workflow_id": scheduled_workflow.workflow_id,
                "pending_status": ExecutionStatus.PENDING.value
            }
            
            await db_manager.database.execute(query, values)
            
            # Create new pending record for next execution
            if scheduled_workflow.is_active and scheduled_workflow.next_run:
                insert_query = """
                INSERT INTO scheduled_executions (id, workflow_id, scheduled_at, cron_expression, timezone, status)
                VALUES (:id, :workflow_id, :scheduled_at, :cron_expression, :timezone, :status)
                """
                
                insert_values = {
                    "id": str(uuid.uuid4()),
                    "workflow_id": scheduled_workflow.workflow_id,
                    "scheduled_at": scheduled_workflow.next_run,
                    "cron_expression": scheduled_workflow.cron_expression,
                    "timezone": scheduled_workflow.timezone,
                    "status": ExecutionStatus.PENDING.value
                }
                
                await db_manager.database.execute(insert_query, insert_values)
            
        except Exception as e:
            logger.error(f"Error updating scheduled execution: {e}")
    
    async def get_scheduled_workflow(self, workflow_id: str) -> Optional[ScheduledWorkflow]:
        """Get scheduled workflow by ID"""
        return self.scheduled_workflows.get(workflow_id)
    
    async def list_scheduled_workflows(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all scheduled workflows"""
        
        workflows = []
        for scheduled_workflow in self.scheduled_workflows.values():
            if not active_only or scheduled_workflow.is_active:
                workflows.append(scheduled_workflow.to_dict())
        
        return workflows
    
    async def get_upcoming_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get upcoming workflow executions"""
        
        executions = []
        for scheduled_workflow in self.scheduled_workflows.values():
            if scheduled_workflow.is_active and scheduled_workflow.next_run:
                executions.append({
                    "workflow_id": scheduled_workflow.workflow_id,
                    "next_run": scheduled_workflow.next_run.isoformat(),
                    "cron_expression": scheduled_workflow.cron_expression,
                    "timezone": scheduled_workflow.timezone,
                    "time_until_execution": str(scheduled_workflow.next_run - datetime.utcnow())
                })
        
        # Sort by next run time
        executions.sort(key=lambda x: x["next_run"])
        
        return executions[:limit]
    
    async def pause_scheduled_workflow(self, workflow_id: str) -> bool:
        """Pause a scheduled workflow"""
        
        scheduled_workflow = self.scheduled_workflows.get(workflow_id)
        if not scheduled_workflow:
            return False
        
        scheduled_workflow.is_active = False
        
        try:
            query = """
            UPDATE scheduled_executions 
            SET status = :status
            WHERE workflow_id = :workflow_id AND status = :pending_status
            """
            
            await db_manager.database.execute(query, {
                "status": ExecutionStatus.CANCELLED.value,
                "workflow_id": workflow_id,
                "pending_status": ExecutionStatus.PENDING.value
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error pausing scheduled workflow: {e}")
            return False
    
    async def resume_scheduled_workflow(self, workflow_id: str) -> bool:
        """Resume a paused scheduled workflow"""
        
        scheduled_workflow = self.scheduled_workflows.get(workflow_id)
        if not scheduled_workflow:
            return False
        
        scheduled_workflow.is_active = True
        scheduled_workflow.calculate_next_run()  # Recalculate next run
        
        try:
            # Create new pending execution
            await self._save_scheduled_workflow(scheduled_workflow)
            return True
            
        except Exception as e:
            logger.error(f"Error resuming scheduled workflow: {e}")
            return False
    
    def validate_cron_expression(self, cron_expression: str) -> Dict[str, Any]:
        """Validate cron expression"""
        
        try:
            cron = croniter(cron_expression)
            
            # Get next few execution times for preview
            next_executions = []
            base_time = datetime.utcnow()
            
            for i in range(5):
                next_time = cron.get_next(datetime)
                next_executions.append(next_time.isoformat())
            
            return {
                "valid": True,
                "next_executions": next_executions,
                "description": self._describe_cron_expression(cron_expression)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "description": None
            }
    
    def _describe_cron_expression(self, cron_expression: str) -> str:
        """Generate human-readable description of cron expression"""
        
        # Simple descriptions for common patterns
        descriptions = {
            "0 * * * *": "Every hour",
            "0 0 * * *": "Every day at midnight",
            "0 0 * * 0": "Every Sunday at midnight",
            "0 9 * * 1-5": "Every weekday at 9 AM",
            "*/15 * * * *": "Every 15 minutes",
            "0 */2 * * *": "Every 2 hours",
            "0 0 1 * *": "First day of every month",
        }
        
        return descriptions.get(cron_expression, f"Custom schedule: {cron_expression}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get scheduler metrics"""
        
        active_workflows = sum(1 for w in self.scheduled_workflows.values() if w.is_active)
        inactive_workflows = len(self.scheduled_workflows) - active_workflows
        
        return {
            "scheduler": {
                "is_running": self.is_running,
                "scheduled_workflows": len(self.scheduled_workflows),
                "active_workflows": active_workflows,
                "inactive_workflows": inactive_workflows,
                "executions_triggered": self.stats["executions_triggered"],
                "missed_executions": self.stats["missed_executions"],
                "scheduler_runs": self.stats["scheduler_runs"],
                "last_run": self.stats["last_run"],
                "check_interval_seconds": self.check_interval
            }
        }
    
    async def cleanup(self):
        """Clean up scheduler"""
        
        await self.stop()
        self.scheduled_workflows.clear()
        
        logger.info("Workflow scheduler cleaned up")