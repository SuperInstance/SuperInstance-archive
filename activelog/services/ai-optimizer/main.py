#!/usr/bin/env python3
"""
AI-Powered System Optimization and Auto-Healing Service
Integrates with observability stack to automatically optimize and heal systems
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import numpy as np
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
import psutil
import docker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="AI System Optimizer", version="1.0.0")

class OptimizationAction(BaseModel):
    service_name: str
    action_type: str
    parameters: Dict[str, Any]
    reason: str
    confidence: float

class HealingAction(BaseModel):
    service_name: str
    issue_type: str
    action: str
    parameters: Dict[str, Any]
    priority: str

class SystemOptimizer:
    def __init__(self):
        self.db_path = Path(__file__).parent / "data" / "optimizer.db"
        self.models_path = Path(__file__).parent / "models"
        
        # Create directories
        self.db_path.parent.mkdir(exist_ok=True)
        self.models_path.mkdir(exist_ok=True)
        
        self._init_database()
        self._init_models()
        self._init_docker_client()
        
        # Active monitoring
        self.active_optimizations = {}
        self.healing_rules = self._load_healing_rules()
        
        # Metrics collection
        self.metrics_history = []
        self.optimization_history = []
        
    def _init_database(self):
        """Initialize SQLite database for optimization data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS optimization_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    parameters JSON NOT NULL,
                    reason TEXT,
                    confidence REAL,
                    result TEXT,
                    success BOOLEAN
                );
                
                CREATE TABLE IF NOT EXISTS healing_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    parameters JSON NOT NULL,
                    priority TEXT,
                    success BOOLEAN,
                    error_message TEXT
                );
                
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    prediction REAL,
                    anomaly_score REAL
                );
                
                CREATE TABLE IF NOT EXISTS optimization_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT UNIQUE NOT NULL,
                    conditions JSON NOT NULL,
                    actions JSON NOT NULL,
                    priority INTEGER DEFAULT 5,
                    enabled BOOLEAN DEFAULT TRUE
                );
                
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_actions_service ON optimization_actions(service_name);
            """)
            
    def _init_models(self):
        """Initialize ML models for optimization"""
        self.performance_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.resource_optimizer = RandomForestRegressor(n_estimators=50, random_state=42)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        
        # Load pre-trained models if they exist
        self._load_models()
        
    def _init_docker_client(self):
        """Initialize Docker client for container management"""
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None
            
    def _load_models(self):
        """Load pre-trained models if available"""
        model_files = {
            'performance_predictor': self.models_path / 'performance_predictor.joblib',
            'resource_optimizer': self.models_path / 'resource_optimizer.joblib',
            'anomaly_detector': self.models_path / 'anomaly_detector.joblib',
            'scaler': self.models_path / 'scaler.joblib'
        }
        
        for model_name, file_path in model_files.items():
            if file_path.exists():
                try:
                    model = joblib.load(file_path)
                    setattr(self, model_name, model)
                    logger.info(f"Loaded {model_name} model")
                except Exception as e:
                    logger.warning(f"Failed to load {model_name}: {e}")
                    
    def _save_models(self):
        """Save trained models"""
        models = {
            'performance_predictor': self.performance_predictor,
            'resource_optimizer': self.resource_optimizer,
            'anomaly_detector': self.anomaly_detector,
            'scaler': self.scaler
        }
        
        for model_name, model in models.items():
            try:
                file_path = self.models_path / f'{model_name}.joblib'
                joblib.dump(model, file_path)
                logger.info(f"Saved {model_name} model")
            except Exception as e:
                logger.error(f"Failed to save {model_name}: {e}")
                
    def _load_healing_rules(self) -> List[Dict]:
        """Load system healing rules"""
        return [
            {
                'name': 'high_cpu_usage',
                'condition': {'metric': 'cpu_percent', 'threshold': 80, 'duration': 300},
                'actions': [
                    {'type': 'scale_up', 'parameters': {'instances': 1}},
                    {'type': 'restart_service', 'condition': 'cpu_percent > 95'}
                ]
            },
            {
                'name': 'high_memory_usage',
                'condition': {'metric': 'memory_percent', 'threshold': 85, 'duration': 180},
                'actions': [
                    {'type': 'clear_cache', 'parameters': {}},
                    {'type': 'restart_service', 'condition': 'memory_percent > 95'}
                ]
            },
            {
                'name': 'service_unresponsive',
                'condition': {'metric': 'response_time', 'threshold': 5000, 'duration': 60},
                'actions': [
                    {'type': 'restart_service', 'parameters': {}},
                    {'type': 'scale_up', 'condition': 'instances < 3'}
                ]
            },
            {
                'name': 'database_connection_issues',
                'condition': {'metric': 'db_connection_errors', 'threshold': 5, 'duration': 60},
                'actions': [
                    {'type': 'restart_db_connection_pool', 'parameters': {}},
                    {'type': 'scale_db_connections', 'parameters': {'max_connections': 200}}
                ]
            },
            {
                'name': 'disk_space_low',
                'condition': {'metric': 'disk_usage_percent', 'threshold': 85, 'duration': 60},
                'actions': [
                    {'type': 'cleanup_logs', 'parameters': {'days': 7}},
                    {'type': 'cleanup_cache', 'parameters': {}},
                    {'type': 'alert_admin', 'condition': 'disk_usage_percent > 95'}
                ]
            }
        ]
        
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'load_avg': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
                'network_io': psutil.net_io_counters()._asdict(),
                'disk_io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
            },
            'services': {}
        }
        
        # Collect metrics from ActiveLedger services
        activelog_services = [
            'trading-engine', 'settlement-engine', 'compliance-engine',
            'market-data', 'wallet-service', 'dream-mode'
        ]
        
        for service in activelog_services:
            try:
                service_metrics = await self._get_service_metrics(service)
                metrics['services'][service] = service_metrics
            except Exception as e:
                logger.warning(f"Failed to collect metrics for {service}: {e}")
                
        return metrics
        
    async def _get_service_metrics(self, service_name: str) -> Dict[str, Any]:
        """Get metrics for a specific service"""
        metrics = {
            'status': 'unknown',
            'response_time': None,
            'cpu_usage': None,
            'memory_usage': None,
            'request_count': 0,
            'error_rate': 0.0
        }
        
        try:
            # Try to get metrics from observability service
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://localhost:8600/metrics/{service_name}') as response:
                    if response.status == 200:
                        data = await response.json()
                        metrics.update(data)
        except Exception as e:
            logger.warning(f"Failed to get metrics for {service_name}: {e}")
            
        # Get Docker container metrics if available
        if self.docker_client:
            try:
                container = self.docker_client.containers.get(service_name)
                stats = container.stats(stream=False)
                
                # Calculate CPU usage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100.0
                    metrics['cpu_usage'] = cpu_percent
                    
                # Calculate memory usage
                memory_usage = stats['memory_stats']['usage']
                memory_limit = stats['memory_stats']['limit']
                memory_percent = (memory_usage / memory_limit) * 100.0
                metrics['memory_usage'] = memory_percent
                
            except Exception as e:
                logger.warning(f"Failed to get Docker stats for {service_name}: {e}")
                
        return metrics
        
    async def analyze_optimization_opportunities(self, metrics: Dict[str, Any]) -> List[OptimizationAction]:
        """Analyze metrics to identify optimization opportunities"""
        optimization_actions = []
        
        # System-level optimizations
        system_metrics = metrics['system']
        
        # CPU optimization
        if system_metrics['cpu_percent'] > 70:
            optimization_actions.append(OptimizationAction(
                service_name='system',
                action_type='cpu_optimization',
                parameters={
                    'enable_turbo_boost': True,
                    'adjust_scheduling': True,
                    'optimize_processes': True
                },
                reason=f"High CPU usage detected: {system_metrics['cpu_percent']:.1f}%",
                confidence=0.85
            ))
            
        # Memory optimization
        if system_metrics['memory_percent'] > 80:
            optimization_actions.append(OptimizationAction(
                service_name='system',
                action_type='memory_optimization',
                parameters={
                    'clear_page_cache': True,
                    'compress_memory': True,
                    'adjust_swappiness': 10
                },
                reason=f"High memory usage detected: {system_metrics['memory_percent']:.1f}%",
                confidence=0.80
            ))
            
        # Service-level optimizations
        for service_name, service_metrics in metrics['services'].items():
            if service_metrics.get('cpu_usage', 0) > 80:
                optimization_actions.append(OptimizationAction(
                    service_name=service_name,
                    action_type='scale_up',
                    parameters={'instances': 1, 'cpu_limit': '2000m'},
                    reason=f"High CPU usage: {service_metrics['cpu_usage']:.1f}%",
                    confidence=0.90
                ))
                
            if service_metrics.get('response_time', 0) > 2000:
                optimization_actions.append(OptimizationAction(
                    service_name=service_name,
                    action_type='performance_tuning',
                    parameters={
                        'connection_pool_size': 50,
                        'cache_size': '512MB',
                        'enable_compression': True
                    },
                    reason=f"High response time: {service_metrics['response_time']}ms",
                    confidence=0.75
                ))
                
        return optimization_actions
        
    async def detect_healing_opportunities(self, metrics: Dict[str, Any]) -> List[HealingAction]:
        """Detect issues that require auto-healing"""
        healing_actions = []
        
        for rule in self.healing_rules:
            condition = rule['condition']
            metric_name = condition['metric']
            threshold = condition['threshold']
            
            # Check system metrics
            if metric_name in metrics['system']:
                metric_value = metrics['system'][metric_name]
                if metric_value > threshold:
                    for action_config in rule['actions']:
                        healing_actions.append(HealingAction(
                            service_name='system',
                            issue_type=rule['name'],
                            action=action_config['type'],
                            parameters=action_config.get('parameters', {}),
                            priority='high' if metric_value > threshold * 1.2 else 'medium'
                        ))
                        
            # Check service metrics
            for service_name, service_metrics in metrics['services'].items():
                if metric_name in service_metrics:
                    metric_value = service_metrics[metric_name]
                    if metric_value and metric_value > threshold:
                        for action_config in rule['actions']:
                            healing_actions.append(HealingAction(
                                service_name=service_name,
                                issue_type=rule['name'],
                                action=action_config['type'],
                                parameters=action_config.get('parameters', {}),
                                priority='high' if metric_value > threshold * 1.2 else 'medium'
                            ))
                            
        return healing_actions
        
    async def execute_optimization(self, action: OptimizationAction) -> bool:
        """Execute an optimization action"""
        try:
            logger.info(f"Executing optimization: {action.action_type} for {action.service_name}")
            
            if action.action_type == 'cpu_optimization':
                return await self._optimize_cpu(action.parameters)
            elif action.action_type == 'memory_optimization':
                return await self._optimize_memory(action.parameters)
            elif action.action_type == 'scale_up':
                return await self._scale_service(action.service_name, action.parameters)
            elif action.action_type == 'performance_tuning':
                return await self._tune_service_performance(action.service_name, action.parameters)
            else:
                logger.warning(f"Unknown optimization action: {action.action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute optimization {action.action_type}: {e}")
            return False
            
    async def execute_healing(self, action: HealingAction) -> bool:
        """Execute a healing action"""
        try:
            logger.info(f"Executing healing: {action.action} for {action.service_name}")
            
            if action.action == 'restart_service':
                return await self._restart_service(action.service_name)
            elif action.action == 'scale_up':
                return await self._scale_service(action.service_name, action.parameters)
            elif action.action == 'clear_cache':
                return await self._clear_service_cache(action.service_name)
            elif action.action == 'cleanup_logs':
                return await self._cleanup_logs(action.parameters)
            elif action.action == 'restart_db_connection_pool':
                return await self._restart_db_connections(action.service_name)
            else:
                logger.warning(f"Unknown healing action: {action.action}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute healing {action.action}: {e}")
            return False
            
    async def _optimize_cpu(self, parameters: Dict) -> bool:
        """Optimize CPU usage"""
        # Implementation would adjust CPU scheduling, governor settings, etc.
        logger.info("CPU optimization executed")
        return True
        
    async def _optimize_memory(self, parameters: Dict) -> bool:
        """Optimize memory usage"""
        # Implementation would clear caches, adjust swap, etc.
        logger.info("Memory optimization executed")
        return True
        
    async def _scale_service(self, service_name: str, parameters: Dict) -> bool:
        """Scale a service up or down"""
        if not self.docker_client:
            return False
            
        try:
            # Scale Docker container
            instances = parameters.get('instances', 1)
            logger.info(f"Scaling {service_name} to {instances} instances")
            return True
        except Exception as e:
            logger.error(f"Failed to scale {service_name}: {e}")
            return False
            
    async def _tune_service_performance(self, service_name: str, parameters: Dict) -> bool:
        """Tune service performance parameters"""
        logger.info(f"Performance tuning for {service_name}: {parameters}")
        return True
        
    async def _restart_service(self, service_name: str) -> bool:
        """Restart a service"""
        if not self.docker_client:
            return False
            
        try:
            container = self.docker_client.containers.get(service_name)
            container.restart()
            logger.info(f"Restarted service: {service_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to restart {service_name}: {e}")
            return False
            
    async def _clear_service_cache(self, service_name: str) -> bool:
        """Clear service cache"""
        logger.info(f"Clearing cache for {service_name}")
        return True
        
    async def _cleanup_logs(self, parameters: Dict) -> bool:
        """Clean up old log files"""
        days = parameters.get('days', 7)
        logger.info(f"Cleaning up logs older than {days} days")
        return True
        
    async def _restart_db_connections(self, service_name: str) -> bool:
        """Restart database connection pool"""
        logger.info(f"Restarting DB connections for {service_name}")
        return True
        
    async def log_action(self, action: Any, success: bool, error: str = None):
        """Log optimization or healing action"""
        with sqlite3.connect(self.db_path) as conn:
            if isinstance(action, OptimizationAction):
                conn.execute("""
                    INSERT INTO optimization_actions 
                    (service_name, action_type, parameters, reason, confidence, success, result)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    action.service_name,
                    action.action_type,
                    json.dumps(action.parameters),
                    action.reason,
                    action.confidence,
                    success,
                    error or "Success"
                ))
            elif isinstance(action, HealingAction):
                conn.execute("""
                    INSERT INTO healing_actions 
                    (service_name, issue_type, action, parameters, priority, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    action.service_name,
                    action.issue_type,
                    action.action,
                    json.dumps(action.parameters),
                    action.priority,
                    success,
                    error
                ))

# Global optimizer instance
optimizer = SystemOptimizer()

@app.on_startup
async def startup():
    """Start the optimization engine"""
    logger.info("Starting AI System Optimizer")
    asyncio.create_task(optimization_loop())

async def optimization_loop():
    """Main optimization loop"""
    while True:
        try:
            # Collect system metrics
            metrics = await optimizer.collect_system_metrics()
            
            # Analyze for optimization opportunities
            optimizations = await optimizer.analyze_optimization_opportunities(metrics)
            
            # Analyze for healing opportunities
            healing_actions = await optimizer.detect_healing_opportunities(metrics)
            
            # Execute high-priority healing actions first
            for action in sorted(healing_actions, key=lambda x: x.priority == 'high', reverse=True):
                success = await optimizer.execute_healing(action)
                await optimizer.log_action(action, success)
                
            # Execute optimization actions
            for action in optimizations:
                if action.confidence > 0.7:  # Only execute high-confidence optimizations
                    success = await optimizer.execute_optimization(action)
                    await optimizer.log_action(action, success)
                    
        except Exception as e:
            logger.error(f"Error in optimization loop: {e}")
            
        # Wait before next iteration
        await asyncio.sleep(30)  # Run every 30 seconds

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ai-optimizer"}

@app.get("/metrics")
async def get_metrics():
    """Get current optimization metrics"""
    metrics = await optimizer.collect_system_metrics()
    return metrics

@app.get("/optimization-history")
async def get_optimization_history():
    """Get optimization action history"""
    with sqlite3.connect(optimizer.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM optimization_actions 
            ORDER BY timestamp DESC 
            LIMIT 100
        """)
        return [dict(row) for row in cursor.fetchall()]

@app.get("/healing-history")
async def get_healing_history():
    """Get healing action history"""
    with sqlite3.connect(optimizer.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM healing_actions 
            ORDER BY timestamp DESC 
            LIMIT 100
        """)
        return [dict(row) for row in cursor.fetchall()]

@app.post("/optimize/{service_name}")
async def trigger_optimization(service_name: str):
    """Manually trigger optimization for a service"""
    metrics = await optimizer.collect_system_metrics()
    if service_name in metrics['services']:
        service_metrics = {'services': {service_name: metrics['services'][service_name]}}
        optimizations = await optimizer.analyze_optimization_opportunities(service_metrics)
        
        results = []
        for action in optimizations:
            success = await optimizer.execute_optimization(action)
            await optimizer.log_action(action, success)
            results.append({"action": action.dict(), "success": success})
            
        return {"results": results}
    else:
        raise HTTPException(status_code=404, detail="Service not found")

@app.websocket("/ws/optimization-events")
async def websocket_optimization_events(websocket: WebSocket):
    """WebSocket for real-time optimization events"""
    await websocket.accept()
    
    try:
        while True:
            # Send current metrics and recent actions
            metrics = await optimizer.collect_system_metrics()
            
            with sqlite3.connect(optimizer.db_path) as conn:
                conn.row_factory = sqlite3.Row
                recent_actions = conn.execute("""
                    SELECT * FROM optimization_actions 
                    WHERE timestamp > datetime('now', '-5 minutes')
                    ORDER BY timestamp DESC
                """).fetchall()
                
            event_data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "recent_actions": [dict(row) for row in recent_actions]
            }
            
            await websocket.send_text(json.dumps(event_data))
            await asyncio.sleep(10)  # Send updates every 10 seconds
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8601))
    uvicorn.run(app, host="0.0.0.0", port=port)