"""
ActiveLog Integration Hub - Service Discovery System
Auto-detects and manages all 70+ services in the ecosystem
"""

import asyncio
import aiohttp
import json
import time
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import yaml
import psutil
import socket
from datetime import datetime, timedelta

class ServiceType(Enum):
    API = "api"
    WEB = "web"
    WORKER = "worker"
    DATABASE = "database"
    QUEUE = "queue"
    CACHE = "cache"
    GATEWAY = "gateway"
    MICROSERVICE = "microservice"

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"
    UNKNOWN = "unknown"

@dataclass
class ServiceEndpoint:
    path: str
    method: str
    description: str = ""
    requires_auth: bool = False
    response_time_ms: Optional[float] = None

@dataclass
class ServiceInfo:
    name: str
    service_type: ServiceType
    version: str = "1.0.0"
    host: str = "localhost"
    port: int = 0
    health_endpoint: str = "/health"
    status: ServiceStatus = ServiceStatus.UNKNOWN
    endpoints: List[ServiceEndpoint] = None
    dependencies: List[str] = None
    tags: List[str] = None
    last_health_check: Optional[datetime] = None
    response_time_ms: Optional[float] = None
    error_count: int = 0
    uptime_seconds: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = []
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

class ServiceDiscovery:
    def __init__(self, activelog_root: str = "/home/activeloguser/activelog"):
        self.activelog_root = Path(activelog_root)
        self.services: Dict[str, ServiceInfo] = {}
        self.service_registry = {}
        self.discovery_cache = {}
        self.last_scan = None
        
    async def discover_all_services(self) -> Dict[str, ServiceInfo]:
        """Discover all services in the ActiveLog ecosystem"""
        discovered_services = {}
        
        # Scan services directory
        services_dir = self.activelog_root / "services"
        if services_dir.exists():
            for service_path in services_dir.iterdir():
                if service_path.is_dir():
                    service_info = await self.analyze_service_directory(service_path)
                    if service_info:
                        discovered_services[service_info.name] = service_info
        
        # Scan for running processes
        running_services = await self.discover_running_services()
        for service_name, service_info in running_services.items():
            if service_name not in discovered_services:
                discovered_services[service_name] = service_info
            else:
                # Merge running service info with directory info
                discovered_services[service_name].status = service_info.status
                discovered_services[service_name].port = service_info.port
                discovered_services[service_name].uptime_seconds = service_info.uptime_seconds
        
        # Scan for Docker services
        docker_services = await self.discover_docker_services()
        for service_name, service_info in docker_services.items():
            if service_name not in discovered_services:
                discovered_services[service_name] = service_info
            else:
                # Update with Docker info
                discovered_services[service_name].status = service_info.status
                if service_info.port > 0:
                    discovered_services[service_name].port = service_info.port
        
        self.services = discovered_services
        self.last_scan = datetime.now()
        return discovered_services
    
    async def analyze_service_directory(self, service_path: Path) -> Optional[ServiceInfo]:
        """Analyze a service directory to extract service information"""
        service_name = service_path.name
        
        # Read package.json if it exists (Node.js services)
        package_json = service_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                    return await self.create_service_from_package_json(service_name, package_data, service_path)
            except Exception as e:
                pass
        
        # Read requirements.txt and analyze Python files
        requirements_txt = service_path / "requirements.txt"
        if requirements_txt.exists() or any(service_path.glob("*.py")):
            return await self.create_service_from_python_analysis(service_name, service_path)
        
        # Check for Docker files
        dockerfile = service_path / "Dockerfile"
        docker_compose = service_path / "docker-compose.yml"
        if dockerfile.exists() or docker_compose.exists():
            return await self.create_service_from_docker_analysis(service_name, service_path)
        
        # Default service info if no specific files found
        return ServiceInfo(
            name=service_name,
            service_type=ServiceType.MICROSERVICE,
            tags=["auto-discovered"],
            metadata={"discovery_method": "directory_scan"}
        )
    
    async def create_service_from_package_json(self, name: str, package_data: dict, service_path: Path) -> ServiceInfo:
        """Create service info from package.json analysis"""
        port = await self.extract_port_from_package(package_data, service_path)
        service_type = self.infer_service_type_from_dependencies(package_data.get("dependencies", {}))
        
        endpoints = []
        dependencies = []
        
        # Analyze main file for routes
        main_file = service_path / (package_data.get("main", "index.js"))
        if main_file.exists():
            endpoints = await self.extract_endpoints_from_js(main_file)
            dependencies = await self.extract_dependencies_from_js(main_file)
        
        return ServiceInfo(
            name=name,
            service_type=service_type,
            version=package_data.get("version", "1.0.0"),
            port=port,
            endpoints=endpoints,
            dependencies=dependencies,
            tags=["nodejs", "auto-discovered"],
            metadata={
                "package_manager": "npm",
                "main_file": package_data.get("main", "index.js"),
                "discovery_method": "package_json"
            }
        )
    
    async def create_service_from_python_analysis(self, name: str, service_path: Path) -> ServiceInfo:
        """Create service info from Python service analysis"""
        port = await self.extract_port_from_python(service_path)
        endpoints = []
        dependencies = []
        
        # Analyze Python files for Flask/FastAPI routes
        for py_file in service_path.glob("**/*.py"):
            file_endpoints = await self.extract_endpoints_from_python(py_file)
            endpoints.extend(file_endpoints)
            
            file_deps = await self.extract_dependencies_from_python(py_file)
            dependencies.extend(file_deps)
        
        service_type = ServiceType.API if endpoints else ServiceType.WORKER
        
        return ServiceInfo(
            name=name,
            service_type=service_type,
            port=port,
            endpoints=endpoints,
            dependencies=list(set(dependencies)),
            tags=["python", "auto-discovered"],
            metadata={
                "language": "python",
                "discovery_method": "python_analysis"
            }
        )
    
    async def create_service_from_docker_analysis(self, name: str, service_path: Path) -> ServiceInfo:
        """Create service info from Docker analysis"""
        port = 0
        service_type = ServiceType.MICROSERVICE
        
        dockerfile = service_path / "Dockerfile"
        if dockerfile.exists():
            try:
                with open(dockerfile, 'r') as f:
                    content = f.read()
                    # Extract EXPOSE port
                    import re
                    expose_match = re.search(r'EXPOSE\s+(\d+)', content)
                    if expose_match:
                        port = int(expose_match.group(1))
            except Exception:
                pass
        
        return ServiceInfo(
            name=name,
            service_type=service_type,
            port=port,
            tags=["docker", "auto-discovered"],
            metadata={
                "containerized": True,
                "discovery_method": "docker_analysis"
            }
        )
    
    async def discover_running_services(self) -> Dict[str, ServiceInfo]:
        """Discover services by scanning running processes"""
        running_services = {}
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                proc_info = proc.info
                cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                
                # Look for ActiveLog-related processes
                if any(keyword in cmdline.lower() for keyword in ['activelog', 'node', 'python', 'flask', 'fastapi']):
                    # Try to extract port from command line
                    port = self.extract_port_from_cmdline(cmdline)
                    if port:
                        service_name = f"running-{proc_info['name']}-{port}"
                        running_services[service_name] = ServiceInfo(
                            name=service_name,
                            service_type=ServiceType.API if port else ServiceType.WORKER,
                            port=port,
                            status=ServiceStatus.HEALTHY,
                            uptime_seconds=time.time() - proc_info['create_time'],
                            tags=["running", "process-discovered"],
                            metadata={
                                "pid": proc_info['pid'],
                                "cmdline": cmdline,
                                "discovery_method": "process_scan"
                            }
                        )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return running_services
    
    async def discover_docker_services(self) -> Dict[str, ServiceInfo]:
        """Discover services running in Docker containers"""
        docker_services = {}
        
        try:
            # Run docker ps command
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line:
                        container_info = json.loads(line)
                        service_name = container_info.get('Names', 'unknown')
                        ports = container_info.get('Ports', '')
                        
                        # Extract port from ports string
                        port = self.extract_port_from_docker_ports(ports)
                        
                        docker_services[service_name] = ServiceInfo(
                            name=service_name,
                            service_type=ServiceType.MICROSERVICE,
                            port=port,
                            status=ServiceStatus.HEALTHY if container_info.get('Status', '').startswith('Up') else ServiceStatus.STOPPED,
                            tags=["docker", "container-discovered"],
                            metadata={
                                "container_id": container_info.get('ID', ''),
                                "image": container_info.get('Image', ''),
                                "ports": ports,
                                "discovery_method": "docker_scan"
                            }
                        )
        except Exception as e:
            pass
        
        return docker_services
    
    async def extract_port_from_package(self, package_data: dict, service_path: Path) -> int:
        """Extract port number from package.json or related files"""
        # Check scripts for port references
        scripts = package_data.get("scripts", {})
        for script in scripts.values():
            port_match = self.extract_port_from_text(script)
            if port_match:
                return port_match
        
        # Check environment files
        env_file = service_path / ".env"
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    port_match = self.extract_port_from_text(content)
                    if port_match:
                        return port_match
            except Exception:
                pass
        
        return 0
    
    async def extract_port_from_python(self, service_path: Path) -> int:
        """Extract port from Python service files"""
        for py_file in service_path.glob("**/*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    # Look for app.run(port=...) or similar
                    import re
                    port_patterns = [
                        r'port=(\d+)',
                        r'PORT\s*=\s*(\d+)',
                        r'listen\((\d+)\)',
                        r'bind.*:(\d+)'
                    ]
                    for pattern in port_patterns:
                        match = re.search(pattern, content)
                        if match:
                            return int(match.group(1))
            except Exception:
                continue
        
        return 0
    
    def extract_port_from_text(self, text: str) -> Optional[int]:
        """Extract port number from text using regex"""
        import re
        # Common port patterns
        patterns = [
            r'port[=\s]*(\d+)',
            r'PORT[=\s]*(\d+)',
            r':(\d{4,5})',  # :8080 format
            r'--port\s+(\d+)',
            r'-p\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                port = int(match.group(1))
                if 3000 <= port <= 9999:  # Reasonable port range
                    return port
        
        return None
    
    def extract_port_from_cmdline(self, cmdline: str) -> int:
        """Extract port from command line"""
        port = self.extract_port_from_text(cmdline)
        return port if port else 0
    
    def extract_port_from_docker_ports(self, ports_str: str) -> int:
        """Extract port from Docker ports string"""
        if not ports_str:
            return 0
        
        import re
        # Docker ports format: "0.0.0.0:8080->8080/tcp"
        match = re.search(r'(\d+)->', ports_str)
        if match:
            return int(match.group(1))
        
        match = re.search(r':(\d+)/', ports_str)
        if match:
            return int(match.group(1))
        
        return 0
    
    def infer_service_type_from_dependencies(self, dependencies: dict) -> ServiceType:
        """Infer service type from package dependencies"""
        if any(dep in dependencies for dep in ['express', 'koa', 'fastify']):
            return ServiceType.API
        elif any(dep in dependencies for dep in ['react', 'vue', 'angular']):
            return ServiceType.WEB
        elif any(dep in dependencies for dep in ['bull', 'agenda', 'kue']):
            return ServiceType.QUEUE
        elif any(dep in dependencies for dep in ['redis', 'memcached']):
            return ServiceType.CACHE
        elif any(dep in dependencies for dep in ['mongoose', 'sequelize', 'prisma']):
            return ServiceType.DATABASE
        else:
            return ServiceType.MICROSERVICE
    
    async def extract_endpoints_from_js(self, js_file: Path) -> List[ServiceEndpoint]:
        """Extract API endpoints from JavaScript files"""
        endpoints = []
        try:
            with open(js_file, 'r') as f:
                content = f.read()
                
            import re
            # Express route patterns
            patterns = [
                r"app\.(\w+)\(['\"]([^'\"]+)['\"]",
                r"router\.(\w+)\(['\"]([^'\"]+)['\"]",
                r"\.(\w+)\(['\"]([^'\"]+)['\"].*?function"
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for method, path in matches:
                    if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                        endpoints.append(ServiceEndpoint(
                            path=path,
                            method=method.upper(),
                            description=f"Auto-discovered {method.upper()} endpoint"
                        ))
        except Exception:
            pass
        
        return endpoints
    
    async def extract_endpoints_from_python(self, py_file: Path) -> List[ServiceEndpoint]:
        """Extract API endpoints from Python files"""
        endpoints = []
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            import re
            # Flask/FastAPI route patterns
            patterns = [
                r"@app\.route\(['\"]([^'\"]+)['\"].*?methods=\[['\"]([\w,\s]+)['\"]\]",
                r"@app\.(\w+)\(['\"]([^'\"]+)['\"]",
                r"@router\.(\w+)\(['\"]([^'\"]+)['\"]"
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match) == 2:
                        if match[0] in ['get', 'post', 'put', 'delete', 'patch']:
                            endpoints.append(ServiceEndpoint(
                                path=match[1],
                                method=match[0].upper(),
                                description=f"Auto-discovered {match[0].upper()} endpoint"
                            ))
                        else:
                            # Route with methods array
                            path, methods = match
                            for method in methods.split(','):
                                method = method.strip().strip('\'"')
                                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                                    endpoints.append(ServiceEndpoint(
                                        path=path,
                                        method=method.upper(),
                                        description=f"Auto-discovered {method.upper()} endpoint"
                                    ))
        except Exception:
            pass
        
        return endpoints
    
    async def extract_dependencies_from_js(self, js_file: Path) -> List[str]:
        """Extract service dependencies from JavaScript files"""
        dependencies = []
        try:
            with open(js_file, 'r') as f:
                content = f.read()
            
            import re
            # Look for require statements and axios calls to other services
            patterns = [
                r"require\(['\"]([^'\"]+)['\"]",
                r"import.*from\s+['\"]([^'\"]+)['\"]",
                r"axios\.\w+\(['\"]([^'\"]+)['\"]",
                r"fetch\(['\"]([^'\"]+)['\"]"
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if any(keyword in match for keyword in ['activelog', 'localhost', 'service']):
                        dependencies.append(match)
        except Exception:
            pass
        
        return dependencies
    
    async def extract_dependencies_from_python(self, py_file: Path) -> List[str]:
        """Extract service dependencies from Python files"""
        dependencies = []
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            import re
            # Look for requests calls and imports
            patterns = [
                r"requests\.\w+\(['\"]([^'\"]+)['\"]",
                r"aiohttp\.\w+\(['\"]([^'\"]+)['\"]",
                r"httpx\.\w+\(['\"]([^'\"]+)['\"]"
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if any(keyword in match for keyword in ['activelog', 'localhost', 'service']):
                        dependencies.append(match)
        except Exception:
            pass
        
        return dependencies
    
    async def register_service(self, service_info: ServiceInfo):
        """Register a service in the discovery system"""
        self.services[service_info.name] = service_info
        self.service_registry[service_info.name] = {
            'registered_at': datetime.now(),
            'last_heartbeat': datetime.now()
        }
    
    async def unregister_service(self, service_name: str):
        """Unregister a service from the discovery system"""
        if service_name in self.services:
            del self.services[service_name]
        if service_name in self.service_registry:
            del self.service_registry[service_name]
    
    async def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """Get service information by name"""
        return self.services.get(service_name)
    
    async def get_services_by_type(self, service_type: ServiceType) -> List[ServiceInfo]:
        """Get all services of a specific type"""
        return [service for service in self.services.values() 
                if service.service_type == service_type]
    
    async def get_healthy_services(self) -> List[ServiceInfo]:
        """Get all healthy services"""
        return [service for service in self.services.values() 
                if service.status == ServiceStatus.HEALTHY]
    
    async def find_services_by_tag(self, tag: str) -> List[ServiceInfo]:
        """Find services by tag"""
        return [service for service in self.services.values() 
                if tag in service.tags]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert discovery state to dictionary"""
        return {
            'services': {name: asdict(service) for name, service in self.services.items()},
            'registry': self.service_registry,
            'last_scan': self.last_scan.isoformat() if self.last_scan else None,
            'total_services': len(self.services),
            'service_types': {
                service_type.value: len(self.get_services_by_type(service_type))
                for service_type in ServiceType
            }
        }

# Example usage
async def main():
    discovery = ServiceDiscovery()
    services = await discovery.discover_all_services()
    
    print(f"Discovered {len(services)} services:")
    for name, service in services.items():
        print(f"- {name}: {service.service_type.value} on port {service.port}")
        if service.endpoints:
            for endpoint in service.endpoints[:3]:  # Show first 3 endpoints
                print(f"  {endpoint.method} {endpoint.path}")

if __name__ == "__main__":
    asyncio.run(main())