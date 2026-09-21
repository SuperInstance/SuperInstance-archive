# ActiveLog AWS Infrastructure - Deployment Guide

A comprehensive guide to deploy the complete ActiveLog infrastructure on AWS with 70+ microservices.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Deployment](#detailed-deployment)
- [Post-Deployment](#post-deployment)
- [Cost Management](#cost-management)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## 🏗️ Overview

This infrastructure deployment creates a production-ready, scalable environment for ActiveLog with:

- **70+ microservices** running on ECS Fargate
- **PostgreSQL with pgvector** for AI embeddings
- **Redis cluster** for high-performance caching
- **Multi-AZ deployment** for high availability
- **CloudFront CDN** for global performance
- **Complete monitoring** and alerting
- **Cost optimization** with intelligent scaling

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
            ┌──────▼──────┐
            │ CloudFront  │ (CDN)
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │   Route53   │ (DNS)
            └──────┬──────┘
                   │
         ┌─────────▼─────────┐
         │   API Gateway     │
         └─────────┬─────────┘
                   │
         ┌─────────▼─────────┐
         │ Application Load  │
         │    Balancer       │
         └─────────┬─────────┘
                   │
    ┌──────────────▼──────────────┐
    │           ECS Cluster       │
    │  ┌─────┐ ┌─────┐ ┌─────┐   │
    │  │Svc 1│ │Svc 2│ │ ... │   │ (70+ Services)
    │  └─────┘ └─────┘ └─────┘   │
    └──────────────┬──────────────┘
                   │
       ┌───────────┼───────────┐
       │           │           │
   ┌───▼───┐   ┌───▼───┐   ┌───▼───┐
   │  RDS  │   │ Redis │   │  S3   │
   │(pgvect│   │Cluster│   │Buckets│
   └───────┘   └───────┘   └───────┘
```

## ✅ Prerequisites

### Required Tools

- **AWS CLI v2** - [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Terraform ≥ 1.0** - [Install Guide](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- **jq** - [Install Guide](https://stedolan.github.io/jq/download/)

### AWS Requirements

- **AWS Account** with administrative access
- **Domain name** (optional but recommended)
- **AWS CLI configured** with appropriate credentials

### Permissions Required

Your AWS user/role needs these managed policies:
- `PowerUserAccess`
- `IAMFullAccess`
- Or custom policy with all necessary permissions

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd ~/activelog/infrastructure/aws
chmod +x scripts/deploy.sh
```

### 2. Deploy Staging Environment

```bash
./scripts/deploy.sh \
  --environment staging \
  --domain staging.activelog.com \
  --region us-west-2
```

### 3. Deploy Production Environment

```bash
./scripts/deploy.sh \
  --environment production \
  --domain activelog.com \
  --region us-west-2 \
  --yes
```

## 📖 Detailed Deployment

### Environment Configuration

#### Staging Environment
- **Purpose**: Development and testing
- **Cost**: ~$1,611/month
- **High Availability**: Single AZ
- **Backup Retention**: 3 days

#### Production Environment
- **Purpose**: Live application
- **Cost**: ~$4,011/month
- **High Availability**: Multi-AZ
- **Backup Retention**: 7 days

### Step-by-Step Deployment

#### 1. Prepare Environment

```bash
# Set environment variables
export AWS_PROFILE=your-aws-profile
export AWS_REGION=us-west-2

# Verify AWS credentials
aws sts get-caller-identity
```

#### 2. Run Dry Run (Optional)

```bash
./scripts/deploy.sh \
  --environment staging \
  --domain staging.activelog.com \
  --dry-run
```

#### 3. Deploy Infrastructure

```bash
./scripts/deploy.sh \
  --environment staging \
  --domain staging.activelog.com
```

#### 4. Monitor Deployment

The deployment will:
1. ✅ Check prerequisites
2. ✅ Create Terraform backend (S3 + DynamoDB)
3. ✅ Initialize Terraform
4. ✅ Create environment-specific configuration
5. ✅ Validate Terraform files
6. ✅ Plan infrastructure changes
7. ✅ Apply changes (creates ~50+ AWS resources)
8. ✅ Display deployment information

### Manual Terraform Deployment

If you prefer manual control:

```bash
cd terraform

# Initialize Terraform
terraform init

# Create environment configuration
cp environments/staging.tfvars.example staging.tfvars
# Edit staging.tfvars with your values

# Plan deployment
terraform plan -var-file=staging.tfvars

# Apply changes
terraform apply -var-file=staging.tfvars
```

## 🔧 Post-Deployment

### 1. DNS Configuration

If using a custom domain:

```bash
# Get nameservers from Route53
aws route53 list-hosted-zones --query 'HostedZones[0].Id' --output text
aws route53 get-hosted-zone --id /hostedzone/YOUR_ZONE_ID

# Update your domain registrar with the nameservers
```

### 2. SSL Certificate Verification

The SSL certificate is automatically created but needs DNS validation:

```bash
# Check certificate status
aws acm list-certificates --region us-west-2
```

### 3. Container Image Deployment

Deploy your application containers:

```bash
# Get ECR repository URLs
terraform output ecr_repositories

# Example: Push image to ECR
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-west-2.amazonaws.com

docker build -t activelog-auth-service .
docker tag activelog-auth-service:latest 123456789.dkr.ecr.us-west-2.amazonaws.com/activelog-staging-auth-service:latest
docker push 123456789.dkr.ecr.us-west-2.amazonaws.com/activelog-staging-auth-service:latest
```

### 4. Database Initialization

Initialize the PostgreSQL database with pgvector:

```bash
# Get database endpoint
DB_ENDPOINT=$(terraform output -raw rds_instance_endpoint)

# Connect and run initialization script
psql -h $DB_ENDPOINT -U activelogadmin -d activelog < modules/rds/init-pgvector.sql
```

### 5. Configure Application Secrets

```bash
# Update database password
aws secretsmanager put-secret-value \
  --secret-id activelog-rds-password-staging \
  --secret-string "your-secure-password"

# Update Redis auth token
aws secretsmanager put-secret-value \
  --secret-id activelog-redis-auth-token \
  --secret-string "your-redis-token"
```

## 💰 Cost Management

### Cost Breakdown

#### Staging Environment (~$1,611/month)
- **ECS Fargate**: $1,200 (70 services, minimal resources)
- **RDS PostgreSQL**: $85 (db.t3.medium)
- **ElastiCache Redis**: $25 (cache.t3.micro)
- **S3 Storage**: $25 (100GB)
- **CloudFront CDN**: $50
- **Load Balancer**: $25
- **NAT Gateways**: $135 (3 AZs)
- **Other services**: $66

#### Production Environment (~$4,011/month)
- **ECS Fargate**: $2,400 (140 services, larger resources)
- **RDS PostgreSQL**: $700 (db.r5.xlarge + replica)
- **ElastiCache Redis**: $180 (cache.r6g.large)
- **S3 Storage**: $120 (1TB)
- **CloudFront CDN**: $200
- **Load Balancer**: $25
- **NAT Gateways**: $135 (3 AZs)
- **Other services**: $251

### Cost Optimization

1. **Use Spot Instances**: 70% cost savings on ECS Fargate
2. **Right-size Resources**: Monitor and adjust instance sizes
3. **Storage Lifecycle**: Automatic transition to cheaper storage classes
4. **Reserved Instances**: 1-3 year commitments for predictable workloads
5. **Cost Alerts**: Automatic notifications when budgets are exceeded

### Budget Alerts

The infrastructure automatically creates:
- **50% budget alert**: Early warning
- **80% budget alert**: Action required
- **100% budget alert**: Budget exceeded
- **120% budget alert**: Emergency alert

## 📊 Monitoring

### CloudWatch Dashboards

Access your monitoring dashboards:

```bash
# Get dashboard URLs
terraform output cloudwatch_dashboard_url
```

### Key Metrics Monitored

#### ECS Services
- CPU and memory utilization
- Task count and health
- Service discovery status
- Load balancer health checks

#### RDS Database
- CPU, memory, and storage utilization
- Connection count
- Query performance
- Backup status

#### ElastiCache Redis
- CPU and memory utilization
- Cache hit ratio
- Connection count
- Eviction rate

#### Application Load Balancer
- Request count and latency
- HTTP response codes
- Target health
- SSL certificate status

### Alerting

Alerts are sent to the configured email when:
- Service CPU/memory exceeds thresholds
- Database connections are high
- Cache hit ratio is low
- SSL certificate expires soon
- Cost budgets are exceeded

## 🔍 Troubleshooting

### Common Issues

#### 1. Terraform State Lock
```bash
# If deployment fails due to state lock
terraform force-unlock LOCK_ID -force

# Or delete the lock manually from DynamoDB
aws dynamodb delete-item \
  --table-name activelog-terraform-locks-staging \
  --key '{"LockID":{"S":"YOUR_LOCK_ID"}}'
```

#### 2. Domain Validation Timeout
```bash
# Check certificate validation status
aws acm describe-certificate --certificate-arn YOUR_CERT_ARN

# Manually create DNS validation records if needed
```

#### 3. ECS Service Not Starting
```bash
# Check service events
aws ecs describe-services --cluster activelog-staging-cluster --services activelog-staging-auth-service

# Check task logs
aws logs get-log-events --log-group-name /ecs/activelog-staging/auth-service
```

#### 4. Database Connection Issues
```bash
# Test database connectivity
nc -zv YOUR_DB_ENDPOINT 5432

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-your-database-sg
```

### Debug Commands

```bash
# Get all Terraform outputs
terraform output

# Validate Terraform configuration
terraform validate

# Check AWS resource status
aws ecs list-clusters
aws rds describe-db-instances
aws elasticache describe-replication-groups
```

## 🔧 Maintenance

### Regular Tasks

#### Weekly
- Review CloudWatch dashboards
- Check cost and usage reports
- Monitor security alerts
- Verify backup completion

#### Monthly
- Update Terraform modules
- Review and optimize resource usage
- Test disaster recovery procedures
- Update security patches

#### Quarterly
- Review and update budget alerts
- Audit IAM permissions
- Performance optimization review
- Capacity planning assessment

### Updates and Upgrades

#### Infrastructure Updates
```bash
# Update Terraform modules
git pull origin main

# Plan and apply updates
terraform plan -var-file=production.tfvars
terraform apply -var-file=production.tfvars
```

#### Application Updates
```bash
# Update ECS services with new container images
aws ecs update-service --cluster activelog-production-cluster \
  --service activelog-production-auth-service \
  --force-new-deployment
```

### Backup and Recovery

#### Database Backups
- **Automated backups**: 7 days retention (production), 3 days (staging)
- **Manual snapshots**: Created before major updates
- **Cross-region backup**: Available for production

#### Application Data Backups
- **S3 versioning**: Enabled on all buckets
- **Cross-region replication**: Critical data only
- **Lifecycle policies**: Automatic archiving to Glacier

### Security Updates

#### Regular Security Tasks
- Monitor AWS Security Hub findings
- Review CloudTrail logs
- Update IAM policies
- Rotate secrets and keys
- Scan container images for vulnerabilities

## 🆘 Support

### Getting Help

1. **Check logs**: CloudWatch Logs for application issues
2. **Review metrics**: CloudWatch Dashboards for performance issues
3. **Check status**: AWS Status Page for service outages
4. **Community**: GitHub issues for infrastructure problems

### Emergency Contacts

- **Infrastructure Team**: infrastructure@activelog.com
- **On-call Engineer**: +1-555-ACTIVELOG
- **AWS Support**: (if you have a support plan)

### Disaster Recovery

#### RTO (Recovery Time Objective): 4 hours
#### RPO (Recovery Point Objective): 15 minutes

1. **Database**: Point-in-time recovery available
2. **Application**: Blue-green deployment capability
3. **Files**: Cross-region replication for critical data
4. **Infrastructure**: Infrastructure as Code for rapid rebuild

---

## 📚 Additional Resources

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/intro.html)
- [RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)

---

**Last Updated**: $(date)  
**Infrastructure Version**: v1.0.0  
**Terraform Version**: ≥ 1.0.0