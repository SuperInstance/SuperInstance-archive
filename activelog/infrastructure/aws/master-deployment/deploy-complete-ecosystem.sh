#!/bin/bash

# ActiveLog.AI Complete Ecosystem Deployment Script
# Deploys master infrastructure + all domain-specific servers
# With security, monitoring, and cost optimization

set -e

# Configuration
PROJECT_NAME="activelog-ai"
AWS_REGION=${AWS_REGION:-"us-east-1"}
ENVIRONMENT=${ENVIRONMENT:-"master"}
MIN_RESOURCES=${MIN_RESOURCES:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging setup
LOG_FILE="deployment-$(date +%Y%m%d-%H%M%S).log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Domain list for multi-domain deployment
DOMAINS=(
    "PersonalLog"
    "MakerLog" 
    "LucidDreamer"
    "BusinessLog"
    "Capitaine"
    "DeckBoss"
    "DMLog"
    "FishingLog"
    "RealLog"
    "PlayerLog"
    "StudyLog"
)

# Master infrastructure domains
MASTER_DOMAINS=(
    "activelog.ai"
    "activeledger.ai"
    "activelogai.com"
    "makerslog.ai"
)

check_prerequisites() {
    echo_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo_error "AWS CLI not found. Please install AWS CLI first."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        echo_error "Terraform not found. Please install Terraform first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check jq for JSON processing
    if ! command -v jq &> /dev/null; then
        echo_warning "jq not found. Installing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install jq || echo_error "Failed to install jq"
        else
            sudo apt-get update && sudo apt-get install -y jq || echo_error "Failed to install jq"
        fi
    fi
    
    echo_success "Prerequisites check completed"
}

create_terraform_backend() {
    echo_info "Setting up Terraform backend..."
    
    BUCKET_NAME="${PROJECT_NAME}-terraform-state-${ENVIRONMENT}"
    TABLE_NAME="${PROJECT_NAME}-terraform-locks-${ENVIRONMENT}"
    
    # Create S3 bucket for Terraform state
    if ! aws s3 ls "s3://$BUCKET_NAME" 2>/dev/null; then
        echo_info "Creating S3 bucket for Terraform state: $BUCKET_NAME"
        if [[ "$AWS_REGION" == "us-east-1" ]]; then
            aws s3 mb "s3://$BUCKET_NAME"
        else
            aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION"
        fi
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "$BUCKET_NAME" \
            --versioning-configuration Status=Enabled
        
        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "$BUCKET_NAME" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
    fi
    
    # Create DynamoDB table for Terraform locks
    if ! aws dynamodb describe-table --table-name "$TABLE_NAME" 2>/dev/null; then
        echo_info "Creating DynamoDB table for Terraform locks: $TABLE_NAME"
        aws dynamodb create-table \
            --table-name "$TABLE_NAME" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
            --region "$AWS_REGION"
        
        # Wait for table to be active
        echo_info "Waiting for DynamoDB table to be active..."
        aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$AWS_REGION"
    fi
    
    echo_success "Terraform backend configured"
}

deploy_master_infrastructure() {
    echo_info "Deploying master infrastructure..."
    
    cd terraform
    
    # Configure backend
    cat > backend.tf << EOF
terraform {
  backend "s3" {
    bucket         = "${PROJECT_NAME}-terraform-state-${ENVIRONMENT}"
    key            = "master-infrastructure/terraform.tfstate"
    region         = "${AWS_REGION}"
    encrypt        = true
    dynamodb_table = "${PROJECT_NAME}-terraform-locks-${ENVIRONMENT}"
  }
}
EOF
    
    # Initialize Terraform
    echo_info "Initializing Terraform..."
    terraform init
    
    # Create terraform.tfvars
    cat > terraform.tfvars << EOF
aws_region      = "${AWS_REGION}"
environment     = "${ENVIRONMENT}"
project_name    = "${PROJECT_NAME}"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
availability_zones = [
    "${AWS_REGION}a",
    "${AWS_REGION}b", 
    "${AWS_REGION}c"
]

# Master domains
domains = [
$(printf '    "%s",\n' "${MASTER_DOMAINS[@]}" | sed '$s/,$//')
]

# Database configuration
rds_instance_class = "db.t3.medium"
rds_multi_az = true
redis_node_type = "cache.t3.medium"
documentdb_instance_class = "db.t3.medium"

# Security
enable_waf = true
enable_cloudtrail = true
allowed_cidr_blocks = ["0.0.0.0/0"]

# Cost optimization
enable_detailed_monitoring = true
cost_alert_email = "alerts@activelog.ai"
monthly_budget = 2000
EOF
    
    # Validate configuration
    echo_info "Validating Terraform configuration..."
    terraform validate
    
    # Plan deployment
    echo_info "Creating Terraform plan..."
    terraform plan -out=tfplan -var-file=terraform.tfvars
    
    # Apply deployment
    echo_info "Applying Terraform plan..."
    terraform apply -auto-approve tfplan
    
    # Save outputs
    terraform output -json > ../master-infrastructure-outputs.json
    
    cd ..
    
    echo_success "Master infrastructure deployed successfully"
}

create_key_pair() {
    echo_info "Creating EC2 key pair..."
    
    KEY_NAME="${PROJECT_NAME}-keypair"
    
    if ! aws ec2 describe-key-pairs --key-names "$KEY_NAME" 2>/dev/null; then
        aws ec2 create-key-pair \
            --key-name "$KEY_NAME" \
            --query 'KeyMaterial' \
            --output text > "${KEY_NAME}.pem"
        
        chmod 600 "${KEY_NAME}.pem"
        echo_success "Key pair created: ${KEY_NAME}.pem"
    else
        echo_info "Key pair already exists: $KEY_NAME"
    fi
}

deploy_domain_servers() {
    echo_info "Deploying domain-specific servers..."
    
    # Get VPC and subnet information from master infrastructure
    if [[ ! -f "master-infrastructure-outputs.json" ]]; then
        echo_error "Master infrastructure outputs not found. Deploy master infrastructure first."
        return 1
    fi
    
    VPC_ID=$(jq -r '.vpc_id.value' master-infrastructure-outputs.json)
    PRIVATE_SUBNETS=$(jq -r '.private_subnet_ids.value[]' master-infrastructure-outputs.json | tr '\n' ',' | sed 's/,$//')
    PUBLIC_SUBNETS=$(jq -r '.public_subnet_ids.value[]' master-infrastructure-outputs.json | tr '\n' ',' | sed 's/,$//')
    
    for DOMAIN in "${DOMAINS[@]}"; do
        echo_info "Deploying $DOMAIN infrastructure..."
        
        # Create security group for domain
        SG_NAME="${PROJECT_NAME}-${DOMAIN,,}-sg"
        
        if ! aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" 2>/dev/null | jq -e '.SecurityGroups[0]' > /dev/null; then
            echo_info "Creating security group for $DOMAIN..."
            
            SG_ID=$(aws ec2 create-security-group \
                --group-name "$SG_NAME" \
                --description "Security group for $DOMAIN domain" \
                --vpc-id "$VPC_ID" \
                --query 'GroupId' \
                --output text)
            
            # Add ingress rules
            aws ec2 authorize-security-group-ingress \
                --group-id "$SG_ID" \
                --protocol tcp \
                --port 80 \
                --cidr 0.0.0.0/0
            
            aws ec2 authorize-security-group-ingress \
                --group-id "$SG_ID" \
                --protocol tcp \
                --port 443 \
                --cidr 0.0.0.0/0
            
            aws ec2 authorize-security-group-ingress \
                --group-id "$SG_ID" \
                --protocol tcp \
                --port 22 \
                --cidr 10.0.0.0/16
            
            # Application ports (8000-8010)
            for port in {8000..8010}; do
                aws ec2 authorize-security-group-ingress \
                    --group-id "$SG_ID" \
                    --protocol tcp \
                    --port "$port" \
                    --source-group "$SG_ID"
            done
            
        else
            SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" --query 'SecurityGroups[0].GroupId' --output text)
        fi
        
        # Deploy domain servers
        deploy_domain_server_stack "$DOMAIN" "$SG_ID" "$PRIVATE_SUBNETS"
        
        # Create subdomain DNS record
        create_domain_dns_record "$DOMAIN"
    done
    
    echo_success "All domain servers deployed"
}

deploy_domain_server_stack() {
    local DOMAIN=$1
    local SG_ID=$2
    local SUBNETS=$3
    
    echo_info "Deploying server stack for $DOMAIN..."
    
    # Domain-specific configurations
    declare -A DOMAIN_CONFIGS
    DOMAIN_CONFIGS=(
        ["PersonalLog"]="backend:t3.small,repository:t3.small,deployer:t3.micro,trainer:t3.medium,builder:t3.small,runner:c5.large"
        ["MakerLog"]="backend:t3.medium,repository:t3.medium,deployer:t3.small,trainer:t3.large,builder:t3.medium,runner:c5.xlarge"
        ["LucidDreamer"]="backend:t3.small,repository:t3.small,deployer:t3.micro,trainer:g4dn.xlarge,builder:t3.small,runner:c5.large"
        ["BusinessLog"]="backend:t3.large,repository:t3.large,deployer:t3.medium,trainer:t3.xlarge,builder:t3.large,runner:c5.2xlarge"
        ["DMLog"]="backend:t3.medium,repository:t3.medium,deployer:t3.small,trainer:g4dn.2xlarge,builder:t3.medium,runner:c5.xlarge"
        ["FishingLog"]="backend:t3.small,repository:t3.small,deployer:t3.micro,trainer:t3.medium,builder:t3.small,runner:c5.large"
    )
    
    # Use default config if not specified
    CONFIG=${DOMAIN_CONFIGS[$DOMAIN]:-"backend:t3.small,repository:t3.small,deployer:t3.micro,trainer:t3.medium,builder:t3.small,runner:c5.large"}
    
    # Parse configuration
    IFS=',' read -ra SERVICES <<< "$CONFIG"
    
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -ra PARTS <<< "$service_config"
        SERVICE=${PARTS[0]}
        INSTANCE_TYPE=${PARTS[1]}
        
        # Skip GPU instances if minimal resources requested
        if [[ "$MIN_RESOURCES" == "true" && "$INSTANCE_TYPE" =~ ^g4 ]]; then
            echo_warning "Skipping GPU instance $INSTANCE_TYPE for $SERVICE in minimal mode"
            continue
        fi
        
        echo_info "Deploying ${DOMAIN}${SERVICE} on ${INSTANCE_TYPE}..."
        
        # Create user data script
        create_domain_user_data_script "$DOMAIN" "$SERVICE" > "userdata-${DOMAIN}-${SERVICE}.sh"
        
        # Launch instance
        INSTANCE_ID=$(aws ec2 run-instances \
            --image-id "$(get_latest_ubuntu_ami)" \
            --instance-type "$INSTANCE_TYPE" \
            --key-name "${PROJECT_NAME}-keypair" \
            --security-group-ids "$SG_ID" \
            --subnet-id "$(echo $SUBNETS | cut -d',' -f1)" \
            --user-data file://userdata-${DOMAIN}-${SERVICE}.sh \
            --iam-instance-profile Name="${PROJECT_NAME}-master-instance-profile" \
            --tag-specifications "ResourceType=instance,Tags=[
                {Key=Name,Value=${PROJECT_NAME}-${DOMAIN}-${SERVICE}},
                {Key=Domain,Value=${DOMAIN}},
                {Key=Service,Value=${SERVICE}},
                {Key=Project,Value=${PROJECT_NAME}},
                {Key=Environment,Value=${ENVIRONMENT}}
            ]" \
            --query 'Instances[0].InstanceId' \
            --output text)
        
        echo_success "Deployed ${DOMAIN}${SERVICE}: $INSTANCE_ID"
        
        # Create auto-scaling group for the service
        create_autoscaling_group "$DOMAIN" "$SERVICE" "$INSTANCE_TYPE" "$SG_ID" "$SUBNETS"
        
        # Clean up user data file
        rm -f "userdata-${DOMAIN}-${SERVICE}.sh"
    done
}

create_domain_user_data_script() {
    local DOMAIN=$1
    local SERVICE=$2
    
    cat << EOF
#!/bin/bash
set -e

# Update system
apt-get update -y
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i amazon-cloudwatch-agent.deb

# Create application directory
mkdir -p /opt/${DOMAIN,,}
cd /opt/${DOMAIN,,}

# Create service configuration
cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  ${SERVICE,,}:
    image: activelog/${DOMAIN,,}-${SERVICE,,}:latest
    ports:
      - "8000:8000"
    environment:
      - DOMAIN=${DOMAIN}
      - SERVICE=${SERVICE}
      - AWS_REGION=${AWS_REGION}
      - ENVIRONMENT=${ENVIRONMENT}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - ${SERVICE,,}
    restart: unless-stopped
COMPOSE_EOF

# Create nginx configuration
cat > nginx.conf << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    upstream app {
        server ${SERVICE,,}:8000;
    }

    server {
        listen 80;
        server_name _;

        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://app;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
NGINX_EOF

# Create data and logs directories
mkdir -p data logs ssl

# Start services
docker-compose up -d

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CW_EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "root"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/opt/${DOMAIN,,}/logs/*.log",
                        "log_group_name": "/aws/ec2/${DOMAIN}/${SERVICE}",
                        "log_stream_name": "{instance_id}/{hostname}",
                        "multi_line_start_pattern": "{timestamp_format}"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "ActiveLog/${DOMAIN}/${SERVICE}",
        "metrics_collected": {
            "cpu": {
                "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": ["used_percent"],
                "metrics_collection_interval": 60,
                "resources": ["*"]
            },
            "mem": {
                "measurement": ["mem_used_percent"],
                "metrics_collection_interval": 60
            }
        }
    }
}
CW_EOF

# Start CloudWatch agent
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

# Create health check script
cat > /opt/health_check.sh << 'HEALTH_EOF'
#!/bin/bash
if curl -f http://localhost/health &>/dev/null; then
    echo "Service healthy"
    exit 0
else
    echo "Service unhealthy"
    exit 1
fi
HEALTH_EOF

chmod +x /opt/health_check.sh

# Create crontab for health monitoring
echo "*/1 * * * * /opt/health_check.sh >> /var/log/health_check.log 2>&1" | crontab -

echo "$(date): ${DOMAIN}${SERVICE} initialization complete" >> /var/log/cloud-init.log
EOF
}

create_autoscaling_group() {
    local DOMAIN=$1
    local SERVICE=$2
    local INSTANCE_TYPE=$3
    local SG_ID=$4
    local SUBNETS=$5
    
    echo_info "Creating auto-scaling group for ${DOMAIN}${SERVICE}..."
    
    # Create launch template
    TEMPLATE_NAME="${PROJECT_NAME}-${DOMAIN}-${SERVICE}-template"
    
    # Generate user data and encode it
    create_domain_user_data_script "$DOMAIN" "$SERVICE" | base64 -w 0 > "userdata-encoded-${DOMAIN}-${SERVICE}.txt"
    
    aws ec2 create-launch-template \
        --launch-template-name "$TEMPLATE_NAME" \
        --launch-template-data "{
            \"ImageId\":\"$(get_latest_ubuntu_ami)\",
            \"InstanceType\":\"$INSTANCE_TYPE\",
            \"KeyName\":\"${PROJECT_NAME}-keypair\",
            \"SecurityGroupIds\":[\"$SG_ID\"],
            \"IamInstanceProfile\":{\"Name\":\"${PROJECT_NAME}-master-instance-profile\"},
            \"UserData\":\"$(cat userdata-encoded-${DOMAIN}-${SERVICE}.txt)\",
            \"TagSpecifications\":[{
                \"ResourceType\":\"instance\",
                \"Tags\":[
                    {\"Key\":\"Name\",\"Value\":\"${PROJECT_NAME}-${DOMAIN}-${SERVICE}\"},
                    {\"Key\":\"Domain\",\"Value\":\"${DOMAIN}\"},
                    {\"Key\":\"Service\",\"Value\":\"${SERVICE}\"},
                    {\"Key\":\"Project\",\"Value\":\"${PROJECT_NAME}\"}
                ]
            }]
        }" &>/dev/null
    
    # Create auto-scaling group
    ASG_NAME="${PROJECT_NAME}-${DOMAIN}-${SERVICE}-asg"
    
    aws autoscaling create-auto-scaling-group \
        --auto-scaling-group-name "$ASG_NAME" \
        --launch-template LaunchTemplateName="$TEMPLATE_NAME",Version='$Latest' \
        --min-size 1 \
        --max-size 5 \
        --desired-capacity 1 \
        --vpc-zone-identifier "$SUBNETS" \
        --health-check-type EC2 \
        --health-check-grace-period 300 \
        --tags "Key=Name,Value=${PROJECT_NAME}-${DOMAIN}-${SERVICE},PropagateAtLaunch=true,ResourceId=$ASG_NAME,ResourceType=auto-scaling-group" \
               "Key=Domain,Value=${DOMAIN},PropagateAtLaunch=true,ResourceId=$ASG_NAME,ResourceType=auto-scaling-group" \
               "Key=Service,Value=${SERVICE},PropagateAtLaunch=true,ResourceId=$ASG_NAME,ResourceType=auto-scaling-group"
    
    # Clean up temporary files
    rm -f "userdata-encoded-${DOMAIN}-${SERVICE}.txt"
    
    echo_success "Auto-scaling group created: $ASG_NAME"
}

create_domain_dns_record() {
    local DOMAIN=$1
    
    echo_info "Creating DNS record for ${DOMAIN}..."
    
    # Get hosted zone ID for main domain
    HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
        --dns-name "activelog.ai" \
        --query 'HostedZones[0].Id' \
        --output text | sed 's|/hostedzone/||')
    
    if [[ "$HOSTED_ZONE_ID" == "None" ]]; then
        echo_warning "Main hosted zone not found. Skipping DNS record creation for $DOMAIN"
        return 0
    fi
    
    # Get ALB DNS name from master infrastructure
    ALB_DNS_NAME=$(jq -r '.alb_dns_name.value' master-infrastructure-outputs.json)
    ALB_ZONE_ID=$(jq -r '.alb_zone_id.value' master-infrastructure-outputs.json)
    
    # Create subdomain DNS record
    SUBDOMAIN="${DOMAIN,,}.activelog.ai"
    
    cat > change-batch-${DOMAIN}.json << EOF
{
    "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "$SUBDOMAIN",
            "Type": "A",
            "AliasTarget": {
                "DNSName": "$ALB_DNS_NAME",
                "EvaluateTargetHealth": true,
                "HostedZoneId": "$ALB_ZONE_ID"
            }
        }
    }]
}
EOF
    
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch file://change-batch-${DOMAIN}.json
    
    rm -f change-batch-${DOMAIN}.json
    
    echo_success "DNS record created: $SUBDOMAIN"
}

get_latest_ubuntu_ami() {
    aws ec2 describe-images \
        --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
                  "Name=state,Values=available" \
        --query 'Images|sort_by(@, &CreationDate)[-1].ImageId' \
        --output text
}

setup_monitoring() {
    echo_info "Setting up monitoring and alerting..."
    
    # Create CloudWatch dashboard for all services
    create_master_dashboard
    
    # Setup cost monitoring
    setup_cost_alerts
    
    # Setup health monitoring
    setup_health_monitoring
    
    echo_success "Monitoring setup complete"
}

create_master_dashboard() {
    echo_info "Creating master CloudWatch dashboard..."
    
    cat > dashboard-config.json << 'EOF'
{
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/EC2", "CPUUtilization" ]
                ],
                "period": 300,
                "stat": "Average",
                "region": "us-east-1",
                "title": "EC2 CPU Utilization"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApplicationELB", "RequestCount" ]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "us-east-1",
                "title": "ALB Request Count"
            }
        }
    ]
}
EOF
    
    aws cloudwatch put-dashboard \
        --dashboard-name "${PROJECT_NAME}-master-dashboard" \
        --dashboard-body file://dashboard-config.json
    
    rm -f dashboard-config.json
    
    echo_success "Master dashboard created"
}

setup_cost_alerts() {
    echo_info "Setting up cost alerts..."
    
    # Create budget for cost monitoring
    cat > budget-config.json << EOF
{
    "BudgetName": "${PROJECT_NAME}-monthly-budget",
    "BudgetLimit": {
        "Amount": "2000.0",
        "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
        "TagKey": ["Project"],
        "TagValue": ["${PROJECT_NAME}"]
    }
}
EOF
    
    aws budgets create-budget \
        --account-id "$(aws sts get-caller-identity --query Account --output text)" \
        --budget file://budget-config.json || true
    
    rm -f budget-config.json
}

setup_health_monitoring() {
    echo_info "Setting up health monitoring..."
    
    # Create SNS topic for alerts
    TOPIC_ARN=$(aws sns create-topic \
        --name "${PROJECT_NAME}-alerts" \
        --query 'TopicArn' \
        --output text)
    
    # Subscribe email to topic
    aws sns subscribe \
        --topic-arn "$TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "alerts@activelog.ai"
    
    echo_success "Health monitoring configured"
}

cleanup_on_error() {
    echo_error "Deployment failed. Cleaning up resources..."
    
    # Add cleanup logic here if needed
    # For now, we'll just log the error
    echo_error "Please check the logs and clean up manually if needed"
}

generate_deployment_summary() {
    echo_info "Generating deployment summary..."
    
    cat > deployment-summary.json << EOF
{
    "deployment_timestamp": "$(date -Iseconds)",
    "project": "${PROJECT_NAME}",
    "environment": "${ENVIRONMENT}", 
    "region": "${AWS_REGION}",
    "master_domains": $(printf '%s\n' "${MASTER_DOMAINS[@]}" | jq -R . | jq -s .),
    "application_domains": $(printf '%s\n' "${DOMAINS[@]}" | jq -R . | jq -s .),
    "infrastructure_deployed": true,
    "domain_servers_deployed": true,
    "monitoring_configured": true,
    "estimated_monthly_cost_usd": 1500,
    "next_steps": [
        "Update DNS nameservers to point to Route 53 hosted zones",
        "Request SSL certificates via AWS Certificate Manager",
        "Deploy application code to servers",
        "Configure monitoring alerts",
        "Test all domain endpoints"
    ]
}
EOF
    
    echo_success "Deployment summary saved to deployment-summary.json"
}

main() {
    echo_info "🚀 Starting ActiveLog.AI Complete Ecosystem Deployment"
    echo_info "Project: $PROJECT_NAME"
    echo_info "Environment: $ENVIRONMENT"
    echo_info "Region: $AWS_REGION"
    echo_info "Minimal Resources: $MIN_RESOURCES"
    echo_info "Log file: $LOG_FILE"
    echo
    
    # Set error trap
    trap cleanup_on_error ERR
    
    # Main deployment flow
    check_prerequisites
    create_terraform_backend
    create_key_pair
    deploy_master_infrastructure
    deploy_domain_servers
    setup_monitoring
    generate_deployment_summary
    
    echo
    echo_success "🎉 ActiveLog.AI Complete Ecosystem Deployment SUCCESSFUL!"
    echo_info "Master Infrastructure: $(jq -r '.alb_dns_name.value' master-infrastructure-outputs.json 2>/dev/null || echo 'Check outputs file')"
    echo_info "Total Domains Deployed: $((${#MASTER_DOMAINS[@]} + ${#DOMAINS[@]}))"
    echo_info "Log File: $LOG_FILE"
    echo
    echo_info "Next Steps:"
    echo "  1. Update DNS nameservers to point to Route 53"
    echo "  2. Request SSL certificates"
    echo "  3. Deploy application code"
    echo "  4. Test all endpoints"
    echo
    echo_info "Access URLs will be available after DNS propagation:"
    for domain in "${MASTER_DOMAINS[@]}"; do
        echo "  • https://$domain"
    done
    for domain in "${DOMAINS[@]}"; do
        echo "  • https://${domain,,}.activelog.ai"
    done
}

# Script usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy ActiveLog.AI complete ecosystem on AWS

OPTIONS:
    --region REGION        AWS region (default: us-east-1)
    --environment ENV      Environment name (default: master)
    --min-resources        Deploy with minimal resources
    --dry-run             Show what would be deployed
    --help                Show this help message

EXAMPLES:
    $0                                    # Deploy with default settings
    $0 --region us-west-2                # Deploy to us-west-2
    $0 --min-resources                   # Deploy with minimal resources
    $0 --environment staging             # Deploy to staging environment

ENVIRONMENT VARIABLES:
    AWS_REGION            AWS region
    ENVIRONMENT           Environment name
    MIN_RESOURCES         Use minimal resources (true/false)
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --min-resources)
            MIN_RESOURCES=true
            shift
            ;;
        --dry-run)
            echo_info "DRY RUN MODE - No resources will be created"
            echo_info "This would deploy:"
            echo "  • Master infrastructure in $AWS_REGION"
            echo "  • ${#DOMAINS[@]} domain-specific server stacks"
            echo "  • Monitoring and alerting"
            echo "  • DNS configuration for all domains"
            exit 0
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Run main deployment
main "$@"