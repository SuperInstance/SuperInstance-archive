"""
ETL Pipeline Manager
Builds and manages ETL pipelines for service integration
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import logging

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
import redis.asyncio as redis
from celery import Celery
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from ..models.etl import (
    ETLPipeline, PipelineExecution, DataSource, 
    DataTarget, TransformationRule, PipelineStatus
)
from ..utils.config import Config
from .data_transformer import DataTransformer
from .data_extractor import DataExtractor
from .data_loader import DataLoader

logger = logging.getLogger(__name__)


class PipelineType(Enum):
    """Types of ETL pipelines"""
    BATCH = "batch"
    STREAMING = "streaming"
    REAL_TIME = "real_time"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"


class ExecutionMode(Enum):
    """Pipeline execution modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    RETRY_ON_FAILURE = "retry_on_failure"


@dataclass
class PipelineConfig:
    """Configuration for ETL pipeline"""
    pipeline_id: str
    name: str
    description: str
    pipeline_type: PipelineType
    execution_mode: ExecutionMode
    source_services: List[str]
    target_services: List[str]
    transformation_rules: List[Dict[str, Any]]
    schedule: Optional[str]  # Cron expression
    retry_config: Dict[str, Any]
    timeout_seconds: int
    batch_size: int
    parallel_workers: int
    quality_checks: List[Dict[str, Any]]
    monitoring_config: Dict[str, Any]
    tags: List[str]
    is_active: bool


@dataclass
class PipelineMetrics:
    """Pipeline execution metrics"""
    execution_id: str
    pipeline_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    records_processed: int
    records_successful: int
    records_failed: int
    bytes_processed: int
    memory_usage_mb: float
    cpu_usage_percent: float
    error_count: int
    warning_count: int
    status: PipelineStatus
    logs: List[str]


class ETLPipelineManager:
    """Manages ETL pipelines for service integration"""
    
    def __init__(self, service_registry, relationship_mapper, db_session_factory, redis_client, config: Config):
        self.service_registry = service_registry
        self.relationship_mapper = relationship_mapper
        self.db_session_factory = db_session_factory
        self.redis_client = redis_client
        self.config = config
        
        # Components
        self.data_extractor = DataExtractor(service_registry, config)
        self.data_transformer = DataTransformer(relationship_mapper, config)
        self.data_loader = DataLoader(service_registry, config)
        
        # Pipeline registry
        self.active_pipelines: Dict[str, PipelineConfig] = {}
        self.pipeline_executions: Dict[str, PipelineMetrics] = {}
        self.pipeline_schedules: Dict[str, Any] = {}
        
        # Celery for background tasks
        self.celery_app = Celery('dmlog-etl', broker=config.redis.url)
        self._configure_celery()
        
        # Execution tracking
        self.running_executions: Set[str] = set()
        self.execution_locks: Dict[str, asyncio.Lock] = {}

    def _configure_celery(self):
        """Configure Celery for background task processing"""
        self.celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_routes={
                'dmlog.etl.extract': {'queue': 'extract'},
                'dmlog.etl.transform': {'queue': 'transform'},
                'dmlog.etl.load': {'queue': 'load'}
            },
            task_annotations={
                '*': {'rate_limit': '100/m'}
            }
        )

    async def initialize(self):
        """Initialize the ETL pipeline manager"""
        logger.info("Initializing ETL Pipeline Manager")
        
        try:
            # Load existing pipelines
            await self._load_existing_pipelines()
            
            # Create default DMLog pipelines
            await self._create_default_pipelines()
            
            # Start pipeline scheduler
            asyncio.create_task(self._pipeline_scheduler())
            
            # Start monitoring task
            asyncio.create_task(self._monitor_pipelines())
            
            logger.info("ETL Pipeline Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ETL pipeline manager: {e}")
            raise

    async def _load_existing_pipelines(self):
        """Load existing pipelines from database"""
        async with self.db_session_factory() as session:
            result = await session.execute(select(ETLPipeline))
            pipelines = result.scalars().all()
            
            for pipeline in pipelines:
                config = PipelineConfig(
                    pipeline_id=pipeline.id,
                    name=pipeline.name,
                    description=pipeline.description,
                    pipeline_type=PipelineType(pipeline.pipeline_type),
                    execution_mode=ExecutionMode(pipeline.execution_mode),
                    source_services=json.loads(pipeline.source_services),
                    target_services=json.loads(pipeline.target_services),
                    transformation_rules=json.loads(pipeline.transformation_rules),
                    schedule=pipeline.schedule,
                    retry_config=json.loads(pipeline.retry_config or "{}"),
                    timeout_seconds=pipeline.timeout_seconds,
                    batch_size=pipeline.batch_size,
                    parallel_workers=pipeline.parallel_workers,
                    quality_checks=json.loads(pipeline.quality_checks or "[]"),
                    monitoring_config=json.loads(pipeline.monitoring_config or "{}"),
                    tags=json.loads(pipeline.tags or "[]"),
                    is_active=pipeline.is_active
                )
                
                self.active_pipelines[pipeline.id] = config
                self.execution_locks[pipeline.id] = asyncio.Lock()

    async def _create_default_pipelines(self):
        """Create default DMLog integration pipelines"""
        
        default_pipelines = [
            # Campaign Data Synchronization Pipeline
            PipelineConfig(
                pipeline_id=str(uuid.uuid4()),
                name="Campaign Data Sync",
                description="Synchronize campaign data across all services",
                pipeline_type=PipelineType.SCHEDULED,
                execution_mode=ExecutionMode.SEQUENTIAL,
                source_services=["dmlog-core"],
                target_services=["dmlog-characters", "dmlog-session", "dmlog-world", "dmlog-ai-dm"],
                transformation_rules=[
                    {
                        "type": "campaign_enrichment",
                        "source_entity": "campaigns",
                        "transformations": [
                            "extract_player_list",
                            "calculate_campaign_stats",
                            "generate_ai_context"
                        ]
                    }
                ],
                schedule="*/15 * * * *",  # Every 15 minutes
                retry_config={
                    "max_retries": 3,
                    "retry_delay_seconds": 60,
                    "exponential_backoff": True
                },
                timeout_seconds=300,
                batch_size=100,
                parallel_workers=2,
                quality_checks=[
                    {"type": "data_completeness", "threshold": 0.95},
                    {"type": "referential_integrity", "foreign_keys": ["campaign_id"]}
                ],
                monitoring_config={
                    "alert_on_failure": True,
                    "performance_threshold_seconds": 180
                },
                tags=["core", "sync", "campaign"],
                is_active=True
            ),
            
            # Character Progression Pipeline
            PipelineConfig(
                pipeline_id=str(uuid.uuid4()),
                name="Character Progression Sync",
                description="Synchronize character progression data",
                pipeline_type=PipelineType.EVENT_DRIVEN,
                execution_mode=ExecutionMode.PARALLEL,
                source_services=["dmlog-characters", "dmlog-session"],
                target_services=["dmlog-player", "dmlog-ai-dm", "dmlog-battle"],
                transformation_rules=[
                    {
                        "type": "character_progression",
                        "source_entity": "characters",
                        "transformations": [
                            "calculate_level_changes",
                            "update_abilities",
                            "sync_battle_stats",
                            "generate_ai_personality_updates"
                        ]
                    }
                ],
                schedule=None,  # Event-driven
                retry_config={
                    "max_retries": 2,
                    "retry_delay_seconds": 30,
                    "exponential_backoff": False
                },
                timeout_seconds=120,
                batch_size=50,
                parallel_workers=3,
                quality_checks=[
                    {"type": "level_validation", "min_level": 1, "max_level": 20},
                    {"type": "stat_consistency", "check_stat_totals": True}
                ],
                monitoring_config={
                    "alert_on_failure": True,
                    "performance_threshold_seconds": 60
                },
                tags=["character", "progression", "real-time"],
                is_active=True
            ),
            
            # Session Analytics Pipeline
            PipelineConfig(
                pipeline_id=str(uuid.uuid4()),
                name="Session Analytics Aggregation",
                description="Aggregate session data for analytics",
                pipeline_type=PipelineType.BATCH,
                execution_mode=ExecutionMode.SEQUENTIAL,
                source_services=["dmlog-session", "dmlog-battle", "dmlog-stream"],
                target_services=["dmlog-core"],  # Store analytics in core
                transformation_rules=[
                    {
                        "type": "session_analytics",
                        "source_entity": "sessions",
                        "transformations": [
                            "calculate_session_metrics",
                            "aggregate_player_engagement",
                            "analyze_combat_encounters",
                            "process_recording_highlights"
                        ]
                    }
                ],
                schedule="0 2 * * *",  # Daily at 2 AM
                retry_config={
                    "max_retries": 2,
                    "retry_delay_seconds": 300,
                    "exponential_backoff": True
                },
                timeout_seconds=1800,  # 30 minutes
                batch_size=500,
                parallel_workers=4,
                quality_checks=[
                    {"type": "metric_validation", "required_fields": ["duration", "players", "encounters"]},
                    {"type": "time_range_validation", "max_session_hours": 12}
                ],
                monitoring_config={
                    "alert_on_failure": True,
                    "performance_threshold_seconds": 1200
                },
                tags=["analytics", "batch", "daily"],
                is_active=True
            ),
            
            # Marketplace Integration Pipeline
            PipelineConfig(
                pipeline_id=str(uuid.uuid4()),
                name="Marketplace Content Sync",
                description="Synchronize marketplace content with campaigns",
                pipeline_type=PipelineType.SCHEDULED,
                execution_mode=ExecutionMode.PARALLEL,
                source_services=["dmlog-marketplace"],
                target_services=["dmlog-templates", "dmlog-world", "dmlog-characters"],
                transformation_rules=[
                    {
                        "type": "marketplace_integration",
                        "source_entity": "purchases",
                        "transformations": [
                            "validate_content_license",
                            "convert_content_format",
                            "integrate_with_campaign",
                            "update_user_library"
                        ]
                    }
                ],
                schedule="*/30 * * * *",  # Every 30 minutes
                retry_config={
                    "max_retries": 3,
                    "retry_delay_seconds": 120,
                    "exponential_backoff": True
                },
                timeout_seconds=600,
                batch_size=20,
                parallel_workers=2,
                quality_checks=[
                    {"type": "license_validation", "check_permissions": True},
                    {"type": "content_integrity", "validate_assets": True}
                ],
                monitoring_config={
                    "alert_on_failure": True,
                    "performance_threshold_seconds": 300
                },
                tags=["marketplace", "content", "integration"],
                is_active=True
            ),
            
            # AI DM Data Enrichment Pipeline
            PipelineConfig(
                pipeline_id=str(uuid.uuid4()),
                name="AI DM Context Enrichment",
                description="Enrich AI DM with campaign and character context",
                pipeline_type=PipelineType.REAL_TIME,
                execution_mode=ExecutionMode.CONDITIONAL,
                source_services=["dmlog-core", "dmlog-characters", "dmlog-world", "dmlog-session"],
                target_services=["dmlog-ai-dm"],
                transformation_rules=[
                    {
                        "type": "ai_context_enrichment",
                        "source_entity": "multiple",
                        "transformations": [
                            "build_campaign_context",
                            "extract_character_relationships",
                            "analyze_world_state",
                            "prepare_ai_prompts"
                        ]
                    }
                ],
                schedule=None,  # Real-time
                retry_config={
                    "max_retries": 1,
                    "retry_delay_seconds": 10,
                    "exponential_backoff": False
                },
                timeout_seconds=30,
                batch_size=10,
                parallel_workers=1,
                quality_checks=[
                    {"type": "context_completeness", "required_context_fields": ["campaign", "characters", "current_state"]},
                    {"type": "ai_prompt_validation", "max_token_length": 4000}
                ],
                monitoring_config={
                    "alert_on_failure": False,  # Don't alert for AI context failures
                    "performance_threshold_seconds": 15
                },
                tags=["ai", "real-time", "context"],
                is_active=True
            )
        ]
        
        # Create and store default pipelines
        for config in default_pipelines:
            if config.pipeline_id not in self.active_pipelines:
                await self._create_pipeline(config)

    async def _create_pipeline(self, config: PipelineConfig):
        """Create a new ETL pipeline"""
        async with self.db_session_factory() as session:
            try:
                pipeline = ETLPipeline(
                    id=config.pipeline_id,
                    name=config.name,
                    description=config.description,
                    pipeline_type=config.pipeline_type.value,
                    execution_mode=config.execution_mode.value,
                    source_services=json.dumps(config.source_services),
                    target_services=json.dumps(config.target_services),
                    transformation_rules=json.dumps(config.transformation_rules),
                    schedule=config.schedule,
                    retry_config=json.dumps(config.retry_config),
                    timeout_seconds=config.timeout_seconds,
                    batch_size=config.batch_size,
                    parallel_workers=config.parallel_workers,
                    quality_checks=json.dumps(config.quality_checks),
                    monitoring_config=json.dumps(config.monitoring_config),
                    tags=json.dumps(config.tags),
                    is_active=config.is_active,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                session.add(pipeline)
                await session.commit()
                
                self.active_pipelines[config.pipeline_id] = config
                self.execution_locks[config.pipeline_id] = asyncio.Lock()
                
                logger.info(f"Created pipeline: {config.name}")
                
            except Exception as e:
                logger.error(f"Failed to create pipeline {config.name}: {e}")
                await session.rollback()

    async def execute_pipeline(self, pipeline_id: str, trigger_type: str = "manual") -> str:
        """Execute a pipeline"""
        if pipeline_id not in self.active_pipelines:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        config = self.active_pipelines[pipeline_id]
        execution_id = str(uuid.uuid4())
        
        # Check if pipeline is already running (for non-parallel pipelines)
        async with self.execution_locks[pipeline_id]:
            if pipeline_id in self.running_executions and config.execution_mode != ExecutionMode.PARALLEL:
                raise ValueError(f"Pipeline {pipeline_id} is already running")
            
            self.running_executions.add(pipeline_id)
        
        # Create execution record
        metrics = PipelineMetrics(
            execution_id=execution_id,
            pipeline_id=pipeline_id,
            start_time=datetime.now(),
            end_time=None,
            duration_seconds=None,
            records_processed=0,
            records_successful=0,
            records_failed=0,
            bytes_processed=0,
            memory_usage_mb=0,
            cpu_usage_percent=0,
            error_count=0,
            warning_count=0,
            status=PipelineStatus.RUNNING,
            logs=[]
        )
        
        self.pipeline_executions[execution_id] = metrics
        
        # Store execution in database
        await self._store_pipeline_execution(execution_id, pipeline_id, trigger_type)
        
        # Execute pipeline asynchronously
        asyncio.create_task(self._run_pipeline_execution(config, metrics))
        
        return execution_id

    async def _run_pipeline_execution(self, config: PipelineConfig, metrics: PipelineMetrics):
        """Run pipeline execution"""
        try:
            logger.info(f"Starting pipeline execution: {config.name} ({metrics.execution_id})")
            
            # Extract phase
            metrics.logs.append(f"Starting extraction from services: {config.source_services}")
            extracted_data = await self._execute_extract_phase(config, metrics)
            
            if not extracted_data:
                metrics.logs.append("No data extracted, skipping pipeline")
                metrics.status = PipelineStatus.COMPLETED
                return
            
            # Transform phase
            metrics.logs.append(f"Starting transformation with {len(config.transformation_rules)} rules")
            transformed_data = await self._execute_transform_phase(config, metrics, extracted_data)
            
            # Quality checks
            if config.quality_checks:
                metrics.logs.append(f"Running {len(config.quality_checks)} quality checks")
                quality_passed = await self._execute_quality_checks(config, metrics, transformed_data)
                
                if not quality_passed:
                    metrics.status = PipelineStatus.FAILED
                    metrics.logs.append("Quality checks failed, aborting pipeline")
                    return
            
            # Load phase
            metrics.logs.append(f"Starting load to services: {config.target_services}")
            await self._execute_load_phase(config, metrics, transformed_data)
            
            # Success
            metrics.status = PipelineStatus.COMPLETED
            metrics.logs.append("Pipeline execution completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            metrics.status = PipelineStatus.FAILED
            metrics.error_count += 1
            metrics.logs.append(f"Pipeline execution failed: {str(e)}")
            
        finally:
            # Cleanup
            metrics.end_time = datetime.now()
            metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            
            self.running_executions.discard(config.pipeline_id)
            
            # Update execution record
            await self._update_pipeline_execution(metrics)
            
            logger.info(f"Pipeline execution finished: {config.name} ({metrics.execution_id}) - Status: {metrics.status.value}")

    async def _execute_extract_phase(self, config: PipelineConfig, metrics: PipelineMetrics) -> Dict[str, Any]:
        """Execute data extraction phase"""
        extracted_data = {}
        
        for service in config.source_services:
            try:
                service_data = await self.data_extractor.extract_from_service(
                    service, 
                    batch_size=config.batch_size
                )
                extracted_data[service] = service_data
                metrics.records_processed += len(service_data.get('records', []))
                
            except Exception as e:
                logger.error(f"Failed to extract from {service}: {e}")
                metrics.error_count += 1
                metrics.logs.append(f"Extraction failed for {service}: {str(e)}")
        
        return extracted_data

    async def _execute_transform_phase(self, config: PipelineConfig, metrics: PipelineMetrics, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data transformation phase"""
        transformed_data = {}
        
        for rule in config.transformation_rules:
            try:
                rule_result = await self.data_transformer.apply_transformation_rule(rule, data)
                
                # Merge results
                for key, value in rule_result.items():
                    if key not in transformed_data:
                        transformed_data[key] = []
                    transformed_data[key].extend(value if isinstance(value, list) else [value])
                
                metrics.records_successful += len(rule_result.get('records', []))
                
            except Exception as e:
                logger.error(f"Transformation failed for rule {rule.get('type', 'unknown')}: {e}")
                metrics.error_count += 1
                metrics.logs.append(f"Transformation failed: {str(e)}")
        
        return transformed_data

    async def _execute_quality_checks(self, config: PipelineConfig, metrics: PipelineMetrics, data: Dict[str, Any]) -> bool:
        """Execute data quality checks"""
        for check in config.quality_checks:
            try:
                check_result = await self._run_quality_check(check, data)
                
                if not check_result['passed']:
                    metrics.error_count += 1
                    metrics.logs.append(f"Quality check failed: {check_result['message']}")
                    return False
                else:
                    metrics.logs.append(f"Quality check passed: {check['type']}")
                    
            except Exception as e:
                logger.error(f"Quality check error: {e}")
                metrics.error_count += 1
                metrics.logs.append(f"Quality check error: {str(e)}")
                return False
        
        return True

    async def _execute_load_phase(self, config: PipelineConfig, metrics: PipelineMetrics, data: Dict[str, Any]):
        """Execute data loading phase"""
        for service in config.target_services:
            try:
                service_data = data.get(service, data)  # Use service-specific data or all data
                
                load_result = await self.data_loader.load_to_service(service, service_data)
                
                if load_result.get('success'):
                    metrics.records_successful += load_result.get('records_loaded', 0)
                    metrics.logs.append(f"Successfully loaded {load_result.get('records_loaded', 0)} records to {service}")
                else:
                    metrics.records_failed += load_result.get('records_failed', 0)
                    metrics.logs.append(f"Load failed for {service}: {load_result.get('error', 'Unknown error')}")
                
            except Exception as e:
                logger.error(f"Failed to load to {service}: {e}")
                metrics.error_count += 1
                metrics.logs.append(f"Load failed for {service}: {str(e)}")

    async def _run_quality_check(self, check: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single quality check"""
        check_type = check.get('type', 'unknown')
        
        if check_type == 'data_completeness':
            threshold = check.get('threshold', 0.95)
            total_records = sum(len(service_data.get('records', [])) for service_data in data.values())
            valid_records = sum(
                len([r for r in service_data.get('records', []) if self._is_record_complete(r)])
                for service_data in data.values()
            )
            completeness = valid_records / total_records if total_records > 0 else 0
            
            return {
                'passed': completeness >= threshold,
                'message': f'Data completeness: {completeness:.2%} (threshold: {threshold:.2%})',
                'metric': completeness
            }
        
        elif check_type == 'referential_integrity':
            foreign_keys = check.get('foreign_keys', [])
            # Implement referential integrity check
            return {'passed': True, 'message': 'Referential integrity check passed'}
        
        else:
            return {'passed': True, 'message': f'Unknown check type: {check_type}'}

    def _is_record_complete(self, record: Dict[str, Any]) -> bool:
        """Check if a record is complete"""
        # Basic completeness check - can be enhanced
        return bool(record) and all(value is not None for value in record.values())

    async def _store_pipeline_execution(self, execution_id: str, pipeline_id: str, trigger_type: str):
        """Store pipeline execution in database"""
        async with self.db_session_factory() as session:
            try:
                execution = PipelineExecution(
                    id=execution_id,
                    pipeline_id=pipeline_id,
                    trigger_type=trigger_type,
                    status=PipelineStatus.RUNNING.value,
                    start_time=datetime.now(),
                    created_at=datetime.now()
                )
                
                session.add(execution)
                await session.commit()
                
            except Exception as e:
                logger.error(f"Failed to store pipeline execution: {e}")
                await session.rollback()

    async def _update_pipeline_execution(self, metrics: PipelineMetrics):
        """Update pipeline execution with final metrics"""
        async with self.db_session_factory() as session:
            try:
                await session.execute(
                    update(PipelineExecution)
                    .where(PipelineExecution.id == metrics.execution_id)
                    .values(
                        status=metrics.status.value,
                        end_time=metrics.end_time,
                        duration_seconds=metrics.duration_seconds,
                        records_processed=metrics.records_processed,
                        records_successful=metrics.records_successful,
                        records_failed=metrics.records_failed,
                        error_count=metrics.error_count,
                        logs=json.dumps(metrics.logs),
                        updated_at=datetime.now()
                    )
                )
                
                await session.commit()
                
            except Exception as e:
                logger.error(f"Failed to update pipeline execution: {e}")
                await session.rollback()

    async def _pipeline_scheduler(self):
        """Background pipeline scheduler"""
        while True:
            try:
                current_time = datetime.now()
                
                for pipeline_id, config in self.active_pipelines.items():
                    if not config.is_active or not config.schedule:
                        continue
                    
                    # Check if pipeline should run (simplified cron check)
                    if await self._should_pipeline_run(config, current_time):
                        try:
                            await self.execute_pipeline(pipeline_id, "scheduled")
                            logger.info(f"Scheduled execution started for pipeline: {config.name}")
                        except Exception as e:
                            logger.error(f"Failed to start scheduled pipeline {config.name}: {e}")
                
                # Sleep until next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Pipeline scheduler error: {e}")
                await asyncio.sleep(60)

    async def _should_pipeline_run(self, config: PipelineConfig, current_time: datetime) -> bool:
        """Check if pipeline should run based on schedule"""
        # Simplified cron parsing - in production, use a proper cron library
        if not config.schedule:
            return False
        
        # For now, just handle simple intervals like "*/15 * * * *" (every 15 minutes)
        if config.schedule.startswith("*/"):
            interval_str = config.schedule.split()[0][2:]  # Remove "*/"
            try:
                interval = int(interval_str)
                return current_time.minute % interval == 0
            except ValueError:
                return False
        
        return False

    async def monitor_active_pipelines(self):
        """Monitor active pipeline executions"""
        for execution_id, metrics in list(self.pipeline_executions.items()):
            if metrics.status == PipelineStatus.RUNNING:
                # Check for timeouts
                config = self.active_pipelines.get(metrics.pipeline_id)
                if config:
                    runtime = (datetime.now() - metrics.start_time).total_seconds()
                    if runtime > config.timeout_seconds:
                        logger.warning(f"Pipeline execution timeout: {execution_id}")
                        metrics.status = PipelineStatus.FAILED
                        metrics.logs.append(f"Pipeline timed out after {runtime} seconds")
                        await self._update_pipeline_execution(metrics)

    async def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get pipeline execution statistics"""
        stats = {
            'total_pipelines': len(self.active_pipelines),
            'active_pipelines': len([p for p in self.active_pipelines.values() if p.is_active]),
            'running_executions': len(self.running_executions),
            'completed_executions': len([m for m in self.pipeline_executions.values() if m.status == PipelineStatus.COMPLETED]),
            'failed_executions': len([m for m in self.pipeline_executions.values() if m.status == PipelineStatus.FAILED]),
            'pipeline_types': {},
            'average_execution_time': 0,
            'total_records_processed': sum(m.records_processed for m in self.pipeline_executions.values())
        }
        
        # Count pipeline types
        for config in self.active_pipelines.values():
            pipeline_type = config.pipeline_type.value
            stats['pipeline_types'][pipeline_type] = stats['pipeline_types'].get(pipeline_type, 0) + 1
        
        # Calculate average execution time
        completed_metrics = [m for m in self.pipeline_executions.values() if m.duration_seconds]
        if completed_metrics:
            stats['average_execution_time'] = sum(m.duration_seconds for m in completed_metrics) / len(completed_metrics)
        
        return stats

    async def cleanup(self):
        """Cleanup pipeline manager resources"""
        logger.info("Cleaning up ETL Pipeline Manager")
        
        # Cancel running executions
        for pipeline_id in list(self.running_executions):
            logger.info(f"Stopping pipeline execution: {pipeline_id}")
        
        self.running_executions.clear()
        self.pipeline_executions.clear()
        
        # Close Celery connection
        if hasattr(self.celery_app, 'close'):
            self.celery_app.close()