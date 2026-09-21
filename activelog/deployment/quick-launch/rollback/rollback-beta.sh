#!/bin/bash

# ActiveLog Beta Rollback Script
# Safe rollback procedures for beta environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
CONFIG_DIR="$SCRIPT_DIR/../configs"
BACKUP_DIR="$PROJECT_ROOT/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Load environment configuration
source "$CONFIG_DIR/environment.sh"

# Show usage
usage() {
    echo "ActiveLog Beta Rollback Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --to-version VERSION    Rollback to specific version"
    echo "  --to-backup BACKUP      Rollback to specific backup"
    echo "  --full                  Full rollback (services + database + files)"
    echo "  --services-only         Rollback services only"
    echo "  --database-only         Rollback database only"
    echo "  --list-backups          List available backups"
    echo "  --dry-run               Show what would be done without executing"
    echo "  --force                 Skip confirmation prompts"
    echo "  --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --list-backups"
    echo "  $0 --to-backup backup_20240824_120000"
    echo "  $0 --full --to-version v1.2.0"
    echo "  $0 --services-only --dry-run"
}

# Parse command line arguments
ROLLBACK_TYPE="full"
TARGET_VERSION=""
TARGET_BACKUP=""
DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --to-version)
            TARGET_VERSION="$2"
            shift 2
            ;;
        --to-backup)
            TARGET_BACKUP="$2"
            shift 2
            ;;
        --full)
            ROLLBACK_TYPE="full"
            shift
            ;;
        --services-only)
            ROLLBACK_TYPE="services"
            shift
            ;;
        --database-only)
            ROLLBACK_TYPE="database"
            shift
            ;;
        --list-backups)
            list_backups
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# List available backups
list_backups() {
    log "Available backups:"
    echo ""
    
    if [[ -d "$BACKUP_DIR" ]]; then
        echo "Database backups:"
        find "$BACKUP_DIR" -name "*.sql" -type f -exec basename {} \; | sort -r | head -10
        echo ""
        
        echo "Service backups:"
        find "$BACKUP_DIR" -name "service-backup-*.tar.gz" -type f -exec basename {} \; | sort -r | head -10
        echo ""
        
        echo "Configuration backups:"
        find "$BACKUP_DIR" -name "config-backup-*.tar.gz" -type f -exec basename {} \; | sort -r | head -10
    else
        warn "Backup directory not found: $BACKUP_DIR"
    fi
}

# Create pre-rollback backup
create_pre_rollback_backup() {
    log "Creating pre-rollback backup..."
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    pre_rollback_dir="$BACKUP_DIR/pre-rollback-$timestamp"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would create backup at: $pre_rollback_dir"
        return
    fi
    
    mkdir -p "$pre_rollback_dir"
    
    # Backup current database
    if docker ps | grep -q "activelog-postgres"; then
        log "Backing up current database..."
        docker exec activelog-postgres pg_dump -U activelog activelog_beta > "$pre_rollback_dir/database.sql"
    fi
    
    # Backup current configuration
    log "Backing up current configuration..."
    tar -czf "$pre_rollback_dir/config.tar.gz" -C "$CONFIG_DIR" .
    
    # Backup current logs
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        log "Backing up current logs..."
        tar -czf "$pre_rollback_dir/logs.tar.gz" -C "$PROJECT_ROOT" logs
    fi
    
    log "Pre-rollback backup created at: $pre_rollback_dir"
}

# Stop services safely
stop_services() {
    log "Stopping beta services..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would stop services"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Graceful shutdown with timeout
    timeout 60 docker-compose -f docker-compose.yml -f "$CONFIG_DIR/docker-compose.beta.yml" stop
    
    if [[ $? -ne 0 ]]; then
        warn "Graceful shutdown failed, forcing stop..."
        docker-compose -f docker-compose.yml -f "$CONFIG_DIR/docker-compose.beta.yml" kill
    fi
    
    log "Services stopped"
}

# Rollback database
rollback_database() {
    local backup_file="$1"
    
    log "Rolling back database..."
    
    if [[ ! -f "$backup_file" ]]; then
        error "Database backup file not found: $backup_file"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would restore database from: $backup_file"
        return
    fi
    
    # Start only the database service
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.yml -f "$CONFIG_DIR/docker-compose.beta.yml" up -d postgres
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    sleep 10
    
    # Drop and recreate database
    docker exec activelog-postgres psql -U activelog -c "DROP DATABASE IF EXISTS activelog_beta;"
    docker exec activelog-postgres psql -U activelog -c "CREATE DATABASE activelog_beta;"
    
    # Restore from backup
    docker exec -i activelog-postgres psql -U activelog activelog_beta < "$backup_file"
    
    log "Database rollback completed"
}

# Rollback services
rollback_services() {
    local target_version="$1"
    
    log "Rolling back services to version: $target_version"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would rollback services to: $target_version"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Update image tags to target version
    export IMAGE_TAG="$target_version"
    
    # Pull images for target version
    docker-compose -f docker-compose.yml -f "$CONFIG_DIR/docker-compose.beta.yml" pull
    
    # Start services with target version
    docker-compose -f docker-compose.yml -f "$CONFIG_DIR/docker-compose.beta.yml" up -d
    
    log "Services rollback completed"
}

# Rollback configuration
rollback_configuration() {
    local config_backup="$1"
    
    log "Rolling back configuration..."
    
    if [[ ! -f "$config_backup" ]]; then
        error "Configuration backup not found: $config_backup"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would restore configuration from: $config_backup"
        return
    fi
    
    # Backup current config before rollback
    timestamp=$(date +%Y%m%d_%H%M%S)
    tar -czf "$BACKUP_DIR/config-backup-before-rollback-$timestamp.tar.gz" -C "$CONFIG_DIR" .
    
    # Restore configuration
    tar -xzf "$config_backup" -C "$CONFIG_DIR"
    
    log "Configuration rollback completed"
}

# Health check after rollback
health_check() {
    log "Performing health check..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would perform health check"
        return
    fi
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "http://localhost:8080/health" > /dev/null 2>&1; then
            log "API Gateway is healthy"
            break
        fi
        
        log "Attempt $attempt/$max_attempts: Waiting for services to be ready..."
        sleep 10
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "Health check failed - services did not start properly"
    fi
    
    log "Health check passed"
}

# Confirmation prompt
confirm_rollback() {
    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi
    
    echo ""
    warn "This will rollback the beta environment. Current data may be lost."
    echo "Rollback type: $ROLLBACK_TYPE"
    
    if [[ -n "$TARGET_VERSION" ]]; then
        echo "Target version: $TARGET_VERSION"
    fi
    
    if [[ -n "$TARGET_BACKUP" ]]; then
        echo "Target backup: $TARGET_BACKUP"
    fi
    
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " -r
    
    if [[ ! "$REPLY" =~ ^[Yy]es$ ]]; then
        log "Rollback cancelled by user"
        exit 0
    fi
}

# Main rollback function
main() {
    log "Starting ActiveLog Beta Rollback"
    log "================================="
    
    # Determine backup files
    local db_backup=""
    local config_backup=""
    
    if [[ -n "$TARGET_BACKUP" ]]; then
        db_backup="$BACKUP_DIR/$TARGET_BACKUP.sql"
        config_backup="$BACKUP_DIR/config-$TARGET_BACKUP.tar.gz"
    else
        # Find latest backup
        db_backup=$(find "$BACKUP_DIR" -name "*.sql" -type f | sort -r | head -1)
        config_backup=$(find "$BACKUP_DIR" -name "config-backup-*.tar.gz" -type f | sort -r | head -1)
    fi
    
    if [[ -z "$TARGET_VERSION" ]]; then
        TARGET_VERSION="latest-stable"
    fi
    
    log "Rollback configuration:"
    log "  Type: $ROLLBACK_TYPE"
    log "  Target version: $TARGET_VERSION"
    log "  Database backup: $(basename "$db_backup" 2>/dev/null || echo "None")"
    log "  Config backup: $(basename "$config_backup" 2>/dev/null || echo "None")"
    log "  Dry run: $DRY_RUN"
    
    confirm_rollback
    
    # Create pre-rollback backup
    create_pre_rollback_backup
    
    # Stop services
    stop_services
    
    # Perform rollback based on type
    case "$ROLLBACK_TYPE" in
        "full")
            if [[ -n "$db_backup" ]]; then
                rollback_database "$db_backup"
            fi
            if [[ -n "$config_backup" ]]; then
                rollback_configuration "$config_backup"
            fi
            rollback_services "$TARGET_VERSION"
            ;;
        "services")
            rollback_services "$TARGET_VERSION"
            ;;
        "database")
            if [[ -n "$db_backup" ]]; then
                rollback_database "$db_backup"
            else
                error "No database backup found for rollback"
            fi
            ;;
    esac
    
    # Health check
    health_check
    
    log "================================="
    log "Beta rollback completed successfully!"
    log "Access points:"
    log "  - Frontend: http://localhost:3000"
    log "  - API: http://localhost:8080"
    log "  - Admin Panel: http://localhost:3000/admin"
}

# Handle script interruption
cleanup() {
    warn "Rollback interrupted. Check system state manually."
    exit 1
}

trap cleanup SIGINT SIGTERM

# Run main function
main "$@"