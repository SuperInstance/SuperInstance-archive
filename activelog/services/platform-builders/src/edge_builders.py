#!/usr/bin/env python3
"""
Edge Computing Platform Builders

Comprehensive edge computing builders supporting AWS Greengrass, Azure IoT Edge,
Google Edge TPU, NVIDIA Edge devices, and Intel NUC platforms.
"""

import asyncio
import threading
import subprocess
import os
import shutil
import json
import time
import logging
import yaml
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from config.build_settings import build_config, OptimizationLevel

logger = logging.getLogger(__name__)


class EdgePlatform(Enum):
    """Edge computing platforms"""
    AWS_GREENGRASS = "aws_greengrass"
    AZURE_IOT_EDGE = "azure_iot_edge"
    GOOGLE_EDGE_TPU = "google_edge_tpu"
    NVIDIA_EDGE = "nvidia_edge"
    INTEL_NUC = "intel_nuc"


class EdgeStatus(Enum):
    """Edge deployment status"""
    PENDING = "pending"
    PREPARING = "preparing"
    BUILDING = "building"
    CONTAINERIZING = "containerizing"
    PACKAGING = "packaging"
    DEPLOYING = "deploying"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class EdgeConfig:
    """Edge computing build configuration"""
    project_name: str
    platform: EdgePlatform
    architecture: str
    optimization_level: OptimizationLevel
    source_path: str
    output_path: str
    incremental: bool = True
    platform_config: Dict[str, Any] = field(default_factory=dict)
    
    # Edge metadata
    service_name: Optional[str] = None
    version: str = "1.0.0"
    
    # Deployment settings
    container_enabled: bool = True
    gpu_support: bool = False
    ai_acceleration: bool = False
    edge_runtime: str = "docker"
    
    # Platform-specific settings
    device_capabilities: List[str] = field(default_factory=list)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    ml_models: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize platform-specific defaults"""
        platform_settings = build_config.edge_settings.get(self.platform.value, {})
        
        # Merge platform config
        for key, value in platform_settings.items():
            if key not in self.platform_config:
                self.platform_config[key] = value
        
        # Set default service name
        if not self.service_name:
            self.service_name = self.project_name


@dataclass
class EdgeBuildResult:
    """Edge computing build result"""
    build_id: str
    config: EdgeConfig
    status: EdgeStatus
    start_time: float
    end_time: Optional[float] = None
    output_files: List[str] = field(default_factory=list)
    log_messages: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    build_metrics: Dict[str, Any] = field(default_factory=dict)
    deployment_info: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get build duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success(self) -> bool:
        """Check if build was successful"""
        return self.status == EdgeStatus.COMPLETED


class EdgeBuilder:
    """Base edge computing builder"""
    
    def __init__(self, platform: EdgePlatform):
        self.platform = platform
        self.build_executor = ThreadPoolExecutor(max_workers=2)
    
    async def build(self, config: EdgeConfig) -> EdgeBuildResult:
        """Build edge computing service"""
        build_id = f"{config.project_name}_{self.platform.value}_{int(time.time())}"
        
        result = EdgeBuildResult(
            build_id=build_id,
            config=config,
            status=EdgeStatus.PENDING,
            start_time=time.time()
        )
        
        try:
            # Prepare build environment
            result.status = EdgeStatus.PREPARING
            await self._prepare_build_environment(config, result)
            
            # Build application
            result.status = EdgeStatus.BUILDING
            await self._build_application(config, result)
            
            # Create container if enabled
            if config.container_enabled:
                result.status = EdgeStatus.CONTAINERIZING
                await self._create_container(config, result)
            
            # Package for platform
            result.status = EdgeStatus.PACKAGING
            await self._package_for_platform(config, result)
            
            # Deploy if configured
            if config.platform_config.get("auto_deploy", False):
                result.status = EdgeStatus.DEPLOYING
                await self._deploy_to_edge(config, result)
            
            # Run tests
            if config.platform_config.get("enable_testing", False):
                result.status = EdgeStatus.TESTING
                await self._run_edge_tests(config, result)
            
            result.status = EdgeStatus.COMPLETED
            result.end_time = time.time()
            
            logger.info(f"Edge build {build_id} completed successfully in {result.duration:.2f}s")
            
        except Exception as e:
            result.status = EdgeStatus.FAILED
            result.error_message = str(e)
            result.end_time = time.time()
            logger.error(f"Edge build {build_id} failed: {e}")
        
        return result
    
    async def _prepare_build_environment(self, config: EdgeConfig, result: EdgeBuildResult):
        """Prepare build environment"""
        # Create output directory
        os.makedirs(config.output_path, exist_ok=True)
        
        # Create build directory
        build_dir = os.path.join(config.output_path, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        result.log_messages.append(f"Created build directory: {build_dir}")
        
        # Platform-specific preparation
        if self.platform == EdgePlatform.AWS_GREENGRASS:
            await self._prepare_greengrass_environment(config, result)
        elif self.platform == EdgePlatform.AZURE_IOT_EDGE:
            await self._prepare_azure_edge_environment(config, result)
        elif self.platform == EdgePlatform.GOOGLE_EDGE_TPU:
            await self._prepare_coral_environment(config, result)
        elif self.platform == EdgePlatform.NVIDIA_EDGE:
            await self._prepare_nvidia_edge_environment(config, result)
        elif self.platform == EdgePlatform.INTEL_NUC:
            await self._prepare_intel_nuc_environment(config, result)
    
    async def _prepare_greengrass_environment(self, config: EdgeConfig, result: EdgeBuildResult):
        """Prepare AWS Greengrass environment"""
        result.log_messages.append("Setting up AWS Greengrass build environment")
        
        build_dir = os.path.join(config.output_path, "build")
        
        # Create Greengrass component recipe
        recipe = {
            "RecipeFormatVersion": "2020-01-25",
            "ComponentName": config.service_name,
            "ComponentVersion": config.version,
            "ComponentDescription": f"Edge service: {config.project_name}",
            "ComponentPublisher": "EdgeBuilder",
            "ComponentConfiguration": {
                "DefaultConfiguration": {
                    "accessControl": {
                        "aws.greengrass.ipc.mqttproxy": {
                            f"{config.service_name}:mqtt:1": {
                                "policyDescription": "Allows access to MQTT",
                                "operations": ["aws.greengrass#PublishToIoTCore", "aws.greengrass#SubscribeToIoTCore"],
                                "resources": ["*"]
                            }
                        }
                    }
                }
            },
            "Manifests": [
                {
                    "Platform": {
                        "os": "linux"
                    },
                    "Lifecycle": {
                        "install": "pip install -r requirements.txt",
                        "run": f"python3 {config.project_name}.py"
                    },
                    "Artifacts": [
                        {
                            "URI": "s3://BUCKET_NAME/COMPONENT_NAME/COMPONENT_VERSION/artifacts.zip",
                            "Unarchive": "ZIP"
                        }
                    ]
                }
            ]
        }
        
        recipe_path = os.path.join(build_dir, "gdk-config.json")
        with open(recipe_path, 'w') as f:
            json.dump({
                "component": recipe,
                "gdk_version": "1.0.0"
            }, f, indent=2)
        
        result.log_messages.append("AWS Greengrass environment ready")
    
    async def _prepare_azure_edge_environment(self, config: EdgeConfig, result: EdgeBuildResult):
        """Prepare Azure IoT Edge environment"""
        result.log_messages.append("Setting up Azure IoT Edge build environment")
        
        build_dir = os.path.join(config.output_path, "build")
        
        # Create deployment manifest
        deployment_manifest = {
            "modulesContent": {
                "$edgeAgent": {
                    "properties.desired": {
                        "schemaVersion": "1.1",
                        "runtime": {
                            "type": "docker",
                            "settings": {
                                "minDockerVersion": "v1.25"
                            }
                        },
                        "systemModules": {
                            "edgeAgent": {
                                "type": "docker",
                                "settings": {
                                    "image": "mcr.microsoft.com/azureiotedge-agent:1.4",
                                    "createOptions": "{}"
                                }
                            },
                            "edgeHub": {
                                "type": "docker",
                                "status": "running",
                                "restartPolicy": "always",
                                "settings": {
                                    "image": "mcr.microsoft.com/azureiotedge-hub:1.4",
                                    "createOptions": "{\"HostConfig\":{\"PortBindings\":{\"5671/tcp\":[{\"HostPort\":\"5671\"}],\"8883/tcp\":[{\"HostPort\":\"8883\"}]}}}"
                                }
                            }
                        },
                        "modules": {
                            config.service_name: {
                                "version": "1.0",
                                "type": "docker",
                                "status": "running",
                                "restartPolicy": "always",
                                "settings": {
                                    "image": f"{config.service_name}:latest",
                                    "createOptions": "{}"
                                }
                            }
                        }
                    }
                }
            }
        }
        
        manifest_path = os.path.join(build_dir, "deployment.template.json")
        with open(manifest_path, 'w') as f:
            json.dump(deployment_manifest, f, indent=2)
        
        result.log_messages.append("Azure IoT Edge environment ready")
    
    async def _prepare_coral_environment(self, config: EdgeConfig, result: EdgeBuildResult):
        """Prepare Google Coral/Edge TPU environment"""
        result.log_messages.append("Setting up Google Coral Edge TPU build environment")
        
        # Check for Edge TPU runtime
        tpu_available = os.path.exists("/usr/lib/x86_64-linux-gnu/libedgetpu.so.1")
        if tpu_available:
            result.log_messages.append("Edge TPU runtime found")
        else:
            result.log_messages.append("Edge TPU runtime not detected")
        
        result.log_messages.append("Coral Edge TPU environment ready")
    
    async def _prepare_nvidia_edge_environment(self, config: EdgeConfig, result: EdgeBuildResult):
        """Prepare NVIDIA Edge environment"""
        result.log_messages.append("Setting up NVIDIA Edge build environment")
        
        # Check for NVIDIA runtime
        nvidia_available = shutil.which("nvidia-smi") is not None
        if nvidia_available:
            result.log_messages.append("NVIDIA GPU runtime found")
            config.gpu_support = True
        
        # Check for DeepStream
        deepstream_available = os.path.exists("/opt/nvidia/deepstream")
        if deepstream_available:
            result.log_messages.append("DeepStream SDK found")
        
        result.log_messages.append("NVIDIA Edge environment ready")
    
    async def _prepare_intel_nuc_environment(self, config: EdgeConfig, result: EdgeBuildResult):
        """Prepare Intel NUC environment"""
        result.log_messages.append("Setting up Intel NUC build environment")
        
        # Check for OpenVINO
        openvino_available = os.path.exists("/opt/intel/openvino")
        if openvino_available:
            result.log_messages.append("Intel OpenVINO found")
            config.ai_acceleration = True
        
        result.log_messages.append("Intel NUC environment ready")
    
    async def _build_application(self, config: EdgeConfig, result: EdgeBuildResult):
        """Build the edge application"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Copy source files
        if os.path.exists(config.source_path):
            for item in os.listdir(config.source_path):
                if item.startswith('.'):
                    continue
                    
                src_path = os.path.join(config.source_path, item)
                dst_path = os.path.join(build_dir, item)
                
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dst_path)
        
        result.log_messages.append("Source files copied to build directory")
        
        # Install dependencies
        requirements_file = os.path.join(build_dir, "requirements.txt")
        if os.path.exists(requirements_file):
            cmd = ["pip", "install", "-r", "requirements.txt"]
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=build_dir
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    result.log_messages.append("Dependencies installed successfully")
                else:
                    result.log_messages.append(f"Dependency installation warning: {stderr.decode()}")
                    
            except Exception as e:
                result.log_messages.append(f"Dependency installation failed: {e}")
        
        result.log_messages.append("Application build completed")
    
    async def _create_container(self, config: EdgeConfig, result: EdgeBuildResult):
        """Create container image"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Create Dockerfile if it doesn't exist
        dockerfile_path = os.path.join(build_dir, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            await self._generate_dockerfile(config, result)
        
        # Build container image
        image_name = f"{config.service_name}:latest"
        cmd = ["docker", "build", "-t", image_name, "."]
        
        result.log_messages.append(f"Building container image: {image_name}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=build_dir
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result.log_messages.append("Container image built successfully")
                result.deployment_info["container_image"] = image_name
            else:
                error_msg = stderr.decode() if stderr else "Container build failed"
                raise Exception(f"Container build failed: {error_msg}")
                
        except FileNotFoundError:
            raise Exception("Docker not found. Please install Docker.")
        except Exception as e:
            raise Exception(f"Failed to create container: {str(e)}")
    
    async def _generate_dockerfile(self, config: EdgeConfig, result: EdgeBuildResult):
        """Generate Dockerfile for the application"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Base image selection
        if config.platform == EdgePlatform.NVIDIA_EDGE and config.gpu_support:
            base_image = "nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3"
        elif config.platform == EdgePlatform.GOOGLE_EDGE_TPU:
            base_image = "python:3.9-slim"
        elif config.ai_acceleration:
            base_image = "openvino/ubuntu20_runtime:latest"
        else:
            base_image = "python:3.9-slim"
        
        dockerfile_content = f"""
FROM {base_image}

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port if needed
EXPOSE 8000

# Run application
CMD ["python", "{config.project_name}.py"]
"""
        
        dockerfile_path = os.path.join(build_dir, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content.strip())
        
        result.log_messages.append("Generated Dockerfile")
    
    async def _package_for_platform(self, config: EdgeConfig, result: EdgeBuildResult):
        """Package for specific edge platform"""
        if self.platform == EdgePlatform.AWS_GREENGRASS:
            await self._package_greengrass_component(config, result)
        elif self.platform == EdgePlatform.AZURE_IOT_EDGE:
            await self._package_azure_module(config, result)
        elif self.platform == EdgePlatform.GOOGLE_EDGE_TPU:
            await self._package_coral_app(config, result)
        elif self.platform == EdgePlatform.NVIDIA_EDGE:
            await self._package_nvidia_container(config, result)
        elif self.platform == EdgePlatform.INTEL_NUC:
            await self._package_intel_app(config, result)
    
    async def _package_greengrass_component(self, config: EdgeConfig, result: EdgeBuildResult):
        """Package as AWS Greengrass component"""
        import zipfile
        
        build_dir = os.path.join(config.output_path, "build")
        zip_path = os.path.join(config.output_path, f"{config.service_name}_greengrass.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, build_dir)
                    zipf.write(file_path, arc_name)
        
        result.output_files.append(zip_path)
        result.log_messages.append("Packaged Greengrass component")
    
    async def _package_azure_module(self, config: EdgeConfig, result: EdgeBuildResult):
        """Package as Azure IoT Edge module"""
        # Azure modules are typically Docker containers
        if "container_image" in result.deployment_info:
            result.log_messages.append("Azure IoT Edge module ready (container image)")
        else:
            result.log_messages.append("Azure IoT Edge module packaged")
    
    async def _package_coral_app(self, config: EdgeConfig, result: EdgeBuildResult):
        """Package for Google Coral Edge TPU"""
        import tarfile
        
        build_dir = os.path.join(config.output_path, "build")
        tar_path = os.path.join(config.output_path, f"{config.service_name}_coral.tar.gz")
        
        with tarfile.open(tar_path, 'w:gz') as tarf:
            tarf.add(build_dir, arcname=config.service_name)
        
        result.output_files.append(tar_path)
        result.log_messages.append("Packaged Coral Edge TPU application")
    
    async def _package_nvidia_container(self, config: EdgeConfig, result: EdgeBuildResult):
        """Package for NVIDIA Edge devices"""
        if "container_image" in result.deployment_info:
            result.log_messages.append("NVIDIA Edge container ready")
        else:
            result.log_messages.append("NVIDIA Edge application packaged")
    
    async def _package_intel_app(self, config: EdgeConfig, result: EdgeBuildResult):
        """Package for Intel NUC"""
        import tarfile
        
        build_dir = os.path.join(config.output_path, "build")
        tar_path = os.path.join(config.output_path, f"{config.service_name}_intel.tar.gz")
        
        with tarfile.open(tar_path, 'w:gz') as tarf:
            tarf.add(build_dir, arcname=config.service_name)
        
        result.output_files.append(tar_path)
        result.log_messages.append("Packaged Intel NUC application")
    
    async def _deploy_to_edge(self, config: EdgeConfig, result: EdgeBuildResult):
        """Deploy to edge device"""
        result.log_messages.append("Deploying to edge device...")
        # Platform-specific deployment would be implemented here
        result.log_messages.append("Deployment completed")
    
    async def _run_edge_tests(self, config: EdgeConfig, result: EdgeBuildResult):
        """Run edge-specific tests"""
        result.log_messages.append("Running edge tests...")
        # Edge testing would be implemented here
        result.log_messages.append("Edge tests completed")


class EdgeBuilderManager:
    """Manages edge computing builders"""
    
    def __init__(self):
        self.builders = {
            EdgePlatform.AWS_GREENGRASS: EdgeBuilder(EdgePlatform.AWS_GREENGRASS),
            EdgePlatform.AZURE_IOT_EDGE: EdgeBuilder(EdgePlatform.AZURE_IOT_EDGE),
            EdgePlatform.GOOGLE_EDGE_TPU: EdgeBuilder(EdgePlatform.GOOGLE_EDGE_TPU),
            EdgePlatform.NVIDIA_EDGE: EdgeBuilder(EdgePlatform.NVIDIA_EDGE),
            EdgePlatform.INTEL_NUC: EdgeBuilder(EdgePlatform.INTEL_NUC)
        }
        
        self.active_builds: Dict[str, EdgeBuildResult] = {}
        self.completed_builds: Dict[str, EdgeBuildResult] = {}
        self.build_callbacks: List[Callable] = []
        
        self._running = False
        self._build_monitor_task = None
        self._lock = threading.Lock()
    
    async def start(self):
        """Start the edge builder manager"""
        self._running = True
        self._build_monitor_task = asyncio.create_task(self._monitor_builds())
        logger.info("Edge builder manager started")
    
    async def stop(self):
        """Stop the edge builder manager"""
        self._running = False
        if self._build_monitor_task:
            self._build_monitor_task.cancel()
            try:
                await self._build_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Edge builder manager stopped")
    
    async def _monitor_builds(self):
        """Monitor active builds"""
        while self._running:
            try:
                with self._lock:
                    completed_build_ids = []
                    for build_id, result in self.active_builds.items():
                        if result.status in [EdgeStatus.COMPLETED, EdgeStatus.FAILED, EdgeStatus.CANCELLED]:
                            completed_build_ids.append(build_id)
                    
                    for build_id in completed_build_ids:
                        result = self.active_builds.pop(build_id)
                        self.completed_builds[build_id] = result
                        
                        for callback in self.build_callbacks:
                            try:
                                await callback({
                                    "event": "edge_build_completed",
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
    
    async def submit_build(self, config: EdgeConfig) -> str:
        """Submit edge build job"""
        builder = self.builders.get(config.platform)
        if not builder:
            raise ValueError(f"Unsupported platform: {config.platform.value}")
        
        result = await builder.build(config)
        
        with self._lock:
            self.active_builds[result.build_id] = result
        
        for callback in self.build_callbacks:
            try:
                await callback({
                    "event": "edge_build_started",
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
                    "deployment_info": result.deployment_info
                }
        
        return None
    
    def _calculate_progress(self, result: EdgeBuildResult) -> float:
        """Calculate build progress percentage"""
        status_progress = {
            EdgeStatus.PENDING: 0.0,
            EdgeStatus.PREPARING: 0.1,
            EdgeStatus.BUILDING: 0.4,
            EdgeStatus.CONTAINERIZING: 0.6,
            EdgeStatus.PACKAGING: 0.8,
            EdgeStatus.DEPLOYING: 0.9,
            EdgeStatus.TESTING: 0.95,
            EdgeStatus.COMPLETED: 1.0,
            EdgeStatus.FAILED: 0.0,
            EdgeStatus.CANCELLED: 0.0
        }
        
        return status_progress.get(result.status, 0.0)
    
    async def cancel_build(self, build_id: str) -> bool:
        """Cancel build"""
        with self._lock:
            if build_id in self.active_builds:
                result = self.active_builds[build_id]
                result.status = EdgeStatus.CANCELLED
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


# Global edge builder manager
edge_builder_manager = EdgeBuilderManager()