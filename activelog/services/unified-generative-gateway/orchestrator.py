#!/usr/bin/env python3
"""
Building Bots Network Service Orchestrator

This orchestrator manages:
- Automatic service startup and shutdown
- Health monitoring and failover
- Load balancing and scaling
- Service dependency management
- Network coordination and optimization
"""

import asyncio
import subprocess
import psutil
import logging
import json
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting" 
    RUNNING = "running"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"
    RESTARTING = "restarting"

@dataclass
class ServiceInstance:
    name: str
    port: int
    process_id: Optional[int] = None
    status: ServiceStatus = ServiceStatus.STOPPED
    startup_command: str = ""
    health_endpoint: str = "/health"
    last_health_check: Optional[datetime] = None
    restart_count: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    response_time: float = 0.0
    error_count: int = 0
    building_specialty: str = "general"

class BuildingBotsNetworkOrchestrator:
    """Orchestrates all Building Bots Network services"""
    
    def __init__(self):
        self.services = self._load_service_configurations()
        self.running = False
        self.health_check_interval = 30  # seconds
        self.restart_threshold = 3  # max restarts before marking as failed
        self.startup_order = self._determine_startup_order()
        
        # Database for tracking
        self.db_path = "/home/activeloguser/activelog/services/unified-generative-gateway/orchestrator.db"
        self._init_database()
        
        # Performance monitoring
        self.performance_history = {}
        self.network_metrics = {
            "services_started": 0,
            "services_failed": 0,
            "total_restarts": 0,
            "uptime_start": datetime.now()
        }
    
    def _load_service_configurations(self) -> Dict[str, ServiceInstance]:
        """Load service configurations from the main gateway"""
        
        services_config = {
            "generative_tools_hub": ServiceInstance(
                name="generative_tools_hub",
                port=8500,
                startup_command="cd /home/activeloguser/activelog/services/generative-tools-hub && python main.py",
                building_specialty="multi_modal_generation"
            ),
            "image_generation_service": ServiceInstance(
                name="image_generation_service", 
                port=8480,
                startup_command="cd /home/activeloguser/activelog/services/image-generation-service && python main.py",
                building_specialty="visual_construction"
            ),
            "audio_generation_service": ServiceInstance(
                name="audio_generation_service",
                port=8481,
                startup_command="cd /home/activeloguser/activelog/services/audio-generation-service && python main.py 8481",
                building_specialty="audio_construction"
            ),
            "video_generation_service": ServiceInstance(
                name="video_generation_service",
                port=8483,
                startup_command="cd /home/activeloguser/activelog/services/video-generation-service && python main.py",
                building_specialty="video_construction"
            ),
            "code_generation_service": ServiceInstance(
                name="code_generation_service",
                port=8482,
                startup_command="cd /home/activeloguser/activelog/services/code-generation-service && python main.py",
                building_specialty="code_construction"
            ),
            "ai_picker_system": ServiceInstance(
                name="ai_picker_system",
                port=8470,
                startup_command="cd /home/activeloguser/activelog/services/ai-picker-system && python main.py",
                building_specialty="intelligence_optimization"
            ),
            "data_lifecycle_manager": ServiceInstance(
                name="data_lifecycle_manager",
                port=8490,
                startup_command="cd /home/activeloguser/activelog/services/data-lifecycle-manager && python main.py",
                building_specialty="data_construction"
            ),
            "openai_integration": ServiceInstance(
                name="openai_integration",
                port=8475,
                startup_command="cd /home/activeloguser/activelog/services/openai-integration && python main.py",
                building_specialty="ai_integration"
            ),
            "claude_task_hierarchy": ServiceInstance(
                name="claude_task_hierarchy",
                port=8474,
                startup_command="cd /home/activeloguser/activelog/services/claude-task-hierarchy && python main.py",
                building_specialty="task_construction"
            ),
            "hierarchical_task_system": ServiceInstance(
                name="hierarchical_task_system",
                port=8471,
                startup_command="cd /home/activeloguser/activelog/services/hierarchical-task-system && python main.py",
                building_specialty="system_construction"
            )
        }
        
        return services_config
    
    def _determine_startup_order(self) -> List[List[str]]:
        """Determine optimal startup order based on dependencies"""
        
        # Define startup phases - services in each phase start together
        startup_phases = [
            # Phase 1: Core infrastructure services
            ["ai_picker_system", "data_lifecycle_manager"],
            
            # Phase 2: AI integration services  
            ["openai_integration", "claude_task_hierarchy", "hierarchical_task_system"],
            
            # Phase 3: Generation services
            ["generative_tools_hub", "image_generation_service"],
            
            # Phase 4: Specialized generation services
            ["audio_generation_service", "video_generation_service", "code_generation_service"]
        ]
        
        return startup_phases
    
    def _init_database(self):
        """Initialize database for orchestrator tracking"""
        
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                cpu_usage REAL,
                memory_usage REAL,
                response_time REAL,
                error_count INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def start_network(self):
        """Start the entire Building Bots Network"""
        
        logger.info("🚀 Starting Building Bots Network orchestration...")
        
        self.running = True
        self.network_metrics["uptime_start"] = datetime.now()
        
        # Start services in phases
        for phase_num, service_names in enumerate(self.startup_order, 1):
            logger.info(f"🔧 Starting Phase {phase_num}: {', '.join(service_names)}")
            
            # Start all services in this phase concurrently
            startup_tasks = []
            for service_name in service_names:
                if service_name in self.services:
                    task = asyncio.create_task(self.start_service(service_name))
                    startup_tasks.append(task)
            
            # Wait for phase to complete
            if startup_tasks:
                results = await asyncio.gather(*startup_tasks, return_exceptions=True)
                
                # Check results
                for i, result in enumerate(results):
                    service_name = service_names[i]
                    if isinstance(result, Exception):
                        logger.error(f"❌ Failed to start {service_name}: {result}")
                        self.network_metrics["services_failed"] += 1
                    else:
                        logger.info(f"✅ Successfully started {service_name}")
                        self.network_metrics["services_started"] += 1
            
            # Wait between phases for services to fully initialize
            if phase_num < len(self.startup_order):
                await asyncio.sleep(10)
        
        # Start monitoring tasks
        asyncio.create_task(self.health_monitoring_loop())
        asyncio.create_task(self.performance_monitoring_loop())
        asyncio.create_task(self.log_network_status_loop())
        
        logger.info("✅ Building Bots Network orchestration complete")
        logger.info(f"📊 Network Status: {self.network_metrics['services_started']} started, {self.network_metrics['services_failed']} failed")
    
    async def start_service(self, service_name: str) -> bool:
        """Start a specific service"""
        
        if service_name not in self.services:
            logger.error(f"❌ Unknown service: {service_name}")
            return False
        
        service = self.services[service_name]
        
        if service.status == ServiceStatus.RUNNING:
            logger.info(f"✅ Service {service_name} already running")
            return True
        
        try:
            # Check if port is already in use
            if self._is_port_in_use(service.port):
                logger.warning(f"⚠️ Port {service.port} already in use for {service_name}")
                # Try to find the existing process
                existing_process = self._find_process_on_port(service.port)
                if existing_process:
                    service.process_id = existing_process.pid
                    service.status = ServiceStatus.RUNNING
                    await self._log_service_event(service_name, "found_existing", "running")
                    return True
            
            service.status = ServiceStatus.STARTING
            await self._log_service_event(service_name, "startup_attempt", "starting")
            
            # Start the service process
            logger.info(f"🚀 Starting {service_name} on port {service.port}...")
            logger.debug(f"Command: {service.startup_command}")
            
            process = await asyncio.create_subprocess_shell(
                service.startup_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(service.startup_command.split()[1])  # Extract directory from command
            )
            
            service.process_id = process.pid
            
            # Wait a moment for service to initialize
            await asyncio.sleep(5)
            
            # Check if service is responding
            if await self._check_service_health(service):
                service.status = ServiceStatus.RUNNING
                await self._log_service_event(service_name, "startup_success", "running")
                logger.info(f"✅ Service {service_name} started successfully (PID: {service.process_id})")
                return True
            else:
                service.status = ServiceStatus.FAILED
                await self._log_service_event(service_name, "startup_failed", "failed", "Health check failed")
                logger.error(f"❌ Service {service_name} failed health check after startup")
                return False
        
        except Exception as e:
            service.status = ServiceStatus.FAILED
            await self._log_service_event(service_name, "startup_error", "failed", str(e))
            logger.error(f"❌ Failed to start {service_name}: {e}")
            return False
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a specific service"""
        
        if service_name not in self.services:
            logger.error(f"❌ Unknown service: {service_name}")
            return False
        
        service = self.services[service_name]
        
        if service.status == ServiceStatus.STOPPED:
            logger.info(f"✅ Service {service_name} already stopped")
            return True
        
        try:
            if service.process_id:
                # Try graceful shutdown first
                try:
                    process = psutil.Process(service.process_id)
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    await asyncio.sleep(5)
                    
                    # Force kill if still running
                    if process.is_running():
                        process.kill()
                        await asyncio.sleep(2)
                    
                    service.status = ServiceStatus.STOPPED
                    service.process_id = None
                    await self._log_service_event(service_name, "shutdown", "stopped")
                    logger.info(f"✅ Service {service_name} stopped successfully")
                    return True
                
                except psutil.NoSuchProcess:
                    # Process already dead
                    service.status = ServiceStatus.STOPPED
                    service.process_id = None
                    return True
            
            else:
                logger.warning(f"⚠️ No process ID for {service_name}, marking as stopped")
                service.status = ServiceStatus.STOPPED
                return True
        
        except Exception as e:
            logger.error(f"❌ Failed to stop {service_name}: {e}")
            return False
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service"""
        
        if service_name not in self.services:
            logger.error(f"❌ Unknown service: {service_name}")
            return False
        
        service = self.services[service_name]
        
        # Check restart threshold
        if service.restart_count >= self.restart_threshold:
            logger.error(f"❌ Service {service_name} exceeded restart threshold ({self.restart_threshold})")
            service.status = ServiceStatus.FAILED
            return False
        
        service.status = ServiceStatus.RESTARTING
        service.restart_count += 1
        self.network_metrics["total_restarts"] += 1
        
        logger.info(f"🔄 Restarting {service_name} (attempt {service.restart_count}/{self.restart_threshold})")
        
        # Stop then start
        await self.stop_service(service_name)
        await asyncio.sleep(2)
        
        success = await self.start_service(service_name)
        
        if success:
            await self._log_service_event(service_name, "restart_success", "running")
        else:
            await self._log_service_event(service_name, "restart_failed", "failed")
        
        return success
    
    async def health_monitoring_loop(self):
        """Continuous health monitoring for all services"""
        
        logger.info("🏥 Starting health monitoring loop")
        
        while self.running:
            try:
                # Check all services
                health_tasks = []
                for service_name, service in self.services.items():
                    if service.status in [ServiceStatus.RUNNING, ServiceStatus.UNHEALTHY]:
                        task = asyncio.create_task(self._monitor_service_health(service_name))
                        health_tasks.append(task)
                
                # Wait for all health checks
                if health_tasks:
                    await asyncio.gather(*health_tasks, return_exceptions=True)
                
                # Sleep until next check
                await asyncio.sleep(self.health_check_interval)
            
            except Exception as e:
                logger.error(f"❌ Error in health monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_service_health(self, service_name: str):
        """Monitor health of a specific service"""
        
        service = self.services[service_name]
        
        try:
            # Check process is still running
            if service.process_id:
                try:
                    process = psutil.Process(service.process_id)
                    if not process.is_running():
                        logger.warning(f"⚠️ Process for {service_name} is no longer running")
                        service.status = ServiceStatus.FAILED
                        await self._log_service_event(service_name, "process_died", "failed")
                        
                        # Attempt restart
                        await self.restart_service(service_name)
                        return
                
                except psutil.NoSuchProcess:
                    logger.warning(f"⚠️ Process {service.process_id} for {service_name} not found")
                    service.status = ServiceStatus.FAILED
                    await self.restart_service(service_name)
                    return
            
            # Health check via HTTP
            health_result = await self._check_service_health(service)
            
            if health_result:
                if service.status == ServiceStatus.UNHEALTHY:
                    logger.info(f"✅ Service {service_name} recovered")
                    await self._log_service_event(service_name, "health_recovered", "running")
                
                service.status = ServiceStatus.RUNNING
                service.last_health_check = datetime.now()
                service.error_count = 0  # Reset error count on successful check
            
            else:
                service.error_count += 1
                
                if service.status == ServiceStatus.RUNNING:
                    logger.warning(f"⚠️ Service {service_name} health check failed")
                    service.status = ServiceStatus.UNHEALTHY
                    await self._log_service_event(service_name, "health_check_failed", "unhealthy")
                
                # If too many consecutive failures, restart
                if service.error_count >= 3:
                    logger.error(f"❌ Service {service_name} has {service.error_count} consecutive failures, restarting")
                    await self.restart_service(service_name)
        
        except Exception as e:
            logger.error(f"❌ Error monitoring {service_name}: {e}")
            service.error_count += 1
    
    async def _check_service_health(self, service: ServiceInstance) -> bool:
        """Check health of a service via HTTP"""
        
        try:
            url = f"http://localhost:{service.port}{service.health_endpoint}"
            
            start_time = time.time()
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    service.response_time = response_time
                    
                    if response.status == 200:
                        # Try to get additional metrics from health response
                        try:
                            health_data = await response.json()
                            # Extract any performance metrics if available
                        except:
                            pass  # Health endpoint might not return JSON
                        
                        return True
                    else:
                        logger.warning(f"⚠️ Service {service.name} returned HTTP {response.status}")
                        return False
        
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Health check timeout for {service.name}")
            service.response_time = 10.0  # Timeout value
            return False
        
        except Exception as e:
            logger.warning(f"⚠️ Health check error for {service.name}: {e}")
            return False
    
    async def performance_monitoring_loop(self):
        """Monitor performance metrics for all services"""
        
        logger.info("📊 Starting performance monitoring loop")
        
        while self.running:
            try:
                for service_name, service in self.services.items():
                    if service.status == ServiceStatus.RUNNING and service.process_id:
                        await self._update_service_performance(service)
                
                # Sleep for 1 minute between performance updates
                await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"❌ Error in performance monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _update_service_performance(self, service: ServiceInstance):
        """Update performance metrics for a service"""
        
        try:
            if service.process_id:
                process = psutil.Process(service.process_id)
                
                # Get CPU and memory usage
                service.cpu_usage = process.cpu_percent()
                service.memory_usage = process.memory_percent()
                
                # Store in database
                await self._store_performance_metrics(service)
                
                # Track in history for analysis
                if service.name not in self.performance_history:
                    self.performance_history[service.name] = []
                
                self.performance_history[service.name].append({
                    "timestamp": datetime.now().isoformat(),
                    "cpu_usage": service.cpu_usage,
                    "memory_usage": service.memory_usage,
                    "response_time": service.response_time
                })
                
                # Keep only last 100 readings
                if len(self.performance_history[service.name]) > 100:
                    self.performance_history[service.name] = self.performance_history[service.name][-100:]
        
        except psutil.NoSuchProcess:
            logger.warning(f"⚠️ Process {service.process_id} for {service.name} no longer exists")
            service.process_id = None
            service.status = ServiceStatus.STOPPED
        
        except Exception as e:
            logger.error(f"❌ Error updating performance for {service.name}: {e}")
    
    async def log_network_status_loop(self):
        """Periodically log network status"""
        
        while self.running:
            try:
                status = await self.get_network_status()
                logger.info(f"📊 Network Status: {status['summary']}")
                
                # Sleep for 5 minutes between status logs
                await asyncio.sleep(300)
            
            except Exception as e:
                logger.error(f"❌ Error logging network status: {e}")
                await asyncio.sleep(300)
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status"""
        
        service_statuses = {}
        healthy_count = 0
        running_count = 0
        
        for service_name, service in self.services.items():
            service_statuses[service_name] = {
                "status": service.status.value,
                "port": service.port,
                "process_id": service.process_id,
                "restart_count": service.restart_count,
                "cpu_usage": service.cpu_usage,
                "memory_usage": service.memory_usage,
                "response_time": service.response_time,
                "error_count": service.error_count,
                "building_specialty": service.building_specialty,
                "last_health_check": service.last_health_check.isoformat() if service.last_health_check else None
            }
            
            if service.status == ServiceStatus.RUNNING:
                running_count += 1
                if service.error_count == 0:
                    healthy_count += 1
        
        # Calculate uptime
        uptime = datetime.now() - self.network_metrics["uptime_start"]
        
        return {
            "services": service_statuses,
            "summary": {
                "total_services": len(self.services),
                "running_services": running_count,
                "healthy_services": healthy_count,
                "network_health_percentage": (healthy_count / len(self.services)) * 100,
                "uptime_seconds": uptime.total_seconds(),
                "total_starts": self.network_metrics["services_started"],
                "total_failures": self.network_metrics["services_failed"],
                "total_restarts": self.network_metrics["total_restarts"]
            },
            "performance_history": {
                name: history[-10:] for name, history in self.performance_history.items()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def shutdown_network(self):
        """Shutdown the entire Building Bots Network"""
        
        logger.info("🛑 Shutting down Building Bots Network...")
        
        self.running = False
        
        # Stop services in reverse order
        for phase in reversed(self.startup_order):
            logger.info(f"🔧 Stopping phase: {', '.join(phase)}")
            
            stop_tasks = []
            for service_name in phase:
                if service_name in self.services:
                    task = asyncio.create_task(self.stop_service(service_name))
                    stop_tasks.append(task)
            
            if stop_tasks:
                await asyncio.gather(*stop_tasks, return_exceptions=True)
            
            await asyncio.sleep(2)
        
        logger.info("✅ Building Bots Network shutdown complete")
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use"""
        
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False
    
    def _find_process_on_port(self, port: int) -> Optional[psutil.Process]:
        """Find process running on specific port"""
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == port:
                        return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return None
    
    async def _log_service_event(self, service_name: str, event_type: str, 
                                status: str, details: str = None):
        """Log service event to database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO service_events (service_name, event_type, status, details)
                VALUES (?, ?, ?, ?)
            ''', (service_name, event_type, status, details))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"❌ Error logging service event: {e}")
    
    async def _store_performance_metrics(self, service: ServiceInstance):
        """Store performance metrics in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (service_name, cpu_usage, memory_usage, response_time, error_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                service.name, 
                service.cpu_usage,
                service.memory_usage,
                service.response_time,
                service.error_count
            ))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"❌ Error storing performance metrics: {e}")


async def main():
    """Main orchestrator function"""
    
    orchestrator = BuildingBotsNetworkOrchestrator()
    
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, shutting down...")
        asyncio.create_task(orchestrator.shutdown_network())
        sys.exit(0)
    
    # Handle shutdown signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the network
        await orchestrator.start_network()
        
        # Keep running
        while orchestrator.running:
            await asyncio.sleep(10)
    
    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
    
    finally:
        await orchestrator.shutdown_network()

if __name__ == "__main__":
    logger.info("🏗️ Building Bots Network Orchestrator starting...")
    asyncio.run(main())