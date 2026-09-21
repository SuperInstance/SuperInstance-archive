#!/bin/bash

# ActiveLog Domain Deployment Script
# Deploys all 11 domains with standardized infrastructure

set -e

# Configuration
DOMAINS=("PersonalLog" "MakerLog" "LucidDreamer" "BusinessLog" "Capitaine" "DeckBoss" "DMLog" "FishingLog" "RealLog" "PlayerLog" "StudyLog")
KEY_NAME="activelog-key"
INSTANCE_TYPE="t3.small"
AMI_ID="ami-0c02fb55956c7d316"  # Ubuntu 22.04 LTS
HOSTED_ZONE_ID="Z0123456789ABCDEFGH"  # Replace with actual hosted zone ID

echo "Starting deployment of all ActiveLog domains..."

# Create EC2 instances and Route53 records for each domain
for DOMAIN in "${DOMAINS[@]}"; do
    echo "Deploying infrastructure for ${DOMAIN}..."
    
    # Create security group for domain
    aws ec2 create-security-group \
        --group-name "sg-domain-${DOMAIN}" \
        --description "Security group for ${DOMAIN} domain" \
        --tag-specifications "ResourceType=security-group,Tags=[{Key=Domain,Value=${DOMAIN}}]" || true
    
    # Add security group rules
    aws ec2 authorize-security-group-ingress \
        --group-name "sg-domain-${DOMAIN}" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 || true
    
    aws ec2 authorize-security-group-ingress \
        --group-name "sg-domain-${DOMAIN}" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 || true
    
    aws ec2 authorize-security-group-ingress \
        --group-name "sg-domain-${DOMAIN}" \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 || true
    
    # Create EC2 instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id ${AMI_ID} \
        --instance-type ${INSTANCE_TYPE} \
        --key-name ${KEY_NAME} \
        --security-groups "sg-domain-${DOMAIN}" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${DOMAIN}-server},{Key=Domain,Value=${DOMAIN}}]" \
        --query 'Instances[0].InstanceId' \
        --output text)
    
    echo "Created EC2 instance: ${INSTANCE_ID} for ${DOMAIN}"
    
    # Wait for instance to be running
    aws ec2 wait instance-running --instance-ids ${INSTANCE_ID}
    
    # Get public IP
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids ${INSTANCE_ID} \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    echo "Instance ${INSTANCE_ID} is running with IP: ${PUBLIC_IP}"
    
    # Create Route53 record (commented out - requires actual hosted zone)
    # aws route53 change-resource-record-sets \
    #     --hosted-zone-id ${HOSTED_ZONE_ID} \
    #     --change-batch "{\"Changes\":[{\"Action\":\"CREATE\",\"ResourceRecordSet\":{\"Name\":\"${DOMAIN}.activelog.ai\",\"Type\":\"A\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"${PUBLIC_IP}\"}]}}]}"
    
    echo "Domain ${DOMAIN} infrastructure deployed successfully"
    echo "---"
done

echo "All domain infrastructure deployed successfully!"