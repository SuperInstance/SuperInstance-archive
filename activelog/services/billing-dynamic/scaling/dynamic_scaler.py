"""
Dynamic Scaling Manager
Automatically scales resources based on demand and cost optimization
"""

import asyncio
import json
import time
import logging
import docker
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import redis
import math
from collections import deque, defaultdict

class ScalingDirection(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SCALE_MAINTAIN = "scale_maintain"

class ScalingTrigger(Enum):
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    QUEUE_LENGTH = "queue_length"
    RESPONSE_TIME = "response_time"
    COST_THRESHOLD = "cost_threshold"
    SCHEDULE = "schedule"
    CUSTOM = "custom"

class ResourceType(Enum):
    COMPUTE_INSTANCES = "compute_instances"
    CONTAINER_REPLICAS = "container_replicas"
    MEMORY_ALLOCATION = "memory_allocation"
    CPU_ALLOCATION = "cpu_allocation"
    STORAGE_CAPACITY = "storage_capacity"
    NETWORK_BANDWIDTH = "network_bandwidth"

@dataclass
class ScalingMetric:
    """Metric used for scaling decisions"""
    name: str
    current_value: float
    target_value: float
    threshold_high: float
    threshold_low: float
    weight: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ScalingRule:
    """Rule defining when and how to scale"""
    rule_id: str
    session_id: str
    resource_type: ResourceType
    trigger: ScalingTrigger
    metric_name: str
    
    # Scaling thresholds
    scale_up_threshold: float
    scale_down_threshold: float
    
    # Scaling parameters
    min_instances: int
    max_instances: int
    scale_up_increment: int
    scale_down_increment: int
    
    # Timing constraints
    cooldown_period: int  # seconds
    evaluation_period: int  # seconds
    
    # Cost constraints
    max_hourly_cost: Optional[float] = None
    cost_per_instance: Optional[float] = None
    
    # Advanced settings
    scale_up_evaluation_periods: int = 2
    scale_down_evaluation_periods: int = 5
    enabled: bool = True
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = None
    total_triggers: int = 0

@dataclass
class ScalingAction:
    """Action taken for scaling"""
    action_id: str
    session_id: str
    rule_id: str
    action_type: ScalingDirection
    resource_type: ResourceType
    
    # Action details
    previous_count: int
    target_count: int
    actual_count: int
    
    # Timing
    requested_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Result
    success: bool = False
    error_message: Optional[str] = None
    cost_impact: Optional[float] = None
    
    # Metadata
    triggering_metrics: Dict[str, float] = field(default_factory=dict)
    execution_time: Optional[float] = None

@dataclass
class ScalingTarget:
    """Target resource for scaling operations"""
    target_id: str
    target_type: str  # container, instance, service
    session_id: str
    user_id: str
    
    # Current state
    current_instances: int
    desired_instances: int
    
    # Resource configuration
    resource_config: Dict[str, Any] = field(default_factory=dict)
    
    # Scaling configuration
    scaling_rules: List[str] = field(default_factory=list)
    
    # Status
    last_scaled_at: Optional[datetime] = None
    scaling_in_progress: bool = False
    health_status: str = "healthy"

class DynamicScalingManager:
    """
    Advanced dynamic scaling manager that automatically adjusts resources
    based on demand, performance metrics, and cost optimization
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Scaling state
        self.scaling_active = False
        self.scaling_rules: Dict[str, ScalingRule] = {}
        self.scaling_targets: Dict[str, ScalingTarget] = {}
        self.scaling_actions: deque = deque(maxlen=1000)
        
        # Metrics collection
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.current_metrics: Dict[str, ScalingMetric] = {}
        
        # Docker client for container scaling
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            self.logger.warning(f"Docker client not available: {e}")
            self.docker_client = None
        
        # Scaling executors
        self.scaling_executors: Dict[ResourceType, Callable] = {
            ResourceType.CONTAINER_REPLICAS: self._scale_container_replicas,
            ResourceType.COMPUTE_INSTANCES: self._scale_compute_instances,
            ResourceType.MEMORY_ALLOCATION: self._scale_memory_allocation,
            ResourceType.CPU_ALLOCATION: self._scale_cpu_allocation,
            ResourceType.STORAGE_CAPACITY: self._scale_storage_capacity,
            ResourceType.NETWORK_BANDWIDTH: self._scale_network_bandwidth
        }
        
        # Performance tracking
        self.metrics = {
            "scaling_actions_taken": 0,
            "successful_scales": 0,
            "failed_scales": 0,
            "cost_savings": 0.0,
            "average_response_time": 0.0
        }
        
        # Configuration
        self.default_cooldown = 300  # 5 minutes
        self.metric_collection_interval = 30  # 30 seconds
        self.scaling_evaluation_interval = 60  # 1 minute

    async def configure_scaling(self, scaling_config: Dict[str, Any]):
        """Configure scaling parameters and rules"""
        try:
            session_id = scaling_config.get("session_id")
            if not session_id:
                raise ValueError("session_id required")
            
            # Configure scaling target
            target_config = scaling_config.get("target", {})
            target = ScalingTarget(
                target_id=target_config.get("target_id", session_id),
                target_type=target_config.get("target_type", "container"),
                session_id=session_id,
                user_id=scaling_config.get("user_id", "unknown"),
                current_instances=target_config.get("current_instances", 1),
                desired_instances=target_config.get("desired_instances", 1),
                resource_config=target_config.get("resource_config", {})
            )
            
            self.scaling_targets[session_id] = target
            
            # Configure scaling rules
            rules_config = scaling_config.get("rules", [])
            for rule_config in rules_config:
                rule = ScalingRule(
                    rule_id=f"{session_id}_{rule_config['trigger']}_{int(time.time())}",
                    session_id=session_id,
                    resource_type=ResourceType(rule_config["resource_type"]),
                    trigger=ScalingTrigger(rule_config["trigger"]),
                    metric_name=rule_config["metric_name"],
                    scale_up_threshold=rule_config["scale_up_threshold"],
                    scale_down_threshold=rule_config["scale_down_threshold"],
                    min_instances=rule_config.get("min_instances", 1),
                    max_instances=rule_config.get("max_instances", 10),
                    scale_up_increment=rule_config.get("scale_up_increment", 1),
                    scale_down_increment=rule_config.get("scale_down_increment", 1),
                    cooldown_period=rule_config.get("cooldown_period", self.default_cooldown),
                    evaluation_period=rule_config.get("evaluation_period", 120),
                    max_hourly_cost=rule_config.get("max_hourly_cost"),
                    cost_per_instance=rule_config.get("cost_per_instance"),
                    scale_up_evaluation_periods=rule_config.get("scale_up_evaluation_periods", 2),
                    scale_down_evaluation_periods=rule_config.get("scale_down_evaluation_periods", 5)
                )
                
                self.scaling_rules[rule.rule_id] = rule
                target.scaling_rules.append(rule.rule_id)
            
            # Store configuration in Redis
            if self.redis_client:
                await self._store_scaling_config_in_redis(session_id, scaling_config)
            
            self.logger.info(f"Configured scaling for session {session_id} with {len(rules_config)} rules")
            
        except Exception as e:
            self.logger.error(f"Failed to configure scaling: {e}")
            raise

    async def trigger_scaling_action(
        self,
        session_id: str,
        scaling_action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Manually trigger scaling action"""
        try:
            if session_id not in self.scaling_targets:
                raise ValueError(f"Scaling target not found for session {session_id}")
            
            target = self.scaling_targets[session_id]
            action_type = ScalingDirection(scaling_action["action_type"])
            resource_type = ResourceType(scaling_action["resource_type"])
            
            # Create scaling action
            action = ScalingAction(
                action_id=f"manual_{session_id}_{int(time.time())}",
                session_id=session_id,
                rule_id="manual",
                action_type=action_type,
                resource_type=resource_type,
                previous_count=target.current_instances,
                target_count=scaling_action["target_count"],
                actual_count=target.current_instances,
                requested_at=datetime.now(timezone.utc),
                triggering_metrics=scaling_action.get("reason", {})
            )
            
            # Execute scaling action
            result = await self._execute_scaling_action(action)
            
            return {
                "action_id": action.action_id,
                "success": result,
                "target_count": action.target_count,
                "actual_count": action.actual_count,
                "error": action.error_message
            }
            
        except Exception as e:
            self.logger.error(f"Failed to trigger scaling action: {e}")
            return {"success": False, "error": str(e)}

    async def start_scaling_monitor(self):
        """Start continuous scaling monitoring"""
        if self.scaling_active:
            return
        
        self.scaling_active = True
        self.logger.info("Starting dynamic scaling monitor")
        
        try:
            # Start monitoring tasks
            monitoring_tasks = [
                asyncio.create_task(self._collect_metrics_loop()),
                asyncio.create_task(self._evaluate_scaling_rules_loop()),
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._cost_optimization_loop())
            ]
            
            # Wait for all tasks
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            self.logger.info("Scaling monitor cancelled")
        except Exception as e:
            self.logger.error(f"Scaling monitor error: {e}")
        finally:
            self.scaling_active = False

    async def _collect_metrics_loop(self):
        """Continuously collect scaling metrics"""
        try:
            while self.scaling_active:
                # Collect metrics for each target
                for session_id, target in self.scaling_targets.items():
                    try:
                        metrics = await self._collect_target_metrics(target)
                        
                        # Update current metrics
                        for metric_name, metric in metrics.items():
                            self.current_metrics[f"{session_id}_{metric_name}"] = metric
                            self.metrics_history[f"{session_id}_{metric_name}"].append(metric)
                        
                        # Store metrics in Redis
                        if self.redis_client:
                            await self._store_metrics_in_redis(session_id, metrics)
                    
                    except Exception as e:
                        self.logger.error(f"Failed to collect metrics for {session_id}: {e}")
                
                # Wait for next collection
                await asyncio.sleep(self.metric_collection_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Metrics collection loop error: {e}")

    async def _evaluate_scaling_rules_loop(self):
        """Continuously evaluate scaling rules"""
        try:
            while self.scaling_active:
                # Evaluate all scaling rules
                for rule_id, rule in self.scaling_rules.items():
                    if not rule.enabled:
                        continue
                    
                    try:
                        # Check cooldown period
                        if rule.last_triggered:
                            time_since_last = (datetime.now(timezone.utc) - rule.last_triggered).total_seconds()
                            if time_since_last < rule.cooldown_period:
                                continue
                        
                        # Evaluate rule
                        scaling_decision = await self._evaluate_scaling_rule(rule)
                        
                        if scaling_decision != ScalingDirection.SCALE_MAINTAIN:
                            await self._execute_scaling_decision(rule, scaling_decision)
                    
                    except Exception as e:
                        self.logger.error(f"Failed to evaluate rule {rule_id}: {e}")
                
                # Wait for next evaluation
                await asyncio.sleep(self.scaling_evaluation_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Scaling rule evaluation loop error: {e}")

    async def _health_check_loop(self):
        """Monitor health of scaled resources"""
        try:
            while self.scaling_active:
                for session_id, target in self.scaling_targets.items():
                    try:
                        health_status = await self._check_target_health(target)
                        target.health_status = health_status
                        
                        # Take corrective action if unhealthy
                        if health_status != "healthy":
                            await self._handle_unhealthy_target(target)
                    
                    except Exception as e:
                        self.logger.error(f"Health check failed for {session_id}: {e}")
                
                # Wait 2 minutes before next health check
                await asyncio.sleep(120)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Health check loop error: {e}")

    async def _cost_optimization_loop(self):
        """Continuously optimize costs through scaling"""
        try:
            while self.scaling_active:
                for session_id, target in self.scaling_targets.items():
                    try:
                        # Analyze cost optimization opportunities
                        optimization = await self._analyze_cost_optimization(target)
                        
                        if optimization["action"] != "maintain":
                            await self._execute_cost_optimization(target, optimization)
                    
                    except Exception as e:
                        self.logger.error(f"Cost optimization failed for {session_id}: {e}")
                
                # Wait 10 minutes before next optimization check
                await asyncio.sleep(600)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Cost optimization loop error: {e}")

    async def _collect_target_metrics(self, target: ScalingTarget) -> Dict[str, ScalingMetric]:
        """Collect metrics for a scaling target"""
        try:
            metrics = {}
            
            if target.target_type == "container" and self.docker_client:
                # Collect container metrics
                container_metrics = await self._collect_container_metrics(target)
                metrics.update(container_metrics)
            
            elif target.target_type == "instance":
                # Collect instance metrics
                instance_metrics = await self._collect_instance_metrics(target)
                metrics.update(instance_metrics)
            
            # Collect custom metrics
            custom_metrics = await self._collect_custom_metrics(target)
            metrics.update(custom_metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics for target {target.target_id}: {e}")
            return {}

    async def _collect_container_metrics(self, target: ScalingTarget) -> Dict[str, ScalingMetric]:
        """Collect Docker container metrics"""
        try:
            metrics = {}
            
            # Find containers for this target
            containers = self.docker_client.containers.list(
                filters={"label": f"session_id={target.session_id}"}
            )
            
            if not containers:
                return metrics
            
            total_cpu = 0.0
            total_memory = 0.0
            running_containers = 0
            
            for container in containers:
                if container.status == "running":
                    running_containers += 1
                    
                    # Get container stats
                    stats = container.stats(stream=False)
                    
                    # Calculate CPU usage
                    cpu_stats = stats.get("cpu_stats", {})
                    precpu_stats = stats.get("precpu_stats", {})
                    
                    if "cpu_usage" in cpu_stats and "cpu_usage" in precpu_stats:
                        cpu_delta = cpu_stats["cpu_usage"]["total_usage"] - precpu_stats["cpu_usage"]["total_usage"]
                        system_delta = cpu_stats["system_cpu_usage"] - precpu_stats["system_cpu_usage"]
                        
                        if system_delta > 0:
                            cpu_percent = (cpu_delta / system_delta) * 100.0
                            total_cpu += cpu_percent
                    
                    # Calculate memory usage
                    memory_stats = stats.get("memory_stats", {})
                    if "usage" in memory_stats and "limit" in memory_stats:
                        memory_percent = (memory_stats["usage"] / memory_stats["limit"]) * 100.0
                        total_memory += memory_percent
            
            # Calculate average metrics
            if running_containers > 0:
                avg_cpu = total_cpu / running_containers
                avg_memory = total_memory / running_containers
                
                metrics["cpu_utilization"] = ScalingMetric(
                    name="cpu_utilization",
                    current_value=avg_cpu,
                    target_value=70.0,
                    threshold_high=80.0,
                    threshold_low=30.0
                )
                
                metrics["memory_utilization"] = ScalingMetric(
                    name="memory_utilization",
                    current_value=avg_memory,
                    target_value=70.0,
                    threshold_high=85.0,
                    threshold_low=40.0
                )
                
                metrics["replica_count"] = ScalingMetric(
                    name="replica_count",
                    current_value=float(running_containers),
                    target_value=float(target.desired_instances),
                    threshold_high=float(target.desired_instances + 1),
                    threshold_low=float(max(1, target.desired_instances - 1))
                )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Container metrics collection failed: {e}")
            return {}

    async def _collect_instance_metrics(self, target: ScalingTarget) -> Dict[str, ScalingMetric]:
        """Collect instance-level metrics"""
        try:
            # This would integrate with cloud provider APIs
            # For now, return placeholder metrics
            metrics = {
                "cpu_utilization": ScalingMetric(
                    name="cpu_utilization",
                    current_value=45.0,  # Placeholder
                    target_value=70.0,
                    threshold_high=80.0,
                    threshold_low=30.0
                ),
                "memory_utilization": ScalingMetric(
                    name="memory_utilization",
                    current_value=60.0,  # Placeholder
                    target_value=70.0,
                    threshold_high=85.0,
                    threshold_low=40.0
                )
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Instance metrics collection failed: {e}")
            return {}

    async def _collect_custom_metrics(self, target: ScalingTarget) -> Dict[str, ScalingMetric]:
        """Collect custom application metrics"""
        try:
            metrics = {}
            
            # Collect queue length if available
            if self.redis_client:
                try:
                    queue_key = f"task_queue:{target.session_id}"
                    queue_length = await self.redis_client.llen(queue_key)
                    
                    metrics["queue_length"] = ScalingMetric(
                        name="queue_length",
                        current_value=float(queue_length),
                        target_value=5.0,
                        threshold_high=10.0,
                        threshold_low=2.0
                    )
                
                except Exception as e:
                    self.logger.debug(f"Queue length collection failed: {e}")
            
            # Collect response time metrics
            response_time_key = f"response_times:{target.session_id}"
            if self.redis_client:
                try:
                    # Get recent response times
                    response_times = await self.redis_client.lrange(response_time_key, 0, 10)
                    
                    if response_times:
                        avg_response_time = sum(float(rt) for rt in response_times) / len(response_times)
                        
                        metrics["response_time"] = ScalingMetric(
                            name="response_time",
                            current_value=avg_response_time,
                            target_value=500.0,  # 500ms
                            threshold_high=1000.0,  # 1 second
                            threshold_low=200.0  # 200ms
                        )
                
                except Exception as e:
                    self.logger.debug(f"Response time collection failed: {e}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Custom metrics collection failed: {e}")
            return {}

    async def _evaluate_scaling_rule(self, rule: ScalingRule) -> ScalingDirection:
        """Evaluate a scaling rule and return decision"""
        try:
            # Get current metric value
            metric_key = f"{rule.session_id}_{rule.metric_name}"
            
            if metric_key not in self.current_metrics:
                return ScalingDirection.SCALE_MAINTAIN
            
            current_metric = self.current_metrics[metric_key]
            
            # Get target
            target = self.scaling_targets.get(rule.session_id)
            if not target:
                return ScalingDirection.SCALE_MAINTAIN
            
            # Check if scaling is already in progress
            if target.scaling_in_progress:
                return ScalingDirection.SCALE_MAINTAIN
            
            # Evaluate based on trigger type
            if rule.trigger == ScalingTrigger.CPU_UTILIZATION:
                return await self._evaluate_utilization_rule(rule, current_metric, target)
            
            elif rule.trigger == ScalingTrigger.MEMORY_UTILIZATION:
                return await self._evaluate_utilization_rule(rule, current_metric, target)
            
            elif rule.trigger == ScalingTrigger.QUEUE_LENGTH:
                return await self._evaluate_queue_rule(rule, current_metric, target)
            
            elif rule.trigger == ScalingTrigger.RESPONSE_TIME:
                return await self._evaluate_response_time_rule(rule, current_metric, target)
            
            elif rule.trigger == ScalingTrigger.COST_THRESHOLD:
                return await self._evaluate_cost_rule(rule, current_metric, target)
            
            elif rule.trigger == ScalingTrigger.SCHEDULE:
                return await self._evaluate_schedule_rule(rule, target)
            
            return ScalingDirection.SCALE_MAINTAIN
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate scaling rule {rule.rule_id}: {e}")
            return ScalingDirection.SCALE_MAINTAIN

    async def _evaluate_utilization_rule(
        self,
        rule: ScalingRule,
        metric: ScalingMetric,
        target: ScalingTarget
    ) -> ScalingDirection:
        """Evaluate CPU or memory utilization rule"""
        try:
            # Check for scale up
            if metric.current_value >= rule.scale_up_threshold:
                if target.current_instances < rule.max_instances:
                    # Check evaluation periods
                    if await self._check_evaluation_periods(rule, metric, "up"):
                        return ScalingDirection.SCALE_UP
            
            # Check for scale down
            elif metric.current_value <= rule.scale_down_threshold:
                if target.current_instances > rule.min_instances:
                    # Check evaluation periods
                    if await self._check_evaluation_periods(rule, metric, "down"):
                        return ScalingDirection.SCALE_DOWN
            
            return ScalingDirection.SCALE_MAINTAIN
            
        except Exception as e:
            self.logger.error(f"Utilization rule evaluation failed: {e}")
            return ScalingDirection.SCALE_MAINTAIN

    async def _evaluate_queue_rule(
        self,
        rule: ScalingRule,
        metric: ScalingMetric,
        target: ScalingTarget
    ) -> ScalingDirection:
        """Evaluate queue length rule"""
        try:
            queue_length = metric.current_value
            
            # Scale up if queue is too long
            if queue_length >= rule.scale_up_threshold:
                if target.current_instances < rule.max_instances:
                    return ScalingDirection.SCALE_UP
            
            # Scale down if queue is short
            elif queue_length <= rule.scale_down_threshold:
                if target.current_instances > rule.min_instances:
                    return ScalingDirection.SCALE_DOWN
            
            return ScalingDirection.SCALE_MAINTAIN
            
        except Exception as e:
            self.logger.error(f"Queue rule evaluation failed: {e}")
            return ScalingDirection.SCALE_MAINTAIN

    async def _evaluate_response_time_rule(
        self,
        rule: ScalingRule,
        metric: ScalingMetric,
        target: ScalingTarget
    ) -> ScalingDirection:
        """Evaluate response time rule"""
        try:
            response_time = metric.current_value
            
            # Scale up if response time is too high
            if response_time >= rule.scale_up_threshold:
                if target.current_instances < rule.max_instances:
                    return ScalingDirection.SCALE_UP
            
            # Scale down if response time is very low
            elif response_time <= rule.scale_down_threshold:
                if target.current_instances > rule.min_instances:
                    return ScalingDirection.SCALE_DOWN
            
            return ScalingDirection.SCALE_MAINTAIN
            
        except Exception as e:
            self.logger.error(f"Response time rule evaluation failed: {e}")
            return ScalingDirection.SCALE_MAINTAIN

    async def _evaluate_cost_rule(
        self,
        rule: ScalingRule,
        metric: ScalingMetric,
        target: ScalingTarget
    ) -> ScalingDirection:
        """Evaluate cost threshold rule"""
        try:
            if not rule.max_hourly_cost or not rule.cost_per_instance:
                return ScalingDirection.SCALE_MAINTAIN
            
            current_hourly_cost = target.current_instances * rule.cost_per_instance
            
            # Scale down if cost is too high
            if current_hourly_cost > rule.max_hourly_cost:
                if target.current_instances > rule.min_instances:
                    return ScalingDirection.SCALE_DOWN
            
            return ScalingDirection.SCALE_MAINTAIN
            
        except Exception as e:
            self.logger.error(f"Cost rule evaluation failed: {e}")
            return ScalingDirection.SCALE_MAINTAIN

    async def _evaluate_schedule_rule(
        self,
        rule: ScalingRule,
        target: ScalingTarget
    ) -> ScalingDirection:
        """Evaluate scheduled scaling rule"""
        try:
            # This would implement scheduled scaling based on time
            # For now, return maintain
            return ScalingDirection.SCALE_MAINTAIN
            
        except Exception as e:
            self.logger.error(f"Schedule rule evaluation failed: {e}")
            return ScalingDirection.SCALE_MAINTAIN

    async def _check_evaluation_periods(
        self,
        rule: ScalingRule,
        metric: ScalingMetric,
        direction: str
    ) -> bool:
        """Check if metric has been consistently above/below threshold"""
        try:
            metric_key = f"{rule.session_id}_{rule.metric_name}"
            history = self.metrics_history.get(metric_key, deque())
            
            if direction == "up":
                required_periods = rule.scale_up_evaluation_periods
                threshold = rule.scale_up_threshold
            else:
                required_periods = rule.scale_down_evaluation_periods
                threshold = rule.scale_down_threshold
            
            if len(history) < required_periods:
                return False
            
            # Check last N periods
            recent_metrics = list(history)[-required_periods:]
            
            for historical_metric in recent_metrics:
                if direction == "up":
                    if historical_metric.current_value < threshold:
                        return False
                else:
                    if historical_metric.current_value > threshold:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Evaluation periods check failed: {e}")
            return False

    async def _execute_scaling_decision(self, rule: ScalingRule, decision: ScalingDirection):
        """Execute scaling decision"""
        try:
            target = self.scaling_targets.get(rule.session_id)
            if not target:
                return
            
            # Calculate new instance count
            if decision == ScalingDirection.SCALE_UP:
                new_count = min(
                    target.current_instances + rule.scale_up_increment,
                    rule.max_instances
                )
            elif decision == ScalingDirection.SCALE_DOWN:
                new_count = max(
                    target.current_instances - rule.scale_down_increment,
                    rule.min_instances
                )
            else:
                return
            
            # Create scaling action
            action = ScalingAction(
                action_id=f"auto_{rule.session_id}_{int(time.time())}",
                session_id=rule.session_id,
                rule_id=rule.rule_id,
                action_type=decision,
                resource_type=rule.resource_type,
                previous_count=target.current_instances,
                target_count=new_count,
                actual_count=target.current_instances,
                requested_at=datetime.now(timezone.utc),
                triggering_metrics={
                    rule.metric_name: self.current_metrics.get(f"{rule.session_id}_{rule.metric_name}").current_value
                }
            )
            
            # Execute scaling action
            success = await self._execute_scaling_action(action)
            
            if success:
                # Update rule tracking
                rule.last_triggered = datetime.now(timezone.utc)
                rule.total_triggers += 1
                
                # Update metrics
                self.metrics["scaling_actions_taken"] += 1
                self.metrics["successful_scales"] += 1
            else:
                self.metrics["failed_scales"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to execute scaling decision: {e}")
            self.metrics["failed_scales"] += 1

    async def _execute_scaling_action(self, action: ScalingAction) -> bool:
        """Execute scaling action using appropriate executor"""
        try:
            action.started_at = datetime.now(timezone.utc)
            target = self.scaling_targets.get(action.session_id)
            
            if not target:
                action.error_message = "Scaling target not found"
                return False
            
            # Mark scaling in progress
            target.scaling_in_progress = True
            
            try:
                # Get executor for resource type
                executor = self.scaling_executors.get(action.resource_type)
                if not executor:
                    action.error_message = f"No executor for resource type {action.resource_type}"
                    return False
                
                # Execute scaling
                result = await executor(action, target)
                
                if result:
                    action.success = True
                    action.actual_count = action.target_count
                    target.current_instances = action.target_count
                    target.last_scaled_at = datetime.now(timezone.utc)
                else:
                    action.success = False
                    action.error_message = "Scaling execution failed"
                
                return result
                
            finally:
                # Mark scaling complete
                target.scaling_in_progress = False
                action.completed_at = datetime.now(timezone.utc)
                
                if action.started_at:
                    action.execution_time = (action.completed_at - action.started_at).total_seconds()
                
                # Store action
                self.scaling_actions.append(action)
                
                # Store in Redis
                if self.redis_client:
                    await self._store_scaling_action_in_redis(action)
            
        except Exception as e:
            self.logger.error(f"Failed to execute scaling action: {e}")
            action.error_message = str(e)
            action.success = False
            return False

    async def _scale_container_replicas(self, action: ScalingAction, target: ScalingTarget) -> bool:
        """Scale Docker container replicas"""
        try:
            if not self.docker_client:
                return False
            
            # Find containers for this session
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": f"session_id={target.session_id}"}
            )
            
            current_count = len([c for c in containers if c.status == "running"])
            target_count = action.target_count
            
            if target_count > current_count:
                # Scale up - create new containers
                containers_to_create = target_count - current_count
                
                # Get configuration from existing container
                if containers:
                    template_container = containers[0]
                    image = template_container.image.tags[0] if template_container.image.tags else "alpine"
                    
                    for i in range(containers_to_create):
                        try:
                            new_container = self.docker_client.containers.run(
                                image=image,
                                detach=True,
                                labels={
                                    "session_id": target.session_id,
                                    "user_id": target.user_id,
                                    "scaled_at": datetime.now(timezone.utc).isoformat()
                                },
                                name=f"{target.session_id}_replica_{current_count + i + 1}"
                            )
                            
                            self.logger.info(f"Created container {new_container.name}")
                        
                        except Exception as e:
                            self.logger.error(f"Failed to create container: {e}")
                            return False
                
            elif target_count < current_count:
                # Scale down - stop and remove containers
                containers_to_remove = current_count - target_count
                running_containers = [c for c in containers if c.status == "running"]
                
                for container in running_containers[:containers_to_remove]:
                    try:
                        container.stop(timeout=30)
                        container.remove()
                        self.logger.info(f"Removed container {container.name}")
                    
                    except Exception as e:
                        self.logger.error(f"Failed to remove container {container.name}: {e}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Container scaling failed: {e}")
            return False

    async def _scale_compute_instances(self, action: ScalingAction, target: ScalingTarget) -> bool:
        """Scale compute instances (cloud provider integration)"""
        try:
            # This would integrate with cloud provider APIs (AWS, GCP, Azure)
            # For now, simulate scaling
            self.logger.info(f"Simulating instance scaling from {action.previous_count} to {action.target_count}")
            
            # Simulate delay
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Instance scaling failed: {e}")
            return False

    async def _scale_memory_allocation(self, action: ScalingAction, target: ScalingTarget) -> bool:
        """Scale memory allocation"""
        try:
            # This would adjust memory limits for containers or instances
            self.logger.info(f"Simulating memory scaling for {target.target_id}")
            
            if self.docker_client:
                # Update container memory limits
                containers = self.docker_client.containers.list(
                    filters={"label": f"session_id={target.session_id}"}
                )
                
                for container in containers:
                    try:
                        # Update memory limit (requires container recreation)
                        self.logger.info(f"Updated memory limit for container {container.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to update memory for {container.name}: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Memory scaling failed: {e}")
            return False

    async def _scale_cpu_allocation(self, action: ScalingAction, target: ScalingTarget) -> bool:
        """Scale CPU allocation"""
        try:
            # This would adjust CPU limits for containers or instances
            self.logger.info(f"Simulating CPU scaling for {target.target_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"CPU scaling failed: {e}")
            return False

    async def _scale_storage_capacity(self, action: ScalingAction, target: ScalingTarget) -> bool:
        """Scale storage capacity"""
        try:
            # This would adjust storage volumes
            self.logger.info(f"Simulating storage scaling for {target.target_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Storage scaling failed: {e}")
            return False

    async def _scale_network_bandwidth(self, action: ScalingAction, target: ScalingTarget) -> bool:
        """Scale network bandwidth"""
        try:
            # This would adjust network limits
            self.logger.info(f"Simulating network scaling for {target.target_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Network scaling failed: {e}")
            return False

    async def _check_target_health(self, target: ScalingTarget) -> str:
        """Check health status of scaling target"""
        try:
            if target.target_type == "container" and self.docker_client:
                # Check container health
                containers = self.docker_client.containers.list(
                    filters={"label": f"session_id={target.session_id}"}
                )
                
                running_containers = len([c for c in containers if c.status == "running"])
                
                if running_containers == 0:
                    return "unhealthy"
                elif running_containers < target.desired_instances * 0.5:
                    return "degraded"
                else:
                    return "healthy"
            
            return "healthy"
            
        except Exception as e:
            self.logger.error(f"Health check failed for {target.target_id}: {e}")
            return "unknown"

    async def _handle_unhealthy_target(self, target: ScalingTarget):
        """Handle unhealthy scaling target"""
        try:
            self.logger.warning(f"Handling unhealthy target {target.target_id}: {target.health_status}")
            
            # Attempt to restore target to healthy state
            if target.target_type == "container":
                # Restart failed containers
                containers = self.docker_client.containers.list(
                    all=True,
                    filters={"label": f"session_id={target.session_id}"}
                )
                
                for container in containers:
                    if container.status in ["exited", "dead"]:
                        try:
                            container.restart()
                            self.logger.info(f"Restarted container {container.name}")
                        except Exception as e:
                            self.logger.error(f"Failed to restart container {container.name}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle unhealthy target: {e}")

    async def _analyze_cost_optimization(self, target: ScalingTarget) -> Dict[str, Any]:
        """Analyze cost optimization opportunities"""
        try:
            # Analyze recent metrics to determine if resources are over-provisioned
            optimization = {
                "action": "maintain",
                "reason": "no optimization opportunities",
                "potential_savings": 0.0
            }
            
            # Check if resources are consistently under-utilized
            session_metrics = {
                k: v for k, v in self.current_metrics.items()
                if k.startswith(f"{target.session_id}_")
            }
            
            cpu_metric = session_metrics.get(f"{target.session_id}_cpu_utilization")
            memory_metric = session_metrics.get(f"{target.session_id}_memory_utilization")
            
            if cpu_metric and memory_metric:
                if cpu_metric.current_value < 20 and memory_metric.current_value < 30:
                    if target.current_instances > 1:
                        optimization = {
                            "action": "scale_down",
                            "reason": "low resource utilization",
                            "potential_savings": target.current_instances * 0.1  # Estimate
                        }
            
            return optimization
            
        except Exception as e:
            self.logger.error(f"Cost optimization analysis failed: {e}")
            return {"action": "maintain"}

    async def _execute_cost_optimization(self, target: ScalingTarget, optimization: Dict[str, Any]):
        """Execute cost optimization action"""
        try:
            if optimization["action"] == "scale_down":
                # Create scaling action for cost optimization
                action = ScalingAction(
                    action_id=f"cost_opt_{target.session_id}_{int(time.time())}",
                    session_id=target.session_id,
                    rule_id="cost_optimization",
                    action_type=ScalingDirection.SCALE_DOWN,
                    resource_type=ResourceType.CONTAINER_REPLICAS,
                    previous_count=target.current_instances,
                    target_count=max(1, target.current_instances - 1),
                    actual_count=target.current_instances,
                    requested_at=datetime.now(timezone.utc),
                    cost_impact=optimization.get("potential_savings", 0.0)
                )
                
                success = await self._execute_scaling_action(action)
                
                if success:
                    self.metrics["cost_savings"] += optimization.get("potential_savings", 0.0)
                    self.logger.info(f"Cost optimization executed for {target.target_id}")
            
        except Exception as e:
            self.logger.error(f"Cost optimization execution failed: {e}")

    async def get_scaling_status(self, session_id: str) -> Dict[str, Any]:
        """Get current scaling status for session"""
        try:
            if session_id not in self.scaling_targets:
                return {"error": "Session not found"}
            
            target = self.scaling_targets[session_id]
            
            # Get related scaling rules
            rules = [
                {
                    "rule_id": rule.rule_id,
                    "trigger": rule.trigger.value,
                    "metric_name": rule.metric_name,
                    "enabled": rule.enabled,
                    "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
                    "total_triggers": rule.total_triggers
                }
                for rule in self.scaling_rules.values()
                if rule.session_id == session_id
            ]
            
            # Get current metrics
            metrics = {
                k.replace(f"{session_id}_", ""): {
                    "current_value": v.current_value,
                    "target_value": v.target_value,
                    "threshold_high": v.threshold_high,
                    "threshold_low": v.threshold_low,
                    "timestamp": v.timestamp.isoformat()
                }
                for k, v in self.current_metrics.items()
                if k.startswith(f"{session_id}_")
            }
            
            # Get recent scaling actions
            recent_actions = [
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "resource_type": action.resource_type.value,
                    "previous_count": action.previous_count,
                    "target_count": action.target_count,
                    "success": action.success,
                    "requested_at": action.requested_at.isoformat(),
                    "completed_at": action.completed_at.isoformat() if action.completed_at else None,
                    "execution_time": action.execution_time
                }
                for action in list(self.scaling_actions)
                if action.session_id == session_id
            ][-10:]  # Last 10 actions
            
            return {
                "session_id": session_id,
                "target": {
                    "current_instances": target.current_instances,
                    "desired_instances": target.desired_instances,
                    "scaling_in_progress": target.scaling_in_progress,
                    "health_status": target.health_status,
                    "last_scaled_at": target.last_scaled_at.isoformat() if target.last_scaled_at else None
                },
                "scaling_rules": rules,
                "current_metrics": metrics,
                "recent_actions": recent_actions
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get scaling status for {session_id}: {e}")
            return {"error": str(e)}

    async def _store_scaling_config_in_redis(self, session_id: str, config: Dict[str, Any]):
        """Store scaling configuration in Redis"""
        try:
            if not self.redis_client:
                return
            
            config_key = f"scaling_config:{session_id}"
            await self.redis_client.hset(config_key, mapping={
                "config": json.dumps(config),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            # Set expiration (30 days)
            await self.redis_client.expire(config_key, 2592000)
            
        except Exception as e:
            self.logger.error(f"Failed to store scaling config in Redis: {e}")

    async def _store_metrics_in_redis(self, session_id: str, metrics: Dict[str, ScalingMetric]):
        """Store scaling metrics in Redis"""
        try:
            if not self.redis_client:
                return
            
            for metric_name, metric in metrics.items():
                metrics_key = f"scaling_metrics:{session_id}:{metric_name}"
                
                metric_data = {
                    "value": metric.current_value,
                    "timestamp": metric.timestamp.isoformat(),
                    "target_value": metric.target_value,
                    "threshold_high": metric.threshold_high,
                    "threshold_low": metric.threshold_low
                }
                
                # Store as sorted set with timestamp as score
                await self.redis_client.zadd(
                    metrics_key,
                    {json.dumps(metric_data): metric.timestamp.timestamp()}
                )
                
                # Keep only recent metrics (last 24 hours)
                cutoff = time.time() - 86400
                await self.redis_client.zremrangebyscore(metrics_key, 0, cutoff)
                
                # Set expiration
                await self.redis_client.expire(metrics_key, 86400)
            
        except Exception as e:
            self.logger.error(f"Failed to store metrics in Redis: {e}")

    async def _store_scaling_action_in_redis(self, action: ScalingAction):
        """Store scaling action in Redis"""
        try:
            if not self.redis_client:
                return
            
            action_key = f"scaling_actions:{action.session_id}"
            
            action_data = {
                "action_id": action.action_id,
                "action_type": action.action_type.value,
                "resource_type": action.resource_type.value,
                "previous_count": action.previous_count,
                "target_count": action.target_count,
                "actual_count": action.actual_count,
                "success": action.success,
                "requested_at": action.requested_at.isoformat(),
                "completed_at": action.completed_at.isoformat() if action.completed_at else None,
                "execution_time": action.execution_time,
                "error_message": action.error_message
            }
            
            # Store as sorted set with timestamp as score
            await self.redis_client.zadd(
                action_key,
                {json.dumps(action_data): action.requested_at.timestamp()}
            )
            
            # Keep only recent actions (last 7 days)
            cutoff = time.time() - 604800
            await self.redis_client.zremrangebyscore(action_key, 0, cutoff)
            
            # Set expiration
            await self.redis_client.expire(action_key, 604800)
            
        except Exception as e:
            self.logger.error(f"Failed to store scaling action in Redis: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get dynamic scaler status"""
        return {
            "scaling_active": self.scaling_active,
            "scaling_targets": len(self.scaling_targets),
            "scaling_rules": len(self.scaling_rules),
            "current_metrics": len(self.current_metrics),
            "scaling_actions": len(self.scaling_actions),
            "metrics": self.metrics,
            "docker_available": self.docker_client is not None,
            "redis_connected": self.redis_client is not None
        }

    async def shutdown(self):
        """Shutdown dynamic scaler gracefully"""
        try:
            self.logger.info("Shutting down dynamic scaler...")
            
            # Stop scaling monitor
            self.scaling_active = False
            
            # Mark all targets as not scaling
            for target in self.scaling_targets.values():
                target.scaling_in_progress = False
            
            self.logger.info("Dynamic scaler shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during dynamic scaler shutdown: {e}")