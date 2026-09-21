#!/bin/bash
# DMLog LLM Cloud Deployment Script
# Deploy auto-scaling LLM cluster for cost-optimized AI gaming

set -e

echo "🎲 Deploying DMLog Cloud LLM Infrastructure..."

# Configuration
AWS_REGION="us-west-2"
KEY_NAME="dmlog-llm-key"
SECURITY_GROUP="dmlog-llm-sg"

# Create security group for LLM instances
echo "Creating security group..."
aws ec2 create-security-group \
    --group-name $SECURITY_GROUP \
    --description "DMLog LLM API access" \
    --region $AWS_REGION

# Allow HTTP access on port 8080
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP \
    --protocol tcp \
    --port 8080 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION

# Allow SSH access
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION

# Create launch template for LLM instances
echo "Creating launch template..."
aws ec2 create-launch-template \
    --launch-template-name dmlog-llm-template \
    --version-description "DMLog LLM Server Template" \
    --launch-template-data '{
        "ImageId": "ami-0c02fb55956c7d316",
        "InstanceType": "g4dn.xlarge", 
        "KeyName": "'$KEY_NAME'",
        "SecurityGroupIds": ["'$SECURITY_GROUP'"],
        "UserData": "'$(base64 -w 0 << 'EOF'
#!/bin/bash
yum update -y
yum install -y docker git python3-pip

# Install NVIDIA Docker
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Run LLM server container
docker run -d --gpus all \
    -p 8080:8080 \
    -e MODEL_NAME=mistral-7b-instruct \
    -e MAX_TOKENS=512 \
    --name llm-server \
    --restart unless-stopped \
    dmlog/llm-server:latest

# Setup auto-shutdown after 10min idle
cat > /opt/auto-shutdown.py << 'SHUTDOWN_SCRIPT'
#!/usr/bin/env python3
import time
import subprocess
import requests
import os

def check_activity():
    try:
        response = requests.get('http://localhost:8080/metrics', timeout=5)
        if response.status_code == 200:
            metrics = response.json()
            return metrics.get('requests_last_10min', 0) > 0
    except:
        pass
    return False

def shutdown_instance():
    instance_id = subprocess.check_output(['curl', '-s', 'http://169.254.169.254/latest/meta-data/instance-id']).decode().strip()
    subprocess.run(['aws', 'ec2', 'terminate-instances', '--instance-ids', instance_id, '--region', 'us-west-2'])

# Check every 5 minutes
idle_periods = 0
while True:
    time.sleep(300)  # 5 minutes
    if not check_activity():
        idle_periods += 1
        if idle_periods >= 2:  # 10 minutes idle
            print("Instance idle for 10+ minutes. Shutting down...")
            shutdown_instance()
            break
    else:
        idle_periods = 0
SHUTDOWN_SCRIPT

chmod +x /opt/auto-shutdown.py
nohup python3 /opt/auto-shutdown.py > /var/log/auto-shutdown.log 2>&1 &

# Health check endpoint
mkdir -p /var/www/html
echo '{"status": "healthy", "model": "mistral-7b-instruct"}' > /var/www/html/health
EOF
        )'"
    }' \
    --region $AWS_REGION

# Create Auto Scaling Group
echo "Creating auto scaling group..."
aws autoscaling create-auto-scaling-group \
    --auto-scaling-group-name dmlog-llm-asg \
    --launch-template '{
        "LaunchTemplateName": "dmlog-llm-template",
        "Version": "$Latest"
    }' \
    --min-size 0 \
    --max-size 5 \
    --desired-capacity 1 \
    --availability-zones us-west-2a us-west-2b us-west-2c \
    --health-check-type EC2 \
    --health-check-grace-period 300 \
    --tags 'Key=Project,Value=DMLog,PropagateAtLaunch=true' 'Key=Environment,Value=Production,PropagateAtLaunch=true' \
    --region $AWS_REGION

# Create scaling policies
echo "Setting up auto-scaling policies..."
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name dmlog-llm-asg \
    --policy-name dmlog-scale-up \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration '{
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ASGAverageCPUUtilization"
        },
        "TargetValue": 70.0
    }' \
    --region $AWS_REGION

# Create Application Load Balancer
echo "Creating load balancer..."
aws elbv2 create-load-balancer \
    --name dmlog-llm-alb \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --subnets subnet-12345678 subnet-87654321 \
    --security-groups $SECURITY_GROUP \
    --region $AWS_REGION

echo "✅ DMLog Cloud LLM Infrastructure deployed!"
echo ""
echo "📊 Cost Estimates:"
echo "   • Development: $1-2/hour (1 instance)" 
echo "   • Production: $5-20/hour (auto-scaling)"
echo "   • Idle periods: $0/hour (auto-shutdown)"
echo ""
echo "🔗 Next steps:"
echo "   1. Set OPENAI_API_KEY for fallback"
echo "   2. Configure DNS for load balancer"
echo "   3. Monitor costs with CloudWatch"
echo ""
echo "🎮 DMLog is ready for voice-interactive gaming!"