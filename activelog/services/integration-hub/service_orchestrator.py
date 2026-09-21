"""
ActiveLog Integration Hub - Service Orchestration Layer
Manages service lifecycle, deployment, scaling, and coordination across all services
"""

import asyncio
import json
import logging
import subprocess
import psutil
import time
import docker
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from service_discovery import ServiceDiscovery, ServiceInfo, ServiceStatus
from health_monitor import HealthMonitor
from configuration_manager import ConfigurationManager
import yaml
import signal
import os

class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    SCALING = "scaling"
    UPDATING = "updating"
    MAINTENANCE = "maintenance"

class DeploymentStrategy(Enum):
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    CANARY = "canary"
    RECREATE = "recreate"

class ScalingPolicy(Enum):
    MANUAL = "manual"
    CPU_BASED = "cpu_based"
    MEMORY_BASED = "memory_based"
    REQUEST_BASED = "request_based"
    CUSTOM = "custom"

@dataclass
class ServiceInstance:
    instance_id: str
    service_name: str
    host: str
    port: int
    pid: Optional[int] = None
    container_id: Optional[str] = None
    state: ServiceState = ServiceState.STOPPED
    health_status: ServiceStatus = ServiceStatus.UNKNOWN
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    resource_usage: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceDeployment:
    service_name: str
    version: str
    strategy: DeploymentStrategy
    target_instances: int
    current_instances: List[ServiceInstance] = field(default_factory=list)
    deployment_config: Dict[str, Any] = field(default_factory=dict)
    rollback_version: Optional[str] = None
    deployment_status: str = "planned"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class ScalingRule:
    service_name: str
    policy: ScalingPolicy
    min_instances: int
    max_instances: int
    target_cpu_percent: float = 70.0
    target_memory_percent: float = 80.0
    target_requests_per_second: float = 100.0
    scale_up_threshold: float = 80.0
    scale_down_threshold: float = 30.0
    cooldown_minutes: int = 5
    enabled: bool = True

@dataclass
class OrchestrationTask:
    task_id: str
    task_type: str  # start, stop, scale, deploy, update
    service_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: float = 0.0

class ServiceOrchestrator:
    """Central service orchestration system"""
    
    def __init__(self, discovery: ServiceDiscovery, health_monitor: HealthMonitor, 
                 config_manager: ConfigurationManager):
        self.discovery = discovery
        self.health_monitor = health_monitor
        self.config_manager = config_manager
        
        # Service management
        self.service_instances: Dict[str, List[ServiceInstance]] = {}
        self.service_deployments: Dict[str, ServiceDeployment] = {}
        self.scaling_rules: Dict[str, ScalingRule] = {}
        
        # Task management
        self.pending_tasks: List[OrchestrationTask] = []
        self.running_tasks: Dict[str, OrchestrationTask] = {}
        self.completed_tasks: List[OrchestrationTask] = []
        
        # Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception:
            self.docker_client = None
            logging.warning("Docker client not available")
        
        # Service definitions
        self.service_definitions: Dict[str, Dict[str, Any]] = {}
        
        # Orchestration settings
        self.max_concurrent_tasks = 10
        self.task_timeout_minutes = 30
        self.health_check_interval = 30
        self.scaling_check_interval = 60
        
        # Control flags
        self.running = False
        
    async def initialize(self):
        """Initialize the orchestrator"""
        # Load service definitions
        await self.load_service_definitions()
        
        # Discover existing service instances
        await self.discover_service_instances()
        
        # Load scaling rules
        await self.load_scaling_rules()
        
        # Start background tasks
        self.running = True
        asyncio.create_task(self.task_processor())
        asyncio.create_task(self.health_checker())
        asyncio.create_task(self.auto_scaler())
        asyncio.create_task(self.resource_monitor())
        
        logging.info("Service orchestrator initialized")
        logging.info(f"Managing {len(self.service_instances)} services")
    
    async def load_service_definitions(self):
        """Load service definitions from configuration"""
        definitions_file = Path("/home/activeloguser/activelog/services/definitions.yaml")
        
        if definitions_file.exists():
            try:
                with open(definitions_file, 'r') as f:
                    definitions_data = yaml.safe_load(f)
                    self.service_definitions = definitions_data or {}
            except Exception as e:
                logging.error(f"Failed to load service definitions: {e}")
        
        # Auto-generate basic definitions for discovered services
        await self.discovery.discover_all_services()
        for service_name, service_info in self.discovery.services.items():
            if service_name not in self.service_definitions:
                self.service_definitions[service_name] = await self.generate_service_definition(service_info)
    
    async def generate_service_definition(self, service_info: ServiceInfo) -> Dict[str, Any]:
        """Auto-generate service definition from discovered service"""
        service_path = Path(f"/home/activeloguser/activelog/services/{service_info.name}")
        
        definition = {
            "name": service_info.name,
            "version": "1.0.0",
            "type": service_info.service_type.value,
            "port": service_info.port,
            "health_endpoint": service_info.health_endpoint,
            "instances": {
                "min": 1,
                "max": 3,
                "desired": 1
            },
            "resources": {
                "cpu_limit": "500m",
                "memory_limit": "512Mi",
                "cpu_request": "100m",
                "memory_request": "128Mi"
            },
            "deployment": {
                "strategy": "rolling",
                "max_unavailable": 1,
                "max_surge": 1
            }
        }
        
        # Check for Docker configuration
        dockerfile = service_path / "Dockerfile"
        docker_compose = service_path / "docker-compose.yml"
        
        if dockerfile.exists():
            definition["runtime"] = "docker"
            definition["build"] = {
                "context": str(service_path),
                "dockerfile": "Dockerfile"
            }
        elif docker_compose.exists():
            definition["runtime"] = "docker-compose"
            definition["compose_file"] = str(docker_compose)
        else:
            # Check for common runtime files
            package_json = service_path / "package.json"
            requirements_txt = service_path / "requirements.txt"
            
            if package_json.exists():
                definition["runtime"] = "nodejs"
                definition["start_command"] = "npm start"
            elif requirements_txt.exists():
                definition["runtime"] = "python"
                definition["start_command"] = "python main.py"
            else:
                definition["runtime"] = "generic"
        
        return definition
    
    async def discover_service_instances(self):
        """Discover existing service instances"""
        # Discover from running processes
        await self.discover_process_instances()
        
        # Discover from Docker containers
        if self.docker_client:
            await self.discover_docker_instances()
    
    async def discover_process_instances(self):
        """Discover service instances from running processes"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                proc_info = proc.info
                cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                
                # Try to match process to a known service
                for service_name in self.service_definitions.keys():
                    if (service_name in cmdline or 
                        any(service_name in arg for arg in proc_info['cmdline']) or
                        proc_info['name'] == service_name):
                        
                        instance = ServiceInstance(
                            instance_id=f"{service_name}-{proc_info['pid']}",
                            service_name=service_name,
                            host="localhost",
                            port=self.extract_port_from_cmdline(cmdline),
                            pid=proc_info['pid'],
                            state=ServiceState.RUNNING,
                            start_time=datetime.fromtimestamp(proc_info['create_time']),
                            metadata={
                                "discovery_method": "process",
                                "cmdline": cmdline
                            }
                        )
                        
                        if service_name not in self.service_instances:
                            self.service_instances[service_name] = []
                        
                        self.service_instances[service_name].append(instance)
                        break
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    async def discover_docker_instances(self):
        """Discover service instances from Docker containers"""
        try:
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                # Try to match container to a service
                container_name = container.name
                image_name = container.image.tags[0] if container.image.tags else ""
                
                for service_name in self.service_definitions.keys():
                    if (service_name in container_name or 
                        service_name in image_name):
                        
                        # Extract port mapping
                        port = 0
                        if container.ports:
                            for container_port, host_bindings in container.ports.items():
                                if host_bindings:
                                    port = int(host_bindings[0]['HostPort'])
                                    break
                        
                        # Determine state
                        state = ServiceState.RUNNING if container.status == 'running' else ServiceState.STOPPED
                        
                        instance = ServiceInstance(
                            instance_id=f"{service_name}-{container.short_id}",
                            service_name=service_name,
                            host="localhost",
                            port=port,
                            container_id=container.id,
                            state=state,
                            start_time=datetime.fromisoformat(container.attrs['Created'].replace('Z', '+00:00')),
                            metadata={
                                "discovery_method": "docker",
                                "container_name": container_name,
                                "image": image_name,
                                "status": container.status
                            }
                        )
                        
                        if service_name not in self.service_instances:
                            self.service_instances[service_name] = []
                        
                        self.service_instances[service_name].append(instance)
                        break
                        
        except Exception as e:
            logging.error(f"Failed to discover Docker instances: {e}")
    
    def extract_port_from_cmdline(self, cmdline: str) -> int:
        """Extract port number from command line"""
        import re
        patterns = [
            r'--port[=\s]+(\d+)',
            r'-p[=\s]+(\d+)',
            r'port[=\s]*(\d+)',
            r':(\d{4,5})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, cmdline, re.IGNORECASE)
            if match:
                port = int(match.group(1))
                if 3000 <= port <= 9999:
                    return port
        
        return 0
    
    async def load_scaling_rules(self):
        """Load auto-scaling rules"""
        scaling_file = Path("/home/activeloguser/activelog/config/scaling.yaml")
        
        if scaling_file.exists():
            try:
                with open(scaling_file, 'r') as f:
                    scaling_data = yaml.safe_load(f)
                    
                    for service_name, rule_config in scaling_data.items():
                        self.scaling_rules[service_name] = ScalingRule(
                            service_name=service_name,
                            policy=ScalingPolicy(rule_config.get('policy', 'manual')),
                            min_instances=rule_config.get('min_instances', 1),
                            max_instances=rule_config.get('max_instances', 5),
                            target_cpu_percent=rule_config.get('target_cpu', 70.0),
                            target_memory_percent=rule_config.get('target_memory', 80.0),
                            scale_up_threshold=rule_config.get('scale_up_threshold', 80.0),
                            scale_down_threshold=rule_config.get('scale_down_threshold', 30.0),
                            cooldown_minutes=rule_config.get('cooldown_minutes', 5),
                            enabled=rule_config.get('enabled', True)
                        )
            except Exception as e:
                logging.error(f"Failed to load scaling rules: {e}")
        
        # Create default scaling rules for services without explicit rules
        for service_name in self.service_definitions.keys():
            if service_name not in self.scaling_rules:
                self.scaling_rules[service_name] = ScalingRule(
                    service_name=service_name,
                    policy=ScalingPolicy.MANUAL,
                    min_instances=1,
                    max_instances=3
                )
    
    async def start_service(self, service_name: str, instances: int = 1) -> str:
        """Start service instances"""
        task = OrchestrationTask(
            task_id=f"start_{service_name}_{int(time.time())}",
            task_type="start",
            service_name=service_name,
            parameters={"instances": instances}
        )
        
        self.pending_tasks.append(task)
        return task.task_id
    
    async def stop_service(self, service_name: str) -> str:
        """Stop all instances of a service"""
        task = OrchestrationTask(
            task_id=f"stop_{service_name}_{int(time.time())}",
            task_type="stop",
            service_name=service_name
        )
        
        self.pending_tasks.append(task)
        return task.task_id
    
    async def scale_service(self, service_name: str, target_instances: int) -> str:
        """Scale service to target number of instances"""
        task = OrchestrationTask(
            task_id=f"scale_{service_name}_{int(time.time())}",
            task_type="scale",
            service_name=service_name,
            parameters={"target_instances": target_instances}
        )
        
        self.pending_tasks.append(task)
        return task.task_id
    
    async def deploy_service(self, service_name: str, version: str, 
                           strategy: DeploymentStrategy = DeploymentStrategy.ROLLING) -> str:
        """Deploy new version of a service"""
        task = OrchestrationTask(
            task_id=f"deploy_{service_name}_{int(time.time())}",
            task_type="deploy",
            service_name=service_name,
            parameters={
                "version": version,
                "strategy": strategy.value
            }
        )
        
        self.pending_tasks.append(task)
        return task.task_id
    
    async def execute_start_task(self, task: OrchestrationTask):
        """Execute service start task"""
        service_name = task.service_name
        instances_count = task.parameters.get("instances", 1)
        
        if service_name not in self.service_definitions:
            raise Exception(f"Service definition not found for {service_name}")
        
        definition = self.service_definitions[service_name]
        
        for i in range(instances_count):
            instance_id = f"{service_name}-{int(time.time())}-{i}"
            
            try:
                instance = await self.create_service_instance(service_name, instance_id, definition)
                
                if service_name not in self.service_instances:
                    self.service_instances[service_name] = []
                
                self.service_instances[service_name].append(instance)
                
                task.progress = ((i + 1) / instances_count) * 100
                
            except Exception as e:
                logging.error(f"Failed to start instance {instance_id}: {e}")
                raise
    
    async def create_service_instance(self, service_name: str, instance_id: str, 
                                    definition: Dict[str, Any]) -> ServiceInstance:
        """Create and start a service instance"""
        runtime = definition.get("runtime", "generic")
        port = definition.get("port", 0)
        
        instance = ServiceInstance(
            instance_id=instance_id,
            service_name=service_name,
            host="localhost",
            port=port,
            state=ServiceState.STARTING,
            start_time=datetime.now()
        )
        
        try:
            if runtime == "docker":
                await self.start_docker_instance(instance, definition)
            elif runtime == "docker-compose":
                await self.start_compose_instance(instance, definition)
            elif runtime in ["nodejs", "python"]:
                await self.start_process_instance(instance, definition)
            else:
                raise Exception(f"Unsupported runtime: {runtime}")
            
            instance.state = ServiceState.RUNNING
            
        except Exception as e:
            instance.state = ServiceState.FAILED
            instance.metadata["error"] = str(e)
            raise
        
        return instance
    
    async def start_docker_instance(self, instance: ServiceInstance, definition: Dict[str, Any]):
        """Start service instance using Docker"""
        if not self.docker_client:
            raise Exception("Docker client not available")
        
        # Build image if needed
        build_config = definition.get("build")
        if build_config:
            image_name = f"{instance.service_name}:latest"
            
            try:
                self.docker_client.images.build(
                    path=build_config["context"],
                    dockerfile=build_config.get("dockerfile", "Dockerfile"),
                    tag=image_name
                )
            except Exception as e:
                logging.warning(f"Failed to build image: {e}")
                # Try to use existing image
        
        # Prepare container configuration
        container_config = {
            "image": f"{instance.service_name}:latest",
            "name": instance.instance_id,
            "detach": True,
            "ports": {f"{instance.port}/tcp": instance.port} if instance.port > 0 else {},
            "environment": await self.get_service_environment(instance.service_name),
            "labels": {
                "orchestrator": "activelog-integration-hub",
                "service": instance.service_name
            }
        }
        
        # Start container
        container = self.docker_client.containers.run(**container_config)
        instance.container_id = container.id
        instance.metadata["container_name"] = container.name
    
    async def start_compose_instance(self, instance: ServiceInstance, definition: Dict[str, Any]):
        """Start service instance using docker-compose"""
        compose_file = definition.get("compose_file")
        if not compose_file:
            raise Exception("Docker compose file not specified")
        
        # Run docker-compose up
        process = await asyncio.create_subprocess_exec(
            "docker-compose", "-f", compose_file, "up", "-d",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(compose_file).parent
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"docker-compose failed: {stderr.decode()}")
        
        instance.metadata["compose_file"] = compose_file
    
    async def start_process_instance(self, instance: ServiceInstance, definition: Dict[str, Any]):
        """Start service instance as a process"""
        start_command = definition.get("start_command")
        if not start_command:
            raise Exception("Start command not specified")
        
        # Get service configuration
        service_config = await self.config_manager.get_service_config(instance.service_name)
        
        # Prepare environment variables
        env = os.environ.copy()
        env.update(await self.get_service_environment(instance.service_name))
        env.update(self.flatten_config(service_config))
        
        # Start process
        service_path = Path(f"/home/activeloguser/activelog/services/{instance.service_name}")
        
        process = await asyncio.create_subprocess_shell(
            start_command,
            cwd=service_path,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid  # Create new process group
        )
        
        instance.pid = process.pid
        instance.metadata["start_command"] = start_command
    
    async def get_service_environment(self, service_name: str) -> Dict[str, str]:
        """Get environment variables for service"""
        env = {
            "ACTIVELOG_SERVICE_NAME": service_name,
            "ACTIVELOG_ENV": os.getenv("ACTIVELOG_ENV", "development")
        }
        
        # Add service-specific environment variables
        service_config = await self.config_manager.get_service_config(service_name)
        env.update(self.flatten_config(service_config, prefix="ACTIVELOG_"))
        
        return env
    
    def flatten_config(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """Flatten nested configuration to environment variables"""
        flat_config = {}
        
        def _flatten(obj: Any, key_prefix: str):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{key_prefix}{key.upper()}"
                    _flatten(value, f"{new_key}_")
            else:
                # Remove trailing underscore
                env_key = key_prefix.rstrip('_')
                flat_config[env_key] = str(obj)
        
        _flatten(config, prefix)
        return flat_config
    
    async def execute_stop_task(self, task: OrchestrationTask):
        """Execute service stop task"""
        service_name = task.service_name
        
        if service_name not in self.service_instances:
            return  # Nothing to stop
        
        instances = self.service_instances[service_name][:]  # Copy list
        
        for i, instance in enumerate(instances):
            try:
                await self.stop_service_instance(instance)
                task.progress = ((i + 1) / len(instances)) * 100
                
            except Exception as e:
                logging.error(f"Failed to stop instance {instance.instance_id}: {e}")
        
        # Remove stopped instances
        self.service_instances[service_name] = [
            inst for inst in self.service_instances[service_name]
            if inst.state != ServiceState.STOPPED
        ]
    
    async def stop_service_instance(self, instance: ServiceInstance):
        """Stop a service instance"""
        instance.state = ServiceState.STOPPING
        
        try:
            if instance.container_id:
                # Stop Docker container
                if self.docker_client:
                    container = self.docker_client.containers.get(instance.container_id)
                    container.stop(timeout=30)
                    container.remove()
            
            elif instance.pid:
                # Stop process
                try:
                    # Send SIGTERM to process group
                    os.killpg(os.getpgid(instance.pid), signal.SIGTERM)
                    
                    # Wait for graceful shutdown
                    await asyncio.sleep(10)
                    
                    # Force kill if still running
                    try:
                        process = psutil.Process(instance.pid)
                        if process.is_running():
                            os.killpg(os.getpgid(instance.pid), signal.SIGKILL)
                    except psutil.NoSuchProcess:
                        pass  # Already stopped
                        
                except (OSError, ProcessLookupError):
                    pass  # Process already stopped
            
            instance.state = ServiceState.STOPPED
            instance.stop_time = datetime.now()
            
        except Exception as e:
            instance.state = ServiceState.FAILED
            instance.metadata["stop_error"] = str(e)
            raise
    
    async def execute_scale_task(self, task: OrchestrationTask):
        """Execute service scaling task"""
        service_name = task.service_name
        target_instances = task.parameters["target_instances"]
        
        current_instances = len(self.service_instances.get(service_name, []))
        
        if target_instances > current_instances:
            # Scale up
            instances_to_add = target_instances - current_instances
            start_task = OrchestrationTask(
                task_id=f"scale_up_{service_name}_{int(time.time())}",
                task_type="start",
                service_name=service_name,
                parameters={"instances": instances_to_add}
            )
            await self.execute_start_task(start_task)
            
        elif target_instances < current_instances:
            # Scale down
            instances_to_remove = current_instances - target_instances
            instances = self.service_instances[service_name][-instances_to_remove:]
            
            for instance in instances:
                await self.stop_service_instance(instance)
            
            # Remove stopped instances
            self.service_instances[service_name] = self.service_instances[service_name][:-instances_to_remove]
        
        task.progress = 100
    
    async def execute_deploy_task(self, task: OrchestrationTask):
        """Execute service deployment task"""
        service_name = task.service_name
        version = task.parameters["version"]
        strategy = DeploymentStrategy(task.parameters["strategy"])
        
        # Create deployment record
        deployment = ServiceDeployment(
            service_name=service_name,
            version=version,
            strategy=strategy,
            target_instances=len(self.service_instances.get(service_name, [])) or 1
        )
        
        self.service_deployments[service_name] = deployment
        
        if strategy == DeploymentStrategy.ROLLING:
            await self.execute_rolling_deployment(task, deployment)
        elif strategy == DeploymentStrategy.BLUE_GREEN:
            await self.execute_blue_green_deployment(task, deployment)
        elif strategy == DeploymentStrategy.RECREATE:
            await self.execute_recreate_deployment(task, deployment)
        
        deployment.deployment_status = "completed"
        deployment.updated_at = datetime.now()
    
    async def execute_rolling_deployment(self, task: OrchestrationTask, deployment: ServiceDeployment):
        """Execute rolling deployment"""
        service_name = deployment.service_name
        current_instances = self.service_instances.get(service_name, [])
        
        # Update service definition with new version
        if service_name in self.service_definitions:
            self.service_definitions[service_name]["version"] = deployment.version
        
        # Replace instances one by one
        for i, old_instance in enumerate(current_instances):
            # Create new instance
            instance_id = f"{service_name}-{deployment.version}-{i}"
            definition = self.service_definitions[service_name]
            new_instance = await self.create_service_instance(service_name, instance_id, definition)
            
            # Wait for new instance to be healthy
            await self.wait_for_instance_health(new_instance)
            
            # Stop old instance
            await self.stop_service_instance(old_instance)
            
            # Update instance list
            current_instances[i] = new_instance
            
            task.progress = ((i + 1) / len(current_instances)) * 100
    
    async def wait_for_instance_health(self, instance: ServiceInstance, timeout_seconds: int = 120):
        """Wait for instance to become healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            # Check if instance is responding
            if instance.port > 0:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://{instance.host}:{instance.port}/health", 
                                             timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status == 200:
                                instance.health_status = ServiceStatus.HEALTHY
                                return
                except:
                    pass
            
            # Check if process is running
            if instance.pid:
                try:
                    process = psutil.Process(instance.pid)
                    if not process.is_running():
                        raise Exception("Process stopped unexpectedly")
                except psutil.NoSuchProcess:
                    raise Exception("Process not found")
            
            await asyncio.sleep(5)
        
        raise Exception(f"Instance {instance.instance_id} failed to become healthy within timeout")
    
    # Background tasks
    async def task_processor(self):
        """Process orchestration tasks"""
        while self.running:
            try:
                # Move tasks from pending to running
                while (len(self.running_tasks) < self.max_concurrent_tasks and 
                       self.pending_tasks):
                    task = self.pending_tasks.pop(0)
                    task.status = "running"
                    task.started_at = datetime.now()
                    self.running_tasks[task.task_id] = task
                    
                    # Execute task
                    asyncio.create_task(self.execute_task(task))
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logging.error(f"Task processor error: {e}")
    
    async def execute_task(self, task: OrchestrationTask):
        """Execute a single orchestration task"""
        try:
            if task.task_type == "start":
                await self.execute_start_task(task)
            elif task.task_type == "stop":
                await self.execute_stop_task(task)
            elif task.task_type == "scale":
                await self.execute_scale_task(task)
            elif task.task_type == "deploy":
                await self.execute_deploy_task(task)
            
            task.status = "completed"
            task.progress = 100
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            logging.error(f"Task {task.task_id} failed: {e}")
        
        finally:
            task.completed_at = datetime.now()
            
            # Move from running to completed
            self.running_tasks.pop(task.task_id, None)
            self.completed_tasks.append(task)
            
            # Keep only recent completed tasks
            if len(self.completed_tasks) > 1000:
                self.completed_tasks = self.completed_tasks[-1000:]
    
    async def health_checker(self):
        """Monitor service instance health"""
        while self.running:
            try:
                for service_name, instances in self.service_instances.items():
                    for instance in instances:
                        if instance.state == ServiceState.RUNNING:
                            await self.check_instance_health(instance)
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logging.error(f"Health checker error: {e}")
    
    async def check_instance_health(self, instance: ServiceInstance):
        """Check health of a single instance"""
        try:
            if instance.port > 0:
                # HTTP health check
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://{instance.host}:{instance.port}/health",
                                         timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            instance.health_status = ServiceStatus.HEALTHY
                        else:
                            instance.health_status = ServiceStatus.UNHEALTHY
            
            elif instance.pid:
                # Process health check
                try:
                    process = psutil.Process(instance.pid)
                    if process.is_running():
                        instance.health_status = ServiceStatus.HEALTHY
                        
                        # Update resource usage
                        instance.resource_usage = {
                            "cpu_percent": process.cpu_percent(),
                            "memory_mb": process.memory_info().rss / 1024 / 1024,
                            "memory_percent": process.memory_percent()
                        }
                    else:
                        instance.health_status = ServiceStatus.UNHEALTHY
                        instance.state = ServiceState.FAILED
                except psutil.NoSuchProcess:
                    instance.health_status = ServiceStatus.UNHEALTHY
                    instance.state = ServiceState.FAILED
            
            # Handle unhealthy instances
            if instance.health_status == ServiceStatus.UNHEALTHY:
                await self.handle_unhealthy_instance(instance)
                
        except Exception as e:
            instance.health_status = ServiceStatus.UNHEALTHY
            logging.error(f"Health check failed for {instance.instance_id}: {e}")
    
    async def handle_unhealthy_instance(self, instance: ServiceInstance):
        """Handle unhealthy service instance"""
        # Attempt restart if not too many recent restarts
        max_restarts = 3
        restart_window_minutes = 30
        
        if instance.restart_count < max_restarts:
            # Check if we're within restart window
            if (instance.last_restart and 
                (datetime.now() - instance.last_restart).seconds < restart_window_minutes * 60):
                return  # Too many recent restarts
            
            # Restart instance
            logging.warning(f"Restarting unhealthy instance {instance.instance_id}")
            
            try:
                # Stop instance
                await self.stop_service_instance(instance)
                
                # Start new instance
                definition = self.service_definitions[instance.service_name]
                new_instance = await self.create_service_instance(
                    instance.service_name, 
                    f"{instance.service_name}-restart-{int(time.time())}", 
                    definition
                )
                
                # Update instance list
                instances = self.service_instances[instance.service_name]
                instance_index = instances.index(instance)
                instances[instance_index] = new_instance
                
                new_instance.restart_count = instance.restart_count + 1
                new_instance.last_restart = datetime.now()
                
            except Exception as e:
                logging.error(f"Failed to restart instance {instance.instance_id}: {e}")
    
    async def auto_scaler(self):
        """Automatic service scaling based on metrics"""
        while self.running:
            try:
                for service_name, scaling_rule in self.scaling_rules.items():
                    if (scaling_rule.enabled and 
                        scaling_rule.policy != ScalingPolicy.MANUAL):
                        await self.evaluate_scaling_rule(service_name, scaling_rule)
                
                await asyncio.sleep(self.scaling_check_interval)
                
            except Exception as e:
                logging.error(f"Auto scaler error: {e}")
    
    async def evaluate_scaling_rule(self, service_name: str, scaling_rule: ScalingRule):
        """Evaluate and apply scaling rule"""
        instances = self.service_instances.get(service_name, [])
        current_count = len(instances)
        
        if not instances:
            return
        
        # Calculate average metrics
        total_cpu = sum(inst.resource_usage.get("cpu_percent", 0) for inst in instances)
        total_memory = sum(inst.resource_usage.get("memory_percent", 0) for inst in instances)
        
        avg_cpu = total_cpu / current_count
        avg_memory = total_memory / current_count
        
        should_scale_up = False
        should_scale_down = False
        
        if scaling_rule.policy == ScalingPolicy.CPU_BASED:
            if avg_cpu > scaling_rule.scale_up_threshold:
                should_scale_up = True
            elif avg_cpu < scaling_rule.scale_down_threshold:
                should_scale_down = True
        
        elif scaling_rule.policy == ScalingPolicy.MEMORY_BASED:
            if avg_memory > scaling_rule.scale_up_threshold:
                should_scale_up = True
            elif avg_memory < scaling_rule.scale_down_threshold:
                should_scale_down = True
        
        # Apply scaling decision
        if should_scale_up and current_count < scaling_rule.max_instances:
            new_count = min(current_count + 1, scaling_rule.max_instances)
            await self.scale_service(service_name, new_count)
            logging.info(f"Scaled up {service_name} to {new_count} instances (CPU: {avg_cpu:.1f}%, Memory: {avg_memory:.1f}%)")
        
        elif should_scale_down and current_count > scaling_rule.min_instances:
            new_count = max(current_count - 1, scaling_rule.min_instances)
            await self.scale_service(service_name, new_count)
            logging.info(f"Scaled down {service_name} to {new_count} instances (CPU: {avg_cpu:.1f}%, Memory: {avg_memory:.1f}%)")
    
    async def resource_monitor(self):
        """Monitor overall resource usage"""
        while self.running:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Log resource usage
                logging.info(f"System resources - CPU: {cpu_percent:.1f}%, "
                           f"Memory: {memory.percent:.1f}%, "
                           f"Disk: {disk.percent:.1f}%")
                
                # Check for resource exhaustion
                if memory.percent > 90:
                    logging.warning("High memory usage detected")
                    # Could trigger aggressive scaling down
                
                if disk.percent > 90:
                    logging.warning("High disk usage detected")
                    # Could trigger cleanup tasks
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"Resource monitor error: {e}")
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get orchestration status"""
        total_instances = sum(len(instances) for instances in self.service_instances.values())
        running_instances = sum(
            len([inst for inst in instances if inst.state == ServiceState.RUNNING])
            for instances in self.service_instances.values()
        )
        
        return {
            "services_managed": len(self.service_instances),
            "total_instances": total_instances,
            "running_instances": running_instances,
            "pending_tasks": len(self.pending_tasks),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "deployments": len(self.service_deployments),
            "scaling_rules": len(self.scaling_rules),
            "active_scaling_rules": len([r for r in self.scaling_rules.values() if r.enabled])
        }
    
    def stop(self):
        """Stop the orchestrator"""
        self.running = False

# Example usage
async def main():
    from service_discovery import ServiceDiscovery
    from health_monitor import HealthMonitor
    from configuration_manager import ConfigurationManager
    
    discovery = ServiceDiscovery()
    health_monitor = HealthMonitor(discovery)
    config_manager = ConfigurationManager(discovery)
    
    orchestrator = ServiceOrchestrator(discovery, health_monitor, config_manager)
    await orchestrator.initialize()
    
    # Example operations
    task_id = await orchestrator.start_service("user-service", instances=2)
    print(f"Started service with task ID: {task_id}")
    
    status = orchestrator.get_orchestration_status()
    print(f"Orchestration status: {json.dumps(status, indent=2)}")
    
    # Wait for tasks to complete
    await asyncio.sleep(60)
    
    orchestrator.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())