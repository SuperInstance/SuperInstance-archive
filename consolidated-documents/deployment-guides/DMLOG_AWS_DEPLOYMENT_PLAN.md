# DMLog.ai Two-Tier AWS Deployment Plan

## Architecture Overview

### Tier 1: Basic Instance (Always-On) - t2.micro/t3.micro
**Purpose**: Lightweight services for basic functionality, minimal cost
**Monthly Cost**: ~$8-12/month (AWS Free Tier eligible)

### Tier 2: Advanced Instance (On-Demand) - c5.large/c5.xlarge + GPU
**Purpose**: AI-powered features, 3D rendering, heavy computation
**Monthly Cost**: ~$50-150/month when active (pay-per-use)

---

## TIER 1: BASIC INSTANCE (Always-On)

### Instance Specifications
- **Type**: t3.micro (2 vCPU, 1GB RAM, 8GB storage)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 20GB EBS gp3
- **Security Group**: Ports 80, 443, 8012, 8300

### Services Deployed
1. **dmlog-core** (Port 8012) - RPG rules engine
2. **dmlog-backend** (Port 8300) - Main API
3. **dmlog-frontend** (Port 80/443) - Web interface
4. **dmlog-session-logger** - Basic logging
5. **Nginx** - Reverse proxy and static files

### Dependencies
```bash
# System packages
sudo apt update && sudo apt install -y \
    python3.11 python3-pip python3-venv \
    nginx sqlite3 git curl

# Python packages (lightweight)
pip3 install fastapi uvicorn sqlalchemy pydantic \
    jinja2 aiofiles python-jose passlib bcrypt
```

### Database
- **SQLite** files for basic data storage
- **No PostgreSQL** (saves resources)

---

## TIER 2: ADVANCED INSTANCE (On-Demand)

### Instance Specifications
- **Type**: c5.xlarge (4 vCPU, 8GB RAM) + g4dn.xlarge (GPU for AI/3D)
- **OS**: Ubuntu 22.04 LTS with CUDA support
- **Storage**: 100GB EBS gp3 + 50GB for AI models
- **Security Group**: Ports 8000-9000 range

### Services Deployed
1. **dmlog-ai-dm** - AI Dungeon Master
2. **dmlog-character-builder** - Advanced character tools
3. **dmlog-world-builder-v2** - World creation (Node.js)
4. **dmlog-visualizer** - 3D rendering and Unreal Engine
5. **dmlog-battle** - Advanced combat simulation
6. **dmlog-ai-insights** - Analytics and ML
7. **dmlog-marketplace** - Content marketplace
8. **dmlog-stream** - Live streaming capabilities

### Dependencies
```bash
# System packages
sudo apt update && sudo apt install -y \
    python3.11 python3-pip python3-venv \
    nodejs npm cuda-toolkit-11-8 \
    ffmpeg portaudio19-dev postgresql-client \
    libsndfile1 libasound2-dev pulseaudio

# GPU drivers
sudo apt install nvidia-driver-525

# Python ML packages
pip3 install torch torchvision torchaudio \
    transformers spacy nltk openai langchain \
    scikit-learn numpy scipy pandas \
    librosa soundfile pillow opencv-python
```

---

## DEPLOYMENT SCRIPTS

### Basic Instance Startup Script
```bash
#!/bin/bash
# basic_instance_startup.sh

cd /home/ubuntu/dmlog

# Start basic services
python3 -m uvicorn dmlog.core.main:app --host 0.0.0.0 --port 8012 &
python3 -m uvicorn dmlog.backend.main:app --host 0.0.0.0 --port 8300 &
python3 -m uvicorn dmlog.frontend.main:app --host 0.0.0.0 --port 8080 &

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx

echo "Basic DMLog services started"
```

### Advanced Instance Startup Script
```bash
#!/bin/bash
# advanced_instance_startup.sh

cd /home/ubuntu/dmlog

# Start AI services
python3 -m uvicorn dmlog.ai_dm.main_service:app --host 0.0.0.0 --port 8020 &
python3 -m uvicorn dmlog.ai_insights.main:app --host 0.0.0.0 --port 8090 &

# Start character builder (Flask)
cd services/dmlog-character-builder
python3 main.py &
cd ../..

# Start world builder (Node.js)
cd services/dmlog-world-builder-v2
npm start &
cd ../..

# Start other advanced services
python3 -m uvicorn dmlog.battle.main:app --host 0.0.0.0 --port 8030 &
python3 -m uvicorn dmlog.marketplace.main_service:app --host 0.0.0.0 --port 8040 &

echo "Advanced DMLog services started"
```

---

## AWS DEPLOYMENT COMMANDS

### 1. Create Security Groups
```bash
# Basic instance security group
aws ec2 create-security-group \
    --group-name dmlog-basic-sg \
    --description "DMLog Basic Instance Security Group"

aws ec2 authorize-security-group-ingress \
    --group-name dmlog-basic-sg \
    --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress \
    --group-name dmlog-basic-sg \
    --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress \
    --group-name dmlog-basic-sg \
    --protocol tcp --port 8012 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress \
    --group-name dmlog-basic-sg \
    --protocol tcp --port 8300 --cidr 0.0.0.0/0

# Advanced instance security group
aws ec2 create-security-group \
    --group-name dmlog-advanced-sg \
    --description "DMLog Advanced Instance Security Group"

aws ec2 authorize-security-group-ingress \
    --group-name dmlog-advanced-sg \
    --protocol tcp --port 8000-9000 --cidr 0.0.0.0/0
```

### 2. Launch Basic Instance
```bash
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.micro \
    --key-name dmlog-key \
    --security-groups dmlog-basic-sg \
    --user-data file://basic_instance_startup.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=DMLog-Basic}]'
```

### 3. Launch Advanced Instance
```bash
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type c5.xlarge \
    --key-name dmlog-key \
    --security-groups dmlog-advanced-sg \
    --user-data file://advanced_instance_startup.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=DMLog-Advanced}]'
```

---

## INSTANCE MANAGEMENT

### Start Advanced Instance (for gaming)
```bash
# Get instance ID
INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=DMLog-Advanced" \
    --query "Reservations[0].Instances[0].InstanceId" \
    --output text)

# Start the instance
aws ec2 start-instances --instance-ids $INSTANCE_ID

# Wait for it to be running
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

echo "Advanced instance started for gaming session"
```

### Stop Advanced Instance (save money)
```bash
# Get instance ID
INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=DMLog-Advanced" \
    --query "Reservations[0].Instances[0].InstanceId" \
    --output text)

# Stop the instance
aws ec2 stop-instances --instance-ids $INSTANCE_ID

echo "Advanced instance stopped - costs reduced"
```

---

## COST OPTIMIZATION

### Basic Instance (Always-On)
- **t3.micro**: $8.50/month (Free Tier: $0 first year)
- **20GB EBS**: $2/month
- **Total**: ~$10.50/month (or free first year)

### Advanced Instance (On-Demand)
- **c5.xlarge**: $0.192/hour = ~$138/month if always on
- **100GB EBS**: $10/month
- **GPU (g4dn.xlarge)**: $0.526/hour for AI features
- **Total when active**: ~$0.70/hour

### Gaming Session Cost
- **2-hour session**: $1.40
- **4-hour session**: $2.80
- **Weekly 4-hour session**: ~$12/month

---

## MONITORING AND ALERTS

### CloudWatch Alarms
```bash
# Alert when advanced instance runs too long
aws cloudwatch put-metric-alarm \
    --alarm-name dmlog-advanced-runtime \
    --alarm-description "DMLog Advanced Instance Running Too Long" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 3600 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 4
```

This architecture provides a cost-effective, scalable solution for the DMLog gaming platform with arcade-style on-demand resource allocation.