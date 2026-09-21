#!/usr/bin/env python3
"""
ActiveLog User-Friendly Web Dashboard
Simple web interface for managing all ActiveLog features with one-click actions
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio
import json
import subprocess
import sys
import psutil
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ActiveLog Dashboard", description="User-friendly ActiveLog control panel")

# Create templates directory if it doesn't exist
templates_dir = Path("dashboard_templates")
templates_dir.mkdir(exist_ok=True)
static_dir = Path("dashboard_static")
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory="dashboard_templates")

class DashboardManager:
    def __init__(self):
        self.system_stats = {}
        self.service_status = {}
        self.optimization_status = {}
        self.user_config = self.load_user_config()
        
    def load_user_config(self) -> Dict:
        """Load user configuration"""
        try:
            with open("activelog_config.json") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"setup_completed": False}
    
    def get_system_overview(self) -> Dict:
        """Get simple system overview"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        # Determine status colors
        cpu_status = "good" if cpu_percent < 50 else "warning" if cpu_percent < 80 else "critical"
        memory_status = "good" if memory.percent < 60 else "warning" if memory.percent < 85 else "critical"
        disk_status = "good" if disk.percent < 70 else "warning" if disk.percent < 90 else "critical"
        
        return {
            "cpu": {
                "usage": round(cpu_percent, 1),
                "status": cpu_status,
                "cores": psutil.cpu_count()
            },
            "memory": {
                "usage": round(memory.percent, 1),
                "used_gb": round(memory.used / 1024**3, 1),
                "total_gb": round(memory.total / 1024**3, 1),
                "status": memory_status
            },
            "disk": {
                "usage": round(disk.percent, 1),
                "free_gb": round(disk.free / 1024**3, 1),
                "total_gb": round(disk.total / 1024**3, 1),
                "status": disk_status
            },
            "overall_health": self.calculate_overall_health(cpu_status, memory_status, disk_status)
        }
    
    def calculate_overall_health(self, cpu_status, memory_status, disk_status) -> str:
        """Calculate overall system health"""
        statuses = [cpu_status, memory_status, disk_status]
        if "critical" in statuses:
            return "critical"
        elif "warning" in statuses:
            return "warning"
        else:
            return "good"
    
    def get_service_status(self) -> Dict:
        """Get status of ActiveLog services"""
        services = {
            "auth": {"port": 8002, "name": "Authentication", "essential": True},
            "api-gateway": {"port": 8088, "name": "API Gateway", "essential": True},
            "file-sync": {"port": 8000, "name": "File Sync", "essential": False},
            "ai-orchestrator": {"port": 8001, "name": "AI Orchestrator", "essential": False},
            "metadata": {"port": 8003, "name": "Metadata", "essential": False}
        }
        
        service_status = {}
        for service_id, info in services.items():
            pid_file = Path(f"pids/{service_id}.pid")
            is_running = False
            pid = None
            
            if pid_file.exists():
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                    is_running = psutil.pid_exists(pid)
                except (ValueError, FileNotFoundError):
                    pass
            
            # Try to check if port is responding
            port_responding = False
            if is_running:
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', info['port']))
                    port_responding = result == 0
                    sock.close()
                except:
                    pass
            
            service_status[service_id] = {
                "name": info["name"],
                "running": is_running,
                "responding": port_responding,
                "essential": info["essential"],
                "port": info["port"],
                "pid": pid,
                "status": "running" if is_running and port_responding else 
                         "starting" if is_running else "stopped"
            }
        
        return service_status
    
    def get_optimization_status(self) -> Dict:
        """Get optimization status"""
        optimizations = {
            "device_optimization": {
                "name": "Device Optimization",
                "status": "enabled" if Path("device_optimized_config.json").exists() else "disabled",
                "description": "Optimized for your device type"
            },
            "cloud_offloading": {
                "name": "Cloud Computing",
                "status": "enabled" if Path("cloud_setup.json").exists() else "disabled", 
                "description": "Offload intensive tasks to cloud"
            },
            "performance_monitoring": {
                "name": "Performance Monitoring",
                "status": "enabled" if Path("performance_metrics.db").exists() else "disabled",
                "description": "Real-time performance tracking"
            },
            "auto_scaling": {
                "name": "Auto Scaling",
                "status": "enabled" if self.user_config.get("recommendations", {}).get("optimizations") else "disabled",
                "description": "Automatic resource adjustment"
            }
        }
        
        return optimizations

dashboard_manager = DashboardManager()

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page"""
    system_overview = dashboard_manager.get_system_overview()
    service_status = dashboard_manager.get_service_status()
    optimization_status = dashboard_manager.get_optimization_status()
    
    context = {
        "request": request,
        "system": system_overview,
        "services": service_status,
        "optimizations": optimization_status,
        "user_config": dashboard_manager.user_config,
        "setup_completed": dashboard_manager.user_config.get("setup_completed", False)
    }
    
    return templates.TemplateResponse("dashboard.html", context)

@app.get("/api/system/overview")
async def get_system_overview():
    """API endpoint for system overview"""
    return dashboard_manager.get_system_overview()

@app.get("/api/services/status")
async def get_services_status():
    """API endpoint for service status"""
    return dashboard_manager.get_service_status()

@app.post("/api/services/{service_id}/start")
async def start_service(service_id: str):
    """Start a specific service"""
    try:
        result = subprocess.run([
            sys.executable, "smart_service_manager.py", "start", "--service", service_id
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return {"success": True, "message": f"Service {service_id} started successfully"}
        else:
            return {"success": False, "message": f"Failed to start {service_id}: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Service start timed out"}
    except Exception as e:
        return {"success": False, "message": f"Error starting service: {e}"}

@app.post("/api/services/{service_id}/stop")
async def stop_service(service_id: str):
    """Stop a specific service"""
    try:
        result = subprocess.run([
            sys.executable, "smart_service_manager.py", "stop", "--service", service_id
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return {"success": True, "message": f"Service {service_id} stopped successfully"}
        else:
            return {"success": False, "message": f"Failed to stop {service_id}: {result.stderr}"}
    except Exception as e:
        return {"success": False, "message": f"Error stopping service: {e}"}

@app.post("/api/system/optimize")
async def optimize_system():
    """Run system optimization"""
    try:
        # Run device optimization
        result = subprocess.run([
            sys.executable, "device_optimization_manager.py"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return {"success": True, "message": "System optimization completed successfully"}
        else:
            return {"success": False, "message": f"Optimization failed: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Optimization timed out"}
    except Exception as e:
        return {"success": False, "message": f"Optimization error: {e}"}

@app.post("/api/setup/run")
async def run_setup():
    """Run the easy setup wizard"""
    try:
        # Run setup in background since it's interactive
        result = subprocess.Popen([
            sys.executable, "easy_setup.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return {"success": True, "message": "Setup wizard started. Check terminal for interactive setup."}
    except Exception as e:
        return {"success": False, "message": f"Failed to start setup: {e}"}

@app.post("/api/cloud/enable")
async def enable_cloud():
    """Enable cloud computing"""
    try:
        result = subprocess.run([
            sys.executable, "cloud_compute_offloader.py"
        ], capture_output=True, text=True, timeout=30)
        
        return {"success": True, "message": "Cloud computing enabled"}
    except Exception as e:
        return {"success": False, "message": f"Failed to enable cloud: {e}"}

@app.get("/api/logs/{service_id}")
async def get_service_logs(service_id: str):
    """Get recent logs for a service"""
    try:
        log_file = Path(f"logs/{service_id}.log")
        if log_file.exists():
            with open(log_file) as f:
                # Get last 50 lines
                lines = f.readlines()[-50:]
                return {"logs": "".join(lines)}
        else:
            return {"logs": "No logs available"}
    except Exception as e:
        return {"logs": f"Error reading logs: {e}"}

# Create HTML template
def create_dashboard_template():
    """Create the main dashboard HTML template"""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ActiveLog Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .quick-actions {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
        }
        
        .btn-secondary {
            background: linear-gradient(45deg, #2196F3, #1976D2);
            color: white;
        }
        
        .btn-warning {
            background: linear-gradient(45deg, #FF9800, #F57C00);
            color: white;
        }
        
        .btn-danger {
            background: linear-gradient(45deg, #f44336, #d32f2f);
            color: white;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            border: 1px solid #e0e0e0;
        }
        
        .card h3 {
            margin-bottom: 20px;
            color: #333;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.3em;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }
        
        .status-good { background: #4CAF50; }
        .status-warning { background: #FF9800; }
        .status-critical { background: #f44336; }
        .status-stopped { background: #9E9E9E; }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-value {
            font-weight: 600;
            font-size: 1.1em;
        }
        
        .service-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .service-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #ddd;
        }
        
        .service-item.running {
            border-left-color: #4CAF50;
            background: #e8f5e8;
        }
        
        .service-item.stopped {
            border-left-color: #f44336;
            background: #fce8e8;
        }
        
        .service-info {
            flex: 1;
        }
        
        .service-name {
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .service-status {
            font-size: 0.9em;
            color: #666;
        }
        
        .service-actions {
            display: flex;
            gap: 8px;
        }
        
        .btn-sm {
            padding: 6px 12px;
            font-size: 0.85em;
        }
        
        .optimization-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .optimization-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .optimization-item.enabled {
            background: #e8f5e8;
            border: 1px solid #4CAF50;
        }
        
        .setup-prompt {
            text-align: center;
            padding: 40px;
            background: linear-gradient(135deg, #FFF3E0, #FFE0B2);
            border-radius: 12px;
            margin-bottom: 20px;
        }
        
        .setup-prompt h2 {
            color: #E65100;
            margin-bottom: 15px;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            z-index: 1000;
            transform: translateX(400px);
            transition: transform 0.3s ease;
        }
        
        .notification.show {
            transform: translateX(0);
        }
        
        .notification.success {
            background: #4CAF50;
        }
        
        .notification.error {
            background: #f44336;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 20px;
                margin: 10px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .quick-actions {
                flex-direction: column;
            }
            
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ActiveLog Dashboard</h1>
            <p>Simple control panel for all ActiveLog features</p>
        </div>

        {% if not setup_completed %}
        <div class="setup-prompt">
            <h2>🎯 Welcome to ActiveLog!</h2>
            <p>Let's get you set up with a quick configuration wizard.</p>
            <button class="btn btn-primary" onclick="runSetup()">
                ⚙️ Run Easy Setup
            </button>
        </div>
        {% endif %}

        <div class="quick-actions">
            <button class="btn btn-primary" onclick="optimizeSystem()">
                ⚡ Optimize System
            </button>
            <button class="btn btn-secondary" onclick="enableCloud()">
                ☁️ Enable Cloud
            </button>
            <button class="btn btn-warning" onclick="refreshStatus()">
                🔄 Refresh Status
            </button>
            <button class="btn btn-secondary" onclick="openMonitor()">
                📊 Performance Monitor
            </button>
        </div>

        <div class="dashboard-grid">
            <!-- System Overview Card -->
            <div class="card">
                <h3>🖥️ System Overview</h3>
                <div class="metric">
                    <span>CPU Usage</span>
                    <span class="metric-value status-{{ system.cpu.status }}">
                        <span class="status-indicator status-{{ system.cpu.status }}"></span>
                        {{ system.cpu.usage }}%
                    </span>
                </div>
                <div class="metric">
                    <span>Memory Usage</span>
                    <span class="metric-value">
                        <span class="status-indicator status-{{ system.memory.status }}"></span>
                        {{ system.memory.used_gb }}GB / {{ system.memory.total_gb }}GB
                    </span>
                </div>
                <div class="metric">
                    <span>Disk Usage</span>
                    <span class="metric-value">
                        <span class="status-indicator status-{{ system.disk.status }}"></span>
                        {{ system.disk.usage }}% ({{ system.disk.free_gb }}GB free)
                    </span>
                </div>
                <div class="metric">
                    <span>Overall Health</span>
                    <span class="metric-value">
                        <span class="status-indicator status-{{ system.overall_health }}"></span>
                        {{ system.overall_health.title() }}
                    </span>
                </div>
            </div>

            <!-- Services Card -->
            <div class="card">
                <h3>🔧 Services Status</h3>
                <div class="service-list">
                    {% for service_id, service in services.items() %}
                    <div class="service-item {{ 'running' if service.running else 'stopped' }}">
                        <div class="service-info">
                            <div class="service-name">{{ service.name }}</div>
                            <div class="service-status">
                                <span class="status-indicator status-{{ 'good' if service.running else 'stopped' }}"></span>
                                {{ service.status.title() }}
                                {% if service.port %} (Port {{ service.port }}) {% endif %}
                            </div>
                        </div>
                        <div class="service-actions">
                            {% if service.running %}
                            <button class="btn btn-danger btn-sm" onclick="stopService('{{ service_id }}')">
                                Stop
                            </button>
                            {% else %}
                            <button class="btn btn-primary btn-sm" onclick="startService('{{ service_id }}')">
                                Start
                            </button>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- Optimizations Card -->
            <div class="card">
                <h3>⚡ Optimizations</h3>
                <div class="optimization-list">
                    {% for opt_id, opt in optimizations.items() %}
                    <div class="optimization-item {{ 'enabled' if opt.status == 'enabled' else '' }}">
                        <div>
                            <div style="font-weight: 600;">{{ opt.name }}</div>
                            <div style="font-size: 0.9em; color: #666;">{{ opt.description }}</div>
                        </div>
                        <div>
                            <span class="status-indicator status-{{ 'good' if opt.status == 'enabled' else 'stopped' }}"></span>
                            {{ opt.status.title() }}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            {% if user_config.device_profile %}
            <!-- Device Info Card -->
            <div class="card">
                <h3>📱 Device Profile</h3>
                <div class="metric">
                    <span>Device Type</span>
                    <span class="metric-value">{{ user_config.device_profile.type }}</span>
                </div>
                <div class="metric">
                    <span>Performance Tier</span>
                    <span class="metric-value">{{ user_config.device_profile.tier.title() }}</span>
                </div>
                <div class="metric">
                    <span>CPU Cores</span>
                    <span class="metric-value">{{ user_config.device_profile.cpu_cores }}</span>
                </div>
                <div class="metric">
                    <span>Memory</span>
                    <span class="metric-value">{{ "%.1f"|format(user_config.device_profile.memory_gb) }} GB</span>
                </div>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        // Notification system
        function showNotification(message, type = 'success') {
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => notification.classList.add('show'), 100);
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => document.body.removeChild(notification), 300);
            }, 3000);
        }

        // API helper function
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = {
                    method,
                    headers: {'Content-Type': 'application/json'}
                };
                if (data) options.body = JSON.stringify(data);
                
                const response = await fetch(endpoint, options);
                return await response.json();
            } catch (error) {
                console.error('API call failed:', error);
                return {success: false, message: error.message};
            }
        }

        // Action functions
        async function startService(serviceId) {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.innerHTML = '<span class="loading"></span> Starting...';
            btn.disabled = true;
            
            const result = await apiCall(`/api/services/${serviceId}/start`, 'POST');
            
            if (result.success) {
                showNotification(`Service ${serviceId} started successfully`);
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }

        async function stopService(serviceId) {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.innerHTML = '<span class="loading"></span> Stopping...';
            btn.disabled = true;
            
            const result = await apiCall(`/api/services/${serviceId}/stop`, 'POST');
            
            if (result.success) {
                showNotification(`Service ${serviceId} stopped successfully`);
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }

        async function optimizeSystem() {
            const btn = event.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="loading"></span> Optimizing...';
            btn.disabled = true;
            
            const result = await apiCall('/api/system/optimize', 'POST');
            
            if (result.success) {
                showNotification('System optimization completed!');
                setTimeout(() => location.reload(), 2000);
            } else {
                showNotification(result.message, 'error');
            }
            
            btn.innerHTML = originalText;
            btn.disabled = false;
        }

        async function enableCloud() {
            const btn = event.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="loading"></span> Enabling...';
            btn.disabled = true;
            
            const result = await apiCall('/api/cloud/enable', 'POST');
            
            if (result.success) {
                showNotification('Cloud computing enabled!');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
            }
            
            btn.innerHTML = originalText;
            btn.disabled = false;
        }

        async function runSetup() {
            const result = await apiCall('/api/setup/run', 'POST');
            if (result.success) {
                showNotification('Setup wizard started! Check your terminal.');
            } else {
                showNotification(result.message, 'error');
            }
        }

        function refreshStatus() {
            showNotification('Refreshing status...');
            location.reload();
        }

        function openMonitor() {
            window.open('/monitor', '_blank');
        }

        // Auto-refresh every 30 seconds
        setInterval(refreshStatus, 30000);
    </script>
</body>
</html>"""
    
    template_file = templates_dir / "dashboard.html"
    with open(template_file, 'w') as f:
        f.write(html_content)

# Create the template when module loads
create_dashboard_template()

if __name__ == "__main__":
    import uvicorn
    
    print("🌐 Starting ActiveLog Web Dashboard...")
    print("Dashboard will be available at: http://localhost:8080")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)