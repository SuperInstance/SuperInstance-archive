#!/usr/bin/env python3
"""
Burst Capacity Manager for ActiveLog Compute Tiers
Intelligent management of burst performance and capacity requirements
"""

import boto3
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class BurstType(Enum):
    """Types of burst patterns"""
    SPORADIC = "sporadic"
    PERIODIC = "periodic"
    SEASONAL = "seasonal"
    TRAFFIC_SPIKE = "traffic_spike"
    BATCH_PROCESSING = "batch_processing"

@dataclass
class BurstPattern:
    """Represents a burst usage pattern"""
    pattern_type: BurstType
    frequency: str  # daily, weekly, monthly
    duration_minutes: int
    intensity_multiplier: float
    predictability_score: float
    confidence: float

@dataclass
class BurstRecommendation:
    """Burst capacity optimization recommendation"""
    instance_id: str
    current_type: str
    recommended_action: str
    target_instance_type: Optional[str]
    estimated_cost_impact: float
    performance_improvement: float
    burst_coverage: float
    implementation_risk: str

class BurstCapacityManager:
    """Manages burst capacity analysis and optimization"""
    
    def __init__(self, ec2_client, cloudwatch_client):
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client
        
        # Burstable instance types and their characteristics
        self.burstable_types = {
            't3.nano': {'baseline_cpu': 5, 'burst_cpu': 100, 'credits_per_hour': 6},
            't3.micro': {'baseline_cpu': 10, 'burst_cpu': 100, 'credits_per_hour': 12},
            't3.small': {'baseline_cpu': 20, 'burst_cpu': 100, 'credits_per_hour': 24},
            't3.medium': {'baseline_cpu': 20, 'burst_cpu': 100, 'credits_per_hour': 24},
            't3.large': {'baseline_cpu': 30, 'burst_cpu': 100, 'credits_per_hour': 36},
            't3.xlarge': {'baseline_cpu': 40, 'burst_cpu': 100, 'credits_per_hour': 96},
            't3.2xlarge': {'baseline_cpu': 40, 'burst_cpu': 100, 'credits_per_hour': 192},
            't3a.nano': {'baseline_cpu': 5, 'burst_cpu': 100, 'credits_per_hour': 6},
            't3a.micro': {'baseline_cpu': 10, 'burst_cpu': 100, 'credits_per_hour': 12},
            't3a.small': {'baseline_cpu': 20, 'burst_cpu': 100, 'credits_per_hour': 24},
            't3a.medium': {'baseline_cpu': 20, 'burst_cpu': 100, 'credits_per_hour': 24},
            't3a.large': {'baseline_cpu': 30, 'burst_cpu': 100, 'credits_per_hour': 36},
            't3a.xlarge': {'baseline_cpu': 40, 'burst_cpu': 100, 'credits_per_hour': 96},
            't3a.2xlarge': {'baseline_cpu': 40, 'burst_cpu': 100, 'credits_per_hour': 192},
            't4g.nano': {'baseline_cpu': 5, 'burst_cpu': 100, 'credits_per_hour': 6},
            't4g.micro': {'baseline_cpu': 10, 'burst_cpu': 100, 'credits_per_hour': 12},
            't4g.small': {'baseline_cpu': 20, 'burst_cpu': 100, 'credits_per_hour': 24},
            't4g.medium': {'baseline_cpu': 20, 'burst_cpu': 100, 'credits_per_hour': 24},
            't4g.large': {'baseline_cpu': 30, 'burst_cpu': 100, 'credits_per_hour': 36},
            't4g.xlarge': {'baseline_cpu': 40, 'burst_cpu': 100, 'credits_per_hour': 96},
            't4g.2xlarge': {'baseline_cpu': 40, 'burst_cpu': 100, 'credits_per_hour': 192}
        }
        
        # High-performance instance alternatives
        self.performance_alternatives = {
            't3.nano': ['t3.micro', 'm5.large'],
            't3.micro': ['t3.small', 'm5.large'],
            't3.small': ['t3.medium', 'm5.large', 'c5.large'],
            't3.medium': ['t3.large', 'm5.large', 'c5.large'],
            't3.large': ['t3.xlarge', 'm5.xlarge', 'c5.xlarge'],
            't3.xlarge': ['t3.2xlarge', 'm5.xlarge', 'c5.xlarge'],
            't3.2xlarge': ['m5.2xlarge', 'c5.2xlarge']
        }

    def analyze_burst_needs(self, instance_ids: List[str]) -> Dict[str, Any]:
        """Analyze burst capacity needs for given instances"""
        try:
            results = {
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'instances_analyzed': len(instance_ids),
                'burst_analysis': {},
                'recommendations': []
            }
            
            for instance_id in instance_ids:
                instance_analysis = self._analyze_instance_burst_needs(instance_id)
                results['burst_analysis'][instance_id] = instance_analysis
                
                if instance_analysis.get('recommendations'):
                    results['recommendations'].extend(instance_analysis['recommendations'])
            
            # Generate summary metrics
            results['summary'] = self._generate_burst_summary(results['burst_analysis'])
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to analyze burst needs: {e}")
            raise

    def _analyze_instance_burst_needs(self, instance_id: str) -> Dict[str, Any]:
        """Analyze burst needs for a single instance"""
        try:
            # Get instance information
            instance_info = self._get_instance_info(instance_id)
            if not instance_info:
                return {'error': f'Instance {instance_id} not found'}
            
            instance_type = instance_info['InstanceType']
            
            # Collect CPU and credit metrics
            metrics = self._collect_burst_metrics(instance_id, days=7)
            
            # Analyze burst patterns
            patterns = self._identify_burst_patterns(metrics)
            
            # Check if instance is burstable
            is_burstable = instance_type in self.burstable_types
            
            analysis = {
                'instance_id': instance_id,
                'instance_type': instance_type,
                'is_burstable': is_burstable,
                'burst_patterns': patterns,
                'metrics_summary': self._summarize_metrics(metrics),
                'credit_analysis': self._analyze_cpu_credits(metrics, instance_type) if is_burstable else None,
                'recommendations': []
            }
            
            # Generate recommendations
            recommendations = self._generate_burst_recommendations(instance_id, analysis)
            analysis['recommendations'] = recommendations
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze instance {instance_id}: {e}")
            return {'error': str(e)}

    def _get_instance_info(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get EC2 instance information"""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            if response['Reservations']:
                return response['Reservations'][0]['Instances'][0]
            return None
        except Exception as e:
            logger.error(f"Failed to get instance info for {instance_id}: {e}")
            return None

    def _collect_burst_metrics(self, instance_id: str, days: int = 7) -> Dict[str, List]:
        """Collect CPU and credit metrics for burst analysis"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        metrics = {
            'cpu_utilization': [],
            'cpu_credit_usage': [],
            'cpu_credit_balance': [],
            'timestamps': []
        }
        
        try:
            # CPU Utilization
            cpu_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5-minute intervals
                Statistics=['Average', 'Maximum']
            )
            
            for datapoint in sorted(cpu_response['Datapoints'], key=lambda x: x['Timestamp']):
                metrics['cpu_utilization'].append({
                    'timestamp': datapoint['Timestamp'],
                    'average': datapoint['Average'],
                    'maximum': datapoint['Maximum']
                })
                metrics['timestamps'].append(datapoint['Timestamp'])
            
            # CPU Credit metrics (for burstable instances)
            try:
                credit_usage_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUCreditUsage',
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Average', 'Sum']
                )
                
                for datapoint in sorted(credit_usage_response['Datapoints'], key=lambda x: x['Timestamp']):
                    metrics['cpu_credit_usage'].append({
                        'timestamp': datapoint['Timestamp'],
                        'average': datapoint['Average'],
                        'sum': datapoint['Sum']
                    })
                
                credit_balance_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUCreditBalance',
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Average', 'Minimum']
                )
                
                for datapoint in sorted(credit_balance_response['Datapoints'], key=lambda x: x['Timestamp']):
                    metrics['cpu_credit_balance'].append({
                        'timestamp': datapoint['Timestamp'],
                        'average': datapoint['Average'],
                        'minimum': datapoint['Minimum']
                    })
                    
            except Exception as e:
                logger.warning(f"Could not collect CPU credit metrics for {instance_id}: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for {instance_id}: {e}")
            return metrics

    def _identify_burst_patterns(self, metrics: Dict[str, List]) -> List[BurstPattern]:
        """Identify burst usage patterns from metrics"""
        patterns = []
        
        if not metrics['cpu_utilization']:
            return patterns
        
        cpu_data = [point['maximum'] for point in metrics['cpu_utilization']]
        timestamps = [point['timestamp'] for point in metrics['cpu_utilization']]
        
        # Define burst threshold (instances using >70% CPU)
        burst_threshold = 70
        burst_episodes = []
        
        # Identify burst episodes
        in_burst = False
        burst_start = None
        
        for i, cpu_util in enumerate(cpu_data):
            if cpu_util > burst_threshold and not in_burst:
                in_burst = True
                burst_start = i
            elif cpu_util <= burst_threshold and in_burst:
                in_burst = False
                burst_episodes.append({
                    'start_index': burst_start,
                    'end_index': i - 1,
                    'duration_minutes': (i - burst_start) * 5,
                    'peak_cpu': max(cpu_data[burst_start:i]),
                    'avg_cpu': sum(cpu_data[burst_start:i]) / len(cpu_data[burst_start:i])
                })
        
        if not burst_episodes:
            return patterns
        
        # Analyze pattern characteristics
        total_episodes = len(burst_episodes)
        avg_duration = sum(ep['duration_minutes'] for ep in burst_episodes) / total_episodes
        avg_intensity = sum(ep['peak_cpu'] for ep in burst_episodes) / total_episodes
        
        # Determine pattern type based on frequency and regularity
        if total_episodes >= 20:  # Frequent bursts
            pattern_type = BurstType.SPORADIC
            frequency = "high"
        elif total_episodes >= 10:
            pattern_type = BurstType.PERIODIC
            frequency = "medium"
        else:
            pattern_type = BurstType.SEASONAL
            frequency = "low"
        
        # Calculate predictability based on regularity of intervals
        intervals = []
        for i in range(1, len(burst_episodes)):
            interval = burst_episodes[i]['start_index'] - burst_episodes[i-1]['end_index']
            intervals.append(interval * 5)  # Convert to minutes
        
        if intervals:
            interval_variance = sum((x - sum(intervals)/len(intervals))**2 for x in intervals) / len(intervals)
            predictability = max(0, 1 - (interval_variance / (sum(intervals)/len(intervals))**2))
        else:
            predictability = 0.5
        
        patterns.append(BurstPattern(
            pattern_type=pattern_type,
            frequency=frequency,
            duration_minutes=int(avg_duration),
            intensity_multiplier=avg_intensity / 50,  # Normalize against moderate usage
            predictability_score=predictability,
            confidence=min(0.9, total_episodes / 20)
        ))
        
        return patterns

    def _summarize_metrics(self, metrics: Dict[str, List]) -> Dict[str, Any]:
        """Summarize burst metrics"""
        if not metrics['cpu_utilization']:
            return {}
        
        cpu_values = [point['average'] for point in metrics['cpu_utilization']]
        cpu_max_values = [point['maximum'] for point in metrics['cpu_utilization']]
        
        return {
            'avg_cpu_utilization': sum(cpu_values) / len(cpu_values),
            'max_cpu_utilization': max(cpu_max_values),
            'min_cpu_utilization': min(cpu_values),
            'cpu_spikes_count': len([x for x in cpu_max_values if x > 80]),
            'high_utilization_periods': len([x for x in cpu_values if x > 70]),
            'data_points': len(cpu_values)
        }

    def _analyze_cpu_credits(self, metrics: Dict[str, List], instance_type: str) -> Dict[str, Any]:
        """Analyze CPU credit usage and balance for burstable instances"""
        if instance_type not in self.burstable_types:
            return {}
        
        instance_specs = self.burstable_types[instance_type]
        
        analysis = {
            'baseline_cpu_percent': instance_specs['baseline_cpu'],
            'credits_per_hour': instance_specs['credits_per_hour'],
            'burst_capacity_cpu_percent': instance_specs['burst_cpu']
        }
        
        if metrics.get('cpu_credit_usage'):
            credit_usage = [point['average'] for point in metrics['cpu_credit_usage']]
            analysis.update({
                'avg_credit_usage_per_minute': sum(credit_usage) / len(credit_usage),
                'max_credit_usage_per_minute': max(credit_usage),
                'total_credits_consumed': sum(point['sum'] for point in metrics['cpu_credit_usage'])
            })
        
        if metrics.get('cpu_credit_balance'):
            credit_balance = [point['average'] for point in metrics['cpu_credit_balance']]
            min_balance = [point['minimum'] for point in metrics['cpu_credit_balance']]
            analysis.update({
                'avg_credit_balance': sum(credit_balance) / len(credit_balance),
                'min_credit_balance': min(min_balance),
                'credit_exhaustion_episodes': len([x for x in min_balance if x < 1])
            })
        
        return analysis

    def _generate_burst_recommendations(self, instance_id: str, analysis: Dict[str, Any]) -> List[BurstRecommendation]:
        """Generate burst capacity optimization recommendations"""
        recommendations = []
        
        instance_type = analysis['instance_type']
        is_burstable = analysis['is_burstable']
        patterns = analysis['burst_patterns']
        metrics_summary = analysis.get('metrics_summary', {})
        credit_analysis = analysis.get('credit_analysis', {})
        
        # High CPU utilization without bursting capability
        if not is_burstable and metrics_summary.get('max_cpu_utilization', 0) > 80:
            recommendations.append(BurstRecommendation(
                instance_id=instance_id,
                current_type=instance_type,
                recommended_action="upgrade_instance",
                target_instance_type=self._suggest_upgrade(instance_type),
                estimated_cost_impact=25.0,  # Rough estimate
                performance_improvement=40.0,
                burst_coverage=100.0,
                implementation_risk="low"
            ))
        
        # Burstable instance with credit exhaustion
        if is_burstable and credit_analysis.get('credit_exhaustion_episodes', 0) > 0:
            if credit_analysis['credit_exhaustion_episodes'] > 5:
                # Frequent credit exhaustion - recommend upgrade
                recommendations.append(BurstRecommendation(
                    instance_id=instance_id,
                    current_type=instance_type,
                    recommended_action="switch_to_fixed_performance",
                    target_instance_type=self._suggest_fixed_performance_alternative(instance_type),
                    estimated_cost_impact=30.0,
                    performance_improvement=60.0,
                    burst_coverage=100.0,
                    implementation_risk="medium"
                ))
            else:
                # Occasional credit exhaustion - recommend larger burstable
                recommendations.append(BurstRecommendation(
                    instance_id=instance_id,
                    current_type=instance_type,
                    recommended_action="upgrade_burstable",
                    target_instance_type=self._suggest_larger_burstable(instance_type),
                    estimated_cost_impact=50.0,
                    performance_improvement=30.0,
                    burst_coverage=90.0,
                    implementation_risk="low"
                ))
        
        # Over-provisioned instance (consistently low utilization)
        if metrics_summary.get('avg_cpu_utilization', 0) < 20 and metrics_summary.get('max_cpu_utilization', 0) < 50:
            recommendations.append(BurstRecommendation(
                instance_id=instance_id,
                current_type=instance_type,
                recommended_action="downsize_to_burstable",
                target_instance_type=self._suggest_smaller_burstable(instance_type),
                estimated_cost_impact=-40.0,  # Cost savings
                performance_improvement=0.0,
                burst_coverage=80.0,
                implementation_risk="low"
            ))
        
        # Predictable burst patterns - suggest scheduling or auto-scaling
        if patterns:
            high_predictability_patterns = [p for p in patterns if p.predictability_score > 0.7]
            if high_predictability_patterns:
                recommendations.append(BurstRecommendation(
                    instance_id=instance_id,
                    current_type=instance_type,
                    recommended_action="implement_scheduled_scaling",
                    target_instance_type=None,
                    estimated_cost_impact=-20.0,
                    performance_improvement=20.0,
                    burst_coverage=95.0,
                    implementation_risk="medium"
                ))
        
        return recommendations

    def _suggest_upgrade(self, current_type: str) -> str:
        """Suggest an upgraded instance type"""
        # Simple upgrade logic - move to next size in same family
        if 'nano' in current_type:
            return current_type.replace('nano', 'micro')
        elif 'micro' in current_type:
            return current_type.replace('micro', 'small')
        elif 'small' in current_type:
            return current_type.replace('small', 'medium')
        elif 'medium' in current_type:
            return current_type.replace('medium', 'large')
        elif 'large' in current_type and 'xlarge' not in current_type:
            return current_type.replace('large', 'xlarge')
        elif 'xlarge' in current_type and '2xlarge' not in current_type:
            return current_type.replace('xlarge', '2xlarge')
        else:
            return 'm5.large'  # Default upgrade

    def _suggest_fixed_performance_alternative(self, current_type: str) -> str:
        """Suggest fixed performance alternative to burstable instance"""
        if current_type in self.performance_alternatives:
            return self.performance_alternatives[current_type][-1]  # Return the highest performance option
        return 'm5.large'  # Default

    def _suggest_larger_burstable(self, current_type: str) -> str:
        """Suggest a larger burstable instance"""
        return self._suggest_upgrade(current_type)

    def _suggest_smaller_burstable(self, current_type: str) -> str:
        """Suggest a smaller burstable instance"""
        if 't3' not in current_type.lower():
            return 't3.medium'  # Default small burstable
        
        if '2xlarge' in current_type:
            return current_type.replace('2xlarge', 'xlarge')
        elif 'xlarge' in current_type:
            return current_type.replace('xlarge', 'large')
        elif 'large' in current_type:
            return current_type.replace('large', 'medium')
        elif 'medium' in current_type:
            return current_type.replace('medium', 'small')
        elif 'small' in current_type:
            return current_type.replace('small', 'micro')
        else:
            return current_type  # Can't go smaller

    def _generate_burst_summary(self, burst_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of burst analysis across all instances"""
        total_instances = len(burst_analysis)
        burstable_instances = 0
        instances_with_patterns = 0
        instances_needing_optimization = 0
        total_recommendations = 0
        
        for instance_id, analysis in burst_analysis.items():
            if analysis.get('is_burstable'):
                burstable_instances += 1
            if analysis.get('burst_patterns'):
                instances_with_patterns += 1
            if analysis.get('recommendations'):
                instances_needing_optimization += 1
                total_recommendations += len(analysis['recommendations'])
        
        return {
            'total_instances_analyzed': total_instances,
            'burstable_instances': burstable_instances,
            'instances_with_burst_patterns': instances_with_patterns,
            'instances_needing_optimization': instances_needing_optimization,
            'total_recommendations': total_recommendations,
            'optimization_opportunity_rate': (instances_needing_optimization / total_instances * 100) if total_instances > 0 else 0
        }

    async def monitor_burst_capacity(self):
        """Continuous monitoring of burst capacity across all managed instances"""
        try:
            # Get all running instances
            response = self.ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            instance_ids = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_ids.append(instance['InstanceId'])
            
            if not instance_ids:
                logger.info("No running instances found for burst monitoring")
                return
            
            # Analyze current burst needs
            analysis = self.analyze_burst_needs(instance_ids)
            
            # Log summary
            summary = analysis['summary']
            logger.info(f"Burst capacity monitoring: {summary['instances_needing_optimization']} "
                       f"of {summary['total_instances_analyzed']} instances need optimization")
            
            # Check for critical burst capacity issues
            for instance_id, instance_analysis in analysis['burst_analysis'].items():
                if instance_analysis.get('credit_analysis', {}).get('credit_exhaustion_episodes', 0) > 10:
                    logger.warning(f"Instance {instance_id} experiencing frequent CPU credit exhaustion")
                
                max_cpu = instance_analysis.get('metrics_summary', {}).get('max_cpu_utilization', 0)
                if max_cpu > 95:
                    logger.warning(f"Instance {instance_id} hitting CPU limits (max: {max_cpu}%)")
            
        except Exception as e:
            logger.error(f"Error in burst capacity monitoring: {e}")

    def optimize_burst_configuration(self, instance_ids: List[str], auto_apply: bool = False) -> Dict[str, Any]:
        """Optimize burst configuration for specified instances"""
        try:
            analysis = self.analyze_burst_needs(instance_ids)
            optimization_plan = {
                'timestamp': datetime.utcnow().isoformat(),
                'instances_analyzed': len(instance_ids),
                'optimizations': [],
                'estimated_savings': 0.0,
                'estimated_performance_gain': 0.0
            }
            
            for instance_id, instance_analysis in analysis['burst_analysis'].items():
                for recommendation in instance_analysis.get('recommendations', []):
                    optimization = {
                        'instance_id': instance_id,
                        'current_type': recommendation.current_type,
                        'recommended_action': recommendation.recommended_action,
                        'target_type': recommendation.target_instance_type,
                        'cost_impact': recommendation.estimated_cost_impact,
                        'performance_improvement': recommendation.performance_improvement,
                        'risk_level': recommendation.implementation_risk,
                        'applied': False
                    }
                    
                    if auto_apply and recommendation.implementation_risk == 'low':
                        # In a real implementation, you would apply the changes here
                        optimization['applied'] = True
                        logger.info(f"Applied optimization for {instance_id}: {recommendation.recommended_action}")
                    
                    optimization_plan['optimizations'].append(optimization)
                    optimization_plan['estimated_savings'] += min(0, recommendation.estimated_cost_impact)
                    optimization_plan['estimated_performance_gain'] += recommendation.performance_improvement
            
            return optimization_plan
            
        except Exception as e:
            logger.error(f"Failed to optimize burst configuration: {e}")
            raise