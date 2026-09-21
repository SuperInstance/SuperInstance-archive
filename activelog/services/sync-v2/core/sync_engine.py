#!/usr/bin/env python3
"""
ActiveLog.ai Sync Engine v2

Core synchronization engine with device-aware sync, conflict resolution, and real-time collaboration.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import hashlib
import sqlite3
from contextlib import asynccontextmanager

class DeviceType(Enum):
    PHONE = "phone"
    TABLET = "tablet"
    DESKTOP = "desktop"
    WEB = "web"
    IOT = "iot"

class DeviceCapabilities(Enum):
    MINIMAL = "minimal"      # IoT devices, limited processing
    MOBILE = "mobile"        # Phones, tablets - limited storage/bandwidth
    STANDARD = "standard"    # Basic desktop/web
    FULL = "full"           # High-end devices with full capabilities

class SyncStatus(Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    ERROR = "error"
    PAUSED = "paused"

class ContentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    DATA = "data"

@dataclass
class DeviceInfo:
    """Device information and capabilities"""
    device_id: str
    device_type: DeviceType
    capabilities: DeviceCapabilities
    name: str
    user_id: str
    platform: str  # ios, android, windows, macos, linux, web
    version: str
    last_seen: str
    is_online: bool = False
    sync_enabled: bool = True
    selective_sync_rules: List[str] = None
    bandwidth_limit: Optional[int] = None  # bytes per second
    storage_limit: Optional[int] = None    # bytes
    battery_level: Optional[int] = None    # percentage
    network_type: str = "unknown"  # wifi, cellular, ethernet

    def __post_init__(self):
        if self.selective_sync_rules is None:
            self.selective_sync_rules = []

@dataclass
class SyncItem:
    """Item to be synchronized"""
    item_id: str
    content_type: ContentType
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: str
    modified_at: str
    version: int
    device_id: str
    user_id: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    priority: int = 5  # 1-10, higher = more priority
    tags: List[str] = None
    permissions: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.permissions is None:
            self.permissions = {}

@dataclass
class SyncConflict:
    """Sync conflict information"""
    conflict_id: str
    item_id: str
    conflicting_versions: List[SyncItem]
    conflict_type: str  # "concurrent_edit", "delete_edit", "move_move"
    detected_at: str
    resolution_strategy: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_data: Optional[Dict[str, Any]] = None

class SyncDatabase:
    """SQLite database for sync state management"""
    
    def __init__(self, db_path: str = "sync_v2.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_type TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                version TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                is_online BOOLEAN DEFAULT FALSE,
                sync_enabled BOOLEAN DEFAULT TRUE,
                selective_sync_rules TEXT,
                bandwidth_limit INTEGER,
                storage_limit INTEGER,
                battery_level INTEGER,
                network_type TEXT DEFAULT 'unknown',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Sync items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_items (
                item_id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                version INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                file_path TEXT,
                file_size INTEGER,
                checksum TEXT,
                priority INTEGER DEFAULT 5,
                tags TEXT,
                permissions TEXT,
                is_deleted BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (device_id) REFERENCES devices (device_id)
            )
        ''')
        
        # Sync state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_state (
                device_id TEXT,
                item_id TEXT,
                last_sync_version INTEGER,
                last_sync_time TEXT,
                sync_status TEXT DEFAULT 'pending',
                error_message TEXT,
                PRIMARY KEY (device_id, item_id),
                FOREIGN KEY (device_id) REFERENCES devices (device_id),
                FOREIGN KEY (item_id) REFERENCES sync_items (item_id)
            )
        ''')
        
        # Conflicts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conflicts (
                conflict_id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                conflicting_versions TEXT NOT NULL,
                conflict_type TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                resolution_strategy TEXT,
                resolved_at TEXT,
                resolved_by TEXT,
                resolution_data TEXT,
                FOREIGN KEY (item_id) REFERENCES sync_items (item_id)
            )
        ''')
        
        # Sync logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                item_id TEXT,
                status TEXT NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL,
                duration_ms INTEGER,
                bytes_transferred INTEGER
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_user ON sync_items(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_device ON sync_items(device_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_modified ON sync_items(modified_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_device ON sync_state(device_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conflicts_item ON conflicts(item_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_device ON sync_logs(device_id)')
        
        conn.commit()
        conn.close()
    
    def add_device(self, device: DeviceInfo):
        """Add or update device"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO devices 
            (device_id, device_type, capabilities, name, user_id, platform, version,
             last_seen, is_online, sync_enabled, selective_sync_rules, bandwidth_limit,
             storage_limit, battery_level, network_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM devices WHERE device_id = ?), ?), ?)
        ''', (
            device.device_id, device.device_type.value, device.capabilities.value,
            device.name, device.user_id, device.platform, device.version,
            device.last_seen, device.is_online, device.sync_enabled,
            json.dumps(device.selective_sync_rules), device.bandwidth_limit,
            device.storage_limit, device.battery_level, device.network_type,
            device.device_id, now, now
        ))
        
        conn.commit()
        conn.close()
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return DeviceInfo(
            device_id=row[0],
            device_type=DeviceType(row[1]),
            capabilities=DeviceCapabilities(row[2]),
            name=row[3],
            user_id=row[4],
            platform=row[5],
            version=row[6],
            last_seen=row[7],
            is_online=bool(row[8]),
            sync_enabled=bool(row[9]),
            selective_sync_rules=json.loads(row[10]) if row[10] else [],
            bandwidth_limit=row[11],
            storage_limit=row[12],
            battery_level=row[13],
            network_type=row[14] or "unknown"
        )
    
    def get_user_devices(self, user_id: str) -> List[DeviceInfo]:
        """Get all devices for user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE user_id = ? ORDER BY last_seen DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        devices = []
        for row in rows:
            devices.append(DeviceInfo(
                device_id=row[0],
                device_type=DeviceType(row[1]),
                capabilities=DeviceCapabilities(row[2]),
                name=row[3],
                user_id=row[4],
                platform=row[5],
                version=row[6],
                last_seen=row[7],
                is_online=bool(row[8]),
                sync_enabled=bool(row[9]),
                selective_sync_rules=json.loads(row[10]) if row[10] else [],
                bandwidth_limit=row[11],
                storage_limit=row[12],
                battery_level=row[13],
                network_type=row[14] or "unknown"
            ))
        
        return devices
    
    def add_sync_item(self, item: SyncItem):
        """Add or update sync item"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sync_items 
            (item_id, content_type, data, metadata, created_at, modified_at, version,
             device_id, user_id, file_path, file_size, checksum, priority, tags, permissions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.item_id, item.content_type.value, json.dumps(item.data),
            json.dumps(item.metadata), item.created_at, item.modified_at,
            item.version, item.device_id, item.user_id, item.file_path,
            item.file_size, item.checksum, item.priority,
            json.dumps(item.tags), json.dumps(item.permissions)
        ))
        
        conn.commit()
        conn.close()
    
    def get_sync_item(self, item_id: str) -> Optional[SyncItem]:
        """Get sync item by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sync_items WHERE item_id = ? AND is_deleted = FALSE', (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return SyncItem(
            item_id=row[0],
            content_type=ContentType(row[1]),
            data=json.loads(row[2]),
            metadata=json.loads(row[3]),
            created_at=row[4],
            modified_at=row[5],
            version=row[6],
            device_id=row[7],
            user_id=row[8],
            file_path=row[9],
            file_size=row[10],
            checksum=row[11],
            priority=row[12],
            tags=json.loads(row[13]) if row[13] else [],
            permissions=json.loads(row[14]) if row[14] else {}
        )
    
    def get_items_for_sync(self, device_id: str, user_id: str, limit: int = 100) -> List[SyncItem]:
        """Get items that need to be synced to device"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get items that are newer than last sync or haven't been synced
        cursor.execute('''
            SELECT si.* FROM sync_items si
            LEFT JOIN sync_state ss ON si.item_id = ss.item_id AND ss.device_id = ?
            WHERE si.user_id = ? AND si.is_deleted = FALSE
            AND (ss.last_sync_version IS NULL OR si.version > ss.last_sync_version)
            ORDER BY si.priority DESC, si.modified_at DESC
            LIMIT ?
        ''', (device_id, user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        items = []
        for row in rows:
            items.append(SyncItem(
                item_id=row[0],
                content_type=ContentType(row[1]),
                data=json.loads(row[2]),
                metadata=json.loads(row[3]),
                created_at=row[4],
                modified_at=row[5],
                version=row[6],
                device_id=row[7],
                user_id=row[8],
                file_path=row[9],
                file_size=row[10],
                checksum=row[11],
                priority=row[12],
                tags=json.loads(row[13]) if row[13] else [],
                permissions=json.loads(row[14]) if row[14] else {}
            ))
        
        return items
    
    def update_sync_state(self, device_id: str, item_id: str, version: int, status: str = "synced"):
        """Update sync state for device and item"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sync_state 
            (device_id, item_id, last_sync_version, last_sync_time, sync_status)
            VALUES (?, ?, ?, ?, ?)
        ''', (device_id, item_id, version, datetime.now().isoformat(), status))
        
        conn.commit()
        conn.close()
    
    def add_conflict(self, conflict: SyncConflict):
        """Add sync conflict"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO conflicts
            (conflict_id, item_id, conflicting_versions, conflict_type, detected_at,
             resolution_strategy, resolved_at, resolved_by, resolution_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conflict.conflict_id, conflict.item_id,
            json.dumps([asdict(v) for v in conflict.conflicting_versions]),
            conflict.conflict_type, conflict.detected_at,
            conflict.resolution_strategy, conflict.resolved_at,
            conflict.resolved_by, json.dumps(conflict.resolution_data) if conflict.resolution_data else None
        ))
        
        conn.commit()
        conn.close()
    
    def log_sync_operation(self, device_id: str, operation: str, status: str, 
                          item_id: str = None, message: str = None, duration_ms: int = None,
                          bytes_transferred: int = None):
        """Log sync operation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sync_logs 
            (device_id, operation, item_id, status, message, timestamp, duration_ms, bytes_transferred)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (device_id, operation, item_id, status, message, datetime.now().isoformat(),
              duration_ms, bytes_transferred))
        
        conn.commit()
        conn.close()

class SyncEngine:
    """Main synchronization engine"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.database = SyncDatabase(self.config.get('database_path', 'sync_v2.db'))
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.get('log_level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Sync configuration
        self.sync_interval = self.config.get('sync_interval', 30)
        self.max_concurrent_syncs = self.config.get('max_concurrent_syncs', 5)
        self.conflict_resolution_strategy = self.config.get('conflict_resolution_strategy', 'manual')
        
        # State
        self.running = False
        self.active_syncs: Set[str] = set()
        self.sync_semaphore = asyncio.Semaphore(self.max_concurrent_syncs)
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Real-time collaboration
        self.collaboration_sessions: Dict[str, Any] = {}
        self.presence_data: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start the sync engine"""
        self.running = True
        self.logger.info("Starting Sync Engine v2...")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._sync_loop()),
            asyncio.create_task(self._presence_loop()),
            asyncio.create_task(self._cleanup_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.running = False
            self.logger.info("Sync engine stopped")
    
    def register_device(self, device_id: str, device_type: DeviceType, capabilities: DeviceCapabilities,
                       name: str, user_id: str, platform: str, version: str = "1.0.0") -> DeviceInfo:
        """Register a new device"""
        device = DeviceInfo(
            device_id=device_id,
            device_type=device_type,
            capabilities=capabilities,
            name=name,
            user_id=user_id,
            platform=platform,
            version=version,
            last_seen=datetime.now().isoformat(),
            is_online=True
        )
        
        self.database.add_device(device)
        self.logger.info(f"Registered device: {device_id} ({device_type.value})")
        
        self._emit_event('device_registered', {'device': asdict(device)})
        return device
    
    def update_device_status(self, device_id: str, is_online: bool = True, 
                           battery_level: int = None, network_type: str = None):
        """Update device online status and metadata"""
        device = self.database.get_device(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        
        device.is_online = is_online
        device.last_seen = datetime.now().isoformat()
        
        if battery_level is not None:
            device.battery_level = battery_level
        if network_type is not None:
            device.network_type = network_type
        
        self.database.add_device(device)
        
        self._emit_event('device_status_updated', {
            'device_id': device_id,
            'is_online': is_online,
            'battery_level': battery_level,
            'network_type': network_type
        })
    
    async def sync_item(self, item: SyncItem, target_devices: List[str] = None) -> Dict[str, str]:
        """Sync item to devices"""
        if item.item_id in self.active_syncs:
            self.logger.debug(f"Sync already in progress for item: {item.item_id}")
            return {}
        
        # Calculate checksum if not provided
        if not item.checksum:
            item.checksum = self._calculate_checksum(item)
        
        # Store item
        self.database.add_sync_item(item)
        
        # Get target devices
        if not target_devices:
            user_devices = self.database.get_user_devices(item.user_id)
            target_devices = [d.device_id for d in user_devices if d.sync_enabled and d.is_online]
        
        # Start sync to each device
        sync_results = {}
        tasks = []
        
        for device_id in target_devices:
            if device_id != item.device_id:  # Don't sync back to origin device
                task = asyncio.create_task(self._sync_item_to_device(item, device_id))
                tasks.append((device_id, task))
        
        # Wait for all syncs to complete
        for device_id, task in tasks:
            try:
                result = await task
                sync_results[device_id] = result
            except Exception as e:
                sync_results[device_id] = f"error: {str(e)}"
                self.logger.error(f"Sync failed to device {device_id}: {e}")
        
        return sync_results
    
    async def _sync_item_to_device(self, item: SyncItem, device_id: str) -> str:
        """Sync single item to specific device"""
        async with self.sync_semaphore:
            self.active_syncs.add(item.item_id)
            start_time = time.time()
            
            try:
                device = self.database.get_device(device_id)
                if not device:
                    raise ValueError(f"Device not found: {device_id}")
                
                # Check if device should receive this item
                if not self._should_sync_to_device(item, device):
                    return "skipped"
                
                # Check for conflicts
                existing_item = self.database.get_sync_item(item.item_id)
                if existing_item and existing_item.version != item.version:
                    conflict = await self._detect_conflict(item, existing_item)
                    if conflict:
                        self.database.add_conflict(conflict)
                        return "conflict"
                
                # Perform sync based on device capabilities
                sync_method = self._get_sync_method(device)
                result = await sync_method(item, device)
                
                # Update sync state
                self.database.update_sync_state(device_id, item.item_id, item.version)
                
                # Log operation
                duration_ms = int((time.time() - start_time) * 1000)
                self.database.log_sync_operation(
                    device_id, "sync_item", "success", item.item_id,
                    f"Synced item {item.item_id}", duration_ms,
                    item.file_size or len(json.dumps(item.data))
                )
                
                self._emit_event('item_synced', {
                    'item_id': item.item_id,
                    'device_id': device_id,
                    'result': result
                })
                
                return result
                
            except Exception as e:
                # Log error
                duration_ms = int((time.time() - start_time) * 1000)
                self.database.log_sync_operation(
                    device_id, "sync_item", "error", item.item_id,
                    str(e), duration_ms
                )
                raise
            
            finally:
                self.active_syncs.discard(item.item_id)
    
    def _should_sync_to_device(self, item: SyncItem, device: DeviceInfo) -> bool:
        """Check if item should be synced to device based on capabilities and rules"""
        # Check device capabilities
        if device.capabilities == DeviceCapabilities.MINIMAL:
            # Only sync critical text items
            if item.content_type != ContentType.TEXT or item.priority < 8:
                return False
        elif device.capabilities == DeviceCapabilities.MOBILE:
            # Skip large files on mobile
            if item.file_size and item.file_size > 10 * 1024 * 1024:  # 10MB
                return False
            # Skip video on cellular
            if device.network_type == "cellular" and item.content_type == ContentType.VIDEO:
                return False
        
        # Check selective sync rules
        for rule in device.selective_sync_rules:
            if rule.startswith("exclude_type:"):
                excluded_type = rule.split(":")[1]
                if item.content_type.value == excluded_type:
                    return False
            elif rule.startswith("include_tag:"):
                required_tag = rule.split(":")[1]
                if required_tag not in item.tags:
                    return False
            elif rule.startswith("max_size:"):
                max_size = int(rule.split(":")[1])
                if item.file_size and item.file_size > max_size:
                    return False
        
        # Check storage limits
        if device.storage_limit:
            # This would need additional logic to track device storage usage
            pass
        
        return True
    
    def _get_sync_method(self, device: DeviceInfo) -> Callable:
        """Get appropriate sync method based on device type"""
        if device.device_type in [DeviceType.PHONE, DeviceType.TABLET]:
            return self._sync_to_mobile_device
        elif device.device_type == DeviceType.DESKTOP:
            return self._sync_to_desktop_device
        elif device.device_type == DeviceType.WEB:
            return self._sync_to_web_device
        else:
            return self._sync_to_generic_device
    
    async def _sync_to_mobile_device(self, item: SyncItem, device: DeviceInfo) -> str:
        """Sync item to mobile device with bandwidth awareness"""
        # Implement mobile-specific sync logic
        # - Use compression for large items
        # - Batch smaller items
        # - Respect bandwidth limits
        
        if device.bandwidth_limit and item.file_size:
            if item.file_size > device.bandwidth_limit * 10:  # 10 seconds worth
                return "deferred"  # Defer large files
        
        # Mobile devices get compressed versions
        if item.content_type == ContentType.IMAGE and item.file_size and item.file_size > 1024 * 1024:
            # Request compressed version
            return "synced_compressed"
        
        return "synced"
    
    async def _sync_to_desktop_device(self, item: SyncItem, device: DeviceInfo) -> str:
        """Sync item to desktop device with full fidelity"""
        # Desktop devices can handle full-quality content
        return "synced"
    
    async def _sync_to_web_device(self, item: SyncItem, device: DeviceInfo) -> str:
        """Sync item to web device through browser"""
        # Web devices have storage limitations
        if item.file_size and item.file_size > 50 * 1024 * 1024:  # 50MB
            return "reference_only"  # Only sync reference, not full file
        
        return "synced"
    
    async def _sync_to_generic_device(self, item: SyncItem, device: DeviceInfo) -> str:
        """Generic sync method"""
        return "synced"
    
    async def _detect_conflict(self, new_item: SyncItem, existing_item: SyncItem) -> Optional[SyncConflict]:
        """Detect and create conflict if items conflict"""
        if new_item.device_id == existing_item.device_id:
            return None  # Same device, no conflict
        
        # Check if both items were modified around the same time
        new_time = datetime.fromisoformat(new_item.modified_at)
        existing_time = datetime.fromisoformat(existing_item.modified_at)
        
        time_diff = abs((new_time - existing_time).total_seconds())
        
        if time_diff < 60:  # Modified within 1 minute
            return SyncConflict(
                conflict_id=str(uuid.uuid4()),
                item_id=new_item.item_id,
                conflicting_versions=[new_item, existing_item],
                conflict_type="concurrent_edit",
                detected_at=datetime.now().isoformat()
            )
        
        return None
    
    def _calculate_checksum(self, item: SyncItem) -> str:
        """Calculate checksum for sync item"""
        content = json.dumps(item.data, sort_keys=True) + item.modified_at
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _sync_loop(self):
        """Main sync loop"""
        while self.running:
            try:
                await self._process_pending_syncs()
            except Exception as e:
                self.logger.error(f"Sync loop error: {e}")
            
            await asyncio.sleep(self.sync_interval)
    
    async def _process_pending_syncs(self):
        """Process any pending sync operations"""
        # This would implement background sync logic
        # - Check for items that need syncing
        # - Handle failed syncs with backoff
        # - Monitor device connectivity
        pass
    
    async def _presence_loop(self):
        """Manage user presence for real-time collaboration"""
        while self.running:
            try:
                # Update presence data
                current_time = datetime.now().isoformat()
                
                # Clean up stale presence data
                stale_cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
                for user_id in list(self.presence_data.keys()):
                    user_presence = self.presence_data[user_id]
                    if user_presence.get('last_seen', '') < stale_cutoff:
                        del self.presence_data[user_id]
                        self._emit_event('user_offline', {'user_id': user_id})
                
            except Exception as e:
                self.logger.error(f"Presence loop error: {e}")
            
            await asyncio.sleep(30)
    
    async def _cleanup_loop(self):
        """Cleanup old data and logs"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Cleanup old logs
                cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
                
                conn = sqlite3.connect(self.database.db_path)
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM sync_logs WHERE timestamp < ?', (cutoff_date,))
                deleted_logs = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                if deleted_logs > 0:
                    self.logger.info(f"Cleaned up {deleted_logs} old sync logs")
                
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
    
    def on(self, event: str, handler: Callable):
        """Register event handler"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def _emit_event(self, event: str, data: Dict[str, Any]):
        """Emit event to registered handlers"""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"Event handler error for {event}: {e}")
    
    def get_sync_status(self, user_id: str) -> Dict[str, Any]:
        """Get sync status for user"""
        devices = self.database.get_user_devices(user_id)
        
        return {
            'user_id': user_id,
            'devices': [asdict(device) for device in devices],
            'active_syncs': len(self.active_syncs),
            'running': self.running
        }

async def main():
    """Example usage"""
    # Initialize sync engine
    config = {
        'sync_interval': 30,
        'max_concurrent_syncs': 5,
        'log_level': 'INFO'
    }
    
    sync_engine = SyncEngine(config)
    
    # Register devices
    phone = sync_engine.register_device(
        device_id="phone-001",
        device_type=DeviceType.PHONE,
        capabilities=DeviceCapabilities.MOBILE,
        name="iPhone 15",
        user_id="user123",
        platform="ios",
        version="1.0.0"
    )
    
    desktop = sync_engine.register_device(
        device_id="desktop-001",
        device_type=DeviceType.DESKTOP,
        capabilities=DeviceCapabilities.FULL,
        name="MacBook Pro",
        user_id="user123",
        platform="macos",
        version="1.0.0"
    )
    
    # Create test sync item
    sync_item = SyncItem(
        item_id="item-001",
        content_type=ContentType.TEXT,
        data={"title": "Test Note", "content": "This is a test note"},
        metadata={"app": "notes"},
        created_at=datetime.now().isoformat(),
        modified_at=datetime.now().isoformat(),
        version=1,
        device_id="phone-001",
        user_id="user123",
        priority=5
    )
    
    # Sync item
    results = await sync_engine.sync_item(sync_item)
    print(f"Sync results: {results}")
    
    # Get sync status
    status = sync_engine.get_sync_status("user123")
    print(f"Sync status: {status}")

if __name__ == '__main__':
    asyncio.run(main())