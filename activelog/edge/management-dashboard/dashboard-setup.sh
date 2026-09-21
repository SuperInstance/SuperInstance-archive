#!/bin/bash
set -e

# ActiveLog.ai Edge Device Management Dashboard Setup
# Configures web-based device monitoring and management

echo "=================================================="
echo "ActiveLog.ai Edge Device Management Dashboard Setup"
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root for security reasons"
    exit 1
fi

print_status "Starting Edge Device Management Dashboard setup..."

# Create directories
print_status "Creating directories..."
sudo mkdir -p /etc/activelog
sudo mkdir -p /var/log/activelog
sudo mkdir -p /opt/activelog/dashboard
sudo mkdir -p /opt/activelog/dashboard/templates
sudo mkdir -p /opt/activelog/dashboard/static
sudo mkdir -p ~/.config/activelog

# Set permissions
sudo chown -R $USER:$USER ~/.config/activelog
sudo chmod 755 /opt/activelog/dashboard

# Update system packages
print_status "Updating system packages..."
sudo apt update

# Install required system packages
print_status "Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    supervisor \
    build-essential \
    python3-dev \
    sqlite3

# Create Python virtual environment
print_status "Setting up Python environment..."
cd /opt/activelog/dashboard
sudo python3 -m venv venv
sudo chown -R $USER:$USER venv

# Activate virtual environment and install packages
source venv/bin/activate

print_status "Installing Python dependencies..."
pip install --upgrade pip

# Install dashboard dependencies
pip install \
    flask \
    flask-socketio \
    requests \
    psutil \
    sqlite3

# Handle optional dependencies
print_warning "Installing optional dependencies..."

# Try to install additional packages
pip install \
    eventlet \
    gunicorn \
    python-socketio[client]

# Copy dashboard files
print_status "Installing dashboard files..."
sudo cp dashboard.py /opt/activelog/dashboard/
sudo cp -r templates /opt/activelog/dashboard/
sudo chown -R $USER:$USER /opt/activelog/dashboard/dashboard.py
sudo chown -R $USER:$USER /opt/activelog/dashboard/templates
sudo chmod +x /opt/activelog/dashboard/dashboard.py

# Create default configuration
print_status "Creating configuration files..."
cat > /tmp/dashboard_config.json << 'EOF'
{
    "database_path": "/var/lib/activelog/dashboard.db",
    "log_file": "/var/log/activelog/dashboard.log",
    "log_level": "INFO",
    "web_port": 5000,
    "web_host": "0.0.0.0",
    "discovery_interval": 300,
    "status_update_interval": 60,
    "metrics_retention_days": 30
}
EOF

sudo mv /tmp/dashboard_config.json /etc/activelog/dashboard.json
sudo chown $USER:$USER /etc/activelog/dashboard.json

# Create database directory
sudo mkdir -p /var/lib/activelog
sudo chown $USER:$USER /var/lib/activelog

# Create systemd service
print_status "Creating systemd service..."
cat > /tmp/activelog-dashboard.service << EOF
[Unit]
Description=ActiveLog Edge Device Management Dashboard
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/activelog/dashboard
Environment=PATH=/opt/activelog/dashboard/venv/bin
ExecStart=/opt/activelog/dashboard/venv/bin/python /opt/activelog/dashboard/dashboard.py --config /etc/activelog/dashboard.json
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/activelog /var/log/activelog /tmp
CapabilityBoundingSet=CAP_NET_RAW

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/activelog-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload

# Configure Nginx reverse proxy
print_status "Configuring Nginx reverse proxy..."
cat > /tmp/activelog-dashboard-nginx << 'EOF'
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Main dashboard
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }

    # WebSocket support
    location /socket.io/ {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /opt/activelog/dashboard/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

sudo mv /tmp/activelog-dashboard-nginx /etc/nginx/sites-available/activelog-dashboard
sudo ln -sf /etc/nginx/sites-available/activelog-dashboard /etc/nginx/sites-enabled/

# Remove default Nginx site
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
if sudo nginx -t; then
    print_status "Nginx configuration is valid"
else
    print_error "Nginx configuration test failed"
    exit 1
fi

# Create log rotation configuration
print_status "Setting up log rotation..."
cat > /tmp/activelog-dashboard.logrotate << 'EOF'
/var/log/activelog/dashboard.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 activelog activelog
    postrotate
        systemctl reload activelog-dashboard 2>/dev/null || true
    endscript
}
EOF

sudo mv /tmp/activelog-dashboard.logrotate /etc/logrotate.d/activelog-dashboard

# Create CLI tool for dashboard management
print_status "Creating CLI management tool..."
cat > /tmp/activelog-dashboard-cli << 'EOF'
#!/bin/bash

# ActiveLog Dashboard CLI Tool

DASHBOARD_API="http://localhost"
CONFIG_FILE="/etc/activelog/dashboard.json"

usage() {
    echo "ActiveLog Dashboard CLI"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  status             Show dashboard service status"
    echo "  start              Start dashboard service"
    echo "  stop               Stop dashboard service"
    echo "  restart            Restart dashboard service"
    echo "  logs               Show dashboard service logs"
    echo "  config             Show current configuration"
    echo "  devices            List managed devices"
    echo "  events             Show recent events"
    echo "  nginx-status       Show Nginx status"
    echo "  nginx-restart      Restart Nginx"
    echo "  backup             Create database backup"
    echo "  restore FILE       Restore database from backup"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 devices"
    echo "  $0 backup"
}

api_call() {
    local endpoint="$1"
    curl -s "$DASHBOARD_API$endpoint" 2>/dev/null || echo '{"error": "Dashboard not available"}'
}

case "$1" in
    status)
        echo "Dashboard Service Status:"
        echo "========================"
        systemctl status activelog-dashboard
        echo ""
        echo "Nginx Status:"
        echo "============="
        systemctl status nginx
        ;;
    
    start)
        echo "Starting dashboard services..."
        sudo systemctl start activelog-dashboard
        sudo systemctl start nginx
        echo "Services started"
        ;;
    
    stop)
        echo "Stopping dashboard services..."
        sudo systemctl stop activelog-dashboard
        echo "Services stopped"
        ;;
    
    restart)
        echo "Restarting dashboard services..."
        sudo systemctl restart activelog-dashboard
        sudo systemctl restart nginx
        echo "Services restarted"
        ;;
    
    logs)
        echo "Dashboard Service Logs:"
        echo "======================"
        journalctl -u activelog-dashboard -f
        ;;
    
    config)
        echo "Current Configuration:"
        echo "====================="
        if [ -f "$CONFIG_FILE" ]; then
            cat "$CONFIG_FILE" | jq .
        else
            echo "Configuration file not found: $CONFIG_FILE"
        fi
        ;;
    
    devices)
        echo "Managed Devices:"
        echo "==============="
        api_call "/api/devices" | jq '.[] | "\(.name) (\(.device_type}) - \(.status)"' -r
        ;;
    
    events)
        echo "Recent Events:"
        echo "============="
        api_call "/api/events" | jq '.[] | "\(.timestamp) - \(.event_type): \(.device_id)"' -r | head -20
        ;;
    
    nginx-status)
        echo "Nginx Status:"
        echo "============"
        systemctl status nginx
        ;;
    
    nginx-restart)
        echo "Restarting Nginx..."
        sudo systemctl restart nginx
        echo "Nginx restarted"
        ;;
    
    backup)
        BACKUP_FILE="/tmp/activelog-dashboard-backup-$(date +%Y%m%d-%H%M%S).sql"
        echo "Creating database backup: $BACKUP_FILE"
        sqlite3 /var/lib/activelog/dashboard.db ".backup $BACKUP_FILE"
        echo "Backup created: $BACKUP_FILE"
        ;;
    
    restore)
        if [ -z "$2" ]; then
            echo "Error: Backup file required"
            usage
            exit 1
        fi
        echo "Restoring database from: $2"
        sqlite3 /var/lib/activelog/dashboard.db ".restore $2"
        echo "Database restored"
        ;;
    
    *)
        usage
        exit 1
        ;;
esac
EOF

sudo mv /tmp/activelog-dashboard-cli /usr/local/bin/activelog-dashboard
sudo chmod +x /usr/local/bin/activelog-dashboard

# Configure firewall
print_status "Configuring firewall..."
if command -v ufw > /dev/null; then
    sudo ufw allow 80/tcp comment "ActiveLog Dashboard HTTP"
    sudo ufw allow 5000/tcp comment "ActiveLog Dashboard Direct"
    print_status "Firewall rules added for HTTP (80) and direct access (5000)"
else
    print_warning "ufw not available - please manually configure firewall for ports 80 and 5000"
fi

# Start and enable services
print_status "Starting dashboard services..."
sudo systemctl enable activelog-dashboard
sudo systemctl start activelog-dashboard

# Wait for service to start
sleep 3

# Check dashboard service status
if systemctl is-active --quiet activelog-dashboard; then
    print_status "Dashboard service is running"
else
    print_warning "Dashboard service failed to start - checking logs..."
    journalctl -u activelog-dashboard --no-pager -n 20
fi

# Start Nginx
sudo systemctl enable nginx
sudo systemctl restart nginx

# Check Nginx status
if systemctl is-active --quiet nginx; then
    print_status "Nginx is running"
else
    print_warning "Nginx failed to start"
    systemctl status nginx --no-pager -l
fi

# Test dashboard endpoint
print_status "Testing dashboard endpoint..."
sleep 5
if curl -s http://localhost/api/stats > /dev/null; then
    print_status "Dashboard API is responding"
else
    print_warning "Dashboard API not responding - service may still be starting"
fi

# Create desktop entry for GUI access (if desktop environment detected)
if [ -n "$DISPLAY" ] && command -v xdg-desktop-menu > /dev/null; then
    print_status "Creating desktop entry..."
    
    cat > /tmp/activelog-dashboard.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=ActiveLog Dashboard
Comment=Edge Device Management Dashboard
Icon=network-server
Exec=xdg-open http://localhost
Terminal=false
Categories=Network;System;
EOF
    
    xdg-desktop-menu install /tmp/activelog-dashboard.desktop
    rm /tmp/activelog-dashboard.desktop
fi

# Create quick reference guide
print_status "Creating quick reference guide..."
cat > ~/.config/activelog/dashboard-reference.md << 'EOF'
# ActiveLog Edge Device Management Dashboard Quick Reference

## Service Management
```bash
sudo systemctl start activelog-dashboard
sudo systemctl stop activelog-dashboard
sudo systemctl restart activelog-dashboard
sudo systemctl status activelog-dashboard
```

## Nginx Management
```bash
sudo systemctl restart nginx
sudo systemctl status nginx
sudo nginx -t  # Test configuration
```

## CLI Commands
```bash
activelog-dashboard status          # Service status
activelog-dashboard devices         # List devices
activelog-dashboard events          # Recent events
activelog-dashboard logs            # View logs
activelog-dashboard backup          # Create backup
activelog-dashboard config          # Show configuration
```

## Web Interface
- Main Dashboard: http://localhost/ or http://[server-ip]/
- Direct Access: http://localhost:5000/
- API Endpoints: http://localhost/api/

## Configuration File
/etc/activelog/dashboard.json

## Log Files
- Dashboard: /var/log/activelog/dashboard.log
- Nginx: /var/log/nginx/
- Systemd: journalctl -u activelog-dashboard

## Database
- Location: /var/lib/activelog/dashboard.db
- Backup: activelog-dashboard backup
- Restore: activelog-dashboard restore [file]

## API Endpoints
- GET /api/devices                  # List all devices
- GET /api/devices/{id}             # Get device details
- GET /api/devices/{id}/metrics     # Get device metrics
- POST /api/devices/{id}/command    # Send command to device
- GET /api/events                   # Get recent events
- GET /api/stats                    # Get dashboard statistics

## Troubleshooting
1. Check service: `systemctl status activelog-dashboard`
2. Check logs: `journalctl -u activelog-dashboard -f`
3. Check Nginx: `systemctl status nginx`
4. Test API: `curl http://localhost/api/stats`
5. Check ports: `netstat -tlnp | grep :5000`
6. Check database: `sqlite3 /var/lib/activelog/dashboard.db ".tables"`

## Security
- Dashboard runs as non-root user
- Nginx provides reverse proxy with security headers
- Database stored in protected directory
- Firewall rules for required ports only
EOF

echo ""
echo "=================================================="
print_status "Edge Device Management Dashboard Setup Complete!"
echo "=================================================="
echo ""
echo "Service Status:"
systemctl status activelog-dashboard --no-pager -l
echo ""
echo "Nginx Status:"
systemctl status nginx --no-pager -l
echo ""
print_status "Web Interface: http://localhost/"
print_status "Direct Access: http://localhost:5000/"
print_status "CLI Tool: activelog-dashboard"
print_status "Configuration: /etc/activelog/dashboard.json"
print_status "Logs: /var/log/activelog/dashboard.log"
print_status "Reference: ~/.config/activelog/dashboard-reference.md"
echo ""
print_status "To view dashboard status: activelog-dashboard status"
print_status "To view managed devices: activelog-dashboard devices"
print_status "To view logs: activelog-dashboard logs"
echo ""

# Show initial dashboard stats
print_status "Initial dashboard stats:"
sleep 3
activelog-dashboard devices 2>/dev/null || print_warning "Dashboard not ready yet - try 'activelog-dashboard devices' in a moment"

# Show local IP addresses for remote access
print_status "Dashboard can be accessed from these addresses:"
ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print "http://" $2}' | sed 's/\/.*$//'

print_status "Setup completed successfully!"
echo ""
print_status "Open your web browser and navigate to http://localhost/ to access the dashboard"