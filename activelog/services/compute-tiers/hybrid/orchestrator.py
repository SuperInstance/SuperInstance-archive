#!/usr/bin/env python3
"""
Hybrid Cloud Orchestrator for ActiveLog Compute Tiers
Intelligent orchestration of workloads across local and cloud infrastructure
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import subprocess
import psutil
import socket

logger = logging.getLogger(__name__)

class InfrastructureType(Enum):
    """Types of infrastructure"""
    LOCAL = "local"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    EDGE = "edge"
    HYBRID = "hybrid"

class WorkloadAffinity(Enum):
    """Workload affinity preferences"""
    LOCAL_PREFERRED = "local_preferred"
    CLOUD_PREFERRED = "cloud_preferred"
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    COMPLIANCE_REQUIRED = "compliance_required"

class OrchestrationStrategy(Enum):
    """Orchestration strategies"""
    BURST_TO_CLOUD = "burst_to_cloud"
    CLOUD_FIRST = "cloud_first"
    LOCAL_FIRST = "local_first"
    BALANCED = "balanced"
    DATA_GRAVITY = "data_gravity"

@dataclass
class InfrastructureNode:
    """Infrastructure node specification"""
    node_id: str
    node_name: str
    infrastructure_type: InfrastructureType
    location: str
    capacity: Dict[str, float]  # cpu_cores, memory_gb, storage_gb, gpu_count
    current_utilization: Dict[str, float]
    cost_per_hour: float
    latency_ms: float
    reliability_score: float
    compliance_level: str
    available: bool
    last_heartbeat: datetime

@dataclass
class WorkloadSpec:
    """Workload specification for hybrid orchestration"""
    workload_id: str
    workload_name: str
    resource_requirements: Dict[str, float]
    data_requirements: Dict[str, Any]
    latency_requirements: Dict[str, float]
    compliance_requirements: List[str]
    affinity: WorkloadAffinity
    estimated_duration_minutes: int
    priority: int
    dependencies: List[str]
    preferred_locations: List[str]

@dataclass
class OrchestrationDecision:
    """Result of orchestration decision"""
    workload_id: str
    selected_nodes: List[str]
    node_details: List[Dict[str, Any]]
    orchestration_strategy: OrchestrationStrategy
    estimated_cost: float
    estimated_latency_ms: float
    data_movement_plan: Dict[str, Any]
    failover_plan: Dict[str, Any]
    monitoring_plan: Dict[str, Any]
    reasoning: str
    confidence_score: float

class HybridOrchestrator:
    """Orchestrates workloads across hybrid infrastructure"""
    
    def __init__(self, config):
        self.config = config
        
        # Infrastructure registry
        self.infrastructure_nodes: Dict[str, InfrastructureNode] = {}
        
        # Workload tracking
        self.active_workloads: Dict[str, Dict[str, Any]] = {}
        
        # Performance history
        self.performance_history: List[Dict[str, Any]] = []
        
        # Initialize infrastructure nodes
        self._initialize_infrastructure_nodes()
        
        # Orchestration policies
        self.orchestration_policies = {
            OrchestrationStrategy.BURST_TO_CLOUD: {
                'local_threshold_percent': 80,
                'cost_weight': 0.3,
                'latency_weight': 0.4,
                'capacity_weight': 0.3
            },
            OrchestrationStrategy.CLOUD_FIRST: {
                'local_threshold_percent': 95,
                'cost_weight': 0.2,
                'latency_weight': 0.3,
                'capacity_weight': 0.5
            },
            OrchestrationStrategy.LOCAL_FIRST: {
                'local_threshold_percent': 20,
                'cost_weight': 0.4,
                'latency_weight': 0.4,
                'capacity_weight': 0.2
            },
            OrchestrationStrategy.BALANCED: {
                'local_threshold_percent': 60,
                'cost_weight': 0.4,
                'latency_weight': 0.3,
                'capacity_weight': 0.3
            },
            OrchestrationStrategy.DATA_GRAVITY: {
                'local_threshold_percent': 50,
                'cost_weight': 0.2,
                'latency_weight': 0.5,
                'capacity_weight': 0.3
            }
        }

    def _initialize_infrastructure_nodes(self):
        """Initialize infrastructure node registry"""
        # Local infrastructure
        local_node = self._discover_local_infrastructure()
        self.infrastructure_nodes[local_node.node_id] = local_node
        
        # Cloud infrastructure (simulated)
        cloud_nodes = self._initialize_cloud_nodes()
        for node in cloud_nodes:
            self.infrastructure_nodes[node.node_id] = node
        
        # Edge infrastructure
        edge_nodes = self._initialize_edge_nodes()
        for node in edge_nodes:
            self.infrastructure_nodes[node.node_id] = node

    def _discover_local_infrastructure(self) -> InfrastructureNode:
        """Discover local infrastructure capabilities"""
        try:
            # Get system information
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check for GPU
            gpu_count = 0
            try:
                result = subprocess.run(['nvidia-smi', '--list-gpus'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    gpu_count = len(result.stdout.strip().split('\n'))
            except:
                pass
            
            # Get hostname
            hostname = socket.gethostname()
            
            capacity = {
                'cpu_cores': float(cpu_count),
                'memory_gb': memory.total / (1024**3),
                'storage_gb': disk.total / (1024**3),
                'gpu_count': float(gpu_count)
            }
            
            current_utilization = {
                'cpu_cores': psutil.cpu_percent() / 100 * cpu_count,
                'memory_gb': memory.used / (1024**3),
                'storage_gb': disk.used / (1024**3),
                'gpu_count': 0.0  # Would need GPU monitoring
            }
            
            return InfrastructureNode(
                node_id=f'local_{hostname}',
                node_name=f'Local Node ({hostname})',
                infrastructure_type=InfrastructureType.LOCAL,
                location='on-premises',
                capacity=capacity,
                current_utilization=current_utilization,
                cost_per_hour=0.0,  # No direct cost for local
                latency_ms=0.1,  # Minimal local latency
                reliability_score=0.95,
                compliance_level='internal',
                available=True,
                last_heartbeat=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to discover local infrastructure: {e}")
            # Return minimal local node
            return InfrastructureNode(
                node_id='local_unknown',
                node_name='Local Node',
                infrastructure_type=InfrastructureType.LOCAL,
                location='on-premises',
                capacity={'cpu_cores': 4.0, 'memory_gb': 8.0, 'storage_gb': 100.0, 'gpu_count': 0.0},
                current_utilization={'cpu_cores': 1.0, 'memory_gb': 2.0, 'storage_gb': 20.0, 'gpu_count': 0.0},
                cost_per_hour=0.0,
                latency_ms=0.1,
                reliability_score=0.95,
                compliance_level='internal',
                available=True,
                last_heartbeat=datetime.utcnow()
            )

    def _initialize_cloud_nodes(self) -> List[InfrastructureNode]:
        """Initialize cloud infrastructure nodes"""
        nodes = []
        
        # AWS nodes
        aws_nodes = [
            {
                'node_id': 'aws_us_east_1_m5_large_pool',
                'node_name': 'AWS US-East-1 M5.Large Pool',
                'location': 'us-east-1',
                'capacity': {'cpu_cores': 100.0, 'memory_gb': 800.0, 'storage_gb': 10000.0, 'gpu_count': 0.0},
                'cost_per_hour': 9.6,  # 100 instances * $0.096/hour
                'latency_ms': 50.0,
                'reliability_score': 0.99
            },
            {
                'node_id': 'aws_us_west_2_c5_xlarge_pool',
                'node_name': 'AWS US-West-2 C5.XLarge Pool',
                'location': 'us-west-2',
                'capacity': {'cpu_cores': 200.0, 'memory_gb': 800.0, 'storage_gb': 8000.0, 'gpu_count': 0.0},
                'cost_per_hour': 17.0,  # 50 instances * $0.34/hour
                'latency_ms': 80.0,
                'reliability_score': 0.995
            },
            {
                'node_id': 'aws_us_east_1_g4dn_pool',
                'node_name': 'AWS US-East-1 G4DN GPU Pool',
                'location': 'us-east-1',
                'capacity': {'cpu_cores': 80.0, 'memory_gb': 320.0, 'storage_gb': 4000.0, 'gpu_count': 20.0},
                'cost_per_hour': 26.08,  # 20 instances * $1.304/hour (g4dn.xlarge)
                'latency_ms': 55.0,
                'reliability_score': 0.98
            }
        ]
        
        for node_data in aws_nodes:
            current_utilization = {
                'cpu_cores': node_data['capacity']['cpu_cores'] * 0.3,  # 30% utilized
                'memory_gb': node_data['capacity']['memory_gb'] * 0.4,  # 40% utilized
                'storage_gb': node_data['capacity']['storage_gb'] * 0.2,  # 20% utilized
                'gpu_count': node_data['capacity']['gpu_count'] * 0.1   # 10% utilized
            }
            
            nodes.append(InfrastructureNode(
                node_id=node_data['node_id'],
                node_name=node_data['node_name'],
                infrastructure_type=InfrastructureType.AWS,
                location=node_data['location'],
                capacity=node_data['capacity'],
                current_utilization=current_utilization,
                cost_per_hour=node_data['cost_per_hour'],
                latency_ms=node_data['latency_ms'],
                reliability_score=node_data['reliability_score'],
                compliance_level='cloud',
                available=True,
                last_heartbeat=datetime.utcnow()
            ))
        
        # Azure nodes
        azure_nodes = [
            {
                'node_id': 'azure_east_us_standard_d4s_pool',
                'node_name': 'Azure East US Standard D4s Pool',
                'location': 'eastus',
                'capacity': {'cpu_cores': 160.0, 'memory_gb': 640.0, 'storage_gb': 6400.0, 'gpu_count': 0.0},
                'cost_per_hour': 15.84,  # 40 instances * $0.396/hour
                'latency_ms': 60.0,
                'reliability_score': 0.995
            }
        ]
        
        for node_data in azure_nodes:
            current_utilization = {
                'cpu_cores': node_data['capacity']['cpu_cores'] * 0.25,
                'memory_gb': node_data['capacity']['memory_gb'] * 0.35,
                'storage_gb': node_data['capacity']['storage_gb'] * 0.15,
                'gpu_count': 0.0
            }
            
            nodes.append(InfrastructureNode(
                node_id=node_data['node_id'],
                node_name=node_data['node_name'],
                infrastructure_type=InfrastructureType.AZURE,
                location=node_data['location'],
                capacity=node_data['capacity'],
                current_utilization=current_utilization,
                cost_per_hour=node_data['cost_per_hour'],
                latency_ms=node_data['latency_ms'],
                reliability_score=node_data['reliability_score'],
                compliance_level='cloud',
                available=True,
                last_heartbeat=datetime.utcnow()
            ))
        
        return nodes

    def _initialize_edge_nodes(self) -> List[InfrastructureNode]:
        """Initialize edge compute nodes"""
        edge_nodes = [
            {
                'node_id': 'edge_chicago_micro',
                'node_name': 'Edge Chicago Micro Node',
                'location': 'chicago',
                'capacity': {'cpu_cores': 8.0, 'memory_gb': 32.0, 'storage_gb': 500.0, 'gpu_count': 1.0},
                'cost_per_hour': 1.2,
                'latency_ms': 15.0,
                'reliability_score': 0.92
            },
            {
                'node_id': 'edge_seattle_micro',
                'node_name': 'Edge Seattle Micro Node',
                'location': 'seattle',
                'capacity': {'cpu_cores': 8.0, 'memory_gb': 32.0, 'storage_gb': 500.0, 'gpu_count': 1.0},
                'cost_per_hour': 1.15,
                'latency_ms': 12.0,
                'reliability_score': 0.94
            }
        ]
        
        nodes = []
        for node_data in edge_nodes:
            current_utilization = {
                'cpu_cores': node_data['capacity']['cpu_cores'] * 0.2,
                'memory_gb': node_data['capacity']['memory_gb'] * 0.3,
                'storage_gb': node_data['capacity']['storage_gb'] * 0.4,
                'gpu_count': node_data['capacity']['gpu_count'] * 0.1
            }
            
            nodes.append(InfrastructureNode(
                node_id=node_data['node_id'],
                node_name=node_data['node_name'],
                infrastructure_type=InfrastructureType.EDGE,
                location=node_data['location'],
                capacity=node_data['capacity'],
                current_utilization=current_utilization,
                cost_per_hour=node_data['cost_per_hour'],
                latency_ms=node_data['latency_ms'],
                reliability_score=node_data['reliability_score'],
                compliance_level='edge',
                available=True,
                last_heartbeat=datetime.utcnow()
            ))
        
        return nodes

    def orchestrate(self, workload_spec: Dict[str, Any], 
                   hybrid_preferences: Dict[str, Any] = None) -> OrchestrationDecision:
        """Orchestrate workload placement across hybrid infrastructure"""
        try:
            # Parse workload specification
            workload = self._parse_workload_spec(workload_spec)
            preferences = hybrid_preferences or {}
            
            # Determine orchestration strategy
            strategy = self._determine_orchestration_strategy(workload, preferences)
            
            # Find suitable nodes
            suitable_nodes = self._find_suitable_nodes(workload, strategy)
            
            if not suitable_nodes:
                return self._create_error_decision(
                    workload.workload_id,
                    "No suitable infrastructure nodes found for workload requirements"
                )
            
            # Select optimal nodes
            selected_nodes = self._select_optimal_nodes(workload, suitable_nodes, strategy, preferences)
            
            # Calculate estimates
            estimated_cost = self._calculate_workload_cost(workload, selected_nodes)
            estimated_latency = self._estimate_workload_latency(workload, selected_nodes)
            
            # Generate plans
            data_movement_plan = self._generate_data_movement_plan(workload, selected_nodes)
            failover_plan = self._generate_failover_plan(workload, selected_nodes, suitable_nodes)
            monitoring_plan = self._generate_monitoring_plan(workload, selected_nodes)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(workload, selected_nodes, strategy)
            
            # Generate reasoning
            reasoning = self._generate_orchestration_reasoning(workload, selected_nodes, strategy, preferences)
            
            # Register active workload
            self.active_workloads[workload.workload_id] = {
                'workload': workload,
                'selected_nodes': [node.node_id for node in selected_nodes],
                'start_time': datetime.utcnow(),
                'strategy': strategy,
                'estimated_cost': estimated_cost
            }
            
            return OrchestrationDecision(
                workload_id=workload.workload_id,
                selected_nodes=[node.node_id for node in selected_nodes],
                node_details=[self._node_to_dict(node) for node in selected_nodes],
                orchestration_strategy=strategy,
                estimated_cost=estimated_cost,
                estimated_latency_ms=estimated_latency,
                data_movement_plan=data_movement_plan,
                failover_plan=failover_plan,
                monitoring_plan=monitoring_plan,
                reasoning=reasoning,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Failed to orchestrate workload: {e}")
            return self._create_error_decision(
                workload_spec.get('workload_id', 'unknown'),
                f"Orchestration error: {str(e)}"
            )

    def _parse_workload_spec(self, spec: Dict[str, Any]) -> WorkloadSpec:
        """Parse workload specification"""
        return WorkloadSpec(
            workload_id=spec.get('workload_id', f'workload_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'),
            workload_name=spec.get('workload_name', 'Unnamed Workload'),
            resource_requirements=spec.get('resource_requirements', {
                'cpu_cores': 2.0,
                'memory_gb': 4.0,
                'storage_gb': 20.0,
                'gpu_count': 0.0
            }),
            data_requirements=spec.get('data_requirements', {}),
            latency_requirements=spec.get('latency_requirements', {'max_latency_ms': 100.0}),
            compliance_requirements=spec.get('compliance_requirements', []),
            affinity=WorkloadAffinity(spec.get('affinity', 'cost_optimized')),
            estimated_duration_minutes=spec.get('estimated_duration_minutes', 60),
            priority=spec.get('priority', 5),
            dependencies=spec.get('dependencies', []),
            preferred_locations=spec.get('preferred_locations', [])
        )

    def _determine_orchestration_strategy(self, workload: WorkloadSpec, 
                                        preferences: Dict[str, Any]) -> OrchestrationStrategy:
        """Determine optimal orchestration strategy"""
        # Check explicit strategy preference
        preferred_strategy = preferences.get('strategy')
        if preferred_strategy:
            try:
                return OrchestrationStrategy(preferred_strategy)
            except ValueError:
                pass
        
        # Determine strategy based on workload characteristics
        if workload.affinity == WorkloadAffinity.LOCAL_PREFERRED:
            return OrchestrationStrategy.LOCAL_FIRST
        elif workload.affinity == WorkloadAffinity.CLOUD_PREFERRED:
            return OrchestrationStrategy.CLOUD_FIRST
        elif workload.affinity == WorkloadAffinity.LATENCY_OPTIMIZED:
            return OrchestrationStrategy.DATA_GRAVITY
        elif workload.affinity == WorkloadAffinity.COST_OPTIMIZED:
            return OrchestrationStrategy.BURST_TO_CLOUD
        else:
            return OrchestrationStrategy.BALANCED

    def _find_suitable_nodes(self, workload: WorkloadSpec, 
                           strategy: OrchestrationStrategy) -> List[InfrastructureNode]:
        """Find nodes suitable for workload"""
        suitable_nodes = []
        
        for node in self.infrastructure_nodes.values():
            # Check if node is available
            if not node.available:
                continue
            
            # Check heartbeat (node must be responsive)
            if (datetime.utcnow() - node.last_heartbeat).total_seconds() > 300:  # 5 minutes
                continue
            
            # Check resource capacity
            if not self._node_has_capacity(node, workload.resource_requirements):
                continue
            
            # Check compliance requirements
            if not self._node_meets_compliance(node, workload.compliance_requirements):
                continue
            
            # Check latency requirements
            max_latency = workload.latency_requirements.get('max_latency_ms', 1000.0)
            if node.latency_ms > max_latency:
                continue
            
            # Check location preferences
            if workload.preferred_locations:
                if node.location not in workload.preferred_locations:
                    continue
            
            suitable_nodes.append(node)
        
        return suitable_nodes

    def _node_has_capacity(self, node: InfrastructureNode, requirements: Dict[str, float]) -> bool:
        """Check if node has sufficient capacity"""
        for resource, required in requirements.items():
            if resource not in node.capacity:
                continue
            
            available = node.capacity[resource] - node.current_utilization[resource]
            if available < required:
                return False
        
        return True

    def _node_meets_compliance(self, node: InfrastructureNode, requirements: List[str]) -> bool:
        """Check if node meets compliance requirements"""
        if not requirements:
            return True
        
        # Simple compliance check based on node compliance level
        node_compliance_levels = {
            'internal': ['internal'],
            'edge': ['internal', 'edge'],
            'cloud': ['internal', 'cloud', 'SOC2', 'ISO27001'],
        }
        
        node_capabilities = node_compliance_levels.get(node.compliance_level, [])
        
        return all(req in node_capabilities for req in requirements)

    def _select_optimal_nodes(self, workload: WorkloadSpec, suitable_nodes: List[InfrastructureNode],
                            strategy: OrchestrationStrategy, preferences: Dict[str, Any]) -> List[InfrastructureNode]:
        """Select optimal nodes based on strategy"""
        if not suitable_nodes:
            return []
        
        # Score nodes based on strategy
        scored_nodes = []
        policy = self.orchestration_policies[strategy]
        
        for node in suitable_nodes:
            score = self._calculate_node_score(node, workload, policy, preferences)
            scored_nodes.append((score, node))
        
        # Sort by score (higher is better)
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        
        # Select nodes based on strategy
        selected_nodes = []
        
        # For most strategies, select single best node
        if scored_nodes:
            selected_nodes.append(scored_nodes[0][1])
        
        # For high-priority workloads, consider redundancy
        if workload.priority <= 2 and len(scored_nodes) > 1:
            # Add backup node from different infrastructure type if available
            primary_type = selected_nodes[0].infrastructure_type
            for score, node in scored_nodes[1:]:
                if node.infrastructure_type != primary_type:
                    selected_nodes.append(node)
                    break
        
        return selected_nodes

    def _calculate_node_score(self, node: InfrastructureNode, workload: WorkloadSpec,
                            policy: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Calculate node score based on policy"""
        score = 0.0
        
        # Cost score (lower cost is better)
        cost_score = max(0, 100 - (node.cost_per_hour * 10))  # Normalize cost
        score += cost_score * policy['cost_weight']
        
        # Latency score (lower latency is better)
        max_latency = workload.latency_requirements.get('max_latency_ms', 100.0)
        latency_score = max(0, 100 - (node.latency_ms / max_latency * 100))
        score += latency_score * policy['latency_weight']
        
        # Capacity score (more available capacity is better)
        capacity_scores = []
        for resource, required in workload.resource_requirements.items():
            if resource in node.capacity and node.capacity[resource] > 0:
                available = node.capacity[resource] - node.current_utilization[resource]
                utilization_after = (node.current_utilization[resource] + required) / node.capacity[resource]
                # Prefer nodes with moderate utilization (not empty, not full)
                capacity_score = 100 * (1 - abs(utilization_after - 0.7))  # Target 70% utilization
                capacity_scores.append(capacity_score)
        
        if capacity_scores:
            avg_capacity_score = sum(capacity_scores) / len(capacity_scores)
            score += avg_capacity_score * policy['capacity_weight']
        
        # Infrastructure type preference
        if workload.affinity == WorkloadAffinity.LOCAL_PREFERRED and node.infrastructure_type == InfrastructureType.LOCAL:
            score += 20
        elif workload.affinity == WorkloadAffinity.CLOUD_PREFERRED and node.infrastructure_type in [InfrastructureType.AWS, InfrastructureType.AZURE, InfrastructureType.GCP]:
            score += 20
        
        # Reliability bonus
        reliability_bonus = node.reliability_score * 10
        score += reliability_bonus
        
        # Location preference bonus
        if workload.preferred_locations and node.location in workload.preferred_locations:
            score += 15
        
        return score

    def _calculate_workload_cost(self, workload: WorkloadSpec, nodes: List[InfrastructureNode]) -> float:
        """Calculate estimated workload cost"""
        total_cost = 0.0
        duration_hours = workload.estimated_duration_minutes / 60.0
        
        for node in nodes:
            # Base node cost
            node_cost = node.cost_per_hour * duration_hours
            
            # Data transfer costs (simplified)
            data_size_gb = workload.data_requirements.get('input_data_gb', 0) + workload.data_requirements.get('output_data_gb', 0)
            if node.infrastructure_type != InfrastructureType.LOCAL and data_size_gb > 0:
                transfer_cost = data_size_gb * 0.09  # $0.09/GB transfer cost
                node_cost += transfer_cost
            
            total_cost += node_cost
        
        return round(total_cost, 2)

    def _estimate_workload_latency(self, workload: WorkloadSpec, nodes: List[InfrastructureNode]) -> float:
        """Estimate workload latency"""
        if not nodes:
            return 1000.0  # High latency if no nodes
        
        # Use minimum latency among selected nodes
        min_latency = min(node.latency_ms for node in nodes)
        
        # Add data transfer latency if needed
        data_size_gb = workload.data_requirements.get('input_data_gb', 0)
        if data_size_gb > 10:  # Significant data movement
            transfer_latency = data_size_gb * 0.1  # Rough estimate
            min_latency += transfer_latency
        
        return min_latency

    def _generate_data_movement_plan(self, workload: WorkloadSpec, nodes: List[InfrastructureNode]) -> Dict[str, Any]:
        """Generate data movement plan"""
        plan = {
            'data_movement_required': False,
            'source_location': 'local',
            'target_locations': [node.location for node in nodes],
            'data_size_gb': workload.data_requirements.get('input_data_gb', 0),
            'transfer_method': 'network',
            'estimated_transfer_time_minutes': 0
        }
        
        # Check if data movement is required
        has_local_node = any(node.infrastructure_type == InfrastructureType.LOCAL for node in nodes)
        if not has_local_node and plan['data_size_gb'] > 0:
            plan['data_movement_required'] = True
            
            # Estimate transfer time (1 Gbps network)
            transfer_time = (plan['data_size_gb'] * 8) / 1  # GB to Gb, then divide by 1 Gbps
            plan['estimated_transfer_time_minutes'] = max(1, int(transfer_time))
            
            # Determine optimal transfer method
            if plan['data_size_gb'] > 100:
                plan['transfer_method'] = 'aws_snowball'
            elif plan['data_size_gb'] > 10:
                plan['transfer_method'] = 'high_speed_network'
        
        return plan

    def _generate_failover_plan(self, workload: WorkloadSpec, selected_nodes: List[InfrastructureNode],
                              suitable_nodes: List[InfrastructureNode]) -> Dict[str, Any]:
        """Generate failover plan"""
        plan = {
            'failover_enabled': len(selected_nodes) > 1,
            'primary_node': selected_nodes[0].node_id if selected_nodes else None,
            'backup_nodes': [node.node_id for node in selected_nodes[1:]] if len(selected_nodes) > 1 else [],
            'failover_trigger': 'health_check_failure',
            'failover_time_minutes': 5
        }
        
        # Add alternative nodes for emergency failover
        alternative_nodes = [node for node in suitable_nodes if node not in selected_nodes]
        if alternative_nodes:
            plan['alternative_nodes'] = [node.node_id for node in alternative_nodes[:3]]
        
        # Adjust failover time based on workload priority
        if workload.priority <= 2:  # High priority
            plan['failover_time_minutes'] = 2
        elif workload.priority >= 8:  # Low priority
            plan['failover_time_minutes'] = 10
        
        return plan

    def _generate_monitoring_plan(self, workload: WorkloadSpec, nodes: List[InfrastructureNode]) -> Dict[str, Any]:
        """Generate monitoring plan"""
        plan = {
            'monitoring_enabled': True,
            'monitoring_interval_seconds': 60,
            'metrics_to_monitor': [
                'cpu_utilization',
                'memory_utilization',
                'network_latency',
                'availability'
            ],
            'alert_thresholds': {
                'cpu_utilization': 80,
                'memory_utilization': 85,
                'network_latency': 200,
                'availability': 99
            },
            'notification_channels': ['email', 'slack']
        }
        
        # Adjust monitoring frequency based on workload priority
        if workload.priority <= 2:
            plan['monitoring_interval_seconds'] = 30
        elif workload.priority >= 8:
            plan['monitoring_interval_seconds'] = 300
        
        # Add node-specific monitoring
        for node in nodes:
            if node.infrastructure_type == InfrastructureType.LOCAL:
                plan['metrics_to_monitor'].extend(['disk_utilization', 'system_load'])
            elif node.infrastructure_type in [InfrastructureType.AWS, InfrastructureType.AZURE]:
                plan['metrics_to_monitor'].extend(['instance_health', 'service_health'])
        
        return plan

    def _calculate_confidence_score(self, workload: WorkloadSpec, nodes: List[InfrastructureNode],
                                  strategy: OrchestrationStrategy) -> float:
        """Calculate confidence score for orchestration decision"""
        if not nodes:
            return 0.0
        
        confidence = 0.8  # Base confidence
        
        # Adjust based on resource availability
        resource_confidence = []
        for node in nodes:
            for resource, required in workload.resource_requirements.items():
                if resource in node.capacity:
                    available = node.capacity[resource] - node.current_utilization[resource]
                    if available >= required * 2:  # 100% buffer
                        resource_confidence.append(1.0)
                    elif available >= required * 1.5:  # 50% buffer
                        resource_confidence.append(0.9)
                    elif available >= required:  # Minimum requirement
                        resource_confidence.append(0.7)
                    else:
                        resource_confidence.append(0.3)
        
        if resource_confidence:
            avg_resource_confidence = sum(resource_confidence) / len(resource_confidence)
            confidence *= avg_resource_confidence
        
        # Adjust based on node reliability
        avg_reliability = sum(node.reliability_score for node in nodes) / len(nodes)
        confidence *= avg_reliability
        
        # Bonus for redundancy
        if len(nodes) > 1:
            confidence = min(1.0, confidence * 1.1)
        
        return round(confidence, 3)

    def _generate_orchestration_reasoning(self, workload: WorkloadSpec, nodes: List[InfrastructureNode],
                                        strategy: OrchestrationStrategy, preferences: Dict[str, Any]) -> str:
        """Generate human-readable reasoning for orchestration decision"""
        reasons = []
        
        # Strategy reasoning
        reasons.append(f"Using {strategy.value} strategy based on workload affinity ({workload.affinity.value})")
        
        # Node selection reasoning
        if nodes:
            primary_node = nodes[0]
            reasons.append(f"Selected {primary_node.infrastructure_type.value} node ({primary_node.node_name}) for optimal {workload.affinity.value}")
            
            if primary_node.cost_per_hour == 0:
                reasons.append("Prioritized local infrastructure for cost savings")
            elif primary_node.latency_ms < 20:
                reasons.append("Prioritized low-latency infrastructure")
        
        # Redundancy reasoning
        if len(nodes) > 1:
            reasons.append(f"Added backup node for high-priority workload (priority {workload.priority})")
        
        # Compliance reasoning
        if workload.compliance_requirements:
            reasons.append(f"Selected compliant infrastructure for {', '.join(workload.compliance_requirements)} requirements")
        
        # Resource reasoning
        total_cpu = sum(workload.resource_requirements.get(r, 0) for r in ['cpu_cores'])
        if total_cpu > 16:
            reasons.append("Selected high-capacity nodes for compute-intensive workload")
        
        if workload.resource_requirements.get('gpu_count', 0) > 0:
            reasons.append("Selected GPU-enabled infrastructure for ML/AI workload")
        
        return "; ".join(reasons)

    def _node_to_dict(self, node: InfrastructureNode) -> Dict[str, Any]:
        """Convert node to dictionary"""
        return {
            'node_id': node.node_id,
            'node_name': node.node_name,
            'infrastructure_type': node.infrastructure_type.value,
            'location': node.location,
            'capacity': node.capacity,
            'current_utilization': node.current_utilization,
            'cost_per_hour': node.cost_per_hour,
            'latency_ms': node.latency_ms,
            'reliability_score': node.reliability_score,
            'compliance_level': node.compliance_level,
            'available': node.available
        }

    def _create_error_decision(self, workload_id: str, error_message: str) -> OrchestrationDecision:
        """Create error orchestration decision"""
        return OrchestrationDecision(
            workload_id=workload_id,
            selected_nodes=[],
            node_details=[],
            orchestration_strategy=OrchestrationStrategy.BALANCED,
            estimated_cost=0.0,
            estimated_latency_ms=1000.0,
            data_movement_plan={'error': error_message},
            failover_plan={'error': error_message},
            monitoring_plan={'error': error_message},
            reasoning=f"Error: {error_message}",
            confidence_score=0.0
        )

    def get_infrastructure_status(self) -> Dict[str, Any]:
        """Get current infrastructure status"""
        try:
            status = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_nodes': len(self.infrastructure_nodes),
                'nodes_by_type': {},
                'total_capacity': {'cpu_cores': 0, 'memory_gb': 0, 'storage_gb': 0, 'gpu_count': 0},
                'total_utilization': {'cpu_cores': 0, 'memory_gb': 0, 'storage_gb': 0, 'gpu_count': 0},
                'active_workloads': len(self.active_workloads),
                'nodes': {}
            }
            
            # Aggregate by infrastructure type
            for node in self.infrastructure_nodes.values():
                node_type = node.infrastructure_type.value
                status['nodes_by_type'][node_type] = status['nodes_by_type'].get(node_type, 0) + 1
                
                # Aggregate capacity and utilization
                for resource in ['cpu_cores', 'memory_gb', 'storage_gb', 'gpu_count']:
                    status['total_capacity'][resource] += node.capacity.get(resource, 0)
                    status['total_utilization'][resource] += node.current_utilization.get(resource, 0)
                
                # Node details
                status['nodes'][node.node_id] = self._node_to_dict(node)
            
            # Calculate utilization percentages
            status['utilization_percentages'] = {}
            for resource in status['total_capacity']:
                if status['total_capacity'][resource] > 0:
                    utilization_pct = (status['total_utilization'][resource] / status['total_capacity'][resource]) * 100
                    status['utilization_percentages'][resource] = round(utilization_pct, 1)
                else:
                    status['utilization_percentages'][resource] = 0.0
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get infrastructure status: {e}")
            return {'error': str(e)}

    def get_workload_status(self, workload_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of active workloads"""
        try:
            if workload_id:
                if workload_id in self.active_workloads:
                    workload_info = self.active_workloads[workload_id]
                    runtime = datetime.utcnow() - workload_info['start_time']
                    
                    return {
                        'workload_id': workload_id,
                        'status': 'running',
                        'runtime_minutes': runtime.total_seconds() / 60,
                        'selected_nodes': workload_info['selected_nodes'],
                        'strategy': workload_info['strategy'].value,
                        'estimated_cost': workload_info['estimated_cost']
                    }
                else:
                    return {'error': f'Workload {workload_id} not found'}
            
            # Return all active workloads
            workloads_status = []
            for wid, workload_info in self.active_workloads.items():
                runtime = datetime.utcnow() - workload_info['start_time']
                workloads_status.append({
                    'workload_id': wid,
                    'workload_name': workload_info['workload'].workload_name,
                    'status': 'running',
                    'runtime_minutes': runtime.total_seconds() / 60,
                    'selected_nodes': workload_info['selected_nodes'],
                    'strategy': workload_info['strategy'].value,
                    'estimated_cost': workload_info['estimated_cost']
                })
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'active_workloads_count': len(workloads_status),
                'workloads': workloads_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get workload status: {e}")
            return {'error': str(e)}

    async def monitor_infrastructure(self):
        """Continuously monitor infrastructure health"""
        try:
            # Update local node status
            local_nodes = [node for node in self.infrastructure_nodes.values() 
                          if node.infrastructure_type == InfrastructureType.LOCAL]
            
            for local_node in local_nodes:
                updated_node = self._discover_local_infrastructure()
                local_node.current_utilization = updated_node.current_utilization
                local_node.last_heartbeat = datetime.utcnow()
            
            # Simulate cloud node updates (in production, this would query actual cloud APIs)
            for node in self.infrastructure_nodes.values():
                if node.infrastructure_type != InfrastructureType.LOCAL:
                    # Simulate some utilization changes
                    for resource in node.current_utilization:
                        # Random walk utilization
                        current = node.current_utilization[resource]
                        capacity = node.capacity[resource]
                        change = (hash(node.node_id + str(datetime.utcnow().minute)) % 10 - 5) / 100
                        new_utilization = max(0, min(capacity * 0.95, current + change * capacity))
                        node.current_utilization[resource] = new_utilization
                    
                    node.last_heartbeat = datetime.utcnow()
            
            logger.debug("Infrastructure monitoring cycle completed")
            
        except Exception as e:
            logger.error(f"Error in infrastructure monitoring: {e}")

    def update_workload_status(self, workload_id: str, status: str):
        """Update workload status"""
        if workload_id in self.active_workloads:
            if status == 'completed' or status == 'failed':
                # Move to performance history
                workload_info = self.active_workloads[workload_id]
                runtime = datetime.utcnow() - workload_info['start_time']
                
                self.performance_history.append({
                    'workload_id': workload_id,
                    'completion_time': datetime.utcnow().isoformat(),
                    'runtime_minutes': runtime.total_seconds() / 60,
                    'strategy': workload_info['strategy'].value,
                    'nodes_used': workload_info['selected_nodes'],
                    'status': status
                })
                
                # Remove from active workloads
                del self.active_workloads[workload_id]
                
                logger.info(f"Workload {workload_id} {status} after {runtime.total_seconds()/60:.1f} minutes")