#!/bin/bash

# ActiveLog Beta Deployment Script
# One-click deployment for beta environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
CONFIG_DIR="$SCRIPT_DIR/../configs"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Load configuration
load_config() {
    if [[ ! -f "$CONFIG_DIR/beta-config.yml" ]]; then
        error "Beta configuration not found at $CONFIG_DIR/beta-config.yml"
    fi
    
    source "$CONFIG_DIR/environment.sh"
    
    log "Configuration loaded for environment: $ENVIRONMENT"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install Docker."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose not found. Please install Docker Compose."
    fi
    
    # Check available disk space (require at least 5GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    required_space=5242880 # 5GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        error "Insufficient disk space. Required: 5GB, Available: $(($available_space/1024/1024))GB"
    fi
    
    # Check if ports are available
    check_port() {
        if netstat -tuln | grep -q ":$1 "; then
            warn "Port $1 is already in use"
            return 1
        fi
        return 0
    }
    
    check_port 8080 # API Gateway
    check_port 3000 # Frontend
    check_port 5432 # PostgreSQL
    check_port 6379 # Redis
    
    log "Pre-deployment checks completed"
}

# Database migration safety
safe_database_migration() {
    log "Starting safe database migration..."
    
    # Backup database before migration
    backup_file="$PROJECT_ROOT/backups/pre-migration-$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p "$PROJECT_ROOT/backups"
    
    if docker ps | grep -q "activelog-postgres"; then
        log "Creating database backup..."
        docker exec activelog-postgres pg_dump -U activelog activelog > "$backup_file"
        log "Database backup created: $backup_file"
    fi
    
    # Run migration with rollback capability
    log "Running database migrations..."
    python3 "$SCRIPT_DIR/../migrations/migration-runner.py" --environment=beta --backup-file="$backup_file"
    
    log "Database migration completed safely"
}

# Deploy services with environment separation
deploy_services() {
    log "Deploying services for beta environment..."
    
    cd "$PROJECT_ROOT"
    
    # Set environment variables
    export ENVIRONMENT=beta
    export COMPOSE_PROJECT_NAME=activelog-beta
    export API_PORT=8080
    export FRONTEND_PORT=3000
    export DB_HOST=localhost
    export DB_PORT=5432
    export REDIS_HOST=localhost
    export REDIS_PORT=6379
    
    # Deploy with beta-specific configuration
    docker-compose -f docker-compose.yml -f "$CONFIG_DIR/docker-compose.beta.yml" up -d
    
    log "Waiting for services to start..."
    sleep 30
    
    # Health checks
    check_service_health() {
        local service=$1
        local url=$2
        local max_attempts=30
        local attempt=1
        
        while [[ $attempt -le $max_attempts ]]; do
            if curl -f -s "$url" > /dev/null 2>&1; then
                log "$service is healthy"
                return 0
            fi
            
            log "Attempt $attempt/$max_attempts: Waiting for $service to be ready..."
            sleep 5
            ((attempt++))
        done
        
        error "$service failed to start within timeout"
    }
    
    check_service_health "API Gateway" "http://localhost:8080/health"
    check_service_health "Frontend" "http://localhost:3000"
    
    log "All services deployed and healthy"
}

# Configure feature flags for beta
configure_feature_flags() {
    log "Configuring feature flags for beta environment..."
    
    # Apply beta-specific feature flags
    python3 "$SCRIPT_DIR/../configs/feature-flags-manager.py" \
        --environment=beta \
        --config="$CONFIG_DIR/beta-feature-flags.json"
    
    log "Feature flags configured"
}

# Set up beta user management
setup_beta_users() {
    log "Setting up beta user management..."
    
    # Initialize beta user database
    python3 "$SCRIPT_DIR/../beta-management/beta-user-manager.py" --init
    
    # Set up invite system
    python3 "$SCRIPT_DIR/../beta-management/invite-system.py" --setup
    
    log "Beta user management configured"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring for beta environment..."
    
    # Deploy monitoring stack
    docker-compose -f "$CONFIG_DIR/docker-compose.monitoring.yml" up -d
    
    # Configure alerts for beta
    python3 "$SCRIPT_DIR/../monitoring/alert-manager.py" --environment=beta
    
    log "Monitoring configured"
}

# Main deployment function
main() {
    log "Starting ActiveLog Beta Deployment"
    log "=================================="
    
    load_config
    pre_deployment_checks
    safe_database_migration
    deploy_services
    configure_feature_flags
    setup_beta_users
    setup_monitoring
    
    log "=================================="
    log "Beta deployment completed successfully!"
    log "Access points:"
    log "  - Frontend: http://localhost:3000"
    log "  - API: http://localhost:8080"
    log "  - Admin Panel: http://localhost:3000/admin"
    log "  - Monitoring: http://localhost:3001"
    log ""
    log "Beta Management:"
    log "  - Invite users: ./beta-management/invite-user.sh <email>"
    log "  - Manage NDAs: ./beta-management/nda-manager.sh"
    log "  - View feedback: ./feedback/view-feedback.sh"
    log ""
    log "For rollback: ./rollback/rollback-beta.sh"
}

# Handle script interruption
cleanup() {
    warn "Deployment interrupted. Cleaning up..."
    # Add cleanup logic here
    exit 1
}

trap cleanup SIGINT SIGTERM

# Run main function
main "$@"