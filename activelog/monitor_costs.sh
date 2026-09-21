#!/bin/bash

# AWS Cost Monitor Script
# Tracks EC2 instance costs and alerts when daily cost exceeds $1

set -e

# Configuration
INSTANCE_ID="i-0441f20fed3415d4a"
COST_LOG_FILE="daily_costs.log"
DAILY_LIMIT=1.00

# t3.micro pricing in US West 2 (Oregon) - $0.0104 per hour
HOURLY_RATE=0.0104

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$COST_LOG_FILE"
}

# Function to check if instance is running
check_instance_state() {
    echo "Checking instance state..."
    
    # Get instance information
    INSTANCE_INFO=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --output json)
    
    # Extract state and launch time
    STATE=$(echo "$INSTANCE_INFO" | grep -A 2 '"State"' | grep '"Name"' | cut -d'"' -f4)
    LAUNCH_TIME=$(echo "$INSTANCE_INFO" | grep '"LaunchTime"' | cut -d'"' -f4)
    INSTANCE_TYPE=$(echo "$INSTANCE_INFO" | grep '"InstanceType"' | cut -d'"' -f4)
    
    echo "Instance ID: $INSTANCE_ID"
    echo "Instance Type: $INSTANCE_TYPE" 
    echo "State: $STATE"
    echo "Launch Time: $LAUNCH_TIME"
    echo ""
    
    if [ "$STATE" = "running" ]; then
        return 0
    else
        echo -e "${GREEN}✓ Instance is not running - no costs accruing${NC}"
        log_message "Instance $INSTANCE_ID is $STATE - no costs"
        return 1
    fi
}

# Function to calculate runtime costs for today
calculate_daily_cost() {
    if [ "$STATE" != "running" ]; then
        DAILY_COST=0.00
        return
    fi
    
    echo "Calculating daily costs..."
    
    # Get current time and start of today in UTC
    CURRENT_TIME=$(date -u '+%Y-%m-%d %H:%M:%S')
    TODAY_START=$(date -u -d 'today 00:00:00' '+%Y-%m-%d %H:%M:%S')
    
    # Convert launch time to comparable format
    LAUNCH_TIME_FORMATTED=$(date -u -d "$LAUNCH_TIME" '+%Y-%m-%d %H:%M:%S')
    
    # Determine the start time for cost calculation (either launch time or start of today, whichever is later)
    if [[ "$LAUNCH_TIME_FORMATTED" > "$TODAY_START" ]]; then
        COST_START_TIME="$LAUNCH_TIME_FORMATTED"
    else
        COST_START_TIME="$TODAY_START"
    fi
    
    # Calculate runtime in hours
    START_EPOCH=$(date -u -d "$COST_START_TIME" +%s)
    CURRENT_EPOCH=$(date -u +%s)
    RUNTIME_SECONDS=$((CURRENT_EPOCH - START_EPOCH))
    RUNTIME_HOURS=$(echo "scale=4; $RUNTIME_SECONDS / 3600" | bc -l)
    
    # Calculate cost
    DAILY_COST=$(echo "scale=4; $RUNTIME_HOURS * $HOURLY_RATE" | bc -l)
    
    echo "Runtime today: ${RUNTIME_HOURS} hours"
    echo "Hourly rate: \$${HOURLY_RATE}"
    echo "Daily cost so far: \$${DAILY_COST}"
    echo ""
}

# Function to check if cost exceeds limit and alert
check_cost_alert() {
    if [ "$STATE" != "running" ]; then
        return
    fi
    
    # Compare costs (using bc for floating point comparison)
    EXCEEDS=$(echo "$DAILY_COST > $DAILY_LIMIT" | bc -l)
    
    if [ "$EXCEEDS" -eq 1 ]; then
        echo -e "${RED}⚠️  ALERT: Daily cost (\$${DAILY_COST}) exceeds limit (\$${DAILY_LIMIT})!${NC}"
        echo ""
        echo -e "${YELLOW}To stop the instance and save costs, run:${NC}"
        echo "aws ec2 stop-instances --instance-ids $INSTANCE_ID"
        echo ""
        log_message "ALERT: Daily cost \$${DAILY_COST} exceeds limit \$${DAILY_LIMIT}"
    else
        echo -e "${GREEN}✓ Daily cost (\$${DAILY_COST}) is within limit (\$${DAILY_LIMIT})${NC}"
    fi
    echo ""
}

# Function to log daily costs
log_daily_cost() {
    DATE=$(date '+%Y-%m-%d')
    log_message "Date: $DATE, Instance: $INSTANCE_ID, State: $STATE, Daily Cost: \$${DAILY_COST:-0.00}"
}

# Function to show recent cost history
show_cost_history() {
    echo "Recent cost history:"
    if [ -f "$COST_LOG_FILE" ]; then
        tail -10 "$COST_LOG_FILE" | grep -E "(Daily Cost|ALERT)" || echo "No recent cost entries found"
    else
        echo "No cost log file found yet"
    fi
    echo ""
}

# Main execution
main() {
    echo "========================================="
    echo "        AWS EC2 Cost Monitor"
    echo "========================================="
    echo ""
    
    # Check if instance is running
    if ! check_instance_state; then
        log_daily_cost
        show_cost_history
        exit 0
    fi
    
    # Calculate daily costs
    calculate_daily_cost
    
    # Check for alerts
    check_cost_alert
    
    # Log the daily cost
    log_daily_cost
    
    # Show recent history
    show_cost_history
    
    echo "========================================="
    echo "Monitoring complete. Check $COST_LOG_FILE for historical data."
}

# Run main function
main "$@"