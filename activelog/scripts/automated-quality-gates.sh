#!/bin/bash
# SuperInstance.AI Automated Code Quality Gates
# Integrates coder bots for comprehensive quality assurance

set -e

echo "🔍 SuperInstance.AI Automated Quality Gates"
echo "==========================================="

# Configuration
CODER_BOTS_PATH="/home/activeloguser/activelog/dev-tools/coder-bots"
SERVICES_PATH="/home/activeloguser/activelog/services"
QUALITY_REPORT_PATH="/home/activeloguser/activelog/reports/quality"
MIN_HEALTH_SCORE=7.0
MAX_COMPLEXITY_SCORE=8.0

# Ensure directories exist
mkdir -p "$QUALITY_REPORT_PATH"
cd "$CODER_BOTS_PATH"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Quality gate functions
check_service_health() {
    local service_name="$1"
    local service_path="$2"
    
    echo "🔍 Analyzing service: $service_name"
    
    # Run code analyzer bot
    local analysis_output
    analysis_output=$(./bots/code-analyzer/analyze-service.py --service "$service_name" --output-format json 2>/dev/null || echo '{"health_score": 0, "complexity_score": 20}')
    
    # Extract metrics
    local health_score
    local complexity_score
    health_score=$(echo "$analysis_output" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('health_score', 0))" 2>/dev/null || echo "0")
    complexity_score=$(echo "$analysis_output" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('complexity_score', 20))" 2>/dev/null || echo "20")
    
    echo "  📊 Health Score: $health_score/10"
    echo "  🧮 Complexity Score: $complexity_score"
    
    # Quality gates
    local health_pass=false
    local complexity_pass=false
    
    if (( $(echo "$health_score >= $MIN_HEALTH_SCORE" | bc -l) )); then
        echo -e "  ✅ Health Score: ${GREEN}PASS${NC} (≥${MIN_HEALTH_SCORE})"
        health_pass=true
    else
        echo -e "  ❌ Health Score: ${RED}FAIL${NC} (${health_score} < ${MIN_HEALTH_SCORE})"
    fi
    
    if (( $(echo "$complexity_score <= $MAX_COMPLEXITY_SCORE" | bc -l) )); then
        echo -e "  ✅ Complexity: ${GREEN}PASS${NC} (≤${MAX_COMPLEXITY_SCORE})"
        complexity_pass=true
    else
        echo -e "  ❌ Complexity: ${RED}FAIL${NC} (${complexity_score} > ${MAX_COMPLEXITY_SCORE})"
    fi
    
    # Overall service status
    if [[ "$health_pass" == true && "$complexity_pass" == true ]]; then
        echo -e "  🎉 Service Status: ${GREEN}PASS${NC}"
        return 0
    else
        echo -e "  🚨 Service Status: ${RED}FAIL${NC}"
        return 1
    fi
}

check_performance_gates() {
    local service_name="$1"
    local port="$2"
    
    echo "⚡ Performance testing: $service_name (port $port)"
    
    # Performance test
    local response_time
    response_time=$(python3 << EOF
import requests
import time
try:
    start = time.time()
    response = requests.get("http://localhost:$port/health", timeout=5)
    end = time.time()
    response_time_ms = (end - start) * 1000
    print(f"{response_time_ms:.1f}")
except:
    print("5000")  # Timeout/error
EOF
)
    
    echo "  📊 Response Time: ${response_time}ms"
    
    if (( $(echo "$response_time < 500" | bc -l) )); then
        echo -e "  ✅ Performance: ${GREEN}PASS${NC} (<500ms)"
        return 0
    else
        echo -e "  ❌ Performance: ${RED}FAIL${NC} (${response_time}ms ≥ 500ms)"
        return 1
    fi
}

check_security_gates() {
    local service_name="$1"
    local service_path="$2"
    
    echo "🔒 Security scanning: $service_name"
    
    # Basic security checks
    local security_issues=0
    
    # Check for hardcoded secrets (basic pattern matching)
    if grep -r -i "password.*=.*['\"].*['\"]" "$service_path" >/dev/null 2>&1; then
        echo -e "  ❌ Security: ${RED}Hardcoded passwords detected${NC}"
        ((security_issues++))
    fi
    
    # Check for SQL injection patterns
    if grep -r "execute.*%.*s" "$service_path" >/dev/null 2>&1; then
        echo -e "  ⚠️  Security: ${YELLOW}Potential SQL injection risk${NC}"
        ((security_issues++))
    fi
    
    # Check for HTTPS usage in production endpoints
    if grep -r "http://" "$service_path" | grep -v localhost >/dev/null 2>&1; then
        echo -e "  ⚠️  Security: ${YELLOW}HTTP URLs detected (use HTTPS)${NC}"
        ((security_issues++))
    fi
    
    if [[ $security_issues -eq 0 ]]; then
        echo -e "  ✅ Security: ${GREEN}PASS${NC} (No obvious issues)"
        return 0
    else
        echo -e "  🚨 Security: ${RED}FAIL${NC} ($security_issues issues found)"
        return 1
    fi
}

run_unit_tests() {
    local service_name="$1"
    local service_path="$2"
    
    echo "🧪 Running unit tests: $service_name"
    
    # Check if tests exist
    if [[ ! -d "$service_path/tests" && ! -f "$service_path/test_*.py" ]]; then
        echo -e "  ⚠️  Tests: ${YELLOW}SKIP${NC} (No tests found)"
        return 0
    fi
    
    # Run tests if they exist
    cd "$service_path"
    if python -m pytest . -v --tb=short >/dev/null 2>&1; then
        echo -e "  ✅ Tests: ${GREEN}PASS${NC}"
        cd - >/dev/null
        return 0
    else
        echo -e "  ❌ Tests: ${RED}FAIL${NC}"
        cd - >/dev/null
        return 1
    fi
}

generate_quality_report() {
    local timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
    local report_file="$QUALITY_REPORT_PATH/quality_report_${timestamp}.json"
    
    echo "📊 Generating quality report: $report_file"
    
    cat > "$report_file" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "quality_gates": {
    "min_health_score": $MIN_HEALTH_SCORE,
    "max_complexity_score": $MAX_COMPLEXITY_SCORE
  },
  "services": [
EOF
    
    # Add service results to report (simplified for now)
    echo "    {\"note\": \"Quality gate results logged above\"}" >> "$report_file"
    
    cat >> "$report_file" << EOF
  ],
  "summary": {
    "total_services_checked": $services_checked,
    "services_passed": $services_passed,
    "services_failed": $services_failed,
    "overall_status": "$overall_status"
  }
}
EOF
    
    echo "✅ Quality report generated: $report_file"
}

# Main execution
main() {
    echo "🚀 Starting automated quality gates..."
    
    # Service definitions (name:port)
    declare -A services=(
        ["auth"]="8001"
        ["api-gateway"]="8088"
        ["ai-insights"]="8090"
        ["user-management"]="8092"
        ["workout-sessions"]="8093"
        ["nutrition-tracking"]="8094"
        ["businesslog-backend"]="8400"
        ["personallog-backend"]="8100"
        ["fishinglog-backend"]="8200"
        ["dmlog-backend"]="8300"
    )
    
    local services_checked=0
    local services_passed=0
    local services_failed=0
    
    # Check each service
    for service_name in "${!services[@]}"; do
        local service_port="${services[$service_name]}"
        local service_path="$SERVICES_PATH/$service_name"
        
        echo ""
        echo "🔍 ===== Quality Gates for $service_name ====="
        ((services_checked++))
        
        # Skip if service directory doesn't exist
        if [[ ! -d "$service_path" ]]; then
            echo -e "⚠️  Service directory not found: $service_path - ${YELLOW}SKIP${NC}"
            continue
        fi
        
        local gates_passed=0
        local gates_total=4
        
        # Gate 1: Service Health & Complexity
        if check_service_health "$service_name" "$service_path"; then
            ((gates_passed++))
        fi
        
        # Gate 2: Performance
        if check_performance_gates "$service_name" "$service_port"; then
            ((gates_passed++))
        fi
        
        # Gate 3: Security
        if check_security_gates "$service_name" "$service_path"; then
            ((gates_passed++))
        fi
        
        # Gate 4: Unit Tests
        if run_unit_tests "$service_name" "$service_path"; then
            ((gates_passed++))
        fi
        
        # Service summary
        echo "📋 Gates Summary: $gates_passed/$gates_total passed"
        
        if [[ $gates_passed -eq $gates_total ]]; then
            echo -e "🎉 Overall: ${GREEN}SERVICE PASSED${NC}"
            ((services_passed++))
        else
            echo -e "🚨 Overall: ${RED}SERVICE FAILED${NC}"
            ((services_failed++))
        fi
    done
    
    # Final summary
    echo ""
    echo "🏁 ===== FINAL QUALITY GATES SUMMARY ====="
    echo "📊 Services Checked: $services_checked"
    echo -e "✅ Services Passed: ${GREEN}$services_passed${NC}"
    echo -e "❌ Services Failed: ${RED}$services_failed${NC}"
    
    local overall_status
    if [[ $services_failed -eq 0 ]]; then
        overall_status="PASSED"
        echo -e "🎉 Overall Status: ${GREEN}$overall_status${NC}"
        echo "✨ All services meet quality standards!"
    else
        overall_status="FAILED"
        echo -e "🚨 Overall Status: ${RED}$overall_status${NC}"
        echo "⚠️  Some services need attention before deployment."
    fi
    
    # Generate report
    generate_quality_report
    
    # Exit with appropriate code
    if [[ $services_failed -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Execute main function
main "$@"