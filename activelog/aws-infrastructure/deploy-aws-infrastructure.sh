#!/bin/bash
# ActiveLog AWS Infrastructure Deployment Script
# Complete automation for AWS environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
AWS_REGION=${2:-us-east-1}
DOMAIN_NAME=${3:-activelog.ai}

echo -e "${BLUE}🚀 ActiveLog AWS Infrastructure Deployment${NC}"
echo -e "${BLUE}===========================================${NC}"
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "Domain: $DOMAIN_NAME"
echo ""

# Functions
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"
    
    local missing_tools=()
    
    # Check required tools
    command -v aws >/dev/null 2>&1 || missing_tools+=("aws-cli")
    command -v terraform >/dev/null 2>&1 || missing_tools+=("terraform")
    command -v packer >/dev/null 2>&1 || missing_tools+=("packer")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required tools: ${missing_tools[*]}${NC}"
        echo "Please install missing tools and try again."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}❌ AWS credentials not configured${NC}"
        echo "Please run 'aws configure' first."
        exit 1
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

setup_terraform_backend() {
    echo -e "${YELLOW}🗄️  Setting up Terraform backend...${NC}"
    
    # Create unique S3 bucket for Terraform state
    BUCKET_NAME="activelog-terraform-state-$(date +%s)"
    
    aws s3api create-bucket \
        --bucket $BUCKET_NAME \
        --region $AWS_REGION \
        --create-bucket-configuration LocationConstraint=$AWS_REGION 2>/dev/null || \
    aws s3api create-bucket \
        --bucket $BUCKET_NAME \
        --region us-east-1  # us-east-1 doesn't need LocationConstraint
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket $BUCKET_NAME \
        --versioning-configuration Status=Enabled
    
    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket $BUCKET_NAME \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    
    # Create DynamoDB table for state locking
    aws dynamodb create-table \
        --table-name terraform-state-lock-$ENVIRONMENT \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region $AWS_REGION 2>/dev/null || true  # Ignore if exists
    
    # Update backend configuration
    cat > terraform/backend.tf <<EOF
terraform {
  backend "s3" {
    bucket         = "$BUCKET_NAME"
    key            = "infrastructure/terraform.tfstate"
    region         = "$AWS_REGION"
    dynamodb_table = "terraform-state-lock-$ENVIRONMENT"
    encrypt        = true
  }
}
EOF
    
    echo -e "${GREEN}✅ Terraform backend configured${NC}"
    echo "   S3 Bucket: $BUCKET_NAME"
    echo "   DynamoDB Table: terraform-state-lock-$ENVIRONMENT"
}

generate_ssh_key() {
    echo -e "${YELLOW}🔑 Setting up SSH key pair...${NC}"
    
    KEY_NAME="activelog-$ENVIRONMENT-$(date +%s)"
    
    # Generate SSH key pair
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/$KEY_NAME -N "" -q
    
    # Import public key to AWS
    aws ec2 import-key-pair \
        --key-name $KEY_NAME \
        --public-key-material fileb://~/.ssh/$KEY_NAME.pub \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ SSH key pair created: $KEY_NAME${NC}"
    echo "   Private key: ~/.ssh/$KEY_NAME"
    echo "   Public key: ~/.ssh/$KEY_NAME.pub"
    
    # Export for Terraform
    export TF_VAR_key_pair_name=$KEY_NAME
}

request_ssl_certificates() {
    echo -e "${YELLOW}🔒 Requesting SSL certificates...${NC}"
    
    # Request certificate for main domain
    CERT_ARN=$(aws acm request-certificate \
        --domain-name $DOMAIN_NAME \
        --subject-alternative-names "*.$DOMAIN_NAME" "www.$DOMAIN_NAME" \
        --validation-method DNS \
        --region $AWS_REGION \
        --query 'CertificateArn' \
        --output text)
    
    echo -e "${GREEN}✅ SSL certificate requested: $CERT_ARN${NC}"
    echo -e "${YELLOW}⚠️  Please validate the certificate via DNS before proceeding${NC}"
    
    # Export for Terraform
    export TF_VAR_ssl_certificate_arn=$CERT_ARN
}

build_ami() {
    echo -e "${YELLOW}🏗️  Building ActiveLog AMI...${NC}"
    
    cd packer
    
    # Build AMI using Packer
    if packer build \
        -var "environment=$ENVIRONMENT" \
        -var "aws_region=$AWS_REGION" \
        activelog-base.pkr.hcl; then
        
        # Get the latest AMI ID
        AMI_ID=$(aws ec2 describe-images \
            --owners self \
            --filters "Name=name,Values=activelog-base-$ENVIRONMENT-*" \
            --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
            --output text \
            --region $AWS_REGION)
        
        echo -e "${GREEN}✅ AMI built successfully: $AMI_ID${NC}"
        
        # Export for Terraform
        export TF_VAR_activelog_ami_id=$AMI_ID
        
        cd ..
    else
        echo -e "${RED}❌ AMI build failed${NC}"
        exit 1
    fi
}

generate_passwords() {
    echo -e "${YELLOW}🔐 Generating secure passwords...${NC}"
    
    # Generate random passwords
    DB_PASSWORD=$(openssl rand -base64 32)
    REDIS_PASSWORD=$(openssl rand -base64 32)
    
    # Export for Terraform
    export TF_VAR_db_password=$DB_PASSWORD
    export TF_VAR_redis_auth_token=$REDIS_PASSWORD
    
    # Save to secure file for later reference
    cat > ~/.activelog-secrets-$ENVIRONMENT <<EOF
# ActiveLog $ENVIRONMENT Environment Secrets
# Generated on $(date)
export TF_VAR_db_password='$DB_PASSWORD'
export TF_VAR_redis_auth_token='$REDIS_PASSWORD'
export TF_VAR_key_pair_name='$KEY_NAME'
export TF_VAR_ssl_certificate_arn='$CERT_ARN'
export TF_VAR_activelog_ami_id='$AMI_ID'
EOF
    
    chmod 600 ~/.activelog-secrets-$ENVIRONMENT
    
    echo -e "${GREEN}✅ Passwords generated and saved to ~/.activelog-secrets-$ENVIRONMENT${NC}"
}

deploy_infrastructure() {
    echo -e "${YELLOW}🏗️  Deploying infrastructure with Terraform...${NC}"
    
    cd terraform
    
    # Initialize Terraform
    terraform init
    
    # Create terraform.tfvars
    cat > terraform.tfvars <<EOF
# ActiveLog $ENVIRONMENT Infrastructure Configuration
environment = "$ENVIRONMENT"
aws_region = "$AWS_REGION"

# Domain configuration
domain_names = ["$DOMAIN_NAME"]
manage_dns = false  # Set to true if using Route 53

# Instance configuration based on environment
$(if [ "$ENVIRONMENT" == "production" ]; then
    echo 'web_instance_type = "t3.medium"'
    echo 'rds_instance_class = "db.r5.large"'
    echo 'redis_node_type = "cache.r7g.large"'
    echo 'asg_min_size = 2'
    echo 'asg_max_size = 10'
    echo 'asg_desired_capacity = 3'
elif [ "$ENVIRONMENT" == "staging" ]; then
    echo 'web_instance_type = "t3.small"'
    echo 'rds_instance_class = "db.t3.medium"'
    echo 'redis_node_type = "cache.r7g.large"'
    echo 'asg_min_size = 1'
    echo 'asg_max_size = 3'
    echo 'asg_desired_capacity = 2'
else
    echo 'web_instance_type = "t3.micro"'
    echo 'rds_instance_class = "db.t3.micro"'
    echo 'redis_node_type = "cache.t3.micro"'
    echo 'asg_min_size = 1'
    echo 'asg_max_size = 2'
    echo 'asg_desired_capacity = 1'
fi)

# Security configuration
enable_waf = $([ "$ENVIRONMENT" == "production" ] && echo "true" || echo "false")
allowed_cidr_blocks = ["0.0.0.0/0"]  # Restrict in production

# Features
features = {
  enable_cloudfront     = true
  enable_elasticache    = true
  enable_rds_encryption = true
  enable_s3_versioning  = true
  enable_vpc_flow_logs  = true
}
EOF
    
    # Plan deployment
    echo -e "${BLUE}📋 Planning infrastructure deployment...${NC}"
    terraform plan -out=tfplan
    
    # Apply deployment
    echo -e "${BLUE}🚀 Applying infrastructure deployment...${NC}"
    terraform apply tfplan
    
    # Get outputs
    LOAD_BALANCER_DNS=$(terraform output -raw alb_dns_name)
    S3_BUCKET=$(terraform output -raw s3_bucket_name)
    
    echo -e "${GREEN}✅ Infrastructure deployed successfully!${NC}"
    echo "   Load Balancer: $LOAD_BALANCER_DNS"
    echo "   S3 Bucket: $S3_BUCKET"
    
    cd ..
}

setup_monitoring() {
    echo -e "${YELLOW}📊 Setting up monitoring and alerting...${NC}"
    
    # Create CloudWatch dashboard
    aws cloudwatch put-dashboard \
        --dashboard-name "ActiveLog-$ENVIRONMENT" \
        --dashboard-body "$(cat monitoring/cloudwatch-dashboard.json | sed "s/ENVIRONMENT/$ENVIRONMENT/g")" \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ Monitoring configured${NC}"
}

run_health_checks() {
    echo -e "${YELLOW}🏥 Running health checks...${NC}"
    
    # Wait for load balancer to be ready
    echo "Waiting for load balancer to be ready..."
    sleep 60
    
    # Check load balancer health
    if curl -s -o /dev/null -w "%{http_code}" "http://$LOAD_BALANCER_DNS/health" | grep -q "200"; then
        echo -e "${GREEN}✅ Application health check passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Application health check failed - may need more time to start${NC}"
    fi
}

print_summary() {
    echo ""
    echo -e "${PURPLE}🎉 ActiveLog AWS Infrastructure Deployment Complete!${NC}"
    echo -e "${PURPLE}====================================================${NC}"
    echo ""
    echo -e "${BLUE}📋 Deployment Summary:${NC}"
    echo "   Environment: $ENVIRONMENT"
    echo "   Region: $AWS_REGION"
    echo "   Domain: $DOMAIN_NAME"
    echo ""
    echo -e "${BLUE}🔗 Important URLs:${NC}"
    echo "   Application: http://$LOAD_BALANCER_DNS"
    echo "   SSL Certificate: $CERT_ARN"
    echo ""
    echo -e "${BLUE}🔑 Security Information:${NC}"
    echo "   SSH Key: $KEY_NAME"
    echo "   Secrets File: ~/.activelog-secrets-$ENVIRONMENT"
    echo ""
    echo -e "${BLUE}💾 Infrastructure State:${NC}"
    echo "   S3 Bucket: $BUCKET_NAME"
    echo "   DynamoDB Table: terraform-state-lock-$ENVIRONMENT"
    echo ""
    echo -e "${BLUE}🎯 Next Steps:${NC}"
    echo "1. Validate SSL certificate via DNS"
    echo "2. Update DNS records to point to: $LOAD_BALANCER_DNS"
    echo "3. Configure application-specific settings"
    echo "4. Set up CI/CD pipelines"
    echo "5. Configure monitoring and alerting"
    echo ""
    echo -e "${YELLOW}⚠️  Important Security Notes:${NC}"
    echo "• Secure your secrets file: ~/.activelog-secrets-$ENVIRONMENT"
    echo "• Restrict security group access in production"
    echo "• Enable AWS CloudTrail for audit logging"
    echo "• Review IAM permissions regularly"
    echo ""
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting ActiveLog AWS Infrastructure Deployment...${NC}"
    
    check_prerequisites
    setup_terraform_backend
    generate_ssh_key
    request_ssl_certificates
    build_ami
    generate_passwords
    deploy_infrastructure
    setup_monitoring
    run_health_checks
    print_summary
}

# Handle script interruption
trap 'echo -e "${RED}❌ Deployment interrupted${NC}"; exit 1' INT TERM

# Run main function
main "$@"