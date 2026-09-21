#!/bin/bash

set -e

ENVIRONMENT=${1:-beta}
DURATION=${2:-24}  # hours
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

print_status "Starting health monitoring for environment: $ENVIRONMENT"
print_status "Duration: $DURATION hours"

# Create monitoring log file
MONITOR_LOG="health_monitor_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S).log"

# Function to log with timestamp
log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$MONITOR_LOG"
}

# Function to check endpoint health
check_endpoint_health() {
    local endpoint=$1
    local expected_status=${2:-200}
    
    response=$(curl -s -o /dev/null -w "%{http_code},%{time_total},%{size_download}" "$endpoint" || echo "000,0,0")
    IFS=',' read -r status_code response_time size <<< "$response"
    
    if [[ "$status_code" == "$expected_status" ]]; then
        log_with_timestamp "✓ $endpoint - Status: $status_code, Time: ${response_time}s, Size: ${size}b"
        return 0
    else
        log_with_timestamp "✗ $endpoint - Status: $status_code, Time: ${response_time}s (Expected: $expected_status)"
        return 1
    fi
}

# Function to check AWS service health
check_aws_service_health() {
    local service=$1
    
    case $service in
        "ec2")
            instances=$(aws ec2 describe-instances \
                --filters "Name=tag:Environment,Values=$ENVIRONMENT" "Name=instance-state-name,Values=running" \
                --query "length(Reservations[].Instances[])" \
                --output text)
            log_with_timestamp "EC2 - Running instances: $instances"
            ;;
        "rds")
            db_instances=$(aws rds describe-db-instances \
                --query "length(DBInstances[?contains(DBInstanceIdentifier, '$ENVIRONMENT') && DBInstanceStatus=='available'])" \
                --output text 2>/dev/null || echo "0")
            log_with_timestamp "RDS - Available instances: $db_instances"
            ;;
        "alb")
            alb_count=$(aws elbv2 describe-load-balancers \
                --query "length(LoadBalancers[?contains(LoadBalancerName, '$ENVIRONMENT') && State.Code=='active'])" \
                --output text 2>/dev/null || echo "0")
            log_with_timestamp "ALB - Active load balancers: $alb_count"
            ;;
        "asg")
            asg_info=$(aws autoscaling describe-auto-scaling-groups \
                --query "AutoScalingGroups[?contains(Tags[?Key=='Environment'].Value, '$ENVIRONMENT')].{Name:AutoScalingGroupName,Desired:DesiredCapacity,Running:length(Instances[?LifecycleState=='InService'])}" \
                --output text | while read -r name desired running; do
                    echo "$name: $running/$desired"
                done)
            log_with_timestamp "ASG - Instance status:"
            echo "$asg_info" | while read -r line; do
                log_with_timestamp "  $line"
            done
            ;;
    esac
}

# Function to check CloudWatch alarms
check_cloudwatch_alarms() {
    local alarm_states=$(aws cloudwatch describe-alarms \
        --alarm-name-prefix "activelog" \
        --query "MetricAlarms[?contains(AlarmName, '$ENVIRONMENT')].{Name:AlarmName,State:StateValue}" \
        --output text)
    
    log_with_timestamp "CloudWatch Alarms Status:"
    
    alarm_count=0
    ok_count=0
    
    while read -r name state; do
        if [[ -n "$name" ]]; then
            ((alarm_count++))
            if [[ "$state" == "OK" ]]; then
                ((ok_count++))
                log_with_timestamp "  ✓ $name: $state"
            else
                log_with_timestamp "  ✗ $name: $state"
            fi
        fi
    done <<< "$alarm_states"
    
    log_with_timestamp "Alarm Summary: $ok_count/$alarm_count OK"
}

# Function to get system metrics
get_system_metrics() {
    log_with_timestamp "System Metrics (Last 5 minutes):"
    
    # CPU utilization
    cpu_avg=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/EC2 \
        --metric-name CPUUtilization \
        --start-time "$(date -u -d '5 minutes ago' --iso-8601)" \
        --end-time "$(date -u --iso-8601)" \
        --period 300 \
        --statistics Average \
        --query "Datapoints[0].Average" \
        --output text 2>/dev/null || echo "N/A")
    
    log_with_timestamp "  Average CPU Utilization: ${cpu_avg}%"
    
    # Request count
    request_count=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ApplicationELB \
        --metric-name RequestCount \
        --start-time "$(date -u -d '5 minutes ago' --iso-8601)" \
        --end-time "$(date -u --iso-8601)" \
        --period 300 \
        --statistics Sum \
        --query "Datapoints[0].Sum" \
        --output text 2>/dev/null || echo "N/A")
    
    log_with_timestamp "  Total Requests (5 min): $request_count"
    
    # Error rate
    error_count=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ApplicationELB \
        --metric-name HTTPCode_Target_5XX_Count \
        --start-time "$(date -u -d '5 minutes ago' --iso-8601)" \
        --end-time "$(date -u --iso-8601)" \
        --period 300 \
        --statistics Sum \
        --query "Datapoints[0].Sum" \
        --output text 2>/dev/null || echo "0")
    
    if [[ "$request_count" != "N/A" && "$request_count" -gt 0 ]]; then
        error_rate=$(echo "scale=2; $error_count * 100 / $request_count" | bc -l 2>/dev/null || echo "0")
        log_with_timestamp "  Error Rate: ${error_rate}%"
    else
        log_with_timestamp "  Error Rate: N/A"
    fi
}

# Function to run comprehensive health check
run_health_check() {
    log_with_timestamp "=== Health Check $(date) ==="
    
    # Get domain endpoints
    if [[ -f "deployment_outputs.json" ]]; then
        endpoints=$(jq -r '.domain_endpoints.value | to_entries[] | "https://\(.value)"' deployment_outputs.json 2>/dev/null || echo "")
    else
        # Fallback: try to get ALB DNS names
        endpoints=$(aws elbv2 describe-load-balancers \
            --query "LoadBalancers[?contains(LoadBalancerName, '$ENVIRONMENT')].DNSName" \
            --output text | tr '\t' '\n' | sed 's/^/http:\/\//' || echo "")
    fi
    
    # Check endpoints
    if [[ -n "$endpoints" ]]; then
        log_with_timestamp "Checking endpoints:"
        endpoint_failures=0
        endpoint_total=0
        
        echo "$endpoints" | while read -r endpoint; do
            if [[ -n "$endpoint" ]]; then
                ((endpoint_total++))
                if ! check_endpoint_health "$endpoint/health" 200; then
                    ((endpoint_failures++))
                fi
            fi
        done
    else
        log_with_timestamp "No endpoints found to check"
    fi
    
    # Check AWS services
    log_with_timestamp "Checking AWS services:"
    check_aws_service_health "ec2"
    check_aws_service_health "rds"
    check_aws_service_health "alb"
    check_aws_service_health "asg"
    
    # Check CloudWatch alarms
    check_cloudwatch_alarms
    
    # Get metrics
    get_system_metrics
    
    log_with_timestamp "=== End Health Check ==="
    echo
}

# Main monitoring loop
log_with_timestamp "Starting health monitoring for ActiveLog $ENVIRONMENT"
log_with_timestamp "Monitoring duration: $DURATION hours"
log_with_timestamp "Log file: $MONITOR_LOG"

start_time=$(date +%s)
end_time=$((start_time + DURATION * 3600))
check_interval=300  # 5 minutes

# Run initial health check
run_health_check

# Create summary variables
total_checks=1
failed_checks=0
last_alert_time=0

# Main monitoring loop
while [[ $(date +%s) -lt $end_time ]]; do
    sleep $check_interval
    
    ((total_checks++))
    
    # Run health check
    if ! run_health_check; then
        ((failed_checks++))
        
        # Send alert if needed (not more than once per hour)
        current_time=$(date +%s)
        if [[ $((current_time - last_alert_time)) -gt 3600 ]]; then
            log_with_timestamp "ALERT: Health check failures detected!"
            
            # Try to send SNS notification
            sns_topic_arn=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'activelog-alerts-$ENVIRONMENT')].TopicArn" --output text 2>/dev/null || echo "")
            
            if [[ -n "$sns_topic_arn" ]]; then
                aws sns publish \
                    --topic-arn "$sns_topic_arn" \
                    --message "ActiveLog $ENVIRONMENT health check failures detected. Check monitoring logs for details." \
                    --subject "ActiveLog Health Alert - $ENVIRONMENT" 2>/dev/null || \
                    log_with_timestamp "Failed to send SNS notification"
            fi
            
            last_alert_time=$current_time
        fi
    fi
    
    # Show progress
    elapsed_hours=$(echo "scale=1; ($(date +%s) - $start_time) / 3600" | bc -l)
    remaining_hours=$(echo "scale=1; ($end_time - $(date +%s)) / 3600" | bc -l)
    
    print_status "Monitoring progress: ${elapsed_hours}h elapsed, ${remaining_hours}h remaining (Check $total_checks)"
done

# Generate final report
log_with_timestamp "=== MONITORING SUMMARY ==="
log_with_timestamp "Environment: $ENVIRONMENT"
log_with_timestamp "Duration: $DURATION hours"
log_with_timestamp "Total health checks: $total_checks"
log_with_timestamp "Failed checks: $failed_checks"

success_rate=$(echo "scale=1; ($total_checks - $failed_checks) * 100 / $total_checks" | bc -l)
log_with_timestamp "Success rate: ${success_rate}%"

if [[ $failed_checks -eq 0 ]]; then
    log_with_timestamp "✓ All health checks passed!"
    print_success "Health monitoring completed successfully!"
elif [[ $failed_checks -lt $((total_checks / 10)) ]]; then
    log_with_timestamp "⚠ Minor issues detected (${failed_checks} failures)"
    print_warning "Health monitoring completed with minor issues"
else
    log_with_timestamp "✗ Significant issues detected (${failed_checks} failures)"
    print_error "Health monitoring completed with significant issues"
fi

# Create summary report file
SUMMARY_REPORT="health_summary_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S).txt"

cat > "$SUMMARY_REPORT" << EOF
ActiveLog Health Monitoring Summary
==================================
Environment: $ENVIRONMENT
Monitoring Period: $(date -d "@$start_time") to $(date -d "@$end_time")
Duration: $DURATION hours
AWS Region: $AWS_REGION

Results:
--------
Total Health Checks: $total_checks
Failed Checks: $failed_checks
Success Rate: ${success_rate}%

Status: $(if [[ $failed_checks -eq 0 ]]; then echo "HEALTHY"; elif [[ $failed_checks -lt $((total_checks / 10)) ]]; then echo "WARNING"; else echo "CRITICAL"; fi)

Detailed Log: $MONITOR_LOG

Recommendations:
---------------
$(if [[ $failed_checks -eq 0 ]]; then
    echo "✓ System is performing well"
    echo "✓ Consider this configuration for production"
    echo "✓ Monitor long-term trends"
elif [[ $failed_checks -lt $((total_checks / 10)) ]]; then
    echo "⚠ Review failed health checks in detailed log"
    echo "⚠ Check CloudWatch alarms and metrics"
    echo "⚠ Consider adjusting scaling policies"
else
    echo "✗ Immediate attention required"
    echo "✗ Review system configuration"
    echo "✗ Check resource constraints"
    echo "✗ Review error logs"
fi)

Next Steps:
----------
1. Review detailed monitoring log: $MONITOR_LOG
2. Analyze CloudWatch metrics and alarms
3. Check application logs for errors
4. Review auto-scaling behavior
5. Validate backup and recovery procedures
6. Optimize based on observed patterns

EOF

print_status "Health monitoring summary saved to: $SUMMARY_REPORT"
print_status "Detailed monitoring log saved to: $MONITOR_LOG"

# Exit with appropriate code
if [[ $failed_checks -eq 0 ]]; then
    exit 0
elif [[ $failed_checks -lt $((total_checks / 10)) ]]; then
    exit 1
else
    exit 2
fi