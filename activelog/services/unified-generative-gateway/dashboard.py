#!/usr/bin/env python3
"""
Building Bots Network Dashboard - Comprehensive Monitoring and Control Interface

This dashboard provides:
- Real-time network status visualization
- Project orchestration monitoring
- Service health and performance tracking
- Resource utilization analytics
- Quality assurance metrics
- Interactive control interface
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import aiohttp
import websockets
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
from pathlib import Path
import plotly.graph_objs as go
import plotly.utils
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardAnalytics:
    """Analytics engine for dashboard data"""
    
    def __init__(self, gateway_url: str = "http://localhost:8600"):
        self.gateway_url = gateway_url
        self.metrics_cache = {}
        self.last_update = None
    
    async def get_network_overview(self) -> Dict[str, Any]:
        """Get network overview data"""
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get network status
                async with session.get(f"{self.gateway_url}/network-status") as response:
                    if response.status == 200:
                        network_data = await response.json()
                    else:
                        network_data = {"error": "Gateway unavailable"}
                
                # Get analytics
                async with session.get(f"{self.gateway_url}/analytics") as response:
                    if response.status == 200:
                        analytics_data = await response.json()
                    else:
                        analytics_data = {"error": "Analytics unavailable"}
                
                return {
                    "network_status": network_data,
                    "analytics": analytics_data,
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error getting network overview: {e}")
            return {
                "error": str(e),
                "network_status": {"building_bots_network": {"total_bots": 0}},
                "analytics": {"network_performance": {}},
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_service_health_matrix(self) -> Dict[str, Any]:
        """Get service health matrix for visualization"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.gateway_url}/network-status") as response:
                    if response.status == 200:
                        data = await response.json()
                        service_statuses = data.get("service_statuses", {})
                        
                        health_matrix = []
                        for service_name, status_info in service_statuses.items():
                            health_matrix.append({
                                "service": service_name,
                                "status": status_info.get("status", "unknown"),
                                "response_time": status_info.get("response_time", 0),
                                "building_specialty": status_info.get("building_specialty", "general"),
                                "timestamp": status_info.get("checked_at", "")
                            })
                        
                        return {
                            "health_matrix": health_matrix,
                            "summary": {
                                "total_services": len(service_statuses),
                                "healthy_services": sum(1 for s in service_statuses.values() if s.get("status") == "healthy"),
                                "response_time_avg": sum(s.get("response_time", 0) for s in service_statuses.values()) / len(service_statuses) if service_statuses else 0
                            }
                        }
        
        except Exception as e:
            logger.error(f"Error getting service health matrix: {e}")
            return {"health_matrix": [], "summary": {"total_services": 0, "healthy_services": 0}}
    
    async def get_project_analytics(self) -> Dict[str, Any]:
        """Get project analytics and trends"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.gateway_url}/analytics") as response:
                    if response.status == 200:
                        analytics = await response.json()
                        
                        # Process project history for trends
                        project_history = analytics.get("project_history_summary", {}).get("recent_projects", [])
                        
                        trends = self._calculate_project_trends(project_history)
                        
                        return {
                            "project_metrics": analytics.get("network_performance", {}),
                            "trends": trends,
                            "recent_projects": project_history[-10:],  # Last 10 projects
                            "service_utilization": analytics.get("service_utilization", {})
                        }
        
        except Exception as e:
            logger.error(f"Error getting project analytics: {e}")
            return {"project_metrics": {}, "trends": {}, "recent_projects": []}
    
    def _calculate_project_trends(self, project_history: List[Dict]) -> Dict[str, Any]:
        """Calculate trends from project history"""
        
        if not project_history:
            return {"quality_trend": [], "cost_trend": [], "success_rate": 0}
        
        # Extract metrics over time
        quality_scores = []
        costs = []
        success_count = 0
        
        for project in project_history:
            quality_metrics = project.get("quality_metrics", {})
            resource_metrics = project.get("resource_metrics", {})
            
            if quality_metrics.get("overall_quality_score"):
                quality_scores.append({
                    "timestamp": project.get("timestamp", ""),
                    "value": quality_metrics["overall_quality_score"]
                })
            
            if resource_metrics.get("total_cost"):
                costs.append({
                    "timestamp": project.get("timestamp", ""),
                    "value": resource_metrics["total_cost"]
                })
            
            if project.get("success", False):
                success_count += 1
        
        return {
            "quality_trend": quality_scores,
            "cost_trend": costs,
            "success_rate": success_count / len(project_history) if project_history else 0,
            "total_projects": len(project_history)
        }
    
    def create_network_health_chart(self, health_matrix: List[Dict]) -> str:
        """Create network health visualization"""
        
        if not health_matrix:
            return json.dumps({})
        
        # Prepare data for heatmap
        services = [item["service"] for item in health_matrix]
        specialties = [item["building_specialty"] for item in health_matrix]
        response_times = [item["response_time"] for item in health_matrix]
        statuses = [1 if item["status"] == "healthy" else 0 for item in health_matrix]
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=[statuses],
            x=services,
            y=["Service Health"],
            colorscale='RdYlGn',
            hoverongaps=False,
            hovertemplate='Service: %{x}<br>Status: %{z}<br>Specialty: ' + 
                         '<br>'.join(specialties) + '<extra></extra>'
        ))
        
        fig.update_layout(
            title="Building Bots Network Health Matrix",
            xaxis_title="Services",
            yaxis_title="Health Status",
            height=200
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def create_performance_chart(self, project_metrics: Dict) -> str:
        """Create performance metrics chart"""
        
        metrics = ['total_projects', 'successful_projects', 'average_satisfaction']
        values = [
            project_metrics.get('total_projects', 0),
            project_metrics.get('successful_projects', 0),
            project_metrics.get('average_satisfaction', 0)
        ]
        
        fig = go.Figure([go.Bar(x=metrics, y=values, marker_color='skyblue')])
        
        fig.update_layout(
            title="Network Performance Metrics",
            xaxis_title="Metrics",
            yaxis_title="Values",
            height=300
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


class DashboardWebSocketManager:
    """WebSocket manager for real-time dashboard updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.analytics = DashboardAnalytics()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Dashboard client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Dashboard client disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_update_to_all(self, data: Dict[str, Any]):
        """Send update to all connected dashboard clients"""
        
        if not self.active_connections:
            return
        
        message = json.dumps(data)
        
        # Send to all connections, remove broken ones
        broken_connections = []
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to dashboard client: {e}")
                broken_connections.append(connection)
        
        # Remove broken connections
        for connection in broken_connections:
            self.disconnect(connection)
    
    async def start_real_time_updates(self):
        """Start sending real-time updates to connected clients"""
        
        while True:
            try:
                if self.active_connections:
                    # Get latest data
                    network_overview = await self.analytics.get_network_overview()
                    health_matrix_data = await self.analytics.get_service_health_matrix()
                    project_analytics = await self.analytics.get_project_analytics()
                    
                    # Create visualizations
                    health_chart = self.analytics.create_network_health_chart(
                        health_matrix_data.get("health_matrix", [])
                    )
                    performance_chart = self.analytics.create_performance_chart(
                        project_analytics.get("project_metrics", {})
                    )
                    
                    update_data = {
                        "type": "dashboard_update",
                        "timestamp": datetime.now().isoformat(),
                        "network_overview": network_overview,
                        "health_matrix": health_matrix_data,
                        "project_analytics": project_analytics,
                        "charts": {
                            "health_chart": health_chart,
                            "performance_chart": performance_chart
                        }
                    }
                    
                    await self.send_update_to_all(update_data)
                
                # Update every 10 seconds
                await asyncio.sleep(10)
            
            except Exception as e:
                logger.error(f"Error in real-time updates: {e}")
                await asyncio.sleep(30)  # Wait longer on error


# Global WebSocket manager
ws_manager = DashboardWebSocketManager()

# FastAPI app for dashboard
dashboard_app = FastAPI(
    title="Building Bots Network Dashboard",
    description="Real-time monitoring and control interface for the Building Bots Network",
    version="1.0.0"
)

dashboard_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dashboard_app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Serve main dashboard interface"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Building Bots Network Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .dashboard-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                transition: transform 0.3s ease;
            }
            .dashboard-card:hover {
                transform: translateY(-5px);
            }
            .metric-card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
            }
            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                display: inline-block;
                margin-right: 8px;
            }
            .status-healthy { background-color: #10b981; }
            .status-unhealthy { background-color: #ef4444; }
            .status-unknown { background-color: #6b7280; }
            .blink { animation: blink 2s infinite; }
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0.5; }
            }
        </style>
    </head>
    <body class="bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 min-h-screen text-white">
        <!-- Header -->
        <header class="bg-black bg-opacity-30 backdrop-filter backdrop-blur-lg border-b border-white border-opacity-20 p-4">
            <div class="container mx-auto flex justify-between items-center">
                <h1 class="text-3xl font-bold">🏗️ Building Bots Network Dashboard</h1>
                <div class="flex items-center space-x-4">
                    <span class="status-indicator blink" id="connection-status"></span>
                    <span id="connection-text">Connecting...</span>
                    <span id="last-update" class="text-sm opacity-75"></span>
                </div>
            </div>
        </header>

        <!-- Main Dashboard -->
        <main class="container mx-auto p-6">
            <!-- Network Overview -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div class="dashboard-card p-6 text-center">
                    <h3 class="text-lg font-semibold mb-2">Total Bots</h3>
                    <div class="text-4xl font-bold" id="total-bots">-</div>
                    <div class="text-sm opacity-75 mt-2">Construction Specialists</div>
                </div>
                <div class="dashboard-card p-6 text-center">
                    <h3 class="text-lg font-semibold mb-2">Healthy Bots</h3>
                    <div class="text-4xl font-bold text-green-400" id="healthy-bots">-</div>
                    <div class="text-sm opacity-75 mt-2">Operational Status</div>
                </div>
                <div class="dashboard-card p-6 text-center">
                    <h3 class="text-lg font-semibold mb-2">Active Projects</h3>
                    <div class="text-4xl font-bold text-blue-400" id="active-projects">-</div>
                    <div class="text-sm opacity-75 mt-2">In Construction</div>
                </div>
                <div class="dashboard-card p-6 text-center">
                    <h3 class="text-lg font-semibold mb-2">Success Rate</h3>
                    <div class="text-4xl font-bold text-yellow-400" id="success-rate">-%</div>
                    <div class="text-sm opacity-75 mt-2">Project Completion</div>
                </div>
            </div>

            <!-- Service Health Matrix -->
            <div class="dashboard-card p-6 mb-8">
                <h2 class="text-2xl font-bold mb-4">🔧 Service Health Matrix</h2>
                <div id="health-matrix" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                    <!-- Service health cards will be populated here -->
                </div>
            </div>

            <!-- Charts Section -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="dashboard-card p-6">
                    <h2 class="text-2xl font-bold mb-4">📊 Network Performance</h2>
                    <div id="performance-chart" style="height: 300px;"></div>
                </div>
                <div class="dashboard-card p-6">
                    <h2 class="text-2xl font-bold mb-4">🏥 Health Overview</h2>
                    <div id="health-chart" style="height: 300px;"></div>
                </div>
            </div>

            <!-- Recent Projects -->
            <div class="dashboard-card p-6 mb-8">
                <h2 class="text-2xl font-bold mb-4">📋 Recent Construction Projects</h2>
                <div id="recent-projects" class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead>
                            <tr class="border-b border-white border-opacity-20">
                                <th class="text-left p-2">Project ID</th>
                                <th class="text-left p-2">Type</th>
                                <th class="text-left p-2">Quality Score</th>
                                <th class="text-left p-2">Status</th>
                                <th class="text-left p-2">Timestamp</th>
                            </tr>
                        </thead>
                        <tbody id="projects-table-body">
                            <!-- Project rows will be populated here -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- System Resources -->
            <div class="dashboard-card p-6">
                <h2 class="text-2xl font-bold mb-4">💻 System Resources</h2>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="metric-card p-4 text-center">
                        <div class="text-lg font-semibold">CPU</div>
                        <div class="text-2xl font-bold" id="cpu-usage">-%</div>
                    </div>
                    <div class="metric-card p-4 text-center">
                        <div class="text-lg font-semibold">Memory</div>
                        <div class="text-2xl font-bold" id="memory-usage">-%</div>
                    </div>
                    <div class="metric-card p-4 text-center">
                        <div class="text-lg font-semibold">Disk</div>
                        <div class="text-2xl font-bold" id="disk-usage">-%</div>
                    </div>
                    <div class="metric-card p-4 text-center">
                        <div class="text-lg font-semibold">Load</div>
                        <div class="text-2xl font-bold" id="load-average">-</div>
                    </div>
                </div>
            </div>
        </main>

        <script>
            // WebSocket connection
            const ws = new WebSocket('ws://localhost:8601/ws');
            const connectionStatus = document.getElementById('connection-status');
            const connectionText = document.getElementById('connection-text');
            const lastUpdate = document.getElementById('last-update');

            ws.onopen = function(event) {
                connectionStatus.className = 'status-indicator status-healthy blink';
                connectionText.textContent = 'Connected';
            };

            ws.onclose = function(event) {
                connectionStatus.className = 'status-indicator status-unhealthy';
                connectionText.textContent = 'Disconnected';
            };

            ws.onerror = function(error) {
                connectionStatus.className = 'status-indicator status-unknown';
                connectionText.textContent = 'Error';
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'dashboard_update') {
                    updateDashboard(data);
                    lastUpdate.textContent = 'Updated: ' + new Date(data.timestamp).toLocaleTimeString();
                }
            };

            function updateDashboard(data) {
                // Update network overview
                const networkData = data.network_overview;
                const bbnData = networkData.network_status?.building_bots_network || {};
                
                document.getElementById('total-bots').textContent = bbnData.total_bots || 0;
                document.getElementById('healthy-bots').textContent = bbnData.healthy_bots || 0;
                document.getElementById('active-projects').textContent = networkData.network_status?.active_projects || 0;
                
                const successRate = data.project_analytics?.project_metrics?.successful_projects || 0;
                const totalProjects = data.project_analytics?.project_metrics?.total_projects || 1;
                document.getElementById('success-rate').textContent = Math.round((successRate / totalProjects) * 100) + '%';

                // Update service health matrix
                updateHealthMatrix(data.health_matrix);

                // Update charts
                if (data.charts?.performance_chart) {
                    const chartData = JSON.parse(data.charts.performance_chart);
                    Plotly.newPlot('performance-chart', chartData.data, chartData.layout, {responsive: true});
                }

                // Update recent projects
                updateRecentProjects(data.project_analytics?.recent_projects || []);

                // Update system resources
                const systemResources = networkData.network_status?.system_resources || {};
                document.getElementById('cpu-usage').textContent = Math.round(systemResources.cpu_percent || 0) + '%';
                document.getElementById('memory-usage').textContent = Math.round(systemResources.memory_percent || 0) + '%';
                document.getElementById('disk-usage').textContent = Math.round(systemResources.disk_percent || 0) + '%';
                
                const loadAvg = systemResources.load_average || [0];
                document.getElementById('load-average').textContent = (loadAvg[0] || 0).toFixed(1);
            }

            function updateHealthMatrix(healthData) {
                const container = document.getElementById('health-matrix');
                container.innerHTML = '';

                (healthData.health_matrix || []).forEach(service => {
                    const card = document.createElement('div');
                    card.className = 'metric-card p-3';
                    
                    const statusClass = service.status === 'healthy' ? 'status-healthy' : 
                                       service.status === 'error' ? 'status-unhealthy' : 'status-unknown';
                    
                    card.innerHTML = `
                        <div class="flex items-center mb-2">
                            <span class="status-indicator ${statusClass}"></span>
                            <span class="font-semibold text-sm">${service.service}</span>
                        </div>
                        <div class="text-xs opacity-75">${service.building_specialty}</div>
                        <div class="text-xs mt-1">${Math.round(service.response_time * 1000)}ms</div>
                    `;
                    
                    container.appendChild(card);
                });
            }

            function updateRecentProjects(projects) {
                const tbody = document.getElementById('projects-table-body');
                tbody.innerHTML = '';

                projects.forEach(project => {
                    const row = document.createElement('tr');
                    row.className = 'border-b border-white border-opacity-10';
                    
                    const qualityScore = project.quality_metrics?.overall_quality_score || 0;
                    const status = project.success ? 'Completed' : 'Failed';
                    const statusColor = project.success ? 'text-green-400' : 'text-red-400';
                    
                    row.innerHTML = `
                        <td class="p-2 font-mono text-xs">${project.project_id?.slice(0, 8)}...</td>
                        <td class="p-2 capitalize">${project.building_bots_network?.specialties_involved?.[0] || 'General'}</td>
                        <td class="p-2">${qualityScore.toFixed(1)}/10</td>
                        <td class="p-2 ${statusColor}">${status}</td>
                        <td class="p-2 text-xs">${new Date(project.timestamp).toLocaleString()}</td>
                    `;
                    
                    tbody.appendChild(row);
                });
            }

            // Initialize dashboard
            console.log('🏗️ Building Bots Network Dashboard initialized');
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@dashboard_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        ws_manager.disconnect(websocket)

@dashboard_app.get("/api/overview")
async def get_dashboard_overview():
    """API endpoint for dashboard overview data"""
    
    analytics = DashboardAnalytics()
    overview = await analytics.get_network_overview()
    return JSONResponse(content=overview)

@dashboard_app.get("/api/health-matrix")
async def get_health_matrix():
    """API endpoint for service health matrix"""
    
    analytics = DashboardAnalytics()
    health_matrix = await analytics.get_service_health_matrix()
    return JSONResponse(content=health_matrix)

@dashboard_app.get("/api/project-analytics")
async def get_project_analytics_api():
    """API endpoint for project analytics"""
    
    analytics = DashboardAnalytics()
    project_analytics = await analytics.get_project_analytics()
    return JSONResponse(content=project_analytics)

@dashboard_app.get("/health")
async def dashboard_health():
    """Health check for dashboard service"""
    return {
        "status": "healthy",
        "service": "Building Bots Network Dashboard",
        "connections": len(ws_manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

async def start_dashboard():
    """Start the dashboard service"""
    
    # Start real-time updates in background
    asyncio.create_task(ws_manager.start_real_time_updates())
    
    logger.info("🚀 Starting Building Bots Network Dashboard...")
    
    config = uvicorn.Config(
        app=dashboard_app,
        host="0.0.0.0",
        port=8601,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(start_dashboard())