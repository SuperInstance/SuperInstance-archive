#!/bin/bash

##############################################################################
# Complete System Health Check
# Validates all components of the Swarm Intelligence Platform
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
WS_URL="${WS_URL:-ws://localhost:8000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Results
HEALTH_REPORT="health_report_$(date +%Y%m%d_%H%M%S).txt"
PASSED=0
FAILED=0
WARNINGS=0

echo "========================================================================="
echo "  Swarm Intelligence Platform - Complete System Health Check"
echo "========================================================================="
echo ""
echo "Timestamp: $(date)"
echo "Report: $HEALTH_REPORT"
echo ""

# Initialize report
cat > "$HEALTH_REPORT" << EOF
Swarm Intelligence Platform - Health Check Report
Generated: $(date)
========================================================================

EOF

# Function to log result
log_result() {
    local component=$1
    local status=$2
    local message=$3

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $component: $message"
        echo "✓ $component: $message" >> "$HEALTH_REPORT"
        PASSED=$((PASSED + 1))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $component: $message"
        echo "✗ $component: $message" >> "$HEALTH_REPORT"
        FAILED=$((FAILED + 1))
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $component: $message"
        echo "⚠ $component: $message" >> "$HEALTH_REPORT"
        WARNINGS=$((WARNINGS + 1))
    fi
}

# Check 1: Core Engine (Go Backend)
check_core_engine() {
    echo ""
    echo "[1/10] Checking Core Engine (Go Backend)..."
    echo "-------------------------------------------"

    # Check if Go is installed
    if command -v go &> /dev/null; then
        GO_VERSION=$(go version | awk '{print $3}')
        log_result "Core Engine" "PASS" "Go installed: $GO_VERSION"
    else
        log_result "Core Engine" "WARN" "Go not found (may be compiled binary)"
    fi

    # Check if backend directory exists
    if [ -d "../backend/core" ]; then
        log_result "Core Engine" "PASS" "Backend directory exists"

        # Try to run tests
        if cd ../backend/core && go test -v -run TestSwarmEngineBasic &> /dev/null; then
            log_result "Core Engine" "PASS" "Basic tests passing"
        else
            log_result "Core Engine" "WARN" "Tests not run or failing"
        fi
        cd - > /dev/null
    else
        log_result "Core Engine" "FAIL" "Backend directory not found"
    fi
}

# Check 2: API Services
check_api_services() {
    echo ""
    echo "[2/10] Checking API Services..."
    echo "-------------------------------"

    # Check health endpoint
    if curl -s -f "$API_URL/health" > /dev/null; then
        HEALTH_DATA=$(curl -s "$API_URL/health")
        STATUS=$(echo "$HEALTH_DATA" | grep -o '"status":"[^"]*' | cut -d'"' -f4)

        if [ "$STATUS" = "healthy" ]; then
            log_result "API Health" "PASS" "API is healthy"
        else
            log_result "API Health" "FAIL" "API status: $STATUS"
        fi
    else
        log_result "API Health" "FAIL" "API not responding at $API_URL"
    fi

    # Check API version
    VERSION=$(curl -s "$API_URL/health" | grep -o '"version":"[^"]*' | cut -d'"' -f4)
    if [ -n "$VERSION" ]; then
        log_result "API Version" "PASS" "Version: $VERSION"
    else
        log_result "API Version" "WARN" "Version not available"
    fi

    # Test authentication endpoint
    if curl -s -f "$API_URL/api/v1/auth/token" -X POST -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=test&password=test" &> /dev/null; then
        log_result "API Auth" "PASS" "Authentication endpoint responding"
    else
        log_result "API Auth" "WARN" "Authentication endpoint not configured or failing"
    fi
}

# Check 3: Frontend
check_frontend() {
    echo ""
    echo "[3/10] Checking Frontend..."
    echo "---------------------------"

    if [ -d "../frontend" ]; then
        log_result "Frontend" "PASS" "Frontend directory exists"

        # Check if package.json exists
        if [ -f "../frontend/package.json" ]; then
            log_result "Frontend" "PASS" "package.json found"

            # Check if node_modules exists
            if [ -d "../frontend/node_modules" ]; then
                log_result "Frontend" "PASS" "Dependencies installed"
            else
                log_result "Frontend" "WARN" "Dependencies not installed (run npm install)"
            fi
        else
            log_result "Frontend" "WARN" "package.json not found"
        fi

        # Check if build exists
        if [ -d "../frontend/dist" ] || [ -d "../frontend/build" ]; then
            log_result "Frontend" "PASS" "Production build exists"
        else
            log_result "Frontend" "WARN" "No production build found"
        fi
    else
        log_result "Frontend" "FAIL" "Frontend directory not found"
    fi
}

# Check 4: Database
check_databases() {
    echo ""
    echo "[4/10] Checking Databases..."
    echo "---------------------------"

    # Check PostgreSQL
    if command -v psql &> /dev/null; then
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" &> /dev/null; then
            log_result "PostgreSQL" "PASS" "Database is ready"
        else
            log_result "PostgreSQL" "WARN" "Cannot connect to database at $DB_HOST:$DB_PORT"
        fi
    else
        log_result "PostgreSQL" "WARN" "psql not installed (database may still be accessible)"
    fi

    # Check Redis
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &> /dev/null; then
            log_result "Redis" "PASS" "Redis is responding"
        else
            log_result "Redis" "WARN" "Cannot connect to Redis at $REDIS_HOST:$REDIS_PORT"
        fi
    else
        log_result "Redis" "WARN" "redis-cli not installed (Redis may still be accessible)"
    fi
}

# Check 5: Message Queues
check_message_queues() {
    echo ""
    echo "[5/10] Checking Message Queues..."
    echo "--------------------------------"

    # Check if Kafka is running (if configured)
    if command -v kafka-topics.sh &> /dev/null; then
        log_result "Kafka" "PASS" "Kafka CLI found"
    else
        log_result "Kafka" "WARN" "Kafka not found (optional)"
    fi

    # Redis can also serve as message queue
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &> /dev/null; then
            log_result "Message Queue" "PASS" "Redis queue available"
        fi
    fi
}

# Check 6: Monitoring
check_monitoring() {
    echo ""
    echo "[6/10] Checking Monitoring..."
    echo "----------------------------"

    # Check if Prometheus is accessible
    if curl -s -f "http://localhost:9090/-/healthy" &> /dev/null; then
        log_result "Prometheus" "PASS" "Prometheus is healthy"
    else
        log_result "Prometheus" "WARN" "Prometheus not accessible (optional)"
    fi

    # Check if Grafana is accessible
    if curl -s -f "http://localhost:3000/api/health" &> /dev/null; then
        log_result "Grafana" "PASS" "Grafana is accessible"
    else
        log_result "Grafana" "WARN" "Grafana not accessible (optional)"
    fi
}

# Check 7: Docker Containers
check_docker() {
    echo ""
    echo "[7/10] Checking Docker..."
    echo "------------------------"

    if command -v docker &> /dev/null; then
        log_result "Docker" "PASS" "Docker installed"

        # Check running containers
        CONTAINER_COUNT=$(docker ps -q 2>/dev/null | wc -l)
        if [ "$CONTAINER_COUNT" -gt 0 ]; then
            log_result "Docker" "PASS" "$CONTAINER_COUNT container(s) running"
        else
            log_result "Docker" "WARN" "No containers running"
        fi

        # Check Docker Compose
        if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
            log_result "Docker Compose" "PASS" "Docker Compose available"
        else
            log_result "Docker Compose" "WARN" "Docker Compose not found"
        fi
    else
        log_result "Docker" "WARN" "Docker not installed (optional for development)"
    fi
}

# Check 8: Disk Space
check_disk_space() {
    echo ""
    echo "[8/10] Checking Disk Space..."
    echo "----------------------------"

    # Check available disk space
    if command -v df &> /dev/null; then
        DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | tr -d '%')

        if [ "$DISK_USAGE" -lt 80 ]; then
            log_result "Disk Space" "PASS" "Disk usage: ${DISK_USAGE}%"
        elif [ "$DISK_USAGE" -lt 90 ]; then
            log_result "Disk Space" "WARN" "Disk usage: ${DISK_USAGE}% (getting high)"
        else
            log_result "Disk Space" "FAIL" "Disk usage: ${DISK_USAGE}% (critical)"
        fi
    else
        log_result "Disk Space" "WARN" "df command not available"
    fi
}

# Check 9: Memory
check_memory() {
    echo ""
    echo "[9/10] Checking Memory..."
    echo "------------------------"

    if command -v free &> /dev/null; then
        MEMORY_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')

        if [ "$MEMORY_USAGE" -lt 80 ]; then
            log_result "Memory" "PASS" "Memory usage: ${MEMORY_USAGE}%"
        elif [ "$MEMORY_USAGE" -lt 90 ]; then
            log_result "Memory" "WARN" "Memory usage: ${MEMORY_USAGE}% (getting high)"
        else
            log_result "Memory" "FAIL" "Memory usage: ${MEMORY_USAGE}% (critical)"
        fi
    else
        log_result "Memory" "WARN" "free command not available"
    fi
}

# Check 10: System Load
check_system_load() {
    echo ""
    echo "[10/10] Checking System Load..."
    echo "-------------------------------"

    if command -v uptime &> /dev/null; then
        LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
        CPU_COUNT=$(nproc 2>/dev/null || echo 1)
        LOAD_THRESHOLD=$(echo "$CPU_COUNT * 2" | bc 2>/dev/null || echo 2)

        log_result "System Load" "PASS" "Load average: $LOAD (CPUs: $CPU_COUNT)"

        # Compare load to threshold
        if command -v bc &> /dev/null; then
            if [ "$(echo "$LOAD > $LOAD_THRESHOLD" | bc)" -eq 1 ]; then
                log_result "System Load" "WARN" "Load is high: $LOAD > $LOAD_THRESHOLD"
            fi
        fi
    else
        log_result "System Load" "WARN" "uptime command not available"
    fi
}

# Generate summary
generate_summary() {
    echo ""
    echo "========================================================================"
    echo "  Health Check Summary"
    echo "========================================================================"
    echo ""

    TOTAL=$((PASSED + FAILED + WARNINGS))

    echo "Total Checks: $TOTAL"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    echo ""

    # Calculate health percentage
    HEALTH_PCT=$((PASSED * 100 / TOTAL))

    echo "Health Score: ${HEALTH_PCT}%"
    echo ""

    # Overall status
    if [ "$FAILED" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
        echo -e "${GREEN}✓ SYSTEM STATUS: HEALTHY${NC}"
        OVERALL_STATUS="HEALTHY"
    elif [ "$FAILED" -eq 0 ]; then
        echo -e "${YELLOW}⚠ SYSTEM STATUS: HEALTHY WITH WARNINGS${NC}"
        OVERALL_STATUS="HEALTHY_WITH_WARNINGS"
    else
        echo -e "${RED}✗ SYSTEM STATUS: UNHEALTHY${NC}"
        OVERALL_STATUS="UNHEALTHY"
    fi

    # Write summary to report
    cat >> "$HEALTH_REPORT" << EOF

========================================================================
SUMMARY
========================================================================

Total Checks: $TOTAL
Passed: $PASSED
Warnings: $WARNINGS
Failed: $FAILED

Health Score: ${HEALTH_PCT}%
Overall Status: $OVERALL_STATUS

EOF

    echo ""
    echo "Full report saved to: $HEALTH_REPORT"
    echo ""

    # Return exit code based on status
    if [ "$OVERALL_STATUS" = "UNHEALTHY" ]; then
        return 1
    else
        return 0
    fi
}

# Main execution
main() {
    check_core_engine
    check_api_services
    check_frontend
    check_databases
    check_message_queues
    check_monitoring
    check_docker
    check_disk_space
    check_memory
    check_system_load
    generate_summary
}

main "$@"
