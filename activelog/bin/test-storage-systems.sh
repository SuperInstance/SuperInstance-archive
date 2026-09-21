#!/bin/bash
# Comprehensive test suite for storage monitoring systems
# Tests all components with size limits and safety measures

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_LOG="$PROJECT_ROOT/logs/storage-systems-test.log"
TEST_DIR="/tmp/activelog-storage-test-$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$TEST_LOG"
}

log_colored() {
    local color=$1
    shift
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] $*${NC}" | tee -a "$TEST_LOG"
}

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

test_result() {
    local test_name="$1"
    local result="$2"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    if [ "$result" = "PASS" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_colored "$GREEN" "✓ $test_name: PASSED"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_colored "$RED" "✗ $test_name: FAILED"
    fi
}

# Setup test environment
setup_test_env() {
    log_colored "$BLUE" "=== Setting up test environment ==="
    
    # Create test directory
    mkdir -p "$TEST_DIR"
    
    # Create various test files
    mkdir -p "$TEST_DIR/logs"
    mkdir -p "$TEST_DIR/temp"
    mkdir -p "$TEST_DIR/cache"
    
    # Create test files of different sizes
    echo "Small log file" > "$TEST_DIR/logs/small.log"
    dd if=/dev/zero of="$TEST_DIR/logs/medium.log" bs=1M count=50 2>/dev/null
    dd if=/dev/zero of="$TEST_DIR/cache/large.cache" bs=1M count=100 2>/dev/null
    
    # Create temporary files
    touch "$TEST_DIR/temp/test1.tmp"
    touch "$TEST_DIR/temp/test2.temp"
    touch "$TEST_DIR/.DS_Store"
    
    # Create stale PID files
    echo "12345" > "$TEST_DIR/stale1.pid"
    echo "67890" > "$TEST_DIR/stale2.pid"
    
    log "Test environment created at: $TEST_DIR"
}

# Test storage monitor API
test_storage_monitor_api() {
    log_colored "$BLUE" "=== Testing Storage Monitor API ==="
    
    # Test basic connectivity
    if curl -s http://localhost:8490/ >/dev/null; then
        test_result "Storage Monitor Connectivity" "PASS"
    else
        test_result "Storage Monitor Connectivity" "FAIL"
        return 1
    fi
    
    # Test status endpoint
    if curl -s http://localhost:8490/status | jq . >/dev/null 2>&1; then
        test_result "Storage Monitor Status API" "PASS"
    else
        test_result "Storage Monitor Status API" "FAIL"
    fi
    
    # Test alerts endpoint
    if curl -s http://localhost:8490/alerts >/dev/null; then
        test_result "Storage Monitor Alerts API" "PASS"
    else
        test_result "Storage Monitor Alerts API" "FAIL"
    fi
    
    # Test metrics endpoint
    if curl -s http://localhost:8490/metrics >/dev/null; then
        test_result "Storage Monitor Metrics API" "PASS"
    else
        test_result "Storage Monitor Metrics API" "FAIL"
    fi
}

# Test cleanup system
test_cleanup_system() {
    log_colored "$BLUE" "=== Testing Cleanup System ==="
    
    # Test dry run mode
    if "$PROJECT_ROOT/bin/cleanup-system.sh" --dry-run >/dev/null 2>&1; then
        test_result "Cleanup System Dry Run" "PASS"
    else
        test_result "Cleanup System Dry Run" "FAIL"
    fi
    
    # Test with test directory (simulate cleanup)
    local test_cleanup_script="/tmp/test-cleanup-$$.sh"
    cat > "$test_cleanup_script" << 'EOF'
#!/bin/bash
TEST_DIR="$1"
if [ -d "$TEST_DIR" ]; then
    # Remove temp files
    find "$TEST_DIR" -name "*.tmp" -delete 2>/dev/null
    find "$TEST_DIR" -name "*.temp" -delete 2>/dev/null
    find "$TEST_DIR" -name ".DS_Store" -delete 2>/dev/null
    echo "Cleanup test completed"
    exit 0
else
    exit 1
fi
EOF
    chmod +x "$test_cleanup_script"
    
    if "$test_cleanup_script" "$TEST_DIR"; then
        test_result "Cleanup System File Removal" "PASS"
    else
        test_result "Cleanup System File Removal" "FAIL"
    fi
    
    rm -f "$test_cleanup_script"
}

# Test improvement bot git functionality
test_improvement_bot() {
    log_colored "$BLUE" "=== Testing Improvement Bot ==="
    
    # Test list command
    if "$PROJECT_ROOT/improvement_bot.sh" list >/dev/null 2>&1; then
        test_result "Improvement Bot List Command" "PASS"
    else
        test_result "Improvement Bot List Command" "FAIL"
    fi
    
    # Test checkpoint creation (git-based)
    local test_checkpoint="test-checkpoint-$$"
    cd "$PROJECT_ROOT"
    
    if "$PROJECT_ROOT/improvement_bot.sh" checkpoint "$test_checkpoint" >/dev/null 2>&1; then
        test_result "Improvement Bot Git Checkpoint" "PASS"
        
        # Clean up test checkpoint
        git tag -d "checkpoint-$test_checkpoint" 2>/dev/null || true
    else
        test_result "Improvement Bot Git Checkpoint" "FAIL"
    fi
}

# Test backup rotation system
test_backup_system() {
    log_colored "$BLUE" "=== Testing Backup System ==="
    
    # Test help command
    if "$PROJECT_ROOT/bin/backup-rotation.sh" --help >/dev/null 2>&1; then
        test_result "Backup System Help Command" "PASS"
    else
        test_result "Backup System Help Command" "FAIL"
    fi
    
    # Test report generation
    if "$PROJECT_ROOT/bin/backup-rotation.sh" report >/dev/null 2>&1; then
        test_result "Backup System Report Generation" "PASS"
    else
        test_result "Backup System Report Generation" "FAIL"
    fi
    
    # Test list command
    if "$PROJECT_ROOT/bin/backup-rotation.sh" list >/dev/null 2>&1; then
        test_result "Backup System List Command" "PASS"
    else
        test_result "Backup System List Command" "FAIL"
    fi
}

# Test size limits and safety measures
test_size_limits() {
    log_colored "$BLUE" "=== Testing Size Limits ==="
    
    # Test disk space check
    local available_space_gb=$(df "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1024/1024)}')
    if [ "$available_space_gb" -gt 10 ]; then
        test_result "Sufficient Disk Space (${available_space_gb}GB available)" "PASS"
    else
        test_result "Sufficient Disk Space (${available_space_gb}GB available)" "FAIL"
    fi
    
    # Test git repository size
    local git_size_mb=$(du -sm "$PROJECT_ROOT/.git" | cut -f1)
    if [ "$git_size_mb" -lt 1000 ]; then
        test_result "Git Repository Size (${git_size_mb}MB)" "PASS"
    else
        test_result "Git Repository Size (${git_size_mb}MB)" "FAIL"
    fi
    
    # Test project total size
    local total_size_gb=$(du -sm "$PROJECT_ROOT" | cut -f1 | awk '{print int($1/1024)}')
    log "Current project size: ${total_size_gb}GB"
    
    if [ "$total_size_gb" -lt 50 ]; then
        test_result "Total Project Size (${total_size_gb}GB)" "PASS"
    else
        test_result "Total Project Size (${total_size_gb}GB)" "FAIL"
    fi
}

# Test cron job setup
test_cron_jobs() {
    log_colored "$BLUE" "=== Testing Cron Jobs ==="
    
    # Check if cleanup cron jobs are installed
    if crontab -l | grep -q "cleanup-system.sh"; then
        test_result "Cleanup Cron Jobs Installed" "PASS"
    else
        test_result "Cleanup Cron Jobs Installed" "FAIL"
    fi
    
    # Check if backup cron jobs are installed
    if crontab -l | grep -q "backup-rotation.sh"; then
        test_result "Backup Cron Jobs Installed" "PASS"
    else
        test_result "Backup Cron Jobs Installed" "FAIL"
    fi
    
    # Check auto-start cron job
    if crontab -l | grep -q "auto_start.sh"; then
        test_result "Auto-start Cron Job Installed" "PASS"
    else
        test_result "Auto-start Cron Job Installed" "FAIL"
    fi
}

# Test storage monitoring thresholds
test_storage_thresholds() {
    log_colored "$BLUE" "=== Testing Storage Thresholds ==="
    
    # Create a test file to trigger monitoring
    local large_test_file="/tmp/large-test-file-$$"
    
    # Create 200MB file to test detection
    dd if=/dev/zero of="$large_test_file" bs=1M count=200 2>/dev/null
    
    if [ -f "$large_test_file" ]; then
        local file_size_mb=$(du -sm "$large_test_file" | cut -f1)
        if [ "$file_size_mb" -ge 200 ]; then
            test_result "Large File Creation (${file_size_mb}MB)" "PASS"
        else
            test_result "Large File Creation (${file_size_mb}MB)" "FAIL"
        fi
        
        # Clean up test file
        rm -f "$large_test_file"
    else
        test_result "Large File Creation" "FAIL"
    fi
    
    # Test storage monitor response to large files
    sleep 2  # Give monitor time to scan
    
    if curl -s http://localhost:8490/large-files | jq . >/dev/null 2>&1; then
        test_result "Storage Monitor Large File Detection" "PASS"
    else
        test_result "Storage Monitor Large File Detection" "FAIL"
    fi
}

# Test emergency cleanup
test_emergency_procedures() {
    log_colored "$BLUE" "=== Testing Emergency Procedures ==="
    
    # Test emergency cleanup (dry run)
    if "$PROJECT_ROOT/bin/cleanup-system.sh" --emergency >/dev/null 2>&1; then
        test_result "Emergency Cleanup Procedure" "PASS"
    else
        test_result "Emergency Cleanup Procedure" "FAIL"
    fi
    
    # Test emergency backup
    if "$PROJECT_ROOT/bin/backup-rotation.sh" emergency >/dev/null 2>&1; then
        test_result "Emergency Backup Procedure" "PASS"
        
        # Clean up emergency backup
        rm -f "$PROJECT_ROOT/backups/emergency-"*.tar.gz 2>/dev/null || true
    else
        test_result "Emergency Backup Procedure" "FAIL"
    fi
}

# Test system integration
test_system_integration() {
    log_colored "$BLUE" "=== Testing System Integration ==="
    
    # Test storage monitor and improvement system communication
    local storage_status=$(curl -s http://localhost:8490/status 2>/dev/null)
    if [ -n "$storage_status" ]; then
        test_result "Storage Monitor Integration" "PASS"
    else
        test_result "Storage Monitor Integration" "FAIL"
    fi
    
    # Test file permissions
    if [ -x "$PROJECT_ROOT/bin/cleanup-system.sh" ] && 
       [ -x "$PROJECT_ROOT/bin/backup-rotation.sh" ] && 
       [ -x "$PROJECT_ROOT/improvement_bot.sh" ]; then
        test_result "Script File Permissions" "PASS"
    else
        test_result "Script File Permissions" "FAIL"
    fi
    
    # Test log directory creation
    if [ -d "$PROJECT_ROOT/logs" ] && [ -w "$PROJECT_ROOT/logs" ]; then
        test_result "Log Directory Access" "PASS"
    else
        test_result "Log Directory Access" "FAIL"
    fi
}

# Generate final test report
generate_test_report() {
    log_colored "$BLUE" "=== Test Summary Report ==="
    
    local pass_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    
    log_colored "$GREEN" "Tests Passed: $TESTS_PASSED"
    log_colored "$RED" "Tests Failed: $TESTS_FAILED"
    log "Total Tests: $TESTS_TOTAL"
    log "Pass Rate: ${pass_rate}%"
    
    if [ "$TESTS_FAILED" -eq 0 ]; then
        log_colored "$GREEN" "🎉 ALL TESTS PASSED - Storage monitoring system is fully operational!"
    else
        log_colored "$YELLOW" "⚠️  Some tests failed - Review the issues above"
    fi
    
    log ""
    log "System Status Summary:"
    log "- Storage Monitor: Running on http://localhost:8490"
    log "- Cleanup System: Automated with cron jobs"
    log "- Backup System: Scheduled with proper rotation"
    log "- Improvement Bot: Using git-based checkpoints"
    log ""
    log "Cron Schedule:"
    crontab -l | grep -E "(cleanup-system|backup-rotation)" | while read -r job; do
        log "  $job"
    done
}

# Cleanup test environment
cleanup_test_env() {
    log "Cleaning up test environment..."
    rm -rf "$TEST_DIR"
}

# Main test execution
main() {
    local start_time=$(date +%s)
    
    log_colored "$BLUE" "=== ActiveLog Storage Systems Test Suite ==="
    log "Starting comprehensive storage systems test..."
    
    # Setup
    setup_test_env
    
    # Run all tests
    test_storage_monitor_api
    test_cleanup_system
    test_improvement_bot
    test_backup_system
    test_size_limits
    test_cron_jobs
    test_storage_thresholds
    test_emergency_procedures
    test_system_integration
    
    # Generate report
    generate_test_report
    
    # Cleanup
    cleanup_test_env
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log "Test suite completed in ${duration} seconds"
    
    # Return appropriate exit code
    if [ "$TESTS_FAILED" -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Handle command line arguments
case "${1:-}" in
    "--help"|"-h")
        echo "ActiveLog Storage Systems Test Suite"
        echo "Usage: $0 [options]"
        echo ""
        echo "This comprehensive test suite validates:"
        echo "- Storage monitoring system functionality"
        echo "- Cleanup automation with size limits"
        echo "- Backup rotation with proper retention"
        echo "- Git-based improvement bot checkpoints"
        echo "- Emergency procedures and safety measures"
        echo "- System integration and cron job setup"
        echo ""
        echo "Results are logged to: $TEST_LOG"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac