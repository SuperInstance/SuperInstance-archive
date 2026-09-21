#!/usr/bin/env python3
"""
Smart Service Manager for ActiveLog
Intelligently manages service startup, health monitoring, and resource optimization
"""

import os
import sys
import json
import time
import signal
import asyncio
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServicePriority(Enum):
    CRITICAL = 1    # Must be running for system to function
    HIGH = 2        # Important for main features
    MEDIUM = 3      # Secondary features
    LOW = 4         # Optional/development features

@dataclass
class ServiceConfig:
    name: str
    directory: Path
    port: int
    priority: ServicePriority
    dependencies: List[str]
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0
    auto_restart: bool = True
    health_endpoint: str = "/health"

class SmartServiceManager:
    def __init__(self, config_file: str = "service_config.json"):
        self.config_file = Path(config_file)
        self.services: Dict[str, ServiceConfig] = {}
        self.running_services: Dict[str, subprocess.Popen] = {}
        self.service_pids: Dict[str, int] = {}
        self.pids_dir = Path("pids")
        self.max_concurrent_starts = 4
        self.shutdown_requested = False
        
        # Create directories
        self.pids_dir.mkdir(exist_ok=True)
        
        # Load service configurations
        self._load_service_configs()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _load_service_configs(self):
        """Load service configurations from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config_data = json.load(f)
                    for name, config in config_data.items():
                        self.services[name] = ServiceConfig(
                            name=name,
                            directory=Path(config['directory']),
                            port=config['port'],
                            priority=ServicePriority(config['priority']),
                            dependencies=config.get('dependencies', []),
                            max_memory_mb=config.get('max_memory_mb', 512),
                            max_cpu_percent=config.get('max_cpu_percent', 50.0),
                            auto_restart=config.get('auto_restart', True),
                            health_endpoint=config.get('health_endpoint', '/health')
                        )
            except Exception as e:
                logger.error(f"Error loading service config: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default service configuration"""
        default_services = {
            "api-gateway": {
                "directory": "services/api-gateway",
                "port": 8088,
                "priority": 1,  # CRITICAL
                "dependencies": [],
                "max_memory_mb": 256,
                "max_cpu_percent": 30.0
            },
            "auth": {
                "directory": "services/auth",
                "port": 8002,
                "priority": 1,  # CRITICAL
                "dependencies": [],
                "max_memory_mb": 128,
                "max_cpu_percent": 20.0
            },
            "file-sync": {
                "directory": "services/file-sync",
                "port": 8000,
                "priority": 2,  # HIGH
                "dependencies": ["auth"],
                "max_memory_mb": 256,
                "max_cpu_percent": 25.0
            },
            "ai-orchestrator": {
                "directory": "services/ai-orchestrator",
                "port": 8001,
                "priority": 2,  # HIGH
                "dependencies": ["auth"],
                "max_memory_mb": 512,
                "max_cpu_percent": 40.0
            },
            "metadata": {
                "directory": "services/metadata",
                "port": 8003,
                "priority": 3,  # MEDIUM
                "dependencies": ["auth", "file-sync"],
                "max_memory_mb": 256,
                "max_cpu_percent": 30.0
            }
        }
        
        # Save default config
        with open(self.config_file, 'w') as f:
            json.dump(default_services, f, indent=2)
        
        # Load the default config
        self._load_service_configs()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_requested = True
        self.stop_all_services()
        sys.exit(0)
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            sock.close()
            return True
        except OSError:
            return False
    
    def _get_service_dependencies_sorted(self) -> List[str]:
        """Get services sorted by dependencies and priority"""
        sorted_services = []
        remaining_services = set(self.services.keys())
        
        while remaining_services:
            # Find services with no unmet dependencies
            ready_services = []
            for service_name in remaining_services:
                service = self.services[service_name]
                unmet_deps = [dep for dep in service.dependencies if dep in remaining_services]
                if not unmet_deps:
                    ready_services.append((service_name, service.priority.value))
            
            if not ready_services:
                # Circular dependency or missing dependency
                logger.warning("Circular dependency detected, starting remaining services")
                ready_services = [(name, self.services[name].priority.value) for name in remaining_services]
            
            # Sort by priority (lower number = higher priority)
            ready_services.sort(key=lambda x: x[1])
            
            # Add to sorted list and remove from remaining
            for service_name, _ in ready_services:
                sorted_services.append(service_name)
                remaining_services.remove(service_name)
        
        return sorted_services
    
    async def _check_service_health(self, service: ServiceConfig) -> bool:
        """Check if a service is healthy"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{service.port}{service.health_endpoint}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except:
            return False
    
    def _get_service_resource_usage(self, pid: int) -> Dict[str, float]:
        """Get resource usage for a service process"""
        try:
            process = psutil.Process(pid)
            return {
                'cpu_percent': process.cpu_percent(interval=1),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'memory_percent': process.memory_percent()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {'cpu_percent': 0, 'memory_mb': 0, 'memory_percent': 0}
    
    def start_service(self, service_name: str, wait_for_health: bool = True) -> bool:
        """Start a single service"""
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found in configuration")
            return False
        
        service = self.services[service_name]
        
        # Check if already running
        if service_name in self.running_services:
            logger.info(f"Service {service_name} is already running")
            return True
        
        # Check port availability
        if not self._is_port_available(service.port):
            logger.warning(f"Port {service.port} is already in use for {service_name}")
            return False
        
        # Check dependencies
        for dep in service.dependencies:
            if dep not in self.running_services:
                logger.warning(f"Dependency {dep} not running for {service_name}")
                return False
        
        # Start the service
        logger.info(f"Starting {service_name} on port {service.port}")
        
        try:
            cwd = Path.cwd() / service.directory
            if not cwd.exists():
                logger.error(f"Service directory {cwd} does not exist")
                return False
            
            # Start process
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            self.running_services[service_name] = process
            self.service_pids[service_name] = process.pid
            
            # Save PID to file
            pid_file = self.pids_dir / f"{service_name}.pid"
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait for service to be healthy
            if wait_for_health:
                max_attempts = 30
                for attempt in range(max_attempts):
                    if asyncio.run(self._check_service_health(service)):
                        logger.info(f"✅ {service_name} started successfully")
                        return True
                    
                    if process.poll() is not None:
                        logger.error(f"❌ {service_name} exited during startup")
                        self._cleanup_service(service_name)
                        return False
                    
                    await asyncio.sleep(1)
                
                logger.warning(f"⚠️  {service_name} started but health check failed")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            self._cleanup_service(service_name)
            return False
    
    def stop_service(self, service_name: str, timeout: int = 10) -> bool:
        """Stop a single service"""
        if service_name not in self.running_services:
            logger.info(f"Service {service_name} is not running")
            return True
        
        process = self.running_services[service_name]
        logger.info(f"Stopping {service_name} (PID: {process.pid})")
        
        try:
            # Send SIGTERM to process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=timeout)
                logger.info(f"✅ {service_name} stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if timeout
                logger.warning(f"Force killing {service_name}")
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
            
        except (ProcessLookupError, OSError):
            logger.warning(f"Process for {service_name} already dead")
        
        self._cleanup_service(service_name)
        return True
    
    def _cleanup_service(self, service_name: str):
        """Clean up service tracking data"""
        if service_name in self.running_services:
            del self.running_services[service_name]
        if service_name in self.service_pids:
            del self.service_pids[service_name]
        
        # Remove PID file
        pid_file = self.pids_dir / f"{service_name}.pid"
        pid_file.unlink(missing_ok=True)
    
    async def start_all_services(self, priority_filter: Optional[ServicePriority] = None):
        """Start all services in dependency order"""
        sorted_services = self._get_service_dependencies_sorted()
        
        # Filter by priority if specified
        if priority_filter:
            sorted_services = [
                name for name in sorted_services 
                if self.services[name].priority.value <= priority_filter.value
            ]
        
        # Start services in batches to limit concurrent starts
        service_batches = [
            sorted_services[i:i + self.max_concurrent_starts] 
            for i in range(0, len(sorted_services), self.max_concurrent_starts)
        ]
        
        for batch in service_batches:
            # Start batch of services concurrently
            tasks = [
                asyncio.create_task(asyncio.to_thread(self.start_service, service_name))
                for service_name in batch
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            for service_name, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Error starting {service_name}: {result}")
                elif not result:
                    logger.error(f"Failed to start {service_name}")
        
        logger.info("Service startup sequence completed")
    
    def stop_all_services(self):
        """Stop all services in reverse dependency order"""
        # Stop in reverse order
        services_to_stop = list(self.running_services.keys())
        services_to_stop.reverse()
        
        for service_name in services_to_stop:
            self.stop_service(service_name)
    
    async def monitor_services(self, interval: int = 30):
        """Monitor service health and resource usage"""
        while not self.shutdown_requested:
            logger.info("🔍 Monitoring service health...")
            
            for service_name, service in self.services.items():
                if service_name not in self.running_services:
                    continue
                
                pid = self.service_pids.get(service_name)
                if not pid:
                    continue
                
                # Check if process is alive
                process = self.running_services[service_name]
                if process.poll() is not None:
                    logger.warning(f"💀 Service {service_name} has died")
                    self._cleanup_service(service_name)
                    
                    if service.auto_restart:
                        logger.info(f"🔄 Auto-restarting {service_name}")
                        self.start_service(service_name)
                    continue
                
                # Check resource usage
                usage = self._get_service_resource_usage(pid)
                
                if usage['memory_mb'] > service.max_memory_mb:
                    logger.warning(
                        f"⚠️  {service_name} using {usage['memory_mb']:.1f}MB "
                        f"(limit: {service.max_memory_mb}MB)"
                    )
                
                if usage['cpu_percent'] > service.max_cpu_percent:
                    logger.warning(
                        f"⚠️  {service_name} using {usage['cpu_percent']:.1f}% CPU "
                        f"(limit: {service.max_cpu_percent}%)"
                    )
                
                # Check health
                if not await self._check_service_health(service):
                    logger.warning(f"💔 Health check failed for {service_name}")
            
            await asyncio.sleep(interval)
    
    def status(self) -> Dict[str, Dict]:
        """Get status of all services"""
        status_info = {}
        
        for service_name, service in self.services.items():
            is_running = service_name in self.running_services
            pid = self.service_pids.get(service_name)
            
            service_status = {
                'running': is_running,
                'pid': pid,
                'port': service.port,
                'priority': service.priority.name,
                'directory': str(service.directory)
            }
            
            if is_running and pid:
                usage = self._get_service_resource_usage(pid)
                service_status['resource_usage'] = usage
            
            status_info[service_name] = service_status
        
        return status_info

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Service Manager for ActiveLog")
    parser.add_argument("command", choices=[
        "start", "stop", "restart", "status", "monitor", "start-critical"
    ], help="Command to execute")
    parser.add_argument("--service", help="Specific service to operate on")
    parser.add_argument("--config", default="service_config.json", help="Service configuration file")
    
    args = parser.parse_args()
    
    manager = SmartServiceManager(args.config)
    
    if args.command == "start":
        if args.service:
            manager.start_service(args.service)
        else:
            await manager.start_all_services()
    
    elif args.command == "start-critical":
        await manager.start_all_services(ServicePriority.CRITICAL)
    
    elif args.command == "stop":
        if args.service:
            manager.stop_service(args.service)
        else:
            manager.stop_all_services()
    
    elif args.command == "restart":
        if args.service:
            manager.stop_service(args.service)
            time.sleep(2)
            manager.start_service(args.service)
        else:
            manager.stop_all_services()
            time.sleep(2)
            await manager.start_all_services()
    
    elif args.command == "status":
        status = manager.status()
        print(json.dumps(status, indent=2))
    
    elif args.command == "monitor":
        logger.info("Starting service monitoring...")
        await manager.monitor_services()

if __name__ == "__main__":
    asyncio.run(main())