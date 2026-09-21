# Developer Onboarding Guide

Welcome to the ActiveLog development team! This guide will get you up and running with a complete development environment in under 30 minutes.

## Pre-Onboarding Checklist

Before starting, ensure you have:
- [ ] **GitHub Account** - With SSH keys configured
- [ ] **Docker Desktop** - Running and functional
- [ ] **Code Editor** - VS Code recommended
- [ ] **Terminal Access** - Command line interface
- [ ] **Git Configuration** - Name and email set

## Step 1: System Requirements

### Minimum Requirements
- **OS**: macOS 10.15+, Ubuntu 20.04+, Windows 10+ with WSL2
- **RAM**: 16GB (8GB minimum, but not recommended)
- **Storage**: 50GB free space
- **Network**: Stable internet for initial setup

### Required Software

**Docker & Docker Compose**
```bash
# macOS (using Homebrew)
brew install --cask docker

# Ubuntu/Debian
sudo apt update && sudo apt install docker.io docker-compose

# Windows: Download Docker Desktop from docker.com
```

**Python 3.9+**
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian  
sudo apt install python3.11 python3.11-venv python3-pip

# Windows (WSL2)
sudo apt update && sudo apt install python3.11 python3-pip
```

**Node.js 18+**
```bash
# Using Node Version Manager (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

# Or via package manager
# macOS: brew install node@18
# Ubuntu: sudo apt install nodejs npm
```

**Additional Tools**
```bash
# PostgreSQL client
# macOS: brew install postgresql
# Ubuntu: sudo apt install postgresql-client

# Redis client
# macOS: brew install redis
# Ubuntu: sudo apt install redis-tools

# Git (if not already installed)
# macOS: brew install git
# Ubuntu: sudo apt install git
```

## Step 2: Repository Setup

### Clone Repository
```bash
# Clone with SSH (recommended)
git clone git@github.com:activelog/activelog.git
cd activelog

# Or clone with HTTPS
git clone https://github.com/activelog/activelog.git
cd activelog
```

### Verify Repository Structure
```bash
ls -la
# You should see:
# - docker-compose.yml
# - services/
# - frontend/
# - docs/
# - scripts/
# - README.md
```

### Set Up Git Configuration
```bash
# Configure Git for this project
git config user.name "Your Name"
git config user.email "your.email@company.com"

# Set up pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

## Step 3: Environment Configuration

### Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit environment variables
nano .env  # or use your preferred editor
```

**Key Variables to Configure**:
```bash
# Database Configuration
POSTGRES_DB=activelog_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password_change_me

# Redis Configuration  
REDIS_URL=redis://localhost:6379/0

# MinIO/S3 Configuration
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=minio_password_change_me
MINIO_BUCKET_NAME=activelog-dev

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# External API Keys (optional for development)
OPENAI_API_KEY=your_openai_key_here
GOOGLE_CLOUD_API_KEY=your_google_key_here

# Development Settings
DEBUG=true
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### Docker Configuration
```bash
# Verify Docker is running
docker --version
docker-compose --version

# Pull base images (optional - speeds up first build)
docker-compose pull
```

## Step 4: Quick Start Script

We provide an automated setup script for faster onboarding:

```bash
# Make script executable
chmod +x scripts/dev-setup.sh

# Run setup script
./scripts/dev-setup.sh
```

The script will:
1. ✅ Check system requirements
2. 🔧 Install Python and Node.js dependencies
3. 🐳 Build Docker images
4. 🗄️ Set up databases and run migrations
5. 🌱 Seed development data
6. 🚀 Start all services
7. ✔️ Run health checks

**Expected Output**:
```
🚀 ActiveLog Development Environment Setup
==========================================

✅ System requirements check passed
✅ Docker services started
✅ Database migrations completed
✅ Development data seeded
✅ All services healthy

🎉 Setup complete! ActiveLog is running at:
   Web App:     http://localhost:3000
   API Gateway: http://localhost:8000
   API Docs:    http://localhost:8000/docs
   
🔧 Development tools:
   pgAdmin:     http://localhost:8080
   MinIO:       http://localhost:9001
   Grafana:     http://localhost:3001
```

## Step 5: Manual Setup (Alternative)

If the script fails or you prefer manual setup:

### Backend Setup
```bash
# Create Python virtual environment
cd services/
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements-dev.txt

# Install additional development tools
pip install black isort mypy pylint pytest-cov
```

### Frontend Setup
```bash
# Install Node.js dependencies
cd frontend/
npm install

# Install development dependencies
npm install --save-dev @types/react @types/node eslint prettier
```

### Database Setup
```bash
# Start database services
docker-compose up -d postgres redis minio elasticsearch

# Wait for services to be ready (about 30 seconds)
sleep 30

# Run database migrations
cd services/
python manage.py migrate

# Seed development data
python manage.py seed_dev_data
```

### Start Services
```bash
# Start all services in development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Step 6: Verify Installation

### Health Check Script
```bash
./scripts/health-check.sh
```

**Expected Output**:
```
🏥 ActiveLog Health Check
========================

✅ API Gateway (http://localhost:8000) - Healthy
✅ Auth Service (http://localhost:8001) - Healthy  
✅ Metadata Service (http://localhost:8002) - Healthy
✅ Analytics Service (http://localhost:8003) - Healthy
✅ Notification Service (http://localhost:8004) - Healthy
✅ PostgreSQL Database - Connected
✅ Redis Cache - Connected
✅ Elasticsearch - Healthy
✅ MinIO Storage - Healthy

🎉 All services are running correctly!
```

### Manual Verification
Test key endpoints:

```bash
# Test API Gateway
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "api-gateway"}

# Test authentication
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "dev@activelog.com", "password": "devpassword"}'

# Test file upload (after getting auth token)
curl -X POST http://localhost:8002/metadata \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "test-123", "filename": "test.txt"}'
```

### Web Interface Check
1. Open http://localhost:3000 in your browser
2. Log in with development credentials:
   - **Username**: `dev@activelog.com`
   - **Password**: `devpassword`
3. Upload a test file
4. Verify file appears in the interface

## Step 7: Development Workflow Setup

### IDE Configuration (VS Code)

**Install Recommended Extensions**:
```bash
# Open VS Code in project directory
code .

# Install extensions from command palette (Ctrl/Cmd + Shift + P)
# Type: "Extensions: Show Recommended Extensions"
# Install all workspace recommendations
```

**Key Extensions**:
- Python Extension Pack
- TypeScript and JavaScript Language Features
- Docker Extension
- GitLens — Git supercharged
- REST Client
- Prettier - Code formatter
- ESLint

### Git Hooks Setup
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Test hooks
pre-commit run --all-files
```

### Code Quality Tools
```bash
# Backend code formatting
cd services/
black --check src/
isort --check-only src/
mypy src/
pylint src/

# Frontend code formatting  
cd frontend/
npm run lint
npm run type-check
npm run format:check
```

## Step 8: Development Commands

### Essential Commands
```bash
# Start all services
make dev-start
# or: docker-compose up

# Stop all services
make dev-stop
# or: docker-compose down

# View logs
make logs
# or: docker-compose logs -f

# Restart specific service
docker-compose restart auth-service

# Rebuild service after code changes
docker-compose up --build auth-service
```

### Testing Commands
```bash
# Run backend tests
cd services/
pytest tests/ -v --cov

# Run frontend tests
cd frontend/
npm test

# Run integration tests  
make test-integration

# Run all tests
make test-all
```

### Database Commands
```bash
# Access PostgreSQL
psql postgresql://dev_user:dev_password_change_me@localhost:5432/activelog_dev

# Run migrations
python services/manage.py migrate

# Create new migration
python services/manage.py makemigrations

# Reset database (development only!)
make db-reset
```

## Step 9: First Development Task

Now that your environment is set up, let's complete a simple task to verify everything works:

### Task: Add a New API Endpoint

1. **Create a new endpoint** in `services/metadata/routes.py`:
```python
@router.get("/hello")
async def hello_world():
    return {"message": "Hello from ActiveLog!", "timestamp": datetime.utcnow()}
```

2. **Test the endpoint**:
```bash
curl http://localhost:8002/metadata/hello
```

3. **Write a test** in `services/metadata/tests/test_routes.py`:
```python
def test_hello_endpoint():
    response = client.get("/metadata/hello")
    assert response.status_code == 200
    assert "message" in response.json()
```

4. **Run the test**:
```bash
cd services/metadata/
pytest tests/test_routes.py::test_hello_endpoint -v
```

5. **Commit your changes**:
```bash
git add .
git commit -m "feat(metadata): add hello world endpoint"
```

✅ **Success!** You've successfully made your first change to ActiveLog.

## Troubleshooting Common Issues

### Docker Issues

**Docker not starting**:
```bash
# Check Docker daemon
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Check available resources
docker system df
docker system prune  # Clean up if needed
```

**Port conflicts**:
```bash
# Check what's using a port
lsof -i :8000  # or any other port
netstat -tulpn | grep :8000

# Stop conflicting processes or change ports in docker-compose.yml
```

### Database Issues

**Connection refused**:
```bash
# Check if PostgreSQL container is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

**Migration errors**:
```bash
# Drop and recreate database (development only!)
docker-compose down
docker volume rm activelog_postgres_data
docker-compose up -d postgres
sleep 10
python services/manage.py migrate
```

### Python Issues

**Import errors**:
```bash
# Ensure virtual environment is activated
source services/venv/bin/activate

# Reinstall dependencies
pip install -r services/requirements-dev.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

**Package conflicts**:
```bash
# Reset virtual environment
rm -rf services/venv/
cd services/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### Node.js Issues

**NPM install failures**:
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf frontend/node_modules/
rm frontend/package-lock.json
cd frontend/
npm install
```

**Version conflicts**:
```bash
# Check Node version
node --version  # Should be 18+

# Use correct Node version
nvm use 18
npm install
```

## Getting Help

### Internal Resources
- **Documentation**: You're reading it! 📚
- **Code Comments**: Look for inline documentation
- **README Files**: Each service has its own README
- **Architecture Docs**: See `docs/architecture/`

### Team Communication
- **Slack**: #activelog-dev channel
- **Email**: dev-team@activelog.com  
- **Office Hours**: Tuesdays 2-4 PM PT, Fridays 9-11 AM PT
- **Team Meeting**: Mondays 10 AM PT (standup)

### External Resources
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **Docker Docs**: https://docs.docker.com/
- **PostgreSQL Docs**: https://postgresql.org/docs/

### Issue Reporting
If you encounter issues during onboarding:

1. **Check Known Issues**: See `docs/troubleshooting/`
2. **Search Existing Issues**: GitHub issues tab
3. **Create New Issue**: Use issue template
4. **Ask in Slack**: #help channel for quick questions

## Next Steps

Congratulations! 🎉 You've successfully set up your ActiveLog development environment. Here's what to do next:

### Week 1: Familiarization
- [ ] **Explore Codebase**: Spend time understanding the structure
- [ ] **Read Architecture Docs**: Understand system design
- [ ] **Complete First Task**: Pick a "good first issue"
- [ ] **Attend Team Meetings**: Introduce yourself
- [ ] **Set Up Monitoring**: Install development tools

### Week 2: First Contribution
- [ ] **Choose Feature**: Pick something to work on
- [ ] **Write Tests**: TDD approach preferred
- [ ] **Create PR**: Follow contribution guidelines
- [ ] **Code Review**: Learn from feedback
- [ ] **Documentation**: Update relevant docs

### Month 1: Deeper Involvement
- [ ] **Own a Service**: Become expert in one microservice
- [ ] **Mentor Others**: Help with onboarding
- [ ] **Improve Tooling**: Contribute to developer experience
- [ ] **Architecture Discussion**: Participate in design decisions

### Resources for Continued Learning
- **Internal Wiki**: Advanced development patterns
- **Tech Talks**: Weekly presentations on architecture
- **Code Review**: Learn from senior developers
- **Pair Programming**: Collaborate on complex features

---

**Welcome to the team!** 👋 

If you have any questions during your onboarding journey, don't hesitate to reach out. We're here to help you succeed and contribute to ActiveLog's mission of intelligent file management.

*Happy coding!* 🚀

---

*This guide is actively maintained. If you find any issues or have suggestions for improvement, please [create an issue](https://github.com/activelog/activelog/issues) or submit a pull request.*