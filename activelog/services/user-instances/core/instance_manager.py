"""
UserInstanceManager - Core class for managing isolated user instances
"""
import boto3
import hashlib
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InstanceConfig:
    """Configuration for a user instance"""
    user_id: str
    tier: str
    instance_type: str
    ami_id: str
    security_group_id: str
    vpc_id: str
    subnet_id: str
    encryption_key_id: str
    tags: Dict[str, str]

class UserInstanceManager:
    """
    Manages isolated EC2 instances for ActiveLog users
    Each paid user gets their own dedicated, encrypted instance
    """
    
    def __init__(self):
        self.ec2_client = boto3.client('ec2')
        self.ec2_resource = boto3.resource('ec2')
        self.kms_client = boto3.client('kms')
        self.base_ami = 'activelog-base-minimal'
        
        # Tier to instance type mapping
        self.tier_instance_mapping = {
            'starter': 't3.small',
            'professional': 't3.medium', 
            'business': 't3.large',
            'enterprise': 'm5.xlarge',
            'premium': 'm5.2xlarge'
        }
    
    def calculate_instance_type(self, tier: str) -> str:
        """Calculate appropriate EC2 instance type based on user tier"""
        return self.tier_instance_mapping.get(tier.lower(), 't3.micro')
    
    def generate_user_encryption_key(self, user_id: str) -> str:
        """Generate user-specific KMS encryption key"""
        key_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "UserOnlyAccess",
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::ACCOUNT:user/{user_id}"},
                    "Action": "kms:*",
                    "Resource": "*"
                },
                {
                    "Sid": "ActiveLogOrchestrationOnly",
                    "Effect": "Allow", 
                    "Principal": {"AWS": "arn:aws:iam::ACCOUNT:role/ActiveLogOrchestrator"},
                    "Action": [
                        "kms:Encrypt",
                        "kms:Decrypt", 
                        "kms:ReEncrypt*",
                        "kms:GenerateDataKey*",
                        "kms:DescribeKey"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        try:
            response = self.kms_client.create_key(
                Description=f'ActiveLog user {user_id} encryption key',
                KeyUsage='ENCRYPT_DECRYPT',
                Policy=str(key_policy).replace("'", '"'),
                Tags=[
                    {'TagKey': 'User', 'TagValue': user_id},
                    {'TagKey': 'Service', 'TagValue': 'ActiveLog'},
                    {'TagKey': 'Purpose', 'TagValue': 'UserDataEncryption'}
                ]
            )
            return response['KeyMetadata']['KeyId']
        except Exception as e:
            logger.error(f"Failed to create encryption key for user {user_id}: {e}")
            raise
    
    def create_user_vpc(self, user_id: str) -> Dict[str, str]:
        """Create isolated VPC for user instance"""
        vpc_cidr = f"10.{hash(user_id) % 255}.0.0/16"
        
        try:
            # Create VPC
            vpc_response = self.ec2_client.create_vpc(
                CidrBlock=vpc_cidr,
                TagSpecifications=[{
                    'ResourceType': 'vpc',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'activelog-user-{user_id}'},
                        {'Key': 'User', 'Value': user_id},
                        {'Key': 'Isolation', 'Value': 'complete'}
                    ]
                }]
            )
            vpc_id = vpc_response['Vpc']['VpcId']
            
            # Create subnet
            subnet_response = self.ec2_client.create_subnet(
                VpcId=vpc_id,
                CidrBlock=f"10.{hash(user_id) % 255}.1.0/24",
                TagSpecifications=[{
                    'ResourceType': 'subnet', 
                    'Tags': [
                        {'Key': 'Name', 'Value': f'activelog-user-{user_id}-subnet'},
                        {'Key': 'User', 'Value': user_id}
                    ]
                }]
            )
            subnet_id = subnet_response['Subnet']['SubnetId']
            
            # Create internet gateway for the VPC
            igw_response = self.ec2_client.create_internet_gateway(
                TagSpecifications=[{
                    'ResourceType': 'internet-gateway',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'activelog-user-{user_id}-igw'},
                        {'Key': 'User', 'Value': user_id}
                    ]
                }]
            )
            igw_id = igw_response['InternetGateway']['InternetGatewayId']
            
            # Attach internet gateway to VPC
            self.ec2_client.attach_internet_gateway(
                InternetGatewayId=igw_id,
                VpcId=vpc_id
            )
            
            return {
                'vpc_id': vpc_id,
                'subnet_id': subnet_id,
                'internet_gateway_id': igw_id
            }
            
        except Exception as e:
            logger.error(f"Failed to create VPC for user {user_id}: {e}")
            raise
    
    def create_user_security_group(self, user_id: str, vpc_id: str) -> str:
        """Create user-specific security group with minimal access"""
        try:
            sg_response = self.ec2_client.create_security_group(
                GroupName=f'activelog-user-{user_id}',
                Description=f'Security group for ActiveLog user {user_id} - isolated access only',
                VpcId=vpc_id,
                TagSpecifications=[{
                    'ResourceType': 'security-group',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'activelog-user-{user_id}-sg'},
                        {'Key': 'User', 'Value': user_id},
                        {'Key': 'AccessControl', 'Value': 'user-only'}
                    ]
                }]
            )
            sg_id = sg_response['GroupId']
            
            # Add minimal required rules
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS access'}]
                    },
                    {
                        'IpProtocol': 'tcp', 
                        'FromPort': 22,
                        'ToPort': 22,
                        'UserIdGroupPairs': [{'GroupId': sg_id, 'Description': 'SSH within security group only'}]
                    }
                ]
            )
            
            return sg_id
            
        except Exception as e:
            logger.error(f"Failed to create security group for user {user_id}: {e}")
            raise
    
    def create_user_instance(self, user_id: str, tier: str) -> Dict[str, Any]:
        """
        Create a dedicated, isolated EC2 instance for a user
        Returns instance details and configuration
        """
        try:
            # Calculate instance specifications
            instance_type = self.calculate_instance_type(tier)
            encryption_key_id = self.generate_user_encryption_key(user_id)
            
            # Create isolated networking
            network_config = self.create_user_vpc(user_id)
            vpc_id = network_config['vpc_id']
            subnet_id = network_config['subnet_id']
            
            # Create security group
            security_group_id = self.create_user_security_group(user_id, vpc_id)
            
            # Instance configuration
            instance_config = InstanceConfig(
                user_id=user_id,
                tier=tier,
                instance_type=instance_type,
                ami_id=self.base_ami,
                security_group_id=security_group_id,
                vpc_id=vpc_id,
                subnet_id=subnet_id,
                encryption_key_id=encryption_key_id,
                tags={
                    'DataOwner': user_id,
                    'ActiveLogRole': 'orchestrator_only',
                    'UserControlled': 'true',
                    'Tier': tier,
                    'CreatedAt': datetime.utcnow().isoformat(),
                    'Name': f'activelog-user-{user_id}'
                }
            )
            
            # Launch instance
            instance_response = self.provision_instance(instance_config)
            
            logger.info(f"Successfully created isolated instance for user {user_id}")
            return {
                'instance_id': instance_response['instance_id'],
                'config': instance_config,
                'network': network_config,
                'status': 'provisioning'
            }
            
        except Exception as e:
            logger.error(f"Failed to create instance for user {user_id}: {e}")
            raise
    
    def provision_instance(self, config: InstanceConfig) -> Dict[str, str]:
        """Provision EC2 instance with the given configuration"""
        try:
            # User data script for instance initialization
            user_data_script = f'''#!/bin/bash
echo "Initializing ActiveLog instance for user {config.user_id}"
echo "USER_ID={config.user_id}" > /opt/activelog/.env
echo "TIER={config.tier}" >> /opt/activelog/.env
echo "ENCRYPTION_KEY={config.encryption_key_id}" >> /opt/activelog/.env

# Start ActiveLog services with user isolation
systemctl enable activelog-user-services
systemctl start activelog-user-services
'''
            
            response = self.ec2_client.run_instances(
                ImageId=config.ami_id,
                MinCount=1,
                MaxCount=1,
                InstanceType=config.instance_type,
                SecurityGroupIds=[config.security_group_id],
                SubnetId=config.subnet_id,
                UserData=user_data_script,
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [{'Key': k, 'Value': v} for k, v in config.tags.items()]
                }],
                BlockDeviceMappings=[{
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'VolumeType': 'gp3',
                        'VolumeSize': 100,
                        'Encrypted': True,
                        'KmsKeyId': config.encryption_key_id,
                        'DeleteOnTermination': True
                    }
                }],
                IamInstanceProfile={
                    'Name': f'ActiveLogUserRole-{config.user_id}'
                }
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            return {'instance_id': instance_id}
            
        except Exception as e:
            logger.error(f"Failed to provision instance: {e}")
            raise
    
    def get_user_instance_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get status of user's instance"""
        try:
            response = self.ec2_client.describe_instances(
                Filters=[
                    {'Name': 'tag:DataOwner', 'Values': [user_id]},
                    {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
                ]
            )
            
            if response['Reservations']:
                instance = response['Reservations'][0]['Instances'][0]
                return {
                    'instance_id': instance['InstanceId'],
                    'state': instance['State']['Name'],
                    'public_ip': instance.get('PublicIpAddress'),
                    'private_ip': instance['PrivateIpAddress'],
                    'instance_type': instance['InstanceType'],
                    'launch_time': instance['LaunchTime']
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get instance status for user {user_id}: {e}")
            return None
    
    def terminate_user_instance(self, user_id: str) -> bool:
        """Terminate user's instance and clean up resources"""
        try:
            # Get instance details
            instance_status = self.get_user_instance_status(user_id)
            if not instance_status:
                logger.warning(f"No instance found for user {user_id}")
                return True
            
            instance_id = instance_status['instance_id']
            
            # Terminate instance
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            
            # Clean up VPC resources (security groups, VPC, etc.)
            # This would be done after instance termination
            logger.info(f"Terminated instance {instance_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate instance for user {user_id}: {e}")
            return False