#!/bin/bash

set -e

DEPLOYMENT_ID=${1:-"unknown"}
ENVIRONMENT=${2:-"beta"}
TOTAL_STEPS=${3:-100}

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

# Unicode symbols
CHECKMARK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
ROCKET="🚀"
GEAR="⚙️"
CLOCK="⏰"
CHART="📊"

# Progress tracking file
PROGRESS_FILE="/tmp/activelog_progress_${DEPLOYMENT_ID}.json"
LOG_FILE="/tmp/activelog_deployment_${DEPLOYMENT_ID}.log"

# Initialize progress tracking
init_progress_tracking() {
    cat > "$PROGRESS_FILE" << EOF
{
  "deployment_id": "$DEPLOYMENT_ID",
  "environment": "$ENVIRONMENT",
  "started_at": "$(date --iso-8601=seconds)",
  "status": "running",
  "current_step": 0,
  "total_steps": $TOTAL_STEPS,
  "stages": {
    "initialization": {"status": "pending", "progress": 0, "started_at": null, "completed_at": null},
    "terraform_plan": {"status": "pending", "progress": 0, "started_at": null, "completed_at": null},
    "terraform_apply": {"status": "pending", "progress": 0, "started_at": null, "completed_at": null},
    "domain_deployment": {"status": "pending", "progress": 0, "started_at": null, "completed_at": null},
    "monitoring_setup": {"status": "pending", "progress": 0, "started_at": null, "completed_at": null},
    "backup_configuration": {"status": "pending", "progress": 0, "started_at": null, "completed_at": null},
    "health_checks": {"status": "pending", "progress": 0, "started_at": null, "completed_at": null},
    "finalization": {"status": "pending", "progress": 0, "started_at": null, "completed_at": null}
  },
  "logs": [],
  "errors": []
}
EOF

    log_event "info" "Progress tracking initialized for deployment $DEPLOYMENT_ID"
}

# Update progress for a specific stage
update_stage_progress() {
    local stage=$1
    local status=$2
    local progress=${3:-0}
    
    # Get current timestamp
    local timestamp=$(date --iso-8601=seconds)
    
    # Update the JSON file using jq
    local temp_file=$(mktemp)
    
    if [[ "$status" == "running" ]]; then
        jq ".stages.\"$stage\".status = \"$status\" | .stages.\"$stage\".progress = $progress | .stages.\"$stage\".started_at = \"$timestamp\"" "$PROGRESS_FILE" > "$temp_file"
    elif [[ "$status" == "completed" ]]; then
        jq ".stages.\"$stage\".status = \"$status\" | .stages.\"$stage\".progress = 100 | .stages.\"$stage\".completed_at = \"$timestamp\"" "$PROGRESS_FILE" > "$temp_file"
    elif [[ "$status" == "failed" ]]; then
        jq ".stages.\"$stage\".status = \"$status\" | .stages.\"$stage\".completed_at = \"$timestamp\"" "$PROGRESS_FILE" > "$temp_file"
    else
        jq ".stages.\"$stage\".status = \"$status\" | .stages.\"$stage\".progress = $progress" "$PROGRESS_FILE" > "$temp_file"
    fi
    
    mv "$temp_file" "$PROGRESS_FILE"
    
    # Update overall progress
    update_overall_progress
}

# Calculate and update overall progress
update_overall_progress() {
    local temp_file=$(mktemp)
    local total_progress=0
    local completed_stages=0
    local failed_stages=0
    
    # Calculate progress from all stages
    while read -r stage_progress; do
        if [[ "$stage_progress" =~ ^[0-9]+$ ]]; then
            total_progress=$((total_progress + stage_progress))
        fi
    done < <(jq -r '.stages[].progress' "$PROGRESS_FILE" 2>/dev/null || echo "0")
    
    # Count completed and failed stages
    completed_stages=$(jq '[.stages[] | select(.status == "completed")] | length' "$PROGRESS_FILE" 2>/dev/null || echo "0")
    failed_stages=$(jq '[.stages[] | select(.status == "failed")] | length' "$PROGRESS_FILE" 2>/dev/null || echo "0")
    
    # Calculate overall progress (out of 8 stages)
    local overall_progress=$((total_progress / 8))
    
    # Update overall status
    local overall_status="running"
    if [[ $failed_stages -gt 0 ]]; then
        overall_status="failed"
    elif [[ $completed_stages -eq 8 ]]; then
        overall_status="completed"
    fi
    
    jq ".current_step = $overall_progress | .status = \"$overall_status\"" "$PROGRESS_FILE" > "$temp_file"
    mv "$temp_file" "$PROGRESS_FILE"
}

# Log an event
log_event() {
    local level=$1
    local message=$2
    local timestamp=$(date --iso-8601=seconds)
    
    # Add to progress file
    local temp_file=$(mktemp)
    jq ".logs += [{\"timestamp\": \"$timestamp\", \"level\": \"$level\", \"message\": \"$message\"}]" "$PROGRESS_FILE" > "$temp_file"
    mv "$temp_file" "$PROGRESS_FILE"
    
    # Also log to file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    # Print to console with colors
    case $level in
        "error")
            echo -e "${RED}${CROSS} $message${NC}" >&2
            ;;
        "warning")
            echo -e "${YELLOW}${WARNING} $message${NC}"
            ;;
        "success")
            echo -e "${GREEN}${CHECKMARK} $message${NC}"
            ;;
        "info")
            echo -e "${BLUE}${INFO} $message${NC}"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Log an error
log_error() {
    local message=$1
    local stage=${2:-"unknown"}
    
    log_event "error" "$message"
    
    # Add to errors array
    local temp_file=$(mktemp)
    local timestamp=$(date --iso-8601=seconds)
    jq ".errors += [{\"timestamp\": \"$timestamp\", \"stage\": \"$stage\", \"message\": \"$message\"}]" "$PROGRESS_FILE" > "$temp_file"
    mv "$temp_file" "$PROGRESS_FILE"
}

# Display current progress
show_progress() {
    clear
    
    # Read current progress
    if [[ ! -f "$PROGRESS_FILE" ]]; then
        echo -e "${RED}Progress file not found!${NC}"
        return 1
    fi
    
    local current_step=$(jq -r '.current_step' "$PROGRESS_FILE")
    local total_steps=$(jq -r '.total_steps' "$PROGRESS_FILE")
    local status=$(jq -r '.status' "$PROGRESS_FILE")
    local started_at=$(jq -r '.started_at' "$PROGRESS_FILE")
    
    # Header
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║         ${WHITE}${BOLD}🚀 ActiveLog Deployment Progress 🚀${NC}${CYAN}         ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    # Overall progress bar
    local progress_percentage=$((current_step * 100 / total_steps))
    local filled=$((progress_percentage * 50 / 100))
    local empty=$((50 - filled))
    
    echo -e "${WHITE}${BOLD}Overall Progress:${NC}"
    printf "${CYAN}["
    printf "%*s" $filled | tr ' ' '█'
    printf "%*s" $empty | tr ' ' '░'
    printf "] %d%% (%d/%d)${NC}\n" $progress_percentage $current_step $total_steps
    echo
    
    # Status indicator
    case $status in
        "running")
            echo -e "${BLUE}${GEAR} Status: ${WHITE}${BOLD}Running${NC}"
            ;;
        "completed")
            echo -e "${GREEN}${CHECKMARK} Status: ${WHITE}${BOLD}Completed Successfully${NC}"
            ;;
        "failed")
            echo -e "${RED}${CROSS} Status: ${WHITE}${BOLD}Failed${NC}"
            ;;
        *)
            echo -e "${YELLOW}${WARNING} Status: ${WHITE}${BOLD}Unknown${NC}"
            ;;
    esac
    
    # Time information
    if [[ "$started_at" != "null" ]]; then
        local elapsed_seconds=$(( $(date +%s) - $(date -d "$started_at" +%s) ))
        local elapsed_minutes=$((elapsed_seconds / 60))
        local elapsed_hours=$((elapsed_minutes / 60))
        
        if [[ $elapsed_hours -gt 0 ]]; then
            echo -e "${WHITE}${CLOCK} Elapsed Time: ${CYAN}${elapsed_hours}h ${$((elapsed_minutes % 60))}m${NC}"
        else
            echo -e "${WHITE}${CLOCK} Elapsed Time: ${CYAN}${elapsed_minutes}m ${$((elapsed_seconds % 60))}s${NC}"
        fi
    fi
    
    echo
    echo -e "${WHITE}${BOLD}Deployment Stages:${NC}"
    echo
    
    # Stage details
    local stages=("initialization" "terraform_plan" "terraform_apply" "domain_deployment" "monitoring_setup" "backup_configuration" "health_checks" "finalization")
    local stage_names=("🔧 Initialization" "📋 Terraform Planning" "🏗️  Infrastructure Creation" "🚀 Domain Deployment" "📊 Monitoring Setup" "💾 Backup Configuration" "🏥 Health Checks" "✨ Finalization")
    
    for i in "${!stages[@]}"; do
        local stage="${stages[$i]}"
        local stage_name="${stage_names[$i]}"
        local stage_status=$(jq -r ".stages.\"$stage\".status" "$PROGRESS_FILE")
        local stage_progress=$(jq -r ".stages.\"$stage\".progress" "$PROGRESS_FILE")
        
        case $stage_status in
            "pending")
                echo -e "  ${CYAN}⏳${NC} $stage_name - ${YELLOW}Pending${NC}"
                ;;
            "running")
                local stage_filled=$((stage_progress * 30 / 100))
                local stage_empty=$((30 - stage_filled))
                printf "  ${BLUE}⚙️${NC}  $stage_name - ${BLUE}"
                printf "%*s" $stage_filled | tr ' ' '█'
                printf "%*s" $stage_empty | tr ' ' '░'
                printf " %d%%${NC}\n" $stage_progress
                ;;
            "completed")
                echo -e "  ${GREEN}${CHECKMARK}${NC} $stage_name - ${GREEN}Completed${NC}"
                ;;
            "failed")
                echo -e "  ${RED}${CROSS}${NC} $stage_name - ${RED}Failed${NC}"
                ;;
        esac
    done
    
    echo
    
    # Recent logs
    local recent_logs=$(jq -r '.logs[-5:][] | "[\(.timestamp | strftime("%H:%M:%S"))] \(.level | ascii_upcase): \(.message)"' "$PROGRESS_FILE" 2>/dev/null || echo "")
    
    if [[ -n "$recent_logs" ]]; then
        echo -e "${WHITE}${BOLD}Recent Activity:${NC}"
        echo "$recent_logs" | while read -r log_line; do
            if [[ "$log_line" =~ ERROR ]]; then
                echo -e "${RED}  $log_line${NC}"
            elif [[ "$log_line" =~ WARNING ]]; then
                echo -e "${YELLOW}  $log_line${NC}"
            elif [[ "$log_line" =~ SUCCESS ]]; then
                echo -e "${GREEN}  $log_line${NC}"
            else
                echo -e "${BLUE}  $log_line${NC}"
            fi
        done
        echo
    fi
    
    # Error summary
    local error_count=$(jq '.errors | length' "$PROGRESS_FILE" 2>/dev/null || echo "0")
    if [[ $error_count -gt 0 ]]; then
        echo -e "${RED}${BOLD}${WARNING} $error_count Error(s) Detected:${NC}"
        jq -r '.errors[-3:][] | "  [\(.timestamp | strftime("%H:%M:%S"))] \(.stage): \(.message)"' "$PROGRESS_FILE" 2>/dev/null | while read -r error_line; do
            echo -e "${RED}  $error_line${NC}"
        done
        echo
    fi
    
    # Next step information
    if [[ "$status" == "running" ]]; then
        local current_stage=""
        for stage in "${stages[@]}"; do
            local stage_status=$(jq -r ".stages.\"$stage\".status" "$PROGRESS_FILE")
            if [[ "$stage_status" == "running" ]]; then
                current_stage=$stage
                break
            fi
        done
        
        if [[ -n "$current_stage" ]]; then
            echo -e "${BLUE}${INFO} Currently executing: ${WHITE}$current_stage${NC}"
        fi
        
        # ETA calculation (rough estimate)
        if [[ $current_step -gt 0 && "$started_at" != "null" ]]; then
            local elapsed_seconds=$(( $(date +%s) - $(date -d "$started_at" +%s) ))
            local rate=$((elapsed_seconds / current_step))
            local remaining_steps=$((total_steps - current_step))
            local eta_seconds=$((remaining_steps * rate))
            local eta_minutes=$((eta_seconds / 60))
            
            if [[ $eta_minutes -gt 0 ]]; then
                echo -e "${CYAN}${CLOCK} Estimated Time Remaining: ${WHITE}~${eta_minutes} minutes${NC}"
            fi
        fi
        
        echo
        echo -e "${YELLOW}Press Ctrl+C to exit monitoring (deployment will continue)${NC}"
    fi
}

# Monitor progress continuously
monitor_progress() {
    local refresh_interval=${1:-5}
    
    echo -e "${BLUE}Starting progress monitoring (refreshing every ${refresh_interval}s)...${NC}"
    echo
    
    while true; do
        show_progress
        
        # Check if deployment is complete or failed
        local status=$(jq -r '.status' "$PROGRESS_FILE" 2>/dev/null || echo "unknown")
        
        if [[ "$status" == "completed" ]]; then
            echo -e "${GREEN}${BOLD}${CHECKMARK} Deployment completed successfully!${NC}"
            break
        elif [[ "$status" == "failed" ]]; then
            echo -e "${RED}${BOLD}${CROSS} Deployment failed. Check the logs for details.${NC}"
            break
        fi
        
        sleep $refresh_interval
    done
}

# Generate final report
generate_final_report() {
    local deployment_id=$1
    local report_file="deployment_report_${deployment_id}_$(date +%Y%m%d_%H%M%S).html"
    
    if [[ ! -f "$PROGRESS_FILE" ]]; then
        echo "Progress file not found!"
        return 1
    fi
    
    local status=$(jq -r '.status' "$PROGRESS_FILE")
    local started_at=$(jq -r '.started_at' "$PROGRESS_FILE")
    local current_step=$(jq -r '.current_step' "$PROGRESS_FILE")
    local total_steps=$(jq -r '.total_steps' "$PROGRESS_FILE")
    
    cat > "$report_file" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ActiveLog Deployment Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        
        .report-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }
        
        .status-completed {
            background: #10B981;
            color: white;
        }
        
        .status-failed {
            background: #EF4444;
            color: white;
        }
        
        .status-running {
            background: #F59E0B;
            color: white;
        }
        
        .content {
            padding: 40px;
        }
        
        .progress-section {
            background: #f8fafc;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
        }
        
        .progress-bar {
            background: #e2e8f0;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
            margin: 20px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        
        .stages-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .stage-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #e2e8f0;
        }
        
        .stage-completed {
            border-left-color: #10B981;
        }
        
        .stage-failed {
            border-left-color: #EF4444;
        }
        
        .stage-running {
            border-left-color: #F59E0B;
        }
        
        .logs-section {
            background: #1e293b;
            color: #e2e8f0;
            border-radius: 10px;
            padding: 20px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .log-entry {
            margin: 5px 0;
            padding: 5px;
        }
        
        .log-error {
            color: #f87171;
        }
        
        .log-warning {
            color: #fbbf24;
        }
        
        .log-success {
            color: #34d399;
        }
        
        .log-info {
            color: #60a5fa;
        }
        
        .metric-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .metric-card {
            text-align: center;
            padding: 20px;
            border-radius: 10px;
            background: white;
            border: 1px solid #e2e8f0;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #4facfe;
        }
        
        .metric-label {
            color: #64748b;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1>🚀 ActiveLog Deployment Report</h1>
            <div class="status-badge status-STATUS_CLASS">STATUS_TEXT</div>
        </div>
        
        <div class="content">
            <div class="progress-section">
                <h2>📊 Overall Progress</h2>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: PROGRESS_PERCENTAGE%"></div>
                </div>
                <p style="text-align: center; font-size: 1.2em; margin: 0;">
                    <strong>CURRENT_STEP / TOTAL_STEPS</strong> steps completed (PROGRESS_PERCENTAGE%)
                </p>
            </div>
            
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="metric-value">DEPLOYMENT_ID</div>
                    <div class="metric-label">Deployment ID</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">ENVIRONMENT</div>
                    <div class="metric-label">Environment</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">STARTED_AT</div>
                    <div class="metric-label">Started At</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">DURATION</div>
                    <div class="metric-label">Duration</div>
                </div>
            </div>
            
            <h2>🏗️ Deployment Stages</h2>
            <div class="stages-grid" id="stages-grid">
                <!-- Stages will be inserted here -->
            </div>
            
            <h2>📝 Deployment Logs</h2>
            <div class="logs-section" id="logs-section">
                <!-- Logs will be inserted here -->
            </div>
        </div>
    </div>

    <script>
        // Insert progress data
        const progressData = PROGRESS_DATA;
        
        // Populate stages
        const stagesGrid = document.getElementById('stages-grid');
        const stages = progressData.stages;
        
        Object.keys(stages).forEach(stageName => {
            const stage = stages[stageName];
            const stageCard = document.createElement('div');
            stageCard.className = `stage-card stage-${stage.status}`;
            
            const statusEmoji = {
                completed: '✅',
                failed: '❌',
                running: '⚙️',
                pending: '⏳'
            };
            
            stageCard.innerHTML = `
                <h3>${statusEmoji[stage.status]} ${stageName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
                <p><strong>Status:</strong> ${stage.status}</p>
                <p><strong>Progress:</strong> ${stage.progress}%</p>
                ${stage.started_at ? `<p><strong>Started:</strong> ${new Date(stage.started_at).toLocaleString()}</p>` : ''}
                ${stage.completed_at ? `<p><strong>Completed:</strong> ${new Date(stage.completed_at).toLocaleString()}</p>` : ''}
            `;
            
            stagesGrid.appendChild(stageCard);
        });
        
        // Populate logs
        const logsSection = document.getElementById('logs-section');
        progressData.logs.forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${log.level}`;
            logEntry.innerHTML = `[${new Date(log.timestamp).toLocaleString()}] [${log.level.toUpperCase()}] ${log.message}`;
            logsSection.appendChild(logEntry);
        });
    </script>
</body>
</html>
EOF

    # Replace placeholders
    local progress_percentage=$((current_step * 100 / total_steps))
    local status_class=$(echo "$status" | tr '[:upper:]' '[:lower:]')
    local status_text=$(echo "$status" | tr '[:lower:]' '[:upper:]')
    
    # Calculate duration
    local duration="N/A"
    if [[ "$started_at" != "null" ]]; then
        local elapsed_seconds=$(( $(date +%s) - $(date -d "$started_at" +%s) ))
        local elapsed_minutes=$((elapsed_seconds / 60))
        local elapsed_hours=$((elapsed_minutes / 60))
        
        if [[ $elapsed_hours -gt 0 ]]; then
            duration="${elapsed_hours}h ${$((elapsed_minutes % 60))}m"
        else
            duration="${elapsed_minutes}m ${$((elapsed_seconds % 60))}s"
        fi
    fi
    
    # Read and escape JSON data
    local progress_json=$(cat "$PROGRESS_FILE" | jq -c .)
    
    sed -i "s/STATUS_CLASS/$status_class/g" "$report_file"
    sed -i "s/STATUS_TEXT/$status_text/g" "$report_file"
    sed -i "s/PROGRESS_PERCENTAGE/$progress_percentage/g" "$report_file"
    sed -i "s/CURRENT_STEP/$current_step/g" "$report_file"
    sed -i "s/TOTAL_STEPS/$total_steps/g" "$report_file"
    sed -i "s/DEPLOYMENT_ID/$deployment_id/g" "$report_file"
    sed -i "s/ENVIRONMENT/${ENVIRONMENT^^}/g" "$report_file"
    sed -i "s/STARTED_AT/$(date -d "$started_at" '+%H:%M' 2>/dev/null || echo 'N\/A')/g" "$report_file"
    sed -i "s/DURATION/$duration/g" "$report_file"
    sed -i "s/PROGRESS_DATA/$progress_json/g" "$report_file"
    
    echo "$report_file"
}

# Main function
main() {
    case "${1:-monitor}" in
        "init")
            init_progress_tracking
            ;;
        "update")
            update_stage_progress "$2" "$3" "$4"
            ;;
        "log")
            log_event "$2" "$3"
            ;;
        "error")
            log_error "$2" "$3"
            ;;
        "monitor")
            monitor_progress "${4:-5}"
            ;;
        "report")
            report_file=$(generate_final_report "$DEPLOYMENT_ID")
            echo "Report generated: $report_file"
            ;;
        "show")
            show_progress
            ;;
        *)
            echo "Usage: $0 {init|update|log|error|monitor|report|show} [args...]"
            echo ""
            echo "Commands:"
            echo "  init                          - Initialize progress tracking"
            echo "  update <stage> <status> [%]   - Update stage progress"
            echo "  log <level> <message>         - Log an event"
            echo "  error <message> [stage]       - Log an error"
            echo "  monitor [interval]            - Monitor progress (default: 5s)"
            echo "  report                        - Generate HTML report"
            echo "  show                          - Show current progress once"
            exit 1
            ;;
    esac
}

# Trap Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Progress monitoring stopped.${NC}"; exit 0' INT

# Run main function
main "$@"