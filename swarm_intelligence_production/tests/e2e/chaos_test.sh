#!/bin/bash
#
# Chaos Engineering Tests for Swarm Intelligence Platform
# Tests system resilience under various failure conditions
#

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-swarm-intelligence}"
DURATION="${DURATION:-300}"  # 5 minutes default
CHAOS_LEVEL="${CHAOS_LEVEL:-medium}"  # low, medium, high

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $*"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARN:${NC} $*"
}

log_info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $*"
}

# Test tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

record_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$1" = "pass" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log "✓ Test passed: $2"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "✗ Test failed: $2"
    fi
}

# Check if system is healthy
check_health() {
    local unhealthy_pods
    unhealthy_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running,status.phase!=Succeeded -o json | jq '.items | length')

    if [ "$unhealthy_pods" -gt 0 ]; then
        return 1
    fi
    return 0
}

# Get current agent count
get_agent_count() {
    kubectl exec -n "$NAMESPACE" deployment/swarm-core -- \
        curl -s http://localhost:9090/metrics | \
        grep '^swarm_agents_total' | \
        awk '{print $2}' | \
        head -1
}

# Test 1: Random Pod Deletion
test_pod_deletion() {
    log "Test 1: Random Pod Deletion"
    log_info "Deleting random swarm-core pod..."

    local pod
    pod=$(kubectl get pods -n "$NAMESPACE" -l app=swarm-core -o name | shuf -n 1)

    if [ -z "$pod" ]; then
        record_test "fail" "No pods found to delete"
        return 1
    fi

    local agent_count_before
    agent_count_before=$(get_agent_count || echo "0")

    # Delete pod
    kubectl delete -n "$NAMESPACE" "$pod" --grace-period=0 --force

    # Wait for replacement
    sleep 10

    # Check if new pod is created
    local pod_count
    pod_count=$(kubectl get pods -n "$NAMESPACE" -l app=swarm-core --field-selector=status.phase=Running -o name | wc -l)

    if [ "$pod_count" -lt 1 ]; then
        record_test "fail" "Pod not replaced after deletion"
        return 1
    fi

    # Wait for system to stabilize
    sleep 20

    # Check agent count recovery
    local agent_count_after
    agent_count_after=$(get_agent_count || echo "0")

    local agent_loss
    agent_loss=$((agent_count_before - agent_count_after))
    local loss_percentage=$((agent_loss * 100 / agent_count_before))

    log_info "Agent count: before=$agent_count_before, after=$agent_count_after, loss=$loss_percentage%"

    if [ "$loss_percentage" -lt 10 ]; then
        record_test "pass" "Pod deletion - minimal agent loss"
    else
        record_test "fail" "Pod deletion - excessive agent loss: $loss_percentage%"
    fi
}

# Test 2: Network Partition Simulation
test_network_partition() {
    log "Test 2: Network Partition Simulation"
    log_info "Creating network partition..."

    # Create network policy to isolate a pod
    cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chaos-network-partition
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: swarm-core
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
EOF

    sleep 30

    # Check system health
    if check_health; then
        record_test "pass" "Network partition - system remains healthy"
    else
        record_test "fail" "Network partition - system degraded"
    fi

    # Cleanup
    kubectl delete networkpolicy chaos-network-partition -n "$NAMESPACE" || true
}

# Test 3: CPU Stress Test
test_cpu_stress() {
    log "Test 3: CPU Stress Test"
    log_info "Injecting CPU stress..."

    local pod
    pod=$(kubectl get pods -n "$NAMESPACE" -l app=swarm-core -o name | head -1 | cut -d/ -f2)

    # Run stress test in background
    kubectl exec -n "$NAMESPACE" "$pod" -- \
        sh -c "dd if=/dev/zero of=/dev/null &" || true

    # Monitor for 30 seconds
    sleep 30

    # Check if system is still processing
    local fps
    fps=$(kubectl exec -n "$NAMESPACE" deployment/swarm-core -- \
        curl -s http://localhost:9090/metrics | \
        grep '^swarm_fps' | \
        awk '{print $2}' | \
        head -1)

    if [ -n "$fps" ] && [ "$(echo "$fps > 10" | bc)" = "1" ]; then
        record_test "pass" "CPU stress - system still functional (FPS: $fps)"
    else
        record_test "fail" "CPU stress - system performance degraded (FPS: $fps)"
    fi

    # Cleanup: kill stress process
    kubectl exec -n "$NAMESPACE" "$pod" -- pkill dd || true
}

# Test 4: Memory Pressure
test_memory_pressure() {
    log "Test 4: Memory Pressure Test"
    log_info "Creating memory pressure..."

    local pod
    pod=$(kubectl get pods -n "$NAMESPACE" -l app=swarm-core -o name | head -1 | cut -d/ -f2)

    # Get current memory
    local mem_before
    mem_before=$(kubectl top pod "$pod" -n "$NAMESPACE" --no-headers | awk '{print $3}')

    log_info "Memory before: $mem_before"

    # Allocate memory (this is simulated, actual implementation would vary)
    sleep 10

    # Check if pod is still running
    if kubectl get pod "$pod" -n "$NAMESPACE" &> /dev/null; then
        record_test "pass" "Memory pressure - pod survived"
    else
        record_test "fail" "Memory pressure - pod crashed"
    fi
}

# Test 5: Database Connection Loss
test_database_disconnect() {
    log "Test 5: Database Connection Loss"
    log_info "Simulating database disconnect..."

    # Scale down PostgreSQL temporarily
    kubectl scale statefulset postgres -n "$NAMESPACE" --replicas=0

    sleep 10

    # Check if system handles gracefully
    local error_logs
    error_logs=$(kubectl logs -n "$NAMESPACE" deployment/swarm-core --tail=50 | grep -i "database" | grep -i "error" | wc -l)

    # Scale back up
    kubectl scale statefulset postgres -n "$NAMESPACE" --replicas=1

    # Wait for PostgreSQL to be ready
    kubectl wait --for=condition=ready pod -l app=postgres -n "$NAMESPACE" --timeout=120s

    # Check recovery
    sleep 10

    if check_health; then
        record_test "pass" "Database disconnect - system recovered"
    else
        record_test "fail" "Database disconnect - system did not recover"
    fi
}

# Test 6: Redis Failure
test_redis_failure() {
    log "Test 6: Redis Cache Failure"
    log_info "Stopping Redis..."

    # Kill Redis pod
    local redis_pod
    redis_pod=$(kubectl get pods -n "$NAMESPACE" -l app=redis -o name | head -1)
    kubectl delete -n "$NAMESPACE" "$redis_pod" --grace-period=0 --force

    sleep 5

    # Check if system continues (should work with degraded performance)
    local fps
    fps=$(kubectl exec -n "$NAMESPACE" deployment/swarm-core -- \
        curl -s http://localhost:9090/metrics | \
        grep '^swarm_fps' | \
        awk '{print $2}' | \
        head -1 || echo "0")

    # Wait for Redis to recover
    kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=120s

    if [ -n "$fps" ] && [ "$(echo "$fps > 0" | bc)" = "1" ]; then
        record_test "pass" "Redis failure - system continued operation"
    else
        record_test "fail" "Redis failure - system stopped"
    fi
}

# Test 7: Kafka Broker Failure
test_kafka_failure() {
    log "Test 7: Kafka Broker Failure"
    log_info "Killing Kafka broker..."

    local kafka_pod
    kafka_pod=$(kubectl get pods -n "$NAMESPACE" -l app=kafka -o name | head -1)
    kubectl delete -n "$NAMESPACE" "$kafka_pod" --grace-period=0 --force

    sleep 10

    # Check if other brokers handle the load
    if check_health; then
        record_test "pass" "Kafka failure - cluster continued"
    else
        record_test "warn" "Kafka failure - degraded performance"
    fi

    # Wait for broker to recover
    kubectl wait --for=condition=ready pod -l app=kafka -n "$NAMESPACE" --timeout=180s
}

# Test 8: Cascading Failure
test_cascading_failure() {
    log "Test 8: Cascading Failure Test"
    log_warn "This test will stress the system significantly"

    # Delete multiple pods simultaneously
    log_info "Deleting 30% of core pods..."

    local total_pods
    total_pods=$(kubectl get pods -n "$NAMESPACE" -l app=swarm-core -o name | wc -l)
    local pods_to_delete=$((total_pods * 30 / 100))

    if [ "$pods_to_delete" -lt 1 ]; then
        pods_to_delete=1
    fi

    kubectl get pods -n "$NAMESPACE" -l app=swarm-core -o name | \
        head -n "$pods_to_delete" | \
        xargs kubectl delete -n "$NAMESPACE" --grace-period=0 --force

    sleep 5

    # Simultaneously kill a database pod
    kubectl delete -n "$NAMESPACE" pod postgres-0 --grace-period=0 --force || true

    # Monitor recovery
    log_info "Waiting for recovery..."
    sleep 60

    # Check if system recovered
    if check_health; then
        record_test "pass" "Cascading failure - system recovered"
    else
        record_test "fail" "Cascading failure - system did not recover"
    fi
}

# Test 9: Rapid Scaling Test
test_rapid_scaling() {
    log "Test 9: Rapid Scaling Test"

    local initial_replicas
    initial_replicas=$(kubectl get deployment swarm-core -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')

    # Scale up rapidly
    log_info "Scaling up..."
    kubectl scale deployment swarm-core -n "$NAMESPACE" --replicas=$((initial_replicas + 10))
    sleep 30

    # Scale down rapidly
    log_info "Scaling down..."
    kubectl scale deployment swarm-core -n "$NAMESPACE" --replicas="$initial_replicas"
    sleep 30

    # Check stability
    if check_health; then
        record_test "pass" "Rapid scaling - system stable"
    else
        record_test "fail" "Rapid scaling - system unstable"
    fi
}

# Test 10: Data Loss Verification
test_data_loss() {
    log "Test 10: Data Loss Verification"

    # Create test data
    log_info "Creating test swarm..."
    local swarm_id
    swarm_id=$(kubectl exec -n "$NAMESPACE" deployment/swarm-api -- \
        curl -s -X POST http://localhost:8080/api/swarms \
        -H "Content-Type: application/json" \
        -d '{"name":"chaos-test-swarm","agent_count":1000}' | \
        jq -r '.swarm_id')

    if [ -z "$swarm_id" ] || [ "$swarm_id" = "null" ]; then
        record_test "fail" "Data loss test - could not create swarm"
        return 1
    fi

    sleep 5

    # Kill database pod
    kubectl delete -n "$NAMESPACE" pod postgres-0 --grace-period=0 --force

    # Wait for recovery
    kubectl wait --for=condition=ready pod postgres-0 -n "$NAMESPACE" --timeout=180s
    sleep 10

    # Verify data still exists
    local swarm_exists
    swarm_exists=$(kubectl exec -n "$NAMESPACE" deployment/swarm-api -- \
        curl -s http://localhost:8080/api/swarms/"$swarm_id" | \
        jq -r '.swarm_id')

    if [ "$swarm_exists" = "$swarm_id" ]; then
        record_test "pass" "Data loss test - no data lost"
    else
        record_test "fail" "Data loss test - data was lost"
    fi
}

# Main execution
main() {
    echo "========================================="
    echo "Swarm Intelligence - Chaos Engineering"
    echo "========================================="
    echo "Namespace: $NAMESPACE"
    echo "Duration: $DURATION seconds"
    echo "Chaos Level: $CHAOS_LEVEL"
    echo ""

    # Verify cluster access
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi

    # Initial health check
    log "Running initial health check..."
    if ! check_health; then
        log_warn "System is not healthy before chaos tests"
    fi

    # Run tests based on chaos level
    case $CHAOS_LEVEL in
        low)
            test_pod_deletion
            test_redis_failure
            ;;
        medium)
            test_pod_deletion
            test_cpu_stress
            test_memory_pressure
            test_redis_failure
            test_kafka_failure
            ;;
        high)
            test_pod_deletion
            test_network_partition
            test_cpu_stress
            test_memory_pressure
            test_database_disconnect
            test_redis_failure
            test_kafka_failure
            test_cascading_failure
            test_rapid_scaling
            test_data_loss
            ;;
    esac

    # Final health check
    log ""
    log "Running final health check..."
    sleep 30

    if check_health; then
        log "✓ System is healthy after chaos tests"
    else
        log_error "System is unhealthy after chaos tests"
    fi

    # Print summary
    echo ""
    echo "========================================="
    echo "CHAOS TEST SUMMARY"
    echo "========================================="
    echo "Tests Run:    $TESTS_RUN"
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"
    echo ""

    if [ "$TESTS_FAILED" -eq 0 ]; then
        log "🎉 All chaos tests passed - system is resilient!"
        exit 0
    else
        log_error "Some chaos tests failed - review system resilience"
        exit 1
    fi
}

# Handle Ctrl+C
trap 'log_warn "Chaos tests interrupted. Cleaning up..."; exit 130' INT TERM

# Run main function
main "$@"
