#!/bin/bash

# Comprehensive Backup Manager for ActiveLog Production
# Handles database, Redis, files, configurations, and disaster recovery

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_BASE_DIR="/opt/activelog/backup"
LOG_DIR="/opt/activelog/logs/backup"
CONFIG_DIR="/opt/activelog/production"

# Database settings
PGHOST="${PGHOST:-postgres}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-activelog_prod}"
PGUSER="${PGUSER:-activelog_admin}"

# Redis settings
REDIS_HOST="${REDIS_HOST:-redis-master}"
REDIS_PORT="${REDIS_PORT:-6379}"

# S3 settings for remote backup
S3_BUCKET="${S3_BUCKET:-activelog-backups}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Retention policies
FULL_BACKUP_RETENTION_DAYS=30
INCREMENTAL_BACKUP_RETENTION_DAYS=7
LOG_RETENTION_DAYS=90

# Create directories
mkdir -p "$BACKUP_BASE_DIR"/{database,redis,files,configs,logs,cross-region}
mkdir -p "$LOG_DIR"

# Logging setup
LOGFILE="$LOG_DIR/backup_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp] $message${NC}" | tee -a "$LOGFILE"
}

warn() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp] WARNING: $message${NC}" | tee -a "$LOGFILE"
}

error() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp] ERROR: $message${NC}" | tee -a "$LOGFILE"
    exit 1
}

info() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp] $message${NC}" | tee -a "$LOGFILE"
}

# Check dependencies
check_dependencies() {
    log "Checking backup dependencies..."
    
    command -v pg_dump >/dev/null 2>&1 || error "pg_dump is required but not installed"
    command -v redis-cli >/dev/null 2>&1 || error "redis-cli is required but not installed"
    command -v aws >/dev/null 2>&1 || warn "AWS CLI not found, remote backup disabled"
    command -v gpg >/dev/null 2>&1 || error "GPG is required for encryption"
    command -v rsync >/dev/null 2>&1 || error "rsync is required for file backup"
    
    # Test database connection
    if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c '\q' >/dev/null 2>&1; then
        error "Cannot connect to PostgreSQL database"
    fi
    
    # Test Redis connection
    if ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
        warn "Cannot connect to Redis - Redis backup will be skipped"
    fi
    
    log "Dependencies check completed"
}

# Generate backup metadata
generate_backup_metadata() {
    local backup_type="$1"
    local backup_dir="$2"
    
    cat > "$backup_dir/backup_metadata.json" << EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "server_hostname": "$(hostname)",
    "activelog_version": "$(cat $CONFIG_DIR/VERSION 2>/dev/null || echo 'unknown')",
    "database_host": "$PGHOST",
    "database_name": "$PGDATABASE",
    "redis_host": "$REDIS_HOST",
    "backup_size_bytes": $(du -sb "$backup_dir" | cut -f1),
    "backup_directory": "$backup_dir",
    "retention_days": $FULL_BACKUP_RETENTION_DAYS
}
EOF
}

# Database backup functions
backup_database_full() {
    log "Starting full database backup..."
    
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_BASE_DIR/database/full/$backup_date"
    mkdir -p "$backup_dir"
    
    local dump_file="$backup_dir/activelog_full_$backup_date.sql"
    local compressed_file="$dump_file.gz"
    
    # Create full database dump
    info "Creating database dump..."
    pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
        --verbose --clean --if-exists --create \
        --format=custom --compress=9 \
        --file="$dump_file.backup"
    
    # Also create SQL dump for manual recovery
    pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
        --verbose --clean --if-exists --create \
        > "$dump_file"
    
    # Compress SQL dump
    gzip "$dump_file"
    
    # Create WAL archive for point-in-time recovery
    info "Archiving WAL files..."
    local wal_dir="$backup_dir/wal_archive"
    mkdir -p "$wal_dir"
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
        "SELECT pg_start_backup('activelog_full_backup_$backup_date', false, false);" >/dev/null
    
    # Copy WAL files (this would be done by PostgreSQL archive_command in production)
    if [ -d "/var/lib/postgresql/data/pg_wal" ]; then
        cp /var/lib/postgresql/data/pg_wal/* "$wal_dir/" 2>/dev/null || true
    fi
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
        "SELECT pg_stop_backup(false, true);" >/dev/null
    
    # Generate checksums
    info "Generating checksums..."
    cd "$backup_dir"
    sha256sum *.backup *.gz > checksums.sha256
    
    # Generate metadata
    generate_backup_metadata "database_full" "$backup_dir"
    
    # Encrypt backup
    encrypt_backup "$backup_dir"
    
    log "Full database backup completed: $backup_dir"
    echo "$backup_dir"
}

backup_database_incremental() {
    log "Starting incremental database backup..."
    
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_BASE_DIR/database/incremental/$backup_date"
    mkdir -p "$backup_dir"
    
    # Find last full backup
    local last_full_backup=$(find "$BACKUP_BASE_DIR/database/full" -maxdepth 1 -type d -name "2*" | sort | tail -1)
    if [ -z "$last_full_backup" ]; then
        warn "No full backup found, creating full backup instead"
        backup_database_full
        return
    fi
    
    info "Creating incremental backup since: $(basename "$last_full_backup")"
    
    # Create schema-only dump
    pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
        --schema-only --format=custom \
        --file="$backup_dir/schema_$backup_date.backup"
    
    # Backup data changes since last full backup
    local last_backup_time=$(date -d "$(basename "$last_full_backup" | cut -d'_' -f1,2 | tr '_' ' ')" +%s)
    local where_clause="WHERE created_at > to_timestamp($last_backup_time) OR updated_at > to_timestamp($last_backup_time)"
    
    # Backup modified tables
    local tables=("users" "files" "file_metadata" "activity_logs" "notifications")
    for table in "${tables[@]}"; do
        info "Backing up modified records from $table..."
        psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
            "\\copy (SELECT * FROM $table $where_clause) TO '$backup_dir/${table}_incremental.csv' WITH CSV HEADER;"
    done
    
    # Compress files
    gzip "$backup_dir"/*.csv
    
    # Generate checksums and metadata
    cd "$backup_dir"
    sha256sum * > checksums.sha256
    generate_backup_metadata "database_incremental" "$backup_dir"
    
    # Encrypt backup
    encrypt_backup "$backup_dir"
    
    log "Incremental database backup completed: $backup_dir"
    echo "$backup_dir"
}

# Redis backup functions
backup_redis() {
    log "Starting Redis backup..."
    
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_BASE_DIR/redis/$backup_date"
    mkdir -p "$backup_dir"
    
    # Trigger Redis save
    info "Triggering Redis BGSAVE..."
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE
    
    # Wait for background save to complete
    while [ "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)" == "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)" ]; do
        sleep 1
    done
    
    # Copy RDB file
    local redis_data_dir="/var/lib/redis"
    if [ -f "$redis_data_dir/dump.rdb" ]; then
        cp "$redis_data_dir/dump.rdb" "$backup_dir/redis_$backup_date.rdb"
    else
        warn "Redis RDB file not found at $redis_data_dir/dump.rdb"
    fi
    
    # Backup Redis configuration
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" CONFIG GET "*" > "$backup_dir/redis_config_$backup_date.txt"
    
    # Export all keys as JSON (for human readability)
    info "Exporting Redis keys..."
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --scan | while read key; do
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" DUMP "$key" | base64 > "$backup_dir/keys/${key//\//_}.dump"
    done 2>/dev/null || mkdir -p "$backup_dir/keys"
    
    # Compress backup
    tar -czf "$backup_dir/redis_backup_$backup_date.tar.gz" -C "$backup_dir" .
    
    # Generate checksums and metadata
    cd "$backup_dir"
    sha256sum *.rdb *.txt *.tar.gz > checksums.sha256 2>/dev/null || true
    generate_backup_metadata "redis" "$backup_dir"
    
    # Encrypt backup
    encrypt_backup "$backup_dir"
    
    log "Redis backup completed: $backup_dir"
    echo "$backup_dir"
}

# File storage backup
backup_files() {
    log "Starting file storage backup..."
    
    local backup_type="${1:-incremental}"
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_BASE_DIR/files/$backup_type/$backup_date"
    mkdir -p "$backup_dir"
    
    local source_dir="/opt/activelog/data/files"
    local exclude_file="$SCRIPT_DIR/backup_exclude.txt"
    
    # Create exclude file if it doesn't exist
    cat > "$exclude_file" << 'EOF'
*.tmp
*.temp
.DS_Store
Thumbs.db
*.log
cache/
temp/
EOF
    
    if [ "$backup_type" == "full" ]; then
        info "Creating full file backup..."
        rsync -av --progress --exclude-from="$exclude_file" \
            "$source_dir/" "$backup_dir/files/"
    else
        info "Creating incremental file backup..."
        local last_backup=$(find "$BACKUP_BASE_DIR/files" -name "*.timestamp" | sort | tail -1)
        local newer_than=""
        
        if [ -n "$last_backup" ]; then
            newer_than="--newer-than=$(cat "$last_backup")"
        fi
        
        rsync -av --progress $newer_than --exclude-from="$exclude_file" \
            "$source_dir/" "$backup_dir/files/"
    fi
    
    # Create timestamp file for next incremental backup
    date +%s > "$backup_dir/backup.timestamp"
    
    # Generate file manifest
    info "Generating file manifest..."
    find "$backup_dir/files" -type f -exec sha256sum {} \; > "$backup_dir/file_manifest.sha256"
    
    # Compress backup
    info "Compressing file backup..."
    tar -czf "$backup_dir/files_$backup_type_$backup_date.tar.gz" -C "$backup_dir" files/
    
    # Generate metadata
    generate_backup_metadata "files_$backup_type" "$backup_dir"
    
    # Encrypt backup
    encrypt_backup "$backup_dir"
    
    log "File backup completed: $backup_dir"
    echo "$backup_dir"
}

# Configuration backup
backup_configs() {
    log "Starting configuration backup..."
    
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_BASE_DIR/configs/$backup_date"
    mkdir -p "$backup_dir"
    
    # Backup production configs
    info "Backing up production configurations..."
    rsync -av --progress "$CONFIG_DIR/" "$backup_dir/production/"
    
    # Backup environment files
    if [ -f "/opt/activelog/.env" ]; then
        cp "/opt/activelog/.env" "$backup_dir/"
    fi
    
    # Backup nginx configs
    if [ -d "/etc/nginx" ]; then
        rsync -av --progress "/etc/nginx/" "$backup_dir/nginx/"
    fi
    
    # Backup SSL certificates
    if [ -d "/etc/ssl/activelog" ]; then
        rsync -av --progress "/etc/ssl/activelog/" "$backup_dir/ssl/"
    fi
    
    # Backup crontabs
    crontab -l > "$backup_dir/crontab.txt" 2>/dev/null || true
    
    # Generate manifest
    find "$backup_dir" -type f -exec sha256sum {} \; > "$backup_dir/config_manifest.sha256"
    
    # Compress configurations
    tar -czf "$backup_dir/configs_$backup_date.tar.gz" -C "$backup_dir" .
    
    # Generate metadata
    generate_backup_metadata "configs" "$backup_dir"
    
    # Encrypt backup (configs contain sensitive data)
    encrypt_backup "$backup_dir"
    
    log "Configuration backup completed: $backup_dir"
    echo "$backup_dir"
}

# Encryption function
encrypt_backup() {
    local backup_dir="$1"
    
    if command -v gpg >/dev/null 2>&1; then
        info "Encrypting backup directory: $backup_dir"
        
        # Create encrypted archive
        tar -czf - -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")" | \
        gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
            --s2k-digest-algo SHA512 --s2k-count 65536 \
            --output "$backup_dir.tar.gz.gpg"
        
        # Verify encryption worked
        if [ -f "$backup_dir.tar.gz.gpg" ]; then
            info "Backup encrypted successfully"
            # Keep original for verification, will be cleaned up later
        else
            error "Failed to encrypt backup"
        fi
    else
        warn "GPG not available, backup not encrypted"
    fi
}

# Upload to remote storage
upload_to_remote() {
    local backup_dir="$1"
    
    if command -v aws >/dev/null 2>&1; then
        info "Uploading backup to S3: $S3_BUCKET"
        
        # Upload encrypted backup
        if [ -f "$backup_dir.tar.gz.gpg" ]; then
            aws s3 cp "$backup_dir.tar.gz.gpg" \
                "s3://$S3_BUCKET/$(basename "$backup_dir").tar.gz.gpg" \
                --storage-class STANDARD_IA \
                --region "$AWS_REGION"
        fi
        
        # Upload metadata
        if [ -f "$backup_dir/backup_metadata.json" ]; then
            aws s3 cp "$backup_dir/backup_metadata.json" \
                "s3://$S3_BUCKET/metadata/$(basename "$backup_dir")_metadata.json" \
                --region "$AWS_REGION"
        fi
        
        log "Backup uploaded to remote storage"
    else
        warn "AWS CLI not available, skipping remote upload"
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_dir="$1"
    
    log "Verifying backup integrity: $backup_dir"
    
    local failed_checks=0
    
    # Verify checksums
    if [ -f "$backup_dir/checksums.sha256" ]; then
        cd "$backup_dir"
        if sha256sum -c checksums.sha256 >/dev/null 2>&1; then
            info "Checksum verification passed"
        else
            error "Checksum verification failed"
            ((failed_checks++))
        fi
    fi
    
    # Verify file manifest
    if [ -f "$backup_dir/file_manifest.sha256" ]; then
        cd "$backup_dir"
        if sha256sum -c file_manifest.sha256 >/dev/null 2>&1; then
            info "File manifest verification passed"
        else
            warn "File manifest verification failed"
            ((failed_checks++))
        fi
    fi
    
    # Test database backup
    if [ -f "$backup_dir"/*.backup ]; then
        info "Testing database backup file..."
        if pg_restore --list "$backup_dir"/*.backup >/dev/null 2>&1; then
            info "Database backup file is valid"
        else
            error "Database backup file is corrupted"
            ((failed_checks++))
        fi
    fi
    
    # Test encrypted backup
    if [ -f "$backup_dir.tar.gz.gpg" ]; then
        info "Testing encrypted backup..."
        if gpg --batch --decrypt "$backup_dir.tar.gz.gpg" | tar -tzf - >/dev/null 2>&1; then
            info "Encrypted backup is valid"
        else
            error "Encrypted backup is corrupted"
            ((failed_checks++))
        fi
    fi
    
    if [ $failed_checks -eq 0 ]; then
        log "Backup verification completed successfully"
        return 0
    else
        error "Backup verification failed with $failed_checks errors"
        return 1
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Clean up local backups based on retention policy
    find "$BACKUP_BASE_DIR/database/full" -type d -mtime +$FULL_BACKUP_RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    find "$BACKUP_BASE_DIR/database/incremental" -type d -mtime +$INCREMENTAL_BACKUP_RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    find "$BACKUP_BASE_DIR/redis" -type d -mtime +$FULL_BACKUP_RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    find "$BACKUP_BASE_DIR/files" -type d -mtime +$FULL_BACKUP_RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    find "$BACKUP_BASE_DIR/configs" -type d -mtime +$FULL_BACKUP_RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    
    # Clean up logs
    find "$LOG_DIR" -name "*.log" -mtime +$LOG_RETENTION_DAYS -delete 2>/dev/null || true
    
    # Clean up encrypted backups
    find "$BACKUP_BASE_DIR" -name "*.tar.gz.gpg" -mtime +$FULL_BACKUP_RETENTION_DAYS -delete 2>/dev/null || true
    
    log "Cleanup completed"
}

# Full backup routine
full_backup() {
    log "Starting full backup routine..."
    
    local start_time=$(date +%s)
    local backup_dirs=()
    
    # Database full backup
    backup_dirs+=($(backup_database_full))
    
    # Redis backup
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
        backup_dirs+=($(backup_redis))
    fi
    
    # Full file backup
    backup_dirs+=($(backup_files "full"))
    
    # Configuration backup
    backup_dirs+=($(backup_configs))
    
    # Verify all backups
    local verification_failed=0
    for backup_dir in "${backup_dirs[@]}"; do
        if ! verify_backup "$backup_dir"; then
            ((verification_failed++))
        fi
    done
    
    # Upload to remote storage
    for backup_dir in "${backup_dirs[@]}"; do
        upload_to_remote "$backup_dir"
    done
    
    # Cleanup old backups
    cleanup_old_backups
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $verification_failed -eq 0 ]; then
        log "Full backup completed successfully in ${duration} seconds"
    else
        error "Full backup completed with $verification_failed verification failures in ${duration} seconds"
    fi
}

# Incremental backup routine
incremental_backup() {
    log "Starting incremental backup routine..."
    
    local start_time=$(date +%s)
    local backup_dirs=()
    
    # Database incremental backup
    backup_dirs+=($(backup_database_incremental))
    
    # Incremental file backup
    backup_dirs+=($(backup_files "incremental"))
    
    # Verify backups
    local verification_failed=0
    for backup_dir in "${backup_dirs[@]}"; do
        if ! verify_backup "$backup_dir"; then
            ((verification_failed++))
        fi
    done
    
    # Upload to remote storage
    for backup_dir in "${backup_dirs[@]}"; do
        upload_to_remote "$backup_dir"
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $verification_failed -eq 0 ]; then
        log "Incremental backup completed successfully in ${duration} seconds"
    else
        error "Incremental backup completed with $verification_failed verification failures in ${duration} seconds"
    fi
}

# Restore functions
restore_database() {
    local backup_file="$1"
    local target_db="${2:-$PGDATABASE}"
    
    log "Restoring database from: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
    fi
    
    # Create target database if it doesn't exist
    createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$target_db" 2>/dev/null || true
    
    # Restore database
    pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$target_db" \
        --verbose --clean --if-exists "$backup_file"
    
    log "Database restore completed"
}

# Health check
health_check() {
    log "Performing backup system health check..."
    
    local health_status="healthy"
    
    # Check disk space
    local backup_disk_usage=$(df "$BACKUP_BASE_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$backup_disk_usage" -gt 80 ]; then
        warn "Backup disk usage is high: ${backup_disk_usage}%"
        health_status="warning"
    fi
    
    # Check recent backups
    local last_full_backup=$(find "$BACKUP_BASE_DIR/database/full" -type d -name "2*" | sort | tail -1)
    if [ -n "$last_full_backup" ]; then
        local backup_age=$(( ($(date +%s) - $(date -d "$(basename "$last_full_backup" | cut -d'_' -f1)" +%s)) / 86400 ))
        if [ "$backup_age" -gt 7 ]; then
            warn "Last full backup is $backup_age days old"
            health_status="warning"
        fi
    else
        error "No full backups found"
        health_status="critical"
    fi
    
    # Test S3 connectivity
    if command -v aws >/dev/null 2>&1; then
        if ! aws s3 ls "s3://$S3_BUCKET" >/dev/null 2>&1; then
            warn "Cannot access S3 backup bucket"
            health_status="warning"
        fi
    fi
    
    info "Backup system health status: $health_status"
    echo "$health_status"
}

# Generate backup report
generate_report() {
    log "Generating backup report..."
    
    local report_file="$LOG_DIR/backup_report_$(date +%Y%m%d).txt"
    
    cat > "$report_file" << EOF
ActiveLog Backup System Report
Generated: $(date)

=== Backup Statistics ===
Full Database Backups: $(find "$BACKUP_BASE_DIR/database/full" -type d -name "2*" | wc -l)
Incremental Database Backups: $(find "$BACKUP_BASE_DIR/database/incremental" -type d -name "2*" | wc -l)
Redis Backups: $(find "$BACKUP_BASE_DIR/redis" -type d -name "2*" | wc -l)
File Backups: $(find "$BACKUP_BASE_DIR/files" -type d -name "2*" | wc -l)
Configuration Backups: $(find "$BACKUP_BASE_DIR/configs" -type d -name "2*" | wc -l)

=== Storage Usage ===
Total Backup Size: $(du -sh "$BACKUP_BASE_DIR" | cut -f1)
Database Backups: $(du -sh "$BACKUP_BASE_DIR/database" 2>/dev/null | cut -f1 || echo "0")
File Backups: $(du -sh "$BACKUP_BASE_DIR/files" 2>/dev/null | cut -f1 || echo "0")
Redis Backups: $(du -sh "$BACKUP_BASE_DIR/redis" 2>/dev/null | cut -f1 || echo "0")

=== Recent Backups ===
Last Full Database Backup: $(basename "$(find "$BACKUP_BASE_DIR/database/full" -type d -name "2*" | sort | tail -1)" 2>/dev/null || echo "None")
Last Incremental Database Backup: $(basename "$(find "$BACKUP_BASE_DIR/database/incremental" -type d -name "2*" | sort | tail -1)" 2>/dev/null || echo "None")
Last Redis Backup: $(basename "$(find "$BACKUP_BASE_DIR/redis" -type d -name "2*" | sort | tail -1)" 2>/dev/null || echo "None")

=== Health Status ===
Overall Status: $(health_check)
Disk Usage: $(df "$BACKUP_BASE_DIR" | awk 'NR==2 {print $5}')

EOF

    log "Backup report generated: $report_file"
    cat "$report_file"
}

# Main execution
case "${1:-full}" in
    "full")
        check_dependencies
        full_backup
        ;;
    "incremental")
        check_dependencies
        incremental_backup
        ;;
    "database")
        check_dependencies
        backup_database_full
        ;;
    "redis")
        check_dependencies
        backup_redis
        ;;
    "files")
        check_dependencies
        backup_files "${2:-incremental}"
        ;;
    "configs")
        check_dependencies
        backup_configs
        ;;
    "restore-db")
        if [ -z "${2:-}" ]; then
            error "Usage: $0 restore-db <backup_file> [target_database]"
        fi
        check_dependencies
        restore_database "$2" "${3:-}"
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "verify")
        if [ -z "${2:-}" ]; then
            error "Usage: $0 verify <backup_directory>"
        fi
        verify_backup "$2"
        ;;
    "health")
        health_check
        ;;
    "report")
        generate_report
        ;;
    *)
        echo "Usage: $0 {full|incremental|database|redis|files|configs|restore-db|cleanup|verify|health|report}"
        echo ""
        echo "Commands:"
        echo "  full              - Complete backup of all components"
        echo "  incremental       - Incremental backup (database + files)"
        echo "  database          - Database backup only"
        echo "  redis             - Redis backup only"
        echo "  files [full|inc]  - File backup (default: incremental)"
        echo "  configs           - Configuration backup only"
        echo "  restore-db <file> - Restore database from backup file"
        echo "  cleanup           - Remove old backups based on retention policy"
        echo "  verify <dir>      - Verify backup integrity"
        echo "  health            - Check backup system health"
        echo "  report            - Generate backup status report"
        exit 1
        ;;
esac