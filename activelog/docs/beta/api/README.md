# API Documentation

Complete reference for integrating with ActiveLog's APIs. The beta program provides access to production-grade APIs with additional beta features and extended rate limits.

## 🌐 API Overview

ActiveLog provides multiple API interfaces to suit different integration needs:

### Available APIs
- **[REST API](rest-api.md)** - Standard HTTP REST endpoints for most operations
- **[GraphQL API](graphql.md)** - Flexible queries and mutations with strong typing  
- **[WebSocket API](websocket.md)** - Real-time communication and live updates
- **[Webhook API](webhooks.md)** - Event-driven notifications and automation
- **[Authentication API](authentication.md)** - Secure access control and token management

### Beta-Specific Features
- **Extended Rate Limits** - Higher request quotas for beta testing
- **Beta Feature Access** - APIs for experimental features
- **Enhanced Debugging** - Detailed error responses and request tracing
- **Priority Support** - Dedicated API support for beta developers

## 🚀 Quick Start

### 1. Get Your API Credentials
```bash
# Using CLI
activelog auth generate-token --name "My Integration"

# Or via web interface
# Settings → API Keys → Generate New Key
```

### 2. Make Your First Request
```bash
# Test connectivity
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://beta-api.activelog.dev/v1/account

# Response
{
  "id": "user-123",
  "email": "user@example.com",
  "plan": "beta",
  "features": ["beta_features", "extended_api_access"]
}
```

### 3. Choose Your API Style
- **REST**: Traditional HTTP methods for CRUD operations
- **GraphQL**: Flexible queries for complex data fetching
- **WebSocket**: Real-time features and live collaboration
- **Webhooks**: Automated responses to events

## 📚 Documentation Structure

### By API Type
| API | Best For | Documentation |
|-----|----------|---------------|
| REST API | Standard integrations, mobile apps | [REST API Guide](rest-api.md) |
| GraphQL | Complex queries, modern web apps | [GraphQL Guide](graphql.md) |
| WebSocket | Real-time features, live updates | [WebSocket Guide](websocket.md) |
| Webhooks | Automation, event-driven workflows | [Webhook Guide](webhooks.md) |

### By Use Case
- **Web Applications**: REST + GraphQL
- **Mobile Applications**: REST + WebSocket  
- **Desktop Applications**: REST + WebSocket
- **Server Integrations**: REST + Webhooks
- **Real-time Apps**: WebSocket + GraphQL subscriptions

## 🔐 Authentication

All APIs use consistent authentication mechanisms:

### API Token Authentication (Recommended)
```javascript
const headers = {
  'Authorization': 'Bearer YOUR_API_TOKEN',
  'Content-Type': 'application/json'
};
```

### OAuth 2.0 (For User-Facing Apps)
```javascript
// Authorization flow
const authUrl = 'https://beta-api.activelog.dev/oauth/authorize?' +
  'client_id=YOUR_CLIENT_ID&' +
  'response_type=code&' +
  'redirect_uri=YOUR_REDIRECT_URI&' +
  'scope=read write';
```

### Session Authentication (Web Apps)
```javascript
// Cookie-based for web applications
fetch('/api/login', {
  method: 'POST',
  credentials: 'include',
  body: JSON.stringify({ email, password })
});
```

**Detailed Authentication Guide**: [Authentication API](authentication.md)

## 📊 Rate Limits & Quotas

### Beta Program Limits
- **REST API**: 10,000 requests/hour (vs 1,000 for regular users)
- **GraphQL**: 500 queries/hour with 10x complexity limit
- **WebSocket**: 50 concurrent connections
- **Webhooks**: Unlimited incoming (within reason)

### Rate Limit Headers
```http
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9847
X-RateLimit-Reset: 1640995200
X-RateLimit-Scope: hour
```

### Handling Rate Limits
```javascript
const response = await fetch(url, options);

if (response.status === 429) {
  const resetTime = response.headers.get('X-RateLimit-Reset');
  const waitTime = (resetTime * 1000) - Date.now();
  
  console.log(`Rate limited. Waiting ${waitTime}ms`);
  await new Promise(resolve => setTimeout(resolve, waitTime));
  
  // Retry request
  return fetch(url, options);
}
```

## 🌍 API Endpoints

### Base URLs
- **Beta Environment**: `https://beta-api.activelog.dev`
- **Production**: `https://api.activelog.dev` (when available)
- **GraphQL**: `https://beta-api.activelog.dev/graphql`
- **WebSocket**: `wss://beta-api.activelog.dev/ws`

### API Versioning
- **Current Version**: `v1`
- **Beta Features**: `v1/beta` or via feature flags
- **Experimental**: `v1/experimental` (subject to change)

### Health Check
```bash
curl https://beta-api.activelog.dev/health

# Response
{
  "status": "healthy",
  "version": "1.0.0-beta.42",
  "environment": "beta",
  "features": ["feature_flags", "real_time_sync"],
  "uptime": "72h 34m 12s"
}
```

## 📝 Data Formats

### Request/Response Format
- **Default**: JSON (application/json)
- **Alternative**: MessagePack for efficiency
- **File Uploads**: Multipart form data
- **Bulk Operations**: JSON Lines (application/x-ndjson)

### Date/Time Format
- **ISO 8601**: `2024-01-15T14:30:00Z`
- **Unix Timestamp**: For performance-critical operations
- **Timezone**: All times in UTC, client handles timezone conversion

### Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "req_123456789",
    "documentation": "https://docs.activelog.dev/api/errors#validation-error"
  }
}
```

## 🔧 SDK Libraries

### Official SDKs
```javascript
// JavaScript/Node.js
npm install @activelog/sdk
const ActiveLog = require('@activelog/sdk');

// Python
pip install activelog-sdk
import activelog

// Go
go get github.com/activelog/activelog-go

// PHP
composer require activelog/activelog-php

// Ruby
gem install activelog-ruby

// Java
// Add to pom.xml or build.gradle
```

### SDK Example
```javascript
const ActiveLog = require('@activelog/sdk');

const client = new ActiveLog({
  apiKey: process.env.ACTIVELOG_API_KEY,
  environment: 'beta'
});

// Upload file
const file = await client.files.upload({
  path: '/path/to/file.pdf',
  metadata: { project: 'beta-test' }
});

// Create project
const project = await client.projects.create({
  name: 'My Beta Project',
  description: 'Testing new features'
});
```

## 🧪 Beta Features API

### Feature Flag Integration
```javascript
// Check feature availability
const features = await client.features.list();
const aiEnabled = features.includes('ai_powered_insights');

if (aiEnabled) {
  // Use AI features
  const insights = await client.ai.generateInsights(data);
}
```

### Experimental Endpoints
```javascript
// Access experimental features (may change)
const experimental = await client.experimental.newFeature({
  data: payload,
  options: { version: 'v1.1-alpha' }
});
```

### Beta Feedback API
```javascript
// Submit API feedback
await client.feedback.submit({
  category: 'api',
  endpoint: '/v1/files/upload',
  rating: 4,
  comment: 'Upload speed improved significantly'
});
```

## 📖 Interactive Documentation

### API Explorer
- **Swagger UI**: https://beta-api.activelog.dev/docs
- **GraphQL Playground**: https://beta-api.activelog.dev/graphql/playground
- **Postman Collection**: [Download Collection](./postman-collection.json)

### Code Examples
Each endpoint includes examples in multiple languages:
- JavaScript/Node.js
- Python
- PHP
- Ruby
- Go
- cURL

### Try It Live
Use the interactive documentation to:
- Test endpoints with your API key
- See real responses with your data
- Generate code snippets for your language
- Explore schema and parameter details

## 🔍 Monitoring & Debugging

### Request Logging
```javascript
const client = new ActiveLog({
  apiKey: process.env.ACTIVELOG_API_KEY,
  debug: true, // Enable request logging
  logLevel: 'debug'
});
```

### Request Tracing
```http
# Add trace header for detailed debugging
X-Trace-Request: true
X-Trace-Level: detailed

# Response includes trace information
X-Trace-ID: trace_abc123
X-Processing-Time: 145ms
X-Cache-Status: miss
```

### Error Reporting
```javascript
// Automatic error reporting in beta SDKs
client.onError((error) => {
  console.error('API Error:', error);
  // Auto-reported to beta team for investigation
});
```

## 📋 API Reference Quick Links

### Core Resources
- [Users & Authentication](rest-api.md#users)
- [Files & Documents](rest-api.md#files)
- [Projects & Workspaces](rest-api.md#projects)
- [Search & Analytics](rest-api.md#search)

### Beta Features
- [AI-Powered Insights](rest-api.md#ai-features)
- [Real-time Collaboration](websocket.md#collaboration)
- [Advanced Analytics](graphql.md#analytics)
- [Custom Integrations](rest-api.md#integrations)

### Integration Patterns
- [Webhook Setup](webhooks.md#setup)
- [Real-time Sync](websocket.md#sync)
- [Bulk Operations](rest-api.md#bulk)
- [File Streaming](rest-api.md#streaming)

## 🆘 API Support

### Beta Developer Support
- **Email**: api-beta@activelog.dev
- **Discord**: [#api-beta channel](https://discord.gg/activelog-api)
- **Office Hours**: Wednesdays 2-3 PM PST
- **Response Time**: < 4 hours for beta developers

### Self-Service Resources
- **Status Page**: [status.activelog.dev](https://status.activelog.dev)
- **Changelog**: [API Changelog](changelog.md)
- **Community Forum**: [developers.activelog.dev](https://developers.activelog.dev)
- **GitHub Issues**: [API Issues](https://github.com/activelog/api-issues)

### Emergency Support
For production-breaking issues:
- **Email**: critical-api@activelog.dev  
- **Phone**: Available for enterprise beta users
- **Response Time**: < 1 hour

## 🔄 Migration & Versioning

### API Versioning Strategy
- **Semantic Versioning**: Major.Minor.Patch
- **Backward Compatibility**: Maintained within major versions
- **Deprecation Notice**: 6 months before removal
- **Beta Features**: May change without notice

### Migration Tools
```bash
# Check compatibility
activelog api compatibility-check --target v2.0

# Generate migration guide
activelog api migration-guide --from v1.0 --to v2.0

# Validate new version
activelog api validate --version v2.0 --config api-config.json
```

### Changelog Subscription
```bash
# Subscribe to API changes
curl -X POST https://beta-api.activelog.dev/v1/notifications/subscribe \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"type": "api_changes", "email": "dev@yourcompany.com"}'
```

---

## 🎯 Next Steps

### For New Developers
1. **Start with REST API** - Most straightforward for basic integrations
2. **Test in Playground** - Use interactive documentation
3. **Build a simple integration** - File upload or project creation
4. **Join the community** - Connect with other beta developers

### For Advanced Use Cases
1. **Explore GraphQL** - Efficient data fetching
2. **Implement WebSocket** - Real-time features
3. **Set up Webhooks** - Event-driven automation
4. **Custom SDK Development** - For specialized languages

### Beta Program Benefits
1. **Early Access** - New features before public release
2. **Extended Limits** - Higher rate limits and quotas
3. **Direct Feedback** - Influence API development
4. **Priority Support** - Faster response times

Ready to build something amazing? Start with the [REST API Guide](rest-api.md) or jump into the [GraphQL Playground](https://beta-api.activelog.dev/graphql/playground)!

---

*Last Updated: [Current Date] | API Version: 1.0.0-beta.42*