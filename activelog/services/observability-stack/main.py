#!/usr/bin/env python3
"""
Advanced Observability Stack for ActiveLog
Comprehensive monitoring, alerting, and analytics platform
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
import asyncpg
import redis
import aioredis
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import os
import psutil
import requests

app = FastAPI(title="ActiveLog Observability Stack", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
METRICS = {
    'api_requests_total': Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status']),
    'api_request_duration': Histogram('api_request_duration_seconds', 'API request duration', ['method', 'endpoint']),
    'system_cpu_usage': Gauge('system_cpu_usage_percent', 'System CPU usage percentage'),
    'system_memory_usage': Gauge('system_memory_usage_percent', 'System memory usage percentage'),
    'database_connections': Gauge('database_connections_active', 'Active database connections'),
    'trading_volume': Gauge('trading_volume_cc', 'Trading volume in CC'),
    'user_sessions': Gauge('user_sessions_active', 'Active user sessions'),
    'anomalies_detected': Counter('anomalies_detected_total', 'Total anomalies detected', ['service', 'type']),
    'alerts_fired': Counter('alerts_fired_total', 'Total alerts fired', ['severity', 'service'])
}

@dataclass
class MetricData:
    timestamp: float
    service: str
    metric_name: str
    value: float
    labels: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class Alert:
    id: str
    service: str
    severity: str  # critical, warning, info
    title: str
    description: str
    timestamp: float
    resolved: bool = False
    resolution_timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AnomalyDetection:
    id: str
    service: str
    metric_name: str
    anomaly_score: float
    timestamp: float
    data_point: Dict[str, Any]
    is_anomaly: bool

class ObservabilityStack:
    def __init__(self):
        self.db_path = "data/observability.db"
        self.redis_client = None
        self.postgres_client = None
        self.metrics_buffer = []
        self.alerts = []
        self.anomaly_detectors = {}
        self.active_websockets = []
        
        # Services to monitor
        self.monitored_services = [
            "activeLedger-trading-engine",
            "activeLedger-settlement", 
            "activeLedger-compliance",
            "activeLedger-market-data",
            "activeLedger-wallet",
            "activeLedger-dream-mode"
        ]
        
        self._init_database()
        self._init_anomaly_detectors()
        
        # Start background tasks
        asyncio.create_task(self._collect_system_metrics())
        asyncio.create_task(self._process_metrics_buffer())
        asyncio.create_task(self._run_anomaly_detection())
        asyncio.create_task(self._check_service_health())
        asyncio.create_task(self._cleanup_old_data())
    
    def _init_database(self):
        """Initialize SQLite database for observability data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                service TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                labels TEXT,
                metadata TEXT,
                INDEX(timestamp),
                INDEX(service),
                INDEX(metric_name)
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp REAL NOT NULL,
                resolved BOOLEAN NOT NULL DEFAULT 0,
                resolution_timestamp REAL,
                metadata TEXT
            )
        ''')
        
        # Anomalies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                anomaly_score REAL NOT NULL,
                timestamp REAL NOT NULL,
                data_point TEXT NOT NULL,
                is_anomaly BOOLEAN NOT NULL
            )
        ''')
        
        # Service health table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_health (
                service TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_check REAL NOT NULL,
                response_time REAL,
                error_count INTEGER DEFAULT 0,
                uptime_percentage REAL DEFAULT 100.0,
                last_error TEXT
            )
        ''')
        
        # Performance insights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_insights (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                insight_type TEXT NOT NULL,
                service TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                priority INTEGER NOT NULL,
                implemented BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_anomaly_detectors(self):
        """Initialize ML models for anomaly detection"""
        for service in self.monitored_services:
            self.anomaly_detectors[service] = {
                'model': IsolationForest(contamination=0.1, random_state=42),
                'scaler': StandardScaler(),
                'trained': False,
                'training_data': [],
                'feature_columns': ['cpu_usage', 'memory_usage', 'response_time', 'error_rate']
            }
    
    async def initialize_connections(self):
        """Initialize database connections"""
        try:
            self.redis_client = await aioredis.from_url("redis://localhost:6379")
            # PostgreSQL connection would be initialized here if available
        except Exception as e:
            print(f"Warning: Could not connect to external databases: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        while True:
            try:
                # System metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                METRICS['system_cpu_usage'].set(cpu_percent)
                METRICS['system_memory_usage'].set(memory.percent)
                
                # Store in database
                await self._store_metric(MetricData(
                    timestamp=time.time(),
                    service="system",
                    metric_name="cpu_usage",
                    value=cpu_percent,
                    labels={"host": "localhost"}
                ))
                
                await self._store_metric(MetricData(
                    timestamp=time.time(),
                    service="system",
                    metric_name="memory_usage",
                    value=memory.percent,
                    labels={"host": "localhost"}
                ))
                
                # Check for system-level anomalies
                if cpu_percent > 90:
                    await self._create_alert("system", "warning", 
                                           "High CPU Usage", 
                                           f"CPU usage is {cpu_percent}%")
                
                if memory.percent > 90:
                    await self._create_alert("system", "warning",
                                           "High Memory Usage", 
                                           f"Memory usage is {memory.percent}%")
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)
    
    async def _check_service_health(self):
        """Check health of all monitored services"""
        while True:
            for service in self.monitored_services:
                try:
                    # Map service names to ports
                    port_mapping = {
                        "activeLedger-trading-engine": 8500,
                        "activeLedger-settlement": 8501,
                        "activeLedger-compliance": 8502,
                        "activeLedger-market-data": 8503,
                        "activeLedger-wallet": 8504,
                        "activeLedger-dream-mode": 8510
                    }
                    
                    port = port_mapping.get(service, 8000)
                    url = f"http://localhost:{port}/health"
                    
                    start_time = time.time()
                    response = requests.get(url, timeout=10)
                    response_time = (time.time() - start_time) * 1000  # ms
                    
                    status = "healthy" if response.status_code == 200 else "unhealthy"
                    
                    # Update service health
                    await self._update_service_health(service, status, response_time)
                    
                    if status == "unhealthy":
                        await self._create_alert(service, "critical",
                                               "Service Unhealthy",
                                               f"Service {service} returned status code {response.status_code}")
                
                except requests.exceptions.RequestException as e:
                    await self._update_service_health(service, "down", None, str(e))
                    await self._create_alert(service, "critical",
                                           "Service Down",
                                           f"Service {service} is not responding: {str(e)}")
                
                except Exception as e:
                    print(f"Error checking health for {service}: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _store_metric(self, metric: MetricData):
        """Store metric in database"""
        self.metrics_buffer.append(metric)
        
        # Also broadcast to WebSocket clients
        await self._broadcast_metric(metric)
    
    async def _process_metrics_buffer(self):
        """Process buffered metrics and store in database"""
        while True:
            if self.metrics_buffer:
                batch = self.metrics_buffer[:100]  # Process in batches
                self.metrics_buffer = self.metrics_buffer[100:]
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for metric in batch:
                    cursor.execute('''
                        INSERT INTO metrics (id, timestamp, service, metric_name, value, labels, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(uuid.uuid4()),
                        metric.timestamp,
                        metric.service,
                        metric.metric_name,
                        metric.value,
                        json.dumps(metric.labels),
                        json.dumps(metric.metadata) if metric.metadata else None
                    ))
                
                conn.commit()
                conn.close()
            
            await asyncio.sleep(10)  # Process every 10 seconds
    
    async def _run_anomaly_detection(self):
        """Run anomaly detection on collected metrics"""
        while True:
            try:
                for service in self.monitored_services:
                    detector = self.anomaly_detectors[service]
                    
                    # Get recent metrics for this service
                    recent_metrics = await self._get_recent_metrics(service, hours=1)
                    
                    if len(recent_metrics) < 10:  # Need minimum data points
                        continue
                    
                    # Prepare feature matrix
                    features = []
                    for metric in recent_metrics:
                        if metric['metric_name'] in detector['feature_columns']:
                            features.append([
                                metric['timestamp'],
                                metric['value'],
                                len(recent_metrics)  # Additional features can be added
                            ])
                    
                    if len(features) < 5:
                        continue
                    
                    features_array = np.array(features)
                    
                    if not detector['trained']:
                        # Train the model
                        if len(features) >= 20:  # Minimum training data
                            detector['scaler'].fit(features_array)
                            scaled_features = detector['scaler'].transform(features_array)
                            detector['model'].fit(scaled_features)
                            detector['trained'] = True
                    else:
                        # Detect anomalies
                        scaled_features = detector['scaler'].transform(features_array)
                        anomaly_scores = detector['model'].decision_function(scaled_features)
                        predictions = detector['model'].predict(scaled_features)
                        
                        # Process recent predictions
                        for i, (score, prediction) in enumerate(zip(anomaly_scores, predictions)):
                            if prediction == -1:  # Anomaly detected
                                anomaly = AnomalyDetection(
                                    id=str(uuid.uuid4()),
                                    service=service,
                                    metric_name="composite",
                                    anomaly_score=float(score),
                                    timestamp=recent_metrics[i]['timestamp'],
                                    data_point=recent_metrics[i],
                                    is_anomaly=True
                                )
                                
                                await self._store_anomaly(anomaly)
                                await self._create_alert(service, "warning",
                                                       "Anomaly Detected",
                                                       f"Unusual behavior detected in {service}")
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                print(f"Error in anomaly detection: {e}")
                await asyncio.sleep(60)
    
    async def _get_recent_metrics(self, service: str, hours: int = 1) -> List[Dict]:
        """Get recent metrics for a service"""
        since_timestamp = time.time() - (hours * 3600)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, service, metric_name, value, labels, metadata
            FROM metrics 
            WHERE service = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (service, since_timestamp))
        
        rows = cursor.fetchall()
        conn.close()
        
        metrics = []
        for row in rows:
            metrics.append({
                'timestamp': row[0],
                'service': row[1],
                'metric_name': row[2],
                'value': row[3],
                'labels': json.loads(row[4]) if row[4] else {},
                'metadata': json.loads(row[5]) if row[5] else {}
            })
        
        return metrics
    
    async def _store_anomaly(self, anomaly: AnomalyDetection):
        """Store anomaly detection result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO anomalies (id, service, metric_name, anomaly_score, timestamp, data_point, is_anomaly)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            anomaly.id,
            anomaly.service,
            anomaly.metric_name,
            anomaly.anomaly_score,
            anomaly.timestamp,
            json.dumps(anomaly.data_point),
            anomaly.is_anomaly
        ))
        
        conn.commit()
        conn.close()
        
        METRICS['anomalies_detected'].labels(service=anomaly.service, type='behavioral').inc()
    
    async def _create_alert(self, service: str, severity: str, title: str, description: str, metadata: Dict = None):
        """Create and store alert"""
        alert = Alert(
            id=str(uuid.uuid4()),
            service=service,
            severity=severity,
            title=title,
            description=description,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (id, service, severity, title, description, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.id,
            alert.service,
            alert.severity,
            alert.title,
            alert.description,
            alert.timestamp,
            json.dumps(alert.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        METRICS['alerts_fired'].labels(severity=severity, service=service).inc()
        
        # Broadcast alert to WebSocket clients
        await self._broadcast_alert(alert)
    
    async def _update_service_health(self, service: str, status: str, response_time: Optional[float], error: Optional[str] = None):
        """Update service health status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO service_health 
            (service, status, last_check, response_time, last_error)
            VALUES (?, ?, ?, ?, ?)
        ''', (service, status, time.time(), response_time, error))
        
        conn.commit()
        conn.close()
    
    async def _broadcast_metric(self, metric: MetricData):
        """Broadcast metric to WebSocket clients"""
        if self.active_websockets:
            message = {
                'type': 'metric',
                'data': asdict(metric)
            }
            
            # Remove disconnected clients
            active_clients = []
            for websocket in self.active_websockets:
                try:
                    await websocket.send_json(message)
                    active_clients.append(websocket)
                except:
                    pass  # Client disconnected
            
            self.active_websockets = active_clients
    
    async def _broadcast_alert(self, alert: Alert):
        """Broadcast alert to WebSocket clients"""
        if self.active_websockets:
            message = {
                'type': 'alert',
                'data': asdict(alert)
            }
            
            active_clients = []
            for websocket in self.active_websockets:
                try:
                    await websocket.send_json(message)
                    active_clients.append(websocket)
                except:
                    pass
            
            self.active_websockets = active_clients
    
    async def _cleanup_old_data(self):
        """Clean up old observability data"""
        while True:
            try:
                # Remove metrics older than 30 days
                cutoff_time = time.time() - (30 * 24 * 60 * 60)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff_time,))
                cursor.execute('DELETE FROM anomalies WHERE timestamp < ?', (cutoff_time,))
                
                # Remove resolved alerts older than 7 days
                alert_cutoff = time.time() - (7 * 24 * 60 * 60)
                cursor.execute('DELETE FROM alerts WHERE resolved = 1 AND resolution_timestamp < ?', (alert_cutoff,))
                
                conn.commit()
                conn.close()
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                print(f"Error in cleanup: {e}")
                await asyncio.sleep(3600)

# Initialize observability stack
obs_stack = ObservabilityStack()

@app.on_event("startup")
async def startup_event():
    await obs_stack.initialize_connections()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "observability-stack"}

@app.post("/api/metrics")
async def ingest_metric(metric_data: dict):
    """Ingest custom metrics from services"""
    try:
        metric = MetricData(
            timestamp=metric_data.get('timestamp', time.time()),
            service=metric_data['service'],
            metric_name=metric_data['metric_name'],
            value=float(metric_data['value']),
            labels=metric_data.get('labels', {}),
            metadata=metric_data.get('metadata')
        )
        
        await obs_stack._store_metric(metric)
        return {"success": True, "message": "Metric ingested"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/metrics/{service}")
async def get_service_metrics(service: str, hours: int = 24):
    """Get metrics for a specific service"""
    metrics = await obs_stack._get_recent_metrics(service, hours)
    return {"success": True, "service": service, "metrics": metrics}

@app.get("/api/alerts")
async def get_alerts(severity: str = None, resolved: bool = None, limit: int = 50):
    """Get alerts with optional filtering"""
    conn = sqlite3.connect(obs_stack.db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM alerts WHERE 1=1"
    params = []
    
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    
    if resolved is not None:
        query += " AND resolved = ?"
        params.append(resolved)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    alerts = []
    columns = ['id', 'service', 'severity', 'title', 'description', 'timestamp', 'resolved', 'resolution_timestamp', 'metadata']
    
    for row in rows:
        alert_data = dict(zip(columns, row))
        if alert_data['metadata']:
            alert_data['metadata'] = json.loads(alert_data['metadata'])
        alerts.append(alert_data)
    
    return {"success": True, "alerts": alerts}

@app.get("/api/dashboard")
async def get_dashboard_data():
    """Get dashboard overview data"""
    conn = sqlite3.connect(obs_stack.db_path)
    cursor = conn.cursor()
    
    # Active alerts
    cursor.execute('SELECT COUNT(*) FROM alerts WHERE resolved = 0')
    active_alerts = cursor.fetchone()[0]
    
    # Services health
    cursor.execute('SELECT service, status FROM service_health')
    services_health = dict(cursor.fetchall())
    
    # Recent anomalies
    since_hour = time.time() - 3600
    cursor.execute('SELECT COUNT(*) FROM anomalies WHERE timestamp >= ? AND is_anomaly = 1', (since_hour,))
    recent_anomalies = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "success": True,
        "dashboard": {
            "active_alerts": active_alerts,
            "services_health": services_health,
            "recent_anomalies": recent_anomalies,
            "monitored_services": len(obs_stack.monitored_services)
        }
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.websocket("/ws/observability")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    obs_stack.active_websockets.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in obs_stack.active_websockets:
            obs_stack.active_websockets.remove(websocket)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8600))
    uvicorn.run(app, host="0.0.0.0", port=port)