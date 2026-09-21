from aiohttp import web, web_request, web_response
from aiohttp.web_middlewares import middleware
import aiohttp_cors
import json
import asyncio
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
import numpy as np
import pickle
import sys
import os

# Add the ml-platform directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from registry.model_registry import ModelRegistry, ModelMetadata, ModelVersion
from testing.ab_testing import ABTestManager, Experiment, ExperimentVariant
from monitoring.performance_monitoring import PerformanceMonitor, ModelHealthCheck
from pipelines.retraining_pipeline import RetrainingPipeline, RetrainingConfig, TriggerType
from feature_store.feature_store import FeatureStore, FeatureGroup, FeatureSchema, FeatureType
from explainability.model_explainer import ModelExplainer, ExplanationType
from drift.drift_detector import DriftMonitor, DriftType
from governance.model_governance import ModelGovernance


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLPlatformServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8109, db_path: str = "ml_platform.db"):
        self.host = host
        self.port = port
        self.db_path = db_path
        
        # Initialize components
        self.model_registry = ModelRegistry(db_path)
        self.ab_test_manager = ABTestManager(db_path)
        self.performance_monitor = PerformanceMonitor(db_path)
        self.health_checker = ModelHealthCheck(self.performance_monitor)
        self.retraining_pipeline = RetrainingPipeline(db_path)
        self.feature_store = FeatureStore(db_path)
        self.model_explainer = ModelExplainer(db_path)
        self.drift_monitor = DriftMonitor(db_path)
        self.governance = ModelGovernance(db_path)
        
        # Start background services
        self.performance_monitor.start_monitoring()
        self.retraining_pipeline.start_scheduler()
        
        self.app = web.Application(middlewares=[self.error_middleware])
        self._setup_routes()
        self._setup_cors()
    
    @middleware
    async def error_middleware(self, request: web_request.Request, handler):
        try:
            response = await handler(request)
            return response
        except Exception as e:
            logger.error(f"Error handling request {request.path}: {str(e)}")
            logger.error(traceback.format_exc())
            return web.json_response({
                "error": str(e),
                "status": "error"
            }, status=500)
    
    def _setup_cors(self):
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def _setup_routes(self):
        # Health check
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/", self.root)
        
        # Model Registry endpoints
        self.app.router.add_post("/models", self.register_model)
        self.app.router.add_get("/models", self.list_models)
        self.app.router.add_get("/models/{model_id}", self.get_model)
        self.app.router.add_get("/models/{model_id}/versions", self.get_model_versions)
        self.app.router.add_post("/models/{model_id}/versions/{version}/promote", self.promote_model)
        self.app.router.add_post("/models/{model_id}/predict", self.predict)
        
        # A/B Testing endpoints
        self.app.router.add_post("/experiments", self.create_experiment)
        self.app.router.add_get("/experiments", self.list_experiments)
        self.app.router.add_get("/experiments/{experiment_id}", self.get_experiment)
        self.app.router.add_post("/experiments/{experiment_id}/start", self.start_experiment)
        self.app.router.add_post("/experiments/{experiment_id}/stop", self.stop_experiment)
        self.app.router.add_post("/experiments/{experiment_id}/assign", self.assign_variant)
        self.app.router.add_post("/experiments/{experiment_id}/event", self.record_experiment_event)
        
        # Performance Monitoring endpoints
        self.app.router.add_get("/models/{model_id}/health", self.get_model_health)
        self.app.router.add_get("/models/{model_id}/metrics", self.get_model_metrics)
        self.app.router.add_post("/models/{model_id}/metrics", self.record_model_metric)
        self.app.router.add_get("/monitoring/alerts", self.get_alerts)
        
        # Retraining Pipeline endpoints
        self.app.router.add_post("/models/{model_id}/retraining", self.configure_retraining)
        self.app.router.add_post("/models/{model_id}/trigger-retraining", self.trigger_retraining)
        self.app.router.add_get("/retraining/runs", self.get_retraining_runs)
        self.app.router.add_get("/retraining/runs/{run_id}", self.get_retraining_run)
        
        # Feature Store endpoints
        self.app.router.add_post("/feature-groups", self.create_feature_group)
        self.app.router.add_post("/feature-groups/{group_id}/ingest", self.ingest_features)
        self.app.router.add_get("/feature-groups/{group_id}/features", self.get_features)
        self.app.router.add_get("/features/online", self.get_online_features)
        
        # Explainability endpoints
        self.app.router.add_post("/models/{model_id}/explain", self.explain_prediction)
        self.app.router.add_get("/models/{model_id}/explanations", self.get_explanations)
        self.app.router.add_get("/models/{model_id}/explanation-report", self.get_explanation_report)
        
        # Drift Detection endpoints
        self.app.router.add_post("/models/{model_id}/drift/check", self.check_drift)
        self.app.router.add_get("/models/{model_id}/drift/history", self.get_drift_history)
        self.app.router.add_get("/drift/alerts", self.get_drift_alerts)
        
        # Governance endpoints
        self.app.router.add_post("/models/{model_id}/governance/evaluate", self.evaluate_governance)
        self.app.router.add_post("/models/{model_id}/approval", self.request_approval)
        self.app.router.add_post("/approvals/{request_id}/approve", self.approve_request)
        self.app.router.add_post("/approvals/{request_id}/reject", self.reject_request)
        self.app.router.add_get("/governance/dashboard", self.get_governance_dashboard)
        
        # General endpoints
        self.app.router.add_get("/dashboard", self.get_dashboard)
    
    # Health and status endpoints
    async def health_check(self, request: web_request.Request) -> web_response.Response:
        return web.json_response({"status": "healthy", "timestamp": datetime.now().isoformat()})
    
    async def root(self, request: web_request.Request) -> web_response.Response:
        return web.json_response({
            "message": "ML Platform API",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        })
    
    # Model Registry endpoints
    async def register_model(self, request: web_request.Request) -> web_response.Response:
        data = await request.json()
        
        # Create model metadata
        metadata = ModelMetadata(
            model_id=data.get("model_id"),
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            format=data.get("format", "pickle"),
            tags=data.get("tags", []),
            stage="development"
        )
        
        # For demo purposes, create a simple model if not provided
        if "model_data" in data:
            model = pickle.loads(bytes.fromhex(data["model_data"]))
        else:
            # Create dummy model
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(n_estimators=10)
        
        model_id = self.model_registry.register_model(model, metadata)
        
        return web.json_response({"model_id": model_id, "status": "registered"})
    
    async def list_models(self, request: web_request.Request) -> web_response.Response:
        models = self.model_registry.list_models()
        return web.json_response({"models": models})
    
    async def get_model(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        model_info = self.model_registry.get_model_info(model_id)
        
        if not model_info:
            return web.json_response({"error": "Model not found"}, status=404)
        
        return web.json_response({"model": model_info})
    
    async def get_model_versions(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        versions = self.model_registry.list_model_versions(model_id)
        return web.json_response({"versions": versions})
    
    async def promote_model(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        version = request.match_info["version"]
        data = await request.json()
        
        new_stage = data.get("stage", "production")
        success = self.model_registry.update_model_stage(model_id, version, new_stage)
        
        if success:
            return web.json_response({"status": "promoted", "new_stage": new_stage})
        else:
            return web.json_response({"error": "Failed to promote model"}, status=400)
    
    async def predict(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        data = await request.json()
        
        # Get model
        model = self.model_registry.load_model(model_id, data.get("version"))
        if not model:
            return web.json_response({"error": "Model not found"}, status=404)
        
        # Make prediction
        features = np.array(data["features"])
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
        
        prediction = model.predict(features)
        
        # Record metrics if monitoring enabled
        if data.get("record_metrics", True):
            latency = 50  # Simulate latency
            self.performance_monitor.record_inference_metrics(
                model_id, data.get("version", "latest"), latency, prediction[0]
            )
        
        return web.json_response({
            "prediction": prediction.tolist(),
            "model_id": model_id,
            "version": data.get("version", "latest")
        })
    
    # A/B Testing endpoints
    async def create_experiment(self, request: web_request.Request) -> web_response.Response:
        data = await request.json()
        
        # Create variants
        variants = []
        for variant_data in data["variants"]:
            variant = ExperimentVariant(
                variant_id=variant_data["variant_id"],
                name=variant_data["name"],
                model_id=variant_data["model_id"],
                model_version=variant_data["model_version"],
                traffic_allocation=variant_data["traffic_allocation"]
            )
            variants.append(variant)
        
        experiment = Experiment(
            experiment_id=data["experiment_id"],
            name=data["name"],
            description=data.get("description", ""),
            variants=variants,
            traffic_split_strategy=data.get("traffic_split_strategy", "random"),
            success_metric=data["success_metric"]
        )
        
        experiment_id = self.ab_test_manager.create_experiment(experiment)
        return web.json_response({"experiment_id": experiment_id, "status": "created"})
    
    async def list_experiments(self, request: web_request.Request) -> web_response.Response:
        experiments = self.ab_test_manager.list_experiments()
        return web.json_response({"experiments": experiments})
    
    async def get_experiment(self, request: web_request.Request) -> web_response.Response:
        experiment_id = request.match_info["experiment_id"]
        experiment = self.ab_test_manager.get_experiment(experiment_id)
        
        if not experiment:
            return web.json_response({"error": "Experiment not found"}, status=404)
        
        return web.json_response({"experiment": experiment})
    
    async def start_experiment(self, request: web_request.Request) -> web_response.Response:
        experiment_id = request.match_info["experiment_id"]
        success = self.ab_test_manager.start_experiment(experiment_id)
        
        return web.json_response({"status": "started" if success else "failed"})
    
    async def stop_experiment(self, request: web_request.Request) -> web_response.Response:
        experiment_id = request.match_info["experiment_id"]
        success = self.ab_test_manager.stop_experiment(experiment_id)
        
        return web.json_response({"status": "stopped" if success else "failed"})
    
    async def assign_variant(self, request: web_request.Request) -> web_response.Response:
        experiment_id = request.match_info["experiment_id"]
        data = await request.json()
        
        variant_id = self.ab_test_manager.assign_variant(experiment_id, data["user_id"])
        return web.json_response({"variant_id": variant_id})
    
    async def record_experiment_event(self, request: web_request.Request) -> web_response.Response:
        experiment_id = request.match_info["experiment_id"]
        data = await request.json()
        
        success = self.ab_test_manager.record_event(
            experiment_id, data["user_id"], data["event_type"], data.get("value")
        )
        
        return web.json_response({"status": "recorded" if success else "failed"})
    
    # Performance Monitoring endpoints
    async def get_model_health(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        version = request.query.get("version", "latest")
        
        health = self.health_checker.check_model_health(model_id, version)
        return web.json_response(health)
    
    async def get_model_metrics(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        version = request.query.get("version", "latest")
        hours = int(request.query.get("hours", 24))
        
        summary = self.performance_monitor.get_model_summary(model_id, version, hours)
        return web.json_response(summary)
    
    async def record_model_metric(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        data = await request.json()
        
        self.performance_monitor.record_metric(
            model_id,
            data.get("version", "latest"),
            data["metric_name"],
            data["value"],
            data.get("metadata")
        )
        
        return web.json_response({"status": "recorded"})
    
    async def get_alerts(self, request: web_request.Request) -> web_response.Response:
        model_id = request.query.get("model_id")
        severity = request.query.get("severity")
        
        alerts = self.performance_monitor.get_active_alerts(model_id, severity)
        
        alert_data = []
        for alert in alerts:
            alert_data.append({
                "alert_id": alert.alert_id,
                "model_id": alert.model_id,
                "model_version": alert.model_version,
                "metric_name": alert.metric_name,
                "threshold": alert.threshold,
                "current_value": alert.current_value,
                "severity": alert.severity,
                "timestamp": alert.timestamp.isoformat(),
                "message": alert.message
            })
        
        return web.json_response({"alerts": alert_data})
    
    # Retraining Pipeline endpoints
    async def configure_retraining(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        data = await request.json()
        
        config = RetrainingConfig(
            model_id=model_id,
            model_version=data["model_version"],
            trigger_type=TriggerType(data["trigger_type"]),
            schedule_cron=data.get("schedule_cron"),
            performance_threshold=data.get("performance_threshold"),
            min_samples_required=data.get("min_samples_required", 100),
            auto_deploy=data.get("auto_deploy", False)
        )
        
        self.retraining_pipeline.add_retraining_config(config)
        return web.json_response({"status": "configured"})
    
    async def trigger_retraining(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        data = await request.json()
        
        run_id = self.retraining_pipeline.trigger_retraining(
            model_id,
            data["model_version"],
            data.get("trigger_reason", "manual")
        )
        
        return web.json_response({"run_id": run_id, "status": "triggered"})
    
    async def get_retraining_runs(self, request: web_request.Request) -> web_response.Response:
        model_id = request.query.get("model_id")
        limit = int(request.query.get("limit", 50))
        
        runs = self.retraining_pipeline.get_recent_runs(model_id, limit)
        
        run_data = []
        for run in runs:
            run_data.append({
                "run_id": run.run_id,
                "model_id": run.config.model_id if run.config else None,
                "model_version": run.config.model_version if run.config else None,
                "status": run.status.value,
                "start_time": run.start_time.isoformat(),
                "end_time": run.end_time.isoformat() if run.end_time else None,
                "trigger_reason": run.trigger_reason,
                "metrics": run.metrics
            })
        
        return web.json_response({"runs": run_data})
    
    async def get_retraining_run(self, request: web_request.Request) -> web_response.Response:
        run_id = request.match_info["run_id"]
        run = self.retraining_pipeline.get_pipeline_run(run_id)
        
        if not run:
            return web.json_response({"error": "Run not found"}, status=404)
        
        return web.json_response({
            "run_id": run.run_id,
            "status": run.status.value,
            "start_time": run.start_time.isoformat(),
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "trigger_reason": run.trigger_reason,
            "metrics": run.metrics,
            "logs": run.logs,
            "error_message": run.error_message
        })
    
    # Feature Store endpoints
    async def create_feature_group(self, request: web_request.Request) -> web_response.Response:
        data = await request.json()
        
        # Create features
        features = []
        for feature_data in data["features"]:
            feature = FeatureSchema(
                feature_name=feature_data["feature_name"],
                feature_type=FeatureType(feature_data["feature_type"]),
                description=feature_data["description"]
            )
            features.append(feature)
        
        feature_group = FeatureGroup(
            group_id=data["group_id"],
            group_name=data["group_name"],
            description=data["description"],
            features=features,
            primary_keys=data["primary_keys"],
            event_timestamp_column=data["event_timestamp_column"]
        )
        
        success = self.feature_store.create_feature_group(feature_group)
        return web.json_response({"status": "created" if success else "failed"})
    
    async def ingest_features(self, request: web_request.Request) -> web_response.Response:
        group_id = request.match_info["group_id"]
        data = await request.json()
        
        success = self.feature_store.ingest_features(
            group_id,
            data["data"],
            data.get("entity_id")
        )
        
        return web.json_response({"status": "ingested" if success else "failed"})
    
    async def get_features(self, request: web_request.Request) -> web_response.Response:
        group_id = request.match_info["group_id"]
        entity_ids = request.query.get("entity_ids", "").split(",")
        
        if not entity_ids or entity_ids == [""]:
            return web.json_response({"error": "entity_ids required"}, status=400)
        
        features = self.feature_store.get_features(group_id, entity_ids)
        
        # Convert datetime objects to strings for JSON serialization
        serialized_features = {}
        for entity_id, entity_features in features.items():
            serialized_features[entity_id] = {}
            for feature_name, feature_data in entity_features.items():
                serialized_features[entity_id][feature_name] = {
                    "value": feature_data["value"],
                    "timestamp": feature_data["timestamp"].isoformat()
                }
        
        return web.json_response({"features": serialized_features})
    
    async def get_online_features(self, request: web_request.Request) -> web_response.Response:
        service_name = request.query.get("service", "default")
        entity_ids = request.query.get("entity_ids", "").split(",")
        
        if not entity_ids or entity_ids == [""]:
            return web.json_response({"error": "entity_ids required"}, status=400)
        
        features = self.feature_store.get_online_features(service_name, entity_ids)
        return web.json_response({"features": features})
    
    # Explainability endpoints
    async def explain_prediction(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        data = await request.json()
        
        # Load model and register with explainer if not already registered
        model = self.model_registry.load_model(model_id, data.get("version"))
        if not model:
            return web.json_response({"error": "Model not found"}, status=404)
        
        features = np.array(data["features"])
        feature_names = data.get("feature_names", [f"feature_{i}" for i in range(len(features))])
        
        # Register model with explainer
        self.model_explainer.register_model(
            model_id, data.get("version", "latest"), model, feature_names
        )
        
        # Get explanation types from request
        explanation_types = [ExplanationType(t) for t in data.get("explanation_types", ["feature_importance"])]
        
        explanations = self.model_explainer.explain_instance(
            model_id, data.get("version", "latest"), features, explanation_types
        )
        
        # Convert to serializable format
        result = {}
        for exp_type, explanation in explanations.items():
            result[exp_type.value] = {
                "explanation_data": explanation.explanation_data,
                "prediction": explanation.prediction,
                "timestamp": explanation.timestamp.isoformat()
            }
        
        return web.json_response({"explanations": result})
    
    async def get_explanations(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        version = request.query.get("version", "latest")
        
        explanations = self.model_explainer.get_explanations(model_id, version)
        
        result = []
        for explanation in explanations:
            result.append({
                "instance_id": explanation.instance_id,
                "explanation_type": explanation.explanation_type.value,
                "explanation_data": explanation.explanation_data,
                "timestamp": explanation.timestamp.isoformat()
            })
        
        return web.json_response({"explanations": result})
    
    async def get_explanation_report(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        version = request.query.get("version", "latest")
        
        report = self.model_explainer.generate_explanation_report(model_id, version)
        return web.json_response(report)
    
    # Drift Detection endpoints
    async def check_drift(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        data = await request.json()
        
        version = data.get("version", "latest")
        current_data = np.array(data["current_data"])
        
        drift_results = self.drift_monitor.check_drift(
            model_id, version, current_data=current_data
        )
        
        # Convert to serializable format
        result = {}
        for drift_type, report in drift_results.items():
            result[drift_type] = {
                "drift_type": report.drift_type.value,
                "overall_drift_score": report.overall_drift_score,
                "is_drifting": report.is_drifting,
                "detected_features": report.detected_features,
                "generated_at": report.generated_at.isoformat()
            }
        
        return web.json_response({"drift_results": result})
    
    async def get_drift_history(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        version = request.query.get("version", "latest")
        days = int(request.query.get("days", 30))
        
        history = self.drift_monitor.get_drift_history(model_id, version, days=days)
        return web.json_response({"history": history})
    
    async def get_drift_alerts(self, request: web_request.Request) -> web_response.Response:
        model_id = request.query.get("model_id")
        
        alerts = self.drift_monitor.get_active_alerts(model_id)
        
        alert_data = []
        for alert in alerts:
            alert_data.append({
                "alert_id": alert.alert_id,
                "model_id": alert.model_id,
                "drift_type": alert.drift_type.value,
                "severity": alert.severity.value,
                "drift_score": alert.drift_score,
                "feature_name": alert.feature_name,
                "detected_at": alert.detected_at.isoformat(),
                "description": alert.description
            })
        
        return web.json_response({"alerts": alert_data})
    
    # Governance endpoints
    async def evaluate_governance(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        data = await request.json()
        
        result = self.governance.evaluate_model_governance(
            model_id,
            data["model_version"],
            data["model_metadata"],
            data["user_id"]
        )
        
        return web.json_response({
            "compliance_status": result["compliance_report"].compliance_status.value,
            "violations": result["compliance_report"].violations,
            "recommendations": result["governance_recommendations"],
            "required_actions": result["required_actions"]
        })
    
    async def request_approval(self, request: web_request.Request) -> web_response.Response:
        model_id = request.match_info["model_id"]
        data = await request.json()
        
        approval_request = self.governance.request_deployment_approval(
            model_id,
            data["model_version"],
            data["model_metadata"],
            data["requested_by"]
        )
        
        return web.json_response({
            "request_id": approval_request.request_id,
            "required_approvers": approval_request.required_approvers,
            "status": approval_request.status.value
        })
    
    async def approve_request(self, request: web_request.Request) -> web_response.Response:
        request_id = request.match_info["request_id"]
        data = await request.json()
        
        success = self.governance.approval_workflow.approve_request(
            request_id, data["approver"], data.get("comments", "")
        )
        
        return web.json_response({"status": "approved" if success else "failed"})
    
    async def reject_request(self, request: web_request.Request) -> web_response.Response:
        request_id = request.match_info["request_id"]
        data = await request.json()
        
        success = self.governance.approval_workflow.reject_request(
            request_id, data["approver"], data.get("comments", "")
        )
        
        return web.json_response({"status": "rejected" if success else "failed"})
    
    async def get_governance_dashboard(self, request: web_request.Request) -> web_response.Response:
        user_id = request.query.get("user_id", "default")
        
        dashboard = self.governance.get_governance_dashboard(user_id)
        return web.json_response(dashboard)
    
    # General dashboard endpoint
    async def get_dashboard(self, request: web_request.Request) -> web_response.Response:
        # Get summary statistics from all components
        models = self.model_registry.list_models()
        experiments = self.ab_test_manager.list_experiments()
        
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "total_models": len(models),
            "total_experiments": len(experiments),
            "active_experiments": len([e for e in experiments if e.get("status") == "running"]),
            "models": models[:5],  # Latest 5 models
            "recent_experiments": experiments[:5]  # Latest 5 experiments
        }
        
        return web.json_response(dashboard_data)
    
    def run(self):
        """Start the ML platform server"""
        logger.info(f"Starting ML Platform Server on {self.host}:{self.port}")
        web.run_app(self.app, host=self.host, port=self.port)


async def init_app():
    """Initialize the application"""
    server = MLPlatformServer()
    return server.app


if __name__ == "__main__":
    server = MLPlatformServer()
    server.run()