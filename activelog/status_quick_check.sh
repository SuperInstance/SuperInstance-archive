#!/bin/bash
# Ultra-fast bot status check - minimal tokens

echo "=== QUICK STATUS ==="
echo "Last update: $(tail -1 micro_updates.log 2>/dev/null || echo 'No updates yet')"
echo "Ready flags: $(ls /tmp/*-ready.flag 2>/dev/null | wc -l)/4 ready"
echo "Active K8s: $(ps aux 2>/dev/null | grep -c kubectl) processes"
echo "Bot activity: $(ps aux 2>/dev/null | grep -c claude) Claude instances"

# Check if bots are stuck (no update in 20+ minutes)
if [ -f micro_updates.log ]; then
    last_hour=$(tail -1 micro_updates.log | cut -d'|' -f1 | cut -d':' -f1)
    last_min=$(tail -1 micro_updates.log | cut -d'|' -f1 | cut -d':' -f2)
    current_hour=$(date +%H)
    current_min=$(date +%M)
    
    time_diff=$((($current_hour * 60 + $current_min) - ($last_hour * 60 + $last_min)))
    if [ $time_diff -gt 20 ]; then
        echo "⚠️  STUCK: $time_diff min since last update"
    else  
        echo "✅ ACTIVE: Recent activity ($time_diff min ago)"
    fi
fi

# Critical path check
if [ -f /tmp/k8s-ready.flag ] && [ ! -f /tmp/auth-service-ready.flag ]; then
    echo "🎯 CRITICAL: Bot-Services should deploy auth-service NOW"
elif [ -f /tmp/auth-service-ready.flag ] && [ ! -f /tmp/activelog-ready.flag ]; then
    echo "🎯 CRITICAL: Bot-Domains should deploy ActiveLog fitness NOW"  
fi