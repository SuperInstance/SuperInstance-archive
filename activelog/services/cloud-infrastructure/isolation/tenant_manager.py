"""
Tenant Management System for User Data Isolation
Provides complete isolation between users with VPC-level separation
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import asdict
import json
import hashlib
import uuid

from core.models import (
    User, UserTier, UserIsolationInfo,
    current_timestamp, generate_id
)

class TenantManager:
    """Manages multi-tenant isolation and security"""
    
    def __init__(self, config: Dict[str, Any], database_manager):
        self.config = config
        self.db = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Isolation configuration
        self.isolation_config = config.get('isolation', {})
        self.isolation_level = self.isolation_config.get('isolation_level', 'vpc')
        
        # Network isolation settings
        self.vpc_cidr_base = self.isolation_config.get('user_vpc_cidr_base', '172.16.0.0/12')
        self.vpc_cidr_mask = self.isolation_config.get('vpc_cidr_mask', 16)
        
        # Security settings
        self.enable_strict_isolation = self.isolation_config.get('enable_strict_isolation', True)
        
        # Track allocated resources
        self.allocated_vpc_cidrs = set()
        self.user_isolation_cache = {}
        
    async def create_user_isolation(self, user: User) -> UserIsolationInfo:
        """Create complete isolation environment for a new user"""
        try:
            self.logger.info(f"Creating isolation environment for user {user.user_id}")
            
            # Generate unique VPC CIDR
            vpc_cidr = self._generate_unique_vpc_cidr(user.user_id)
            
            # Create VPC (mock implementation - replace with actual AWS calls)
            vpc_id = await self._create_user_vpc(user, vpc_cidr)
            
            # Create subnets
            subnet_ids = await self._create_user_subnets(user, vpc_id, vpc_cidr)
            
            # Create security groups
            security_group_ids = await self._create_user_security_groups(user, vpc_id)
            
            # Create encryption key
            encryption_key_id = await self._create_user_encryption_key(user)
            
            # Create IAM role
            iam_role_arn = await self._create_user_iam_role(user)
            
            # Create isolation info
            isolation_info = UserIsolationInfo(
                user_id=user.user_id,
                vpc_id=vpc_id,
                subnet_ids=subnet_ids,
                security_group_ids=security_group_ids,
                encryption_key_id=encryption_key_id,
                iam_role_arn=iam_role_arn,
                isolation_level=self.isolation_level
            )
            
            # Update user record
            user.vpc_id = vpc_id
            user.encryption_key_id = encryption_key_id
            await self.db.update_user(user)
            
            # Cache isolation info
            self.user_isolation_cache[user.user_id] = isolation_info
            
            # Save isolation configuration
            await self.db.save_user_isolation_info(isolation_info)
            
            self.logger.info(f"Created isolation environment for user {user.user_id}: VPC {vpc_id}")
            
            return isolation_info
            
        except Exception as e:
            self.logger.error(f"Error creating user isolation for {user.user_id}: {e}")
            raise
    
    async def get_user_isolation(self, user_id: str) -> Optional[UserIsolationInfo]:
        """Get isolation information for a user"""
        try:
            # Check cache first
            if user_id in self.user_isolation_cache:
                return self.user_isolation_cache[user_id]
            
            # Load from database
            isolation_info = await self.db.get_user_isolation_info(user_id)
            
            if isolation_info:
                self.user_isolation_cache[user_id] = isolation_info
            
            return isolation_info
            
        except Exception as e:
            self.logger.error(f"Error getting user isolation for {user_id}: {e}")
            return None
    
    async def validate_user_access(self, user_id: str, resource_id: str, 
                                 resource_type: str) -> bool:
        """Validate that user has access to a specific resource"""
        try:
            # Get user isolation info
            isolation_info = await self.get_user_isolation(user_id)
            if not isolation_info:
                return False
            
            # Validate based on resource type
            if resource_type == 'instance':
                return await self._validate_instance_access(user_id, resource_id, isolation_info)
            elif resource_type == 'subnet':
                return resource_id in isolation_info.subnet_ids
            elif resource_type == 'security_group':
                return resource_id in isolation_info.security_group_ids
            elif resource_type == 'vpc':
                return resource_id == isolation_info.vpc_id
            else:
                self.logger.warning(f"Unknown resource type for validation: {resource_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating access for user {user_id}: {e}")
            return False
    
    async def _validate_instance_access(self, user_id: str, instance_id: str,
                                      isolation_info: UserIsolationInfo) -> bool:
        """Validate that user has access to a specific instance"""
        try:
            # Get instance details
            instance = await self.db.get_instance(instance_id)
            if not instance:
                return False
            
            # Check if instance belongs to user
            if instance.user_id != user_id:
                return False
            
            # Check if instance is in user's VPC
            if instance.vpc_id != isolation_info.vpc_id:
                return False
            
            # Check if instance subnet is allowed
            if instance.subnet_id not in isolation_info.subnet_ids:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating instance access: {e}")
            return False
    
    def _generate_unique_vpc_cidr(self, user_id: str) -> str:
        """Generate a unique VPC CIDR for the user"""
        # Use hash of user_id to generate deterministic but unique CIDR
        user_hash = hashlib.md5(user_id.encode()).hexdigest()
        
        # Convert first 4 hex chars to decimal for unique network
        network_suffix = int(user_hash[:4], 16) % 4096  # Ensure it fits in /12
        
        # Calculate CIDR based on base network
        # For 172.16.0.0/12, we can allocate /16 networks from 172.16.0.0 to 172.31.255.255
        second_octet = 16 + (network_suffix // 256)
        third_octet = network_suffix % 256
        
        vpc_cidr = f"172.{second_octet}.{third_octet}.0/{self.vpc_cidr_mask}"
        
        # Ensure uniqueness
        while vpc_cidr in self.allocated_vpc_cidrs:
            network_suffix = (network_suffix + 1) % 4096
            second_octet = 16 + (network_suffix // 256)
            third_octet = network_suffix % 256
            vpc_cidr = f"172.{second_octet}.{third_octet}.0/{self.vpc_cidr_mask}"
        
        self.allocated_vpc_cidrs.add(vpc_cidr)
        return vpc_cidr
    
    async def _create_user_vpc(self, user: User, vpc_cidr: str) -> str:
        """Create isolated VPC for user"""
        try:
            # Mock VPC creation (replace with actual AWS VPC creation)
            vpc_id = f"vpc-{user.user_id}-{uuid.uuid4().hex[:8]}"
            
            vpc_config = {
                'VpcId': vpc_id,
                'CidrBlock': vpc_cidr,
                'State': 'available',
                'Tags': [
                    {'Key': 'Name', 'Value': f"VPC-{user.user_id}"},
                    {'Key': 'UserId', 'Value': user.user_id},
                    {'Key': 'IsolationLevel', 'Value': self.isolation_level},
                    {'Key': 'CreatedBy', 'Value': 'cloud-infrastructure-system'},
                    {'Key': 'Environment', 'Value': 'production'}
                ]
            }
            
            # In production, create actual VPC:
            # ec2_client.create_vpc(CidrBlock=vpc_cidr, TagSpecifications=tags)
            
            self.logger.info(f"Created VPC {vpc_id} with CIDR {vpc_cidr} for user {user.user_id}")
            
            # Store VPC configuration
            await self.db.save_vpc_config(vpc_config)
            
            return vpc_id
            
        except Exception as e:
            self.logger.error(f"Error creating VPC for user {user.user_id}: {e}")
            raise
    
    async def _create_user_subnets(self, user: User, vpc_id: str, vpc_cidr: str) -> List[str]:
        """Create isolated subnets within user's VPC"""
        try:
            subnets = []
            
            # Create private subnets in multiple AZs for high availability
            availability_zones = self.config['aws']['availability_zones']
            
            # Calculate subnet CIDRs (split VPC CIDR into smaller subnets)
            base_ip = vpc_cidr.split('/')[0]
            base_parts = base_ip.split('.')
            
            for i, az in enumerate(availability_zones[:3]):  # Max 3 AZs
                # Create /24 subnets within the /16 VPC
                subnet_cidr = f"{base_parts[0]}.{base_parts[1]}.{i}.0/24"
                subnet_id = f"subnet-{user.user_id}-{az}-{uuid.uuid4().hex[:8]}"
                
                subnet_config = {
                    'SubnetId': subnet_id,
                    'VpcId': vpc_id,
                    'CidrBlock': subnet_cidr,
                    'AvailabilityZone': az,
                    'State': 'available',
                    'Tags': [
                        {'Key': 'Name', 'Value': f"Subnet-{user.user_id}-{az}"},
                        {'Key': 'UserId', 'Value': user.user_id},
                        {'Key': 'Type', 'Value': 'private'},
                        {'Key': 'AZ', 'Value': az}
                    ]
                }
                
                # In production:
                # ec2_client.create_subnet(VpcId=vpc_id, CidrBlock=subnet_cidr, AvailabilityZone=az)
                
                subnets.append(subnet_id)
                await self.db.save_subnet_config(subnet_config)
            
            self.logger.info(f"Created {len(subnets)} subnets for user {user.user_id} in VPC {vpc_id}")
            
            return subnets
            
        except Exception as e:
            self.logger.error(f"Error creating subnets for user {user.user_id}: {e}")
            raise
    
    async def _create_user_security_groups(self, user: User, vpc_id: str) -> List[str]:
        """Create security groups for user isolation"""
        try:
            security_groups = []
            
            # Web server security group
            web_sg_id = f"sg-{user.user_id}-web-{uuid.uuid4().hex[:8]}"
            web_sg_config = {
                'GroupId': web_sg_id,
                'GroupName': f"sg-{user.user_id}-web",
                'Description': f"Web server security group for user {user.user_id}",
                'VpcId': vpc_id,
                'IngressRules': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'CidrBlocks': ['0.0.0.0/0']
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'CidrBlocks': ['0.0.0.0/0']
                    }
                ],
                'Tags': [
                    {'Key': 'Name', 'Value': f"sg-{user.user_id}-web"},
                    {'Key': 'UserId', 'Value': user.user_id},
                    {'Key': 'Type', 'Value': 'web'}
                ]
            }
            
            security_groups.append(web_sg_id)
            await self.db.save_security_group_config(web_sg_config)
            
            # SSH access security group
            ssh_sg_id = f"sg-{user.user_id}-ssh-{uuid.uuid4().hex[:8]}"
            ssh_sg_config = {
                'GroupId': ssh_sg_id,
                'GroupName': f"sg-{user.user_id}-ssh",
                'Description': f"SSH access security group for user {user.user_id}",
                'VpcId': vpc_id,
                'IngressRules': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'CidrBlocks': ['0.0.0.0/0']  # In production, restrict to specific IPs
                    }
                ],
                'Tags': [
                    {'Key': 'Name', 'Value': f"sg-{user.user_id}-ssh"},
                    {'Key': 'UserId', 'Value': user.user_id},
                    {'Key': 'Type', 'Value': 'ssh'}
                ]
            }
            
            security_groups.append(ssh_sg_id)
            await self.db.save_security_group_config(ssh_sg_config)
            
            # Database security group (internal access only)
            db_sg_id = f"sg-{user.user_id}-db-{uuid.uuid4().hex[:8]}"
            db_sg_config = {
                'GroupId': db_sg_id,
                'GroupName': f"sg-{user.user_id}-db",
                'Description': f"Database security group for user {user.user_id}",
                'VpcId': vpc_id,
                'IngressRules': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 3306,
                        'ToPort': 3306,
                        'SourceSecurityGroupId': web_sg_id  # Only allow from web servers
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'SourceSecurityGroupId': web_sg_id  # PostgreSQL
                    }
                ],
                'Tags': [
                    {'Key': 'Name', 'Value': f"sg-{user.user_id}-db"},
                    {'Key': 'UserId', 'Value': user.user_id},
                    {'Key': 'Type', 'Value': 'database'}
                ]
            }
            
            security_groups.append(db_sg_id)
            await self.db.save_security_group_config(db_sg_config)
            
            self.logger.info(f"Created {len(security_groups)} security groups for user {user.user_id}")
            
            return security_groups
            
        except Exception as e:
            self.logger.error(f"Error creating security groups for user {user.user_id}: {e}")
            raise
    
    async def _create_user_encryption_key(self, user: User) -> str:
        """Create user-specific encryption key"""
        try:
            # Mock KMS key creation (replace with actual KMS calls)
            key_id = f"arn:aws:kms:us-west-2:123456789012:key/{uuid.uuid4()}"
            
            key_config = {
                'KeyId': key_id,
                'UserId': user.user_id,
                'KeyUsage': 'ENCRYPT_DECRYPT',
                'KeySpec': 'SYMMETRIC_DEFAULT',
                'Description': f"Encryption key for user {user.user_id}",
                'KeyPolicy': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'AWS': f"arn:aws:iam::123456789012:user/{user.user_id}"},
                            'Action': [
                                'kms:Encrypt',
                                'kms:Decrypt',
                                'kms:ReEncrypt*',
                                'kms:GenerateDataKey*',
                                'kms:DescribeKey'
                            ],
                            'Resource': '*'
                        }
                    ]
                },
                'Tags': [
                    {'TagKey': 'UserId', 'TagValue': user.user_id},
                    {'TagKey': 'Purpose', 'TagValue': 'user-data-encryption'}
                ]
            }
            
            # In production:
            # kms_client.create_key(Policy=json.dumps(key_policy), Description=description, Tags=tags)
            
            await self.db.save_encryption_key_config(key_config)
            
            self.logger.info(f"Created encryption key for user {user.user_id}")
            
            return key_id
            
        except Exception as e:
            self.logger.error(f"Error creating encryption key for user {user.user_id}: {e}")
            raise
    
    async def _create_user_iam_role(self, user: User) -> str:
        """Create IAM role with minimal permissions for user"""
        try:
            role_name = f"CloudInfraRole-{user.user_id}"
            role_arn = f"arn:aws:iam::123456789012:role/{role_name}"
            
            # Base permissions policy
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ec2:DescribeInstances",
                            "ec2:DescribeInstanceStatus",
                            "ec2:StartInstances",
                            "ec2:StopInstances",
                            "ec2:RebootInstances"
                        ],
                        "Resource": "*",
                        "Condition": {
                            "StringEquals": {
                                "ec2:ResourceTag/UserId": user.user_id
                            }
                        }
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "kms:Encrypt",
                            "kms:Decrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*",
                            "kms:DescribeKey"
                        ],
                        "Resource": user.encryption_key_id or "*",
                        "Condition": {
                            "StringEquals": {
                                "kms:ViaService": f"ec2.{self.config['aws']['region']}.amazonaws.com"
                            }
                        }
                    }
                ]
            }
            
            # Add tier-specific permissions
            if user.tier == UserTier.ENTERPRISE:
                policy_document["Statement"].extend([
                    {
                        "Effect": "Allow",
                        "Action": [
                            "cloudwatch:GetMetricStatistics",
                            "cloudwatch:ListMetrics",
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Resource": "*"
                    }
                ])
            
            role_config = {
                'RoleName': role_name,
                'RoleArn': role_arn,
                'UserId': user.user_id,
                'AssumeRolePolicyDocument': {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "ec2.amazonaws.com"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                },
                'PolicyDocument': policy_document,
                'Tags': [
                    {'Key': 'UserId', 'Value': user.user_id},
                    {'Key': 'Tier', 'Value': user.tier.value}
                ]
            }
            
            # In production:
            # iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument=assume_role_policy)
            # iam_client.put_role_policy(RoleName=role_name, PolicyName=policy_name, PolicyDocument=policy)
            
            await self.db.save_iam_role_config(role_config)
            
            self.logger.info(f"Created IAM role {role_name} for user {user.user_id}")
            
            return role_arn
            
        except Exception as e:
            self.logger.error(f"Error creating IAM role for user {user.user_id}: {e}")
            raise
    
    async def cleanup_user_isolation(self, user_id: str) -> bool:
        """Clean up all isolation resources for a user"""
        try:
            isolation_info = await self.get_user_isolation(user_id)
            if not isolation_info:
                return True
            
            self.logger.info(f"Cleaning up isolation resources for user {user_id}")
            
            # Terminate all user instances first
            user_instances = await self.db.get_user_instances(user_id)
            for instance in user_instances:
                if instance.state not in ['terminated', 'terminating']:
                    # Terminate instance (would be handled by provisioner)
                    self.logger.info(f"Terminating instance {instance.instance_id}")
            
            # Delete security groups
            for sg_id in isolation_info.security_group_ids:
                self.logger.info(f"Deleting security group {sg_id}")
                # In production: ec2_client.delete_security_group(GroupId=sg_id)
                await self.db.delete_security_group_config(sg_id)
            
            # Delete subnets
            for subnet_id in isolation_info.subnet_ids:
                self.logger.info(f"Deleting subnet {subnet_id}")
                # In production: ec2_client.delete_subnet(SubnetId=subnet_id)
                await self.db.delete_subnet_config(subnet_id)
            
            # Delete VPC
            self.logger.info(f"Deleting VPC {isolation_info.vpc_id}")
            # In production: ec2_client.delete_vpc(VpcId=isolation_info.vpc_id)
            await self.db.delete_vpc_config(isolation_info.vpc_id)
            
            # Delete encryption key (schedule deletion)
            self.logger.info(f"Scheduling deletion of encryption key {isolation_info.encryption_key_id}")
            # In production: kms_client.schedule_key_deletion(KeyId=isolation_info.encryption_key_id)
            
            # Delete IAM role
            role_name = isolation_info.iam_role_arn.split('/')[-1]
            self.logger.info(f"Deleting IAM role {role_name}")
            # In production: iam_client.delete_role(RoleName=role_name)
            await self.db.delete_iam_role_config(role_name)
            
            # Remove from cache
            if user_id in self.user_isolation_cache:
                del self.user_isolation_cache[user_id]
            
            # Delete isolation info from database
            await self.db.delete_user_isolation_info(user_id)
            
            self.logger.info(f"Successfully cleaned up isolation resources for user {user_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up user isolation for {user_id}: {e}")
            return False
    
    async def audit_user_isolation(self, user_id: str) -> Dict[str, Any]:
        """Audit isolation configuration for a user"""
        try:
            isolation_info = await self.get_user_isolation(user_id)
            if not isolation_info:
                return {
                    'user_id': user_id,
                    'isolated': False,
                    'error': 'No isolation configuration found'
                }
            
            audit_results = {
                'user_id': user_id,
                'isolated': True,
                'isolation_level': isolation_info.isolation_level,
                'vpc_id': isolation_info.vpc_id,
                'subnet_count': len(isolation_info.subnet_ids),
                'security_group_count': len(isolation_info.security_group_ids),
                'encryption_key_id': isolation_info.encryption_key_id,
                'iam_role_arn': isolation_info.iam_role_arn,
                'checks': {}
            }
            
            # Perform isolation checks
            checks = audit_results['checks']
            
            # Check VPC isolation
            checks['vpc_isolated'] = await self._check_vpc_isolation(isolation_info.vpc_id)
            
            # Check subnet isolation
            checks['subnets_isolated'] = await self._check_subnet_isolation(isolation_info.subnet_ids)
            
            # Check security group isolation
            checks['security_groups_isolated'] = await self._check_security_group_isolation(
                isolation_info.security_group_ids, isolation_info.vpc_id
            )
            
            # Check encryption key access
            checks['encryption_key_accessible'] = await self._check_encryption_key_access(
                user_id, isolation_info.encryption_key_id
            )
            
            # Check IAM role permissions
            checks['iam_role_valid'] = await self._check_iam_role_permissions(
                isolation_info.iam_role_arn, user_id
            )
            
            # Overall compliance score
            passed_checks = sum(1 for check in checks.values() if check)
            total_checks = len(checks)
            compliance_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
            
            audit_results['compliance_score'] = compliance_score
            audit_results['compliant'] = compliance_score >= 90  # 90% threshold
            audit_results['timestamp'] = current_timestamp().isoformat()
            
            return audit_results
            
        except Exception as e:
            self.logger.error(f"Error auditing user isolation for {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    async def _check_vpc_isolation(self, vpc_id: str) -> bool:
        """Check VPC isolation configuration"""
        try:
            vpc_config = await self.db.get_vpc_config(vpc_id)
            return vpc_config is not None and vpc_config.get('State') == 'available'
        except:
            return False
    
    async def _check_subnet_isolation(self, subnet_ids: List[str]) -> bool:
        """Check subnet isolation configuration"""
        try:
            for subnet_id in subnet_ids:
                subnet_config = await self.db.get_subnet_config(subnet_id)
                if not subnet_config or subnet_config.get('State') != 'available':
                    return False
            return True
        except:
            return False
    
    async def _check_security_group_isolation(self, sg_ids: List[str], vpc_id: str) -> bool:
        """Check security group isolation"""
        try:
            for sg_id in sg_ids:
                sg_config = await self.db.get_security_group_config(sg_id)
                if not sg_config or sg_config.get('VpcId') != vpc_id:
                    return False
            return True
        except:
            return False
    
    async def _check_encryption_key_access(self, user_id: str, key_id: str) -> bool:
        """Check encryption key access"""
        try:
            key_config = await self.db.get_encryption_key_config(key_id)
            return key_config is not None and key_config.get('UserId') == user_id
        except:
            return False
    
    async def _check_iam_role_permissions(self, role_arn: str, user_id: str) -> bool:
        """Check IAM role permissions"""
        try:
            role_name = role_arn.split('/')[-1]
            role_config = await self.db.get_iam_role_config(role_name)
            return role_config is not None and role_config.get('UserId') == user_id
        except:
            return False
    
    async def get_isolation_metrics(self) -> Dict[str, Any]:
        """Get isolation system metrics"""
        try:
            # Count isolated users
            total_users = await self.db.count_total_users()
            isolated_users = await self.db.count_isolated_users()
            
            # Count allocated resources
            total_vpcs = len(self.allocated_vpc_cidrs)
            cached_isolations = len(self.user_isolation_cache)
            
            return {
                'total_users': total_users,
                'isolated_users': isolated_users,
                'isolation_coverage': (isolated_users / total_users) * 100 if total_users > 0 else 0,
                'allocated_vpcs': total_vpcs,
                'cached_isolations': cached_isolations,
                'isolation_level': self.isolation_level,
                'strict_isolation_enabled': self.enable_strict_isolation,
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting isolation metrics: {e}")
            return {
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for tenant manager"""
        try:
            # Test isolation functionality
            test_passed = True
            error_message = None
            
            try:
                # Test VPC CIDR generation
                test_cidr = self._generate_unique_vpc_cidr("health-check-test")
                if not test_cidr:
                    test_passed = False
                    error_message = "VPC CIDR generation failed"
            except Exception as e:
                test_passed = False
                error_message = f"Health check test failed: {e}"
            
            # Get system metrics
            metrics = await self.get_isolation_metrics()
            
            return {
                'service': 'tenant_manager',
                'healthy': test_passed,
                'error': error_message,
                'isolation_level': self.isolation_level,
                'strict_isolation': self.enable_strict_isolation,
                'metrics': metrics,
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Tenant manager health check failed: {e}")
            return {
                'service': 'tenant_manager',
                'healthy': False,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }