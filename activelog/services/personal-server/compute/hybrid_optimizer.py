"""
ActiveLog Personal Server - Hybrid Compute Decision Engine
Intelligent task allocation across personal servers, main API, and cloud resources
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import asyncio
import json
import logging

class ComputeTarget(Enum):
    """Available compute targets for task allocation"""
    MAIN_API = "main_api"              # Secure main servers
    PERSONAL_SERVER = "personal_server" # User's personal server
    LOCAL_MACHINE = "local_machine"    # User's local computer
    BURST_TO_CLOUD = "burst_to_cloud"  # Temporary cloud resources
    HYBRID = "hybrid"                  # Split across multiple targets

class TaskSensitivity(Enum):
    """Task sensitivity levels for security considerations"""
    PUBLIC = "public"        # No sensitive data
    LOW = "low"             # Minimal sensitive data
    MEDIUM = "medium"       # Some sensitive data
    HIGH = "high"           # Highly sensitive data
    CRITICAL = "critical"   # Critical business data

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

@dataclass
class TaskRequirements:
    """Requirements and characteristics of a computational task"""
    task_id: str
    task_type: str
    sensitivity: TaskSensitivity
    priority: TaskPriority
    
    # Performance requirements
    latency_critical: bool = False
    compute_heavy: bool = False
    memory_intensive: bool = False
    requires_gpu: bool = False
    requires_specialized_hardware: bool = False
    
    # Resource estimates
    estimated_cpu_hours: float = 0.1
    estimated_memory_gb: float = 0.5
    estimated_storage_gb: float = 0.1
    estimated_network_gb: float = 0.01
    estimated_duration_minutes: float = 5.0
    
    # Data characteristics
    input_data_size_gb: float = 0.0
    output_data_size_gb: float = 0.0
    requires_data_locality: bool = False
    
    # Dependencies and constraints
    dependencies: List[str] = field(default_factory=list)
    allowed_targets: Set[ComputeTarget] = field(default_factory=lambda: set(ComputeTarget))
    prohibited_targets: Set[ComputeTarget] = field(default_factory=set)
    
    # Metadata
    user_id: str = ""
    application: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ComputeResource:
    """Represents available compute resources"""
    target: ComputeTarget
    available: bool
    
    # Capacity
    cpu_cores: int
    memory_gb: float
    storage_gb: float
    gpu_available: bool = False
    
    # Performance metrics
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    current_load: float = 0.0
    
    # Cost metrics
    cost_per_hour: float = 0.0
    cost_per_gb_transfer: float = 0.0
    
    # Reliability and security
    availability_sla: float = 0.99
    security_level: str = "standard"
    data_residency: str = "unknown"
    
    # Current status
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    health_status: str = "healthy"

@dataclass
class UserConfiguration:
    """User's configuration and preferences for compute allocation"""
    user_id: str
    
    # Budget and cost preferences
    budget_mode: bool = False
    max_hourly_spend: float = 10.0
    cost_optimization_priority: float = 0.5  # 0=performance, 1=cost
    
    # Performance preferences
    performance_priority: float = 0.7  # 0=cost, 1=performance
    acceptable_latency_ms: int = 5000
    acceptable_processing_time_multiplier: float = 2.0
    
    # Security and compliance
    data_residency_requirements: Set[str] = field(default_factory=set)
    security_requirements: Set[str] = field(default_factory=set)
    compliance_requirements: Set[str] = field(default_factory=set)
    
    # Resource preferences
    preferred_targets: List[ComputeTarget] = field(default_factory=list)
    avoided_targets: List[ComputeTarget] = field(default_factory=list)
    
    # Auto-scaling settings
    auto_scale_enabled: bool = True
    max_burst_duration_minutes: int = 60
    burst_cost_threshold: float = 5.0

@dataclass
class AllocationDecision:
    """Result of compute allocation decision"""
    task_id: str
    selected_target: ComputeTarget
    confidence: float
    reasoning: str
    
    # Estimated metrics
    estimated_cost: float
    estimated_duration: float
    estimated_performance_score: float
    
    # Alternative options
    alternative_allocations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Execution details
    resource_allocation: Dict[str, Any] = field(default_factory=dict)
    execution_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Monitoring and fallback
    fallback_targets: List[ComputeTarget] = field(default_factory=list)
    monitoring_requirements: Dict[str, Any] = field(default_factory=dict)

class HybridComputeOptimizer:
    """
    Intelligent compute allocation engine that optimizes task distribution
    across personal servers, main API, and cloud resources
    """
    
    def __init__(self):
        self.available_resources: Dict[ComputeTarget, ComputeResource] = {}
        self.allocation_history: List[AllocationDecision] = []
        self.performance_metrics: Dict[str, float] = {}
        self.cost_tracking: Dict[str, float] = {}
        
        # Decision engine configuration
        self.decision_weights = {
            "cost": 0.25,
            "performance": 0.25,
            "security": 0.20,
            "reliability": 0.15,
            "latency": 0.15
        }
        
        # Initialize available resources
        self._initialize_resources()
        
        self.logger = logging.getLogger(__name__)
    
    def _initialize_resources(self):
        """Initialize available compute resources"""
        
        # Main API servers (secure, reliable, higher cost)
        self.available_resources[ComputeTarget.MAIN_API] = ComputeResource(
            target=ComputeTarget.MAIN_API,
            available=True,
            cpu_cores=8,
            memory_gb=32,
            storage_gb=1000,
            cost_per_hour=0.50,
            availability_sla=0.999,
            security_level="enterprise",
            data_residency="us-east-1"
        )
        
        # Personal server (user-controlled, moderate cost)
        self.available_resources[ComputeTarget.PERSONAL_SERVER] = ComputeResource(
            target=ComputeTarget.PERSONAL_SERVER,
            available=True,
            cpu_cores=4,
            memory_gb=8,
            storage_gb=500,
            cost_per_hour=0.10,
            availability_sla=0.95,
            security_level="personal",
            data_residency="user_controlled"
        )
        
        # Local machine (free but limited)
        self.available_resources[ComputeTarget.LOCAL_MACHINE] = ComputeResource(
            target=ComputeTarget.LOCAL_MACHINE,
            available=True,
            cpu_cores=2,
            memory_gb=4,
            storage_gb=100,
            cost_per_hour=0.0,
            availability_sla=0.90,
            security_level="local",
            data_residency="local"
        )
        
        # Cloud burst (high performance, highest cost)
        self.available_resources[ComputeTarget.BURST_TO_CLOUD] = ComputeResource(
            target=ComputeTarget.BURST_TO_CLOUD,
            available=True,
            cpu_cores=16,
            memory_gb=64,
            storage_gb=2000,
            gpu_available=True,
            cost_per_hour=2.00,
            availability_sla=0.999,
            security_level="cloud",
            data_residency="multi_region"
        )
    
    async def allocate_task(self, task: TaskRequirements, 
                          user_config: UserConfiguration) -> AllocationDecision:
        """
        Main allocation function - decides optimal compute target for a task
        """
        
        # Evaluate all possible targets
        target_scores = {}
        
        for target, resource in self.available_resources.items():
            if not resource.available:
                continue
            
            # Check if target is allowed
            if task.allowed_targets and target not in task.allowed_targets:
                continue
            
            if target in task.prohibited_targets:
                continue
            
            # Calculate score for this target
            score = await self._calculate_target_score(task, user_config, target, resource)
            target_scores[target] = score
        
        if not target_scores:
            raise ValueError("No suitable compute targets available")
        
        # Select best target
        best_target = max(target_scores.items(), key=lambda x: x[1])
        selected_target, best_score = best_target
        
        # Generate allocation decision
        decision = await self._generate_allocation_decision(
            task, user_config, selected_target, best_score, target_scores
        )
        
        # Store decision for learning
        self.allocation_history.append(decision)
        
        return decision
    
    async def _calculate_target_score(self, task: TaskRequirements, 
                                    user_config: UserConfiguration,
                                    target: ComputeTarget, 
                                    resource: ComputeResource) -> float:
        """Calculate score for allocating task to specific target"""
        
        scores = {}
        
        # Cost score (0-1, higher is better/cheaper)
        scores["cost"] = await self._calculate_cost_score(task, user_config, resource)
        
        # Performance score (0-1, higher is better performance)
        scores["performance"] = await self._calculate_performance_score(task, resource)
        
        # Security score (0-1, higher is more secure)
        scores["security"] = await self._calculate_security_score(task, user_config, target)
        
        # Reliability score (0-1, higher is more reliable)
        scores["reliability"] = await self._calculate_reliability_score(task, resource)
        
        # Latency score (0-1, higher is lower latency)
        scores["latency"] = await self._calculate_latency_score(task, target)
        
        # Calculate weighted total score
        total_score = sum(
            scores[factor] * weight 
            for factor, weight in self.decision_weights.items()
        )
        
        # Apply user preferences
        total_score = await self._apply_user_preferences(
            total_score, scores, task, user_config, target
        )
        
        return total_score
    
    async def _calculate_cost_score(self, task: TaskRequirements,
                                  user_config: UserConfiguration,
                                  resource: ComputeResource) -> float:
        """Calculate cost score for resource (higher = cheaper)"""
        
        # Estimate total cost
        compute_cost = task.estimated_cpu_hours * resource.cost_per_hour
        transfer_cost = (task.input_data_size_gb + task.output_data_size_gb) * resource.cost_per_gb_transfer
        total_cost = compute_cost + transfer_cost
        
        # Free resources get perfect score
        if total_cost == 0:
            return 1.0
        
        # Score based on user's budget and preferences
        if user_config.budget_mode:
            # In budget mode, heavily favor low cost
            max_acceptable_cost = user_config.max_hourly_spend * 0.1  # 10% of budget
            if total_cost <= max_acceptable_cost:
                return 1.0
            else:
                return max(0.0, 1.0 - (total_cost - max_acceptable_cost) / max_acceptable_cost)
        else:
            # Normal mode - cost vs performance balance
            # Normalize cost (assume $10/hour as expensive)
            normalized_cost = min(total_cost / 10.0, 1.0)
            return 1.0 - normalized_cost
    
    async def _calculate_performance_score(self, task: TaskRequirements,
                                         resource: ComputeResource) -> float:
        """Calculate performance score for resource"""
        
        # Check if resource meets minimum requirements
        if task.requires_gpu and not resource.gpu_available:
            return 0.0
        
        # Calculate performance metrics
        cpu_score = min(resource.cpu_cores / max(task.estimated_cpu_hours * 4, 1), 1.0)
        memory_score = min(resource.memory_gb / max(task.estimated_memory_gb, 0.5), 1.0)
        
        # Factor in current utilization
        available_cpu = resource.cpu_cores * (1 - resource.cpu_utilization)
        available_memory = resource.memory_gb * (1 - resource.memory_utilization)
        
        utilization_penalty = (resource.cpu_utilization + resource.memory_utilization) / 2
        
        performance_score = (cpu_score + memory_score) / 2
        performance_score *= (1 - utilization_penalty * 0.5)  # 50% penalty for high utilization
        
        return max(0.0, min(1.0, performance_score))
    
    async def _calculate_security_score(self, task: TaskRequirements,
                                      user_config: UserConfiguration,
                                      target: ComputeTarget) -> float:
        """Calculate security score for target"""
        
        # High sensitivity tasks require secure targets
        if task.sensitivity == TaskSensitivity.CRITICAL:
            if target == ComputeTarget.MAIN_API:
                return 1.0
            elif target == ComputeTarget.PERSONAL_SERVER:
                return 0.7
            else:
                return 0.3
        
        elif task.sensitivity == TaskSensitivity.HIGH:
            if target in [ComputeTarget.MAIN_API, ComputeTarget.PERSONAL_SERVER]:
                return 0.9
            elif target == ComputeTarget.BURST_TO_CLOUD:
                return 0.6
            else:
                return 0.4
        
        elif task.sensitivity == TaskSensitivity.MEDIUM:
            if target == ComputeTarget.LOCAL_MACHINE:
                return 0.5
            else:
                return 0.8
        
        else:  # LOW or PUBLIC
            return 0.8  # Most targets are fine for low sensitivity
    
    async def _calculate_reliability_score(self, task: TaskRequirements,
                                         resource: ComputeResource) -> float:
        """Calculate reliability score for resource"""
        
        # Base score from SLA
        base_score = resource.availability_sla
        
        # Adjust based on health status
        if resource.health_status == "healthy":
            health_multiplier = 1.0
        elif resource.health_status == "degraded":
            health_multiplier = 0.7
        else:  # unhealthy
            health_multiplier = 0.3
        
        # Adjust based on current load
        load_penalty = resource.current_load * 0.2  # Up to 20% penalty for high load
        
        reliability_score = base_score * health_multiplier * (1 - load_penalty)
        
        return max(0.0, min(1.0, reliability_score))
    
    async def _calculate_latency_score(self, task: TaskRequirements,
                                     target: ComputeTarget) -> float:
        """Calculate latency score for target"""
        
        if not task.latency_critical:
            return 0.8  # Latency not critical, give decent score to all
        
        # Latency estimates (milliseconds)
        latency_estimates = {
            ComputeTarget.LOCAL_MACHINE: 10,
            ComputeTarget.PERSONAL_SERVER: 50,
            ComputeTarget.MAIN_API: 100,
            ComputeTarget.BURST_TO_CLOUD: 200
        }
        
        estimated_latency = latency_estimates.get(target, 500)
        
        # Score based on latency (lower is better)
        max_acceptable_latency = 1000  # 1 second
        if estimated_latency <= max_acceptable_latency:
            return 1.0 - (estimated_latency / max_acceptable_latency) * 0.5
        else:
            return 0.1  # Poor score for high latency
    
    async def _apply_user_preferences(self, base_score: float, scores: Dict[str, float],
                                    task: TaskRequirements, user_config: UserConfiguration,
                                    target: ComputeTarget) -> float:
        """Apply user preferences to modify base score"""
        
        # User's preferred targets get bonus
        if target in user_config.preferred_targets:
            base_score *= 1.2
        
        # User's avoided targets get penalty
        if target in user_config.avoided_targets:
            base_score *= 0.5
        
        # Budget mode heavily favors cost
        if user_config.budget_mode:
            base_score = base_score * 0.7 + scores["cost"] * 0.3
        
        # Performance priority adjustment
        if user_config.performance_priority > 0.7:
            base_score = base_score * 0.8 + scores["performance"] * 0.2
        
        return min(1.0, base_score)
    
    async def _generate_allocation_decision(self, task: TaskRequirements,
                                          user_config: UserConfiguration,
                                          selected_target: ComputeTarget,
                                          best_score: float,
                                          all_scores: Dict[ComputeTarget, float]) -> AllocationDecision:
        """Generate detailed allocation decision with reasoning"""
        
        resource = self.available_resources[selected_target]
        
        # Calculate estimated metrics
        estimated_cost = task.estimated_cpu_hours * resource.cost_per_hour
        estimated_duration = task.estimated_duration_minutes
        estimated_performance_score = best_score
        
        # Generate reasoning
        reasoning_parts = []
        
        if task.sensitivity in [TaskSensitivity.HIGH, TaskSensitivity.CRITICAL]:
            if selected_target == ComputeTarget.MAIN_API:
                reasoning_parts.append("High sensitivity task requires secure main API")
            elif selected_target == ComputeTarget.PERSONAL_SERVER:
                reasoning_parts.append("High sensitivity task allocated to personal server for security")
        
        if task.latency_critical and selected_target in [ComputeTarget.LOCAL_MACHINE, ComputeTarget.PERSONAL_SERVER]:
            reasoning_parts.append("Latency-critical task allocated to low-latency target")
        
        if task.compute_heavy and selected_target == ComputeTarget.BURST_TO_CLOUD:
            reasoning_parts.append("Compute-heavy task requires cloud burst resources")
        
        if user_config.budget_mode and estimated_cost < 0.10:
            reasoning_parts.append("Budget mode prioritizes cost-effective allocation")
        
        if not reasoning_parts:
            reasoning_parts.append(f"Optimal allocation based on weighted scoring (score: {best_score:.2f})")
        
        reasoning = "; ".join(reasoning_parts)
        
        # Generate alternative allocations
        alternatives = []
        sorted_targets = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[1:3]  # Top 2 alternatives
        
        for alt_target, alt_score in sorted_targets:
            alt_resource = self.available_resources[alt_target]
            alt_cost = task.estimated_cpu_hours * alt_resource.cost_per_hour
            
            alternatives.append({
                "target": alt_target.value,
                "score": alt_score,
                "estimated_cost": alt_cost,
                "trade_offs": f"Score: {alt_score:.2f}, Cost: ${alt_cost:.3f}"
            })
        
        # Generate fallback targets
        fallback_targets = [target for target, score in sorted(all_scores.items(), 
                                                              key=lambda x: x[1], reverse=True)[1:]]
        
        return AllocationDecision(
            task_id=task.task_id,
            selected_target=selected_target,
            confidence=best_score,
            reasoning=reasoning,
            estimated_cost=estimated_cost,
            estimated_duration=estimated_duration,
            estimated_performance_score=estimated_performance_score,
            alternative_allocations=alternatives,
            resource_allocation={
                "cpu_cores": min(resource.cpu_cores, int(task.estimated_cpu_hours * 2)),
                "memory_gb": min(resource.memory_gb, task.estimated_memory_gb * 1.2),
                "storage_gb": task.estimated_storage_gb
            },
            execution_parameters={
                "priority": task.priority.value,
                "max_duration": task.estimated_duration_minutes * 2,  # 2x buffer
                "resource_limits": True
            },
            fallback_targets=fallback_targets,
            monitoring_requirements={
                "performance_tracking": task.compute_heavy or task.latency_critical,
                "cost_tracking": user_config.budget_mode,
                "security_monitoring": task.sensitivity in [TaskSensitivity.HIGH, TaskSensitivity.CRITICAL]
            }
        )
    
    async def optimize_task_allocation(self, tasks: List[TaskRequirements],
                                     user_config: UserConfiguration,
                                     system_load: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimize allocation for multiple tasks simultaneously"""
        
        # Update resource status based on system load
        if system_load:
            await self._update_resource_status(system_load)
        
        # Allocate all tasks
        allocations = []
        total_cost = 0
        allocation_summary = defaultdict(int)
        
        # Sort tasks by priority and sensitivity
        sorted_tasks = sorted(tasks, key=lambda t: (t.priority.value, t.sensitivity.value), reverse=True)
        
        for task in sorted_tasks:
            try:
                allocation = await self.allocate_task(task, user_config)
                allocations.append(allocation)
                total_cost += allocation.estimated_cost
                allocation_summary[allocation.selected_target] += 1
                
                # Update resource utilization for subsequent tasks
                await self._update_resource_utilization(allocation.selected_target, task)
                
            except Exception as e:
                self.logger.error(f"Failed to allocate task {task.task_id}: {e}")
                continue
        
        # Generate optimization insights
        insights = await self._generate_optimization_insights(allocations, user_config)
        
        return {
            "allocations": [
                {
                    "task_id": alloc.task_id,
                    "target": alloc.selected_target.value,
                    "cost": alloc.estimated_cost,
                    "confidence": alloc.confidence,
                    "reasoning": alloc.reasoning
                }
                for alloc in allocations
            ],
            "estimated_savings": insights.get("estimated_savings", {}),
            "performance_metrics": {
                "total_tasks": len(tasks),
                "successfully_allocated": len(allocations),
                "allocation_distribution": {k.value: v for k, v in allocation_summary.items()},
                "total_estimated_cost": total_cost,
                "average_confidence": sum(a.confidence for a in allocations) / max(len(allocations), 1)
            },
            "decision_reasoning": insights.get("decision_patterns", {}),
            "optimization_recommendations": insights.get("recommendations", [])
        }
    
    async def _update_resource_status(self, system_load: Dict[str, Any]):
        """Update resource status based on current system load"""
        
        for target_name, load_info in system_load.items():
            try:
                target = ComputeTarget(target_name)
                if target in self.available_resources:
                    resource = self.available_resources[target]
                    resource.cpu_utilization = load_info.get("cpu_utilization", 0.0)
                    resource.memory_utilization = load_info.get("memory_utilization", 0.0)
                    resource.current_load = load_info.get("current_load", 0.0)
                    resource.available = load_info.get("available", True)
                    resource.last_updated = datetime.now(timezone.utc)
            except (ValueError, KeyError):
                continue
    
    async def _update_resource_utilization(self, target: ComputeTarget, task: TaskRequirements):
        """Update resource utilization after task allocation"""
        
        if target in self.available_resources:
            resource = self.available_resources[target]
            
            # Estimate utilization increase
            cpu_increase = task.estimated_cpu_hours / resource.cpu_cores
            memory_increase = task.estimated_memory_gb / resource.memory_gb
            
            resource.cpu_utilization = min(1.0, resource.cpu_utilization + cpu_increase)
            resource.memory_utilization = min(1.0, resource.memory_utilization + memory_increase)
            resource.current_load = (resource.cpu_utilization + resource.memory_utilization) / 2
    
    async def _generate_optimization_insights(self, allocations: List[AllocationDecision],
                                            user_config: UserConfiguration) -> Dict[str, Any]:
        """Generate insights about allocation patterns and optimization opportunities"""
        
        insights = {
            "estimated_savings": {},
            "decision_patterns": {},
            "recommendations": []
        }
        
        # Analyze allocation patterns
        target_distribution = Counter(alloc.selected_target for alloc in allocations)
        total_cost = sum(alloc.estimated_cost for alloc in allocations)
        
        insights["decision_patterns"] = {
            "most_used_target": target_distribution.most_common(1)[0][0].value if target_distribution else None,
            "cost_distribution": {
                target.value: sum(alloc.estimated_cost for alloc in allocations 
                                if alloc.selected_target == target)
                for target in target_distribution.keys()
            },
            "average_confidence": sum(alloc.confidence for alloc in allocations) / max(len(allocations), 1)
        }
        
        # Calculate potential savings
        personal_server_tasks = sum(1 for alloc in allocations 
                                  if alloc.selected_target == ComputeTarget.PERSONAL_SERVER)
        local_tasks = sum(1 for alloc in allocations 
                         if alloc.selected_target == ComputeTarget.LOCAL_MACHINE)
        
        if personal_server_tasks > 0 or local_tasks > 0:
            # Estimate savings vs using only main API
            main_api_cost = len(allocations) * 0.50  # Assume $0.50/hour for main API
            actual_cost = total_cost
            
            insights["estimated_savings"] = {
                "monthly": (main_api_cost - actual_cost) * 24 * 30,
                "percentage": ((main_api_cost - actual_cost) / max(main_api_cost, 0.01)) * 100
            }
        
        # Generate recommendations
        if user_config.budget_mode and total_cost > user_config.max_hourly_spend:
            insights["recommendations"].append("Consider upgrading personal server capacity to reduce cloud usage")
        
        if target_distribution.get(ComputeTarget.MAIN_API, 0) > len(allocations) * 0.7:
            insights["recommendations"].append("Many tasks using main API - personal server could reduce costs")
        
        if target_distribution.get(ComputeTarget.BURST_TO_CLOUD, 0) > 0:
            insights["recommendations"].append("Cloud burst usage detected - consider upgrading base capacity")
        
        return insights
    
    def is_running(self) -> bool:
        """Check if the optimizer is operational"""
        return len(self.available_resources) > 0
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get current status of all compute resources"""
        
        return {
            target.value: {
                "available": resource.available,
                "cpu_utilization": resource.cpu_utilization,
                "memory_utilization": resource.memory_utilization,
                "current_load": resource.current_load,
                "health_status": resource.health_status,
                "last_updated": resource.last_updated.isoformat()
            }
            for target, resource in self.available_resources.items()
        }
    
    def get_allocation_statistics(self) -> Dict[str, Any]:
        """Get statistics about historical allocations"""
        
        if not self.allocation_history:
            return {"message": "No allocation history available"}
        
        recent_allocations = [a for a in self.allocation_history 
                            if (datetime.now(timezone.utc) - 
                                datetime.fromisoformat(a.task_id.split('_')[-1] if '_' in a.task_id else '2024-01-01T00:00:00+00:00')
                                ).days <= 7]
        
        target_distribution = Counter(alloc.selected_target for alloc in recent_allocations)
        
        return {
            "total_allocations": len(self.allocation_history),
            "recent_allocations": len(recent_allocations),
            "target_distribution": {k.value: v for k, v in target_distribution.items()},
            "average_confidence": sum(a.confidence for a in recent_allocations) / max(len(recent_allocations), 1),
            "total_estimated_cost": sum(a.estimated_cost for a in recent_allocations)
        }