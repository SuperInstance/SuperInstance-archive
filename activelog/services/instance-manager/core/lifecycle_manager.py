"""
Instance Lifecycle Manager
Handles the complete lifecycle of EC2 instances with intelligent state management
"""

import logging
import boto3
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class InstanceState(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    STOPPING = "stopping"
    STOPPED = "stopped"
    SHUTTING_DOWN = "shutting-down"
    TERMINATED = "terminated"
    REBOOTING = "rebooting"

class LifecycleAction(Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    TERMINATE = "terminate"
    RESIZE = "resize"
    BACKUP = "backup"

class LifecycleManager:
    """Manages the complete lifecycle of EC2 instances"""
    
    def __init__(self, ec2_client):
        self.ec2 = ec2_client
        self.resource = boto3.resource('ec2', region_name=ec2_client.meta.region_name)
        
    async def get_instance_lifecycle_info(self, instance_id: str) -> Dict[str, Any]:
        """Get comprehensive lifecycle information for an instance"""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance_data = response['Reservations'][0]['Instances'][0]
            
            # Calculate uptime
            launch_time = instance_data.get('LaunchTime')
            uptime_hours = 0
            if launch_time and instance_data['State']['Name'] == 'running':
                uptime = datetime.utcnow() - launch_time.replace(tzinfo=None)
                uptime_hours = uptime.total_seconds() / 3600
            
            # Get instance lifecycle history
            history = await self._get_instance_history(instance_id)
            
            # Calculate cost information
            cost_info = await self._calculate_instance_costs(instance_data, uptime_hours)
            
            lifecycle_info = {
                'instance_id': instance_id,
                'state': instance_data['State']['Name'],
                'instance_type': instance_data['InstanceType'],
                'launch_time': launch_time.isoformat() if launch_time else None,
                'uptime_hours': uptime_hours,
                'platform': instance_data.get('Platform', 'linux'),
                'vpc_id': instance_data.get('VpcId'),
                'subnet_id': instance_data.get('SubnetId'),
                'availability_zone': instance_data['Placement']['AvailabilityZone'],
                'lifecycle_history': history,
                'cost_info': cost_info,
                'tags': {tag['Key']: tag['Value'] for tag in instance_data.get('Tags', [])}
            }
            
            return lifecycle_info
            
        except ClientError as e:
            logger.error(f"Failed to get lifecycle info for {instance_id}: {e}")
            raise
    
    async def _get_instance_history(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get historical state changes for an instance"""
        try:
            # Get CloudTrail events for this instance (simplified version)
            # In production, you'd query CloudTrail logs
            history = []
            
            # For now, return basic state history from tags
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            
            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            
            if 'lifecycle:last_start' in tags:
                history.append({
                    'action': 'start',
                    'timestamp': tags['lifecycle:last_start'],
                    'reason': tags.get('lifecycle:start_reason', 'manual')
                })
            
            if 'lifecycle:last_stop' in tags:
                history.append({
                    'action': 'stop', 
                    'timestamp': tags['lifecycle:last_stop'],
                    'reason': tags.get('lifecycle:stop_reason', 'manual')
                })
            
            return sorted(history, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.warning(f"Could not retrieve history for {instance_id}: {e}")
            return []
    
    async def _calculate_instance_costs(self, instance_data: Dict, uptime_hours: float) -> Dict[str, Any]:
        """Calculate cost information for an instance"""
        try:
            instance_type = instance_data['InstanceType']
            platform = instance_data.get('Platform', 'linux')
            
            # Simplified cost calculation - in production, use AWS Pricing API
            hourly_rates = {
                't3.nano': 0.0052,
                't3.micro': 0.0104,
                't3.small': 0.0208,
                't3.medium': 0.0416,
                't3.large': 0.0832,
                't3.xlarge': 0.1664,
                't3.2xlarge': 0.3328,
                'm5.large': 0.096,
                'm5.xlarge': 0.192,
                'm5.2xlarge': 0.384,
                'c5.large': 0.085,
                'c5.xlarge': 0.17,
                'r5.large': 0.126,
                'r5.xlarge': 0.252
            }
            
            hourly_rate = hourly_rates.get(instance_type, 0.10)  # Default rate
            
            if platform == 'windows':
                hourly_rate *= 2  # Windows instances cost more
            
            current_month_cost = uptime_hours * hourly_rate
            projected_monthly_cost = hourly_rate * 24 * 30  # Assuming 24/7 usage
            
            return {
                'hourly_rate': hourly_rate,
                'uptime_hours': uptime_hours,
                'current_month_cost': round(current_month_cost, 4),
                'projected_monthly_cost': round(projected_monthly_cost, 2),
                'currency': 'USD'
            }
            
        except Exception as e:
            logger.warning(f"Could not calculate costs: {e}")
            return {
                'hourly_rate': 0,
                'uptime_hours': uptime_hours,
                'current_month_cost': 0,
                'projected_monthly_cost': 0,
                'currency': 'USD'
            }
    
    async def perform_lifecycle_action(self, instance_id: str, action: LifecycleAction, 
                                     options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform a lifecycle action on an instance"""
        options = options or {}
        
        try:
            logger.info(f"Performing {action.value} on instance {instance_id}")
            
            # Record action in instance tags
            await self._record_lifecycle_action(instance_id, action, options)
            
            if action == LifecycleAction.START:
                return await self._start_instance(instance_id, options)
            elif action == LifecycleAction.STOP:
                return await self._stop_instance(instance_id, options)
            elif action == LifecycleAction.RESTART:
                return await self._restart_instance(instance_id, options)
            elif action == LifecycleAction.TERMINATE:
                return await self._terminate_instance(instance_id, options)
            elif action == LifecycleAction.RESIZE:
                return await self._resize_instance(instance_id, options)
            elif action == LifecycleAction.BACKUP:
                return await self._backup_instance(instance_id, options)
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Failed to perform {action.value} on {instance_id}: {e}")
            raise
    
    async def _record_lifecycle_action(self, instance_id: str, action: LifecycleAction, 
                                     options: Dict[str, Any]):
        """Record lifecycle action in instance tags"""
        try:
            timestamp = datetime.utcnow().isoformat()
            reason = options.get('reason', 'api')
            
            tags_to_create = [
                {
                    'Key': f'lifecycle:last_{action.value}',
                    'Value': timestamp
                },
                {
                    'Key': f'lifecycle:{action.value}_reason',
                    'Value': reason
                }
            ]
            
            if 'user' in options:
                tags_to_create.append({
                    'Key': f'lifecycle:{action.value}_user',
                    'Value': options['user']
                })
            
            self.ec2.create_tags(
                Resources=[instance_id],
                Tags=tags_to_create
            )
            
        except Exception as e:
            logger.warning(f"Could not record lifecycle action: {e}")
    
    async def _start_instance(self, instance_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Start an instance"""
        try:
            response = self.ec2.start_instances(InstanceIds=[instance_id])
            
            # Wait for instance to be running if requested
            if options.get('wait', False):
                logger.info(f"Waiting for {instance_id} to start...")
                waiter = self.ec2.get_waiter('instance_running')
                waiter.wait(InstanceIds=[instance_id])
            
            return {
                'action': 'start',
                'instance_id': instance_id,
                'status': 'success',
                'starting_instances': response['StartingInstances'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'IncorrectInstanceState':
                return {
                    'action': 'start',
                    'instance_id': instance_id,
                    'status': 'already_running',
                    'message': 'Instance is already running or starting'
                }
            raise
    
    async def _stop_instance(self, instance_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Stop an instance"""
        try:
            force_stop = options.get('force', False)
            
            if force_stop:
                response = self.ec2.stop_instances(InstanceIds=[instance_id], Force=True)
            else:
                response = self.ec2.stop_instances(InstanceIds=[instance_id])
            
            # Wait for instance to be stopped if requested
            if options.get('wait', False):
                logger.info(f"Waiting for {instance_id} to stop...")
                waiter = self.ec2.get_waiter('instance_stopped')
                waiter.wait(InstanceIds=[instance_id])
            
            return {
                'action': 'stop',
                'instance_id': instance_id,
                'status': 'success',
                'stopping_instances': response['StoppingInstances'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'IncorrectInstanceState':
                return {
                    'action': 'stop',
                    'instance_id': instance_id,
                    'status': 'already_stopped',
                    'message': 'Instance is already stopped or stopping'
                }
            raise
    
    async def _restart_instance(self, instance_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Restart an instance"""
        try:
            response = self.ec2.reboot_instances(InstanceIds=[instance_id])
            
            return {
                'action': 'restart',
                'instance_id': instance_id,
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            raise
    
    async def _terminate_instance(self, instance_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Terminate an instance"""
        try:
            # Check termination protection
            response = self.ec2.describe_instance_attribute(
                InstanceId=instance_id,
                Attribute='disableApiTermination'
            )
            
            if response['DisableApiTermination']['Value']:
                if not options.get('disable_termination_protection', False):
                    return {
                        'action': 'terminate',
                        'instance_id': instance_id,
                        'status': 'error',
                        'message': 'Instance has termination protection enabled'
                    }
                else:
                    # Disable termination protection
                    self.ec2.modify_instance_attribute(
                        InstanceId=instance_id,
                        DisableApiTermination={'Value': False}
                    )
            
            response = self.ec2.terminate_instances(InstanceIds=[instance_id])
            
            return {
                'action': 'terminate',
                'instance_id': instance_id,
                'status': 'success',
                'terminating_instances': response['TerminatingInstances'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            raise
    
    async def _resize_instance(self, instance_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Resize an instance to a different instance type"""
        try:
            new_instance_type = options.get('instance_type')
            if not new_instance_type:
                raise ValueError("instance_type is required for resize action")
            
            # Stop instance if it's running
            instance = self.resource.Instance(instance_id)
            original_state = instance.state['Name']
            
            if original_state == 'running':
                logger.info(f"Stopping {instance_id} for resize...")
                await self._stop_instance(instance_id, {'wait': True})
            
            # Modify instance type
            self.ec2.modify_instance_attribute(
                InstanceId=instance_id,
                InstanceType={'Value': new_instance_type}
            )
            
            # Start instance if it was originally running
            if original_state == 'running' and options.get('auto_start', True):
                logger.info(f"Starting {instance_id} after resize...")
                await self._start_instance(instance_id, {'wait': True})
            
            return {
                'action': 'resize',
                'instance_id': instance_id,
                'status': 'success',
                'new_instance_type': new_instance_type,
                'original_state': original_state,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            raise
    
    async def _backup_instance(self, instance_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Create a backup (AMI) of an instance"""
        try:
            instance_name = options.get('name', f"backup-{instance_id}")
            description = options.get('description', f"Backup of {instance_id} created on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
            
            response = self.ec2.create_image(
                InstanceId=instance_id,
                Name=instance_name,
                Description=description,
                NoReboot=options.get('no_reboot', True)
            )
            
            ami_id = response['ImageId']
            
            # Tag the AMI
            tags = [
                {'Key': 'Name', 'Value': instance_name},
                {'Key': 'SourceInstance', 'Value': instance_id},
                {'Key': 'BackupType', 'Value': 'instance-backup'},
                {'Key': 'CreatedBy', 'Value': 'instance-manager'},
                {'Key': 'CreatedAt', 'Value': datetime.utcnow().isoformat()}
            ]
            
            if 'retention_days' in options:
                delete_date = datetime.utcnow() + timedelta(days=options['retention_days'])
                tags.append({
                    'Key': 'DeleteAfter',
                    'Value': delete_date.strftime('%Y-%m-%d')
                })
            
            self.ec2.create_tags(Resources=[ami_id], Tags=tags)
            
            return {
                'action': 'backup',
                'instance_id': instance_id,
                'status': 'success',
                'ami_id': ami_id,
                'ami_name': instance_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            raise
    
    async def get_instance_recommendations(self, instance_id: str) -> Dict[str, Any]:
        """Get optimization recommendations for an instance"""
        try:
            lifecycle_info = await self.get_instance_lifecycle_info(instance_id)
            
            recommendations = []
            
            # Cost optimization recommendations
            if lifecycle_info['uptime_hours'] > 168:  # Running for more than a week
                if lifecycle_info['cost_info']['projected_monthly_cost'] > 50:
                    recommendations.append({
                        'type': 'cost_optimization',
                        'priority': 'high',
                        'title': 'Consider Reserved Instance',
                        'description': f"Instance running 24/7 with high monthly cost (${lifecycle_info['cost_info']['projected_monthly_cost']}). Reserved Instance could save 30-60%",
                        'action': 'analyze_reserved_instance'
                    })
            
            # Right-sizing recommendations
            instance_type = lifecycle_info['instance_type']
            if instance_type.startswith('t3.'):
                recommendations.append({
                    'type': 'rightsizing',
                    'priority': 'medium',
                    'title': 'Monitor CPU Credits',
                    'description': 'T3 instances use CPU credits. Monitor usage to ensure optimal performance',
                    'action': 'monitor_cpu_credits'
                })
            
            # Backup recommendations
            tags = lifecycle_info['tags']
            if 'lifecycle:last_backup' not in tags:
                recommendations.append({
                    'type': 'backup',
                    'priority': 'high',
                    'title': 'No Recent Backup Found',
                    'description': 'Consider creating an AMI backup for disaster recovery',
                    'action': 'create_backup'
                })
            
            # Security recommendations
            if lifecycle_info['uptime_hours'] > 720:  # Running for more than a month
                recommendations.append({
                    'type': 'security',
                    'priority': 'medium',
                    'title': 'Consider OS Updates',
                    'description': 'Long-running instance may need OS and security updates',
                    'action': 'schedule_maintenance'
                })
            
            return {
                'instance_id': instance_id,
                'recommendations': recommendations,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations for {instance_id}: {e}")
            raise