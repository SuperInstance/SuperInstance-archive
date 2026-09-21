"""
Runtime Optimizer Main Service

Comprehensive API service for adaptive resource management, feature scaling,
network adaptation, and cost optimization with real-time monitoring and optimization.
"""

import asyncio
import logging
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
from websockets.exceptions import ConnectionClosedError

# Import our optimization modules
from config.settings import config, ResourceTier, NetworkTier, FeatureProfile
from src.adaptive_resource_manager import (
    resource_manager, TaskPriority, ResourceType, schedule_background_task, 
    schedule_critical_task
)
from src.feature_scaling_system import feature_scaler, FeatureCategory, ScalingDirection
from src.network_adaptation import network_adapter, DataType, SyncMode
from src.cost_optimization import (
    cost_optimizer, CostCategory, BillingModel, estimate_and_warn,
    record_compute_usage, record_storage_usage, record_api_usage
)
from src.monitoring_system import monitoring_system, HealthStatus, AlertLevel, MetricType
from src.ai_optimization_engine import ai_optimizer
from src.caching_system import MultiTierCacheManager, SmartCacheLayer, EvictionPolicy, CacheType
from src.gpu_compute_optimizer import (
    gpu_optimizer, GPUWorkload, ComputeType, WorkloadPriority,
    create_ai_training_workload, create_ai_inference_workload, create_scientific_workload
)
from src.distributed_orchestration import (
    distributed_orchestrator, DistributedTask, TaskExecutionMode, LoadBalancingStrategy,
    create_compute_task, create_map_reduce_task, create_pipeline_task
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests
class TaskRequest(BaseModel):
    task_id: str
    function_name: str = Field(description="Function to execute")
    args: List[Any] = Field(default=[], description="Function arguments")
    kwargs: Dict[str, Any] = Field(default={}, description="Function keyword arguments")
    priority: str = Field(default="normal", description="Task priority")
    resource_requirements: Dict[str, float] = Field(default={}, description="Resource requirements")
    estimated_duration: float = Field(default=60.0, description="Estimated duration in seconds")
    deadline_minutes: Optional[int] = Field(default=None, description="Deadline in minutes from now")

class FeatureScaleRequest(BaseModel):
    feature_id: str
    target_quality: float = Field(ge=0.0, le=1.0, description="Target quality level (0.0-1.0)")

class FeatureEnableRequest(BaseModel):
    feature_id: str
    enabled: bool

class NetworkTransferRequest(BaseModel):
    data: Any
    data_type: str = Field(description="Type of data (text, json, image, video, binary)")
    destination: Optional[str] = None
    compress: Optional[bool] = None

class OfflineQueueRequest(BaseModel):
    operation_type: str = Field(description="Type of operation (upload, download, sync)")
    data: Any
    priority: int = Field(default=5, ge=0, le=10, description="Priority (0-10)")

class CostBudgetRequest(BaseModel):
    name: str
    amount: float = Field(gt=0, description="Budget amount in USD")
    period: str = Field(default="monthly", description="Budget period")
    category: Optional[str] = None
    service_name: Optional[str] = None
    alert_thresholds: Optional[Dict[str, float]] = None

class CostRecordRequest(BaseModel):
    category: str
    service_name: str
    resource_type: str
    quantity: float
    unit: str
    unit_cost: Optional[float] = None
    billing_model: str = Field(default="pay_per_use")
    metadata: Optional[Dict[str, Any]] = None

class CostEstimateRequest(BaseModel):
    operation: str
    parameters: Dict[str, Any]
    cost_threshold: Optional[float] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except (WebSocketDisconnect, ConnectionClosedError):
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except (WebSocketDisconnect, ConnectionClosedError):
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Initialize cache manager
cache_manager = MultiTierCacheManager()

# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    logger.info("Starting Runtime Optimizer Service...")
    
    # Initialize advanced caching layers
    memory_cache = SmartCacheLayer(
        capacity=10000,
        eviction_policy=EvictionPolicy.ARC,
        cache_type=CacheType.MEMORY,
        enable_predictive=True
    )
    
    disk_cache = SmartCacheLayer(
        capacity=50000,
        eviction_policy=EvictionPolicy.PREDICTIVE,
        cache_type=CacheType.DISK,
        disk_cache_path="/tmp/runtime_optimizer_cache",
        enable_predictive=True
    )
    
    hybrid_cache = SmartCacheLayer(
        capacity=25000,
        eviction_policy=EvictionPolicy.ARC,
        cache_type=CacheType.HYBRID,
        disk_cache_path="/tmp/runtime_optimizer_hybrid",
        enable_predictive=True
    )
    
    # Add cache layers with routing
    cache_manager.add_cache_layer("memory", memory_cache, ["metrics", "status", "temp"])
    cache_manager.add_cache_layer("disk", disk_cache, ["historical", "logs", "archive"])
    cache_manager.add_cache_layer("hybrid", hybrid_cache, ["optimization", "features", "network"])
    
    await cache_manager.start_all()
    
    # Start all subsystems
    await resource_manager.start()
    await network_adapter.start_monitoring()
    await monitoring_system.start_monitoring()
    await ai_optimizer.start()
    await gpu_optimizer.start()
    await distributed_orchestrator.start()
    
    # Set up callbacks for real-time updates
    resource_manager.add_optimization_callback(broadcast_resource_update)
    feature_scaler.add_scaling_callback(broadcast_feature_update)
    network_adapter.add_adaptation_callback(broadcast_network_update)
    cost_optimizer.add_cost_callback(broadcast_cost_alert)
    monitoring_system.alert_manager.add_alert_callback(broadcast_monitoring_alert)
    
    # Start background optimization tasks
    optimization_task = asyncio.create_task(optimization_loop())
    
    logger.info("Runtime Optimizer Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Runtime Optimizer Service...")
    
    optimization_task.cancel()
    await resource_manager.stop()
    await network_adapter.stop_monitoring()
    await monitoring_system.stop_monitoring()
    await ai_optimizer.stop()
    await gpu_optimizer.stop()
    await distributed_orchestrator.stop()
    await cache_manager.stop_all()
    
    logger.info("Runtime Optimizer Service shut down complete")

# Create FastAPI app
app = FastAPI(
    title="Runtime Optimizer Service",
    description="Adaptive resource management, feature scaling, network adaptation, and cost optimization",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Callback functions for real-time updates
async def broadcast_resource_update(event_type: str, *args):
    """Broadcast resource manager updates"""
    await manager.broadcast({
        'type': 'resource_update',
        'event': event_type,
        'data': args,
        'timestamp': datetime.now().isoformat()
    })

async def broadcast_feature_update(event):
    """Broadcast feature scaling updates"""
    await manager.broadcast({
        'type': 'feature_update',
        'event': event.to_dict(),
        'timestamp': datetime.now().isoformat()
    })

async def broadcast_network_update(event_type: str, *args):
    """Broadcast network adaptation updates"""
    await manager.broadcast({
        'type': 'network_update',
        'event': event_type,
        'data': args,
        'timestamp': datetime.now().isoformat()
    })

async def broadcast_cost_alert(alert):
    """Broadcast cost alerts"""
    await manager.broadcast({
        'type': 'cost_alert',
        'alert': alert.to_dict(),
        'timestamp': datetime.now().isoformat()
    })

async def broadcast_monitoring_alert(alert):
    """Broadcast monitoring alerts"""
    await manager.broadcast({
        'type': 'monitoring_alert',
        'alert': alert.to_dict(),
        'timestamp': datetime.now().isoformat()
    })

# Background optimization loop
async def optimization_loop():
    """Background optimization and monitoring"""
    while True:
        try:
            # Update resource tier based on current metrics
            new_tier = resource_manager.update_resource_tier()
            
            # Update feature scaling based on resource tier
            await feature_scaler.update_resource_tier(new_tier, "automatic_optimization")
            
            # Generate and broadcast system health
            health_data = {
                'timestamp': datetime.now().isoformat(),
                'resource_tier': new_tier.value,
                'network_tier': network_adapter.current_tier.value,
                'system_load': await get_system_load_summary()
            }
            
            await manager.broadcast({
                'type': 'system_health',
                'data': health_data
            })
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
        except Exception as e:
            logger.error(f"Error in optimization loop: {e}")
            await asyncio.sleep(10)

async def get_system_load_summary() -> Dict[str, Any]:
    """Get summary of current system load"""
    metrics = resource_manager.monitor.get_current_metrics()
    if not metrics:
        return {'available': False}
    
    return {
        'available': True,
        'cpu_percent': metrics.cpu_percent,
        'memory_percent': metrics.memory_percent,
        'network_mbps': metrics.network_bandwidth_mbps,
        'temperature': metrics.cpu_temperature
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'runtime-optimizer',
        'version': '1.0.0',
        'subsystems': {
            'resource_manager': resource_manager.running,
            'feature_scaler': feature_scaler.auto_scaling_enabled,
            'network_adapter': network_adapter.monitoring_active,
            'cost_optimizer': cost_optimizer.auto_optimization
        }
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time system updates"""
    await manager.connect(websocket)
    try:
        # Send initial system status
        initial_status = await get_comprehensive_status()
        await manager.send_personal_message({
            'type': 'initial_status',
            'data': initial_status
        }, websocket)
        
        # Keep connection alive and handle client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle client requests
                if message.get('type') == 'get_status':
                    status = await get_comprehensive_status()
                    await manager.send_personal_message({
                        'type': 'status_response',
                        'data': status
                    }, websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    'type': 'error',
                    'message': 'Invalid JSON message'
                }, websocket)
            except Exception as e:
                await manager.send_personal_message({
                    'type': 'error',
                    'message': str(e)
                }, websocket)
    
    finally:
        manager.disconnect(websocket)

# === RESOURCE MANAGEMENT ENDPOINTS ===

@app.get("/resource-manager/status")
async def get_resource_manager_status():
    """Get resource manager status"""
    return resource_manager.get_system_status()

@app.get("/resource-manager/metrics")
async def get_current_metrics():
    """Get current system metrics"""
    metrics = resource_manager.monitor.get_current_metrics()
    if not metrics:
        raise HTTPException(status_code=503, detail="Metrics not available")
    return metrics.to_dict()

@app.get("/resource-manager/metrics/history")
async def get_metrics_history(hours: int = 1):
    """Get metrics history"""
    cutoff_time = time.time() - (hours * 3600)
    history = [m.to_dict() for m in resource_manager.monitor.metrics_history 
               if m.timestamp >= cutoff_time]
    return {'metrics': history, 'count': len(history)}

@app.get("/resource-manager/predictions")
async def get_resource_predictions(seconds_ahead: int = 300):
    """Get resource usage predictions"""
    predictions = resource_manager.monitor.predict_resource_usage(seconds_ahead)
    return {'predictions': predictions, 'seconds_ahead': seconds_ahead}

@app.post("/resource-manager/tasks/schedule")
async def schedule_task(task_request: TaskRequest):
    """Schedule a task for execution"""
    try:
        # Convert priority string to enum
        priority_map = {
            'critical': TaskPriority.CRITICAL,
            'high': TaskPriority.HIGH,
            'normal': TaskPriority.NORMAL,
            'low': TaskPriority.LOW,
            'idle': TaskPriority.IDLE
        }
        priority = priority_map.get(task_request.priority.lower(), TaskPriority.NORMAL)
        
        # Convert resource requirements
        resource_reqs = {}
        for resource, value in task_request.resource_requirements.items():
            try:
                resource_type = ResourceType(resource)
                resource_reqs[resource_type] = value
            except ValueError:
                logger.warning(f"Unknown resource type: {resource}")
        
        # Calculate deadline
        deadline = None
        if task_request.deadline_minutes:
            deadline = datetime.now() + timedelta(minutes=task_request.deadline_minutes)
        
        # Create dummy function for demo (in real implementation, would lookup by name)
        async def demo_task(*args, **kwargs):
            await asyncio.sleep(1)  # Simulate work
            return f"Task {task_request.task_id} completed with args: {args}, kwargs: {kwargs}"
        
        # Schedule the task
        task_id = resource_manager.schedule_task(
            task_id=task_request.task_id,
            function=demo_task,
            args=tuple(task_request.args),
            kwargs=task_request.kwargs,
            priority=priority,
            resource_requirements=resource_reqs,
            estimated_duration=task_request.estimated_duration,
            deadline=deadline
        )
        
        return {'task_id': task_id, 'status': 'scheduled'}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/resource-manager/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    status = resource_manager.scheduler.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return status

@app.delete("/resource-manager/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a task"""
    success = resource_manager.scheduler.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found or cannot be cancelled")
    return {'task_id': task_id, 'status': 'cancelled'}

@app.get("/resource-manager/tasks/queue")
async def get_task_queue_status():
    """Get task queue status"""
    return resource_manager.scheduler.get_queue_status()

# === FEATURE SCALING ENDPOINTS ===

@app.get("/feature-scaling/status")
async def get_feature_scaling_status():
    """Get feature scaling system status"""
    return feature_scaler.get_all_features_status()

@app.get("/feature-scaling/features/{feature_id}")
async def get_feature_status(feature_id: str):
    """Get status of a specific feature"""
    status = feature_scaler.get_feature_status(feature_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Feature {feature_id} not found")
    return status

@app.post("/feature-scaling/features/{feature_id}/scale")
async def scale_feature(feature_id: str, request: FeatureScaleRequest):
    """Manually scale a feature"""
    success = await feature_scaler.manual_scale_feature(feature_id, request.target_quality)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to scale feature {feature_id}")
    return {'feature_id': feature_id, 'target_quality': request.target_quality, 'status': 'scaled'}

@app.post("/feature-scaling/features/{feature_id}/toggle")
async def toggle_feature(feature_id: str, request: FeatureEnableRequest):
    """Enable or disable a feature"""
    if request.enabled:
        success = await feature_scaler.enable_feature(feature_id)
    else:
        success = await feature_scaler.disable_feature(feature_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to {'enable' if request.enabled else 'disable'} feature {feature_id}")
    
    return {'feature_id': feature_id, 'enabled': request.enabled, 'status': 'updated'}

@app.get("/feature-scaling/history")
async def get_scaling_history(hours: int = 24):
    """Get feature scaling history"""
    history = feature_scaler.get_scaling_history(hours)
    return {'history': history, 'count': len(history)}

@app.get("/feature-scaling/suggestions")
async def get_optimization_suggestions():
    """Get feature optimization suggestions"""
    suggestions = feature_scaler.get_optimization_suggestions()
    return {'suggestions': suggestions}

@app.post("/feature-scaling/tier/update")
async def update_feature_tier(tier: str, reason: str = "manual"):
    """Manually update feature scaling tier"""
    try:
        resource_tier = ResourceTier(tier)
        await feature_scaler.update_resource_tier(resource_tier, reason)
        return {'tier': tier, 'reason': reason, 'status': 'updated'}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid resource tier: {tier}")

# === NETWORK ADAPTATION ENDPOINTS ===

@app.get("/network-adaptation/status")
async def get_network_status():
    """Get network adaptation status"""
    return network_adapter.get_network_status()

@app.post("/network-adaptation/transfer")
async def transfer_data(request: NetworkTransferRequest):
    """Transfer data with network optimization"""
    try:
        data_type = DataType(request.data_type)
        transfer = await network_adapter.transfer_data(
            request.data, data_type, request.destination, request.compress)
        return transfer.to_dict()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid data type: {request.data_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/network-adaptation/offline-queue")
async def add_to_offline_queue(request: OfflineQueueRequest):
    """Add item to offline queue"""
    try:
        item_id = await network_adapter.add_to_offline_queue(
            request.operation_type, request.data, request.priority)
        return {'item_id': item_id, 'status': 'queued'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/network-adaptation/offline-queue")
async def get_offline_queue_status():
    """Get offline queue status"""
    queue_items = [item.to_dict() for item in network_adapter.offline_queue]
    return {
        'queue_items': queue_items,
        'count': len(queue_items),
        'total_size_mb': sum(item.size_bytes for item in network_adapter.offline_queue) / (1024 * 1024)
    }

@app.post("/network-adaptation/offline-mode")
async def toggle_offline_mode(enable: bool):
    """Enable or disable offline mode"""
    if enable:
        await network_adapter.enable_offline_mode()
    else:
        await network_adapter.disable_offline_mode()
    
    return {'offline_mode': enable, 'status': 'updated'}

@app.get("/network-adaptation/recommendations")
async def get_network_recommendations():
    """Get network optimization recommendations"""
    recommendations = network_adapter.get_optimization_recommendations()
    return {'recommendations': recommendations}

@app.get("/network-adaptation/metrics")
async def get_network_metrics(hours: int = 1):
    """Get network metrics history"""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    metrics = [m.to_dict() for m in network_adapter.metrics_history 
               if m.timestamp >= cutoff_time]
    return {'metrics': metrics, 'count': len(metrics)}

# === COST OPTIMIZATION ENDPOINTS ===

@app.get("/cost-optimization/status")
async def get_cost_optimization_status():
    """Get cost optimization status"""
    return cost_optimizer.get_system_status()

@app.post("/cost-optimization/record")
async def record_cost(request: CostRecordRequest):
    """Record a cost metric"""
    try:
        category = CostCategory(request.category)
        billing_model = BillingModel(request.billing_model)
        
        metric_id = cost_optimizer.record_cost(
            category=category,
            service_name=request.service_name,
            resource_type=request.resource_type,
            quantity=request.quantity,
            unit=request.unit,
            unit_cost=request.unit_cost,
            billing_model=billing_model,
            metadata=request.metadata
        )
        
        return {'metric_id': metric_id, 'status': 'recorded'}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cost-optimization/estimate")
async def estimate_operation_cost(request: CostEstimateRequest):
    """Estimate cost of an operation"""
    try:
        can_proceed, cost, message = await cost_optimizer.should_proceed_with_operation(
            request.operation, request.parameters, request.cost_threshold)
        
        return {
            'operation': request.operation,
            'estimated_cost': cost,
            'can_proceed': can_proceed,
            'message': message,
            'threshold': request.cost_threshold or config.cost_settings['warn_expensive_threshold']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cost-optimization/budgets")
async def create_budget(request: CostBudgetRequest):
    """Create a cost budget"""
    try:
        category = CostCategory(request.category) if request.category else None
        
        budget_id = cost_optimizer.create_budget(
            name=request.name,
            amount=request.amount,
            period=request.period,
            category=category,
            service_name=request.service_name,
            alert_thresholds=request.alert_thresholds
        )
        
        return {'budget_id': budget_id, 'status': 'created'}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cost-optimization/budgets")
async def get_budgets():
    """Get all budgets"""
    budgets = {bid: budget.to_dict() for bid, budget in cost_optimizer.budgets.items()}
    return {'budgets': budgets}

@app.get("/cost-optimization/breakdown")
async def get_cost_breakdown(period: str = "monthly"):
    """Get cost breakdown"""
    try:
        breakdown = cost_optimizer.get_cost_breakdown(period)
        return breakdown
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cost-optimization/forecast")
async def get_cost_forecast(days_ahead: int = 30):
    """Get cost forecast"""
    try:
        forecast = cost_optimizer.get_cost_forecast(days_ahead)
        return forecast
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cost-optimization/suggestions")
async def get_cost_suggestions():
    """Get cost optimization suggestions"""
    suggestions = cost_optimizer.generate_optimization_suggestions()
    return {'suggestions': [s.to_dict() for s in suggestions]}

@app.get("/cost-optimization/alerts")
async def get_cost_alerts(limit: int = 50):
    """Get recent cost alerts"""
    recent_alerts = list(cost_optimizer.alerts)[-limit:]
    return {'alerts': [alert.to_dict() for alert in recent_alerts]}

@app.get("/cost-optimization/free-tier")
async def get_free_tier_status():
    """Get free tier usage status"""
    return cost_optimizer.free_tier_manager.get_free_tier_status()

# === MONITORING AND HEALTH CHECK ENDPOINTS ===

@app.get("/monitoring/health")
async def get_health_status():
    """Get comprehensive health status"""
    return monitoring_system.health_checker.get_health_summary()

@app.get("/monitoring/health/{check_name}")
async def run_specific_health_check(check_name: str):
    """Run a specific health check"""
    result = await monitoring_system.health_checker.run_health_check(check_name)
    return result.to_dict()

@app.post("/monitoring/health/run-all")
async def run_all_health_checks():
    """Run all health checks"""
    results = await monitoring_system.health_checker.run_all_health_checks(force=True)
    return {check: result.to_dict() for check, result in results.items()}

@app.get("/monitoring/metrics")
async def get_metrics_summary():
    """Get metrics summary"""
    return monitoring_system.metrics_collector.get_all_metrics_summary()

@app.get("/monitoring/metrics/{metric_name}")
async def get_metric_details(metric_name: str, minutes: int = 60):
    """Get details for a specific metric"""
    summary = monitoring_system.metrics_collector.get_metric_summary(metric_name, minutes)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Metric {metric_name} not found or no data")
    return {'metric_name': metric_name, 'summary': summary}

@app.post("/monitoring/metrics/record")
async def record_custom_metric(metric_name: str, value: float, metric_type: str = "gauge", 
                              tags: Dict[str, str] = None):
    """Record a custom metric"""
    try:
        metric_type_enum = MetricType(metric_type)
        monitoring_system.metrics_collector.record_metric(metric_name, metric_type_enum, value, tags)
        return {'metric_name': metric_name, 'value': value, 'type': metric_type, 'status': 'recorded'}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric type: {metric_type}")

@app.get("/monitoring/alerts")
async def get_monitoring_alerts(level: str = None, active_only: bool = True):
    """Get monitoring alerts"""
    try:
        alert_level = AlertLevel(level) if level else None
        if active_only:
            alerts = monitoring_system.alert_manager.get_active_alerts(alert_level)
        else:
            # Get all alerts
            all_alerts = list(monitoring_system.alert_manager.alerts)
            if alert_level:
                all_alerts = [a for a in all_alerts if a.level == alert_level]
            alerts = [alert.to_dict() for alert in all_alerts]
        
        return {'alerts': alerts, 'count': len(alerts)}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid alert level: {level}")

@app.post("/monitoring/alerts")
async def create_monitoring_alert(component: str, level: str, message: str, 
                                details: Dict[str, Any] = None):
    """Create a manual monitoring alert"""
    try:
        alert_id = await monitoring_system.create_manual_alert(component, level, message, details)
        return {'alert_id': alert_id, 'status': 'created'}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/monitoring/alerts/{alert_id}/resolve")
async def resolve_monitoring_alert(alert_id: str):
    """Resolve a monitoring alert"""
    success = await monitoring_system.alert_manager.resolve_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {'alert_id': alert_id, 'status': 'resolved'}

@app.get("/monitoring/dashboard")
async def get_monitoring_dashboard():
    """Get monitoring dashboard data with intelligent caching"""
    cache_key = f"dashboard_data_{int(time.time() // 30)}"  # Cache for 30 seconds
    
    cached_data = await cache_manager.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    dashboard_data = monitoring_system.get_monitoring_dashboard_data()
    await cache_manager.put(cache_key, dashboard_data, ttl=30.0)
    
    return dashboard_data

@app.get("/monitoring/performance-report")
async def get_performance_report():
    """Get system performance report"""
    return monitoring_system.get_system_performance_report()

# === COMPREHENSIVE STATUS ENDPOINT ===

async def get_comprehensive_status():
    """Get comprehensive system status"""
    resource_status = resource_manager.get_system_status()
    feature_status = feature_scaler.get_all_features_status()
    network_status = network_adapter.get_network_status()
    cost_status = cost_optimizer.get_system_status()
    monitoring_status = monitoring_system.get_monitoring_dashboard_data()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'service_info': {
            'name': 'runtime-optimizer',
            'version': '1.0.0',
            'port': config.port,
            'uptime_seconds': time.time() - getattr(get_comprehensive_status, 'start_time', time.time())
        },
        'resource_management': resource_status,
        'feature_scaling': feature_status,
        'network_adaptation': network_status,
        'cost_optimization': cost_status,
        'monitoring_system': monitoring_status,
        'active_websockets': len(manager.active_connections)
    }

# Store service start time for uptime calculation
get_comprehensive_status.start_time = time.time()

@app.get("/status/comprehensive")
async def comprehensive_status():
    """Get comprehensive system status"""
    return await get_comprehensive_status()

@app.get("/status/summary")
async def status_summary():
    """Get high-level status summary"""
    metrics = resource_manager.monitor.get_current_metrics()
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'overall_health': 'healthy',
        'resource_tier': resource_manager.current_resource_tier.value,
        'network_tier': network_adapter.current_tier.value,
        'active_tasks': len(resource_manager.scheduler.running_tasks),
        'queued_tasks': len(resource_manager.scheduler.task_queue),
        'total_features': len(feature_scaler.features),
        'enabled_features': sum(1 for f in feature_scaler.features.values() if f.enabled),
        'offline_queue_items': len(network_adapter.offline_queue),
        'daily_cost_usd': cost_optimizer.daily_costs.get(datetime.now().strftime('%Y-%m-%d'), 0.0)
    }
    
    if metrics:
        summary.update({
            'cpu_percent': metrics.cpu_percent,
            'memory_percent': metrics.memory_percent,
            'network_mbps': metrics.network_bandwidth_mbps,
            'temperature_c': metrics.cpu_temperature
        })
    
    return summary

# === UTILITY ENDPOINTS ===

@app.post("/optimize/trigger")
async def trigger_optimization():
    """Manually trigger optimization"""
    try:
        # Update resource tier
        new_tier = resource_manager.update_resource_tier()
        
        # Trigger feature scaling
        await feature_scaler.update_resource_tier(new_tier, "manual_trigger")
        
        # Generate cost suggestions
        cost_suggestions = cost_optimizer.generate_optimization_suggestions()
        
        # Get network recommendations
        network_recommendations = network_adapter.get_optimization_recommendations()
        
        return {
            'status': 'optimization_triggered',
            'resource_tier': new_tier.value,
            'cost_suggestions_count': len(cost_suggestions),
            'network_recommendations_count': len(network_recommendations),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_configuration():
    """Get current configuration"""
    return {
        'resource_thresholds': {
            'cpu_critical': config.thresholds.cpu_critical,
            'memory_critical': config.thresholds.memory_critical,
            'temperature_critical': config.thresholds.temperature_critical
        },
        'optimization_settings': {
            'monitoring_interval': config.optimization.monitoring_interval,
            'enable_auto_scaling': config.optimization.enable_auto_scaling,
            'scaling_sensitivity': config.optimization.scaling_sensitivity
        },
        'cost_settings': config.cost_settings,
        'service_info': {
            'port': config.port,
            'debug': config.debug,
            'log_level': config.log_level
        }
    }

# === CACHE MANAGEMENT ENDPOINTS ===

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics and status"""
    return cache_manager.get_global_stats()

@app.post("/cache/clear")
async def clear_cache():
    """Clear all cache layers"""
    cleared_layers = 0
    for layer_name, layer in cache_manager.cache_layers.items():
        await layer.clear()
        cleared_layers += 1
    
    return {
        'status': 'cache_cleared',
        'layers_cleared': cleared_layers,
        'timestamp': datetime.now().isoformat()
    }

@app.delete("/cache/keys/{key}")
async def delete_cache_key(key: str):
    """Delete specific key from cache"""
    deleted = await cache_manager.delete(key) if hasattr(cache_manager, 'delete') else False
    
    # Try deleting from all layers
    deleted_from_layers = 0
    for layer in cache_manager.cache_layers.values():
        if await layer.delete(key):
            deleted_from_layers += 1
    
    return {
        'key': key,
        'deleted': deleted or deleted_from_layers > 0,
        'layers_affected': deleted_from_layers
    }

@app.get("/cache/keys/{key}")
async def get_cache_key(key: str):
    """Get value from cache"""
    value = await cache_manager.get(key)
    
    if value is None:
        raise HTTPException(status_code=404, detail=f"Cache key '{key}' not found")
    
    return {
        'key': key,
        'value': value,
        'retrieved_at': datetime.now().isoformat()
    }

@app.put("/cache/keys/{key}")
async def set_cache_key(key: str, value: Any, ttl: Optional[float] = None, priority: int = 0):
    """Set value in cache"""
    success = await cache_manager.put(key, value, ttl=ttl, priority=priority)
    
    return {
        'key': key,
        'stored': success,
        'ttl': ttl,
        'priority': priority,
        'stored_at': datetime.now().isoformat()
    }

# === GPU COMPUTE OPTIMIZATION ENDPOINTS ===

class GPUWorkloadRequest(BaseModel):
    name: str
    compute_type: str = Field(description="Type of compute workload")
    priority: str = Field(default="normal", description="Workload priority")
    memory_required_mb: int = Field(description="Required GPU memory in MB")
    estimated_duration_seconds: float = Field(description="Estimated duration")
    requires_tensor_cores: bool = Field(default=False, description="Requires tensor cores")
    requires_rt_cores: bool = Field(default=False, description="Requires RT cores")
    requires_double_precision: bool = Field(default=False, description="Requires FP64")

@app.get("/gpu/status")
async def get_gpu_status():
    """Get comprehensive GPU status"""
    return gpu_optimizer.get_gpu_status()

@app.post("/gpu/workloads/submit")
async def submit_gpu_workload(workload_request: GPUWorkloadRequest):
    """Submit GPU workload for execution"""
    try:
        compute_type = ComputeType(workload_request.compute_type)
        priority = WorkloadPriority(workload_request.priority)
        
        workload = GPUWorkload(
            id=f"workload_{int(time.time())}_{workload_request.name}",
            name=workload_request.name,
            compute_type=compute_type,
            priority=priority,
            memory_required_mb=workload_request.memory_required_mb,
            estimated_duration_seconds=workload_request.estimated_duration_seconds,
            compute_units_required=0.5,  # Default
            requires_tensor_cores=workload_request.requires_tensor_cores,
            requires_rt_cores=workload_request.requires_rt_cores,
            requires_double_precision=workload_request.requires_double_precision
        )
        
        workload_id = gpu_optimizer.submit_workload(workload)
        
        return {
            'workload_id': workload_id,
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")

@app.get("/gpu/workloads/{workload_id}")
async def get_gpu_workload_status(workload_id: str):
    """Get GPU workload status"""
    status = gpu_optimizer.get_workload_status(workload_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Workload {workload_id} not found")
    
    return status

@app.delete("/gpu/workloads/{workload_id}")
async def cancel_gpu_workload(workload_id: str):
    """Cancel GPU workload"""
    success = gpu_optimizer.cancel_workload(workload_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Workload {workload_id} not found or already completed")
    
    return {
        'workload_id': workload_id,
        'status': 'cancelled',
        'cancelled_at': datetime.now().isoformat()
    }

@app.post("/gpu/workloads/ai-training")
async def submit_ai_training_workload(name: str, memory_mb: int, duration_seconds: float, 
                                     priority: str = "high"):
    """Submit AI training workload (convenience endpoint)"""
    try:
        priority_enum = WorkloadPriority(priority)
        workload = create_ai_training_workload(name, memory_mb, duration_seconds, priority_enum)
        workload_id = gpu_optimizer.submit_workload(workload)
        
        return {
            'workload_id': workload_id,
            'type': 'ai_training',
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/gpu/workloads/ai-inference")
async def submit_ai_inference_workload(name: str, memory_mb: int, duration_seconds: float,
                                      priority: str = "normal"):
    """Submit AI inference workload (convenience endpoint)"""
    try:
        priority_enum = WorkloadPriority(priority)
        workload = create_ai_inference_workload(name, memory_mb, duration_seconds, priority_enum)
        workload_id = gpu_optimizer.submit_workload(workload)
        
        return {
            'workload_id': workload_id,
            'type': 'ai_inference',
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/gpu/workloads/scientific")
async def submit_scientific_workload(name: str, memory_mb: int, duration_seconds: float,
                                    requires_fp64: bool = False):
    """Submit scientific computing workload (convenience endpoint)"""
    workload = create_scientific_workload(name, memory_mb, duration_seconds, requires_fp64)
    workload_id = gpu_optimizer.submit_workload(workload)
    
    return {
        'workload_id': workload_id,
        'type': 'scientific',
        'status': 'submitted',
        'submitted_at': datetime.now().isoformat()
    }

@app.get("/gpu/scheduler/statistics")
async def get_gpu_scheduler_statistics():
    """Get GPU scheduler statistics"""
    return gpu_optimizer.gpu_scheduler.get_statistics()

@app.post("/gpu/scheduler/strategy")
async def set_gpu_scheduling_strategy(strategy: str):
    """Set GPU scheduling strategy"""
    try:
        from src.gpu_compute_optimizer import GPUSchedulingStrategy
        strategy_enum = GPUSchedulingStrategy(strategy)
        gpu_optimizer.set_scheduling_strategy(strategy_enum)
        
        return {
            'strategy': strategy,
            'status': 'updated',
            'updated_at': datetime.now().isoformat()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")

# === DISTRIBUTED ORCHESTRATION ENDPOINTS ===

class DistributedTaskRequest(BaseModel):
    name: str
    execution_mode: str = Field(description="Task execution mode")
    required_capabilities: List[str] = Field(description="Required node capabilities")
    required_resources: Dict[str, float] = Field(description="Required resources")
    priority: int = Field(default=0, description="Task priority")
    timeout_seconds: float = Field(default=300.0, description="Task timeout")
    dependency_task_ids: List[str] = Field(default=[], description="Dependency tasks")
    payload: Optional[Any] = Field(default=None, description="Task payload")

@app.get("/cluster/status")
async def get_cluster_status():
    """Get comprehensive cluster status"""
    return distributed_orchestrator.get_cluster_status()

@app.get("/cluster/statistics")
async def get_orchestration_statistics():
    """Get orchestration statistics"""
    return distributed_orchestrator.get_orchestration_stats()

@app.post("/cluster/tasks/submit")
async def submit_distributed_task(task_request: DistributedTaskRequest):
    """Submit distributed task"""
    try:
        execution_mode = TaskExecutionMode(task_request.execution_mode)
        
        task = DistributedTask(
            task_id=f"dist_task_{int(time.time())}_{task_request.name}",
            name=task_request.name,
            execution_mode=execution_mode,
            required_capabilities=set(task_request.required_capabilities),
            required_resources=task_request.required_resources,
            priority=task_request.priority,
            timeout_seconds=task_request.timeout_seconds,
            dependency_task_ids=task_request.dependency_task_ids,
            payload=task_request.payload
        )
        
        task_id = distributed_orchestrator.submit_task(task)
        
        return {
            'task_id': task_id,
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")

@app.get("/cluster/tasks/{task_id}")
async def get_distributed_task_status(task_id: str):
    """Get distributed task status"""
    status = distributed_orchestrator.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return status

@app.delete("/cluster/tasks/{task_id}")
async def cancel_distributed_task(task_id: str):
    """Cancel distributed task"""
    success = distributed_orchestrator.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found or already completed")
    
    return {
        'task_id': task_id,
        'status': 'cancelled',
        'cancelled_at': datetime.now().isoformat()
    }

@app.post("/cluster/tasks/{task_id}/complete")
async def complete_distributed_task(task_id: str, success: bool = True, result: Optional[Any] = None, 
                                   error: Optional[str] = None):
    """Complete distributed task (internal use)"""
    distributed_orchestrator.complete_task(task_id, success, result, error)
    
    return {
        'task_id': task_id,
        'status': 'completed' if success else 'failed',
        'completed_at': datetime.now().isoformat()
    }

@app.post("/cluster/tasks/compute")
async def submit_compute_task(name: str, capabilities: List[str], resources: Dict[str, float],
                             execution_mode: str = "local", priority: int = 0):
    """Submit compute task (convenience endpoint)"""
    try:
        execution_mode_enum = TaskExecutionMode(execution_mode)
        task = create_compute_task(name, set(capabilities), resources, execution_mode_enum, priority)
        task_id = distributed_orchestrator.submit_task(task)
        
        return {
            'task_id': task_id,
            'type': 'compute',
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/cluster/tasks/map-reduce")
async def submit_map_reduce_task(name: str, map_tasks: int, reduce_tasks: int, 
                                capabilities: List[str], resources: Dict[str, float]):
    """Submit map-reduce task (convenience endpoint)"""
    task = create_map_reduce_task(name, map_tasks, reduce_tasks, set(capabilities), resources)
    task_id = distributed_orchestrator.submit_task(task)
    
    return {
        'task_id': task_id,
        'type': 'map_reduce',
        'status': 'submitted',
        'submitted_at': datetime.now().isoformat()
    }

@app.post("/cluster/tasks/pipeline")
async def submit_pipeline_task(name: str, stages: List[str], capabilities: List[str], 
                              resources: Dict[str, float]):
    """Submit pipeline task (convenience endpoint)"""
    task = create_pipeline_task(name, stages, set(capabilities), resources)
    task_id = distributed_orchestrator.submit_task(task)
    
    return {
        'task_id': task_id,
        'type': 'pipeline',
        'status': 'submitted',
        'submitted_at': datetime.now().isoformat()
    }

@app.post("/cluster/load-balancing/strategy")
async def set_load_balancing_strategy(strategy: str):
    """Set load balancing strategy"""
    try:
        strategy_enum = LoadBalancingStrategy(strategy)
        distributed_orchestrator.set_load_balancing_strategy(strategy_enum)
        
        return {
            'strategy': strategy,
            'status': 'updated',
            'updated_at': datetime.now().isoformat()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")

if __name__ == "__main__":
    port = config.port
    uvicorn.run(
        "main:app",
        host=config.host,
        port=port,
        log_level=config.log_level.lower(),
        reload=config.debug
    )