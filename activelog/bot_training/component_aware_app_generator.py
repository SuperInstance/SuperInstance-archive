"""
Component-Aware Application Generator
Advanced system for generating optimized applications with deep SuperInstance component knowledge
"""

import torch
import torch.nn as nn
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import networkx as nx
import numpy as np
from pathlib import Path
import yaml

class ComponentType(Enum):
    AUTHENTICATION = "authentication"
    DATABASE = "database"
    API_SERVICE = "api_service"
    FRONTEND = "frontend"
    CACHING = "caching"
    MONITORING = "monitoring"
    MESSAGING = "messaging"
    FILE_STORAGE = "file_storage"
    AI_SERVICE = "ai_service"
    LOAD_BALANCER = "load_balancer"
    SECURITY_GATEWAY = "security_gateway"
    ANALYTICS = "analytics"

class DeploymentTarget(Enum):
    LOCAL_ONLY = "local_only"
    EDGE_DEVICE = "edge_device"
    HYBRID_CLOUD = "hybrid_cloud"
    FULL_CLOUD = "full_cloud"
    DISTRIBUTED_MESH = "distributed_mesh"

@dataclass
class ComponentMetadata:
    name: str
    type: ComponentType
    version: str
    description: str
    interfaces: List[str]
    dependencies: List[str]
    resource_requirements: Dict[str, float]
    scaling_characteristics: Dict[str, Any]
    security_properties: Dict[str, Any]
    performance_metrics: Dict[str, float]
    compatibility_matrix: Dict[str, float]
    deployment_options: List[DeploymentTarget]

@dataclass
class ApplicationBlueprint:
    name: str
    description: str
    components: List[ComponentMetadata]
    architecture_graph: nx.DiGraph
    deployment_strategy: Dict[str, Any]
    resource_optimization: Dict[str, Any]
    security_configuration: Dict[str, Any]
    performance_targets: Dict[str, float]
    estimated_costs: Dict[str, float]

@dataclass
class GenerationContext:
    user_requirements: Dict[str, Any]
    target_deployment: DeploymentTarget
    performance_constraints: Dict[str, float]
    security_requirements: Dict[str, Any]
    budget_constraints: Dict[str, float]
    existing_infrastructure: Dict[str, Any]

class ComponentCompatibilityPredictor(nn.Module):
    """Neural network for predicting component compatibility and optimal configurations"""
    
    def __init__(self, num_components: int = 50, embedding_dim: int = 128):
        super().__init__()
        
        # Component embeddings
        self.component_embeddings = nn.Embedding(num_components, embedding_dim)
        
        # Context encoder for requirements and constraints
        self.context_encoder = nn.Sequential(
            nn.Linear(256, 512),  # Input context features
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, embedding_dim)
        )
        
        # Compatibility prediction head
        self.compatibility_predictor = nn.Sequential(
            nn.Linear(embedding_dim * 3, 256),  # Component1 + Component2 + Context
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
        
        # Performance impact predictor
        self.performance_predictor = nn.Sequential(
            nn.Linear(embedding_dim * 3, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 5)  # Latency, throughput, cpu, memory, storage impact
        )
        
        # Resource optimization head
        self.resource_optimizer = nn.Sequential(
            nn.Linear(embedding_dim * 2 + 64, 256),  # Components + resource context
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 4)  # CPU, Memory, Storage, Network allocation
        )
    
    def forward(self, component1_ids: torch.Tensor, component2_ids: torch.Tensor,
                context_features: torch.Tensor, resource_context: torch.Tensor = None):
        
        # Get component embeddings
        comp1_emb = self.component_embeddings(component1_ids)
        comp2_emb = self.component_embeddings(component2_ids)
        
        # Encode context
        context_emb = self.context_encoder(context_features)
        
        # Predict compatibility
        compat_input = torch.cat([comp1_emb, comp2_emb, context_emb], dim=-1)
        compatibility = self.compatibility_predictor(compat_input)
        
        # Predict performance impact
        performance = self.performance_predictor(compat_input)
        
        # Resource optimization
        resource_output = None
        if resource_context is not None:
            resource_input = torch.cat([comp1_emb, comp2_emb, resource_context], dim=-1)
            resource_output = self.resource_optimizer(resource_input)
        
        return compatibility, performance, resource_output

class ComponentAwareApplicationGenerator:
    """Main application generation system with deep component knowledge"""
    
    def __init__(self, component_registry_path: str = None):
        self.logger = logging.getLogger(__name__)
        
        # Component knowledge base
        self.component_registry = {}
        self.compatibility_matrix = {}
        self.performance_profiles = {}
        
        # ML models
        self.compatibility_predictor = ComponentCompatibilityPredictor()
        self.component_graph = nx.DiGraph()
        
        # Generation strategies
        self.generation_strategies = {
            'minimal': self._generate_minimal_app,
            'balanced': self._generate_balanced_app,
            'performance': self._generate_performance_optimized_app,
            'cost_optimized': self._generate_cost_optimized_app,
            'security_first': self._generate_security_first_app
        }
        
        # Load component registry
        if component_registry_path:
            self.load_component_registry(component_registry_path)
        else:
            self._initialize_default_registry()
        
        self.logger.info("Component-Aware Application Generator initialized")
    
    def generate_application(self, requirements: Dict[str, Any], 
                           strategy: str = 'balanced') -> ApplicationBlueprint:
        """Generate a complete application blueprint based on requirements"""
        
        self.logger.info(f"Generating application with strategy: {strategy}")
        
        # Create generation context
        context = self._create_generation_context(requirements)
        
        # Select generation strategy
        if strategy not in self.generation_strategies:
            strategy = 'balanced'
        
        generator_func = self.generation_strategies[strategy]
        
        # Generate application blueprint
        blueprint = generator_func(context)
        
        # Optimize the generated blueprint
        optimized_blueprint = self._optimize_blueprint(blueprint, context)
        
        # Validate the blueprint
        validation_result = self._validate_blueprint(optimized_blueprint)
        
        if not validation_result['valid']:
            self.logger.warning(f"Blueprint validation failed: {validation_result['issues']}")
            # Attempt to fix issues
            optimized_blueprint = self._fix_blueprint_issues(optimized_blueprint, validation_result)
        
        self.logger.info(f"Generated application '{optimized_blueprint.name}' "
                        f"with {len(optimized_blueprint.components)} components")
        
        return optimized_blueprint
    
    def analyze_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user requirements and suggest optimal component selections"""
        
        analysis = {
            'required_components': [],
            'optional_components': [],
            'deployment_recommendations': [],
            'performance_predictions': {},
            'cost_estimates': {},
            'security_recommendations': []
        }
        
        # Extract required components based on functional requirements
        if requirements.get('user_authentication', False):
            analysis['required_components'].append('authentication')
        
        if requirements.get('data_persistence', False):
            analysis['required_components'].append('database')
        
        if requirements.get('api_access', False):
            analysis['required_components'].append('api_service')
        
        if requirements.get('web_interface', False):
            analysis['required_components'].append('frontend')
        
        # Analyze performance requirements
        concurrent_users = requirements.get('concurrent_users', 10)
        if concurrent_users > 100:
            analysis['optional_components'].extend(['load_balancer', 'caching'])
        
        if concurrent_users > 1000:
            analysis['optional_components'].extend(['monitoring', 'analytics'])
        
        # Deployment recommendations
        if requirements.get('offline_capable', False):
            analysis['deployment_recommendations'].append(DeploymentTarget.LOCAL_ONLY)
        elif requirements.get('global_scale', False):
            analysis['deployment_recommendations'].append(DeploymentTarget.FULL_CLOUD)
        else:
            analysis['deployment_recommendations'].append(DeploymentTarget.HYBRID_CLOUD)
        
        # Performance predictions using ML models
        analysis['performance_predictions'] = self._predict_performance(
            analysis['required_components'] + analysis['optional_components'],
            requirements
        )
        
        # Cost estimates
        analysis['cost_estimates'] = self._estimate_costs(
            analysis['required_components'] + analysis['optional_components'],
            requirements
        )
        
        # Security recommendations
        if requirements.get('sensitive_data', False):
            analysis['security_recommendations'].extend([
                'security_gateway', 'encryption', 'audit_logging'
            ])
        
        return analysis
    
    def optimize_for_constraints(self, blueprint: ApplicationBlueprint, 
                                constraints: Dict[str, Any]) -> ApplicationBlueprint:
        """Optimize application blueprint for specific constraints"""
        
        optimized = blueprint
        
        # Cost optimization
        if 'max_monthly_cost' in constraints:
            optimized = self._optimize_for_cost(optimized, constraints['max_monthly_cost'])
        
        # Performance optimization
        if 'min_response_time' in constraints:
            optimized = self._optimize_for_performance(optimized, constraints['min_response_time'])
        
        # Resource optimization
        if 'resource_limits' in constraints:
            optimized = self._optimize_for_resources(optimized, constraints['resource_limits'])
        
        # Security optimization
        if 'security_level' in constraints:
            optimized = self._optimize_for_security(optimized, constraints['security_level'])
        
        return optimized
    
    def _create_generation_context(self, requirements: Dict[str, Any]) -> GenerationContext:
        """Create generation context from requirements"""
        
        # Determine target deployment
        target_deployment = DeploymentTarget.HYBRID_CLOUD
        if requirements.get('offline_only', False):
            target_deployment = DeploymentTarget.LOCAL_ONLY
        elif requirements.get('cloud_native', False):
            target_deployment = DeploymentTarget.FULL_CLOUD
        
        # Extract performance constraints
        performance_constraints = {
            'max_response_time': requirements.get('max_response_time', 500),
            'min_throughput': requirements.get('min_throughput', 100),
            'max_cpu_usage': requirements.get('max_cpu_usage', 80),
            'max_memory_usage': requirements.get('max_memory_usage', 80)
        }
        
        # Extract security requirements
        security_requirements = {
            'encryption_required': requirements.get('encryption_required', False),
            'audit_logging': requirements.get('audit_logging', False),
            'access_control_level': requirements.get('access_control_level', 'basic')
        }
        
        # Budget constraints
        budget_constraints = {
            'max_monthly_cost': requirements.get('max_monthly_cost', 100),
            'max_setup_cost': requirements.get('max_setup_cost', 500)
        }
        
        return GenerationContext(
            user_requirements=requirements,
            target_deployment=target_deployment,
            performance_constraints=performance_constraints,
            security_requirements=security_requirements,
            budget_constraints=budget_constraints,
            existing_infrastructure=requirements.get('existing_infrastructure', {})
        )
    
    def _generate_minimal_app(self, context: GenerationContext) -> ApplicationBlueprint:
        """Generate minimal viable application"""
        
        required_components = []
        
        # Always include core components for authenticated apps
        if not context.user_requirements.get('authentication_optional', False):
            required_components.append(self._get_component_by_type(ComponentType.AUTHENTICATION))
        
        # Add essential components based on requirements
        if context.user_requirements.get('data_persistence', False):
            required_components.append(self._get_component_by_type(ComponentType.DATABASE))
        
        if context.user_requirements.get('api_access', False):
            required_components.append(self._get_component_by_type(ComponentType.API_SERVICE))
        
        if context.user_requirements.get('web_interface', False):
            required_components.append(self._get_component_by_type(ComponentType.FRONTEND))
        
        # Create minimal architecture
        architecture = self._create_minimal_architecture(required_components)
        
        return ApplicationBlueprint(
            name=f"Minimal {context.user_requirements.get('app_name', 'Application')}",
            description="Minimal viable application with essential components only",
            components=required_components,
            architecture_graph=architecture,
            deployment_strategy=self._create_minimal_deployment_strategy(context),
            resource_optimization=self._create_minimal_resource_config(),
            security_configuration=self._create_basic_security_config(),
            performance_targets=self._create_basic_performance_targets(),
            estimated_costs=self._estimate_minimal_costs(required_components)
        )
    
    def _generate_balanced_app(self, context: GenerationContext) -> ApplicationBlueprint:
        """Generate balanced application with good performance/cost ratio"""
        
        components = []
        
        # Core components
        if not context.user_requirements.get('authentication_optional', False):
            components.append(self._get_component_by_type(ComponentType.AUTHENTICATION))
        
        components.append(self._get_component_by_type(ComponentType.DATABASE))
        components.append(self._get_component_by_type(ComponentType.API_SERVICE))
        
        if context.user_requirements.get('web_interface', True):
            components.append(self._get_component_by_type(ComponentType.FRONTEND))
        
        # Performance enhancing components
        concurrent_users = context.user_requirements.get('concurrent_users', 100)
        if concurrent_users > 50:
            components.append(self._get_component_by_type(ComponentType.CACHING))
        
        if concurrent_users > 200:
            components.append(self._get_component_by_type(ComponentType.LOAD_BALANCER))
        
        # Monitoring for production apps
        if context.target_deployment != DeploymentTarget.LOCAL_ONLY:
            components.append(self._get_component_by_type(ComponentType.MONITORING))
        
        # AI services if requested
        if context.user_requirements.get('ai_features', False):
            components.append(self._get_component_by_type(ComponentType.AI_SERVICE))
        
        # Create balanced architecture
        architecture = self._create_balanced_architecture(components)
        
        return ApplicationBlueprint(
            name=f"Balanced {context.user_requirements.get('app_name', 'Application')}",
            description="Well-balanced application with optimal performance/cost ratio",
            components=components,
            architecture_graph=architecture,
            deployment_strategy=self._create_balanced_deployment_strategy(context),
            resource_optimization=self._create_balanced_resource_config(),
            security_configuration=self._create_standard_security_config(),
            performance_targets=self._create_balanced_performance_targets(),
            estimated_costs=self._estimate_balanced_costs(components)
        )
    
    def _generate_performance_optimized_app(self, context: GenerationContext) -> ApplicationBlueprint:
        """Generate performance-optimized application"""
        
        components = []
        
        # High-performance core components
        components.append(self._get_component_by_type(ComponentType.AUTHENTICATION))
        components.append(self._get_component_by_type(ComponentType.DATABASE))
        components.append(self._get_component_by_type(ComponentType.API_SERVICE))
        components.append(self._get_component_by_type(ComponentType.FRONTEND))
        
        # Performance critical components
        components.append(self._get_component_by_type(ComponentType.CACHING))
        components.append(self._get_component_by_type(ComponentType.LOAD_BALANCER))
        
        # Advanced performance components
        if context.user_requirements.get('real_time_features', False):
            components.append(self._get_component_by_type(ComponentType.MESSAGING))
        
        # Always include monitoring for performance optimization
        components.append(self._get_component_by_type(ComponentType.MONITORING))
        components.append(self._get_component_by_type(ComponentType.ANALYTICS))
        
        # Create performance-optimized architecture
        architecture = self._create_performance_architecture(components)
        
        return ApplicationBlueprint(
            name=f"Performance-Optimized {context.user_requirements.get('app_name', 'Application')}",
            description="High-performance application optimized for speed and scalability",
            components=components,
            architecture_graph=architecture,
            deployment_strategy=self._create_performance_deployment_strategy(context),
            resource_optimization=self._create_performance_resource_config(),
            security_configuration=self._create_standard_security_config(),
            performance_targets=self._create_performance_targets(),
            estimated_costs=self._estimate_performance_costs(components)
        )
    
    def _generate_cost_optimized_app(self, context: GenerationContext) -> ApplicationBlueprint:
        """Generate cost-optimized application"""
        
        components = []
        budget = context.budget_constraints.get('max_monthly_cost', 50)
        
        # Essential components only if budget is very low
        if budget < 25:
            if not context.user_requirements.get('authentication_optional', False):
                components.append(self._get_component_by_type(ComponentType.AUTHENTICATION))
            components.append(self._get_component_by_type(ComponentType.DATABASE))
            components.append(self._get_component_by_type(ComponentType.API_SERVICE))
        else:
            # Standard components for higher budgets
            components.append(self._get_component_by_type(ComponentType.AUTHENTICATION))
            components.append(self._get_component_by_type(ComponentType.DATABASE))
            components.append(self._get_component_by_type(ComponentType.API_SERVICE))
            components.append(self._get_component_by_type(ComponentType.FRONTEND))
            
            # Add caching if budget allows
            if budget > 50:
                components.append(self._get_component_by_type(ComponentType.CACHING))
        
        # Create cost-optimized architecture
        architecture = self._create_cost_optimized_architecture(components)
        
        return ApplicationBlueprint(
            name=f"Cost-Optimized {context.user_requirements.get('app_name', 'Application')}",
            description="Cost-efficient application designed to minimize operational expenses",
            components=components,
            architecture_graph=architecture,
            deployment_strategy=self._create_cost_deployment_strategy(context),
            resource_optimization=self._create_cost_resource_config(),
            security_configuration=self._create_basic_security_config(),
            performance_targets=self._create_cost_performance_targets(),
            estimated_costs=self._estimate_cost_optimized_costs(components)
        )
    
    def _generate_security_first_app(self, context: GenerationContext) -> ApplicationBlueprint:
        """Generate security-focused application"""
        
        components = []
        
        # Security-hardened core components
        components.append(self._get_component_by_type(ComponentType.SECURITY_GATEWAY))
        components.append(self._get_component_by_type(ComponentType.AUTHENTICATION))
        components.append(self._get_component_by_type(ComponentType.DATABASE))
        components.append(self._get_component_by_type(ComponentType.API_SERVICE))
        components.append(self._get_component_by_type(ComponentType.FRONTEND))
        
        # Security monitoring and analytics
        components.append(self._get_component_by_type(ComponentType.MONITORING))
        components.append(self._get_component_by_type(ComponentType.ANALYTICS))
        
        # Create security-focused architecture
        architecture = self._create_security_architecture(components)
        
        return ApplicationBlueprint(
            name=f"Security-First {context.user_requirements.get('app_name', 'Application')}",
            description="Security-hardened application with comprehensive protection",
            components=components,
            architecture_graph=architecture,
            deployment_strategy=self._create_security_deployment_strategy(context),
            resource_optimization=self._create_standard_resource_config(),
            security_configuration=self._create_enhanced_security_config(),
            performance_targets=self._create_balanced_performance_targets(),
            estimated_costs=self._estimate_security_costs(components)
        )
    
    def _get_component_by_type(self, component_type: ComponentType) -> ComponentMetadata:
        """Get the best component of a specific type from registry"""
        
        candidates = [comp for comp in self.component_registry.values() 
                     if comp.type == component_type]
        
        if not candidates:
            # Return a default component
            return self._create_default_component(component_type)
        
        # Return the highest-rated component
        return max(candidates, key=lambda c: c.performance_metrics.get('overall_score', 0.5))
    
    def _create_default_component(self, component_type: ComponentType) -> ComponentMetadata:
        """Create a default component of the specified type"""
        
        defaults = {
            ComponentType.AUTHENTICATION: {
                'name': 'JWT Authentication',
                'interfaces': ['REST API', 'WebSocket'],
                'dependencies': ['database'],
                'resources': {'cpu': 0.5, 'memory': 0.5, 'storage': 0.1}
            },
            ComponentType.DATABASE: {
                'name': 'PostgreSQL Database',
                'interfaces': ['SQL', 'Connection Pool'],
                'dependencies': [],
                'resources': {'cpu': 0.3, 'memory': 1.0, 'storage': 5.0}
            },
            ComponentType.API_SERVICE: {
                'name': 'FastAPI Service',
                'interfaces': ['REST API', 'OpenAPI'],
                'dependencies': ['database'],
                'resources': {'cpu': 0.7, 'memory': 0.8, 'storage': 0.2}
            },
            ComponentType.FRONTEND: {
                'name': 'React Frontend',
                'interfaces': ['HTTP', 'WebSocket'],
                'dependencies': ['api_service'],
                'resources': {'cpu': 0.3, 'memory': 0.4, 'storage': 0.5}
            }
        }
        
        default_config = defaults.get(component_type, {
            'name': f'Default {component_type.value}',
            'interfaces': ['HTTP'],
            'dependencies': [],
            'resources': {'cpu': 0.5, 'memory': 0.5, 'storage': 0.3}
        })
        
        return ComponentMetadata(
            name=default_config['name'],
            type=component_type,
            version='1.0.0',
            description=f"Default {component_type.value} component",
            interfaces=default_config['interfaces'],
            dependencies=default_config['dependencies'],
            resource_requirements=default_config['resources'],
            scaling_characteristics={'horizontal': True, 'vertical': True},
            security_properties={'encryption': 'TLS', 'authentication': 'required'},
            performance_metrics={'latency': 50, 'throughput': 1000, 'overall_score': 0.7},
            compatibility_matrix={},
            deployment_options=[DeploymentTarget.HYBRID_CLOUD, DeploymentTarget.LOCAL_ONLY]
        )
    
    def _initialize_default_registry(self):
        """Initialize default component registry"""
        
        default_components = [
            ComponentType.AUTHENTICATION,
            ComponentType.DATABASE,
            ComponentType.API_SERVICE,
            ComponentType.FRONTEND,
            ComponentType.CACHING,
            ComponentType.MONITORING,
            ComponentType.LOAD_BALANCER,
            ComponentType.SECURITY_GATEWAY,
            ComponentType.AI_SERVICE,
            ComponentType.ANALYTICS
        ]
        
        for comp_type in default_components:
            component = self._create_default_component(comp_type)
            self.component_registry[component.name] = component
        
        self.logger.info(f"Initialized default registry with {len(self.component_registry)} components")
    
    def _predict_performance(self, components: List[str], requirements: Dict[str, Any]) -> Dict[str, float]:
        """Predict performance characteristics using ML models"""
        
        # Simplified performance prediction
        base_latency = 100  # ms
        base_throughput = 1000  # req/s
        
        # Adjust based on components
        if 'caching' in components:
            base_latency *= 0.7
            base_throughput *= 1.5
        
        if 'load_balancer' in components:
            base_throughput *= 2.0
        
        if 'monitoring' in components:
            base_latency *= 1.1  # Slight overhead
        
        # Adjust based on requirements
        concurrent_users = requirements.get('concurrent_users', 100)
        if concurrent_users > 1000:
            base_latency *= 1.5
            base_throughput *= 0.8
        
        return {
            'estimated_latency_ms': base_latency,
            'estimated_throughput_rps': base_throughput,
            'estimated_cpu_usage': min(concurrent_users * 0.05, 80),
            'estimated_memory_usage': min(concurrent_users * 0.1, 85)
        }
    
    def _estimate_costs(self, components: List[str], requirements: Dict[str, Any]) -> Dict[str, float]:
        """Estimate operational costs"""
        
        # Base component costs (monthly)
        component_costs = {
            'authentication': 5,
            'database': 15,
            'api_service': 10,
            'frontend': 5,
            'caching': 8,
            'monitoring': 12,
            'load_balancer': 20,
            'security_gateway': 25,
            'ai_service': 30,
            'analytics': 15
        }
        
        total_cost = sum(component_costs.get(comp, 5) for comp in components)
        
        # Scale based on usage
        concurrent_users = requirements.get('concurrent_users', 100)
        if concurrent_users > 500:
            total_cost *= 1.5
        elif concurrent_users > 1000:
            total_cost *= 2.0
        
        return {
            'monthly_operational_cost': total_cost,
            'setup_cost': total_cost * 0.3,
            'scaling_cost_per_100_users': total_cost * 0.1
        }
    
    def _create_minimal_architecture(self, components: List[ComponentMetadata]) -> nx.DiGraph:
        """Create minimal architecture graph"""
        graph = nx.DiGraph()
        
        for comp in components:
            graph.add_node(comp.name, component=comp)
        
        # Add basic dependencies
        for comp in components:
            for dep in comp.dependencies:
                dep_comp = next((c for c in components if c.type.value == dep), None)
                if dep_comp:
                    graph.add_edge(comp.name, dep_comp.name)
        
        return graph
    
    def _create_balanced_architecture(self, components: List[ComponentMetadata]) -> nx.DiGraph:
        """Create balanced architecture with proper layering"""
        graph = nx.DiGraph()
        
        # Add nodes
        for comp in components:
            graph.add_node(comp.name, component=comp, layer=self._determine_layer(comp))
        
        # Add edges based on dependencies and optimal data flow
        self._add_architectural_edges(graph, components, 'balanced')
        
        return graph
    
    def _create_performance_architecture(self, components: List[ComponentMetadata]) -> nx.DiGraph:
        """Create performance-optimized architecture"""
        graph = nx.DiGraph()
        
        # Add nodes with performance attributes
        for comp in components:
            graph.add_node(comp.name, component=comp, 
                          layer=self._determine_layer(comp),
                          performance_critical=self._is_performance_critical(comp))
        
        # Add performance-optimized edges
        self._add_architectural_edges(graph, components, 'performance')
        
        return graph
    
    def _determine_layer(self, component: ComponentMetadata) -> str:
        """Determine architectural layer for component"""
        layer_map = {
            ComponentType.FRONTEND: 'presentation',
            ComponentType.LOAD_BALANCER: 'edge',
            ComponentType.SECURITY_GATEWAY: 'edge',
            ComponentType.API_SERVICE: 'application',
            ComponentType.AI_SERVICE: 'application',
            ComponentType.AUTHENTICATION: 'application',
            ComponentType.CACHING: 'data',
            ComponentType.DATABASE: 'data',
            ComponentType.FILE_STORAGE: 'data',
            ComponentType.MONITORING: 'infrastructure',
            ComponentType.ANALYTICS: 'infrastructure'
        }
        
        return layer_map.get(component.type, 'application')
    
    def _is_performance_critical(self, component: ComponentMetadata) -> bool:
        """Determine if component is performance critical"""
        critical_types = {
            ComponentType.DATABASE,
            ComponentType.CACHING,
            ComponentType.LOAD_BALANCER,
            ComponentType.API_SERVICE
        }
        
        return component.type in critical_types
    
    def _add_architectural_edges(self, graph: nx.DiGraph, 
                                components: List[ComponentMetadata], 
                                strategy: str):
        """Add edges to architecture graph based on strategy"""
        
        # Basic dependency edges
        for comp in components:
            for dep in comp.dependencies:
                dep_comp = next((c for c in components if c.type.value == dep), None)
                if dep_comp:
                    graph.add_edge(comp.name, dep_comp.name, edge_type='dependency')
        
        # Strategy-specific edges
        if strategy == 'performance':
            self._add_performance_edges(graph, components)
        elif strategy == 'balanced':
            self._add_balanced_edges(graph, components)
    
    def _add_performance_edges(self, graph: nx.DiGraph, components: List[ComponentMetadata]):
        """Add performance-optimized edges"""
        # Add caching edges
        cache_comp = next((c for c in components if c.type == ComponentType.CACHING), None)
        if cache_comp:
            api_comps = [c for c in components if c.type == ComponentType.API_SERVICE]
            for api_comp in api_comps:
                graph.add_edge(api_comp.name, cache_comp.name, edge_type='caching')
        
        # Add load balancer edges
        lb_comp = next((c for c in components if c.type == ComponentType.LOAD_BALANCER), None)
        if lb_comp:
            frontend_comps = [c for c in components if c.type == ComponentType.FRONTEND]
            for frontend_comp in frontend_comps:
                graph.add_edge(lb_comp.name, frontend_comp.name, edge_type='load_balancing')
    
    def _add_balanced_edges(self, graph: nx.DiGraph, components: List[ComponentMetadata]):
        """Add balanced architecture edges"""
        # Standard request flow: Frontend -> API -> Database
        frontend_comp = next((c for c in components if c.type == ComponentType.FRONTEND), None)
        api_comp = next((c for c in components if c.type == ComponentType.API_SERVICE), None)
        db_comp = next((c for c in components if c.type == ComponentType.DATABASE), None)
        
        if frontend_comp and api_comp:
            graph.add_edge(frontend_comp.name, api_comp.name, edge_type='api_call')
        if api_comp and db_comp:
            graph.add_edge(api_comp.name, db_comp.name, edge_type='data_access')
    
    def _optimize_blueprint(self, blueprint: ApplicationBlueprint, 
                          context: GenerationContext) -> ApplicationBlueprint:
        """Optimize the generated blueprint"""
        
        optimized = blueprint
        
        # Resource optimization
        optimized.resource_optimization = self._optimize_resources(
            optimized.components, context.performance_constraints
        )
        
        # Deployment optimization
        optimized.deployment_strategy = self._optimize_deployment(
            optimized.deployment_strategy, context.target_deployment
        )
        
        # Cost optimization
        max_cost = context.budget_constraints.get('max_monthly_cost')
        if max_cost and optimized.estimated_costs['monthly_operational_cost'] > max_cost:
            optimized = self._reduce_costs(optimized, max_cost)
        
        return optimized
    
    def _validate_blueprint(self, blueprint: ApplicationBlueprint) -> Dict[str, Any]:
        """Validate the generated blueprint"""
        
        issues = []
        
        # Check for missing dependencies
        for component in blueprint.components:
            for dep in component.dependencies:
                if not any(c.type.value == dep for c in blueprint.components):
                    issues.append(f"Missing dependency '{dep}' for component '{component.name}'")
        
        # Check for circular dependencies
        if not nx.is_directed_acyclic_graph(blueprint.architecture_graph):
            issues.append("Circular dependencies detected in architecture")
        
        # Check resource constraints
        total_cpu = sum(c.resource_requirements.get('cpu', 0) for c in blueprint.components)
        if total_cpu > 8:  # Assume 8 CPU limit
            issues.append(f"Total CPU requirement ({total_cpu}) exceeds limits")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    def _fix_blueprint_issues(self, blueprint: ApplicationBlueprint, 
                            validation_result: Dict[str, Any]) -> ApplicationBlueprint:
        """Fix issues in the blueprint"""
        
        fixed = blueprint
        
        for issue in validation_result['issues']:
            if 'Missing dependency' in issue:
                # Add missing dependency
                dep_name = issue.split("'")[1]
                dep_type = ComponentType(dep_name)
                missing_comp = self._get_component_by_type(dep_type)
                fixed.components.append(missing_comp)
                fixed.architecture_graph.add_node(missing_comp.name, component=missing_comp)
        
        return fixed
    
    # Additional helper methods for deployment strategies, resource configs, etc.
    def _create_minimal_deployment_strategy(self, context: GenerationContext) -> Dict[str, Any]:
        return {
            'target': context.target_deployment.value,
            'scaling': 'manual',
            'availability': 'single_zone',
            'backup_strategy': 'basic'
        }
    
    def _create_balanced_deployment_strategy(self, context: GenerationContext) -> Dict[str, Any]:
        return {
            'target': context.target_deployment.value,
            'scaling': 'auto',
            'availability': 'multi_zone',
            'backup_strategy': 'automated',
            'monitoring': 'enabled'
        }
    
    def _create_minimal_resource_config(self) -> Dict[str, Any]:
        return {
            'cpu_allocation': 'shared',
            'memory_allocation': 'basic',
            'storage_type': 'standard'
        }
    
    def _create_balanced_resource_config(self) -> Dict[str, Any]:
        return {
            'cpu_allocation': 'dedicated',
            'memory_allocation': 'optimized',
            'storage_type': 'ssd',
            'auto_scaling': True
        }
    
    def _create_basic_security_config(self) -> Dict[str, Any]:
        return {
            'encryption': 'tls',
            'authentication': 'jwt',
            'authorization': 'rbac'
        }
    
    def _create_standard_security_config(self) -> Dict[str, Any]:
        return {
            'encryption': 'tls_1_3',
            'authentication': 'multi_factor',
            'authorization': 'rbac',
            'audit_logging': True,
            'security_scanning': True
        }
    
    def _create_basic_performance_targets(self) -> Dict[str, float]:
        return {
            'response_time_p99': 1000,
            'throughput_rps': 100,
            'availability': 99.0
        }
    
    def _create_balanced_performance_targets(self) -> Dict[str, float]:
        return {
            'response_time_p99': 500,
            'throughput_rps': 1000,
            'availability': 99.9
        }
    
    def _estimate_minimal_costs(self, components: List[ComponentMetadata]) -> Dict[str, float]:
        base_cost = len(components) * 5  # $5 per component per month
        return {
            'monthly_operational_cost': base_cost,
            'setup_cost': base_cost * 0.2
        }
    
    def _estimate_balanced_costs(self, components: List[ComponentMetadata]) -> Dict[str, float]:
        base_cost = len(components) * 12  # $12 per component per month
        return {
            'monthly_operational_cost': base_cost,
            'setup_cost': base_cost * 0.3
        }
    
    def load_component_registry(self, registry_path: str):
        """Load component registry from file"""
        try:
            with open(registry_path, 'r') as f:
                registry_data = yaml.safe_load(f)
            
            for comp_data in registry_data.get('components', []):
                component = ComponentMetadata(**comp_data)
                self.component_registry[component.name] = component
            
            self.logger.info(f"Loaded {len(self.component_registry)} components from registry")
            
        except Exception as e:
            self.logger.error(f"Failed to load component registry: {e}")
            self._initialize_default_registry()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the generator
    generator = ComponentAwareApplicationGenerator()
    
    # Test requirements
    requirements = {
        'app_name': 'Fitness Tracker',
        'user_authentication': True,
        'data_persistence': True,
        'api_access': True,
        'web_interface': True,
        'concurrent_users': 500,
        'ai_features': True,
        'max_response_time': 300,
        'max_monthly_cost': 75
    }
    
    # Analyze requirements
    analysis = generator.analyze_requirements(requirements)
    print("Requirements Analysis:")
    print(f"Required components: {analysis['required_components']}")
    print(f"Optional components: {analysis['optional_components']}")
    print(f"Estimated cost: ${analysis['cost_estimates']['monthly_operational_cost']:.2f}/month")
    
    # Generate application with different strategies
    strategies = ['minimal', 'balanced', 'performance']
    
    for strategy in strategies:
        blueprint = generator.generate_application(requirements, strategy)
        print(f"\n{strategy.upper()} Strategy:")
        print(f"Components: {[c.name for c in blueprint.components]}")
        print(f"Estimated cost: ${blueprint.estimated_costs['monthly_operational_cost']:.2f}/month")
        print(f"Performance targets: {blueprint.performance_targets}")
        print(f"Architecture nodes: {len(blueprint.architecture_graph.nodes())}")
        print(f"Architecture edges: {len(blueprint.architecture_graph.edges())}")