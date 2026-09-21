"""
EC2 Instance Provisioning System
Handles automated EC2 instance provisioning with user isolation and security
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import json
import uuid
import subprocess
from dataclasses import asdict

# Mock AWS SDK for demonstration (replace with boto3 in production)
class MockEC2Client:
    """Mock EC2 client for testing and demonstration"""
    
    def __init__(self):
        self.instances = {}
        self.vpcs = {}
        self.subnets = {}
        self.security_groups = {}
        
    async def run_instances(self, **kwargs) -> Dict[str, Any]:
        """Mock instance creation"""
        instance_id = f"i-{uuid.uuid4().hex[:8]}"
        
        instance = {
            'InstanceId': instance_id,
            'State': {'Name': 'pending'},
            'InstanceType': kwargs.get('InstanceType', 't3.medium'),
            'PublicIpAddress': f"54.{(hash(instance_id) % 200) + 10}.{(hash(instance_id) % 200) + 10}.{(hash(instance_id) % 254) + 1}",
            'PrivateIpAddress': f"10.0.{(hash(instance_id) % 200) + 10}.{(hash(instance_id) % 254) + 1}",
            'LaunchTime': datetime.now(timezone.utc),
            'VpcId': kwargs.get('VpcId', 'vpc-default'),
            'SubnetId': kwargs.get('SubnetId', 'subnet-default'),
            'SecurityGroups': [{'GroupId': sg} for sg in kwargs.get('SecurityGroupIds', ['sg-default'])],
            'Tags': [{'Key': k, 'Value': v} for k, v in kwargs.get('Tags', {}).items()]
        }
        
        self.instances[instance_id] = instance
        
        # Simulate launch delay
        await asyncio.sleep(1)
        instance['State']['Name'] = 'running'
        
        return {'Instances': [instance]}
    
    async def describe_instances(self, instance_ids: List[str] = None) -> Dict[str, Any]:
        """Mock describe instances"""
        if instance_ids:
            instances = [self.instances[iid] for iid in instance_ids if iid in self.instances]
        else:
            instances = list(self.instances.values())
        
        return {'Reservations': [{'Instances': instances}] if instances else []}
    
    async def terminate_instances(self, instance_ids: List[str]) -> Dict[str, Any]:
        """Mock instance termination"""
        results = []
        for instance_id in instance_ids:
            if instance_id in self.instances:
                self.instances[instance_id]['State']['Name'] = 'terminating'
                results.append({
                    'InstanceId': instance_id,
                    'CurrentState': {'Name': 'terminating'},
                    'PreviousState': {'Name': 'running'}
                })
        return {'TerminatingInstances': results}

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    USE_REAL_AWS = True
except ImportError:
    USE_REAL_AWS = False

from core.models import (
    EC2Instance, User, InstanceState, InstanceType, 
    CreateInstanceRequest, InstanceResponse, current_timestamp, generate_id
)

class EC2Provisioner:
    """EC2 instance provisioning and management"""
    
    def __init__(self, config: Dict[str, Any], database_manager):
        self.config = config
        self.db = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize AWS client (mock or real)
        if USE_REAL_AWS and config.get('aws', {}).get('use_real_aws', False):
            self.ec2_client = boto3.client(
                'ec2',
                region_name=config['aws']['region']
            )
            self.use_mock = False
        else:
            self.ec2_client = MockEC2Client()
            self.use_mock = True
            
        self.provisioning_tasks = {}  # Track ongoing provisioning
        
    async def provision_instance(self, request: CreateInstanceRequest) -> InstanceResponse:
        """Provision a new EC2 instance with user isolation"""
        try:
            # Validate user exists and has permissions
            user = await self.db.get_user(request.user_id)
            if not user:
                raise ValueError(f"User {request.user_id} not found")
            
            # Check user limits
            current_instances = await self.db.count_user_instances(request.user_id)
            max_instances = self.config['aws']['max_instances_per_user']
            
            if current_instances >= max_instances:
                raise ValueError(f"User has reached maximum instance limit: {max_instances}")
            
            # Get or create user's isolated VPC
            vpc_id = await self._ensure_user_vpc(user)
            subnet_id = await self._ensure_user_subnet(user, vpc_id)
            security_groups = await self._ensure_user_security_groups(user, vpc_id)
            
            # Prepare instance launch parameters
            launch_params = {
                'ImageId': request.image_id,
                'InstanceType': request.instance_type.value,
                'MinCount': 1,
                'MaxCount': 1,
                'VpcId': vpc_id,
                'SubnetId': subnet_id,
                'SecurityGroupIds': security_groups + request.security_groups,
                'UserData': request.user_data or self._get_default_user_data(request.instance_type),
                'Tags': {
                    **self.config['provisioning']['default_tags'],
                    'UserId': request.user_id,
                    'BillingEnabled': 'true',
                    'CreatedBy': 'cloud-infrastructure-system',
                    **request.tags
                }
            }
            
            # Launch instance
            self.logger.info(f"Launching instance for user {request.user_id}")
            
            if self.use_mock:
                response = await self.ec2_client.run_instances(**launch_params)
            else:
                # Real AWS call would be synchronous, wrap in executor
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: self.ec2_client.run_instances(**launch_params)
                )
            
            instance_data = response['Instances'][0]
            instance_id = instance_data['InstanceId']
            
            # Create instance record
            instance = EC2Instance(
                instance_id=instance_id,
                user_id=request.user_id,
                instance_type=request.instance_type,
                state=InstanceState.PENDING,
                created_at=current_timestamp(),
                public_ip=instance_data.get('PublicIpAddress'),
                private_ip=instance_data.get('PrivateIpAddress'),
                vpc_id=vpc_id,
                subnet_id=subnet_id,
                security_groups=security_groups + request.security_groups,
                tags=launch_params['Tags']
            )
            
            # Save to database
            await self.db.create_instance(instance)
            
            # Start monitoring task
            asyncio.create_task(self._monitor_instance_launch(instance_id))
            
            self.logger.info(f"Instance {instance_id} launched successfully for user {request.user_id}")
            
            return InstanceResponse(
                instance_id=instance.instance_id,
                state=instance.state,
                instance_type=instance.instance_type,
                public_ip=instance.public_ip,
                private_ip=instance.private_ip,
                created_at=instance.created_at,
                tags=instance.tags
            )
            
        except Exception as e:
            self.logger.error(f"Failed to provision instance: {e}")
            raise
    
    async def terminate_instance(self, user_id: str, instance_id: str) -> bool:
        """Terminate an EC2 instance"""
        try:
            # Verify user owns the instance
            instance = await self.db.get_instance(instance_id)
            if not instance or instance.user_id != user_id:
                raise ValueError(f"Instance {instance_id} not found or not owned by user {user_id}")
            
            if instance.state in [InstanceState.TERMINATING, InstanceState.TERMINATED]:
                return True
            
            # Terminate instance
            self.logger.info(f"Terminating instance {instance_id} for user {user_id}")
            
            if self.use_mock:
                await self.ec2_client.terminate_instances([instance_id])
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.ec2_client.terminate_instances(InstanceIds=[instance_id])
                )
            
            # Update instance state
            instance.state = InstanceState.TERMINATING
            await self.db.update_instance(instance)
            
            # Create final billing record
            await self._finalize_instance_billing(instance)
            
            self.logger.info(f"Instance {instance_id} terminated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to terminate instance {instance_id}: {e}")
            return False
    
    async def get_user_instances(self, user_id: str) -> List[InstanceResponse]:
        """Get all instances for a user"""
        try:
            instances = await self.db.get_user_instances(user_id)
            
            # Update instance states from AWS
            await self._sync_instance_states(instances)
            
            return [
                InstanceResponse(
                    instance_id=inst.instance_id,
                    state=inst.state,
                    instance_type=inst.instance_type,
                    public_ip=inst.public_ip,
                    private_ip=inst.private_ip,
                    created_at=inst.created_at,
                    tags=inst.tags
                )
                for inst in instances
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get instances for user {user_id}: {e}")
            return []
    
    async def _ensure_user_vpc(self, user: User) -> str:
        """Ensure user has an isolated VPC"""
        if user.vpc_id:
            return user.vpc_id
            
        # Create user-specific VPC (mock implementation)
        vpc_cidr = self._calculate_user_vpc_cidr(user.user_id)
        vpc_id = f"vpc-{user.user_id}-{uuid.uuid4().hex[:8]}"
        
        self.logger.info(f"Creating VPC {vpc_id} for user {user.user_id}")
        
        # In real implementation, create actual VPC
        # vpc = await self.ec2_client.create_vpc(CidrBlock=vpc_cidr)
        
        # Update user record
        user.vpc_id = vpc_id
        await self.db.update_user(user)
        
        return vpc_id
    
    async def _ensure_user_subnet(self, user: User, vpc_id: str) -> str:
        """Ensure user has a private subnet"""
        # Create or get user subnet
        subnet_cidr = self._calculate_user_subnet_cidr(user.user_id)
        subnet_id = f"subnet-{user.user_id}-private"
        
        # In real implementation, create actual subnet
        self.logger.info(f"Using subnet {subnet_id} for user {user.user_id}")
        
        return subnet_id
    
    async def _ensure_user_security_groups(self, user: User, vpc_id: str) -> List[str]:
        """Ensure user has appropriate security groups"""
        security_groups = [
            f"sg-{user.user_id}-web",
            f"sg-{user.user_id}-ssh"
        ]
        
        # In real implementation, create actual security groups
        self.logger.info(f"Using security groups {security_groups} for user {user.user_id}")
        
        return security_groups
    
    def _calculate_user_vpc_cidr(self, user_id: str) -> str:
        """Calculate unique VPC CIDR for user"""
        # Use hash of user_id to generate unique CIDR
        user_hash = hash(user_id) % 256
        return f"172.16.{user_hash}.0/24"
    
    def _calculate_user_subnet_cidr(self, user_id: str) -> str:
        """Calculate unique subnet CIDR for user"""
        user_hash = hash(user_id) % 256
        return f"172.16.{user_hash}.0/26"
    
    def _get_default_user_data(self, instance_type: InstanceType) -> str:
        """Get default user data script based on instance type"""
        if "game" in instance_type.value:
            return """#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
# Game server specific setup
"""
        else:
            return """#!/bin/bash
yum update -y
yum install -y awscli
# Standard instance setup
"""
    
    async def _monitor_instance_launch(self, instance_id: str):
        """Monitor instance launch and update state"""
        timeout = self.config['provisioning']['provisioning_timeout_minutes'] * 60
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self.use_mock:
                    response = await self.ec2_client.describe_instances([instance_id])
                else:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.ec2_client.describe_instances(InstanceIds=[instance_id])
                    )
                
                if response['Reservations']:
                    instance_data = response['Reservations'][0]['Instances'][0]
                    state_name = instance_data['State']['Name']
                    
                    # Update instance in database
                    instance = await self.db.get_instance(instance_id)
                    if instance:
                        instance.state = InstanceState(state_name)
                        if 'PublicIpAddress' in instance_data:
                            instance.public_ip = instance_data['PublicIpAddress']
                        if 'PrivateIpAddress' in instance_data:
                            instance.private_ip = instance_data['PrivateIpAddress']
                        
                        await self.db.update_instance(instance)
                    
                    # If running, start billing
                    if state_name == 'running':
                        await self._start_instance_billing(instance)
                        break
                    elif state_name in ['terminated', 'terminating']:
                        break
                
                await asyncio.sleep(self.config['provisioning']['health_check_interval_seconds'])
                
            except Exception as e:
                self.logger.error(f"Error monitoring instance {instance_id}: {e}")
                await asyncio.sleep(30)
        
        # Handle timeout
        if time.time() - start_time >= timeout:
            self.logger.error(f"Instance {instance_id} launch timed out")
            instance = await self.db.get_instance(instance_id)
            if instance:
                instance.state = InstanceState.ERROR
                await self.db.update_instance(instance)
    
    async def _sync_instance_states(self, instances: List[EC2Instance]):
        """Synchronize instance states with AWS"""
        if not instances:
            return
            
        instance_ids = [inst.instance_id for inst in instances]
        
        try:
            if self.use_mock:
                response = await self.ec2_client.describe_instances(instance_ids)
            else:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.ec2_client.describe_instances(InstanceIds=instance_ids)
                )
            
            # Update states
            aws_instances = {}
            for reservation in response.get('Reservations', []):
                for inst_data in reservation['Instances']:
                    aws_instances[inst_data['InstanceId']] = inst_data
            
            for instance in instances:
                if instance.instance_id in aws_instances:
                    aws_data = aws_instances[instance.instance_id]
                    new_state = InstanceState(aws_data['State']['Name'])
                    
                    if instance.state != new_state:
                        instance.state = new_state
                        await self.db.update_instance(instance)
                        
                        # Handle state changes for billing
                        if new_state == InstanceState.RUNNING:
                            await self._start_instance_billing(instance)
                        elif new_state in [InstanceState.STOPPED, InstanceState.TERMINATED]:
                            await self._finalize_instance_billing(instance)
                            
        except Exception as e:
            self.logger.error(f"Failed to sync instance states: {e}")
    
    async def _start_instance_billing(self, instance: EC2Instance):
        """Start billing tracking for running instance"""
        try:
            if not instance.last_billed_at:
                instance.last_billed_at = current_timestamp()
                await self.db.update_instance(instance)
                self.logger.info(f"Started billing for instance {instance.instance_id}")
        except Exception as e:
            self.logger.error(f"Failed to start billing for instance {instance.instance_id}: {e}")
    
    async def _finalize_instance_billing(self, instance: EC2Instance):
        """Finalize billing for terminated/stopped instance"""
        try:
            if instance.last_billed_at:
                end_time = current_timestamp()
                duration = (end_time - instance.last_billed_at).total_seconds() / 60  # minutes
                
                # Create final billing record
                from billing.usage_tracker import UsageTracker
                usage_tracker = UsageTracker(self.config, self.db)
                await usage_tracker.record_usage(
                    user_id=instance.user_id,
                    instance_id=instance.instance_id,
                    instance_type=instance.instance_type,
                    start_time=instance.last_billed_at,
                    end_time=end_time,
                    duration_minutes=int(duration)
                )
                
                self.logger.info(f"Finalized billing for instance {instance.instance_id}")
        except Exception as e:
            self.logger.error(f"Failed to finalize billing for instance {instance.instance_id}: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on provisioning system"""
        try:
            # Check AWS connectivity (mock always succeeds)
            if self.use_mock:
                aws_healthy = True
            else:
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: self.ec2_client.describe_regions()
                        ),
                        timeout=10
                    )
                    aws_healthy = True
                except:
                    aws_healthy = False
            
            # Get system stats
            total_instances = await self.db.count_all_instances()
            running_instances = await self.db.count_instances_by_state(InstanceState.RUNNING)
            
            return {
                "service": "ec2_provisioner",
                "healthy": aws_healthy,
                "aws_connection": aws_healthy,
                "total_instances": total_instances,
                "running_instances": running_instances,
                "pending_tasks": len(self.provisioning_tasks),
                "timestamp": current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "service": "ec2_provisioner",
                "healthy": False,
                "error": str(e),
                "timestamp": current_timestamp().isoformat()
            }