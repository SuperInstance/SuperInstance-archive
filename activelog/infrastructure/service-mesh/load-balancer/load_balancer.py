import asyncio
import aiohttp
import random
import time
import threading
import logging
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import hashlib
import consul


class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    RANDOM = "random"
    WEIGHTED_RANDOM = "weighted_random"
    CONSISTENT_HASH = "consistent_hash"
    IP_HASH = "ip_hash"
    HEALTH_WEIGHTED = "health_weighted"


class InstanceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    DISABLED = "disabled"


@dataclass
class ServiceInstance:
    instance_id: str
    service_name: str
    host: str
    port: int
    weight: int = 100
    status: InstanceStatus = InstanceStatus.HEALTHY
    current_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_request_time: datetime = None
    metadata: Dict[str, Any] = None


@dataclass
class LoadBalancingResult:
    instance: ServiceInstance
    strategy_used: LoadBalancingStrategy
    selection_time: float
    metadata: Dict[str, Any] = None


class LoadBalancingMetrics:
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.request_counts = defaultdict(int)
        self.response_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.connection_counts = defaultdict(int)
        self.last_selected = defaultdict(lambda: datetime.min)
        self.total_requests = 0
        self.lock = threading.RLock()
    
    def record_request(self, instance_id: str, response_time: float, success: bool):
        with self.lock:
            self.request_counts[instance_id] += 1
            self.total_requests += 1
            
            # Keep response times in a rolling window
            self.response_times[instance_id].append(response_time)
            if len(self.response_times[instance_id]) > self.window_size:
                self.response_times[instance_id] = self.response_times[instance_id][-self.window_size:]
            
            if not success:
                self.error_counts[instance_id] += 1
            
            self.last_selected[instance_id] = datetime.now()
    
    def update_connections(self, instance_id: str, connections: int):
        with self.lock:
            self.connection_counts[instance_id] = connections
    
    def get_avg_response_time(self, instance_id: str) -> float:
        with self.lock:
            times = self.response_times.get(instance_id, [])
            return statistics.mean(times) if times else 0.0
    
    def get_error_rate(self, instance_id: str) -> float:
        with self.lock:
            total = self.request_counts.get(instance_id, 0)
            errors = self.error_counts.get(instance_id, 0)
            return (errors / total) if total > 0 else 0.0
    
    def get_request_count(self, instance_id: str) -> int:
        with self.lock:
            return self.request_counts.get(instance_id, 0)
    
    def get_connection_count(self, instance_id: str) -> int:
        with self.lock:
            return self.connection_counts.get(instance_id, 0)


class ConsistentHashRing:
    """Consistent hashing implementation for load balancing"""
    
    def __init__(self, virtual_nodes: int = 100):
        self.virtual_nodes = virtual_nodes
        self.ring = {}
        self.sorted_keys = []
    
    def add_node(self, node_id: str, weight: int = 1):
        """Add a node to the hash ring"""
        # Add virtual nodes based on weight
        node_count = weight * self.virtual_nodes
        
        for i in range(node_count):
            virtual_key = f"{node_id}:{i}"
            hash_key = self._hash(virtual_key)
            self.ring[hash_key] = node_id
        
        self.sorted_keys = sorted(self.ring.keys())
    
    def remove_node(self, node_id: str):
        """Remove a node from the hash ring"""
        keys_to_remove = [k for k, v in self.ring.items() if v == node_id]
        for key in keys_to_remove:
            del self.ring[key]
        self.sorted_keys = sorted(self.ring.keys())
    
    def get_node(self, key: str) -> Optional[str]:
        """Get the node responsible for a key"""
        if not self.ring:
            return None
        
        hash_key = self._hash(key)
        
        # Find the first node clockwise
        for ring_key in self.sorted_keys:
            if hash_key <= ring_key:
                return self.ring[ring_key]
        
        # Wrap around to the first node
        return self.ring[self.sorted_keys[0]]
    
    def _hash(self, key: str) -> int:
        """Hash function for consistent hashing"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)


class LoadBalancer:
    """Intelligent load balancer with multiple strategies"""
    
    def __init__(self, service_name: str, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.service_name = service_name
        self.strategy = strategy
        self.instances: Dict[str, ServiceInstance] = {}
        self.metrics = LoadBalancingMetrics()
        self.logger = logging.getLogger(__name__)
        
        # Strategy-specific state
        self._round_robin_index = 0
        self._consistent_hash = ConsistentHashRing()
        self._lock = threading.RLock()
        
        # Configuration
        self.health_check_threshold = 0.1  # 10% error rate threshold
        self.response_time_threshold = 5000  # 5 second threshold
        self.connection_limit = 1000  # Max connections per instance
    
    def add_instance(self, instance: ServiceInstance):
        """Add a service instance to the load balancer"""
        with self._lock:
            self.instances[instance.instance_id] = instance
            
            # Update consistent hash ring
            if self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
                self._consistent_hash.add_node(instance.instance_id, instance.weight)
            
            self.logger.info(f"Added instance {instance.instance_id} to {self.service_name} load balancer")
    
    def remove_instance(self, instance_id: str):
        """Remove a service instance from the load balancer"""
        with self._lock:
            if instance_id in self.instances:
                del self.instances[instance_id]
                
                # Update consistent hash ring
                if self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
                    self._consistent_hash.remove_node(instance_id)
                
                self.logger.info(f"Removed instance {instance_id} from {self.service_name} load balancer")
    
    def update_instance_health(self, instance_id: str, status: InstanceStatus):
        """Update instance health status"""
        with self._lock:
            if instance_id in self.instances:
                self.instances[instance_id].status = status
    
    def update_instance_metrics(self, instance_id: str, connections: int = None, 
                              response_time: float = None, success: bool = True):
        """Update instance metrics"""
        with self._lock:
            if instance_id not in self.instances:
                return
            
            instance = self.instances[instance_id]
            
            if connections is not None:
                instance.current_connections = connections
                self.metrics.update_connections(instance_id, connections)
            
            if response_time is not None:
                # Update rolling average
                if instance.avg_response_time == 0:
                    instance.avg_response_time = response_time
                else:
                    # Exponential moving average
                    alpha = 0.1
                    instance.avg_response_time = (alpha * response_time + 
                                                 (1 - alpha) * instance.avg_response_time)
                
                instance.total_requests += 1
                if not success:
                    instance.failed_requests += 1
                
                instance.last_request_time = datetime.now()
                self.metrics.record_request(instance_id, response_time, success)
    
    def select_instance(self, client_ip: str = None, session_id: str = None, 
                       request_path: str = None) -> Optional[LoadBalancingResult]:
        """Select an instance based on the configured strategy"""
        start_time = time.time()
        
        with self._lock:
            healthy_instances = self._get_healthy_instances()
            
            if not healthy_instances:
                self.logger.warning(f"No healthy instances available for {self.service_name}")
                return None
            
            selected_instance = None
            selection_metadata = {}
            
            try:
                if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                    selected_instance = self._round_robin_select(healthy_instances)
                
                elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                    selected_instance = self._weighted_round_robin_select(healthy_instances)
                
                elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                    selected_instance = self._least_connections_select(healthy_instances)
                
                elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
                    selected_instance = self._least_response_time_select(healthy_instances)
                
                elif self.strategy == LoadBalancingStrategy.RANDOM:
                    selected_instance = self._random_select(healthy_instances)
                
                elif self.strategy == LoadBalancingStrategy.WEIGHTED_RANDOM:
                    selected_instance = self._weighted_random_select(healthy_instances)
                
                elif self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
                    hash_key = session_id or client_ip or request_path or ""
                    selected_instance = self._consistent_hash_select(healthy_instances, hash_key)
                
                elif self.strategy == LoadBalancingStrategy.IP_HASH:
                    selected_instance = self._ip_hash_select(healthy_instances, client_ip)
                
                elif self.strategy == LoadBalancingStrategy.HEALTH_WEIGHTED:
                    selected_instance = self._health_weighted_select(healthy_instances)
                
                else:
                    selected_instance = self._round_robin_select(healthy_instances)
                
                if selected_instance:
                    selection_time = (time.time() - start_time) * 1000
                    return LoadBalancingResult(
                        instance=selected_instance,
                        strategy_used=self.strategy,
                        selection_time=selection_time,
                        metadata=selection_metadata
                    )
                
                return None
                
            except Exception as e:
                self.logger.error(f"Error selecting instance for {self.service_name}: {e}")
                # Fallback to random selection
                return LoadBalancingResult(
                    instance=random.choice(healthy_instances),
                    strategy_used=LoadBalancingStrategy.RANDOM,
                    selection_time=(time.time() - start_time) * 1000,
                    metadata={"error": str(e), "fallback": True}
                )
    
    def _get_healthy_instances(self) -> List[ServiceInstance]:
        """Get list of healthy instances"""
        healthy = []
        
        for instance in self.instances.values():
            # Check basic health status
            if instance.status not in [InstanceStatus.HEALTHY, InstanceStatus.DRAINING]:
                continue
            
            # Check error rate
            error_rate = self.metrics.get_error_rate(instance.instance_id)
            if error_rate > self.health_check_threshold:
                continue
            
            # Check response time
            if instance.avg_response_time > self.response_time_threshold:
                continue
            
            # Check connection limit
            if instance.current_connections >= self.connection_limit:
                continue
            
            healthy.append(instance)
        
        return healthy
    
    def _round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round-robin selection"""
        if not instances:
            return None
        
        selected = instances[self._round_robin_index % len(instances)]
        self._round_robin_index = (self._round_robin_index + 1) % len(instances)
        return selected
    
    def _weighted_round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted round-robin selection"""
        if not instances:
            return None
        
        # Create weighted list
        weighted_instances = []
        for instance in instances:
            weight = max(1, instance.weight)  # Ensure minimum weight of 1
            weighted_instances.extend([instance] * weight)
        
        if not weighted_instances:
            return instances[0]
        
        selected = weighted_instances[self._round_robin_index % len(weighted_instances)]
        self._round_robin_index = (self._round_robin_index + 1) % len(weighted_instances)
        return selected
    
    def _least_connections_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Least connections selection"""
        if not instances:
            return None
        
        return min(instances, key=lambda x: x.current_connections)
    
    def _least_response_time_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Least response time selection"""
        if not instances:
            return None
        
        # Combine response time and current connections
        def selection_key(instance):
            response_time = instance.avg_response_time or 0
            connections = instance.current_connections
            return response_time + (connections * 10)  # Weight connections
        
        return min(instances, key=selection_key)
    
    def _random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Random selection"""
        return random.choice(instances) if instances else None
    
    def _weighted_random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted random selection"""
        if not instances:
            return None
        
        total_weight = sum(max(1, instance.weight) for instance in instances)
        if total_weight == 0:
            return random.choice(instances)
        
        rand_weight = random.randint(1, total_weight)
        current_weight = 0
        
        for instance in instances:
            current_weight += max(1, instance.weight)
            if current_weight >= rand_weight:
                return instance
        
        return instances[-1]  # Fallback
    
    def _consistent_hash_select(self, instances: List[ServiceInstance], key: str) -> ServiceInstance:
        """Consistent hash selection"""
        if not instances:
            return None
        
        if not key:
            return random.choice(instances)
        
        selected_id = self._consistent_hash.get_node(key)
        if selected_id:
            selected_instance = self.instances.get(selected_id)
            if selected_instance and selected_instance in instances:
                return selected_instance
        
        # Fallback to first available
        return instances[0]
    
    def _ip_hash_select(self, instances: List[ServiceInstance], client_ip: str) -> ServiceInstance:
        """IP hash selection for session affinity"""
        if not instances or not client_ip:
            return random.choice(instances) if instances else None
        
        # Simple hash based on IP
        ip_hash = hash(client_ip) % len(instances)
        return instances[ip_hash]
    
    def _health_weighted_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Health-weighted selection based on performance metrics"""
        if not instances:
            return None
        
        # Calculate health scores
        scored_instances = []
        
        for instance in instances:
            # Base score from weight
            score = instance.weight
            
            # Adjust for error rate (lower is better)
            error_rate = self.metrics.get_error_rate(instance.instance_id)
            score *= (1.0 - min(error_rate, 0.9))
            
            # Adjust for response time (lower is better)
            if instance.avg_response_time > 0:
                response_factor = max(0.1, 1000.0 / instance.avg_response_time)
                score *= response_factor
            
            # Adjust for current load (lower is better)
            connection_factor = max(0.1, 1.0 - (instance.current_connections / self.connection_limit))
            score *= connection_factor
            
            scored_instances.append((instance, score))
        
        # Sort by score (descending)
        scored_instances.sort(key=lambda x: x[1], reverse=True)
        
        # Weighted random selection from top candidates
        top_candidates = scored_instances[:max(1, len(scored_instances) // 2)]
        total_score = sum(score for _, score in top_candidates)
        
        if total_score <= 0:
            return scored_instances[0][0]
        
        rand_score = random.uniform(0, total_score)
        current_score = 0
        
        for instance, score in top_candidates:
            current_score += score
            if current_score >= rand_score:
                return instance
        
        return top_candidates[0][0]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        with self._lock:
            stats = {
                "service_name": self.service_name,
                "strategy": self.strategy.value,
                "total_instances": len(self.instances),
                "healthy_instances": len(self._get_healthy_instances()),
                "total_requests": self.metrics.total_requests,
                "instances": {}
            }
            
            for instance_id, instance in self.instances.items():
                stats["instances"][instance_id] = {
                    "status": instance.status.value,
                    "weight": instance.weight,
                    "current_connections": instance.current_connections,
                    "total_requests": instance.total_requests,
                    "failed_requests": instance.failed_requests,
                    "error_rate": self.metrics.get_error_rate(instance_id),
                    "avg_response_time": instance.avg_response_time,
                    "last_request": instance.last_request_time.isoformat() if instance.last_request_time else None
                }
            
            return stats
    
    def set_strategy(self, strategy: LoadBalancingStrategy):
        """Change load balancing strategy"""
        with self._lock:
            old_strategy = self.strategy
            self.strategy = strategy
            
            # Reset strategy-specific state
            self._round_robin_index = 0
            
            # Rebuild consistent hash ring if needed
            if strategy == LoadBalancingStrategy.CONSISTENT_HASH:
                self._consistent_hash = ConsistentHashRing()
                for instance in self.instances.values():
                    self._consistent_hash.add_node(instance.instance_id, instance.weight)
            
            self.logger.info(f"Changed load balancing strategy from {old_strategy.value} to {strategy.value}")


class ServiceLoadBalancerManager:
    """Manages load balancers for multiple services"""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.update_thread = None
    
    def get_or_create_load_balancer(self, service_name: str, 
                                  strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN) -> LoadBalancer:
        """Get or create a load balancer for a service"""
        if service_name not in self.load_balancers:
            self.load_balancers[service_name] = LoadBalancer(service_name, strategy)
            self.logger.info(f"Created load balancer for service: {service_name}")
        
        return self.load_balancers[service_name]
    
    def remove_load_balancer(self, service_name: str):
        """Remove a load balancer for a service"""
        if service_name in self.load_balancers:
            del self.load_balancers[service_name]
            self.logger.info(f"Removed load balancer for service: {service_name}")
    
    def start_service_discovery_sync(self):
        """Start syncing with Consul service discovery"""
        self.running = True
        self.update_thread = threading.Thread(target=self._sync_services, daemon=True)
        self.update_thread.start()
        self.logger.info("Started service discovery sync")
    
    def stop_service_discovery_sync(self):
        """Stop syncing with Consul"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        self.logger.info("Stopped service discovery sync")
    
    def _sync_services(self):
        """Sync services from Consul service discovery"""
        while self.running:
            try:
                # Get all services from Consul
                services = self.consul.health.state('any')[1]
                service_instances = defaultdict(list)
                
                # Group by service name
                for service_data in services:
                    service_name = service_data['ServiceName']
                    if service_name == 'consul':  # Skip consul itself
                        continue
                    
                    service_instances[service_name].append(service_data)
                
                # Update load balancers
                for service_name, instances in service_instances.items():
                    lb = self.get_or_create_load_balancer(service_name)
                    self._update_load_balancer_instances(lb, instances)
                
                # Remove load balancers for services that no longer exist
                current_services = set(service_instances.keys())
                existing_services = set(self.load_balancers.keys())
                
                for service_name in existing_services - current_services:
                    self.remove_load_balancer(service_name)
                
                time.sleep(30)  # Sync every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error syncing services: {e}")
                time.sleep(30)
    
    def _update_load_balancer_instances(self, lb: LoadBalancer, consul_services: List[Dict]):
        """Update load balancer instances from Consul data"""
        # Build current instance map
        current_instances = {}
        
        for service_data in consul_services:
            service_info = service_data.get('Service', {})
            checks = service_data.get('Checks', [])
            
            instance_id = service_info.get('ID')
            if not instance_id:
                continue
            
            # Determine health status
            status = InstanceStatus.HEALTHY
            for check in checks:
                check_status = check.get('Status')
                if check_status == 'critical':
                    status = InstanceStatus.UNHEALTHY
                    break
                elif check_status == 'warning':
                    status = InstanceStatus.DRAINING
            
            # Get metadata
            meta = service_info.get('Meta', {})
            weight = int(meta.get('weight', 100))
            
            instance = ServiceInstance(
                instance_id=instance_id,
                service_name=service_info.get('Service', ''),
                host=service_info.get('Address', 'localhost'),
                port=service_info.get('Port', 80),
                weight=weight,
                status=status,
                metadata=meta
            )
            
            current_instances[instance_id] = instance
        
        # Update load balancer
        existing_instance_ids = set(lb.instances.keys())
        current_instance_ids = set(current_instances.keys())
        
        # Add new instances
        for instance_id in current_instance_ids - existing_instance_ids:
            lb.add_instance(current_instances[instance_id])
        
        # Remove deleted instances
        for instance_id in existing_instance_ids - current_instance_ids:
            lb.remove_instance(instance_id)
        
        # Update existing instances
        for instance_id in current_instance_ids & existing_instance_ids:
            current_instance = current_instances[instance_id]
            lb.update_instance_health(instance_id, current_instance.status)
            # Update other instance properties as needed
    
    def select_instance(self, service_name: str, client_ip: str = None, 
                       session_id: str = None, request_path: str = None) -> Optional[LoadBalancingResult]:
        """Select an instance for a service"""
        if service_name not in self.load_balancers:
            # Try to create from Consul if not exists
            self.get_or_create_load_balancer(service_name)
            # Trigger immediate sync
            if self.running:
                threading.Thread(target=self._sync_single_service, args=(service_name,), daemon=True).start()
        
        if service_name in self.load_balancers:
            return self.load_balancers[service_name].select_instance(client_ip, session_id, request_path)
        
        return None
    
    def _sync_single_service(self, service_name: str):
        """Sync a single service immediately"""
        try:
            services = self.consul.health.service(service_name)[1]
            if service_name in self.load_balancers:
                self._update_load_balancer_instances(self.load_balancers[service_name], services)
        except Exception as e:
            self.logger.error(f"Error syncing service {service_name}: {e}")
    
    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all load balancers"""
        return {name: lb.get_statistics() for name, lb in self.load_balancers.items()}
    
    def update_instance_metrics(self, service_name: str, instance_id: str, 
                              response_time: float, success: bool = True,
                              connections: int = None):
        """Update metrics for an instance"""
        if service_name in self.load_balancers:
            self.load_balancers[service_name].update_instance_metrics(
                instance_id, connections, response_time, success
            )


# Usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create load balancer manager
    lb_manager = ServiceLoadBalancerManager()
    lb_manager.start_service_discovery_sync()
    
    try:
        # Example: Select instance for API service
        result = lb_manager.select_instance("api-service", client_ip="192.168.1.100")
        
        if result:
            print(f"Selected instance: {result.instance.host}:{result.instance.port}")
            print(f"Strategy used: {result.strategy_used.value}")
            print(f"Selection time: {result.selection_time:.2f}ms")
            
            # Simulate request completion
            lb_manager.update_instance_metrics(
                "api-service", 
                result.instance.instance_id, 
                response_time=150.0, 
                success=True
            )
        else:
            print("No healthy instances available")
        
        # Get statistics
        stats = lb_manager.get_all_statistics()
        for service_name, service_stats in stats.items():
            print(f"\nService: {service_name}")
            print(f"  Strategy: {service_stats['strategy']}")
            print(f"  Healthy instances: {service_stats['healthy_instances']}/{service_stats['total_instances']}")
            print(f"  Total requests: {service_stats['total_requests']}")
        
        time.sleep(60)  # Run for a minute
        
    finally:
        lb_manager.stop_service_discovery_sync()