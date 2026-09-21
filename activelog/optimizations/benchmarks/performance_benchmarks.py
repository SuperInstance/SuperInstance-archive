"""
Comprehensive performance benchmarking suite for ActiveLog.
Provides detailed performance analysis and bottleneck identification.
"""
import asyncio
import time
import statistics
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import psutil
import aiohttp
import asyncpg
import aioredis
from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path
import subprocess
import sys
import os

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a benchmark test."""
    name: str
    duration: float
    success_rate: float
    throughput: float  # operations per second
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    max_response_time: float
    min_response_time: float
    error_count: int
    total_operations: int
    memory_usage: Dict[str, float]
    cpu_usage: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System resource usage metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: float
    disk_io_read: float
    disk_io_write: float
    network_io_sent: float
    network_io_recv: float


class SystemMonitor:
    """Monitors system resources during benchmarks."""
    
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.metrics: List[SystemMetrics] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._initial_disk_io = None
        self._initial_network_io = None
    
    async def start_monitoring(self):
        """Start monitoring system resources."""
        self._monitoring = True
        
        # Get initial values for cumulative metrics
        self._initial_disk_io = psutil.disk_io_counters()
        self._initial_network_io = psutil.net_io_counters()
        
        self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self):
        """Stop monitoring system resources."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self._monitoring:
                # Get current system metrics
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                network_io = psutil.net_io_counters()
                
                # Calculate differential metrics
                disk_read = disk_io.read_bytes - self._initial_disk_io.read_bytes if self._initial_disk_io else 0
                disk_write = disk_io.write_bytes - self._initial_disk_io.write_bytes if self._initial_disk_io else 0
                net_sent = network_io.bytes_sent - self._initial_network_io.bytes_sent if self._initial_network_io else 0
                net_recv = network_io.bytes_recv - self._initial_network_io.bytes_recv if self._initial_network_io else 0
                
                metrics = SystemMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=psutil.cpu_percent(interval=None),
                    memory_percent=memory.percent,
                    memory_used=memory.used / (1024 ** 3),  # GB
                    disk_io_read=disk_read / (1024 ** 2),  # MB
                    disk_io_write=disk_write / (1024 ** 2),  # MB
                    network_io_sent=net_sent / (1024 ** 2),  # MB
                    network_io_recv=net_recv / (1024 ** 2)  # MB
                )
                
                self.metrics.append(metrics)
                await asyncio.sleep(self.interval)
                
        except asyncio.CancelledError:
            pass
    
    def get_average_metrics(self) -> Dict[str, float]:
        """Get average metrics over the monitoring period."""
        if not self.metrics:
            return {}
        
        return {
            'avg_cpu_percent': statistics.mean(m.cpu_percent for m in self.metrics),
            'max_cpu_percent': max(m.cpu_percent for m in self.metrics),
            'avg_memory_percent': statistics.mean(m.memory_percent for m in self.metrics),
            'max_memory_used_gb': max(m.memory_used for m in self.metrics),
            'total_disk_read_mb': max(m.disk_io_read for m in self.metrics),
            'total_disk_write_mb': max(m.disk_io_write for m in self.metrics),
            'total_network_sent_mb': max(m.network_io_sent for m in self.metrics),
            'total_network_recv_mb': max(m.network_io_recv for m in self.metrics)
        }


class DatabaseBenchmark:
    """Database performance benchmarking."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def setup(self):
        """Setup database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=10,
            max_size=50
        )
    
    async def teardown(self):
        """Close database connections."""
        if self.pool:
            await self.pool.close()
    
    async def benchmark_simple_queries(self, iterations: int = 1000) -> BenchmarkResult:
        """Benchmark simple SELECT queries."""
        response_times = []
        errors = 0
        
        start_time = time.time()
        
        for _ in range(iterations):
            query_start = time.time()
            try:
                async with self.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                response_times.append(time.time() - query_start)
            except Exception as e:
                errors += 1
                logger.error(f"Query error: {e}")
        
        duration = time.time() - start_time
        
        return self._create_result(
            "database_simple_queries",
            response_times,
            errors,
            iterations,
            duration
        )
    
    async def benchmark_complex_queries(self, iterations: int = 500) -> BenchmarkResult:
        """Benchmark complex queries with joins."""
        response_times = []
        errors = 0
        
        # Complex query with multiple joins and aggregations
        complex_query = """
        SELECT 
            u.id,
            u.name,
            COUNT(f.id) as file_count,
            SUM(f.size) as total_size,
            AVG(f.size) as avg_size,
            MAX(f.updated_at) as last_updated
        FROM users u
        LEFT JOIN files f ON u.id = f.user_id AND f.deleted_at IS NULL
        LEFT JOIN file_metadata fm ON f.id = fm.file_id
        WHERE u.created_at > NOW() - INTERVAL '30 days'
        GROUP BY u.id, u.name
        ORDER BY total_size DESC
        LIMIT 100
        """
        
        start_time = time.time()
        
        for _ in range(iterations):
            query_start = time.time()
            try:
                async with self.pool.acquire() as conn:
                    await conn.fetch(complex_query)
                response_times.append(time.time() - query_start)
            except Exception as e:
                errors += 1
                logger.error(f"Complex query error: {e}")
        
        duration = time.time() - start_time
        
        return self._create_result(
            "database_complex_queries",
            response_times,
            errors,
            iterations,
            duration
        )
    
    async def benchmark_concurrent_operations(self, concurrency: int = 50, iterations: int = 1000) -> BenchmarkResult:
        """Benchmark concurrent database operations."""
        response_times = []
        errors = 0
        
        async def worker():
            nonlocal errors
            worker_times = []
            
            for _ in range(iterations // concurrency):
                query_start = time.time()
                try:
                    async with self.pool.acquire() as conn:
                        # Mix of operations
                        await conn.fetchval("SELECT COUNT(*) FROM users")
                        await conn.fetchval("SELECT COUNT(*) FROM files WHERE deleted_at IS NULL")
                    worker_times.append(time.time() - query_start)
                except Exception as e:
                    errors += 1
                    logger.error(f"Concurrent operation error: {e}")
            
            return worker_times
        
        start_time = time.time()
        
        # Run concurrent workers
        tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        
        # Collect response times
        for result in results:
            if isinstance(result, list):
                response_times.extend(result)
        
        return self._create_result(
            "database_concurrent_operations",
            response_times,
            errors,
            len(response_times),
            duration
        )
    
    def _create_result(self, name: str, response_times: List[float], errors: int, 
                      total_ops: int, duration: float) -> BenchmarkResult:
        """Create benchmark result from collected data."""
        if not response_times:
            response_times = [0.0]
        
        response_times.sort()
        
        return BenchmarkResult(
            name=name,
            duration=duration,
            success_rate=(total_ops - errors) / total_ops if total_ops > 0 else 0.0,
            throughput=total_ops / duration if duration > 0 else 0.0,
            avg_response_time=statistics.mean(response_times),
            p50_response_time=response_times[int(len(response_times) * 0.5)],
            p95_response_time=response_times[int(len(response_times) * 0.95)],
            p99_response_time=response_times[int(len(response_times) * 0.99)],
            max_response_time=max(response_times),
            min_response_time=min(response_times),
            error_count=errors,
            total_operations=total_ops,
            memory_usage={},
            cpu_usage=0.0
        )


class APIBenchmark:
    """API endpoint performance benchmarking."""
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def setup(self):
        """Setup HTTP session."""
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=50,
            keepalive_timeout=30
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
    
    async def teardown(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
    
    async def benchmark_endpoint(
        self,
        endpoint: str,
        method: str = 'GET',
        payload: Optional[Dict[str, Any]] = None,
        iterations: int = 1000,
        concurrency: int = 10
    ) -> BenchmarkResult:
        """Benchmark a specific API endpoint."""
        response_times = []
        errors = 0
        status_codes = {}
        
        async def worker():
            nonlocal errors, status_codes
            worker_times = []
            
            for _ in range(iterations // concurrency):
                request_start = time.time()
                try:
                    if method.upper() == 'GET':
                        async with self.session.get(f"{self.base_url}{endpoint}") as response:
                            await response.read()
                            status_codes[response.status] = status_codes.get(response.status, 0) + 1
                    elif method.upper() == 'POST':
                        async with self.session.post(f"{self.base_url}{endpoint}", json=payload) as response:
                            await response.read()
                            status_codes[response.status] = status_codes.get(response.status, 0) + 1
                    
                    worker_times.append(time.time() - request_start)
                except Exception as e:
                    errors += 1
                    logger.error(f"API request error: {e}")
            
            return worker_times
        
        start_time = time.time()
        
        # Run concurrent workers
        tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        
        # Collect response times
        for result in results:
            if isinstance(result, list):
                response_times.extend(result)
        
        result = self._create_api_result(
            f"api_{endpoint.replace('/', '_').strip('_')}",
            response_times,
            errors,
            len(response_times),
            duration
        )
        
        result.metadata['status_codes'] = status_codes
        return result
    
    async def benchmark_file_upload(
        self,
        endpoint: str,
        file_size_mb: int = 10,
        iterations: int = 50
    ) -> BenchmarkResult:
        """Benchmark file upload endpoint."""
        response_times = []
        errors = 0
        
        # Create test file data
        test_data = b'0' * (file_size_mb * 1024 * 1024)
        
        start_time = time.time()
        
        for _ in range(iterations):
            request_start = time.time()
            try:
                data = aiohttp.FormData()
                data.add_field('file', test_data, filename=f'test_{file_size_mb}mb.bin', 
                              content_type='application/octet-stream')
                
                async with self.session.post(f"{self.base_url}{endpoint}", data=data) as response:
                    await response.read()
                
                response_times.append(time.time() - request_start)
            except Exception as e:
                errors += 1
                logger.error(f"File upload error: {e}")
        
        duration = time.time() - start_time
        
        result = self._create_api_result(
            f"api_file_upload_{file_size_mb}mb",
            response_times,
            errors,
            iterations,
            duration
        )
        
        result.metadata['file_size_mb'] = file_size_mb
        return result
    
    def _create_api_result(self, name: str, response_times: List[float], errors: int,
                          total_ops: int, duration: float) -> BenchmarkResult:
        """Create API benchmark result."""
        if not response_times:
            response_times = [0.0]
        
        response_times.sort()
        
        return BenchmarkResult(
            name=name,
            duration=duration,
            success_rate=(total_ops - errors) / total_ops if total_ops > 0 else 0.0,
            throughput=total_ops / duration if duration > 0 else 0.0,
            avg_response_time=statistics.mean(response_times),
            p50_response_time=response_times[int(len(response_times) * 0.5)],
            p95_response_time=response_times[int(len(response_times) * 0.95)],
            p99_response_time=response_times[int(len(response_times) * 0.99)],
            max_response_time=max(response_times),
            min_response_time=min(response_times),
            error_count=errors,
            total_operations=total_ops,
            memory_usage={},
            cpu_usage=0.0
        )


class RedisBenchmark:
    """Redis performance benchmarking."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
    
    async def setup(self):
        """Setup Redis connection."""
        self.redis = aioredis.from_url(self.redis_url)
    
    async def teardown(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
    
    async def benchmark_basic_operations(self, iterations: int = 10000) -> BenchmarkResult:
        """Benchmark basic Redis operations (SET/GET)."""
        response_times = []
        errors = 0
        
        start_time = time.time()
        
        for i in range(iterations):
            op_start = time.time()
            try:
                # SET operation
                await self.redis.set(f"benchmark_key_{i}", f"value_{i}")
                # GET operation
                await self.redis.get(f"benchmark_key_{i}")
                response_times.append(time.time() - op_start)
            except Exception as e:
                errors += 1
                logger.error(f"Redis operation error: {e}")
        
        duration = time.time() - start_time
        
        # Cleanup
        try:
            keys = [f"benchmark_key_{i}" for i in range(iterations)]
            await self.redis.delete(*keys)
        except Exception:
            pass
        
        return self._create_redis_result(
            "redis_basic_operations",
            response_times,
            errors,
            iterations,
            duration
        )
    
    async def benchmark_pipeline_operations(self, iterations: int = 10000, pipeline_size: int = 100) -> BenchmarkResult:
        """Benchmark Redis pipeline operations."""
        response_times = []
        errors = 0
        
        start_time = time.time()
        
        for batch_start in range(0, iterations, pipeline_size):
            batch_end = min(batch_start + pipeline_size, iterations)
            pipeline_start = time.time()
            
            try:
                pipe = self.redis.pipeline()
                
                for i in range(batch_start, batch_end):
                    pipe.set(f"pipeline_key_{i}", f"value_{i}")
                    pipe.get(f"pipeline_key_{i}")
                
                await pipe.execute()
                response_times.append(time.time() - pipeline_start)
            except Exception as e:
                errors += 1
                logger.error(f"Redis pipeline error: {e}")
        
        duration = time.time() - start_time
        
        # Cleanup
        try:
            keys = [f"pipeline_key_{i}" for i in range(iterations)]
            await self.redis.delete(*keys)
        except Exception:
            pass
        
        return self._create_redis_result(
            "redis_pipeline_operations",
            response_times,
            errors,
            len(response_times),
            duration
        )
    
    def _create_redis_result(self, name: str, response_times: List[float], errors: int,
                           total_ops: int, duration: float) -> BenchmarkResult:
        """Create Redis benchmark result."""
        if not response_times:
            response_times = [0.0]
        
        response_times.sort()
        
        return BenchmarkResult(
            name=name,
            duration=duration,
            success_rate=(total_ops - errors) / total_ops if total_ops > 0 else 0.0,
            throughput=total_ops / duration if duration > 0 else 0.0,
            avg_response_time=statistics.mean(response_times),
            p50_response_time=response_times[int(len(response_times) * 0.5)],
            p95_response_time=response_times[int(len(response_times) * 0.95)],
            p99_response_time=response_times[int(len(response_times) * 0.99)],
            max_response_time=max(response_times),
            min_response_time=min(response_times),
            error_count=errors,
            total_operations=total_ops,
            memory_usage={},
            cpu_usage=0.0
        )


class ComprehensiveBenchmarkSuite:
    """Main benchmark suite that runs all performance tests."""
    
    def __init__(
        self,
        database_url: str,
        redis_url: str,
        api_base_url: str,
        auth_token: Optional[str] = None,
        output_dir: str = "benchmark_results"
    ):
        self.database_url = database_url
        self.redis_url = redis_url
        self.api_base_url = api_base_url
        self.auth_token = auth_token
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.db_benchmark = DatabaseBenchmark(database_url)
        self.redis_benchmark = RedisBenchmark(redis_url)
        self.api_benchmark = APIBenchmark(api_base_url, auth_token)
        self.system_monitor = SystemMonitor()
        
        self.results: List[BenchmarkResult] = []
    
    async def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run complete benchmark suite."""
        logger.info("Starting comprehensive benchmark suite")
        
        # Setup all benchmarks
        await self._setup_benchmarks()
        
        # Start system monitoring
        await self.system_monitor.start_monitoring()
        
        try:
            # Run database benchmarks
            await self._run_database_benchmarks()
            
            # Run Redis benchmarks
            await self._run_redis_benchmarks()
            
            # Run API benchmarks
            await self._run_api_benchmarks()
            
        finally:
            # Stop monitoring and cleanup
            await self.system_monitor.stop_monitoring()
            await self._teardown_benchmarks()
        
        # Add system metrics to results
        system_metrics = self.system_monitor.get_average_metrics()
        for result in self.results:
            result.memory_usage.update(system_metrics)
            result.cpu_usage = system_metrics.get('avg_cpu_percent', 0.0)
        
        # Generate reports
        await self._generate_reports()
        
        logger.info(f"Benchmark suite completed. {len(self.results)} tests run.")
        return self.results
    
    async def _setup_benchmarks(self):
        """Setup all benchmark instances."""
        await self.db_benchmark.setup()
        await self.redis_benchmark.setup()
        await self.api_benchmark.setup()
    
    async def _teardown_benchmarks(self):
        """Teardown all benchmark instances."""
        await self.db_benchmark.teardown()
        await self.redis_benchmark.teardown()
        await self.api_benchmark.teardown()
    
    async def _run_database_benchmarks(self):
        """Run all database benchmarks."""
        logger.info("Running database benchmarks...")
        
        tests = [
            self.db_benchmark.benchmark_simple_queries(iterations=2000),
            self.db_benchmark.benchmark_complex_queries(iterations=500),
            self.db_benchmark.benchmark_concurrent_operations(concurrency=20, iterations=1000)
        ]
        
        for test in tests:
            result = await test
            self.results.append(result)
            logger.info(f"Completed: {result.name} - Throughput: {result.throughput:.2f} ops/sec")
    
    async def _run_redis_benchmarks(self):
        """Run all Redis benchmarks."""
        logger.info("Running Redis benchmarks...")
        
        tests = [
            self.redis_benchmark.benchmark_basic_operations(iterations=5000),
            self.redis_benchmark.benchmark_pipeline_operations(iterations=5000, pipeline_size=50)
        ]
        
        for test in tests:
            result = await test
            self.results.append(result)
            logger.info(f"Completed: {result.name} - Throughput: {result.throughput:.2f} ops/sec")
    
    async def _run_api_benchmarks(self):
        """Run all API benchmarks."""
        logger.info("Running API benchmarks...")
        
        # Common API endpoints to benchmark
        endpoints = [
            ('/health', 'GET', None),
            ('/api/v1/users/me', 'GET', None),
            ('/api/v1/files', 'GET', None),
        ]
        
        for endpoint, method, payload in endpoints:
            try:
                result = await self.api_benchmark.benchmark_endpoint(
                    endpoint, method, payload, iterations=500, concurrency=10
                )
                self.results.append(result)
                logger.info(f"Completed: {result.name} - Throughput: {result.throughput:.2f} req/sec")
            except Exception as e:
                logger.error(f"Failed to benchmark {endpoint}: {e}")
        
        # File upload benchmark
        try:
            upload_result = await self.api_benchmark.benchmark_file_upload(
                '/api/v1/files/upload', file_size_mb=1, iterations=20
            )
            self.results.append(upload_result)
            logger.info(f"Completed: {upload_result.name} - Throughput: {upload_result.throughput:.2f} req/sec")
        except Exception as e:
            logger.error(f"Failed to benchmark file upload: {e}")
    
    async def _generate_reports(self):
        """Generate comprehensive benchmark reports."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON report
        json_report = {
            'timestamp': timestamp,
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024 ** 3),
                'python_version': sys.version
            },
            'results': [
                {
                    'name': r.name,
                    'duration': r.duration,
                    'success_rate': r.success_rate,
                    'throughput': r.throughput,
                    'avg_response_time': r.avg_response_time,
                    'p95_response_time': r.p95_response_time,
                    'p99_response_time': r.p99_response_time,
                    'error_count': r.error_count,
                    'total_operations': r.total_operations,
                    'memory_usage': r.memory_usage,
                    'cpu_usage': r.cpu_usage,
                    'metadata': r.metadata
                }
                for r in self.results
            ]
        }
        
        json_file = self.output_dir / f"benchmark_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(json_report, f, indent=2, default=str)
        
        # HTML report
        html_report = self._generate_html_report(json_report)
        html_file = self.output_dir / f"benchmark_report_{timestamp}.html"
        with open(html_file, 'w') as f:
            f.write(html_report)
        
        # Summary report
        summary_file = self.output_dir / f"benchmark_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(self._generate_summary_report())
        
        logger.info(f"Reports generated in {self.output_dir}")
    
    def _generate_html_report(self, json_data: Dict[str, Any]) -> str:
        """Generate HTML report."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ActiveLog Performance Benchmark Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .metric-good { color: green; }
                .metric-warning { color: orange; }
                .metric-bad { color: red; }
                .chart { margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1>ActiveLog Performance Benchmark Report</h1>
            <p><strong>Generated:</strong> {timestamp}</p>
            <p><strong>CPU Cores:</strong> {cpu_count}</p>
            <p><strong>Memory:</strong> {memory_total_gb:.1f} GB</p>
            
            <h2>Performance Summary</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Duration (s)</th>
                        <th>Success Rate</th>
                        <th>Throughput (ops/s)</th>
                        <th>Avg Response (ms)</th>
                        <th>P95 Response (ms)</th>
                        <th>P99 Response (ms)</th>
                        <th>Errors</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            
            <h2>System Resource Usage</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Avg CPU (%)</th>
                        <th>Max Memory (GB)</th>
                        <th>Disk I/O (MB)</th>
                        <th>Network I/O (MB)</th>
                    </tr>
                </thead>
                <tbody>
                    {resource_rows}
                </tbody>
            </table>
        </body>
        </html>
        """
        
        # Generate table rows
        table_rows = []
        resource_rows = []
        
        for result in json_data['results']:
            # Performance table row
            success_class = 'metric-good' if result['success_rate'] > 0.95 else 'metric-warning' if result['success_rate'] > 0.9 else 'metric-bad'
            throughput_class = 'metric-good' if result['throughput'] > 100 else 'metric-warning' if result['throughput'] > 50 else 'metric-bad'
            
            table_rows.append(f"""
                <tr>
                    <td>{result['name']}</td>
                    <td>{result['duration']:.2f}</td>
                    <td class="{success_class}">{result['success_rate']:.3f}</td>
                    <td class="{throughput_class}">{result['throughput']:.2f}</td>
                    <td>{result['avg_response_time'] * 1000:.2f}</td>
                    <td>{result['p95_response_time'] * 1000:.2f}</td>
                    <td>{result['p99_response_time'] * 1000:.2f}</td>
                    <td>{result['error_count']}</td>
                </tr>
            """)
            
            # Resource usage table row
            memory_usage = result.get('memory_usage', {})
            resource_rows.append(f"""
                <tr>
                    <td>{result['name']}</td>
                    <td>{result.get('cpu_usage', 0):.1f}</td>
                    <td>{memory_usage.get('max_memory_used_gb', 0):.2f}</td>
                    <td>{memory_usage.get('total_disk_read_mb', 0) + memory_usage.get('total_disk_write_mb', 0):.2f}</td>
                    <td>{memory_usage.get('total_network_sent_mb', 0) + memory_usage.get('total_network_recv_mb', 0):.2f}</td>
                </tr>
            """)
        
        return html_template.format(
            timestamp=json_data['timestamp'],
            cpu_count=json_data['system_info']['cpu_count'],
            memory_total_gb=json_data['system_info']['memory_total_gb'],
            table_rows=''.join(table_rows),
            resource_rows=''.join(resource_rows)
        )
    
    def _generate_summary_report(self) -> str:
        """Generate text summary report."""
        summary = []
        summary.append("ActiveLog Performance Benchmark Summary")
        summary.append("=" * 50)
        summary.append(f"Generated: {datetime.now()}")
        summary.append(f"Total Tests: {len(self.results)}")
        summary.append("")
        
        # Overall statistics
        total_ops = sum(r.total_operations for r in self.results)
        total_errors = sum(r.error_count for r in self.results)
        avg_success_rate = statistics.mean(r.success_rate for r in self.results)
        
        summary.append(f"Overall Success Rate: {avg_success_rate:.3f}")
        summary.append(f"Total Operations: {total_ops:,}")
        summary.append(f"Total Errors: {total_errors:,}")
        summary.append("")
        
        # Top performers
        summary.append("Top Performing Tests (by throughput):")
        sorted_results = sorted(self.results, key=lambda x: x.throughput, reverse=True)
        for i, result in enumerate(sorted_results[:5], 1):
            summary.append(f"  {i}. {result.name}: {result.throughput:.2f} ops/sec")
        
        summary.append("")
        summary.append("Slowest Tests (by avg response time):")
        sorted_by_time = sorted(self.results, key=lambda x: x.avg_response_time, reverse=True)
        for i, result in enumerate(sorted_by_time[:5], 1):
            summary.append(f"  {i}. {result.name}: {result.avg_response_time * 1000:.2f} ms")
        
        return "\n".join(summary)


# CLI interface
def main():
    """Main CLI interface for benchmarks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Performance Benchmark Suite")
    parser.add_argument('--database-url', required=True, help="Database connection URL")
    parser.add_argument('--redis-url', required=True, help="Redis connection URL")
    parser.add_argument('--api-url', required=True, help="API base URL")
    parser.add_argument('--auth-token', help="Authentication token for API")
    parser.add_argument('--output-dir', default="benchmark_results", help="Output directory")
    parser.add_argument('--log-level', default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run benchmarks
    suite = ComprehensiveBenchmarkSuite(
        database_url=args.database_url,
        redis_url=args.redis_url,
        api_base_url=args.api_url,
        auth_token=args.auth_token,
        output_dir=args.output_dir
    )
    
    results = asyncio.run(suite.run_all_benchmarks())
    
    # Print summary
    print(f"\nBenchmark completed! {len(results)} tests run.")
    print(f"Results saved to: {args.output_dir}")


if __name__ == "__main__":
    main()