#!/bin/bash

# ActiveLog Universal Service Deployment Script
# Deploys any service to EC2 with automatic port assignment and nginx configuration

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="${SCRIPT_DIR}/services"
NGINX_CONF_REMOTE="/etc/nginx/sites-available/activelog"
NGINX_ENABLED_REMOTE="/etc/nginx/sites-enabled/activelog"
DEPLOY_USER="ubuntu"
REMOTE_DEPLOY_DIR="/home/ubuntu/activelog"
PORT_RANGE_START=8400
PORT_RANGE_END=8500
LOG_FILE="${SCRIPT_DIR}/logs/deploy.log"

# Default configuration
EC2_HOST="${EC2_HOST:-}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_KEY="${EC2_KEY:-~/.ssh/personallog_key}"
SERVICE_DOMAIN="${DEPLOY_DOMAIN:-activelog.ai}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Log to file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    # Color output for console
    case "$level" in
        "ERROR")   echo -e "${RED}[$level]${NC} $message" >&2 ;;
        "SUCCESS") echo -e "${GREEN}[$level]${NC} $message" ;;
        "WARN")    echo -e "${YELLOW}[$level]${NC} $message" ;;
        "INFO")    echo -e "${BLUE}[$level]${NC} $message" ;;
        "DEBUG")   echo -e "${PURPLE}[$level]${NC} $message" ;;
        *)         echo -e "${CYAN}[$level]${NC} $message" ;;
    esac
}

# Print usage information
usage() {
    echo "Usage: $0 SERVICE_NAME [OPTIONS]"
    echo ""
    echo "Deploy a service to EC2 with automatic port assignment and nginx configuration"
    echo ""
    echo "Arguments:"
    echo "  SERVICE_NAME    Name of the service to deploy (must exist in services/ directory)"
    echo ""
    echo "Options:"
    echo "  --host HOST     EC2 host/IP address (required if EC2_HOST not set)"
    echo "  --key KEY_FILE  SSH private key file (required if EC2_KEY not set)"
    echo "  --port PORT     Force specific port (otherwise auto-assigned)"
    echo "  --domain DOMAIN Domain name for nginx proxy (default: activelog.ai)"
    echo "  --no-nginx      Skip nginx configuration"
    echo "  --no-start      Deploy files but don't start service"
    echo "  --dry-run       Show what would be done without executing"
    echo "  --verbose       Enable verbose output"
    echo "  --help          Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  EC2_HOST        EC2 host/IP address"
    echo "  EC2_KEY         SSH private key file path"
    echo "  DEPLOY_DOMAIN   Domain for nginx proxy"
    echo ""
    echo "Examples:"
    echo "  $0 personallog-backend --host ec2-user@1.2.3.4 --key ~/.ssh/my-key.pem"
    echo "  EC2_HOST=ubuntu@ec2-1-2-3-4.compute-1.amazonaws.com $0 dmlog-core"
    echo "  $0 api-gateway --port 8080 --domain myapp.com"
    echo ""
    echo "Available services:"
    if [[ -d "$SERVICES_DIR" ]]; then
        ls -1 "$SERVICES_DIR" | grep -v "main.py" | head -10
        if [[ $(ls -1 "$SERVICES_DIR" | wc -l) -gt 10 ]]; then
            echo "  ... and $(($(ls -1 "$SERVICES_DIR" | wc -l) - 10)) more"
        fi
    else
        echo "  (No services directory found at $SERVICES_DIR)"
    fi
}

# Check if service exists
check_service_exists() {
    local service_name="$1"
    local service_path="${SERVICES_DIR}/${service_name}"
    
    if [[ ! -d "$service_path" ]]; then
        log "ERROR" "Service '$service_name' not found in $SERVICES_DIR"
        log "INFO" "Available services:"
        if [[ -d "$SERVICES_DIR" ]]; then
            ls -1 "$SERVICES_DIR" | head -10 | while read -r svc; do
                log "INFO" "  - $svc"
            done
        fi
        return 1
    fi
    
    return 0
}

# Get next available port on remote server
get_available_port() {
    local ec2_connection="$1"
    local ssh_key="$2"
    local forced_port="$3"
    
    if [[ -n "$forced_port" ]]; then
        log "INFO" "Using forced port: $forced_port"
        echo "$forced_port"
        return 0
    fi
    
    log "INFO" "Finding available port on remote server..."
    
    # Get list of used ports
    local used_ports
    used_ports=$(ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "netstat -tuln 2>/dev/null | awk '\$1==\"tcp\" && \$6==\"LISTEN\" {split(\$4,a,\":\"); print a[length(a)]}' | sort -n" 2>/dev/null || echo "")
    
    # Find first available port in range
    for port in $(seq $PORT_RANGE_START $PORT_RANGE_END); do
        if ! echo "$used_ports" | grep -q "^${port}$"; then
            log "INFO" "Found available port: $port"
            echo "$port"
            return 0
        fi
    done
    
    log "ERROR" "No available ports in range $PORT_RANGE_START-$PORT_RANGE_END"
    return 1
}

# Detect service type and requirements
detect_service_type() {
    local service_path="$1"
    
    if [[ -f "${service_path}/package.json" ]]; then
        echo "nodejs"
    elif [[ -f "${service_path}/requirements.txt" ]] || [[ -f "${service_path}/main.py" ]]; then
        echo "python"
    elif [[ -f "${service_path}/Dockerfile" ]]; then
        echo "docker"
    else
        echo "unknown"
    fi
}

# Generate service startup script
generate_startup_script() {
    local service_name="$1"
    local service_type="$2"
    local port="$3"
    local service_path="$4"
    
    local startup_script="#!/bin/bash
# Auto-generated startup script for $service_name
# Generated by deploy.sh on $(date)

set -euo pipefail

SERVICE_NAME=\"$service_name\"
SERVICE_PORT=\"$port\"
SERVICE_DIR=\"${REMOTE_DEPLOY_DIR}/services/\${SERVICE_NAME}\"
PID_FILE=\"/tmp/\${SERVICE_NAME}.pid\"
LOG_FILE=\"\${SERVICE_DIR}/service.log\"

# Create log directory
mkdir -p \"\$(dirname \"\$LOG_FILE\")\"

# Function to stop service
stop_service() {
    if [[ -f \"\$PID_FILE\" ]]; then
        local pid=\$(cat \"\$PID_FILE\")
        if kill -0 \"\$pid\" 2>/dev/null; then
            echo \"Stopping \$SERVICE_NAME (PID: \$pid)\"
            kill \"\$pid\"
            sleep 3
            if kill -0 \"\$pid\" 2>/dev/null; then
                kill -9 \"\$pid\"
            fi
        fi
        rm -f \"\$PID_FILE\"
    fi
    
    # Kill any processes using the port
    pkill -f \"PORT=\$SERVICE_PORT\" 2>/dev/null || true
    lsof -ti:\$SERVICE_PORT | xargs -r kill -9 2>/dev/null || true
}

# Function to start service
start_service() {
    cd \"\$SERVICE_DIR\"
    
    echo \"Starting \$SERVICE_NAME on port \$SERVICE_PORT\"
    echo \"Service directory: \$SERVICE_DIR\"
    echo \"Log file: \$LOG_FILE\"
"

    case "$service_type" in
        "nodejs")
            startup_script+="    
    # Install dependencies if needed
    if [[ -f package.json ]] && [[ ! -d node_modules ]]; then
        echo \"Installing Node.js dependencies...\"
        npm install
    fi
    
    # Start Node.js service
    PORT=\$SERVICE_PORT nohup node server.js > \"\$LOG_FILE\" 2>&1 &
    echo \$! > \"\$PID_FILE\"
"
            ;;
        "python")
            startup_script+="    
    # Install dependencies if needed
    if [[ -f requirements.txt ]]; then
        echo \"Installing Python dependencies...\"
        pip3 install -r requirements.txt 2>/dev/null || true
    fi
    
    # Start Python service
    PORT=\$SERVICE_PORT nohup python3 main.py > \"\$LOG_FILE\" 2>&1 &
    echo \$! > \"\$PID_FILE\"
"
            ;;
        "docker")
            startup_script+="    
    # Build and start Docker service
    docker build -t \"\$SERVICE_NAME\" .
    docker stop \"\$SERVICE_NAME\" 2>/dev/null || true
    docker rm \"\$SERVICE_NAME\" 2>/dev/null || true
    docker run -d --name \"\$SERVICE_NAME\" -p \"\$SERVICE_PORT:8080\" \"\$SERVICE_NAME\"
    docker ps -q --filter \"name=\$SERVICE_NAME\" > \"\$PID_FILE\"
"
            ;;
        *)
            startup_script+="    
    echo \"Unknown service type, attempting to start with default command...\"
    if [[ -f main.py ]]; then
        PORT=\$SERVICE_PORT nohup python3 main.py > \"\$LOG_FILE\" 2>&1 &
    elif [[ -f server.js ]]; then
        PORT=\$SERVICE_PORT nohup node server.js > \"\$LOG_FILE\" 2>&1 &
    else
        echo \"ERROR: No known entry point found\"
        exit 1
    fi
    echo \$! > \"\$PID_FILE\"
"
            ;;
    esac

    startup_script+="    
    sleep 2
    
    # Check if service started successfully
    if [[ -f \"\$PID_FILE\" ]]; then
        local pid=\$(cat \"\$PID_FILE\")
        if kill -0 \"\$pid\" 2>/dev/null; then
            echo \"✅ \$SERVICE_NAME started successfully (PID: \$pid)\"
            echo \"📊 Service running on port \$SERVICE_PORT\"
            echo \"📝 Logs: \$LOG_FILE\"
        else
            echo \"❌ \$SERVICE_NAME failed to start\"
            echo \"📝 Check logs: \$LOG_FILE\"
            exit 1
        fi
    else
        echo \"❌ PID file not created, service may have failed to start\"
        exit 1
    fi
}

# Function to check service status
status_service() {
    if [[ -f \"\$PID_FILE\" ]]; then
        local pid=\$(cat \"\$PID_FILE\")
        if kill -0 \"\$pid\" 2>/dev/null; then
            echo \"✅ \$SERVICE_NAME is running (PID: \$pid)\"
            echo \"📊 Port: \$SERVICE_PORT\"
            echo \"📈 CPU: \$(ps -p \$pid -o %cpu= 2>/dev/null || echo 'N/A')%\"
            echo \"📊 Memory: \$(ps -p \$pid -o rss= 2>/dev/null | awk '{print \$1/1024\" MB\"}' || echo 'N/A')\"
            return 0
        else
            echo \"❌ \$SERVICE_NAME is not running (stale PID file)\"
            rm -f \"\$PID_FILE\"
            return 1
        fi
    else
        echo \"❌ \$SERVICE_NAME is not running (no PID file)\"
        return 1
    fi
}

# Main script logic
case \"\${1:-start}\" in
    \"start\")
        stop_service
        start_service
        ;;
    \"stop\")
        stop_service
        echo \"✅ \$SERVICE_NAME stopped\"
        ;;
    \"restart\")
        stop_service
        sleep 1
        start_service
        ;;
    \"status\")
        status_service
        ;;
    \"logs\")
        if [[ -f \"\$LOG_FILE\" ]]; then
            tail -f \"\$LOG_FILE\"
        else
            echo \"No log file found at \$LOG_FILE\"
        fi
        ;;
    *)
        echo \"Usage: \$0 {start|stop|restart|status|logs}\"
        exit 1
        ;;
esac
"
    
    echo "$startup_script"
}

# Generate nginx configuration
generate_nginx_config() {
    local service_name="$1"
    local port="$2"
    local domain="$3"
    
    local config="# ActiveLog Nginx Configuration
# Generated by deploy.sh on $(date)

upstream activelog_backend {
    server 127.0.0.1:${port};
    keepalive 32;
}

server {
    listen 80;
    server_name ${domain} www.${domain};
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${domain} www.${domain};
    
    # SSL Configuration (update paths as needed)
    ssl_certificate /etc/ssl/certs/activelog.crt;
    ssl_certificate_key /etc/ssl/private/activelog.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options \"SAMEORIGIN\" always;
    add_header X-XSS-Protection \"1; mode=block\" always;
    add_header X-Content-Type-Options \"nosniff\" always;
    add_header Referrer-Policy \"no-referrer-when-downgrade\" always;
    add_header Content-Security-Policy \"default-src 'self' http: https: data: blob: 'unsafe-inline'\" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript application/json;
    
    # Service-specific routing
    location /${service_name}/ {
        proxy_pass http://activelog_backend/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # API routes
    location /api/ {
        proxy_pass http://activelog_backend/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # API-specific settings
        proxy_read_timeout 300s;
        client_max_body_size 50m;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://activelog_backend/health;
        access_log off;
    }
    
    # Static files (if any)
    location /static/ {
        root ${REMOTE_DEPLOY_DIR}/services/${service_name}/;
        expires 1y;
        add_header Cache-Control \"public, immutable\";
    }
    
    # Default location
    location / {
        proxy_pass http://activelog_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    
    # Logs
    access_log /var/log/nginx/activelog_access.log;
    error_log /var/log/nginx/activelog_error.log;
}
"
    
    echo "$config"
}

# Upload files to EC2
upload_service_files() {
    local service_name="$1"
    local ec2_connection="$2"
    local ssh_key="$3"
    local dry_run="$4"
    local verbose="$5"
    
    local service_path="${SERVICES_DIR}/${service_name}"
    local remote_service_dir="${REMOTE_DEPLOY_DIR}/services/${service_name}"
    
    log "INFO" "Uploading service files to EC2..."
    
    if [[ "$dry_run" == "true" ]]; then
        log "INFO" "[DRY RUN] Would upload: $service_path -> $remote_service_dir"
        return 0
    fi
    
    # Create remote directories
    ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "mkdir -p '$remote_service_dir'" 2>/dev/null
    
    # Prepare rsync options
    local rsync_opts=(-avz --delete)
    if [[ "$verbose" == "true" ]]; then
        rsync_opts+=(--progress)
    else
        rsync_opts+=(--quiet)
    fi
    
    # Upload service files
    rsync "${rsync_opts[@]}" \
        -e "ssh -i '$ssh_key' -o StrictHostKeyChecking=no -o ConnectTimeout=30" \
        "$service_path/" \
        "$ec2_connection:$remote_service_dir/"
    
    log "SUCCESS" "Service files uploaded successfully"
}

# Deploy service startup script
deploy_startup_script() {
    local service_name="$1"
    local service_type="$2"
    local port="$3"
    local ec2_connection="$4"
    local ssh_key="$5"
    local dry_run="$6"
    
    local startup_script_content
    startup_script_content=$(generate_startup_script "$service_name" "$service_type" "$port" "${SERVICES_DIR}/${service_name}")
    
    local remote_script_path="${REMOTE_DEPLOY_DIR}/scripts/${service_name}.sh"
    
    log "INFO" "Deploying startup script..."
    
    if [[ "$dry_run" == "true" ]]; then
        log "INFO" "[DRY RUN] Would create startup script: $remote_script_path"
        return 0
    fi
    
    # Create scripts directory and upload startup script
    ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "mkdir -p '${REMOTE_DEPLOY_DIR}/scripts'" 2>/dev/null
    
    echo "$startup_script_content" | ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "cat > '$remote_script_path' && chmod +x '$remote_script_path'"
    
    log "SUCCESS" "Startup script deployed: $remote_script_path"
}

# Configure nginx
configure_nginx() {
    local service_name="$1"
    local port="$2"
    local domain="$3"
    local ec2_connection="$4"
    local ssh_key="$5"
    local dry_run="$6"
    
    log "INFO" "Configuring nginx..."
    
    local nginx_config_content
    nginx_config_content=$(generate_nginx_config "$service_name" "$port" "$domain")
    
    if [[ "$dry_run" == "true" ]]; then
        log "INFO" "[DRY RUN] Would configure nginx for $service_name on port $port"
        log "INFO" "[DRY RUN] Domain: $domain"
        return 0
    fi
    
    # Upload nginx configuration
    echo "$nginx_config_content" | ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "sudo tee '$NGINX_CONF_REMOTE' >/dev/null"
    
    # Enable site and test configuration
    ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "sudo ln -sf '$NGINX_CONF_REMOTE' '$NGINX_ENABLED_REMOTE' && sudo nginx -t" 2>/dev/null
    
    # Reload nginx
    ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "sudo systemctl reload nginx" 2>/dev/null
    
    log "SUCCESS" "Nginx configured and reloaded"
}

# Start the service
start_service() {
    local service_name="$1"
    local ec2_connection="$2"
    local ssh_key="$3"
    local dry_run="$4"
    
    local remote_script_path="${REMOTE_DEPLOY_DIR}/scripts/${service_name}.sh"
    
    log "INFO" "Starting service..."
    
    if [[ "$dry_run" == "true" ]]; then
        log "INFO" "[DRY RUN] Would start service using: $remote_script_path"
        return 0
    fi
    
    # Start the service
    ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "'$remote_script_path' start" 2>&1
    
    # Wait a moment and check status
    sleep 3
    
    local status_output
    status_output=$(ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "'$remote_script_path' status" 2>&1 || echo "Status check failed")
    
    if echo "$status_output" | grep -q "is running"; then
        log "SUCCESS" "Service started successfully"
        log "INFO" "$status_output"
    else
        log "WARN" "Service may not have started properly"
        log "DEBUG" "$status_output"
    fi
}

# Health check
health_check() {
    local service_name="$1"
    local port="$2"
    local domain="$3"
    local ec2_connection="$4"
    local ssh_key="$5"
    local dry_run="$6"
    
    if [[ "$dry_run" == "true" ]]; then
        log "INFO" "[DRY RUN] Would perform health check"
        return 0
    fi
    
    log "INFO" "Performing health check..."
    
    # Test local port connectivity
    local host_ip
    host_ip=$(echo "$ec2_connection" | cut -d'@' -f2)
    
    # Try to connect to the service port
    if timeout 10 bash -c "echo >/dev/tcp/$host_ip/$port" 2>/dev/null; then
        log "SUCCESS" "Service is responding on port $port"
    else
        log "WARN" "Service may not be responding on port $port"
    fi
    
    # Try HTTP health check if available
    local health_url="http://$host_ip:$port/health"
    local http_status
    http_status=$(ssh -i "$ssh_key" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$ec2_connection" \
        "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 '$health_url'" 2>/dev/null || echo "000")
    
    if [[ "$http_status" =~ ^2[0-9]{2}$ ]]; then
        log "SUCCESS" "Health endpoint responding (HTTP $http_status)"
    else
        log "INFO" "Health endpoint test: HTTP $http_status (this may be expected)"
    fi
}

# Main deployment function
deploy_service() {
    local service_name="$1"
    local ec2_host="$2"
    local ssh_key="$3"
    local forced_port="$4"
    local domain="$5"
    local no_nginx="$6"
    local no_start="$7"
    local dry_run="$8"
    local verbose="$9"
    
    log "INFO" "Starting deployment of '$service_name'"
    log "INFO" "Target: $ec2_host"
    log "INFO" "Domain: $domain"
    
    # Check service exists
    if ! check_service_exists "$service_name"; then
        return 1
    fi
    
    # Detect service type
    local service_type
    service_type=$(detect_service_type "${SERVICES_DIR}/${service_name}")
    log "INFO" "Detected service type: $service_type"
    
    # Get available port
    local port
    if ! port=$(get_available_port "$ec2_host" "$ssh_key" "$forced_port"); then
        return 1
    fi
    
    # Upload service files
    if ! upload_service_files "$service_name" "$ec2_host" "$ssh_key" "$dry_run" "$verbose"; then
        log "ERROR" "Failed to upload service files"
        return 1
    fi
    
    # Deploy startup script
    if ! deploy_startup_script "$service_name" "$service_type" "$port" "$ec2_host" "$ssh_key" "$dry_run"; then
        log "ERROR" "Failed to deploy startup script"
        return 1
    fi
    
    # Configure nginx
    if [[ "$no_nginx" == "false" ]]; then
        if ! configure_nginx "$service_name" "$port" "$domain" "$ec2_host" "$ssh_key" "$dry_run"; then
            log "WARN" "Nginx configuration failed, but continuing..."
        fi
    fi
    
    # Start service
    if [[ "$no_start" == "false" ]]; then
        if ! start_service "$service_name" "$ec2_host" "$ssh_key" "$dry_run"; then
            log "ERROR" "Failed to start service"
            return 1
        fi
        
        # Health check
        health_check "$service_name" "$port" "$domain" "$ec2_host" "$ssh_key" "$dry_run"
    fi
    
    # Generate URLs
    local host_ip
    host_ip=$(echo "$ec2_host" | cut -d'@' -f2)
    local service_url="https://${domain}/${service_name}/"
    local api_url="https://${domain}/api/"
    local health_url="https://${domain}/health"
    local direct_url="http://${host_ip}:${port}"
    
    if [[ "$dry_run" == "true" ]]; then
        log "INFO" "[DRY RUN] Deployment simulation completed"
    else
        log "SUCCESS" "🚀 Deployment completed successfully!"
    fi
    
    echo ""
    echo "=================================================="
    echo "🎉 Service '$service_name' Deployment Complete!"
    echo "=================================================="
    echo "📍 Service URL:     $service_url"
    echo "🔗 API URL:         $api_url"
    echo "❤️  Health Check:   $health_url"
    echo "🔧 Direct Access:   $direct_url"
    echo "📊 Port:            $port"
    echo "🏷️  Domain:          $domain"
    echo "⚙️  Service Type:    $service_type"
    echo ""
    echo "🔧 Management Commands:"
    echo "   Start:   ssh -i '$ssh_key' '$ec2_host' '${REMOTE_DEPLOY_DIR}/scripts/${service_name}.sh start'"
    echo "   Stop:    ssh -i '$ssh_key' '$ec2_host' '${REMOTE_DEPLOY_DIR}/scripts/${service_name}.sh stop'"
    echo "   Status:  ssh -i '$ssh_key' '$ec2_host' '${REMOTE_DEPLOY_DIR}/scripts/${service_name}.sh status'"
    echo "   Logs:    ssh -i '$ssh_key' '$ec2_host' '${REMOTE_DEPLOY_DIR}/scripts/${service_name}.sh logs'"
    echo ""
    echo "📝 Deployment log: $LOG_FILE"
    echo "=================================================="
    
    return 0
}

# Parse command line arguments
main() {
    local service_name=""
    local ec2_host="${EC2_HOST:-}"
    local ssh_key="${EC2_KEY:-}"
    local forced_port=""
    local domain="${SERVICE_DOMAIN:-activelog.ai}"
    local no_nginx="false"
    local no_start="false"
    local dry_run="false"
    local verbose="false"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                usage
                exit 0
                ;;
            --host)
                ec2_host="$2"
                shift 2
                ;;
            --key)
                ssh_key="$2"
                shift 2
                ;;
            --port)
                forced_port="$2"
                shift 2
                ;;
            --domain)
                domain="$2"
                shift 2
                ;;
            --no-nginx)
                no_nginx="true"
                shift
                ;;
            --no-start)
                no_start="true"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            --verbose)
                verbose="true"
                shift
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                if [[ -z "$service_name" ]]; then
                    service_name="$1"
                else
                    log "ERROR" "Unexpected argument: $1"
                    usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Validate required arguments
    if [[ -z "$service_name" ]]; then
        log "ERROR" "Service name is required"
        usage
        exit 1
    fi
    
    if [[ -z "$ec2_host" ]]; then
        log "ERROR" "EC2 host is required (use --host or set EC2_HOST environment variable)"
        usage
        exit 1
    fi
    
    if [[ -z "$ssh_key" ]]; then
        log "ERROR" "SSH key is required (use --key or set EC2_KEY environment variable)"
        usage
        exit 1
    fi
    
    if [[ ! -f "$ssh_key" ]]; then
        log "ERROR" "SSH key file not found: $ssh_key"
        exit 1
    fi
    
    # Deploy the service
    if deploy_service "$service_name" "$ec2_host" "$ssh_key" "$forced_port" "$domain" "$no_nginx" "$no_start" "$dry_run" "$verbose"; then
        exit 0
    else
        log "ERROR" "Deployment failed"
        exit 1
    fi
}

# Check for required commands
for cmd in ssh rsync curl; do
    if ! command -v "$cmd" &> /dev/null; then
        log "ERROR" "Required command not found: $cmd"
        exit 1
    fi
done

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi