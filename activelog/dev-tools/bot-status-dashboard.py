#!/usr/bin/env python3
"""
SuperInstance Bot Status Dashboard
=================================

Real-time dashboard for monitoring bot collaboration, task progress,
and system performance to ensure 200% velocity improvement.

🤖 Features:
- Real-time bot status monitoring
- Task progress visualization
- Conflict detection and prevention alerts
- Performance metrics tracking
- Collaboration efficiency analysis
"""

import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

logger = logging.getLogger(__name__)

class BotStatusDashboard:
    """Real-time bot collaboration dashboard"""
    
    def __init__(self, coordination_file: str = "/home/activeloguser/activelog/bot-coordination.json",
                 micro_updates_file: str = "/home/activeloguser/activelog/micro_updates.log"):
        self.coordination_file = coordination_file
        self.micro_updates_file = micro_updates_file
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Dashboard state
        self.dashboard_data = {
            "bots": [],
            "tasks": [],
            "metrics": {},
            "alerts": [],
            "performance": {
                "velocity_improvement": 0,
                "conflict_prevention_rate": 0,
                "task_completion_rate": 0,
                "collaboration_efficiency": 0
            },
            "recent_activities": []
        }
        
        # Start monitoring thread
        self._start_monitoring()

    def _start_monitoring(self):
        """Start background monitoring of coordination system"""
        def monitor_loop():
            while True:
                try:
                    self._update_dashboard_data()
                    self._broadcast_updates()
                except Exception as e:
                    logger.error(f"Dashboard monitoring error: {e}")
                time.sleep(5)  # Update every 5 seconds
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logger.info("Bot status monitoring started")

    def _update_dashboard_data(self):
        """Update dashboard data from coordination system"""
        try:
            # Load coordination data
            if os.path.exists(self.coordination_file):
                with open(self.coordination_file, 'r') as f:
                    coord_data = json.load(f)
                
                self.dashboard_data["bots"] = coord_data.get("bots", [])
                self.dashboard_data["tasks"] = coord_data.get("tasks", [])
                self.dashboard_data["metrics"] = coord_data.get("metrics", {})
            
            # Load recent activities from micro_updates.log
            self._load_recent_activities()
            
            # Calculate performance metrics
            self._calculate_performance_metrics()
            
            # Detect alerts
            self._detect_alerts()
            
        except Exception as e:
            logger.error(f"Failed to update dashboard data: {e}")

    def _load_recent_activities(self):
        """Load recent activities from micro_updates.log"""
        try:
            if os.path.exists(self.micro_updates_file):
                with open(self.micro_updates_file, 'r') as f:
                    lines = f.readlines()
                
                # Get last 20 lines
                recent_lines = lines[-20:] if len(lines) > 20 else lines
                activities = []
                
                for line in recent_lines:
                    line = line.strip()
                    if line and " - " in line:
                        try:
                            parts = line.split(" - ", 2)
                            if len(parts) >= 3:
                                timestamp = parts[0]
                                bot_id = parts[1]
                                activity = parts[2]
                                
                                activities.append({
                                    "timestamp": timestamp,
                                    "bot_id": bot_id,
                                    "activity": activity,
                                    "type": self._categorize_activity(activity)
                                })
                        except Exception:
                            continue
                
                self.dashboard_data["recent_activities"] = list(reversed(activities))
        
        except Exception as e:
            logger.error(f"Failed to load recent activities: {e}")

    def _categorize_activity(self, activity: str) -> str:
        """Categorize activity type for color coding"""
        activity_lower = activity.lower()
        
        if "conflict" in activity_lower or "blocked" in activity_lower:
            return "warning"
        elif "complete" in activity_lower or "success" in activity_lower:
            return "success"
        elif "error" in activity_lower or "failed" in activity_lower:
            return "error"
        elif "start" in activity_lower or "begin" in activity_lower:
            return "info"
        else:
            return "default"

    def _calculate_performance_metrics(self):
        """Calculate key performance metrics"""
        try:
            bots = self.dashboard_data["bots"]
            tasks = self.dashboard_data["tasks"]
            
            if not bots or not tasks:
                return
            
            # Bot utilization
            active_bots = len([bot for bot in bots if bot.get("status") == "working"])
            total_bots = len(bots)
            collaboration_efficiency = (active_bots / total_bots * 100) if total_bots > 0 else 0
            
            # Task completion rate
            completed_tasks = len([task for task in tasks if task.get("status") == "completed"])
            total_tasks = len(tasks)
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Conflict prevention (estimate from metrics)
            metrics = self.dashboard_data["metrics"]
            conflicts_prevented = metrics.get("resource_lock_violations_prevented", 0)
            conflict_prevention_rate = min(100, conflicts_prevented * 10)  # Rough estimate
            
            # Velocity improvement (based on parallel execution)
            baseline_velocity = 1.0  # Single bot baseline
            current_velocity = collaboration_efficiency / 100 * total_bots
            velocity_improvement = ((current_velocity / baseline_velocity) - 1) * 100
            
            self.dashboard_data["performance"] = {
                "velocity_improvement": round(velocity_improvement, 1),
                "conflict_prevention_rate": round(conflict_prevention_rate, 1),
                "task_completion_rate": round(completion_rate, 1),
                "collaboration_efficiency": round(collaboration_efficiency, 1)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")

    def _detect_alerts(self):
        """Detect system alerts and potential issues"""
        alerts = []
        
        try:
            bots = self.dashboard_data["bots"]
            tasks = self.dashboard_data["tasks"]
            
            # Check for blocked bots
            blocked_bots = [bot for bot in bots if bot.get("status") == "blocked"]
            for bot in blocked_bots:
                alerts.append({
                    "type": "warning",
                    "title": f"Bot {bot.get('bot_id', 'Unknown')} is blocked",
                    "description": f"Bot has been blocked - check for resource conflicts",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check for long-running tasks
            now = datetime.now()
            for task in tasks:
                if task.get("status") == "in_progress" and task.get("started_at"):
                    start_time = datetime.fromisoformat(task["started_at"])
                    duration = (now - start_time).total_seconds() / 60
                    estimated = task.get("estimated_duration", 60)
                    
                    if duration > estimated * 1.5:  # 50% over estimated
                        alerts.append({
                            "type": "warning", 
                            "title": f"Task taking longer than expected",
                            "description": f"Task '{task.get('title', 'Unknown')}' has been running for {duration:.1f} minutes (estimated: {estimated})",
                            "timestamp": datetime.now().isoformat()
                        })
            
            # Check for offline bots
            offline_threshold = datetime.now() - timedelta(minutes=10)
            for bot in bots:
                if bot.get("last_activity"):
                    last_activity = datetime.fromisoformat(bot["last_activity"])
                    if last_activity < offline_threshold:
                        alerts.append({
                            "type": "error",
                            "title": f"Bot {bot.get('bot_id', 'Unknown')} appears offline",
                            "description": f"No activity for {(datetime.now() - last_activity).total_seconds() / 60:.1f} minutes",
                            "timestamp": datetime.now().isoformat()
                        })
            
            # Check for low collaboration efficiency
            efficiency = self.dashboard_data["performance"]["collaboration_efficiency"]
            if efficiency < 50 and len(bots) > 1:
                alerts.append({
                    "type": "info",
                    "title": "Low collaboration efficiency detected",
                    "description": f"Only {efficiency:.1f}% of bots are actively working - consider task rebalancing",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Limit alerts to last 10
            self.dashboard_data["alerts"] = alerts[-10:]
            
        except Exception as e:
            logger.error(f"Failed to detect alerts: {e}")

    async def _broadcast_updates(self):
        """Broadcast updates to all connected WebSocket clients"""
        if self.active_connections:
            message = json.dumps(self.dashboard_data)
            disconnected = []
            
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for conn in disconnected:
                self.active_connections.remove(conn)

    async def connect_websocket(self, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Active connections: {len(self.active_connections)}")

    async def disconnect_websocket(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")

# Create dashboard instance
dashboard = BotStatusDashboard()

# FastAPI app
app = FastAPI(title="SuperInstance Bot Dashboard", description="Real-time bot collaboration monitoring")

@app.get("/")
async def get_dashboard():
    """Serve dashboard HTML"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SuperInstance Bot Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body class="bg-gray-900 text-white">
        <div id="app" class="container mx-auto p-4">
            <header class="mb-8">
                <h1 class="text-4xl font-bold text-blue-400 mb-2">🤖 SuperInstance Bot Dashboard</h1>
                <p class="text-gray-400">Real-time collaboration monitoring for 200% velocity improvement</p>
            </header>

            <!-- Performance Metrics -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div class="bg-gray-800 p-4 rounded-lg">
                    <h3 class="text-sm text-gray-400 mb-1">Velocity Improvement</h3>
                    <p class="text-2xl font-bold text-green-400" id="velocity-metric">0%</p>
                </div>
                <div class="bg-gray-800 p-4 rounded-lg">
                    <h3 class="text-sm text-gray-400 mb-1">Conflict Prevention</h3>
                    <p class="text-2xl font-bold text-blue-400" id="conflict-metric">0%</p>
                </div>
                <div class="bg-gray-800 p-4 rounded-lg">
                    <h3 class="text-sm text-gray-400 mb-1">Task Completion</h3>
                    <p class="text-2xl font-bold text-purple-400" id="completion-metric">0%</p>
                </div>
                <div class="bg-gray-800 p-4 rounded-lg">
                    <h3 class="text-sm text-gray-400 mb-1">Collaboration Efficiency</h3>
                    <p class="text-2xl font-bold text-yellow-400" id="efficiency-metric">0%</p>
                </div>
            </div>

            <!-- Bots and Tasks Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <!-- Bot Status -->
                <div class="bg-gray-800 rounded-lg p-6">
                    <h2 class="text-xl font-bold mb-4">🤖 Bot Status</h2>
                    <div id="bot-list" class="space-y-3">
                        <!-- Bots will be populated here -->
                    </div>
                </div>

                <!-- Task Progress -->
                <div class="bg-gray-800 rounded-lg p-6">
                    <h2 class="text-xl font-bold mb-4">📋 Active Tasks</h2>
                    <div id="task-list" class="space-y-3">
                        <!-- Tasks will be populated here -->
                    </div>
                </div>
            </div>

            <!-- Alerts and Activities -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Alerts -->
                <div class="bg-gray-800 rounded-lg p-6">
                    <h2 class="text-xl font-bold mb-4">⚠️ System Alerts</h2>
                    <div id="alerts-list" class="space-y-3">
                        <!-- Alerts will be populated here -->
                    </div>
                </div>

                <!-- Recent Activity -->
                <div class="bg-gray-800 rounded-lg p-6">
                    <h2 class="text-xl font-bold mb-4">📊 Recent Activity</h2>
                    <div id="activity-list" class="space-y-2 max-h-96 overflow-y-auto">
                        <!-- Activities will be populated here -->
                    </div>
                </div>
            </div>
        </div>

        <script>
            let socket = new WebSocket(`ws://${window.location.host}/ws`);
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            socket.onclose = function(event) {
                console.log('WebSocket closed, attempting to reconnect...');
                setTimeout(() => {
                    socket = new WebSocket(`ws://${window.location.host}/ws`);
                }, 3000);
            };

            function updateDashboard(data) {
                // Update performance metrics
                document.getElementById('velocity-metric').textContent = data.performance.velocity_improvement + '%';
                document.getElementById('conflict-metric').textContent = data.performance.conflict_prevention_rate + '%';
                document.getElementById('completion-metric').textContent = data.performance.task_completion_rate + '%';
                document.getElementById('efficiency-metric').textContent = data.performance.collaboration_efficiency + '%';
                
                // Update bot list
                updateBotList(data.bots);
                
                // Update task list
                updateTaskList(data.tasks);
                
                // Update alerts
                updateAlerts(data.alerts);
                
                // Update activities
                updateActivities(data.recent_activities);
            }

            function updateBotList(bots) {
                const container = document.getElementById('bot-list');
                container.innerHTML = '';
                
                bots.forEach(bot => {
                    const statusColor = {
                        'working': 'text-green-400',
                        'idle': 'text-blue-400', 
                        'blocked': 'text-red-400',
                        'offline': 'text-gray-400'
                    }[bot.status] || 'text-gray-400';
                    
                    const botElement = document.createElement('div');
                    botElement.className = 'border border-gray-700 rounded-lg p-3';
                    botElement.innerHTML = `
                        <div class="flex justify-between items-center">
                            <div>
                                <h4 class="font-semibold">${bot.bot_id}</h4>
                                <p class="text-sm text-gray-400">${bot.bot_type}</p>
                            </div>
                            <div class="text-right">
                                <p class="text-sm ${statusColor}">${bot.status}</p>
                                <p class="text-xs text-gray-500">Load: ${bot.current_workload}/${bot.workload_capacity}</p>
                            </div>
                        </div>
                        ${bot.current_task ? `<p class="text-xs text-blue-300 mt-2">Task: ${bot.current_task}</p>` : ''}
                    `;
                    container.appendChild(botElement);
                });
                
                if (bots.length === 0) {
                    container.innerHTML = '<p class="text-gray-400">No bots registered</p>';
                }
            }

            function updateTaskList(tasks) {
                const container = document.getElementById('task-list');
                container.innerHTML = '';
                
                const activeTasks = tasks.filter(task => 
                    task.status === 'assigned' || task.status === 'in_progress'
                ).slice(0, 10);
                
                activeTasks.forEach(task => {
                    const taskElement = document.createElement('div');
                    taskElement.className = 'border border-gray-700 rounded-lg p-3';
                    taskElement.innerHTML = `
                        <div class="flex justify-between items-center mb-2">
                            <h4 class="font-semibold text-sm">${task.title}</h4>
                            <span class="text-xs px-2 py-1 rounded ${task.status === 'in_progress' ? 'bg-blue-600' : 'bg-gray-600'}">${task.status}</span>
                        </div>
                        <div class="w-full bg-gray-700 rounded-full h-2">
                            <div class="bg-blue-600 h-2 rounded-full" style="width: ${task.progress_percentage}%"></div>
                        </div>
                        <p class="text-xs text-gray-400 mt-1">${task.progress_percentage}% • ${task.assigned_bot || 'Unassigned'}</p>
                    `;
                    container.appendChild(taskElement);
                });
                
                if (activeTasks.length === 0) {
                    container.innerHTML = '<p class="text-gray-400">No active tasks</p>';
                }
            }

            function updateAlerts(alerts) {
                const container = document.getElementById('alerts-list');
                container.innerHTML = '';
                
                alerts.slice(0, 5).forEach(alert => {
                    const alertColor = {
                        'error': 'border-red-500 text-red-300',
                        'warning': 'border-yellow-500 text-yellow-300',
                        'info': 'border-blue-500 text-blue-300'
                    }[alert.type] || 'border-gray-500';
                    
                    const alertElement = document.createElement('div');
                    alertElement.className = `border-l-4 ${alertColor} bg-gray-700 p-3 rounded`;
                    alertElement.innerHTML = `
                        <h4 class="font-semibold text-sm">${alert.title}</h4>
                        <p class="text-xs text-gray-400 mt-1">${alert.description}</p>
                    `;
                    container.appendChild(alertElement);
                });
                
                if (alerts.length === 0) {
                    container.innerHTML = '<p class="text-gray-400">No active alerts</p>';
                }
            }

            function updateActivities(activities) {
                const container = document.getElementById('activity-list');
                container.innerHTML = '';
                
                activities.slice(0, 15).forEach(activity => {
                    const typeColor = {
                        'success': 'text-green-400',
                        'warning': 'text-yellow-400',
                        'error': 'text-red-400',
                        'info': 'text-blue-400'
                    }[activity.type] || 'text-gray-400';
                    
                    const activityElement = document.createElement('div');
                    activityElement.className = 'text-sm border-b border-gray-700 pb-2';
                    activityElement.innerHTML = `
                        <div class="flex justify-between items-start">
                            <div>
                                <span class="font-medium ${typeColor}">${activity.bot_id}</span>
                                <span class="text-gray-300"> - ${activity.activity}</span>
                            </div>
                            <span class="text-xs text-gray-500">${new Date(activity.timestamp).toLocaleTimeString()}</span>
                        </div>
                    `;
                    container.appendChild(activityElement);
                });
                
                if (activities.length === 0) {
                    container.innerHTML = '<p class="text-gray-400">No recent activity</p>';
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await dashboard.connect_websocket(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        await dashboard.disconnect_websocket(websocket)

@app.get("/api/status")
async def get_status():
    """REST API endpoint for dashboard data"""
    return dashboard.dashboard_data

def find_free_port(start_port=8300):
    """Find a free port starting from start_port"""
    import socket
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return start_port

def main():
    """Run the bot status dashboard"""
    port = find_free_port(8300)
    print(f"🤖 SuperInstance Bot Dashboard starting on port {port}")
    print(f"📊 Dashboard URL: http://localhost:{port}")
    print(f"🔄 Real-time WebSocket updates enabled")
    print(f"📈 Monitoring bot collaboration for 200% velocity improvement")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()