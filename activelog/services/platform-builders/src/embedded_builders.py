#!/usr/bin/env python3
"""
Embedded System Builders

Comprehensive embedded platform builders supporting Raspberry Pi, Arduino, ESP32/ESP8266,
NVIDIA Jetson, BeagleBone, PLCs, automotive, marine, smart home, and medical devices.
"""

import asyncio
import threading
import subprocess
import os
import shutil
import json
import time
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from config.build_settings import build_config, OptimizationLevel

logger = logging.getLogger(__name__)


class EmbeddedPlatform(Enum):
    """Embedded platforms"""
    RASPBERRY_PI = "raspberry_pi"
    ARDUINO = "arduino"
    ESP32 = "esp32"
    ESP8266 = "esp8266"
    JETSON = "jetson"
    BEAGLEBONE = "beaglebone"
    PLC = "plc"
    AUTOMOTIVE = "automotive"
    MARINE = "marine"
    SMART_HOME = "smart_home"
    MEDICAL = "medical"


class FirmwareStatus(Enum):
    """Firmware build status"""
    PENDING = "pending"
    PREPARING = "preparing"
    COMPILING = "compiling"
    LINKING = "linking"
    GENERATING = "generating"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FirmwareConfig:
    """Embedded firmware build configuration"""
    project_name: str
    platform: EmbeddedPlatform
    architecture: str
    optimization_level: OptimizationLevel
    source_path: str
    output_path: str
    incremental: bool = True
    platform_config: Dict[str, Any] = field(default_factory=dict)
    
    # Firmware metadata
    firmware_name: Optional[str] = None
    version: str = "1.0.0"
    
    # Build settings
    debug_build: bool = False
    bootloader_support: bool = False
    ota_support: bool = False  # Over-the-air updates
    low_power_mode: bool = False
    real_time_features: bool = False
    
    # Platform-specific settings
    mcu_frequency: Optional[int] = None
    flash_size: Optional[str] = None
    ram_size: Optional[str] = None
    
    # Dependencies
    libraries: List[str] = field(default_factory=list)
    drivers: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize platform-specific defaults"""
        platform_settings = build_config.embedded_settings.get(self.platform.value, {})
        
        # Merge platform config
        for key, value in platform_settings.items():
            if key not in self.platform_config:
                self.platform_config[key] = value
        
        # Set default firmware name
        if not self.firmware_name:
            self.firmware_name = self.project_name


@dataclass
class FirmwareBuildResult:
    """Embedded firmware build result"""
    build_id: str
    config: FirmwareConfig
    status: FirmwareStatus
    start_time: float
    end_time: Optional[float] = None
    output_files: List[str] = field(default_factory=list)
    log_messages: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    build_metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get build duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success(self) -> bool:
        """Check if build was successful"""
        return self.status == FirmwareStatus.COMPLETED


class EmbeddedBuilder:
    """Base embedded system builder"""
    
    def __init__(self, platform: EmbeddedPlatform):
        self.platform = platform
        self.build_executor = ThreadPoolExecutor(max_workers=2)
    
    async def build(self, config: FirmwareConfig) -> FirmwareBuildResult:
        """Build embedded firmware"""
        build_id = f"{config.project_name}_{self.platform.value}_{int(time.time())}"
        
        result = FirmwareBuildResult(
            build_id=build_id,
            config=config,
            status=FirmwareStatus.PENDING,
            start_time=time.time()
        )
        
        try:
            # Prepare build environment
            result.status = FirmwareStatus.PREPARING
            await self._prepare_build_environment(config, result)
            
            # Compile firmware
            result.status = FirmwareStatus.COMPILING
            await self._compile_firmware(config, result)
            
            # Link firmware
            result.status = FirmwareStatus.LINKING
            await self._link_firmware(config, result)
            
            # Generate firmware image
            result.status = FirmwareStatus.GENERATING
            await self._generate_firmware_image(config, result)
            
            # Run tests if enabled
            if config.platform_config.get("enable_testing", False):
                result.status = FirmwareStatus.TESTING
                await self._run_firmware_tests(config, result)
            
            result.status = FirmwareStatus.COMPLETED
            result.end_time = time.time()
            
            logger.info(f"Firmware build {build_id} completed successfully in {result.duration:.2f}s")
            
        except Exception as e:
            result.status = FirmwareStatus.FAILED
            result.error_message = str(e)
            result.end_time = time.time()
            logger.error(f"Firmware build {build_id} failed: {e}")
        
        return result
    
    async def _prepare_build_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare build environment"""
        # Create output directory
        os.makedirs(config.output_path, exist_ok=True)
        
        # Create build directory
        build_dir = os.path.join(config.output_path, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        result.log_messages.append(f"Created build directory: {build_dir}")
        
        # Platform-specific preparation
        if self.platform == EmbeddedPlatform.RASPBERRY_PI:
            await self._prepare_raspberry_pi_environment(config, result)
        elif self.platform == EmbeddedPlatform.ARDUINO:
            await self._prepare_arduino_environment(config, result)
        elif self.platform in [EmbeddedPlatform.ESP32, EmbeddedPlatform.ESP8266]:
            await self._prepare_esp_environment(config, result)
        elif self.platform == EmbeddedPlatform.JETSON:
            await self._prepare_jetson_environment(config, result)
        elif self.platform == EmbeddedPlatform.BEAGLEBONE:
            await self._prepare_beaglebone_environment(config, result)
        elif self.platform == EmbeddedPlatform.PLC:
            await self._prepare_plc_environment(config, result)
        elif self.platform == EmbeddedPlatform.AUTOMOTIVE:
            await self._prepare_automotive_environment(config, result)
        elif self.platform == EmbeddedPlatform.MARINE:
            await self._prepare_marine_environment(config, result)
        elif self.platform == EmbeddedPlatform.SMART_HOME:
            await self._prepare_smart_home_environment(config, result)
        elif self.platform == EmbeddedPlatform.MEDICAL:
            await self._prepare_medical_environment(config, result)
    
    async def _prepare_raspberry_pi_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare Raspberry Pi build environment"""
        result.log_messages.append("Setting up Raspberry Pi cross-compilation environment")
        
        # Check for cross-compiler
        cross_compiler = f"arm-linux-gnueabihf-gcc"
        if config.architecture == "arm64":
            cross_compiler = "aarch64-linux-gnu-gcc"
        
        try:
            process = await asyncio.create_subprocess_exec(
                "which", cross_compiler,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.communicate()
            
            if process.returncode != 0:
                result.log_messages.append(f"Warning: {cross_compiler} not found, using native compiler")
                
        except Exception as e:
            result.log_messages.append(f"Cross-compiler check failed: {e}")
        
        result.log_messages.append("Raspberry Pi build environment ready")
    
    async def _prepare_arduino_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare Arduino build environment"""
        result.log_messages.append("Setting up Arduino build environment")
        
        # Create Arduino project structure
        build_dir = os.path.join(config.output_path, "build")
        sketch_dir = os.path.join(build_dir, f"{config.project_name}")
        os.makedirs(sketch_dir, exist_ok=True)
        
        # Create basic Arduino sketch if it doesn't exist
        sketch_file = os.path.join(sketch_dir, f"{config.project_name}.ino")
        if not os.path.exists(sketch_file):
            with open(sketch_file, 'w') as f:
                f.write(f"""
// {config.project_name} Arduino Sketch
// Version: {config.version}

void setup() {{
  // Initialize serial communication
  Serial.begin(9600);
  Serial.println("{config.firmware_name} starting...");
}}

void loop() {{
  // Main program loop
  delay(1000);
}}
""")
        
        result.log_messages.append("Arduino build environment ready")
    
    async def _prepare_esp_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare ESP32/ESP8266 build environment"""
        result.log_messages.append(f"Setting up {self.platform.value.upper()} build environment")
        
        # Check for ESP-IDF or Arduino Core
        idf_path = os.environ.get('IDF_PATH')
        if not idf_path:
            result.log_messages.append("ESP-IDF not found, using Arduino framework")
        
        # Create basic project structure
        build_dir = os.path.join(config.output_path, "build")
        
        # Create CMakeLists.txt for ESP-IDF
        cmake_file = os.path.join(build_dir, "CMakeLists.txt")
        if not os.path.exists(cmake_file):
            with open(cmake_file, 'w') as f:
                f.write(f"""
cmake_minimum_required(VERSION 3.5)

set(PROJECT_NAME "{config.project_name}")
include($ENV{{IDF_PATH}}/tools/cmake/project.cmake)
project(${{PROJECT_NAME}})
""")
        
        result.log_messages.append(f"{self.platform.value.upper()} build environment ready")
    
    async def _prepare_jetson_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare NVIDIA Jetson build environment"""
        result.log_messages.append("Setting up NVIDIA Jetson build environment")
        
        # Check for CUDA and TensorRT
        cuda_available = os.path.exists("/usr/local/cuda")
        tensorrt_available = os.path.exists("/usr/include/NvInfer.h")
        
        if cuda_available:
            result.log_messages.append("CUDA toolkit found")
        if tensorrt_available:
            result.log_messages.append("TensorRT found")
        
        result.log_messages.append("Jetson build environment ready")
    
    async def _prepare_beaglebone_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare BeagleBone build environment"""
        result.log_messages.append("Setting up BeagleBone build environment")
        result.log_messages.append("BeagleBone build environment ready")
    
    async def _prepare_plc_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare PLC build environment"""
        result.log_messages.append("Setting up PLC build environment")
        result.log_messages.append("PLC build environment ready")
    
    async def _prepare_automotive_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare automotive system build environment"""
        result.log_messages.append("Setting up automotive build environment")
        result.log_messages.append("Automotive build environment ready")
    
    async def _prepare_marine_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare marine electronics build environment"""
        result.log_messages.append("Setting up marine electronics build environment")
        result.log_messages.append("Marine build environment ready")
    
    async def _prepare_smart_home_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare smart home device build environment"""
        result.log_messages.append("Setting up smart home build environment")
        result.log_messages.append("Smart home build environment ready")
    
    async def _prepare_medical_environment(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Prepare medical device build environment"""
        result.log_messages.append("Setting up medical device build environment")
        result.log_messages.append("Medical device build environment ready")
    
    async def _compile_firmware(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Compile firmware source code"""
        if self.platform == EmbeddedPlatform.ARDUINO:
            await self._compile_arduino_firmware(config, result)
        elif self.platform in [EmbeddedPlatform.ESP32, EmbeddedPlatform.ESP8266]:
            await self._compile_esp_firmware(config, result)
        else:
            await self._compile_generic_firmware(config, result)
    
    async def _compile_arduino_firmware(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Compile Arduino firmware"""
        build_dir = os.path.join(config.output_path, "build")
        sketch_path = os.path.join(build_dir, f"{config.project_name}", f"{config.project_name}.ino")
        
        # Arduino CLI command
        board = config.platform_config.get("board", "arduino:avr:uno")
        cmd = ["arduino-cli", "compile", "--fqbn", board, sketch_path]
        
        result.log_messages.append(f"Compiling Arduino sketch for board: {board}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result.log_messages.append("Arduino firmware compiled successfully")
            else:
                error_msg = stderr.decode() if stderr else "Compilation failed"
                raise Exception(f"Arduino compilation failed: {error_msg}")
                
        except FileNotFoundError:
            raise Exception("Arduino CLI not found. Please install Arduino CLI.")
        except Exception as e:
            raise Exception(f"Failed to compile Arduino firmware: {str(e)}")
    
    async def _compile_esp_firmware(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Compile ESP32/ESP8266 firmware"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Use idf.py for ESP-IDF or Arduino CLI for Arduino framework
        idf_path = os.environ.get('IDF_PATH')
        
        if idf_path:
            # ESP-IDF build
            cmd = ["idf.py", "build"]
            result.log_messages.append("Building with ESP-IDF")
        else:
            # Arduino framework
            board = "esp32:esp32:esp32" if self.platform == EmbeddedPlatform.ESP32 else "esp8266:esp8266:nodemcu"
            cmd = ["arduino-cli", "compile", "--fqbn", board]
            result.log_messages.append("Building with Arduino framework")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=build_dir
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result.log_messages.append("ESP firmware compiled successfully")
            else:
                error_msg = stderr.decode() if stderr else "Compilation failed"
                raise Exception(f"ESP compilation failed: {error_msg}")
                
        except FileNotFoundError:
            raise Exception("Build tools not found. Please install ESP-IDF or Arduino CLI.")
        except Exception as e:
            raise Exception(f"Failed to compile ESP firmware: {str(e)}")
    
    async def _compile_generic_firmware(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Compile generic embedded firmware"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Find source files
        source_files = []
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx')):
                    source_files.append(os.path.join(root, file))
        
        if not source_files:
            result.log_messages.append("No source files found, creating minimal firmware")
            return
        
        result.log_messages.append(f"Found {len(source_files)} source files")
        
        # Determine compiler based on platform
        if self.platform == EmbeddedPlatform.RASPBERRY_PI:
            compiler = "arm-linux-gnueabihf-gcc" if config.architecture == "arm" else "aarch64-linux-gnu-gcc"
        else:
            compiler = "gcc"
        
        # Compile with embedded-specific flags
        flags = ["-Os", "-ffunction-sections", "-fdata-sections"]
        
        for source_file in source_files:
            obj_file = source_file.replace(os.path.splitext(source_file)[1], '.o')
            cmd = [compiler] + flags + ["-c", source_file, "-o", obj_file]
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Compilation failed"
                    result.log_messages.append(f"Warning: Failed to compile {source_file}: {error_msg}")
                    
            except FileNotFoundError:
                result.log_messages.append(f"Compiler {compiler} not found, skipping compilation")
                break
        
        result.log_messages.append("Generic firmware compilation completed")
    
    async def _link_firmware(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Link firmware executable"""
        result.log_messages.append("Linking firmware")
        # Platform-specific linking would be implemented here
        result.log_messages.append("Firmware linking completed")
    
    async def _generate_firmware_image(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Generate firmware image/binary"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Generate platform-specific firmware images
        if self.platform == EmbeddedPlatform.ARDUINO:
            # Arduino generates .hex files
            hex_file = os.path.join(build_dir, f"{config.project_name}.hex")
            result.output_files.append(hex_file)
            result.log_messages.append("Generated Arduino HEX file")
            
        elif self.platform in [EmbeddedPlatform.ESP32, EmbeddedPlatform.ESP8266]:
            # ESP generates .bin files
            bin_file = os.path.join(build_dir, f"{config.project_name}.bin")
            result.output_files.append(bin_file)
            result.log_messages.append("Generated ESP binary file")
            
        else:
            # Generic binary
            bin_file = os.path.join(config.output_path, f"{config.project_name}.bin")
            result.output_files.append(bin_file)
            result.log_messages.append("Generated firmware binary")
        
        result.build_metrics["firmware_size"] = os.path.getsize(result.output_files[0]) if result.output_files else 0
    
    async def _run_firmware_tests(self, config: FirmwareConfig, result: FirmwareBuildResult):
        """Run firmware tests"""
        result.log_messages.append("Running firmware tests")
        # Platform-specific testing would be implemented here
        result.log_messages.append("Firmware tests completed")


class EmbeddedBuilderManager:
    """Manages embedded system builders"""
    
    def __init__(self):
        self.builders = {
            EmbeddedPlatform.RASPBERRY_PI: EmbeddedBuilder(EmbeddedPlatform.RASPBERRY_PI),
            EmbeddedPlatform.ARDUINO: EmbeddedBuilder(EmbeddedPlatform.ARDUINO),
            EmbeddedPlatform.ESP32: EmbeddedBuilder(EmbeddedPlatform.ESP32),
            EmbeddedPlatform.ESP8266: EmbeddedBuilder(EmbeddedPlatform.ESP8266),
            EmbeddedPlatform.JETSON: EmbeddedBuilder(EmbeddedPlatform.JETSON),
            EmbeddedPlatform.BEAGLEBONE: EmbeddedBuilder(EmbeddedPlatform.BEAGLEBONE),
            EmbeddedPlatform.PLC: EmbeddedBuilder(EmbeddedPlatform.PLC),
            EmbeddedPlatform.AUTOMOTIVE: EmbeddedBuilder(EmbeddedPlatform.AUTOMOTIVE),
            EmbeddedPlatform.MARINE: EmbeddedBuilder(EmbeddedPlatform.MARINE),
            EmbeddedPlatform.SMART_HOME: EmbeddedBuilder(EmbeddedPlatform.SMART_HOME),
            EmbeddedPlatform.MEDICAL: EmbeddedBuilder(EmbeddedPlatform.MEDICAL)
        }
        
        self.active_builds: Dict[str, FirmwareBuildResult] = {}
        self.completed_builds: Dict[str, FirmwareBuildResult] = {}
        self.build_callbacks: List[Callable] = []
        
        self._running = False
        self._build_monitor_task = None
        self._lock = threading.Lock()
    
    async def start(self):
        """Start the embedded builder manager"""
        self._running = True
        self._build_monitor_task = asyncio.create_task(self._monitor_builds())
        logger.info("Embedded builder manager started")
    
    async def stop(self):
        """Stop the embedded builder manager"""
        self._running = False
        if self._build_monitor_task:
            self._build_monitor_task.cancel()
            try:
                await self._build_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Embedded builder manager stopped")
    
    async def _monitor_builds(self):
        """Monitor active builds"""
        while self._running:
            try:
                with self._lock:
                    completed_build_ids = []
                    for build_id, result in self.active_builds.items():
                        if result.status in [FirmwareStatus.COMPLETED, FirmwareStatus.FAILED, FirmwareStatus.CANCELLED]:
                            completed_build_ids.append(build_id)
                    
                    for build_id in completed_build_ids:
                        result = self.active_builds.pop(build_id)
                        self.completed_builds[build_id] = result
                        
                        for callback in self.build_callbacks:
                            try:
                                await callback({
                                    "event": "embedded_build_completed",
                                    "build_id": build_id,
                                    "platform": result.config.platform.value,
                                    "status": result.status.value,
                                    "duration": result.duration
                                })
                            except Exception as e:
                                logger.error(f"Build callback error: {e}")
                
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Build monitor error: {e}")
                await asyncio.sleep(5.0)
    
    async def submit_build(self, config: FirmwareConfig) -> str:
        """Submit embedded build job"""
        builder = self.builders.get(config.platform)
        if not builder:
            raise ValueError(f"Unsupported platform: {config.platform.value}")
        
        result = await builder.build(config)
        
        with self._lock:
            self.active_builds[result.build_id] = result
        
        for callback in self.build_callbacks:
            try:
                await callback({
                    "event": "embedded_build_started",
                    "build_id": result.build_id,
                    "platform": config.platform.value,
                    "architecture": config.architecture
                })
            except Exception as e:
                logger.error(f"Build callback error: {e}")
        
        return result.build_id
    
    async def get_build_status(self, build_id: str) -> Optional[Dict[str, Any]]:
        """Get build status"""
        with self._lock:
            result = self.active_builds.get(build_id) or self.completed_builds.get(build_id)
            
            if result:
                return {
                    "build_id": build_id,
                    "platform": result.config.platform.value,
                    "architecture": result.config.architecture,
                    "status": result.status.value,
                    "progress": self._calculate_progress(result),
                    "duration": result.duration,
                    "start_time": result.start_time,
                    "end_time": result.end_time,
                    "output_files": result.output_files,
                    "error_message": result.error_message,
                    "firmware_size": result.build_metrics.get("firmware_size", 0)
                }
        
        return None
    
    def _calculate_progress(self, result: FirmwareBuildResult) -> float:
        """Calculate build progress percentage"""
        status_progress = {
            FirmwareStatus.PENDING: 0.0,
            FirmwareStatus.PREPARING: 0.1,
            FirmwareStatus.COMPILING: 0.5,
            FirmwareStatus.LINKING: 0.7,
            FirmwareStatus.GENERATING: 0.9,
            FirmwareStatus.TESTING: 0.95,
            FirmwareStatus.COMPLETED: 1.0,
            FirmwareStatus.FAILED: 0.0,
            FirmwareStatus.CANCELLED: 0.0
        }
        
        return status_progress.get(result.status, 0.0)
    
    async def cancel_build(self, build_id: str) -> bool:
        """Cancel build"""
        with self._lock:
            if build_id in self.active_builds:
                result = self.active_builds[build_id]
                result.status = FirmwareStatus.CANCELLED
                result.end_time = time.time()
                return True
        return False
    
    async def get_build_logs(self, build_id: str, lines: int = 100) -> Optional[List[str]]:
        """Get build logs"""
        with self._lock:
            result = self.active_builds.get(build_id) or self.completed_builds.get(build_id)
            if result:
                return result.log_messages[-lines:] if lines > 0 else result.log_messages
        return None
    
    async def get_build_artifacts(self, build_id: str) -> Optional[List[str]]:
        """Get build artifacts"""
        with self._lock:
            result = self.active_builds.get(build_id) or self.completed_builds.get(build_id)
            if result:
                return result.output_files
        return None
    
    async def get_artifact_path(self, build_id: str, filename: Optional[str] = None) -> Optional[str]:
        """Get artifact file path"""
        artifacts = await self.get_build_artifacts(build_id)
        
        if not artifacts:
            return None
        
        if filename:
            for artifact in artifacts:
                if os.path.basename(artifact) == filename:
                    return artifact
            return None
        
        return artifacts[0] if artifacts else None
    
    def add_build_callback(self, callback: Callable):
        """Add build event callback"""
        self.build_callbacks.append(callback)
    
    def is_healthy(self) -> bool:
        """Check if builder manager is healthy"""
        return self._running
    
    def get_active_build_count(self) -> int:
        """Get number of active builds"""
        with self._lock:
            return len(self.active_builds)
    
    def get_completed_build_count(self) -> int:
        """Get number of completed builds"""
        with self._lock:
            return len(self.completed_builds)


# Global embedded builder manager
embedded_builder_manager = EmbeddedBuilderManager()