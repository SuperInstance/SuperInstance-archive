#!/usr/bin/env python3
"""
ActiveLog Plugin Resource Monitor - Monitor and enforce resource limits
"""

import asyncio
import logging
import psutil
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable


@dataclass
class ResourceUsage:
    cpu_percent: float
    memory_bytes: int
    disk_read_bytes: int
    disk_write_bytes: int
    network_sent_bytes: int
    network_recv_bytes: int
    open_files: int
    processes: int
    timestamp: float


@dataclass
class ResourceQuota:
    cpu_limit_percent: float = 50.0  # Max CPU usage
    memory_limit_bytes: int = 256 * 1024 * 1024  # 256MB
    disk_read_limit_bytes: int = 100 * 1024 * 1024  # 100MB
    disk_write_limit_bytes: int = 50 * 1024 * 1024   # 50MB
    network_limit_bytes: int = 10 * 1024 * 1024      # 10MB total
    max_open_files: int = 64
    max_processes: int = 10
    time_limit_seconds: int = 300  # 5 minutes max execution


@dataclass
class ViolationEvent:
    plugin_id: str
    violation_type: str
    current_value: float
    limit_value: float
    severity: str  # warning, critical
    timestamp: float
    message: str


class ResourceMonitor:
    """Monitor resource usage for plugin processes"""
    
    def __init__(self, plugin_id: str, quota: ResourceQuota):
        self.plugin_id = plugin_id
        self.quota = quota
        self.logger = logging.getLogger(f"{__name__}.{plugin_id}")
        
        self.start_time = time.time()
        self.initial_usage = None
        self.monitoring = False
        self.violations = []
        self.callbacks = []
        
        # Track cumulative usage
        self.cumulative_disk_read = 0
        self.cumulative_disk_write = 0
        self.cumulative_network = 0
    
    def add_violation_callback(self, callback: Callable[[ViolationEvent], None]):
        """Add callback for violation events"""
        self.callbacks.append(callback)
    
    async def start_monitoring(self, pid: Optional[int] = None, container_id: Optional[str] = None):
        """Start monitoring resources"""
        self.monitoring = True
        self.start_time = time.time()
        
        if pid:
            await self._monitor_process(pid)
        elif container_id:
            await self._monitor_container(container_id)
        else:
            raise ValueError("Either pid or container_id must be provided")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
    
    async def _monitor_process(self, pid: int):
        """Monitor a specific process and its children"""
        try:
            process = psutil.Process(pid)
            self.initial_usage = self._get_process_usage(process)
            
            while self.monitoring:
                current_usage = self._get_process_usage(process)
                await self._check_limits(current_usage)
                await asyncio.sleep(1)  # Check every second
                
        except psutil.NoSuchProcess:
            self.logger.info(f"Process {pid} no longer exists")
            self.monitoring = False
        except Exception as e:
            self.logger.error(f"Error monitoring process {pid}: {e}")
            self.monitoring = False
    
    async def _monitor_container(self, container_id: str):
        """Monitor Docker container resources"""
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(container_id)
            
            while self.monitoring and container.status == 'running':
                stats = container.stats(stream=False)
                current_usage = self._parse_container_stats(stats)
                await self._check_limits(current_usage)
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error monitoring container {container_id}: {e}")
            self.monitoring = False
    
    def _get_process_usage(self, process: psutil.Process) -> ResourceUsage:
        """Get current resource usage for process and children"""
        try:
            # Get process and all children
            processes = [process] + process.children(recursive=True)
            
            # Aggregate usage
            total_cpu = 0
            total_memory = 0
            total_disk_read = 0
            total_disk_write = 0
            total_network_sent = 0
            total_network_recv = 0
            total_open_files = 0
            total_processes = len(processes)
            
            for proc in processes:
                try:
                    # CPU usage
                    total_cpu += proc.cpu_percent()
                    
                    # Memory usage
                    memory_info = proc.memory_info()
                    total_memory += memory_info.rss
                    
                    # Disk I/O
                    io_counters = proc.io_counters()
                    total_disk_read += io_counters.read_bytes
                    total_disk_write += io_counters.write_bytes
                    
                    # Network I/O (not per-process, but approximate)
                    net_io = psutil.net_io_counters()
                    if net_io:
                        total_network_sent += net_io.bytes_sent / total_processes  # Rough estimate
                        total_network_recv += net_io.bytes_recv / total_processes
                    
                    # Open files
                    total_open_files += len(proc.open_files())
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return ResourceUsage(
                cpu_percent=total_cpu,
                memory_bytes=total_memory,
                disk_read_bytes=total_disk_read,
                disk_write_bytes=total_disk_write,
                network_sent_bytes=total_network_sent,
                network_recv_bytes=total_network_recv,
                open_files=total_open_files,
                processes=total_processes,
                timestamp=time.time()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting process usage: {e}")
            return ResourceUsage(0, 0, 0, 0, 0, 0, 0, 0, time.time())
    
    def _parse_container_stats(self, stats: Dict) -> ResourceUsage:
        """Parse Docker container stats"""
        try:
            # CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
            
            # Memory usage
            memory_bytes = stats['memory_stats']['usage']
            
            # Network I/O
            networks = stats.get('networks', {})
            network_sent = sum(net['tx_bytes'] for net in networks.values())
            network_recv = sum(net['rx_bytes'] for net in networks.values())
            
            # Block I/O
            blkio = stats.get('blkio_stats', {})
            disk_read = sum(item['value'] for item in blkio.get('io_service_bytes_recursive', []) 
                          if item['op'] == 'Read')
            disk_write = sum(item['value'] for item in blkio.get('io_service_bytes_recursive', []) 
                           if item['op'] == 'Write')
            
            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_bytes=memory_bytes,
                disk_read_bytes=disk_read,
                disk_write_bytes=disk_write,
                network_sent_bytes=network_sent,
                network_recv_bytes=network_recv,
                open_files=0,  # Not available from container stats
                processes=len(stats.get('pids_stats', {}).get('current', [])),
                timestamp=time.time()
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing container stats: {e}")
            return ResourceUsage(0, 0, 0, 0, 0, 0, 0, 0, time.time())
    
    async def _check_limits(self, usage: ResourceUsage):
        """Check current usage against limits and trigger violations"""
        violations = []
        
        # Check time limit
        elapsed_time = time.time() - self.start_time
        if elapsed_time > self.quota.time_limit_seconds:
            violations.append(ViolationEvent(
                plugin_id=self.plugin_id,
                violation_type="time_limit",
                current_value=elapsed_time,
                limit_value=self.quota.time_limit_seconds,
                severity="critical",
                timestamp=time.time(),
                message=f"Execution time limit exceeded: {elapsed_time:.1f}s > {self.quota.time_limit_seconds}s"
            ))
        
        # Check CPU limit
        if usage.cpu_percent > self.quota.cpu_limit_percent:
            violations.append(ViolationEvent(
                plugin_id=self.plugin_id,
                violation_type="cpu_limit",
                current_value=usage.cpu_percent,
                limit_value=self.quota.cpu_limit_percent,
                severity="warning",
                timestamp=usage.timestamp,
                message=f"CPU usage exceeded: {usage.cpu_percent:.1f}% > {self.quota.cpu_limit_percent}%"
            ))
        
        # Check memory limit
        if usage.memory_bytes > self.quota.memory_limit_bytes:
            violations.append(ViolationEvent(
                plugin_id=self.plugin_id,
                violation_type="memory_limit",
                current_value=usage.memory_bytes,
                limit_value=self.quota.memory_limit_bytes,
                severity="critical",
                timestamp=usage.timestamp,
                message=f"Memory usage exceeded: {usage.memory_bytes / 1024 / 1024:.1f}MB > {self.quota.memory_limit_bytes / 1024 / 1024:.1f}MB"
            ))
        
        # Check disk I/O limits
        if self.initial_usage:
            disk_read_delta = usage.disk_read_bytes - self.initial_usage.disk_read_bytes
            disk_write_delta = usage.disk_write_bytes - self.initial_usage.disk_write_bytes
            
            if disk_read_delta > self.quota.disk_read_limit_bytes:
                violations.append(ViolationEvent(
                    plugin_id=self.plugin_id,
                    violation_type="disk_read_limit",
                    current_value=disk_read_delta,
                    limit_value=self.quota.disk_read_limit_bytes,
                    severity="warning",
                    timestamp=usage.timestamp,
                    message=f"Disk read limit exceeded: {disk_read_delta / 1024 / 1024:.1f}MB > {self.quota.disk_read_limit_bytes / 1024 / 1024:.1f}MB"
                ))
            
            if disk_write_delta > self.quota.disk_write_limit_bytes:
                violations.append(ViolationEvent(
                    plugin_id=self.plugin_id,
                    violation_type="disk_write_limit",
                    current_value=disk_write_delta,
                    limit_value=self.quota.disk_write_limit_bytes,
                    severity="warning",
                    timestamp=usage.timestamp,
                    message=f"Disk write limit exceeded: {disk_write_delta / 1024 / 1024:.1f}MB > {self.quota.disk_write_limit_bytes / 1024 / 1024:.1f}MB"
                ))
        
        # Check network limit (combined sent + received)
        total_network = usage.network_sent_bytes + usage.network_recv_bytes
        if total_network > self.quota.network_limit_bytes:
            violations.append(ViolationEvent(
                plugin_id=self.plugin_id,
                violation_type="network_limit",
                current_value=total_network,
                limit_value=self.quota.network_limit_bytes,
                severity="warning",
                timestamp=usage.timestamp,
                message=f"Network usage exceeded: {total_network / 1024 / 1024:.1f}MB > {self.quota.network_limit_bytes / 1024 / 1024:.1f}MB"
            ))
        
        # Check open files limit
        if usage.open_files > self.quota.max_open_files:
            violations.append(ViolationEvent(
                plugin_id=self.plugin_id,
                violation_type="open_files_limit",
                current_value=usage.open_files,
                limit_value=self.quota.max_open_files,
                severity="warning",
                timestamp=usage.timestamp,
                message=f"Open files limit exceeded: {usage.open_files} > {self.quota.max_open_files}"
            ))
        
        # Check processes limit
        if usage.processes > self.quota.max_processes:
            violations.append(ViolationEvent(
                plugin_id=self.plugin_id,
                violation_type="processes_limit",
                current_value=usage.processes,
                limit_value=self.quota.max_processes,
                severity="critical",
                timestamp=usage.timestamp,
                message=f"Process count exceeded: {usage.processes} > {self.quota.max_processes}"
            ))
        
        # Handle violations
        for violation in violations:
            await self._handle_violation(violation)
    
    async def _handle_violation(self, violation: ViolationEvent):
        """Handle resource limit violation"""
        self.violations.append(violation)
        
        # Log violation
        if violation.severity == "critical":
            self.logger.error(violation.message)
        else:
            self.logger.warning(violation.message)
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(violation)
            except Exception as e:
                self.logger.error(f"Error in violation callback: {e}")
        
        # Take action based on severity
        if violation.severity == "critical":
            self.logger.error(f"Critical violation for plugin {self.plugin_id}, stopping execution")
            self.monitoring = False
    
    def get_violations(self) -> List[ViolationEvent]:
        """Get all violations that occurred"""
        return self.violations.copy()
    
    def get_summary(self) -> Dict:
        """Get monitoring summary"""
        return {
            'plugin_id': self.plugin_id,
            'monitoring_duration': time.time() - self.start_time,
            'violations_count': len(self.violations),
            'violations_by_type': self._group_violations_by_type(),
            'quota': {
                'cpu_limit_percent': self.quota.cpu_limit_percent,
                'memory_limit_mb': self.quota.memory_limit_bytes / 1024 / 1024,
                'disk_read_limit_mb': self.quota.disk_read_limit_bytes / 1024 / 1024,
                'disk_write_limit_mb': self.quota.disk_write_limit_bytes / 1024 / 1024,
                'network_limit_mb': self.quota.network_limit_bytes / 1024 / 1024,
                'max_open_files': self.quota.max_open_files,
                'max_processes': self.quota.max_processes,
                'time_limit_seconds': self.quota.time_limit_seconds
            }
        }
    
    def _group_violations_by_type(self) -> Dict[str, int]:
        """Group violations by type for summary"""
        counts = {}
        for violation in self.violations:
            counts[violation.violation_type] = counts.get(violation.violation_type, 0) + 1
        return counts


class ResourceManager:
    """Manage resource monitoring for multiple plugins"""
    
    def __init__(self):
        self.monitors = {}
        self.logger = logging.getLogger(__name__)
    
    def create_monitor(self, plugin_id: str, quota: ResourceQuota) -> ResourceMonitor:
        """Create a new resource monitor for a plugin"""
        monitor = ResourceMonitor(plugin_id, quota)
        self.monitors[plugin_id] = monitor
        return monitor
    
    def remove_monitor(self, plugin_id: str):
        """Remove resource monitor"""
        if plugin_id in self.monitors:
            self.monitors[plugin_id].stop_monitoring()
            del self.monitors[plugin_id]
    
    def get_monitor(self, plugin_id: str) -> Optional[ResourceMonitor]:
        """Get resource monitor for plugin"""
        return self.monitors.get(plugin_id)
    
    def get_all_summaries(self) -> Dict[str, Dict]:
        """Get summaries for all active monitors"""
        return {
            plugin_id: monitor.get_summary() 
            for plugin_id, monitor in self.monitors.items()
        }
    
    async def shutdown_all(self):
        """Shutdown all monitors"""
        for monitor in self.monitors.values():
            monitor.stop_monitoring()
        self.monitors.clear()


# Global resource manager instance
resource_manager = ResourceManager()


async def main():
    """Test the resource monitor"""
    import json
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: resource-monitor.py <pid>")
        sys.exit(1)
    
    pid = int(sys.argv[1])
    
    # Create test quota
    quota = ResourceQuota(
        cpu_limit_percent=25.0,
        memory_limit_bytes=128 * 1024 * 1024,  # 128MB
        time_limit_seconds=60
    )
    
    # Create monitor
    monitor = ResourceMonitor(f"test-plugin-{pid}", quota)
    
    # Add violation callback
    def on_violation(violation: ViolationEvent):
        print(f"VIOLATION: {violation.message}")
    
    monitor.add_violation_callback(on_violation)
    
    # Start monitoring
    try:
        await monitor.start_monitoring(pid=pid)
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        
        # Print summary
        summary = monitor.get_summary()
        print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    asyncio.run(main())