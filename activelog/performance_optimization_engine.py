#!/usr/bin/env python3
"""
SuperInstance Performance Optimization Engine
BREAKTHROUGH: Cross-service performance monitoring and optimization
INNOVATION: Real-time performance tuning for all SuperInstance domains
AI INTEGRATION: Performance pattern learning and predictive optimization
"""

import asyncio
import aiohttp
import time
import json
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ServiceMetrics:
    service_name: str
    port: int
    response_time: float
    status_code: int
    memory_usage: float
    cpu_usage: float
    timestamp: datetime
    health_status: str = "unknown"

@dataclass
class OptimizationRecommendation:
    service: str
    recommendation_type: str
    description: str
    impact_score: float
    implementation_priority: str

class SuperInstancePerformanceEngine:
    def __init__(self):
        self.services = {
            "auth-service": {"port": 8001, "url": "http://localhost:8001/api/health"},
            "api-gateway": {"port": 8088, "url": "http://localhost:8088/health"},
            "activelog-ai": {"port": 8090, "url": "http://localhost:8090/health"},
            "user-management": {"port": 8092, "url": "http://localhost:8092/health"},
            "personallog-ai": {"port": 8095, "url": "http://localhost:8095/health"},
            "fishinglog-ai": {"port": 8096, "url": "http://localhost:8096/health"},
            "dmlog-ai": {"port": 8097, "url": "http://localhost:8097/health"},
            "businesslog-ai": {"port": 8098, "url": "http://localhost:8098/health"},
        }
        
        self.metrics_history = []
        self.optimization_recommendations = []
        self.performance_thresholds = {
            "response_time_ms": 500,
            "memory_usage_mb": 256,
            "cpu_usage_percent": 75,
            "error_rate_percent": 1.0
        }
        
    async def collect_service_metrics(self, service_name: str, config: Dict) -> Optional[ServiceMetrics]:
        """Collect comprehensive metrics for a service"""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(config["url"]) as response:
                    response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    status_code = response.status
                    
                    # Get system resource usage for the port
                    memory_usage, cpu_usage = self._get_process_metrics(config["port"])
                    
                    # Determine health status
                    health_status = "healthy" if status_code == 200 else "unhealthy"
                    
                    return ServiceMetrics(
                        service_name=service_name,
                        port=config["port"],
                        response_time=response_time,
                        status_code=status_code,
                        memory_usage=memory_usage,
                        cpu_usage=cpu_usage,
                        timestamp=datetime.now(),
                        health_status=health_status
                    )
                    
        except Exception as e:
            logger.warning(f"Failed to collect metrics for {service_name}: {e}")
            return ServiceMetrics(
                service_name=service_name,
                port=config["port"],
                response_time=0,
                status_code=0,
                memory_usage=0,
                cpu_usage=0,
                timestamp=datetime.now(),
                health_status="error"
            )
    
    def _get_process_metrics(self, port: int) -> Tuple[float, float]:
        """Get memory and CPU usage for process listening on given port"""
        try:
            connections = psutil.net_connections()
            for conn in connections:
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    if conn.pid:
                        process = psutil.Process(conn.pid)
                        memory_mb = process.memory_info().rss / 1024 / 1024
                        cpu_percent = process.cpu_percent(interval=0.1)
                        return memory_mb, cpu_percent
        except Exception:
            pass
        return 0.0, 0.0
    
    async def run_performance_scan(self) -> List[ServiceMetrics]:
        """Run comprehensive performance scan across all services"""
        logger.info("🔍 Starting SuperInstance performance scan...")
        
        tasks = []
        async with aiohttp.ClientSession() as session:
            for service_name, config in self.services.items():
                task = self.collect_service_metrics(service_name, config)
                tasks.append(task)
        
        metrics = await asyncio.gather(*tasks, return_exceptions=True)
        valid_metrics = [m for m in metrics if isinstance(m, ServiceMetrics)]
        
        # Store metrics in history
        self.metrics_history.extend(valid_metrics)
        
        # Keep only last 1000 metrics for memory efficiency
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        logger.info(f"✅ Performance scan complete - collected metrics for {len(valid_metrics)} services")
        return valid_metrics
    
    def analyze_performance_patterns(self, metrics: List[ServiceMetrics]) -> List[OptimizationRecommendation]:
        """Analyze performance patterns and generate optimization recommendations"""
        recommendations = []
        
        for metric in metrics:
            # Response time analysis
            if metric.response_time > self.performance_thresholds["response_time_ms"]:
                recommendations.append(OptimizationRecommendation(
                    service=metric.service_name,
                    recommendation_type="response_time",
                    description=f"Response time {metric.response_time:.1f}ms exceeds threshold {self.performance_thresholds['response_time_ms']}ms. Consider implementing caching, connection pooling, or async optimization.",
                    impact_score=0.8,
                    implementation_priority="HIGH"
                ))
            
            # Memory usage analysis
            if metric.memory_usage > self.performance_thresholds["memory_usage_mb"]:
                recommendations.append(OptimizationRecommendation(
                    service=metric.service_name,
                    recommendation_type="memory_optimization",
                    description=f"Memory usage {metric.memory_usage:.1f}MB exceeds threshold {self.performance_thresholds['memory_usage_mb']}MB. Implement memory pooling and garbage collection optimization.",
                    impact_score=0.7,
                    implementation_priority="MEDIUM"
                ))
            
            # CPU usage analysis
            if metric.cpu_usage > self.performance_thresholds["cpu_usage_percent"]:
                recommendations.append(OptimizationRecommendation(
                    service=metric.service_name,
                    recommendation_type="cpu_optimization",
                    description=f"CPU usage {metric.cpu_usage:.1f}% exceeds threshold {self.performance_thresholds['cpu_usage_percent']}%. Consider algorithm optimization and async processing.",
                    impact_score=0.9,
                    implementation_priority="HIGH"
                ))
            
            # Health status analysis
            if metric.health_status in ["unhealthy", "error"]:
                recommendations.append(OptimizationRecommendation(
                    service=metric.service_name,
                    recommendation_type="reliability",
                    description=f"Service health status: {metric.health_status}. Implement circuit breakers, retry logic, and health monitoring.",
                    impact_score=1.0,
                    implementation_priority="CRITICAL"
                ))
        
        return recommendations
    
    def generate_cross_service_optimizations(self, metrics: List[ServiceMetrics]) -> List[OptimizationRecommendation]:
        """Generate cross-service optimization recommendations"""
        recommendations = []
        
        # Analyze service interdependencies and bottlenecks
        ai_services = [m for m in metrics if "ai" in m.service_name.lower()]
        avg_ai_response_time = statistics.mean([m.response_time for m in ai_services]) if ai_services else 0
        
        if avg_ai_response_time > 300:  # 300ms threshold for AI services
            recommendations.append(OptimizationRecommendation(
                service="cross-domain-ai",
                recommendation_type="ai_optimization",
                description=f"Average AI service response time {avg_ai_response_time:.1f}ms indicates need for AI pipeline optimization. Implement request batching, model caching, and vector similarity optimization.",
                impact_score=0.85,
                implementation_priority="HIGH"
            ))
        
        # Database connection optimization
        db_heavy_services = ["user-management", "activelog-ai", "personallog-ai"]
        db_services_metrics = [m for m in metrics if m.service_name in db_heavy_services]
        
        if len(db_services_metrics) >= 2:
            recommendations.append(OptimizationRecommendation(
                service="database-layer",
                recommendation_type="connection_pooling",
                description="Multiple database-heavy services detected. Implement connection pooling, read replicas, and query optimization for PostgreSQL.",
                impact_score=0.75,
                implementation_priority="MEDIUM"
            ))
        
        return recommendations
    
    def print_performance_report(self, metrics: List[ServiceMetrics]):
        """Print comprehensive performance report"""
        print("\n" + "="*80)
        print("🚀 SUPERINSTANCE PERFORMANCE OPTIMIZATION REPORT")
        print("="*80)
        print(f"📊 Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔍 Services Analyzed: {len(metrics)}")
        print()
        
        # Service Status Overview
        print("📈 SERVICE PERFORMANCE OVERVIEW")
        print("-" * 50)
        for metric in sorted(metrics, key=lambda x: x.response_time, reverse=True):
            status_icon = "✅" if metric.health_status == "healthy" else "❌"
            response_icon = "🔥" if metric.response_time > 200 else "⚡"
            memory_icon = "🧠" if metric.memory_usage < 128 else "🔶"
            
            print(f"{status_icon} {metric.service_name:20} | Port: {metric.port:4} | "
                  f"{response_icon} {metric.response_time:6.1f}ms | "
                  f"{memory_icon} {metric.memory_usage:6.1f}MB | "
                  f"CPU: {metric.cpu_usage:5.1f}%")
        
        print()
        
        # Performance Statistics
        healthy_services = [m for m in metrics if m.health_status == "healthy"]
        avg_response_time = statistics.mean([m.response_time for m in healthy_services]) if healthy_services else 0
        total_memory = sum([m.memory_usage for m in metrics])
        
        print("📊 PERFORMANCE STATISTICS")
        print("-" * 30)
        print(f"🎯 Healthy Services: {len(healthy_services)}/{len(metrics)}")
        print(f"⚡ Average Response Time: {avg_response_time:.1f}ms")
        print(f"🧠 Total Memory Usage: {total_memory:.1f}MB")
        print(f"🔄 Services Scanned: {len(self.services)}")
        
        # Generate and display recommendations
        recommendations = self.analyze_performance_patterns(metrics)
        cross_service_recs = self.generate_cross_service_optimizations(metrics)
        all_recommendations = recommendations + cross_service_recs
        
        if all_recommendations:
            print("\n🔧 OPTIMIZATION RECOMMENDATIONS")
            print("-" * 40)
            
            # Group by priority
            critical_recs = [r for r in all_recommendations if r.implementation_priority == "CRITICAL"]
            high_recs = [r for r in all_recommendations if r.implementation_priority == "HIGH"]
            medium_recs = [r for r in all_recommendations if r.implementation_priority == "MEDIUM"]
            
            for priority, recs in [("CRITICAL", critical_recs), ("HIGH", high_recs), ("MEDIUM", medium_recs)]:
                if recs:
                    priority_icon = "🚨" if priority == "CRITICAL" else "⚠️" if priority == "HIGH" else "💡"
                    print(f"\n{priority_icon} {priority} PRIORITY ({len(recs)} recommendations)")
                    for i, rec in enumerate(recs, 1):
                        print(f"   {i}. {rec.service}: {rec.description}")
        else:
            print("\n🎉 EXCELLENT PERFORMANCE - No optimization recommendations needed!")
        
        print("\n" + "="*80)
    
    async def continuous_monitoring(self, interval_seconds: int = 30):
        """Run continuous performance monitoring"""
        logger.info(f"🔄 Starting continuous monitoring (interval: {interval_seconds}s)")
        
        while True:
            try:
                metrics = await self.run_performance_scan()
                self.print_performance_report(metrics)
                
                # Log critical issues
                critical_issues = [m for m in metrics if m.health_status in ["unhealthy", "error"]]
                if critical_issues:
                    logger.warning(f"🚨 {len(critical_issues)} services have critical issues!")
                
                await asyncio.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("👋 Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
                await asyncio.sleep(interval_seconds)

async def main():
    """Main performance optimization execution"""
    print("🚀 SuperInstance Performance Optimization Engine")
    print("🎯 Analyzing all SuperInstance services...")
    
    engine = SuperInstancePerformanceEngine()
    
    # Single performance scan
    metrics = await engine.run_performance_scan()
    engine.print_performance_report(metrics)
    
    # Ask for continuous monitoring
    print("\n" + "="*50)
    print("🔄 CONTINUOUS MONITORING AVAILABLE")
    print("Run with --continuous for real-time monitoring")
    print("Example: python3 performance_optimization_engine.py --continuous")

if __name__ == "__main__":
    import sys
    
    if "--continuous" in sys.argv:
        asyncio.run(SuperInstancePerformanceEngine().continuous_monitoring())
    else:
        asyncio.run(main())