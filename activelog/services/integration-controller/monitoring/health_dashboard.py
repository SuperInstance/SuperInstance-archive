"""
Service Health Monitoring Dashboard

Provides comprehensive health monitoring and dashboard capabilities including:
- Real-time service health monitoring
- Interactive web dashboard with charts and metrics
- Health status aggregation and alerting
- Service dependency health visualization
- Historical health data and trending
- Custom health check definitions
- Integration with service mesh health monitoring
- Alert notifications and escalation
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
import logging
from aiohttp import web, WSMsgType
import aiohttp_cors
import weakref

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class ServiceHealthMetrics:
    """Service health metrics data"""
    service_name: str
    instance_id: str
    status: HealthStatus
    response_time: float
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    error_rate: float = 0.0
    request_rate: float = 0.0
    uptime: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    version: str = ""
    tags: List[str] = field(default_factory=list)

@dataclass
class HealthAlert:
    """Health alert definition"""
    alert_id: str
    service_name: str
    alert_type: str
    level: AlertLevel
    message: str
    threshold: float
    current_value: float
    triggered_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    title: str = "Integration Controller Health Dashboard"
    refresh_interval: int = 5000  # milliseconds
    history_retention: int = 7  # days
    alert_retention: int = 30  # days
    show_dependencies: bool = True
    show_metrics: bool = True
    show_alerts: bool = True
    custom_metrics: List[str] = field(default_factory=list)

class HealthDataStorage:
    """Storage for health monitoring data"""
    
    def __init__(self, db_path: str = "health_monitoring.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Service health metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                instance_id TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time REAL,
                cpu_usage REAL,
                memory_usage REAL,
                error_rate REAL,
                request_rate REAL,
                uptime INTEGER,
                timestamp TEXT NOT NULL,
                custom_metrics TEXT,
                dependencies TEXT,
                version TEXT,
                tags TEXT
            )
        ''')
        
        # Health alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_alerts (
                alert_id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                threshold REAL,
                current_value REAL,
                triggered_at TEXT NOT NULL,
                resolved_at TEXT,
                acknowledged BOOLEAN DEFAULT FALSE,
                metadata TEXT
            )
        ''')
        
        # Service registry table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_registry (
                service_name TEXT NOT NULL,
                instance_id TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                last_seen TEXT NOT NULL,
                metadata TEXT,
                PRIMARY KEY (service_name, instance_id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_health_timestamp ON health_metrics(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_health_service ON health_metrics(service_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_service ON health_alerts(service_name)')
        
        conn.commit()
        conn.close()
    
    def store_health_metrics(self, metrics: ServiceHealthMetrics):
        """Store health metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO health_metrics 
            (service_name, instance_id, status, response_time, cpu_usage, memory_usage,
             error_rate, request_rate, uptime, timestamp, custom_metrics, dependencies, version, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.service_name, metrics.instance_id, metrics.status.value,
            metrics.response_time, metrics.cpu_usage, metrics.memory_usage,
            metrics.error_rate, metrics.request_rate, metrics.uptime,
            metrics.timestamp.isoformat(), json.dumps(metrics.custom_metrics),
            json.dumps(metrics.dependencies), metrics.version, json.dumps(metrics.tags)
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_health_metrics(self, limit: int = 100) -> List[ServiceHealthMetrics]:
        """Get latest health metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY service_name, instance_id ORDER BY timestamp DESC) as rn
                FROM health_metrics
                WHERE timestamp > datetime('now', '-1 hour')
            ) WHERE rn = 1
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        metrics = []
        for row in cursor.fetchall():
            metric = ServiceHealthMetrics(
                service_name=row[1],
                instance_id=row[2],
                status=HealthStatus(row[3]),
                response_time=row[4],
                cpu_usage=row[5] or 0.0,
                memory_usage=row[6] or 0.0,
                error_rate=row[7] or 0.0,
                request_rate=row[8] or 0.0,
                uptime=row[9] or 0,
                timestamp=datetime.fromisoformat(row[10]),
                custom_metrics=json.loads(row[11]) if row[11] else {},
                dependencies=json.loads(row[12]) if row[12] else [],
                version=row[13] or "",
                tags=json.loads(row[14]) if row[14] else []
            )
            metrics.append(metric)
        
        conn.close()
        return metrics
    
    def get_health_history(self, service_name: str, hours: int = 24) -> List[ServiceHealthMetrics]:
        """Get health history for a service"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_time = datetime.now() - timedelta(hours=hours)
        cursor.execute('''
            SELECT * FROM health_metrics 
            WHERE service_name = ? AND timestamp > ? 
            ORDER BY timestamp ASC
        ''', (service_name, since_time.isoformat()))
        
        metrics = []
        for row in cursor.fetchall():
            metric = ServiceHealthMetrics(
                service_name=row[1],
                instance_id=row[2],
                status=HealthStatus(row[3]),
                response_time=row[4],
                cpu_usage=row[5] or 0.0,
                memory_usage=row[6] or 0.0,
                error_rate=row[7] or 0.0,
                request_rate=row[8] or 0.0,
                uptime=row[9] or 0,
                timestamp=datetime.fromisoformat(row[10]),
                custom_metrics=json.loads(row[11]) if row[11] else {},
                dependencies=json.loads(row[12]) if row[12] else [],
                version=row[13] or "",
                tags=json.loads(row[14]) if row[14] else []
            )
            metrics.append(metric)
        
        conn.close()
        return metrics
    
    def store_alert(self, alert: HealthAlert):
        """Store health alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO health_alerts 
            (alert_id, service_name, alert_type, level, message, threshold, current_value,
             triggered_at, resolved_at, acknowledged, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.alert_id, alert.service_name, alert.alert_type, alert.level.value,
            alert.message, alert.threshold, alert.current_value,
            alert.triggered_at.isoformat(),
            alert.resolved_at.isoformat() if alert.resolved_at else None,
            alert.acknowledged, json.dumps(alert.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def get_active_alerts(self) -> List[HealthAlert]:
        """Get active (unresolved) alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM health_alerts 
            WHERE resolved_at IS NULL 
            ORDER BY triggered_at DESC
        ''')
        
        alerts = []
        for row in cursor.fetchall():
            alert = HealthAlert(
                alert_id=row[0],
                service_name=row[1],
                alert_type=row[2],
                level=AlertLevel(row[3]),
                message=row[4],
                threshold=row[5],
                current_value=row[6],
                triggered_at=datetime.fromisoformat(row[7]),
                resolved_at=datetime.fromisoformat(row[8]) if row[8] else None,
                acknowledged=bool(row[9]),
                metadata=json.loads(row[10]) if row[10] else {}
            )
            alerts.append(alert)
        
        conn.close()
        return alerts

class HealthAlerter:
    """Health alerting system"""
    
    def __init__(self, storage: HealthDataStorage):
        self.storage = storage
        self.alert_rules = self._load_default_alert_rules()
        self.active_alerts: Dict[str, HealthAlert] = {}
    
    def _load_default_alert_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load default alerting rules"""
        return {
            "high_response_time": {
                "metric": "response_time",
                "threshold": 5000,  # 5 seconds
                "comparison": ">",
                "level": AlertLevel.WARNING,
                "message": "High response time detected"
            },
            "high_error_rate": {
                "metric": "error_rate",
                "threshold": 0.05,  # 5%
                "comparison": ">",
                "level": AlertLevel.CRITICAL,
                "message": "High error rate detected"
            },
            "high_cpu_usage": {
                "metric": "cpu_usage",
                "threshold": 0.90,  # 90%
                "comparison": ">",
                "level": AlertLevel.WARNING,
                "message": "High CPU usage detected"
            },
            "high_memory_usage": {
                "metric": "memory_usage",
                "threshold": 0.90,  # 90%
                "comparison": ">",
                "level": AlertLevel.WARNING,
                "message": "High memory usage detected"
            },
            "service_unhealthy": {
                "metric": "status",
                "threshold": "unhealthy",
                "comparison": "==",
                "level": AlertLevel.CRITICAL,
                "message": "Service is unhealthy"
            }
        }
    
    def check_alerts(self, metrics: ServiceHealthMetrics) -> List[HealthAlert]:
        """Check metrics against alert rules and generate alerts"""
        triggered_alerts = []
        
        for rule_name, rule in self.alert_rules.items():
            alert_key = f"{metrics.service_name}_{metrics.instance_id}_{rule_name}"
            
            # Get current metric value
            if rule["metric"] == "status":
                current_value = metrics.status.value
            else:
                current_value = getattr(metrics, rule["metric"], 0)
            
            # Check if alert condition is met
            should_trigger = False
            if rule["comparison"] == ">":
                should_trigger = current_value > rule["threshold"]
            elif rule["comparison"] == "<":
                should_trigger = current_value < rule["threshold"]
            elif rule["comparison"] == "==":
                should_trigger = current_value == rule["threshold"]
            
            if should_trigger:
                # Create or update alert
                if alert_key not in self.active_alerts:
                    alert = HealthAlert(
                        alert_id=alert_key,
                        service_name=metrics.service_name,
                        alert_type=rule_name,
                        level=rule["level"],
                        message=f"{rule['message']} - {metrics.service_name}:{metrics.instance_id}",
                        threshold=rule["threshold"],
                        current_value=current_value,
                        metadata={
                            "instance_id": metrics.instance_id,
                            "rule_name": rule_name
                        }
                    )
                    
                    self.active_alerts[alert_key] = alert
                    self.storage.store_alert(alert)
                    triggered_alerts.append(alert)
                    
                    logger.warning(f"Alert triggered: {alert.message}")
            else:
                # Resolve alert if it was active
                if alert_key in self.active_alerts:
                    alert = self.active_alerts[alert_key]
                    alert.resolved_at = datetime.now()
                    
                    self.storage.store_alert(alert)
                    del self.active_alerts[alert_key]
                    
                    logger.info(f"Alert resolved: {alert.message}")
        
        return triggered_alerts

class HealthCollector:
    """Collects health data from services"""
    
    def __init__(self, storage: HealthDataStorage):
        self.storage = storage
        self.alerter = HealthAlerter(storage)
        self.running = False
        self._collection_task = None
        
        # Integration with service mesh health monitoring
        self.service_mesh_health = None
    
    def set_service_mesh_integration(self, service_mesh):
        """Set service mesh integration for health data"""
        self.service_mesh_health = service_mesh
    
    async def start_collection(self, interval: int = 30):
        """Start health data collection"""
        self.running = True
        self._collection_task = asyncio.create_task(self._collection_loop(interval))
        logger.info("Health data collection started")
    
    async def stop_collection(self):
        """Stop health data collection"""
        self.running = False
        if self._collection_task:
            self._collection_task.cancel()
        logger.info("Health data collection stopped")
    
    async def _collection_loop(self, interval: int):
        """Main collection loop"""
        while self.running:
            try:
                await self._collect_health_data()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health collection loop: {e}")
                await asyncio.sleep(5)
    
    async def _collect_health_data(self):
        """Collect health data from all sources"""
        # Collect from service mesh if available
        if self.service_mesh_health:
            await self._collect_from_service_mesh()
        
        # Collect from direct service monitoring
        await self._collect_from_direct_monitoring()
    
    async def _collect_from_service_mesh(self):
        """Collect health data from service mesh"""
        try:
            # Get service health from service mesh
            services = self.service_mesh_health.discover_service("*")  # Get all services
            
            for service_info in services:
                health_data = self.service_mesh_health.get_service_health(service_info["name"])
                
                if health_data:
                    metrics = ServiceHealthMetrics(
                        service_name=service_info["name"],
                        instance_id=service_info.get("instance_id", service_info["host"]),
                        status=HealthStatus(health_data.get("status", "unknown")),
                        response_time=health_data.get("response_time", 0.0),
                        cpu_usage=health_data.get("cpu_usage", 0.0),
                        memory_usage=health_data.get("memory_usage", 0.0),
                        error_rate=health_data.get("error_rate", 0.0),
                        request_rate=health_data.get("request_rate", 0.0),
                        uptime=health_data.get("uptime", 0),
                        custom_metrics=health_data.get("custom_metrics", {}),
                        dependencies=health_data.get("dependencies", []),
                        version=health_data.get("version", ""),
                        tags=health_data.get("tags", [])
                    )
                    
                    self.storage.store_health_metrics(metrics)
                    
                    # Check for alerts
                    self.alerter.check_alerts(metrics)
                    
        except Exception as e:
            logger.error(f"Error collecting from service mesh: {e}")
    
    async def _collect_from_direct_monitoring(self):
        """Collect health data from direct service monitoring"""
        # This would implement direct service monitoring
        # For now, we'll simulate some data
        pass

class HealthDashboardServer:
    """Web server for health monitoring dashboard"""
    
    def __init__(self, storage: HealthDataStorage, config: DashboardConfig = None):
        self.storage = storage
        self.config = config or DashboardConfig()
        self.app = web.Application()
        self.websockets = weakref.WeakSet()
        
        # Setup routes
        self._setup_routes()
        
        # Setup CORS
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
        """Setup web routes"""
        self.app.router.add_get('/', self._dashboard_page)
        self.app.router.add_get('/api/health/current', self._api_current_health)
        self.app.router.add_get('/api/health/history/{service}', self._api_health_history)
        self.app.router.add_get('/api/alerts', self._api_alerts)
        self.app.router.add_get('/api/services', self._api_services)
        self.app.router.add_get('/ws', self._websocket_handler)
        self.app.router.add_static('/', path='static', name='static')
    
    async def _dashboard_page(self, request):
        """Serve the main dashboard page"""
        html_content = self._generate_dashboard_html()
        return web.Response(text=html_content, content_type='text/html')
    
    async def _api_current_health(self, request):
        """API endpoint for current health status"""
        metrics = self.storage.get_latest_health_metrics()
        
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "services": []
        }
        
        for metric in metrics:
            service_data = {
                "name": metric.service_name,
                "instance_id": metric.instance_id,
                "status": metric.status.value,
                "response_time": metric.response_time,
                "cpu_usage": metric.cpu_usage,
                "memory_usage": metric.memory_usage,
                "error_rate": metric.error_rate,
                "request_rate": metric.request_rate,
                "uptime": metric.uptime,
                "version": metric.version,
                "tags": metric.tags,
                "timestamp": metric.timestamp.isoformat()
            }
            response_data["services"].append(service_data)
        
        return web.json_response(response_data)
    
    async def _api_health_history(self, request):
        """API endpoint for service health history"""
        service_name = request.match_info['service']
        hours = int(request.query.get('hours', 24))
        
        metrics = self.storage.get_health_history(service_name, hours)
        
        response_data = {
            "service": service_name,
            "history": []
        }
        
        for metric in metrics:
            data_point = {
                "timestamp": metric.timestamp.isoformat(),
                "status": metric.status.value,
                "response_time": metric.response_time,
                "cpu_usage": metric.cpu_usage,
                "memory_usage": metric.memory_usage,
                "error_rate": metric.error_rate,
                "request_rate": metric.request_rate
            }
            response_data["history"].append(data_point)
        
        return web.json_response(response_data)
    
    async def _api_alerts(self, request):
        """API endpoint for active alerts"""
        alerts = self.storage.get_active_alerts()
        
        response_data = {
            "alerts": []
        }
        
        for alert in alerts:
            alert_data = {
                "alert_id": alert.alert_id,
                "service_name": alert.service_name,
                "alert_type": alert.alert_type,
                "level": alert.level.value,
                "message": alert.message,
                "threshold": alert.threshold,
                "current_value": alert.current_value,
                "triggered_at": alert.triggered_at.isoformat(),
                "acknowledged": alert.acknowledged
            }
            response_data["alerts"].append(alert_data)
        
        return web.json_response(response_data)
    
    async def _api_services(self, request):
        """API endpoint for service list"""
        metrics = self.storage.get_latest_health_metrics()
        
        # Group by service name
        services = {}
        for metric in metrics:
            if metric.service_name not in services:
                services[metric.service_name] = {
                    "name": metric.service_name,
                    "instances": [],
                    "overall_status": "healthy",
                    "total_instances": 0,
                    "healthy_instances": 0
                }
            
            instance_data = {
                "instance_id": metric.instance_id,
                "status": metric.status.value,
                "response_time": metric.response_time,
                "version": metric.version,
                "tags": metric.tags
            }
            
            services[metric.service_name]["instances"].append(instance_data)
            services[metric.service_name]["total_instances"] += 1
            
            if metric.status == HealthStatus.HEALTHY:
                services[metric.service_name]["healthy_instances"] += 1
            
            # Determine overall service status
            if metric.status == HealthStatus.UNHEALTHY:
                services[metric.service_name]["overall_status"] = "unhealthy"
            elif metric.status == HealthStatus.DEGRADED and services[metric.service_name]["overall_status"] != "unhealthy":
                services[metric.service_name]["overall_status"] = "degraded"
        
        return web.json_response({"services": list(services.values())})
    
    async def _websocket_handler(self, request):
        """WebSocket handler for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        logger.info("WebSocket connection established")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # Handle incoming WebSocket messages if needed
                    pass
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            logger.info("WebSocket connection closed")
        
        return ws
    
    def _generate_dashboard_html(self) -> str:
        """Generate the main dashboard HTML"""
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Integration Controller Health Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .header {
                    background: #2c3e50;
                    color: white;
                    padding: 20px;
                    margin: -20px -20px 20px -20px;
                }
                .dashboard-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                }
                .card {
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .status-healthy { color: #27ae60; }
                .status-degraded { color: #f39c12; }
                .status-unhealthy { color: #e74c3c; }
                .status-unknown { color: #95a5a6; }
                .alert {
                    padding: 10px;
                    margin: 5px 0;
                    border-radius: 4px;
                    border-left: 4px solid;
                }
                .alert-warning { 
                    background: #fff3cd;
                    border-color: #f39c12;
                    color: #856404;
                }
                .alert-critical {
                    background: #f8d7da;
                    border-color: #e74c3c;
                    color: #721c24;
                }
                .metric {
                    display: flex;
                    justify-content: space-between;
                    margin: 10px 0;
                    padding: 5px 0;
                    border-bottom: 1px solid #eee;
                }
                .refresh-indicator {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #3498db;
                    color: white;
                    padding: 10px;
                    border-radius: 4px;
                    display: none;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Integration Controller Health Dashboard</h1>
                <p>Real-time monitoring of service health and performance</p>
            </div>

            <div class="refresh-indicator" id="refreshIndicator">
                Updating...
            </div>

            <div class="dashboard-grid">
                <div class="card">
                    <h2>Service Overview</h2>
                    <div id="serviceOverview">Loading...</div>
                </div>

                <div class="card">
                    <h2>Active Alerts</h2>
                    <div id="activeAlerts">Loading...</div>
                </div>

                <div class="card">
                    <h2>Response Time Trends</h2>
                    <canvas id="responseTimeChart" width="400" height="200"></canvas>
                </div>

                <div class="card">
                    <h2>Error Rate Trends</h2>
                    <canvas id="errorRateChart" width="400" height="200"></canvas>
                </div>

                <div class="card">
                    <h2>Service Dependencies</h2>
                    <div id="serviceDependencies">Loading...</div>
                </div>

                <div class="card">
                    <h2>System Metrics</h2>
                    <div id="systemMetrics">Loading...</div>
                </div>
            </div>

            <script>
                // Dashboard JavaScript implementation
                class HealthDashboard {
                    constructor() {
                        this.websocket = null;
                        this.charts = {};
                        this.init();
                    }

                    init() {
                        this.setupWebSocket();
                        this.setupCharts();
                        this.loadInitialData();
                        this.startPeriodicUpdates();
                    }

                    setupWebSocket() {
                        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                        const wsUrl = `${protocol}//${window.location.host}/ws`;
                        
                        this.websocket = new WebSocket(wsUrl);
                        
                        this.websocket.onmessage = (event) => {
                            const data = JSON.parse(event.data);
                            this.handleRealtimeUpdate(data);
                        };

                        this.websocket.onclose = () => {
                            console.log('WebSocket connection closed, attempting to reconnect...');
                            setTimeout(() => this.setupWebSocket(), 5000);
                        };
                    }

                    setupCharts() {
                        // Response time chart
                        const responseCtx = document.getElementById('responseTimeChart').getContext('2d');
                        this.charts.responseTime = new Chart(responseCtx, {
                            type: 'line',
                            data: {
                                labels: [],
                                datasets: []
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Response Time (ms)'
                                        }
                                    }
                                }
                            }
                        });

                        // Error rate chart
                        const errorCtx = document.getElementById('errorRateChart').getContext('2d');
                        this.charts.errorRate = new Chart(errorCtx, {
                            type: 'line',
                            data: {
                                labels: [],
                                datasets: []
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Error Rate (%)'
                                        }
                                    }
                                }
                            }
                        });
                    }

                    async loadInitialData() {
                        await Promise.all([
                            this.updateServiceOverview(),
                            this.updateAlerts(),
                            this.updateCharts()
                        ]);
                    }

                    startPeriodicUpdates() {
                        setInterval(() => {
                            this.showRefreshIndicator();
                            this.loadInitialData().then(() => {
                                this.hideRefreshIndicator();
                            });
                        }, 30000); // Update every 30 seconds
                    }

                    async updateServiceOverview() {
                        try {
                            const response = await fetch('/api/services');
                            const data = await response.json();
                            
                            const overview = document.getElementById('serviceOverview');
                            overview.innerHTML = '';
                            
                            data.services.forEach(service => {
                                const serviceDiv = document.createElement('div');
                                serviceDiv.innerHTML = `
                                    <div class="metric">
                                        <span>${service.name}</span>
                                        <span class="status-${service.overall_status}">${service.overall_status.toUpperCase()}</span>
                                    </div>
                                    <div style="font-size: 12px; color: #666; margin-left: 10px;">
                                        ${service.healthy_instances}/${service.total_instances} instances healthy
                                    </div>
                                `;
                                overview.appendChild(serviceDiv);
                            });
                        } catch (error) {
                            console.error('Error updating service overview:', error);
                        }
                    }

                    async updateAlerts() {
                        try {
                            const response = await fetch('/api/alerts');
                            const data = await response.json();
                            
                            const alertsDiv = document.getElementById('activeAlerts');
                            alertsDiv.innerHTML = '';
                            
                            if (data.alerts.length === 0) {
                                alertsDiv.innerHTML = '<p style="color: #27ae60;">No active alerts</p>';
                            } else {
                                data.alerts.forEach(alert => {
                                    const alertDiv = document.createElement('div');
                                    alertDiv.className = `alert alert-${alert.level}`;
                                    alertDiv.innerHTML = `
                                        <strong>${alert.service_name}</strong>: ${alert.message}
                                        <br><small>Triggered: ${new Date(alert.triggered_at).toLocaleString()}</small>
                                    `;
                                    alertsDiv.appendChild(alertDiv);
                                });
                            }
                        } catch (error) {
                            console.error('Error updating alerts:', error);
                        }
                    }

                    async updateCharts() {
                        // This would fetch historical data and update charts
                        // For brevity, implementing basic structure
                    }

                    handleRealtimeUpdate(data) {
                        // Handle real-time WebSocket updates
                        console.log('Real-time update received:', data);
                    }

                    showRefreshIndicator() {
                        document.getElementById('refreshIndicator').style.display = 'block';
                    }

                    hideRefreshIndicator() {
                        document.getElementById('refreshIndicator').style.display = 'none';
                    }
                }

                // Initialize dashboard when page loads
                window.addEventListener('load', () => {
                    new HealthDashboard();
                });
            </script>
        </body>
        </html>
        '''
    
    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast real-time updates to connected WebSocket clients"""
        if not self.websockets:
            return
        
        message = json.dumps(data)
        disconnected = []
        
        for ws in self.websockets:
            try:
                await ws.send_str(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.append(ws)
        
        # Remove disconnected WebSockets
        for ws in disconnected:
            self.websockets.discard(ws)
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the dashboard web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Health dashboard server started on http://{host}:{port}")
        return runner

class HealthMonitoringDashboard:
    """Main health monitoring dashboard coordinator"""
    
    def __init__(self, service_orchestrator=None):
        self.service_orchestrator = service_orchestrator
        self.storage = HealthDataStorage()
        self.collector = HealthCollector(self.storage)
        self.config = DashboardConfig()
        self.server = HealthDashboardServer(self.storage, self.config)
        self.running = False
    
    def set_service_mesh_integration(self, service_mesh):
        """Set service mesh integration"""
        self.collector.set_service_mesh_integration(service_mesh)
    
    async def start(self, host: str = "0.0.0.0", port: int = 8080, collection_interval: int = 30):
        """Start the health monitoring dashboard"""
        self.running = True
        
        # Start health data collection
        await self.collector.start_collection(collection_interval)
        
        # Start web server
        runner = await self.server.start_server(host, port)
        
        logger.info(f"Health monitoring dashboard started on http://{host}:{port}")
        return runner
    
    async def stop(self):
        """Stop the health monitoring dashboard"""
        self.running = False
        await self.collector.stop_collection()
        logger.info("Health monitoring dashboard stopped")

# Factory function
def create_health_monitoring_dashboard(service_orchestrator=None) -> HealthMonitoringDashboard:
    """Create and return a health monitoring dashboard instance"""
    return HealthMonitoringDashboard(service_orchestrator)