#!/usr/bin/env python3
"""
System Resource Monitor
Monitors CPU, memory, disk, and network usage to throttle bot activity
"""

import asyncio
import psutil
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import statistics
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ResourceMetrics:
    """System resource metrics snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    process_count: int
    load_average_1min: float
    temperature_celsius: Optional[float] = None

@dataclass
class ThrottleConfig:
    """Configuration for resource-based throttling"""
    cpu_warning_threshold: float = 70.0
    cpu_critical_threshold: float = 85.0
    memory_warning_threshold: float = 75.0
    memory_critical_threshold: float = 90.0
    disk_usage_warning_threshold: float = 80.0
    disk_usage_critical_threshold: float = 95.0
    load_warning_threshold: float = 2.0
    load_critical_threshold: float = 4.0
    temperature_warning_threshold: float = 70.0
    temperature_critical_threshold: float = 80.0
    
    # Throttling levels
    warning_bot_limit: int = 2  # Reduce to 2 bots
    critical_bot_limit: int = 1  # Reduce to 1 bot
    emergency_bot_limit: int = 0  # Stop all bots

@dataclass
class ThrottleRecommendation:
    """Recommendation for bot throttling"""
    recommended_bot_count: int
    throttle_level: str  # 'none', 'warning', 'critical', 'emergency'
    reason: str
    metrics_summary: str
    actions_to_take: List[str]
    estimated_duration: int  # seconds

class SystemResourceMonitor:
    """Monitors system resources and recommends bot throttling"""
    
    def __init__(self, config: ThrottleConfig = None):
        self.config = config or ThrottleConfig()
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history_size = 300  # 5 minutes at 1-second intervals
        self.baseline_metrics: Optional[ResourceMetrics] = None
        self.last_disk_io = None
        self.last_network_io = None
        self._baseline_task = None
    
    async def _establish_baseline(self):
        """Establish baseline resource usage when system is idle"""
        logger.info("🔍 Establishing system resource baseline...")
        
        baseline_samples = []
        for i in range(30):  # 30 seconds of samples
            metrics = await self._collect_metrics()
            baseline_samples.append(metrics)
            await asyncio.sleep(1)
        
        # Calculate baseline averages
        if baseline_samples:
            self.baseline_metrics = ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=statistics.mean([m.cpu_percent for m in baseline_samples]),
                memory_percent=statistics.mean([m.memory_percent for m in baseline_samples]),
                disk_usage_percent=statistics.mean([m.disk_usage_percent for m in baseline_samples]),
                disk_io_read_mb=statistics.mean([m.disk_io_read_mb for m in baseline_samples]),
                disk_io_write_mb=statistics.mean([m.disk_io_write_mb for m in baseline_samples]),
                network_io_sent_mb=statistics.mean([m.network_io_sent_mb for m in baseline_samples]),
                network_io_recv_mb=statistics.mean([m.network_io_recv_mb for m in baseline_samples]),
                process_count=int(statistics.mean([m.process_count for m in baseline_samples])),
                load_average_1min=statistics.mean([m.load_average_1min for m in baseline_samples]),
                temperature_celsius=statistics.mean([m.temperature_celsius for m in baseline_samples if m.temperature_celsius])
            )
            
            logger.info(f"✅ Baseline established - CPU: {self.baseline_metrics.cpu_percent:.1f}%, "
                       f"Memory: {self.baseline_metrics.memory_percent:.1f}%, "
                       f"Load: {self.baseline_metrics.load_average_1min:.2f}")
    
    async def _collect_metrics(self) -> ResourceMetrics:
        """Collect current system metrics"""
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        if disk_io:
            if self.last_disk_io:
                disk_io_read_mb = (disk_io.read_bytes - self.last_disk_io.read_bytes) / 1024 / 1024
                disk_io_write_mb = (disk_io.write_bytes - self.last_disk_io.write_bytes) / 1024 / 1024
            else:
                disk_io_read_mb = 0
                disk_io_write_mb = 0
            self.last_disk_io = disk_io
        else:
            disk_io_read_mb = disk_io_write_mb = 0
        
        # Network I/O
        network_io = psutil.net_io_counters()
        if network_io:
            if self.last_network_io:
                network_io_sent_mb = (network_io.bytes_sent - self.last_network_io.bytes_sent) / 1024 / 1024
                network_io_recv_mb = (network_io.bytes_recv - self.last_network_io.bytes_recv) / 1024 / 1024
            else:
                network_io_sent_mb = 0
                network_io_recv_mb = 0
            self.last_network_io = network_io
        else:
            network_io_sent_mb = network_io_recv_mb = 0
        
        # Process count
        process_count = len(psutil.pids())
        
        # Load average
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        load_average_1min = load_avg[0]
        
        # Temperature (if available)
        temperature = None
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get CPU temperature if available
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'core' in name.lower():
                            if entries:
                                temperature = entries[0].current
                                break
        except:
            pass
        
        return ResourceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_usage_percent=disk_usage_percent,
            disk_io_read_mb=max(disk_io_read_mb, 0),  # Ensure non-negative
            disk_io_write_mb=max(disk_io_write_mb, 0),
            network_io_sent_mb=max(network_io_sent_mb, 0),
            network_io_recv_mb=max(network_io_recv_mb, 0),
            process_count=process_count,
            load_average_1min=load_average_1min,
            temperature_celsius=temperature
        )
    
    def _add_metrics_to_history(self, metrics: ResourceMetrics):
        """Add metrics to history and maintain size limit"""
        self.metrics_history.append(metrics)
        
        # Trim history if too large
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def _get_recent_average(self, duration_seconds: int = 60) -> Optional[ResourceMetrics]:
        """Get average metrics over recent duration"""
        if not self.metrics_history:
            return None
        
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return None
        
        return ResourceMetrics(
            timestamp=datetime.now(),
            cpu_percent=statistics.mean([m.cpu_percent for m in recent_metrics]),
            memory_percent=statistics.mean([m.memory_percent for m in recent_metrics]),
            disk_usage_percent=statistics.mean([m.disk_usage_percent for m in recent_metrics]),
            disk_io_read_mb=statistics.mean([m.disk_io_read_mb for m in recent_metrics]),
            disk_io_write_mb=statistics.mean([m.disk_io_write_mb for m in recent_metrics]),
            network_io_sent_mb=statistics.mean([m.network_io_sent_mb for m in recent_metrics]),
            network_io_recv_mb=statistics.mean([m.network_io_recv_mb for m in recent_metrics]),
            process_count=int(statistics.mean([m.process_count for m in recent_metrics])),
            load_average_1min=statistics.mean([m.load_average_1min for m in recent_metrics]),
            temperature_celsius=statistics.mean([m.temperature_celsius for m in recent_metrics if m.temperature_celsius])
        )
    
    def analyze_throttle_requirements(self, current_bot_count: int = 3) -> ThrottleRecommendation:
        """Analyze current system state and recommend bot throttling"""
        
        if not self.metrics_history:
            return ThrottleRecommendation(
                recommended_bot_count=current_bot_count,
                throttle_level="none",
                reason="No metrics available yet",
                metrics_summary="Waiting for metrics collection...",
                actions_to_take=[],
                estimated_duration=0
            )
        
        # Get current and recent average metrics
        current_metrics = self.metrics_history[-1]
        avg_metrics = self._get_recent_average(60) or current_metrics
        
        # Analyze each resource type
        issues = []
        throttle_level = "none"
        recommended_bots = current_bot_count
        
        # CPU Analysis
        if avg_metrics.cpu_percent >= self.config.cpu_critical_threshold:
            issues.append(f"CPU usage critical: {avg_metrics.cpu_percent:.1f}%")
            throttle_level = "emergency"
            recommended_bots = self.config.emergency_bot_limit
        elif avg_metrics.cpu_percent >= self.config.cpu_warning_threshold:
            issues.append(f"CPU usage high: {avg_metrics.cpu_percent:.1f}%")
            if throttle_level == "none":
                throttle_level = "warning"
                recommended_bots = min(recommended_bots, self.config.warning_bot_limit)
        
        # Memory Analysis
        if avg_metrics.memory_percent >= self.config.memory_critical_threshold:
            issues.append(f"Memory usage critical: {avg_metrics.memory_percent:.1f}%")
            throttle_level = "emergency"
            recommended_bots = self.config.emergency_bot_limit
        elif avg_metrics.memory_percent >= self.config.memory_warning_threshold:
            issues.append(f"Memory usage high: {avg_metrics.memory_percent:.1f}%")
            if throttle_level == "none":
                throttle_level = "warning"
                recommended_bots = min(recommended_bots, self.config.warning_bot_limit)
        
        # Load Average Analysis
        if avg_metrics.load_average_1min >= self.config.load_critical_threshold:
            issues.append(f"System load critical: {avg_metrics.load_average_1min:.2f}")
            throttle_level = "critical"
            recommended_bots = min(recommended_bots, self.config.critical_bot_limit)
        elif avg_metrics.load_average_1min >= self.config.load_warning_threshold:
            issues.append(f"System load high: {avg_metrics.load_average_1min:.2f}")
            if throttle_level == "none":
                throttle_level = "warning"
                recommended_bots = min(recommended_bots, self.config.warning_bot_limit)
        
        # Disk Usage Analysis
        if avg_metrics.disk_usage_percent >= self.config.disk_usage_critical_threshold:
            issues.append(f"Disk usage critical: {avg_metrics.disk_usage_percent:.1f}%")
            throttle_level = "critical" if throttle_level != "emergency" else throttle_level
            recommended_bots = min(recommended_bots, self.config.critical_bot_limit)
        elif avg_metrics.disk_usage_percent >= self.config.disk_usage_warning_threshold:
            issues.append(f"Disk usage high: {avg_metrics.disk_usage_percent:.1f}%")
            if throttle_level == "none":
                throttle_level = "warning"
                recommended_bots = min(recommended_bots, self.config.warning_bot_limit)
        
        # Temperature Analysis
        if avg_metrics.temperature_celsius and avg_metrics.temperature_celsius >= self.config.temperature_critical_threshold:
            issues.append(f"Temperature critical: {avg_metrics.temperature_celsius:.1f}°C")
            throttle_level = "emergency"
            recommended_bots = self.config.emergency_bot_limit
        elif avg_metrics.temperature_celsius and avg_metrics.temperature_celsius >= self.config.temperature_warning_threshold:
            issues.append(f"Temperature high: {avg_metrics.temperature_celsius:.1f}°C")
            if throttle_level == "none":
                throttle_level = "warning"
                recommended_bots = min(recommended_bots, self.config.warning_bot_limit)
        
        # Build recommendation
        if not issues:
            reason = f"System resources healthy - CPU: {avg_metrics.cpu_percent:.1f}%, Memory: {avg_metrics.memory_percent:.1f}%, Load: {avg_metrics.load_average_1min:.2f}"
        else:
            reason = "; ".join(issues)
        
        # Determine actions
        actions = []
        if throttle_level == "warning":
            actions = [
                f"Reduce bot count to {recommended_bots}",
                "Monitor resource usage closely",
                "Consider delaying non-critical tasks"
            ]
        elif throttle_level == "critical":
            actions = [
                f"Reduce bot count to {recommended_bots}",
                "Pause resource-intensive operations",
                "Clear temporary files and caches",
                "Monitor system stability"
            ]
        elif throttle_level == "emergency":
            actions = [
                "Stop all bot operations immediately",
                "Alert system administrator",
                "Investigate resource consumption",
                "Wait for system recovery before resuming"
            ]
        
        # Estimate duration based on throttle level
        estimated_duration = {
            "none": 0,
            "warning": 300,  # 5 minutes
            "critical": 900,  # 15 minutes
            "emergency": 1800  # 30 minutes
        }.get(throttle_level, 0)
        
        metrics_summary = (f"CPU: {avg_metrics.cpu_percent:.1f}% | "
                          f"Memory: {avg_metrics.memory_percent:.1f}% | "
                          f"Load: {avg_metrics.load_average_1min:.2f} | "
                          f"Disk: {avg_metrics.disk_usage_percent:.1f}%")
        
        if avg_metrics.temperature_celsius:
            metrics_summary += f" | Temp: {avg_metrics.temperature_celsius:.1f}°C"
        
        return ThrottleRecommendation(
            recommended_bot_count=recommended_bots,
            throttle_level=throttle_level,
            reason=reason,
            metrics_summary=metrics_summary,
            actions_to_take=actions,
            estimated_duration=estimated_duration
        )
    
    async def start_monitoring(self, update_interval: int = 5):
        """Start continuous resource monitoring"""
        logger.info(f"🔍 Starting resource monitoring (interval: {update_interval}s)")
        
        # Start baseline establishment if not already running
        if not self._baseline_task:
            self._baseline_task = asyncio.create_task(self._establish_baseline())
        
        while True:
            try:
                metrics = await self._collect_metrics()
                self._add_metrics_to_history(metrics)
                
                # Log significant resource usage
                if (metrics.cpu_percent > 50 or 
                    metrics.memory_percent > 60 or 
                    metrics.load_average_1min > 1.5):
                    
                    logger.info(f"📊 Resources: CPU {metrics.cpu_percent:.1f}% | "
                               f"Memory {metrics.memory_percent:.1f}% | "
                               f"Load {metrics.load_average_1min:.2f}")
                
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"❌ Error during monitoring: {e}")
                await asyncio.sleep(update_interval)
    
    def get_resource_summary(self) -> Dict:
        """Get current resource usage summary"""
        if not self.metrics_history:
            return {"status": "no_data", "message": "No metrics collected yet"}
        
        current = self.metrics_history[-1]
        avg_5min = self._get_recent_average(300)
        
        summary = {
            "timestamp": current.timestamp.isoformat(),
            "current": {
                "cpu_percent": current.cpu_percent,
                "memory_percent": current.memory_percent,
                "disk_usage_percent": current.disk_usage_percent,
                "load_average": current.load_average_1min,
                "process_count": current.process_count
            },
            "5min_average": {
                "cpu_percent": avg_5min.cpu_percent if avg_5min else current.cpu_percent,
                "memory_percent": avg_5min.memory_percent if avg_5min else current.memory_percent,
                "load_average": avg_5min.load_average_1min if avg_5min else current.load_average_1min
            },
            "io_rates": {
                "disk_read_mb_per_sec": current.disk_io_read_mb,
                "disk_write_mb_per_sec": current.disk_io_write_mb,
                "network_sent_mb_per_sec": current.network_io_sent_mb,
                "network_recv_mb_per_sec": current.network_io_recv_mb
            }
        }
        
        if current.temperature_celsius:
            summary["current"]["temperature_celsius"] = current.temperature_celsius
        
        if self.baseline_metrics:
            summary["baseline"] = {
                "cpu_percent": self.baseline_metrics.cpu_percent,
                "memory_percent": self.baseline_metrics.memory_percent,
                "load_average": self.baseline_metrics.load_average_1min
            }
        
        return summary
    
    def get_historical_data(self, duration_minutes: int = 60) -> List[Dict]:
        """Get historical metrics for specified duration"""
        if not self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "load_average": m.load_average_1min,
                "disk_io_read_mb": m.disk_io_read_mb,
                "disk_io_write_mb": m.disk_io_write_mb
            }
            for m in recent_metrics
        ]

# Test the resource monitor
async def main():
    """Test resource monitoring"""
    
    # Custom config for testing
    config = ThrottleConfig(
        cpu_warning_threshold=50.0,
        memory_warning_threshold=60.0,
        cpu_critical_threshold=75.0,
        memory_critical_threshold=80.0
    )
    
    monitor = SystemResourceMonitor(config)
    
    print("🔍 System Resource Monitor Test")
    print("===============================")
    
    # Wait for baseline
    await asyncio.sleep(3)
    
    # Test throttle analysis
    for bot_count in [3, 2, 1]:
        recommendation = monitor.analyze_throttle_requirements(bot_count)
        
        print(f"\n🤖 Bot Count: {bot_count}")
        print(f"📊 {recommendation.metrics_summary}")
        print(f"🚦 Throttle Level: {recommendation.throttle_level}")
        print(f"💡 Recommendation: {recommendation.recommended_bot_count} bots")
        print(f"📝 Reason: {recommendation.reason}")
        
        if recommendation.actions_to_take:
            print("🎯 Actions:")
            for action in recommendation.actions_to_take:
                print(f"   • {action}")
    
    # Get resource summary
    summary = monitor.get_resource_summary()
    print(f"\n📈 Resource Summary:")
    print(json.dumps(summary, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())