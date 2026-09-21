# ActiveLog Instance Manager

Advanced AWS instance lifecycle management service with intelligent cost optimization, predictive scaling, and automated scheduling.

## 🚀 Features

### Core Capabilities
- **Instance Lifecycle Management** - Complete EC2 instance lifecycle control
- **Automatic Scheduling** - Start/stop instances based on schedules and patterns
- **Workload-based Scaling** - Intelligent scaling based on actual usage patterns
- **Cost Optimization** - Comprehensive cost analysis and optimization recommendations
- **Spot Instance Integration** - Automated spot instance management for cost savings
- **Reserved Instance Optimization** - Analysis and recommendations for Reserved Instances
- **Multi-cloud Support** - Manage instances across AWS, Azure, and GCP
- **Predictive Scaling** - ML-based scaling predictions
- **Usage Pattern Learning** - Automatically learn and optimize based on usage patterns

### Advanced Features
- **Development/Production Switching** - Environment-aware instance management
- **Night/Weekend Downscaling** - Automatic downscaling during off-hours
- **Cost Alerts and Limits** - Real-time cost monitoring with alerts
- **Failover to Cheaper Regions** - Automatic failover to cost-effective regions
- **Interruption Handling** - Smart handling of spot instance interruptions

## 🏗️ Architecture

```
Instance Manager Service (Port 8330)
├── Core/
│   ├── Lifecycle Manager - Instance state management
│   └── Instance Controller - Direct instance control
├── Scheduling/
│   ├── Scheduler - Automated scheduling engine
│   └── Workload Analyzer - Usage pattern analysis
├── Scaling/
│   ├── Auto Scaler - Intelligent scaling decisions
│   └── Spot Manager - Spot instance optimization
├── Cost/
│   ├── Cost Optimizer - Cost analysis and recommendations
│   └── Reserved Instance Optimizer - RI analysis
├── Predictive/
│   └── Predictor - ML-based scaling predictions
├── Multi-cloud/
│   └── Multi Cloud Manager - Cross-cloud management
└── Monitoring/
    └── Metrics Collector - Performance monitoring
```

## 🚀 Quick Start

### Prerequisites
- AWS credentials configured
- Python 3.8+
- Required permissions for EC2, CloudWatch, Cost Explorer

### Installation

1. **Clone and Setup**
```bash
cd /home/activeloguser/activelog/services/instance-manager
chmod +x start.sh
```

2. **Install Dependencies**
```bash
./start.sh install-deps
```

3. **Configure Environment**
```bash
export AWS_DEFAULT_REGION=us-west-2
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

4. **Start Service**
```bash
./start.sh start
```

5. **Verify Installation**
```bash
./start.sh health
curl http://localhost:8330/health
```

## 📖 Usage Guide

### Basic Instance Management

**List All Instances**
```bash
curl http://localhost:8330/instances
```

**Start an Instance**
```bash
curl -X POST http://localhost:8330/instances/i-1234567890abcdef0/start
```

**Stop an Instance**
```bash
curl -X POST http://localhost:8330/instances/i-1234567890abcdef0/stop
```

### Scheduling

**Create a Business Hours Schedule**
```bash
curl -X POST http://localhost:8330/schedule \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Business Hours - Web Servers",
    "schedule_type": "business_hours",
    "action": "start",
    "instance_ids": ["i-1234567890abcdef0"],
    "business_hours_start": "09:00:00",
    "business_hours_end": "17:00:00",
    "business_days": [0, 1, 2, 3, 4],
    "timezone": "America/New_York"
  }'
```

**Create a Night Shutdown Schedule**
```bash
curl -X POST http://localhost:8330/schedule \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Night Shutdown",
    "schedule_type": "smart",
    "action": "stop", 
    "instance_ids": ["i-1234567890abcdef0"],
    "smart_pattern": "night_shutdown",
    "smart_parameters": {
      "night_hour": 22,
      "morning_hour": 8
    }
  }'
```

### Cost Optimization

**Run Cost Analysis**
```bash
curl -X POST http://localhost:8330/cost/optimize
```

**Analyze Spot Opportunities**
```bash
curl -X POST http://localhost:8330/cost/optimize \\
  -H "Content-Type: application/json" \\
  -d '{"type": "spot"}'
```

### Workload Analysis

**Analyze Scaling Needs**
```bash
curl -X POST http://localhost:8330/scaling/analyze \\
  -H "Content-Type: application/json" \\
  -d '{
    "instance_ids": ["i-1234567890abcdef0"],
    "time_range_hours": 168
  }'
```

**Get Predictive Forecast**
```bash
curl -X POST http://localhost:8330/predictive/forecast \\
  -H "Content-Type: application/json" \\
  -d '{
    "instance_ids": ["i-1234567890abcdef0"],
    "forecast_hours": 24
  }'
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_DEFAULT_REGION` | AWS region | `us-west-2` |
| `INSTANCE_MANAGER_PORT` | Service port | `8330` |
| `ENVIRONMENT` | Environment (dev/staging/prod) | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `COST_ALERT_THRESHOLD` | Monthly cost alert threshold | `1000` |
| `AUTO_SCALING_ENABLED` | Enable auto-scaling | `true` |

### Configuration File

Create `/home/activeloguser/activelog/services/instance-manager/config.json`:

```json
{
  "aws_region": "us-west-2",
  "auto_scaling_enabled": true,
  "scaling_check_interval_minutes": 5,
  "cost_alert_threshold_usd": 1000.0,
  "notification_from_email": "alerts@yourcompany.com",
  "smtp_host": "smtp.yourcompany.com",
  "smtp_port": 587
}
```

## 🔧 API Reference

### Instance Management

#### `GET /instances`
List all managed instances with status and metrics.

#### `POST /instances/{instance_id}/start`
Start a specific instance.
- **Parameters**: `wait` (boolean) - Wait for instance to be running

#### `POST /instances/{instance_id}/stop`
Stop a specific instance.
- **Parameters**: `force` (boolean) - Force stop if needed

### Scheduling

#### `GET /schedule`
Get all active schedules.

#### `POST /schedule`
Create a new schedule.

**Request Body**:
```json
{
  "name": "Schedule Name",
  "schedule_type": "business_hours|cron|one_time|smart",
  "action": "start|stop|restart",
  "instance_ids": ["i-1234567890abcdef0"],
  "timezone": "UTC"
}
```

#### `PUT /schedule/{schedule_id}`
Update an existing schedule.

#### `DELETE /schedule/{schedule_id}`
Delete a schedule.

### Cost Optimization

#### `POST /cost/optimize`
Run comprehensive cost optimization analysis.

#### `GET /cost/alerts`
Get current cost alerts.

### Scaling

#### `POST /scaling/analyze`
Analyze current workload and scaling needs.

#### `GET /scaling/rules`
Get current auto-scaling rules.

#### `PUT /scaling/rules/{rule_name}`
Update a scaling rule.

### Monitoring

#### `GET /metrics/dashboard`
Get metrics for monitoring dashboard.

#### `GET /health`
Service health check endpoint.

## 🏷️ Instance Tagging

The Instance Manager uses specific tags for operation:

| Tag | Purpose | Example |
|-----|---------|---------|
| `AutoScaling` | Enable auto-scaling | `enabled` |
| `Environment` | Environment classification | `production` |
| `Schedule` | Associated schedule ID | `schedule-uuid` |
| `CostCenter` | Cost allocation | `engineering` |
| `Owner` | Resource owner | `team@company.com` |

**Enable Auto-scaling for an Instance**:
```bash
aws ec2 create-tags \\
  --resources i-1234567890abcdef0 \\
  --tags Key=AutoScaling,Value=enabled
```

## 📊 Monitoring & Alerting

### Built-in Metrics
- Instance utilization (CPU, Memory, Network)
- Cost tracking and trends
- Scaling events and decisions
- Schedule execution success/failure
- Spot instance interruption rates

### Cost Alerts
- Daily cost threshold alerts
- Monthly budget alerts
- Unusual spending pattern detection
- Resource waste notifications

### Integration
- CloudWatch metrics and alarms
- SNS notifications
- Email alerts
- Slack integration (via webhooks)

## 🛡️ Security

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "cloudwatch:*",
        "ce:GetCostAndUsage",
        "pricing:GetProducts"
      ],
      "Resource": "*"
    }
  ]
}
```

### Security Best Practices
- Use IAM roles instead of access keys when possible
- Enable CloudTrail for API call logging
- Restrict API access using security groups
- Use encrypted connections (HTTPS)
- Implement proper authentication for production

## 🔍 Troubleshooting

### Common Issues

**Service Won't Start**
```bash
# Check dependencies
./start.sh diagnostics

# Check logs
./start.sh logs

# Verify AWS credentials
aws sts get-caller-identity
```

**Scaling Not Working**
1. Check instance has `AutoScaling=enabled` tag
2. Verify CloudWatch metrics are available
3. Check scaling rules configuration
4. Review scaling history for errors

**Schedules Not Executing**
1. Verify schedule is enabled
2. Check timezone configuration
3. Review schedule execution logs
4. Ensure instances exist and are accessible

**Cost Analysis Failing**
1. Verify Cost Explorer API access
2. Check AWS billing permissions
3. Ensure region supports Cost Explorer
4. Review API rate limits

### Log Files
- Service logs: `/home/activeloguser/activelog/logs/instance-manager.log`
- Schedule execution: Check service logs
- API access: Check service logs with DEBUG level

### Debugging Commands
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
./start.sh restart

# Follow logs in real-time
./start.sh follow-logs

# Check service status
./start.sh status

# Run health diagnostics
./start.sh health
```

## 🚀 Deployment

### Production Deployment

1. **Configure Production Environment**
```bash
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export COST_ALERT_THRESHOLD=5000
```

2. **Use IAM Roles** (Recommended)
```bash
# Remove access key environment variables
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY

# Attach IAM role to EC2 instance running the service
```

3. **Enable Service Auto-start**
```bash
# Add to crontab for auto-start on reboot
echo "@reboot /home/activeloguser/activelog/services/instance-manager/start.sh start" | crontab -
```

4. **Setup Monitoring**
```bash
# Create CloudWatch alarms for service health
aws cloudwatch put-metric-alarm \\
  --alarm-name "InstanceManager-HealthCheck" \\
  --alarm-description "Instance Manager Health Check" \\
  --metric-name "HealthCheck" \\
  --namespace "ActiveLog/InstanceManager" \\
  --statistic Average \\
  --period 300 \\
  --threshold 1 \\
  --comparison-operator LessThanThreshold
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 8330

CMD ["python", "main.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: instance-manager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: instance-manager
  template:
    metadata:
      labels:
        app: instance-manager
    spec:
      containers:
      - name: instance-manager
        image: activelog/instance-manager:latest
        ports:
        - containerPort: 8330
        env:
        - name: AWS_DEFAULT_REGION
          value: "us-west-2"
        - name: ENVIRONMENT  
          value: "production"
```

## 📈 Performance Optimization

### Scaling the Service
- Use multiple instances behind a load balancer
- Implement Redis for shared state
- Use database for persistent storage
- Enable API caching

### Cost Optimization Tips
1. **Enable Auto-scaling**: Tag instances with `AutoScaling=enabled`
2. **Use Schedules**: Implement business hours scheduling
3. **Review Recommendations**: Act on cost optimization recommendations
4. **Monitor Spot Prices**: Use spot instances for suitable workloads
5. **Right-size Instances**: Regularly review utilization metrics

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone <repository>
cd instance-manager

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Start in development mode
ENVIRONMENT=development python main.py
```

### Testing
```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/

# Run with coverage
python -m pytest --cov=.
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README and inline documentation
- **Issues**: Report bugs via GitHub issues
- **Community**: Join our Slack channel
- **Enterprise Support**: Contact sales@activelog.com

---

**ActiveLog Instance Manager** - Intelligent AWS instance management for modern infrastructure.

*Version: 1.0.0 | Last Updated: 2024*