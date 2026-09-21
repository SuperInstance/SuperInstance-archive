#!/bin/bash

# Redis Backup Script for ActiveLog Production
# Supports RDB snapshots, AOF backups, and live data replication
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/backup.conf"
LOG_FILE="${SCRIPT_DIR}/../logs/redis_backup.log"
BACKUP_BASE_DIR="/opt/activelog/backups/redis"
RETENTION_DAYS=30
ENCRYPT_BACKUP=true
COMPRESSION_LEVEL=6

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

get_redis_info() {
    redis-cli $REDIS_CLI_OPTS info server | grep -E "redis_version|os|arch|process_id|run_id"
}

get_redis_memory_usage() {
    redis-cli $REDIS_CLI_OPTS info memory | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r'
}

get_redis_keyspace_info() {
    redis-cli $REDIS_CLI_OPTS info keyspace
}

create_rdb_backup() {
    local backup_type="${1:-rdb}"
    local timestamp="$(date '+%Y%m%d_%H%M%S')"
    local backup_dir="$BACKUP_BASE_DIR/$backup_type/$timestamp"
    
    ensure_directory "$backup_dir"
    
    log_info "Starting RDB backup to: $backup_dir"
    
    # Get Redis information for metadata
    local redis_info=$(get_redis_info)
    local memory_usage=$(get_redis_memory_usage)
    local keyspace_info=$(get_redis_keyspace_info)
    
    # Create backup metadata
    cat > "$backup_dir/backup_metadata.json" <<EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$timestamp",
    "redis_host": "$REDIS_HOST",
    "redis_port": $REDIS_PORT,
    "redis_db": $REDIS_DB,
    "compression": "gzip",
    "compression_level": $COMPRESSION_LEVEL,
    "encrypted": $ENCRYPT_BACKUP,
    "memory_usage": "$memory_usage",
    "script_version": "1.0.0",
    "redis_info": $(echo "$redis_info" | jq -R -s -c 'split("\n") | map(select(length > 0))'),
    "keyspace_info": $(echo "$keyspace_info" | jq -R -s -c 'split("\n") | map(select(length > 0))')
}
EOF
    
    local start_time=$(date +%s)
    local rdb_file="$backup_dir/redis_${timestamp}.rdb"
    
    # Method 1: Use BGSAVE and copy the RDB file
    log_info "Triggering background save..."
    redis-cli $REDIS_CLI_OPTS bgsave
    
    # Wait for background save to complete
    local max_wait=300  # 5 minutes
    local waited=0
    
    while [[ $waited -lt $max_wait ]]; do
        local save_status=$(redis-cli $REDIS_CLI_OPTS lastsave)
        sleep 2
        local new_save_status=$(redis-cli $REDIS_CLI_OPTS lastsave)
        
        if [[ "$save_status" != "$new_save_status" ]]; then
            log_info "Background save completed"
            break
        fi
        
        sleep 3
        waited=$((waited + 5))
    done
    
    if [[ $waited -ge $max_wait ]]; then
        log_error "Background save timed out after $max_wait seconds"
        return 1
    fi
    
    # Find and copy the RDB file
    local redis_data_dir="/data"  # Default Redis data directory in container
    local source_rdb="$redis_data_dir/dump.rdb"
    
    # If running in Docker, we might need to copy from the container
    if command -v docker >/dev/null 2>&1; then
        local redis_container=$(docker ps --filter "name=redis" --format "{{.Names}}" | head -1)
        if [[ -n "$redis_container" ]]; then
            log_info "Copying RDB file from Redis container: $redis_container"
            docker cp "$redis_container:$source_rdb" "$rdb_file" 2>/dev/null || {
                log_warning "Failed to copy from container, trying direct file access"
                cp "$source_rdb" "$rdb_file" 2>/dev/null || {
                    log_error "Failed to access RDB file"
                    return 1
                }
            }
        else
            cp "$source_rdb" "$rdb_file" 2>/dev/null || {
                log_error "RDB file not found: $source_rdb"
                return 1
            }
        fi
    else
        cp "$source_rdb" "$rdb_file" 2>/dev/null || {
            log_error "RDB file not found: $source_rdb"
            return 1
        }
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Compress the backup
    log_info "Compressing RDB backup..."
    gzip -f "$rdb_file"
    local compressed_file="${rdb_file}.gz"
    
    # Encrypt if enabled
    local final_file="$compressed_file"
    if [[ "$ENCRYPT_BACKUP" == "true" ]]; then
        log_info "Encrypting backup..."
        if command -v gpg >/dev/null 2>&1; then
            local encrypted_file="${compressed_file}.enc"
            gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
                --s2k-digest-algo SHA512 --s2k-count 65536 --quiet \
                --passphrase-file="/run/secrets/backup_passphrase" \
                --output "$encrypted_file" "$compressed_file"
            rm -f "$compressed_file"
            final_file="$encrypted_file"
        else
            log_error "GPG not available for encryption, backup will remain unencrypted"
        fi
    fi
    
    # Update metadata with final information
    local final_size=$(du -h "$final_file" | cut -f1)
    jq --arg size "$final_size" \
       --arg duration "$duration" \
       --arg status "completed" \
       --arg final_file "$(basename "$final_file")" \
       '. + {final_size: $size, duration_seconds: ($duration | tonumber), status: $status, final_file: $final_file}' \
       "$backup_dir/backup_metadata.json" > "$backup_dir/backup_metadata.json.tmp"
    mv "$backup_dir/backup_metadata.json.tmp" "$backup_dir/backup_metadata.json"
    
    log_info "RDB backup completed successfully"
    log_info "Duration: ${duration}s, Size: $final_size"
    log_info "Backup location: $final_file"
    
    # Create symlink to latest backup
    local latest_link="$BACKUP_BASE_DIR/$backup_type/latest"
    rm -f "$latest_link"
    ln -sf "$timestamp" "$latest_link"
    
    echo "$backup_dir"
}

create_aof_backup() {
    local backup_type="aof"
    local timestamp="$(date '+%Y%m%d_%H%M%S')"
    local backup_dir="$BACKUP_BASE_DIR/$backup_type/$timestamp"
    
    ensure_directory "$backup_dir"
    
    log_info "Starting AOF backup to: $backup_dir"
    
    local start_time=$(date +%s)
    
    # Check if AOF is enabled
    local aof_enabled=$(redis-cli $REDIS_CLI_OPTS config get appendonly | tail -1)
    if [[ "$aof_enabled" != "yes" ]]; then
        log_warning "AOF is not enabled, enabling temporarily for backup"
        redis-cli $REDIS_CLI_OPTS config set appendonly yes
        sleep 2
    fi
    
    # Trigger AOF rewrite to get a clean, compacted AOF file
    log_info "Triggering AOF rewrite..."
    redis-cli $REDIS_CLI_OPTS bgrewriteaof
    
    # Wait for AOF rewrite to complete
    local max_wait=300  # 5 minutes
    local waited=0
    
    while [[ $waited -lt $max_wait ]]; do
        local aof_rewrite_status=$(redis-cli $REDIS_CLI_OPTS info persistence | grep "aof_rewrite_in_progress" | cut -d: -f2 | tr -d '\r')
        
        if [[ "$aof_rewrite_status" == "0" ]]; then
            log_info "AOF rewrite completed"
            break
        fi
        
        sleep 5
        waited=$((waited + 5))
    done
    
    if [[ $waited -ge $max_wait ]]; then
        log_error "AOF rewrite timed out after $max_wait seconds"
        return 1
    fi
    
    # Copy the AOF file
    local redis_data_dir="/data"
    local source_aof="$redis_data_dir/appendonly.aof"
    local aof_file="$backup_dir/redis_${timestamp}.aof"
    
    # Copy from container if needed
    if command -v docker >/dev/null 2>&1; then
        local redis_container=$(docker ps --filter "name=redis" --format "{{.Names}}" | head -1)
        if [[ -n "$redis_container" ]]; then
            log_info "Copying AOF file from Redis container: $redis_container"
            docker cp "$redis_container:$source_aof" "$aof_file" 2>/dev/null || {
                log_warning "Failed to copy from container, trying direct file access"
                cp "$source_aof" "$aof_file" 2>/dev/null || {
                    log_error "Failed to access AOF file"
                    return 1
                }
            }
        else
            cp "$source_aof" "$aof_file" 2>/dev/null || {
                log_error "AOF file not found: $source_aof"
                return 1
            }
        fi
    else
        cp "$source_aof" "$aof_file" 2>/dev/null || {
            log_error "AOF file not found: $source_aof"
            return 1
        }
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Restore original AOF setting if it was disabled
    if [[ "$aof_enabled" != "yes" ]]; then
        log_info "Restoring original AOF setting"
        redis-cli $REDIS_CLI_OPTS config set appendonly no
    fi
    
    # Compress and encrypt the backup (similar to RDB backup)
    log_info "Compressing AOF backup..."
    gzip -f "$aof_file"
    local compressed_file="${aof_file}.gz"
    
    # Create metadata and handle encryption (same as RDB)
    local memory_usage=$(get_redis_memory_usage)
    local keyspace_info=$(get_redis_keyspace_info)
    
    cat > "$backup_dir/backup_metadata.json" <<EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$timestamp",
    "redis_host": "$REDIS_HOST",
    "redis_port": $REDIS_PORT,
    "redis_db": $REDIS_DB,
    "compression": "gzip",
    "compression_level": $COMPRESSION_LEVEL,
    "encrypted": $ENCRYPT_BACKUP,
    "memory_usage": "$memory_usage",
    "duration_seconds": $duration,
    "script_version": "1.0.0",
    "keyspace_info": $(echo "$keyspace_info" | jq -R -s -c 'split("\n") | map(select(length > 0))')
}
EOF
    
    log_info "AOF backup completed successfully"
    echo "$backup_dir"
}

create_live_data_backup() {
    local backup_type="live"
    local timestamp="$(date '+%Y%m%d_%H%M%S')"
    local backup_dir="$BACKUP_BASE_DIR/$backup_type/$timestamp"
    
    ensure_directory "$backup_dir"
    
    log_info "Starting live data backup to: $backup_dir"
    
    local start_time=$(date +%s)
    local backup_file="$backup_dir/redis_live_${timestamp}.redis"
    
    # Get all keys and their values
    log_info "Extracting live data using DUMP commands..."
    
    # Get all keys
    local all_keys_file="$backup_dir/all_keys.txt"
    redis-cli $REDIS_CLI_OPTS --raw keys "*" > "$all_keys_file"
    
    # Create Redis protocol file for restoration
    {
        echo "# Redis live data backup"
        echo "# Generated on $(date)"
        echo "# Memory usage: $(get_redis_memory_usage)"
        echo ""
        
        while IFS= read -r key; do
            if [[ -n "$key" ]]; then
                # Get key type
                local key_type=$(redis-cli $REDIS_CLI_OPTS type "$key" | tr -d '\r')
                
                case "$key_type" in
                    "string")
                        local value=$(redis-cli $REDIS_CLI_OPTS get "$key" | sed 's/"/\\"/g')
                        echo "SET \"$key\" \"$value\""
                        ;;
                    "list")
                        echo "DEL \"$key\""
                        redis-cli $REDIS_CLI_OPTS lrange "$key" 0 -1 | while IFS= read -r item; do
                            echo "RPUSH \"$key\" \"$item\""
                        done
                        ;;
                    "set")
                        echo "DEL \"$key\""
                        redis-cli $REDIS_CLI_OPTS smembers "$key" | while IFS= read -r item; do
                            echo "SADD \"$key\" \"$item\""
                        done
                        ;;
                    "zset")
                        echo "DEL \"$key\""
                        redis-cli $REDIS_CLI_OPTS zrange "$key" 0 -1 withscores | {
                            while IFS= read -r member && IFS= read -r score; do
                                echo "ZADD \"$key\" $score \"$member\""
                            done
                        }
                        ;;
                    "hash")
                        echo "DEL \"$key\""
                        redis-cli $REDIS_CLI_OPTS hgetall "$key" | {
                            while IFS= read -r field && IFS= read -r value; do
                                echo "HSET \"$key\" \"$field\" \"$value\""
                            done
                        }
                        ;;
                esac
                
                # Handle TTL
                local ttl=$(redis-cli $REDIS_CLI_OPTS ttl "$key" | tr -d '\r')
                if [[ "$ttl" -gt 0 ]]; then
                    echo "EXPIRE \"$key\" $ttl"
                fi
                
                echo ""
            fi
        done < "$all_keys_file"
    } > "$backup_file"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Compress and encrypt
    gzip -f "$backup_file"
    local compressed_file="${backup_file}.gz"
    
    local final_file="$compressed_file"
    if [[ "$ENCRYPT_BACKUP" == "true" ]] && command -v gpg >/dev/null 2>&1; then
        local encrypted_file="${compressed_file}.enc"
        gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
            --s2k-digest-algo SHA512 --s2k-count 65536 --quiet \
            --passphrase-file="/run/secrets/backup_passphrase" \
            --output "$encrypted_file" "$compressed_file"
        rm -f "$compressed_file"
        final_file="$encrypted_file"
    fi
    
    # Create metadata
    local final_size=$(du -h "$final_file" | cut -f1)
    local key_count=$(wc -l < "$all_keys_file")
    
    cat > "$backup_dir/backup_metadata.json" <<EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$timestamp",
    "redis_host": "$REDIS_HOST",
    "redis_port": $REDIS_PORT,
    "redis_db": $REDIS_DB,
    "key_count": $key_count,
    "compression": "gzip",
    "encrypted": $ENCRYPT_BACKUP,
    "duration_seconds": $duration,
    "final_size": "$final_size",
    "final_file": "$(basename "$final_file")",
    "status": "completed",
    "script_version": "1.0.0"
}
EOF
    
    log_info "Live data backup completed successfully"
    log_info "Keys backed up: $key_count, Duration: ${duration}s, Size: $final_size"
    
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
    
    # Check backup files
    local backup_files=($(find "$backup_dir" -name "*.rdb*" -o -name "*.aof*" -o -name "*.redis*"))
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
        if [[ "$file" == *.gz ]] && [[ "$file" != *.enc ]]; then
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
    
    local backup_types=("rdb" "aof" "live")
    
    for backup_type in "${backup_types[@]}"; do
        local backup_dir="$BACKUP_BASE_DIR/$backup_type"
        if [[ -d "$backup_dir" ]]; then
            find "$backup_dir" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -name "[0-9]*_[0-9]*" | while read -r old_backup; do
                log_info "Removing old backup: $old_backup"
                rm -rf "$old_backup"
            done
        fi
    done
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
                        \"alertname\": \"RedisBackup\",
                        \"service\": \"backup\",
                        \"component\": \"redis\",
                        \"severity\": \"$status\"
                    },
                    \"annotations\": {
                        \"summary\": \"$message\",
                        \"description\": \"$backup_info\"
                    }
                }]
            }" >/dev/null 2>&1 || true
    fi
    
    # Log to structured log
    cat >> "$SCRIPT_DIR/../logs/backup_events.json" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "service": "redis_backup",
    "status": "$status",
    "message": "$message",
    "details": "$backup_info"
}
EOF
}

# Main execution
main() {
    local action="${1:-rdb}"
    
    log_info "Starting Redis backup script (action: $action)"
    
    # Create necessary directories
    ensure_directory "$BACKUP_BASE_DIR"
    ensure_directory "$(dirname "$LOG_FILE")"
    
    # Load configuration and check connection
    load_redis_config
    check_redis_connection
    
    case "$action" in
        "rdb")
            backup_dir=$(create_rdb_backup "rdb")
            if verify_backup "$backup_dir"; then
                send_notification "info" "Redis RDB backup completed successfully" "Backup location: $backup_dir"
            else
                send_notification "critical" "Redis RDB backup verification failed" "Backup location: $backup_dir"
                exit 1
            fi
            ;;
        "aof")
            backup_dir=$(create_aof_backup)
            if verify_backup "$backup_dir"; then
                send_notification "info" "Redis AOF backup completed successfully" "Backup location: $backup_dir"
            else
                send_notification "critical" "Redis AOF backup verification failed" "Backup location: $backup_dir"
                exit 1
            fi
            ;;
        "live")
            backup_dir=$(create_live_data_backup)
            if verify_backup "$backup_dir"; then
                send_notification "info" "Redis live data backup completed successfully" "Backup location: $backup_dir"
            else
                send_notification "critical" "Redis live data backup verification failed" "Backup location: $backup_dir"
                exit 1
            fi
            ;;
        "cleanup")
            cleanup_old_backups
            send_notification "info" "Redis backup cleanup completed" ""
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
            echo "Usage: $0 {rdb|aof|live|cleanup|verify <backup_dir>}"
            exit 1
            ;;
    esac
    
    log_info "Redis backup script completed successfully"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi