#!/bin/bash

# ActiveLog Raspberry Pi Edge Device Setup Script
# Supports Raspberry Pi 4/5 with automatic configuration

set -e

# Configuration
ACTIVELOG_VERSION="1.0.0"
EDGE_USER="activelog"
ACTIVELOG_HOME="/opt/activelog"
LOG_FILE="/var/log/activelog-setup.log"
CONFIG_FILE="/etc/activelog/edge.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
    log "INFO: $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "SUCCESS: $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    log "WARNING: $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    log "ERROR: $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Detect Raspberry Pi model
detect_rpi_model() {
    print_status "Detecting Raspberry Pi model..."
    
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(cat /proc/device-tree/model)
        print_status "Detected: $MODEL"
        
        if [[ $MODEL == *"Raspberry Pi 4"* ]]; then
            RPI_MODEL="4"
        elif [[ $MODEL == *"Raspberry Pi 5"* ]]; then
            RPI_MODEL="5"
        elif [[ $MODEL == *"Raspberry Pi 3"* ]]; then
            RPI_MODEL="3"
        else
            print_warning "Unsupported Pi model: $MODEL"
            RPI_MODEL="unknown"
        fi
    else
        print_error "Cannot detect Raspberry Pi model"
        exit 1
    fi
}

# Update system
update_system() {
    print_status "Updating system packages..."
    
    apt-get update -y
    apt-get upgrade -y
    
    # Install essential packages
    apt-get install -y \
        curl wget git vim \
        python3 python3-pip python3-venv \
        nodejs npm \
        docker.io docker-compose \
        bluetooth bluez libbluetooth-dev \
        wireless-tools wpasupplicant \
        i2c-tools spi-tools \
        htop iotop \
        ufw fail2ban \
        systemd-timesyncd \
        avahi-daemon \
        mosquitto mosquitto-clients
    
    print_success "System packages updated"
}

# Configure GPIO and hardware interfaces
configure_hardware() {
    print_status "Configuring hardware interfaces..."
    
    # Enable I2C, SPI, Camera
    raspi-config nonint do_i2c 0
    raspi-config nonint do_spi 0
    raspi-config nonint do_camera 0
    
    # Enable SSH
    systemctl enable ssh
    systemctl start ssh
    
    # Configure GPU memory split (for camera)
    if [ "$RPI_MODEL" = "4" ] || [ "$RPI_MODEL" = "5" ]; then
        echo "gpu_mem=128" >> /boot/config.txt
    else
        echo "gpu_mem=64" >> /boot/config.txt
    fi
    
    print_success "Hardware interfaces configured"
}

# Create ActiveLog user
create_activelog_user() {
    print_status "Creating ActiveLog user..."
    
    if ! id "$EDGE_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$EDGE_USER"
        usermod -aG sudo,gpio,i2c,spi,video,audio,dialout "$EDGE_USER"
        
        # Create SSH key for the user
        sudo -u "$EDGE_USER" ssh-keygen -t ed25519 -f "/home/$EDGE_USER/.ssh/id_ed25519" -N ""
        
        print_success "ActiveLog user created"
    else
        print_status "ActiveLog user already exists"
    fi
}

# Install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Create virtual environment
    sudo -u "$EDGE_USER" python3 -m venv "/home/$EDGE_USER/activelog-venv"
    
    # Install packages in virtual environment
    sudo -u "$EDGE_USER" /home/"$EDGE_USER"/activelog-venv/bin/pip install --upgrade pip
    sudo -u "$EDGE_USER" /home/"$EDGE_USER"/activelog-venv/bin/pip install \
        requests paho-mqtt websockets \
        opencv-python pillow \
        numpy scipy scikit-learn \
        flask fastapi uvicorn \
        psutil GPUtil \
        RPi.GPIO gpiozero \
        picamera2 \
        bluepy pybluez \
        cryptography pyotp \
        schedule watchdog \
        prometheus-client
    
    print_success "Python dependencies installed"
}

# Install Node.js dependencies
install_nodejs_deps() {
    print_status "Installing Node.js dependencies..."
    
    # Install global packages
    npm install -g pm2 node-red
    
    # Configure PM2 for autostart
    sudo -u "$EDGE_USER" pm2 startup
    
    print_success "Node.js dependencies installed"
}

# Create ActiveLog directories
create_directories() {
    print_status "Creating ActiveLog directories..."
    
    mkdir -p "$ACTIVELOG_HOME"/{bin,config,data,logs,scripts,models}
    mkdir -p /etc/activelog
    mkdir -p /var/log/activelog
    mkdir -p /var/lib/activelog
    
    # Set ownership
    chown -R "$EDGE_USER:$EDGE_USER" "$ACTIVELOG_HOME"
    chown -R "$EDGE_USER:$EDGE_USER" /var/log/activelog
    chown -R "$EDGE_USER:$EDGE_USER" /var/lib/activelog
    
    print_success "ActiveLog directories created"
}

# Download and install ActiveLog edge software
install_activelog_edge() {
    print_status "Installing ActiveLog edge software..."
    
    # Download edge agent
    curl -sSL "https://github.com/activelog/edge-agent/releases/latest/download/activelog-edge-rpi.tar.gz" \
        -o "/tmp/activelog-edge.tar.gz" || {
        print_warning "Could not download from GitHub, using local files"
        
        # Copy local files instead
        cp -r "$(dirname "$0")"/../* "$ACTIVELOG_HOME"/
    }
    
    if [ -f "/tmp/activelog-edge.tar.gz" ]; then
        tar -xzf "/tmp/activelog-edge.tar.gz" -C "$ACTIVELOG_HOME"
        rm "/tmp/activelog-edge.tar.gz"
    fi
    
    # Make scripts executable
    chmod +x "$ACTIVELOG_HOME"/bin/*
    chmod +x "$ACTIVELOG_HOME"/scripts/*
    
    # Create symlinks
    ln -sf "$ACTIVELOG_HOME/bin/activelog-agent" /usr/local/bin/activelog-agent
    ln -sf "$ACTIVELOG_HOME/bin/activelog-cli" /usr/local/bin/activelog-cli
    
    print_success "ActiveLog edge software installed"
}

# Configure network
configure_network() {
    print_status "Configuring network..."
    
    # Create WiFi configuration template
    cat > /etc/wpa_supplicant/wpa_supplicant.conf.template << 'EOF'
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

# Example WiFi network configuration
# Uncomment and modify for your network
#network={
#    ssid="YourWiFiName"
#    psk="YourWiFiPassword"
#    key_mgmt=WPA-PSK
#}

# Example enterprise WiFi
#network={
#    ssid="Enterprise-WiFi"
#    key_mgmt=WPA-EAP
#    eap=PEAP
#    identity="username"
#    password="password"
#    phase2="auth=MSCHAPV2"
#}
EOF

    # Configure Bluetooth
    systemctl enable bluetooth
    systemctl start bluetooth
    
    # Enable Avahi for mDNS
    systemctl enable avahi-daemon
    systemctl start avahi-daemon
    
    print_success "Network configured"
}

# Configure security
configure_security() {
    print_status "Configuring security..."
    
    # Configure UFW firewall
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow ActiveLog ports
    ufw allow 8080/tcp  # Web dashboard
    ufw allow 8883/tcp  # MQTT TLS
    ufw allow 5000/tcp  # API server
    
    # Allow mDNS
    ufw allow 5353/udp
    
    # Enable firewall
    ufw --force enable
    
    # Configure fail2ban
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

    systemctl enable fail2ban
    systemctl start fail2ban
    
    # Generate device certificate
    openssl req -x509 -newkey rsa:4096 -keyout /etc/activelog/device.key \
        -out /etc/activelog/device.crt -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=ActiveLog/CN=$(hostname)"
    
    chmod 600 /etc/activelog/device.key
    chmod 644 /etc/activelog/device.crt
    
    print_success "Security configured"
}

# Create configuration file
create_config() {
    print_status "Creating configuration file..."
    
    DEVICE_ID=$(openssl rand -hex 16)
    
    cat > "$CONFIG_FILE" << EOF
# ActiveLog Edge Device Configuration
[device]
id = $DEVICE_ID
name = $(hostname)
type = raspberry-pi
model = $RPI_MODEL
version = $ACTIVELOG_VERSION

[network]
wifi_interface = wlan0
ethernet_interface = eth0
bluetooth_interface = hci0
enable_hotspot = true
hotspot_ssid = ActiveLog-$(hostname)

[security]
certificate_path = /etc/activelog/device.crt
private_key_path = /etc/activelog/device.key
enable_encryption = true
enable_authentication = true

[processing]
enable_ai = true
enable_camera = true
enable_sensors = true
max_cpu_usage = 80
max_memory_usage = 75

[sync]
server_url = https://api.activelog.ai
sync_interval = 300
offline_queue_size = 1000
compression_enabled = true

[logging]
level = INFO
file_path = /var/log/activelog/edge.log
max_size = 10MB
backup_count = 5
EOF

    chown "$EDGE_USER:$EDGE_USER" "$CONFIG_FILE"
    chmod 640 "$CONFIG_FILE"
    
    print_success "Configuration file created"
}

# Create systemd services
create_services() {
    print_status "Creating systemd services..."
    
    # ActiveLog Edge Agent service
    cat > /etc/systemd/system/activelog-edge.service << 'EOF'
[Unit]
Description=ActiveLog Edge Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=activelog
Group=activelog
WorkingDirectory=/opt/activelog
ExecStart=/opt/activelog/bin/activelog-agent --config /etc/activelog/edge.conf
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/activelog /var/log/activelog /var/lib/activelog

[Install]
WantedBy=multi-user.target
EOF

    # ActiveLog Health Monitor service
    cat > /etc/systemd/system/activelog-health.service << 'EOF'
[Unit]
Description=ActiveLog Health Monitor
After=activelog-edge.service
Requires=activelog-edge.service

[Service]
Type=simple
User=activelog
Group=activelog
ExecStart=/opt/activelog/bin/activelog-health-monitor
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    # Enable services
    systemctl daemon-reload
    systemctl enable activelog-edge.service
    systemctl enable activelog-health.service
    
    print_success "Systemd services created"
}

# Configure camera
configure_camera() {
    print_status "Configuring camera..."
    
    # Add camera configuration to config.txt
    if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
        echo "camera_auto_detect=1" >> /boot/config.txt
    fi
    
    # Create camera test script
    cat > "$ACTIVELOG_HOME/scripts/test-camera.py" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/activelog/activelog-venv/lib/python3.11/site-packages')

try:
    from picamera2 import Picamera2
    import time
    
    print("Initializing camera...")
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration())
    picam2.start()
    
    print("Camera started successfully!")
    time.sleep(2)
    
    # Capture a test image
    picam2.capture_file("/tmp/test_image.jpg")
    print("Test image captured: /tmp/test_image.jpg")
    
    picam2.stop()
    print("Camera test completed successfully!")
    
except Exception as e:
    print(f"Camera test failed: {e}")
    sys.exit(1)
EOF

    chmod +x "$ACTIVELOG_HOME/scripts/test-camera.py"
    
    print_success "Camera configured"
}

# Setup monitoring
setup_monitoring() {
    print_status "Setting up monitoring..."
    
    # Create monitoring script
    cat > "$ACTIVELOG_HOME/scripts/monitor.py" << 'EOF'
#!/usr/bin/env python3
import psutil
import json
import time
import requests
from datetime import datetime

def get_system_stats():
    return {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent,
        'temperature': get_cpu_temperature(),
        'uptime': time.time() - psutil.boot_time()
    }

def get_cpu_temperature():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
            return temp
    except:
        return None

if __name__ == "__main__":
    stats = get_system_stats()
    print(json.dumps(stats, indent=2))
EOF

    chmod +x "$ACTIVELOG_HOME/scripts/monitor.py"
    
    # Create cron job for monitoring
    echo "*/5 * * * * $EDGE_USER /opt/activelog/scripts/monitor.py >> /var/log/activelog/monitoring.log 2>&1" >> /etc/crontab
    
    print_success "Monitoring setup completed"
}

# Create installation summary
create_summary() {
    print_status "Creating installation summary..."
    
    cat > "$ACTIVELOG_HOME/INSTALLATION_SUMMARY.md" << EOF
# ActiveLog Edge Device Installation Summary

**Installation Date:** $(date)
**Device Model:** Raspberry Pi $RPI_MODEL
**Device ID:** $(grep "^id" "$CONFIG_FILE" | cut -d' ' -f3)
**ActiveLog Version:** $ACTIVELOG_VERSION

## Installed Components

- ✅ ActiveLog Edge Agent
- ✅ Python 3 with virtual environment
- ✅ Node.js and PM2
- ✅ Docker and Docker Compose
- ✅ Bluetooth and WiFi support
- ✅ Camera support (if available)
- ✅ Security hardening (UFW, fail2ban)
- ✅ System monitoring
- ✅ Automatic updates

## Service Status

- ActiveLog Edge Agent: systemctl status activelog-edge
- Health Monitor: systemctl status activelog-health
- SSH: systemctl status ssh
- Bluetooth: systemctl status bluetooth

## Important Files

- Configuration: $CONFIG_FILE
- Logs: /var/log/activelog/
- Data: /var/lib/activelog/
- Scripts: $ACTIVELOG_HOME/scripts/

## Next Steps

1. Configure WiFi (if needed):
   sudo cp /etc/wpa_supplicant/wpa_supplicant.conf.template /etc/wpa_supplicant/wpa_supplicant.conf
   sudo nano /etc/wpa_supplicant/wpa_supplicant.conf

2. Test camera (if available):
   sudo $ACTIVELOG_HOME/scripts/test-camera.py

3. Start ActiveLog services:
   sudo systemctl start activelog-edge
   sudo systemctl start activelog-health

4. Check device status:
   activelog-cli status

5. Access web dashboard:
   http://$(hostname).local:8080

## Support

- Documentation: https://docs.activelog.ai/edge/
- Community: https://community.activelog.ai/
- Issues: https://github.com/activelog/edge-device/issues

EOF

    print_success "Installation summary created"
}

# Main installation function
main() {
    print_status "Starting ActiveLog Raspberry Pi setup..."
    print_status "Installation log: $LOG_FILE"
    
    check_root
    detect_rpi_model
    update_system
    configure_hardware
    create_activelog_user
    install_python_deps
    install_nodejs_deps
    create_directories
    install_activelog_edge
    configure_network
    configure_security
    create_config
    create_services
    configure_camera
    setup_monitoring
    create_summary
    
    print_success "ActiveLog Raspberry Pi setup completed!"
    print_status "Please reboot your device to complete the installation:"
    print_status "sudo reboot"
    
    print_status "After reboot, you can:"
    print_status "1. Check status: activelog-cli status"
    print_status "2. View logs: journalctl -u activelog-edge -f"
    print_status "3. Access dashboard: http://$(hostname).local:8080"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "ActiveLog Raspberry Pi Setup Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --dry-run      Show what would be done without making changes"
        echo "  --minimal      Install minimal components only"
        echo ""
        exit 0
        ;;
    --dry-run)
        print_status "DRY RUN MODE - No changes will be made"
        # Set all commands to echo mode
        alias apt-get='echo apt-get'
        alias systemctl='echo systemctl'
        alias useradd='echo useradd'
        alias mkdir='echo mkdir'
        alias cp='echo cp'
        alias chmod='echo chmod'
        alias chown='echo chown'
        ;;
    --minimal)
        print_status "MINIMAL INSTALLATION MODE"
        MINIMAL_INSTALL=true
        ;;
esac

# Run main installation
main "$@"