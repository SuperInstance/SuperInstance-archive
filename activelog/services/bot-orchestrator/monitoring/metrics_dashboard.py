import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import threading
import statistics
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import plotly.graph_objs as go
import plotly.utils

logger = logging.getLogger(__name__)

class MetricAggregation(Enum):
    AVERAGE = "average"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P95 = "p95"
    P99 = "p99"

class TimeInterval(Enum):
    SECOND = "1s"
    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    HOUR = "1h"
    DAY = "1d"

@dataclass
class MetricPoint:
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class MetricSeries:
    name: str
    points: List[MetricPoint] = field(default_factory=list)
    aggregation: MetricAggregation = MetricAggregation.AVERAGE
    interval: TimeInterval = TimeInterval.MINUTE
    
    def add_point(self, value: float, timestamp: datetime = None, labels: Dict[str, str] = None):
        point = MetricPoint(
            timestamp=timestamp or datetime.now(),
            value=value,
            labels=labels or {}
        )
        self.points.append(point)
        
        # Keep only recent points (last 24 hours)
        cutoff_time = datetime.now() - timedelta(days=1)
        self.points = [p for p in self.points if p.timestamp > cutoff_time]
    
    def get_aggregated_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get aggregated data points for a time range"""
        relevant_points = [
            p for p in self.points 
            if start_time <= p.timestamp <= end_time
        ]
        
        if not relevant_points:
            return []
        
        # Group points by time interval
        interval_seconds = self._get_interval_seconds()
        grouped_points = defaultdict(list)
        
        for point in relevant_points:
            # Round timestamp to interval
            epoch = point.timestamp.timestamp()
            rounded_epoch = (epoch // interval_seconds) * interval_seconds
            rounded_time = datetime.fromtimestamp(rounded_epoch)
            grouped_points[rounded_time].append(point.value)
        
        # Aggregate each group
        result = []
        for timestamp, values in sorted(grouped_points.items()):
            aggregated_value = self._aggregate_values(values)
            result.append({
                "timestamp": timestamp.isoformat(),
                "value": aggregated_value,
                "count": len(values)
            })
        
        return result
    
    def _get_interval_seconds(self) -> int:
        """Get interval in seconds"""
        interval_map = {
            TimeInterval.SECOND: 1,
            TimeInterval.MINUTE: 60,
            TimeInterval.FIVE_MINUTES: 300,
            TimeInterval.FIFTEEN_MINUTES: 900,
            TimeInterval.HOUR: 3600,
            TimeInterval.DAY: 86400
        }
        return interval_map.get(self.interval, 60)
    
    def _aggregate_values(self, values: List[float]) -> float:
        """Aggregate values based on aggregation type"""
        if not values:
            return 0.0
        
        if self.aggregation == MetricAggregation.AVERAGE:
            return statistics.mean(values)
        elif self.aggregation == MetricAggregation.SUM:
            return sum(values)
        elif self.aggregation == MetricAggregation.MIN:
            return min(values)
        elif self.aggregation == MetricAggregation.MAX:
            return max(values)
        elif self.aggregation == MetricAggregation.COUNT:
            return len(values)
        elif self.aggregation == MetricAggregation.P95:
            return np.percentile(values, 95)
        elif self.aggregation == MetricAggregation.P99:
            return np.percentile(values, 99)
        else:
            return statistics.mean(values)

class MetricsCollector:
    def __init__(self):
        self.series = {}
        self.lock = threading.RLock()
        
        # Pre-define common metrics
        self._initialize_common_metrics()
    
    def _initialize_common_metrics(self):
        """Initialize common system metrics"""
        common_metrics = [
            ("system.cpu_usage", MetricAggregation.AVERAGE),
            ("system.memory_usage", MetricAggregation.AVERAGE),
            ("system.disk_usage", MetricAggregation.AVERAGE),
            ("tasks.submitted", MetricAggregation.COUNT),
            ("tasks.completed", MetricAggregation.COUNT),
            ("tasks.failed", MetricAggregation.COUNT),
            ("tasks.execution_time", MetricAggregation.AVERAGE),
            ("tasks.queue_depth", MetricAggregation.AVERAGE),
            ("api.requests", MetricAggregation.COUNT),
            ("api.response_time", MetricAggregation.AVERAGE),
            ("api.error_rate", MetricAggregation.AVERAGE),
            ("cache.hit_rate", MetricAggregation.AVERAGE),
            ("cache.size", MetricAggregation.AVERAGE),
            ("bots.active", MetricAggregation.AVERAGE),
            ("bots.utilization", MetricAggregation.AVERAGE),
            ("alerts.active", MetricAggregation.COUNT),
            ("alerts.created", MetricAggregation.COUNT)
        ]
        
        for metric_name, aggregation in common_metrics:
            self.series[metric_name] = MetricSeries(
                name=metric_name,
                aggregation=aggregation
            )
    
    def record_metric(self, name: str, value: float, timestamp: datetime = None, 
                     labels: Dict[str, str] = None):
        """Record a metric value"""
        with self.lock:
            if name not in self.series:
                self.series[name] = MetricSeries(name=name)
            
            self.series[name].add_point(value, timestamp, labels)
    
    def get_metric_data(self, name: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get aggregated metric data for a time range"""
        with self.lock:
            if name not in self.series:
                return []
            
            return self.series[name].get_aggregated_data(start_time, end_time)
    
    def get_all_metrics(self) -> List[str]:
        """Get list of all available metrics"""
        with self.lock:
            return list(self.series.keys())
    
    def get_recent_value(self, name: str) -> Optional[float]:
        """Get the most recent value for a metric"""
        with self.lock:
            if name not in self.series or not self.series[name].points:
                return None
            
            return self.series[name].points[-1].value

class DashboardManager:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.websocket_connections = set()
        self.dashboard_config = self._get_default_dashboard_config()
        
        # Real-time update task
        self.update_task = None
        self.running = False
        self.update_interval = 5  # seconds
    
    async def start(self):
        """Start dashboard manager"""
        self.running = True
        self.update_task = asyncio.create_task(self._update_loop())
        logger.info("Dashboard Manager started")
    
    async def stop(self):
        """Stop dashboard manager"""
        self.running = False
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections
        for ws in self.websocket_connections.copy():
            try:
                await ws.close()
            except:
                pass
        
        logger.info("Dashboard Manager stopped")
    
    def record_metric(self, name: str, value: float, timestamp: datetime = None, 
                     labels: Dict[str, str] = None):
        """Record a metric value"""
        self.metrics_collector.record_metric(name, value, timestamp, labels)
    
    async def add_websocket_connection(self, websocket: WebSocket):
        """Add a WebSocket connection for real-time updates"""
        await websocket.accept()
        self.websocket_connections.add(websocket)
        
        # Send initial dashboard data
        await self._send_dashboard_data(websocket)
        
        logger.info(f"WebSocket connection added: {websocket.client}")
    
    async def remove_websocket_connection(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.websocket_connections.discard(websocket)
        logger.info(f"WebSocket connection removed: {websocket.client}")
    
    async def get_dashboard_data(self, time_range: str = "1h") -> Dict[str, Any]:
        """Get complete dashboard data"""
        end_time = datetime.now()
        start_time = self._parse_time_range(time_range, end_time)
        
        dashboard_data = {
            "timestamp": end_time.isoformat(),
            "time_range": time_range,
            "charts": []
        }
        
        # Generate data for each chart in dashboard config
        for chart_config in self.dashboard_config["charts"]:
            chart_data = await self._generate_chart_data(chart_config, start_time, end_time)
            dashboard_data["charts"].append(chart_data)
        
        # Add summary statistics
        dashboard_data["summary"] = await self._generate_summary_stats()
        
        return dashboard_data
    
    async def _generate_chart_data(self, chart_config: Dict[str, Any], 
                                 start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate data for a specific chart"""
        chart_data = {
            "id": chart_config["id"],
            "title": chart_config["title"],
            "type": chart_config["type"],
            "series": []
        }
        
        for series_config in chart_config["series"]:
            metric_name = series_config["metric"]
            metric_data = self.metrics_collector.get_metric_data(metric_name, start_time, end_time)
            
            series_data = {
                "name": series_config["name"],
                "data": metric_data,
                "color": series_config.get("color", "#007bff")
            }
            chart_data["series"].append(series_data)
        
        return chart_data
    
    async def _generate_summary_stats(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        summary = {}
        
        # Key metrics with recent values
        key_metrics = [
            "system.cpu_usage",
            "system.memory_usage", 
            "tasks.queue_depth",
            "bots.active",
            "alerts.active",
            "cache.hit_rate"
        ]
        
        for metric in key_metrics:
            value = self.metrics_collector.get_recent_value(metric)
            if value is not None:
                summary[metric] = {
                    "current": value,
                    "unit": self._get_metric_unit(metric)
                }
        
        return summary
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """Get unit for a metric"""
        unit_map = {
            "system.cpu_usage": "%",
            "system.memory_usage": "%",
            "system.disk_usage": "%",
            "tasks.execution_time": "ms",
            "api.response_time": "ms",
            "api.error_rate": "%",
            "cache.hit_rate": "%",
            "bots.utilization": "%"
        }
        return unit_map.get(metric_name, "")
    
    def _parse_time_range(self, time_range: str, end_time: datetime) -> datetime:
        """Parse time range string to start time"""
        time_map = {
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7)
        }
        
        delta = time_map.get(time_range, timedelta(hours=1))
        return end_time - delta
    
    def _get_default_dashboard_config(self) -> Dict[str, Any]:
        """Get default dashboard configuration"""
        return {
            "title": "Bot Orchestrator Dashboard",
            "refresh_interval": 5,
            "charts": [
                {
                    "id": "system_metrics",
                    "title": "System Metrics",
                    "type": "line",
                    "series": [
                        {"metric": "system.cpu_usage", "name": "CPU Usage", "color": "#ff6b6b"},
                        {"metric": "system.memory_usage", "name": "Memory Usage", "color": "#4ecdc4"},
                        {"metric": "system.disk_usage", "name": "Disk Usage", "color": "#45b7d1"}
                    ]
                },
                {
                    "id": "task_metrics",
                    "title": "Task Metrics",
                    "type": "line",
                    "series": [
                        {"metric": "tasks.submitted", "name": "Submitted", "color": "#96ceb4"},
                        {"metric": "tasks.completed", "name": "Completed", "color": "#6c5ce7"},
                        {"metric": "tasks.failed", "name": "Failed", "color": "#fd79a8"}
                    ]
                },
                {
                    "id": "performance_metrics",
                    "title": "Performance Metrics",
                    "type": "line",
                    "series": [
                        {"metric": "tasks.execution_time", "name": "Avg Execution Time", "color": "#fdcb6e"},
                        {"metric": "api.response_time", "name": "API Response Time", "color": "#e17055"}
                    ]
                },
                {
                    "id": "bot_metrics",
                    "title": "Bot Metrics",
                    "type": "area",
                    "series": [
                        {"metric": "bots.active", "name": "Active Bots", "color": "#00b894"},
                        {"metric": "bots.utilization", "name": "Utilization", "color": "#0984e3"}
                    ]
                },
                {
                    "id": "cache_metrics", 
                    "title": "Cache Metrics",
                    "type": "line",
                    "series": [
                        {"metric": "cache.hit_rate", "name": "Hit Rate", "color": "#00cec9"},
                        {"metric": "cache.size", "name": "Cache Size", "color": "#6c5ce7"}
                    ]
                },
                {
                    "id": "alert_metrics",
                    "title": "Alert Metrics",
                    "type": "bar",
                    "series": [
                        {"metric": "alerts.active", "name": "Active Alerts", "color": "#e84393"},
                        {"metric": "alerts.created", "name": "Created", "color": "#fd79a8"}
                    ]
                }
            ]
        }
    
    async def _update_loop(self):
        """Send real-time updates to WebSocket connections"""
        while self.running:
            try:
                if self.websocket_connections:
                    # Get latest dashboard data
                    dashboard_data = await self.get_dashboard_data("5m")
                    
                    # Send to all connected clients
                    disconnected = set()
                    for websocket in self.websocket_connections.copy():
                        try:
                            await websocket.send_json({
                                "type": "dashboard_update",
                                "data": dashboard_data
                            })
                        except Exception as e:
                            logger.error(f"Failed to send update to WebSocket: {e}")
                            disconnected.add(websocket)
                    
                    # Remove disconnected clients
                    self.websocket_connections -= disconnected
                
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dashboard update loop error: {e}")
                await asyncio.sleep(30)
    
    async def _send_dashboard_data(self, websocket: WebSocket):
        """Send initial dashboard data to a WebSocket connection"""
        try:
            dashboard_data = await self.get_dashboard_data("1h")
            await websocket.send_json({
                "type": "dashboard_init",
                "data": dashboard_data
            })
        except Exception as e:
            logger.error(f"Failed to send initial dashboard data: {e}")

class DashboardAPI:
    def __init__(self, dashboard_manager: DashboardManager):
        self.dashboard_manager = dashboard_manager
        self.app = FastAPI(title="Metrics Dashboard API")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def dashboard_html():
            """Serve the dashboard HTML"""
            return HTMLResponse(content=self._get_dashboard_html())
        
        @self.app.get("/api/dashboard")
        async def get_dashboard_data(time_range: str = "1h"):
            """Get dashboard data"""
            return await self.dashboard_manager.get_dashboard_data(time_range)
        
        @self.app.get("/api/metrics")
        async def get_available_metrics():
            """Get list of available metrics"""
            return {"metrics": self.dashboard_manager.metrics_collector.get_all_metrics()}
        
        @self.app.get("/api/metrics/{metric_name}")
        async def get_metric_data(metric_name: str, time_range: str = "1h"):
            """Get data for a specific metric"""
            end_time = datetime.now()
            start_time = self.dashboard_manager._parse_time_range(time_range, end_time)
            
            data = self.dashboard_manager.metrics_collector.get_metric_data(
                metric_name, start_time, end_time
            )
            
            return {
                "metric": metric_name,
                "time_range": time_range,
                "data": data
            }
        
        @self.app.websocket("/ws/dashboard")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time dashboard updates"""
            await self.dashboard_manager.add_websocket_connection(websocket)
            
            try:
                while True:
                    # Keep connection alive and handle client messages
                    message = await websocket.receive_json()
                    
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("type") == "request_update":
                        await self.dashboard_manager._send_dashboard_data(websocket)
            
            except WebSocketDisconnect:
                await self.dashboard_manager.remove_websocket_connection(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await self.dashboard_manager.remove_websocket_connection(websocket)
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Bot Orchestrator Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: flex; justify-content: space-around; margin-bottom: 30px; }
        .summary-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; min-width: 150px; }
        .summary-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .summary-label { color: #666; margin-top: 5px; }
        .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; }
        .chart { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .chart-title { font-size: 18px; font-weight: bold; margin-bottom: 15px; text-align: center; }
        .status { position: fixed; top: 10px; right: 10px; padding: 10px; border-radius: 5px; }
        .status.connected { background-color: #d4edda; color: #155724; }
        .status.disconnected { background-color: #f8d7da; color: #721c24; }
        .controls { text-align: center; margin-bottom: 20px; }
        .time-selector { margin: 0 10px; padding: 5px 10px; }
    </style>
</head>
<body>
    <div class="status" id="status">Connecting...</div>
    
    <div class="header">
        <h1>Bot Orchestrator Dashboard</h1>
        <div class="controls">
            <label>Time Range:</label>
            <select class="time-selector" id="timeRange">
                <option value="5m">5 minutes</option>
                <option value="15m">15 minutes</option>
                <option value="1h" selected>1 hour</option>
                <option value="6h">6 hours</option>
                <option value="24h">24 hours</option>
                <option value="7d">7 days</option>
            </select>
            <button onclick="refreshDashboard()">Refresh</button>
        </div>
    </div>
    
    <div id="summary" class="summary"></div>
    <div id="charts" class="charts"></div>
    
    <script>
        let socket = null;
        let currentData = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = protocol + '//' + window.location.host + '/ws/dashboard';
            
            socket = new WebSocket(wsUrl);
            
            socket.onopen = function(event) {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'status connected';
            };
            
            socket.onmessage = function(event) {
                const message = JSON.parse(event.data);
                if (message.type === 'dashboard_init' || message.type === 'dashboard_update') {
                    updateDashboard(message.data);
                }
            };
            
            socket.onclose = function(event) {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'status disconnected';
                
                // Reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };
            
            socket.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function updateDashboard(data) {
            currentData = data;
            updateSummary(data.summary);
            updateCharts(data.charts);
        }
        
        function updateSummary(summary) {
            const summaryDiv = document.getElementById('summary');
            summaryDiv.innerHTML = '';
            
            for (const [metric, info] of Object.entries(summary)) {
                const card = document.createElement('div');
                card.className = 'summary-card';
                card.innerHTML = \`
                    <div class="summary-value">\${info.current.toFixed(1)}\${info.unit}</div>
                    <div class="summary-label">\${metric.split('.').pop().replace('_', ' ').toUpperCase()}</div>
                \`;
                summaryDiv.appendChild(card);
            }
        }
        
        function updateCharts(charts) {
            const chartsDiv = document.getElementById('charts');
            chartsDiv.innerHTML = '';
            
            charts.forEach(chart => {
                const chartDiv = document.createElement('div');
                chartDiv.className = 'chart';
                chartDiv.innerHTML = \`
                    <div class="chart-title">\${chart.title}</div>
                    <div id="chart-\${chart.id}" style="height: 300px;"></div>
                \`;
                chartsDiv.appendChild(chartDiv);
                
                renderChart(chart);
            });
        }
        
        function renderChart(chartConfig) {
            const traces = chartConfig.series.map(series => {
                const x = series.data.map(point => point.timestamp);
                const y = series.data.map(point => point.value);
                
                return {
                    x: x,
                    y: y,
                    name: series.name,
                    type: chartConfig.type === 'line' ? 'scatter' : chartConfig.type,
                    mode: chartConfig.type === 'line' ? 'lines+markers' : undefined,
                    line: { color: series.color },
                    marker: { color: series.color }
                };
            });
            
            const layout = {
                title: '',
                xaxis: { title: 'Time' },
                yaxis: { title: 'Value' },
                showlegend: true,
                margin: { t: 20, r: 20, b: 40, l: 60 }
            };
            
            Plotly.newPlot(\`chart-\${chartConfig.id}\`, traces, layout, {responsive: true});
        }
        
        function refreshDashboard() {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({type: 'request_update'}));
            } else {
                // Fallback to HTTP request
                const timeRange = document.getElementById('timeRange').value;
                fetch(\`/api/dashboard?time_range=\${timeRange}\`)
                    .then(response => response.json())
                    .then(data => updateDashboard(data))
                    .catch(error => console.error('Failed to refresh dashboard:', error));
            }
        }
        
        // Time range selector change handler
        document.getElementById('timeRange').addEventListener('change', function() {
            refreshDashboard();
        });
        
        // Initialize
        connectWebSocket();
        
        // Keep connection alive
        setInterval(() => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({type: 'ping'}));
            }
        }, 30000);
    </script>
</body>
</html>
        """
    
    def get_app(self):
        """Get FastAPI application"""
        return self.app