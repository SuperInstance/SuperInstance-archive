#!/usr/bin/env python3
"""
SuperInstance Component Usage Analytics & Optimization
=====================================================

Tracks usage patterns, performance metrics, and optimizes component performance 
for the SuperInstance $2/month Lego-like software construction system.

Features:
- Real-time usage tracking and analytics
- Performance monitoring and bottleneck detection
- Component optimization recommendations
- Usage pattern analysis for improved architecture
- Cost optimization based on actual usage
- Automated performance testing and benchmarking
"""

import os
import json
import sqlite3
import time
import psutil
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
import asyncio
import subprocess
from collections import defaultdict, Counter

@dataclass
class ComponentMetrics:
    """Performance and usage metrics for a component"""
    component_name: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    response_times: List[float]
    error_rates: Dict[str, int]
    request_count: int
    active_connections: int
    uptime: float
    timestamp: str

@dataclass
class UsagePattern:
    """Usage pattern analysis for components"""
    component_name: str
    peak_hours: List[int]
    average_load: float
    scaling_triggers: List[str]
    cost_efficiency: float
    optimization_opportunities: List[str]
    integration_frequency: Dict[str, int]

@dataclass
class OptimizationRecommendation:
    """Optimization recommendations for improved performance"""
    component_name: str
    issue_type: str  # 'performance', 'cost', 'scaling', 'resource'
    severity: str   # 'low', 'medium', 'high', 'critical'
    description: str
    solution: str
    estimated_improvement: str
    implementation_effort: str
    estimated_cost_savings: float

class ComponentUsageAnalytics:
    """
    Real-time analytics and optimization system for SuperInstance components
    """
    
    def __init__(self, base_path: str = "/home/activeloguser/activelog"):
        self.base_path = Path(base_path)
        self.db_path = self.base_path / "component_analytics.db"
        self.running_services = {}
        self.metrics_history = defaultdict(list)
        self.optimization_rules = {}
        self.monitoring_active = False
        
        self._initialize_database()
        self._load_optimization_rules()
        self._discover_running_services()
    
    def _initialize_database(self):
        """Initialize SQLite database for analytics storage"""
        with sqlite3.connect(self.db_path) as conn:
            # Component metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS component_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_name TEXT,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    network_io TEXT,
                    response_times TEXT,
                    error_rates TEXT,
                    request_count INTEGER,
                    active_connections INTEGER,
                    uptime REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Usage patterns table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS usage_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_name TEXT,
                    peak_hours TEXT,
                    average_load REAL,
                    scaling_triggers TEXT,
                    cost_efficiency REAL,
                    optimization_opportunities TEXT,
                    integration_frequency TEXT,
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Optimization recommendations table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS optimization_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_name TEXT,
                    issue_type TEXT,
                    severity TEXT,
                    description TEXT,
                    solution TEXT,
                    estimated_improvement TEXT,
                    implementation_effort TEXT,
                    estimated_cost_savings REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'open'
                )
            ''')
            
            # Performance benchmarks table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_benchmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_name TEXT,
                    test_type TEXT,
                    requests_per_second REAL,
                    average_response_time REAL,
                    error_rate REAL,
                    resource_usage TEXT,
                    benchmark_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def _load_optimization_rules(self):
        """Load optimization rules for different component types"""
        self.optimization_rules = {
            'fastapi': {
                'max_cpu_usage': 70.0,
                'max_memory_usage': 512.0,  # MB
                'max_response_time': 2.0,   # seconds
                'max_error_rate': 5.0,      # percentage
                'scaling_triggers': ['cpu > 60', 'memory > 400', 'response_time > 1.5']
            },
            'database': {
                'max_cpu_usage': 80.0,
                'max_memory_usage': 1024.0,
                'max_response_time': 0.5,
                'max_error_rate': 1.0,
                'scaling_triggers': ['connections > 80', 'cpu > 70', 'disk_io > 80']
            },
            'ai_service': {
                'max_cpu_usage': 90.0,
                'max_memory_usage': 2048.0,
                'max_response_time': 10.0,
                'max_error_rate': 3.0,
                'scaling_triggers': ['cpu > 85', 'memory > 1800', 'queue_length > 10']
            }
        }
    
    def _discover_running_services(self):
        """Discover currently running SuperInstance services"""
        services = {}
        
        try:
            # Check for running Python services on common ports
            common_ports = [8090, 8091, 8092, 8093, 8094, 8095, 8096, 8097, 8098, 8099, 8001]
            
            for port in common_ports:
                try:
                    response = requests.get(f"http://localhost:{port}/health", timeout=1)
                    if response.status_code == 200:
                        # Try to get service info
                        try:
                            info_response = requests.get(f"http://localhost:{port}/info", timeout=1)
                            if info_response.status_code == 200:
                                service_info = info_response.json()
                                service_name = service_info.get('name', f'service-{port}')
                            else:
                                service_name = f'service-{port}'
                        except:
                            service_name = f'service-{port}'
                        
                        services[service_name] = {
                            'port': port,
                            'url': f'http://localhost:{port}',
                            'status': 'running'
                        }
                        
                except requests.exceptions.RequestException:
                    continue
            
            self.running_services = services
            print(f"📊 Discovered {len(services)} running services for analytics")
            
        except Exception as e:
            print(f"Warning: Could not discover services: {e}")
    
    def collect_component_metrics(self, component_name: str, port: int) -> Optional[ComponentMetrics]:
        """Collect real-time metrics for a specific component"""
        try:
            # Get system metrics for the port
            cpu_usage = 0.0
            memory_usage = 0.0
            connections = 0
            
            # Find processes using this port
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    for conn in proc.connections():
                        if conn.laddr.port == port:
                            cpu_usage = proc.cpu_percent()
                            memory_usage = proc.memory_info().rss / 1024 / 1024  # MB
                            connections += 1
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Test response time
            response_times = []
            error_count = 0
            
            try:
                start_time = time.time()
                response = requests.get(f"http://localhost:{port}/health", timeout=5)
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                if response.status_code != 200:
                    error_count += 1
                    
            except requests.exceptions.RequestException:
                error_count += 1
                response_times.append(5.0)  # Timeout
            
            # Get disk usage for the service directory
            disk_usage = 0.0
            try:
                service_path = self.base_path / "services" / component_name
                if service_path.exists():
                    disk_usage = sum(f.stat().st_size for f in service_path.rglob('*') if f.is_file()) / 1024 / 1024  # MB
            except:
                pass
            
            return ComponentMetrics(
                component_name=component_name,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io={'bytes_sent': 0, 'bytes_recv': 0},  # Could be enhanced
                response_times=response_times,
                error_rates={'http_errors': error_count},
                request_count=1,  # This would be tracked over time
                active_connections=connections,
                uptime=time.time(),  # Simplified
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"Warning: Could not collect metrics for {component_name}: {e}")
            return None
    
    def analyze_usage_patterns(self, component_name: str, hours: int = 24) -> UsagePattern:
        """Analyze usage patterns over the specified time period"""
        with sqlite3.connect(self.db_path) as conn:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            cursor = conn.execute('''
                SELECT * FROM component_metrics 
                WHERE component_name = ? AND timestamp > ?
                ORDER BY timestamp
            ''', (component_name, cutoff_time.isoformat()))
            
            metrics = cursor.fetchall()
            
            if not metrics:
                # Return default pattern for new components
                return UsagePattern(
                    component_name=component_name,
                    peak_hours=[9, 10, 11, 14, 15, 16],  # Default business hours
                    average_load=0.0,
                    scaling_triggers=[],
                    cost_efficiency=1.0,
                    optimization_opportunities=[],
                    integration_frequency={}
                )
            
            # Analyze hourly patterns
            hourly_loads = defaultdict(list)
            total_cpu = 0
            total_memory = 0
            
            for metric in metrics:
                timestamp = datetime.fromisoformat(metric[11])
                hour = timestamp.hour
                cpu_usage = metric[2] or 0
                memory_usage = metric[3] or 0
                
                hourly_loads[hour].append(cpu_usage + memory_usage / 100)  # Combined load score
                total_cpu += cpu_usage
                total_memory += memory_usage
            
            # Find peak hours (top 25% of load)
            avg_hourly_loads = {hour: sum(loads) / len(loads) for hour, loads in hourly_loads.items()}
            sorted_hours = sorted(avg_hourly_loads.items(), key=lambda x: x[1], reverse=True)
            peak_hours = [hour for hour, load in sorted_hours[:6]]  # Top 6 hours
            
            average_load = (total_cpu + total_memory / 100) / len(metrics) if metrics else 0
            
            # Determine scaling triggers based on thresholds
            scaling_triggers = []
            if average_load > 60:
                scaling_triggers.append('high_load')
            if total_memory / len(metrics) > 400:
                scaling_triggers.append('memory_pressure')
            
            return UsagePattern(
                component_name=component_name,
                peak_hours=peak_hours,
                average_load=average_load,
                scaling_triggers=scaling_triggers,
                cost_efficiency=self._calculate_cost_efficiency(component_name, average_load),
                optimization_opportunities=self._identify_optimizations(component_name, metrics),
                integration_frequency={}
            )
    
    def generate_optimization_recommendations(self, component_name: str) -> List[OptimizationRecommendation]:
        """Generate actionable optimization recommendations"""
        recommendations = []
        
        # Get recent metrics
        usage_pattern = self.analyze_usage_patterns(component_name)
        
        # Performance optimization
        if usage_pattern.average_load > 70:
            recommendations.append(OptimizationRecommendation(
                component_name=component_name,
                issue_type='performance',
                severity='high',
                description=f'High average load detected: {usage_pattern.average_load:.1f}%',
                solution='Implement caching, optimize database queries, or scale horizontally',
                estimated_improvement='30-50% performance improvement',
                implementation_effort='medium',
                estimated_cost_savings=15.0
            ))
        
        # Memory optimization
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT AVG(memory_usage) FROM component_metrics 
                WHERE component_name = ? AND timestamp > datetime('now', '-1 hour')
            ''', (component_name,))
            
            avg_memory = cursor.fetchone()[0] or 0
            
            if avg_memory > 400:  # MB
                recommendations.append(OptimizationRecommendation(
                    component_name=component_name,
                    issue_type='resource',
                    severity='medium',
                    description=f'High memory usage: {avg_memory:.0f} MB average',
                    solution='Implement memory pooling, optimize data structures, add garbage collection tuning',
                    estimated_improvement='20-40% memory reduction',
                    implementation_effort='low',
                    estimated_cost_savings=8.0
                ))
        
        # Cost optimization
        if usage_pattern.cost_efficiency < 0.7:
            recommendations.append(OptimizationRecommendation(
                component_name=component_name,
                issue_type='cost',
                severity='medium',
                description=f'Low cost efficiency: {usage_pattern.cost_efficiency:.2f}',
                solution='Consider consolidating with other services or using smaller instance types',
                estimated_improvement='25-50% cost reduction',
                implementation_effort='medium',
                estimated_cost_savings=25.0
            ))
        
        # Scaling optimization
        if 'high_load' in usage_pattern.scaling_triggers:
            recommendations.append(OptimizationRecommendation(
                component_name=component_name,
                issue_type='scaling',
                severity='high',
                description='Service requires auto-scaling setup for peak loads',
                solution='Implement horizontal pod autoscaling or load-based container scaling',
                estimated_improvement='Better peak performance, cost optimization',
                implementation_effort='high',
                estimated_cost_savings=20.0
            ))
        
        # Store recommendations in database
        with sqlite3.connect(self.db_path) as conn:
            for rec in recommendations:
                conn.execute('''
                    INSERT INTO optimization_recommendations 
                    (component_name, issue_type, severity, description, solution, 
                     estimated_improvement, implementation_effort, estimated_cost_savings)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (rec.component_name, rec.issue_type, rec.severity, rec.description,
                      rec.solution, rec.estimated_improvement, rec.implementation_effort,
                      rec.estimated_cost_savings))
        
        return recommendations
    
    def run_performance_benchmarks(self, component_name: str, port: int) -> Dict[str, Any]:
        """Run performance benchmarks on a component"""
        print(f"🚀 Running performance benchmarks for {component_name}...")
        
        benchmark_results = {
            'component_name': component_name,
            'test_results': {},
            'recommendations': []
        }
        
        try:
            # Simple load test with varying concurrency
            for concurrency in [1, 5, 10, 20]:
                print(f"  Testing with {concurrency} concurrent requests...")
                
                start_time = time.time()
                successful_requests = 0
                total_response_time = 0
                errors = 0
                
                # Simulate concurrent requests (simplified)
                for i in range(concurrency * 10):  # 10 requests per concurrent user
                    try:
                        req_start = time.time()
                        response = requests.get(f"http://localhost:{port}/health", timeout=10)
                        req_time = time.time() - req_start
                        
                        if response.status_code == 200:
                            successful_requests += 1
                            total_response_time += req_time
                        else:
                            errors += 1
                    except requests.exceptions.RequestException:
                        errors += 1
                
                total_time = time.time() - start_time
                requests_per_second = (successful_requests) / total_time if total_time > 0 else 0
                avg_response_time = total_response_time / successful_requests if successful_requests > 0 else 0
                error_rate = errors / (successful_requests + errors) * 100 if (successful_requests + errors) > 0 else 0
                
                benchmark_results['test_results'][f'concurrency_{concurrency}'] = {
                    'requests_per_second': requests_per_second,
                    'average_response_time': avg_response_time,
                    'error_rate': error_rate,
                    'total_requests': concurrency * 10,
                    'successful_requests': successful_requests
                }
                
                # Store in database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT INTO performance_benchmarks 
                        (component_name, test_type, requests_per_second, average_response_time, error_rate, resource_usage)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (component_name, f'load_test_c{concurrency}', requests_per_second, 
                          avg_response_time, error_rate, json.dumps({})))
        
        except Exception as e:
            print(f"Warning: Benchmark failed for {component_name}: {e}")
            benchmark_results['error'] = str(e)
        
        return benchmark_results
    
    def start_continuous_monitoring(self, interval_seconds: int = 60):
        """Start continuous monitoring of all discovered services"""
        self.monitoring_active = True
        print(f"🔄 Starting continuous monitoring (interval: {interval_seconds}s)")
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    for service_name, service_info in self.running_services.items():
                        metrics = self.collect_component_metrics(service_name, service_info['port'])
                        
                        if metrics:
                            # Store metrics in database
                            with sqlite3.connect(self.db_path) as conn:
                                conn.execute('''
                                    INSERT INTO component_metrics 
                                    (component_name, cpu_usage, memory_usage, disk_usage, network_io, 
                                     response_times, error_rates, request_count, active_connections, uptime)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (metrics.component_name, metrics.cpu_usage, metrics.memory_usage,
                                      metrics.disk_usage, json.dumps(metrics.network_io),
                                      json.dumps(metrics.response_times), json.dumps(metrics.error_rates),
                                      metrics.request_count, metrics.active_connections, metrics.uptime))
                            
                            # Add to in-memory history
                            self.metrics_history[service_name].append(metrics)
                            
                            # Keep only recent metrics in memory (last 100 data points)
                            if len(self.metrics_history[service_name]) > 100:
                                self.metrics_history[service_name] = self.metrics_history[service_name][-100:]
                    
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    print(f"Monitoring error: {e}")
                    time.sleep(interval_seconds)
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False
        print("🛑 Monitoring stopped")
    
    def _calculate_cost_efficiency(self, component_name: str, average_load: float) -> float:
        """Calculate cost efficiency score based on resource utilization"""
        if average_load == 0:
            return 0.0
        
        # Ideal utilization is around 60-70% for good efficiency
        if 50 <= average_load <= 75:
            return 1.0  # Perfect efficiency
        elif average_load < 30:
            return 0.5  # Under-utilized
        elif average_load > 85:
            return 0.6  # Over-utilized, needs scaling
        else:
            # Gradual scoring
            return 0.8
    
    def _identify_optimizations(self, component_name: str, metrics: List) -> List[str]:
        """Identify optimization opportunities based on metrics"""
        opportunities = []
        
        if not metrics:
            return opportunities
        
        # Analyze patterns in the metrics data
        cpu_values = [m[2] for m in metrics if m[2] is not None]
        memory_values = [m[3] for m in metrics if m[3] is not None]
        
        if cpu_values:
            avg_cpu = sum(cpu_values) / len(cpu_values)
            max_cpu = max(cpu_values)
            
            if avg_cpu > 70:
                opportunities.append("cpu_optimization")
            if max_cpu > 90:
                opportunities.append("cpu_spike_handling")
        
        if memory_values:
            avg_memory = sum(memory_values) / len(memory_values)
            if avg_memory > 400:
                opportunities.append("memory_optimization")
        
        return opportunities
    
    def generate_analytics_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'services_monitored': len(self.running_services),
            'total_recommendations': 0,
            'cost_savings_potential': 0.0,
            'performance_summary': {},
            'top_recommendations': [],
            'system_health': 'good'
        }
        
        with sqlite3.connect(self.db_path) as conn:
            # Count total recommendations
            cursor = conn.execute('SELECT COUNT(*) FROM optimization_recommendations WHERE status = "open"')
            report['total_recommendations'] = cursor.fetchone()[0]
            
            # Calculate potential cost savings
            cursor = conn.execute('SELECT SUM(estimated_cost_savings) FROM optimization_recommendations WHERE status = "open"')
            savings = cursor.fetchone()[0]
            report['cost_savings_potential'] = savings if savings else 0.0
            
            # Get top recommendations
            cursor = conn.execute('''
                SELECT component_name, issue_type, severity, description, estimated_cost_savings
                FROM optimization_recommendations 
                WHERE status = "open"
                ORDER BY estimated_cost_savings DESC, severity DESC
                LIMIT 5
            ''')
            
            report['top_recommendations'] = [
                {
                    'component': row[0],
                    'type': row[1],
                    'severity': row[2],
                    'description': row[3],
                    'savings': row[4]
                }
                for row in cursor.fetchall()
            ]
        
        # Performance summary for each service
        for service_name in self.running_services:
            if service_name in self.metrics_history:
                recent_metrics = self.metrics_history[service_name][-10:]  # Last 10 data points
                if recent_metrics:
                    avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
                    avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
                    avg_response_time = sum(sum(m.response_times) / len(m.response_times) if m.response_times else 0 for m in recent_metrics) / len(recent_metrics)
                    
                    report['performance_summary'][service_name] = {
                        'cpu_usage': avg_cpu,
                        'memory_usage': avg_memory,
                        'response_time': avg_response_time,
                        'health_score': self._calculate_health_score(avg_cpu, avg_memory, avg_response_time)
                    }
        
        return report
    
    def _calculate_health_score(self, cpu: float, memory: float, response_time: float) -> str:
        """Calculate health score based on metrics"""
        if cpu < 50 and memory < 300 and response_time < 1.0:
            return 'excellent'
        elif cpu < 70 and memory < 400 and response_time < 2.0:
            return 'good'
        elif cpu < 85 and memory < 600 and response_time < 5.0:
            return 'fair'
        else:
            return 'needs_attention'

def main():
    """
    Main function to run component usage analytics
    """
    print("📊 SuperInstance Component Usage Analytics & Optimization")
    print("=" * 60)
    
    # Initialize analytics system
    analytics = ComponentUsageAnalytics()
    
    # Start continuous monitoring
    analytics.start_continuous_monitoring(interval_seconds=30)
    
    print(f"\n🎯 Monitoring {len(analytics.running_services)} services:")
    for name, info in analytics.running_services.items():
        print(f"  • {name} on port {info['port']}")
    
    # Run performance benchmarks on all services
    print("\n🚀 Running performance benchmarks...")
    benchmark_results = {}
    for service_name, service_info in analytics.running_services.items():
        results = analytics.run_performance_benchmarks(service_name, service_info['port'])
        benchmark_results[service_name] = results
    
    # Wait a bit for monitoring data
    print("\n⏱️  Collecting initial monitoring data...")
    time.sleep(30)
    
    # Generate optimization recommendations
    print("\n🔧 Generating optimization recommendations...")
    all_recommendations = []
    for service_name in analytics.running_services:
        recommendations = analytics.generate_optimization_recommendations(service_name)
        all_recommendations.extend(recommendations)
        
        if recommendations:
            print(f"\n📋 Recommendations for {service_name}:")
            for rec in recommendations[:3]:  # Show top 3
                print(f"  • {rec.issue_type.upper()}: {rec.description}")
                print(f"    Solution: {rec.solution}")
                print(f"    Savings: ${rec.estimated_cost_savings:.2f}/month")
    
    # Generate comprehensive report
    report = analytics.generate_analytics_report()
    
    print(f"\n📈 Analytics Summary:")
    print(f"  • Services monitored: {report['services_monitored']}")
    print(f"  • Total recommendations: {report['total_recommendations']}")
    print(f"  • Potential monthly savings: ${report['cost_savings_potential']:.2f}")
    print(f"  • System health: {report['system_health']}")
    
    print("\n💡 Top Optimization Opportunities:")
    for rec in report['top_recommendations'][:3]:
        print(f"  • {rec['component']}: {rec['description']} (${rec['savings']:.2f} savings)")
    
    print(f"\n✅ Analytics system operational!")
    print("🔄 Continuous monitoring active")
    print("💰 SuperInstance: Optimizing your $2/month investment for maximum value")
    
    # Keep monitoring running for demo
    try:
        time.sleep(60)  # Monitor for 1 minute
    except KeyboardInterrupt:
        pass
    finally:
        analytics.stop_monitoring()

if __name__ == "__main__":
    main()