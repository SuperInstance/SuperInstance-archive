#!/bin/bash

# File Storage Restore Script for ActiveLog Production
# Supports full restore, incremental restore, and selective restoration
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/backup.conf"
LOG_FILE="${SCRIPT_DIR}/../logs/file_restore.log"
BACKUP_BASE_DIR="/opt/activelog/backups/files"
RESTORE_TEMP_DIR="/tmp/file_restore"

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

find_backup() {
    local backup_identifier="$1"
    local backup_type="${2:-}"
    local backup_dir=""
    
    # If it's a full path and exists, use it
    if [[ -d "$backup_identifier" ]]; then
        backup_dir="$backup_identifier"
    # If it's a timestamp, find it in backup directories
    elif [[ "$backup_identifier" =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
        local search_types=("full" "incremental")
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
        local search_types=("full" "incremental")
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

extract_backup() {
    local backup_dir="$1"
    local temp_dir="$2"
    local selective_paths="${3:-}"
    
    log_info "Extracting backup from: $backup_dir"
    
    # Find archive files
    local archive_files=($(find "$backup_dir" -name "*.tar.gz*" | grep -v metadata))
    
    if [[ ${#archive_files[@]} -eq 0 ]]; then
        # Check if this is an uncompressed backup
        local data_dirs=($(find "$backup_dir" -maxdepth 1 -type d -not -name "$(basename "$backup_dir")"))
        if [[ ${#data_dirs[@]} -gt 0 ]]; then
            log_info "Found uncompressed backup data"
            echo "$backup_dir"
            return 0
        fi
        
        log_error "No archive files or data directories found in backup"
        return 1
    fi
    
    local extract_dir="$temp_dir/extracted"
    ensure_directory "$extract_dir"
    
    # Process each archive
    for archive_file in "${archive_files[@]}"; do
        log_info "Extracting archive: $(basename "$archive_file")"
        
        local work_file="$archive_file"
        
        # Handle encrypted files
        if [[ "$archive_file" == *.enc ]]; then
            local decrypted_file="$temp_dir/$(basename "${archive_file%.enc}")"
            decrypt_backup "$archive_file" "$decrypted_file"
            work_file="$decrypted_file"
        fi
        
        # Extract archive
        if [[ -n "$selective_paths" ]]; then
            log_info "Selective extraction for paths: $selective_paths"
            
            # Create patterns for tar extraction
            local extract_patterns=""
            IFS=',' read -ra PATHS <<< "$selective_paths"
            for path in "${PATHS[@]}"; do
                extract_patterns="$extract_patterns --wildcards '*$path*'"
            done
            
            eval "tar -xzf \"$work_file\" -C \"$extract_dir\" $extract_patterns" || {
                log_warning "Selective extraction failed, extracting full archive"
                tar -xzf "$work_file" -C "$extract_dir"
            }
        else
            tar -xzf "$work_file" -C "$extract_dir"
        fi
        
        # Clean up decrypted file if created
        if [[ "$work_file" != "$archive_file" ]]; then
            rm -f "$work_file"
        fi
    done
    
    log_info "Extraction completed to: $extract_dir"
    echo "$extract_dir"
}

build_restore_chain() {
    local target_backup="$1"
    local chain=()
    
    log_info "Building restore chain for: $target_backup"
    
    # Get backup metadata
    local metadata_file="$target_backup/backup_metadata.json"
    if [[ ! -f "$metadata_file" ]]; then
        log_error "Backup metadata not found: $metadata_file"
        return 1
    fi
    
    local backup_type=$(jq -r '.backup_type' "$metadata_file")
    
    if [[ "$backup_type" == "full" ]]; then
        # Full backup only needs itself
        chain=("$target_backup")
    elif [[ "$backup_type" == "incremental" ]]; then
        # Find the chain of incremental backups back to the full backup
        local current_backup="$target_backup"
        
        while [[ "$backup_type" == "incremental" ]]; do
            chain=("$current_backup" "${chain[@]}")
            
            # Get base backup
            local base_backup=$(jq -r '.base_backup // empty' "$current_backup/backup_metadata.json")
            if [[ -z "$base_backup" ]]; then
                log_error "Base backup reference not found in: $current_backup"
                return 1
            fi
            
            current_backup="$base_backup"
            backup_type=$(jq -r '.backup_type' "$current_backup/backup_metadata.json")
        done
        
        # Add the full backup at the beginning
        if [[ "$backup_type" == "full" ]]; then
            chain=("$current_backup" "${chain[@]}")
        else
            log_error "Invalid backup chain, no full backup found"
            return 1
        fi
    else
        log_error "Unknown backup type: $backup_type"
        return 1
    fi
    
    log_info "Restore chain: ${chain[*]}"
    printf '%s\n' "${chain[@]}"
}

apply_incremental_changes() {
    local incremental_backup="$1"
    local restore_base="$2"
    
    log_info "Applying incremental changes from: $incremental_backup"
    
    local changes_file="$incremental_backup/changes.txt"
    if [[ ! -f "$changes_file" ]]; then
        log_warning "No changes file found in incremental backup"
        return 0
    fi
    
    local changes_applied=0
    local changes_failed=0
    
    # Extract incremental backup
    local temp_extract_dir=$(mktemp -d -p "$TEMP_DIR")
    local extracted_dir=$(extract_backup "$incremental_backup" "$temp_extract_dir")
    
    # Apply changes
    while IFS= read -r change_line; do
        if [[ -z "$change_line" ]]; then
            continue
        fi
        
        local change_type=$(echo "$change_line" | cut -d: -f1)
        local file_path=$(echo "$change_line" | cut -d: -f2- | sed 's/^ *//')
        
        case "$change_type" in
            "CHANGED")
                # Copy changed file to restore location
                local rel_path="${file_path#/}"
                local source_file=""
                
                # Find the file in extracted backup
                if [[ -f "$extracted_dir/$rel_path" ]]; then
                    source_file="$extracted_dir/$rel_path"
                else
                    # Search for the file
                    source_file=$(find "$extracted_dir" -path "*/$rel_path" | head -1)
                fi
                
                if [[ -n "$source_file" && -f "$source_file" ]]; then
                    local target_file="$restore_base/$rel_path"
                    ensure_directory "$(dirname "$target_file")"
                    
                    if cp "$source_file" "$target_file"; then
                        changes_applied=$((changes_applied + 1))
                        log_info "Applied change: $file_path"
                    else
                        changes_failed=$((changes_failed + 1))
                        log_error "Failed to apply change: $file_path"
                    fi
                else
                    changes_failed=$((changes_failed + 1))
                    log_error "Source file not found for change: $file_path"
                fi
                ;;
                
            "DELETED")
                # Remove deleted file from restore location
                local rel_path="${file_path#/}"
                local target_file="$restore_base/$rel_path"
                
                if [[ -f "$target_file" ]]; then
                    if rm -f "$target_file"; then
                        changes_applied=$((changes_applied + 1))
                        log_info "Applied deletion: $file_path"
                    else
                        changes_failed=$((changes_failed + 1))
                        log_error "Failed to delete: $file_path"
                    fi
                else
                    # File already doesn't exist, count as applied
                    changes_applied=$((changes_applied + 1))
                fi
                ;;
                
            *)
                log_warning "Unknown change type: $change_type"
                ;;
        esac
        
    done < "$changes_file"
    
    log_info "Incremental changes applied: $changes_applied, failed: $changes_failed"
    
    # Cleanup temporary extraction
    rm -rf "$temp_extract_dir"
    
    return 0
}

restore_backup() {
    local backup_identifier="$1"
    local target_path="$2"
    local selective_paths="${3:-}"
    local preserve_existing="${4:-false}"
    
    log_info "Starting restore process"
    log_info "Backup: $backup_identifier, Target: $target_path"
    
    # Find the target backup
    local target_backup=$(find_backup "$backup_identifier")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    # Build restore chain
    local restore_chain_file="$TEMP_DIR/restore_chain.txt"
    if ! build_restore_chain "$target_backup" > "$restore_chain_file"; then
        return 1
    fi
    
    local restore_chain=($(cat "$restore_chain_file"))
    log_info "Restore chain contains ${#restore_chain[@]} backup(s)"
    
    # Prepare target directory
    ensure_directory "$target_path"
    
    if [[ "$preserve_existing" != "true" ]]; then
        log_warning "Clearing target directory: $target_path"
        find "$target_path" -mindepth 1 -delete 2>/dev/null || true
    fi
    
    local start_time=$(date +%s)
    local total_files=0
    local total_size=0
    
    # Apply backups in order
    for i in "${!restore_chain[@]}"; do
        local backup_dir="${restore_chain[$i]}"
        local backup_name=$(basename "$backup_dir")
        local backup_type=$(jq -r '.backup_type' "$backup_dir/backup_metadata.json")
        
        log_info "Processing backup $((i+1))/${#restore_chain[@]}: $backup_name ($backup_type)"
        
        if [[ "$backup_type" == "full" ]]; then
            # Extract full backup
            local extracted_dir=$(extract_backup "$backup_dir" "$TEMP_DIR" "$selective_paths")
            if [[ $? -ne 0 ]]; then
                log_error "Failed to extract full backup: $backup_dir"
                return 1
            fi
            
            # Copy files to target
            log_info "Copying files to target directory..."
            if rsync -av "$extracted_dir/" "$target_path/"; then
                local backup_files=$(find "$extracted_dir" -type f | wc -l)
                local backup_size=$(du -sb "$extracted_dir" | cut -f1)
                
                total_files=$((total_files + backup_files))
                total_size=$((total_size + backup_size))
                
                log_info "Full backup restored: $backup_files files, $(numfmt --to=iec $backup_size)"
            else
                log_error "Failed to copy files from full backup"
                return 1
            fi
            
        elif [[ "$backup_type" == "incremental" ]]; then
            # Apply incremental changes
            if ! apply_incremental_changes "$backup_dir" "$target_path"; then
                log_error "Failed to apply incremental backup: $backup_dir"
                return 1
            fi
            
        else
            log_error "Unknown backup type: $backup_type"
            return 1
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Verify restoration
    local final_files=$(find "$target_path" -type f | wc -l)
    local final_size=$(du -sb "$target_path" | cut -f1)
    
    log_info "Restore completed successfully"
    log_info "Duration: ${duration}s, Files: $final_files, Size: $(numfmt --to=iec $final_size)"
    
    # Create restore report
    cat > "$target_path/.restore_info.json" <<EOF
{
    "restore_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "source_backup": "$backup_identifier",
    "target_path": "$target_path",
    "selective_paths": "$selective_paths",
    "restore_chain": $(printf '%s\n' "${restore_chain[@]}" | jq -R . | jq -s .),
    "duration_seconds": $duration,
    "final_files": $final_files,
    "final_size_bytes": $final_size,
    "script_version": "1.0.0"
}
EOF
    
    return 0
}

verify_restoration() {
    local target_path="$1"
    local backup_identifier="${2:-}"
    
    log_info "Verifying restoration in: $target_path"
    
    if [[ ! -d "$target_path" ]]; then
        log_error "Target path does not exist: $target_path"
        return 1
    fi
    
    # Check if restore info exists
    local restore_info="$target_path/.restore_info.json"
    if [[ -f "$restore_info" ]]; then
        local restore_timestamp=$(jq -r '.restore_timestamp' "$restore_info")
        local file_count=$(jq -r '.final_files' "$restore_info")
        log_info "Restore info found, completed at: $restore_timestamp, files: $file_count"
    else
        log_warning "No restore info found"
    fi
    
    # Basic checks
    local current_files=$(find "$target_path" -type f | wc -l)
    local current_size=$(du -sh "$target_path" | cut -f1)
    
    log_info "Current state: $current_files files, $current_size"
    
    # Check for common directory structure
    local expected_dirs=("data" "uploads" "import-queue")
    local missing_dirs=()
    
    for dir in "${expected_dirs[@]}"; do
        if [[ ! -d "$target_path/$dir" ]]; then
            missing_dirs+=("$dir")
        fi
    done
    
    if [[ ${#missing_dirs[@]} -gt 0 ]]; then
        log_warning "Missing expected directories: ${missing_dirs[*]}"
    else
        log_info "All expected directories present"
    fi
    
    # Verify checksums if available
    if [[ -n "$backup_identifier" ]]; then
        local backup_dir=$(find_backup "$backup_identifier")
        if [[ $? -eq 0 ]]; then
            local checksums_file="$backup_dir/checksums.sha256"
            if [[ -f "$checksums_file" ]]; then
                log_info "Verifying file checksums..."
                
                local verified=0
                local failed=0
                
                while IFS= read -r checksum_line; do
                    if [[ -n "$checksum_line" ]]; then
                        local expected_hash=$(echo "$checksum_line" | cut -d' ' -f1)
                        local file_path=$(echo "$checksum_line" | cut -d' ' -f3-)
                        local restored_file="$target_path/${file_path#/}"
                        
                        if [[ -f "$restored_file" ]]; then
                            local actual_hash=$(sha256sum "$restored_file" | cut -d' ' -f1)
                            if [[ "$expected_hash" == "$actual_hash" ]]; then
                                verified=$((verified + 1))
                            else
                                failed=$((failed + 1))
                                log_warning "Checksum mismatch: $restored_file"
                            fi
                        else
                            failed=$((failed + 1))
                            log_warning "File not found: $restored_file"
                        fi
                    fi
                done < "$checksums_file"
                
                log_info "Checksum verification: $verified passed, $failed failed"
                
                if [[ $failed -gt 0 ]]; then
                    log_warning "Some files failed checksum verification"
                    return 1
                fi
            fi
        fi
    fi
    
    log_info "Restoration verification completed successfully"
    return 0
}

list_available_backups() {
    log_info "Available file backups:"
    
    local backup_types=("full" "incremental")
    
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
                        local files=$(jq -r '.total_files // .total_changes // "N/A"' "$metadata_file" 2>/dev/null || echo "N/A")
                        echo "  $timestamp (Size: $size, Status: $status, Files/Changes: $files)"
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
                        \"alertname\": \"FileRestore\",
                        \"service\": \"backup\",
                        \"component\": \"files\",
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
    restore <backup_id> <target_path> [--selective=paths] [--preserve]
        Restore file backup to target directory
        
    list
        List available backups
        
    verify <target_path> [backup_id]
        Verify restored files
        
    help
        Show this help message

Examples:
    $0 restore latest /opt/activelog/restored_data
    $0 restore 20231215_143000 /tmp/restore --selective=uploads,data
    $0 restore latest /opt/data --preserve
    $0 list
    $0 verify /opt/activelog/restored_data 20231215_143000

Options:
    --selective=... Comma-separated list of paths to restore selectively
    --preserve      Don't clear target directory before restore
EOF
}

# Main execution
main() {
    local command="${1:-help}"
    
    if [[ "$command" == "help" || "$command" == "--help" || "$command" == "-h" ]]; then
        show_usage
        exit 0
    fi
    
    log_info "Starting file restore script (command: $command)"
    
    # Create necessary directories
    ensure_directory "$(dirname "$LOG_FILE")"
    TEMP_DIR=$(mktemp -d -p "$RESTORE_TEMP_DIR" file_restore.XXXXXX)
    ensure_directory "$TEMP_DIR"
    
    case "$command" in
        "restore")
            if [[ $# -lt 3 ]]; then
                log_error "Insufficient arguments for restore"
                show_usage
                exit 1
            fi
            
            local backup_id="$2"
            local target_path="$3"
            local selective_paths=""
            local preserve_existing=false
            
            # Parse additional arguments
            shift 3
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --selective=*)
                        selective_paths="${1#*=}"
                        ;;
                    --preserve)
                        preserve_existing=true
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
                shift
            done
            
            if restore_backup "$backup_id" "$target_path" "$selective_paths" "$preserve_existing"; then
                if verify_restoration "$target_path" "$backup_id"; then
                    send_notification "info" "File restore completed successfully" "Target: $target_path, Backup: $backup_id"
                else
                    send_notification "warning" "File restore completed with verification warnings" "Target: $target_path, Backup: $backup_id"
                fi
            else
                send_notification "critical" "File restore failed" "Target: $target_path, Backup: $backup_id"
                exit 1
            fi
            ;;
            
        "list")
            list_available_backups
            ;;
            
        "verify")
            if [[ $# -lt 2 ]]; then
                log_error "Target path required for verification"
                show_usage
                exit 1
            fi
            
            local target_path="$2"
            local backup_id="${3:-}"
            
            verify_restoration "$target_path" "$backup_id"
            ;;
            
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
    
    log_info "File restore script completed successfully"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi