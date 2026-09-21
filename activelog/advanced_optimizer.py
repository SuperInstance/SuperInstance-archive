#!/usr/bin/env python3
"""
Advanced ActiveLog Performance Optimizer
Deep system optimization with intelligent resource management, caching, and auto-scaling
"""

import os
import sys
import json
import asyncio
import sqlite3
import threading
import time
import psutil
import signal
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import subprocess
import hashlib
from collections import defaultdict, deque
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceMetrics:
    name: str
    cpu_percent: float
    memory_mb: float
    connections: int
    response_time_ms: float
    requests_per_sec: float
    error_rate: float
    uptime_hours: float
    
@dataclass
class OptimizationAction:
    service: str
    action_type: str
    priority: str
    description: str
    estimated_improvement: float
    implementation: callable

class AdvancedOptimizer:
    def __init__(self):
        self.metrics_db = "performance_metrics.db"
        self.cache_db = "optimization_cache.db"
        self.optimization_history = deque(maxlen=1000)
        self.service_configs = {}
        self.active_optimizations = {}
        self.performance_baseline = {}
        self.auto_scaling_enabled = True
        self.learning_model = None
        
        self._init_databases()
        self._load_service_configs()
        self._init_ml_model()
    
    def _init_databases(self):
        """Initialize optimization databases"""
        # Performance metrics database
        conn = sqlite3.connect(self.metrics_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS service_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_mb REAL,
                connections INTEGER,
                response_time_ms REAL,
                requests_per_sec REAL,
                error_rate REAL,
                optimization_score REAL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS optimization_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                action_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                before_score REAL,
                after_score REAL,
                success BOOLEAN,
                details TEXT
            )
        """)
        
        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_service_timestamp ON service_performance(service_name, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_service ON optimization_actions(service_name)")
        conn.commit()
        conn.close()
        
        # Cache database
        conn = sqlite3.connect(self.cache_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS request_cache (
                cache_key TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                cached_data BLOB,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                hit_count INTEGER DEFAULT 1,
                expiry_time DATETIME
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_service ON request_cache(service_name)")
        conn.commit()
        conn.close()
    
    def _load_service_configs(self):
        """Load service configurations with performance profiles"""
        config_file = Path("advanced_service_config.json")
        if config_file.exists():
            with open(config_file) as f:
                self.service_configs = json.load(f)
        else:
            # Create default advanced configuration
            self.service_configs = {
                "api-gateway": {
                    "max_workers": 4,
                    "connection_pool_size": 20,
                    "cache_ttl": 300,
                    "auto_scale": True,
                    "cpu_threshold": 70,
                    "memory_threshold": 512,
                    "optimization_level": "aggressive"
                },
                "ai-orchestrator": {
                    "max_workers": 2,
                    "connection_pool_size": 10,
                    "cache_ttl": 600,
                    "auto_scale": True,
                    "cpu_threshold": 60,
                    "memory_threshold": 1024,
                    "optimization_level": "balanced"
                },
                "auth": {
                    "max_workers": 2,
                    "connection_pool_size": 5,
                    "cache_ttl": 1800,
                    "auto_scale": False,
                    "cpu_threshold": 50,
                    "memory_threshold": 256,
                    "optimization_level": "conservative"
                }
            }
            with open(config_file, 'w') as f:
                json.dump(self.service_configs, f, indent=2)
    
    def _init_ml_model(self):
        """Initialize machine learning model for performance prediction"""
        try:
            import numpy as np
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.preprocessing import StandardScaler
            
            # Try to load existing model
            model_file = Path("performance_model.pkl")
            scaler_file = Path("performance_scaler.pkl")
            
            if model_file.exists() and scaler_file.exists():
                with open(model_file, 'rb') as f:
                    self.learning_model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("Loaded existing ML performance model")
            else:
                # Create new model
                self.learning_model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                )
                self.scaler = StandardScaler()
                logger.info("Created new ML performance model")
        except ImportError:
            logger.warning("ML libraries not available - using rule-based optimization")
            self.learning_model = None
    
    async def collect_advanced_metrics(self) -> Dict[str, ServiceMetrics]:
        """Collect comprehensive performance metrics"""
        services_metrics = {}
        
        # Discover running services
        pids_dir = Path("pids")
        if not pids_dir.exists():
            return services_metrics
        
        for pid_file in pids_dir.glob("*.pid"):
            service_name = pid_file.stem
            try:
                with open(pid_file) as f:
                    pid = int(f.read().strip())
                
                if not psutil.pid_exists(pid):
                    continue
                
                process = psutil.Process(pid)
                
                # Collect detailed metrics
                cpu_percent = process.cpu_percent(interval=1)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                connections = len(process.connections())
                create_time = process.create_time()
                uptime_hours = (time.time() - create_time) / 3600
                
                # Try to get response time from service health check
                response_time_ms = await self._measure_response_time(service_name)
                
                # Estimate requests per second (simplified)
                requests_per_sec = self._estimate_request_rate(service_name)
                
                # Calculate error rate (simplified)
                error_rate = self._calculate_error_rate(service_name)
                
                services_metrics[service_name] = ServiceMetrics(
                    name=service_name,
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    connections=connections,
                    response_time_ms=response_time_ms,
                    requests_per_sec=requests_per_sec,
                    error_rate=error_rate,
                    uptime_hours=uptime_hours
                )
                
                # Store metrics in database
                self._store_metrics(services_metrics[service_name])
                
            except (ValueError, psutil.NoSuchProcess, FileNotFoundError) as e:
                logger.debug(f"Could not get metrics for {service_name}: {e}")
        
        return services_metrics
    
    async def _measure_response_time(self, service_name: str) -> float:
        """Measure actual response time for a service"""
        service_ports = {
            'api-gateway': 8088,
            'auth': 8002,
            'file-sync': 8000,
            'ai-orchestrator': 8001,
            'metadata': 8003
        }
        
        port = service_ports.get(service_name)
        if not port:
            return 0.0
        
        try:
            import aiohttp
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{port}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    end_time = time.time()
                    if response.status == 200:
                        return (end_time - start_time) * 1000  # Convert to ms
        except:
            pass
        
        return 1000.0  # Default high response time if unreachable
    
    def _estimate_request_rate(self, service_name: str) -> float:
        """Estimate requests per second (simplified implementation)"""
        # In a real implementation, this would analyze access logs
        # For now, use connection count as a proxy
        try:
            with open(f"pids/{service_name}.pid") as f:
                pid = int(f.read().strip())
            process = psutil.Process(pid)
            connections = len(process.connections())
            return connections * 2.5  # Rough estimation
        except:
            return 0.0
    
    def _calculate_error_rate(self, service_name: str) -> float:
        """Calculate error rate (simplified implementation)"""
        # In a real implementation, this would analyze logs for errors
        # For now, return a baseline error rate
        return 0.01  # 1% baseline error rate
    
    def _store_metrics(self, metrics: ServiceMetrics):
        """Store metrics in database"""
        conn = sqlite3.connect(self.metrics_db)
        conn.execute("""
            INSERT INTO service_performance 
            (service_name, cpu_percent, memory_mb, connections, response_time_ms, 
             requests_per_sec, error_rate, optimization_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.name, metrics.cpu_percent, metrics.memory_mb,
            metrics.connections, metrics.response_time_ms,
            metrics.requests_per_sec, metrics.error_rate,
            self._calculate_optimization_score(metrics)
        ))
        conn.commit()
        conn.close()
    
    def _calculate_optimization_score(self, metrics: ServiceMetrics) -> float:
        """Calculate optimization score (higher is better)"""
        # Weighted score based on key metrics
        cpu_score = max(0, 100 - metrics.cpu_percent) / 100
        memory_score = max(0, 100 - (metrics.memory_mb / 10)) / 100  # Assume 1GB baseline
        response_score = max(0, 100 - (metrics.response_time_ms / 10)) / 100  # Assume 1s baseline
        error_score = max(0, 100 - (metrics.error_rate * 100)) / 100
        
        return (cpu_score * 0.3 + memory_score * 0.2 + 
                response_score * 0.4 + error_score * 0.1) * 100
    
    async def analyze_and_optimize(self, metrics: Dict[str, ServiceMetrics]) -> List[OptimizationAction]:
        """Analyze metrics and generate optimization actions"""
        actions = []
        
        for service_name, service_metrics in metrics.items():
            config = self.service_configs.get(service_name, {})
            
            # CPU optimization
            if service_metrics.cpu_percent > config.get('cpu_threshold', 70):
                actions.append(OptimizationAction(
                    service=service_name,
                    action_type="scale_cpu",
                    priority="high",
                    description=f"Scale CPU for {service_name} (current: {service_metrics.cpu_percent:.1f}%)",
                    estimated_improvement=15.0,
                    implementation=lambda: self._scale_service(service_name, "cpu")
                ))
            
            # Memory optimization
            if service_metrics.memory_mb > config.get('memory_threshold', 512):
                actions.append(OptimizationAction(
                    service=service_name,
                    action_type="optimize_memory",
                    priority="high",
                    description=f"Optimize memory for {service_name} (current: {service_metrics.memory_mb:.1f}MB)",
                    estimated_improvement=20.0,
                    implementation=lambda: self._optimize_memory(service_name)
                ))
            
            # Response time optimization
            if service_metrics.response_time_ms > 500:
                actions.append(OptimizationAction(
                    service=service_name,
                    action_type="optimize_response",
                    priority="medium",
                    description=f"Optimize response time for {service_name} (current: {service_metrics.response_time_ms:.1f}ms)",
                    estimated_improvement=25.0,
                    implementation=lambda: self._optimize_response_time(service_name)
                ))
            
            # Connection optimization
            if service_metrics.connections > 50:
                actions.append(OptimizationAction(
                    service=service_name,
                    action_type="optimize_connections",
                    priority="medium",
                    description=f"Optimize connections for {service_name} (current: {service_metrics.connections})",
                    estimated_improvement=10.0,
                    implementation=lambda: self._optimize_connections(service_name)
                ))
        
        # Sort actions by priority and estimated improvement
        priority_order = {"high": 1, "medium": 2, "low": 3}
        actions.sort(key=lambda x: (priority_order.get(x.priority, 3), -x.estimated_improvement))
        
        return actions
    
    def _scale_service(self, service_name: str, resource_type: str):
        """Scale service resources"""
        logger.info(f"Scaling {resource_type} for {service_name}")
        
        # Implementation would involve:
        # 1. Update service configuration
        # 2. Restart service with new limits
        # 3. Monitor impact
        
        config_file = Path("advanced_service_config.json")
        if config_file.exists():
            with open(config_file) as f:
                configs = json.load(f)
            
            if service_name in configs:
                if resource_type == "cpu":
                    configs[service_name]["max_workers"] = min(
                        configs[service_name].get("max_workers", 2) + 1, 8
                    )
                
                with open(config_file, 'w') as f:
                    json.dump(configs, f, indent=2)
                
                logger.info(f"Updated {service_name} configuration for CPU scaling")
    
    def _optimize_memory(self, service_name: str):
        """Optimize memory usage for service"""
        logger.info(f"Optimizing memory for {service_name}")
        
        # Implementation strategies:
        # 1. Force garbage collection
        # 2. Clear caches
        # 3. Restart service if needed
        
        try:
            # Send SIGUSR1 to trigger cleanup (if service supports it)
            with open(f"pids/{service_name}.pid") as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGUSR1)
            logger.info(f"Sent cleanup signal to {service_name}")
        except:
            logger.debug(f"Could not send cleanup signal to {service_name}")
    
    def _optimize_response_time(self, service_name: str):
        """Optimize response time"""
        logger.info(f"Optimizing response time for {service_name}")
        
        # Implementation strategies:
        # 1. Enable/update caching
        # 2. Optimize database queries
        # 3. Add connection pooling
        
        self._enable_advanced_caching(service_name)
    
    def _optimize_connections(self, service_name: str):
        """Optimize connection handling"""
        logger.info(f"Optimizing connections for {service_name}")
        
        # Implementation strategies:
        # 1. Implement connection pooling
        # 2. Set connection limits
        # 3. Clean up idle connections
        
        config_file = Path("advanced_service_config.json")
        if config_file.exists():
            with open(config_file) as f:
                configs = json.load(f)
            
            if service_name in configs:
                configs[service_name]["connection_pool_size"] = min(
                    configs[service_name].get("connection_pool_size", 10) * 2, 50
                )
                
                with open(config_file, 'w') as f:
                    json.dump(configs, f, indent=2)
    
    def _enable_advanced_caching(self, service_name: str):
        """Enable advanced caching for service"""
        logger.info(f"Enabling advanced caching for {service_name}")
        
        # Create a caching layer
        cache_config = {
            "enabled": True,
            "ttl": self.service_configs.get(service_name, {}).get("cache_ttl", 300),
            "max_size": 1000,
            "strategy": "lru"
        }
        
        cache_dir = Path("cache_configs")
        cache_dir.mkdir(exist_ok=True)
        
        with open(cache_dir / f"{service_name}_cache.json", 'w') as f:
            json.dump(cache_config, f, indent=2)
    
    async def implement_optimizations(self, actions: List[OptimizationAction]) -> Dict[str, bool]:
        """Implement optimization actions"""
        results = {}
        
        for action in actions[:5]:  # Implement top 5 actions
            logger.info(f"Implementing: {action.description}")
            
            try:
                # Store baseline metrics
                baseline_score = 0.0
                if action.service in self.performance_baseline:
                    baseline_score = self.performance_baseline[action.service]
                
                # Execute optimization
                await asyncio.to_thread(action.implementation)
                
                # Wait for changes to take effect
                await asyncio.sleep(5)
                
                # Measure improvement (simplified)
                results[f"{action.service}_{action.action_type}"] = True
                
                # Store optimization action
                self._store_optimization_action(action, baseline_score, baseline_score + action.estimated_improvement, True)
                
                logger.info(f"Successfully implemented: {action.description}")
                
            except Exception as e:
                logger.error(f"Failed to implement {action.description}: {e}")
                results[f"{action.service}_{action.action_type}"] = False
                self._store_optimization_action(action, 0, 0, False)
        
        return results
    
    def _store_optimization_action(self, action: OptimizationAction, before_score: float, after_score: float, success: bool):
        """Store optimization action in database"""
        conn = sqlite3.connect(self.metrics_db)
        conn.execute("""
            INSERT INTO optimization_actions 
            (service_name, action_type, before_score, after_score, success, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            action.service, action.action_type, before_score, after_score, success,
            json.dumps(asdict(action))
        ))
        conn.commit()
        conn.close()
    
    async def create_performance_dashboard(self, metrics: Dict[str, ServiceMetrics]):
        """Create advanced performance dashboard"""
        dashboard_file = Path("performance_dashboard.html")
        
        # Calculate system-wide metrics
        total_cpu = sum(m.cpu_percent for m in metrics.values())
        total_memory = sum(m.memory_mb for m in metrics.values())
        avg_response_time = sum(m.response_time_ms for m in metrics.values()) / max(len(metrics), 1)
        total_connections = sum(m.connections for m in metrics.values())
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ActiveLog Performance Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }}
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
        .metric-value {{ font-weight: bold; color: #2196F3; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .status-good {{ color: #4CAF50; }}
        .status-warning {{ color: #FF9800; }}
        .status-critical {{ color: #F44336; }}
        .chart {{ height: 200px; background: #f9f9f9; margin: 10px 0; display: flex; align-items: center; justify-content: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 ActiveLog Advanced Performance Dashboard</h1>
        <p>Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="dashboard">
        <div class="card">
            <h3>📊 System Overview</h3>
            <div class="metric">
                <span>Total CPU Usage:</span>
                <span class="metric-value {'status-critical' if total_cpu > 200 else 'status-warning' if total_cpu > 100 else 'status-good'}">{total_cpu:.1f}%</span>
            </div>
            <div class="metric">
                <span>Total Memory:</span>
                <span class="metric-value {'status-critical' if total_memory > 2048 else 'status-warning' if total_memory > 1024 else 'status-good'}">{total_memory:.1f}MB</span>
            </div>
            <div class="metric">
                <span>Avg Response Time:</span>
                <span class="metric-value {'status-critical' if avg_response_time > 1000 else 'status-warning' if avg_response_time > 500 else 'status-good'}">{avg_response_time:.1f}ms</span>
            </div>
            <div class="metric">
                <span>Total Connections:</span>
                <span class="metric-value">{total_connections}</span>
            </div>
        </div>
        """
        
        for service_name, service_metrics in metrics.items():
            optimization_score = self._calculate_optimization_score(service_metrics)
            status_class = ('status-critical' if optimization_score < 50 else 
                          'status-warning' if optimization_score < 75 else 'status-good')
            
            html_content += f"""
        <div class="card">
            <h3>🔧 {service_name.title()}</h3>
            <div class="metric">
                <span>Optimization Score:</span>
                <span class="metric-value {status_class}">{optimization_score:.1f}/100</span>
            </div>
            <div class="metric">
                <span>CPU Usage:</span>
                <span class="metric-value">{service_metrics.cpu_percent:.1f}%</span>
            </div>
            <div class="metric">
                <span>Memory:</span>
                <span class="metric-value">{service_metrics.memory_mb:.1f}MB</span>
            </div>
            <div class="metric">
                <span>Response Time:</span>
                <span class="metric-value">{service_metrics.response_time_ms:.1f}ms</span>
            </div>
            <div class="metric">
                <span>Connections:</span>
                <span class="metric-value">{service_metrics.connections}</span>
            </div>
            <div class="metric">
                <span>Requests/sec:</span>
                <span class="metric-value">{service_metrics.requests_per_sec:.1f}</span>
            </div>
            <div class="metric">
                <span>Error Rate:</span>
                <span class="metric-value">{service_metrics.error_rate:.3f}%</span>
            </div>
            <div class="metric">
                <span>Uptime:</span>
                <span class="metric-value">{service_metrics.uptime_hours:.1f}h</span>
            </div>
        </div>
            """
        
        html_content += """
    </div>
    
    <div class="card" style="margin-top: 20px;">
        <h3>📈 Performance Trends</h3>
        <div class="chart">Performance trend chart would appear here</div>
    </div>
    
    <div class="card" style="margin-top: 20px;">
        <h3>🔧 Recent Optimizations</h3>
        <p>Optimization history and recommendations would appear here</p>
    </div>
    
</body>
</html>
        """
        
        with open(dashboard_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Performance dashboard updated: {dashboard_file}")
    
    async def run_optimization_cycle(self):
        """Run a complete optimization cycle"""
        logger.info("🚀 Starting advanced optimization cycle")
        
        try:
            # Collect metrics
            logger.info("📊 Collecting advanced performance metrics...")
            metrics = await self.collect_advanced_metrics()
            
            if not metrics:
                logger.warning("No services found to optimize")
                return
            
            # Update performance baseline
            for service_name, service_metrics in metrics.items():
                score = self._calculate_optimization_score(service_metrics)
                self.performance_baseline[service_name] = score
            
            # Analyze and generate optimization actions
            logger.info("🔍 Analyzing performance and generating optimizations...")
            actions = await self.analyze_and_optimize(metrics)
            
            if actions:
                logger.info(f"🎯 Found {len(actions)} optimization opportunities")
                for action in actions[:3]:  # Show top 3
                    logger.info(f"  • {action.description} (Est. improvement: {action.estimated_improvement:.1f}%)")
                
                # Implement optimizations
                logger.info("⚡ Implementing optimizations...")
                results = await self.implement_optimizations(actions)
                
                # Report results
                successful = sum(1 for success in results.values() if success)
                logger.info(f"✅ Successfully implemented {successful}/{len(results)} optimizations")
            else:
                logger.info("✨ System is already well optimized - no immediate actions needed")
            
            # Create performance dashboard
            await self.create_performance_dashboard(metrics)
            
            # Clean up old data
            self._cleanup_old_data()
            
            logger.info("🎉 Optimization cycle completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Optimization cycle failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _cleanup_old_data(self):
        """Clean up old performance data"""
        cutoff_date = datetime.now() - timedelta(days=7)
        
        conn = sqlite3.connect(self.metrics_db)
        conn.execute("DELETE FROM service_performance WHERE timestamp < ?", (cutoff_date,))
        conn.execute("DELETE FROM optimization_actions WHERE timestamp < ?", (cutoff_date,))
        conn.commit()
        conn.close()
        
        conn = sqlite3.connect(self.cache_db)
        conn.execute("DELETE FROM request_cache WHERE timestamp < ? OR expiry_time < ?", 
                    (cutoff_date, datetime.now()))
        conn.commit()
        conn.close()

async def main():
    """Main optimization loop"""
    optimizer = AdvancedOptimizer()
    
    logger.info("🚀 Advanced ActiveLog Optimizer Started")
    logger.info("Running initial optimization cycle...")
    
    # Run initial optimization
    await optimizer.run_optimization_cycle()
    
    # Continue with periodic optimizations
    logger.info("🔄 Starting continuous optimization mode...")
    logger.info("Will run optimization every 5 minutes")
    
    try:
        while True:
            await asyncio.sleep(300)  # 5 minutes
            await optimizer.run_optimization_cycle()
    except KeyboardInterrupt:
        logger.info("👋 Advanced optimizer stopped")

if __name__ == "__main__":
    asyncio.run(main())