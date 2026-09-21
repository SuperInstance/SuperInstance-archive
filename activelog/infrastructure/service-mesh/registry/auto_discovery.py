import asyncio
import aiohttp
import docker
import json
import threading
import time
import logging
import psutil
import socket
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import consul
from pathlib import Path
import yaml
import os


class ServiceDiscoveryMethod(Enum):
    DOCKER = "docker"
    PROCESS = "process"
    KUBERNETES = "kubernetes"
    CONSUL_CONNECT = "consul_connect"
    FILE_BASED = "file_based"
    NETWORK_SCAN = "network_scan"


@dataclass
class DiscoveredService:
    name: str
    instance_id: str
    host: str
    port: int
    protocol: str  # http, https, grpc, tcp
    version: str
    tags: List[str]
    health_check_path: str
    discovery_method: ServiceDiscoveryMethod
    discovered_at: datetime
    metadata: Dict[str, Any]
    container_id: Optional[str] = None
    process_id: Optional[int] = None


class DockerServiceDiscovery:
    """Discover services running in Docker containers"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.logger = logging.getLogger(__name__)
    
    def discover_services(self) -> List[DiscoveredService]:
        """Discover services from Docker containers"""
        services = []
        
        try:
            containers = self.docker_client.containers.list(all=False)  # Only running containers
            
            for container in containers:
                # Get container info
                attrs = container.attrs
                config = attrs.get('Config', {})
                network_settings = attrs.get('NetworkSettings', {})
                
                # Extract service information from labels
                labels = config.get('Labels') or {}
                
                # Check if this is a service container
                if not self._is_service_container(labels, config):
                    continue
                
                service_name = self._extract_service_name(container.name, labels)
                if not service_name:
                    continue
                
                # Extract ports
                ports = self._extract_ports(network_settings, config)
                if not ports:
                    continue
                
                for port_info in ports:
                    service = DiscoveredService(
                        name=service_name,
                        instance_id=f"{service_name}-{container.short_id}",
                        host=port_info['host'],
                        port=port_info['port'],
                        protocol=port_info.get('protocol', 'http'),
                        version=labels.get('version', '1.0'),
                        tags=self._extract_tags(labels),
                        health_check_path=labels.get('health.path', '/health'),
                        discovery_method=ServiceDiscoveryMethod.DOCKER,
                        discovered_at=datetime.now(),
                        metadata={
                            'container_name': container.name,
                            'image': config.get('Image'),
                            'created': attrs.get('Created'),
                            'labels': labels
                        },
                        container_id=container.id
                    )
                    services.append(service)
            
            self.logger.info(f"Discovered {len(services)} services from Docker")
            return services
            
        except Exception as e:
            self.logger.error(f"Error discovering Docker services: {e}")
            return []
    
    def _is_service_container(self, labels: Dict[str, str], config: Dict[str, Any]) -> bool:
        """Check if container is a service"""
        # Check for service labels
        if labels.get('service.enable') == 'true':
            return True
        
        if labels.get('traefik.enable') == 'true':
            return True
        
        # Check for exposed ports
        exposed_ports = config.get('ExposedPorts', {})
        if exposed_ports:
            return True
        
        # Check for service annotation
        if any(key.startswith('service.') for key in labels.keys()):
            return True
        
        return False
    
    def _extract_service_name(self, container_name: str, labels: Dict[str, str]) -> Optional[str]:
        """Extract service name from container"""
        # Check labels first
        if 'service.name' in labels:
            return labels['service.name']
        
        if 'com.docker.compose.service' in labels:
            return labels['com.docker.compose.service']
        
        # Extract from container name
        # Remove leading slash if present
        name = container_name.lstrip('/')
        
        # Handle docker-compose naming (project_service_number)
        parts = name.split('_')
        if len(parts) >= 2:
            return parts[-2]  # Service name is usually second to last
        
        return name
    
    def _extract_ports(self, network_settings: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract port information from container"""
        ports = []
        
        # Get port bindings
        port_bindings = network_settings.get('Ports', {})
        networks = network_settings.get('Networks', {})
        
        # Get container IP
        container_ip = None
        for network_name, network_info in networks.items():
            if network_info.get('IPAddress'):
                container_ip = network_info['IPAddress']
                break
        
        if not container_ip:
            container_ip = 'localhost'
        
        # Extract ports from bindings
        for container_port, bindings in port_bindings.items():
            if bindings:
                port_num = int(container_port.split('/')[0])
                protocol = self._detect_protocol(port_num)
                
                # Use host binding if available
                for binding in bindings:
                    host_port = int(binding['HostPort'])
                    ports.append({
                        'host': 'localhost',
                        'port': host_port,
                        'protocol': protocol
                    })
                    break
            else:
                # No host binding, use container IP and port
                port_num = int(container_port.split('/')[0])
                protocol = self._detect_protocol(port_num)
                ports.append({
                    'host': container_ip,
                    'port': port_num,
                    'protocol': protocol
                })
        
        return ports
    
    def _detect_protocol(self, port: int) -> str:
        """Detect protocol based on port number"""
        if port == 443:
            return 'https'
        elif port in [80, 8080, 8000, 3000, 5000]:
            return 'http'
        elif port in [50051, 9090]:
            return 'grpc'
        else:
            return 'http'  # Default to HTTP
    
    def _extract_tags(self, labels: Dict[str, str]) -> List[str]:
        """Extract tags from container labels"""
        tags = []
        
        if 'service.tags' in labels:
            tags.extend(labels['service.tags'].split(','))
        
        # Add environment tag
        if 'environment' in labels:
            tags.append(f"env:{labels['environment']}")
        
        # Add version tag
        if 'version' in labels:
            tags.append(f"version:{labels['version']}")
        
        return [tag.strip() for tag in tags if tag.strip()]


class ProcessServiceDiscovery:
    """Discover services running as processes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.known_service_patterns = [
            (r'.*server.*', ['server']),
            (r'.*api.*', ['api']),
            (r'.*web.*', ['web']),
            (r'.*service.*', ['service']),
            (r'nginx.*', ['web', 'proxy']),
            (r'redis.*', ['database', 'cache']),
            (r'postgres.*', ['database']),
            (r'mysql.*', ['database']),
            (r'mongo.*', ['database']),
        ]
    
    def discover_services(self) -> List[DiscoveredService]:
        """Discover services from running processes"""
        services = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'connections']):
                try:
                    proc_info = proc.info
                    
                    if not self._is_service_process(proc_info):
                        continue
                    
                    # Get process connections
                    connections = proc_info.get('connections', [])
                    listening_ports = self._get_listening_ports(connections)
                    
                    if not listening_ports:
                        continue
                    
                    service_name = self._extract_service_name_from_process(proc_info)
                    tags = self._extract_tags_from_process(proc_info)
                    
                    for port_info in listening_ports:
                        service = DiscoveredService(
                            name=service_name,
                            instance_id=f"{service_name}-{proc_info['pid']}",
                            host=port_info['host'],
                            port=port_info['port'],
                            protocol=self._detect_protocol(port_info['port']),
                            version='1.0',  # Default version
                            tags=tags,
                            health_check_path='/health',
                            discovery_method=ServiceDiscoveryMethod.PROCESS,
                            discovered_at=datetime.now(),
                            metadata={
                                'cmdline': proc_info.get('cmdline', []),
                                'name': proc_info.get('name', ''),
                            },
                            process_id=proc_info['pid']
                        )
                        services.append(service)
                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    self.logger.debug(f"Error processing process {proc_info.get('pid')}: {e}")
                    continue
            
            self.logger.info(f"Discovered {len(services)} services from processes")
            return services
            
        except Exception as e:
            self.logger.error(f"Error discovering process services: {e}")
            return []
    
    def _is_service_process(self, proc_info: Dict[str, Any]) -> bool:
        """Check if process is likely a service"""
        name = proc_info.get('name', '').lower()
        cmdline = ' '.join(proc_info.get('cmdline', [])).lower()
        
        # Skip system processes
        system_processes = ['systemd', 'kernel', 'kthread', 'migration', 'rcu_', 'watchdog']
        if any(sys_proc in name for sys_proc in system_processes):
            return False
        
        # Skip shell processes
        if name in ['bash', 'sh', 'zsh', 'fish', 'dash']:
            return False
        
        # Check for service indicators
        service_indicators = ['server', 'service', 'daemon', 'api', 'web', 'app']
        if any(indicator in name or indicator in cmdline for indicator in service_indicators):
            return True
        
        # Check for specific service patterns
        for pattern, _ in self.known_service_patterns:
            if re.match(pattern, name) or re.match(pattern, cmdline):
                return True
        
        return False
    
    def _get_listening_ports(self, connections: List[Any]) -> List[Dict[str, Any]]:
        """Extract listening ports from process connections"""
        ports = []
        
        for conn in connections:
            if hasattr(conn, 'status') and conn.status == 'LISTEN':
                if hasattr(conn, 'laddr') and conn.laddr:
                    host = conn.laddr.ip if conn.laddr.ip != '0.0.0.0' else 'localhost'
                    port = conn.laddr.port
                    
                    # Skip privileged ports that are likely system services
                    if port < 1024 and port not in [80, 443]:
                        continue
                    
                    ports.append({'host': host, 'port': port})
        
        return ports
    
    def _extract_service_name_from_process(self, proc_info: Dict[str, Any]) -> str:
        """Extract service name from process info"""
        name = proc_info.get('name', '')
        cmdline = proc_info.get('cmdline', [])
        
        # Try to extract from command line
        if cmdline:
            # Look for script names or executables
            for arg in cmdline:
                if any(ext in arg for ext in ['.py', '.js', '.jar', '.go']):
                    basename = os.path.basename(arg).split('.')[0]
                    if basename and basename != 'main':
                        return basename
            
            # Look for service names in arguments
            for arg in cmdline:
                if 'service' in arg.lower() or 'server' in arg.lower():
                    basename = os.path.basename(arg)
                    if basename:
                        return basename.split('.')[0]
        
        # Fallback to process name
        return name or f"unknown-{proc_info['pid']}"
    
    def _extract_tags_from_process(self, proc_info: Dict[str, Any]) -> List[str]:
        """Extract tags from process info"""
        tags = []
        name = proc_info.get('name', '').lower()
        cmdline = ' '.join(proc_info.get('cmdline', [])).lower()
        
        # Apply known patterns
        for pattern, pattern_tags in self.known_service_patterns:
            if re.match(pattern, name) or re.match(pattern, cmdline):
                tags.extend(pattern_tags)
                break
        
        # Add language/runtime tags
        if 'python' in name or '.py' in cmdline:
            tags.append('python')
        elif 'java' in name or '.jar' in cmdline:
            tags.append('java')
        elif 'node' in name or '.js' in cmdline:
            tags.append('nodejs')
        elif 'go' in name or 'golang' in cmdline:
            tags.append('go')
        
        return list(set(tags))  # Remove duplicates
    
    def _detect_protocol(self, port: int) -> str:
        """Detect protocol based on port number"""
        if port == 443:
            return 'https'
        elif port in [80, 8080, 8000, 3000, 5000, 8888, 9000]:
            return 'http'
        elif port in [50051, 9090]:
            return 'grpc'
        else:
            return 'http'


class NetworkServiceDiscovery:
    """Discover services by scanning network"""
    
    def __init__(self, scan_ranges: List[str] = None):
        self.scan_ranges = scan_ranges or ['127.0.0.1', '192.168.1.0/24']
        self.logger = logging.getLogger(__name__)
        self.common_ports = [
            80, 443, 8080, 8000, 8443, 3000, 5000, 9000, 9090,
            3306, 5432, 6379, 27017, 5672, 15672
        ]
    
    async def discover_services(self) -> List[DiscoveredService]:
        """Discover services by network scanning"""
        services = []
        
        try:
            # For demonstration, we'll scan localhost common ports
            for port in self.common_ports:
                if await self._is_port_open('localhost', port):
                    service_info = await self._identify_service('localhost', port)
                    if service_info:
                        service = DiscoveredService(
                            name=service_info['name'],
                            instance_id=f"{service_info['name']}-localhost-{port}",
                            host='localhost',
                            port=port,
                            protocol=service_info['protocol'],
                            version='1.0',
                            tags=service_info.get('tags', []),
                            health_check_path='/health',
                            discovery_method=ServiceDiscoveryMethod.NETWORK_SCAN,
                            discovered_at=datetime.now(),
                            metadata=service_info.get('metadata', {})
                        )
                        services.append(service)
            
            self.logger.info(f"Discovered {len(services)} services from network scan")
            return services
            
        except Exception as e:
            self.logger.error(f"Error during network discovery: {e}")
            return []
    
    async def _is_port_open(self, host: str, port: int) -> bool:
        """Check if port is open"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=1.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
    
    async def _identify_service(self, host: str, port: int) -> Optional[Dict[str, Any]]:
        """Try to identify service type from port and responses"""
        try:
            # Try HTTP first
            if await self._try_http_identification(host, port):
                return await self._try_http_identification(host, port)
            
            # Try specific service identification based on port
            service_map = {
                3306: {'name': 'mysql', 'protocol': 'tcp', 'tags': ['database']},
                5432: {'name': 'postgresql', 'protocol': 'tcp', 'tags': ['database']},
                6379: {'name': 'redis', 'protocol': 'tcp', 'tags': ['cache', 'database']},
                27017: {'name': 'mongodb', 'protocol': 'tcp', 'tags': ['database']},
                5672: {'name': 'rabbitmq', 'protocol': 'tcp', 'tags': ['messaging']},
                15672: {'name': 'rabbitmq-mgmt', 'protocol': 'http', 'tags': ['messaging', 'management']},
            }
            
            if port in service_map:
                return service_map[port]
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error identifying service on {host}:{port}: {e}")
            return None
    
    async def _try_http_identification(self, host: str, port: int) -> Optional[Dict[str, Any]]:
        """Try to identify HTTP-based service"""
        try:
            protocol = 'https' if port == 443 else 'http'
            url = f"{protocol}://{host}:{port}/"
            
            timeout = aiohttp.ClientTimeout(total=2.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    # Check for service identification headers
                    server = response.headers.get('Server', '').lower()
                    
                    service_name = f"http-service-{port}"
                    tags = ['http']
                    
                    if 'nginx' in server:
                        service_name = 'nginx'
                        tags.extend(['web', 'proxy'])
                    elif 'apache' in server:
                        service_name = 'apache'
                        tags.extend(['web'])
                    elif 'express' in server:
                        service_name = 'express-app'
                        tags.extend(['nodejs', 'api'])
                    
                    return {
                        'name': service_name,
                        'protocol': protocol,
                        'tags': tags,
                        'metadata': {
                            'server_header': server,
                            'status_code': response.status
                        }
                    }
        except:
            return None


class AutoServiceRegistry:
    """Automatic service discovery and registration system"""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.discovered_services: Dict[str, DiscoveredService] = {}
        self.registry_thread = None
        
        # Initialize discovery methods
        self.docker_discovery = DockerServiceDiscovery()
        self.process_discovery = ProcessServiceDiscovery()
        self.network_discovery = NetworkServiceDiscovery()
        
        # Discovery settings
        self.discovery_interval = 30  # seconds
        self.enabled_methods = [
            ServiceDiscoveryMethod.DOCKER,
            ServiceDiscoveryMethod.PROCESS,
            ServiceDiscoveryMethod.NETWORK_SCAN
        ]
    
    def start_auto_discovery(self):
        """Start automatic service discovery"""
        self.running = True
        self.registry_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.registry_thread.start()
        self.logger.info("Auto discovery started")
    
    def stop_auto_discovery(self):
        """Stop automatic service discovery"""
        self.running = False
        if self.registry_thread:
            self.registry_thread.join(timeout=5)
        self.logger.info("Auto discovery stopped")
    
    def _discovery_loop(self):
        """Main discovery loop"""
        while self.running:
            try:
                self._perform_discovery()
                time.sleep(self.discovery_interval)
            except Exception as e:
                self.logger.error(f"Error in discovery loop: {e}")
                time.sleep(self.discovery_interval)
    
    def _perform_discovery(self):
        """Perform service discovery using enabled methods"""
        all_discovered = []
        
        # Docker discovery
        if ServiceDiscoveryMethod.DOCKER in self.enabled_methods:
            try:
                docker_services = self.docker_discovery.discover_services()
                all_discovered.extend(docker_services)
            except Exception as e:
                self.logger.error(f"Docker discovery failed: {e}")
        
        # Process discovery
        if ServiceDiscoveryMethod.PROCESS in self.enabled_methods:
            try:
                process_services = self.process_discovery.discover_services()
                all_discovered.extend(process_services)
            except Exception as e:
                self.logger.error(f"Process discovery failed: {e}")
        
        # Network discovery (async)
        if ServiceDiscoveryMethod.NETWORK_SCAN in self.enabled_methods:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                network_services = loop.run_until_complete(self.network_discovery.discover_services())
                all_discovered.extend(network_services)
                loop.close()
            except Exception as e:
                self.logger.error(f"Network discovery failed: {e}")
        
        # Update registry
        self._update_service_registry(all_discovered)
    
    def _update_service_registry(self, discovered: List[DiscoveredService]):
        """Update Consul service registry with discovered services"""
        current_services = {s.instance_id for s in discovered}
        previous_services = set(self.discovered_services.keys())
        
        # Register new services
        new_services = current_services - previous_services
        for service_id in new_services:
            service = next(s for s in discovered if s.instance_id == service_id)
            self._register_discovered_service(service)
        
        # Deregister removed services
        removed_services = previous_services - current_services
        for service_id in removed_services:
            self._deregister_service(service_id)
        
        # Update discovered services cache
        self.discovered_services = {s.instance_id: s for s in discovered}
        
        self.logger.info(f"Discovery update: {len(new_services)} new, {len(removed_services)} removed")
    
    def _register_discovered_service(self, service: DiscoveredService) -> bool:
        """Register discovered service with Consul"""
        try:
            # Create health check
            health_check_url = f"{service.protocol}://{service.host}:{service.port}{service.health_check_path}"
            
            check = {
                "HTTP": health_check_url,
                "Interval": "30s",
                "Timeout": "10s",
                "DeregisterCriticalServiceAfter": "60s"
            }
            
            # If it's not HTTP, use TCP check
            if service.protocol not in ['http', 'https']:
                check = {
                    "TCP": f"{service.host}:{service.port}",
                    "Interval": "30s",
                    "Timeout": "10s",
                    "DeregisterCriticalServiceAfter": "60s"
                }
            
            # Register with Consul
            self.consul.agent.service.register(
                name=service.name,
                service_id=service.instance_id,
                address=service.host,
                port=service.port,
                tags=service.tags + [f"discovery:{service.discovery_method.value}"],
                meta={
                    'version': service.version,
                    'protocol': service.protocol,
                    'discovered_at': service.discovered_at.isoformat(),
                    'discovery_method': service.discovery_method.value,
                    **{k: str(v) for k, v in service.metadata.items()}
                },
                check=check
            )
            
            self.logger.info(f"Registered discovered service: {service.name} ({service.instance_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register service {service.instance_id}: {e}")
            return False
    
    def _deregister_service(self, service_id: str) -> bool:
        """Deregister service from Consul"""
        try:
            self.consul.agent.service.deregister(service_id)
            self.logger.info(f"Deregistered service: {service_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    def get_discovered_services(self) -> List[DiscoveredService]:
        """Get all currently discovered services"""
        return list(self.discovered_services.values())
    
    def force_discovery(self):
        """Force an immediate discovery cycle"""
        self._perform_discovery()


# Usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize auto discovery
    auto_registry = AutoServiceRegistry()
    
    try:
        # Start auto discovery
        auto_registry.start_auto_discovery()
        
        # Let it run for a while
        time.sleep(60)
        
        # Show discovered services
        services = auto_registry.get_discovered_services()
        print(f"\nDiscovered {len(services)} services:")
        for service in services:
            print(f"  - {service.name} ({service.host}:{service.port}) "
                  f"via {service.discovery_method.value}")
        
    finally:
        auto_registry.stop_auto_discovery()