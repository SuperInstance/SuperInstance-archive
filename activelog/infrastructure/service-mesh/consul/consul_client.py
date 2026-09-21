import consul
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import socket
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    WARNING = "warning"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    service_name: str
    instance_id: str
    address: str
    port: int
    tags: List[str]
    metadata: Dict[str, Any]
    status: ServiceStatus
    version: str
    registered_at: datetime
    last_heartbeat: datetime
    health_check_url: Optional[str] = None
    weight: int = 100


@dataclass
class HealthCheck:
    check_id: str
    service_name: str
    check_type: str  # http, tcp, script, ttl
    target: str  # URL, address:port, or script
    interval: int  # seconds
    timeout: int  # seconds
    deregister_critical_after: int  # seconds
    notes: str = ""


class ConsulServiceDiscovery:
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500,
                 datacenter: str = "dc1", token: Optional[str] = None):
        self.consul = consul.Consul(
            host=consul_host,
            port=consul_port,
            dc=datacenter,
            token=token
        )
        self.logger = logging.getLogger(__name__)
        self.services_cache = {}
        self.health_cache = {}
        self.watch_threads = {}
        self.cache_lock = threading.RLock()
        self.running = False
        
        # Initialize consul connection
        self._init_consul()
    
    def _init_consul(self):
        """Initialize consul connection and verify it's working"""
        try:
            # Test connection
            self.consul.agent.self()
            self.logger.info("Successfully connected to Consul")
        except Exception as e:
            self.logger.error(f"Failed to connect to Consul: {e}")
            raise
    
    def register_service(self, service: ServiceInstance, health_checks: List[HealthCheck] = None) -> bool:
        """Register a service with Consul"""
        try:
            # Prepare service registration
            service_def = {
                "Name": service.service_name,
                "ID": service.instance_id,
                "Address": service.address,
                "Port": service.port,
                "Tags": service.tags,
                "Meta": {
                    **service.metadata,
                    "version": service.version,
                    "registered_at": service.registered_at.isoformat(),
                    "weight": str(service.weight)
                }
            }
            
            # Add health checks
            if health_checks:
                service_def["Checks"] = []
                for check in health_checks:
                    check_def = {
                        "CheckID": check.check_id,
                        "Name": f"{service.service_name}-{check.check_type}",
                        "Interval": f"{check.interval}s",
                        "Timeout": f"{check.timeout}s",
                        "DeregisterCriticalServiceAfter": f"{check.deregister_critical_after}s",
                        "Notes": check.notes
                    }
                    
                    if check.check_type == "http":
                        check_def["HTTP"] = check.target
                    elif check.check_type == "tcp":
                        check_def["TCP"] = check.target
                    elif check.check_type == "script":
                        check_def["Script"] = check.target
                    elif check.check_type == "ttl":
                        check_def["TTL"] = f"{check.interval}s"
                    
                    service_def["Checks"].append(check_def)
            
            # Register service
            self.consul.agent.service.register(
                name=service.service_name,
                service_id=service.instance_id,
                address=service.address,
                port=service.port,
                tags=service.tags,
                meta=service_def["Meta"],
                check=service_def.get("Checks")
            )
            
            self.logger.info(f"Successfully registered service {service.service_name}:{service.instance_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register service {service.service_name}: {e}")
            return False
    
    def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from Consul"""
        try:
            self.consul.agent.service.deregister(service_id)
            self.logger.info(f"Successfully deregistered service {service_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    def discover_services(self, service_name: str = None, 
                         tags: List[str] = None,
                         healthy_only: bool = True) -> List[ServiceInstance]:
        """Discover services from Consul"""
        try:
            if service_name:
                # Get specific service
                services = self.consul.health.service(
                    service_name, 
                    passing=healthy_only,
                    tag=tags[0] if tags else None
                )
            else:
                # Get all services
                services = []
                all_services = self.consul.agent.services()
                for service_id, service_info in all_services.items():
                    if tags and not any(tag in service_info.get('Tags', []) for tag in tags):
                        continue
                    
                    # Get health info
                    health_info = self.consul.health.service(service_info['Service'])
                    services.extend(health_info[1])
            
            instances = []
            for service_entry in services[1] if service_name else services:
                service_info = service_entry.get('Service', {})
                health_info = service_entry.get('Checks', [])
                
                # Determine health status
                status = ServiceStatus.HEALTHY
                for check in health_info:
                    check_status = check.get('Status', 'unknown')
                    if check_status == 'critical':
                        status = ServiceStatus.CRITICAL
                        break
                    elif check_status == 'warning':
                        status = ServiceStatus.WARNING
                
                meta = service_info.get('Meta', {})
                instance = ServiceInstance(
                    service_name=service_info.get('Service', ''),
                    instance_id=service_info.get('ID', ''),
                    address=service_info.get('Address', ''),
                    port=service_info.get('Port', 0),
                    tags=service_info.get('Tags', []),
                    metadata=meta,
                    status=status,
                    version=meta.get('version', '1.0'),
                    registered_at=datetime.fromisoformat(meta.get('registered_at', datetime.now().isoformat())),
                    last_heartbeat=datetime.now(),
                    weight=int(meta.get('weight', 100))
                )
                instances.append(instance)
            
            return instances
            
        except Exception as e:
            self.logger.error(f"Failed to discover services: {e}")
            return []
    
    def get_service_health(self, service_name: str) -> Dict[str, ServiceStatus]:
        """Get health status for all instances of a service"""
        try:
            health_data = self.consul.health.service(service_name)
            health_map = {}
            
            for entry in health_data[1]:
                service_id = entry['Service']['ID']
                checks = entry.get('Checks', [])
                
                status = ServiceStatus.HEALTHY
                for check in checks:
                    check_status = check.get('Status', 'unknown')
                    if check_status == 'critical':
                        status = ServiceStatus.CRITICAL
                        break
                    elif check_status == 'warning':
                        status = ServiceStatus.WARNING
                
                health_map[service_id] = status
            
            return health_map
            
        except Exception as e:
            self.logger.error(f"Failed to get service health for {service_name}: {e}")
            return {}
    
    def watch_service(self, service_name: str, callback: Callable[[List[ServiceInstance]], None],
                     interval: int = 5) -> str:
        """Watch a service for changes"""
        watch_id = f"{service_name}_{int(time.time())}"
        
        def watch_thread():
            last_services = []
            while self.running and watch_id in self.watch_threads:
                try:
                    current_services = self.discover_services(service_name)
                    
                    # Check if services changed
                    if self._services_changed(last_services, current_services):
                        callback(current_services)
                        last_services = current_services.copy()
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in watch thread for {service_name}: {e}")
                    time.sleep(interval)
        
        thread = threading.Thread(target=watch_thread, daemon=True)
        self.watch_threads[watch_id] = thread
        thread.start()
        
        return watch_id
    
    def _services_changed(self, old_services: List[ServiceInstance], 
                         new_services: List[ServiceInstance]) -> bool:
        """Check if service list has changed"""
        if len(old_services) != len(new_services):
            return True
        
        old_ids = {s.instance_id for s in old_services}
        new_ids = {s.instance_id for s in new_services}
        
        return old_ids != new_ids
    
    def stop_watch(self, watch_id: str) -> bool:
        """Stop watching a service"""
        if watch_id in self.watch_threads:
            del self.watch_threads[watch_id]
            return True
        return False
    
    def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services grouped by name"""
        try:
            services = self.consul.catalog.services()[1]
            all_services = {}
            
            for service_name, tags in services.items():
                if service_name == "consul":  # Skip consul itself
                    continue
                
                instances = self.discover_services(service_name, healthy_only=False)
                all_services[service_name] = instances
            
            return all_services
            
        except Exception as e:
            self.logger.error(f"Failed to get all services: {e}")
            return {}
    
    def update_service_metadata(self, service_id: str, metadata: Dict[str, Any]) -> bool:
        """Update service metadata"""
        try:
            # Get current service info
            services = self.consul.agent.services()
            if service_id not in services:
                return False
            
            service_info = services[service_id]
            
            # Update metadata
            current_meta = service_info.get('Meta', {})
            current_meta.update(metadata)
            
            # Re-register service with updated metadata
            self.consul.agent.service.register(
                name=service_info['Service'],
                service_id=service_id,
                address=service_info['Address'],
                port=service_info['Port'],
                tags=service_info['Tags'],
                meta=current_meta
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update service metadata for {service_id}: {e}")
            return False
    
    def perform_health_check(self, service_instance: ServiceInstance, 
                           check: HealthCheck) -> ServiceStatus:
        """Perform manual health check on a service"""
        try:
            if check.check_type == "http":
                response = requests.get(check.target, timeout=check.timeout)
                if response.status_code == 200:
                    return ServiceStatus.HEALTHY
                elif 200 <= response.status_code < 300:
                    return ServiceStatus.WARNING
                else:
                    return ServiceStatus.UNHEALTHY
                    
            elif check.check_type == "tcp":
                host, port = check.target.split(":")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(check.timeout)
                result = sock.connect_ex((host, int(port)))
                sock.close()
                
                if result == 0:
                    return ServiceStatus.HEALTHY
                else:
                    return ServiceStatus.UNHEALTHY
                    
            else:
                return ServiceStatus.UNKNOWN
                
        except Exception as e:
            self.logger.error(f"Health check failed for {service_instance.service_name}: {e}")
            return ServiceStatus.CRITICAL
    
    def get_service_dependencies(self, service_name: str) -> Dict[str, List[str]]:
        """Get service dependencies from metadata"""
        try:
            instances = self.discover_services(service_name, healthy_only=False)
            dependencies = {}
            
            for instance in instances:
                deps = instance.metadata.get("dependencies", "")
                if deps:
                    dep_list = [d.strip() for d in deps.split(",") if d.strip()]
                    dependencies[instance.instance_id] = dep_list
                else:
                    dependencies[instance.instance_id] = []
            
            return dependencies
            
        except Exception as e:
            self.logger.error(f"Failed to get dependencies for {service_name}: {e}")
            return {}
    
    def register_with_ttl_check(self, service: ServiceInstance, ttl_seconds: int = 30) -> bool:
        """Register service with TTL health check for auto-deregistration"""
        ttl_check = HealthCheck(
            check_id=f"{service.instance_id}-ttl",
            service_name=service.service_name,
            check_type="ttl",
            target="",
            interval=ttl_seconds,
            timeout=ttl_seconds,
            deregister_critical_after=ttl_seconds * 3,
            notes="TTL check for auto-deregistration"
        )
        
        return self.register_service(service, [ttl_check])
    
    def heartbeat(self, service_id: str) -> bool:
        """Send heartbeat for TTL check"""
        try:
            check_id = f"{service_id}-ttl"
            self.consul.agent.check.ttl_pass(check_id)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send heartbeat for {service_id}: {e}")
            return False
    
    def start(self):
        """Start the service discovery client"""
        self.running = True
        self.logger.info("Consul service discovery client started")
    
    def stop(self):
        """Stop the service discovery client"""
        self.running = False
        
        # Stop all watch threads
        for watch_id in list(self.watch_threads.keys()):
            self.stop_watch(watch_id)
        
        self.logger.info("Consul service discovery client stopped")


class ServiceRegistry:
    """High-level service registry wrapper around Consul"""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.consul_client = ConsulServiceDiscovery(consul_host, consul_port)
        self.registered_services = {}
        self.heartbeat_threads = {}
        self.logger = logging.getLogger(__name__)
        
    def auto_register_service(self, service_name: str, port: int, 
                            health_check_path: str = "/health",
                            tags: List[str] = None,
                            metadata: Dict[str, Any] = None) -> str:
        """Automatically register a service with best practices"""
        
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Generate instance ID
        instance_id = f"{service_name}-{local_ip}-{port}"
        
        # Create service instance
        service = ServiceInstance(
            service_name=service_name,
            instance_id=instance_id,
            address=local_ip,
            port=port,
            tags=tags or [],
            metadata=metadata or {},
            status=ServiceStatus.UNKNOWN,
            version=metadata.get("version", "1.0") if metadata else "1.0",
            registered_at=datetime.now(),
            last_heartbeat=datetime.now()
        )
        
        # Create health checks
        health_checks = [
            HealthCheck(
                check_id=f"{instance_id}-http",
                service_name=service_name,
                check_type="http",
                target=f"http://{local_ip}:{port}{health_check_path}",
                interval=10,
                timeout=5,
                deregister_critical_after=60,
                notes="HTTP health check"
            )
        ]
        
        # Register service
        if self.consul_client.register_service(service, health_checks):
            self.registered_services[instance_id] = service
            
            # Start heartbeat for additional TTL check
            self._start_heartbeat(instance_id)
            
            return instance_id
        
        return None
    
    def _start_heartbeat(self, service_id: str, interval: int = 15):
        """Start heartbeat thread for a service"""
        def heartbeat_thread():
            while service_id in self.registered_services:
                try:
                    self.consul_client.heartbeat(service_id)
                    time.sleep(interval)
                except Exception as e:
                    self.logger.error(f"Heartbeat failed for {service_id}: {e}")
                    time.sleep(interval)
        
        thread = threading.Thread(target=heartbeat_thread, daemon=True)
        self.heartbeat_threads[service_id] = thread
        thread.start()
    
    def unregister_service(self, service_id: str) -> bool:
        """Unregister a service"""
        if service_id in self.registered_services:
            success = self.consul_client.deregister_service(service_id)
            if success:
                del self.registered_services[service_id]
                if service_id in self.heartbeat_threads:
                    del self.heartbeat_threads[service_id]
            return success
        return False
    
    def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get healthy instances of a service"""
        return self.consul_client.discover_services(service_name, healthy_only=True)
    
    def watch_service_changes(self, service_name: str, 
                            callback: Callable[[List[ServiceInstance]], None]) -> str:
        """Watch for service changes"""
        return self.consul_client.watch_service(service_name, callback)
    
    def start(self):
        """Start the service registry"""
        self.consul_client.start()
        self.logger.info("Service registry started")
    
    def stop(self):
        """Stop the service registry and cleanup"""
        # Unregister all services
        for service_id in list(self.registered_services.keys()):
            self.unregister_service(service_id)
        
        self.consul_client.stop()
        self.logger.info("Service registry stopped")


# Usage example
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize service registry
    registry = ServiceRegistry()
    registry.start()
    
    # Auto-register a service
    service_id = registry.auto_register_service(
        service_name="example-service",
        port=8080,
        tags=["api", "v1"],
        metadata={"version": "1.0", "team": "platform"}
    )
    
    print(f"Registered service with ID: {service_id}")
    
    # Watch for changes
    def on_service_change(instances):
        print(f"Service instances changed: {len(instances)} instances")
        for instance in instances:
            print(f"  - {instance.instance_id} ({instance.status.value})")
    
    watch_id = registry.watch_service_changes("example-service", on_service_change)
    
    try:
        time.sleep(30)  # Run for 30 seconds
    finally:
        registry.stop()