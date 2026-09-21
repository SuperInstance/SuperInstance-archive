#!/bin/bash

# Configuration Backup Script for ActiveLog Production
# Backs up Docker configs, secrets, environment files, and service configurations
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/backup.conf"
LOG_FILE="${SCRIPT_DIR}/../logs/config_backup.log"
BACKUP_BASE_DIR="/opt/activelog/backups/config"
RETENTION_DAYS=90
ENCRYPT_BACKUP=true

# Configuration paths to backup
declare -a CONFIG_PATHS=(
    "/home/activeloguser/activelog/docker-compose*.yml"
    "/home/activeloguser/activelog/production/configs"
    "/home/activeloguser/activelog/nginx"
    "/home/activeloguser/activelog/monitoring"
    "/home/activeloguser/activelog/logging"
    "/home/activeloguser/activelog/infrastructure"
    "/home/activeloguser/activelog/.env*"
    "/home/activeloguser/activelog/Makefile"
    "/home/activeloguser/activelog/secrets/*.txt"
    "/etc/nginx"
    "/etc/ssl"
    "/etc/systemd/system/activelog*"
)

# Sensitive patterns to exclude or anonymize
declare -a SENSITIVE_PATTERNS=(
    "password"
    "secret"
    "key"
    "token"
    "credential"
    "private"
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

get_docker_info() {
    local info_file="$1"
    
    cat > "$info_file" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "docker_version": "$(docker --version 2>/dev/null || echo 'Not available')",
    "docker_compose_version": "$(docker-compose --version 2>/dev/null || echo 'Not available')",
    "containers": $(docker ps --format json 2>/dev/null | jq -s . || echo '[]'),
    "images": $(docker images --format json 2>/dev/null | jq -s . || echo '[]'),
    "volumes": $(docker volume ls --format json 2>/dev/null | jq -s . || echo '[]'),
    "networks": $(docker network ls --format json 2>/dev/null | jq -s . || echo '[]')
}
EOF
}

get_system_info() {
    local info_file="$1"
    
    cat > "$info_file" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "hostname": "$(hostname)",
    "kernel": "$(uname -r)",
    "os_release": $(cat /etc/os-release 2>/dev/null | grep -E '^(NAME|VERSION)=' | sed 's/^/"/;s/=/": "/;s/$/"/' | tr '\n' ',' | sed 's/,$//' | sed 's/^/{/;s/$/}/'),
    "uptime": "$(uptime)",
    "disk_usage": $(df -h / /opt /var /tmp 2>/dev/null | tail -n +2 | jq -R 'split(" ") | {filesystem: .[0], size: .[1], used: .[2], available: .[3], percent: .[4], mount: .[5]}' | jq -s .),
    "memory_info": $(free -h | jq -R 'split(" +"; "g") | select(length > 1)' | jq -s '{"total": .[1][1], "used": .[1][2], "free": .[1][3], "available": .[1][6] // "N/A"}'),
    "active_services": $(systemctl list-units --state=active --type=service | grep activelog | awk '{print $1}' | jq -R . | jq -s .)
}
EOF
}

anonymize_sensitive_content() {
    local source_file="$1"
    local target_file="$2"
    
    log_info "Anonymizing sensitive content in: $(basename "$source_file")"
    
    # Copy the original file
    cp "$source_file" "$target_file"
    
    # Replace sensitive values with placeholders
    for pattern in "${SENSITIVE_PATTERNS[@]}"; do
        # Replace values in key=value format
        sed -i "s/\($pattern[_-]*[^=]*=\)[^[:space:]]*/\1***REDACTED***/gi" "$target_file"
        
        # Replace values in YAML format
        sed -i "s/\($pattern[_-]*[^:]*:\s*\)[^[:space:]]*/\1***REDACTED***/gi" "$target_file"
        
        # Replace values in JSON format
        sed -i "s/\(\"$pattern[_-]*[^\"]*\":\s*\"\)[^\"]*\"/\1***REDACTED***/gi" "$target_file"
    done
    
    # Additional specific replacements for common patterns
    sed -i 's/\(password[^=]*=\)[^[:space:]]*/\1***REDACTED***/gi' "$target_file"
    sed -i 's/\(secret[^=]*=\)[^[:space:]]*/\1***REDACTED***/gi' "$target_file"
    sed -i 's/\([0-9a-fA-F]\{32,\}\)/***REDACTED_HASH***/g' "$target_file"
    
    log_info "Sensitive content anonymized"
}

backup_docker_configs() {
    local backup_dir="$1"
    local docker_dir="$backup_dir/docker"
    
    ensure_directory "$docker_dir"
    
    log_info "Backing up Docker configurations..."
    
    # Backup compose files
    for compose_file in /home/activeloguser/activelog/docker-compose*.yml; do
        if [[ -f "$compose_file" ]]; then
            local filename=$(basename "$compose_file")
            anonymize_sensitive_content "$compose_file" "$docker_dir/$filename"
            log_info "Backed up: $filename"
        fi
    done
    
    # Backup Docker daemon configuration
    if [[ -f "/etc/docker/daemon.json" ]]; then
        cp "/etc/docker/daemon.json" "$docker_dir/daemon.json"
        log_info "Backed up Docker daemon config"
    fi
    
    # Get Docker system information
    get_docker_info "$docker_dir/docker_info.json"
    
    # Backup container inspect data
    local containers_dir="$docker_dir/containers"
    ensure_directory "$containers_dir"
    
    if command -v docker >/dev/null 2>&1; then
        docker ps -a --format "{{.Names}}" | while read -r container_name; do
            if [[ -n "$container_name" ]]; then
                docker inspect "$container_name" > "$containers_dir/${container_name}.json" 2>/dev/null || true
            fi
        done
        
        # Backup docker-compose service configs
        if [[ -f "/home/activeloguser/activelog/docker-compose.prod.yml" ]]; then
            docker-compose -f /home/activeloguser/activelog/docker-compose.prod.yml config > "$docker_dir/resolved_compose.yml" 2>/dev/null || true
        fi
    fi
    
    log_info "Docker configurations backed up"
}

backup_secrets() {
    local backup_dir="$1"
    local secrets_dir="$backup_dir/secrets"
    
    ensure_directory "$secrets_dir"
    
    log_info "Backing up secrets (anonymized)..."
    
    # Create secrets inventory without exposing actual values
    local secrets_inventory="$secrets_dir/secrets_inventory.json"
    cat > "$secrets_inventory" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "secrets_files": [],
    "environment_variables": []
}
EOF
    
    # List secret files (without content)
    if [[ -d "/home/activeloguser/activelog/secrets" ]]; then
        find /home/activeloguser/activelog/secrets -name "*.txt" -type f | while read -r secret_file; do
            local filename=$(basename "$secret_file")
            local file_size=$(stat -c%s "$secret_file" 2>/dev/null || echo "0")
            local file_modified=$(stat -c%Y "$secret_file" 2>/dev/null || echo "0")
            
            # Add to inventory
            jq --arg name "$filename" \
               --arg size "$file_size" \
               --arg modified "$file_modified" \
               '.secrets_files += [{"name": $name, "size": ($size | tonumber), "modified": ($modified | tonumber)}]' \
               "$secrets_inventory" > "$secrets_inventory.tmp"
            mv "$secrets_inventory.tmp" "$secrets_inventory"
            
            # Create placeholder file
            echo "***REDACTED*** (original size: $file_size bytes)" > "$secrets_dir/$filename"
        done
    fi
    
    # Backup environment variable names (not values)
    env | grep -i "activelog\|postgres\|redis\|jwt\|aws\|openai" | cut -d'=' -f1 | while read -r env_var; do
        if [[ -n "$env_var" ]]; then
            jq --arg name "$env_var" \
               '.environment_variables += [$name]' \
               "$secrets_inventory" > "$secrets_inventory.tmp"
            mv "$secrets_inventory.tmp" "$secrets_inventory"
        fi
    done
    
    log_info "Secrets inventory created (sensitive values redacted)"
}

backup_nginx_configs() {
    local backup_dir="$1"
    local nginx_dir="$backup_dir/nginx"
    
    ensure_directory "$nginx_dir"
    
    log_info "Backing up Nginx configurations..."
    
    # Application nginx configs
    if [[ -d "/home/activeloguser/activelog/nginx" ]]; then
        cp -r /home/activeloguser/activelog/nginx/* "$nginx_dir/" 2>/dev/null || true
    fi
    
    # System nginx configs
    if [[ -d "/etc/nginx" ]]; then
        local system_nginx_dir="$nginx_dir/system"
        ensure_directory "$system_nginx_dir"
        
        # Copy main config files
        for config_file in /etc/nginx/nginx.conf /etc/nginx/sites-available/* /etc/nginx/sites-enabled/*; do
            if [[ -f "$config_file" ]]; then
                local rel_path="${config_file#/etc/nginx/}"
                local target_dir="$system_nginx_dir/$(dirname "$rel_path")"
                ensure_directory "$target_dir"
                cp "$config_file" "$system_nginx_dir/$rel_path" 2>/dev/null || true
            fi
        done
    fi
    
    # Nginx status and configuration test
    if command -v nginx >/dev/null 2>&1; then
        nginx -t 2>&1 | tee "$nginx_dir/config_test.log" || true
        nginx -V 2>&1 | tee "$nginx_dir/version_info.log" || true
    fi
    
    log_info "Nginx configurations backed up"
}

backup_monitoring_configs() {
    local backup_dir="$1"
    local monitoring_dir="$backup_dir/monitoring"
    
    ensure_directory "$monitoring_dir"
    
    log_info "Backing up monitoring configurations..."
    
    # Application monitoring configs
    if [[ -d "/home/activeloguser/activelog/monitoring" ]]; then
        cp -r /home/activeloguser/activelog/monitoring/* "$monitoring_dir/" 2>/dev/null || true
        
        # Anonymize any sensitive content in monitoring configs
        find "$monitoring_dir" -name "*.yml" -o -name "*.yaml" -o -name "*.json" | while read -r config_file; do
            local temp_file=$(mktemp)
            anonymize_sensitive_content "$config_file" "$temp_file"
            mv "$temp_file" "$config_file"
        done
    fi
    
    log_info "Monitoring configurations backed up"
}

backup_ssl_certificates() {
    local backup_dir="$1"
    local ssl_dir="$backup_dir/ssl"
    
    ensure_directory "$ssl_dir"
    
    log_info "Backing up SSL certificate information..."
    
    # Create SSL certificate inventory (without private keys)
    local ssl_inventory="$ssl_dir/ssl_inventory.json"
    cat > "$ssl_inventory" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "certificates": []
}
EOF
    
    # Check common SSL certificate locations
    local ssl_locations=(
        "/etc/ssl/certs"
        "/etc/nginx/ssl"
        "/home/activeloguser/activelog/nginx/ssl"
    )
    
    for ssl_location in "${ssl_locations[@]}"; do
        if [[ -d "$ssl_location" ]]; then
            find "$ssl_location" -name "*.crt" -o -name "*.pem" -o -name "*.cert" | while read -r cert_file; do
                if [[ -f "$cert_file" ]]; then
                    local cert_info=""
                    if command -v openssl >/dev/null 2>&1; then
                        cert_info=$(openssl x509 -in "$cert_file" -text -noout 2>/dev/null || echo "Unable to read certificate")
                        
                        # Extract key information
                        local subject=$(echo "$cert_info" | grep "Subject:" | sed 's/.*Subject: //')
                        local issuer=$(echo "$cert_info" | grep "Issuer:" | sed 's/.*Issuer: //')
                        local not_before=$(echo "$cert_info" | grep "Not Before:" | sed 's/.*Not Before: //')
                        local not_after=$(echo "$cert_info" | grep "Not After:" | sed 's/.*Not After: //')
                        
                        jq --arg file "$cert_file" \
                           --arg subject "$subject" \
                           --arg issuer "$issuer" \
                           --arg not_before "$not_before" \
                           --arg not_after "$not_after" \
                           '.certificates += [{"file": $file, "subject": $subject, "issuer": $issuer, "not_before": $not_before, "not_after": $not_after}]' \
                           "$ssl_inventory" > "$ssl_inventory.tmp"
                        mv "$ssl_inventory.tmp" "$ssl_inventory"
                    fi
                    
                    # Copy public certificate (not private key)
                    if [[ "$cert_file" != *".key"* && "$cert_file" != *"private"* ]]; then
                        local rel_path="${cert_file#$ssl_location/}"
                        local target_dir="$ssl_dir/$(dirname "$rel_path")"
                        ensure_directory "$target_dir"
                        cp "$cert_file" "$ssl_dir/$rel_path" 2>/dev/null || true
                    fi
                fi
            done
        fi
    done
    
    log_info "SSL certificate information backed up (private keys excluded)"
}

backup_systemd_services() {
    local backup_dir="$1"
    local systemd_dir="$backup_dir/systemd"
    
    ensure_directory "$systemd_dir"
    
    log_info "Backing up systemd service configurations..."
    
    # Backup ActiveLog-related systemd services
    find /etc/systemd/system -name "*activelog*" -type f | while read -r service_file; do
        if [[ -f "$service_file" ]]; then
            local filename=$(basename "$service_file")
            cp "$service_file" "$systemd_dir/$filename"
            log_info "Backed up systemd service: $filename"
        fi
    done
    
    # Get service status information
    local services_status="$systemd_dir/services_status.json"
    cat > "$services_status" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "services": []
}
EOF
    
    systemctl list-units --type=service | grep activelog | while read -r line; do
        local service_name=$(echo "$line" | awk '{print $1}')
        if [[ -n "$service_name" ]]; then
            local status=$(systemctl is-active "$service_name" 2>/dev/null || echo "unknown")
            local enabled=$(systemctl is-enabled "$service_name" 2>/dev/null || echo "unknown")
            
            jq --arg name "$service_name" \
               --arg status "$status" \
               --arg enabled "$enabled" \
               '.services += [{"name": $name, "status": $status, "enabled": $enabled}]' \
               "$services_status" > "$services_status.tmp"
            mv "$services_status.tmp" "$services_status"
        fi
    done
    
    log_info "Systemd service configurations backed up"
}

create_configuration_backup() {
    local timestamp="$(date '+%Y%m%d_%H%M%S')"
    local backup_dir="$BACKUP_BASE_DIR/$timestamp"
    
    ensure_directory "$backup_dir"
    
    log_info "Starting configuration backup to: $backup_dir"
    
    local start_time=$(date +%s)
    
    # Create backup metadata
    cat > "$backup_dir/backup_metadata.json" <<EOF
{
    "backup_type": "configuration",
    "timestamp": "$timestamp",
    "script_version": "1.0.0",
    "hostname": "$(hostname)",
    "backup_components": [
        "docker_configs",
        "secrets_inventory",
        "nginx_configs",
        "monitoring_configs",
        "ssl_certificates",
        "systemd_services",
        "system_info"
    ]
}
EOF
    
    # Backup different configuration components
    backup_docker_configs "$backup_dir"
    backup_secrets "$backup_dir"
    backup_nginx_configs "$backup_dir"
    backup_monitoring_configs "$backup_dir"
    backup_ssl_certificates "$backup_dir"
    backup_systemd_services "$backup_dir"
    
    # Backup additional application configs
    local app_configs_dir="$backup_dir/application"
    ensure_directory "$app_configs_dir"
    
    # Copy other important config files
    for config_path in "${CONFIG_PATHS[@]}"; do
        if [[ -e $config_path ]]; then  # Use glob expansion
            for file in $config_path; do
                if [[ -f "$file" ]]; then
                    local rel_path="${file#/home/activeloguser/activelog/}"
                    local target_dir="$app_configs_dir/$(dirname "$rel_path")"
                    ensure_directory "$target_dir"
                    
                    # Anonymize sensitive files
                    if [[ "$file" == *".env"* || "$file" == *"secret"* || "$file" == *"password"* ]]; then
                        anonymize_sensitive_content "$file" "$app_configs_dir/$rel_path"
                    else
                        cp "$file" "$app_configs_dir/$rel_path"
                    fi
                    
                    log_info "Backed up config: $file"
                elif [[ -d "$file" ]]; then
                    local rel_path="${file#/home/activeloguser/activelog/}"
                    cp -r "$file" "$app_configs_dir/$rel_path" 2>/dev/null || true
                    log_info "Backed up config directory: $file"
                fi
            done
        else
            log_warning "Config path not found: $config_path"
        fi
    done
    
    # Get system information
    get_system_info "$backup_dir/system_info.json"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Compress the backup
    log_info "Compressing configuration backup..."
    local archive_file="$backup_dir.tar.gz"
    tar -czf "$archive_file" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    
    # Remove uncompressed directory
    rm -rf "$backup_dir"
    
    # Create new directory for metadata and archive
    mkdir -p "$backup_dir"
    mv "$archive_file" "$backup_dir/"
    
    # Encrypt if enabled
    local final_file="$backup_dir/$(basename "$archive_file")"
    if [[ "$ENCRYPT_BACKUP" == "true" ]]; then
        log_info "Encrypting configuration backup..."
        if command -v gpg >/dev/null 2>&1 && [[ -f "/run/secrets/backup_passphrase" ]]; then
            local encrypted_file="${final_file}.enc"
            gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
                --s2k-digest-algo SHA512 --s2k-count 65536 --quiet \
                --passphrase-file="/run/secrets/backup_passphrase" \
                --output "$encrypted_file" "$final_file"
            rm -f "$final_file"
            final_file="$encrypted_file"
        else
            log_warning "Encryption not available, backup will remain unencrypted"
        fi
    fi
    
    # Update metadata with final information
    local final_size=$(du -h "$final_file" | cut -f1)
    
    cat > "$backup_dir/backup_metadata.json" <<EOF
{
    "backup_type": "configuration",
    "timestamp": "$timestamp",
    "script_version": "1.0.0",
    "hostname": "$(hostname)",
    "duration_seconds": $duration,
    "final_size": "$final_size",
    "final_file": "$(basename "$final_file")",
    "encrypted": $ENCRYPT_BACKUP,
    "status": "completed",
    "backup_components": [
        "docker_configs",
        "secrets_inventory", 
        "nginx_configs",
        "monitoring_configs",
        "ssl_certificates",
        "systemd_services",
        "system_info",
        "application_configs"
    ]
}
EOF
    
    log_info "Configuration backup completed successfully"
    log_info "Duration: ${duration}s, Size: $final_size"
    log_info "Backup location: $final_file"
    
    # Create symlink to latest backup
    local latest_link="$BACKUP_BASE_DIR/latest"
    rm -f "$latest_link"
    ln -sf "$timestamp" "$latest_link"
    
    echo "$backup_dir"
}

verify_backup() {
    local backup_dir="$1"
    
    log_info "Verifying configuration backup integrity..."
    
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
    local backup_files=($(find "$backup_dir" -name "*.tar.gz*" | head -1))
    if [[ ${#backup_files[@]} -eq 0 ]]; then
        log_error "No backup files found in: $backup_dir"
        return 1
    fi
    
    local backup_file="${backup_files[0]}"
    
    # Test archive integrity
    if [[ "$backup_file" == *.tar.gz ]] && [[ "$backup_file" != *.enc ]]; then
        if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
            log_error "Corrupted archive: $backup_file"
            return 1
        fi
    fi
    
    log_info "Configuration backup verification passed"
    return 0
}

cleanup_old_backups() {
    log_info "Cleaning up old configuration backups (retention: $RETENTION_DAYS days)..."
    
    find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -name "[0-9]*_[0-9]*" | while read -r old_backup; do
        log_info "Removing old backup: $old_backup"
        rm -rf "$old_backup"
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
                        \"alertname\": \"ConfigurationBackup\",
                        \"service\": \"backup\",
                        \"component\": \"configuration\",
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
    "service": "config_backup",
    "status": "$status",
    "message": "$message",
    "details": "$backup_info"
}
EOF
}

# Main execution
main() {
    local action="${1:-backup}"
    
    log_info "Starting configuration backup script (action: $action)"
    
    # Create necessary directories
    ensure_directory "$BACKUP_BASE_DIR"
    ensure_directory "$(dirname "$LOG_FILE")"
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    
    case "$action" in
        "backup")
            backup_dir=$(create_configuration_backup)
            if verify_backup "$backup_dir"; then
                send_notification "info" "Configuration backup completed successfully" "Backup location: $backup_dir"
            else
                send_notification "critical" "Configuration backup verification failed" "Backup location: $backup_dir"
                exit 1
            fi
            ;;
        "cleanup")
            cleanup_old_backups
            send_notification "info" "Configuration backup cleanup completed" ""
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
            echo "Usage: $0 {backup|cleanup|verify <backup_dir>}"
            exit 1
            ;;
    esac
    
    log_info "Configuration backup script completed successfully"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi