# Docker Compose Deployment

Deploy ActiveLog using Docker Compose for development, testing, or small production environments. This guide covers single-server deployments with all services running as containers.

## When to Use Docker Compose

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

## Prerequisites

### System Requirements

**Minimum:**
- 4 CPU cores, 8GB RAM, 50GB storage
- Docker 20.10+ and Docker Compose 2.0+
- Ubuntu 20.04+, CentOS 8+, or macOS 12+

**Recommended:**
- 8 CPU cores, 16GB RAM, 200GB SSD storage
- Docker 24.0+ and Docker Compose 2.20+
- Dedicated server or VM

### Software Installation

**Ubuntu/Debian:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

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

**CentOS/RHEL:**
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

**macOS:**
```bash
# Install Docker Desktop
brew install --cask docker

# Or download from https://www.docker.com/products/docker-desktop
```

## Quick Start (5 minutes)

### 1. Clone Repository
```bash
git clone https://github.com/activelog/activelog.git
cd activelog
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Generate secure secrets
./scripts/generate-secrets.sh

# Edit configuration (optional)
nano .env
```

### 3. Start ActiveLog
```bash
# Start all services
docker compose up -d

# Watch startup logs
docker compose logs -f
```

### 4. Verify Installation
```bash
# Check service health
./scripts/health-check.sh

# Or manually check
curl http://localhost:8000/health
```

### 5. Access ActiveLog
- **Web App:** http://localhost:3000
- **API Documentation:** http://localhost:8000/docs
- **Admin Panel:** http://localhost:3000/admin

**Default Login:**
- Username: `admin@activelog.com`
- Password: `admin123` (change immediately!)

## Production Deployment

### 1. Prepare Production Environment

**Create dedicated user:**
```bash
sudo useradd -m -s /bin/bash activelog
sudo usermod -aG docker activelog
sudo su - activelog
```

**Set up directories:**
```bash
mkdir -p ~/activelog/{data,logs,backups,ssl}
cd ~/activelog
git clone https://github.com/activelog/activelog.git .
```

### 2. Production Configuration

**Create production environment file:**
```bash
cp .env.example .env.production
```

**Essential production settings:**
```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Generate secure secrets
JWT_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)
MINIO_ROOT_PASSWORD=$(openssl rand -base64 32)

# Database configuration
POSTGRES_HOST=postgres
POSTGRES_DB=activelog_prod
POSTGRES_USER=activelog_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# External URLs (replace with your domain)
FRONTEND_URL=https://yourdomain.com
API_URL=https://api.yourdomain.com

# SSL Configuration
SSL_ENABLED=true
SSL_CERT_PATH=./ssl/fullchain.pem
SSL_KEY_PATH=./ssl/privkey.pem

# Email configuration (for notifications)
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=your_smtp_password

# Object storage (use S3 for production)
STORAGE_BACKEND=s3
AWS_S3_BUCKET=yourdomain-activelog-files
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-west-2
```

### 3. SSL Certificate Setup

**Option A: Let's Encrypt (Recommended)**
```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d api.yourdomain.com \
  --email admin@yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/activelog/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/activelog/ssl/
sudo chown activelog:activelog ~/activelog/ssl/*

# Set up auto-renewal
sudo crontab -e
# Add: 0 2 * * * certbot renew --quiet --post-hook "docker compose -f /home/activelog/activelog/docker-compose.yml restart nginx"
```

**Option B: Self-signed (Development/Testing)**
```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem \
  -out ssl/fullchain.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=yourdomain.com"
```

### 4. Production Docker Compose

**Create production compose file:**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./data/static:/var/www/static:ro
    depends_on:
      - api-gateway
      - frontend
    restart: unless-stopped
    networks:
      - frontend

  api-gateway:
    image: activelog/api-gateway:latest
    env_file: .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - frontend
      - backend
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  auth-service:
    image: activelog/auth-service:latest
    env_file: .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  metadata-service:
    image: activelog/metadata-service:latest
    env_file: .env.production
    depends_on:
      - postgres
      - elasticsearch
    restart: unless-stopped
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  frontend:
    image: activelog/frontend:latest
    env_file: .env.production
    restart: unless-stopped
    networks:
      - frontend

  postgres:
    image: postgres:15-alpine
    env_file: .env.production
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init:/docker-entrypoint-initdb.d
    restart: unless-stopped
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    restart: unless-stopped
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    restart: unless-stopped
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    restart: unless-stopped
    networks:
      - monitoring

volumes:
  postgres_data:
  redis_data:
  elasticsearch_data:
  prometheus_data:
  grafana_data:

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
  monitoring:
    driver: bridge
```

### 5. NGINX Configuration

**Create production NGINX config:**
```nginx
# nginx/nginx.prod.conf
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api-gateway:8000;
        keepalive 32;
    }

    upstream frontend_backend {
        server frontend:3000;
        keepalive 32;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name yourdomain.com api.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # Main application server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        client_max_body_size 500M;
        client_body_timeout 300s;
        proxy_read_timeout 300s;

        # Frontend application
        location / {
            proxy_pass http://frontend_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support for real-time features
        location /ws {
            proxy_pass http://frontend_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # API server
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        client_max_body_size 500M;
        client_body_timeout 300s;
        proxy_read_timeout 300s;

        # API endpoints
        location / {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Auth endpoints (stricter rate limiting)
        location /auth {
            limit_req zone=auth burst=10 nodelay;
            
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check (no rate limiting)
        location /health {
            proxy_pass http://api_backend;
            access_log off;
        }
    }
}
```

### 6. Start Production Deployment

```bash
# Start with production configuration
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check all services are running
docker compose ps

# Monitor logs
docker compose logs -f --tail=100

# Wait for all services to be healthy
./scripts/wait-for-services.sh
```

## Service Management

### Start/Stop Services

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d api-gateway

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ Data loss!)
docker compose down -v

# Restart specific service
docker compose restart auth-service

# Scale services
docker compose up -d --scale api-gateway=3
```

### View Logs

```bash
# All services logs
docker compose logs -f

# Specific service logs
docker compose logs -f api-gateway

# Last 100 lines
docker compose logs --tail=100

# Follow logs from specific time
docker compose logs -f --since="2024-01-01T10:00:00"
```

### Service Health Monitoring

```bash
# Check service status
docker compose ps

# Health check script
./scripts/health-check.sh

# Individual service health
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Auth Service
curl http://localhost:8002/health  # Metadata Service
```

## Configuration Management

### Environment Variables

**Development (.env):**
```bash
# Development settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Local database
POSTGRES_HOST=postgres
POSTGRES_PASSWORD=dev_password_123

# Local storage
STORAGE_BACKEND=minio
MINIO_ENDPOINT=minio:9000
```

**Production (.env.production):**
```bash
# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Production database (managed)
POSTGRES_HOST=prod-db.example.com
POSTGRES_PASSWORD=secure_random_password_here

# S3 storage
STORAGE_BACKEND=s3
AWS_S3_BUCKET=activelog-prod-files
```

### Service Configuration

**Override specific service configs:**
```yaml
# docker-compose.override.yml
version: '3.8'

services:
  api-gateway:
    environment:
      - CUSTOM_SETTING=value
    volumes:
      - ./custom-config:/app/config
      
  postgres:
    command: postgres -c shared_preload_libraries=pg_stat_statements
```

### Secrets Management

**Using Docker secrets (Swarm mode):**
```bash
# Create secrets
echo "super_secret_jwt_key" | docker secret create jwt_secret -
echo "database_password" | docker secret create db_password -

# Use in compose file
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

## Backup and Recovery

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/activelog/backups"
DATE=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="/home/activelog/activelog/docker-compose.yml"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Database backup
echo "Backing up database..."
docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U activelog_user activelog_prod > \
  "$BACKUP_DIR/database_$DATE.sql"

# File storage backup (if using local MinIO)
echo "Backing up file storage..."
docker compose -f "$COMPOSE_FILE" exec -T minio tar czf - /data > \
  "$BACKUP_DIR/files_$DATE.tar.gz"

# Configuration backup
echo "Backing up configuration..."
tar czf "$BACKUP_DIR/config_$DATE.tar.gz" .env* docker-compose*.yml nginx/

# Compress and encrypt
echo "Compressing and encrypting backup..."
tar czf "$BACKUP_DIR/full_backup_$DATE.tar.gz" \
  "$BACKUP_DIR/database_$DATE.sql" \
  "$BACKUP_DIR/files_$DATE.tar.gz" \
  "$BACKUP_DIR/config_$DATE.tar.gz"

# Encrypt backup
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/full_backup_$DATE.tar.gz"

# Upload to cloud storage (optional)
if [ -n "$AWS_S3_BACKUP_BUCKET" ]; then
  aws s3 cp "$BACKUP_DIR/full_backup_$DATE.tar.gz.gpg" \
    "s3://$AWS_S3_BACKUP_BUCKET/activelog/"
fi

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.tar.gz*" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/full_backup_$DATE.tar.gz.gpg"
```

**Set up automated backups:**
```bash
# Make script executable
chmod +x ~/activelog/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/activelog/activelog/backup.sh
```

### Recovery Procedures

**Database Recovery:**
```bash
# Stop services
docker compose down

# Start only database
docker compose up -d postgres

# Restore database
docker compose exec -T postgres psql -U activelog_user -d activelog_prod < \
  /backups/database_20240101_020000.sql

# Start all services
docker compose up -d
```

**File Storage Recovery:**
```bash
# Stop services
docker compose down

# Restore files (if using MinIO)
docker compose up -d minio
docker compose exec -T minio tar xzf - -C / < /backups/files_20240101_020000.tar.gz

# Start all services
docker compose up -d
```

## Security Configuration

### Firewall Setup (UFW)

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow monitoring (restrict to specific IPs if needed)
sudo ufw allow from 10.0.0.0/8 to any port 9090  # Prometheus
sudo ufw allow from 10.0.0.0/8 to any port 3001  # Grafana

# Deny all other traffic
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Check status
sudo ufw status verbose
```

### Docker Security

```yaml
# docker-compose.security.yml
version: '3.8'

services:
  api-gateway:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    user: "1000:1000"
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

### Network Isolation

```yaml
# Network security configuration
networks:
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
  backend:
    driver: bridge
    internal: true  # No external access
    ipam:
      config:
        - subnet: 172.21.0.0/16
```

## Performance Optimization

### Resource Limits

```yaml
# docker-compose.yml resource configuration
services:
  api-gateway:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
        max_attempts: 3
        delay: 10s
```

### PostgreSQL Tuning

```bash
# postgres/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### Redis Optimization

```bash
# redis/redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### NGINX Performance

```nginx
# nginx/nginx.conf performance settings
worker_processes auto;
worker_connections 1024;

gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript;

# Enable HTTP/2
listen 443 ssl http2;

# Connection keepalive
keepalive_timeout 65;
keepalive_requests 100;
```

## Monitoring and Alerting

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'activelog'
    static_configs:
      - targets: 
          - api-gateway:8000
          - auth-service:8001
          - metadata-service:8002
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### Grafana Dashboards

```bash
# Import pre-built dashboards
curl -o monitoring/grafana/dashboards/activelog-overview.json \
  https://raw.githubusercontent.com/activelog/grafana-dashboards/main/activelog-overview.json

# Or create custom dashboard JSON files in monitoring/grafana/dashboards/
```

### Log Aggregation

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.10.0
    volumes:
      - ./logging/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.10.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.10.0
    user: root
    volumes:
      - ./logging/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - logstash
```

## Troubleshooting

### Common Issues

1. **Services won't start:**
   ```bash
   # Check service logs
   docker compose logs [service-name]
   
   # Check resource usage
   docker stats
   
   # Verify configuration
   ./scripts/validate-config.sh
   ```

2. **Database connection errors:**
   ```bash
   # Test database connectivity
   docker compose exec postgres pg_isready -U activelog_user
   
   # Check database logs
   docker compose logs postgres
   
   # Verify credentials
   docker compose exec postgres psql -U activelog_user -d activelog_prod -c "SELECT 1;"
   ```

3. **High memory usage:**
   ```bash
   # Check memory usage per service
   docker stats --no-stream
   
   # Adjust memory limits
   # Edit docker-compose.yml resource limits
   
   # Clear caches if needed
   docker compose exec redis redis-cli FLUSHALL
   ```

4. **SSL certificate issues:**
   ```bash
   # Check certificate validity
   openssl x509 -in ssl/fullchain.pem -text -noout
   
   # Test SSL connection
   openssl s_client -connect yourdomain.com:443
   
   # Renew Let's Encrypt certificate
   sudo certbot renew
   ```

### Performance Issues

1. **Slow response times:**
   ```bash
   # Check service response times
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
   
   # Monitor database performance
   docker compose exec postgres pg_stat_statements
   
   # Check resource utilization
   htop
   iotop
   ```

2. **High CPU usage:**
   ```bash
   # Identify high-CPU services
   docker stats
   
   # Scale services if needed
   docker compose up -d --scale api-gateway=3
   
   # Optimize service configurations
   ```

### Data Issues

1. **Data corruption:**
   ```bash
   # Check database integrity
   docker compose exec postgres pg_dump --schema-only activelog_prod > schema.sql
   
   # Restore from backup if needed
   docker compose exec -T postgres psql -U activelog_user -d activelog_prod < backup.sql
   ```

2. **Storage issues:**
   ```bash
   # Check disk space
   df -h
   docker system df
   
   # Clean up unused images/volumes
   docker system prune -a
   
   # Check file storage integrity
   docker compose exec minio mc admin heal minio/activelog-bucket --recursive
   ```

## Migration and Updates

### Service Updates

```bash
# Pull latest images
docker compose pull

# Update with zero downtime (if using multiple replicas)
docker compose up -d --no-deps api-gateway

# Full update (brief downtime)
docker compose down
docker compose pull
docker compose up -d
```

### Database Migrations

```bash
# Run database migrations
docker compose exec api-gateway python manage.py migrate

# Check migration status
docker compose exec api-gateway python manage.py showmigrations
```

### Configuration Updates

```bash
# Update configuration
nano .env

# Restart affected services
docker compose up -d --no-deps --force-recreate api-gateway

# Full restart if needed
docker compose restart
```

## Best Practices

### Production Checklist

- [ ] Use strong, unique passwords for all services
- [ ] Enable SSL/TLS with valid certificates
- [ ] Configure firewalls and security groups
- [ ] Set up regular automated backups
- [ ] Configure monitoring and alerting
- [ ] Use resource limits for all services
- [ ] Enable log rotation and aggregation
- [ ] Test disaster recovery procedures
- [ ] Document deployment and recovery procedures
- [ ] Set up health checks and restart policies

### Maintenance Tasks

**Daily:**
- Monitor service health and performance
- Check disk space and resource usage
- Review security logs for anomalies

**Weekly:**
- Update system packages
- Review and analyze performance metrics
- Test backup and recovery procedures

**Monthly:**
- Update Docker images and ActiveLog
- Review and update SSL certificates
- Conduct security audit
- Review and optimize resource allocation

---

**Need Help?**
- Check the [troubleshooting guide](../troubleshooting/README.md)
- Join our [Discord community](https://discord.gg/activelog)
- Contact support at support@activelog.com

*This deployment method is perfect for getting ActiveLog up and running quickly. For high-availability production environments, consider our [Kubernetes deployment guide](./kubernetes.md).*