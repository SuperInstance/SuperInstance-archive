#!/usr/bin/env python3
"""
Distributed Multi-Node Resource Orchestration

Provides distributed computing orchestration across multiple nodes including
cluster management, load balancing, fault tolerance, and service discovery.
"""

import asyncio
import threading
import time
import json
import hashlib
import logging
import socket
import random
import uuid
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, deque
import heapq
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import websockets
from datetime import datetime, timedelta
import psutil

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """Node roles in the cluster"""
    LEADER = "leader"
    FOLLOWER = "follower"
    WORKER = "worker"
    OBSERVER = "observer"


class NodeStatus(Enum):
    """Node operational status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class TaskExecutionMode(Enum):
    """Task execution modes"""
    LOCAL = "local"
    DISTRIBUTED = "distributed"
    MAP_REDUCE = "map_reduce"
    PIPELINE = "pipeline"
    BROADCAST = "broadcast"


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_LOADED = "least_loaded"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    CONSISTENT_HASH = "consistent_hash"
    GEOGRAPHICAL = "geographical"


@dataclass
class NodeInfo:
    """Information about a cluster node"""
    node_id: str
    hostname: str
    ip_address: str
    port: int
    role: NodeRole
    status: NodeStatus
    capabilities: Set[str]
    resources: Dict[str, float]  # CPU, memory, storage, etc.
    load_metrics: Dict[str, float] = field(default_factory=dict)
    last_heartbeat: float = 0.0
    last_seen: float = 0.0
    version: str = "1.0.0"
    region: str = "default"
    availability_zone: str = "default"
    tags: Dict[str, str] = field(default_factory=dict)
    current_tasks: int = 0
    max_tasks: int = 100
    
    def is_healthy(self, heartbeat_timeout: float = 30.0) -> bool:
        """Check if node is healthy based on recent heartbeat"""
        if self.status in [NodeStatus.FAILED, NodeStatus.MAINTENANCE]:
            return False
        
        if time.time() - self.last_heartbeat > heartbeat_timeout:
            return False
        
        return True
    
    def calculate_load_score(self) -> float:
        """Calculate overall load score for the node"""
        cpu_load = self.load_metrics.get('cpu_percent', 0.0) / 100.0
        memory_load = self.load_metrics.get('memory_percent', 0.0) / 100.0
        task_load = self.current_tasks / max(self.max_tasks, 1)
        
        # Weighted average
        return (cpu_load * 0.4 + memory_load * 0.4 + task_load * 0.2)
    
    def can_handle_task(self, required_capabilities: Set[str], required_resources: Dict[str, float]) -> bool:
        """Check if node can handle a task"""
        if not self.is_healthy():
            return False
        
        # Check capabilities
        if not required_capabilities.issubset(self.capabilities):
            return False
        
        # Check resources
        for resource, required_amount in required_resources.items():
            if self.resources.get(resource, 0.0) < required_amount:
                return False
        
        # Check task capacity
        if self.current_tasks >= self.max_tasks:
            return False
        
        return True


@dataclass
class DistributedTask:
    """Distributed task specification"""
    task_id: str
    name: str
    execution_mode: TaskExecutionMode
    required_capabilities: Set[str]
    required_resources: Dict[str, float]
    priority: int = 0
    timeout_seconds: float = 300.0
    retry_count: int = 3
    dependency_task_ids: List[str] = field(default_factory=list)
    affinity_rules: Dict[str, Any] = field(default_factory=dict)
    payload: Any = None
    callback_url: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    assigned_nodes: List[str] = field(default_factory=list)
    status: str = "pending"
    progress: float = 0.0
    result: Any = None
    error: Optional[str] = None
    
    def is_ready_to_execute(self, completed_tasks: Set[str]) -> bool:
        """Check if task is ready to execute (dependencies satisfied)"""
        return all(dep_id in completed_tasks for dep_id in self.dependency_task_ids)


class ConsistentHashRing:
    """Consistent hashing ring for node selection"""
    
    def __init__(self, virtual_nodes: int = 150):
        self.virtual_nodes = virtual_nodes
        self.ring: Dict[int, str] = {}
        self.nodes: Set[str] = set()
    
    def add_node(self, node_id: str):
        """Add node to the ring"""
        self.nodes.add(node_id)
        for i in range(self.virtual_nodes):
            key = f"{node_id}:{i}"
            hash_value = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
            self.ring[hash_value] = node_id
    
    def remove_node(self, node_id: str):
        """Remove node from the ring"""
        if node_id not in self.nodes:
            return
        
        self.nodes.remove(node_id)
        keys_to_remove = [key for key, value in self.ring.items() if value == node_id]
        for key in keys_to_remove:
            del self.ring[key]
    
    def get_node(self, key: str) -> Optional[str]:
        """Get node for a given key"""
        if not self.ring:
            return None
        
        key_hash = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
        
        # Find the first node with hash >= key_hash
        for hash_value in sorted(self.ring.keys()):
            if hash_value >= key_hash:
                return self.ring[hash_value]
        
        # Wrap around to the first node
        return self.ring[min(self.ring.keys())]
    
    def get_nodes(self, key: str, count: int) -> List[str]:
        """Get multiple nodes for replication"""
        if count <= 0 or not self.ring:
            return []
        
        key_hash = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
        sorted_hashes = sorted(self.ring.keys())
        
        result_nodes = []
        used_nodes = set()
        
        # Find starting position
        start_idx = 0
        for i, hash_value in enumerate(sorted_hashes):
            if hash_value >= key_hash:
                start_idx = i
                break
        
        # Collect nodes
        for i in range(len(sorted_hashes)):
            idx = (start_idx + i) % len(sorted_hashes)
            hash_value = sorted_hashes[idx]
            node_id = self.ring[hash_value]
            
            if node_id not in used_nodes:
                result_nodes.append(node_id)
                used_nodes.add(node_id)
                
                if len(result_nodes) >= count:
                    break
        
        return result_nodes


class ServiceDiscovery:
    """Service discovery and health monitoring"""
    
    def __init__(self):
        self.services: Dict[str, List[NodeInfo]] = defaultdict(list)
        self.health_checks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
    
    def register_service(self, service_name: str, node: NodeInfo):
        """Register a service instance"""
        with self._lock:
            # Remove existing registration for this node
            self.services[service_name] = [
                n for n in self.services[service_name] 
                if n.node_id != node.node_id
            ]
            
            # Add new registration
            self.services[service_name].append(node)
            
            logger.info(f"Registered service {service_name} on node {node.node_id}")
    
    def deregister_service(self, service_name: str, node_id: str):
        """Deregister a service instance"""
        with self._lock:
            self.services[service_name] = [
                n for n in self.services[service_name]
                if n.node_id != node_id
            ]
            
            logger.info(f"Deregistered service {service_name} from node {node_id}")
    
    def discover_service(self, service_name: str, healthy_only: bool = True) -> List[NodeInfo]:
        """Discover service instances"""
        with self._lock:
            instances = self.services.get(service_name, [])
            
            if healthy_only:
                instances = [node for node in instances if node.is_healthy()]
            
            return instances.copy()
    
    def add_health_check(self, service_name: str, health_check: Callable):
        """Add health check for a service"""
        self.health_checks[service_name] = health_check
    
    async def perform_health_checks(self):
        """Perform health checks on all services"""
        for service_name, health_check in self.health_checks.items():
            instances = self.discover_service(service_name, healthy_only=False)
            
            for node in instances:
                try:
                    is_healthy = await health_check(node)
                    if not is_healthy:
                        node.status = NodeStatus.DEGRADED
                        logger.warning(f"Health check failed for {service_name} on {node.node_id}")
                except Exception as e:
                    node.status = NodeStatus.FAILED
                    logger.error(f"Health check error for {service_name} on {node.node_id}: {e}")


class LoadBalancer:
    """Load balancer for distributing requests across nodes"""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED):
        self.strategy = strategy
        self.consistent_hash = ConsistentHashRing()
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.connection_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def add_node(self, node: NodeInfo, weight: float = 1.0):
        """Add node to load balancer"""
        if self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            self.consistent_hash.add_node(node.node_id)
        
        # Store weight information if needed
        setattr(node, '_lb_weight', weight)
    
    def remove_node(self, node_id: str):
        """Remove node from load balancer"""
        if self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            self.consistent_hash.remove_node(node_id)
        
        with self._lock:
            self.request_counts.pop(node_id, None)
            self.connection_counts.pop(node_id, None)
    
    def select_node(self, nodes: List[NodeInfo], request_key: Optional[str] = None) -> Optional[NodeInfo]:
        """Select best node based on strategy"""
        if not nodes:
            return None
        
        # Filter healthy nodes
        healthy_nodes = [node for node in nodes if node.is_healthy()]
        if not healthy_nodes:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            with self._lock:
                # Simple round robin based on request count
                selected = min(healthy_nodes, key=lambda n: self.request_counts[n.node_id])
                self.request_counts[selected.node_id] += 1
                return selected
        
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return min(healthy_nodes, key=lambda n: self.connection_counts[n.node_id])
        
        elif self.strategy == LoadBalancingStrategy.LEAST_LOADED:
            return min(healthy_nodes, key=lambda n: n.calculate_load_score())
        
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            # Weighted selection based on node weight
            total_weight = sum(getattr(node, '_lb_weight', 1.0) for node in healthy_nodes)
            if total_weight == 0:
                return random.choice(healthy_nodes)
            
            r = random.uniform(0, total_weight)
            cumulative = 0
            
            for node in healthy_nodes:
                cumulative += getattr(node, '_lb_weight', 1.0)
                if r <= cumulative:
                    return node
            
            return healthy_nodes[-1]  # Fallback
        
        elif self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            if request_key:
                node_id = self.consistent_hash.get_node(request_key)
                for node in healthy_nodes:
                    if node.node_id == node_id:
                        return node
            
            # Fallback to random selection
            return random.choice(healthy_nodes)
        
        elif self.strategy == LoadBalancingStrategy.GEOGRAPHICAL:
            # Select based on geographical proximity (simplified)
            # In real implementation, would use actual geographic distance
            return min(healthy_nodes, key=lambda n: (n.region, n.availability_zone))
        
        else:
            return random.choice(healthy_nodes)
    
    def record_connection_start(self, node_id: str):
        """Record connection start"""
        with self._lock:
            self.connection_counts[node_id] += 1
    
    def record_connection_end(self, node_id: str):
        """Record connection end"""
        with self._lock:
            self.connection_counts[node_id] = max(0, self.connection_counts[node_id] - 1)


class ClusterManager:
    """Manages cluster membership and coordination"""
    
    def __init__(self, node_id: str, port: int = 8432):
        self.node_id = node_id
        self.port = port
        self.nodes: Dict[str, NodeInfo] = {}
        self.leader_id: Optional[str] = None
        self.is_leader = False
        
        # Create self node info
        self.self_node = NodeInfo(
            node_id=node_id,
            hostname=socket.gethostname(),
            ip_address=self._get_local_ip(),
            port=port,
            role=NodeRole.FOLLOWER,
            status=NodeStatus.HEALTHY,
            capabilities={"compute", "storage", "network"},
            resources=self._get_system_resources()
        )
        
        self.service_discovery = ServiceDiscovery()
        self.load_balancer = LoadBalancer()
        
        # Task management
        self.pending_tasks: Dict[str, DistributedTask] = {}
        self.running_tasks: Dict[str, DistributedTask] = {}
        self.completed_tasks: Set[str] = set()
        
        self._heartbeat_task = None
        self._leader_election_task = None
        self._task_scheduler_task = None
        self._running = False
        self._lock = threading.Lock()
        
        logger.info(f"Initialized cluster manager for node {node_id}")
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"
    
    def _get_system_resources(self) -> Dict[str, float]:
        """Get current system resources"""
        return {
            'cpu_cores': float(psutil.cpu_count()),
            'memory_gb': float(psutil.virtual_memory().total / (1024**3)),
            'disk_gb': float(psutil.disk_usage('/').total / (1024**3)),
            'network_mbps': 1000.0  # Assume 1Gbps
        }
    
    async def start(self):
        """Start the cluster manager"""
        self._running = True
        
        # Add self to cluster
        with self._lock:
            self.nodes[self.node_id] = self.self_node
        
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._leader_election_task = asyncio.create_task(self._leader_election_loop())
        self._task_scheduler_task = asyncio.create_task(self._task_scheduler_loop())
        
        logger.info(f"Cluster manager started on {self.self_node.ip_address}:{self.port}")
    
    async def stop(self):
        """Stop the cluster manager"""
        self._running = False
        
        # Cancel background tasks
        for task in [self._heartbeat_task, self._leader_election_task, self._task_scheduler_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Cluster manager stopped")
    
    async def _heartbeat_loop(self):
        """Send heartbeat to other nodes"""
        while self._running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(10.0)  # Heartbeat every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(10.0)
    
    async def _leader_election_loop(self):
        """Leader election process"""
        while self._running:
            try:
                await self._perform_leader_election()
                await asyncio.sleep(30.0)  # Check leadership every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Leader election error: {e}")
                await asyncio.sleep(30.0)
    
    async def _task_scheduler_loop(self):
        """Task scheduler loop"""
        while self._running:
            try:
                if self.is_leader:
                    await self._schedule_pending_tasks()
                await asyncio.sleep(1.0)  # Check tasks every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task scheduler error: {e}")
                await asyncio.sleep(5.0)
    
    async def _send_heartbeat(self):
        """Send heartbeat to all known nodes"""
        # Update self node metrics
        self.self_node.load_metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
        self.self_node.last_heartbeat = time.time()
        self.self_node.current_tasks = len(self.running_tasks)
        
        # Send to other nodes (simplified - would use actual network communication)
        heartbeat_data = {
            'node_id': self.node_id,
            'node_info': asdict(self.self_node),
            'timestamp': time.time(),
            'leader_id': self.leader_id
        }
        
        # In real implementation, would send via HTTP/WebSocket to other nodes
        logger.debug(f"Sent heartbeat: {heartbeat_data}")
    
    async def _perform_leader_election(self):
        """Perform leader election using bully algorithm"""
        with self._lock:
            healthy_nodes = [node for node in self.nodes.values() if node.is_healthy()]
            
            if not healthy_nodes:
                return
            
            # Sort by node_id for deterministic election
            healthy_nodes.sort(key=lambda n: n.node_id)
            
            # Highest node_id becomes leader (simplified bully algorithm)
            new_leader_id = healthy_nodes[-1].node_id
            
            if self.leader_id != new_leader_id:
                old_leader = self.leader_id
                self.leader_id = new_leader_id
                self.is_leader = (new_leader_id == self.node_id)
                
                if self.is_leader:
                    self.self_node.role = NodeRole.LEADER
                    logger.info(f"Node {self.node_id} became leader")
                else:
                    self.self_node.role = NodeRole.FOLLOWER
                    logger.info(f"Node {new_leader_id} is the new leader")
    
    async def _schedule_pending_tasks(self):
        """Schedule pending tasks (leader only)"""
        if not self.is_leader:
            return
        
        with self._lock:
            ready_tasks = []
            
            # Find tasks ready to execute
            for task_id, task in self.pending_tasks.items():
                if task.is_ready_to_execute(self.completed_tasks):
                    ready_tasks.append(task)
            
            # Schedule ready tasks
            for task in ready_tasks:
                success = await self._assign_task_to_nodes(task)
                if success:
                    self.pending_tasks.pop(task.task_id)
                    self.running_tasks[task.task_id] = task
                    task.started_at = time.time()
                    task.status = "running"
    
    async def _assign_task_to_nodes(self, task: DistributedTask) -> bool:
        """Assign task to appropriate nodes"""
        with self._lock:
            # Find capable nodes
            capable_nodes = []
            for node in self.nodes.values():
                if node.can_handle_task(task.required_capabilities, task.required_resources):
                    capable_nodes.append(node)
            
            if not capable_nodes:
                logger.warning(f"No capable nodes found for task {task.task_id}")
                return False
            
            # Select nodes based on execution mode
            if task.execution_mode == TaskExecutionMode.LOCAL:
                selected_node = self.load_balancer.select_node(capable_nodes, task.task_id)
                if selected_node:
                    task.assigned_nodes = [selected_node.node_id]
                    selected_node.current_tasks += 1
                    return True
            
            elif task.execution_mode == TaskExecutionMode.DISTRIBUTED:
                # Assign to multiple nodes
                num_nodes = min(len(capable_nodes), 3)  # Up to 3 nodes
                selected_nodes = sorted(capable_nodes, key=lambda n: n.calculate_load_score())[:num_nodes]
                task.assigned_nodes = [node.node_id for node in selected_nodes]
                for node in selected_nodes:
                    node.current_tasks += 1
                return True
            
            elif task.execution_mode == TaskExecutionMode.BROADCAST:
                # Send to all capable nodes
                task.assigned_nodes = [node.node_id for node in capable_nodes]
                for node in capable_nodes:
                    node.current_tasks += 1
                return True
            
            return False
    
    def submit_task(self, task: DistributedTask) -> str:
        """Submit task to the cluster"""
        with self._lock:
            self.pending_tasks[task.task_id] = task
            logger.info(f"Submitted task {task.task_id} to cluster")
            return task.task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        with self._lock:
            # Remove from pending
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
                return True
            
            # Cancel running task
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.status = "cancelled"
                
                # Update node task counts
                for node_id in task.assigned_nodes:
                    if node_id in self.nodes:
                        self.nodes[node_id].current_tasks = max(0, self.nodes[node_id].current_tasks - 1)
                
                del self.running_tasks[task_id]
                return True
            
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        with self._lock:
            if task_id in self.pending_tasks:
                task = self.pending_tasks[task_id]
                return {
                    'task_id': task_id,
                    'status': 'pending',
                    'progress': 0.0,
                    'created_at': task.created_at
                }
            
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                return {
                    'task_id': task_id,
                    'status': task.status,
                    'progress': task.progress,
                    'assigned_nodes': task.assigned_nodes,
                    'started_at': task.started_at
                }
            
            if task_id in self.completed_tasks:
                return {
                    'task_id': task_id,
                    'status': 'completed',
                    'progress': 1.0
                }
            
            return None
    
    def complete_task(self, task_id: str, success: bool = True, result: Any = None, error: str = None):
        """Mark task as completed"""
        with self._lock:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.completed_at = time.time()
                task.status = "completed" if success else "failed"
                task.result = result
                task.error = error
                
                # Update node task counts
                for node_id in task.assigned_nodes:
                    if node_id in self.nodes:
                        self.nodes[node_id].current_tasks = max(0, self.nodes[node_id].current_tasks - 1)
                
                del self.running_tasks[task_id]
                if success:
                    self.completed_tasks.add(task_id)
                
                logger.info(f"Task {task_id} {'completed' if success else 'failed'}")
    
    def join_cluster(self, seed_nodes: List[str]):
        """Join an existing cluster"""
        # In real implementation, would contact seed nodes to join cluster
        logger.info(f"Joining cluster with seed nodes: {seed_nodes}")
    
    def leave_cluster(self):
        """Leave the cluster gracefully"""
        # Cancel all running tasks
        with self._lock:
            for task_id in list(self.running_tasks.keys()):
                self.cancel_task(task_id)
        
        logger.info("Left cluster gracefully")
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive cluster status"""
        with self._lock:
            healthy_nodes = [node for node in self.nodes.values() if node.is_healthy()]
            
            total_resources = defaultdict(float)
            used_resources = defaultdict(float)
            
            for node in self.nodes.values():
                for resource, amount in node.resources.items():
                    total_resources[resource] += amount
                
                # Estimate used resources based on load
                cpu_used = node.load_metrics.get('cpu_percent', 0.0) / 100.0 * node.resources.get('cpu_cores', 0.0)
                memory_used = node.load_metrics.get('memory_percent', 0.0) / 100.0 * node.resources.get('memory_gb', 0.0)
                used_resources['cpu_cores'] += cpu_used
                used_resources['memory_gb'] += memory_used
            
            return {
                'cluster_id': f"cluster_{self.node_id}",
                'leader_id': self.leader_id,
                'is_leader': self.is_leader,
                'total_nodes': len(self.nodes),
                'healthy_nodes': len(healthy_nodes),
                'total_resources': dict(total_resources),
                'used_resources': dict(used_resources),
                'pending_tasks': len(self.pending_tasks),
                'running_tasks': len(self.running_tasks),
                'completed_tasks': len(self.completed_tasks),
                'nodes': {node_id: asdict(node) for node_id, node in self.nodes.items()},
                'self_node_id': self.node_id
            }
    
    def add_node_to_cluster(self, node_info: NodeInfo):
        """Add node to cluster (internal use)"""
        with self._lock:
            self.nodes[node_info.node_id] = node_info
            self.load_balancer.add_node(node_info)
            logger.info(f"Added node {node_info.node_id} to cluster")
    
    def remove_node_from_cluster(self, node_id: str):
        """Remove node from cluster (internal use)"""
        with self._lock:
            if node_id in self.nodes:
                node = self.nodes.pop(node_id)
                self.load_balancer.remove_node(node_id)
                
                # Reassign tasks if this node was handling any
                tasks_to_reassign = []
                for task_id, task in self.running_tasks.items():
                    if node_id in task.assigned_nodes:
                        tasks_to_reassign.append(task_id)
                
                # Move tasks back to pending for reassignment
                for task_id in tasks_to_reassign:
                    task = self.running_tasks.pop(task_id)
                    task.assigned_nodes = []
                    task.status = "pending"
                    self.pending_tasks[task_id] = task
                
                logger.info(f"Removed node {node_id} from cluster, reassigned {len(tasks_to_reassign)} tasks")


class DistributedOrchestrator:
    """Main distributed orchestration coordinator"""
    
    def __init__(self, node_id: Optional[str] = None, port: int = 8432):
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:8]}"
        self.cluster_manager = ClusterManager(self.node_id, port)
        
        # Orchestration callbacks
        self.orchestration_callbacks: List[Callable] = []
        
        # Statistics
        self.orchestration_stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'nodes_joined': 0,
            'nodes_left': 0,
            'leader_elections': 0
        }
        
        self._running = False
        self._monitoring_task = None
        
        logger.info(f"Initialized distributed orchestrator for node {self.node_id}")
    
    async def start(self, seed_nodes: Optional[List[str]] = None):
        """Start the distributed orchestrator"""
        self._running = True
        
        await self.cluster_manager.start()
        
        if seed_nodes:
            self.cluster_manager.join_cluster(seed_nodes)
        
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Distributed orchestrator started")
    
    async def stop(self):
        """Stop the distributed orchestrator"""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.cluster_manager.leave_cluster()
        await self.cluster_manager.stop()
        
        logger.info("Distributed orchestrator stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                await self._perform_monitoring()
                await asyncio.sleep(30.0)  # Monitor every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Orchestration monitoring error: {e}")
                await asyncio.sleep(30.0)
    
    async def _perform_monitoring(self):
        """Perform orchestration monitoring"""
        cluster_status = self.cluster_manager.get_cluster_status()
        
        # Update statistics
        self.orchestration_stats.update({
            'current_nodes': cluster_status['total_nodes'],
            'healthy_nodes': cluster_status['healthy_nodes'],
            'pending_tasks': cluster_status['pending_tasks'],
            'running_tasks': cluster_status['running_tasks']
        })
        
        # Notify callbacks
        for callback in self.orchestration_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback({
                        'type': 'orchestration_status',
                        'cluster_status': cluster_status,
                        'orchestration_stats': self.orchestration_stats
                    })
                else:
                    callback({
                        'type': 'orchestration_status',
                        'cluster_status': cluster_status,
                        'orchestration_stats': self.orchestration_stats
                    })
            except Exception as e:
                logger.error(f"Orchestration callback error: {e}")
    
    def submit_task(self, task: DistributedTask) -> str:
        """Submit distributed task"""
        task_id = self.cluster_manager.submit_task(task)
        self.orchestration_stats['tasks_submitted'] += 1
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel distributed task"""
        return self.cluster_manager.cancel_task(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        return self.cluster_manager.get_task_status(task_id)
    
    def complete_task(self, task_id: str, success: bool = True, result: Any = None, error: str = None):
        """Complete task"""
        self.cluster_manager.complete_task(task_id, success, result, error)
        if success:
            self.orchestration_stats['tasks_completed'] += 1
        else:
            self.orchestration_stats['tasks_failed'] += 1
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        return self.cluster_manager.get_cluster_status()
    
    def get_orchestration_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics"""
        return self.orchestration_stats.copy()
    
    def add_orchestration_callback(self, callback: Callable):
        """Add orchestration callback"""
        self.orchestration_callbacks.append(callback)
    
    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy):
        """Set load balancing strategy"""
        self.cluster_manager.load_balancer.strategy = strategy
        logger.info(f"Load balancing strategy set to {strategy.value}")


# Global orchestrator instance
distributed_orchestrator = DistributedOrchestrator()


# Convenience functions for creating distributed tasks
def create_compute_task(name: str, capabilities: Set[str], resources: Dict[str, float],
                       execution_mode: TaskExecutionMode = TaskExecutionMode.LOCAL,
                       priority: int = 0) -> DistributedTask:
    """Create a compute task"""
    return DistributedTask(
        task_id=f"compute_{int(time.time())}_{name}",
        name=name,
        execution_mode=execution_mode,
        required_capabilities=capabilities,
        required_resources=resources,
        priority=priority
    )


def create_map_reduce_task(name: str, map_tasks: int, reduce_tasks: int,
                          capabilities: Set[str], resources: Dict[str, float]) -> DistributedTask:
    """Create a map-reduce task"""
    return DistributedTask(
        task_id=f"mapreduce_{int(time.time())}_{name}",
        name=name,
        execution_mode=TaskExecutionMode.MAP_REDUCE,
        required_capabilities=capabilities,
        required_resources=resources,
        payload={'map_tasks': map_tasks, 'reduce_tasks': reduce_tasks}
    )


def create_pipeline_task(name: str, stages: List[str], capabilities: Set[str], 
                        resources: Dict[str, float]) -> DistributedTask:
    """Create a pipeline task"""
    return DistributedTask(
        task_id=f"pipeline_{int(time.time())}_{name}",
        name=name,
        execution_mode=TaskExecutionMode.PIPELINE,
        required_capabilities=capabilities,
        required_resources=resources,
        payload={'stages': stages}
    )