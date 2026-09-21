#!/usr/bin/env python3
"""
ActiveLog Cost Optimizer and Predictor
Intelligent cost analysis, prediction, and optimization recommendations
"""

import json
import boto3
import datetime
import argparse
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Unicode symbols
SYMBOLS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'money': '💰',
    'chart': '📊',
    'lightbulb': '💡',
    'rocket': '🚀'
}

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class CostPrediction:
    current_monthly: float
    predicted_monthly: float
    predicted_yearly: float
    confidence: float
    trend: str
    factors: List[str]

@dataclass
class OptimizationRecommendation:
    title: str
    description: str
    potential_savings_monthly: float
    potential_savings_yearly: float
    implementation_effort: str
    risk_level: RiskLevel
    priority: Priority
    category: str
    steps: List[str]
    estimated_time: str

@dataclass
class ResourceUsage:
    resource_type: str
    resource_id: str
    utilization: float
    cost_monthly: float
    right_size_recommendation: Optional[str]
    potential_savings: float

class ActiveLogCostOptimizer:
    def __init__(self, environment: str = "beta", region: str = "us-west-2"):
        self.environment = environment
        self.region = region
        self.session = boto3.Session(region_name=region)
        
        # AWS clients
        self.ec2 = self.session.client('ec2')
        self.cloudwatch = self.session.client('cloudwatch')
        self.ce = self.session.client('ce')  # Cost Explorer
        self.pricing = self.session.client('pricing', region_name='us-east-1')
        self.autoscaling = self.session.client('autoscaling')
        self.elbv2 = self.session.client('elbv2')
        self.rds = self.session.client('rds')
        self.s3 = self.session.client('s3')
        
        # Pricing data cache
        self.pricing_cache = {}
        
        print(f"{SYMBOLS['info']} {Colors.OKBLUE}ActiveLog Cost Optimizer initialized{Colors.ENDC}")
        print(f"   Environment: {Colors.BOLD}{environment}{Colors.ENDC}")
        print(f"   Region: {Colors.BOLD}{region}{Colors.ENDC}")
        print()

    def get_current_costs(self) -> Dict:
        """Get current AWS costs using Cost Explorer"""
        print(f"{SYMBOLS['chart']} {Colors.OKBLUE}Fetching current cost data...{Colors.ENDC}")
        
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=30)
        
        try:
            response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'TAG', 'Key': 'Environment'}
                ]
            )
            
            total_cost = 0
            service_costs = {}
            
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    total_cost += cost
                    service_costs[service] = service_costs.get(service, 0) + cost
            
            return {
                'total_monthly': total_cost,
                'by_service': service_costs,
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            print(f"{SYMBOLS['warning']} {Colors.WARNING}Could not fetch cost data: {e}{Colors.ENDC}")
            return {'total_monthly': 0, 'by_service': {}, 'error': str(e)}

    def analyze_resource_utilization(self) -> List[ResourceUsage]:
        """Analyze resource utilization and identify optimization opportunities"""
        print(f"{SYMBOLS['chart']} {Colors.OKBLUE}Analyzing resource utilization...{Colors.ENDC}")
        
        resources = []
        
        # Analyze EC2 instances
        try:
            instances = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Environment', 'Values': [self.environment]},
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    
                    # Get CPU utilization from CloudWatch
                    cpu_util = self.get_cpu_utilization(instance_id)
                    
                    # Estimate monthly cost
                    monthly_cost = self.estimate_instance_cost(instance_type)
                    
                    # Right-sizing recommendation
                    right_size, savings = self.get_right_size_recommendation(
                        instance_type, cpu_util
                    )
                    
                    resources.append(ResourceUsage(
                        resource_type='EC2',
                        resource_id=instance_id,
                        utilization=cpu_util,
                        cost_monthly=monthly_cost,
                        right_size_recommendation=right_size,
                        potential_savings=savings
                    ))
                    
        except Exception as e:
            print(f"{SYMBOLS['warning']} {Colors.WARNING}Error analyzing EC2: {e}{Colors.ENDC}")
        
        # Analyze RDS instances
        try:
            rds_instances = self.rds.describe_db_instances()
            
            for db in rds_instances['DBInstances']:
                if self.environment in db['DBInstanceIdentifier']:
                    db_id = db['DBInstanceIdentifier']
                    db_class = db['DBInstanceClass']
                    
                    # Get CPU utilization
                    cpu_util = self.get_rds_cpu_utilization(db_id)
                    
                    # Estimate cost
                    monthly_cost = self.estimate_rds_cost(db_class)
                    
                    # Right-sizing recommendation
                    right_size, savings = self.get_rds_right_size_recommendation(
                        db_class, cpu_util
                    )
                    
                    resources.append(ResourceUsage(
                        resource_type='RDS',
                        resource_id=db_id,
                        utilization=cpu_util,
                        cost_monthly=monthly_cost,
                        right_size_recommendation=right_size,
                        potential_savings=savings
                    ))
                    
        except Exception as e:
            print(f"{SYMBOLS['warning']} {Colors.WARNING}Error analyzing RDS: {e}{Colors.ENDC}")
        
        return resources

    def get_cpu_utilization(self, instance_id: str, days: int = 7) -> float:
        """Get average CPU utilization for an instance"""
        try:
            end_time = datetime.datetime.utcnow()
            start_time = end_time - datetime.timedelta(days=days)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                return np.mean([dp['Average'] for dp in response['Datapoints']])
            return 0
            
        except Exception:
            return 0

    def get_rds_cpu_utilization(self, db_id: str, days: int = 7) -> float:
        """Get average CPU utilization for RDS instance"""
        try:
            end_time = datetime.datetime.utcnow()
            start_time = end_time - datetime.timedelta(days=days)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                return np.mean([dp['Average'] for dp in response['Datapoints']])
            return 0
            
        except Exception:
            return 0

    def estimate_instance_cost(self, instance_type: str) -> float:
        """Estimate monthly cost for EC2 instance"""
        # Simplified pricing - in real implementation, use AWS Pricing API
        pricing_map = {
            't3.micro': 8.76, 't3.small': 17.52, 't3.medium': 35.04,
            't3.large': 70.08, 't3.xlarge': 140.16, 't3.2xlarge': 280.32,
            'c5.large': 61.92, 'c5.xlarge': 123.84, 'c5.2xlarge': 247.68,
            'm5.large': 69.12, 'm5.xlarge': 138.24, 'm5.2xlarge': 276.48,
            'g4dn.xlarge': 376.32
        }
        return pricing_map.get(instance_type, 100)

    def estimate_rds_cost(self, db_class: str) -> float:
        """Estimate monthly cost for RDS instance"""
        # Simplified RDS pricing
        pricing_map = {
            'db.t3.micro': 14.76, 'db.t3.small': 29.52, 'db.t3.medium': 59.04,
            'db.t3.large': 118.08, 'db.t3.xlarge': 236.16,
            'db.m5.large': 138.24, 'db.m5.xlarge': 276.48
        }
        return pricing_map.get(db_class, 150)

    def get_right_size_recommendation(self, instance_type: str, cpu_util: float) -> Tuple[Optional[str], float]:
        """Get right-sizing recommendation for EC2 instance"""
        if cpu_util < 10:
            # Very low utilization - recommend smaller instance
            downsize_map = {
                't3.large': 't3.medium',
                't3.medium': 't3.small',
                't3.small': 't3.micro',
                'c5.xlarge': 'c5.large',
                'c5.large': 't3.large',
                'm5.xlarge': 'm5.large',
                'm5.large': 't3.large'
            }
            if instance_type in downsize_map:
                new_type = downsize_map[instance_type]
                current_cost = self.estimate_instance_cost(instance_type)
                new_cost = self.estimate_instance_cost(new_type)
                savings = current_cost - new_cost
                return new_type, savings
                
        elif cpu_util > 80:
            # High utilization - recommend larger instance
            upsize_map = {
                't3.micro': 't3.small',
                't3.small': 't3.medium',
                't3.medium': 't3.large',
                't3.large': 'c5.large',
                'c5.large': 'c5.xlarge'
            }
            if instance_type in upsize_map:
                new_type = upsize_map[instance_type]
                return new_type, 0  # No savings, but performance improvement
        
        return None, 0

    def get_rds_right_size_recommendation(self, db_class: str, cpu_util: float) -> Tuple[Optional[str], float]:
        """Get right-sizing recommendation for RDS instance"""
        if cpu_util < 15:
            downsize_map = {
                'db.t3.large': 'db.t3.medium',
                'db.t3.medium': 'db.t3.small',
                'db.t3.small': 'db.t3.micro',
                'db.m5.xlarge': 'db.m5.large',
                'db.m5.large': 'db.t3.large'
            }
            if db_class in downsize_map:
                new_class = downsize_map[db_class]
                current_cost = self.estimate_rds_cost(db_class)
                new_cost = self.estimate_rds_cost(new_class)
                savings = current_cost - new_cost
                return new_class, savings
        
        return None, 0

    def predict_costs(self, months_ahead: int = 3) -> CostPrediction:
        """Predict future costs based on current trends"""
        print(f"{SYMBOLS['chart']} {Colors.OKBLUE}Predicting costs for next {months_ahead} months...{Colors.ENDC}")
        
        try:
            # Get historical costs for trend analysis
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=90)  # 3 months history
            
            response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost']
            )
            
            costs = []
            for result in response['ResultsByTime']:
                total = sum(float(group['Metrics']['BlendedCost']['Amount']) 
                           for group in result['Groups'])
                costs.append(total)
            
            if len(costs) < 2:
                # Not enough data, use current estimate
                current_monthly = self.estimate_current_monthly_cost()
                return CostPrediction(
                    current_monthly=current_monthly,
                    predicted_monthly=current_monthly,
                    predicted_yearly=current_monthly * 12,
                    confidence=0.5,
                    trend="stable",
                    factors=["Insufficient historical data"]
                )
            
            # Simple linear regression for trend prediction
            x = np.arange(len(costs))
            coeffs = np.polyfit(x, costs, 1)
            trend_slope = coeffs[0]
            
            # Predict future cost
            future_x = len(costs) + months_ahead - 1
            predicted_monthly = np.polyval(coeffs, future_x)
            current_monthly = costs[-1] if costs else predicted_monthly
            
            # Determine trend
            trend = "stable"
            if trend_slope > current_monthly * 0.05:  # 5% increase
                trend = "increasing"
            elif trend_slope < -current_monthly * 0.05:  # 5% decrease
                trend = "decreasing"
            
            # Calculate confidence based on data consistency
            variance = np.var(costs)
            confidence = max(0.3, min(0.9, 1.0 - (variance / (current_monthly ** 2))))
            
            # Identify cost factors
            factors = self.identify_cost_factors()
            
            return CostPrediction(
                current_monthly=current_monthly,
                predicted_monthly=max(0, predicted_monthly),
                predicted_yearly=max(0, predicted_monthly * 12),
                confidence=confidence,
                trend=trend,
                factors=factors
            )
            
        except Exception as e:
            print(f"{SYMBOLS['warning']} {Colors.WARNING}Error predicting costs: {e}{Colors.ENDC}")
            current_monthly = self.estimate_current_monthly_cost()
            return CostPrediction(
                current_monthly=current_monthly,
                predicted_monthly=current_monthly,
                predicted_yearly=current_monthly * 12,
                confidence=0.3,
                trend="unknown",
                factors=[f"Error in prediction: {str(e)}"]
            )

    def estimate_current_monthly_cost(self) -> float:
        """Estimate current monthly cost based on running resources"""
        total_cost = 0
        
        try:
            # EC2 instances
            instances = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Environment', 'Values': [self.environment]},
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    cost = self.estimate_instance_cost(instance['InstanceType'])
                    total_cost += cost
            
            # RDS instances
            rds_instances = self.rds.describe_db_instances()
            for db in rds_instances['DBInstances']:
                if self.environment in db['DBInstanceIdentifier']:
                    cost = self.estimate_rds_cost(db['DBInstanceClass'])
                    total_cost += cost
            
            # Add estimates for other services (ELB, S3, etc.)
            total_cost += 50  # Rough estimate for other services
            
        except Exception:
            total_cost = 100  # Fallback estimate
        
        return total_cost

    def identify_cost_factors(self) -> List[str]:
        """Identify factors affecting cost trends"""
        factors = []
        
        try:
            # Check for scaling activities
            asgs = self.autoscaling.describe_auto_scaling_groups()
            for asg in asgs['AutoScalingGroups']:
                if any(tag['Key'] == 'Environment' and tag['Value'] == self.environment 
                       for tag in asg['Tags']):
                    if asg['DesiredCapacity'] > asg['MinSize']:
                        factors.append("Auto Scaling Group active scaling")
            
            # Check for high utilization instances
            instances = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Environment', 'Values': [self.environment]},
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            high_util_count = 0
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    cpu_util = self.get_cpu_utilization(instance['InstanceId'])
                    if cpu_util > 70:
                        high_util_count += 1
            
            if high_util_count > 0:
                factors.append(f"{high_util_count} high-utilization instances")
            
            # Add seasonal factors
            current_month = datetime.datetime.now().month
            if current_month in [11, 12, 1]:  # Holiday season
                factors.append("Holiday season traffic patterns")
            
        except Exception:
            factors.append("Unable to analyze cost factors")
        
        return factors or ["Standard usage patterns"]

    def generate_optimization_recommendations(self, resources: List[ResourceUsage]) -> List[OptimizationRecommendation]:
        """Generate intelligent optimization recommendations"""
        print(f"{SYMBOLS['lightbulb']} {Colors.OKBLUE}Generating optimization recommendations...{Colors.ENDC}")
        
        recommendations = []
        
        # Right-sizing recommendations
        total_rightsizing_savings = sum(r.potential_savings for r in resources if r.potential_savings > 0)
        
        if total_rightsizing_savings > 20:  # $20+ potential savings
            over_provisioned = [r for r in resources if r.utilization < 30 and r.potential_savings > 0]
            
            recommendations.append(OptimizationRecommendation(
                title="Right-size Over-provisioned Resources",
                description=f"Reduce instance sizes for {len(over_provisioned)} under-utilized resources",
                potential_savings_monthly=total_rightsizing_savings,
                potential_savings_yearly=total_rightsizing_savings * 12,
                implementation_effort="Medium",
                risk_level=RiskLevel.MEDIUM,
                priority=Priority.HIGH if total_rightsizing_savings > 100 else Priority.MEDIUM,
                category="Right-sizing",
                steps=[
                    "Review resource utilization metrics",
                    "Test application performance with smaller instances",
                    "Gradually downsize instances during low-traffic periods",
                    "Monitor performance after changes"
                ],
                estimated_time="2-4 hours"
            ))
        
        # Auto Scaling recommendations
        try:
            asgs = self.autoscaling.describe_auto_scaling_groups()
            static_capacity_asgs = []
            
            for asg in asgs['AutoScalingGroups']:
                if any(tag['Key'] == 'Environment' and tag['Value'] == self.environment 
                       for tag in asg['Tags']):
                    if asg['MinSize'] == asg['MaxSize'] == asg['DesiredCapacity']:
                        static_capacity_asgs.append(asg['AutoScalingGroupName'])
            
            if static_capacity_asgs:
                potential_savings = len(static_capacity_asgs) * 50  # Estimate
                recommendations.append(OptimizationRecommendation(
                    title="Enable Dynamic Auto Scaling",
                    description=f"Configure dynamic scaling for {len(static_capacity_asgs)} ASGs with static capacity",
                    potential_savings_monthly=potential_savings,
                    potential_savings_yearly=potential_savings * 12,
                    implementation_effort="Low",
                    risk_level=RiskLevel.LOW,
                    priority=Priority.MEDIUM,
                    category="Auto Scaling",
                    steps=[
                        "Review current traffic patterns",
                        "Set appropriate scaling policies",
                        "Configure CloudWatch alarms",
                        "Test scaling behavior"
                    ],
                    estimated_time="1-2 hours"
                ))
        except Exception:
            pass
        
        # Spot Instance recommendations
        on_demand_instances = []
        try:
            instances = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Environment', 'Values': [self.environment]},
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    # Check if it's not already a spot instance
                    if instance.get('SpotInstanceRequestId') is None:
                        on_demand_instances.append(instance)
            
            if on_demand_instances and self.environment != "production":
                potential_savings = len(on_demand_instances) * 30  # ~50-70% savings estimate
                recommendations.append(OptimizationRecommendation(
                    title="Use Spot Instances for Non-Production",
                    description=f"Convert {len(on_demand_instances)} On-Demand instances to Spot instances",
                    potential_savings_monthly=potential_savings,
                    potential_savings_yearly=potential_savings * 12,
                    implementation_effort="Medium",
                    risk_level=RiskLevel.MEDIUM,
                    priority=Priority.HIGH if potential_savings > 100 else Priority.MEDIUM,
                    category="Instance Types",
                    steps=[
                        "Identify fault-tolerant workloads",
                        "Create Spot Fleet or ASG with mixed instances",
                        "Implement graceful handling of interruptions",
                        "Monitor cost savings and availability"
                    ],
                    estimated_time="3-5 hours"
                ))
        except Exception:
            pass
        
        # Reserved Instance recommendations
        if self.environment == "production":
            steady_instances = [r for r in resources if r.resource_type == 'EC2' and r.utilization > 50]
            if len(steady_instances) >= 2:
                potential_savings = len(steady_instances) * 25  # ~30-40% savings estimate
                recommendations.append(OptimizationRecommendation(
                    title="Purchase Reserved Instances",
                    description=f"Buy 1-year Reserved Instances for {len(steady_instances)} steady-state instances",
                    potential_savings_monthly=potential_savings,
                    potential_savings_yearly=potential_savings * 12,
                    implementation_effort="Low",
                    risk_level=RiskLevel.LOW,
                    priority=Priority.MEDIUM,
                    category="Reserved Capacity",
                    steps=[
                        "Analyze instance usage patterns",
                        "Purchase appropriate Reserved Instances",
                        "Monitor utilization and modify if needed"
                    ],
                    estimated_time="30 minutes"
                ))
        
        # Scheduled Scaling recommendations
        recommendations.append(OptimizationRecommendation(
            title="Implement Scheduled Scaling",
            description="Automatically scale down resources during off-hours",
            potential_savings_monthly=75,
            potential_savings_yearly=900,
            implementation_effort="Low",
            risk_level=RiskLevel.LOW,
            priority=Priority.MEDIUM,
            category="Scheduling",
            steps=[
                "Analyze traffic patterns to identify off-hours",
                "Create scheduled scaling policies",
                "Configure weekend/holiday scaling",
                "Monitor and adjust schedules"
            ],
            estimated_time="1 hour"
        ))
        
        # Storage optimization
        recommendations.append(OptimizationRecommendation(
            title="Optimize Storage with Intelligent Tiering",
            description="Enable S3 Intelligent-Tiering and EBS GP3 optimization",
            potential_savings_monthly=25,
            potential_savings_yearly=300,
            implementation_effort="Low",
            risk_level=RiskLevel.LOW,
            priority=Priority.LOW,
            category="Storage",
            steps=[
                "Enable S3 Intelligent-Tiering on buckets",
                "Convert EBS volumes to GP3 where appropriate",
                "Review and optimize snapshot retention"
            ],
            estimated_time="30 minutes"
        ))
        
        # Sort by potential savings and priority
        recommendations.sort(key=lambda x: (x.priority.value, -x.potential_savings_monthly))
        
        return recommendations

    def create_cost_report(self, output_file: str = None) -> Dict:
        """Create comprehensive cost analysis report"""
        print(f"{SYMBOLS['rocket']} {Colors.OKBLUE}Generating comprehensive cost report...{Colors.ENDC}")
        
        # Gather all analysis data
        current_costs = self.get_current_costs()
        resources = self.analyze_resource_utilization()
        predictions = self.predict_costs()
        recommendations = self.generate_optimization_recommendations(resources)
        
        # Create report data
        report = {
            'metadata': {
                'generated_at': datetime.datetime.now().isoformat(),
                'environment': self.environment,
                'region': self.region,
                'analysis_period': '30 days'
            },
            'current_costs': current_costs,
            'cost_predictions': asdict(predictions),
            'resources': [asdict(r) for r in resources],
            'recommendations': [asdict(r) for r in recommendations],
            'summary': {
                'total_monthly_cost': current_costs.get('total_monthly', 0),
                'predicted_monthly_cost': predictions.predicted_monthly,
                'total_potential_savings': sum(r.potential_savings_monthly for r in recommendations),
                'high_priority_recommendations': len([r for r in recommendations if r.priority == Priority.HIGH]),
                'resource_count': len(resources),
                'under_utilized_resources': len([r for r in resources if r.utilization < 30])
            }
        }
        
        # Save report to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"{SYMBOLS['success']} {Colors.OKGREEN}Report saved to: {output_file}{Colors.ENDC}")
        
        return report

    def display_report(self, report: Dict):
        """Display cost report in terminal with colors and formatting"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}💰 ACTIVELOG COST OPTIMIZATION REPORT 💰{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        # Summary section
        summary = report['summary']
        print(f"{Colors.BOLD}{SYMBOLS['chart']} COST SUMMARY{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Environment:{Colors.ENDC} {Colors.BOLD}{self.environment.upper()}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Current Monthly Cost:{Colors.ENDC} {Colors.BOLD}${summary['total_monthly_cost']:.2f}{Colors.ENDC}")
        
        predictions = report['cost_predictions']
        trend_color = Colors.OKGREEN if predictions['trend'] == 'decreasing' else Colors.WARNING if predictions['trend'] == 'increasing' else Colors.OKBLUE
        print(f"{Colors.OKCYAN}Predicted Monthly Cost:{Colors.ENDC} {Colors.BOLD}{trend_color}${predictions['predicted_monthly']:.2f}{Colors.ENDC} ({predictions['trend']})")
        print(f"{Colors.OKCYAN}Potential Monthly Savings:{Colors.ENDC} {Colors.BOLD}{Colors.OKGREEN}${summary['total_potential_savings']:.2f}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Potential Yearly Savings:{Colors.ENDC} {Colors.BOLD}{Colors.OKGREEN}${summary['total_potential_savings'] * 12:.2f}{Colors.ENDC}")
        print()
        
        # Resource utilization
        print(f"{Colors.BOLD}{SYMBOLS['info']} RESOURCE ANALYSIS{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Total Resources Analyzed:{Colors.ENDC} {summary['resource_count']}")
        print(f"{Colors.OKCYAN}Under-utilized Resources:{Colors.ENDC} {Colors.WARNING}{summary['under_utilized_resources']}{Colors.ENDC}")
        print()
        
        # Top recommendations
        recommendations = [OptimizationRecommendation(**r) for r in report['recommendations']]
        high_priority = [r for r in recommendations if r.priority == Priority.HIGH]
        
        print(f"{Colors.BOLD}{SYMBOLS['lightbulb']} TOP OPTIMIZATION RECOMMENDATIONS{Colors.ENDC}")
        
        for i, rec in enumerate(recommendations[:5], 1):
            priority_color = Colors.FAIL if rec.priority == Priority.HIGH else Colors.WARNING if rec.priority == Priority.MEDIUM else Colors.OKBLUE
            risk_color = Colors.FAIL if rec.risk_level == RiskLevel.HIGH else Colors.WARNING if rec.risk_level == RiskLevel.MEDIUM else Colors.OKGREEN
            
            print(f"\n{Colors.BOLD}{i}. {rec.title}{Colors.ENDC}")
            print(f"   {Colors.OKCYAN}Priority:{Colors.ENDC} {priority_color}{rec.priority.value.upper()}{Colors.ENDC}")
            print(f"   {Colors.OKCYAN}Potential Savings:{Colors.ENDC} {Colors.OKGREEN}${rec.potential_savings_monthly:.2f}/month{Colors.ENDC}")
            print(f"   {Colors.OKCYAN}Risk Level:{Colors.ENDC} {risk_color}{rec.risk_level.value.upper()}{Colors.ENDC}")
            print(f"   {Colors.OKCYAN}Implementation:{Colors.ENDC} {rec.implementation_effort} ({rec.estimated_time})")
            print(f"   {Colors.OKCYAN}Description:{Colors.ENDC} {rec.description}")
        
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}💡 Total potential annual savings: ${summary['total_potential_savings'] * 12:.2f}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

    def create_cost_dashboard(self, report: Dict, output_file: str = "cost_dashboard.png"):
        """Create visual cost dashboard"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'ActiveLog Cost Optimization Dashboard - {self.environment.upper()}', 
                        fontsize=16, fontweight='bold')
            
            # Current vs Predicted costs
            current_cost = report['summary']['total_monthly_cost']
            predicted_cost = report['cost_predictions']['predicted_monthly']
            savings = report['summary']['total_potential_savings']
            optimized_cost = current_cost - savings
            
            costs = [current_cost, predicted_cost, optimized_cost]
            labels = ['Current', 'Predicted', 'Optimized']
            colors = ['#ff6b6b', '#feca57', '#48cae4']
            
            ax1.bar(labels, costs, color=colors)
            ax1.set_title('Monthly Cost Comparison')
            ax1.set_ylabel('Cost ($)')
            
            # Add value labels on bars
            for i, v in enumerate(costs):
                ax1.text(i, v + 5, f'${v:.0f}', ha='center', fontweight='bold')
            
            # Resource utilization distribution
            resources = [OptimizationRecommendation(**r) for r in report.get('resources', [])]
            utilizations = [r.utilization for r in resources if hasattr(r, 'utilization')]
            
            if utilizations:
                ax2.hist(utilizations, bins=10, alpha=0.7, color='#54a0ff')
                ax2.set_title('Resource Utilization Distribution')
                ax2.set_xlabel('CPU Utilization (%)')
                ax2.set_ylabel('Number of Resources')
                ax2.axvline(x=30, color='red', linestyle='--', label='Under-utilized threshold')
                ax2.legend()
            else:
                ax2.text(0.5, 0.5, 'No utilization data available', ha='center', va='center', transform=ax2.transAxes)
                ax2.set_title('Resource Utilization Distribution')
            
            # Savings by category
            recommendations = [OptimizationRecommendation(**r) for r in report['recommendations']]
            categories = {}
            for rec in recommendations:
                categories[rec.category] = categories.get(rec.category, 0) + rec.potential_savings_monthly
            
            if categories:
                ax3.pie(categories.values(), labels=categories.keys(), autopct='%1.1f%%', startangle=90)
                ax3.set_title('Potential Savings by Category')
            
            # Priority vs Savings scatter
            priority_map = {'low': 1, 'medium': 2, 'high': 3, 'urgent': 4}
            x_vals = [priority_map[rec.priority.value] for rec in recommendations]
            y_vals = [rec.potential_savings_monthly for rec in recommendations]
            colors_scatter = ['red' if rec.risk_level == RiskLevel.HIGH else 
                            'orange' if rec.risk_level == RiskLevel.MEDIUM else 'green' 
                            for rec in recommendations]
            
            ax4.scatter(x_vals, y_vals, c=colors_scatter, alpha=0.6, s=100)
            ax4.set_title('Recommendations: Priority vs Savings')
            ax4.set_xlabel('Priority Level')
            ax4.set_ylabel('Monthly Savings ($)')
            ax4.set_xticks([1, 2, 3, 4])
            ax4.set_xticklabels(['Low', 'Medium', 'High', 'Urgent'])
            
            # Add legend for risk levels
            red_patch = mpatches.Patch(color='red', label='High Risk')
            orange_patch = mpatches.Patch(color='orange', label='Medium Risk')
            green_patch = mpatches.Patch(color='green', label='Low Risk')
            ax4.legend(handles=[red_patch, orange_patch, green_patch])
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"{SYMBOLS['success']} {Colors.OKGREEN}Cost dashboard saved to: {output_file}{Colors.ENDC}")
            
        except ImportError:
            print(f"{SYMBOLS['warning']} {Colors.WARNING}matplotlib not available, skipping dashboard creation{Colors.ENDC}")
        except Exception as e:
            print(f"{SYMBOLS['error']} {Colors.FAIL}Error creating dashboard: {e}{Colors.ENDC}")

def main():
    parser = argparse.ArgumentParser(description='ActiveLog Cost Optimizer and Predictor')
    parser.add_argument('--environment', '-e', default='beta', help='Environment to analyze (default: beta)')
    parser.add_argument('--region', '-r', default='us-west-2', help='AWS region (default: us-west-2)')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--dashboard', '-d', action='store_true', help='Generate visual dashboard')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress detailed output')
    
    args = parser.parse_args()
    
    try:
        optimizer = ActiveLogCostOptimizer(args.environment, args.region)
        
        # Generate comprehensive report
        report = optimizer.create_cost_report(args.output)
        
        if not args.quiet:
            optimizer.display_report(report)
        
        if args.dashboard:
            optimizer.create_cost_dashboard(report)
        
        # Exit with code based on potential savings
        total_savings = report['summary']['total_potential_savings']
        if total_savings > 100:
            print(f"\n{SYMBOLS['money']} {Colors.WARNING}HIGH SAVINGS POTENTIAL: ${total_savings:.2f}/month{Colors.ENDC}")
            return 2
        elif total_savings > 50:
            print(f"\n{SYMBOLS['money']} {Colors.OKBLUE}MODERATE SAVINGS POTENTIAL: ${total_savings:.2f}/month{Colors.ENDC}")
            return 1
        else:
            print(f"\n{SYMBOLS['success']} {Colors.OKGREEN}COSTS ARE WELL OPTIMIZED{Colors.ENDC}")
            return 0
            
    except KeyboardInterrupt:
        print(f"\n{SYMBOLS['warning']} {Colors.WARNING}Cost analysis interrupted by user{Colors.ENDC}")
        return 130
    except Exception as e:
        print(f"\n{SYMBOLS['error']} {Colors.FAIL}Error: {e}{Colors.ENDC}")
        return 1

if __name__ == "__main__":
    exit(main())