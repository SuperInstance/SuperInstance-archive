import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import consul
import aiohttp
from collections import defaultdict, deque


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STARTING = "starting"
    STOPPING = "stopping"
    MAINTENANCE = "maintenance"


class ServiceType(Enum):
    WEB = "web"
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    WORKER = "worker"
    GATEWAY = "gateway"
    PROXY = "proxy"
    MONITOR = "monitor"


class OrchestrationAction(Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"
    MIGRATE = "migrate"
    HEALTH_CHECK = "health_check"
    UPDATE_CONFIG = "update_config"


@dataclass
class ServiceInstance:
    instance_id: str
    service_name: str
    host: str
    port: int
    status: ServiceStatus
    version: str = "1.0.0"
    service_type: ServiceType = ServiceType.API
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_check_url: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    startup_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.health_check_url:
            self.health_check_url = f"http://{self.host}:{self.port}/health"


@dataclass
class OrchestrationTask:
    task_id: str
    action: OrchestrationAction
    target_service: str
    target_instances: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10, 10 being highest
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ServiceDependency:
    service_name: str
    depends_on: str
    dependency_type: str = "hard"  # hard, soft, optional
    startup_delay: int = 0  # seconds to wait after dependency is ready


class ServiceRegistry:
    """Registry for managing service instances and their metadata"""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.services: Dict[str, Dict[str, ServiceInstance]] = defaultdict(dict)
        self.dependencies: Dict[str, List[ServiceDependency]] = defaultdict(list)
        self.service_groups: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)
        self.lock = threading.RLock()
    
    def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance"""
        try:
            with self.lock:
                self.services[instance.service_name][instance.instance_id] = instance
            
            # Register with Consul
            self.consul.agent.service.register(
                name=instance.service_name,
                service_id=instance.instance_id,
                address=instance.host,
                port=instance.port,
                tags=instance.tags + [instance.service_type.value],
                meta={
                    'version': instance.version,
                    'status': instance.status.value,
                    'startup_time': instance.startup_time.isoformat() if instance.startup_time else None,
                    **{k: str(v) for k, v in instance.metadata.items()}
                },
                check={
                    "HTTP": instance.health_check_url,
                    "Interval": "30s",
                    "Timeout": "10s",
                    "DeregisterCriticalServiceAfter": "90s"
                }
            )
            
            self.logger.info(f"Registered service instance: {instance.service_name}:{instance.instance_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register service {instance.service_name}: {e}")
            return False
    
    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance"""
        try:
            with self.lock:
                if service_name in self.services and instance_id in self.services[service_name]:
                    del self.services[service_name][instance_id]
                    
                    if not self.services[service_name]:
                        del self.services[service_name]
            
            # Deregister from Consul
            self.consul.agent.service.deregister(instance_id)
            
            self.logger.info(f"Deregistered service instance: {service_name}:{instance_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deregister service {service_name}: {e}")
            return False
    
    def get_service_instances(self, service_name: str, 
                            status_filter: List[ServiceStatus] = None) -> List[ServiceInstance]:
        """Get instances of a service"""
        with self.lock:
            if service_name not in self.services:
                return []
            
            instances = list(self.services[service_name].values())
            
            if status_filter:
                instances = [inst for inst in instances if inst.status in status_filter]
            
            return instances
    
    def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services"""
        with self.lock:
            return {
                service_name: list(instances.values())
                for service_name, instances in self.services.items()
            }
    
    def add_dependency(self, service_name: str, dependency: ServiceDependency):
        """Add service dependency"""
        with self.lock:
            self.dependencies[service_name].append(dependency)
            self.logger.info(f"Added dependency: {service_name} depends on {dependency.depends_on}")
    
    def get_dependencies(self, service_name: str) -> List[ServiceDependency]:
        """Get service dependencies"""
        with self.lock:
            return self.dependencies.get(service_name, [])
    
    def get_dependents(self, service_name: str) -> List[str]:
        """Get services that depend on this service"""
        dependents = []
        with self.lock:
            for service, deps in self.dependencies.items():
                for dep in deps:
                    if dep.depends_on == service_name:
                        dependents.append(service)
        return dependents
    
    def create_service_group(self, group_name: str, services: List[str]):
        """Create a logical grouping of services"""
        with self.lock:
            self.service_groups[group_name] = services
            self.logger.info(f"Created service group '{group_name}' with services: {services}")
    
    def get_service_group(self, group_name: str) -> List[str]:
        """Get services in a group"""
        with self.lock:
            return self.service_groups.get(group_name, [])


class HealthChecker:
    """Performs health checks on service instances"""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.logger = logging.getLogger(__name__)
        self.check_interval = 30  # seconds
        self.running = False
        self.check_thread = None
    
    def start(self):
        """Start health checking"""
        if not self.running:
            self.running = True
            self.check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self.check_thread.start()
            self.logger.info("Health checker started")
    
    def stop(self):
        """Stop health checking"""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        self.logger.info("Health checker stopped")
    
    def _health_check_loop(self):
        """Main health check loop"""
        while self.running:
            try:
                self._perform_health_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                time.sleep(self.check_interval)
    
    def _perform_health_checks(self):
        """Perform health checks on all services"""
        all_services = self.registry.get_all_services()
        
        for service_name, instances in all_services.items():
            for instance in instances:
                asyncio.run(self._check_instance_health(instance))
    
    async def _check_instance_health(self, instance: ServiceInstance):
        """Check health of a single instance"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(instance.health_check_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Update instance status
                        if instance.status == ServiceStatus.UNHEALTHY:
                            instance.status = ServiceStatus.HEALTHY
                            self.logger.info(f"Service {instance.service_name}:{instance.instance_id} recovered")
                        
                        instance.last_health_check = datetime.now()
                        
                        # Update resource usage if provided
                        if isinstance(data, dict) and 'resources' in data:
                            instance.resource_usage.update(data['resources'])
                            
                    else:
                        self._mark_unhealthy(instance, f"HTTP {response.status}")
                        
        except Exception as e:
            self._mark_unhealthy(instance, str(e))
    
    def _mark_unhealthy(self, instance: ServiceInstance, reason: str):
        """Mark instance as unhealthy"""
        if instance.status != ServiceStatus.UNHEALTHY:
            instance.status = ServiceStatus.UNHEALTHY
            instance.last_health_check = datetime.now()
            self.logger.warning(f"Service {instance.service_name}:{instance.instance_id} unhealthy: {reason}")


class TaskQueue:
    """Priority queue for orchestration tasks"""
    
    def __init__(self):
        self.tasks: List[OrchestrationTask] = []
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
    
    def enqueue(self, task: OrchestrationTask):
        """Add task to queue"""
        with self.condition:
            self.tasks.append(task)
            # Sort by priority (higher priority first), then by creation time
            self.tasks.sort(key=lambda t: (-t.priority, t.created_at))
            self.condition.notify()
    
    def dequeue(self, timeout: float = None) -> Optional[OrchestrationTask]:
        """Get next task from queue"""
        with self.condition:
            while not self.tasks:
                if not self.condition.wait(timeout):
                    return None
            
            # Find first ready task
            now = datetime.now()
            for i, task in enumerate(self.tasks):
                if task.scheduled_at is None or task.scheduled_at <= now:
                    return self.tasks.pop(i)
            
            # No ready tasks
            return None
    
    def peek(self) -> Optional[OrchestrationTask]:
        """Peek at next task without removing it"""
        with self.lock:
            return self.tasks[0] if self.tasks else None
    
    def size(self) -> int:
        """Get queue size"""
        with self.lock:
            return len(self.tasks)
    
    def get_pending_tasks(self, service_name: str = None) -> List[OrchestrationTask]:
        """Get pending tasks for a service"""
        with self.lock:
            if service_name:
                return [task for task in self.tasks if task.target_service == service_name]
            return self.tasks.copy()


class ServiceOrchestrator:
    """Master service orchestrator that coordinates all services"""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.registry = ServiceRegistry(consul_host, consul_port)
        self.health_checker = HealthChecker(self.registry)
        self.task_queue = TaskQueue()
        self.logger = logging.getLogger(__name__)
        
        # State
        self.running = False
        self.worker_threads: List[threading.Thread] = []
        self.num_workers = 3
        
        # Callbacks
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Statistics
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'services_managed': 0,
            'uptime_start': None
        }
    
    def start(self):
        """Start the orchestrator"""
        if self.running:
            return
        
        self.running = True
        self.stats['uptime_start'] = datetime.now()
        
        # Start health checker
        self.health_checker.start()
        
        # Start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker_loop, name=f"orchestrator-worker-{i}", daemon=True)
            worker.start()
            self.worker_threads.append(worker)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        self.worker_threads.append(monitor_thread)
        
        self.logger.info(f"Service orchestrator started with {self.num_workers} workers")
    
    def stop(self):
        """Stop the orchestrator"""
        if not self.running:
            return
        
        self.running = False
        
        # Stop health checker
        self.health_checker.stop()
        
        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=5)
        
        self.worker_threads.clear()
        self.logger.info("Service orchestrator stopped")
    
    def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service with the orchestrator"""
        success = self.registry.register_service(instance)
        if success:
            self.stats['services_managed'] = len(self.registry.get_all_services())
            self._emit_event('service_registered', {'service': instance.service_name, 'instance': instance.instance_id})
        return success
    
    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service"""
        success = self.registry.deregister_service(service_name, instance_id)
        if success:
            self.stats['services_managed'] = len(self.registry.get_all_services())
            self._emit_event('service_deregistered', {'service': service_name, 'instance': instance_id})
        return success
    
    def execute_action(self, action: OrchestrationAction, service_name: str,
                      instances: List[str] = None, parameters: Dict[str, Any] = None,
                      priority: int = 5, scheduled_at: datetime = None) -> str:
        """Execute an orchestration action"""
        task = OrchestrationTask(
            task_id=str(uuid.uuid4()),
            action=action,
            target_service=service_name,
            target_instances=instances or [],
            parameters=parameters or {},
            priority=priority,
            scheduled_at=scheduled_at
        )
        
        self.task_queue.enqueue(task)
        self.logger.info(f"Queued task: {action.value} on {service_name} (ID: {task.task_id})")
        
        return task.task_id
    
    def start_service(self, service_name: str, instances: List[str] = None, 
                     parameters: Dict[str, Any] = None) -> str:
        """Start service instances"""
        return self.execute_action(OrchestrationAction.START, service_name, instances, parameters, priority=8)
    
    def stop_service(self, service_name: str, instances: List[str] = None,
                    graceful: bool = True) -> str:
        """Stop service instances"""
        params = parameters or {}
        params['graceful'] = graceful
        return self.execute_action(OrchestrationAction.STOP, service_name, instances, params, priority=9)
    
    def restart_service(self, service_name: str, instances: List[str] = None) -> str:
        """Restart service instances"""
        return self.execute_action(OrchestrationAction.RESTART, service_name, instances, priority=7)
    
    def scale_service(self, service_name: str, target_instances: int, 
                     scale_up: bool = True) -> str:
        """Scale service up or down"""
        action = OrchestrationAction.SCALE_UP if scale_up else OrchestrationAction.SCALE_DOWN
        parameters = {'target_instances': target_instances}
        return self.execute_action(action, service_name, parameters=parameters, priority=6)
    
    def deploy_service(self, service_name: str, version: str, 
                      deployment_config: Dict[str, Any] = None) -> str:
        """Deploy a new version of a service"""
        parameters = {'version': version, 'config': deployment_config or {}}
        return self.execute_action(OrchestrationAction.DEPLOY, service_name, parameters=parameters, priority=7)
    
    def rollback_service(self, service_name: str, target_version: str) -> str:
        """Rollback service to previous version"""
        parameters = {'target_version': target_version}
        return self.execute_action(OrchestrationAction.ROLLBACK, service_name, parameters=parameters, priority=8)
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get comprehensive service status"""
        instances = self.registry.get_service_instances(service_name)
        dependencies = self.registry.get_dependencies(service_name)
        dependents = self.registry.get_dependents(service_name)
        
        status_counts = defaultdict(int)
        total_requests = 0
        avg_response_time = 0
        
        for instance in instances:
            status_counts[instance.status.value] += 1
            if 'requests' in instance.resource_usage:
                total_requests += instance.resource_usage['requests']
            if 'response_time' in instance.resource_usage:
                avg_response_time += instance.resource_usage['response_time']
        
        if instances:
            avg_response_time /= len(instances)
        
        return {
            'service_name': service_name,
            'instance_count': len(instances),
            'status_distribution': dict(status_counts),
            'dependencies': [dep.depends_on for dep in dependencies],
            'dependents': dependents,
            'metrics': {
                'total_requests': total_requests,
                'avg_response_time': avg_response_time
            },
            'instances': [
                {
                    'id': inst.instance_id,
                    'host': f"{inst.host}:{inst.port}",
                    'status': inst.status.value,
                    'version': inst.version,
                    'uptime': (datetime.now() - inst.startup_time).total_seconds() if inst.startup_time else 0
                }
                for inst in instances
            ]
        }
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get orchestrator status and statistics"""
        uptime = (datetime.now() - self.stats['uptime_start']).total_seconds() if self.stats['uptime_start'] else 0
        
        return {
            'running': self.running,
            'uptime_seconds': uptime,
            'worker_threads': len(self.worker_threads),
            'queue_size': self.task_queue.size(),
            'services_managed': self.stats['services_managed'],
            'tasks_completed': self.stats['tasks_completed'],
            'tasks_failed': self.stats['tasks_failed'],
            'success_rate': (self.stats['tasks_completed'] / 
                           (self.stats['tasks_completed'] + self.stats['tasks_failed']) * 100
                           if (self.stats['tasks_completed'] + self.stats['tasks_failed']) > 0 else 0)
        }
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler"""
        self.event_handlers[event_type].append(handler)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to handlers"""
        for handler in self.event_handlers[event_type]:
            try:
                handler(event_type, data)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_type}: {e}")
    
    def _worker_loop(self):
        """Worker thread loop for processing tasks"""
        while self.running:
            try:
                task = self.task_queue.dequeue(timeout=1.0)
                if task:
                    self._execute_task(task)
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
    
    def _execute_task(self, task: OrchestrationTask):
        """Execute an orchestration task"""
        task.started_at = datetime.now()
        task.status = "running"
        
        try:
            self.logger.info(f"Executing task: {task.action.value} on {task.target_service}")
            
            if task.action == OrchestrationAction.START:
                result = self._start_service_instances(task)
            elif task.action == OrchestrationAction.STOP:
                result = self._stop_service_instances(task)
            elif task.action == OrchestrationAction.RESTART:
                result = self._restart_service_instances(task)
            elif task.action == OrchestrationAction.SCALE_UP:
                result = self._scale_service_up(task)
            elif task.action == OrchestrationAction.SCALE_DOWN:
                result = self._scale_service_down(task)
            elif task.action == OrchestrationAction.DEPLOY:
                result = self._deploy_service(task)
            elif task.action == OrchestrationAction.ROLLBACK:
                result = self._rollback_service(task)
            elif task.action == OrchestrationAction.HEALTH_CHECK:
                result = self._perform_service_health_check(task)
            else:
                result = {'success': False, 'message': f'Unsupported action: {task.action.value}'}
            
            task.completed_at = datetime.now()
            task.status = "completed" if result.get('success', False) else "failed"
            task.result = result
            
            if task.status == "completed":
                self.stats['tasks_completed'] += 1
                self._emit_event('task_completed', {'task_id': task.task_id, 'action': task.action.value})
            else:
                self.stats['tasks_failed'] += 1
                self._emit_event('task_failed', {'task_id': task.task_id, 'action': task.action.value, 'error': result.get('message')})
            
        except Exception as e:
            task.completed_at = datetime.now()
            task.status = "failed"
            task.error = str(e)
            self.stats['tasks_failed'] += 1
            self.logger.error(f"Task execution failed: {e}")
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = "pending"
                task.started_at = None
                task.completed_at = None
                task.scheduled_at = datetime.now() + timedelta(seconds=30)  # Retry in 30 seconds
                self.task_queue.enqueue(task)
                self.logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
    
    def _start_service_instances(self, task: OrchestrationTask) -> Dict[str, Any]:
        """Start service instances"""
        # This would integrate with container orchestration (Docker, Kubernetes, etc.)
        # For now, we'll simulate the operation
        instances = self.registry.get_service_instances(task.target_service)
        
        if task.target_instances:
            instances = [inst for inst in instances if inst.instance_id in task.target_instances]
        
        started = []
        for instance in instances:
            if instance.status in [ServiceStatus.UNKNOWN, ServiceStatus.UNHEALTHY]:
                instance.status = ServiceStatus.STARTING
                instance.startup_time = datetime.now()
                # Simulate startup delay
                time.sleep(1)
                instance.status = ServiceStatus.HEALTHY
                started.append(instance.instance_id)
        
        return {
            'success': True,
            'message': f'Started {len(started)} instances',
            'started_instances': started
        }
    
    def _stop_service_instances(self, task: OrchestrationTask) -> Dict[str, Any]:
        """Stop service instances"""
        instances = self.registry.get_service_instances(task.target_service)
        graceful = task.parameters.get('graceful', True)
        
        if task.target_instances:
            instances = [inst for inst in instances if inst.instance_id in task.target_instances]
        
        stopped = []
        for instance in instances:
            if instance.status != ServiceStatus.STOPPING:
                instance.status = ServiceStatus.STOPPING
                # Simulate graceful shutdown
                if graceful:
                    time.sleep(2)
                instance.status = ServiceStatus.UNKNOWN
                stopped.append(instance.instance_id)
        
        return {
            'success': True,
            'message': f'Stopped {len(stopped)} instances',
            'stopped_instances': stopped
        }
    
    def _restart_service_instances(self, task: OrchestrationTask) -> Dict[str, Any]:
        """Restart service instances"""
        # Stop then start
        stop_result = self._stop_service_instances(task)
        if stop_result.get('success'):
            time.sleep(2)  # Brief pause between stop and start
            start_result = self._start_service_instances(task)
            return {
                'success': start_result.get('success', False),
                'message': f"Restarted service instances",
                'details': {'stop': stop_result, 'start': start_result}
            }
        else:
            return {'success': False, 'message': 'Failed to stop instances for restart'}
    
    def _scale_service_up(self, task: OrchestrationTask) -> Dict[str, Any]:
        """Scale service up"""
        target_count = task.parameters.get('target_instances', 1)
        current_instances = self.registry.get_service_instances(task.target_service)
        current_count = len([inst for inst in current_instances if inst.status == ServiceStatus.HEALTHY])
        
        if target_count <= current_count:
            return {'success': True, 'message': 'Already at or above target instance count'}
        
        # This would typically create new container instances
        new_instances = target_count - current_count
        return {
            'success': True,
            'message': f'Would scale up by {new_instances} instances',
            'new_instances': new_instances
        }
    
    def _scale_service_down(self, task: OrchestrationTask) -> Dict[str, Any]:
        """Scale service down"""
        target_count = task.parameters.get('target_instances', 1)
        current_instances = self.registry.get_service_instances(task.target_service)
        healthy_instances = [inst for inst in current_instances if inst.status == ServiceStatus.HEALTHY]
        
        if target_count >= len(healthy_instances):
            return {'success': True, 'message': 'Already at or below target instance count'}
        
        # Stop excess instances
        instances_to_stop = healthy_instances[target_count:]
        stopped = []
        
        for instance in instances_to_stop:
            instance.status = ServiceStatus.STOPPING
            stopped.append(instance.instance_id)
        
        return {
            'success': True,
            'message': f'Scaled down by {len(stopped)} instances',
            'stopped_instances': stopped
        }
    
    def _deploy_service(self, task: OrchestrationTask) -> Dict[str, Any]:
        """Deploy new service version"""
        version = task.parameters.get('version')
        config = task.parameters.get('config', {})
        
        # This would typically involve container image deployment
        instances = self.registry.get_service_instances(task.target_service)
        updated = []
        
        for instance in instances:
            instance.version = version
            instance.metadata.update(config)
            updated.append(instance.instance_id)
        
        return {
            'success': True,
            'message': f'Deployed version {version} to {len(updated)} instances',
            'updated_instances': updated
        }
    
    def _rollback_service(self, task: OrchestrationTask) -> Dict[str, Any]:
        """Rollback service to previous version"""
        target_version = task.parameters.get('target_version')
        
        instances = self.registry.get_service_instances(task.target_service)
        rolled_back = []
        
        for instance in instances:
            instance.version = target_version
            rolled_back.append(instance.instance_id)
        
        return {
            'success': True,
            'message': f'Rolled back {len(rolled_back)} instances to version {target_version}',
            'rolled_back_instances': rolled_back
        }
    
    def _perform_service_health_check(self, task: OrchestrationTask) -> Dict[str, Any]:
        """Perform manual health check"""
        instances = self.registry.get_service_instances(task.target_service)
        
        if task.target_instances:
            instances = [inst for inst in instances if inst.instance_id in task.target_instances]
        
        health_results = {}
        for instance in instances:
            asyncio.run(self.health_checker._check_instance_health(instance))
            health_results[instance.instance_id] = instance.status.value
        
        return {
            'success': True,
            'message': f'Health check completed for {len(instances)} instances',
            'health_results': health_results
        }
    
    def _monitoring_loop(self):
        """Background monitoring and maintenance"""
        while self.running:
            try:
                # Check for stuck tasks
                now = datetime.now()
                all_services = self.registry.get_all_services()
                
                # Auto-recovery for unhealthy services
                for service_name, instances in all_services.items():
                    unhealthy_instances = [inst for inst in instances if inst.status == ServiceStatus.UNHEALTHY]
                    
                    for instance in unhealthy_instances:
                        if (instance.last_health_check and 
                            now - instance.last_health_check > timedelta(minutes=5)):
                            
                            # Auto-restart unhealthy instances
                            self.logger.warning(f"Auto-restarting unhealthy instance: {instance.instance_id}")
                            self.execute_action(
                                OrchestrationAction.RESTART,
                                service_name,
                                [instance.instance_id],
                                priority=6
                            )
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)


# Usage example
if __name__ == "__main__":
    import signal
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    def signal_handler(sig, frame):
        print("Shutting down orchestrator...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and start orchestrator
    orchestrator = ServiceOrchestrator()
    orchestrator.start()
    
    # Register some example services
    api_service = ServiceInstance(
        instance_id="api-1",
        service_name="api-service", 
        host="localhost",
        port=8080,
        status=ServiceStatus.HEALTHY,
        service_type=ServiceType.API,
        tags=["api", "v1"]
    )
    
    orchestrator.register_service(api_service)
    
    # Add event handlers
    def on_service_registered(event_type, data):
        print(f"Service registered: {data}")
    
    orchestrator.add_event_handler('service_registered', on_service_registered)
    
    # Example orchestration actions
    print("Testing orchestration actions...")
    
    task_id = orchestrator.start_service("api-service")
    print(f"Started service with task ID: {task_id}")
    
    time.sleep(2)
    
    status = orchestrator.get_service_status("api-service")
    print(f"Service status: {json.dumps(status, indent=2)}")
    
    orchestrator_status = orchestrator.get_orchestrator_status()
    print(f"Orchestrator status: {json.dumps(orchestrator_status, indent=2)}")
    
    # Keep running
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        pass