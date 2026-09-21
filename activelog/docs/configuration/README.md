# Configuration Documentation

This section contains comprehensive configuration documentation for ActiveLog, covering environment variables, service configuration, deployment settings, and best practices.

## Configuration Files Overview

ActiveLog uses multiple configuration approaches depending on the deployment scenario:

- **Environment Variables** - Primary configuration method
- **Configuration Files** - YAML/JSON for complex settings
- **Docker Compose** - Container orchestration configuration
- **Kubernetes Manifests** - Production orchestration configuration

## Quick Start Configurations

### Development Setup
```bash
# Copy example configuration
cp .env.example .env

# Edit with your preferred editor
nano .env

# Essential development settings
DEBUG=true
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### Production Setup
```bash
# Use secure configuration template
cp .env.production.example .env.production

# Set secure values (never use defaults!)
JWT_SECRET_KEY="$(openssl rand -hex 32)"
POSTGRES_PASSWORD="$(openssl rand -base64 32)"
```

## Configuration Categories

### 🔐 [Environment Variables](./environment-variables.md)
Complete reference for all environment variables across services:
- Database configuration
- Cache settings  
- Storage options
- Authentication & security
- AI/ML configuration
- Monitoring settings

### ⚙️ [Service Configuration](./service-config.md)
Individual service configuration files:
- FastAPI service settings
- Database connection pools
- Message queue configuration
- External API integrations

### 🐳 [Container Configuration](./container-config.md)
Docker and Kubernetes configuration:
- Docker Compose files
- Kubernetes manifests
- Resource limits and requests
- Health checks and probes

### 🌍 [Environment-Specific Settings](./environments.md)
Configuration for different deployment environments:
- Development environment
- Staging environment  
- Production environment
- Testing environment

### 🔒 [Security Configuration](./security-config.md)
Security-focused configuration:
- SSL/TLS certificates
- Authentication providers
- Authorization policies
- Encryption settings

### 📊 [Monitoring Configuration](./monitoring-config.md)
Observability and monitoring setup:
- Prometheus metrics
- Grafana dashboards
- Log aggregation
- Distributed tracing

### 🌐 [Network Configuration](./network-config.md)
Networking and connectivity settings:
- Load balancer configuration
- Service mesh settings
- DNS configuration
- Firewall rules

## Configuration Management Tools

### Configuration Validation
```bash
# Validate environment variables
./scripts/validate-config.sh

# Check for security issues
./scripts/security-check.sh

# Test database connections
./scripts/test-connections.sh
```

### Configuration Templates
```bash
# Generate configuration from template
./scripts/generate-config.sh --env production --region us-west-2

# Migrate configuration between versions
./scripts/migrate-config.sh --from v1.0 --to v1.1
```

### Secret Management
```bash
# Generate secure secrets
./scripts/generate-secrets.sh

# Rotate existing secrets
./scripts/rotate-secrets.sh --service auth

# Backup configuration
./scripts/backup-config.sh
```

## Configuration Hierarchy

ActiveLog loads configuration in the following order (later sources override earlier ones):

1. **Default Values** - Built into the application
2. **Configuration Files** - YAML/JSON files in `/config`
3. **Environment Variables** - System environment variables
4. **Command Line Arguments** - Runtime parameters
5. **Runtime Configuration** - Admin panel settings

### Example Configuration Loading
```python
# Configuration priority example
config = {
    'database_url': 'sqlite:///default.db',        # 1. Default
    **load_config_file('config/app.yaml'),         # 2. Config file
    **load_environment_variables(),                # 3. Environment
    **parse_command_line_args(),                   # 4. CLI args
    **load_runtime_config()                        # 5. Runtime
}
```

## Common Configuration Patterns

### Multi-Environment Configuration

```yaml
# config/app.yaml
default: &default
  debug: false
  log_level: INFO
  
development:
  <<: *default
  debug: true
  log_level: DEBUG
  database_url: postgresql://dev:dev@localhost/activelog_dev
  
production:
  <<: *default
  database_url: ${DATABASE_URL}
  redis_url: ${REDIS_URL}
  jwt_secret_key: ${JWT_SECRET_KEY}
```

### Feature Flags
```yaml
# config/features.yaml
features:
  ai_processing: true
  real_time_collaboration: true
  mobile_api: true
  advanced_analytics: false
  beta_features: false
  
environments:
  development:
    beta_features: true
  production:
    beta_features: false
```

### Service-Specific Configuration
```yaml
# config/services/auth-service.yaml
auth:
  jwt:
    secret_key: ${JWT_SECRET_KEY}
    algorithm: HS256
    access_token_expire_minutes: 15
    refresh_token_expire_days: 7
  
  oauth:
    google:
      client_id: ${GOOGLE_OAUTH_CLIENT_ID}
      client_secret: ${GOOGLE_OAUTH_CLIENT_SECRET}
    microsoft:
      client_id: ${MICROSOFT_OAUTH_CLIENT_ID}
      client_secret: ${MICROSOFT_OAUTH_CLIENT_SECRET}
  
  security:
    password_min_length: 8
    max_login_attempts: 5
    lockout_duration_minutes: 30
```

## Configuration Best Practices

### Security Best Practices

1. **Never commit secrets to version control**
   ```bash
   # Add to .gitignore
   .env*
   secrets/
   *.key
   *.pem
   ```

2. **Use environment variables for secrets**
   ```bash
   # Good - environment variable
   DATABASE_URL=${DATABASE_URL}
   
   # Bad - hardcoded in config file
   database_url: postgresql://user:password@localhost/db
   ```

3. **Rotate secrets regularly**
   ```bash
   # Set up automated secret rotation
   ./scripts/rotate-secrets.sh --schedule weekly
   ```

### Performance Best Practices

1. **Optimize connection pools**
   ```yaml
   database:
     pool_size: 20
     max_overflow: 30
     pool_timeout: 30
     pool_recycle: 3600
   ```

2. **Configure appropriate cache TTL**
   ```yaml
   cache:
     default_ttl: 3600
     short_ttl: 300
     long_ttl: 86400
   ```

3. **Set resource limits**
   ```yaml
   resources:
     limits:
       memory: "1Gi"
       cpu: "1000m"
     requests:
       memory: "512Mi"
       cpu: "500m"
   ```

### Maintainability Best Practices

1. **Document all configuration options**
   ```yaml
   # config/app.yaml
   app:
     # Application debug mode (true/false)
     # Default: false
     # Environment variable: DEBUG
     debug: ${DEBUG:false}
   ```

2. **Use consistent naming conventions**
   ```bash
   # Service-specific prefixes
   AUTH_JWT_SECRET_KEY
   STORAGE_S3_BUCKET_NAME
   CACHE_REDIS_URL
   ```

3. **Validate configuration on startup**
   ```python
   def validate_config():
       required_vars = ['DATABASE_URL', 'JWT_SECRET_KEY', 'REDIS_URL']
       missing = [var for var in required_vars if not os.getenv(var)]
       if missing:
           raise ConfigurationError(f"Missing required variables: {missing}")
   ```

## Configuration Migration

### Version Compatibility

When upgrading ActiveLog versions, configuration may need migration:

```bash
# Check configuration compatibility
./scripts/check-config-version.sh --target-version 2.0.0

# Migrate configuration
./scripts/migrate-config.sh --from-version 1.5.0 --to-version 2.0.0

# Validate migrated configuration
./scripts/validate-config.sh --version 2.0.0
```

### Breaking Changes

Major version upgrades may include breaking configuration changes:

| Version | Changes | Migration Required |
|---------|---------|-------------------|
| v2.0.0 | Database connection string format changed | Yes |
| v1.5.0 | New required JWT configuration | Yes |
| v1.4.0 | Redis configuration restructured | Yes |
| v1.3.0 | Added AI service configuration | No |

## Troubleshooting Configuration Issues

### Common Issues

1. **Service won't start**
   ```bash
   # Check configuration syntax
   ./scripts/validate-config.sh
   
   # Test database connection
   ./scripts/test-db-connection.sh
   
   # Verify all required variables are set
   ./scripts/check-required-vars.sh
   ```

2. **Authentication failures**
   ```bash
   # Verify JWT configuration
   grep JWT .env
   
   # Check secret key format
   python -c "import os; print(len(os.getenv('JWT_SECRET_KEY', '')))"
   ```

3. **Performance issues**
   ```bash
   # Check resource limits
   docker stats
   
   # Review pool configurations
   grep POOL .env
   
   # Monitor connection usage
   ./scripts/monitor-connections.sh
   ```

### Debug Configuration

Enable configuration debugging to troubleshoot issues:

```bash
# Enable config debugging
export CONFIG_DEBUG=true
export LOG_LEVEL=DEBUG

# Start service with debug logging
docker-compose up auth-service
```

### Configuration Backup and Recovery

```bash
# Backup current configuration
./scripts/backup-config.sh --output config-backup-$(date +%Y%m%d).tar.gz

# Restore from backup
./scripts/restore-config.sh --input config-backup-20240101.tar.gz

# Compare configurations
./scripts/diff-config.sh current.env backup.env
```

## Getting Help

### Resources

- **Documentation**: Each configuration section has detailed documentation
- **Examples**: See `config/examples/` for sample configurations
- **Templates**: Use `config/templates/` for starting points
- **Validation**: Run `./scripts/validate-config.sh` for syntax checking

### Support Channels

- **GitHub Issues**: Configuration-related bugs and questions
- **Discord**: Real-time help with configuration
- **Email**: support@activelog.com for enterprise configuration support
- **Documentation**: Updates and improvements welcome via PRs

### Configuration Checklist

Before deploying to production:

- [ ] All secrets are environment variables (not hardcoded)
- [ ] Configuration syntax is valid
- [ ] Required variables are set
- [ ] Database connections work
- [ ] Cache connections work
- [ ] External API keys are valid
- [ ] Resource limits are appropriate
- [ ] Monitoring is configured
- [ ] Backups are configured
- [ ] Security settings are production-ready

---

*This configuration guide is actively maintained. For the latest updates, see the [ActiveLog documentation repository](https://github.com/activelog/activelog/tree/main/docs).*