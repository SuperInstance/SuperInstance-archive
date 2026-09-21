# Monitoring Stack Guide for Continuous Performance Tracking

## Table of Contents
1. [Overview](#overview)
2. [Metrics Collection Architecture](#metrics-collection-architecture)
3. [Time-Series Database Setup](#time-series-database-setup)
4. [Monitoring Agent Design](#monitoring-agent-design)
5. [Anomaly Detection](#anomaly-detection)
6. [Dashboard Examples](#dashboard-examples)
7. [Alerting Configuration](#alerting-configuration)
8. [Scaling Considerations](#scaling-considerations)

---

## Overview

A robust monitoring stack enables continuous tracking of provider performance, early detection of issues, and automated fraud detection through statistical analysis.

### Monitoring Goals

1. **Performance Tracking**: Monitor benchmark scores over time
2. **Anomaly Detection**: Identify unusual patterns indicating fraud or issues
3. **SLA Compliance**: Verify providers meet performance commitments
4. **Capacity Planning**: Understand resource utilization trends
5. **Alerting**: Notify operators of critical issues

### Technology Stack Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│  Provider Nodes → Monitoring Agents → Push Gateway → Prometheus │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  • Prometheus (Short-term: 15 days)                             │
│  • VictoriaMetrics/Thanos (Long-term: 1+ years)                 │
│  • PostgreSQL (Metadata)                                         │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  • Anomaly Detection (ML models)                                │
│  • Statistical Analysis                                          │
│  • Aggregation & Rollups                                        │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                   VISUALIZATION LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  • Grafana Dashboards                                           │
│  • Alertmanager                                                 │
│  • API for External Access                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Port | Retention |
|-----------|---------|------|-----------|
| Prometheus | Metrics collection & storage | 9090 | 15 days |
| Node Exporter | System metrics | 9100 | N/A |
| Push Gateway | Push-based metrics | 9091 | N/A |
| Grafana | Visualization | 3000 | N/A |
| Alertmanager | Alert routing | 9093 | N/A |
| Loki | Log aggregation | 3100 | 30 days |
| VictoriaMetrics | Long-term storage | 8428 | 1+ years |

---

## Metrics Collection Architecture

### Metric Types

#### 1. Benchmark Metrics

```
# Geekbench scores
benchmark_cpu_single_core{provider="provider_xyz",cpu="AMD_EPYC_7763"} 1523
benchmark_cpu_multi_core{provider="provider_xyz",cpu="AMD_EPYC_7763"} 18945

# MLPerf throughput
benchmark_mlperf_throughput{provider="provider_xyz",model="resnet50",scenario="offline"} 3245.67

# Network performance
benchmark_network_bandwidth_gbps{provider="provider_xyz",direction="send"} 9.4
benchmark_network_latency_ms{provider="provider_xyz",percentile="p99"} 0.45

# Storage performance
benchmark_storage_iops{provider="provider_xyz",operation="randread",blocksize="4k"} 125000
benchmark_storage_bandwidth_mbps{provider="provider_xyz",operation="seqread"} 3500
```

#### 2. System Metrics

```
# CPU utilization
node_cpu_seconds_total{provider="provider_xyz",cpu="0",mode="user"}

# Memory usage
node_memory_MemAvailable_bytes{provider="provider_xyz"}

# Disk I/O
node_disk_read_bytes_total{provider="provider_xyz",device="nvme0n1"}

# Network I/O
node_network_receive_bytes_total{provider="provider_xyz",device="eth0"}
```

#### 3. Application Metrics

```
# Benchmark execution status
benchmark_execution_total{provider="provider_xyz",status="success"} 42
benchmark_execution_total{provider="provider_xyz",status="failed"} 3

# Benchmark duration
benchmark_execution_duration_seconds{provider="provider_xyz",benchmark="geekbench6"} 847.3

# TEE attestation
tee_attestation_valid{provider="provider_xyz",tee_type="SEV_SNP"} 1
```

### Collection Methods

#### 1. Pull-Based (Prometheus Scraping)

For persistent infrastructure:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'compute-marketplace'
    environment: 'production'

scrape_configs:
  # Provider node exporters
  - job_name: 'node-exporter'
    static_configs:
      - targets:
        - 'provider-1.example.com:9100'
        - 'provider-2.example.com:9100'
        - 'provider-3.example.com:9100'

  # Benchmark results exporter
  - job_name: 'benchmark-exporter'
    scrape_interval: 5m
    static_configs:
      - targets:
        - 'benchmark-exporter:9101'

  # Service discovery for dynamic providers
  - job_name: 'providers-sd'
    consul_sd_configs:
      - server: 'consul.example.com:8500'
        services: ['provider-node']
```

#### 2. Push-Based (Push Gateway)

For short-lived jobs and ephemeral instances:

```python
# push_metrics.py
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

def push_benchmark_results(provider_id: str, results: dict):
    """Push benchmark results to Prometheus Push Gateway."""

    registry = CollectorRegistry()

    # Create gauges
    single_core = Gauge(
        'benchmark_cpu_single_core',
        'Geekbench 6 single-core score',
        ['provider', 'cpu'],
        registry=registry
    )

    multi_core = Gauge(
        'benchmark_cpu_multi_core',
        'Geekbench 6 multi-core score',
        ['provider', 'cpu'],
        registry=registry
    )

    # Set values
    single_core.labels(
        provider=provider_id,
        cpu=results['cpu_model']
    ).set(results['single_core_score'])

    multi_core.labels(
        provider=provider_id,
        cpu=results['cpu_model']
    ).set(results['multi_core_score'])

    # Push to gateway
    push_to_gateway(
        'pushgateway.example.com:9091',
        job='benchmark-results',
        registry=registry
    )

# Example usage
results = {
    'cpu_model': 'AMD_EPYC_7763',
    'single_core_score': 1523,
    'multi_core_score': 18945
}

push_benchmark_results('provider_xyz', results)
```

### Metric Naming Conventions

Follow Prometheus best practices:

```
<namespace>_<subsystem>_<name>_<unit>

Examples:
- benchmark_cpu_single_core (counter/gauge, unitless score)
- benchmark_network_bandwidth_gbps (gauge, gigabits per second)
- benchmark_execution_duration_seconds (histogram, seconds)
- node_memory_available_bytes (gauge, bytes)
```

---

## Time-Series Database Setup

### Prometheus Installation

```bash
#!/bin/bash
# install_prometheus.sh

set -e

PROMETHEUS_VERSION="2.48.0"

echo "Installing Prometheus ${PROMETHEUS_VERSION}..."

# Download
wget https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz

# Extract
tar xzf prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz
sudo mv prometheus-${PROMETHEUS_VERSION}.linux-amd64 /opt/prometheus

# Create user
sudo useradd -r -s /bin/false prometheus

# Create directories
sudo mkdir -p /var/lib/prometheus
sudo mkdir -p /etc/prometheus
sudo chown -R prometheus:prometheus /var/lib/prometheus /etc/prometheus

# Create systemd service
cat <<'EOF' | sudo tee /etc/systemd/system/prometheus.service
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/opt/prometheus/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus/ \
  --storage.tsdb.retention.time=15d \
  --web.console.templates=/opt/prometheus/consoles \
  --web.console.libraries=/opt/prometheus/console_libraries

Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Create basic config
cat <<'EOF' | sudo tee /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus

echo "✓ Prometheus installed and running"
echo "Access at: http://localhost:9090"
```

### VictoriaMetrics for Long-Term Storage

VictoriaMetrics provides better compression and query performance for long-term data:

```bash
#!/bin/bash
# install_victoriametrics.sh

set -e

VM_VERSION="1.96.0"

echo "Installing VictoriaMetrics ${VM_VERSION}..."

# Download
wget https://github.com/VictoriaMetrics/VictoriaMetrics/releases/download/v${VM_VERSION}/victoria-metrics-linux-amd64-v${VM_VERSION}.tar.gz

# Extract
mkdir -p /opt/victoriametrics
tar xzf victoria-metrics-linux-amd64-v${VM_VERSION}.tar.gz -C /opt/victoriametrics

# Create user and directories
sudo useradd -r -s /bin/false victoriametrics
sudo mkdir -p /var/lib/victoriametrics
sudo chown -R victoriametrics:victoriametrics /var/lib/victoriametrics

# Create systemd service
cat <<'EOF' | sudo tee /etc/systemd/system/victoriametrics.service
[Unit]
Description=VictoriaMetrics
After=network.target

[Service]
User=victoriametrics
Group=victoriametrics
Type=simple
ExecStart=/opt/victoriametrics/victoria-metrics-prod \
  -storageDataPath=/var/lib/victoriametrics \
  -retentionPeriod=12 \
  -httpListenAddr=:8428

Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable victoriametrics
sudo systemctl start victoriametrics

echo "✓ VictoriaMetrics installed and running"
echo "Access at: http://localhost:8428"

# Configure Prometheus to remote write to VictoriaMetrics
cat <<'EOF' | sudo tee -a /etc/prometheus/prometheus.yml

remote_write:
  - url: http://localhost:8428/api/v1/write
EOF

sudo systemctl restart prometheus
```

### Docker Compose Stack

```yaml
# docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    restart: unless-stopped

  pushgateway:
    image: prom/pushgateway:v1.6.2
    container_name: pushgateway
    ports:
      - "9091:9091"
    restart: unless-stopped

  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.96.0
    container_name: victoriametrics
    volumes:
      - victoriametrics-data:/storage
    command:
      - '-storageDataPath=/storage'
      - '-retentionPeriod=12'
    ports:
      - "8428:8428"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.2.2
    container_name: grafana
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    restart: unless-stopped
    depends_on:
      - prometheus

  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    ports:
      - "9093:9093"
    restart: unless-stopped

  loki:
    image: grafana/loki:2.9.3
    container_name: loki
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    restart: unless-stopped

volumes:
  prometheus-data:
  victoriametrics-data:
  grafana-data:
```

Start the stack:

```bash
docker-compose up -d
```

---

## Monitoring Agent Design

### Benchmark Results Exporter

Custom exporter that exposes benchmark results as Prometheus metrics:

```python
# benchmark_exporter.py
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from typing import Dict
import time
import json
from pathlib import Path

class BenchmarkExporter:
    """Prometheus exporter for benchmark results."""

    def __init__(self, results_dir: str = "/var/benchmark/results"):
        self.results_dir = Path(results_dir)

        # Define metrics
        self.cpu_single_core = Gauge(
            'benchmark_cpu_single_core',
            'Geekbench 6 single-core score',
            ['provider', 'cpu_model']
        )

        self.cpu_multi_core = Gauge(
            'benchmark_cpu_multi_core',
            'Geekbench 6 multi-core score',
            ['provider', 'cpu_model']
        )

        self.mlperf_throughput = Gauge(
            'benchmark_mlperf_throughput',
            'MLPerf inference throughput',
            ['provider', 'model', 'scenario']
        )

        self.network_bandwidth = Gauge(
            'benchmark_network_bandwidth_gbps',
            'Network bandwidth in Gbps',
            ['provider', 'direction']
        )

        self.storage_iops = Gauge(
            'benchmark_storage_iops',
            'Storage IOPS',
            ['provider', 'operation', 'blocksize']
        )

        self.benchmark_duration = Histogram(
            'benchmark_execution_duration_seconds',
            'Benchmark execution duration',
            ['provider', 'benchmark_type']
        )

        self.benchmark_executions = Counter(
            'benchmark_execution_total',
            'Total benchmark executions',
            ['provider', 'status']
        )

        self.tee_attestation = Gauge(
            'tee_attestation_valid',
            'TEE attestation validity (1=valid, 0=invalid)',
            ['provider', 'tee_type']
        )

    def update_metrics(self):
        """Update metrics from latest benchmark results."""
        # Find latest results for each provider
        for result_file in self.results_dir.glob("*_report.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)

                provider_id = data['provider_id']

                # Update CPU benchmark metrics
                if 'benchmarks' in data and 'cpu' in data['benchmarks']:
                    cpu_data = data['benchmarks']['cpu']

                    self.cpu_single_core.labels(
                        provider=provider_id,
                        cpu_model=data['claimed_specs']['cpu']
                    ).set(cpu_data['single_core']['average'])

                    self.cpu_multi_core.labels(
                        provider=provider_id,
                        cpu_model=data['claimed_specs']['cpu']
                    ).set(cpu_data['multi_core']['average'])

                # Update network metrics
                if 'network' in data:
                    net_data = data['network']

                    self.network_bandwidth.labels(
                        provider=provider_id,
                        direction='send'
                    ).set(net_data.get('tcp_single_gbps', 0))

                # Update storage metrics
                if 'storage' in data:
                    storage_data = data['storage']

                    self.storage_iops.labels(
                        provider=provider_id,
                        operation='randread',
                        blocksize='4k'
                    ).set(storage_data.get('randread_iops', 0))

                # Update attestation status
                if 'validation' in data:
                    attestation_valid = 1 if data['validation'].get('tee_valid', False) else 0

                    self.tee_attestation.labels(
                        provider=provider_id,
                        tee_type=data.get('tee_type', 'unknown')
                    ).set(attestation_valid)

                # Update execution counter
                status = data.get('verdict', {}).get('status', 'unknown')
                self.benchmark_executions.labels(
                    provider=provider_id,
                    status=status.lower()
                ).inc()

            except Exception as e:
                print(f"Error processing {result_file}: {e}")

    def run(self, port: int = 9101, update_interval: int = 60):
        """Run the exporter."""
        # Start HTTP server
        start_http_server(port)
        print(f"Benchmark exporter listening on port {port}")

        # Update metrics periodically
        while True:
            self.update_metrics()
            time.sleep(update_interval)


if __name__ == "__main__":
    exporter = BenchmarkExporter()
    exporter.run(port=9101, update_interval=60)
```

Run as systemd service:

```ini
# /etc/systemd/system/benchmark-exporter.service
[Unit]
Description=Benchmark Metrics Exporter
After=network.target

[Service]
Type=simple
User=benchmark
ExecStart=/usr/bin/python3 /opt/benchmark/benchmark_exporter.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Provider Node Agent

Agent running on provider nodes to collect and push metrics:

```python
# provider_agent.py
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import psutil
import time
import subprocess
import json

class ProviderAgent:
    """Agent running on provider nodes."""

    def __init__(self, provider_id: str, push_gateway: str):
        self.provider_id = provider_id
        self.push_gateway = push_gateway
        self.registry = CollectorRegistry()

        # Define metrics
        self.cpu_usage = Gauge(
            'provider_cpu_usage_percent',
            'CPU usage percentage',
            ['provider', 'cpu'],
            registry=self.registry
        )

        self.memory_available = Gauge(
            'provider_memory_available_bytes',
            'Available memory in bytes',
            ['provider'],
            registry=self.registry
        )

        self.disk_usage = Gauge(
            'provider_disk_usage_percent',
            'Disk usage percentage',
            ['provider', 'mount'],
            registry=self.registry
        )

        self.gpu_utilization = Gauge(
            'provider_gpu_utilization_percent',
            'GPU utilization percentage',
            ['provider', 'gpu_id'],
            registry=self.registry
        )

    def collect_system_metrics(self):
        """Collect system metrics."""
        # CPU usage per core
        cpu_percents = psutil.cpu_percent(interval=1, percpu=True)
        for i, percent in enumerate(cpu_percents):
            self.cpu_usage.labels(
                provider=self.provider_id,
                cpu=str(i)
            ).set(percent)

        # Memory
        memory = psutil.virtual_memory()
        self.memory_available.labels(
            provider=self.provider_id
        ).set(memory.available)

        # Disk usage
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                self.disk_usage.labels(
                    provider=self.provider_id,
                    mount=partition.mountpoint
                ).set(usage.percent)
            except:
                pass

        # GPU metrics (if nvidia-smi available)
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=index,utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    gpu_id, utilization = line.split(',')
                    self.gpu_utilization.labels(
                        provider=self.provider_id,
                        gpu_id=gpu_id.strip()
                    ).set(float(utilization.strip()))
        except:
            pass

    def push_metrics(self):
        """Push metrics to gateway."""
        try:
            push_to_gateway(
                self.push_gateway,
                job=f'provider-agent',
                registry=self.registry,
                grouping_key={'provider': self.provider_id}
            )
        except Exception as e:
            print(f"Failed to push metrics: {e}")

    def run(self, interval: int = 15):
        """Run agent loop."""
        print(f"Provider agent started for {self.provider_id}")
        print(f"Pushing to {self.push_gateway} every {interval}s")

        while True:
            self.collect_system_metrics()
            self.push_metrics()
            time.sleep(interval)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: provider_agent.py <provider_id> <push_gateway>")
        sys.exit(1)

    provider_id = sys.argv[1]
    push_gateway = sys.argv[2]

    agent = ProviderAgent(provider_id, push_gateway)
    agent.run(interval=15)
```

---

## Anomaly Detection

### Statistical Anomaly Detection

```python
# anomaly_detector.py
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
import requests
from datetime import datetime, timedelta

@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    threshold: float
    explanation: str

class StatisticalAnomalyDetector:
    """Detect anomalies in benchmark scores using statistical methods."""

    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url

    def query_prometheus(self, query: str, start: datetime, end: datetime) -> List[float]:
        """Query Prometheus for historical data."""
        params = {
            'query': query,
            'start': start.timestamp(),
            'end': end.timestamp(),
            'step': '1h'
        }

        response = requests.get(
            f"{self.prometheus_url}/api/v1/query_range",
            params=params
        )
        response.raise_for_status()

        data = response.json()['data']['result']

        if not data:
            return []

        values = [float(v[1]) for v in data[0]['values']]
        return values

    def detect_zscore_anomaly(
        self,
        provider_id: str,
        metric: str,
        current_value: float,
        threshold: float = 3.0
    ) -> AnomalyResult:
        """
        Detect anomaly using Z-score method.

        Args:
            provider_id: Provider identifier
            metric: Metric name (e.g., 'benchmark_cpu_single_core')
            current_value: Current metric value
            threshold: Z-score threshold (default: 3.0)

        Returns:
            AnomalyResult
        """
        # Get historical data (last 30 days)
        end = datetime.now()
        start = end - timedelta(days=30)

        query = f'{metric}{{provider="{provider_id}"}}'
        historical_values = self.query_prometheus(query, start, end)

        if len(historical_values) < 10:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                threshold=threshold,
                explanation="Insufficient historical data"
            )

        # Calculate Z-score
        mean = np.mean(historical_values)
        std = np.std(historical_values)

        if std == 0:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                threshold=threshold,
                explanation="Zero standard deviation"
            )

        z_score = abs((current_value - mean) / std)

        is_anomaly = z_score > threshold

        explanation = f"Current value: {current_value:.2f}, " \
                     f"Historical mean: {mean:.2f}, " \
                     f"Std dev: {std:.2f}, " \
                     f"Z-score: {z_score:.2f}"

        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=z_score,
            threshold=threshold,
            explanation=explanation
        )

    def detect_iqr_anomaly(
        self,
        provider_id: str,
        metric: str,
        current_value: float,
        iqr_multiplier: float = 1.5
    ) -> AnomalyResult:
        """
        Detect anomaly using Interquartile Range (IQR) method.

        More robust to outliers than Z-score.
        """
        # Get historical data
        end = datetime.now()
        start = end - timedelta(days=30)

        query = f'{metric}{{provider="{provider_id}"}}'
        historical_values = self.query_prometheus(query, start, end)

        if len(historical_values) < 10:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                threshold=iqr_multiplier,
                explanation="Insufficient historical data"
            )

        # Calculate IQR
        q1 = np.percentile(historical_values, 25)
        q3 = np.percentile(historical_values, 75)
        iqr = q3 - q1

        # Calculate bounds
        lower_bound = q1 - iqr_multiplier * iqr
        upper_bound = q3 + iqr_multiplier * iqr

        is_anomaly = current_value < lower_bound or current_value > upper_bound

        # Calculate anomaly score (distance from nearest bound)
        if current_value < lower_bound:
            score = (lower_bound - current_value) / iqr
        elif current_value > upper_bound:
            score = (current_value - upper_bound) / iqr
        else:
            score = 0.0

        explanation = f"Current value: {current_value:.2f}, " \
                     f"Q1: {q1:.2f}, Q3: {q3:.2f}, " \
                     f"IQR: {iqr:.2f}, " \
                     f"Bounds: [{lower_bound:.2f}, {upper_bound:.2f}]"

        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=score,
            threshold=iqr_multiplier,
            explanation=explanation
        )

    def detect_trend_change(
        self,
        provider_id: str,
        metric: str,
        threshold_percent: float = 10.0
    ) -> AnomalyResult:
        """
        Detect sudden trend changes (e.g., performance degradation).

        Args:
            threshold_percent: Percentage change threshold
        """
        # Get recent data
        end = datetime.now()
        start = end - timedelta(days=14)

        query = f'{metric}{{provider="{provider_id}"}}'
        values = self.query_prometheus(query, start, end)

        if len(values) < 20:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                threshold=threshold_percent,
                explanation="Insufficient data for trend analysis"
            )

        # Split into two periods
        mid = len(values) // 2
        period1_mean = np.mean(values[:mid])
        period2_mean = np.mean(values[mid:])

        # Calculate percentage change
        percent_change = ((period2_mean - period1_mean) / period1_mean) * 100

        is_anomaly = abs(percent_change) > threshold_percent

        explanation = f"Period 1 mean: {period1_mean:.2f}, " \
                     f"Period 2 mean: {period2_mean:.2f}, " \
                     f"Change: {percent_change:.2f}%"

        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=abs(percent_change),
            threshold=threshold_percent,
            explanation=explanation
        )

    def comprehensive_check(
        self,
        provider_id: str,
        benchmark_results: Dict
    ) -> Dict:
        """
        Run comprehensive anomaly detection on benchmark results.

        Returns:
            Dictionary with anomaly detection results
        """
        results = {
            'provider_id': provider_id,
            'timestamp': datetime.now().isoformat(),
            'anomalies_detected': False,
            'checks': []
        }

        # Check CPU single-core score
        if 'single_core_score' in benchmark_results:
            zscore_result = self.detect_zscore_anomaly(
                provider_id,
                'benchmark_cpu_single_core',
                benchmark_results['single_core_score']
            )

            iqr_result = self.detect_iqr_anomaly(
                provider_id,
                'benchmark_cpu_single_core',
                benchmark_results['single_core_score']
            )

            results['checks'].append({
                'metric': 'cpu_single_core',
                'value': benchmark_results['single_core_score'],
                'zscore_anomaly': zscore_result.is_anomaly,
                'zscore_score': zscore_result.score,
                'iqr_anomaly': iqr_result.is_anomaly,
                'iqr_score': iqr_result.score,
                'explanation': zscore_result.explanation
            })

            if zscore_result.is_anomaly or iqr_result.is_anomaly:
                results['anomalies_detected'] = True

        # Check for performance degradation trend
        trend_result = self.detect_trend_change(
            provider_id,
            'benchmark_cpu_single_core',
            threshold_percent=10.0
        )

        results['checks'].append({
            'metric': 'cpu_single_core_trend',
            'trend_anomaly': trend_result.is_anomaly,
            'trend_score': trend_result.score,
            'explanation': trend_result.explanation
        })

        if trend_result.is_anomaly:
            results['anomalies_detected'] = True

        return results


# Example usage
if __name__ == "__main__":
    detector = StatisticalAnomalyDetector()

    # New benchmark results
    results = {
        'single_core_score': 1200,  # Suspiciously low
        'multi_core_score': 18000
    }

    # Check for anomalies
    anomaly_report = detector.comprehensive_check('provider_xyz', results)

    print(f"Anomalies detected: {anomaly_report['anomalies_detected']}")

    for check in anomaly_report['checks']:
        print(f"\n{check['metric']}:")
        print(f"  Value: {check.get('value', 'N/A')}")
        print(f"  Z-score anomaly: {check.get('zscore_anomaly', False)}")
        print(f"  IQR anomaly: {check.get('iqr_anomaly', False)}")
        print(f"  Trend anomaly: {check.get('trend_anomaly', False)}")
        print(f"  {check['explanation']}")
```

---

## Dashboard Examples

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "Compute Marketplace - Provider Performance",
    "panels": [
      {
        "id": 1,
        "title": "CPU Single-Core Score Over Time",
        "type": "graph",
        "targets": [
          {
            "expr": "benchmark_cpu_single_core{provider=\"$provider\"}",
            "legendFormat": "{{cpu_model}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "CPU Multi-Core Score Over Time",
        "type": "graph",
        "targets": [
          {
            "expr": "benchmark_cpu_multi_core{provider=\"$provider\"}",
            "legendFormat": "{{cpu_model}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Network Bandwidth",
        "type": "graph",
        "targets": [
          {
            "expr": "benchmark_network_bandwidth_gbps{provider=\"$provider\"}",
            "legendFormat": "{{direction}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Storage IOPS",
        "type": "graph",
        "targets": [
          {
            "expr": "benchmark_storage_iops{provider=\"$provider\"}",
            "legendFormat": "{{operation}} ({{blocksize}})"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "id": 5,
        "title": "TEE Attestation Status",
        "type": "stat",
        "targets": [
          {
            "expr": "tee_attestation_valid{provider=\"$provider\"}",
            "legendFormat": "{{tee_type}}"
          }
        ],
        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 16}
      },
      {
        "id": 6,
        "title": "Benchmark Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(benchmark_execution_total{provider=\"$provider\",status=\"success\"}[1h]) / rate(benchmark_execution_total{provider=\"$provider\"}[1h]) * 100"
          }
        ],
        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 16}
      }
    ],
    "templating": {
      "list": [
        {
          "name": "provider",
          "type": "query",
          "query": "label_values(benchmark_cpu_single_core, provider)"
        }
      ]
    },
    "time": {
      "from": "now-7d",
      "to": "now"
    },
    "refresh": "1m"
  }
}
```

### Create Dashboard Programmatically

```python
# create_grafana_dashboard.py
import requests
import json

def create_provider_dashboard(grafana_url: str, api_key: str):
    """Create Grafana dashboard for provider monitoring."""

    dashboard = {
        "dashboard": {
            "title": "Provider Performance Dashboard",
            "tags": ["benchmark", "providers"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "CPU Benchmark Scores",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "benchmark_cpu_single_core{provider=\"$provider\"}",
                            "legendFormat": "Single-Core"
                        },
                        {
                            "expr": "benchmark_cpu_multi_core{provider=\"$provider\"} / 10",
                            "legendFormat": "Multi-Core (/10)"
                        }
                    ]
                }
            ],
            "templating": {
                "list": [
                    {
                        "name": "provider",
                        "type": "query",
                        "query": "label_values(benchmark_cpu_single_core, provider)",
                        "multi": False,
                        "includeAll": False
                    }
                ]
            }
        },
        "overwrite": True
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{grafana_url}/api/dashboards/db",
        headers=headers,
        data=json.dumps(dashboard)
    )

    response.raise_for_status()

    dashboard_url = response.json()['url']
    print(f"Dashboard created: {grafana_url}{dashboard_url}")

if __name__ == "__main__":
    create_provider_dashboard(
        grafana_url="http://localhost:3000",
        api_key="YOUR_API_KEY"
    )
```

---

## Alerting Configuration

### Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'provider']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://webhook.example.com/alerts'

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

### Prometheus Alert Rules

```yaml
# alert_rules.yml
groups:
  - name: benchmark_alerts
    interval: 1m
    rules:
      - alert: BenchmarkScoreDrop
        expr: |
          (
            benchmark_cpu_single_core -
            benchmark_cpu_single_core offset 24h
          ) / benchmark_cpu_single_core offset 24h < -0.10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Benchmark score dropped >10% for {{ $labels.provider }}"
          description: "CPU single-core score has dropped significantly"

      - alert: TEEAttestationFailed
        expr: tee_attestation_valid == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "TEE attestation failed for {{ $labels.provider }}"
          description: "Provider {{ $labels.provider }} failed TEE attestation"

      - alert: BenchmarkExecutionFailure
        expr: |
          rate(benchmark_execution_total{status="failed"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High benchmark failure rate for {{ $labels.provider }}"
          description: "More than 10% of benchmarks are failing"

      - alert: ProviderOffline
        expr: up{job="provider-agent"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Provider {{ $labels.provider }} is offline"
          description: "No metrics received from provider for 5 minutes"

      - alert: AnomalyDetected
        expr: anomaly_score > 3
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Anomaly detected for {{ $labels.provider }}"
          description: "Statistical anomaly detected in benchmark results"
```

---

## Scaling Considerations

### High-Scale Architecture

For thousands of providers:

```
┌────────────────────────────────────────────────────────────┐
│                     COLLECTION LAYER                        │
│  Multiple Prometheus instances (federated)                 │
│  - Prometheus Shard 1 (Providers 1-1000)                   │
│  - Prometheus Shard 2 (Providers 1001-2000)                │
│  - Prometheus Shard N (Providers N...)                     │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│               AGGREGATION LAYER                             │
│  Thanos/Cortex for unified querying                        │
│  - Query Frontend                                           │
│  - Query Engine                                            │
│  - Store Gateway                                            │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│                 STORAGE LAYER                               │
│  Object Storage (S3/GCS) for long-term retention           │
│  - Compressed blocks                                        │
│  - Deduplicated                                            │
│  - Tiered (hot/warm/cold)                                  │
└────────────────────────────────────────────────────────────┘
```

### Performance Optimization

- **Metric Cardinality**: Limit label combinations
- **Retention Policies**: Short-term in Prometheus, long-term in object storage
- **Query Optimization**: Use recording rules for expensive queries
- **Downsampling**: Reduce resolution for older data

---

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [VictoriaMetrics](https://docs.victoriametrics.com/)
- [Thanos](https://thanos.io/)
- [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
