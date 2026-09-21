#!/bin/bash

# ActiveLog Jetson Nano Edge AI Setup Script
# Optimized for AI inference at the edge with CUDA acceleration

set -e

# Configuration
ACTIVELOG_VERSION="1.0.0"
EDGE_USER="activelog"
ACTIVELOG_HOME="/opt/activelog"
LOG_FILE="/var/log/activelog-setup.log"
CONFIG_FILE="/etc/activelog/edge.conf"
JETPACK_VERSION=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_ai() {
    echo -e "${PURPLE}[AI]${NC} $1"
    log "AI: $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Detect Jetson model and JetPack version
detect_jetson() {
    print_status "Detecting Jetson model and JetPack version..."
    
    if [ -f /etc/nv_tegra_release ]; then
        JETPACK_VERSION=$(head -n 1 /etc/nv_tegra_release | cut -d' ' -f2 | cut -d',' -f1)
        print_status "JetPack version: $JETPACK_VERSION"
    fi
    
    # Detect specific Jetson model
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(cat /proc/device-tree/model)
        print_status "Detected: $MODEL"
        
        if [[ $MODEL == *"Jetson Nano"* ]]; then
            JETSON_MODEL="nano"
            GPU_MEMORY=128
            MAX_FREQ=1479000000
        elif [[ $MODEL == *"Jetson Xavier NX"* ]]; then
            JETSON_MODEL="xavier-nx"
            GPU_MEMORY=256
            MAX_FREQ=1377000000
        elif [[ $MODEL == *"Jetson AGX Xavier"* ]]; then
            JETSON_MODEL="agx-xavier"
            GPU_MEMORY=512
            MAX_FREQ=1377000000
        elif [[ $MODEL == *"Jetson Orin"* ]]; then
            JETSON_MODEL="orin"
            GPU_MEMORY=1024
            MAX_FREQ=2201600000
        else
            print_warning "Unknown Jetson model: $MODEL"
            JETSON_MODEL="unknown"
            GPU_MEMORY=128
            MAX_FREQ=1000000000
        fi
    else
        print_error "Cannot detect Jetson model"
        exit 1
    fi
    
    print_status "Jetson model: $JETSON_MODEL"
    print_status "GPU memory allocation: ${GPU_MEMORY}MB"
}

# Configure power management and performance
configure_power_performance() {
    print_status "Configuring power management and performance..."
    
    # Set maximum performance mode
    if command -v nvpmodel &> /dev/null; then
        nvpmodel -m 0  # Maximum performance mode
        print_status "Set to maximum performance mode"
    fi
    
    # Enable all CPU cores and set maximum frequency
    if command -v jetson_clocks &> /dev/null; then
        jetson_clocks
        print_status "Enabled jetson_clocks for maximum performance"
    fi
    
    # Configure CPU governor
    echo "performance" > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    
    # Set GPU frequency
    if [ -f /sys/kernel/debug/bpmp/debug/clk/gpu/rate ]; then
        echo $MAX_FREQ > /sys/kernel/debug/bpmp/debug/clk/gpu/rate
    fi
    
    print_success "Power and performance configured"
}

# Update system and install dependencies
update_system() {
    print_status "Updating system packages..."
    
    apt-get update -y
    apt-get upgrade -y
    
    # Install essential packages
    apt-get install -y \
        curl wget git vim htop \
        python3 python3-pip python3-dev python3-venv \
        build-essential cmake pkg-config \
        libjpeg-dev libtiff5-dev libjasper-dev libpng-dev \
        libavcodec-dev libavformat-dev libswscale-dev libv4l-dev \
        libxvidcore-dev libx264-dev \
        libgtk-3-dev \
        libatlas-base-dev gfortran \
        libhdf5-serial-dev \
        libprotobuf-dev protobuf-compiler \
        libgoogle-glog-dev libgflags-dev \
        libgphoto2-dev libeigen3-dev libhdf5-dev doxygen \
        nodejs npm \
        docker.io docker-compose \
        bluetooth bluez libbluetooth-dev \
        wireless-tools wpasupplicant \
        i2c-tools \
        ufw fail2ban \
        systemd-timesyncd \
        avahi-daemon \
        mosquitto mosquitto-clients \
        libssl-dev libffi-dev \
        libopenblas-dev \
        liblapack-dev \
        gstreamer1.0-tools gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly
    
    print_success "System packages updated"
}

# Install CUDA tools and libraries
install_cuda_tools() {
    print_ai "Installing CUDA development tools..."
    
    # Install CUDA samples (if not already installed)
    if [ ! -d "/usr/local/cuda/samples" ]; then
        print_status "CUDA samples not found, installing..."
        apt-get install -y cuda-samples-11-4 || apt-get install -y cuda-samples-10-2
    fi
    
    # Install additional CUDA libraries
    apt-get install -y \
        cuda-toolkit-11-4 \
        libcudnn8 \
        libcudnn8-dev \
        libnvidia-container-tools \
        nvidia-container-runtime || {
        print_warning "Some CUDA packages may not be available for this JetPack version"
    }
    
    # Set CUDA environment variables
    cat > /etc/environment << 'EOF'
CUDA_HOME=/usr/local/cuda
CUDA_ROOT=/usr/local/cuda
PATH=/usr/local/cuda/bin:$PATH
LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
EOF

    # Add to current session
    export CUDA_HOME=/usr/local/cuda
    export CUDA_ROOT=/usr/local/cuda
    export PATH=/usr/local/cuda/bin:$PATH
    export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
    
    print_success "CUDA tools installed"
}

# Install TensorRT
install_tensorrt() {
    print_ai "Installing TensorRT..."
    
    # TensorRT should be pre-installed with JetPack, but ensure python bindings
    apt-get install -y \
        python3-libnvinfer \
        python3-libnvinfer-dev \
        tensorrt || {
        print_warning "TensorRT packages may not be available"
    }
    
    print_success "TensorRT installation completed"
}

# Create ActiveLog user with GPU access
create_activelog_user() {
    print_status "Creating ActiveLog user with GPU access..."
    
    if ! id "$EDGE_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$EDGE_USER"
        usermod -aG sudo,video,i2c,dialout,gpio "$EDGE_USER"
        
        # Add to docker group for containerized AI models
        usermod -aG docker "$EDGE_USER"
        
        # Create SSH key for the user
        sudo -u "$EDGE_USER" ssh-keygen -t ed25519 -f "/home/$EDGE_USER/.ssh/id_ed25519" -N ""
        
        print_success "ActiveLog user created with GPU access"
    else
        print_status "ActiveLog user already exists"
    fi
}

# Install Python AI/ML libraries
install_python_ai_deps() {
    print_ai "Installing Python AI/ML dependencies..."
    
    # Create virtual environment
    sudo -u "$EDGE_USER" python3 -m venv "/home/$EDGE_USER/activelog-ai-venv"
    VENV_PATH="/home/$EDGE_USER/activelog-ai-venv"
    
    # Upgrade pip
    sudo -u "$EDGE_USER" $VENV_PATH/bin/pip install --upgrade pip
    
    # Install PyTorch for Jetson (CUDA-enabled)
    print_ai "Installing PyTorch for Jetson..."
    if [ "$JETSON_MODEL" = "nano" ]; then
        # PyTorch 1.10.0 for Jetson Nano
        sudo -u "$EDGE_USER" $VENV_PATH/bin/pip install \
            https://nvidia.box.com/shared/static/fjtbno0vpo676a25cgvuqc1wty0fkkg6.whl
    else
        # For newer Jetson models
        sudo -u "$EDGE_USER" $VENV_PATH/bin/pip install torch torchvision torchaudio \
            --extra-index-url https://download.pytorch.org/whl/cu116
    fi
    
    # Install TensorFlow for Jetson
    print_ai "Installing TensorFlow for Jetson..."
    sudo -u "$EDGE_USER" $VENV_PATH/bin/pip install \
        https://developer.download.nvidia.com/compute/redist/jp/v50/tensorflow/tensorflow-2.11.0+nv23.01-cp38-cp38-linux_aarch64.whl || \
        sudo -u "$EDGE_USER" $VENV_PATH/bin/pip install tensorflow
    
    # Install other AI/ML libraries
    sudo -u "$EDGE_USER" $VENV_PATH/bin/pip install \
        numpy opencv-python pillow \
        scikit-learn scipy \
        onnx onnxruntime-gpu \
        tensorrt \
        pycuda \
        numba \
        cupy-cuda11x \
        transformers \
        ultralytics \
        detectron2 \
        tritonclient[all] \
        jetson-stats \
        jetson-inference \
        jetson-utils
    
    # Install ActiveLog specific packages
    sudo -u "$EDGE_USER" $VENV_PATH/bin/pip install \
        requests paho-mqtt websockets \
        flask fastapi uvicorn \
        psutil GPUtil \
        Jetson.GPIO \
        cryptography pyotp \
        schedule watchdog \
        prometheus-client \
        asyncio aiofiles \
        sqlalchemy databases \
        redis \
        minio
    
    print_success "Python AI/ML dependencies installed"
}

# Install Docker containers for AI models
install_ai_containers() {
    print_ai "Setting up AI inference containers..."
    
    # Enable Docker for GPU access
    if [ ! -f /etc/docker/daemon.json ]; then
        mkdir -p /etc/docker
        cat > /etc/docker/daemon.json << 'EOF'
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}
EOF
        systemctl restart docker
    fi
    
    # Pull useful AI containers
    docker pull nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3 || true
    docker pull nvcr.io/nvidia/l4t-tensorflow:r35.2.1-tf2.11-py3 || true
    docker pull nvcr.io/nvidia/tritonserver:23.04-py3 || true
    
    print_success "AI containers set up"
}

# Create directories and install ActiveLog AI edge software
install_activelog_ai_edge() {
    print_ai "Installing ActiveLog AI Edge software..."
    
    # Create directories
    mkdir -p "$ACTIVELOG_HOME"/{bin,config,data,logs,scripts,models,ai-cache}
    mkdir -p /etc/activelog
    mkdir -p /var/log/activelog
    mkdir -p /var/lib/activelog/{models,cache,data}
    
    # Set ownership
    chown -R "$EDGE_USER:$EDGE_USER" "$ACTIVELOG_HOME"
    chown -R "$EDGE_USER:$EDGE_USER" /var/log/activelog
    chown -R "$EDGE_USER:$EDGE_USER" /var/lib/activelog
    
    # Copy AI-specific agent
    cp "$(dirname "$0")/jetson-ai-agent.py" "$ACTIVELOG_HOME/bin/"
    cp "$(dirname "$0")/ai-inference-server.py" "$ACTIVELOG_HOME/bin/"
    cp "$(dirname "$0")/model-optimizer.py" "$ACTIVELOG_HOME/bin/"
    
    # Make scripts executable
    chmod +x "$ACTIVELOG_HOME"/bin/*
    
    # Create symlinks
    ln -sf "$ACTIVELOG_HOME/bin/jetson-ai-agent.py" /usr/local/bin/activelog-ai-agent
    ln -sf "$ACTIVELOG_HOME/bin/ai-inference-server.py" /usr/local/bin/activelog-inference
    ln -sf "$ACTIVELOG_HOME/bin/model-optimizer.py" /usr/local/bin/activelog-optimize
    
    print_success "ActiveLog AI Edge software installed"
}

# Configure AI model optimization
configure_ai_optimization() {
    print_ai "Configuring AI model optimization..."
    
    # Create TensorRT optimization script
    cat > "$ACTIVELOG_HOME/scripts/optimize-models.sh" << 'EOF'
#!/bin/bash
# Optimize AI models for Jetson hardware

MODELS_DIR="/var/lib/activelog/models"
OPTIMIZED_DIR="/var/lib/activelog/models/optimized"

mkdir -p "$OPTIMIZED_DIR"

# Function to optimize ONNX models with TensorRT
optimize_onnx() {
    local input_model="$1"
    local output_model="$2"
    
    echo "Optimizing $input_model..."
    
    python3 << PYTHON
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

def build_engine(model_path, engine_path):
    logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, logger)
    
    with open(model_path, 'rb') as f:
        parser.parse(f.read())
    
    config = builder.create_builder_config()
    config.max_workspace_size = 1 << 30  # 1GB
    config.set_flag(trt.BuilderFlag.FP16)  # Enable FP16 for better performance
    
    engine = builder.build_engine(network, config)
    
    with open(engine_path, 'wb') as f:
        f.write(engine.serialize())
    
    print(f"Optimized model saved to {engine_path}")

build_engine("$input_model", "$output_model")
PYTHON
}

# Optimize all ONNX models in the models directory
for model in "$MODELS_DIR"/*.onnx; do
    if [ -f "$model" ]; then
        basename=$(basename "$model" .onnx)
        optimize_onnx "$model" "$OPTIMIZED_DIR/${basename}.trt"
    fi
done
EOF

    chmod +x "$ACTIVELOG_HOME/scripts/optimize-models.sh"
    
    print_success "AI model optimization configured"
}

# Create Jetson-specific configuration
create_jetson_config() {
    print_status "Creating Jetson-specific configuration..."
    
    DEVICE_ID=$(openssl rand -hex 16)
    
    cat > "$CONFIG_FILE" << EOF
# ActiveLog Jetson Edge AI Device Configuration
[device]
id = $DEVICE_ID
name = $(hostname)
type = jetson
model = $JETSON_MODEL
jetpack_version = $JETPACK_VERSION
version = $ACTIVELOG_VERSION

[hardware]
gpu_memory = $GPU_MEMORY
max_cpu_freq = $MAX_FREQ
cuda_enabled = true
tensorrt_enabled = true
opencv_cuda = true

[ai]
enable_inference = true
enable_training = false
enable_optimization = true
max_models_loaded = 5
model_cache_size = 2048
fp16_enabled = true
int8_enabled = false
batch_size = 1
max_gpu_usage = 80

[models]
model_dir = /var/lib/activelog/models
cache_dir = /var/lib/activelog/cache
auto_optimize = true
optimization_format = tensorrt

[inference]
api_port = 8000
grpc_port = 8001
enable_streaming = true
enable_batching = true
max_batch_delay = 10
triton_enabled = false

[network]
wifi_interface = wlan0
ethernet_interface = eth0
bluetooth_interface = hci0
enable_hotspot = true
hotspot_ssid = ActiveLog-Jetson-$(hostname)

[security]
certificate_path = /etc/activelog/device.crt
private_key_path = /etc/activelog/device.key
enable_encryption = true
enable_authentication = true

[processing]
enable_camera = true
enable_sensors = true
max_cpu_usage = 85
max_memory_usage = 80
thermal_throttle = 75

[power]
mode = performance
enable_jetson_clocks = true
enable_nvpmodel = true
thermal_limit = 80

[sync]
server_url = https://api.activelog.ai
sync_interval = 300
offline_queue_size = 2000
compression_enabled = true

[logging]
level = INFO
file_path = /var/log/activelog/jetson-edge.log
max_size = 50MB
backup_count = 10
EOF

    chown "$EDGE_USER:$EDGE_USER" "$CONFIG_FILE"
    chmod 640 "$CONFIG_FILE"
    
    print_success "Jetson configuration file created"
}

# Create systemd services for AI processing
create_ai_services() {
    print_ai "Creating AI inference services..."
    
    # ActiveLog Jetson AI Agent service
    cat > /etc/systemd/system/activelog-jetson-ai.service << 'EOF'
[Unit]
Description=ActiveLog Jetson AI Agent
After=network-online.target nvidia-persistenced.service
Wants=network-online.target
Requires=nvidia-persistenced.service

[Service]
Type=simple
User=activelog
Group=activelog
WorkingDirectory=/opt/activelog
ExecStart=/home/activelog/activelog-ai-venv/bin/python /opt/activelog/bin/jetson-ai-agent.py --config /etc/activelog/edge.conf
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# GPU access
SupplementaryGroups=video

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/activelog /var/log/activelog /var/lib/activelog /tmp

[Install]
WantedBy=multi-user.target
EOF

    # AI Inference Server service
    cat > /etc/systemd/system/activelog-inference.service << 'EOF'
[Unit]
Description=ActiveLog AI Inference Server
After=activelog-jetson-ai.service
Requires=activelog-jetson-ai.service

[Service]
Type=simple
User=activelog
Group=activelog
ExecStart=/home/activelog/activelog-ai-venv/bin/python /opt/activelog/bin/ai-inference-server.py
Restart=always
RestartSec=15

# GPU access
SupplementaryGroups=video

[Install]
WantedBy=multi-user.target
EOF

    # Model Optimization service (runs periodically)
    cat > /etc/systemd/system/activelog-model-optimizer.service << 'EOF'
[Unit]
Description=ActiveLog Model Optimizer
After=activelog-jetson-ai.service

[Service]
Type=oneshot
User=activelog
Group=activelog
ExecStart=/opt/activelog/scripts/optimize-models.sh

# GPU access
SupplementaryGroups=video
EOF

    cat > /etc/systemd/system/activelog-model-optimizer.timer << 'EOF'
[Unit]
Description=Run ActiveLog Model Optimizer daily
Requires=activelog-model-optimizer.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable services
    systemctl daemon-reload
    systemctl enable activelog-jetson-ai.service
    systemctl enable activelog-inference.service
    systemctl enable activelog-model-optimizer.timer
    
    print_success "AI inference services created"
}

# Configure thermal management
configure_thermal_management() {
    print_status "Configuring thermal management..."
    
    # Create thermal monitoring script
    cat > "$ACTIVELOG_HOME/scripts/thermal-monitor.py" << 'EOF'
#!/usr/bin/env python3
import time
import subprocess
import json
from pathlib import Path

class ThermalMonitor:
    def __init__(self):
        self.thermal_zones = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/class/thermal/thermal_zone1/temp",
            "/sys/class/thermal/thermal_zone2/temp"
        ]
        self.temp_limit = 80.0  # Celsius
        self.critical_limit = 85.0
    
    def get_temperatures(self):
        temps = {}
        for i, zone in enumerate(self.thermal_zones):
            try:
                with open(zone, 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
                    temps[f"zone_{i}"] = temp
            except:
                continue
        return temps
    
    def get_gpu_temp(self):
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=temperature.gpu', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return None
    
    def throttle_if_needed(self, temps):
        max_temp = max(temps.values()) if temps else 0
        gpu_temp = self.get_gpu_temp()
        
        if gpu_temp:
            max_temp = max(max_temp, gpu_temp)
        
        if max_temp > self.critical_limit:
            # Emergency throttling
            subprocess.run(['nvpmodel', '-m', '2'], check=False)  # Low power mode
            return "critical"
        elif max_temp > self.temp_limit:
            # Moderate throttling
            subprocess.run(['nvpmodel', '-m', '1'], check=False)  # Balanced mode
            return "throttled"
        else:
            # Full performance
            subprocess.run(['nvpmodel', '-m', '0'], check=False)  # Max performance
            return "normal"
    
    def monitor(self):
        while True:
            temps = self.get_temperatures()
            gpu_temp = self.get_gpu_temp()
            status = self.throttle_if_needed(temps)
            
            monitoring_data = {
                "timestamp": time.time(),
                "cpu_temps": temps,
                "gpu_temp": gpu_temp,
                "thermal_status": status
            }
            
            # Log thermal data
            with open("/var/log/activelog/thermal.log", "a") as f:
                f.write(json.dumps(monitoring_data) + "\n")
            
            time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    monitor = ThermalMonitor()
    monitor.monitor()
EOF

    chmod +x "$ACTIVELOG_HOME/scripts/thermal-monitor.py"
    
    # Create thermal monitoring service
    cat > /etc/systemd/system/activelog-thermal.service << 'EOF'
[Unit]
Description=ActiveLog Thermal Monitor
After=multi-user.target

[Service]
Type=simple
User=root
ExecStart=/opt/activelog/scripts/thermal-monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable activelog-thermal.service
    
    print_success "Thermal management configured"
}

# Setup AI model management
setup_model_management() {
    print_ai "Setting up AI model management..."
    
    # Create model management directories
    mkdir -p /var/lib/activelog/models/{onnx,tensorrt,pytorch,tensorflow}
    mkdir -p /var/lib/activelog/models/downloads
    
    # Create model download script
    cat > "$ACTIVELOG_HOME/scripts/download-models.py" << 'EOF'
#!/usr/bin/env python3
"""
Download and prepare common AI models for edge inference
"""
import os
import requests
import hashlib
from pathlib import Path

MODELS_DIR = Path("/var/lib/activelog/models")
MODELS_CONFIG = {
    "yolov5s": {
        "url": "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt",
        "type": "pytorch",
        "description": "YOLOv5 small object detection model"
    },
    "resnet50": {
        "url": "https://download.pytorch.org/models/resnet50-0676ba61.pth",
        "type": "pytorch", 
        "description": "ResNet-50 image classification model"
    },
    "mobilenet_v2": {
        "url": "https://storage.googleapis.com/tensorflow/keras-applications/mobilenet_v2/mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224.h5",
        "type": "tensorflow",
        "description": "MobileNet v2 lightweight classification model"
    }
}

def download_model(name, config):
    """Download a model if it doesn't exist"""
    model_dir = MODELS_DIR / config["type"]
    model_dir.mkdir(exist_ok=True)
    
    filename = config["url"].split("/")[-1]
    local_path = model_dir / filename
    
    if local_path.exists():
        print(f"Model {name} already exists at {local_path}")
        return
    
    print(f"Downloading {name}: {config['description']}")
    
    response = requests.get(config["url"], stream=True)
    response.raise_for_status()
    
    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Downloaded {name} to {local_path}")

def main():
    """Download all configured models"""
    for name, config in MODELS_CONFIG.items():
        try:
            download_model(name, config)
        except Exception as e:
            print(f"Failed to download {name}: {e}")

if __name__ == "__main__":
    main()
EOF

    chmod +x "$ACTIVELOG_HOME/scripts/download-models.py"
    
    # Set ownership
    chown -R "$EDGE_USER:$EDGE_USER" /var/lib/activelog/models
    
    print_success "AI model management set up"
}

# Create installation summary
create_jetson_summary() {
    print_status "Creating Jetson installation summary..."
    
    cat > "$ACTIVELOG_HOME/JETSON_INSTALLATION_SUMMARY.md" << EOF
# ActiveLog Jetson Edge AI Installation Summary

**Installation Date:** $(date)
**Device Model:** Jetson $JETSON_MODEL
**JetPack Version:** $JETPACK_VERSION
**Device ID:** $(grep "^id" "$CONFIG_FILE" | cut -d' ' -f3)
**ActiveLog Version:** $ACTIVELOG_VERSION

## Hardware Configuration

- **GPU Memory:** ${GPU_MEMORY}MB
- **Max CPU Frequency:** ${MAX_FREQ}Hz
- **CUDA Enabled:** Yes
- **TensorRT Enabled:** Yes
- **Performance Mode:** Maximum

## Installed AI Components

- ✅ CUDA Toolkit and Libraries
- ✅ TensorRT for inference optimization
- ✅ PyTorch (Jetson-optimized)
- ✅ TensorFlow (Jetson-optimized)
- ✅ OpenCV with CUDA support
- ✅ AI inference server
- ✅ Model optimization tools
- ✅ Thermal management

## Services

- **AI Agent:** systemctl status activelog-jetson-ai
- **Inference Server:** systemctl status activelog-inference
- **Thermal Monitor:** systemctl status activelog-thermal
- **Model Optimizer:** systemctl status activelog-model-optimizer.timer

## Important Directories

- **Models:** /var/lib/activelog/models/
- **Cache:** /var/lib/activelog/cache/
- **Logs:** /var/log/activelog/
- **Config:** $CONFIG_FILE

## AI Inference Endpoints

- **HTTP API:** http://$(hostname):8000
- **gRPC API:** $(hostname):8001
- **WebSocket:** ws://$(hostname):8000/ws

## Performance Optimization

- **Max Performance Mode:** nvpmodel -m 0
- **Enable Clocks:** jetson_clocks
- **Model Optimization:** /opt/activelog/scripts/optimize-models.sh

## Next Steps

1. Download common AI models:
   sudo -u activelog /opt/activelog/scripts/download-models.py

2. Optimize models for TensorRT:
   sudo -u activelog /opt/activelog/scripts/optimize-models.sh

3. Start AI services:
   sudo systemctl start activelog-jetson-ai
   sudo systemctl start activelog-inference

4. Test inference API:
   curl http://localhost:8000/health

5. Monitor performance:
   jtop  # or htop

## Monitoring Commands

- **GPU Usage:** nvidia-smi
- **System Stats:** jtop
- **Thermal Status:** cat /var/log/activelog/thermal.log
- **Service Logs:** journalctl -u activelog-jetson-ai -f

## Support

- Documentation: https://docs.activelog.ai/edge/jetson/
- Model Zoo: https://models.activelog.ai/
- Community: https://community.activelog.ai/jetson/

EOF

    print_success "Jetson installation summary created"
}

# Main installation function
main() {
    print_ai "Starting ActiveLog Jetson Nano AI Edge setup..."
    print_status "Installation log: $LOG_FILE"
    
    check_root
    detect_jetson
    configure_power_performance
    update_system
    install_cuda_tools
    install_tensorrt
    create_activelog_user
    install_python_ai_deps
    install_ai_containers
    install_activelog_ai_edge
    configure_ai_optimization
    create_jetson_config
    create_ai_services
    configure_thermal_management
    setup_model_management
    create_jetson_summary
    
    print_success "ActiveLog Jetson AI Edge setup completed!"
    print_ai "Your Jetson is now ready for AI inference at the edge!"
    
    print_status "Please reboot to complete the setup:"
    print_status "sudo reboot"
    
    print_status "After reboot, you can:"
    print_status "1. Download AI models: sudo -u activelog /opt/activelog/scripts/download-models.py"
    print_status "2. Start AI services: sudo systemctl start activelog-jetson-ai"
    print_status "3. Test inference: curl http://localhost:8000/health"
    print_status "4. Monitor with: jtop"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "ActiveLog Jetson AI Edge Setup Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --performance-only  Configure performance settings only"
        echo "  --models-only       Download and optimize models only"
        echo ""
        exit 0
        ;;
    --performance-only)
        print_ai "PERFORMANCE CONFIGURATION ONLY"
        check_root
        detect_jetson
        configure_power_performance
        exit 0
        ;;
    --models-only)
        print_ai "MODELS DOWNLOAD AND OPTIMIZATION ONLY"
        setup_model_management
        sudo -u activelog /opt/activelog/scripts/download-models.py
        /opt/activelog/scripts/optimize-models.sh
        exit 0
        ;;
esac

# Run main installation
main "$@"