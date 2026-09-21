#!/usr/bin/env python3
"""
SuperInstance Clustering System
Handles horizontal scaling, service discovery, and distributed coordination
"""

import asyncio
import time
import json
import logging
import hashlib
import random
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import socket
from collections import defaultdict, deque

# Initialize logger
logger = logging.getLogger(__name__)

class NodeRole(Enum):
    MASTER = "master"
    WORKER = "worker"
    COORDINATOR = "coordinator"
    EDGE = "edge"

class NodeStatus(Enum):
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    OFFLINE = "offline"

@dataclass
class ClusterNode:
    """Represents a node in the cluster"""
    id: str
    hostname: str
    port: int
    role: NodeRole
    status: NodeStatus = NodeStatus.INITIALIZING
    capabilities: Set[str] = field(default_factory=set)
    resources: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = 0.0
    join_time: float = 0.0
    
    # Performance metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_usage: float = 0.0
    active_connections: int = 0
    request_count: int = 0
    error_count: int = 0
    
    @property
    def is_healthy(self) -> bool:
        return self.status in [NodeStatus.HEALTHY, NodeStatus.DEGRADED]
    
    @property
    def load_factor(self) -> float:
        """Calculate node load factor (0.0 to 1.0)"""
        return (self.cpu_usage + self.memory_usage + self.disk_usage) / 300.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count

@dataclass
class ServiceEndpoint:
    """Represents a service endpoint"""
    service_name: str
    node_id: str
    host: str
    port: int
    path: str = "/"
    protocol: str = "http"
    health_check_path: str = "/health"
    tags: Set[str] = field(default_factory=set)
    weight: float = 1.0
    
    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}{self.path}"

class ServiceRegistry:
    """Service discovery and registry"""
    
    def __init__(self):
        self.services: Dict[str, List[ServiceEndpoint]] = defaultdict(list)
        self.service_watchers: Dict[str, List] = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def register_service(self, endpoint: ServiceEndpoint):
        """Register a service endpoint"""
        async with self.lock:
            self.services[endpoint.service_name].append(endpoint)
            logger.info(f"Registered service {endpoint.service_name} at {endpoint.url}")
            
            # Notify watchers
            for callback in self.service_watchers[endpoint.service_name]:
                try:
                    await callback('register', endpoint)
                except Exception as e:
                    logger.error(f"Service watcher error: {e}")
    
    async def deregister_service(self, service_name: str, node_id: str):
        """Deregister service endpoints for a node"""
        async with self.lock:
            if service_name in self.services:
                endpoints_to_remove = [
                    ep for ep in self.services[service_name]
                    if ep.node_id == node_id
                ]
                
                for endpoint in endpoints_to_remove:
                    self.services[service_name].remove(endpoint)
                    logger.info(f"Deregistered service {service_name} from node {node_id}")
                    
                    # Notify watchers
                    for callback in self.service_watchers[service_name]:
                        try:
                            await callback('deregister', endpoint)
                        except Exception as e:
                            logger.error(f"Service watcher error: {e}")
    
    def discover_service(self, service_name: str, 
                        tags: Optional[Set[str]] = None) -> List[ServiceEndpoint]:
        """Discover service endpoints"""
        endpoints = self.services.get(service_name, [])
        
        if tags:
            endpoints = [ep for ep in endpoints if tags.issubset(ep.tags)]
        
        return endpoints
    
    async def watch_service(self, service_name: str, callback):
        """Watch for service changes"""
        self.service_watchers[service_name].append(callback)

class ConsensusManager:
    """Distributed consensus for cluster coordination"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.term = 0
        self.voted_for: Optional[str] = None
        self.log: List[Dict[str, Any]] = []
        self.commit_index = 0
        self.last_applied = 0
        self.leader_id: Optional[str] = None
        self.state = "follower"  # follower, candidate, leader
        self.election_timeout = 5.0
        self.heartbeat_interval = 1.0
        self.last_heartbeat = 0.0
        self.votes_received: Set[str] = set()
    
    async def start_election(self):
        """Start leader election process"""
        self.state = "candidate"
        self.term += 1
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}
        self.last_heartbeat = time.time()
        
        logger.info(f"Node {self.node_id} starting election for term {self.term}")
    
    async def handle_vote_request(self, candidate_id: str, term: int, 
                                 last_log_index: int, last_log_term: int) -> bool:
        """Handle vote request from candidate"""
        if term < self.term:
            return False
        
        if term > self.term:
            self.term = term
            self.voted_for = None
            self.state = "follower"
        
        if (self.voted_for is None or self.voted_for == candidate_id):
            # Check if candidate's log is up to date
            our_last_index = len(self.log) - 1
            our_last_term = self.log[-1]['term'] if self.log else 0
            
            if (last_log_term > our_last_term or 
                (last_log_term == our_last_term and last_log_index >= our_last_index)):
                self.voted_for = candidate_id
                self.last_heartbeat = time.time()
                logger.info(f"Node {self.node_id} voted for {candidate_id} in term {term}")
                return True
        
        return False
    
    async def handle_vote_response(self, node_id: str, term: int, granted: bool):
        """Handle vote response"""
        if self.state != "candidate" or term != self.term:
            return
        
        if granted:
            self.votes_received.add(node_id)
            logger.debug(f"Node {self.node_id} received vote from {node_id} ({len(self.votes_received)} votes)")
    
    async def become_leader(self, cluster_size: int):
        """Become cluster leader"""
        if len(self.votes_received) > cluster_size // 2:
            self.state = "leader"
            self.leader_id = self.node_id
            logger.info(f"Node {self.node_id} became leader for term {self.term}")
            return True
        return False
    
    async def handle_heartbeat(self, leader_id: str, term: int):
        """Handle heartbeat from leader"""
        if term >= self.term:
            self.term = term
            self.leader_id = leader_id
            self.state = "follower"
            self.last_heartbeat = time.time()
            return True
        return False

class ClusterManager:
    """Main cluster management system"""
    
    def __init__(self, node_id: str, hostname: str, port: int, role: NodeRole):
        self.local_node = ClusterNode(
            id=node_id,
            hostname=hostname,
            port=port,
            role=role,
            join_time=time.time()
        )
        
        self.nodes: Dict[str, ClusterNode] = {node_id: self.local_node}
        self.service_registry = ServiceRegistry()
        self.consensus = ConsensusManager(node_id)
        
        # Configuration
        self.heartbeat_interval = 5.0
        self.node_timeout = 15.0
        self.health_check_interval = 30.0
        
        # State
        self.running = False
        self.cluster_events = deque(maxlen=1000)
        
        # Coordination
        self.coordination_tasks: Dict[str, Any] = {}
        self.distributed_locks: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """Initialize cluster manager"""
        logger.info(f"Initializing cluster node {self.local_node.id}")
        
        self.local_node.status = NodeStatus.HEALTHY
        self.local_node.last_heartbeat = time.time()
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._consensus_loop())
        asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Cluster node {self.local_node.id} initialized successfully")
    
    async def join_cluster(self, seed_nodes: List[Tuple[str, int]]):
        """Join an existing cluster"""
        logger.info(f"Attempting to join cluster via seed nodes: {seed_nodes}")
        
        for seed_host, seed_port in seed_nodes:
            try:
                await self._contact_seed_node(seed_host, seed_port)
                logger.info(f"Successfully joined cluster via {seed_host}:{seed_port}")
                return True
            except Exception as e:
                logger.warning(f"Failed to contact seed node {seed_host}:{seed_port}: {e}")
        
        logger.warning("Failed to join cluster, starting as single node")
        return False
    
    async def _contact_seed_node(self, host: str, port: int):
        """Contact a seed node to join cluster"""
        url = f"http://{host}:{port}/cluster/join"
        node_info = {
            'node_id': self.local_node.id,
            'hostname': self.local_node.hostname,
            'port': self.local_node.port,
            'role': self.local_node.role.value,
            'capabilities': list(self.local_node.capabilities),
            'metadata': self.local_node.metadata
        }
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=node_info) as response:
                if response.status == 200:
                    cluster_info = await response.json()
                    await self._update_cluster_topology(cluster_info)
                else:
                    raise Exception(f"Join request rejected: {response.status}")
    
    async def handle_join_request(self, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle join request from another node"""
        node = ClusterNode(
            id=node_info['node_id'],
            hostname=node_info['hostname'],
            port=node_info['port'],
            role=NodeRole(node_info['role']),
            capabilities=set(node_info.get('capabilities', [])),
            metadata=node_info.get('metadata', {}),
            join_time=time.time(),
            last_heartbeat=time.time(),
            status=NodeStatus.HEALTHY
        )
        
        self.nodes[node.id] = node
        
        # Log cluster event
        event = {
            'type': 'node_joined',
            'node_id': node.id,
            'timestamp': time.time(),
            'details': node_info
        }
        self.cluster_events.append(event)
        
        logger.info(f"Node {node.id} joined cluster")
        
        # Return current cluster state
        return {
            'nodes': {
                node_id: {
                    'hostname': n.hostname,
                    'port': n.port,
                    'role': n.role.value,
                    'status': n.status.value,
                    'capabilities': list(n.capabilities)
                }
                for node_id, n in self.nodes.items()
            },
            'leader': self.consensus.leader_id,
            'services': dict(self.service_registry.services)
        }
    
    async def _update_cluster_topology(self, cluster_info: Dict[str, Any]):
        """Update local view of cluster topology"""
        for node_id, node_data in cluster_info.get('nodes', {}).items():
            if node_id not in self.nodes:
                node = ClusterNode(
                    id=node_id,
                    hostname=node_data['hostname'],
                    port=node_data['port'],
                    role=NodeRole(node_data['role']),
                    status=NodeStatus(node_data['status']),
                    capabilities=set(node_data.get('capabilities', [])),
                    last_heartbeat=time.time()
                )
                self.nodes[node_id] = node
        
        # Update leader info
        if cluster_info.get('leader'):
            self.consensus.leader_id = cluster_info['leader']
        
        # Update service registry
        for service_name, endpoints in cluster_info.get('services', {}).items():
            for endpoint_data in endpoints:
                endpoint = ServiceEndpoint(**endpoint_data)
                await self.service_registry.register_service(endpoint)
    
    async def leave_cluster(self):
        """Leave the cluster gracefully"""
        logger.info(f"Node {self.local_node.id} leaving cluster")
        
        # Mark as draining
        self.local_node.status = NodeStatus.DRAINING
        
        # Notify other nodes
        await self._broadcast_message({
            'type': 'node_leaving',
            'node_id': self.local_node.id,
            'timestamp': time.time()
        })
        
        # Deregister services
        for service_name in list(self.service_registry.services.keys()):
            await self.service_registry.deregister_service(service_name, self.local_node.id)
        
        # Wait a bit for graceful shutdown
        await asyncio.sleep(2.0)
        
        self.running = False
        self.local_node.status = NodeStatus.OFFLINE
        
        logger.info(f"Node {self.local_node.id} left cluster")
    
    async def _heartbeat_loop(self):
        """Background heartbeat loop"""
        while self.running:
            try:
                await self._send_heartbeats()
                await self._check_node_timeouts()
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(1.0)
    
    async def _send_heartbeats(self):
        """Send heartbeat to all known nodes"""
        self.local_node.last_heartbeat = time.time()
        
        heartbeat_data = {
            'type': 'heartbeat',
            'node_id': self.local_node.id,
            'timestamp': self.local_node.last_heartbeat,
            'status': self.local_node.status.value,
            'resources': {
                'cpu_usage': self.local_node.cpu_usage,
                'memory_usage': self.local_node.memory_usage,
                'active_connections': self.local_node.active_connections
            },
            'leader_id': self.consensus.leader_id,
            'term': self.consensus.term
        }
        
        # Update local resource metrics
        await self._update_resource_metrics()
        
        # Send to all other nodes
        for node_id, node in self.nodes.items():
            if node_id != self.local_node.id and node.is_healthy:
                try:
                    await self._send_message_to_node(node, heartbeat_data)
                except Exception as e:
                    logger.debug(f"Heartbeat to {node_id} failed: {e}")
    
    async def _update_resource_metrics(self):
        """Update local resource metrics"""
        try:
            import psutil
            
            # CPU and memory usage
            self.local_node.cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            self.local_node.memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.local_node.disk_usage = (disk.used / disk.total) * 100
            
            # Network usage (simplified)
            net_io = psutil.net_io_counters()
            self.local_node.network_usage = (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024)  # MB
            
        except ImportError:
            # Fallback if psutil not available
            self.local_node.cpu_usage = random.uniform(10, 80)
            self.local_node.memory_usage = random.uniform(20, 70)
            self.local_node.disk_usage = random.uniform(10, 50)
    
    async def handle_heartbeat(self, heartbeat_data: Dict[str, Any]):
        """Handle heartbeat from another node"""
        node_id = heartbeat_data['node_id']
        
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.last_heartbeat = heartbeat_data['timestamp']
            node.status = NodeStatus(heartbeat_data.get('status', 'healthy'))
            
            # Update resource metrics
            resources = heartbeat_data.get('resources', {})
            node.cpu_usage = resources.get('cpu_usage', 0.0)
            node.memory_usage = resources.get('memory_usage', 0.0)
            node.active_connections = resources.get('active_connections', 0)
            
            # Handle consensus information
            if 'leader_id' in heartbeat_data:
                await self.consensus.handle_heartbeat(
                    heartbeat_data.get('leader_id'),
                    heartbeat_data.get('term', 0)
                )
    
    async def _check_node_timeouts(self):
        """Check for timed out nodes"""
        current_time = time.time()
        timed_out_nodes = []
        
        for node_id, node in self.nodes.items():
            if (node_id != self.local_node.id and 
                node.status != NodeStatus.OFFLINE and
                current_time - node.last_heartbeat > self.node_timeout):
                
                timed_out_nodes.append(node_id)
        
        for node_id in timed_out_nodes:
            logger.warning(f"Node {node_id} timed out")
            self.nodes[node_id].status = NodeStatus.OFFLINE
            
            # Deregister services for this node
            for service_name in list(self.service_registry.services.keys()):
                await self.service_registry.deregister_service(service_name, node_id)
            
            # Log event
            event = {
                'type': 'node_timeout',
                'node_id': node_id,
                'timestamp': current_time
            }
            self.cluster_events.append(event)
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while self.running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(10.0)
    
    async def _perform_health_checks(self):
        """Perform health checks on services"""
        for service_name, endpoints in self.service_registry.services.items():
            for endpoint in endpoints:
                try:
                    await self._check_service_health(endpoint)
                except Exception as e:
                    logger.debug(f"Health check failed for {endpoint.service_name}: {e}")
    
    async def _check_service_health(self, endpoint: ServiceEndpoint):
        """Check health of a service endpoint"""
        health_url = f"{endpoint.protocol}://{endpoint.host}:{endpoint.port}{endpoint.health_check_path}"
        
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(health_url) as response:
                if response.status != 200:
                    logger.warning(f"Service {endpoint.service_name} health check failed: {response.status}")
    
    async def _consensus_loop(self):
        """Background consensus loop for leader election"""
        while self.running:
            try:
                # Only participate in consensus if we're a coordinator or master
                if self.local_node.role in [NodeRole.COORDINATOR, NodeRole.MASTER]:
                    await self._handle_consensus()
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Consensus loop error: {e}")
                await asyncio.sleep(5.0)
    
    async def _handle_consensus(self):
        """Handle consensus algorithm"""
        current_time = time.time()
        
        if self.consensus.state == "follower":
            # Check if we need to start election
            if (current_time - self.consensus.last_heartbeat > self.consensus.election_timeout and
                not self.consensus.leader_id):
                await self.consensus.start_election()
                await self._broadcast_vote_request()
        
        elif self.consensus.state == "candidate":
            # Check if we won the election
            active_nodes = len([n for n in self.nodes.values() if n.is_healthy])
            if await self.consensus.become_leader(active_nodes):
                await self._broadcast_leadership()
        
        elif self.consensus.state == "leader":
            # Send heartbeats to maintain leadership
            if current_time - self.consensus.last_heartbeat >= self.consensus.heartbeat_interval:
                await self._broadcast_leadership()
                self.consensus.last_heartbeat = current_time
    
    async def _broadcast_vote_request(self):
        """Broadcast vote request to all nodes"""
        vote_request = {
            'type': 'vote_request',
            'candidate_id': self.local_node.id,
            'term': self.consensus.term,
            'last_log_index': len(self.consensus.log) - 1,
            'last_log_term': self.consensus.log[-1]['term'] if self.consensus.log else 0
        }
        
        await self._broadcast_message(vote_request)
    
    async def _broadcast_leadership(self):
        """Broadcast leadership heartbeat"""
        leadership_msg = {
            'type': 'leadership_heartbeat',
            'leader_id': self.local_node.id,
            'term': self.consensus.term,
            'timestamp': time.time()
        }
        
        await self._broadcast_message(leadership_msg)
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all nodes"""
        for node_id, node in self.nodes.items():
            if node_id != self.local_node.id and node.is_healthy:
                try:
                    await self._send_message_to_node(node, message)
                except Exception as e:
                    logger.debug(f"Broadcast to {node_id} failed: {e}")
    
    async def _send_message_to_node(self, node: ClusterNode, message: Dict[str, Any]):
        """Send message to specific node"""
        url = f"http://{node.hostname}:{node.port}/cluster/message"
        
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=message) as response:
                if response.status != 200:
                    raise Exception(f"Message sending failed: {response.status}")
    
    async def handle_cluster_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming cluster message"""
        msg_type = message.get('type')
        
        if msg_type == 'heartbeat':
            await self.handle_heartbeat(message)
            return {'status': 'ok'}
        
        elif msg_type == 'vote_request':
            granted = await self.consensus.handle_vote_request(
                message['candidate_id'],
                message['term'],
                message['last_log_index'],
                message['last_log_term']
            )
            return {'vote_granted': granted, 'term': self.consensus.term}
        
        elif msg_type == 'vote_response':
            await self.consensus.handle_vote_response(
                message['node_id'],
                message['term'],
                message['vote_granted']
            )
            return {'status': 'ok'}
        
        elif msg_type == 'leadership_heartbeat':
            await self.consensus.handle_heartbeat(
                message['leader_id'],
                message['term']
            )
            return {'status': 'ok'}
        
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            return {'status': 'unknown_type'}
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.running:
            try:
                await self._cleanup_expired_data()
                await asyncio.sleep(300)  # Cleanup every 5 minutes
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired_data(self):
        """Clean up expired cluster data"""
        current_time = time.time()
        
        # Remove offline nodes after extended period
        offline_cutoff = current_time - 3600  # 1 hour
        nodes_to_remove = [
            node_id for node_id, node in self.nodes.items()
            if (node.status == NodeStatus.OFFLINE and 
                node.last_heartbeat < offline_cutoff and
                node_id != self.local_node.id)
        ]
        
        for node_id in nodes_to_remove:
            del self.nodes[node_id]
            logger.info(f"Removed expired node {node_id} from cluster")
        
        # Trim old cluster events
        event_cutoff = current_time - 3600  # Keep 1 hour of events
        while (self.cluster_events and 
               self.cluster_events[0]['timestamp'] < event_cutoff):
            self.cluster_events.popleft()
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get current cluster status"""
        return {
            'local_node': {
                'id': self.local_node.id,
                'role': self.local_node.role.value,
                'status': self.local_node.status.value,
                'uptime': time.time() - self.local_node.join_time
            },
            'cluster': {
                'total_nodes': len(self.nodes),
                'healthy_nodes': len([n for n in self.nodes.values() if n.is_healthy]),
                'leader': self.consensus.leader_id,
                'term': self.consensus.term
            },
            'services': {
                service: len(endpoints) 
                for service, endpoints in self.service_registry.services.items()
            },
            'nodes': {
                node_id: {
                    'hostname': node.hostname,
                    'role': node.role.value,
                    'status': node.status.value,
                    'load_factor': node.load_factor,
                    'uptime': time.time() - node.join_time
                }
                for node_id, node in self.nodes.items()
            }
        }
    
    async def acquire_distributed_lock(self, lock_name: str, timeout: float = 30.0) -> bool:
        """Acquire a distributed lock"""
        if self.consensus.leader_id != self.local_node.id:
            # Forward to leader
            if self.consensus.leader_id:
                leader_node = self.nodes.get(self.consensus.leader_id)
                if leader_node:
                    try:
                        url = f"http://{leader_node.hostname}:{leader_node.port}/cluster/lock"
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json={
                                'action': 'acquire',
                                'lock_name': lock_name,
                                'node_id': self.local_node.id,
                                'timeout': timeout
                            }) as response:
                                result = await response.json()
                                return result.get('acquired', False)
                    except Exception as e:
                        logger.error(f"Failed to acquire distributed lock: {e}")
            return False
        
        # We are the leader, handle locally
        current_time = time.time()
        
        if lock_name in self.distributed_locks:
            lock_info = self.distributed_locks[lock_name]
            if current_time < lock_info['expires']:
                return False  # Lock is held
        
        # Acquire the lock
        self.distributed_locks[lock_name] = {
            'owner': self.local_node.id,
            'acquired': current_time,
            'expires': current_time + timeout
        }
        
        logger.info(f"Distributed lock '{lock_name}' acquired by {self.local_node.id}")
        return True
    
    async def release_distributed_lock(self, lock_name: str) -> bool:
        """Release a distributed lock"""
        if self.consensus.leader_id != self.local_node.id:
            # Forward to leader
            if self.consensus.leader_id:
                leader_node = self.nodes.get(self.consensus.leader_id)
                if leader_node:
                    try:
                        url = f"http://{leader_node.hostname}:{leader_node.port}/cluster/lock"
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json={
                                'action': 'release',
                                'lock_name': lock_name,
                                'node_id': self.local_node.id
                            }) as response:
                                result = await response.json()
                                return result.get('released', False)
                    except Exception as e:
                        logger.error(f"Failed to release distributed lock: {e}")
            return False
        
        # We are the leader, handle locally
        if lock_name in self.distributed_locks:
            lock_info = self.distributed_locks[lock_name]
            if lock_info['owner'] == self.local_node.id:
                del self.distributed_locks[lock_name]
                logger.info(f"Distributed lock '{lock_name}' released by {self.local_node.id}")
                return True
        
        return False

# Factory function for creating cluster manager
def create_cluster_manager(node_id: Optional[str] = None, 
                          hostname: Optional[str] = None,
                          port: int = 9000,
                          role: NodeRole = NodeRole.WORKER) -> ClusterManager:
    """Create a cluster manager instance"""
    
    if not node_id:
        node_id = f"node-{int(time.time())}-{random.randint(1000, 9999)}"
    
    if not hostname:
        hostname = socket.gethostname()
    
    return ClusterManager(node_id, hostname, port, role)

# Example usage
async def example_cluster_setup():
    """Example of setting up a cluster"""
    
    # Create cluster manager
    cluster = create_cluster_manager(
        node_id="example-node-1",
        hostname="localhost",
        port=9001,
        role=NodeRole.COORDINATOR
    )
    
    # Initialize
    await cluster.initialize()
    
    # Register some services
    service_endpoint = ServiceEndpoint(
        service_name="ml-service",
        node_id=cluster.local_node.id,
        host="localhost",
        port=8001,
        tags={"ml", "nlp"}
    )
    
    await cluster.service_registry.register_service(service_endpoint)
    
    # Get cluster status
    status = cluster.get_cluster_status()
    print(f"Cluster status: {json.dumps(status, indent=2)}")
    
    # Simulate running
    await asyncio.sleep(5)
    
    # Shutdown
    await cluster.leave_cluster()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run example
    asyncio.run(example_cluster_setup())