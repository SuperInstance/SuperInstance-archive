"""
Cross-Device Synchronization System for Adaptive UX

This module provides seamless handoff between devices, configuration synchronization,
state preservation, device capability negotiation, workload distribution, and
device clustering capabilities.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol
import numpy as np
from collections import defaultdict, deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceType(Enum):
    DESKTOP = "desktop"
    LAPTOP = "laptop"
    TABLET = "tablet"
    SMARTPHONE = "smartphone"
    TV = "tv"
    WATCH = "watch"
    IOT_DEVICE = "iot_device"

class ConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    PAIRING = "pairing"

class SyncScope(Enum):
    FULL = "full"
    CONFIGURATION = "configuration"
    STATE = "state"
    PREFERENCES = "preferences"
    CONTENT = "content"
    MINIMAL = "minimal"

class ConflictResolution(Enum):
    LATEST_WINS = "latest_wins"
    DEVICE_PRIORITY = "device_priority"
    USER_CHOICE = "user_choice"
    MERGE = "merge"
    KEEP_BOTH = "keep_both"

@dataclass
class DeviceCapabilities:
    screen_size: Tuple[int, int]
    input_methods: List[str]
    processing_power: float  # 0-1 scale
    memory_gb: int
    storage_gb: int
    network_speed: float  # Mbps
    battery_powered: bool
    has_camera: bool
    has_microphone: bool
    has_speakers: bool
    gpu_capable: bool
    touch_enabled: bool
    keyboard_available: bool
    mouse_available: bool

@dataclass
class DeviceInfo:
    device_id: str
    device_name: str
    device_type: DeviceType
    capabilities: DeviceCapabilities
    os_version: str
    app_version: str
    user_id: str
    last_seen: datetime
    connection_status: ConnectionStatus
    sync_preferences: Dict[str, Any] = field(default_factory=dict)
    trust_level: float = 0.0  # 0-1 scale
    location: Optional[str] = None

@dataclass
class SyncState:
    device_id: str
    state_id: str
    state_type: str
    data: Dict[str, Any]
    timestamp: datetime
    checksum: str
    version: int = 1
    dependencies: List[str] = field(default_factory=list)

@dataclass
class HandoffRequest:
    request_id: str
    source_device: str
    target_device: str
    handoff_type: str
    state_data: Dict[str, Any]
    timestamp: datetime
    priority: int = 1  # 1-10 scale
    expiry_time: Optional[datetime] = None
    user_confirmation: bool = False

class DeviceCluster:
    """Manages a cluster of related devices"""
    
    def __init__(self, cluster_id: str, primary_device: str):
        self.cluster_id = cluster_id
        self.primary_device = primary_device
        self.devices: Dict[str, DeviceInfo] = {}
        self.shared_state: Dict[str, SyncState] = {}
        self.workload_distribution: Dict[str, float] = {}
        self.cluster_capabilities: Dict[str, Any] = {}
        
    def add_device(self, device: DeviceInfo):
        """Add device to cluster"""
        self.devices[device.device_id] = device
        self._update_cluster_capabilities()
        
    def remove_device(self, device_id: str):
        """Remove device from cluster"""
        if device_id in self.devices:
            del self.devices[device_id]
            self._update_cluster_capabilities()
    
    def _update_cluster_capabilities(self):
        """Update cluster-wide capabilities"""
        if not self.devices:
            self.cluster_capabilities = {}
            return
        
        # Aggregate capabilities
        total_processing = sum(d.capabilities.processing_power for d in self.devices.values())
        total_memory = sum(d.capabilities.memory_gb for d in self.devices.values())
        max_screen_size = max(
            d.capabilities.screen_size[0] * d.capabilities.screen_size[1] 
            for d in self.devices.values()
        )
        
        all_input_methods = set()
        for device in self.devices.values():
            all_input_methods.update(device.capabilities.input_methods)
        
        self.cluster_capabilities = {
            'total_processing_power': total_processing,
            'total_memory_gb': total_memory,
            'max_screen_pixels': max_screen_size,
            'available_input_methods': list(all_input_methods),
            'device_count': len(self.devices),
            'has_mobile_device': any(d.device_type in [DeviceType.SMARTPHONE, DeviceType.TABLET] 
                                   for d in self.devices.values()),
            'has_desktop_device': any(d.device_type in [DeviceType.DESKTOP, DeviceType.LAPTOP] 
                                    for d in self.devices.values())
        }

class CrossDeviceSynchronizer:
    """Main cross-device synchronization coordinator"""
    
    def __init__(self, device_id: str, device_info: DeviceInfo):
        self.device_id = device_id
        self.device_info = device_info
        
        # Device management
        self.known_devices: Dict[str, DeviceInfo] = {}
        self.device_clusters: Dict[str, DeviceCluster] = {}
        self.active_connections: Dict[str, WebSocketClientProtocol] = {}
        
        # Synchronization state
        self.local_state: Dict[str, SyncState] = {}
        self.sync_queue: deque = deque()
        self.conflict_queue: List[Dict[str, Any]] = []
        self.handoff_requests: Dict[str, HandoffRequest] = {}
        
        # Configuration
        self.sync_preferences = {
            'auto_sync': True,
            'conflict_resolution': ConflictResolution.LATEST_WINS,
            'sync_scope': SyncScope.FULL,
            'max_sync_interval': 300,  # 5 minutes
            'trust_threshold': 0.5
        }
        
        # WebSocket server for incoming connections
        self.websocket_server = None
        self.server_port = 8900 + hash(device_id) % 100  # Unique port per device
        
        # Background tasks
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.is_running = False
        
        # State tracking
        self.state_versions: Dict[str, int] = {}
        self.last_sync_times: Dict[str, datetime] = {}
        
        logger.info(f"Cross-device synchronizer initialized for device {device_id}")
    
    async def start_synchronization(self):
        """Start the synchronization service"""
        self.is_running = True
        
        # Start WebSocket server for incoming connections
        await self._start_websocket_server()
        
        # Start background sync loop
        asyncio.create_task(self._sync_loop())
        
        # Start device discovery
        asyncio.create_task(self._device_discovery_loop())
        
        logger.info(f"Cross-device synchronization started on port {self.server_port}")
    
    async def stop_synchronization(self):
        """Stop the synchronization service"""
        self.is_running = False
        
        # Close WebSocket server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        # Close active connections
        for connection in self.active_connections.values():
            await connection.close()
        
        logger.info("Cross-device synchronization stopped")
    
    async def _start_websocket_server(self):
        """Start WebSocket server for incoming device connections"""
        try:
            self.websocket_server = await websockets.serve(
                self._handle_incoming_connection,
                "0.0.0.0",
                self.server_port
            )
            logger.info(f"WebSocket server started on port {self.server_port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def _handle_incoming_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connection from another device"""
        try:
            remote_device_id = None
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    if message_type == 'device_hello':
                        remote_device_id = data.get('device_id')
                        await self._handle_device_hello(websocket, data)
                    
                    elif message_type == 'sync_state':
                        await self._handle_sync_message(websocket, data)
                    
                    elif message_type == 'handoff_request':
                        await self._handle_handoff_request(websocket, data)
                    
                    elif message_type == 'conflict_resolution':
                        await self._handle_conflict_resolution(websocket, data)
                    
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON from device")
                except Exception as e:
                    logger.error(f"Error handling message from device: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            if remote_device_id:
                logger.info(f"Device {remote_device_id} disconnected")
                if remote_device_id in self.known_devices:
                    self.known_devices[remote_device_id].connection_status = ConnectionStatus.DISCONNECTED
        
        except Exception as e:
            logger.error(f"Error in incoming connection handler: {e}")
    
    async def _handle_device_hello(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle initial device hello message"""
        try:
            device_info_data = data.get('device_info')
            if not device_info_data:
                return
            
            # Parse device info
            device_info = DeviceInfo(
                device_id=device_info_data['device_id'],
                device_name=device_info_data['device_name'],
                device_type=DeviceType(device_info_data['device_type']),
                capabilities=DeviceCapabilities(**device_info_data['capabilities']),
                os_version=device_info_data['os_version'],
                app_version=device_info_data['app_version'],
                user_id=device_info_data['user_id'],
                last_seen=datetime.now(),
                connection_status=ConnectionStatus.CONNECTED
            )
            
            # Validate device (same user, etc.)
            if not await self._validate_device(device_info):
                await websocket.send(json.dumps({
                    'type': 'device_rejected',
                    'reason': 'Device validation failed'
                }))
                return
            
            # Add to known devices
            self.known_devices[device_info.device_id] = device_info
            
            # Send our device info
            response = {
                'type': 'device_hello_response',
                'device_info': asdict(self.device_info),
                'sync_preferences': self.sync_preferences
            }
            await websocket.send(json.dumps(response, default=str))
            
            # Start sync process
            await self._initiate_sync_with_device(device_info.device_id, websocket)
            
            logger.info(f"Device {device_info.device_id} connected and validated")
            
        except Exception as e:
            logger.error(f"Error handling device hello: {e}")
    
    async def _validate_device(self, device_info: DeviceInfo) -> bool:
        """Validate incoming device connection"""
        # Check if same user
        if device_info.user_id != self.device_info.user_id:
            return False
        
        # Check trust level (simplified)
        # In real implementation, would check certificates, keys, etc.
        device_info.trust_level = 0.8  # Assume trusted for now
        
        return device_info.trust_level >= self.sync_preferences['trust_threshold']
    
    async def _initiate_sync_with_device(self, device_id: str, websocket: WebSocketServerProtocol):
        """Initiate synchronization with a connected device"""
        try:
            # Send current state checksums for comparison
            state_checksums = {}
            for state_id, state in self.local_state.items():
                state_checksums[state_id] = {
                    'checksum': state.checksum,
                    'version': state.version,
                    'timestamp': state.timestamp.isoformat()
                }
            
            sync_request = {
                'type': 'sync_request',
                'device_id': self.device_id,
                'state_checksums': state_checksums,
                'sync_scope': self.sync_preferences['sync_scope'].value
            }
            
            await websocket.send(json.dumps(sync_request))
            
        except Exception as e:
            logger.error(f"Error initiating sync with device {device_id}: {e}")
    
    async def _handle_sync_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle synchronization message from another device"""
        try:
            message_type = data.get('sync_type')
            
            if message_type == 'sync_request':
                await self._handle_sync_request(websocket, data)
            elif message_type == 'sync_response':
                await self._handle_sync_response(websocket, data)
            elif message_type == 'state_update':
                await self._handle_state_update(websocket, data)
            elif message_type == 'conflict_detected':
                await self._handle_conflict_detected(websocket, data)
            
        except Exception as e:
            logger.error(f"Error handling sync message: {e}")
    
    async def _handle_sync_request(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle sync request from another device"""
        try:
            remote_checksums = data.get('state_checksums', {})
            sync_scope = data.get('sync_scope', 'full')
            
            states_to_send = []
            states_to_request = []
            
            # Compare our state with remote checksums
            for state_id, local_state in self.local_state.items():
                remote_info = remote_checksums.get(state_id)
                
                if not remote_info:
                    # Remote doesn't have this state - send it
                    states_to_send.append(state_id)
                else:
                    # Compare versions and timestamps
                    remote_version = remote_info.get('version', 0)
                    remote_timestamp = datetime.fromisoformat(remote_info['timestamp'])
                    
                    if local_state.version > remote_version:
                        states_to_send.append(state_id)
                    elif local_state.version < remote_version:
                        states_to_request.append(state_id)
                    elif local_state.timestamp != remote_timestamp:
                        # Same version but different timestamps - potential conflict
                        await self._detect_conflict(state_id, local_state, remote_info)
            
            # Check for states remote has that we don't
            for state_id in remote_checksums:
                if state_id not in self.local_state:
                    states_to_request.append(state_id)
            
            # Send response
            sync_response = {
                'type': 'sync_response',
                'device_id': self.device_id,
                'states_to_send': [asdict(self.local_state[sid]) for sid in states_to_send],
                'states_to_request': states_to_request
            }
            
            await websocket.send(json.dumps(sync_response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling sync request: {e}")
    
    async def _handle_sync_response(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle sync response from another device"""
        try:
            states_received = data.get('states_to_send', [])
            states_to_request = data.get('states_to_request', [])
            
            # Process received states
            for state_data in states_received:
                await self._merge_received_state(state_data)
            
            # Send requested states
            if states_to_request:
                states_to_send = []
                for state_id in states_to_request:
                    if state_id in self.local_state:
                        states_to_send.append(asdict(self.local_state[state_id]))
                
                update_message = {
                    'type': 'state_update',
                    'device_id': self.device_id,
                    'states': states_to_send
                }
                
                await websocket.send(json.dumps(update_message, default=str))
            
        except Exception as e:
            logger.error(f"Error handling sync response: {e}")
    
    async def _merge_received_state(self, state_data: Dict[str, Any]):
        """Merge received state with local state"""
        try:
            state_id = state_data['state_id']
            received_state = SyncState(**state_data)
            
            if state_id in self.local_state:
                local_state = self.local_state[state_id]
                
                # Check for conflicts
                if (received_state.version == local_state.version and 
                    received_state.checksum != local_state.checksum):
                    
                    await self._handle_merge_conflict(state_id, local_state, received_state)
                    return
                
                # Update if received state is newer
                if received_state.version > local_state.version:
                    self.local_state[state_id] = received_state
                    self.state_versions[state_id] = received_state.version
                    logger.info(f"Updated state {state_id} to version {received_state.version}")
            else:
                # New state - add it
                self.local_state[state_id] = received_state
                self.state_versions[state_id] = received_state.version
                logger.info(f"Added new state {state_id}")
            
        except Exception as e:
            logger.error(f"Error merging received state: {e}")
    
    async def _handle_merge_conflict(self, state_id: str, local_state: SyncState, 
                                   remote_state: SyncState):
        """Handle merge conflict between local and remote state"""
        try:
            conflict_resolution = self.sync_preferences['conflict_resolution']
            
            if conflict_resolution == ConflictResolution.LATEST_WINS:
                if remote_state.timestamp > local_state.timestamp:
                    self.local_state[state_id] = remote_state
                    logger.info(f"Resolved conflict for {state_id}: remote state wins (latest)")
                else:
                    logger.info(f"Resolved conflict for {state_id}: local state wins (latest)")
            
            elif conflict_resolution == ConflictResolution.DEVICE_PRIORITY:
                # Use device priority (simplified - desktop > laptop > mobile)
                if await self._should_remote_device_win(remote_state.device_id):
                    self.local_state[state_id] = remote_state
                    logger.info(f"Resolved conflict for {state_id}: remote device priority wins")
                else:
                    logger.info(f"Resolved conflict for {state_id}: local device priority wins")
            
            elif conflict_resolution == ConflictResolution.MERGE:
                merged_state = await self._merge_conflicting_states(local_state, remote_state)
                if merged_state:
                    self.local_state[state_id] = merged_state
                    logger.info(f"Resolved conflict for {state_id}: states merged")
            
            else:
                # Add to conflict queue for user resolution
                self.conflict_queue.append({
                    'state_id': state_id,
                    'local_state': local_state,
                    'remote_state': remote_state,
                    'timestamp': datetime.now()
                })
                logger.info(f"Conflict queued for user resolution: {state_id}")
            
        except Exception as e:
            logger.error(f"Error handling merge conflict: {e}")
    
    async def _should_remote_device_win(self, remote_device_id: str) -> bool:
        """Determine if remote device should win based on priority"""
        if remote_device_id not in self.known_devices:
            return False
        
        remote_device = self.known_devices[remote_device_id]
        local_device = self.device_info
        
        # Priority: Desktop > Laptop > Tablet > Phone
        priority_order = [DeviceType.DESKTOP, DeviceType.LAPTOP, DeviceType.TABLET, DeviceType.SMARTPHONE]
        
        try:
            local_priority = priority_order.index(local_device.device_type)
            remote_priority = priority_order.index(remote_device.device_type)
            
            return remote_priority < local_priority
        except ValueError:
            return False
    
    async def _merge_conflicting_states(self, local_state: SyncState, 
                                      remote_state: SyncState) -> Optional[SyncState]:
        """Merge two conflicting states"""
        try:
            # Simple merge strategy - combine data from both states
            merged_data = local_state.data.copy()
            
            for key, value in remote_state.data.items():
                if key not in merged_data:
                    merged_data[key] = value
                elif key in merged_data and merged_data[key] != value:
                    # For conflicting values, keep both with prefixes
                    merged_data[f"local_{key}"] = merged_data[key]
                    merged_data[f"remote_{key}"] = value
                    del merged_data[key]
            
            # Create merged state
            merged_state = SyncState(
                device_id=local_state.device_id,
                state_id=local_state.state_id,
                state_type=local_state.state_type,
                data=merged_data,
                timestamp=max(local_state.timestamp, remote_state.timestamp),
                checksum=self._calculate_checksum(merged_data),
                version=max(local_state.version, remote_state.version) + 1
            )
            
            return merged_state
            
        except Exception as e:
            logger.error(f"Error merging conflicting states: {e}")
            return None
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for state data"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    async def connect_to_device(self, device_address: str, device_port: int) -> bool:
        """Connect to another device"""
        try:
            uri = f"ws://{device_address}:{device_port}"
            websocket = await websockets.connect(uri)
            
            # Send hello message
            hello_message = {
                'type': 'device_hello',
                'device_info': asdict(self.device_info),
                'sync_preferences': self.sync_preferences
            }
            
            await websocket.send(json.dumps(hello_message, default=str))
            
            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get('type') == 'device_hello_response':
                device_info_data = response_data.get('device_info')
                remote_device = DeviceInfo(**device_info_data)
                self.known_devices[remote_device.device_id] = remote_device
                self.active_connections[remote_device.device_id] = websocket
                
                # Start message handling for this connection
                asyncio.create_task(self._handle_outgoing_connection(websocket, remote_device.device_id))
                
                logger.info(f"Connected to device {remote_device.device_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to device at {device_address}:{device_port}: {e}")
            return False
    
    async def _handle_outgoing_connection(self, websocket: WebSocketClientProtocol, device_id: str):
        """Handle messages from outgoing connection"""
        try:
            async for message in websocket:
                data = json.loads(message)
                message_type = data.get('type')
                
                if message_type == 'sync_request':
                    await self._handle_sync_request(websocket, data)
                elif message_type == 'sync_response':
                    await self._handle_sync_response(websocket, data)
                # Handle other message types...
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection to device {device_id} closed")
            if device_id in self.active_connections:
                del self.active_connections[device_id]
            if device_id in self.known_devices:
                self.known_devices[device_id].connection_status = ConnectionStatus.DISCONNECTED
        
        except Exception as e:
            logger.error(f"Error handling outgoing connection to {device_id}: {e}")
    
    async def update_local_state(self, state_id: str, state_type: str, data: Dict[str, Any]):
        """Update local state and propagate to connected devices"""
        try:
            # Calculate checksum
            checksum = self._calculate_checksum(data)
            
            # Create or update state
            if state_id in self.local_state:
                version = self.local_state[state_id].version + 1
            else:
                version = 1
            
            new_state = SyncState(
                device_id=self.device_id,
                state_id=state_id,
                state_type=state_type,
                data=data,
                timestamp=datetime.now(),
                checksum=checksum,
                version=version
            )
            
            self.local_state[state_id] = new_state
            self.state_versions[state_id] = version
            
            # Add to sync queue for propagation
            self.sync_queue.append({
                'action': 'state_update',
                'state': new_state,
                'target_devices': 'all'
            })
            
            logger.info(f"Updated local state {state_id} to version {version}")
            
        except Exception as e:
            logger.error(f"Error updating local state: {e}")
    
    async def request_handoff(self, target_device_id: str, handoff_type: str, 
                            state_data: Dict[str, Any]) -> bool:
        """Request handoff to another device"""
        try:
            if target_device_id not in self.active_connections:
                logger.warning(f"Target device {target_device_id} not connected")
                return False
            
            request_id = str(uuid.uuid4())
            handoff_request = HandoffRequest(
                request_id=request_id,
                source_device=self.device_id,
                target_device=target_device_id,
                handoff_type=handoff_type,
                state_data=state_data,
                timestamp=datetime.now(),
                expiry_time=datetime.now() + timedelta(minutes=5)
            )
            
            self.handoff_requests[request_id] = handoff_request
            
            # Send handoff request
            websocket = self.active_connections[target_device_id]
            message = {
                'type': 'handoff_request',
                'request_id': request_id,
                'handoff_type': handoff_type,
                'state_data': state_data,
                'source_device': self.device_id,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(message, default=str))
            
            logger.info(f"Handoff request {request_id} sent to device {target_device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error requesting handoff: {e}")
            return False
    
    async def _handle_handoff_request(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle incoming handoff request"""
        try:
            request_id = data.get('request_id')
            handoff_type = data.get('handoff_type')
            state_data = data.get('state_data', {})
            source_device = data.get('source_device')
            
            # Validate handoff capability
            can_handle = await self._can_handle_handoff(handoff_type, state_data)
            
            response = {
                'type': 'handoff_response',
                'request_id': request_id,
                'accepted': can_handle,
                'device_id': self.device_id
            }
            
            if can_handle:
                # Accept handoff and prepare to receive state
                await self._prepare_for_handoff(handoff_type, state_data)
                response['message'] = 'Handoff accepted'
                logger.info(f"Accepted handoff request {request_id} from {source_device}")
            else:
                response['message'] = 'Handoff rejected - insufficient capabilities'
                logger.info(f"Rejected handoff request {request_id} from {source_device}")
            
            await websocket.send(json.dumps(response))
            
        except Exception as e:
            logger.error(f"Error handling handoff request: {e}")
    
    async def _can_handle_handoff(self, handoff_type: str, state_data: Dict[str, Any]) -> bool:
        """Check if device can handle requested handoff"""
        # Check device capabilities
        capabilities = self.device_info.capabilities
        
        if handoff_type == 'video_streaming':
            return capabilities.screen_size[0] >= 1280 and capabilities.has_speakers
        elif handoff_type == 'document_editing':
            return capabilities.keyboard_available or capabilities.touch_enabled
        elif handoff_type == 'presentation':
            return capabilities.screen_size[0] >= 1024
        elif handoff_type == 'gaming':
            return capabilities.processing_power > 0.5 and capabilities.gpu_capable
        
        # Default: can handle if has screen
        return capabilities.screen_size[0] > 0
    
    async def _prepare_for_handoff(self, handoff_type: str, state_data: Dict[str, Any]):
        """Prepare device to receive handoff"""
        # Implementation depends on handoff type
        if handoff_type == 'video_streaming':
            # Prepare video player, allocate bandwidth
            pass
        elif handoff_type == 'document_editing':
            # Prepare editor, load document
            pass
        # ... other handoff types
    
    async def _sync_loop(self):
        """Background synchronization loop"""
        while self.is_running:
            try:
                # Process sync queue
                while self.sync_queue and len(self.sync_queue) > 0:
                    sync_item = self.sync_queue.popleft()
                    await self._process_sync_item(sync_item)
                
                # Check for expired handoff requests
                await self._cleanup_expired_handoffs()
                
                # Periodic sync with all connected devices
                await self._periodic_sync()
                
                await asyncio.sleep(10)  # Run every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(30)
    
    async def _process_sync_item(self, sync_item: Dict[str, Any]):
        """Process item from sync queue"""
        try:
            action = sync_item['action']
            
            if action == 'state_update':
                state = sync_item['state']
                target_devices = sync_item['target_devices']
                
                # Send state update to target devices
                update_message = {
                    'type': 'sync_state',
                    'sync_type': 'state_update',
                    'state': asdict(state),
                    'device_id': self.device_id
                }
                
                message_str = json.dumps(update_message, default=str)
                
                if target_devices == 'all':
                    for device_id, websocket in self.active_connections.items():
                        try:
                            await websocket.send(message_str)
                        except Exception as e:
                            logger.error(f"Failed to send update to {device_id}: {e}")
                else:
                    for device_id in target_devices:
                        if device_id in self.active_connections:
                            try:
                                await self.active_connections[device_id].send(message_str)
                            except Exception as e:
                                logger.error(f"Failed to send update to {device_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing sync item: {e}")
    
    async def _cleanup_expired_handoffs(self):
        """Clean up expired handoff requests"""
        current_time = datetime.now()
        expired_requests = []
        
        for request_id, request in self.handoff_requests.items():
            if request.expiry_time and current_time > request.expiry_time:
                expired_requests.append(request_id)
        
        for request_id in expired_requests:
            del self.handoff_requests[request_id]
            logger.info(f"Expired handoff request {request_id}")
    
    async def _periodic_sync(self):
        """Perform periodic sync with all connected devices"""
        current_time = datetime.now()
        
        for device_id, websocket in self.active_connections.items():
            last_sync = self.last_sync_times.get(device_id, current_time - timedelta(hours=1))
            
            if (current_time - last_sync).total_seconds() > self.sync_preferences['max_sync_interval']:
                try:
                    await self._initiate_sync_with_device(device_id, websocket)
                    self.last_sync_times[device_id] = current_time
                except Exception as e:
                    logger.error(f"Error in periodic sync with {device_id}: {e}")
    
    async def _device_discovery_loop(self):
        """Background device discovery loop"""
        while self.is_running:
            try:
                # Simple device discovery - in real implementation would use mDNS, etc.
                await self._discover_nearby_devices()
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error in device discovery: {e}")
                await asyncio.sleep(120)
    
    async def _discover_nearby_devices(self):
        """Discover nearby devices (simplified implementation)"""
        # In real implementation, would use network discovery protocols
        # For now, just simulate discovery
        pass
    
    async def get_device_status(self) -> Dict[str, Any]:
        """Get current device synchronization status"""
        connected_devices = [
            {
                'device_id': device.device_id,
                'device_name': device.device_name,
                'device_type': device.device_type.value,
                'connection_status': device.connection_status.value,
                'last_seen': device.last_seen.isoformat(),
                'trust_level': device.trust_level
            }
            for device in self.known_devices.values()
        ]
        
        return {
            'device_id': self.device_id,
            'server_port': self.server_port,
            'is_running': self.is_running,
            'connected_devices': connected_devices,
            'active_connections': len(self.active_connections),
            'local_states': len(self.local_state),
            'sync_queue_size': len(self.sync_queue),
            'conflict_queue_size': len(self.conflict_queue),
            'active_handoffs': len(self.handoff_requests),
            'sync_preferences': self.sync_preferences
        }

# Usage example
async def main():
    """Example usage of Cross-Device Synchronization"""
    
    # Create device capabilities
    laptop_capabilities = DeviceCapabilities(
        screen_size=(1920, 1080),
        input_methods=['mouse', 'keyboard', 'touchpad'],
        processing_power=0.8,
        memory_gb=16,
        storage_gb=512,
        network_speed=100.0,
        battery_powered=True,
        has_camera=True,
        has_microphone=True,
        has_speakers=True,
        gpu_capable=True,
        touch_enabled=False,
        keyboard_available=True,
        mouse_available=True
    )
    
    # Create device info
    device_info = DeviceInfo(
        device_id="laptop_001",
        device_name="My Laptop",
        device_type=DeviceType.LAPTOP,
        capabilities=laptop_capabilities,
        os_version="Windows 11",
        app_version="1.0.0",
        user_id="user123",
        last_seen=datetime.now(),
        connection_status=ConnectionStatus.DISCONNECTED
    )
    
    # Create synchronizer
    sync = CrossDeviceSynchronizer("laptop_001", device_info)
    
    print("Starting cross-device synchronization...")
    await sync.start_synchronization()
    
    # Update some local state
    await sync.update_local_state(
        "user_preferences",
        "configuration",
        {
            "theme": "dark",
            "language": "en",
            "notifications": True
        }
    )
    
    # Get status
    status = await sync.get_device_status()
    print(f"Synchronization status: {status}")
    
    # Let it run for a bit
    await asyncio.sleep(2)
    
    await sync.stop_synchronization()

if __name__ == "__main__":
    asyncio.run(main())