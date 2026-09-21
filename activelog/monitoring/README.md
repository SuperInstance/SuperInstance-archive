# ActiveLog Monitoring Stack

This comprehensive monitoring setup provides observability for all ActiveLog services including:

## Components

### Core Monitoring
- **Prometheus** - Metrics collection and time-series database
- **Grafana** - Visualization and dashboards
- **AlertManager** - Alert routing and management

### Tracing & APM
- **Jaeger** - Distributed tracing
- **Tempo** - Trace storage backend
- **OpenTelemetry Collector** - Unified observability data pipeline

### Logging
- **Loki** - Log aggregation and querying
- **Promtail** - Log shipping agent
- **Vector** - High-performance log collection and transformation
- **Fluentd** - Log processing and forwarding
- **Elasticsearch** - Log storage and indexing
- **Kibana** - Log analysis and visualization

### Infrastructure Monitoring
- **Node Exporter** - System metrics
- **cAdvisor** - Container metrics
- **PostgreSQL Exporter** - Database metrics
- **Redis Exporter** - Cache metrics
- **Nginx Exporter** - Web server metrics
- **Blackbox Exporter** - Endpoint monitoring

### Advanced Features
- **Performance Regression Detector** - Automated performance analysis
- **Service Mesh Observability** - Istio integration
- **Thanos** - Long-term Prometheus storage
- **Grafana OnCall** - Alert management
- **MinIO** - Object storage for artifacts

## Quick Start

1. Start the monitoring stack:
   ```bash
   cd ~/activelog/monitoring
   docker-compose up -d
   ```

2. Access the services:
   - Grafana: http://localhost:3000 (admin/admin123)
   - Prometheus: http://localhost:9090
   - Jaeger: http://localhost:16686
   - AlertManager: http://localhost:9093
   - Kibana: http://localhost:5601
   - Loki: http://localhost:3100

## Service Monitoring

### Monitored Services
All ActiveLog services are configured for monitoring:

- **Core Services**: API Gateway, Auth, Metadata, File Processor
- **AI Services**: AI Orchestrator, Document AI, ML Pipeline
- **Data Services**: Sync Engine, Batch Import, Data Export
- **Collaboration**: Workspaces, Real-time features
- **Infrastructure**: Cache, Backup, Notifications, Workflows

### Metrics Collected
- **Latency**: Request/response times, processing durations
- **Throughput**: Request rates, operation counts
- **Errors**: Error rates, failure counts
- **Resources**: CPU, memory, disk usage
- **Business**: User actions, file operations, AI inference

## Dashboards

### Available Dashboards
1. **Infrastructure Overview** - System resources and containers
2. **Services Health** - Service status and performance
3. **Distributed Tracing** - Trace analysis and service dependencies
4. **Application Metrics** - Business-specific metrics
5. **Security Monitoring** - Authentication and access patterns

### Custom Dashboards
Create custom dashboards by:
1. Accessing Grafana at http://localhost:3000
2. Importing dashboard JSON from `/monitoring/dashboards/`
3. Creating new dashboards with Prometheus metrics

## Alerting

### Alert Rules
Comprehensive alerting rules cover:
- **System**: High CPU, memory, disk usage
- **Services**: Service down, high latency, error rates
- **Business**: Failed operations, queue backlogs
- **Security**: Suspicious activities, failed logins
- **Performance**: Regression detection

### Alert Channels
Configure alert notifications:
- Slack webhooks
- Email notifications
- PagerDuty integration
- Discord/Teams webhooks

### Custom Alerts
Add custom alerts by editing:
- `/monitoring/prometheus/rules/alerting_rules.yml`
- `/monitoring/alertmanager/alertmanager.yml`

## Performance Regression Detection

Automated system detects:
- Latency increases (>50% from baseline)
- Throughput decreases (>30% from baseline)
- Error rate increases (>2x from baseline)

Configure thresholds in:
- `/monitoring/performance-regression/config.yaml`

## Log Aggregation

### Log Sources
- Application logs from all services
- System logs (syslog, auth, kernel)
- Container logs
- Nginx access/error logs
- Database logs

### Log Processing
- Structured JSON parsing
- Log level extraction
- Trace correlation
- Metric generation from logs

### Query Logs
- **Loki**: Use LogQL in Grafana
- **Elasticsearch**: Use Kibana for analysis

## Service Mesh Integration

For Kubernetes deployments with Istio:
1. Apply service mesh configurations:
   ```bash
   kubectl apply -f /monitoring/service-mesh/
   ```

2. Configure telemetry collection
3. Monitor service-to-service communication

## Maintenance

### Data Retention
- **Prometheus**: 30 days local, long-term via Thanos
- **Loki**: 30 days
- **Elasticsearch**: 7 days (configurable)
- **Jaeger**: 24 hours

### Backup
Regular backups include:
- Grafana dashboards and configs
- Prometheus configuration
- Alert rules and contacts

### Scaling
For high-load environments:
1. Scale Prometheus with federation
2. Use Thanos for long-term storage
3. Scale Loki with multiple instances
4. Use Elasticsearch cluster

## Troubleshooting

### Common Issues
1. **High memory usage**: Adjust retention periods
2. **Missing metrics**: Check service /metrics endpoints
3. **No alerts**: Verify AlertManager configuration
4. **Slow queries**: Optimize Prometheus queries

### Debug Commands
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs -f prometheus

# Restart specific service
docker-compose restart grafana

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets
```

## Configuration Files

### Key Files
- `docker-compose.yml` - Main orchestration
- `prometheus/prometheus.yml` - Metrics collection
- `prometheus/rules/` - Alert rules
- `grafana/dashboards/` - Dashboard definitions
- `loki/loki-config.yml` - Log aggregation
- `performance-regression/config.yaml` - Regression detection

### Environment Variables
Set these in `.env` file:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
ONCALL_SECRET_KEY=your-secret-key-here
```

## Security

### Authentication
- Grafana: admin/admin123 (change in production)
- Basic auth for Prometheus/AlertManager
- API keys for external integrations

### Network Security
- Internal monitoring network (172.20.0.0/16)
- Exposed ports only for UI access
- TLS termination at proxy level

### Data Protection
- Log data anonymization
- Metric data retention limits
- Secure secret management

## Contributing

To add new monitoring:
1. Add service metrics endpoint
2. Update Prometheus configuration
3. Create service-specific dashboard
4. Add relevant alert rules
5. Update documentation

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review configuration files
3. Consult Grafana/Prometheus documentation
4. Submit issues to the ActiveLog repository