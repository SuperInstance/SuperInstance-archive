"""
Performance Benchmark Testing Engine for ActiveLog Platform

This module provides comprehensive performance benchmarking including response time analysis,
throughput testing, resource utilization monitoring, and performance regression detection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
import json
import asyncio
import aiohttp
import time
import statistics
import logging
from pathlib import Path
import psutil
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import subprocess
import threading
import queue


class BenchmarkType(Enum):
    """Types of performance benchmarks"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    LATENCY_DISTRIBUTION = "latency_distribution"
    RESOURCE_UTILIZATION = "resource_utilization"
    MEMORY_USAGE = "memory_usage"
    CPU_PERFORMANCE = "cpu_performance"
    DATABASE_PERFORMANCE = "database_performance"
    NETWORK_PERFORMANCE = "network_performance"
    CACHE_PERFORMANCE = "cache_performance"
    FILE_IO_PERFORMANCE = "file_io_performance"


class PerformanceMetric(Enum):
    """Performance metrics to track"""
    RESPONSE_TIME_MS = "response_time_ms"
    REQUESTS_PER_SECOND = "requests_per_second"
    CPU_USAGE_PERCENT = "cpu_usage_percent"
    MEMORY_USAGE_MB = "memory_usage_mb"
    DISK_IO_MB_S = "disk_io_mb_s"
    NETWORK_IO_MB_S = "network_io_mb_s"
    DATABASE_QUERY_TIME_MS = "database_query_time_ms"
    CACHE_HIT_RATIO = "cache_hit_ratio"
    ERROR_RATE_PERCENT = "error_rate_percent"
    THROUGHPUT_MB_S = "throughput_mb_s"


class BenchmarkResult(Enum):
    """Benchmark result status"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class PerformanceBenchmark:
    """Performance benchmark definition"""
    benchmark_id: str
    name: str
    description: str
    benchmark_type: BenchmarkType
    target_endpoint: str
    test_method: str = "GET"
    test_data: Optional[Dict[str, Any]] = None
    concurrent_users: int = 10
    duration_seconds: float = 60.0
    warm_up_seconds: float = 10.0
    target_metrics: Dict[PerformanceMetric, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class BenchmarkMeasurement:
    """Single performance measurement"""
    timestamp: datetime
    metric: PerformanceMetric
    value: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark"""
    benchmark_id: str
    benchmark_name: str
    benchmark_type: BenchmarkType
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    measurements: List[BenchmarkMeasurement] = field(default_factory=list)
    summary_statistics: Dict[str, Any] = field(default_factory=dict)
    performance_score: float = 0.0
    result_status: str = "unknown"
    recommendations: List[str] = field(default_factory=list)
    baseline_comparison: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceReport:
    """Comprehensive performance benchmark report"""
    report_id: str
    test_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_benchmarks: int = 0
    benchmark_results: List[BenchmarkResult] = field(default_factory=list)
    overall_performance_score: float = 0.0
    system_info: Dict[str, Any] = field(default_factory=dict)
    performance_trends: Dict[str, List[float]] = field(default_factory=dict)
    regression_analysis: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class SystemMonitor:
    """Monitors system performance metrics"""
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.monitoring = False
        self.measurements: List[BenchmarkMeasurement] = []
        self.monitor_thread: Optional[threading.Thread] = None
    
    def start_monitoring(self):
        """Start system monitoring"""
        self.monitoring = True
        self.measurements = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            timestamp = datetime.now()
            
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.measurements.append(BenchmarkMeasurement(
                    timestamp=timestamp,
                    metric=PerformanceMetric.CPU_USAGE_PERCENT,
                    value=cpu_percent
                ))
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_mb = memory.used / (1024 * 1024)
                self.measurements.append(BenchmarkMeasurement(
                    timestamp=timestamp,
                    metric=PerformanceMetric.MEMORY_USAGE_MB,
                    value=memory_mb
                ))
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    # Calculate I/O rate (simplified)
                    disk_io_mb_s = (disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024)
                    self.measurements.append(BenchmarkMeasurement(
                        timestamp=timestamp,
                        metric=PerformanceMetric.DISK_IO_MB_S,
                        value=disk_io_mb_s
                    ))
                
                # Network I/O
                network_io = psutil.net_io_counters()
                if network_io:
                    network_io_mb_s = (network_io.bytes_sent + network_io.bytes_recv) / (1024 * 1024)
                    self.measurements.append(BenchmarkMeasurement(
                        timestamp=timestamp,
                        metric=PerformanceMetric.NETWORK_IO_MB_S,
                        value=network_io_mb_s
                    ))
                
            except Exception as e:
                logging.error(f"Error collecting system metrics: {e}")
            
            time.sleep(self.collection_interval)
    
    def get_measurements(self) -> List[BenchmarkMeasurement]:
        """Get collected measurements"""
        return self.measurements.copy()


class ResponseTimeBenchmarker:
    """Benchmarks HTTP response times"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=100)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def benchmark_endpoint(self, benchmark: PerformanceBenchmark) -> BenchmarkResult:
        """Benchmark a specific endpoint"""
        result = BenchmarkResult(
            benchmark_id=benchmark.benchmark_id,
            benchmark_name=benchmark.name,
            benchmark_type=benchmark.benchmark_type,
            start_time=datetime.now()
        )
        
        measurements = []
        url = f"{self.base_url}{benchmark.target_endpoint}"
        
        try:
            # Warm-up phase
            if benchmark.warm_up_seconds > 0:
                await self._warm_up(url, benchmark.test_method, benchmark.warm_up_seconds)
            
            # Main benchmark phase
            end_time = time.time() + benchmark.duration_seconds
            request_count = 0
            error_count = 0
            
            # Create semaphore for concurrent requests
            semaphore = asyncio.Semaphore(benchmark.concurrent_users)
            
            async def make_request():
                nonlocal request_count, error_count
                
                async with semaphore:
                    start_request = time.time()
                    
                    try:
                        if benchmark.test_method.upper() == "POST":
                            async with self.session.post(url, json=benchmark.test_data) as response:
                                await response.read()
                                status_code = response.status
                        else:
                            async with self.session.get(url) as response:
                                await response.read()
                                status_code = response.status
                        
                        response_time_ms = (time.time() - start_request) * 1000
                        
                        measurements.append(BenchmarkMeasurement(
                            timestamp=datetime.now(),
                            metric=PerformanceMetric.RESPONSE_TIME_MS,
                            value=response_time_ms,
                            context={"status_code": status_code}
                        ))
                        
                        request_count += 1
                        
                        if status_code >= 400:
                            error_count += 1
                    
                    except Exception as e:
                        error_count += 1
                        logging.debug(f"Request error: {e}")
            
            # Generate concurrent requests
            tasks = []
            while time.time() < end_time:
                # Create batch of concurrent requests
                batch_size = min(benchmark.concurrent_users, 50)  # Limit batch size
                batch_tasks = [make_request() for _ in range(batch_size)]
                
                # Wait for batch to complete or timeout
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*batch_tasks, return_exceptions=True),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    pass
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            # Wait for remaining tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            result.measurements = measurements
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            # Calculate statistics
            if measurements:
                response_times = [m.value for m in measurements if m.metric == PerformanceMetric.RESPONSE_TIME_MS]
                
                result.summary_statistics = {
                    "total_requests": request_count,
                    "total_errors": error_count,
                    "error_rate_percent": (error_count / request_count * 100) if request_count > 0 else 0,
                    "requests_per_second": request_count / result.duration_seconds if result.duration_seconds > 0 else 0,
                    "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
                    "min_response_time_ms": min(response_times) if response_times else 0,
                    "max_response_time_ms": max(response_times) if response_times else 0,
                    "p50_response_time_ms": statistics.median(response_times) if response_times else 0,
                    "p95_response_time_ms": np.percentile(response_times, 95) if response_times else 0,
                    "p99_response_time_ms": np.percentile(response_times, 99) if response_times else 0
                }
                
                # Calculate performance score
                result.performance_score = self._calculate_performance_score(result.summary_statistics)
                result.result_status = self._determine_result_status(result.performance_score)
                result.recommendations = self._generate_recommendations(result.summary_statistics)
        
        except Exception as e:
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            result.result_status = "error"
            logging.error(f"Benchmark error: {e}")
        
        return result
    
    async def _warm_up(self, url: str, method: str, duration: float):
        """Warm up the endpoint"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            try:
                if method.upper() == "POST":
                    async with self.session.post(url) as response:
                        await response.read()
                else:
                    async with self.session.get(url) as response:
                        await response.read()
            except:
                pass
            
            await asyncio.sleep(0.1)
    
    def _calculate_performance_score(self, stats: Dict[str, Any]) -> float:
        """Calculate performance score based on statistics"""
        score = 100.0
        
        # Penalize high response times
        avg_response_time = stats.get("avg_response_time_ms", 0)
        if avg_response_time > 1000:  # > 1 second
            score -= 30
        elif avg_response_time > 500:  # > 500ms
            score -= 15
        elif avg_response_time > 200:  # > 200ms
            score -= 5
        
        # Penalize high error rates
        error_rate = stats.get("error_rate_percent", 0)
        if error_rate > 10:
            score -= 40
        elif error_rate > 5:
            score -= 20
        elif error_rate > 1:
            score -= 10
        
        # Penalize low throughput
        rps = stats.get("requests_per_second", 0)
        if rps < 10:
            score -= 20
        elif rps < 50:
            score -= 10
        
        # Penalize high P95 response times
        p95_time = stats.get("p95_response_time_ms", 0)
        if p95_time > 2000:
            score -= 20
        elif p95_time > 1000:
            score -= 10
        
        return max(0, score)
    
    def _determine_result_status(self, score: float) -> str:
        """Determine result status based on score"""
        if score >= 90:
            return BenchmarkResult.EXCELLENT.value
        elif score >= 75:
            return BenchmarkResult.GOOD.value
        elif score >= 60:
            return BenchmarkResult.ACCEPTABLE.value
        elif score >= 40:
            return BenchmarkResult.POOR.value
        else:
            return BenchmarkResult.CRITICAL.value
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        avg_response_time = stats.get("avg_response_time_ms", 0)
        if avg_response_time > 500:
            recommendations.append("Optimize response time - consider caching, database indexing, or code optimization")
        
        error_rate = stats.get("error_rate_percent", 0)
        if error_rate > 5:
            recommendations.append("Investigate and fix errors causing high error rate")
        
        rps = stats.get("requests_per_second", 0)
        if rps < 50:
            recommendations.append("Improve throughput - consider scaling resources or optimizing bottlenecks")
        
        p95_time = stats.get("p95_response_time_ms", 0)
        if p95_time > avg_response_time * 3:
            recommendations.append("High response time variance - investigate outliers and optimize slow requests")
        
        return recommendations


class DatabaseBenchmarker:
    """Benchmarks database performance"""
    
    def __init__(self, connection_string: str, db_type: str = "postgresql"):
        self.connection_string = connection_string
        self.db_type = db_type
    
    async def benchmark_queries(self, queries: List[Dict[str, Any]]) -> List[BenchmarkMeasurement]:
        """Benchmark database queries"""
        measurements = []
        
        # This is a simplified implementation
        # In practice, would use actual database connections
        
        for i, query_info in enumerate(queries):
            query = query_info.get("query", "")
            iterations = query_info.get("iterations", 100)
            
            query_times = []
            
            for _ in range(iterations):
                start_time = time.time()
                
                # Simulate query execution
                await asyncio.sleep(random.uniform(0.001, 0.05))  # Mock query time
                
                query_time_ms = (time.time() - start_time) * 1000
                query_times.append(query_time_ms)
            
            # Calculate statistics
            avg_query_time = statistics.mean(query_times)
            measurements.append(BenchmarkMeasurement(
                timestamp=datetime.now(),
                metric=PerformanceMetric.DATABASE_QUERY_TIME_MS,
                value=avg_query_time,
                context={
                    "query_id": i,
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "iterations": iterations,
                    "min_time_ms": min(query_times),
                    "max_time_ms": max(query_times),
                    "p95_time_ms": np.percentile(query_times, 95)
                }
            ))
        
        return measurements


class CacheBenchmarker:
    """Benchmarks cache performance"""
    
    def __init__(self, cache_url: str = "redis://localhost:6379"):
        self.cache_url = cache_url
    
    async def benchmark_cache_operations(self, operations: List[str], key_count: int = 1000) -> List[BenchmarkMeasurement]:
        """Benchmark cache operations"""
        measurements = []
        
        # Mock cache operations
        for operation in operations:
            start_time = time.time()
            
            if operation == "set":
                # Simulate SET operations
                for i in range(key_count):
                    await asyncio.sleep(0.0001)  # Mock set operation
                
                operation_time_ms = (time.time() - start_time) * 1000
                throughput = key_count / (operation_time_ms / 1000)
                
                measurements.append(BenchmarkMeasurement(
                    timestamp=datetime.now(),
                    metric=PerformanceMetric.THROUGHPUT_MB_S,
                    value=throughput,
                    context={
                        "operation": operation,
                        "key_count": key_count,
                        "operation_time_ms": operation_time_ms
                    }
                ))
            
            elif operation == "get":
                # Simulate GET operations with hit ratio
                hit_count = 0
                for i in range(key_count):
                    # Simulate cache hit/miss
                    if random.random() < 0.85:  # 85% hit ratio
                        hit_count += 1
                    await asyncio.sleep(0.0001)
                
                hit_ratio = (hit_count / key_count) * 100
                
                measurements.append(BenchmarkMeasurement(
                    timestamp=datetime.now(),
                    metric=PerformanceMetric.CACHE_HIT_RATIO,
                    value=hit_ratio,
                    context={
                        "operation": operation,
                        "key_count": key_count,
                        "hit_count": hit_count
                    }
                ))
        
        return measurements


class PerformanceBenchmarkEngine:
    """Main performance benchmark testing engine"""
    
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.benchmarks: List[PerformanceBenchmark] = []
        self.baseline_results: Dict[str, BenchmarkResult] = {}
        self.system_monitor = SystemMonitor()
    
    def add_benchmark(self, benchmark: PerformanceBenchmark):
        """Add performance benchmark"""
        self.benchmarks.append(benchmark)
    
    def create_default_benchmarks(self):
        """Create default performance benchmarks for ActiveLog platform"""
        
        # API Response Time Benchmark
        api_response_benchmark = PerformanceBenchmark(
            benchmark_id="api_response_time",
            name="API Response Time",
            description="Measure API endpoint response times",
            benchmark_type=BenchmarkType.RESPONSE_TIME,
            target_endpoint="/api/health",
            concurrent_users=20,
            duration_seconds=60.0,
            target_metrics={
                PerformanceMetric.RESPONSE_TIME_MS: 200.0,
                PerformanceMetric.REQUESTS_PER_SECOND: 100.0,
                PerformanceMetric.ERROR_RATE_PERCENT: 1.0
            }
        )
        
        # Throughput Benchmark
        throughput_benchmark = PerformanceBenchmark(
            benchmark_id="api_throughput",
            name="API Throughput",
            description="Measure maximum API throughput",
            benchmark_type=BenchmarkType.THROUGHPUT,
            target_endpoint="/api/data",
            concurrent_users=50,
            duration_seconds=120.0,
            target_metrics={
                PerformanceMetric.REQUESTS_PER_SECOND: 200.0,
                PerformanceMetric.CPU_USAGE_PERCENT: 70.0
            }
        )
        
        # Database Performance Benchmark
        db_benchmark = PerformanceBenchmark(
            benchmark_id="database_performance",
            name="Database Performance",
            description="Measure database query performance",
            benchmark_type=BenchmarkType.DATABASE_PERFORMANCE,
            target_endpoint="/api/users",
            concurrent_users=10,
            duration_seconds=90.0,
            target_metrics={
                PerformanceMetric.DATABASE_QUERY_TIME_MS: 50.0
            }
        )
        
        # Memory Usage Benchmark
        memory_benchmark = PerformanceBenchmark(
            benchmark_id="memory_usage",
            name="Memory Usage",
            description="Monitor memory consumption under load",
            benchmark_type=BenchmarkType.MEMORY_USAGE,
            target_endpoint="/api/content/create",
            test_method="POST",
            test_data={"title": "Performance Test", "content": "Test content " * 100},
            concurrent_users=30,
            duration_seconds=180.0,
            target_metrics={
                PerformanceMetric.MEMORY_USAGE_MB: 1000.0
            }
        )
        
        self.add_benchmark(api_response_benchmark)
        self.add_benchmark(throughput_benchmark)
        self.add_benchmark(db_benchmark)
        self.add_benchmark(memory_benchmark)
    
    async def run_all_benchmarks(self) -> PerformanceReport:
        """Run all performance benchmarks"""
        session_id = f"perf_benchmark_{int(time.time())}"
        
        report = PerformanceReport(
            report_id=f"report_{session_id}",
            test_session_id=session_id,
            start_time=datetime.now(),
            total_benchmarks=len(self.benchmarks),
            system_info=self._get_system_info()
        )
        
        print(f"Starting performance benchmarks...")
        print(f"Running {len(self.benchmarks)} benchmarks against {self.target_url}")
        
        # Start system monitoring
        self.system_monitor.start_monitoring()
        
        try:
            async with ResponseTimeBenchmarker(self.target_url) as benchmarker:
                
                for benchmark in self.benchmarks:
                    print(f"Running benchmark: {benchmark.name}")
                    
                    try:
                        if benchmark.benchmark_type in [BenchmarkType.RESPONSE_TIME, BenchmarkType.THROUGHPUT, BenchmarkType.MEMORY_USAGE]:
                            result = await benchmarker.benchmark_endpoint(benchmark)
                        elif benchmark.benchmark_type == BenchmarkType.DATABASE_PERFORMANCE:
                            result = await self._run_database_benchmark(benchmark)
                        elif benchmark.benchmark_type == BenchmarkType.CACHE_PERFORMANCE:
                            result = await self._run_cache_benchmark(benchmark)
                        else:
                            result = await benchmarker.benchmark_endpoint(benchmark)
                        
                        # Compare with baseline if available
                        if benchmark.benchmark_id in self.baseline_results:
                            result.baseline_comparison = self._compare_with_baseline(
                                result, self.baseline_results[benchmark.benchmark_id]
                            )
                        
                        report.benchmark_results.append(result)
                        
                        print(f"  - {benchmark.name}: {result.result_status} (Score: {result.performance_score:.1f})")
                        
                    except Exception as e:
                        logging.error(f"Benchmark {benchmark.name} failed: {e}")
                        
                        # Create error result
                        error_result = BenchmarkResult(
                            benchmark_id=benchmark.benchmark_id,
                            benchmark_name=benchmark.name,
                            benchmark_type=benchmark.benchmark_type,
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            result_status="error"
                        )
                        report.benchmark_results.append(error_result)
                    
                    # Brief pause between benchmarks
                    await asyncio.sleep(5.0)
        
        finally:
            # Stop system monitoring
            self.system_monitor.stop_monitoring()
            
            # Add system measurements to report
            system_measurements = self.system_monitor.get_measurements()
            report.performance_trends = self._analyze_performance_trends(system_measurements)
        
        # Calculate overall performance score
        if report.benchmark_results:
            scores = [r.performance_score for r in report.benchmark_results if r.performance_score > 0]
            report.overall_performance_score = statistics.mean(scores) if scores else 0
        
        # Generate recommendations
        report.recommendations = self._generate_overall_recommendations(report)
        
        # Regression analysis
        report.regression_analysis = self._perform_regression_analysis(report)
        
        report.end_time = datetime.now()
        
        print(f"Performance benchmarks completed:")
        print(f"  Overall Score: {report.overall_performance_score:.1f}/100")
        print(f"  Duration: {(report.end_time - report.start_time).total_seconds():.1f}s")
        
        return report
    
    async def _run_database_benchmark(self, benchmark: PerformanceBenchmark) -> BenchmarkResult:
        """Run database-specific benchmark"""
        result = BenchmarkResult(
            benchmark_id=benchmark.benchmark_id,
            benchmark_name=benchmark.name,
            benchmark_type=benchmark.benchmark_type,
            start_time=datetime.now()
        )
        
        try:
            # Mock database benchmarking
            db_benchmarker = DatabaseBenchmarker("mock://connection")
            
            test_queries = [
                {"query": "SELECT * FROM users WHERE id = ?", "iterations": 1000},
                {"query": "SELECT * FROM posts WHERE user_id = ?", "iterations": 500},
                {"query": "SELECT COUNT(*) FROM users", "iterations": 100}
            ]
            
            measurements = await db_benchmarker.benchmark_queries(test_queries)
            result.measurements = measurements
            
            if measurements:
                query_times = [m.value for m in measurements]
                result.summary_statistics = {
                    "avg_query_time_ms": statistics.mean(query_times),
                    "min_query_time_ms": min(query_times),
                    "max_query_time_ms": max(query_times),
                    "total_queries": sum(m.context.get("iterations", 0) for m in measurements)
                }
                
                result.performance_score = self._calculate_db_performance_score(result.summary_statistics)
                result.result_status = self._determine_result_status_from_score(result.performance_score)
        
        except Exception as e:
            result.result_status = "error"
            logging.error(f"Database benchmark error: {e}")
        
        result.end_time = datetime.now()
        result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _run_cache_benchmark(self, benchmark: PerformanceBenchmark) -> BenchmarkResult:
        """Run cache-specific benchmark"""
        result = BenchmarkResult(
            benchmark_id=benchmark.benchmark_id,
            benchmark_name=benchmark.name,
            benchmark_type=benchmark.benchmark_type,
            start_time=datetime.now()
        )
        
        try:
            cache_benchmarker = CacheBenchmarker()
            measurements = await cache_benchmarker.benchmark_cache_operations(["set", "get"], 10000)
            result.measurements = measurements
            
            if measurements:
                hit_ratios = [m.value for m in measurements if m.metric == PerformanceMetric.CACHE_HIT_RATIO]
                throughputs = [m.value for m in measurements if m.metric == PerformanceMetric.THROUGHPUT_MB_S]
                
                result.summary_statistics = {
                    "avg_cache_hit_ratio": statistics.mean(hit_ratios) if hit_ratios else 0,
                    "avg_throughput": statistics.mean(throughputs) if throughputs else 0
                }
                
                result.performance_score = self._calculate_cache_performance_score(result.summary_statistics)
                result.result_status = self._determine_result_status_from_score(result.performance_score)
        
        except Exception as e:
            result.result_status = "error"
            logging.error(f"Cache benchmark error: {e}")
        
        result.end_time = datetime.now()
        result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "cpu_cores": psutil.cpu_count(),
                "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                "total_memory_gb": psutil.virtual_memory().total / (1024**3),
                "disk_space_gb": psutil.disk_usage('/').total / (1024**3),
                "platform": psutil.os.name,
                "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}"
            }
        except:
            return {"error": "Could not collect system info"}
    
    def _analyze_performance_trends(self, measurements: List[BenchmarkMeasurement]) -> Dict[str, List[float]]:
        """Analyze performance trends from measurements"""
        trends = {}
        
        # Group measurements by metric
        by_metric = {}
        for measurement in measurements:
            metric = measurement.metric.value
            if metric not in by_metric:
                by_metric[metric] = []
            by_metric[metric].append(measurement.value)
        
        # Calculate trends
        for metric, values in by_metric.items():
            if len(values) > 1:
                # Simple moving average trend
                window_size = min(10, len(values) // 5)
                if window_size > 0:
                    trend = []
                    for i in range(len(values)):
                        start_idx = max(0, i - window_size + 1)
                        window_values = values[start_idx:i+1]
                        trend.append(statistics.mean(window_values))
                    trends[metric] = trend
        
        return trends
    
    def _compare_with_baseline(self, current: BenchmarkResult, baseline: BenchmarkResult) -> Dict[str, Any]:
        """Compare current result with baseline"""
        comparison = {
            "performance_score_change": current.performance_score - baseline.performance_score,
            "performance_score_change_percent": ((current.performance_score - baseline.performance_score) / baseline.performance_score) * 100 if baseline.performance_score > 0 else 0
        }
        
        # Compare specific metrics
        current_stats = current.summary_statistics
        baseline_stats = baseline.summary_statistics
        
        metric_comparisons = {}
        for metric in current_stats:
            if metric in baseline_stats:
                current_val = current_stats[metric]
                baseline_val = baseline_stats[metric]
                
                if baseline_val > 0:
                    change_percent = ((current_val - baseline_val) / baseline_val) * 100
                    metric_comparisons[metric] = {
                        "current": current_val,
                        "baseline": baseline_val,
                        "change_percent": change_percent,
                        "improved": self._is_metric_improved(metric, change_percent)
                    }
        
        comparison["metric_comparisons"] = metric_comparisons
        return comparison
    
    def _is_metric_improved(self, metric: str, change_percent: float) -> bool:
        """Determine if metric change is an improvement"""
        # For response times, lower is better
        if "response_time" in metric or "query_time" in metric:
            return change_percent < 0
        
        # For error rates, lower is better
        if "error_rate" in metric:
            return change_percent < 0
        
        # For throughput and RPS, higher is better
        if "requests_per_second" in metric or "throughput" in metric:
            return change_percent > 0
        
        # For hit ratios, higher is better
        if "hit_ratio" in metric:
            return change_percent > 0
        
        return False
    
    def _calculate_db_performance_score(self, stats: Dict[str, Any]) -> float:
        """Calculate database performance score"""
        score = 100.0
        
        avg_query_time = stats.get("avg_query_time_ms", 0)
        if avg_query_time > 100:
            score -= 30
        elif avg_query_time > 50:
            score -= 15
        elif avg_query_time > 20:
            score -= 5
        
        return max(0, score)
    
    def _calculate_cache_performance_score(self, stats: Dict[str, Any]) -> float:
        """Calculate cache performance score"""
        score = 100.0
        
        hit_ratio = stats.get("avg_cache_hit_ratio", 0)
        if hit_ratio < 70:
            score -= 40
        elif hit_ratio < 85:
            score -= 20
        elif hit_ratio < 95:
            score -= 10
        
        throughput = stats.get("avg_throughput", 0)
        if throughput < 1000:
            score -= 20
        elif throughput < 5000:
            score -= 10
        
        return max(0, score)
    
    def _determine_result_status_from_score(self, score: float) -> str:
        """Determine result status from performance score"""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "acceptable"
        elif score >= 40:
            return "poor"
        else:
            return "critical"
    
    def _generate_overall_recommendations(self, report: PerformanceReport) -> List[str]:
        """Generate overall performance recommendations"""
        recommendations = []
        
        # Analyze results
        poor_results = [r for r in report.benchmark_results if r.performance_score < 60]
        critical_results = [r for r in report.benchmark_results if r.performance_score < 40]
        
        if critical_results:
            recommendations.append(f"URGENT: Address {len(critical_results)} critical performance issues immediately")
        
        if poor_results:
            recommendations.append(f"Optimize {len(poor_results)} underperforming components")
        
        # System resource recommendations
        if report.performance_trends:
            cpu_trend = report.performance_trends.get("cpu_usage_percent", [])
            if cpu_trend and statistics.mean(cpu_trend) > 80:
                recommendations.append("High CPU usage detected - consider scaling or optimization")
            
            memory_trend = report.performance_trends.get("memory_usage_mb", [])
            if memory_trend and len(memory_trend) > 1:
                memory_growth = (memory_trend[-1] - memory_trend[0]) / memory_trend[0] * 100
                if memory_growth > 50:
                    recommendations.append("Memory usage growth detected - investigate memory leaks")
        
        # General recommendations
        recommendations.extend([
            "Set up continuous performance monitoring",
            "Establish performance budgets and alerts",
            "Implement caching strategies where applicable",
            "Consider database query optimization",
            "Monitor and optimize critical user journeys"
        ])
        
        return recommendations[:10]
    
    def _perform_regression_analysis(self, report: PerformanceReport) -> Dict[str, Any]:
        """Perform regression analysis"""
        analysis = {
            "regressions_detected": 0,
            "improvements_detected": 0,
            "stable_metrics": 0
        }
        
        for result in report.benchmark_results:
            if result.baseline_comparison:
                change_percent = result.baseline_comparison.get("performance_score_change_percent", 0)
                
                if change_percent < -10:  # More than 10% degradation
                    analysis["regressions_detected"] += 1
                elif change_percent > 10:  # More than 10% improvement
                    analysis["improvements_detected"] += 1
                else:
                    analysis["stable_metrics"] += 1
        
        return analysis
    
    def save_baseline(self, results: List[BenchmarkResult]):
        """Save benchmark results as baseline"""
        for result in results:
            self.baseline_results[result.benchmark_id] = result
        
        # Save to file for persistence
        baseline_file = Path("performance_baseline.json")
        baseline_data = {
            result.benchmark_id: {
                "performance_score": result.performance_score,
                "summary_statistics": result.summary_statistics,
                "timestamp": result.start_time.isoformat()
            }
            for result in results
        }
        
        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        print(f"Baseline saved with {len(results)} benchmark results")
    
    def load_baseline(self, baseline_file: str = "performance_baseline.json"):
        """Load baseline results from file"""
        try:
            with open(baseline_file, 'r') as f:
                baseline_data = json.load(f)
            
            for benchmark_id, data in baseline_data.items():
                # Create minimal baseline result for comparison
                baseline_result = BenchmarkResult(
                    benchmark_id=benchmark_id,
                    benchmark_name=f"Baseline {benchmark_id}",
                    benchmark_type=BenchmarkType.RESPONSE_TIME,  # Default
                    start_time=datetime.fromisoformat(data["timestamp"]),
                    performance_score=data["performance_score"],
                    summary_statistics=data["summary_statistics"]
                )
                self.baseline_results[benchmark_id] = baseline_result
            
            print(f"Loaded baseline with {len(baseline_data)} benchmark results")
        
        except Exception as e:
            logging.warning(f"Could not load baseline: {e}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    import random
    
    async def run_performance_benchmarks():
        # Initialize performance benchmark engine
        engine = PerformanceBenchmarkEngine("http://localhost:3000")
        
        # Create default benchmarks
        engine.create_default_benchmarks()
        
        try:
            # Load existing baseline if available
            engine.load_baseline()
        except:
            pass
        
        print("Starting comprehensive performance benchmarks...")
        
        # Run all benchmarks
        report = await engine.run_all_benchmarks()
        
        # Save results as new baseline (optional)
        # engine.save_baseline(report.benchmark_results)
        
        # Generate detailed output
        print(f"\n=== Performance Benchmark Report ===")
        print(f"Overall Performance Score: {report.overall_performance_score:.1f}/100")
        print(f"Total Benchmarks: {report.total_benchmarks}")
        
        print(f"\nBenchmark Results:")
        for result in report.benchmark_results:
            print(f"  - {result.benchmark_name}: {result.result_status} ({result.performance_score:.1f})")
            
            if result.baseline_comparison:
                change = result.baseline_comparison["performance_score_change"]
                print(f"    Baseline comparison: {change:+.1f} points")
        
        print(f"\nSystem Performance Trends:")
        for metric, trend in report.performance_trends.items():
            if trend:
                print(f"  - {metric}: {trend[0]:.2f} → {trend[-1]:.2f}")
        
        print(f"\nRecommendations:")
        for rec in report.recommendations[:5]:
            print(f"  • {rec}")
        
        return report
    
    # Run the performance benchmarks
    asyncio.run(run_performance_benchmarks())