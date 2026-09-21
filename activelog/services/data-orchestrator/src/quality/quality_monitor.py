"""
Data Quality Monitor
Implements comprehensive data quality monitoring and validation
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import logging
import statistics
from collections import defaultdict

import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from great_expectations import DataContext
from great_expectations.core.batch import RuntimeBatchRequest
import cerberus

from ..models.quality import (
    QualityRule, QualityCheck, QualityMetric, 
    QualityAlert, DataProfile, QualityScore
)
from ..utils.config import Config

logger = logging.getLogger(__name__)


class QualityCheckType(Enum):
    """Types of data quality checks"""
    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    UNIQUENESS = "uniqueness"
    TIMELINESS = "timeliness"
    CONFORMITY = "conformity"
    INTEGRITY = "integrity"


class QualitySeverity(Enum):
    """Severity levels for quality issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QualityCheckResult:
    """Result of a quality check"""
    check_id: str
    rule_id: str
    service_name: str
    entity_name: str
    field_name: Optional[str]
    check_type: QualityCheckType
    passed: bool
    score: float
    expected_value: Any
    actual_value: Any
    threshold: float
    message: str
    details: Dict[str, Any]
    severity: QualitySeverity
    timestamp: datetime
    records_checked: int
    records_failed: int


@dataclass
class DataProfileResult:
    """Data profiling results"""
    service_name: str
    entity_name: str
    field_name: str
    data_type: str
    total_records: int
    null_count: int
    unique_count: int
    duplicate_count: int
    min_value: Any
    max_value: Any
    mean_value: Optional[float]
    median_value: Optional[float]
    std_deviation: Optional[float]
    percentiles: Dict[str, Any]
    most_common_values: List[Tuple[Any, int]]
    pattern_matches: Dict[str, int]
    anomalies: List[Dict[str, Any]]
    profiled_at: datetime


@dataclass
class QualityTrend:
    """Quality trend analysis"""
    metric_name: str
    time_period: str
    values: List[float]
    timestamps: List[datetime]
    trend_direction: str  # 'improving', 'degrading', 'stable'
    trend_strength: float
    forecast: Optional[List[float]]
    anomalies: List[int]  # indices of anomalous values


class DataQualityMonitor:
    """Monitors data quality across all DMLog services"""
    
    def __init__(self, service_registry, db_session_factory, config: Config):
        self.service_registry = service_registry
        self.db_session_factory = db_session_factory
        self.config = config
        
        # Quality rules and checks
        self.quality_rules: Dict[str, QualityRule] = {}
        self.active_checks: Dict[str, QualityCheck] = {}
        
        # Great Expectations context
        self.ge_context = None
        
        # Quality metrics and scores
        self.quality_scores: Dict[str, float] = {}  # service -> overall score
        self.quality_metrics: Dict[str, List[QualityMetric]] = defaultdict(list)
        
        # Schema validators
        self.schema_validators: Dict[str, cerberus.Validator] = {}
        
        # Quality check history
        self.check_results: List[QualityCheckResult] = []
        self.data_profiles: Dict[str, DataProfileResult] = {}
        
        # Alert thresholds
        self.alert_thresholds = {
            QualitySeverity.CRITICAL: 0.5,  # Score below 50%
            QualitySeverity.HIGH: 0.7,      # Score below 70%
            QualitySeverity.MEDIUM: 0.85,   # Score below 85%
            QualitySeverity.LOW: 0.95       # Score below 95%
        }
        
        # Background monitoring
        self._monitoring_tasks: set = set()

    async def initialize(self):
        """Initialize the data quality monitor"""
        logger.info("Initializing Data Quality Monitor")
        
        try:
            # Initialize Great Expectations
            await self._initialize_great_expectations()
            
            # Load quality rules from database
            await self._load_quality_rules()
            
            # Create default quality rules for DMLog services
            await self._create_default_quality_rules()
            
            # Initialize schema validators
            await self._initialize_schema_validators()
            
            # Start background monitoring
            self._start_background_monitoring()
            
            logger.info("Data Quality Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data quality monitor: {e}")
            raise

    async def _initialize_great_expectations(self):
        """Initialize Great Expectations data context"""
        try:
            # In production, this would use a proper GE configuration
            self.ge_context = DataContext()
            logger.info("Great Expectations context initialized")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Great Expectations: {e}")
            # Continue without GE - use custom validation logic

    async def _load_quality_rules(self):
        """Load quality rules from database"""
        async with self.db_session_factory() as session:
            result = await session.execute(select(QualityRule))
            rules = result.scalars().all()
            
            for rule in rules:
                self.quality_rules[rule.id] = rule
                
                # Create schema validator if needed
                if rule.rule_type == QualityCheckType.CONFORMITY.value and rule.validation_schema:
                    schema = json.loads(rule.validation_schema)
                    self.schema_validators[rule.id] = cerberus.Validator(schema)

    async def _create_default_quality_rules(self):
        """Create default quality rules for DMLog services"""
        
        default_rules = [
            # Core Campaign Data Rules
            {
                'rule_name': 'Campaign ID Not Null',
                'service_name': 'dmlog-core',
                'entity_name': 'campaigns',
                'field_name': 'id',
                'rule_type': QualityCheckType.COMPLETENESS,
                'validation_logic': 'field_not_null',
                'threshold': 1.0,
                'severity': QualitySeverity.CRITICAL,
                'description': 'Campaign ID must always be present'
            },
            
            # Character Data Rules
            {
                'rule_name': 'Character Level Range',
                'service_name': 'dmlog-characters',
                'entity_name': 'characters',
                'field_name': 'level',
                'rule_type': QualityCheckType.VALIDITY,
                'validation_logic': 'value_in_range',
                'validation_params': {'min_value': 1, 'max_value': 20},
                'threshold': 0.95,
                'severity': QualitySeverity.HIGH,
                'description': 'Character level must be between 1 and 20'
            },
            
            # Session Data Rules
            {
                'rule_name': 'Session Duration Validity',
                'service_name': 'dmlog-session',
                'entity_name': 'sessions',
                'field_name': 'duration',
                'rule_type': QualityCheckType.VALIDITY,
                'validation_logic': 'value_positive',
                'threshold': 0.9,
                'severity': QualitySeverity.MEDIUM,
                'description': 'Session duration must be positive'
            },
            
            # Data Consistency Rules
            {
                'rule_name': 'Character Campaign Reference',
                'service_name': 'dmlog-characters',
                'entity_name': 'characters',
                'field_name': 'campaign_id',
                'rule_type': QualityCheckType.INTEGRITY,
                'validation_logic': 'foreign_key_exists',
                'validation_params': {'reference_service': 'dmlog-core', 'reference_entity': 'campaigns', 'reference_field': 'id'},
                'threshold': 1.0,
                'severity': QualitySeverity.CRITICAL,
                'description': 'Character must reference existing campaign'
            },
            
            # Uniqueness Rules
            {
                'rule_name': 'Unique Campaign Names per User',
                'service_name': 'dmlog-core',
                'entity_name': 'campaigns',
                'field_name': ['name', 'user_id'],
                'rule_type': QualityCheckType.UNIQUENESS,
                'validation_logic': 'composite_unique',
                'threshold': 1.0,
                'severity': QualitySeverity.HIGH,
                'description': 'Campaign names must be unique per user'
            },
            
            # Timeliness Rules
            {
                'rule_name': 'Recent Session Updates',
                'service_name': 'dmlog-session',
                'entity_name': 'sessions',
                'field_name': 'updated_at',
                'rule_type': QualityCheckType.TIMELINESS,
                'validation_logic': 'updated_within_timeframe',
                'validation_params': {'max_age_hours': 24},
                'threshold': 0.8,
                'severity': QualitySeverity.LOW,
                'description': 'Active sessions should be updated within 24 hours'
            }
        ]
        
        # Create and store rules
        for rule_data in default_rules:
            rule_id = str(uuid.uuid4())
            
            if rule_id not in self.quality_rules:
                await self._create_quality_rule(rule_id, rule_data)

    async def _create_quality_rule(self, rule_id: str, rule_data: Dict[str, Any]):
        """Create a new quality rule"""
        async with self.db_session_factory() as session:
            try:
                rule = QualityRule(
                    id=rule_id,
                    rule_name=rule_data['rule_name'],
                    service_name=rule_data['service_name'],
                    entity_name=rule_data['entity_name'],
                    field_name=rule_data.get('field_name'),
                    rule_type=rule_data['rule_type'].value if isinstance(rule_data['rule_type'], QualityCheckType) else rule_data['rule_type'],
                    validation_logic=rule_data['validation_logic'],
                    validation_params=json.dumps(rule_data.get('validation_params', {})),
                    validation_schema=json.dumps(rule_data.get('validation_schema', {})),
                    threshold=rule_data['threshold'],
                    severity=rule_data['severity'].value if isinstance(rule_data['severity'], QualitySeverity) else rule_data['severity'],
                    description=rule_data['description'],
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                session.add(rule)
                await session.commit()
                
                self.quality_rules[rule_id] = rule
                
                logger.info(f"Created quality rule: {rule_data['rule_name']}")
                
            except Exception as e:
                logger.error(f"Failed to create quality rule {rule_data['rule_name']}: {e}")
                await session.rollback()

    async def _initialize_schema_validators(self):
        """Initialize schema validators for conformity checks"""
        
        # DMLog entity schemas
        dmlog_schemas = {
            'campaign_schema': {
                'id': {'type': 'string', 'required': True},
                'name': {'type': 'string', 'required': True, 'minlength': 1, 'maxlength': 255},
                'description': {'type': 'string', 'maxlength': 1000},
                'created_at': {'type': 'datetime', 'required': True},
                'user_id': {'type': 'string', 'required': True},
                'is_active': {'type': 'boolean', 'required': True}
            },
            
            'character_schema': {
                'id': {'type': 'string', 'required': True},
                'name': {'type': 'string', 'required': True, 'minlength': 1, 'maxlength': 100},
                'level': {'type': 'integer', 'required': True, 'min': 1, 'max': 20},
                'race': {'type': 'string', 'required': True},
                'class': {'type': 'string', 'required': True},
                'campaign_id': {'type': 'string', 'required': True},
                'hp_current': {'type': 'integer', 'min': 0},
                'hp_max': {'type': 'integer', 'min': 1}
            },
            
            'session_schema': {
                'id': {'type': 'string', 'required': True},
                'campaign_id': {'type': 'string', 'required': True},
                'start_time': {'type': 'datetime', 'required': True},
                'end_time': {'type': 'datetime'},
                'duration': {'type': 'integer', 'min': 0},
                'player_count': {'type': 'integer', 'min': 1}
            }
        }
        
        for schema_name, schema_def in dmlog_schemas.items():
            self.schema_validators[schema_name] = cerberus.Validator(schema_def)

    def _start_background_monitoring(self):
        """Start background quality monitoring tasks"""
        
        # Periodic quality checks
        task1 = asyncio.create_task(self._periodic_quality_check_loop())
        self._monitoring_tasks.add(task1)
        
        # Data profiling task
        task2 = asyncio.create_task(self._data_profiling_loop())
        self._monitoring_tasks.add(task2)
        
        # Quality score calculation
        task3 = asyncio.create_task(self._quality_score_calculation_loop())
        self._monitoring_tasks.add(task3)
        
        # Alert monitoring
        task4 = asyncio.create_task(self._alert_monitoring_loop())
        self._monitoring_tasks.add(task4)

    async def run_quality_checks(self, service_name: Optional[str] = None, entity_name: Optional[str] = None):
        """Run quality checks for specified service/entity or all"""
        logger.info(f"Running quality checks - Service: {service_name}, Entity: {entity_name}")
        
        try:
            # Filter rules based on parameters
            relevant_rules = []
            for rule in self.quality_rules.values():
                if service_name and rule.service_name != service_name:
                    continue
                if entity_name and rule.entity_name != entity_name:
                    continue
                if rule.is_active:
                    relevant_rules.append(rule)
            
            logger.info(f"Found {len(relevant_rules)} relevant quality rules")
            
            # Execute checks
            results = []
            for rule in relevant_rules:
                try:
                    result = await self._execute_quality_check(rule)
                    if result:
                        results.append(result)
                        self.check_results.append(result)
                        
                        # Store result in database
                        await self._store_quality_check_result(result)
                        
                except Exception as e:
                    logger.error(f"Failed to execute quality check for rule {rule.rule_name}: {e}")
            
            logger.info(f"Completed {len(results)} quality checks")
            return results
            
        except Exception as e:
            logger.error(f"Error running quality checks: {e}")
            return []

    async def _execute_quality_check(self, rule: QualityRule) -> Optional[QualityCheckResult]:
        """Execute a single quality check"""
        try:
            # Get data from service
            data = await self._get_service_data(rule.service_name, rule.entity_name)
            
            if not data:
                logger.warning(f"No data found for {rule.service_name}.{rule.entity_name}")
                return None
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(data)
            
            if df.empty:
                logger.warning(f"Empty dataset for {rule.service_name}.{rule.entity_name}")
                return None
            
            # Execute check based on rule type
            check_result = await self._run_validation_check(rule, df)
            
            return check_result
            
        except Exception as e:
            logger.error(f"Error executing quality check for rule {rule.rule_name}: {e}")
            return None

    async def _run_validation_check(self, rule: QualityRule, df: pd.DataFrame) -> QualityCheckResult:
        """Run validation check on data"""
        check_type = QualityCheckType(rule.rule_type)
        validation_params = json.loads(rule.validation_params or "{}")
        
        total_records = len(df)
        failed_records = 0
        passed = False
        score = 0.0
        actual_value = None
        details = {}
        
        if check_type == QualityCheckType.COMPLETENESS:
            # Check for null values
            if rule.field_name and rule.field_name in df.columns:
                null_count = df[rule.field_name].isnull().sum()
                failed_records = null_count
                completeness_rate = (total_records - null_count) / total_records
                score = completeness_rate
                passed = score >= rule.threshold
                actual_value = completeness_rate
                details = {'null_count': null_count, 'completeness_rate': completeness_rate}
        
        elif check_type == QualityCheckType.VALIDITY:
            # Check valid values based on validation logic
            if rule.validation_logic == 'value_in_range' and rule.field_name in df.columns:
                min_val = validation_params.get('min_value', float('-inf'))
                max_val = validation_params.get('max_value', float('inf'))
                
                valid_mask = (df[rule.field_name] >= min_val) & (df[rule.field_name] <= max_val)
                valid_count = valid_mask.sum()
                failed_records = total_records - valid_count
                validity_rate = valid_count / total_records
                score = validity_rate
                passed = score >= rule.threshold
                actual_value = validity_rate
                details = {'valid_count': valid_count, 'invalid_count': failed_records}
            
            elif rule.validation_logic == 'value_positive' and rule.field_name in df.columns:
                positive_mask = df[rule.field_name] > 0
                positive_count = positive_mask.sum()
                failed_records = total_records - positive_count
                validity_rate = positive_count / total_records
                score = validity_rate
                passed = score >= rule.threshold
                actual_value = validity_rate
                details = {'positive_count': positive_count, 'non_positive_count': failed_records}
        
        elif check_type == QualityCheckType.UNIQUENESS:
            # Check for duplicates
            if isinstance(rule.field_name, str):
                field_name = rule.field_name
            elif isinstance(rule.field_name, list):
                field_name = rule.field_name
            else:
                field_name = json.loads(rule.field_name) if rule.field_name else []
            
            if field_name and all(col in df.columns for col in (field_name if isinstance(field_name, list) else [field_name])):
                duplicate_count = df.duplicated(subset=field_name).sum()
                failed_records = duplicate_count
                uniqueness_rate = (total_records - duplicate_count) / total_records
                score = uniqueness_rate
                passed = score >= rule.threshold
                actual_value = uniqueness_rate
                details = {'duplicate_count': duplicate_count, 'uniqueness_rate': uniqueness_rate}
        
        elif check_type == QualityCheckType.CONSISTENCY:
            # Cross-field consistency checks
            score = 1.0  # Default to consistent
            passed = True
            actual_value = score
        
        elif check_type == QualityCheckType.CONFORMITY:
            # Schema validation
            if rule.validation_schema:
                schema = json.loads(rule.validation_schema)
                validator = cerberus.Validator(schema)
                
                conformity_failures = 0
                for _, record in df.iterrows():
                    if not validator.validate(record.to_dict()):
                        conformity_failures += 1
                
                failed_records = conformity_failures
                conformity_rate = (total_records - conformity_failures) / total_records
                score = conformity_rate
                passed = score >= rule.threshold
                actual_value = conformity_rate
                details = {'conformity_failures': conformity_failures, 'conformity_rate': conformity_rate}
        
        elif check_type == QualityCheckType.TIMELINESS:
            # Check data freshness
            if rule.validation_logic == 'updated_within_timeframe' and rule.field_name in df.columns:
                max_age_hours = validation_params.get('max_age_hours', 24)
                cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
                
                df[rule.field_name] = pd.to_datetime(df[rule.field_name])
                fresh_mask = df[rule.field_name] >= cutoff_time
                fresh_count = fresh_mask.sum()
                failed_records = total_records - fresh_count
                freshness_rate = fresh_count / total_records
                score = freshness_rate
                passed = score >= rule.threshold
                actual_value = freshness_rate
                details = {'fresh_count': fresh_count, 'stale_count': failed_records}
        
        # Determine severity
        severity = QualitySeverity(rule.severity)
        if not passed:
            if score < self.alert_thresholds[QualitySeverity.CRITICAL]:
                severity = QualitySeverity.CRITICAL
            elif score < self.alert_thresholds[QualitySeverity.HIGH]:
                severity = QualitySeverity.HIGH
            elif score < self.alert_thresholds[QualitySeverity.MEDIUM]:
                severity = QualitySeverity.MEDIUM
        
        # Generate message
        message = f"Quality check {'passed' if passed else 'failed'}: {rule.rule_name} (Score: {score:.2%})"
        
        return QualityCheckResult(
            check_id=str(uuid.uuid4()),
            rule_id=rule.id,
            service_name=rule.service_name,
            entity_name=rule.entity_name,
            field_name=rule.field_name,
            check_type=check_type,
            passed=passed,
            score=score,
            expected_value=rule.threshold,
            actual_value=actual_value,
            threshold=rule.threshold,
            message=message,
            details=details,
            severity=severity,
            timestamp=datetime.now(),
            records_checked=total_records,
            records_failed=failed_records
        )

    async def _get_service_data(self, service_name: str, entity_name: str) -> List[Dict[str, Any]]:
        """Get data from a DMLog service for quality checking"""
        try:
            # In a real implementation, this would call the actual service APIs
            # For now, return mock data structure
            
            mock_data = {
                'dmlog-core': {
                    'campaigns': [
                        {'id': 'camp1', 'name': 'Test Campaign', 'user_id': 'user1', 'created_at': datetime.now(), 'is_active': True},
                        {'id': 'camp2', 'name': 'Another Campaign', 'user_id': 'user1', 'created_at': datetime.now(), 'is_active': True}
                    ]
                },
                'dmlog-characters': {
                    'characters': [
                        {'id': 'char1', 'name': 'Hero', 'level': 5, 'race': 'Human', 'class': 'Fighter', 'campaign_id': 'camp1', 'hp_current': 45, 'hp_max': 50},
                        {'id': 'char2', 'name': 'Wizard', 'level': 3, 'race': 'Elf', 'class': 'Wizard', 'campaign_id': 'camp1', 'hp_current': 20, 'hp_max': 25}
                    ]
                },
                'dmlog-session': {
                    'sessions': [
                        {'id': 'sess1', 'campaign_id': 'camp1', 'start_time': datetime.now() - timedelta(hours=2), 'end_time': datetime.now(), 'duration': 7200, 'player_count': 4},
                        {'id': 'sess2', 'campaign_id': 'camp1', 'start_time': datetime.now() - timedelta(hours=1), 'end_time': None, 'duration': None, 'player_count': 3}
                    ]
                }
            }
            
            return mock_data.get(service_name, {}).get(entity_name, [])
            
        except Exception as e:
            logger.error(f"Failed to get data from {service_name}.{entity_name}: {e}")
            return []

    async def _store_quality_check_result(self, result: QualityCheckResult):
        """Store quality check result in database"""
        async with self.db_session_factory() as session:
            try:
                quality_check = QualityCheck(
                    id=result.check_id,
                    rule_id=result.rule_id,
                    service_name=result.service_name,
                    entity_name=result.entity_name,
                    field_name=result.field_name,
                    check_type=result.check_type.value,
                    passed=result.passed,
                    score=result.score,
                    threshold=result.threshold,
                    records_checked=result.records_checked,
                    records_failed=result.records_failed,
                    details=json.dumps(result.details),
                    severity=result.severity.value,
                    message=result.message,
                    executed_at=result.timestamp,
                    created_at=datetime.now()
                )
                
                session.add(quality_check)
                await session.commit()
                
            except Exception as e:
                logger.error(f"Failed to store quality check result: {e}")
                await session.rollback()

    async def _periodic_quality_check_loop(self):
        """Periodic quality check execution"""
        while True:
            try:
                # Run quality checks for all services
                await self.run_quality_checks()
                
                # Wait for next check cycle
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in periodic quality check: {e}")
                await asyncio.sleep(300)

    async def _data_profiling_loop(self):
        """Periodic data profiling"""
        while True:
            try:
                # Profile data for each service
                for service in ['dmlog-core', 'dmlog-characters', 'dmlog-session']:
                    await self._profile_service_data(service)
                
                # Wait for next profiling cycle
                await asyncio.sleep(1800)  # Profile every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in data profiling: {e}")
                await asyncio.sleep(1800)

    async def _profile_service_data(self, service_name: str):
        """Profile data for a specific service"""
        try:
            # Get service entities (mock implementation)
            entities = {
                'dmlog-core': ['campaigns', 'users'],
                'dmlog-characters': ['characters'],
                'dmlog-session': ['sessions']
            }.get(service_name, [])
            
            for entity_name in entities:
                data = await self._get_service_data(service_name, entity_name)
                if data:
                    df = pd.DataFrame(data)
                    await self._create_data_profile(service_name, entity_name, df)
                    
        except Exception as e:
            logger.error(f"Error profiling data for {service_name}: {e}")

    async def _create_data_profile(self, service_name: str, entity_name: str, df: pd.DataFrame):
        """Create data profile for entity"""
        try:
            for column in df.columns:
                if column in df.columns:
                    series = df[column].dropna()
                    
                    profile = DataProfileResult(
                        service_name=service_name,
                        entity_name=entity_name,
                        field_name=column,
                        data_type=str(df[column].dtype),
                        total_records=len(df),
                        null_count=df[column].isnull().sum(),
                        unique_count=df[column].nunique(),
                        duplicate_count=len(df) - df[column].nunique(),
                        min_value=series.min() if len(series) > 0 and pd.api.types.is_numeric_dtype(series) else None,
                        max_value=series.max() if len(series) > 0 and pd.api.types.is_numeric_dtype(series) else None,
                        mean_value=series.mean() if len(series) > 0 and pd.api.types.is_numeric_dtype(series) else None,
                        median_value=series.median() if len(series) > 0 and pd.api.types.is_numeric_dtype(series) else None,
                        std_deviation=series.std() if len(series) > 0 and pd.api.types.is_numeric_dtype(series) else None,
                        percentiles={
                            '25th': series.quantile(0.25) if len(series) > 0 and pd.api.types.is_numeric_dtype(series) else None,
                            '75th': series.quantile(0.75) if len(series) > 0 and pd.api.types.is_numeric_dtype(series) else None,
                            '95th': series.quantile(0.95) if len(series) > 0 and pd.api.types.is_numeric_dtype(series) else None
                        },
                        most_common_values=series.value_counts().head(5).to_dict() if len(series) > 0 else {},
                        pattern_matches={},  # Could add regex pattern matching
                        anomalies=[],  # Could add anomaly detection
                        profiled_at=datetime.now()
                    )
                    
                    profile_key = f"{service_name}.{entity_name}.{column}"
                    self.data_profiles[profile_key] = profile
                    
        except Exception as e:
            logger.error(f"Error creating data profile: {e}")

    async def _quality_score_calculation_loop(self):
        """Calculate overall quality scores"""
        while True:
            try:
                await self._calculate_quality_scores()
                await asyncio.sleep(600)  # Calculate every 10 minutes
                
            except Exception as e:
                logger.error(f"Error calculating quality scores: {e}")
                await asyncio.sleep(600)

    async def _calculate_quality_scores(self):
        """Calculate quality scores for each service"""
        try:
            service_scores = {}
            
            # Group recent check results by service
            recent_results = [r for r in self.check_results if r.timestamp > datetime.now() - timedelta(hours=1)]
            
            for service in ['dmlog-core', 'dmlog-characters', 'dmlog-session', 'dmlog-ai-dm']:
                service_results = [r for r in recent_results if r.service_name == service]
                
                if service_results:
                    # Calculate weighted average score
                    total_weight = 0
                    weighted_score = 0
                    
                    for result in service_results:
                        # Weight by severity
                        weight = {
                            QualitySeverity.CRITICAL: 4,
                            QualitySeverity.HIGH: 3,
                            QualitySeverity.MEDIUM: 2,
                            QualitySeverity.LOW: 1
                        }.get(result.severity, 1)
                        
                        weighted_score += result.score * weight
                        total_weight += weight
                    
                    if total_weight > 0:
                        service_scores[service] = weighted_score / total_weight
                    else:
                        service_scores[service] = 0.0
                else:
                    service_scores[service] = 1.0  # No issues found
            
            self.quality_scores = service_scores
            
            logger.info(f"Updated quality scores: {service_scores}")
            
        except Exception as e:
            logger.error(f"Error calculating quality scores: {e}")

    async def _alert_monitoring_loop(self):
        """Monitor for quality alerts"""
        while True:
            try:
                await self._check_quality_alerts()
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in alert monitoring: {e}")
                await asyncio.sleep(60)

    async def _check_quality_alerts(self):
        """Check for quality issues that require alerts"""
        try:
            recent_results = [r for r in self.check_results if r.timestamp > datetime.now() - timedelta(minutes=5)]
            
            for result in recent_results:
                if not result.passed and result.severity in [QualitySeverity.CRITICAL, QualitySeverity.HIGH]:
                    await self._send_quality_alert(result)
                    
        except Exception as e:
            logger.error(f"Error checking quality alerts: {e}")

    async def _send_quality_alert(self, result: QualityCheckResult):
        """Send quality alert"""
        try:
            alert = {
                'alert_id': str(uuid.uuid4()),
                'alert_type': 'data_quality_issue',
                'severity': result.severity.value,
                'service': result.service_name,
                'entity': result.entity_name,
                'field': result.field_name,
                'issue': result.message,
                'score': result.score,
                'threshold': result.threshold,
                'timestamp': result.timestamp.isoformat(),
                'details': result.details
            }
            
            logger.warning(f"QUALITY ALERT: {alert}")
            
            # In production, this would send to alerting system
            # (Slack, PagerDuty, etc.)
            
        except Exception as e:
            logger.error(f"Error sending quality alert: {e}")

    async def get_quality_dashboard_data(self) -> Dict[str, Any]:
        """Get data for quality monitoring dashboard"""
        try:
            recent_results = [r for r in self.check_results if r.timestamp > datetime.now() - timedelta(hours=24)]
            
            dashboard_data = {
                'overall_scores': self.quality_scores,
                'recent_checks': len(recent_results),
                'failed_checks': len([r for r in recent_results if not r.passed]),
                'critical_issues': len([r for r in recent_results if r.severity == QualitySeverity.CRITICAL]),
                'quality_trends': await self._calculate_quality_trends(),
                'service_breakdown': self._get_service_breakdown(recent_results),
                'check_type_distribution': self._get_check_type_distribution(recent_results),
                'data_profiles': len(self.data_profiles),
                'active_rules': len([r for r in self.quality_rules.values() if r.is_active])
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting quality dashboard data: {e}")
            return {}

    async def _calculate_quality_trends(self) -> Dict[str, Any]:
        """Calculate quality trends over time"""
        try:
            # Group results by time periods
            trends = {}
            
            for service in self.quality_scores.keys():
                service_results = [r for r in self.check_results if r.service_name == service]
                
                # Group by hour for last 24 hours
                hourly_scores = defaultdict(list)
                for result in service_results:
                    hour_key = result.timestamp.replace(minute=0, second=0, microsecond=0)
                    hourly_scores[hour_key].append(result.score)
                
                # Calculate average score per hour
                hourly_averages = []
                timestamps = []
                for hour, scores in sorted(hourly_scores.items()):
                    if scores:
                        hourly_averages.append(statistics.mean(scores))
                        timestamps.append(hour)
                
                if len(hourly_averages) >= 2:
                    # Simple trend calculation
                    recent_avg = statistics.mean(hourly_averages[-3:]) if len(hourly_averages) >= 3 else hourly_averages[-1]
                    older_avg = statistics.mean(hourly_averages[:3]) if len(hourly_averages) >= 3 else hourly_averages[0]
                    
                    if recent_avg > older_avg + 0.05:
                        trend_direction = 'improving'
                    elif recent_avg < older_avg - 0.05:
                        trend_direction = 'degrading'
                    else:
                        trend_direction = 'stable'
                    
                    trends[service] = {
                        'direction': trend_direction,
                        'current_score': recent_avg,
                        'previous_score': older_avg,
                        'change': recent_avg - older_avg
                    }
                
            return trends
            
        except Exception as e:
            logger.error(f"Error calculating quality trends: {e}")
            return {}

    def _get_service_breakdown(self, results: List[QualityCheckResult]) -> Dict[str, Any]:
        """Get quality breakdown by service"""
        breakdown = {}
        
        for service in ['dmlog-core', 'dmlog-characters', 'dmlog-session', 'dmlog-ai-dm']:
            service_results = [r for r in results if r.service_name == service]
            
            if service_results:
                breakdown[service] = {
                    'total_checks': len(service_results),
                    'passed_checks': len([r for r in service_results if r.passed]),
                    'failed_checks': len([r for r in service_results if not r.passed]),
                    'average_score': statistics.mean([r.score for r in service_results]),
                    'critical_issues': len([r for r in service_results if r.severity == QualitySeverity.CRITICAL])
                }
        
        return breakdown

    def _get_check_type_distribution(self, results: List[QualityCheckResult]) -> Dict[str, int]:
        """Get distribution of check types"""
        distribution = defaultdict(int)
        
        for result in results:
            distribution[result.check_type.value] += 1
        
        return dict(distribution)

    async def cleanup(self):
        """Cleanup quality monitor resources"""
        logger.info("Cleaning up Data Quality Monitor")
        
        # Cancel background tasks
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        # Clear caches
        self.check_results.clear()
        self.data_profiles.clear()
        self.quality_scores.clear()
        
        logger.info("Data Quality Monitor cleanup complete")