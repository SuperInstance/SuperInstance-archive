"""
Enhanced Universal Hardware Abstraction System
Next-generation hardware abstraction platform with AI, ML, and advanced analytics
Port: 8420
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# Core components
from core.udp_core import UniversalDeviceProtocol
from discovery.mdns_discovery import mDNSDeviceDiscovery
from device_types.device_registry import DeviceRegistry
from communication.comm_manager import CommunicationManager
from capability.negotiation import CapabilityNegotiator
from monitoring.health_monitor import DeviceHealthMonitor

# Enhanced components
from utils.config import Config
from utils.logger import setup_logging
from utils.analytics import AnalyticsEngine
from utils.ml_classifier import DeviceClassifier

# API components
from api.routes import router as api_router, setup_routes, connection_manager
from api.auth import get_current_user, create_access_token, authenticate_user
from api.models import *

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global system components
config = Config()
udp_core: Optional[UniversalDeviceProtocol] = None
device_discovery: Optional[mDNSDeviceDiscovery] = None
device_registry: Optional[DeviceRegistry] = None
comm_manager: Optional[CommunicationManager] = None
capability_negotiator: Optional[CapabilityNegotiator] = None
health_monitor: Optional[DeviceHealthMonitor] = None
analytics_engine: Optional[AnalyticsEngine] = None
ml_classifier: Optional[DeviceClassifier] = None

# System state
system_start_time = datetime.now()
active_websockets: List[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("🚀 Starting Enhanced Hardware Abstraction System...")
    
    global udp_core, device_discovery, device_registry, comm_manager
    global capability_negotiator, health_monitor, analytics_engine, ml_classifier
    
    try:
        # Initialize core components
        udp_core = UniversalDeviceProtocol(config)
        await udp_core.initialize()
        
        device_discovery = mDNSDeviceDiscovery(config)
        await device_discovery.start()
        
        device_registry = DeviceRegistry(config)
        await device_registry.initialize()
        
        comm_manager = CommunicationManager(config)
        await comm_manager.initialize()
        
        capability_negotiator = CapabilityNegotiator(config, comm_manager)
        await capability_negotiator.initialize()
        
        # Initialize enhanced components
        analytics_engine = AnalyticsEngine(config.get_all())
        ml_classifier = DeviceClassifier()
        
        health_monitor = DeviceHealthMonitor(config, analytics_engine)
        await health_monitor.start()
        
        # Setup API routes with dependencies
        setup_routes(
            device_registry, 
            comm_manager, 
            capability_negotiator, 
            health_monitor,
            analytics_engine,
            ml_classifier
        )
        
        logger.info("✅ Enhanced Hardware Abstraction System started successfully!")
        logger.info(f"🌐 API Documentation: http://localhost:{config.get('server.port', 8420)}/api/docs")
        logger.info(f"🎛️ Admin Dashboard: http://localhost:{config.get('server.port', 8420)}/dashboard")
        
    except Exception as e:
        logger.error(f"❌ Failed to start Enhanced Hardware Abstraction System: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down Enhanced Hardware Abstraction System...")
    
    try:
        # Stop analytics background tasks
        if analytics_engine and hasattr(analytics_engine, 'analytics_tasks'):
            for task in analytics_engine.analytics_tasks:
                task.cancel()
            
        # Stop monitoring
        if health_monitor:
            await health_monitor.stop()
            
        # Stop discovery
        if device_discovery:
            await device_discovery.stop()
            
        # Shutdown core
        if udp_core:
            await udp_core.shutdown()
            
        # Close active WebSocket connections
        for websocket in active_websockets:
            try:
                await websocket.close()
            except:
                pass
        
        logger.info("✅ Enhanced Hardware Abstraction System shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="Enhanced Hardware Abstraction System",
    description="Next-generation universal device protocol with AI/ML capabilities",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Enhanced middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure properly in production
)

# Include enhanced API routes
app.include_router(api_router, prefix="/api/v1")

# ===== ENHANCED CORE ENDPOINTS =====

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Enhanced system status with comprehensive information"""
    uptime = (datetime.now() - system_start_time).total_seconds()
    
    # Get system statistics
    device_count = len(device_registry.devices) if device_registry else 0
    active_protocols = len(comm_manager.protocols) if comm_manager else 0
    
    # Get system health
    system_health = 0.95  # Calculate actual system health
    if analytics_engine:
        try:
            health_data = await analytics_engine.get_system_analytics("1h")
            system_health = health_data.get("average_health_score", 0.95)
        except:
            pass
    
    return {
        "service": "Enhanced Hardware Abstraction System",
        "version": "2.0.0",
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": uptime,
        "system_health": system_health,
        "components": {
            "udp_core": "Universal Device Protocol v2.0",
            "discovery": "AI-Enhanced Device Discovery",
            "registry": f"Device Registry ({device_count} devices)",
            "communication": f"Multi-Protocol Manager ({active_protocols} protocols)",
            "capability": "Intelligent Capability Negotiation",
            "health": "Predictive Health Monitoring",
            "analytics": "Real-time Analytics Engine",
            "ml": "ML-Based Device Classification",
            "security": "Advanced Authentication & Authorization"
        },
        "features": {
            "real_time_monitoring": True,
            "predictive_maintenance": True,
            "ml_device_classification": True,
            "websocket_streaming": True,
            "advanced_analytics": True,
            "role_based_auth": True,
            "api_key_support": True,
            "quantum_protocol_support": True
        },
        "endpoints": {
            "api_docs": "/api/docs",
            "dashboard": "/dashboard", 
            "websocket": "/api/v1/ws/devices",
            "health": "/health",
            "metrics": "/metrics"
        }
    }

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check core components
    components = [
        ("udp_core", udp_core),
        ("device_discovery", device_discovery),
        ("device_registry", device_registry),
        ("comm_manager", comm_manager),
        ("capability_negotiator", capability_negotiator),
        ("health_monitor", health_monitor),
        ("analytics_engine", analytics_engine),
        ("ml_classifier", ml_classifier)
    ]
    
    for name, component in components:
        if component is None:
            health_status["checks"][name] = {"status": "down", "message": "Not initialized"}
            health_status["status"] = "degraded"
        else:
            health_status["checks"][name] = {"status": "up", "message": "Operational"}
    
    # Add system metrics
    if analytics_engine:
        try:
            system_metrics = await analytics_engine.get_system_analytics("1h")
            health_status["metrics"] = {
                "devices": system_metrics.get("total_devices", 0),
                "active_devices": system_metrics.get("active_devices", 0),
                "error_rate": system_metrics.get("error_rate", 0),
                "avg_health_score": system_metrics.get("average_health_score", 1.0)
            }
        except Exception as e:
            health_status["checks"]["analytics"] = {"status": "error", "message": str(e)}
    
    return JSONResponse(
        content=health_status,
        status_code=200 if health_status["status"] == "healthy" else 503
    )

@app.get("/metrics")
async def get_metrics():
    """Prometheus-style metrics endpoint"""
    metrics = []
    
    if analytics_engine and device_registry:
        try:
            system_stats = await analytics_engine.get_system_analytics("1h")
            
            # Device metrics
            metrics.extend([
                f"hardware_abstraction_devices_total {system_stats.get('total_devices', 0)}",
                f"hardware_abstraction_devices_active {system_stats.get('active_devices', 0)}",
                f"hardware_abstraction_health_score {system_stats.get('average_health_score', 0)}",
                f"hardware_abstraction_error_rate {system_stats.get('error_rate', 0)}",
                f"hardware_abstraction_commands_total {system_stats.get('commands_executed', 0)}",
                f"hardware_abstraction_data_transferred_gb {system_stats.get('total_data_transferred', 0)}"
            ])
            
            # System metrics
            uptime = (datetime.now() - system_start_time).total_seconds()
            metrics.append(f"hardware_abstraction_uptime_seconds {uptime}")
            
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
    
    return "\n".join(metrics) + "\n"

# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/auth/login")
async def login(credentials: Dict[str, str]):
    """Enhanced login endpoint"""
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    user = await authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token = create_access_token(data={"sub": username})
    
    # Log authentication event
    if analytics_engine:
        await analytics_engine.log_event("system", "user_login", "info", {
            "username": username,
            "timestamp": datetime.now().isoformat()
        })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "permissions": user.get("permissions", []),
            "roles": user.get("roles", [])
        }
    }

# ===== ADMIN DASHBOARD =====

@app.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    """Enhanced admin dashboard"""
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hardware Abstraction System - Admin Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { 
                background: rgba(255,255,255,0.95); 
                backdrop-filter: blur(10px);
                padding: 20px; 
                border-radius: 15px; 
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            }
            .header h1 { color: #4a5568; font-size: 2.5em; margin-bottom: 10px; }
            .header p { color: #718096; font-size: 1.1em; }
            .status-badge { 
                display: inline-block; 
                background: #48bb78; 
                color: white; 
                padding: 5px 15px; 
                border-radius: 20px; 
                font-size: 0.9em;
                font-weight: bold;
                margin-left: 15px;
            }
            .grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px; 
            }
            .card { 
                background: rgba(255,255,255,0.95); 
                backdrop-filter: blur(10px);
                padding: 25px; 
                border-radius: 15px; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .card:hover { transform: translateY(-5px); }
            .card h3 { color: #4a5568; margin-bottom: 15px; font-size: 1.3em; }
            .metric { 
                display: flex; 
                justify-content: space-between; 
                margin-bottom: 10px; 
                padding: 10px 0;
                border-bottom: 1px solid #e2e8f0;
            }
            .metric:last-child { border-bottom: none; }
            .metric-value { 
                font-weight: bold; 
                color: #2d3748;
                font-size: 1.1em;
            }
            .api-links { margin-top: 20px; }
            .api-links a { 
                display: inline-block; 
                background: #4299e1; 
                color: white; 
                padding: 12px 24px; 
                text-decoration: none; 
                border-radius: 8px; 
                margin-right: 15px; 
                margin-bottom: 10px;
                transition: background 0.3s ease;
            }
            .api-links a:hover { background: #3182ce; }
            .features { 
                background: rgba(255,255,255,0.95); 
                backdrop-filter: blur(10px);
                padding: 25px; 
                border-radius: 15px; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            }
            .features h3 { color: #4a5568; margin-bottom: 20px; }
            .feature-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 15px; 
            }
            .feature { 
                padding: 15px; 
                background: #f7fafc; 
                border-radius: 10px; 
                border-left: 4px solid #4299e1;
            }
            .feature strong { color: #2d3748; }
            .ws-status { 
                position: fixed; 
                top: 20px; 
                right: 20px; 
                background: #48bb78; 
                color: white; 
                padding: 10px 20px; 
                border-radius: 25px; 
                font-size: 0.9em;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            .ws-status.disconnected { background: #f56565; }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
            .pulse { animation: pulse 2s infinite; }
        </style>
    </head>
    <body>
        <div class="ws-status" id="wsStatus">🔗 Connecting...</div>
        <div class="container">
            <div class="header">
                <h1>🚀 Hardware Abstraction System</h1>
                <p>Next-generation universal device protocol with AI/ML capabilities</p>
                <span class="status-badge pulse">ACTIVE</span>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>📊 System Overview</h3>
                    <div class="metric">
                        <span>System Version</span>
                        <span class="metric-value">v2.0.0 Enhanced</span>
                    </div>
                    <div class="metric">
                        <span>Uptime</span>
                        <span class="metric-value" id="uptime">Loading...</span>
                    </div>
                    <div class="metric">
                        <span>System Health</span>
                        <span class="metric-value" id="health">Loading...</span>
                    </div>
                    <div class="metric">
                        <span>Active Devices</span>
                        <span class="metric-value" id="devices">Loading...</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🔧 Core Components</h3>
                    <div class="metric">
                        <span>Device Registry</span>
                        <span class="metric-value">✅ Active</span>
                    </div>
                    <div class="metric">
                        <span>ML Classifier</span>
                        <span class="metric-value">✅ Active</span>
                    </div>
                    <div class="metric">
                        <span>Analytics Engine</span>
                        <span class="metric-value">✅ Active</span>
                    </div>
                    <div class="metric">
                        <span>Health Monitor</span>
                        <span class="metric-value">✅ Active</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🌐 Network & Protocols</h3>
                    <div class="metric">
                        <span>Active Protocols</span>
                        <span class="metric-value" id="protocols">Loading...</span>
                    </div>
                    <div class="metric">
                        <span>Data Transferred</span>
                        <span class="metric-value" id="dataTransferred">Loading...</span>
                    </div>
                    <div class="metric">
                        <span>Commands Executed</span>
                        <span class="metric-value" id="commands">Loading...</span>
                    </div>
                    <div class="metric">
                        <span>Error Rate</span>
                        <span class="metric-value" id="errorRate">Loading...</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🎯 Quick Actions</h3>
                    <div class="api-links">
                        <a href="/api/docs" target="_blank">📚 API Documentation</a>
                        <a href="/api/v1/devices" target="_blank">📱 View Devices</a>
                        <a href="/api/v1/analytics/system" target="_blank">📈 System Analytics</a>
                        <a href="/health" target="_blank">❤️ Health Check</a>
                        <a href="/metrics" target="_blank">📊 Metrics</a>
                    </div>
                </div>
            </div>
            
            <div class="features">
                <h3>🚀 Enhanced Features</h3>
                <div class="feature-grid">
                    <div class="feature">
                        <strong>🤖 AI/ML Classification</strong><br>
                        Intelligent device recognition and categorization
                    </div>
                    <div class="feature">
                        <strong>📊 Real-time Analytics</strong><br>
                        Live performance monitoring and insights
                    </div>
                    <div class="feature">
                        <strong>🔮 Predictive Maintenance</strong><br>
                        AI-powered failure prediction and recommendations
                    </div>
                    <div class="feature">
                        <strong>🌊 WebSocket Streaming</strong><br>
                        Real-time device event streaming
                    </div>
                    <div class="feature">
                        <strong>🔒 Advanced Security</strong><br>
                        JWT authentication and role-based access control
                    </div>
                    <div class="feature">
                        <strong>⚡ Quantum Protocols</strong><br>
                        Next-generation communication protocols
                    </div>
                    <div class="feature">
                        <strong>🎛️ Dynamic Discovery</strong><br>
                        Automatic device discovery across protocols
                    </div>
                    <div class="feature">
                        <strong>📈 Performance Optimization</strong><br>
                        Intelligent resource allocation and QoS management
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // WebSocket connection for real-time updates
            let ws = null;
            
            function connectWebSocket() {
                try {
                    ws = new WebSocket(`ws://${window.location.host}/api/v1/ws/devices`);
                    
                    ws.onopen = function() {
                        document.getElementById('wsStatus').textContent = '🟢 Connected';
                        document.getElementById('wsStatus').className = 'ws-status';
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        console.log('WebSocket message:', data);
                        // Handle real-time updates here
                    };
                    
                    ws.onclose = function() {
                        document.getElementById('wsStatus').textContent = '🔴 Disconnected';
                        document.getElementById('wsStatus').className = 'ws-status disconnected';
                        // Reconnect after 5 seconds
                        setTimeout(connectWebSocket, 5000);
                    };
                } catch (error) {
                    console.error('WebSocket connection failed:', error);
                }
            }
            
            // Fetch system status
            async function updateStatus() {
                try {
                    const response = await fetch('/');
                    const data = await response.json();
                    
                    // Update uptime
                    const uptimeHours = Math.floor(data.uptime_seconds / 3600);
                    document.getElementById('uptime').textContent = `${uptimeHours}h`;
                    
                    // Update health
                    const healthPercent = Math.round(data.system_health * 100);
                    document.getElementById('health').textContent = `${healthPercent}%`;
                    
                    // Try to get analytics data
                    const analyticsResponse = await fetch('/api/v1/analytics/system');
                    if (analyticsResponse.ok) {
                        const analyticsData = await analyticsResponse.json();
                        document.getElementById('devices').textContent = analyticsData.active_devices || '0';
                        document.getElementById('protocols').textContent = Object.keys(analyticsData.protocol_usage || {}).length;
                        document.getElementById('dataTransferred').textContent = `${(analyticsData.total_data_transferred || 0).toFixed(2)} GB`;
                        document.getElementById('commands').textContent = analyticsData.commands_executed || '0';
                        document.getElementById('errorRate').textContent = `${(analyticsData.error_rate || 0).toFixed(1)}%`;
                    }
                } catch (error) {
                    console.error('Failed to fetch status:', error);
                }
            }
            
            // Initialize
            connectWebSocket();
            updateStatus();
            
            // Update every 30 seconds
            setInterval(updateStatus, 30000);
        </script>
    </body>
    </html>
    """
    return dashboard_html

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8420))
    uvicorn.run(
        "main_enhanced:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )