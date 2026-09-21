#!/usr/bin/env python3
"""
Device Optimization Manager
Optimizes ActiveLog for various devices, platforms, and hardware configurations
"""

import os
import sys
import json
import platform
import psutil
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DeviceProfile:
    device_type: str
    cpu_cores: int
    memory_gb: float
    storage_type: str  # 'ssd', 'hdd', 'nvme'
    network_type: str  # 'ethernet', 'wifi', 'mobile'
    platform: str     # 'linux', 'windows', 'macos', 'android', 'ios'
    architecture: str  # 'x86_64', 'arm64', 'armv7'
    performance_tier: str  # 'high', 'medium', 'low', 'embedded'

class DeviceOptimizationManager:
    def __init__(self):
        self.device_profile = self._detect_device_profile()
        self.optimizations_applied = []
        self.config_overrides = {}
        
        logger.info(f"Detected device profile: {self.device_profile}")
    
    def _detect_device_profile(self) -> DeviceProfile:
        """Automatically detect device characteristics"""
        # Get system information
        cpu_count = psutil.cpu_count(logical=False)
        memory_gb = psutil.virtual_memory().total / (1024**3)
        platform_system = platform.system().lower()
        architecture = platform.machine().lower()
        
        # Detect storage type (simplified)
        storage_type = 'ssd'  # Default assumption
        try:
            # Try to detect SSD on Linux
            if platform_system == 'linux':
                result = subprocess.run(['lsblk', '-d', '-o', 'NAME,ROTA'], 
                                      capture_output=True, text=True)
                if '0' in result.stdout:  # 0 = SSD, 1 = HDD
                    storage_type = 'ssd'
                elif '1' in result.stdout:
                    storage_type = 'hdd'
        except:
            pass
        
        # Detect network type (simplified)
        network_type = 'ethernet'  # Default assumption
        
        # Determine performance tier
        if cpu_count >= 8 and memory_gb >= 16:
            performance_tier = 'high'
        elif cpu_count >= 4 and memory_gb >= 8:
            performance_tier = 'medium' 
        elif cpu_count >= 2 and memory_gb >= 4:
            performance_tier = 'low'
        else:
            performance_tier = 'embedded'
        
        # Determine device type
        device_type = 'desktop'
        if memory_gb < 4 or cpu_count < 2:
            device_type = 'embedded'
        elif 'arm' in architecture:
            device_type = 'mobile'
        
        return DeviceProfile(
            device_type=device_type,
            cpu_cores=cpu_count,
            memory_gb=memory_gb,
            storage_type=storage_type,
            network_type=network_type,
            platform=platform_system,
            architecture=architecture,
            performance_tier=performance_tier
        )
    
    def generate_optimized_configs(self) -> Dict[str, Dict]:
        """Generate optimized configurations for current device"""
        configs = {}
        
        # Base configuration adjustments based on performance tier
        if self.device_profile.performance_tier == 'high':
            base_config = {
                'max_workers': min(self.device_profile.cpu_cores, 8),
                'memory_limit_mb': int(self.device_profile.memory_gb * 1024 * 0.7),
                'connection_pool_size': 50,
                'cache_size_mb': 256,
                'batch_size': 100,
                'concurrent_requests': 20
            }
        elif self.device_profile.performance_tier == 'medium':
            base_config = {
                'max_workers': min(self.device_profile.cpu_cores, 4),
                'memory_limit_mb': int(self.device_profile.memory_gb * 1024 * 0.6),
                'connection_pool_size': 20,
                'cache_size_mb': 128,
                'batch_size': 50,
                'concurrent_requests': 10
            }
        elif self.device_profile.performance_tier == 'low':
            base_config = {
                'max_workers': min(self.device_profile.cpu_cores, 2),
                'memory_limit_mb': int(self.device_profile.memory_gb * 1024 * 0.5),
                'connection_pool_size': 10,
                'cache_size_mb': 64,
                'batch_size': 25,
                'concurrent_requests': 5
            }
        else:  # embedded
            base_config = {
                'max_workers': 1,
                'memory_limit_mb': int(self.device_profile.memory_gb * 1024 * 0.4),
                'connection_pool_size': 5,
                'cache_size_mb': 32,
                'batch_size': 10,
                'concurrent_requests': 2
            }
        
        # Storage-specific optimizations
        if self.device_profile.storage_type == 'hdd':
            base_config['io_buffer_size'] = 8192  # Larger buffers for HDD
            base_config['fsync_frequency'] = 'low'  # Reduce disk writes
        else:  # SSD/NVMe
            base_config['io_buffer_size'] = 4096
            base_config['fsync_frequency'] = 'normal'
        
        # Platform-specific adjustments
        if self.device_profile.platform == 'windows':
            base_config['process_priority'] = 'normal'
            base_config['memory_strategy'] = 'conservative'
        elif self.device_profile.platform == 'linux':
            base_config['process_priority'] = 'high'
            base_config['memory_strategy'] = 'aggressive'
        
        # Architecture-specific optimizations
        if 'arm' in self.device_profile.architecture:
            base_config['cpu_intensive_tasks'] = False
            base_config['prefer_async'] = True
        
        # Generate service-specific configurations
        services = ['api-gateway', 'auth', 'file-sync', 'ai-orchestrator', 'metadata']
        
        for service in services:
            service_config = base_config.copy()
            
            # Service-specific adjustments
            if service == 'api-gateway':
                service_config['max_workers'] = max(2, base_config['max_workers'])
                service_config['connection_pool_size'] = max(20, base_config['connection_pool_size'])
            elif service == 'ai-orchestrator':
                service_config['memory_limit_mb'] = int(base_config['memory_limit_mb'] * 1.5)
                service_config['cpu_affinity'] = self._get_cpu_affinity()
            elif service == 'auth':
                service_config['max_workers'] = min(2, base_config['max_workers'])
                service_config['memory_limit_mb'] = int(base_config['memory_limit_mb'] * 0.3)
            
            configs[service] = service_config
        
        return configs
    
    def _get_cpu_affinity(self) -> List[int]:
        """Get optimal CPU affinity based on device"""
        if self.device_profile.cpu_cores >= 4:
            # Use half the cores for CPU-intensive services
            return list(range(self.device_profile.cpu_cores // 2))
        else:
            # Use all available cores on low-end devices
            return list(range(self.device_profile.cpu_cores))
    
    def create_lightweight_startup_script(self) -> str:
        """Create device-optimized startup script"""
        script_content = f"""#!/bin/bash
# Device-Optimized ActiveLog Startup Script
# Generated for: {self.device_profile.device_type} ({self.device_profile.performance_tier} performance)

echo "🚀 Starting ActiveLog for {self.device_profile.device_type} device..."
echo "Device specs: {self.device_profile.cpu_cores} cores, {self.device_profile.memory_gb:.1f}GB RAM"

# Set environment variables based on device
export ACTIVELOG_DEVICE_TYPE="{self.device_profile.device_type}"
export ACTIVELOG_PERFORMANCE_TIER="{self.device_profile.performance_tier}"
export ACTIVELOG_MAX_MEMORY="{int(self.device_profile.memory_gb * 1024 * 0.6)}"

# Platform-specific optimizations
"""
        
        if self.device_profile.platform == 'linux':
            script_content += """
# Linux optimizations
export OMP_NUM_THREADS=$(($(nproc) / 2))
ulimit -n 4096  # Increase file descriptor limit
"""
        elif self.device_profile.platform == 'windows':
            script_content += """
# Windows optimizations  
set "OMP_NUM_THREADS=%NUMBER_OF_PROCESSORS%"
"""
        
        # Service startup order based on device capabilities
        if self.device_profile.performance_tier in ['high', 'medium']:
            script_content += """
# Start core services in parallel (high/medium performance devices)
start_services_parallel() {
    echo "Starting core services in parallel..."
    
    cd services/auth && python3 main.py &
    AUTH_PID=$!
    
    cd ../../services/api-gateway && python3 main.py &
    GATEWAY_PID=$!
    
    cd ../../services/file-sync && python3 main.py &
    FILESYNC_PID=$!
    
    # Wait for core services
    wait $AUTH_PID $GATEWAY_PID $FILESYNC_PID
    
    # Start secondary services
    cd ../../services/ai-orchestrator && python3 main.py &
    cd ../../services/metadata && python3 main.py &
}
"""
        else:
            script_content += """
# Start services sequentially (low performance/embedded devices)  
start_services_sequential() {
    echo "Starting services sequentially for resource conservation..."
    
    echo "Starting auth service..."
    cd services/auth && python3 main.py &
    sleep 3
    
    echo "Starting API gateway..."
    cd ../../services/api-gateway && python3 main.py &
    sleep 3
    
    echo "Starting file sync..."
    cd ../../services/file-sync && python3 main.py &
    sleep 2
    
    # Optional services for low-end devices
    if [ "$ACTIVELOG_PERFORMANCE_TIER" != "embedded" ]; then
        echo "Starting AI orchestrator..."
        cd ../../services/ai-orchestrator && python3 main.py &
    fi
}
"""
        
        script_content += f"""
# Health check function
check_service_health() {{
    local service_name=$1
    local port=$2
    local max_attempts=10
    
    for i in $(seq 1 $max_attempts); do
        if curl -s http://localhost:$port/health >/dev/null 2>&1; then
            echo "✅ $service_name is healthy"
            return 0
        fi
        sleep 1
    done
    
    echo "❌ $service_name failed to start properly"
    return 1
}}

# Main startup logic
main() {{
    # Create necessary directories
    mkdir -p pids logs cache
    
    # Apply device-specific system optimizations
    if [ "{self.device_profile.performance_tier}" = "high" ]; then
        start_services_parallel
    else
        start_services_sequential  
    fi
    
    # Health checks
    sleep 5
    check_service_health "Auth" 8002
    check_service_health "API Gateway" 8088
    check_service_health "File Sync" 8000
    
    echo ""
    echo "🎉 ActiveLog started successfully on {self.device_profile.device_type} device!"
    echo "Performance tier: {self.device_profile.performance_tier}"
    echo "Main interface: http://localhost:8088"
    echo "Memory usage optimized for {self.device_profile.memory_gb:.1f}GB RAM"
}}

# Run main function
main "$@"
"""
        
        return script_content
    
    def create_mobile_friendly_config(self) -> Dict:
        """Create mobile-friendly configuration"""
        return {
            'ui': {
                'responsive_breakpoints': {
                    'mobile': 768,
                    'tablet': 1024,
                    'desktop': 1200
                },
                'touch_friendly': True,
                'reduced_animations': True,
                'offline_mode': True,
                'lazy_loading': True,
                'image_compression': True,
                'bundle_splitting': True
            },
            'performance': {
                'preload_critical_resources': True,
                'defer_non_critical': True,
                'compress_responses': True,
                'cache_static_assets': True,
                'minimize_network_requests': True
            },
            'features': {
                'background_sync': True,
                'push_notifications': False,  # Disabled by default for battery
                'location_services': False,
                'camera_integration': False,
                'reduced_functionality': True  # Enable lite mode
            }
        }
    
    def create_embedded_config(self) -> Dict:
        """Create embedded device configuration (IoT, Raspberry Pi, etc.)"""
        return {
            'system': {
                'memory_limit_mb': min(512, int(self.device_profile.memory_gb * 1024 * 0.4)),
                'swap_usage': 'minimal',
                'cpu_governor': 'powersave',
                'service_count_limit': 3,  # Only run essential services
                'log_level': 'WARNING',  # Reduce log verbosity
                'database_sync_frequency': 'low'
            },
            'services': {
                'enabled': ['auth', 'api-gateway'],  # Only essential services
                'disabled': ['ai-orchestrator', 'metadata', 'backup'],
                'polling_intervals': {
                    'health_check': 60,  # Less frequent health checks
                    'metrics_collection': 300,
                    'cache_cleanup': 1800
                }
            },
            'storage': {
                'database_size_limit_mb': 100,
                'log_rotation_size_mb': 10,
                'cache_size_mb': 16,
                'temp_cleanup_frequency': 3600
            }
        }
    
    def generate_dockerfile_variants(self) -> Dict[str, str]:
        """Generate Docker configurations for different architectures"""
        dockerfiles = {}
        
        # Base Dockerfile for x86_64
        base_dockerfile = """
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    sqlite3 \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports
EXPOSE 8000 8001 8002 8088

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8088/health || exit 1
"""
        
        # ARM64 variant
        dockerfiles['arm64'] = base_dockerfile.replace(
            'FROM python:3.11-slim',
            'FROM --platform=linux/arm64 python:3.11-slim'
        ) + """
# ARM64 optimizations
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=2
"""
        
        # ARM32/ARMv7 variant  
        dockerfiles['armv7'] = """
FROM --platform=linux/arm/v7 python:3.11-slim

# ARM32 specific optimizations
RUN apt-get update && apt-get install -y \\
    curl \\
    sqlite3 \\
    python3-dev \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Reduce memory usage during pip install
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ARM32 environment optimizations
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072

EXPOSE 8000 8002 8088

# Simplified health check for low-power devices
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=2 \\
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["python3", "smart_service_manager.py", "start-critical"]
"""
        
        # Embedded/Alpine variant
        dockerfiles['embedded'] = """
FROM python:3.11-alpine

# Install minimal dependencies
RUN apk add --no-cache \\
    curl \\
    sqlite

WORKDIR /app

# Install only essential Python packages
COPY requirements-minimal.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Embedded device optimizations
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OMP_NUM_THREADS=1

# Only expose essential ports
EXPOSE 8002 8088

# Basic health check
HEALTHCHECK --interval=120s --timeout=30s --start-period=15s --retries=1 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:8002/health || exit 1

CMD ["python3", "smart_service_manager.py", "start-critical"]
"""
        
        return dockerfiles
    
    def create_requirements_variants(self) -> Dict[str, List[str]]:
        """Create different requirements.txt files for different device types"""
        
        base_requirements = [
            'fastapi>=0.104.0',
            'uvicorn[standard]>=0.24.0',
            'pydantic>=2.4.0',
            'python-multipart>=0.0.6',
            'aiofiles>=23.2.1',
            'httpx>=0.25.0',
            'python-jose[cryptography]>=3.3.0',
        ]
        
        full_requirements = base_requirements + [
            'numpy>=1.24.0',
            'pandas>=2.0.0',  
            'scikit-learn>=1.3.0',
            'psutil>=5.9.0',
            'redis>=5.0.0',
            'aiohttp>=3.9.0',
            'pillow>=10.0.0',
            'matplotlib>=3.7.0',
        ]
        
        embedded_requirements = [
            'fastapi>=0.104.0',
            'uvicorn>=0.24.0',
            'pydantic>=2.4.0',
            'aiofiles>=23.2.1',
            'httpx>=0.25.0',
            'psutil>=5.9.0',
        ]
        
        return {
            'full': full_requirements,
            'minimal': embedded_requirements,
            'mobile': base_requirements + ['psutil>=5.9.0'],
        }
    
    async def apply_device_optimizations(self):
        """Apply all device-specific optimizations"""
        logger.info(f"Applying optimizations for {self.device_profile.device_type} device...")
        
        # Generate optimized configurations
        configs = self.generate_optimized_configs()
        
        # Save device-specific configuration
        config_file = Path("device_optimized_config.json")
        with open(config_file, 'w') as f:
            json.dump({
                'device_profile': self.device_profile.__dict__,
                'service_configs': configs,
                'optimization_timestamp': str(asyncio.get_event_loop().time())
            }, f, indent=2)
        
        # Create optimized startup script
        startup_script = self.create_lightweight_startup_script()
        script_file = Path("start_optimized.sh")
        with open(script_file, 'w') as f:
            f.write(startup_script)
        os.chmod(script_file, 0o755)
        
        # Create mobile config if applicable
        if self.device_profile.device_type == 'mobile' or self.device_profile.performance_tier == 'low':
            mobile_config = self.create_mobile_friendly_config()
            with open('mobile_config.json', 'w') as f:
                json.dump(mobile_config, f, indent=2)
        
        # Create embedded config if applicable  
        if self.device_profile.performance_tier == 'embedded':
            embedded_config = self.create_embedded_config()
            with open('embedded_config.json', 'w') as f:
                json.dump(embedded_config, f, indent=2)
        
        # Generate Docker variants
        dockerfiles = self.generate_dockerfile_variants()
        docker_dir = Path("docker")
        docker_dir.mkdir(exist_ok=True)
        
        for arch, dockerfile_content in dockerfiles.items():
            with open(docker_dir / f"Dockerfile.{arch}", 'w') as f:
                f.write(dockerfile_content)
        
        # Generate requirements variants
        requirements_variants = self.create_requirements_variants()
        for variant, requirements in requirements_variants.items():
            with open(f"requirements-{variant}.txt", 'w') as f:
                f.write('\n'.join(requirements) + '\n')
        
        logger.info("✅ Device optimizations applied successfully")
        logger.info(f"📄 Configurations saved for {self.device_profile.performance_tier} performance tier")
        logger.info(f"🚀 Use './start_optimized.sh' to start with device optimizations")
    
    def print_optimization_summary(self):
        """Print summary of applied optimizations"""
        print("\n🎯 Device Optimization Summary")
        print("=" * 50)
        print(f"Device Type: {self.device_profile.device_type}")
        print(f"Performance Tier: {self.device_profile.performance_tier}")
        print(f"Platform: {self.device_profile.platform} ({self.device_profile.architecture})")
        print(f"CPU Cores: {self.device_profile.cpu_cores}")
        print(f"Memory: {self.device_profile.memory_gb:.1f}GB")
        print(f"Storage: {self.device_profile.storage_type}")
        print()
        
        print("📋 Applied Optimizations:")
        configs = self.generate_optimized_configs()
        base_config = configs.get('api-gateway', {})
        
        print(f"• Max Workers: {base_config.get('max_workers', 'N/A')}")
        print(f"• Memory Limit: {base_config.get('memory_limit_mb', 'N/A')}MB")
        print(f"• Connection Pool: {base_config.get('connection_pool_size', 'N/A')}")
        print(f"• Cache Size: {base_config.get('cache_size_mb', 'N/A')}MB")
        print(f"• Batch Size: {base_config.get('batch_size', 'N/A')}")
        
        if self.device_profile.performance_tier == 'embedded':
            print("\n🔧 Embedded Device Features:")
            print("• Reduced service count")
            print("• Lower polling frequencies") 
            print("• Minimal logging")
            print("• Optimized for battery life")
        
        print(f"\n🚀 Start optimized system with: ./start_optimized.sh")

async def main():
    """Main optimization function"""
    optimizer = DeviceOptimizationManager()
    
    # Apply optimizations
    await optimizer.apply_device_optimizations()
    
    # Print summary
    optimizer.print_optimization_summary()

if __name__ == "__main__":
    asyncio.run(main())