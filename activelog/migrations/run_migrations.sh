#!/bin/bash

# ActiveLog Database Migration Runner
# This script executes all database migrations in the correct order

set -e  # Exit on any error

# Configuration
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
DB_NAME=${DB_NAME:-"activelog"}
DB_USER=${DB_USER:-"postgres"}
MIGRATION_DIR=$(dirname "$0")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if PostgreSQL is running
check_postgres() {
    log "Checking PostgreSQL connection..."
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        error "Cannot connect to PostgreSQL database"
        error "Please check connection parameters:"
        error "  Host: $DB_HOST"
        error "  Port: $DB_PORT"
        error "  Database: $DB_NAME"
        error "  User: $DB_USER"
        exit 1
    fi
    success "PostgreSQL connection established"
}

# Create migration history table if it doesn't exist
create_migration_table() {
    log "Creating migration history table..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q << 'EOF'
CREATE TABLE IF NOT EXISTS migration_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT,
    checksum VARCHAR(64),
    execution_time INTERVAL
);
EOF
    success "Migration history table ready"
}

# Check if migration has already been applied
is_migration_applied() {
    local version=$1
    local count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM migration_history WHERE version = $version;" 2>/dev/null | tr -d ' ')
    [[ "$count" -gt 0 ]]
}

# Calculate file checksum
calculate_checksum() {
    local file=$1
    if command -v sha256sum > /dev/null; then
        sha256sum "$file" | cut -d' ' -f1
    elif command -v shasum > /dev/null; then
        shasum -a 256 "$file" | cut -d' ' -f1
    else
        # Fallback to a simple checksum
        md5sum "$file" | cut -d' ' -f1
    fi
}

# Execute a single migration
run_migration() {
    local migration_file=$1
    local migration_name=$(basename "$migration_file" .sql)
    local version=$(echo "$migration_name" | grep -o '^[0-9]\+')
    
    log "Checking migration: $migration_name"
    
    if is_migration_applied "$version"; then
        warning "Migration $migration_name already applied, skipping..."
        return 0
    fi
    
    log "Applying migration: $migration_name"
    local start_time=$(date +%s)
    local checksum=$(calculate_checksum "$migration_file")
    
    # Execute the migration
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration_file"; then
        local end_time=$(date +%s)
        local execution_time=$((end_time - start_time))
        
        # Update migration history (if not already done by the migration itself)
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q << EOF
INSERT INTO migration_history (version, name, applied_at, checksum, execution_time) 
VALUES ($version, '$migration_name', NOW(), '$checksum', INTERVAL '$execution_time seconds')
ON CONFLICT (version) DO UPDATE SET
    applied_at = NOW(),
    checksum = '$checksum',
    execution_time = INTERVAL '$execution_time seconds';
EOF
        
        success "Migration $migration_name completed in ${execution_time}s"
        return 0
    else
        error "Migration $migration_name failed!"
        return 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check required extensions
    local extensions=("pg_trgm" "btree_gin" "vector" "pg_cron")
    
    for ext in "${extensions[@]}"; do
        log "Checking extension: $ext"
        if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT 1 FROM pg_extension WHERE extname = '$ext';" | grep -q 1; then
            warning "Extension $ext not found, attempting to install..."
            if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS $ext;"; then
                success "Extension $ext installed"
            else
                error "Failed to install extension $ext"
                error "Please install manually: CREATE EXTENSION IF NOT EXISTS $ext;"
                exit 1
            fi
        else
            success "Extension $ext is available"
        fi
    done
}

# Show migration status
show_status() {
    log "Migration Status:"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT 
        version,
        name,
        applied_at,
        execution_time,
        description
    FROM migration_history 
    ORDER BY version;
    "
}

# Backup database before migrations
backup_database() {
    if [[ "$SKIP_BACKUP" != "true" ]]; then
        log "Creating backup before migrations..."
        local backup_file="/tmp/activelog_pre_migration_$(date +%Y%m%d_%H%M%S).sql"
        
        if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "$backup_file"; then
            success "Backup created: $backup_file"
            echo "BACKUP_FILE=$backup_file"
        else
            error "Backup failed, aborting migrations"
            exit 1
        fi
    else
        warning "Skipping backup (SKIP_BACKUP=true)"
    fi
}

# Main execution
main() {
    echo "========================================"
    echo "  ActiveLog Database Migration Runner"
    echo "========================================"
    echo ""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --status-only)
                STATUS_ONLY=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --skip-backup     Skip database backup before migrations"
                echo "  --status-only     Show migration status and exit"
                echo "  --help           Show this help message"
                echo ""
                echo "Environment variables:"
                echo "  DB_HOST          PostgreSQL host (default: localhost)"
                echo "  DB_PORT          PostgreSQL port (default: 5432)"
                echo "  DB_NAME          Database name (default: activelog)"
                echo "  DB_USER          Database user (default: postgres)"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check connection first
    check_postgres
    
    # Create migration table
    create_migration_table
    
    # Show status if requested
    if [[ "$STATUS_ONLY" == "true" ]]; then
        show_status
        exit 0
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Backup database
    backup_database
    
    # Define migration files in order
    local migrations=(
        "001_create_indexes.sql"
        "002_partitioning.sql"
        "003_materialized_views.sql"
        "004_backup_restore.sql"
        "005_vector_optimization.sql"
        "006_connection_pooling.sql"
    )
    
    log "Starting migrations..."
    local failed_migrations=0
    
    # Run each migration
    for migration in "${migrations[@]}"; do
        local migration_file="$MIGRATION_DIR/$migration"
        
        if [[ ! -f "$migration_file" ]]; then
            error "Migration file not found: $migration_file"
            ((failed_migrations++))
            continue
        fi
        
        if ! run_migration "$migration_file"; then
            ((failed_migrations++))
            if [[ "$CONTINUE_ON_ERROR" != "true" ]]; then
                error "Migration failed, stopping execution"
                break
            fi
        fi
    done
    
    echo ""
    if [[ $failed_migrations -eq 0 ]]; then
        success "All migrations completed successfully!"
    else
        error "$failed_migrations migration(s) failed"
        exit 1
    fi
    
    # Show final status
    echo ""
    show_status
    
    log "Migration process completed"
}

# Execute main function
main "$@"