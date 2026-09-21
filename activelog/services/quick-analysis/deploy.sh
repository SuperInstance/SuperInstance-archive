#!/bin/bash

# Quick Analysis Portal Deployment Script
# This script sets up the production environment

set -e  # Exit on any error

echo "🚀 Starting Quick Analysis Portal Deployment..."

# Configuration
SERVICE_NAME="quick-analysis"
INSTALL_DIR="/opt/$SERVICE_NAME"
LOG_DIR="/var/log/$SERVICE_NAME"
NGINX_SITES="/etc/nginx/sites-available"
SYSTEMD_DIR="/etc/systemd/system"
USER="www-data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

print_status "Setting up directory structure..."

# Create directories
mkdir -p $INSTALL_DIR
mkdir -p $LOG_DIR
mkdir -p $INSTALL_DIR/data
mkdir -p $INSTALL_DIR/logs

print_status "Installing system dependencies..."

# Update package list
apt-get update

# Install required packages
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    redis-server \
    curl \
    git \
    build-essential \
    libssl-dev \
    libffi-dev

print_status "Setting up Python virtual environment..."

# Create virtual environment
python3 -m venv $INSTALL_DIR/venv

# Copy application files
print_status "Copying application files..."
cp -r . $INSTALL_DIR/
cd $INSTALL_DIR

# Install Python dependencies
print_status "Installing Python dependencies..."
$INSTALL_DIR/venv/bin/pip install --upgrade pip
$INSTALL_DIR/venv/bin/pip install -r requirements.txt

print_status "Setting up environment configuration..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.template .env
    print_warning "Created .env file from template. Please update it with your configuration."
fi

print_status "Setting up database..."

# Initialize database
$INSTALL_DIR/venv/bin/python -c "
import sqlite3
import os
from pathlib import Path

# Ensure data directory exists
Path('data').mkdir(exist_ok=True)

# Create database and tables
conn = sqlite3.connect('data/quick_analysis.db')
cursor = conn.cursor()

# Create users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        tier TEXT DEFAULT 'free',
        api_key TEXT UNIQUE,
        daily_searches INTEGER DEFAULT 0,
        last_search_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Create search_history table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        search_type TEXT DEFAULT 'basic',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES users (session_id)
    )
''')

# Create indexes for better performance
cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_session_id ON users (session_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_api_key ON users (api_key)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_history_session_id ON search_history (session_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_history_timestamp ON search_history (timestamp)')

conn.commit()
conn.close()
print('Database initialized successfully')
"

print_status "Setting up systemd service..."

# Install systemd service
cp quick-analysis.service $SYSTEMD_DIR/$SERVICE_NAME.service

print_status "Configuring nginx..."

# Create nginx configuration
cat > $NGINX_SITES/$SERVICE_NAME << 'EOF'
server {
    listen 80;
    server_name analysis.activeledger.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name analysis.activeledger.ai;

    # SSL configuration (update with your certificate paths)
    # ssl_certificate /path/to/your/certificate.pem;
    # ssl_certificate_key /path/to/your/private.key;

    # For development/testing (remove in production)
    listen 8420;

    location / {
        proxy_pass http://127.0.0.1:8420;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias $INSTALL_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable nginx site
ln -sf $NGINX_SITES/$SERVICE_NAME /etc/nginx/sites-enabled/

print_status "Setting up permissions..."

# Set ownership and permissions
chown -R $USER:$USER $INSTALL_DIR
chown -R $USER:$USER $LOG_DIR
chmod -R 755 $INSTALL_DIR
chmod -R 755 $LOG_DIR

print_status "Starting services..."

# Reload systemd
systemctl daemon-reload

# Enable and start services
systemctl enable redis-server
systemctl start redis-server
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME
systemctl enable nginx
systemctl restart nginx

print_status "Testing deployment..."

# Wait for service to start
sleep 5

# Test health endpoint
if curl -f http://localhost:8420/health > /dev/null 2>&1; then
    print_status "Service is running and healthy!"
else
    print_error "Service health check failed"
    systemctl status $SERVICE_NAME
    exit 1
fi

print_status "Creating maintenance scripts..."

# Create backup script
cat > /usr/local/bin/backup-quick-analysis << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/quick-analysis"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp /opt/quick-analysis/data/quick_analysis.db $BACKUP_DIR/quick_analysis_$DATE.db

# Backup logs (last 7 days)
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /var/log/quick-analysis/

# Keep only last 30 backups
find $BACKUP_DIR -name "quick_analysis_*.db" -type f -mtime +30 -delete
find $BACKUP_DIR -name "logs_*.tar.gz" -type f -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /usr/local/bin/backup-quick-analysis

# Create update script
cat > /usr/local/bin/update-quick-analysis << 'EOF'
#!/bin/bash
set -e

echo "Updating Quick Analysis Portal..."

cd /opt/quick-analysis

# Backup current installation
/usr/local/bin/backup-quick-analysis

# Pull latest changes (if using git)
# git pull origin main

# Update dependencies
/opt/quick-analysis/venv/bin/pip install --upgrade -r requirements.txt

# Restart service
systemctl restart quick-analysis

echo "Update completed successfully"
EOF

chmod +x /usr/local/bin/update-quick-analysis

print_status "Setting up log rotation..."

# Create logrotate configuration
cat > /etc/logrotate.d/$SERVICE_NAME << 'EOF'
/var/log/quick-analysis/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload quick-analysis
    endscript
}
EOF

print_status "Deployment completed successfully!"

echo
echo "📋 Deployment Summary:"
echo "======================"
echo "Service: $SERVICE_NAME"
echo "Install Directory: $INSTALL_DIR"
echo "Log Directory: $LOG_DIR"
echo "Service Status: $(systemctl is-active $SERVICE_NAME)"
echo "URL: http://localhost:8420"
echo "Health Check: http://localhost:8420/health"
echo

print_status "Useful commands:"
echo "  sudo systemctl status $SERVICE_NAME     # Check service status"
echo "  sudo systemctl restart $SERVICE_NAME    # Restart service"
echo "  sudo tail -f $LOG_DIR/access.log        # View access logs"
echo "  sudo /usr/local/bin/backup-quick-analysis # Create backup"
echo "  sudo /usr/local/bin/update-quick-analysis # Update application"

echo
print_warning "Next steps:"
echo "  1. Update .env file with your configuration"
echo "  2. Configure SSL certificates for production"
echo "  3. Update nginx configuration for your domain"
echo "  4. Set up monitoring and alerts"
echo "  5. Configure payment processing for premium features"

echo
print_status "🎉 Quick Analysis Portal is now running!"