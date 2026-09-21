#!/bin/bash

# Environment Configuration for ActiveLog Deployment
# Supports both beta and production environments

# Set default environment if not specified
ENVIRONMENT=${ENVIRONMENT:-"beta"}

# Common configuration
export PROJECT_NAME="activelog"
export COMPOSE_PROJECT_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

# Database configuration
export DB_NAME="${PROJECT_NAME}_${ENVIRONMENT}"
export DB_USER="${PROJECT_NAME}_user"
export DB_PASSWORD_FILE="/run/secrets/db_password"

# Redis configuration
export REDIS_DB=0
if [[ "$ENVIRONMENT" == "beta" ]]; then
    export REDIS_DB=1  # Use different Redis DB for beta
fi

# API configuration
export API_VERSION="v1"
export API_BASE_PATH="/api/${API_VERSION}"

# Security configuration
export JWT_SECRET_FILE="/run/secrets/jwt_secret"
export ENCRYPTION_KEY_FILE="/run/secrets/encryption_key"

# Feature flags
export FEATURE_FLAGS_ENABLED=true
export FEATURE_FLAGS_REFRESH_INTERVAL=300  # 5 minutes

# Monitoring and logging
export LOG_LEVEL="INFO"
export METRICS_ENABLED=true
export TRACING_ENABLED=true

# Environment-specific configuration
case "$ENVIRONMENT" in
    "beta")
        # Beta environment settings
        export API_PORT=8080
        export FRONTEND_PORT=3000
        export ADMIN_PORT=3001
        export DB_PORT=5432
        export REDIS_PORT=6379
        
        # Beta-specific features
        export DEBUG_MODE=true
        export BETA_FEATURES_ENABLED=true
        export FEEDBACK_COLLECTION_ENABLED=true
        export NDA_REQUIRED=true
        export INVITE_ONLY=true
        
        # Resource limits (lighter for beta)
        export DB_MAX_CONNECTIONS=50
        export API_WORKERS=2
        export REDIS_MAXMEMORY="256mb"
        
        # Backup and safety
        export BACKUP_RETENTION_DAYS=7
        export MIGRATION_BACKUP_ENABLED=true
        export ROLLBACK_ENABLED=true
        
        # Domain and URLs
        export DOMAIN="beta.activelog.dev"
        export FRONTEND_URL="http://localhost:3000"
        export API_URL="http://localhost:8080"
        export WEBHOOK_BASE_URL="http://localhost:8080/webhooks"
        
        # Email configuration (test mode)
        export EMAIL_PROVIDER="smtp"
        export EMAIL_TEST_MODE=true
        export EMAIL_FROM="noreply-beta@activelog.dev"
        
        # File storage (local for beta)
        export STORAGE_TYPE="local"
        export STORAGE_PATH="/app/storage"
        export MAX_FILE_SIZE="100MB"
        
        ;;
        
    "production")
        # Production environment settings
        export API_PORT=80
        export FRONTEND_PORT=443
        export ADMIN_PORT=8443
        export DB_PORT=5432
        export REDIS_PORT=6379
        
        # Production security
        export DEBUG_MODE=false
        export BETA_FEATURES_ENABLED=false
        export FEEDBACK_COLLECTION_ENABLED=true
        export NDA_REQUIRED=false
        export INVITE_ONLY=false
        export HTTPS_ENABLED=true
        export SSL_CERT_PATH="/etc/ssl/certs/activelog.crt"
        export SSL_KEY_PATH="/etc/ssl/private/activelog.key"
        
        # Resource limits (full capacity)
        export DB_MAX_CONNECTIONS=200
        export API_WORKERS=8
        export REDIS_MAXMEMORY="2gb"
        
        # Backup and safety
        export BACKUP_RETENTION_DAYS=30
        export MIGRATION_BACKUP_ENABLED=true
        export ROLLBACK_ENABLED=true
        export BLUE_GREEN_DEPLOYMENT=true
        
        # Domain and URLs
        export DOMAIN="activelog.com"
        export FRONTEND_URL="https://activelog.com"
        export API_URL="https://api.activelog.com"
        export WEBHOOK_BASE_URL="https://api.activelog.com/webhooks"
        
        # Email configuration (production)
        export EMAIL_PROVIDER="ses"  # AWS SES
        export EMAIL_TEST_MODE=false
        export EMAIL_FROM="noreply@activelog.com"
        
        # File storage (S3 for production)
        export STORAGE_TYPE="s3"
        export S3_BUCKET="activelog-storage"
        export S3_REGION="us-east-1"
        export MAX_FILE_SIZE="1GB"
        
        # CDN configuration
        export CDN_ENABLED=true
        export CDN_URL="https://cdn.activelog.com"
        
        ;;
        
    *)
        echo "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Derived configuration
export DATABASE_URL="postgresql://${DB_USER}@localhost:${DB_PORT}/${DB_NAME}"
export REDIS_URL="redis://localhost:${REDIS_PORT}/${REDIS_DB}"

# Docker configuration
export DOCKER_REGISTRY="activelog"
export IMAGE_TAG="${ENVIRONMENT}-$(date +%Y%m%d)"

# Logging configuration
export LOG_FORMAT="json"
export LOG_FILE="/var/log/activelog/${ENVIRONMENT}.log"

# Health check configuration
export HEALTH_CHECK_INTERVAL=30
export HEALTH_CHECK_TIMEOUT=10
export HEALTH_CHECK_RETRIES=3

# Rate limiting
if [[ "$ENVIRONMENT" == "beta" ]]; then
    export RATE_LIMIT_REQUESTS_PER_MINUTE=100
else
    export RATE_LIMIT_REQUESTS_PER_MINUTE=1000
fi

# Print configuration summary
echo "Environment configuration loaded:"
echo "  Environment: $ENVIRONMENT"
echo "  Project: $COMPOSE_PROJECT_NAME"
echo "  Frontend URL: $FRONTEND_URL"
echo "  API URL: $API_URL"
echo "  Database: $DB_NAME"
echo "  Debug Mode: $DEBUG_MODE"
echo "  Beta Features: $BETA_FEATURES_ENABLED"