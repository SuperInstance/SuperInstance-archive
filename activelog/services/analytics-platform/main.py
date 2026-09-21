"""
Analytics Platform Main Service
Comprehensive analytics platform with forecasting, anomaly detection, and advanced analytics
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import asyncio
import logging
import json
import uuid
import pandas as pd
import numpy as np
from enum import Enum
import plotly.graph_objects as go
import plotly.io as pio
import base64

# Import analytics components
from time_series.forecasting_engine import (
    ForecastingEngine, ForecastConfig, ForecastModel, 
    SeasonalityType, TrendType, TimeSeriesAnalyzer
)
from anomaly_detection.anomaly_engine import (
    AnomalyDetectionEngine, AnomalyConfig, AnomalyMethod,
    AnomalyType, StatisticalAnomalyDetector
)
from predictive.models_engine import (
    PredictiveModelsEngine, ModelConfig, ModelType, 
    ProblemType, FeatureEngineeringType
)
from export.bi_export_engine import (
    BIExportEngine, ExportConfig, ExportFormat, BIToolType
)
from reports.scheduler_engine import (
    ScheduledReportsEngine, ReportTemplate, ScheduleConfig, DeliveryConfig,
    ReportFrequency, DeliveryMethod, ReportStatus
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsJobType(str, Enum):
    TIME_SERIES_FORECAST = "time_series_forecast"
    ANOMALY_DETECTION = "anomaly_detection"
    COHORT_ANALYSIS = "cohort_analysis"
    FUNNEL_ANALYSIS = "funnel_analysis"
    RETENTION_ANALYSIS = "retention_analysis"
    AB_TEST = "ab_test"
    CUSTOM_METRICS = "custom_metrics"
    PREDICTIVE_MODEL = "predictive_model"

class MetricType(str, Enum):
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    RATIO = "ratio"
    GROWTH_RATE = "growth_rate"
    CONVERSION_RATE = "conversion_rate"

# Request/Response Models
class TimeSeriesForecastRequest(BaseModel):
    data: Dict[str, List[Union[float, int]]]  # {timestamp: value} or {index: value}
    forecast_config: Dict[str, Any]
    analysis_config: Dict[str, Any] = Field(default_factory=dict)

class AnomalyDetectionRequest(BaseModel):
    data: Dict[str, List[Union[float, int]]]
    detection_config: Dict[str, Any]
    ensemble_configs: Optional[List[Dict[str, Any]]] = None

class CohortAnalysisRequest(BaseModel):
    user_data: List[Dict[str, Any]]  # User events with timestamps
    cohort_type: str = "monthly"  # monthly, weekly, daily
    period_range: int = 12
    event_name: str = "signup"
    value_column: Optional[str] = None

class FunnelAnalysisRequest(BaseModel):
    events_data: List[Dict[str, Any]]
    funnel_steps: List[Dict[str, str]]  # [{step_name, event_name}]
    user_id_column: str = "user_id"
    timestamp_column: str = "timestamp"
    time_window_days: int = 30

class RetentionAnalysisRequest(BaseModel):
    user_events: List[Dict[str, Any]]
    cohort_date_column: str = "signup_date"
    activity_date_column: str = "activity_date" 
    user_id_column: str = "user_id"
    period_type: str = "weekly"  # daily, weekly, monthly
    periods_to_analyze: int = 12

class ABTestRequest(BaseModel):
    experiment_data: List[Dict[str, Any]]
    control_group: str
    treatment_groups: List[str]
    metric_column: str
    user_id_column: str = "user_id"
    confidence_level: float = 0.95

class CustomMetricRequest(BaseModel):
    metric_name: str
    metric_type: MetricType
    data_source: Dict[str, Any]
    aggregation_rules: Dict[str, Any]
    filters: Dict[str, Any] = Field(default_factory=dict)
    dimensions: List[str] = Field(default_factory=list)

class PredictiveModelRequest(BaseModel):
    model_name: str
    model_type: str  # from ModelType enum
    problem_type: str  # from ProblemType enum
    training_data: Dict[str, List[Union[float, int, str]]]
    target_column: str
    feature_columns: List[str] = Field(default_factory=list)
    test_size: float = 0.2
    hyperparameter_tuning: bool = True
    feature_engineering: List[str] = Field(default_factory=list)
    model_parameters: Dict[str, Any] = Field(default_factory=dict)

class PredictionRequest(BaseModel):
    model_id: str
    prediction_data: Dict[str, List[Union[float, int, str]]]

class DataExportRequest(BaseModel):
    job_id: Optional[str] = None  # Export specific job results
    data_source: str = "job_results"  # job_results, custom_data, dashboard_data
    export_format: str  # from ExportFormat enum
    filename: Optional[str] = None
    include_metadata: bool = True
    include_visualizations: bool = False
    custom_data: Optional[Dict[str, Any]] = None
    bi_tool: Optional[str] = None  # from BIToolType enum
    export_settings: Dict[str, Any] = Field(default_factory=dict)

class ReportTemplateRequest(BaseModel):
    name: str
    description: str = ""
    analytics_job_type: str
    data_query: Dict[str, Any]
    visualization_config: Dict[str, Any] = Field(default_factory=dict)
    export_formats: List[str] = Field(default_factory=lambda: ["pdf", "excel"])
    custom_content: Dict[str, Any] = Field(default_factory=dict)

class ScheduledReportRequest(BaseModel):
    name: str
    template_id: str
    schedule: Dict[str, Any]  # frequency, time_of_day, etc.
    delivery: Dict[str, Any]  # method, recipients, etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnalyticsPlatformService:
    """Main analytics platform service"""
    
    def __init__(self):
        # Analytics engines
        self.forecasting_engine = ForecastingEngine()
        self.anomaly_engine = AnomalyDetectionEngine()
        self.time_series_analyzer = TimeSeriesAnalyzer()
        self.predictive_engine = PredictiveModelsEngine()
        self.export_engine = BIExportEngine()
        self.reports_engine = ScheduledReportsEngine(analytics_service=self)
        
        # Job tracking
        self.active_jobs = {}
        self.completed_jobs = {}
        self.custom_metrics = {}
        self.dashboards = {}
        self.ab_tests = {}
        self.predictive_models = {}
        
        # WebSocket connections for real-time updates
        self.websocket_connections = {}
        
        logger.info("Analytics Platform Service initialized")
    
    async def create_time_series_forecast(self, request: TimeSeriesForecastRequest) -> Dict[str, Any]:
        """Create time series forecast"""
        job_id = str(uuid.uuid4())
        
        try:
            # Convert data to pandas Series
            if isinstance(list(request.data.keys())[0], str):
                # Assume timestamp format
                timestamps = pd.to_datetime(list(request.data.keys()))
                values = list(request.data.values())
                data_series = pd.Series(values, index=timestamps)
            else:
                # Assume numeric index
                data_series = pd.Series(list(request.data.values()))
            
            # Create forecast configuration
            forecast_config = ForecastConfig(
                model_type=ForecastModel(request.forecast_config.get('model_type', 'prophet')),
                forecast_periods=request.forecast_config.get('forecast_periods', 30),
                confidence_intervals=request.forecast_config.get('confidence_intervals', [0.8, 0.95]),
                seasonality_type=SeasonalityType(request.forecast_config.get('seasonality_type', 'auto')),
                trend_type=TrendType(request.forecast_config.get('trend_type', 'linear')),
                parameters=request.forecast_config.get('parameters', {}),
                validation_split=request.forecast_config.get('validation_split', 0.2),
                cross_validation=request.forecast_config.get('cross_validation', True)
            )
            
            # Create job entry
            job_entry = {
                'job_id': job_id,
                'job_type': AnalyticsJobType.TIME_SERIES_FORECAST,
                'status': 'running',
                'created_at': datetime.utcnow(),
                'data_points': len(data_series),
                'config': forecast_config
            }
            self.active_jobs[job_id] = job_entry
            
            # Run analysis if requested
            analysis_results = None
            if request.analysis_config.get('run_analysis', True):
                analysis_results = await self.time_series_analyzer.analyze_time_series(data_series)
            
            # Create forecast
            forecast_result = await self.forecasting_engine.create_forecast(data_series, forecast_config)
            
            # Generate visualization
            visualization = await self.forecasting_engine.generate_forecast_visualization(data_series, forecast_result)
            
            # Complete job
            job_entry['status'] = 'completed'
            job_entry['completed_at'] = datetime.utcnow()
            job_entry['results'] = {
                'forecast': forecast_result.forecast.to_dict(),
                'confidence_intervals': {k: v.to_dict() for k, v in forecast_result.confidence_intervals.items()},
                'metrics': forecast_result.metrics,
                'model_parameters': forecast_result.model_parameters,
                'analysis': analysis_results,
                'visualization': pio.to_json(visualization)
            }
            
            self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            # Send real-time update
            await self._broadcast_job_update(job_id, 'completed')
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'forecast_points': len(forecast_result.forecast),
                'model_used': forecast_result.model_name,
                'execution_time': job_entry['results'].get('execution_time', 0),
                'metrics': forecast_result.metrics
            }
            
        except Exception as e:
            # Handle job failure
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = 'failed'
                self.active_jobs[job_id]['error'] = str(e)
                self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'failed')
            
            logger.error(f"Time series forecast failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def detect_anomalies(self, request: AnomalyDetectionRequest) -> Dict[str, Any]:
        """Detect anomalies in data"""
        job_id = str(uuid.uuid4())
        
        try:
            # Convert data to DataFrame
            if isinstance(request.data, dict) and len(request.data) > 0:
                # If dict format {column: [values]}
                df = pd.DataFrame(request.data)
            else:
                raise ValueError("Invalid data format")
            
            # Create anomaly configuration
            anomaly_config = AnomalyConfig(
                method=AnomalyMethod(request.detection_config.get('method', 'isolation_forest')),
                contamination=request.detection_config.get('contamination', 0.1),
                parameters=request.detection_config.get('parameters', {}),
                preprocessing=request.detection_config.get('preprocessing', {}),
                detection_type=AnomalyType(request.detection_config.get('detection_type', 'point'))
            )
            
            # Create job entry
            job_entry = {
                'job_id': job_id,
                'job_type': AnalyticsJobType.ANOMALY_DETECTION,
                'status': 'running',
                'created_at': datetime.utcnow(),
                'data_points': len(df),
                'config': anomaly_config
            }
            self.active_jobs[job_id] = job_entry
            
            # Detect anomalies
            if request.ensemble_configs:
                # Ensemble detection
                ensemble_configs = [
                    AnomalyConfig(**config) for config in request.ensemble_configs
                ]
                anomaly_result = await self.anomaly_engine.detect_ensemble_anomalies(df, ensemble_configs)
            else:
                # Single method detection
                anomaly_result = await self.anomaly_engine.detect_anomalies(df, anomaly_config)
            
            # Generate visualization
            visualization = await self.anomaly_engine.generate_anomaly_visualization(anomaly_result)
            
            # Complete job
            job_entry['status'] = 'completed'
            job_entry['completed_at'] = datetime.utcnow()
            job_entry['results'] = {
                'anomalies': anomaly_result.anomalies.to_dict(),
                'statistics': anomaly_result.statistics,
                'threshold': anomaly_result.threshold,
                'method_used': anomaly_result.method_name,
                'execution_time': anomaly_result.execution_time,
                'visualization': pio.to_json(visualization)
            }
            
            self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            # Send real-time update
            await self._broadcast_job_update(job_id, 'completed')
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'anomalies_detected': anomaly_result.statistics['anomalies_detected'],
                'anomaly_rate': anomaly_result.statistics['anomaly_rate'],
                'method_used': anomaly_result.method_name,
                'execution_time': anomaly_result.execution_time
            }
            
        except Exception as e:
            # Handle job failure
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = 'failed'
                self.active_jobs[job_id]['error'] = str(e)
                self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'failed')
            
            logger.error(f"Anomaly detection failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analyze_cohorts(self, request: CohortAnalysisRequest) -> Dict[str, Any]:
        """Perform cohort analysis"""
        job_id = str(uuid.uuid4())
        
        try:
            # Create job entry
            job_entry = {
                'job_id': job_id,
                'job_type': AnalyticsJobType.COHORT_ANALYSIS,
                'status': 'running',
                'created_at': datetime.utcnow(),
                'config': request.dict()
            }
            self.active_jobs[job_id] = job_entry
            
            # Convert to DataFrame
            df = pd.DataFrame(request.user_data)
            
            # Perform cohort analysis
            cohort_results = await self._perform_cohort_analysis(df, request)
            
            # Generate visualization
            cohort_viz = await self._generate_cohort_visualization(cohort_results)
            
            # Complete job
            job_entry['status'] = 'completed'
            job_entry['completed_at'] = datetime.utcnow()
            job_entry['results'] = {
                'cohort_table': cohort_results['cohort_table'].to_dict(),
                'cohort_sizes': cohort_results['cohort_sizes'].to_dict(),
                'retention_rates': cohort_results['retention_rates'].to_dict(),
                'summary_stats': cohort_results['summary_stats'],
                'visualization': pio.to_json(cohort_viz)
            }
            
            self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'completed')
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'cohorts_analyzed': len(cohort_results['cohort_table']),
                'average_retention': cohort_results['summary_stats']['average_retention'],
                'cohort_type': request.cohort_type
            }
            
        except Exception as e:
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = 'failed'
                self.active_jobs[job_id]['error'] = str(e)
                self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'failed')
            logger.error(f"Cohort analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analyze_funnel(self, request: FunnelAnalysisRequest) -> Dict[str, Any]:
        """Perform funnel analysis"""
        job_id = str(uuid.uuid4())
        
        try:
            job_entry = {
                'job_id': job_id,
                'job_type': AnalyticsJobType.FUNNEL_ANALYSIS,
                'status': 'running',
                'created_at': datetime.utcnow(),
                'config': request.dict()
            }
            self.active_jobs[job_id] = job_entry
            
            # Convert to DataFrame
            df = pd.DataFrame(request.events_data)
            
            # Perform funnel analysis
            funnel_results = await self._perform_funnel_analysis(df, request)
            
            # Generate visualization
            funnel_viz = await self._generate_funnel_visualization(funnel_results)
            
            # Complete job
            job_entry['status'] = 'completed'
            job_entry['completed_at'] = datetime.utcnow()
            job_entry['results'] = {
                'funnel_data': funnel_results['funnel_data'],
                'conversion_rates': funnel_results['conversion_rates'],
                'drop_off_analysis': funnel_results['drop_off_analysis'],
                'summary_stats': funnel_results['summary_stats'],
                'visualization': pio.to_json(funnel_viz)
            }
            
            self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'completed')
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'funnel_steps': len(request.funnel_steps),
                'overall_conversion': funnel_results['summary_stats']['overall_conversion_rate'],
                'total_users': funnel_results['summary_stats']['total_users_entered']
            }
            
        except Exception as e:
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = 'failed'
                self.active_jobs[job_id]['error'] = str(e)
                self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'failed')
            logger.error(f"Funnel analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analyze_retention(self, request: RetentionAnalysisRequest) -> Dict[str, Any]:
        """Perform retention analysis"""
        job_id = str(uuid.uuid4())
        
        try:
            job_entry = {
                'job_id': job_id,
                'job_type': AnalyticsJobType.RETENTION_ANALYSIS,
                'status': 'running',
                'created_at': datetime.utcnow(),
                'config': request.dict()
            }
            self.active_jobs[job_id] = job_entry
            
            # Convert to DataFrame
            df = pd.DataFrame(request.user_events)
            
            # Perform retention analysis
            retention_results = await self._perform_retention_analysis(df, request)
            
            # Generate visualization
            retention_viz = await self._generate_retention_visualization(retention_results)
            
            # Complete job
            job_entry['status'] = 'completed'
            job_entry['completed_at'] = datetime.utcnow()
            job_entry['results'] = {
                'retention_table': retention_results['retention_table'].to_dict(),
                'retention_curves': retention_results['retention_curves'].to_dict(),
                'cohort_summary': retention_results['cohort_summary'].to_dict(),
                'summary_stats': retention_results['summary_stats'],
                'visualization': pio.to_json(retention_viz)
            }
            
            self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'completed')
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'cohorts_analyzed': len(retention_results['retention_table']),
                'average_retention': retention_results['summary_stats']['average_retention_rate'],
                'period_type': request.period_type
            }
            
        except Exception as e:
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = 'failed'
                self.active_jobs[job_id]['error'] = str(e)
                self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'failed')
            logger.error(f"Retention analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def run_ab_test(self, request: ABTestRequest) -> Dict[str, Any]:
        """Run A/B test analysis"""
        job_id = str(uuid.uuid4())
        
        try:
            job_entry = {
                'job_id': job_id,
                'job_type': AnalyticsJobType.AB_TEST,
                'status': 'running',
                'created_at': datetime.utcnow(),
                'config': request.dict()
            }
            self.active_jobs[job_id] = job_entry
            
            # Convert to DataFrame
            df = pd.DataFrame(request.experiment_data)
            
            # Perform A/B test analysis
            ab_results = await self._perform_ab_test_analysis(df, request)
            
            # Generate visualization
            ab_viz = await self._generate_ab_test_visualization(ab_results)
            
            # Store A/B test results
            test_id = str(uuid.uuid4())
            self.ab_tests[test_id] = ab_results
            
            # Complete job
            job_entry['status'] = 'completed'
            job_entry['completed_at'] = datetime.utcnow()
            job_entry['results'] = {
                'test_id': test_id,
                'group_statistics': ab_results['group_statistics'],
                'statistical_tests': ab_results['statistical_tests'],
                'recommendations': ab_results['recommendations'],
                'visualization': pio.to_json(ab_viz)
            }
            
            self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'completed')
            
            return {
                'job_id': job_id,
                'test_id': test_id,
                'status': 'completed',
                'groups_compared': len(request.treatment_groups) + 1,  # +1 for control
                'is_significant': ab_results['statistical_tests']['is_significant'],
                'recommended_action': ab_results['recommendations']['action']
            }
            
        except Exception as e:
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = 'failed'
                self.active_jobs[job_id]['error'] = str(e)
                self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'failed')
            logger.error(f"A/B test analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_custom_metric(self, request: CustomMetricRequest) -> Dict[str, Any]:
        """Create custom metric definition"""
        metric_id = str(uuid.uuid4())
        
        try:
            # Validate metric configuration
            await self._validate_custom_metric(request)
            
            # Create metric definition
            metric_definition = {
                'metric_id': metric_id,
                'name': request.metric_name,
                'type': request.metric_type,
                'data_source': request.data_source,
                'aggregation_rules': request.aggregation_rules,
                'filters': request.filters,
                'dimensions': request.dimensions,
                'created_at': datetime.utcnow(),
                'status': 'active'
            }
            
            # Store metric
            self.custom_metrics[metric_id] = metric_definition
            
            # Calculate initial value
            initial_value = await self._calculate_custom_metric(metric_definition)
            
            return {
                'metric_id': metric_id,
                'name': request.metric_name,
                'status': 'created',
                'initial_value': initial_value,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Custom metric creation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def train_predictive_model(self, request: PredictiveModelRequest) -> Dict[str, Any]:
        """Train a predictive model"""
        job_id = str(uuid.uuid4())
        
        try:
            # Create job entry
            job_entry = {
                'job_id': job_id,
                'job_type': AnalyticsJobType.PREDICTIVE_MODEL,
                'status': 'running',
                'created_at': datetime.utcnow(),
                'config': request.dict()
            }
            self.active_jobs[job_id] = job_entry
            
            # Convert training data to DataFrame
            training_df = pd.DataFrame(request.training_data)
            
            # Create model configuration
            model_config = ModelConfig(
                model_type=ModelType(request.model_type),
                problem_type=ProblemType(request.problem_type),
                target_column=request.target_column,
                feature_columns=request.feature_columns,
                test_size=request.test_size,
                hyperparameter_tuning=request.hyperparameter_tuning,
                feature_engineering=[FeatureEngineeringType(fe) for fe in request.feature_engineering],
                model_parameters=request.model_parameters
            )
            
            # Train model
            model_result = await self.predictive_engine.train_model(training_df, model_config)
            
            # Store model information
            self.predictive_models[model_result.model_id] = {
                'model_name': request.model_name,
                'model_result': model_result,
                'config': model_config,
                'created_at': datetime.utcnow()
            }
            
            # Complete job
            job_entry['status'] = 'completed'
            job_entry['completed_at'] = datetime.utcnow()
            job_entry['results'] = {
                'model_id': model_result.model_id,
                'model_name': request.model_name,
                'model_type': model_result.model_type,
                'problem_type': model_result.problem_type,
                'training_score': model_result.training_score,
                'validation_score': model_result.validation_score,
                'feature_importance': model_result.feature_importance,
                'metrics': model_result.metrics,
                'training_time': model_result.training_time
            }
            
            self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            # Send real-time update
            await self._broadcast_job_update(job_id, 'completed')
            
            return {
                'job_id': job_id,
                'model_id': model_result.model_id,
                'model_name': request.model_name,
                'status': 'completed',
                'training_score': model_result.training_score,
                'validation_score': model_result.validation_score,
                'training_time': model_result.training_time,
                'model_type': model_result.model_type
            }
            
        except Exception as e:
            # Handle job failure
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = 'failed'
                self.active_jobs[job_id]['error'] = str(e)
                self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
            await self._broadcast_job_update(job_id, 'failed')
            
            logger.error(f"Predictive model training failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def make_prediction(self, request: PredictionRequest) -> Dict[str, Any]:
        """Make predictions using a trained model"""
        try:
            # Convert prediction data to DataFrame
            prediction_df = pd.DataFrame(request.prediction_data)
            
            # Make prediction
            prediction_result = await self.predictive_engine.make_prediction(
                request.model_id, prediction_df
            )
            
            return {
                'success': True,
                'model_id': request.model_id,
                'predictions': prediction_result['predictions'],
                'probabilities': prediction_result.get('probabilities'),
                'prediction_count': prediction_result['prediction_count'],
                'timestamp': prediction_result['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a trained model"""
        try:
            if model_id not in self.predictive_models:
                raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
            
            model_info = self.predictive_models[model_id]
            model_result = model_info['model_result']
            
            return {
                'success': True,
                'model_id': model_id,
                'model_name': model_info['model_name'],
                'model_type': model_result.model_type,
                'problem_type': model_result.problem_type,
                'training_score': model_result.training_score,
                'validation_score': model_result.validation_score,
                'feature_importance': model_result.feature_importance,
                'metrics': model_result.metrics,
                'training_time': model_result.training_time,
                'created_at': model_info['created_at'].isoformat(),
                'cross_validation_scores': model_result.cross_validation_scores
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get model info failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_predictive_models(self) -> Dict[str, Any]:
        """List all trained predictive models"""
        try:
            models_list = [
                {
                    'model_id': model_id,
                    'model_name': info['model_name'],
                    'model_type': info['model_result'].model_type,
                    'problem_type': info['model_result'].problem_type,
                    'validation_score': info['model_result'].validation_score,
                    'created_at': info['created_at'].isoformat()
                }
                for model_id, info in self.predictive_models.items()
            ]
            
            return {
                'success': True,
                'models': models_list,
                'total_models': len(models_list)
            }
            
        except Exception as e:
            logger.error(f"List predictive models failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def export_data(self, request: DataExportRequest) -> Dict[str, Any]:
        """Export data to various formats for BI tools"""
        try:
            # Determine data source
            if request.data_source == "job_results" and request.job_id:
                if request.job_id not in self.completed_jobs:
                    raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found or not completed")
                
                export_data = self.completed_jobs[request.job_id].get('results', {})
                
            elif request.data_source == "custom_data" and request.custom_data:
                export_data = request.custom_data
                
            elif request.data_source == "dashboard_data":
                # Export current platform overview
                export_data = await self.get_analytics_overview()
                
            else:
                raise HTTPException(status_code=400, detail="Invalid data source or missing required data")
            
            # Create export configuration
            export_config = ExportConfig(
                export_format=ExportFormat(request.export_format),
                include_metadata=request.include_metadata,
                include_visualizations=request.include_visualizations,
                **request.export_settings
            )
            
            # Handle BI tool specific exports
            if request.bi_tool:
                bi_tool = BIToolType(request.bi_tool)
                export_result = await self.export_engine.create_bi_dashboard_export(
                    export_data, bi_tool, export_config
                )
            else:
                # Regular data export
                export_result = await self.export_engine.export_data(
                    export_data, export_config, request.filename
                )
            
            # Encode file content as base64 for API response
            file_content_b64 = None
            if export_result.file_content:
                file_content_b64 = base64.b64encode(export_result.file_content).decode('utf-8')
            
            return {
                'success': True,
                'export_id': export_result.export_id,
                'export_format': export_result.export_format,
                'file_size': export_result.file_size,
                'export_time': export_result.export_time,
                'file_content_base64': file_content_b64,
                'metadata': export_result.metadata,
                'filename': export_result.metadata.get('filename')
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Data export failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def export_job_results(self, job_id: str, export_format: str, bi_tool: str = None) -> Dict[str, Any]:
        """Export specific job results"""
        try:
            if job_id not in self.completed_jobs:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found or not completed")
            
            job_results = self.completed_jobs[job_id].get('results', {})
            
            # Create export configuration
            export_config = ExportConfig(
                export_format=ExportFormat(export_format),
                include_metadata=True
            )
            
            if bi_tool:
                bi_tool_type = BIToolType(bi_tool)
                export_result = await self.export_engine.create_bi_dashboard_export(
                    job_results, bi_tool_type, export_config
                )
            else:
                export_result = await self.export_engine.export_analytics_results(
                    job_id, job_results, export_config
                )
            
            # Encode file content as base64
            file_content_b64 = None
            if export_result.file_content:
                file_content_b64 = base64.b64encode(export_result.file_content).decode('utf-8')
            
            return {
                'success': True,
                'export_id': export_result.export_id,
                'job_id': job_id,
                'export_format': export_result.export_format,
                'file_size': export_result.file_size,
                'export_time': export_result.export_time,
                'file_content_base64': file_content_b64,
                'metadata': export_result.metadata
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Job export failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_export_info(self, export_id: str) -> Dict[str, Any]:
        """Get information about an export"""
        try:
            export_result = await self.export_engine.get_export_info(export_id)
            
            if not export_result:
                raise HTTPException(status_code=404, detail=f"Export {export_id} not found")
            
            return {
                'success': True,
                'export_id': export_result.export_id,
                'export_format': export_result.export_format,
                'file_size': export_result.file_size,
                'export_time': export_result.export_time,
                'success': export_result.success,
                'metadata': export_result.metadata,
                'error_message': export_result.error_message
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get export info failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_exports(self, limit: int = 50) -> Dict[str, Any]:
        """List recent exports"""
        try:
            exports_list = await self.export_engine.list_exports(limit)
            
            return {
                'success': True,
                'exports': exports_list,
                'total_exports': len(exports_list)
            }
            
        except Exception as e:
            logger.error(f"List exports failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_report_template(self, request: ReportTemplateRequest) -> Dict[str, Any]:
        """Create a new report template"""
        try:
            template_id = await self.reports_engine.create_report_template(request.dict())
            
            return {
                'success': True,
                'template_id': template_id,
                'name': request.name,
                'analytics_job_type': request.analytics_job_type
            }
            
        except Exception as e:
            logger.error(f"Create report template failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_scheduled_report(self, request: ScheduledReportRequest) -> Dict[str, Any]:
        """Create a new scheduled report"""
        try:
            report_id = await self.reports_engine.create_scheduled_report(request.dict())
            
            return {
                'success': True,
                'report_id': report_id,
                'name': request.name,
                'template_id': request.template_id
            }
            
        except Exception as e:
            logger.error(f"Create scheduled report failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_report_now(self, report_id: str) -> Dict[str, Any]:
        """Execute a report immediately"""
        try:
            execution_id = await self.reports_engine.execute_report(report_id, force=True)
            
            return {
                'success': True,
                'report_id': report_id,
                'execution_id': execution_id,
                'status': 'started'
            }
            
        except Exception as e:
            logger.error(f"Execute report failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_report_info(self, report_id: str) -> Dict[str, Any]:
        """Get information about a scheduled report"""
        try:
            report_info = await self.reports_engine.get_report_info(report_id)
            
            return {
                'success': True,
                **report_info
            }
            
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Get report info failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_scheduled_reports(self, status: Optional[str] = None) -> Dict[str, Any]:
        """List scheduled reports"""
        try:
            reports_list = await self.reports_engine.list_reports(status)
            
            return {
                'success': True,
                'reports': reports_list,
                'total_reports': len(reports_list)
            }
            
        except Exception as e:
            logger.error(f"List scheduled reports failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_report_templates(self) -> Dict[str, Any]:
        """List available report templates"""
        try:
            templates_list = await self.reports_engine.list_templates()
            
            return {
                'success': True,
                'templates': templates_list,
                'total_templates': len(templates_list)
            }
            
        except Exception as e:
            logger.error(f"List report templates failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_execution_info(self, execution_id: str) -> Dict[str, Any]:
        """Get information about a report execution"""
        try:
            execution_info = await self.reports_engine.get_execution_info(execution_id)
            
            return {
                'success': True,
                **execution_info
            }
            
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Get execution info failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def pause_scheduled_report(self, report_id: str) -> Dict[str, Any]:
        """Pause a scheduled report"""
        try:
            success = await self.reports_engine.pause_report(report_id)
            
            if not success:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            
            return {
                'success': True,
                'report_id': report_id,
                'status': 'paused'
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Pause report failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def resume_scheduled_report(self, report_id: str) -> Dict[str, Any]:
        """Resume a paused report"""
        try:
            success = await self.reports_engine.resume_report(report_id)
            
            if not success:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            
            return {
                'success': True,
                'report_id': report_id,
                'status': 'active'
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Resume report failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def delete_scheduled_report(self, report_id: str) -> Dict[str, Any]:
        """Delete a scheduled report"""
        try:
            success = await self.reports_engine.delete_report(report_id)
            
            if not success:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            
            return {
                'success': True,
                'report_id': report_id,
                'status': 'deleted'
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Delete report failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and results"""
        if job_id in self.active_jobs:
            return {
                'job_id': job_id,
                'status': self.active_jobs[job_id]['status'],
                'job_type': self.active_jobs[job_id]['job_type'],
                'created_at': self.active_jobs[job_id]['created_at'].isoformat(),
                'progress': self.active_jobs[job_id].get('progress', 0)
            }
        elif job_id in self.completed_jobs:
            job = self.completed_jobs[job_id]
            return {
                'job_id': job_id,
                'status': job['status'],
                'job_type': job['job_type'],
                'created_at': job['created_at'].isoformat(),
                'completed_at': job.get('completed_at', datetime.utcnow()).isoformat(),
                'results': job.get('results', {}),
                'error': job.get('error')
            }
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    async def get_analytics_overview(self) -> Dict[str, Any]:
        """Get analytics platform overview"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'platform_stats': {
                'active_jobs': len(self.active_jobs),
                'completed_jobs': len(self.completed_jobs),
                'custom_metrics': len(self.custom_metrics),
                'ab_tests': len(self.ab_tests),
                'predictive_models': len(self.predictive_models)
            },
            'job_types': {
                job_type.value: len([
                    j for j in list(self.active_jobs.values()) + list(self.completed_jobs.values())
                    if j['job_type'] == job_type
                ]) for job_type in AnalyticsJobType
            },
            'recent_jobs': [
                {
                    'job_id': job_id,
                    'job_type': job['job_type'],
                    'status': job['status'],
                    'created_at': job['created_at'].isoformat()
                }
                for job_id, job in list(self.completed_jobs.items())[-10:]
            ],
            'predictive_models_summary': [
                {
                    'model_id': model_id,
                    'model_name': info['model_name'],
                    'model_type': info['model_result'].model_type,
                    'validation_score': info['model_result'].validation_score
                }
                for model_id, info in list(self.predictive_models.items())[-5:]
            ]
        }
    
    # Helper methods
    async def _perform_cohort_analysis(self, df: pd.DataFrame, request: CohortAnalysisRequest) -> Dict[str, Any]:
        """Perform cohort analysis logic"""
        # This is a simplified implementation
        # In a real system, this would be much more comprehensive
        
        # Convert dates
        df['event_date'] = pd.to_datetime(df['timestamp'])
        
        # Create cohort periods based on signup date
        if request.cohort_type == 'monthly':
            df['cohort_period'] = df['event_date'].dt.to_period('M')
        elif request.cohort_type == 'weekly':
            df['cohort_period'] = df['event_date'].dt.to_period('W')
        else:  # daily
            df['cohort_period'] = df['event_date'].dt.to_period('D')
        
        # Create cohort table
        cohort_data = df.groupby(['user_id', 'cohort_period']).size().reset_index(name='events')
        cohort_table = cohort_data.pivot_table(
            index='cohort_period',
            columns='user_id',
            values='events',
            fill_value=0
        )
        
        # Calculate cohort sizes
        cohort_sizes = cohort_table.sum(axis=1)
        
        # Calculate retention rates (simplified)
        retention_rates = cohort_table.div(cohort_sizes, axis=0)
        
        # Summary statistics
        summary_stats = {
            'total_cohorts': len(cohort_table),
            'average_cohort_size': float(cohort_sizes.mean()),
            'average_retention': float(retention_rates.mean().mean()),
            'cohort_period': request.cohort_type
        }
        
        return {
            'cohort_table': cohort_table,
            'cohort_sizes': cohort_sizes,
            'retention_rates': retention_rates,
            'summary_stats': summary_stats
        }
    
    async def _generate_cohort_visualization(self, cohort_results: Dict[str, Any]) -> go.Figure:
        """Generate cohort analysis visualization"""
        fig = go.Figure(data=go.Heatmap(
            z=cohort_results['retention_rates'].values,
            x=cohort_results['retention_rates'].columns.astype(str),
            y=cohort_results['retention_rates'].index.astype(str),
            colorscale='Blues'
        ))
        
        fig.update_layout(
            title='Cohort Retention Heatmap',
            xaxis_title='User ID',
            yaxis_title='Cohort Period'
        )
        
        return fig
    
    async def _perform_funnel_analysis(self, df: pd.DataFrame, request: FunnelAnalysisRequest) -> Dict[str, Any]:
        """Perform funnel analysis logic"""
        # Simplified funnel analysis implementation
        funnel_data = {}
        conversion_rates = {}
        
        # Track users through funnel steps
        for i, step in enumerate(request.funnel_steps):
            step_name = step['step_name']
            event_name = step['event_name']
            
            # Count users who completed this step
            step_users = df[df['event_name'] == event_name][request.user_id_column].nunique()
            funnel_data[step_name] = step_users
            
            # Calculate conversion rate from previous step
            if i > 0:
                previous_step = request.funnel_steps[i-1]['step_name']
                conversion_rates[f"{previous_step}_to_{step_name}"] = step_users / funnel_data[previous_step] if funnel_data[previous_step] > 0 else 0
        
        # Calculate drop-off analysis
        drop_off_analysis = {}
        step_names = [step['step_name'] for step in request.funnel_steps]
        
        for i in range(len(step_names) - 1):
            current_step = step_names[i]
            next_step = step_names[i + 1]
            drop_off = funnel_data[current_step] - funnel_data[next_step]
            drop_off_rate = drop_off / funnel_data[current_step] if funnel_data[current_step] > 0 else 0
            
            drop_off_analysis[f"{current_step}_to_{next_step}"] = {
                'dropped_users': drop_off,
                'drop_off_rate': drop_off_rate
            }
        
        # Summary statistics
        first_step = step_names[0]
        last_step = step_names[-1]
        
        summary_stats = {
            'total_steps': len(request.funnel_steps),
            'total_users_entered': funnel_data[first_step],
            'total_users_completed': funnel_data[last_step],
            'overall_conversion_rate': funnel_data[last_step] / funnel_data[first_step] if funnel_data[first_step] > 0 else 0
        }
        
        return {
            'funnel_data': funnel_data,
            'conversion_rates': conversion_rates,
            'drop_off_analysis': drop_off_analysis,
            'summary_stats': summary_stats
        }
    
    async def _generate_funnel_visualization(self, funnel_results: Dict[str, Any]) -> go.Figure:
        """Generate funnel visualization"""
        steps = list(funnel_results['funnel_data'].keys())
        values = list(funnel_results['funnel_data'].values())
        
        fig = go.Figure(go.Funnel(
            y=steps,
            x=values,
            textinfo="value+percent initial"
        ))
        
        fig.update_layout(title="User Journey Funnel Analysis")
        
        return fig
    
    async def _perform_retention_analysis(self, df: pd.DataFrame, request: RetentionAnalysisRequest) -> Dict[str, Any]:
        """Perform retention analysis logic"""
        # Convert date columns
        df[request.cohort_date_column] = pd.to_datetime(df[request.cohort_date_column])
        df[request.activity_date_column] = pd.to_datetime(df[request.activity_date_column])
        
        # Create cohort periods
        if request.period_type == 'monthly':
            df['cohort_period'] = df[request.cohort_date_column].dt.to_period('M')
            df['activity_period'] = df[request.activity_date_column].dt.to_period('M')
        elif request.period_type == 'weekly':
            df['cohort_period'] = df[request.cohort_date_column].dt.to_period('W')
            df['activity_period'] = df[request.activity_date_column].dt.to_period('W')
        else:  # daily
            df['cohort_period'] = df[request.cohort_date_column].dt.to_period('D')
            df['activity_period'] = df[request.activity_date_column].dt.to_period('D')
        
        # Calculate period differences
        df['period_number'] = (df['activity_period'] - df['cohort_period']).apply(attrgetter('n'))
        
        # Create retention table
        retention_table = df.groupby(['cohort_period', 'period_number'])[request.user_id_column].nunique().reset_index()
        retention_table = retention_table.pivot(index='cohort_period', columns='period_number', values=request.user_id_column)
        
        # Calculate cohort sizes (users in period 0)
        cohort_sizes = retention_table.iloc[:, 0]
        
        # Calculate retention rates
        retention_rates = retention_table.divide(cohort_sizes, axis=0)
        
        # Generate retention curves
        retention_curves = retention_rates.mean()
        
        # Cohort summary
        cohort_summary = pd.DataFrame({
            'cohort_size': cohort_sizes,
            'retention_1': retention_rates.iloc[:, 1] if retention_rates.shape[1] > 1 else 0,
            'retention_3': retention_rates.iloc[:, 3] if retention_rates.shape[1] > 3 else 0,
            'retention_6': retention_rates.iloc[:, 6] if retention_rates.shape[1] > 6 else 0
        })
        
        # Summary statistics
        summary_stats = {
            'total_cohorts': len(retention_table),
            'average_cohort_size': float(cohort_sizes.mean()),
            'average_retention_rate': float(retention_rates.mean().mean()),
            'period_type': request.period_type
        }
        
        return {
            'retention_table': retention_table.fillna(0),
            'retention_curves': retention_curves,
            'cohort_summary': cohort_summary,
            'summary_stats': summary_stats
        }
    
    async def _generate_retention_visualization(self, retention_results: Dict[str, Any]) -> go.Figure:
        """Generate retention visualization"""
        fig = go.Figure()
        
        # Add retention curve
        retention_curves = retention_results['retention_curves']
        fig.add_trace(go.Scatter(
            x=list(range(len(retention_curves))),
            y=retention_curves.values,
            mode='lines+markers',
            name='Average Retention Rate'
        ))
        
        fig.update_layout(
            title='User Retention Curve',
            xaxis_title='Period',
            yaxis_title='Retention Rate',
            yaxis=dict(tickformat='.2%')
        )
        
        return fig
    
    async def _perform_ab_test_analysis(self, df: pd.DataFrame, request: ABTestRequest) -> Dict[str, Any]:
        """Perform A/B test statistical analysis"""
        from scipy import stats
        
        # Group statistics
        group_stats = {}
        all_groups = [request.control_group] + request.treatment_groups
        
        for group in all_groups:
            group_data = df[df['group'] == group][request.metric_column]
            group_stats[group] = {
                'count': len(group_data),
                'mean': float(group_data.mean()),
                'std': float(group_data.std()),
                'median': float(group_data.median()),
                'min': float(group_data.min()),
                'max': float(group_data.max())
            }
        
        # Statistical tests
        control_data = df[df['group'] == request.control_group][request.metric_column]
        
        test_results = {}
        for treatment_group in request.treatment_groups:
            treatment_data = df[df['group'] == treatment_group][request.metric_column]
            
            # T-test
            t_stat, p_value = stats.ttest_ind(control_data, treatment_data)
            
            # Effect size (Cohen's d)
            pooled_std = np.sqrt(((len(control_data) - 1) * control_data.std()**2 + 
                                 (len(treatment_data) - 1) * treatment_data.std()**2) / 
                                (len(control_data) + len(treatment_data) - 2))
            cohens_d = (treatment_data.mean() - control_data.mean()) / pooled_std
            
            test_results[f"{request.control_group}_vs_{treatment_group}"] = {
                't_statistic': float(t_stat),
                'p_value': float(p_value),
                'is_significant': p_value < (1 - request.confidence_level),
                'cohens_d': float(cohens_d),
                'effect_size': 'small' if abs(cohens_d) < 0.5 else 'medium' if abs(cohens_d) < 0.8 else 'large'
            }
        
        # Recommendations
        best_group = max(group_stats.keys(), key=lambda x: group_stats[x]['mean'])
        is_significant = any(test['is_significant'] for test in test_results.values())
        
        recommendations = {
            'action': 'implement' if is_significant and best_group != request.control_group else 'no_change',
            'best_performing_group': best_group,
            'confidence_level': request.confidence_level,
            'sample_size_adequate': all(group_stats[g]['count'] >= 30 for g in group_stats),
            'notes': []
        }
        
        return {
            'group_statistics': group_stats,
            'statistical_tests': {
                'results': test_results,
                'is_significant': is_significant,
                'confidence_level': request.confidence_level
            },
            'recommendations': recommendations
        }
    
    async def _generate_ab_test_visualization(self, ab_results: Dict[str, Any]) -> go.Figure:
        """Generate A/B test visualization"""
        fig = go.Figure()
        
        groups = list(ab_results['group_statistics'].keys())
        means = [ab_results['group_statistics'][g]['mean'] for g in groups]
        stds = [ab_results['group_statistics'][g]['std'] for g in groups]
        
        fig.add_trace(go.Bar(
            x=groups,
            y=means,
            error_y=dict(type='data', array=stds),
            name='Group Means'
        ))
        
        fig.update_layout(
            title='A/B Test Results - Group Comparison',
            xaxis_title='Groups',
            yaxis_title='Metric Value'
        )
        
        return fig
    
    async def _validate_custom_metric(self, request: CustomMetricRequest) -> bool:
        """Validate custom metric configuration"""
        # Basic validation logic
        if not request.metric_name or not request.metric_type:
            raise ValueError("Metric name and type are required")
        
        if request.metric_type not in [mt.value for mt in MetricType]:
            raise ValueError(f"Invalid metric type: {request.metric_type}")
        
        return True
    
    async def _calculate_custom_metric(self, metric_definition: Dict[str, Any]) -> float:
        """Calculate custom metric value"""
        # Simplified calculation - in real implementation, 
        # this would connect to actual data sources
        return 42.0  # Placeholder value
    
    async def _broadcast_job_update(self, job_id: str, status: str):
        """Broadcast job status update to WebSocket connections"""
        message = {
            'type': 'job_update',
            'job_id': job_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send to all connected clients
        for connection in self.websocket_connections.values():
            try:
                await connection.send_json(message)
            except:
                pass  # Connection may have closed
    
    async def handle_websocket_connection(self, websocket: WebSocket, client_id: str):
        """Handle WebSocket connection for real-time updates"""
        await websocket.accept()
        self.websocket_connections[client_id] = websocket
        
        try:
            while True:
                # Keep connection alive
                await websocket.receive_text()
        except:
            pass
        finally:
            if client_id in self.websocket_connections:
                del self.websocket_connections[client_id]

# FastAPI App
app = FastAPI(
    title="Analytics Platform Service",
    description="Comprehensive analytics platform with forecasting, anomaly detection, and advanced analytics",
    version="1.0.0"
)

service = AnalyticsPlatformService()

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "analytics-platform",
        "timestamp": datetime.utcnow().isoformat(),
        "active_jobs": len(service.active_jobs),
        "completed_jobs": len(service.completed_jobs),
        "custom_metrics": len(service.custom_metrics)
    }

# Time Series and Forecasting endpoints
@app.post("/api/analytics/forecast")
async def create_forecast(request: TimeSeriesForecastRequest):
    result = await service.create_time_series_forecast(request)
    return {"success": True, **result}

# Anomaly Detection endpoints
@app.post("/api/analytics/anomaly-detection")
async def detect_anomalies(request: AnomalyDetectionRequest):
    result = await service.detect_anomalies(request)
    return {"success": True, **result}

# Cohort Analysis endpoints
@app.post("/api/analytics/cohort-analysis")
async def analyze_cohorts(request: CohortAnalysisRequest):
    result = await service.analyze_cohorts(request)
    return {"success": True, **result}

# Funnel Analysis endpoints
@app.post("/api/analytics/funnel-analysis")
async def analyze_funnel(request: FunnelAnalysisRequest):
    result = await service.analyze_funnel(request)
    return {"success": True, **result}

# Retention Analysis endpoints
@app.post("/api/analytics/retention-analysis")
async def analyze_retention(request: RetentionAnalysisRequest):
    result = await service.analyze_retention(request)
    return {"success": True, **result}

# A/B Testing endpoints
@app.post("/api/analytics/ab-test")
async def run_ab_test(request: ABTestRequest):
    result = await service.run_ab_test(request)
    return {"success": True, **result}

# Custom Metrics endpoints
@app.post("/api/analytics/custom-metrics")
async def create_custom_metric(request: CustomMetricRequest):
    result = await service.create_custom_metric(request)
    return {"success": True, **result}

@app.get("/api/analytics/custom-metrics")
async def list_custom_metrics():
    return {
        "success": True,
        "metrics": list(service.custom_metrics.keys()),
        "total": len(service.custom_metrics)
    }

# Predictive Models endpoints
@app.post("/api/analytics/predictive-models/train")
async def train_predictive_model(request: PredictiveModelRequest):
    result = await service.train_predictive_model(request)
    return result

@app.post("/api/analytics/predictive-models/predict")
async def make_prediction(request: PredictionRequest):
    result = await service.make_prediction(request)
    return result

@app.get("/api/analytics/predictive-models/{model_id}")
async def get_predictive_model_info(model_id: str):
    result = await service.get_model_info(model_id)
    return result

@app.get("/api/analytics/predictive-models")
async def list_predictive_models():
    result = await service.list_predictive_models()
    return result

# Data Export endpoints
@app.post("/api/analytics/export")
async def export_data(request: DataExportRequest):
    result = await service.export_data(request)
    return result

@app.get("/api/analytics/export/job/{job_id}")
async def export_job_results(job_id: str, export_format: str, bi_tool: str = None):
    result = await service.export_job_results(job_id, export_format, bi_tool)
    return result

@app.get("/api/analytics/export/{export_id}")
async def get_export_info(export_id: str):
    result = await service.get_export_info(export_id)
    return result

@app.get("/api/analytics/exports")
async def list_exports(limit: int = 50):
    result = await service.list_exports(limit)
    return result

# Scheduled Reports endpoints
@app.post("/api/analytics/reports/templates")
async def create_report_template(request: ReportTemplateRequest):
    result = await service.create_report_template(request)
    return result

@app.post("/api/analytics/reports/scheduled")
async def create_scheduled_report(request: ScheduledReportRequest):
    result = await service.create_scheduled_report(request)
    return result

@app.post("/api/analytics/reports/scheduled/{report_id}/execute")
async def execute_report_now(report_id: str):
    result = await service.execute_report_now(report_id)
    return result

@app.get("/api/analytics/reports/scheduled/{report_id}")
async def get_scheduled_report_info(report_id: str):
    result = await service.get_report_info(report_id)
    return result

@app.get("/api/analytics/reports/scheduled")
async def list_scheduled_reports(status: Optional[str] = None):
    result = await service.list_scheduled_reports(status)
    return result

@app.get("/api/analytics/reports/templates")
async def list_report_templates():
    result = await service.list_report_templates()
    return result

@app.get("/api/analytics/reports/executions/{execution_id}")
async def get_report_execution_info(execution_id: str):
    result = await service.get_execution_info(execution_id)
    return result

@app.post("/api/analytics/reports/scheduled/{report_id}/pause")
async def pause_scheduled_report(report_id: str):
    result = await service.pause_scheduled_report(report_id)
    return result

@app.post("/api/analytics/reports/scheduled/{report_id}/resume")
async def resume_scheduled_report(report_id: str):
    result = await service.resume_scheduled_report(report_id)
    return result

@app.delete("/api/analytics/reports/scheduled/{report_id}")
async def delete_scheduled_report(report_id: str):
    result = await service.delete_scheduled_report(report_id)
    return result

# Job Management endpoints
@app.get("/api/analytics/jobs/{job_id}")
async def get_job_status(job_id: str):
    result = await service.get_job_status(job_id)
    return {"success": True, **result}

@app.get("/api/analytics/jobs")
async def list_jobs():
    active_jobs = list(service.active_jobs.keys())
    completed_jobs = list(service.completed_jobs.keys())
    
    return {
        "success": True,
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs[-20:],  # Last 20
        "total_active": len(active_jobs),
        "total_completed": len(completed_jobs)
    }

# Dashboard and Overview endpoints
@app.get("/api/analytics/overview")
async def get_analytics_overview():
    result = await service.get_analytics_overview()
    return {"success": True, **result}

# Real-time WebSocket endpoint
@app.websocket("/ws/analytics/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await service.handle_websocket_connection(websocket, client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8104)

# Import for attribute access in retention analysis
from operator import attrgetter