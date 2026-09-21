import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import psutil
import math

class ResourceTier(Enum):
    MINIMAL = "minimal"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    
class WorkloadType(Enum):
    WEB_APP = "web_app"
    DATABASE = "database"
    CACHE = "cache"
    WORKER = "worker"
    HYBRID = "hybrid"

@dataclass
class ResourceRequirement:
    cpu_cores: float
    memory_gb: float
    storage_gb: float
    network_mbps: float
    gpu_required: bool = False
    special_requirements: List[str] = None

@dataclass
class ServerSpec:
    cpu_cores: int
    memory_gb: int
    storage_gb: int
    instance_type: str
    estimated_cost_monthly: float
    performance_score: float
    efficiency_ratio: float

class MinimalSpecCalculator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Resource baselines for different workloads
        self.workload_baselines = {
            WorkloadType.WEB_APP: ResourceRequirement(1.0, 2.0, 20, 100),
            WorkloadType.DATABASE: ResourceRequirement(2.0, 4.0, 50, 200),
            WorkloadType.CACHE: ResourceRequirement(1.0, 8.0, 10, 500),
            WorkloadType.WORKER: ResourceRequirement(2.0, 2.0, 20, 50),
            WorkloadType.HYBRID: ResourceRequirement(2.0, 4.0, 40, 200)
        }
        
        # Instance type catalog with pricing
        self.instance_catalog = {
            "nano": {"cpu": 1, "memory": 1, "cost": 5.50, "network": 100},
            "micro": {"cpu": 1, "memory": 2, "cost": 8.50, "network": 200},
            "small": {"cpu": 1, "memory": 4, "cost": 16.00, "network": 500},
            "medium": {"cpu": 2, "memory": 8, "cost": 32.00, "network": 1000},
            "large": {"cpu": 4, "memory": 16, "cost": 64.00, "network": 2000},
            "xlarge": {"cpu": 8, "memory": 32, "cost": 128.00, "network": 4000},
            "2xlarge": {"cpu": 16, "memory": 64, "cost": 256.00, "network": 8000}
        }

    async def analyze_usage_patterns(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze usage patterns to determine resource requirements"""
        try:
            analysis = {
                "peak_cpu_usage": usage_data.get("cpu_peaks", []),
                "memory_patterns": usage_data.get("memory_usage", []),
                "storage_growth": usage_data.get("storage_growth", 0),
                "network_patterns": usage_data.get("network_usage", []),
                "concurrent_users": usage_data.get("concurrent_users", 1),
                "feature_usage": usage_data.get("features", {}),
                "time_patterns": usage_data.get("time_distribution", {})
            }
            
            # Calculate resource multipliers based on patterns
            cpu_multiplier = self._calculate_cpu_multiplier(analysis)
            memory_multiplier = self._calculate_memory_multiplier(analysis)
            storage_multiplier = self._calculate_storage_multiplier(analysis)
            network_multiplier = self._calculate_network_multiplier(analysis)
            
            return {
                "multipliers": {
                    "cpu": cpu_multiplier,
                    "memory": memory_multiplier,
                    "storage": storage_multiplier,
                    "network": network_multiplier
                },
                "analysis": analysis,
                "workload_type": self._identify_workload_type(analysis)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing usage patterns: {e}")
            return {"multipliers": {"cpu": 1.0, "memory": 1.0, "storage": 1.0, "network": 1.0}}

    def _calculate_cpu_multiplier(self, analysis: Dict[str, Any]) -> float:
        """Calculate CPU requirement multiplier based on usage patterns"""
        peak_usage = max(analysis.get("peak_cpu_usage", [50]), default=50)
        concurrent_users = analysis.get("concurrent_users", 1)
        
        # Base multiplier from peak usage
        base_multiplier = peak_usage / 100.0
        
        # User concurrency factor
        user_factor = math.log10(concurrent_users + 1) * 0.5
        
        # Feature complexity factor
        features = analysis.get("feature_usage", {})
        complex_features = ["ai_processing", "image_processing", "data_analytics"]
        complexity_factor = sum(0.3 for feature in complex_features if features.get(feature, 0) > 10)
        
        return max(0.5, base_multiplier + user_factor + complexity_factor)

    def _calculate_memory_multiplier(self, analysis: Dict[str, Any]) -> float:
        """Calculate memory requirement multiplier"""
        memory_patterns = analysis.get("memory_patterns", [])
        avg_memory = sum(memory_patterns) / len(memory_patterns) if memory_patterns else 50
        peak_memory = max(memory_patterns, default=70)
        
        concurrent_users = analysis.get("concurrent_users", 1)
        
        # Memory grows faster with concurrent users
        base_multiplier = peak_memory / 100.0
        user_multiplier = math.sqrt(concurrent_users) * 0.2
        
        # Cache-heavy features need more memory
        features = analysis.get("feature_usage", {})
        cache_factor = 0.5 if features.get("caching", 0) > 20 else 0
        
        return max(0.5, base_multiplier + user_multiplier + cache_factor)

    def _calculate_storage_multiplier(self, analysis: Dict[str, Any]) -> float:
        """Calculate storage requirement multiplier"""
        growth_rate = analysis.get("storage_growth", 0)  # GB per month
        concurrent_users = analysis.get("concurrent_users", 1)
        
        # Project storage needs for 12 months
        projected_growth = growth_rate * 12
        base_multiplier = 1.0 + (projected_growth / 20)  # 20GB baseline
        
        # User data factor
        user_factor = math.log10(concurrent_users + 1) * 0.3
        
        return max(1.0, base_multiplier + user_factor)

    def _calculate_network_multiplier(self, analysis: Dict[str, Any]) -> float:
        """Calculate network requirement multiplier"""
        network_patterns = analysis.get("network_patterns", [])
        peak_network = max(network_patterns, default=100)  # Mbps
        concurrent_users = analysis.get("concurrent_users", 1)
        
        base_multiplier = peak_network / 100.0
        user_multiplier = math.sqrt(concurrent_users) * 0.1
        
        # API-heavy applications need more bandwidth
        features = analysis.get("feature_usage", {})
        api_factor = 0.3 if features.get("api_calls", 0) > 1000 else 0
        
        return max(0.5, base_multiplier + user_multiplier + api_factor)

    def _identify_workload_type(self, analysis: Dict[str, Any]) -> WorkloadType:
        """Identify the primary workload type based on usage patterns"""
        features = analysis.get("feature_usage", {})
        
        # Database-heavy workload
        if features.get("database_operations", 0) > 500:
            return WorkloadType.DATABASE
        
        # Cache-heavy workload
        if features.get("caching", 0) > 100:
            return WorkloadType.CACHE
        
        # Background processing
        if features.get("background_jobs", 0) > 50:
            return WorkloadType.WORKER
        
        # Mixed workload
        feature_count = sum(1 for v in features.values() if v > 10)
        if feature_count > 3:
            return WorkloadType.HYBRID
        
        # Default to web app
        return WorkloadType.WEB_APP

    async def calculate_minimal_specs(
        self,
        usage_data: Dict[str, Any],
        tier: ResourceTier = ResourceTier.BALANCED,
        budget_limit: Optional[float] = None
    ) -> ServerSpec:
        """Calculate minimal server specifications based on usage data"""
        try:
            # Analyze usage patterns
            pattern_analysis = await self.analyze_usage_patterns(usage_data)
            workload_type = pattern_analysis["workload_type"]
            multipliers = pattern_analysis["multipliers"]
            
            # Get baseline requirements
            baseline = self.workload_baselines[workload_type]
            
            # Apply multipliers and tier adjustments
            tier_multiplier = self._get_tier_multiplier(tier)
            
            required_cpu = baseline.cpu_cores * multipliers["cpu"] * tier_multiplier
            required_memory = baseline.memory_gb * multipliers["memory"] * tier_multiplier
            required_storage = baseline.storage_gb * multipliers["storage"] * tier_multiplier
            required_network = baseline.network_mbps * multipliers["network"] * tier_multiplier
            
            # Find optimal instance type
            optimal_instance = self._find_optimal_instance(
                required_cpu, required_memory, required_storage, required_network, budget_limit
            )
            
            # Calculate performance metrics
            performance_score = self._calculate_performance_score(
                optimal_instance, required_cpu, required_memory
            )
            efficiency_ratio = self._calculate_efficiency_ratio(
                optimal_instance, required_cpu, required_memory
            )
            
            return ServerSpec(
                cpu_cores=optimal_instance["cpu"],
                memory_gb=optimal_instance["memory"],
                storage_gb=max(int(required_storage), 20),
                instance_type=optimal_instance["type"],
                estimated_cost_monthly=optimal_instance["cost"],
                performance_score=performance_score,
                efficiency_ratio=efficiency_ratio
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating minimal specs: {e}")
            # Return safe default
            return ServerSpec(2, 4, 40, "small", 16.00, 0.7, 0.8)

    def _get_tier_multiplier(self, tier: ResourceTier) -> float:
        """Get resource multiplier for the selected tier"""
        multipliers = {
            ResourceTier.MINIMAL: 0.8,
            ResourceTier.BALANCED: 1.0,
            ResourceTier.PERFORMANCE: 1.5
        }
        return multipliers[tier]

    def _find_optimal_instance(
        self,
        cpu_req: float,
        memory_req: float,
        storage_req: float,
        network_req: float,
        budget_limit: Optional[float]
    ) -> Dict[str, Any]:
        """Find the most cost-effective instance that meets requirements"""
        candidates = []
        
        for instance_type, specs in self.instance_catalog.items():
            # Check if instance meets minimum requirements
            if (specs["cpu"] >= cpu_req and 
                specs["memory"] >= memory_req and
                specs["network"] >= network_req):
                
                # Skip if over budget
                if budget_limit and specs["cost"] > budget_limit:
                    continue
                
                # Calculate efficiency score
                cpu_efficiency = specs["cpu"] / max(cpu_req, 0.1)
                memory_efficiency = specs["memory"] / max(memory_req, 0.1)
                cost_efficiency = 1.0 / specs["cost"]
                
                efficiency_score = (cpu_efficiency + memory_efficiency + cost_efficiency) / 3
                
                candidates.append({
                    "type": instance_type,
                    "cpu": specs["cpu"],
                    "memory": specs["memory"],
                    "network": specs["network"],
                    "cost": specs["cost"],
                    "efficiency": efficiency_score
                })
        
        # Return most efficient option, or fallback to small if none found
        if candidates:
            optimal = max(candidates, key=lambda x: x["efficiency"])
            return optimal
        else:
            # Fallback to small instance
            small_specs = self.instance_catalog["small"]
            return {
                "type": "small",
                "cpu": small_specs["cpu"],
                "memory": small_specs["memory"],
                "network": small_specs["network"],
                "cost": small_specs["cost"],
                "efficiency": 0.6
            }

    def _calculate_performance_score(self, instance: Dict[str, Any], req_cpu: float, req_memory: float) -> float:
        """Calculate performance score (0-1) based on how well instance meets requirements"""
        cpu_ratio = min(instance["cpu"] / max(req_cpu, 0.1), 2.0)
        memory_ratio = min(instance["memory"] / max(req_memory, 0.1), 2.0)
        
        # Performance score peaks at 100% over-provisioning
        cpu_score = 1.0 - abs(cpu_ratio - 1.5) / 1.5
        memory_score = 1.0 - abs(memory_ratio - 1.5) / 1.5
        
        return max(0.1, (cpu_score + memory_score) / 2)

    def _calculate_efficiency_ratio(self, instance: Dict[str, Any], req_cpu: float, req_memory: float) -> float:
        """Calculate resource utilization efficiency (0-1)"""
        cpu_utilization = min(req_cpu / instance["cpu"], 1.0)
        memory_utilization = min(req_memory / instance["memory"], 1.0)
        
        return (cpu_utilization + memory_utilization) / 2

    async def generate_recommendations(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate server recommendations for different tiers"""
        recommendations = {}
        
        for tier in ResourceTier:
            spec = await self.calculate_minimal_specs(usage_data, tier)
            recommendations[tier.value] = {
                "spec": spec,
                "description": self._get_tier_description(tier),
                "use_case": self._get_tier_use_case(tier)
            }
        
        # Add cost comparison
        costs = [rec["spec"].estimated_cost_monthly for rec in recommendations.values()]
        recommendations["cost_comparison"] = {
            "min_cost": min(costs),
            "max_cost": max(costs),
            "savings_minimal": max(costs) - min(costs)
        }
        
        return recommendations

    def _get_tier_description(self, tier: ResourceTier) -> str:
        descriptions = {
            ResourceTier.MINIMAL: "Most cost-effective option with essential resources only",
            ResourceTier.BALANCED: "Optimal balance of performance and cost",
            ResourceTier.PERFORMANCE: "Maximum performance with generous resource allocation"
        }
        return descriptions[tier]

    def _get_tier_use_case(self, tier: ResourceTier) -> str:
        use_cases = {
            ResourceTier.MINIMAL: "Development, testing, low-traffic personal use",
            ResourceTier.BALANCED: "Production use, moderate traffic, general purpose",
            ResourceTier.PERFORMANCE: "High traffic, mission-critical, performance-sensitive applications"
        }
        return use_cases[tier]

    async def optimize_for_budget(self, usage_data: Dict[str, Any], budget: float) -> Dict[str, Any]:
        """Find the best configuration within budget constraints"""
        try:
            # Try each tier within budget
            for tier in [ResourceTier.PERFORMANCE, ResourceTier.BALANCED, ResourceTier.MINIMAL]:
                spec = await self.calculate_minimal_specs(usage_data, tier, budget)
                
                if spec.estimated_cost_monthly <= budget:
                    return {
                        "recommended_spec": spec,
                        "tier": tier.value,
                        "budget_utilization": spec.estimated_cost_monthly / budget,
                        "monthly_savings": budget - spec.estimated_cost_monthly,
                        "performance_trade_offs": self._analyze_performance_tradeoffs(spec, usage_data)
                    }
            
            # If no tier fits budget, return minimal with warnings
            minimal_spec = await self.calculate_minimal_specs(usage_data, ResourceTier.MINIMAL)
            return {
                "recommended_spec": minimal_spec,
                "tier": "minimal",
                "budget_exceeded": True,
                "additional_cost": minimal_spec.estimated_cost_monthly - budget,
                "warning": "Budget insufficient for recommended specifications"
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing for budget: {e}")
            return {"error": str(e)}

    def _analyze_performance_tradeoffs(self, spec: ServerSpec, usage_data: Dict[str, Any]) -> Dict[str, str]:
        """Analyze performance trade-offs of the selected specification"""
        tradeoffs = {}
        
        if spec.performance_score < 0.7:
            tradeoffs["performance"] = "May experience slower response times during peak usage"
        
        if spec.efficiency_ratio > 0.9:
            tradeoffs["capacity"] = "Limited headroom for traffic spikes or feature expansion"
        
        if spec.memory_gb < 8 and usage_data.get("concurrent_users", 1) > 50:
            tradeoffs["concurrency"] = "Memory constraints may limit concurrent user capacity"
        
        return tradeoffs