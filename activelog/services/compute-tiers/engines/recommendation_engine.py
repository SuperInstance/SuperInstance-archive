"""
Instance Type Recommendation Engine
Advanced ML-based instance type recommendations based on workload characteristics
"""

import logging
import boto3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class WorkloadType(Enum):
    COMPUTE_INTENSIVE = "compute_intensive"
    MEMORY_INTENSIVE = "memory_intensive"
    IO_INTENSIVE = "io_intensive"
    NETWORK_INTENSIVE = "network_intensive"
    GPU_INTENSIVE = "gpu_intensive"
    BALANCED = "balanced"
    BURSTABLE = "burstable"
    BATCH = "batch"
    WEB_SERVER = "web_server"
    DATABASE = "database"

class PerformanceTier(Enum):
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    EXTREME = "extreme"

@dataclass
class WorkloadRequirements:
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    storage_gb: Optional[int] = None
    network_gbps: Optional[float] = None
    gpu_count: Optional[int] = None
    gpu_memory_gb: Optional[float] = None
    workload_type: Optional[WorkloadType] = None
    performance_tier: Optional[PerformanceTier] = None
    availability_requirements: Optional[float] = None  # 99.9%
    latency_requirements_ms: Optional[float] = None
    burst_requirements: Optional[bool] = None

@dataclass
class InstanceRecommendation:
    instance_type: str
    confidence_score: float
    monthly_cost_estimate: float
    performance_score: float
    suitability_reasons: List[str]
    limitations: List[str]
    configuration_recommendations: Dict[str, Any]

class RecommendationEngine:
    """Advanced instance type recommendation engine"""
    
    def __init__(self, ec2_client, cloudwatch_client):
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client
        
        # Load instance type database
        self.instance_types = self._load_instance_type_database()
        
        # Performance benchmarks (would be populated from actual benchmarks)
        self.performance_benchmarks = self._load_performance_benchmarks()
        
        # Pricing data (simplified - would use AWS Pricing API)
        self.pricing_data = self._load_pricing_data()
    
    def _load_instance_type_database(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive instance type specifications"""
        return {
            # General Purpose - T3 (Burstable)
            "t3.nano": {
                "family": "t3", "vcpus": 2, "memory_gb": 0.5, "network": "up_to_5",
                "burst_capable": True, "baseline_performance": 5, "ebs_optimized": True,
                "suitable_for": [WorkloadType.WEB_SERVER, WorkloadType.BURSTABLE]
            },
            "t3.micro": {
                "family": "t3", "vcpus": 2, "memory_gb": 1, "network": "up_to_5", 
                "burst_capable": True, "baseline_performance": 10, "ebs_optimized": True,
                "suitable_for": [WorkloadType.WEB_SERVER, WorkloadType.BURSTABLE]
            },
            "t3.small": {
                "family": "t3", "vcpus": 2, "memory_gb": 2, "network": "up_to_5",
                "burst_capable": True, "baseline_performance": 20, "ebs_optimized": True,
                "suitable_for": [WorkloadType.WEB_SERVER, WorkloadType.BURSTABLE]
            },
            "t3.medium": {
                "family": "t3", "vcpus": 2, "memory_gb": 4, "network": "up_to_5",
                "burst_capable": True, "baseline_performance": 20, "ebs_optimized": True,
                "suitable_for": [WorkloadType.WEB_SERVER, WorkloadType.BALANCED]
            },
            "t3.large": {
                "family": "t3", "vcpus": 2, "memory_gb": 8, "network": "up_to_5",
                "burst_capable": True, "baseline_performance": 30, "ebs_optimized": True,
                "suitable_for": [WorkloadType.WEB_SERVER, WorkloadType.BALANCED]
            },
            
            # General Purpose - M5 (Balanced)
            "m5.large": {
                "family": "m5", "vcpus": 2, "memory_gb": 8, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.BALANCED, WorkloadType.WEB_SERVER]
            },
            "m5.xlarge": {
                "family": "m5", "vcpus": 4, "memory_gb": 16, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.BALANCED, WorkloadType.WEB_SERVER]
            },
            "m5.2xlarge": {
                "family": "m5", "vcpus": 8, "memory_gb": 32, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.BALANCED, WorkloadType.DATABASE]
            },
            "m5.4xlarge": {
                "family": "m5", "vcpus": 16, "memory_gb": 64, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.BALANCED, WorkloadType.DATABASE]
            },
            
            # Compute Optimized - C5
            "c5.large": {
                "family": "c5", "vcpus": 2, "memory_gb": 4, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.COMPUTE_INTENSIVE, WorkloadType.BATCH]
            },
            "c5.xlarge": {
                "family": "c5", "vcpus": 4, "memory_gb": 8, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.COMPUTE_INTENSIVE, WorkloadType.BATCH]
            },
            "c5.2xlarge": {
                "family": "c5", "vcpus": 8, "memory_gb": 16, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.COMPUTE_INTENSIVE, WorkloadType.BATCH]
            },
            
            # Memory Optimized - R5
            "r5.large": {
                "family": "r5", "vcpus": 2, "memory_gb": 16, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.MEMORY_INTENSIVE, WorkloadType.DATABASE]
            },
            "r5.xlarge": {
                "family": "r5", "vcpus": 4, "memory_gb": 32, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.MEMORY_INTENSIVE, WorkloadType.DATABASE]
            },
            "r5.2xlarge": {
                "family": "r5", "vcpus": 8, "memory_gb": 64, "network": "up_to_10",
                "burst_capable": False, "baseline_performance": 100, "ebs_optimized": True,
                "suitable_for": [WorkloadType.MEMORY_INTENSIVE, WorkloadType.DATABASE]
            },
            
            # GPU Instances - P3
            "p3.2xlarge": {
                "family": "p3", "vcpus": 8, "memory_gb": 61, "network": "up_to_10",
                "gpu_count": 1, "gpu_type": "V100", "gpu_memory_gb": 16,
                "suitable_for": [WorkloadType.GPU_INTENSIVE]
            },
            "p3.8xlarge": {
                "family": "p3", "vcpus": 32, "memory_gb": 244, "network": "10",
                "gpu_count": 4, "gpu_type": "V100", "gpu_memory_gb": 64,
                "suitable_for": [WorkloadType.GPU_INTENSIVE]
            },
            
            # GPU Instances - G4
            "g4dn.xlarge": {
                "family": "g4dn", "vcpus": 4, "memory_gb": 16, "network": "up_to_25",
                "gpu_count": 1, "gpu_type": "T4", "gpu_memory_gb": 16,
                "suitable_for": [WorkloadType.GPU_INTENSIVE]
            },
            "g4dn.2xlarge": {
                "family": "g4dn", "vcpus": 8, "memory_gb": 32, "network": "up_to_25",
                "gpu_count": 1, "gpu_type": "T4", "gpu_memory_gb": 16,
                "suitable_for": [WorkloadType.GPU_INTENSIVE]
            }
        }
    
    def _load_performance_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Load performance benchmark data for instance types"""
        return {
            "compute_score": {
                "t3.nano": 100, "t3.micro": 200, "t3.small": 400, "t3.medium": 800,
                "m5.large": 1000, "m5.xlarge": 2000, "m5.2xlarge": 4000,
                "c5.large": 1200, "c5.xlarge": 2400, "c5.2xlarge": 4800,
                "r5.large": 950, "r5.xlarge": 1900, "r5.2xlarge": 3800,
                "p3.2xlarge": 15000, "g4dn.xlarge": 8000
            },
            "memory_bandwidth": {
                "t3.nano": 1.0, "t3.micro": 2.0, "t3.small": 4.0, "t3.medium": 8.0,
                "m5.large": 15.0, "m5.xlarge": 30.0, "m5.2xlarge": 60.0,
                "r5.large": 25.0, "r5.xlarge": 50.0, "r5.2xlarge": 100.0
            },
            "network_performance": {
                "t3.nano": 0.5, "t3.micro": 1.0, "t3.small": 2.5, "t3.medium": 5.0,
                "m5.large": 8.0, "m5.xlarge": 10.0, "m5.2xlarge": 10.0,
                "c5.large": 8.0, "c5.xlarge": 10.0, "c5.2xlarge": 10.0
            }
        }
    
    def _load_pricing_data(self) -> Dict[str, float]:
        """Load pricing data (simplified - would use AWS Pricing API)"""
        return {
            "t3.nano": 0.0052, "t3.micro": 0.0104, "t3.small": 0.0208, "t3.medium": 0.0416,
            "t3.large": 0.0832, "m5.large": 0.096, "m5.xlarge": 0.192, "m5.2xlarge": 0.384,
            "c5.large": 0.085, "c5.xlarge": 0.17, "c5.2xlarge": 0.34,
            "r5.large": 0.126, "r5.xlarge": 0.252, "r5.2xlarge": 0.504,
            "p3.2xlarge": 3.06, "g4dn.xlarge": 0.526
        }
    
    def recommend_instance_types(self, workload_requirements: Dict[str, Any], 
                                constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate instance type recommendations"""
        try:
            # Parse requirements
            requirements = self._parse_requirements(workload_requirements)
            constraints = constraints or {}
            
            # Get candidate instance types
            candidates = self._filter_candidates(requirements, constraints)
            
            # Score each candidate
            scored_candidates = []
            for instance_type in candidates:
                score = self._calculate_recommendation_score(instance_type, requirements)
                recommendation = self._create_recommendation(instance_type, score, requirements)
                scored_candidates.append(recommendation)
            
            # Sort by confidence score
            scored_candidates.sort(key=lambda x: x.confidence_score, reverse=True)
            
            # Generate recommendation summary
            summary = self._generate_recommendation_summary(scored_candidates, requirements)
            
            return {
                'recommendations': [self._recommendation_to_dict(rec) for rec in scored_candidates[:10]],
                'summary': summary,
                'requirements_analysis': self._analyze_requirements(requirements),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            raise
    
    def _parse_requirements(self, workload_requirements: Dict[str, Any]) -> WorkloadRequirements:
        """Parse workload requirements from input"""
        return WorkloadRequirements(
            cpu_cores=workload_requirements.get('cpu_cores'),
            memory_gb=workload_requirements.get('memory_gb'),
            storage_gb=workload_requirements.get('storage_gb'),
            network_gbps=workload_requirements.get('network_gbps'),
            gpu_count=workload_requirements.get('gpu_count'),
            gpu_memory_gb=workload_requirements.get('gpu_memory_gb'),
            workload_type=WorkloadType(workload_requirements.get('workload_type', 'balanced')),
            performance_tier=PerformanceTier(workload_requirements.get('performance_tier', 'standard')),
            availability_requirements=workload_requirements.get('availability_requirements'),
            latency_requirements_ms=workload_requirements.get('latency_requirements_ms'),
            burst_requirements=workload_requirements.get('burst_requirements')
        )
    
    def _filter_candidates(self, requirements: WorkloadRequirements, 
                          constraints: Dict[str, Any]) -> List[str]:
        """Filter instance types based on requirements and constraints"""
        candidates = []
        
        # Budget constraint
        max_monthly_cost = constraints.get('max_monthly_cost')
        
        for instance_type, specs in self.instance_types.items():
            # Check basic resource requirements
            if requirements.cpu_cores and specs['vcpus'] < requirements.cpu_cores:
                continue
            
            if requirements.memory_gb and specs['memory_gb'] < requirements.memory_gb:
                continue
            
            if requirements.gpu_count and specs.get('gpu_count', 0) < requirements.gpu_count:
                continue
            
            # Check workload type compatibility
            if (requirements.workload_type and 
                requirements.workload_type not in specs.get('suitable_for', [])):
                continue
            
            # Check budget constraints
            if max_monthly_cost:
                monthly_cost = self.pricing_data.get(instance_type, 0) * 24 * 30
                if monthly_cost > max_monthly_cost:
                    continue
            
            # Check burst requirements
            if requirements.burst_requirements and not specs.get('burst_capable', False):
                continue
            
            candidates.append(instance_type)
        
        return candidates
    
    def _calculate_recommendation_score(self, instance_type: str, 
                                      requirements: WorkloadRequirements) -> float:
        """Calculate recommendation score for an instance type"""
        specs = self.instance_types[instance_type]
        total_score = 0.0
        weight_sum = 0.0
        
        # CPU score
        if requirements.cpu_cores:
            cpu_ratio = specs['vcpus'] / requirements.cpu_cores
            cpu_score = self._calculate_fit_score(cpu_ratio, optimal_range=(1.0, 1.5))
            total_score += cpu_score * 0.25
            weight_sum += 0.25
        
        # Memory score
        if requirements.memory_gb:
            memory_ratio = specs['memory_gb'] / requirements.memory_gb
            memory_score = self._calculate_fit_score(memory_ratio, optimal_range=(1.0, 1.5))
            total_score += memory_score * 0.25
            weight_sum += 0.25
        
        # Workload type compatibility score
        if requirements.workload_type:
            workload_score = 1.0 if requirements.workload_type in specs.get('suitable_for', []) else 0.3
            total_score += workload_score * 0.20
            weight_sum += 0.20
        
        # Performance tier alignment
        performance_score = self._calculate_performance_tier_score(instance_type, requirements.performance_tier)
        total_score += performance_score * 0.15
        weight_sum += 0.15
        
        # Cost efficiency score
        cost_score = self._calculate_cost_efficiency_score(instance_type, requirements)
        total_score += cost_score * 0.15
        weight_sum += 0.15
        
        return (total_score / weight_sum) if weight_sum > 0 else 0.0
    
    def _calculate_fit_score(self, ratio: float, optimal_range: Tuple[float, float]) -> float:
        """Calculate how well a ratio fits within optimal range"""
        min_optimal, max_optimal = optimal_range
        
        if min_optimal <= ratio <= max_optimal:
            return 1.0
        elif ratio < min_optimal:
            # Under-provisioned
            return max(0.0, ratio / min_optimal)
        else:
            # Over-provisioned
            penalty = (ratio - max_optimal) / max_optimal
            return max(0.0, 1.0 - penalty * 0.5)
    
    def _calculate_performance_tier_score(self, instance_type: str, 
                                        performance_tier: PerformanceTier) -> float:
        """Calculate performance tier alignment score"""
        if not performance_tier:
            return 0.7
        
        specs = self.instance_types[instance_type]
        family = specs['family']
        
        # Define performance tiers for each family
        tier_mapping = {
            't3': PerformanceTier.BASIC,
            'm5': PerformanceTier.STANDARD,
            'c5': PerformanceTier.HIGH,
            'r5': PerformanceTier.HIGH,
            'p3': PerformanceTier.EXTREME,
            'g4dn': PerformanceTier.HIGH
        }
        
        instance_tier = tier_mapping.get(family, PerformanceTier.STANDARD)
        
        tier_scores = {
            PerformanceTier.BASIC: 1,
            PerformanceTier.STANDARD: 2,
            PerformanceTier.HIGH: 3,
            PerformanceTier.EXTREME: 4
        }
        
        required_score = tier_scores[performance_tier]
        instance_score = tier_scores[instance_tier]
        
        if instance_score >= required_score:
            return 1.0 - (instance_score - required_score) * 0.1  # Small penalty for over-provisioning
        else:
            return instance_score / required_score * 0.5  # Large penalty for under-provisioning
    
    def _calculate_cost_efficiency_score(self, instance_type: str, 
                                       requirements: WorkloadRequirements) -> float:
        """Calculate cost efficiency score"""
        hourly_cost = self.pricing_data.get(instance_type, 0)
        specs = self.instance_types[instance_type]
        
        # Calculate performance per dollar
        compute_score = self.performance_benchmarks['compute_score'].get(instance_type, 1000)
        efficiency = compute_score / (hourly_cost * 1000) if hourly_cost > 0 else 0
        
        # Normalize efficiency score (higher is better)
        # This is simplified - in practice would use more sophisticated normalization
        normalized_efficiency = min(1.0, efficiency / 10.0)
        
        return normalized_efficiency
    
    def _create_recommendation(self, instance_type: str, score: float,
                             requirements: WorkloadRequirements) -> InstanceRecommendation:
        """Create detailed recommendation object"""
        specs = self.instance_types[instance_type]
        hourly_cost = self.pricing_data.get(instance_type, 0)
        monthly_cost = hourly_cost * 24 * 30
        
        # Generate suitability reasons
        suitability_reasons = []
        if requirements.workload_type in specs.get('suitable_for', []):
            suitability_reasons.append(f"Optimized for {requirements.workload_type.value} workloads")
        
        if requirements.cpu_cores and specs['vcpus'] >= requirements.cpu_cores:
            suitability_reasons.append(f"Meets CPU requirements ({specs['vcpus']} cores)")
        
        if requirements.memory_gb and specs['memory_gb'] >= requirements.memory_gb:
            suitability_reasons.append(f"Meets memory requirements ({specs['memory_gb']}GB)")
        
        # Generate limitations
        limitations = []
        if requirements.cpu_cores and specs['vcpus'] < requirements.cpu_cores * 1.5:
            limitations.append("Limited CPU headroom for burst workloads")
        
        if specs.get('burst_capable') and not requirements.burst_requirements:
            limitations.append("Burstable instance - consistent performance may vary")
        
        # Configuration recommendations
        config_recommendations = {
            'ebs_optimized': specs.get('ebs_optimized', False),
            'enhanced_networking': specs.get('enhanced_networking', True),
            'placement_group': self._recommend_placement_group(instance_type, requirements),
            'monitoring': {
                'detailed_monitoring': True,
                'custom_metrics': self._recommend_custom_metrics(requirements)
            }
        }
        
        return InstanceRecommendation(
            instance_type=instance_type,
            confidence_score=score,
            monthly_cost_estimate=monthly_cost,
            performance_score=self._calculate_overall_performance_score(instance_type),
            suitability_reasons=suitability_reasons,
            limitations=limitations,
            configuration_recommendations=config_recommendations
        )
    
    def _recommend_placement_group(self, instance_type: str, 
                                 requirements: WorkloadRequirements) -> Optional[str]:
        """Recommend placement group strategy"""
        if requirements.workload_type == WorkloadType.COMPUTE_INTENSIVE:
            return "cluster"
        elif requirements.latency_requirements_ms and requirements.latency_requirements_ms < 10:
            return "cluster"
        elif requirements.availability_requirements and requirements.availability_requirements > 99.9:
            return "spread"
        return None
    
    def _recommend_custom_metrics(self, requirements: WorkloadRequirements) -> List[str]:
        """Recommend custom CloudWatch metrics to monitor"""
        metrics = ['MemoryUtilization', 'DiskSpaceUtilization']
        
        if requirements.workload_type == WorkloadType.DATABASE:
            metrics.extend(['DatabaseConnections', 'DatabaseLatency'])
        elif requirements.workload_type == WorkloadType.WEB_SERVER:
            metrics.extend(['HTTPRequestCount', 'ResponseTime'])
        elif requirements.workload_type == WorkloadType.BATCH:
            metrics.extend(['JobsInQueue', 'ProcessingTime'])
        
        return metrics
    
    def _calculate_overall_performance_score(self, instance_type: str) -> float:
        """Calculate overall performance score for instance type"""
        compute_score = self.performance_benchmarks['compute_score'].get(instance_type, 1000)
        # Normalize to 0-100 scale
        return min(100.0, compute_score / 100.0)
    
    def _generate_recommendation_summary(self, recommendations: List[InstanceRecommendation],
                                       requirements: WorkloadRequirements) -> Dict[str, Any]:
        """Generate summary of recommendations"""
        if not recommendations:
            return {
                'message': 'No suitable instance types found for the given requirements',
                'suggestions': ['Relax budget constraints', 'Consider different workload type']
            }
        
        top_rec = recommendations[0]
        cost_range = {
            'min': min(rec.monthly_cost_estimate for rec in recommendations[:5]),
            'max': max(rec.monthly_cost_estimate for rec in recommendations[:5])
        }
        
        return {
            'top_recommendation': top_rec.instance_type,
            'confidence': f"{top_rec.confidence_score:.1%}",
            'estimated_monthly_cost_range': cost_range,
            'total_recommendations': len(recommendations),
            'key_insights': self._generate_key_insights(recommendations, requirements)
        }
    
    def _generate_key_insights(self, recommendations: List[InstanceRecommendation],
                             requirements: WorkloadRequirements) -> List[str]:
        """Generate key insights from recommendations"""
        insights = []
        
        if recommendations:
            top_rec = recommendations[0]
            
            # Cost insights
            if top_rec.monthly_cost_estimate < 100:
                insights.append("Cost-effective options available under $100/month")
            elif top_rec.monthly_cost_estimate > 1000:
                insights.append("High-performance workload - consider Reserved Instance pricing")
            
            # Performance insights
            burstable_count = len([r for r in recommendations[:5] 
                                 if self.instance_types[r.instance_type].get('burst_capable')])
            if burstable_count > 2:
                insights.append("Consider burstable instances for variable workloads")
            
            # GPU insights
            if requirements.gpu_count:
                gpu_recs = [r for r in recommendations if 'gpu_count' in self.instance_types[r.instance_type]]
                if gpu_recs:
                    insights.append(f"GPU instances recommended - consider spot pricing for {len(gpu_recs)} options")
        
        return insights
    
    def _analyze_requirements(self, requirements: WorkloadRequirements) -> Dict[str, Any]:
        """Analyze the input requirements"""
        analysis = {
            'completeness_score': 0.0,
            'complexity_level': 'simple',
            'optimization_opportunities': []
        }
        
        # Calculate completeness
        specified_fields = sum([
            1 for field in [requirements.cpu_cores, requirements.memory_gb, 
                          requirements.workload_type, requirements.performance_tier]
            if field is not None
        ])
        analysis['completeness_score'] = specified_fields / 4.0
        
        # Determine complexity
        if requirements.gpu_count or requirements.latency_requirements_ms:
            analysis['complexity_level'] = 'complex'
        elif requirements.burst_requirements or requirements.availability_requirements:
            analysis['complexity_level'] = 'moderate'
        
        # Optimization opportunities
        if not requirements.burst_requirements:
            analysis['optimization_opportunities'].append('Consider burstable instances for cost savings')
        
        if not requirements.availability_requirements:
            analysis['optimization_opportunities'].append('Specify availability requirements for better recommendations')
        
        return analysis
    
    def _recommendation_to_dict(self, rec: InstanceRecommendation) -> Dict[str, Any]:
        """Convert recommendation to dictionary"""
        return {
            'instance_type': rec.instance_type,
            'confidence_score': round(rec.confidence_score, 3),
            'monthly_cost_estimate': round(rec.monthly_cost_estimate, 2),
            'performance_score': round(rec.performance_score, 1),
            'suitability_reasons': rec.suitability_reasons,
            'limitations': rec.limitations,
            'configuration_recommendations': rec.configuration_recommendations
        }
    
    def get_instance_specifications(self, instance_type: str) -> Dict[str, Any]:
        """Get detailed specifications for an instance type"""
        if instance_type not in self.instance_types:
            raise ValueError(f"Unknown instance type: {instance_type}")
        
        specs = self.instance_types[instance_type].copy()
        specs['hourly_cost'] = self.pricing_data.get(instance_type, 0)
        specs['monthly_cost_estimate'] = specs['hourly_cost'] * 24 * 30
        specs['performance_benchmarks'] = {
            'compute_score': self.performance_benchmarks['compute_score'].get(instance_type),
            'memory_bandwidth': self.performance_benchmarks['memory_bandwidth'].get(instance_type),
            'network_performance': self.performance_benchmarks['network_performance'].get(instance_type)
        }
        
        return specs