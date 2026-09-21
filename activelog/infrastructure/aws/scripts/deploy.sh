#!/bin/bash
# ActiveLog AWS Infrastructure - One-Click Deployment Script
# This script deploys the entire ActiveLog infrastructure to AWS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
REGION="us-west-2"
DOMAIN_NAME=""
SKIP_CONFIRMATION=false
DRY_RUN=false
DESTROY=false
AUTO_APPROVE=false

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="${SCRIPT_DIR}/../terraform"
ENVIRONMENTS_DIR="${SCRIPT_DIR}/../environments"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
usage() {
    cat << EOF
ActiveLog AWS Infrastructure Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -e, --environment ENVIRONMENT    Environment to deploy (staging|production)
    -r, --region REGION             AWS region (default: us-west-2)
    -d, --domain DOMAIN             Domain name for the application
    -y, --yes                       Skip confirmation prompts
    --dry-run                       Show what would be deployed without actually deploying
    --destroy                       Destroy the infrastructure instead of creating it
    --auto-approve                  Auto-approve Terraform operations
    -h, --help                      Show this help message

EXAMPLES:
    $0 -e staging -d staging.activelog.com
    $0 -e production -d activelog.com -y
    $0 --destroy -e staging
    $0 --dry-run -e production -d activelog.com

REQUIREMENTS:
    - AWS CLI configured with appropriate credentials
    - Terraform >= 1.0
    - jq (for JSON processing)
    - Valid AWS account with necessary permissions

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN_NAME="$2"
            shift 2
            ;;
        -y|--yes)
            SKIP_CONFIRMATION=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --destroy)
            DESTROY=true
            shift
            ;;
        --auto-approve)
            AUTO_APPROVE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$ENVIRONMENT" ]]; then
    print_error "Environment is required. Use -e or --environment"
    usage
    exit 1
fi

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    print_error "Environment must be 'staging' or 'production'"
    exit 1
fi

if [[ -z "$DOMAIN_NAME" && "$DESTROY" == false ]]; then
    print_error "Domain name is required for deployment. Use -d or --domain"
    usage
    exit 1
fi

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials are not configured or invalid."
        exit 1
    fi

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    # Check Terraform version
    TERRAFORM_VERSION=$(terraform version -json | jq -r '.terraform_version')
    if [[ $(echo "$TERRAFORM_VERSION 1.0.0" | tr " " "\n" | sort -V | head -n1) != "1.0.0" ]]; then
        print_error "Terraform version $TERRAFORM_VERSION is too old. Minimum required: 1.0.0"
        exit 1
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        print_error "jq is not installed. Please install it first."
        exit 1
    fi

    print_success "All prerequisites satisfied"
}

# Function to get AWS account info
get_aws_info() {
    print_status "Getting AWS account information..."
    
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    
    print_status "AWS Account ID: $AWS_ACCOUNT_ID"
    print_status "AWS User/Role: $AWS_USER_ARN"
    print_status "AWS Region: $REGION"
}

# Function to estimate costs
estimate_costs() {
    print_status "Estimating monthly costs for $ENVIRONMENT environment..."
    
    case $ENVIRONMENT in
        staging)
            cat << EOF

📊 ESTIMATED MONTHLY COSTS (STAGING):
┌─────────────────────────┬──────────┐
│ Service                 │ Cost USD │
├─────────────────────────┼──────────┤
│ ECS Fargate (70 tasks)  │  $1,200  │
│ RDS PostgreSQL (t3.med) │    $85   │
│ ElastiCache (t3.micro)  │    $25   │
│ S3 Storage (100GB)      │    $25   │
│ CloudFront CDN          │    $50   │
│ Application Load Balancer│   $25   │
│ Route53 Hosted Zone     │    $1    │
│ CloudWatch Logs         │    $15   │
│ Data Transfer           │    $50   │
│ NAT Gateways (3)        │   $135   │
├─────────────────────────┼──────────┤
│ TOTAL                   │ ~$1,611  │
└─────────────────────────┴──────────┘

💡 This is an estimate. Actual costs may vary based on usage.
EOF
            ;;
        production)
            cat << EOF

📊 ESTIMATED MONTHLY COSTS (PRODUCTION):
┌─────────────────────────┬──────────┐
│ Service                 │ Cost USD │
├─────────────────────────┼──────────┤
│ ECS Fargate (140 tasks) │  $2,400  │
│ RDS PostgreSQL (r5.xl)  │   $350   │
│ RDS Read Replica        │   $350   │
│ ElastiCache (r6g.large) │   $180   │
│ S3 Storage (1TB)        │   $120   │
│ CloudFront CDN          │   $200   │
│ Application Load Balancer│   $25   │
│ Route53 Hosted Zone     │    $1    │
│ CloudWatch Logs         │    $50   │
│ Data Transfer           │   $150   │
│ NAT Gateways (3)        │   $135   │
│ AWS Backup              │    $30   │
│ Performance Insights    │    $20   │
├─────────────────────────┼──────────┤
│ TOTAL                   │ ~$4,011  │
└─────────────────────────┴──────────┘

💡 This is an estimate. Actual costs may vary based on usage.
EOF
            ;;
    esac
}

# Function to setup Terraform backend
setup_terraform_backend() {
    print_status "Setting up Terraform backend..."
    
    BACKEND_BUCKET="activelog-terraform-state-${ENVIRONMENT}-$(echo $AWS_ACCOUNT_ID | tail -c 8)"
    DYNAMODB_TABLE="activelog-terraform-locks-${ENVIRONMENT}"
    
    # Create S3 bucket for Terraform state
    if ! aws s3 ls "s3://$BACKEND_BUCKET" 2>/dev/null; then
        print_status "Creating Terraform state bucket: $BACKEND_BUCKET"
        aws s3 mb "s3://$BACKEND_BUCKET" --region "$REGION"
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "$BACKEND_BUCKET" \
            --versioning-configuration Status=Enabled
        
        # Enable server-side encryption
        aws s3api put-bucket-encryption \
            --bucket "$BACKEND_BUCKET" \
            --server-side-encryption-configuration '{
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }'
        
        # Block public access
        aws s3api put-public-access-block \
            --bucket "$BACKEND_BUCKET" \
            --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    fi
    
    # Create DynamoDB table for state locking
    if ! aws dynamodb describe-table --table-name "$DYNAMODB_TABLE" --region "$REGION" 2>/dev/null; then
        print_status "Creating Terraform lock table: $DYNAMODB_TABLE"
        aws dynamodb create-table \
            --table-name "$DYNAMODB_TABLE" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
            --region "$REGION"
        
        # Wait for table to be active
        aws dynamodb wait table-exists --table-name "$DYNAMODB_TABLE" --region "$REGION"
    fi
    
    print_success "Terraform backend configured"
}

# Function to initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    
    cd "$TERRAFORM_DIR"
    
    # Create backend configuration
    cat > backend.hcl << EOF
bucket         = "activelog-terraform-state-${ENVIRONMENT}-$(echo $AWS_ACCOUNT_ID | tail -c 8)"
key            = "terraform.tfstate"
region         = "${REGION}"
encrypt        = true
dynamodb_table = "activelog-terraform-locks-${ENVIRONMENT}"
EOF
    
    # Initialize Terraform with backend
    terraform init -backend-config=backend.hcl -reconfigure
    
    print_success "Terraform initialized"
}

# Function to create tfvars file
create_tfvars() {
    print_status "Creating Terraform variables file..."
    
    TFVARS_FILE="$TERRAFORM_DIR/${ENVIRONMENT}.tfvars"
    
    cat > "$TFVARS_FILE" << EOF
# ActiveLog Infrastructure Configuration - ${ENVIRONMENT}
# Generated on $(date)

# General Configuration
environment = "${ENVIRONMENT}"
aws_region  = "${REGION}"
domain_name = "${DOMAIN_NAME}"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"

# Environment-specific overrides
$(case $ENVIRONMENT in
    staging)
        cat << EOF2
# Staging Configuration
rds_instance_class     = "db.t3.medium"
redis_node_type       = "cache.t3.micro"
min_capacity          = 1
max_capacity          = 5
rds_multi_az          = false
rds_deletion_protection = false
monthly_budget        = 2000

# Feature flags for staging
enable_shield_advanced = false
rds_backup_retention_period = 3
EOF2
        ;;
    production)
        cat << EOF2
# Production Configuration
rds_instance_class     = "db.r5.xlarge"
redis_node_type       = "cache.r6g.large"
min_capacity          = 2
max_capacity          = 20
rds_multi_az          = true
rds_deletion_protection = true
monthly_budget        = 5000

# Feature flags for production
enable_shield_advanced = true
rds_backup_retention_period = 7
enable_detailed_monitoring = true
EOF2
        ;;
esac)

# Cost Management
cost_alert_email = "admin@activelog.com"

# Security
allowed_cidr_blocks = ["0.0.0.0/0"]  # Restrict this in production

# Monitoring
log_retention_days = 30
enable_xray_tracing = true
EOF
    
    print_success "Created $TFVARS_FILE"
}

# Function to validate Terraform configuration
validate_terraform() {
    print_status "Validating Terraform configuration..."
    
    cd "$TERRAFORM_DIR"
    
    terraform validate
    terraform fmt -check
    
    print_success "Terraform configuration is valid"
}

# Function to plan Terraform changes
plan_terraform() {
    print_status "Planning Terraform changes..."
    
    cd "$TERRAFORM_DIR"
    
    local plan_args="-var-file=${ENVIRONMENT}.tfvars -out=${ENVIRONMENT}.tfplan"
    
    if [[ "$DESTROY" == true ]]; then
        plan_args="-destroy $plan_args"
    fi
    
    terraform plan $plan_args
    
    print_success "Terraform plan completed"
}

# Function to apply Terraform changes
apply_terraform() {
    print_status "Applying Terraform changes..."
    
    cd "$TERRAFORM_DIR"
    
    local apply_args="${ENVIRONMENT}.tfplan"
    
    if [[ "$AUTO_APPROVE" == true ]]; then
        apply_args="-auto-approve $apply_args"
    fi
    
    terraform apply $apply_args
    
    if [[ "$DESTROY" == true ]]; then
        print_success "Infrastructure destroyed successfully"
    else
        print_success "Infrastructure deployed successfully"
        show_deployment_info
    fi
}

# Function to show deployment information
show_deployment_info() {
    print_status "Retrieving deployment information..."
    
    cd "$TERRAFORM_DIR"
    
    # Get outputs
    APP_URL=$(terraform output -raw application_url 2>/dev/null || echo "Not available")
    API_URL=$(terraform output -raw api_url 2>/dev/null || echo "Not available")
    ADMIN_URL=$(terraform output -raw admin_url 2>/dev/null || echo "Not available")
    
    cat << EOF

🚀 DEPLOYMENT SUCCESSFUL!

📋 Deployment Summary:
┌─────────────────────────┬────────────────────────────────┐
│ Environment             │ ${ENVIRONMENT}                     │
│ AWS Region              │ ${REGION}                         │
│ AWS Account ID          │ ${AWS_ACCOUNT_ID}                │
│ Domain Name             │ ${DOMAIN_NAME}                   │
└─────────────────────────┴────────────────────────────────┘

🌐 Application URLs:
┌─────────────────────────┬────────────────────────────────┐
│ Main Application        │ ${APP_URL}                      │
│ API Endpoint            │ ${API_URL}                      │
│ Admin Panel             │ ${ADMIN_URL}                    │
└─────────────────────────┴────────────────────────────────┘

📊 Monitoring & Management:
┌─────────────────────────┬────────────────────────────────┐
│ AWS Console             │ https://console.aws.amazon.com  │
│ CloudWatch Dashboards   │ Check outputs for dashboard URLs│
│ Cost Management         │ https://console.aws.amazon.com/billing/│
└─────────────────────────┴────────────────────────────────┘

⚠️  IMPORTANT NEXT STEPS:
1. Update your DNS nameservers if using a custom domain
2. Configure your application secrets in AWS Secrets Manager
3. Deploy your application containers to ECR repositories
4. Set up monitoring alerts and notifications
5. Review and configure security groups for your specific needs

📖 For more information, check the outputs:
   terraform output
   
🎉 Your ActiveLog infrastructure is ready!
EOF
}

# Function to cleanup temporary files
cleanup() {
    print_status "Cleaning up temporary files..."
    
    cd "$TERRAFORM_DIR"
    
    # Remove plan files
    rm -f *.tfplan
    rm -f backend.hcl
    
    print_success "Cleanup completed"
}

# Function to show confirmation prompt
show_confirmation() {
    if [[ "$SKIP_CONFIRMATION" == true ]]; then
        return 0
    fi
    
    echo
    print_warning "You are about to:"
    if [[ "$DESTROY" == true ]]; then
        echo "  🔥 DESTROY the $ENVIRONMENT infrastructure"
        echo "  🗑️  This will DELETE all resources and data!"
    else
        echo "  🚀 DEPLOY the $ENVIRONMENT infrastructure"
        echo "  💰 This will create billable AWS resources"
    fi
    echo "  🌍 Region: $REGION"
    if [[ -n "$DOMAIN_NAME" ]]; then
        echo "  🌐 Domain: $DOMAIN_NAME"
    fi
    echo
    
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        print_status "Operation cancelled by user"
        exit 0
    fi
}

# Main execution function
main() {
    print_status "Starting ActiveLog AWS Infrastructure Deployment"
    print_status "Environment: $ENVIRONMENT"
    print_status "Region: $REGION"
    if [[ -n "$DOMAIN_NAME" ]]; then
        print_status "Domain: $DOMAIN_NAME"
    fi
    
    check_prerequisites
    get_aws_info
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "DRY RUN MODE - No changes will be made"
        estimate_costs
        setup_terraform_backend
        init_terraform
        create_tfvars
        validate_terraform
        plan_terraform
        print_success "Dry run completed successfully"
        return 0
    fi
    
    estimate_costs
    show_confirmation
    
    setup_terraform_backend
    init_terraform
    
    if [[ "$DESTROY" == false ]]; then
        create_tfvars
    fi
    
    validate_terraform
    plan_terraform
    apply_terraform
    cleanup
}

# Trap for cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"

print_success "Script execution completed!"