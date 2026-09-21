#!/bin/bash
# Proper backup rotation system with size limits
# Implements 5 daily, 4 weekly, 12 monthly retention policy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_CONFIG="$PROJECT_ROOT/backup-system/backup_config.json"
BACKUP_LOG="$PROJECT_ROOT/logs/backup-rotation.log"

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$BACKUP_LOG"
}

# Load configuration
load_config() {
    if [ -f "$BACKUP_CONFIG" ]; then
        # Extract retention settings from JSON
        DAILY_KEEP=$(jq -r '.retention_policies.daily.keep_count' "$BACKUP_CONFIG" 2>/dev/null || echo "5")
        WEEKLY_KEEP=$(jq -r '.retention_policies.weekly.keep_count' "$BACKUP_CONFIG" 2>/dev/null || echo "4")
        MONTHLY_KEEP=$(jq -r '.retention_policies.monthly.keep_count' "$BACKUP_CONFIG" 2>/dev/null || echo "12")
        MAX_BACKUP_SIZE_GB=$(jq -r '.backup_settings.max_backup_size_gb' "$BACKUP_CONFIG" 2>/dev/null || echo "10")
    else
        log "Config file not found, using defaults"
        DAILY_KEEP=5
        WEEKLY_KEEP=4
        MONTHLY_KEEP=12
        MAX_BACKUP_SIZE_GB=10
    fi
    
    log "Backup retention policy: ${DAILY_KEEP} daily, ${WEEKLY_KEEP} weekly, ${MONTHLY_KEEP} monthly"
    log "Maximum backup size limit: ${MAX_BACKUP_SIZE_GB}GB"
}

# Check if we have enough disk space for a backup
check_disk_space() {
    local required_space_mb=$((MAX_BACKUP_SIZE_GB * 1024))
    local available_space_mb=$(df "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1024)}')
    
    log "Available disk space: ${available_space_mb}MB"
    log "Required space for backup: ${required_space_mb}MB"
    
    if [ "$available_space_mb" -lt "$required_space_mb" ]; then
        log "ERROR: Insufficient disk space for backup"
        return 1
    fi
    
    return 0
}

# Create a backup with size monitoring
create_backup() {
    local backup_type="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="${backup_type}-${timestamp}"
    local temp_backup_dir="/tmp/activelog-backup-${timestamp}"
    
    log "Creating $backup_type backup: $backup_name"
    
    # Check disk space first
    if ! check_disk_space; then
        log "Aborting backup due to insufficient space"
        return 1
    fi
    
    # Create temporary backup directory
    mkdir -p "$temp_backup_dir"
    
    # Start backup with monitoring
    local backup_pid=""
    local size_monitor_pid=""
    
    # Create backup in background with size monitoring
    (
        cd "$PROJECT_ROOT"
        
        # Create filtered backup based on config exclusions
        if [ -f "$BACKUP_CONFIG" ]; then
            # Use rsync with exclusions from config
            rsync -av \
                --exclude='node_modules/' \
                --exclude='.git/objects/' \
                --exclude='.git/logs/' \
                --exclude='*.log' \
                --exclude='*.tmp' \
                --exclude='*.temp' \
                --exclude='.DS_Store' \
                --exclude='Thumbs.db' \
                --exclude='coverage/' \
                --exclude='dist/' \
                --exclude='build/' \
                --exclude='.cache/' \
                --exclude='*.lock' \
                --exclude='__pycache__/' \
                --exclude='*.pyc' \
                --exclude='.venv/' \
                --exclude='*.pid' \
                --exclude='*.swp' \
                --exclude='*.swo' \
                --exclude='*~' \
                . "$temp_backup_dir/" > /dev/null 2>&1
        else
            # Basic backup
            cp -r . "$temp_backup_dir/" 2>/dev/null || true
        fi
    ) &
    backup_pid=$!
    
    # Monitor backup size
    (
        while kill -0 "$backup_pid" 2>/dev/null; do
            if [ -d "$temp_backup_dir" ]; then
                local current_size_mb=$(du -sm "$temp_backup_dir" 2>/dev/null | cut -f1)
                local max_size_mb=$((MAX_BACKUP_SIZE_GB * 1024))
                
                if [ "$current_size_mb" -gt "$max_size_mb" ]; then
                    log "WARNING: Backup size ($current_size_mb MB) exceeds limit ($max_size_mb MB)"
                    kill "$backup_pid" 2>/dev/null || true
                    break
                fi
            fi
            sleep 5
        done
    ) &
    size_monitor_pid=$!
    
    # Wait for backup to complete
    wait "$backup_pid" 2>/dev/null
    local backup_result=$?
    
    # Stop size monitor
    kill "$size_monitor_pid" 2>/dev/null || true
    
    if [ $backup_result -eq 0 ]; then
        # Compress the backup
        local final_backup_path="$PROJECT_ROOT/backups/${backup_name}.tar.gz"
        mkdir -p "$PROJECT_ROOT/backups"
        
        tar -czf "$final_backup_path" -C "$temp_backup_dir" . 2>/dev/null
        
        if [ $? -eq 0 ]; then
            local final_size=$(du -sh "$final_backup_path" | cut -f1)
            log "Backup created successfully: $backup_name ($final_size)"
            
            # Create git tag for this backup
            cd "$PROJECT_ROOT"
            git tag "backup-$backup_name" 2>/dev/null || true
            
        else
            log "ERROR: Failed to compress backup"
            rm -f "$final_backup_path"
            rm -rf "$temp_backup_dir"
            return 1
        fi
    else
        log "ERROR: Backup creation failed"
        rm -rf "$temp_backup_dir"
        return 1
    fi
    
    # Clean up temp directory
    rm -rf "$temp_backup_dir"
    
    return 0
}

# Clean up old backups according to retention policy
cleanup_old_backups() {
    local backup_type="$1"
    local keep_count="$2"
    
    log "Cleaning up old $backup_type backups (keeping $keep_count)"
    
    if [ ! -d "$PROJECT_ROOT/backups" ]; then
        log "No backups directory found"
        return 0
    fi
    
    # Find and remove old backups
    local backup_files=($(ls -t "$PROJECT_ROOT/backups/${backup_type}-"*.tar.gz 2>/dev/null || true))
    local count=0
    
    for backup_file in "${backup_files[@]}"; do
        count=$((count + 1))
        if [ $count -gt $keep_count ]; then
            local size=$(du -sh "$backup_file" | cut -f1)
            rm -f "$backup_file"
            log "Removed old backup: $(basename "$backup_file") ($size)"
            
            # Remove corresponding git tag
            local backup_name=$(basename "$backup_file" .tar.gz)
            git tag -d "backup-$backup_name" 2>/dev/null || true
        fi
    done
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"
    
    log "Verifying backup integrity: $(basename "$backup_file")"
    
    if tar -tzf "$backup_file" >/dev/null 2>&1; then
        log "Backup verification passed: $(basename "$backup_file")"
        return 0
    else
        log "ERROR: Backup verification failed: $(basename "$backup_file")"
        return 1
    fi
}

# Generate backup report
generate_report() {
    log "=== Backup Rotation Report ==="
    
    if [ -d "$PROJECT_ROOT/backups" ]; then
        local total_backups=$(ls "$PROJECT_ROOT/backups"/*.tar.gz 2>/dev/null | wc -l)
        local total_size=$(du -sh "$PROJECT_ROOT/backups" 2>/dev/null | cut -f1 || echo "0")
        
        log "Total backups: $total_backups"
        log "Total backup storage used: $total_size"
        
        log "Recent backups:"
        ls -lah "$PROJECT_ROOT/backups" | tail -10 | while read -r line; do
            log "  $line"
        done
    else
        log "No backups found"
    fi
    
    # Git backup tags
    local git_backup_tags=$(git tag -l "backup-*" 2>/dev/null | wc -l)
    log "Git backup tags: $git_backup_tags"
}

# Run daily backup
run_daily_backup() {
    log "=== Running daily backup ==="
    if create_backup "daily"; then
        cleanup_old_backups "daily" "$DAILY_KEEP"
    fi
}

# Run weekly backup (on Sundays)
run_weekly_backup() {
    local day_of_week=$(date +%u)  # 1=Monday, 7=Sunday
    
    if [ "$day_of_week" -eq 7 ]; then
        log "=== Running weekly backup ==="
        if create_backup "weekly"; then
            cleanup_old_backups "weekly" "$WEEKLY_KEEP"
        fi
    fi
}

# Run monthly backup (on 1st of month)
run_monthly_backup() {
    local day_of_month=$(date +%d)
    
    if [ "$day_of_month" -eq "01" ]; then
        log "=== Running monthly backup ==="
        if create_backup "monthly"; then
            cleanup_old_backups "monthly" "$MONTHLY_KEEP"
        fi
    fi
}

# Emergency backup (before dangerous operations)
run_emergency_backup() {
    log "=== Running emergency backup ==="
    if create_backup "emergency"; then
        # Keep only 3 emergency backups
        cleanup_old_backups "emergency" 3
    fi
}

# List available backups
list_backups() {
    log "Available backups:"
    
    if [ -d "$PROJECT_ROOT/backups" ]; then
        ls -lah "$PROJECT_ROOT/backups" | grep "\.tar\.gz"
    else
        log "No backups directory found"
    fi
    
    log ""
    log "Git backup tags:"
    git tag -l "backup-*" --sort=-creatordate | head -20
}

# Restore from backup
restore_backup() {
    local backup_name="$1"
    local backup_file="$PROJECT_ROOT/backups/${backup_name}.tar.gz"
    
    if [ ! -f "$backup_file" ]; then
        log "ERROR: Backup file not found: $backup_file"
        return 1
    fi
    
    log "WARNING: This will restore from backup and overwrite current files"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log "Restore cancelled"
        return 1
    fi
    
    # Create emergency backup before restore
    run_emergency_backup
    
    # Restore from backup
    local temp_restore_dir="/tmp/activelog-restore-$(date +%s)"
    mkdir -p "$temp_restore_dir"
    
    if tar -xzf "$backup_file" -C "$temp_restore_dir"; then
        # Move current files to backup
        local current_backup_dir="$PROJECT_ROOT/../activelog-current-$(date +%s)"
        mv "$PROJECT_ROOT" "$current_backup_dir"
        
        # Restore files
        mv "$temp_restore_dir" "$PROJECT_ROOT"
        
        log "Restore completed successfully"
        log "Previous version backed up to: $current_backup_dir"
    else
        log "ERROR: Restore failed"
        rm -rf "$temp_restore_dir"
        return 1
    fi
}

# Main function
main() {
    local command="${1:-daily}"
    local backup_name="${2:-}"
    
    load_config
    
    case "$command" in
        "daily")
            run_daily_backup
            ;;
        "weekly")
            run_weekly_backup
            ;;
        "monthly")
            run_monthly_backup
            ;;
        "emergency")
            run_emergency_backup
            ;;
        "full")
            run_daily_backup
            run_weekly_backup
            run_monthly_backup
            ;;
        "list")
            list_backups
            ;;
        "restore")
            if [ -z "$backup_name" ]; then
                echo "Usage: $0 restore <backup_name>"
                exit 1
            fi
            restore_backup "$backup_name"
            ;;
        "verify")
            if [ -z "$backup_name" ]; then
                echo "Usage: $0 verify <backup_name>"
                exit 1
            fi
            verify_backup "$PROJECT_ROOT/backups/${backup_name}.tar.gz"
            ;;
        "cleanup")
            cleanup_old_backups "daily" "$DAILY_KEEP"
            cleanup_old_backups "weekly" "$WEEKLY_KEEP"
            cleanup_old_backups "monthly" "$MONTHLY_KEEP"
            cleanup_old_backups "emergency" 3
            ;;
        "report")
            generate_report
            ;;
        "--help"|"-h")
            echo "ActiveLog Backup Rotation System"
            echo "Usage: $0 [command] [backup_name]"
            echo ""
            echo "Commands:"
            echo "  daily      - Run daily backup"
            echo "  weekly     - Run weekly backup (Sundays only)"
            echo "  monthly    - Run monthly backup (1st of month only)"
            echo "  emergency  - Run emergency backup"
            echo "  full       - Run all applicable backups"
            echo "  list       - List available backups"
            echo "  restore    - Restore from backup"
            echo "  verify     - Verify backup integrity"
            echo "  cleanup    - Clean up old backups"
            echo "  report     - Generate backup report"
            echo ""
            echo "Examples:"
            echo "  $0 daily                    # Run daily backup"
            echo "  $0 list                     # List backups"
            echo "  $0 restore daily-20240826   # Restore specific backup"
            echo "  $0 verify daily-20240826    # Verify backup integrity"
            exit 0
            ;;
        *)
            echo "Unknown command: $command"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
    
    generate_report
}

main "$@"