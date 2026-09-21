#!/bin/bash

# Redis Restore Script for ActiveLog Production
# Supports RDB, AOF, and live data restoration
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/backup.conf"
LOG_FILE="${SCRIPT_DIR}/../logs/redis_restore.log"
BACKUP_BASE_DIR="/opt/activelog/backups/redis"
RESTORE_TEMP_DIR="/tmp/redis_restore"

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

load_redis_config() {
    # Load Redis connection details
    if [[ -f "/run/secrets/redis_password" ]]; then
        export REDIS_PASSWORD="$(cat /run/secrets/redis_password)"
    else
        export REDIS_PASSWORD="${REDIS_PASSWORD:-}"
    fi
    
    export REDIS_HOST="${REDIS_HOST:-localhost}"
    export REDIS_PORT="${REDIS_PORT:-6379}"
    export REDIS_DB="${REDIS_DB:-0}"
    
    # Redis CLI options
    REDIS_CLI_OPTS="-h $REDIS_HOST -p $REDIS_PORT"
    if [[ -n "$REDIS_PASSWORD" ]]; then
        REDIS_CLI_OPTS="$REDIS_CLI_OPTS -a $REDIS_PASSWORD"
    fi
}

check_redis_connection() {
    log_info "Checking Redis connection..."
    if ! redis-cli $REDIS_CLI_OPTS ping >/dev/null 2>&1; then
        log_error "Redis is not accessible or connection failed"
        return 1
    fi
    log_info "Redis connection verified"
}

find_backup() {
    local backup_identifier="$1"
    local backup_type="${2:-}"
    local backup_dir=""
    
    # If it's a full path and exists, use it
    if [[ -d "$backup_identifier" ]]; then
        backup_dir="$backup_identifier"
    # If it's a timestamp, find it in backup directories
    elif [[ "$backup_identifier" =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
        local search_types=("rdb" "aof" "live")
        if [[ -n "$backup_type" ]]; then
            search_types=("$backup_type")
        fi
        
        for type in "${search_types[@]}"; do
            if [[ -d "$BACKUP_BASE_DIR/$type/$backup_identifier" ]]; then
                backup_dir="$BACKUP_BASE_DIR/$type/$backup_identifier"
                break
            fi
        done
    # If it's "latest", find the most recent backup
    elif [[ "$backup_identifier" == "latest" ]]; then
        local search_types=("rdb" "aof" "live")
        if [[ -n "$backup_type" ]]; then
            search_types=("$backup_type")
        fi
        
        for type in "${search_types[@]}"; do
            local latest_link="$BACKUP_BASE_DIR/$type/latest"
            if [[ -L "$latest_link" ]]; then
                backup_dir="$BACKUP_BASE_DIR/$type/$(readlink "$latest_link")"
                break
            fi
        done
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
    local rdb_file=$(find "$backup_dir" -name "*.rdb*" | head -1)
    local aof_file=$(find "$backup_dir" -name "*.aof*" | head -1)
    local redis_file=$(find "$backup_dir" -name "*.redis*" | head -1)
    
    local backup_file=""
    local backup_type=""
    
    # Determine backup type and file
    if [[ -n "$rdb_file" && -f "$rdb_file" ]]; then
        backup_file="$rdb_file"
        backup_type="rdb"
    elif [[ -n "$aof_file" && -f "$aof_file" ]]; then
        backup_file="$aof_file"
        backup_type="aof"
    elif [[ -n "$redis_file" && -f "$redis_file" ]]; then
        backup_file="$redis_file"
        backup_type="live"
    else
        log_error "No suitable backup file found in: $backup_dir"
        return 1
    fi
    
    log_info "Found backup type: $backup_type, file: $(basename "$backup_file")"
    
    # Prepare the file
    local prepared_file="$temp_dir/$(basename "$backup_file")"
    
    # Handle encrypted files
    if [[ "$backup_file" == *.enc ]]; then
        local decrypted_file="${prepared_file%.enc}"
        decrypt_backup "$backup_file" "$decrypted_file"
        prepared_file="$decrypted_file"
    else
        cp "$backup_file" "$prepared_file"
    fi
    
    # Decompress if needed
    if [[ "$prepared_file" == *.gz ]]; then
        gunzip "$prepared_file"
        prepared_file="${prepared_file%.gz}"
    fi
    
    echo "$backup_type:$prepared_file"
}

stop_redis_safely() {
    local save_data="${1:-true}"
    
    log_info "Stopping Redis safely..."
    
    if [[ "$save_data" == "true" ]]; then
        log_info "Saving current data before stopping..."
        redis-cli $REDIS_CLI_OPTS bgsave
        
        # Wait for save to complete
        local max_wait=60
        local waited=0
        
        while [[ $waited -lt $max_wait ]]; do
            local save_status=$(redis-cli $REDIS_CLI_OPTS lastsave)
            sleep 1
            local new_save_status=$(redis-cli $REDIS_CLI_OPTS lastsave)
            
            if [[ "$save_status" != "$new_save_status" ]]; then
                log_info "Data saved successfully"
                break
            fi
            
            sleep 2
            waited=$((waited + 3))
        done
    fi
    
    # Stop Redis service (method depends on deployment)
    if command -v docker >/dev/null 2>&1; then
        local redis_container=$(docker ps --filter "name=redis" --format "{{.Names}}" | head -1)
        if [[ -n "$redis_container" ]]; then
            log_info "Stopping Redis container: $redis_container"
            docker stop "$redis_container"
            return 0
        fi
    fi
    
    # Alternative: use redis-cli shutdown
    log_info "Shutting down Redis via redis-cli..."
    redis-cli $REDIS_CLI_OPTS shutdown nosave >/dev/null 2>&1 || true
}

start_redis() {
    log_info "Starting Redis..."
    
    if command -v docker >/dev/null 2>&1; then
        local redis_container=$(docker ps -a --filter "name=redis" --format "{{.Names}}" | head -1)
        if [[ -n "$redis_container" ]]; then
            log_info "Starting Redis container: $redis_container"
            docker start "$redis_container"
            
            # Wait for Redis to be ready
            local max_wait=30
            local waited=0
            
            while [[ $waited -lt $max_wait ]]; do
                if redis-cli $REDIS_CLI_OPTS ping >/dev/null 2>&1; then
                    log_info "Redis is ready"
                    return 0
                fi
                sleep 1
                waited=$((waited + 1))
            done
            
            log_error "Redis failed to start within $max_wait seconds"
            return 1
        fi
    fi
    
    log_error "Unable to start Redis - no container found"
    return 1
}

restore_rdb_backup() {
    local rdb_file="$1"
    local flush_existing="${2:-true}"
    
    log_info "Restoring from RDB backup: $rdb_file"
    
    # Flush existing data if requested
    if [[ "$flush_existing" == "true" ]]; then
        log_warning "Flushing existing Redis data"
        redis-cli $REDIS_CLI_OPTS flushall
    fi
    
    # Stop Redis
    stop_redis_safely false
    
    # Copy RDB file to Redis data directory
    local redis_data_dir="/data"
    local target_rdb="$redis_data_dir/dump.rdb"
    
    if command -v docker >/dev/null 2>&1; then
        local redis_container=$(docker ps -a --filter "name=redis" --format "{{.Names}}" | head -1)
        if [[ -n "$redis_container" ]]; then
            log_info "Copying RDB file to Redis container: $redis_container"
            docker cp "$rdb_file" "$redis_container:$target_rdb"
        else
            cp "$rdb_file" "$target_rdb"
        fi
    else
        cp "$rdb_file" "$target_rdb"
    fi
    
    # Start Redis
    start_redis
    
    log_info "RDB backup restored successfully"
}

restore_aof_backup() {
    local aof_file="$1"
    local flush_existing="${2:-true}"
    
    log_info "Restoring from AOF backup: $aof_file"
    
    # Flush existing data if requested
    if [[ "$flush_existing" == "true" ]]; then
        log_warning "Flushing existing Redis data"
        redis-cli $REDIS_CLI_OPTS flushall
    fi
    
    # Enable AOF if not enabled
    local aof_enabled=$(redis-cli $REDIS_CLI_OPTS config get appendonly | tail -1)
    if [[ "$aof_enabled" != "yes" ]]; then
        log_info "Enabling AOF for restoration"
        redis-cli $REDIS_CLI_OPTS config set appendonly yes
    fi
    
    # Stop Redis
    stop_redis_safely false
    
    # Copy AOF file to Redis data directory
    local redis_data_dir="/data"
    local target_aof="$redis_data_dir/appendonly.aof"
    
    if command -v docker >/dev/null 2>&1; then
        local redis_container=$(docker ps -a --filter "name=redis" --format "{{.Names}}" | head -1)
        if [[ -n "$redis_container" ]]; then
            log_info "Copying AOF file to Redis container: $redis_container"
            docker cp "$aof_file" "$redis_container:$target_aof"
        else
            cp "$aof_file" "$target_aof"
        fi
    else
        cp "$aof_file" "$target_aof"
    fi
    
    # Start Redis
    start_redis
    
    log_info "AOF backup restored successfully"
}

restore_live_backup() {
    local redis_file="$1"
    local flush_existing="${2:-true}"
    
    log_info "Restoring from live data backup: $redis_file"
    
    # Flush existing data if requested
    if [[ "$flush_existing" == "true" ]]; then
        log_warning "Flushing existing Redis data"
        redis-cli $REDIS_CLI_OPTS flushall
    fi
    
    # Execute Redis commands from backup file
    log_info "Executing Redis commands from backup file..."
    
    local start_time=$(date +%s)
    local command_count=0
    
    # Filter out comments and empty lines, then execute commands
    grep -v "^#" "$redis_file" | grep -v "^$" | while IFS= read -r command; do
        if [[ -n "$command" ]]; then
            if ! redis-cli $REDIS_CLI_OPTS eval "return redis.call(unpack(ARGV))" 0 $command; then
                log_warning "Failed to execute command: $command"
            fi
            command_count=$((command_count + 1))
            
            # Show progress every 1000 commands
            if [[ $((command_count % 1000)) -eq 0 ]]; then
                log_info "Executed $command_count commands..."
            fi
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Live data backup restored successfully"
    log_info "Executed $command_count commands in ${duration}s"
}

verify_restoration() {
    local expected_key_count="${1:-}"
    
    log_info "Verifying restoration..."
    
    # Basic connectivity test
    if ! redis-cli $REDIS_CLI_OPTS ping >/dev/null 2>&1; then
        log_error "Cannot connect to Redis after restoration"
        return 1
    fi
    
    # Get current key count
    local current_key_count=$(redis-cli $REDIS_CLI_OPTS eval "return #redis.call('keys', '*')" 0)
    log_info "Current key count: $current_key_count"
    
    # Check against expected count if provided
    if [[ -n "$expected_key_count" ]]; then
        if [[ "$current_key_count" -eq "$expected_key_count" ]]; then
            log_info "Key count matches expected: $expected_key_count"
        else
            log_warning "Key count mismatch. Expected: $expected_key_count, Actual: $current_key_count"
        fi
    fi
    
    # Get memory usage and other info
    local memory_usage=$(redis-cli $REDIS_CLI_OPTS info memory | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
    local keyspace_info=$(redis-cli $REDIS_CLI_OPTS info keyspace)
    
    log_info "Memory usage: $memory_usage"
    log_info "Keyspace info: $keyspace_info"
    
    log_info "Redis restoration verification completed"
    return 0
}

list_available_backups() {
    log_info "Available Redis backups:"
    
    local backup_types=("rdb" "aof" "live")
    
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
                        local key_count=$(jq -r '.key_count // "N/A"' "$metadata_file" 2>/dev/null || echo "N/A")
                        echo "  $timestamp (Size: $size, Status: $status, Keys: $key_count)"
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
                        \"alertname\": \"RedisRestore\",
                        \"service\": \"backup\",
                        \"component\": \"redis\",
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
    restore <backup_id> [--type=rdb|aof|live] [--no-flush]
        Restore Redis backup
        
    list
        List available backups
        
    verify [expected_key_count]
        Verify Redis data after restoration
        
    help
        Show this help message

Examples:
    $0 restore latest --type=rdb
    $0 restore 20231215_143000 --no-flush
    $0 list
    $0 verify 1000

Options:
    --type=...      Specify backup type (rdb, aof, live)
    --no-flush      Don't flush existing data before restore
EOF
}

# Main execution
main() {
    local command="${1:-help}"
    
    if [[ "$command" == "help" || "$command" == "--help" || "$command" == "-h" ]]; then
        show_usage
        exit 0
    fi
    
    log_info "Starting Redis restore script (command: $command)"
    
    # Create necessary directories
    ensure_directory "$(dirname "$LOG_FILE")"
    TEMP_DIR=$(mktemp -d -p "$RESTORE_TEMP_DIR" redis_restore.XXXXXX)
    ensure_directory "$TEMP_DIR"
    
    # Load configuration and check connection
    load_redis_config
    check_redis_connection
    
    case "$command" in
        "restore")
            if [[ $# -lt 2 ]]; then
                log_error "Backup ID required for restore"
                show_usage
                exit 1
            fi
            
            local backup_id="$2"
            local backup_type=""
            local flush_existing=true
            
            # Parse additional arguments
            shift 2
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --type=*)
                        backup_type="${1#*=}"
                        ;;
                    --no-flush)
                        flush_existing=false
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
                shift
            done
            
            backup_dir=$(find_backup "$backup_id" "$backup_type")
            if [[ $? -ne 0 ]]; then
                exit 1
            fi
            
            # Prepare backup file
            backup_info=$(prepare_backup_file "$backup_dir" "$TEMP_DIR")
            if [[ $? -ne 0 ]]; then
                exit 1
            fi
            
            local detected_type=$(echo "$backup_info" | cut -d: -f1)
            local backup_file=$(echo "$backup_info" | cut -d: -f2)
            
            log_info "Restoring $detected_type backup from: $backup_file"
            
            # Perform restoration based on type
            case "$detected_type" in
                "rdb")
                    restore_rdb_backup "$backup_file" "$flush_existing"
                    ;;
                "aof")
                    restore_aof_backup "$backup_file" "$flush_existing"
                    ;;
                "live")
                    restore_live_backup "$backup_file" "$flush_existing"
                    ;;
                *)
                    log_error "Unknown backup type: $detected_type"
                    exit 1
                    ;;
            esac
            
            # Verify restoration
            if verify_restoration; then
                send_notification "info" "Redis restore completed successfully" "Backup: $backup_id, Type: $detected_type"
            else
                send_notification "warning" "Redis restore completed with warnings" "Backup: $backup_id, Type: $detected_type"
            fi
            ;;
            
        "list")
            list_available_backups
            ;;
            
        "verify")
            local expected_key_count="${2:-}"
            verify_restoration "$expected_key_count"
            ;;
            
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
    
    log_info "Redis restore script completed successfully"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi