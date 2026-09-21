# Service Mesh Infrastructure

A comprehensive service mesh implementation providing service discovery, health monitoring, load balancing, circuit breaker patterns, retry logic, distributed tracing, and more for managing 70+ microservices.

## Features

### ✅ Core Components Implemented

1. **Service Discovery & Registry** 
   - Consul-based service discovery
   - Auto-discovery of Docker containers, processes, and network services
   - Service registration with health checks and metadata

2. **Health Monitoring**
   - HTTP, TCP, database, and custom health checks
   - Real-time health status tracking
   - Automated failure detection and alerting

3. **Intelligent Load Balancing**
   - Multiple strategies: Round Robin, Weighted, Least Connections, Health-weighted
   - Consistent hashing for session affinity
   - Integration with service discovery for dynamic updates

4. **Circuit Breaker Patterns**
   - Automatic failure detection and recovery
   - Configurable failure thresholds and timeouts
   - State transitions (Closed → Open → Half-Open)

5. **Retry Logic with Exponential Backoff**
   - Multiple backoff strategies (exponential, linear, fibonacci)
   - Configurable retry conditions and timeouts
   - Comprehensive retry metrics and monitoring

6. **Distributed Request Tracing**
   - OpenTracing-compatible distributed tracing
   - Automatic span creation and context propagation
   - Trace analysis and dependency mapping

7. **Service Dependency Visualization**
   - Interactive topology graphs with Plotly
   - Dependency matrix and health dashboards
   - Network graph export (GraphML, JSON)

8. **Auto-Discovery System**
   - Docker container discovery
   - Process-based service detection
   - Network port scanning
   - Automatic Consul registration

## Architecture

```
service-mesh/
├── consul/                 # Consul service discovery client
├── health/                 # Health monitoring and checks
├── registry/               # Auto-discovery and registration
├── load-balancer/          # Intelligent load balancing
├── circuit-breaker/        # Circuit breaker patterns
├── retry/                  # Retry logic with backoff
├── tracing/                # Distributed request tracing
├── visualizer/             # Dependency graph visualization
├── service_mesh.py         # Main coordinator
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Consul (Required)

```bash
# Using Docker
docker run -d --name consul -p 8500:8500 consul:latest agent -server -bootstrap -ui -bind=0.0.0.0 -client=0.0.0.0

# Or download and run locally
consul agent -dev -bind=127.0.0.1 -client=127.0.0.1
```

### 3. Initialize Service Mesh

```python
from service_mesh import initialize_service_mesh, ServiceMeshConfig, LoadBalancingStrategy

# Configure service mesh
config = ServiceMeshConfig(
    consul_host="localhost",
    consul_port=8500,
    enable_auto_discovery=True,
    health_check_interval=30,
    load_balancing_strategy=LoadBalancingStrategy.HEALTH_WEIGHTED
)

# Start service mesh
service_mesh = initialize_service_mesh(config)
```

### 4. Register Services

```python
# Register a service
service_id = service_mesh.register_service(
    service_name="api-service",
    port=8080,
    health_check_path="/health",
    tags=["api", "v1"],
    metadata={"version": "1.0.0", "team": "backend"}
)

print(f"Registered service: {service_id}")
```

### 5. Discover Services

```python
# Discover service instances
instances = service_mesh.discover_service("api-service")
for instance in instances:
    print(f"Instance: {instance['host']}:{instance['port']} ({instance['status']})")
```

## Component Usage

### Circuit Breaker

```python
from circuit_breaker.circuit_breaker import circuit_breaker, CircuitBreakerConfig

# Using decorator
@circuit_breaker("external-api", config=CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=30
))
def call_external_service():
    # Your service call here
    pass

# Manual usage
cb = service_mesh.circuit_breaker_registry.get_or_create("my-service")
result = cb.call(my_function, *args, **kwargs)
```

### Retry Logic

```python
from retry.retry_logic import retry, RetryStrategy

# Using decorator
@retry(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0
)
def unreliable_function():
    # Function that might fail
    pass

# Manual usage
result = service_mesh.retry_manager.retry(
    my_function, 
    config_name="api-calls",
    *args, **kwargs
)
```

### Distributed Tracing

```python
from tracing.distributed_tracing import trace, get_tracer

# Using decorator
@trace("process_order", service_name="order-service")
def process_order(order_id):
    # Processing logic
    pass

# Manual usage
tracer = get_tracer("my-service")
with tracer.span("operation_name") as span:
    span.set_tag("user.id", "12345")
    # Your operation
```

### Health Monitoring

```python
from health.health_monitor import HealthCheckConfig, CheckType

# Add custom health check
health_config = HealthCheckConfig(
    check_id="api-http-check",
    service_name="api-service",
    check_type=CheckType.HTTP,
    target="http://localhost:8080/health",
    interval=30,
    timeout=10
)

service_mesh.health_monitor.add_health_check(health_config)
```

## API Reference

### ServiceMesh Class

Main coordinator class that integrates all service mesh components.

#### Methods

- `register_service(service_name, port, health_check_path, tags, metadata)` - Register a service
- `unregister_service(instance_id)` - Unregister a service  
- `discover_service(service_name)` - Discover service instances
- `get_service_health(service_name)` - Get comprehensive health info
- `get_service_mesh_metrics()` - Get service mesh metrics
- `generate_topology_visualization()` - Create dependency visualizations

### Configuration

```python
@dataclass
class ServiceMeshConfig:
    consul_host: str = "localhost"
    consul_port: int = 8500
    enable_auto_discovery: bool = True
    enable_health_monitoring: bool = True
    enable_load_balancing: bool = True
    enable_circuit_breaker: bool = True
    enable_retry_logic: bool = True
    enable_tracing: bool = True
    health_check_interval: int = 30
    discovery_interval: int = 60
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.HEALTH_WEIGHTED
    circuit_breaker_failure_threshold: int = 10
    retry_max_attempts: int = 3
```

## Monitoring and Observability

### Service Health Dashboard

```python
# Get service health
health = service_mesh.get_service_health("api-service")
print(f"Status: {health['overall_status']}")
print(f"Uptime: {health['uptime_percentage']:.1f}%")
```

### Topology Visualization

```python
# Generate interactive visualizations
files = await service_mesh.generate_topology_visualization()
print(f"Generated: {files}")

# Files created:
# - service_topology.html (Network graph)
# - dependency_matrix.html (Dependency matrix)
# - service_dashboard.html (Health dashboard)
# - service_topology.json (Raw data)
```

### Metrics Collection

```python
# Get comprehensive metrics
metrics = service_mesh.get_service_mesh_metrics()
print(f"Total services: {metrics['total_services']}")
print(f"Healthy services: {metrics['healthy_services']}")
print(f"Circuit breakers: {metrics['circuit_breaker_stats']}")
```

## Production Deployment

### 1. Consul Cluster Setup

For production, deploy a Consul cluster with multiple nodes:

```bash
# Consul server nodes
consul agent -server -bootstrap-expect=3 -datacenter=dc1 -bind=<IP> -client=0.0.0.0

# Consul clients on each service host  
consul agent -datacenter=dc1 -bind=<IP> -retry-join=<SERVER_IP>
```

### 2. Service Registration

Each service should register itself on startup:

```python
# In your service startup code
from service_mesh import get_service_mesh

service_mesh = get_service_mesh()
if service_mesh:
    service_mesh.register_service(
        service_name=os.environ.get('SERVICE_NAME'),
        port=int(os.environ.get('SERVICE_PORT')),
        metadata={'version': os.environ.get('SERVICE_VERSION')}
    )
```

### 3. Health Check Endpoints

Implement health check endpoints in your services:

```python
# Flask example
@app.route('/health')
def health_check():
    # Check database connectivity, dependencies, etc.
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
```

### 4. Graceful Shutdown

Ensure services unregister on shutdown:

```python
import signal
import sys

def signal_handler(sig, frame):
    service_mesh = get_service_mesh()
    if service_mesh and service_id:
        service_mesh.unregister_service(service_id)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

## Advanced Features

### Custom Load Balancing

```python
from load_balancer.load_balancer import LoadBalancer, LoadBalancingStrategy

# Create custom load balancer
lb = service_mesh.load_balancer_manager.get_or_create_load_balancer(
    "my-service",
    LoadBalancingStrategy.CONSISTENT_HASH
)

# Select instance for request
result = lb.select_instance(client_ip="192.168.1.100")
if result:
    print(f"Selected: {result.instance.host}:{result.instance.port}")
```

### Custom Circuit Breaker

```python
from circuit_breaker.circuit_breaker import CircuitBreakerConfig

# Configure custom circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=10,
    recovery_timeout=60,
    request_timeout=30,
    success_threshold=5,
    failure_rate_threshold=0.5
)

cb = service_mesh.circuit_breaker_registry.get_or_create("critical-service", config)
```

### Trace Analysis

```python
from tracing.distributed_tracing import TraceAnalyzer

# Analyze traces for insights
analyzer = TraceAnalyzer(collected_spans)
stats = analyzer.get_trace_statistics()
slow_traces = analyzer.find_slow_traces(percentile=95)
dependencies = analyzer.analyze_service_dependencies()
```

## Troubleshooting

### Common Issues

1. **Consul Connection Failed**
   - Ensure Consul is running and accessible
   - Check network connectivity and firewall rules
   - Verify Consul configuration

2. **Services Not Discovered**  
   - Check service registration in Consul UI (http://localhost:8500)
   - Verify health checks are passing
   - Review service tags and metadata

3. **Health Checks Failing**
   - Ensure health check endpoints are implemented
   - Check network connectivity between services
   - Review health check configuration (timeouts, intervals)

4. **Circuit Breaker Not Triggering**
   - Verify failure threshold configuration
   - Check if sufficient requests have been made
   - Review error classification logic

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable component-specific debugging
logging.getLogger('consul').setLevel(logging.DEBUG)
logging.getLogger('health').setLevel(logging.DEBUG)
```

## Performance Considerations

- **Consul Performance**: Use Consul clustering for high availability
- **Health Check Frequency**: Balance between responsiveness and resource usage  
- **Circuit Breaker Tuning**: Adjust thresholds based on service characteristics
- **Tracing Sampling**: Use sampling in high-traffic environments
- **Memory Usage**: Monitor span storage and batch processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

**Service Mesh Infrastructure v1.0**  
*Comprehensive microservices management for scale*