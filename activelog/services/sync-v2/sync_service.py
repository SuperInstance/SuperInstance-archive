#!/usr/bin/env python3
"""
ActiveLog.ai Sync Service v2 - Main Entry Point

Unified sync service orchestrating all synchronization components.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .core.sync_engine import SyncEngine, DeviceInfo, SyncItem, DeviceType, DeviceCapabilities
from .protocols.sync_protocol import SyncProtocolFactory, SyncRequest, SyncDirection
from .strategies.selective_sync import SelectiveSyncEngine, SyncOptimizer
from .strategies.bandwidth_aware import NetworkMonitor, AdaptiveSyncScheduler
from .resolution.conflict_resolver import ConflictManager
from .realtime.collaboration_hub import CollaborationHub

class SyncServiceV2:
    """Main sync service coordinating all components"""
    
    def __init__(self, config_path: str = None):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.get('log_level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.get('log_file', 'sync_v2.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.sync_engine = SyncEngine(self.config.get('sync_engine', {}))
        self.selective_sync = SelectiveSyncEngine()
        self.sync_optimizer = SyncOptimizer()
        self.conflict_manager = ConflictManager(self.config.get('conflict_resolution', {}))
        
        # Network and bandwidth management
        self.network_monitor = NetworkMonitor(
            monitor_interval=self.config.get('network_monitor_interval', 30)
        )
        self.sync_scheduler = AdaptiveSyncScheduler(self.network_monitor)
        
        # Real-time collaboration
        self.collaboration_hub = CollaborationHub(self.config.get('collaboration', {}))
        
        # Active sync protocols
        self.active_protocols: Dict[str, Any] = {}
        
        # Service state
        self.running = False
        self.stats = {
            'items_synced': 0,
            'conflicts_resolved': 0,
            'bytes_transferred': 0,
            'sync_sessions': 0,
            'start_time': None
        }
    
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load service configuration"""
        default_config = {
            'sync_engine': {
                'sync_interval': 30,
                'max_concurrent_syncs': 5,
                'database_path': 'sync_v2.db'
            },
            'network_monitor_interval': 30,
            'conflict_resolution': {
                'auto_resolve_low_severity': True,
                'auto_resolve_threshold': 0.8
            },
            'collaboration': {
                'enabled': True,
                'websocket_port': 8765,
                'max_operation_history': 1000
            },
            'log_level': 'INFO',
            'log_file': 'sync_v2.log'
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                print(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    async def start(self):
        """Start the sync service"""
        if self.running:
            self.logger.warning("Sync service is already running")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.now().isoformat()
        
        self.logger.info("Starting ActiveLog Sync Service v2...")
        
        try:
            # Start core components
            tasks = [
                asyncio.create_task(self.sync_engine.start()),
                asyncio.create_task(self.network_monitor.start_monitoring()),
                asyncio.create_task(self._stats_loop())
            ]
            
            # Start collaboration hub if enabled
            if self.config.get('collaboration', {}).get('enabled', True):
                collaboration_port = self.config.get('collaboration', {}).get('websocket_port', 8765)
                tasks.append(
                    asyncio.create_task(
                        self.collaboration_hub.start_server("0.0.0.0", collaboration_port)
                    )
                )
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
        
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Sync service error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the sync service"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping ActiveLog Sync Service v2...")
        
        # Disconnect all protocols
        for protocol in self.active_protocols.values():
            try:
                await protocol.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting protocol: {e}")
        
        # Stop network monitoring
        self.network_monitor.stop_monitoring()
        
        self.logger.info("Sync service stopped")
    
    async def register_device(self, device_info: DeviceInfo) -> str:
        """Register a device for synchronization"""
        # Register with sync engine
        registered_device = self.sync_engine.register_device(
            device_info.device_id,
            device_info.device_type,
            device_info.capabilities,
            device_info.name,
            device_info.user_id,
            device_info.platform,
            device_info.version
        )
        
        # Create appropriate sync protocol
        protocol_config = self.config.get('protocols', {})
        protocol = SyncProtocolFactory.create_protocol(device_info, protocol_config)
        
        # Store active protocol
        self.active_protocols[device_info.device_id] = protocol
        
        self.logger.info(f"Registered device: {device_info.name} ({device_info.device_id})")
        
        return device_info.device_id
    
    async def sync_device(self, device_id: str, endpoint: str = None, 
                         credentials: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform sync operation for device"""
        if device_id not in self.active_protocols:
            raise ValueError(f"Device not registered: {device_id}")
        
        protocol = self.active_protocols[device_id]
        device_info = self.sync_engine.database.get_device(device_id)
        
        if not device_info:
            raise ValueError(f"Device info not found: {device_id}")
        
        sync_start_time = time.time()
        
        try:
            # Connect if not already connected
            if not protocol.is_connected:
                sync_endpoint = endpoint or self._get_sync_endpoint(device_info)
                connected = await protocol.connect(sync_endpoint, credentials)
                
                if not connected:
                    raise RuntimeError("Failed to connect to sync endpoint")
            
            # Create sync request
            sync_request = SyncRequest(
                device_id=device_id,
                last_sync_timestamp=self._get_last_sync_timestamp(device_id),
                sync_direction=SyncDirection.BIDIRECTIONAL,
                max_items=self._get_max_items_for_device(device_info)
            )
            
            # Perform sync
            response = await protocol.sync_items(sync_request)
            
            # Process synced items
            sync_results = await self._process_sync_response(device_id, response)
            
            # Update stats
            self.stats['items_synced'] += len(response.items)
            self.stats['sync_sessions'] += 1
            
            sync_duration = time.time() - sync_start_time
            
            return {
                'status': 'success',
                'items_synced': len(response.items),
                'conflicts_detected': len(response.conflicts),
                'duration_seconds': sync_duration,
                'next_sync_token': response.next_sync_token,
                'results': sync_results
            }
        
        except Exception as e:
            self.logger.error(f"Sync failed for device {device_id}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'duration_seconds': time.time() - sync_start_time
            }
    
    async def sync_item(self, item: SyncItem, target_devices: List[str] = None) -> Dict[str, Any]:
        """Sync specific item to target devices"""
        return await self.sync_engine.sync_item(item, target_devices)
    
    async def resolve_conflict(self, conflict_id: str, resolution_strategy: str = None,
                              user_id: str = "system") -> Dict[str, Any]:
        """Resolve a sync conflict"""
        # This would integrate with the conflict manager
        # Implementation depends on how conflicts are stored and tracked
        
        self.logger.info(f"Resolving conflict {conflict_id} with strategy {resolution_strategy}")
        
        # Increment stats
        self.stats['conflicts_resolved'] += 1
        
        return {
            'status': 'resolved',
            'conflict_id': conflict_id,
            'strategy_used': resolution_strategy,
            'resolved_by': user_id,
            'resolved_at': datetime.now().isoformat()
        }
    
    async def start_collaboration_session(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """Start real-time collaboration session"""
        if not self.config.get('collaboration', {}).get('enabled', True):
            raise RuntimeError("Real-time collaboration is not enabled")
        
        # Create collaboration session
        session = await self.collaboration_hub._get_or_create_session(document_id)
        
        return {
            'session_id': session.session_id,
            'document_id': document_id,
            'websocket_url': f"ws://localhost:{self.config.get('collaboration', {}).get('websocket_port', 8765)}",
            'current_revision': session.current_revision
        }
    
    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of registered device"""
        if device_id not in self.active_protocols:
            return None
        
        protocol = self.active_protocols[device_id]
        device_info = self.sync_engine.database.get_device(device_id)
        
        if not device_info:
            return None
        
        return {
            'device_id': device_id,
            'device_info': asdict(device_info),
            'protocol_connected': protocol.is_connected,
            'last_heartbeat': protocol.last_heartbeat,
            'session_id': protocol.session_id
        }
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics"""
        uptime_seconds = 0
        if self.stats['start_time']:
            start_time = datetime.fromisoformat(self.stats['start_time'])
            uptime_seconds = (datetime.now() - start_time).total_seconds()
        
        return {
            **self.stats,
            'uptime_seconds': uptime_seconds,
            'registered_devices': len(self.active_protocols),
            'active_connections': sum(1 for p in self.active_protocols.values() if p.is_connected),
            'collaboration_stats': self.collaboration_hub.get_session_stats(),
            'network_quality': self.network_monitor.get_connection_quality().value if self.network_monitor.current_metrics else 'unknown'
        }
    
    def get_device_list(self) -> List[Dict[str, Any]]:
        """Get list of registered devices"""
        devices = []
        
        for device_id, protocol in self.active_protocols.items():
            device_info = self.sync_engine.database.get_device(device_id)
            if device_info:
                devices.append({
                    'device_id': device_id,
                    'name': device_info.name,
                    'device_type': device_info.device_type.value,
                    'capabilities': device_info.capabilities.value,
                    'platform': device_info.platform,
                    'is_online': device_info.is_online,
                    'last_seen': device_info.last_seen,
                    'protocol_connected': protocol.is_connected
                })
        
        return devices
    
    async def _process_sync_response(self, device_id: str, response) -> List[Dict[str, Any]]:
        """Process sync response and handle conflicts"""
        results = []
        
        # Process synced items
        for item in response.items:
            try:
                # Add item to sync engine
                await self.sync_engine.sync_item(item, [device_id])
                results.append({
                    'item_id': item.item_id,
                    'status': 'synced'
                })
            except Exception as e:
                results.append({
                    'item_id': item.item_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Process conflicts
        for conflict_data in response.conflicts:
            try:
                # Handle conflict using conflict manager
                self.logger.warning(f"Conflict detected: {conflict_data}")
                results.append({
                    'conflict_id': conflict_data.get('conflict_id'),
                    'status': 'conflict_detected'
                })
            except Exception as e:
                self.logger.error(f"Conflict processing error: {e}")
        
        return results
    
    def _get_sync_endpoint(self, device_info: DeviceInfo) -> str:
        """Get appropriate sync endpoint for device"""
        endpoints = self.config.get('endpoints', {})
        
        if device_info.device_type in [DeviceType.PHONE, DeviceType.TABLET]:
            return endpoints.get('mobile', 'https://sync.activelog.ai/mobile')
        elif device_info.device_type == DeviceType.DESKTOP:
            return endpoints.get('desktop', 'https://sync.activelog.ai/desktop')
        elif device_info.device_type == DeviceType.WEB:
            return endpoints.get('web', 'https://sync.activelog.ai/web')
        else:
            return endpoints.get('default', 'https://sync.activelog.ai/api')
    
    def _get_last_sync_timestamp(self, device_id: str) -> Optional[str]:
        """Get last sync timestamp for device"""
        # This would query the sync state from database
        # For now, return None to sync all items
        return None
    
    def _get_max_items_for_device(self, device_info: DeviceInfo) -> int:
        """Get maximum items per sync for device"""
        if device_info.capabilities == DeviceCapabilities.MINIMAL:
            return 10
        elif device_info.capabilities == DeviceCapabilities.MOBILE:
            return 50
        elif device_info.capabilities == DeviceCapabilities.STANDARD:
            return 100
        else:  # FULL
            return 200
    
    async def _stats_loop(self):
        """Background task to update statistics"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Update network stats
                if self.network_monitor.current_metrics:
                    self.stats['network_quality'] = self.network_monitor.get_connection_quality().value
                
                # Log periodic stats
                if self.stats['sync_sessions'] > 0:
                    self.logger.info(f"Sync stats: {self.stats['items_synced']} items, "
                                   f"{self.stats['sync_sessions']} sessions, "
                                   f"{self.stats['conflicts_resolved']} conflicts resolved")
            
            except Exception as e:
                self.logger.error(f"Stats update error: {e}")

async def main():
    """Main entry point for sync service"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Sync Service v2')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--port', type=int, default=8000, help='HTTP API port')
    args = parser.parse_args()
    
    # Create and start sync service
    sync_service = SyncServiceV2(args.config)
    
    # Example: Register some test devices
    phone_device = DeviceInfo(
        device_id="phone-001",
        device_type=DeviceType.PHONE,
        capabilities=DeviceCapabilities.MOBILE,
        name="iPhone 15",
        user_id="user123",
        platform="ios",
        version="1.0.0",
        last_seen=datetime.now().isoformat()
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
    
    await sync_service.register_device(phone_device)
    await sync_service.register_device(desktop_device)
    
    print("Registered test devices:")
    for device in sync_service.get_device_list():
        print(f"  - {device['name']} ({device['device_type']})")
    
    # Start the service
    await sync_service.start()

if __name__ == '__main__':
    asyncio.run(main())