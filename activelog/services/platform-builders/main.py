#!/usr/bin/env python3
"""
Platform-Specific Builders Service

Comprehensive multi-platform build and distribution system supporting desktop,
mobile, embedded, and edge computing platforms with optimization and deployment.
"""

import asyncio
import logging
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn

# Import platform builders
from src.desktop_builders import desktop_builder_manager, DesktopPlatform, BuildConfig
from src.mobile_builders import mobile_builder_manager, MobilePlatform, AppConfig
from src.embedded_builders import embedded_builder_manager, EmbeddedPlatform, FirmwareConfig
from src.edge_builders import edge_builder_manager, EdgePlatform, EdgeConfig
from src.build_optimizer import build_optimizer, OptimizationProfile, OptimizationLevel
from src.distribution_system import distribution_system, UpdateChannel, RolloutStrategy
from src.platform_detector import PlatformDetector
from src.performance_profiler import get_profiler, start_profiling, stop_profiling, get_performance_summary, get_optimization_recommendations, profile_function
from src.bottleneck_analyzer import get_analyzer, AnalysisType
from src.security_compliance import security_compliance_manager
from src.analytics_dashboard import get_dashboard, start_dashboard, stop_dashboard, ChartType, MetricType, AlertLevel, Metric, Alert, Dashboard, ChartConfig
from config.build_settings import build_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests
class BuildRequest(BaseModel):
    project_name: str
    platform: str = Field(description="Target platform")
    architecture: str = Field(description="Target architecture")
    optimization_level: str = Field(default="balanced", description="Optimization level")
    config: Dict[str, Any] = Field(default={}, description="Platform-specific config")
    source_path: Optional[str] = Field(default=None, description="Source code path")
    output_path: Optional[str] = Field(default=None, description="Output path")
    incremental: bool = Field(default=True, description="Enable incremental builds")

class DistributionRequest(BaseModel):
    build_id: str
    channel: str = Field(default="stable", description="Distribution channel")
    rollout_strategy: str = Field(default="staged", description="Rollout strategy")
    regions: List[str] = Field(default=[], description="Target regions")
    platforms: List[str] = Field(default=[], description="Target platforms")
    metadata: Dict[str, Any] = Field(default={}, description="Release metadata")

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

    async def send_personal_message(self, message: str, websocket: WebSocket):
        if websocket in self.active_connections:
            try:
                await websocket.send_text(message)
            except:
                self.disconnect(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# WebSocket event broadcasters
async def broadcast_build_update(event_data: Dict[str, Any]):
    """Broadcast build status updates"""
    message = json.dumps({
        "type": "build_update",
        "event": event_data.get("event", "status_change"),
        "data": event_data,
        "timestamp": datetime.now().isoformat()
    })
    await manager.broadcast(message)

async def broadcast_distribution_update(event_data: Dict[str, Any]):
    """Broadcast distribution status updates"""
    message = json.dumps({
        "type": "distribution_update",
        "event": event_data.get("event", "status_change"),
        "data": event_data,
        "timestamp": datetime.now().isoformat()
    })
    await manager.broadcast(message)

# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    logger.info("Starting Platform Builders Service...")
    
    # Start all subsystems
    await desktop_builder_manager.start()
    await mobile_builder_manager.start()
    await embedded_builder_manager.start()
    await edge_builder_manager.start()
    await build_optimizer.start()
    await distribution_system.start()
    
    # Set up callbacks for real-time updates
    desktop_builder_manager.add_build_callback(broadcast_build_update)
    mobile_builder_manager.add_build_callback(broadcast_build_update)
    embedded_builder_manager.add_build_callback(broadcast_build_update)
    edge_builder_manager.add_build_callback(broadcast_build_update)
    distribution_system.add_distribution_callback(broadcast_distribution_update)
    
    logger.info("Platform Builders Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Platform Builders Service...")
    
    await desktop_builder_manager.stop()
    await mobile_builder_manager.stop()
    await embedded_builder_manager.stop()
    await edge_builder_manager.stop()
    await build_optimizer.stop()
    await distribution_system.stop()
    
    logger.info("Platform Builders Service shut down complete")

# Create FastAPI app
app = FastAPI(
    title="Platform Builders Service",
    description="Multi-platform build and distribution system",
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

# === CORE ENDPOINTS ===

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Platform Builders Service",
        "version": "1.0.0",
        "description": "Multi-platform build and distribution system",
        "supported_platforms": {
            "desktop": ["windows", "macos", "linux", "chromeos", "freebsd"],
            "mobile": ["ios", "android", "windows_mobile", "kaios", "wearos"],
            "embedded": ["raspberry_pi", "arduino", "esp32", "jetson", "beaglebone", "plc"],
            "edge": ["aws_greengrass", "azure_iot_edge", "google_edge_tpu", "nvidia_edge", "intel_nuc"]
        },
        "port": 8432,
        "endpoints": {
            "build": "/build/{platform}",
            "distribute": "/distribute",
            "status": "/status",
            "websocket": "/ws"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "subsystems": {
            "desktop_builders": desktop_builder_manager.is_healthy(),
            "mobile_builders": mobile_builder_manager.is_healthy(),
            "embedded_builders": embedded_builder_manager.is_healthy(),
            "edge_builders": edge_builder_manager.is_healthy(),
            "build_optimizer": build_optimizer.is_healthy(),
            "distribution_system": distribution_system.is_healthy()
        }
    }

@app.get("/status")
async def get_service_status():
    """Get comprehensive service status"""
    return {
        "service_status": "running",
        "uptime_seconds": time.time() - build_config.start_time,
        "active_builds": (
            desktop_builder_manager.get_active_build_count() +
            mobile_builder_manager.get_active_build_count() +
            embedded_builder_manager.get_active_build_count() +
            edge_builder_manager.get_active_build_count()
        ),
        "total_builds_completed": (
            desktop_builder_manager.get_completed_build_count() +
            mobile_builder_manager.get_completed_build_count() +
            embedded_builder_manager.get_completed_build_count() +
            edge_builder_manager.get_completed_build_count()
        ),
        "distribution_stats": distribution_system.get_statistics(),
        "optimization_stats": build_optimizer.get_statistics(),
        "supported_platforms": await get_supported_platforms()
    }

@app.get("/platforms")
async def get_supported_platforms():
    """Get all supported platforms"""
    return {
        "desktop": {
            "windows": ["x86", "x64", "arm64"],
            "macos": ["x64", "arm64"],
            "linux": ["x86", "x64", "arm", "arm64"],
            "chromeos": ["x64", "arm64"],
            "freebsd": ["x64", "arm64"]
        },
        "mobile": {
            "ios": ["arm64", "arm64e"],
            "android": ["arm", "arm64", "x86", "x64"],
            "windows_mobile": ["arm64"],
            "kaios": ["arm"],
            "wearos": ["arm", "arm64"]
        },
        "embedded": {
            "raspberry_pi": ["arm", "arm64"],
            "arduino": ["avr", "arm", "esp32"],
            "esp32": ["xtensa", "riscv"],
            "jetson": ["arm64"],
            "beaglebone": ["arm"],
            "plc": ["x86", "arm"],
            "automotive": ["arm", "arm64"],
            "marine": ["arm", "x86"],
            "smart_home": ["arm", "esp32"],
            "medical": ["arm", "x86"]
        },
        "edge": {
            "aws_greengrass": ["x64", "arm64"],
            "azure_iot_edge": ["x64", "arm64"],
            "google_edge_tpu": ["arm64"],
            "nvidia_edge": ["arm64"],
            "intel_nuc": ["x64"]
        }
    }

# === BUILD ENDPOINTS ===

@app.post("/build/desktop")
async def build_desktop_platform(build_request: BuildRequest, background_tasks: BackgroundTasks):
    """Build for desktop platforms"""
    try:
        platform = DesktopPlatform(build_request.platform)
        
        config = BuildConfig(
            project_name=build_request.project_name,
            platform=platform,
            architecture=build_request.architecture,
            optimization_level=OptimizationLevel(build_request.optimization_level),
            source_path=build_request.source_path or f"projects/{build_request.project_name}",
            output_path=build_request.output_path or f"dist/{build_request.project_name}",
            incremental=build_request.incremental,
            platform_config=build_request.config
        )
        
        build_id = await desktop_builder_manager.submit_build(config)
        
        return {
            "build_id": build_id,
            "platform": build_request.platform,
            "architecture": build_request.architecture,
            "status": "submitted",
            "estimated_duration": "5-15 minutes",
            "submitted_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build submission failed: {str(e)}")

@app.post("/build/mobile")
async def build_mobile_platform(build_request: BuildRequest, background_tasks: BackgroundTasks):
    """Build for mobile platforms"""
    try:
        platform = MobilePlatform(build_request.platform)
        
        config = AppConfig(
            project_name=build_request.project_name,
            platform=platform,
            architecture=build_request.architecture,
            optimization_level=OptimizationLevel(build_request.optimization_level),
            source_path=build_request.source_path or f"projects/{build_request.project_name}",
            output_path=build_request.output_path or f"dist/{build_request.project_name}",
            incremental=build_request.incremental,
            platform_config=build_request.config
        )
        
        build_id = await mobile_builder_manager.submit_build(config)
        
        return {
            "build_id": build_id,
            "platform": build_request.platform,
            "architecture": build_request.architecture,
            "status": "submitted",
            "estimated_duration": "10-30 minutes",
            "submitted_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build submission failed: {str(e)}")

@app.post("/build/embedded")
async def build_embedded_platform(build_request: BuildRequest, background_tasks: BackgroundTasks):
    """Build for embedded platforms"""
    try:
        platform = EmbeddedPlatform(build_request.platform)
        
        config = FirmwareConfig(
            project_name=build_request.project_name,
            platform=platform,
            architecture=build_request.architecture,
            optimization_level=OptimizationLevel(build_request.optimization_level),
            source_path=build_request.source_path or f"projects/{build_request.project_name}",
            output_path=build_request.output_path or f"dist/{build_request.project_name}",
            incremental=build_request.incremental,
            platform_config=build_request.config
        )
        
        build_id = await embedded_builder_manager.submit_build(config)
        
        return {
            "build_id": build_id,
            "platform": build_request.platform,
            "architecture": build_request.architecture,
            "status": "submitted",
            "estimated_duration": "3-10 minutes",
            "submitted_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build submission failed: {str(e)}")

@app.post("/build/edge")
async def build_edge_platform(build_request: BuildRequest, background_tasks: BackgroundTasks):
    """Build for edge computing platforms"""
    try:
        platform = EdgePlatform(build_request.platform)
        
        config = EdgeConfig(
            project_name=build_request.project_name,
            platform=platform,
            architecture=build_request.architecture,
            optimization_level=OptimizationLevel(build_request.optimization_level),
            source_path=build_request.source_path or f"projects/{build_request.project_name}",
            output_path=build_request.output_path or f"dist/{build_request.project_name}",
            incremental=build_request.incremental,
            platform_config=build_request.config
        )
        
        build_id = await edge_builder_manager.submit_build(config)
        
        return {
            "build_id": build_id,
            "platform": build_request.platform,
            "architecture": build_request.architecture,
            "status": "submitted",
            "estimated_duration": "5-20 minutes",
            "submitted_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build submission failed: {str(e)}")

@app.get("/build/{build_id}/status")
async def get_build_status(build_id: str):
    """Get build status"""
    # Check all builder managers for the build
    for manager in [desktop_builder_manager, mobile_builder_manager, 
                   embedded_builder_manager, edge_builder_manager]:
        status = await manager.get_build_status(build_id)
        if status:
            return status
    
    raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

@app.delete("/build/{build_id}")
async def cancel_build(build_id: str):
    """Cancel a build"""
    # Try to cancel in all builder managers
    cancelled = False
    for manager in [desktop_builder_manager, mobile_builder_manager,
                   embedded_builder_manager, edge_builder_manager]:
        if await manager.cancel_build(build_id):
            cancelled = True
            break
    
    if not cancelled:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found or already completed")
    
    return {
        "build_id": build_id,
        "status": "cancelled",
        "cancelled_at": datetime.now().isoformat()
    }

@app.get("/build/{build_id}/logs")
async def get_build_logs(build_id: str, lines: int = 100):
    """Get build logs"""
    # Check all builder managers for logs
    for manager in [desktop_builder_manager, mobile_builder_manager,
                   embedded_builder_manager, edge_builder_manager]:
        logs = await manager.get_build_logs(build_id, lines)
        if logs:
            return {"build_id": build_id, "logs": logs}
    
    raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

@app.get("/build/{build_id}/artifacts")
async def get_build_artifacts(build_id: str):
    """Get build artifacts"""
    # Check all builder managers for artifacts
    for manager in [desktop_builder_manager, mobile_builder_manager,
                   embedded_builder_manager, edge_builder_manager]:
        artifacts = await manager.get_build_artifacts(build_id)
        if artifacts:
            return {"build_id": build_id, "artifacts": artifacts}
    
    raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

@app.get("/build/{build_id}/download")
async def download_build_artifact(build_id: str, filename: Optional[str] = None):
    """Download build artifact"""
    # Find the build and return the file
    for manager in [desktop_builder_manager, mobile_builder_manager,
                   embedded_builder_manager, edge_builder_manager]:
        file_path = await manager.get_artifact_path(build_id, filename)
        if file_path and os.path.exists(file_path):
            return FileResponse(
                path=file_path,
                filename=filename or os.path.basename(file_path),
                media_type='application/octet-stream'
            )
    
    raise HTTPException(status_code=404, detail=f"Artifact not found")

# === DISTRIBUTION ENDPOINTS ===

@app.post("/distribute")
async def create_distribution(dist_request: DistributionRequest):
    """Create distribution package"""
    try:
        channel = UpdateChannel(dist_request.channel)
        strategy = RolloutStrategy(dist_request.rollout_strategy)
        
        distribution_id = await distribution_system.create_distribution(
            build_id=dist_request.build_id,
            channel=channel,
            rollout_strategy=strategy,
            target_regions=dist_request.regions,
            target_platforms=dist_request.platforms,
            metadata=dist_request.metadata
        )
        
        return {
            "distribution_id": distribution_id,
            "build_id": dist_request.build_id,
            "channel": dist_request.channel,
            "strategy": dist_request.rollout_strategy,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Distribution creation failed: {str(e)}")

@app.get("/distribute/{distribution_id}/status")
async def get_distribution_status(distribution_id: str):
    """Get distribution status"""
    status = await distribution_system.get_distribution_status(distribution_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Distribution {distribution_id} not found")
    
    return status

@app.post("/distribute/{distribution_id}/deploy")
async def deploy_distribution(distribution_id: str):
    """Deploy distribution"""
    success = await distribution_system.deploy_distribution(distribution_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Distribution {distribution_id} not found or cannot be deployed")
    
    return {
        "distribution_id": distribution_id,
        "status": "deploying",
        "deployed_at": datetime.now().isoformat()
    }

@app.post("/distribute/{distribution_id}/rollback")
async def rollback_distribution(distribution_id: str):
    """Rollback distribution"""
    success = await distribution_system.rollback_distribution(distribution_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Distribution {distribution_id} not found or cannot be rolled back")
    
    return {
        "distribution_id": distribution_id,
        "status": "rolling_back",
        "rollback_at": datetime.now().isoformat()
    }

# === OPTIMIZATION ENDPOINTS ===

@app.get("/optimize/profiles")
async def get_optimization_profiles():
    """Get available optimization profiles"""
    return await build_optimizer.get_available_profiles()

@app.post("/optimize/analyze")
async def analyze_build_optimization(build_id: str):
    """Analyze build for optimization opportunities"""
    analysis = await build_optimizer.analyze_build(build_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found for analysis")
    
    return analysis

@app.post("/optimize/apply")
async def apply_build_optimizations(build_id: str, optimizations: List[str]):
    """Apply specific optimizations to a build"""
    success = await build_optimizer.apply_optimizations(build_id, optimizations)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found or optimizations could not be applied")
    
    return {
        "build_id": build_id,
        "optimizations": optimizations,
        "status": "applied",
        "applied_at": datetime.now().isoformat()
    }

# === PLATFORM DETECTION ENDPOINTS ===

@app.get("/detect/platform")
async def detect_current_platform():
    """Detect current platform"""
    detector = PlatformDetector()
    platform_info = detector.detect_platform()
    
    return {
        "platform": platform_info,
        "detected_at": datetime.now().isoformat()
    }

@app.post("/detect/requirements")
async def detect_build_requirements(source_path: str):
    """Detect build requirements from source code"""
    detector = PlatformDetector()
    requirements = await detector.detect_build_requirements(source_path)
    
    return {
        "source_path": source_path,
        "requirements": requirements,
        "detected_at": datetime.now().isoformat()
    }

# === PERFORMANCE PROFILING ENDPOINTS ===

@app.post("/performance/start-profiling")
async def start_performance_profiling():
    """Start real-time performance profiling"""
    await start_profiling()
    return {
        "status": "profiling_started",
        "started_at": datetime.now().isoformat()
    }

@app.post("/performance/stop-profiling")
async def stop_performance_profiling():
    """Stop performance profiling"""
    await stop_profiling()
    return {
        "status": "profiling_stopped",
        "stopped_at": datetime.now().isoformat()
    }

@app.get("/performance/summary")
async def get_performance_profiling_summary():
    """Get comprehensive performance summary"""
    summary = get_performance_summary()
    return {
        "performance_summary": summary,
        "retrieved_at": datetime.now().isoformat()
    }

@app.get("/performance/recommendations")
async def get_performance_recommendations():
    """Get optimization recommendations based on performance analysis"""
    recommendations = get_optimization_recommendations()
    return {
        "recommendations": recommendations,
        "generated_at": datetime.now().isoformat()
    }

@app.post("/performance/analyze-bottlenecks")
async def analyze_performance_bottlenecks():
    """Analyze current performance bottlenecks using advanced algorithms"""
    profiler = get_profiler()
    analyzer = get_analyzer()
    
    # Get current performance data
    performance_data = profiler.get_performance_summary()
    
    # Perform bottleneck analysis
    analysis_result = await analyzer.analyze_bottlenecks(
        performance_data, 
        AnalysisType.REAL_TIME
    )
    
    return {
        "analysis_result": {
            "timestamp": analysis_result.timestamp,
            "analysis_type": analysis_result.analysis_type.value,
            "bottlenecks_found": len(analysis_result.bottlenecks_found),
            "patterns_detected": [
                {
                    "pattern": pattern.pattern.value,
                    "frequency": pattern.frequency,
                    "severity_trend": pattern.severity_trend,
                    "locations": list(pattern.locations)
                }
                for pattern in analysis_result.patterns_detected
            ],
            "resolution_actions": [
                {
                    "id": action.id,
                    "strategy": action.strategy.value,
                    "description": action.description,
                    "estimated_impact": action.estimated_impact,
                    "risk_level": action.risk_level
                }
                for action in analysis_result.resolution_actions
            ],
            "confidence_score": analysis_result.confidence_score
        },
        "analyzed_at": datetime.now().isoformat()
    }

@app.post("/performance/execute-resolution/{action_id}")
async def execute_resolution_action(action_id: str, parameters: Optional[Dict[str, Any]] = None):
    """Execute a performance resolution action"""
    analyzer = get_analyzer()
    
    result = await analyzer.execute_resolution_action(action_id, parameters)
    
    return {
        "action_id": action_id,
        "execution_result": result,
        "executed_at": datetime.now().isoformat()
    }

@app.get("/performance/analysis-history")
async def get_performance_analysis_history():
    """Get performance analysis history and trends"""
    analyzer = get_analyzer()
    summary = analyzer.get_analysis_summary()
    
    return {
        "analysis_history": summary,
        "retrieved_at": datetime.now().isoformat()
    }

# === ANALYTICS DASHBOARD ENDPOINTS ===

@app.get("/analytics/dashboards")
async def get_analytics_dashboards():
    """Get list of available analytics dashboards"""
    dashboard = get_dashboard()
    dashboards = dashboard.get_dashboards()
    
    return {
        "dashboards": dashboards,
        "retrieved_at": datetime.now().isoformat()
    }

@app.get("/analytics/dashboard/{dashboard_id}")
async def get_analytics_dashboard(dashboard_id: str, 
                                start_time: Optional[float] = None,
                                end_time: Optional[float] = None,
                                aggregation: Optional[str] = "avg"):
    """Get rendered analytics dashboard data"""
    dashboard = get_dashboard()
    
    filters = {}
    if start_time:
        filters['start_time'] = start_time
    if end_time:
        filters['end_time'] = end_time
    if aggregation:
        filters['aggregation'] = aggregation
    
    try:
        dashboard_data = await dashboard.get_dashboard(dashboard_id, filters)
        return dashboard_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/analytics/metrics/summary")
async def get_analytics_metrics_summary():
    """Get summary of all analytics metrics"""
    dashboard = get_dashboard()
    summary = dashboard.get_metrics_summary()
    
    return {
        "metrics_summary": summary,
        "retrieved_at": datetime.now().isoformat()
    }

@app.post("/analytics/metrics/add")
async def add_analytics_metric_data(metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Add data point to analytics metric"""
    dashboard = get_dashboard()
    dashboard.add_metric_data(metric_name, value, labels)
    
    return {
        "metric_name": metric_name,
        "value": value,
        "labels": labels or {},
        "added_at": datetime.now().isoformat()
    }

@app.get("/analytics/alerts/active")
async def get_active_analytics_alerts():
    """Get currently active alerts"""
    dashboard = get_dashboard()
    active_alerts = dashboard.get_active_alerts()
    
    return {
        "active_alerts": active_alerts,
        "count": len(active_alerts),
        "retrieved_at": datetime.now().isoformat()
    }

@app.get("/analytics/alerts/history")
async def get_analytics_alert_history(hours: int = 24):
    """Get alert history for specified hours"""
    dashboard = get_dashboard()
    alert_history = dashboard.get_alert_history(hours)
    
    return {
        "alert_history": alert_history,
        "hours": hours,
        "count": len(alert_history),
        "retrieved_at": datetime.now().isoformat()
    }

@app.post("/analytics/dashboard/create")
async def create_custom_dashboard(dashboard_config: Dict[str, Any]):
    """Create custom analytics dashboard"""
    dashboard = get_dashboard()
    
    try:
        # Parse dashboard configuration
        charts = []
        for chart_config in dashboard_config.get('charts', []):
            chart = ChartConfig(
                id=chart_config['id'],
                title=chart_config['title'],
                type=ChartType(chart_config['type']),
                metrics=chart_config['metrics'],
                width=chart_config.get('width', 12),
                height=chart_config.get('height', 300),
                refresh_interval=chart_config.get('refresh_interval', 5000),
                color_scheme=chart_config.get('color_scheme', 'default'),
                options=chart_config.get('options', {})
            )
            charts.append(chart)
        
        custom_dashboard = Dashboard(
            id=dashboard_config['id'],
            name=dashboard_config['name'],
            description=dashboard_config.get('description', ''),
            charts=charts,
            layout=dashboard_config.get('layout', {'columns': 12, 'rows': 'auto'}),
            filters=dashboard_config.get('filters', {}),
            auto_refresh=dashboard_config.get('auto_refresh', True)
        )
        
        dashboard.register_dashboard(custom_dashboard)
        
        return {
            "dashboard_id": custom_dashboard.id,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid dashboard configuration: {str(e)}")

@app.post("/analytics/alert/create")
async def create_custom_alert(alert_config: Dict[str, Any]):
    """Create custom analytics alert"""
    dashboard = get_dashboard()
    
    try:
        alert = Alert(
            id=alert_config['id'],
            name=alert_config['name'],
            description=alert_config.get('description', ''),
            level=AlertLevel(alert_config['level']),
            condition=alert_config['condition'],
            metric=alert_config['metric'],
            threshold=float(alert_config['threshold'])
        )
        
        dashboard.register_alert(alert)
        
        return {
            "alert_id": alert.id,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid alert configuration: {str(e)}")

# === PROJECT MANAGEMENT ENDPOINTS ===

@app.post("/projects")
async def create_project(name: str, template: Optional[str] = None):
    """Create new project"""
    project_path = f"projects/{name}"
    
    if os.path.exists(project_path):
        raise HTTPException(status_code=400, detail=f"Project {name} already exists")
    
    os.makedirs(project_path, exist_ok=True)
    
    # Create project from template if specified
    if template:
        # Template creation logic would go here
        pass
    
    return {
        "project_name": name,
        "project_path": project_path,
        "template": template,
        "status": "created",
        "created_at": datetime.now().isoformat()
    }

@app.get("/projects")
async def list_projects():
    """List all projects"""
    projects_dir = "projects"
    projects = []
    
    if os.path.exists(projects_dir):
        for item in os.listdir(projects_dir):
            project_path = os.path.join(projects_dir, item)
            if os.path.isdir(project_path):
                projects.append({
                    "name": item,
                    "path": project_path,
                    "modified": datetime.fromtimestamp(os.path.getmtime(project_path)).isoformat()
                })
    
    return {"projects": projects}

@app.delete("/projects/{project_name}")
async def delete_project(project_name: str):
    """Delete project"""
    project_path = f"projects/{project_name}"
    
    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail=f"Project {project_name} not found")
    
    # In a real implementation, would safely delete the directory
    # For now, just return success
    
    return {
        "project_name": project_name,
        "status": "deleted",
        "deleted_at": datetime.now().isoformat()
    }

# === WEBSOCKET ENDPOINT ===

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def startup_event():
    """Startup event handler"""
    logger.info("Platform Builders service starting up...")
    
    # Start performance profiling automatically
    await start_profiling()
    logger.info("Performance profiling started")
    
    # Start analytics dashboard
    await start_dashboard()
    logger.info("Analytics dashboard started")

async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Platform Builders service shutting down...")
    
    # Stop performance profiling
    await stop_profiling()
    logger.info("Performance profiling stopped")
    
    # Stop analytics dashboard
    await stop_dashboard()
    logger.info("Analytics dashboard stopped")

# Add event handlers
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

if __name__ == "__main__":
    port = build_config.port
    uvicorn.run(
        "main:app",
        host=build_config.host,
        port=port,
        log_level=build_config.log_level.value.lower(),
        reload=build_config.debug
    )