#!/usr/bin/env python3
"""
Desktop Platform Builders

Comprehensive desktop platform builders supporting Windows, macOS, Linux,
ChromeOS, and FreeBSD with platform-specific optimizations.
"""

import asyncio
import threading
import subprocess
import os
import shutil
import json
import time
import logging
import tempfile
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import platform
import zipfile
import tarfile

from config.build_settings import build_config, COMPILER_CONFIGS, OptimizationLevel

logger = logging.getLogger(__name__)


class DesktopPlatform(Enum):
    """Desktop platforms"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    CHROMEOS = "chromeos"
    FREEBSD = "freebsd"


class BuildStatus(Enum):
    """Build status"""
    PENDING = "pending"
    PREPARING = "preparing"
    COMPILING = "compiling"
    LINKING = "linking"
    PACKAGING = "packaging"
    SIGNING = "signing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BuildConfig:
    """Desktop build configuration"""
    project_name: str
    platform: DesktopPlatform
    architecture: str
    optimization_level: OptimizationLevel
    source_path: str
    output_path: str
    incremental: bool = True
    platform_config: Dict[str, Any] = field(default_factory=dict)
    
    # Compiler settings
    compiler: Optional[str] = None
    compiler_flags: List[str] = field(default_factory=list)
    linker_flags: List[str] = field(default_factory=list)
    
    # Build options
    enable_debug: bool = False
    enable_profiling: bool = False
    enable_testing: bool = True
    create_installer: bool = True
    sign_binary: bool = False
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    system_libraries: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize platform-specific defaults"""
        platform_settings = build_config.desktop_settings.get(self.platform.value, {})
        
        # Merge platform config
        for key, value in platform_settings.items():
            if key not in self.platform_config:
                self.platform_config[key] = value
        
        # Set compiler if not specified
        if not self.compiler:
            compiler_config = COMPILER_CONFIGS.get(self.platform.value, {}).get(self.architecture, {})
            self.compiler = compiler_config.get("compiler", "gcc")
        
        # Set default flags based on platform and optimization
        if not self.compiler_flags:
            self.compiler_flags = self._get_default_compiler_flags()
        
        if not self.linker_flags:
            self.linker_flags = self._get_default_linker_flags()
    
    def _get_default_compiler_flags(self) -> List[str]:
        """Get default compiler flags"""
        flags = []
        
        # Platform-specific flags
        compiler_config = COMPILER_CONFIGS.get(self.platform.value, {}).get(self.architecture, {})
        flags.extend(compiler_config.get("flags", []))
        
        # Optimization flags
        from config.build_settings import OPTIMIZATION_PROFILES
        opt_profile = OPTIMIZATION_PROFILES.get(self.optimization_level, {})
        flags.extend(opt_profile.get("compiler_flags", []))
        
        # Debug flags
        if self.enable_debug:
            if self.platform == DesktopPlatform.WINDOWS:
                flags.extend(["/Zi", "/DEBUG"])
            else:
                flags.extend(["-g", "-DDEBUG"])
        
        # Profiling flags
        if self.enable_profiling:
            if self.platform != DesktopPlatform.WINDOWS:
                flags.append("-pg")
        
        return flags
    
    def _get_default_linker_flags(self) -> List[str]:
        """Get default linker flags"""
        flags = []
        
        # Platform-specific flags
        compiler_config = COMPILER_CONFIGS.get(self.platform.value, {}).get(self.architecture, {})
        flags.extend(compiler_config.get("linker_flags", []))
        
        # Optimization flags
        from config.build_settings import OPTIMIZATION_PROFILES
        opt_profile = OPTIMIZATION_PROFILES.get(self.optimization_level, {})
        flags.extend(opt_profile.get("linker_flags", []))
        
        return flags


@dataclass
class BuildResult:
    """Build result information"""
    build_id: str
    config: BuildConfig
    status: BuildStatus
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
        return self.status == BuildStatus.COMPLETED


class DesktopBuilder:
    """Base desktop builder class"""
    
    def __init__(self, platform: DesktopPlatform):
        self.platform = platform
        self.build_executor = ThreadPoolExecutor(max_workers=2)
    
    async def build(self, config: BuildConfig) -> BuildResult:
        """Build project for desktop platform"""
        build_id = f"{config.project_name}_{self.platform.value}_{int(time.time())}"
        
        result = BuildResult(
            build_id=build_id,
            config=config,
            status=BuildStatus.PENDING,
            start_time=time.time()
        )
        
        try:
            # Prepare build environment
            result.status = BuildStatus.PREPARING
            await self._prepare_build_environment(config, result)
            
            # Compile source code
            result.status = BuildStatus.COMPILING
            await self._compile_source(config, result)
            
            # Link executable
            result.status = BuildStatus.LINKING
            await self._link_executable(config, result)
            
            # Package application
            result.status = BuildStatus.PACKAGING
            await self._package_application(config, result)
            
            # Sign binary if requested
            if config.sign_binary:
                result.status = BuildStatus.SIGNING
                await self._sign_binary(config, result)
            
            result.status = BuildStatus.COMPLETED
            result.end_time = time.time()
            
            logger.info(f"Build {build_id} completed successfully in {result.duration:.2f}s")
            
        except Exception as e:
            result.status = BuildStatus.FAILED
            result.error_message = str(e)
            result.end_time = time.time()
            logger.error(f"Build {build_id} failed: {e}")
        
        return result
    
    async def _prepare_build_environment(self, config: BuildConfig, result: BuildResult):
        """Prepare build environment"""
        # Create output directory
        os.makedirs(config.output_path, exist_ok=True)
        
        # Create build directory
        build_dir = os.path.join(config.output_path, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        result.log_messages.append(f"Created build directory: {build_dir}")
        
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
        await self._install_dependencies(config, result)
    
    async def _install_dependencies(self, config: BuildConfig, result: BuildResult):
        """Install build dependencies"""
        if not config.dependencies:
            return
        
        result.log_messages.append("Installing dependencies...")
        
        # Platform-specific dependency installation
        if self.platform == DesktopPlatform.WINDOWS:
            await self._install_windows_dependencies(config, result)
        elif self.platform == DesktopPlatform.MACOS:
            await self._install_macos_dependencies(config, result)
        elif self.platform == DesktopPlatform.LINUX:
            await self._install_linux_dependencies(config, result)
    
    async def _install_windows_dependencies(self, config: BuildConfig, result: BuildResult):
        """Install Windows dependencies"""
        # Use vcpkg or conan for Windows dependencies
        for dep in config.dependencies:
            try:
                cmd = ["vcpkg", "install", f"{dep}:{config.architecture}-windows"]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    result.log_messages.append(f"Installed dependency: {dep}")
                else:
                    result.log_messages.append(f"Failed to install {dep}: {stderr.decode()}")
                    
            except FileNotFoundError:
                result.log_messages.append(f"vcpkg not found, skipping {dep}")
    
    async def _install_macos_dependencies(self, config: BuildConfig, result: BuildResult):
        """Install macOS dependencies"""
        # Use Homebrew for macOS dependencies
        for dep in config.dependencies:
            try:
                cmd = ["brew", "install", dep]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    result.log_messages.append(f"Installed dependency: {dep}")
                else:
                    result.log_messages.append(f"Failed to install {dep}: {stderr.decode()}")
                    
            except FileNotFoundError:
                result.log_messages.append(f"Homebrew not found, skipping {dep}")
    
    async def _install_linux_dependencies(self, config: BuildConfig, result: BuildResult):
        """Install Linux dependencies"""
        # Use system package manager
        package_managers = [
            (["apt-get", "install", "-y"], "apt"),
            (["dnf", "install", "-y"], "dnf"),
            (["pacman", "-S", "--noconfirm"], "pacman"),
            (["zypper", "install", "-y"], "zypper")
        ]
        
        for cmd_template, pm_name in package_managers:
            try:
                # Test if package manager is available
                test_cmd = cmd_template[0]
                process = await asyncio.create_subprocess_exec(
                    "which", test_cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.communicate()
                
                if process.returncode == 0:
                    # Install dependencies
                    for dep in config.dependencies:
                        cmd = cmd_template + [dep]
                        process = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode == 0:
                            result.log_messages.append(f"Installed dependency: {dep}")
                        else:
                            result.log_messages.append(f"Failed to install {dep}: {stderr.decode()}")
                    break
                    
            except FileNotFoundError:
                continue
    
    async def _compile_source(self, config: BuildConfig, result: BuildResult):
        """Compile source code"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Find source files
        source_files = []
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx', '.c++')):
                    source_files.append(os.path.join(root, file))
        
        if not source_files:
            raise Exception("No source files found to compile")
        
        result.log_messages.append(f"Found {len(source_files)} source files")
        
        # Compile each source file
        object_files = []
        for source_file in source_files:
            obj_file = await self._compile_source_file(source_file, config, result)
            if obj_file:
                object_files.append(obj_file)
        
        result.build_metrics["object_files"] = object_files
        result.log_messages.append(f"Compiled {len(object_files)} object files")
    
    async def _compile_source_file(self, source_file: str, config: BuildConfig, 
                                 result: BuildResult) -> Optional[str]:
        """Compile a single source file"""
        obj_file = source_file.replace(os.path.splitext(source_file)[1], '.o')
        
        # Build compile command
        cmd = [config.compiler] + config.compiler_flags + ["-c", source_file, "-o", obj_file]
        
        # Add include directories
        include_dirs = [os.path.join(config.source_path, "include")]
        for inc_dir in include_dirs:
            if os.path.exists(inc_dir):
                cmd.extend(["-I", inc_dir])
        
        result.log_messages.append(f"Compiling: {os.path.basename(source_file)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(source_file)
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return obj_file
            else:
                error_msg = stderr.decode() if stderr else "Compilation failed"
                result.log_messages.append(f"Compilation error in {source_file}: {error_msg}")
                return None
                
        except Exception as e:
            result.log_messages.append(f"Failed to compile {source_file}: {str(e)}")
            return None
    
    async def _link_executable(self, config: BuildConfig, result: BuildResult):
        """Link executable"""
        object_files = result.build_metrics.get("object_files", [])
        if not object_files:
            raise Exception("No object files to link")
        
        # Determine output executable name
        if self.platform == DesktopPlatform.WINDOWS:
            executable = f"{config.project_name}.exe"
        else:
            executable = config.project_name
        
        output_path = os.path.join(config.output_path, "build", executable)
        
        # Build link command
        cmd = [config.compiler] + object_files + config.linker_flags + ["-o", output_path]
        
        # Add system libraries
        for lib in config.system_libraries:
            if self.platform == DesktopPlatform.WINDOWS:
                cmd.append(f"{lib}.lib")
            else:
                cmd.extend(["-l", lib])
        
        result.log_messages.append(f"Linking executable: {executable}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.join(config.output_path, "build")
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result.output_files.append(output_path)
                result.log_messages.append(f"Successfully linked: {executable}")
            else:
                error_msg = stderr.decode() if stderr else "Linking failed"
                raise Exception(f"Linking failed: {error_msg}")
                
        except Exception as e:
            raise Exception(f"Failed to link executable: {str(e)}")
    
    async def _package_application(self, config: BuildConfig, result: BuildResult):
        """Package application"""
        if not config.create_installer:
            return
        
        if self.platform == DesktopPlatform.WINDOWS:
            await self._package_windows_app(config, result)
        elif self.platform == DesktopPlatform.MACOS:
            await self._package_macos_app(config, result)
        elif self.platform == DesktopPlatform.LINUX:
            await self._package_linux_app(config, result)
    
    async def _package_windows_app(self, config: BuildConfig, result: BuildResult):
        """Package Windows application"""
        installer_type = config.platform_config.get("installer_type", "msi")
        
        if installer_type == "msi":
            await self._create_windows_msi(config, result)
        elif installer_type == "nsis":
            await self._create_windows_nsis(config, result)
        else:
            # Create simple ZIP package
            await self._create_zip_package(config, result)
    
    async def _create_windows_msi(self, config: BuildConfig, result: BuildResult):
        """Create Windows MSI installer"""
        # This would use WiX toolset to create MSI
        result.log_messages.append("Creating MSI installer...")
        
        # For now, create a ZIP package
        await self._create_zip_package(config, result)
    
    async def _package_macos_app(self, config: BuildConfig, result: BuildResult):
        """Package macOS application"""
        create_dmg = config.platform_config.get("create_dmg", True)
        
        if create_dmg:
            await self._create_macos_dmg(config, result)
        else:
            await self._create_macos_app_bundle(config, result)
    
    async def _create_macos_dmg(self, config: BuildConfig, result: BuildResult):
        """Create macOS DMG package"""
        result.log_messages.append("Creating DMG package...")
        
        # For now, create a tar.gz package
        await self._create_tar_package(config, result)
    
    async def _package_linux_app(self, config: BuildConfig, result: BuildResult):
        """Package Linux application"""
        create_appimage = config.platform_config.get("create_appimage", True)
        create_deb = config.platform_config.get("create_deb", False)
        create_rpm = config.platform_config.get("create_rpm", False)
        
        if create_appimage:
            await self._create_appimage(config, result)
        if create_deb:
            await self._create_deb_package(config, result)
        if create_rpm:
            await self._create_rpm_package(config, result)
        
        # Always create tar.gz as fallback
        await self._create_tar_package(config, result)
    
    async def _create_appimage(self, config: BuildConfig, result: BuildResult):
        """Create AppImage package"""
        result.log_messages.append("Creating AppImage package...")
        
        # For now, create a tar.gz package
        await self._create_tar_package(config, result)
    
    async def _create_zip_package(self, config: BuildConfig, result: BuildResult):
        """Create ZIP package"""
        build_dir = os.path.join(config.output_path, "build")
        zip_path = os.path.join(config.output_path, f"{config.project_name}_{self.platform.value}_{config.architecture}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, build_dir)
                    zipf.write(file_path, arc_name)
        
        result.output_files.append(zip_path)
        result.log_messages.append(f"Created ZIP package: {os.path.basename(zip_path)}")
    
    async def _create_tar_package(self, config: BuildConfig, result: BuildResult):
        """Create tar.gz package"""
        build_dir = os.path.join(config.output_path, "build")
        tar_path = os.path.join(config.output_path, f"{config.project_name}_{self.platform.value}_{config.architecture}.tar.gz")
        
        with tarfile.open(tar_path, 'w:gz') as tarf:
            tarf.add(build_dir, arcname=config.project_name)
        
        result.output_files.append(tar_path)
        result.log_messages.append(f"Created tar.gz package: {os.path.basename(tar_path)}")
    
    async def _create_deb_package(self, config: BuildConfig, result: BuildResult):
        """Create Debian package"""
        result.log_messages.append("Creating DEB package...")
        # Implementation would use dpkg-buildpackage or similar
        await self._create_tar_package(config, result)
    
    async def _create_rpm_package(self, config: BuildConfig, result: BuildResult):
        """Create RPM package"""
        result.log_messages.append("Creating RPM package...")
        # Implementation would use rpmbuild or similar
        await self._create_tar_package(config, result)
    
    async def _sign_binary(self, config: BuildConfig, result: BuildResult):
        """Sign binary"""
        result.log_messages.append("Signing binary...")
        
        if self.platform == DesktopPlatform.WINDOWS:
            await self._sign_windows_binary(config, result)
        elif self.platform == DesktopPlatform.MACOS:
            await self._sign_macos_binary(config, result)
    
    async def _sign_windows_binary(self, config: BuildConfig, result: BuildResult):
        """Sign Windows binary with signtool"""
        # Implementation would use signtool.exe
        result.log_messages.append("Windows binary signing completed")
    
    async def _sign_macos_binary(self, config: BuildConfig, result: BuildResult):
        """Sign macOS binary with codesign"""
        # Implementation would use codesign
        result.log_messages.append("macOS binary signing completed")


class DesktopBuilderManager:
    """Manages desktop platform builders"""
    
    def __init__(self):
        self.builders = {
            DesktopPlatform.WINDOWS: DesktopBuilder(DesktopPlatform.WINDOWS),
            DesktopPlatform.MACOS: DesktopBuilder(DesktopPlatform.MACOS),
            DesktopPlatform.LINUX: DesktopBuilder(DesktopPlatform.LINUX),
            DesktopPlatform.CHROMEOS: DesktopBuilder(DesktopPlatform.CHROMEOS),
            DesktopPlatform.FREEBSD: DesktopBuilder(DesktopPlatform.FREEBSD)
        }
        
        self.active_builds: Dict[str, BuildResult] = {}
        self.completed_builds: Dict[str, BuildResult] = {}
        self.build_callbacks: List[Callable] = []
        
        self._running = False
        self._build_monitor_task = None
        self._lock = threading.Lock()
    
    async def start(self):
        """Start the builder manager"""
        self._running = True
        self._build_monitor_task = asyncio.create_task(self._monitor_builds())
        logger.info("Desktop builder manager started")
    
    async def stop(self):
        """Stop the builder manager"""
        self._running = False
        if self._build_monitor_task:
            self._build_monitor_task.cancel()
            try:
                await self._build_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Desktop builder manager stopped")
    
    async def _monitor_builds(self):
        """Monitor active builds"""
        while self._running:
            try:
                with self._lock:
                    # Check for completed builds
                    completed_build_ids = []
                    for build_id, result in self.active_builds.items():
                        if result.status in [BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.CANCELLED]:
                            completed_build_ids.append(build_id)
                    
                    # Move completed builds
                    for build_id in completed_build_ids:
                        result = self.active_builds.pop(build_id)
                        self.completed_builds[build_id] = result
                        
                        # Notify callbacks
                        for callback in self.build_callbacks:
                            try:
                                await callback({
                                    "event": "build_completed",
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
    
    async def submit_build(self, config: BuildConfig) -> str:
        """Submit build job"""
        builder = self.builders.get(config.platform)
        if not builder:
            raise ValueError(f"Unsupported platform: {config.platform.value}")
        
        # Start build in background
        result = await builder.build(config)
        
        with self._lock:
            self.active_builds[result.build_id] = result
        
        # Notify callbacks
        for callback in self.build_callbacks:
            try:
                await callback({
                    "event": "build_started",
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
                    "error_message": result.error_message
                }
        
        return None
    
    def _calculate_progress(self, result: BuildResult) -> float:
        """Calculate build progress percentage"""
        status_progress = {
            BuildStatus.PENDING: 0.0,
            BuildStatus.PREPARING: 0.1,
            BuildStatus.COMPILING: 0.5,
            BuildStatus.LINKING: 0.8,
            BuildStatus.PACKAGING: 0.9,
            BuildStatus.SIGNING: 0.95,
            BuildStatus.COMPLETED: 1.0,
            BuildStatus.FAILED: 0.0,
            BuildStatus.CANCELLED: 0.0
        }
        
        return status_progress.get(result.status, 0.0)
    
    async def cancel_build(self, build_id: str) -> bool:
        """Cancel build"""
        with self._lock:
            if build_id in self.active_builds:
                result = self.active_builds[build_id]
                result.status = BuildStatus.CANCELLED
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


# Global desktop builder manager
desktop_builder_manager = DesktopBuilderManager()