#!/bin/bash
set -e

# ActiveLog.ai Edge Offline Sync Setup
# Configures offline operation with intelligent sync queue

echo "=================================================="
echo "ActiveLog.ai Edge Offline Sync Setup"
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

print_status "Starting offline sync setup..."

# Create directories
print_status "Creating directories..."
sudo mkdir -p /etc/activelog
sudo mkdir -p /var/log/activelog
sudo mkdir -p /var/lib/activelog/sync
sudo mkdir -p /opt/activelog/sync
sudo mkdir -p ~/.config/activelog

# Set permissions
sudo chown -R $USER:$USER ~/.config/activelog
sudo chown $USER:$USER /var/lib/activelog/sync
sudo chmod 755 /opt/activelog/sync

# Update system packages
print_status "Updating system packages..."
sudo apt update

# Install required system packages
print_status "Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    sqlite3 \
    curl \
    wget \
    build-essential \
    python3-dev

# Create Python virtual environment
print_status "Setting up Python environment..."
cd /opt/activelog/sync
sudo python3 -m venv venv
sudo chown -R $USER:$USER venv

# Activate virtual environment and install packages
source venv/bin/activate

print_status "Installing Python dependencies..."
pip install --upgrade pip

# Install sync dependencies
pip install \
    asyncio \
    requests \
    sqlite3 \
    aiohttp \
    aiofiles

# Copy sync queue manager
print_status "Installing sync queue manager..."
sudo cp sync-queue.py /opt/activelog/sync/
sudo chown $USER:$USER /opt/activelog/sync/sync-queue.py
sudo chmod +x /opt/activelog/sync/sync-queue.py

# Create default configuration
print_status "Creating configuration files..."
cat > /tmp/sync_config.json << 'EOF'
{
    "api_base_url": "https://api.activelog.ai",
    "api_key": "",
    "queue_db_path": "/var/lib/activelog/sync/queue.db",
    "log_file": "/var/log/activelog/sync.log",
    "log_level": "INFO",
    "sync_interval": 60,
    "batch_size": 50,
    "max_concurrent": 5,
    "cleanup_age_hours": 24,
    "check_hosts": [
        "google.com",
        "cloudflare.com",
        "8.8.8.8"
    ],
    "retry_config": {
        "max_retries": 3,
        "backoff_multiplier": 2,
        "max_delay_minutes": 60
    },
    "file_upload": {
        "chunk_size_mb": 1,
        "max_file_size_mb": 100,
        "allowed_extensions": [".jpg", ".png", ".pdf", ".txt", ".log", ".json", ".csv"]
    }
}
EOF

sudo mv /tmp/sync_config.json /etc/activelog/sync.json
sudo chown $USER:$USER /etc/activelog/sync.json

# Create systemd service
print_status "Creating systemd service..."
cat > /tmp/activelog-sync.service << EOF
[Unit]
Description=ActiveLog Offline Sync Manager
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/activelog/sync
Environment=PATH=/opt/activelog/sync/venv/bin
ExecStart=/opt/activelog/sync/venv/bin/python /opt/activelog/sync/sync-queue.py --config /etc/activelog/sync.json
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
CapabilityBoundingSet=

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/activelog-sync.service /etc/systemd/system/
sudo systemctl daemon-reload

# Create log rotation configuration
print_status "Setting up log rotation..."
cat > /tmp/activelog-sync.logrotate << 'EOF'
/var/log/activelog/sync.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 activelog activelog
    postrotate
        systemctl reload activelog-sync 2>/dev/null || true
    endscript
}
EOF

sudo mv /tmp/activelog-sync.logrotate /etc/logrotate.d/activelog-sync

# Create CLI tool for sync management
print_status "Creating CLI management tool..."
cat > /tmp/activelog-sync-cli << 'EOF'
#!/bin/bash

# ActiveLog Sync CLI Tool

SYNC_DB="/var/lib/activelog/sync/queue.db"
CONFIG_FILE="/etc/activelog/sync.json"

usage() {
    echo "ActiveLog Offline Sync CLI"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  status             Show sync service status"
    echo "  start              Start sync service"
    echo "  stop               Stop sync service"
    echo "  restart            Restart sync service"
    echo "  logs               Show sync service logs"
    echo "  config             Show current configuration"
    echo "  queue-stats        Show sync queue statistics"
    echo "  queue-list         List pending sync items"
    echo "  queue-clear        Clear failed items from queue"
    echo "  network-test       Test network connectivity"
    echo "  force-sync         Force immediate sync attempt"
    echo "  backup             Create queue database backup"
    echo "  restore FILE       Restore queue database from backup"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 queue-stats"
    echo "  $0 force-sync"
}

check_db() {
    if [ ! -f "$SYNC_DB" ]; then
        echo "Sync database not found: $SYNC_DB"
        return 1
    fi
    return 0
}

case "$1" in
    status)
        echo "Sync Service Status:"
        echo "==================="
        systemctl status activelog-sync
        echo ""
        if check_db; then
            echo "Queue Statistics:"
            echo "================"
            sqlite3 "$SYNC_DB" "
                SELECT 
                    'Total items: ' || COUNT(*) as stat
                FROM sync_queue
                UNION ALL
                SELECT 
                    'Pending: ' || COUNT(*) as stat
                FROM sync_queue WHERE status = 'pending'
                UNION ALL
                SELECT 
                    'Completed: ' || COUNT(*) as stat
                FROM sync_queue WHERE status = 'completed'
                UNION ALL
                SELECT 
                    'Failed: ' || COUNT(*) as stat
                FROM sync_queue WHERE status = 'failed'
            "
        fi
        ;;
    
    start)
        echo "Starting sync service..."
        sudo systemctl start activelog-sync
        echo "Service started"
        ;;
    
    stop)
        echo "Stopping sync service..."
        sudo systemctl stop activelog-sync
        echo "Service stopped"
        ;;
    
    restart)
        echo "Restarting sync service..."
        sudo systemctl restart activelog-sync
        echo "Service restarted"
        ;;
    
    logs)
        echo "Sync Service Logs:"
        echo "=================="
        journalctl -u activelog-sync -f
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
    
    queue-stats)
        if ! check_db; then exit 1; fi
        echo "Sync Queue Statistics:"
        echo "====================="
        sqlite3 "$SYNC_DB" -header -column "
            SELECT 
                status,
                COUNT(*) as count,
                MIN(created_at) as oldest,
                MAX(created_at) as newest
            FROM sync_queue 
            GROUP BY status
            ORDER BY status
        "
        echo ""
        echo "Priority Breakdown:"
        echo "=================="
        sqlite3 "$SYNC_DB" -header -column "
            SELECT 
                CASE priority
                    WHEN 1 THEN 'Low'
                    WHEN 2 THEN 'Normal'
                    WHEN 3 THEN 'High'
                    WHEN 4 THEN 'Critical'
                    ELSE 'Unknown'
                END as priority,
                COUNT(*) as count
            FROM sync_queue 
            WHERE status = 'pending'
            GROUP BY priority
            ORDER BY priority DESC
        "
        ;;
    
    queue-list)
        if ! check_db; then exit 1; fi
        echo "Pending Sync Items:"
        echo "=================="
        sqlite3 "$SYNC_DB" -header -column "
            SELECT 
                SUBSTR(id, 1, 8) as id,
                operation_type,
                endpoint,
                CASE priority
                    WHEN 1 THEN 'Low'
                    WHEN 2 THEN 'Normal'
                    WHEN 3 THEN 'High'
                    WHEN 4 THEN 'Critical'
                END as priority,
                retry_count,
                created_at
            FROM sync_queue 
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT 20
        "
        ;;
    
    queue-clear)
        if ! check_db; then exit 1; fi
        echo "Clearing failed items from queue..."
        failed_count=$(sqlite3 "$SYNC_DB" "SELECT COUNT(*) FROM sync_queue WHERE status = 'failed'")
        if [ "$failed_count" -gt 0 ]; then
            sqlite3 "$SYNC_DB" "DELETE FROM sync_queue WHERE status = 'failed'"
            echo "Cleared $failed_count failed items"
        else
            echo "No failed items to clear"
        fi
        ;;
    
    network-test)
        echo "Testing network connectivity..."
        echo "=============================="
        
        # Test basic connectivity
        if ping -c 1 google.com > /dev/null 2>&1; then
            echo "✓ Basic connectivity: OK"
        else
            echo "✗ Basic connectivity: FAILED"
        fi
        
        # Test API endpoint
        api_url=$(jq -r '.api_base_url' "$CONFIG_FILE" 2>/dev/null || echo "https://api.activelog.ai")
        if curl -s --max-time 5 "$api_url/health" > /dev/null 2>&1; then
            echo "✓ API endpoint: OK"
        else
            echo "✗ API endpoint: FAILED"
        fi
        
        # Test DNS resolution
        if nslookup google.com > /dev/null 2>&1; then
            echo "✓ DNS resolution: OK"
        else
            echo "✗ DNS resolution: FAILED"
        fi
        ;;
    
    force-sync)
        echo "Forcing immediate sync attempt..."
        if systemctl is-active --quiet activelog-sync; then
            sudo systemctl restart activelog-sync
            echo "Sync service restarted - sync will begin immediately"
        else
            echo "Sync service is not running - starting it now"
            sudo systemctl start activelog-sync
        fi
        ;;
    
    backup)
        if ! check_db; then exit 1; fi
        BACKUP_FILE="/tmp/activelog-sync-backup-$(date +%Y%m%d-%H%M%S).sql"
        echo "Creating sync queue backup: $BACKUP_FILE"
        sqlite3 "$SYNC_DB" ".backup $BACKUP_FILE"
        echo "Backup created: $BACKUP_FILE"
        ;;
    
    restore)
        if [ -z "$2" ]; then
            echo "Error: Backup file required"
            usage
            exit 1
        fi
        echo "Restoring sync queue from: $2"
        echo "WARNING: This will overwrite the current queue!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo systemctl stop activelog-sync
            sqlite3 "$SYNC_DB" ".restore $2"
            sudo systemctl start activelog-sync
            echo "Sync queue restored and service restarted"
        else
            echo "Operation cancelled"
        fi
        ;;
    
    *)
        usage
        exit 1
        ;;
esac
EOF

sudo mv /tmp/activelog-sync-cli /usr/local/bin/activelog-sync
sudo chmod +x /usr/local/bin/activelog-sync

# Create Python API wrapper module
print_status "Creating Python API wrapper..."
cat > /tmp/activelog_offline_api.py << 'EOF'
#!/usr/bin/env python3
"""
ActiveLog Offline API Wrapper

Simple Python API for offline-capable operations.
Automatically queues operations when offline and syncs when online.
"""

import json
import os
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

class Priority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class ActiveLogOfflineAPI:
    def __init__(self, config_path: str = "/etc/activelog/sync.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.queue_db = self.config.get('queue_db_path', '/var/lib/activelog/sync/queue.db')
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except:
            return {
                'queue_db_path': '/var/lib/activelog/sync/queue.db',
                'api_base_url': 'https://api.activelog.ai'
            }
    
    def _add_to_queue(self, operation_type: str, endpoint: str, data: Dict[str, Any], 
                     priority: Priority = Priority.NORMAL, file_path: str = None) -> str:
        """Add operation to sync queue"""
        import hashlib
        
        # Generate unique ID
        content = f"{operation_type}-{endpoint}-{json.dumps(data, sort_keys=True)}"
        item_id = hashlib.md5(content.encode()).hexdigest()
        
        # Connect to queue database
        conn = sqlite3.connect(self.queue_db)
        cursor = conn.cursor()
        
        # Insert sync item
        cursor.execute('''
            INSERT OR REPLACE INTO sync_queue 
            (id, operation_type, endpoint, data, priority, created_at, scheduled_at,
             retry_count, max_retries, status, file_path, dependencies, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item_id, operation_type, endpoint, json.dumps(data),
            priority.value, datetime.now().isoformat(), datetime.now().isoformat(),
            0, 3, 'pending', file_path, '[]', '{}'
        ))
        
        conn.commit()
        conn.close()
        
        return item_id
    
    # Log Operations
    def create_log(self, message: str, level: str = "info", metadata: Dict[str, Any] = None) -> str:
        """Create log entry"""
        data = {
            'message': message,
            'level': level,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        return self._add_to_queue('create', '/api/logs', data, Priority.NORMAL)
    
    def create_critical_log(self, message: str, metadata: Dict[str, Any] = None) -> str:
        """Create critical log entry"""
        data = {
            'message': message,
            'level': 'critical',
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        return self._add_to_queue('create', '/api/logs', data, Priority.CRITICAL)
    
    # File Operations
    def upload_file(self, file_path: str, metadata: Dict[str, Any] = None) -> str:
        """Upload file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        data = {
            'filename': os.path.basename(file_path),
            'size': os.path.getsize(file_path),
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        return self._add_to_queue('upload', '/api/files', data, Priority.HIGH, file_path)
    
    # Metrics Operations
    def send_metrics(self, device_id: str, metrics: Dict[str, Any]) -> str:
        """Send device metrics"""
        data = {
            'device_id': device_id,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        }
        return self._add_to_queue('create', '/api/metrics', data, Priority.LOW)
    
    # Event Operations
    def report_event(self, event_type: str, description: str, severity: str = "info", 
                    metadata: Dict[str, Any] = None) -> str:
        """Report system event"""
        priority_map = {
            'debug': Priority.LOW,
            'info': Priority.NORMAL,
            'warning': Priority.HIGH,
            'error': Priority.CRITICAL,
            'critical': Priority.CRITICAL
        }
        
        data = {
            'event_type': event_type,
            'description': description,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        priority = priority_map.get(severity, Priority.NORMAL)
        return self._add_to_queue('create', '/api/events', data, priority)
    
    # Queue Management
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get sync queue statistics"""
        conn = sqlite3.connect(self.queue_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM sync_queue
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total': result[0] or 0,
            'pending': result[1] or 0,
            'completed': result[2] or 0,
            'failed': result[3] or 0
        }

# Example usage
if __name__ == '__main__':
    api = ActiveLogOfflineAPI()
    
    # Create some test entries
    api.create_log("Application started")
    api.report_event("startup", "System initialization completed")
    api.send_metrics("device-001", {"cpu_usage": 45.2, "memory_usage": 67.8})
    
    print("Queue stats:", api.get_queue_stats())
EOF

sudo mv /tmp/activelog_offline_api.py /opt/activelog/sync/
sudo chown $USER:$USER /opt/activelog/sync/activelog_offline_api.py

# Install Python API module system-wide
print_status "Installing Python API module..."
sudo pip3 install /opt/activelog/sync/activelog_offline_api.py 2>/dev/null || true

# Create example usage script
print_status "Creating example usage script..."
cat > ~/.config/activelog/offline-sync-example.py << 'EOF'
#!/usr/bin/env python3
"""
Example usage of ActiveLog Offline API

This script demonstrates how to use the offline-capable API
for logging, file uploads, metrics, and event reporting.
"""

import sys
import os
sys.path.append('/opt/activelog/sync')

from activelog_offline_api import ActiveLogOfflineAPI, Priority

def main():
    # Initialize API
    api = ActiveLogOfflineAPI()
    
    print("ActiveLog Offline API Example")
    print("============================")
    
    # Create log entries
    print("Creating log entries...")
    api.create_log("Application started successfully")
    api.create_log("User logged in", "info", {"user_id": "user123"})
    api.create_critical_log("Critical system error detected")
    
    # Report events
    print("Reporting events...")
    api.report_event("user_action", "User created new document", "info")
    api.report_event("system_warning", "Disk space low", "warning")
    
    # Send metrics
    print("Sending metrics...")
    api.send_metrics("device-001", {
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "disk_usage": 23.1,
        "temperature": 42.5
    })
    
    # Upload file (create test file first)
    test_file = "/tmp/test_upload.txt"
    with open(test_file, 'w') as f:
        f.write("This is a test file for upload")
    
    print("Uploading file...")
    api.upload_file(test_file, {"description": "Test file upload"})
    
    # Show queue statistics
    stats = api.get_queue_stats()
    print("\nQueue Statistics:")
    print(f"Total items: {stats['total']}")
    print(f"Pending: {stats['pending']}")
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    
    print("\nItems have been queued for sync.")
    print("Use 'activelog-sync status' to check sync progress.")

if __name__ == '__main__':
    main()
EOF

chmod +x ~/.config/activelog/offline-sync-example.py

# Test network connectivity
print_status "Testing network connectivity..."
if ping -c 1 google.com > /dev/null 2>&1; then
    print_status "Network connectivity: OK"
else
    print_warning "Network connectivity: Limited or offline"
fi

# Initialize sync queue database
print_status "Initializing sync queue database..."
cd /opt/activelog/sync
source venv/bin/activate
python3 -c "
from sync_queue import OfflineSyncQueue
queue = OfflineSyncQueue('/var/lib/activelog/sync/queue.db')
print('Sync queue database initialized')
"

# Start and enable service
print_status "Starting sync service..."
sudo systemctl enable activelog-sync
sudo systemctl start activelog-sync

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet activelog-sync; then
    print_status "Sync service is running"
else
    print_warning "Sync service failed to start - checking logs..."
    journalctl -u activelog-sync --no-pager -n 20
fi

# Create quick reference guide
print_status "Creating quick reference guide..."
cat > ~/.config/activelog/offline-sync-reference.md << 'EOF'
# ActiveLog Offline Sync Quick Reference

## Service Management
```bash
sudo systemctl start activelog-sync
sudo systemctl stop activelog-sync
sudo systemctl restart activelog-sync
sudo systemctl status activelog-sync
```

## CLI Commands
```bash
activelog-sync status          # Service and queue status
activelog-sync queue-stats     # Detailed queue statistics
activelog-sync queue-list      # List pending items
activelog-sync network-test    # Test connectivity
activelog-sync force-sync      # Force immediate sync
activelog-sync backup          # Create database backup
activelog-sync logs            # View service logs
```

## Python API Usage
```python
from activelog_offline_api import ActiveLogOfflineAPI

api = ActiveLogOfflineAPI()

# Create log entries
api.create_log("Application started")
api.create_critical_log("Critical error occurred")

# Report events
api.report_event("user_action", "User logged in", "info")

# Send metrics
api.send_metrics("device-001", {"cpu": 45.2, "memory": 67.8})

# Upload files
api.upload_file("/path/to/file.txt", {"type": "log"})

# Check queue status
stats = api.get_queue_stats()
print(f"Pending items: {stats['pending']}")
```

## Configuration
- Config file: /etc/activelog/sync.json
- Database: /var/lib/activelog/sync/queue.db
- Logs: /var/log/activelog/sync.log

## How It Works
1. API calls are queued locally when offline
2. Sync service automatically retries when online
3. Items are prioritized (Critical > High > Normal > Low)
4. Failed items are retried with exponential backoff
5. Large files are uploaded in chunks for reliability

## Troubleshooting
1. Check service: `activelog-sync status`
2. View logs: `activelog-sync logs`
3. Test network: `activelog-sync network-test`
4. Check queue: `activelog-sync queue-stats`
5. Force sync: `activelog-sync force-sync`
EOF

echo ""
echo "=================================================="
print_status "Offline Sync Setup Complete!"
echo "=================================================="
echo ""
echo "Service Status:"
systemctl status activelog-sync --no-pager -l
echo ""
print_status "CLI Tool: activelog-sync"
print_status "Configuration: /etc/activelog/sync.json"
print_status "Database: /var/lib/activelog/sync/queue.db"
print_status "Logs: /var/log/activelog/sync.log"
print_status "Reference: ~/.config/activelog/offline-sync-reference.md"
print_status "Example: ~/.config/activelog/offline-sync-example.py"
echo ""
print_status "To check sync status: activelog-sync status"
print_status "To test the API: python3 ~/.config/activelog/offline-sync-example.py"
print_status "To view logs: activelog-sync logs"
echo ""

# Run example to test setup
print_status "Testing offline API..."
python3 ~/.config/activelog/offline-sync-example.py

echo ""
print_status "Setup completed successfully!"
print_status "Your edge device can now operate offline and sync data when connectivity is restored."