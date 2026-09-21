# Master Deployment Operations Guide
**ActiveLog Technologies Platform**

---

*This comprehensive guide consolidates all deployment documentation into a single definitive reference, eliminating the need to consult multiple deployment guides. It provides complete coverage from development environments to enterprise-scale production deployments.*

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Prerequisites and Environment Setup](#prerequisites-and-environment-setup)
3. [AWS Cloud Infrastructure Deployment](#aws-cloud-infrastructure-deployment)
4. [Complete System Rebuild Guide](#complete-system-rebuild-guide)
5. [Container-Based Deployments](#container-based-deployments)
6. [Smart Contract Deployment](#smart-contract-deployment)
7. [DMLog Gaming Platform Deployment](#dmlog-gaming-platform-deployment)
8. [Development Environment Setup](#development-environment-setup)
9. [Production Operations](#production-operations)
10. [Monitoring and Maintenance](#monitoring-and-maintenance)
11. [Cost Management](#cost-management)
12. [Security and Compliance](#security-and-compliance)
13. [Troubleshooting Guide](#troubleshooting-guide)

---

## Deployment Overview

The ActiveLog platform supports multiple deployment strategies tailored to different use cases, from small team development to enterprise-scale production environments.

### Deployment Options

#### 1. Development Environments
- **Local Docker Compose**: Single-machine development
- **Development VM**: Isolated development instances
- **Staging Environment**: Pre-production testing

#### 2. Production Environments
- **Single Server**: Small teams (1-50 users)
- **Multi-Server**: Medium scale (50-1000 users)
- **Cloud Infrastructure**: Enterprise scale (1000+ users)
- **Kubernetes**: Container orchestration for high availability

#### 3. Specialized Deployments
- **DMLog Gaming Platform**: Two-tier gaming architecture
- **Smart Contracts**: Blockchain equity management
- **AI Services**: Specialized AI/ML workloads

### Architecture Components

The platform consists of:
- **182 microservices** across 5 specialized domains
- **Core infrastructure**: PostgreSQL, Redis, Elasticsearch
- **AI/ML services**: TensorFlow, PyTorch, Hugging Face
- **Web services**: React, FastAPI, Node.js
- **Gaming services**: WebGL, real-time collaboration
- **Blockchain services**: Ethereum smart contracts

---

## Prerequisites and Environment Setup

### Hardware Requirements

#### Development Environment
- **CPU**: 8 cores, 2.4GHz+
- **RAM**: 32GB
- **Storage**: 500GB SSD
- **Network**: Broadband internet connection

#### Production Environment
- **CPU**: 64 cores across multiple nodes
- **RAM**: 256GB+ distributed
- **Storage**: 2TB+ NVMe SSD with backup
- **Network**: High-speed, low-latency connection
- **GPU**: Optional for AI workloads (V100/A100)

### Software Prerequisites

#### Required Tools
- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Kubernetes**: 1.28+ (for production)
- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 16+
- **Redis**: 7+
- **Nginx**: 1.24+

#### Cloud Tools
- **AWS CLI v2** - [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Terraform ≥ 1.0** - [Install Guide](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- **kubectl** - Kubernetes command-line tool
- **helm** - Kubernetes package manager

### Initial System Setup

#### Ubuntu/Debian Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git unzip build-essential

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

#### AWS CLI Configuration
```bash
# Install AWS CLI v2
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

---

## AWS Cloud Infrastructure Deployment

### Architecture Overview

The AWS deployment creates a production-ready, scalable environment with:
- **70+ microservices** running on ECS Fargate
- **PostgreSQL with pgvector** for AI embeddings
- **Redis cluster** for high-performance caching
- **Multi-AZ deployment** for high availability
- **CloudFront CDN** for global performance

### Infrastructure Components

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

### Multi-Environment Strategy

```yaml
Production Environment (activelog.ai):
  Region: us-east-1 (Primary)
  VPC: 10.0.0.0/16
  Public Subnets: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24
  Private Subnets: 10.0.11.0/24, 10.0.12.0/24, 10.0.13.0/24
  Database Subnets: 10.0.21.0/24, 10.0.22.0/24, 10.0.23.0/24
  DR Region: us-west-2 (VPC: 10.1.0.0/16)

Staging Environment (staging.activelog.ai):
  Region: us-east-1
  VPC: 10.10.0.0/16

Development Environment (dev.activelog.ai):
  Region: us-east-1
  VPC: 10.20.0.0/16
```

### Quick Deployment

#### 1. Automated Deployment Script
```bash
cd ~/activelog/infrastructure/aws

# Deploy Staging Environment
./scripts/deploy.sh \
  --environment staging \
  --domain staging.activelog.com \
  --region us-west-2

# Deploy Production Environment
./scripts/deploy.sh \
  --environment production \
  --domain activelog.com \
  --region us-west-2 \
  --yes
```

#### 2. Manual Terraform Deployment
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

### Domain and SSL Configuration

#### Domain Registration
1. **activelog.ai** (Main platform domain)
   - Production: https://activelog.ai
   - API: https://api.activelog.ai
   - CDN: https://cdn.activelog.ai

2. **activeledger.ai** (Financial trading platform)
   - Production: https://activeledger.ai
   - Trading API: https://trading.activeledger.ai
   - Market Data: https://market.activeledger.ai

#### SSL Certificate Setup
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificates
sudo certbot --nginx -d api.activelog.ai
sudo certbot --nginx -d personallog.activelog.ai  
sudo certbot --nginx -d fishinglog.activelog.ai
```

### Service Distribution

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

---

## Complete System Rebuild Guide

### SuperInstance Architecture

The ActiveLog SuperInstance implements a revolutionary architecture that enables a single master codebase to serve multiple specialized domains through intelligent service pruning, dynamic deployment strategies, and advanced container orchestration.

#### Core Statistics
- **182 Microservices** across 5 domains
- **Container-native architecture** with Kubernetes orchestration
- **Cross-domain data synchronization** with Apache Kafka
- **Multi-LLM integration** (Claude, OpenAI, Ollama, GPT4All)
- **Production-ready** with comprehensive monitoring and security

### Phase-by-Phase Rebuild Process

#### Phase 1: Infrastructure Setup

**Base System Preparation**
```bash
# Create project directory
mkdir -p /opt/activelog-superinstance
cd /opt/activelog-superinstance

# Clone repository
git clone https://github.com/your-org/activelog.git .

# Create necessary directories
mkdir -p logs data backups ssl config
```

**Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Required Environment Variables:
DATABASE_URL=postgresql://superinstance:SuperInstance2025!@postgres:5432/superinstance
REDIS_URL=redis://redis:6379
CLAUDE_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
DOMAIN=activelog.ai
JWT_SECRET_KEY=your_jwt_secret_key_here
PORT_RANGE_START=8400
PORT_RANGE_END=8500
```

**Database Setup**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres createdb superinstance
sudo -u postgres createuser superinstance

# Set password and permissions
sudo -u postgres psql << EOF
ALTER USER superinstance WITH PASSWORD 'SuperInstance2025!';
GRANT ALL PRIVILEGES ON DATABASE superinstance TO superinstance;
\q
EOF

# Run database initialization scripts
psql -U superinstance -d superinstance -f scripts/init_database.sql
psql -U superinstance -d superinstance -f activelog_fitness_schema.sql
psql -U superinstance -d superinstance -f migrations/001_create_indexes.sql
```

#### Phase 2: Core Service Deployment

**Authentication Service (Port 8000)**
```bash
cd services/auth-service

# Install dependencies
pip install -r requirements.txt

# Initialize auth database
python -c "
from main import init_database
init_database()
"

# Start service
python main.py --port 8000
```

**API Gateway (Port 8080)**
```bash
cd services/api-gateway

# Install dependencies
pip install -r requirements.txt

# Start gateway
python main.py --port 8080
```

**Testing Core Services**
```bash
# Test authentication
curl http://localhost:8000/health

# Create test user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'
```

#### Phase 3: Domain-Specific Service Deployment

**Personal Productivity Domain**
```bash
# PersonalLog Backend (Port 8001)
cd services/personallog-backend
pip install -r requirements.txt
python -c "
from main import setup_database
setup_database()
"
python main.py --port 8001

# Collaboration Sync Service
cd services/collaboration-sync
pip install -r requirements.txt
python main.py
```

**Gaming Entertainment Domain**
```bash
# DMLog Session Logger
cd services/dmlog-session-logger
pip install -r requirements.txt
python main.py

# DMLog Character Builder
cd services/dmlog-character-builder
pip install -r requirements.txt
python main.py

# DMLog World Builder
cd services/dmlog-world
pip install -r requirements.txt
python main.py
```

**Business Operations Domain**
```bash
# Accounting Core
cd services/accounting-core
pip install -r requirements.txt
python main.py

# Invoice Engine
cd services/invoice-engine
pip install -r requirements.txt
python main.py

# Business Platform
cd services/business-platform
pip install -r requirements.txt
python main.py
```

#### Phase 4: Production Deployment

**Docker Containerization**
```bash
# Build all services using docker-compose
docker-compose build

# Start infrastructure services first
docker-compose up -d postgres redis

# Wait for databases to initialize
sleep 30

# Start core services
docker-compose up -d auth-service api-gateway cache

# Start domain services
docker-compose up -d personallog-backend fishinglog-backend dmlog-core accounting-core fitness-data-api
```

**Nginx Load Balancer Configuration**
```bash
# Create nginx configuration
sudo nano /etc/nginx/sites-available/activelog
```

```nginx
upstream api_gateway {
    server 127.0.0.1:8080 weight=3;
    server 127.0.0.1:8081 weight=3;
    server 127.0.0.1:8082 weight=3;
    keepalive 32;
}

server {
    listen 80;
    server_name api.activelog.ai;
    
    location / {
        proxy_pass http://api_gateway;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Domain-specific configurations
server {
    listen 80;
    server_name personallog.activelog.ai;
    
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## Container-Based Deployments

### Docker Compose Deployment

#### When to Use Docker Compose

**✅ Perfect for:**
- Development and testing environments
- Small team deployments (1-50 users)
- Single-server production setups
- Proof-of-concept deployments
- CI/CD pipeline testing

**❌ Not ideal for:**
- High-availability production (use Kubernetes)
- Multi-server deployments
- Auto-scaling requirements
- Enterprise-scale deployments

#### Quick Start (5 minutes)

```bash
# 1. Clone Repository
git clone https://github.com/activelog/activelog.git
cd activelog

# 2. Configure Environment
cp .env.example .env
./scripts/generate-secrets.sh

# 3. Start ActiveLog
docker compose up -d

# 4. Watch startup logs
docker compose logs -f

# 5. Verify Installation
./scripts/health-check.sh
curl http://localhost:8000/health
```

#### Access Points
- **Web App:** http://localhost:3000
- **API Documentation:** http://localhost:8000/docs
- **Admin Panel:** http://localhost:3000/admin

**Default Login:**
- Username: `admin@activelog.com`
- Password: `admin123` (change immediately!)

#### Production Docker Compose Setup

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash activelog
sudo usermod -aG docker activelog
sudo su - activelog

# Set up directories
mkdir -p ~/activelog/{data,logs,backups,ssl}
cd ~/activelog
git clone https://github.com/activelog/activelog.git .

# Create production environment file
cp .env.example .env.production
```

### Kubernetes Deployment

#### Horizontal Scaling with Kubernetes
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: activelog/api-gateway:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          value: "postgresql://user:pass@postgres:5432/db"
```

#### Service Management
```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Scale services
kubectl scale deployment api-gateway --replicas=5

# Check service status
kubectl get pods
kubectl get services
```

---

## Smart Contract Deployment

### Contract Architecture

#### Core Contracts
1. **ActiveLogShareToken.sol**: ERC20 token representing equity shares
2. **VestingContract.sol**: Employee stock option vesting
3. **GovernanceContract.sol**: Shareholder voting system
4. **ComplianceAutomation.sol**: KYC/AML verification

### Development Environment Setup

```bash
# Install Node.js and npm
node --version  # v18.0.0+
npm --version   # v8.0.0+

# Install Hardhat development framework
npm install --save-dev hardhat
npm install --save-dev @nomiclabs/hardhat-ethers ethers

# Install OpenZeppelin contracts
npm install @openzeppelin/contracts

# Install additional dependencies
npm install --save-dev @nomiclabs/hardhat-waffle chai
```

### Network Configuration

```javascript
// hardhat.config.js
require("@nomiclabs/hardhat-waffle");

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    mainnet: {
      url: process.env.MAINNET_RPC_URL,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      gasPrice: 20000000000 // 20 gwei
    },
    polygon: {
      url: "https://polygon-rpc.com/",
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      gasPrice: 30000000000 // 30 gwei
    },
    arbitrum: {
      url: "https://arb1.arbitrum.io/rpc",
      accounts: [process.env.DEPLOYER_PRIVATE_KEY]
    }
  }
};
```

### Complete Deployment Script

```javascript
// scripts/deploy-all.js
const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  
  // Company parameters
  const COMPANY_VALUATION = ethers.utils.parseEther("1000000"); // $1M
  const TOTAL_SHARES = 1000000; // 1M shares
  const COMPLIANCE_OFFICER = process.env.COMPLIANCE_OFFICER;
  
  console.log("=== ActiveLog Smart Contract Deployment ===");
  console.log("Deployer:", deployer.address);
  console.log("Balance:", ethers.utils.formatEther(await deployer.getBalance()));
  
  // 1. Deploy Share Token
  console.log("\n1. Deploying Share Token...");
  const ShareToken = await ethers.getContractFactory("ActiveLogShareToken");
  const shareToken = await ShareToken.deploy(
    "ActiveLog Shares",
    "ALOG",
    COMPANY_VALUATION,
    TOTAL_SHARES
  );
  await shareToken.deployed();
  console.log("✓ ShareToken:", shareToken.address);
  
  // 2. Deploy Vesting Contract
  console.log("\n2. Deploying Vesting Contract...");
  const VestingContract = await ethers.getContractFactory("VestingContract");
  const vesting = await VestingContract.deploy(shareToken.address);
  await vesting.deployed();
  console.log("✓ VestingContract:", vesting.address);
  
  // 3. Deploy Governance Contract
  console.log("\n3. Deploying Governance Contract...");
  const GovernanceContract = await ethers.getContractFactory("GovernanceContract");
  const governance = await GovernanceContract.deploy(shareToken.address);
  await governance.deployed();
  console.log("✓ GovernanceContract:", governance.address);
  
  // 4. Deploy Compliance Contract
  console.log("\n4. Deploying Compliance Contract...");
  const ComplianceAutomation = await ethers.getContractFactory("ComplianceAutomation");
  const compliance = await ComplianceAutomation.deploy(COMPLIANCE_OFFICER);
  await compliance.deployed();
  console.log("✓ ComplianceAutomation:", compliance.address);
  
  // Save addresses
  const addresses = {
    network: hre.network.name,
    shareToken: shareToken.address,
    vesting: vesting.address,
    governance: governance.address,
    compliance: compliance.address,
    deployer: deployer.address,
    timestamp: new Date().toISOString()
  };
  
  const fs = require('fs');
  fs.writeFileSync(
    `deployment-${hre.network.name}.json`,
    JSON.stringify(addresses, null, 2)
  );
  
  return addresses;
}
```

### Deployment Commands

```bash
# Local Development
npx hardhat node
npx hardhat run scripts/deploy-all.js --network localhost

# Testnet Deployment
npx hardhat run scripts/deploy-all.js --network goerli

# Mainnet Deployment
npx hardhat run scripts/deploy-all.js --network mainnet
npx hardhat run scripts/deploy-all.js --network polygon
npx hardhat run scripts/deploy-all.js --network arbitrum
```

---

## DMLog Gaming Platform Deployment

### Two-Tier Gaming Architecture

The DMLog platform implements an innovative arcade-style architecture that maximizes performance while minimizing costs through a two-tier system.

#### ✅ BASIC TIER (Always-On)
- **Instance**: t3.micro (Free Tier eligible)
- **Monthly Cost**: ~$8-12 (FREE for first year with AWS Free Tier)
- **Always Available Services**:
  - 🎲 Core RPG Engine (dice rolling, basic mechanics)
  - 🌐 Web Interface for game management
  - 📊 Session logging and basic features

#### ⚡ ADVANCED TIER (On-Demand)
- **Instance**: c5.large (auto-created when needed)
- **Cost**: $0.096/hour (~$0.38 for 4-hour session)
- **Gaming Session Services**:
  - 🧙‍♂️ AI-Powered Dungeon Master
  - 👤 Advanced Character Builder with 3D visualization
  - 🌍 Intelligent World Builder
  - ⚔️ Advanced Combat Simulator
  - 🎨 Real-time collaboration tools

### Deployment Process

#### 1. Basic Tier Setup
```bash
# Deploy basic tier (always-on)
./dmlog_basic_deploy.sh

# Verify deployment
./dmlog_game_manager.sh status
```

#### 2. Advanced Tier Configuration
```bash
# Deploy advanced tier infrastructure
./dmlog_advanced_deploy.sh

# Configure auto-scaling
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name dmlog-advanced-tier \
  --min-size 0 \
  --max-size 1 \
  --desired-capacity 0
```

### Gaming Session Management

```bash
# Check platform status
./dmlog_game_manager.sh status

# Start a gaming session (launches advanced features)
./dmlog_game_manager.sh start

# Stop session when done (saves money)
./dmlog_game_manager.sh stop

# View cost calculator
./dmlog_game_manager.sh cost
```

### Gaming Features

#### Basic Tier Features (Always Available)
- D20 dice rolling system
- Basic character sheets
- Campaign session logs
- Simple encounter tracking
- Party management tools

#### Advanced Tier Features (On-Demand)
- **AI Dungeon Master**: Generates campaigns, NPCs, and storylines
- **Smart Character Builder**: AI-optimized builds with 3D preview
- **World Generator**: Procedural world creation with lore consistency
- **Combat Simulator**: Advanced tactical combat with environmental effects
- **Voice Integration**: Speech recognition for immersive gameplay
- **Real-time Collaboration**: Multi-player session management
- **3D Visualization**: WebGL rendering for characters and scenes

### Cost Examples
- **Casual Gamer** (8 hours/month): ~$11-13
- **Regular Gamer** (16 hours/month): ~$12-15  
- **Hardcore Gamer** (40 hours/month): ~$16-20

---

## Development Environment Setup

### Local Development Setup

#### System Requirements
- **Minimum**: 4 CPU cores, 8GB RAM, 50GB storage
- **Recommended**: 8 CPU cores, 16GB RAM, 200GB SSD storage

#### Quick Development Setup
```bash
# Clone repository
git clone https://github.com/activelog/activelog.git
cd activelog

# Setup development environment
./scripts/dev-setup.sh

# Start development services
docker-compose -f docker-compose.dev.yml up -d

# Install development dependencies
npm install
pip install -r requirements-dev.txt

# Run database migrations
python manage.py migrate

# Create development user
python manage.py createsuperuser

# Start development server
npm run dev
```

#### Development Services
- **Frontend Dev Server**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Database Admin**: http://localhost:8080 (pgAdmin)
- **Redis Admin**: http://localhost:8081 (Redis Commander)
- **Documentation**: http://localhost:8082

### CI/CD Pipeline Setup

#### GitHub Actions Workflow
```yaml
name: ActiveLog CI/CD
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm install
      - name: Run tests
        run: npm test
      - name: Build application
        run: npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: ./scripts/deploy-production.sh
```

---

## Production Operations

### Service Management

#### Systemd Services
```bash
# Create service template
sudo nano /etc/systemd/system/activelog@.service
```

```ini
[Unit]
Description=ActiveLog %i Service
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=activelog
WorkingDirectory=/opt/activelog-superinstance/services/%i
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=/opt/activelog-superinstance

[Install]
WantedBy=multi-user.target
```

#### Enable and Manage Services
```bash
sudo systemctl enable activelog@auth-service
sudo systemctl enable activelog@api-gateway
sudo systemctl enable activelog@personallog-backend

sudo systemctl start activelog@auth-service
sudo systemctl start activelog@api-gateway

# Check service status
sudo systemctl status activelog@auth-service
```

### Health Check Monitoring

```bash
#!/bin/bash
# scripts/health_check.sh
services=(
    "auth-service:8000"
    "api-gateway:8080"
    "personallog-backend:8001"
    "fishinglog-backend:8002"
    "accounting-core:8003"
)

for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    if curl -s "http://localhost:$port/health" > /dev/null; then
        echo "✅ $name is healthy"
    else
        echo "❌ $name is unhealthy"
    fi
done
```

### Database Operations

#### Connection Pooling
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=300
)
```

#### Performance Indexes
```sql
-- Apply performance indexes
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX CONCURRENTLY idx_entries_created_at ON entries(created_at DESC);
```

### Load Balancing and Scaling

#### Nginx Load Balancer
```nginx
upstream backend {
    least_conn;
    server backend1.example.com:8000 weight=3;
    server backend2.example.com:8000 weight=3;
    server backend3.example.com:8000 weight=2;
    keepalive 32;
}

server {
    listen 80;
    server_name api.activelog.ai;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Monitoring and Maintenance

### Prometheus and Grafana Setup

#### Prometheus Configuration
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'activelog-services'
    static_configs:
      - targets: 
        - 'localhost:8000'  # auth-service
        - 'localhost:8001'  # personallog-backend
        - 'localhost:8002'  # fishinglog-backend
        - 'localhost:8080'  # api-gateway
```

#### Start Monitoring Services
```bash
# Start Prometheus
docker run -d -p 9090:9090 \
  -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Start Grafana
docker run -d -p 3000:3000 grafana/grafana
```

### CloudWatch Integration (AWS)

#### Key Metrics Monitored

**ECS Services**
- CPU and memory utilization
- Task count and health
- Service discovery status
- Load balancer health checks

**RDS Database**
- CPU, memory, and storage utilization
- Connection count
- Query performance
- Backup status

**ElastiCache Redis**
- CPU and memory utilization
- Cache hit ratio
- Connection count
- Eviction rate

**Application Load Balancer**
- Request count and latency
- HTTP response codes
- Target health
- SSL certificate status

### Backup Strategy

#### Database Backup
```bash
#!/bin/bash
# scripts/backup_database.sh
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/opt/activelog-superinstance/backups"
DB_NAME="superinstance"

# Create backup
pg_dump -U superinstance -d $DB_NAME | gzip > "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: backup_$TIMESTAMP.sql.gz"
```

#### Application Data Backup
- **S3 versioning**: Enabled on all buckets
- **Cross-region replication**: Critical data only
- **Lifecycle policies**: Automatic archiving to Glacier

### Maintenance Procedures

#### Daily Tasks
- Check system health via monitoring dashboards
- Review application logs for errors
- Verify backup completion

#### Weekly Tasks
- Update security patches
- Review performance metrics
- Clean up old log files

#### Monthly Tasks
- Database maintenance and optimization
- SSL certificate renewal check
- Capacity planning review
- Security audit

---

## Cost Management

### AWS Cost Breakdown

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

### Cost Optimization Strategies

1. **Use Spot Instances**: 70% cost savings on ECS Fargate
2. **Right-size Resources**: Monitor and adjust instance sizes
3. **Storage Lifecycle**: Automatic transition to cheaper storage classes
4. **Reserved Instances**: 1-3 year commitments for predictable workloads
5. **Cost Alerts**: Automatic notifications when budgets are exceeded

### Budget Alerts
- **50% budget alert**: Early warning
- **80% budget alert**: Action required
- **100% budget alert**: Budget exceeded
- **120% budget alert**: Emergency alert

### DMLog Gaming Platform Costs

#### Basic Tier (Always Running)
- **t3.micro**: $8.50/month (FREE first year)
- **Storage**: $2/month
- **Total**: $10.50/month (or FREE)

#### Advanced Tier (Gaming Sessions Only)
- **Per Hour**: $0.096
- **2-hour session**: $0.19
- **4-hour session**: $0.38
- **8-hour epic session**: $0.77
- **Weekly 4-hour sessions**: ~$6.14/month

---

## Security and Compliance

### Security Architecture

#### Multi-Layer Security
- **Zero Trust Model**: All services authenticated
- **API Security**: Rate limiting, input validation
- **Data Protection**: Field-level encryption for PII
- **Access Control**: RBAC with attribute-based extensions

#### Security Headers
```python
# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response
```

#### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest):
    # Login implementation
    pass
```

### Compliance Framework

#### Certifications and Standards
- **SOC 2 Type II**: Completed August 2024
- **GDPR Compliance**: Full compliance implemented
- **HIPAA Ready**: Healthcare module certified
- **PCI DSS**: Level 1 merchant compliance

#### Security Testing
- **Penetration Testing**: Quarterly external audits
- **Vulnerability Scanning**: Daily automated scans
- **Security Reviews**: All code changes reviewed
- **Incident Response**: 24/7 security monitoring

### Disaster Recovery

#### Recovery Objectives
- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 15 minutes

#### Recovery Strategy
1. **Database**: Point-in-time recovery available
2. **Application**: Blue-green deployment capability
3. **Files**: Cross-region replication for critical data
4. **Infrastructure**: Infrastructure as Code for rapid rebuild

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Services Won't Start
```bash
# Check logs
docker-compose logs service-name

# Check port conflicts
sudo netstat -tlnp | grep :8000

# Verify environment variables
echo $DATABASE_URL
```

#### 2. Database Connection Issues
```bash
# Test PostgreSQL connectivity
psql -U superinstance -d superinstance -c "SELECT version();"

# Check database permissions
psql -U superinstance -d superinstance -c "\du"

# Restart database
sudo systemctl restart postgresql
```

#### 3. High Memory Usage
```bash
# Monitor resource usage
docker stats

# Adjust container memory limits
# Edit docker-compose.yml and add:
# mem_limit: 512m
```

#### 4. SSL Certificate Issues
```bash
# Renew certificates
sudo certbot renew

# Check certificate expiration
sudo certbot certificates

# Test SSL configuration
openssl s_client -connect api.activelog.ai:443
```

#### 5. Terraform State Lock
```bash
# If deployment fails due to state lock
terraform force-unlock LOCK_ID -force

# Or delete the lock manually from DynamoDB
aws dynamodb delete-item \
  --table-name activelog-terraform-locks-staging \
  --key '{"LockID":{"S":"YOUR_LOCK_ID"}}'
```

#### 6. ECS Service Not Starting
```bash
# Check service events
aws ecs describe-services --cluster activelog-staging-cluster --services activelog-staging-auth-service

# Check task logs
aws logs get-log-events --log-group-name /ecs/activelog-staging/auth-service
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

# Check service health
curl -f http://localhost:8000/health || echo "Service unhealthy"

# Monitor system resources
htop
iostat -x 1
free -h
df -h
```

### Load Testing

#### K6 Load Testing
```bash
# Install k6
sudo apt update
sudo apt install k6

# Create load test script
nano tests/load_test.js
```

```javascript
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
};

export default function() {
  let response = http.get('http://localhost:8080/health');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
}
```

```bash
# Run load test
k6 run tests/load_test.js
```

### Performance Optimization

#### Database Performance
```sql
-- Check slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Vacuum and analyze tables
VACUUM ANALYZE;
```

#### Application Performance
```python
# Redis caching configuration
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args))}"
            cached = redis_client.get(cache_key)
            
            if cached:
                return json.loads(cached)
            
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            return result
        return wrapper
    return decorator
```

---

## References

This guide consolidates information from the following source documents:
- AWS Infrastructure Setup Guide (`AWS-SETUP-GUIDE.md`)
- Complete System Rebuild Guide (`COMPLETE_SYSTEM_REBUILD_GUIDE.md`)
- Comprehensive Implementation Guide (`COMPREHENSIVE_IMPLEMENTATION_GUIDE.md`)
- Deployment Guide (`DEPLOYMENT_GUIDE.md`)
- Development Environment Guide (`DEVELOPMENT_ENVIRONMENT_GUIDE.md`)
- DMLog Deployment Complete (`DMLOG_DEPLOYMENT_COMPLETE.md`)
- Docker Compose Guide (`docker-compose.md`)
- Smart Contract Deployment Guide (`deployment-guide.md`)
- Various specialized deployment guides for DMLOG, AI services, and infrastructure components

---

**Document Version**: 1.0  
**Last Updated**: August 31, 2024  
**Maintained By**: DevOps Team  
**Next Review**: September 30, 2024