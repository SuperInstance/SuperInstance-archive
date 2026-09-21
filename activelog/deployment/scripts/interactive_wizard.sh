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
BOLD='\033[1m'

# Unicode symbols for better UX
CHECKMARK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
ROCKET="🚀"
GEAR="⚙️"
MONEY="💰"
CLOCK="⏰"
SHIELD="🛡️"

clear

print_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║              ${WHITE}${BOLD}🌟 ActiveLog Deployment Wizard 🌟${NC}${CYAN}              ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║           ${PURPLE}Interactive Setup for Your Ecosystem${NC}${CYAN}             ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

print_step() {
    local step_num=$1
    local total_steps=$2
    local title=$3
    echo -e "${BLUE}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│ ${WHITE}Step $step_num/$total_steps: $title${NC}${BLUE}$(printf "%*s" $((53 - ${#title} - ${#step_num} - ${#total_steps})) "")│${NC}"
    echo -e "${BLUE}└─────────────────────────────────────────────────────────────┘${NC}"
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

print_progress_bar() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r${CYAN}Progress: ["
    printf "%*s" $filled | tr ' ' '█'
    printf "%*s" $empty | tr ' ' '░'
    printf "] %d%% (%d/%d)${NC}" $percentage $current $total
}

ask_question() {
    local question=$1
    local default=$2
    local response
    
    if [[ -n "$default" ]]; then
        echo -e "${WHITE}❓ $question ${CYAN}[default: $default]${NC}"
        read -r response
        echo "${response:-$default}"
    else
        echo -e "${WHITE}❓ $question${NC}"
        read -r response
        echo "$response"
    fi
}

ask_yes_no() {
    local question=$1
    local default=${2:-"n"}
    local response
    
    while true; do
        if [[ "$default" == "y" ]]; then
            response=$(ask_question "$question (y/N)" "y")
        else
            response=$(ask_question "$question (y/N)" "n")
        fi
        
        case ${response,,} in
            y|yes) return 0 ;;
            n|no) return 1 ;;
            *) echo -e "${RED}Please answer yes (y) or no (n)${NC}" ;;
        esac
    done
}

select_from_list() {
    local prompt=$1
    shift
    local options=("$@")
    
    echo -e "${WHITE}$prompt${NC}"
    echo
    
    for i in "${!options[@]}"; do
        echo -e "${CYAN}  $((i+1))) ${options[$i]}${NC}"
    done
    echo
    
    while true; do
        read -p "Select option (1-${#options[@]}): " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            echo "${options[$((choice-1))]}"
            return
        else
            echo -e "${RED}Invalid selection. Please choose 1-${#options[@]}${NC}"
        fi
    done
}

animate_thinking() {
    local message=$1
    local duration=${2:-3}
    local chars="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    
    for ((i=0; i<duration*4; i++)); do
        printf "\r${BLUE}${chars:$((i%10)):1} $message...${NC}"
        sleep 0.25
    done
    printf "\r${GREEN}${CHECKMARK} $message... Done!${NC}\n"
}

check_prerequisites() {
    print_step 1 8 "Prerequisites Check"
    
    local checks=(
        "aws:AWS CLI"
        "terraform:Terraform"
        "docker:Docker"
        "jq:JQ JSON processor"
        "curl:CURL"
        "git:Git"
    )
    
    local all_good=true
    
    for check in "${checks[@]}"; do
        IFS=':' read -r cmd name <<< "$check"
        
        printf "%-30s" "Checking $name..."
        if command -v "$cmd" &> /dev/null; then
            echo -e "${GREEN}${CHECKMARK}${NC}"
        else
            echo -e "${RED}${CROSS}${NC}"
            all_good=false
        fi
    done
    
    echo
    
    if [[ "$all_good" == "true" ]]; then
        print_success "All prerequisites are installed!"
    else
        print_error "Some prerequisites are missing. Please install them before continuing."
        echo
        print_info "Installation guides:"
        echo "  AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        echo "  Terraform: https://learn.hashicorp.com/tutorials/terraform/install-cli"
        echo "  Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check AWS credentials
    printf "%-30s" "Checking AWS credentials..."
    if aws sts get-caller-identity &> /dev/null; then
        echo -e "${GREEN}${CHECKMARK}${NC}"
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
        AWS_USER_ARN=$(aws sts get-caller-identity --query 'Arn' --output text)
        print_info "Connected as: $(echo "$AWS_USER_ARN" | cut -d'/' -f2) in account $AWS_ACCOUNT_ID"
    else
        echo -e "${RED}${CROSS}${NC}"
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    echo
}

gather_deployment_preferences() {
    print_step 2 8 "Deployment Configuration"
    
    echo -e "${WHITE}${BOLD}Let's configure your ActiveLog deployment!${NC}"
    echo
    
    # Environment selection
    ENVIRONMENT=$(select_from_list "Select deployment environment:" \
        "Development (dev) - Minimal resources, frequent changes" \
        "Beta (beta) - Testing with realistic load" \
        "Staging (staging) - Pre-production validation" \
        "Production (production) - Live environment")
    
    case "$ENVIRONMENT" in
        "Development"*) ENVIRONMENT="dev" ;;
        "Beta"*) ENVIRONMENT="beta" ;;
        "Staging"*) ENVIRONMENT="staging" ;;
        "Production"*) ENVIRONMENT="production" ;;
    esac
    
    echo
    print_info "Selected environment: $ENVIRONMENT"
    
    # Region selection
    AWS_REGION=$(select_from_list "Select AWS region:" \
        "US West (Oregon) - us-west-2" \
        "US East (N. Virginia) - us-east-1" \
        "US East (Ohio) - us-east-2" \
        "Europe (Ireland) - eu-west-1" \
        "Asia Pacific (Tokyo) - ap-northeast-1" \
        "Custom - I'll specify")
    
    case "$AWS_REGION" in
        "US West"*) AWS_REGION="us-west-2" ;;
        "US East (N. Virginia)"*) AWS_REGION="us-east-1" ;;
        "US East (Ohio)"*) AWS_REGION="us-east-2" ;;
        "Europe"*) AWS_REGION="eu-west-1" ;;
        "Asia Pacific"*) AWS_REGION="ap-northeast-1" ;;
        "Custom"*) AWS_REGION=$(ask_question "Enter AWS region code (e.g., us-west-2)") ;;
    esac
    
    echo
    print_info "Selected region: $AWS_REGION"
    
    # Cost optimization preference
    if ask_yes_no "${MONEY} Enable cost optimization features?" "y"; then
        COST_OPTIMIZED="true"
        print_success "Cost optimization enabled - resources will scale down during off-hours"
    else
        COST_OPTIMIZED="false"
        print_info "Cost optimization disabled - resources will maintain steady state"
    fi
    
    echo
}

select_domains() {
    print_step 3 8 "Domain Selection"
    
    echo -e "${WHITE}${BOLD}Choose which ActiveLog domains to deploy:${NC}"
    echo
    
    local available_domains=(
        "DMLog:D&D Campaign Management:Advanced RPG tools with AI DM assistance"
        "PersonalLog:Personal Productivity:Life tracking and goal management"
        "BusinessLog:Business Intelligence:Analytics and reporting platform"
        "FishingLog:Fishing Companion:Trip logging and marine data"
        "StudyLog:Educational Gamification:Learning progress with achievements"
        "MakerLog:Developer Productivity:Project tracking and automation"
    )
    
    SELECTED_DOMAINS=()
    
    for domain_info in "${available_domains[@]}"; do
        IFS=':' read -r domain_name domain_title domain_desc <<< "$domain_info"
        
        echo -e "${CYAN}${BOLD}$domain_name${NC} - ${WHITE}$domain_title${NC}"
        echo -e "  ${PURPLE}$domain_desc${NC}"
        
        if ask_yes_no "  Deploy $domain_name?" "n"; then
            SELECTED_DOMAINS+=("$domain_name")
            print_success "Added $domain_name to deployment"
        fi
        echo
    done
    
    if [[ ${#SELECTED_DOMAINS[@]} -eq 0 ]]; then
        print_warning "No domains selected. Selecting DMLog as default."
        SELECTED_DOMAINS=("DMLog")
    fi
    
    echo -e "${GREEN}${BOLD}Selected domains:${NC}"
    for domain in "${SELECTED_DOMAINS[@]}"; do
        echo -e "  ${CHECKMARK} $domain"
    done
    echo
}

configure_resources() {
    print_step 4 8 "Resource Configuration"
    
    echo -e "${WHITE}${BOLD}Configure computing resources:${NC}"
    echo
    
    # Resource sizing
    RESOURCE_SIZE=$(select_from_list "Select resource sizing strategy:" \
        "Minimal - Cost-effective, suitable for testing (t3.micro/small)" \
        "Balanced - Good performance-to-cost ratio (t3.small/medium)" \
        "Performance - Optimized for high load (t3.large/c5.large)" \
        "High Performance - Maximum performance (c5.xlarge/m5.xlarge)")
    
    case "$RESOURCE_SIZE" in
        "Minimal"*) INSTANCE_CLASS="minimal" ;;
        "Balanced"*) INSTANCE_CLASS="balanced" ;;
        "Performance"*) INSTANCE_CLASS="performance" ;;
        "High Performance"*) INSTANCE_CLASS="high_performance" ;;
    esac
    
    # GPU for DMLog
    ENABLE_GPU="false"
    if [[ " ${SELECTED_DOMAINS[*]} " =~ " DMLog " ]]; then
        if ask_yes_no "${GEAR} Enable GPU instances for DMLog AI features?" "n"; then
            ENABLE_GPU="true"
            print_warning "GPU instances are more expensive but provide better AI performance"
        fi
    fi
    
    # Auto-scaling configuration
    if ask_yes_no "${ROCKET} Enable intelligent auto-scaling?" "y"; then
        AUTO_SCALING="true"
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            MIN_INSTANCES=$(ask_question "Minimum instances per domain" "2")
            MAX_INSTANCES=$(ask_question "Maximum instances per domain" "10")
        else
            MIN_INSTANCES=$(ask_question "Minimum instances per domain" "1")
            MAX_INSTANCES=$(ask_question "Maximum instances per domain" "5")
        fi
    else
        AUTO_SCALING="false"
        MIN_INSTANCES="1"
        MAX_INSTANCES="1"
    fi
    
    echo
    print_info "Resource configuration:"
    echo -e "  Instance Class: ${CYAN}$INSTANCE_CLASS${NC}"
    echo -e "  GPU Enabled: ${CYAN}$ENABLE_GPU${NC}"
    echo -e "  Auto-scaling: ${CYAN}$AUTO_SCALING${NC}"
    if [[ "$AUTO_SCALING" == "true" ]]; then
        echo -e "  Instance Range: ${CYAN}$MIN_INSTANCES - $MAX_INSTANCES${NC}"
    fi
    echo
}

configure_monitoring() {
    print_step 5 8 "Monitoring & Alerting"
    
    echo -e "${WHITE}${BOLD}Configure monitoring and alerting:${NC}"
    echo
    
    # Monitoring level
    MONITORING_LEVEL=$(select_from_list "Select monitoring intensity:" \
        "Basic - Essential metrics only" \
        "Standard - Comprehensive monitoring" \
        "Advanced - Detailed metrics with custom dashboards" \
        "Enterprise - Full observability with AI insights")
    
    case "$MONITORING_LEVEL" in
        "Basic"*) MONITORING="basic" ;;
        "Standard"*) MONITORING="standard" ;;
        "Advanced"*) MONITORING="advanced" ;;
        "Enterprise"*) MONITORING="enterprise" ;;
    esac
    
    # Notification preferences
    if ask_yes_no "${INFO} Set up alert notifications?" "y"; then
        ENABLE_ALERTS="true"
        
        # Email notification
        if ask_yes_no "  Enable email alerts?" "y"; then
            ALERT_EMAIL=$(ask_question "  Enter email address for alerts")
        fi
        
        # Slack integration
        if ask_yes_no "  Enable Slack notifications?" "n"; then
            SLACK_WEBHOOK=$(ask_question "  Enter Slack webhook URL")
        fi
        
        # SMS alerts for critical issues
        if ask_yes_no "  Enable SMS alerts for critical issues?" "n"; then
            ALERT_PHONE=$(ask_question "  Enter phone number (+1234567890)")
        fi
    else
        ENABLE_ALERTS="false"
    fi
    
    echo
    print_info "Monitoring configuration:"
    echo -e "  Level: ${CYAN}$MONITORING${NC}"
    echo -e "  Alerts: ${CYAN}$ENABLE_ALERTS${NC}"
    if [[ -n "$ALERT_EMAIL" ]]; then
        echo -e "  Email: ${CYAN}$ALERT_EMAIL${NC}"
    fi
    echo
}

configure_backup() {
    print_step 6 8 "Backup & Disaster Recovery"
    
    echo -e "${WHITE}${BOLD}Configure backup and disaster recovery:${NC}"
    echo
    
    # Backup strategy
    BACKUP_STRATEGY=$(select_from_list "Select backup strategy:" \
        "Basic - Daily backups, 7-day retention" \
        "Standard - Daily + weekly backups, 30-day retention" \
        "Advanced - Multiple schedules, 90-day retention" \
        "Enterprise - Continuous backup, 1-year retention")
    
    case "$BACKUP_STRATEGY" in
        "Basic"*) BACKUP_RETENTION="7"; BACKUP_FREQUENCY="daily" ;;
        "Standard"*) BACKUP_RETENTION="30"; BACKUP_FREQUENCY="daily_weekly" ;;
        "Advanced"*) BACKUP_RETENTION="90"; BACKUP_FREQUENCY="comprehensive" ;;
        "Enterprise"*) BACKUP_RETENTION="365"; BACKUP_FREQUENCY="continuous" ;;
    esac
    
    # Cross-region backup
    if ask_yes_no "${SHIELD} Enable cross-region disaster recovery?" "y"; then
        CROSS_REGION_BACKUP="true"
        
        # Select backup region
        BACKUP_REGION=$(select_from_list "Select backup region:" \
            "US East (N. Virginia) - us-east-1" \
            "US West (Oregon) - us-west-2" \
            "Europe (Ireland) - eu-west-1" \
            "Asia Pacific (Tokyo) - ap-northeast-1")
        
        case "$BACKUP_REGION" in
            "US East"*) BACKUP_REGION="us-east-1" ;;
            "US West"*) BACKUP_REGION="us-west-2" ;;
            "Europe"*) BACKUP_REGION="eu-west-1" ;;
            "Asia Pacific"*) BACKUP_REGION="ap-northeast-1" ;;
        esac
    else
        CROSS_REGION_BACKUP="false"
        BACKUP_REGION=""
    fi
    
    echo
    print_info "Backup configuration:"
    echo -e "  Strategy: ${CYAN}$BACKUP_STRATEGY${NC}"
    echo -e "  Retention: ${CYAN}$BACKUP_RETENTION days${NC}"
    if [[ "$CROSS_REGION_BACKUP" == "true" ]]; then
        echo -e "  Disaster Recovery: ${CYAN}$BACKUP_REGION${NC}"
    fi
    echo
}

estimate_costs() {
    print_step 7 8 "Cost Estimation"
    
    echo -e "${WHITE}${BOLD}${MONEY} Estimating deployment costs...${NC}"
    echo
    
    animate_thinking "Calculating resource costs" 2
    
    # Simple cost estimation based on configuration
    local base_cost=0
    local domain_count=${#SELECTED_DOMAINS[@]}
    
    case "$INSTANCE_CLASS" in
        "minimal") base_cost=$((domain_count * 20)) ;;
        "balanced") base_cost=$((domain_count * 50)) ;;
        "performance") base_cost=$((domain_count * 100)) ;;
        "high_performance") base_cost=$((domain_count * 200)) ;;
    esac
    
    # GPU surcharge
    if [[ "$ENABLE_GPU" == "true" ]]; then
        base_cost=$((base_cost + 150))
    fi
    
    # Auto-scaling multiplier
    if [[ "$AUTO_SCALING" == "true" ]]; then
        base_cost=$((base_cost * MAX_INSTANCES / 2))
    fi
    
    # Environment multiplier
    case "$ENVIRONMENT" in
        "dev") base_cost=$((base_cost / 2)) ;;
        "staging") base_cost=$((base_cost * 3 / 4)) ;;
        "production") base_cost=$((base_cost * 5 / 4)) ;;
    esac
    
    # Cost optimization discount
    if [[ "$COST_OPTIMIZED" == "true" ]]; then
        base_cost=$((base_cost * 3 / 4))
    fi
    
    local monthly_cost=$base_cost
    local yearly_cost=$((monthly_cost * 12 * 9 / 10))  # 10% discount for annual
    
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                  ║${NC}"
    echo -e "${CYAN}║              ${WHITE}${BOLD}💰 Cost Estimation${NC}${CYAN}                ║${NC}"
    echo -e "${CYAN}║                                                  ║${NC}"
    echo -e "${CYAN}║  Monthly Cost:  ${GREEN}${BOLD}\$$(printf "%3d" $monthly_cost)${NC}${CYAN}                          ║${NC}"
    echo -e "${CYAN}║  Yearly Cost:   ${GREEN}${BOLD}\$$(printf "%4d" $yearly_cost) ${WHITE}(10% discount)${NC}${CYAN}         ║${NC}"
    echo -e "${CYAN}║                                                  ║${NC}"
    echo -e "${CYAN}║  ${YELLOW}Note: Estimates are approximate${NC}${CYAN}             ║${NC}"
    echo -e "${CYAN}║  ${YELLOW}Actual costs may vary based on usage${NC}${CYAN}       ║${NC}"
    echo -e "${CYAN}║                                                  ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
    
    echo
    
    if [[ $monthly_cost -gt 500 ]]; then
        print_warning "High cost detected! Consider enabling cost optimization features."
        if ask_yes_no "Would you like to adjust your configuration to reduce costs?" "n"; then
            return 1  # Signal to go back and reconfigure
        fi
    fi
    
    ESTIMATED_MONTHLY_COST=$monthly_cost
    return 0
}

show_deployment_summary() {
    print_step 8 8 "Deployment Summary"
    
    echo -e "${WHITE}${BOLD}📋 Your ActiveLog deployment configuration:${NC}"
    echo
    
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    ${WHITE}${BOLD}Deployment Summary${NC}${CYAN}                      ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "Environment:" "$ENVIRONMENT"
    printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "AWS Region:" "$AWS_REGION"
    printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "Instance Class:" "$INSTANCE_CLASS"
    printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "Cost Optimized:" "$COST_OPTIMIZED"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║ ${WHITE}${BOLD}Selected Domains:${NC}${CYAN}                                         ║${NC}"
    for domain in "${SELECTED_DOMAINS[@]}"; do
        printf "${CYAN}║${NC}   ${GREEN}${CHECKMARK}${NC} %-50s ${CYAN}║${NC}\n" "$domain"
    done
    echo -e "${CYAN}║                                                              ║${NC}"
    printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "Auto-scaling:" "$AUTO_SCALING"
    if [[ "$AUTO_SCALING" == "true" ]]; then
        printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "Instance Range:" "$MIN_INSTANCES - $MAX_INSTANCES"
    fi
    printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "Monitoring Level:" "$MONITORING"
    printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "Backup Strategy:" "$BACKUP_FREQUENCY"
    if [[ "$CROSS_REGION_BACKUP" == "true" ]]; then
        printf "${CYAN}║${NC} %-20s ${WHITE}%-38s${NC} ${CYAN}║${NC}\n" "Backup Region:" "$BACKUP_REGION"
    fi
    echo -e "${CYAN}║                                                              ║${NC}"
    printf "${CYAN}║${NC} ${MONEY} %-18s ${GREEN}${BOLD}\$%-37d${NC} ${CYAN}║${NC}\n" "Estimated Cost/Month:" "$ESTIMATED_MONTHLY_COST"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    
    echo
    
    if ask_yes_no "${ROCKET} Proceed with deployment?" "y"; then
        return 0
    else
        return 1
    fi
}

create_configuration_files() {
    print_info "Creating configuration files..."
    
    # Create terraform variables
    cat > terraform.tfvars << EOF
# ActiveLog Deployment Configuration
# Generated by Interactive Wizard on $(date)

aws_region = "$AWS_REGION"
environment = "$ENVIRONMENT"

domains = {
EOF

    # Add domain configurations
    for domain in "${SELECTED_DOMAINS[@]}"; do
        local backend_type="t3.small"
        local trainer_type="t3.large"
        local runner_type="t3.medium"
        local enable_gpu="false"
        
        case "$INSTANCE_CLASS" in
            "minimal")
                backend_type="t3.micro"
                trainer_type="t3.small"
                runner_type="t3.small"
                ;;
            "balanced")
                backend_type="t3.small"
                trainer_type="t3.medium"
                runner_type="t3.medium"
                ;;
            "performance")
                backend_type="t3.medium"
                trainer_type="t3.large"
                runner_type="c5.large"
                ;;
            "high_performance")
                backend_type="t3.large"
                trainer_type="t3.xlarge"
                runner_type="c5.xlarge"
                ;;
        esac
        
        if [[ "$domain" == "DMLog" && "$ENABLE_GPU" == "true" ]]; then
            trainer_type="g4dn.xlarge"
            enable_gpu="true"
        fi
        
        cat >> terraform.tfvars << EOF
  "$domain" = {
    backend_instance_type    = "$backend_type"
    repository_instance_type = "t3.medium"
    deployer_instance_type   = "t3.small"
    trainer_instance_type    = "$trainer_type"
    builder_instance_type    = "t3.medium"
    runner_instance_type     = "$runner_type"
    enable_gpu              = $enable_gpu
    min_instances           = $MIN_INSTANCES
    max_instances           = $MAX_INSTANCES
  }
EOF
    done
    
    cat >> terraform.tfvars << EOF
}

# Cost optimization
cost_optimized = $COST_OPTIMIZED
auto_scaling_enabled = $AUTO_SCALING

# Monitoring
monitoring_level = "$MONITORING"
enable_alerts = $ENABLE_ALERTS

# Backup
backup_retention_days = $BACKUP_RETENTION
cross_region_backup = $CROSS_REGION_BACKUP
backup_region = "$BACKUP_REGION"
EOF

    # Create deployment configuration
    cat > deployment_config.json << EOF
{
  "deployment_id": "activelog-$(date +%Y%m%d-%H%M%S)",
  "created_at": "$(date --iso-8601=seconds)",
  "configuration": {
    "environment": "$ENVIRONMENT",
    "aws_region": "$AWS_REGION",
    "instance_class": "$INSTANCE_CLASS",
    "domains": [$(printf '"%s",' "${SELECTED_DOMAINS[@]}" | sed 's/,$//')],
    "auto_scaling": $AUTO_SCALING,
    "cost_optimized": $COST_OPTIMIZED,
    "monitoring_level": "$MONITORING",
    "backup_strategy": "$BACKUP_FREQUENCY",
    "estimated_monthly_cost": $ESTIMATED_MONTHLY_COST
  },
  "contacts": {
    $(if [[ -n "$ALERT_EMAIL" ]]; then echo "\"email\": \"$ALERT_EMAIL\","; fi)
    $(if [[ -n "$SLACK_WEBHOOK" ]]; then echo "\"slack_webhook\": \"$SLACK_WEBHOOK\","; fi)
    $(if [[ -n "$ALERT_PHONE" ]]; then echo "\"phone\": \"$ALERT_PHONE\","; fi)
    "aws_account_id": "$AWS_ACCOUNT_ID"
  }
}
EOF

    print_success "Configuration files created!"
}

run_deployment() {
    echo
    echo -e "${YELLOW}${BOLD}${ROCKET} Starting deployment...${NC}"
    echo
    
    # Build deployment command
    local deploy_cmd="./deploy_activelog.sh"
    deploy_cmd+=" --environment=$ENVIRONMENT"
    deploy_cmd+=" --region=$AWS_REGION"
    
    if [[ "$COST_OPTIMIZED" == "true" ]]; then
        deploy_cmd+=" --min-resources"
    fi
    
    deploy_cmd+=" --skip-confirmation"
    
    print_info "Running: $deploy_cmd"
    
    # Execute deployment
    if eval "$deploy_cmd"; then
        echo
        print_success "Deployment initiated successfully!"
        print_info "You can monitor progress with: ./monitor_health.sh $ENVIRONMENT 24"
    else
        print_error "Deployment failed! Check the logs above for details."
        return 1
    fi
}

main() {
    print_header
    
    # Main wizard flow
    check_prerequisites
    
    while true; do
        gather_deployment_preferences
        select_domains
        configure_resources
        configure_monitoring
        configure_backup
        
        if estimate_costs; then
            break
        fi
        
        print_warning "Let's reconfigure to optimize costs..."
        echo
    done
    
    if show_deployment_summary; then
        create_configuration_files
        
        if ask_yes_no "${CLOCK} Start deployment now?" "y"; then
            run_deployment
        else
            echo
            print_info "Configuration saved! You can run the deployment later with:"
            echo -e "${CYAN}  ./deploy_activelog.sh --environment=$ENVIRONMENT --region=$AWS_REGION$(if [[ "$COST_OPTIMIZED" == "true" ]]; then echo " --min-resources"; fi)${NC}"
        fi
    else
        print_info "Deployment cancelled. Configuration has been saved for later use."
    fi
    
    echo
    echo -e "${GREEN}${BOLD}Thank you for using the ActiveLog Deployment Wizard! ${ROCKET}${NC}"
    echo
}

# Trap Ctrl+C for graceful exit
trap 'echo -e "\n${YELLOW}Deployment wizard cancelled by user.${NC}"; exit 130' INT

# Change to deployment directory
cd "$(dirname "$0")/.."

# Run the wizard
main "$@"