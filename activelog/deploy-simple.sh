#!/bin/bash

# SuperInstance.AI Simple Deployment Script
set -euo pipefail

# Configuration
EC2_HOST="${EC2_HOST:-ubuntu@54.203.181.245}"
EC2_KEY="${EC2_KEY:-/home/activeloguser/.ssh/personallog_key}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Main deployment function
main() {
    log_info "Starting SuperInstance.AI deployment to $EC2_HOST"
    
    # Install Docker and services
    log_info "Installing Docker and setting up services..."
    ssh -i "$EC2_KEY" "$EC2_HOST" << 'EOF'
# Update system
sudo apt-get update -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo systemctl start docker
sudo systemctl enable docker

# Install docker-compose
sudo apt-get install -y docker-compose nginx

# Create directory structure
mkdir -p /home/ubuntu/superinstance/{config,services,logs}

# Create nginx config
sudo tee /etc/nginx/sites-available/superinstance << 'NGINX_EOF'
server {
    listen 80 default_server;
    server_name _;
    
    location /auth/ {
        proxy_pass http://localhost:3001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location / {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX_EOF

# Enable site
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/superinstance /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# Create auth service files
mkdir -p /home/ubuntu/superinstance/services/auth
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
    "cors": "^2.8.5"
  }
}
AUTH_PACKAGE

cat > /home/ubuntu/superinstance/services/auth/server.js << 'AUTH_SERVER'
const express = require('express');
const jwt = require('jsonwebtoken');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const JWT_SECRET = 'superinstance-jwt-secret-key';

app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'auth' });
});

app.post('/login', (req, res) => {
    const { email, password } = req.body;
    
    if (email === 'admin@superinstance.ai' && password === 'admin') {
        const token = jwt.sign({ email, role: 'admin' }, JWT_SECRET, { expiresIn: '24h' });
        res.json({ token, user: { email, role: 'admin' } });
    } else {
        res.status(401).json({ error: 'Invalid credentials' });
    }
});

app.post('/verify', (req, res) => {
    const { token } = req.body;
    try {
        const decoded = jwt.verify(token, JWT_SECRET);
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
    "cors": "^2.8.5"
  }
}
FISHING_PACKAGE

cat > /home/ubuntu/superinstance/services/fishinglog/server.js << 'FISHING_SERVER'
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'fishinglog-backend' });
});

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

app.get('/', (req, res) => {
    res.json({ 
        message: 'SuperInstance.AI FishingLog Backend',
        endpoints: ['/health', '/api/logs'],
        status: 'running'
    });
});

app.listen(8001, '0.0.0.0', () => {
    console.log('FishingLog Backend running on port 8001');
});
FISHING_SERVER

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install service dependencies and start services
cd /home/ubuntu/superinstance/services/auth && npm install
cd /home/ubuntu/superinstance/services/fishinglog && npm install

# Create systemd services
sudo tee /etc/systemd/system/superinstance-auth.service << 'AUTH_SERVICE'
[Unit]
Description=SuperInstance Auth Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/superinstance/services/auth
ExecStart=/usr/bin/node server.js
Restart=always
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
AUTH_SERVICE

sudo tee /etc/systemd/system/superinstance-fishinglog.service << 'FISHING_SERVICE'
[Unit]
Description=SuperInstance FishingLog Service  
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/superinstance/services/fishinglog
ExecStart=/usr/bin/node server.js
Restart=always
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
FISHING_SERVICE

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable superinstance-auth superinstance-fishinglog
sudo systemctl start superinstance-auth superinstance-fishinglog

echo "SuperInstance.AI deployment completed successfully!"
echo "Services:"
echo "- Auth Service: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):3001"
echo "- FishingLog Backend: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8001"
echo "- Main Site: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
EOF

    log_success "SuperInstance.AI deployment completed!"
    
    # Get public IP and show endpoints
    PUBLIC_IP=$(aws ec2 describe-instances --instance-ids i-0d2218e080784921d --query "Reservations[*].Instances[*].PublicIpAddress" --output text)
    
    log_success "Services available at:"
    log_success "Auth Service: http://$PUBLIC_IP:3001/health"
    log_success "FishingLog Backend: http://$PUBLIC_IP:8001/health"
    log_success "Main Site: http://$PUBLIC_IP"
}

main "$@"