"""
Over-The-Air (OTA) Update System
"""

import uuid
import hashlib
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import subprocess

from ..database import OTAUpdate, Device, DeviceType, OTAUpdateStatus, DeviceStatus


class OTAUpdateManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.firmware_storage_path = Path("/tmp/edge_programmer_ota")
        self.firmware_storage_path.mkdir(exist_ok=True)
        
        # OTA server endpoints for different device types
        self.ota_endpoints = {
            DeviceType.ESP32: {
                "base_url": "http://localhost:8339/ota/esp32",
                "manifest_path": "/manifest.json",
                "firmware_path": "/firmware/{version}/firmware.bin"
            },
            DeviceType.ESP8266: {
                "base_url": "http://localhost:8339/ota/esp8266",
                "manifest_path": "/manifest.json", 
                "firmware_path": "/firmware/{version}/firmware.bin"
            }
        }
        
        # Device-specific OTA configurations
        self.ota_configs = {
            DeviceType.ESP32: {
                "partition_scheme": "default",
                "flash_size": "4MB",
                "flash_mode": "DIO",
                "flash_freq": "40m",
                "bootloader": "esp32_bootloader.bin",
                "partitions": "partitions.bin"
            },
            DeviceType.ESP8266: {
                "partition_scheme": "minimal",
                "flash_size": "4MB",
                "flash_mode": "DOUT",
                "flash_freq": "40m",
                "bootloader": "esp8266_bootloader.bin"
            }
        }
    
    async def create_firmware_package(
        self,
        device_type: DeviceType,
        version: str,
        firmware_data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a firmware package for OTA distribution"""
        
        if device_type not in [DeviceType.ESP32, DeviceType.ESP8266]:
            raise ValueError(f"OTA updates not supported for {device_type}")
        
        # Create version directory
        version_dir = self.firmware_storage_path / device_type.value / version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Save firmware binary
        firmware_file = version_dir / "firmware.bin"
        async with aiofiles.open(firmware_file, 'wb') as f:
            await f.write(firmware_data)
        
        # Calculate checksum
        checksum = hashlib.sha256(firmware_data).hexdigest()
        
        # Create manifest
        manifest = {
            "version": version,
            "device_type": device_type.value,
            "firmware_size": len(firmware_data),
            "checksum": checksum,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "download_url": f"{self.ota_endpoints[device_type]['base_url']}/firmware/{version}/firmware.bin"
        }
        
        # Save manifest
        manifest_file = version_dir / "manifest.json"
        async with aiofiles.open(manifest_file, 'w') as f:
            import json
            await f.write(json.dumps(manifest, indent=2))
        
        # Update global manifest
        await self._update_global_manifest(device_type, version, manifest)
        
        return str(firmware_file)
    
    async def _update_global_manifest(
        self,
        device_type: DeviceType,
        version: str,
        firmware_manifest: Dict[str, Any]
    ):
        """Update global manifest with new firmware version"""
        
        global_manifest_file = self.firmware_storage_path / device_type.value / "manifest.json"
        
        # Load existing manifest or create new one
        global_manifest = {
            "device_type": device_type.value,
            "latest_version": version,
            "updated_at": datetime.utcnow().isoformat(),
            "versions": {}
        }
        
        if global_manifest_file.exists():
            async with aiofiles.open(global_manifest_file, 'r') as f:
                content = await f.read()
                if content.strip():
                    import json
                    global_manifest = json.loads(content)
        
        # Add new version
        global_manifest["versions"][version] = firmware_manifest
        global_manifest["latest_version"] = version
        global_manifest["updated_at"] = datetime.utcnow().isoformat()
        
        # Save updated manifest
        async with aiofiles.open(global_manifest_file, 'w') as f:
            import json
            await f.write(json.dumps(global_manifest, indent=2))
    
    async def schedule_ota_update(
        self,
        device_id: uuid.UUID,
        firmware_version: str,
        force_update: bool = False,
        schedule_time: Optional[datetime] = None
    ) -> uuid.UUID:
        """Schedule an OTA update for a device"""
        
        # Get device info
        result = await self.session.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        if device.device_type not in [DeviceType.ESP32, DeviceType.ESP8266]:
            raise ValueError(f"OTA updates not supported for {device.device_type}")
        
        # Check if firmware version exists
        firmware_path = (self.firmware_storage_path / 
                        device.device_type.value / 
                        firmware_version / 
                        "firmware.bin")
        
        if not firmware_path.exists():
            raise ValueError(f"Firmware version {firmware_version} not found for {device.device_type}")
        
        # Load firmware manifest
        manifest_path = firmware_path.parent / "manifest.json"
        async with aiofiles.open(manifest_path, 'r') as f:
            import json
            manifest = json.loads(await f.read())
        
        # Create OTA update record
        ota_update = OTAUpdate(
            firmware_version=firmware_version,
            firmware_url=manifest["download_url"],
            checksum=manifest["checksum"],
            device_id=device_id,
            started_at=schedule_time
        )
        
        self.session.add(ota_update)
        await self.session.commit()
        await self.session.refresh(ota_update)
        
        # If immediate update, trigger now
        if not schedule_time or schedule_time <= datetime.utcnow():
            asyncio.create_task(self._execute_ota_update(ota_update.id))
        
        return ota_update.id
    
    async def _execute_ota_update(self, update_id: uuid.UUID):
        """Execute OTA update process"""
        
        result = await self.session.execute(
            select(OTAUpdate).where(OTAUpdate.id == update_id)
        )
        ota_update = result.scalar_one_or_none()
        
        if not ota_update:
            return
        
        try:
            # Update status to downloading
            await self.session.execute(
                update(OTAUpdate)
                .where(OTAUpdate.id == update_id)
                .values(
                    status=OTAUpdateStatus.DOWNLOADING,
                    started_at=datetime.utcnow()
                )
            )
            await self.session.commit()
            
            # Get device info
            device_result = await self.session.execute(
                select(Device).where(Device.id == ota_update.device_id)
            )
            device = device_result.scalar_one()
            
            # Update device status
            await self.session.execute(
                update(Device)
                .where(Device.id == ota_update.device_id)
                .values(status=DeviceStatus.UPDATING)
            )
            await self.session.commit()
            
            # Send OTA update command to device
            success = await self._send_ota_command(device, ota_update)
            
            if success:
                # Monitor update progress
                await self._monitor_update_progress(update_id)
            else:
                # Update failed
                await self.session.execute(
                    update(OTAUpdate)
                    .where(OTAUpdate.id == update_id)
                    .values(
                        status=OTAUpdateStatus.FAILED,
                        error_message="Failed to initiate OTA update",
                        completed_at=datetime.utcnow()
                    )
                )
                await self.session.commit()
                
                # Restore device status
                await self.session.execute(
                    update(Device)
                    .where(Device.id == ota_update.device_id)
                    .values(status=DeviceStatus.ONLINE)
                )
                await self.session.commit()
        
        except Exception as e:
            await self.session.execute(
                update(OTAUpdate)
                .where(OTAUpdate.id == update_id)
                .values(
                    status=OTAUpdateStatus.FAILED,
                    error_message=str(e),
                    completed_at=datetime.utcnow()
                )
            )
            await self.session.commit()
    
    async def _send_ota_command(self, device: Device, ota_update: OTAUpdate) -> bool:
        """Send OTA update command to device"""
        
        if not device.ip_address:
            # Try to get IP from ActiveLog or use broadcast
            return await self._send_ota_via_activelog(device, ota_update)
        
        try:
            # Send HTTP request to device's OTA endpoint
            update_payload = {
                "command": "ota_update",
                "firmware_url": ota_update.firmware_url,
                "firmware_version": ota_update.firmware_version,
                "checksum": ota_update.checksum,
                "update_id": str(ota_update.id)
            }
            
            device_ota_url = f"http://{device.ip_address}/ota/update"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    device_ota_url,
                    json=update_payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("status") == "accepted"
                    else:
                        return False
        
        except Exception as e:
            print(f"Failed to send OTA command to {device.ip_address}: {str(e)}")
            return False
    
    async def _send_ota_via_activelog(self, device: Device, ota_update: OTAUpdate) -> bool:
        """Send OTA update command via ActiveLog platform"""
        
        activelog_device_id = device.metadata.get("activelog_device_id")
        if not activelog_device_id:
            return False
        
        try:
            # Get user for API key
            user_result = await self.session.execute(
                select(User).where(User.id == device.owner_id)
            )
            user = user_result.scalar_one()
            
            if not user.api_key:
                return False
            
            # Send command via ActiveLog
            command_payload = {
                "command": "ota_update",
                "parameters": {
                    "firmware_url": ota_update.firmware_url,
                    "firmware_version": ota_update.firmware_version,
                    "checksum": ota_update.checksum,
                    "update_id": str(ota_update.id)
                }
            }
            
            headers = {"Authorization": f"Bearer {user.api_key}"}
            activelog_command_url = f"https://api.activelog.com/v1/devices/{activelog_device_id}/commands"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    activelog_command_url,
                    json=command_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    return response.status == 200
        
        except Exception as e:
            print(f"Failed to send OTA command via ActiveLog: {str(e)}")
            return False
    
    async def _monitor_update_progress(self, update_id: uuid.UUID):
        """Monitor OTA update progress"""
        
        max_wait_time = 300  # 5 minutes
        check_interval = 10   # 10 seconds
        elapsed = 0
        
        while elapsed < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed += check_interval
            
            # Check if device reported progress
            result = await self.session.execute(
                select(OTAUpdate).where(OTAUpdate.id == update_id)
            )
            ota_update = result.scalar_one_or_none()
            
            if not ota_update:
                break
            
            if ota_update.status == OTAUpdateStatus.COMPLETED:
                # Update successful
                await self._finalize_successful_update(update_id)
                break
            elif ota_update.status == OTAUpdateStatus.FAILED:
                # Update failed
                await self._handle_failed_update(update_id)
                break
            elif ota_update.progress > 0:
                # Update in progress
                print(f"OTA Update {update_id}: {ota_update.progress:.1f}% complete")
        
        # Timeout handling
        if elapsed >= max_wait_time:
            await self.session.execute(
                update(OTAUpdate)
                .where(OTAUpdate.id == update_id)
                .values(
                    status=OTAUpdateStatus.FAILED,
                    error_message="Update timeout",
                    completed_at=datetime.utcnow()
                )
            )
            await self.session.commit()
    
    async def _finalize_successful_update(self, update_id: uuid.UUID):
        """Finalize successful OTA update"""
        
        result = await self.session.execute(
            select(OTAUpdate).where(OTAUpdate.id == update_id)
        )
        ota_update = result.scalar_one()
        
        # Update device firmware version and status
        await self.session.execute(
            update(Device)
            .where(Device.id == ota_update.device_id)
            .values(
                firmware_version=ota_update.firmware_version,
                status=DeviceStatus.ONLINE
            )
        )
        
        # Mark update as completed
        await self.session.execute(
            update(OTAUpdate)
            .where(OTAUpdate.id == update_id)
            .values(
                status=OTAUpdateStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                progress=100.0
            )
        )
        await self.session.commit()
        
        print(f"✓ OTA Update {update_id} completed successfully")
    
    async def _handle_failed_update(self, update_id: uuid.UUID):
        """Handle failed OTA update"""
        
        result = await self.session.execute(
            select(OTAUpdate).where(OTAUpdate.id == update_id)
        )
        ota_update = result.scalar_one()
        
        # Restore device status
        await self.session.execute(
            update(Device)
            .where(Device.id == ota_update.device_id)
            .values(status=DeviceStatus.ONLINE)
        )
        await self.session.commit()
        
        print(f"✗ OTA Update {update_id} failed: {ota_update.error_message}")
    
    async def update_progress(
        self,
        update_id: uuid.UUID,
        progress: float,
        status: Optional[OTAUpdateStatus] = None,
        error_message: Optional[str] = None
    ):
        """Update OTA progress (called by device or monitoring system)"""
        
        update_values = {"progress": progress}
        
        if status:
            update_values["status"] = status
            
            if status in [OTAUpdateStatus.COMPLETED, OTAUpdateStatus.FAILED]:
                update_values["completed_at"] = datetime.utcnow()
        
        if error_message:
            update_values["error_message"] = error_message
        
        await self.session.execute(
            update(OTAUpdate)
            .where(OTAUpdate.id == update_id)
            .values(**update_values)
        )
        await self.session.commit()
    
    async def rollback_update(self, update_id: uuid.UUID) -> bool:
        """Rollback a failed OTA update"""
        
        result = await self.session.execute(
            select(OTAUpdate).where(OTAUpdate.id == update_id)
        )
        ota_update = result.scalar_one_or_none()
        
        if not ota_update:
            return False
        
        # Update status to rollback
        await self.session.execute(
            update(OTAUpdate)
            .where(OTAUpdate.id == update_id)
            .values(
                status=OTAUpdateStatus.ROLLBACK,
                error_message="Manual rollback initiated"
            )
        )
        await self.session.commit()
        
        # Get device info
        device_result = await self.session.execute(
            select(Device).where(Device.id == ota_update.device_id)
        )
        device = device_result.scalar_one()
        
        # Find previous firmware version
        previous_version = await self._get_previous_firmware_version(
            device.device_type, ota_update.firmware_version
        )
        
        if previous_version:
            # Schedule rollback to previous version
            rollback_id = await self.schedule_ota_update(
                ota_update.device_id, 
                previous_version,
                force_update=True
            )
            return rollback_id is not None
        
        return False
    
    async def _get_previous_firmware_version(
        self,
        device_type: DeviceType,
        current_version: str
    ) -> Optional[str]:
        """Get the previous firmware version for rollback"""
        
        manifest_file = self.firmware_storage_path / device_type.value / "manifest.json"
        
        if not manifest_file.exists():
            return None
        
        try:
            async with aiofiles.open(manifest_file, 'r') as f:
                import json
                manifest = json.loads(await f.read())
            
            versions = list(manifest.get("versions", {}).keys())
            versions.sort(reverse=True)  # Most recent first
            
            # Find current version and return the previous one
            if current_version in versions:
                current_index = versions.index(current_version)
                if current_index + 1 < len(versions):
                    return versions[current_index + 1]
            
            return None
        
        except Exception as e:
            print(f"Error getting previous firmware version: {str(e)}")
            return None
    
    async def get_ota_history(
        self,
        device_id: uuid.UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get OTA update history for a device"""
        
        result = await self.session.execute(
            select(OTAUpdate)
            .where(OTAUpdate.device_id == device_id)
            .order_by(OTAUpdate.created_at.desc())
            .limit(limit)
        )
        
        updates = result.scalars().all()
        
        return [
            {
                "id": str(update.id),
                "firmware_version": update.firmware_version,
                "status": update.status.value,
                "progress": update.progress,
                "started_at": update.started_at.isoformat() if update.started_at else None,
                "completed_at": update.completed_at.isoformat() if update.completed_at else None,
                "error_message": update.error_message
            }
            for update in updates
        ]
    
    async def get_available_firmware_versions(
        self,
        device_type: DeviceType
    ) -> List[Dict[str, Any]]:
        """Get available firmware versions for a device type"""
        
        manifest_file = self.firmware_storage_path / device_type.value / "manifest.json"
        
        if not manifest_file.exists():
            return []
        
        try:
            async with aiofiles.open(manifest_file, 'r') as f:
                import json
                manifest = json.loads(await f.read())
            
            versions = []
            for version, info in manifest.get("versions", {}).items():
                versions.append({
                    "version": version,
                    "size": info.get("firmware_size", 0),
                    "checksum": info.get("checksum", ""),
                    "created_at": info.get("created_at", ""),
                    "metadata": info.get("metadata", {})
                })
            
            # Sort by version (assuming semantic versioning)
            versions.sort(key=lambda x: x["created_at"], reverse=True)
            return versions
        
        except Exception as e:
            print(f"Error reading firmware manifest: {str(e)}")
            return []
    
    async def cleanup_old_firmware(self, keep_versions: int = 5):
        """Clean up old firmware versions to save storage space"""
        
        for device_type in [DeviceType.ESP32, DeviceType.ESP8266]:
            device_dir = self.firmware_storage_path / device_type.value
            
            if not device_dir.exists():
                continue
            
            # Get all version directories
            version_dirs = [d for d in device_dir.iterdir() 
                          if d.is_dir() and d.name != "manifest.json"]
            
            # Sort by modification time (newest first)
            version_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the specified number of versions
            for old_dir in version_dirs[keep_versions:]:
                try:
                    import shutil
                    shutil.rmtree(old_dir)
                    print(f"Cleaned up old firmware version: {old_dir.name}")
                except Exception as e:
                    print(f"Failed to clean up {old_dir}: {str(e)}")
            
            # Update manifest to remove references to deleted versions
            await self._cleanup_manifest(device_type, version_dirs[:keep_versions])
    
    async def _cleanup_manifest(
        self,
        device_type: DeviceType,
        kept_dirs: List[Path]
    ):
        """Update manifest after cleaning up old versions"""
        
        manifest_file = self.firmware_storage_path / device_type.value / "manifest.json"
        
        if not manifest_file.exists():
            return
        
        try:
            async with aiofiles.open(manifest_file, 'r') as f:
                import json
                manifest = json.loads(await f.read())
            
            kept_versions = {d.name for d in kept_dirs}
            
            # Filter versions to only include kept ones
            manifest["versions"] = {
                version: info
                for version, info in manifest.get("versions", {}).items()
                if version in kept_versions
            }
            
            # Update latest version if necessary
            if manifest["versions"]:
                latest = max(manifest["versions"].keys(),
                           key=lambda v: manifest["versions"][v].get("created_at", ""))
                manifest["latest_version"] = latest
            
            # Save updated manifest
            async with aiofiles.open(manifest_file, 'w') as f:
                await f.write(json.dumps(manifest, indent=2))
        
        except Exception as e:
            print(f"Failed to update manifest after cleanup: {str(e)}")