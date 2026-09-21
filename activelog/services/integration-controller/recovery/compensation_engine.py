"""
Compensation Engine for Failure Recovery

Provides comprehensive compensation and failure recovery mechanisms including:
- Automatic compensation strategy selection
- Multi-level compensation (step, workflow, system)
- Idempotent compensation operations
- Compensation monitoring and verification
- State-based recovery patterns
- Timeout and retry handling for compensations
- Recovery point management
- Integration with saga pattern and workflows
"""

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompensationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"

class RecoveryStrategy(Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    MIXED = "mixed"

class CompensationType(Enum):
    ROLLBACK = "rollback"
    FORWARD_RECOVERY = "forward_recovery"
    COMPENSATING_ACTION = "compensating_action"
    STATE_RESTORATION = "state_restoration"

class RecoveryLevel(Enum):
    STEP = "step"
    TRANSACTION = "transaction" 
    WORKFLOW = "workflow"
    SYSTEM = "system"

@dataclass
class RecoveryPoint:
    """Recovery checkpoint for state restoration"""
    recovery_point_id: str
    name: str
    entity_id: str
    entity_type: str
    state_snapshot: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    valid_until: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

@dataclass
class CompensationAction:
    """Individual compensation action definition"""
    action_id: str
    name: str
    compensation_type: CompensationType
    target_service: str
    target_action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    timeout: int = 60
    retry_count: int = 3
    retry_delay: int = 5
    idempotent: bool = True
    verification_action: Optional[str] = None
    verification_parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    condition: Optional[str] = None
    recovery_level: RecoveryLevel = RecoveryLevel.STEP

@dataclass
class CompensationPlan:
    """Complete compensation execution plan"""
    plan_id: str
    name: str
    description: str
    target_entity: str
    target_entity_type: str
    actions: List[CompensationAction] = field(default_factory=list)
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.AUTOMATIC
    execution_order: List[str] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    timeout: int = 300
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CompensationExecution:
    """Runtime compensation execution state"""
    execution_id: str
    plan_id: str
    target_entity: str
    status: CompensationStatus
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    executed_actions: List[str] = field(default_factory=list)
    failed_actions: List[str] = field(default_factory=list)
    skipped_actions: List[str] = field(default_factory=list)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    recovery_points_used: List[str] = field(default_factory=list)
    verification_results: Dict[str, bool] = field(default_factory=dict)

class CompensationStorage:
    """Persistent storage for compensation data"""
    
    def __init__(self, db_path: str = "compensation_storage.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Recovery points table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_points (
                recovery_point_id TEXT PRIMARY KEY,
                name TEXT,
                entity_id TEXT,
                entity_type TEXT,
                state_snapshot TEXT,
                created_at TEXT,
                metadata TEXT,
                valid_until TEXT,
                tags TEXT
            )
        ''')
        
        # Compensation plans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compensation_plans (
                plan_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                target_entity TEXT,
                target_entity_type TEXT,
                actions TEXT,
                recovery_strategy TEXT,
                execution_order TEXT,
                parallel_groups TEXT,
                timeout INTEGER,
                created_at TEXT,
                metadata TEXT,
                context TEXT
            )
        ''')
        
        # Compensation executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compensation_executions (
                execution_id TEXT PRIMARY KEY,
                plan_id TEXT,
                target_entity TEXT,
                status TEXT,
                started_at TEXT,
                completed_at TEXT,
                executed_actions TEXT,
                failed_actions TEXT,
                skipped_actions TEXT,
                execution_log TEXT,
                error_message TEXT,
                recovery_points_used TEXT,
                verification_results TEXT,
                FOREIGN KEY (plan_id) REFERENCES compensation_plans (plan_id)
            )
        ''')
        
        # Compensation history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compensation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT,
                action_id TEXT,
                event_type TEXT,
                timestamp TEXT,
                details TEXT,
                success BOOLEAN,
                FOREIGN KEY (execution_id) REFERENCES compensation_executions (execution_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_recovery_point(self, recovery_point: RecoveryPoint):
        """Save recovery point to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO recovery_points 
            (recovery_point_id, name, entity_id, entity_type, state_snapshot,
             created_at, metadata, valid_until, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recovery_point.recovery_point_id, recovery_point.name,
            recovery_point.entity_id, recovery_point.entity_type,
            json.dumps(recovery_point.state_snapshot),
            recovery_point.created_at.isoformat(), 
            json.dumps(recovery_point.metadata),
            recovery_point.valid_until.isoformat() if recovery_point.valid_until else None,
            json.dumps(recovery_point.tags)
        ))
        
        conn.commit()
        conn.close()
    
    def load_recovery_point(self, recovery_point_id: str) -> Optional[RecoveryPoint]:
        """Load recovery point from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM recovery_points WHERE recovery_point_id = ?', (recovery_point_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        recovery_point = RecoveryPoint(
            recovery_point_id=row[0],
            name=row[1],
            entity_id=row[2],
            entity_type=row[3],
            state_snapshot=json.loads(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            metadata=json.loads(row[6]) if row[6] else {},
            valid_until=datetime.fromisoformat(row[7]) if row[7] else None,
            tags=json.loads(row[8]) if row[8] else []
        )
        
        conn.close()
        return recovery_point
    
    def save_compensation_plan(self, plan: CompensationPlan):
        """Save compensation plan to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO compensation_plans 
            (plan_id, name, description, target_entity, target_entity_type,
             actions, recovery_strategy, execution_order, parallel_groups,
             timeout, created_at, metadata, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plan.plan_id, plan.name, plan.description, plan.target_entity,
            plan.target_entity_type, json.dumps([asdict(action) for action in plan.actions]),
            plan.recovery_strategy.value, json.dumps(plan.execution_order),
            json.dumps(plan.parallel_groups), plan.timeout,
            plan.created_at.isoformat(), json.dumps(plan.metadata),
            json.dumps(plan.context)
        ))
        
        conn.commit()
        conn.close()
    
    def load_compensation_plan(self, plan_id: str) -> Optional[CompensationPlan]:
        """Load compensation plan from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM compensation_plans WHERE plan_id = ?', (plan_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        actions_data = json.loads(row[5]) if row[5] else []
        actions = []
        for action_data in actions_data:
            action = CompensationAction(**action_data)
            action.compensation_type = CompensationType(action_data['compensation_type'])
            action.recovery_level = RecoveryLevel(action_data['recovery_level'])
            actions.append(action)
        
        plan = CompensationPlan(
            plan_id=row[0],
            name=row[1],
            description=row[2],
            target_entity=row[3],
            target_entity_type=row[4],
            actions=actions,
            recovery_strategy=RecoveryStrategy(row[6]),
            execution_order=json.loads(row[7]) if row[7] else [],
            parallel_groups=json.loads(row[8]) if row[8] else [],
            timeout=row[9],
            created_at=datetime.fromisoformat(row[10]),
            metadata=json.loads(row[11]) if row[11] else {},
            context=json.loads(row[12]) if row[12] else {}
        )
        
        conn.close()
        return plan

class RecoveryPointManager:
    """Manages recovery points for state restoration"""
    
    def __init__(self, storage: CompensationStorage):
        self.storage = storage
    
    def create_recovery_point(self, entity_id: str, entity_type: str, state: Dict[str, Any], 
                            name: str = None, ttl_hours: int = 24, **kwargs) -> str:
        """Create a new recovery point"""
        recovery_point_id = str(uuid.uuid4())
        
        recovery_point = RecoveryPoint(
            recovery_point_id=recovery_point_id,
            name=name or f"Recovery point for {entity_id}",
            entity_id=entity_id,
            entity_type=entity_type,
            state_snapshot=state,
            valid_until=datetime.now() + timedelta(hours=ttl_hours),
            **kwargs
        )
        
        self.storage.save_recovery_point(recovery_point)
        logger.info(f"Created recovery point {recovery_point_id} for {entity_type} {entity_id}")
        
        return recovery_point_id
    
    def restore_from_recovery_point(self, recovery_point_id: str) -> Optional[Dict[str, Any]]:
        """Restore state from a recovery point"""
        recovery_point = self.storage.load_recovery_point(recovery_point_id)
        
        if not recovery_point:
            logger.error(f"Recovery point {recovery_point_id} not found")
            return None
        
        if recovery_point.valid_until and datetime.now() > recovery_point.valid_until:
            logger.error(f"Recovery point {recovery_point_id} has expired")
            return None
        
        logger.info(f"Restored state from recovery point {recovery_point_id}")
        return recovery_point.state_snapshot
    
    def cleanup_expired_recovery_points(self):
        """Clean up expired recovery points"""
        # This would be implemented to remove expired recovery points
        pass

class CompensationActionExecutor:
    """Executes individual compensation actions"""
    
    def __init__(self, service_orchestrator):
        self.service_orchestrator = service_orchestrator
    
    async def execute_action(self, action: CompensationAction, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute a compensation action"""
        logger.info(f"Executing compensation action {action.action_id}: {action.name}")
        
        try:
            # Check condition if specified
            if action.condition and not self._evaluate_condition(action.condition, context):
                logger.info(f"Compensation action {action.action_id} skipped due to condition")
                return True, "Skipped due to condition"
            
            # Execute with retries
            for attempt in range(action.retry_count + 1):
                try:
                    # Execute the compensation action
                    result = await asyncio.wait_for(
                        self.service_orchestrator.execute_action(
                            action.target_service, action.target_action, action.parameters
                        ),
                        timeout=action.timeout
                    )
                    
                    # Verify the action if verification is specified
                    if action.verification_action:
                        verification_success = await self._verify_action(action, context)
                        if not verification_success:
                            raise Exception("Action verification failed")
                    
                    logger.info(f"Compensation action {action.action_id} completed successfully")
                    return True, None
                    
                except asyncio.TimeoutError:
                    error_msg = f"Compensation action {action.action_id} timed out"
                    if attempt < action.retry_count:
                        logger.warning(f"{error_msg}, retrying in {action.retry_delay}s")
                        await asyncio.sleep(action.retry_delay)
                    else:
                        logger.error(error_msg)
                        return False, error_msg
                        
                except Exception as e:
                    error_msg = f"Compensation action {action.action_id} failed: {str(e)}"
                    if attempt < action.retry_count:
                        logger.warning(f"{error_msg}, retrying in {action.retry_delay}s")
                        await asyncio.sleep(action.retry_delay)
                    else:
                        logger.error(error_msg)
                        return False, error_msg
                        
        except Exception as e:
            error_msg = f"Compensation action {action.action_id} failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def _verify_action(self, action: CompensationAction, context: Dict[str, Any]) -> bool:
        """Verify that a compensation action completed successfully"""
        try:
            result = await self.service_orchestrator.execute_action(
                action.target_service, action.verification_action, action.verification_parameters
            )
            
            # Simple verification - check if result indicates success
            if isinstance(result, dict):
                return result.get('success', True)
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Verification failed for action {action.action_id}: {e}")
            return False
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate action condition"""
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return True

class CompensationPlanGenerator:
    """Generates compensation plans automatically"""
    
    def __init__(self):
        self.action_templates = self._load_action_templates()
    
    def generate_plan(self, failure_context: Dict[str, Any]) -> CompensationPlan:
        """Generate a compensation plan based on failure context"""
        plan_id = str(uuid.uuid4())
        
        plan = CompensationPlan(
            plan_id=plan_id,
            name=f"Auto-generated compensation plan",
            description=f"Generated for {failure_context.get('entity_type', 'unknown')} failure",
            target_entity=failure_context.get('entity_id', ''),
            target_entity_type=failure_context.get('entity_type', 'unknown'),
            context=failure_context
        )
        
        # Generate actions based on failure type and context
        actions = self._generate_actions(failure_context)
        plan.actions = actions
        
        # Determine execution order
        plan.execution_order = self._determine_execution_order(actions)
        
        # Identify parallel groups
        plan.parallel_groups = self._identify_parallel_groups(actions)
        
        return plan
    
    def _load_action_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load compensation action templates"""
        return {
            "database_rollback": {
                "compensation_type": CompensationType.ROLLBACK,
                "target_action": "rollback_transaction",
                "idempotent": True,
                "priority": 10
            },
            "file_restore": {
                "compensation_type": CompensationType.STATE_RESTORATION,
                "target_action": "restore_file",
                "idempotent": True,
                "priority": 8
            },
            "cache_invalidate": {
                "compensation_type": CompensationType.COMPENSATING_ACTION,
                "target_action": "invalidate_cache",
                "idempotent": True,
                "priority": 5
            },
            "notification_cancel": {
                "compensation_type": CompensationType.COMPENSATING_ACTION,
                "target_action": "cancel_notification",
                "idempotent": True,
                "priority": 3
            }
        }
    
    def _generate_actions(self, failure_context: Dict[str, Any]) -> List[CompensationAction]:
        """Generate compensation actions based on failure context"""
        actions = []
        
        # This is a simplified example - in practice, this would be more sophisticated
        failed_operations = failure_context.get('failed_operations', [])
        
        for operation in failed_operations:
            if operation.get('type') == 'database_operation':
                action = CompensationAction(
                    action_id=str(uuid.uuid4()),
                    name=f"Rollback database operation {operation['id']}",
                    compensation_type=CompensationType.ROLLBACK,
                    target_service=operation.get('service', 'database-service'),
                    target_action="rollback_transaction",
                    parameters={'transaction_id': operation.get('transaction_id')},
                    priority=10
                )
                actions.append(action)
                
            elif operation.get('type') == 'file_operation':
                action = CompensationAction(
                    action_id=str(uuid.uuid4()),
                    name=f"Restore file {operation['file_path']}",
                    compensation_type=CompensationType.STATE_RESTORATION,
                    target_service=operation.get('service', 'file-service'),
                    target_action="restore_file",
                    parameters={'file_path': operation.get('file_path')},
                    priority=8
                )
                actions.append(action)
        
        return actions
    
    def _determine_execution_order(self, actions: List[CompensationAction]) -> List[str]:
        """Determine the execution order of actions"""
        # Sort by priority (higher priority first) and handle dependencies
        sorted_actions = sorted(actions, key=lambda x: x.priority, reverse=True)
        return [action.action_id for action in sorted_actions]
    
    def _identify_parallel_groups(self, actions: List[CompensationAction]) -> List[List[str]]:
        """Identify actions that can be executed in parallel"""
        # Group actions that have no dependencies and same priority
        priority_groups = {}
        for action in actions:
            if not action.prerequisites:
                if action.priority not in priority_groups:
                    priority_groups[action.priority] = []
                priority_groups[action.priority].append(action.action_id)
        
        return [group for group in priority_groups.values() if len(group) > 1]

class CompensationEngine:
    """Main compensation engine"""
    
    def __init__(self, service_orchestrator):
        self.service_orchestrator = service_orchestrator
        self.storage = CompensationStorage()
        self.recovery_point_manager = RecoveryPointManager(self.storage)
        self.action_executor = CompensationActionExecutor(service_orchestrator)
        self.plan_generator = CompensationPlanGenerator()
        self.active_executions: Dict[str, CompensationExecution] = {}
    
    def create_recovery_point(self, entity_id: str, entity_type: str, state: Dict[str, Any], **kwargs) -> str:
        """Create a recovery point"""
        return self.recovery_point_manager.create_recovery_point(entity_id, entity_type, state, **kwargs)
    
    def create_compensation_plan(self, name: str, target_entity: str, target_entity_type: str, **kwargs) -> str:
        """Create a compensation plan"""
        plan_id = str(uuid.uuid4())
        plan = CompensationPlan(
            plan_id=plan_id,
            name=name,
            target_entity=target_entity,
            target_entity_type=target_entity_type,
            **kwargs
        )
        
        self.storage.save_compensation_plan(plan)
        logger.info(f"Created compensation plan {plan_id}: {name}")
        return plan_id
    
    def add_compensation_action(self, plan_id: str, action: CompensationAction):
        """Add an action to a compensation plan"""
        plan = self.storage.load_compensation_plan(plan_id)
        if not plan:
            raise ValueError(f"Compensation plan {plan_id} not found")
        
        plan.actions.append(action)
        plan.execution_order.append(action.action_id)
        
        self.storage.save_compensation_plan(plan)
        logger.info(f"Added action {action.action_id} to compensation plan {plan_id}")
    
    async def execute_compensation_plan(self, plan_id: str, context: Dict[str, Any] = None) -> CompensationExecution:
        """Execute a compensation plan"""
        plan = self.storage.load_compensation_plan(plan_id)
        if not plan:
            raise ValueError(f"Compensation plan {plan_id} not found")
        
        execution_id = str(uuid.uuid4())
        execution = CompensationExecution(
            execution_id=execution_id,
            plan_id=plan_id,
            target_entity=plan.target_entity,
            status=CompensationStatus.RUNNING
        )
        
        if context is None:
            context = plan.context.copy()
        else:
            context.update(plan.context)
        
        self.active_executions[execution_id] = execution
        
        try:
            success = await self._execute_plan_actions(plan, execution, context)
            
            execution.status = CompensationStatus.COMPLETED if success else CompensationStatus.PARTIAL
            execution.completed_at = datetime.now()
            
        except Exception as e:
            execution.status = CompensationStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            logger.error(f"Compensation plan {plan_id} execution failed: {e}")
        
        finally:
            self.active_executions.pop(execution_id, None)
        
        return execution
    
    async def _execute_plan_actions(self, plan: CompensationPlan, execution: CompensationExecution, 
                                   context: Dict[str, Any]) -> bool:
        """Execute all actions in a compensation plan"""
        action_map = {action.action_id: action for action in plan.actions}
        
        # Execute actions based on execution order
        if plan.parallel_groups:
            return await self._execute_parallel_groups(plan, execution, context, action_map)
        else:
            return await self._execute_sequential_actions(plan, execution, context, action_map)
    
    async def _execute_sequential_actions(self, plan: CompensationPlan, execution: CompensationExecution,
                                        context: Dict[str, Any], action_map: Dict[str, CompensationAction]) -> bool:
        """Execute actions sequentially"""
        overall_success = True
        
        for action_id in plan.execution_order:
            if action_id not in action_map:
                continue
            
            action = action_map[action_id]
            
            # Check prerequisites
            if not all(prereq in execution.executed_actions for prereq in action.prerequisites):
                logger.warning(f"Prerequisites not met for action {action_id}, skipping")
                execution.skipped_actions.append(action_id)
                continue
            
            # Execute action
            success, error_msg = await self.action_executor.execute_action(action, context)
            
            # Log execution
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action_id": action_id,
                "action_name": action.name,
                "success": success,
                "error": error_msg
            }
            execution.execution_log.append(log_entry)
            
            if success:
                execution.executed_actions.append(action_id)
            else:
                execution.failed_actions.append(action_id)
                overall_success = False
                
                # Stop on first failure for critical actions
                if action.priority >= 8:
                    break
        
        return overall_success
    
    async def _execute_parallel_groups(self, plan: CompensationPlan, execution: CompensationExecution,
                                     context: Dict[str, Any], action_map: Dict[str, CompensationAction]) -> bool:
        """Execute actions with parallel groups"""
        overall_success = True
        executed_actions = set()
        
        # Execute parallel groups
        for group in plan.parallel_groups:
            group_actions = [action_map[aid] for aid in group if aid in action_map]
            
            # Execute group actions in parallel
            tasks = [
                self.action_executor.execute_action(action, context.copy()) 
                for action in group_actions
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, (action, result) in enumerate(zip(group_actions, results)):
                if isinstance(result, Exception):
                    success, error_msg = False, str(result)
                else:
                    success, error_msg = result
                
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "action_id": action.action_id,
                    "action_name": action.name,
                    "success": success,
                    "error": error_msg
                }
                execution.execution_log.append(log_entry)
                
                if success:
                    execution.executed_actions.append(action.action_id)
                    executed_actions.add(action.action_id)
                else:
                    execution.failed_actions.append(action.action_id)
                    overall_success = False
        
        # Execute remaining sequential actions
        remaining_actions = [
            action_id for action_id in plan.execution_order 
            if action_id not in executed_actions and action_id in action_map
        ]
        
        for action_id in remaining_actions:
            action = action_map[action_id]
            success, error_msg = await self.action_executor.execute_action(action, context)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action_id": action_id,
                "action_name": action.name,
                "success": success,
                "error": error_msg
            }
            execution.execution_log.append(log_entry)
            
            if success:
                execution.executed_actions.append(action_id)
            else:
                execution.failed_actions.append(action_id)
                overall_success = False
        
        return overall_success
    
    def auto_generate_compensation_plan(self, failure_context: Dict[str, Any]) -> str:
        """Auto-generate a compensation plan from failure context"""
        plan = self.plan_generator.generate_plan(failure_context)
        self.storage.save_compensation_plan(plan)
        
        logger.info(f"Auto-generated compensation plan {plan.plan_id}")
        return plan.plan_id
    
    def get_compensation_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get compensation execution status"""
        # Check active executions first
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
        else:
            # Load from storage if not active
            execution = None  # Would implement storage loading
        
        if not execution:
            return None
        
        return {
            "execution_id": execution.execution_id,
            "plan_id": execution.plan_id,
            "target_entity": execution.target_entity,
            "status": execution.status.value,
            "progress": {
                "executed_actions": len(execution.executed_actions),
                "failed_actions": len(execution.failed_actions),
                "skipped_actions": len(execution.skipped_actions)
            },
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "error_message": execution.error_message,
            "execution_log": execution.execution_log
        }

# Factory function
def create_compensation_engine(service_orchestrator) -> CompensationEngine:
    """Create and return a compensation engine instance"""
    return CompensationEngine(service_orchestrator)

# Helper functions
def create_compensation_action(name: str, target_service: str, target_action: str, **kwargs) -> CompensationAction:
    """Create a compensation action"""
    return CompensationAction(
        action_id=str(uuid.uuid4()),
        name=name,
        target_service=target_service,
        target_action=target_action,
        **kwargs
    )