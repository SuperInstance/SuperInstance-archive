#!/bin/bash
set -e

# ActiveLog.ai Edge Device Discovery Setup
# Configures Bluetooth/WiFi device discovery protocol

echo "=================================================="
echo "ActiveLog.ai Edge Device Discovery Setup"
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

print_status "Starting device discovery setup..."

# Create directories
print_status "Creating directories..."
sudo mkdir -p /etc/activelog
sudo mkdir -p /var/log/activelog
sudo mkdir -p /opt/activelog/discovery
sudo mkdir -p ~/.config/activelog

# Set permissions
sudo chown -R $USER:$USER ~/.config/activelog
sudo chmod 755 /opt/activelog/discovery

# Update system packages
print_status "Updating system packages..."
sudo apt update

# Install required system packages
print_status "Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    bluetooth \
    bluez \
    bluez-tools \
    libbluetooth-dev \
    wireless-tools \
    net-tools \
    nmap \
    iwlist \
    rfkill \
    build-essential \
    python3-dev

# Enable and start Bluetooth service
print_status "Configuring Bluetooth service..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Ensure Bluetooth is not blocked
sudo rfkill unblock bluetooth

# Create Python virtual environment
print_status "Setting up Python environment..."
cd /opt/activelog/discovery
sudo python3 -m venv venv
sudo chown -R $USER:$USER venv

# Activate virtual environment and install packages
source venv/bin/activate

print_status "Installing Python dependencies..."
pip install --upgrade pip

# Install discovery agent dependencies
pip install \
    asyncio \
    pybluez \
    wifi \
    requests \
    aiohttp \
    sqlite3

# Handle optional dependencies
print_warning "Installing optional dependencies (may fail on some systems)..."

# Try to install pybluez with fallback
if ! pip install pybluez; then
    print_warning "pybluez installation failed - trying alternative method..."
    sudo apt install -y python3-bluetooth python3-bluez
fi

# Try to install wifi module
if ! pip install wifi; then
    print_warning "wifi module installation failed - using system tools fallback"
fi

# Copy discovery agent
print_status "Installing discovery agent..."
sudo cp discovery-agent.py /opt/activelog/discovery/
sudo chown $USER:$USER /opt/activelog/discovery/discovery-agent.py
sudo chmod +x /opt/activelog/discovery/discovery-agent.py

# Create default configuration
print_status "Creating configuration files..."
cat > /tmp/discovery_config.json << 'EOF'
{
    "scan_interval": 60,
    "bluetooth_scan_duration": 10,
    "cleanup_interval": 3600,
    "max_device_age_hours": 24,
    "registry_db_path": "/tmp/activelog_device_registry.db",
    "log_file": "/var/log/activelog/discovery.log",
    "log_level": "INFO",
    "enable_bluetooth": true,
    "enable_wifi": true,
    "enable_network_scan": true,
    "trusted_device_patterns": [
        "activelog-*",
        "pi-*",
        "jetson-*",
        "edge-*"
    ],
    "api_port": 8765
}
EOF

sudo mv /tmp/discovery_config.json /etc/activelog/discovery.json
sudo chown $USER:$USER /etc/activelog/discovery.json

# Create systemd service
print_status "Creating systemd service..."
cat > /tmp/activelog-discovery.service << EOF
[Unit]
Description=ActiveLog Device Discovery Agent
After=network.target bluetooth.service
Wants=bluetooth.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/activelog/discovery
Environment=PATH=/opt/activelog/discovery/venv/bin
ExecStart=/opt/activelog/discovery/venv/bin/python /opt/activelog/discovery/discovery-agent.py --config /etc/activelog/discovery.json
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/tmp /var/log/activelog
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/activelog-discovery.service /etc/systemd/system/
sudo systemctl daemon-reload

# Create log rotation configuration
print_status "Setting up log rotation..."
cat > /tmp/activelog-discovery.logrotate << 'EOF'
/var/log/activelog/discovery.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 activelog activelog
    postrotate
        systemctl reload activelog-discovery 2>/dev/null || true
    endscript
}
EOF

sudo mv /tmp/activelog-discovery.logrotate /etc/logrotate.d/activelog-discovery

# Create CLI tool for device management
print_status "Creating CLI management tool..."
cat > /tmp/activelog-discovery-cli << 'EOF'
#!/bin/bash

# ActiveLog Device Discovery CLI Tool

DISCOVERY_API="http://localhost:8765"
CONFIG_FILE="/etc/activelog/discovery.json"

usage() {
    echo "ActiveLog Device Discovery CLI"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  list [TYPE]        List discovered devices (optional type filter)"
    echo "  show DEVICE_ID     Show detailed device information"
    echo "  trust DEVICE_ID    Mark device as trusted"
    echo "  untrust DEVICE_ID  Remove device from trusted list"
    echo "  status             Show discovery service status"
    echo "  start              Start discovery service"
    echo "  stop               Stop discovery service"
    echo "  restart            Restart discovery service"
    echo "  logs               Show discovery service logs"
    echo "  config             Show current configuration"
    echo ""
    echo "Device Types:"
    echo "  bluetooth          Bluetooth devices"
    echo "  wifi               WiFi networks"
    echo "  network            Network devices"
    echo "  activelog          ActiveLog edge devices"
    echo ""
    echo "Examples:"
    echo "  $0 list bluetooth"
    echo "  $0 show bt_aa_bb_cc_dd_ee_ff"
    echo "  $0 trust net_192_168_1_100"
}

api_call() {
    local endpoint="$1"
    curl -s "$DISCOVERY_API$endpoint" 2>/dev/null || echo '{"error": "API not available"}'
}

case "$1" in
    list)
        if [ -n "$2" ]; then
            echo "Devices of type: $2"
            echo "=================="
            api_call "/devices" | jq --arg type "$2" '.[] | select(.device_type == $type) | "\(.name) (\(.device_id)) - \(.address)"' -r
        else
            echo "All discovered devices:"
            echo "======================"
            api_call "/devices" | jq '.[] | "\(.device_type): \(.name) (\(.device_id)) - \(.address)"' -r
        fi
        ;;
    
    show)
        if [ -z "$2" ]; then
            echo "Error: Device ID required"
            usage
            exit 1
        fi
        echo "Device Information:"
        echo "=================="
        api_call "/devices/$2" | jq .
        ;;
    
    trust|untrust)
        echo "Error: Trust management not yet implemented via CLI"
        echo "Please use the API directly or modify the configuration file"
        ;;
    
    status)
        echo "Discovery Service Status:"
        echo "========================"
        systemctl status activelog-discovery
        ;;
    
    start)
        echo "Starting discovery service..."
        sudo systemctl start activelog-discovery
        echo "Service started"
        ;;
    
    stop)
        echo "Stopping discovery service..."
        sudo systemctl stop activelog-discovery
        echo "Service stopped"
        ;;
    
    restart)
        echo "Restarting discovery service..."
        sudo systemctl restart activelog-discovery
        echo "Service restarted"
        ;;
    
    logs)
        echo "Discovery Service Logs:"
        echo "======================"
        journalctl -u activelog-discovery -f
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
    
    *)
        usage
        exit 1
        ;;
esac
EOF

sudo mv /tmp/activelog-discovery-cli /usr/local/bin/activelog-discovery
sudo chmod +x /usr/local/bin/activelog-discovery

# Configure Bluetooth permissions
print_status "Configuring Bluetooth permissions..."
sudo usermod -a -G bluetooth $USER

# Configure network scanning permissions
print_status "Configuring network scanning permissions..."
sudo setcap cap_net_raw,cap_net_admin+eip /usr/bin/nmap || print_warning "Could not set nmap capabilities"

# Test Bluetooth functionality
print_status "Testing Bluetooth functionality..."
if bluetoothctl --version > /dev/null 2>&1; then
    print_status "Bluetooth CLI available"
    
    # Enable Bluetooth if needed
    if ! bluetoothctl show | grep -q "Powered: yes"; then
        print_status "Enabling Bluetooth..."
        echo "power on" | bluetoothctl
        sleep 2
    fi
    
    # Make device discoverable
    echo "discoverable on" | bluetoothctl
    echo "pairable on" | bluetoothctl
else
    print_warning "Bluetooth CLI not available"
fi

# Test WiFi functionality
print_status "Testing WiFi functionality..."
if iwconfig 2>/dev/null | grep -q "IEEE 802.11"; then
    print_status "WiFi interface available"
else
    print_warning "No WiFi interface detected"
fi

# Test network tools
print_status "Testing network tools..."
if command -v nmap > /dev/null; then
    print_status "nmap available for network scanning"
else
    print_warning "nmap not available - network scanning will use ping fallback"
fi

# Create firewall rule for API port
print_status "Configuring firewall..."
if command -v ufw > /dev/null; then
    sudo ufw allow 8765/tcp comment "ActiveLog Discovery API"
    print_status "Firewall rule added for API port 8765"
else
    print_warning "ufw not available - please manually configure firewall for port 8765"
fi

# Start and enable service
print_status "Starting discovery service..."
sudo systemctl enable activelog-discovery
sudo systemctl start activelog-discovery

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet activelog-discovery; then
    print_status "Discovery service is running"
else
    print_warning "Discovery service failed to start - checking logs..."
    journalctl -u activelog-discovery --no-pager -n 20
fi

# Test API endpoint
print_status "Testing API endpoint..."
if curl -s http://localhost:8765/devices > /dev/null; then
    print_status "API endpoint is responding"
else
    print_warning "API endpoint not responding - service may still be starting"
fi

# Create desktop entry for GUI management (if desktop environment detected)
if [ -n "$DISPLAY" ] && command -v xdg-desktop-menu > /dev/null; then
    print_status "Creating desktop entry..."
    
    cat > /tmp/activelog-discovery.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=ActiveLog Device Discovery
Comment=Manage ActiveLog edge device discovery
Icon=network-wireless
Exec=x-terminal-emulator -e activelog-discovery status
Terminal=false
Categories=Network;System;
EOF
    
    xdg-desktop-menu install /tmp/activelog-discovery.desktop
    rm /tmp/activelog-discovery.desktop
fi

print_status "Creating quick reference guide..."
cat > ~/.config/activelog/discovery-reference.md << 'EOF'
# ActiveLog Device Discovery Quick Reference

## Service Management
```bash
sudo systemctl start activelog-discovery
sudo systemctl stop activelog-discovery
sudo systemctl restart activelog-discovery
sudo systemctl status activelog-discovery
```

## CLI Commands
```bash
activelog-discovery list                    # List all devices
activelog-discovery list bluetooth         # List Bluetooth devices
activelog-discovery show DEVICE_ID         # Show device details
activelog-discovery status                 # Service status
activelog-discovery logs                   # View logs
activelog-discovery config                 # Show configuration
```

## API Endpoints
- GET http://localhost:8765/devices         # List all devices
- GET http://localhost:8765/devices/ID      # Get specific device

## Configuration File
/etc/activelog/discovery.json

## Log Files
/var/log/activelog/discovery.log

## Device Types
- bluetooth: Bluetooth devices (phones, headsets, etc.)
- wifi: WiFi access points and networks
- network: Network devices (computers, printers, etc.)
- activelog: ActiveLog edge devices with special capabilities

## Troubleshooting
1. Check service status: `systemctl status activelog-discovery`
2. View logs: `journalctl -u activelog-discovery -f`
3. Test Bluetooth: `bluetoothctl scan on`
4. Test WiFi: `iwlist scan`
5. Test API: `curl http://localhost:8765/devices`
EOF

echo ""
echo "=================================================="
print_status "Device Discovery Setup Complete!"
echo "=================================================="
echo ""
echo "Service Status:"
systemctl status activelog-discovery --no-pager -l
echo ""
print_status "CLI Tool: activelog-discovery"
print_status "API Endpoint: http://localhost:8765/devices"
print_status "Configuration: /etc/activelog/discovery.json"
print_status "Logs: /var/log/activelog/discovery.log"
print_status "Reference: ~/.config/activelog/discovery-reference.md"
echo ""
print_status "To view discovered devices: activelog-discovery list"
print_status "To check logs: activelog-discovery logs"
echo ""

# Show initial device scan
print_status "Initial device scan results (this may take a moment)..."
sleep 5
activelog-discovery list 2>/dev/null || print_warning "API not ready yet - try 'activelog-discovery list' in a few moments"

print_status "Setup completed successfully!"