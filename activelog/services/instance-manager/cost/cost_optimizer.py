"""
Cost Optimizer
Comprehensive cost optimization with alerts, limits, and intelligent recommendations
"""

import logging
import boto3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics
import asyncio
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CostCategory(Enum):
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    OTHER = "other"

@dataclass
class CostAlert:
    id: str
    severity: AlertSeverity
    category: CostCategory
    threshold: float
    current_value: float
    message: str
    timestamp: datetime
    resolved: bool = False

@dataclass
class CostOptimizationRecommendation:
    id: str
    title: str
    description: str
    category: CostCategory
    estimated_savings: float
    effort_level: str  # 'low', 'medium', 'high'
    implementation_steps: List[str]
    priority_score: float

class CostOptimizer:
    """Comprehensive cost optimization and monitoring"""
    
    def __init__(self, ec2_client, pricing_client):
        self.ec2 = ec2_client
        self.pricing_client = pricing_client
        self.cloudwatch = boto3.client('cloudwatch', region_name=ec2_client.meta.region_name)
        self.cost_explorer = boto3.client('ce')  # Cost Explorer
        
        # Cost tracking
        self.monthly_cost_limit = 5000.0  # Default $5000/month
        self.daily_cost_limit = 200.0     # Default $200/day
        self.active_alerts: List[CostAlert] = []
        
        # Cost optimization rules
        self.optimization_rules = self._initialize_optimization_rules()
        
    def _initialize_optimization_rules(self) -> List[Dict[str, Any]]:
        """Initialize cost optimization rules"""
        return [
            {
                'name': 'unused_instances',
                'description': 'Detect instances with low utilization',
                'threshold': {'cpu': 5, 'network': 1000},  # 5% CPU, 1KB network
                'savings_potential': 0.9,
                'effort': 'low'
            },
            {
                'name': 'oversized_instances',
                'description': 'Detect oversized instances',
                'threshold': {'cpu': 25, 'memory': 30},  # 25% CPU, 30% memory
                'savings_potential': 0.4,
                'effort': 'medium'
            },
            {
                'name': 'unattached_volumes',
                'description': 'Find unattached EBS volumes',
                'threshold': {},
                'savings_potential': 1.0,
                'effort': 'low'
            },
            {
                'name': 'old_snapshots',
                'description': 'Identify old snapshots for cleanup',
                'threshold': {'age_days': 90},
                'savings_potential': 0.8,
                'effort': 'low'
            },
            {
                'name': 'non_gp3_volumes',
                'description': 'Volumes not using cost-effective gp3',
                'threshold': {},
                'savings_potential': 0.2,
                'effort': 'low'
            }
        ]
    
    async def optimize_all(self) -> Dict[str, Any]:
        """Run comprehensive cost optimization analysis"""
        try:
            logger.info("Starting comprehensive cost optimization analysis")
            
            # Get current cost data
            cost_analysis = await self._analyze_current_costs()
            
            # Analyze instance costs
            instance_recommendations = await self._analyze_instance_costs()
            
            # Analyze storage costs
            storage_recommendations = await self._analyze_storage_costs()
            
            # Check for unused resources
            unused_resources = await self._find_unused_resources()
            
            # Analyze reserved instance opportunities
            ri_recommendations = await self._analyze_reserved_instance_opportunities()
            
            # Spot instance opportunities
            spot_recommendations = await self._analyze_spot_opportunities()
            
            # Generate consolidated recommendations
            all_recommendations = (
                instance_recommendations + 
                storage_recommendations + 
                unused_resources + 
                ri_recommendations + 
                spot_recommendations
            )
            
            # Sort by potential savings
            all_recommendations.sort(key=lambda x: x.estimated_savings, reverse=True)
            
            total_potential_savings = sum(rec.estimated_savings for rec in all_recommendations)
            
            optimization_summary = {
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'current_monthly_cost': cost_analysis['monthly_estimate'],
                'potential_monthly_savings': total_potential_savings,
                'savings_percentage': (total_potential_savings / cost_analysis['monthly_estimate'] * 100) if cost_analysis['monthly_estimate'] > 0 else 0,
                'total_recommendations': len(all_recommendations),
                'high_priority_count': len([r for r in all_recommendations if r.priority_score >= 8.0]),
                'quick_wins_count': len([r for r in all_recommendations if r.effort_level == 'low']),
                'recommendations': [self._recommendation_to_dict(rec) for rec in all_recommendations[:20]]  # Top 20
            }
            
            return optimization_summary
            
        except Exception as e:
            logger.error(f"Failed to run cost optimization: {e}")
            raise
    
    async def _analyze_current_costs(self) -> Dict[str, Any]:
        """Analyze current cost patterns"""
        try:
            # Get cost data for the last 30 days
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=30)
            
            response = self.cost_explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            # Calculate daily costs and trends
            daily_costs = []
            service_costs = {}
            
            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                total_cost = 0
                
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    total_cost += cost
                    
                    if service not in service_costs:
                        service_costs[service] = []
                    service_costs[service].append(cost)
                
                daily_costs.append({
                    'date': date,
                    'cost': total_cost
                })
            
            # Calculate statistics
            total_30_day_cost = sum(day['cost'] for day in daily_costs)
            avg_daily_cost = total_30_day_cost / len(daily_costs) if daily_costs else 0
            monthly_estimate = avg_daily_cost * 30
            
            # Find top services by cost
            top_services = [
                {
                    'service': service,
                    'total_cost': sum(costs),
                    'avg_daily_cost': statistics.mean(costs),
                    'percentage_of_total': (sum(costs) / total_30_day_cost * 100) if total_30_day_cost > 0 else 0
                }
                for service, costs in service_costs.items()
            ]
            top_services.sort(key=lambda x: x['total_cost'], reverse=True)
            
            return {
                'period_days': 30,
                'total_cost': total_30_day_cost,
                'average_daily_cost': avg_daily_cost,
                'monthly_estimate': monthly_estimate,
                'daily_costs': daily_costs[-7:],  # Last 7 days
                'top_services': top_services[:10]  # Top 10 services
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze current costs: {e}")
            return {
                'period_days': 30,
                'total_cost': 0,
                'average_daily_cost': 0,
                'monthly_estimate': 0,
                'daily_costs': [],
                'top_services': []
            }
    
    async def _analyze_instance_costs(self) -> List[CostOptimizationRecommendation]:
        """Analyze EC2 instance costs and generate recommendations"""
        recommendations = []
        
        try:
            # Get all running instances
            response = self.ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    
                    # Get utilization metrics
                    utilization = await self._get_instance_utilization(instance_id)
                    
                    # Get cost estimation
                    hourly_cost = self._estimate_instance_hourly_cost(instance_type)
                    monthly_cost = hourly_cost * 24 * 30
                    
                    # Check for underutilized instances
                    if utilization['avg_cpu'] < 10 and utilization['avg_network'] < 1000:
                        recommendations.append(CostOptimizationRecommendation(
                            id=f"unused_instance_{instance_id}",
                            title=f"Underutilized Instance: {instance_id}",
                            description=f"Instance {instance_id} ({instance_type}) has very low utilization: {utilization['avg_cpu']:.1f}% CPU",
                            category=CostCategory.COMPUTE,
                            estimated_savings=monthly_cost * 0.9,  # 90% savings if terminated
                            effort_level='low',
                            implementation_steps=[
                                'Verify instance is not needed for critical services',
                                'Create backup/snapshot if needed',
                                'Stop or terminate the instance',
                                'Update monitoring and alerting'
                            ],
                            priority_score=9.0
                        ))\n                    \n                    # Check for oversized instances\n                    elif utilization['avg_cpu'] < 30 and utilization['avg_memory'] < 40:\n                        smaller_type = self._suggest_smaller_instance_type(instance_type)\n                        if smaller_type:\n                            smaller_cost = self._estimate_instance_hourly_cost(smaller_type) * 24 * 30\n                            potential_savings = monthly_cost - smaller_cost\n                            \n                            recommendations.append(CostOptimizationRecommendation(\n                                id=f\"rightsize_instance_{instance_id}\",\n                                title=f\"Right-size Instance: {instance_id}\",\n                                description=f\"Instance {instance_id} can be downsized from {instance_type} to {smaller_type}\",\n                                category=CostCategory.COMPUTE,\n                                estimated_savings=potential_savings,\n                                effort_level='medium',\n                                implementation_steps=[\n                                    'Schedule maintenance window',\n                                    'Stop the instance',\n                                    f'Change instance type to {smaller_type}',\n                                    'Start instance and verify functionality',\n                                    'Monitor performance after change'\n                                ],\n                                priority_score=7.5\n                            ))\n                    \n                    # Check for old instances that might benefit from newer types\n                    launch_time = instance.get('LaunchTime')\n                    if launch_time and (datetime.utcnow() - launch_time.replace(tzinfo=None)).days > 365:\n                        modern_type = self._suggest_modern_instance_type(instance_type)\n                        if modern_type != instance_type:\n                            modern_cost = self._estimate_instance_hourly_cost(modern_type) * 24 * 30\n                            potential_savings = monthly_cost - modern_cost\n                            \n                            if potential_savings > 0:\n                                recommendations.append(CostOptimizationRecommendation(\n                                    id=f\"modernize_instance_{instance_id}\",\n                                    title=f\"Modernize Instance: {instance_id}\",\n                                    description=f\"Upgrade old instance from {instance_type} to more efficient {modern_type}\",\n                                    category=CostCategory.COMPUTE,\n                                    estimated_savings=potential_savings,\n                                    effort_level='high',\n                                    implementation_steps=[\n                                        'Test application compatibility with new instance type',\n                                        'Create AMI backup',\n                                        'Schedule maintenance window',\n                                        f'Migrate to {modern_type}',\n                                        'Performance testing and validation'\n                                    ],\n                                    priority_score=6.0\n                                ))\n            \n            return recommendations\n            \n        except Exception as e:\n            logger.error(f\"Failed to analyze instance costs: {e}\")\n            return []\n    \n    async def _get_instance_utilization(self, instance_id: str) -> Dict[str, float]:\n        \"\"\"Get instance utilization metrics\"\"\"\n        try:\n            end_time = datetime.utcnow()\n            start_time = end_time - timedelta(days=7)  # Last 7 days\n            \n            # Get CPU utilization\n            cpu_response = self.cloudwatch.get_metric_statistics(\n                Namespace='AWS/EC2',\n                MetricName='CPUUtilization',\n                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],\n                StartTime=start_time,\n                EndTime=end_time,\n                Period=3600,  # 1 hour\n                Statistics=['Average']\n            )\n            \n            # Get network utilization\n            network_response = self.cloudwatch.get_metric_statistics(\n                Namespace='AWS/EC2',\n                MetricName='NetworkIn',\n                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],\n                StartTime=start_time,\n                EndTime=end_time,\n                Period=3600,\n                Statistics=['Average']\n            )\n            \n            cpu_values = [dp['Average'] for dp in cpu_response['Datapoints']]\n            network_values = [dp['Average'] for dp in network_response['Datapoints']]\n            \n            return {\n                'avg_cpu': statistics.mean(cpu_values) if cpu_values else 0,\n                'max_cpu': max(cpu_values) if cpu_values else 0,\n                'avg_network': statistics.mean(network_values) if network_values else 0,\n                'avg_memory': 50  # Would need CloudWatch agent for actual memory metrics\n            }\n            \n        except Exception as e:\n            logger.warning(f\"Could not get utilization for {instance_id}: {e}\")\n            return {'avg_cpu': 50, 'max_cpu': 80, 'avg_network': 5000, 'avg_memory': 60}\n    \n    def _estimate_instance_hourly_cost(self, instance_type: str) -> float:\n        \"\"\"Estimate hourly cost for instance type (simplified)\"\"\"\n        # Simplified pricing - in production, use AWS Pricing API\n        hourly_rates = {\n            't3.nano': 0.0052, 't3.micro': 0.0104, 't3.small': 0.0208,\n            't3.medium': 0.0416, 't3.large': 0.0832, 't3.xlarge': 0.1664,\n            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,\n            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,\n            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504\n        }\n        return hourly_rates.get(instance_type, 0.10)\n    \n    def _suggest_smaller_instance_type(self, current_type: str) -> Optional[str]:\n        \"\"\"Suggest a smaller instance type\"\"\"\n        downgrade_map = {\n            't3.large': 't3.medium',\n            't3.medium': 't3.small',\n            't3.small': 't3.micro',\n            'm5.xlarge': 'm5.large',\n            'm5.2xlarge': 'm5.xlarge',\n            'c5.xlarge': 'c5.large',\n            'c5.2xlarge': 'c5.xlarge',\n            'r5.xlarge': 'r5.large',\n            'r5.2xlarge': 'r5.xlarge'\n        }\n        return downgrade_map.get(current_type)\n    \n    def _suggest_modern_instance_type(self, current_type: str) -> str:\n        \"\"\"Suggest a modern equivalent instance type\"\"\"\n        modernization_map = {\n            't2.micro': 't3.micro',\n            't2.small': 't3.small',\n            't2.medium': 't3.medium',\n            'm4.large': 'm5.large',\n            'm4.xlarge': 'm5.xlarge',\n            'c4.large': 'c5.large',\n            'c4.xlarge': 'c5.xlarge',\n            'r4.large': 'r5.large',\n            'r4.xlarge': 'r5.xlarge'\n        }\n        return modernization_map.get(current_type, current_type)\n    \n    async def _analyze_storage_costs(self) -> List[CostOptimizationRecommendation]:\n        \"\"\"Analyze storage costs and generate recommendations\"\"\"\n        recommendations = []\n        \n        try:\n            # Analyze EBS volumes\n            volumes_response = self.ec2.describe_volumes()\n            \n            for volume in volumes_response['Volumes']:\n                volume_id = volume['VolumeId']\n                volume_type = volume['VolumeType']\n                size = volume['Size']\n                state = volume['State']\n                \n                monthly_cost = self._estimate_volume_monthly_cost(volume_type, size)\n                \n                # Check for unattached volumes\n                if state == 'available':  # Unattached\n                    recommendations.append(CostOptimizationRecommendation(\n                        id=f\"unattached_volume_{volume_id}\",\n                        title=f\"Unattached Volume: {volume_id}\",\n                        description=f\"Volume {volume_id} ({size}GB, {volume_type}) is not attached to any instance\",\n                        category=CostCategory.STORAGE,\n                        estimated_savings=monthly_cost,\n                        effort_level='low',\n                        implementation_steps=[\n                            'Verify volume is not needed',\n                            'Create snapshot if data needs to be preserved',\n                            'Delete the volume'\n                        ],\n                        priority_score=9.5\n                    ))\n                \n                # Check for non-gp3 volumes\n                elif volume_type in ['gp2', 'io1'] and size >= 100:\n                    gp3_cost = self._estimate_volume_monthly_cost('gp3', size)\n                    potential_savings = monthly_cost - gp3_cost\n                    \n                    if potential_savings > 5:  # Only recommend if savings > $5/month\n                        recommendations.append(CostOptimizationRecommendation(\n                            id=f\"convert_to_gp3_{volume_id}\",\n                            title=f\"Convert to gp3: {volume_id}\",\n                            description=f\"Convert {volume_type} volume to gp3 for cost savings\",\n                            category=CostCategory.STORAGE,\n                            estimated_savings=potential_savings,\n                            effort_level='low',\n                            implementation_steps=[\n                                'Schedule maintenance window if volume is in use',\n                                f'Modify volume type from {volume_type} to gp3',\n                                'Monitor performance after conversion'\n                            ],\n                            priority_score=7.0\n                        ))\n            \n            # Analyze snapshots\n            snapshots_response = self.ec2.describe_snapshots(OwnerIds=['self'])\n            \n            old_snapshots = []\n            for snapshot in snapshots_response['Snapshots']:\n                start_time = snapshot['StartTime']\n                age_days = (datetime.utcnow() - start_time.replace(tzinfo=None)).days\n                \n                if age_days > 90:  # Older than 90 days\n                    old_snapshots.append({\n                        'snapshot_id': snapshot['SnapshotId'],\n                        'age_days': age_days,\n                        'size': snapshot.get('VolumeSize', 0)\n                    })\n            \n            if old_snapshots:\n                total_size = sum(s['size'] for s in old_snapshots)\n                estimated_savings = total_size * 0.05  # $0.05 per GB-month\n                \n                recommendations.append(CostOptimizationRecommendation(\n                    id=\"cleanup_old_snapshots\",\n                    title=f\"Clean up {len(old_snapshots)} old snapshots\",\n                    description=f\"Remove {len(old_snapshots)} snapshots older than 90 days ({total_size}GB total)\",\n                    category=CostCategory.STORAGE,\n                    estimated_savings=estimated_savings,\n                    effort_level='low',\n                    implementation_steps=[\n                        'Review snapshot list for important data',\n                        'Delete snapshots no longer needed',\n                        'Set up lifecycle policy for future snapshots'\n                    ],\n                    priority_score=8.0\n                ))\n            \n            return recommendations\n            \n        except Exception as e:\n            logger.error(f\"Failed to analyze storage costs: {e}\")\n            return []\n    \n    def _estimate_volume_monthly_cost(self, volume_type: str, size_gb: int) -> float:\n        \"\"\"Estimate monthly cost for EBS volume\"\"\"\n        # Simplified pricing per GB-month\n        pricing = {\n            'gp2': 0.10,\n            'gp3': 0.08,\n            'io1': 0.125,\n            'io2': 0.125,\n            'st1': 0.045,\n            'sc1': 0.025\n        }\n        \n        rate = pricing.get(volume_type, 0.10)\n        return size_gb * rate\n    \n    async def _find_unused_resources(self) -> List[CostOptimizationRecommendation]:\n        \"\"\"Find unused resources that are incurring costs\"\"\"\n        recommendations = []\n        \n        try:\n            # Find unused Elastic IPs\n            eips_response = self.ec2.describe_addresses()\n            unused_eips = [eip for eip in eips_response['Addresses'] if 'InstanceId' not in eip]\n            \n            if unused_eips:\n                monthly_cost = len(unused_eips) * 3.65  # $0.005/hour * 24 * 30\n                recommendations.append(CostOptimizationRecommendation(\n                    id=\"unused_elastic_ips\",\n                    title=f\"Release {len(unused_eips)} unused Elastic IPs\",\n                    description=f\"Found {len(unused_eips)} Elastic IPs not associated with instances\",\n                    category=CostCategory.NETWORK,\n                    estimated_savings=monthly_cost,\n                    effort_level='low',\n                    implementation_steps=[\n                        'Verify EIPs are not needed',\n                        'Release unused Elastic IPs'\n                    ],\n                    priority_score=8.5\n                ))\n            \n            # Find unused load balancers (simplified check)\n            try:\n                elbv2_client = boto3.client('elbv2', region_name=self.ec2.meta.region_name)\n                lbs_response = elbv2_client.describe_load_balancers()\n                \n                unused_lbs = []\n                for lb in lbs_response['LoadBalancers']:\n                    # Check if load balancer has targets\n                    target_groups = elbv2_client.describe_target_groups(\n                        LoadBalancerArn=lb['LoadBalancerArn']\n                    )\n                    \n                    has_targets = False\n                    for tg in target_groups['TargetGroups']:\n                        targets = elbv2_client.describe_target_health(\n                            TargetGroupArn=tg['TargetGroupArn']\n                        )\n                        if targets['TargetHealthDescriptions']:\n                            has_targets = True\n                            break\n                    \n                    if not has_targets:\n                        unused_lbs.append(lb)\n                \n                if unused_lbs:\n                    monthly_cost = len(unused_lbs) * 22.5  # Approximate ALB cost\n                    recommendations.append(CostOptimizationRecommendation(\n                        id=\"unused_load_balancers\",\n                        title=f\"Remove {len(unused_lbs)} unused load balancers\",\n                        description=f\"Found {len(unused_lbs)} load balancers with no targets\",\n                        category=CostCategory.NETWORK,\n                        estimated_savings=monthly_cost,\n                        effort_level='medium',\n                        implementation_steps=[\n                            'Verify load balancers are not needed',\n                            'Update DNS records if necessary',\n                            'Delete unused load balancers'\n                        ],\n                        priority_score=7.5\n                    ))\n                    \n            except Exception as e:\n                logger.warning(f\"Could not analyze load balancers: {e}\")\n            \n            return recommendations\n            \n        except Exception as e:\n            logger.error(f\"Failed to find unused resources: {e}\")\n            return []\n    \n    def _recommendation_to_dict(self, rec: CostOptimizationRecommendation) -> Dict[str, Any]:\n        \"\"\"Convert recommendation to dictionary\"\"\"\n        return {\n            'id': rec.id,\n            'title': rec.title,\n            'description': rec.description,\n            'category': rec.category.value,\n            'estimated_savings': rec.estimated_savings,\n            'effort_level': rec.effort_level,\n            'implementation_steps': rec.implementation_steps,\n            'priority_score': rec.priority_score\n        }"