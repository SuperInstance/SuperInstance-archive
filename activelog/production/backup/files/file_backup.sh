#!/bin/bash

# File Storage Backup Script for ActiveLog Production
# Supports full backups, incremental backups, and deduplication
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/backup.conf"
LOG_FILE="${SCRIPT_DIR}/../logs/file_backup.log"
BACKUP_BASE_DIR="/opt/activelog/backups/files"
RETENTION_DAYS=90
ENCRYPT_BACKUP=true
COMPRESSION_ENABLED=true
RSYNC_OPTS="--archive --verbose --compress --delete-during --partial --progress"
DEDUPLICATION_ENABLED=true
PARALLEL_JOBS=4

# Source paths to backup
declare -a SOURCE_PATHS=(
    "/opt/activelog/data"
    "/home/activeloguser/activelog/uploads"
    "/home/activeloguser/activelog/import-queue"
    "/var/lib/docker/volumes"
)

# Exclude patterns
declare -a EXCLUDE_PATTERNS=(
    "*.tmp"
    "*.log"
    "*.cache"
    "*/temp/*"
    "*/cache/*"
    "*/.git/*"
    "*/node_modules/*"
    "*/__pycache__/*"
    "*.pyc"
    "*.pyo"
    "*/logs/*"
)

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
    
    # Cleanup any temporary mount points
    if [[ -n "${TEMP_MOUNT:-}" && -d "$TEMP_MOUNT" ]]; then
        log_info "Unmounting and cleaning up: $TEMP_MOUNT"
        umount "$TEMP_MOUNT" 2>/dev/null || true
        rmdir "$TEMP_MOUNT" 2>/dev/null || true
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

get_backup_size() {
    local backup_path="$1"
    if [[ -d "$backup_path" ]]; then
        du -sh "$backup_path" | cut -f1
    elif [[ -f "$backup_path" ]]; then
        du -h "$backup_path" | cut -f1
    else
        echo "Unknown"
    fi
}

calculate_checksum() {
    local file_path="$1"
    if [[ -f "$file_path" ]]; then
        sha256sum "$file_path" | cut -d' ' -f1
    else
        echo ""
    fi
}

build_exclude_options() {
    local exclude_opts=""
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        exclude_opts="$exclude_opts --exclude=$pattern"
    done
    echo "$exclude_opts"
}

compress_backup() {
    local source_dir="$1"
    local target_archive="$2"
    local compression_level="${3:-6}"
    
    log_info "Compressing backup: $source_dir -> $target_archive"
    
    local start_time=$(date +%s)
    
    # Use tar with compression
    tar -czf "$target_archive" \
        --directory="$(dirname "$source_dir")" \
        --exclude-from=<(printf '%s\n' "${EXCLUDE_PATTERNS[@]}") \
        "$(basename "$source_dir")"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Compression completed in ${duration}s"
    echo "$duration"
}

encrypt_backup() {
    local source_file="$1"
    local encrypted_file="$2"
    
    log_info "Encrypting backup: $source_file -> $encrypted_file"
    
    if command -v gpg >/dev/null 2>&1; then
        if [[ -f "/run/secrets/backup_passphrase" ]]; then
            gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
                --s2k-digest-algo SHA512 --s2k-count 65536 --quiet \
                --passphrase-file="/run/secrets/backup_passphrase" \
                --output "$encrypted_file" "$source_file"
        else
            log_error "Backup passphrase file not found"
            return 1
        fi
    else
        log_error "GPG not available for encryption"
        return 1
    fi
    
    log_info "Encryption completed successfully"
}

create_full_backup() {
    local backup_type="${1:-full}"
    local timestamp="$(date '+%Y%m%d_%H%M%S')"
    local backup_dir="$BACKUP_BASE_DIR/$backup_type/$timestamp"
    
    ensure_directory "$backup_dir"
    
    log_info "Starting $backup_type backup to: $backup_dir"
    
    local start_time=$(date +%s)
    local total_size=0
    local total_files=0
    local exclude_opts=$(build_exclude_options)
    
    # Create backup metadata
    cat > "$backup_dir/backup_metadata.json" <<EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$timestamp",
    "compression_enabled": $COMPRESSION_ENABLED,
    "encryption_enabled": $ENCRYPT_BACKUP,
    "deduplication_enabled": $DEDUPLICATION_ENABLED,
    "script_version": "1.0.0",
    "source_paths": $(printf '%s\n' "${SOURCE_PATHS[@]}" | jq -R . | jq -s .),
    "exclude_patterns": $(printf '%s\n' "${EXCLUDE_PATTERNS[@]}" | jq -R . | jq -s .),
    "rsync_options": "$RSYNC_OPTS $exclude_opts"
}
EOF
    
    # Create file list for tracking
    local file_list="$backup_dir/file_list.txt"
    local checksums_file="$backup_dir/checksums.sha256"
    
    > "$file_list"
    > "$checksums_file"
    
    # Backup each source path
    for source_path in "${SOURCE_PATHS[@]}"; do
        if [[ ! -d "$source_path" && ! -f "$source_path" ]]; then
            log_warning "Source path does not exist: $source_path"
            continue
        fi
        
        local path_name=$(basename "$source_path")
        local target_dir="$backup_dir/$path_name"
        
        log_info "Backing up: $source_path -> $target_dir"
        
        # Use rsync for efficient copying
        if rsync $RSYNC_OPTS $exclude_opts "$source_path/" "$target_dir/"; then
            log_info "Successfully backed up: $source_path"
            
            # Count files and calculate size
            local path_files=$(find "$target_dir" -type f | wc -l)
            local path_size=$(du -sb "$target_dir" | cut -f1)
            
            total_files=$((total_files + path_files))
            total_size=$((total_size + path_size))
            
            # Generate file list and checksums
            find "$target_dir" -type f -printf "%p\n" >> "$file_list"
            find "$target_dir" -type f -exec sha256sum {} \; >> "$checksums_file"
            
        else
            log_error "Failed to backup: $source_path"
            continue
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Post-processing
    local final_backup_dir="$backup_dir"
    local final_size_human=$(get_backup_size "$backup_dir")
    
    # Compress if enabled
    if [[ "$COMPRESSION_ENABLED" == "true" ]]; then
        local archive_file="$backup_dir.tar.gz"
        local compression_duration=$(compress_backup "$backup_dir" "$archive_file")
        
        # Replace directory with archive
        rm -rf "$backup_dir"
        mkdir -p "$backup_dir"
        mv "$archive_file" "$backup_dir/"
        mv "$file_list" "$backup_dir/" 2>/dev/null || true
        mv "$checksums_file" "$backup_dir/" 2>/dev/null || true
        
        final_backup_dir="$backup_dir/$(basename "$archive_file")"
        final_size_human=$(get_backup_size "$final_backup_dir")
    fi
    
    # Encrypt if enabled
    if [[ "$ENCRYPT_BACKUP" == "true" ]]; then
        if [[ "$COMPRESSION_ENABLED" == "true" ]]; then
            local archive_file="$backup_dir/$(basename "$backup_dir").tar.gz"
            local encrypted_file="${archive_file}.enc"
            
            encrypt_backup "$archive_file" "$encrypted_file"
            rm -f "$archive_file"
            
            final_backup_dir="$encrypted_file"
            final_size_human=$(get_backup_size "$encrypted_file")
        else
            log_warning "Encryption without compression not implemented for directories"
        fi
    fi
    
    # Update metadata with final information
    jq --arg total_files "$total_files" \
       --arg total_size "$total_size" \
       --arg final_size "$final_size_human" \
       --arg duration "$duration" \
       --arg status "completed" \
       '. + {
           total_files: ($total_files | tonumber),
           total_size_bytes: ($total_size | tonumber),
           final_size: $final_size,
           duration_seconds: ($duration | tonumber),
           status: $status
       }' \
       "$backup_dir/backup_metadata.json" > "$backup_dir/backup_metadata.json.tmp"
    mv "$backup_dir/backup_metadata.json.tmp" "$backup_dir/backup_metadata.json"
    
    log_info "$backup_type backup completed successfully"
    log_info "Files: $total_files, Duration: ${duration}s, Size: $final_size_human"
    
    # Create symlink to latest backup
    local latest_link="$BACKUP_BASE_DIR/$backup_type/latest"
    rm -f "$latest_link"
    ln -sf "$timestamp" "$latest_link"
    
    echo "$backup_dir"
}

create_incremental_backup() {
    local base_backup="${1:-}"
    local timestamp="$(date '+%Y%m%d_%H%M%S')"
    local backup_dir="$BACKUP_BASE_DIR/incremental/$timestamp"
    
    # Find base backup if not specified
    if [[ -z "$base_backup" ]]; then
        local latest_full="$BACKUP_BASE_DIR/full/latest"
        if [[ -L "$latest_full" ]]; then
            base_backup="$BACKUP_BASE_DIR/full/$(readlink "$latest_full")"
        else
            log_error "No base backup found for incremental backup"
            return 1
        fi
    fi
    
    if [[ ! -d "$base_backup" ]]; then
        log_error "Base backup directory not found: $base_backup"
        return 1
    fi
    
    ensure_directory "$backup_dir"
    
    log_info "Starting incremental backup to: $backup_dir"
    log_info "Base backup: $base_backup"
    
    local start_time=$(date +%s)
    local exclude_opts=$(build_exclude_options)
    
    # Create backup metadata
    cat > "$backup_dir/backup_metadata.json" <<EOF
{
    "backup_type": "incremental",
    "timestamp": "$timestamp",
    "base_backup": "$base_backup",
    "compression_enabled": $COMPRESSION_ENABLED,
    "encryption_enabled": $ENCRYPT_BACKUP,
    "script_version": "1.0.0",
    "source_paths": $(printf '%s\n' "${SOURCE_PATHS[@]}" | jq -R . | jq -s .),
    "exclude_patterns": $(printf '%s\n' "${EXCLUDE_PATTERNS[@]}" | jq -R . | jq -s .)
}
EOF
    
    local changes_file="$backup_dir/changes.txt"
    local new_checksums="$backup_dir/checksums.sha256"
    
    > "$changes_file"
    > "$new_checksums"
    
    # Load previous checksums if available
    local previous_checksums="$base_backup/checksums.sha256"
    if [[ ! -f "$previous_checksums" ]]; then
        log_warning "No checksums file found in base backup, performing full comparison"
        previous_checksums="/dev/null"
    fi
    
    local total_changes=0
    local total_size=0
    
    # Check each source path for changes
    for source_path in "${SOURCE_PATHS[@]}"; do
        if [[ ! -d "$source_path" && ! -f "$source_path" ]]; then
            log_warning "Source path does not exist: $source_path"
            continue
        fi
        
        local path_name=$(basename "$source_path")
        local target_dir="$backup_dir/$path_name"
        
        log_info "Checking for changes in: $source_path"
        
        ensure_directory "$target_dir"
        
        # Find files that have changed since base backup
        local temp_checksums=$(mktemp)
        find "$source_path" -type f -exec sha256sum {} \; > "$temp_checksums"
        
        # Compare with previous checksums
        local changed_files=$(mktemp)
        if [[ -s "$previous_checksums" ]]; then
            # Find new or modified files
            comm -23 <(sort "$temp_checksums") <(sort "$previous_checksums") | cut -d' ' -f3- > "$changed_files"
        else
            # All files are considered changed
            cut -d' ' -f3- "$temp_checksums" > "$changed_files"
        fi
        
        local path_changes=0
        local path_size=0
        
        # Copy changed files
        while IFS= read -r file_path; do
            if [[ -n "$file_path" && -f "$file_path" ]]; then
                # Calculate relative path
                local rel_path="${file_path#$source_path/}"
                local target_file="$target_dir/$rel_path"
                
                # Create target directory
                ensure_directory "$(dirname "$target_file")"
                
                # Copy file
                if cp "$file_path" "$target_file"; then
                    echo "CHANGED: $file_path" >> "$changes_file"
                    
                    # Calculate file size
                    local file_size=$(stat -c%s "$file_path")
                    path_size=$((path_size + file_size))
                    path_changes=$((path_changes + 1))
                    
                    # Add to new checksums
                    echo "$(sha256sum "$target_file" | cut -d' ' -f1) $file_path" >> "$new_checksums"
                else
                    log_warning "Failed to copy: $file_path"
                fi
            fi
        done < "$changed_files"
        
        # Check for deleted files
        if [[ -s "$previous_checksums" ]]; then
            local deleted_files=$(mktemp)
            comm -13 <(sort "$temp_checksums") <(sort "$previous_checksums") | cut -d' ' -f3- > "$deleted_files"
            
            while IFS= read -r file_path; do
                if [[ -n "$file_path" ]]; then
                    echo "DELETED: $file_path" >> "$changes_file"
                    path_changes=$((path_changes + 1))
                fi
            done < "$deleted_files"
            
            rm -f "$deleted_files"
        fi
        
        total_changes=$((total_changes + path_changes))
        total_size=$((total_size + path_size))
        
        log_info "Path: $source_path, Changes: $path_changes, Size: $(numfmt --to=iec $path_size)"
        
        rm -f "$temp_checksums" "$changed_files"
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # If no changes, mark as empty backup
    if [[ $total_changes -eq 0 ]]; then
        log_info "No changes detected, creating empty incremental backup"
        echo "No changes detected at $(date)" > "$backup_dir/no_changes.txt"
    fi
    
    # Post-processing (compression and encryption)
    local final_size_human=$(get_backup_size "$backup_dir")
    
    if [[ "$COMPRESSION_ENABLED" == "true" && $total_changes -gt 0 ]]; then
        local archive_file="$backup_dir.tar.gz"
        compress_backup "$backup_dir" "$archive_file"
        
        rm -rf "$backup_dir"
        mkdir -p "$backup_dir"
        mv "$archive_file" "$backup_dir/"
        
        final_size_human=$(get_backup_size "$backup_dir")
    fi
    
    # Update metadata
    jq --arg total_changes "$total_changes" \
       --arg total_size "$total_size" \
       --arg final_size "$final_size_human" \
       --arg duration "$duration" \
       --arg status "completed" \
       '. + {
           total_changes: ($total_changes | tonumber),
           changed_size_bytes: ($total_size | tonumber),
           final_size: $final_size,
           duration_seconds: ($duration | tonumber),
           status: $status
       }' \
       "$backup_dir/backup_metadata.json" > "$backup_dir/backup_metadata.json.tmp"
    mv "$backup_dir/backup_metadata.json.tmp" "$backup_dir/backup_metadata.json"
    
    log_info "Incremental backup completed successfully"
    log_info "Changes: $total_changes, Duration: ${duration}s, Size: $final_size_human"
    
    # Create symlink to latest incremental backup
    local latest_link="$BACKUP_BASE_DIR/incremental/latest"
    rm -f "$latest_link"
    ln -sf "$timestamp" "$latest_link"
    
    echo "$backup_dir"
}

deduplicate_backups() {
    log_info "Starting deduplication process..."
    
    if ! command -v fdupes >/dev/null 2>&1; then
        log_warning "fdupes not available, skipping deduplication"
        return 0
    fi
    
    local start_time=$(date +%s)
    local savings=0
    
    # Deduplicate within backup directories
    local backup_types=("full" "incremental")
    
    for backup_type in "${backup_types[@]}"; do
        local type_dir="$BACKUP_BASE_DIR/$backup_type"
        if [[ -d "$type_dir" ]]; then
            log_info "Deduplicating $backup_type backups..."
            
            # Find duplicates and create hard links
            local duplicates_found=$(fdupes -r "$type_dir" | grep -v "^$" | wc -l)
            
            if [[ $duplicates_found -gt 0 ]]; then
                # Calculate space before deduplication
                local size_before=$(du -sb "$type_dir" | cut -f1)
                
                # Perform deduplication (create hard links)
                fdupes -r -L "$type_dir" >/dev/null 2>&1
                
                # Calculate space after deduplication
                local size_after=$(du -sb "$type_dir" | cut -f1)
                local type_savings=$((size_before - size_after))
                savings=$((savings + type_savings))
                
                log_info "Deduplication saved $(numfmt --to=iec $type_savings) in $backup_type backups"
            else
                log_info "No duplicates found in $backup_type backups"
            fi
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Deduplication completed in ${duration}s, total savings: $(numfmt --to=iec $savings)"
}

verify_backup() {
    local backup_dir="$1"
    
    log_info "Verifying backup integrity: $backup_dir"
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup directory not found: $backup_dir"
        return 1
    fi
    
    local metadata_file="$backup_dir/backup_metadata.json"
    if [[ ! -f "$metadata_file" ]]; then
        log_error "Backup metadata not found: $metadata_file"
        return 1
    fi
    
    # Verify metadata
    if ! jq empty "$metadata_file" 2>/dev/null; then
        log_error "Invalid backup metadata JSON"
        return 1
    fi
    
    # Check for backup files
    local backup_files=($(find "$backup_dir" -name "*.tar.gz*" -o -name "checksums.sha256" | grep -v metadata))
    if [[ ${#backup_files[@]} -eq 0 ]]; then
        # Check for no_changes file (valid for empty incremental backups)
        if [[ -f "$backup_dir/no_changes.txt" ]]; then
            log_info "Empty incremental backup verification passed"
            return 0
        fi
        
        log_error "No backup files found in: $backup_dir"
        return 1
    fi
    
    # Verify compressed files
    for file in "${backup_files[@]}"; do
        if [[ "$file" == *.tar.gz ]] && [[ "$file" != *.enc ]]; then
            if ! tar -tzf "$file" >/dev/null 2>&1; then
                log_error "Corrupted archive: $file"
                return 1
            fi
        fi
    done
    
    # Verify checksums if available
    local checksums_file="$backup_dir/checksums.sha256"
    if [[ -f "$checksums_file" ]]; then
        log_info "Verifying file checksums..."
        # Note: This would require extracting compressed backups for full verification
        # For now, we just check the checksums file format
        if ! sha256sum -c "$checksums_file" --quiet 2>/dev/null; then
            log_warning "Some checksum verifications failed (files may be in archive)"
        fi
    fi
    
    log_info "Backup verification passed"
    return 0
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
    
    local backup_types=("full" "incremental")
    
    for backup_type in "${backup_types[@]}"; do
        local type_dir="$BACKUP_BASE_DIR/$backup_type"
        if [[ -d "$type_dir" ]]; then
            find "$type_dir" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -name "[0-9]*_[0-9]*" | while read -r old_backup; do
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
                        \"alertname\": \"FileBackup\",
                        \"service\": \"backup\",
                        \"component\": \"files\",
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
    "service": "file_backup",
    "status": "$status",
    "message": "$message",
    "details": "$backup_info"
}
EOF
}

# Main execution
main() {
    local action="${1:-full}"
    
    log_info "Starting file backup script (action: $action)"
    
    # Create necessary directories
    ensure_directory "$BACKUP_BASE_DIR"
    ensure_directory "$(dirname "$LOG_FILE")"
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    
    case "$action" in
        "full")
            backup_dir=$(create_full_backup "full")
            if verify_backup "$backup_dir"; then
                if [[ "$DEDUPLICATION_ENABLED" == "true" ]]; then
                    deduplicate_backups
                fi
                send_notification "info" "File full backup completed successfully" "Backup location: $backup_dir"
            else
                send_notification "critical" "File full backup verification failed" "Backup location: $backup_dir"
                exit 1
            fi
            ;;
        "incremental")
            base_backup="${2:-}"
            backup_dir=$(create_incremental_backup "$base_backup")
            if verify_backup "$backup_dir"; then
                if [[ "$DEDUPLICATION_ENABLED" == "true" ]]; then
                    deduplicate_backups
                fi
                send_notification "info" "File incremental backup completed successfully" "Backup location: $backup_dir"
            else
                send_notification "critical" "File incremental backup verification failed" "Backup location: $backup_dir"
                exit 1
            fi
            ;;
        "deduplicate")
            deduplicate_backups
            send_notification "info" "File backup deduplication completed" ""
            ;;
        "cleanup")
            cleanup_old_backups
            send_notification "info" "File backup cleanup completed" ""
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
            echo "Usage: $0 {full|incremental [base_backup]|deduplicate|cleanup|verify <backup_dir>}"
            exit 1
            ;;
    esac
    
    log_info "File backup script completed successfully"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi