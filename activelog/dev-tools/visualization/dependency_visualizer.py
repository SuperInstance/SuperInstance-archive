#!/usr/bin/env python3
"""
ActiveLog Service Dependency Visualizer
Analyzes and visualizes service dependencies, imports, and architecture.
"""

import os
import sys
import ast
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

# Optional dependencies for visualization
try:
    import graphviz
    HAS_GRAPHVIZ = True
except ImportError:
    HAS_GRAPHVIZ = False

try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Information about a service."""
    name: str
    path: Path
    port: Optional[int] = None
    description: str = ""
    dependencies: Set[str] = field(default_factory=set)
    imports: Set[str] = field(default_factory=set)
    exports: Set[str] = field(default_factory=set)
    endpoints: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    database_tables: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    lines_of_code: int = 0
    test_coverage: Optional[float] = None


@dataclass
class DependencyEdge:
    """Represents a dependency between services."""
    source: str
    target: str
    type: str  # 'import', 'api_call', 'database', 'config'
    weight: int = 1
    details: str = ""


class DependencyAnalyzer:
    """Analyzes service dependencies and architecture."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.services: Dict[str, ServiceInfo] = {}
        self.dependencies: List[DependencyEdge] = []
        self.external_dependencies: Set[str] = set()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
    
    def analyze_project(self) -> Dict[str, Any]:
        """Analyze the entire project for dependencies."""
        logger.info("🔍 Analyzing ActiveLog project dependencies...")
        
        # Discover services
        self._discover_services()
        
        # Analyze each service
        for service_name, service_info in self.services.items():
            logger.info(f"Analyzing service: {service_name}")
            self._analyze_service(service_info)
        
        # Analyze cross-service dependencies
        self._analyze_cross_dependencies()
        
        # Load configuration dependencies
        self._analyze_config_dependencies()
        
        # Analyze database dependencies
        self._analyze_database_dependencies()
        
        logger.info(f"✅ Analysis complete: {len(self.services)} services, {len(self.dependencies)} dependencies")
        
        return self._generate_analysis_report()
    
    def _discover_services(self):
        """Discover all services in the project."""
        # Check services directory
        services_dir = self.project_root / "services"
        if services_dir.exists():
            for service_path in services_dir.iterdir():
                if service_path.is_dir() and not service_path.name.startswith('.'):
                    service_name = service_path.name
                    self.services[service_name] = ServiceInfo(
                        name=service_name,
                        path=service_path
                    )
        
        # Check for API gateway
        api_gateway = self.project_root / "api_gateway"
        if api_gateway.exists():
            self.services["api_gateway"] = ServiceInfo(
                name="api_gateway",
                path=api_gateway,
                port=8000,
                description="Main API Gateway"
            )
        
        # Load service info from CLI config
        self._load_service_config()
    
    def _load_service_config(self):
        """Load service configuration from CLI config."""
        if not HAS_YAML:
            return
        
        cli_config = self.project_root / "dev-tools" / "cli" / "config.yml"
        if not cli_config.exists():
            return
        
        try:
            with open(cli_config) as f:
                config = yaml.safe_load(f)
            
            for service_name, service_config in config.get('services', {}).items():
                if service_name in self.services:
                    service_info = self.services[service_name]
                    service_info.port = service_config.get('port')
                    service_info.description = service_config.get('description', '')
                    
                    # Add configured dependencies
                    deps = service_config.get('dependencies', [])
                    service_info.dependencies.update(deps)
                    
        except Exception as e:
            logger.warning(f"Failed to load CLI config: {e}")
    
    def _analyze_service(self, service_info: ServiceInfo):
        """Analyze a single service for dependencies and structure."""
        service_path = service_info.path
        
        # Analyze Python files
        python_files = list(service_path.rglob("*.py"))
        service_info.lines_of_code = self._count_lines_of_code(python_files)
        
        for py_file in python_files:
            self._analyze_python_file(py_file, service_info)
        
        # Analyze configuration files
        config_files = [
            "config.py", "settings.py", ".env", "requirements.txt",
            "Dockerfile", "docker-compose.yml"
        ]
        
        for config_file in config_files:
            config_path = service_path / config_file
            if config_path.exists():
                service_info.config_files.append(config_file)
                self._analyze_config_file(config_path, service_info)
        
        # Look for API endpoints in FastAPI/Flask apps
        self._discover_endpoints(service_info)
        
        # Discover models
        self._discover_models(service_info)
        
        # Discover database tables
        self._discover_database_tables(service_info)
    
    def _count_lines_of_code(self, python_files: List[Path]) -> int:
        """Count lines of code in Python files."""
        total_lines = 0
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Count non-empty, non-comment lines
                    code_lines = [
                        line.strip() for line in lines 
                        if line.strip() and not line.strip().startswith('#')
                    ]
                    total_lines += len(code_lines)
            except Exception:
                pass
        
        return total_lines
    
    def _analyze_python_file(self, file_path: Path, service_info: ServiceInfo):
        """Analyze a Python file for imports and dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find imports
            try:
                tree = ast.parse(content)
                self._extract_imports_from_ast(tree, service_info)
            except SyntaxError:
                # Fallback to regex parsing
                self._extract_imports_from_regex(content, service_info)
            
            # Look for API calls and external service usage
            self._find_api_calls(content, service_info)
            
        except Exception as e:
            logger.debug(f"Error analyzing {file_path}: {e}")
    
    def _extract_imports_from_ast(self, tree: ast.AST, service_info: ServiceInfo):
        """Extract imports using AST parsing."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    service_info.imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    service_info.imports.add(node.module)
                    
                    # Check for internal service imports
                    if self._is_internal_service_import(node.module):
                        self._add_service_dependency(service_info, node.module)
    
    def _extract_imports_from_regex(self, content: str, service_info: ServiceInfo):
        """Extract imports using regex (fallback method)."""
        # Find import statements
        import_patterns = [
            r'^import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
            r'^from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import'
        ]
        
        for line in content.split('\n'):
            line = line.strip()
            for pattern in import_patterns:
                match = re.match(pattern, line)
                if match:
                    module = match.group(1)
                    service_info.imports.add(module)
                    
                    if self._is_internal_service_import(module):
                        self._add_service_dependency(service_info, module)
    
    def _is_internal_service_import(self, module: str) -> bool:
        """Check if an import is from an internal service."""
        # Check if module starts with a known service name
        for service_name in self.services.keys():
            if module.startswith(service_name):
                return True
        
        # Check for common internal patterns
        internal_patterns = [
            'services.',
            'api_gateway.',
            'shared.',
            'common.',
        ]
        
        return any(module.startswith(pattern) for pattern in internal_patterns)
    
    def _add_service_dependency(self, service_info: ServiceInfo, module: str):
        """Add a service dependency."""
        # Extract service name from module
        parts = module.split('.')
        if parts[0] in self.services:
            target_service = parts[0]
            if target_service != service_info.name:
                service_info.dependencies.add(target_service)
                
                # Add dependency edge
                self.dependencies.append(DependencyEdge(
                    source=service_info.name,
                    target=target_service,
                    type='import',
                    details=f"imports {module}"
                ))
    
    def _find_api_calls(self, content: str, service_info: ServiceInfo):
        """Find API calls to other services."""
        # Look for HTTP client usage
        api_patterns = [
            r'requests\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'httpx\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'aiohttp\.ClientSession\(\)\.([a-z]+)\s*\(\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in api_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if len(match.groups()) >= 2:
                    method = match.group(1)
                    url = match.group(2)
                    
                    # Try to identify target service from URL
                    target_service = self._identify_service_from_url(url)
                    if target_service and target_service != service_info.name:
                        service_info.dependencies.add(target_service)
                        
                        self.dependencies.append(DependencyEdge(
                            source=service_info.name,
                            target=target_service,
                            type='api_call',
                            details=f"{method.upper()} {url}"
                        ))
    
    def _identify_service_from_url(self, url: str) -> Optional[str]:
        """Identify target service from URL."""
        # Look for service identifiers in URL
        for service_name in self.services.keys():
            if service_name in url.lower():
                return service_name
        
        # Check for port-based identification
        port_matches = re.findall(r':(\d+)', url)
        if port_matches:
            port = int(port_matches[0])
            for service_name, service_info in self.services.items():
                if service_info.port == port:
                    return service_name
        
        return None
    
    def _analyze_config_file(self, config_path: Path, service_info: ServiceInfo):
        """Analyze configuration files for dependencies."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for database URLs
            db_patterns = [
                r'DATABASE_URL\s*=\s*["\']([^"\']+)["\']',
                r'postgresql://([^/]+)/(\w+)',
                r'redis://([^/]+)',
                r'elasticsearch://([^/]+)',
            ]
            
            for pattern in db_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    # Add database dependency
                    self.dependencies.append(DependencyEdge(
                        source=service_info.name,
                        target="database",
                        type="database",
                        details=match.group(0)
                    ))
            
            # Look for external service configurations
            external_patterns = [
                r'OPENAI_API_KEY',
                r'ANTHROPIC_API_KEY',
                r'AWS_',
                r'SENTRY_DSN',
                r'SMTP_',
            ]
            
            for pattern in external_patterns:
                if re.search(pattern, content):
                    self.external_dependencies.add(pattern)
                    
        except Exception as e:
            logger.debug(f"Error analyzing config {config_path}: {e}")
    
    def _discover_endpoints(self, service_info: ServiceInfo):
        """Discover API endpoints in the service."""
        endpoint_patterns = [
            r'@app\.route\s*\(\s*["\']([^"\']+)["\']',  # Flask
            r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',  # FastAPI
            r'app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',  # FastAPI
        ]
        
        for py_file in service_info.path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in endpoint_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        if len(match.groups()) >= 2:
                            endpoint = match.group(2)
                        else:
                            endpoint = match.group(1)
                        
                        if endpoint not in service_info.endpoints:
                            service_info.endpoints.append(endpoint)
                            
            except Exception:
                pass
    
    def _discover_models(self, service_info: ServiceInfo):
        """Discover data models in the service."""
        model_patterns = [
            r'class\s+(\w+)\s*\(\s*BaseModel\s*\)',  # Pydantic
            r'class\s+(\w+)\s*\(\s*Base\s*\)',  # SQLAlchemy
            r'class\s+(\w+)\s*\(\s*db\.Model\s*\)',  # Flask-SQLAlchemy
        ]
        
        for py_file in service_info.path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in model_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        model_name = match.group(1)
                        if model_name not in service_info.models:
                            service_info.models.append(model_name)
                            
            except Exception:
                pass
    
    def _discover_database_tables(self, service_info: ServiceInfo):
        """Discover database tables used by the service."""
        table_patterns = [
            r'__tablename__\s*=\s*["\']([^"\']+)["\']',
            r'Table\s*\(\s*["\']([^"\']+)["\']',
        ]
        
        for py_file in service_info.path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in table_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        table_name = match.group(1)
                        if table_name not in service_info.database_tables:
                            service_info.database_tables.append(table_name)
                            
            except Exception:
                pass
    
    def _analyze_cross_dependencies(self):
        """Analyze dependencies between services."""
        # Check for circular dependencies
        self._detect_circular_dependencies()
        
        # Calculate dependency metrics
        self._calculate_dependency_metrics()
    
    def _detect_circular_dependencies(self):
        """Detect circular dependencies between services."""
        # Build dependency graph
        graph = defaultdict(list)
        for dep in self.dependencies:
            if dep.source in self.services and dep.target in self.services:
                graph[dep.source].append(dep.target)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph[node]:
                dfs(neighbor, path + [neighbor])
            
            rec_stack.remove(node)
        
        for service in self.services:
            if service not in visited:
                dfs(service, [service])
        
        if cycles:
            logger.warning(f"⚠️  Detected {len(cycles)} circular dependencies:")
            for cycle in cycles:
                logger.warning(f"   {' -> '.join(cycle)}")
    
    def _calculate_dependency_metrics(self):
        """Calculate dependency metrics for services."""
        # Calculate in-degree and out-degree for each service
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        
        for dep in self.dependencies:
            if dep.source in self.services and dep.target in self.services:
                out_degree[dep.source] += 1
                in_degree[dep.target] += 1
        
        # Store metrics
        for service_name, service_info in self.services.items():
            service_info.in_degree = in_degree[service_name]
            service_info.out_degree = out_degree[service_name]
    
    def _analyze_config_dependencies(self):
        """Analyze configuration-based dependencies."""
        # Load docker-compose files
        compose_files = [
            self.project_root / "docker-compose.yml",
            self.project_root / "docker-compose.dev.yml"
        ]
        
        for compose_file in compose_files:
            if compose_file.exists() and HAS_YAML:
                try:
                    with open(compose_file) as f:
                        compose_config = yaml.safe_load(f)
                    
                    services_config = compose_config.get('services', {})
                    for service_name, config in services_config.items():
                        if service_name in self.services:
                            # Add depends_on dependencies
                            depends_on = config.get('depends_on', [])
                            for dep in depends_on:
                                self.dependencies.append(DependencyEdge(
                                    source=service_name,
                                    target=dep,
                                    type='config',
                                    details=f"docker-compose depends_on"
                                ))
                                
                except Exception as e:
                    logger.debug(f"Error analyzing {compose_file}: {e}")
    
    def _analyze_database_dependencies(self):
        """Analyze database dependencies."""
        # Look for migration files
        alembic_dir = self.project_root / "alembic"
        if alembic_dir.exists():
            for service_info in self.services.values():
                self.dependencies.append(DependencyEdge(
                    source=service_info.name,
                    target="postgres",
                    type="database",
                    details="uses shared database"
                ))
    
    def _generate_analysis_report(self) -> Dict[str, Any]:
        """Generate analysis report."""
        return {
            'services': {
                name: {
                    'name': info.name,
                    'path': str(info.path),
                    'port': info.port,
                    'description': info.description,
                    'dependencies': list(info.dependencies),
                    'imports': list(info.imports),
                    'endpoints': info.endpoints,
                    'models': info.models,
                    'database_tables': info.database_tables,
                    'lines_of_code': info.lines_of_code,
                    'config_files': info.config_files
                }
                for name, info in self.services.items()
            },
            'dependencies': [
                {
                    'source': dep.source,
                    'target': dep.target,
                    'type': dep.type,
                    'weight': dep.weight,
                    'details': dep.details
                }
                for dep in self.dependencies
            ],
            'external_dependencies': list(self.external_dependencies),
            'metrics': self._calculate_project_metrics()
        }
    
    def _calculate_project_metrics(self) -> Dict[str, Any]:
        """Calculate project-level metrics."""
        total_services = len(self.services)
        total_dependencies = len(self.dependencies)
        total_loc = sum(info.lines_of_code for info in self.services.values())
        
        # Calculate complexity metrics
        avg_dependencies = total_dependencies / total_services if total_services > 0 else 0
        
        return {
            'total_services': total_services,
            'total_dependencies': total_dependencies,
            'total_lines_of_code': total_loc,
            'average_dependencies_per_service': avg_dependencies,
            'external_dependencies_count': len(self.external_dependencies)
        }


class DependencyVisualizer:
    """Creates visualizations of service dependencies."""
    
    def __init__(self, analysis_data: Dict[str, Any]):
        self.analysis_data = analysis_data
        self.services = analysis_data['services']
        self.dependencies = analysis_data['dependencies']
    
    def create_graphviz_diagram(self, output_file: str = "dependencies.svg"):
        """Create dependency diagram using Graphviz."""
        if not HAS_GRAPHVIZ:
            raise RuntimeError("Graphviz not available. Install with: pip install graphviz")
        
        dot = graphviz.Digraph(comment='ActiveLog Service Dependencies')
        dot.attr(rankdir='TB', size='12,8')
        dot.attr('node', shape='box', style='rounded,filled')
        
        # Color scheme for different service types
        colors = {
            'api_gateway': '#FF6B6B',
            'auth': '#4ECDC4',
            'file': '#45B7D1',
            'ai': '#96CEB4',
            'metadata': '#FFEAA7',
            'analytics': '#DDA0DD',
            'database': '#A8E6CF',
            'external': '#FFB6C1'
        }
        
        # Add service nodes
        for service_name, service_info in self.services.items():
            color = self._get_service_color(service_name, colors)
            label = f"{service_name}\\n({service_info['port']})" if service_info['port'] else service_name
            
            dot.node(service_name, label, fillcolor=color)
        
        # Add database and external nodes
        external_services = set()
        for dep in self.dependencies:
            if dep['target'] not in self.services:
                external_services.add(dep['target'])
        
        for ext_service in external_services:
            dot.node(ext_service, ext_service, fillcolor=colors.get('external', '#FFB6C1'))
        
        # Add dependency edges
        for dep in self.dependencies:
            style = self._get_edge_style(dep['type'])
            dot.edge(dep['source'], dep['target'], 
                    label=dep['type'], style=style)
        
        # Save diagram
        try:
            dot.render(output_file, format='svg', cleanup=True)
            logger.info(f"✅ Graphviz diagram saved: {output_file}.svg")
        except Exception as e:
            logger.error(f"❌ Failed to save Graphviz diagram: {e}")
    
    def create_networkx_diagram(self, output_file: str = "dependencies.png"):
        """Create dependency diagram using NetworkX and Matplotlib."""
        if not HAS_NETWORKX:
            raise RuntimeError("NetworkX not available. Install with: pip install networkx matplotlib")
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add nodes
        for service_name, service_info in self.services.items():
            G.add_node(service_name, 
                      port=service_info['port'],
                      loc=service_info['lines_of_code'])
        
        # Add edges
        for dep in self.dependencies:
            G.add_edge(dep['source'], dep['target'], 
                      type=dep['type'], weight=dep['weight'])
        
        # Create layout
        plt.figure(figsize=(15, 10))
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # Draw nodes
        node_colors = [self._get_node_color(node) for node in G.nodes()]
        node_sizes = [max(300, self.services.get(node, {}).get('lines_of_code', 0) / 10) 
                     for node in G.nodes()]
        
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                              node_size=node_sizes, alpha=0.8)
        
        # Draw edges
        edge_colors = [self._get_edge_color(G[u][v]['type']) 
                      for u, v in G.edges()]
        
        nx.draw_networkx_edges(G, pos, edge_color=edge_colors, 
                              arrows=True, arrowsize=20, alpha=0.6)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
        
        # Add legend
        self._add_legend()
        
        plt.title("ActiveLog Service Dependencies", size=16, weight='bold')
        plt.axis('off')
        plt.tight_layout()
        
        try:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            logger.info(f"✅ NetworkX diagram saved: {output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save NetworkX diagram: {e}")
        
        plt.close()
    
    def create_html_report(self, output_file: str = "dependencies.html"):
        """Create interactive HTML report."""
        html_content = self._generate_html_report()
        
        try:
            with open(output_file, 'w') as f:
                f.write(html_content)
            logger.info(f"✅ HTML report saved: {output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save HTML report: {e}")
    
    def _get_service_color(self, service_name: str, colors: Dict[str, str]) -> str:
        """Get color for service based on its type."""
        for service_type, color in colors.items():
            if service_type in service_name.lower():
                return color
        return '#E0E0E0'  # Default gray
    
    def _get_edge_style(self, dep_type: str) -> str:
        """Get edge style based on dependency type."""
        styles = {
            'import': 'solid',
            'api_call': 'dashed',
            'database': 'dotted',
            'config': 'bold'
        }
        return styles.get(dep_type, 'solid')
    
    def _get_node_color(self, node_name: str) -> str:
        """Get node color for NetworkX visualization."""
        if 'api' in node_name.lower():
            return 'lightcoral'
        elif 'auth' in node_name.lower():
            return 'lightblue'
        elif 'file' in node_name.lower():
            return 'lightgreen'
        elif 'ai' in node_name.lower():
            return 'lightyellow'
        elif node_name in ['postgres', 'redis', 'elasticsearch']:
            return 'lightgray'
        else:
            return 'white'
    
    def _get_edge_color(self, dep_type: str) -> str:
        """Get edge color for NetworkX visualization."""
        colors = {
            'import': 'blue',
            'api_call': 'red',
            'database': 'green',
            'config': 'orange'
        }
        return colors.get(dep_type, 'black')
    
    def _add_legend(self):
        """Add legend to matplotlib plot."""
        legend_elements = [
            mpatches.Patch(color='lightcoral', label='API Services'),
            mpatches.Patch(color='lightblue', label='Auth Services'),
            mpatches.Patch(color='lightgreen', label='File Services'),
            mpatches.Patch(color='lightyellow', label='AI Services'),
            mpatches.Patch(color='lightgray', label='Databases'),
        ]
        
        plt.legend(handles=legend_elements, loc='upper right')
    
    def _generate_html_report(self) -> str:
        """Generate HTML report content."""
        services_table = self._generate_services_table()
        dependencies_table = self._generate_dependencies_table()
        metrics_section = self._generate_metrics_section()
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ActiveLog Service Dependencies</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .metric {{ display: inline-block; margin: 10px; padding: 20px; 
                         background: #f0f0f0; border-radius: 8px; text-align: center; }}
                .service-card {{ margin: 10px; padding: 15px; border: 1px solid #ccc; 
                               border-radius: 8px; background: #f9f9f9; }}
                .dependency-import {{ color: blue; }}
                .dependency-api {{ color: red; }}
                .dependency-database {{ color: green; }}
                .dependency-config {{ color: orange; }}
            </style>
        </head>
        <body>
            <h1>ActiveLog Service Dependencies Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            {metrics_section}
            
            <h2>Services Overview</h2>
            {services_table}
            
            <h2>Dependencies</h2>
            {dependencies_table}
            
            <h2>Service Details</h2>
            {self._generate_service_details()}
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_services_table(self) -> str:
        """Generate services table HTML."""
        rows = []
        for service_name, service_info in self.services.items():
            deps_count = len(service_info['dependencies'])
            endpoints_count = len(service_info['endpoints'])
            
            rows.append(f"""
                <tr>
                    <td><strong>{service_name}</strong></td>
                    <td>{service_info['port'] or 'N/A'}</td>
                    <td>{service_info['description']}</td>
                    <td>{deps_count}</td>
                    <td>{endpoints_count}</td>
                    <td>{service_info['lines_of_code']}</td>
                </tr>
            """)
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Port</th>
                    <th>Description</th>
                    <th>Dependencies</th>
                    <th>Endpoints</th>
                    <th>Lines of Code</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _generate_dependencies_table(self) -> str:
        """Generate dependencies table HTML."""
        rows = []
        for dep in self.dependencies:
            dep_class = f"dependency-{dep['type']}"
            rows.append(f"""
                <tr>
                    <td>{dep['source']}</td>
                    <td>{dep['target']}</td>
                    <td class="{dep_class}">{dep['type']}</td>
                    <td>{dep['details']}</td>
                </tr>
            """)
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>Source</th>
                    <th>Target</th>
                    <th>Type</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _generate_metrics_section(self) -> str:
        """Generate metrics section HTML."""
        metrics = self.analysis_data['metrics']
        
        return f"""
        <h2>Project Metrics</h2>
        <div>
            <div class="metric">
                <h3>{metrics['total_services']}</h3>
                <p>Total Services</p>
            </div>
            <div class="metric">
                <h3>{metrics['total_dependencies']}</h3>
                <p>Dependencies</p>
            </div>
            <div class="metric">
                <h3>{metrics['total_lines_of_code']:,}</h3>
                <p>Lines of Code</p>
            </div>
            <div class="metric">
                <h3>{metrics['average_dependencies_per_service']:.1f}</h3>
                <p>Avg Dependencies</p>
            </div>
        </div>
        """
    
    def _generate_service_details(self) -> str:
        """Generate detailed service information."""
        details = []
        
        for service_name, service_info in self.services.items():
            endpoints_list = '<br>'.join(service_info['endpoints'][:10])  # Show first 10
            models_list = ', '.join(service_info['models'][:10])
            
            details.append(f"""
                <div class="service-card">
                    <h3>{service_name}</h3>
                    <p><strong>Description:</strong> {service_info['description']}</p>
                    <p><strong>Port:</strong> {service_info['port'] or 'N/A'}</p>
                    <p><strong>Lines of Code:</strong> {service_info['lines_of_code']:,}</p>
                    <p><strong>Dependencies:</strong> {', '.join(service_info['dependencies'])}</p>
                    <p><strong>Endpoints:</strong><br>{endpoints_list}</p>
                    <p><strong>Models:</strong> {models_list}</p>
                </div>
            """)
        
        return ''.join(details)


def main():
    """Main function for dependency visualization."""
    parser = argparse.ArgumentParser(description="ActiveLog Service Dependency Visualizer")
    parser.add_argument('--output', '-o', default='dependencies', help='Output file prefix')
    parser.add_argument('--format', choices=['svg', 'png', 'html', 'json', 'all'], 
                       default='all', help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Find project root
    project_root = Path(__file__).parent.parent.parent
    
    # Analyze dependencies
    analyzer = DependencyAnalyzer(project_root)
    analysis_data = analyzer.analyze_project()
    
    # Save JSON data
    if args.format in ['json', 'all']:
        json_file = f"{args.output}.json"
        with open(json_file, 'w') as f:
            json.dump(analysis_data, f, indent=2, default=str)
        logger.info(f"✅ Analysis data saved: {json_file}")
    
    # Create visualizations
    visualizer = DependencyVisualizer(analysis_data)
    
    if args.format in ['svg', 'all']:
        try:
            visualizer.create_graphviz_diagram(f"{args.output}.svg")
        except RuntimeError as e:
            logger.warning(f"Skipping Graphviz: {e}")
    
    if args.format in ['png', 'all']:
        try:
            visualizer.create_networkx_diagram(f"{args.output}.png")
        except RuntimeError as e:
            logger.warning(f"Skipping NetworkX: {e}")
    
    if args.format in ['html', 'all']:
        visualizer.create_html_report(f"{args.output}.html")
    
    logger.info("🎉 Dependency visualization completed!")


if __name__ == '__main__':
    main()