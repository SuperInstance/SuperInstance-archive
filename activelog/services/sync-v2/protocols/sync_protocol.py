#!/usr/bin/env python3
"""
ActiveLog.ai Cross-Platform Sync Protocols

Unified sync protocols for phone, desktop, and web platforms.
"""

import asyncio
import json
import logging
import hashlib
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import platform
import uuid

from ..core.sync_engine import SyncItem, DeviceInfo, DeviceType, DeviceCapabilities
from ..strategies.selective_sync import SelectiveSyncEngine
from ..strategies.bandwidth_aware import NetworkMonitor, AdaptiveSyncScheduler
from ..resolution.conflict_resolver import ConflictManager
from ..realtime.collaboration_hub import CollaborationHub

class ProtocolType(Enum):
    PHONE_SYNC = "phone_sync"
    DESKTOP_SYNC = "desktop_sync"
    WEB_SYNC = "web_sync"
    API_SYNC = "api_sync"

class SyncDirection(Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download" 
    BIDIRECTIONAL = "bidirectional"

class MessageType(Enum):
    HANDSHAKE = "handshake"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    ITEM_UPDATE = "item_update"
    CONFLICT_NOTIFICATION = "conflict_notification"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

@dataclass
class SyncMessage:
    """Sync protocol message"""
    message_id: str
    message_type: MessageType
    protocol_version: str
    device_id: str
    timestamp: str
    payload: Dict[str, Any]
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate message checksum"""
        content = f"{self.message_id}{self.message_type.value}{json.dumps(self.payload, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

@dataclass
class SyncRequest:
    """Sync request parameters"""
    device_id: str
    last_sync_timestamp: Optional[str]
    sync_direction: SyncDirection
    content_filters: List[str] = None
    priority_threshold: int = 1
    max_items: int = 100
    include_conflicts: bool = True

    def __post_init__(self):
        if self.content_filters is None:
            self.content_filters = []

@dataclass
class SyncResponse:
    """Sync response data"""
    items: List[SyncItem]
    conflicts: List[Dict[str, Any]]
    next_sync_token: str
    has_more: bool = False
    server_timestamp: str = None
    
    def __post_init__(self):
        if self.server_timestamp is None:
            self.server_timestamp = datetime.now().isoformat()

class BaseSyncProtocol:
    """Base class for all sync protocols"""
    
    def __init__(self, device_info: DeviceInfo, config: Dict[str, Any] = None):
        self.device_info = device_info
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Protocol version
        self.protocol_version = "2.0"
        
        # Components
        self.selective_sync = SelectiveSyncEngine()
        self.conflict_manager = ConflictManager()
        
        # Connection state
        self.is_connected = False
        self.last_heartbeat = None
        self.session_id = None
    
    async def connect(self, endpoint: str, credentials: Dict[str, Any] = None) -> bool:
        """Connect to sync endpoint"""
        try:
            # Perform handshake
            handshake_result = await self._perform_handshake(endpoint, credentials)
            
            if handshake_result['success']:
                self.is_connected = True
                self.session_id = handshake_result['session_id']
                self.logger.info(f"Connected to sync endpoint: {endpoint}")
                
                # Start heartbeat
                asyncio.create_task(self._heartbeat_loop())
                
                return True
            else:
                self.logger.error(f"Handshake failed: {handshake_result.get('error')}")
                return False
        
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from sync endpoint"""
        self.is_connected = False
        self.session_id = None
        self.logger.info("Disconnected from sync endpoint")
    
    async def sync_items(self, request: SyncRequest) -> SyncResponse:
        """Perform sync operation"""
        if not self.is_connected:
            raise RuntimeError("Not connected to sync endpoint")
        
        # Create sync message
        message = SyncMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.SYNC_REQUEST,
            protocol_version=self.protocol_version,
            device_id=self.device_info.device_id,
            timestamp=datetime.now().isoformat(),
            payload=asdict(request)
        )
        
        # Send request and wait for response
        response_message = await self._send_message(message)
        
        if response_message.message_type == MessageType.SYNC_RESPONSE:
            return self._parse_sync_response(response_message)
        elif response_message.message_type == MessageType.ERROR:
            raise RuntimeError(f"Sync error: {response_message.payload.get('error')}")
        else:
            raise RuntimeError(f"Unexpected response type: {response_message.message_type}")
    
    async def upload_item(self, item: SyncItem) -> Dict[str, Any]:
        """Upload single item"""
        # Check if item should be synced
        sync_decision = self.selective_sync.should_sync_item(item, self.device_info)
        
        if not sync_decision['sync']:
            return {
                'status': 'skipped',
                'reason': sync_decision['reason']
            }
        
        # Apply transformations if needed
        if sync_decision['transform']:
            item = await self._apply_transformations(item, sync_decision['transformations'])
        
        # Create upload message
        message = SyncMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.ITEM_UPDATE,
            protocol_version=self.protocol_version,
            device_id=self.device_info.device_id,
            timestamp=datetime.now().isoformat(),
            payload={
                'action': 'upload',
                'item': asdict(item)
            }
        )
        
        # Send upload
        response = await self._send_message(message)
        
        return {
            'status': 'uploaded',
            'item_id': item.item_id,
            'server_version': response.payload.get('version')
        }
    
    async def _perform_handshake(self, endpoint: str, credentials: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform protocol handshake"""
        handshake_payload = {
            'device_info': asdict(self.device_info),
            'protocol_version': self.protocol_version,
            'capabilities': self._get_protocol_capabilities(),
            'credentials': credentials or {}
        }
        
        message = SyncMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.HANDSHAKE,
            protocol_version=self.protocol_version,
            device_id=self.device_info.device_id,
            timestamp=datetime.now().isoformat(),
            payload=handshake_payload
        )
        
        # This would be implemented by subclasses
        return await self._send_handshake_message(message)
    
    async def _send_message(self, message: SyncMessage) -> SyncMessage:
        """Send message and wait for response"""
        raise NotImplementedError("Subclasses must implement _send_message")
    
    async def _send_handshake_message(self, message: SyncMessage) -> Dict[str, Any]:
        """Send handshake message"""
        raise NotImplementedError("Subclasses must implement _send_handshake_message")
    
    def _get_protocol_capabilities(self) -> List[str]:
        """Get protocol capabilities"""
        capabilities = [
            "selective_sync",
            "conflict_resolution",
            "compression",
            "incremental_sync"
        ]
        
        # Add device-specific capabilities
        if self.device_info.device_type in [DeviceType.PHONE, DeviceType.TABLET]:
            capabilities.extend([
                "bandwidth_awareness",
                "battery_optimization",
                "background_sync"
            ])
        elif self.device_info.device_type == DeviceType.DESKTOP:
            capabilities.extend([
                "real_time_collaboration",
                "version_history",
                "bulk_operations"
            ])
        elif self.device_info.device_type == DeviceType.WEB:
            capabilities.extend([
                "progressive_sync",
                "reference_only_large_files"
            ])
        
        return capabilities
    
    def _parse_sync_response(self, message: SyncMessage) -> SyncResponse:
        """Parse sync response message"""
        payload = message.payload
        
        # Parse items
        items = []
        for item_data in payload.get('items', []):
            items.append(SyncItem(**item_data))
        
        return SyncResponse(
            items=items,
            conflicts=payload.get('conflicts', []),
            next_sync_token=payload.get('next_sync_token', ''),
            has_more=payload.get('has_more', False),
            server_timestamp=payload.get('server_timestamp')
        )
    
    async def _apply_transformations(self, item: SyncItem, transformations: List[Dict[str, Any]]) -> SyncItem:
        """Apply transformations to item"""
        transformed_item = item
        
        for transform in transformations:
            if transform['type'] == 'compression':
                transformed_item = await self._compress_item(transformed_item, transform['params'])
            elif transform['type'] == 'resize':
                transformed_item = await self._resize_item(transformed_item, transform['params'])
            elif transform['type'] == 'format_conversion':
                transformed_item = await self._convert_format(transformed_item, transform['params'])
        
        return transformed_item
    
    async def _compress_item(self, item: SyncItem, params: Dict[str, Any]) -> SyncItem:
        """Compress item data"""
        # Implementation would depend on content type
        return item
    
    async def _resize_item(self, item: SyncItem, params: Dict[str, Any]) -> SyncItem:
        """Resize item (for images/videos)"""
        # Implementation would depend on content type
        return item
    
    async def _convert_format(self, item: SyncItem, params: Dict[str, Any]) -> SyncItem:
        """Convert item format"""
        # Implementation would depend on content type
        return item
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        heartbeat_interval = self.config.get('heartbeat_interval', 30)
        
        while self.is_connected:
            try:
                await asyncio.sleep(heartbeat_interval)
                
                if self.is_connected:
                    await self._send_heartbeat()
                    
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
    
    async def _send_heartbeat(self):
        """Send heartbeat message"""
        message = SyncMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.HEARTBEAT,
            protocol_version=self.protocol_version,
            device_id=self.device_info.device_id,
            timestamp=datetime.now().isoformat(),
            payload={'status': 'alive'}
        )
        
        try:
            await self._send_message(message)
            self.last_heartbeat = datetime.now().isoformat()
        except Exception as e:
            self.logger.error(f"Heartbeat failed: {e}")
            self.is_connected = False

class MobileSyncProtocol(BaseSyncProtocol):
    """Mobile device sync protocol with bandwidth and battery awareness"""
    
    def __init__(self, device_info: DeviceInfo, config: Dict[str, Any] = None):
        super().__init__(device_info, config)
        
        # Mobile-specific components
        self.network_monitor = NetworkMonitor(monitor_interval=60)
        self.scheduler = AdaptiveSyncScheduler(self.network_monitor)
        
        # Mobile sync settings
        self.wifi_only_large_files = config.get('wifi_only_large_files', True)
        self.battery_aware_sync = config.get('battery_aware_sync', True)
        self.background_sync_enabled = config.get('background_sync_enabled', True)
    
    async def connect(self, endpoint: str, credentials: Dict[str, Any] = None) -> bool:
        """Connect with mobile-specific optimizations"""
        # Start network monitoring
        asyncio.create_task(self.network_monitor.start_monitoring())
        
        # Check network conditions before connecting
        if not await self._check_connection_conditions():
            self.logger.info("Deferring connection due to poor network conditions")
            return False
        
        return await super().connect(endpoint, credentials)
    
    async def sync_items(self, request: SyncRequest) -> SyncResponse:
        """Mobile-optimized sync"""
        # Check battery and network conditions
        if not await self._should_sync_now():
            raise RuntimeError("Sync deferred due to device conditions")
        
        # Optimize request for mobile
        mobile_request = await self._optimize_sync_request(request)
        
        return await super().sync_items(mobile_request)
    
    async def _check_connection_conditions(self) -> bool:
        """Check if connection conditions are suitable"""
        # Wait for network monitoring to start
        await asyncio.sleep(1)
        
        quality = self.network_monitor.get_connection_quality()
        metrics = self.network_monitor.current_metrics
        
        # Don't connect on very poor networks
        if quality.value == "unreliable":
            return False
        
        # Check if on metered connection with data limits
        if metrics and metrics.is_metered:
            if metrics.data_limit and metrics.data_used:
                usage_percent = metrics.data_used / metrics.data_limit
                if usage_percent > 0.9:  # >90% of data limit used
                    return False
        
        return True
    
    async def _should_sync_now(self) -> bool:
        """Check if device conditions are suitable for sync"""
        # Check battery level
        if self.battery_aware_sync and self.device_info.battery_level:
            if self.device_info.battery_level < 15:  # <15% battery
                return False
        
        # Check network conditions
        quality = self.network_monitor.get_connection_quality()
        if quality.value in ["poor", "unreliable"]:
            return False
        
        return True
    
    async def _optimize_sync_request(self, request: SyncRequest) -> SyncRequest:
        """Optimize sync request for mobile conditions"""
        optimized_request = SyncRequest(
            device_id=request.device_id,
            last_sync_timestamp=request.last_sync_timestamp,
            sync_direction=request.sync_direction,
            content_filters=request.content_filters.copy(),
            priority_threshold=request.priority_threshold,
            max_items=request.max_items,
            include_conflicts=request.include_conflicts
        )
        
        # Adjust based on network conditions
        quality = self.network_monitor.get_connection_quality()
        
        if quality.value == "poor":
            # Reduce batch size and increase priority threshold
            optimized_request.max_items = min(request.max_items, 20)
            optimized_request.priority_threshold = max(request.priority_threshold, 7)
            
            # Exclude media on poor connections
            if "exclude_media" not in optimized_request.content_filters:
                optimized_request.content_filters.append("exclude_media")
        
        # Add cellular-specific filters
        if self.network_monitor.current_metrics and self.network_monitor.current_metrics.connection_type.value == "cellular":
            if self.wifi_only_large_files:
                optimized_request.content_filters.append("max_size:5MB")
        
        return optimized_request
    
    async def _send_message(self, message: SyncMessage) -> SyncMessage:
        """Mobile-optimized message sending"""
        # Add mobile-specific headers
        message.payload['mobile_optimizations'] = {
            'compression_preferred': True,
            'battery_level': self.device_info.battery_level,
            'network_type': self.device_info.network_type,
            'connection_quality': self.network_monitor.get_connection_quality().value
        }
        
        # Implementation would use HTTP/WebSocket with mobile optimizations
        # For now, this is a stub
        return message
    
    async def _send_handshake_message(self, message: SyncMessage) -> Dict[str, Any]:
        """Mobile handshake with network preferences"""
        # Add mobile-specific handshake data
        message.payload['mobile_preferences'] = {
            'wifi_only_large_files': self.wifi_only_large_files,
            'battery_aware_sync': self.battery_aware_sync,
            'background_sync_enabled': self.background_sync_enabled
        }
        
        # Stub implementation
        return {
            'success': True,
            'session_id': str(uuid.uuid4()),
            'server_capabilities': ['compression', 'selective_sync', 'mobile_optimization']
        }

class DesktopSyncProtocol(BaseSyncProtocol):
    """Desktop sync protocol with full-featured capabilities"""
    
    def __init__(self, device_info: DeviceInfo, config: Dict[str, Any] = None):
        super().__init__(device_info, config)
        
        # Desktop-specific components
        self.collaboration_hub = CollaborationHub(config.get('collaboration', {}))
        
        # Desktop sync settings
        self.real_time_sync = config.get('real_time_sync', True)
        self.version_history_enabled = config.get('version_history', True)
        self.bulk_operations_enabled = config.get('bulk_operations', True)
    
    async def connect(self, endpoint: str, credentials: Dict[str, Any] = None) -> bool:
        """Desktop connection with collaboration support"""
        result = await super().connect(endpoint, credentials)
        
        if result and self.real_time_sync:
            # Start collaboration hub if enabled
            collaboration_port = self.config.get('collaboration_port', 8765)
            asyncio.create_task(
                self.collaboration_hub.start_server("localhost", collaboration_port)
            )
        
        return result
    
    async def sync_bulk_items(self, items: List[SyncItem]) -> List[Dict[str, Any]]:
        """Bulk sync operation for desktop"""
        if not self.bulk_operations_enabled:
            # Fall back to individual sync
            results = []
            for item in items:
                result = await self.upload_item(item)
                results.append(result)
            return results
        
        # Bulk upload
        message = SyncMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.ITEM_UPDATE,
            protocol_version=self.protocol_version,
            device_id=self.device_info.device_id,
            timestamp=datetime.now().isoformat(),
            payload={
                'action': 'bulk_upload',
                'items': [asdict(item) for item in items]
            }
        )
        
        response = await self._send_message(message)
        return response.payload.get('results', [])
    
    async def start_collaboration_session(self, document_id: str) -> str:
        """Start real-time collaboration session"""
        if not self.real_time_sync:
            raise RuntimeError("Real-time collaboration not enabled")
        
        # Create collaboration session
        session = await self.collaboration_hub._get_or_create_session(document_id)
        
        return session.session_id
    
    async def _send_message(self, message: SyncMessage) -> SyncMessage:
        """Desktop message sending with full capabilities"""
        # Add desktop-specific capabilities
        message.payload['desktop_features'] = {
            'real_time_collaboration': self.real_time_sync,
            'version_history': self.version_history_enabled,
            'bulk_operations': self.bulk_operations_enabled,
            'full_quality_media': True
        }
        
        # Stub implementation - would use HTTP/WebSocket
        return message
    
    async def _send_handshake_message(self, message: SyncMessage) -> Dict[str, Any]:
        """Desktop handshake with full capabilities"""
        return {
            'success': True,
            'session_id': str(uuid.uuid4()),
            'server_capabilities': [
                'real_time_collaboration',
                'version_history', 
                'bulk_operations',
                'full_quality_media',
                'conflict_resolution'
            ]
        }

class WebSyncProtocol(BaseSyncProtocol):
    """Web browser sync protocol with progressive loading"""
    
    def __init__(self, device_info: DeviceInfo, config: Dict[str, Any] = None):
        super().__init__(device_info, config)
        
        # Web-specific settings
        self.progressive_sync = config.get('progressive_sync', True)
        self.reference_only_large_files = config.get('reference_only_large_files', True)
        self.session_based_sync = config.get('session_based_sync', True)
        self.storage_quota = config.get('storage_quota', 50 * 1024 * 1024)  # 50MB default
    
    async def sync_items(self, request: SyncRequest) -> SyncResponse:
        """Web-optimized sync with progressive loading"""
        if self.progressive_sync:
            # Load items progressively
            return await self._progressive_sync(request)
        else:
            return await super().sync_items(request)
    
    async def _progressive_sync(self, request: SyncRequest) -> SyncResponse:
        """Progressive sync for web browsers"""
        # Start with high-priority, small items
        priority_request = SyncRequest(
            device_id=request.device_id,
            last_sync_timestamp=request.last_sync_timestamp,
            sync_direction=request.sync_direction,
            content_filters=request.content_filters + ["max_size:1MB", "priority_min:7"],
            priority_threshold=7,
            max_items=20,
            include_conflicts=request.include_conflicts
        )
        
        initial_response = await super().sync_items(priority_request)
        
        # Schedule background loading of remaining items
        if initial_response.has_more:
            asyncio.create_task(self._background_sync_remaining(request))
        
        return initial_response
    
    async def _background_sync_remaining(self, original_request: SyncRequest):
        """Background sync of remaining items"""
        try:
            # Wait a bit before starting background sync
            await asyncio.sleep(2)
            
            # Load remaining items in smaller batches
            batch_request = SyncRequest(
                device_id=original_request.device_id,
                last_sync_timestamp=original_request.last_sync_timestamp,
                sync_direction=original_request.sync_direction,
                content_filters=original_request.content_filters,
                priority_threshold=1,
                max_items=10,
                include_conflicts=False
            )
            
            while True:
                response = await super().sync_items(batch_request)
                
                if not response.has_more or not response.items:
                    break
                
                # Update sync token for next batch
                batch_request.last_sync_timestamp = response.next_sync_token
                
                # Rate limit background sync
                await asyncio.sleep(1)
        
        except Exception as e:
            self.logger.error(f"Background sync error: {e}")
    
    async def upload_item(self, item: SyncItem) -> Dict[str, Any]:
        """Web upload with storage quota checking"""
        # Check storage quota
        if self._would_exceed_quota(item):
            if self.reference_only_large_files:
                # Upload reference only
                return await self._upload_reference(item)
            else:
                return {
                    'status': 'deferred',
                    'reason': 'storage_quota_exceeded'
                }
        
        return await super().upload_item(item)
    
    def _would_exceed_quota(self, item: SyncItem) -> bool:
        """Check if item would exceed storage quota"""
        item_size = item.file_size or len(json.dumps(item.data))
        
        # Get current storage usage (would be implemented with Storage API)
        current_usage = 0  # Stub
        
        return (current_usage + item_size) > self.storage_quota
    
    async def _upload_reference(self, item: SyncItem) -> Dict[str, Any]:
        """Upload item reference only"""
        reference_item = SyncItem(
            item_id=item.item_id,
            content_type=item.content_type,
            data={
                'title': item.data.get('title', ''),
                'preview': item.data.get('preview', ''),
                'reference_only': True,
                'full_size': item.file_size
            },
            metadata=item.metadata,
            created_at=item.created_at,
            modified_at=item.modified_at,
            version=item.version,
            device_id=item.device_id,
            user_id=item.user_id,
            priority=item.priority
        )
        
        return await super().upload_item(reference_item)
    
    async def _send_message(self, message: SyncMessage) -> SyncMessage:
        """Web message sending with browser limitations"""
        # Add web-specific constraints
        message.payload['web_constraints'] = {
            'storage_quota': self.storage_quota,
            'progressive_sync': self.progressive_sync,
            'reference_only_large_files': self.reference_only_large_files,
            'cors_mode': True
        }
        
        # Stub implementation - would use fetch() API
        return message
    
    async def _send_handshake_message(self, message: SyncMessage) -> Dict[str, Any]:
        """Web handshake with browser capabilities"""
        return {
            'success': True,
            'session_id': str(uuid.uuid4()),
            'server_capabilities': [
                'progressive_sync',
                'reference_only_files',
                'cors_support',
                'compression'
            ]
        }

class SyncProtocolFactory:
    """Factory for creating appropriate sync protocols"""
    
    @staticmethod
    def create_protocol(device_info: DeviceInfo, config: Dict[str, Any] = None) -> BaseSyncProtocol:
        """Create appropriate sync protocol for device"""
        if device_info.device_type in [DeviceType.PHONE, DeviceType.TABLET]:
            return MobileSyncProtocol(device_info, config)
        elif device_info.device_type == DeviceType.DESKTOP:
            return DesktopSyncProtocol(device_info, config)
        elif device_info.device_type == DeviceType.WEB:
            return WebSyncProtocol(device_info, config)
        else:
            return BaseSyncProtocol(device_info, config)
    
    @staticmethod
    def get_supported_protocols() -> List[ProtocolType]:
        """Get list of supported protocol types"""
        return list(ProtocolType)

async def main():
    """Example usage of sync protocols"""
    # Create device info
    mobile_device = DeviceInfo(
        device_id="phone-001",
        device_type=DeviceType.PHONE,
        capabilities=DeviceCapabilities.MOBILE,
        name="iPhone 15",
        user_id="user123",
        platform="ios",
        version="1.0.0",
        last_seen=datetime.now().isoformat(),
        network_type="wifi",
        battery_level=85
    )
    
    desktop_device = DeviceInfo(
        device_id="desktop-001",
        device_type=DeviceType.DESKTOP,
        capabilities=DeviceCapabilities.FULL,
        name="MacBook Pro",
        user_id="user123",
        platform="macos",
        version="1.0.0",
        last_seen=datetime.now().isoformat()
    )
    
    # Create protocols
    mobile_protocol = SyncProtocolFactory.create_protocol(mobile_device)
    desktop_protocol = SyncProtocolFactory.create_protocol(desktop_device)
    
    print(f"Mobile protocol capabilities: {mobile_protocol._get_protocol_capabilities()}")
    print(f"Desktop protocol capabilities: {desktop_protocol._get_protocol_capabilities()}")
    
    # Simulate connections
    mobile_connected = await mobile_protocol.connect("https://sync.activelog.ai/mobile")
    desktop_connected = await desktop_protocol.connect("https://sync.activelog.ai/desktop")
    
    print(f"Mobile connected: {mobile_connected}")
    print(f"Desktop connected: {desktop_connected}")

if __name__ == '__main__':
    asyncio.run(main())