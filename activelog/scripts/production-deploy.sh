#!/bin/bash
# SuperInstance.AI Production Deployment Pipeline
# Complete multi-domain production deployment system

set -e

echo "🚀 SuperInstance.AI Production Deployment"
echo "=========================================="

# Configuration
DOMAIN=${DOMAIN:-"activelog"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
SKIP_TESTS=${SKIP_TESTS:-"false"}
DEPLOY_TYPE=${DEPLOY_TYPE:-"rolling"}  # rolling, blue-green, canary

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check if all required services are healthy
    local required_services=("auth:8001" "api-gateway:8088" "ai-insights:8090")
    
    case $DOMAIN in
        "activelog")
            required_services+=("businesslog-backend:8400")
            ;;
        "all")
            required_services+=("personallog-backend:8100" "fishinglog-backend:8200" "dmlog-backend:8300" "businesslog-backend:8400")
            ;;
    esac
    
    local failed_checks=0
    for service in "${required_services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        if ! curl -s -f http://localhost:$port/health > /dev/null; then
            error "$name service not healthy on port $port"
            ((failed_checks++))
        else
            log "✅ $name service healthy"
        fi
    done
    
    if [ $failed_checks -gt 0 ]; then
        error "Pre-deployment checks failed. Fix services and retry."
        exit 1
    fi
    
    log "✅ All pre-deployment checks passed"
}

# Build and test pipeline
build_and_test() {
    log "Building and testing all components..."
    
    # Run security checks
    if [ "$SKIP_TESTS" != "true" ]; then
        log "Running security scans..."
        make security || {
            error "Security checks failed"
            exit 1
        }
        
        log "Running quick tests..."
        make test-quick || {
            error "Tests failed"
            exit 1
        }
    else
        warn "Skipping tests and security checks"
    fi
    
    # Build frontend
    log "Building frontend..."
    cd frontend-unified
    npm ci --silent
    npm run build
    cd ..
    
    # Build Docker containers
    log "Building production Docker containers..."
    docker-compose -f docker-compose.prod.yml build --parallel
    
    log "✅ Build and test pipeline completed"
}

# Database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Backup database first
    log "Creating database backup..."
    ./scripts/backup-database.sh || {
        warn "Database backup failed, continuing with deployment"
    }
    
    # Run migrations
    if [ -d "migrations" ] && [ -f "migrations/run_migrations.sh" ]; then
        cd migrations
        ./run_migrations.sh
        cd ..
        log "✅ Database migrations completed"
    else
        warn "No migrations found, skipping"
    fi
}

# Deploy services
deploy_services() {
    log "Deploying services for domain: $DOMAIN (type: $DEPLOY_TYPE)"
    
    case $DEPLOY_TYPE in
        "rolling")
            deploy_rolling_update
            ;;
        "blue-green")
            deploy_blue_green
            ;;
        "canary")
            deploy_canary
            ;;
        *)
            error "Unknown deployment type: $DEPLOY_TYPE"
            exit 1
            ;;
    esac
}

# Rolling update deployment
deploy_rolling_update() {
    log "Starting rolling update deployment..."
    
    # Update services one by one
    local services_to_update
    
    case $DOMAIN in
        "activelog")
            services_to_update=("auth" "api-gateway" "ai-insights" "businesslog-backend")
            ;;
        "all")
            services_to_update=("auth" "api-gateway" "ai-insights" "personallog-backend" "fishinglog-backend" "dmlog-backend" "businesslog-backend")
            ;;
        *)
            error "Unknown domain: $DOMAIN"
            exit 1
            ;;
    esac
    
    for service in "${services_to_update[@]}"; do
        log "Updating $service..."
        
        # Graceful restart with health check
        restart_service_with_health_check "$service"
        
        log "✅ $service updated successfully"
        sleep 2  # Brief pause between updates
    done
    
    log "✅ Rolling update completed"
}

# Blue-green deployment
deploy_blue_green() {
    log "Starting blue-green deployment..."
    
    # Start green environment
    log "Starting green environment..."
    docker-compose -f docker-compose.prod.yml -p activelog-green up -d
    
    # Health check green environment
    sleep 10
    local green_healthy=true
    if ! curl -s -f http://localhost:8089/health > /dev/null; then  # Green API gateway
        error "Green environment failed health check"
        green_healthy=false
    fi
    
    if [ "$green_healthy" = true ]; then
        log "Green environment healthy, switching traffic..."
        
        # Update load balancer to point to green
        update_load_balancer_to_green
        
        # Stop blue environment after successful switch
        sleep 5
        docker-compose -f docker-compose.prod.yml -p activelog-blue down
        
        log "✅ Blue-green deployment completed"
    else
        error "Blue-green deployment failed"
        docker-compose -f docker-compose.prod.yml -p activelog-green down
        exit 1
    fi
}

# Canary deployment
deploy_canary() {
    log "Starting canary deployment (10% traffic)..."
    
    # Deploy canary version
    docker-compose -f docker-compose.prod.yml -p activelog-canary up -d
    
    # Configure load balancer for 10% traffic to canary
    configure_canary_traffic
    
    log "Canary deployed, monitoring for 5 minutes..."
    sleep 300  # Monitor for 5 minutes
    
    # Check canary metrics
    if check_canary_metrics; then
        log "Canary metrics good, promoting to full deployment..."
        promote_canary_to_production
        log "✅ Canary deployment promoted to production"
    else
        error "Canary metrics failed, rolling back..."
        rollback_canary
        exit 1
    fi
}

# Helper function to restart service with health check
restart_service_with_health_check() {
    local service=$1
    local port
    
    # Get service port
    case $service in
        "auth") port=8001 ;;
        "api-gateway") port=8088 ;;
        "ai-insights") port=8090 ;;
        "personallog-backend") port=8100 ;;
        "fishinglog-backend") port=8200 ;;
        "dmlog-backend") port=8300 ;;
        "businesslog-backend") port=8400 ;;
        *) error "Unknown service: $service"; return 1 ;;
    esac
    
    # Kill existing process
    pkill -f "$service.*main.py" || true
    sleep 2
    
    # Start new process
    case $service in
        "auth")
            cd services/auth && python main.py &
            ;;
        "api-gateway")
            cd services/api-gateway && python main.py &
            ;;
        "ai-insights")
            cd services/ai-insights && python main.py &
            ;;
        "personallog-backend")
            cd services/personallog-backend && python main_simple.py &
            ;;
        "fishinglog-backend")
            cd services/fishinglog-backend && python main_simple.py &
            ;;
        "dmlog-backend")
            cd services/dmlog-backend && python main.py &
            ;;
        "businesslog-backend")
            cd services/businesslog-backend && python main.py &
            ;;
    esac
    
    # Wait for service to be healthy
    local retries=10
    for i in $(seq 1 $retries); do
        if curl -s -f http://localhost:$port/health > /dev/null; then
            return 0
        fi
        log "Waiting for $service to be healthy... (attempt $i/$retries)"
        sleep 3
    done
    
    error "$service failed to become healthy after restart"
    return 1
}

# Post-deployment verification
post_deployment_verification() {
    log "Running post-deployment verification..."
    
    # Health checks
    ./scripts/service-monitor.sh check
    
    # Smoke tests
    if [ -f "scripts/smoke-tests.sh" ]; then
        ./scripts/smoke-tests.sh
    fi
    
    # Performance baseline
    if [ -f "scripts/performance-baseline.sh" ]; then
        ./scripts/performance-baseline.sh
    fi
    
    log "✅ Post-deployment verification completed"
}

# Rollback function
rollback_deployment() {
    log "Rolling back deployment..."
    
    # Restore from backup
    if [ -f "scripts/restore-from-backup.sh" ]; then
        ./scripts/restore-from-backup.sh
    fi
    
    # Restart previous version
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.yml up -d
    
    error "Deployment rolled back"
}

# Notification system
send_deployment_notification() {
    local status=$1
    local message="SuperInstance.AI Deployment ${status}: Domain=$DOMAIN, Environment=$ENVIRONMENT, Type=$DEPLOY_TYPE"
    
    # Log to coordination system
    echo "$(date +%H:%M)|build_specialist|DEPLOY_${status}|${message}" >> /home/activeloguser/activelog/micro_updates.log
    
    log "$message"
}

# Main execution
main() {
    log "Starting production deployment for $DOMAIN"
    
    # Trap for cleanup on error
    trap 'rollback_deployment; send_deployment_notification "FAILED"' ERR
    
    send_deployment_notification "STARTED"
    
    # Execute deployment pipeline
    pre_deployment_checks
    build_and_test
    run_migrations
    deploy_services
    post_deployment_verification
    
    send_deployment_notification "SUCCESS"
    log "🎉 Production deployment completed successfully!"
    
    # Generate deployment report
    generate_deployment_report
}

# Generate deployment report
generate_deployment_report() {
    local report_file="deployment-report-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$report_file" << EOF
{
  "deployment": {
    "timestamp": "$(date -Iseconds)",
    "domain": "$DOMAIN",
    "environment": "$ENVIRONMENT",
    "type": "$DEPLOY_TYPE",
    "status": "success",
    "services_deployed": $(./scripts/service-monitor.sh check | grep -c "✅"),
    "build_artifacts": {
      "frontend": "frontend-unified/dist",
      "containers": "docker-compose.prod.yml"
    }
  }
}
EOF
    
    log "Deployment report generated: $report_file"
}

# Help function
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "SuperInstance.AI Production Deployment Pipeline"
    echo ""
    echo "Options:"
    echo "  -d, --domain DOMAIN       Target domain (activelog, all)"
    echo "  -e, --env ENVIRONMENT     Environment (production, staging)"
    echo "  -t, --type TYPE           Deployment type (rolling, blue-green, canary)"
    echo "  -s, --skip-tests          Skip tests and security checks"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --domain activelog --type rolling"
    echo "  $0 --domain all --type blue-green --env staging"
    echo "  $0 --domain activelog --type canary --skip-tests"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--type)
            DEPLOY_TYPE="$2"
            shift 2
            ;;
        -s|--skip-tests)
            SKIP_TESTS="true"
            shift
            ;;
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