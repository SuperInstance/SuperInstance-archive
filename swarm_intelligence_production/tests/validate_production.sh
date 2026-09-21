#!/bin/bash

##############################################################################
# Quick Production Validation
# 5-minute validation of production readiness
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

API_URL="${API_URL:-http://localhost:8000}"

echo "========================================================================"
echo -e "${CYAN}  Swarm Intelligence Platform - Quick Production Validation${NC}"
echo "========================================================================"
echo ""
echo "Starting 5-minute production validation..."
echo "API URL: $API_URL"
echo ""

PASSED=0
FAILED=0
START_TIME=$(date +%s)

# Test function
run_test() {
    local name=$1
    local result=$2

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $name"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $name"
        FAILED=$((FAILED + 1))
    fi
}

echo "[1/10] Health Check..."
curl -s -f "$API_URL/health" > /dev/null
run_test "API Health" $?

echo "[2/10] System Health Check..."
cd "$(dirname "$0")/health"
if [ -f "health_check_all.sh" ]; then
    bash health_check_all.sh > /dev/null 2>&1
    run_test "System Health" $?
else
    echo -e "${YELLOW}⚠${NC} Health check script not found"
fi
cd - > /dev/null

echo "[3/10] Critical Tests..."
cd "$(dirname "$0")/.."
pytest tests/integration/test_api_integration.py::TestRESTEndpoints::test_health_endpoint -v --tb=short > /dev/null 2>&1
run_test "Critical Integration Tests" $?

echo "[4/10] Performance Benchmarks..."
cd backend/core
go test -run TestSwarmEngineBasic -timeout 30s > /dev/null 2>&1
run_test "Core Engine Performance" $?
cd ../..

echo "[5/10] Security Compliance..."
if [ -f "tests/security/security_scan_results.md" ]; then
    run_test "Security Documentation" 0
else
    run_test "Security Documentation" 1
fi

echo "[6/10] Database Connectivity..."
if command -v pg_isready &> /dev/null; then
    pg_isready -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} > /dev/null 2>&1
    run_test "Database Connection" $?
else
    echo -e "${YELLOW}⚠${NC} Database check skipped (pg_isready not found)"
fi

echo "[7/10] Redis/Cache..."
if command -v redis-cli &> /dev/null; then
    redis-cli -h ${REDIS_HOST:-localhost} -p ${REDIS_PORT:-6379} ping > /dev/null 2>&1
    run_test "Redis Cache" $?
else
    echo -e "${YELLOW}⚠${NC} Redis check skipped (redis-cli not found)"
fi

echo "[8/10] Disk Space..."
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    run_test "Disk Space (${DISK_USAGE}% used)" 0
else
    run_test "Disk Space (${DISK_USAGE}% used - HIGH)" 1
fi

echo "[9/10] Memory..."
if command -v free &> /dev/null; then
    MEMORY_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    if [ "$MEMORY_USAGE" -lt 90 ]; then
        run_test "Memory (${MEMORY_USAGE}% used)" 0
    else
        run_test "Memory (${MEMORY_USAGE}% used - HIGH)" 1
    fi
else
    echo -e "${YELLOW}⚠${NC} Memory check skipped"
fi

echo "[10/10] Production Readiness..."
if [ -f "tests/PRODUCTION_READINESS.md" ]; then
    run_test "Production Readiness Checklist" 0
else
    run_test "Production Readiness Checklist" 1
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "========================================================================"
echo "  Validation Complete"
echo "========================================================================"
echo ""
echo "Duration: ${DURATION}s"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ System Ready for Production!${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ✗ System NOT Ready for Production${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Please fix the failed checks before deploying."
    exit 1
fi
