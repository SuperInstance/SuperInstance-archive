# Deployment Architecture: Infrastructure & Cloud Strategy

## Executive Summary

This document provides comprehensive deployment architecture for the compute marketplace platform, including Kubernetes deployment strategies, cloud provider recommendations, CI/CD pipelines, auto-scaling strategies, and cost estimates.

**Recommended Cloud**: AWS (primary), with multi-cloud strategy for high availability
**Orchestration**: Kubernetes (EKS)
**CI/CD**: GitHub Actions + ArgoCD
**Monitoring**: Prometheus + Grafana + ELK Stack

---

## Table of Contents

1. [Cloud Provider Comparison](#cloud-provider-comparison)
2. [Kubernetes Architecture](#kubernetes-architecture)
3. [Infrastructure as Code](#infrastructure-as-code)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Auto-Scaling Strategy](#auto-scaling-strategy)
6. [Monitoring & Observability](#monitoring--observability)
7. [Security & Compliance](#security--compliance)
8. [Cost Optimization](#cost-optimization)
9. [Disaster Recovery](#disaster-recovery)

---

## Cloud Provider Comparison

### AWS vs Azure vs GCP (2025)

| Feature | AWS | Azure | GCP | Winner |
|---------|-----|-------|-----|--------|
| **Market Share** | ~32% | ~23% | ~10% | AWS |
| **Kubernetes Service** | EKS | AKS | GKE | GKE (easiest) |
| **Pricing** | Moderate | Moderate-High | Moderate-Low | GCP |
| **Global Reach** | 33 regions | 60+ regions | 40+ regions | Azure |
| **Compute Options** | EC2, Lambda, Fargate | VMs, Functions, Container Instances | Compute Engine, Cloud Run | AWS (most options) |
| **Database Options** | RDS, Aurora, DynamoDB | Azure SQL, Cosmos DB | Cloud SQL, Spanner | AWS (most mature) |
| **Networking** | VPC, CloudFront, Route 53 | VNet, Azure CDN | VPC, Cloud CDN | AWS (most flexible) |
| **Monitoring** | CloudWatch | Azure Monitor | Cloud Monitoring | Tie |
| **Marketplace Presence** | Largest | Large | Growing | AWS |
| **Enterprise Support** | Excellent | Excellent (Microsoft focus) | Good | Azure (enterprise) |
| **Startup Credits** | $100K+ available | $150K+ available | $200K+ available | GCP |
| **Learning Curve** | Moderate | Moderate | Easy | GCP |

### Recommendation: AWS (Primary)

**Rationale:**
1. **Market leadership**: Largest ecosystem, most third-party integrations
2. **Mature services**: Battle-tested infrastructure, extensive feature set
3. **EKS**: Robust Kubernetes service with good integration
4. **Pricing**: Competitive with reserved instances and savings plans
5. **Global presence**: 33 regions covering all major markets
6. **Documentation**: Extensive resources and community support

**Multi-Cloud Strategy:**
- **Primary**: AWS (production workloads)
- **Secondary**: GCP (AI/ML workloads, cost-sensitive dev/test)
- **Tertiary**: Azure (enterprise customers, hybrid scenarios)

---

## Kubernetes Architecture

### Why Kubernetes?

```
✓ Container orchestration (automated deployment, scaling, management)
✓ Self-healing (automatic restarts, replacements)
✓ Service discovery and load balancing
✓ Automated rollouts and rollbacks
✓ Secret and configuration management
✓ Horizontal scaling
✓ Cloud-agnostic (portable across AWS, GCP, Azure)
✓ Industry standard (huge ecosystem)
```

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    VPC (10.0.0.0/16)                       │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │            Availability Zone 1 (us-east-1a)          │ │ │
│  │  │                                                      │ │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │ │ │
│  │  │  │  Public    │  │  Private   │  │   Private    │  │ │ │
│  │  │  │  Subnet    │  │  Subnet    │  │   Subnet     │  │ │ │
│  │  │  │            │  │            │  │              │  │ │ │
│  │  │  │  ALB       │  │  EKS       │  │  RDS         │  │ │ │
│  │  │  │  (LB)      │  │  Worker    │  │  Primary     │  │ │ │
│  │  │  │            │  │  Nodes     │  │              │  │ │ │
│  │  │  └────────────┘  └────────────┘  └──────────────┘  │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │            Availability Zone 2 (us-east-1b)          │ │ │
│  │  │                                                      │ │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │ │ │
│  │  │  │  Public    │  │  Private   │  │   Private    │  │ │ │
│  │  │  │  Subnet    │  │  Subnet    │  │   Subnet     │  │ │ │
│  │  │  │            │  │            │  │              │  │ │ │
│  │  │  │  ALB       │  │  EKS       │  │  RDS         │  │ │ │
│  │  │  │  (LB)      │  │  Worker    │  │  Replica     │  │ │ │
│  │  │  │            │  │  Nodes     │  │              │  │ │ │
│  │  │  └────────────┘  └────────────┘  └──────────────┘  │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │            Availability Zone 3 (us-east-1c)          │ │ │
│  │  │                                                      │ │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │ │ │
│  │  │  │  Public    │  │  Private   │  │   Private    │  │ │ │
│  │  │  │  Subnet    │  │  Subnet    │  │   Subnet     │  │ │ │
│  │  │  │            │  │            │  │              │  │ │ │
│  │  │  │  NAT GW    │  │  EKS       │  │  ElastiCache │  │ │ │
│  │  │  │            │  │  Worker    │  │  (Redis)     │  │ │ │
│  │  │  │            │  │  Nodes     │  │              │  │ │ │
│  │  │  └────────────┘  └────────────┘  └──────────────┘  │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  External Services:                                              │
│  - Route 53 (DNS)                                               │
│  - CloudFront (CDN)                                             │
│  - S3 (Object Storage)                                          │
│  - ECR (Container Registry)                                     │
│  - CloudWatch (Monitoring)                                      │
└──────────────────────────────────────────────────────────────────┘
```

### EKS Cluster Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                       EKS Control Plane                       │
│                    (Managed by AWS)                           │
│  - API Server                                                 │
│  - etcd (Cluster State)                                       │
│  - Controller Manager                                         │
│  - Scheduler                                                  │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            │ kubectl, API calls
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                       EKS Worker Nodes                        │
│                   (EC2 Instances / Fargate)                   │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Node 1    │  │   Node 2    │  │   Node 3    │          │
│  │             │  │             │  │             │          │
│  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │          │
│  │  │ Pod   │  │  │  │ Pod   │  │  │  │ Pod   │  │          │
│  │  │ API   │  │  │  │ API   │  │  │  │Worker │  │          │
│  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │          │
│  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │          │
│  │  │ Pod   │  │  │  │ Pod   │  │  │  │ Pod   │  │          │
│  │  │ Web   │  │  │  │ DB    │  │  │  │Queue  │  │          │
│  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                               │
│  - kubelet (Node Agent)                                       │
│  - kube-proxy (Network Proxy)                                 │
│  - Container Runtime (containerd)                             │
└───────────────────────────────────────────────────────────────┘
```

### Kubernetes Resources

#### 1. Namespace Organization

```yaml
# namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging
---
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    environment: development
```

#### 2. API Deployment

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: production
  labels:
    app: api
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
        version: v1
    spec:
      containers:
      - name: api
        image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/marketplace-api:v1.0.0
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: NODE_ENV
          value: "production"
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: host
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: production
spec:
  selector:
    app: api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: ClusterIP
```

#### 3. Ingress (ALB Controller)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: marketplace-ingress
  namespace: production
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abc123
    alb.ingress.kubernetes.io/ssl-redirect: '443'
spec:
  rules:
  - host: api.marketplace.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api
            port:
              number: 80
```

#### 4. ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: production
data:
  LOG_LEVEL: "info"
  API_VERSION: "v1"
  RATE_LIMIT_MAX: "1000"
  RATE_LIMIT_WINDOW: "3600"
```

#### 5. Secret

```yaml
# secret.yaml (encrypted in production)
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: production
type: Opaque
stringData:
  host: marketplace-db.cluster-abc123.us-east-1.rds.amazonaws.com
  username: app_user
  password: <encrypted-password>
  database: marketplace
```

#### 6. HorizontalPodAutoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 25
        periodSeconds: 60
```

---

## Infrastructure as Code

### Terraform Configuration

**Directory Structure:**
```
terraform/
├── modules/
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── eks/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── rds/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── elasticache/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── production/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── development/
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
└── backend.tf
```

#### VPC Module

```hcl
# modules/vpc/main.tf
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name                                            = "${var.project_name}-public-${count.index + 1}"
    Environment                                     = var.environment
    "kubernetes.io/role/elb"                        = "1"
    "kubernetes.io/cluster/${var.cluster_name}"     = "shared"
  }
}

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name                                            = "${var.project_name}-private-${count.index + 1}"
    Environment                                     = var.environment
    "kubernetes.io/role/internal-elb"               = "1"
    "kubernetes.io/cluster/${var.cluster_name}"     = "shared"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-igw"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "main" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name        = "${var.project_name}-nat-${count.index + 1}"
    Environment = var.environment
  }
}

resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"

  tags = {
    Name        = "${var.project_name}-eip-${count.index + 1}"
    Environment = var.environment
  }
}
```

#### EKS Module

```hcl
# modules/eks/main.tf
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.allowed_cidr_blocks
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.cluster_AmazonEKSVPCResourceController,
  ]

  tags = {
    Name        = var.cluster_name
    Environment = var.environment
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-node-group"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids

  scaling_config {
    desired_size = var.desired_size
    max_size     = var.max_size
    min_size     = var.min_size
  }

  instance_types = var.instance_types

  remote_access {
    ec2_ssh_key               = var.ssh_key_name
    source_security_group_ids = var.ssh_source_security_group_ids
  }

  labels = {
    Environment = var.environment
    NodeGroup   = "main"
  }

  tags = {
    Name        = "${var.cluster_name}-node-group"
    Environment = var.environment
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly,
  ]
}
```

#### RDS Module

```hcl
# modules/rds/main.tf
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "${var.project_name}-db-subnet-group"
    Environment = var.environment
  }
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  db_name  = var.database_name
  username = var.master_username
  password = var.master_password
  port     = 5432

  multi_az               = var.multi_az
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled    = true
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn

  deletion_protection = var.environment == "production" ? true : false
  skip_final_snapshot = var.environment != "production"

  tags = {
    Name        = "${var.project_name}-db"
    Environment = var.environment
  }
}

resource "aws_db_instance" "replica" {
  count              = var.create_replica ? 1 : 0
  identifier         = "${var.project_name}-db-replica"
  replicate_source_db = aws_db_instance.main.identifier

  instance_class = var.instance_class

  multi_az               = false
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 0
  skip_final_snapshot     = true

  tags = {
    Name        = "${var.project_name}-db-replica"
    Environment = var.environment
    Role        = "read-replica"
  }
}
```

#### Production Environment

```hcl
# environments/production/main.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "marketplace-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Marketplace"
      Environment = "production"
      ManagedBy   = "Terraform"
    }
  }
}

module "vpc" {
  source = "../../modules/vpc"

  project_name       = var.project_name
  environment        = "production"
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
  cluster_name       = "${var.project_name}-production"
}

module "eks" {
  source = "../../modules/eks"

  cluster_name         = "${var.project_name}-production"
  environment          = "production"
  kubernetes_version   = "1.28"
  subnet_ids           = module.vpc.all_subnet_ids
  private_subnet_ids   = module.vpc.private_subnet_ids
  allowed_cidr_blocks  = ["0.0.0.0/0"]

  instance_types = ["t3.xlarge", "t3.2xlarge"]
  desired_size   = 3
  min_size       = 3
  max_size       = 20

  ssh_key_name = var.ssh_key_name
}

module "rds" {
  source = "../../modules/rds"

  project_name      = var.project_name
  environment       = "production"
  subnet_ids        = module.vpc.database_subnet_ids
  vpc_id            = module.vpc.vpc_id

  instance_class        = "db.r6g.xlarge"
  allocated_storage     = 100
  max_allocated_storage = 1000
  multi_az              = true
  create_replica        = true

  database_name   = "marketplace"
  master_username = var.db_username
  master_password = var.db_password
}

module "elasticache" {
  source = "../../modules/elasticache"

  project_name = var.project_name
  environment  = "production"
  subnet_ids   = module.vpc.cache_subnet_ids
  vpc_id       = module.vpc.vpc_id

  node_type           = "cache.r6g.large"
  num_cache_nodes     = 3
  parameter_group_name = "default.redis7"
  engine_version      = "7.0"
}
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: CI/CD Pipeline

on:
  push:
    branches:
      - main
      - staging
      - develop
  pull_request:
    branches:
      - main

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: marketplace-api
  EKS_CLUSTER_NAME: marketplace-production

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linter
        run: npm run lint

      - name: Run unit tests
        run: npm run test:unit

      - name: Run integration tests
        run: npm run test:integration

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info

  build:
    name: Build and Push Docker Image
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    outputs:
      image-tag: ${{ steps.image-tag.outputs.tag }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Generate image tag
        id: image-tag
        run: |
          TAG=$(echo $GITHUB_SHA | cut -c1-7)
          echo "tag=$TAG" >> $GITHUB_OUTPUT
          echo "IMAGE_TAG=$TAG" >> $GITHUB_ENV

      - name: Build Docker image
        run: |
          docker build \
            --build-arg NODE_ENV=production \
            --tag ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }} \
            --tag ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:latest \
            .

      - name: Scan image for vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }}
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Push Docker image
        run: |
          docker push ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }}
          docker push ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:latest

  deploy-staging:
    name: Deploy to Staging
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    environment:
      name: staging
      url: https://api-staging.marketplace.example.com
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig \
            --region ${{ env.AWS_REGION }} \
            --name marketplace-staging

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/api \
            api=${{ needs.build.outputs.image-tag }} \
            -n staging

          kubectl rollout status deployment/api -n staging

      - name: Run smoke tests
        run: |
          npm run test:smoke -- --env=staging

  deploy-production:
    name: Deploy to Production
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://api.marketplace.example.com
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig \
            --region ${{ env.AWS_REGION }} \
            --name ${{ env.EKS_CLUSTER_NAME }}

      - name: Blue-Green Deployment
        run: |
          # Deploy new version (green)
          kubectl apply -f k8s/production/api-deployment-green.yaml

          # Wait for rollout
          kubectl rollout status deployment/api-green -n production

          # Run health checks
          ./scripts/health-check.sh api-green

          # Switch traffic (update service selector)
          kubectl patch service api -n production \
            -p '{"spec":{"selector":{"version":"green"}}}'

          # Monitor for 5 minutes
          sleep 300

          # Scale down old version (blue)
          kubectl scale deployment/api-blue --replicas=0 -n production

      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Production deployment ${{ job.status }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "Deployment to production: *${{ job.status }}*\nCommit: ${{ github.sha }}\nAuthor: ${{ github.actor }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### ArgoCD Setup (GitOps)

```yaml
# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: marketplace-api
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/marketplace/k8s-manifests
    targetRevision: main
    path: production
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

---

## Auto-Scaling Strategy

### Three-Layer Scaling

```
Layer 1: Pod-level (HPA)
  - Scale pods based on CPU/memory/custom metrics
  - Fast response (seconds to minutes)

Layer 2: Node-level (Cluster Autoscaler)
  - Add/remove EC2 nodes based on pod demands
  - Medium response (2-5 minutes)

Layer 3: Application-level (custom logic)
  - Predictive scaling based on historical patterns
  - Slow response (minutes to hours)
```

### Horizontal Pod Autoscaler (HPA)

Already covered in Kubernetes section. Key points:
- Scale based on CPU (70% threshold) and memory (80% threshold)
- Min 3 replicas, max 20 replicas
- Scale up aggressively (50% increase per minute)
- Scale down conservatively (25% decrease per minute, 5-minute stabilization)

### Cluster Autoscaler

```yaml
# cluster-autoscaler.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - name: cluster-autoscaler
        image: registry.k8s.io/autoscaling/cluster-autoscaler:v1.28.0
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/marketplace-production
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
        env:
        - name: AWS_REGION
          value: us-east-1
        resources:
          limits:
            cpu: 100m
            memory: 600Mi
          requests:
            cpu: 100m
            memory: 600Mi
```

### Predictive Scaling (Custom)

```python
# predictive-scaler.py
import boto3
import pandas as pd
from datetime import datetime, timedelta

def predict_load(historical_data):
    """Predict load for next hour based on historical patterns."""

    df = pd.DataFrame(historical_data)

    # Extract time features
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek

    # Calculate average load by hour and day
    avg_load = df.groupby(['day_of_week', 'hour'])['load'].mean()

    # Predict for current time
    now = datetime.now()
    predicted_load = avg_load.loc[(now.weekday(), now.hour)]

    return predicted_load

def scale_resources(predicted_load):
    """Scale Kubernetes deployment based on predicted load."""

    # Calculate desired replicas
    base_replicas = 3
    load_factor = predicted_load / 100  # Normalize to 0-1
    desired_replicas = max(base_replicas, int(base_replicas * (1 + load_factor)))

    # Update deployment
    k8s_client = kubernetes.client.AppsV1Api()
    k8s_client.patch_namespaced_deployment_scale(
        name='api',
        namespace='production',
        body={'spec': {'replicas': desired_replicas}}
    )

    print(f"Scaled to {desired_replicas} replicas based on predicted load: {predicted_load}")

# Run every 15 minutes
while True:
    historical_data = fetch_historical_metrics()
    predicted_load = predict_load(historical_data)
    scale_resources(predicted_load)
    time.sleep(900)  # 15 minutes
```

---

## Monitoring & Observability

### Monitoring Stack

```
┌─────────────────────────────────────────────┐
│          Application (Pods)                 │
│  - API metrics exposed on /metrics          │
└──────────────────┬──────────────────────────┘
                   │
                   │ Scrape metrics
                   │
┌──────────────────▼──────────────────────────┐
│          Prometheus                         │
│  - Metric collection and storage            │
│  - Alert evaluation                         │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
┌──────────┐  ┌────────┐  ┌───────────┐
│ Grafana  │  │AlertMgr│  │Prometheus │
│(Visualize)  │(Notify)│  │ Adapter   │
└──────────┘  └────────┘  └───────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │      HPA      │
                        │ (Custom Metrics)
                        └───────────────┘
```

### Prometheus Setup

```yaml
# prometheus-deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    scrape_configs:
    - job_name: 'kubernetes-apiservers'
      kubernetes_sd_configs:
      - role: endpoints
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token

    - job_name: 'kubernetes-nodes'
      kubernetes_sd_configs:
      - role: node
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token

    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

    - job_name: 'api'
      static_configs:
      - targets: ['api.production.svc.cluster.local:3000']
      metrics_path: '/metrics'
```

### Grafana Dashboards

**Key Dashboards:**
1. **Cluster Overview**
   - Node CPU/Memory usage
   - Pod count
   - Network I/O
   - Disk usage

2. **Application Metrics**
   - Request rate (requests/sec)
   - Error rate (%)
   - Response time (p50, p95, p99)
   - Apdex score

3. **Database Metrics**
   - Connection pool utilization
   - Query execution time
   - Slow queries
   - Replication lag

4. **Business Metrics**
   - Active users
   - Bookings per minute
   - Revenue per hour
   - Conversion rate

### Alerting Rules

```yaml
# prometheus-alerts.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-alerts
  namespace: monitoring
data:
  alerts.yml: |
    groups:
    - name: application
      interval: 30s
      rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} req/sec"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High response time"
          description: "P95 latency is {{ $value }} seconds"

      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pod {{ $labels.pod }} is crash looping"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.pod }}"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      - alert: DatabaseConnectionPoolExhausted
        expr: pg_stat_database_numbackends / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly exhausted"
```

### Logging (ELK Stack)

```yaml
# fluentd-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    metadata:
      labels:
        name: fluentd
    spec:
      serviceAccountName: fluentd
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
        env:
        - name: FLUENT_ELASTICSEARCH_HOST
          value: "elasticsearch.logging.svc.cluster.local"
        - name: FLUENT_ELASTICSEARCH_PORT
          value: "9200"
        - name: FLUENT_ELASTICSEARCH_SCHEME
          value: "http"
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

---

## Security & Compliance

### Security Best Practices

```
✓ Encrypt data at rest (EBS, RDS, S3)
✓ Encrypt data in transit (TLS 1.3)
✓ Use IAM roles (not access keys)
✓ Enable VPC Flow Logs
✓ Use AWS WAF for API protection
✓ Implement network policies in Kubernetes
✓ Scan container images for vulnerabilities
✓ Use secrets management (AWS Secrets Manager, Vault)
✓ Enable audit logging (CloudTrail, EKS audit logs)
✓ Implement least privilege access
✓ Regular security patches and updates
✓ DDoS protection (AWS Shield, CloudFront)
```

### Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

---

## Cost Optimization

### Cost Breakdown (Production - 10K users)

```
Monthly Infrastructure Costs:

1. Compute (EKS + EC2)
   - 3x t3.xlarge nodes (on-demand): $300
   - EKS control plane: $72
   - Subtotal: $372

2. Database (RDS PostgreSQL)
   - db.r6g.xlarge (primary): $380
   - db.r6g.xlarge (replica): $380
   - Storage (500 GB): $115
   - Subtotal: $875

3. Cache (ElastiCache Redis)
   - cache.r6g.large (3 nodes): $420
   - Subtotal: $420

4. Load Balancing
   - Application Load Balancer: $25
   - Data processed (5 TB): $40
   - Subtotal: $65

5. Storage (S3)
   - Standard storage (1 TB): $23
   - Data transfer (1 TB): $90
   - Subtotal: $113

6. Networking
   - NAT Gateway (3): $97
   - Data transfer: $150
   - Subtotal: $247

7. Monitoring & Logging
   - CloudWatch logs (50 GB): $25
   - CloudWatch metrics: $10
   - Subtotal: $35

8. CDN (CloudFront)
   - Data transfer (10 TB): $850
   - Requests (100M): $7.50
   - Subtotal: $858

9. Container Registry (ECR)
   - Storage (100 GB): $10
   - Subtotal: $10

Total: ~$3,000/month

Optimizations:
- Use Reserved Instances (save 30-40%): -$500
- Spot Instances for non-critical (save 50-70%): -$200
- S3 Intelligent-Tiering: -$10
- Optimized Data Transfer: -$100

Optimized Total: ~$2,200/month
```

### Savings Strategies

1. **Reserved Instances** (1-3 year commitment)
   - EC2: Save 30-40%
   - RDS: Save 35-45%

2. **Savings Plans** (flexible commitment)
   - Compute Savings Plans: Save 17-25%

3. **Spot Instances** (interruptible workloads)
   - Development/staging environments
   - Batch processing jobs
   - CI/CD runners
   - Save 50-70%

4. **Right-Sizing**
   - Use AWS Compute Optimizer recommendations
   - Monitor resource utilization
   - Downsize over-provisioned resources

5. **Auto-Scaling**
   - Scale down during off-peak hours
   - Implement predictive scaling

6. **Storage Optimization**
   - S3 Intelligent-Tiering
   - Lifecycle policies (move to Glacier)
   - Clean up old snapshots

7. **Data Transfer Optimization**
   - Use CloudFront CDN
   - Enable compression
   - Optimize API payloads

---

## Disaster Recovery

### RTO/RPO Targets

```
Recovery Time Objective (RTO): 1 hour
  - Time to restore service after disaster

Recovery Point Objective (RPO): 15 minutes
  - Maximum acceptable data loss
```

### Backup Strategy

**Database Backups:**
```
- Automated daily snapshots (RDS)
- 7-day retention
- Cross-region replication (disaster recovery)
- Point-in-time recovery enabled
- Test restores monthly
```

**Application State:**
```
- Stateless architecture (pods can be recreated)
- Persistent data in RDS and S3 only
- Infrastructure as Code (Terraform) in git
- Kubernetes manifests in git (ArgoCD)
```

### Multi-Region Setup (Optional)

```
Primary Region: us-east-1
Secondary Region: us-west-2

Architecture:
- Active-Passive failover
- Database replication (RDS cross-region read replica)
- S3 cross-region replication
- Route 53 health checks with failover routing
- Manual failover process (DNS switch)
```

---

## Conclusion

This deployment architecture provides:

1. **Cloud-native infrastructure** with AWS EKS for container orchestration
2. **Infrastructure as Code** with Terraform for reproducible deployments
3. **Automated CI/CD** with GitHub Actions and ArgoCD for GitOps
4. **Auto-scaling** at pod, node, and application levels
5. **Comprehensive monitoring** with Prometheus, Grafana, and ELK
6. **Security** with encryption, network policies, and least privilege
7. **Cost optimization** strategies saving 20-30% on infrastructure
8. **Disaster recovery** with backups and multi-region capability

**Estimated Costs:**
- Small (1K users): $500-1,000/month
- Medium (10K users): $2,000-3,000/month
- Large (100K users): $10,000-20,000/month
- Extra Large (1M users): $50,000-100,000/month

**Next Steps:**
1. Set up AWS account and enable billing alerts
2. Deploy infrastructure with Terraform
3. Configure CI/CD pipelines
4. Implement monitoring and alerting
5. Run load tests and optimize
6. Document runbooks for operations team

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Author**: DevOps & Infrastructure Team
