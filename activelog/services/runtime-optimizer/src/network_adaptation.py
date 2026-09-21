"""
Network Adaptation System

Intelligent network management with bandwidth detection, adaptive streaming,
offline mode, connection fallback, and data usage optimization.
"""

import asyncio
import aiohttp
import time
import logging
import json
import socket
import subprocess
import platform
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import gzip
import zlib

from config.settings import config, NetworkTier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionType(Enum):
    """Types of network connections"""
    WIFI = "wifi"
    ETHERNET = "ethernet"
    CELLULAR_5G = "cellular_5g"
    CELLULAR_4G = "cellular_4g"
    CELLULAR_3G = "cellular_3g"
    SATELLITE = "satellite"
    OFFLINE = "offline"

class DataType(Enum):
    """Types of data for compression/optimization"""
    TEXT = "text"
    JSON = "json"
    IMAGE = "image"
    VIDEO = "video"
    BINARY = "binary"
    STREAMING = "streaming"

class SyncMode(Enum):
    """Synchronization modes"""
    REAL_TIME = "real_time"
    NEAR_REAL_TIME = "near_real_time"
    PERIODIC = "periodic"
    MANUAL = "manual"
    OFFLINE = "offline"

@dataclass
class NetworkMetrics:
    """Network performance metrics"""
    timestamp: datetime
    connection_type: ConnectionType
    bandwidth_mbps: float
    latency_ms: float
    packet_loss_percent: float
    jitter_ms: float
    signal_strength: Optional[int]  # 0-100 for wireless
    data_usage_mb: float
    connection_stable: bool
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['connection_type'] = self.connection_type.value
        return data

@dataclass
class DataTransfer:
    """Data transfer record"""
    transfer_id: str
    timestamp: datetime
    data_type: DataType
    size_bytes: int
    compressed_size_bytes: int
    compression_ratio: float
    transfer_time_ms: float
    bandwidth_used_mbps: float
    success: bool
    error_message: Optional[str] = None
    retries: int = 0
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['data_type'] = self.data_type.value
        return data

@dataclass
class OfflineQueueItem:
    """Item in offline queue"""
    item_id: str
    timestamp: datetime
    operation_type: str  # 'upload', 'download', 'sync'
    data: Any
    priority: int  # 0-10, higher is more important
    retry_count: int = 0
    max_retries: int = 3
    size_bytes: int = 0
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        # Don't serialize actual data, just metadata
        data['data'] = f"<{type(self.data).__name__}>" if self.data else None
        return data

class BandwidthTester:
    """Network bandwidth testing utility"""
    
    def __init__(self):
        self.test_servers = [
            'http://speedtest.ftp.otenet.gr/files/test1Mb.db',
            'http://speedtest.ftp.otenet.gr/files/test10Mb.db',
            'http://proof.ovh.net/files/1Mb.dat',
            'http://proof.ovh.net/files/10Mb.dat'
        ]
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_download_speed(self, test_duration: float = 5.0) -> float:
        """Test download speed in Mbps"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
            
            # Use 1MB file for quick test
            test_url = self.test_servers[0]
            
            start_time = time.time()
            total_bytes = 0
            
            async with self.session.get(test_url) as response:
                if response.status == 200:
                    async for chunk in response.content.iter_chunked(8192):
                        total_bytes += len(chunk)
                        elapsed = time.time() - start_time
                        if elapsed >= test_duration:
                            break
            
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                # Convert to Mbps
                mbps = (total_bytes * 8) / (elapsed_time * 1024 * 1024)
                return max(0.1, mbps)  # Minimum 0.1 Mbps
            
        except Exception as e:
            logger.warning(f"Download speed test failed: {e}")
        
        return 0.0
    
    async def test_upload_speed(self, test_duration: float = 3.0) -> float:
        """Test upload speed in Mbps (simplified)"""
        try:
            # Simulate upload test by measuring local processing speed
            # In real implementation, would upload to test server
            test_data = b"x" * (1024 * 1024)  # 1MB of data
            start_time = time.time()
            
            # Compress data to simulate upload processing
            compressed = gzip.compress(test_data)
            
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                # Estimate upload speed (typically 1/10th of download)
                download_speed = await self.test_download_speed(test_duration)
                return max(0.05, download_speed * 0.1)  # Estimate upload as 10% of download
            
        except Exception as e:
            logger.warning(f"Upload speed test failed: {e}")
        
        return 0.0
    
    async def test_latency(self) -> float:
        """Test network latency in milliseconds"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))
            
            # Test latency to multiple servers and take average
            latencies = []
            test_urls = [
                'http://www.google.com',
                'http://www.cloudflare.com',
                'http://1.1.1.1'
            ]
            
            for url in test_urls[:2]:  # Test 2 servers max
                try:
                    start_time = time.time()
                    async with self.session.head(url) as response:
                        latency_ms = (time.time() - start_time) * 1000
                        if latency_ms < 5000:  # Ignore > 5 second responses
                            latencies.append(latency_ms)
                except:
                    continue
            
            if latencies:
                return np.median(latencies)
            
        except Exception as e:
            logger.warning(f"Latency test failed: {e}")
        
        return 1000.0  # Default high latency

class DataCompressor:
    """Data compression utilities"""
    
    @staticmethod
    def compress_text(data: str, level: int = 6) -> bytes:
        """Compress text data"""
        return gzip.compress(data.encode('utf-8'), compresslevel=level)
    
    @staticmethod
    def decompress_text(data: bytes) -> str:
        """Decompress text data"""
        return gzip.decompress(data).decode('utf-8')
    
    @staticmethod
    def compress_json(data: Dict[str, Any], level: int = 6) -> bytes:
        """Compress JSON data"""
        json_str = json.dumps(data, separators=(',', ':'))  # Minimal JSON
        return gzip.compress(json_str.encode('utf-8'), compresslevel=level)
    
    @staticmethod
    def decompress_json(data: bytes) -> Dict[str, Any]:
        """Decompress JSON data"""
        json_str = gzip.decompress(data).decode('utf-8')
        return json.loads(json_str)
    
    @staticmethod
    def compress_binary(data: bytes, level: int = 6) -> bytes:
        """Compress binary data"""
        return zlib.compress(data, level)
    
    @staticmethod
    def decompress_binary(data: bytes) -> bytes:
        """Decompress binary data"""
        return zlib.decompress(data)
    
    @staticmethod
    def get_compression_ratio(original_size: int, compressed_size: int) -> float:
        """Calculate compression ratio"""
        if original_size == 0:
            return 1.0
        return compressed_size / original_size
    
    @staticmethod
    def estimate_compression_ratio(data_type: DataType) -> float:
        """Estimate compression ratio for different data types"""
        ratios = {
            DataType.TEXT: 0.3,      # Text compresses well
            DataType.JSON: 0.4,      # JSON compresses well
            DataType.IMAGE: 0.9,     # Images already compressed
            DataType.VIDEO: 0.95,    # Video already compressed
            DataType.BINARY: 0.7,    # Variable compression
            DataType.STREAMING: 1.0  # Real-time, no compression
        }
        return ratios.get(data_type, 0.7)

class ConnectionManager:
    """Network connection management"""
    
    def __init__(self):
        self.current_connection_type = ConnectionType.ETHERNET
        self.connection_history = deque(maxlen=100)
        self.fallback_enabled = True
        self.preferred_connections = [
            ConnectionType.ETHERNET,
            ConnectionType.WIFI,
            ConnectionType.CELLULAR_5G,
            ConnectionType.CELLULAR_4G,
            ConnectionType.CELLULAR_3G,
            ConnectionType.SATELLITE
        ]
    
    async def detect_connection_type(self) -> ConnectionType:
        """Detect current connection type"""
        try:
            # Check for ethernet connection
            if await self._is_ethernet_connected():
                return ConnectionType.ETHERNET
            
            # Check for WiFi
            if await self._is_wifi_connected():
                return ConnectionType.WIFI
            
            # Check for cellular
            cellular_type = await self._detect_cellular_type()
            if cellular_type:
                return cellular_type
            
            # Check for satellite
            if await self._is_satellite_connected():
                return ConnectionType.SATELLITE
            
            return ConnectionType.OFFLINE
            
        except Exception as e:
            logger.error(f"Connection detection failed: {e}")
            return ConnectionType.OFFLINE
    
    async def _is_ethernet_connected(self) -> bool:
        """Check if ethernet is connected"""
        try:
            # Check network interfaces
            if platform.system() == "Linux":
                result = subprocess.run(['ip', 'addr', 'show'], 
                                      capture_output=True, text=True, timeout=5)
                return 'state UP' in result.stdout and ('eth' in result.stdout or 'enp' in result.stdout)
            elif platform.system() == "Windows":
                result = subprocess.run(['ipconfig'], 
                                      capture_output=True, text=True, timeout=5)
                return 'Ethernet adapter' in result.stdout
            else:
                # macOS or other
                result = subprocess.run(['ifconfig'], 
                                      capture_output=True, text=True, timeout=5)
                return 'en0:' in result.stdout or 'en1:' in result.stdout
        except:
            pass
        return False
    
    async def _is_wifi_connected(self) -> bool:
        """Check if WiFi is connected"""
        try:
            if platform.system() == "Linux":
                result = subprocess.run(['iwgetid'], 
                                      capture_output=True, text=True, timeout=5)
                return bool(result.stdout.strip())
            elif platform.system() == "Windows":
                result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], 
                                      capture_output=True, text=True, timeout=5)
                return 'Profile' in result.stdout
            else:
                # macOS
                result = subprocess.run(['networksetup', '-getairportnetwork', 'en0'], 
                                      capture_output=True, text=True, timeout=5)
                return 'not associated' not in result.stdout
        except:
            pass
        return False
    
    async def _detect_cellular_type(self) -> Optional[ConnectionType]:
        """Detect cellular connection type"""
        try:
            # This would integrate with system APIs or check network interface names
            # For demo, we'll simulate based on connection speed
            if hasattr(self, '_simulated_cellular'):
                return self._simulated_cellular
        except:
            pass
        return None
    
    async def _is_satellite_connected(self) -> bool:
        """Check if satellite connection is active"""
        # Would integrate with satellite modem APIs
        return False
    
    async def test_connection_fallback(self) -> List[ConnectionType]:
        """Test available connection fallbacks"""
        available_connections = []
        
        for conn_type in self.preferred_connections:
            try:
                if conn_type == ConnectionType.ETHERNET:
                    if await self._is_ethernet_connected():
                        available_connections.append(conn_type)
                elif conn_type == ConnectionType.WIFI:
                    if await self._is_wifi_connected():
                        available_connections.append(conn_type)
                elif conn_type in [ConnectionType.CELLULAR_5G, ConnectionType.CELLULAR_4G, ConnectionType.CELLULAR_3G]:
                    cellular = await self._detect_cellular_type()
                    if cellular == conn_type:
                        available_connections.append(conn_type)
                elif conn_type == ConnectionType.SATELLITE:
                    if await self._is_satellite_connected():
                        available_connections.append(conn_type)
            except Exception as e:
                logger.warning(f"Connection test failed for {conn_type}: {e}")
        
        return available_connections
    
    async def switch_connection(self, target_type: ConnectionType) -> bool:
        """Switch to target connection type"""
        try:
            logger.info(f"Attempting to switch to {target_type.value}")
            
            # In a real implementation, this would:
            # 1. Disable current connection
            # 2. Enable target connection
            # 3. Wait for connection establishment
            # 4. Verify connectivity
            
            # For demo, just simulate the switch
            await asyncio.sleep(1)  # Simulate connection time
            self.current_connection_type = target_type
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch to {target_type.value}: {e}")
            return False

class NetworkAdaptationSystem:
    """Main network adaptation system"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1000)
        self.transfer_history = deque(maxlen=5000)
        self.offline_queue = deque(maxlen=1000)
        self.connection_manager = ConnectionManager()
        self.compressor = DataCompressor()
        
        self.current_tier = NetworkTier.MODERATE
        self.current_sync_mode = SyncMode.PERIODIC
        self.adaptation_callbacks = []
        
        # Configuration
        self.bandwidth_test_interval = config.optimization.bandwidth_test_interval
        self.auto_adaptation_enabled = True
        self.compression_enabled = True
        self.offline_mode_enabled = True
        
        # CDN and server selection
        self.cdn_servers = [
            {'region': 'us-east', 'url': 'https://cdn-east.example.com', 'latency': 0},
            {'region': 'us-west', 'url': 'https://cdn-west.example.com', 'latency': 0},
            {'region': 'eu', 'url': 'https://cdn-eu.example.com', 'latency': 0},
            {'region': 'asia', 'url': 'https://cdn-asia.example.com', 'latency': 0}
        ]
        self.selected_cdn = self.cdn_servers[0]
        
        # Data usage tracking
        self.daily_data_usage = 0.0  # MB
        self.monthly_data_usage = 0.0  # MB
        self.data_usage_limit_daily = 500.0  # MB
        self.data_usage_limit_monthly = 10000.0  # MB
        
        # Background monitoring
        self.monitoring_active = False
        self._monitor_task = None
        
    async def start_monitoring(self):
        """Start network monitoring"""
        self.monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Network adaptation monitoring started")
    
    async def stop_monitoring(self):
        """Stop network monitoring"""
        self.monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Network adaptation monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        last_bandwidth_test = 0
        
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # Test bandwidth periodically
                if current_time - last_bandwidth_test >= self.bandwidth_test_interval:
                    await self._test_and_update_metrics()
                    last_bandwidth_test = current_time
                
                # Process offline queue if online
                if self.current_tier != NetworkTier.OFFLINE:
                    await self._process_offline_queue()
                
                # Update CDN selection
                await self._update_cdn_selection()
                
                # Check data usage limits
                await self._check_data_usage_limits()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in network monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _test_and_update_metrics(self):
        """Test network and update metrics"""
        try:
            async with BandwidthTester() as tester:
                # Test connection
                bandwidth = await tester.test_download_speed(test_duration=3.0)
                latency = await tester.test_latency()
                
                # Detect connection type
                connection_type = await self.connection_manager.detect_connection_type()
                
                # Create metrics
                metrics = NetworkMetrics(
                    timestamp=datetime.now(),
                    connection_type=connection_type,
                    bandwidth_mbps=bandwidth,
                    latency_ms=latency,
                    packet_loss_percent=0.0,  # Would measure in real implementation
                    jitter_ms=latency * 0.1,  # Estimate
                    signal_strength=None,
                    data_usage_mb=self.daily_data_usage,
                    connection_stable=bandwidth > 0.5 and latency < 1000
                )
                
                self.metrics_history.append(metrics)
                
                # Update network tier
                new_tier = config.get_network_tier(bandwidth, latency)
                if new_tier != self.current_tier:
                    await self._update_network_tier(new_tier)
                
                logger.debug(f"Network metrics: {bandwidth:.1f} Mbps, {latency:.1f} ms, {connection_type.value}")
                
        except Exception as e:
            logger.error(f"Network testing failed: {e}")
            # Assume offline if testing fails repeatedly
            if self.current_tier != NetworkTier.OFFLINE:
                await self._update_network_tier(NetworkTier.OFFLINE)
    
    async def _update_network_tier(self, new_tier: NetworkTier):
        """Update network tier and adapt settings"""
        old_tier = self.current_tier
        self.current_tier = new_tier
        
        logger.info(f"Network tier changed: {old_tier.value} -> {new_tier.value}")
        
        # Update sync mode based on tier
        if new_tier == NetworkTier.OFFLINE:
            self.current_sync_mode = SyncMode.OFFLINE
        elif new_tier in [NetworkTier.POOR, NetworkTier.SLOW]:
            self.current_sync_mode = SyncMode.MANUAL
        elif new_tier == NetworkTier.MODERATE:
            self.current_sync_mode = SyncMode.PERIODIC
        else:  # FAST or EXCELLENT
            self.current_sync_mode = SyncMode.NEAR_REAL_TIME
        
        # Notify callbacks
        await self._notify_adaptation_callbacks('tier_change', old_tier, new_tier)
    
    async def _process_offline_queue(self):
        """Process items from offline queue"""
        if not self.offline_queue:
            return
        
        # Sort queue by priority (highest first)
        sorted_queue = sorted(self.offline_queue, key=lambda x: x.priority, reverse=True)
        processed_count = 0
        max_process = min(5, len(sorted_queue))  # Process max 5 items per cycle
        
        for item in sorted_queue[:max_process]:
            try:
                success = await self._process_queue_item(item)
                if success:
                    self.offline_queue.remove(item)
                    processed_count += 1
                else:
                    item.retry_count += 1
                    if item.retry_count >= item.max_retries:
                        self.offline_queue.remove(item)
                        logger.warning(f"Queue item {item.item_id} failed after {item.retry_count} retries")
                
            except Exception as e:
                logger.error(f"Error processing queue item {item.item_id}: {e}")
                item.retry_count += 1
        
        if processed_count > 0:
            logger.info(f"Processed {processed_count} items from offline queue")
    
    async def _process_queue_item(self, item: OfflineQueueItem) -> bool:
        """Process a single queue item"""
        try:
            # Simulate processing different operation types
            if item.operation_type == 'upload':
                # Simulate file upload
                await asyncio.sleep(0.1)
                logger.debug(f"Uploaded {item.item_id}")
                
            elif item.operation_type == 'download':
                # Simulate file download
                await asyncio.sleep(0.05)
                logger.debug(f"Downloaded {item.item_id}")
                
            elif item.operation_type == 'sync':
                # Simulate data sync
                await asyncio.sleep(0.02)
                logger.debug(f"Synced {item.item_id}")
            
            # Update data usage
            self.daily_data_usage += item.size_bytes / (1024 * 1024)  # Convert to MB
            self.monthly_data_usage += item.size_bytes / (1024 * 1024)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process queue item {item.item_id}: {e}")
            return False
    
    async def _update_cdn_selection(self):
        """Update CDN server selection based on latency"""
        if self.current_tier == NetworkTier.OFFLINE:
            return
        
        # Test latency to each CDN server (simplified)
        best_cdn = self.selected_cdn
        best_latency = float('inf')
        
        for cdn in self.cdn_servers[:2]:  # Test first 2 CDNs
            try:
                start_time = time.time()
                # Simulate latency test
                await asyncio.sleep(0.01)  # Simulate network request
                latency = (time.time() - start_time) * 1000 + np.random.uniform(10, 100)
                
                cdn['latency'] = latency
                if latency < best_latency:
                    best_latency = latency
                    best_cdn = cdn
                    
            except Exception as e:
                logger.warning(f"CDN latency test failed for {cdn['region']}: {e}")
                cdn['latency'] = 1000  # High latency for failed servers
        
        if best_cdn != self.selected_cdn:
            old_cdn = self.selected_cdn['region']
            self.selected_cdn = best_cdn
            logger.info(f"Switched CDN: {old_cdn} -> {best_cdn['region']} (latency: {best_latency:.1f}ms)")
    
    async def _check_data_usage_limits(self):
        """Check data usage limits and warn if necessary"""
        daily_percent = (self.daily_data_usage / self.data_usage_limit_daily) * 100
        monthly_percent = (self.monthly_data_usage / self.data_usage_limit_monthly) * 100
        
        if daily_percent >= 90:
            await self._notify_adaptation_callbacks('data_limit_warning', 'daily', daily_percent)
        
        if monthly_percent >= 90:
            await self._notify_adaptation_callbacks('data_limit_warning', 'monthly', monthly_percent)
    
    async def _notify_adaptation_callbacks(self, event_type: str, *args):
        """Notify adaptation callbacks"""
        for callback in self.adaptation_callbacks:
            try:
                await callback(event_type, *args)
            except Exception as e:
                logger.error(f"Adaptation callback error: {e}")
    
    def add_adaptation_callback(self, callback):
        """Add adaptation callback"""
        self.adaptation_callbacks.append(callback)
    
    async def transfer_data(self, data: Any, data_type: DataType, 
                          destination: str = None, compress: bool = None) -> DataTransfer:
        """Transfer data with automatic optimization"""
        transfer_id = f"transfer_{int(time.time() * 1000)}"
        start_time = time.time()
        
        # Determine if compression should be used
        should_compress = compress if compress is not None else self.compression_enabled
        should_compress = should_compress and self.current_tier in [NetworkTier.POOR, NetworkTier.SLOW, NetworkTier.MODERATE]
        
        try:
            # Convert data to bytes
            if isinstance(data, str):
                original_bytes = data.encode('utf-8')
            elif isinstance(data, dict):
                original_bytes = json.dumps(data).encode('utf-8')
            elif isinstance(data, bytes):
                original_bytes = data
            else:
                original_bytes = str(data).encode('utf-8')
            
            original_size = len(original_bytes)
            compressed_size = original_size
            
            # Apply compression if needed
            if should_compress:
                if data_type == DataType.TEXT:
                    if isinstance(data, str):
                        compressed_bytes = self.compressor.compress_text(data)
                    else:
                        compressed_bytes = self.compressor.compress_binary(original_bytes)
                elif data_type == DataType.JSON:
                    if isinstance(data, dict):
                        compressed_bytes = self.compressor.compress_json(data)
                    else:
                        compressed_bytes = self.compressor.compress_binary(original_bytes)
                else:
                    compressed_bytes = self.compressor.compress_binary(original_bytes)
                
                compressed_size = len(compressed_bytes)
            else:
                compressed_bytes = original_bytes
            
            # Simulate network transfer
            transfer_time = self._simulate_transfer_time(compressed_size)
            await asyncio.sleep(transfer_time / 1000.0)  # Convert ms to seconds
            
            # Update data usage
            self.daily_data_usage += compressed_size / (1024 * 1024)
            self.monthly_data_usage += compressed_size / (1024 * 1024)
            
            # Calculate transfer metrics
            compression_ratio = self.compressor.get_compression_ratio(original_size, compressed_size)
            bandwidth_used = (compressed_size * 8) / (transfer_time / 1000) / (1024 * 1024)  # Mbps
            
            transfer = DataTransfer(
                transfer_id=transfer_id,
                timestamp=datetime.now(),
                data_type=data_type,
                size_bytes=original_size,
                compressed_size_bytes=compressed_size,
                compression_ratio=compression_ratio,
                transfer_time_ms=transfer_time,
                bandwidth_used_mbps=bandwidth_used,
                success=True
            )
            
            self.transfer_history.append(transfer)
            logger.debug(f"Data transfer completed: {transfer_id} ({original_size} -> {compressed_size} bytes)")
            
            return transfer
            
        except Exception as e:
            transfer = DataTransfer(
                transfer_id=transfer_id,
                timestamp=datetime.now(),
                data_type=data_type,
                size_bytes=len(original_bytes) if 'original_bytes' in locals() else 0,
                compressed_size_bytes=0,
                compression_ratio=1.0,
                transfer_time_ms=time.time() - start_time,
                bandwidth_used_mbps=0.0,
                success=False,
                error_message=str(e)
            )
            
            self.transfer_history.append(transfer)
            logger.error(f"Data transfer failed: {transfer_id}: {e}")
            
            # Add to offline queue if connection is poor
            if self.current_tier in [NetworkTier.OFFLINE, NetworkTier.POOR]:
                await self.add_to_offline_queue('upload', data, priority=5, size_bytes=transfer.size_bytes)
            
            return transfer
    
    def _simulate_transfer_time(self, size_bytes: int) -> float:
        """Simulate network transfer time based on current conditions"""
        if self.current_tier == NetworkTier.OFFLINE:
            return float('inf')
        
        # Get recent metrics
        recent_metrics = [m for m in self.metrics_history if (datetime.now() - m.timestamp).seconds < 30]
        if recent_metrics:
            avg_bandwidth_mbps = np.mean([m.bandwidth_mbps for m in recent_metrics])
            avg_latency_ms = np.mean([m.latency_ms for m in recent_metrics])
        else:
            # Default values based on tier
            tier_bandwidth = {
                NetworkTier.POOR: 0.5,
                NetworkTier.SLOW: 2.0,
                NetworkTier.MODERATE: 10.0,
                NetworkTier.FAST: 50.0,
                NetworkTier.EXCELLENT: 100.0
            }
            avg_bandwidth_mbps = tier_bandwidth.get(self.current_tier, 10.0)
            avg_latency_ms = 100.0
        
        # Calculate transfer time: latency + (size / bandwidth)
        if avg_bandwidth_mbps > 0:
            bandwidth_bps = avg_bandwidth_mbps * 1024 * 1024 / 8  # Convert to bytes per second
            transfer_time_ms = avg_latency_ms + (size_bytes / bandwidth_bps) * 1000
        else:
            transfer_time_ms = 10000  # 10 seconds for very poor connection
        
        # Add some randomness
        transfer_time_ms *= np.random.uniform(0.8, 1.2)
        
        return transfer_time_ms
    
    async def add_to_offline_queue(self, operation_type: str, data: Any, 
                                 priority: int = 5, size_bytes: int = None) -> str:
        """Add item to offline queue"""
        item_id = f"queue_{int(time.time() * 1000)}"
        
        if size_bytes is None:
            if isinstance(data, str):
                size_bytes = len(data.encode('utf-8'))
            elif isinstance(data, bytes):
                size_bytes = len(data)
            elif isinstance(data, dict):
                size_bytes = len(json.dumps(data).encode('utf-8'))
            else:
                size_bytes = len(str(data).encode('utf-8'))
        
        queue_item = OfflineQueueItem(
            item_id=item_id,
            timestamp=datetime.now(),
            operation_type=operation_type,
            data=data,
            priority=priority,
            size_bytes=size_bytes
        )
        
        self.offline_queue.append(queue_item)
        logger.info(f"Added item to offline queue: {item_id} ({operation_type})")
        
        return item_id
    
    async def enable_offline_mode(self):
        """Enable offline mode"""
        self.current_tier = NetworkTier.OFFLINE
        self.current_sync_mode = SyncMode.OFFLINE
        logger.info("Offline mode enabled")
        await self._notify_adaptation_callbacks('offline_mode_enabled')
    
    async def disable_offline_mode(self):
        """Disable offline mode and test connection"""
        await self._test_and_update_metrics()
        logger.info("Offline mode disabled")
        await self._notify_adaptation_callbacks('offline_mode_disabled')
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status"""
        recent_metrics = list(self.metrics_history)[-10:]  # Last 10 measurements
        recent_transfers = list(self.transfer_history)[-100:]  # Last 100 transfers
        
        # Calculate averages
        avg_bandwidth = np.mean([m.bandwidth_mbps for m in recent_metrics]) if recent_metrics else 0.0
        avg_latency = np.mean([m.latency_ms for m in recent_metrics]) if recent_metrics else 0.0
        
        # Transfer statistics
        successful_transfers = sum(1 for t in recent_transfers if t.success)
        total_transfers = len(recent_transfers)
        success_rate = (successful_transfers / total_transfers * 100) if total_transfers > 0 else 0.0
        
        avg_compression_ratio = np.mean([t.compression_ratio for t in recent_transfers]) if recent_transfers else 1.0
        
        return {
            'current_tier': self.current_tier.value,
            'sync_mode': self.current_sync_mode.value,
            'connection_type': self.connection_manager.current_connection_type.value,
            'current_metrics': {
                'bandwidth_mbps': avg_bandwidth,
                'latency_ms': avg_latency,
                'stable': avg_bandwidth > 1.0 and avg_latency < 500
            },
            'data_usage': {
                'daily_mb': self.daily_data_usage,
                'monthly_mb': self.monthly_data_usage,
                'daily_limit_percent': (self.daily_data_usage / self.data_usage_limit_daily) * 100,
                'monthly_limit_percent': (self.monthly_data_usage / self.data_usage_limit_monthly) * 100
            },
            'transfer_statistics': {
                'total_transfers': total_transfers,
                'success_rate_percent': success_rate,
                'average_compression_ratio': avg_compression_ratio
            },
            'offline_queue': {
                'items_queued': len(self.offline_queue),
                'queue_size_mb': sum(item.size_bytes for item in self.offline_queue) / (1024 * 1024)
            },
            'cdn_info': {
                'selected_region': self.selected_cdn['region'],
                'latency_ms': self.selected_cdn.get('latency', 0)
            },
            'settings': {
                'auto_adaptation_enabled': self.auto_adaptation_enabled,
                'compression_enabled': self.compression_enabled,
                'offline_mode_enabled': self.offline_mode_enabled
            }
        }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get network optimization recommendations"""
        recommendations = []
        
        # Analyze recent performance
        recent_metrics = list(self.metrics_history)[-50:]
        if not recent_metrics:
            return recommendations
        
        avg_bandwidth = np.mean([m.bandwidth_mbps for m in recent_metrics])
        avg_latency = np.mean([m.latency_ms for m in recent_metrics])
        
        # Bandwidth recommendations
        if avg_bandwidth < 1.0:
            recommendations.append({
                'type': 'low_bandwidth',
                'priority': 'high',
                'description': f'Very low bandwidth detected ({avg_bandwidth:.1f} Mbps)',
                'recommendation': 'Enable aggressive compression and switch to offline mode for non-critical operations',
                'actions': ['enable_compression', 'reduce_quality', 'batch_operations']
            })
        elif avg_bandwidth < 5.0:
            recommendations.append({
                'type': 'moderate_bandwidth',
                'priority': 'medium',
                'description': f'Limited bandwidth ({avg_bandwidth:.1f} Mbps)',
                'recommendation': 'Enable compression and reduce background sync frequency',
                'actions': ['enable_compression', 'reduce_sync_frequency']
            })
        
        # Latency recommendations
        if avg_latency > 500:
            recommendations.append({
                'type': 'high_latency',
                'priority': 'high',
                'description': f'High latency detected ({avg_latency:.0f} ms)',
                'recommendation': 'Batch operations and use predictive prefetching',
                'actions': ['batch_operations', 'enable_prefetch', 'reduce_real_time_features']
            })
        
        # Data usage recommendations
        daily_percent = (self.daily_data_usage / self.data_usage_limit_daily) * 100
        if daily_percent > 80:
            recommendations.append({
                'type': 'data_usage_warning',
                'priority': 'high',
                'description': f'High data usage ({daily_percent:.0f}% of daily limit)',
                'recommendation': 'Enable data saver mode and defer non-critical uploads',
                'actions': ['enable_data_saver', 'defer_uploads', 'increase_compression']
            })
        
        # Connection stability
        connection_changes = len(set(m.connection_type for m in recent_metrics[-10:]))
        if connection_changes > 2:
            recommendations.append({
                'type': 'unstable_connection',
                'priority': 'medium',
                'description': 'Frequent connection changes detected',
                'recommendation': 'Enable connection fallback and increase retry logic',
                'actions': ['enable_fallback', 'increase_retries', 'cache_aggressively']
            })
        
        return recommendations

# Global network adaptation system
network_adapter = NetworkAdaptationSystem()

if __name__ == "__main__":
    # Demo usage
    async def adaptation_callback(event_type: str, *args):
        print(f"Network adaptation event: {event_type} - {args}")
    
    async def main():
        # Add callback
        network_adapter.add_adaptation_callback(adaptation_callback)
        
        # Start monitoring
        await network_adapter.start_monitoring()
        
        # Simulate some data transfers
        print("Simulating data transfers...")
        
        # Test different data types
        text_data = "This is a sample text that should compress well when using gzip compression."
        json_data = {"users": [{"id": i, "name": f"User {i}"} for i in range(100)]}
        binary_data = bytes(range(256)) * 10  # 2.5KB of binary data
        
        transfers = [
            await network_adapter.transfer_data(text_data, DataType.TEXT),
            await network_adapter.transfer_data(json_data, DataType.JSON),
            await network_adapter.transfer_data(binary_data, DataType.BINARY)
        ]
        
        for transfer in transfers:
            print(f"Transfer {transfer.transfer_id}: "
                  f"{transfer.size_bytes} -> {transfer.compressed_size_bytes} bytes "
                  f"(ratio: {transfer.compression_ratio:.2f}) "
                  f"in {transfer.transfer_time_ms:.1f}ms")
        
        # Add some items to offline queue
        await network_adapter.add_to_offline_queue('upload', 'Offline data 1', priority=8)
        await network_adapter.add_to_offline_queue('sync', {'key': 'value'}, priority=5)
        
        # Wait for some monitoring cycles
        await asyncio.sleep(10)
        
        # Get status
        status = network_adapter.get_network_status()
        print("\nNetwork Status:")
        print(json.dumps(status, indent=2))
        
        # Get recommendations
        recommendations = network_adapter.get_optimization_recommendations()
        print("\nOptimization Recommendations:")
        for rec in recommendations:
            print(f"- {rec['description']}")
            print(f"  Recommendation: {rec['recommendation']}")
        
        # Stop monitoring
        await network_adapter.stop_monitoring()
    
    asyncio.run(main())