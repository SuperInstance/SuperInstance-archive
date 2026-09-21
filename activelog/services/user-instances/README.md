# ActiveLog User Instances Service

Complete user-isolated instance architecture service running on port 8476.

## Overview

This service provides dedicated, isolated EC2 instances for ActiveLog users with:
- **Complete User Isolation**: Each paid user gets their own dedicated EC2 instance
- **User-Owned Data**: Users have full control and ownership of their data
- **Tier-Based Provisioning**: Instance specifications based on user subscription tier
- **Comprehensive Security**: User-specific VPCs, security groups, and encryption keys
- **Real-time Monitoring**: CloudWatch integration with custom metrics
- **Transparent Billing**: Detailed cost tracking and real-time billing

## Architecture

### Core Components

1. **UserInstanceManager**: Core EC2 provisioning and lifecycle management
2. **Instance Monitoring**: CloudWatch metrics and health monitoring  
3. **Billing System**: Real-time cost tracking and usage billing
4. **Security**: User-specific encryption, VPCs, and access controls
5. **FastAPI Service**: RESTful API for instance management

### User Isolation Features

- **Dedicated EC2 Instances**: Every paid user gets their own instance
- **Private VPCs**: Isolated networking per user
- **User-Specific Encryption**: Individual KMS keys per user
- **Security Groups**: User-only access controls
- **Data Ownership**: Users own all data, ActiveLog has orchestration-only access

## API Endpoints

### Instance Management
- `POST /instances` - Create new user instance
- `GET /instances/status` - Get instance status and metrics
- `POST /instances/start` - Start stopped instance
- `POST /instances/stop` - Stop running instance  
- `DELETE /instances` - Terminate instance (destroys data)

### Monitoring & Billing
- `GET /instances/billing` - Get detailed billing information
- `GET /health` - Service health check

### Admin Endpoints
- `GET /admin/instances` - List all instances (admin only)

## User Tiers & Instance Types

| Tier | Instance Type | Monthly Estimate | CPU | Memory | Storage |
|------|---------------|------------------|-----|--------|---------|
| Starter | t3.small | ~$50 | 2 vCPU | 2 GB | 100 GB |
| Professional | t3.medium | ~$150 | 2 vCPU | 4 GB | 250 GB |
| Business | t3.large | ~$350 | 2 vCPU | 8 GB | 500 GB |
| Enterprise | m5.xlarge | ~$750 | 4 vCPU | 16 GB | 1000 GB |
| Premium | m5.2xlarge | ~$1500 | 8 vCPU | 32 GB | 2000 GB |

## Security Features

### Encryption
- User-specific KMS keys for EBS encryption
- All data encrypted at rest and in transit
- Users control their encryption keys

### Network Isolation  
- Dedicated VPC per user
- Private subnets with controlled internet access
- Security groups allowing minimal required access
- VPC Flow Logs for audit trails

### Access Controls
- JWT token authentication
- Role-based access (user vs admin)
- Rate limiting per user
- Audit logging for all actions

## Installation & Setup

1. **Clone and Navigate**:
```bash
cd ~/activelog/services/user-instances/
```

2. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure Environment**:
```bash
cp .env.template .env
# Edit .env with your AWS credentials and configuration
```

4. **AWS Setup**:
- Configure AWS credentials with EC2, VPC, KMS permissions
- Create base AMI with ActiveLog services
- Set up SNS topic for CloudWatch alarms

5. **Start Service**:
```bash
python main.py
```

## Usage Examples

### Create User Instance
```bash
curl -X POST "http://localhost:8476/instances" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tier": "professional"}'
```

### Check Instance Status
```bash
curl -X GET "http://localhost:8476/instances/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Billing Information
```bash
curl -X GET "http://localhost:8476/instances/billing" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Monitoring & Alerts

### CloudWatch Metrics
- CPU Utilization
- Memory Usage (with CloudWatch agent)
- Network I/O
- Disk I/O
- Status Check Failures

### Automated Alerts
- High CPU usage (>80%)
- High memory usage (>90%)
- Instance status check failures
- Cost threshold exceeded

### Health Monitoring
- Instance health scores (0-100)
- Real-time metric collection
- Automated recovery procedures

## Billing & Cost Management

### Cost Components
- **Compute**: EC2 instance hourly rates
- **Storage**: EBS volume costs  
- **Network**: Data transfer charges
- **Encryption**: KMS key usage

### Billing Features
- Real-time cost tracking
- Monthly cost estimates
- Usage-based billing
- Detailed cost breakdown
- Cost alert notifications

## Development

### Running Tests
```bash
pytest tests/
```

### Docker Deployment
```bash
docker build -t user-instances .
docker run -p 8476:8476 user-instances
```

### Database Schema
The service uses SQLite for billing records with tables:
- `billing_sessions` - Active billing sessions
- `usage_metrics` - Historical usage data  
- `monthly_summaries` - Monthly billing summaries

## Integration

### Required Services
- **Auth Service** (port 8001): User authentication
- **Billing Service** (port 8005): Payment processing
- **Monitoring Service** (port 8020): Metrics collection
- **Notification Service** (port 8010): User alerts

### Environment Variables
See `.env.template` for complete configuration options.

## Security Considerations

- All AWS credentials should be securely managed
- User encryption keys are user-controlled
- Network access is strictly limited
- All actions are audit logged
- Rate limiting prevents abuse

## Support

For issues or questions:
1. Check service logs for error details
2. Verify AWS permissions and credentials
3. Ensure all dependent services are running
4. Monitor CloudWatch metrics for issues