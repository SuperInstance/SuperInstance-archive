#!/usr/bin/env python3
"""
ActiveLog Service Performance Profiler
Profiles service performance, memory usage, and identifies bottlenecks.
"""

import os
import sys
import time
import json
import asyncio
import argparse
import subprocess
import signal
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

# Optional dependencies for profiling
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import memory_profiler
    HAS_MEMORY_PROFILER = True
except ImportError:
    HAS_MEMORY_PROFILER = False

logger = logging.getLogger(__name__)


@dataclass
class ProfilerSnapshot:
    """Performance snapshot at a specific time."""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    threads: int
    open_files: int
    connections: int
    io_read_mb: float
    io_write_mb: float
    response_time_ms: Optional[float] = None
    error_count: int = 0


@dataclass
class EndpointMetrics:
    """Metrics for a specific endpoint."""
    endpoint: str
    request_count: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    error_count: int = 0
    status_codes: Dict[int, int] = field(default_factory=dict)
    
    @property
    def avg_response_time(self) -> float:
        return self.total_response_time / self.request_count if self.request_count > 0 else 0.0


class ServiceProfiler:
    """Profiles service performance and resource usage."""
    
    def __init__(self, service_name: str, service_port: int):
        self.service_name = service_name
        self.service_port = service_port
        self.process: Optional[psutil.Process] = None
        self.snapshots: List[ProfilerSnapshot] = []
        self.endpoint_metrics: Dict[str, EndpointMetrics] = {}
        self.profiling = False
        self.profile_thread: Optional[threading.Thread] = None
        
        # Initial I/O counters
        self.initial_io_read = 0
        self.initial_io_write = 0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
    
    def find_service_process(self) -> bool:
        """Find the running service process."""
        if not HAS_PSUTIL:
            logger.error("psutil not available. Install with: pip install psutil")
            return False
        
        # Look for process listening on the service port
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.info['connections']
                if connections:
                    for conn in connections:
                        if (hasattr(conn, 'laddr') and 
                            conn.laddr.port == self.service_port):
                            self.process = psutil.Process(proc.info['pid'])
                            logger.info(f"Found {self.service_name} process: PID {proc.info['pid']}")
                            
                            # Get initial I/O counters
                            try:
                                io_counters = self.process.io_counters()
                                self.initial_io_read = io_counters.read_bytes
                                self.initial_io_write = io_counters.write_bytes
                            except Exception:
                                pass
                            
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        logger.error(f"Could not find process for {self.service_name} on port {self.service_port}")
        return False
    
    def start_profiling(self, duration: int = 60, interval: float = 1.0):
        """Start profiling the service."""
        if not self.find_service_process():
            return False
        
        logger.info(f"🔍 Starting profiling for {self.service_name} (PID: {self.process.pid})")
        logger.info(f"📊 Duration: {duration}s, Interval: {interval}s")
        
        self.profiling = True
        self.snapshots.clear()
        
        # Start profiling thread
        self.profile_thread = threading.Thread(
            target=self._profile_loop,
            args=(duration, interval)
        )
        self.profile_thread.start()
        
        return True
    
    def stop_profiling(self):
        """Stop profiling the service."""
        logger.info("⏹️  Stopping profiling...")
        self.profiling = False
        
        if self.profile_thread:
            self.profile_thread.join()
    
    def _profile_loop(self, duration: int, interval: float):
        """Main profiling loop."""
        start_time = time.time()
        end_time = start_time + duration
        
        while self.profiling and time.time() < end_time:
            try:
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)
                
                # Test endpoint if available
                if HAS_REQUESTS:
                    self._test_endpoint_performance()
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error during profiling: {e}")
                time.sleep(interval)
        
        self.profiling = False
        logger.info(f"✅ Profiling completed: {len(self.snapshots)} snapshots collected")
    
    def _take_snapshot(self) -> ProfilerSnapshot:
        """Take a performance snapshot."""
        if not self.process or not self.process.is_running():
            raise RuntimeError("Process not running")
        
        # Get basic metrics
        cpu_percent = self.process.cpu_percent()
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        # Get thread and file descriptor counts
        try:
            threads = self.process.num_threads()
        except Exception:
            threads = 0
        
        try:
            open_files = len(self.process.open_files())
        except Exception:
            open_files = 0
        
        try:
            connections = len(self.process.connections())
        except Exception:
            connections = 0
        
        # Get I/O counters
        io_read_mb = 0
        io_write_mb = 0
        try:
            io_counters = self.process.io_counters()
            io_read_mb = (io_counters.read_bytes - self.initial_io_read) / (1024 * 1024)
            io_write_mb = (io_counters.write_bytes - self.initial_io_write) / (1024 * 1024)
        except Exception:
            pass
        
        return ProfilerSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_mb=memory_info.rss / (1024 * 1024),
            memory_percent=memory_percent,
            threads=threads,
            open_files=open_files,
            connections=connections,
            io_read_mb=io_read_mb,
            io_write_mb=io_write_mb
        )
    
    def _test_endpoint_performance(self):
        """Test endpoint performance."""
        endpoints_to_test = [
            '/health',
            '/info',
            '/',
        ]
        
        for endpoint in endpoints_to_test:
            try:
                start_time = time.time()
                response = requests.get(
                    f"http://localhost:{self.service_port}{endpoint}",
                    timeout=5
                )
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Update endpoint metrics
                if endpoint not in self.endpoint_metrics:
                    self.endpoint_metrics[endpoint] = EndpointMetrics(endpoint)
                
                metrics = self.endpoint_metrics[endpoint]
                metrics.request_count += 1
                metrics.total_response_time += response_time
                metrics.min_response_time = min(metrics.min_response_time, response_time)
                metrics.max_response_time = max(metrics.max_response_time, response_time)
                
                status_code = response.status_code
                metrics.status_codes[status_code] = metrics.status_codes.get(status_code, 0) + 1
                
                if status_code >= 400:
                    metrics.error_count += 1
                
                # Add response time to latest snapshot
                if self.snapshots:
                    self.snapshots[-1].response_time_ms = response_time
                
            except Exception as e:
                logger.debug(f"Error testing endpoint {endpoint}: {e}")
                
                # Record error
                if endpoint not in self.endpoint_metrics:
                    self.endpoint_metrics[endpoint] = EndpointMetrics(endpoint)
                
                self.endpoint_metrics[endpoint].error_count += 1
                
                if self.snapshots:
                    self.snapshots[-1].error_count += 1
    
    def generate_report(self, output_file: str = None) -> Dict[str, Any]:
        """Generate profiling report."""
        if not self.snapshots:
            logger.warning("No profiling data available")
            return {}
        
        report = self._calculate_metrics()
        
        # Save JSON report
        if output_file:
            json_file = f"{output_file}.json"
            with open(json_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"📄 Report saved: {json_file}")
        
        # Generate visualizations
        if HAS_MATPLOTLIB and output_file:
            self._create_visualizations(output_file, report)
        
        # Generate HTML report
        if output_file:
            self._create_html_report(f"{output_file}.html", report)
        
        return report
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from snapshots."""
        if not self.snapshots:
            return {}
        
        # Basic statistics
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_mb for s in self.snapshots]
        response_times = [s.response_time_ms for s in self.snapshots if s.response_time_ms is not None]
        
        # Calculate percentiles
        def percentile(data, p):
            if not data:
                return 0
            sorted_data = sorted(data)
            index = int(p * len(sorted_data))
            return sorted_data[min(index, len(sorted_data) - 1)]
        
        # Resource metrics
        resource_metrics = {
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'min': min(cpu_values),
                'max': max(cpu_values),
                'p95': percentile(cpu_values, 0.95),
                'p99': percentile(cpu_values, 0.99)
            },
            'memory': {
                'avg_mb': sum(memory_values) / len(memory_values),
                'min_mb': min(memory_values),
                'max_mb': max(memory_values),
                'p95_mb': percentile(memory_values, 0.95),
                'p99_mb': percentile(memory_values, 0.99)
            }
        }
        
        # Response time metrics
        if response_times:
            resource_metrics['response_time'] = {
                'avg_ms': sum(response_times) / len(response_times),
                'min_ms': min(response_times),
                'max_ms': max(response_times),
                'p95_ms': percentile(response_times, 0.95),
                'p99_ms': percentile(response_times, 0.99)
            }
        
        # Thread and connection metrics
        thread_values = [s.threads for s in self.snapshots]
        connection_values = [s.connections for s in self.snapshots]
        
        # I/O metrics
        io_read_values = [s.io_read_mb for s in self.snapshots]
        io_write_values = [s.io_write_mb for s in self.snapshots]
        
        # Endpoint metrics
        endpoint_summary = {}
        for endpoint, metrics in self.endpoint_metrics.items():
            endpoint_summary[endpoint] = {
                'request_count': metrics.request_count,
                'avg_response_time_ms': metrics.avg_response_time,
                'min_response_time_ms': metrics.min_response_time if metrics.min_response_time != float('inf') else 0,
                'max_response_time_ms': metrics.max_response_time,
                'error_count': metrics.error_count,
                'error_rate': metrics.error_count / metrics.request_count if metrics.request_count > 0 else 0,
                'status_codes': dict(metrics.status_codes)
            }
        
        return {
            'service_name': self.service_name,
            'service_port': self.service_port,
            'profiling_duration': len(self.snapshots),
            'timestamp': datetime.now().isoformat(),
            'resource_metrics': resource_metrics,
            'system_metrics': {
                'avg_threads': sum(thread_values) / len(thread_values),
                'max_threads': max(thread_values),
                'avg_connections': sum(connection_values) / len(connection_values),
                'max_connections': max(connection_values),
                'total_io_read_mb': max(io_read_values) if io_read_values else 0,
                'total_io_write_mb': max(io_write_values) if io_write_values else 0
            },
            'endpoint_metrics': endpoint_summary,
            'snapshots': [
                {
                    'timestamp': s.timestamp.isoformat(),
                    'cpu_percent': s.cpu_percent,
                    'memory_mb': s.memory_mb,
                    'response_time_ms': s.response_time_ms,
                    'threads': s.threads,
                    'connections': s.connections
                }
                for s in self.snapshots
            ]
        }
    
    def _create_visualizations(self, output_prefix: str, report: Dict[str, Any]):
        """Create performance visualization charts."""
        if not self.snapshots:
            return
        
        # Prepare data
        timestamps = [s.timestamp for s in self.snapshots]
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_mb for s in self.snapshots]
        response_times = [s.response_time_ms or 0 for s in self.snapshots]
        
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'{self.service_name} Performance Profile', fontsize=16)
        
        # CPU Usage
        ax1.plot(timestamps, cpu_values, 'b-', linewidth=2)
        ax1.set_title('CPU Usage (%)')
        ax1.set_ylabel('CPU %')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Memory Usage
        ax2.plot(timestamps, memory_values, 'g-', linewidth=2)
        ax2.set_title('Memory Usage (MB)')
        ax2.set_ylabel('Memory (MB)')
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Response Time
        if any(rt > 0 for rt in response_times):
            ax3.plot(timestamps, response_times, 'r-', linewidth=2)
            ax3.set_title('Response Time (ms)')
            ax3.set_ylabel('Time (ms)')
            ax3.grid(True, alpha=0.3)
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        else:
            ax3.text(0.5, 0.5, 'No Response Time Data', 
                    ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('Response Time (ms)')
        
        # Thread Count
        thread_values = [s.threads for s in self.snapshots]
        ax4.plot(timestamps, thread_values, 'm-', linewidth=2)
        ax4.set_title('Thread Count')
        ax4.set_ylabel('Threads')
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Format x-axis
        for ax in [ax1, ax2, ax3, ax4]:
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Save chart
        chart_file = f"{output_prefix}_performance.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"📈 Performance chart saved: {chart_file}")
        
        # Create resource utilization chart
        self._create_resource_chart(output_prefix)
    
    def _create_resource_chart(self, output_prefix: str):
        """Create resource utilization chart."""
        if not self.snapshots:
            return
        
        timestamps = [s.timestamp for s in self.snapshots]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f'{self.service_name} Resource Utilization', fontsize=16)
        
        # CPU and Memory on same chart
        ax1_mem = ax1.twinx()
        
        cpu_line = ax1.plot(timestamps, [s.cpu_percent for s in self.snapshots], 
                           'b-', linewidth=2, label='CPU %')
        mem_line = ax1_mem.plot(timestamps, [s.memory_mb for s in self.snapshots], 
                               'g-', linewidth=2, label='Memory (MB)')
        
        ax1.set_ylabel('CPU %', color='b')
        ax1_mem.set_ylabel('Memory (MB)', color='g')
        ax1.set_title('CPU and Memory Usage')
        ax1.grid(True, alpha=0.3)
        
        # Combine legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_mem.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # I/O Operations
        io_read = [s.io_read_mb for s in self.snapshots]
        io_write = [s.io_write_mb for s in self.snapshots]
        
        ax2.plot(timestamps, io_read, 'orange', linewidth=2, label='I/O Read (MB)')
        ax2.plot(timestamps, io_write, 'red', linewidth=2, label='I/O Write (MB)')
        ax2.set_ylabel('I/O (MB)')
        ax2.set_title('Disk I/O Operations')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Format x-axis
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Save chart
        resource_file = f"{output_prefix}_resources.png"
        plt.savefig(resource_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"📊 Resource chart saved: {resource_file}")
    
    def _create_html_report(self, output_file: str, report: Dict[str, Any]):
        """Create HTML report."""
        html_content = self._generate_html_content(report)
        
        try:
            with open(output_file, 'w') as f:
                f.write(html_content)
            logger.info(f"📄 HTML report saved: {output_file}")
        except Exception as e:
            logger.error(f"Failed to save HTML report: {e}")
    
    def _generate_html_content(self, report: Dict[str, Any]) -> str:
        """Generate HTML report content."""
        # Extract metrics
        resource_metrics = report.get('resource_metrics', {})
        system_metrics = report.get('system_metrics', {})
        endpoint_metrics = report.get('endpoint_metrics', {})
        
        # Generate sections
        summary_section = self._generate_summary_section(report, resource_metrics)
        endpoint_section = self._generate_endpoint_section(endpoint_metrics)
        resource_section = self._generate_resource_section(resource_metrics, system_metrics)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.service_name} Performance Profile</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; border-radius: 8px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; 
                         background: #f0f0f0; border-radius: 8px; text-align: center; }}
                .metric h3 {{ margin: 0; font-size: 24px; }}
                .metric p {{ margin: 5px 0 0 0; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .good {{ color: green; }}
                .warning {{ color: orange; }}
                .error {{ color: red; }}
                .chart-placeholder {{ background: #f5f5f5; padding: 20px; text-align: center; 
                                   border: 2px dashed #ccc; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{self.service_name} Performance Profile</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Service Port: {self.service_port}</p>
            </div>
            
            {summary_section}
            {resource_section}
            {endpoint_section}
            
            <h2>Performance Charts</h2>
            <div class="chart-placeholder">
                <p>📈 Performance charts available as separate PNG files:</p>
                <ul>
                    <li>*_performance.png - CPU, Memory, Response Time, Threads</li>
                    <li>*_resources.png - Resource Utilization and I/O</li>
                </ul>
            </div>
            
            <h2>Raw Data</h2>
            <p>Detailed profiling data available in JSON format.</p>
        </body>
        </html>
        """
    
    def _generate_summary_section(self, report: Dict[str, Any], resource_metrics: Dict[str, Any]) -> str:
        """Generate summary metrics section."""
        cpu_metrics = resource_metrics.get('cpu', {})
        memory_metrics = resource_metrics.get('memory', {})
        response_metrics = resource_metrics.get('response_time', {})
        
        return f"""
        <h2>Performance Summary</h2>
        <div>
            <div class="metric">
                <h3>{report.get('profiling_duration', 0)}</h3>
                <p>Snapshots</p>
            </div>
            <div class="metric">
                <h3>{cpu_metrics.get('avg', 0):.1f}%</h3>
                <p>Avg CPU</p>
            </div>
            <div class="metric">
                <h3>{memory_metrics.get('avg_mb', 0):.1f}MB</h3>
                <p>Avg Memory</p>
            </div>
            <div class="metric">
                <h3>{response_metrics.get('avg_ms', 0):.1f}ms</h3>
                <p>Avg Response</p>
            </div>
            <div class="metric">
                <h3>{cpu_metrics.get('p95', 0):.1f}%</h3>
                <p>P95 CPU</p>
            </div>
            <div class="metric">
                <h3>{response_metrics.get('p95_ms', 0):.1f}ms</h3>
                <p>P95 Response</p>
            </div>
        </div>
        """
    
    def _generate_resource_section(self, resource_metrics: Dict[str, Any], system_metrics: Dict[str, Any]) -> str:
        """Generate resource metrics section."""
        cpu_metrics = resource_metrics.get('cpu', {})
        memory_metrics = resource_metrics.get('memory', {})
        
        return f"""
        <h2>Resource Utilization</h2>
        <table>
            <thead>
                <tr><th>Metric</th><th>Average</th><th>Min</th><th>Max</th><th>P95</th><th>P99</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>CPU Usage (%)</td>
                    <td>{cpu_metrics.get('avg', 0):.1f}</td>
                    <td>{cpu_metrics.get('min', 0):.1f}</td>
                    <td>{cpu_metrics.get('max', 0):.1f}</td>
                    <td>{cpu_metrics.get('p95', 0):.1f}</td>
                    <td>{cpu_metrics.get('p99', 0):.1f}</td>
                </tr>
                <tr>
                    <td>Memory Usage (MB)</td>
                    <td>{memory_metrics.get('avg_mb', 0):.1f}</td>
                    <td>{memory_metrics.get('min_mb', 0):.1f}</td>
                    <td>{memory_metrics.get('max_mb', 0):.1f}</td>
                    <td>{memory_metrics.get('p95_mb', 0):.1f}</td>
                    <td>{memory_metrics.get('p99_mb', 0):.1f}</td>
                </tr>
            </tbody>
        </table>
        
        <h3>System Metrics</h3>
        <table>
            <thead>
                <tr><th>Metric</th><th>Value</th></tr>
            </thead>
            <tbody>
                <tr><td>Average Threads</td><td>{system_metrics.get('avg_threads', 0):.1f}</td></tr>
                <tr><td>Max Threads</td><td>{system_metrics.get('max_threads', 0)}</td></tr>
                <tr><td>Average Connections</td><td>{system_metrics.get('avg_connections', 0):.1f}</td></tr>
                <tr><td>Max Connections</td><td>{system_metrics.get('max_connections', 0)}</td></tr>
                <tr><td>Total I/O Read (MB)</td><td>{system_metrics.get('total_io_read_mb', 0):.2f}</td></tr>
                <tr><td>Total I/O Write (MB)</td><td>{system_metrics.get('total_io_write_mb', 0):.2f}</td></tr>
            </tbody>
        </table>
        """
    
    def _generate_endpoint_section(self, endpoint_metrics: Dict[str, Any]) -> str:
        """Generate endpoint metrics section."""
        if not endpoint_metrics:
            return "<h2>Endpoint Performance</h2><p>No endpoint data collected.</p>"
        
        rows = []
        for endpoint, metrics in endpoint_metrics.items():
            error_class = "error" if metrics['error_rate'] > 0.05 else "good"
            response_class = "warning" if metrics['avg_response_time_ms'] > 1000 else "good"
            
            rows.append(f"""
                <tr>
                    <td>{endpoint}</td>
                    <td>{metrics['request_count']}</td>
                    <td class="{response_class}">{metrics['avg_response_time_ms']:.1f}</td>
                    <td>{metrics['min_response_time_ms']:.1f}</td>
                    <td>{metrics['max_response_time_ms']:.1f}</td>
                    <td class="{error_class}">{metrics['error_count']}</td>
                    <td class="{error_class}">{metrics['error_rate']:.1%}</td>
                </tr>
            """)
        
        return f"""
        <h2>Endpoint Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Endpoint</th>
                    <th>Requests</th>
                    <th>Avg Response (ms)</th>
                    <th>Min Response (ms)</th>
                    <th>Max Response (ms)</th>
                    <th>Errors</th>
                    <th>Error Rate</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """


class MemoryProfiler:
    """Memory profiling using memory_profiler."""
    
    def __init__(self, service_name: str, service_port: int):
        self.service_name = service_name
        self.service_port = service_port
    
    def profile_memory(self, duration: int = 60) -> Optional[str]:
        """Profile memory usage of the service."""
        if not HAS_MEMORY_PROFILER:
            logger.error("memory_profiler not available. Install with: pip install memory_profiler")
            return None
        
        # Find service process PID
        service_pid = self._find_service_pid()
        if not service_pid:
            logger.error(f"Could not find process for {self.service_name}")
            return None
        
        logger.info(f"🧠 Profiling memory for {self.service_name} (PID: {service_pid})")
        
        # Run memory profiler
        output_file = f"memory_profile_{self.service_name}_{int(time.time())}.txt"
        
        try:
            subprocess.run([
                'python', '-m', 'memory_profiler',
                '--backend', 'psutil',
                '--timeout', str(duration),
                '--interval', '1',
                '--output', output_file,
                '--pid', str(service_pid)
            ], check=True)
            
            logger.info(f"📄 Memory profile saved: {output_file}")
            return output_file
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Memory profiling failed: {e}")
            return None
    
    def _find_service_pid(self) -> Optional[int]:
        """Find the service process PID."""
        if not HAS_PSUTIL:
            return None
        
        for proc in psutil.process_iter(['pid', 'connections']):
            try:
                connections = proc.info['connections']
                if connections:
                    for conn in connections:
                        if (hasattr(conn, 'laddr') and 
                            conn.laddr.port == self.service_port):
                            return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return None


def run_py_spy_profiler(service_name: str, service_port: int, duration: int = 60) -> Optional[str]:
    """Run py-spy profiler if available."""
    if not shutil.which('py-spy'):
        logger.warning("py-spy not available. Install with: pip install py-spy")
        return None
    
    # Find service process PID
    if not HAS_PSUTIL:
        logger.error("psutil required for finding process PID")
        return None
    
    service_pid = None
    for proc in psutil.process_iter(['pid', 'connections']):
        try:
            connections = proc.info['connections']
            if connections:
                for conn in connections:
                    if (hasattr(conn, 'laddr') and 
                        conn.laddr.port == service_port):
                        service_pid = proc.info['pid']
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not service_pid:
        logger.error(f"Could not find process for {service_name}")
        return None
    
    logger.info(f"🔥 Running py-spy profiler for {service_name} (PID: {service_pid})")
    
    # Run py-spy
    output_file = f"pyspy_profile_{service_name}_{int(time.time())}.svg"
    
    try:
        subprocess.run([
            'py-spy', 'record',
            '--pid', str(service_pid),
            '--duration', str(duration),
            '--output', output_file,
            '--format', 'svg'
        ], check=True)
        
        logger.info(f"🔥 py-spy profile saved: {output_file}")
        return output_file
        
    except subprocess.CalledProcessError as e:
        logger.error(f"py-spy profiling failed: {e}")
        return None


def main():
    """Main function for service profiling."""
    parser = argparse.ArgumentParser(description="ActiveLog Service Performance Profiler")
    parser.add_argument('--service', required=True, help='Service name')
    parser.add_argument('--port', type=int, help='Service port (auto-detect if not provided)')
    parser.add_argument('--duration', type=int, default=60, help='Profiling duration in seconds')
    parser.add_argument('--interval', type=float, default=1.0, help='Sampling interval in seconds')
    parser.add_argument('--output', help='Output file prefix')
    parser.add_argument('--memory', action='store_true', help='Include memory profiling')
    parser.add_argument('--py-spy', action='store_true', help='Include py-spy profiling')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Auto-detect port if not provided
    service_port = args.port
    if not service_port:
        # Try to load from CLI config
        project_root = Path(__file__).parent.parent.parent
        cli_config = project_root / "dev-tools" / "cli" / "config.yml"
        
        if cli_config.exists() and HAS_YAML:
            try:
                import yaml
                with open(cli_config) as f:
                    config = yaml.safe_load(f)
                
                services = config.get('services', {})
                if args.service in services:
                    service_port = services[args.service].get('port')
            except Exception:
                pass
    
    if not service_port:
        logger.error(f"Could not determine port for service {args.service}")
        sys.exit(1)
    
    # Setup output prefix
    output_prefix = args.output or f"profile_{args.service}_{int(time.time())}"
    
    logger.info(f"🔍 Profiling {args.service} on port {service_port}")
    
    # Main profiling
    profiler = ServiceProfiler(args.service, service_port)
    
    if not profiler.start_profiling(args.duration, args.interval):
        logger.error("Failed to start profiling")
        sys.exit(1)
    
    try:
        # Wait for profiling to complete
        profiler.profile_thread.join()
        
        # Generate report
        report = profiler.generate_report(output_prefix)
        
        # Print summary
        print("\\n📊 Profiling Summary:")
        print(f"Service: {args.service}")
        print(f"Duration: {args.duration}s")
        print(f"Snapshots: {len(profiler.snapshots)}")
        
        if report and 'resource_metrics' in report:
            cpu_metrics = report['resource_metrics'].get('cpu', {})
            memory_metrics = report['resource_metrics'].get('memory', {})
            
            print(f"Average CPU: {cpu_metrics.get('avg', 0):.1f}%")
            print(f"Peak CPU: {cpu_metrics.get('max', 0):.1f}%")
            print(f"Average Memory: {memory_metrics.get('avg_mb', 0):.1f}MB")
            print(f"Peak Memory: {memory_metrics.get('max_mb', 0):.1f}MB")
        
        # Additional profiling
        if args.memory:
            memory_profiler = MemoryProfiler(args.service, service_port)
            memory_file = memory_profiler.profile_memory(60)
            if memory_file:
                print(f"Memory profile: {memory_file}")
        
        if args.py_spy:
            pyspy_file = run_py_spy_profiler(args.service, service_port, 30)
            if pyspy_file:
                print(f"py-spy profile: {pyspy_file}")
        
        print(f"\\n📁 Reports saved with prefix: {output_prefix}")
        
    except KeyboardInterrupt:
        print("\\n⚠️  Profiling interrupted by user")
        profiler.stop_profiling()
    except Exception as e:
        logger.error(f"Profiling failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()