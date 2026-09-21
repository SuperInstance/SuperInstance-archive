#!/usr/bin/env python3
"""
ActiveLog.AI Master Infrastructure Deployment Script
Deploys the complete AWS infrastructure for the ActiveLog.AI master platform

This script creates:
1. VPC with multi-AZ networking
2. Route 53 domain management
3. CloudFront global CDN
4. Master servers with auto-scaling
5. Security groups and IAM roles
6. Monitoring and logging
"""

import json
import boto3
import time
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'activelog-deployment-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ServerConfig:
    """Configuration for each master server"""
    name: str
    instance_type: str
    min_size: int
    max_size: int
    desired_capacity: int
    port: int
    health_check_path: str
    description: str

class MasterInfrastructureDeployer:
    def __init__(self, region='us-east-1', environment='master'):
        self.region = region
        self.environment = environment
        self.project_name = 'activelog-ai'
        
        # Initialize AWS clients
        self.ec2 = boto3.client('ec2', region_name=region)
        self.elbv2 = boto3.client('elbv2', region_name=region)
        self.autoscaling = boto3.client('autoscaling', region_name=region)
        self.route53 = boto3.client('route53')
        self.cloudfront = boto3.client('cloudfront')
        self.iam = boto3.client('iam')
        self.cloudwatch = boto3.client('cloudwatch')
        self.s3 = boto3.client('s3')
        
        # Master server configurations
        self.master_servers = {
            'master-backend': ServerConfig(
                name='master-backend',
                instance_type='t3.medium',
                min_size=1,
                max_size=5,
                desired_capacity=2,
                port=8000,
                health_check_path='/health',
                description='Authentication, JWT management, basic payments'
            ),
            'master-repository': ServerConfig(
                name='master-repository',
                instance_type='t3.large',
                min_size=1,
                max_size=3,
                desired_capacity=1,
                port=8001,
                health_check_path='/health',
                description='All deployment files, version control'
            ),
            'master-deployer': ServerConfig(
                name='master-deployer',
                instance_type='t3.medium',
                min_size=1,
                max_size=4,
                desired_capacity=2,
                port=8002,
                health_check_path='/health',
                description='Custom deployment generator with EC2 automation'
            ),
            'master-trainer': ServerConfig(
                name='master-trainer',
                instance_type='g4dn.xlarge',
                min_size=0,
                max_size=2,
                desired_capacity=0,  # On-demand scaling
                port=8003,
                health_check_path='/health',
                description='Model training workshop (GPU-enabled)'
            ),
            'master-builder': ServerConfig(
                name='master-builder',
                instance_type='t3.large',
                min_size=1,
                max_size=3,
                desired_capacity=1,
                port=8004,
                health_check_path='/health',
                description='CI/CD for new features'
            ),
            'master-default-user': ServerConfig(
                name='master-default-user',
                instance_type='t3.small',
                min_size=1,
                max_size=2,
                desired_capacity=1,
                port=8005,
                health_check_path='/health',
                description='Template configurations'
            ),
            'master-runner': ServerConfig(
                name='master-runner',
                instance_type='c5.2xlarge',
                min_size=1,
                max_size=5,
                desired_capacity=2,
                port=8006,
                health_check_path='/health',
                description='High-performance compute for weak devices'
            )
        }
        
        self.domains = [
            'activelog.ai',
            'activeledger.ai',
            'activelogai.com',
            'makerslog.ai'
        ]

    def deploy_infrastructure(self):
        """Main deployment orchestration"""
        logger.info("Starting ActiveLog.AI Master Infrastructure Deployment")
        
        try:
            # Step 1: Create VPC and Networking
            vpc_id, subnet_info = self.create_vpc_and_networking()
            
            # Step 2: Create Security Groups
            security_groups = self.create_security_groups(vpc_id)
            
            # Step 3: Create IAM Roles
            iam_roles = self.create_iam_roles()
            
            # Step 4: Create S3 Buckets
            s3_buckets = self.create_s3_buckets()
            
            # Step 5: Deploy Master Servers
            server_resources = self.deploy_master_servers(
                subnet_info, security_groups, iam_roles
            )
            
            # Step 6: Configure Load Balancers
            load_balancers = self.create_load_balancers(
                vpc_id, subnet_info['public'], security_groups, server_resources
            )
            
            # Step 7: Setup Route 53
            self.setup_route53(load_balancers)
            
            # Step 8: Configure CloudFront CDN
            self.setup_cloudfront(s3_buckets, load_balancers)
            
            # Step 9: Setup Monitoring and Logging
            self.setup_monitoring(server_resources)
            
            # Step 10: Configure Auto-scaling
            self.configure_autoscaling(server_resources)
            
            logger.info("✅ ActiveLog.AI Master Infrastructure deployed successfully!")
            
            # Generate deployment summary
            self.generate_deployment_summary(
                vpc_id, subnet_info, security_groups, server_resources, 
                load_balancers, s3_buckets
            )
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {str(e)}")
            raise

    def create_vpc_and_networking(self):
        """Create VPC with public/private subnets across 3 AZs"""
        logger.info("Creating VPC and networking infrastructure...")
        
        # Create VPC
        vpc_response = self.ec2.create_vpc(
            CidrBlock='10.0.0.0/16',
            EnableDnsHostnames=True,
            EnableDnsSupport=True,
            TagSpecifications=[{
                'ResourceType': 'vpc',
                'Tags': [
                    {'Key': 'Name', 'Value': f'{self.project_name}-{self.environment}-vpc'},
                    {'Key': 'Project', 'Value': self.project_name},
                    {'Key': 'Environment', 'Value': self.environment}
                ]
            }]
        )
        
        vpc_id = vpc_response['Vpc']['VpcId']
        logger.info(f"Created VPC: {vpc_id}")
        
        # Get available zones
        az_response = self.ec2.describe_availability_zones(
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        availability_zones = [az['ZoneName'] for az in az_response['AvailabilityZones'][:3]]
        
        # Create Internet Gateway
        igw_response = self.ec2.create_internet_gateway(
            TagSpecifications=[{
                'ResourceType': 'internet-gateway',
                'Tags': [
                    {'Key': 'Name', 'Value': f'{self.project_name}-{self.environment}-igw'},
                    {'Key': 'Project', 'Value': self.project_name}
                ]
            }]
        )
        igw_id = igw_response['InternetGateway']['InternetGatewayId']
        
        # Attach IGW to VPC
        self.ec2.attach_internet_gateway(
            InternetGatewayId=igw_id,
            VpcId=vpc_id
        )
        
        # Create subnets
        subnet_info = {
            'public': [],
            'private': [],
            'nat_gateways': []
        }
        
        for i, az in enumerate(availability_zones):
            # Public subnet
            public_subnet = self.ec2.create_subnet(
                VpcId=vpc_id,
                CidrBlock=f'10.0.{i*10}.0/24',
                AvailabilityZone=az,
                TagSpecifications=[{
                    'ResourceType': 'subnet',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'{self.project_name}-public-{az}'},
                        {'Key': 'Type', 'Value': 'public'}
                    ]
                }]
            )
            public_subnet_id = public_subnet['Subnet']['SubnetId']
            subnet_info['public'].append(public_subnet_id)
            
            # Private subnet
            private_subnet = self.ec2.create_subnet(
                VpcId=vpc_id,
                CidrBlock=f'10.0.{i*10+5}.0/24',
                AvailabilityZone=az,
                TagSpecifications=[{
                    'ResourceType': 'subnet',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'{self.project_name}-private-{az}'},
                        {'Key': 'Type', 'Value': 'private'}
                    ]
                }]
            )
            private_subnet_id = private_subnet['Subnet']['SubnetId']
            subnet_info['private'].append(private_subnet_id)
            
            # Create NAT Gateway
            eip_response = self.ec2.allocate_address(Domain='vpc')
            eip_id = eip_response['AllocationId']
            
            nat_response = self.ec2.create_nat_gateway(
                SubnetId=public_subnet_id,
                AllocationId=eip_id,
                TagSpecifications=[{
                    'ResourceType': 'nat-gateway',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'{self.project_name}-nat-{az}'},
                    ]
                }]
            )
            nat_id = nat_response['NatGateway']['NatGatewayId']
            subnet_info['nat_gateways'].append(nat_id)
            
        # Wait for NAT gateways to be available
        logger.info("Waiting for NAT gateways to become available...")
        time.sleep(120)  # NAT gateways take time to initialize
        
        # Create route tables
        self.create_route_tables(vpc_id, igw_id, subnet_info)
        
        return vpc_id, subnet_info

    def create_route_tables(self, vpc_id: str, igw_id: str, subnet_info: Dict):
        """Create and configure route tables"""
        # Public route table
        public_rt = self.ec2.create_route_table(
            VpcId=vpc_id,
            TagSpecifications=[{
                'ResourceType': 'route-table',
                'Tags': [{'Key': 'Name', 'Value': f'{self.project_name}-public-rt'}]
            }]
        )
        public_rt_id = public_rt['RouteTable']['RouteTableId']
        
        # Add route to internet gateway
        self.ec2.create_route(
            RouteTableId=public_rt_id,
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=igw_id
        )
        
        # Associate public subnets with public route table
        for subnet_id in subnet_info['public']:
            self.ec2.associate_route_table(
                SubnetId=subnet_id,
                RouteTableId=public_rt_id
            )
        
        # Create private route tables (one per AZ for NAT gateway)
        for i, (private_subnet_id, nat_id) in enumerate(zip(subnet_info['private'], subnet_info['nat_gateways'])):
            private_rt = self.ec2.create_route_table(
                VpcId=vpc_id,
                TagSpecifications=[{
                    'ResourceType': 'route-table',
                    'Tags': [{'Key': 'Name', 'Value': f'{self.project_name}-private-rt-{i}'}]
                }]
            )
            private_rt_id = private_rt['RouteTable']['RouteTableId']
            
            # Add route to NAT gateway
            self.ec2.create_route(
                RouteTableId=private_rt_id,
                DestinationCidrBlock='0.0.0.0/0',
                NatGatewayId=nat_id
            )
            
            # Associate private subnet
            self.ec2.associate_route_table(
                SubnetId=private_subnet_id,
                RouteTableId=private_rt_id
            )

    def create_security_groups(self, vpc_id: str) -> Dict[str, str]:
        """Create security groups for different services"""
        logger.info("Creating security groups...")
        
        security_groups = {}
        
        # ALB Security Group
        alb_sg = self.ec2.create_security_group(
            GroupName=f'{self.project_name}-alb-sg',
            Description='Security group for Application Load Balancer',
            VpcId=vpc_id,
            TagSpecifications=[{
                'ResourceType': 'security-group',
                'Tags': [{'Key': 'Name', 'Value': f'{self.project_name}-alb-sg'}]
            }]
        )
        alb_sg_id = alb_sg['GroupId']
        security_groups['alb'] = alb_sg_id
        
        # Allow HTTP and HTTPS traffic
        self.ec2.authorize_security_group_ingress(
            GroupId=alb_sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        
        # Master Servers Security Group
        master_sg = self.ec2.create_security_group(
            GroupName=f'{self.project_name}-master-sg',
            Description='Security group for master servers',
            VpcId=vpc_id,
            TagSpecifications=[{
                'ResourceType': 'security-group',
                'Tags': [{'Key': 'Name', 'Value': f'{self.project_name}-master-sg'}]
            }]
        )
        master_sg_id = master_sg['GroupId']
        security_groups['master'] = master_sg_id
        
        # Allow traffic from ALB
        self.ec2.authorize_security_group_ingress(
            GroupId=master_sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 8000,
                    'ToPort': 8010,
                    'UserIdGroupPairs': [{'GroupId': alb_sg_id}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '10.0.0.0/16'}]  # VPC only
                }
            ]
        )
        
        return security_groups

    def create_iam_roles(self) -> Dict[str, str]:
        """Create IAM roles for master servers"""
        logger.info("Creating IAM roles...")
        
        # Master Server Role
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        role_name = f'{self.project_name}-master-server-role'
        
        try:
            self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description='IAM role for ActiveLog.AI master servers'
            )
            
            # Attach policies
            policies = [
                'arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy',
                'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore',
                'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'
            ]
            
            for policy_arn in policies:
                self.iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            
            # Create instance profile
            instance_profile_name = f'{self.project_name}-master-instance-profile'
            self.iam.create_instance_profile(InstanceProfileName=instance_profile_name)
            self.iam.add_role_to_instance_profile(
                InstanceProfileName=instance_profile_name,
                RoleName=role_name
            )
            
        except self.iam.exceptions.EntityAlreadyExistsException:
            logger.info(f"IAM role {role_name} already exists")
        
        return {'master_server': role_name, 'instance_profile': instance_profile_name}

    def create_s3_buckets(self) -> Dict[str, str]:
        """Create S3 buckets for repositories and static content"""
        logger.info("Creating S3 buckets...")
        
        buckets = {}
        bucket_configs = [
            ('repository', 'Repository files and deployments'),
            ('static-assets', 'Static assets and CDN content'),
            ('logs', 'Application and infrastructure logs'),
            ('backups', 'System backups and snapshots')
        ]
        
        for bucket_type, description in bucket_configs:
            bucket_name = f'{self.project_name}-{self.environment}-{bucket_type}'
            
            try:
                if self.region == 'us-east-1':
                    self.s3.create_bucket(Bucket=bucket_name)
                else:
                    self.s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                
                # Configure bucket versioning
                self.s3.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                
                # Configure lifecycle policy for logs bucket
                if bucket_type == 'logs':
                    lifecycle_config = {
                        'Rules': [{
                            'ID': 'LogRetention',
                            'Status': 'Enabled',
                            'Filter': {'Prefix': ''},
                            'Transitions': [
                                {
                                    'Days': 30,
                                    'StorageClass': 'STANDARD_IA'
                                },
                                {
                                    'Days': 90,
                                    'StorageClass': 'GLACIER'
                                }
                            ],
                            'Expiration': {'Days': 365}
                        }]
                    }
                    self.s3.put_bucket_lifecycle_configuration(
                        Bucket=bucket_name,
                        LifecycleConfiguration=lifecycle_config
                    )
                
                buckets[bucket_type] = bucket_name
                logger.info(f"Created S3 bucket: {bucket_name}")
                
            except Exception as e:
                if 'BucketAlreadyExists' in str(e) or 'BucketAlreadyOwnedByYou' in str(e):
                    buckets[bucket_type] = bucket_name
                    logger.info(f"S3 bucket already exists: {bucket_name}")
                else:
                    raise
        
        return buckets

    def deploy_master_servers(self, subnet_info: Dict, security_groups: Dict, 
                            iam_roles: Dict) -> Dict[str, Dict]:
        """Deploy all master servers with auto-scaling groups"""
        logger.info("Deploying master servers...")
        
        server_resources = {}
        
        # Create launch template for each server type
        for server_name, config in self.master_servers.items():
            logger.info(f"Deploying {server_name}...")
            
            # User data script for server initialization
            user_data = self.generate_user_data_script(config)
            
            # Create launch template
            lt_name = f'{self.project_name}-{server_name}-lt'
            
            launch_template = self.ec2.create_launch_template(
                LaunchTemplateName=lt_name,
                LaunchTemplateData={
                    'ImageId': self.get_latest_amazon_linux_ami(),
                    'InstanceType': config.instance_type,
                    'KeyName': f'{self.project_name}-keypair',  # Assume key pair exists
                    'SecurityGroupIds': [security_groups['master']],
                    'IamInstanceProfile': {'Name': iam_roles['instance_profile']},
                    'UserData': user_data,
                    'TagSpecifications': [{
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': f'{self.project_name}-{server_name}'},
                            {'Key': 'Project', 'Value': self.project_name},
                            {'Key': 'Service', 'Value': server_name},
                            {'Key': 'Environment', 'Value': self.environment}
                        ]
                    }],
                    'Monitoring': {'Enabled': True}
                }
            )
            
            lt_id = launch_template['LaunchTemplate']['LaunchTemplateId']
            
            # Create auto-scaling group
            asg_name = f'{self.project_name}-{server_name}-asg'
            
            self.autoscaling.create_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                LaunchTemplate={
                    'LaunchTemplateId': lt_id,
                    'Version': '$Latest'
                },
                MinSize=config.min_size,
                MaxSize=config.max_size,
                DesiredCapacity=config.desired_capacity,
                VPCZoneIdentifier=','.join(subnet_info['private']),
                TargetGroupARNs=[],  # Will be updated when load balancers are created
                HealthCheckType='ELB' if config.desired_capacity > 0 else 'EC2',
                HealthCheckGracePeriod=300,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': f'{self.project_name}-{server_name}',
                        'PropagateAtLaunch': True,
                        'ResourceId': asg_name,
                        'ResourceType': 'auto-scaling-group'
                    }
                ]
            )
            
            server_resources[server_name] = {
                'launch_template_id': lt_id,
                'auto_scaling_group': asg_name,
                'config': config
            }
            
            logger.info(f"✅ Deployed {server_name} with ASG: {asg_name}")
        
        return server_resources

    def generate_user_data_script(self, config: ServerConfig) -> str:
        """Generate user data script for server initialization"""
        script = f"""#!/bin/bash
yum update -y
yum install -y docker python3 python3-pip git

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
pip3 install docker-compose

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{{
    "agent": {{
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    }},
    "logs": {{
        "logs_collected": {{
            "files": {{
                "collect_list": [
                    {{
                        "file_path": "/var/log/messages",
                        "log_group_name": "/aws/ec2/{config.name}",
                        "log_stream_name": "{{instance_id}}/messages"
                    }}
                ]
            }}
        }}
    }},
    "metrics": {{
        "namespace": "ActiveLog/{config.name}",
        "metrics_collected": {{
            "cpu": {{
                "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
                "metrics_collection_interval": 60,
                "totalcpu": false
            }},
            "disk": {{
                "measurement": ["used_percent"],
                "metrics_collection_interval": 60,
                "resources": ["*"]
            }},
            "mem": {{
                "measurement": ["mem_used_percent"],
                "metrics_collection_interval": 60
            }}
        }}
    }}
}}
EOF

# Start CloudWatch agent
systemctl start amazon-cloudwatch-agent
systemctl enable amazon-cloudwatch-agent

# Create application directory
mkdir -p /opt/activelog
cd /opt/activelog

# Download application code (placeholder - replace with actual deployment)
echo "Initializing {config.name} service..." > /var/log/activelog-init.log
echo "Service: {config.description}" >> /var/log/activelog-init.log

# Create a simple health check endpoint
cat > health_check.py << 'EOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {{"status": "healthy", "service": "{config.name}"}}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', {config.port}), HealthCheckHandler)
    print(f"Health check server running on port {config.port}")
    server.serve_forever()
EOF

# Start the health check service
nohup python3 health_check.py > /var/log/health_check.log 2>&1 &

# Signal that initialization is complete
/opt/aws/bin/cfn-signal -e $? --stack unknown --resource {config.name} --region {self.region} || echo "cfn-signal not available"
"""
        
        import base64
        return base64.b64encode(script.encode('utf-8')).decode('utf-8')

    def get_latest_amazon_linux_ami(self) -> str:
        """Get the latest Amazon Linux 2 AMI ID"""
        response = self.ec2.describe_images(
            Owners=['amazon'],
            Filters=[
                {'Name': 'name', 'Values': ['amzn2-ami-hvm-*']},
                {'Name': 'architecture', 'Values': ['x86_64']},
                {'Name': 'virtualization-type', 'Values': ['hvm']},
                {'Name': 'state', 'Values': ['available']}
            ]
        )
        
        # Sort by creation date and return the latest
        images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
        return images[0]['ImageId'] if images else 'ami-0abcdef1234567890'  # Fallback

    def create_load_balancers(self, vpc_id: str, public_subnets: List[str], 
                            security_groups: Dict, server_resources: Dict) -> Dict:
        """Create Application Load Balancers for master servers"""
        logger.info("Creating Application Load Balancers...")
        
        # Main ALB for all services
        alb_name = f'{self.project_name}-master-alb'
        
        alb_response = self.elbv2.create_load_balancer(
            Name=alb_name,
            Subnets=public_subnets,
            SecurityGroups=[security_groups['alb']],
            Scheme='internet-facing',
            Type='application',
            IpAddressType='ipv4',
            Tags=[
                {'Key': 'Name', 'Value': alb_name},
                {'Key': 'Project', 'Value': self.project_name}
            ]
        )
        
        alb_arn = alb_response['LoadBalancers'][0]['LoadBalancerArn']
        alb_dns_name = alb_response['LoadBalancers'][0]['DNSName']
        alb_zone_id = alb_response['LoadBalancers'][0]['CanonicalHostedZoneId']
        
        logger.info(f"Created ALB: {alb_dns_name}")
        
        # Create target groups and listeners for each service
        target_groups = {}
        
        for server_name, resources in server_resources.items():
            config = resources['config']
            
            # Create target group
            tg_name = f'{self.project_name}-{server_name}-tg'
            
            tg_response = self.elbv2.create_target_group(
                Name=tg_name,
                Protocol='HTTP',
                Port=config.port,
                VpcId=vpc_id,
                HealthCheckProtocol='HTTP',
                HealthCheckPath=config.health_check_path,
                HealthCheckIntervalSeconds=30,
                HealthCheckTimeoutSeconds=5,
                HealthyThresholdCount=2,
                UnhealthyThresholdCount=5,
                Tags=[
                    {'Key': 'Name', 'Value': tg_name},
                    {'Key': 'Service', 'Value': server_name}
                ]
            )
            
            tg_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
            target_groups[server_name] = tg_arn
            
            # Update ASG to use target group
            self.autoscaling.update_auto_scaling_group(
                AutoScalingGroupName=resources['auto_scaling_group'],
                TargetGroupARNs=[tg_arn]
            )
            
        # Create main listener (HTTPS)
        listener_response = self.elbv2.create_listener(
            LoadBalancerArn=alb_arn,
            Protocol='HTTP',  # Start with HTTP, upgrade to HTTPS after SSL cert
            Port=80,
            DefaultActions=[{
                'Type': 'fixed-response',
                'FixedResponseConfig': {
                    'StatusCode': '200',
                    'ContentType': 'text/plain',
                    'MessageBody': 'ActiveLog.AI Master Infrastructure - Healthy'
                }
            }]
        )
        
        # Create listener rules for each service
        priority = 100
        for server_name, tg_arn in target_groups.items():
            self.elbv2.create_rule(
                ListenerArn=listener_response['Listeners'][0]['ListenerArn'],
                Priority=priority,
                Conditions=[{
                    'Field': 'path-pattern',
                    'Values': [f'/{server_name}/*']
                }],
                Actions=[{
                    'Type': 'forward',
                    'TargetGroupArn': tg_arn
                }]
            )
            priority += 10
        
        return {
            'alb_arn': alb_arn,
            'alb_dns_name': alb_dns_name,
            'alb_zone_id': alb_zone_id,
            'target_groups': target_groups
        }

    def setup_route53(self, load_balancers: Dict):
        """Setup Route 53 hosted zones and DNS records"""
        logger.info("Setting up Route 53 DNS management...")
        
        hosted_zones = {}
        
        for domain in self.domains:
            try:
                # Create hosted zone
                hz_response = self.route53.create_hosted_zone(
                    Name=domain,
                    CallerReference=str(int(time.time())),
                    HostedZoneConfig={
                        'Comment': f'Hosted zone for {domain}',
                        'PrivateZone': False
                    }
                )
                
                hosted_zone_id = hz_response['HostedZone']['Id']
                hosted_zones[domain] = hosted_zone_id
                
                # Create A record pointing to ALB
                self.route53.change_resource_record_sets(
                    HostedZoneId=hosted_zone_id,
                    ChangeBatch={
                        'Changes': [{
                            'Action': 'CREATE',
                            'ResourceRecordSet': {
                                'Name': domain,
                                'Type': 'A',
                                'AliasTarget': {
                                    'DNSName': load_balancers['alb_dns_name'],
                                    'EvaluateTargetHealth': True,
                                    'HostedZoneId': load_balancers['alb_zone_id']
                                }
                            }
                        }]
                    }
                )
                
                # Create www subdomain
                self.route53.change_resource_record_sets(
                    HostedZoneId=hosted_zone_id,
                    ChangeBatch={
                        'Changes': [{
                            'Action': 'CREATE',
                            'ResourceRecordSet': {
                                'Name': f'www.{domain}',
                                'Type': 'A',
                                'AliasTarget': {
                                    'DNSName': load_balancers['alb_dns_name'],
                                    'EvaluateTargetHealth': True,
                                    'HostedZoneId': load_balancers['alb_zone_id']
                                }
                            }
                        }]
                    }
                )
                
                logger.info(f"✅ Created hosted zone for {domain}")
                
            except Exception as e:
                if 'already exists' in str(e).lower():
                    logger.info(f"Hosted zone for {domain} already exists")
                else:
                    logger.error(f"Failed to create hosted zone for {domain}: {e}")

    def setup_cloudfront(self, s3_buckets: Dict, load_balancers: Dict):
        """Configure CloudFront CDN for global distribution"""
        logger.info("Setting up CloudFront CDN...")
        
        # Create CloudFront distribution
        distribution_config = {
            'CallerReference': str(int(time.time())),
            'Comment': 'ActiveLog.AI Master Infrastructure CDN',
            'Enabled': True,
            'Origins': {
                'Quantity': 2,
                'Items': [
                    {
                        'Id': 'alb-origin',
                        'DomainName': load_balancers['alb_dns_name'],
                        'CustomOriginConfig': {
                            'HTTPPort': 80,
                            'HTTPSPort': 443,
                            'OriginProtocolPolicy': 'http-only',
                            'OriginSslProtocols': {
                                'Quantity': 1,
                                'Items': ['TLSv1.2']
                            }
                        }
                    },
                    {
                        'Id': 's3-static-origin',
                        'DomainName': f"{s3_buckets['static-assets']}.s3.amazonaws.com",
                        'S3OriginConfig': {
                            'OriginAccessIdentity': ''
                        }
                    }
                ]
            },
            'DefaultCacheBehavior': {
                'TargetOriginId': 'alb-origin',
                'ViewerProtocolPolicy': 'redirect-to-https',
                'MinTTL': 0,
                'ForwardedValues': {
                    'QueryString': True,
                    'Cookies': {'Forward': 'all'}
                }
            },
            'CacheBehaviors': {
                'Quantity': 1,
                'Items': [{
                    'PathPattern': '/static/*',
                    'TargetOriginId': 's3-static-origin',
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'MinTTL': 86400,
                    'ForwardedValues': {
                        'QueryString': False,
                        'Cookies': {'Forward': 'none'}
                    }
                }]
            },
            'PriceClass': 'PriceClass_100'  # Use only North America and Europe
        }
        
        try:
            cf_response = self.cloudfront.create_distribution(
                DistributionConfig=distribution_config
            )
            
            distribution_id = cf_response['Distribution']['Id']
            distribution_domain = cf_response['Distribution']['DomainName']
            
            logger.info(f"✅ Created CloudFront distribution: {distribution_domain}")
            
        except Exception as e:
            logger.error(f"Failed to create CloudFront distribution: {e}")

    def setup_monitoring(self, server_resources: Dict):
        """Setup CloudWatch monitoring and logging"""
        logger.info("Setting up monitoring and logging...")
        
        # Create CloudWatch dashboards
        dashboard_body = {
            "widgets": []
        }
        
        row = 0
        for server_name in server_resources.keys():
            # CPU utilization widget
            dashboard_body["widgets"].append({
                "type": "metric",
                "x": 0,
                "y": row,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", f"{self.project_name}-{server_name}-asg"]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": self.region,
                    "title": f"{server_name} CPU Utilization"
                }
            })
            
            # Memory utilization widget
            dashboard_body["widgets"].append({
                "type": "metric",
                "x": 12,
                "y": row,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["ActiveLog", server_name, "mem_used_percent"]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": self.region,
                    "title": f"{server_name} Memory Usage"
                }
            })
            
            row += 6
        
        # Create dashboard
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=f'{self.project_name}-master-dashboard',
                DashboardBody=json.dumps(dashboard_body)
            )
            logger.info("✅ Created CloudWatch dashboard")
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
        
        # Create alarms for critical metrics
        for server_name, resources in server_resources.items():
            # High CPU alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=f'{self.project_name}-{server_name}-high-cpu',
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=2,
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Period=300,
                Statistic='Average',
                Threshold=80.0,
                ActionsEnabled=True,
                AlarmActions=[],  # Add SNS topic ARN here for notifications
                AlarmDescription=f'High CPU utilization on {server_name}',
                Dimensions=[
                    {
                        'Name': 'AutoScalingGroupName',
                        'Value': resources['auto_scaling_group']
                    }
                ],
                Unit='Percent'
            )

    def configure_autoscaling(self, server_resources: Dict):
        """Configure auto-scaling policies and schedules"""
        logger.info("Configuring auto-scaling policies...")
        
        for server_name, resources in server_resources.items():
            asg_name = resources['auto_scaling_group']
            config = resources['config']
            
            # Skip if it's a single-instance service
            if config.max_size <= config.min_size:
                continue
                
            # Scale up policy
            scale_up_policy = self.autoscaling.put_scaling_policy(
                AutoScalingGroupName=asg_name,
                PolicyName=f'{server_name}-scale-up',
                ScalingAdjustment=1,
                AdjustmentType='ChangeInCapacity',
                Cooldown=300,
                PolicyType='SimpleScaling'
            )
            
            # Scale down policy
            scale_down_policy = self.autoscaling.put_scaling_policy(
                AutoScalingGroupName=asg_name,
                PolicyName=f'{server_name}-scale-down',
                ScalingAdjustment=-1,
                AdjustmentType='ChangeInCapacity',
                Cooldown=300,
                PolicyType='SimpleScaling'
            )
            
            # Create CloudWatch alarms to trigger scaling
            scale_up_arn = scale_up_policy['PolicyARN']
            scale_down_arn = scale_down_policy['PolicyARN']
            
            # High CPU alarm for scale up
            self.cloudwatch.put_metric_alarm(
                AlarmName=f'{server_name}-cpu-high',
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=2,
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Period=300,
                Statistic='Average',
                Threshold=70.0,
                ActionsEnabled=True,
                AlarmActions=[scale_up_arn],
                AlarmDescription=f'Scale up {server_name} on high CPU',
                Dimensions=[{
                    'Name': 'AutoScalingGroupName',
                    'Value': asg_name
                }]
            )
            
            # Low CPU alarm for scale down
            self.cloudwatch.put_metric_alarm(
                AlarmName=f'{server_name}-cpu-low',
                ComparisonOperator='LessThanThreshold',
                EvaluationPeriods=2,
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Period=300,
                Statistic='Average',
                Threshold=20.0,
                ActionsEnabled=True,
                AlarmActions=[scale_down_arn],
                AlarmDescription=f'Scale down {server_name} on low CPU',
                Dimensions=[{
                    'Name': 'AutoScalingGroupName',
                    'Value': asg_name
                }]
            )
            
            logger.info(f"✅ Configured auto-scaling for {server_name}")

    def generate_deployment_summary(self, vpc_id: str, subnet_info: Dict, 
                                  security_groups: Dict, server_resources: Dict,
                                  load_balancers: Dict, s3_buckets: Dict):
        """Generate a comprehensive deployment summary"""
        logger.info("Generating deployment summary...")
        
        summary = {
            'deployment_timestamp': datetime.now().isoformat(),
            'project': self.project_name,
            'environment': self.environment,
            'region': self.region,
            'infrastructure': {
                'vpc_id': vpc_id,
                'subnets': {
                    'public': subnet_info['public'],
                    'private': subnet_info['private'],
                    'nat_gateways': subnet_info['nat_gateways']
                },
                'security_groups': security_groups,
                'load_balancer': {
                    'dns_name': load_balancers['alb_dns_name'],
                    'arn': load_balancers['alb_arn']
                },
                's3_buckets': s3_buckets
            },
            'master_servers': {},
            'domains': self.domains,
            'estimated_monthly_cost': self.calculate_estimated_cost()
        }
        
        for server_name, resources in server_resources.items():
            summary['master_servers'][server_name] = {
                'instance_type': resources['config'].instance_type,
                'auto_scaling_group': resources['auto_scaling_group'],
                'min_size': resources['config'].min_size,
                'max_size': resources['config'].max_size,
                'desired_capacity': resources['config'].desired_capacity,
                'port': resources['config'].port,
                'description': resources['config'].description
            }
        
        # Write summary to file
        with open(f'activelog-deployment-summary-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print("\n" + "="*80)
        print("🚀 ACTIVELOG.AI MASTER INFRASTRUCTURE DEPLOYMENT COMPLETE!")
        print("="*80)
        print(f"Project: {self.project_name}")
        print(f"Environment: {self.environment}")
        print(f"Region: {self.region}")
        print(f"VPC ID: {vpc_id}")
        print(f"Load Balancer: {load_balancers['alb_dns_name']}")
        print(f"Estimated Monthly Cost: ${summary['estimated_monthly_cost']:,.2f}")
        
        print("\n📊 Master Servers Deployed:")
        for server_name, info in summary['master_servers'].items():
            print(f"  • {server_name}: {info['instance_type']} ({info['min_size']}-{info['max_size']} instances)")
        
        print("\n🌍 Configured Domains:")
        for domain in self.domains:
            print(f"  • {domain}")
        
        print("\n📚 Next Steps:")
        print("  1. Update DNS nameservers to point to Route 53 hosted zones")
        print("  2. Request SSL certificates via AWS Certificate Manager")
        print("  3. Update ALB listeners to use HTTPS")
        print("  4. Deploy application code to master servers")
        print("  5. Configure monitoring alerts and notifications")
        
        print("="*80)

    def calculate_estimated_cost(self) -> float:
        """Calculate estimated monthly cost"""
        
        # Instance costs per hour (us-east-1 pricing)
        instance_costs = {
            't3.small': 0.0208,
            't3.medium': 0.0416,
            't3.large': 0.0832,
            'c5.2xlarge': 0.34,
            'g4dn.xlarge': 0.526
        }
        
        total_monthly_cost = 0.0
        hours_per_month = 24 * 30
        
        # Calculate instance costs
        for server_name, config in self.master_servers.items():
            instance_cost = instance_costs.get(config.instance_type, 0.10)  # Default fallback
            monthly_instance_cost = instance_cost * config.desired_capacity * hours_per_month
            total_monthly_cost += monthly_instance_cost
        
        # Add additional AWS service costs (estimated)
        total_monthly_cost += 50   # ALB
        total_monthly_cost += 20   # NAT Gateways
        total_monthly_cost += 10   # CloudWatch
        total_monthly_cost += 5    # Route 53
        total_monthly_cost += 15   # CloudFront
        total_monthly_cost += 25   # S3 storage and requests
        
        return total_monthly_cost


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy ActiveLog.AI Master Infrastructure')
    parser.add_argument('--region', default='us-east-1', help='AWS region for deployment')
    parser.add_argument('--environment', default='master', help='Environment name')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without creating resources')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🏃 Performing dry run - no resources will be created")
        return
    
    logger.info(f"🚀 Starting ActiveLog.AI Master Infrastructure deployment in {args.region}")
    
    deployer = MasterInfrastructureDeployer(region=args.region, environment=args.environment)
    
    try:
        deployer.deploy_infrastructure()
        logger.info("✅ Deployment completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"❌ Deployment failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())