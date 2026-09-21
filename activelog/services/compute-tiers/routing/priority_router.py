#!/usr/bin/env python3
"""
Priority Router for ActiveLog Compute Tiers
Intelligent workload routing based on priority, SLA, and resource optimization
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math

logger = logging.getLogger(__name__)

class WorkloadPriority(Enum):
    """Workload priority levels"""
    CRITICAL = "critical"
    HIGH = "high" 
    NORMAL = "normal"
    LOW = "low"
    BATCH = "batch"

class ServiceTier(Enum):
    """Service tiers for routing"""
    PREMIUM = "premium"
    STANDARD = "standard"
    ECONOMY = "economy"
    SPOT = "spot"

class ResourceProfile(Enum):
    """Resource usage profiles"""
    CPU_INTENSIVE = "cpu_intensive"
    MEMORY_INTENSIVE = "memory_intensive"
    IO_INTENSIVE = "io_intensive"
    NETWORK_INTENSIVE = "network_intensive"
    GPU_COMPUTE = "gpu_compute"
    BALANCED = "balanced"

@dataclass
class WorkloadSpec:
    """Workload specification for routing"""
    workload_id: str
    workload_name: str
    priority: WorkloadPriority
    resource_profile: ResourceProfile
    cpu_cores: int
    memory_gb: float
    gpu_count: int
    storage_gb: float
    network_bandwidth_mbps: Optional[float]
    estimated_duration_minutes: int
    deadline: Optional[datetime]
    cost_budget_usd: Optional[float]
    fault_tolerance: str  # high, medium, low
    data_locality_requirements: List[str]
    compliance_requirements: List[str]

@dataclass
class ComputeTier:
    """Compute tier definition"""
    tier_name: str
    service_level: ServiceTier
    instance_types: List[str]
    availability_zones: List[str]
    cost_per_hour: float
    performance_multiplier: float
    reliability_score: float
    sla_uptime_percent: float
    max_concurrent_workloads: int
    suitable_profiles: List[ResourceProfile]

@dataclass
class RoutingDecision:
    """Routing decision result"""
    workload_id: str
    selected_tier: str
    instance_type: str
    availability_zone: str
    estimated_cost: float
    estimated_completion_time: datetime
    confidence_score: float
    reasoning: str
    alternatives: List[Dict[str, Any]]
    routing_metadata: Dict[str, Any]

class PriorityRouter:
    """Routes workloads to optimal compute tiers based on priority and requirements"""
    
    def __init__(self, config):
        self.config = config
        
        # Define available compute tiers
        self.compute_tiers = {
            'premium_gpu': ComputeTier(
                tier_name='premium_gpu',
                service_level=ServiceTier.PREMIUM,
                instance_types=['p4d.24xlarge', 'p3.16xlarge', 'p3.8xlarge'],
                availability_zones=['us-east-1a', 'us-west-2a'],
                cost_per_hour=32.0,
                performance_multiplier=10.0,
                reliability_score=0.99,
                sla_uptime_percent=99.9,
                max_concurrent_workloads=10,
                suitable_profiles=[ResourceProfile.GPU_COMPUTE]
            ),
            'premium_cpu': ComputeTier(
                tier_name='premium_cpu',
                service_level=ServiceTier.PREMIUM,
                instance_types=['c5.18xlarge', 'c5.12xlarge', 'c5n.18xlarge'],
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b'],
                cost_per_hour=3.0,
                performance_multiplier=5.0,
                reliability_score=0.995,
                sla_uptime_percent=99.9,
                max_concurrent_workloads=50,
                suitable_profiles=[ResourceProfile.CPU_INTENSIVE, ResourceProfile.NETWORK_INTENSIVE]
            ),
            'premium_memory': ComputeTier(
                tier_name='premium_memory',
                service_level=ServiceTier.PREMIUM,
                instance_types=['r5.24xlarge', 'r5.16xlarge', 'x1e.16xlarge'],
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b'],
                cost_per_hour=5.0,
                performance_multiplier=4.0,
                reliability_score=0.995,
                sla_uptime_percent=99.9,
                max_concurrent_workloads=30,
                suitable_profiles=[ResourceProfile.MEMORY_INTENSIVE]
            ),
            'standard_balanced': ComputeTier(
                tier_name='standard_balanced',
                service_level=ServiceTier.STANDARD,
                instance_types=['m5.8xlarge', 'm5.4xlarge', 'm5.2xlarge'],
                availability_zones=['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-west-2a', 'us-west-2b', 'us-west-2c'],
                cost_per_hour=1.5,
                performance_multiplier=2.0,
                reliability_score=0.99,
                sla_uptime_percent=99.5,
                max_concurrent_workloads=100,
                suitable_profiles=[ResourceProfile.BALANCED, ResourceProfile.CPU_INTENSIVE, ResourceProfile.MEMORY_INTENSIVE]
            ),
            'standard_gpu': ComputeTier(
                tier_name='standard_gpu',
                service_level=ServiceTier.STANDARD,
                instance_types=['g4dn.8xlarge', 'g4dn.4xlarge', 'g4dn.2xlarge'],
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b'],
                cost_per_hour=2.2,
                performance_multiplier=3.0,
                reliability_score=0.99,
                sla_uptime_percent=99.5,
                max_concurrent_workloads=40,
                suitable_profiles=[ResourceProfile.GPU_COMPUTE]
            ),
            'economy_cpu': ComputeTier(
                tier_name='economy_cpu',
                service_level=ServiceTier.ECONOMY,
                instance_types=['c5.large', 'c5.xlarge', 'c5.2xlarge'],
                availability_zones=['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-west-2a', 'us-west-2b', 'us-west-2c'],
                cost_per_hour=0.3,
                performance_multiplier=1.0,
                reliability_score=0.98,
                sla_uptime_percent=99.0,
                max_concurrent_workloads=200,
                suitable_profiles=[ResourceProfile.CPU_INTENSIVE, ResourceProfile.BALANCED]
            ),
            'economy_memory': ComputeTier(
                tier_name='economy_memory',
                service_level=ServiceTier.ECONOMY,
                instance_types=['r5.large', 'r5.xlarge', 'r5.2xlarge'],
                availability_zones=['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-west-2a', 'us-west-2b', 'us-west-2c'],
                cost_per_hour=0.4,
                performance_multiplier=1.0,
                reliability_score=0.98,
                sla_uptime_percent=99.0,
                max_concurrent_workloads=150,
                suitable_profiles=[ResourceProfile.MEMORY_INTENSIVE, ResourceProfile.BALANCED]
            ),
            'spot_batch': ComputeTier(
                tier_name='spot_batch',
                service_level=ServiceTier.SPOT,
                instance_types=['c5.large', 'm5.large', 'r5.large', 'g4dn.xlarge'],
                availability_zones=['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-west-2a', 'us-west-2b', 'us-west-2c'],
                cost_per_hour=0.15,
                performance_multiplier=0.8,
                reliability_score=0.85,
                sla_uptime_percent=95.0,
                max_concurrent_workloads=500,
                suitable_profiles=[ResourceProfile.CPU_INTENSIVE, ResourceProfile.MEMORY_INTENSIVE, ResourceProfile.BALANCED, ResourceProfile.GPU_COMPUTE]
            )
        }
        
        # Tier utilization tracking
        self.tier_utilization: Dict[str, int] = {tier: 0 for tier in self.compute_tiers.keys()}
        
        # Routing policies based on priority
        self.priority_policies = {
            WorkloadPriority.CRITICAL: {
                'preferred_service_levels': [ServiceTier.PREMIUM],
                'cost_weight': 0.1,
                'performance_weight': 0.6,
                'reliability_weight': 0.3,
                'max_queue_time_minutes': 5
            },
            WorkloadPriority.HIGH: {
                'preferred_service_levels': [ServiceTier.PREMIUM, ServiceTier.STANDARD],
                'cost_weight': 0.2,
                'performance_weight': 0.5,
                'reliability_weight': 0.3,
                'max_queue_time_minutes': 15
            },
            WorkloadPriority.NORMAL: {
                'preferred_service_levels': [ServiceTier.STANDARD, ServiceTier.ECONOMY],
                'cost_weight': 0.4,
                'performance_weight': 0.4,
                'reliability_weight': 0.2,
                'max_queue_time_minutes': 60
            },
            WorkloadPriority.LOW: {
                'preferred_service_levels': [ServiceTier.ECONOMY, ServiceTier.SPOT],
                'cost_weight': 0.6,
                'performance_weight': 0.2,
                'reliability_weight': 0.2,
                'max_queue_time_minutes': 240
            },
            WorkloadPriority.BATCH: {
                'preferred_service_levels': [ServiceTier.SPOT, ServiceTier.ECONOMY],
                'cost_weight': 0.8,
                'performance_weight': 0.1,
                'reliability_weight': 0.1,
                'max_queue_time_minutes': 1440  # 24 hours
            }
        }

    def route_workload(self, workload_spec: Dict[str, Any], routing_preferences: Dict[str, Any] = None) -> RoutingDecision:
        """Route workload to optimal compute tier"""
        try:
            # Parse workload specification
            workload = self._parse_workload_spec(workload_spec)
            preferences = routing_preferences or {}
            
            # Get routing policy for priority level
            policy = self.priority_policies[workload.priority]
            
            # Find suitable tiers
            suitable_tiers = self._find_suitable_tiers(workload, policy)
            
            if not suitable_tiers:
                return self._create_error_decision(
                    workload.workload_id,
                    "No suitable compute tiers found for workload requirements"
                )
            
            # Score and rank tiers
            scored_tiers = self._score_tiers(workload, suitable_tiers, policy, preferences)
            
            # Select best tier
            best_tier, best_score = scored_tiers[0]
            
            # Select optimal instance and AZ
            instance_type = self._select_instance_type(workload, best_tier)
            availability_zone = self._select_availability_zone(workload, best_tier, preferences)
            
            # Calculate estimates
            estimated_cost = self._calculate_cost(workload, best_tier, instance_type)
            estimated_completion = self._estimate_completion_time(workload, best_tier)
            
            # Generate alternatives
            alternatives = self._generate_alternatives(workload, scored_tiers[1:5], policy)
            
            # Update tier utilization
            self.tier_utilization[best_tier.tier_name] += 1
            
            return RoutingDecision(
                workload_id=workload.workload_id,
                selected_tier=best_tier.tier_name,
                instance_type=instance_type,
                availability_zone=availability_zone,
                estimated_cost=estimated_cost,
                estimated_completion_time=estimated_completion,
                confidence_score=best_score,
                reasoning=self._generate_reasoning(workload, best_tier, policy),
                alternatives=alternatives,
                routing_metadata={
                    'routing_timestamp': datetime.utcnow().isoformat(),
                    'policy_applied': workload.priority.value,
                    'tier_utilization_at_routing': self.tier_utilization.copy(),
                    'preferences_applied': preferences
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to route workload: {e}")
            return self._create_error_decision(
                workload_spec.get('workload_id', 'unknown'),
                f"Routing error: {str(e)}"
            )

    def _parse_workload_spec(self, spec: Dict[str, Any]) -> WorkloadSpec:
        """Parse workload specification"""
        return WorkloadSpec(
            workload_id=spec.get('workload_id', f'workload_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'),
            workload_name=spec.get('workload_name', 'Unnamed Workload'),
            priority=WorkloadPriority(spec.get('priority', 'normal')),
            resource_profile=ResourceProfile(spec.get('resource_profile', 'balanced')),
            cpu_cores=spec.get('cpu_cores', 2),
            memory_gb=spec.get('memory_gb', 4),
            gpu_count=spec.get('gpu_count', 0),
            storage_gb=spec.get('storage_gb', 20),
            network_bandwidth_mbps=spec.get('network_bandwidth_mbps'),
            estimated_duration_minutes=spec.get('estimated_duration_minutes', 60),
            deadline=datetime.fromisoformat(spec['deadline']) if spec.get('deadline') else None,
            cost_budget_usd=spec.get('cost_budget_usd'),
            fault_tolerance=spec.get('fault_tolerance', 'medium'),
            data_locality_requirements=spec.get('data_locality_requirements', []),
            compliance_requirements=spec.get('compliance_requirements', [])
        )

    def _find_suitable_tiers(self, workload: WorkloadSpec, policy: Dict[str, Any]) -> List[ComputeTier]:
        """Find tiers suitable for the workload"""
        suitable_tiers = []
        
        for tier in self.compute_tiers.values():
            # Check service level preference
            if tier.service_level not in policy['preferred_service_levels']:
                # Allow other service levels but with lower priority
                if len(policy['preferred_service_levels']) >= 2:
                    continue
            
            # Check resource profile compatibility
            if workload.resource_profile not in tier.suitable_profiles:
                continue
            
            # Check capacity availability
            if self.tier_utilization[tier.tier_name] >= tier.max_concurrent_workloads:
                continue
            
            # Check GPU requirements
            if workload.gpu_count > 0 and workload.resource_profile != ResourceProfile.GPU_COMPUTE:
                continue
            
            # Check deadline constraints
            if workload.deadline:
                estimated_completion = self._estimate_completion_time(workload, tier)
                if estimated_completion > workload.deadline:
                    continue
            
            # Check budget constraints
            if workload.cost_budget_usd:
                estimated_cost = self._calculate_cost(workload, tier, tier.instance_types[0])
                if estimated_cost > workload.cost_budget_usd:
                    continue
            
            suitable_tiers.append(tier)
        
        return suitable_tiers

    def _score_tiers(self, workload: WorkloadSpec, tiers: List[ComputeTier], 
                    policy: Dict[str, Any], preferences: Dict[str, Any]) -> List[Tuple[ComputeTier, float]]:
        """Score and rank suitable tiers"""
        scored_tiers = []
        
        for tier in tiers:
            score = 0.0
            
            # Cost score (lower cost = higher score)
            cost = self._calculate_cost(workload, tier, tier.instance_types[0])
            normalized_cost = min(1.0, cost / 100.0)  # Normalize to 0-1 scale
            cost_score = (1.0 - normalized_cost) * 100
            score += cost_score * policy['cost_weight']
            
            # Performance score
            performance_score = tier.performance_multiplier * 20  # Scale to 0-100
            score += performance_score * policy['performance_weight']
            
            # Reliability score
            reliability_score = tier.reliability_score * 100
            score += reliability_score * policy['reliability_weight']
            
            # Tier utilization penalty (prefer less utilized tiers)
            utilization_rate = self.tier_utilization[tier.tier_name] / tier.max_concurrent_workloads
            utilization_penalty = utilization_rate * 20
            score -= utilization_penalty
            
            # Priority matching bonus
            if tier.service_level in policy['preferred_service_levels']:
                priority_index = policy['preferred_service_levels'].index(tier.service_level)
                priority_bonus = (len(policy['preferred_service_levels']) - priority_index) * 10
                score += priority_bonus
            
            # Resource profile matching bonus
            if workload.resource_profile in tier.suitable_profiles:
                profile_index = tier.suitable_profiles.index(workload.resource_profile)
                profile_bonus = (len(tier.suitable_profiles) - profile_index) * 5
                score += profile_bonus
            
            # Deadline urgency bonus
            if workload.deadline:
                time_to_deadline = (workload.deadline - datetime.utcnow()).total_seconds() / 3600  # hours
                if time_to_deadline < 24:  # Less than 24 hours
                    urgency_bonus = max(0, 20 - time_to_deadline)
                    score += urgency_bonus
            
            # User preferences
            preferred_tier = preferences.get('preferred_tier')
            if preferred_tier and tier.tier_name == preferred_tier:
                score += 25
            
            preferred_service_level = preferences.get('preferred_service_level')
            if preferred_service_level and tier.service_level.value == preferred_service_level:
                score += 15
            
            scored_tiers.append((tier, score))
        
        # Sort by score (highest first)
        scored_tiers.sort(key=lambda x: x[1], reverse=True)
        
        return scored_tiers

    def _select_instance_type(self, workload: WorkloadSpec, tier: ComputeTier) -> str:
        """Select optimal instance type within tier"""
        # For now, select the first (typically smallest) instance that meets requirements
        # In a production system, this would be more sophisticated
        
        for instance_type in tier.instance_types:
            # Check if instance meets minimum requirements
            # This is simplified - in reality you'd check actual instance specifications
            if self._instance_meets_requirements(instance_type, workload):
                return instance_type
        
        # Fallback to largest instance in tier
        return tier.instance_types[-1]

    def _instance_meets_requirements(self, instance_type: str, workload: WorkloadSpec) -> bool:
        """Check if instance type meets workload requirements"""
        # Simplified instance specification lookup
        instance_specs = {
            # CPU optimized
            'c5.large': {'vcpus': 2, 'memory_gb': 4, 'gpu': 0},
            'c5.xlarge': {'vcpus': 4, 'memory_gb': 8, 'gpu': 0},
            'c5.2xlarge': {'vcpus': 8, 'memory_gb': 16, 'gpu': 0},
            'c5.4xlarge': {'vcpus': 16, 'memory_gb': 32, 'gpu': 0},
            'c5.12xlarge': {'vcpus': 48, 'memory_gb': 96, 'gpu': 0},
            'c5.18xlarge': {'vcpus': 72, 'memory_gb': 144, 'gpu': 0},
            
            # Memory optimized  
            'r5.large': {'vcpus': 2, 'memory_gb': 16, 'gpu': 0},
            'r5.xlarge': {'vcpus': 4, 'memory_gb': 32, 'gpu': 0},
            'r5.2xlarge': {'vcpus': 8, 'memory_gb': 64, 'gpu': 0},
            'r5.16xlarge': {'vcpus': 64, 'memory_gb': 512, 'gpu': 0},
            'r5.24xlarge': {'vcpus': 96, 'memory_gb': 768, 'gpu': 0},
            
            # General purpose
            'm5.large': {'vcpus': 2, 'memory_gb': 8, 'gpu': 0},
            'm5.2xlarge': {'vcpus': 8, 'memory_gb': 32, 'gpu': 0},
            'm5.4xlarge': {'vcpus': 16, 'memory_gb': 64, 'gpu': 0},
            'm5.8xlarge': {'vcpus': 32, 'memory_gb': 128, 'gpu': 0},
            
            # GPU instances
            'g4dn.xlarge': {'vcpus': 4, 'memory_gb': 16, 'gpu': 1},
            'g4dn.2xlarge': {'vcpus': 8, 'memory_gb': 32, 'gpu': 1},
            'g4dn.4xlarge': {'vcpus': 16, 'memory_gb': 64, 'gpu': 1},
            'g4dn.8xlarge': {'vcpus': 32, 'memory_gb': 128, 'gpu': 1},
            'p3.8xlarge': {'vcpus': 32, 'memory_gb': 244, 'gpu': 4},
            'p3.16xlarge': {'vcpus': 64, 'memory_gb': 488, 'gpu': 8},
            'p4d.24xlarge': {'vcpus': 96, 'memory_gb': 1152, 'gpu': 8},
        }
        
        specs = instance_specs.get(instance_type, {'vcpus': 2, 'memory_gb': 4, 'gpu': 0})
        
        return (
            specs['vcpus'] >= workload.cpu_cores and
            specs['memory_gb'] >= workload.memory_gb and
            specs['gpu'] >= workload.gpu_count
        )

    def _select_availability_zone(self, workload: WorkloadSpec, tier: ComputeTier, 
                                preferences: Dict[str, Any]) -> str:
        """Select optimal availability zone"""
        available_azs = tier.availability_zones
        
        # Check user preferences
        preferred_az = preferences.get('preferred_availability_zone')
        if preferred_az and preferred_az in available_azs:
            return preferred_az
        
        # Check data locality requirements
        if workload.data_locality_requirements:
            for requirement in workload.data_locality_requirements:
                if requirement in available_azs:
                    return requirement
        
        # Select based on current utilization (prefer less utilized AZs)
        # For now, return first available AZ
        return available_azs[0]

    def _calculate_cost(self, workload: WorkloadSpec, tier: ComputeTier, instance_type: str) -> float:
        """Calculate estimated cost for workload"""
        duration_hours = workload.estimated_duration_minutes / 60.0
        base_cost = tier.cost_per_hour * duration_hours
        
        # Add storage costs
        storage_cost = (workload.storage_gb / 1000) * 0.10 * duration_hours  # $0.10/GB/hour
        
        # Add network costs if significant bandwidth required
        network_cost = 0.0
        if workload.network_bandwidth_mbps and workload.network_bandwidth_mbps > 1000:
            network_cost = (workload.network_bandwidth_mbps / 1000) * 0.05 * duration_hours
        
        total_cost = base_cost + storage_cost + network_cost
        
        # Apply discounts for longer running workloads
        if duration_hours > 24:
            total_cost *= 0.9  # 10% discount for long-running jobs
        
        return round(total_cost, 2)

    def _estimate_completion_time(self, workload: WorkloadSpec, tier: ComputeTier) -> datetime:
        """Estimate workload completion time"""
        # Base duration adjusted by tier performance
        adjusted_duration = workload.estimated_duration_minutes / tier.performance_multiplier
        
        # Add queue wait time
        current_utilization = self.tier_utilization[tier.tier_name] / tier.max_concurrent_workloads
        queue_wait_minutes = current_utilization * 30  # Max 30 minutes wait for full utilization
        
        total_minutes = adjusted_duration + queue_wait_minutes + 5  # 5 min startup overhead
        
        return datetime.utcnow() + timedelta(minutes=total_minutes)

    def _generate_alternatives(self, workload: WorkloadSpec, scored_tiers: List[Tuple[ComputeTier, float]], 
                             policy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alternative routing options"""
        alternatives = []
        
        for tier, score in scored_tiers:
            instance_type = self._select_instance_type(workload, tier)
            cost = self._calculate_cost(workload, tier, instance_type)
            completion_time = self._estimate_completion_time(workload, tier)
            
            alternatives.append({
                'tier_name': tier.tier_name,
                'service_level': tier.service_level.value,
                'instance_type': instance_type,
                'estimated_cost': cost,
                'estimated_completion_time': completion_time.isoformat(),
                'score': round(score, 2),
                'reliability_score': tier.reliability_score,
                'performance_multiplier': tier.performance_multiplier,
                'sla_uptime_percent': tier.sla_uptime_percent
            })
        
        return alternatives

    def _generate_reasoning(self, workload: WorkloadSpec, tier: ComputeTier, policy: Dict[str, Any]) -> str:
        """Generate human-readable reasoning for routing decision"""
        reasons = []
        
        # Priority-based reasoning
        reasons.append(f"Selected {tier.service_level.value} tier based on {workload.priority.value} priority")
        
        # Resource matching
        if workload.resource_profile in tier.suitable_profiles:
            reasons.append(f"Tier optimized for {workload.resource_profile.value} workloads")
        
        # Performance considerations
        if tier.performance_multiplier > 2.0:
            reasons.append(f"High-performance tier provides {tier.performance_multiplier}x performance boost")
        
        # Cost considerations
        if policy['cost_weight'] > 0.5:
            reasons.append("Cost optimization prioritized based on workload priority")
        
        # Deadline considerations
        if workload.deadline:
            time_to_deadline = (workload.deadline - datetime.utcnow()).total_seconds() / 3600
            if time_to_deadline < 24:
                reasons.append("Urgent deadline requires high-priority tier")
        
        # Capacity considerations
        utilization_rate = self.tier_utilization[tier.tier_name] / tier.max_concurrent_workloads
        if utilization_rate < 0.5:
            reasons.append("Selected tier has good availability")
        
        return "; ".join(reasons)

    def _create_error_decision(self, workload_id: str, error_message: str) -> RoutingDecision:
        """Create error routing decision"""
        return RoutingDecision(
            workload_id=workload_id,
            selected_tier="error",
            instance_type="unknown",
            availability_zone="unknown",
            estimated_cost=0.0,
            estimated_completion_time=datetime.utcnow(),
            confidence_score=0.0,
            reasoning=error_message,
            alternatives=[],
            routing_metadata={'error': True, 'timestamp': datetime.utcnow().isoformat()}
        )

    def get_routing_status(self) -> Dict[str, Any]:
        """Get current routing system status"""
        try:
            status = {
                'timestamp': datetime.utcnow().isoformat(),
                'compute_tiers': {},
                'utilization_summary': {},
                'routing_policies': {priority.value: policy for priority, policy in self.priority_policies.items()}
            }
            
            # Tier information
            for tier_name, tier in self.compute_tiers.items():
                current_utilization = self.tier_utilization[tier_name]
                utilization_percent = (current_utilization / tier.max_concurrent_workloads) * 100
                
                status['compute_tiers'][tier_name] = {
                    'service_level': tier.service_level.value,
                    'instance_types': tier.instance_types,
                    'availability_zones': tier.availability_zones,
                    'cost_per_hour': tier.cost_per_hour,
                    'performance_multiplier': tier.performance_multiplier,
                    'reliability_score': tier.reliability_score,
                    'sla_uptime_percent': tier.sla_uptime_percent,
                    'current_utilization': current_utilization,
                    'max_concurrent_workloads': tier.max_concurrent_workloads,
                    'utilization_percent': round(utilization_percent, 1),
                    'suitable_profiles': [profile.value for profile in tier.suitable_profiles]
                }
            
            # Utilization summary
            total_capacity = sum(tier.max_concurrent_workloads for tier in self.compute_tiers.values())
            total_utilized = sum(self.tier_utilization.values())
            
            status['utilization_summary'] = {
                'total_capacity': total_capacity,
                'total_utilized': total_utilized,
                'overall_utilization_percent': round((total_utilized / total_capacity) * 100, 1) if total_capacity > 0 else 0,
                'available_capacity': total_capacity - total_utilized
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get routing status: {e}")
            return {'error': str(e)}

    def update_tier_utilization(self, tier_name: str, change: int):
        """Update tier utilization count"""
        if tier_name in self.tier_utilization:
            self.tier_utilization[tier_name] = max(0, self.tier_utilization[tier_name] + change)

    def get_tier_recommendations(self, workload_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get tier recommendations for a workload profile"""
        try:
            # Parse workload profile
            workload = self._parse_workload_spec(workload_profile)
            policy = self.priority_policies[workload.priority]
            
            # Find and score all suitable tiers
            suitable_tiers = self._find_suitable_tiers(workload, policy)
            scored_tiers = self._score_tiers(workload, suitable_tiers, policy, {})
            
            recommendations = {
                'workload_id': workload.workload_id,
                'timestamp': datetime.utcnow().isoformat(),
                'tier_recommendations': []
            }
            
            for tier, score in scored_tiers:
                instance_type = self._select_instance_type(workload, tier)
                cost = self._calculate_cost(workload, tier, instance_type)
                completion_time = self._estimate_completion_time(workload, tier)
                
                recommendations['tier_recommendations'].append({
                    'rank': len(recommendations['tier_recommendations']) + 1,
                    'tier_name': tier.tier_name,
                    'service_level': tier.service_level.value,
                    'recommended_instance': instance_type,
                    'estimated_cost': cost,
                    'estimated_completion_time': completion_time.isoformat(),
                    'score': round(score, 2),
                    'performance_multiplier': tier.performance_multiplier,
                    'reliability_score': tier.reliability_score,
                    'current_utilization_percent': round((self.tier_utilization[tier.tier_name] / tier.max_concurrent_workloads) * 100, 1),
                    'reasoning': self._generate_reasoning(workload, tier, policy)
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate tier recommendations: {e}")
            return {'error': str(e)}