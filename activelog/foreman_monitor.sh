#!/bin/bash
# Foreman monitoring script - track bot progress and system health

echo "=== SuperInstance Cloud Migration - Foreman Monitor ==="
echo "Timestamp: $(date)"
echo

# Check storage usage (prevent runaway processes)
echo "--- Storage Status ---"
df -h / | grep -E "Size|/dev"
echo "ActiveLog size: $(du -sh /home/activeloguser/activelog | cut -f1)"
echo

# Check AWS infrastructure status
echo "--- AWS Infrastructure Status ---"
echo "Region: $(aws configure get region 2>/dev/null || echo 'Not configured')"
echo "Account: $(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'No access')"
echo "VPCs: $(aws ec2 describe-vpcs --query 'length(Vpcs)' 2>/dev/null || echo '0')"

# Check Kubernetes status
echo -n "Kubernetes: "
if [ -f /tmp/k8s-ready.flag ]; then
    echo "READY"
else
    echo "NOT READY"
fi

echo -n "Infrastructure env: "
if [ -f /tmp/infrastructure.env ]; then
    echo "EXISTS"
else
    echo "MISSING"
fi
echo

# Bot status check
for bot in infrastructure services domains; do
    log_file="/home/activeloguser/activelog/bot_${bot}_log.txt"
    echo "--- Bot-${bot^} Status ---"
    if [ -f "$log_file" ]; then
        current_status=$(grep "Current Status:" "$log_file" | cut -d: -f2 | xargs)
        active_puzzles=$(grep -A5 "ACTIVE PUZZLES:" "$log_file" | tail -n +2 | grep -v "^#" | grep -v "^$" | wc -l)
        completed_tasks=$(grep -A20 "COMPLETED TASKS:" "$log_file" | grep -c "^-")
        
        echo "Status: $current_status"
        echo "Active puzzles: $active_puzzles"
        echo "Completed tasks: $completed_tasks"
    else
        echo "Log file missing!"
    fi
    echo
done

# Process monitoring (catch runaway processes)
echo "--- System Resource Usage ---"
echo "CPU usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d% -f1)"
echo "Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "Top processes:"
ps aux --sort=-%cpu | head -3 | tail -2 | awk '{print $1, $2, $3"% CPU", $4"% MEM", $11}'
echo