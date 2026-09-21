#!/bin/bash

# SuperInstance.AI Remote Deployment Script
set -euo pipefail

# Configuration
EC2_HOST="${EC2_HOST:-ubuntu@54.203.181.245}"
EC2_KEY="${EC2_KEY:-/home/activeloguser/.ssh/personallog_key}"
SUPERINSTANCE_HOME="/home/ubuntu/superinstance"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Create remote installation script
create_remote_script() {
    cat > /tmp/superinstance-remote-install.sh << 'EOF'
#!/bin/bash
set -euo pipefail

# Update system and install Docker
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-plugin nginx curl git

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# Create directory structure
mkdir -p /home/ubuntu/superinstance/{config,services,scripts,logs,data,secrets,monitoring,docs}

# Create docker-compose.yml for basic services
cat > /home/ubuntu/superinstance/docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    container_name: superinstance-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf
    restart: unless-stopped

  redis:
    image: redis:alpine
    container_name: superinstance-redis
    ports:
      - "6379:6379"
    restart: unless-stopped

  auth-service:
    build: ./services/auth
    container_name: superinstance-auth
    ports:
      - "3001:3001"
    environment:
      - JWT_SECRET=superinstance-jwt-secret-key
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  fishinglog-backend:
    build: ./services/fishinglog
    container_name: superinstance-fishinglog
    ports:
      - "8001:8001"
    depends_on:
      - auth-service
      - redis
    restart: unless-stopped
COMPOSE_EOF

# Create nginx configuration
mkdir -p /home/ubuntu/superinstance/config
cat > /home/ubuntu/superinstance/config/nginx.conf << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    upstream auth_service {
        server auth-service:3001;
    }
    
    upstream fishinglog_service {
        server fishinglog-backend:8001;
    }

    server {
        listen 80;
        server_name fishinglog.ai;
        
        location /auth/ {
            proxy_pass http://auth_service/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location / {
            proxy_pass http://fishinglog_service/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
    
    server {
        listen 80 default_server;
        server_name _;
        return 301 http://fishinglog.ai$request_uri;
    }
}
NGINX_EOF

# Create auth service
mkdir -p /home/ubuntu/superinstance/services/auth
cat > /home/ubuntu/superinstance/services/auth/Dockerfile << 'AUTH_DOCKERFILE'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3001
CMD ["npm", "start"]
AUTH_DOCKERFILE

cat > /home/ubuntu/superinstance/services/auth/package.json << 'AUTH_PACKAGE'
{
  "name": "superinstance-auth",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.0",
    "jsonwebtoken": "^9.0.0",
    "bcryptjs": "^2.4.3",
    "redis": "^4.6.0",
    "cors": "^2.8.5"
  }
}
AUTH_PACKAGE

cat > /home/ubuntu/superinstance/services/auth/server.js << 'AUTH_SERVER'
const express = require('express');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const redis = require('redis');
const cors = require('cors');

const app = express();
const client = redis.createClient({ url: process.env.REDIS_URL });

app.use(cors());
app.use(express.json());

client.connect();

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'auth' });
});

// Login endpoint
app.post('/login', async (req, res) => {
    const { email, password } = req.body;
    
    if (email === 'admin@superinstance.ai' && password === 'admin') {
        const token = jwt.sign({ email, role: 'admin' }, process.env.JWT_SECRET, { expiresIn: '24h' });
        res.json({ token, user: { email, role: 'admin' } });
    } else {
        res.status(401).json({ error: 'Invalid credentials' });
    }
});

// Verify token
app.post('/verify', (req, res) => {
    const { token } = req.body;
    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        res.json({ valid: true, user: decoded });
    } catch (error) {
        res.status(401).json({ valid: false, error: 'Invalid token' });
    }
});

app.listen(3001, '0.0.0.0', () => {
    console.log('SuperInstance Auth Service running on port 3001');
});
AUTH_SERVER

# Create fishinglog service
mkdir -p /home/ubuntu/superinstance/services/fishinglog
cat > /home/ubuntu/superinstance/services/fishinglog/Dockerfile << 'FISHING_DOCKERFILE'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 8001
CMD ["npm", "start"]
FISHING_DOCKERFILE

cat > /home/ubuntu/superinstance/services/fishinglog/package.json << 'FISHING_PACKAGE'
{
  "name": "fishinglog-backend",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.0",
    "cors": "^2.8.5",
    "axios": "^1.6.0"
  }
}
FISHING_PACKAGE

cat > /home/ubuntu/superinstance/services/fishinglog/server.js << 'FISHING_SERVER'
const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();

app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'fishinglog-backend' });
});

// Demo fishing logs
app.get('/api/logs', (req, res) => {
    res.json([
        {
            id: 1,
            date: '2025-08-26',
            location: 'Alaskan Waters',
            species: 'Salmon',
            quantity: 5,
            weather: 'Clear'
        },
        {
            id: 2,
            date: '2025-08-25',
            location: 'Pacific Ocean',
            species: 'Halibut',
            quantity: 2,
            weather: 'Cloudy'
        }
    ]);
});

app.post('/api/logs', (req, res) => {
    const newLog = { id: Date.now(), ...req.body };
    res.json(newLog);
});

app.listen(8001, '0.0.0.0', () => {
    console.log('FishingLog Backend running on port 8001');
});
FISHING_SERVER

echo "SuperInstance.AI remote installation completed!"
echo "Directory structure created at /home/ubuntu/superinstance"
echo "Docker services ready to start"
EOF

    chmod +x /tmp/superinstance-remote-install.sh
}

# Main deployment function
main() {
    log_info "Starting SuperInstance.AI deployment to $EC2_HOST"
    
    # Test SSH connection
    log_info "Testing SSH connection..."
    ssh -i "$EC2_KEY" "$EC2_HOST" "echo 'SSH connection successful'"
    
    # Create and upload installation script
    log_info "Creating remote installation script..."
    create_remote_script
    
    # Copy script to remote server
    log_info "Copying installation script to remote server..."
    scp -i "$EC2_KEY" /tmp/superinstance-remote-install.sh "$EC2_HOST":/tmp/
    
    # Execute remote installation
    log_info "Executing remote installation..."
    ssh -i "$EC2_KEY" "$EC2_HOST" "chmod +x /tmp/superinstance-remote-install.sh && /tmp/superinstance-remote-install.sh"
    
    # Start services
    log_info "Starting Docker services..."
    ssh -i "$EC2_KEY" "$EC2_HOST" "cd /home/ubuntu/superinstance && sudo docker compose up -d"
    
    # Get the public IP
    PUBLIC_IP=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=172.31.47.65" --query "Reservations[*].Instances[*].PublicIpAddress" --output text)
    
    log_success "SuperInstance.AI deployment completed!"
    log_success "Auth Service: http://$PUBLIC_IP:3001"
    log_success "FishingLog Backend: http://$PUBLIC_IP:8001"
    log_success "Main Site: http://$PUBLIC_IP (redirects to fishinglog.ai)"
    
    # Clean up
    rm -f /tmp/superinstance-remote-install.sh
}

main "$@"