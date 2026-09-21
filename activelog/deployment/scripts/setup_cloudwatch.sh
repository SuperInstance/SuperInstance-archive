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

print_status "Setting up CloudWatch monitoring for environment: $ENVIRONMENT"

# Create CloudWatch dashboard
DASHBOARD_NAME="ActiveLog-${ENVIRONMENT}"

print_status "Creating CloudWatch dashboard: $DASHBOARD_NAME"

# Get all Auto Scaling Groups for this environment
ASG_NAMES=$(aws autoscaling describe-auto-scaling-groups \
    --query "AutoScalingGroups[?contains(Tags[?Key=='Environment'].Value, '$ENVIRONMENT')].AutoScalingGroupName" \
    --output text)

if [[ -z "$ASG_NAMES" ]]; then
    print_warning "No Auto Scaling Groups found for environment: $ENVIRONMENT"
    ASG_NAMES=""
fi

# Get all Load Balancers for this environment
ALB_ARNS=$(aws elbv2 describe-load-balancers \
    --query "LoadBalancers[?contains(LoadBalancerName, '$ENVIRONMENT') || contains(LoadBalancerName, 'activelog')].LoadBalancerArn" \
    --output text 2>/dev/null || echo "")

# Create comprehensive dashboard configuration
cat > /tmp/dashboard_config.json << EOF
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
$(if [[ -n "$ASG_NAMES" ]]; then
    echo "$ASG_NAMES" | tr '\t' '\n' | head -5 | sed 's/.*/"AWS\/EC2", "CPUUtilization", "AutoScalingGroupName", "&",/' | sed '$s/,$//'
else
    echo '["AWS/EC2", "CPUUtilization"]'
fi)
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$AWS_REGION",
                "title": "EC2 CPU Utilization",
                "period": 300,
                "stat": "Average"
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
$(if [[ -n "$ASG_NAMES" ]]; then
    echo "$ASG_NAMES" | tr '\t' '\n' | head -5 | sed 's/.*/"AWS\/ApplicationELB", "TargetResponseTime", "LoadBalancer", "&",/' | sed '$s/,$//'
else
    echo '["AWS/ApplicationELB", "TargetResponseTime"]'
fi)
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$AWS_REGION",
                "title": "Response Time",
                "period": 300,
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 6,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
$(if [[ -n "$ASG_NAMES" ]]; then
    echo "$ASG_NAMES" | tr '\t' '\n' | head -3 | sed 's/.*/"AWS\/AutoScaling", "GroupDesiredCapacity", "AutoScalingGroupName", "&",\n"AWS\/AutoScaling", "GroupInServiceInstances", "AutoScalingGroupName", "&",/' | sed '$s/,$//'
else
    echo '["AWS/AutoScaling", "GroupDesiredCapacity"]'
fi)
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$AWS_REGION",
                "title": "Auto Scaling Group Capacity",
                "period": 300,
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 8,
            "y": 6,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
$(if [[ -n "$ALB_ARNS" ]]; then
    echo "$ALB_ARNS" | tr '\t' '\n' | head -3 | while read arn; do
        if [[ -n "$arn" ]]; then
            lb_name=$(echo "$arn" | cut -d'/' -f2-4)
            echo "\"AWS/ApplicationELB\", \"RequestCount\", \"LoadBalancer\", \"$lb_name\","
        fi
    done | sed '$s/,$//'
else
    echo '["AWS/ApplicationELB", "RequestCount"]'
fi)
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$AWS_REGION",
                "title": "Request Count",
                "period": 300,
                "stat": "Sum"
            }
        },
        {
            "type": "metric",
            "x": 16,
            "y": 6,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
$(if [[ -n "$ALB_ARNS" ]]; then
    echo "$ALB_ARNS" | tr '\t' '\n' | head -3 | while read arn; do
        if [[ -n "$arn" ]]; then
            lb_name=$(echo "$arn" | cut -d'/' -f2-4)
            echo "\"AWS/ApplicationELB\", \"HTTPCode_Target_4XX_Count\", \"LoadBalancer\", \"$lb_name\","
            echo "\"AWS/ApplicationELB\", \"HTTPCode_Target_5XX_Count\", \"LoadBalancer\", \"$lb_name\","
        fi
    done | sed '$s/,$//'
else
    echo '["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count"], ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count"]'
fi)
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$AWS_REGION",
                "title": "Error Rates",
                "period": 300,
                "stat": "Sum"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 12,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
$(if [[ -n "$ASG_NAMES" ]]; then
    echo "$ASG_NAMES" | tr '\t' '\n' | head -5 | sed 's/.*/"CWAgent", "mem_used_percent", "AutoScalingGroupName", "&",/' | sed '$s/,$//'
else
    echo '["CWAgent", "mem_used_percent"]'
fi)
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$AWS_REGION",
                "title": "Memory Utilization",
                "period": 300,
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 12,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
$(if [[ -n "$ASG_NAMES" ]]; then
    echo "$ASG_NAMES" | tr '\t' '\n' | head -5 | sed 's/.*/"CWAgent", "disk_used_percent", "AutoScalingGroupName", "&", "device", "\/*",/' | sed '$s/,$//'
else
    echo '["CWAgent", "disk_used_percent"]'
fi)
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$AWS_REGION",
                "title": "Disk Utilization",
                "period": 300,
                "stat": "Average"
            }
        },
        {
            "type": "log",
            "x": 0,
            "y": 18,
            "width": 24,
            "height": 6,
            "properties": {
                "query": "SOURCE '/aws/ec2/activelog' | fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 100",
                "region": "$AWS_REGION",
                "title": "Recent Error Logs",
                "view": "table"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 24,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Billing", "EstimatedCharges", "Currency", "USD" ]
                ],
                "view": "singleValue",
                "region": "us-east-1",
                "title": "Estimated Charges (USD)",
                "period": 86400,
                "stat": "Maximum"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 24,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "ActiveLog/Custom", "DeploymentCount", "Environment", "$ENVIRONMENT" ],
                    [ "ActiveLog/Custom", "UserCount", "Environment", "$ENVIRONMENT" ],
                    [ "ActiveLog/Custom", "ActiveSessions", "Environment", "$ENVIRONMENT" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$AWS_REGION",
                "title": "Custom Application Metrics",
                "period": 300,
                "stat": "Average"
            }
        }
    ]
}
EOF

# Create the dashboard
aws cloudwatch put-dashboard \
    --dashboard-name "$DASHBOARD_NAME" \
    --dashboard-body file:///tmp/dashboard_config.json

print_success "Created CloudWatch dashboard: $DASHBOARD_NAME"

# Create CloudWatch log groups
print_status "Creating CloudWatch log groups..."

LOG_GROUPS=(
    "/aws/ec2/activelog"
    "/aws/lambda/activelog-cost-optimizer-$ENVIRONMENT"
    "/aws/applicationloadbalancer/activelog-$ENVIRONMENT"
)

for log_group in "${LOG_GROUPS[@]}"; do
    aws logs create-log-group --log-group-name "$log_group" 2>/dev/null || true
    aws logs put-retention-policy --log-group-name "$log_group" --retention-in-days 30 2>/dev/null || true
    print_status "  Created log group: $log_group"
done

# Create comprehensive CloudWatch alarms
print_status "Creating CloudWatch alarms..."

# High CPU alarm for each ASG
echo "$ASG_NAMES" | tr '\t' '\n' | while read -r asg_name; do
    if [[ -z "$asg_name" ]]; then
        continue
    fi
    
    # High CPU alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${asg_name}-high-cpu" \
        --alarm-description "High CPU utilization for $asg_name" \
        --metric-name CPUUtilization \
        --namespace AWS/EC2 \
        --statistic Average \
        --period 300 \
        --threshold 85 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-severity high \
        --dimensions Name=AutoScalingGroupName,Value="$asg_name"
    
    # High memory alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${asg_name}-high-memory" \
        --alarm-description "High memory utilization for $asg_name" \
        --metric-name mem_used_percent \
        --namespace CWAgent \
        --statistic Average \
        --period 300 \
        --threshold 90 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-severity high \
        --dimensions Name=AutoScalingGroupName,Value="$asg_name"
    
    # High disk usage alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${asg_name}-high-disk" \
        --alarm-description "High disk utilization for $asg_name" \
        --metric-name disk_used_percent \
        --namespace CWAgent \
        --statistic Average \
        --period 300 \
        --threshold 85 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 1 \
        --alarm-severity medium \
        --dimensions Name=AutoScalingGroupName,Value="$asg_name" Name=device,Value="/*"
    
    # Instance status check failed
    aws cloudwatch put-metric-alarm \
        --alarm-name "${asg_name}-instance-status-check" \
        --alarm-description "Instance status check failed for $asg_name" \
        --metric-name StatusCheckFailed_Instance \
        --namespace AWS/EC2 \
        --statistic Maximum \
        --period 60 \
        --threshold 0 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-severity critical \
        --dimensions Name=AutoScalingGroupName,Value="$asg_name"
    
    print_success "  Created alarms for ASG: $asg_name"
done

# Load Balancer alarms
echo "$ALB_ARNS" | tr '\t' '\n' | while read -r alb_arn; do
    if [[ -z "$alb_arn" ]]; then
        continue
    fi
    
    lb_name=$(echo "$alb_arn" | cut -d'/' -f2-4)
    alarm_name=$(echo "$lb_name" | tr '/' '-')
    
    # High response time alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "alb-${alarm_name}-high-response-time" \
        --alarm-description "High response time for ALB $lb_name" \
        --metric-name TargetResponseTime \
        --namespace AWS/ApplicationELB \
        --statistic Average \
        --period 300 \
        --threshold 5 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-severity medium \
        --dimensions Name=LoadBalancer,Value="$lb_name"
    
    # High 4xx error rate
    aws cloudwatch put-metric-alarm \
        --alarm-name "alb-${alarm_name}-high-4xx-errors" \
        --alarm-description "High 4xx error rate for ALB $lb_name" \
        --metric-name HTTPCode_Target_4XX_Count \
        --namespace AWS/ApplicationELB \
        --statistic Sum \
        --period 300 \
        --threshold 10 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-severity medium \
        --dimensions Name=LoadBalancer,Value="$lb_name"
    
    # High 5xx error rate
    aws cloudwatch put-metric-alarm \
        --alarm-name "alb-${alarm_name}-high-5xx-errors" \
        --alarm-description "High 5xx error rate for ALB $lb_name" \
        --metric-name HTTPCode_Target_5XX_Count \
        --namespace AWS/ApplicationELB \
        --statistic Sum \
        --period 300 \
        --threshold 5 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 1 \
        --alarm-severity high \
        --dimensions Name=LoadBalancer,Value="$lb_name"
    
    # Unhealthy hosts alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "alb-${alarm_name}-unhealthy-hosts" \
        --alarm-description "Unhealthy hosts for ALB $lb_name" \
        --metric-name UnHealthyHostCount \
        --namespace AWS/ApplicationELB \
        --statistic Average \
        --period 60 \
        --threshold 0 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-severity critical \
        --dimensions Name=LoadBalancer,Value="$lb_name"
    
    print_success "  Created alarms for ALB: $lb_name"
done

# Cost monitoring alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "activelog-high-cost-$ENVIRONMENT" \
    --alarm-description "High AWS costs for ActiveLog $ENVIRONMENT" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 86400 \
    --threshold 100 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --alarm-severity high \
    --dimensions Name=Currency,Value=USD

print_success "Created cost monitoring alarm"

# Create SNS topic for notifications
SNS_TOPIC_NAME="activelog-alerts-$ENVIRONMENT"

TOPIC_ARN=$(aws sns create-topic --name "$SNS_TOPIC_NAME" --query 'TopicArn' --output text)

print_success "Created SNS topic: $SNS_TOPIC_NAME"

# Create CloudWatch composite alarms
print_status "Creating composite alarms..."

aws cloudwatch put-composite-alarm \
    --alarm-name "activelog-system-health-$ENVIRONMENT" \
    --alarm-description "Overall system health for ActiveLog $ENVIRONMENT" \
    --alarm-rule "FALSE" \
    --actions-enabled

# Update all created alarms to send notifications to SNS
print_status "Configuring alarm notifications..."

ALL_ALARMS=$(aws cloudwatch describe-alarms \
    --query "MetricAlarms[?contains(AlarmName, '$ENVIRONMENT') || contains(AlarmName, 'activelog')].AlarmName" \
    --output text)

echo "$ALL_ALARMS" | tr '\t' '\n' | while read -r alarm_name; do
    if [[ -n "$alarm_name" ]]; then
        aws cloudwatch put-metric-alarm \
            --alarm-name "$alarm_name" \
            --alarm-actions "$TOPIC_ARN" \
            --ok-actions "$TOPIC_ARN" \
            --insufficient-data-actions "$TOPIC_ARN" 2>/dev/null || true
    fi
done

# Create custom metrics Lambda function
print_status "Creating custom metrics Lambda function..."

LAMBDA_FUNCTION_NAME="activelog-custom-metrics-$ENVIRONMENT"

# Create Lambda function code for custom metrics
cat > /tmp/custom_metrics.py << 'EOF'
import json
import boto3
import datetime
import requests
import os
from botocore.exceptions import ClientError

cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    environment = os.environ.get('ENVIRONMENT', 'beta')
    
    try:
        # Example custom metrics - replace with actual data collection
        
        # Simulated user count
        user_count = 100  # Replace with actual user count from database
        
        # Simulated active sessions
        active_sessions = 25  # Replace with actual session count
        
        # Deployment count (could be from CI/CD system)
        deployment_count = 1
        
        # Send custom metrics to CloudWatch
        metrics_data = [
            {
                'MetricName': 'UserCount',
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': environment
                    }
                ],
                'Unit': 'Count',
                'Value': user_count
            },
            {
                'MetricName': 'ActiveSessions',
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': environment
                    }
                ],
                'Unit': 'Count',
                'Value': active_sessions
            },
            {
                'MetricName': 'DeploymentCount',
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': environment
                    }
                ],
                'Unit': 'Count',
                'Value': deployment_count
            }
        ]
        
        # Send metrics to CloudWatch
        cloudwatch.put_metric_data(
            Namespace='ActiveLog/Custom',
            MetricData=metrics_data
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps('Custom metrics sent successfully')
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
EOF

# Package Lambda function
cd /tmp
zip custom_metrics.zip custom_metrics.py

# Get the Lambda execution role ARN (created by autoscaling script)
LAMBDA_ROLE_NAME="activelog-lambda-execution-role-$ENVIRONMENT"
LAMBDA_ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [[ -n "$LAMBDA_ROLE_ARN" ]]; then
    # Create or update Lambda function
    aws lambda create-function \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --runtime "python3.9" \
        --role "$LAMBDA_ROLE_ARN" \
        --handler "custom_metrics.lambda_handler" \
        --zip-file "fileb://custom_metrics.zip" \
        --description "ActiveLog custom metrics collection" \
        --timeout 60 \
        --environment "Variables={ENVIRONMENT=$ENVIRONMENT}" 2>/dev/null || \
    aws lambda update-function-code \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --zip-file "fileb://custom_metrics.zip" >/dev/null
    
    print_success "Created/updated custom metrics Lambda function: $LAMBDA_FUNCTION_NAME"
    
    # Create CloudWatch rule to trigger Lambda every 5 minutes
    RULE_NAME="activelog-custom-metrics-$ENVIRONMENT"
    
    aws events put-rule \
        --name "$RULE_NAME" \
        --schedule-expression "rate(5 minutes)" \
        --description "Trigger custom metrics collection for ActiveLog $ENVIRONMENT" \
        --state ENABLED > /dev/null
    
    # Add Lambda as target
    LAMBDA_ARN=$(aws lambda get-function --function-name "$LAMBDA_FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text)
    
    aws events put-targets \
        --rule "$RULE_NAME" \
        --targets "Id=1,Arn=$LAMBDA_ARN" > /dev/null
    
    # Add permission for EventBridge to invoke Lambda
    aws lambda add-permission \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --statement-id "AllowExecutionFromCloudWatchCustomMetrics" \
        --action "lambda:InvokeFunction" \
        --principal "events.amazonaws.com" \
        --source-arn "arn:aws:events:$AWS_REGION:$(aws sts get-caller-identity --query 'Account' --output text):rule/$RULE_NAME" 2>/dev/null || true
    
    print_success "Configured scheduled custom metrics collection (every 5 minutes)"
else
    print_warning "Lambda execution role not found. Skipping custom metrics Lambda function."
fi

# Create monitoring summary dashboard
print_status "Creating monitoring summary..."

DASHBOARD_URL="https://$AWS_REGION.console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=$DASHBOARD_NAME"

# Cleanup temporary files
rm -f /tmp/dashboard_config.json /tmp/custom_metrics.py /tmp/custom_metrics.zip

# Create summary report
cat > "monitoring_config_${ENVIRONMENT}.txt" << EOF
CloudWatch Monitoring Configuration Summary
==========================================
Environment: $ENVIRONMENT
Configuration Date: $(date)
AWS Region: $AWS_REGION

Dashboard: $DASHBOARD_NAME
URL: $DASHBOARD_URL

SNS Topic: $SNS_TOPIC_NAME
Topic ARN: $TOPIC_ARN

Log Groups Created:
$(printf '%s\n' "${LOG_GROUPS[@]}" | sed 's/^/  - /')

Auto Scaling Groups Monitored:
$(echo "$ASG_NAMES" | tr '\t' '\n' | sed 's/^/  - /')

Load Balancers Monitored:
$(echo "$ALB_ARNS" | tr '\t' '\n' | sed 's|.*/||' | sed 's/^/  - /')

Alarms Created:
  - High CPU utilization
  - High memory utilization
  - High disk utilization
  - Instance status check failures
  - Load balancer response time
  - HTTP error rates (4xx, 5xx)
  - Unhealthy target count
  - Cost monitoring

Custom Metrics:
  - User count
  - Active sessions
  - Deployment count

Lambda Functions:
$(if [[ -n "$LAMBDA_ROLE_ARN" ]]; then echo "  - $LAMBDA_FUNCTION_NAME"; fi)

Next Steps:
1. Configure SNS topic subscriptions (email, SMS, Slack)
2. Set up alarm notification escalation
3. Customize metric thresholds based on usage patterns
4. Implement log analysis and alerting
5. Set up cross-region monitoring (if needed)
6. Configure automated remediation workflows

Access your monitoring dashboard at:
$DASHBOARD_URL
EOF

print_success "CloudWatch monitoring setup completed for environment: $ENVIRONMENT"
print_status "Configuration summary saved to monitoring_config_${ENVIRONMENT}.txt"
print_status "Dashboard URL: $DASHBOARD_URL"