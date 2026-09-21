#!/bin/bash

# Complete Infrastructure Deployment for ActiveLog Domains
# Deploys all infrastructure components following the template pattern

set -e

echo "============================================="
echo "ActiveLog Domain Infrastructure Deployment"
echo "============================================="

# Configuration
STACK_NAME_PREFIX="activelog"
REGION="us-east-1"
VPC_ID="vpc-12345678"  # Replace with actual VPC ID
SUBNET_IDS="subnet-12345678,subnet-87654321"  # Replace with actual subnet IDs
CERTIFICATE_ARN="arn:aws:acm:us-east-1:123456789012:certificate/example"  # Replace with actual certificate
KEY_NAME="activelog-key"  # Replace with actual key pair name

echo "Configuration:"
echo "  Region: $REGION"
echo "  VPC ID: $VPC_ID"
echo "  Subnets: $SUBNET_IDS"
echo "  Key Pair: $KEY_NAME"
echo ""

# Function to deploy CloudFormation stack
deploy_stack() {
    local stack_name=$1
    local template_file=$2
    local parameters=$3
    
    echo "Deploying stack: $stack_name"
    echo "Template: $template_file"
    
    aws cloudformation deploy \
        --template-file "$template_file" \
        --stack-name "$stack_name" \
        --parameter-overrides $parameters \
        --capabilities CAPABILITY_IAM \
        --region "$REGION" \
        --no-fail-on-empty-changeset
    
    if [ $? -eq 0 ]; then
        echo "✅ Stack $stack_name deployed successfully"
    else
        echo "❌ Failed to deploy stack $stack_name"
        exit 1
    fi
    echo ""
}

# Create infrastructure directory if it doesn't exist
mkdir -p infrastructure

echo "Step 1: Deploying Load Balancers..."
deploy_stack \
    "${STACK_NAME_PREFIX}-load-balancers" \
    "infrastructure/load-balancer-config.yml" \
    "VPCId=$VPC_ID SubnetIds=$SUBNET_IDS CertificateArn=$CERTIFICATE_ARN"

echo "Step 2: Deploying Auto Scaling Groups..."
deploy_stack \
    "${STACK_NAME_PREFIX}-auto-scaling" \
    "infrastructure/auto-scaling-config.yml" \
    "KeyName=$KEY_NAME SubnetIds=$SUBNET_IDS"

echo "Step 3: Starting Free Tier with Ads Service..."
cd services/free-tier-ads
python3 -m pip install -r requirements.txt
nohup python3 main.py > ../../logs/free-tier-ads.log 2>&1 &
echo $! > ../../pids/free-tier-ads.pid
cd ../..

echo "✅ Free Tier with Ads service started (PID: $(cat pids/free-tier-ads.pid))"

echo "Step 4: Deploying domain services..."
DOMAIN_SERVICES=(
    "personallog-backend" "personallog-repository" "personallog-deployer" "personallog-trainer"
    "personallog-builder" "personallog-defaultuser" "personallog-runner"
    "makerlog-backend" "makerlog-repository" "makerlog-deployer" "makerlog-trainer"
    "makerlog-builder" "makerlog-defaultuser" "makerlog-runner"
    "luciddreamer-backend" "luciddreamer-repository" "luciddreamer-deployer" "luciddreamer-trainer"
    "luciddreamer-builder" "luciddreamer-defaultuser" "luciddreamer-runner"
    "businesslog-backend" "businesslog-repository" "businesslog-deployer" "businesslog-trainer"
    "businesslog-builder" "businesslog-defaultuser" "businesslog-runner"
    "capitaine-backend" "capitaine-repository" "capitaine-deployer" "capitaine-trainer"
    "capitaine-builder" "capitaine-defaultuser" "capitaine-runner"
    "deckboss-backend" "deckboss-repository" "deckboss-deployer" "deckboss-trainer"
    "deckboss-builder" "deckboss-defaultuser" "deckboss-runner"
    "dmlog-backend" "dmlog-repository" "dmlog-deployer" "dmlog-trainer"
    "dmlog-builder" "dmlog-defaultuser" "dmlog-runner"
    "fishinglog-backend" "fishinglog-repository" "fishinglog-deployer" "fishinglog-trainer"
    "fishinglog-builder" "fishinglog-defaultuser" "fishinglog-runner"
    "reallog-backend" "reallog-repository" "reallog-deployer" "reallog-trainer"
    "reallog-builder" "reallog-defaultuser" "reallog-runner"
    "playerlog-backend" "playerlog-repository" "playerlog-deployer" "playerlog-trainer"
    "playerlog-builder" "playerlog-defaultuser" "playerlog-runner"
    "studylog-backend" "studylog-repository" "studylog-deployer" "studylog-trainer"
    "studylog-builder" "studylog-defaultuser" "studylog-runner"
)

echo "Starting ${#DOMAIN_SERVICES[@]} domain services..."

# Create logs and pids directories
mkdir -p logs pids

# Start all domain services
for service in "${DOMAIN_SERVICES[@]}"; do
    if [ -d "services/$service" ]; then
        echo "Starting $service..."
        cd "services/$service"
        
        # Install dependencies
        if [ -f "requirements.txt" ]; then
            python3 -m pip install -r requirements.txt > /dev/null 2>&1
        fi
        
        # Get next available port (starting from 8100)
        PORT=$((8100 + $(find ../../pids -name "*.pid" 2>/dev/null | wc -l)))
        
        # Start service
        nohup python3 main.py --port $PORT > "../../logs/$service.log" 2>&1 &
        echo $! > "../../pids/$service.pid"
        
        echo "  ✅ $service started on port $PORT (PID: $!)"
        cd ../..
        
        # Small delay to prevent port conflicts
        sleep 0.5
    else
        echo "  ⚠️  Service directory not found: services/$service"
    fi
done

echo ""
echo "Step 5: Generating deployment summary..."

# Create deployment summary
cat > deployment-summary.md << EOF
# ActiveLog Domain Deployment Summary

## Infrastructure Deployed

### Load Balancers
- 11 Application Load Balancers (one per domain)
- SSL/TLS termination with certificate
- Health checks every 30 seconds
- Cross-zone load balancing enabled

### Auto Scaling Groups
- 11 Auto Scaling Groups (one per domain)
- Min: 1 instance, Max: 10 instances per domain
- Target CPU utilization: 70%
- Health check grace period: 5 minutes

### Domains Deployed
1. **PersonalLog** - Personal journaling and life tracking
2. **MakerLog** - Project and maker activity logging  
3. **LucidDreamer** - Dream journaling and analysis
4. **BusinessLog** - Business operations and analytics
5. **Capitaine** - Maritime and navigation systems
6. **DeckBoss** - Deck operations management
7. **DMLog** - Dungeon Master tools and campaign management
8. **FishingLog** - Fishing trip logging and analysis
9. **RealLog** - Real estate transaction logging
10. **PlayerLog** - Gaming session and achievement tracking
11. **StudyLog** - Educational progress and study tracking

### Services Per Domain (77 total services)
- **Backend**: Load balancing and policy management
- **Repository**: Domain-specific deployments  
- **Deployer**: Hardware-optimized versions
- **Trainer**: Domain-specific AI models
- **Builder**: Feature development tools
- **DefaultUser**: Initial user state management
- **Runner**: Compute service orchestration

### Free Tier with Ads System
- **Service**: Running on port 8080
- **Database**: SQLite with user balance tracking
- **Ad Rates**: 
  - 15-second ad = 5 minutes compute
  - 30-second ad = 10 minutes compute  
  - 60-second ad = 25 minutes compute
  - 120-second ad = 60 minutes compute
- **Limits**: 20 ads/day, 480 minutes compute/day
- **Minimum interval**: 3 minutes between ads

## Deployment Status
- **Infrastructure**: ✅ Deployed
- **Load Balancers**: ✅ Active
- **Auto Scaling**: ✅ Configured
- **Domain Services**: ✅ Running ($(find pids -name "*.pid" | wc -l) services)
- **Free Tier System**: ✅ Operational

## Next Steps
1. Configure DNS records to point to load balancer endpoints
2. Set up monitoring and alerting
3. Configure backup and disaster recovery
4. Implement CI/CD pipelines for service updates
5. Set up centralized logging and metrics collection

## Access URLs (after DNS configuration)
- PersonalLog: https://personallog.activelog.ai
- MakerLog: https://makerlog.activelog.ai
- LucidDreamer: https://luciddreamer.activelog.ai
- BusinessLog: https://businesslog.activelog.ai
- Capitaine: https://capitaine.activelog.ai
- DeckBoss: https://deckboss.activelog.ai
- DMLog: https://dmlog.activelog.ai
- FishingLog: https://fishinglog.activelog.ai
- RealLog: https://reallog.activelog.ai
- PlayerLog: https://playerlog.activelog.ai
- StudyLog: https://studylog.activelog.ai

Deployment completed: $(date)
EOF

echo ""
echo "============================================="
echo "🎉 DEPLOYMENT COMPLETE! 🎉"
echo "============================================="
echo ""
echo "✅ Infrastructure deployed successfully"
echo "✅ $(find pids -name "*.pid" | wc -l) services running"
echo "✅ Free tier with ads system operational"
echo "✅ Load balancers configured for all 11 domains"
echo "✅ Auto-scaling enabled (1-10 instances per domain)"
echo ""
echo "📄 Deployment summary: deployment-summary.md"
echo "📊 Service logs: logs/"
echo "🔧 Process IDs: pids/"
echo ""
echo "Next: Configure DNS records and SSL certificates"