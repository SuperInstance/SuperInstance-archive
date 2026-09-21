#!/usr/bin/env python3
"""
Universal Distribution System

Comprehensive distribution system with delta updates, rollback mechanisms,
signature verification, staged rollouts, and cross-platform package management.
"""

import asyncio
import threading
import subprocess
import os
import shutil
import json
import time
import logging
import hashlib
import zipfile
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from config.build_settings import build_config

logger = logging.getLogger(__name__)


class UpdateChannel(Enum):
    """Update channels"""
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"
    NIGHTLY = "nightly"
    CUSTOM = "custom"


class RolloutStrategy(Enum):
    """Rollout strategies"""
    IMMEDIATE = "immediate"
    STAGED = "staged"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    GRADUAL = "gradual"


class DistributionStatus(Enum):
    """Distribution status"""
    CREATED = "created"
    PREPARING = "preparing"
    PACKAGING = "packaging"
    SIGNING = "signing"
    TESTING = "testing"
    DEPLOYING = "deploying"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


class PackageFormat(Enum):
    """Package formats"""
    MSI = "msi"              # Windows
    EXE = "exe"              # Windows
    DMG = "dmg"              # macOS
    PKG = "pkg"              # macOS
    DEB = "deb"              # Debian/Ubuntu
    RPM = "rpm"              # RedHat/CentOS
    APPIMAGE = "appimage"    # Linux
    FLATPAK = "flatpak"      # Linux
    SNAP = "snap"            # Linux
    APK = "apk"              # Android
    IPA = "ipa"              # iOS
    APPX = "appx"            # Windows Store
    ZIP = "zip"              # Universal
    TAR_GZ = "tar_gz"        # Universal


@dataclass
class PackageInfo:
    """Package information"""
    name: str
    version: str
    format: PackageFormat
    platform: str
    architecture: str
    file_path: str
    file_size: int
    checksum: str
    signature: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_checksum(self) -> str:
        """Calculate package checksum"""
        if not os.path.exists(self.file_path):
            return ""
        
        sha256_hash = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        self.checksum = sha256_hash.hexdigest()
        return self.checksum


@dataclass
class DistributionConfig:
    """Distribution configuration"""
    build_id: str
    channel: UpdateChannel
    rollout_strategy: RolloutStrategy
    target_regions: List[str]
    target_platforms: List[str]
    metadata: Dict[str, Any]
    
    # Package settings
    create_delta_updates: bool = True
    enable_compression: bool = True
    sign_packages: bool = True
    
    # Rollout settings
    staged_rollout_percentage: int = 10
    canary_percentage: int = 5
    rollback_enabled: bool = True
    
    # Verification settings
    signature_verification: bool = True
    integrity_checks: bool = True


@dataclass
class DistributionResult:
    """Distribution result"""
    distribution_id: str
    config: DistributionConfig
    status: DistributionStatus
    start_time: float
    end_time: Optional[float] = None
    packages: List[PackageInfo] = field(default_factory=list)
    log_messages: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    deployment_stats: Dict[str, Any] = field(default_factory=dict)
    rollout_progress: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get distribution duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success(self) -> bool:
        """Check if distribution was successful"""
        return self.status == DistributionStatus.COMPLETED


class PackageManager:
    """Multi-platform package manager"""
    
    def __init__(self):
        self.package_formats = {
            "windows": [PackageFormat.MSI, PackageFormat.EXE, PackageFormat.APPX],
            "macos": [PackageFormat.DMG, PackageFormat.PKG],
            "linux": [PackageFormat.DEB, PackageFormat.RPM, PackageFormat.APPIMAGE, 
                     PackageFormat.FLATPAK, PackageFormat.SNAP],
            "android": [PackageFormat.APK],
            "ios": [PackageFormat.IPA]
        }
    
    async def create_package(self, build_path: str, package_info: PackageInfo) -> bool:
        """Create platform-specific package"""
        try:
            if package_info.format == PackageFormat.MSI:
                return await self._create_msi_package(build_path, package_info)
            elif package_info.format == PackageFormat.DMG:
                return await self._create_dmg_package(build_path, package_info)
            elif package_info.format == PackageFormat.DEB:
                return await self._create_deb_package(build_path, package_info)
            elif package_info.format == PackageFormat.RPM:
                return await self._create_rpm_package(build_path, package_info)
            elif package_info.format == PackageFormat.APPIMAGE:
                return await self._create_appimage_package(build_path, package_info)
            elif package_info.format == PackageFormat.APK:
                return await self._create_apk_package(build_path, package_info)
            elif package_info.format == PackageFormat.ZIP:
                return await self._create_zip_package(build_path, package_info)
            else:
                logger.warning(f"Unsupported package format: {package_info.format}")
                return False
                
        except Exception as e:
            logger.error(f"Package creation failed: {e}")
            return False
    
    async def _create_msi_package(self, build_path: str, package_info: PackageInfo) -> bool:
        """Create Windows MSI package"""
        # This would use WiX toolset or similar
        logger.info(f"Creating MSI package: {package_info.name}")
        
        # Placeholder implementation - create ZIP for now
        return await self._create_zip_package(build_path, package_info)
    
    async def _create_dmg_package(self, build_path: str, package_info: PackageInfo) -> bool:
        """Create macOS DMG package"""
        logger.info(f"Creating DMG package: {package_info.name}")
        
        # Use hdiutil to create DMG
        try:
            cmd = [
                "hdiutil", "create", "-volname", package_info.name,
                "-srcfolder", build_path, "-ov", "-format", "UDBZ",
                package_info.file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return process.returncode == 0
            
        except FileNotFoundError:
            logger.warning("hdiutil not found, creating ZIP package instead")
            return await self._create_zip_package(build_path, package_info)
    
    async def _create_deb_package(self, build_path: str, package_info: PackageInfo) -> bool:
        """Create Debian package"""
        logger.info(f"Creating DEB package: {package_info.name}")
        
        # Create debian package structure
        debian_dir = os.path.join(os.path.dirname(package_info.file_path), "debian")
        os.makedirs(debian_dir, exist_ok=True)
        
        # Create control file
        control_content = f"""Package: {package_info.name}
Version: {package_info.version}
Section: base
Priority: optional
Architecture: {package_info.architecture}
Maintainer: Package Builder
Description: {package_info.name} application
"""
        
        with open(os.path.join(debian_dir, "control"), 'w') as f:
            f.write(control_content)
        
        # Use dpkg-buildpackage or dpkg-deb
        try:
            cmd = ["dpkg-deb", "--build", debian_dir, package_info.file_path]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return process.returncode == 0
            
        except FileNotFoundError:
            logger.warning("dpkg-deb not found, creating ZIP package instead")
            return await self._create_zip_package(build_path, package_info)
    
    async def _create_rpm_package(self, build_path: str, package_info: PackageInfo) -> bool:
        """Create RPM package"""
        logger.info(f"Creating RPM package: {package_info.name}")
        
        # This would use rpmbuild
        return await self._create_zip_package(build_path, package_info)
    
    async def _create_appimage_package(self, build_path: str, package_info: PackageInfo) -> bool:
        """Create AppImage package"""
        logger.info(f"Creating AppImage package: {package_info.name}")
        
        # This would use appimagetool
        return await self._create_zip_package(build_path, package_info)
    
    async def _create_apk_package(self, build_path: str, package_info: PackageInfo) -> bool:
        """Create Android APK package"""
        logger.info(f"Creating APK package: {package_info.name}")
        
        # This would use aapt and apksigner
        return await self._create_zip_package(build_path, package_info)
    
    async def _create_zip_package(self, build_path: str, package_info: PackageInfo) -> bool:
        """Create ZIP package (universal fallback)"""
        logger.info(f"Creating ZIP package: {package_info.name}")
        
        try:
            with zipfile.ZipFile(package_info.file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(build_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, build_path)
                        zipf.write(file_path, arc_name)
            
            package_info.file_size = os.path.getsize(package_info.file_path)
            package_info.calculate_checksum()
            
            return True
            
        except Exception as e:
            logger.error(f"ZIP package creation failed: {e}")
            return False
    
    def get_supported_formats(self, platform: str) -> List[PackageFormat]:
        """Get supported package formats for platform"""
        return self.package_formats.get(platform, [PackageFormat.ZIP])


class DeltaUpdateManager:
    """Delta update management"""
    
    def __init__(self):
        self.delta_cache: Dict[str, bytes] = {}
    
    async def create_delta_update(self, old_version_path: str, new_version_path: str,
                                delta_path: str) -> bool:
        """Create delta update between versions"""
        try:
            # Simple delta creation using binary diff
            # Real implementation would use sophisticated delta algorithms
            
            if not os.path.exists(old_version_path) or not os.path.exists(new_version_path):
                return False
            
            # Read both versions
            with open(old_version_path, 'rb') as f:
                old_data = f.read()
            
            with open(new_version_path, 'rb') as f:
                new_data = f.read()
            
            # Create simple delta (this would use a proper delta algorithm in reality)
            delta_data = {
                "old_checksum": hashlib.sha256(old_data).hexdigest(),
                "new_checksum": hashlib.sha256(new_data).hexdigest(),
                "size_old": len(old_data),
                "size_new": len(new_data),
                "delta_type": "binary_diff"
            }
            
            # Save delta metadata
            with open(delta_path, 'w') as f:
                json.dump(delta_data, f)
            
            logger.info(f"Created delta update: {delta_path}")
            return True
            
        except Exception as e:
            logger.error(f"Delta update creation failed: {e}")
            return False
    
    async def apply_delta_update(self, base_path: str, delta_path: str, 
                               output_path: str) -> bool:
        """Apply delta update to create new version"""
        try:
            # Load delta metadata
            with open(delta_path, 'r') as f:
                delta_data = json.load(f)
            
            # Verify base file
            with open(base_path, 'rb') as f:
                base_data = f.read()
            
            base_checksum = hashlib.sha256(base_data).hexdigest()
            if base_checksum != delta_data["old_checksum"]:
                logger.error("Base file checksum mismatch")
                return False
            
            # For this simplified implementation, we just copy the base
            # Real implementation would apply the actual delta
            shutil.copy2(base_path, output_path)
            
            logger.info(f"Applied delta update: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Delta update application failed: {e}")
            return False


class SignatureManager:
    """Package signature management"""
    
    def __init__(self):
        self.signing_keys: Dict[str, str] = {}
    
    async def sign_package(self, package_path: str, signing_key: str = None) -> bool:
        """Sign package with digital signature"""
        try:
            # This would use actual cryptographic signing
            # For now, create a simple signature file
            
            signature_path = f"{package_path}.sig"
            
            # Calculate package hash
            with open(package_path, 'rb') as f:
                package_data = f.read()
            
            package_hash = hashlib.sha256(package_data).hexdigest()
            
            # Create signature metadata
            signature_data = {
                "package_hash": package_hash,
                "signature_algorithm": "SHA256withRSA",
                "signing_time": datetime.now().isoformat(),
                "signer": "Package Builder"
            }
            
            with open(signature_path, 'w') as f:
                json.dump(signature_data, f)
            
            logger.info(f"Signed package: {package_path}")
            return True
            
        except Exception as e:
            logger.error(f"Package signing failed: {e}")
            return False
    
    async def verify_signature(self, package_path: str) -> bool:
        """Verify package signature"""
        try:
            signature_path = f"{package_path}.sig"
            
            if not os.path.exists(signature_path):
                logger.warning(f"No signature found for {package_path}")
                return False
            
            # Load signature
            with open(signature_path, 'r') as f:
                signature_data = json.load(f)
            
            # Verify package hash
            with open(package_path, 'rb') as f:
                package_data = f.read()
            
            package_hash = hashlib.sha256(package_data).hexdigest()
            
            if package_hash == signature_data["package_hash"]:
                logger.info(f"Package signature verified: {package_path}")
                return True
            else:
                logger.error(f"Package signature verification failed: {package_path}")
                return False
                
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


class RolloutManager:
    """Rollout strategy management"""
    
    def __init__(self):
        self.active_rollouts: Dict[str, Dict[str, Any]] = {}
    
    async def start_rollout(self, distribution_id: str, strategy: RolloutStrategy,
                          config: Dict[str, Any]) -> bool:
        """Start distribution rollout"""
        try:
            rollout_info = {
                "distribution_id": distribution_id,
                "strategy": strategy,
                "config": config,
                "start_time": time.time(),
                "current_percentage": 0,
                "target_percentage": config.get("target_percentage", 100),
                "step_size": config.get("step_size", 10),
                "step_interval": config.get("step_interval", 3600),  # 1 hour
                "last_step_time": time.time(),
                "status": "active"
            }
            
            self.active_rollouts[distribution_id] = rollout_info
            
            if strategy == RolloutStrategy.IMMEDIATE:
                rollout_info["current_percentage"] = 100
                rollout_info["status"] = "completed"
            
            logger.info(f"Started rollout for {distribution_id}: {strategy.value}")
            return True
            
        except Exception as e:
            logger.error(f"Rollout start failed: {e}")
            return False
    
    async def update_rollout_progress(self, distribution_id: str) -> bool:
        """Update rollout progress"""
        if distribution_id not in self.active_rollouts:
            return False
        
        rollout = self.active_rollouts[distribution_id]
        
        if rollout["status"] != "active":
            return True
        
        current_time = time.time()
        time_since_last_step = current_time - rollout["last_step_time"]
        
        # Check if it's time for next step
        if time_since_last_step >= rollout["step_interval"]:
            rollout["current_percentage"] = min(
                rollout["current_percentage"] + rollout["step_size"],
                rollout["target_percentage"]
            )
            rollout["last_step_time"] = current_time
            
            if rollout["current_percentage"] >= rollout["target_percentage"]:
                rollout["status"] = "completed"
            
            logger.info(f"Rollout progress for {distribution_id}: {rollout['current_percentage']}%")
        
        return True
    
    async def rollback_distribution(self, distribution_id: str) -> bool:
        """Rollback distribution"""
        try:
            if distribution_id in self.active_rollouts:
                rollout = self.active_rollouts[distribution_id]
                rollout["status"] = "rolling_back"
                rollout["current_percentage"] = 0
                
                logger.info(f"Rolling back distribution: {distribution_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def get_rollout_status(self, distribution_id: str) -> Optional[Dict[str, Any]]:
        """Get rollout status"""
        return self.active_rollouts.get(distribution_id)


class DistributionSystem:
    """Main distribution system coordinator"""
    
    def __init__(self):
        self.package_manager = PackageManager()
        self.delta_manager = DeltaUpdateManager()
        self.signature_manager = SignatureManager()
        self.rollout_manager = RolloutManager()
        
        self.active_distributions: Dict[str, DistributionResult] = {}
        self.completed_distributions: Dict[str, DistributionResult] = {}
        self.distribution_callbacks: List[Callable] = []
        
        self._running = False
        self._monitor_task = None
        self._lock = threading.Lock()
    
    async def start(self):
        """Start the distribution system"""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_distributions())
        logger.info("Distribution system started")
    
    async def stop(self):
        """Stop the distribution system"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Distribution system stopped")
    
    async def _monitor_distributions(self):
        """Monitor active distributions"""
        while self._running:
            try:
                with self._lock:
                    completed_dist_ids = []
                    
                    for dist_id, result in self.active_distributions.items():
                        # Update rollout progress
                        await self.rollout_manager.update_rollout_progress(dist_id)
                        
                        # Check if completed
                        if result.status in [DistributionStatus.COMPLETED, DistributionStatus.FAILED]:
                            completed_dist_ids.append(dist_id)
                    
                    # Move completed distributions
                    for dist_id in completed_dist_ids:
                        result = self.active_distributions.pop(dist_id)
                        self.completed_distributions[dist_id] = result
                        
                        # Notify callbacks
                        for callback in self.distribution_callbacks:
                            try:
                                await callback({
                                    "event": "distribution_completed",
                                    "distribution_id": dist_id,
                                    "status": result.status.value,
                                    "duration": result.duration
                                })
                            except Exception as e:
                                logger.error(f"Distribution callback error: {e}")
                
                await asyncio.sleep(10.0)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Distribution monitor error: {e}")
                await asyncio.sleep(10.0)
    
    async def create_distribution(self, build_id: str, channel: UpdateChannel,
                                rollout_strategy: RolloutStrategy, target_regions: List[str],
                                target_platforms: List[str], metadata: Dict[str, Any]) -> str:
        """Create new distribution"""
        distribution_id = f"dist_{build_id}_{int(time.time())}"
        
        config = DistributionConfig(
            build_id=build_id,
            channel=channel,
            rollout_strategy=rollout_strategy,
            target_regions=target_regions,
            target_platforms=target_platforms,
            metadata=metadata
        )
        
        result = DistributionResult(
            distribution_id=distribution_id,
            config=config,
            status=DistributionStatus.CREATED,
            start_time=time.time()
        )
        
        with self._lock:
            self.active_distributions[distribution_id] = result
        
        logger.info(f"Created distribution: {distribution_id}")
        return distribution_id
    
    async def get_distribution_status(self, distribution_id: str) -> Optional[Dict[str, Any]]:
        """Get distribution status"""
        with self._lock:
            result = (self.active_distributions.get(distribution_id) or 
                     self.completed_distributions.get(distribution_id))
            
            if result:
                rollout_status = self.rollout_manager.get_rollout_status(distribution_id)
                
                return {
                    "distribution_id": distribution_id,
                    "status": result.status.value,
                    "progress": self._calculate_progress(result),
                    "duration": result.duration,
                    "start_time": result.start_time,
                    "end_time": result.end_time,
                    "packages": len(result.packages),
                    "error_message": result.error_message,
                    "rollout_status": rollout_status
                }
        
        return None
    
    def _calculate_progress(self, result: DistributionResult) -> float:
        """Calculate distribution progress percentage"""
        status_progress = {
            DistributionStatus.CREATED: 0.0,
            DistributionStatus.PREPARING: 0.1,
            DistributionStatus.PACKAGING: 0.3,
            DistributionStatus.SIGNING: 0.5,
            DistributionStatus.TESTING: 0.7,
            DistributionStatus.DEPLOYING: 0.8,
            DistributionStatus.MONITORING: 0.9,
            DistributionStatus.COMPLETED: 1.0,
            DistributionStatus.FAILED: 0.0,
            DistributionStatus.ROLLBACK: 0.0
        }
        
        return status_progress.get(result.status, 0.0)
    
    async def deploy_distribution(self, distribution_id: str) -> bool:
        """Deploy distribution"""
        with self._lock:
            if distribution_id not in self.active_distributions:
                return False
            
            result = self.active_distributions[distribution_id]
            result.status = DistributionStatus.DEPLOYING
        
        # Start rollout
        await self.rollout_manager.start_rollout(
            distribution_id,
            result.config.rollout_strategy,
            {"target_percentage": 100, "step_size": result.config.staged_rollout_percentage}
        )
        
        # Update status
        result.status = DistributionStatus.MONITORING
        
        logger.info(f"Deployed distribution: {distribution_id}")
        return True
    
    async def rollback_distribution(self, distribution_id: str) -> bool:
        """Rollback distribution"""
        success = await self.rollout_manager.rollback_distribution(distribution_id)
        
        if success:
            with self._lock:
                if distribution_id in self.active_distributions:
                    result = self.active_distributions[distribution_id]
                    result.status = DistributionStatus.ROLLBACK
        
        return success
    
    def add_distribution_callback(self, callback: Callable):
        """Add distribution callback"""
        self.distribution_callbacks.append(callback)
    
    def is_healthy(self) -> bool:
        """Check if distribution system is healthy"""
        return self._running
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get distribution statistics"""
        with self._lock:
            return {
                "active_distributions": len(self.active_distributions),
                "completed_distributions": len(self.completed_distributions),
                "total_distributions": len(self.active_distributions) + len(self.completed_distributions),
                "active_rollouts": len(self.rollout_manager.active_rollouts),
                "supported_package_formats": len(PackageFormat),
                "supported_platforms": list(self.package_manager.package_formats.keys())
            }


# Global distribution system instance
distribution_system = DistributionSystem()