import json
import asyncio
import aiohttp
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading
import time
import consul
from collections import defaultdict, deque
import numpy as np


class ServiceHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DependencyType(Enum):
    SYNCHRONOUS = "sync"      # Direct API calls
    ASYNCHRONOUS = "async"    # Message queues, events
    DATABASE = "database"     # Database connections
    CACHE = "cache"          # Cache dependencies
    EXTERNAL = "external"     # External services
    STORAGE = "storage"       # File storage, object storage


@dataclass
class ServiceNode:
    name: str
    version: str
    instances: List[str]
    health_status: ServiceHealth
    metadata: Dict[str, Any]
    tags: List[str] = None
    response_time: float = 0.0
    request_rate: float = 0.0
    error_rate: float = 0.0
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ServiceDependency:
    source: str
    target: str
    dependency_type: DependencyType
    request_count: int = 0
    avg_response_time: float = 0.0
    error_count: int = 0
    last_interaction: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count
    
    @property
    def health_score(self) -> float:
        # Calculate health score (0-1) based on error rate and response time
        error_penalty = min(self.error_rate * 2, 1.0)  # Max penalty of 1.0
        response_penalty = min(self.avg_response_time / 5000, 1.0)  # Normalize by 5s
        return max(0.0, 1.0 - error_penalty - (response_penalty * 0.5))


class ServiceTopologyDiscovery:
    """Discover service dependencies and topology"""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.logger = logging.getLogger(__name__)
        self.dependency_map = defaultdict(set)
        self.service_nodes = {}
        self.traffic_analyzer = TrafficAnalyzer()
    
    async def discover_topology(self) -> Tuple[Dict[str, ServiceNode], List[ServiceDependency]]:
        """Discover complete service topology"""
        # Get services from Consul
        services = await self._discover_services_from_consul()
        
        # Analyze traffic patterns
        dependencies = await self._analyze_service_dependencies(services)
        
        # Enrich with metrics
        await self._enrich_with_metrics(services, dependencies)
        
        return services, dependencies
    
    async def _discover_services_from_consul(self) -> Dict[str, ServiceNode]:
        """Discover services from Consul"""
        services = {}
        
        try:
            # Get all services
            consul_services = self.consul.catalog.services()[1]
            
            for service_name, tags in consul_services.items():
                if service_name == "consul":
                    continue
                
                # Get service health
                health_data = self.consul.health.service(service_name)[1]
                
                instances = []
                health_status = ServiceHealth.UNKNOWN
                metadata = {}
                
                for entry in health_data:
                    service_info = entry['Service']
                    checks = entry['Checks']
                    
                    instance_id = service_info['ID']
                    instances.append(instance_id)
                    
                    # Get metadata
                    service_meta = service_info.get('Meta', {})
                    metadata.update(service_meta)
                    
                    # Determine health
                    instance_health = self._determine_health_status(checks)
                    if health_status == ServiceHealth.UNKNOWN or instance_health != ServiceHealth.HEALTHY:
                        health_status = instance_health
                
                service_node = ServiceNode(
                    name=service_name,
                    version=metadata.get('version', '1.0'),
                    instances=instances,
                    health_status=health_status,
                    metadata=metadata,
                    tags=tags
                )
                
                services[service_name] = service_node
            
            self.logger.info(f"Discovered {len(services)} services")
            return services
            
        except Exception as e:
            self.logger.error(f"Error discovering services from Consul: {e}")
            return {}
    
    def _determine_health_status(self, checks: List[Dict]) -> ServiceHealth:
        """Determine health status from Consul checks"""
        if not checks:
            return ServiceHealth.UNKNOWN
        
        has_critical = any(check['Status'] == 'critical' for check in checks)
        has_warning = any(check['Status'] == 'warning' for check in checks)
        
        if has_critical:
            return ServiceHealth.UNHEALTHY
        elif has_warning:
            return ServiceHealth.DEGRADED
        else:
            return ServiceHealth.HEALTHY
    
    async def _analyze_service_dependencies(self, services: Dict[str, ServiceNode]) -> List[ServiceDependency]:
        """Analyze service dependencies from various sources"""
        dependencies = []
        
        # Method 1: From service metadata (dependencies declared in service config)
        dependencies.extend(self._extract_declared_dependencies(services))
        
        # Method 2: From network traffic analysis (if available)
        dependencies.extend(await self._analyze_network_traffic())
        
        # Method 3: From application logs (if available)
        dependencies.extend(await self._analyze_application_logs())
        
        # Method 4: From infrastructure (database connections, etc.)
        dependencies.extend(await self._analyze_infrastructure_dependencies())
        
        return self._deduplicate_dependencies(dependencies)
    
    def _extract_declared_dependencies(self, services: Dict[str, ServiceNode]) -> List[ServiceDependency]:
        """Extract dependencies declared in service metadata"""
        dependencies = []
        
        for service_name, service_node in services.items():
            # Check for dependency metadata
            deps_metadata = service_node.metadata.get('dependencies', '')
            if deps_metadata:
                declared_deps = [dep.strip() for dep in deps_metadata.split(',') if dep.strip()]
                
                for dep_name in declared_deps:
                    if dep_name in services:
                        dependency = ServiceDependency(
                            source=service_name,
                            target=dep_name,
                            dependency_type=DependencyType.SYNCHRONOUS,
                            metadata={'declared': True}
                        )
                        dependencies.append(dependency)
            
            # Check for database dependencies
            db_type = service_node.metadata.get('database', '')
            if db_type:
                dependency = ServiceDependency(
                    source=service_name,
                    target=f"{db_type}-database",
                    dependency_type=DependencyType.DATABASE,
                    metadata={'database_type': db_type}
                )
                dependencies.append(dependency)
            
            # Check for cache dependencies
            cache_type = service_node.metadata.get('cache', '')
            if cache_type:
                dependency = ServiceDependency(
                    source=service_name,
                    target=f"{cache_type}-cache",
                    dependency_type=DependencyType.CACHE,
                    metadata={'cache_type': cache_type}
                )
                dependencies.append(dependency)
        
        return dependencies
    
    async def _analyze_network_traffic(self) -> List[ServiceDependency]:
        """Analyze network traffic patterns (mock implementation)"""
        dependencies = []
        
        # In a real implementation, this would analyze:
        # - Network flow data
        # - Service mesh sidecar metrics
        # - Load balancer logs
        # - API gateway logs
        
        # Mock some common patterns
        common_patterns = [
            ("api-gateway", "user-service", DependencyType.SYNCHRONOUS),
            ("api-gateway", "auth-service", DependencyType.SYNCHRONOUS),
            ("user-service", "notification-service", DependencyType.ASYNCHRONOUS),
            ("order-service", "payment-service", DependencyType.SYNCHRONOUS),
            ("order-service", "inventory-service", DependencyType.SYNCHRONOUS),
        ]
        
        for source, target, dep_type in common_patterns:
            dependency = ServiceDependency(
                source=source,
                target=target,
                dependency_type=dep_type,
                request_count=100,
                avg_response_time=150.0,
                error_count=5,
                metadata={'discovered_from': 'network_traffic'}
            )
            dependencies.append(dependency)
        
        return dependencies
    
    async def _analyze_application_logs(self) -> List[ServiceDependency]:
        """Analyze application logs for dependencies (mock implementation)"""
        dependencies = []
        
        # In a real implementation, this would:
        # - Parse application logs
        # - Look for HTTP requests, database queries
        # - Analyze distributed tracing data
        # - Extract service interaction patterns
        
        return dependencies
    
    async def _analyze_infrastructure_dependencies(self) -> List[ServiceDependency]:
        """Analyze infrastructure-level dependencies"""
        dependencies = []
        
        # Mock common infrastructure dependencies
        infra_deps = [
            ("user-service", "postgres", DependencyType.DATABASE),
            ("user-service", "redis", DependencyType.CACHE),
            ("order-service", "postgres", DependencyType.DATABASE),
            ("notification-service", "rabbitmq", DependencyType.ASYNCHRONOUS),
            ("api-gateway", "external-payment-api", DependencyType.EXTERNAL),
        ]
        
        for source, target, dep_type in infra_deps:
            dependency = ServiceDependency(
                source=source,
                target=target,
                dependency_type=dep_type,
                metadata={'infrastructure': True}
            )
            dependencies.append(dependency)
        
        return dependencies
    
    def _deduplicate_dependencies(self, dependencies: List[ServiceDependency]) -> List[ServiceDependency]:
        """Remove duplicate dependencies and merge information"""
        dep_map = {}
        
        for dep in dependencies:
            key = (dep.source, dep.target)
            
            if key in dep_map:
                # Merge information
                existing = dep_map[key]
                existing.request_count += dep.request_count
                existing.error_count += dep.error_count
                
                # Update response time (weighted average)
                if dep.avg_response_time > 0:
                    if existing.avg_response_time > 0:
                        total_requests = existing.request_count + dep.request_count
                        existing.avg_response_time = (
                            (existing.avg_response_time * existing.request_count +
                             dep.avg_response_time * dep.request_count) / total_requests
                        )
                    else:
                        existing.avg_response_time = dep.avg_response_time
                
                # Merge metadata
                existing.metadata.update(dep.metadata)
            else:
                dep_map[key] = dep
        
        return list(dep_map.values())
    
    async def _enrich_with_metrics(self, services: Dict[str, ServiceNode], 
                                 dependencies: List[ServiceDependency]):
        """Enrich services and dependencies with real-time metrics"""
        # In a real implementation, this would fetch metrics from:
        # - Prometheus/monitoring system
        # - Application performance monitoring tools
        # - Service mesh metrics
        
        # Mock metrics enrichment
        for service_name, service_node in services.items():
            # Mock response time and request rate
            service_node.response_time = np.random.normal(200, 50)  # avg 200ms
            service_node.request_rate = np.random.exponential(10)  # requests/sec
            service_node.error_rate = np.random.beta(1, 20)  # low error rate
        
        for dep in dependencies:
            if dep.request_count == 0:
                dep.request_count = int(np.random.exponential(50))
            if dep.avg_response_time == 0:
                dep.avg_response_time = np.random.normal(150, 30)
            if dep.error_count == 0:
                dep.error_count = max(0, int(np.random.normal(2, 1)))


class TrafficAnalyzer:
    """Analyze traffic patterns between services"""
    
    def __init__(self):
        self.traffic_history = defaultdict(lambda: deque(maxlen=1000))
        self.logger = logging.getLogger(__name__)
    
    def record_request(self, source: str, target: str, response_time: float, success: bool):
        """Record a request between services"""
        timestamp = datetime.now()
        
        self.traffic_history[(source, target)].append({
            'timestamp': timestamp,
            'response_time': response_time,
            'success': success
        })
    
    def get_traffic_stats(self, source: str, target: str, 
                         window_minutes: int = 60) -> Dict[str, Any]:
        """Get traffic statistics for a service pair"""
        key = (source, target)
        if key not in self.traffic_history:
            return {}
        
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_requests = [
            req for req in self.traffic_history[key]
            if req['timestamp'] >= cutoff_time
        ]
        
        if not recent_requests:
            return {}
        
        total_requests = len(recent_requests)
        successful_requests = sum(1 for req in recent_requests if req['success'])
        response_times = [req['response_time'] for req in recent_requests]
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'error_rate': (total_requests - successful_requests) / total_requests,
            'avg_response_time': np.mean(response_times),
            'p95_response_time': np.percentile(response_times, 95),
            'p99_response_time': np.percentile(response_times, 99),
            'request_rate': total_requests / window_minutes  # per minute
        }


class ServiceDependencyVisualizer:
    """Create interactive visualizations of service dependencies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_network_graph(self, services: Dict[str, ServiceNode], 
                           dependencies: List[ServiceDependency]) -> nx.DiGraph:
        """Create NetworkX graph from services and dependencies"""
        G = nx.DiGraph()
        
        # Add nodes
        for service_name, service_node in services.items():
            G.add_node(service_name, **asdict(service_node))
        
        # Add dependency nodes (databases, caches, etc.)
        for dep in dependencies:
            if dep.target not in G:
                # Add infrastructure nodes
                if dep.dependency_type in [DependencyType.DATABASE, DependencyType.CACHE, 
                                         DependencyType.EXTERNAL]:
                    G.add_node(dep.target, 
                             name=dep.target,
                             version="N/A",
                             instances=[],
                             health_status=ServiceHealth.UNKNOWN,
                             metadata={'infrastructure': True},
                             tags=[dep.dependency_type.value])
        
        # Add edges
        for dep in dependencies:
            if dep.source in G and dep.target in G:
                G.add_edge(dep.source, dep.target, **asdict(dep))
        
        return G
    
    def create_plotly_visualization(self, services: Dict[str, ServiceNode], 
                                  dependencies: List[ServiceDependency]) -> go.Figure:
        """Create interactive Plotly visualization"""
        G = self.create_network_graph(services, dependencies)
        
        # Use spring layout for positioning
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # Extract node and edge information
        node_trace = self._create_node_trace(G, pos)
        edge_trace = self._create_edge_trace(G, pos)
        
        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                            title='Service Dependency Graph',
                            titlefont_size=16,
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20,l=5,r=5,t=40),
                            annotations=[ dict(
                                text="Service Mesh Topology",
                                showarrow=False,
                                xref="paper", yref="paper",
                                x=0.005, y=-0.002,
                                xanchor='left', yanchor='bottom',
                                font=dict(color="#888", size=12)
                            )],
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            plot_bgcolor='white'
                        ))
        
        return fig
    
    def _create_node_trace(self, G: nx.DiGraph, pos: Dict) -> go.Scatter:
        """Create node trace for Plotly"""
        node_x = []
        node_y = []
        node_text = []
        node_color = []
        node_size = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Get node attributes
            node_data = G.nodes[node]
            health_status = node_data.get('health_status', ServiceHealth.UNKNOWN)
            
            # Color based on health
            color_map = {
                ServiceHealth.HEALTHY: 'green',
                ServiceHealth.DEGRADED: 'orange',
                ServiceHealth.UNHEALTHY: 'red',
                ServiceHealth.UNKNOWN: 'gray'
            }
            node_color.append(color_map[health_status])
            
            # Size based on number of connections
            adjacencies = list(G.neighbors(node))
            node_size.append(15 + len(adjacencies) * 5)
            
            # Text information
            instances = node_data.get('instances', [])
            version = node_data.get('version', 'N/A')
            
            node_text.append(
                f"{node}<br>"
                f"Version: {version}<br>"
                f"Instances: {len(instances)}<br>"
                f"Health: {health_status.value if hasattr(health_status, 'value') else str(health_status)}<br>"
                f"Connections: {len(adjacencies)}"
            )
        
        return go.Scatter(x=node_x, y=node_y,
                         mode='markers+text',
                         text=[node.replace('-', '<br>') for node in G.nodes()],
                         textposition="middle center",
                         textfont=dict(size=10, color="white"),
                         hovertext=node_text,
                         hoverinfo='text',
                         marker=dict(size=node_size,
                                   color=node_color,
                                   line=dict(width=2, color='black')))
    
    def _create_edge_trace(self, G: nx.DiGraph, pos: Dict) -> go.Scatter:
        """Create edge trace for Plotly"""
        edge_x = []
        edge_y = []
        edge_text = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        return go.Scatter(x=edge_x, y=edge_y,
                         line=dict(width=2, color='#888'),
                         hoverinfo='none',
                         mode='lines')
    
    def create_dependency_matrix(self, services: Dict[str, ServiceNode], 
                               dependencies: List[ServiceDependency]) -> go.Figure:
        """Create dependency matrix heatmap"""
        service_names = list(services.keys())
        
        # Create adjacency matrix
        matrix = np.zeros((len(service_names), len(service_names)))
        
        for dep in dependencies:
            if dep.source in service_names and dep.target in service_names:
                i = service_names.index(dep.source)
                j = service_names.index(dep.target)
                matrix[i][j] = dep.health_score
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
                        z=matrix,
                        x=service_names,
                        y=service_names,
                        colorscale='RdYlGn',
                        text=matrix,
                        texttemplate="%{text:.2f}",
                        textfont={"size": 10}))
        
        fig.update_layout(
            title='Service Dependency Health Matrix',
            xaxis_title='Target Service',
            yaxis_title='Source Service'
        )
        
        return fig
    
    def create_service_health_dashboard(self, services: Dict[str, ServiceNode]) -> go.Figure:
        """Create service health dashboard"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Service Health Distribution', 'Response Time Distribution',
                           'Error Rate by Service', 'Request Rate by Service'),
            specs=[[{"type": "pie"}, {"type": "histogram"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Health distribution
        health_counts = defaultdict(int)
        service_names = []
        response_times = []
        error_rates = []
        request_rates = []
        
        for service_name, service in services.items():
            health_counts[service.health_status.value] += 1
            service_names.append(service_name)
            response_times.append(service.response_time)
            error_rates.append(service.error_rate * 100)  # Convert to percentage
            request_rates.append(service.request_rate)
        
        # Pie chart for health distribution
        fig.add_trace(
            go.Pie(labels=list(health_counts.keys()), 
                  values=list(health_counts.values()),
                  name="Health Status"),
            row=1, col=1
        )
        
        # Histogram for response times
        fig.add_trace(
            go.Histogram(x=response_times, nbinsx=20, name="Response Time"),
            row=1, col=2
        )
        
        # Bar chart for error rates
        fig.add_trace(
            go.Bar(x=service_names, y=error_rates, name="Error Rate %"),
            row=2, col=1
        )
        
        # Bar chart for request rates
        fig.add_trace(
            go.Bar(x=service_names, y=request_rates, name="Request Rate"),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=False, 
                         title_text="Service Mesh Health Dashboard")
        
        return fig
    
    def export_to_graphml(self, services: Dict[str, ServiceNode], 
                         dependencies: List[ServiceDependency], 
                         filename: str = "service_topology.graphml"):
        """Export topology to GraphML format"""
        G = self.create_network_graph(services, dependencies)
        nx.write_graphml(G, filename)
        self.logger.info(f"Exported topology to {filename}")
    
    def export_to_json(self, services: Dict[str, ServiceNode], 
                      dependencies: List[ServiceDependency], 
                      filename: str = "service_topology.json"):
        """Export topology to JSON format"""
        topology = {
            "services": {name: asdict(service) for name, service in services.items()},
            "dependencies": [asdict(dep) for dep in dependencies],
            "generated_at": datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(topology, f, indent=2, default=str)
        
        self.logger.info(f"Exported topology to {filename}")


class ServiceTopologyMonitor:
    """Monitor service topology changes and generate alerts"""
    
    def __init__(self, discovery: ServiceTopologyDiscovery):
        self.discovery = discovery
        self.logger = logging.getLogger(__name__)
        self.previous_topology = None
        self.change_callbacks = []
    
    def add_change_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for topology changes"""
        self.change_callbacks.append(callback)
    
    async def monitor_topology_changes(self, interval_seconds: int = 60):
        """Monitor topology for changes"""
        while True:
            try:
                # Discover current topology
                services, dependencies = await self.discovery.discover_topology()
                
                current_topology = {
                    'services': services,
                    'dependencies': dependencies,
                    'timestamp': datetime.now()
                }
                
                # Compare with previous topology
                if self.previous_topology:
                    changes = self._detect_changes(self.previous_topology, current_topology)
                    
                    if changes:
                        self.logger.info(f"Detected {len(changes)} topology changes")
                        
                        # Notify callbacks
                        for callback in self.change_callbacks:
                            try:
                                callback(changes)
                            except Exception as e:
                                self.logger.error(f"Error in change callback: {e}")
                
                self.previous_topology = current_topology
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error monitoring topology: {e}")
                await asyncio.sleep(interval_seconds)
    
    def _detect_changes(self, previous: Dict, current: Dict) -> Dict[str, List[str]]:
        """Detect changes between topology snapshots"""
        changes = {
            'new_services': [],
            'removed_services': [],
            'new_dependencies': [],
            'removed_dependencies': [],
            'health_changes': []
        }
        
        prev_services = set(previous['services'].keys())
        curr_services = set(current['services'].keys())
        
        # Service changes
        changes['new_services'] = list(curr_services - prev_services)
        changes['removed_services'] = list(prev_services - curr_services)
        
        # Health changes
        for service_name in prev_services & curr_services:
            prev_health = previous['services'][service_name].health_status
            curr_health = current['services'][service_name].health_status
            
            if prev_health != curr_health:
                changes['health_changes'].append(
                    f"{service_name}: {prev_health.value} -> {curr_health.value}"
                )
        
        # Dependency changes
        prev_deps = {(d.source, d.target) for d in previous['dependencies']}
        curr_deps = {(d.source, d.target) for d in current['dependencies']}
        
        changes['new_dependencies'] = [f"{s} -> {t}" for s, t in (curr_deps - prev_deps)]
        changes['removed_dependencies'] = [f"{s} -> {t}" for s, t in (prev_deps - curr_deps)]
        
        # Filter out empty changes
        return {k: v for k, v in changes.items() if v}


# Usage example and main function
async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Initialize components
    topology_discovery = ServiceTopologyDiscovery()
    visualizer = ServiceDependencyVisualizer()
    
    # Discover topology
    services, dependencies = await topology_discovery.discover_topology()
    
    print(f"Discovered {len(services)} services and {len(dependencies)} dependencies")
    
    # Create visualizations
    network_fig = visualizer.create_plotly_visualization(services, dependencies)
    matrix_fig = visualizer.create_dependency_matrix(services, dependencies)
    dashboard_fig = visualizer.create_service_health_dashboard(services)
    
    # Save visualizations
    network_fig.write_html("service_topology.html")
    matrix_fig.write_html("dependency_matrix.html")
    dashboard_fig.write_html("service_dashboard.html")
    
    # Export topology data
    visualizer.export_to_json(services, dependencies)
    visualizer.export_to_graphml(services, dependencies)
    
    print("Visualizations and exports created successfully!")
    
    # Start monitoring (optional)
    # monitor = ServiceTopologyMonitor(topology_discovery)
    # await monitor.monitor_topology_changes()


if __name__ == "__main__":
    asyncio.run(main())