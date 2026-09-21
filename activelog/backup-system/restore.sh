#!/bin/bash

# ActiveLog Backup Restore System
# Intelligent restore script that can restore from any backup source

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/backup_config.json"
LOG_FILE="/tmp/activelog-restore.log"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Global variables
RESTORE_SOURCE=""
RESTORE_TARGET=""
BACKUP_ID=""
TEMP_DIR=""
MANIFEST_FILE=""
DRY_RUN=false
VERIFY_ONLY=false

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

show_help() {
    cat << 'EOF'
ActiveLog Backup Restore System

USAGE:
    restore.sh [OPTIONS] <BACKUP_SOURCE> [TARGET_DIRECTORY]

BACKUP SOURCES:
    Local path:           /path/to/backup/directory
    GitHub release:       github:owner/repo:tag-name
    S3 location:          s3://bucket/prefix/backup-id/
    Backup ID:            backup-id (searches all configured sources)

OPTIONS:
    -h, --help           Show this help message
    -c, --config FILE    Use custom configuration file
    -d, --dry-run        Show what would be restored without actual restoration
    -v, --verify         Verify backup integrity only (don't restore)
    -f, --force          Force restore even if target directory exists
    -q, --quiet          Suppress non-error output
    --no-verify          Skip integrity verification
    --list-backups       List available backups from all sources

EXAMPLES:
    # Restore from local backup directory
    restore.sh /tmp/activelog-backups/activelog_20240123_143022_abc123

    # Restore from GitHub release
    restore.sh github:myorg/activelog:backup-20240123_143022

    # Restore from S3
    restore.sh s3://my-backup-bucket/activelog-backups/activelog_20240123_143022_abc123/

    # Auto-find and restore latest backup
    restore.sh latest

    # Dry run to see what would be restored
    restore.sh --dry-run github:myorg/activelog:backup-20240123_143022

    # Verify backup integrity only
    restore.sh --verify /path/to/backup

    # List all available backups
    restore.sh --list-backups

EOF
}

cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        log_info "Cleaning up temporary directory: $TEMP_DIR"
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

check_dependencies() {
    local missing_deps=()
    
    # Essential dependencies
    local deps=("jq" "tar" "gzip" "sha256sum" "curl")
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing_deps+=("$dep")
        fi
    done
    
    # Optional dependencies
    if command -v aws >/dev/null 2>&1; then
        log_info "AWS CLI available - S3 restore enabled"
    else
        log_warn "AWS CLI not found - S3 restore disabled"
    fi
    
    if command -v gh >/dev/null 2>&1; then
        log_info "GitHub CLI available - GitHub releases restore enabled"
    else
        log_warn "GitHub CLI not found - GitHub releases restore disabled"
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
        log_warn "Configuration file not found: $CONFIG_FILE"
        log_info "Using default configuration"
        return 0
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
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "$default"
        return
    fi
    
    local value=$(jq -r "$path" "$CONFIG_FILE" 2>/dev/null)
    
    if [[ "$value" == "null" || "$value" == "" ]]; then
        echo "$default"
    else
        # Expand environment variables
        echo "$value" | envsubst 2>/dev/null || echo "$value"
    fi
}

parse_backup_source() {
    local source="$1"
    
    log_info "Parsing backup source: $source"
    
    if [[ "$source" == "latest" ]]; then
        log_info "Finding latest backup from configured sources..."
        find_latest_backup
        return
    elif [[ "$source" =~ ^github: ]]; then
        # GitHub release format: github:owner/repo:tag-name
        if [[ "$source" =~ ^github:([^:]+):([^:]+)$ ]]; then
            RESTORE_SOURCE="github"
            export GITHUB_REPO="${BASH_REMATCH[1]}"
            export GITHUB_TAG="${BASH_REMATCH[2]}"
            log_info "GitHub source: $GITHUB_REPO @ $GITHUB_TAG"
        else
            log_error "Invalid GitHub source format. Use: github:owner/repo:tag-name"
            exit 1
        fi
    elif [[ "$source" =~ ^s3:// ]]; then
        # S3 format: s3://bucket/prefix/backup-id/
        RESTORE_SOURCE="s3"
        export S3_URL="$source"
        log_info "S3 source: $source"
    elif [[ -d "$source" ]]; then
        # Local directory
        RESTORE_SOURCE="local"
        export LOCAL_PATH="$(realpath "$source")"
        log_info "Local source: $LOCAL_PATH"
    elif [[ "$source" =~ ^activelog_.+_.+$ ]]; then
        # Backup ID format: activelog_timestamp_commit
        log_info "Searching for backup ID: $source"
        search_backup_by_id "$source"
    else
        log_error "Unknown backup source format: $source"
        log_error "See --help for supported formats"
        exit 1
    fi
}

find_latest_backup() {
    log_info "Searching for latest backup across all configured sources..."
    
    local latest_backup=""
    local latest_timestamp=0
    
    # Search GitHub releases
    if command -v gh >/dev/null 2>&1; then
        local github_repo
        github_repo=$(get_config_value '.destinations[] | select(.type == "github_releases") | .config.repository' '')
        
        if [[ -n "$github_repo" ]]; then
            github_repo=$(echo "$github_repo" | envsubst)
            log_info "Checking GitHub releases in: $github_repo"
            
            local latest_release
            latest_release=$(gh release list --repo "$github_repo" --limit 10 --json tagName,createdAt 2>/dev/null | \
                           jq -r '.[] | select(.tagName | startswith("backup-")) | "\(.createdAt) github:\(env.github_repo):\(.tagName)"' | \
                           sort -nr | head -n1 || echo "")
            
            if [[ -n "$latest_release" ]]; then
                local release_time release_source
                release_time=$(echo "$latest_release" | cut -d' ' -f1)
                release_source=$(echo "$latest_release" | cut -d' ' -f2-)
                
                local release_timestamp
                release_timestamp=$(date -d "$release_time" +%s 2>/dev/null || echo "0")
                
                if [[ $release_timestamp -gt $latest_timestamp ]]; then
                    latest_timestamp=$release_timestamp
                    latest_backup="$release_source"
                    log_info "Found GitHub backup: $release_source ($release_time)"
                fi
            fi
        fi
    fi
    
    # Search local backups
    local local_path
    local_path=$(get_config_value '.destinations[] | select(.type == "local") | .config.path' '/tmp/activelog-backups')
    local_path=$(echo "$local_path" | envsubst)
    
    if [[ -d "$local_path" ]]; then
        log_info "Checking local backups in: $local_path"
        
        local local_backups
        local_backups=$(find "$local_path" -maxdepth 1 -type d -name "activelog_*" -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 || echo "")
        
        if [[ -n "$local_backups" ]]; then
            local backup_time backup_path
            backup_time=$(echo "$local_backups" | cut -d' ' -f1)
            backup_path=$(echo "$local_backups" | cut -d' ' -f2-)
            
            local backup_timestamp
            backup_timestamp=$(printf "%.0f" "$backup_time")
            
            if [[ $backup_timestamp -gt $latest_timestamp ]]; then
                latest_timestamp=$backup_timestamp
                latest_backup="$backup_path"
                log_info "Found local backup: $backup_path ($(date -d "@$backup_timestamp"))"
            fi
        fi
    fi
    
    # Search S3 (if configured)
    if command -v aws >/dev/null 2>&1; then
        local s3_bucket s3_prefix
        s3_bucket=$(get_config_value '.destinations[] | select(.type == "s3") | .config.bucket' '')
        s3_prefix=$(get_config_value '.destinations[] | select(.type == "s3") | .config.prefix' 'activelog-backups/')
        
        s3_bucket=$(echo "$s3_bucket" | envsubst)
        s3_prefix=$(echo "$s3_prefix" | envsubst)
        
        if [[ -n "$s3_bucket" ]]; then
            log_info "Checking S3 backups in: s3://$s3_bucket/$s3_prefix"
            
            local s3_backups
            s3_backups=$(aws s3 ls "s3://$s3_bucket/$s3_prefix" --recursive | \
                        grep "manifest.json$" | \
                        sort -k1,2 -nr | head -n1 | \
                        awk '{print $4}' || echo "")
            
            if [[ -n "$s3_backups" ]]; then
                # Extract backup directory from manifest path
                local s3_backup_dir
                s3_backup_dir=$(dirname "$s3_backups")
                local s3_backup_url="s3://$s3_bucket/$s3_backup_dir/"
                
                # Get modification time
                local s3_time
                s3_time=$(aws s3 ls "s3://$s3_bucket/$s3_backups" | awk '{print $1 " " $2}')
                local s3_timestamp
                s3_timestamp=$(date -d "$s3_time" +%s 2>/dev/null || echo "0")
                
                if [[ $s3_timestamp -gt $latest_timestamp ]]; then
                    latest_timestamp=$s3_timestamp
                    latest_backup="$s3_backup_url"
                    log_info "Found S3 backup: $s3_backup_url ($s3_time)"
                fi
            fi
        fi
    fi
    
    if [[ -n "$latest_backup" ]]; then
        log_success "Latest backup found: $latest_backup"
        parse_backup_source "$latest_backup"
    else
        log_error "No backups found in any configured source"
        exit 1
    fi
}

search_backup_by_id() {
    local backup_id="$1"
    
    log_info "Searching for backup ID: $backup_id"
    
    # Try local first
    local local_path
    local_path=$(get_config_value '.destinations[] | select(.type == "local") | .config.path' '/tmp/activelog-backups')
    local_path=$(echo "$local_path" | envsubst)
    
    local local_backup="$local_path/$backup_id"
    if [[ -d "$local_backup" ]]; then
        log_success "Found local backup: $local_backup"
        RESTORE_SOURCE="local"
        export LOCAL_PATH="$local_backup"
        return
    fi
    
    # Try GitHub releases
    if command -v gh >/dev/null 2>&1; then
        local github_repo
        github_repo=$(get_config_value '.destinations[] | select(.type == "github_releases") | .config.repository' '')
        
        if [[ -n "$github_repo" ]]; then
            github_repo=$(echo "$github_repo" | envsubst)
            
            # Search for release with backup ID in the name
            local matching_releases
            matching_releases=$(gh release list --repo "$github_repo" --limit 50 --json tagName 2>/dev/null | \
                              jq -r '.[] | select(.tagName | contains("'$backup_id'")) | .tagName' | head -n1 || echo "")
            
            if [[ -n "$matching_releases" ]]; then
                log_success "Found GitHub release: $matching_releases"
                RESTORE_SOURCE="github"
                export GITHUB_REPO="$github_repo"
                export GITHUB_TAG="$matching_releases"
                return
            fi
        fi
    fi
    
    # Try S3
    if command -v aws >/dev/null 2>&1; then
        local s3_bucket s3_prefix
        s3_bucket=$(get_config_value '.destinations[] | select(.type == "s3") | .config.bucket' '')
        s3_prefix=$(get_config_value '.destinations[] | select(.type == "s3") | .config.prefix' 'activelog-backups/')
        
        s3_bucket=$(echo "$s3_bucket" | envsubst)
        s3_prefix=$(echo "$s3_prefix" | envsubst)
        
        if [[ -n "$s3_bucket" ]]; then
            local s3_backup_path="${s3_prefix}${backup_id}/"
            
            # Check if backup exists in S3
            if aws s3 ls "s3://$s3_bucket/$s3_backup_path" >/dev/null 2>&1; then
                log_success "Found S3 backup: s3://$s3_bucket/$s3_backup_path"
                RESTORE_SOURCE="s3"
                export S3_URL="s3://$s3_bucket/$s3_backup_path"
                return
            fi
        fi
    fi
    
    log_error "Backup ID not found: $backup_id"
    exit 1
}

download_backup_local() {
    local source_path="$LOCAL_PATH"
    
    log_info "Using local backup: $source_path"
    
    if [[ ! -d "$source_path" ]]; then
        log_error "Local backup directory not found: $source_path"
        exit 1
    fi
    
    # Copy files to temp directory
    log_info "Copying backup files to temporary location..."
    cp -r "$source_path"/* "$TEMP_DIR/"
    
    log_success "Local backup files prepared"
}

download_backup_github() {
    local repo="$GITHUB_REPO"
    local tag="$GITHUB_TAG"
    
    log_info "Downloading backup from GitHub: $repo @ $tag"
    
    if ! command -v gh >/dev/null 2>&1; then
        log_error "GitHub CLI not available for GitHub restore"
        exit 1
    fi
    
    # List release assets
    local assets
    assets=$(gh release view "$tag" --repo "$repo" --json assets --jq '.assets[].name' 2>/dev/null || echo "")
    
    if [[ -z "$assets" ]]; then
        log_error "No assets found in release: $repo @ $tag"
        exit 1
    fi
    
    log_info "Found $(echo "$assets" | wc -l) assets in release"
    
    # Download all assets
    local download_errors=0
    
    while IFS= read -r asset; do
        if [[ -n "$asset" ]]; then
            log_info "Downloading: $asset"
            
            if gh release download "$tag" --repo "$repo" --pattern "$asset" --dir "$TEMP_DIR" >/dev/null 2>&1; then
                log_success "✓ Downloaded: $asset"
            else
                log_error "✗ Failed to download: $asset"
                ((download_errors++))
            fi
        fi
    done <<< "$assets"
    
    if [[ $download_errors -gt 0 ]]; then
        log_error "Failed to download $download_errors assets"
        exit 1
    fi
    
    log_success "GitHub backup downloaded successfully"
}

download_backup_s3() {
    local s3_url="$S3_URL"
    
    log_info "Downloading backup from S3: $s3_url"
    
    if ! command -v aws >/dev/null 2>&1; then
        log_error "AWS CLI not available for S3 restore"
        exit 1
    fi
    
    # Download all files from S3 prefix
    log_info "Downloading backup files from S3..."
    
    if aws s3 cp "$s3_url" "$TEMP_DIR/" --recursive --no-progress 2>/dev/null; then
        log_success "S3 backup downloaded successfully"
    else
        log_error "Failed to download backup from S3"
        exit 1
    fi
}

verify_backup_integrity() {
    log_info "Verifying backup integrity..."
    
    # Find manifest file
    MANIFEST_FILE=$(find "$TEMP_DIR" -name "manifest.json" -type f | head -n1)
    
    if [[ ! -f "$MANIFEST_FILE" ]]; then
        log_error "Manifest file not found in backup"
        exit 1
    fi
    
    log_info "Using manifest: $(basename "$MANIFEST_FILE")"
    
    # Extract backup information
    local backup_id project_name chunk_count
    backup_id=$(jq -r '.backup_id // "unknown"' "$MANIFEST_FILE")
    project_name=$(jq -r '.project_name // "unknown"' "$MANIFEST_FILE")
    chunk_count=$(jq -r '.chunk_count // 0' "$MANIFEST_FILE")
    
    log_info "Backup ID: $backup_id"
    log_info "Project: $project_name"
    log_info "Chunks: $chunk_count"
    
    BACKUP_ID="$backup_id"
    
    # Verify file checksums
    local validation_errors=0
    local file_count
    file_count=$(jq -r '.files | length' "$MANIFEST_FILE")
    
    log_info "Verifying $file_count files..."
    
    for ((i=0; i<file_count; i++)); do
        local file_name expected_checksum file_path
        
        file_name=$(jq -r ".files[$i].name" "$MANIFEST_FILE")
        expected_checksum=$(jq -r ".files[$i].checksum" "$MANIFEST_FILE")
        file_path="$TEMP_DIR/$file_name"
        
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
        log_success "Backup integrity verification passed"
        return 0
    else
        log_error "Backup integrity verification failed with $validation_errors errors"
        return 1
    fi
}

extract_backup() {
    local target_dir="$1"
    
    log_info "Extracting backup to: $target_dir"
    
    if [[ ! -f "$MANIFEST_FILE" ]]; then
        log_error "Manifest file required for extraction"
        exit 1
    fi
    
    # Create target directory
    mkdir -p "$target_dir"
    
    # Determine extraction method based on file structure
    local chunk_count
    chunk_count=$(jq -r '.chunk_count // 1' "$MANIFEST_FILE")
    
    if [[ $chunk_count -eq 1 ]]; then
        # Single archive
        local archive_file
        archive_file=$(jq -r '.files[] | select(.type == "single") | .name' "$MANIFEST_FILE")
        
        if [[ -z "$archive_file" ]]; then
            archive_file=$(jq -r '.files[0].name' "$MANIFEST_FILE")
        fi
        
        local archive_path="$TEMP_DIR/$archive_file"
        
        if [[ ! -f "$archive_path" ]]; then
            log_error "Archive file not found: $archive_file"
            exit 1
        fi
        
        log_info "Extracting single archive: $archive_file"
        
        if tar -xzf "$archive_path" -C "$target_dir" 2>/dev/null; then
            log_success "Single archive extracted successfully"
        else
            log_error "Failed to extract archive: $archive_file"
            exit 1
        fi
        
    else
        # Split archive - reassemble and extract
        log_info "Reassembling $chunk_count chunks..."
        
        # Get chunk files in correct order
        local chunk_files=()
        for ((i=0; i<chunk_count; i++)); do
            # Try different naming patterns
            local chunk_patterns=(
                "activelog_backup_$(printf "%03d" $i)"
                "activelog_backup_$(printf "%02d" $i)"
                "activelog_backup_$i"
            )
            
            local found_chunk=""
            for pattern in "${chunk_patterns[@]}"; do
                if [[ -f "$TEMP_DIR/$pattern" ]]; then
                    found_chunk="$pattern"
                    break
                fi
            done
            
            if [[ -n "$found_chunk" ]]; then
                chunk_files+=("$TEMP_DIR/$found_chunk")
                log_info "Found chunk $((i+1))/$chunk_count: $found_chunk"
            else
                log_error "Missing chunk $((i+1))/$chunk_count"
                exit 1
            fi
        done
        
        # Reassemble and extract
        log_info "Reassembling and extracting chunks..."
        
        if cat "${chunk_files[@]}" | tar -xzf - -C "$target_dir" 2>/dev/null; then
            log_success "Split archive reassembled and extracted successfully"
        else
            log_error "Failed to reassemble and extract split archive"
            exit 1
        fi
    fi
    
    log_success "Backup extracted to: $target_dir"
}

list_backups() {
    echo -e "${CYAN}Available Backups:${NC}"
    echo "=================="
    
    local found_backups=false
    
    # List local backups
    local local_path
    local_path=$(get_config_value '.destinations[] | select(.type == "local") | .config.path' '/tmp/activelog-backups')
    local_path=$(echo "$local_path" | envsubst)
    
    if [[ -d "$local_path" ]]; then
        echo -e "\n${YELLOW}Local Backups ($local_path):${NC}"
        local local_backups
        local_backups=$(find "$local_path" -maxdepth 1 -type d -name "activelog_*" -printf '%T@ %f\n' 2>/dev/null | sort -nr || echo "")
        
        if [[ -n "$local_backups" ]]; then
            while IFS= read -r backup_line; do
                local backup_time backup_name
                backup_time=$(echo "$backup_line" | cut -d' ' -f1)
                backup_name=$(echo "$backup_line" | cut -d' ' -f2-)
                
                local backup_date
                backup_date=$(date -d "@$(printf "%.0f" "$backup_time")" '+%Y-%m-%d %H:%M:%S')
                
                echo "  $backup_name ($backup_date)"
                found_backups=true
            done <<< "$local_backups"
        else
            echo "  No local backups found"
        fi
    fi
    
    # List GitHub releases
    if command -v gh >/dev/null 2>&1; then
        local github_repo
        github_repo=$(get_config_value '.destinations[] | select(.type == "github_releases") | .config.repository' '')
        
        if [[ -n "$github_repo" ]]; then
            github_repo=$(echo "$github_repo" | envsubst)
            echo -e "\n${YELLOW}GitHub Releases ($github_repo):${NC}"
            
            local github_backups
            github_backups=$(gh release list --repo "$github_repo" --limit 20 --json tagName,createdAt 2>/dev/null | \
                           jq -r '.[] | select(.tagName | startswith("backup-")) | "\(.createdAt) \(.tagName)"' || echo "")
            
            if [[ -n "$github_backups" ]]; then
                while IFS= read -r backup_line; do
                    local backup_date backup_tag
                    backup_date=$(echo "$backup_line" | cut -d' ' -f1)
                    backup_tag=$(echo "$backup_line" | cut -d' ' -f2-)
                    
                    local formatted_date
                    formatted_date=$(date -d "$backup_date" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$backup_date")
                    
                    echo "  $backup_tag ($formatted_date)"
                    found_backups=true
                done <<< "$github_backups"
            else
                echo "  No GitHub backup releases found"
            fi
        fi
    fi
    
    # List S3 backups
    if command -v aws >/dev/null 2>&1; then
        local s3_bucket s3_prefix
        s3_bucket=$(get_config_value '.destinations[] | select(.type == "s3") | .config.bucket' '')
        s3_prefix=$(get_config_value '.destinations[] | select(.type == "s3") | .config.prefix' 'activelog-backups/')
        
        s3_bucket=$(echo "$s3_bucket" | envsubst)
        s3_prefix=$(echo "$s3_prefix" | envsubst)
        
        if [[ -n "$s3_bucket" ]]; then
            echo -e "\n${YELLOW}S3 Backups (s3://$s3_bucket/$s3_prefix):${NC}"
            
            local s3_backups
            s3_backups=$(aws s3 ls "s3://$s3_bucket/$s3_prefix" | grep "PRE.*activelog_" | awk '{print $2}' | sed 's|/$||' || echo "")
            
            if [[ -n "$s3_backups" ]]; then
                while IFS= read -r backup_dir; do
                    if [[ -n "$backup_dir" ]]; then
                        # Get backup date from S3
                        local s3_date
                        s3_date=$(aws s3 ls "s3://$s3_bucket/$s3_prefix$backup_dir/" | head -n1 | awk '{print $1 " " $2}' || echo "unknown")
                        
                        echo "  $backup_dir ($s3_date)"
                        found_backups=true
                    fi
                done <<< "$s3_backups"
            else
                echo "  No S3 backups found"
            fi
        fi
    fi
    
    if [[ "$found_backups" != "true" ]]; then
        echo -e "\n${RED}No backups found in any configured source${NC}"
        return 1
    fi
    
    echo ""
    echo -e "${GREEN}Use any of the above backup names or paths with this restore script${NC}"
}

main() {
    local start_time
    start_time=$(date +%s)
    
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════╗
    ║       ActiveLog Backup Restore        ║
    ║     Intelligent Restore System v1.0  ║
    ╚═══════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    log_info "Starting ActiveLog restore process..."
    
    # Initialize
    check_dependencies
    load_config
    
    # Create temporary working directory
    TEMP_DIR=$(mktemp -d -t "activelog-restore-XXXXXX")
    log_info "Working directory: $TEMP_DIR"
    
    # Parse and validate source
    parse_backup_source "$RESTORE_SOURCE"
    
    # Download backup files
    case "$RESTORE_SOURCE" in
        "local")
            download_backup_local
            ;;
        "github")
            download_backup_github
            ;;
        "s3")
            download_backup_s3
            ;;
        *)
            log_error "Unknown restore source: $RESTORE_SOURCE"
            exit 1
            ;;
    esac
    
    # Verify backup integrity
    if ! verify_backup_integrity; then
        log_error "Backup verification failed - restore aborted"
        exit 1
    fi
    
    if [[ "$VERIFY_ONLY" == "true" ]]; then
        log_success "Backup verification completed successfully"
        exit 0
    fi
    
    # Determine target directory
    if [[ -z "$RESTORE_TARGET" ]]; then
        RESTORE_TARGET="./restored-$BACKUP_ID"
        log_info "Using default target directory: $RESTORE_TARGET"
    fi
    
    # Check if target exists
    if [[ -e "$RESTORE_TARGET" && "$DRY_RUN" == "false" ]]; then
        log_error "Target directory exists: $RESTORE_TARGET"
        log_error "Use --force to overwrite or specify a different target"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would restore backup to: $RESTORE_TARGET"
        log_info "DRY RUN: Backup ID: $BACKUP_ID"
        log_info "DRY RUN: Source: $RESTORE_SOURCE"
        log_success "Dry run completed - no files were restored"
        exit 0
    fi
    
    # Extract backup
    extract_backup "$RESTORE_TARGET"
    
    # Calculate duration
    local end_time duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    # Print summary
    echo ""
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}         RESTORE SUMMARY${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo -e "Backup ID:     ${CYAN}$BACKUP_ID${NC}"
    echo -e "Source:        ${CYAN}$RESTORE_SOURCE${NC}"
    echo -e "Target:        ${CYAN}$RESTORE_TARGET${NC}"
    echo -e "Duration:      ${CYAN}${duration}s${NC}"
    echo -e "Status:        ${GREEN}SUCCESS${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo ""
    
    log_success "Restore completed successfully in ${duration} seconds"
    log_info "Restored files are available in: $RESTORE_TARGET"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verify)
            VERIFY_ONLY=true
            shift
            ;;
        -f|--force)
            # Force overwrite (handled in main)
            shift
            ;;
        -q|--quiet)
            # Quiet mode (could redirect output)
            shift
            ;;
        --no-verify)
            # Skip verification (could be implemented)
            shift
            ;;
        --list-backups)
            check_dependencies
            load_config
            list_backups
            exit $?
            ;;
        -*)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            if [[ -z "$RESTORE_SOURCE" ]]; then
                RESTORE_SOURCE="$1"
            elif [[ -z "$RESTORE_TARGET" ]]; then
                RESTORE_TARGET="$1"
            else
                log_error "Too many arguments: $1"
                echo "Use --help for usage information"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "$RESTORE_SOURCE" ]]; then
    log_error "Backup source is required"
    echo "Use --help for usage information"
    exit 1
fi

# Run main function
main "$@"