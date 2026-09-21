# Developer Documentation

Welcome to the ActiveLog developer documentation! This section contains everything you need to contribute to ActiveLog, extend its functionality, or integrate it into your systems.

## Quick Start for Developers

### Prerequisites Checklist
- [ ] **Docker & Docker Compose** (v20.10+ recommended)
- [ ] **Python 3.9+** with pip and virtualenv
- [ ] **Node.js 18+** with npm/yarn
- [ ] **Git** with SSH keys configured
- [ ] **PostgreSQL** client tools (psql)
- [ ] **Redis** client tools (redis-cli)

### 5-Minute Setup
```bash
# Clone the repository
git clone git@github.com:activelog/activelog.git
cd activelog

# Run the setup script
./scripts/dev-setup.sh

# Start all services
docker-compose up -d

# Verify everything is running
./scripts/health-check.sh
```

🎉 **Success!** ActiveLog should now be running at http://localhost:3000

## Documentation Structure

### For New Developers
- [**Developer Onboarding**](./onboarding.md) - Complete setup guide
- [**Architecture Overview**](./architecture-overview.md) - System design principles
- [**Development Workflow**](./workflow.md) - Git flow, testing, deployment
- [**Environment Setup**](./environment-setup.md) - Local development environment

### Core Development
- [**Backend Development**](./backend/README.md) - FastAPI services and APIs
- [**Frontend Development**](./frontend/README.md) - React/TypeScript components
- [**Database Development**](./database/README.md) - Schema, migrations, optimization
- [**AI/ML Development**](./ml/README.md) - Machine learning pipelines

### Advanced Topics
- [**Microservices Guide**](./microservices/README.md) - Service architecture patterns
- [**Performance Optimization**](./performance/README.md) - Scaling and optimization
- [**Security Guidelines**](./security/README.md) - Secure development practices
- [**Testing Strategies**](./testing/README.md) - Unit, integration, and E2E testing

### Integration & Extensions
- [**Plugin Development**](./plugins/README.md) - Create custom plugins
- [**API Integration**](./api/README.md) - Integrate with external systems
- [**Webhook Development**](./webhooks/README.md) - Event-driven integrations
- [**SDK Development**](./sdks/README.md) - Client library development

### Operations & Deployment
- [**Deployment Guide**](./deployment/README.md) - Production deployment strategies
- [**Monitoring & Observability**](./monitoring/README.md) - Metrics, logs, traces
- [**DevOps Practices**](./devops/README.md) - CI/CD, infrastructure as code
- [**Troubleshooting**](./troubleshooting/README.md) - Debug common issues

## Development Stack

### Backend Technologies
- **Language**: Python 3.9+
- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL 14+ with asyncpg
- **Cache**: Redis 7+ with async redis-py
- **Message Queue**: RabbitMQ with Celery
- **Search**: Elasticsearch 8+
- **Vector DB**: Pinecone/Weaviate for embeddings
- **Storage**: MinIO (S3-compatible) + cloud storage

### Frontend Technologies  
- **Language**: TypeScript 5+
- **Framework**: React 18+ with hooks
- **Build Tool**: Vite for fast development
- **State Management**: Zustand + React Query
- **UI Library**: Custom components + Tailwind CSS
- **Mobile**: React Native with Expo

### AI/ML Technologies
- **Framework**: PyTorch 2+ and Transformers
- **Models**: Sentence transformers, OpenAI GPT
- **Vector Search**: FAISS, Pinecone, Weaviate
- **Computer Vision**: OpenCV, PIL, scikit-image
- **NLP**: spaCy, NLTK, Hugging Face transformers

### Infrastructure & DevOps
- **Containers**: Docker + Docker Compose
- **Orchestration**: Kubernetes (production)
- **Service Mesh**: Istio for microservices
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger for distributed tracing
- **CI/CD**: GitHub Actions + ArgoCD

## Code Quality Standards

### Python Code Style
```python
# Use Black for formatting
black --line-length 88 src/

# Use isort for imports
isort src/ --profile black

# Use mypy for type checking
mypy src/ --strict

# Use pylint for linting
pylint src/ --rcfile=.pylintrc
```

### TypeScript Code Style
```bash
# Use Prettier for formatting
prettier --write "src/**/*.{ts,tsx}"

# Use ESLint for linting
eslint "src/**/*.{ts,tsx}" --fix

# Use TypeScript compiler for type checking
tsc --noEmit
```

### Git Commit Standards
We follow [Conventional Commits](https://conventionalcommits.org/):

```bash
# Format: type(scope): description
feat(auth): add OAuth2 integration
fix(search): resolve indexing performance issue
docs(api): update authentication examples
test(backend): add integration tests for file service
chore(deps): update FastAPI to v0.104.1
```

### Code Review Process
1. **Create Feature Branch**: `git checkout -b feature/your-feature-name`
2. **Write Tests**: Ensure >80% code coverage
3. **Update Documentation**: Keep docs in sync with code
4. **Create Pull Request**: Use PR template
5. **Code Review**: Minimum 2 approvals required
6. **Automated Checks**: All CI/CD checks must pass
7. **Merge**: Squash and merge to main

## Testing Strategy

### Test Pyramid
```
    /\
   /E2E\     ← Few, but critical user journeys
  /____\
 /      \
/  UNIT  \   ← Many, fast, isolated tests
\________/
```

### Testing Commands
```bash
# Backend tests
pytest tests/ -v --cov=src/ --cov-report=html

# Frontend tests  
npm test -- --coverage --watchAll=false

# Integration tests
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# E2E tests
npm run test:e2e

# Load tests
locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 5m
```

## Performance Guidelines

### Backend Performance
- **Response Time**: < 200ms for 95th percentile
- **Throughput**: > 1000 RPS per service instance
- **Memory Usage**: < 512MB per service instance
- **Database**: < 100ms query time for 95th percentile

### Frontend Performance
- **First Contentful Paint**: < 1.5s
- **Largest Contentful Paint**: < 2.5s
- **Cumulative Layout Shift**: < 0.1
- **Bundle Size**: < 500KB gzipped for main bundle

### Monitoring & Alerting
- **Uptime**: 99.9% SLA target
- **Error Rate**: < 0.1% for user-facing operations
- **Database Connections**: Monitor pool utilization
- **Queue Depth**: Monitor message queue backlogs

## Security Guidelines

### Authentication & Authorization
- All endpoints require authentication except health checks
- Use JWT tokens with short expiration (15 minutes)
- Implement refresh tokens for session management
- Role-based access control (RBAC) for all resources

### Data Protection
- Encrypt all PII using AES-256
- Hash passwords using bcrypt with salt
- Use HTTPS/TLS 1.3 for all communications
- Implement rate limiting on all public endpoints

### Secure Coding Practices
```python
# ✅ Good: Use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# ❌ Bad: SQL injection vulnerability
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ Good: Validate input
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    email: str
    password: str
    
    @validator('email')
    def email_must_be_valid(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
```

## Contributing Guidelines

### Before You Start
1. **Check Existing Issues**: Look for related work
2. **Create Issue**: Describe your proposed changes
3. **Discuss Approach**: Get feedback from maintainers
4. **Fork Repository**: Work in your own fork
5. **Follow Standards**: Use our coding standards

### Pull Request Checklist
- [ ] Tests added/updated with >80% coverage
- [ ] Documentation updated
- [ ] Changelog entry added
- [ ] Breaking changes documented
- [ ] All CI checks passing
- [ ] Code reviewed by team members

### Getting Help

**Developer Channels**:
- 💬 **Discord**: [discord.gg/activelog-dev](https://discord.gg/activelog-dev)
- 📧 **Email**: dev-support@activelog.com
- 📋 **GitHub Issues**: For bugs and feature requests
- 📚 **Wiki**: [github.com/activelog/activelog/wiki](https://github.com/activelog/activelog/wiki)

**Office Hours**: 
- **When**: Tuesdays 2-4 PM PT, Fridays 9-11 AM PT
- **Where**: Discord voice channel
- **What**: Live Q&A with core developers

## Release Process

### Version Strategy
We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)  
- **PATCH**: Bug fixes (backward compatible)

### Release Schedule
- **Major Releases**: Every 6 months
- **Minor Releases**: Monthly (first Tuesday)
- **Patch Releases**: As needed (critical bugs)
- **Hotfixes**: Emergency releases

### Release Checklist
1. **Version Bump**: Update version in all package files
2. **Changelog**: Update CHANGELOG.md with new features/fixes
3. **Documentation**: Ensure docs are up to date
4. **Testing**: Full test suite passes
5. **Security Scan**: Vulnerability assessment
6. **Performance Test**: Load testing on staging
7. **Deployment**: Deploy to staging → production
8. **Monitoring**: Monitor metrics post-deployment

## Development Resources

### Useful Commands
```bash
# Start development environment
make dev-start

# Run all tests
make test

# Build production images
make build

# Deploy to staging
make deploy-staging

# View logs
make logs service=auth-service

# Database migration
make migrate

# Reset development database
make db-reset
```

### IDE Configuration

**VS Code Extensions** (recommended):
- Python extension pack
- TypeScript and JavaScript
- Docker
- GitLens
- REST Client
- Thunder Client (API testing)

**VS Code Settings** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true,
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

### Database Access
```bash
# Connect to development database
psql postgresql://dev:dev@localhost:5432/activelog_dev

# Connect to Redis
redis-cli -h localhost -p 6379

# View Elasticsearch indices
curl http://localhost:9200/_cat/indices?v

# MinIO web console
open http://localhost:9001
```

## API Development

### OpenAPI Standards
- All APIs must have OpenAPI 3.0 specifications
- Use Pydantic models for request/response validation
- Include comprehensive examples in documentation
- Follow RESTful conventions

### API Versioning
```python
# Include version in URL path
@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str):
    pass

# Support multiple versions
@app.get("/api/v2/users/{user_id}")
async def get_user_v2(user_id: str):
    pass
```

### Error Handling
```python
from fastapi import HTTPException
from enum import Enum

class ErrorCode(str, Enum):
    USER_NOT_FOUND = "USER_NOT_FOUND"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.USER_NOT_FOUND,
                "message": "User not found",
                "user_id": user_id
            }
        )
    return user
```

## Next Steps

Ready to contribute? Here's what to do next:

1. **🚀 [Complete Onboarding](./onboarding.md)** - Set up your development environment
2. **🎯 [Pick First Issue](https://github.com/activelog/activelog/labels/good%20first%20issue)** - Find beginner-friendly tasks  
3. **📚 [Read Architecture Guide](./architecture-overview.md)** - Understand system design
4. **🔧 [Set Up IDE](./environment-setup.md#ide-setup)** - Configure your development tools
5. **🧪 [Run Tests](./testing/README.md)** - Ensure everything works
6. **💬 [Join Community](https://discord.gg/activelog-dev)** - Connect with other developers

**Welcome to the ActiveLog development team!** 🎉

---

*This documentation is maintained by the ActiveLog development team. For improvements or corrections, please [open an issue](https://github.com/activelog/activelog/issues) or submit a pull request.*