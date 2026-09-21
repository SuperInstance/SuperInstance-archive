# CORE-001: ActiveLog System Overview

**Type:** Architecture Overview  
**Complexity:** Medium  
**Dependencies:** None (root concept)  
**Last Updated:** 2025-08-26  

## Simple View (50 tokens)
ActiveLog: 70+ Python microservices ecosystem for productivity/logging with React frontends, FastAPI APIs, Docker containerization.

## Advanced View (200 tokens)
ActiveLog is a comprehensive microservices ecosystem consisting of:
- **70+ Services**: FastAPI-based Python services, each with isolated databases
- **Frontend Systems**: Multiple React applications (main app, DMLog game system)
- **Architecture**: Service-oriented with API gateway, authentication, monitoring
- **Tech Stack**: Python 3.9+, FastAPI, SQLite/PostgreSQL, Redis, Docker, React 18
- **Deployment**: Docker-compose orchestration, health monitoring, service discovery
- **Purpose**: Productivity tools, logging systems, business applications, AI integration

## Full Documentation
ActiveLog represents a large-scale microservices architecture designed for maximum modularity and scalability. The system originated as a logging and productivity platform but has evolved into a comprehensive business application suite.

### Key Architectural Decisions
1. **Service Isolation**: Each service maintains its own database and API
2. **Standardized Patterns**: Consistent structure across all services (main.py, routes, models)
3. **Technology Consistency**: Python/FastAPI for backend, React for frontend
4. **Development Efficiency**: Automated service generation and deployment tools

### Service Categories
- **Core Services**: Authentication, API gateway, data export, metadata
- **Business Services**: Accounting, invoicing, market analysis, revenue tracking
- **AI Services**: Bot ecosystem, ML pipeline, content generation
- **Gaming Services**: DMLog D&D campaign management system
- **Infrastructure**: Monitoring, backup, deployment, health checks

### Development Workflow
1. Service generation via CLI tools
2. Standardized testing and validation
3. Docker containerization
4. Health check integration
5. Automated deployment

### Integration Points
- **Authentication**: Central JWT-based auth service
- **API Gateway**: Request routing and load balancing
- **Monitoring**: Health checks and performance tracking
- **Data Flow**: Cross-service data export and synchronization

### Scalability Patterns
- Horizontal service scaling
- Database sharding strategies
- Caching layers (Redis)
- Load balancing and failover

## Related Concepts
- **SVC-001**: Standard service template pattern
- **TECH-001**: Technology stack details
- **STRUCT-001**: Project structure organization
- **AUTH-001**: Authentication architecture
- **MON-001**: Monitoring and health check systems

## Code References
- Main project: `~/activelog/`
- Service directory: `~/activelog/services/`
- Frontend apps: `~/activelog/frontend*/`
- Development tools: `~/activelog/dev-tools/`

## Recent Changes
- Added bot-ecosystem service with ML routing
- Enhanced security middleware
- Implemented streaming capabilities
- Upgraded to React 18 across frontends