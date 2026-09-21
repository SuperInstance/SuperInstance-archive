# ActiveLog.AI Master Infrastructure Deployment

## Overview

This repository contains the complete AWS infrastructure deployment for ActiveLog.AI's master platform, including:

- **Master Infrastructure**: Core services (Backend, Repository, Deployer, Trainer, Builder, DefaultUser, Runner)
- **Domain-Specific Servers**: PersonalLog, MakerLog, BusinessLog, DMLog, FishingLog, etc.
- **Security**: IAM roles, security groups, WAF, CloudTrail, Secrets Manager
- **Databases**: PostgreSQL (RDS), Redis (ElastiCache), DocumentDB
- **Monitoring**: CloudWatch dashboards, alarms, cost tracking
- **Auto-scaling**: Intelligent scaling based on load and cost optimization

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CloudFront CDN                           │
│                 (Global Distribution)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Route 53 DNS                                │
│    activelog.ai, activeledger.ai, makerslog.ai             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Application Load Balancer                      │
│                 (Multi-AZ, SSL)                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│ Master       │ │ Domain  │ │   Domain    │
│ Services     │ │ Servers │ │   Servers   │
│              │ │         │ │             │
│ - Backend    │ │Personal │ │ Business    │
│ - Repository │ │MakerLog │ │ DMLog       │
│ - Deployer   │ │LucidDr. │ │ FishingLog  │
│ - Trainer    │ │etc.     │ │ etc.        │
│ - Builder    │ │         │ │             │
│ - Runner     │ │         │ │             │
└──────────────┘ └─────────┘ └─────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Databases                                 │
│  PostgreSQL (RDS) │ Redis (ElastiCache) │ DocumentDB       │
│  User accounts    │ Session management  │ Flexible data    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0
- Python 3.8+
- jq (for JSON processing)

### 1. Deploy Master Infrastructure

```bash
# Clone and navigate to deployment directory
cd infrastructure/aws/master-deployment/

# Make deployment script executable
chmod +x deploy-complete-ecosystem.sh

# Deploy with default settings
./deploy-complete-ecosystem.sh

# Or deploy with minimal resources for cost savings
./deploy-complete-ecosystem.sh --min-resources

# Deploy to specific region
./deploy-complete-ecosystem.sh --region us-west-2
```

### 2. Monitor Deployment

```bash
# Check deployment status
aws cloudformation describe-stacks --region us-east-1

# View logs
tail -f deployment-*.log

# Check health of deployed services
python3 scale-management.py --report
```

### 3. Configure Auto-scaling

```bash
# Set up intelligent auto-scaling
python3 scale-management.py --schedule

# Start continuous monitoring
python3 scale-management.py --monitor

# Generate cost analysis report
python3 scale-management.py --report
```

## Infrastructure Components

### Master Services

| Service | Instance Type | Purpose |
|---------|---------------|---------|
| MasterBackend | t3.medium | Authentication, JWT, payments |
| MasterRepository | t3.large | Deployment files, version control |
| MasterDeployer | t3.medium | Custom deployment generation |
| MasterTrainer | g4dn.xlarge | Model training (GPU) |
| MasterBuilder | t3.large | CI/CD pipeline |
| MasterDefaultUser | t3.small | Template configurations |
| MasterRunner | c5.2xlarge | High-performance compute |

### Domain Services

Each domain (PersonalLog, MakerLog, BusinessLog, etc.) includes:

- **Backend**: Load balancing, policy management
- **Repository**: Domain-specific deployments  
- **Deployer**: Hardware-optimized versions
- **Trainer**: Domain-specific AI models
- **Builder**: Feature development
- **DefaultUser**: Initial user states
- **Runner**: Compute services

### Security Features

- **IAM Roles**: Least-privilege access for each service
- **Security Groups**: Minimal required ports only
- **Secrets Manager**: Encrypted storage of API keys and passwords
- **WAF**: DDoS protection and request filtering
- **CloudTrail**: Comprehensive audit logging
- **VPC**: Isolated network with public/private subnets

### Database Layer

- **PostgreSQL (RDS)**: User accounts, structured data
- **Redis (ElastiCache)**: Session management, caching
- **DocumentDB**: Flexible document storage
- **Automated Backups**: Cross-region replication enabled

## Auto-scaling Configuration

The system implements intelligent auto-scaling based on:

### Load-based Scaling

```python
def scale_instance(server_name, load_percentage):
    if load_percentage > 80:
        # Scale up
        if current_type == "t3.small":
            resize_to("t3.medium")
        elif current_type == "t3.medium":
            resize_to("t3.large")
    elif load_percentage < 20 and not_peak_hours():
        # Scale down to save costs
        downgrade_instance()
```

### Domain-specific Configuration

Each domain has customized scaling parameters:

- **PersonalLog**: Cost-optimized, t3.micro → t3.medium
- **MakerLog**: Performance-focused, t3.small → c5.large  
- **BusinessLog**: High availability, t3.medium → c5.xlarge
- **DMLog**: GPU-enabled, t3.medium → g4dn.2xlarge

### Cost Optimization

- **Scheduled Scaling**: Scale down during off-peak hours
- **Spot Instances**: For non-critical workloads
- **Reserved Instances**: For predictable baseline load
- **Instance Right-sizing**: Continuous optimization

## Monitoring & Alerting

### CloudWatch Dashboards

- **Master Dashboard**: Overall system health
- **Domain Dashboards**: Per-domain metrics
- **Cost Dashboard**: Spending tracking

### Alerts

- **High CPU**: > 80% for 2 consecutive periods
- **High Memory**: > 85% for 5 minutes
- **Cost Alerts**: Monthly budget thresholds
- **Health Check Failures**: Immediate notification

### Logging

- **Application Logs**: Structured JSON logging
- **Infrastructure Logs**: CloudTrail, VPC Flow Logs
- **Performance Logs**: X-Ray tracing

## Cost Analysis

### Estimated Monthly Costs

| Component | Cost (USD) |
|-----------|------------|
| Master Infrastructure | $800 |
| Domain Services | $1,200 |
| Databases | $300 |
| Load Balancers | $50 |
| CloudFront | $25 |
| Monitoring | $30 |
| **Total** | **~$2,405** |

### Cost Optimization Features

- **Auto-shutdown**: During nights/weekends
- **Intelligent Scaling**: Scale to zero for unused domains
- **S3 Intelligent Tiering**: Automatic storage optimization
- **Reserved Instances**: Up to 60% savings on predictable workloads

## Deployment Commands

### Full Ecosystem Deployment

```bash
# Complete deployment with all domains
./deploy-complete-ecosystem.sh

# Minimal resources for development
./deploy-complete-ecosystem.sh --min-resources

# Production deployment with high availability
./deploy-complete-ecosystem.sh --environment production
```

### Domain-specific Deployment

```bash
# Deploy only specific domains
export DOMAINS="PersonalLog,MakerLog,BusinessLog"
./deploy-complete-ecosystem.sh
```

### Infrastructure Management

```bash
# Scale specific domain
python3 scale-management.py --domain PersonalLog

# Generate cost report
python3 scale-management.py --report

# Emergency scale-down (cost saving)
python3 scale-management.py --emergency-scale-down
```

## Security Best Practices

### Network Security

- VPC with private subnets for databases
- NAT Gateways for secure internet access
- Security groups with minimal required ports
- Network ACLs for additional layer of protection

### Access Control

- IAM roles with least-privilege access
- MFA required for admin access
- Service-linked roles for AWS services
- Cross-account access for management

### Data Protection

- Encryption at rest for all databases
- Encryption in transit with SSL/TLS
- Secrets Manager for sensitive data
- Regular security scanning

## Troubleshooting

### Common Issues

1. **Deployment Failures**
   ```bash
   # Check CloudFormation events
   aws cloudformation describe-stack-events --stack-name activelog-ai-master
   
   # Check Terraform state
   terraform show
   ```

2. **Auto-scaling Issues**
   ```bash
   # Check ASG activities
   aws autoscaling describe-scaling-activities
   
   # View CloudWatch metrics
   python3 scale-management.py --report
   ```

3. **High Costs**
   ```bash
   # Analyze cost breakdown
   aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31
   
   # Optimize instance sizes
   python3 scale-management.py --optimize-costs
   ```

### Recovery Procedures

1. **Database Recovery**
   ```bash
   # Restore from backup
   aws rds restore-db-instance-from-db-snapshot
   ```

2. **Service Recovery**
   ```bash
   # Restart failed services
   ./deploy-complete-ecosystem.sh --service-recovery
   ```

## Support & Maintenance

### Regular Maintenance

- **Weekly**: Review cost reports and optimize
- **Monthly**: Update AMIs and security patches
- **Quarterly**: Capacity planning and architecture review

### Monitoring

- **24/7**: Automated health checks and alerting
- **Business Hours**: Active monitoring and response
- **Escalation**: PagerDuty integration for critical issues

### Updates

- **Rolling Updates**: Zero-downtime deployments
- **Blue-Green**: For major infrastructure changes
- **Canary**: For new feature rollouts

## Next Steps

1. **DNS Configuration**: Update nameservers for your domains
2. **SSL Certificates**: Request certificates via AWS Certificate Manager
3. **Application Deployment**: Deploy your application code
4. **Monitoring Setup**: Configure alerts and notifications
5. **Performance Testing**: Load test all endpoints

## Contact

For support or questions:
- **Email**: infrastructure@activelog.ai
- **Slack**: #infrastructure-team
- **Documentation**: https://docs.activelog.ai/infrastructure