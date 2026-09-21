#!/bin/bash

# ActiveLog Camera Device Setup Script
# Configures camera devices for intelligent capture and batch upload

set -e

# Configuration
ACTIVELOG_HOME="/opt/activelog"
CAMERA_CONFIG="/etc/activelog/camera.conf"
LOG_FILE="/var/log/activelog/camera-setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Default values
DEVICE_TYPE="usb"
UPLOAD_BATCH_SIZE=10
RESOLUTION="1920x1080"
FPS=30
MOTION_ONLY=false
QUALITY_THRESHOLD=0.3

# Print functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO: $1" >> "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS: $1" >> "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - WARNING: $1" >> "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1" >> "$LOG_FILE"
}

print_camera() {
    echo -e "${PURPLE}[CAMERA]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - CAMERA: $1" >> "$LOG_FILE"
}

# Help function
show_help() {
    cat << EOF
ActiveLog Camera Device Setup Script

Usage: $0 [options]

Options:
    --device TYPE           Camera device type (usb, csi, ip, action)
    --upload-batch SIZE     Number of images per upload batch (default: 10)
    --resolution WxH        Camera resolution (default: 1920x1080)
    --fps RATE             Frame rate (default: 30)
    --motion-only          Only capture when motion is detected
    --quality-threshold N   Minimum quality threshold 0.0-1.0 (default: 0.3)
    --config-only          Only create configuration, don't install
    --test                 Test camera after setup
    --help, -h             Show this help message

Examples:
    $0 --device usb --upload-batch 10
    $0 --device csi --resolution 1280x720 --fps 15 --motion-only
    $0 --device ip --config-only

Supported Device Types:
    usb         USB webcam or capture device
    csi         CSI camera module (Raspberry Pi)
    ip          IP/network camera
    action      Action camera (GoPro, DJI, etc.)

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --device)
                DEVICE_TYPE="$2"
                shift 2
                ;;
            --upload-batch)
                UPLOAD_BATCH_SIZE="$2"
                shift 2
                ;;
            --resolution)
                RESOLUTION="$2"
                shift 2
                ;;
            --fps)
                FPS="$2"
                shift 2
                ;;
            --motion-only)
                MOTION_ONLY=true
                shift
                ;;
            --quality-threshold)
                QUALITY_THRESHOLD="$2"
                shift 2
                ;;
            --config-only)
                CONFIG_ONLY=true
                shift
                ;;
            --test)
                TEST_CAMERA=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Detect available cameras
detect_cameras() {
    print_camera "Detecting available cameras..."
    
    # USB cameras
    USB_CAMERAS=()
    for device in /dev/video*; do
        if [ -c "$device" ]; then
            device_num=${device#/dev/video}
            USB_CAMERAS+=("$device_num")
        fi
    done
    
    if [ ${#USB_CAMERAS[@]} -gt 0 ]; then
        print_camera "Found USB cameras: ${USB_CAMERAS[*]}"
    else
        print_warning "No USB cameras detected"
    fi
    
    # CSI cameras (Raspberry Pi)
    if [ -e /dev/vchiq ]; then
        print_camera "CSI camera interface available"
        CSI_AVAILABLE=true
    else
        CSI_AVAILABLE=false
    fi
    
    # Test camera capabilities
    for camera_id in "${USB_CAMERAS[@]}"; do
        test_camera_capabilities "$camera_id"
    done
}

test_camera_capabilities() {
    local camera_id="$1"
    print_camera "Testing capabilities for camera $camera_id..."
    
    # Use v4l2-ctl if available
    if command -v v4l2-ctl &> /dev/null; then
        print_camera "Camera $camera_id capabilities:"
        v4l2-ctl --device="/dev/video$camera_id" --list-formats-ext 2>/dev/null | head -20 || true
    fi
    
    # Test with OpenCV
    python3 << EOF
import cv2
import sys

camera_id = $camera_id
cap = cv2.VideoCapture(camera_id)

if cap.isOpened():
    # Get current settings
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    print(f"Camera {camera_id}: {width}x{height} @ {fps}fps")
    
    # Test frame capture
    ret, frame = cap.read()
    if ret:
        print(f"Successfully captured test frame: {frame.shape}")
    else:
        print("Failed to capture test frame")
    
    cap.release()
else:
    print(f"Failed to open camera {camera_id}")
    sys.exit(1)
EOF
}

# Install dependencies
install_dependencies() {
    print_status "Installing camera dependencies..."
    
    # Update package list
    apt-get update -y
    
    # Install camera and video processing packages
    apt-get install -y \
        v4l-utils \
        uvcdynctrl \
        guvcview \
        python3-opencv \
        python3-pil \
        python3-numpy \
        python3-requests \
        python3-sqlite3 \
        ffmpeg \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly
    
    # Install Python packages
    pip3 install --upgrade \
        opencv-python \
        pillow \
        numpy \
        requests \
        sqlite3 \
        asyncio \
        aiofiles \
        Pillow
    
    print_success "Dependencies installed"
}

# Configure camera device
configure_camera_device() {
    print_camera "Configuring camera device type: $DEVICE_TYPE"
    
    case $DEVICE_TYPE in
        usb)
            configure_usb_camera
            ;;
        csi)
            configure_csi_camera
            ;;
        ip)
            configure_ip_camera
            ;;
        action)
            configure_action_camera
            ;;
        *)
            print_error "Unsupported device type: $DEVICE_TYPE"
            exit 1
            ;;
    esac
}

configure_usb_camera() {
    print_camera "Configuring USB camera..."
    
    if [ ${#USB_CAMERAS[@]} -eq 0 ]; then
        print_error "No USB cameras detected"
        exit 1
    fi
    
    # Use the first available camera
    CAMERA_ID=${USB_CAMERAS[0]}
    CAMERA_DEVICE="/dev/video$CAMERA_ID"
    
    print_camera "Using USB camera: $CAMERA_DEVICE"
    
    # Set optimal settings for USB camera
    if command -v v4l2-ctl &> /dev/null; then
        # Set resolution and frame rate
        IFS='x' read -r width height <<< "$RESOLUTION"
        v4l2-ctl --device="$CAMERA_DEVICE" --set-fmt-video=width=$width,height=$height || true
        
        # Set frame rate
        v4l2-ctl --device="$CAMERA_DEVICE" --set-parm="$FPS" || true
        
        # Optimize settings
        v4l2-ctl --device="$CAMERA_DEVICE" --set-ctrl=brightness=128 || true
        v4l2-ctl --device="$CAMERA_DEVICE" --set-ctrl=contrast=32 || true
        v4l2-ctl --device="$CAMERA_DEVICE" --set-ctrl=saturation=64 || true
        v4l2-ctl --device="$CAMERA_DEVICE" --set-ctrl=white_balance_temperature_auto=1 || true
        v4l2-ctl --device="$CAMERA_DEVICE" --set-ctrl=exposure_auto=3 || true
        v4l2-ctl --device="$CAMERA_DEVICE" --set-ctrl=focus_auto=1 || true
    fi
}

configure_csi_camera() {
    print_camera "Configuring CSI camera..."
    
    if [ "$CSI_AVAILABLE" != true ]; then
        print_error "CSI camera interface not available"
        exit 1
    fi
    
    # Enable camera in config.txt
    if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
        echo "camera_auto_detect=1" >> /boot/config.txt
        echo "dtoverlay=imx219" >> /boot/config.txt  # Common CSI camera
        print_camera "Enabled CSI camera in boot config"
    fi
    
    # Set camera ID for libcamera
    CAMERA_ID=0
    CAMERA_DEVICE="libcamera"
    
    print_camera "CSI camera configured (reboot may be required)"
}

configure_ip_camera() {
    print_camera "Configuring IP camera..."
    
    # Get IP camera details from user
    read -p "Enter IP camera URL (e.g., rtsp://192.168.1.100:554/stream): " IP_CAMERA_URL
    read -p "Enter username (or press enter for none): " IP_USERNAME
    read -s -p "Enter password (or press enter for none): " IP_PASSWORD
    echo
    
    if [ -n "$IP_USERNAME" ] && [ -n "$IP_PASSWORD" ]; then
        CAMERA_DEVICE="$IP_CAMERA_URL"
        # Store credentials securely
        mkdir -p /etc/activelog/credentials
        cat > /etc/activelog/credentials/ip_camera.json << EOF
{
    "url": "$IP_CAMERA_URL",
    "username": "$IP_USERNAME",
    "password": "$IP_PASSWORD"
}
EOF
        chmod 600 /etc/activelog/credentials/ip_camera.json
    else
        CAMERA_DEVICE="$IP_CAMERA_URL"
    fi
    
    CAMERA_ID="$CAMERA_DEVICE"
    print_camera "IP camera configured: $IP_CAMERA_URL"
}

configure_action_camera() {
    print_camera "Configuring action camera..."
    
    echo "Action camera setup options:"
    echo "1. GoPro via WiFi"
    echo "2. DJI camera via USB"
    echo "3. Generic action camera via USB"
    
    read -p "Select option (1-3): " ACTION_TYPE
    
    case $ACTION_TYPE in
        1)
            configure_gopro_wifi
            ;;
        2)
            configure_dji_usb
            ;;
        3)
            configure_generic_action
            ;;
        *)
            print_error "Invalid action camera type"
            exit 1
            ;;
    esac
}

configure_gopro_wifi() {
    print_camera "Configuring GoPro WiFi connection..."
    
    read -p "Enter GoPro WiFi SSID: " GOPRO_SSID
    read -s -p "Enter GoPro WiFi password: " GOPRO_PASS
    echo
    
    # Configure WiFi connection for GoPro
    cat >> /etc/wpa_supplicant/wpa_supplicant.conf << EOF

# GoPro Camera WiFi
network={
    ssid="$GOPRO_SSID"
    psk="$GOPRO_PASS"
    priority=1
}
EOF

    CAMERA_ID="gopro_wifi"
    CAMERA_DEVICE="http://10.5.5.9:8080/live/amba.m3u8"  # Default GoPro streaming URL
    print_camera "GoPro WiFi configured"
}

configure_dji_usb() {
    print_camera "Configuring DJI camera via USB..."
    
    # DJI cameras often appear as USB storage + video device
    CAMERA_ID="dji_usb"
    CAMERA_DEVICE="/dev/video0"  # Will be detected during camera detection
    
    print_camera "DJI USB camera configured"
}

configure_generic_action() {
    print_camera "Configuring generic action camera..."
    
    # Most action cameras appear as standard USB video devices
    configure_usb_camera
    print_camera "Generic action camera configured as USB device"
}

# Create camera configuration file
create_camera_config() {
    print_status "Creating camera configuration..."
    
    mkdir -p "$(dirname "$CAMERA_CONFIG")"
    
    # Parse resolution
    IFS='x' read -r width height <<< "$RESOLUTION"
    
    cat > "$CAMERA_CONFIG" << EOF
{
    "device": {
        "id": "camera_$(hostname)_$(date +%s)",
        "name": "ActiveLog Camera - $(hostname)",
        "type": "$DEVICE_TYPE",
        "location": "$(hostname)"
    },
    "camera": {
        "device_id": "$CAMERA_ID",
        "device_path": "$CAMERA_DEVICE",
        "resolution": [$width, $height],
        "fps": $FPS,
        "format": "MJPG",
        "auto_exposure": true,
        "brightness": 0.5,
        "contrast": 0.5,
        "saturation": 0.5,
        "enable_auto_focus": true,
        "enable_stabilization": true
    },
    "capture": {
        "motion_only": $MOTION_ONLY,
        "min_quality": $QUALITY_THRESHOLD,
        "interval": 1.0,
        "enable_thumbnails": true,
        "max_file_size": 1048576,
        "save_raw": false
    },
    "processing": {
        "enable_motion_detection": true,
        "motion_sensitivity": 0.1,
        "motion_min_area": 500,
        "enable_quality_analysis": true,
        "enable_face_detection": false,
        "enable_object_detection": false,
        "enable_compression": true
    },
    "upload": {
        "batch_size": $UPLOAD_BATCH_SIZE,
        "max_batch_age": 300,
        "compression_quality": 85,
        "enable_deduplication": true,
        "max_file_size": 1048576,
        "server_url": "https://api.activelog.ai",
        "upload_timeout": 60,
        "retry_attempts": 3,
        "retry_delay": 5
    },
    "storage": {
        "data_dir": "/var/lib/activelog/camera",
        "max_storage_gb": 10,
        "cleanup_days": 30,
        "enable_local_backup": true,
        "backup_location": "/var/backups/activelog/camera"
    },
    "security": {
        "enable_encryption": true,
        "encrypt_uploads": true,
        "enable_authentication": true,
        "certificate_path": "/etc/activelog/device.crt",
        "private_key_path": "/etc/activelog/device.key"
    },
    "monitoring": {
        "enable_health_checks": true,
        "health_check_interval": 300,
        "enable_performance_monitoring": true,
        "log_level": "INFO",
        "enable_statistics": true,
        "statistics_interval": 300
    },
    "power": {
        "enable_power_management": true,
        "sleep_mode_enabled": false,
        "low_power_threshold": 20,
        "enable_thermal_throttling": true,
        "thermal_threshold": 70
    }
}
EOF

    chmod 640 "$CAMERA_CONFIG"
    
    print_success "Camera configuration created: $CAMERA_CONFIG"
}

# Create systemd service
create_camera_service() {
    print_status "Creating camera service..."
    
    cat > /etc/systemd/system/activelog-camera.service << 'EOF'
[Unit]
Description=ActiveLog Camera Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=activelog
Group=activelog
WorkingDirectory=/opt/activelog
ExecStart=/usr/bin/python3 /opt/activelog/bin/camera-agent.py --config /etc/activelog/camera.conf
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Camera access
SupplementaryGroups=video

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/activelog /var/log/activelog /var/lib/activelog /etc/activelog

[Install]
WantedBy=multi-user.target
EOF

    # Copy camera agent
    cp "$(dirname "$0")/camera-agent.py" "$ACTIVELOG_HOME/bin/"
    chmod +x "$ACTIVELOG_HOME/bin/camera-agent.py"
    
    # Create symlink
    ln -sf "$ACTIVELOG_HOME/bin/camera-agent.py" /usr/local/bin/activelog-camera
    
    systemctl daemon-reload
    systemctl enable activelog-camera.service
    
    print_success "Camera service created and enabled"
}

# Create storage directories
create_storage_directories() {
    print_status "Creating storage directories..."
    
    mkdir -p /var/lib/activelog/camera/{images,thumbnails,processed,uploads}
    mkdir -p /var/log/activelog
    mkdir -p /var/backups/activelog/camera
    
    # Set ownership
    chown -R activelog:activelog /var/lib/activelog/camera 2>/dev/null || true
    chown -R activelog:activelog /var/log/activelog 2>/dev/null || true
    chown -R activelog:activelog /var/backups/activelog/camera 2>/dev/null || true
    
    print_success "Storage directories created"
}

# Test camera functionality
test_camera_functionality() {
    print_camera "Testing camera functionality..."
    
    # Create test script
    cat > /tmp/camera_test.py << 'EOF'
#!/usr/bin/env python3
import cv2
import sys
import json
import time
from pathlib import Path

def test_camera(config_path):
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    camera_config = config.get('camera', {})
    device_id = camera_config.get('device_id', 0)
    
    print(f"Testing camera device: {device_id}")
    
    # Initialize camera
    cap = cv2.VideoCapture(device_id)
    
    if not cap.isOpened():
        print(f"ERROR: Failed to open camera {device_id}")
        return False
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    print(f"Camera properties: {width}x{height} @ {fps}fps")
    
    # Capture test frames
    success_count = 0
    for i in range(10):
        ret, frame = cap.read()
        if ret:
            success_count += 1
            print(f"Frame {i+1}: {frame.shape} - OK")
        else:
            print(f"Frame {i+1}: FAILED")
        time.sleep(0.1)
    
    cap.release()
    
    print(f"Test completed: {success_count}/10 frames captured successfully")
    return success_count >= 8

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/activelog/camera.conf"
    success = test_camera(config_path)
    sys.exit(0 if success else 1)
EOF

    python3 /tmp/camera_test.py "$CAMERA_CONFIG"
    test_result=$?
    
    rm -f /tmp/camera_test.py
    
    if [ $test_result -eq 0 ]; then
        print_success "Camera test passed"
    else
        print_error "Camera test failed"
        return 1
    fi
}

# Create monitoring script
create_monitoring_script() {
    print_status "Creating monitoring script..."
    
    cat > "$ACTIVELOG_HOME/scripts/camera-monitor.sh" << 'EOF'
#!/bin/bash

# ActiveLog Camera Monitoring Script

CAMERA_CONFIG="/etc/activelog/camera.conf"
LOG_FILE="/var/log/activelog/camera-monitor.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_camera_service() {
    if systemctl is-active --quiet activelog-camera; then
        log_message "Camera service is running"
        return 0
    else
        log_message "Camera service is NOT running"
        return 1
    fi
}

check_camera_device() {
    if [ -f "$CAMERA_CONFIG" ]; then
        device_id=$(python3 -c "
import json
with open('$CAMERA_CONFIG', 'r') as f:
    config = json.load(f)
print(config.get('camera', {}).get('device_id', 0))
")
        
        if [ -c "/dev/video$device_id" ]; then
            log_message "Camera device /dev/video$device_id is available"
            return 0
        else
            log_message "Camera device /dev/video$device_id is NOT available"
            return 1
        fi
    else
        log_message "Camera configuration file not found"
        return 1
    fi
}

check_storage_space() {
    storage_dir="/var/lib/activelog/camera"
    if [ -d "$storage_dir" ]; then
        usage=$(df "$storage_dir" | awk 'NR==2 {print $5}' | sed 's/%//')
        log_message "Camera storage usage: $usage%"
        
        if [ "$usage" -gt 90 ]; then
            log_message "WARNING: Camera storage usage is high"
            return 1
        fi
    else
        log_message "Camera storage directory not found"
        return 1
    fi
    
    return 0
}

restart_camera_service() {
    log_message "Restarting camera service..."
    systemctl restart activelog-camera
    sleep 5
    
    if systemctl is-active --quiet activelog-camera; then
        log_message "Camera service restarted successfully"
        return 0
    else
        log_message "Failed to restart camera service"
        return 1
    fi
}

main() {
    log_message "Starting camera monitoring check..."
    
    issues=0
    
    # Check service
    if ! check_camera_service; then
        ((issues++))
        restart_camera_service
    fi
    
    # Check device
    if ! check_camera_device; then
        ((issues++))
    fi
    
    # Check storage
    if ! check_storage_space; then
        ((issues++))
    fi
    
    if [ $issues -eq 0 ]; then
        log_message "All camera checks passed"
    else
        log_message "Camera monitoring found $issues issue(s)"
    fi
    
    log_message "Camera monitoring check completed"
}

main "$@"
EOF

    chmod +x "$ACTIVELOG_HOME/scripts/camera-monitor.sh"
    
    # Add to crontab for periodic monitoring
    (crontab -l 2>/dev/null; echo "*/10 * * * * /opt/activelog/scripts/camera-monitor.sh") | crontab -
    
    print_success "Camera monitoring script created"
}

# Main setup function
main() {
    print_status "Starting ActiveLog Camera Device Setup"
    
    # Parse arguments
    parse_arguments "$@"
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Check if running as root for system modifications
    if [[ $EUID -ne 0 ]] && [[ "$CONFIG_ONLY" != true ]]; then
        print_error "This script must be run as root for system setup (use sudo)"
        print_status "Use --config-only to create configuration without system changes"
        exit 1
    fi
    
    # Detect available cameras
    detect_cameras
    
    # Install dependencies (unless config-only)
    if [[ "$CONFIG_ONLY" != true ]]; then
        install_dependencies
    fi
    
    # Configure camera device
    configure_camera_device
    
    # Create configuration
    create_camera_config
    
    # Setup system components (unless config-only)
    if [[ "$CONFIG_ONLY" != true ]]; then
        create_storage_directories
        create_camera_service
        create_monitoring_script
    fi
    
    # Test camera if requested
    if [[ "$TEST_CAMERA" == true ]]; then
        test_camera_functionality
    fi
    
    print_success "ActiveLog Camera Device setup completed!"
    
    if [[ "$CONFIG_ONLY" != true ]]; then
        print_status "Next steps:"
        print_status "1. Start the camera service: sudo systemctl start activelog-camera"
        print_status "2. Check service status: sudo systemctl status activelog-camera"
        print_status "3. View logs: journalctl -u activelog-camera -f"
        print_status "4. Monitor camera: /opt/activelog/scripts/camera-monitor.sh"
    else
        print_status "Configuration created. Run without --config-only to complete system setup."
    fi
    
    print_status "Configuration file: $CAMERA_CONFIG"
    print_status "Log file: $LOG_FILE"
}

# Run main function
main "$@"