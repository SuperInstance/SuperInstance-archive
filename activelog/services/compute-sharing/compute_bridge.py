"""
Compute Bridge - Desktop to Phone Power Sharing

Seamlessly bridges computing power between desktop and mobile devices,
enabling resource sharing and distributed processing.
"""

import asyncio
import json
import logging
import platform
import psutil
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
import aiohttp
import websockets
import subprocess
import threading
import queue
import hashlib

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    DESKTOP = "desktop"
    LAPTOP = "laptop"
    MOBILE = "mobile"
    TABLET = "tablet"
    SERVER = "server"
    EMBEDDED = "embedded"

class ConnectionMethod(Enum):
    WEBSOCKET = "websocket"
    HTTP_API = "http_api"
    TCP_SOCKET = "tcp_socket"
    BLUETOOTH = "bluetooth"
    WIFI_DIRECT = "wifi_direct"
    USB = "usb"

class TaskType(Enum):
    CPU_INTENSIVE = "cpu_intensive"
    GPU_COMPUTE = "gpu_compute"
    MEMORY_HEAVY = "memory_heavy"
    IO_BOUND = "io_bound"
    NETWORK_BOUND = "network_bound"
    MIXED = "mixed"

@dataclass
class DeviceCapabilities:
    device_id: str
    device_type: DeviceType
    cpu_cores: int
    cpu_frequency: float  # GHz
    memory_gb: float
    storage_gb: float
    gpu_available: bool
    gpu_memory_gb: float
    network_speed_mbps: float
    battery_level: Optional[float] = None  # For mobile devices
    is_charging: Optional[bool] = None
    thermal_state: str = "normal"  # normal, warm, hot, critical

@dataclass
class ComputeTask:
    task_id: str
    task_type: TaskType
    description: str
    estimated_cpu_time: float  # seconds
    estimated_memory_mb: float
    priority: int  # 1-10, higher = more important
    payload_data: Any
    result_callback: Optional[Callable] = None
    timeout_seconds: float = 300.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_device: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_data: Optional[Any] = None
    error_message: Optional[str] = None

@dataclass
class DeviceConnection:
    device_id: str
    device_info: DeviceCapabilities
    connection_method: ConnectionMethod
    websocket: Optional[Any] = None
    last_ping: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    current_load: float = 0.0
    trust_score: float = 0.5  # 0-1, higher = more trusted

class ComputeBridge:
    """
    Main compute bridge managing desktop-to-phone and device-to-device
    power sharing with intelligent task distribution.
    """
    
    def __init__(self, port: int = 8440):
        self.port = port
        self.device_id = str(uuid.uuid4())
        self.connections = {}  # device_id -> DeviceConnection
        self.pending_tasks = queue.PriorityQueue()
        self.active_tasks = {}  # task_id -> ComputeTask
        self.completed_tasks = {}  # task_id -> ComputeTask
        
        # Local device capabilities
        self.local_capabilities = self._detect_local_capabilities()
        self.server = None
        self.running = False
        
        # Task execution
        self.executor_thread = None
        self.max_concurrent_tasks = min(psutil.cpu_count(), 4)
        self.current_task_count = 0
        
        # Performance metrics
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_compute_time": 0.0,
            "power_saved_wh": 0.0,  # Estimated power savings
            "devices_connected": 0,
            "network_bytes_transferred": 0
        }
        
        # Security
        self.trusted_devices = set()
        self.device_certificates = {}
        
    async def start(self):
        """Start the compute bridge server"""
        self.running = True
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self._handle_websocket_connection,
            "0.0.0.0",
            self.port
        )
        
        # Start task executor
        self.executor_thread = threading.Thread(target=self._task_executor_loop)
        self.executor_thread.start()
        
        # Start device discovery
        asyncio.create_task(self._device_discovery_loop())
        
        # Start health monitoring
        asyncio.create_task(self._health_monitor_loop())
        
        logger.info(f"Compute Bridge started on port {self.port}")
        logger.info(f"Device ID: {self.device_id}")
        logger.info(f"Local capabilities: {self.local_capabilities}")
    
    async def stop(self):
        """Stop the compute bridge"""
        self.running = False
        
        # Close all connections
        for connection in self.connections.values():
            if connection.websocket:
                await connection.websocket.close()
        
        # Stop server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Wait for executor to finish
        if self.executor_thread:
            self.executor_thread.join(timeout=5.0)
        
        logger.info("Compute Bridge stopped")
    
    def _detect_local_capabilities(self) -> DeviceCapabilities:
        """Detect local device capabilities"""
        try:
            # CPU info
            cpu_count = psutil.cpu_count(logical=False) or 1
            cpu_freq = psutil.cpu_freq()
            cpu_frequency = cpu_freq.current / 1000.0 if cpu_freq else 2.0  # Default 2GHz
            
            # Memory info
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            
            # Storage info
            disk = psutil.disk_usage('/')
            storage_gb = disk.total / (1024**3)
            
            # Network speed (estimated)
            network_speed = 100.0  # Default 100 Mbps
            
            # Device type detection
            device_type = DeviceType.DESKTOP
            if platform.system() == "Darwin":
                # Mac detection logic
                device_type = DeviceType.LAPTOP if "MacBook" in platform.machine() else DeviceType.DESKTOP
            elif platform.system() == "Linux":
                # Linux device detection
                if "arm" in platform.machine().lower():
                    device_type = DeviceType.EMBEDDED
                else:
                    device_type = DeviceType.DESKTOP
            elif platform.system() == "Windows":
                device_type = DeviceType.DESKTOP
            
            # GPU detection (basic)
            gpu_available = False
            gpu_memory = 0.0
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_available = True
                    gpu_memory = max([gpu.memoryTotal for gpu in gpus]) / 1024.0  # GB
            except ImportError:
                pass  # GPU detection not available
            
            # Battery info (for laptops/mobile)
            battery_level = None
            is_charging = None
            try:
                battery = psutil.sensors_battery()
                if battery:
                    battery_level = battery.percent
                    is_charging = battery.power_plugged
            except:
                pass
            
            return DeviceCapabilities(
                device_id=self.device_id,
                device_type=device_type,
                cpu_cores=cpu_count,
                cpu_frequency=cpu_frequency,
                memory_gb=memory_gb,
                storage_gb=storage_gb,
                gpu_available=gpu_available,
                gpu_memory_gb=gpu_memory,
                network_speed_mbps=network_speed,
                battery_level=battery_level,
                is_charging=is_charging
            )
            
        except Exception as e:
            logger.error(f"Failed to detect capabilities: {e}")
            # Return minimal capabilities as fallback
            return DeviceCapabilities(
                device_id=self.device_id,
                device_type=DeviceType.DESKTOP,
                cpu_cores=2,
                cpu_frequency=2.0,
                memory_gb=4.0,
                storage_gb=100.0,
                gpu_available=False,
                gpu_memory_gb=0.0,
                network_speed_mbps=100.0
            )
    
    async def _handle_websocket_connection(self, websocket, path):
        """Handle incoming WebSocket connections"""
        try:
            # Handshake and device registration
            handshake_msg = await websocket.recv()
            handshake_data = json.loads(handshake_msg)
            
            if handshake_data.get("type") != "device_registration":
                await websocket.send(json.dumps({"error": "Invalid handshake"}))
                return
            
            device_info = DeviceCapabilities(**handshake_data["device_info"])
            device_id = device_info.device_id
            
            # Verify device (basic security)
            if not self._verify_device(device_id, handshake_data.get("auth_token")):
                await websocket.send(json.dumps({"error": "Device verification failed"}))
                return
            
            # Register connection
            connection = DeviceConnection(
                device_id=device_id,
                device_info=device_info,
                connection_method=ConnectionMethod.WEBSOCKET,
                websocket=websocket
            )
            
            self.connections[device_id] = connection
            self.metrics["devices_connected"] = len(self.connections)
            
            # Send registration confirmation
            await websocket.send(json.dumps({
                "type": "registration_confirmed",
                "bridge_device_id": self.device_id,
                "bridge_capabilities": self.local_capabilities.__dict__
            }))
            
            logger.info(f"Device connected: {device_id} ({device_info.device_type.value})")
            
            # Handle messages from device
            async for message in websocket:
                await self._handle_device_message(device_id, json.loads(message))
                
        except websockets.exceptions.ConnectionClosed:
            if device_id in self.connections:
                del self.connections[device_id]
                self.metrics["devices_connected"] = len(self.connections)
                logger.info(f"Device disconnected: {device_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
    
    def _verify_device(self, device_id: str, auth_token: Optional[str]) -> bool:
        """Basic device verification"""
        # For now, accept all devices
        # In production, implement proper authentication
        return True
    
    async def _handle_device_message(self, device_id: str, message: Dict[str, Any]):
        """Handle messages from connected devices"""
        msg_type = message.get("type")
        
        if msg_type == "ping":
            connection = self.connections.get(device_id)
            if connection:
                connection.last_ping = datetime.now(timezone.utc)
                await connection.websocket.send(json.dumps({"type": "pong"}))
        
        elif msg_type == "task_result":
            await self._handle_task_result(device_id, message)
        
        elif msg_type == "resource_update":
            await self._handle_resource_update(device_id, message)
        
        elif msg_type == "error":
            await self._handle_device_error(device_id, message)
        
        else:
            logger.warning(f"Unknown message type from {device_id}: {msg_type}")
    
    async def _handle_task_result(self, device_id: str, message: Dict[str, Any]):
        """Handle task completion from device"""
        task_id = message.get("task_id")
        if task_id not in self.active_tasks:
            return
        
        task = self.active_tasks[task_id]
        task.completed_at = datetime.now(timezone.utc)
        
        if message.get("success"):
            task.result_data = message.get("result")
            self.metrics["tasks_completed"] += 1
            
            # Calculate compute time
            if task.started_at:
                compute_time = (task.completed_at - task.started_at).total_seconds()
                self.metrics["total_compute_time"] += compute_time
                
                # Estimate power savings
                estimated_power_saved = self._calculate_power_savings(task, device_id)
                self.metrics["power_saved_wh"] += estimated_power_saved
        else:
            task.error_message = message.get("error", "Unknown error")
            self.metrics["tasks_failed"] += 1
        
        # Move to completed tasks
        self.completed_tasks[task_id] = task
        del self.active_tasks[task_id]
        self.current_task_count -= 1
        
        # Call result callback if provided
        if task.result_callback:
            try:
                if asyncio.iscoroutinefunction(task.result_callback):
                    await task.result_callback(task)
                else:
                    task.result_callback(task)
            except Exception as e:
                logger.error(f"Task callback error: {e}")
        
        logger.info(f"Task completed: {task_id} on device {device_id}")
    
    async def _handle_resource_update(self, device_id: str, message: Dict[str, Any]):
        """Handle resource usage updates from device"""
        connection = self.connections.get(device_id)
        if connection:
            connection.current_load = message.get("cpu_usage", 0.0)
            # Update device capabilities if provided
            if "capabilities" in message:
                connection.device_info = DeviceCapabilities(**message["capabilities"])
    
    async def _handle_device_error(self, device_id: str, message: Dict[str, Any]):
        """Handle error reports from device"""
        logger.error(f"Device {device_id} reported error: {message.get('error', 'Unknown error')}")
        
        # If device is overheating or has critical error, reduce its task allocation
        error_type = message.get("error_type", "")
        if error_type in ["thermal", "memory", "critical"]:
            connection = self.connections.get(device_id)
            if connection:
                connection.trust_score *= 0.8  # Reduce trust
    
    def _calculate_power_savings(self, task: ComputeTask, remote_device_id: str) -> float:
        """Calculate estimated power savings from remote execution"""
        if not task.started_at or not task.completed_at:
            return 0.0
        
        execution_time_hours = (task.completed_at - task.started_at).total_seconds() / 3600
        
        # Estimate local power consumption (simplified)
        local_power_w = self.local_capabilities.cpu_cores * 15  # ~15W per core
        local_consumption_wh = local_power_w * execution_time_hours
        
        # Estimate remote device power efficiency
        remote_connection = self.connections.get(remote_device_id)
        if remote_connection and remote_connection.device_info.device_type == DeviceType.MOBILE:
            # Mobile devices are typically more power-efficient for light tasks
            efficiency_factor = 0.3  # 30% of desktop power
        else:
            efficiency_factor = 0.8  # Similar power consumption
        
        remote_consumption_wh = local_consumption_wh * efficiency_factor
        power_saved_wh = max(0, local_consumption_wh - remote_consumption_wh)
        
        return power_saved_wh
    
    def submit_task(self, task: ComputeTask) -> str:
        """Submit a compute task for execution"""
        task_priority = -task.priority  # Negative for max-heap behavior
        self.pending_tasks.put((task_priority, task.created_at, task))
        logger.info(f"Task submitted: {task.task_id} ({task.task_type.value})")
        return task.task_id
    
    def _task_executor_loop(self):
        """Main task execution loop (runs in separate thread)"""
        while self.running:
            try:
                if self.current_task_count >= self.max_concurrent_tasks:
                    time.sleep(0.1)
                    continue
                
                try:
                    # Get next task (blocks with timeout)
                    priority, created_at, task = self.pending_tasks.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Find best device for task
                best_device = self._select_best_device(task)
                
                if best_device:
                    # Assign task to remote device
                    asyncio.run(self._assign_task_to_device(task, best_device))
                else:
                    # Execute locally
                    asyncio.run(self._execute_task_locally(task))
                
                self.current_task_count += 1
                self.active_tasks[task.task_id] = task
                
            except Exception as e:
                logger.error(f"Task executor error: {e}")
    
    def _select_best_device(self, task: ComputeTask) -> Optional[str]:
        """Select the best device for executing a task"""
        if not self.connections:
            return None  # No remote devices available
        
        best_device = None
        best_score = -1.0
        
        for device_id, connection in self.connections.items():
            if not connection.is_active:
                continue
            
            device_info = connection.device_info
            score = self._calculate_device_score(task, device_info, connection)
            
            if score > best_score:
                best_score = score
                best_device = device_id
        
        # Only use remote device if significantly better than local
        if best_score > 0.6:  # Threshold for remote execution
            return best_device
        
        return None  # Execute locally
    
    def _calculate_device_score(self, task: ComputeTask, device_info: DeviceCapabilities, 
                               connection: DeviceConnection) -> float:
        """Calculate suitability score for device-task pairing"""
        score = 0.0
        
        # CPU capability
        cpu_score = min(1.0, device_info.cpu_cores / max(1, task.estimated_cpu_time))
        score += cpu_score * 0.3
        
        # Memory capability
        memory_score = min(1.0, (device_info.memory_gb * 1024) / task.estimated_memory_mb)
        score += memory_score * 0.2
        
        # Current load (prefer less busy devices)
        load_score = 1.0 - min(1.0, connection.current_load)
        score += load_score * 0.2
        
        # Trust score
        score += connection.trust_score * 0.1
        
        # Task type specialization
        specialization_score = self._get_specialization_score(task.task_type, device_info)
        score += specialization_score * 0.2
        
        return score
    
    def _get_specialization_score(self, task_type: TaskType, device_info: DeviceCapabilities) -> float:
        """Get device specialization score for task type"""
        if task_type == TaskType.GPU_COMPUTE:
            return 1.0 if device_info.gpu_available else 0.0
        elif task_type == TaskType.CPU_INTENSIVE:
            return min(1.0, device_info.cpu_cores / 8.0)  # Normalize to 8 cores
        elif task_type == TaskType.MEMORY_HEAVY:
            return min(1.0, device_info.memory_gb / 16.0)  # Normalize to 16GB
        else:
            return 0.5  # Neutral for other task types
    
    async def _assign_task_to_device(self, task: ComputeTask, device_id: str):
        """Assign task to remote device"""
        connection = self.connections.get(device_id)
        if not connection or not connection.websocket:
            await self._execute_task_locally(task)
            return
        
        task.assigned_device = device_id
        task.started_at = datetime.now(timezone.utc)
        
        # Send task to device
        task_message = {
            "type": "execute_task",
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "description": task.description,
            "payload": task.payload_data,
            "timeout_seconds": task.timeout_seconds
        }
        
        try:
            await connection.websocket.send(json.dumps(task_message))
            logger.info(f"Task {task.task_id} assigned to device {device_id}")
        except Exception as e:
            logger.error(f"Failed to send task to device {device_id}: {e}")
            await self._execute_task_locally(task)
    
    async def _execute_task_locally(self, task: ComputeTask):
        """Execute task on local device"""
        task.assigned_device = self.device_id
        task.started_at = datetime.now(timezone.utc)
        
        try:
            # Simple task execution (placeholder)
            await asyncio.sleep(min(task.estimated_cpu_time, 1.0))  # Simulate work
            
            # Mock result based on task type
            if task.task_type == TaskType.CPU_INTENSIVE:
                result = {"computation_result": "completed", "iterations": 1000}
            elif task.task_type == TaskType.MEMORY_HEAVY:
                result = {"data_processed": "large_dataset", "memory_used_mb": task.estimated_memory_mb}
            else:
                result = {"status": "completed", "output": "task_result"}
            
            task.result_data = result
            task.completed_at = datetime.now(timezone.utc)
            
            # Move to completed tasks
            self.completed_tasks[task.task_id] = task
            self.current_task_count -= 1
            self.metrics["tasks_completed"] += 1
            
            # Call result callback
            if task.result_callback:
                try:
                    if asyncio.iscoroutinefunction(task.result_callback):
                        await task.result_callback(task)
                    else:
                        task.result_callback(task)
                except Exception as e:
                    logger.error(f"Local task callback error: {e}")
            
            logger.info(f"Task {task.task_id} completed locally")
            
        except Exception as e:
            task.error_message = str(e)
            task.completed_at = datetime.now(timezone.utc)
            self.completed_tasks[task.task_id] = task
            self.current_task_count -= 1
            self.metrics["tasks_failed"] += 1
            logger.error(f"Local task execution failed: {e}")
    
    async def _device_discovery_loop(self):
        """Discover devices on local network"""
        while self.running:
            try:
                await self._broadcast_discovery()
                await asyncio.sleep(30)  # Discovery every 30 seconds
            except Exception as e:
                logger.error(f"Device discovery error: {e}")
    
    async def _broadcast_discovery(self):
        """Broadcast device discovery message"""
        discovery_message = {
            "type": "device_discovery",
            "device_id": self.device_id,
            "device_capabilities": self.local_capabilities.__dict__,
            "bridge_port": self.port,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # UDP broadcast for local network discovery
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            message_bytes = json.dumps(discovery_message).encode('utf-8')
            sock.sendto(message_bytes, ('<broadcast>', self.port + 1))
            sock.close()
            
        except Exception as e:
            logger.error(f"Discovery broadcast failed: {e}")
    
    async def _health_monitor_loop(self):
        """Monitor health of connected devices"""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Check for stale connections
                stale_devices = []
                for device_id, connection in self.connections.items():
                    time_since_ping = current_time - connection.last_ping
                    if time_since_ping.total_seconds() > 60:  # 1 minute timeout
                        stale_devices.append(device_id)
                        connection.is_active = False
                
                # Remove stale connections
                for device_id in stale_devices:
                    if device_id in self.connections:
                        del self.connections[device_id]
                        logger.info(f"Removed stale device: {device_id}")
                
                self.metrics["devices_connected"] = len(self.connections)
                
                await asyncio.sleep(30)  # Health check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "device_id": self.device_id,
            "running": self.running,
            "local_capabilities": self.local_capabilities.__dict__,
            "connected_devices": len(self.connections),
            "active_tasks": len(self.active_tasks),
            "pending_tasks": self.pending_tasks.qsize(),
            "completed_tasks": len(self.completed_tasks),
            "metrics": self.metrics,
            "connected_device_info": [
                {
                    "device_id": conn.device_id,
                    "device_type": conn.device_info.device_type.value,
                    "current_load": conn.current_load,
                    "trust_score": conn.trust_score,
                    "is_active": conn.is_active
                }
                for conn in self.connections.values()
            ]
        }

# Global instance
compute_bridge = ComputeBridge()