#!/bin/bash

##############################################################################
# Stress Test Script
# Pushes the system to breaking point to identify bottlenecks
##############################################################################

set -e

echo "========================================="
echo "Swarm Intelligence Platform - Stress Test"
echo "========================================="
echo ""

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
MAX_SWARMS=1000
MAX_AGENTS_PER_SWARM=100000
CONCURRENT_REQUESTS=500

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Results
RESULTS_DIR="./stress_test_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo ""

# Function to check if API is available
check_api() {
    echo "[1/8] Checking API availability..."
    if curl -s -f "$API_URL/health" > /dev/null; then
        echo -e "${GREEN}✓ API is available${NC}"
        return 0
    else
        echo -e "${RED}✗ API is not available at $API_URL${NC}"
        return 1
    fi
}

# Function to authenticate
authenticate() {
    echo "[2/8] Authenticating..."

    TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=test@example.com&password=testpass")

    API_KEY=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

    if [ -n "$API_KEY" ]; then
        echo -e "${GREEN}✓ Authentication successful${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Using default API key${NC}"
        API_KEY="default-test-key"
        return 0
    fi
}

# Test 1: Maximum concurrent swarms
test_max_concurrent_swarms() {
    echo ""
    echo "[3/8] Testing maximum concurrent swarms..."
    echo "Creating swarms until system fails..."

    local count=0
    local failed=0
    local swarm_ids=()

    while [ $count -lt $MAX_SWARMS ]; do
        response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/swarms" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"stress-swarm-$count\",\"agent_count\":100}")

        http_code=$(echo "$response" | tail -n1)

        if [ "$http_code" = "200" ]; then
            swarm_id=$(echo "$response" | head -n-1 | grep -o '"swarm_id":"[^"]*' | cut -d'"' -f4)
            swarm_ids+=("$swarm_id")
            count=$((count + 1))

            if [ $((count % 10)) -eq 0 ]; then
                echo "  Created $count swarms..."
            fi
        else
            failed=$((failed + 1))
            if [ $failed -ge 10 ]; then
                echo -e "${YELLOW}⚠ System limit reached at $count swarms${NC}"
                break
            fi
        fi

        sleep 0.1
    done

    echo "Maximum concurrent swarms: $count" > "$RESULTS_DIR/max_concurrent_swarms.txt"
    echo -e "${GREEN}✓ Maximum concurrent swarms: $count${NC}"

    # Cleanup
    echo "  Cleaning up swarms..."
    for swarm_id in "${swarm_ids[@]}"; do
        curl -s -X DELETE "$API_URL/api/v1/swarms/$swarm_id" \
            -H "Authorization: Bearer $API_KEY" > /dev/null
    done
}

# Test 2: Maximum agents per swarm
test_max_agents_per_swarm() {
    echo ""
    echo "[4/8] Testing maximum agents per swarm..."

    local agent_count=1000
    local max_successful=0

    while [ $agent_count -le $MAX_AGENTS_PER_SWARM ]; do
        echo "  Testing $agent_count agents..."

        response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/swarms" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"large-swarm-test\",\"agent_count\":$agent_count}")

        http_code=$(echo "$response" | tail -n1)

        if [ "$http_code" = "200" ]; then
            swarm_id=$(echo "$response" | head -n-1 | grep -o '"swarm_id":"[^"]*' | cut -d'"' -f4)
            max_successful=$agent_count

            # Wait for initialization
            sleep 5

            # Check if swarm is running
            status=$(curl -s "$API_URL/api/v1/swarms/$swarm_id" \
                -H "Authorization: Bearer $API_KEY" | grep -o '"status":"[^"]*' | cut -d'"' -f4)

            if [ "$status" = "RUNNING" ]; then
                echo -e "    ${GREEN}✓ $agent_count agents: SUCCESS${NC}"
            else
                echo -e "    ${YELLOW}⚠ $agent_count agents: CREATED but not RUNNING${NC}"
            fi

            # Cleanup
            curl -s -X DELETE "$API_URL/api/v1/swarms/$swarm_id" \
                -H "Authorization: Bearer $API_KEY" > /dev/null
        else
            echo -e "    ${RED}✗ $agent_count agents: FAILED${NC}"
            break
        fi

        agent_count=$((agent_count * 10))
        sleep 2
    done

    echo "Maximum agents per swarm: $max_successful" > "$RESULTS_DIR/max_agents_per_swarm.txt"
    echo -e "${GREEN}✓ Maximum agents per swarm: $max_successful${NC}"
}

# Test 3: Request throughput limit
test_request_throughput() {
    echo ""
    echo "[5/8] Testing request throughput limits..."
    echo "Sending concurrent requests..."

    # Create temporary script for parallel requests
    cat > "$RESULTS_DIR/parallel_request.sh" << 'EOF'
#!/bin/bash
API_URL=$1
API_KEY=$2
curl -s -w "%{http_code}\n" "$API_URL/health" \
    -H "Authorization: Bearer $API_KEY" > /dev/null
EOF

    chmod +x "$RESULTS_DIR/parallel_request.sh"

    local successful=0
    local failed=0
    local start_time=$(date +%s)

    # Send concurrent requests
    for i in $(seq 1 $CONCURRENT_REQUESTS); do
        "$RESULTS_DIR/parallel_request.sh" "$API_URL" "$API_KEY" &
    done

    wait

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local throughput=$((CONCURRENT_REQUESTS / duration))

    echo "Throughput: $throughput requests/second" > "$RESULTS_DIR/throughput.txt"
    echo -e "${GREEN}✓ Throughput: ~$throughput requests/second${NC}"
}

# Test 4: Memory stress test
test_memory_stress() {
    echo ""
    echo "[6/8] Testing memory limits..."

    # Create large swarm to stress memory
    echo "  Creating large swarm (100,000 agents)..."

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/swarms" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"name":"memory-stress-test","agent_count":100000}')

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
        swarm_id=$(echo "$response" | head -n-1 | grep -o '"swarm_id":"[^"]*' | cut -d'"' -f4)

        sleep 10

        # Check system metrics
        if command -v free &> /dev/null; then
            free -h > "$RESULTS_DIR/memory_usage.txt"
            echo -e "${GREEN}✓ Memory stress test completed${NC}"
        fi

        # Cleanup
        curl -s -X DELETE "$API_URL/api/v1/swarms/$swarm_id" \
            -H "Authorization: Bearer $API_KEY" > /dev/null
    else
        echo -e "${RED}✗ Failed to create large swarm${NC}"
    fi
}

# Test 5: Task queue stress
test_task_queue_stress() {
    echo ""
    echo "[7/8] Testing task queue limits..."

    # Create swarm
    response=$(curl -s -X POST "$API_URL/api/v1/swarms" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"name":"task-queue-test","agent_count":1000}')

    swarm_id=$(echo "$response" | grep -o '"swarm_id":"[^"]*' | cut -d'"' -f4)

    if [ -n "$swarm_id" ]; then
        sleep 3

        echo "  Submitting 1000 tasks..."
        local submitted=0

        for i in $(seq 1 1000); do
            response=$(curl -s -w "%{http_code}" -X POST "$API_URL/api/v1/swarms/$swarm_id/tasks" \
                -H "Authorization: Bearer $API_KEY" \
                -H "Content-Type: application/json" \
                -d "{\"type\":\"compute\",\"payload\":{\"id\":$i}}")

            if [ "$response" = "200" ]; then
                submitted=$((submitted + 1))
            fi
        done

        echo "Tasks submitted: $submitted/1000" > "$RESULTS_DIR/task_queue_stress.txt"
        echo -e "${GREEN}✓ Submitted $submitted/1000 tasks${NC}"

        # Cleanup
        curl -s -X DELETE "$API_URL/api/v1/swarms/$swarm_id" \
            -H "Authorization: Bearer $API_KEY" > /dev/null
    fi
}

# Test 6: Recovery from overload
test_recovery() {
    echo ""
    echo "[8/8] Testing recovery from overload..."

    # Intentionally overload the system
    echo "  Overloading system..."
    for i in $(seq 1 50); do
        curl -s -X POST "$API_URL/api/v1/swarms" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"overload-$i\",\"agent_count\":10000}" > /dev/null &
    done

    wait
    sleep 10

    # Check if system is still responsive
    echo "  Checking system responsiveness..."
    if curl -s -f "$API_URL/health" > /dev/null; then
        echo -e "${GREEN}✓ System recovered from overload${NC}"
        echo "PASS" > "$RESULTS_DIR/recovery_test.txt"
    else
        echo -e "${RED}✗ System did not recover${NC}"
        echo "FAIL" > "$RESULTS_DIR/recovery_test.txt"
    fi
}

# Generate summary report
generate_report() {
    echo ""
    echo "========================================="
    echo "Stress Test Summary"
    echo "========================================="

    cat > "$RESULTS_DIR/summary.md" << EOF
# Stress Test Summary

**Date**: $(date)
**API URL**: $API_URL

## Results

EOF

    if [ -f "$RESULTS_DIR/max_concurrent_swarms.txt" ]; then
        echo "### Maximum Concurrent Swarms" >> "$RESULTS_DIR/summary.md"
        cat "$RESULTS_DIR/max_concurrent_swarms.txt" >> "$RESULTS_DIR/summary.md"
        echo "" >> "$RESULTS_DIR/summary.md"
    fi

    if [ -f "$RESULTS_DIR/max_agents_per_swarm.txt" ]; then
        echo "### Maximum Agents Per Swarm" >> "$RESULTS_DIR/summary.md"
        cat "$RESULTS_DIR/max_agents_per_swarm.txt" >> "$RESULTS_DIR/summary.md"
        echo "" >> "$RESULTS_DIR/summary.md"
    fi

    if [ -f "$RESULTS_DIR/throughput.txt" ]; then
        echo "### Request Throughput" >> "$RESULTS_DIR/summary.md"
        cat "$RESULTS_DIR/throughput.txt" >> "$RESULTS_DIR/summary.md"
        echo "" >> "$RESULTS_DIR/summary.md"
    fi

    echo ""
    echo -e "${GREEN}✓ Full report saved to: $RESULTS_DIR/summary.md${NC}"
    echo ""
}

# Main execution
main() {
    if ! check_api; then
        exit 1
    fi

    authenticate
    test_max_concurrent_swarms
    test_max_agents_per_swarm
    test_request_throughput
    test_memory_stress
    test_task_queue_stress
    test_recovery
    generate_report

    echo "========================================="
    echo -e "${GREEN}Stress test completed!${NC}"
    echo "========================================="
}

main "$@"
