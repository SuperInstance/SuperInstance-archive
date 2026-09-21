#!/bin/bash
# Continuous resource monitoring - prevent runaway processes

LOGFILE="/home/activeloguser/activelog/resource_alerts.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEM=80  
ALERT_THRESHOLD_DISK=90
ALERT_THRESHOLD_LOGSIZE=100  # MB

log_alert() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ALERT: $1" | tee -a "$LOGFILE"
}

# Check storage usage
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt "$ALERT_THRESHOLD_DISK" ]; then
    log_alert "DISK USAGE HIGH: ${DISK_USAGE}%"
fi

# Check large log files
find /home/activeloguser/activelog -name "*.log" -size +${ALERT_THRESHOLD_LOGSIZE}M 2>/dev/null | while read logfile; do
    SIZE=$(du -m "$logfile" | cut -f1)
    log_alert "LARGE LOG FILE: $logfile ($SIZE MB)"
    
    # Auto-rotate large logs
    if [ "$SIZE" -gt 500 ]; then
        mv "$logfile" "${logfile}.old.$(date +%s)"
        touch "$logfile"
        log_alert "AUTO-ROTATED: $logfile"
    fi
done

# Check runaway processes
ps aux --sort=-%cpu | head -10 | awk 'NR>1 && $3>50 {print "HIGH CPU PROCESS:", $11, $3"%"}' | while read line; do
    log_alert "$line"
done

# Check memory usage
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", ($3/$2)*100}')
if [ "$MEM_USAGE" -gt "$ALERT_THRESHOLD_MEM" ]; then
    log_alert "MEMORY USAGE HIGH: ${MEM_USAGE}%"
fi

# Check bot activity (should see recent updates)
LAST_UPDATE=$(tail -1 /home/activeloguser/activelog/micro_updates.log 2>/dev/null | cut -d'|' -f1)
if [ -n "$LAST_UPDATE" ]; then
    CURRENT_TIME=$(date +%H:%M)
    LAST_HOUR=$(echo $LAST_UPDATE | cut -d':' -f1)
    LAST_MIN=$(echo $LAST_UPDATE | cut -d':' -f2)
    CURRENT_HOUR=$(date +%H)
    CURRENT_MIN=$(date +%M)
    
    TIME_DIFF=$((($CURRENT_HOUR * 60 + $CURRENT_MIN) - ($LAST_HOUR * 60 + $LAST_MIN)))
    if [ $TIME_DIFF -gt 30 ]; then
        log_alert "BOTS INACTIVE: $TIME_DIFF minutes since last update"
    fi
fi

# Count active processes
ACTIVE_PROCESSES=$(ps aux | grep -c claude)
echo "$(date '+%H:%M') MONITOR: CPU:${MEM_USAGE}% MEM:${MEM_USAGE}% DISK:${DISK_USAGE}% BOTS:${ACTIVE_PROCESSES}"