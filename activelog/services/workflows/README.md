# ActiveLog Workflows Service

A comprehensive workflow automation service with IFTTT-style triggers and actions, built with FastAPI and PostgreSQL.

## Features

### ✅ **IFTTT-Style Triggers and Actions**
- **Triggers**: Webhook, Schedule (cron), Event, Manual
- **Actions**: HTTP Request, Email, Slack, Database, File Operations, Webhooks, Conditional Logic, Delays, Custom Scripts
- **Context Management**: Variable passing between steps with templating support
- **Retry Logic**: Configurable retries with exponential backoff

### ✅ **Zapier-Compatible Webhook System**
- Secure webhook endpoints with signature verification
- Rate limiting and origin validation
- Zapier-specific response formats and sample data
- Request/response logging and analytics

### ✅ **Custom Workflow Designer API**
- Visual workflow builder support with REST API
- Workflow validation and testing endpoints
- Step dependency management
- Real-time execution monitoring

### ✅ **Scheduled Workflows (Cron-Style)**
- Full cron expression support with timezone handling
- Missed execution handling and recovery
- Scheduler health monitoring
- Next execution preview

### ✅ **Conditional Logic and Branching**
- 15+ condition operators (equals, contains, regex, etc.)
- Logical operators (AND, OR, NOT)
- Dynamic branching based on previous step results
- Variable interpolation in conditions

### ✅ **External Service Integrations**
- **Built-in Services**: Slack, Email (SMTP), GitHub, Google Sheets
- OAuth2 and API key authentication
- Encrypted credential storage
- Rate limiting per service
- Health monitoring and error handling

### ✅ **Workflow Templates Marketplace**
- Public template marketplace with categories
- Template rating and review system
- One-click template installation
- Version management and updates
- Featured templates and search functionality

## Architecture

```
├── main.py                 # FastAPI server entry point
├── requirements.txt        # Python dependencies
├── src/
│   ├── api/               # REST API routes
│   ├── core/              # Core database and config
│   ├── workflow/          # Workflow engine and execution
│   ├── webhooks/          # Webhook management
│   ├── scheduler/         # Cron-style scheduling
│   ├── integrations/      # External service integrations
│   ├── templates/         # Template marketplace
│   └── middleware/        # Auth and rate limiting
```

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Database**
   ```bash
   # PostgreSQL database required
   createdb workflows_db
   ```

3. **Environment Configuration**
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost:5432/workflows_db"
   export REDIS_URL="redis://localhost:6379/2"
   export SECRET_KEY="your-secret-key"
   ```

4. **Start Service**
   ```bash
   python main.py
   ```

5. **Access API Documentation**
   - Swagger UI: http://localhost:8014/docs
   - ReDoc: http://localhost:8014/redoc

## API Examples

### Create a Workflow
```bash
curl -X POST http://localhost:8014/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Slack Reminder",
    "description": "Send daily standup reminder",
    "owner_id": "user-123",
    "trigger_config": {
      "type": "schedule",
      "config": {
        "cron_expression": "0 9 * * 1-5",
        "timezone": "UTC"
      }
    },
    "actions": [
      {
        "type": "slack",
        "name": "Send Reminder",
        "config": {
          "webhook_url": "https://hooks.slack.com/...",
          "channel": "#standup",
          "text": "Time for standup! 🌅"
        }
      }
    ]
  }'
```

### Execute Workflow Manually
```bash
curl -X POST http://localhost:8014/api/v1/workflows/{workflow_id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_data": {
      "manual_trigger": true,
      "user_id": "user-123"
    }
  }'
```

### Create Webhook Endpoint
```bash
curl -X POST http://localhost:8014/api/v1/workflows/{workflow_id}/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "workflow-123",
    "name": "GitHub Issues Webhook",
    "secret_token": "optional-secret",
    "zapier_compatible": true
  }'
```

### Browse Template Marketplace
```bash
# Get featured templates
curl http://localhost:8014/marketplace/featured

# Search templates
curl "http://localhost:8014/api/v1/templates/search?query=slack&category=communication"

# Install template
curl -X POST http://localhost:8014/api/v1/templates/{template_id}/install \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "customizations": {
      "name": "My Custom Workflow"
    }
  }'
```

## Built-in Templates

The service includes several pre-built templates:

1. **Daily Slack Standup Reminder** - Automated team standup reminders
2. **GitHub Issue to Slack Notification** - Real-time issue notifications
3. **Weekly Report Email** - Automated weekly summary reports
4. **Website Monitor with Alerts** - Uptime monitoring with instant alerts

## Service Endpoints

- **Main API**: `/api/v1/*`
- **Webhooks**: `/webhook/{endpoint_id}`
- **Health Check**: `/health`
- **Metrics**: `/metrics`
- **Documentation**: `/docs`
- **Marketplace**: `/marketplace/*`

## Database Schema

- **workflows** - Workflow definitions and metadata
- **workflow_executions** - Execution history and results  
- **execution_steps** - Individual step execution details
- **webhook_endpoints** - Webhook endpoint configurations
- **integrations** - External service integrations
- **templates** - Template marketplace content
- **scheduled_executions** - Scheduled workflow executions
- **users** - User accounts and settings

## Monitoring and Analytics

The service provides comprehensive monitoring:

- Execution success/failure rates
- Performance metrics and timing
- Integration health status
- Scheduler statistics
- Webhook request analytics
- Template usage statistics

## Security Features

- Request signature verification for webhooks
- Encrypted credential storage for integrations
- Rate limiting on all endpoints
- CORS and origin validation
- Secure template sharing with access controls

## Scalability

The service is designed for scale:

- Async processing with FastAPI
- Background task queues
- Database connection pooling
- Distributed scheduling support
- Horizontal scaling ready

This service provides everything needed for a production-ready workflow automation platform, comparable to services like Zapier, IFTTT, or Microsoft Power Automate!