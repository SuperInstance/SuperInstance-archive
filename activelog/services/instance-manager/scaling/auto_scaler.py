"""
Auto Scaler
Intelligent workload-based scaling with predictive capabilities
"""

import logging
import boto3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics
import asyncio
from dataclasses import dataclass

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class ScalingAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down" 
    NO_ACTION = "no_action"

class ScalingTrigger(Enum):
    CPU_HIGH = "cpu_high"
    CPU_LOW = "cpu_low"
    MEMORY_HIGH = "memory_high"
    MEMORY_LOW = "memory_low"
    NETWORK_HIGH = "network_high"
    PREDICTIVE = "predictive"
    SCHEDULED = "scheduled"
    MANUAL = "manual"

@dataclass
class ScalingRule:
    name: str
    metric: str
    threshold_high: float
    threshold_low: float
    evaluation_periods: int
    cooldown_minutes: int
    scale_up_action: Dict[str, Any]
    scale_down_action: Dict[str, Any]
    enabled: bool = True

@dataclass
class ScalingEvent:
    timestamp: datetime
    instance_id: str
    action: ScalingAction
    trigger: ScalingTrigger
    old_instance_type: str
    new_instance_type: str
    metric_value: float
    threshold: float
    success: bool
    message: str

class AutoScaler:
    """Intelligent auto-scaling based on workload patterns"""
    
    def __init__(self, ec2_client, cloudwatch_client):
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client
        self.scaling_rules = self._initialize_default_rules()
        self.scaling_history: List[ScalingEvent] = []
        self.cooldown_tracker = {}  # Track cooldown periods
        
        # Instance type performance mapping
        self.instance_types = self._load_instance_type_mapping()
    
    def _initialize_default_rules(self) -> List[ScalingRule]:
        """Initialize default scaling rules"""
        return [
            ScalingRule(
                name="CPU High Utilization",
                metric="CPUUtilization",
                threshold_high=80.0,
                threshold_low=20.0,
                evaluation_periods=2,
                cooldown_minutes=15,
                scale_up_action={"type": "resize", "direction": "up"},
                scale_down_action={"type": "resize", "direction": "down"}
            ),
            ScalingRule(
                name="Memory High Utilization", 
                metric="MemoryUtilization",
                threshold_high=85.0,
                threshold_low=25.0,
                evaluation_periods=2,
                cooldown_minutes=15,
                scale_up_action={"type": "resize", "direction": "up"},
                scale_down_action={"type": "resize", "direction": "down"}
            ),
            ScalingRule(
                name="Network High Usage",
                metric="NetworkPacketsIn",
                threshold_high=1000000,  # 1M packets
                threshold_low=100000,    # 100K packets
                evaluation_periods=3,
                cooldown_minutes=20,
                scale_up_action={"type": "resize", "direction": "up"},
                scale_down_action={"type": "resize", "direction": "down"}
            )
        ]
    
    def _load_instance_type_mapping(self) -> Dict[str, Any]:
        """Load instance type performance and cost mapping"""
        return {
            # T3 instances
            "t3.nano": {"vcpu": 2, "memory": 0.5, "network": "up_to_5", "cost_factor": 1, "family": "t3"},
            "t3.micro": {"vcpu": 2, "memory": 1, "network": "up_to_5", "cost_factor": 2, "family": "t3"},
            "t3.small": {"vcpu": 2, "memory": 2, "network": "up_to_5", "cost_factor": 4, "family": "t3"},
            "t3.medium": {"vcpu": 2, "memory": 4, "network": "up_to_5", "cost_factor": 8, "family": "t3"},
            "t3.large": {"vcpu": 2, "memory": 8, "network": "up_to_5", "cost_factor": 16, "family": "t3"},
            "t3.xlarge": {"vcpu": 4, "memory": 16, "network": "up_to_5", "cost_factor": 32, "family": "t3"},
            "t3.2xlarge": {"vcpu": 8, "memory": 32, "network": "up_to_5", "cost_factor": 64, "family": "t3"},
            
            # M5 instances
            "m5.large": {"vcpu": 2, "memory": 8, "network": "up_to_10", "cost_factor": 20, "family": "m5"},
            "m5.xlarge": {"vcpu": 4, "memory": 16, "network": "up_to_10", "cost_factor": 40, "family": "m5"},
            "m5.2xlarge": {"vcpu": 8, "memory": 32, "network": "up_to_10", "cost_factor": 80, "family": "m5"},
            "m5.4xlarge": {"vcpu": 16, "memory": 64, "network": "up_to_10", "cost_factor": 160, "family": "m5"},
            
            # C5 instances (compute optimized)
            "c5.large": {"vcpu": 2, "memory": 4, "network": "up_to_10", "cost_factor": 18, "family": "c5"},
            "c5.xlarge": {"vcpu": 4, "memory": 8, "network": "up_to_10", "cost_factor": 36, "family": "c5"},
            "c5.2xlarge": {"vcpu": 8, "memory": 16, "network": "up_to_10", "cost_factor": 72, "family": "c5"},
            
            # R5 instances (memory optimized)
            "r5.large": {"vcpu": 2, "memory": 16, "network": "up_to_10", "cost_factor": 25, "family": "r5"},
            "r5.xlarge": {"vcpu": 4, "memory": 32, "network": "up_to_10", "cost_factor": 50, "family": "r5"},
            "r5.2xlarge": {"vcpu": 8, "memory": 64, "network": "up_to_10", "cost_factor": 100, "family": "r5"},
        }
    
    async def check_scaling_needs(self, instance_ids: List[str] = None):
        """Check if any instances need scaling"""
        try:
            if not instance_ids:
                # Get all running instances
                response = self.ec2.describe_instances(
                    Filters=[
                        {'Name': 'instance-state-name', 'Values': ['running']},
                        {'Name': 'tag:AutoScaling', 'Values': ['enabled']}
                    ]
                )
                
                instance_ids = []
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        instance_ids.append(instance['InstanceId'])
            
            scaling_decisions = []
            
            for instance_id in instance_ids:
                try:
                    decision = await self._evaluate_instance_scaling(instance_id)
                    if decision['action'] != ScalingAction.NO_ACTION:
                        scaling_decisions.append(decision)
                except Exception as e:
                    logger.error(f"Failed to evaluate scaling for {instance_id}: {e}")
            
            # Execute scaling decisions
            for decision in scaling_decisions:
                await self._execute_scaling_decision(decision)
                
        except Exception as e:
            logger.error(f"Failed to check scaling needs: {e}")
    
    async def _evaluate_instance_scaling(self, instance_id: str) -> Dict[str, Any]:
        """Evaluate scaling needs for a single instance"""
        try:
            # Check cooldown period
            if self._is_in_cooldown(instance_id):
                return {
                    'instance_id': instance_id,
                    'action': ScalingAction.NO_ACTION,
                    'reason': 'In cooldown period'
                }
            
            # Get current metrics
            current_metrics = await self._get_current_metrics(instance_id)
            
            # Get instance information
            instance_info = await self._get_instance_info(instance_id)
            current_type = instance_info['instance_type']
            
            # Evaluate each scaling rule
            for rule in self.scaling_rules:
                if not rule.enabled:
                    continue
                
                metric_value = current_metrics.get(rule.metric, 0)
                
                # Check for scale up condition
                if metric_value > rule.threshold_high:
                    # Verify condition over evaluation periods
                    if await self._verify_condition(instance_id, rule.metric, 
                                                  rule.threshold_high, rule.evaluation_periods, 'above'):
                        
                        next_type = self._get_next_instance_type(current_type, 'up')
                        if next_type and next_type != current_type:
                            return {
                                'instance_id': instance_id,
                                'action': ScalingAction.SCALE_UP,
                                'trigger': ScalingTrigger(f"{rule.metric.lower()}_high"),
                                'current_type': current_type,
                                'target_type': next_type,
                                'metric_value': metric_value,
                                'threshold': rule.threshold_high,
                                'rule': rule.name
                            }
                
                # Check for scale down condition
                elif metric_value < rule.threshold_low:
                    if await self._verify_condition(instance_id, rule.metric, 
                                                  rule.threshold_low, rule.evaluation_periods, 'below'):
                        
                        next_type = self._get_next_instance_type(current_type, 'down')
                        if next_type and next_type != current_type:
                            return {
                                'instance_id': instance_id,
                                'action': ScalingAction.SCALE_DOWN,
                                'trigger': ScalingTrigger(f"{rule.metric.lower()}_low"),
                                'current_type': current_type,
                                'target_type': next_type,
                                'metric_value': metric_value,
                                'threshold': rule.threshold_low,
                                'rule': rule.name
                            }
            
            return {
                'instance_id': instance_id,
                'action': ScalingAction.NO_ACTION,
                'reason': 'No scaling conditions met'
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate scaling for {instance_id}: {e}")
            return {
                'instance_id': instance_id,
                'action': ScalingAction.NO_ACTION,
                'reason': f'Evaluation error: {str(e)}'
            }
    
    def _is_in_cooldown(self, instance_id: str) -> bool:
        """Check if instance is in cooldown period"""
        if instance_id not in self.cooldown_tracker:
            return False
        
        last_scaling = self.cooldown_tracker[instance_id]
        cooldown_end = last_scaling + timedelta(minutes=15)  # Default cooldown
        
        return datetime.utcnow() < cooldown_end
    
    async def _get_current_metrics(self, instance_id: str) -> Dict[str, float]:
        """Get current metrics for an instance"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)  # Last 10 minutes
            
            metrics = {}
            metric_names = ['CPUUtilization', 'NetworkIn', 'NetworkOut', 'DiskReadBytes', 'DiskWriteBytes']
            
            for metric_name in metric_names:
                try:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName=metric_name,
                        Dimensions=[
                            {
                                'Name': 'InstanceId',
                                'Value': instance_id
                            }
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=300,  # 5 minute periods
                        Statistics=['Average']
                    )
                    
                    if response['Datapoints']:
                        # Get the latest datapoint
                        latest = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                        metrics[metric_name] = latest['Average']
                    else:
                        metrics[metric_name] = 0
                        
                except Exception as e:
                    logger.warning(f"Failed to get {metric_name} for {instance_id}: {e}")
                    metrics[metric_name] = 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get current metrics for {instance_id}: {e}")
            return {}
    
    async def _get_instance_info(self, instance_id: str) -> Dict[str, Any]:
        """Get instance information"""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            
            return {
                'instance_id': instance_id,
                'instance_type': instance['InstanceType'],
                'state': instance['State']['Name'],
                'availability_zone': instance['Placement']['AvailabilityZone'],
                'vpc_id': instance.get('VpcId'),
                'subnet_id': instance.get('SubnetId')
            }
            
        except Exception as e:
            logger.error(f"Failed to get instance info for {instance_id}: {e}")
            raise
    
    async def _verify_condition(self, instance_id: str, metric_name: str, 
                              threshold: float, evaluation_periods: int, 
                              condition: str) -> bool:
        """Verify that a condition has been met for the required evaluation periods"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=evaluation_periods * 5)  # 5 min per period
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName=metric_name,
                Dimensions=[
                    {
                        'Name': 'InstanceId',
                        'Value': instance_id
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5 minute periods
                Statistics=['Average']
            )
            
            if len(response['Datapoints']) < evaluation_periods:
                return False  # Not enough data
            
            # Sort by timestamp and take the most recent periods
            sorted_datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
            recent_datapoints = sorted_datapoints[-evaluation_periods:]
            
            # Check if all recent periods meet the condition
            for datapoint in recent_datapoints:
                value = datapoint['Average']
                if condition == 'above' and value <= threshold:
                    return False
                elif condition == 'below' and value >= threshold:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify condition for {instance_id}: {e}")
            return False
    
    def _get_next_instance_type(self, current_type: str, direction: str) -> Optional[str]:
        """Get the next instance type for scaling up or down"""
        if current_type not in self.instance_types:
            return None
        
        current_info = self.instance_types[current_type]
        family = current_info['family']
        current_cost = current_info['cost_factor']
        
        # Get all instances in the same family
        family_instances = {
            itype: info for itype, info in self.instance_types.items()
            if info['family'] == family
        }
        
        if direction == 'up':
            # Find next larger instance type
            candidates = [
                itype for itype, info in family_instances.items()
                if info['cost_factor'] > current_cost
            ]
            if candidates:
                # Return the smallest upgrade
                return min(candidates, key=lambda x: family_instances[x]['cost_factor'])
        
        elif direction == 'down':
            # Find next smaller instance type
            candidates = [
                itype for itype, info in family_instances.items()
                if info['cost_factor'] < current_cost
            ]
            if candidates:
                # Return the largest downgrade
                return max(candidates, key=lambda x: family_instances[x]['cost_factor'])
        
        return None
    
    async def _execute_scaling_decision(self, decision: Dict[str, Any]):
        """Execute a scaling decision"""
        try:
            instance_id = decision['instance_id']
            action = decision['action']
            target_type = decision['target_type']
            
            logger.info(f"Executing scaling decision: {instance_id} -> {target_type}")
            
            # Stop the instance
            logger.info(f"Stopping instance {instance_id} for scaling")
            self.ec2.stop_instances(InstanceIds=[instance_id])
            
            # Wait for instance to stop
            waiter = self.ec2.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[instance_id])
            
            # Change instance type
            logger.info(f"Changing instance type to {target_type}")
            self.ec2.modify_instance_attribute(
                InstanceId=instance_id,
                InstanceType={'Value': target_type}
            )
            
            # Start the instance
            logger.info(f"Starting instance {instance_id}")
            self.ec2.start_instances(InstanceIds=[instance_id])
            
            # Record scaling event
            scaling_event = ScalingEvent(
                timestamp=datetime.utcnow(),
                instance_id=instance_id,
                action=action,
                trigger=decision['trigger'],
                old_instance_type=decision['current_type'],
                new_instance_type=target_type,
                metric_value=decision['metric_value'],
                threshold=decision['threshold'],
                success=True,
                message=f"Successfully scaled {action.value} from {decision['current_type']} to {target_type}"
            )
            
            self.scaling_history.append(scaling_event)
            
            # Set cooldown period
            self.cooldown_tracker[instance_id] = datetime.utcnow()
            
            # Update instance tags
            self.ec2.create_tags(
                Resources=[instance_id],
                Tags=[
                    {
                        'Key': 'LastAutoScale',
                        'Value': datetime.utcnow().isoformat()
                    },
                    {
                        'Key': 'LastScaleAction',
                        'Value': action.value
                    },
                    {
                        'Key': 'PreviousInstanceType',
                        'Value': decision['current_type']
                    }
                ]
            )
            
            logger.info(f"Successfully executed scaling for {instance_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute scaling decision for {decision['instance_id']}: {e}")
            
            # Record failed scaling event
            scaling_event = ScalingEvent(
                timestamp=datetime.utcnow(),
                instance_id=decision['instance_id'],
                action=decision['action'],
                trigger=decision['trigger'],
                old_instance_type=decision['current_type'],
                new_instance_type=decision['target_type'],
                metric_value=decision['metric_value'],
                threshold=decision['threshold'],
                success=False,
                message=f"Failed to scale: {str(e)}"
            )
            
            self.scaling_history.append(scaling_event)
    
    async def predict_scaling_needs(self, instance_id: str, 
                                  forecast_hours: int = 24) -> Dict[str, Any]:
        """Predict future scaling needs based on historical patterns"""
        try:
            # Get historical metrics
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)  # Look back 7 days
            
            historical_data = {}
            metric_names = ['CPUUtilization', 'NetworkIn', 'NetworkOut']
            
            for metric_name in metric_names:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName=metric_name,
                    Dimensions=[
                        {
                            'Name': 'InstanceId',
                            'Value': instance_id
                        }
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1 hour periods
                    Statistics=['Average']
                )
                
                historical_data[metric_name] = {
                    dp['Timestamp']: dp['Average']
                    for dp in response['Datapoints']
                }
            
            # Analyze patterns and predict scaling needs
            predictions = self._analyze_scaling_patterns(historical_data, forecast_hours)
            
            return {
                'instance_id': instance_id,
                'forecast_hours': forecast_hours,
                'predictions': predictions,
                'confidence': 0.7,  # Simple model confidence
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to predict scaling needs for {instance_id}: {e}")
            raise
    
    def _analyze_scaling_patterns(self, historical_data: Dict[str, Dict], 
                                forecast_hours: int) -> List[Dict[str, Any]]:
        """Analyze historical data to predict scaling patterns"""
        predictions = []
        
        try:
            # Group CPU data by hour of day to find patterns
            cpu_data = historical_data.get('CPUUtilization', {})
            
            if not cpu_data:
                return predictions
            
            hourly_patterns = {}
            for timestamp, cpu_value in cpu_data.items():
                hour = timestamp.hour
                if hour not in hourly_patterns:
                    hourly_patterns[hour] = []
                hourly_patterns[hour].append(cpu_value)
            
            # Calculate average CPU by hour
            avg_hourly_cpu = {
                hour: statistics.mean(values)
                for hour, values in hourly_patterns.items()
                if values
            }
            
            # Generate predictions for each hour
            current_time = datetime.utcnow()
            
            for i in range(forecast_hours):
                forecast_time = current_time + timedelta(hours=i)
                hour = forecast_time.hour
                
                predicted_cpu = avg_hourly_cpu.get(hour, 50)  # Default to 50% if no data
                
                # Determine if scaling might be needed
                scaling_action = ScalingAction.NO_ACTION
                confidence = 0.5
                
                if predicted_cpu > 80:
                    scaling_action = ScalingAction.SCALE_UP
                    confidence = min(0.9, predicted_cpu / 100)
                elif predicted_cpu < 20:
                    scaling_action = ScalingAction.SCALE_DOWN
                    confidence = min(0.9, (100 - predicted_cpu) / 100)
                
                predictions.append({
                    'timestamp': forecast_time.isoformat(),
                    'predicted_cpu': predicted_cpu,
                    'scaling_action': scaling_action.value,
                    'confidence': confidence,
                    'trigger': ScalingTrigger.PREDICTIVE.value
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to analyze scaling patterns: {e}")
            return predictions
    
    def get_scaling_rules(self) -> List[Dict[str, Any]]:
        """Get current scaling rules"""
        return [
            {
                'name': rule.name,
                'metric': rule.metric,
                'threshold_high': rule.threshold_high,
                'threshold_low': rule.threshold_low,
                'evaluation_periods': rule.evaluation_periods,
                'cooldown_minutes': rule.cooldown_minutes,
                'scale_up_action': rule.scale_up_action,
                'scale_down_action': rule.scale_down_action,
                'enabled': rule.enabled
            }
            for rule in self.scaling_rules
        ]
    
    def update_scaling_rule(self, rule_name: str, updates: Dict[str, Any]) -> bool:
        """Update a scaling rule"""
        try:
            for rule in self.scaling_rules:
                if rule.name == rule_name:
                    for key, value in updates.items():
                        if hasattr(rule, key):
                            setattr(rule, key, value)
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update scaling rule {rule_name}: {e}")
            return False
    
    def get_scaling_history(self, instance_id: str = None, 
                          hours: int = 24) -> List[Dict[str, Any]]:
        """Get scaling history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        filtered_history = [
            event for event in self.scaling_history
            if event.timestamp >= cutoff_time and (
                instance_id is None or event.instance_id == instance_id
            )
        ]
        
        return [
            {
                'timestamp': event.timestamp.isoformat(),
                'instance_id': event.instance_id,
                'action': event.action.value,
                'trigger': event.trigger.value,
                'old_instance_type': event.old_instance_type,
                'new_instance_type': event.new_instance_type,
                'metric_value': event.metric_value,
                'threshold': event.threshold,
                'success': event.success,
                'message': event.message
            }
            for event in sorted(filtered_history, key=lambda x: x.timestamp, reverse=True)
        ]