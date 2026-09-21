"""
ETL Pipeline Main Service
Comprehensive data pipeline with Airflow, ingestion, transformation, and monitoring
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import json
import uuid
from enum import Enum

# Import pipeline components
from airflow_config import (
    setup_airflow_environment, get_default_dag_args,
    get_data_source_connections, AirflowDagBuilder
)
from ingestion.data_sources import (
    DataSourceFactory, get_all_data_source_configs,
    get_data_source_config, DataSourceType, DataFormat
)
from transformations.transformation_engine import (
    TransformationEngine, TransformationRule, TransformationType,
    get_sample_transformation_rules
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PipelineStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class JobType(str, Enum):
    INGESTION = "ingestion"
    TRANSFORMATION = "transformation"
    FULL_PIPELINE = "full_pipeline"
    VALIDATION = "validation"
    QUALITY_CHECK = "quality_check"

# Request/Response Models
class PipelineRequest(BaseModel):
    pipeline_id: str
    name: str
    description: str = ""
    source_configs: List[Dict[str, Any]]
    transformation_rules: List[Dict[str, Any]] = Field(default_factory=list)
    destination_config: Dict[str, Any]
    schedule: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=10)
    tags: List[str] = Field(default_factory=list)

class JobRequest(BaseModel):
    job_type: JobType
    pipeline_id: Optional[str] = None
    source_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class DataQualityCheck(BaseModel):
    check_id: str
    check_type: str
    parameters: Dict[str, Any]
    thresholds: Dict[str, float] = Field(default_factory=dict)

class ETLPipelineService:
    """Main ETL Pipeline service"""
    
    def __init__(self):
        self.pipelines = {}
        self.active_jobs = {}
        self.job_history = {}
        self.transformation_engine = TransformationEngine()
        self.data_sources = {}
        self.quality_checks = {}
        
        # Initialize components
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the ETL pipeline service"""
        try:
            # Setup Airflow environment
            setup_airflow_environment()
            logger.info("Airflow environment initialized")
            
            # Load data source configurations
            self._load_data_sources()
            
            # Load sample transformation rules
            self._load_transformation_rules()
            
            logger.info("ETL Pipeline service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ETL Pipeline service: {e}")
            raise
    
    def _load_data_sources(self):
        """Load and initialize data sources"""
        try:
            source_configs = get_all_data_source_configs()
            
            for config in source_configs:
                try:
                    source = DataSourceFactory.create_source(config)
                    self.data_sources[config.source_id] = {
                        'config': config,
                        'source': source,
                        'status': 'initialized',
                        'last_used': None,
                        'error_count': 0
                    }
                    logger.info(f"Loaded data source: {config.source_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to load data source {config.source_id}: {e}")
            
            logger.info(f"Loaded {len(self.data_sources)} data sources")
            
        except Exception as e:
            logger.error(f"Failed to load data sources: {e}")
    
    def _load_transformation_rules(self):
        """Load sample transformation rules"""
        try:
            sample_rules = get_sample_transformation_rules()
            
            for rule in sample_rules:
                self.transformation_engine.register_transformation(rule)
                logger.info(f"Loaded transformation rule: {rule.rule_id}")
            
            logger.info(f"Loaded {len(sample_rules)} transformation rules")
            
        except Exception as e:
            logger.error(f"Failed to load transformation rules: {e}")
    
    async def create_pipeline(self, request: PipelineRequest) -> Dict[str, Any]:
        """Create a new ETL pipeline"""
        try:
            pipeline_id = request.pipeline_id
            
            if pipeline_id in self.pipelines:
                raise ValueError(f"Pipeline {pipeline_id} already exists")
            
            # Validate source configurations
            for source_config in request.source_configs:
                source_id = source_config.get('source_id')
                if source_id not in self.data_sources:
                    raise ValueError(f"Data source {source_id} not found")
            
            # Validate transformation rules
            for rule_config in request.transformation_rules:
                rule_id = rule_config.get('rule_id')
                if rule_id not in self.transformation_engine.get_registered_transformations():
                    logger.warning(f"Transformation rule {rule_id} not registered")
            
            # Create pipeline configuration
            pipeline = {
                'pipeline_id': pipeline_id,
                'name': request.name,
                'description': request.description,
                'source_configs': request.source_configs,
                'transformation_rules': request.transformation_rules,
                'destination_config': request.destination_config,
                'schedule': request.schedule,
                'priority': request.priority,
                'tags': request.tags,
                'status': PipelineStatus.CREATED,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'run_history': [],
                'statistics': {
                    'total_runs': 0,
                    'successful_runs': 0,
                    'failed_runs': 0,
                    'average_execution_time': 0.0
                }
            }
            
            self.pipelines[pipeline_id] = pipeline
            
            # Create Airflow DAG if scheduled
            if request.schedule:
                await self._create_airflow_dag(pipeline)
            
            logger.info(f"Created pipeline: {pipeline_id}")
            
            return {
                'pipeline_id': pipeline_id,
                'status': 'created',
                'created_at': pipeline['created_at'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create pipeline: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def run_pipeline(self, pipeline_id: str, parameters: Dict[str, Any] = None) -> str:
        """Run an ETL pipeline"""
        if pipeline_id not in self.pipelines:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")
        
        pipeline = self.pipelines[pipeline_id]
        run_id = str(uuid.uuid4())
        
        # Create job for pipeline execution
        job_config = {
            'job_id': run_id,
            'job_type': JobType.FULL_PIPELINE,
            'pipeline_id': pipeline_id,
            'parameters': parameters or {},
            'status': PipelineStatus.RUNNING,
            'started_at': datetime.utcnow(),
            'pipeline_config': pipeline
        }
        
        self.active_jobs[run_id] = job_config
        pipeline['status'] = PipelineStatus.RUNNING
        
        # Execute pipeline asynchronously
        asyncio.create_task(self._execute_pipeline(run_id))
        
        logger.info(f"Started pipeline execution: {pipeline_id} (run_id: {run_id})")
        
        return run_id
    
    async def _execute_pipeline(self, run_id: str):
        """Execute pipeline asynchronously"""
        job = self.active_jobs[run_id]
        pipeline_config = job['pipeline_config']
        
        try:
            execution_log = []
            
            # Step 1: Data Ingestion
            logger.info(f"Starting data ingestion for run {run_id}")
            ingested_data = await self._execute_ingestion(
                pipeline_config['source_configs'],
                job['parameters']
            )
            execution_log.append({
                'step': 'ingestion',
                'status': 'completed',
                'records_ingested': len(ingested_data) if isinstance(ingested_data, list) else 1,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Step 2: Data Transformation
            logger.info(f"Starting data transformation for run {run_id}")
            transformed_data = await self._execute_transformations(
                ingested_data,
                pipeline_config['transformation_rules']
            )
            execution_log.append({
                'step': 'transformation',
                'status': 'completed',
                'records_processed': len(transformed_data) if isinstance(transformed_data, list) else 1,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Step 3: Data Quality Checks
            logger.info(f"Running data quality checks for run {run_id}")
            quality_results = await self._run_quality_checks(transformed_data)
            execution_log.append({
                'step': 'quality_checks',
                'status': 'completed',
                'quality_score': quality_results.get('overall_score', 0),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Step 4: Data Loading (to destination)
            logger.info(f"Loading data to destination for run {run_id}")
            load_result = await self._load_to_destination(
                transformed_data,
                pipeline_config['destination_config']
            )
            execution_log.append({
                'step': 'loading',
                'status': 'completed',
                'records_loaded': load_result.get('records_loaded', 0),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Complete job
            job['status'] = PipelineStatus.COMPLETED
            job['completed_at'] = datetime.utcnow()
            job['execution_log'] = execution_log
            job['result'] = {
                'records_processed': len(transformed_data) if isinstance(transformed_data, list) else 1,
                'quality_score': quality_results.get('overall_score', 0),
                'execution_time': (job['completed_at'] - job['started_at']).total_seconds()
            }
            
            # Update pipeline statistics
            pipeline = self.pipelines[pipeline_config['pipeline_id']]
            pipeline['status'] = PipelineStatus.COMPLETED
            pipeline['statistics']['total_runs'] += 1
            pipeline['statistics']['successful_runs'] += 1
            
            # Move to history
            self.job_history[run_id] = self.active_jobs.pop(run_id)
            
            logger.info(f"Pipeline execution completed successfully: {run_id}")
            
        except Exception as e:
            logger.error(f"Pipeline execution failed for run {run_id}: {e}")
            
            job['status'] = PipelineStatus.FAILED
            job['completed_at'] = datetime.utcnow()
            job['error'] = str(e)
            
            # Update pipeline statistics
            pipeline = self.pipelines[pipeline_config['pipeline_id']]
            pipeline['status'] = PipelineStatus.FAILED
            pipeline['statistics']['total_runs'] += 1
            pipeline['statistics']['failed_runs'] += 1
            
            # Move to history
            self.job_history[run_id] = self.active_jobs.pop(run_id)
    
    async def _execute_ingestion(self, source_configs: List[Dict[str, Any]], 
                               parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute data ingestion from configured sources"""
        all_data = []
        
        for source_config in source_configs:
            source_id = source_config['source_id']
            
            if source_id not in self.data_sources:
                logger.warning(f"Data source {source_id} not found, skipping")
                continue
            
            try:
                data_source = self.data_sources[source_id]['source']
                
                # Connect to data source
                connected = await data_source.connect()
                if not connected:
                    logger.error(f"Failed to connect to data source {source_id}")
                    continue
                
                # Extract data
                query_params = {**source_config.get('query_params', {}), **parameters}
                
                extracted_data = []
                async for record in data_source.extract_data(query_params):
                    extracted_data.append(record)
                
                all_data.extend(extracted_data)
                
                # Update source status
                self.data_sources[source_id]['status'] = 'active'
                self.data_sources[source_id]['last_used'] = datetime.utcnow()
                
                logger.info(f"Ingested {len(extracted_data)} records from {source_id}")
                
                # Disconnect
                await data_source.disconnect()
                
            except Exception as e:
                logger.error(f"Failed to ingest from {source_id}: {e}")
                self.data_sources[source_id]['error_count'] += 1
                self.data_sources[source_id]['status'] = 'error'
        
        return all_data
    
    async def _execute_transformations(self, data: List[Dict[str, Any]], 
                                     transformation_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute data transformations"""
        if not transformation_rules:
            return data
        
        # Extract rule IDs
        rule_ids = [rule['rule_id'] for rule in transformation_rules if 'rule_id' in rule]
        
        # Apply transformation pipeline
        result = await self.transformation_engine.apply_transformation_pipeline(rule_ids, data)
        
        if result.success:
            return result.transformed_data
        else:
            logger.error(f"Transformation failed: {result.errors}")
            # Return original data on failure
            return data
    
    async def _run_quality_checks(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run data quality checks"""
        quality_results = {
            'overall_score': 0.0,
            'checks': [],
            'total_records': len(data) if isinstance(data, list) else 1,
            'valid_records': 0,
            'invalid_records': 0
        }
        
        if not data:
            return quality_results
        
        try:
            # Basic quality checks
            checks = [
                self._check_completeness(data),
                self._check_uniqueness(data),
                self._check_format_consistency(data),
                self._check_value_ranges(data)
            ]
            
            check_results = await asyncio.gather(*checks)
            quality_results['checks'] = check_results
            
            # Calculate overall score
            scores = [check.get('score', 0) for check in check_results]
            quality_results['overall_score'] = sum(scores) / len(scores) if scores else 0
            
            # Count valid/invalid records
            valid_records = 0
            for check in check_results:
                if check.get('passed', False):
                    valid_records += check.get('valid_records', 0)
            
            quality_results['valid_records'] = valid_records
            quality_results['invalid_records'] = quality_results['total_records'] - valid_records
            
        except Exception as e:
            logger.error(f"Quality checks failed: {e}")
        
        return quality_results
    
    async def _check_completeness(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check data completeness"""
        total_records = len(data)
        complete_records = 0
        
        for record in data:
            if all(value is not None and value != '' for value in record.values()):
                complete_records += 1
        
        score = (complete_records / total_records) * 100 if total_records > 0 else 0
        
        return {
            'check_name': 'completeness',
            'score': score,
            'passed': score >= 80,  # 80% threshold
            'total_records': total_records,
            'valid_records': complete_records,
            'details': f'{complete_records}/{total_records} complete records'
        }
    
    async def _check_uniqueness(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check data uniqueness"""
        if not data:
            return {'check_name': 'uniqueness', 'score': 0, 'passed': False}
        
        # Use first record to determine fields to check
        fields_to_check = ['id', 'user_id', 'email', 'key']  # Common unique fields
        existing_fields = [field for field in fields_to_check if field in data[0]]
        
        if not existing_fields:
            return {
                'check_name': 'uniqueness',
                'score': 100,
                'passed': True,
                'details': 'No uniqueness fields found'
            }
        
        unique_violations = 0
        for field in existing_fields:
            values = [record.get(field) for record in data if record.get(field) is not None]
            unique_values = set(values)
            if len(values) != len(unique_values):
                unique_violations += 1
        
        score = ((len(existing_fields) - unique_violations) / len(existing_fields)) * 100
        
        return {
            'check_name': 'uniqueness',
            'score': score,
            'passed': score >= 90,
            'violations': unique_violations,
            'details': f'{unique_violations} uniqueness violations found'
        }
    
    async def _check_format_consistency(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check format consistency"""
        if not data:
            return {'check_name': 'format_consistency', 'score': 0, 'passed': False}
        
        # Check email format consistency
        email_fields = ['email', 'user_email', 'contact_email']
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        total_checks = 0
        passed_checks = 0
        
        for field in email_fields:
            if field in data[0]:
                for record in data:
                    if record.get(field):
                        total_checks += 1
                        if re.match(email_pattern, str(record[field])):
                            passed_checks += 1
        
        score = (passed_checks / total_checks) * 100 if total_checks > 0 else 100
        
        return {
            'check_name': 'format_consistency',
            'score': score,
            'passed': score >= 85,
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'details': f'{passed_checks}/{total_checks} format checks passed'
        }
    
    async def _check_value_ranges(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check value ranges"""
        if not data:
            return {'check_name': 'value_ranges', 'score': 0, 'passed': False}
        
        # Check numeric fields for reasonable ranges
        numeric_fields = []
        for record in data[:10]:  # Sample first 10 records
            for field, value in record.items():
                if isinstance(value, (int, float)) and field not in numeric_fields:
                    numeric_fields.append(field)
        
        if not numeric_fields:
            return {
                'check_name': 'value_ranges',
                'score': 100,
                'passed': True,
                'details': 'No numeric fields found'
            }
        
        range_violations = 0
        total_values = 0
        
        for field in numeric_fields:
            values = [record.get(field) for record in data if isinstance(record.get(field), (int, float))]
            
            if values:
                min_val = min(values)
                max_val = max(values)
                total_values += len(values)
                
                # Check for unreasonable values (very basic checks)
                for value in values:
                    if value < 0 and field in ['age', 'count', 'quantity']:  # Age/count shouldn't be negative
                        range_violations += 1
                    elif abs(value) > 1e10:  # Unreasonably large numbers
                        range_violations += 1
        
        score = ((total_values - range_violations) / total_values) * 100 if total_values > 0 else 100
        
        return {
            'check_name': 'value_ranges',
            'score': score,
            'passed': score >= 95,
            'violations': range_violations,
            'total_values': total_values,
            'details': f'{range_violations}/{total_values} range violations found'
        }
    
    async def _load_to_destination(self, data: List[Dict[str, Any]], 
                                 destination_config: Dict[str, Any]) -> Dict[str, Any]:
        """Load transformed data to destination"""
        destination_type = destination_config.get('type', 'file')
        
        try:
            if destination_type == 'file':
                file_path = destination_config.get('file_path', '/tmp/etl_output.json')
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                return {
                    'records_loaded': len(data),
                    'destination': file_path,
                    'format': 'json'
                }
            
            elif destination_type == 'database':
                # Placeholder for database loading
                logger.info(f"Would load {len(data)} records to database")
                return {
                    'records_loaded': len(data),
                    'destination': 'database',
                    'table': destination_config.get('table', 'default_table')
                }
            
            else:
                logger.warning(f"Unsupported destination type: {destination_type}")
                return {
                    'records_loaded': 0,
                    'error': f"Unsupported destination type: {destination_type}"
                }
                
        except Exception as e:
            logger.error(f"Failed to load to destination: {e}")
            return {
                'records_loaded': 0,
                'error': str(e)
            }
    
    async def _create_airflow_dag(self, pipeline: Dict[str, Any]):
        """Create Airflow DAG for scheduled pipeline"""
        try:
            dag_builder = AirflowDagBuilder()
            
            dag = dag_builder.create_data_pipeline_dag(
                dag_id=f"etl_pipeline_{pipeline['pipeline_id']}",
                description=pipeline['description'],
                schedule_interval=pipeline['schedule'],
                source_configs=pipeline['source_configs'],
                transformation_configs=pipeline['transformation_rules'],
                destination_configs=[pipeline['destination_config']]
            )
            
            logger.info(f"Created Airflow DAG for pipeline: {pipeline['pipeline_id']}")
            
        except Exception as e:
            logger.error(f"Failed to create Airflow DAG: {e}")
    
    async def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get pipeline status and statistics"""
        if pipeline_id not in self.pipelines:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")
        
        pipeline = self.pipelines[pipeline_id]
        
        # Get active jobs for this pipeline
        active_jobs = [
            job for job in self.active_jobs.values()
            if job.get('pipeline_id') == pipeline_id
        ]
        
        # Get recent job history
        recent_jobs = [
            job for job in list(self.job_history.values())[-10:]
            if job.get('pipeline_id') == pipeline_id
        ]
        
        return {
            'pipeline_id': pipeline_id,
            'status': pipeline['status'],
            'statistics': pipeline['statistics'],
            'active_jobs': len(active_jobs),
            'recent_runs': len(recent_jobs),
            'last_run': recent_jobs[-1]['completed_at'].isoformat() if recent_jobs else None,
            'created_at': pipeline['created_at'].isoformat(),
            'updated_at': pipeline['updated_at'].isoformat()
        }
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and details"""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            return {
                'job_id': job_id,
                'status': job['status'],
                'started_at': job['started_at'].isoformat(),
                'pipeline_id': job.get('pipeline_id'),
                'job_type': job['job_type']
            }
        elif job_id in self.job_history:
            job = self.job_history[job_id]
            return {
                'job_id': job_id,
                'status': job['status'],
                'started_at': job['started_at'].isoformat(),
                'completed_at': job.get('completed_at', datetime.utcnow()).isoformat(),
                'pipeline_id': job.get('pipeline_id'),
                'job_type': job['job_type'],
                'result': job.get('result', {}),
                'execution_log': job.get('execution_log', [])
            }
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    async def get_data_sources_status(self) -> Dict[str, Any]:
        """Get status of all data sources"""
        source_statuses = {}
        
        for source_id, source_info in self.data_sources.items():
            source_statuses[source_id] = {
                'source_type': source_info['config'].source_type,
                'data_format': source_info['config'].data_format,
                'status': source_info['status'],
                'last_used': source_info['last_used'].isoformat() if source_info['last_used'] else None,
                'error_count': source_info['error_count'],
                'enabled': source_info['config'].enabled
            }
        
        return {
            'total_sources': len(self.data_sources),
            'active_sources': len([s for s in self.data_sources.values() if s['status'] == 'active']),
            'error_sources': len([s for s in self.data_sources.values() if s['status'] == 'error']),
            'sources': source_statuses
        }
    
    async def shutdown(self):
        """Shutdown the ETL pipeline service"""
        try:
            # Shutdown transformation engine
            await self.transformation_engine.shutdown()
            
            # Close data source connections
            for source_info in self.data_sources.values():
                try:
                    await source_info['source'].disconnect()
                except:
                    pass
            
            logger.info("ETL Pipeline service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# FastAPI App
app = FastAPI(
    title="ETL Pipeline Service",
    description="Comprehensive data pipeline with Airflow integration, ingestion, transformation, and monitoring",
    version="1.0.0"
)

service = ETLPipelineService()

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("ETL Pipeline service started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    await service.shutdown()

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "etl-pipeline",
        "timestamp": datetime.utcnow().isoformat(),
        "active_pipelines": len(service.pipelines),
        "active_jobs": len(service.active_jobs),
        "data_sources": len(service.data_sources)
    }

# Pipeline endpoints
@app.post("/api/pipelines")
async def create_pipeline(request: PipelineRequest):
    result = await service.create_pipeline(request)
    return {"success": True, **result}

@app.post("/api/pipelines/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, parameters: Dict[str, Any] = None):
    run_id = await service.run_pipeline(pipeline_id, parameters)
    return {"success": True, "run_id": run_id}

@app.get("/api/pipelines/{pipeline_id}/status")
async def get_pipeline_status(pipeline_id: str):
    result = await service.get_pipeline_status(pipeline_id)
    return {"success": True, **result}

@app.get("/api/pipelines")
async def list_pipelines():
    pipelines = list(service.pipelines.keys())
    return {"success": True, "pipelines": pipelines, "total": len(pipelines)}

# Job endpoints
@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    result = await service.get_job_status(job_id)
    return {"success": True, **result}

@app.get("/api/jobs")
async def list_jobs():
    active_jobs = list(service.active_jobs.keys())
    completed_jobs = list(service.job_history.keys())
    return {
        "success": True,
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs[-20:],  # Last 20 completed jobs
        "total_active": len(active_jobs),
        "total_completed": len(completed_jobs)
    }

# Data sources endpoints
@app.get("/api/data-sources")
async def get_data_sources_status():
    result = await service.get_data_sources_status()
    return {"success": True, **result}

@app.get("/api/data-sources/{source_id}/test")
async def test_data_source(source_id: str):
    if source_id not in service.data_sources:
        raise HTTPException(status_code=404, detail=f"Data source {source_id} not found")
    
    data_source = service.data_sources[source_id]['source']
    health_status = await data_source.health_check()
    
    return {
        "success": True,
        "source_id": source_id,
        "health_status": health_status,
        "tested_at": datetime.utcnow().isoformat()
    }

# Transformation endpoints
@app.get("/api/transformations")
async def list_transformations():
    transformations = service.transformation_engine.get_registered_transformations()
    stats = service.transformation_engine.get_transformation_stats()
    
    return {
        "success": True,
        "transformations": transformations,
        "statistics": stats,
        "total": len(transformations)
    }

# Monitoring endpoints
@app.get("/api/monitoring/overview")
async def get_monitoring_overview():
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "pipelines": {
            "total": len(service.pipelines),
            "running": len([p for p in service.pipelines.values() if p['status'] == PipelineStatus.RUNNING]),
            "completed": len([p for p in service.pipelines.values() if p['status'] == PipelineStatus.COMPLETED]),
            "failed": len([p for p in service.pipelines.values() if p['status'] == PipelineStatus.FAILED])
        },
        "jobs": {
            "active": len(service.active_jobs),
            "completed_today": len([
                job for job in service.job_history.values()
                if job.get('completed_at', datetime.min).date() == datetime.utcnow().date()
            ])
        },
        "data_sources": {
            "total": len(service.data_sources),
            "healthy": len([s for s in service.data_sources.values() if s['status'] == 'active']),
            "errors": len([s for s in service.data_sources.values() if s['status'] == 'error'])
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8103)