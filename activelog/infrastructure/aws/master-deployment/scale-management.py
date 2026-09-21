#!/usr/bin/env python3
"""
ActiveLog.AI Auto-Scaling Management System
Implements intelligent scaling based on load, cost optimization, and domain-specific requirements
"""

import boto3
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScalingConfig:
    """Configuration for auto-scaling behavior"""
    min_instances: int
    max_instances: int
    target_cpu: int
    scale_up_threshold: int
    scale_down_threshold: int
    cooldown_period: int
    instance_types: List[str]  # Ordered from smallest to largest

@dataclass
class DomainConfig:
    """Domain-specific configuration"""
    name: str
    scaling_config: ScalingConfig
    peak_hours: List[int]  # Hours of day (0-23) when traffic is highest
    timezone: str
    gpu_enabled: bool
    cost_priority: str  # 'cost' or 'performance'

class ActiveLogAutoScaler:
    def __init__(self, region='us-east-1'):
        self.region = region
        self.ec2 = boto3.client('ec2', region_name=region)
        self.autoscaling = boto3.client('autoscaling', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.pricing = boto3.client('pricing', region_name='us-east-1')  # Pricing API only in us-east-1
        
        # Domain configurations
        self.domain_configs = {
            'PersonalLog': DomainConfig(
                name='PersonalLog',
                scaling_config=ScalingConfig(
                    min_instances=1,
                    max_instances=3,
                    target_cpu=60,
                    scale_up_threshold=75,
                    scale_down_threshold=25,
                    cooldown_period=300,
                    instance_types=['t3.micro', 't3.small', 't3.medium']
                ),
                peak_hours=[8, 9, 17, 18, 19, 20, 21],
                timezone='UTC',
                gpu_enabled=False,
                cost_priority='cost'
            ),
            'MakerLog': DomainConfig(
                name='MakerLog', 
                scaling_config=ScalingConfig(
                    min_instances=2,
                    max_instances=8,
                    target_cpu=65,
                    scale_up_threshold=70,
                    scale_down_threshold=30,
                    cooldown_period=240,
                    instance_types=['t3.small', 't3.medium', 't3.large', 'c5.large']
                ),
                peak_hours=[6, 7, 8, 9, 18, 19, 20, 21, 22],
                timezone='UTC',
                gpu_enabled=True,
                cost_priority='performance'
            ),
            'BusinessLog': DomainConfig(
                name='BusinessLog',
                scaling_config=ScalingConfig(
                    min_instances=3,
                    max_instances=15,
                    target_cpu=55,
                    scale_up_threshold=65,
                    scale_down_threshold=35,
                    cooldown_period=180,
                    instance_types=['t3.medium', 't3.large', 'c5.large', 'c5.xlarge']
                ),
                peak_hours=[8, 9, 10, 11, 13, 14, 15, 16, 17],  # Business hours
                timezone='UTC',
                gpu_enabled=False,
                cost_priority='performance'
            ),
            'DMLog': DomainConfig(
                name='DMLog',
                scaling_config=ScalingConfig(
                    min_instances=1,
                    max_instances=5,
                    target_cpu=70,
                    scale_up_threshold=80,
                    scale_down_threshold=20,
                    cooldown_period=300,
                    instance_types=['t3.medium', 't3.large', 'g4dn.xlarge', 'g4dn.2xlarge']
                ),
                peak_hours=[17, 18, 19, 20, 21, 22, 23],  # Evening gaming hours
                timezone='UTC',
                gpu_enabled=True,
                cost_priority='performance'
            )
        }

    def scale_instance(self, server_name: str, load_percentage: float) -> Dict:
        """
        Main scaling logic as requested in the requirements
        """
        domain = server_name.split('-')[0] if '-' in server_name else server_name
        
        if domain not in self.domain_configs:
            logger.warning(f"No configuration found for domain: {domain}")
            return {'action': 'none', 'reason': 'no_config'}
        
        config = self.domain_configs[domain]
        current_hour = datetime.now().hour
        is_peak_hours = current_hour in config.peak_hours
        
        # Get current instance info
        current_instances = self.get_current_instances(server_name)
        current_type = self.get_current_instance_type(server_name)
        
        if load_percentage > config.scaling_config.scale_up_threshold:
            return self._scale_up(server_name, current_type, current_instances, config, is_peak_hours)
        elif load_percentage < config.scaling_config.scale_down_threshold and not is_peak_hours:
            return self._scale_down(server_name, current_type, current_instances, config)
        
        return {'action': 'none', 'reason': 'within_thresholds'}

    def _scale_up(self, server_name: str, current_type: str, current_instances: int, 
                  config: DomainConfig, is_peak_hours: bool) -> Dict:
        """Scale up logic"""
        
        # First try to add more instances if we're below max
        if current_instances < config.scaling_config.max_instances:
            new_capacity = min(current_instances + 1, config.scaling_config.max_instances)
            self.update_auto_scaling_group_capacity(server_name, new_capacity)
            return {
                'action': 'scale_out',
                'from_instances': current_instances,
                'to_instances': new_capacity,
                'reason': 'high_load'
            }
        
        # If at max instances, try to upgrade instance type
        current_type_index = None
        instance_types = config.scaling_config.instance_types
        
        try:
            current_type_index = instance_types.index(current_type)
        except ValueError:
            logger.warning(f"Current instance type {current_type} not in scaling config")
            return {'action': 'none', 'reason': 'unknown_instance_type'}
        
        if current_type_index < len(instance_types) - 1:
            new_type = instance_types[current_type_index + 1]
            self.resize_to(server_name, new_type)
            return {
                'action': 'scale_up',
                'from_type': current_type,
                'to_type': new_type,
                'reason': 'high_load_max_instances'
            }
        
        return {'action': 'none', 'reason': 'max_capacity_reached'}

    def _scale_down(self, server_name: str, current_type: str, current_instances: int,
                    config: DomainConfig) -> Dict:
        """Scale down logic"""
        
        # First try to remove instances if we're above min
        if current_instances > config.scaling_config.min_instances:
            new_capacity = max(current_instances - 1, config.scaling_config.min_instances)
            self.update_auto_scaling_group_capacity(server_name, new_capacity)
            return {
                'action': 'scale_in',
                'from_instances': current_instances,
                'to_instances': new_capacity,
                'reason': 'low_load'
            }
        
        # If at min instances, try to downgrade instance type
        instance_types = config.scaling_config.instance_types
        
        try:
            current_type_index = instance_types.index(current_type)
        except ValueError:
            return {'action': 'none', 'reason': 'unknown_instance_type'}
        
        if current_type_index > 0:
            new_type = instance_types[current_type_index - 1]
            self.downgrade_instance(server_name, new_type)
            return {
                'action': 'scale_down',
                'from_type': current_type,
                'to_type': new_type,
                'reason': 'low_load_cost_optimization'
            }
        
        return {'action': 'none', 'reason': 'min_capacity_reached'}

    def resize_to(self, server_name: str, new_instance_type: str):
        """Resize instances to new type"""
        logger.info(f"Resizing {server_name} to {new_instance_type}")
        
        try:
            # Update launch template with new instance type
            self.update_launch_template(server_name, new_instance_type)
            
            # Trigger instance refresh to apply new configuration
            self.trigger_instance_refresh(server_name)
            
            logger.info(f"Successfully initiated resize of {server_name} to {new_instance_type}")
            
        except Exception as e:
            logger.error(f"Failed to resize {server_name}: {str(e)}")
            raise

    def downgrade_instance(self, server_name: str, new_instance_type: str):
        """Downgrade to smaller instance type"""
        logger.info(f"Downgrading {server_name} to {new_instance_type} for cost savings")
        self.resize_to(server_name, new_instance_type)

    def get_current_instances(self, server_name: str) -> int:
        """Get current number of running instances"""
        try:
            asg_name = f"activelog-ai-{server_name}-asg"
            response = self.autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg_name]
            )
            
            if response['AutoScalingGroups']:
                return response['AutoScalingGroups'][0]['DesiredCapacity']
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get instance count for {server_name}: {str(e)}")
            return 0

    def get_current_instance_type(self, server_name: str) -> str:
        """Get current instance type from launch template"""
        try:
            template_name = f"activelog-ai-{server_name}-template"
            response = self.ec2.describe_launch_template_versions(
                LaunchTemplateName=template_name,
                Versions=['$Latest']
            )
            
            if response['LaunchTemplateVersions']:
                return response['LaunchTemplateVersions'][0]['LaunchTemplateData']['InstanceType']
            
            return 't3.micro'  # Default fallback
            
        except Exception as e:
            logger.error(f"Failed to get instance type for {server_name}: {str(e)}")
            return 't3.micro'

    def update_auto_scaling_group_capacity(self, server_name: str, new_capacity: int):
        """Update ASG desired capacity"""
        try:
            asg_name = f"activelog-ai-{server_name}-asg"
            
            self.autoscaling.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                DesiredCapacity=new_capacity
            )
            
            logger.info(f"Updated {server_name} ASG capacity to {new_capacity}")
            
        except Exception as e:
            logger.error(f"Failed to update ASG capacity for {server_name}: {str(e)}")
            raise

    def update_launch_template(self, server_name: str, new_instance_type: str):
        """Update launch template with new instance type"""
        try:
            template_name = f"activelog-ai-{server_name}-template"
            
            # Get current launch template
            response = self.ec2.describe_launch_template_versions(
                LaunchTemplateName=template_name,
                Versions=['$Latest']
            )
            
            if not response['LaunchTemplateVersions']:
                raise Exception(f"Launch template not found: {template_name}")
            
            current_data = response['LaunchTemplateVersions'][0]['LaunchTemplateData']
            
            # Update instance type
            current_data['InstanceType'] = new_instance_type
            
            # Create new version
            self.ec2.create_launch_template_version(
                LaunchTemplateName=template_name,
                LaunchTemplateData=current_data,
                SourceVersion='$Latest'
            )
            
            logger.info(f"Updated launch template {template_name} with instance type {new_instance_type}")
            
        except Exception as e:
            logger.error(f"Failed to update launch template for {server_name}: {str(e)}")
            raise

    def trigger_instance_refresh(self, server_name: str):
        """Trigger instance refresh to apply new launch template"""
        try:
            asg_name = f"activelog-ai-{server_name}-asg"
            
            self.autoscaling.start_instance_refresh(
                AutoScalingGroupName=asg_name,
                Strategy='Rolling',
                Preferences={
                    'InstanceWarmup': 300,
                    'MinHealthyPercentage': 50
                }
            )
            
            logger.info(f"Started instance refresh for {server_name}")
            
        except Exception as e:
            logger.error(f"Failed to start instance refresh for {server_name}: {str(e)}")
            raise

    def get_cpu_utilization(self, server_name: str, period_minutes: int = 5) -> float:
        """Get average CPU utilization for the server"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=period_minutes)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[
                    {
                        'Name': 'AutoScalingGroupName',
                        'Value': f"activelog-ai-{server_name}-asg"
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                return sum(dp['Average'] for dp in response['Datapoints']) / len(response['Datapoints'])
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get CPU utilization for {server_name}: {str(e)}")
            return 0.0

    def monitor_and_scale_all_domains(self):
        """Monitor all domains and apply scaling decisions"""
        logger.info("Starting monitoring cycle for all domains")
        
        scaling_actions = {}
        
        for domain_name in self.domain_configs.keys():
            logger.info(f"Checking scaling for {domain_name}")
            
            # Check each service type for this domain
            services = ['backend', 'repository', 'deployer', 'trainer', 'builder', 'runner']
            
            for service in services:
                server_name = f"{domain_name}-{service}"
                cpu_usage = self.get_cpu_utilization(server_name)
                
                if cpu_usage > 0:  # Only scale if we have metrics
                    action = self.scale_instance(server_name, cpu_usage)
                    
                    if action['action'] != 'none':
                        scaling_actions[server_name] = action
                        logger.info(f"Scaling action for {server_name}: {action}")
        
        return scaling_actions

    def calculate_cost_savings(self, domain: str, period_days: int = 7) -> Dict:
        """Calculate potential cost savings from scaling optimizations"""
        config = self.domain_configs.get(domain)
        if not config:
            return {}
        
        # Get current costs (simplified calculation)
        current_cost = self.estimate_current_cost(domain)
        optimized_cost = self.estimate_optimized_cost(domain, config)
        
        savings = current_cost - optimized_cost
        
        return {
            'domain': domain,
            'current_monthly_cost': current_cost,
            'optimized_monthly_cost': optimized_cost,
            'monthly_savings': savings,
            'yearly_savings': savings * 12,
            'savings_percentage': (savings / current_cost * 100) if current_cost > 0 else 0
        }

    def estimate_current_cost(self, domain: str) -> float:
        """Estimate current monthly cost for domain"""
        # Simplified cost calculation - in reality, use AWS Cost Explorer API
        base_cost_per_instance = {
            't3.micro': 8.76,
            't3.small': 17.52,
            't3.medium': 35.04,
            't3.large': 70.08,
            'c5.large': 76.65,
            'c5.xlarge': 153.30,
            'g4dn.xlarge': 526.0
        }
        
        total_cost = 0.0
        
        # Estimate based on current configuration
        config = self.domain_configs[domain]
        avg_instances = (config.scaling_config.min_instances + config.scaling_config.max_instances) / 2
        avg_instance_type = config.scaling_config.instance_types[len(config.scaling_config.instance_types) // 2]
        
        total_cost = base_cost_per_instance.get(avg_instance_type, 35.04) * avg_instances
        
        return total_cost

    def estimate_optimized_cost(self, domain: str, config: DomainConfig) -> float:
        """Estimate cost with optimized scaling"""
        # Apply cost optimization factors
        base_cost = self.estimate_current_cost(domain)
        
        if config.cost_priority == 'cost':
            return base_cost * 0.7  # 30% savings
        else:
            return base_cost * 0.85  # 15% savings
        
    def create_scaling_schedule(self, domain: str):
        """Create scheduled scaling actions for predictable patterns"""
        config = self.domain_configs[domain]
        
        # Create CloudWatch Events rules for scheduled scaling
        events_client = boto3.client('events', region_name=self.region)
        
        # Scale up before peak hours
        peak_start = min(config.peak_hours)
        scale_up_time = f"0 {peak_start-1} * * ? *"  # 1 hour before peak
        
        events_client.put_rule(
            Name=f"{domain}-scale-up-schedule",
            ScheduleExpression=f"cron({scale_up_time})",
            Description=f"Scale up {domain} before peak hours",
            State='ENABLED'
        )
        
        # Scale down after peak hours
        peak_end = max(config.peak_hours)
        scale_down_time = f"0 {(peak_end+2) % 24} * * ? *"  # 2 hours after peak
        
        events_client.put_rule(
            Name=f"{domain}-scale-down-schedule", 
            ScheduleExpression=f"cron({scale_down_time})",
            Description=f"Scale down {domain} after peak hours",
            State='ENABLED'
        )
        
        logger.info(f"Created scaling schedule for {domain}")

    def generate_scaling_report(self) -> Dict:
        """Generate comprehensive scaling report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'domains': {},
            'total_estimated_savings': 0.0
        }
        
        for domain_name in self.domain_configs.keys():
            domain_report = {
                'config': self.domain_configs[domain_name].__dict__,
                'current_status': {},
                'cost_analysis': self.calculate_cost_savings(domain_name)
            }
            
            # Get current status for each service
            services = ['backend', 'repository', 'deployer', 'trainer', 'builder', 'runner']
            for service in services:
                server_name = f"{domain_name}-{service}"
                domain_report['current_status'][service] = {
                    'instances': self.get_current_instances(server_name),
                    'instance_type': self.get_current_instance_type(server_name),
                    'cpu_utilization': self.get_cpu_utilization(server_name)
                }
            
            report['domains'][domain_name] = domain_report
            report['total_estimated_savings'] += domain_report['cost_analysis'].get('monthly_savings', 0)
        
        return report


def main():
    """Main function for running the auto-scaler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog.AI Auto-Scaling Manager')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--domain', help='Specific domain to scale (optional)')
    parser.add_argument('--monitor', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--report', action='store_true', help='Generate scaling report')
    parser.add_argument('--schedule', action='store_true', help='Create scaling schedules')
    
    args = parser.parse_args()
    
    scaler = ActiveLogAutoScaler(region=args.region)
    
    if args.report:
        report = scaler.generate_scaling_report()
        print(json.dumps(report, indent=2, default=str))
        return
    
    if args.schedule:
        for domain in scaler.domain_configs.keys():
            scaler.create_scaling_schedule(domain)
        logger.info("Scaling schedules created for all domains")
        return
    
    if args.monitor:
        logger.info("Starting continuous monitoring...")
        while True:
            try:
                actions = scaler.monitor_and_scale_all_domains()
                if actions:
                    logger.info(f"Applied {len(actions)} scaling actions")
                
                time.sleep(300)  # Check every 5 minutes
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    elif args.domain:
        # Scale specific domain
        cpu_usage = scaler.get_cpu_utilization(f"{args.domain}-backend")
        action = scaler.scale_instance(f"{args.domain}-backend", cpu_usage)
        print(f"Scaling action: {action}")
    
    else:
        # Run one-time scaling check for all domains
        actions = scaler.monitor_and_scale_all_domains()
        print(f"Applied {len(actions)} scaling actions")
        for server, action in actions.items():
            print(f"  {server}: {action}")


if __name__ == "__main__":
    main()