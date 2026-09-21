# ActiveLog API Documentation

This directory contains comprehensive API documentation for all ActiveLog services. Each service provides OpenAPI specifications and interactive documentation.

## Services Overview

ActiveLog consists of multiple microservices, each with their own REST API:

### Core Services

1. **Auth Service** - Authentication and authorization
2. **API Gateway** - Request routing and load balancing
3. **Metadata Service** - File metadata and search
4. **File Sync** - File synchronization and versioning
5. **Analytics Service** - Usage analytics and reporting
6. **Notifications Service** - Push notifications and alerts

### Processing Services

7. **Document AI** - Document processing and OCR
8. **Video Pipeline** - Video transcoding and analysis
9. **ML Pipeline** - Machine learning workflows
10. **AI Orchestrator** - AI model coordination

### Storage & Sync Services

11. **Backup Service** - Data backup and recovery
12. **Batch Import** - Bulk data import
13. **File Watcher** - File system monitoring
14. **Sync Engine** - Real-time synchronization

### Specialized Services

15. **Collaboration** - Real-time collaboration features
16. **Smart Folders** - Intelligent folder organization
17. **Workflows** - Automated workflow engine
18. **Mobile API** - Mobile-optimized endpoints
19. **Data Export** - Data export and archival

## API Documentation Access

### Interactive Documentation

Each service provides interactive Swagger UI documentation at:
- `http://localhost:{port}/docs` - Swagger UI
- `http://localhost:{port}/redoc` - ReDoc

### Service Ports

| Service | Port | Swagger UI | ReDoc |
|---------|------|------------|-------|
| Auth | 8001 | [/docs](http://localhost:8001/docs) | [/redoc](http://localhost:8001/redoc) |
| API Gateway | 8000 | [/docs](http://localhost:8000/docs) | [/redoc](http://localhost:8000/redoc) |
| Metadata | 8002 | [/docs](http://localhost:8002/docs) | [/redoc](http://localhost:8002/redoc) |
| Analytics | 8003 | [/docs](http://localhost:8003/docs) | [/redoc](http://localhost:8003/redoc) |
| Notifications | 8004 | [/docs](http://localhost:8004/docs) | [/redoc](http://localhost:8004/redoc) |
| Document AI | 8005 | [/docs](http://localhost:8005/docs) | [/redoc](http://localhost:8005/redoc) |
| Video Pipeline | 8006 | [/docs](http://localhost:8006/docs) | [/redoc](http://localhost:8006/redoc) |
| ML Pipeline | 8007 | [/docs](http://localhost:8007/docs) | [/redoc](http://localhost:8007/redoc) |
| Backup | 8008 | [/docs](http://localhost:8008/docs) | [/redoc](http://localhost:8008/redoc) |
| Batch Import | 8009 | [/docs](http://localhost:8009/docs) | [/redoc](http://localhost:8009/redoc) |
| Collaboration | 8010 | [/docs](http://localhost:8010/docs) | [/redoc](http://localhost:8010/redoc) |
| Smart Folders | 8011 | [/docs](http://localhost:8011/docs) | [/redoc](http://localhost:8011/redoc) |
| Workflows | 8012 | [/docs](http://localhost:8012/docs) | [/redoc](http://localhost:8012/redoc) |
| Mobile API | 8013 | [/docs](http://localhost:8013/docs) | [/redoc](http://localhost:8013/redoc) |
| Data Export | 8014 | [/docs](http://localhost:8014/docs) | [/redoc](http://localhost:8014/redoc) |

## Authentication

Most APIs require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

Get a token from the Auth Service:
```bash
curl -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

## Common Response Formats

### Success Response
```json
{
  "status": "success",
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": { ... }
  }
}
```

### Pagination
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

## Rate Limiting

APIs are rate-limited to prevent abuse:
- **Standard**: 100 requests per minute
- **Authenticated**: 1000 requests per minute
- **Premium**: 10000 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1609459200
```

## Webhooks

Some services support webhooks for real-time notifications:
- File uploads/updates
- Processing completion
- Error notifications
- User activity

Configure webhooks via the respective service APIs or admin dashboard.

## SDK Support

Official SDKs are available for:
- Python: `pip install activelog-sdk`
- JavaScript/Node.js: `npm install @activelog/sdk`
- TypeScript: `npm install @activelog/sdk-ts`

## API Versioning

APIs are versioned using URL prefixes:
- `/v1/` - Current stable version
- `/v2/` - Beta version (where applicable)

Version information is included in response headers:
```
X-API-Version: v1.0.0
```

## OpenAPI Specifications

Download OpenAPI 3.0 specifications:
- [auth-service.yaml](./openapi/auth-service.yaml)
- [metadata-service.yaml](./openapi/metadata-service.yaml)
- [analytics-service.yaml](./openapi/analytics-service.yaml)
- ... (see openapi/ directory for all services)

## Examples

See the [examples](./examples/) directory for:
- cURL examples
- Python SDK examples
- JavaScript SDK examples
- Postman collections
- Integration patterns

## Support

For API support:
- Documentation: [docs.activelog.com](https://docs.activelog.com)
- Community: [community.activelog.com](https://community.activelog.com)
- Issues: [GitHub Issues](https://github.com/activelog/activelog/issues)
- Email: api-support@activelog.com