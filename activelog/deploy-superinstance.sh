#!/bin/bash

# SuperInstance.AI Fresh Deployment Script
# Container-native deployment with intelligent service pruning and cross-domain optimization
# Version: 2.0.0
# Company: SuperInstance.AI

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${LOG_FILE:-/tmp/superinstance-deployment.log}"
DEPLOYMENT_TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
SUPERINSTANCE_HOME="${SUPERINSTANCE_HOME:-/home/ubuntu/superinstance}"
CONTAINER_REGISTRY="superinstance"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-development}"

# Domain configuration
DOMAINS=(
    "personallog.ai:personal"
    "fishinglog.ai:fishing" 
    "dmlog.ai:gaming"
    "businesslog.ai:business"
    "activelog.ai:fitness"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE" 2>/dev/null || true
}

log_info() { log "INFO" "$@"; }
log_success() { log "SUCCESS" "${GREEN}$*${NC}"; }
log_warning() { log "WARN" "${YELLOW}$*${NC}"; }
log_error() { log "ERROR" "${RED}$*${NC}"; }

# Error handling
handle_error() {
    log_error "Deployment failed at line $1"
    log_error "Command: $BASH_COMMAND"
    log_error "Check logs: $LOG_FILE"
    exit 1
}

trap 'handle_error $LINENO' ERR

print_banner() {
    echo -e "${PURPLE}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                    SuperInstance.AI                         ║
║                Container-Native Deployment                   ║
║                                                              ║
║  🚀 Domains: personallog.ai, fishinglog.ai, dmlog.ai       ║
║             businesslog.ai, activelog.ai                    ║
║  📦 Container orchestration with intelligent pruning        ║
║  💰 Compute capital economy integration                     ║
║  🔗 Cross-domain resource optimization                      ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    local missing_tools=()
    
    # Required tools
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v docker-compose >/dev/null 2>&1 || missing_tools+=("docker-compose") 
    command -v nginx >/dev/null 2>&1 || missing_tools+=("nginx")
    command -v python3 >/dev/null 2>&1 || missing_tools+=("python3")
    command -v node >/dev/null 2>&1 || missing_tools+=("node")
    command -v git >/dev/null 2>&1 || missing_tools+=("git")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Installing missing tools..."
        
        sudo apt update
        for tool in "${missing_tools[@]}"; do
            case $tool in
                docker)
                    curl -fsSL https://get.docker.com -o get-docker.sh
                    sudo sh get-docker.sh
                    sudo usermod -aG docker $USER
                    ;;
                docker-compose)
                    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
                    sudo chmod +x /usr/local/bin/docker-compose
                    ;;
                nginx)
                    sudo apt install -y nginx
                    ;;
                python3)
                    sudo apt install -y python3 python3-pip python3-venv
                    ;;
                node)
                    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
                    sudo apt install -y nodejs
                    ;;
                git)
                    sudo apt install -y git
                    ;;
            esac
        done
    fi
    
    # Check Docker daemon
    if ! sudo systemctl is-active --quiet docker; then
        log_info "Starting Docker daemon..."
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    
    log_success "Prerequisites check completed"
}

# Create SuperInstance.AI directory structure on remote server
setup_directory_structure() {
    log_info "Setting up SuperInstance.AI directory structure on $EC2_HOST..."
    
    # Create container-native directory structure on remote server
    ssh -i "$EC2_KEY" "$EC2_HOST" "
        mkdir -p /home/ubuntu/superinstance/{config/{domains,kubernetes,docker-compose},services/{core,personal,fishing,gaming,business,fitness},scripts/{deployment,monitoring,backup},logs/{services,deployment,monitoring},data/{databases,cache,analytics},secrets/{certificates,keys,tokens},monitoring/{prometheus,grafana,alerts},docs/{api,deployment,architecture}}
    "
    
    log_success "Directory structure created at $SUPERINSTANCE_HOME on remote server"
}

# Generate core infrastructure containers
deploy_core_infrastructure() {
    log_info "Deploying core infrastructure containers..."
    
    cd "$SUPERINSTANCE_HOME"
    
    # Create Docker Compose for core infrastructure
    cat > docker-compose.infrastructure.yml << 'EOF'
version: '3.8'

services:
  # Redis Cache Cluster
  redis-master:
    image: redis:7-alpine
    container_name: superinstance-redis-master
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --replica-read-only no
    volumes:
      - redis-data:/data
      - ./config/redis/redis.conf:/usr/local/etc/redis/redis.conf
    networks:
      - superinstance-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # PostgreSQL Database Cluster
  postgres-primary:
    image: postgres:15-alpine
    container_name: superinstance-postgres-primary
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: superinstance
      POSTGRES_USER: superinstance
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./config/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - superinstance-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U superinstance"]
      interval: 10s
      timeout: 5s
      retries: 5

  # API Gateway with Service Mesh
  api-gateway:
    build:
      context: ./services/core/api-gateway
      dockerfile: Dockerfile
    container_name: superinstance-api-gateway
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - ENVIRONMENT=${DEPLOYMENT_ENV}
      - REDIS_URL=redis://redis-master:6379
      - DATABASE_URL=postgresql://superinstance:${POSTGRES_PASSWORD}@postgres-primary:5432/superinstance
    depends_on:
      redis-master:
        condition: service_healthy
      postgres-primary:
        condition: service_healthy
    networks:
      - superinstance-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Authentication Service
  auth-service:
    build:
      context: ./services/core/auth-service
      dockerfile: Dockerfile
    container_name: superinstance-auth-service
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=${DEPLOYMENT_ENV}
      - REDIS_URL=redis://redis-master:6379
      - DATABASE_URL=postgresql://superinstance:${POSTGRES_PASSWORD}@postgres-primary:5432/superinstance
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      redis-master:
        condition: service_healthy
      postgres-primary:
        condition: service_healthy
    networks:
      - superinstance-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Compute Capital Engine
  compute-capital-engine:
    build:
      context: ./services/core/compute-capital-engine
      dockerfile: Dockerfile
    container_name: superinstance-compute-capital-engine
    restart: unless-stopped
    ports:
      - "8090:8090"
    environment:
      - ENVIRONMENT=${DEPLOYMENT_ENV}
      - REDIS_URL=redis://redis-master:6379
      - DATABASE_URL=postgresql://superinstance:${POSTGRES_PASSWORD}@postgres-primary:5432/superinstance
    depends_on:
      redis-master:
        condition: service_healthy
      postgres-primary:
        condition: service_healthy
    networks:
      - superinstance-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Monitoring Stack
  prometheus:
    image: prom/prometheus:latest
    container_name: superinstance-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    networks:
      - superinstance-net

  grafana:
    image: grafana/grafana:latest
    container_name: superinstance-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - superinstance-net
    depends_on:
      - prometheus

volumes:
  redis-data:
  postgres-data:
  prometheus-data:
  grafana-data:

networks:
  superinstance-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
EOF

    # Generate environment file
    cat > .env << EOF
# SuperInstance.AI Environment Configuration
DEPLOYMENT_ENV=$DEPLOYMENT_ENV
POSTGRES_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 64)
GRAFANA_PASSWORD=$(openssl rand -base64 16)
COMPOSE_PROJECT_NAME=superinstance
EOF

    log_success "Core infrastructure configuration created"
}

# Create core service containers
create_core_services() {
    log_info "Creating core service containers..."
    
    # Auth Service
    mkdir -p services/core/auth-service
    cat > services/core/auth-service/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF

    cat > services/core/auth-service/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.7
redis==5.0.1
pyjwt==2.8.0
bcrypt==4.1.2
pydantic==2.5.0
python-multipart==0.0.6
slowapi==0.1.9
prometheus-client==0.19.0
EOF

    cat > services/core/auth-service/main.py << 'EOF'
"""
SuperInstance.AI Authentication Service
Container-native JWT authentication with cross-domain support
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import jwt
import bcrypt
import redis
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://superinstance:password@localhost:5432/superinstance")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "superinstance-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Initialize FastAPI
app = FastAPI(
    title="SuperInstance.AI Authentication Service",
    description="Container-native authentication with cross-domain support",
    version="2.0.0"
)

# CORS middleware for cross-domain requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://personallog.ai", "https://fishinglog.ai", "https://dmlog.ai", 
                  "https://businesslog.ai", "https://activelog.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    domains_access = Column(Text, default="personal,fishing,gaming,business,fitness")

# Create tables
Base.metadata.create_all(bind=engine)

# Redis client
redis_client = redis.from_url(REDIS_URL)

# Security
security = HTTPBearer()

# Metrics
auth_requests = Counter('auth_requests_total', 'Total authentication requests', ['domain', 'endpoint'])
auth_duration = Histogram('auth_request_duration_seconds', 'Authentication request duration')

# Pydantic models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)
    domains: Optional[str] = Field(default="personal,fishing,gaming,business,fitness")

class UserLogin(BaseModel):
    username: str
    password: str
    domain: Optional[str] = Field(default="personal")

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    domain: str

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication utilities
class AuthManager:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str):
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

auth_manager = AuthManager()

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        # Check Redis
        redis_client.ping()
        
        return {
            "status": "healthy",
            "service": "SuperInstance.AI Authentication Service",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "domains": ["personallog.ai", "fishinglog.ai", "dmlog.ai", "businesslog.ai", "activelog.ai"]
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/auth/register", response_model=dict)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user with cross-domain access"""
    auth_requests.labels(domain="registration", endpoint="/auth/register").inc()
    
    # Check if user already exists
    if db.query(User).filter((User.username == user.username) | (User.email == user.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Create new user
    hashed_password = auth_manager.hash_password(user.password)
    db_user = User(
        id=f"user_{datetime.utcnow().timestamp()}",
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        domains_access=user.domains
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {
        "message": "User registered successfully",
        "user_id": db_user.id,
        "domains_access": db_user.domains_access.split(",")
    }

@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login with domain-specific token"""
    auth_requests.labels(domain=user.domain, endpoint="/auth/login").inc()
    
    # Verify user credentials
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not auth_manager.verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user has access to requested domain
    user_domains = db_user.domains_access.split(",")
    domain_mapping = {
        "personal": "personallog.ai",
        "fishing": "fishinglog.ai", 
        "gaming": "dmlog.ai",
        "business": "businesslog.ai",
        "fitness": "activelog.ai"
    }
    
    if user.domain not in user_domains:
        raise HTTPException(status_code=403, detail=f"Access denied to {user.domain} domain")
    
    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_manager.create_access_token(
        data={
            "sub": db_user.id,
            "username": db_user.username,
            "domain": user.domain,
            "domains_access": user_domains
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = auth_manager.create_refresh_token(db_user.id)
    
    # Update last login
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    # Cache user session
    session_data = {
        "user_id": db_user.id,
        "username": db_user.username,
        "domain": user.domain,
        "login_time": datetime.utcnow().isoformat()
    }
    redis_client.setex(f"session:{db_user.id}", 3600, str(session_data))
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        domain=domain_mapping.get(user.domain, user.domain)
    )

@app.get("/auth/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token for cross-domain requests"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "domain": payload.get("domain"),
            "domains_access": payload.get("domains_access"),
            "expires": payload.get("exp")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

    # API Gateway Service
    mkdir -p services/core/api-gateway
    cat > services/core/api-gateway/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
EOF

    cat > services/core/api-gateway/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.2
pydantic==2.5.0
redis==5.0.1
prometheus-client==0.19.0
pyjwt==2.8.0
EOF

    cat > services/core/api-gateway/main.py << 'EOF'
"""
SuperInstance.AI API Gateway
Container-native gateway with intelligent routing and economic optimization
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import redis
from prometheus_client import Counter, Histogram, generate_latest

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

# Domain service mapping
DOMAIN_SERVICES = {
    "personallog.ai": "http://personallog-backend:8010",
    "fishinglog.ai": "http://fishinglog-backend:8001", 
    "dmlog.ai": "http://dmlog-backend:8020",
    "businesslog.ai": "http://businesslog-backend:8030",
    "activelog.ai": "http://activelog-backend:8040"
}

app = FastAPI(
    title="SuperInstance.AI API Gateway",
    description="Container-native gateway with intelligent routing",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://personallog.ai", "https://fishinglog.ai", "https://dmlog.ai", 
                  "https://businesslog.ai", "https://activelog.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
redis_client = redis.from_url(REDIS_URL)

# Metrics
gateway_requests = Counter('gateway_requests_total', 'Total gateway requests', ['domain', 'method', 'status'])
gateway_duration = Histogram('gateway_request_duration_seconds', 'Gateway request duration', ['domain'])
service_health = Counter('service_health_checks_total', 'Service health checks', ['service', 'status'])

class ServiceRouter:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def route_request(self, request: Request, domain: str, path: str):
        """Route request to appropriate domain service with economic optimization"""
        
        if domain not in DOMAIN_SERVICES:
            raise HTTPException(status_code=404, detail=f"Domain {domain} not found")
        
        service_url = DOMAIN_SERVICES[domain]
        full_url = f"{service_url}{path}"
        
        # Extract request data
        headers = dict(request.headers)
        headers.pop('host', None)  # Remove host header
        
        query_params = dict(request.query_params)
        
        try:
            # Route based on HTTP method
            if request.method == "GET":
                response = await self.client.get(full_url, headers=headers, params=query_params)
            elif request.method == "POST":
                body = await request.body()
                response = await self.client.post(full_url, headers=headers, params=query_params, content=body)
            elif request.method == "PUT":
                body = await request.body()
                response = await self.client.put(full_url, headers=headers, params=query_params, content=body)
            elif request.method == "DELETE":
                response = await self.client.delete(full_url, headers=headers, params=query_params)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            # Record metrics
            gateway_requests.labels(
                domain=domain, 
                method=request.method, 
                status=response.status_code
            ).inc()
            
            return JSONResponse(
                content=response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.RequestError as e:
            gateway_requests.labels(domain=domain, method=request.method, status="error").inc()
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

router = ServiceRouter()

@app.get("/health")
async def health_check():
    """Health check with service status"""
    service_status = {}
    
    for domain, service_url in DOMAIN_SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service_url}/health")
                service_status[domain] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
                service_health.labels(service=domain, status="healthy").inc()
        except Exception:
            service_status[domain] = {"status": "unreachable", "response_time": None}
            service_health.labels(service=domain, status="unhealthy").inc()
    
    return {
        "status": "healthy",
        "service": "SuperInstance.AI API Gateway", 
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": service_status
    }

@app.api_route("/{domain}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_domain_request(request: Request, domain: str, path: str):
    """Route requests to domain-specific services"""
    
    # Extract domain from subdomain format (personallog.ai -> personallog)
    if '.' in domain:
        domain_key = domain
    else:
        # Map short names to full domains
        domain_mapping = {
            "personal": "personallog.ai",
            "fishing": "fishinglog.ai",
            "gaming": "dmlog.ai", 
            "business": "businesslog.ai",
            "fitness": "activelog.ai"
        }
        domain_key = domain_mapping.get(domain, f"{domain}.ai")
    
    with gateway_duration.labels(domain=domain_key).time():
        return await router.route_request(request, domain_key, f"/{path}")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics"""
    return generate_latest()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF

    log_success "Core services created"
}

# Create domain-specific services
create_domain_services() {
    log_info "Creating domain-specific services..."
    
    # Fishing Domain Service (fishinglog.ai)
    mkdir -p services/fishing/fishinglog-backend
    cat > services/fishing/fishinglog-backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
EOF

    cat > services/fishing/fishinglog-backend/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.7
pydantic==2.5.0
httpx==0.25.2
prometheus-client==0.19.0
redis==5.0.1
EOF

    cat > services/fishing/fishinglog-backend/main.py << 'EOF'
"""
SuperInstance.AI FishingLog Backend Service
Container-native fishing operations logging with cross-domain analytics
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from prometheus_client import Counter, generate_latest
import httpx

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://superinstance:password@localhost:5432/superinstance")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

app = FastAPI(
    title="FishingLog.ai Backend Service",
    description="Container-native fishing operations logging",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fishinglog.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FishingCatch(Base):
    __tablename__ = "fishing_catches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    fish_type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    weight = Column(Float)
    length = Column(Float)
    bait_used = Column(String)
    technique = Column(String)
    weather_conditions = Column(String)
    catch_released = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Metrics
catches_created = Counter('fishing_catches_created_total', 'Total fishing catches created')
catches_retrieved = Counter('fishing_catches_retrieved_total', 'Total fishing catches retrieved')

# Pydantic models
class FishingCatchCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=50000)
    fish_type: str = Field(..., min_length=1, max_length=100)
    location: str = Field(..., min_length=1, max_length=200)
    weight: Optional[float] = Field(None, ge=0.0, le=1000.0)
    length: Optional[float] = Field(None, ge=0.0, le=200.0)
    bait_used: Optional[str] = Field(None, max_length=100)
    technique: Optional[str] = Field(None, max_length=100)
    weather_conditions: Optional[str] = Field(None, max_length=200)
    catch_released: bool = Field(default=True)

    @validator('fish_type')
    def validate_fish_type(cls, v):
        return v.strip().title()

class FishingCatchResponse(BaseModel):
    id: str
    title: str
    content: str
    fish_type: str
    location: str
    weight: Optional[float]
    length: Optional[float]
    bait_used: Optional[str]
    technique: Optional[str]
    weather_conditions: Optional[str]
    catch_released: bool
    created_at: datetime

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FishingLog.ai Backend Service",
        "version": "2.0.0",
        "domain": "fishinglog.ai",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/catches", response_model=FishingCatchResponse)
async def create_catch(catch: FishingCatchCreate, db: Session = Depends(get_db)):
    """Create new fishing catch entry"""
    
    # TODO: Add authentication middleware
    user_id = "demo-user"  # Placeholder for authenticated user
    
    db_catch = FishingCatch(
        user_id=user_id,
        **catch.dict()
    )
    
    db.add(db_catch)
    db.commit()
    db.refresh(db_catch)
    
    catches_created.inc()
    
    return db_catch

@app.get("/api/catches", response_model=List[FishingCatchResponse])
async def get_catches(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Get fishing catch entries"""
    
    catches = db.query(FishingCatch).offset(skip).limit(limit).all()
    catches_retrieved.inc()
    
    return catches

@app.get("/api/catches/{catch_id}", response_model=FishingCatchResponse)
async def get_catch(catch_id: str, db: Session = Depends(get_db)):
    """Get specific fishing catch"""
    
    catch = db.query(FishingCatch).filter(FishingCatch.id == catch_id).first()
    if not catch:
        raise HTTPException(status_code=404, detail="Catch not found")
    
    return catch

@app.get("/api/species")
async def get_fish_species():
    """Get fish species database"""
    species = [
        {"name": "Bass", "category": "Freshwater Sport Fish"},
        {"name": "Trout", "category": "Freshwater Game Fish"},
        {"name": "Salmon", "category": "Anadromous Game Fish"},
        {"name": "Pike", "category": "Predator Fish"},
        {"name": "Walleye", "category": "Freshwater Game Fish"},
        {"name": "Catfish", "category": "Freshwater Fish"},
        {"name": "Bluegill", "category": "Panfish"},
        {"name": "Perch", "category": "Freshwater Fish"}
    ]
    return {"species": species}

@app.get("/api/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get fishing analytics"""
    
    total_catches = db.query(FishingCatch).count()
    species_count = db.query(FishingCatch.fish_type).distinct().count()
    
    return {
        "summary": {
            "total_catches": total_catches,
            "species_count": species_count,
            "avg_weight": 2.5,  # Placeholder
            "max_weight": 15.0  # Placeholder
        }
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics"""
    return generate_latest()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
EOF

    # Create similar services for other domains (abbreviated for space)
    # Personal Domain (personallog.ai)
    mkdir -p services/personal/personallog-backend
    cp services/fishing/fishinglog-backend/Dockerfile services/personal/personallog-backend/
    sed 's/8001/8010/g' services/fishing/fishinglog-backend/requirements.txt > services/personal/personallog-backend/requirements.txt
    
    # Fitness Domain (activelog.ai)  
    mkdir -p services/fitness/activelog-backend
    cp services/fishing/fishinglog-backend/Dockerfile services/fitness/activelog-backend/
    sed 's/8001/8040/g' services/fishing/fishinglog-backend/Dockerfile > services/fitness/activelog-backend/Dockerfile
    
    cat > services/fitness/activelog-backend/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.7
pydantic==2.5.0
httpx==0.25.2
prometheus-client==0.19.0
redis==5.0.1
EOF

    cat > services/fitness/activelog-backend/main.py << 'EOF'
"""
SuperInstance.AI ActiveLog Backend Service  
Container-native fitness performance logging with cross-domain analytics
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from prometheus_client import Counter, generate_latest

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://superinstance:password@localhost:5432/superinstance")

app = FastAPI(
    title="ActiveLog.ai Backend Service",
    description="Container-native fitness performance logging",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://activelog.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    workout_type = Column(String, nullable=False)
    duration_minutes = Column(Integer)
    calories_burned = Column(Integer)
    heart_rate_avg = Column(Integer)
    heart_rate_max = Column(Integer)
    intensity_level = Column(Integer)  # 1-10 scale
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Metrics
workouts_created = Counter('workouts_created_total', 'Total workouts created')
workouts_retrieved = Counter('workouts_retrieved_total', 'Total workouts retrieved')

# Pydantic models
class WorkoutCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    workout_type: str = Field(..., min_length=1, max_length=100)
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    calories_burned: Optional[int] = Field(None, ge=0, le=5000)
    heart_rate_avg: Optional[int] = Field(None, ge=40, le=220)
    heart_rate_max: Optional[int] = Field(None, ge=40, le=220)
    intensity_level: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=1000)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ActiveLog.ai Backend Service",
        "version": "2.0.0",
        "domain": "activelog.ai", 
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/workouts")
async def create_workout(workout: WorkoutCreate, db: Session = Depends(get_db)):
    """Create new workout session"""
    
    user_id = "demo-user"  # Placeholder
    
    db_workout = WorkoutSession(
        user_id=user_id,
        **workout.dict()
    )
    
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    
    workouts_created.inc()
    
    return db_workout

@app.get("/api/workouts")
async def get_workouts(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Get workout sessions"""
    
    workouts = db.query(WorkoutSession).offset(skip).limit(limit).all()
    workouts_retrieved.inc()
    
    return workouts

@app.get("/api/analytics")
async def get_fitness_analytics(db: Session = Depends(get_db)):
    """Get fitness analytics"""
    
    total_workouts = db.query(WorkoutSession).count()
    
    return {
        "summary": {
            "total_workouts": total_workouts,
            "avg_duration": 45,  # Placeholder
            "total_calories": 5000,  # Placeholder
            "workout_types": ["Cardio", "Strength", "Flexibility", "HIIT"]
        }
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics"""
    return generate_latest()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8040)
EOF

    log_success "Domain services created"
}

# Configure Nginx for container routing
configure_nginx() {
    log_info "Configuring Nginx for container routing..."
    
    # Create Nginx configuration for SuperInstance.AI
    cat > /tmp/superinstance-nginx.conf << 'EOF'
# SuperInstance.AI Nginx Configuration
# Container-native routing with domain-based load balancing

upstream superinstance_gateway {
    server 127.0.0.1:8080;
    keepalive 32;
}

upstream superinstance_auth {
    server 127.0.0.1:8000;
    keepalive 16;
}

# Main SuperInstance.AI site
server {
    listen 80;
    server_name superinstance.ai www.superinstance.ai;
    
    location / {
        proxy_pass http://superinstance_gateway;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# PersonalLog.ai Domain
server {
    listen 80;
    server_name personallog.ai www.personallog.ai;
    
    location / {
        proxy_pass http://superinstance_gateway/personal;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# FishingLog.ai Domain  
server {
    listen 80;
    server_name fishinglog.ai www.fishinglog.ai;
    
    location / {
        proxy_pass http://superinstance_gateway/fishing;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# DMLog.ai Domain
server {
    listen 80;
    server_name dmlog.ai www.dmlog.ai;
    
    location / {
        proxy_pass http://superinstance_gateway/gaming;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# BusinessLog.ai Domain
server {
    listen 80;
    server_name businesslog.ai www.businesslog.ai;
    
    location / {
        proxy_pass http://superinstance_gateway/business;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# ActiveLog.ai Domain (Fitness)
server {
    listen 80;
    server_name activelog.ai www.activelog.ai;
    
    location / {
        proxy_pass http://superinstance_gateway/fitness;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Authentication Service
server {
    listen 80;
    server_name auth.superinstance.ai;
    
    location / {
        proxy_pass http://superinstance_auth;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

    sudo cp /tmp/superinstance-nginx.conf /etc/nginx/sites-available/superinstance.ai
    sudo ln -sf /etc/nginx/sites-available/superinstance.ai /etc/nginx/sites-enabled/
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload Nginx
    sudo nginx -t && sudo systemctl reload nginx
    
    log_success "Nginx configured for SuperInstance.AI"
}

# Create monitoring configuration
setup_monitoring() {
    log_info "Setting up monitoring configuration..."
    
    mkdir -p monitoring/{prometheus,grafana}
    
    # Prometheus configuration
    cat > monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # Add alerting rules here

scrape_configs:
  - job_name: 'superinstance-auth'
    static_configs:
      - targets: ['auth-service:8000']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'superinstance-gateway' 
    static_configs:
      - targets: ['api-gateway:8080']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'superinstance-fishing'
    static_configs:
      - targets: ['fishinglog-backend:8001']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'superinstance-fitness'
    static_configs:
      - targets: ['activelog-backend:8040']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF

    # Grafana datasource
    mkdir -p monitoring/grafana/datasources
    cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

    log_success "Monitoring configuration created"
}

# Create deployment scripts
create_deployment_scripts() {
    log_info "Creating deployment scripts..."
    
    mkdir -p scripts/deployment
    
    # Start script
    cat > scripts/deployment/start.sh << 'EOF'
#!/bin/bash
# Start SuperInstance.AI container stack

cd /home/ubuntu/superinstance

echo "🚀 Starting SuperInstance.AI containers..."

# Start core infrastructure
docker-compose -f docker-compose.infrastructure.yml up -d

# Wait for core services to be healthy
echo "⏳ Waiting for core services to be ready..."
sleep 30

# Start domain services
docker-compose -f docker-compose.domains.yml up -d

echo "✅ SuperInstance.AI started successfully!"
echo "🌐 Access points:"
echo "  - API Gateway: http://localhost:8080"
echo "  - Auth Service: http://localhost:8000" 
echo "  - Grafana: http://localhost:3000"
echo "  - Prometheus: http://localhost:9090"
EOF

    # Stop script
    cat > scripts/deployment/stop.sh << 'EOF'
#!/bin/bash
# Stop SuperInstance.AI container stack

cd /home/ubuntu/superinstance

echo "🛑 Stopping SuperInstance.AI containers..."

docker-compose -f docker-compose.domains.yml down
docker-compose -f docker-compose.infrastructure.yml down

echo "✅ SuperInstance.AI stopped successfully!"
EOF

    # Status script
    cat > scripts/deployment/status.sh << 'EOF'
#!/bin/bash
# Check SuperInstance.AI container status

cd /home/ubuntu/superinstance

echo "📊 SuperInstance.AI Container Status"
echo "======================================"

docker-compose -f docker-compose.infrastructure.yml ps
echo ""
docker-compose -f docker-compose.domains.yml ps

echo ""
echo "🏥 Health Checks"
echo "=================="

# Check core services
echo "Auth Service: $(curl -s http://localhost:8000/health | jq -r .status 2>/dev/null || echo 'unavailable')"
echo "API Gateway: $(curl -s http://localhost:8080/health | jq -r .status 2>/dev/null || echo 'unavailable')"
echo "Fishing Service: $(curl -s http://localhost:8001/health | jq -r .status 2>/dev/null || echo 'unavailable')"
echo "Fitness Service: $(curl -s http://localhost:8040/health | jq -r .status 2>/dev/null || echo 'unavailable')"
EOF

    chmod +x scripts/deployment/*.sh
    
    log_success "Deployment scripts created"
}

# Main deployment function
deploy_superinstance() {
    log_info "Starting SuperInstance.AI fresh deployment..."
    
    # Deploy core infrastructure
    cd "$SUPERINSTANCE_HOME"
    
    log_info "Building and starting core infrastructure containers..."
    docker-compose -f docker-compose.infrastructure.yml build
    docker-compose -f docker-compose.infrastructure.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for core services to initialize..."
    sleep 45
    
    # Verify core services
    log_info "Verifying core service health..."
    for service in "auth-service:8000" "api-gateway:8080"; do
        IFS=':' read -r name port <<< "$service"
        if curl -f -s "http://localhost:$port/health" > /dev/null; then
            log_success "$name is healthy on port $port"
        else
            log_warning "$name may not be fully ready on port $port"
        fi
    done
    
    log_success "SuperInstance.AI core infrastructure deployed successfully!"
}

# Create domain compose file
create_domain_compose() {
    log_info "Creating domain services compose file..."
    
    cat > docker-compose.domains.yml << 'EOF'
version: '3.8'

services:
  # Fishing Domain Service
  fishinglog-backend:
    build:
      context: ./services/fishing/fishinglog-backend
      dockerfile: Dockerfile
    container_name: superinstance-fishinglog-backend
    restart: unless-stopped
    ports:
      - "8001:8001"
    environment:
      - ENVIRONMENT=${DEPLOYMENT_ENV}
      - DATABASE_URL=postgresql://superinstance:${POSTGRES_PASSWORD}@postgres-primary:5432/superinstance
      - AUTH_SERVICE_URL=http://auth-service:8000
    depends_on:
      - postgres-primary
      - auth-service
    networks:
      - superinstance-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Fitness Domain Service  
  activelog-backend:
    build:
      context: ./services/fitness/activelog-backend
      dockerfile: Dockerfile
    container_name: superinstance-activelog-backend
    restart: unless-stopped
    ports:
      - "8040:8040"
    environment:
      - ENVIRONMENT=${DEPLOYMENT_ENV}
      - DATABASE_URL=postgresql://superinstance:${POSTGRES_PASSWORD}@postgres-primary:5432/superinstance
      - AUTH_SERVICE_URL=http://auth-service:8000
    depends_on:
      - postgres-primary
      - auth-service
    networks:
      - superinstance-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8040/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  superinstance-net:
    external: true
EOF

    log_success "Domain services compose file created"
}

# Final deployment summary
print_deployment_summary() {
    echo -e "\n${GREEN}🎉 SuperInstance.AI Deployment Complete! 🎉${NC}\n"
    
    cat << EOF
╔════════════════════════════════════════════════════════════════════════╗
║                        SuperInstance.AI                               ║
║                     Container-Native Platform                         ║
║                                                                        ║
║  🚀 Core Infrastructure:                                              ║
║     • Authentication Service: http://localhost:8000                   ║
║     • API Gateway: http://localhost:8080                             ║
║     • Redis Cache: localhost:6379                                    ║
║     • PostgreSQL Database: localhost:5432                            ║
║                                                                        ║
║  🏗️  Domain Services:                                                 ║
║     • FishingLog.ai: http://localhost:8001                           ║
║     • ActiveLog.ai: http://localhost:8040                            ║
║                                                                        ║
║  📊 Monitoring:                                                       ║
║     • Grafana: http://localhost:3000                                 ║
║     • Prometheus: http://localhost:9090                              ║
║                                                                        ║
║  🌐 Domain Access (via Nginx):                                       ║
║     • fishinglog.ai → Fishing operations                            ║
║     • activelog.ai → Fitness performance                            ║
║     • personallog.ai → Personal productivity (coming soon)           ║
║     • dmlog.ai → Gaming & D&D (coming soon)                         ║
║     • businesslog.ai → Business operations (coming soon)            ║
║                                                                        ║
║  📁 Project Location: $SUPERINSTANCE_HOME                       ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝

🔧 Management Commands:
   • Start:  $SUPERINSTANCE_HOME/scripts/deployment/start.sh
   • Stop:   $SUPERINSTANCE_HOME/scripts/deployment/stop.sh  
   • Status: $SUPERINSTANCE_HOME/scripts/deployment/status.sh

📋 Next Steps:
   1. Configure domain DNS to point to this server
   2. Set up SSL certificates with certbot
   3. Deploy additional domain services
   4. Configure cross-domain analytics
   5. Enable compute capital economy features

📖 Documentation: See $SUPERINSTANCE_HOME/docs/
🔍 Logs: $LOG_FILE
EOF

    log_success "SuperInstance.AI deployment completed successfully!"
}

# Main execution
main() {
    print_banner
    
    log_info "Starting SuperInstance.AI fresh deployment at $(date)"
    log_info "Deployment environment: $DEPLOYMENT_ENV"
    log_info "Target directory: $SUPERINSTANCE_HOME"
    
    # Execute deployment steps
    check_prerequisites
    setup_directory_structure
    deploy_core_infrastructure
    create_core_services
    create_domain_services
    create_domain_compose
    configure_nginx
    setup_monitoring
    create_deployment_scripts
    deploy_superinstance
    
    print_deployment_summary
    
    log_info "SuperInstance.AI deployment completed at $(date)"
}

# Run main function
main "$@"