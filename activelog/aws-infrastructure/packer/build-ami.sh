#!/bin/bash
# Build ActiveLog Base AMI using Packer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
AWS_REGION=${2:-us-east-1}
INSTANCE_TYPE=${3:-t3.medium}

echo -e "${BLUE}🏗️  Building ActiveLog Base AMI${NC}"
echo -e "${BLUE}=====================================${NC}"
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION" 
echo "Instance Type: $INSTANCE_TYPE"
echo ""

# Check prerequisites
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

# Check if Packer is installed
if ! command -v packer &> /dev/null; then
    echo -e "${RED}❌ Packer is not installed. Please install Packer first.${NC}"
    exit 1
fi

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install AWS CLI first.${NC}"
    exit 1
fi

# Test AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Validate Packer template
echo -e "${YELLOW}🔧 Validating Packer template...${NC}"
if ! packer validate -var "environment=$ENVIRONMENT" -var "aws_region=$AWS_REGION" -var "instance_type=$INSTANCE_TYPE" activelog-base.pkr.hcl; then
    echo -e "${RED}❌ Packer template validation failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Packer template validation passed${NC}"

# Build AMI
echo -e "${YELLOW}🚀 Starting AMI build...${NC}"
echo "This process will take 10-15 minutes..."
echo ""

start_time=$(date +%s)

if packer build \
    -var "environment=$ENVIRONMENT" \
    -var "aws_region=$AWS_REGION" \
    -var "instance_type=$INSTANCE_TYPE" \
    activelog-base.pkr.hcl; then
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    minutes=$((duration / 60))
    seconds=$((duration % 60))
    
    echo ""
    echo -e "${GREEN}✅ AMI build completed successfully!${NC}"
    echo -e "${GREEN}⏱️  Build time: ${minutes}m ${seconds}s${NC}"
    
    # Get the AMI ID from Packer output
    AMI_ID=$(aws ec2 describe-images \
        --owners self \
        --filters "Name=name,Values=activelog-base-$ENVIRONMENT-*" \
        --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
        --output text \
        --region $AWS_REGION)
    
    if [ "$AMI_ID" != "None" ] && [ -n "$AMI_ID" ]; then
        echo -e "${GREEN}📋 AMI Details:${NC}"
        echo "   AMI ID: $AMI_ID"
        echo "   Region: $AWS_REGION"
        echo "   Environment: $ENVIRONMENT"
        echo ""
        
        # Get AMI details
        aws ec2 describe-images \
            --image-ids $AMI_ID \
            --query 'Images[0].{Name:Name,Description:Description,CreationDate:CreationDate,State:State}' \
            --output table \
            --region $AWS_REGION
        
        # Save AMI ID to file for Terraform
        echo $AMI_ID > ../terraform/ami_id_${ENVIRONMENT}.txt
        echo -e "${GREEN}💾 AMI ID saved to ami_id_${ENVIRONMENT}.txt${NC}"
        
        echo ""
        echo -e "${BLUE}🎯 Next Steps:${NC}"
        echo "1. Update Terraform variables with new AMI ID: $AMI_ID"
        echo "2. Run terraform plan to see changes"
        echo "3. Run terraform apply to deploy with new AMI"
        echo ""
        echo -e "${BLUE}💡 Terraform variable update:${NC}"
        echo "export TF_VAR_activelog_ami_id=$AMI_ID"
    else
        echo -e "${YELLOW}⚠️  Could not retrieve AMI ID automatically${NC}"
        echo "Please check AWS Console for the created AMI"
    fi
    
else
    echo -e "${RED}❌ AMI build failed${NC}"
    exit 1
fi

# Test the AMI (optional)
echo ""
read -p "Do you want to test launch an instance with the new AMI? (y/N): " test_launch

if [[ $test_launch =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🧪 Launching test instance...${NC}"
    
    # Get default VPC and subnet
    VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $AWS_REGION)
    SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0].SubnetId' --output text --region $AWS_REGION)
    
    # Create security group for testing
    SG_ID=$(aws ec2 create-security-group \
        --group-name activelog-test-sg-$(date +%s) \
        --description "Temporary security group for ActiveLog AMI testing" \
        --vpc-id $VPC_ID \
        --query 'GroupId' \
        --output text \
        --region $AWS_REGION)
    
    # Allow SSH access
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region $AWS_REGION
    
    # Launch test instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --count 1 \
        --instance-type t3.micro \
        --subnet-id $SUBNET_ID \
        --security-group-ids $SG_ID \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=activelog-ami-test},{Key=Environment,Value=test}]" \
        --query 'Instances[0].InstanceId' \
        --output text \
        --region $AWS_REGION)
    
    echo -e "${GREEN}✅ Test instance launched: $INSTANCE_ID${NC}"
    echo -e "${YELLOW}⚠️  Remember to terminate the test instance when done:${NC}"
    echo "aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $AWS_REGION"
    echo "aws ec2 delete-security-group --group-id $SG_ID --region $AWS_REGION"
fi

echo ""
echo -e "${GREEN}🎉 ActiveLog AMI build process completed!${NC}"