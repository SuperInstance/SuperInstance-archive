# ActiveLog Service Mesh

A comprehensive service mesh implementation for ActiveLog with Envoy proxy, Consul service discovery, advanced traffic management, and deployment strategies.

## Features

### Core Service Mesh
- **Envoy Proxy**: High-performance edge and service proxy
- **Consul Service Discovery**: Dynamic service registration and discovery
- **Circuit Breakers**: Automatic failure detection and isolation
- **Retry Logic**: Exponential backoff retry policies
- **Load Balancing**: Multiple algorithms (round-robin, least-request, etc.)

### Traffic Management
- **Request Routing**: Header-based, path-based, and weighted routing
- **Traffic Splitting**: Weighted traffic distribution
- **Fault Injection**: Chaos engineering capabilities
- **Rate Limiting**: Request throttling and burst protection
- **Timeouts**: Configurable request timeouts per service

### Deployment Strategies
- **Blue-Green Deployments**: Zero-downtime deployments with instant traffic switching
- **Canary Releases**: Gradual traffic shifting with automated monitoring
- **A/B Testing**: User-based traffic routing for feature testing
- **Rollback Capabilities**: Automatic and manual rollback mechanisms

### Observability
- **Distributed Tracing**: Jaeger integration for request tracing
- **Metrics Collection**: Prometheus metrics for all mesh components
- **Health Monitoring**: Comprehensive health checking and alerting
- **Access Logging**: Detailed request/response logging

## Quick Start

### 1. Start the Service Mesh

```bash
cd ~/activelog/infrastructure/mesh
make start
```

This will start all mesh components:
- Consul server for service discovery
- Envoy gateway proxy
- Traffic management services
- Monitoring and control plane

### 2. Verify Mesh Status

```bash
make status
```

### 3. Deploy Services with Blue-Green

```bash
make deploy-blue-green SERVICE=api-gateway IMAGE=activelog/api-gateway:v1.1.0
```

### 4. Deploy Services with Canary

```bash
make deploy-canary SERVICE=auth-service IMAGE=activelog/auth-service:v1.1.0 PERCENTAGE=10
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │  Load Balancer  │    │  External APIs  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     Envoy Gateway         │
                    │   (Edge Proxy + LB)       │
                    └─────────────┬─────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
   ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
   │  API Gateway    │  │  Auth Service   │  │ GraphQL Service │
   │                 │  │                 │  │                 │
   │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │
   │ │Blue │Green │ │  │ │Stable│Canary│ │  │ │Stable│Canary│ │
   │ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │
   └─────────────────┘  └─────────────────┘  └─────────────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │    Consul Service         │
                    │    Discovery + KV         │
                    └───────────────────────────┘
```

## Service Discovery

### Consul Configuration

Services automatically register with Consul using the configuration in `consul/consul-agent.json`:

```json
{
  "id": "api-gateway",
  "name": "api-gateway",
  "tags": ["activelog", "gateway", "api"],
  "address": "api-gateway",
  "port": 8000,
  "check": {
    "http": "http://api-gateway:8000/health",
    "interval": "10s"
  }
}
```

### Service Registration

Services are automatically discovered and registered when they start. Health checks ensure only healthy instances receive traffic.

## Circuit Breakers

### Configuration

Circuit breakers are configured per service in `envoy/envoy.yaml`:

```yaml
circuit_breakers:
  thresholds:
  - priority: DEFAULT
    max_connections: 100
    max_pending_requests: 50
    max_requests: 200
    max_retries: 5
```

### Monitoring

Check circuit breaker status:

```bash
make circuit-breakers
```

## Retry Logic

### Exponential Backoff

Retry policies with exponential backoff are configured per route:

```yaml
retry_policy:
  retry_on: "5xx,gateway-error,connect-failure,refused-stream"
  num_retries: 3
  per_try_timeout: 10s
  retry_back_off:
    base_interval: 1s
    max_interval: 10s
```

## Traffic Routing

### Header-Based Routing

Route traffic based on headers:

```bash
curl -H "x-canary: true" http://localhost:8080/api/users
```

### Version-Based Routing

Route to specific API versions:

```bash
curl http://localhost:8080/api/v2/users  # Routes to canary
curl http://localhost:8080/api/v1/users  # Routes to stable
```

### Geographic Routing

Route based on region:

```bash
curl -H "x-region: us-west" http://localhost:8080/api/users
```

## Deployment Strategies

### Blue-Green Deployments

Deploy new version to green environment:

```bash
# Deploy to green environment
make deploy-blue-green SERVICE=api-gateway IMAGE=v1.1.0 TARGET_COLOR=green

# Switch traffic to green
make switch-traffic SERVICE=api-gateway TARGET_COLOR=green STRATEGY=instant

# Rollback if needed
make rollback SERVICE=api-gateway TARGET_COLOR=blue
```

### Canary Releases

Gradual traffic shifting:

```bash
# Start canary at 10%
make deploy-canary SERVICE=auth-service IMAGE=v1.1.0 PERCENTAGE=10

# Monitor and increase traffic
make switch-traffic SERVICE=auth-service TARGET_COLOR=canary STRATEGY=gradual

# Promote to stable or rollback
make deploy-canary SERVICE=auth-service IMAGE=v1.1.0 PERCENTAGE=100
```

### Automated Canary Progression

The canary controller automatically progresses traffic based on success criteria:

1. **5%** traffic for 10 minutes
2. **10%** traffic for 20 minutes  
3. **25%** traffic for 30 minutes
4. **50%** traffic for 1 hour
5. **100%** traffic (promotion)

Automatic rollback occurs if:
- Error rate > 5%
- P95 latency > 5 seconds
- Success rate < 95%

## Monitoring

### Mesh Metrics

```bash
make metrics
```

### Service Health

```bash
make health-check
```

### Traffic Statistics

```bash
make traffic-stats
```

### Access Dashboards

- **Consul UI**: http://localhost:8500
- **Envoy Admin**: http://localhost:9901
- **Jaeger Tracing**: http://localhost:16687
- **Mesh Metrics**: http://localhost:9095

## Load Testing

### Basic Load Test

```bash
make load-test TARGET=/api/health DURATION=60s
```

### Chaos Engineering

```bash
make chaos-test
```

## Configuration

### Mesh Configuration

Main configuration file: `configs/mesh-config.yaml`

```yaml
mesh:
  name: "activelog-mesh"
  global:
    security:
      tls_enabled: true
      mtls_mode: "permissive"
    observability:
      tracing:
        enabled: true
        sampling_rate: 0.1
```

### Service-Specific Configuration

Each service can have custom configuration:

```yaml
services:
  api-gateway:
    circuit_breaker:
      failure_threshold: 5
      timeout: 30s
    retry_policy:
      max_retries: 3
    load_balancing:
      policy: "round_robin"
```

## API Management

### Mesh Controller API

The mesh controller provides REST APIs for management:

```bash
# Get mesh status
curl http://localhost:8094/api/v1/mesh/status

# Update traffic weights
curl -X POST http://localhost:8094/api/v1/traffic/weights \
  -d '{"service": "api-gateway", "stable": 90, "canary": 10}'

# Trigger deployment
curl -X POST http://localhost:8094/api/v1/deploy/canary \
  -d '{"service": "auth-service", "image": "v1.1.0", "percentage": 10}'
```

### CLI Management

Use the mesh manager CLI:

```bash
# Check status
python3 scripts/mesh-manager.py status

# Deploy blue-green
python3 scripts/mesh-manager.py deploy-blue-green --service api-gateway --image v1.1.0

# Deploy canary
python3 scripts/mesh-manager.py deploy-canary --service auth-service --image v1.1.0 --percentage 10
```

## Security

### Mutual TLS (mTLS)

Enable mTLS between services:

```yaml
global:
  security:
    tls_enabled: true
    mtls_mode: "strict"
```

### Network Policies

Define network access policies:

```yaml
network_policies:
  - name: "api-gateway-ingress"
    from: ["internet"]
    to: ["api-gateway"]
    ports: [8080]
```

### Service-to-Service Authentication

Configure service authentication:

```bash
consul intention create api-gateway auth-service
consul intention create graphql-service metadata-service
```

## Troubleshooting

### Check Service Discovery

```bash
curl http://localhost:8500/v1/catalog/services
curl http://localhost:8500/v1/health/service/api-gateway
```

### Debug Envoy Configuration

```bash
curl http://localhost:9901/config_dump
curl http://localhost:9901/clusters
curl http://localhost:9901/stats
```

### View Logs

```bash
make logs SERVICE=envoy-gateway
make logs SERVICE=consul-server
make logs  # All services
```

### Emergency Procedures

```bash
# Emergency rollback all services
make emergency-rollback

# Emergency stop
make emergency-stop
```

## Development

### Setup Development Environment

```bash
make dev-setup
```

### Build Components

```bash
make build
```

### Run Tests

```bash
make load-test
make chaos-test
```

## Production Considerations

### High Availability

1. **Multi-AZ Deployment**: Deploy across multiple availability zones
2. **Consul Clustering**: Use 3+ Consul servers for HA
3. **Envoy Redundancy**: Multiple Envoy instances with load balancing
4. **Health Monitoring**: Comprehensive health checks and alerting

### Scaling

1. **Horizontal Scaling**: Scale Envoy proxies based on traffic
2. **Service Scaling**: Auto-scale backend services
3. **Resource Limits**: Set appropriate CPU/memory limits
4. **Connection Pooling**: Configure connection pools for efficiency

### Security Hardening

1. **Enable mTLS**: Strict mutual TLS between all services
2. **Network Policies**: Restrict service-to-service communication
3. **Secret Management**: Use external secret stores
4. **Access Control**: Implement RBAC policies

### Monitoring & Alerting

1. **SLO/SLI Monitoring**: Define and monitor service level objectives
2. **Error Budgets**: Track error budgets for reliability
3. **Capacity Planning**: Monitor resource utilization trends
4. **Incident Response**: Automated incident detection and response

## Contributing

1. **Configuration Changes**: Update configs in version control
2. **Testing**: Test all changes in staging environment
3. **Documentation**: Update documentation for new features
4. **Rollback Plans**: Always have rollback procedures ready

## Support

For questions or issues:

1. Check logs: `make logs`
2. Verify configuration: `make validate-config`  
3. Run health checks: `make health-check`
4. Review monitoring dashboards
5. Consult troubleshooting guide