# ActiveLog AWS Infrastructure Setup Guide
**Complete AWS Environment Setup for ActiveLog.ai Platform**

## 📋 **Prerequisites Checklist**

### 1. **AWS Account Setup**
- [ ] Create AWS account at https://aws.amazon.com/
- [ ] Enable billing alerts and set up cost monitoring
- [ ] Request service limit increases for production workloads
- [ ] Set up AWS Organizations for multi-account strategy (recommended)

### 2. **Required AWS Services**
- [ ] EC2 (Elastic Compute Cloud)
- [ ] VPC (Virtual Private Cloud)
- [ ] RDS (Relational Database Service)
- [ ] ElastiCache (Redis)
- [ ] ELB (Elastic Load Balancer)
- [ ] Route 53 (DNS)
- [ ] Certificate Manager (SSL/TLS)
- [ ] CloudFront (CDN)
- [ ] S3 (Object Storage)
- [ ] IAM (Identity and Access Management)
- [ ] CloudWatch (Monitoring)
- [ ] Systems Manager (Parameter Store)

### 3. **Development Tools**
- [ ] AWS CLI v2 installed and configured
- [ ] Terraform >= 1.5.0 installed
- [ ] Packer >= 1.9.0 installed (for AMI creation)
- [ ] Docker installed
- [ ] Git with SSH keys configured

## 🔧 **Initial AWS Configuration**

### Step 1: AWS CLI Setup
```bash
# Install AWS CLI v2 (if not installed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS CLI
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

### Step 2: Create IAM User for Terraform
```bash
# Create dedicated IAM user for infrastructure management
aws iam create-user --user-name terraform-user

# Create access key
aws iam create-access-key --user-name terraform-user

# Attach necessary policies (be restrictive in production)
aws iam attach-user-policy --user-name terraform-user --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

### Step 3: Set Up Terraform Backend
```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket --bucket activelog-terraform-state-$(date +%s)

# Enable versioning
aws s3api put-bucket-versioning --bucket activelog-terraform-state-xxxxx --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
    --table-name terraform-state-lock \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

## 🏗️ **Architecture Overview**

### Multi-Environment Strategy
```
Production Environment (activelog.ai)
├── us-east-1 (Primary)
│   ├── VPC: 10.0.0.0/16
│   ├── Public Subnets: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24
│   ├── Private Subnets: 10.0.11.0/24, 10.0.12.0/24, 10.0.13.0/24
│   └── Database Subnets: 10.0.21.0/24, 10.0.22.0/24, 10.0.23.0/24
└── us-west-2 (Disaster Recovery)
    └── VPC: 10.1.0.0/16

Staging Environment (staging.activelog.ai)
└── us-east-1
    └── VPC: 10.10.0.0/16

Development Environment (dev.activelog.ai)
└── us-east-1
    └── VPC: 10.20.0.0/16
```

### Service Distribution Strategy
```yaml
ActiveLog Core Services:
  - Load Balancer: Application Load Balancer (ALB)
  - Web Servers: EC2 Auto Scaling Group (t3.medium)
  - API Gateway: AWS API Gateway + Lambda
  - Databases: RDS PostgreSQL Multi-AZ
  - Cache: ElastiCache Redis Cluster
  - File Storage: S3 + CloudFront CDN

ActiveLedger Financial Services:
  - Dedicated VPC: 10.5.0.0/16 (isolated)
  - Compute: c5.xlarge instances (high performance)
  - Database: RDS PostgreSQL with encryption
  - Backup: Automated snapshots + cross-region replication
  - Security: AWS WAF + Shield Advanced
```

## 🌐 **Domain Registration Plan**

### Primary Domains
1. **activelog.ai** (Main platform domain)
   - Production: https://activelog.ai
   - API: https://api.activelog.ai
   - CDN: https://cdn.activelog.ai

2. **activeledger.ai** (Financial trading platform)
   - Production: https://activeledger.ai
   - Trading API: https://trading.activeledger.ai
   - Market Data: https://market.activeledger.ai

### Subdomain Structure
```
activelog.ai
├── www.activelog.ai (main website)
├── api.activelog.ai (main API)
├── admin.activelog.ai (admin dashboard)
├── docs.activelog.ai (documentation)
├── status.activelog.ai (status page)
├── staging.activelog.ai (staging environment)
└── dev.activelog.ai (development environment)

activeledger.ai
├── www.activeledger.ai (trading platform)
├── trading.activeledger.ai (trading API)
├── market.activeledger.ai (market data)
├── compliance.activeledger.ai (compliance dashboard)
└── admin.activeledger.ai (administrative interface)
```

## 💰 **Cost Estimation**

### Monthly AWS Costs (Production)
```yaml
Compute (EC2):
  - Web Servers: 6x t3.medium = $150/month
  - ActiveLedger: 4x c5.xlarge = $480/month
  - Load Balancers: 2x ALB = $32/month

Storage:
  - RDS PostgreSQL: db.r5.large Multi-AZ = $350/month
  - ElastiCache: 3-node Redis cluster = $180/month
  - S3 Storage: 500GB = $12/month

Networking:
  - Data Transfer: ~1TB/month = $90/month
  - CloudFront CDN: ~5TB/month = $425/month
  - Route 53 DNS: 2 hosted zones = $2/month

Security & Monitoring:
  - AWS WAF: $5/month + requests
  - CloudWatch: $50/month
  - Certificate Manager: Free

Total Estimated: ~$1,776/month
```

### Cost Optimization Strategies
- Use Reserved Instances for predictable workloads (30-60% savings)
- Implement auto-scaling to reduce idle capacity
- Use Spot Instances for non-critical workloads
- Enable S3 Intelligent Tiering
- Regular cost reviews and rightsizing

## 🔒 **Security Configuration**

### IAM Roles and Policies
```yaml
Core Roles:
  - ActiveLogEC2Role: EC2 instances access to required services
  - ActiveLogLambdaRole: Lambda function execution
  - ActiveLogRDSRole: Database enhanced monitoring
  - ActiveLogBackupRole: Automated backup operations

Security Groups:
  - activelog-web-sg: HTTP/HTTPS from internet
  - activelog-api-sg: API access from web tier
  - activelog-db-sg: Database access from API tier
  - activelog-cache-sg: Redis access from API tier
```

### Compliance and Auditing
- Enable AWS CloudTrail for all API calls
- Configure AWS Config for resource compliance
- Set up GuardDuty for threat detection
- Enable VPC Flow Logs for network monitoring
- Implement AWS Systems Manager for patch management

## 📊 **Monitoring and Alerting**

### CloudWatch Metrics
```yaml
Application Metrics:
  - API response times (< 200ms target)
  - Error rates (< 0.1% target)
  - Database connections
  - Cache hit rates

Infrastructure Metrics:
  - EC2 CPU utilization (< 80%)
  - Memory usage (< 85%)
  - Disk usage (< 90%)
  - Network throughput

Business Metrics:
  - User registrations
  - Trading volume (ActiveLedger)
  - Revenue metrics
  - Compliance violations
```

### Alerting Strategy
- Critical alerts: Page on-call engineer
- Warning alerts: Email/Slack notifications
- Info alerts: Dashboard updates only

## 🚀 **Deployment Strategy**

### Blue-Green Deployment
```yaml
Blue Environment:
  - Current production version
  - Receives all live traffic
  - Monitored continuously

Green Environment:
  - New version deployment
  - Testing and validation
  - Traffic switch after verification

Rollback Strategy:
  - Immediate traffic switch to blue
  - Database rollback if needed
  - Automated health checks
```

### CI/CD Pipeline
```yaml
Source Control: GitHub
  ↓
Build: GitHub Actions
  ↓
Test: Automated testing suite
  ↓
Package: Docker containers + Terraform
  ↓
Deploy: Terraform apply
  ↓
Verify: Health checks + smoke tests
  ↓
Monitor: CloudWatch + custom metrics
```

## ⚡ **Quick Start Commands**

### 1. Clone and Setup
```bash
git clone <your-repo>
cd activelog/aws-infrastructure
```

### 2. Initialize Terraform
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 3. Build AMI
```bash
cd packer
packer build activelog-base.pkr.hcl
```

### 4. Deploy Application
```bash
cd terraform/environments/production
terraform init
terraform apply
```

This setup provides a production-ready AWS infrastructure for the ActiveLog platform with proper security, scalability, and cost optimization.