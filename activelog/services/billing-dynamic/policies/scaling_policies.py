"""
Automated Scaling Policies
Intelligent policies for automatic resource scaling based on usage patterns
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import redis
from decimal import Decimal

class PolicyType(Enum):
    THRESHOLD_BASED = "threshold_based"
    PREDICTIVE = "predictive"
    SCHEDULE_BASED = "schedule_based"
    COST_OPTIMIZED = "cost_optimized"
    HYBRID = "hybrid"

class MetricType(Enum):
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    RESPONSE_TIME = "response_time"
    QUEUE_LENGTH = "queue_length"
    ERROR_RATE = "error_rate"
    COST_PER_HOUR = "cost_per_hour"
    THROUGHPUT = "throughput"

class ScalingAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"

@dataclass
class PolicyCondition:
    """Individual condition within a policy"""
    metric_type: MetricType
    operator: str  # >, <, >=, <=, ==
    threshold: float
    duration_seconds: int  # How long condition must be true
    weight: float = 1.0  # Weight for multi-condition policies

@dataclass
class ScalingPolicy:
    """Automated scaling policy definition"""
    policy_id: str
    user_id: str
    policy_name: str
    policy_type: PolicyType
    
    # Target configuration
    session_id: Optional[str] = None
    service_type: Optional[str] = None
    
    # Scale up conditions and actions
    scale_up_conditions: List[PolicyCondition] = field(default_factory=list)
    scale_up_action: Dict[str, Any] = field(default_factory=dict)
    
    # Scale down conditions and actions
    scale_down_conditions: List[PolicyCondition] = field(default_factory=dict)
    scale_down_action: Dict[str, Any] = field(default_factory=dict)
    
    # Policy settings
    cooldown_period: int = 300  # 5 minutes
    min_instances: int = 1
    max_instances: int = 10
    scaling_factor: float = 1.0  # Multiplier for scaling actions
    
    # Cost constraints
    max_hourly_cost: Optional[float] = None
    cost_per_instance: float = 0.10
    
    # Scheduling (for schedule-based policies)
    schedule: Dict[str, Any] = field(default_factory=dict)
    
    # Policy status
    enabled: bool = True
    last_action_time: Optional[datetime] = None
    action_count: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""

@dataclass
class PolicyExecution:
    """Record of policy execution"""
    execution_id: str
    policy_id: str
    action_taken: ScalingAction
    triggered_conditions: List[str]
    
    # Before and after state
    instances_before: int
    instances_after: int
    
    # Metrics at execution time
    metrics_snapshot: Dict[str, float] = field(default_factory=dict)
    
    # Result
    success: bool = False
    error_message: Optional[str] = None
    
    # Timing
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Cost impact
    cost_impact: Optional[float] = None

class AutomatedScalingPolicies:
    """
    Engine for automated scaling policies with intelligent decision making
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Policy storage
        self.policies: Dict[str, ScalingPolicy] = {}
        self.policy_executions: List[PolicyExecution] = []
        
        # Metric collection
        self.current_metrics: Dict[str, Dict[str, float]] = {}
        self.metric_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # Policy engine state
        self.policy_engine_running = False
        
        # Policy templates
        self.policy_templates = self._initialize_policy_templates()
        
        # Performance metrics
        self.metrics = {
            "policies_evaluated": 0,
            "actions_taken": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "cost_savings": 0.0
        }
        
        # Configuration
        self.evaluation_interval = 60  # 1 minute
        self.metric_retention_hours = 24

    def _initialize_policy_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common policy templates"""
        return {
            "cpu_threshold": {
                "name": "CPU Threshold Scaling",
                "type": "threshold_based",
                "scale_up_conditions": [
                    {
                        "metric_type": "cpu_utilization",
                        "operator": ">=",
                        "threshold": 80.0,
                        "duration_seconds": 300
                    }
                ],
                "scale_down_conditions": [
                    {
                        "metric_type": "cpu_utilization",
                        "operator": "<=",
                        "threshold": 30.0,
                        "duration_seconds": 600
                    }
                ],
                "scale_up_action": {"increment": 1, "max_increment": 3},
                "scale_down_action": {"decrement": 1, "max_decrement": 2}
            },
            "response_time": {
                "name": "Response Time Scaling",
                "type": "threshold_based",
                "scale_up_conditions": [
                    {
                        "metric_type": "response_time",
                        "operator": ">=",
                        "threshold": 1000.0,  # 1 second
                        "duration_seconds": 180
                    }
                ],
                "scale_down_conditions": [
                    {
                        "metric_type": "response_time",
                        "operator": "<=",
                        "threshold": 200.0,  # 200ms
                        "duration_seconds": 900
                    }
                ]
            },
            "cost_optimized": {
                "name": "Cost-Optimized Scaling",
                "type": "cost_optimized",
                "scale_up_conditions": [
                    {
                        "metric_type": "cpu_utilization",
                        "operator": ">=",
                        "threshold": 85.0,
                        "duration_seconds": 300
                    },
                    {
                        "metric_type": "cost_per_hour",
                        "operator": "<=",
                        "threshold": 5.0,
                        "duration_seconds": 60
                    }
                ],
                "scale_down_conditions": [
                    {
                        "metric_type": "cpu_utilization",
                        "operator": "<=",
                        "threshold": 25.0,
                        "duration_seconds": 900
                    }
                ]
            },
            "predictive": {
                "name": "Predictive Scaling",
                "type": "predictive",
                "scale_up_conditions": [
                    {
                        "metric_type": "throughput",
                        "operator": ">=",
                        "threshold": 100.0,
                        "duration_seconds": 120
                    }
                ]
            },
            "schedule_based": {
                "name": "Business Hours Scaling",
                "type": "schedule_based",
                "schedule": {
                    "business_hours": {
                        "start_time": "09:00",
                        "end_time": "17:00",
                        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                        "min_instances": 3,
                        "max_instances": 10
                    },
                    "off_hours": {
                        "min_instances": 1,
                        "max_instances": 3
                    }
                }
            }
        }

    async def create_policy(self, policy_data: Dict[str, Any]) -> str:
        """Create new automated scaling policy"""
        try:
            user_id = policy_data["user_id"]
            policy_name = policy_data["policy_name"]
            
            # Generate policy ID
            policy_id = f"policy_{user_id}_{policy_name.replace(' ', '_').lower()}_{int(datetime.now().timestamp())}"
            
            # Create policy from template or custom definition
            if "template" in policy_data:
                template = self.policy_templates.get(policy_data["template"])
                if not template:
                    raise ValueError(f"Unknown policy template: {policy_data['template']}")
                
                policy = self._create_policy_from_template(policy_id, user_id, template, policy_data)
            else:
                policy = self._create_custom_policy(policy_id, user_id, policy_data)
            
            # Store policy
            self.policies[policy_id] = policy
            
            # Store in Redis
            if self.redis_client:
                await self._store_policy_in_redis(policy)
            
            self.logger.info(f"Created scaling policy {policy_id} for user {user_id}")
            
            return policy_id
            
        except Exception as e:
            self.logger.error(f"Failed to create policy: {e}")
            raise

    async def update_policy(self, policy_id: str, policy_data: Dict[str, Any]):
        """Update existing scaling policy"""
        try:
            if policy_id not in self.policies:
                raise ValueError(f"Policy {policy_id} not found")
            
            policy = self.policies[policy_id]
            
            # Update policy fields
            if "enabled" in policy_data:
                policy.enabled = policy_data["enabled"]
            
            if "min_instances" in policy_data:
                policy.min_instances = policy_data["min_instances"]
            
            if "max_instances" in policy_data:
                policy.max_instances = policy_data["max_instances"]
            
            if "cooldown_period" in policy_data:
                policy.cooldown_period = policy_data["cooldown_period"]
            
            if "max_hourly_cost" in policy_data:
                policy.max_hourly_cost = policy_data["max_hourly_cost"]
            
            if "scale_up_conditions" in policy_data:
                policy.scale_up_conditions = [
                    PolicyCondition(**condition) for condition in policy_data["scale_up_conditions"]
                ]
            
            if "scale_down_conditions" in policy_data:
                policy.scale_down_conditions = [
                    PolicyCondition(**condition) for condition in policy_data["scale_down_conditions"]
                ]
            
            policy.updated_at = datetime.now(timezone.utc)
            
            # Update in Redis
            if self.redis_client:
                await self._store_policy_in_redis(policy)
            
            self.logger.info(f"Updated scaling policy {policy_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update policy {policy_id}: {e}")
            raise

    async def delete_policy(self, policy_id: str):
        """Delete scaling policy"""
        try:
            if policy_id not in self.policies:
                raise ValueError(f"Policy {policy_id} not found")
            
            # Remove policy
            del self.policies[policy_id]
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.delete(f"scaling_policy:{policy_id}")
            
            self.logger.info(f"Deleted scaling policy {policy_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to delete policy {policy_id}: {e}")
            raise

    async def get_user_policies(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all policies for a user"""
        try:
            user_policies = [
                policy for policy in self.policies.values()
                if policy.user_id == user_id
            ]
            
            return [
                {
                    "policy_id": policy.policy_id,
                    "policy_name": policy.policy_name,
                    "policy_type": policy.policy_type.value,
                    "enabled": policy.enabled,
                    "min_instances": policy.min_instances,
                    "max_instances": policy.max_instances,
                    "session_id": policy.session_id,
                    "service_type": policy.service_type,
                    "last_action_time": policy.last_action_time.isoformat() if policy.last_action_time else None,
                    "action_count": policy.action_count,
                    "created_at": policy.created_at.isoformat(),
                    "description": policy.description
                }
                for policy in user_policies
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get user policies: {e}")
            return []

    async def start_policy_engine(self):
        """Start automated policy evaluation engine"""
        if self.policy_engine_running:
            return
        
        self.policy_engine_running = True
        self.logger.info("Starting automated scaling policy engine")
        
        try:
            # Start policy evaluation tasks
            engine_tasks = [
                asyncio.create_task(self._policy_evaluation_loop()),
                asyncio.create_task(self._metric_collection_loop()),
                asyncio.create_task(self._policy_cleanup_loop())
            ]
            
            # Wait for all tasks
            await asyncio.gather(*engine_tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            self.logger.info("Policy engine cancelled")
        except Exception as e:
            self.logger.error(f"Policy engine error: {e}")
        finally:
            self.policy_engine_running = False

    async def _policy_evaluation_loop(self):
        """Main policy evaluation loop"""
        try:
            while self.policy_engine_running:
                # Evaluate all active policies
                for policy_id, policy in self.policies.items():
                    if not policy.enabled:
                        continue
                    
                    try:
                        # Check cooldown period
                        if self._is_in_cooldown(policy):
                            continue
                        
                        # Evaluate policy
                        action = await self._evaluate_policy(policy)
                        
                        if action != ScalingAction.NO_ACTION:
                            await self._execute_policy_action(policy, action)
                        
                        self.metrics["policies_evaluated"] += 1
                    
                    except Exception as e:
                        self.logger.error(f"Failed to evaluate policy {policy_id}: {e}")
                
                # Wait for next evaluation cycle
                await asyncio.sleep(self.evaluation_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Policy evaluation loop error: {e}")

    async def _metric_collection_loop(self):
        """Collect metrics for policy evaluation"""
        try:
            while self.policy_engine_running:
                # Collect metrics for each active session/service
                active_targets = set()
                
                for policy in self.policies.values():
                    if policy.enabled and policy.session_id:
                        active_targets.add(policy.session_id)
                
                for target in active_targets:
                    try:
                        metrics = await self._collect_target_metrics(target)
                        self.current_metrics[target] = metrics
                        
                        # Store metric history
                        current_time = datetime.now(timezone.utc)
                        for metric_name, value in metrics.items():
                            history_key = f"{target}_{metric_name}"
                            if history_key not in self.metric_history:
                                self.metric_history[history_key] = []
                            
                            self.metric_history[history_key].append((current_time, value))
                            
                            # Limit history size
                            cutoff_time = current_time - timedelta(hours=self.metric_retention_hours)
                            self.metric_history[history_key] = [
                                (time, val) for time, val in self.metric_history[history_key]
                                if time > cutoff_time
                            ]
                    
                    except Exception as e:
                        self.logger.error(f"Failed to collect metrics for target {target}: {e}")
                
                # Wait 30 seconds before next collection
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Metric collection loop error: {e}")

    async def _policy_cleanup_loop(self):
        """Clean up old policy executions and metrics"""
        try:
            while self.policy_engine_running:
                current_time = datetime.now(timezone.utc)
                
                # Clean up old executions (keep last 1000)
                if len(self.policy_executions) > 1000:
                    self.policy_executions = self.policy_executions[-1000:]
                
                # Clean up old metric history
                cutoff_time = current_time - timedelta(hours=self.metric_retention_hours)
                cleaned_keys = 0
                
                for history_key in list(self.metric_history.keys()):
                    original_size = len(self.metric_history[history_key])
                    self.metric_history[history_key] = [
                        (time, val) for time, val in self.metric_history[history_key]
                        if time > cutoff_time
                    ]
                    
                    if len(self.metric_history[history_key]) < original_size:
                        cleaned_keys += 1
                
                if cleaned_keys > 0:
                    self.logger.debug(f"Cleaned metric history for {cleaned_keys} keys")
                
                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Policy cleanup loop error: {e}")

    def _create_policy_from_template(
        self,
        policy_id: str,
        user_id: str,
        template: Dict[str, Any],
        policy_data: Dict[str, Any]
    ) -> ScalingPolicy:
        """Create policy from template"""
        try:
            # Create conditions from template
            scale_up_conditions = []
            for condition_data in template.get("scale_up_conditions", []):
                condition = PolicyCondition(
                    metric_type=MetricType(condition_data["metric_type"]),
                    operator=condition_data["operator"],
                    threshold=condition_data["threshold"],
                    duration_seconds=condition_data["duration_seconds"],
                    weight=condition_data.get("weight", 1.0)
                )
                scale_up_conditions.append(condition)
            
            scale_down_conditions = []
            for condition_data in template.get("scale_down_conditions", []):
                condition = PolicyCondition(
                    metric_type=MetricType(condition_data["metric_type"]),
                    operator=condition_data["operator"],
                    threshold=condition_data["threshold"],
                    duration_seconds=condition_data["duration_seconds"],
                    weight=condition_data.get("weight", 1.0)
                )
                scale_down_conditions.append(condition)
            
            policy = ScalingPolicy(
                policy_id=policy_id,
                user_id=user_id,
                policy_name=template["name"],
                policy_type=PolicyType(template["type"]),
                session_id=policy_data.get("session_id"),
                service_type=policy_data.get("service_type"),
                scale_up_conditions=scale_up_conditions,
                scale_down_conditions=scale_down_conditions,
                scale_up_action=template.get("scale_up_action", {}),
                scale_down_action=template.get("scale_down_action", {}),
                cooldown_period=policy_data.get("cooldown_period", 300),
                min_instances=policy_data.get("min_instances", 1),
                max_instances=policy_data.get("max_instances", 10),
                max_hourly_cost=policy_data.get("max_hourly_cost"),
                schedule=template.get("schedule", {}),
                description=policy_data.get("description", template["name"])
            )
            
            return policy
            
        except Exception as e:
            self.logger.error(f"Failed to create policy from template: {e}")
            raise

    def _create_custom_policy(self, policy_id: str, user_id: str, policy_data: Dict[str, Any]) -> ScalingPolicy:
        """Create custom policy from data"""
        try:
            policy = ScalingPolicy(
                policy_id=policy_id,
                user_id=user_id,
                policy_name=policy_data["policy_name"],
                policy_type=PolicyType(policy_data.get("policy_type", "threshold_based")),
                session_id=policy_data.get("session_id"),
                service_type=policy_data.get("service_type"),
                cooldown_period=policy_data.get("cooldown_period", 300),
                min_instances=policy_data.get("min_instances", 1),
                max_instances=policy_data.get("max_instances", 10),
                max_hourly_cost=policy_data.get("max_hourly_cost"),
                description=policy_data.get("description", "")
            )
            
            # Add conditions if provided
            if "scale_up_conditions" in policy_data:
                policy.scale_up_conditions = [
                    PolicyCondition(
                        metric_type=MetricType(condition["metric_type"]),
                        operator=condition["operator"],
                        threshold=condition["threshold"],
                        duration_seconds=condition["duration_seconds"],
                        weight=condition.get("weight", 1.0)
                    )
                    for condition in policy_data["scale_up_conditions"]
                ]
            
            if "scale_down_conditions" in policy_data:
                policy.scale_down_conditions = [
                    PolicyCondition(
                        metric_type=MetricType(condition["metric_type"]),
                        operator=condition["operator"],
                        threshold=condition["threshold"],
                        duration_seconds=condition["duration_seconds"],
                        weight=condition.get("weight", 1.0)
                    )
                    for condition in policy_data["scale_down_conditions"]
                ]
            
            return policy
            
        except Exception as e:
            self.logger.error(f"Failed to create custom policy: {e}")
            raise

    def _is_in_cooldown(self, policy: ScalingPolicy) -> bool:
        """Check if policy is in cooldown period"""
        if not policy.last_action_time:
            return False
        
        time_since_last_action = (datetime.now(timezone.utc) - policy.last_action_time).total_seconds()
        return time_since_last_action < policy.cooldown_period

    async def _evaluate_policy(self, policy: ScalingPolicy) -> ScalingAction:
        """Evaluate policy and determine scaling action"""
        try:
            if policy.policy_type == PolicyType.THRESHOLD_BASED:
                return await self._evaluate_threshold_policy(policy)
            elif policy.policy_type == PolicyType.SCHEDULE_BASED:
                return await self._evaluate_schedule_policy(policy)
            elif policy.policy_type == PolicyType.COST_OPTIMIZED:
                return await self._evaluate_cost_optimized_policy(policy)
            elif policy.policy_type == PolicyType.PREDICTIVE:
                return await self._evaluate_predictive_policy(policy)
            elif policy.policy_type == PolicyType.HYBRID:
                return await self._evaluate_hybrid_policy(policy)
            else:
                return ScalingAction.NO_ACTION
            
        except Exception as e:
            self.logger.error(f"Policy evaluation failed: {e}")
            return ScalingAction.NO_ACTION

    async def _evaluate_threshold_policy(self, policy: ScalingPolicy) -> ScalingAction:
        """Evaluate threshold-based policy"""
        try:
            target_key = policy.session_id or f"user_{policy.user_id}"
            current_metrics = self.current_metrics.get(target_key, {})
            
            if not current_metrics:
                return ScalingAction.NO_ACTION
            
            # Check scale up conditions
            if await self._conditions_met(policy.scale_up_conditions, target_key, current_metrics):
                return ScalingAction.SCALE_UP
            
            # Check scale down conditions
            if await self._conditions_met(policy.scale_down_conditions, target_key, current_metrics):
                return ScalingAction.SCALE_DOWN
            
            return ScalingAction.NO_ACTION
            
        except Exception as e:
            self.logger.error(f"Threshold policy evaluation failed: {e}")
            return ScalingAction.NO_ACTION

    async def _evaluate_schedule_policy(self, policy: ScalingPolicy) -> ScalingAction:
        """Evaluate schedule-based policy"""
        try:
            if not policy.schedule:
                return ScalingAction.NO_ACTION
            
            current_time = datetime.now(timezone.utc)
            current_day = current_time.strftime("%A").lower()
            current_hour_minute = current_time.strftime("%H:%M")
            
            # Get current instance count
            current_instances = await self._get_current_instances(policy)
            
            # Check business hours schedule
            business_hours = policy.schedule.get("business_hours", {})
            if business_hours and current_day in business_hours.get("days", []):
                start_time = business_hours.get("start_time", "09:00")
                end_time = business_hours.get("end_time", "17:00")
                
                if start_time <= current_hour_minute <= end_time:
                    # During business hours
                    target_min = business_hours.get("min_instances", policy.min_instances)
                    
                    if current_instances < target_min:
                        return ScalingAction.SCALE_UP
            
            # Check off hours
            off_hours = policy.schedule.get("off_hours", {})
            if off_hours:
                target_min = off_hours.get("min_instances", policy.min_instances)
                
                if current_instances > target_min:
                    return ScalingAction.SCALE_DOWN
            
            return ScalingAction.NO_ACTION
            
        except Exception as e:
            self.logger.error(f"Schedule policy evaluation failed: {e}")
            return ScalingAction.NO_ACTION

    async def _evaluate_cost_optimized_policy(self, policy: ScalingPolicy) -> ScalingAction:
        """Evaluate cost-optimized policy"""
        try:
            # First check cost constraints
            current_instances = await self._get_current_instances(policy)
            current_cost = current_instances * policy.cost_per_instance
            
            if policy.max_hourly_cost and current_cost >= policy.max_hourly_cost:
                # Cost limit reached, only allow scale down
                target_key = policy.session_id or f"user_{policy.user_id}"
                current_metrics = self.current_metrics.get(target_key, {})
                
                if current_metrics.get("cpu_utilization", 0) < 40:  # Very low utilization
                    return ScalingAction.SCALE_DOWN
            
            # Otherwise evaluate like threshold policy but with cost awareness
            return await self._evaluate_threshold_policy(policy)
            
        except Exception as e:
            self.logger.error(f"Cost-optimized policy evaluation failed: {e}")
            return ScalingAction.NO_ACTION

    async def _evaluate_predictive_policy(self, policy: ScalingPolicy) -> ScalingAction:
        """Evaluate predictive policy"""
        try:
            target_key = policy.session_id or f"user_{policy.user_id}"
            
            # Get metric history for prediction
            history_key = f"{target_key}_cpu_utilization"
            if history_key not in self.metric_history or len(self.metric_history[history_key]) < 10:
                # Insufficient data for prediction, fall back to threshold
                return await self._evaluate_threshold_policy(policy)
            
            # Simple trend-based prediction
            recent_metrics = self.metric_history[history_key][-10:]  # Last 10 data points
            values = [value for _, value in recent_metrics]
            
            # Calculate trend
            if len(values) >= 5:
                recent_avg = sum(values[-5:]) / 5
                older_avg = sum(values[-10:-5]) / 5 if len(values) >= 10 else recent_avg
                
                trend = recent_avg - older_avg
                
                # Predict scaling need based on trend
                if trend > 10:  # Increasing trend
                    if recent_avg > 60:  # Already moderate usage
                        return ScalingAction.SCALE_UP
                elif trend < -10:  # Decreasing trend
                    if recent_avg < 30:  # Low usage
                        return ScalingAction.SCALE_DOWN
            
            return ScalingAction.NO_ACTION
            
        except Exception as e:
            self.logger.error(f"Predictive policy evaluation failed: {e}")
            return ScalingAction.NO_ACTION

    async def _evaluate_hybrid_policy(self, policy: ScalingPolicy) -> ScalingAction:
        """Evaluate hybrid policy (combines multiple approaches)"""
        try:
            # Get results from different policy types
            threshold_result = await self._evaluate_threshold_policy(policy)
            cost_result = await self._evaluate_cost_optimized_policy(policy)
            
            # Simple voting system
            results = [threshold_result, cost_result]
            scale_up_votes = results.count(ScalingAction.SCALE_UP)
            scale_down_votes = results.count(ScalingAction.SCALE_DOWN)
            
            if scale_up_votes > scale_down_votes:
                return ScalingAction.SCALE_UP
            elif scale_down_votes > scale_up_votes:
                return ScalingAction.SCALE_DOWN
            else:
                return ScalingAction.NO_ACTION
            
        except Exception as e:
            self.logger.error(f"Hybrid policy evaluation failed: {e}")
            return ScalingAction.NO_ACTION

    async def _conditions_met(
        self,
        conditions: List[PolicyCondition],
        target_key: str,
        current_metrics: Dict[str, float]
    ) -> bool:
        """Check if policy conditions are met"""
        try:
            if not conditions:
                return False
            
            conditions_met = []
            
            for condition in conditions:
                metric_value = current_metrics.get(condition.metric_type.value, 0)
                
                # Check if condition duration requirement is met
                if await self._condition_duration_met(condition, target_key, metric_value):
                    condition_met = self._evaluate_condition(condition, metric_value)
                    conditions_met.append(condition_met)
                else:
                    conditions_met.append(False)
            
            # For now, require all conditions to be met (AND logic)
            return all(conditions_met)
            
        except Exception as e:
            self.logger.error(f"Condition evaluation failed: {e}")
            return False

    async def _condition_duration_met(
        self,
        condition: PolicyCondition,
        target_key: str,
        current_value: float
    ) -> bool:
        """Check if condition has been true for required duration"""
        try:
            history_key = f"{target_key}_{condition.metric_type.value}"
            
            if history_key not in self.metric_history:
                return False
            
            # Check history for required duration
            current_time = datetime.now(timezone.utc)
            required_start_time = current_time - timedelta(seconds=condition.duration_seconds)
            
            # Get metrics within duration window
            relevant_metrics = [
                value for time, value in self.metric_history[history_key]
                if time >= required_start_time
            ]
            
            if len(relevant_metrics) < 2:  # Need at least 2 data points
                return False
            
            # Check if condition was consistently met during duration
            condition_met_count = sum(
                1 for value in relevant_metrics
                if self._evaluate_condition(condition, value)
            )
            
            # Require 80% of measurements to meet condition
            return (condition_met_count / len(relevant_metrics)) >= 0.8
            
        except Exception as e:
            self.logger.error(f"Duration check failed: {e}")
            return False

    def _evaluate_condition(self, condition: PolicyCondition, metric_value: float) -> bool:
        """Evaluate individual condition"""
        try:
            if condition.operator == ">":
                return metric_value > condition.threshold
            elif condition.operator == ">=":
                return metric_value >= condition.threshold
            elif condition.operator == "<":
                return metric_value < condition.threshold
            elif condition.operator == "<=":
                return metric_value <= condition.threshold
            elif condition.operator == "==":
                return abs(metric_value - condition.threshold) < 0.001
            else:
                return False
            
        except Exception:
            return False

    async def _execute_policy_action(self, policy: ScalingPolicy, action: ScalingAction):
        """Execute scaling action for policy"""
        try:
            current_instances = await self._get_current_instances(policy)
            target_instances = current_instances
            
            if action == ScalingAction.SCALE_UP:
                increment = policy.scale_up_action.get("increment", 1)
                max_increment = policy.scale_up_action.get("max_increment", increment)
                actual_increment = min(increment, max_increment)
                target_instances = min(current_instances + actual_increment, policy.max_instances)
            
            elif action == ScalingAction.SCALE_DOWN:
                decrement = policy.scale_down_action.get("decrement", 1)
                max_decrement = policy.scale_down_action.get("max_decrement", decrement)
                actual_decrement = min(decrement, max_decrement)
                target_instances = max(current_instances - actual_decrement, policy.min_instances)
            
            # Only proceed if there's an actual change
            if target_instances == current_instances:
                return
            
            # Record execution
            execution = PolicyExecution(
                execution_id=f"exec_{policy.policy_id}_{int(datetime.now().timestamp())}",
                policy_id=policy.policy_id,
                action_taken=action,
                triggered_conditions=[],  # Would populate with specific conditions
                instances_before=current_instances,
                instances_after=target_instances,
                metrics_snapshot=self.current_metrics.get(
                    policy.session_id or f"user_{policy.user_id}", {}
                ).copy()
            )
            
            # Execute scaling (this would integrate with actual scaling system)
            success = await self._perform_scaling_action(policy, target_instances)
            
            execution.success = success
            if not success:
                execution.error_message = "Scaling action failed"
            
            # Calculate cost impact
            cost_change = (target_instances - current_instances) * policy.cost_per_instance
            execution.cost_impact = cost_change
            
            # Update policy state
            policy.last_action_time = datetime.now(timezone.utc)
            policy.action_count += 1
            
            # Store execution
            self.policy_executions.append(execution)
            
            # Update metrics
            self.metrics["actions_taken"] += 1
            if success:
                self.metrics["successful_actions"] += 1
                if cost_change < 0:  # Cost reduction
                    self.metrics["cost_savings"] += abs(cost_change)
            else:
                self.metrics["failed_actions"] += 1
            
            self.logger.info(f"Executed {action.value} for policy {policy.policy_id}: {current_instances} -> {target_instances}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute policy action: {e}")

    async def _collect_target_metrics(self, target: str) -> Dict[str, float]:
        """Collect metrics for target (placeholder)"""
        try:
            # This would integrate with actual monitoring system
            # For now, return simulated metrics
            import random
            
            metrics = {
                "cpu_utilization": random.uniform(20, 90),
                "memory_utilization": random.uniform(30, 85),
                "response_time": random.uniform(100, 2000),
                "queue_length": random.uniform(0, 20),
                "error_rate": random.uniform(0, 5),
                "throughput": random.uniform(10, 200)
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Metric collection failed for {target}: {e}")
            return {}

    async def _get_current_instances(self, policy: ScalingPolicy) -> int:
        """Get current instance count for policy target"""
        try:
            # This would integrate with actual scaling system
            # For now, return simulated count
            return 2  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Failed to get current instances: {e}")
            return 1

    async def _perform_scaling_action(self, policy: ScalingPolicy, target_instances: int) -> bool:
        """Perform actual scaling action"""
        try:
            # This would integrate with actual scaling system (Docker, K8s, cloud APIs)
            self.logger.info(f"Simulating scaling to {target_instances} instances for policy {policy.policy_id}")
            
            # Simulate success/failure
            return True  # Always succeed for simulation
            
        except Exception as e:
            self.logger.error(f"Scaling action failed: {e}")
            return False

    async def _store_policy_in_redis(self, policy: ScalingPolicy):
        """Store policy in Redis"""
        try:
            if not self.redis_client:
                return
            
            policy_key = f"scaling_policy:{policy.policy_id}"
            
            policy_data = {
                "policy_id": policy.policy_id,
                "user_id": policy.user_id,
                "policy_name": policy.policy_name,
                "policy_type": policy.policy_type.value,
                "session_id": policy.session_id or "",
                "service_type": policy.service_type or "",
                "enabled": str(policy.enabled),
                "min_instances": str(policy.min_instances),
                "max_instances": str(policy.max_instances),
                "cooldown_period": str(policy.cooldown_period),
                "max_hourly_cost": str(policy.max_hourly_cost) if policy.max_hourly_cost else "",
                "created_at": policy.created_at.isoformat(),
                "updated_at": policy.updated_at.isoformat(),
                "description": policy.description
            }
            
            await self.redis_client.hset(policy_key, mapping=policy_data)
            await self.redis_client.expire(policy_key, 2592000)  # 30 days
            
            # Add to user's policies set
            user_policies_key = f"user_scaling_policies:{policy.user_id}"
            await self.redis_client.sadd(user_policies_key, policy.policy_id)
            await self.redis_client.expire(user_policies_key, 2592000)
            
        except Exception as e:
            self.logger.error(f"Failed to store policy in Redis: {e}")

    async def get_policy_executions(self, policy_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a policy"""
        try:
            policy_executions = [
                execution for execution in self.policy_executions
                if execution.policy_id == policy_id
            ]
            
            # Sort by execution time (newest first)
            policy_executions.sort(key=lambda e: e.executed_at, reverse=True)
            
            return [
                {
                    "execution_id": execution.execution_id,
                    "action_taken": execution.action_taken.value,
                    "instances_before": execution.instances_before,
                    "instances_after": execution.instances_after,
                    "success": execution.success,
                    "cost_impact": execution.cost_impact,
                    "executed_at": execution.executed_at.isoformat(),
                    "metrics_snapshot": execution.metrics_snapshot
                }
                for execution in policy_executions[:limit]
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get policy executions: {e}")
            return []

    async def get_policy_templates(self) -> Dict[str, Any]:
        """Get available policy templates"""
        return {
            "templates": [
                {
                    "template_id": template_id,
                    "name": template["name"],
                    "type": template["type"],
                    "description": f"Template for {template['name'].lower()}"
                }
                for template_id, template in self.policy_templates.items()
            ]
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get scaling policies engine status"""
        return {
            "policy_engine_running": self.policy_engine_running,
            "total_policies": len(self.policies),
            "active_policies": sum(1 for p in self.policies.values() if p.enabled),
            "policy_executions": len(self.policy_executions),
            "metrics": self.metrics,
            "current_targets": len(self.current_metrics),
            "metric_history_keys": len(self.metric_history),
            "redis_connected": self.redis_client is not None
        }

    async def shutdown(self):
        """Shutdown scaling policies engine"""
        try:
            self.logger.info("Shutting down automated scaling policies engine...")
            
            # Stop policy engine
            self.policy_engine_running = False
            
            # Store final policy states
            for policy in self.policies.values():
                if self.redis_client:
                    await self._store_policy_in_redis(policy)
            
            self.logger.info("Scaling policies engine shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during scaling policies engine shutdown: {e}")