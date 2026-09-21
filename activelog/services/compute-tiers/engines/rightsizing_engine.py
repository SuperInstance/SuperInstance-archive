"""
Right-sizing Engine
Automatic instance right-sizing based on historical usage patterns and performance metrics
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

logger = logging.getLogger(__name__)

class RightsizingAction(Enum):
    DOWNSIZE = "downsize"
    UPSIZE = "upsize"
    NO_CHANGE = "no_change"
    FAMILY_CHANGE = "family_change"
    TERMINATE = "terminate"

class UtilizationLevel(Enum):
    VERY_LOW = "very_low"      # 0-10%
    LOW = "low"                # 10-25%
    MODERATE = "moderate"      # 25-50%
    HIGH = "high"              # 50-80%
    VERY_HIGH = "very_high"    # 80-100%
    EXCESSIVE = "excessive"    # >100% (burst)

@dataclass
class UtilizationMetrics:
    avg_cpu: float
    max_cpu: float
    avg_memory: float
    max_memory: float
    avg_network_in: float
    avg_network_out: float
    avg_disk_read: float
    avg_disk_write: float
    burst_credit_balance: Optional[float] = None
    sample_count: int = 0

@dataclass
class RightsizingRecommendation:
    instance_id: str
    current_type: str
    recommended_type: str
    action: RightsizingAction
    confidence: float
    potential_savings: float
    performance_impact: str  # "none", "minimal", "moderate", "significant"
    utilization_summary: Dict[str, Any]
    implementation_plan: List[str]
    risks: List[str]

class RightsizingEngine:
    """Automatic instance right-sizing engine"""
    
    def __init__(self, ec2_client, cloudwatch_client):
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client
        
        # Instance type hierarchy for sizing decisions
        self.instance_hierarchies = self._build_instance_hierarchies()
        
        # Pricing data (simplified)
        self.pricing = self._load_pricing_data()
        
        # Right-sizing rules
        self.rightsizing_rules = self._initialize_rightsizing_rules()
    
    def _build_instance_hierarchies(self) -> Dict[str, List[str]]:
        """Build instance type hierarchies for scaling decisions"""
        return {
            # T3 family (burstable)
            "t3": ["t3.nano", "t3.micro", "t3.small", "t3.medium", "t3.large", "t3.xlarge", "t3.2xlarge"],
            
            # M5 family (general purpose)
            "m5": ["m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge", "m5.8xlarge", "m5.12xlarge", "m5.16xlarge"],
            
            # C5 family (compute optimized)
            "c5": ["c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge", "c5.12xlarge", "c5.18xlarge"],
            
            # R5 family (memory optimized)
            "r5": ["r5.large", "r5.xlarge", "r5.2xlarge", "r5.4xlarge", "r5.8xlarge", "r5.12xlarge", "r5.16xlarge"],
            
            # Cross-family recommendations
            "upgrades": {
                "t3.large": ["m5.large", "c5.large"],
                "t3.xlarge": ["m5.xlarge", "c5.xlarge"],
                "m5.large": ["c5.large", "r5.large"],
                "m5.xlarge": ["c5.xlarge", "r5.xlarge"]
            }
        }
    
    def _load_pricing_data(self) -> Dict[str, float]:
        """Load hourly pricing data for instance types"""
        return {
            "t3.nano": 0.0052, "t3.micro": 0.0104, "t3.small": 0.0208,
            "t3.medium": 0.0416, "t3.large": 0.0832, "t3.xlarge": 0.1664,
            "m5.large": 0.096, "m5.xlarge": 0.192, "m5.2xlarge": 0.384,
            "m5.4xlarge": 0.768, "c5.large": 0.085, "c5.xlarge": 0.17,
            "c5.2xlarge": 0.34, "r5.large": 0.126, "r5.xlarge": 0.252,
            "r5.2xlarge": 0.504
        }
    
    def _initialize_rightsizing_rules(self) -> List[Dict[str, Any]]:
        """Initialize right-sizing rules"""
        return [
            {
                "name": "very_low_utilization",
                "conditions": {
                    "avg_cpu": {"max": 5},
                    "max_cpu": {"max": 20}
                },
                "action": RightsizingAction.TERMINATE,
                "confidence_base": 0.9,
                "description": "Instance with very low utilization - consider terminating"
            },
            {
                "name": "low_cpu_utilization",
                "conditions": {
                    "avg_cpu": {"max": 15},
                    "max_cpu": {"max": 40}
                },
                "action": RightsizingAction.DOWNSIZE,
                "confidence_base": 0.8,
                "description": "Low CPU utilization - downsize recommended"
            },
            {
                "name": "high_cpu_utilization", 
                "conditions": {
                    "avg_cpu": {"min": 70},
                    "max_cpu": {"min": 85}
                },
                "action": RightsizingAction.UPSIZE,
                "confidence_base": 0.85,
                "description": "High CPU utilization - upsize recommended"
            },
            {
                "name": "memory_pressure",
                "conditions": {
                    "avg_memory": {"min": 80},
                    "max_memory": {"min": 90}
                },
                "action": RightsizingAction.FAMILY_CHANGE,
                "confidence_base": 0.75,
                "description": "Memory pressure - consider memory-optimized instance"
            },
            {
                "name": "burst_credit_exhaustion",
                "conditions": {
                    "burst_credit_balance": {"max": 10}
                },
                "action": RightsizingAction.FAMILY_CHANGE,
                "confidence_base": 0.7,
                "description": "Burst credit exhaustion - consider non-burstable instance"
            }
        ]
    
    async def analyze_instances(self, instance_ids: List[str] = None, 
                              analysis_period_days: int = 7) -> Dict[str, Any]:
        """Analyze instances and generate right-sizing recommendations"""
        try:
            if not instance_ids:
                instance_ids = await self._get_all_running_instances()
            
            recommendations = []
            
            for instance_id in instance_ids:
                try:
                    recommendation = await self._analyze_single_instance(
                        instance_id, analysis_period_days
                    )
                    if recommendation:
                        recommendations.append(recommendation)
                except Exception as e:
                    logger.warning(f"Failed to analyze instance {instance_id}: {e}")
            
            # Generate summary statistics
            summary = self._generate_analysis_summary(recommendations)
            
            return {
                'recommendations': [self._recommendation_to_dict(rec) for rec in recommendations],
                'summary': summary,
                'analysis_period_days': analysis_period_days,
                'total_instances_analyzed': len(instance_ids),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze instances: {e}")
            raise
    
    async def _get_all_running_instances(self) -> List[str]:
        """Get all running EC2 instances"""
        try:
            response = self.ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            instance_ids = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_ids.append(instance['InstanceId'])
            
            return instance_ids
            
        except Exception as e:
            logger.error(f"Failed to get running instances: {e}")
            return []
    
    async def _analyze_single_instance(self, instance_id: str, 
                                     analysis_period_days: int) -> Optional[RightsizingRecommendation]:
        """Analyze a single instance for right-sizing opportunities"""
        try:
            # Get instance information
            instance_info = await self._get_instance_info(instance_id)
            if not instance_info:
                return None
            
            current_type = instance_info['instance_type']
            
            # Get utilization metrics
            utilization = await self._get_utilization_metrics(instance_id, analysis_period_days)
            
            if utilization.sample_count < 10:  # Not enough data
                return None
            
            # Apply right-sizing rules
            action, confidence = self._apply_rightsizing_rules(utilization, current_type)
            
            if action == RightsizingAction.NO_CHANGE:
                return None
            
            # Get recommended instance type
            recommended_type = self._get_recommended_instance_type(
                current_type, action, utilization
            )
            
            if not recommended_type or recommended_type == current_type:
                return None
            
            # Calculate potential savings
            potential_savings = self._calculate_potential_savings(
                current_type, recommended_type
            )
            
            # Assess performance impact
            performance_impact = self._assess_performance_impact(
                current_type, recommended_type, utilization
            )
            
            # Generate implementation plan
            implementation_plan = self._generate_implementation_plan(
                instance_id, current_type, recommended_type, action
            )
            
            # Identify risks
            risks = self._identify_risks(current_type, recommended_type, utilization)
            
            return RightsizingRecommendation(
                instance_id=instance_id,
                current_type=current_type,
                recommended_type=recommended_type,
                action=action,
                confidence=confidence,
                potential_savings=potential_savings,
                performance_impact=performance_impact,
                utilization_summary=self._summarize_utilization(utilization),
                implementation_plan=implementation_plan,
                risks=risks
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze instance {instance_id}: {e}")
            return None
    
    async def _get_instance_info(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get instance information"""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            
            return {
                'instance_id': instance_id,
                'instance_type': instance['InstanceType'],
                'launch_time': instance['LaunchTime'],
                'state': instance['State']['Name'],
                'platform': instance.get('Platform', 'linux')
            }
            
        except Exception as e:
            logger.error(f"Failed to get instance info for {instance_id}: {e}")
            return None
    
    async def _get_utilization_metrics(self, instance_id: str, 
                                     period_days: int) -> UtilizationMetrics:
        """Get comprehensive utilization metrics"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=period_days)
            
            metrics_data = {}
            
            # Define metrics to collect
            metric_definitions = [
                ('CPUUtilization', 'AWS/EC2', 'Percent'),
                ('NetworkIn', 'AWS/EC2', 'Bytes'),
                ('NetworkOut', 'AWS/EC2', 'Bytes'),
                ('DiskReadBytes', 'AWS/EC2', 'Bytes'),
                ('DiskWriteBytes', 'AWS/EC2', 'Bytes'),
                ('CPUCreditBalance', 'AWS/EC2', 'Count')  # For burstable instances
            ]
            
            for metric_name, namespace, unit in metric_definitions:
                try:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace=namespace,
                        MetricName=metric_name,
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1 hour periods
                        Statistics=['Average', 'Maximum']
                    )
                    
                    if response['Datapoints']:
                        avg_values = [dp['Average'] for dp in response['Datapoints']]
                        max_values = [dp['Maximum'] for dp in response['Datapoints']]
                        
                        metrics_data[metric_name] = {
                            'avg': statistics.mean(avg_values),
                            'max': max(max_values),
                            'samples': len(avg_values)
                        }
                    
                except Exception as e:
                    logger.warning(f"Failed to get {metric_name} for {instance_id}: {e}")
                    metrics_data[metric_name] = {'avg': 0, 'max': 0, 'samples': 0}
            
            # Get memory utilization (requires CloudWatch agent)
            memory_data = await self._get_memory_utilization(instance_id, start_time, end_time)
            
            sample_count = metrics_data.get('CPUUtilization', {}).get('samples', 0)
            
            return UtilizationMetrics(
                avg_cpu=metrics_data.get('CPUUtilization', {}).get('avg', 0),
                max_cpu=metrics_data.get('CPUUtilization', {}).get('max', 0),
                avg_memory=memory_data.get('avg', 50),  # Default if not available
                max_memory=memory_data.get('max', 70),
                avg_network_in=metrics_data.get('NetworkIn', {}).get('avg', 0),
                avg_network_out=metrics_data.get('NetworkOut', {}).get('avg', 0),
                avg_disk_read=metrics_data.get('DiskReadBytes', {}).get('avg', 0),
                avg_disk_write=metrics_data.get('DiskWriteBytes', {}).get('avg', 0),
                burst_credit_balance=metrics_data.get('CPUCreditBalance', {}).get('avg'),
                sample_count=sample_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get utilization metrics for {instance_id}: {e}")
            return UtilizationMetrics(0, 0, 0, 0, 0, 0, 0, 0, sample_count=0)
    
    async def _get_memory_utilization(self, instance_id: str, 
                                    start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """Get memory utilization from CloudWatch agent metrics"""
        try:
            # Try to get memory utilization from CloudWatch agent
            response = self.cloudwatch.get_metric_statistics(
                Namespace='CWAgent',
                MetricName='MemoryUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average', 'Maximum']
            )
            
            if response['Datapoints']:
                avg_values = [dp['Average'] for dp in response['Datapoints']]
                max_values = [dp['Maximum'] for dp in response['Datapoints']]
                
                return {
                    'avg': statistics.mean(avg_values),
                    'max': max(max_values)
                }
            
        except Exception as e:
            logger.warning(f"Memory metrics not available for {instance_id}: {e}")
        
        # Return estimated values if memory metrics aren't available
        return {'avg': 50, 'max': 70}
    
    def _apply_rightsizing_rules(self, utilization: UtilizationMetrics, 
                               current_type: str) -> Tuple[RightsizingAction, float]:
        """Apply right-sizing rules to determine recommended action"""
        best_action = RightsizingAction.NO_CHANGE
        best_confidence = 0.0
        
        for rule in self.rightsizing_rules:
            confidence = self._evaluate_rule(rule, utilization, current_type)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_action = rule['action']
        
        # Minimum confidence threshold
        if best_confidence < 0.6:
            return RightsizingAction.NO_CHANGE, best_confidence
        
        return best_action, best_confidence
    
    def _evaluate_rule(self, rule: Dict[str, Any], utilization: UtilizationMetrics,
                      current_type: str) -> float:
        """Evaluate a single right-sizing rule"""
        conditions = rule['conditions']
        confidence = rule['confidence_base']
        
        # Check each condition
        condition_matches = 0
        total_conditions = len(conditions)
        
        for metric, criteria in conditions.items():
            metric_value = getattr(utilization, metric, None)
            
            if metric_value is None:
                continue
            
            matches_condition = True
            
            if 'min' in criteria and metric_value < criteria['min']:
                matches_condition = False
            
            if 'max' in criteria and metric_value > criteria['max']:
                matches_condition = False
            
            if matches_condition:
                condition_matches += 1
        
        # Calculate confidence based on condition matches
        if condition_matches == total_conditions:
            # All conditions met - apply confidence modifiers
            confidence *= self._get_confidence_modifier(utilization, current_type)
            return confidence
        
        return 0.0
    
    def _get_confidence_modifier(self, utilization: UtilizationMetrics, 
                               current_type: str) -> float:
        """Get confidence modifier based on additional factors"""
        modifier = 1.0
        
        # More samples = higher confidence
        if utilization.sample_count > 100:
            modifier *= 1.1
        elif utilization.sample_count < 50:
            modifier *= 0.9
        
        # Consistent patterns = higher confidence
        if abs(utilization.avg_cpu - utilization.max_cpu/2) < 5:  # Consistent usage
            modifier *= 1.05
        
        # Burstable instance specific adjustments
        if current_type.startswith('t3') and utilization.burst_credit_balance:
            if utilization.burst_credit_balance < 50:
                modifier *= 1.15  # Higher confidence for burst exhaustion
        
        return modifier
    
    def _get_recommended_instance_type(self, current_type: str, action: RightsizingAction,
                                     utilization: UtilizationMetrics) -> Optional[str]:
        """Get recommended instance type based on action and utilization"""
        current_family = current_type.split('.')[0]
        
        if action == RightsizingAction.TERMINATE:
            return None
        
        elif action == RightsizingAction.DOWNSIZE:
            return self._get_smaller_instance_type(current_type)
        
        elif action == RightsizingAction.UPSIZE:
            return self._get_larger_instance_type(current_type)
        
        elif action == RightsizingAction.FAMILY_CHANGE:
            return self._get_different_family_instance(current_type, utilization)
        
        return None
    
    def _get_smaller_instance_type(self, current_type: str) -> Optional[str]:
        """Get the next smaller instance type in the same family"""
        family = current_type.split('.')[0]
        
        if family in self.instance_hierarchies:
            hierarchy = self.instance_hierarchies[family]
            try:
                current_index = hierarchy.index(current_type)
                if current_index > 0:
                    return hierarchy[current_index - 1]
            except ValueError:
                pass
        
        return None
    
    def _get_larger_instance_type(self, current_type: str) -> Optional[str]:
        """Get the next larger instance type in the same family"""
        family = current_type.split('.')[0]
        
        if family in self.instance_hierarchies:
            hierarchy = self.instance_hierarchies[family]
            try:
                current_index = hierarchy.index(current_type)
                if current_index < len(hierarchy) - 1:
                    return hierarchy[current_index + 1]
            except ValueError:
                pass
        
        return None
    
    def _get_different_family_instance(self, current_type: str, 
                                     utilization: UtilizationMetrics) -> Optional[str]:
        """Get instance type from different family based on utilization pattern"""
        # High memory usage -> Memory optimized
        if utilization.avg_memory > 70:
            if current_type == 't3.large':
                return 'r5.large'
            elif current_type == 't3.xlarge':
                return 'r5.xlarge'
            elif current_type == 'm5.large':
                return 'r5.large'
            elif current_type == 'm5.xlarge':
                return 'r5.xlarge'
        
        # High CPU usage -> Compute optimized
        elif utilization.avg_cpu > 60:
            if current_type == 't3.large':
                return 'c5.large'
            elif current_type == 't3.xlarge':
                return 'c5.xlarge'
            elif current_type == 'm5.large':
                return 'c5.large'
            elif current_type == 'm5.xlarge':
                return 'c5.xlarge'
        
        # Burstable with credit exhaustion -> Non-burstable
        elif (current_type.startswith('t3') and 
              utilization.burst_credit_balance and 
              utilization.burst_credit_balance < 50):
            if current_type == 't3.large':
                return 'm5.large'
            elif current_type == 't3.xlarge':
                return 'm5.xlarge'
        
        return None
    
    def _calculate_potential_savings(self, current_type: str, 
                                   recommended_type: str) -> float:
        """Calculate potential monthly savings from right-sizing"""
        current_cost = self.pricing.get(current_type, 0)
        recommended_cost = self.pricing.get(recommended_type, 0)
        
        monthly_savings = (current_cost - recommended_cost) * 24 * 30
        return monthly_savings
    
    def _assess_performance_impact(self, current_type: str, recommended_type: str,
                                 utilization: UtilizationMetrics) -> str:
        """Assess the performance impact of the recommendation"""
        # Get instance specifications (simplified)
        current_specs = self._get_instance_specs(current_type)
        recommended_specs = self._get_instance_specs(recommended_type)
        
        # Compare key metrics
        cpu_ratio = recommended_specs['vcpus'] / current_specs['vcpus']
        memory_ratio = recommended_specs['memory_gb'] / current_specs['memory_gb']
        
        # Determine impact based on utilization and spec changes
        if cpu_ratio >= 1.0 and memory_ratio >= 1.0:
            return "none"
        elif (cpu_ratio >= 0.8 and utilization.avg_cpu < 50 and
              memory_ratio >= 0.8 and utilization.avg_memory < 60):
            return "minimal"
        elif cpu_ratio >= 0.5 or memory_ratio >= 0.5:
            return "moderate"
        else:
            return "significant"
    
    def _get_instance_specs(self, instance_type: str) -> Dict[str, Any]:
        """Get simplified instance specifications"""
        specs_map = {
            "t3.nano": {"vcpus": 2, "memory_gb": 0.5},
            "t3.micro": {"vcpus": 2, "memory_gb": 1},
            "t3.small": {"vcpus": 2, "memory_gb": 2},
            "t3.medium": {"vcpus": 2, "memory_gb": 4},
            "t3.large": {"vcpus": 2, "memory_gb": 8},
            "t3.xlarge": {"vcpus": 4, "memory_gb": 16},
            "m5.large": {"vcpus": 2, "memory_gb": 8},
            "m5.xlarge": {"vcpus": 4, "memory_gb": 16},
            "m5.2xlarge": {"vcpus": 8, "memory_gb": 32},
            "c5.large": {"vcpus": 2, "memory_gb": 4},
            "c5.xlarge": {"vcpus": 4, "memory_gb": 8},
            "r5.large": {"vcpus": 2, "memory_gb": 16},
            "r5.xlarge": {"vcpus": 4, "memory_gb": 32}
        }
        
        return specs_map.get(instance_type, {"vcpus": 2, "memory_gb": 4})
    
    def _generate_implementation_plan(self, instance_id: str, current_type: str,
                                    recommended_type: str, action: RightsizingAction) -> List[str]:
        """Generate implementation plan for the recommendation"""
        if action == RightsizingAction.TERMINATE:
            return [
                "1. Verify instance is not needed for critical services",
                "2. Create final backup/snapshot if required",
                "3. Update monitoring and load balancer configurations",
                "4. Terminate the instance",
                "5. Monitor for any service disruptions"
            ]
        
        return [
            "1. Schedule maintenance window during low-traffic period",
            "2. Create AMI backup of current instance",
            "3. Stop the instance",
            f"4. Change instance type from {current_type} to {recommended_type}",
            "5. Start instance and verify all services are working",
            "6. Monitor performance for 24-48 hours",
            "7. Update monitoring thresholds if necessary"
        ]
    
    def _identify_risks(self, current_type: str, recommended_type: str,
                       utilization: UtilizationMetrics) -> List[str]:
        """Identify potential risks with the recommendation"""
        risks = []
        
        current_specs = self._get_instance_specs(current_type)
        recommended_specs = self._get_instance_specs(recommended_type)
        
        # CPU risks
        if recommended_specs['vcpus'] < current_specs['vcpus']:
            if utilization.max_cpu > 60:
                risks.append("Potential CPU bottleneck during peak loads")
        
        # Memory risks
        if recommended_specs['memory_gb'] < current_specs['memory_gb']:
            if utilization.max_memory > 70:
                risks.append("Potential memory pressure during peak usage")
        
        # Application-specific risks
        if current_type.startswith('t3') and not recommended_type.startswith('t3'):
            risks.append("Loss of burst capability - monitor CPU credit usage patterns")
        
        # Family change risks
        if current_type.split('.')[0] != recommended_type.split('.')[0]:
            risks.append("Family change may affect network or storage performance")
            risks.append("Thorough testing recommended before production deployment")
        
        return risks
    
    def _summarize_utilization(self, utilization: UtilizationMetrics) -> Dict[str, Any]:
        """Summarize utilization metrics"""
        return {
            'cpu': {
                'average': round(utilization.avg_cpu, 1),
                'maximum': round(utilization.max_cpu, 1),
                'level': self._get_utilization_level(utilization.avg_cpu).value
            },
            'memory': {
                'average': round(utilization.avg_memory, 1),
                'maximum': round(utilization.max_memory, 1),
                'level': self._get_utilization_level(utilization.avg_memory).value
            },
            'network': {
                'avg_in_mbps': round(utilization.avg_network_in / 1024 / 1024 * 8, 2),
                'avg_out_mbps': round(utilization.avg_network_out / 1024 / 1024 * 8, 2)
            },
            'samples': utilization.sample_count,
            'burst_credit_balance': utilization.burst_credit_balance
        }
    
    def _get_utilization_level(self, utilization_percent: float) -> UtilizationLevel:
        """Get utilization level enum from percentage"""
        if utilization_percent <= 10:
            return UtilizationLevel.VERY_LOW
        elif utilization_percent <= 25:
            return UtilizationLevel.LOW
        elif utilization_percent <= 50:
            return UtilizationLevel.MODERATE
        elif utilization_percent <= 80:
            return UtilizationLevel.HIGH
        elif utilization_percent <= 100:
            return UtilizationLevel.VERY_HIGH
        else:
            return UtilizationLevel.EXCESSIVE
    
    def _generate_analysis_summary(self, recommendations: List[RightsizingRecommendation]) -> Dict[str, Any]:
        """Generate summary of analysis results"""
        if not recommendations:
            return {
                'total_recommendations': 0,
                'potential_monthly_savings': 0,
                'message': 'No right-sizing opportunities found'
            }
        
        total_savings = sum(rec.potential_savings for rec in recommendations)
        action_counts = {}
        for rec in recommendations:
            action = rec.action.value
            action_counts[action] = action_counts.get(action, 0) + 1
        
        high_confidence_count = len([r for r in recommendations if r.confidence > 0.8])
        
        return {
            'total_recommendations': len(recommendations),
            'potential_monthly_savings': round(total_savings, 2),
            'action_breakdown': action_counts,
            'high_confidence_recommendations': high_confidence_count,
            'average_confidence': round(statistics.mean([r.confidence for r in recommendations]), 2),
            'top_savings_opportunity': max(recommendations, key=lambda x: x.potential_savings).instance_id
        }
    
    def _recommendation_to_dict(self, rec: RightsizingRecommendation) -> Dict[str, Any]:
        """Convert recommendation to dictionary"""
        return {
            'instance_id': rec.instance_id,
            'current_type': rec.current_type,
            'recommended_type': rec.recommended_type,
            'action': rec.action.value,
            'confidence': round(rec.confidence, 2),
            'potential_monthly_savings': round(rec.potential_savings, 2),
            'performance_impact': rec.performance_impact,
            'utilization_summary': rec.utilization_summary,
            'implementation_plan': rec.implementation_plan,
            'risks': rec.risks
        }
    
    async def continuous_analysis(self):
        """Continuously analyze instances for right-sizing opportunities"""
        try:
            logger.info("Starting continuous right-sizing analysis")
            
            # Get all instances to analyze
            instance_ids = await self._get_all_running_instances()
            
            if not instance_ids:
                return
            
            # Analyze in batches to avoid overwhelming the API
            batch_size = 10
            for i in range(0, len(instance_ids), batch_size):
                batch = instance_ids[i:i + batch_size]
                
                try:
                    results = await self.analyze_instances(batch, analysis_period_days=7)
                    
                    # Process high-confidence recommendations
                    for rec_dict in results['recommendations']:
                        if rec_dict['confidence'] > 0.8:
                            logger.info(f"High-confidence right-sizing opportunity: "
                                      f"{rec_dict['instance_id']} -> {rec_dict['recommended_type']} "
                                      f"(${rec_dict['potential_monthly_savings']:.2f}/month savings)")
                    
                    # Small delay between batches
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to analyze batch {i//batch_size + 1}: {e}")
            
            logger.info("Completed continuous right-sizing analysis")
            
        except Exception as e:
            logger.error(f"Continuous analysis failed: {e}")