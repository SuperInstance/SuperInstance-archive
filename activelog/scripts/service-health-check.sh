#!/bin/bash

# ActiveLog Service Health Check Script
# Comprehensive health monitoring for all services

echo "🏥 ActiveLog Service Health Check Starting..."

# Configuration
SERVICES_DIR="/home/activeloguser/activelog/services"
PID_DIR="/home/activeloguser/activelog/pids"
LOGS_DIR="/home/activeloguser/activelog/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
HEALTHY=0
UNHEALTHY=0
STOPPED=0

echo "📊 System Overview:"
echo "   - Total processes: $(ps aux | wc -l)"
echo "   - Memory usage: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "   - Load average: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

# Check Docker infrastructure services
echo "🐳 Infrastructure Services:"
if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "activelog-postgres.*Up"; then
    echo -e "   ${GREEN}✅ PostgreSQL - Running${NC}"
    ((HEALTHY++))
else
    echo -e "   ${RED}❌ PostgreSQL - Down${NC}" 
    ((UNHEALTHY++))
fi

if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "activelog-redis.*Up"; then
    echo -e "   ${GREEN}✅ Redis - Running${NC}"
    ((HEALTHY++))
else
    echo -e "   ${RED}❌ Redis - Down${NC}"
    ((UNHEALTHY++))
fi

if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "activelog-elasticsearch.*Up"; then
    echo -e "   ${GREEN}✅ Elasticsearch - Running${NC}"
    ((HEALTHY++))
else
    echo -e "   ${RED}❌ Elasticsearch - Down${NC}"
    ((UNHEALTHY++))
fi

if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "activelog-minio.*Up"; then
    echo -e "   ${GREEN}✅ MinIO - Running${NC}"
    ((HEALTHY++))
else
    echo -e "   ${RED}❌ MinIO - Down${NC}"
    ((UNHEALTHY++))
fi

echo ""
echo "🔍 Application Services:"

# Check application services with PID files
for pid_file in "$PID_DIR"/*.pid; do
    if [ ! -f "$pid_file" ]; then
        continue
    fi
    
    service_name=$(basename "$pid_file" .pid)
    
    if [ -s "$pid_file" ]; then
        pid=$(cat "$pid_file")
        
        if kill -0 "$pid" 2>/dev/null; then
            # Check if service is responding (basic check)
            port_info=$(netstat -tuln | grep ":8[0-9][0-9][0-9]" | grep LISTEN | head -1)
            if [ ! -z "$port_info" ]; then
                echo -e "   ${GREEN}✅ $service_name (PID: $pid) - Healthy${NC}"
            else
                echo -e "   ${YELLOW}⚠️  $service_name (PID: $pid) - Running but no ports${NC}"
            fi
            ((HEALTHY++))
        else
            echo -e "   ${RED}❌ $service_name - Process not found${NC}"
            ((UNHEALTHY++))
        fi
    else
        echo -e "   ${RED}❌ $service_name - Empty PID file${NC}"
        ((STOPPED++))
    fi
done

echo ""
echo "📊 Health Summary:"
echo -e "   ${GREEN}Healthy services: $HEALTHY${NC}"
echo -e "   ${RED}Unhealthy services: $UNHEALTHY${NC}"
echo -e "   ${YELLOW}Stopped services: $STOPPED${NC}"

# Overall health status
TOTAL_SERVICES=$((HEALTHY + UNHEALTHY + STOPPED))
HEALTH_PERCENTAGE=$((HEALTHY * 100 / TOTAL_SERVICES))

echo ""
if [ $HEALTH_PERCENTAGE -ge 80 ]; then
    echo -e "🎯 ${GREEN}System Health: ${HEALTH_PERCENTAGE}% - Excellent${NC}"
elif [ $HEALTH_PERCENTAGE -ge 60 ]; then
    echo -e "🎯 ${YELLOW}System Health: ${HEALTH_PERCENTAGE}% - Good${NC}"
else
    echo -e "🎯 ${RED}System Health: ${HEALTH_PERCENTAGE}% - Needs Attention${NC}"
fi

# Recommendations
if [ $UNHEALTHY -gt 0 ] || [ $STOPPED -gt 0 ]; then
    echo ""
    echo "💡 Recommendations:"
    echo "   - Run './scripts/cleanup-pids.sh' to clean stale PIDs"
    echo "   - Check logs in $LOGS_DIR for service errors"
    echo "   - Restart failed services: './start_activelog.sh'"
    echo "   - Monitor resource usage: 'htop' or 'docker stats'"
fi