"""
Advanced Dashboard System for Storage Monitoring
Provides real-time visualization, metrics, and interactive monitoring capabilities
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, asdict
import hashlib

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.utils import PlotlyJSONEncoder
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

@dataclass
class DashboardMetrics:
    """Comprehensive system metrics for dashboard display"""
    timestamp: float
    system_health: str
    total_monitored_paths: int
    active_alerts: int
    resolved_alerts_24h: int
    storage_usage_gb: float
    growth_rate_mb_per_hour: float
    prediction_accuracy: float
    remediation_success_rate: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    uptime_hours: float
    
class RealTimeVisualization:
    """Real-time data visualization engine"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    def generate_growth_trend_chart(self, hours: int = 24) -> Dict:
        """Generate interactive growth trend visualization"""
        if not PLOTLY_AVAILABLE:
            return {"error": "Plotly not available for visualization"}
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get growth data for the specified time period
            cutoff_time = time.time() - (hours * 3600)
            cursor.execute("""
                SELECT timestamp, path, size_bytes, growth_rate
                FROM file_info 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 1000
            """, (cutoff_time,))
            
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                return {"error": "No data available"}
                
            # Convert to DataFrame if pandas available
            if PANDAS_AVAILABLE:
                df = pd.DataFrame(data, columns=['timestamp', 'path', 'size', 'growth_rate'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                
                # Create interactive plot
                fig = px.line(df, x='datetime', y='growth_rate', 
                            color='path', title=f'Storage Growth Trends - Last {hours}h')
                fig.update_layout(
                    xaxis_title="Time",
                    yaxis_title="Growth Rate (MB/hour)",
                    hovermode='x unified'
                )
                
                return json.loads(fig.to_json())
            else:
                # Fallback to simple data structure
                timestamps = [datetime.fromtimestamp(d[0]).isoformat() for d in data]
                growth_rates = [d[3] for d in data]
                
                return {
                    "type": "line",
                    "timestamps": timestamps,
                    "growth_rates": growth_rates,
                    "title": f"Growth Trends - Last {hours}h"
                }
                
        except Exception as e:
            self.logger.error(f"Error generating growth chart: {e}")
            return {"error": str(e)}
    
    def generate_storage_heatmap(self) -> Dict:
        """Generate storage usage heatmap by directory"""
        if not PLOTLY_AVAILABLE:
            return {"error": "Plotly not available for heatmap"}
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current storage usage by directory
            cursor.execute("""
                SELECT path, SUM(size_bytes) / (1024*1024*1024) as size_gb,
                       AVG(growth_rate) as avg_growth
                FROM file_info 
                WHERE timestamp > ?
                GROUP BY SUBSTR(path, 1, INSTR(path || '/', '/') - 1)
                HAVING size_gb > 0.1
                ORDER BY size_gb DESC
                LIMIT 20
            """, (time.time() - 3600,))  # Last hour
            
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                return {"error": "No storage data available"}
                
            paths = [d[0] for d in data]
            sizes = [d[1] for d in data]
            growth = [d[2] or 0 for d in data]
            
            if PANDAS_AVAILABLE:
                # Create heatmap-style visualization
                fig = go.Figure(data=go.Bar(
                    x=paths,
                    y=sizes,
                    marker=dict(
                        color=growth,
                        colorscale='RdYlGn_r',
                        showscale=True,
                        colorbar=dict(title="Growth Rate (MB/h)")
                    ),
                    text=[f"{s:.1f} GB" for s in sizes],
                    textposition='outside'
                ))
                
                fig.update_layout(
                    title="Storage Usage Heatmap by Directory",
                    xaxis_title="Directory",
                    yaxis_title="Storage Usage (GB)",
                    xaxis_tickangle=-45
                )
                
                return json.loads(fig.to_json())
            else:
                return {
                    "type": "heatmap",
                    "directories": paths,
                    "sizes_gb": sizes,
                    "growth_rates": growth
                }
                
        except Exception as e:
            self.logger.error(f"Error generating heatmap: {e}")
            return {"error": str(e)}
    
    def generate_alert_timeline(self, days: int = 7) -> Dict:
        """Generate alert timeline visualization"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = time.time() - (days * 24 * 3600)
            cursor.execute("""
                SELECT timestamp, alert_type, severity, message, resolved
                FROM alerts 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff_time,))
            
            alerts = cursor.fetchall()
            conn.close()
            
            # Group alerts by hour for timeline
            timeline_data = {}
            for alert in alerts:
                hour = datetime.fromtimestamp(alert[0]).strftime("%Y-%m-%d %H:00")
                severity = alert[2]
                
                if hour not in timeline_data:
                    timeline_data[hour] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                
                timeline_data[hour][severity] = timeline_data[hour].get(severity, 0) + 1
            
            return {
                "type": "timeline",
                "data": timeline_data,
                "title": f"Alert Timeline - Last {days} days"
            }
            
        except Exception as e:
            self.logger.error(f"Error generating alert timeline: {e}")
            return {"error": str(e)}

class AdvancedDashboard:
    """Advanced dashboard with real-time metrics and interactive features"""
    
    def __init__(self, db_path: str, config: Dict):
        self.db_path = db_path
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.visualization = RealTimeVisualization(db_path)
        self.start_time = time.time()
        
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview for dashboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current metrics
            current_time = time.time()
            hour_ago = current_time - 3600
            day_ago = current_time - 86400
            
            # Active alerts
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE resolved = 0")
            active_alerts = cursor.fetchone()[0]
            
            # Resolved alerts in last 24h
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE resolved = 1 AND timestamp > ?", (day_ago,))
            resolved_alerts = cursor.fetchone()[0]
            
            # Storage metrics
            cursor.execute("""
                SELECT COUNT(DISTINCT path), 
                       SUM(size_bytes) / (1024*1024*1024),
                       AVG(growth_rate)
                FROM file_info 
                WHERE timestamp > ?
            """, (hour_ago,))
            
            storage_data = cursor.fetchone()
            monitored_paths = storage_data[0] or 0
            storage_gb = storage_data[1] or 0
            avg_growth = storage_data[2] or 0
            
            # System performance (mock data - replace with actual system metrics)
            import psutil
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            
            conn.close()
            
            return {
                "overview": {
                    "system_health": self._calculate_system_health(active_alerts, cpu_usage, memory_info.percent),
                    "uptime_hours": (current_time - self.start_time) / 3600,
                    "total_monitored_paths": monitored_paths,
                    "active_alerts": active_alerts,
                    "resolved_alerts_24h": resolved_alerts,
                    "storage_usage_gb": round(storage_gb, 2),
                    "growth_rate_mb_per_hour": round(avg_growth, 2)
                },
                "system_resources": {
                    "cpu_usage": round(cpu_usage, 1),
                    "memory_usage": round(memory_info.percent, 1),
                    "disk_usage": round((disk_info.used / disk_info.total) * 100, 1),
                    "available_space_gb": round(disk_info.free / (1024**3), 1)
                },
                "recent_activity": await self._get_recent_activity(),
                "top_consumers": await self._get_top_storage_consumers()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system overview: {e}")
            return {"error": str(e)}
    
    def _calculate_system_health(self, alerts: int, cpu: float, memory: float) -> str:
        """Calculate overall system health status"""
        if alerts > 5 or cpu > 90 or memory > 95:
            return "critical"
        elif alerts > 2 or cpu > 70 or memory > 80:
            return "warning"
        elif alerts > 0 or cpu > 50 or memory > 60:
            return "caution"
        else:
            return "healthy"
    
    async def _get_recent_activity(self) -> List[Dict]:
        """Get recent system activity for dashboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent alerts and remediation actions
            cursor.execute("""
                SELECT timestamp, alert_type, severity, message
                FROM alerts 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    "timestamp": datetime.fromtimestamp(row[0]).strftime("%H:%M:%S"),
                    "type": row[1],
                    "severity": row[2],
                    "message": row[3]
                })
            
            conn.close()
            return activities
            
        except Exception as e:
            self.logger.error(f"Error getting recent activity: {e}")
            return []
    
    async def _get_top_storage_consumers(self) -> List[Dict]:
        """Get top storage consuming directories"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT path, 
                       MAX(size_bytes) / (1024*1024*1024) as size_gb,
                       MAX(growth_rate) as growth_rate
                FROM file_info 
                WHERE timestamp > ?
                GROUP BY SUBSTR(path, 1, 50)  -- Group by directory prefix
                ORDER BY size_gb DESC 
                LIMIT 10
            """, (time.time() - 3600,))
            
            consumers = []
            for row in cursor.fetchall():
                consumers.append({
                    "path": row[0],
                    "size_gb": round(row[1], 2),
                    "growth_rate": round(row[2] or 0, 2)
                })
            
            conn.close()
            return consumers
            
        except Exception as e:
            self.logger.error(f"Error getting top consumers: {e}")
            return []
    
    async def get_predictive_analytics(self) -> Dict[str, Any]:
        """Get predictive analytics data for dashboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get growth patterns for prediction
            cursor.execute("""
                SELECT path, growth_rate, size_bytes
                FROM file_info 
                WHERE timestamp > ? AND growth_rate > 0
                ORDER BY growth_rate DESC
                LIMIT 20
            """, (time.time() - 86400,))  # Last 24 hours
            
            data = cursor.fetchall()
            conn.close()
            
            predictions = []
            for row in data:
                path, growth_rate, current_size = row
                
                # Simple linear prediction
                hours_to_1gb = None
                hours_to_critical = None
                
                if growth_rate > 0:
                    bytes_per_hour = growth_rate * 1024 * 1024  # Convert MB/h to bytes/h
                    
                    # Time to reach 1GB
                    if current_size < 1024**3:
                        hours_to_1gb = (1024**3 - current_size) / bytes_per_hour
                    
                    # Time to reach critical threshold (based on available space)
                    critical_size = current_size + (10 * 1024**3)  # 10GB beyond current
                    hours_to_critical = (critical_size - current_size) / bytes_per_hour
                
                predictions.append({
                    "path": path,
                    "current_size_gb": round(current_size / (1024**3), 2),
                    "growth_rate_mb_h": round(growth_rate, 2),
                    "hours_to_1gb": round(hours_to_1gb, 1) if hours_to_1gb else None,
                    "hours_to_critical": round(hours_to_critical, 1) if hours_to_critical else None,
                    "risk_level": self._calculate_risk_level(growth_rate, current_size)
                })
            
            return {
                "predictions": predictions,
                "summary": {
                    "high_risk_paths": len([p for p in predictions if p["risk_level"] == "high"]),
                    "medium_risk_paths": len([p for p in predictions if p["risk_level"] == "medium"]),
                    "total_monitored": len(predictions)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting predictive analytics: {e}")
            return {"error": str(e)}
    
    def _calculate_risk_level(self, growth_rate: float, current_size: int) -> str:
        """Calculate risk level based on growth rate and current size"""
        # High risk: Fast growth or already large
        if growth_rate > 100 or current_size > 5 * 1024**3:  # >100MB/h or >5GB
            return "high"
        elif growth_rate > 50 or current_size > 1024**3:  # >50MB/h or >1GB
            return "medium"
        else:
            return "low"
    
    async def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive system report"""
        try:
            overview = await self.get_system_overview()
            analytics = await self.get_predictive_analytics()
            
            # Generate visualizations
            growth_chart = self.visualization.generate_growth_trend_chart(24)
            heatmap = self.visualization.generate_storage_heatmap()
            alert_timeline = self.visualization.generate_alert_timeline(7)
            
            return {
                "report_timestamp": datetime.now().isoformat(),
                "system_overview": overview,
                "predictive_analytics": analytics,
                "visualizations": {
                    "growth_trends": growth_chart,
                    "storage_heatmap": heatmap,
                    "alert_timeline": alert_timeline
                },
                "recommendations": self._generate_recommendations(overview, analytics)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive report: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(self, overview: Dict, analytics: Dict) -> List[Dict]:
        """Generate intelligent recommendations based on current system state"""
        recommendations = []
        
        try:
            # Check system health
            if overview.get("overview", {}).get("active_alerts", 0) > 5:
                recommendations.append({
                    "priority": "high",
                    "category": "alerts",
                    "title": "High Alert Volume",
                    "description": "System has many active alerts - review and address critical issues",
                    "action": "Review active alerts and prioritize remediation"
                })
            
            # Check storage growth
            growth_rate = overview.get("overview", {}).get("growth_rate_mb_per_hour", 0)
            if growth_rate > 100:
                recommendations.append({
                    "priority": "high",
                    "category": "storage",
                    "title": "Rapid Storage Growth",
                    "description": f"Storage growing at {growth_rate} MB/hour - investigate causes",
                    "action": "Enable emergency monitoring and consider cleanup actions"
                })
            
            # Check resource usage
            resources = overview.get("system_resources", {})
            if resources.get("disk_usage", 0) > 85:
                recommendations.append({
                    "priority": "critical",
                    "category": "resources",
                    "title": "Low Disk Space",
                    "description": f"Disk usage at {resources['disk_usage']}% - immediate action needed",
                    "action": "Run emergency cleanup or expand storage capacity"
                })
            
            # Check high-risk predictions
            high_risk_count = analytics.get("summary", {}).get("high_risk_paths", 0)
            if high_risk_count > 3:
                recommendations.append({
                    "priority": "medium",
                    "category": "prediction",
                    "title": "Multiple High-Risk Paths",
                    "description": f"{high_risk_count} paths predicted to have storage issues",
                    "action": "Review predictive analytics and implement preventive measures"
                })
            
            # Performance recommendations
            cpu_usage = resources.get("cpu_usage", 0)
            if cpu_usage > 80:
                recommendations.append({
                    "priority": "medium", 
                    "category": "performance",
                    "title": "High CPU Usage",
                    "description": f"CPU usage at {cpu_usage}% - may impact monitoring performance",
                    "action": "Consider reducing scan frequency or adding more worker threads"
                })
                
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            
        return recommendations

class WebSocketDashboard:
    """WebSocket-based real-time dashboard updates"""
    
    def __init__(self, dashboard: AdvancedDashboard):
        self.dashboard = dashboard
        self.connected_clients = set()
        self.logger = logging.getLogger(__name__)
        
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.connected_clients.add(websocket)
        self.logger.info(f"Dashboard client connected. Total: {len(self.connected_clients)}")
        
        # Send initial data
        try:
            overview = await self.dashboard.get_system_overview()
            await websocket.send_text(json.dumps({
                "type": "initial_data",
                "data": overview
            }))
        except Exception as e:
            self.logger.error(f"Error sending initial data: {e}")
    
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.connected_clients.discard(websocket)
        self.logger.info(f"Dashboard client disconnected. Total: {len(self.connected_clients)}")
    
    async def broadcast_update(self, update_type: str, data: Dict):
        """Broadcast update to all connected clients"""
        if not self.connected_clients:
            return
            
        message = json.dumps({
            "type": update_type,
            "timestamp": time.time(),
            "data": data
        })
        
        # Send to all clients (remove failed connections)
        failed_clients = set()
        for client in self.connected_clients:
            try:
                await client.send_text(message)
            except Exception as e:
                self.logger.warning(f"Failed to send update to client: {e}")
                failed_clients.add(client)
        
        # Remove failed clients
        self.connected_clients -= failed_clients
    
    async def start_periodic_updates(self):
        """Start periodic dashboard updates"""
        while True:
            try:
                if self.connected_clients:
                    overview = await self.dashboard.get_system_overview()
                    await self.broadcast_update("system_update", overview)
                
                # Wait 30 seconds before next update
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error in periodic updates: {e}")
                await asyncio.sleep(60)  # Wait longer on error