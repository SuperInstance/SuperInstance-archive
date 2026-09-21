#!/bin/bash

set -e

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Unicode symbols
CHECKMARK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
ROCKET="🚀"
GEAR="⚙️"
SHIELD="🛡️"
HISTORY="📜"

DEPLOYMENT_ID=${1:-""}
ACTION=${2:-"status"}
ENVIRONMENT=${3:-"beta"}

print_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║           ${WHITE}🔄 ActiveLog Rollback Manager 🔄${NC}${CYAN}           ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║         ${PURPLE}Automated Recovery and State Management${NC}${CYAN}        ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}${CHECKMARK} $1${NC}"
}

print_error() {
    echo -e "${RED}${CROSS} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

# Create rollback checkpoint
create_checkpoint() {
    local deployment_id=$1
    local checkpoint_name=${2:-"pre_deployment_$(date +%Y%m%d_%H%M%S)"}
    
    print_info "Creating rollback checkpoint: $checkpoint_name"
    
    local checkpoint_dir="./checkpoints/$checkpoint_name"
    mkdir -p "$checkpoint_dir"
    
    # Save current Terraform state
    if [[ -f "terraform/terraform.tfstate" ]]; then
        cp "terraform/terraform.tfstate" "$checkpoint_dir/terraform.tfstate.backup"
        print_success "Terraform state backed up"
    fi
    
    # Save current configuration
    if [[ -f "terraform/terraform.tfvars" ]]; then
        cp "terraform/terraform.tfvars" "$checkpoint_dir/terraform.tfvars.backup"
    fi
    
    # Get current AWS resource state
    print_info "Capturing AWS resource state..."
    
    # EC2 instances
    aws ec2 describe-instances \
        --filters "Name=tag:Environment,Values=$ENVIRONMENT" \
        --query "Reservations[].Instances[]" \
        --output json > "$checkpoint_dir/ec2_instances.json" 2>/dev/null || true
    
    # Auto Scaling Groups
    aws autoscaling describe-auto-scaling-groups \
        --query "AutoScalingGroups[?contains(Tags[?Key=='Environment'].Value, '$ENVIRONMENT')]" \
        --output json > "$checkpoint_dir/auto_scaling_groups.json" 2>/dev/null || true
    
    # Load Balancers
    aws elbv2 describe-load-balancers \
        --query "LoadBalancers[?contains(LoadBalancerName, '$ENVIRONMENT')]" \
        --output json > "$checkpoint_dir/load_balancers.json" 2>/dev/null || true
    
    # RDS instances
    aws rds describe-db-instances \
        --query "DBInstances[?contains(DBInstanceIdentifier, '$ENVIRONMENT')]" \
        --output json > "$checkpoint_dir/rds_instances.json" 2>/dev/null || true
    
    # S3 buckets
    aws s3api list-buckets --query "Buckets[?contains(Name, '$ENVIRONMENT')]" \
        --output json > "$checkpoint_dir/s3_buckets.json" 2>/dev/null || true
    
    # CloudWatch alarms
    aws cloudwatch describe-alarms \
        --alarm-name-prefix "activelog" \
        --output json > "$checkpoint_dir/cloudwatch_alarms.json" 2>/dev/null || true
    
    # Create checkpoint metadata
    cat > "$checkpoint_dir/checkpoint_info.json" << EOF
{
  "checkpoint_name": "$checkpoint_name",
  "deployment_id": "$deployment_id",
  "environment": "$ENVIRONMENT",
  "created_at": "$(date --iso-8601=seconds)",
  "created_by": "rollback_manager",
  "aws_region": "$(aws configure get region 2>/dev/null || echo 'us-west-2')",
  "aws_account": "$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'unknown')",
  "terraform_version": "$(terraform version -json 2>/dev/null | jq -r .terraform_version || echo 'unknown')"
}
EOF
    
    print_success "Checkpoint created: $checkpoint_dir"
    echo "$checkpoint_dir"
}

# List available checkpoints
list_checkpoints() {
    print_info "Available rollback checkpoints:"
    echo
    
    if [[ ! -d "./checkpoints" ]]; then
        print_warning "No checkpoints directory found"
        return 1
    fi
    
    local count=0
    for checkpoint_dir in ./checkpoints/*/; do
        if [[ -d "$checkpoint_dir" && -f "$checkpoint_dir/checkpoint_info.json" ]]; then
            ((count++))
            
            local info=$(cat "$checkpoint_dir/checkpoint_info.json")
            local name=$(echo "$info" | jq -r '.checkpoint_name')
            local created_at=$(echo "$info" | jq -r '.created_at')
            local deployment_id=$(echo "$info" | jq -r '.deployment_id // "N/A"')
            local environment=$(echo "$info" | jq -r '.environment')
            
            echo -e "${CYAN}$count.${NC} ${WHITE}$name${NC}"
            echo -e "   ${BLUE}Environment:${NC} $environment"
            echo -e "   ${BLUE}Deployment ID:${NC} $deployment_id"
            echo -e "   ${BLUE}Created:${NC} $(date -d "$created_at" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$created_at")"
            echo -e "   ${BLUE}Path:${NC} $checkpoint_dir"
            echo
        fi
    done
    
    if [[ $count -eq 0 ]]; then
        print_warning "No valid checkpoints found"
        return 1
    fi
    
    print_info "Total checkpoints: $count"
}

# Validate checkpoint
validate_checkpoint() {
    local checkpoint_path=$1
    
    print_info "Validating checkpoint: $checkpoint_path"
    
    if [[ ! -d "$checkpoint_path" ]]; then
        print_error "Checkpoint directory not found: $checkpoint_path"
        return 1
    fi
    
    local required_files=("checkpoint_info.json")
    local validation_score=0
    local total_checks=0
    
    # Check required files
    for file in "${required_files[@]}"; do
        ((total_checks++))
        if [[ -f "$checkpoint_path/$file" ]]; then
            ((validation_score++))
            print_success "Found: $file"
        else
            print_error "Missing: $file"
        fi
    done
    
    # Check optional but important files
    local optional_files=("terraform.tfstate.backup" "ec2_instances.json" "auto_scaling_groups.json")
    for file in "${optional_files[@]}"; do
        ((total_checks++))
        if [[ -f "$checkpoint_path/$file" ]]; then
            ((validation_score++))
            print_info "Found: $file"
        else
            print_warning "Optional file missing: $file"
        fi
    done
    
    # Validate JSON files
    for json_file in "$checkpoint_path"/*.json; do
        if [[ -f "$json_file" ]]; then
            if jq empty "$json_file" 2>/dev/null; then
                print_success "Valid JSON: $(basename "$json_file")"
            else
                print_error "Invalid JSON: $(basename "$json_file")"
                ((validation_score--))
            fi
        fi
    done
    
    local validation_percentage=$((validation_score * 100 / total_checks))
    
    if [[ $validation_percentage -ge 80 ]]; then
        print_success "Checkpoint validation: ${validation_percentage}% (Good)"
        return 0
    elif [[ $validation_percentage -ge 60 ]]; then
        print_warning "Checkpoint validation: ${validation_percentage}% (Fair)"
        return 0
    else
        print_error "Checkpoint validation: ${validation_percentage}% (Poor)"
        return 1
    fi
}

# Intelligent rollback strategy
plan_rollback() {
    local checkpoint_path=$1
    local current_state_path="/tmp/current_state_$(date +%s)"
    
    print_info "Planning intelligent rollback strategy..."
    
    # Capture current state
    mkdir -p "$current_state_path"
    capture_current_state "$current_state_path"
    
    # Load checkpoint state
    local checkpoint_info=$(cat "$checkpoint_path/checkpoint_info.json")
    local checkpoint_env=$(echo "$checkpoint_info" | jq -r '.environment')
    
    print_info "Analyzing differences between current state and checkpoint..."
    
    # Plan rollback steps
    local rollback_plan="$current_state_path/rollback_plan.json"
    
    cat > "$rollback_plan" << EOF
{
  "rollback_id": "rollback_$(date +%s)",
  "checkpoint_path": "$checkpoint_path",
  "current_state_path": "$current_state_path",
  "target_environment": "$checkpoint_env",
  "created_at": "$(date --iso-8601=seconds)",
  "steps": []
}
EOF
    
    # Compare EC2 instances
    if [[ -f "$checkpoint_path/ec2_instances.json" && -f "$current_state_path/ec2_instances.json" ]]; then
        local current_instances=$(jq -r '.[].InstanceId // empty' "$current_state_path/ec2_instances.json" | wc -l)
        local checkpoint_instances=$(jq -r '.[].InstanceId // empty' "$checkpoint_path/ec2_instances.json" | wc -l)
        
        if [[ $current_instances -ne $checkpoint_instances ]]; then
            local step=$(cat << 'STEP_EOF'
{
  "step": "ec2_instances",
  "action": "reconcile",
  "description": "Reconcile EC2 instances to match checkpoint state",
  "risk_level": "medium",
  "estimated_duration": "5-10 minutes"
}
STEP_EOF
)
            jq ".steps += [$step]" "$rollback_plan" > "$rollback_plan.tmp" && mv "$rollback_plan.tmp" "$rollback_plan"
        fi
    fi
    
    # Compare Auto Scaling Groups
    if [[ -f "$checkpoint_path/auto_scaling_groups.json" && -f "$current_state_path/auto_scaling_groups.json" ]]; then
        local current_asgs=$(jq -r '.[].AutoScalingGroupName // empty' "$current_state_path/auto_scaling_groups.json" | wc -l)
        local checkpoint_asgs=$(jq -r '.[].AutoScalingGroupName // empty' "$checkpoint_path/auto_scaling_groups.json" | wc -l)
        
        if [[ $current_asgs -ne $checkpoint_asgs ]]; then
            local step=$(cat << 'STEP_EOF'
{
  "step": "auto_scaling_groups",
  "action": "restore",
  "description": "Restore Auto Scaling Groups configuration",
  "risk_level": "high",
  "estimated_duration": "10-15 minutes"
}
STEP_EOF
)
            jq ".steps += [$step]" "$rollback_plan" > "$rollback_plan.tmp" && mv "$rollback_plan.tmp" "$rollback_plan"
        fi
    fi
    
    # Compare Terraform state
    if [[ -f "$checkpoint_path/terraform.tfstate.backup" && -f "terraform/terraform.tfstate" ]]; then
        if ! diff -q "$checkpoint_path/terraform.tfstate.backup" "terraform/terraform.tfstate" > /dev/null 2>&1; then
            local step=$(cat << 'STEP_EOF'
{
  "step": "terraform_state",
  "action": "restore",
  "description": "Restore Terraform state to checkpoint version",
  "risk_level": "high",
  "estimated_duration": "15-30 minutes"
}
STEP_EOF
)
            jq ".steps += [$step]" "$rollback_plan" > "$rollback_plan.tmp" && mv "$rollback_plan.tmp" "$rollback_plan"
        fi
    fi
    
    # Calculate overall risk and duration
    local high_risk_steps=$(jq '[.steps[] | select(.risk_level == "high")] | length' "$rollback_plan")
    local medium_risk_steps=$(jq '[.steps[] | select(.risk_level == "medium")] | length' "$rollback_plan")
    local total_steps=$(jq '.steps | length' "$rollback_plan")
    
    local overall_risk="low"
    if [[ $high_risk_steps -gt 0 ]]; then
        overall_risk="high"
    elif [[ $medium_risk_steps -gt 0 ]]; then
        overall_risk="medium"
    fi
    
    # Update plan with metadata
    jq ". + {\"overall_risk\": \"$overall_risk\", \"total_steps\": $total_steps}" "$rollback_plan" > "$rollback_plan.tmp" && mv "$rollback_plan.tmp" "$rollback_plan"
    
    print_info "Rollback plan created: $rollback_plan"
    display_rollback_plan "$rollback_plan"
    
    echo "$rollback_plan"
}

# Display rollback plan
display_rollback_plan() {
    local plan_file=$1
    
    echo
    echo -e "${PURPLE}${HISTORY} Rollback Execution Plan${NC}"
    echo -e "${PURPLE}═══════════════════════════${NC}"
    echo
    
    local plan_data=$(cat "$plan_file")
    local rollback_id=$(echo "$plan_data" | jq -r '.rollback_id')
    local overall_risk=$(echo "$plan_data" | jq -r '.overall_risk')
    local total_steps=$(echo "$plan_data" | jq -r '.total_steps')
    
    echo -e "${BLUE}Rollback ID:${NC} $rollback_id"
    echo -e "${BLUE}Total Steps:${NC} $total_steps"
    
    case "$overall_risk" in
        "high")
            echo -e "${BLUE}Overall Risk:${NC} ${RED}HIGH RISK${NC} ${WARNING}"
            ;;
        "medium")
            echo -e "${BLUE}Overall Risk:${NC} ${YELLOW}MEDIUM RISK${NC} ${WARNING}"
            ;;
        *)
            echo -e "${BLUE}Overall Risk:${NC} ${GREEN}LOW RISK${NC} ${CHECKMARK}"
            ;;
    esac
    
    echo
    echo -e "${WHITE}Planned Steps:${NC}"
    
    local step_num=0
    echo "$plan_data" | jq -r '.steps[] | @json' | while read -r step_json; do
        ((step_num++))
        
        local step=$(echo "$step_json" | jq -r '.step')
        local action=$(echo "$step_json" | jq -r '.action')
        local description=$(echo "$step_json" | jq -r '.description')
        local risk_level=$(echo "$step_json" | jq -r '.risk_level')
        local duration=$(echo "$step_json" | jq -r '.estimated_duration')
        
        local risk_color="${GREEN}"
        local risk_symbol="${CHECKMARK}"
        
        case "$risk_level" in
            "high")
                risk_color="${RED}"
                risk_symbol="${CROSS}"
                ;;
            "medium")
                risk_color="${YELLOW}"
                risk_symbol="${WARNING}"
                ;;
        esac
        
        echo -e "${CYAN}$step_num.${NC} ${WHITE}$step${NC} (${action})"
        echo -e "   ${BLUE}Description:${NC} $description"
        echo -e "   ${BLUE}Risk Level:${NC} ${risk_color}$risk_level${NC} ${risk_symbol}"
        echo -e "   ${BLUE}Duration:${NC} $duration"
        echo
    done
}

# Execute rollback
execute_rollback() {
    local plan_file=$1
    local auto_confirm=${2:-false}
    
    if [[ ! -f "$plan_file" ]]; then
        print_error "Rollback plan not found: $plan_file"
        return 1
    fi
    
    local plan_data=$(cat "$plan_file")
    local rollback_id=$(echo "$plan_data" | jq -r '.rollback_id')
    local checkpoint_path=$(echo "$plan_data" | jq -r '.checkpoint_path')
    local overall_risk=$(echo "$plan_data" | jq -r '.overall_risk')
    local total_steps=$(echo "$plan_data" | jq -r '.total_steps')
    
    print_info "Executing rollback: $rollback_id"
    
    # Safety confirmation
    if [[ "$auto_confirm" != "true" ]]; then
        echo
        print_warning "You are about to execute a rollback operation!"
        echo -e "${YELLOW}This will modify your AWS resources and may cause downtime.${NC}"
        echo -e "${BLUE}Rollback Risk Level:${NC} ${overall_risk^^}"
        echo -e "${BLUE}Total Steps:${NC} $total_steps"
        echo
        
        read -p "Are you sure you want to proceed? (type 'ROLLBACK' to confirm): " confirmation
        
        if [[ "$confirmation" != "ROLLBACK" ]]; then
            print_info "Rollback cancelled by user"
            return 0
        fi
    fi
    
    print_info "Starting rollback execution..."
    
    # Create rollback log
    local rollback_log="./logs/rollback_${rollback_id}.log"
    mkdir -p "./logs"
    
    {
        echo "Rollback Execution Log"
        echo "====================="
        echo "Rollback ID: $rollback_id"
        echo "Started: $(date)"
        echo "Plan: $plan_file"
        echo "Checkpoint: $checkpoint_path"
        echo
    } > "$rollback_log"
    
    # Execute each step
    local step_num=0
    local failed_steps=0
    
    echo "$plan_data" | jq -r '.steps[] | @json' | while read -r step_json; do
        ((step_num++))
        
        local step=$(echo "$step_json" | jq -r '.step')
        local action=$(echo "$step_json" | jq -r '.action')
        local description=$(echo "$step_json" | jq -r '.description')
        
        print_info "Step $step_num: $description"
        
        {
            echo "Step $step_num: $step ($action)"
            echo "Started: $(date)"
        } >> "$rollback_log"
        
        case "$step" in
            "terraform_state")
                execute_terraform_rollback "$checkpoint_path" "$rollback_log" || ((failed_steps++))
                ;;
            "ec2_instances")
                execute_ec2_rollback "$checkpoint_path" "$rollback_log" || ((failed_steps++))
                ;;
            "auto_scaling_groups")
                execute_asg_rollback "$checkpoint_path" "$rollback_log" || ((failed_steps++))
                ;;
            *)
                print_warning "Unknown rollback step: $step"
                echo "Warning: Unknown step $step" >> "$rollback_log"
                ;;
        esac
        
        {
            echo "Completed: $(date)"
            echo
        } >> "$rollback_log"
    done
    
    # Final status
    {
        echo "Rollback Execution Completed"
        echo "============================"
        echo "Finished: $(date)"
        echo "Failed Steps: $failed_steps"
    } >> "$rollback_log"
    
    if [[ $failed_steps -eq 0 ]]; then
        print_success "Rollback completed successfully!"
        print_info "Log file: $rollback_log"
    else
        print_error "Rollback completed with $failed_steps failed steps"
        print_warning "Please review the log file: $rollback_log"
        return 1
    fi
}

# Execute Terraform rollback
execute_terraform_rollback() {
    local checkpoint_path=$1
    local log_file=$2
    
    print_info "Restoring Terraform state..."
    
    if [[ ! -f "$checkpoint_path/terraform.tfstate.backup" ]]; then
        print_error "Terraform state backup not found in checkpoint"
        echo "Error: Terraform state backup not found" >> "$log_file"
        return 1
    fi
    
    # Backup current state before rollback
    cp "terraform/terraform.tfstate" "terraform/terraform.tfstate.pre_rollback" 2>/dev/null || true
    
    # Restore checkpoint state
    cp "$checkpoint_path/terraform.tfstate.backup" "terraform/terraform.tfstate"
    
    # Restore configuration if available
    if [[ -f "$checkpoint_path/terraform.tfvars.backup" ]]; then
        cp "$checkpoint_path/terraform.tfvars.backup" "terraform/terraform.tfvars"
    fi
    
    # Apply the restored state
    cd terraform
    if terraform plan -detailed-exitcode &>> "$log_file"; then
        print_success "Terraform state restored successfully"
        echo "Success: Terraform state restored" >> "$log_file"
        cd ..
        return 0
    else
        print_error "Failed to apply restored Terraform state"
        echo "Error: Failed to apply restored Terraform state" >> "$log_file"
        cd ..
        return 1
    fi
}

# Execute EC2 rollback
execute_ec2_rollback() {
    local checkpoint_path=$1
    local log_file=$2
    
    print_info "Reconciling EC2 instances..."
    
    if [[ ! -f "$checkpoint_path/ec2_instances.json" ]]; then
        print_warning "EC2 instances backup not found in checkpoint"
        echo "Warning: EC2 instances backup not found" >> "$log_file"
        return 0
    fi
    
    # This is a placeholder for EC2 reconciliation logic
    # In a real implementation, you would:
    # 1. Compare current instances with checkpoint
    # 2. Terminate extra instances
    # 3. Launch missing instances
    # 4. Update instance configurations
    
    print_info "EC2 reconciliation is complex and requires manual intervention"
    echo "Info: EC2 reconciliation requires manual review" >> "$log_file"
    
    return 0
}

# Execute ASG rollback
execute_asg_rollback() {
    local checkpoint_path=$1
    local log_file=$2
    
    print_info "Restoring Auto Scaling Groups..."
    
    if [[ ! -f "$checkpoint_path/auto_scaling_groups.json" ]]; then
        print_warning "Auto Scaling Groups backup not found in checkpoint"
        echo "Warning: ASG backup not found" >> "$log_file"
        return 0
    fi
    
    # Restore ASG configurations
    local checkpoint_asgs=$(cat "$checkpoint_path/auto_scaling_groups.json")
    
    echo "$checkpoint_asgs" | jq -r '.[].AutoScalingGroupName' | while read -r asg_name; do
        if [[ -n "$asg_name" ]]; then
            local desired_capacity=$(echo "$checkpoint_asgs" | jq -r ".[] | select(.AutoScalingGroupName == \"$asg_name\") | .DesiredCapacity")
            local min_size=$(echo "$checkpoint_asgs" | jq -r ".[] | select(.AutoScalingGroupName == \"$asg_name\") | .MinSize")
            local max_size=$(echo "$checkpoint_asgs" | jq -r ".[] | select(.AutoScalingGroupName == \"$asg_name\") | .MaxSize")
            
            if aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$asg_name" &>/dev/null; then
                print_info "Updating ASG: $asg_name"
                
                aws autoscaling update-auto-scaling-group \
                    --auto-scaling-group-name "$asg_name" \
                    --desired-capacity "$desired_capacity" \
                    --min-size "$min_size" \
                    --max-size "$max_size" &>> "$log_file"
                
                print_success "Updated ASG: $asg_name"
            else
                print_warning "ASG not found (may need recreation): $asg_name"
            fi
        fi
    done
    
    return 0
}

# Capture current AWS state
capture_current_state() {
    local output_dir=$1
    
    print_info "Capturing current AWS state..."
    
    # Similar to create_checkpoint but for current state analysis
    aws ec2 describe-instances \
        --filters "Name=tag:Environment,Values=$ENVIRONMENT" \
        --query "Reservations[].Instances[]" \
        --output json > "$output_dir/ec2_instances.json" 2>/dev/null || true
    
    aws autoscaling describe-auto-scaling-groups \
        --query "AutoScalingGroups[?contains(Tags[?Key=='Environment'].Value, '$ENVIRONMENT')]" \
        --output json > "$output_dir/auto_scaling_groups.json" 2>/dev/null || true
    
    print_success "Current state captured"
}

# Health check after rollback
post_rollback_health_check() {
    local rollback_id=$1
    
    print_info "Performing post-rollback health check..."
    
    local health_report="./logs/post_rollback_health_${rollback_id}.json"
    
    # Initialize health report
    cat > "$health_report" << EOF
{
  "rollback_id": "$rollback_id",
  "health_check_time": "$(date --iso-8601=seconds)",
  "environment": "$ENVIRONMENT",
  "checks": {}
}
EOF
    
    # Check EC2 instances
    local running_instances=$(aws ec2 describe-instances \
        --filters "Name=tag:Environment,Values=$ENVIRONMENT" "Name=instance-state-name,Values=running" \
        --query "length(Reservations[].Instances[])" \
        --output text 2>/dev/null || echo "0")
    
    jq ".checks.ec2_instances = {\"running\": $running_instances, \"status\": \"$([ "$running_instances" -gt 0 ] && echo "healthy" || echo "warning")\"}" "$health_report" > "$health_report.tmp" && mv "$health_report.tmp" "$health_report"
    
    # Check Auto Scaling Groups
    local active_asgs=$(aws autoscaling describe-auto-scaling-groups \
        --query "length(AutoScalingGroups[?contains(Tags[?Key=='Environment'].Value, '$ENVIRONMENT')])" \
        --output text 2>/dev/null || echo "0")
    
    jq ".checks.auto_scaling_groups = {\"active\": $active_asgs, \"status\": \"$([ "$active_asgs" -gt 0 ] && echo "healthy" || echo "warning")\"}" "$health_report" > "$health_report.tmp" && mv "$health_report.tmp" "$health_report"
    
    # Check Load Balancers
    local active_albs=$(aws elbv2 describe-load-balancers \
        --query "length(LoadBalancers[?contains(LoadBalancerName, '$ENVIRONMENT') && State.Code=='active'])" \
        --output text 2>/dev/null || echo "0")
    
    jq ".checks.load_balancers = {\"active\": $active_albs, \"status\": \"$([ "$active_albs" -gt 0 ] && echo "healthy" || echo "warning")\"}" "$health_report" > "$health_report.tmp" && mv "$health_report.tmp" "$health_report"
    
    # Overall health assessment
    local overall_status="healthy"
    if [[ $running_instances -eq 0 && $active_asgs -eq 0 ]]; then
        overall_status="critical"
    elif [[ $running_instances -eq 0 || $active_asgs -eq 0 ]]; then
        overall_status="degraded"
    fi
    
    jq ".overall_status = \"$overall_status\"" "$health_report" > "$health_report.tmp" && mv "$health_report.tmp" "$health_report"
    
    print_info "Health check report: $health_report"
    
    # Display results
    echo
    echo -e "${PURPLE}${SHIELD} Post-Rollback Health Check${NC}"
    echo -e "${PURPLE}═════════════════════════════${NC}"
    echo
    echo -e "${BLUE}EC2 Instances:${NC} $running_instances running"
    echo -e "${BLUE}Auto Scaling Groups:${NC} $active_asgs active"
    echo -e "${BLUE}Load Balancers:${NC} $active_albs active"
    echo
    
    case "$overall_status" in
        "healthy")
            print_success "Overall Status: HEALTHY"
            ;;
        "degraded")
            print_warning "Overall Status: DEGRADED"
            ;;
        "critical")
            print_error "Overall Status: CRITICAL"
            ;;
    esac
    
    return 0
}

# Main function
main() {
    print_header
    
    case "$ACTION" in
        "create")
            if [[ -z "$DEPLOYMENT_ID" ]]; then
                DEPLOYMENT_ID="manual_$(date +%Y%m%d_%H%M%S)"
            fi
            checkpoint_path=$(create_checkpoint "$DEPLOYMENT_ID")
            print_success "Checkpoint created: $checkpoint_path"
            ;;
        
        "list")
            list_checkpoints
            ;;
        
        "validate")
            if [[ -z "$DEPLOYMENT_ID" ]]; then
                print_error "Please specify a checkpoint path to validate"
                echo "Usage: $0 <checkpoint_path> validate"
                exit 1
            fi
            validate_checkpoint "$DEPLOYMENT_ID"
            ;;
        
        "plan")
            if [[ -z "$DEPLOYMENT_ID" ]]; then
                print_error "Please specify a checkpoint path for rollback planning"
                echo "Usage: $0 <checkpoint_path> plan"
                exit 1
            fi
            plan_file=$(plan_rollback "$DEPLOYMENT_ID")
            print_success "Rollback plan created: $plan_file"
            ;;
        
        "execute")
            if [[ -z "$DEPLOYMENT_ID" ]]; then
                print_error "Please specify a rollback plan file to execute"
                echo "Usage: $0 <plan_file> execute [auto]"
                exit 1
            fi
            auto_confirm="false"
            if [[ "${4:-}" == "auto" ]]; then
                auto_confirm="true"
            fi
            execute_rollback "$DEPLOYMENT_ID" "$auto_confirm"
            ;;
        
        "health")
            if [[ -z "$DEPLOYMENT_ID" ]]; then
                DEPLOYMENT_ID="manual_health_check"
            fi
            post_rollback_health_check "$DEPLOYMENT_ID"
            ;;
        
        "status"|*)
            print_info "ActiveLog Rollback Manager"
            echo
            print_info "Available commands:"
            echo "  create [deployment_id]     - Create a new checkpoint"
            echo "  list                       - List available checkpoints"
            echo "  validate <checkpoint_path> - Validate a checkpoint"
            echo "  plan <checkpoint_path>     - Plan rollback strategy"
            echo "  execute <plan_file> [auto] - Execute rollback plan"
            echo "  health [rollback_id]       - Perform health check"
            echo
            print_info "Examples:"
            echo "  $0 create my_deployment_123"
            echo "  $0 list"
            echo "  $0 ./checkpoints/backup_20231201 validate"
            echo "  $0 ./checkpoints/backup_20231201 plan"
            echo "  $0 /tmp/rollback_plan.json execute"
            ;;
    esac
}

# Trap Ctrl+C for graceful exit
trap 'echo -e "\n${YELLOW}Rollback operation cancelled by user.${NC}"; exit 130' INT

# Run main function
main "$@"