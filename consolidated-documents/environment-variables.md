# Environment Variables Configuration

This document provides a comprehensive reference for all environment variables used across ActiveLog services. Variables are organized by category and include descriptions, default values, and examples.

## Quick Reference

### Essential Variables for Development
```bash
# Database
POSTGRES_DB=activelog_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password_change_me
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis Cache
REDIS_URL=redis://redis:6379/0

# Object Storage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=minio_password_change_me
MINIO_BUCKET_NAME=activelog-dev

# Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# Application
DEBUG=true
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### Essential Variables for Production
```bash
# Database
POSTGRES_HOST=your-rds-endpoint.amazonaws.com
POSTGRES_DB=activelog_prod
POSTGRES_USER=activelog_user
POSTGRES_PASSWORD=secure_random_password_here

# Redis
REDIS_URL=redis://your-elasticache-endpoint:6379/0

# Object Storage (S3)
AWS_S3_BUCKET=activelog-prod-files
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-west-2

# Security
JWT_SECRET_KEY=production-secret-from-secrets-manager
ENCRYPTION_KEY=32-byte-encryption-key-for-sensitive-data

# Application
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## Database Configuration

### PostgreSQL Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `POSTGRES_HOST` | Database server hostname | `localhost` | `postgres` or `db.example.com` |
| `POSTGRES_PORT` | Database server port | `5432` | `5432` |
| `POSTGRES_DB` | Database name | `activelog` | `activelog_prod` |
| `POSTGRES_USER` | Database username | `postgres` | `activelog_user` |
| `POSTGRES_PASSWORD` | Database password | `password` | `secure_random_password` |
| `DATABASE_URL` | Full connection string | Auto-generated | `postgresql://user:pass@host:5432/db` |

### Database Connection Pool

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `DB_POOL_MIN_SIZE` | Minimum connections in pool | `5` | `1-50` |
| `DB_POOL_MAX_SIZE` | Maximum connections in pool | `20` | `10-100` |
| `DB_POOL_MAX_OVERFLOW` | Additional connections allowed | `10` | `0-50` |
| `DB_POOL_TIMEOUT` | Connection timeout (seconds) | `30` | `5-300` |
| `DB_POOL_RECYCLE` | Connection recycle time (seconds) | `3600` | `300-7200` |

### Database Performance

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `DB_QUERY_TIMEOUT` | Max query time (seconds) | `30` | Prevents long-running queries |
| `DB_STATEMENT_TIMEOUT` | Statement timeout (seconds) | `60` | PostgreSQL specific |
| `DB_SLOW_QUERY_THRESHOLD` | Log slow queries (milliseconds) | `1000` | Performance monitoring |

## Cache Configuration

### Redis Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | `redis://redis:6379/1` |
| `REDIS_HOST` | Redis server hostname | `localhost` | `redis` or `cache.example.com` |
| `REDIS_PORT` | Redis server port | `6379` | `6379` |
| `REDIS_DB` | Redis database number | `0` | `0-15` |
| `REDIS_PASSWORD` | Redis password | None | `redis_password_here` |

### Cache Behavior

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `CACHE_TTL_DEFAULT` | Default cache expiration (seconds) | `3600` | `60-86400` |
| `CACHE_TTL_SHORT` | Short-lived cache (seconds) | `300` | `30-1800` |
| `CACHE_TTL_LONG` | Long-lived cache (seconds) | `86400` | `3600-604800` |
| `CACHE_MAX_MEMORY` | Max memory usage | `256mb` | `64mb-2gb` |
| `CACHE_EVICTION_POLICY` | Memory eviction policy | `allkeys-lru` | `allkeys-lru`, `volatile-lru` |

## Storage Configuration

### Object Storage (S3/MinIO)

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `STORAGE_BACKEND` | Storage backend type | `minio` | `s3`, `minio`, `gcs`, `azure` |
| `STORAGE_ENDPOINT` | Storage endpoint URL | `http://minio:9000` | `s3.amazonaws.com` |
| `STORAGE_ACCESS_KEY` | Access key ID | `minio_admin` | `AKIAIOSFODNN7EXAMPLE` |
| `STORAGE_SECRET_KEY` | Secret access key | `minio_password` | `wJalrXUtnFEMI/K7MDENG/...` |
| `STORAGE_BUCKET_NAME` | Primary bucket name | `activelog` | `activelog-prod-files` |
| `STORAGE_REGION` | Storage region | `us-east-1` | `us-west-2`, `eu-west-1` |

### File Upload Limits

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `MAX_FILE_SIZE` | Maximum file size (bytes) | `104857600` | `1MB-10GB` |
| `MAX_FILES_PER_UPLOAD` | Max files per batch upload | `100` | `1-1000` |
| `UPLOAD_TIMEOUT` | Upload timeout (seconds) | `300` | `30-1800` |
| `ALLOWED_FILE_TYPES` | Comma-separated extensions | `*` | `pdf,jpg,png,docx` |

### Storage Optimization

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `STORAGE_COMPRESSION` | Enable file compression | `true` | `true`, `false` |
| `STORAGE_ENCRYPTION` | Enable at-rest encryption | `true` | `true`, `false` |
| `STORAGE_MULTIPART_THRESHOLD` | Multipart upload threshold | `64MB` | `5MB-5GB` |
| `STORAGE_MULTIPART_CHUNKSIZE` | Multipart chunk size | `16MB` | `5MB-100MB` |

## Authentication & Security

### JWT Configuration

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `JWT_SECRET_KEY` | JWT signing key | **Required** | Min 32 characters, random |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` | `HS256`, `RS256`, `ES256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiration | `15` | `5-60 minutes` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiration | `7` | `1-30 days` |
| `JWT_ISSUER` | Token issuer | `activelog` | Your organization name |

### Password Security

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `PASSWORD_MIN_LENGTH` | Minimum password length | `8` | `6-50` |
| `PASSWORD_REQUIRE_UPPERCASE` | Require uppercase letter | `true` | `true`, `false` |
| `PASSWORD_REQUIRE_LOWERCASE` | Require lowercase letter | `true` | `true`, `false` |
| `PASSWORD_REQUIRE_NUMBERS` | Require numbers | `true` | `true`, `false` |
| `PASSWORD_REQUIRE_SYMBOLS` | Require symbols | `false` | `true`, `false` |
| `PASSWORD_BCRYPT_ROUNDS` | Bcrypt hash rounds | `12` | `10-15` |

### Rate Limiting

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | `true`, `false` |
| `RATE_LIMIT_REQUESTS` | Requests per window | `100` | `10-10000` |
| `RATE_LIMIT_WINDOW` | Time window (seconds) | `3600` | `60-86400` |
| `RATE_LIMIT_AUTH_REQUESTS` | Auth requests per window | `10` | `5-100` |
| `RATE_LIMIT_AUTH_WINDOW` | Auth time window (seconds) | `300` | `60-3600` |

### Session Security

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `SESSION_SECURE` | Require HTTPS for sessions | `false` | `true` (production) |
| `SESSION_SAMESITE` | SameSite cookie attribute | `Lax` | `Strict`, `Lax`, `None` |
| `SESSION_HTTPONLY` | HTTPOnly cookie attribute | `true` | `true`, `false` |
| `CSRF_ENABLED` | Enable CSRF protection | `true` | `true`, `false` |

## AI & ML Configuration

### OpenAI Integration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API key | None | `sk-proj-...` |
| `OPENAI_MODEL` | Default model to use | `gpt-3.5-turbo` | `gpt-4`, `gpt-3.5-turbo` |
| `OPENAI_MAX_TOKENS` | Max tokens per request | `2048` | `100-4096` |
| `OPENAI_TEMPERATURE` | Response creativity | `0.7` | `0.0-2.0` |
| `OPENAI_TIMEOUT` | Request timeout (seconds) | `30` | `5-300` |

### Embedding Models

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `EMBEDDING_MODEL` | Default embedding model | `text-embedding-ada-002` | See available models |
| `EMBEDDING_DIMENSIONS` | Embedding dimensions | `1536` | Model-dependent |
| `EMBEDDING_BATCH_SIZE` | Batch processing size | `100` | `1-1000` |
| `VECTOR_DB_TYPE` | Vector database type | `pinecone` | `pinecone`, `weaviate`, `faiss` |

### Document Processing

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `OCR_ENABLED` | Enable OCR processing | `true` | `true`, `false` |
| `OCR_LANGUAGE` | OCR language | `eng` | `eng`, `spa`, `fra`, etc. |
| `OCR_CONFIDENCE_THRESHOLD` | Min confidence level | `0.7` | `0.0-1.0` |
| `TEXT_EXTRACTION_TIMEOUT` | Processing timeout (seconds) | `120` | `30-600` |

### Image Processing

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `IMAGE_RESIZE_ENABLED` | Auto-resize large images | `true` | `true`, `false` |
| `IMAGE_MAX_WIDTH` | Maximum image width | `2048` | `512-4096` |
| `IMAGE_MAX_HEIGHT` | Maximum image height | `2048` | `512-4096` |
| `IMAGE_QUALITY` | JPEG compression quality | `85` | `50-100` |
| `THUMBNAIL_SIZE` | Thumbnail dimensions | `300` | `100-500` |

## Search Configuration

### Elasticsearch Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ELASTICSEARCH_URL` | Elasticsearch endpoint | `http://elasticsearch:9200` | `https://search-domain.es.amazonaws.com` |
| `ELASTICSEARCH_USERNAME` | Authentication username | None | `elastic` |
| `ELASTICSEARCH_PASSWORD` | Authentication password | None | `elastic_password` |
| `ELASTICSEARCH_INDEX_PREFIX` | Index name prefix | `activelog` | `prod-activelog` |

### Search Behavior

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `SEARCH_RESULTS_PER_PAGE` | Results per page | `20` | `10-100` |
| `SEARCH_MAX_RESULTS` | Maximum total results | `1000` | `100-10000` |
| `SEARCH_TIMEOUT` | Search timeout (seconds) | `30` | `5-120` |
| `SEARCH_MIN_SCORE` | Minimum relevance score | `0.1` | `0.0-1.0` |

### Full-Text Search

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `FTS_ANALYZER` | Text analyzer | `standard` | `standard`, `keyword`, `simple` |
| `FTS_MIN_GRAM` | N-gram minimum size | `2` | `1-5` |
| `FTS_MAX_GRAM` | N-gram maximum size | `3` | `2-10` |
| `FTS_FUZZINESS` | Fuzzy matching level | `AUTO` | `0`, `1`, `2`, `AUTO` |

## Notification Configuration

### Email Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SMTP_HOST` | SMTP server hostname | `localhost` | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` | `587`, `465`, `25` |
| `SMTP_USERNAME` | SMTP username | None | `your-email@gmail.com` |
| `SMTP_PASSWORD` | SMTP password | None | `your-app-password` |
| `SMTP_USE_TLS` | Use TLS encryption | `true` | `true`, `false` |
| `SMTP_USE_SSL` | Use SSL encryption | `false` | `true`, `false` |

### Email Templates

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `EMAIL_FROM_ADDRESS` | Sender email address | `noreply@activelog.com` | Must be verified |
| `EMAIL_FROM_NAME` | Sender display name | `ActiveLog` | Your organization |
| `EMAIL_TEMPLATE_DIR` | Template directory | `templates/email/` | Relative path |
| `EMAIL_LOGO_URL` | Logo URL for emails | None | Full URL to logo |

### Push Notifications

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PUSH_ENABLED` | Enable push notifications | `false` | `true`, `false` |
| `FCM_SERVER_KEY` | Firebase server key | None | `AAAA...` |
| `APNS_KEY_ID` | Apple Push key ID | None | `ABC123DEF4` |
| `APNS_TEAM_ID` | Apple team ID | None | `DEF123GHI4` |
| `APNS_PRIVATE_KEY` | Apple private key path | None | `/path/to/key.p8` |

## Message Queue Configuration

### RabbitMQ Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `RABBITMQ_URL` | RabbitMQ connection string | `amqp://guest:guest@rabbitmq:5672/` | Full connection URL |
| `RABBITMQ_HOST` | RabbitMQ hostname | `rabbitmq` | `mq.example.com` |
| `RABBITMQ_PORT` | RabbitMQ port | `5672` | `5672` |
| `RABBITMQ_USERNAME` | RabbitMQ username | `guest` | `activelog_user` |
| `RABBITMQ_PASSWORD` | RabbitMQ password | `guest` | `secure_password` |
| `RABBITMQ_VHOST` | Virtual host | `/` | `/activelog` |

### Queue Configuration

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `QUEUE_DEFAULT` | Default queue name | `activelog.default` | Main processing queue |
| `QUEUE_HIGH_PRIORITY` | High priority queue | `activelog.high` | Urgent tasks |
| `QUEUE_LOW_PRIORITY` | Low priority queue | `activelog.low` | Background tasks |
| `QUEUE_DLQ` | Dead letter queue | `activelog.dlq` | Failed messages |

### Worker Configuration

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `WORKER_CONCURRENCY` | Concurrent workers | `4` | `1-16` |
| `WORKER_PREFETCH_COUNT` | Messages per worker | `10` | `1-100` |
| `WORKER_MAX_RETRIES` | Max retry attempts | `3` | `0-10` |
| `WORKER_RETRY_DELAY` | Retry delay (seconds) | `60` | `10-3600` |
| `WORKER_TASK_TIMEOUT` | Task timeout (seconds) | `300` | `30-1800` |

## Monitoring & Observability

### Logging Configuration

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `LOG_LEVEL` | Global log level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | Log output format | `json` | `json`, `text`, `structured` |
| `LOG_FILE` | Log file path | None | `/var/log/activelog.log` |
| `LOG_MAX_SIZE` | Max log file size | `100MB` | `10MB-1GB` |
| `LOG_BACKUP_COUNT` | Number of backups | `5` | `1-20` |

### Service-Specific Logging

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `AUTH_LOG_LEVEL` | Auth service log level | `INFO` | Override global level |
| `API_LOG_REQUESTS` | Log all API requests | `false` | Performance impact |
| `DB_LOG_QUERIES` | Log database queries | `false` | Debug only |
| `CACHE_LOG_OPERATIONS` | Log cache operations | `false` | Debug only |

### Metrics Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `METRICS_ENABLED` | Enable metrics collection | `true` | `true`, `false` |
| `METRICS_PORT` | Metrics endpoint port | `9090` | `9090-9099` |
| `METRICS_PATH` | Metrics endpoint path | `/metrics` | `/prometheus` |
| `PROMETHEUS_URL` | Prometheus server URL | None | `http://prometheus:9090` |

### Tracing Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TRACING_ENABLED` | Enable distributed tracing | `false` | `true`, `false` |
| `JAEGER_AGENT_HOST` | Jaeger agent hostname | `jaeger` | `jaeger.example.com` |
| `JAEGER_AGENT_PORT` | Jaeger agent port | `6831` | `6831` |
| `JAEGER_SERVICE_NAME` | Service name in traces | Service-specific | `activelog-auth` |
| `TRACE_SAMPLING_RATE` | Sampling percentage | `0.1` | `0.0-1.0` |

## Application Configuration

### General Settings

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `ENVIRONMENT` | Deployment environment | `development` | `development`, `staging`, `production` |
| `DEBUG` | Enable debug mode | `false` | `true`, `false` |
| `SECRET_KEY` | Application secret key | **Required** | Random string |
| `APP_NAME` | Application name | `ActiveLog` | Your deployment name |
| `APP_VERSION` | Application version | `1.0.0` | Semantic version |

### API Configuration

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `API_PREFIX` | API URL prefix | `/api/v1` | URL path |
| `API_DOCS_URL` | API documentation URL | `/docs` | URL path or `null` |
| `API_REDOC_URL` | ReDoc documentation URL | `/redoc` | URL path or `null` |
| `API_OPENAPI_URL` | OpenAPI spec URL | `/openapi.json` | URL path or `null` |

### CORS Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CORS_ALLOW_ORIGINS` | Allowed origins | `*` | `https://app.example.com,https://admin.example.com` |
| `CORS_ALLOW_METHODS` | Allowed HTTP methods | `*` | `GET,POST,PUT,DELETE` |
| `CORS_ALLOW_HEADERS` | Allowed headers | `*` | `Authorization,Content-Type` |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials | `true` | `true`, `false` |

### Feature Flags

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `FEATURE_AI_ENABLED` | Enable AI features | `true` | Requires API keys |
| `FEATURE_COLLABORATION` | Enable real-time collaboration | `true` | WebSocket required |
| `FEATURE_MOBILE_API` | Enable mobile API endpoints | `true` | Mobile app features |
| `FEATURE_ANALYTICS` | Enable analytics collection | `true` | Privacy considerations |
| `FEATURE_WEBHOOKS` | Enable webhook support | `false` | External integrations |

## Service-Specific Variables

### Auth Service

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `AUTH_OAUTH_GOOGLE_CLIENT_ID` | Google OAuth client ID | None | OAuth integration |
| `AUTH_OAUTH_GOOGLE_CLIENT_SECRET` | Google OAuth secret | None | OAuth integration |
| `AUTH_OAUTH_MICROSOFT_CLIENT_ID` | Microsoft OAuth client ID | None | OAuth integration |
| `AUTH_OAUTH_MICROSOFT_CLIENT_SECRET` | Microsoft OAuth secret | None | OAuth integration |
| `AUTH_LDAP_SERVER` | LDAP server URL | None | Enterprise auth |
| `AUTH_LDAP_BASE_DN` | LDAP base DN | None | Enterprise auth |

### File Sync Service

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `SYNC_BATCH_SIZE` | Files per sync batch | `100` | `10-1000` |
| `SYNC_INTERVAL` | Sync check interval (seconds) | `30` | `5-300` |
| `SYNC_CONFLICT_RESOLUTION` | Default conflict resolution | `keep_both` | `keep_both`, `keep_server`, `keep_client` |
| `SYNC_MAX_FILE_AGE` | Max file age for sync (days) | `365` | `7-3650` |

### Analytics Service

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `ANALYTICS_RETENTION_DAYS` | Event retention period | `90` | `7-730` |
| `ANALYTICS_BATCH_SIZE` | Events per batch | `1000` | `100-10000` |
| `ANALYTICS_FLUSH_INTERVAL` | Flush interval (seconds) | `60` | `10-300` |
| `ANALYTICS_SAMPLE_RATE` | Event sampling rate | `1.0` | `0.0-1.0` |

## Environment-Specific Configurations

### Development Environment
```bash
# .env.development
DEBUG=true
LOG_LEVEL=DEBUG
CORS_ALLOW_ORIGINS=*
CACHE_TTL_DEFAULT=300
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=5
METRICS_ENABLED=false
TRACING_ENABLED=false
```

### Staging Environment
```bash
# .env.staging
DEBUG=false
LOG_LEVEL=INFO
CORS_ALLOW_ORIGINS=https://staging.example.com
CACHE_TTL_DEFAULT=1800
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=15
METRICS_ENABLED=true
TRACING_ENABLED=true
```

### Production Environment
```bash
# .env.production
DEBUG=false
LOG_LEVEL=WARNING
CORS_ALLOW_ORIGINS=https://app.example.com
CACHE_TTL_DEFAULT=3600
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=50
METRICS_ENABLED=true
TRACING_ENABLED=true
RATE_LIMIT_ENABLED=true
SESSION_SECURE=true
```

## Configuration Validation

### Required Variables Check
```bash
# Script to validate required environment variables
#!/bin/bash
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "JWT_SECRET_KEY" 
    "STORAGE_SECRET_KEY"
    "SECRET_KEY"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "Error: Required variable $var is not set"
        exit 1
    fi
done
```

### Security Validation
```bash
# Check for insecure defaults
if [[ "$JWT_SECRET_KEY" == "your-super-secret-jwt-key-change-this" ]]; then
    echo "Warning: Using default JWT secret key in production!"
fi

if [[ "$POSTGRES_PASSWORD" == "password" ]] && [[ "$ENVIRONMENT" == "production" ]]; then
    echo "Error: Insecure database password in production!"
    exit 1
fi
```

## Configuration Management Tools

### Environment File Templates
```bash
# Generate environment file from template
./scripts/generate-env.sh --environment production --output .env.prod

# Validate environment configuration
./scripts/validate-config.sh --env-file .env.prod

# Compare configurations
./scripts/diff-config.sh .env.staging .env.production
```

### Configuration Backup
```bash
# Backup current configuration
tar czf config-backup-$(date +%Y%m%d).tar.gz .env* docker-compose*.yml

# Restore configuration
tar xzf config-backup-20240101.tar.gz
```

## Best Practices

### Security Best Practices

1. **Never commit secrets to version control**
   ```bash
   # Use git-secrets to prevent accidental commits
   git secrets --install
   git secrets --register-aws
   ```

2. **Use strong, unique passwords and keys**
   ```bash
   # Generate secure random keys
   openssl rand -hex 32  # For JWT secrets
   openssl rand -base64 32  # For encryption keys
   ```

3. **Rotate secrets regularly**
   - JWT keys: Every 90 days
   - Database passwords: Every 180 days
   - API keys: As recommended by provider

4. **Use environment-specific configurations**
   - Separate files for dev/staging/production
   - Different secrets for each environment
   - Appropriate debug and logging levels

### Performance Optimization

1. **Database Connection Pooling**
   ```bash
   # Production settings
   DB_POOL_MIN_SIZE=10
   DB_POOL_MAX_SIZE=50
   DB_POOL_MAX_OVERFLOW=20
   ```

2. **Cache Configuration**
   ```bash
   # Optimize cache TTL based on data access patterns
   CACHE_TTL_SHORT=300    # Frequently changing data
   CACHE_TTL_DEFAULT=3600 # Regular data
   CACHE_TTL_LONG=86400   # Rarely changing data
   ```

3. **Worker Scaling**
   ```bash
   # Scale based on CPU cores and workload
   WORKER_CONCURRENCY=$(($(nproc) * 2))
   ```

### Monitoring Configuration

1. **Enable appropriate logging levels**
   ```bash
   # Production: WARNING or ERROR
   # Staging: INFO
   # Development: DEBUG
   ```

2. **Set up metrics collection**
   ```bash
   METRICS_ENABLED=true
   PROMETHEUS_URL=http://prometheus:9090
   ```

3. **Configure alerting thresholds**
   ```bash
   # Example alerting configuration
   ALERT_ERROR_RATE_THRESHOLD=0.01
   ALERT_RESPONSE_TIME_THRESHOLD=2000
   ALERT_DISK_USAGE_THRESHOLD=0.85
   ```

---

**Important Notes:**

1. Always use environment-specific configuration files
2. Never commit sensitive information to version control
3. Regularly review and update configurations
4. Test configuration changes in staging before production
5. Monitor application behavior after configuration changes

For additional help with configuration, contact support at support@activelog.com or refer to the [troubleshooting guide](../troubleshooting/README.md).