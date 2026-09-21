# Troubleshooting Guide

This comprehensive troubleshooting guide helps you quickly diagnose and resolve common issues with ActiveLog. Issues are organized by category with step-by-step solutions.

## Quick Diagnostic Tools

### Health Check Script
First, run our automated health check to identify issues:

```bash
# From ActiveLog root directory
./scripts/health-check.sh

# Or manual health checks
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Auth Service  
curl http://localhost:8002/health  # Metadata Service
```

### Service Status Check
```bash
# Check Docker services
docker-compose ps

# Check specific service logs
docker-compose logs -f [service-name]

# Check system resources
docker stats

# Check disk space
df -h
```

## Installation & Setup Issues

### Docker Issues

**Problem: Docker services won't start**

```bash
# Check if Docker daemon is running
sudo systemctl status docker

# Check Docker version
docker --version
docker-compose --version

# Restart Docker
sudo systemctl restart docker

# Clear Docker cache if needed
docker system prune -a
```

**Problem: Port conflicts**

```
Error: bind: address already in use
```

Solution:
```bash
# Find what's using the port
lsof -i :8000  # Replace with your port
netstat -tulpn | grep :8000

# Kill the process or change ports in docker-compose.yml
# Edit docker-compose.yml to use different ports
```

**Problem: Out of disk space**

```
Error: no space left on device
```

Solution:
```bash
# Check disk usage
df -h
docker system df

# Clean up Docker
docker system prune -a -f
docker volume prune -f

# Clean up log files
sudo find /var/lib/docker/containers/ -name "*.log" -exec truncate -s 0 {} \;
```

### Database Connection Issues

**Problem: Cannot connect to PostgreSQL**

```
Error: could not connect to server: Connection refused
```

Diagnosis:
```bash
# Check if PostgreSQL container is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection manually
psql postgresql://dev:dev@localhost:5432/activelog_dev
```

Solutions:
```bash
# 1. Restart PostgreSQL
docker-compose restart postgres

# 2. Check connection string in .env
grep POSTGRES .env

# 3. Recreate database (DEV ONLY - loses data!)
docker-compose down
docker volume rm activelog_postgres_data
docker-compose up -d postgres
```

**Problem: Database migration failures**

```
Error: relation "table_name" already exists
```

Solutions:
```bash
# Check migration status
python services/manage.py showmigrations

# Reset migrations (DEV ONLY)
python services/manage.py reset_db
python services/manage.py migrate

# Manual migration rollback
python services/manage.py migrate [app_name] [migration_number]
```

### Redis Connection Issues

**Problem: Redis connection refused**

Diagnosis:
```bash
# Test Redis connection
redis-cli -h localhost -p 6379 ping

# Check Redis container
docker-compose ps redis
docker-compose logs redis
```

Solutions:
```bash
# Restart Redis
docker-compose restart redis

# Clear Redis data (if corrupted)
redis-cli -h localhost -p 6379 FLUSHALL
```

## Service-Specific Issues

### Auth Service Issues

**Problem: JWT token validation failing**

```
Error: 401 Unauthorized - Invalid token
```

Diagnosis:
```bash
# Check JWT secret in environment
grep JWT_SECRET .env

# Check token expiration
# Decode JWT at https://jwt.io (paste your token)

# Test auth endpoint
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "dev@activelog.com", "password": "devpassword"}'
```

Solutions:
```bash
# 1. Refresh your token
curl -X POST http://localhost:8001/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token"}'

# 2. Check system time (JWT is time-sensitive)
date
timedatectl status

# 3. Restart auth service
docker-compose restart auth-service
```

**Problem: User authentication failing**

Check user exists and password is correct:
```bash
# Connect to database
psql postgresql://dev:dev@localhost:5432/activelog_dev

# Check user table
SELECT id, email, is_active FROM users WHERE email = 'your-email@example.com';

# Reset password (development)
UPDATE users SET password_hash = '$2b$12$...' WHERE email = 'your-email@example.com';
```

### File Upload Issues

**Problem: File upload timeout or failure**

```
Error: 504 Gateway Timeout
Error: Request Entity Too Large
```

Solutions:
```bash
# 1. Check file size limits
grep MAX_FILE_SIZE .env
# Default: 100MB per file

# 2. Check available storage
df -h
docker exec activelog_minio_1 df -h

# 3. Check MinIO status
curl http://localhost:9000/minio/health/live

# 4. Increase timeout in nginx config
# Edit nginx/nginx.conf:
# client_max_body_size 500M;
# proxy_read_timeout 300s;
```

**Problem: Files not appearing after upload**

Diagnosis:
```bash
# Check file processing queue
curl http://localhost:8000/admin/queue-status

# Check MinIO storage
curl -X GET http://localhost:9000/activelog-dev/

# Check metadata service logs
docker-compose logs metadata-service
```

### Search Issues

**Problem: Search returns no results**

```
Error: Search returned 0 results for "known filename"
```

Diagnosis:
```bash
# Check Elasticsearch status
curl http://localhost:9200/_cluster/health

# Check indices
curl http://localhost:9200/_cat/indices?v

# Check if files are indexed
curl "http://localhost:9200/files/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match_all": {}}}'
```

Solutions:
```bash
# 1. Restart Elasticsearch
docker-compose restart elasticsearch

# 2. Reindex files
curl -X POST http://localhost:8002/admin/reindex-all

# 3. Check indexing queue
curl http://localhost:8002/admin/indexing-status
```

**Problem: Slow search performance**

Solutions:
```bash
# 1. Check Elasticsearch performance
curl http://localhost:9200/_nodes/stats/indices/search

# 2. Clear query cache
curl -X POST http://localhost:9200/_cache/clear

# 3. Check available memory
free -h
docker stats elasticsearch
```

## Performance Issues

### Slow Response Times

**Diagnosis**:
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Monitor service performance
docker stats

# Check database query performance
tail -f logs/postgres.log | grep "duration"
```

**Solutions**:
```bash
# 1. Increase service resources
# Edit docker-compose.yml:
# mem_limit: 1g
# cpus: 2

# 2. Enable Redis caching
grep CACHE_ENABLED .env

# 3. Check for memory leaks
docker stats --no-stream
```

### High Memory Usage

**Diagnosis**:
```bash
# Check memory usage by service
docker stats --no-stream

# Check system memory
free -h
top -p $(pgrep -f "activelog")
```

**Solutions**:
```bash
# 1. Restart high-memory services
docker-compose restart [service-name]

# 2. Reduce batch sizes
grep BATCH_SIZE .env

# 3. Enable memory limits
# Edit docker-compose.yml to add memory limits
```

### High CPU Usage

**Common Causes**:
- Large file processing
- Heavy search queries  
- Infinite loops in code
- Insufficient caching

**Solutions**:
```bash
# 1. Check processing queues
curl http://localhost:8000/admin/queue-status

# 2. Limit concurrent processing
grep WORKER_CONCURRENCY .env

# 3. Profile CPU usage
docker exec -it activelog_api-gateway_1 top
```

## Network & Connectivity Issues

### Service Discovery Issues

**Problem: Services can't communicate**

```
Error: Service 'auth-service' not found
Error: Connection refused to metadata-service:8002
```

Diagnosis:
```bash
# Check Docker network
docker network ls
docker network inspect activelog_default

# Test service connectivity
docker exec activelog_api-gateway_1 ping auth-service
docker exec activelog_api-gateway_1 nslookup metadata-service
```

Solutions:
```bash
# 1. Recreate Docker network
docker-compose down
docker network prune
docker-compose up

# 2. Check service names in docker-compose.yml
# Ensure consistent naming

# 3. Use service discovery URLs
# http://service-name:port instead of localhost
```

### External API Issues

**Problem: Cannot connect to external APIs**

```
Error: Failed to connect to api.openai.com
Error: DNS resolution failed
```

Solutions:
```bash
# 1. Check DNS resolution
nslookup api.openai.com
dig api.openai.com

# 2. Check firewall/proxy settings
curl -v https://api.openai.com

# 3. Test from container
docker exec activelog_ai-orchestrator_1 curl https://api.openai.com

# 4. Check API keys
grep OPENAI_API_KEY .env
```

## Data & Storage Issues

### Database Issues

**Problem: Database corruption**

```
Error: index "idx_name" is corrupted
Error: could not read block in file
```

Solutions:
```bash
# 1. Check database integrity
psql postgresql://dev:dev@localhost:5432/activelog_dev
# Run: VACUUM FULL;
# Run: REINDEX DATABASE activelog_dev;

# 2. Backup and restore (if corruption is severe)
pg_dump activelog_dev > backup.sql
# Recreate database and restore from backup

# 3. Check disk space and permissions
df -h
ls -la data/postgres/
```

**Problem: Slow database queries**

Diagnosis:
```sql
-- Enable query logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
SELECT pg_reload_conf();

-- Find slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

Solutions:
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_files_created_at ON files(created_at);
CREATE INDEX CONCURRENTLY idx_files_user_id ON files(user_id);

-- Update statistics
ANALYZE;

-- Vacuum tables
VACUUM ANALYZE files;
```

### File Storage Issues

**Problem: MinIO/S3 storage errors**

```
Error: Access Denied
Error: Bucket does not exist
```

Solutions:
```bash
# 1. Check MinIO credentials
grep MINIO .env

# 2. Create missing bucket
curl -X PUT http://localhost:9000/activelog-dev \
  -H "Authorization: AWS4-HMAC-SHA256 ..."

# 3. Fix permissions
docker exec activelog_minio_1 mc policy set public activelog-dev

# 4. Check storage space
docker exec activelog_minio_1 df -h
```

## Security Issues

### Authentication Problems

**Problem: CORS errors in browser**

```
Error: Access to XMLHttpRequest blocked by CORS policy
```

Solutions:
```python
# Fix CORS configuration in backend
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Problem: SSL/TLS certificate errors**

```
Error: certificate verify failed
Error: SSL handshake failed
```

Solutions:
```bash
# 1. For development, disable SSL verification
export PYTHONHTTPSVERIFY=0

# 2. Update certificate store
sudo apt-get update && sudo apt-get install ca-certificates

# 3. Use HTTP for local development
# Edit configuration to use http:// instead of https://
```

### Permission Issues

**Problem: File access denied**

```
Error: Permission denied
Error: Insufficient privileges
```

Solutions:
```bash
# 1. Check file permissions
ls -la data/
ls -la logs/

# 2. Fix ownership
sudo chown -R $USER:$USER data/
sudo chmod -R 755 data/

# 3. Check Docker user mapping
grep -r "user:" docker-compose.yml
```

## Mobile & Sync Issues

### Mobile App Issues

**Problem: App won't connect to server**

Solutions:
```bash
# 1. Check mobile device can reach server
# From mobile device browser: http://your-server-ip:8000/health

# 2. Update mobile API configuration
# Check mobile-api service configuration

# 3. Check firewall rules
sudo ufw status
sudo iptables -L
```

**Problem: Sync conflicts**

```
Error: Sync conflict detected
Error: File modified on both devices
```

Solutions:
```bash
# 1. View conflict resolution options
curl http://localhost:8017/sync/conflicts

# 2. Resolve conflicts manually
curl -X POST http://localhost:8017/sync/resolve \
  -H "Content-Type: application/json" \
  -d '{"conflict_id": "123", "resolution": "keep_both"}'

# 3. Reset sync (last resort)
curl -X POST http://localhost:8017/sync/reset-device \
  -H "Authorization: Bearer $TOKEN"
```

## Monitoring & Observability

### Log Analysis

**Find errors in logs**:
```bash
# Search for errors across all services
docker-compose logs | grep -i error

# Search for specific error patterns
docker-compose logs | grep "500\|timeout\|connection refused"

# Monitor logs in real-time
docker-compose logs -f --tail=100

# Export logs for analysis
docker-compose logs > activelog-logs-$(date +%Y%m%d).txt
```

**Structured log analysis**:
```bash
# Filter by service
docker-compose logs auth-service | grep ERROR

# Filter by time (if using timestamps)
docker-compose logs --since="2024-01-01T10:00:00"

# Follow logs from specific time
docker-compose logs -f --since="1h"
```

### Metrics & Monitoring

**Check Prometheus metrics**:
```bash
# Service health metrics
curl http://localhost:9090/api/v1/query?query=up

# Response time metrics
curl http://localhost:9090/api/v1/query?query=http_request_duration_seconds

# Memory usage
curl http://localhost:9090/api/v1/query?query=process_resident_memory_bytes
```

**Check Grafana dashboards**:
- Open http://localhost:3001 (admin/admin)
- View system overview dashboard
- Check service-specific dashboards
- Set up alerts for critical metrics

## Emergency Procedures

### Complete System Reset

**⚠️ WARNING: This will delete ALL data!**

```bash
# Stop all services
docker-compose down

# Remove all volumes and networks
docker system prune -a -f --volumes

# Remove local data
sudo rm -rf data/ logs/

# Restart from scratch
cp .env.example .env
# Edit .env with your configuration
./scripts/dev-setup.sh
```

### Backup & Recovery

**Create emergency backup**:
```bash
# Backup databases
./scripts/backup-databases.sh

# Backup file storage
docker exec activelog_minio_1 tar czf /backup/files-$(date +%Y%m%d).tar.gz /data

# Backup configuration
tar czf config-backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

**Restore from backup**:
```bash
# Restore database
psql activelog_dev < backup-20240101.sql

# Restore files
docker exec -i activelog_minio_1 tar xzf - -C /data < files-20240101.tar.gz
```

## Getting Additional Help

### Self-Service Options

1. **Check Documentation**: Each service has detailed README files
2. **Search Issues**: GitHub issues and discussions
3. **Community Forum**: Stack Overflow with `activelog` tag
4. **Status Page**: https://status.activelog.com

### Support Channels

**Community Support** (Free):
- GitHub Issues: Bug reports and feature requests
- Discord: Real-time community chat
- Stack Overflow: Technical questions

**Professional Support** (Paid):
- Email: support@activelog.com
- Phone: 1-800-ACTIVELOG (enterprise customers)
- Slack Connect: Priority support channel

### Reporting Bugs

**Bug Report Template**:
```markdown
## Environment
- ActiveLog Version: [version]
- Operating System: [OS and version]  
- Docker Version: [version]
- Browser: [if web-related]

## Expected Behavior
[What should happen]

## Actual Behavior  
[What actually happens]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [And so on...]

## Logs/Screenshots
[Include relevant logs or screenshots]

## Additional Context
[Any other relevant information]
```

### Performance Troubleshooting Template

```markdown
## Performance Issue Report

### Symptoms
- [ ] Slow response times (>5 seconds)
- [ ] High CPU usage (>80%)
- [ ] High memory usage (>80%)
- [ ] Database timeout errors
- [ ] File upload failures

### Environment Info
- Number of users: [count]
- Data size: [GB/TB]
- Request volume: [requests/minute]
- Hardware specs: [CPU/RAM/Storage]

### Measurements
- Response time: [milliseconds]
- Throughput: [requests/second]
- Error rate: [percentage]
- Resource utilization: [percentages]

### Attempted Solutions
- [ ] Restarted services
- [ ] Cleared caches  
- [ ] Optimized queries
- [ ] Scaled resources
```

---

**Remember**: Most issues can be resolved by restarting the problematic service. When in doubt, try a service restart first, then escalate to more complex solutions.

For urgent issues affecting production systems, contact support immediately at support@activelog.com or call our emergency hotline.

*This troubleshooting guide is continuously updated based on common user issues. If you solve an issue not covered here, please contribute the solution back to help others.*