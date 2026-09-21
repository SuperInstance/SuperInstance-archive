#!/usr/bin/env python3
"""
ActiveLog Performance Monitor
Real-time monitoring and optimization suggestions for the ActiveLog system
"""

import os
import sys
import time
import json
import psutil
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self):
        self.metrics_history = []
        self.alerts = []
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'response_time_ms': 1000.0
        }
        self.services = self._discover_services()
        
    def _discover_services(self) -> Dict[str, Dict]:
        """Discover running ActiveLog services"""
        services = {}
        
        # Check PID files
        pids_dir = Path("pids")
        if pids_dir.exists():
            for pid_file in pids_dir.glob("*.pid"):
                service_name = pid_file.stem
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                    
                    if psutil.pid_exists(pid):
                        process = psutil.Process(pid)
                        services[service_name] = {
                            'pid': pid,
                            'process': process,
                            'start_time': datetime.fromtimestamp(process.create_time())
                        }
                except (ValueError, psutil.NoSuchProcess, FileNotFoundError):
                    pass
        
        return services
    
    def collect_system_metrics(self) -> Dict:
        """Collect system-wide metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_mb': memory.used / 1024 / 1024,
            'memory_total_mb': memory.total / 1024 / 1024,
            'disk_usage_percent': disk.percent,
            'disk_free_gb': disk.free / 1024 / 1024 / 1024,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
        
        return metrics
    
    def collect_service_metrics(self) -> Dict[str, Dict]:
        """Collect per-service metrics"""
        service_metrics = {}
        
        for service_name, service_info in self.services.items():
            try:
                process = service_info['process']
                
                # Update process info
                process_info = process.as_dict(attrs=[
                    'pid', 'name', 'cpu_percent', 'memory_percent',
                    'memory_info', 'connections', 'num_threads'
                ])
                
                metrics = {
                    'pid': process_info['pid'],
                    'cpu_percent': process_info['cpu_percent'],
                    'memory_percent': process_info['memory_percent'],
                    'memory_mb': process_info['memory_info'].rss / 1024 / 1024,
                    'num_threads': process_info['num_threads'],
                    'connections': len(process_info['connections']),
                    'uptime_hours': (datetime.now() - service_info['start_time']).total_seconds() / 3600
                }
                
                service_metrics[service_name] = metrics
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Service process no longer exists
                logger.warning(f"Service {service_name} is no longer running")
                continue
        
        return service_metrics
    
    def check_performance_issues(self, system_metrics: Dict, service_metrics: Dict[str, Dict]):
        """Check for performance issues and generate alerts"""
        alerts = []
        
        # System-level checks
        if system_metrics['cpu_percent'] > self.thresholds['cpu_percent']:
            alerts.append({
                'level': 'WARNING',
                'type': 'HIGH_CPU',
                'message': f"High system CPU usage: {system_metrics['cpu_percent']:.1f}%",
                'timestamp': system_metrics['timestamp'],
                'recommendation': "Consider scaling services or optimizing CPU-intensive operations"
            })
        
        if system_metrics['memory_percent'] > self.thresholds['memory_percent']:
            alerts.append({
                'level': 'WARNING',
                'type': 'HIGH_MEMORY',
                'message': f"High memory usage: {system_metrics['memory_percent']:.1f}%",
                'timestamp': system_metrics['timestamp'],
                'recommendation': "Check for memory leaks or consider adding more RAM"
            })
        
        if system_metrics['disk_usage_percent'] > self.thresholds['disk_usage_percent']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'HIGH_DISK',
                'message': f"High disk usage: {system_metrics['disk_usage_percent']:.1f}%",
                'timestamp': system_metrics['timestamp'],
                'recommendation': "Clean up old files, logs, or expand storage"
            })
        
        # Service-level checks
        for service_name, metrics in service_metrics.items():
            if metrics['cpu_percent'] > 50.0:
                alerts.append({
                    'level': 'INFO',
                    'type': 'SERVICE_HIGH_CPU',
                    'service': service_name,
                    'message': f"{service_name} high CPU: {metrics['cpu_percent']:.1f}%",
                    'timestamp': system_metrics['timestamp'],
                    'recommendation': f"Optimize {service_name} or scale horizontally"
                })
            
            if metrics['memory_mb'] > 500:
                alerts.append({
                    'level': 'INFO',
                    'type': 'SERVICE_HIGH_MEMORY',
                    'service': service_name,
                    'message': f"{service_name} high memory: {metrics['memory_mb']:.1f}MB",
                    'timestamp': system_metrics['timestamp'],
                    'recommendation': f"Check {service_name} for memory leaks"
                })
        
        return alerts
    
    def generate_optimization_suggestions(self, system_metrics: Dict, service_metrics: Dict[str, Dict]) -> List[str]:
        """Generate performance optimization suggestions"""
        suggestions = []
        
        # Service count analysis
        service_count = len(service_metrics)
        if service_count > 20:
            suggestions.append(
                f"Consider consolidating services - currently running {service_count} services"
            )
        
        # Memory usage analysis
        total_service_memory = sum(m['memory_mb'] for m in service_metrics.values())
        if total_service_memory > 2048:  # 2GB
            suggestions.append(
                f"High total service memory usage: {total_service_memory:.1f}MB - optimize or add RAM"
            )
        
        # Connection analysis
        total_connections = sum(m['connections'] for m in service_metrics.values())
        if total_connections > 100:
            suggestions.append(
                f"High connection count: {total_connections} - implement connection pooling"
            )
        
        # Thread analysis
        high_thread_services = [
            name for name, m in service_metrics.items() if m['num_threads'] > 10
        ]
        if high_thread_services:
            suggestions.append(
                f"Services with many threads: {', '.join(high_thread_services)} - review thread usage"
            )
        
        # CPU usage patterns
        if system_metrics['cpu_percent'] > 60:
            cpu_intensive_services = [
                name for name, m in service_metrics.items() if m['cpu_percent'] > 20
            ]
            if cpu_intensive_services:
                suggestions.append(
                    f"CPU intensive services: {', '.join(cpu_intensive_services)} - optimize algorithms"
                )
        
        return suggestions
    
    async def health_check_services(self) -> Dict[str, bool]:
        """Check health of services via HTTP endpoints"""
        health_status = {}
        
        # Common service ports
        service_ports = {
            'api-gateway': 8088,
            'auth': 8002,
            'file-sync': 8000,
            'ai-orchestrator': 8001,
            'metadata': 8003
        }
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                for service_name, port in service_ports.items():
                    try:
                        async with session.get(
                            f"http://localhost:{port}/health",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            health_status[service_name] = response.status == 200
                    except:
                        health_status[service_name] = False
        except ImportError:
            # aiohttp not available, use basic check
            import socket
            for service_name, port in service_ports.items():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                health_status[service_name] = result == 0
                sock.close()
        
        return health_status
    
    def save_metrics(self, metrics: Dict):
        """Save metrics to file"""
        metrics_file = Path("performance_metrics.jsonl")
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(metrics) + '\n')
    
    def print_dashboard(self, system_metrics: Dict, service_metrics: Dict[str, Dict], 
                       health_status: Dict[str, bool], suggestions: List[str]):
        """Print performance dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🚀 ActiveLog Performance Monitor")
        print("=" * 60)
        print(f"Timestamp: {system_metrics['timestamp']}")
        print()
        
        # System metrics
        print("📊 System Metrics:")
        print(f"  CPU Usage:    {system_metrics['cpu_percent']:6.1f}%")
        print(f"  Memory Usage: {system_metrics['memory_percent']:6.1f}% "
              f"({system_metrics['memory_used_mb']:.0f}MB / {system_metrics['memory_total_mb']:.0f}MB)")
        print(f"  Disk Usage:   {system_metrics['disk_usage_percent']:6.1f}% "
              f"({system_metrics['disk_free_gb']:.1f}GB free)")
        print(f"  Load Average: {system_metrics['load_average'][0]:.2f}, "
              f"{system_metrics['load_average'][1]:.2f}, {system_metrics['load_average'][2]:.2f}")
        print()
        
        # Service health
        print("🏥 Service Health:")
        for service_name, is_healthy in health_status.items():
            status = "✅ Healthy" if is_healthy else "❌ Unhealthy"
            print(f"  {service_name:15} {status}")
        print()
        
        # Service metrics
        if service_metrics:
            print("🔧 Service Performance:")
            print(f"{'Service':<15} {'CPU%':>6} {'Mem(MB)':>8} {'Threads':>8} {'Conn':>6} {'Uptime(h)':>10}")
            print("-" * 70)
            for service_name, metrics in service_metrics.items():
                print(f"{service_name:<15} "
                      f"{metrics['cpu_percent']:6.1f} "
                      f"{metrics['memory_mb']:8.0f} "
                      f"{metrics['num_threads']:8d} "
                      f"{metrics['connections']:6d} "
                      f"{metrics['uptime_hours']:10.1f}")
            print()
        
        # Optimization suggestions
        if suggestions:
            print("💡 Optimization Suggestions:")
            for i, suggestion in enumerate(suggestions[:5], 1):
                print(f"  {i}. {suggestion}")
            print()
        
        # Recent alerts
        if self.alerts:
            print("⚠️  Recent Alerts:")
            for alert in self.alerts[-5:]:
                level_icon = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🚨"}.get(alert['level'], "•")
                print(f"  {level_icon} {alert['message']}")
            print()
    
    async def monitor_loop(self, interval: int = 10):
        """Main monitoring loop"""
        print("Starting ActiveLog Performance Monitor...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                # Collect metrics
                system_metrics = self.collect_system_metrics()
                service_metrics = self.collect_service_metrics()
                health_status = await self.health_check_services()
                
                # Check for issues
                new_alerts = self.check_performance_issues(system_metrics, service_metrics)
                self.alerts.extend(new_alerts)
                
                # Keep only recent alerts (last hour)
                cutoff_time = (datetime.now() - timedelta(hours=1)).isoformat()
                self.alerts = [a for a in self.alerts if a['timestamp'] > cutoff_time]
                
                # Generate suggestions
                suggestions = self.generate_optimization_suggestions(system_metrics, service_metrics)
                
                # Display dashboard
                self.print_dashboard(system_metrics, service_metrics, health_status, suggestions)
                
                # Save metrics
                all_metrics = {
                    'system': system_metrics,
                    'services': service_metrics,
                    'health': health_status,
                    'alerts': new_alerts
                }
                self.save_metrics(all_metrics)
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Performance monitoring stopped")

async def main():
    monitor = PerformanceMonitor()
    await monitor.monitor_loop()

if __name__ == "__main__":
    asyncio.run(main())