"""
ActiveLog Integration Hub - Service Dependency Mapper
Visualizes and analyzes dependencies between all 70+ services
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from service_discovery import ServiceDiscovery, ServiceInfo, ServiceType
import re

class DependencyType(Enum):
    HTTP_API = "http_api"
    DATABASE = "database"
    QUEUE = "queue"
    CACHE = "cache"
    FILE_SYSTEM = "file_system"
    EXTERNAL_SERVICE = "external_service"
    LIBRARY = "library"
    CONFIGURATION = "configuration"

class DependencyStrength(Enum):
    CRITICAL = "critical"  # Service cannot function without this dependency
    IMPORTANT = "important"  # Service functionality is severely limited
    MODERATE = "moderate"  # Some features depend on this
    OPTIONAL = "optional"  # Nice to have, graceful degradation

@dataclass
class ServiceDependency:
    source_service: str
    target_service: str
    dependency_type: DependencyType
    strength: DependencyStrength
    description: str = ""
    discovered_method: str = ""
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    first_seen: Optional[datetime] = None
    last_verified: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.first_seen:
            self.first_seen = datetime.now()
        if not self.last_verified:
            self.last_verified = datetime.now()

@dataclass
class DependencyCluster:
    cluster_id: str
    name: str
    services: List[str]
    cluster_type: str  # e.g., "data_processing", "user_interface", "ml_pipeline"
    internal_dependencies: List[ServiceDependency]
    external_dependencies: List[ServiceDependency]
    criticality: DependencyStrength
    description: str = ""

@dataclass
class DependencyAnalysis:
    total_services: int
    total_dependencies: int
    dependency_depth: int
    circular_dependencies: List[List[str]]
    critical_path_services: List[str]
    isolated_services: List[str]
    dependency_clusters: List[DependencyCluster]
    bottleneck_services: List[str]
    single_points_of_failure: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

class DependencyMapper:
    def __init__(self, discovery: ServiceDiscovery):
        self.discovery = discovery
        self.dependencies: List[ServiceDependency] = []
        self.dependency_graph = nx.DiGraph()
        self.analysis_cache: Optional[DependencyAnalysis] = None
        self.last_analysis = None
        
        # Configuration for dependency detection
        self.confidence_thresholds = {
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4
        }
        
        # Patterns for different dependency types
        self.dependency_patterns = {
            DependencyType.HTTP_API: [
                r'https?://([^/\s]+)',
                r'fetch\([\'"]([^\'"]+)[\'"]',
                r'axios\.[a-z]+\([\'"]([^\'"]+)[\'"]',
                r'requests\.[a-z]+\([\'"]([^\'"]+)[\'"]',
                r'http://localhost:(\d+)',
                r'http://([a-zA-Z-]+):(\d+)'
            ],
            DependencyType.DATABASE: [
                r'mongodb://([^/\s]+)',
                r'postgresql://([^/\s]+)',
                r'mysql://([^/\s]+)',
                r'redis://([^/\s]+)',
                r'sqlite:([^\s]+)',
                r'DATABASE_URL.*?([^/\s]+)'
            ],
            DependencyType.QUEUE: [
                r'amqp://([^/\s]+)',
                r'rabbitmq://([^/\s]+)',
                r'kafka://([^/\s]+)',
                r'redis://([^/\s]+).*queue',
                r'Queue\([\'"]([^\'"]+)[\'"]'
            ],
            DependencyType.CACHE: [
                r'redis://([^/\s]+)',
                r'memcached://([^/\s]+)',
                r'REDIS_URL.*?([^/\s]+)',
                r'cache\.set\(',
                r'Redis\('
            ]
        }
        
    async def discover_all_dependencies(self) -> List[ServiceDependency]:
        """Discover all dependencies between services"""
        await self.discovery.discover_all_services()
        self.dependencies = []
        
        # Analyze each service for dependencies
        for service_name, service_info in self.discovery.services.items():
            service_deps = await self.analyze_service_dependencies(service_info)
            self.dependencies.extend(service_deps)
        
        # Build dependency graph
        await self.build_dependency_graph()
        
        # Remove duplicates and merge similar dependencies
        self.dependencies = await self.deduplicate_dependencies()
        
        return self.dependencies
    
    async def analyze_service_dependencies(self, service: ServiceInfo) -> List[ServiceDependency]:
        """Analyze a single service for dependencies"""
        dependencies = []
        
        # Analyze configuration files
        config_deps = await self.analyze_configuration_dependencies(service)
        dependencies.extend(config_deps)
        
        # Analyze source code
        code_deps = await self.analyze_code_dependencies(service)
        dependencies.extend(code_deps)
        
        # Analyze Docker files
        docker_deps = await self.analyze_docker_dependencies(service)
        dependencies.extend(docker_deps)
        
        # Analyze package dependencies
        package_deps = await self.analyze_package_dependencies(service)
        dependencies.extend(package_deps)
        
        # Analyze environment variables
        env_deps = await self.analyze_environment_dependencies(service)
        dependencies.extend(env_deps)
        
        return dependencies
    
    async def analyze_configuration_dependencies(self, service: ServiceInfo) -> List[ServiceDependency]:
        """Analyze configuration files for dependencies"""
        dependencies = []
        service_path = Path(f"/home/activeloguser/activelog/services/{service.name}")
        
        if not service_path.exists():
            return dependencies
        
        # Check common config files
        config_files = [
            "config.json", "config.yml", "config.yaml",
            ".env", ".env.local", ".env.production",
            "docker-compose.yml", "docker-compose.yaml"
        ]
        
        for config_file in config_files:
            config_path = service_path / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        content = f.read()
                        
                    # Extract dependencies from config content
                    deps = await self.extract_dependencies_from_text(
                        content, service.name, f"config:{config_file}"
                    )
                    dependencies.extend(deps)
                    
                except Exception as e:
                    continue
        
        return dependencies
    
    async def analyze_code_dependencies(self, service: ServiceInfo) -> List[ServiceDependency]:
        """Analyze source code for dependencies"""
        dependencies = []
        service_path = Path(f"/home/activeloguser/activelog/services/{service.name}")
        
        if not service_path.exists():
            return dependencies
        
        # Analyze code files
        code_extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java"]
        
        for code_file in service_path.rglob("*"):
            if code_file.suffix in code_extensions:
                try:
                    with open(code_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract dependencies from code
                    deps = await self.extract_dependencies_from_text(
                        content, service.name, f"code:{code_file.name}"
                    )
                    dependencies.extend(deps)
                    
                except Exception:
                    continue
        
        return dependencies
    
    async def analyze_docker_dependencies(self, service: ServiceInfo) -> List[ServiceDependency]:
        """Analyze Docker files for dependencies"""
        dependencies = []
        service_path = Path(f"/home/activeloguser/activelog/services/{service.name}")
        
        docker_files = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
        
        for docker_file in docker_files:
            docker_path = service_path / docker_file
            if docker_path.exists():
                try:
                    with open(docker_path, 'r') as f:
                        content = f.read()
                    
                    # Extract service dependencies from docker-compose
                    if "docker-compose" in docker_file:
                        deps = await self.extract_docker_compose_dependencies(
                            content, service.name
                        )
                        dependencies.extend(deps)
                    
                    # Extract external dependencies from Dockerfile
                    else:
                        deps = await self.extract_dockerfile_dependencies(
                            content, service.name
                        )
                        dependencies.extend(deps)
                        
                except Exception:
                    continue
        
        return dependencies
    
    async def analyze_package_dependencies(self, service: ServiceInfo) -> List[ServiceDependency]:
        """Analyze package.json or requirements.txt for library dependencies"""
        dependencies = []
        service_path = Path(f"/home/activeloguser/activelog/services/{service.name}")
        
        # Check package.json (Node.js)
        package_json = service_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                
                # Regular dependencies
                for dep_name, version in package_data.get("dependencies", {}).items():
                    # Filter out ActiveLog internal dependencies
                    if "activelog" in dep_name.lower() or dep_name in self.discovery.services:
                        target_service = self.resolve_service_name(dep_name)
                        if target_service:
                            dependencies.append(ServiceDependency(
                                source_service=service.name,
                                target_service=target_service,
                                dependency_type=DependencyType.LIBRARY,
                                strength=DependencyStrength.IMPORTANT,
                                description=f"NPM dependency: {dep_name}@{version}",
                                discovered_method="package.json",
                                confidence=0.9
                            ))
                
            except Exception:
                pass
        
        # Check requirements.txt (Python)
        requirements_txt = service_path / "requirements.txt"
        if requirements_txt.exists():
            try:
                with open(requirements_txt, 'r') as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name
                        package_name = line.split('==')[0].split('>=')[0].split('<=')[0]
                        
                        # Check if it's an ActiveLog service
                        if "activelog" in package_name.lower():
                            target_service = self.resolve_service_name(package_name)
                            if target_service:
                                dependencies.append(ServiceDependency(
                                    source_service=service.name,
                                    target_service=target_service,
                                    dependency_type=DependencyType.LIBRARY,
                                    strength=DependencyStrength.IMPORTANT,
                                    description=f"Python dependency: {line}",
                                    discovered_method="requirements.txt",
                                    confidence=0.9
                                ))
            except Exception:
                pass
        
        return dependencies
    
    async def analyze_environment_dependencies(self, service: ServiceInfo) -> List[ServiceDependency]:
        """Analyze environment variables for service dependencies"""
        dependencies = []
        service_path = Path(f"/home/activeloguser/activelog/services/{service.name}")
        
        env_files = [".env", ".env.local", ".env.production", ".env.development"]
        
        for env_file in env_files:
            env_path = service_path / env_file
            if env_path.exists():
                try:
                    with open(env_path, 'r') as f:
                        lines = f.readlines()
                    
                    for line in lines:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            
                            # Check for service URLs in environment variables
                            if any(keyword in key.upper() for keyword in ['URL', 'HOST', 'ENDPOINT', 'SERVICE']):
                                deps = await self.extract_dependencies_from_text(
                                    value, service.name, f"env:{key}"
                                )
                                dependencies.extend(deps)
                
                except Exception:
                    continue
        
        return dependencies
    
    async def extract_dependencies_from_text(self, text: str, source_service: str, source_context: str) -> List[ServiceDependency]:
        """Extract dependencies from text using patterns"""
        dependencies = []
        
        for dep_type, patterns in self.dependency_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[1] if len(match) > 1 else ""
                    
                    if match:
                        # Try to resolve to a known service
                        target_service = await self.resolve_dependency_target(match, dep_type)
                        
                        if target_service:
                            strength = await self.infer_dependency_strength(text, match, dep_type)
                            confidence = await self.calculate_confidence(match, dep_type, source_context)
                            
                            dependencies.append(ServiceDependency(
                                source_service=source_service,
                                target_service=target_service,
                                dependency_type=dep_type,
                                strength=strength,
                                description=f"Dependency found via {source_context}",
                                discovered_method=source_context,
                                confidence=confidence,
                                metadata={"pattern_match": match}
                            ))
        
        return dependencies
    
    async def extract_docker_compose_dependencies(self, content: str, source_service: str) -> List[ServiceDependency]:
        """Extract service dependencies from docker-compose.yml"""
        dependencies = []
        
        try:
            import yaml
            compose_data = yaml.safe_load(content)
            
            if "services" in compose_data:
                for service_name, service_config in compose_data["services"].items():
                    if service_name != source_service:
                        # This is a dependency
                        dependencies.append(ServiceDependency(
                            source_service=source_service,
                            target_service=service_name,
                            dependency_type=DependencyType.HTTP_API,
                            strength=DependencyStrength.IMPORTANT,
                            description=f"Docker Compose service dependency",
                            discovered_method="docker-compose.yml",
                            confidence=0.95
                        ))
                    
                    # Check for depends_on
                    if "depends_on" in service_config:
                        for dep_service in service_config["depends_on"]:
                            dependencies.append(ServiceDependency(
                                source_service=service_name,
                                target_service=dep_service,
                                dependency_type=DependencyType.HTTP_API,
                                strength=DependencyStrength.CRITICAL,
                                description="Explicit Docker Compose dependency",
                                discovered_method="docker-compose:depends_on",
                                confidence=1.0
                            ))
        
        except Exception:
            pass
        
        return dependencies
    
    async def extract_dockerfile_dependencies(self, content: str, source_service: str) -> List[ServiceDependency]:
        """Extract dependencies from Dockerfile"""
        dependencies = []
        
        # Look for base images and external services
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('FROM'):
                # Base image dependency
                image = line.split(' ', 1)[1].split(':')[0]
                if 'activelog' in image:
                    target = self.resolve_service_name(image)
                    if target:
                        dependencies.append(ServiceDependency(
                            source_service=source_service,
                            target_service=target,
                            dependency_type=DependencyType.EXTERNAL_SERVICE,
                            strength=DependencyStrength.CRITICAL,
                            description=f"Docker base image: {image}",
                            discovered_method="dockerfile:FROM",
                            confidence=0.8
                        ))
        
        return dependencies
    
    async def resolve_dependency_target(self, match: str, dep_type: DependencyType) -> Optional[str]:
        """Resolve a dependency match to a known service name"""
        # Direct service name match
        if match in self.discovery.services:
            return match
        
        # Try to find service by partial match
        for service_name in self.discovery.services.keys():
            if service_name.replace('-', '').replace('_', '').lower() in match.lower():
                return service_name
            if match.replace('-', '').replace('_', '').lower() in service_name.lower():
                return service_name
        
        # For localhost URLs, try to match by port
        if "localhost" in match or "127.0.0.1" in match:
            port_match = re.search(r':(\d+)', match)
            if port_match:
                port = int(port_match.group(1))
                for service_name, service in self.discovery.services.items():
                    if service.port == port:
                        return service_name
        
        # If no internal service found, return as external dependency
        if dep_type in [DependencyType.DATABASE, DependencyType.CACHE, DependencyType.QUEUE]:
            return f"external-{dep_type.value}-{hash(match) % 1000}"
        
        return None
    
    def resolve_service_name(self, name: str) -> Optional[str]:
        """Resolve a name to a known service"""
        # Direct match
        if name in self.discovery.services:
            return name
        
        # Fuzzy match
        name_clean = name.replace('-', '').replace('_', '').lower()
        for service_name in self.discovery.services.keys():
            service_clean = service_name.replace('-', '').replace('_', '').lower()
            if name_clean in service_clean or service_clean in name_clean:
                return service_name
        
        return None
    
    async def infer_dependency_strength(self, text: str, match: str, dep_type: DependencyType) -> DependencyStrength:
        """Infer the strength of a dependency"""
        # Look for keywords that indicate strength
        critical_keywords = ['required', 'must', 'essential', 'critical', 'fatal']
        important_keywords = ['important', 'needed', 'depends', 'require']
        optional_keywords = ['optional', 'cache', 'optimization', 'enhancement']
        
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in critical_keywords):
            return DependencyStrength.CRITICAL
        elif any(keyword in text_lower for keyword in important_keywords):
            return DependencyStrength.IMPORTANT
        elif any(keyword in text_lower for keyword in optional_keywords):
            return DependencyStrength.OPTIONAL
        
        # Default based on dependency type
        if dep_type in [DependencyType.DATABASE, DependencyType.QUEUE]:
            return DependencyStrength.CRITICAL
        elif dep_type == DependencyType.HTTP_API:
            return DependencyStrength.IMPORTANT
        else:
            return DependencyStrength.MODERATE
    
    async def calculate_confidence(self, match: str, dep_type: DependencyType, source_context: str) -> float:
        """Calculate confidence score for a dependency"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for explicit configurations
        if "config:" in source_context:
            confidence += 0.3
        elif "docker-compose" in source_context:
            confidence += 0.4
        elif "env:" in source_context:
            confidence += 0.2
        
        # Higher confidence for known service patterns
        if any(service_name in match for service_name in self.discovery.services.keys()):
            confidence += 0.3
        
        # Higher confidence for localhost URLs with known ports
        if "localhost" in match:
            port_match = re.search(r':(\d+)', match)
            if port_match:
                port = int(port_match.group(1))
                if any(service.port == port for service in self.discovery.services.values()):
                    confidence += 0.2
        
        return min(confidence, 1.0)
    
    async def deduplicate_dependencies(self) -> List[ServiceDependency]:
        """Remove duplicate dependencies and merge similar ones"""
        unique_deps = {}
        
        for dep in self.dependencies:
            key = f"{dep.source_service}->{dep.target_service}:{dep.dependency_type.value}"
            
            if key not in unique_deps:
                unique_deps[key] = dep
            else:
                # Merge with existing dependency - keep higher confidence
                existing = unique_deps[key]
                if dep.confidence > existing.confidence:
                    unique_deps[key] = dep
                elif dep.strength.value == "critical" and existing.strength.value != "critical":
                    existing.strength = dep.strength
        
        return list(unique_deps.values())
    
    async def build_dependency_graph(self):
        """Build NetworkX graph from dependencies"""
        self.dependency_graph.clear()
        
        # Add all services as nodes
        for service_name, service_info in self.discovery.services.items():
            self.dependency_graph.add_node(
                service_name,
                service_type=service_info.service_type.value,
                port=service_info.port,
                status=service_info.status.value
            )
        
        # Add dependencies as edges
        for dep in self.dependencies:
            if dep.target_service not in self.dependency_graph:
                # Add external service node
                self.dependency_graph.add_node(
                    dep.target_service,
                    service_type="external",
                    external=True
                )
            
            self.dependency_graph.add_edge(
                dep.source_service,
                dep.target_service,
                dependency_type=dep.dependency_type.value,
                strength=dep.strength.value,
                confidence=dep.confidence,
                description=dep.description
            )
    
    async def analyze_dependencies(self) -> DependencyAnalysis:
        """Perform comprehensive dependency analysis"""
        if not self.dependencies:
            await self.discover_all_dependencies()
        
        # Find circular dependencies
        circular_deps = list(nx.simple_cycles(self.dependency_graph))
        
        # Find critical path services (most dependencies)
        in_degrees = dict(self.dependency_graph.in_degree())
        critical_path_services = sorted(in_degrees, key=in_degrees.get, reverse=True)[:10]
        
        # Find isolated services (no dependencies)
        isolated_services = [node for node in self.dependency_graph.nodes() 
                           if self.dependency_graph.degree(node) == 0]
        
        # Find bottleneck services (high out-degree)
        out_degrees = dict(self.dependency_graph.out_degree())
        bottleneck_services = [node for node, degree in out_degrees.items() if degree > 5]
        
        # Find single points of failure
        single_points = []
        for node in self.dependency_graph.nodes():
            # Remove node temporarily and check connectivity
            temp_graph = self.dependency_graph.copy()
            temp_graph.remove_node(node)
            
            # If removing this node significantly reduces connectivity, it's a SPOF
            if not nx.is_weakly_connected(temp_graph) and nx.is_weakly_connected(self.dependency_graph):
                single_points.append(node)
        
        # Calculate dependency depth (longest path)
        try:
            dependency_depth = nx.dag_longest_path_length(self.dependency_graph)
        except:
            dependency_depth = 0
        
        # Identify clusters
        clusters = await self.identify_dependency_clusters()
        
        analysis = DependencyAnalysis(
            total_services=len(self.discovery.services),
            total_dependencies=len(self.dependencies),
            dependency_depth=dependency_depth,
            circular_dependencies=circular_deps,
            critical_path_services=critical_path_services,
            isolated_services=isolated_services,
            dependency_clusters=clusters,
            bottleneck_services=bottleneck_services,
            single_points_of_failure=single_points
        )
        
        self.analysis_cache = analysis
        self.last_analysis = datetime.now()
        
        return analysis
    
    async def identify_dependency_clusters(self) -> List[DependencyCluster]:
        """Identify clusters of tightly coupled services"""
        clusters = []
        
        # Use community detection algorithms
        try:
            # Convert to undirected graph for community detection
            undirected_graph = self.dependency_graph.to_undirected()
            
            # Find communities using greedy modularity
            import networkx.algorithms.community as nx_comm
            communities = nx_comm.greedy_modularity_communities(undirected_graph)
            
            for i, community in enumerate(communities):
                if len(community) > 1:  # Only consider clusters with multiple services
                    cluster_services = list(community)
                    
                    # Analyze internal vs external dependencies
                    internal_deps = [dep for dep in self.dependencies 
                                   if dep.source_service in cluster_services and dep.target_service in cluster_services]
                    
                    external_deps = [dep for dep in self.dependencies 
                                   if dep.source_service in cluster_services and dep.target_service not in cluster_services]
                    
                    # Determine cluster type based on service types
                    cluster_type = await self.infer_cluster_type(cluster_services)
                    
                    # Determine criticality
                    criticality = DependencyStrength.MODERATE
                    if any(dep.strength == DependencyStrength.CRITICAL for dep in internal_deps):
                        criticality = DependencyStrength.CRITICAL
                    elif any(dep.strength == DependencyStrength.IMPORTANT for dep in internal_deps):
                        criticality = DependencyStrength.IMPORTANT
                    
                    clusters.append(DependencyCluster(
                        cluster_id=f"cluster_{i}",
                        name=f"{cluster_type.title()} Cluster {i+1}",
                        services=cluster_services,
                        cluster_type=cluster_type,
                        internal_dependencies=internal_deps,
                        external_dependencies=external_deps,
                        criticality=criticality,
                        description=f"Cluster of {len(cluster_services)} {cluster_type} services"
                    ))
        
        except Exception as e:
            # Fallback: simple clustering by service type
            service_type_clusters = {}
            for service_name, service_info in self.discovery.services.items():
                service_type = service_info.service_type.value
                if service_type not in service_type_clusters:
                    service_type_clusters[service_type] = []
                service_type_clusters[service_type].append(service_name)
            
            for i, (service_type, services) in enumerate(service_type_clusters.items()):
                if len(services) > 1:
                    internal_deps = [dep for dep in self.dependencies 
                                   if dep.source_service in services and dep.target_service in services]
                    external_deps = [dep for dep in self.dependencies 
                                   if dep.source_service in services and dep.target_service not in services]
                    
                    clusters.append(DependencyCluster(
                        cluster_id=f"type_cluster_{i}",
                        name=f"{service_type.title()} Services",
                        services=services,
                        cluster_type=service_type,
                        internal_dependencies=internal_deps,
                        external_dependencies=external_deps,
                        criticality=DependencyStrength.MODERATE
                    ))
        
        return clusters
    
    async def infer_cluster_type(self, services: List[str]) -> str:
        """Infer the type of a service cluster"""
        service_types = [self.discovery.services[service].service_type.value 
                        for service in services if service in self.discovery.services]
        
        # Count service types
        type_counts = {}
        for service_type in service_types:
            type_counts[service_type] = type_counts.get(service_type, 0) + 1
        
        # Return most common type
        if type_counts:
            return max(type_counts, key=type_counts.get)
        
        # Infer from service names
        if any("ml" in service or "ai" in service for service in services):
            return "ml_pipeline"
        elif any("user" in service or "auth" in service for service in services):
            return "user_management"
        elif any("data" in service or "sync" in service for service in services):
            return "data_processing"
        else:
            return "general"
    
    def get_service_dependencies(self, service_name: str, include_transitive: bool = False) -> Dict[str, Any]:
        """Get all dependencies for a specific service"""
        if service_name not in self.discovery.services:
            return {"error": f"Service {service_name} not found"}
        
        direct_deps = [dep for dep in self.dependencies if dep.source_service == service_name]
        dependents = [dep for dep in self.dependencies if dep.target_service == service_name]
        
        result = {
            "service_name": service_name,
            "direct_dependencies": [asdict(dep) for dep in direct_deps],
            "dependent_services": [asdict(dep) for dep in dependents],
            "dependency_count": len(direct_deps),
            "dependent_count": len(dependents)
        }
        
        if include_transitive:
            # Find transitive dependencies using graph traversal
            transitive_deps = set()
            
            def traverse_deps(current_service, visited):
                if current_service in visited:
                    return
                visited.add(current_service)
                
                for dep in self.dependencies:
                    if dep.source_service == current_service:
                        transitive_deps.add(dep.target_service)
                        traverse_deps(dep.target_service, visited)
            
            traverse_deps(service_name, set())
            result["transitive_dependencies"] = list(transitive_deps)
        
        return result
    
    def generate_dependency_report(self) -> Dict[str, Any]:
        """Generate comprehensive dependency report"""
        if not self.analysis_cache:
            return {"error": "No analysis available. Run analyze_dependencies() first."}
        
        analysis = self.analysis_cache
        
        # Service dependency statistics
        dependency_stats = {}
        for service_name in self.discovery.services.keys():
            deps_out = len([d for d in self.dependencies if d.source_service == service_name])
            deps_in = len([d for d in self.dependencies if d.target_service == service_name])
            
            dependency_stats[service_name] = {
                "dependencies_out": deps_out,
                "dependencies_in": deps_in,
                "total_connections": deps_out + deps_in
            }
        
        # Dependency type breakdown
        type_breakdown = {}
        for dep in self.dependencies:
            dep_type = dep.dependency_type.value
            type_breakdown[dep_type] = type_breakdown.get(dep_type, 0) + 1
        
        # Strength breakdown
        strength_breakdown = {}
        for dep in self.dependencies:
            strength = dep.strength.value
            strength_breakdown[strength] = strength_breakdown.get(strength, 0) + 1
        
        return {
            "analysis_summary": {
                "total_services": analysis.total_services,
                "total_dependencies": analysis.total_dependencies,
                "dependency_depth": analysis.dependency_depth,
                "circular_dependencies_count": len(analysis.circular_dependencies),
                "isolated_services_count": len(analysis.isolated_services),
                "clusters_count": len(analysis.dependency_clusters),
                "bottlenecks_count": len(analysis.bottleneck_services),
                "single_points_of_failure_count": len(analysis.single_points_of_failure)
            },
            "dependency_statistics": dependency_stats,
            "dependency_type_breakdown": type_breakdown,
            "dependency_strength_breakdown": strength_breakdown,
            "critical_issues": {
                "circular_dependencies": analysis.circular_dependencies,
                "single_points_of_failure": analysis.single_points_of_failure,
                "isolated_services": analysis.isolated_services,
                "bottleneck_services": analysis.bottleneck_services
            },
            "clusters": [asdict(cluster) for cluster in analysis.dependency_clusters],
            "recommendations": self.generate_recommendations(analysis)
        }
    
    def generate_recommendations(self, analysis: DependencyAnalysis) -> List[str]:
        """Generate recommendations based on dependency analysis"""
        recommendations = []
        
        if analysis.circular_dependencies:
            recommendations.append(f"Address {len(analysis.circular_dependencies)} circular dependencies to improve system stability")
        
        if analysis.single_points_of_failure:
            recommendations.append(f"Implement redundancy for {len(analysis.single_points_of_failure)} single points of failure")
        
        if analysis.isolated_services:
            recommendations.append(f"Review {len(analysis.isolated_services)} isolated services for potential integration opportunities")
        
        if analysis.bottleneck_services:
            recommendations.append(f"Consider load balancing or service splitting for {len(analysis.bottleneck_services)} bottleneck services")
        
        if analysis.dependency_depth > 10:
            recommendations.append("Consider flattening deep dependency chains to reduce complexity")
        
        # Low confidence dependencies
        low_confidence_deps = [d for d in self.dependencies if d.confidence < 0.6]
        if low_confidence_deps:
            recommendations.append(f"Verify {len(low_confidence_deps)} low-confidence dependencies")
        
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mapper state to dictionary"""
        return {
            "total_dependencies": len(self.dependencies),
            "last_analysis": self.last_analysis.isoformat() if self.last_analysis else None,
            "graph_info": {
                "nodes": self.dependency_graph.number_of_nodes(),
                "edges": self.dependency_graph.number_of_edges(),
                "is_directed": self.dependency_graph.is_directed()
            },
            "analysis": asdict(self.analysis_cache) if self.analysis_cache else None
        }

# Example usage
async def main():
    discovery = ServiceDiscovery()
    mapper = DependencyMapper(discovery)
    
    print("Discovering service dependencies...")
    dependencies = await mapper.discover_all_dependencies()
    print(f"Found {len(dependencies)} dependencies")
    
    print("Analyzing dependency structure...")
    analysis = await mapper.analyze_dependencies()
    
    print(f"Analysis complete:")
    print(f"- {analysis.total_services} services")
    print(f"- {analysis.total_dependencies} dependencies")
    print(f"- {len(analysis.circular_dependencies)} circular dependencies")
    print(f"- {len(analysis.single_points_of_failure)} single points of failure")
    
    # Generate report
    report = mapper.generate_dependency_report()
    print("\nRecommendations:")
    for rec in report["recommendations"]:
        print(f"- {rec}")

if __name__ == "__main__":
    asyncio.run(main())