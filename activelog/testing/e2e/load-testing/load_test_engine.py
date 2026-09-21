"""
Load Testing Engine for 10,000+ Concurrent Users

This module provides comprehensive load testing capabilities with realistic user
simulation, distributed testing, performance monitoring, and scalability analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
import json
import asyncio
import aiohttp
import time
import random
import statistics
import logging
from pathlib import Path
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil
import websockets
import ssl
from urllib.parse import urljoin, urlparse


class LoadTestType(Enum):
    """Types of load tests"""
    STRESS_TEST = "stress_test"  # Beyond normal capacity
    LOAD_TEST = "load_test"  # Normal expected load
    SPIKE_TEST = "spike_test"  # Sudden traffic spikes
    VOLUME_TEST = "volume_test"  # Large amounts of data
    ENDURANCE_TEST = "endurance_test"  # Extended periods
    CAPACITY_TEST = "capacity_test"  # Maximum capacity
    BREAKPOINT_TEST = "breakpoint_test"  # Find breaking point


class UserBehaviorPattern(Enum):
    """Different user behavior patterns"""
    LINEAR_RAMP = "linear_ramp"  # Steady increase
    EXPONENTIAL_RAMP = "exponential_ramp"  # Exponential growth
    STEP_RAMP = "step_ramp"  # Step increases
    CONSTANT_LOAD = "constant_load"  # Constant number
    WAVE_PATTERN = "wave_pattern"  # Periodic waves
    RANDOM_BURST = "random_burst"  # Random bursts
    REALISTIC_DAILY = "realistic_daily"  # Daily usage pattern


class RequestType(Enum):
    """Types of requests to simulate"""
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    HTTP_PUT = "http_put"
    HTTP_DELETE = "http_delete"
    WEBSOCKET = "websocket"
    GRAPHQL = "graphql"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    API_BATCH = "api_batch"


@dataclass
class LoadTestRequest:
    """Individual request definition"""
    request_id: str
    request_type: RequestType
    endpoint: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    data: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, str]] = None
    weight: float = 1.0  # Probability weight
    think_time: float = 1.0  # Seconds to wait after request
    timeout: float = 30.0
    expected_status: List[int] = field(default_factory=lambda: [200])


@dataclass
class VirtualUser:
    """Virtual user simulation"""
    user_id: str
    session_id: str
    user_type: str
    requests: List[LoadTestRequest]
    session_data: Dict[str, Any] = field(default_factory=dict)
    auth_token: Optional[str] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    current_request_index: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class LoadTestScenario:
    """Load test scenario definition"""
    scenario_id: str
    name: str
    description: str
    test_type: LoadTestType
    max_concurrent_users: int
    ramp_up_pattern: UserBehaviorPattern
    test_duration: float  # seconds
    target_endpoints: List[str]
    user_requests: List[LoadTestRequest]
    think_time_range: Tuple[float, float] = (1.0, 5.0)
    authentication: Optional[Dict[str, Any]] = None
    test_data: Optional[Dict[str, Any]] = None
    success_criteria: Dict[str, float] = field(default_factory=lambda: {
        "max_response_time": 5.0,
        "max_error_rate": 5.0,
        "min_throughput": 100.0
    })


@dataclass
class LoadTestMetrics:
    """Performance metrics collected during test"""
    scenario_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    concurrent_users: int = 0
    max_concurrent_users: int = 0
    response_times: List[float] = field(default_factory=list)
    throughput_per_second: List[float] = field(default_factory=list)
    error_rates: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    network_io: List[Dict[str, float]] = field(default_factory=list)
    endpoint_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error_breakdown: Dict[str, int] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, LoadTestMetrics] = {}
        self.collection_interval = 1.0  # seconds
        self.system_monitor = SystemMonitor()
    
    def start_collection(self, scenario_id: str) -> LoadTestMetrics:
        """Start collecting metrics for a scenario"""
        metrics = LoadTestMetrics(
            scenario_id=scenario_id,
            start_time=datetime.now()
        )
        self.metrics[scenario_id] = metrics
        return metrics
    
    def record_request(self, scenario_id: str, request_id: str, response_time: float,
                      status_code: int, error: Optional[str] = None):
        """Record individual request metrics"""
        if scenario_id not in self.metrics:
            return
        
        metrics = self.metrics[scenario_id]
        metrics.total_requests += 1
        
        if error or status_code >= 400:
            metrics.failed_requests += 1
            if error:
                metrics.error_breakdown[error] = metrics.error_breakdown.get(error, 0) + 1
        else:
            metrics.successful_requests += 1
        
        metrics.response_times.append(response_time)
        
        # Update endpoint-specific metrics
        if request_id not in metrics.endpoint_metrics:
            metrics.endpoint_metrics[request_id] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "response_times": [],
                "avg_response_time": 0,
                "min_response_time": float('inf'),
                "max_response_time": 0
            }
        
        endpoint_metrics = metrics.endpoint_metrics[request_id]
        endpoint_metrics["total_requests"] += 1
        endpoint_metrics["response_times"].append(response_time)
        
        if error or status_code >= 400:
            endpoint_metrics["failed_requests"] += 1
        else:
            endpoint_metrics["successful_requests"] += 1
        
        # Update response time stats
        endpoint_metrics["min_response_time"] = min(endpoint_metrics["min_response_time"], response_time)
        endpoint_metrics["max_response_time"] = max(endpoint_metrics["max_response_time"], response_time)
        endpoint_metrics["avg_response_time"] = statistics.mean(endpoint_metrics["response_times"])
    
    def record_user_count(self, scenario_id: str, concurrent_users: int):
        """Record current concurrent user count"""
        if scenario_id not in self.metrics:
            return
        
        metrics = self.metrics[scenario_id]
        metrics.concurrent_users = concurrent_users
        metrics.max_concurrent_users = max(metrics.max_concurrent_users, concurrent_users)
    
    def record_system_metrics(self, scenario_id: str):
        """Record current system metrics"""
        if scenario_id not in self.metrics:
            return
        
        system_stats = self.system_monitor.get_current_stats()
        metrics = self.metrics[scenario_id]
        
        metrics.cpu_usage.append(system_stats["cpu_percent"])
        metrics.memory_usage.append(system_stats["memory_percent"])
        metrics.network_io.append({
            "bytes_sent": system_stats["network_sent"],
            "bytes_recv": system_stats["network_recv"]
        })
    
    def calculate_throughput(self, scenario_id: str, time_window: float = 1.0):
        """Calculate current throughput (requests per second)"""
        if scenario_id not in self.metrics:
            return 0.0
        
        metrics = self.metrics[scenario_id]
        if not metrics.response_times:
            return 0.0
        
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        # Count requests in the time window (simplified)
        recent_requests = len([t for t in metrics.response_times[-100:]])  # Last 100 requests
        return recent_requests / time_window
    
    def get_summary_stats(self, scenario_id: str) -> Dict[str, Any]:
        """Get summary statistics for a scenario"""
        if scenario_id not in self.metrics:
            return {}
        
        metrics = self.metrics[scenario_id]
        
        if not metrics.response_times:
            return {"error": "No data available"}
        
        response_times = metrics.response_times
        total_time = (metrics.end_time - metrics.start_time).total_seconds() if metrics.end_time else 0
        
        return {
            "scenario_id": scenario_id,
            "duration": total_time,
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "success_rate": (metrics.successful_requests / metrics.total_requests) * 100 if metrics.total_requests > 0 else 0,
            "max_concurrent_users": metrics.max_concurrent_users,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p50_response_time": statistics.median(response_times),
            "p90_response_time": statistics.quantiles(response_times, n=10)[8] if len(response_times) >= 10 else max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
            "p99_response_time": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times),
            "requests_per_second": metrics.total_requests / total_time if total_time > 0 else 0,
            "avg_cpu_usage": statistics.mean(metrics.cpu_usage) if metrics.cpu_usage else 0,
            "avg_memory_usage": statistics.mean(metrics.memory_usage) if metrics.memory_usage else 0,
            "error_breakdown": metrics.error_breakdown,
            "endpoint_performance": {
                endpoint: {
                    "total_requests": data["total_requests"],
                    "success_rate": (data["successful_requests"] / data["total_requests"]) * 100 if data["total_requests"] > 0 else 0,
                    "avg_response_time": data["avg_response_time"],
                    "min_response_time": data["min_response_time"] if data["min_response_time"] != float('inf') else 0,
                    "max_response_time": data["max_response_time"]
                }
                for endpoint, data in metrics.endpoint_metrics.items()
            }
        }


class SystemMonitor:
    """Monitors system resources during load testing"""
    
    def __init__(self):
        self.process = psutil.Process()
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            network = psutil.net_io_counters()
            disk = psutil.disk_io_counters()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "network_sent": network.bytes_sent if network else 0,
                "network_recv": network.bytes_recv if network else 0,
                "disk_read": disk.read_bytes if disk else 0,
                "disk_write": disk.write_bytes if disk else 0,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
                "cpu_cores": psutil.cpu_count(),
                "timestamp": time.time()
            }
        except Exception as e:
            logging.error(f"Error collecting system stats: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_used_gb": 0,
                "memory_available_gb": 0,
                "network_sent": 0,
                "network_recv": 0,
                "disk_read": 0,
                "disk_write": 0,
                "load_average": 0,
                "cpu_cores": 1,
                "timestamp": time.time()
            }


class UserSimulator:
    """Simulates virtual user behavior"""
    
    def __init__(self, base_url: str, ssl_verify: bool = False):
        self.base_url = base_url.rstrip('/')
        self.ssl_verify = ssl_verify
        self.session_timeout = aiohttp.ClientTimeout(total=30)
    
    async def simulate_user(self, user: VirtualUser, metrics_collector: MetricsCollector,
                           scenario_id: str) -> VirtualUser:
        """Simulate a virtual user session"""
        user.start_time = datetime.now()
        
        connector = aiohttp.TCPConnector(ssl=ssl.create_default_context() if self.ssl_verify else False)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=self.session_timeout,
            cookies=user.cookies
        ) as session:
            
            # Authenticate if needed
            if user.auth_token:
                session.headers.update({"Authorization": f"Bearer {user.auth_token}"})
            
            # Execute user requests
            for request in user.requests:
                if user.end_time:  # User session ended
                    break
                
                try:
                    await self._execute_request(
                        session, request, user, metrics_collector, scenario_id
                    )
                    
                    # Think time between requests
                    think_time = random.uniform(
                        request.think_time * 0.5, request.think_time * 1.5
                    )
                    await asyncio.sleep(think_time)
                    
                except Exception as e:
                    user.errors.append({
                        "request_id": request.request_id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    user.failed_requests += 1
                    
                    metrics_collector.record_request(
                        scenario_id, request.request_id, 0, 500, str(e)
                    )
        
        user.end_time = datetime.now()
        return user
    
    async def _execute_request(self, session: aiohttp.ClientSession, 
                             request: LoadTestRequest, user: VirtualUser,
                             metrics_collector: MetricsCollector, scenario_id: str):
        """Execute individual request"""
        url = urljoin(self.base_url, request.endpoint)
        start_time = time.time()
        
        # Replace template variables in URL and data
        url = self._replace_template_vars(url, user.session_data)
        request_data = self._replace_template_vars(request.data, user.session_data) if request.data else None
        
        try:
            if request.request_type == RequestType.HTTP_GET:
                async with session.get(url, headers=request.headers) as response:
                    await response.read()
                    status = response.status
            
            elif request.request_type == RequestType.HTTP_POST:
                async with session.post(url, json=request_data, headers=request.headers) as response:
                    response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    status = response.status
                    
                    # Store response data for later requests
                    if isinstance(response_data, dict):
                        user.session_data.update(response_data)
            
            elif request.request_type == RequestType.HTTP_PUT:
                async with session.put(url, json=request_data, headers=request.headers) as response:
                    await response.read()
                    status = response.status
            
            elif request.request_type == RequestType.HTTP_DELETE:
                async with session.delete(url, headers=request.headers) as response:
                    await response.read()
                    status = response.status
            
            elif request.request_type == RequestType.FILE_UPLOAD:
                # Simulate file upload
                file_data = aiohttp.FormData()
                if request.files:
                    for field_name, file_path in request.files.items():
                        file_data.add_field(field_name, b'test file content', filename='test.txt')
                
                async with session.post(url, data=file_data, headers=request.headers) as response:
                    await response.read()
                    status = response.status
            
            elif request.request_type == RequestType.WEBSOCKET:
                # Simulate WebSocket connection
                await self._simulate_websocket(url, request, user)
                status = 200  # WebSocket success
            
            else:
                # Default to GET
                async with session.get(url, headers=request.headers) as response:
                    await response.read()
                    status = response.status
            
            response_time = time.time() - start_time
            user.total_requests += 1
            user.response_times.append(response_time)
            
            # Check if status is expected
            error = None
            if status not in request.expected_status:
                error = f"Unexpected status code: {status}"
                user.failed_requests += 1
            
            # Record metrics
            metrics_collector.record_request(
                scenario_id, request.request_id, response_time, status, error
            )
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            user.failed_requests += 1
            user.errors.append({
                "request_id": request.request_id,
                "error": "Request timeout",
                "timestamp": datetime.now().isoformat()
            })
            metrics_collector.record_request(
                scenario_id, request.request_id, response_time, 408, "Request timeout"
            )
        
        except Exception as e:
            response_time = time.time() - start_time
            user.failed_requests += 1
            user.errors.append({
                "request_id": request.request_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            metrics_collector.record_request(
                scenario_id, request.request_id, response_time, 500, str(e)
            )
    
    async def _simulate_websocket(self, url: str, request: LoadTestRequest, user: VirtualUser):
        """Simulate WebSocket connection"""
        ws_url = url.replace('http://', 'ws://').replace('https://', 'wss://')
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send test message
                test_message = request.data or {"type": "test", "user_id": user.user_id}
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                
                # Store response in session data
                try:
                    response_data = json.loads(response)
                    if isinstance(response_data, dict):
                        user.session_data.update(response_data)
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            raise Exception(f"WebSocket error: {e}")
    
    def _replace_template_vars(self, data: Any, session_data: Dict[str, Any]) -> Any:
        """Replace template variables in data"""
        if isinstance(data, str):
            for key, value in session_data.items():
                data = data.replace(f"{{{key}}}", str(value))
            return data
        elif isinstance(data, dict):
            return {k: self._replace_template_vars(v, session_data) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_template_vars(item, session_data) for item in data]
        return data


class LoadTestEngine:
    """Main load testing engine"""
    
    def __init__(self, target_url: str, max_workers: int = None):
        self.target_url = target_url
        self.max_workers = max_workers or min(32, (multiprocessing.cpu_count() or 1) + 4)
        self.metrics_collector = MetricsCollector()
        self.user_simulator = UserSimulator(target_url)
        self.active_scenarios: Dict[str, bool] = {}
        self.scenario_tasks: Dict[str, List[asyncio.Task]] = {}
        
    async def run_load_test(self, scenario: LoadTestScenario) -> Dict[str, Any]:
        """Run a complete load test scenario"""
        print(f"Starting load test: {scenario.name}")
        print(f"Target: {scenario.max_concurrent_users} concurrent users")
        print(f"Duration: {scenario.test_duration} seconds")
        
        # Start metrics collection
        metrics = self.metrics_collector.start_collection(scenario.scenario_id)
        self.active_scenarios[scenario.scenario_id] = True
        
        # Start system monitoring task
        monitoring_task = asyncio.create_task(
            self._monitor_system_resources(scenario.scenario_id, scenario.test_duration)
        )
        
        try:
            # Generate user ramp-up schedule
            user_schedule = self._generate_user_schedule(scenario)
            
            # Execute load test
            await self._execute_load_test(scenario, user_schedule)
            
        finally:
            # Stop scenario
            self.active_scenarios[scenario.scenario_id] = False
            
            # Wait for monitoring to finish
            try:
                await asyncio.wait_for(monitoring_task, timeout=5.0)
            except asyncio.TimeoutError:
                monitoring_task.cancel()
            
            # Finalize metrics
            metrics.end_time = datetime.now()
            
            # Generate report
            summary = self.metrics_collector.get_summary_stats(scenario.scenario_id)
            
            print(f"Load test completed: {scenario.name}")
            print(f"Total requests: {summary.get('total_requests', 0)}")
            print(f"Success rate: {summary.get('success_rate', 0):.1f}%")
            print(f"Average response time: {summary.get('avg_response_time', 0):.3f}s")
            print(f"P95 response time: {summary.get('p95_response_time', 0):.3f}s")
            print(f"Requests/second: {summary.get('requests_per_second', 0):.1f}")
            
            return summary
    
    def _generate_user_schedule(self, scenario: LoadTestScenario) -> List[Tuple[float, int]]:
        """Generate user ramp-up schedule"""
        schedule = []
        max_users = scenario.max_concurrent_users
        duration = scenario.test_duration
        pattern = scenario.ramp_up_pattern
        
        if pattern == UserBehaviorPattern.LINEAR_RAMP:
            # Linear increase to max users over first 20% of duration
            ramp_duration = duration * 0.2
            step_interval = ramp_duration / max_users
            
            for i in range(1, max_users + 1):
                schedule.append((i * step_interval, i))
            
            # Maintain max users for remaining duration
            schedule.append((duration, max_users))
        
        elif pattern == UserBehaviorPattern.STEP_RAMP:
            # Step increases every 10% of duration
            steps = 10
            step_duration = duration / steps
            users_per_step = max_users / steps
            
            for i in range(1, steps + 1):
                schedule.append((i * step_duration, int(i * users_per_step)))
        
        elif pattern == UserBehaviorPattern.EXPONENTIAL_RAMP:
            # Exponential growth
            import math
            ramp_duration = duration * 0.3
            
            for i in range(1, 21):  # 20 steps
                time_point = (i / 20) * ramp_duration
                user_count = int(max_users * (math.exp(i / 20) - 1) / (math.exp(1) - 1))
                schedule.append((time_point, min(user_count, max_users)))
            
            schedule.append((duration, max_users))
        
        elif pattern == UserBehaviorPattern.CONSTANT_LOAD:
            # Immediate constant load
            schedule.append((0, max_users))
            schedule.append((duration, max_users))
        
        elif pattern == UserBehaviorPattern.SPIKE_TEST:
            # Quick ramp to max, then back down
            spike_duration = duration * 0.1
            schedule.append((spike_duration, max_users))
            schedule.append((spike_duration + 60, max_users // 2))  # Drop to half
            schedule.append((duration, max_users // 4))  # Drop to quarter
        
        elif pattern == UserBehaviorPattern.WAVE_PATTERN:
            # Sinusoidal wave pattern
            import math
            steps = 20
            for i in range(steps):
                time_point = (i / steps) * duration
                # Wave between 25% and 100% of max users
                user_count = int(max_users * 0.25 + max_users * 0.75 * (1 + math.sin(2 * math.pi * i / steps)) / 2)
                schedule.append((time_point, user_count))
        
        else:
            # Default to linear ramp
            schedule.append((duration * 0.2, max_users))
            schedule.append((duration, max_users))
        
        return schedule
    
    async def _execute_load_test(self, scenario: LoadTestScenario, 
                               user_schedule: List[Tuple[float, int]]):
        """Execute the load test with user ramp-up"""
        start_time = time.time()
        current_users = 0
        user_tasks: List[asyncio.Task] = []
        self.scenario_tasks[scenario.scenario_id] = user_tasks
        
        # Process user schedule
        schedule_index = 0
        
        while (time.time() - start_time) < scenario.test_duration and self.active_scenarios.get(scenario.scenario_id, False):
            current_time = time.time() - start_time
            
            # Check if we need to adjust user count
            if schedule_index < len(user_schedule) and current_time >= user_schedule[schedule_index][0]:
                target_users = user_schedule[schedule_index][1]
                
                if target_users > current_users:
                    # Add more users
                    for _ in range(target_users - current_users):
                        user = self._create_virtual_user(scenario, len(user_tasks))
                        task = asyncio.create_task(
                            self.user_simulator.simulate_user(
                                user, self.metrics_collector, scenario.scenario_id
                            )
                        )
                        user_tasks.append(task)
                        current_users += 1
                
                elif target_users < current_users:
                    # Remove users (let some finish naturally)
                    users_to_remove = current_users - target_users
                    for i in range(min(users_to_remove, len(user_tasks))):
                        if not user_tasks[i].done():
                            user_tasks[i].cancel()
                    current_users = target_users
                
                self.metrics_collector.record_user_count(scenario.scenario_id, current_users)
                schedule_index += 1
            
            # Clean up completed tasks
            user_tasks = [task for task in user_tasks if not task.done()]
            
            # Brief pause
            await asyncio.sleep(1)
        
        # Wait for all users to complete
        if user_tasks:
            print(f"Waiting for {len(user_tasks)} users to complete...")
            await asyncio.gather(*user_tasks, return_exceptions=True)
    
    def _create_virtual_user(self, scenario: LoadTestScenario, user_index: int) -> VirtualUser:
        """Create a virtual user for the scenario"""
        user_id = f"user_{scenario.scenario_id}_{user_index}_{int(time.time())}"
        
        # Create session data with unique identifiers
        session_data = {
            "user_id": user_id,
            "session_id": f"session_{user_index}",
            "timestamp": int(time.time()),
            "random_id": random.randint(1000, 9999)
        }
        
        # Add test data if provided
        if scenario.test_data:
            session_data.update(scenario.test_data)
        
        # Authenticate if needed
        auth_token = None
        if scenario.authentication:
            # Simplified authentication - in real scenario, would make auth request
            auth_token = f"test_token_{user_index}"
        
        # Shuffle and weight requests based on probability
        weighted_requests = []
        for request in scenario.user_requests:
            # Add multiple copies based on weight
            copies = int(request.weight * 10)  # Scale weight to number of copies
            weighted_requests.extend([request] * max(1, copies))
        
        random.shuffle(weighted_requests)
        
        return VirtualUser(
            user_id=user_id,
            session_id=session_data["session_id"],
            user_type="load_test_user",
            requests=weighted_requests[:50],  # Limit to 50 requests per user
            session_data=session_data,
            auth_token=auth_token
        )
    
    async def _monitor_system_resources(self, scenario_id: str, duration: float):
        """Monitor system resources during test"""
        start_time = time.time()
        
        while (time.time() - start_time) < duration and self.active_scenarios.get(scenario_id, False):
            self.metrics_collector.record_system_metrics(scenario_id)
            await asyncio.sleep(self.metrics_collector.collection_interval)
    
    async def run_breakpoint_test(self, base_scenario: LoadTestScenario, 
                                max_users: int = 50000, step_size: int = 1000) -> Dict[str, Any]:
        """Find the breaking point by gradually increasing load"""
        print(f"Starting breakpoint test - finding maximum capacity")
        
        results = []
        current_users = step_size
        
        while current_users <= max_users:
            print(f"Testing {current_users} concurrent users...")
            
            # Create test scenario
            test_scenario = LoadTestScenario(
                scenario_id=f"breakpoint_{current_users}",
                name=f"Breakpoint Test - {current_users} users",
                description=f"Testing {current_users} concurrent users",
                test_type=LoadTestType.BREAKPOINT_TEST,
                max_concurrent_users=current_users,
                ramp_up_pattern=UserBehaviorPattern.LINEAR_RAMP,
                test_duration=120,  # 2 minutes per test
                target_endpoints=base_scenario.target_endpoints,
                user_requests=base_scenario.user_requests,
                success_criteria=base_scenario.success_criteria
            )
            
            # Run test
            result = await self.run_load_test(test_scenario)
            results.append({
                "concurrent_users": current_users,
                "success_rate": result.get("success_rate", 0),
                "avg_response_time": result.get("avg_response_time", 0),
                "p95_response_time": result.get("p95_response_time", 0),
                "requests_per_second": result.get("requests_per_second", 0),
                "cpu_usage": result.get("avg_cpu_usage", 0),
                "memory_usage": result.get("avg_memory_usage", 0)
            })
            
            # Check if we've hit the breaking point
            if (result.get("success_rate", 0) < 95 or 
                result.get("p95_response_time", 0) > base_scenario.success_criteria.get("max_response_time", 5.0)):
                print(f"Breaking point found at {current_users} users")
                break
            
            current_users += step_size
            
            # Brief pause between tests
            await asyncio.sleep(30)
        
        return {
            "breaking_point": current_users - step_size if current_users > step_size else current_users,
            "test_results": results,
            "summary": {
                "max_stable_users": max([r for r in results if r["success_rate"] >= 95], 
                                      key=lambda x: x["concurrent_users"], default={"concurrent_users": 0})["concurrent_users"],
                "peak_throughput": max(results, key=lambda x: x["requests_per_second"])["requests_per_second"] if results else 0
            }
        }
    
    def cleanup(self):
        """Clean up resources"""
        # Cancel all running scenarios
        for scenario_id in self.active_scenarios:
            self.active_scenarios[scenario_id] = False
        
        # Cancel scenario tasks
        for tasks in self.scenario_tasks.values():
            for task in tasks:
                if not task.done():
                    task.cancel()


# Pre-built load test scenarios for ActiveLog platform
def create_default_scenarios() -> List[LoadTestScenario]:
    """Create default load test scenarios for ActiveLog"""
    
    scenarios = []
    
    # Standard load test - 10,000 users
    standard_load = LoadTestScenario(
        scenario_id="standard_load_10k",
        name="Standard Load Test - 10,000 Users",
        description="Test normal expected load with 10,000 concurrent users",
        test_type=LoadTestType.LOAD_TEST,
        max_concurrent_users=10000,
        ramp_up_pattern=UserBehaviorPattern.LINEAR_RAMP,
        test_duration=1800,  # 30 minutes
        target_endpoints=[
            "http://localhost:3000",
            "http://localhost:8000/api",
            "http://localhost:8216"
        ],
        user_requests=[
            LoadTestRequest("home_page", RequestType.HTTP_GET, "/", weight=3.0),
            LoadTestRequest("login", RequestType.HTTP_POST, "/auth/login", 
                          data={"username": "testuser{random_id}", "password": "password"}, weight=2.0),
            LoadTestRequest("dashboard", RequestType.HTTP_GET, "/dashboard", weight=2.5),
            LoadTestRequest("api_status", RequestType.HTTP_GET, "/api/health", weight=1.0),
            LoadTestRequest("tutorial_start", RequestType.HTTP_GET, "/tutorials/start", weight=1.5),
            LoadTestRequest("create_content", RequestType.HTTP_POST, "/api/content",
                          data={"title": "Test Content {timestamp}", "body": "Test content body"}, weight=1.0),
            LoadTestRequest("websocket_connect", RequestType.WEBSOCKET, "/ws", weight=0.5)
        ],
        success_criteria={
            "max_response_time": 5.0,
            "max_error_rate": 2.0,
            "min_throughput": 1000.0
        }
    )
    scenarios.append(standard_load)
    
    # Stress test - 25,000 users
    stress_test = LoadTestScenario(
        scenario_id="stress_test_25k",
        name="Stress Test - 25,000 Users",
        description="Stress test with 25,000 concurrent users",
        test_type=LoadTestType.STRESS_TEST,
        max_concurrent_users=25000,
        ramp_up_pattern=UserBehaviorPattern.EXPONENTIAL_RAMP,
        test_duration=2400,  # 40 minutes
        target_endpoints=["http://localhost:3000", "http://localhost:8000/api"],
        user_requests=[
            LoadTestRequest("home_page", RequestType.HTTP_GET, "/", weight=2.0),
            LoadTestRequest("api_heavy", RequestType.HTTP_GET, "/api/data/heavy", weight=1.0),
            LoadTestRequest("search", RequestType.HTTP_GET, "/api/search?q=test{random_id}", weight=1.5),
            LoadTestRequest("user_profile", RequestType.HTTP_GET, "/api/users/profile", weight=1.0)
        ],
        success_criteria={
            "max_response_time": 10.0,
            "max_error_rate": 5.0,
            "min_throughput": 500.0
        }
    )
    scenarios.append(stress_test)
    
    # Spike test
    spike_test = LoadTestScenario(
        scenario_id="spike_test",
        name="Spike Test - Traffic Burst",
        description="Test sudden traffic spikes",
        test_type=LoadTestType.SPIKE_TEST,
        max_concurrent_users=15000,
        ramp_up_pattern=UserBehaviorPattern.SPIKE_TEST,
        test_duration=900,  # 15 minutes
        target_endpoints=["http://localhost:3000"],
        user_requests=[
            LoadTestRequest("home_page", RequestType.HTTP_GET, "/", weight=5.0),
            LoadTestRequest("popular_content", RequestType.HTTP_GET, "/content/popular", weight=3.0),
            LoadTestRequest("search", RequestType.HTTP_GET, "/search", weight=2.0)
        ],
        success_criteria={
            "max_response_time": 8.0,
            "max_error_rate": 10.0,
            "min_throughput": 800.0
        }
    )
    scenarios.append(spike_test)
    
    return scenarios


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def run_load_tests():
        # Initialize load test engine
        engine = LoadTestEngine("http://localhost:3000")
        
        try:
            # Create scenarios
            scenarios = create_default_scenarios()
            
            print("Available load test scenarios:")
            for scenario in scenarios:
                print(f"- {scenario.name}: {scenario.max_concurrent_users} users, {scenario.test_duration}s")
            
            # Run a smaller test first
            test_scenario = LoadTestScenario(
                scenario_id="quick_test",
                name="Quick Load Test",
                description="Quick test with 100 users",
                test_type=LoadTestType.LOAD_TEST,
                max_concurrent_users=100,
                ramp_up_pattern=UserBehaviorPattern.LINEAR_RAMP,
                test_duration=60,  # 1 minute
                target_endpoints=["http://localhost:3000"],
                user_requests=[
                    LoadTestRequest("home_page", RequestType.HTTP_GET, "/", weight=2.0),
                    LoadTestRequest("api_health", RequestType.HTTP_GET, "/health", weight=1.0)
                ]
            )
            
            # Run the test
            result = await engine.run_load_test(test_scenario)
            
            print("\n=== Load Test Results ===")
            print(f"Total Requests: {result['total_requests']}")
            print(f"Success Rate: {result['success_rate']:.1f}%")
            print(f"Average Response Time: {result['avg_response_time']:.3f}s")
            print(f"P95 Response Time: {result['p95_response_time']:.3f}s")
            print(f"Requests/Second: {result['requests_per_second']:.1f}")
            print(f"Max Concurrent Users: {result['max_concurrent_users']}")
            
        finally:
            engine.cleanup()
    
    # Run the load tests
    asyncio.run(run_load_tests())