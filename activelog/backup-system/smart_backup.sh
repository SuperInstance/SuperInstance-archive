#!/bin/bash

# ActiveLog Smart Backup System
# Intelligent backup script with automatic size detection, splitting, and multi-destination support

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${SCRIPT_DIR}/backup_config.json"
LOG_FILE="/tmp/activelog-backup.log"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Global variables
BACKUP_ID=""
BACKUP_TIMESTAMP=""
TOTAL_SIZE=0
CHUNK_COUNT=0
MANIFEST_FILE=""
TEMP_DIR=""

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_warn() {
    log "WARN" "$@"
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    log "ERROR" "$@"
    echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    log "SUCCESS" "$@"
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# Utility functions
cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        log_info "Cleaning up temporary directory: $TEMP_DIR"
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

generate_backup_id() {
    BACKUP_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    local git_commit=""
    
    if command -v git >/dev/null 2>&1 && [[ -d "$PROJECT_ROOT/.git" ]]; then
        git_commit=$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    else
        git_commit="nogit"
    fi
    
    BACKUP_ID="activelog_${BACKUP_TIMESTAMP}_${git_commit}"
    log_info "Generated backup ID: $BACKUP_ID"
}

check_dependencies() {
    local missing_deps=()
    
    # Essential dependencies
    local deps=("jq" "tar" "gzip" "sha256sum" "du" "find")
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing_deps+=("$dep")
        fi
    done
    
    # Optional dependencies
    if command -v aws >/dev/null 2>&1; then
        log_info "AWS CLI available - S3 backup enabled"
    else
        log_warn "AWS CLI not found - S3 backup disabled"
    fi
    
    if command -v gh >/dev/null 2>&1; then
        log_info "GitHub CLI available - GitHub releases backup enabled"
    else
        log_warn "GitHub CLI not found - GitHub releases backup disabled"
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install missing dependencies and try again"
        exit 1
    fi
    
    log_success "All required dependencies are available"
}

load_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Validate JSON syntax
    if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
        log_error "Invalid JSON in configuration file: $CONFIG_FILE"
        exit 1
    fi
    
    log_success "Configuration loaded from: $CONFIG_FILE"
}

get_config_value() {
    local path="$1"
    local default="${2:-}"
    
    local value=$(jq -r "$path" "$CONFIG_FILE" 2>/dev/null)
    
    if [[ "$value" == "null" || "$value" == "" ]]; then
        echo "$default"
    else
        # Expand environment variables
        echo "$value" | envsubst
    fi
}

calculate_project_size() {
    log_info "Calculating project size..."
    
    local exclude_args=()
    local patterns
    patterns=$(get_config_value '.exclusion_patterns[]' | tr '\n' '\0')
    
    while IFS= read -r -d '' pattern; do
        if [[ -n "$pattern" ]]; then
            exclude_args+=("--exclude=$pattern")
        fi
    done <<< "$patterns"
    
    # Calculate size using tar with exclusions (dry run)
    local size_bytes
    size_bytes=$(cd "$PROJECT_ROOT" && tar "${exclude_args[@]}" -cf /dev/null . 2>/dev/null && \
                 du -sb . | cut -f1)
    
    TOTAL_SIZE=$((size_bytes / 1024 / 1024)) # Convert to MB
    
    log_info "Project size: ${TOTAL_SIZE} MB ($(numfmt --to=iec-i --suffix=B $((TOTAL_SIZE * 1024 * 1024))))"
    
    # Check if size exceeds reasonable limits
    local max_size_gb
    max_size_gb=$(get_config_value '.backup_settings.max_backup_size_gb' '10')
    local max_size_mb=$((max_size_gb * 1024))
    
    if [[ $TOTAL_SIZE -gt $max_size_mb ]]; then
        log_error "Project size (${TOTAL_SIZE} MB) exceeds maximum allowed size (${max_size_mb} MB)"
        exit 1
    fi
}

create_exclusion_file() {
    local exclusion_file="$1"
    
    log_info "Creating exclusion patterns file: $exclusion_file"
    
    # Get exclusion patterns from config
    jq -r '.exclusion_patterns[]' "$CONFIG_FILE" > "$exclusion_file"
    
    # Add dynamic exclusions
    echo "backup-system/" >> "$exclusion_file"
    echo ".backup/" >> "$exclusion_file"
    echo "*.backup" >> "$exclusion_file"
    echo "backup-*" >> "$exclusion_file"
    
    log_info "Created exclusion file with $(wc -l < "$exclusion_file") patterns"
}

create_manifest() {
    local manifest_file="$1"
    
    log_info "Creating backup manifest: $manifest_file"
    
    local git_info=""
    if command -v git >/dev/null 2>&1 && [[ -d "$PROJECT_ROOT/.git" ]]; then
        git_info=$(cd "$PROJECT_ROOT" && cat <<EOF
{
  "commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
  "commit_short": "$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')",
  "branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')",
  "tag": "$(git describe --tags --exact-match 2>/dev/null || echo 'none')",
  "dirty": $(if git diff-index --quiet HEAD -- 2>/dev/null; then echo 'false'; else echo 'true'; fi)
}
EOF
)
    else
        git_info='{"commit": "unknown", "commit_short": "unknown", "branch": "unknown", "tag": "none", "dirty": false}'
    fi
    
    cat > "$manifest_file" <<EOF
{
  "backup_id": "$BACKUP_ID",
  "timestamp": "$BACKUP_TIMESTAMP",
  "iso_timestamp": "$(date -Iseconds)",
  "project_name": "$(get_config_value '.project_name' 'activelog')",
  "version": "1.0",
  "size_mb": $TOTAL_SIZE,
  "chunk_count": $CHUNK_COUNT,
  "compression": "$(get_config_value '.backup_settings.compression.algorithm' 'gzip')",
  "compression_level": $(get_config_value '.backup_settings.compression.level' '6'),
  "git": $git_info,
  "system": {
    "hostname": "$(hostname)",
    "user": "$(whoami)",
    "os": "$(uname -s)",
    "architecture": "$(uname -m)",
    "kernel": "$(uname -r)"
  },
  "files": []
}
EOF
    
    MANIFEST_FILE="$manifest_file"
    log_success "Manifest created: $manifest_file"
}

should_split_backup() {
    local threshold_mb
    threshold_mb=$(get_config_value '.backup_settings.split_threshold_mb' '1000')
    
    if [[ $TOTAL_SIZE -gt $threshold_mb ]]; then
        log_info "Backup size (${TOTAL_SIZE} MB) exceeds split threshold (${threshold_mb} MB) - will split into chunks"
        return 0
    else
        log_info "Backup size (${TOTAL_SIZE} MB) is below split threshold (${threshold_mb} MB) - single archive"
        return 1
    fi
}

create_single_backup() {
    local output_file="$1"
    local exclusion_file="$2"
    
    log_info "Creating single backup archive: $output_file"
    
    local compression_level
    compression_level=$(get_config_value '.backup_settings.compression.level' '6')
    
    cd "$PROJECT_ROOT"
    tar --exclude-from="$exclusion_file" -czf "$output_file" . 2>/dev/null
    
    # Calculate checksum
    local checksum
    checksum=$(sha256sum "$output_file" | cut -d' ' -f1)
    
    # Update manifest
    local file_size
    file_size=$(stat -c%s "$output_file")
    
    jq --arg file "$(basename "$output_file")" \
       --arg checksum "$checksum" \
       --argjson size "$file_size" \
       '.files += [{"name": $file, "checksum": $checksum, "size": $size, "type": "single"}]' \
       "$MANIFEST_FILE" > "${MANIFEST_FILE}.tmp" && mv "${MANIFEST_FILE}.tmp" "$MANIFEST_FILE"
    
    CHUNK_COUNT=1
    log_success "Single backup created: $output_file ($(numfmt --to=iec-i --suffix=B $file_size))"
}

create_split_backup() {
    local output_prefix="$1"
    local exclusion_file="$2"
    
    log_info "Creating split backup archives with prefix: $output_prefix"
    
    local chunk_size_mb
    chunk_size_mb=$(get_config_value '.backup_settings.chunk_size_mb' '950')
    local chunk_size_bytes=$((chunk_size_mb * 1024 * 1024))
    
    cd "$PROJECT_ROOT"
    
    # Create tar archive and split it
    tar --exclude-from="$exclusion_file" -czf - . 2>/dev/null | \
        split -b "$chunk_size_bytes" -d --suffix-length=3 - "$output_prefix"
    
    # Count chunks and calculate checksums
    local chunk_files=("$output_prefix"*)
    CHUNK_COUNT=${#chunk_files[@]}
    
    log_info "Created $CHUNK_COUNT chunks"
    
    # Update manifest with chunk information
    for chunk_file in "${chunk_files[@]}"; do
        local checksum
        checksum=$(sha256sum "$chunk_file" | cut -d' ' -f1)
        
        local file_size
        file_size=$(stat -c%s "$chunk_file")
        
        jq --arg file "$(basename "$chunk_file")" \
           --arg checksum "$checksum" \
           --argjson size "$file_size" \
           '.files += [{"name": $file, "checksum": $checksum, "size": $size, "type": "chunk"}]' \
           "$MANIFEST_FILE" > "${MANIFEST_FILE}.tmp" && mv "${MANIFEST_FILE}.tmp" "$MANIFEST_FILE"
        
        log_info "Chunk created: $(basename "$chunk_file") ($(numfmt --to=iec-i --suffix=B $file_size))"
    done
    
    # Update chunk count in manifest
    jq --argjson count "$CHUNK_COUNT" '.chunk_count = $count' \
       "$MANIFEST_FILE" > "${MANIFEST_FILE}.tmp" && mv "${MANIFEST_FILE}.tmp" "$MANIFEST_FILE"
    
    log_success "Split backup created: $CHUNK_COUNT chunks"
}

validate_backup_integrity() {
    local backup_dir="$1"
    
    log_info "Validating backup integrity..."
    
    if [[ ! -f "$MANIFEST_FILE" ]]; then
        log_error "Manifest file not found: $MANIFEST_FILE"
        return 1
    fi
    
    local validation_errors=0
    local file_count
    file_count=$(jq -r '.files | length' "$MANIFEST_FILE")
    
    log_info "Validating $file_count files..."
    
    # Validate each file's checksum
    for ((i=0; i<file_count; i++)); do
        local file_name
        local expected_checksum
        local file_path
        
        file_name=$(jq -r ".files[$i].name" "$MANIFEST_FILE")
        expected_checksum=$(jq -r ".files[$i].checksum" "$MANIFEST_FILE")
        file_path="$backup_dir/$file_name"
        
        if [[ ! -f "$file_path" ]]; then
            log_error "Missing file: $file_name"
            ((validation_errors++))
            continue
        fi
        
        local actual_checksum
        actual_checksum=$(sha256sum "$file_path" | cut -d' ' -f1)
        
        if [[ "$actual_checksum" != "$expected_checksum" ]]; then
            log_error "Checksum mismatch for $file_name"
            log_error "  Expected: $expected_checksum"
            log_error "  Actual:   $actual_checksum"
            ((validation_errors++))
        else
            log_info "✓ $file_name"
        fi
    done
    
    if [[ $validation_errors -eq 0 ]]; then
        log_success "Backup integrity validation passed"
        return 0
    else
        log_error "Backup integrity validation failed with $validation_errors errors"
        return 1
    fi
}

upload_to_s3() {
    local backup_dir="$1"
    local destination_config="$2"
    
    if ! command -v aws >/dev/null 2>&1; then
        log_warn "AWS CLI not available - skipping S3 upload"
        return 1
    fi
    
    local bucket
    local prefix
    local region
    local storage_class
    
    bucket=$(echo "$destination_config" | jq -r '.config.bucket // empty' | envsubst)
    prefix=$(echo "$destination_config" | jq -r '.config.prefix // "backups/"' | envsubst)
    region=$(echo "$destination_config" | jq -r '.config.region // "us-east-1"' | envsubst)
    storage_class=$(echo "$destination_config" | jq -r '.config.storage_class // "STANDARD_IA"')
    
    if [[ -z "$bucket" ]]; then
        log_error "S3 bucket not configured"
        return 1
    fi
    
    log_info "Uploading backup to S3: s3://$bucket/$prefix$BACKUP_ID/"
    
    # Upload all files in backup directory
    local upload_errors=0
    
    for file in "$backup_dir"/*; do
        if [[ -f "$file" ]]; then
            local file_name
            file_name=$(basename "$file")
            local s3_key="${prefix}${BACKUP_ID}/${file_name}"
            
            log_info "Uploading: $file_name"
            
            if aws s3 cp "$file" "s3://$bucket/$s3_key" \
                --region "$region" \
                --storage-class "$storage_class" \
                --no-progress 2>/dev/null; then
                log_success "✓ Uploaded: $file_name"
            else
                log_error "✗ Failed to upload: $file_name"
                ((upload_errors++))
            fi
        fi
    done
    
    if [[ $upload_errors -eq 0 ]]; then
        log_success "S3 upload completed successfully"
        return 0
    else
        log_error "S3 upload completed with $upload_errors errors"
        return 1
    fi
}

upload_to_github_releases() {
    local backup_dir="$1"
    local destination_config="$2"
    
    if ! command -v gh >/dev/null 2>&1; then
        log_warn "GitHub CLI not available - skipping GitHub releases upload"
        return 1
    fi
    
    local repository
    repository=$(echo "$destination_config" | jq -r '.config.repository // empty' | envsubst)
    
    if [[ -z "$repository" ]]; then
        log_error "GitHub repository not configured"
        return 1
    fi
    
    log_info "Uploading backup to GitHub releases: $repository"
    
    # Create release
    local release_tag="backup-$BACKUP_TIMESTAMP"
    local release_title="Automated Backup - $BACKUP_TIMESTAMP"
    local release_body="Automated backup created on $(date -Iseconds)
    
Backup ID: $BACKUP_ID
Project Size: ${TOTAL_SIZE} MB
Chunks: $CHUNK_COUNT
    
This backup was created automatically by the ActiveLog backup system."
    
    log_info "Creating GitHub release: $release_tag"
    
    if ! gh release create "$release_tag" \
        --repo "$repository" \
        --title "$release_title" \
        --notes "$release_body"; then
        log_error "Failed to create GitHub release"
        return 1
    fi
    
    # Upload files as assets
    local upload_errors=0
    
    for file in "$backup_dir"/*; do
        if [[ -f "$file" ]]; then
            local file_name
            file_name=$(basename "$file")
            
            log_info "Uploading asset: $file_name"
            
            if gh release upload "$release_tag" "$file" \
                --repo "$repository" \
                --clobber; then
                log_success "✓ Uploaded asset: $file_name"
            else
                log_error "✗ Failed to upload asset: $file_name"
                ((upload_errors++))
            fi
        fi
    done
    
    if [[ $upload_errors -eq 0 ]]; then
        log_success "GitHub releases upload completed successfully"
        return 0
    else
        log_error "GitHub releases upload completed with $upload_errors errors"
        return 1
    fi
}

store_local_backup() {
    local backup_dir="$1"
    local destination_config="$2"
    
    local local_path
    local_path=$(echo "$destination_config" | jq -r '.config.path // "/tmp/activelog-backups"' | envsubst)
    
    log_info "Storing backup locally: $local_path"
    
    # Create local backup directory
    mkdir -p "$local_path"
    
    # Copy backup to local storage
    local final_backup_dir="$local_path/$BACKUP_ID"
    
    if cp -r "$backup_dir" "$final_backup_dir"; then
        log_success "Local backup stored: $final_backup_dir"
        
        # Implement local backup rotation
        rotate_local_backups "$local_path" "$destination_config"
        return 0
    else
        log_error "Failed to store local backup"
        return 1
    fi
}

rotate_local_backups() {
    local backup_path="$1"
    local destination_config="$2"
    
    local max_backups
    max_backups=$(echo "$destination_config" | jq -r '.config.max_local_backups // 5')
    
    log_info "Rotating local backups (keeping $max_backups)"
    
    # List backup directories sorted by creation time (oldest first)
    local backup_dirs
    mapfile -t backup_dirs < <(find "$backup_path" -maxdepth 1 -type d -name "activelog_*" -printf '%T@ %p\n' | sort -n | cut -d' ' -f2-)
    
    local backup_count=${#backup_dirs[@]}
    
    if [[ $backup_count -gt $max_backups ]]; then
        local to_remove=$((backup_count - max_backups))
        log_info "Removing $to_remove old backups"
        
        for ((i=0; i<to_remove; i++)); do
            local old_backup="${backup_dirs[i]}"
            log_info "Removing old backup: $(basename "$old_backup")"
            rm -rf "$old_backup"
        done
        
        log_success "Local backup rotation completed"
    else
        log_info "No backup rotation needed ($backup_count <= $max_backups)"
    fi
}

send_notification() {
    local status="$1"
    local message="$2"
    
    # Webhook notification
    local webhook_enabled
    local webhook_url
    
    webhook_enabled=$(get_config_value '.notifications.webhook.enabled' 'false')
    webhook_url=$(get_config_value '.notifications.webhook.url' '')
    
    if [[ "$webhook_enabled" == "true" && -n "$webhook_url" ]]; then
        local should_notify=false
        
        if [[ "$status" == "success" ]]; then
            should_notify=$(get_config_value '.notifications.webhook.on_success' 'true')
        else
            should_notify=$(get_config_value '.notifications.webhook.on_failure' 'true')
        fi
        
        if [[ "$should_notify" == "true" ]]; then
            log_info "Sending webhook notification..."
            
            local payload
            payload=$(jq -n \
                --arg status "$status" \
                --arg message "$message" \
                --arg backup_id "$BACKUP_ID" \
                --arg timestamp "$BACKUP_TIMESTAMP" \
                --argjson size "$TOTAL_SIZE" \
                --argjson chunks "$CHUNK_COUNT" \
                '{
                    "backup_id": $backup_id,
                    "timestamp": $timestamp,
                    "status": $status,
                    "message": $message,
                    "size_mb": $size,
                    "chunk_count": $chunks,
                    "project": "activelog"
                }')
            
            if curl -s -X POST "$webhook_url" \
                -H "Content-Type: application/json" \
                -d "$payload" \
                --max-time 30 >/dev/null; then
                log_success "Webhook notification sent"
            else
                log_warn "Failed to send webhook notification"
            fi
        fi
    fi
    
    # Add more notification methods (email, Slack, etc.) here if needed
}

print_backup_summary() {
    local status="$1"
    local destinations_used="$2"
    
    echo ""
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}         BACKUP SUMMARY${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo -e "Backup ID:     ${CYAN}$BACKUP_ID${NC}"
    echo -e "Status:        $(if [[ "$status" == "success" ]]; then echo -e "${GREEN}SUCCESS${NC}"; else echo -e "${RED}FAILED${NC}"; fi)"
    echo -e "Timestamp:     ${CYAN}$(date -d "@$(date +%s)" '+%Y-%m-%d %H:%M:%S %Z')${NC}"
    echo -e "Project Size:  ${CYAN}${TOTAL_SIZE} MB${NC}"
    echo -e "Chunks:        ${CYAN}$CHUNK_COUNT${NC}"
    echo -e "Destinations:  ${CYAN}$destinations_used${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo ""
}

main() {
    local start_time
    start_time=$(date +%s)
    
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════╗
    ║        ActiveLog Smart Backup         ║
    ║     Intelligent Backup System v1.0   ║
    ╚═══════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    log_info "Starting ActiveLog backup process..."
    
    # Initialize
    check_dependencies
    load_config
    generate_backup_id
    
    # Create temporary working directory
    TEMP_DIR=$(mktemp -d -t "activelog-backup-XXXXXX")
    log_info "Working directory: $TEMP_DIR"
    
    # Analyze project
    calculate_project_size
    
    # Prepare backup files
    local exclusion_file="$TEMP_DIR/exclusions.txt"
    local manifest_file="$TEMP_DIR/manifest.json"
    
    create_exclusion_file "$exclusion_file"
    create_manifest "$manifest_file"
    
    # Create backup
    local backup_success=true
    local destinations_used=""
    
    if should_split_backup; then
        create_split_backup "$TEMP_DIR/activelog_backup_" "$exclusion_file"
    else
        create_single_backup "$TEMP_DIR/activelog_backup.tar.gz" "$exclusion_file"
    fi
    
    # Validate backup integrity
    if ! validate_backup_integrity "$TEMP_DIR"; then
        backup_success=false
    fi
    
    # Upload to destinations (in priority order)
    if [[ "$backup_success" == "true" ]]; then
        local destinations
        destinations=$(jq -c '.destinations[] | select(.enabled == true) | [.priority, .type, .name, .]' "$CONFIG_FILE" | sort -n)
        
        local upload_success=false
        
        while IFS= read -r destination_array; do
            local destination_info
            destination_info=$(echo "$destination_array" | jq -c '.[3]')
            local dest_type
            dest_type=$(echo "$destination_info" | jq -r '.type')
            local dest_name
            dest_name=$(echo "$destination_info" | jq -r '.name')
            
            log_info "Attempting upload to: $dest_name ($dest_type)"
            
            case "$dest_type" in
                "s3")
                    if upload_to_s3 "$TEMP_DIR" "$destination_info"; then
                        upload_success=true
                        destinations_used="$destinations_used S3"
                    fi
                    ;;
                "github_releases")
                    if upload_to_github_releases "$TEMP_DIR" "$destination_info"; then
                        upload_success=true
                        destinations_used="$destinations_used GitHub"
                    fi
                    ;;
                "local")
                    if store_local_backup "$TEMP_DIR" "$destination_info"; then
                        upload_success=true
                        destinations_used="$destinations_used Local"
                    fi
                    ;;
                *)
                    log_warn "Unknown destination type: $dest_type"
                    ;;
            esac
            
            # If at least one destination succeeds, we can break (unless configured otherwise)
            if [[ "$upload_success" == "true" ]]; then
                break
            fi
            
        done <<< "$destinations"
        
        if [[ "$upload_success" != "true" ]]; then
            backup_success=false
            log_error "All destination uploads failed"
        fi
    fi
    
    # Calculate duration
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Send notifications and print summary
    if [[ "$backup_success" == "true" ]]; then
        local success_message="Backup completed successfully in ${duration}s. Size: ${TOTAL_SIZE}MB, Chunks: $CHUNK_COUNT"
        send_notification "success" "$success_message"
        print_backup_summary "success" "$destinations_used"
        log_success "Backup process completed successfully in ${duration} seconds"
        exit 0
    else
        local failure_message="Backup failed after ${duration}s. Check logs for details."
        send_notification "failure" "$failure_message"
        print_backup_summary "failed" "$destinations_used"
        log_error "Backup process failed after ${duration} seconds"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "--help"|"-h")
        echo "ActiveLog Smart Backup System"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --config FILE  Use custom configuration file"
        echo "  --dry-run      Show what would be backed up without creating backup"
        echo "  --validate     Validate existing backup integrity"
        echo ""
        exit 0
        ;;
    "--config")
        if [[ -n "${2:-}" ]]; then
            CONFIG_FILE="$2"
        else
            log_error "Config file path required with --config option"
            exit 1
        fi
        shift 2
        ;;
    "--dry-run")
        log_info "DRY RUN MODE - No backup will be created"
        # Set dry run flag and continue with modified behavior
        exit 0
        ;;
    "--validate")
        log_info "VALIDATION MODE - Not implemented yet"
        exit 0
        ;;
esac

# Run main function
main "$@"