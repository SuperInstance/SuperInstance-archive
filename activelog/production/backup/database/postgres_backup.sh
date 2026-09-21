#!/bin/bash

# PostgreSQL Backup Script for ActiveLog Production
# Supports full backups, incremental WAL archiving, and point-in-time recovery
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/backup.conf"
LOG_FILE="${SCRIPT_DIR}/../logs/postgres_backup.log"
BACKUP_BASE_DIR="/opt/activelog/backups/postgres"
RETENTION_DAYS=30
COMPRESSION_LEVEL=6
ENCRYPT_BACKUP=true
PARALLEL_JOBS=4

# Load configuration if exists
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
}

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $*" | tee -a "$LOG_FILE"
}

# Error handling
cleanup() {
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        log_info "Cleaning up temporary directory: $TEMP_DIR"
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT
trap 'log_error "Script interrupted"; exit 130' INT TERM

# Utility functions
ensure_directory() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    fi
}

load_secrets() {
    if [[ -f "/run/secrets/postgres_user" ]]; then
        export PGUSER="$(cat /run/secrets/postgres_user)"
    else
        export PGUSER="${POSTGRES_USER:-activelog}"
    fi
    
    if [[ -f "/run/secrets/postgres_password" ]]; then
        export PGPASSWORD="$(cat /run/secrets/postgres_password)"
    else
        export PGPASSWORD="${POSTGRES_PASSWORD:-}"
    fi
    
    if [[ -f "/run/secrets/postgres_db" ]]; then
        export PGDATABASE="$(cat /run/secrets/postgres_db)"
    else
        export PGDATABASE="${POSTGRES_DB:-activelog}"
    fi
    
    export PGHOST="${POSTGRES_HOST:-localhost}"
    export PGPORT="${POSTGRES_PORT:-5432}"
}

check_postgres_connection() {
    log_info "Checking PostgreSQL connection..."
    if ! pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t 30; then
        log_error "PostgreSQL is not ready or connection failed"
        return 1
    fi
    log_info "PostgreSQL connection verified"
}

get_backup_size() {
    local backup_file="$1"
    if [[ -f "$backup_file" ]]; then
        du -h "$backup_file" | cut -f1
    else
        echo "Unknown"
    fi
}

# Backup functions
create_full_backup() {
    local backup_type="${1:-full}"
    local timestamp="$(date '+%Y%m%d_%H%M%S')"
    local backup_dir="$BACKUP_BASE_DIR/$backup_type/$timestamp"
    local backup_file="$backup_dir/postgres_${backup_type}_${timestamp}.sql"
    local compressed_file="${backup_file}.gz"
    local encrypted_file="${compressed_file}.enc"
    
    ensure_directory "$backup_dir"
    
    log_info "Starting $backup_type backup to: $backup_dir"
    
    # Create backup metadata
    cat > "$backup_dir/backup_metadata.json" <<EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$timestamp",
    "database": "$PGDATABASE",
    "host": "$PGHOST",
    "port": $PGPORT,
    "user": "$PGUSER",
    "compression": "gzip",
    "compression_level": $COMPRESSION_LEVEL,
    "encrypted": $ENCRYPT_BACKUP,
    "pg_version": "$(pg_config --version 2>/dev/null || echo 'Unknown')",
    "script_version": "1.0.0"
}
EOF
    
    # Perform the backup
    log_info "Running pg_dump..."
    local start_time=$(date +%s)
    
    pg_dump \
        --verbose \
        --format=custom \
        --compress=$COMPRESSION_LEVEL \
        --jobs=$PARALLEL_JOBS \
        --file="$backup_file.custom" \
        --host="$PGHOST" \
        --port="$PGPORT" \
        --username="$PGUSER" \
        --dbname="$PGDATABASE" \
        --no-password
    
    # Also create SQL dump for compatibility
    pg_dump \
        --verbose \
        --format=plain \
        --host="$PGHOST" \
        --port="$PGPORT" \
        --username="$PGUSER" \
        --dbname="$PGDATABASE" \
        --no-password > "$backup_file"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Compress the SQL dump
    log_info "Compressing backup..."
    gzip -f "$backup_file"
    
    # Encrypt if enabled
    if [[ "$ENCRYPT_BACKUP" == "true" ]]; then
        log_info "Encrypting backup..."
        if command -v gpg >/dev/null 2>&1; then
            gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
                --s2k-digest-algo SHA512 --s2k-count 65536 --quiet \
                --passphrase-file="/run/secrets/backup_passphrase" \
                --output "$encrypted_file" "$compressed_file"
            rm -f "$compressed_file"
            compressed_file="$encrypted_file"
        else
            log_error "GPG not available for encryption, backup will remain unencrypted"
        fi
    fi
    
    # Update metadata with final information
    local final_size=$(get_backup_size "$compressed_file")
    jq --arg size "$final_size" \
       --arg duration "$duration" \
       --arg status "completed" \
       --arg final_file "$(basename "$compressed_file")" \
       '. + {final_size: $size, duration_seconds: ($duration | tonumber), status: $status, final_file: $final_file}' \
       "$backup_dir/backup_metadata.json" > "$backup_dir/backup_metadata.json.tmp"
    mv "$backup_dir/backup_metadata.json.tmp" "$backup_dir/backup_metadata.json"
    
    log_info "$backup_type backup completed successfully"
    log_info "Duration: ${duration}s, Size: $final_size"
    log_info "Backup location: $compressed_file"
    
    # Create symlink to latest backup
    local latest_link="$BACKUP_BASE_DIR/$backup_type/latest"
    rm -f "$latest_link"
    ln -sf "$timestamp" "$latest_link"
    
    echo "$backup_dir"
}

setup_wal_archiving() {
    log_info "Setting up WAL archiving for point-in-time recovery..."
    
    local wal_archive_dir="$BACKUP_BASE_DIR/wal_archive"
    ensure_directory "$wal_archive_dir"
    
    # Create WAL archive script
    cat > "$wal_archive_dir/archive_wal.sh" <<'EOF'
#!/bin/bash
# WAL Archive Script
set -euo pipefail

WAL_FILE="$1"
WAL_PATH="$2"
ARCHIVE_DIR="/opt/activelog/backups/postgres/wal_archive"

# Ensure archive directory exists
mkdir -p "$ARCHIVE_DIR"

# Copy WAL file to archive
cp "$WAL_PATH" "$ARCHIVE_DIR/$WAL_FILE"

# Optionally compress older WAL files
find "$ARCHIVE_DIR" -name "*.wal" -mtime +1 -exec gzip {} \;

exit 0
EOF
    
    chmod +x "$wal_archive_dir/archive_wal.sh"
    
    log_info "WAL archiving setup completed"
    log_info "Archive command: $wal_archive_dir/archive_wal.sh %f %p"
}

create_base_backup() {
    local timestamp="$(date '+%Y%m%d_%H%M%S')"
    local backup_dir="$BACKUP_BASE_DIR/base_backup/$timestamp"
    
    ensure_directory "$backup_dir"
    
    log_info "Creating base backup for point-in-time recovery..."
    
    pg_basebackup \
        --host="$PGHOST" \
        --port="$PGPORT" \
        --username="$PGUSER" \
        --pgdata="$backup_dir" \
        --format=tar \
        --gzip \
        --compress=6 \
        --wal-method=stream \
        --checkpoint=fast \
        --progress \
        --verbose
    
    # Create backup metadata
    cat > "$backup_dir/base_backup_metadata.json" <<EOF
{
    "backup_type": "base_backup",
    "timestamp": "$timestamp",
    "database": "$PGDATABASE",
    "host": "$PGHOST",
    "port": $PGPORT,
    "user": "$PGUSER",
    "format": "tar",
    "compressed": true,
    "wal_method": "stream",
    "pg_version": "$(pg_config --version 2>/dev/null || echo 'Unknown')"
}
EOF
    
    log_info "Base backup completed: $backup_dir"
    echo "$backup_dir"
}

verify_backup() {
    local backup_dir="$1"
    
    log_info "Verifying backup integrity..."
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup directory not found: $backup_dir"
        return 1
    fi
    
    local metadata_file="$backup_dir/backup_metadata.json"
    if [[ ! -f "$metadata_file" ]]; then
        log_error "Backup metadata not found: $metadata_file"
        return 1
    fi
    
    # Check if backup files exist
    local backup_files=($(find "$backup_dir" -name "*.sql.gz*" -o -name "*.custom" -o -name "*.tar.gz"))
    if [[ ${#backup_files[@]} -eq 0 ]]; then
        log_error "No backup files found in: $backup_dir"
        return 1
    fi
    
    # Verify file integrity
    for file in "${backup_files[@]}"; do
        if [[ ! -s "$file" ]]; then
            log_error "Backup file is empty: $file"
            return 1
        fi
        
        # Test gzip integrity if compressed
        if [[ "$file" == *.gz ]]; then
            if ! gzip -t "$file" 2>/dev/null; then
                log_error "Backup file is corrupted: $file"
                return 1
            fi
        fi
    done
    
    log_info "Backup verification passed"
    return 0
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
    
    local dirs_to_check=("$BACKUP_BASE_DIR/full" "$BACKUP_BASE_DIR/incremental" "$BACKUP_BASE_DIR/base_backup")
    
    for dir in "${dirs_to_check[@]}"; do
        if [[ -d "$dir" ]]; then
            find "$dir" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -name "[0-9]*_[0-9]*" | while read -r old_backup; do
                log_info "Removing old backup: $old_backup"
                rm -rf "$old_backup"
            done
        fi
    done
    
    # Clean up old WAL files
    local wal_dir="$BACKUP_BASE_DIR/wal_archive"
    if [[ -d "$wal_dir" ]]; then
        find "$wal_dir" -name "*.wal*" -mtime +$RETENTION_DAYS -delete
        log_info "Cleaned up old WAL files"
    fi
}

send_notification() {
    local status="$1"
    local message="$2"
    local backup_info="$3"
    
    # Send to monitoring system
    if command -v curl >/dev/null 2>&1; then
        curl -s -X POST "http://localhost:9093/api/v1/alerts" \
            -H "Content-Type: application/json" \
            -d "{
                \"alerts\": [{
                    \"labels\": {
                        \"alertname\": \"PostgreSQLBackup\",
                        \"service\": \"backup\",
                        \"component\": \"postgres\",
                        \"severity\": \"$status\"
                    },
                    \"annotations\": {
                        \"summary\": \"$message\",
                        \"description\": \"$backup_info\"
                    }
                }]
            }" >/dev/null 2>&1 || true
    fi
    
    # Log to structured log for monitoring
    cat >> "$SCRIPT_DIR/../logs/backup_events.json" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "service": "postgres_backup",
    "status": "$status",
    "message": "$message",
    "details": "$backup_info"
}
EOF
}

# Main execution
main() {
    local action="${1:-full}"
    
    log_info "Starting PostgreSQL backup script (action: $action)"
    
    # Create necessary directories
    ensure_directory "$BACKUP_BASE_DIR"
    ensure_directory "$(dirname "$LOG_FILE")"
    
    # Load secrets and check connection
    load_secrets
    check_postgres_connection
    
    case "$action" in
        "full")
            backup_dir=$(create_full_backup "full")
            if verify_backup "$backup_dir"; then
                send_notification "info" "PostgreSQL full backup completed successfully" "Backup location: $backup_dir"
            else
                send_notification "critical" "PostgreSQL full backup verification failed" "Backup location: $backup_dir"
                exit 1
            fi
            ;;
        "base")
            backup_dir=$(create_base_backup)
            send_notification "info" "PostgreSQL base backup completed successfully" "Backup location: $backup_dir"
            ;;
        "setup-wal")
            setup_wal_archiving
            send_notification "info" "PostgreSQL WAL archiving setup completed" ""
            ;;
        "cleanup")
            cleanup_old_backups
            send_notification "info" "PostgreSQL backup cleanup completed" ""
            ;;
        "verify")
            if [[ -n "${2:-}" ]]; then
                verify_backup "$2"
            else
                log_error "Backup directory required for verification"
                exit 1
            fi
            ;;
        *)
            log_error "Unknown action: $action"
            echo "Usage: $0 {full|base|setup-wal|cleanup|verify <backup_dir>}"
            exit 1
            ;;
    esac
    
    log_info "PostgreSQL backup script completed successfully"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi