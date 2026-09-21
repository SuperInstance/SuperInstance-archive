# Monitoring Setup Guide

## Overview

Comprehensive monitoring setup for the Swarm Intelligence Platform using Prometheus, Grafana, Jaeger, and optional DataDog integration.

## Quick Start

```bash
# Deploy all monitoring components
kubectl apply -f infrastructure/kubernetes/monitoring/

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=prometheus -n swarm-intelligence --timeout=5m
kubectl wait --for=condition=ready pod -l app=grafana -n swarm-intelligence --timeout=5m

# Port forward to access dashboards
kubectl port-forward -n swarm-intelligence svc/grafana 3000:3000 &
kubectl port-forward -n swarm-intelligence svc/prometheus 9090:9090 &
kubectl port-forward -n swarm-intelligence svc/jaeger-query 16686:16686 &
```

## Access Monitoring Tools

### Grafana
- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: Get from secrets:
  ```bash
  kubectl get secret swarm-secrets -n swarm-intelligence \
    -o jsonpath='{.data.grafana-password}' | base64 -d
  ```

### Prometheus
- **URL**: http://localhost:9090
- **Query Language**: PromQL
- **No authentication** (internal only)

### Jaeger
- **URL**: http://localhost:16686
- **Purpose**: Distributed tracing
- **No authentication**

## Import Grafana Dashboards

### Method 1: Via UI

1. Navigate to http://localhost:3000
2. Login with admin credentials
3. Go to Dashboards → Import
4. Upload JSON files from `monitoring/grafana-dashboards/`:
   - `swarm-overview.json` - Main swarm metrics dashboard
   - `api-metrics.json` - API performance dashboard
   - `business-metrics.json` - Business KPIs
   - `cost-tracking.json` - Infrastructure costs
   - `alert-dashboard.json` - Active alerts

### Method 2: Via API

```bash
GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASS=$(kubectl get secret swarm-secrets -n swarm-intelligence \
  -o jsonpath='{.data.grafana-password}' | base64 -d)

# Import each dashboard
for dashboard in monitoring/grafana-dashboards/*.json; do
  curl -X POST \
    -H "Content-Type: application/json" \
    -u "$GRAFANA_USER:$GRAFANA_PASS" \
    -d @"$dashboard" \
    "$GRAFANA_URL/api/dashboards/db"
done
```

### Method 3: ConfigMap (Automated)

```bash
# Create ConfigMap with all dashboards
kubectl create configmap grafana-dashboards \
  --from-file=monitoring/grafana-dashboards/ \
  -n swarm-intelligence

# Grafana will auto-load dashboards from ConfigMap
```

## Configure Prometheus Alerts

### Apply Alert Rules

```bash
# Deploy alert rules
kubectl apply -f monitoring/prometheus-rules.yaml

# Verify rules are loaded
kubectl exec -n swarm-intelligence prometheus-0 -- \
  promtool check config /etc/prometheus/prometheus.yml

# Check active alerts
curl http://localhost:9090/api/v1/alerts | jq .
```

### Key Alert Rules

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| LowFPS | <30 FPS for 5min | Warning | Scale up core pods |
| CriticalLowFPS | <15 FPS for 2min | Critical | Page on-call |
| HighAPILatency | p99 >200ms for 5min | Warning | Investigate |
| HighMemoryUsage | >80% for 10min | Warning | Scale or optimize |
| PodCrashLooping | Restarts in 15min | Critical | Immediate fix |

## Configure Alertmanager

### Setup Slack Notifications

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: swarm-intelligence
data:
  alertmanager.yml: |
    global:
      slack_api_url: '${SLACK_WEBHOOK_URL}'

    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'slack-notifications'
      routes:
      - match:
          severity: critical
        receiver: 'slack-critical'
      - match:
          severity: warning
        receiver: 'slack-warnings'

    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#swarm-alerts'
        title: 'Swarm Intelligence Alert'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

    - name: 'slack-critical'
      slack_configs:
      - channel: '#swarm-critical'
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

    - name: 'slack-warnings'
      slack_configs:
      - channel: '#swarm-warnings'
        title: '⚠️  WARNING: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
EOF
```

### Setup PagerDuty for Critical Alerts

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: pagerduty-secret
  namespace: swarm-intelligence
stringData:
  integration-key: YOUR_PAGERDUTY_KEY
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-pagerduty
  namespace: swarm-intelligence
data:
  pagerduty.yml: |
    receivers:
    - name: 'pagerduty-critical'
      pagerduty_configs:
      - service_key: \${PAGERDUTY_KEY}
        description: '{{ .GroupLabels.alertname }}: {{ .Annotations.summary }}'
        severity: critical
EOF
```

## DataDog Integration (Optional)

### Deploy DataDog Agent

```bash
# Create secret with API key
kubectl create secret generic datadog-secret \
  --from-literal=api-key=YOUR_DATADOG_API_KEY \
  -n swarm-intelligence

# Deploy DataDog agent
kubectl apply -f monitoring/datadog-config.yaml

# Verify
kubectl get pods -n swarm-intelligence -l app=datadog-agent
```

### Configure Custom Metrics

DataDog will automatically collect:
- All Prometheus metrics with `swarm_*` prefix
- Kubernetes state metrics
- Container resource metrics
- APM traces from instrumented services

### Setup Synthetic Monitoring

```bash
# Install DataDog CLI
pip install datadog-api-client

# Create synthetic tests
python <<EOF
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.synthetics_api import SyntheticsApi
from datadog_api_client.v1.model.synthetics_api_test import SyntheticsAPITest

configuration = Configuration()
configuration.api_key["apiKeyAuth"] = "YOUR_API_KEY"
configuration.api_key["appKeyAuth"] = "YOUR_APP_KEY"

with ApiClient(configuration) as api_client:
    api_instance = SyntheticsApi(api_client)

    # Create API health check
    body = SyntheticsAPITest(
        name="Swarm API Health Check",
        type="api",
        subtype="http",
        request={
            "method": "GET",
            "url": "https://api.swarm-intelligence.example.com/health"
        },
        assertions=[
            {"type": "statusCode", "operator": "is", "target": 200},
            {"type": "responseTime", "operator": "lessThan", "target": 200}
        ],
        locations=["aws:us-east-1", "aws:us-west-2"],
        options={"tick_every": 60}
    )

    result = api_instance.create_synthetics_api_test(body=body)
    print(f"Created synthetic test: {result['public_id']}")
EOF
```

## Key Metrics to Monitor

### Application Metrics

```promql
# Agent Count
swarm_agents_total

# FPS by Pod
swarm_fps

# Processing Latency (p95, p99)
histogram_quantile(0.95, sum(rate(swarm_processing_duration_seconds_bucket[5m])) by (le))
histogram_quantile(0.99, sum(rate(swarm_processing_duration_seconds_bucket[5m])) by (le))

# Task Completion Rate
rate(swarm_tasks_completed_total[5m])

# Active Swarms
swarm_active_swarms_total
```

### API Metrics

```promql
# Request Rate
sum(rate(http_requests_total{service="swarm-api"}[5m])) by (endpoint)

# Latency
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))

# Error Rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# WebSocket Connections
sum(websocket_connections_active)
```

### Infrastructure Metrics

```promql
# CPU Usage
sum(rate(container_cpu_usage_seconds_total{namespace="swarm-intelligence"}[5m])) by (pod)

# Memory Usage
sum(container_memory_working_set_bytes{namespace="swarm-intelligence"}) by (pod) / 1024 / 1024 / 1024

# Network I/O
sum(rate(container_network_receive_bytes_total{namespace="swarm-intelligence"}[5m]))
sum(rate(container_network_transmit_bytes_total{namespace="swarm-intelligence"}[5m]))

# Disk Usage
kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes
```

## Custom Dashboard Queries

### 1M Agents Performance Dashboard

Create a dashboard with these panels:

```yaml
- Agent Distribution:
  sum(swarm_agents_total) by (behavior, pod)

- Memory per Agent:
  sum(container_memory_working_set_bytes{container="swarm-core"}) / sum(swarm_agents_total)

- Agent Updates per Second:
  sum(rate(swarm_agent_updates_total[1m]))

- FPS Histogram:
  histogram_quantile(0.50, swarm_fps_bucket)
  histogram_quantile(0.95, swarm_fps_bucket)
  histogram_quantile(0.99, swarm_fps_bucket)
```

## Troubleshooting

### Prometheus Not Scraping

```bash
# Check service discovery
kubectl exec -n swarm-intelligence prometheus-0 -- \
  wget -qO- http://localhost:9090/api/v1/targets | jq .

# Check ServiceMonitor
kubectl get servicemonitor -n swarm-intelligence

# Verify pod annotations
kubectl get pod <pod-name> -n swarm-intelligence -o yaml | grep -A 5 annotations
```

### Grafana Dashboard Not Loading Data

```bash
# Test Prometheus datasource
kubectl exec -n swarm-intelligence grafana-0 -- \
  curl http://prometheus:9090/api/v1/query?query=up

# Check Grafana logs
kubectl logs -n swarm-intelligence deployment/grafana

# Verify datasource configuration
kubectl get configmap grafana-datasources -n swarm-intelligence -o yaml
```

### High Cardinality Issues

If Prometheus memory usage is high:

```bash
# Check series count
curl http://localhost:9090/api/v1/status/tsdb | jq .

# Reduce retention
kubectl patch deployment prometheus -n swarm-intelligence \
  --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/args","value":["--storage.tsdb.retention.time=7d"]}]'

# Add relabel configs to drop high-cardinality labels
```

## Performance Benchmarks

Expected metrics for different scales:

| Scale | Agents | FPS | Memory/Agent | Prometheus Samples/s |
|-------|--------|-----|--------------|---------------------|
| Small | 100K | 60 | 64 bytes | 50K |
| Medium | 1M | 60 | 512 bytes | 500K |
| Large | 10M | 30 | 256 bytes | 5M |

## Backup and Restore

### Backup Prometheus Data

```bash
# Create snapshot
kubectl exec -n swarm-intelligence prometheus-0 -- \
  curl -XPOST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Copy snapshot
kubectl cp swarm-intelligence/prometheus-0:/prometheus/snapshots/<snapshot-id> \
  ./prometheus-backup-$(date +%Y%m%d)
```

### Backup Grafana Dashboards

```bash
# Export all dashboards
for dash in $(curl -s http://localhost:3000/api/search?query=\& | jq -r '.[].uri'); do
  curl -s http://localhost:3000/api/dashboards/${dash} | jq .dashboard > ${dash//\//-}.json
done
```

## Advanced Configuration

### Enable Remote Write (for long-term storage)

```yaml
# prometheus-config.yaml
remote_write:
  - url: https://prometheus-storage.example.com/api/v1/write
    basic_auth:
      username: admin
      password: ${REMOTE_WRITE_PASSWORD}
    queue_config:
      capacity: 10000
      max_shards: 50
      min_shards: 1
      max_samples_per_send: 5000
```

### Enable Grafana Alerting

```bash
# Configure SMTP for email alerts
kubectl edit configmap grafana-config -n swarm-intelligence

# Add SMTP configuration
[smtp]
enabled = true
host = smtp.gmail.com:587
user = alerts@example.com
password = ${SMTP_PASSWORD}
from_address = alerts@example.com
from_name = Swarm Intelligence Alerts
```

## Support

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/
- **Alert Examples**: See `monitoring/prometheus-rules.yaml`
- **Dashboard Examples**: See `monitoring/grafana-dashboards/`
