#!/usr/bin/env python3
"""
Advanced Monitoring, Observability, and Alerting System
Real-time metrics collection, distributed tracing, and intelligent alerting
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio
import sqlite3
import numpy as np
import json
import logging
import uvicorn
import os
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import threading
import time
import psutil
import aiofiles
from dataclasses import dataclass
import hashlib
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ActiveLog Monitoring & Observability",
    description="Advanced monitoring, observability, and alerting system",
    version="2.0.0"
)

# Configuration
DB_PATH = "data/monitoring.db"
METRICS_RETENTION_DAYS = 30
ALERT_CHECK_INTERVAL = 30  # seconds
MAX_WEBSOCKET_CONNECTIONS = 100

# Pydantic Models
class MetricPoint(BaseModel):
    service_name: str
    metric_name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = {}
    unit: str = ""

class AlertRule(BaseModel):
    name: str
    service_pattern: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "contains"
    threshold: float
    duration_minutes: int = 5
    severity: str = "warning"  # "info", "warning", "error", "critical"
    enabled: bool = True

class ServiceHealth(BaseModel):
    service_name: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    last_check: datetime
    response_time_ms: float = 0
    error_rate: float = 0
    availability: float = 100.0

class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: str = "ok"  # "ok", "error", "timeout"
    tags: Dict[str, str] = {}

@dataclass
class Alert:
    id: str
    rule_name: str
    service_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: str
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    status: str = "firing"  # "firing", "resolved"

class MonitoringSystem:
    """Advanced monitoring and observability system"""
    
    def __init__(self):
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=10000))
        self.alert_rules = {}
        self.active_alerts = {}
        self.service_health = {}
        self.traces = defaultdict(list)
        self.websocket_connections = set()
        
        self.init_db()
        self.start_background_tasks()
    
    def init_db(self):
        """Initialize monitoring database"""
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT,
                metric_name TEXT,
                value REAL,
                timestamp DATETIME,
                labels TEXT,
                unit TEXT
            )
        """)
        
        # Alert rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                service_pattern TEXT,
                metric_name TEXT,
                condition TEXT,
                threshold REAL,
                duration_minutes INTEGER,
                severity TEXT,
                enabled BOOLEAN
            )
        """)
        
        # Alerts history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                rule_name TEXT,
                service_name TEXT,
                metric_name TEXT,
                current_value REAL,
                threshold REAL,
                severity TEXT,
                message TEXT,
                triggered_at DATETIME,
                resolved_at DATETIME,
                status TEXT
            )
        """)
        
        # Service health table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT,
                status TEXT,
                last_check DATETIME,
                response_time_ms REAL,
                error_rate REAL,
                availability REAL
            )
        """)
        
        # Traces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                span_id TEXT,
                parent_span_id TEXT,
                service_name TEXT,
                operation_name TEXT,
                start_time DATETIME,
                end_time DATETIME,
                duration_ms REAL,
                status TEXT,
                tags TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_metric(self, metric: MetricPoint):
        """Record a metric point"""
        self.metrics_buffer[f"{metric.service_name}.{metric.metric_name}"].append(metric)
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO metrics (service_name, metric_name, value, timestamp, labels, unit)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            metric.service_name, metric.metric_name, metric.value,
            metric.timestamp, json.dumps(metric.labels), metric.unit
        ))
        
        conn.commit()
        conn.close()
        
        # Check alert rules
        asyncio.create_task(self.check_alerts_for_metric(metric))
    
    async def check_alerts_for_metric(self, metric: MetricPoint):
        """Check if metric triggers any alert rules"""
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # Check if service matches pattern
            if rule.service_pattern in metric.service_name and rule.metric_name == metric.metric_name:
                should_trigger = False
                
                if rule.condition == "gt" and metric.value > rule.threshold:
                    should_trigger = True
                elif rule.condition == "lt" and metric.value < rule.threshold:
                    should_trigger = True
                elif rule.condition == "eq" and metric.value == rule.threshold:
                    should_trigger = True
                
                if should_trigger:
                    alert_id = f"{rule_name}_{metric.service_name}_{int(time.time())}"
                    
                    alert = Alert(
                        id=alert_id,
                        rule_name=rule_name,
                        service_name=metric.service_name,
                        metric_name=metric.metric_name,
                        current_value=metric.value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        message=f"{metric.service_name} {metric.metric_name} is {metric.value} (threshold: {rule.threshold})",
                        triggered_at=datetime.now()
                    )
                    
                    self.active_alerts[alert_id] = alert
                    await self.send_alert_to_websockets(alert)
                    self.store_alert_history(alert)
    
    async def send_alert_to_websockets(self, alert: Alert):
        """Send alert to all connected websocket clients"""
        if self.websocket_connections:
            alert_data = {
                "type": "alert",
                "alert_id": alert.id,
                "rule_name": alert.rule_name,
                "service_name": alert.service_name,
                "severity": alert.severity,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat()
            }
            
            disconnected = set()
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(json.dumps(alert_data))
                except Exception as e:
                    logger.warning(f"Failed to send alert to websocket: {e}")
                    disconnected.add(websocket)
            
            # Remove disconnected websockets
            self.websocket_connections -= disconnected
    
    def store_alert_history(self, alert: Alert):
        """Store alert in history database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO alerts_history 
            (alert_id, rule_name, service_name, metric_name, current_value, 
             threshold, severity, message, triggered_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id, alert.rule_name, alert.service_name, alert.metric_name,
            alert.current_value, alert.threshold, alert.severity, alert.message,
            alert.triggered_at, alert.status
        ))
        
        conn.commit()
        conn.close()
    
    def update_service_health(self, health: ServiceHealth):
        """Update service health status"""
        self.service_health[health.service_name] = health
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO service_health 
            (service_name, status, last_check, response_time_ms, error_rate, availability)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            health.service_name, health.status, health.last_check,
            health.response_time_ms, health.error_rate, health.availability
        ))
        
        conn.commit()
        conn.close()
    
    def record_trace_span(self, span: TraceSpan):
        """Record a distributed trace span"""
        self.traces[span.trace_id].append(span)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO traces 
            (trace_id, span_id, parent_span_id, service_name, operation_name,
             start_time, end_time, duration_ms, status, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            span.trace_id, span.span_id, span.parent_span_id, span.service_name,
            span.operation_name, span.start_time, span.end_time, span.duration_ms,
            span.status, json.dumps(span.tags)
        ))
        
        conn.commit()
        conn.close()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_usage": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "timestamp": datetime.now().isoformat()
        }
    
    def start_background_tasks(self):
        """Start background monitoring tasks"""
        def system_metrics_collector():
            while True:
                try:
                    metrics = self.get_system_metrics()
                    
                    # Record system metrics
                    timestamp = datetime.now()
                    self.record_metric(MetricPoint(
                        service_name="system",
                        metric_name="cpu_usage",
                        value=metrics["cpu_usage"],
                        timestamp=timestamp
                    ))
                    
                    self.record_metric(MetricPoint(
                        service_name="system",
                        metric_name="memory_usage", 
                        value=metrics["memory_usage"],
                        timestamp=timestamp
                    ))
                    
                    self.record_metric(MetricPoint(
                        service_name="system",
                        metric_name="disk_usage",
                        value=metrics["disk_usage"],
                        timestamp=timestamp
                    ))
                    
                    time.sleep(30)  # Collect every 30 seconds
                    
                except Exception as e:
                    logger.error(f"System metrics collection error: {e}")
                    time.sleep(30)
        
        def cleanup_old_data():
            while True:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    cutoff_date = datetime.now() - timedelta(days=METRICS_RETENTION_DAYS)
                    
                    cursor.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_date,))
                    cursor.execute("DELETE FROM alerts_history WHERE triggered_at < ?", (cutoff_date,))
                    cursor.execute("DELETE FROM service_health WHERE last_check < ?", (cutoff_date,))
                    cursor.execute("DELETE FROM traces WHERE start_time < ?", (cutoff_date,))
                    
                    conn.commit()
                    conn.close()
                    
                    logger.info(f"Cleaned up monitoring data older than {METRICS_RETENTION_DAYS} days")
                    time.sleep(3600 * 24)  # Run daily
                    
                except Exception as e:
                    logger.error(f"Data cleanup error: {e}")
                    time.sleep(3600)
        
        # Start background threads
        threading.Thread(target=system_metrics_collector, daemon=True).start()
        threading.Thread(target=cleanup_old_data, daemon=True).start()
        logger.info("Monitoring background tasks started")

# Global monitoring system
monitoring = MonitoringSystem()

@app.get("/")
async def root():
    return {
        "service": "ActiveLog Monitoring & Observability",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "Real-time metrics collection",
            "Distributed tracing", 
            "Intelligent alerting",
            "Service health monitoring",
            "WebSocket notifications",
            "System metrics collection"
        ]
    }

@app.post("/metrics")
async def record_metrics(metric: MetricPoint):
    """Record a metric point"""
    try:
        monitoring.record_metric(metric)
        return {"status": "recorded", "timestamp": metric.timestamp}
    except Exception as e:
        logger.error(f"Metric recording error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/{service_name}")
async def get_service_metrics(service_name: str, hours: int = 24, metric_name: Optional[str] = None):
    """Get metrics for a service"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        
        if metric_name:
            cursor.execute("""
                SELECT metric_name, value, timestamp, labels, unit
                FROM metrics 
                WHERE service_name = ? AND metric_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (service_name, metric_name, since))
        else:
            cursor.execute("""
                SELECT metric_name, value, timestamp, labels, unit
                FROM metrics 
                WHERE service_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (service_name, since))
        
        results = cursor.fetchall()
        conn.close()
        
        metrics = []
        for row in results:
            metrics.append({
                "metric_name": row[0],
                "value": row[1], 
                "timestamp": row[2],
                "labels": json.loads(row[3]) if row[3] else {},
                "unit": row[4]
            })
        
        return {
            "service_name": service_name,
            "metrics": metrics,
            "total_points": len(metrics),
            "time_range_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Get metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/health")
async def update_service_health(health: ServiceHealth):
    """Update service health status"""
    try:
        monitoring.update_service_health(health)
        return {"status": "updated", "service": health.service_name}
    except Exception as e:
        logger.error(f"Health update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def get_all_service_health():
    """Get health status of all services"""
    try:
        return {
            "services": monitoring.service_health,
            "system_metrics": monitoring.get_system_metrics(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get health error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/traces")
async def record_trace_span(span: TraceSpan):
    """Record a distributed trace span"""
    try:
        monitoring.record_trace_span(span)
        return {"status": "recorded", "trace_id": span.trace_id, "span_id": span.span_id}
    except Exception as e:
        logger.error(f"Trace recording error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get complete trace by ID"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT trace_id, span_id, parent_span_id, service_name, operation_name,
                   start_time, end_time, duration_ms, status, tags
            FROM traces 
            WHERE trace_id = ?
            ORDER BY start_time
        """, (trace_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        spans = []
        for row in results:
            spans.append({
                "trace_id": row[0],
                "span_id": row[1],
                "parent_span_id": row[2],
                "service_name": row[3],
                "operation_name": row[4],
                "start_time": row[5],
                "end_time": row[6],
                "duration_ms": row[7],
                "status": row[8],
                "tags": json.loads(row[9]) if row[9] else {}
            })
        
        return {
            "trace_id": trace_id,
            "spans": spans,
            "total_spans": len(spans)
        }
        
    except Exception as e:
        logger.error(f"Get trace error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/rules")
async def create_alert_rule(rule: AlertRule):
    """Create a new alert rule"""
    try:
        monitoring.alert_rules[rule.name] = rule
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO alert_rules 
            (name, service_pattern, metric_name, condition, threshold, 
             duration_minutes, severity, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule.name, rule.service_pattern, rule.metric_name, rule.condition,
            rule.threshold, rule.duration_minutes, rule.severity, rule.enabled
        ))
        
        conn.commit()
        conn.close()
        
        return {"status": "created", "rule_name": rule.name}
        
    except Exception as e:
        logger.error(f"Create alert rule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts/active")
async def get_active_alerts():
    """Get all active alerts"""
    alerts = []
    for alert in monitoring.active_alerts.values():
        alerts.append({
            "id": alert.id,
            "rule_name": alert.rule_name,
            "service_name": alert.service_name,
            "severity": alert.severity,
            "message": alert.message,
            "triggered_at": alert.triggered_at.isoformat(),
            "status": alert.status
        })
    
    return {"active_alerts": alerts, "total": len(alerts)}

@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring updates"""
    await websocket.accept()
    
    if len(monitoring.websocket_connections) >= MAX_WEBSOCKET_CONNECTIONS:
        await websocket.close(code=1000, reason="Maximum connections reached")
        return
    
    monitoring.websocket_connections.add(websocket)
    
    try:
        while True:
            # Send periodic system metrics
            system_metrics = monitoring.get_system_metrics()
            await websocket.send_text(json.dumps({
                "type": "system_metrics",
                "data": system_metrics
            }))
            
            await asyncio.sleep(10)  # Send every 10 seconds
            
    except Exception as e:
        logger.info(f"WebSocket connection closed: {e}")
    finally:
        monitoring.websocket_connections.discard(websocket)

@app.get("/dashboard")
async def get_monitoring_dashboard():
    """Get comprehensive monitoring dashboard data"""
    try:
        # Get recent metrics summary
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=1)
        
        cursor.execute("""
            SELECT service_name, COUNT(*) as metric_count
            FROM metrics 
            WHERE timestamp > ?
            GROUP BY service_name
        """, (since,))
        
        service_metrics = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT COUNT(*) as total_alerts
            FROM alerts_history 
            WHERE triggered_at > ?
        """, (since,))
        
        recent_alerts = cursor.fetchone()[0]
        
        conn.close()
        
        dashboard = {
            "system_metrics": monitoring.get_system_metrics(),
            "service_health": monitoring.service_health,
            "active_alerts": len(monitoring.active_alerts),
            "recent_alerts_1h": recent_alerts,
            "service_metrics_1h": service_metrics,
            "websocket_connections": len(monitoring.websocket_connections),
            "timestamp": datetime.now().isoformat()
        }
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8091))
    uvicorn.run(app, host="0.0.0.0", port=port)