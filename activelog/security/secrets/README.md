# ActiveLog Secrets Rotation Service

A comprehensive automated secrets rotation system for ActiveLog that securely manages, rotates, and distributes secrets across multiple environments and external services.

## Features

### Core Functionality
- **Automated Rotation**: Scheduled automatic rotation based on configurable intervals
- **Manual Rotation**: On-demand rotation via REST API or CLI
- **Emergency Rotation**: Immediate rotation of all secrets in case of security incidents
- **Version Management**: Maintains multiple versions of secrets with configurable retention
- **Rollback Support**: Ability to rollback to previous secret versions

### Security Features
- **Encryption at Rest**: All secrets encrypted using Fernet symmetric encryption
- **Secure Generation**: Cryptographically secure secret generation per type
- **Access Control**: API key-based authentication and rate limiting
- **Audit Logging**: Comprehensive audit trail of all secret operations
- **Compliance**: SOX, PCI, and GDPR compliant logging and retention

### External Integrations
- **HashiCorp Vault**: Automatic secret updates in Vault
- **AWS Secrets Manager**: Integration with AWS Secrets Manager
- **Database Updates**: Automatic database credential rotation
- **Service Notifications**: Slack, email, and PagerDuty notifications

### Monitoring & Observability
- **Health Checks**: Comprehensive health monitoring
- **Metrics**: Prometheus metrics for rotation statistics
- **Distributed Tracing**: Jaeger integration for request tracing
- **Real-time Status**: Live status dashboard for all secrets

## Quick Start

### 1. Start the Secrets Rotation Service

```bash
cd ~/activelog/security/secrets
docker-compose up -d
```

This starts all components:
- PostgreSQL database for secret storage
- Redis for caching and session management
- HashiCorp Vault for secure secret storage
- Secrets rotation service with REST API
- Background scheduler for automated rotations
- Web UI for secret management

### 2. Verify Service Status

```bash
# Check all services
docker-compose ps

# Check service health
curl http://localhost:8087/api/v1/secrets/status
```

### 3. Configure Your First Secret

```bash
# Using the CLI tool
python3 scripts/rotate-secrets.py create database-password database_password --interval 30 --environments production staging

# Or via REST API
curl -X POST http://localhost:8087/api/v1/secrets/config \
  -H "Content-Type: application/json" \
  -d '{
    "name": "database-password",
    "type": "database_password",
    "rotation_interval_days": 30,
    "auto_rotate": true,
    "environments": ["production", "staging"]
  }'
```

### 4. Manual Secret Rotation

```bash
# Using CLI
python3 scripts/rotate-secrets.py rotate database-password

# Or via API
curl -X POST http://localhost:8087/api/v1/secrets/database-password/rotate
```

## Secret Types

The service supports various secret types with appropriate generation strategies:

### Database Passwords
- **Type**: `database_password`
- **Length**: 32 characters
- **Characters**: Alphanumeric only (no special characters that might cause DB issues)
- **Use Case**: Database user passwords, connection strings

### API Keys
- **Type**: `api_key`
- **Format**: URL-safe Base64 encoded
- **Length**: 32 bytes (44 characters encoded)
- **Use Case**: External service API keys, internal service authentication

### JWT Secrets
- **Type**: `jwt_secret`
- **Format**: URL-safe Base64 encoded
- **Length**: 64 bytes (88 characters encoded)
- **Use Case**: JWT token signing and verification

### Encryption Keys
- **Type**: `encryption_key`
- **Format**: Fernet-compatible key
- **Length**: 32 bytes Base64 encoded
- **Use Case**: Application-level encryption, data protection

### Generic Passwords
- **Type**: `password`
- **Length**: 24-32 characters
- **Characters**: Mixed alphanumeric with symbols
- **Requirements**: Uppercase, lowercase, numbers, symbols
- **Use Case**: User accounts, service passwords

## Configuration

### Environment Variables

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_DB=activelog_secrets
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=2

# HashiCorp Vault
VAULT_URL=http://localhost:8200
VAULT_TOKEN=your-vault-token

# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1

# Notification Settings
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=notifications@activelog.com
EMAIL_PASSWORD=app-password
EMAIL_FROM=noreply@activelog.com
```

### Secret Configuration

Each secret is configured with the following parameters:

```yaml
name: "database-master-password"
type: "database_password"
rotation_interval_days: 30
auto_rotate: true
backup_versions: 3
notification_before_expiry_hours: 24
environments: ["production", "staging"]
```

## CLI Usage

The CLI tool provides comprehensive secret management capabilities:

### List All Secrets
```bash
python3 scripts/rotate-secrets.py list
```

### Get Secret Information
```bash
python3 scripts/rotate-secrets.py get database-password
```

### Create Secret Configuration
```bash
python3 scripts/rotate-secrets.py create api-key-stripe api_key --interval 30 --environments production
```

### Manual Rotation
```bash
python3 scripts/rotate-secrets.py rotate database-password
```

### Emergency Rotation
```bash
python3 scripts/rotate-secrets.py emergency
```

### Test Connection
```bash
python3 scripts/rotate-secrets.py test
```

## REST API

### Create/Update Secret Configuration
```bash
POST /api/v1/secrets/config
{
  "name": "database-password",
  "type": "database_password",
  "rotation_interval_days": 30,
  "auto_rotate": true,
  "backup_versions": 3,
  "notification_before_expiry_hours": 24,
  "environments": ["production", "staging"]
}
```

### Rotate Secret
```bash
POST /api/v1/secrets/{secret_name}/rotate
```

### Get Current Secret Version
```bash
GET /api/v1/secrets/{secret_name}/current
```

### Get Rotation Status
```bash
GET /api/v1/secrets/status
```

### Emergency Rotation
```bash
POST /api/v1/secrets/emergency-rotation
```

## Automated Scheduling

The service automatically performs the following operations:

### Rotation Checks (Hourly)
- Checks all secrets with `auto_rotate: true`
- Compares last rotation time with rotation interval
- Initiates rotation for expired secrets
- Records all rotation attempts in audit log

### Expiry Notifications (Every 6 hours)
- Identifies secrets expiring within notification window
- Sends notifications via configured channels (Slack, email)
- Tracks notification delivery status

### Cleanup Tasks (Daily)
- Removes old secret versions beyond retention policy
- Cleans up expired audit logs
- Optimizes database performance

## External Service Integration

### HashiCorp Vault
```bash
# Secrets are automatically stored in Vault at:
# {environment}/{secret_name}
vault kv get secret/production/database-password
```

### AWS Secrets Manager
```bash
# Secrets are automatically stored as:
# {environment}/{secret_name}
aws secretsmanager get-secret-value --secret-id production/database-password
```

### Database Connections
The service can automatically update database connection strings and user passwords across multiple database instances.

## Monitoring

### Health Endpoints
- **Service Health**: `GET /health`
- **Detailed Status**: `GET /api/v1/secrets/status`
- **Metrics**: `GET /metrics` (Prometheus format)

### Key Metrics
- `secrets_total`: Total number of configured secrets
- `secrets_rotations_total`: Total rotations performed
- `secrets_rotation_failures_total`: Failed rotation attempts
- `secrets_expiring_soon`: Secrets expiring within 7 days
- `secrets_expired`: Expired secrets requiring immediate attention

### Grafana Dashboard
Access the monitoring dashboard at: `http://localhost:3001`

Key visualizations:
- Rotation success rate over time
- Secret expiry timeline
- Failed rotation alerts
- Service performance metrics

## Compliance & Audit

### Audit Logging
All operations are logged with:
- Timestamp and user identification
- Action performed (create, rotate, access)
- Resource affected (secret name, version)
- Source IP address and user agent
- Success/failure status and error details

### Retention Policies
- **Audit Logs**: 7 years (SOX compliance)
- **Rotation History**: 3 years
- **Notification Logs**: 90 days
- **Secret Versions**: Configurable per secret (default: 3 versions)

### GDPR Compliance
- Data subject access requests supported
- Right to be forgotten implementation
- Data processing transparency
- Privacy-by-design architecture

## Security Considerations

### Encryption
- All secrets encrypted at rest using Fernet symmetric encryption
- Encryption keys stored separately from encrypted data
- Regular key rotation (annually by default)

### Access Control
- API key authentication required for all endpoints
- Rate limiting to prevent brute force attacks
- IP whitelisting for production deployments
- Role-based access control (RBAC) integration

### Network Security
- TLS encryption for all API communications
- Internal service mesh with mTLS
- Firewall rules restricting access to necessary ports only
- VPC isolation in cloud deployments

## Troubleshooting

### Check Service Status
```bash
# View container logs
docker-compose logs secrets-rotation

# Check database connectivity
docker-compose exec postgres psql -U postgres -d activelog_secrets -c "SELECT COUNT(*) FROM secret_configs;"

# Test Redis connection
docker-compose exec redis redis-cli ping

# Verify Vault status
docker-compose exec vault vault status
```

### Common Issues

#### Secret Rotation Failures
1. Check external service connectivity (Vault, AWS)
2. Verify credentials and permissions
3. Review rotation history for error messages
4. Check database constraints and foreign key relationships

#### Database Connection Issues
1. Verify PostgreSQL service is running
2. Check connection parameters in environment variables
3. Ensure database schema is properly initialized
4. Review database logs for connection errors

#### Notification Failures
1. Test SMTP settings and credentials
2. Verify Slack webhook URL is valid
3. Check firewall rules for outbound connections
4. Review notification service logs

### Emergency Procedures

#### Security Incident Response
```bash
# Immediate emergency rotation of all secrets
python3 scripts/rotate-secrets.py emergency

# Disable automatic rotation temporarily
curl -X PUT http://localhost:8087/api/v1/config/auto-rotate -d '{"enabled": false}'

# Export audit logs for investigation
curl -X GET http://localhost:8087/api/v1/audit/export > security_incident_$(date +%Y%m%d).json
```

#### Service Recovery
```bash
# Restart all services
docker-compose restart

# Force database schema rebuild (CAUTION: Will lose data)
docker-compose down -v
docker-compose up -d

# Restore from backup
./scripts/restore-backup.sh backup_20231201_120000.sql
```

## Development

### Local Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Start development server
python rotation-service.py
```

### Testing
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Load testing
k6 run tests/load/rotation-load-test.js
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request with detailed description

## Support

For issues or questions:
1. Check service logs: `make logs`
2. Review configuration: `make validate-config`
3. Test connectivity: `python3 scripts/rotate-secrets.py test`
4. Consult troubleshooting guide above
5. Contact security team: security@activelog.com