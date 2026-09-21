#!/bin/bash
# Automated cleanup system for ActiveLog
# Prevents storage bloat and maintains system health

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
CLEANUP_LOG="$LOG_DIR/cleanup.log"
DRY_RUN=${DRY_RUN:-false}

# Size thresholds (in MB)
MAX_LOG_FILE_SIZE=100
MAX_TEMP_DIR_SIZE=500
MAX_NODE_MODULES_CACHE_SIZE=1000

# Age thresholds (in days)
LOG_RETENTION_DAYS=7
TEMP_FILE_MAX_AGE=1
STALE_PID_MAX_AGE=7

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$CLEANUP_LOG"
}

# Function to safely remove files/directories
safe_remove() {
    local target="$1"
    local reason="$2"
    
    if [ "$DRY_RUN" = "true" ]; then
        log "DRY_RUN: Would remove $target ($reason)"
        return 0
    fi
    
    if [ -e "$target" ]; then
        local size=$(du -sh "$target" 2>/dev/null | cut -f1 || echo "unknown")
        rm -rf "$target"
        log "Removed $target - Size: $size - Reason: $reason"
        return 0
    else
        log "Target not found: $target"
        return 1
    fi
}

# Function to compress old log files
compress_old_logs() {
    log "=== Compressing old log files ==="
    
    find "$PROJECT_ROOT" -name "*.log" -type f -mtime +1 ! -name "*.gz" | while read -r logfile; do
        # Skip if already compressed or currently being written to
        if lsof "$logfile" >/dev/null 2>&1; then
            log "Skipping active log file: $logfile"
            continue
        fi
        
        local size_mb=$(du -m "$logfile" 2>/dev/null | cut -f1)
        if [ "$size_mb" -gt 10 ]; then
            if [ "$DRY_RUN" = "true" ]; then
                log "DRY_RUN: Would compress $logfile (${size_mb}MB)"
            else
                gzip "$logfile" && log "Compressed $logfile (${size_mb}MB)"
            fi
        fi
    done
}

# Function to clean up old log files
cleanup_old_logs() {
    log "=== Cleaning up old log files ==="
    
    # Remove log files older than retention period
    find "$PROJECT_ROOT" -name "*.log" -type f -mtime "+$LOG_RETENTION_DAYS" | while read -r logfile; do
        safe_remove "$logfile" "older than $LOG_RETENTION_DAYS days"
    done
    
    # Remove compressed logs older than 30 days
    find "$PROJECT_ROOT" -name "*.log.gz" -type f -mtime +30 | while read -r gzlog; do
        safe_remove "$gzlog" "compressed log older than 30 days"
    done
    
    # Remove oversized log files
    find "$PROJECT_ROOT" -name "*.log" -type f -size "+${MAX_LOG_FILE_SIZE}M" | while read -r biglog; do
        local size=$(du -sh "$biglog" 2>/dev/null | cut -f1)
        safe_remove "$biglog" "oversized log file ($size)"
    done
}

# Function to clean up temporary files
cleanup_temp_files() {
    log "=== Cleaning up temporary files ==="
    
    # Temporary files and directories
    local temp_patterns=("*.tmp" "*.temp" "*.swp" "*.swo" "*~" ".DS_Store" "Thumbs.db")
    
    for pattern in "${temp_patterns[@]}"; do
        find "$PROJECT_ROOT" -name "$pattern" -type f -mtime "+$TEMP_FILE_MAX_AGE" | while read -r tempfile; do
            safe_remove "$tempfile" "temporary file older than $TEMP_FILE_MAX_AGE day(s)"
        done
    done
    
    # Clean up empty temporary directories
    find "$PROJECT_ROOT" -type d -name "tmp" -empty | while read -r tmpdir; do
        safe_remove "$tmpdir" "empty temporary directory"
    done
}

# Function to clean up stale PID files
cleanup_stale_pids() {
    log "=== Cleaning up stale PID files ==="
    
    find "$PROJECT_ROOT" -name "*.pid" -type f | while read -r pidfile; do
        if [ -f "$pidfile" ]; then
            local pid=$(cat "$pidfile" 2>/dev/null || echo "")
            if [ -n "$pid" ]; then
                if ! kill -0 "$pid" 2>/dev/null; then
                    safe_remove "$pidfile" "stale PID file (process $pid not running)"
                fi
            else
                safe_remove "$pidfile" "empty PID file"
            fi
        fi
    done
}

# Function to clean up node_modules cache
cleanup_node_modules() {
    log "=== Cleaning up node_modules cache ==="
    
    # Find large node_modules directories and clean their cache
    find "$PROJECT_ROOT" -name "node_modules" -type d | while read -r nm_dir; do
        local size_mb=$(du -sm "$nm_dir" 2>/dev/null | cut -f1)
        if [ "$size_mb" -gt "$MAX_NODE_MODULES_CACHE_SIZE" ]; then
            # Clean npm cache within node_modules
            if [ -d "$nm_dir/.cache" ]; then
                safe_remove "$nm_dir/.cache" "large node_modules cache (${size_mb}MB total)"
            fi
        fi
    done
}

# Function to clean up Docker artifacts (if Docker is installed)
cleanup_docker() {
    if command -v docker >/dev/null 2>&1; then
        log "=== Cleaning up Docker artifacts ==="
        
        if [ "$DRY_RUN" = "true" ]; then
            log "DRY_RUN: Would clean Docker system"
        else
            # Clean up dangling images and containers
            docker system prune -f >/dev/null 2>&1 && log "Cleaned Docker system" || log "Docker cleanup skipped (no dangling resources)"
        fi
    fi
}

# Function to clean up old git objects
cleanup_git() {
    log "=== Cleaning up Git repository ==="
    
    if [ -d "$PROJECT_ROOT/.git" ]; then
        if [ "$DRY_RUN" = "true" ]; then
            log "DRY_RUN: Would run git gc"
        else
            cd "$PROJECT_ROOT"
            git gc --prune=now --aggressive >/dev/null 2>&1 && log "Git garbage collection completed"
        fi
    fi
}

# Function to generate cleanup report
generate_report() {
    log "=== Cleanup Summary Report ==="
    
    local total_space_before=${1:-0}
    local total_space_after=$(du -sm "$PROJECT_ROOT" 2>/dev/null | cut -f1)
    local space_freed=$((total_space_before - total_space_after))
    
    log "Space before cleanup: ${total_space_before}MB"
    log "Space after cleanup: ${total_space_after}MB"
    log "Space freed: ${space_freed}MB"
    
    # Log largest directories for monitoring
    log "Top 10 largest directories after cleanup:"
    du -sm "$PROJECT_ROOT"/* 2>/dev/null | sort -nr | head -10 | while read -r size dir; do
        log "  ${size}MB - $(basename "$dir")"
    done
}

# Function to check disk space and alert if low
check_disk_space() {
    log "=== Checking disk space ==="
    
    local disk_usage=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $5}' | sed 's/%//')
    log "Current disk usage: ${disk_usage}%"
    
    if [ "$disk_usage" -gt 90 ]; then
        log "WARNING: Disk usage is critical (${disk_usage}%)"
        # Trigger emergency cleanup
        emergency_cleanup
    elif [ "$disk_usage" -gt 80 ]; then
        log "WARNING: Disk usage is high (${disk_usage}%)"
    fi
}

# Emergency cleanup when disk space is critical
emergency_cleanup() {
    log "=== EMERGENCY CLEANUP ACTIVATED ==="
    
    # More aggressive cleanup
    find "$PROJECT_ROOT" -name "*.log" -type f -size +50M | while read -r biglog; do
        safe_remove "$biglog" "emergency: large log file"
    done
    
    # Remove old compressed logs immediately
    find "$PROJECT_ROOT" -name "*.log.gz" -type f -mtime +7 | while read -r gzlog; do
        safe_remove "$gzlog" "emergency: old compressed log"
    done
    
    # Alert storage monitor if running
    if curl -f http://localhost:8490/emergency-alert >/dev/null 2>&1; then
        log "Alerted storage monitor of emergency cleanup"
    fi
}

# Main cleanup function
main() {
    local start_time=$(date +%s)
    log "=== Starting automated cleanup ==="
    
    if [ "$DRY_RUN" = "true" ]; then
        log "DRY RUN MODE - No files will be deleted"
    fi
    
    # Calculate initial space usage
    local total_space_before=$(du -sm "$PROJECT_ROOT" 2>/dev/null | cut -f1)
    
    # Run cleanup functions
    check_disk_space
    cleanup_stale_pids
    cleanup_temp_files
    compress_old_logs
    cleanup_old_logs
    cleanup_node_modules
    cleanup_git
    cleanup_docker
    
    # Generate final report
    generate_report "$total_space_before"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log "Cleanup completed in ${duration} seconds"
}

# Handle command line arguments
case "${1:-}" in
    --dry-run)
        DRY_RUN=true
        main
        ;;
    --emergency)
        log "Running emergency cleanup"
        emergency_cleanup
        ;;
    --help|-h)
        echo "Usage: $0 [options]"
        echo "Options:"
        echo "  --dry-run    Show what would be cleaned without making changes"
        echo "  --emergency  Run emergency cleanup for critical disk space"
        echo "  --help       Show this help message"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac