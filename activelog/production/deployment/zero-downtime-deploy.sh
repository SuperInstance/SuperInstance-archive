#!/bin/bash

# Zero-Downtime Deployment Script for ActiveLog Production
# Implements blue-green deployment strategy with health checks and rollback

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/activeloguser/activelog"
DEPLOY_LOG="/opt/activelog/logs/deployment/deploy_$(date +%Y%m%d_%H%M%S).log"
HEALTH_CHECK_URL="http://localhost/health"
DEPLOY_TIMEOUT=900  # 15 minutes
HEALTH_CHECK_RETRIES=30
ROLLBACK_ENABLED=true

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ensure log directory exists
mkdir -p "$(dirname "$DEPLOY_LOG")"

log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp] $message${NC}" | tee -a "$DEPLOY_LOG"
}

warn() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp] WARNING: $message${NC}" | tee -a "$DEPLOY_LOG"
}

error() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp] ERROR: $message${NC}" | tee -a "$DEPLOY_LOG"
    
    if [ "$ROLLBACK_ENABLED" = true ]; then
        warn "Initiating automatic rollback..."
        rollback_deployment
    fi
    exit 1
}

info() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp] $message${NC}" | tee -a "$DEPLOY_LOG"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running"
    fi
    
    # Check if required images are available or can be built
    if [ -n "${NEW_IMAGE_TAG:-}" ]; then
        if ! docker image inspect "$NEW_IMAGE_TAG" >/dev/null 2>&1; then
            error "Image $NEW_IMAGE_TAG not found"
        fi
    fi
    
    # Check current system health
    if ! curl -sf "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
        error "Current system is not healthy, aborting deployment"
    fi
    
    # Check disk space
    local disk_usage=$(df /opt/activelog | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 85 ]; then
        error "Insufficient disk space: ${disk_usage}% used"
    fi
    
    # Check if deployment lock exists
    if [ -f "/tmp/activelog_deploy.lock" ]; then
        local lock_pid=$(cat /tmp/activelog_deploy.lock)
        if ps -p "$lock_pid" >/dev/null 2>&1; then
            error "Another deployment is in progress (PID: $lock_pid)"
        else
            warn "Removing stale deployment lock"
            rm -f /tmp/activelog_deploy.lock
        fi
    fi
    
    log "Pre-deployment checks passed"
}

# Create deployment lock
create_deployment_lock() {
    echo $$ > /tmp/activelog_deploy.lock
    log "Created deployment lock (PID: $$)"
}

# Remove deployment lock
remove_deployment_lock() {
    rm -f /tmp/activelog_deploy.lock
    log "Removed deployment lock"
}

# Health check function
health_check() {
    local url="$1"
    local max_retries="${2:-30}"
    local retry_interval="${3:-10}"
    
    log "Performing health check on $url"
    
    for ((i=1; i<=max_retries; i++)); do
        if curl -sf "$url" >/dev/null 2>&1; then
            log "Health check passed (attempt $i/$max_retries)"
            return 0
        fi
        
        if [ $i -lt $max_retries ]; then
            info "Health check failed (attempt $i/$max_retries), retrying in ${retry_interval}s..."
            sleep $retry_interval
        fi
    done
    
    error "Health check failed after $max_retries attempts"
    return 1
}

# Database migration
run_database_migrations() {
    log "Running database migrations..."
    
    # Create backup before migration
    cd "$PROJECT_ROOT/production/backup"
    ./backup-manager.sh database
    
    # Run migrations
    docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" exec -T postgres \
        psql -U activelog_admin -d activelog_prod -f /docker-entrypoint-initdb.d/migrations.sql
    
    log "Database migrations completed"
}

# Build new images
build_images() {
    log "Building new Docker images..."
    
    local build_start=$(date +%s)
    
    # Build with build args and cache
    docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" build \
        --parallel \
        --pull \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD)" \
        --build-arg VERSION="${NEW_IMAGE_TAG:-latest}"
    
    local build_end=$(date +%s)
    local build_time=$((build_end - build_start))
    
    log "Image build completed in ${build_time} seconds"
}

# Blue-green deployment
blue_green_deploy() {
    log "Starting blue-green deployment..."
    
    # Determine current and new environment
    local current_env="blue"
    local new_env="green"
    
    if docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" ps | grep -q "green"; then
        current_env="green"
        new_env="blue"
    fi
    
    log "Current environment: $current_env, deploying to: $new_env"
    
    # Start new environment
    log "Starting $new_env environment..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" \
        -f "$PROJECT_ROOT/docker-compose.$new_env.yml" \
        up -d --remove-orphans
    
    # Wait for services to be ready
    log "Waiting for $new_env environment to be ready..."
    sleep 30
    
    # Health check new environment
    local new_health_url="http://localhost:808${new_env:0:1}/health"  # blue=8080, green=8081
    health_check "$new_health_url" 30 10
    
    # Run smoke tests
    run_smoke_tests "$new_env"
    
    # Switch load balancer to new environment
    switch_load_balancer "$current_env" "$new_env"
    
    # Final health check on main URL
    health_check "$HEALTH_CHECK_URL" 10 5
    
    # Stop old environment after successful switch
    log "Stopping $current_env environment..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" \
        -f "$PROJECT_ROOT/docker-compose.$current_env.yml" \
        down
    
    log "Blue-green deployment completed successfully"
}

# Switch load balancer
switch_load_balancer() {
    local old_env="$1"
    local new_env="$2"
    
    log "Switching load balancer from $old_env to $new_env..."
    
    # Update nginx upstream configuration
    local nginx_config="/etc/nginx/conf.d/upstream.conf"
    local new_port="808${new_env:0:1}"  # blue=8080, green=8081
    
    # Create new upstream configuration
    cat > "$nginx_config" << EOF
upstream backend {
    server 127.0.0.1:$new_port max_fails=3 fail_timeout=30s;
    keepalive 32;
}
EOF
    
    # Test nginx configuration
    if ! nginx -t; then
        error "Nginx configuration test failed"
    fi
    
    # Reload nginx
    if ! nginx -s reload; then
        error "Failed to reload nginx"
    fi
    
    log "Load balancer switched to $new_env environment"
}

# Smoke tests
run_smoke_tests() {
    local env="$1"
    local base_url="http://localhost:808${env:0:1}"
    
    log "Running smoke tests against $env environment..."
    
    # Test critical endpoints
    local endpoints=(
        "/health"
        "/api/v1/status"
        "/api/v1/users/me"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="$base_url$endpoint"
        info "Testing endpoint: $url"
        
        if ! curl -sf "$url" >/dev/null 2>&1; then
            error "Smoke test failed for endpoint: $endpoint"
        fi
    done
    
    # Test database connectivity
    if ! docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" exec -T postgres \
        psql -U activelog_admin -d activelog_prod -c "SELECT 1;" >/dev/null 2>&1; then
        error "Database connectivity test failed"
    fi
    
    # Test Redis connectivity
    if ! docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" exec -T redis-master \
        redis-cli ping >/dev/null 2>&1; then
        error "Redis connectivity test failed"
    fi
    
    log "All smoke tests passed"
}

# Rollback deployment
rollback_deployment() {
    log "Starting deployment rollback..."
    
    # Find previous working image tags
    local previous_images=$(docker images --format "table {{.Repository}}\t{{.Tag}}" | grep activelog | head -5)
    log "Available images for rollback:"
    echo "$previous_images"
    
    # Restore from backup if database was migrated
    if [ -f "/tmp/activelog_migration_backup" ]; then
        warn "Restoring database from backup..."
        cd "$PROJECT_ROOT/production/backup"
        local backup_file=$(cat /tmp/activelog_migration_backup)
        ./backup-manager.sh restore-db "$backup_file"
        rm -f /tmp/activelog_migration_backup
    fi
    
    # Restart previous version
    docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" \
        down --remove-orphans
    
    docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" \
        up -d --remove-orphans
    
    # Health check after rollback
    sleep 30
    health_check "$HEALTH_CHECK_URL" 20 10
    
    log "Deployment rollback completed"
}

# Post-deployment tasks
post_deployment_tasks() {
    log "Running post-deployment tasks..."
    
    # Clear application caches
    log "Clearing application caches..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" exec -T redis-master \
        redis-cli FLUSHDB || warn "Failed to clear Redis cache"
    
    # Warm up caches
    log "Warming up caches..."
    local warmup_endpoints=(
        "/api/v1/dashboard"
        "/api/v1/files?limit=10"
        "/api/v1/users/stats"
    )
    
    for endpoint in "${warmup_endpoints[@]}"; do
        curl -sf "$HEALTH_CHECK_URL$endpoint" >/dev/null 2>&1 || warn "Failed to warm up $endpoint"
    done
    
    # Update monitoring annotations
    log "Updating monitoring annotations..."
    local deploy_annotation="{\"time\": $(date +%s)000, \"title\": \"Deployment\", \"text\": \"Successful deployment to production\"}"
    curl -sf -X POST "http://grafana:3000/api/annotations" \
        -H "Content-Type: application/json" \
        -d "$deploy_annotation" >/dev/null 2>&1 || warn "Failed to create monitoring annotation"
    
    # Clean up old Docker images
    log "Cleaning up old Docker images..."
    docker image prune -f || warn "Failed to clean up old images"
    
    # Verify final system state
    log "Verifying final system state..."
    health_check "$HEALTH_CHECK_URL" 5 5
    
    log "Post-deployment tasks completed"
}

# Deployment summary
deployment_summary() {
    log "Deployment Summary"
    echo "==================" | tee -a "$DEPLOY_LOG"
    echo "Deployment completed: $(date)" | tee -a "$DEPLOY_LOG"
    echo "Deployment log: $DEPLOY_LOG" | tee -a "$DEPLOY_LOG"
    echo "New image tag: ${NEW_IMAGE_TAG:-latest}" | tee -a "$DEPLOY_LOG"
    echo "Health check URL: $HEALTH_CHECK_URL" | tee -a "$DEPLOY_LOG"
    
    # Service status
    echo "" | tee -a "$DEPLOY_LOG"
    echo "Service Status:" | tee -a "$DEPLOY_LOG"
    docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" ps | tee -a "$DEPLOY_LOG"
    
    # Resource usage
    echo "" | tee -a "$DEPLOY_LOG"
    echo "Resource Usage:" | tee -a "$DEPLOY_LOG"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | tee -a "$DEPLOY_LOG"
}

# Signal handlers
cleanup() {
    local exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        error "Deployment failed with exit code $exit_code"
    fi
    
    remove_deployment_lock
    
    # Send deployment notification
    local status="SUCCESS"
    if [ $exit_code -ne 0 ]; then
        status="FAILED"
    fi
    
    local message="ActiveLog deployment $status at $(date)"
    echo "$message" | mail -s "ActiveLog Deployment $status" ops@activelog.local 2>/dev/null || true
    
    exit $exit_code
}

trap cleanup EXIT INT TERM

# Main deployment function
main_deployment() {
    local deploy_start=$(date +%s)
    
    log "Starting ActiveLog zero-downtime deployment..."
    
    create_deployment_lock
    pre_deployment_checks
    
    # Optional: Run database migrations
    if [ "${RUN_MIGRATIONS:-}" = "true" ]; then
        run_database_migrations
    fi
    
    # Build new images if needed
    if [ "${BUILD_IMAGES:-}" = "true" ]; then
        build_images
    fi
    
    # Deploy using blue-green strategy
    blue_green_deploy
    
    # Post-deployment tasks
    post_deployment_tasks
    
    local deploy_end=$(date +%s)
    local deploy_time=$((deploy_end - deploy_start))
    
    log "Deployment completed successfully in ${deploy_time} seconds"
    
    deployment_summary
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main_deployment
        ;;
    "rollback")
        ROLLBACK_ENABLED=false  # Prevent recursive rollback
        create_deployment_lock
        rollback_deployment
        remove_deployment_lock
        ;;
    "health-check")
        health_check "${2:-$HEALTH_CHECK_URL}"
        ;;
    "smoke-test")
        run_smoke_tests "${2:-green}"
        ;;
    "status")
        docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" ps
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|health-check|smoke-test|status}"
        echo ""
        echo "Commands:"
        echo "  deploy       - Run zero-downtime deployment"
        echo "  rollback     - Rollback to previous version"
        echo "  health-check - Check application health"
        echo "  smoke-test   - Run smoke tests"
        echo "  status       - Show service status"
        echo ""
        echo "Environment variables:"
        echo "  NEW_IMAGE_TAG   - Docker image tag to deploy"
        echo "  RUN_MIGRATIONS  - Set to 'true' to run database migrations"
        echo "  BUILD_IMAGES    - Set to 'true' to build new images"
        echo "  ROLLBACK_ENABLED - Set to 'false' to disable auto-rollback"
        exit 1
        ;;
esac