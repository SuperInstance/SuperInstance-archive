# Instance Orchestrator - ActiveLog Auto-Scaling Service

The Instance Orchestrator is an intelligent auto-scaling system that monitors resource usage on the current t3.micro instance and automatically scales to t3.medium when needed, ensuring seamless service continuity.

## 🚀 Features

### Core Capabilities
- **Real-time Monitoring**: Continuous CPU and memory monitoring with configurable thresholds
- **Automatic Scaling**: Launches t3.medium instance when usage exceeds 70% for 5+ minutes
- **Seamless Migration**: Migrates all services with zero-downtime using advanced orchestration
- **DNS Management**: Automatically updates Route53 records to point to the new instance
- **Safety Features**: Comprehensive rollback and error handling mechanisms

### Advanced Features
- **Web Dashboard**: Real-time monitoring interface with metrics and controls
- **Health Checks**: Continuous service health monitoring and verification
- **Smart Migration**: Preserves service configurations, data, and nginx settings
- **Cost Optimization**: Automatically terminates old instances after successful migration
- **Audit Trail**: Comprehensive logging of all scaling operations

## 📊 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   t3.micro      │    │ Instance        │    │   t3.medium     │
│   (Current)     │───▶│ Orchestrator    │───▶│   (Target)      │
│                 │    │                 │    │                 │
│ • PersonalLog   │    │ • Monitors      │    │ • PersonalLog   │
│ • FishingLog    │    │ • Migrates      │    │ • FishingLog    │
│ • DMLog         │    │ • Updates DNS   │    │ • DMLog         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       ▲
         ▼                       ▼                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Route53      │    │   Dashboard     │    │    Services     │
│                 │    │                 │    │                 │
│ • personallog.ai│    │ • Metrics       │    │ • Health Checks │
│ • fishinglog.ai │    │ • Controls      │    │ • Auto-restart  │
│ • dmlog.ai      │    │ • Logs          │    │ • Configuration │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Installation & Setup

### Prerequisites
```bash
# Required software
sudo yum update -y
sudo yum install -y python3 python3-pip git

# AWS CLI (if not already installed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Installation
```bash
# Clone or navigate to the service directory
cd /home/activeloguser/activelog/services/instance-orchestrator

# Install Python dependencies
pip3 install -r requirements.txt --user

# Make scripts executable
chmod +x startup.sh test_orchestrator.py

# Test the installation
python3 test_orchestrator.py
```

### Configuration
The service uses `config.yaml` for configuration. Key settings:

```yaml
monitoring:
  cpu_threshold: 70.0          # CPU % to trigger scaling
  memory_threshold: 70.0       # Memory % to trigger scaling
  check_interval: 60           # Check every 60 seconds
  threshold_duration: 300      # Must be sustained for 5 minutes

aws:
  region: "us-west-2"
  target_instance_type: "t3.medium"
  
services:
  service_names:
    - "personallog-backend"
    - "fishinglog"
    - "dmlog-session-logger"
```

## 🚀 Usage

### Starting the Service
```bash
# Start the orchestrator
./startup.sh start

# Check status
./startup.sh status

# View real-time logs
./startup.sh logs
```

### Using the Dashboard
Once started, access the web dashboard at:
```
http://YOUR_EC2_IP:8500
```

The dashboard provides:
- Real-time CPU/memory metrics with visual indicators
- Current instance information and status
- Service health monitoring
- Manual scaling trigger (for testing)
- Live activity logs and notifications

### Manual Scaling
For testing or emergency situations:
```bash
# Via dashboard: Click "Trigger Manual Scale" button
# Via API:
curl -X POST http://localhost:8500/trigger-scale
```

### System Service Installation
```bash
# Install as system service (runs on boot)
sudo ./startup.sh install
sudo systemctl start instance-orchestrator
sudo systemctl status instance-orchestrator
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard interface |
| `/api/status` | GET | JSON status and metrics |
| `/health` | GET | Health check endpoint |
| `/trigger-scale` | POST | Manual scaling trigger |

### API Response Example
```json
{
  "status": "running",
  "scaling_in_progress": false,
  "current_usage": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1
  },
  "thresholds": {
    "cpu_threshold": 70.0,
    "memory_threshold": 70.0
  },
  "instance_details": {
    "instance_id": "i-0123456789abcdef0",
    "instance_type": "t3.micro",
    "public_ip": "34.223.235.20",
    "state": "running"
  },
  "threshold_breaches": 0,
  "services": ["personallog-backend", "fishinglog", "dmlog-session-logger"]
}
```

## 🔄 Scaling Workflow

When resource usage exceeds thresholds for the configured duration:

### Phase 1: Detection & Validation
1. **Threshold Monitoring**: Continuous monitoring detects sustained high usage
2. **Safety Checks**: Validates no recent scaling events and system stability
3. **Resource Assessment**: Confirms scaling is necessary and feasible

### Phase 2: New Instance Provisioning
4. **Instance Launch**: Creates new t3.medium instance with identical configuration
5. **System Preparation**: Installs required software and dependencies
6. **Security Setup**: Configures security groups, SSH access, and networking

### Phase 3: Service Migration
7. **Service Backup**: Creates safe backup of current service states
8. **File Transfer**: Migrates all service files and configurations using rsync
9. **Database Migration**: Transfers any local databases or persistent data
10. **Configuration Update**: Updates service configurations for new environment

### Phase 4: DNS & Traffic Switching
11. **DNS Update**: Updates Route53 A records to point to new instance IP
12. **Propagation Wait**: Allows time for DNS changes to propagate globally
13. **Health Verification**: Confirms all services are responding on new instance

### Phase 5: Cleanup & Finalization
14. **Traffic Validation**: Monitors traffic flow to new instance
15. **Old Instance Termination**: Safely terminates the original t3.micro instance
16. **Cleanup**: Removes temporary files and updates internal state

## 🛡️ Safety Features

### Rollback Mechanisms
- **Automatic Rollback**: If migration fails, traffic reverts to original instance
- **Health Check Validation**: Continuous monitoring ensures service availability
- **Timeout Protection**: Maximum time limits prevent hanging operations

### Error Handling
- **Graceful Degradation**: Service continues monitoring even if scaling fails
- **Comprehensive Logging**: Detailed logs for troubleshooting
- **Alert System**: Notifications for critical failures (configurable)

### Cost Protection
- **Scaling Limits**: Maximum number of scaling events per day
- **Minimum Intervals**: Prevents rapid successive scaling operations
- **Instance Cleanup**: Automatic termination of old instances to control costs

## 📊 Monitoring & Alerts

### Metrics Tracked
- **CPU Usage**: Real-time and historical CPU utilization
- **Memory Usage**: Physical and virtual memory consumption
- **Service Health**: Individual service status and response times
- **Instance State**: EC2 instance health and configuration
- **Network Performance**: Bandwidth and latency metrics

### Dashboard Features
- **Real-time Graphs**: Live updating resource utilization charts
- **Historical Data**: Trends and patterns over time
- **Alert Status**: Current threshold breaches and scaling state
- **Service Matrix**: Health status of all managed services

## 🧪 Testing

### Unit Tests
```bash
# Run comprehensive test suite
python3 test_orchestrator.py

# Include CPU load simulation
python3 test_orchestrator.py --load-test
```

### Integration Testing
```bash
# Test with manual threshold trigger
curl -X POST http://localhost:8500/trigger-scale

# Monitor scaling process
./startup.sh logs
```

### Health Checks
```bash
# System health validation
./startup.sh health

# Service endpoint testing
curl http://localhost:8500/health
```

## 📝 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check dependencies
pip3 install -r requirements.txt --user

# Verify AWS credentials
aws sts get-caller-identity

# Check logs for errors
tail -f /var/log/instance-orchestrator.log
```

#### Dashboard Not Accessible
```bash
# Check if service is running
./startup.sh status

# Verify port 8500 is open
netstat -tulpn | grep :8500

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-06ffa55bce9e97a7f
```

#### Scaling Operation Fails
```bash
# Check AWS permissions
aws iam get-user

# Verify instance limits
aws service-quotas get-service-quota --service-code ec2 --quota-code L-34B43A08

# Review detailed logs
grep "ERROR" /var/log/instance-orchestrator.log
```

### Log Locations
- **Main Log**: `/var/log/instance-orchestrator.log`
- **Service Logs**: `/home/ubuntu/activelog/services/*/service.log`
- **System Logs**: `/var/log/messages` or `journalctl -u instance-orchestrator`

## 🔧 Configuration Reference

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `CPU_THRESHOLD` | CPU threshold percentage | 70.0 |
| `MEMORY_THRESHOLD` | Memory threshold percentage | 70.0 |
| `AWS_REGION` | AWS region for operations | us-west-2 |
| `PORT` | Dashboard port | 8500 |

### Configuration File Options
See `config.yaml` for comprehensive configuration options including:
- Monitoring thresholds and intervals
- AWS instance and networking settings
- Service definitions and health checks
- Safety limits and rollback settings
- Dashboard and notification preferences

## 🚀 Production Deployment

### Pre-deployment Checklist
- [ ] AWS credentials configured with appropriate permissions
- [ ] Security groups allow necessary ports (8500 for dashboard)
- [ ] Route53 hosted zones configured for all domains
- [ ] All dependent services (PersonalLog, FishingLog, DMLog) are operational
- [ ] SSL certificates are properly configured
- [ ] Backup and recovery procedures are in place

### Deployment Steps
1. **Install Dependencies**: Ensure all system requirements are met
2. **Configure Service**: Update config.yaml with production settings
3. **Test Installation**: Run test suite to verify functionality
4. **Install as Service**: Use `./startup.sh install` for automatic startup
5. **Monitor Deployment**: Watch logs and dashboard for initial stability
6. **Document Access**: Record dashboard URL and management commands

### Production Monitoring
- **Set up external monitoring** for the dashboard endpoint
- **Configure log rotation** to manage disk space
- **Establish backup procedures** for configuration and logs
- **Create runbooks** for common operational procedures
- **Set up alerting** for critical failures or scaling events

## 📈 Performance & Scaling

### Resource Requirements
- **CPU**: Minimal impact, typically <1% CPU usage during monitoring
- **Memory**: ~50MB RAM footprint for the orchestrator service
- **Network**: Low bandwidth for monitoring, higher during migration
- **Storage**: Log files and temporary migration data

### Scaling Characteristics
- **Detection Time**: 5-10 minutes from threshold breach to scaling initiation
- **Migration Time**: 5-15 minutes depending on service complexity and data volume
- **DNS Propagation**: 1-3 minutes for Route53 updates to take effect
- **Total Scaling Time**: Typically 10-30 minutes for complete operation

### Optimization Tips
- **Adjust thresholds** based on actual usage patterns and requirements
- **Optimize service startup** times to reduce migration duration
- **Use placement groups** to ensure optimal network performance between instances
- **Consider reserved instances** for cost optimization if scaling frequently

## 🤝 Integration

### Service Integration
The Instance Orchestrator integrates with:
- **All ActiveLog Services**: PersonalLog, FishingLog, DMLog, BusinessLog
- **Authentication System**: Preserves JWT tokens and user sessions
- **Nginx Configuration**: Maintains reverse proxy and SSL settings
- **Route53 DNS**: Updates all domain mappings automatically

### External Integration Points
- **AWS CloudWatch**: Can export metrics for advanced monitoring
- **Slack/Email Notifications**: Configurable alerting for scaling events
- **Log Aggregation**: Compatible with ELK stack or CloudWatch Logs
- **Monitoring Systems**: Prometheus/Grafana integration available

## 🔒 Security

### Access Controls
- **IAM Permissions**: Uses least-privilege access for AWS operations
- **SSH Key Management**: Secure key-based authentication for instance access
- **Network Security**: Security group rules restrict access to necessary ports
- **Dashboard Security**: Consider adding authentication for production use

### Data Protection
- **Encryption in Transit**: All AWS API calls use HTTPS/TLS
- **Secure Migration**: Service data encrypted during transfer
- **Audit Logging**: All operations logged with timestamps and details
- **Backup Security**: Temporary files cleaned up after operations

## 📞 Support & Maintenance

### Regular Maintenance
- **Log Rotation**: Monitor and rotate log files to prevent disk space issues
- **Security Updates**: Keep system packages and dependencies updated  
- **Configuration Review**: Periodically review thresholds and settings
- **Permission Auditing**: Verify AWS permissions remain appropriate

### Support Resources
- **Documentation**: This README and inline code documentation
- **Test Suite**: Comprehensive testing for validation and troubleshooting
- **Log Analysis**: Detailed logging for operational insight
- **Health Endpoints**: Built-in health checks for monitoring integration

## 🎯 Future Enhancements

### Planned Features
- **Multi-region Support**: Scale across AWS regions for ultimate resilience
- **Advanced Scheduling**: Time-based scaling for predictable load patterns
- **Cost Optimization**: Spot instance integration for development environments
- **Enhanced Monitoring**: Custom CloudWatch metrics and dashboards
- **Notification System**: Slack, email, and SMS alerts for scaling events

### Extension Points
- **Plugin Architecture**: Support for custom scaling triggers and actions
- **API Extensions**: Additional endpoints for advanced management
- **Dashboard Enhancements**: More detailed metrics and historical analysis
- **Integration APIs**: Webhooks and callbacks for external system integration

---

**Instance Orchestrator** - Intelligent auto-scaling for the ActiveLog ecosystem  
🚀 Built for reliability, designed for scale, optimized for cost efficiency.