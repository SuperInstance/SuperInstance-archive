# ActiveLog Architecture Documentation

This directory contains comprehensive architecture documentation for the ActiveLog system, including high-level system overview, service interactions, data flow, and deployment architectures.

## Architecture Diagrams

All diagrams are created using Mermaid syntax for easy maintenance and version control.

### System Overview
- [High-Level Architecture](./high-level-architecture.md) - Overall system architecture
- [Service Map](./service-map.md) - Complete service topology
- [Data Flow](./data-flow.md) - Data movement through the system

### Service Architecture
- [Microservices Architecture](./microservices.md) - Service decomposition and boundaries
- [API Gateway Pattern](./api-gateway.md) - Request routing and aggregation
- [Event-Driven Architecture](./event-driven.md) - Asynchronous messaging and events

### Data Architecture
- [Database Schema](./database-schema.md) - Database design and relationships
- [Storage Architecture](./storage.md) - File storage and content delivery
- [Caching Strategy](./caching.md) - Multi-level caching architecture

### Infrastructure
- [Deployment Architecture](./deployment.md) - Container orchestration and infrastructure
- [Network Architecture](./network.md) - Service mesh and load balancing
- [Security Architecture](./security.md) - Authentication, authorization, and data protection

### Integration Patterns
- [Message Queues](./message-queues.md) - Asynchronous processing patterns
- [Webhook Architecture](./webhooks.md) - External integrations and callbacks
- [Plugin System](./plugins.md) - Extensibility and third-party integrations

## Viewing Diagrams

### Online Viewers
- [Mermaid Live Editor](https://mermaid.live/) - Copy and paste diagrams
- [GitHub/GitLab](https://github.com) - Native Mermaid rendering

### Local Tools
- VS Code Mermaid Preview extension
- Mermaid CLI: `npm install -g @mermaid-js/mermaid-cli`

### Generate Images
```bash
# Install mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Generate PNG from mermaid file
mmdc -i diagram.md -o diagram.png

# Generate SVG
mmdc -i diagram.md -o diagram.svg -f svg
```

## Diagram Standards

### Colors
- **Blue (#2196F3)**: Core services
- **Green (#4CAF50)**: External systems
- **Orange (#FF9800)**: Processing services  
- **Purple (#9C27B0)**: Storage systems
- **Red (#F44336)**: Security/Auth components

### Symbols
- `[Service]`: Internal service
- `((API))`: API endpoint
- `{Database}`: Database
- `<Storage>`: File storage
- `-->`: Synchronous call
- `-.-`: Asynchronous message
- `==`: Data flow

### Naming Conventions
- Services: PascalCase (UserService)
- APIs: kebab-case (user-api)
- Databases: lowercase (userdb)
- External systems: UPPERCASE (AWS_S3)

## Architecture Decisions

See [Architecture Decision Records (ADRs)](../decisions/) for detailed reasoning behind architectural choices:

- [ADR-001: Microservices Architecture](../decisions/001-microservices.md)
- [ADR-002: Event-Driven Communication](../decisions/002-event-driven.md)
- [ADR-003: Database Per Service](../decisions/003-database-per-service.md)
- [ADR-004: API Gateway Pattern](../decisions/004-api-gateway.md)

## Diagrams Index

| Diagram | Description | Complexity |
|---------|-------------|------------|
| [System Overview](./high-level-architecture.md) | 10,000-foot view | Simple |
| [Service Interactions](./microservices.md) | Service-to-service calls | Medium |
| [Data Flow](./data-flow.md) | Information flow paths | Complex |
| [Deployment](./deployment.md) | Infrastructure layout | Medium |
| [Security](./security.md) | Auth and security boundaries | Complex |

## Contributing

When adding new diagrams:

1. Follow the naming conventions
2. Use consistent colors and symbols
3. Add descriptions and context
4. Update this README index
5. Generate PNG/SVG versions for presentations

## Tools and Resources

- [Mermaid Documentation](https://mermaid-js.github.io/mermaid/)
- [Diagram Types](https://mermaid-js.github.io/mermaid/#/README?id=diagram-types)
- [Architecture Patterns](https://microservices.io/patterns/)
- [C4 Model](https://c4model.com/) for software architecture