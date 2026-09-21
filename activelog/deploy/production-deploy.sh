#!/bin/bash

# ActiveLog Production Deployment Script
# This script deploys ActiveLog to production environment

set -e

# Configuration
DEPLOY_DIR="/opt/activelog"
BACKUP_DIR="/opt/activelog/backups"
COMPOSE_FILE="docker-compose.prod.yml"
MONITORING_FILE="docker-compose.monitoring.yml"
LOG_FILE="/var/log/activelog-deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Check available disk space (at least 10GB)
    available_space=$(df / | awk 'NR==2{print $4}')
    if [ "$available_space" -lt 10485760 ]; then
        error "Insufficient disk space. At least 10GB required"
    fi
    
    # Check available memory (at least 4GB)
    available_memory=$(free -k | awk 'NR==2{print $7}')
    if [ "$available_memory" -lt 4194304 ]; then
        warning "Less than 4GB of available memory. Performance may be affected"
    fi
    
    success "Prerequisites check passed"
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    
    sudo mkdir -p "$DEPLOY_DIR"
    sudo mkdir -p "$BACKUP_DIR"
    sudo mkdir -p "/var/log/activelog"
    sudo mkdir -p "/etc/activelog"
    
    # Set proper ownership
    sudo chown -R "$(whoami):$(whoami)" "$DEPLOY_DIR"
    sudo chown -R "$(whoami):$(whoami)" "$BACKUP_DIR"
    
    success "Directories setup completed"
}

# Backup existing deployment
backup_existing() {
    if [ -f "$DEPLOY_DIR/$COMPOSE_FILE" ]; then
        log "Creating backup of existing deployment..."
        
        backup_name="activelog-backup-$(date +%Y%m%d-%H%M%S)"
        backup_path="$BACKUP_DIR/$backup_name"
        
        mkdir -p "$backup_path"
        
        # Backup Docker volumes
        docker run --rm -v activelog_postgres_data:/data -v "$backup_path:/backup" ubuntu tar czf /backup/postgres_data.tar.gz -C /data .
        docker run --rm -v activelog_redis_data:/data -v "$backup_path:/backup" ubuntu tar czf /backup/redis_data.tar.gz -C /data .
        docker run --rm -v activelog_prometheus_data:/data -v "$backup_path:/backup" ubuntu tar czf /backup/prometheus_data.tar.gz -C /data .
        docker run --rm -v activelog_grafana_data:/data -v "$backup_path:/backup" ubuntu tar czf /backup/grafana_data.tar.gz -C /data .
        
        # Backup configuration files
        cp -r "$DEPLOY_DIR"/* "$backup_path/" 2>/dev/null || true
        
        success "Backup created at $backup_path"
    else
        log "No existing deployment found, skipping backup"
    fi
}

# Deploy application
deploy_app() {
    log "Deploying ActiveLog application..."
    
    cd "$DEPLOY_DIR"
    
    # Pull latest images
    log "Pulling latest Docker images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Start the application
    log "Starting ActiveLog services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log "Waiting for services to become healthy..."
    timeout=300  # 5 minutes
    elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if docker-compose -f "$COMPOSE_FILE" ps | grep -q "unhealthy"; then
            log "Some services are still starting... (${elapsed}s elapsed)"
            sleep 10
            elapsed=$((elapsed + 10))
        else
            break
        fi
    done
    
    if [ $elapsed -ge $timeout ]; then
        error "Services failed to become healthy within timeout"
    fi
    
    success "ActiveLog application deployed successfully"
}

# Deploy monitoring
deploy_monitoring() {
    log "Deploying monitoring stack..."
    
    cd "$DEPLOY_DIR"
    
    # Start monitoring services
    docker-compose -f "$MONITORING_FILE" up -d
    
    # Wait for monitoring services
    log "Waiting for monitoring services..."
    sleep 30
    
    success "Monitoring stack deployed successfully"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Wait for database to be ready
    sleep 20
    
    # Run migrations
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U activelog -d activelog_prod -f /docker-entrypoint-initdb.d/001_create_indexes.sql
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U activelog -d activelog_prod -f /docker-entrypoint-initdb.d/002_partitioning.sql
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U activelog -d activelog_prod -f /docker-entrypoint-initdb.d/003_materialized_views.sql
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U activelog -d activelog_prod -f /docker-entrypoint-initdb.d/004_backup_restore.sql
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U activelog -d activelog_prod -f /docker-entrypoint-initdb.d/005_vector_optimization.sql
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U activelog -d activelog_prod -f /docker-entrypoint-initdb.d/006_connection_pooling.sql
    
    success "Database migrations completed"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check all services are running
    services=("api-gateway" "auth" "metadata" "file-processor" "ai-orchestrator" "notification" "postgres" "redis" "prometheus" "grafana")
    
    for service in "${services[@]}"; do
        if ! docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            error "Service $service is not running"
        fi
    done
    
    # Check HTTP endpoints
    endpoints=(
        "http://localhost/health"
        "http://localhost/api/health"
        "http://localhost:9090/-/healthy"
        "http://localhost:3001/api/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if ! curl -f "$endpoint" >/dev/null 2>&1; then
            error "Health check failed for $endpoint"
        fi
    done
    
    success "All health checks passed"
}

# Setup SSL certificates (Let's Encrypt)
setup_ssl() {
    log "Setting up SSL certificates..."
    
    if [ ! -f "/etc/nginx/ssl/activelog.crt" ]; then
        log "SSL certificates not found. Setting up Let's Encrypt..."
        
        # Install certbot if not present
        if ! command -v certbot &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y certbot python3-certbot-nginx
        fi
        
        # Generate certificates
        sudo certbot --nginx -d activelog.example.com --non-interactive --agree-tos --email admin@activelog.example.com
        
        # Copy certificates to nginx directory
        sudo mkdir -p /etc/nginx/ssl
        sudo cp /etc/letsencrypt/live/activelog.example.com/fullchain.pem /etc/nginx/ssl/activelog.crt
        sudo cp /etc/letsencrypt/live/activelog.example.com/privkey.pem /etc/nginx/ssl/activelog.key
        
        # Set up auto-renewal
        echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
        
        success "SSL certificates configured"
    else
        log "SSL certificates already exist"
    fi
}

# Setup firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Install ufw if not present
    if ! command -v ufw &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y ufw
    fi
    
    # Configure firewall rules
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH
    sudo ufw allow ssh
    
    # Allow HTTP and HTTPS
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Allow monitoring endpoints (from internal networks only)
    sudo ufw allow from 10.0.0.0/8 to any port 9090
    sudo ufw allow from 10.0.0.0/8 to any port 3001
    sudo ufw allow from 172.16.0.0/12 to any port 9090
    sudo ufw allow from 172.16.0.0/12 to any port 3001
    sudo ufw allow from 192.168.0.0/16 to any port 9090
    sudo ufw allow from 192.168.0.0/16 to any port 3001
    
    # Enable firewall
    sudo ufw --force enable
    
    success "Firewall configured"
}

# Setup log rotation
setup_log_rotation() {
    log "Setting up log rotation..."
    
    cat << EOF | sudo tee /etc/logrotate.d/activelog
/var/log/activelog/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 activelog activelog
    postrotate
        docker-compose -f $DEPLOY_DIR/$COMPOSE_FILE restart fluentd
    endscript
}
EOF
    
    success "Log rotation configured"
}

# Main deployment function
main() {
    log "Starting ActiveLog production deployment..."
    
    check_root
    check_prerequisites
    setup_directories
    backup_existing
    
    # Copy deployment files
    log "Copying deployment files..."
    cp -r . "$DEPLOY_DIR/"
    cd "$DEPLOY_DIR"
    
    # Setup secrets
    log "Setting up secrets..."
    ./secrets/setup-secrets.sh
    
    # Deploy services
    deploy_app
    run_migrations
    deploy_monitoring
    
    # Setup SSL and security
    setup_ssl
    setup_firewall
    setup_log_rotation
    
    # Final health check
    health_check
    
    success "ActiveLog production deployment completed successfully!"
    
    log "Deployment Summary:"
    log "- Application URL: https://activelog.example.com"
    log "- Grafana Dashboard: http://localhost:3001"
    log "- Prometheus: http://localhost:9090"
    log "- Log files: /var/log/activelog/"
    log "- Backup location: $BACKUP_DIR"
    
    log "Next steps:"
    log "1. Update DNS records to point to this server"
    log "2. Configure SMTP settings in secrets/"
    log "3. Set up monitoring alerts"
    log "4. Review security settings"
}

# Run main function
main "$@"