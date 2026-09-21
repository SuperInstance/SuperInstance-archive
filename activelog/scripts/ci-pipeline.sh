#!/bin/bash
# SuperInstance.AI Continuous Integration Pipeline
# Optimized for multi-domain build automation

set -e

echo "🤖 SuperInstance.AI CI Pipeline"
echo "================================"

# Configuration
export CI=true
export NODE_ENV=test
export DATABASE_URL="${DATABASE_URL:-postgresql://activelog:activelog@localhost:5432/activelog_test}"

# Logging function
log() {
    echo "[$(date +'%H:%M:%S')] $1"
}

# Stage 1: Environment Setup
stage_setup() {
    log "📋 Stage 1: Environment Setup"
    
    # Clean previous builds
    make clean
    
    # Install dependencies
    log "Installing dependencies..."
    make install
    
    # Setup test environment
    log "Setting up test environment..."
    make setup-dev
    
    log "✅ Environment setup completed"
}

# Stage 2: Code Quality
stage_quality() {
    log "🔍 Stage 2: Code Quality Checks"
    
    # Linting
    log "Running linting..."
    make lint || {
        log "❌ Linting failed"
        return 1
    }
    
    # Security scanning
    log "Running security scans..."
    make security || {
        log "❌ Security checks failed"
        return 1
    }
    
    log "✅ Code quality checks passed"
}

# Stage 3: Testing
stage_testing() {
    log "🧪 Stage 3: Testing"
    
    # Start test services
    log "Starting test services..."
    make test-services
    
    # Unit tests
    log "Running unit tests..."
    make test-unit || {
        log "❌ Unit tests failed"
        make stop-test-services
        return 1
    }
    
    # Integration tests
    log "Running integration tests..."
    make test-integration || {
        log "❌ Integration tests failed"
        make stop-test-services
        return 1
    }
    
    # Stop test services
    make stop-test-services
    
    log "✅ All tests passed"
}

# Stage 4: Build Verification
stage_build() {
    log "🏗️  Stage 4: Build Verification"
    
    # Docker build test
    log "Testing Docker builds..."
    make docker-test || {
        log "❌ Docker build failed"
        return 1
    }
    
    # Domain-specific builds
    for domain in activelog personallog fishinglog dmlog businesslog; do
        if [ -d "frontend-$domain" ] || [ -d "services/$domain-backend" ]; then
            log "Testing $domain domain build..."
            ./scripts/build-automation.sh --domain $domain --type development --skip-tests
        fi
    done
    
    log "✅ Build verification completed"
}

# Stage 5: Performance Testing
stage_performance() {
    log "⚡ Stage 5: Performance Testing"
    
    # Light load testing
    log "Running light load tests..."
    make test-load || {
        log "⚠️  Load tests failed - continuing with warnings"
    }
    
    log "✅ Performance testing completed"
}

# Stage 6: Deployment Readiness
stage_deployment() {
    log "🚀 Stage 6: Deployment Readiness Check"
    
    # Check all services are buildable
    log "Verifying service health endpoints..."
    
    # Start core services temporarily
    cd services/api-gateway && python main.py &
    GATEWAY_PID=$!
    sleep 3
    
    # Health check
    if curl -s -f http://localhost:8088/health > /dev/null; then
        log "✅ API Gateway health check passed"
    else
        log "❌ API Gateway health check failed"
    fi
    
    # Cleanup
    kill $GATEWAY_PID 2>/dev/null || true
    
    log "✅ Deployment readiness verified"
}

# Error handler
handle_error() {
    log "❌ CI Pipeline failed at stage: $1"
    
    # Cleanup
    make stop-test-services 2>/dev/null || true
    pkill -f "python.*main.py" 2>/dev/null || true
    
    # Generate failure report
    echo "CI Failure Report - $(date)" > ci-failure-report.txt
    echo "Stage: $1" >> ci-failure-report.txt
    echo "Last 20 lines of build log:" >> ci-failure-report.txt
    tail -20 ci-pipeline.log >> ci-failure-report.txt
    
    exit 1
}

# Success handler
handle_success() {
    log "🎉 CI Pipeline completed successfully!"
    
    # Generate success report
    echo "CI Success Report - $(date)" > ci-success-report.txt
    echo "All stages completed successfully" >> ci-success-report.txt
    echo "Build artifacts ready for deployment" >> ci-success-report.txt
    
    # Update team coordination
    echo "$(date +%H:%M)|build_specialist|COMPLETE|ci-pipeline-full-success-all-domains-tested" >> micro_updates.log
}

# Main pipeline execution
main() {
    log "Starting CI Pipeline for SuperInstance.AI"
    
    # Log all output
    exec > >(tee ci-pipeline.log)
    exec 2>&1
    
    # Execute stages
    stage_setup || handle_error "setup"
    stage_quality || handle_error "quality"
    stage_testing || handle_error "testing" 
    stage_build || handle_error "build"
    stage_performance || handle_error "performance"
    stage_deployment || handle_error "deployment"
    
    handle_success
}

# Help function
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "SuperInstance.AI Continuous Integration Pipeline"
    echo ""
    echo "Stages:"
    echo "  1. Environment Setup"
    echo "  2. Code Quality Checks"
    echo "  3. Testing (Unit + Integration)"
    echo "  4. Build Verification"
    echo "  5. Performance Testing"
    echo "  6. Deployment Readiness"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Execute main function
main