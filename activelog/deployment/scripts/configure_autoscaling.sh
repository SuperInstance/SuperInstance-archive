#!/bin/bash

set -e

ENVIRONMENT=${1:-beta}
AWS_REGION=${AWS_DEFAULT_REGION:-us-west-2}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_status "Configuring auto-scaling for environment: $ENVIRONMENT"

# Get all Auto Scaling Groups for this environment
ASG_NAMES=$(aws autoscaling describe-auto-scaling-groups \
    --query "AutoScalingGroups[?contains(Tags[?Key=='Environment'].Value, '$ENVIRONMENT')].AutoScalingGroupName" \
    --output text)

if [[ -z "$ASG_NAMES" ]]; then
    print_error "No Auto Scaling Groups found for environment: $ENVIRONMENT"
    exit 1
fi

print_status "Found Auto Scaling Groups:"
echo "$ASG_NAMES" | tr '\t' '\n' | sed 's/^/  - /'

# Configure scaling policies for each ASG
echo "$ASG_NAMES" | tr '\t' '\n' | while read -r asg_name; do
    if [[ -z "$asg_name" ]]; then
        continue
    fi
    
    print_status "Configuring scaling policies for: $asg_name"
    
    # Get domain name from tags
    DOMAIN_NAME=$(aws autoscaling describe-auto-scaling-groups \
        --auto-scaling-group-names "$asg_name" \
        --query "AutoScalingGroups[0].Tags[?Key=='Domain'].Value" \
        --output text)
    
    print_status "  Domain: ${DOMAIN_NAME:-Unknown}"
    
    # Create enhanced scaling policies
    
    # CPU-based scaling
    SCALE_UP_POLICY_ARN=$(aws autoscaling put-scaling-policy \
        --auto-scaling-group-name "$asg_name" \
        --policy-name "${asg_name}-cpu-scale-up" \
        --policy-type "TargetTrackingScaling" \
        --target-tracking-configuration '{
            "TargetValue": 70.0,
            "PredefinedMetricSpecification": {
                "PredefinedMetricType": "ASGAverageCPUUtilization"
            },
            "ScaleOutCooldown": 300,
            "ScaleInCooldown": 300
        }' \
        --query 'PolicyARN' \
        --output text)
    
    print_success "  Created CPU-based scaling policy: $SCALE_UP_POLICY_ARN"
    
    # Request count-based scaling (ALB)
    ALB_ARN=$(aws autoscaling describe-auto-scaling-groups \
        --auto-scaling-group-names "$asg_name" \
        --query "AutoScalingGroups[0].TargetGroupARNs[0]" \
        --output text)
    
    if [[ -n "$ALB_ARN" && "$ALB_ARN" != "None" ]]; then
        # Get the load balancer name from target group ARN
        LB_NAME=$(echo "$ALB_ARN" | cut -d'/' -f2)
        
        REQUEST_COUNT_POLICY_ARN=$(aws autoscaling put-scaling-policy \
            --auto-scaling-group-name "$asg_name" \
            --policy-name "${asg_name}-request-count-scale" \
            --policy-type "TargetTrackingScaling" \
            --target-tracking-configuration '{
                "TargetValue": 1000.0,
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "ALBRequestCountPerTarget",
                    "ResourceLabel": "'$LB_NAME'/'$(echo "$ALB_ARN" | cut -d'/' -f3)'"
                },
                "ScaleOutCooldown": 300,
                "ScaleInCooldown": 300
            }' \
            --query 'PolicyARN' \
            --output text 2>/dev/null || echo "")
        
        if [[ -n "$REQUEST_COUNT_POLICY_ARN" ]]; then
            print_success "  Created request count-based scaling policy: $REQUEST_COUNT_POLICY_ARN"
        else
            print_warning "  Could not create request count-based scaling policy"
        fi
    fi
    
    # Memory-based scaling (custom metric)
    MEMORY_SCALE_POLICY_ARN=$(aws autoscaling put-scaling-policy \
        --auto-scaling-group-name "$asg_name" \
        --policy-name "${asg_name}-memory-scale-up" \
        --policy-type "StepScaling" \
        --step-adjustments '[
            {
                "MetricIntervalLowerBound": 0,
                "MetricIntervalUpperBound": 20,
                "ScalingAdjustment": 1
            },
            {
                "MetricIntervalLowerBound": 20,
                "ScalingAdjustment": 2
            }
        ]' \
        --adjustment-type "ChangeInCapacity" \
        --cooldown 300 \
        --query 'PolicyARN' \
        --output text)
    
    print_success "  Created memory-based scaling policy: $MEMORY_SCALE_POLICY_ARN"
    
    # Create CloudWatch alarms for memory scaling
    aws cloudwatch put-metric-alarm \
        --alarm-name "${asg_name}-high-memory" \
        --alarm-description "High memory utilization for $asg_name" \
        --metric-name MemoryUtilization \
        --namespace "AWS/EC2" \
        --statistic Average \
        --period 300 \
        --threshold 80 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-actions "$MEMORY_SCALE_POLICY_ARN" \
        --dimensions "Name=AutoScalingGroupName,Value=$asg_name"
    
    print_success "  Created memory utilization alarm"
    
    # Predictive scaling (if supported)
    PREDICTIVE_POLICY=$(aws autoscaling put-scaling-policy \
        --auto-scaling-group-name "$asg_name" \
        --policy-name "${asg_name}-predictive-scaling" \
        --policy-type "PredictiveScaling" \
        --predictive-scaling-configuration '{
            "MetricSpecifications": [
                {
                    "TargetValue": 70.0,
                    "PredefinedMetricSpecification": {
                        "PredefinedMetricType": "ASGAverageCPUUtilization"
                    }
                }
            ],
            "Mode": "ForecastAndScale",
            "SchedulingBufferTime": 300,
            "MaxCapacityBreachBehavior": "HonorMaxCapacity",
            "MaxCapacityBuffer": 10
        }' \
        --query 'PolicyARN' \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$PREDICTIVE_POLICY" ]]; then
        print_success "  Created predictive scaling policy: $PREDICTIVE_POLICY"
    else
        print_warning "  Predictive scaling not available in this region"
    fi
    
    # Configure scheduled scaling for cost optimization
    if [[ "$ENVIRONMENT" != "production" ]]; then
        print_status "  Setting up scheduled scaling for cost optimization..."
        
        # Scale down at night (11 PM UTC)
        aws autoscaling put-scheduled-update-group-action \
            --auto-scaling-group-name "$asg_name" \
            --scheduled-action-name "${asg_name}-scale-down-night" \
            --recurrence "0 23 * * MON-FRI" \
            --desired-capacity 0 \
            --min-size 0 > /dev/null
        
        # Scale up in morning (8 AM UTC)  
        aws autoscaling put-scheduled-update-group-action \
            --auto-scaling-group-name "$asg_name" \
            --scheduled-action-name "${asg_name}-scale-up-morning" \
            --recurrence "0 8 * * MON-FRI" \
            --desired-capacity 1 \
            --min-size 1 > /dev/null
        
        # Weekend scaling (minimal resources)
        aws autoscaling put-scheduled-update-group-action \
            --auto-scaling-group-name "$asg_name" \
            --scheduled-action-name "${asg_name}-scale-down-weekend" \
            --recurrence "0 23 * * FRI" \
            --desired-capacity 0 \
            --min-size 0 > /dev/null
        
        aws autoscaling put-scheduled-update-group-action \
            --auto-scaling-group-name "$asg_name" \
            --scheduled-action-name "${asg_name}-scale-up-weekend-end" \
            --recurrence "0 8 * * MON" \
            --desired-capacity 1 \
            --min-size 1 > /dev/null
        
        print_success "  Configured scheduled scaling for cost optimization"
    fi
    
    # Create warm pool for faster scaling
    aws autoscaling put-warm-pool \
        --auto-scaling-group-name "$asg_name" \
        --max-group-prepared-capacity 2 \
        --min-size 0 \
        --pool-state "Stopped" \
        --instance-reuse-policy '{"ReuseOnScaleIn": true}' 2>/dev/null || \
        print_warning "  Could not create warm pool (feature may not be available)"
    
    # Configure instance protection for critical instances
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Enable termination protection for at least one instance
        INSTANCE_IDS=$(aws autoscaling describe-auto-scaling-groups \
            --auto-scaling-group-names "$asg_name" \
            --query "AutoScalingGroups[0].Instances[0].InstanceId" \
            --output text)
        
        if [[ -n "$INSTANCE_IDS" && "$INSTANCE_IDS" != "None" ]]; then
            aws autoscaling set-instance-protection \
                --instance-ids "$INSTANCE_IDS" \
                --auto-scaling-group-name "$asg_name" \
                --protected-from-scale-in 2>/dev/null || \
                print_warning "  Could not set instance protection"
            
            print_success "  Enabled termination protection for critical instance"
        fi
    fi
    
    echo
done

# Configure Application Auto Scaling for ECS/Fargate services (if any)
print_status "Checking for ECS services to configure auto-scaling..."

ECS_CLUSTERS=$(aws ecs list-clusters --query "clusterArns[?contains(@, '$ENVIRONMENT')]" --output text 2>/dev/null || echo "")

if [[ -n "$ECS_CLUSTERS" ]]; then
    echo "$ECS_CLUSTERS" | tr '\t' '\n' | while read -r cluster_arn; do
        if [[ -z "$cluster_arn" ]]; then
            continue
        fi
        
        cluster_name=$(echo "$cluster_arn" | cut -d'/' -f2)
        print_status "Found ECS cluster: $cluster_name"
        
        # Get services in cluster
        SERVICES=$(aws ecs list-services --cluster "$cluster_name" --query "serviceArns" --output text 2>/dev/null || echo "")
        
        if [[ -n "$SERVICES" ]]; then
            echo "$SERVICES" | tr '\t' '\n' | while read -r service_arn; do
                if [[ -z "$service_arn" ]]; then
                    continue
                fi
                
                service_name=$(echo "$service_arn" | cut -d'/' -f3)
                print_status "  Configuring auto-scaling for ECS service: $service_name"
                
                # Register scalable target
                aws application-autoscaling register-scalable-target \
                    --service-namespace ecs \
                    --resource-id "service/$cluster_name/$service_name" \
                    --scalable-dimension "ecs:service:DesiredCount" \
                    --min-capacity 1 \
                    --max-capacity 10 2>/dev/null || \
                    print_warning "    Could not register scalable target for $service_name"
                
                # CPU-based scaling policy
                aws application-autoscaling put-scaling-policy \
                    --service-namespace ecs \
                    --resource-id "service/$cluster_name/$service_name" \
                    --scalable-dimension "ecs:service:DesiredCount" \
                    --policy-name "${service_name}-cpu-scaling" \
                    --policy-type "TargetTrackingScaling" \
                    --target-tracking-scaling-policy-configuration '{
                        "TargetValue": 70.0,
                        "PredefinedMetricSpecification": {
                            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
                        },
                        "ScaleOutCooldown": 300,
                        "ScaleInCooldown": 300
                    }' 2>/dev/null || \
                    print_warning "    Could not create ECS scaling policy for $service_name"
                
                print_success "    Configured ECS auto-scaling for $service_name"
            done
        fi
    done
fi

# Create cost optimization Lambda function
print_status "Creating cost optimization Lambda function..."

LAMBDA_FUNCTION_NAME="activelog-cost-optimizer-$ENVIRONMENT"

# Create Lambda execution role
LAMBDA_ROLE_NAME="activelog-lambda-execution-role-$ENVIRONMENT"

TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'

LAMBDA_ROLE_ARN=$(aws iam create-role \
    --role-name "$LAMBDA_ROLE_NAME" \
    --assume-role-policy-document "$TRUST_POLICY" \
    --query 'Role.Arn' \
    --output text 2>/dev/null || \
    aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --query 'Role.Arn' --output text)

# Attach policies
aws iam attach-role-policy \
    --role-name "$LAMBDA_ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>/dev/null || true

aws iam attach-role-policy \
    --role-name "$LAMBDA_ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/AutoScalingFullAccess" 2>/dev/null || true

# Create Lambda function code
cat > /tmp/cost_optimizer.py << 'EOF'
import json
import boto3
import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    autoscaling = boto3.client('autoscaling')
    cloudwatch = boto3.client('cloudwatch')
    
    environment = event.get('environment', 'beta')
    
    try:
        # Get all ASGs for this environment
        response = autoscaling.describe_auto_scaling_groups()
        
        for asg in response['AutoScalingGroups']:
            asg_name = asg['AutoScalingGroupName']
            
            # Check if ASG belongs to our environment
            environment_tag = next((tag['Value'] for tag in asg['Tags'] if tag['Key'] == 'Environment'), None)
            
            if environment_tag != environment:
                continue
            
            logger.info(f"Processing ASG: {asg_name}")
            
            # Get recent metrics
            end_time = datetime.datetime.utcnow()
            start_time = end_time - datetime.timedelta(hours=1)
            
            # Check CPU utilization
            cpu_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[
                    {
                        'Name': 'AutoScalingGroupName',
                        'Value': asg_name
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if cpu_response['Datapoints']:
                avg_cpu = sum(point['Average'] for point in cpu_response['Datapoints']) / len(cpu_response['Datapoints'])
                logger.info(f"Average CPU for {asg_name}: {avg_cpu}%")
                
                # Scale down if CPU is very low for non-production environments
                if environment != 'production' and avg_cpu < 5 and asg['DesiredCapacity'] > 0:
                    logger.info(f"Scaling down {asg_name} due to low CPU utilization")
                    autoscaling.set_desired_capacity(
                        AutoScalingGroupName=asg_name,
                        DesiredCapacity=max(0, asg['DesiredCapacity'] - 1),
                        HonorCooldown=True
                    )
                
                # Scale up if CPU is high
                elif avg_cpu > 80 and asg['DesiredCapacity'] < asg['MaxSize']:
                    logger.info(f"Scaling up {asg_name} due to high CPU utilization")
                    autoscaling.set_desired_capacity(
                        AutoScalingGroupName=asg_name,
                        DesiredCapacity=min(asg['MaxSize'], asg['DesiredCapacity'] + 1),
                        HonorCooldown=True
                    )
        
        return {
            'statusCode': 200,
            'body': json.dumps('Cost optimization completed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
EOF

# Package Lambda function
cd /tmp
zip cost_optimizer.zip cost_optimizer.py

# Wait for role to be available
sleep 10

# Create or update Lambda function
aws lambda create-function \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --runtime "python3.9" \
    --role "$LAMBDA_ROLE_ARN" \
    --handler "cost_optimizer.lambda_handler" \
    --zip-file "fileb://cost_optimizer.zip" \
    --description "ActiveLog cost optimization function" \
    --timeout 300 \
    --environment "Variables={ENVIRONMENT=$ENVIRONMENT}" 2>/dev/null || \
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file "fileb://cost_optimizer.zip" >/dev/null

print_success "Created/updated cost optimization Lambda function: $LAMBDA_FUNCTION_NAME"

# Create CloudWatch rule to trigger Lambda every 30 minutes
RULE_NAME="activelog-cost-optimization-$ENVIRONMENT"

aws events put-rule \
    --name "$RULE_NAME" \
    --schedule-expression "rate(30 minutes)" \
    --description "Trigger cost optimization for ActiveLog $ENVIRONMENT" \
    --state ENABLED > /dev/null

# Add Lambda as target
LAMBDA_ARN=$(aws lambda get-function --function-name "$LAMBDA_FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text)

aws events put-targets \
    --rule "$RULE_NAME" \
    --targets "Id=1,Arn=$LAMBDA_ARN,Input='{\"environment\":\"$ENVIRONMENT\"}'" > /dev/null

# Add permission for EventBridge to invoke Lambda
aws lambda add-permission \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --statement-id "AllowExecutionFromCloudWatch" \
    --action "lambda:InvokeFunction" \
    --principal "events.amazonaws.com" \
    --source-arn "arn:aws:events:$AWS_REGION:$(aws sts get-caller-identity --query 'Account' --output text):rule/$RULE_NAME" 2>/dev/null || true

print_success "Configured scheduled cost optimization (every 30 minutes)"

# Cleanup
rm -f /tmp/cost_optimizer.py /tmp/cost_optimizer.zip

print_success "Auto-scaling configuration completed for environment: $ENVIRONMENT"

# Create summary report
cat > "autoscaling_config_${ENVIRONMENT}.txt" << EOF
Auto-Scaling Configuration Summary
=================================
Environment: $ENVIRONMENT
Configuration Date: $(date)
AWS Region: $AWS_REGION

Auto Scaling Groups Configured:
$(echo "$ASG_NAMES" | tr '\t' '\n' | sed 's/^/  - /')

Scaling Policies Created:
  - Target Tracking Scaling (CPU utilization: 70%)
  - Target Tracking Scaling (Request count: 1000 per target)
  - Step Scaling (Memory utilization)
  - Predictive Scaling (where available)

Cost Optimization Features:
  - Scheduled scaling (nights and weekends for non-production)
  - Warm pools for faster scaling
  - Lambda-based intelligent scaling
  - Instance termination protection (production only)

Lambda Function: $LAMBDA_FUNCTION_NAME
CloudWatch Rule: $RULE_NAME

Next Steps:
1. Monitor scaling activities in AWS Console
2. Review CloudWatch alarms and metrics
3. Adjust thresholds based on actual usage patterns
4. Test scaling during peak load scenarios
EOF

print_status "Configuration summary saved to autoscaling_config_${ENVIRONMENT}.txt"