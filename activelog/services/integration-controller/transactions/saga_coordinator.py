"""
Saga Pattern Implementation for Distributed Transactions

Provides comprehensive distributed transaction coordination using the Saga pattern including:
- Orchestration-based saga coordination
- Choreography-based saga patterns
- Transaction step execution and monitoring
- Compensation logic for rollbacks
- State persistence and recovery
- Timeout and failure handling
- Saga visualization and debugging
- Integration with service orchestrator
"""

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SagaStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATED = "compensated"
    FAILED = "failed"
    SKIPPED = "skipped"

class SagaType(Enum):
    ORCHESTRATION = "orchestration"
    CHOREOGRAPHY = "choreography"

class CompensationStrategy(Enum):
    REVERSE_ORDER = "reverse_order"
    PARALLEL = "parallel"
    SELECTIVE = "selective"

@dataclass
class SagaStep:
    """Individual step in a saga transaction"""
    step_id: str
    name: str
    service_name: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    compensation_action: Optional[str] = None
    compensation_parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 60
    retry_count: int = 3
    retry_delay: int = 5
    status: StepStatus = StepStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    order: int = 0
    idempotent: bool = True
    critical: bool = True  # If false, failure doesn't trigger compensation
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

@dataclass
class SagaDefinition:
    """Saga transaction definition"""
    saga_id: str
    name: str
    description: str
    steps: List[SagaStep] = field(default_factory=list)
    saga_type: SagaType = SagaType.ORCHESTRATION
    compensation_strategy: CompensationStrategy = CompensationStrategy.REVERSE_ORDER
    timeout: int = 3600
    max_retries: int = 3
    auto_retry: bool = True
    parallel_execution: bool = False
    status: SagaStatus = SagaStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SagaExecution:
    """Runtime saga execution state"""
    execution_id: str
    saga_id: str
    instance_id: str
    status: SagaStatus
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    compensated_steps: List[str] = field(default_factory=list)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None

class SagaStorage:
    """Persistent storage for saga definitions and executions"""
    
    def __init__(self, db_path: str = "saga_storage.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Saga definitions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saga_definitions (
                saga_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                steps TEXT,
                saga_type TEXT,
                compensation_strategy TEXT,
                timeout INTEGER,
                max_retries INTEGER,
                auto_retry BOOLEAN,
                parallel_execution BOOLEAN,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                metadata TEXT,
                context TEXT
            )
        ''')
        
        # Saga executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saga_executions (
                execution_id TEXT PRIMARY KEY,
                saga_id TEXT,
                instance_id TEXT,
                status TEXT,
                current_step TEXT,
                completed_steps TEXT,
                failed_steps TEXT,
                compensated_steps TEXT,
                execution_log TEXT,
                started_at TEXT,
                updated_at TEXT,
                error_message TEXT,
                FOREIGN KEY (saga_id) REFERENCES saga_definitions (saga_id)
            )
        ''')
        
        # Step executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS step_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT,
                step_id TEXT,
                status TEXT,
                start_time TEXT,
                end_time TEXT,
                error_message TEXT,
                result TEXT,
                compensation_executed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (execution_id) REFERENCES saga_executions (execution_id)
            )
        ''')
        
        # Saga events table for choreography
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saga_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                saga_id TEXT,
                execution_id TEXT,
                event_type TEXT,
                step_id TEXT,
                timestamp TEXT,
                payload TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_saga_definition(self, saga: SagaDefinition):
        """Save saga definition to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO saga_definitions 
            (saga_id, name, description, steps, saga_type, compensation_strategy,
             timeout, max_retries, auto_retry, parallel_execution, status,
             created_at, started_at, completed_at, metadata, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            saga.saga_id, saga.name, saga.description,
            json.dumps([asdict(step) for step in saga.steps]),
            saga.saga_type.value, saga.compensation_strategy.value,
            saga.timeout, saga.max_retries, saga.auto_retry,
            saga.parallel_execution, saga.status.value,
            saga.created_at.isoformat(),
            saga.started_at.isoformat() if saga.started_at else None,
            saga.completed_at.isoformat() if saga.completed_at else None,
            json.dumps(saga.metadata), json.dumps(saga.context)
        ))
        
        conn.commit()
        conn.close()
    
    def load_saga_definition(self, saga_id: str) -> Optional[SagaDefinition]:
        """Load saga definition from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM saga_definitions WHERE saga_id = ?', (saga_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        steps_data = json.loads(row[3]) if row[3] else []
        steps = []
        for step_data in steps_data:
            # Convert datetime strings back to datetime objects
            if step_data.get('start_time'):
                step_data['start_time'] = datetime.fromisoformat(step_data['start_time'])
            if step_data.get('end_time'):
                step_data['end_time'] = datetime.fromisoformat(step_data['end_time'])
            
            step = SagaStep(**step_data)
            step.status = StepStatus(step_data['status'])
            steps.append(step)
        
        saga = SagaDefinition(
            saga_id=row[0],
            name=row[1],
            description=row[2],
            steps=steps,
            saga_type=SagaType(row[4]),
            compensation_strategy=CompensationStrategy(row[5]),
            timeout=row[6],
            max_retries=row[7],
            auto_retry=row[8],
            parallel_execution=row[9],
            status=SagaStatus(row[10]),
            created_at=datetime.fromisoformat(row[11]) if row[11] else datetime.now(),
            started_at=datetime.fromisoformat(row[12]) if row[12] else None,
            completed_at=datetime.fromisoformat(row[13]) if row[13] else None,
            metadata=json.loads(row[14]) if row[14] else {},
            context=json.loads(row[15]) if row[15] else {}
        )
        
        conn.close()
        return saga
    
    def save_saga_execution(self, execution: SagaExecution):
        """Save saga execution state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO saga_executions 
            (execution_id, saga_id, instance_id, status, current_step,
             completed_steps, failed_steps, compensated_steps, execution_log,
             started_at, updated_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            execution.execution_id, execution.saga_id, execution.instance_id,
            execution.status.value, execution.current_step,
            json.dumps(execution.completed_steps),
            json.dumps(execution.failed_steps),
            json.dumps(execution.compensated_steps),
            json.dumps(execution.execution_log),
            execution.started_at.isoformat(),
            execution.updated_at.isoformat(),
            execution.error_message
        ))
        
        conn.commit()
        conn.close()
    
    def load_saga_execution(self, execution_id: str) -> Optional[SagaExecution]:
        """Load saga execution state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM saga_executions WHERE execution_id = ?', (execution_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        execution = SagaExecution(
            execution_id=row[0],
            saga_id=row[1],
            instance_id=row[2],
            status=SagaStatus(row[3]),
            current_step=row[4],
            completed_steps=json.loads(row[5]) if row[5] else [],
            failed_steps=json.loads(row[6]) if row[6] else [],
            compensated_steps=json.loads(row[7]) if row[7] else [],
            execution_log=json.loads(row[8]) if row[8] else [],
            started_at=datetime.fromisoformat(row[9]),
            updated_at=datetime.fromisoformat(row[10]),
            error_message=row[11]
        )
        
        conn.close()
        return execution

class SagaStepExecutor:
    """Executes individual saga steps"""
    
    def __init__(self, service_orchestrator):
        self.service_orchestrator = service_orchestrator
    
    async def execute_step(self, step: SagaStep, context: Dict[str, Any]) -> bool:
        """Execute a saga step"""
        step.status = StepStatus.RUNNING
        step.start_time = datetime.now()
        
        try:
            # Check condition if specified
            if step.condition and not self._evaluate_condition(step.condition, context):
                step.status = StepStatus.SKIPPED
                step.end_time = datetime.now()
                logger.info(f"Step {step.step_id} skipped due to condition")
                return True
            
            # Execute step with retries
            for attempt in range(step.retry_count + 1):
                try:
                    result = await self.service_orchestrator.execute_action(
                        step.service_name, step.action, step.parameters
                    )
                    
                    step.result = result
                    step.status = StepStatus.COMPLETED
                    step.end_time = datetime.now()
                    
                    # Update context with step result
                    context[f"step_{step.step_id}_result"] = result
                    
                    logger.info(f"Step {step.step_id} completed successfully")
                    return True
                    
                except Exception as e:
                    if attempt < step.retry_count:
                        logger.warning(f"Step {step.step_id} failed (attempt {attempt + 1}), retrying in {step.retry_delay}s: {e}")
                        await asyncio.sleep(step.retry_delay)
                    else:
                        raise e
        
        except Exception as e:
            step.error_message = str(e)
            step.status = StepStatus.FAILED
            step.end_time = datetime.now()
            logger.error(f"Step {step.step_id} failed: {e}")
            return False
    
    async def compensate_step(self, step: SagaStep, context: Dict[str, Any]) -> bool:
        """Execute compensation for a step"""
        if not step.compensation_action:
            logger.warning(f"No compensation action defined for step {step.step_id}")
            return True
        
        try:
            logger.info(f"Compensating step {step.step_id}")
            
            result = await self.service_orchestrator.execute_action(
                step.service_name, 
                step.compensation_action, 
                step.compensation_parameters or step.parameters
            )
            
            step.status = StepStatus.COMPENSATED
            logger.info(f"Step {step.step_id} compensated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compensate step {step.step_id}: {e}")
            return False
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate step condition"""
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return True

class OrchestrationSagaCoordinator:
    """Orchestration-based saga coordinator"""
    
    def __init__(self, service_orchestrator, storage: SagaStorage):
        self.service_orchestrator = service_orchestrator
        self.storage = storage
        self.step_executor = SagaStepExecutor(service_orchestrator)
    
    async def execute_saga(self, saga: SagaDefinition, instance_id: str = None) -> SagaExecution:
        """Execute a saga using orchestration pattern"""
        if not instance_id:
            instance_id = str(uuid.uuid4())
        
        execution_id = str(uuid.uuid4())
        execution = SagaExecution(
            execution_id=execution_id,
            saga_id=saga.saga_id,
            instance_id=instance_id,
            status=SagaStatus.RUNNING
        )
        
        saga.status = SagaStatus.RUNNING
        saga.started_at = datetime.now()
        
        self.storage.save_saga_definition(saga)
        self.storage.save_saga_execution(execution)
        
        try:
            success = await self._execute_saga_steps(saga, execution)
            
            if success:
                execution.status = SagaStatus.COMPLETED
                saga.status = SagaStatus.COMPLETED
            else:
                # Start compensation
                execution.status = SagaStatus.COMPENSATING
                saga.status = SagaStatus.COMPENSATING
                
                compensation_success = await self._compensate_saga(saga, execution)
                
                if compensation_success:
                    execution.status = SagaStatus.COMPENSATED
                    saga.status = SagaStatus.COMPENSATED
                else:
                    execution.status = SagaStatus.FAILED
                    saga.status = SagaStatus.FAILED
            
            execution.updated_at = datetime.now()
            saga.completed_at = datetime.now()
            
        except Exception as e:
            execution.status = SagaStatus.FAILED
            execution.error_message = str(e)
            execution.updated_at = datetime.now()
            
            saga.status = SagaStatus.FAILED
            saga.completed_at = datetime.now()
            
            logger.error(f"Saga {saga.saga_id} execution failed: {e}")
        
        self.storage.save_saga_definition(saga)
        self.storage.save_saga_execution(execution)
        
        return execution
    
    async def _execute_saga_steps(self, saga: SagaDefinition, execution: SagaExecution) -> bool:
        """Execute all steps in the saga"""
        context = saga.context.copy()
        
        if saga.parallel_execution:
            return await self._execute_parallel_steps(saga, execution, context)
        else:
            return await self._execute_sequential_steps(saga, execution, context)
    
    async def _execute_sequential_steps(self, saga: SagaDefinition, execution: SagaExecution, context: Dict[str, Any]) -> bool:
        """Execute steps sequentially"""
        # Sort steps by order and resolve dependencies
        sorted_steps = self._resolve_step_dependencies(saga.steps)
        
        for step in sorted_steps:
            execution.current_step = step.step_id
            self.storage.save_saga_execution(execution)
            
            # Log step start
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "step_started",
                "step_id": step.step_id,
                "step_name": step.name
            }
            execution.execution_log.append(log_entry)
            
            success = await self.step_executor.execute_step(step, context)
            
            # Log step completion
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "step_completed" if success else "step_failed",
                "step_id": step.step_id,
                "success": success,
                "error": step.error_message if not success else None
            }
            execution.execution_log.append(log_entry)
            
            if success:
                execution.completed_steps.append(step.step_id)
            else:
                execution.failed_steps.append(step.step_id)
                
                # Check if step is critical
                if step.critical:
                    return False
            
            self.storage.save_saga_execution(execution)
        
        return True
    
    async def _execute_parallel_steps(self, saga: SagaDefinition, execution: SagaExecution, context: Dict[str, Any]) -> bool:
        """Execute steps in parallel where possible"""
        dependency_levels = self._get_dependency_levels(saga.steps)
        
        for level_steps in dependency_levels:
            # Execute all steps in current level in parallel
            tasks = []
            for step in level_steps:
                execution.current_step = step.step_id
                task = self.step_executor.execute_step(step, context.copy())
                tasks.append((step, task))
            
            # Wait for all tasks in current level
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            level_success = True
            for i, (step, result) in enumerate(zip([s for s, _ in tasks], results)):
                if isinstance(result, Exception) or not result:
                    execution.failed_steps.append(step.step_id)
                    if step.critical:
                        level_success = False
                else:
                    execution.completed_steps.append(step.step_id)
            
            if not level_success:
                return False
        
        return True
    
    def _resolve_step_dependencies(self, steps: List[SagaStep]) -> List[SagaStep]:
        """Resolve step dependencies and return ordered list"""
        step_map = {step.step_id: step for step in steps}
        resolved = []
        processed = set()
        
        def resolve_step(step: SagaStep):
            if step.step_id in processed:
                return
            
            # First resolve all dependencies
            for dep_id in step.dependencies:
                if dep_id in step_map and dep_id not in processed:
                    resolve_step(step_map[dep_id])
            
            resolved.append(step)
            processed.add(step.step_id)
        
        # Sort by order first, then resolve dependencies
        sorted_steps = sorted(steps, key=lambda s: s.order)
        for step in sorted_steps:
            resolve_step(step)
        
        return resolved
    
    def _get_dependency_levels(self, steps: List[SagaStep]) -> List[List[SagaStep]]:
        """Group steps by dependency levels for parallel execution"""
        step_map = {step.step_id: step for step in steps}
        levels = []
        processed = set()
        
        while len(processed) < len(steps):
            current_level = []
            
            for step in steps:
                if (step.step_id not in processed and 
                    all(dep in processed for dep in step.dependencies)):
                    current_level.append(step)
            
            if not current_level:
                # Circular dependency
                remaining = [s for s in steps if s.step_id not in processed]
                levels.append(remaining)
                break
            
            levels.append(current_level)
            processed.update(step.step_id for step in current_level)
        
        return levels
    
    async def _compensate_saga(self, saga: SagaDefinition, execution: SagaExecution) -> bool:
        """Compensate completed steps in reverse order"""
        completed_steps = [
            step for step in saga.steps 
            if step.step_id in execution.completed_steps
        ]
        
        if saga.compensation_strategy == CompensationStrategy.REVERSE_ORDER:
            # Compensate in reverse order of execution
            compensation_order = reversed(completed_steps)
        elif saga.compensation_strategy == CompensationStrategy.PARALLEL:
            # Compensate all steps in parallel
            compensation_tasks = [
                self.step_executor.compensate_step(step, saga.context)
                for step in completed_steps
            ]
            results = await asyncio.gather(*compensation_tasks, return_exceptions=True)
            return all(result is True or not isinstance(result, Exception) for result in results)
        else:
            # Selective compensation based on step configuration
            compensation_order = [step for step in completed_steps if step.compensation_action]
        
        for step in compensation_order:
            success = await self.step_executor.compensate_step(step, saga.context)
            if success:
                execution.compensated_steps.append(step.step_id)
            else:
                logger.error(f"Failed to compensate step {step.step_id}")
                return False
        
        return True

class ChoreographySagaCoordinator:
    """Choreography-based saga coordinator using events"""
    
    def __init__(self, event_bus, storage: SagaStorage):
        self.event_bus = event_bus
        self.storage = storage
        self.active_sagas: Dict[str, SagaExecution] = {}
    
    async def start_saga(self, saga: SagaDefinition, initial_event: Dict[str, Any]) -> str:
        """Start a choreography saga by publishing initial event"""
        execution_id = str(uuid.uuid4())
        instance_id = str(uuid.uuid4())
        
        execution = SagaExecution(
            execution_id=execution_id,
            saga_id=saga.saga_id,
            instance_id=instance_id,
            status=SagaStatus.RUNNING
        )
        
        self.active_sagas[execution_id] = execution
        self.storage.save_saga_execution(execution)
        
        # Publish initial event to start the saga
        from ..messaging.event_bus import create_event
        event = create_event(
            event_type=f"saga_{saga.saga_id}_started",
            source="saga_coordinator",
            data={
                "saga_id": saga.saga_id,
                "execution_id": execution_id,
                "instance_id": instance_id,
                **initial_event
            }
        )
        
        await self.event_bus.publish(event)
        logger.info(f"Started choreography saga {saga.saga_id} with execution {execution_id}")
        
        return execution_id
    
    def register_saga_event_handlers(self, saga: SagaDefinition):
        """Register event handlers for saga steps"""
        from ..messaging.event_bus import create_subscription
        
        for step in saga.steps:
            # Subscribe to step completion events
            subscription = create_subscription(
                service_name="saga_coordinator",
                event_types=[f"step_{step.step_id}_completed", f"step_{step.step_id}_failed"],
                handler=self._handle_step_event
            )
            self.event_bus.subscribe(subscription)
    
    def _handle_step_event(self, event):
        """Handle step completion/failure events"""
        # This would be implemented to process step events and trigger next steps
        # For now, just log the event
        logger.info(f"Received saga step event: {event.event_type}")

class SagaCoordinator:
    """Main saga coordinator that supports both orchestration and choreography"""
    
    def __init__(self, service_orchestrator, event_bus=None):
        self.service_orchestrator = service_orchestrator
        self.event_bus = event_bus
        self.storage = SagaStorage()
        self.orchestration_coordinator = OrchestrationSagaCoordinator(service_orchestrator, self.storage)
        if event_bus:
            self.choreography_coordinator = ChoreographySagaCoordinator(event_bus, self.storage)
        self.active_executions: Dict[str, SagaExecution] = {}
    
    def create_saga(self, name: str, description: str = "", **kwargs) -> str:
        """Create a new saga definition"""
        saga_id = str(uuid.uuid4())
        saga = SagaDefinition(
            saga_id=saga_id,
            name=name,
            description=description,
            **kwargs
        )
        
        self.storage.save_saga_definition(saga)
        logger.info(f"Created saga {saga_id}: {name}")
        return saga_id
    
    def add_step(self, saga_id: str, step: SagaStep):
        """Add a step to a saga"""
        saga = self.storage.load_saga_definition(saga_id)
        if not saga:
            raise ValueError(f"Saga {saga_id} not found")
        
        saga.steps.append(step)
        self.storage.save_saga_definition(saga)
        logger.info(f"Added step {step.step_id} to saga {saga_id}")
    
    async def execute_saga(self, saga_id: str, instance_id: str = None) -> SagaExecution:
        """Execute a saga"""
        saga = self.storage.load_saga_definition(saga_id)
        if not saga:
            raise ValueError(f"Saga {saga_id} not found")
        
        if saga.saga_type == SagaType.ORCHESTRATION:
            return await self.orchestration_coordinator.execute_saga(saga, instance_id)
        else:
            raise NotImplementedError("Choreography sagas not fully implemented in this example")
    
    def get_saga_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get saga execution status"""
        execution = self.storage.load_saga_execution(execution_id)
        if not execution:
            return None
        
        saga = self.storage.load_saga_definition(execution.saga_id)
        if not saga:
            return None
        
        return {
            "execution_id": execution.execution_id,
            "saga_id": execution.saga_id,
            "saga_name": saga.name,
            "status": execution.status.value,
            "progress": {
                "total_steps": len(saga.steps),
                "completed_steps": len(execution.completed_steps),
                "failed_steps": len(execution.failed_steps),
                "compensated_steps": len(execution.compensated_steps)
            },
            "current_step": execution.current_step,
            "started_at": execution.started_at.isoformat(),
            "updated_at": execution.updated_at.isoformat(),
            "error_message": execution.error_message,
            "execution_log": execution.execution_log
        }

# Factory function
def create_saga_coordinator(service_orchestrator, event_bus=None) -> SagaCoordinator:
    """Create and return a saga coordinator instance"""
    return SagaCoordinator(service_orchestrator, event_bus)

# Helper functions
def create_saga_step(name: str, service_name: str, action: str, **kwargs) -> SagaStep:
    """Create a saga step"""
    return SagaStep(
        step_id=str(uuid.uuid4()),
        name=name,
        service_name=service_name,
        action=action,
        **kwargs
    )

def create_payment_saga() -> Tuple[str, List[SagaStep]]:
    """Create a sample payment processing saga"""
    saga_id = str(uuid.uuid4())
    
    steps = [
        SagaStep(
            step_id="validate_payment",
            name="Validate Payment Details",
            service_name="payment-service",
            action="validate_payment",
            compensation_action="cancel_payment_validation",
            order=1
        ),
        SagaStep(
            step_id="reserve_inventory",
            name="Reserve Inventory",
            service_name="inventory-service",
            action="reserve_items",
            compensation_action="release_reservation",
            dependencies=["validate_payment"],
            order=2
        ),
        SagaStep(
            step_id="process_payment",
            name="Process Payment",
            service_name="payment-service",
            action="charge_payment",
            compensation_action="refund_payment",
            dependencies=["reserve_inventory"],
            order=3
        ),
        SagaStep(
            step_id="confirm_order",
            name="Confirm Order",
            service_name="order-service",
            action="confirm_order",
            compensation_action="cancel_order",
            dependencies=["process_payment"],
            order=4
        )
    ]
    
    return saga_id, steps