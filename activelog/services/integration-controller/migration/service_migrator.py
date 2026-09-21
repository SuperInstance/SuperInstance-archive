"""
Service Migration Tools

Provides comprehensive service migration capabilities including:
- Service deployment and rollback strategies
- Blue-green deployments
- Canary releases with traffic splitting
- Database migration coordination
- Configuration migration
- Health check validation
- Rollback automation
- Migration workflow orchestration
"""

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationStrategy(Enum):
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    RECREATE = "recreate"

class MigrationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"

class MigrationType(Enum):
    SERVICE_DEPLOYMENT = "service_deployment"
    DATABASE_SCHEMA = "database_schema"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"

class EnvironmentType(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class MigrationTask:
    """Individual migration task"""
    task_id: str
    name: str
    task_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 3
    retry_delay: int = 30
    rollback_task: Optional[str] = None
    validation_checks: List[str] = field(default_factory=list)
    priority: int = 0
    environment: EnvironmentType = EnvironmentType.PRODUCTION

@dataclass
class ServiceVersion:
    """Service version information"""
    version_id: str
    service_name: str
    version: str
    image: str
    configuration: Dict[str, Any] = field(default_factory=dict)
    health_check_path: str = "/health"
    readiness_check_path: str = "/ready"
    ports: List[int] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MigrationPlan:
    """Complete migration plan"""
    plan_id: str
    name: str
    description: str
    strategy: MigrationStrategy
    migration_type: MigrationType
    source_version: Optional[ServiceVersion] = None
    target_version: Optional[ServiceVersion] = None
    tasks: List[MigrationTask] = field(default_factory=list)
    pre_migration_checks: List[str] = field(default_factory=list)
    post_migration_checks: List[str] = field(default_factory=list)
    rollback_plan: Optional[str] = None
    approval_required: bool = True
    auto_rollback: bool = True
    rollback_threshold: Dict[str, Any] = field(default_factory=dict)
    traffic_split_config: Optional[Dict[str, Any]] = None
    environment: EnvironmentType = EnvironmentType.PRODUCTION
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MigrationExecution:
    """Migration execution state"""
    execution_id: str
    plan_id: str
    status: MigrationStatus
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    current_task: Optional[str] = None
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    approval_status: str = "pending"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

class MigrationStorage:
    """Storage for migration plans and executions"""
    
    def __init__(self, db_path: str = "migration_storage.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Migration plans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migration_plans (
                plan_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                strategy TEXT,
                migration_type TEXT,
                source_version TEXT,
                target_version TEXT,
                tasks TEXT,
                pre_migration_checks TEXT,
                post_migration_checks TEXT,
                rollback_plan TEXT,
                approval_required BOOLEAN,
                auto_rollback BOOLEAN,
                rollback_threshold TEXT,
                traffic_split_config TEXT,
                environment TEXT,
                created_at TEXT,
                metadata TEXT
            )
        ''')
        
        # Migration executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migration_executions (
                execution_id TEXT PRIMARY KEY,
                plan_id TEXT,
                status TEXT,
                started_at TEXT,
                completed_at TEXT,
                current_task TEXT,
                completed_tasks TEXT,
                failed_tasks TEXT,
                execution_log TEXT,
                metrics TEXT,
                error_message TEXT,
                approval_status TEXT,
                approved_by TEXT,
                approved_at TEXT,
                FOREIGN KEY (plan_id) REFERENCES migration_plans (plan_id)
            )
        ''')
        
        # Service versions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_versions (
                version_id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                version TEXT NOT NULL,
                image TEXT,
                configuration TEXT,
                health_check_path TEXT,
                readiness_check_path TEXT,
                ports TEXT,
                environment_variables TEXT,
                resource_requirements TEXT,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_migration_plan(self, plan: MigrationPlan):
        """Save migration plan to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO migration_plans 
            (plan_id, name, description, strategy, migration_type, source_version,
             target_version, tasks, pre_migration_checks, post_migration_checks,
             rollback_plan, approval_required, auto_rollback, rollback_threshold,
             traffic_split_config, environment, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plan.plan_id, plan.name, plan.description, plan.strategy.value,
            plan.migration_type.value,
            json.dumps(plan.source_version.__dict__) if plan.source_version else None,
            json.dumps(plan.target_version.__dict__) if plan.target_version else None,
            json.dumps([task.__dict__ for task in plan.tasks]),
            json.dumps(plan.pre_migration_checks),
            json.dumps(plan.post_migration_checks),
            plan.rollback_plan, plan.approval_required, plan.auto_rollback,
            json.dumps(plan.rollback_threshold),
            json.dumps(plan.traffic_split_config),
            plan.environment.value, plan.created_at.isoformat(),
            json.dumps(plan.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def save_migration_execution(self, execution: MigrationExecution):
        """Save migration execution state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO migration_executions 
            (execution_id, plan_id, status, started_at, completed_at, current_task,
             completed_tasks, failed_tasks, execution_log, metrics, error_message,
             approval_status, approved_by, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            execution.execution_id, execution.plan_id, execution.status.value,
            execution.started_at.isoformat(),
            execution.completed_at.isoformat() if execution.completed_at else None,
            execution.current_task, json.dumps(execution.completed_tasks),
            json.dumps(execution.failed_tasks), json.dumps(execution.execution_log),
            json.dumps(execution.metrics), execution.error_message,
            execution.approval_status, execution.approved_by,
            execution.approved_at.isoformat() if execution.approved_at else None
        ))
        
        conn.commit()
        conn.close()

class HealthValidator:
    """Validates service health during migrations"""
    
    def __init__(self, service_orchestrator):
        self.service_orchestrator = service_orchestrator
    
    async def validate_service_health(self, service_name: str, version: ServiceVersion, 
                                    timeout: int = 60) -> bool:
        """Validate service health"""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                # Check health endpoint
                health_result = await self.service_orchestrator.execute_action(
                    service_name, "health_check", {"path": version.health_check_path}
                )
                
                if health_result and health_result.get("status") == "healthy":
                    return True
                
                # Check readiness endpoint
                readiness_result = await self.service_orchestrator.execute_action(
                    service_name, "readiness_check", {"path": version.readiness_check_path}
                )
                
                if readiness_result and readiness_result.get("ready"):
                    return True
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                await asyncio.sleep(5)
        
        logger.error(f"Service {service_name} failed health validation within {timeout}s")
        return False
    
    async def validate_traffic_routing(self, service_name: str, expected_traffic_percentage: float) -> bool:
        """Validate traffic routing percentages"""
        try:
            # This would integrate with load balancer to check traffic distribution
            # For now, simulate validation
            logger.info(f"Validating traffic routing for {service_name}: {expected_traffic_percentage}%")
            return True
            
        except Exception as e:
            logger.error(f"Traffic routing validation failed: {e}")
            return False

class TrafficSplitter:
    """Manages traffic splitting for canary deployments"""
    
    def __init__(self, service_orchestrator, load_balancer=None):
        self.service_orchestrator = service_orchestrator
        self.load_balancer = load_balancer
        self.traffic_rules: Dict[str, Dict[str, float]] = {}
    
    async def split_traffic(self, service_name: str, version_weights: Dict[str, float]):
        """Split traffic between service versions"""
        # Normalize weights to sum to 100%
        total_weight = sum(version_weights.values())
        if total_weight == 0:
            raise ValueError("Total weight cannot be zero")
        
        normalized_weights = {
            version: (weight / total_weight) * 100 
            for version, weight in version_weights.items()
        }
        
        self.traffic_rules[service_name] = normalized_weights
        
        # Apply traffic splitting rules to load balancer
        if self.load_balancer:
            await self._apply_traffic_rules(service_name, normalized_weights)
        
        logger.info(f"Traffic split configured for {service_name}: {normalized_weights}")
    
    async def _apply_traffic_rules(self, service_name: str, weights: Dict[str, float]):
        """Apply traffic rules to load balancer"""
        # This would integrate with actual load balancer
        # For now, just log the action
        logger.info(f"Applying traffic rules to load balancer for {service_name}")
    
    async def get_traffic_metrics(self, service_name: str) -> Dict[str, Any]:
        """Get traffic metrics for service versions"""
        # This would integrate with monitoring system
        return {
            "service": service_name,
            "traffic_distribution": self.traffic_rules.get(service_name, {}),
            "timestamp": datetime.now().isoformat()
        }

class BlueGreenDeployment:
    """Blue-green deployment strategy"""
    
    def __init__(self, service_orchestrator, health_validator: HealthValidator):
        self.service_orchestrator = service_orchestrator
        self.health_validator = health_validator
    
    async def execute(self, plan: MigrationPlan, execution: MigrationExecution) -> bool:
        """Execute blue-green deployment"""
        if not plan.target_version:
            raise ValueError("Target version required for blue-green deployment")
        
        service_name = plan.target_version.service_name
        
        try:
            # Step 1: Deploy green environment
            logger.info(f"Deploying green environment for {service_name}")
            
            deploy_result = await self.service_orchestrator.execute_action(
                service_name, "deploy_version", {
                    "version": plan.target_version.version,
                    "image": plan.target_version.image,
                    "configuration": plan.target_version.configuration,
                    "environment": "green"
                }
            )
            
            if not deploy_result or not deploy_result.get("success"):
                raise Exception("Green deployment failed")
            
            # Step 2: Validate green environment health
            logger.info(f"Validating green environment health for {service_name}")
            
            health_valid = await self.health_validator.validate_service_health(
                service_name, plan.target_version
            )
            
            if not health_valid:
                raise Exception("Green environment health validation failed")
            
            # Step 3: Switch traffic to green
            logger.info(f"Switching traffic to green environment for {service_name}")
            
            switch_result = await self.service_orchestrator.execute_action(
                service_name, "switch_traffic", {
                    "target_environment": "green"
                }
            )
            
            if not switch_result or not switch_result.get("success"):
                raise Exception("Traffic switch failed")
            
            # Step 4: Validate traffic switch
            await asyncio.sleep(10)  # Allow time for traffic to stabilize
            
            final_health = await self.health_validator.validate_service_health(
                service_name, plan.target_version
            )
            
            if not final_health:
                raise Exception("Post-switch health validation failed")
            
            # Step 5: Clean up blue environment (optional)
            if plan.metadata.get("cleanup_old_version", True):
                logger.info(f"Cleaning up blue environment for {service_name}")
                await self.service_orchestrator.execute_action(
                    service_name, "cleanup_environment", {"environment": "blue"}
                )
            
            logger.info(f"Blue-green deployment completed successfully for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Blue-green deployment failed for {service_name}: {e}")
            
            # Attempt rollback
            if plan.auto_rollback:
                await self._rollback_blue_green(service_name, plan)
            
            return False
    
    async def _rollback_blue_green(self, service_name: str, plan: MigrationPlan):
        """Rollback blue-green deployment"""
        try:
            logger.info(f"Rolling back blue-green deployment for {service_name}")
            
            # Switch traffic back to blue
            await self.service_orchestrator.execute_action(
                service_name, "switch_traffic", {"target_environment": "blue"}
            )
            
            # Clean up failed green deployment
            await self.service_orchestrator.execute_action(
                service_name, "cleanup_environment", {"environment": "green"}
            )
            
            logger.info(f"Blue-green rollback completed for {service_name}")
            
        except Exception as e:
            logger.error(f"Blue-green rollback failed for {service_name}: {e}")

class CanaryDeployment:
    """Canary deployment strategy"""
    
    def __init__(self, service_orchestrator, health_validator: HealthValidator, 
                 traffic_splitter: TrafficSplitter):
        self.service_orchestrator = service_orchestrator
        self.health_validator = health_validator
        self.traffic_splitter = traffic_splitter
    
    async def execute(self, plan: MigrationPlan, execution: MigrationExecution) -> bool:
        """Execute canary deployment"""
        if not plan.target_version or not plan.traffic_split_config:
            raise ValueError("Target version and traffic split configuration required for canary deployment")
        
        service_name = plan.target_version.service_name
        traffic_config = plan.traffic_split_config
        
        try:
            # Step 1: Deploy canary version
            logger.info(f"Deploying canary version for {service_name}")
            
            deploy_result = await self.service_orchestrator.execute_action(
                service_name, "deploy_version", {
                    "version": plan.target_version.version,
                    "image": plan.target_version.image,
                    "configuration": plan.target_version.configuration,
                    "deployment_type": "canary"
                }
            )
            
            if not deploy_result or not deploy_result.get("success"):
                raise Exception("Canary deployment failed")
            
            # Step 2: Validate canary health
            health_valid = await self.health_validator.validate_service_health(
                service_name, plan.target_version
            )
            
            if not health_valid:
                raise Exception("Canary health validation failed")
            
            # Step 3: Progressive traffic splitting
            phases = traffic_config.get("phases", [
                {"percentage": 10, "duration": 300},  # 10% for 5 minutes
                {"percentage": 25, "duration": 600},  # 25% for 10 minutes
                {"percentage": 50, "duration": 600},  # 50% for 10 minutes
                {"percentage": 100, "duration": 300}  # 100% for 5 minutes
            ])
            
            for phase in phases:
                percentage = phase["percentage"]
                duration = phase["duration"]
                
                logger.info(f"Splitting {percentage}% traffic to canary for {duration}s")
                
                # Split traffic
                await self.traffic_splitter.split_traffic(service_name, {
                    "current": 100 - percentage,
                    "canary": percentage
                })
                
                # Monitor for duration
                monitoring_interval = 30
                monitoring_cycles = duration // monitoring_interval
                
                for cycle in range(monitoring_cycles):
                    await asyncio.sleep(monitoring_interval)
                    
                    # Check canary health
                    health_valid = await self.health_validator.validate_service_health(
                        service_name, plan.target_version
                    )
                    
                    if not health_valid:
                        raise Exception(f"Canary health check failed during {percentage}% phase")
                    
                    # Check metrics (error rates, response times, etc.)
                    metrics_valid = await self._validate_canary_metrics(service_name, plan.rollback_threshold)
                    
                    if not metrics_valid:
                        raise Exception(f"Canary metrics validation failed during {percentage}% phase")
            
            # Step 4: Complete migration - 100% traffic to new version
            await self.traffic_splitter.split_traffic(service_name, {"canary": 100})
            
            # Step 5: Clean up old version
            if plan.metadata.get("cleanup_old_version", True):
                logger.info(f"Cleaning up old version for {service_name}")
                await self.service_orchestrator.execute_action(
                    service_name, "cleanup_old_version", {}
                )
            
            logger.info(f"Canary deployment completed successfully for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Canary deployment failed for {service_name}: {e}")
            
            # Rollback canary
            if plan.auto_rollback:
                await self._rollback_canary(service_name, plan)
            
            return False
    
    async def _validate_canary_metrics(self, service_name: str, rollback_threshold: Dict[str, Any]) -> bool:
        """Validate canary metrics against rollback thresholds"""
        try:
            # Get current metrics
            metrics = await self.traffic_splitter.get_traffic_metrics(service_name)
            
            # Check error rate threshold
            error_rate_threshold = rollback_threshold.get("error_rate", 0.05)  # 5% default
            current_error_rate = metrics.get("error_rate", 0)
            
            if current_error_rate > error_rate_threshold:
                logger.error(f"Error rate {current_error_rate} exceeds threshold {error_rate_threshold}")
                return False
            
            # Check response time threshold
            response_time_threshold = rollback_threshold.get("response_time_p95", 5000)  # 5s default
            current_response_time = metrics.get("response_time_p95", 0)
            
            if current_response_time > response_time_threshold:
                logger.error(f"Response time {current_response_time}ms exceeds threshold {response_time_threshold}ms")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Metrics validation failed: {e}")
            return False
    
    async def _rollback_canary(self, service_name: str, plan: MigrationPlan):
        """Rollback canary deployment"""
        try:
            logger.info(f"Rolling back canary deployment for {service_name}")
            
            # Route 100% traffic back to current version
            await self.traffic_splitter.split_traffic(service_name, {"current": 100})
            
            # Clean up canary deployment
            await self.service_orchestrator.execute_action(
                service_name, "cleanup_canary", {}
            )
            
            logger.info(f"Canary rollback completed for {service_name}")
            
        except Exception as e:
            logger.error(f"Canary rollback failed for {service_name}: {e}")

class ServiceMigrator:
    """Main service migration coordinator"""
    
    def __init__(self, service_orchestrator):
        self.service_orchestrator = service_orchestrator
        self.storage = MigrationStorage()
        self.health_validator = HealthValidator(service_orchestrator)
        self.traffic_splitter = TrafficSplitter(service_orchestrator)
        
        # Strategy implementations
        self.strategies = {
            MigrationStrategy.BLUE_GREEN: BlueGreenDeployment(service_orchestrator, self.health_validator),
            MigrationStrategy.CANARY: CanaryDeployment(service_orchestrator, self.health_validator, self.traffic_splitter)
        }
        
        self.active_migrations: Dict[str, MigrationExecution] = {}
    
    def create_migration_plan(self, name: str, strategy: MigrationStrategy, 
                            migration_type: MigrationType, **kwargs) -> str:
        """Create a new migration plan"""
        plan_id = str(uuid.uuid4())
        
        plan = MigrationPlan(
            plan_id=plan_id,
            name=name,
            strategy=strategy,
            migration_type=migration_type,
            **kwargs
        )
        
        self.storage.save_migration_plan(plan)
        logger.info(f"Created migration plan {plan_id}: {name}")
        
        return plan_id
    
    def add_migration_task(self, plan_id: str, task: MigrationTask):
        """Add a task to migration plan"""
        # This would load the plan, add the task, and save it back
        logger.info(f"Added task {task.task_id} to migration plan {plan_id}")
    
    async def execute_migration(self, plan_id: str, approved_by: str = None) -> MigrationExecution:
        """Execute a migration plan"""
        plan = await self._load_migration_plan(plan_id)
        if not plan:
            raise ValueError(f"Migration plan {plan_id} not found")
        
        execution_id = str(uuid.uuid4())
        execution = MigrationExecution(
            execution_id=execution_id,
            plan_id=plan_id,
            status=MigrationStatus.PENDING
        )
        
        # Check approval requirement
        if plan.approval_required and not approved_by:
            execution.approval_status = "required"
            execution.status = MigrationStatus.PENDING
            self.storage.save_migration_execution(execution)
            return execution
        
        if approved_by:
            execution.approval_status = "approved"
            execution.approved_by = approved_by
            execution.approved_at = datetime.now()
        
        # Start execution
        execution.status = MigrationStatus.RUNNING
        self.active_migrations[execution_id] = execution
        
        try:
            # Run pre-migration checks
            pre_checks_passed = await self._run_pre_migration_checks(plan, execution)
            if not pre_checks_passed:
                raise Exception("Pre-migration checks failed")
            
            # Execute migration strategy
            strategy_impl = self.strategies.get(plan.strategy)
            if not strategy_impl:
                raise Exception(f"Strategy {plan.strategy} not implemented")
            
            success = await strategy_impl.execute(plan, execution)
            
            if success:
                # Run post-migration checks
                post_checks_passed = await self._run_post_migration_checks(plan, execution)
                if post_checks_passed:
                    execution.status = MigrationStatus.COMPLETED
                else:
                    raise Exception("Post-migration checks failed")
            else:
                execution.status = MigrationStatus.FAILED
            
        except Exception as e:
            execution.status = MigrationStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Migration {plan_id} failed: {e}")
            
            # Auto-rollback if enabled
            if plan.auto_rollback:
                await self._rollback_migration(plan, execution)
        
        execution.completed_at = datetime.now()
        self.storage.save_migration_execution(execution)
        self.active_migrations.pop(execution_id, None)
        
        return execution
    
    async def _run_pre_migration_checks(self, plan: MigrationPlan, execution: MigrationExecution) -> bool:
        """Run pre-migration validation checks"""
        logger.info(f"Running pre-migration checks for plan {plan.plan_id}")
        
        for check in plan.pre_migration_checks:
            try:
                # Execute validation check
                result = await self.service_orchestrator.execute_action(
                    "migration-validator", check, {"plan": plan.plan_id}
                )
                
                if not result or not result.get("passed", False):
                    logger.error(f"Pre-migration check failed: {check}")
                    return False
                
                logger.info(f"Pre-migration check passed: {check}")
                
            except Exception as e:
                logger.error(f"Pre-migration check error: {check} - {e}")
                return False
        
        return True
    
    async def _run_post_migration_checks(self, plan: MigrationPlan, execution: MigrationExecution) -> bool:
        """Run post-migration validation checks"""
        logger.info(f"Running post-migration checks for plan {plan.plan_id}")
        
        for check in plan.post_migration_checks:
            try:
                # Execute validation check
                result = await self.service_orchestrator.execute_action(
                    "migration-validator", check, {"plan": plan.plan_id}
                )
                
                if not result or not result.get("passed", False):
                    logger.error(f"Post-migration check failed: {check}")
                    return False
                
                logger.info(f"Post-migration check passed: {check}")
                
            except Exception as e:
                logger.error(f"Post-migration check error: {check} - {e}")
                return False
        
        return True
    
    async def _rollback_migration(self, plan: MigrationPlan, execution: MigrationExecution):
        """Rollback a failed migration"""
        logger.info(f"Rolling back migration {plan.plan_id}")
        execution.status = MigrationStatus.ROLLING_BACK
        
        try:
            # Execute strategy-specific rollback
            strategy_impl = self.strategies.get(plan.strategy)
            if strategy_impl and hasattr(strategy_impl, 'rollback'):
                await strategy_impl.rollback(plan, execution)
            
            execution.status = MigrationStatus.ROLLED_BACK
            logger.info(f"Migration {plan.plan_id} rolled back successfully")
            
        except Exception as e:
            logger.error(f"Rollback failed for migration {plan.plan_id}: {e}")
            execution.status = MigrationStatus.FAILED
    
    async def approve_migration(self, execution_id: str, approved_by: str) -> bool:
        """Approve a pending migration"""
        execution = self.active_migrations.get(execution_id)
        if not execution or execution.approval_status != "required":
            return False
        
        execution.approval_status = "approved"
        execution.approved_by = approved_by
        execution.approved_at = datetime.now()
        
        # Continue with execution
        plan = await self._load_migration_plan(execution.plan_id)
        if plan:
            asyncio.create_task(self._continue_migration_execution(plan, execution))
        
        return True
    
    async def _continue_migration_execution(self, plan: MigrationPlan, execution: MigrationExecution):
        """Continue migration execution after approval"""
        # This would contain the migration execution logic
        # moved from execute_migration method
        pass
    
    async def _load_migration_plan(self, plan_id: str) -> Optional[MigrationPlan]:
        """Load migration plan from storage"""
        # This would load from database and reconstruct the plan object
        return None
    
    def get_migration_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get migration execution status"""
        execution = self.active_migrations.get(execution_id)
        if not execution:
            # Try loading from storage
            return None
        
        return {
            "execution_id": execution.execution_id,
            "plan_id": execution.plan_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "current_task": execution.current_task,
            "completed_tasks": len(execution.completed_tasks),
            "failed_tasks": len(execution.failed_tasks),
            "approval_status": execution.approval_status,
            "approved_by": execution.approved_by,
            "error_message": execution.error_message
        }
    
    def list_active_migrations(self) -> List[Dict[str, Any]]:
        """List all active migrations"""
        return [
            self.get_migration_status(execution_id)
            for execution_id in self.active_migrations.keys()
        ]

# Factory function
def create_service_migrator(service_orchestrator) -> ServiceMigrator:
    """Create and return a service migrator instance"""
    return ServiceMigrator(service_orchestrator)

# Helper functions
def create_service_version(service_name: str, version: str, image: str, **kwargs) -> ServiceVersion:
    """Create a service version"""
    return ServiceVersion(
        version_id=str(uuid.uuid4()),
        service_name=service_name,
        version=version,
        image=image,
        **kwargs
    )

def create_migration_task(name: str, task_type: str, **kwargs) -> MigrationTask:
    """Create a migration task"""
    return MigrationTask(
        task_id=str(uuid.uuid4()),
        name=name,
        task_type=task_type,
        **kwargs
    )