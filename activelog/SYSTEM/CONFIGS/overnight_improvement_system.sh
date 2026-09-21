#!/bin/bash
# Overnight Autonomous Improvement System
# Runs continuous research synthesis and project enhancement while you sleep

# Configuration
LOG_FILE="/home/activeloguser/activelog/SYSTEM/LOGS/overnight_$(date +%Y%m%d_%H%M%S).log"
STORAGE_LIMIT_MB=8192  # 8GB storage limit
API_BUDGET_LIMIT=50    # $50 Claude API budget limit
IMPROVEMENT_CYCLES=12  # 12 cycles over ~8 hours (40 minutes each)

# Initialize logging
mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date): Starting Overnight Improvement System" >> "$LOG_FILE"
echo "Storage Limit: ${STORAGE_LIMIT_MB}MB, API Budget: \$${API_BUDGET_LIMIT}" >> "$LOG_FILE"

# Track resource usage
STORAGE_USED=0
API_COST_ESTIMATED=0

function check_resources() {
    # Check storage usage
    CURRENT_STORAGE=$(du -sm /home/activeloguser/activelog 2>/dev/null | cut -f1)
    if [ "$CURRENT_STORAGE" -gt "$STORAGE_LIMIT_MB" ]; then
        echo "$(date): Storage limit exceeded ($CURRENT_STORAGE MB > $STORAGE_LIMIT_MB MB)" >> "$LOG_FILE"
        return 1
    fi
    
    # Check API cost estimate
    if [ "$API_COST_ESTIMATED" -gt "$API_BUDGET_LIMIT" ]; then
        echo "$(date): API budget limit reached (\$$API_COST_ESTIMATED > \$$API_BUDGET_LIMIT)" >> "$LOG_FILE"
        return 1
    fi
    
    return 0
}

function cleanup_space() {
    echo "$(date): Cleaning up space to stay within limits" >> "$LOG_FILE"
    
    # Remove old log files (keep last 7 days)
    find /home/activeloguser/activelog/SYSTEM/LOGS -name "*.log" -mtime +7 -delete 2>/dev/null
    
    # Compress large files older than 1 day
    find /home/activeloguser/activelog -name "*.md" -size +1M -mtime +1 -exec gzip {} \; 2>/dev/null
    
    # Clean up temporary files
    find /home/activeloguser/activelog -name "tmp_*" -delete 2>/dev/null
    find /home/activeloguser/activelog -name "*.tmp" -delete 2>/dev/null
}

function run_improvement_cycle() {
    local cycle_num=$1
    echo "$(date): Starting improvement cycle $cycle_num" >> "$LOG_FILE"
    
    # Check resources before starting
    if ! check_resources; then
        echo "$(date): Resource limits reached, stopping cycles" >> "$LOG_FILE"
        return 1
    fi
    
    # Cleanup space if needed
    if [ "$CURRENT_STORAGE" -gt $((STORAGE_LIMIT_MB * 80 / 100)) ]; then
        cleanup_space
    fi
    
    # Run improvement cycle
    python3 /home/activeloguser/activelog/SYSTEM/SCRIPTS/overnight_improvement.py \
        --cycle=$cycle_num \
        --max-api-cost=4 \
        --storage-limit=$STORAGE_LIMIT_MB >> "$LOG_FILE" 2>&1
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "$(date): Cycle $cycle_num completed successfully" >> "$LOG_FILE"
        API_COST_ESTIMATED=$((API_COST_ESTIMATED + 4))
    else
        echo "$(date): Cycle $cycle_num failed with exit code $exit_code" >> "$LOG_FILE"
    fi
    
    # Sleep between cycles (40 minutes)
    echo "$(date): Sleeping 40 minutes before next cycle" >> "$LOG_FILE"
    sleep 2400
    
    return $exit_code
}

# Main execution loop
echo "$(date): Beginning $IMPROVEMENT_CYCLES improvement cycles" >> "$LOG_FILE"

for i in $(seq 1 $IMPROVEMENT_CYCLES); do
    if ! run_improvement_cycle $i; then
        echo "$(date): Stopping improvement cycles due to failure or resource limits" >> "$LOG_FILE"
        break
    fi
done

echo "$(date): Overnight improvement system completed" >> "$LOG_FILE"
echo "Final storage usage: $(du -sm /home/activeloguser/activelog | cut -f1)MB" >> "$LOG_FILE"
echo "Estimated API costs: \$${API_COST_ESTIMATED}" >> "$LOG_FILE"