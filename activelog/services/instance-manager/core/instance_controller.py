"""
Instance Controller
Direct control interface for EC2 instances with safety checks and batch operations
"""

import logging
import boto3
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class InstanceController:
    """Direct control interface for EC2 instances"""
    
    def __init__(self, ec2_client):
        self.ec2 = ec2_client
        self.resource = boto3.resource('ec2', region_name=ec2_client.meta.region_name)
        
    def list_instances(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """List instances with optional filters"""
        try:
            ec2_filters = []
            
            if filters:
                if 'state' in filters:
                    ec2_filters.append({
                        'Name': 'instance-state-name',
                        'Values': filters['state'] if isinstance(filters['state'], list) else [filters['state']]
                    })
                
                if 'instance_type' in filters:
                    ec2_filters.append({
                        'Name': 'instance-type',
                        'Values': filters['instance_type'] if isinstance(filters['instance_type'], list) else [filters['instance_type']]
                    })
                
                if 'vpc_id' in filters:
                    ec2_filters.append({
                        'Name': 'vpc-id',
                        'Values': [filters['vpc_id']]
                    })
                
                if 'tag' in filters:
                    for key, value in filters['tag'].items():
                        ec2_filters.append({
                            'Name': f'tag:{key}',
                            'Values': [value] if isinstance(value, str) else value
                        })
            
            response = self.ec2.describe_instances(Filters=ec2_filters)
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append(self._format_instance_info(instance))
            
            return instances
            
        except ClientError as e:
            logger.error(f"Failed to list instances: {e}")
            raise
    
    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific instance"""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            return self._format_instance_info(instance, detailed=True)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
                raise ValueError(f"Instance {instance_id} not found")
            logger.error(f"Failed to get instance {instance_id}: {e}")
            raise
    
    def _format_instance_info(self, instance: Dict[str, Any], detailed: bool = False) -> Dict[str, Any]:
        """Format instance information for API response"""
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        
        instance_info = {
            'instance_id': instance['InstanceId'],
            'state': instance['State']['Name'],
            'state_code': instance['State']['Code'],
            'instance_type': instance['InstanceType'],
            'platform': instance.get('Platform', 'linux'),
            'launch_time': instance.get('LaunchTime').isoformat() if instance.get('LaunchTime') else None,
            'availability_zone': instance['Placement']['AvailabilityZone'],
            'vpc_id': instance.get('VpcId'),
            'subnet_id': instance.get('SubnetId'),
            'private_ip': instance.get('PrivateIpAddress'),
            'public_ip': instance.get('PublicIpAddress'),
            'security_groups': [sg['GroupName'] for sg in instance.get('SecurityGroups', [])],
            'tags': tags,
            'name': tags.get('Name', 'unnamed'),
            'environment': tags.get('Environment', 'untagged'),
            'project': tags.get('Project', 'untagged'),
            'owner': tags.get('Owner', 'unknown')
        }
        
        if detailed:
            instance_info.update({
                'architecture': instance.get('Architecture'),
                'hypervisor': instance.get('Hypervisor'),
                'virtualization_type': instance.get('VirtualizationType'),
                'root_device_type': instance.get('RootDeviceType'),
                'root_device_name': instance.get('RootDeviceName'),
                'block_device_mappings': instance.get('BlockDeviceMappings', []),
                'network_interfaces': instance.get('NetworkInterfaces', []),
                'iam_instance_profile': instance.get('IamInstanceProfile'),
                'monitoring': instance.get('Monitoring', {}).get('State', 'disabled'),
                'spot_instance_request_id': instance.get('SpotInstanceRequestId')
            })
        
        return instance_info
    
    def start_instance(self, instance_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start a single instance"""
        options = options or {}
        
        try:
            # Check current state
            instance = self.get_instance(instance_id)
            current_state = instance['state']
            
            if current_state == 'running':
                return {
                    'status': 'already_running',
                    'message': f'Instance {instance_id} is already running',
                    'instance_id': instance_id
                }
            
            if current_state in ['stopping', 'pending', 'rebooting']:
                return {
                    'status': 'transitioning',
                    'message': f'Instance {instance_id} is in {current_state} state',
                    'instance_id': instance_id
                }
            
            if current_state in ['shutting-down', 'terminated']:
                return {
                    'status': 'error',
                    'message': f'Cannot start instance in {current_state} state',
                    'instance_id': instance_id
                }
            
            # Start the instance
            response = self.ec2.start_instances(InstanceIds=[instance_id])
            
            result = {
                'status': 'success',
                'message': f'Instance {instance_id} start initiated',
                'instance_id': instance_id,
                'previous_state': current_state,
                'starting_instances': response['StartingInstances']
            }
            
            # Wait for instance to be running if requested
            if options.get('wait', False):
                logger.info(f"Waiting for {instance_id} to start...")
                waiter = self.ec2.get_waiter('instance_running')
                waiter.wait(
                    InstanceIds=[instance_id],
                    WaiterConfig={
                        'Delay': 15,
                        'MaxAttempts': 40  # Wait up to 10 minutes
                    }
                )
                result['status'] = 'running'
                result['message'] = f'Instance {instance_id} is now running'
            
            return result
            
        except ClientError as e:
            logger.error(f"Failed to start instance {instance_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'instance_id': instance_id
            }
    
    def stop_instance(self, instance_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Stop a single instance"""
        options = options or {}
        
        try:
            # Check current state
            instance = self.get_instance(instance_id)
            current_state = instance['state']
            
            if current_state == 'stopped':
                return {
                    'status': 'already_stopped',
                    'message': f'Instance {instance_id} is already stopped',
                    'instance_id': instance_id
                }
            
            if current_state in ['stopping', 'pending', 'rebooting']:
                return {
                    'status': 'transitioning',
                    'message': f'Instance {instance_id} is in {current_state} state',
                    'instance_id': instance_id
                }
            
            if current_state in ['shutting-down', 'terminated']:
                return {
                    'status': 'error',
                    'message': f'Cannot stop instance in {current_state} state',
                    'instance_id': instance_id
                }
            
            # Stop the instance
            stop_params = {'InstanceIds': [instance_id]}
            if options.get('force', False):
                stop_params['Force'] = True
            
            response = self.ec2.stop_instances(**stop_params)
            
            result = {
                'status': 'success',
                'message': f'Instance {instance_id} stop initiated',
                'instance_id': instance_id,
                'previous_state': current_state,
                'stopping_instances': response['StoppingInstances']
            }
            
            # Wait for instance to be stopped if requested
            if options.get('wait', False):
                logger.info(f"Waiting for {instance_id} to stop...")
                waiter = self.ec2.get_waiter('instance_stopped')
                waiter.wait(
                    InstanceIds=[instance_id],
                    WaiterConfig={
                        'Delay': 15,
                        'MaxAttempts': 40  # Wait up to 10 minutes
                    }
                )
                result['status'] = 'stopped'
                result['message'] = f'Instance {instance_id} is now stopped'
            
            return result
            
        except ClientError as e:
            logger.error(f"Failed to stop instance {instance_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'instance_id': instance_id
            }
    
    def restart_instance(self, instance_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Restart a single instance"""
        options = options or {}
        
        try:
            # Check current state
            instance = self.get_instance(instance_id)
            current_state = instance['state']
            
            if current_state != 'running':
                return {
                    'status': 'error',
                    'message': f'Instance {instance_id} must be running to restart (current state: {current_state})',
                    'instance_id': instance_id
                }
            
            # Reboot the instance
            self.ec2.reboot_instances(InstanceIds=[instance_id])
            
            return {
                'status': 'success',
                'message': f'Instance {instance_id} restart initiated',
                'instance_id': instance_id
            }
            
        except ClientError as e:
            logger.error(f"Failed to restart instance {instance_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'instance_id': instance_id
            }
    
    def batch_operation(self, instance_ids: List[str], operation: str, 
                       options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform batch operations on multiple instances"""
        options = options or {}
        max_workers = options.get('max_workers', 5)
        
        results = {
            'operation': operation,
            'total_instances': len(instance_ids),
            'results': {},
            'summary': {
                'success': 0,
                'error': 0,
                'skipped': 0
            }
        }
        
        def execute_single_operation(instance_id):
            try:
                if operation == 'start':
                    return instance_id, self.start_instance(instance_id, options)
                elif operation == 'stop':
                    return instance_id, self.stop_instance(instance_id, options)
                elif operation == 'restart':
                    return instance_id, self.restart_instance(instance_id, options)
                else:
                    return instance_id, {
                        'status': 'error',
                        'message': f'Unknown operation: {operation}',
                        'instance_id': instance_id
                    }
            except Exception as e:
                return instance_id, {
                    'status': 'error',
                    'message': str(e),
                    'instance_id': instance_id
                }
        
        # Execute operations in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_instance = {
                executor.submit(execute_single_operation, instance_id): instance_id 
                for instance_id in instance_ids
            }
            
            for future in as_completed(future_to_instance):
                instance_id, result = future.result()
                results['results'][instance_id] = result
                
                if result['status'] == 'success':
                    results['summary']['success'] += 1
                elif result['status'] in ['already_running', 'already_stopped', 'transitioning']:
                    results['summary']['skipped'] += 1
                else:
                    results['summary']['error'] += 1
        
        return results
    
    def get_instance_metrics(self, instance_id: str, 
                           metric_names: List[str] = None, 
                           hours: int = 24) -> Dict[str, Any]:
        """Get CloudWatch metrics for an instance"""
        try:
            cloudwatch = boto3.client('cloudwatch', region_name=self.ec2.meta.region_name)
            
            if metric_names is None:
                metric_names = ['CPUUtilization', 'NetworkIn', 'NetworkOut', 'DiskReadBytes', 'DiskWriteBytes']
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            metrics_data = {}
            
            for metric_name in metric_names:
                try:
                    response = cloudwatch.get_metric_statistics(
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
                        Statistics=['Average', 'Maximum']
                    )
                    
                    datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics_data[metric_name] = {
                        'datapoints': [
                            {
                                'timestamp': dp['Timestamp'].isoformat(),
                                'average': dp.get('Average', 0),
                                'maximum': dp.get('Maximum', 0)
                            }
                            for dp in datapoints
                        ],
                        'latest_average': datapoints[-1].get('Average', 0) if datapoints else 0,
                        'latest_maximum': datapoints[-1].get('Maximum', 0) if datapoints else 0
                    }
                except Exception as e:
                    logger.warning(f"Failed to get {metric_name} for {instance_id}: {e}")
                    metrics_data[metric_name] = {'error': str(e)}
            
            return {
                'instance_id': instance_id,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'hours': hours
                },
                'metrics': metrics_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics for {instance_id}: {e}")
            raise
    
    def modify_instance_attributes(self, instance_id: str, 
                                 attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Modify instance attributes"""
        try:
            results = {}
            
            # Instance type
            if 'instance_type' in attributes:
                # Check if instance is stopped
                instance = self.get_instance(instance_id)
                if instance['state'] != 'stopped':
                    return {
                        'status': 'error',
                        'message': 'Instance must be stopped to change instance type'
                    }
                
                self.ec2.modify_instance_attribute(
                    InstanceId=instance_id,
                    InstanceType={'Value': attributes['instance_type']}
                )
                results['instance_type'] = 'updated'
            
            # Security groups
            if 'security_groups' in attributes:
                self.ec2.modify_instance_attribute(
                    InstanceId=instance_id,
                    Groups=attributes['security_groups']
                )
                results['security_groups'] = 'updated'
            
            # User data
            if 'user_data' in attributes:
                # Note: User data can only be changed when instance is stopped
                instance = self.get_instance(instance_id)
                if instance['state'] != 'stopped':
                    return {
                        'status': 'error',
                        'message': 'Instance must be stopped to change user data'
                    }
                
                import base64
                user_data_b64 = base64.b64encode(attributes['user_data'].encode()).decode()
                
                self.ec2.modify_instance_attribute(
                    InstanceId=instance_id,
                    UserData={'Value': user_data_b64}
                )
                results['user_data'] = 'updated'
            
            # Termination protection
            if 'disable_api_termination' in attributes:
                self.ec2.modify_instance_attribute(
                    InstanceId=instance_id,
                    DisableApiTermination={'Value': attributes['disable_api_termination']}
                )
                results['disable_api_termination'] = 'updated'
            
            # Source/destination check
            if 'source_dest_check' in attributes:
                self.ec2.modify_instance_attribute(
                    InstanceId=instance_id,
                    SourceDestCheck={'Value': attributes['source_dest_check']}
                )
                results['source_dest_check'] = 'updated'
            
            return {
                'status': 'success',
                'instance_id': instance_id,
                'updated_attributes': results
            }
            
        except ClientError as e:
            logger.error(f"Failed to modify attributes for {instance_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'instance_id': instance_id
            }
    
    def create_instance_tags(self, instance_id: str, tags: Dict[str, str]) -> Dict[str, Any]:
        """Create or update tags for an instance"""
        try:
            tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
            
            self.ec2.create_tags(
                Resources=[instance_id],
                Tags=tag_list
            )
            
            return {
                'status': 'success',
                'instance_id': instance_id,
                'tags_created': len(tags)
            }
            
        except ClientError as e:
            logger.error(f"Failed to create tags for {instance_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'instance_id': instance_id
            }
    
    def get_instance_console_output(self, instance_id: str, latest: bool = True) -> Dict[str, Any]:
        """Get console output for an instance"""
        try:
            params = {'InstanceId': instance_id}
            if latest:
                params['Latest'] = True
            
            response = self.ec2.get_console_output(**params)
            
            return {
                'instance_id': instance_id,
                'timestamp': response.get('Timestamp'),
                'output': response.get('Output', ''),
                'has_output': bool(response.get('Output'))
            }
            
        except ClientError as e:
            logger.error(f"Failed to get console output for {instance_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'instance_id': instance_id
            }