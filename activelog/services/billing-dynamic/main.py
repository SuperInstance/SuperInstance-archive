"""
ActiveLog Dynamic Billing System - Main Service
Pay-by-minute billing with dynamic scaling and cost optimization
Port 8475
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import aiohttp
from aiohttp import web, ClientSession
import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

# Local imports
from billing.billing_engine import MinuteLevelBillingEngine
from tracking.usage_tracker import ResourceUsageTracker
from scaling.dynamic_scaler import DynamicScalingManager
from prediction.cost_predictor import CostPredictionEngine
from alerts.notification_manager import BillingAlertManager
from payment.payment_processor import PaymentIntegrationSystem
from analytics.usage_analytics import UsageAnalyticsDashboard
from policies.scaling_policies import AutomatedScalingPolicies

class BillingSystemState:
    def __init__(self):
        # Core components
        self.billing_engine: Optional[MinuteLevelBillingEngine] = None
        self.usage_tracker: Optional[ResourceUsageTracker] = None
        self.dynamic_scaler: Optional[DynamicScalingManager] = None
        self.cost_predictor: Optional[CostPredictionEngine] = None
        self.alert_manager: Optional[BillingAlertManager] = None
        self.payment_processor: Optional[PaymentIntegrationSystem] = None
        self.analytics_dashboard: Optional[UsageAnalyticsDashboard] = None
        self.scaling_policies: Optional[AutomatedScalingPolicies] = None
        
        # System state
        self.redis_client: Optional[redis.Redis] = None
        self.background_tasks: Set[asyncio.Task] = set()
        self.is_initialized = False
        self.logger = logging.getLogger(__name__)

# Global state
billing_state = BillingSystemState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    await startup_billing_system()
    try:
        yield
    finally:
        # Shutdown
        await shutdown_billing_system()

# FastAPI application
app = FastAPI(
    title="ActiveLog Dynamic Billing System",
    description="Pay-by-minute billing with dynamic scaling and cost optimization",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def startup_billing_system():
    """Initialize all billing system components"""
    try:
        billing_state.logger.info("Starting Dynamic Billing System...")
        
        # Initialize Redis connection
        try:
            billing_state.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
            await billing_state.redis_client.ping()
            billing_state.logger.info("Redis connection established")
        except Exception as e:
            billing_state.logger.warning(f"Redis connection failed: {e}")
        
        # Initialize core components
        billing_state.billing_engine = MinuteLevelBillingEngine(billing_state.redis_client)
        billing_state.usage_tracker = ResourceUsageTracker(billing_state.redis_client)
        billing_state.dynamic_scaler = DynamicScalingManager(billing_state.redis_client)
        billing_state.cost_predictor = CostPredictionEngine(billing_state.redis_client)
        billing_state.alert_manager = BillingAlertManager(billing_state.redis_client)
        billing_state.payment_processor = PaymentIntegrationSystem(billing_state.redis_client)
        billing_state.analytics_dashboard = UsageAnalyticsDashboard(billing_state.redis_client)
        billing_state.scaling_policies = AutomatedScalingPolicies(billing_state.redis_client)
        
        # Start background tasks
        await start_background_tasks()
        
        billing_state.is_initialized = True
        billing_state.logger.info("Dynamic Billing System initialized successfully")
        
    except Exception as e:
        billing_state.logger.error(f"Failed to initialize billing system: {e}")
        raise

async def start_background_tasks():
    """Start all background monitoring and processing tasks"""
    try:
        # Billing engine background tasks
        if billing_state.billing_engine:
            task = asyncio.create_task(billing_state.billing_engine.start_billing_processor())
            billing_state.background_tasks.add(task)
            task.add_done_callback(billing_state.background_tasks.discard)
        
        # Usage tracking background tasks
        if billing_state.usage_tracker:
            task = asyncio.create_task(billing_state.usage_tracker.start_continuous_monitoring())
            billing_state.background_tasks.add(task)
            task.add_done_callback(billing_state.background_tasks.discard)
        
        # Dynamic scaling background tasks
        if billing_state.dynamic_scaler:
            task = asyncio.create_task(billing_state.dynamic_scaler.start_scaling_monitor())
            billing_state.background_tasks.add(task)
            task.add_done_callback(billing_state.background_tasks.discard)
        
        # Cost prediction updates
        if billing_state.cost_predictor:
            task = asyncio.create_task(billing_state.cost_predictor.start_prediction_updates())
            billing_state.background_tasks.add(task)
            task.add_done_callback(billing_state.background_tasks.discard)
        
        # Alert monitoring
        if billing_state.alert_manager:
            task = asyncio.create_task(billing_state.alert_manager.start_alert_monitor())
            billing_state.background_tasks.add(task)
            task.add_done_callback(billing_state.background_tasks.discard)
        
        # Automated scaling policies
        if billing_state.scaling_policies:
            task = asyncio.create_task(billing_state.scaling_policies.start_policy_engine())
            billing_state.background_tasks.add(task)
            task.add_done_callback(billing_state.background_tasks.discard)
        
        billing_state.logger.info(f"Started {len(billing_state.background_tasks)} background tasks")
        
    except Exception as e:
        billing_state.logger.error(f"Failed to start background tasks: {e}")
        raise

async def shutdown_billing_system():
    """Shutdown billing system gracefully"""
    try:
        billing_state.logger.info("Shutting down Dynamic Billing System...")
        
        # Cancel all background tasks
        for task in billing_state.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if billing_state.background_tasks:
            await asyncio.gather(*billing_state.background_tasks, return_exceptions=True)
        
        # Shutdown components
        if billing_state.billing_engine:
            await billing_state.billing_engine.shutdown()
        
        if billing_state.usage_tracker:
            await billing_state.usage_tracker.shutdown()
        
        if billing_state.dynamic_scaler:
            await billing_state.dynamic_scaler.shutdown()
        
        # Close Redis connection
        if billing_state.redis_client:
            billing_state.redis_client.close()
        
        billing_state.logger.info("Dynamic Billing System shutdown complete")
        
    except Exception as e:
        billing_state.logger.error(f"Error during shutdown: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not billing_state.is_initialized:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "billing_engine": billing_state.billing_engine is not None,
            "usage_tracker": billing_state.usage_tracker is not None,
            "dynamic_scaler": billing_state.dynamic_scaler is not None,
            "cost_predictor": billing_state.cost_predictor is not None,
            "alert_manager": billing_state.alert_manager is not None,
            "payment_processor": billing_state.payment_processor is not None,
            "analytics_dashboard": billing_state.analytics_dashboard is not None,
            "scaling_policies": billing_state.scaling_policies is not None
        },
        "background_tasks": len(billing_state.background_tasks),
        "redis_connected": billing_state.redis_client is not None
    }
    
    return health_status

# Billing Engine Endpoints
@app.post("/billing/start")
async def start_billing_session(request_data: Dict[str, Any]):
    """Start a new billing session"""
    if not billing_state.billing_engine:
        raise HTTPException(status_code=503, detail="Billing engine not available")
    
    try:
        session_id = await billing_state.billing_engine.start_billing_session(
            user_id=request_data["user_id"],
            service_type=request_data["service_type"],
            resource_config=request_data.get("resource_config", {}),
            billing_config=request_data.get("billing_config", {})
        )
        
        return {"session_id": session_id, "status": "started"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/billing/stop/{session_id}")
async def stop_billing_session(session_id: str):
    """Stop a billing session"""
    if not billing_state.billing_engine:
        raise HTTPException(status_code=503, detail="Billing engine not available")
    
    try:
        final_bill = await billing_state.billing_engine.stop_billing_session(session_id)
        return final_bill
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/billing/session/{session_id}")
async def get_billing_session(session_id: str):
    """Get current billing session details"""
    if not billing_state.billing_engine:
        raise HTTPException(status_code=503, detail="Billing engine not available")
    
    try:
        session_info = await billing_state.billing_engine.get_session_details(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session_info
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/billing/user/{user_id}/current")
async def get_user_current_bill(user_id: str):
    """Get user's current accumulated bill"""
    if not billing_state.billing_engine:
        raise HTTPException(status_code=503, detail="Billing engine not available")
    
    try:
        current_bill = await billing_state.billing_engine.get_user_current_bill(user_id)
        return current_bill
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Usage Tracking Endpoints
@app.post("/usage/track")
async def track_resource_usage(usage_data: Dict[str, Any]):
    """Track resource usage for billing"""
    if not billing_state.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker not available")
    
    try:
        await billing_state.usage_tracker.record_usage(usage_data)
        return {"status": "recorded"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/usage/session/{session_id}")
async def get_session_usage(session_id: str):
    """Get usage statistics for a session"""
    if not billing_state.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker not available")
    
    try:
        usage_stats = await billing_state.usage_tracker.get_session_usage(session_id)
        return usage_stats
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/usage/user/{user_id}/summary")
async def get_user_usage_summary(user_id: str, days: int = 30):
    """Get user usage summary for specified period"""
    if not billing_state.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker not available")
    
    try:
        usage_summary = await billing_state.usage_tracker.get_user_usage_summary(user_id, days)
        return usage_summary
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Dynamic Scaling Endpoints
@app.post("/scaling/configure")
async def configure_scaling(scaling_config: Dict[str, Any]):
    """Configure dynamic scaling parameters"""
    if not billing_state.dynamic_scaler:
        raise HTTPException(status_code=503, detail="Dynamic scaler not available")
    
    try:
        await billing_state.dynamic_scaler.configure_scaling(scaling_config)
        return {"status": "configured"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/scaling/trigger/{session_id}")
async def trigger_scaling_action(session_id: str, scaling_action: Dict[str, Any]):
    """Manually trigger scaling action"""
    if not billing_state.dynamic_scaler:
        raise HTTPException(status_code=503, detail="Dynamic scaler not available")
    
    try:
        result = await billing_state.dynamic_scaler.trigger_scaling_action(session_id, scaling_action)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/scaling/status/{session_id}")
async def get_scaling_status(session_id: str):
    """Get current scaling status for session"""
    if not billing_state.dynamic_scaler:
        raise HTTPException(status_code=503, detail="Dynamic scaler not available")
    
    try:
        scaling_status = await billing_state.dynamic_scaler.get_scaling_status(session_id)
        return scaling_status
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Cost Prediction Endpoints
@app.post("/prediction/forecast")
async def forecast_costs(forecast_request: Dict[str, Any]):
    """Forecast costs based on usage patterns"""
    if not billing_state.cost_predictor:
        raise HTTPException(status_code=503, detail="Cost predictor not available")
    
    try:
        forecast = await billing_state.cost_predictor.forecast_costs(forecast_request)
        return forecast
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/prediction/user/{user_id}/monthly")
async def get_monthly_prediction(user_id: str):
    """Get monthly cost prediction for user"""
    if not billing_state.cost_predictor:
        raise HTTPException(status_code=503, detail="Cost predictor not available")
    
    try:
        monthly_prediction = await billing_state.cost_predictor.get_monthly_prediction(user_id)
        return monthly_prediction
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/prediction/optimize")
async def optimize_costs(optimization_request: Dict[str, Any]):
    """Get cost optimization recommendations"""
    if not billing_state.cost_predictor:
        raise HTTPException(status_code=503, detail="Cost predictor not available")
    
    try:
        optimization = await billing_state.cost_predictor.optimize_costs(optimization_request)
        return optimization
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Alert Management Endpoints
@app.post("/alerts/configure")
async def configure_billing_alerts(alert_config: Dict[str, Any]):
    """Configure billing alerts and thresholds"""
    if not billing_state.alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    try:
        await billing_state.alert_manager.configure_alerts(alert_config)
        return {"status": "configured"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/alerts/user/{user_id}")
async def get_user_alerts(user_id: str):
    """Get active alerts for user"""
    if not billing_state.alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    try:
        alerts = await billing_state.alert_manager.get_user_alerts(user_id)
        return alerts
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    if not billing_state.alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    try:
        await billing_state.alert_manager.acknowledge_alert(alert_id)
        return {"status": "acknowledged"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Payment Integration Endpoints
@app.post("/payment/add-method")
async def add_payment_method(payment_data: Dict[str, Any]):
    """Add payment method for user"""
    if not billing_state.payment_processor:
        raise HTTPException(status_code=503, detail="Payment processor not available")
    
    try:
        result = await billing_state.payment_processor.add_payment_method(payment_data)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/payment/process-bill")
async def process_bill_payment(payment_request: Dict[str, Any]):
    """Process payment for bill"""
    if not billing_state.payment_processor:
        raise HTTPException(status_code=503, detail="Payment processor not available")
    
    try:
        result = await billing_state.payment_processor.process_payment(payment_request)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/payment/user/{user_id}/methods")
async def get_payment_methods(user_id: str):
    """Get user's payment methods"""
    if not billing_state.payment_processor:
        raise HTTPException(status_code=503, detail="Payment processor not available")
    
    try:
        methods = await billing_state.payment_processor.get_payment_methods(user_id)
        return methods
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Analytics Dashboard Endpoints
@app.get("/analytics/dashboard/{user_id}")
async def get_usage_dashboard(user_id: str, period: str = "30d"):
    """Get usage analytics dashboard data"""
    if not billing_state.analytics_dashboard:
        raise HTTPException(status_code=503, detail="Analytics dashboard not available")
    
    try:
        dashboard_data = await billing_state.analytics_dashboard.get_dashboard_data(user_id, period)
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/analytics/reports/{user_id}")
async def get_usage_reports(user_id: str, report_type: str = "monthly"):
    """Get detailed usage reports"""
    if not billing_state.analytics_dashboard:
        raise HTTPException(status_code=503, detail="Analytics dashboard not available")
    
    try:
        reports = await billing_state.analytics_dashboard.generate_reports(user_id, report_type)
        return reports
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/analytics/trends/system")
async def get_system_trends():
    """Get system-wide usage trends"""
    if not billing_state.analytics_dashboard:
        raise HTTPException(status_code=503, detail="Analytics dashboard not available")
    
    try:
        trends = await billing_state.analytics_dashboard.get_system_trends()
        return trends
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Scaling Policy Endpoints
@app.post("/policies/create")
async def create_scaling_policy(policy_data: Dict[str, Any]):
    """Create automated scaling policy"""
    if not billing_state.scaling_policies:
        raise HTTPException(status_code=503, detail="Scaling policies not available")
    
    try:
        policy_id = await billing_state.scaling_policies.create_policy(policy_data)
        return {"policy_id": policy_id, "status": "created"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/policies/{policy_id}")
async def update_scaling_policy(policy_id: str, policy_data: Dict[str, Any]):
    """Update scaling policy"""
    if not billing_state.scaling_policies:
        raise HTTPException(status_code=503, detail="Scaling policies not available")
    
    try:
        await billing_state.scaling_policies.update_policy(policy_id, policy_data)
        return {"status": "updated"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/policies/user/{user_id}")
async def get_user_policies(user_id: str):
    """Get user's scaling policies"""
    if not billing_state.scaling_policies:
        raise HTTPException(status_code=503, detail="Scaling policies not available")
    
    try:
        policies = await billing_state.scaling_policies.get_user_policies(user_id)
        return policies
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/policies/{policy_id}")
async def delete_scaling_policy(policy_id: str):
    """Delete scaling policy"""
    if not billing_state.scaling_policies:
        raise HTTPException(status_code=503, detail="Scaling policies not available")
    
    try:
        await billing_state.scaling_policies.delete_policy(policy_id)
        return {"status": "deleted"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# System Management Endpoints
@app.get("/system/status")
async def get_system_status():
    """Get comprehensive system status"""
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
        "metrics": {}
    }
    
    # Component status
    if billing_state.billing_engine:
        status["components"]["billing_engine"] = await billing_state.billing_engine.get_status()
    
    if billing_state.usage_tracker:
        status["components"]["usage_tracker"] = await billing_state.usage_tracker.get_status()
    
    if billing_state.dynamic_scaler:
        status["components"]["dynamic_scaler"] = await billing_state.dynamic_scaler.get_status()
    
    # System metrics
    status["metrics"]["active_sessions"] = len(billing_state.background_tasks)
    status["metrics"]["redis_connected"] = billing_state.redis_client is not None
    
    return status

@app.post("/system/maintenance")
async def trigger_maintenance(maintenance_config: Dict[str, Any]):
    """Trigger system maintenance tasks"""
    try:
        results = {}
        
        if maintenance_config.get("cleanup_old_data", False):
            # Cleanup old billing data
            if billing_state.billing_engine:
                cleanup_result = await billing_state.billing_engine.cleanup_old_data()
                results["cleanup"] = cleanup_result
        
        if maintenance_config.get("optimize_storage", False):
            # Optimize data storage
            if billing_state.usage_tracker:
                optimize_result = await billing_state.usage_tracker.optimize_storage()
                results["optimization"] = optimize_result
        
        if maintenance_config.get("update_predictions", False):
            # Update cost predictions
            if billing_state.cost_predictor:
                update_result = await billing_state.cost_predictor.update_models()
                results["predictions"] = update_result
        
        return {"maintenance_results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8475,
        reload=False,
        log_level="info"
    )