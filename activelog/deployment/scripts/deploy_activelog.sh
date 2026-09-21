#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="beta"
MIN_RESOURCES="false"
AWS_REGION="us-west-2"
TERRAFORM_WORKSPACE=""
SKIP_CONFIRMATION="false"

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
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy ActiveLog ecosystem to AWS

OPTIONS:
    --environment=ENV       Set environment (beta, staging, production) [default: beta]
    --min-resources        Use minimal resources for cost optimization
    --region=REGION        AWS region [default: us-west-2]
    --workspace=NAME       Terraform workspace name
    --skip-confirmation    Skip confirmation prompts
    --help                 Show this help message

EXAMPLES:
    # Deploy with minimal resources for beta testing
    $0 --environment=beta --min-resources

    # Deploy to production
    $0 --environment=production --region=us-east-1

    # Deploy to staging with specific workspace
    $0 --environment=staging --workspace=staging-v2
EOF
}

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --environment=*)
            ENVIRONMENT="${arg#*=}"
            shift
            ;;
        --min-resources)
            MIN_RESOURCES="true"
            shift
            ;;
        --region=*)
            AWS_REGION="${arg#*=}"
            shift
            ;;
        --workspace=*)
            TERRAFORM_WORKSPACE="${arg#*=}"
            shift
            ;;
        --skip-confirmation)
            SKIP_CONFIRMATION="true"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $arg"
            show_usage
            exit 1
            ;;
    esac
done

print_status "Starting ActiveLog deployment..."
print_status "Environment: $ENVIRONMENT"
print_status "Region: $AWS_REGION"
print_status "Min Resources: $MIN_RESOURCES"

# Check prerequisites
print_status "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found. Please install Terraform first."
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker first."
    exit 1
fi

# Verify AWS credentials
print_status "Verifying AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    print_error "AWS credentials not configured or invalid."
    print_error "Please run 'aws configure' or set AWS environment variables."
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
print_success "AWS credentials verified. Account ID: $AWS_ACCOUNT_ID"

# Set AWS region
export AWS_DEFAULT_REGION=$AWS_REGION
print_status "Using AWS region: $AWS_REGION"

# Check if user has necessary permissions
print_status "Checking AWS permissions..."
required_services=("ec2" "s3" "iam" "cloudwatch" "autoscaling" "elasticloadbalancing")
for service in "${required_services[@]}"; do
    if ! aws iam simulate-principal-policy \
        --policy-source-arn "arn:aws:iam::$AWS_ACCOUNT_ID:user/$(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)" \
        --action-names "${service}:*" \
        --resource-arns "*" \
        --query 'EvaluationResults[0].EvalDecision' \
        --output text 2>/dev/null | grep -q "allowed"; then
        print_warning "May not have sufficient permissions for $service"
    fi
done

# Create domains list
cat > domains.txt << EOF
DMLog
PersonalLog
BusinessLog
FishingLog
StudyLog
MakerLog
EOF

print_status "Domains to deploy:"
cat domains.txt

# Confirmation
if [[ "$SKIP_CONFIRMATION" != "true" ]]; then
    echo
    print_warning "This will create AWS resources that may incur costs."
    read -p "Continue with deployment? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled."
        exit 0
    fi
fi

# Change to terraform directory
cd "$(dirname "$0")/../terraform"

# Initialize Terraform
print_status "Initializing Terraform..."
if ! terraform init; then
    print_error "Terraform initialization failed"
    exit 1
fi

# Setup Terraform workspace
if [[ -n "$TERRAFORM_WORKSPACE" ]]; then
    print_status "Setting up Terraform workspace: $TERRAFORM_WORKSPACE"
    terraform workspace select "$TERRAFORM_WORKSPACE" 2>/dev/null || terraform workspace new "$TERRAFORM_WORKSPACE"
fi

# Create terraform.tfvars file
print_status "Generating Terraform variables..."
cat > terraform.tfvars << EOF
aws_region = "$AWS_REGION"
environment = "$ENVIRONMENT"

domains = {
EOF

# Add domain configurations based on min_resources flag
if [[ "$MIN_RESOURCES" == "true" ]]; then
    cat >> terraform.tfvars << 'EOF'
  "DMLog" = {
    backend_instance_type    = "t3.micro"
    repository_instance_type = "t3.micro"
    deployer_instance_type   = "t3.micro"
    trainer_instance_type    = "t3.small"
    builder_instance_type    = "t3.micro"
    runner_instance_type     = "t3.micro"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 2
  }
  "PersonalLog" = {
    backend_instance_type    = "t3.micro"
    repository_instance_type = "t3.micro"
    deployer_instance_type   = "t3.micro"
    trainer_instance_type    = "t3.small"
    builder_instance_type    = "t3.micro"
    runner_instance_type     = "t3.micro"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 2
  }
  "BusinessLog" = {
    backend_instance_type    = "t3.micro"
    repository_instance_type = "t3.micro"
    deployer_instance_type   = "t3.micro"
    trainer_instance_type    = "t3.small"
    builder_instance_type    = "t3.micro"
    runner_instance_type     = "t3.micro"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 2
  }
  "FishingLog" = {
    backend_instance_type    = "t3.micro"
    repository_instance_type = "t3.micro"
    deployer_instance_type   = "t3.micro"
    trainer_instance_type    = "t3.small"
    builder_instance_type    = "t3.micro"
    runner_instance_type     = "t3.micro"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 2
  }
  "StudyLog" = {
    backend_instance_type    = "t3.micro"
    repository_instance_type = "t3.micro"
    deployer_instance_type   = "t3.micro"
    trainer_instance_type    = "t3.small"
    builder_instance_type    = "t3.micro"
    runner_instance_type     = "t3.micro"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 2
  }
  "MakerLog" = {
    backend_instance_type    = "t3.micro"
    repository_instance_type = "t3.micro"
    deployer_instance_type   = "t3.micro"
    trainer_instance_type    = "t3.small"
    builder_instance_type    = "t3.micro"
    runner_instance_type     = "t3.micro"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 2
  }
EOF
else
    cat >> terraform.tfvars << 'EOF'
  "DMLog" = {
    backend_instance_type    = "t3.small"
    repository_instance_type = "t3.medium"
    deployer_instance_type   = "t3.small"
    trainer_instance_type    = "g4dn.xlarge"
    builder_instance_type    = "t3.medium"
    runner_instance_type     = "c5.xlarge"
    enable_gpu              = true
    min_instances           = 1
    max_instances           = 5
  }
  "PersonalLog" = {
    backend_instance_type    = "t3.small"
    repository_instance_type = "t3.medium"
    deployer_instance_type   = "t3.small"
    trainer_instance_type    = "t3.large"
    builder_instance_type    = "t3.medium"
    runner_instance_type     = "c5.xlarge"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 3
  }
  "BusinessLog" = {
    backend_instance_type    = "t3.small"
    repository_instance_type = "t3.medium"
    deployer_instance_type   = "t3.small"
    trainer_instance_type    = "t3.large"
    builder_instance_type    = "t3.medium"
    runner_instance_type     = "c5.xlarge"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 3
  }
  "FishingLog" = {
    backend_instance_type    = "t3.small"
    repository_instance_type = "t3.medium"
    deployer_instance_type   = "t3.small"
    trainer_instance_type    = "t3.large"
    builder_instance_type    = "t3.medium"
    runner_instance_type     = "c5.xlarge"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 3
  }
  "StudyLog" = {
    backend_instance_type    = "t3.small"
    repository_instance_type = "t3.medium"
    deployer_instance_type   = "t3.small"
    trainer_instance_type    = "t3.large"
    builder_instance_type    = "t3.medium"
    runner_instance_type     = "c5.xlarge"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 3
  }
  "MakerLog" = {
    backend_instance_type    = "t3.small"
    repository_instance_type = "t3.medium"
    deployer_instance_type   = "t3.small"
    trainer_instance_type    = "t3.large"
    builder_instance_type    = "t3.medium"
    runner_instance_type     = "c5.xlarge"
    enable_gpu              = false
    min_instances           = 1
    max_instances           = 3
  }
EOF
fi

cat >> terraform.tfvars << 'EOF'
}
EOF

# Plan deployment
print_status "Creating Terraform plan..."
if ! terraform plan -var-file=terraform.tfvars -out=tfplan; then
    print_error "Terraform planning failed"
    exit 1
fi

# Apply infrastructure
print_status "Applying Terraform infrastructure..."
if ! terraform apply tfplan; then
    print_error "Terraform apply failed"
    exit 1
fi

print_success "Infrastructure deployment completed!"

# Get outputs
print_status "Retrieving deployment outputs..."
terraform output -json > deployment_outputs.json

# Deploy applications to each domain
print_status "Deploying applications to domains..."
while read -r domain; do
    print_status "Deploying $domain..."
    if [[ -f "../scripts/deploy_domain.sh" ]]; then
        bash "../scripts/deploy_domain.sh" "$domain" "$ENVIRONMENT"
    else
        print_warning "Domain deployment script not found, skipping $domain application deployment"
    fi
done < domains.txt

# Setup monitoring
print_status "Setting up monitoring..."
if [[ -f "../scripts/setup_cloudwatch.sh" ]]; then
    bash "../scripts/setup_cloudwatch.sh" "$ENVIRONMENT"
else
    print_warning "CloudWatch setup script not found"
fi

# Configure auto-scaling
print_status "Configuring auto-scaling..."
if [[ -f "../scripts/configure_autoscaling.sh" ]]; then
    bash "../scripts/configure_autoscaling.sh" "$ENVIRONMENT"
else
    print_warning "Auto-scaling configuration script not found"
fi

# Display results
print_success "ActiveLog ecosystem deployed successfully!"
echo
print_status "Deployment Summary:"
print_status "==================="
print_status "Environment: $ENVIRONMENT"
print_status "Region: $AWS_REGION"
print_status "Account: $AWS_ACCOUNT_ID"
echo

print_status "Domain Endpoints:"
if [[ -f "deployment_outputs.json" ]]; then
    if command -v jq &> /dev/null; then
        jq -r '.domain_endpoints.value | to_entries[] | "  \(.key): https://\(.value)"' deployment_outputs.json
    else
        print_warning "jq not installed, cannot display endpoints nicely"
        cat deployment_outputs.json
    fi
fi

echo
print_status "Monitoring Dashboard:"
if command -v jq &> /dev/null && [[ -f "deployment_outputs.json" ]]; then
    jq -r '.monitoring_dashboard_url.value' deployment_outputs.json
fi

echo
print_success "Access your ActiveLog ecosystem at: https://activelog.ai"
print_status "Deployment completed at: $(date)"

# Save deployment info
cat > deployment_info.txt << EOF
ActiveLog Deployment Information
===============================
Deployment Date: $(date)
Environment: $ENVIRONMENT
AWS Region: $AWS_REGION
AWS Account: $AWS_ACCOUNT_ID
Terraform Workspace: ${TERRAFORM_WORKSPACE:-default}
Min Resources Mode: $MIN_RESOURCES

Domains Deployed:
$(cat domains.txt | sed 's/^/  - /')

Next Steps:
1. Verify all endpoints are responding
2. Configure DNS records for custom domains
3. Set up SSL certificates
4. Configure monitoring alerts
5. Test backup and recovery procedures
EOF

print_status "Deployment information saved to deployment_info.txt"