# ActiveLog Production Deployment Guide

This directory contains all the necessary files and scripts for deploying ActiveLog to production.

## Quick Start

1. **Prepare the server**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y docker.io docker-compose git curl
   sudo usermod -aG docker $USER
   ```

2. **Clone and deploy**:
   ```bash
   git clone <repository-url> /opt/activelog
   cd /opt/activelog
   ./deploy/production-deploy.sh
   ```

## Architecture Overview

### Multi-stage Docker Images
- **Builder stage**: Compiles dependencies and builds the application
- **Production stage**: Minimal runtime environment with only necessary components
- **Security**: Non-root users, minimal attack surface, security updates

### Service Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Frontend      │    │  API Gateway    │
│  Load Balancer  │────│   (React/Vue)   │────│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         │              ┌─────────────────┐             │
         └──────────────│   Microservices │─────────────┘
                        │                 │
                        │ • Auth Service  │
                        │ • Metadata      │
                        │ • File Proc.    │
                        │ • AI Orchestr.  │
                        │ • Notifications │
                        └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │    Storage      │
│   Database      │    │     Cache       │    │     (S3)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Monitoring Stack
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │────│     Grafana     │    │  Alertmanager   │
│   (Metrics)     │    │  (Dashboard)    │    │   (Alerts)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         │              ┌─────────────────┐             │
         └──────────────│    Fluentd      │─────────────┘
                        │ (Log Aggreg.)   │
                        └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │  Elasticsearch  │
                        │    (Optional)   │
                        └─────────────────┘
```

## Configuration Files

### Docker Compose Files
- `docker-compose.prod.yml` - Main application services
- `docker-compose.monitoring.yml` - Monitoring and observability services
- `docker-compose.test.yml` - Testing environment

### Service Configuration
- `nginx/nginx.conf` - Load balancer configuration
- `monitoring/prometheus.yml` - Metrics collection
- `monitoring/grafana/` - Dashboard configurations
- `logging/fluent.conf` - Log aggregation rules

### Security
- `secrets/` - Encrypted secrets management
- SSL/TLS certificates
- Network policies and firewall rules

## Resource Requirements

### Minimum Requirements
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **Network**: 1Gbps

### Recommended Production
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 200GB+ SSD
- **Network**: 10Gbps
- **Backup**: Automated offsite backups

## Resource Limits

Each service has configured resource limits:

| Service | CPU Limit | Memory Limit | CPU Reservation | Memory Reservation |
|---------|-----------|--------------|-----------------|-------------------|
| API Gateway | 1.0 | 1GB | 0.25 | 256MB |
| Auth Service | 0.5 | 512MB | 0.1 | 128MB |
| Metadata Service | 0.5 | 512MB | 0.1 | 128MB |
| File Processor | 1.0 | 1GB | 0.25 | 256MB |
| AI Orchestrator | 1.0 | 1GB | 0.25 | 256MB |
| Notification | 0.5 | 512MB | 0.1 | 128MB |
| PostgreSQL | 2.0 | 2GB | 0.5 | 512MB |
| Redis | 0.5 | 512MB | 0.1 | 128MB |
| Prometheus | 1.0 | 1GB | 0.25 | 256MB |
| Grafana | 0.5 | 512MB | 0.1 | 128MB |

## Health Checks

All services include comprehensive health checks:

- **HTTP Health Endpoints**: `/health` for web services
- **Database Connectivity**: Connection and query tests
- **Cache Availability**: Redis ping tests
- **External Services**: OpenAI and S3 connectivity
- **Resource Utilization**: CPU, memory, and disk monitoring

## Secrets Management

### Automated Secret Generation
```bash
cd secrets/
./setup-secrets.sh
```

### Manual Secret Configuration
Update these files with your actual values:
- `openai_api_key.txt` - OpenAI API key
- `aws_access_key.txt` - AWS access key
- `aws_secret_key.txt` - AWS secret key
- `smtp_*.txt` - Email configuration

### Security Best Practices
- All secrets stored as Docker secrets
- File permissions: 600 (owner read/write only)
- Secrets mounted as files, not environment variables
- Regular rotation of credentials

## Monitoring and Observability

### Metrics Collection
- **Application Metrics**: Custom business metrics
- **System Metrics**: CPU, memory, disk, network
- **Container Metrics**: Docker container statistics
- **Database Metrics**: PostgreSQL performance
- **Cache Metrics**: Redis statistics

### Log Aggregation
- **Structured Logging**: JSON format with metadata
- **Log Levels**: Debug, Info, Warning, Error, Critical
- **Log Rotation**: Automatic cleanup and compression
- **Security Filtering**: Sensitive data exclusion

### Alerting Rules
- **Service Availability**: Uptime monitoring
- **Performance Thresholds**: Response time alerts
- **Error Rates**: Application error monitoring
- **Resource Usage**: CPU/memory/disk alerts
- **Business Metrics**: User activity and feature usage

### Dashboards
- **System Overview**: High-level health status
- **Service Details**: Individual service metrics
- **Infrastructure**: Database and cache performance
- **Business Metrics**: User engagement and activity

## Deployment Process

### Zero-Downtime Deployment
1. **Health Check**: Verify current system health
2. **Backup**: Create database and volume backups
3. **Image Pull**: Download latest Docker images
4. **Rolling Update**: Update services one by one
5. **Health Verification**: Ensure new deployment is healthy
6. **Rollback Ready**: Automatic rollback on failure

### Deployment Environments
- **Development**: Local development environment
- **Testing**: Automated testing environment
- **Staging**: Pre-production testing
- **Production**: Live environment

## Backup and Recovery

### Automated Backups
- **Database**: Daily PostgreSQL dumps
- **Files**: S3 bucket synchronization
- **Configurations**: Version-controlled settings
- **Logs**: Retention and archival

### Recovery Procedures
- **Point-in-time Recovery**: Database restoration
- **Service Recovery**: Container restart procedures
- **Data Recovery**: File and metadata restoration
- **Disaster Recovery**: Complete system rebuild

## Security Measures

### Network Security
- **Firewall**: UFW configuration with minimal open ports
- **SSL/TLS**: Let's Encrypt certificates with auto-renewal
- **Network Isolation**: Docker networks for service isolation
- **Rate Limiting**: Nginx-based request throttling

### Application Security
- **Authentication**: JWT-based user authentication
- **Authorization**: Role-based access control
- **Input Validation**: Request sanitization and validation
- **Security Headers**: OWASP recommended headers

### Container Security
- **Non-root Users**: All services run as non-root
- **Image Scanning**: Automated vulnerability scanning
- **Resource Limits**: Prevent resource exhaustion
- **Secrets Management**: Encrypted secrets storage

## Maintenance

### Regular Tasks
- **System Updates**: OS and package updates
- **Certificate Renewal**: SSL certificate automation
- **Log Cleanup**: Automated log rotation
- **Backup Verification**: Restore testing
- **Security Scanning**: Vulnerability assessments

### Monitoring Tasks
- **Alert Review**: Regular alert tuning
- **Dashboard Updates**: Metric visualization improvements
- **Performance Optimization**: Resource usage analysis
- **Capacity Planning**: Growth projection and scaling

## Troubleshooting

### Common Issues
- **Service Startup Failures**: Check logs and dependencies
- **Database Connection Issues**: Verify credentials and network
- **High Resource Usage**: Monitor and optimize containers
- **SSL Certificate Issues**: Check Let's Encrypt renewal

### Debugging Commands
```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View service logs
docker-compose -f docker-compose.prod.yml logs -f <service>

# Check resource usage
docker stats

# Database connection test
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# Redis connection test
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### Log Locations
- **Application Logs**: `/var/log/fluentd/application/`
- **Infrastructure Logs**: `/var/log/fluentd/infrastructure/`
- **Error Logs**: `/var/log/fluentd/errors/`
- **Nginx Logs**: `/var/log/nginx/`

## Scaling

### Horizontal Scaling
- **Load Balancer**: Nginx upstream configuration
- **Service Replicas**: Docker Swarm or Kubernetes
- **Database**: Read replicas and connection pooling
- **Cache**: Redis clustering

### Vertical Scaling
- **Resource Limits**: Increase CPU/memory allocations
- **Storage**: Expand volume sizes
- **Network**: Upgrade bandwidth capacity

## Support

### Documentation
- **API Documentation**: OpenAPI/Swagger specifications
- **Architecture Diagrams**: System design documentation
- **Runbooks**: Operational procedures
- **Troubleshooting Guides**: Common issue resolution

### Monitoring
- **Health Dashboard**: Real-time system status
- **Alert Notifications**: Email, Slack, PagerDuty integration
- **Performance Metrics**: Response time and throughput
- **Error Tracking**: Application error monitoring

For additional support, consult the main project documentation or contact the development team.