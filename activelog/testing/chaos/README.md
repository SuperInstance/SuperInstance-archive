# Chaos Engineering Test Suite

A comprehensive chaos engineering framework for the ActiveLog system, designed to test system resilience, identify failure points, and validate recovery mechanisms.

## Overview

This chaos engineering test suite evaluates the ActiveLog system's ability to withstand various failure conditions including:

- **Network Failures**: Partitions, latency, DNS issues
- **Resource Exhaustion**: CPU, memory, disk, file descriptors  
- **Dependency Failures**: Database, cache, external services
- **Data Integrity Issues**: Corruption, transactions, backups

## Quick Start

### Prerequisites

```bash
# Install dependencies
npm install

# Ensure required tools are available
sudo apt-get update
sudo apt-get install -y stress-ng iptables tc docker.io
```

### Running Individual Test Categories

```bash
# Network chaos experiments
npm run chaos:network

# Resource stress experiments  
npm run chaos:resource

# Dependency failure experiments
npm run chaos:dependency

# Data integrity experiments
npm run chaos:data

# Run all experiments
npm run chaos:all

# Generate comprehensive report
npm run chaos:report
```

## Test Categories

### 🌐 Network Chaos (`scenarios/network-chaos.js`)

Tests system behavior under network-related failures:

- **Network Partitions**: Service isolation and reconnection
- **High Latency**: Response to increased network delays
- **Intermittent Failures**: Handling of sporadic connectivity issues
- **DNS Failures**: Service discovery resilience

**Key Experiments:**
- SSO to Data Bridge Network Partition
- High Latency Network Conditions  
- Intermittent Network Failures
- DNS Resolution Failure

### 💻 Resource Chaos (`scenarios/resource-chaos.js`)

Evaluates system performance under resource constraints:

- **CPU Stress**: High CPU load handling
- **Memory Exhaustion**: Out-of-memory conditions
- **Disk I/O Saturation**: Storage bottlenecks
- **File Descriptor Limits**: Resource limit handling

**Key Experiments:**
- High CPU Load on SSO Service
- Memory Exhaustion Attack
- Disk I/O Saturation
- File Descriptor Exhaustion
- Network Bandwidth Exhaustion

### 🔗 Dependency Chaos (`scenarios/dependency-chaos.js`)

Tests resilience to external dependency failures:

- **Database Failures**: Connection issues, timeouts
- **Cache Failures**: Redis outages, degraded performance  
- **Search Failures**: Elasticsearch cluster issues
- **External API Failures**: Third-party service outages

**Key Experiments:**
- Redis Cache Failure
- Database Connection Pool Exhaustion
- Elasticsearch Cluster Partition
- External API Service Timeout
- Cascading Service Failures

### 💾 Data Chaos (`scenarios/data-chaos.js`)

Validates data integrity and recovery mechanisms:

- **Transaction Integrity**: Connection loss during writes
- **Data Corruption**: Partial corruption detection/recovery
- **Backup Failures**: Backup system resilience
- **Migration Issues**: Schema change rollbacks

**Key Experiments:**
- Database Connection Interruption
- Partial Data Corruption
- Disk Space Exhaustion During Write
- Concurrent Write Conflicts
- Backup System Failure
- Data Migration Interruption

## Architecture

### Core Components

```
testing/chaos/
├── utils/
│   ├── chaos-engine.js       # Main chaos execution engine
│   └── chaos-reporter.js     # Comprehensive reporting
├── scenarios/
│   ├── network-chaos.js      # Network failure tests
│   ├── resource-chaos.js     # Resource exhaustion tests
│   ├── dependency-chaos.js   # Dependency failure tests
│   └── data-chaos.js         # Data integrity tests
└── reports/                  # Generated test reports
```

### Chaos Engine (`utils/chaos-engine.js`)

The core orchestration engine that:
- Registers and executes chaos experiments
- Monitors system health during failures
- Tracks recovery times and success rates
- Handles cleanup and restoration
- Generates detailed execution logs

**Key Features:**
- Pre/post experiment health checks
- Configurable recovery timeouts
- Automatic cleanup mechanisms
- Comprehensive metrics collection
- Real-time experiment monitoring

### Chaos Reporter (`utils/chaos-reporter.js`)

Comprehensive reporting system that:
- Aggregates results across all test categories
- Calculates resilience scores and ratings
- Identifies critical vulnerabilities and strengths
- Generates executive summaries and technical reports
- Provides actionable recommendations

**Report Formats:**
- HTML dashboard with interactive charts
- JSON data for programmatic analysis
- Markdown documentation
- Executive summary for stakeholders

## Experiment Configuration

### Experiment Structure

```javascript
{
  name: 'Experiment Name',
  description: 'What this experiment tests',
  action: 'chaos_action_type',
  target: {
    // Experiment-specific configuration
    type: 'resource_type',
    duration: 180000,
    parameters: {}
  },
  monitoringDuration: 240000,
  maxRecoveryTime: 120000,
  expectedOutcome: {
    // Expected behaviors during failure
    gracefulDegradation: true,
    automaticRecovery: true
  }
}
```

### Supported Chaos Actions

- `network_partition`: Create network isolation
- `resource_stress`: Exhaust system resources
- `dependency_failure`: Simulate service outages
- `data_corruption`: Test data integrity mechanisms
- `latency_injection`: Add network delays
- `cascading_failure`: Multi-service failure scenarios

## Safety Measures

### Built-in Protections

1. **Health Checks**: Pre-experiment system validation
2. **Timeout Limits**: Automatic experiment termination
3. **Cleanup Procedures**: Guaranteed state restoration
4. **Test Environment**: Isolated from production
5. **Gradual Escalation**: Progressive failure introduction

### Emergency Procedures

```bash
# Stop all active experiments
pkill -f "chaos"

# Clean up network rules
sudo iptables -F
sudo tc qdisc del dev lo root

# Restart services if needed
docker restart $(docker ps -q)
```

## Monitoring and Metrics

### System Health Monitoring

The chaos engine continuously monitors:
- Service availability and response times
- Resource utilization (CPU, memory, disk)
- Network connectivity and latency
- Database connections and query performance
- Error rates and failure patterns

### Custom Metrics

Each experiment tracks specific metrics:
- **Network**: Latency, packet loss, connection failures
- **Resource**: CPU usage, memory pressure, disk I/O
- **Dependency**: Connection pools, timeout rates, fallback usage
- **Data**: Transaction success rates, integrity checks, recovery times

## Report Generation

### Comprehensive Reports

```bash
npm run chaos:report
```

Generates multiple report formats:

1. **HTML Dashboard** (`comprehensive-chaos-report.html`)
   - Interactive visualizations
   - Drill-down experiment details
   - Resilience scoring
   - Vulnerability analysis

2. **JSON Data** (`comprehensive-chaos-report.json`)
   - Machine-readable results
   - API integration ready
   - Programmatic analysis support

3. **Markdown Report** (`comprehensive-chaos-report.md`)
   - Documentation friendly
   - Version control ready
   - Technical team sharing

4. **Executive Summary** (`executive-summary.md`)
   - Business impact focus
   - Strategic recommendations
   - Investment priorities
   - Risk assessment

### Key Report Sections

- **Resilience Score**: Overall system reliability rating
- **Critical Vulnerabilities**: High-priority security/reliability issues
- **System Strengths**: Validated resilience capabilities
- **Recovery Analysis**: Failure recovery effectiveness
- **Risk Assessment**: Business impact evaluation
- **Action Items**: Prioritized improvement tasks

## Integration

### CI/CD Integration

```yaml
# .github/workflows/chaos-testing.yml
name: Chaos Engineering Tests
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2AM
  workflow_dispatch:

jobs:
  chaos-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd testing/chaos && npm install
      - name: Run chaos tests
        run: cd testing/chaos && npm run chaos:all
      - name: Generate report
        run: cd testing/chaos && npm run chaos:report
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: chaos-reports
          path: testing/chaos/reports/
```

### Monitoring Integration

```javascript
// Example Prometheus metrics export
const prometheus = require('prom-client');

const chaosMetrics = {
  experimentsTotal: new prometheus.Counter({
    name: 'chaos_experiments_total',
    help: 'Total chaos experiments run',
    labelNames: ['category', 'status']
  }),
  recoveryTime: new prometheus.Histogram({
    name: 'chaos_recovery_time_seconds',
    help: 'Time to recover from chaos experiments',
    buckets: [1, 5, 10, 30, 60, 120, 300]
  })
};
```

## Best Practices

### Experiment Design

1. **Start Small**: Begin with low-impact experiments
2. **Gradual Escalation**: Increase severity progressively  
3. **Clear Hypotheses**: Define expected outcomes
4. **Measurable Impact**: Track quantifiable metrics
5. **Safe Boundaries**: Use circuit breakers and timeouts

### Execution Guidelines

1. **Test Environment**: Never run against production
2. **Team Coordination**: Notify relevant teams
3. **Monitoring**: Watch systems closely during tests
4. **Documentation**: Record observations and learnings
5. **Follow-up**: Act on discovered vulnerabilities

### Safety First

1. **Health Checks**: Validate system state before/after
2. **Automatic Cleanup**: Ensure state restoration
3. **Emergency Stops**: Have kill switches ready
4. **Recovery Procedures**: Document restoration steps
5. **Team Readiness**: Have support team available

## Troubleshooting

### Common Issues

**Experiment Won't Start**
```bash
# Check system permissions
sudo chmod +x scenarios/*.js

# Verify network tools
which iptables tc stress-ng

# Check Docker access
docker ps
```

**Network Rules Not Cleaning Up**
```bash
# Manual network cleanup
sudo iptables -F
sudo iptables -X
sudo tc qdisc del dev lo root
```

**High Resource Usage**
```bash
# Stop resource stress tests
pkill -f stress-ng
pkill -f chaos

# Check system load
top
iostat 1
```

### Debugging

Enable debug logging:
```bash
DEBUG=chaos:* npm run chaos:all
```

Check experiment logs:
```bash
tail -f reports/chaos.log
tail -f reports/chaos-error.log
```

## Contributing

### Adding New Experiments

1. Choose appropriate scenario file
2. Define experiment configuration
3. Implement custom chaos actions if needed
4. Add cleanup procedures
5. Update documentation

### Example New Experiment

```javascript
// In scenarios/network-chaos.js
const newExperiment = {
  name: 'Custom Network Experiment',
  description: 'Tests custom network scenario',
  action: 'custom_network_chaos',
  target: {
    customParameter: 'value'
  },
  expectedOutcome: {
    customBehavior: true
  }
};

// Custom executor
class CustomNetworkExecutor {
  static async executeCustomNetworkChaos(target) {
    // Implementation
  }
}
```

### Testing Guidelines

1. Test new experiments in isolation
2. Verify cleanup procedures work
3. Document expected behaviors
4. Add appropriate error handling
5. Update report generation if needed

## Resources

### External Dependencies

- **stress-ng**: System resource stress testing
- **iptables**: Network traffic control
- **tc (traffic control)**: Network delay/loss simulation
- **Docker**: Container management for service chaos
- **Node.js**: Test execution environment

### Reference Materials

- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [Netflix Chaos Monkey](https://github.com/Netflix/chaosmonkey)
- [Litmus Chaos](https://litmuschaos.io/)
- [Chaos Toolkit](https://chaostoolkit.org/)

### Team Contacts

- **Chaos Engineering Lead**: [Team Lead]
- **Site Reliability Team**: [SRE Team]
- **Platform Engineering**: [Platform Team]
- **Security Team**: [Security Team]

---

**⚠️ Important**: Always run chaos experiments in a controlled test environment. Never execute against production systems without proper safeguards and approvals.

**🎯 Goal**: Build confidence in system resilience through controlled failure injection and comprehensive analysis.