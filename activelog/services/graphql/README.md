# ActiveLog GraphQL Service

A comprehensive GraphQL API for the ActiveLog platform, built with Apollo Server and supporting real-time subscriptions, schema stitching, DataLoader optimization, and advanced features.

## Features

- 🚀 **Apollo Server 4** with Express integration
- 📊 **Comprehensive Schema** covering all ActiveLog entities
- 🔄 **Real-time Subscriptions** via WebSocket with Redis PubSub
- 🔗 **Schema Stitching** for microservices architecture
- ⚡ **DataLoader** for N+1 query optimization
- 🎮 **GraphQL Playground** for interactive development
- 📈 **Query Complexity Analysis** with role-based limits
- 🛡️ **Rate Limiting** per query complexity and user role
- 💾 **Redis Caching** with automatic invalidation
- 📝 **Comprehensive Logging** and monitoring
- 🔐 **JWT Authentication** with role-based permissions
- 🏗️ **Federation Support** for distributed schemas

## Quick Start

### Prerequisites

- Node.js 18+ 
- Redis 6+
- PostgreSQL 14+ (for data sources)

### Installation

```bash
# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env

# Edit environment variables
nano .env

# Start development server
npm run dev

# Or start production server
npm run build
npm start
```

### Docker Setup

```bash
# Start Redis and PostgreSQL
docker-compose up -d redis postgres

# Start the GraphQL service
npm run dev
```

## API Endpoints

- **GraphQL Endpoint**: `http://localhost:8010/graphql`
- **GraphQL Playground**: `http://localhost:8010/graphql` (development)
- **Subscriptions**: `ws://localhost:8010/graphql`
- **Health Check**: `http://localhost:8010/health`
- **Ready Check**: `http://localhost:8010/ready`

## Schema Overview

The GraphQL schema includes comprehensive types for:

### Core Entities
- **Users** - Authentication, profiles, preferences
- **Files** - Upload, sharing, folder management
- **Videos** - Processing, transcoding, analysis
- **Organizations** - Teams, billing, member management
- **Plugins** - Marketplace, installation, execution

### Advanced Features
- **Analytics** - Dashboards, metrics, real-time data
- **Notifications** - Multi-channel delivery system
- **Subscriptions** - Billing and usage management

## Real-time Subscriptions

WebSocket subscriptions for live updates:

```graphql
subscription {
  fileUploaded(userId: "user123") {
    id
    filename
    status
  }
}

subscription {
  notificationReceived(userId: "user123") {
    id
    title
    message
    type
  }
}
```

## DataLoader Optimization

Automatic batching and caching for:
- User lookups
- File relationships
- Organization members
- Permission checks
- Usage metrics

## Query Complexity & Rate Limiting

Queries are analyzed for complexity with role-based limits:
- **Users**: 1000 complexity units
- **Admins**: 5000 complexity units
- Rate limiting per user/IP with Redis

## Caching Strategy

Multi-layer caching with Redis:
- Query result caching
- DataLoader caching
- User session caching
- Automatic invalidation

## Schema Stitching

Support for microservices architecture:
- Gateway mode for distributed schemas
- Service federation with Apollo
- Cross-service type resolution

## Development

### Available Scripts

```bash
# Development with hot reload
npm run dev

# Build TypeScript
npm run build

# Start production server
npm start

# Type checking
npm run type-check

# Linting
npm run lint

# Testing
npm test

# Generate schema documentation
npm run schema:docs
```

### Project Structure

```
src/
├── schema/           # GraphQL type definitions
├── resolvers/        # Query/mutation/subscription resolvers  
├── dataloaders/      # DataLoader implementations
├── middleware/       # Authentication middleware
├── plugins/          # Apollo Server plugins
├── types/           # TypeScript type definitions
└── server.ts        # Main server file
```

## Configuration

### Environment Variables

Key configuration options:

- `PORT` - Server port (default: 8010)
- `USE_GATEWAY` - Enable schema stitching
- `JWT_SECRET` - JWT signing secret
- `REDIS_HOST/PORT` - Redis connection
- `RATE_LIMIT_MAX` - Requests per window
- `ENABLE_PLAYGROUND` - GraphQL Playground

### Schema Directives

Custom directives for cross-cutting concerns:

```graphql
type Query {
  # Require authentication
  me: User! @auth(requires: USER)
  
  # Rate limiting
  files: [File!]! @rateLimit(max: 50, window: 60)
  
  # Query complexity
  analytics: Analytics @complexity(value: 10)
  
  # Caching
  publicFiles: [File!]! @cache(ttl: 300)
}
```

## Monitoring

Built-in monitoring and observability:

- Request/response logging
- Performance metrics
- Error tracking
- Cache hit rates
- Query complexity analysis

## Security

Security features implemented:

- JWT-based authentication
- Role-based authorization
- Query complexity limiting
- Rate limiting per user/IP
- Input validation
- CORS protection
- Helmet security headers

## Performance

Optimization strategies:

- DataLoader for N+1 prevention
- Redis caching at multiple layers
- Query complexity analysis
- Pagination for large datasets
- Field-level caching
- Connection pooling

## Production Deployment

For production deployment:

1. Set `NODE_ENV=production`
2. Configure Redis cluster
3. Set strong `JWT_SECRET`
4. Configure monitoring endpoints
5. Set up log aggregation
6. Configure CORS for your domain
7. Set appropriate rate limits

## Contributing

1. Follow TypeScript best practices
2. Add tests for new resolvers
3. Update schema documentation
4. Follow conventional commits
5. Ensure all checks pass

## License

MIT License - see LICENSE file for details