#!/bin/bash

# PostgreSQL Restore Script for ActiveLog Production
# Supports full restore, point-in-time recovery, and selective restoration
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/backup.conf"
LOG_FILE="${SCRIPT_DIR}/../logs/postgres_restore.log"
BACKUP_BASE_DIR="/opt/activelog/backups/postgres"
RESTORE_TEMP_DIR="/tmp/postgres_restore"

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

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $*" | tee -a "$LOG_FILE"
}

# Error handling and cleanup
cleanup() {
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        log_info "Cleaning up temporary directory: $TEMP_DIR"
        rm -rf "$TEMP_DIR"
    fi
    
    # Remove temporary restore instance if it exists
    if [[ -n "${RESTORE_INSTANCE_DIR:-}" && -d "$RESTORE_INSTANCE_DIR" ]]; then
        log_info "Cleaning up temporary restore instance: $RESTORE_INSTANCE_DIR"
        rm -rf "$RESTORE_INSTANCE_DIR"
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
    if ! pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d template1 -t 30; then
        log_error "PostgreSQL is not ready or connection failed"
        return 1
    fi
    log_info "PostgreSQL connection verified"
}

find_backup() {
    local backup_identifier="$1"
    local backup_dir=""
    
    # If it's a full path and exists, use it
    if [[ -d "$backup_identifier" ]]; then
        backup_dir="$backup_identifier"
    # If it's a timestamp, find it in backup directories
    elif [[ "$backup_identifier" =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
        for type in full base_backup; do
            if [[ -d "$BACKUP_BASE_DIR/$type/$backup_identifier" ]]; then
                backup_dir="$BACKUP_BASE_DIR/$type/$backup_identifier"
                break
            fi
        done
    # If it's "latest", find the most recent backup
    elif [[ "$backup_identifier" == "latest" ]]; then
        local latest_full="$BACKUP_BASE_DIR/full/latest"
        if [[ -L "$latest_full" ]]; then
            backup_dir="$BACKUP_BASE_DIR/full/$(readlink "$latest_full")"
        fi
    fi
    
    if [[ -z "$backup_dir" || ! -d "$backup_dir" ]]; then
        log_error "Backup not found: $backup_identifier"
        return 1
    fi
    
    log_info "Found backup: $backup_dir"
    echo "$backup_dir"
}

decrypt_backup() {
    local encrypted_file="$1"
    local output_file="$2"
    
    if [[ ! -f "$encrypted_file" ]]; then
        log_error "Encrypted backup file not found: $encrypted_file"
        return 1
    fi
    
    log_info "Decrypting backup file..."
    if command -v gpg >/dev/null 2>&1; then
        if [[ -f "/run/secrets/backup_passphrase" ]]; then
            gpg --decrypt --quiet --batch --yes \
                --passphrase-file="/run/secrets/backup_passphrase" \
                --output "$output_file" "$encrypted_file"
        else
            log_error "Backup passphrase file not found"
            return 1
        fi
    else
        log_error "GPG not available for decryption"
        return 1
    fi
    
    log_info "Backup decrypted successfully"
}

prepare_backup_file() {
    local backup_dir="$1"
    local temp_dir="$2"
    
    # Find backup files
    local sql_backup_file=$(find "$backup_dir" -name "*.sql.gz*" | head -1)
    local custom_backup_file=$(find "$backup_dir" -name "*.custom" | head -1)
    
    if [[ -n "$custom_backup_file" && -f "$custom_backup_file" ]]; then
        echo "$custom_backup_file"
        return 0
    fi
    
    if [[ -n "$sql_backup_file" && -f "$sql_backup_file" ]]; then
        local prepared_file="$temp_dir/$(basename "$sql_backup_file")"
        
        # Handle encrypted files
        if [[ "$sql_backup_file" == *.enc ]]; then
            local decrypted_file="${prepared_file%.enc}"
            decrypt_backup "$sql_backup_file" "$decrypted_file"
            prepared_file="$decrypted_file"
        else
            cp "$sql_backup_file" "$prepared_file"
        fi
        
        # Decompress if needed
        if [[ "$prepared_file" == *.gz ]]; then
            gunzip "$prepared_file"
            prepared_file="${prepared_file%.gz}"
        fi
        
        echo "$prepared_file"
        return 0
    fi
    
    log_error "No suitable backup file found in: $backup_dir"
    return 1
}

create_restoration_database() {
    local target_db="$1"
    local force="${2:-false}"
    
    log_info "Preparing database for restoration: $target_db"
    
    # Check if database exists
    if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d template1 -lqt | cut -d \| -f 1 | grep -qw "$target_db"; then
        if [[ "$force" == "true" ]]; then
            log_warning "Dropping existing database: $target_db"
            # Terminate existing connections
            psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d template1 -c "
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = '$target_db' AND pid <> pg_backend_pid();
            " >/dev/null 2>&1 || true
            
            # Drop database
            dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$target_db"
        else
            log_error "Database '$target_db' already exists. Use --force to overwrite."
            return 1
        fi
    fi
    
    # Create new database
    log_info "Creating database: $target_db"
    createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$target_db"
}

restore_from_sql_dump() {
    local backup_file="$1"
    local target_db="$2"
    local selective_tables="${3:-}"
    
    log_info "Restoring from SQL dump: $backup_file"
    
    if [[ -n "$selective_tables" ]]; then
        log_info "Selective restore for tables: $selective_tables"
        # Create temporary filtered dump
        local filtered_dump="$TEMP_DIR/filtered_dump.sql"
        
        # Extract specific tables (this is a simplified approach)
        # In production, you might want to use pg_restore with --table option
        grep -A 1000000 "CREATE TABLE.*\($selective_tables\)" "$backup_file" > "$filtered_dump" || true
        backup_file="$filtered_dump"
    fi
    
    # Perform restoration
    local start_time=$(date +%s)
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$target_db" \
         -v ON_ERROR_STOP=1 -f "$backup_file"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "SQL dump restoration completed in ${duration}s"
}

restore_from_custom_dump() {
    local backup_file="$1"
    local target_db="$2"
    local selective_tables="${3:-}"
    local parallel_jobs="${4:-4}"
    
    log_info "Restoring from custom dump: $backup_file"
    
    local restore_options="--verbose --exit-on-error"
    
    if [[ -n "$selective_tables" ]]; then
        log_info "Selective restore for tables: $selective_tables"
        # Add table selection options
        IFS=',' read -ra TABLES <<< "$selective_tables"
        for table in "${TABLES[@]}"; do
            restore_options="$restore_options --table=$table"
        done
    fi
    
    # Perform restoration
    local start_time=$(date +%s)
    
    pg_restore $restore_options \
        --host="$PGHOST" \
        --port="$PGPORT" \
        --username="$PGUSER" \
        --dbname="$target_db" \
        --jobs="$parallel_jobs" \
        "$backup_file"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Custom dump restoration completed in ${duration}s"
}

point_in_time_recovery() {
    local base_backup_dir="$1"
    local target_time="$2"
    local target_db="$3"
    local recovery_port="${4:-5433}"
    
    log_info "Starting point-in-time recovery to: $target_time"
    
    # Create temporary recovery instance
    RESTORE_INSTANCE_DIR="$RESTORE_TEMP_DIR/recovery_instance"
    ensure_directory "$RESTORE_INSTANCE_DIR"
    
    # Extract base backup
    log_info "Extracting base backup..."
    local base_tar=$(find "$base_backup_dir" -name "base.tar.gz" | head -1)
    if [[ -z "$base_tar" ]]; then
        log_error "Base backup tar file not found in: $base_backup_dir"
        return 1
    fi
    
    tar -xzf "$base_tar" -C "$RESTORE_INSTANCE_DIR"
    
    # Create recovery configuration
    cat > "$RESTORE_INSTANCE_DIR/postgresql.conf" <<EOF
# Recovery configuration
port = $recovery_port
logging_collector = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_min_messages = info
log_min_error_statement = info
log_min_duration_statement = 1000

# Point-in-time recovery settings
restore_command = 'cp /opt/activelog/backups/postgres/wal_archive/%f %p'
recovery_target_time = '$target_time'
recovery_target_action = 'promote'
EOF
    
    # Create recovery signal file (PostgreSQL 12+)
    touch "$RESTORE_INSTANCE_DIR/recovery.signal"
    
    # Start temporary PostgreSQL instance
    log_info "Starting temporary PostgreSQL instance for recovery..."
    pg_ctl -D "$RESTORE_INSTANCE_DIR" -l "$RESTORE_INSTANCE_DIR/recovery.log" start
    
    # Wait for recovery to complete
    local max_wait=300  # 5 minutes
    local waited=0
    
    while [[ $waited -lt $max_wait ]]; do
        if pg_isready -h localhost -p "$recovery_port" -t 1 >/dev/null 2>&1; then
            log_info "Recovery instance is ready"
            break
        fi
        sleep 5
        waited=$((waited + 5))
    done
    
    if [[ $waited -ge $max_wait ]]; then
        log_error "Recovery instance failed to start within $max_wait seconds"
        return 1
    fi
    
    # Dump the recovered database
    log_info "Dumping recovered database..."
    local recovered_dump="$TEMP_DIR/recovered_database.sql"
    
    pg_dump --host=localhost --port="$recovery_port" --username="$PGUSER" \
            --dbname="$PGDATABASE" --verbose > "$recovered_dump"
    
    # Stop temporary instance
    pg_ctl -D "$RESTORE_INSTANCE_DIR" stop
    
    # Restore to target database
    create_restoration_database "$target_db" true
    restore_from_sql_dump "$recovered_dump" "$target_db"
    
    log_info "Point-in-time recovery completed successfully"
}

verify_restoration() {
    local target_db="$1"
    
    log_info "Verifying restoration..."
    
    # Basic connectivity test
    if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$target_db" -c "SELECT 1;" >/dev/null 2>&1; then
        log_error "Cannot connect to restored database: $target_db"
        return 1
    fi
    
    # Check if database has tables
    local table_count=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$target_db" -t -c "
        SELECT count(*) FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    " | tr -d ' ')
    
    if [[ "$table_count" -eq 0 ]]; then
        log_warning "No tables found in restored database"
    else
        log_info "Restored database contains $table_count tables"
    fi
    
    # Run basic integrity checks
    local check_result=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$target_db" -t -c "
        SELECT 'OK' WHERE EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public'
        );
    " | tr -d ' ')
    
    if [[ "$check_result" == "OK" ]]; then
        log_info "Database restoration verification passed"
        return 0
    else
        log_error "Database restoration verification failed"
        return 1
    fi
}

list_available_backups() {
    log_info "Available backups:"
    
    local backup_types=("full" "base_backup")
    
    for type in "${backup_types[@]}"; do
        local type_dir="$BACKUP_BASE_DIR/$type"
        if [[ -d "$type_dir" ]]; then
            echo ""
            echo "=== $type backups ==="
            for backup_dir in "$type_dir"/[0-9]*_[0-9]*; do
                if [[ -d "$backup_dir" ]]; then
                    local timestamp=$(basename "$backup_dir")
                    local metadata_file="$backup_dir/backup_metadata.json"
                    
                    if [[ -f "$metadata_file" ]]; then
                        local size=$(jq -r '.final_size // "Unknown"' "$metadata_file" 2>/dev/null || echo "Unknown")
                        local status=$(jq -r '.status // "Unknown"' "$metadata_file" 2>/dev/null || echo "Unknown")
                        echo "  $timestamp (Size: $size, Status: $status)"
                    else
                        echo "  $timestamp (No metadata)"
                    fi
                fi
            done
        fi
    done
}

send_notification() {
    local status="$1"
    local message="$2"
    local restore_info="$3"
    
    # Send to monitoring system
    if command -v curl >/dev/null 2>&1; then
        curl -s -X POST "http://localhost:9093/api/v1/alerts" \
            -H "Content-Type: application/json" \
            -d "{
                \"alerts\": [{
                    \"labels\": {
                        \"alertname\": \"PostgreSQLRestore\",
                        \"service\": \"backup\",
                        \"component\": \"postgres\",
                        \"severity\": \"$status\"
                    },
                    \"annotations\": {
                        \"summary\": \"$message\",
                        \"description\": \"$restore_info\"
                    }
                }]
            }" >/dev/null 2>&1 || true
    fi
}

# Main functions
show_usage() {
    cat <<EOF
Usage: $0 <command> [options]

Commands:
    full <backup_id> <target_db> [--force] [--tables=table1,table2]
        Restore full backup to target database
        
    pitr <base_backup_id> <target_time> <target_db> [--port=5433]
        Point-in-time recovery
        
    list
        List available backups
        
    verify <database>
        Verify restored database
        
    help
        Show this help message

Examples:
    $0 full latest activelog_restored --force
    $0 full 20231215_143000 activelog_test --tables=users,files
    $0 pitr 20231215_120000 "2023-12-15 14:30:00" activelog_recovered
    $0 list
    $0 verify activelog_restored

Options:
    --force         Overwrite existing target database
    --tables=...    Comma-separated list of tables to restore (selective restore)
    --port=...      Port for temporary recovery instance (default: 5433)
EOF
}

# Main execution
main() {
    local command="${1:-help}"
    
    if [[ "$command" == "help" || "$command" == "--help" || "$command" == "-h" ]]; then
        show_usage
        exit 0
    fi
    
    log_info "Starting PostgreSQL restore script (command: $command)"
    
    # Create necessary directories
    ensure_directory "$(dirname "$LOG_FILE")"
    TEMP_DIR=$(mktemp -d -p "$RESTORE_TEMP_DIR" postgres_restore.XXXXXX)
    ensure_directory "$TEMP_DIR"
    
    # Load secrets and check connection
    load_secrets
    check_postgres_connection
    
    case "$command" in
        "full")
            if [[ $# -lt 3 ]]; then
                log_error "Insufficient arguments for full restore"
                show_usage
                exit 1
            fi
            
            local backup_id="$2"
            local target_db="$3"
            local force=false
            local selective_tables=""
            
            # Parse additional arguments
            shift 3
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --force)
                        force=true
                        ;;
                    --tables=*)
                        selective_tables="${1#*=}"
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
                shift
            done
            
            backup_dir=$(find_backup "$backup_id")
            if [[ $? -ne 0 ]]; then
                exit 1
            fi
            
            create_restoration_database "$target_db" "$force"
            
            backup_file=$(prepare_backup_file "$backup_dir" "$TEMP_DIR")
            if [[ $? -ne 0 ]]; then
                exit 1
            fi
            
            if [[ "$backup_file" == *.custom ]]; then
                restore_from_custom_dump "$backup_file" "$target_db" "$selective_tables"
            else
                restore_from_sql_dump "$backup_file" "$target_db" "$selective_tables"
            fi
            
            if verify_restoration "$target_db"; then
                send_notification "info" "PostgreSQL restore completed successfully" "Database: $target_db, Backup: $backup_id"
            else
                send_notification "critical" "PostgreSQL restore verification failed" "Database: $target_db, Backup: $backup_id"
                exit 1
            fi
            ;;
            
        "pitr")
            if [[ $# -lt 4 ]]; then
                log_error "Insufficient arguments for point-in-time recovery"
                show_usage
                exit 1
            fi
            
            local base_backup_id="$2"
            local target_time="$3"
            local target_db="$4"
            local recovery_port=5433
            
            # Parse additional arguments
            shift 4
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --port=*)
                        recovery_port="${1#*=}"
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
                shift
            done
            
            base_backup_dir=$(find_backup "$base_backup_id")
            if [[ $? -ne 0 ]]; then
                exit 1
            fi
            
            point_in_time_recovery "$base_backup_dir" "$target_time" "$target_db" "$recovery_port"
            
            if verify_restoration "$target_db"; then
                send_notification "info" "Point-in-time recovery completed successfully" "Database: $target_db, Time: $target_time"
            else
                send_notification "critical" "Point-in-time recovery verification failed" "Database: $target_db, Time: $target_time"
                exit 1
            fi
            ;;
            
        "list")
            list_available_backups
            ;;
            
        "verify")
            if [[ $# -lt 2 ]]; then
                log_error "Database name required for verification"
                show_usage
                exit 1
            fi
            
            verify_restoration "$2"
            ;;
            
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
    
    log_info "PostgreSQL restore script completed successfully"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi