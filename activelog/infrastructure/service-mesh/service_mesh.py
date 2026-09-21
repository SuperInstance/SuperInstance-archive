"""
Service Mesh Infrastructure
===========================

Comprehensive service mesh providing:
- Consul-based service discovery
- Health checking and monitoring  
- Intelligent load balancing
- Circuit breaker patterns
- Retry logic with exponential backoff
- Distributed request tracing
- Service dependency visualization
- Auto-discovery and registration
- Failover mechanisms
- Rate limiting
- Service-to-service authentication
- Version management and canary deployments

This is the main entry point that coordinates all service mesh components.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import json

# Import service mesh components
from consul.consul_client import ServiceRegistry, ConsulServiceDiscovery
from health.health_monitor import HealthMonitor, HealthCheckConfig, CheckType
from registry.auto_discovery import AutoServiceRegistry
from load_balancer.load_balancer import ServiceLoadBalancerManager, LoadBalancingStrategy
from circuit_breaker.circuit_breaker import CircuitBreakerRegistry, CircuitBreakerConfig
from retry.retry_logic import RetryManager, RetryConfig, RetryStrategy
from tracing.distributed_tracing import get_tracer, MemorySpanExporter
from visualizer.dependency_graph import ServiceTopologyDiscovery, ServiceDependencyVisualizer


@dataclass
class ServiceMeshConfig:
    """Configuration for the service mesh"""
    consul_host: str = "localhost"
    consul_port: int = 8500
    enable_auto_discovery: bool = True
    enable_health_monitoring: bool = True
    enable_load_balancing: bool = True
    enable_circuit_breaker: bool = True
    enable_retry_logic: bool = True
    enable_tracing: bool = True
    enable_metrics: bool = True
    health_check_interval: int = 30
    discovery_interval: int = 60
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.HEALTH_WEIGHTED
    
    # Circuit breaker defaults
    circuit_breaker_failure_threshold: int = 10
    circuit_breaker_recovery_timeout: int = 60
    
    # Retry defaults
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF


class ServiceMesh:
    """
    Main service mesh coordinator that integrates all components
    """
    
    def __init__(self, config: ServiceMeshConfig = None):
        self.config = config or ServiceMeshConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.consul_discovery = None
        self.service_registry = None
        self.auto_registry = None
        self.health_monitor = None
        self.load_balancer_manager = None
        self.circuit_breaker_registry = None
        self.retry_manager = None
        self.topology_discovery = None
        self.visualizer = None
        
        # State
        self.running = False
        self.registered_services = {}
        self.component_threads = {}
        
        # Initialize components based on config
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize service mesh components"""
        try:
            # Core service discovery
            self.consul_discovery = ConsulServiceDiscovery(
                self.config.consul_host, 
                self.config.consul_port
            )
            
            self.service_registry = ServiceRegistry(
                self.config.consul_host,
                self.config.consul_port
            )
            
            # Auto-discovery
            if self.config.enable_auto_discovery:
                self.auto_registry = AutoServiceRegistry(
                    self.config.consul_host,
                    self.config.consul_port
                )
            
            # Health monitoring
            if self.config.enable_health_monitoring:
                self.health_monitor = HealthMonitor()
            
            # Load balancing
            if self.config.enable_load_balancing:
                self.load_balancer_manager = ServiceLoadBalancerManager(
                    self.config.consul_host,
                    self.config.consul_port
                )
            
            # Circuit breaker
            if self.config.enable_circuit_breaker:
                self.circuit_breaker_registry = CircuitBreakerRegistry()
                
                # Set default circuit breaker config
                default_cb_config = CircuitBreakerConfig(
                    failure_threshold=self.config.circuit_breaker_failure_threshold,
                    recovery_timeout=self.config.circuit_breaker_recovery_timeout
                )
                self.circuit_breaker_registry.default_config = default_cb_config
            
            # Retry logic
            if self.config.enable_retry_logic:
                self.retry_manager = RetryManager()
                
                # Set default retry config
                default_retry_config = RetryConfig(
                    max_attempts=self.config.retry_max_attempts,
                    base_delay=self.config.retry_base_delay,
                    strategy=self.config.retry_strategy
                )
                self.retry_manager.default_config = default_retry_config
            
            # Topology discovery and visualization
            self.topology_discovery = ServiceTopologyDiscovery(
                self.config.consul_host,
                self.config.consul_port
            )
            self.visualizer = ServiceDependencyVisualizer()
            
            self.logger.info("Service mesh components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize service mesh components: {e}")
            raise
    
    def start(self):
        """Start the service mesh"""
        if self.running:
            self.logger.warning("Service mesh is already running")
            return
        
        try:
            self.running = True
            
            # Start core components
            self.consul_discovery.start()
            self.service_registry.start()
            
            # Start auto-discovery
            if self.auto_registry:
                self.auto_registry.start_auto_discovery()
            
            # Start health monitoring
            if self.health_monitor:
                self.health_monitor.start()
            
            # Start load balancer sync
            if self.load_balancer_manager:
                self.load_balancer_manager.start_service_discovery_sync()
            
            # Start background tasks
            self._start_background_tasks()
            
            self.logger.info("Service mesh started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start service mesh: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the service mesh"""
        if not self.running:
            return
        
        try:
            self.running = False
            
            # Stop background tasks
            self._stop_background_tasks()
            
            # Stop components
            if self.load_balancer_manager:
                self.load_balancer_manager.stop_service_discovery_sync()
            
            if self.health_monitor:
                self.health_monitor.stop()
            
            if self.auto_registry:
                self.auto_registry.stop_auto_discovery()
            
            if self.service_registry:
                self.service_registry.stop()
            
            if self.consul_discovery:
                self.consul_discovery.stop()
            
            self.logger.info("Service mesh stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping service mesh: {e}")
    
    def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        # Health check automation
        if self.health_monitor:
            health_thread = threading.Thread(
                target=self._health_monitoring_loop, 
                daemon=True
            )
            health_thread.start()
            self.component_threads['health'] = health_thread
        
        # Metrics collection
        if self.config.enable_metrics:
            metrics_thread = threading.Thread(
                target=self._metrics_collection_loop,
                daemon=True
            )
            metrics_thread.start()
            self.component_threads['metrics'] = metrics_thread
    
    def _stop_background_tasks(self):
        """Stop background tasks"""
        # Threads are daemon threads, so they'll stop when main process stops
        self.component_threads.clear()
    
    def _health_monitoring_loop(self):
        """Background health monitoring loop"""
        while self.running:
            try:
                # Auto-configure health checks for discovered services
                services = self.consul_discovery.get_all_services()
                
                for service_name, instances in services.items():
                    for instance in instances:
                        check_id = f"{instance.instance_id}-auto-health"
                        
                        # Check if health check already exists
                        existing_checks = [
                            check for check in self.health_monitor.checks.values()
                            if check.check_id == check_id
                        ]
                        
                        if not existing_checks:
                            # Create HTTP health check
                            health_check_config = HealthCheckConfig(
                                check_id=check_id,
                                service_name=service_name,
                                check_type=CheckType.HTTP,
                                target=f"http://{instance.host}:{instance.port}/health",
                                interval=self.config.health_check_interval,
                                timeout=10
                            )
                            
                            self.health_monitor.add_health_check(health_check_config)
                
                time.sleep(self.config.discovery_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(30)
    
    def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        while self.running:
            try:
                # Collect and log service mesh metrics
                metrics = self.get_service_mesh_metrics()
                
                # Log key metrics
                self.logger.info(
                    f"Service Mesh Metrics: "
                    f"Services: {metrics.get('total_services', 0)}, "
                    f"Healthy: {metrics.get('healthy_services', 0)}, "
                    f"Circuit Breakers: {metrics.get('circuit_breaker_stats', {}).get('total', 0)}"
                )
                
                time.sleep(60)  # Collect metrics every minute
                
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                time.sleep(60)
    
    def register_service(self, service_name: str, port: int, 
                        health_check_path: str = "/health",
                        tags: List[str] = None,
                        metadata: Dict[str, Any] = None) -> str:
        """
        Register a service with the service mesh
        
        Args:
            service_name: Name of the service
            port: Port the service is running on
            health_check_path: HTTP path for health checks
            tags: Service tags
            metadata: Additional metadata
            
        Returns:
            Service instance ID
        """
        if not self.running:
            raise RuntimeError("Service mesh is not running")
        
        try:
            # Register with service registry
            instance_id = self.service_registry.auto_register_service(
                service_name=service_name,
                port=port,
                health_check_path=health_check_path,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            if instance_id:
                self.registered_services[instance_id] = {
                    'service_name': service_name,
                    'port': port,
                    'registered_at': datetime.now()
                }
                
                self.logger.info(f"Registered service: {service_name} with ID: {instance_id}")
                return instance_id
            else:
                raise Exception("Failed to register service")
            
        except Exception as e:
            self.logger.error(f"Failed to register service {service_name}: {e}")
            raise
    
    def unregister_service(self, instance_id: str) -> bool:
        """Unregister a service from the service mesh"""
        try:
            success = self.service_registry.unregister_service(instance_id)
            
            if success and instance_id in self.registered_services:
                del self.registered_services[instance_id]
                self.logger.info(f"Unregistered service: {instance_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to unregister service {instance_id}: {e}")
            return False
    
    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """
        Discover instances of a service
        
        Args:
            service_name: Name of the service to discover
            
        Returns:
            List of service instances with health and load balancing info
        """
        try:
            # Get instances from service discovery
            instances = self.consul_discovery.discover_services(service_name, healthy_only=True)
            
            # Enrich with load balancing information
            if self.load_balancer_manager:
                lb_result = self.load_balancer_manager.select_instance(service_name)
                
                if lb_result:
                    # Mark the selected instance
                    selected_id = lb_result.instance.instance_id
                    for instance in instances:
                        instance.metadata['selected_by_lb'] = (instance.instance_id == selected_id)
                        instance.metadata['lb_strategy'] = lb_result.strategy_used.value
            
            return [
                {
                    'instance_id': inst.instance_id,
                    'host': inst.host,
                    'port': inst.port,
                    'status': inst.status.value,
                    'tags': inst.tags,
                    'metadata': inst.metadata
                }
                for inst in instances
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to discover service {service_name}: {e}")
            return []
    
    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """Get comprehensive health information for a service"""
        try:
            health_info = {
                'service_name': service_name,
                'overall_status': 'unknown',
                'instances': [],
                'health_checks': [],
                'circuit_breaker_status': None
            }
            
            # Get health from health monitor
            if self.health_monitor:
                service_health = self.health_monitor.get_service_health(service_name)
                health_info.update({
                    'overall_status': service_health.overall_status.value,
                    'uptime_percentage': service_health.uptime_percentage,
                    'avg_response_time': service_health.avg_response_time,
                    'health_checks': [
                        {
                            'check_id': check.check_id,
                            'status': check.status.value,
                            'response_time': check.response_time,
                            'message': check.message
                        }
                        for check in service_health.checks
                    ]
                })
            
            # Get circuit breaker status
            if self.circuit_breaker_registry:
                cb_status = self.circuit_breaker_registry.get_all_status()
                service_cb = cb_status.get(service_name)
                if service_cb:
                    health_info['circuit_breaker_status'] = service_cb
            
            # Get instance information
            instances = self.discover_service(service_name)
            health_info['instances'] = instances
            
            return health_info
            
        except Exception as e:
            self.logger.error(f"Failed to get health for service {service_name}: {e}")
            return {'error': str(e)}
    
    async def generate_topology_visualization(self) -> Dict[str, str]:
        """Generate service dependency visualizations"""
        try:
            # Discover topology
            services, dependencies = await self.topology_discovery.discover_topology()
            
            # Generate visualizations
            network_fig = self.visualizer.create_plotly_visualization(services, dependencies)
            matrix_fig = self.visualizer.create_dependency_matrix(services, dependencies)
            dashboard_fig = self.visualizer.create_service_health_dashboard(services)
            
            # Save to files
            output_files = {}
            
            network_fig.write_html("service_topology.html")
            output_files['network'] = "service_topology.html"
            
            matrix_fig.write_html("dependency_matrix.html")  
            output_files['matrix'] = "dependency_matrix.html"
            
            dashboard_fig.write_html("service_dashboard.html")
            output_files['dashboard'] = "service_dashboard.html"
            
            # Export data
            self.visualizer.export_to_json(services, dependencies, "service_topology.json")
            output_files['data'] = "service_topology.json"
            
            self.logger.info("Generated topology visualizations")
            return output_files
            
        except Exception as e:
            self.logger.error(f"Failed to generate topology visualization: {e}")
            return {'error': str(e)}
    
    def get_service_mesh_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service mesh metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_services': 0,
            'healthy_services': 0,
            'registered_services': len(self.registered_services),
            'circuit_breaker_stats': {},
            'retry_stats': {},
            'load_balancer_stats': {}
        }
        
        try:
            # Service discovery metrics
            if self.consul_discovery:
                all_services = self.consul_discovery.get_all_services()
                metrics['total_services'] = len(all_services)
                
                # Count healthy services
                healthy_count = 0
                for service_name, instances in all_services.items():
                    if any(inst.status.value == 'healthy' for inst in instances):
                        healthy_count += 1
                
                metrics['healthy_services'] = healthy_count
            
            # Circuit breaker metrics
            if self.circuit_breaker_registry:
                cb_stats = self.circuit_breaker_registry.get_all_status()
                metrics['circuit_breaker_stats'] = {
                    'total': len(cb_stats),
                    'open': sum(1 for status in cb_stats.values() if status['state'] == 'open'),
                    'closed': sum(1 for status in cb_stats.values() if status['state'] == 'closed'),
                    'half_open': sum(1 for status in cb_stats.values() if status['state'] == 'half_open')
                }
            
            # Retry metrics
            if self.retry_manager:
                retry_stats = self.retry_manager.metrics.get_stats()
                metrics['retry_stats'] = {
                    'configurations': len(retry_stats),
                    'total_calls': sum(stats.get('total_calls', 0) for stats in retry_stats.values()),
                    'successful_calls': sum(stats.get('successful_calls', 0) for stats in retry_stats.values()),
                    'failed_calls': sum(stats.get('failed_calls', 0) for stats in retry_stats.values())
                }
            
            # Load balancer metrics
            if self.load_balancer_manager:
                lb_stats = self.load_balancer_manager.get_all_statistics()
                metrics['load_balancer_stats'] = {
                    'total_load_balancers': len(lb_stats),
                    'strategies': {}
                }
                
                # Count strategies
                for service_stats in lb_stats.values():
                    strategy = service_stats.get('strategy', 'unknown')
                    metrics['load_balancer_stats']['strategies'][strategy] = \
                        metrics['load_balancer_stats']['strategies'].get(strategy, 0) + 1
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting service mesh metrics: {e}")
            metrics['error'] = str(e)
            return metrics
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current service mesh configuration"""
        return {
            'consul_host': self.config.consul_host,
            'consul_port': self.config.consul_port,
            'components_enabled': {
                'auto_discovery': self.config.enable_auto_discovery,
                'health_monitoring': self.config.enable_health_monitoring,
                'load_balancing': self.config.enable_load_balancing,
                'circuit_breaker': self.config.enable_circuit_breaker,
                'retry_logic': self.config.enable_retry_logic,
                'tracing': self.config.enable_tracing,
                'metrics': self.config.enable_metrics
            },
            'intervals': {
                'health_check': self.config.health_check_interval,
                'discovery': self.config.discovery_interval
            },
            'defaults': {
                'load_balancing_strategy': self.config.load_balancing_strategy.value,
                'circuit_breaker_failure_threshold': self.config.circuit_breaker_failure_threshold,
                'retry_max_attempts': self.config.retry_max_attempts
            }
        }


# Global service mesh instance
_service_mesh_instance = None


def initialize_service_mesh(config: ServiceMeshConfig = None) -> ServiceMesh:
    """Initialize the global service mesh instance"""
    global _service_mesh_instance
    
    if _service_mesh_instance is None:
        _service_mesh_instance = ServiceMesh(config)
        _service_mesh_instance.start()
    
    return _service_mesh_instance


def get_service_mesh() -> Optional[ServiceMesh]:
    """Get the global service mesh instance"""
    return _service_mesh_instance


def shutdown_service_mesh():
    """Shutdown the global service mesh instance"""
    global _service_mesh_instance
    
    if _service_mesh_instance:
        _service_mesh_instance.stop()
        _service_mesh_instance = None


# Usage example
if __name__ == "__main__":
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\nShutting down service mesh...")
        shutdown_service_mesh()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize service mesh with custom config
    config = ServiceMeshConfig(
        consul_host="localhost",
        consul_port=8500,
        enable_auto_discovery=True,
        health_check_interval=15,
        load_balancing_strategy=LoadBalancingStrategy.HEALTH_WEIGHTED
    )
    
    service_mesh = initialize_service_mesh(config)
    
    # Example: Register a service
    try:
        service_id = service_mesh.register_service(
            service_name="example-api",
            port=8080,
            tags=["api", "v1.0"],
            metadata={"version": "1.0.0", "team": "platform"}
        )
        print(f"Registered service with ID: {service_id}")
        
        # Show service mesh metrics
        metrics = service_mesh.get_service_mesh_metrics()
        print(f"Service Mesh Metrics: {json.dumps(metrics, indent=2)}")
        
        # Keep running
        print("Service mesh is running... Press Ctrl+C to stop")
        while True:
            time.sleep(10)
            
            # Periodically show status
            print(f"Services: {metrics.get('total_services', 0)}, Healthy: {metrics.get('healthy_services', 0)}")
            metrics = service_mesh.get_service_mesh_metrics()
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        shutdown_service_mesh()