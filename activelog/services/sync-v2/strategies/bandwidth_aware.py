#!/usr/bin/env python3
"""
ActiveLog.ai Bandwidth-Aware Sync Strategies

Adaptive sync strategies based on network conditions, data usage, and device constraints.
"""

import asyncio
import json
import logging
import time
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import subprocess
import platform

class NetworkType(Enum):
    UNKNOWN = "unknown"
    ETHERNET = "ethernet"
    WIFI = "wifi"
    CELLULAR = "cellular"
    SATELLITE = "satellite"

class ConnectionQuality(Enum):
    EXCELLENT = "excellent"  # >50 Mbps, <20ms latency
    GOOD = "good"           # >10 Mbps, <50ms latency
    FAIR = "fair"           # >1 Mbps, <100ms latency
    POOR = "poor"           # <1 Mbps or >200ms latency
    UNRELIABLE = "unreliable"  # Frequent disconnections

@dataclass
class NetworkMetrics:
    """Network performance metrics"""
    bandwidth_down: float  # Mbps
    bandwidth_up: float    # Mbps
    latency: float        # milliseconds
    packet_loss: float    # percentage
    jitter: float         # milliseconds
    connection_type: NetworkType
    is_metered: bool = False
    data_limit: Optional[int] = None  # bytes per month
    data_used: Optional[int] = None   # bytes used this month
    cost_per_mb: Optional[float] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class BandwidthProfile:
    """Bandwidth usage profile for different content types"""
    content_type: str
    base_size: int        # Base size in bytes
    compression_ratio: float  # Achievable compression (0.1-1.0)
    priority_multiplier: float  # Priority adjustment
    streaming_capable: bool = False
    chunked_transfer: bool = True
    delta_sync_capable: bool = False

@dataclass
class SyncStrategy:
    """Adaptive sync strategy configuration"""
    strategy_name: str
    network_quality_threshold: ConnectionQuality
    max_concurrent_transfers: int
    chunk_size: int
    compression_enabled: bool
    delta_sync_enabled: bool
    queue_management: str  # "fifo", "priority", "adaptive"
    bandwidth_throttle: Optional[float] = None  # Limit bandwidth usage (Mbps)
    retry_policy: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.retry_policy is None:
            self.retry_policy = {
                "max_retries": 3,
                "backoff_multiplier": 2.0,
                "initial_delay": 1.0
            }

class NetworkMonitor:
    """Monitor network conditions and performance"""
    
    def __init__(self, monitor_interval: int = 30):
        self.monitor_interval = monitor_interval
        self.logger = logging.getLogger(__name__)
        self.metrics_history: List[NetworkMetrics] = []
        self.current_metrics: Optional[NetworkMetrics] = None
        self.monitoring = False
    
    async def start_monitoring(self):
        """Start continuous network monitoring"""
        self.monitoring = True
        while self.monitoring:
            try:
                metrics = await self._measure_network()
                self.current_metrics = metrics
                self.metrics_history.append(metrics)
                
                # Keep only last 100 measurements
                if len(self.metrics_history) > 100:
                    self.metrics_history.pop(0)
                
                self.logger.debug(f"Network metrics: {metrics.bandwidth_down:.1f}Mbps down, "
                                f"{metrics.latency:.1f}ms latency")
                
            except Exception as e:
                self.logger.error(f"Network monitoring error: {e}")
            
            await asyncio.sleep(self.monitor_interval)
    
    def stop_monitoring(self):
        """Stop network monitoring"""
        self.monitoring = False
    
    async def _measure_network(self) -> NetworkMetrics:
        """Measure current network performance"""
        # Detect connection type
        connection_type = await self._detect_connection_type()
        
        # Measure bandwidth
        bandwidth_down, bandwidth_up = await self._measure_bandwidth()
        
        # Measure latency and packet loss
        latency, packet_loss, jitter = await self._measure_latency()
        
        # Check if connection is metered
        is_metered = await self._is_metered_connection()
        
        return NetworkMetrics(
            bandwidth_down=bandwidth_down,
            bandwidth_up=bandwidth_up,
            latency=latency,
            packet_loss=packet_loss,
            jitter=jitter,
            connection_type=connection_type,
            is_metered=is_metered
        )
    
    async def _detect_connection_type(self) -> NetworkType:
        """Detect current connection type"""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Check for wireless interface
                result = await asyncio.create_subprocess_exec(
                    "cat", "/proc/net/wireless",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if stdout and len(stdout.decode().strip().split('\n')) > 2:
                    return NetworkType.WIFI
                
                # Check for ethernet
                result = await asyncio.create_subprocess_exec(
                    "ip", "route", "show", "default",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if "eth" in stdout.decode() or "enp" in stdout.decode():
                    return NetworkType.ETHERNET
            
            elif system == "Darwin":  # macOS
                result = await asyncio.create_subprocess_exec(
                    "route", "get", "default",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if "en0" in stdout.decode():  # Typical WiFi interface
                    return NetworkType.WIFI
                elif "en1" in stdout.decode():  # Typical Ethernet interface
                    return NetworkType.ETHERNET
            
            elif system == "Windows":
                # Windows network detection would go here
                pass
            
        except Exception as e:
            self.logger.error(f"Connection type detection failed: {e}")
        
        return NetworkType.UNKNOWN
    
    async def _measure_bandwidth(self) -> Tuple[float, float]:
        """Measure download and upload bandwidth"""
        # Simplified bandwidth measurement
        # In production, this would use proper speed test servers
        
        try:
            # Measure download speed with a small test file
            start_time = time.time()
            
            # Use ping to estimate rough bandwidth
            result = await asyncio.create_subprocess_exec(
                "ping", "-c", "3", "8.8.8.8",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            elapsed_time = time.time() - start_time
            
            # Very rough estimation - replace with proper bandwidth test
            if elapsed_time < 0.1:
                estimated_bandwidth = 100.0  # Fast connection
            elif elapsed_time < 0.5:
                estimated_bandwidth = 50.0   # Good connection
            elif elapsed_time < 1.0:
                estimated_bandwidth = 10.0   # Fair connection
            else:
                estimated_bandwidth = 1.0    # Slow connection
            
            # Assume symmetric for simplicity
            return estimated_bandwidth, estimated_bandwidth * 0.8
            
        except Exception as e:
            self.logger.error(f"Bandwidth measurement failed: {e}")
            return 10.0, 5.0  # Default values
    
    async def _measure_latency(self) -> Tuple[float, float, float]:
        """Measure latency, packet loss, and jitter"""
        try:
            result = await asyncio.create_subprocess_exec(
                "ping", "-c", "10", "8.8.8.8",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return 100.0, 0.0, 10.0  # Default values
            
            output = stdout.decode()
            
            # Parse ping output
            latencies = []
            packet_loss = 0.0
            
            for line in output.split('\n'):
                if 'time=' in line:
                    try:
                        time_part = line.split('time=')[1].split()[0]
                        latency = float(time_part)
                        latencies.append(latency)
                    except:
                        pass
                elif 'packet loss' in line:
                    try:
                        loss_part = line.split('packet loss')[0].split()[-1]
                        packet_loss = float(loss_part.replace('%', ''))
                    except:
                        pass
            
            if latencies:
                avg_latency = statistics.mean(latencies)
                jitter = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
            else:
                avg_latency = 100.0
                jitter = 10.0
            
            return avg_latency, packet_loss, jitter
            
        except Exception as e:
            self.logger.error(f"Latency measurement failed: {e}")
            return 100.0, 0.0, 10.0
    
    async def _is_metered_connection(self) -> bool:
        """Check if connection is metered (mobile data, etc.)"""
        # This would need platform-specific implementation
        # For now, assume cellular connections are metered
        return self.current_metrics.connection_type == NetworkType.CELLULAR if self.current_metrics else False
    
    def get_connection_quality(self) -> ConnectionQuality:
        """Assess current connection quality"""
        if not self.current_metrics:
            return ConnectionQuality.UNKNOWN
        
        metrics = self.current_metrics
        
        # Excellent: >50 Mbps, <20ms latency, <1% loss
        if (metrics.bandwidth_down > 50 and 
            metrics.latency < 20 and 
            metrics.packet_loss < 1):
            return ConnectionQuality.EXCELLENT
        
        # Good: >10 Mbps, <50ms latency, <2% loss
        elif (metrics.bandwidth_down > 10 and 
              metrics.latency < 50 and 
              metrics.packet_loss < 2):
            return ConnectionQuality.GOOD
        
        # Fair: >1 Mbps, <100ms latency, <5% loss
        elif (metrics.bandwidth_down > 1 and 
              metrics.latency < 100 and 
              metrics.packet_loss < 5):
            return ConnectionQuality.FAIR
        
        # Poor: <1 Mbps or >200ms latency or >10% loss
        elif (metrics.bandwidth_down < 1 or 
              metrics.latency > 200 or 
              metrics.packet_loss > 10):
            return ConnectionQuality.POOR
        
        else:
            return ConnectionQuality.UNRELIABLE
    
    def get_bandwidth_recommendation(self) -> Dict[str, Any]:
        """Get bandwidth usage recommendations"""
        quality = self.get_connection_quality()
        metrics = self.current_metrics
        
        if not metrics:
            return {"recommended_max_usage": 1.0, "strategy": "conservative"}
        
        recommendations = {
            ConnectionQuality.EXCELLENT: {
                "recommended_max_usage": metrics.bandwidth_down * 0.8,  # 80% of available
                "strategy": "aggressive",
                "concurrent_transfers": 10,
                "chunk_size": 10 * 1024 * 1024  # 10MB
            },
            ConnectionQuality.GOOD: {
                "recommended_max_usage": metrics.bandwidth_down * 0.6,  # 60% of available
                "strategy": "balanced",
                "concurrent_transfers": 5,
                "chunk_size": 5 * 1024 * 1024   # 5MB
            },
            ConnectionQuality.FAIR: {
                "recommended_max_usage": metrics.bandwidth_down * 0.4,  # 40% of available
                "strategy": "conservative",
                "concurrent_transfers": 2,
                "chunk_size": 1024 * 1024       # 1MB
            },
            ConnectionQuality.POOR: {
                "recommended_max_usage": metrics.bandwidth_down * 0.2,  # 20% of available
                "strategy": "minimal",
                "concurrent_transfers": 1,
                "chunk_size": 256 * 1024        # 256KB
            },
            ConnectionQuality.UNRELIABLE: {
                "recommended_max_usage": 0.1,   # Minimal usage
                "strategy": "emergency_only",
                "concurrent_transfers": 1,
                "chunk_size": 64 * 1024         # 64KB
            }
        }
        
        return recommendations.get(quality, recommendations[ConnectionQuality.POOR])

class AdaptiveSyncScheduler:
    """Schedule sync operations based on network conditions and priorities"""
    
    def __init__(self, network_monitor: NetworkMonitor):
        self.network_monitor = network_monitor
        self.logger = logging.getLogger(__name__)
        
        # Content type profiles
        self.content_profiles = {
            "text": BandwidthProfile("text", 1024, 0.7, 1.0, False, True, True),
            "image": BandwidthProfile("image", 500000, 0.8, 0.8, False, True, False),
            "video": BandwidthProfile("video", 50000000, 0.9, 0.6, True, True, False),
            "audio": BandwidthProfile("audio", 5000000, 0.9, 0.7, True, True, False),
            "document": BandwidthProfile("document", 100000, 0.6, 0.9, False, True, True)
        }
        
        # Strategy configurations
        self.strategies = {
            "aggressive": SyncStrategy(
                "aggressive", ConnectionQuality.GOOD, 10, 10*1024*1024, True, True, "priority"
            ),
            "balanced": SyncStrategy(
                "balanced", ConnectionQuality.FAIR, 5, 5*1024*1024, True, True, "adaptive"
            ),
            "conservative": SyncStrategy(
                "conservative", ConnectionQuality.POOR, 2, 1024*1024, True, False, "fifo"
            ),
            "minimal": SyncStrategy(
                "minimal", ConnectionQuality.UNRELIABLE, 1, 256*1024, True, False, "priority"
            )
        }
        
        # Active transfers tracking
        self.active_transfers: Dict[str, Dict[str, Any]] = {}
        self.transfer_queue: List[Dict[str, Any]] = []
        self.bandwidth_usage = 0.0  # Current bandwidth usage in Mbps
    
    def get_optimal_strategy(self) -> SyncStrategy:
        """Get optimal sync strategy for current network conditions"""
        quality = self.network_monitor.get_connection_quality()
        recommendation = self.network_monitor.get_bandwidth_recommendation()
        strategy_name = recommendation["strategy"]
        
        if strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
            
            # Adjust strategy based on current conditions
            if self.network_monitor.current_metrics and self.network_monitor.current_metrics.is_metered:
                # More conservative on metered connections
                strategy.max_concurrent_transfers = min(strategy.max_concurrent_transfers, 2)
                strategy.chunk_size = min(strategy.chunk_size, 1024*1024)
                strategy.bandwidth_throttle = min(
                    recommendation["recommended_max_usage"] * 0.5,  # 50% on metered
                    strategy.bandwidth_throttle or float('inf')
                )
            
            return strategy
        
        return self.strategies["conservative"]
    
    def calculate_transfer_priority(self, item_data: Dict[str, Any]) -> float:
        """Calculate transfer priority based on item characteristics and network conditions"""
        base_priority = item_data.get('priority', 5)
        content_type = item_data.get('content_type', 'text')
        file_size = item_data.get('file_size', 0)
        age_hours = item_data.get('age_hours', 0)
        
        # Get content profile
        profile = self.content_profiles.get(content_type, self.content_profiles['text'])
        
        # Calculate priority score
        priority_score = base_priority * profile.priority_multiplier
        
        # Adjust for file size (smaller files get higher priority on poor connections)
        quality = self.network_monitor.get_connection_quality()
        if quality in [ConnectionQuality.POOR, ConnectionQuality.UNRELIABLE]:
            size_factor = max(0.1, 1.0 - (file_size / (10 * 1024 * 1024)))  # Penalize >10MB
            priority_score *= size_factor
        
        # Boost priority for recent items
        if age_hours < 1:
            priority_score *= 1.5
        elif age_hours < 24:
            priority_score *= 1.2
        elif age_hours > 168:  # >1 week
            priority_score *= 0.8
        
        # Network condition adjustments
        if self.network_monitor.current_metrics:
            metrics = self.network_monitor.current_metrics
            
            # Boost text on poor connections
            if quality == ConnectionQuality.POOR and content_type == 'text':
                priority_score *= 2.0
            
            # Penalize large files on metered connections
            if metrics.is_metered and file_size > 5 * 1024 * 1024:  # >5MB
                priority_score *= 0.5
        
        return priority_score
    
    def should_defer_transfer(self, item_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Decide if transfer should be deferred"""
        content_type = item_data.get('content_type', 'text')
        file_size = item_data.get('file_size', 0)
        priority = item_data.get('priority', 5)
        
        quality = self.network_monitor.get_connection_quality()
        metrics = self.network_monitor.current_metrics
        
        # Never defer critical items
        if priority >= 9:
            return False, "critical_priority"
        
        # Defer large files on poor connections
        if quality == ConnectionQuality.POOR:
            if content_type == 'video' and file_size > 10 * 1024 * 1024:
                return True, "large_video_poor_connection"
            if file_size > 50 * 1024 * 1024:
                return True, "large_file_poor_connection"
        
        # Defer non-essential content on unreliable connections
        if quality == ConnectionQuality.UNRELIABLE:
            if content_type in ['video', 'audio'] and priority < 7:
                return True, "media_unreliable_connection"
        
        # Defer expensive transfers on metered connections
        if metrics and metrics.is_metered:
            if content_type == 'video' and file_size > 25 * 1024 * 1024:
                return True, "large_video_metered"
            if file_size > 100 * 1024 * 1024:
                return True, "large_file_metered"
        
        # Check current bandwidth usage
        recommendation = self.network_monitor.get_bandwidth_recommendation()
        max_usage = recommendation["recommended_max_usage"]
        
        if self.bandwidth_usage >= max_usage * 0.9:  # 90% of recommended max
            if priority < 7:
                return True, "bandwidth_limit_reached"
        
        return False, "no_deferral_needed"
    
    def estimate_transfer_time(self, item_data: Dict[str, Any], strategy: SyncStrategy) -> float:
        """Estimate transfer time for item"""
        file_size = item_data.get('file_size', len(json.dumps(item_data.get('data', {}))))
        content_type = item_data.get('content_type', 'text')
        
        # Get content profile for compression estimation
        profile = self.content_profiles.get(content_type, self.content_profiles['text'])
        
        # Calculate effective size after compression
        if strategy.compression_enabled:
            effective_size = file_size * profile.compression_ratio
        else:
            effective_size = file_size
        
        # Get available bandwidth
        if self.network_monitor.current_metrics:
            available_bandwidth = self.network_monitor.current_metrics.bandwidth_up
            
            # Account for bandwidth throttling
            if strategy.bandwidth_throttle:
                available_bandwidth = min(available_bandwidth, strategy.bandwidth_throttle)
            
            # Account for current usage
            available_bandwidth = max(0.1, available_bandwidth - self.bandwidth_usage)
        else:
            available_bandwidth = 1.0  # Conservative estimate
        
        # Convert Mbps to bytes per second
        bandwidth_bps = available_bandwidth * 1024 * 1024 / 8
        
        # Estimate transfer time with overhead
        base_time = effective_size / bandwidth_bps
        overhead_factor = 1.5  # Protocol overhead, processing time, etc.
        
        return base_time * overhead_factor
    
    def schedule_transfer(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule transfer with optimal timing and parameters"""
        strategy = self.get_optimal_strategy()
        
        # Check if transfer should be deferred
        should_defer, defer_reason = self.should_defer_transfer(item_data)
        
        if should_defer:
            return {
                "action": "defer",
                "reason": defer_reason,
                "retry_after": self._calculate_retry_delay(defer_reason)
            }
        
        # Calculate priority and estimated time
        priority = self.calculate_transfer_priority(item_data)
        estimated_time = self.estimate_transfer_time(item_data, strategy)
        
        # Check if we can start transfer immediately
        can_start_now = len(self.active_transfers) < strategy.max_concurrent_transfers
        
        transfer_plan = {
            "action": "transfer" if can_start_now else "queue",
            "priority": priority,
            "estimated_time": estimated_time,
            "strategy": strategy.strategy_name,
            "chunk_size": strategy.chunk_size,
            "compression_enabled": strategy.compression_enabled,
            "delta_sync_enabled": strategy.delta_sync_enabled,
            "concurrent_allowed": can_start_now
        }
        
        if not can_start_now:
            # Add to queue with priority
            queue_position = self._find_queue_position(priority)
            transfer_plan["queue_position"] = queue_position
            transfer_plan["estimated_wait_time"] = self._estimate_queue_wait_time(queue_position)
        
        return transfer_plan
    
    def _calculate_retry_delay(self, defer_reason: str) -> int:
        """Calculate retry delay in seconds based on defer reason"""
        retry_delays = {
            "large_video_poor_connection": 3600,     # 1 hour
            "large_file_poor_connection": 1800,      # 30 minutes
            "media_unreliable_connection": 600,      # 10 minutes
            "large_video_metered": 7200,             # 2 hours
            "large_file_metered": 3600,              # 1 hour
            "bandwidth_limit_reached": 300           # 5 minutes
        }
        
        return retry_delays.get(defer_reason, 600)
    
    def _find_queue_position(self, priority: float) -> int:
        """Find appropriate position in queue based on priority"""
        for i, queued_item in enumerate(self.transfer_queue):
            if priority > queued_item.get('priority', 0):
                return i
        return len(self.transfer_queue)
    
    def _estimate_queue_wait_time(self, queue_position: int) -> float:
        """Estimate wait time based on queue position"""
        if queue_position == 0:
            return 0
        
        # Estimate based on active transfers and queue
        active_transfer_times = [
            transfer.get('estimated_remaining', 60)
            for transfer in self.active_transfers.values()
        ]
        
        queue_transfer_times = [
            item.get('estimated_time', 60)
            for item in self.transfer_queue[:queue_position]
        ]
        
        return sum(active_transfer_times) + sum(queue_transfer_times)
    
    def update_bandwidth_usage(self, transfer_id: str, bytes_per_second: float):
        """Update current bandwidth usage"""
        if transfer_id in self.active_transfers:
            # Convert bytes/sec to Mbps
            mbps = bytes_per_second * 8 / (1024 * 1024)
            self.active_transfers[transfer_id]['current_bandwidth'] = mbps
        
        # Recalculate total bandwidth usage
        self.bandwidth_usage = sum(
            transfer.get('current_bandwidth', 0)
            for transfer in self.active_transfers.values()
        )

class BandwidthThrottler:
    """Throttle bandwidth usage to prevent network saturation"""
    
    def __init__(self, max_bandwidth_mbps: float):
        self.max_bandwidth_mbps = max_bandwidth_mbps
        self.active_transfers: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Token bucket for rate limiting
        self.bucket_size = max_bandwidth_mbps * 1024 * 1024 / 8  # bytes
        self.current_tokens = self.bucket_size
        self.last_refill = time.time()
        self.refill_rate = self.bucket_size  # tokens per second
    
    async def acquire_bandwidth(self, transfer_id: str, bytes_needed: int) -> bool:
        """Acquire bandwidth tokens for transfer"""
        await self._refill_bucket()
        
        if self.current_tokens >= bytes_needed:
            self.current_tokens -= bytes_needed
            return True
        
        return False
    
    async def _refill_bucket(self):
        """Refill token bucket based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        tokens_to_add = elapsed * self.refill_rate
        self.current_tokens = min(self.bucket_size, self.current_tokens + tokens_to_add)
        self.last_refill = now
    
    def get_available_bandwidth(self) -> float:
        """Get currently available bandwidth in Mbps"""
        return (self.current_tokens * 8) / (1024 * 1024)

async def main():
    """Example usage of bandwidth-aware sync"""
    # Initialize network monitor
    monitor = NetworkMonitor(monitor_interval=10)
    
    # Start monitoring in background
    monitor_task = asyncio.create_task(monitor.start_monitoring())
    
    # Wait for initial measurements
    await asyncio.sleep(2)
    
    # Initialize scheduler
    scheduler = AdaptiveSyncScheduler(monitor)
    
    # Test transfer scheduling
    test_items = [
        {
            "id": "text-001",
            "content_type": "text",
            "file_size": 1024,
            "priority": 8,
            "age_hours": 0.5,
            "data": {"title": "Important note"}
        },
        {
            "id": "image-001", 
            "content_type": "image",
            "file_size": 5 * 1024 * 1024,
            "priority": 6,
            "age_hours": 2,
            "data": {"filename": "photo.jpg"}
        },
        {
            "id": "video-001",
            "content_type": "video", 
            "file_size": 100 * 1024 * 1024,
            "priority": 4,
            "age_hours": 24,
            "data": {"filename": "video.mp4"}
        }
    ]
    
    print("Network Quality:", monitor.get_connection_quality().value)
    print("Bandwidth Recommendation:", monitor.get_bandwidth_recommendation())
    print()
    
    for item in test_items:
        plan = scheduler.schedule_transfer(item)
        print(f"Item {item['id']} ({item['content_type']}):")
        print(f"  Action: {plan['action']}")
        print(f"  Priority: {plan.get('priority', 'N/A'):.2f}")
        print(f"  Estimated time: {plan.get('estimated_time', 0):.1f}s")
        if plan['action'] == 'defer':
            print(f"  Defer reason: {plan['reason']}")
            print(f"  Retry after: {plan['retry_after']}s")
        print()
    
    # Stop monitoring
    monitor.stop_monitoring()
    monitor_task.cancel()

if __name__ == '__main__':
    asyncio.run(main())