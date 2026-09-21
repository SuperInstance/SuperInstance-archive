#!/usr/bin/env python3
"""
Advanced Load Balancer for SuperInstance ML Ecosystem
Handles intelligent request distribution, health monitoring, and auto-scaling
"""

import asyncio
import time
import logging
import hashlib
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import aiohttp
import psutil
from collections import defaultdict, deque

# Initialize logger
logger = logging.getLogger(__name__)

class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    RESOURCE_AWARE = "resource_aware"
    ML_OPTIMIZED = "ml_optimized"

@dataclass
class ServerInstance:
    """Represents a backend server instance"""
    id: str
    host: str
    port: int
    weight: float = 1.0
    max_connections: int = 1000
    current_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_health_check: float = 0.0
    health_status: str = "unknown"  # healthy, unhealthy, draining
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    ml_model_load: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    
    @property
    def is_healthy(self) -> bool:
        return self.health_status == "healthy"
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.failed_requests) / self.total_requests
    
    @property
    def load_score(self) -> float:
        """Calculate overall load score (lower is better)"""
        connection_load = self.current_connections / self.max_connections
        cpu_load = self.cpu_usage / 100.0
        memory_load = self.memory_usage / 100.0
        ml_load = self.ml_model_load / 100.0
        
        # Weighted average with emphasis on connections and ML load
        return (connection_load * 0.4 + cpu_load * 0.2 + 
                memory_load * 0.2 + ml_load * 0.2)

@dataclass
class LoadBalancerConfig:
    """Configuration for load balancer"""
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ML_OPTIMIZED
    health_check_interval: int = 30  # seconds
    health_check_timeout: int = 5    # seconds
    max_retries: int = 3
    retry_delay: float = 1.0
    connection_timeout: int = 30
    enable_sticky_sessions: bool = False
    session_timeout: int = 3600  # 1 hour
    circuit_breaker_threshold: float = 0.5  # 50% failure rate
    circuit_breaker_timeout: int = 60  # 1 minute
    auto_scale_enabled: bool = True
    scale_up_threshold: float = 0.8   # 80% capacity
    scale_down_threshold: float = 0.3  # 30% capacity
    min_instances: int = 2
    max_instances: int = 20

class CircuitBreaker:
    """Circuit breaker for handling server failures"""
    
    def __init__(self, failure_threshold: float = 0.5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open
    
    def record_success(self):
        self.success_count += 1
        if self.state == "half_open" and self.success_count >= 3:
            self.state = "closed"
            self.failure_count = 0
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        total_requests = self.failure_count + self.success_count
        if total_requests > 10:  # Minimum sample size
            failure_rate = self.failure_count / total_requests
            if failure_rate >= self.failure_threshold:
                self.state = "open"
    
    def can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = "half_open"
                return True
            return False
        else:  # half_open
            return True

class LoadBalancer:
    """Advanced load balancer with ML optimization"""
    
    def __init__(self, config: LoadBalancerConfig):
        self.config = config
        self.servers: Dict[str, ServerInstance] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.sticky_sessions: Dict[str, str] = {}  # session_id -> server_id
        self.request_history = deque(maxlen=1000)
        self.round_robin_index = 0
        self.running = False
        
        # ML-based optimization
        self.server_performance_history = defaultdict(list)
        self.request_patterns = defaultdict(int)
        self.optimization_weights = {
            'response_time': 0.3,
            'success_rate': 0.25,
            'load_score': 0.25,
            'capability_match': 0.2
        }
    
    async def initialize(self):
        """Initialize the load balancer"""
        logger.info("Initializing SuperInstance Load Balancer")
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._metrics_collection_loop())
        asyncio.create_task(self._auto_scale_loop())
        asyncio.create_task(self._cleanup_loop())
        
        logger.info("Load balancer initialized successfully")
    
    def add_server(self, server: ServerInstance):
        """Add a server to the load balancer"""
        self.servers[server.id] = server
        self.circuit_breakers[server.id] = CircuitBreaker(
            self.config.circuit_breaker_threshold,
            self.config.circuit_breaker_timeout
        )
        logger.info(f"Added server {server.id} ({server.host}:{server.port})")
    
    def remove_server(self, server_id: str):
        """Remove a server from the load balancer"""
        if server_id in self.servers:
            del self.servers[server_id]
            del self.circuit_breakers[server_id]
            logger.info(f"Removed server {server_id}")
    
    async def select_server(self, request_info: Dict[str, Any]) -> Optional[ServerInstance]:
        """Select the best server for a request"""
        healthy_servers = [
            server for server in self.servers.values()
            if server.is_healthy and self.circuit_breakers[server.id].can_attempt()
        ]
        
        if not healthy_servers:
            logger.warning("No healthy servers available")
            return None
        
        # Check for sticky session
        session_id = request_info.get('session_id')
        if self.config.enable_sticky_sessions and session_id:
            if session_id in self.sticky_sessions:
                server_id = self.sticky_sessions[session_id]
                if server_id in self.servers and self.servers[server_id] in healthy_servers:
                    return self.servers[server_id]
        
        # Apply load balancing strategy
        if self.config.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy_servers)
        elif self.config.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(healthy_servers)
        elif self.config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy_servers)
        elif self.config.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_select(healthy_servers)
        elif self.config.strategy == LoadBalancingStrategy.IP_HASH:
            return self._ip_hash_select(healthy_servers, request_info.get('client_ip', ''))
        elif self.config.strategy == LoadBalancingStrategy.RESOURCE_AWARE:
            return self._resource_aware_select(healthy_servers)
        elif self.config.strategy == LoadBalancingStrategy.ML_OPTIMIZED:
            return await self._ml_optimized_select(healthy_servers, request_info)
        else:
            return self._round_robin_select(healthy_servers)
    
    def _round_robin_select(self, servers: List[ServerInstance]) -> ServerInstance:
        """Simple round-robin selection"""
        server = servers[self.round_robin_index % len(servers)]
        self.round_robin_index += 1
        return server
    
    def _weighted_round_robin_select(self, servers: List[ServerInstance]) -> ServerInstance:
        """Weighted round-robin based on server weights"""
        total_weight = sum(server.weight for server in servers)
        random_weight = random.uniform(0, total_weight)
        
        current_weight = 0
        for server in servers:
            current_weight += server.weight
            if random_weight <= current_weight:
                return server
        
        return servers[0]  # Fallback
    
    def _least_connections_select(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server with least active connections"""
        return min(servers, key=lambda s: s.current_connections)
    
    def _least_response_time_select(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server with lowest average response time"""
        return min(servers, key=lambda s: s.avg_response_time)
    
    def _ip_hash_select(self, servers: List[ServerInstance], client_ip: str) -> ServerInstance:
        """Select server based on client IP hash"""
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        return servers[hash_value % len(servers)]
    
    def _resource_aware_select(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server based on resource utilization"""
        return min(servers, key=lambda s: s.load_score)
    
    async def _ml_optimized_select(self, servers: List[ServerInstance], 
                                 request_info: Dict[str, Any]) -> ServerInstance:
        """ML-optimized server selection"""
        request_type = request_info.get('request_type', 'general')
        required_capabilities = request_info.get('capabilities', [])
        
        # Score each server
        server_scores = {}
        for server in servers:
            score = 0
            
            # Response time score (lower is better)
            if server.avg_response_time > 0:
                response_score = 1.0 / (1.0 + server.avg_response_time)
                score += response_score * self.optimization_weights['response_time']
            
            # Success rate score
            success_score = server.success_rate
            score += success_score * self.optimization_weights['success_rate']
            
            # Load score (invert because lower load is better)
            load_score = 1.0 - min(server.load_score, 1.0)
            score += load_score * self.optimization_weights['load_score']
            
            # Capability matching score
            if required_capabilities:
                matched_capabilities = len(set(required_capabilities) & set(server.capabilities))
                capability_score = matched_capabilities / len(required_capabilities)
                score += capability_score * self.optimization_weights['capability_match']
            
            server_scores[server.id] = score
        
        # Select server with highest score
        best_server_id = max(server_scores, key=server_scores.get)
        return self.servers[best_server_id]
    
    async def handle_request(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a request through the load balancer"""
        start_time = time.time()
        server = await self.select_server(request_info)
        
        if not server:
            return {
                'success': False,
                'error': 'No available servers',
                'response_time': time.time() - start_time
            }
        
        # Update connection count
        server.current_connections += 1
        
        try:
            # Make the actual request
            result = await self._make_request(server, request_info)
            
            # Update metrics
            response_time = time.time() - start_time
            server.total_requests += 1
            server.avg_response_time = (
                (server.avg_response_time * (server.total_requests - 1) + response_time) /
                server.total_requests
            )
            
            if result['success']:
                self.circuit_breakers[server.id].record_success()
            else:
                server.failed_requests += 1
                self.circuit_breakers[server.id].record_failure()
            
            # Handle sticky sessions
            session_id = request_info.get('session_id')
            if self.config.enable_sticky_sessions and session_id:
                self.sticky_sessions[session_id] = server.id
            
            # Record request for ML optimization
            self._record_request(server.id, request_info, result, response_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Request failed on server {server.id}: {e}")
            server.failed_requests += 1
            self.circuit_breakers[server.id].record_failure()
            return {
                'success': False,
                'error': str(e),
                'response_time': time.time() - start_time
            }
        finally:
            server.current_connections -= 1
    
    async def _make_request(self, server: ServerInstance, 
                          request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to the selected server"""
        url = f"http://{server.host}:{server.port}{request_info.get('path', '/')}"
        
        timeout = aiohttp.ClientTimeout(total=self.config.connection_timeout)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if request_info.get('method', 'GET') == 'POST':
                    async with session.post(
                        url,
                        json=request_info.get('data'),
                        headers=request_info.get('headers', {})
                    ) as response:
                        return {
                            'success': response.status < 400,
                            'status': response.status,
                            'data': await response.json() if response.content_type == 'application/json' else await response.text()
                        }
                else:
                    async with session.get(
                        url,
                        headers=request_info.get('headers', {})
                    ) as response:
                        return {
                            'success': response.status < 400,
                            'status': response.status,
                            'data': await response.json() if response.content_type == 'application/json' else await response.text()
                        }
        except asyncio.TimeoutError:
            raise Exception("Request timeout")
        except Exception as e:
            raise Exception(f"Connection error: {e}")
    
    def _record_request(self, server_id: str, request_info: Dict[str, Any], 
                       result: Dict[str, Any], response_time: float):
        """Record request data for ML optimization"""
        record = {
            'server_id': server_id,
            'request_type': request_info.get('request_type', 'general'),
            'success': result['success'],
            'response_time': response_time,
            'timestamp': time.time()
        }
        
        self.request_history.append(record)
        self.server_performance_history[server_id].append({
            'response_time': response_time,
            'success': result['success'],
            'timestamp': time.time()
        })
        
        # Update request patterns
        request_pattern = request_info.get('request_type', 'general')
        self.request_patterns[request_pattern] += 1
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while self.running:
            try:
                for server in self.servers.values():
                    await self._check_server_health(server)
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)
    
    async def _check_server_health(self, server: ServerInstance):
        """Check health of a single server"""
        try:
            start_time = time.time()
            health_url = f"http://{server.host}:{server.port}/health"
            
            timeout = aiohttp.ClientTimeout(total=self.config.health_check_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    if response.status == 200:
                        server.health_status = "healthy"
                        
                        # Try to get resource metrics from health endpoint
                        try:
                            health_data = await response.json()
                            server.cpu_usage = health_data.get('cpu_usage', 0.0)
                            server.memory_usage = health_data.get('memory_usage', 0.0)
                            server.ml_model_load = health_data.get('ml_model_load', 0.0)
                        except:
                            pass
                    else:
                        server.health_status = "unhealthy"
            
            server.last_health_check = time.time()
            
        except Exception as e:
            logger.warning(f"Health check failed for server {server.id}: {e}")
            server.health_status = "unhealthy"
            server.last_health_check = time.time()
    
    async def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(60)  # Collect every minute
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(30)
    
    async def _collect_system_metrics(self):
        """Collect system-wide metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Calculate aggregate metrics
            total_requests = sum(server.total_requests for server in self.servers.values())
            total_connections = sum(server.current_connections for server in self.servers.values())
            avg_response_time = sum(server.avg_response_time * server.total_requests 
                                   for server in self.servers.values()) / max(total_requests, 1)
            
            metrics = {
                'timestamp': time.time(),
                'system_cpu': cpu_percent,
                'system_memory': memory.percent,
                'total_requests': total_requests,
                'total_connections': total_connections,
                'avg_response_time': avg_response_time,
                'healthy_servers': len([s for s in self.servers.values() if s.is_healthy])
            }
            
            logger.info(f"Load balancer metrics: {json.dumps(metrics, indent=2)}")
            
        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")
    
    async def _auto_scale_loop(self):
        """Auto-scaling loop"""
        if not self.config.auto_scale_enabled:
            return
        
        while self.running:
            try:
                await self._check_auto_scaling()
                await asyncio.sleep(120)  # Check every 2 minutes
            except Exception as e:
                logger.error(f"Auto-scaling error: {e}")
                await asyncio.sleep(60)
    
    async def _check_auto_scaling(self):
        """Check if auto-scaling is needed"""
        healthy_servers = [s for s in self.servers.values() if s.is_healthy]
        
        if len(healthy_servers) == 0:
            return
        
        # Calculate average load across all servers
        avg_load = sum(server.load_score for server in healthy_servers) / len(healthy_servers)
        
        if avg_load > self.config.scale_up_threshold and len(healthy_servers) < self.config.max_instances:
            logger.info(f"Auto-scaling up: avg_load={avg_load:.2f}, servers={len(healthy_servers)}")
            await self._scale_up()
        elif avg_load < self.config.scale_down_threshold and len(healthy_servers) > self.config.min_instances:
            logger.info(f"Auto-scaling down: avg_load={avg_load:.2f}, servers={len(healthy_servers)}")
            await self._scale_down()
    
    async def _scale_up(self):
        """Scale up by adding a new server instance"""
        # In a real implementation, this would integrate with container orchestration
        # For now, we'll log the scaling event
        logger.info("Scaling up - would create new server instance")
        
        # Example: Create new server instance
        # new_server = ServerInstance(
        #     id=f"auto-scale-{int(time.time())}",
        #     host="new-instance-host",
        #     port=8000,
        #     capabilities=["ml", "nlp"]
        # )
        # self.add_server(new_server)
    
    async def _scale_down(self):
        """Scale down by removing the least utilized server"""
        healthy_servers = [s for s in self.servers.values() if s.is_healthy]
        
        if len(healthy_servers) <= self.config.min_instances:
            return
        
        # Find server with lowest load
        least_used = min(healthy_servers, key=lambda s: s.load_score)
        
        # Graceful shutdown - mark as draining first
        least_used.health_status = "draining"
        logger.info(f"Scaling down - draining server {least_used.id}")
        
        # In a real implementation, would wait for connections to finish
        # then remove the server
        # await asyncio.sleep(30)  # Wait for connections to finish
        # self.remove_server(least_used.id)
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.running:
            try:
                await self._cleanup_expired_sessions()
                await self._cleanup_old_metrics()
                await asyncio.sleep(300)  # Cleanup every 5 minutes
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sticky sessions"""
        if not self.config.enable_sticky_sessions:
            return
        
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, server_id in self.sticky_sessions.items()
            if current_time - self.servers.get(server_id, type('obj', (object,), {'last_health_check': 0})).last_health_check > self.config.session_timeout
        ]
        
        for session_id in expired_sessions:
            del self.sticky_sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    async def _cleanup_old_metrics(self):
        """Clean up old performance metrics"""
        cutoff_time = time.time() - 3600  # Keep 1 hour of data
        
        for server_id in self.server_performance_history:
            old_count = len(self.server_performance_history[server_id])
            self.server_performance_history[server_id] = [
                record for record in self.server_performance_history[server_id]
                if record['timestamp'] > cutoff_time
            ]
            new_count = len(self.server_performance_history[server_id])
            
            if old_count != new_count:
                logger.debug(f"Cleaned up {old_count - new_count} old metrics for server {server_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        healthy_servers = [s for s in self.servers.values() if s.is_healthy]
        
        return {
            'total_servers': len(self.servers),
            'healthy_servers': len(healthy_servers),
            'total_requests': sum(server.total_requests for server in self.servers.values()),
            'total_connections': sum(server.current_connections for server in self.servers.values()),
            'avg_response_time': sum(server.avg_response_time * server.total_requests 
                                   for server in self.servers.values()) / max(sum(server.total_requests for server in self.servers.values()), 1),
            'success_rate': sum(server.success_rate * server.total_requests 
                               for server in self.servers.values()) / max(sum(server.total_requests for server in self.servers.values()), 1),
            'strategy': self.config.strategy.value,
            'auto_scaling_enabled': self.config.auto_scale_enabled
        }
    
    async def shutdown(self):
        """Graceful shutdown of load balancer"""
        logger.info("Shutting down load balancer")
        self.running = False
        
        # Mark all servers as draining
        for server in self.servers.values():
            if server.health_status == "healthy":
                server.health_status = "draining"
        
        # Wait for connections to finish (with timeout)
        timeout = 30
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            active_connections = sum(server.current_connections for server in self.servers.values())
            if active_connections == 0:
                break
            await asyncio.sleep(1)
        
        logger.info("Load balancer shutdown complete")

# Factory function for creating load balancer instances
def create_load_balancer(strategy: str = "ml_optimized", 
                        auto_scale: bool = True) -> LoadBalancer:
    """Create a configured load balancer instance"""
    
    config = LoadBalancerConfig(
        strategy=LoadBalancingStrategy(strategy),
        auto_scale_enabled=auto_scale,
        health_check_interval=30,
        max_retries=3,
        enable_sticky_sessions=True
    )
    
    return LoadBalancer(config)

# Example usage and testing
async def example_usage():
    """Example of how to use the load balancer"""
    
    # Create load balancer
    lb = create_load_balancer("ml_optimized", auto_scale=True)
    
    # Add servers
    servers = [
        ServerInstance("server1", "localhost", 8001, capabilities=["ml", "nlp"]),
        ServerInstance("server2", "localhost", 8002, capabilities=["ml", "cv"]),
        ServerInstance("server3", "localhost", 8003, capabilities=["general"])
    ]
    
    for server in servers:
        lb.add_server(server)
    
    # Initialize
    await lb.initialize()
    
    # Handle some requests
    request_info = {
        'method': 'POST',
        'path': '/api/process',
        'data': {'text': 'Hello world'},
        'client_ip': '192.168.1.1',
        'request_type': 'nlp',
        'capabilities': ['nlp']
    }
    
    result = await lb.handle_request(request_info)
    print(f"Request result: {result}")
    
    # Get statistics
    stats = lb.get_statistics()
    print(f"Load balancer stats: {json.dumps(stats, indent=2)}")
    
    # Shutdown
    await lb.shutdown()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run example
    asyncio.run(example_usage())