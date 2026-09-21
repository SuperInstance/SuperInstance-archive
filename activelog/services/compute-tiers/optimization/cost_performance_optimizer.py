#!/usr/bin/env python3
"""
Cost vs Performance Optimizer for ActiveLog Compute Tiers
Advanced optimization engine balancing cost efficiency with performance requirements
"""

import boto3
import json
import logging
import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OptimizationTarget(Enum):
    """Optimization target strategies"""
    COST = "cost"
    PERFORMANCE = "performance" 
    BALANCED = "balanced"
    EFFICIENCY = "efficiency"
    THROUGHPUT = "throughput"

class PerformanceMetric(Enum):
    """Performance measurement types"""
    COMPUTE_THROUGHPUT = "compute_throughput"
    MEMORY_BANDWIDTH = "memory_bandwidth"
    NETWORK_THROUGHPUT = "network_throughput"
    STORAGE_IOPS = "storage_iops"
    GPU_PERFORMANCE = "gpu_performance"

@dataclass
class WorkloadProfile:
    """Workload performance and cost profile"""
    workload_id: str
    workload_name: str
    cpu_utilization_avg: float
    cpu_utilization_p95: float
    memory_utilization_avg: float
    memory_utilization_p95: float
    network_throughput_mbps: float
    storage_iops: float
    gpu_utilization_avg: float
    runtime_minutes: int
    cost_sensitivity: float  # 0-1 (0=cost insensitive, 1=very cost sensitive)
    performance_requirements: Dict[str, float]
    sla_requirements: Dict[str, Any]

@dataclass
class InstanceSpec:
    """Instance type specifications"""
    instance_type: str
    instance_family: str
    vcpus: int
    memory_gb: float
    network_performance: str
    storage_type: str
    gpu_count: int
    gpu_type: Optional[str]
    cost_per_hour: float
    spot_price: Optional[float]
    performance_scores: Dict[PerformanceMetric, float]
    availability_zones: List[str]

@dataclass
class OptimizationRecommendation:
    """Cost-performance optimization recommendation"""
    workload_id: str
    current_instance_type: str
    recommended_instance_type: str
    optimization_type: str
    cost_impact_percent: float
    performance_impact_percent: float
    efficiency_score: float
    estimated_savings_monthly: float
    confidence_score: float
    implementation_complexity: str
    risk_assessment: str
    reasoning: str

class CostPerformanceOptimizer:
    """Optimizes cost vs performance trade-offs for compute workloads"""
    
    def __init__(self, ec2_client, cloudwatch_client):
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client
        
        # Instance performance database
        self.instance_catalog = self._build_instance_catalog()
        
        # Performance benchmarks (normalized scores 0-100)
        self.performance_benchmarks = self._load_performance_benchmarks()
        
        # Cost optimization strategies
        self.optimization_strategies = {
            OptimizationTarget.COST: {
                'cost_weight': 0.8,
                'performance_weight': 0.2,
                'prefer_spot': True,
                'prefer_smaller_instances': True,
                'accept_performance_degradation': 0.3  # Up to 30% performance loss acceptable
            },
            OptimizationTarget.PERFORMANCE: {
                'cost_weight': 0.2,
                'performance_weight': 0.8,
                'prefer_spot': False,
                'prefer_smaller_instances': False,
                'accept_performance_degradation': 0.05  # Max 5% performance loss
            },
            OptimizationTarget.BALANCED: {
                'cost_weight': 0.5,
                'performance_weight': 0.5,
                'prefer_spot': True,
                'prefer_smaller_instances': False,
                'accept_performance_degradation': 0.15  # Up to 15% performance loss
            },
            OptimizationTarget.EFFICIENCY: {
                'cost_weight': 0.4,
                'performance_weight': 0.6,
                'prefer_spot': True,
                'prefer_smaller_instances': False,
                'accept_performance_degradation': 0.1  # Up to 10% performance loss
            },
            OptimizationTarget.THROUGHPUT: {
                'cost_weight': 0.3,
                'performance_weight': 0.7,
                'prefer_spot': True,
                'prefer_smaller_instances': False,
                'accept_performance_degradation': 0.0  # No performance loss acceptable
            }
        }

    def _build_instance_catalog(self) -> Dict[str, InstanceSpec]:
        """Build comprehensive instance catalog with specifications"""
        catalog = {}
        
        # CPU Optimized instances
        cpu_instances = [
            ('c5.large', 'c5', 2, 4, 'Up to 10 Gigabit', 'EBS', 0, None, 0.085),
            ('c5.xlarge', 'c5', 4, 8, 'Up to 10 Gigabit', 'EBS', 0, None, 0.17),
            ('c5.2xlarge', 'c5', 8, 16, 'Up to 10 Gigabit', 'EBS', 0, None, 0.34),
            ('c5.4xlarge', 'c5', 16, 32, 'Up to 10 Gigabit', 'EBS', 0, None, 0.68),
            ('c5.9xlarge', 'c5', 36, 72, '10 Gigabit', 'EBS', 0, None, 1.53),
            ('c5.18xlarge', 'c5', 72, 144, '25 Gigabit', 'EBS', 0, None, 3.06),
            ('c5n.large', 'c5n', 2, 5.25, 'Up to 25 Gigabit', 'EBS', 0, None, 0.108),
            ('c5n.xlarge', 'c5n', 4, 10.5, 'Up to 25 Gigabit', 'EBS', 0, None, 0.216),
            ('c5n.2xlarge', 'c5n', 8, 21, 'Up to 25 Gigabit', 'EBS', 0, None, 0.432),
            ('c5n.4xlarge', 'c5n', 16, 42, '25 Gigabit', 'EBS', 0, None, 0.864),
            ('c5n.9xlarge', 'c5n', 36, 96, '50 Gigabit', 'EBS', 0, None, 1.944),
            ('c5n.18xlarge', 'c5n', 72, 192, '100 Gigabit', 'EBS', 0, None, 3.888),
        ]
        
        # Memory Optimized instances
        memory_instances = [
            ('r5.large', 'r5', 2, 16, 'Up to 10 Gigabit', 'EBS', 0, None, 0.126),
            ('r5.xlarge', 'r5', 4, 32, 'Up to 10 Gigabit', 'EBS', 0, None, 0.252),
            ('r5.2xlarge', 'r5', 8, 64, 'Up to 10 Gigabit', 'EBS', 0, None, 0.504),
            ('r5.4xlarge', 'r5', 16, 128, 'Up to 10 Gigabit', 'EBS', 0, None, 1.008),
            ('r5.8xlarge', 'r5', 32, 256, '10 Gigabit', 'EBS', 0, None, 2.016),
            ('r5.16xlarge', 'r5', 64, 512, '20 Gigabit', 'EBS', 0, None, 4.032),
            ('r5.24xlarge', 'r5', 96, 768, '25 Gigabit', 'EBS', 0, None, 6.048),
            ('x1e.xlarge', 'x1e', 4, 122, 'Up to 10 Gigabit', 'SSD', 0, None, 0.834),
            ('x1e.2xlarge', 'x1e', 8, 244, 'Up to 10 Gigabit', 'SSD', 0, None, 1.668),
            ('x1e.4xlarge', 'x1e', 16, 488, 'Up to 10 Gigabit', 'SSD', 0, None, 3.336),
        ]
        
        # General Purpose instances
        general_instances = [
            ('m5.large', 'm5', 2, 8, 'Up to 10 Gigabit', 'EBS', 0, None, 0.096),
            ('m5.xlarge', 'm5', 4, 16, 'Up to 10 Gigabit', 'EBS', 0, None, 0.192),
            ('m5.2xlarge', 'm5', 8, 32, 'Up to 10 Gigabit', 'EBS', 0, None, 0.384),
            ('m5.4xlarge', 'm5', 16, 64, 'Up to 10 Gigabit', 'EBS', 0, None, 0.768),
            ('m5.8xlarge', 'm5', 32, 128, '10 Gigabit', 'EBS', 0, None, 1.536),
            ('m5.16xlarge', 'm5', 64, 256, '20 Gigabit', 'EBS', 0, None, 3.072),
            ('m5.24xlarge', 'm5', 96, 384, '25 Gigabit', 'EBS', 0, None, 4.608),
        ]
        
        # GPU instances
        gpu_instances = [
            ('g4dn.xlarge', 'g4dn', 4, 16, 'Up to 25 Gigabit', 'NVMe SSD', 1, 'T4', 0.526),
            ('g4dn.2xlarge', 'g4dn', 8, 32, 'Up to 25 Gigabit', 'NVMe SSD', 1, 'T4', 0.752),
            ('g4dn.4xlarge', 'g4dn', 16, 64, 'Up to 25 Gigabit', 'NVMe SSD', 1, 'T4', 1.204),
            ('g4dn.8xlarge', 'g4dn', 32, 128, '50 Gigabit', 'NVMe SSD', 1, 'T4', 2.176),
            ('g4dn.12xlarge', 'g4dn', 48, 192, '50 Gigabit', 'NVMe SSD', 4, 'T4', 3.912),
            ('g4dn.16xlarge', 'g4dn', 64, 256, '50 Gigabit', 'NVMe SSD', 1, 'T4', 4.352),
            ('p3.2xlarge', 'p3', 8, 61, 'Up to 10 Gigabit', 'EBS', 1, 'V100', 3.06),
            ('p3.8xlarge', 'p3', 32, 244, '10 Gigabit', 'EBS', 4, 'V100', 12.24),
            ('p3.16xlarge', 'p3', 64, 488, '25 Gigabit', 'EBS', 8, 'V100', 24.48),
            ('p4d.24xlarge', 'p4d', 96, 1152, '400 Gigabit', 'NVMe SSD', 8, 'A100', 32.77),
        ]
        
        # Build catalog
        all_instances = cpu_instances + memory_instances + general_instances + gpu_instances
        
        for instance_data in all_instances:
            instance_type, family, vcpus, memory, network, storage, gpu_count, gpu_type, cost = instance_data
            
            # Calculate performance scores
            performance_scores = self._calculate_performance_scores(
                instance_type, family, vcpus, memory, network, storage, gpu_count, gpu_type
            )
            
            catalog[instance_type] = InstanceSpec(
                instance_type=instance_type,
                instance_family=family,
                vcpus=vcpus,
                memory_gb=memory,
                network_performance=network,
                storage_type=storage,
                gpu_count=gpu_count,
                gpu_type=gpu_type,
                cost_per_hour=cost,
                spot_price=None,  # Updated dynamically
                performance_scores=performance_scores,
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            )
        
        return catalog

    def _calculate_performance_scores(self, instance_type: str, family: str, vcpus: int, 
                                    memory: float, network: str, storage: str, 
                                    gpu_count: int, gpu_type: Optional[str]) -> Dict[PerformanceMetric, float]:
        """Calculate normalized performance scores for instance"""
        scores = {}
        
        # Compute throughput (based on vCPUs and family optimization)
        base_compute = vcpus * 10  # Base score
        if family.startswith('c'):  # CPU optimized
            base_compute *= 1.5
        elif family.startswith('m'):  # Balanced
            base_compute *= 1.0
        elif family.startswith('r'):  # Memory optimized
            base_compute *= 0.9
        
        scores[PerformanceMetric.COMPUTE_THROUGHPUT] = min(100, base_compute)
        
        # Memory bandwidth (based on memory size and family)
        memory_score = memory * 2
        if family.startswith('r') or family.startswith('x'):  # Memory optimized
            memory_score *= 1.8
        elif family.startswith('c'):  # CPU optimized
            memory_score *= 0.8
        
        scores[PerformanceMetric.MEMORY_BANDWIDTH] = min(100, memory_score)
        
        # Network throughput
        network_score = 20  # Default
        if 'Up to 10' in network:
            network_score = 30
        elif 'Up to 25' in network:
            network_score = 50
        elif '10 Gigabit' in network:
            network_score = 40
        elif '25 Gigabit' in network:
            network_score = 70
        elif '50 Gigabit' in network:
            network_score = 85
        elif '100 Gigabit' in network or '400 Gigabit' in network:
            network_score = 100
        
        scores[PerformanceMetric.NETWORK_THROUGHPUT] = network_score
        
        # Storage IOPS
        storage_score = 40  # EBS baseline
        if 'SSD' in storage:
            storage_score = 80
        elif 'NVMe' in storage:
            storage_score = 100
        
        scores[PerformanceMetric.STORAGE_IOPS] = storage_score
        
        # GPU performance
        gpu_score = 0
        if gpu_count > 0 and gpu_type:
            if gpu_type == 'T4':
                gpu_score = 40 * gpu_count
            elif gpu_type == 'V100':
                gpu_score = 80 * gpu_count
            elif gpu_type == 'A100':
                gpu_score = 100 * gpu_count
        
        scores[PerformanceMetric.GPU_PERFORMANCE] = min(100, gpu_score)
        
        return scores

    def _load_performance_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Load performance benchmarks for different workload types"""
        return {
            'web_server': {
                PerformanceMetric.COMPUTE_THROUGHPUT.value: 70,
                PerformanceMetric.MEMORY_BANDWIDTH.value: 40,
                PerformanceMetric.NETWORK_THROUGHPUT.value: 80,
                PerformanceMetric.STORAGE_IOPS.value: 50,
                PerformanceMetric.GPU_PERFORMANCE.value: 0
            },
            'database': {
                PerformanceMetric.COMPUTE_THROUGHPUT.value: 50,
                PerformanceMetric.MEMORY_BANDWIDTH.value: 90,
                PerformanceMetric.NETWORK_THROUGHPUT.value: 60,
                PerformanceMetric.STORAGE_IOPS.value: 95,
                PerformanceMetric.GPU_PERFORMANCE.value: 0
            },
            'compute_intensive': {
                PerformanceMetric.COMPUTE_THROUGHPUT.value: 95,
                PerformanceMetric.MEMORY_BANDWIDTH.value: 60,
                PerformanceMetric.NETWORK_THROUGHPUT.value: 30,
                PerformanceMetric.STORAGE_IOPS.value: 40,
                PerformanceMetric.GPU_PERFORMANCE.value: 0
            },
            'ml_training': {
                PerformanceMetric.COMPUTE_THROUGHPUT.value: 80,
                PerformanceMetric.MEMORY_BANDWIDTH.value: 85,
                PerformanceMetric.NETWORK_THROUGHPUT.value: 70,
                PerformanceMetric.STORAGE_IOPS.value: 60,
                PerformanceMetric.GPU_PERFORMANCE.value: 95
            },
            'data_analytics': {
                PerformanceMetric.COMPUTE_THROUGHPUT.value: 85,
                PerformanceMetric.MEMORY_BANDWIDTH.value: 95,
                PerformanceMetric.NETWORK_THROUGHPUT.value: 80,
                PerformanceMetric.STORAGE_IOPS.value: 85,
                PerformanceMetric.GPU_PERFORMANCE.value: 20
            }
        }

    def optimize(self, workload_profile: Dict[str, Any], optimization_target: str = 'balanced') -> Dict[str, Any]:
        """Optimize cost vs performance for workload"""
        try:
            # Parse workload profile
            profile = self._parse_workload_profile(workload_profile)
            target = OptimizationTarget(optimization_target)
            strategy = self.optimization_strategies[target]
            
            # Get current instance performance and cost baseline
            current_instance = workload_profile.get('current_instance_type', 'm5.large')
            
            # Find optimization opportunities
            optimization_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'workload_id': profile.workload_id,
                'optimization_target': target.value,
                'current_instance': current_instance,
                'recommendations': [],
                'summary': {}
            }
            
            # Analyze current performance vs requirements
            current_analysis = self._analyze_current_instance(profile, current_instance)
            
            # Generate recommendations
            recommendations = self._generate_optimization_recommendations(profile, current_instance, target, strategy)
            optimization_results['recommendations'] = recommendations
            
            # Calculate optimization summary
            summary = self._calculate_optimization_summary(current_analysis, recommendations)
            optimization_results['summary'] = summary
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Failed to optimize cost vs performance: {e}")
            raise

    def _parse_workload_profile(self, profile_data: Dict[str, Any]) -> WorkloadProfile:
        """Parse workload profile from input data"""
        return WorkloadProfile(
            workload_id=profile_data.get('workload_id', f'workload_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'),
            workload_name=profile_data.get('workload_name', 'Unnamed Workload'),
            cpu_utilization_avg=profile_data.get('cpu_utilization_avg', 50.0),
            cpu_utilization_p95=profile_data.get('cpu_utilization_p95', 80.0),
            memory_utilization_avg=profile_data.get('memory_utilization_avg', 60.0),
            memory_utilization_p95=profile_data.get('memory_utilization_p95', 85.0),
            network_throughput_mbps=profile_data.get('network_throughput_mbps', 100.0),
            storage_iops=profile_data.get('storage_iops', 1000.0),
            gpu_utilization_avg=profile_data.get('gpu_utilization_avg', 0.0),
            runtime_minutes=profile_data.get('runtime_minutes', 60),
            cost_sensitivity=profile_data.get('cost_sensitivity', 0.5),
            performance_requirements=profile_data.get('performance_requirements', {}),
            sla_requirements=profile_data.get('sla_requirements', {})
        )

    def _analyze_current_instance(self, profile: WorkloadProfile, current_instance: str) -> Dict[str, Any]:
        """Analyze current instance performance and cost"""
        if current_instance not in self.instance_catalog:
            return {'error': f'Instance type {current_instance} not found in catalog'}
        
        instance = self.instance_catalog[current_instance]
        
        # Calculate resource utilization efficiency
        cpu_efficiency = min(100, (profile.cpu_utilization_avg / 100) * 100)
        memory_efficiency = min(100, (profile.memory_utilization_avg / 100) * 100)
        
        # Calculate cost efficiency (performance per dollar)
        total_performance = sum(instance.performance_scores.values()) / len(instance.performance_scores)
        cost_efficiency = total_performance / (instance.cost_per_hour * 100)  # Performance per cent
        
        # Identify over/under provisioning
        over_provisioned = []
        under_provisioned = []
        
        if profile.cpu_utilization_p95 < 50:
            over_provisioned.append('cpu')
        elif profile.cpu_utilization_p95 > 90:
            under_provisioned.append('cpu')
        
        if profile.memory_utilization_p95 < 40:
            over_provisioned.append('memory')
        elif profile.memory_utilization_p95 > 95:
            under_provisioned.append('memory')
        
        return {
            'instance_type': current_instance,
            'instance_specs': {
                'vcpus': instance.vcpus,
                'memory_gb': instance.memory_gb,
                'cost_per_hour': instance.cost_per_hour
            },
            'utilization_efficiency': {
                'cpu_efficiency': cpu_efficiency,
                'memory_efficiency': memory_efficiency,
                'overall_efficiency': (cpu_efficiency + memory_efficiency) / 2
            },
            'cost_efficiency': cost_efficiency,
            'performance_scores': instance.performance_scores,
            'over_provisioned_resources': over_provisioned,
            'under_provisioned_resources': under_provisioned,
            'monthly_cost_estimate': instance.cost_per_hour * 24 * 30  # Rough monthly estimate
        }

    def _generate_optimization_recommendations(self, profile: WorkloadProfile, current_instance: str, 
                                             target: OptimizationTarget, strategy: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Generate cost-performance optimization recommendations"""
        recommendations = []
        current_inst = self.instance_catalog[current_instance]
        
        # Analyze all instance types for potential improvements
        for instance_type, instance_spec in self.instance_catalog.items():
            if instance_type == current_instance:
                continue
            
            # Skip if resource requirements are not met
            if not self._meets_resource_requirements(profile, instance_spec):
                continue
            
            # Calculate optimization scores
            cost_improvement = self._calculate_cost_improvement(current_inst, instance_spec)
            performance_impact = self._calculate_performance_impact(profile, current_inst, instance_spec)
            
            # Apply strategy filters
            if not self._passes_strategy_filters(cost_improvement, performance_impact, strategy):
                continue
            
            # Calculate overall optimization score
            optimization_score = self._calculate_optimization_score(cost_improvement, performance_impact, strategy)
            
            # Skip low-value optimizations
            if optimization_score < 0.1:
                continue
            
            # Determine optimization type
            opt_type = self._determine_optimization_type(cost_improvement, performance_impact)
            
            # Calculate efficiency score
            efficiency_score = self._calculate_efficiency_score(instance_spec, profile)
            
            # Assess implementation complexity and risk
            complexity = self._assess_implementation_complexity(current_instance, instance_type)
            risk = self._assess_optimization_risk(profile, current_inst, instance_spec)
            
            # Generate reasoning
            reasoning = self._generate_optimization_reasoning(
                profile, current_inst, instance_spec, cost_improvement, performance_impact, strategy
            )
            
            recommendations.append(OptimizationRecommendation(
                workload_id=profile.workload_id,
                current_instance_type=current_instance,
                recommended_instance_type=instance_type,
                optimization_type=opt_type,
                cost_impact_percent=cost_improvement,
                performance_impact_percent=performance_impact,
                efficiency_score=efficiency_score,
                estimated_savings_monthly=self._calculate_monthly_savings(current_inst, instance_spec),
                confidence_score=optimization_score,
                implementation_complexity=complexity,
                risk_assessment=risk,
                reasoning=reasoning
            ))
        
        # Sort by optimization score
        recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return recommendations[:10]  # Return top 10 recommendations

    def _meets_resource_requirements(self, profile: WorkloadProfile, instance: InstanceSpec) -> bool:
        """Check if instance meets minimum resource requirements"""
        # CPU requirements
        cpu_required = (profile.cpu_utilization_p95 / 100) * self.instance_catalog.get(
            profile.workload_id, InstanceSpec('', '', 2, 4, '', '', 0, None, 1.0, None, {}, [])
        ).vcpus
        
        if instance.vcpus < cpu_required * 0.8:  # Allow 20% margin
            return False
        
        # Memory requirements  
        memory_required = (profile.memory_utilization_p95 / 100) * 8  # Assume 8GB baseline
        if instance.memory_gb < memory_required * 0.8:
            return False
        
        # GPU requirements
        if profile.gpu_utilization_avg > 0 and instance.gpu_count == 0:
            return False
        
        return True

    def _calculate_cost_improvement(self, current: InstanceSpec, candidate: InstanceSpec) -> float:
        """Calculate cost improvement percentage"""
        cost_difference = current.cost_per_hour - candidate.cost_per_hour
        return (cost_difference / current.cost_per_hour) * 100

    def _calculate_performance_impact(self, profile: WorkloadProfile, current: InstanceSpec, 
                                    candidate: InstanceSpec) -> float:
        """Calculate performance impact percentage"""
        # Weight performance metrics based on workload profile
        weights = self._determine_performance_weights(profile)
        
        current_weighted_perf = 0
        candidate_weighted_perf = 0
        
        for metric, weight in weights.items():
            current_weighted_perf += current.performance_scores[metric] * weight
            candidate_weighted_perf += candidate.performance_scores[metric] * weight
        
        performance_difference = candidate_weighted_perf - current_weighted_perf
        return (performance_difference / current_weighted_perf) * 100 if current_weighted_perf > 0 else 0

    def _determine_performance_weights(self, profile: WorkloadProfile) -> Dict[PerformanceMetric, float]:
        """Determine performance metric weights based on workload profile"""
        weights = {
            PerformanceMetric.COMPUTE_THROUGHPUT: 0.3,
            PerformanceMetric.MEMORY_BANDWIDTH: 0.2,
            PerformanceMetric.NETWORK_THROUGHPUT: 0.2,
            PerformanceMetric.STORAGE_IOPS: 0.2,
            PerformanceMetric.GPU_PERFORMANCE: 0.1
        }
        
        # Adjust weights based on utilization patterns
        if profile.cpu_utilization_avg > 70:
            weights[PerformanceMetric.COMPUTE_THROUGHPUT] = 0.4
            weights[PerformanceMetric.MEMORY_BANDWIDTH] = 0.15
        
        if profile.memory_utilization_avg > 70:
            weights[PerformanceMetric.MEMORY_BANDWIDTH] = 0.4
            weights[PerformanceMetric.COMPUTE_THROUGHPUT] = 0.25
        
        if profile.network_throughput_mbps > 1000:
            weights[PerformanceMetric.NETWORK_THROUGHPUT] = 0.35
        
        if profile.gpu_utilization_avg > 50:
            weights[PerformanceMetric.GPU_PERFORMANCE] = 0.5
            for metric in [PerformanceMetric.COMPUTE_THROUGHPUT, PerformanceMetric.MEMORY_BANDWIDTH]:
                weights[metric] *= 0.7
        
        return weights

    def _passes_strategy_filters(self, cost_improvement: float, performance_impact: float, 
                               strategy: Dict[str, Any]) -> bool:
        """Check if recommendation passes strategy filters"""
        # Check acceptable performance degradation
        if performance_impact < 0:  # Performance degradation
            if abs(performance_impact) > strategy['accept_performance_degradation'] * 100:
                return False
        
        # For cost-focused strategies, require cost improvement
        if strategy['cost_weight'] > 0.6 and cost_improvement <= 0:
            return False
        
        # For performance-focused strategies, avoid significant performance loss
        if strategy['performance_weight'] > 0.6 and performance_impact < -5:
            return False
        
        return True

    def _calculate_optimization_score(self, cost_improvement: float, performance_impact: float, 
                                    strategy: Dict[str, Any]) -> float:
        """Calculate overall optimization score"""
        # Normalize improvements to 0-1 scale
        cost_score = max(0, min(1, cost_improvement / 50))  # 50% cost improvement = max score
        performance_score = max(0, min(1, (performance_impact + 20) / 40))  # -20% to +20% performance range
        
        # Weighted combination
        overall_score = (cost_score * strategy['cost_weight'] + 
                        performance_score * strategy['performance_weight'])
        
        return overall_score

    def _determine_optimization_type(self, cost_improvement: float, performance_impact: float) -> str:
        """Determine the type of optimization"""
        if cost_improvement > 15 and performance_impact >= -5:
            return "cost_optimization_high_value"
        elif cost_improvement > 5 and performance_impact >= 0:
            return "cost_optimization_no_performance_loss"
        elif performance_impact > 15 and cost_improvement >= -10:
            return "performance_optimization"
        elif cost_improvement > 0 and performance_impact > 0:
            return "win_win_optimization"
        elif abs(cost_improvement) < 5 and abs(performance_impact) < 5:
            return "lateral_optimization"
        else:
            return "trade_off_optimization"

    def _calculate_efficiency_score(self, instance: InstanceSpec, profile: WorkloadProfile) -> float:
        """Calculate efficiency score for instance"""
        # Performance per dollar
        avg_performance = sum(instance.performance_scores.values()) / len(instance.performance_scores)
        efficiency = avg_performance / (instance.cost_per_hour * 100)
        
        # Adjust for utilization matching
        cpu_match_score = 1.0 - abs(profile.cpu_utilization_avg - 70) / 100  # 70% target utilization
        memory_match_score = 1.0 - abs(profile.memory_utilization_avg - 70) / 100
        
        utilization_bonus = (cpu_match_score + memory_match_score) / 2
        
        return efficiency * (1 + utilization_bonus)

    def _assess_implementation_complexity(self, current: str, candidate: str) -> str:
        """Assess implementation complexity"""
        current_family = current.split('.')[0]
        candidate_family = candidate.split('.')[0]
        
        if current_family == candidate_family:
            return "Low"  # Same instance family
        elif current_family[0] == candidate_family[0]:  # Same generation
            return "Medium"
        else:
            return "High"  # Different family

    def _assess_optimization_risk(self, profile: WorkloadProfile, current: InstanceSpec, 
                                candidate: InstanceSpec) -> str:
        """Assess optimization risk"""
        risk_factors = []
        
        # Performance risk
        if current.vcpus > candidate.vcpus:
            risk_factors.append("CPU downgrade")
        
        if current.memory_gb > candidate.memory_gb:
            risk_factors.append("Memory reduction")
        
        if current.gpu_count > candidate.gpu_count:
            risk_factors.append("GPU reduction")
        
        # Workload characteristics
        if profile.cpu_utilization_p95 > 85:
            risk_factors.append("High CPU utilization")
        
        if profile.memory_utilization_p95 > 90:
            risk_factors.append("High memory utilization")
        
        if len(risk_factors) == 0:
            return "Low"
        elif len(risk_factors) <= 2:
            return "Medium"
        else:
            return "High"

    def _generate_optimization_reasoning(self, profile: WorkloadProfile, current: InstanceSpec, 
                                       candidate: InstanceSpec, cost_improvement: float, 
                                       performance_impact: float, strategy: Dict[str, Any]) -> str:
        """Generate human-readable reasoning for optimization"""
        reasons = []
        
        # Cost reasoning
        if cost_improvement > 10:
            reasons.append(f"Reduces costs by {cost_improvement:.1f}% ({cost_improvement * current.cost_per_hour / 100:.3f}$/hour)")
        elif cost_improvement < -10:
            reasons.append(f"Higher cost by {abs(cost_improvement):.1f}% for performance gain")
        
        # Performance reasoning
        if performance_impact > 10:
            reasons.append(f"Improves performance by {performance_impact:.1f}%")
        elif performance_impact < -5:
            reasons.append(f"Minor performance impact ({performance_impact:.1f}%)")
        
        # Resource matching
        if current.vcpus > candidate.vcpus and profile.cpu_utilization_avg < 50:
            reasons.append("Right-sizes CPU resources based on low utilization")
        
        if current.memory_gb > candidate.memory_gb and profile.memory_utilization_avg < 50:
            reasons.append("Right-sizes memory based on low utilization")
        
        # Instance family benefits
        if candidate.instance_family.startswith('c') and profile.cpu_utilization_avg > 70:
            reasons.append("CPU-optimized instance matches compute-intensive workload")
        
        if candidate.instance_family.startswith('r') and profile.memory_utilization_avg > 70:
            reasons.append("Memory-optimized instance matches memory-intensive workload")
        
        if candidate.instance_family.startswith('m'):
            reasons.append("Balanced instance provides good all-around performance")
        
        return "; ".join(reasons) if reasons else "General optimization based on workload profile"

    def _calculate_monthly_savings(self, current: InstanceSpec, candidate: InstanceSpec) -> float:
        """Calculate estimated monthly savings"""
        hourly_savings = current.cost_per_hour - candidate.cost_per_hour
        return hourly_savings * 24 * 30  # 30-day month

    def _calculate_optimization_summary(self, current_analysis: Dict[str, Any], 
                                      recommendations: List[OptimizationRecommendation]) -> Dict[str, Any]:
        """Calculate optimization summary statistics"""
        if not recommendations:
            return {
                'total_recommendations': 0,
                'optimization_opportunities': 'None found'
            }
        
        # Top recommendation
        top_rec = recommendations[0]
        
        # Aggregate statistics
        total_potential_savings = sum(rec.estimated_savings_monthly for rec in recommendations)
        avg_confidence = sum(rec.confidence_score for rec in recommendations) / len(recommendations)
        
        # Categorize recommendations
        cost_optimizations = len([r for r in recommendations if r.cost_impact_percent > 5])
        performance_optimizations = len([r for r in recommendations if r.performance_impact_percent > 5])
        balanced_optimizations = len([r for r in recommendations if abs(r.cost_impact_percent) <= 5 and abs(r.performance_impact_percent) <= 5])
        
        return {
            'total_recommendations': len(recommendations),
            'top_recommendation': {
                'instance_type': top_rec.recommended_instance_type,
                'optimization_type': top_rec.optimization_type,
                'cost_impact_percent': top_rec.cost_impact_percent,
                'performance_impact_percent': top_rec.performance_impact_percent,
                'estimated_monthly_savings': top_rec.estimated_savings_monthly,
                'confidence_score': top_rec.confidence_score
            },
            'total_potential_monthly_savings': total_potential_savings,
            'average_confidence_score': avg_confidence,
            'recommendation_categories': {
                'cost_focused': cost_optimizations,
                'performance_focused': performance_optimizations,
                'balanced': balanced_optimizations
            },
            'current_instance_efficiency': current_analysis.get('utilization_efficiency', {}).get('overall_efficiency', 0)
        }

    async def continuous_optimization(self):
        """Continuously monitor and optimize cost vs performance"""
        try:
            # This would integrate with actual monitoring systems
            # For now, log the optimization cycle
            logger.info("Running continuous cost-performance optimization cycle")
            
            # In production, this would:
            # 1. Query CloudWatch for current instance utilization
            # 2. Analyze performance trends
            # 3. Identify optimization opportunities
            # 4. Generate recommendations
            # 5. Optionally auto-apply low-risk optimizations
            
        except Exception as e:
            logger.error(f"Error in continuous optimization: {e}")

    def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get cost-performance optimization metrics"""
        try:
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'instance_catalog_size': len(self.instance_catalog),
                'optimization_targets': [target.value for target in OptimizationTarget],
                'performance_metrics_tracked': [metric.value for metric in PerformanceMetric],
                'total_instance_families': len(set(inst.instance_family for inst in self.instance_catalog.values())),
                'gpu_enabled_instances': len([inst for inst in self.instance_catalog.values() if inst.gpu_count > 0]),
                'cost_range': {
                    'min_cost_per_hour': min(inst.cost_per_hour for inst in self.instance_catalog.values()),
                    'max_cost_per_hour': max(inst.cost_per_hour for inst in self.instance_catalog.values()),
                    'avg_cost_per_hour': sum(inst.cost_per_hour for inst in self.instance_catalog.values()) / len(self.instance_catalog)
                }
            }
        except Exception as e:
            logger.error(f"Failed to get optimization metrics: {e}")
            return {'error': str(e)}