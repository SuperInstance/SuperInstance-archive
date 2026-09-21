#!/usr/bin/env python3
"""
Custom ActiveLog Monitoring Dashboard

A comprehensive monitoring dashboard that aggregates data from:
- Prometheus metrics
- Elasticsearch logs
- Jaeger traces
- Business metrics
- Infrastructure health
- Real-time alerts and notifications
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict

import aiohttp
from aiohttp import web, WSMsgType, ClientSession
import aiohttp_cors
from elasticsearch import AsyncElasticsearch
import asyncpg
import redis.asyncio as redis
import plotly.graph_objs as go
import plotly.utils as plotly_utils
import pandas as pd
import weakref

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSource:
    """Base class for data sources"""
    
    def __init__(self, name: str):
        self.name = name
        self.connected = False
    
    async def connect(self):
        """Connect to the data source"""
        pass
    
    async def disconnect(self):
        """Disconnect from the data source"""
        pass
    
    async def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute a query"""
        raise NotImplementedError

class PrometheusDataSource(DataSource):
    """Prometheus data source"""
    
    def __init__(self, url: str = "http://prometheus:9090"):
        super().__init__("prometheus")
        self.url = url
        self.session = None
    
    async def connect(self):
        """Connect to Prometheus"""
        self.session = ClientSession()
        self.connected = True
        logger.info("Connected to Prometheus")
    
    async def disconnect(self):
        """Disconnect from Prometheus"""
        if self.session:
            await self.session.close()
        self.connected = False
    
    async def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute Prometheus query"""
        if not self.session:
            await self.connect()
        
        params = {
            'query': query,
            **kwargs
        }
        
        async with self.session.get(f"{self.url}/api/v1/query", params=params) as response:
            return await response.json()
    
    async def query_range(self, query: str, start: datetime, end: datetime, step: str = "15s") -> Dict[str, Any]:
        """Execute Prometheus range query"""
        if not self.session:
            await self.connect()
        
        params = {
            'query': query,
            'start': start.timestamp(),
            'end': end.timestamp(),
            'step': step
        }
        
        async with self.session.get(f"{self.url}/api/v1/query_range", params=params) as response:
            return await response.json()

class ElasticsearchDataSource(DataSource):
    """Elasticsearch data source"""
    
    def __init__(self, hosts: List[str] = None):
        super().__init__("elasticsearch")
        self.hosts = hosts or ["http://elasticsearch:9200"]
        self.client = None
    
    async def connect(self):
        """Connect to Elasticsearch"""
        self.client = AsyncElasticsearch(
            hosts=self.hosts,
            http_auth=("elastic", "password"),  # Configure properly
            verify_certs=False
        )
        self.connected = True
        logger.info("Connected to Elasticsearch")
    
    async def disconnect(self):
        """Disconnect from Elasticsearch"""
        if self.client:
            await self.client.close()
        self.connected = False
    
    async def query(self, index: str, body: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute Elasticsearch query"""
        if not self.client:
            await self.connect()
        
        return await self.client.search(index=index, body=body, **kwargs)

class PostgreSQLDataSource(DataSource):
    """PostgreSQL data source for business metrics"""
    
    def __init__(self, dsn: str = "postgresql://activelog:password@postgres:5432/activelog"):
        super().__init__("postgresql")
        self.dsn = dsn
        self.pool = None
    
    async def connect(self):
        """Connect to PostgreSQL"""
        self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
        self.connected = True
        logger.info("Connected to PostgreSQL")
    
    async def disconnect(self):
        """Disconnect from PostgreSQL"""
        if self.pool:
            await self.pool.close()
        self.connected = False
    
    async def query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute PostgreSQL query"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

class RedisDataSource(DataSource):
    """Redis data source for real-time data"""
    
    def __init__(self, url: str = "redis://redis:6379"):
        super().__init__("redis")
        self.url = url
        self.client = None
    
    async def connect(self):
        """Connect to Redis"""
        self.client = redis.from_url(self.url)
        self.connected = True
        logger.info("Connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
        self.connected = False
    
    async def query(self, command: str, *args) -> Any:
        """Execute Redis command"""
        if not self.client:
            await self.connect()
        
        return await getattr(self.client, command.lower())(*args)

class DashboardMetrics:
    """Handles metric collection and aggregation"""
    
    def __init__(self, data_sources: Dict[str, DataSource]):
        self.data_sources = data_sources
        self.cache = {}
        self.cache_ttl = 60  # 1 minute cache
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        prometheus = self.data_sources.get('prometheus')
        if not prometheus:
            return {}
        
        # Service uptime
        uptime_query = 'up{job=~"activelog-.*"}'
        uptime_result = await prometheus.query(uptime_query)
        
        # Error rates
        error_query = '''
            sum(rate(http_requests_total{job=~"activelog-.*",status=~"5.."}[5m])) by (service) /
            sum(rate(http_requests_total{job=~"activelog-.*"}[5m])) by (service)
        '''
        error_result = await prometheus.query(error_query)
        
        # Response times
        response_time_query = '''
            histogram_quantile(0.95,
                sum(rate(http_request_duration_seconds_bucket{job=~"activelog-.*"}[5m])) by (service, le)
            )
        '''
        response_time_result = await prometheus.query(response_time_query)
        
        return {
            "uptime": uptime_result,
            "error_rates": error_result,
            "response_times": response_time_result,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_business_metrics(self) -> Dict[str, Any]:
        """Get business KPIs"""
        postgres = self.data_sources.get('postgresql')
        if not postgres:
            return {}
        
        # Active users (last 24 hours)
        active_users_query = """
            SELECT COUNT(DISTINCT user_id) as active_users
            FROM user_activity
            WHERE last_active_at > NOW() - INTERVAL '24 hours'
        """
        active_users = await postgres.query(active_users_query)
        
        # Revenue (last 24 hours)
        revenue_query = """
            SELECT SUM(amount_cents) as revenue_cents
            FROM payments
            WHERE created_at > NOW() - INTERVAL '24 hours'
              AND status = 'completed'
        """
        revenue = await postgres.query(revenue_query)
        
        # New signups (last 24 hours)
        signups_query = """
            SELECT COUNT(*) as new_signups
            FROM users
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """
        signups = await postgres.query(signups_query)
        
        # Subscription metrics
        subscription_query = """
            SELECT 
                plan_type,
                COUNT(*) as count,
                SUM(monthly_amount_cents) as mrr_cents
            FROM subscriptions
            WHERE status = 'active'
            GROUP BY plan_type
        """
        subscriptions = await postgres.query(subscription_query)
        
        return {
            "active_users": active_users[0]['active_users'] if active_users else 0,
            "revenue_24h": revenue[0]['revenue_cents'] if revenue else 0,
            "new_signups_24h": signups[0]['new_signups'] if signups else 0,
            "subscriptions": subscriptions,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_error_analysis(self) -> Dict[str, Any]:
        """Get error analysis from logs"""
        elasticsearch = self.data_sources.get('elasticsearch')
        if not elasticsearch:
            return {}
        
        # Error count by service (last 1 hour)
        error_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"log_severity": "error"}},
                        {"range": {"@timestamp": {"gte": "now-1h"}}}
                    ]
                }
            },
            "aggs": {
                "services": {
                    "terms": {
                        "field": "service_name.keyword",
                        "size": 10
                    }
                },
                "error_types": {
                    "terms": {
                        "field": "message.keyword",
                        "size": 10
                    }
                }
            }
        }
        
        try:
            result = await elasticsearch.query("activelog-logs-*", error_query)
            return {
                "total_errors": result['hits']['total']['value'],
                "errors_by_service": result['aggregations']['services']['buckets'],
                "error_types": result['aggregations']['error_types']['buckets'],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error querying Elasticsearch: {e}")
            return {}
    
    async def get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trends over time"""
        prometheus = self.data_sources.get('prometheus')
        if not prometheus:
            return {}
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=6)
        
        # Request rate trend
        request_rate_query = 'sum(rate(http_requests_total{job=~"activelog-.*"}[5m]))'
        request_rate_result = await prometheus.query_range(
            request_rate_query, start_time, end_time, "1m"
        )
        
        # Error rate trend
        error_rate_query = '''
            sum(rate(http_requests_total{job=~"activelog-.*",status=~"5.."}[5m])) /
            sum(rate(http_requests_total{job=~"activelog-.*"}[5m]))
        '''
        error_rate_result = await prometheus.query_range(
            error_rate_query, start_time, end_time, "1m"
        )
        
        # Response time trend
        response_time_query = '''
            histogram_quantile(0.95,
                sum(rate(http_request_duration_seconds_bucket{job=~"activelog-.*"}[5m])) by (le)
            )
        '''
        response_time_result = await prometheus.query_range(
            response_time_query, start_time, end_time, "1m"
        )
        
        return {
            "request_rate": request_rate_result,
            "error_rate": error_rate_result,
            "response_time": response_time_result,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    
    async def get_infrastructure_metrics(self) -> Dict[str, Any]:
        """Get infrastructure health metrics"""
        prometheus = self.data_sources.get('prometheus')
        if not prometheus:
            return {}
        
        # CPU usage
        cpu_query = '(1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100'
        cpu_result = await prometheus.query(cpu_query)
        
        # Memory usage
        memory_query = '''
            (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
        '''
        memory_result = await prometheus.query(memory_query)
        
        # Disk usage
        disk_query = '''
            (1 - (node_filesystem_free_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100
        '''
        disk_result = await prometheus.query(disk_query)
        
        # Database connections
        db_connections_query = 'sum(postgresql_stat_database_numbackends) by (instance)'
        db_connections_result = await prometheus.query(db_connections_query)
        
        return {
            "cpu_usage": cpu_result,
            "memory_usage": memory_result,
            "disk_usage": disk_result,
            "database_connections": db_connections_result,
            "timestamp": datetime.now().isoformat()
        }

class DashboardServer:
    """Main dashboard web server"""
    
    def __init__(self):
        self.app = web.Application()
        self.data_sources = {}
        self.metrics = None
        self.websocket_connections = weakref.WeakSet()
        self.running = False
        
        # Initialize data sources
        self._initialize_data_sources()
        
        # Setup routes
        self._setup_routes()
        
        # Setup CORS
        self._setup_cors()
        
        # Background tasks
        self._metrics_task = None
        self._broadcast_task = None
    
    def _initialize_data_sources(self):
        """Initialize all data sources"""
        self.data_sources = {
            'prometheus': PrometheusDataSource(),
            'elasticsearch': ElasticsearchDataSource(),
            'postgresql': PostgreSQLDataSource(),
            'redis': RedisDataSource()
        }
        
        self.metrics = DashboardMetrics(self.data_sources)
    
    def _setup_routes(self):
        """Setup web routes"""
        # Static files
        self.app.router.add_get('/', self._dashboard_page)
        
        # API endpoints
        self.app.router.add_get('/api/health', self._health_endpoint)
        self.app.router.add_get('/api/metrics/system', self._system_metrics_endpoint)
        self.app.router.add_get('/api/metrics/business', self._business_metrics_endpoint)
        self.app.router.add_get('/api/metrics/errors', self._error_metrics_endpoint)
        self.app.router.add_get('/api/metrics/performance', self._performance_metrics_endpoint)
        self.app.router.add_get('/api/metrics/infrastructure', self._infrastructure_metrics_endpoint)
        
        # Charts and visualizations
        self.app.router.add_get('/api/charts/system-overview', self._system_overview_chart)
        self.app.router.add_get('/api/charts/business-dashboard', self._business_dashboard_chart)
        self.app.router.add_get('/api/charts/error-analysis', self._error_analysis_chart)
        
        # Real-time WebSocket
        self.app.router.add_get('/ws', self._websocket_handler)
    
    def _setup_cors(self):
        """Setup CORS"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def _dashboard_page(self, request):
        """Serve the main dashboard page"""
        html_content = self._generate_dashboard_html()
        return web.Response(text=html_content, content_type='text/html')
    
    def _generate_dashboard_html(self) -> str:
        """Generate the main dashboard HTML"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ActiveLog Monitoring Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #1a1a1a;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .navbar {
            background-color: #2d2d2d !important;
        }
        .card {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            margin-bottom: 20px;
        }
        .card-header {
            background-color: #3d3d3d;
            border-bottom: 1px solid #4d4d4d;
        }
        .metric-card {
            text-align: center;
            padding: 20px;
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #aaa;
        }
        .status-healthy { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-critical { color: #dc3545; }
        .chart-container {
            height: 400px;
            margin: 20px 0;
        }
        .alert-item {
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }
        .alert-critical { 
            background-color: rgba(220, 53, 69, 0.1);
            border-left-color: #dc3545;
        }
        .alert-warning { 
            background-color: rgba(255, 193, 7, 0.1);
            border-left-color: #ffc107;
        }
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2rem;
            color: #aaa;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="#">
                <i class="fas fa-chart-line me-2"></i>
                ActiveLog Dashboard
            </a>
            <div class="navbar-nav ms-auto">
                <span class="navbar-text" id="last-updated">
                    Last updated: <span id="update-time">--</span>
                </span>
            </div>
        </div>
    </nav>

    <!-- Main Dashboard -->
    <div class="container-fluid mt-4">
        <!-- System Overview Row -->
        <div class="row">
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body metric-card">
                        <div class="metric-value status-healthy" id="services-up">--</div>
                        <div class="metric-label">Services Up</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body metric-card">
                        <div class="metric-value" id="active-users">--</div>
                        <div class="metric-label">Active Users (24h)</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body metric-card">
                        <div class="metric-value" id="revenue-24h">--</div>
                        <div class="metric-label">Revenue (24h)</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body metric-card">
                        <div class="metric-value" id="error-rate">--</div>
                        <div class="metric-label">Error Rate</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row">
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-area me-2"></i>Performance Trends</h5>
                    </div>
                    <div class="card-body">
                        <div id="performance-chart" class="chart-container"></div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-exclamation-triangle me-2"></i>Recent Alerts</h5>
                    </div>
                    <div class="card-body">
                        <div id="alerts-container">
                            <div class="loading">Loading alerts...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Business Metrics Row -->
        <div class="row">
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-pie me-2"></i>Business Metrics</h5>
                    </div>
                    <div class="card-body">
                        <div id="business-chart" class="chart-container"></div>
                    </div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-server me-2"></i>Infrastructure Health</h5>
                    </div>
                    <div class="card-body">
                        <div id="infrastructure-chart" class="chart-container"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Error Analysis Row -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-bug me-2"></i>Error Analysis</h5>
                    </div>
                    <div class="card-body">
                        <div id="error-analysis-chart" class="chart-container"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Dashboard JavaScript implementation
        class ActiveLogDashboard {
            constructor() {
                this.websocket = null;
                this.updateInterval = 30000; // 30 seconds
                this.init();
            }

            init() {
                this.setupWebSocket();
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

            async loadInitialData() {
                try {
                    await Promise.all([
                        this.updateSystemMetrics(),
                        this.updateBusinessMetrics(),
                        this.updatePerformanceChart(),
                        this.updateBusinessChart(),
                        this.updateInfrastructureChart(),
                        this.updateErrorAnalysisChart()
                    ]);
                    
                    this.updateTimestamp();
                } catch (error) {
                    console.error('Error loading initial data:', error);
                }
            }

            async updateSystemMetrics() {
                try {
                    const response = await fetch('/api/metrics/system');
                    const data = await response.json();
                    
                    // Update service health
                    const servicesUp = data.uptime?.data?.result?.length || 0;
                    document.getElementById('services-up').textContent = servicesUp;
                    
                    // Update error rate
                    const errorRate = data.error_rates?.data?.result?.[0]?.value?.[1] || 0;
                    const errorPercent = (parseFloat(errorRate) * 100).toFixed(2);
                    document.getElementById('error-rate').textContent = errorPercent + '%';
                    
                    // Update error rate status
                    const errorElement = document.getElementById('error-rate');
                    errorElement.className = 'metric-value ' + (errorPercent > 5 ? 'status-critical' : 
                                             errorPercent > 1 ? 'status-warning' : 'status-healthy');
                    
                } catch (error) {
                    console.error('Error updating system metrics:', error);
                }
            }

            async updateBusinessMetrics() {
                try {
                    const response = await fetch('/api/metrics/business');
                    const data = await response.json();
                    
                    // Update active users
                    document.getElementById('active-users').textContent = 
                        (data.active_users || 0).toLocaleString();
                    
                    // Update revenue
                    const revenue = (data.revenue_24h || 0) / 100; // Convert cents to dollars
                    document.getElementById('revenue-24h').textContent = 
                        '$' + revenue.toLocaleString();
                    
                } catch (error) {
                    console.error('Error updating business metrics:', error);
                }
            }

            async updatePerformanceChart() {
                try {
                    const response = await fetch('/api/charts/system-overview');
                    const chartData = await response.json();
                    
                    Plotly.newPlot('performance-chart', chartData.data, chartData.layout, 
                                   {responsive: true, displayModeBar: false});
                    
                } catch (error) {
                    console.error('Error updating performance chart:', error);
                }
            }

            async updateBusinessChart() {
                try {
                    const response = await fetch('/api/charts/business-dashboard');
                    const chartData = await response.json();
                    
                    Plotly.newPlot('business-chart', chartData.data, chartData.layout,
                                   {responsive: true, displayModeBar: false});
                    
                } catch (error) {
                    console.error('Error updating business chart:', error);
                }
            }

            async updateInfrastructureChart() {
                try {
                    const response = await fetch('/api/metrics/infrastructure');
                    const data = await response.json();
                    
                    // Create infrastructure health chart
                    const traces = [];
                    
                    if (data.cpu_usage?.data?.result) {
                        traces.push({
                            x: ['CPU'],
                            y: [parseFloat(data.cpu_usage.data.result[0]?.value?.[1] || 0)],
                            type: 'bar',
                            name: 'CPU Usage %',
                            marker: { color: '#ff6b6b' }
                        });
                    }
                    
                    if (data.memory_usage?.data?.result) {
                        traces.push({
                            x: ['Memory'],
                            y: [parseFloat(data.memory_usage.data.result[0]?.value?.[1] || 0)],
                            type: 'bar',
                            name: 'Memory Usage %',
                            marker: { color: '#4ecdc4' }
                        });
                    }
                    
                    const layout = {
                        title: 'Resource Usage',
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        font: { color: '#ffffff' },
                        xaxis: { color: '#ffffff' },
                        yaxis: { color: '#ffffff', range: [0, 100] }
                    };
                    
                    Plotly.newPlot('infrastructure-chart', traces, layout,
                                   {responsive: true, displayModeBar: false});
                    
                } catch (error) {
                    console.error('Error updating infrastructure chart:', error);
                }
            }

            async updateErrorAnalysisChart() {
                try {
                    const response = await fetch('/api/charts/error-analysis');
                    const chartData = await response.json();
                    
                    Plotly.newPlot('error-analysis-chart', chartData.data, chartData.layout,
                                   {responsive: true, displayModeBar: false});
                    
                } catch (error) {
                    console.error('Error updating error analysis chart:', error);
                }
            }

            startPeriodicUpdates() {
                setInterval(() => {
                    this.loadInitialData();
                }, this.updateInterval);
            }

            handleRealtimeUpdate(data) {
                // Handle real-time WebSocket updates
                if (data.type === 'metric_update') {
                    // Update specific metrics without full reload
                    console.log('Received metric update:', data);
                } else if (data.type === 'alert') {
                    // Handle new alerts
                    this.showAlert(data.alert);
                }
            }

            showAlert(alert) {
                const alertsContainer = document.getElementById('alerts-container');
                const alertElement = document.createElement('div');
                alertElement.className = `alert-item alert-${alert.severity}`;
                alertElement.innerHTML = `
                    <strong>${alert.service}</strong>: ${alert.message}
                    <br><small>${new Date(alert.timestamp).toLocaleString()}</small>
                `;
                
                // Add to top of alerts
                alertsContainer.insertBefore(alertElement, alertsContainer.firstChild);
                
                // Remove old alerts (keep only 5)
                const alerts = alertsContainer.children;
                if (alerts.length > 5) {
                    alertsContainer.removeChild(alerts[alerts.length - 1]);
                }
            }

            updateTimestamp() {
                document.getElementById('update-time').textContent = 
                    new Date().toLocaleTimeString();
            }
        }

        // Initialize dashboard when page loads
        document.addEventListener('DOMContentLoaded', () => {
            new ActiveLogDashboard();
        });
    </script>
</body>
</html>
        '''
    
    # API Endpoints
    async def _health_endpoint(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "data_sources": {
                name: source.connected 
                for name, source in self.data_sources.items()
            }
        })
    
    async def _system_metrics_endpoint(self, request):
        """System metrics endpoint"""
        try:
            metrics = await self.metrics.get_system_health()
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _business_metrics_endpoint(self, request):
        """Business metrics endpoint"""
        try:
            metrics = await self.metrics.get_business_metrics()
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Error getting business metrics: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _error_metrics_endpoint(self, request):
        """Error metrics endpoint"""
        try:
            metrics = await self.metrics.get_error_analysis()
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Error getting error metrics: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _performance_metrics_endpoint(self, request):
        """Performance metrics endpoint"""
        try:
            metrics = await self.metrics.get_performance_trends()
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _infrastructure_metrics_endpoint(self, request):
        """Infrastructure metrics endpoint"""
        try:
            metrics = await self.metrics.get_infrastructure_metrics()
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Error getting infrastructure metrics: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    # Chart Endpoints
    async def _system_overview_chart(self, request):
        """System overview chart data"""
        try:
            performance_data = await self.metrics.get_performance_trends()
            
            # Convert Prometheus data to Plotly format
            traces = []
            
            if performance_data.get('request_rate', {}).get('data', {}).get('result'):
                request_data = performance_data['request_rate']['data']['result'][0]
                times = [datetime.fromtimestamp(float(t)) for t, v in request_data['values']]
                values = [float(v) for t, v in request_data['values']]
                
                traces.append({
                    'x': times,
                    'y': values,
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': 'Request Rate',
                    'line': {'color': '#00d2ff'}
                })
            
            layout = {
                'title': 'Request Rate Over Time',
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'plot_bgcolor': 'rgba(0,0,0,0)',
                'font': {'color': '#ffffff'},
                'xaxis': {'color': '#ffffff'},
                'yaxis': {'color': '#ffffff'}
            }
            
            return web.json_response({
                'data': traces,
                'layout': layout
            })
            
        except Exception as e:
            logger.error(f"Error generating system overview chart: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _business_dashboard_chart(self, request):
        """Business dashboard chart data"""
        try:
            business_data = await self.metrics.get_business_metrics()
            
            # Create subscription distribution pie chart
            subscriptions = business_data.get('subscriptions', [])
            
            if subscriptions:
                labels = [sub['plan_type'] for sub in subscriptions]
                values = [sub['count'] for sub in subscriptions]
                
                trace = {
                    'labels': labels,
                    'values': values,
                    'type': 'pie',
                    'marker': {
                        'colors': ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']
                    }
                }
                
                layout = {
                    'title': 'Subscription Distribution',
                    'paper_bgcolor': 'rgba(0,0,0,0)',
                    'font': {'color': '#ffffff'}
                }
                
                return web.json_response({
                    'data': [trace],
                    'layout': layout
                })
            else:
                return web.json_response({
                    'data': [],
                    'layout': {'title': 'No subscription data available'}
                })
                
        except Exception as e:
            logger.error(f"Error generating business dashboard chart: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _error_analysis_chart(self, request):
        """Error analysis chart data"""
        try:
            error_data = await self.metrics.get_error_analysis()
            
            errors_by_service = error_data.get('errors_by_service', [])
            
            if errors_by_service:
                services = [item['key'] for item in errors_by_service]
                counts = [item['doc_count'] for item in errors_by_service]
                
                trace = {
                    'x': services,
                    'y': counts,
                    'type': 'bar',
                    'name': 'Errors by Service',
                    'marker': {'color': '#ff6b6b'}
                }
                
                layout = {
                    'title': 'Errors by Service (Last Hour)',
                    'paper_bgcolor': 'rgba(0,0,0,0)',
                    'plot_bgcolor': 'rgba(0,0,0,0)',
                    'font': {'color': '#ffffff'},
                    'xaxis': {'color': '#ffffff'},
                    'yaxis': {'color': '#ffffff'}
                }
                
                return web.json_response({
                    'data': [trace],
                    'layout': layout
                })
            else:
                return web.json_response({
                    'data': [],
                    'layout': {'title': 'No error data available'}
                })
                
        except Exception as e:
            logger.error(f"Error generating error analysis chart: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    # WebSocket Handler
    async def _websocket_handler(self, request):
        """Handle WebSocket connections for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.add(ws)
        logger.info("WebSocket connection established")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            "error": "Invalid JSON format"
                        }))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.websocket_connections.discard(ws)
            logger.info("WebSocket connection closed")
        
        return ws
    
    async def _handle_websocket_message(self, ws, data):
        """Handle incoming WebSocket messages"""
        message_type = data.get('type')
        
        if message_type == 'subscribe':
            await ws.send_str(json.dumps({
                "type": "subscription_ack",
                "message": "Subscribed to real-time updates"
            }))
        elif message_type == 'ping':
            await ws.send_str(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }))
    
    async def broadcast_update(self, update):
        """Broadcast update to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message = json.dumps(update)
        disconnected = []
        
        for ws in list(self.websocket_connections):
            try:
                await ws.send_str(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket update: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.websocket_connections.discard(ws)
    
    # Background Tasks
    async def _metrics_collection_task(self):
        """Background task for collecting metrics"""
        while self.running:
            try:
                # Collect latest metrics and broadcast to WebSocket clients
                system_metrics = await self.metrics.get_system_health()
                
                await self.broadcast_update({
                    "type": "metric_update",
                    "data": system_metrics
                })
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection task: {e}")
                await asyncio.sleep(10)
    
    async def start(self, host='0.0.0.0', port=8080):
        """Start the dashboard server"""
        # Connect to all data sources
        for name, source in self.data_sources.items():
            try:
                await source.connect()
                logger.info(f"Connected to {name}")
            except Exception as e:
                logger.error(f"Failed to connect to {name}: {e}")
        
        # Start background tasks
        self.running = True
        self._metrics_task = asyncio.create_task(self._metrics_collection_task())
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"ActiveLog Dashboard started on http://{host}:{port}")
        return runner
    
    async def stop(self):
        """Stop the dashboard server"""
        self.running = False
        
        # Stop background tasks
        if self._metrics_task:
            self._metrics_task.cancel()
        
        # Disconnect from data sources
        for source in self.data_sources.values():
            try:
                await source.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from {source.name}: {e}")
        
        logger.info("ActiveLog Dashboard stopped")

async def main():
    """Main entry point"""
    dashboard = DashboardServer()
    
    try:
        runner = await dashboard.start(port=8080)
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down dashboard...")
    finally:
        await dashboard.stop()

if __name__ == "__main__":
    asyncio.run(main())