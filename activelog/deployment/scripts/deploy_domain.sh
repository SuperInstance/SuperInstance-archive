#!/bin/bash

set -e

DOMAIN_NAME=$1
ENVIRONMENT=$2

if [[ -z "$DOMAIN_NAME" || -z "$ENVIRONMENT" ]]; then
    echo "Usage: $0 <domain_name> <environment>"
    echo "Example: $0 DMLog beta"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Deploying $DOMAIN_NAME to $ENVIRONMENT environment..."

# Change to project root
cd "$(dirname "$0")/../.."

# Check if domain services exist
SERVICES_DIR="services"
FRONTEND_DIR="frontend-$(echo $DOMAIN_NAME | tr '[:upper:]' '[:lower:]')"

print_status "Looking for services and frontend for $DOMAIN_NAME..."

# Find related services
DOMAIN_SERVICES=$(find $SERVICES_DIR -name "*$(echo $DOMAIN_NAME | tr '[:upper:]' '[:lower:]')*" -type d 2>/dev/null || true)
if [[ -n "$DOMAIN_SERVICES" ]]; then
    print_status "Found services:"
    echo "$DOMAIN_SERVICES"
else
    print_warning "No specific services found for $DOMAIN_NAME"
fi

# Check for frontend
if [[ -d "$FRONTEND_DIR" ]]; then
    print_status "Found frontend: $FRONTEND_DIR"
else
    print_warning "No frontend found for $DOMAIN_NAME at $FRONTEND_DIR"
    # Look for alternative frontend directories
    ALTERNATIVE_FRONTEND=$(find . -name "*$(echo $DOMAIN_NAME | tr '[:upper:]' '[:lower:]')*" -type d | grep frontend | head -1)
    if [[ -n "$ALTERNATIVE_FRONTEND" ]]; then
        FRONTEND_DIR="$ALTERNATIVE_FRONTEND"
        print_status "Using alternative frontend: $FRONTEND_DIR"
    fi
fi

# Create deployment package
DEPLOYMENT_PACKAGE="/tmp/${DOMAIN_NAME}_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S).tar.gz"
print_status "Creating deployment package: $DEPLOYMENT_PACKAGE"

# Create temporary directory for packaging
TEMP_DIR="/tmp/activelog_deploy_$$"
mkdir -p "$TEMP_DIR/$DOMAIN_NAME"

# Copy common files
print_status "Packaging common files..."
cp -r deployment/scripts "$TEMP_DIR/$DOMAIN_NAME/" 2>/dev/null || true
cp -r security "$TEMP_DIR/$DOMAIN_NAME/" 2>/dev/null || true

# Copy domain-specific services
if [[ -n "$DOMAIN_SERVICES" ]]; then
    print_status "Packaging domain services..."
    echo "$DOMAIN_SERVICES" | while read -r service; do
        if [[ -n "$service" && -d "$service" ]]; then
            cp -r "$service" "$TEMP_DIR/$DOMAIN_NAME/services/"
        fi
    done
fi

# Copy core services that all domains need
CORE_SERVICES=("api-gateway" "auth" "analytics" "backup")
print_status "Packaging core services..."
for core_service in "${CORE_SERVICES[@]}"; do
    if [[ -d "$SERVICES_DIR/$core_service" ]]; then
        mkdir -p "$TEMP_DIR/$DOMAIN_NAME/services"
        cp -r "$SERVICES_DIR/$core_service" "$TEMP_DIR/$DOMAIN_NAME/services/"
    fi
done

# Copy frontend
if [[ -d "$FRONTEND_DIR" ]]; then
    print_status "Packaging frontend..."
    cp -r "$FRONTEND_DIR" "$TEMP_DIR/$DOMAIN_NAME/frontend"
fi

# Create Docker Compose file for deployment
print_status "Generating Docker Compose configuration..."
cat > "$TEMP_DIR/$DOMAIN_NAME/docker-compose.yml" << EOF
version: '3.8'

services:
  # Load Balancer / Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api-gateway
      - frontend
    restart: unless-stopped
    networks:
      - activelog-network

  # API Gateway
  api-gateway:
    build: ./services/api-gateway
    environment:
      - ENVIRONMENT=$ENVIRONMENT
      - DOMAIN_NAME=$DOMAIN_NAME
      - PORT=8000
    expose:
      - "8000"
    depends_on:
      - auth
      - analytics
    restart: unless-stopped
    networks:
      - activelog-network

  # Authentication Service
  auth:
    build: ./services/auth
    environment:
      - ENVIRONMENT=$ENVIRONMENT
      - DOMAIN_NAME=$DOMAIN_NAME
      - PORT=8001
    expose:
      - "8001"
    restart: unless-stopped
    networks:
      - activelog-network

  # Analytics Service
  analytics:
    build: ./services/analytics
    environment:
      - ENVIRONMENT=$ENVIRONMENT
      - DOMAIN_NAME=$DOMAIN_NAME
      - PORT=8002
    expose:
      - "8002"
    restart: unless-stopped
    networks:
      - activelog-network

  # Frontend
  frontend:
    build: ./frontend
    environment:
      - ENVIRONMENT=$ENVIRONMENT
      - DOMAIN_NAME=$DOMAIN_NAME
      - REACT_APP_API_URL=http://api-gateway:8000
    expose:
      - "3000"
    depends_on:
      - api-gateway
    restart: unless-stopped
    networks:
      - activelog-network

  # Health Check Service
  health-check:
    image: alpine:latest
    command: |
      sh -c 'while true; do
        sleep 30
        wget -q --spider http://nginx/health || echo "Health check failed"
      done'
    depends_on:
      - nginx
    restart: unless-stopped
    networks:
      - activelog-network

networks:
  activelog-network:
    driver: bridge

volumes:
  app-data:
EOF

# Create nginx configuration
print_status "Generating Nginx configuration..."
cat > "$TEMP_DIR/$DOMAIN_NAME/nginx.conf" << EOF
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api-gateway:8000;
    }

    upstream frontend_backend {
        server frontend:3000;
    }

    # Health check endpoint
    server {
        listen 80;
        location /health {
            access_log off;
            return 200 "healthy\\n";
            add_header Content-Type text/plain;
        }
    }

    # Main server configuration
    server {
        listen 80 default_server;
        server_name _;

        # Frontend routes
        location / {
            proxy_pass http://frontend_backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # API routes
        location /api/ {
            proxy_pass http://api_backend/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # WebSocket support
        location /ws/ {
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF

# Create deployment script for the package
print_status "Creating deployment script..."
cat > "$TEMP_DIR/$DOMAIN_NAME/deploy.sh" << 'EOF'
#!/bin/bash

set -e

DOMAIN_NAME="${DOMAIN_NAME:-DefaultDomain}"
ENVIRONMENT="${ENVIRONMENT:-beta}"

echo "Deploying $DOMAIN_NAME in $ENVIRONMENT environment..."

# Update system packages
sudo yum update -y

# Install required packages
sudo yum install -y docker git

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
sudo mkdir -p /opt/activelog
sudo chown $USER:$USER /opt/activelog
cd /opt/activelog

# Extract deployment package (assuming it's already copied here)
if [[ -f "deployment.tar.gz" ]]; then
    tar -xzf deployment.tar.gz
    cd */
fi

# Build and start services
echo "Building and starting services..."
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Health check
echo "Performing health check..."
if curl -f http://localhost/health; then
    echo "Deployment successful! Services are healthy."
else
    echo "Health check failed. Checking logs..."
    docker-compose logs
    exit 1
fi

echo "Deployment completed successfully!"
echo "Access your application at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)"
EOF

chmod +x "$TEMP_DIR/$DOMAIN_NAME/deploy.sh"

# Create the deployment package
print_status "Creating final deployment package..."
cd "$TEMP_DIR"
tar -czf "$DEPLOYMENT_PACKAGE" "$DOMAIN_NAME"

# Get AWS information
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-west-2")
BUCKET_NAME=$(echo "${DOMAIN_NAME}-${ENVIRONMENT}-activelog-$(openssl rand -hex 4)" | tr '[:upper:]' '[:lower:]')

# Upload to S3
print_status "Uploading deployment package to S3..."
aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION" 2>/dev/null || true
aws s3 cp "$DEPLOYMENT_PACKAGE" "s3://$BUCKET_NAME/deployment.tar.gz"

print_success "Deployment package uploaded to s3://$BUCKET_NAME/deployment.tar.gz"

# Get the Auto Scaling Group name for this domain
ASG_NAME=$(aws autoscaling describe-auto-scaling-groups \
    --query "AutoScalingGroups[?contains(Tags[?Key=='Domain'].Value, '$DOMAIN_NAME') && contains(Tags[?Key=='Environment'].Value, '$ENVIRONMENT')].AutoScalingGroupName" \
    --output text 2>/dev/null || echo "")

if [[ -n "$ASG_NAME" ]]; then
    print_status "Found Auto Scaling Group: $ASG_NAME"
    
    # Create deployment script for instances
    DEPLOY_SCRIPT=$(cat << 'DEPLOY_EOF'
#!/bin/bash
cd /tmp
aws s3 cp s3://BUCKET_NAME/deployment.tar.gz .
tar -xzf deployment.tar.gz
cd */
sudo ./deploy.sh
DEPLOY_EOF
)
    
    # Replace placeholder with actual bucket name
    DEPLOY_SCRIPT=${DEPLOY_SCRIPT//BUCKET_NAME/$BUCKET_NAME}
    
    # Create user data script
    USER_DATA=$(cat << USER_DATA_EOF
#!/bin/bash
yum update -y
yum install -y awscli
$(echo "$DEPLOY_SCRIPT")
USER_DATA_EOF
)
    
    # Update launch template with new user data
    LAUNCH_TEMPLATE_ID=$(aws autoscaling describe-auto-scaling-groups \
        --auto-scaling-group-names "$ASG_NAME" \
        --query 'AutoScalingGroups[0].LaunchTemplate.LaunchTemplateId' \
        --output text 2>/dev/null)
    
    if [[ -n "$LAUNCH_TEMPLATE_ID" && "$LAUNCH_TEMPLATE_ID" != "None" ]]; then
        print_status "Updating launch template: $LAUNCH_TEMPLATE_ID"
        
        aws ec2 create-launch-template-version \
            --launch-template-id "$LAUNCH_TEMPLATE_ID" \
            --user-data "$(echo "$USER_DATA" | base64 -w 0)" \
            --source-version '$Latest' > /dev/null
        
        # Start instance refresh
        print_status "Starting instance refresh for Auto Scaling Group..."
        aws autoscaling start-instance-refresh \
            --auto-scaling-group-name "$ASG_NAME" \
            --preferences '{
                "InstanceWarmup": 300,
                "MinHealthyPercentage": 50
            }' > /dev/null
        
        print_success "Instance refresh started. New instances will be deployed automatically."
        
        # Monitor instance refresh
        print_status "Monitoring instance refresh..."
        while true; do
            REFRESH_STATUS=$(aws autoscaling describe-instance-refreshes \
                --auto-scaling-group-name "$ASG_NAME" \
                --query 'InstanceRefreshes[0].Status' \
                --output text 2>/dev/null || echo "")
            
            if [[ "$REFRESH_STATUS" == "Successful" ]]; then
                print_success "Instance refresh completed successfully!"
                break
            elif [[ "$REFRESH_STATUS" == "Failed" ]]; then
                print_error "Instance refresh failed!"
                exit 1
            else
                print_status "Instance refresh status: $REFRESH_STATUS"
                sleep 30
            fi
        done
    else
        print_warning "Could not find launch template ID"
    fi
else
    print_warning "Could not find Auto Scaling Group for $DOMAIN_NAME in $ENVIRONMENT"
    print_status "Package available at s3://$BUCKET_NAME/deployment.tar.gz for manual deployment"
fi

# Cleanup
rm -rf "$TEMP_DIR"
rm -f "$DEPLOYMENT_PACKAGE"

print_success "$DOMAIN_NAME deployment completed!"

# Save deployment information
cat > "${DOMAIN_NAME}_${ENVIRONMENT}_deployment.txt" << EOF
$DOMAIN_NAME Deployment Information
==================================
Deployment Date: $(date)
Environment: $ENVIRONMENT
Domain: $DOMAIN_NAME
S3 Bucket: $BUCKET_NAME
Auto Scaling Group: ${ASG_NAME:-Not found}
Launch Template: ${LAUNCH_TEMPLATE_ID:-Not found}

Deployment Package: s3://$BUCKET_NAME/deployment.tar.gz

Services Included:
$(echo "$DOMAIN_SERVICES" | sed 's/^/  - /')

Frontend: ${FRONTEND_DIR:-Not found}
EOF

print_status "Deployment information saved to ${DOMAIN_NAME}_${ENVIRONMENT}_deployment.txt"