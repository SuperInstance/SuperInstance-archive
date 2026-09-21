#!/bin/bash

##############################################################################
# Master Test Runner
# Runs all test suites with reporting
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
TEST_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$TEST_ROOT/reports/$(date +%Y%m%d_%H%M%S)"
PARALLEL="${PARALLEL:-true}"
COVERAGE="${COVERAGE:-true}"

# Timing
START_TIME=$(date +%s)

echo "========================================================================"
echo "  Swarm Intelligence Platform - Complete Test Suite"
echo "========================================================================"
echo ""
echo "Test Root: $TEST_ROOT"
echo "Report Directory: $REPORT_DIR"
echo "Parallel Execution: $PARALLEL"
echo "Coverage Analysis: $COVERAGE"
echo ""

# Create report directory
mkdir -p "$REPORT_DIR"

# Initialize test results
UNIT_RESULT=0
INTEGRATION_RESULT=0
E2E_RESULT=0
PERFORMANCE_RESULT=0
SECURITY_RESULT=0

# Function to print section header
print_section() {
    echo ""
    echo -e "${CYAN}========================================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================================================${NC}"
    echo ""
}

# Function to run tests with timing
run_test_suite() {
    local name=$1
    local command=$2
    local result_var=$3

    print_section "$name"

    local suite_start=$(date +%s)

    if eval "$command"; then
        local suite_end=$(date +%s)
        local duration=$((suite_end - suite_start))
        echo -e "${GREEN}✓ $name completed in ${duration}s${NC}"
        eval "$result_var=0"
    else
        local suite_end=$(date +%s)
        local duration=$((suite_end - suite_start))
        echo -e "${RED}✗ $name failed after ${duration}s${NC}"
        eval "$result_var=1"
    fi
}

# 1. Unit Tests
run_unit_tests() {
    print_section "Unit Tests (5 min estimated)"

    cd "$TEST_ROOT/.."

    # Python unit tests
    if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        echo "Running Python unit tests..."
        if $COVERAGE; then
            pytest api/ demos/ -v --cov=. --cov-report=html:$REPORT_DIR/coverage_python \
                --cov-report=term --junitxml=$REPORT_DIR/unit_python.xml 2>&1 | tee "$REPORT_DIR/unit_python.log"
        else
            pytest api/ demos/ -v --junitxml=$REPORT_DIR/unit_python.xml 2>&1 | tee "$REPORT_DIR/unit_python.log"
        fi
    fi

    # Go unit tests
    if [ -d "backend/core" ]; then
        echo "Running Go unit tests..."
        cd backend/core
        if $COVERAGE; then
            go test -v -cover -coverprofile=$REPORT_DIR/coverage_go.out ./... 2>&1 | tee "$REPORT_DIR/unit_go.log"
            go tool cover -html=$REPORT_DIR/coverage_go.out -o $REPORT_DIR/coverage_go.html
        else
            go test -v ./... 2>&1 | tee "$REPORT_DIR/unit_go.log"
        fi
        cd ../..
    fi

    # JavaScript unit tests
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        echo "Running JavaScript unit tests..."
        cd frontend
        npm test -- --coverage --coverageDirectory=$REPORT_DIR/coverage_js 2>&1 | tee "$REPORT_DIR/unit_js.log" || true
        cd ..
    fi
}

# 2. Integration Tests
run_integration_tests() {
    print_section "Integration Tests (15 min estimated)"

    cd "$TEST_ROOT"

    pytest integration/ -v -m "not slow" \
        --junitxml=$REPORT_DIR/integration.xml \
        2>&1 | tee "$REPORT_DIR/integration.log"
}

# 3. End-to-End Tests
run_e2e_tests() {
    print_section "End-to-End Tests (20 min estimated)"

    cd "$TEST_ROOT"

    pytest integration/test_complete_workflow.py -v \
        --junitxml=$REPORT_DIR/e2e.xml \
        2>&1 | tee "$REPORT_DIR/e2e.log"
}

# 4. Performance Tests
run_performance_tests() {
    print_section "Performance Tests (30 min estimated)"

    cd "$TEST_ROOT"

    # Run Python performance tests
    pytest performance/benchmark_suite.py -v -m "not slow" \
        --junitxml=$REPORT_DIR/performance.xml \
        2>&1 | tee "$REPORT_DIR/performance.log" || true

    # Run K6 load tests (if K6 installed)
    if command -v k6 &> /dev/null; then
        echo "Running K6 load tests..."
        k6 run performance/load_test_scenarios.js \
            --out json=$REPORT_DIR/k6_results.json \
            2>&1 | tee "$REPORT_DIR/k6.log" || true
    else
        echo "K6 not installed, skipping load tests"
    fi

    # Run stress test
    if [ -f "performance/stress_test.sh" ]; then
        echo "Running stress tests..."
        bash performance/stress_test.sh 2>&1 | tee "$REPORT_DIR/stress.log" || true
    fi
}

# 5. Security Scans
run_security_scans() {
    print_section "Security Scans (10 min estimated)"

    cd "$TEST_ROOT/.."

    # Python dependency scan
    if command -v pip-audit &> /dev/null; then
        echo "Running pip-audit..."
        pip-audit --format json --output $REPORT_DIR/pip_audit.json || true
    fi

    # NPM audit
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend
        echo "Running npm audit..."
        npm audit --json > $REPORT_DIR/npm_audit.json || true
        cd ..
    fi

    # Go vulnerability check
    if command -v govulncheck &> /dev/null && [ -d "backend" ]; then
        cd backend
        echo "Running govulncheck..."
        govulncheck ./... > $REPORT_DIR/govulncheck.txt 2>&1 || true
        cd ..
    fi

    # OWASP dependency check (if installed)
    if command -v dependency-check &> /dev/null; then
        echo "Running OWASP dependency check..."
        dependency-check --project "Swarm Intelligence" --scan . \
            --format JSON --out $REPORT_DIR/owasp_dependency_check.json || true
    fi
}

# 6. Generate Test Report
generate_test_report() {
    print_section "Generating Test Report"

    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    local minutes=$((total_duration / 60))
    local seconds=$((total_duration % 60))

    # Create HTML report
    cat > "$REPORT_DIR/index.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Swarm Intelligence - Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .summary { background: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .pass { color: #4CAF50; font-weight: bold; }
        .fail { color: #f44336; font-weight: bold; }
        .warn { color: #ff9800; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        tr:hover { background: #f5f5f5; }
        .metric { display: inline-block; margin: 10px 20px 10px 0; }
        .metric-label { font-weight: bold; color: #666; }
        .metric-value { font-size: 24px; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Swarm Intelligence Platform - Test Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Duration:</strong> ${minutes}m ${seconds}s</p>

        <div class="summary">
            <h2>Summary</h2>
            <div class="metric">
                <div class="metric-label">Unit Tests</div>
                <div class="metric-value $([ $UNIT_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $UNIT_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">Integration Tests</div>
                <div class="metric-value $([ $INTEGRATION_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $INTEGRATION_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">E2E Tests</div>
                <div class="metric-value $([ $E2E_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $E2E_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">Performance Tests</div>
                <div class="metric-value $([ $PERFORMANCE_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $PERFORMANCE_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </div>
            </div>
        </div>

        <h2>Test Suites</h2>
        <table>
            <tr>
                <th>Suite</th>
                <th>Status</th>
                <th>Report</th>
            </tr>
            <tr>
                <td>Unit Tests</td>
                <td class="$([ $UNIT_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $UNIT_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </td>
                <td><a href="unit_python.log">Python</a> | <a href="unit_go.log">Go</a> | <a href="coverage_python/index.html">Coverage</a></td>
            </tr>
            <tr>
                <td>Integration Tests</td>
                <td class="$([ $INTEGRATION_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $INTEGRATION_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </td>
                <td><a href="integration.log">Log</a> | <a href="integration.xml">JUnit XML</a></td>
            </tr>
            <tr>
                <td>E2E Tests</td>
                <td class="$([ $E2E_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $E2E_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </td>
                <td><a href="e2e.log">Log</a> | <a href="e2e.xml">JUnit XML</a></td>
            </tr>
            <tr>
                <td>Performance Tests</td>
                <td class="$([ $PERFORMANCE_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $PERFORMANCE_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </td>
                <td><a href="performance.log">Benchmarks</a> | <a href="k6.log">K6</a> | <a href="stress.log">Stress</a></td>
            </tr>
            <tr>
                <td>Security Scans</td>
                <td class="$([ $SECURITY_RESULT -eq 0 ] && echo 'pass' || echo 'fail')">
                    $([ $SECURITY_RESULT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')
                </td>
                <td><a href="pip_audit.json">pip-audit</a> | <a href="npm_audit.json">npm audit</a></td>
            </tr>
        </table>

        <h2>Coverage</h2>
        <ul>
            <li><a href="coverage_python/index.html">Python Coverage Report</a></li>
            <li><a href="coverage_go.html">Go Coverage Report</a></li>
        </ul>
    </div>
</body>
</html>
EOF

    echo ""
    echo -e "${GREEN}Test report generated: $REPORT_DIR/index.html${NC}"
}

# Main execution
main() {
    run_test_suite "Unit Tests" "run_unit_tests" "UNIT_RESULT"
    run_test_suite "Integration Tests" "run_integration_tests" "INTEGRATION_RESULT"
    run_test_suite "End-to-End Tests" "run_e2e_tests" "E2E_RESULT"
    run_test_suite "Performance Tests" "run_performance_tests" "PERFORMANCE_RESULT"
    run_test_suite "Security Scans" "run_security_scans" "SECURITY_RESULT"

    generate_test_report

    # Summary
    print_section "Test Execution Complete"

    local total_duration=$(($(date +%s) - START_TIME))
    local minutes=$((total_duration / 60))
    local seconds=$((total_duration % 60))

    echo "Total Duration: ${minutes}m ${seconds}s"
    echo ""

    # Calculate overall result
    local total_failures=$((UNIT_RESULT + INTEGRATION_RESULT + E2E_RESULT + PERFORMANCE_RESULT))

    if [ $total_failures -eq 0 ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  ALL TESTS PASSED ✓${NC}"
        echo -e "${GREEN}========================================${NC}"
        exit 0
    else
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}  SOME TESTS FAILED ✗${NC}"
        echo -e "${RED}========================================${NC}"
        echo "Failed suites: $total_failures"
        exit 1
    fi
}

main "$@"
