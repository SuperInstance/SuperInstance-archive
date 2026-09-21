# Auto-Scheduler Service

A comprehensive automation system for intelligent scheduling, backup management, and progress reporting.

## Features

### 🤖 Intelligent Scheduling System
- **5-hour limit tracking per bot** - Automatic monitoring of bot usage limits
- **Automatic throttling near limits** - Smart resource management to prevent overuse
- **Night-time acceleration (3am default)** - 2x capacity during off-peak hours
- **Task priority queue** - Priority-based task scheduling
- **Deadline management** - Automatic deadline tracking and prioritization
- **Resource reservation** - Advanced resource allocation system
- **Maintenance windows** - Configurable maintenance scheduling

### 💾 Comprehensive Backup System
- **Nightly incremental backups** - Efficient differential backups
- **Weekly stability snapshots** - Regular system state captures
- **Monthly milestone saves** - Long-term project milestones
- **6-month archives** - Extended retention for compliance
- **Yearly permanent copies** - Long-term archival storage
- **Intelligent version selection** - Smart backup selection algorithms
- **Rollback automation** - Automated recovery procedures
- **Backup verification** - Integrity checking and validation
- **Space optimization** - Compression and deduplication
- **Cloud sync support** - Optional cloud storage integration

### 📊 Advanced Progress Reporting
- **Minute-by-minute updates** - Real-time system monitoring
- **Hourly summaries** - Aggregated performance metrics
- **Daily reports** - Comprehensive system analysis
- **Task completion logs** - Detailed task tracking
- **Performance analytics** - Bot efficiency and system utilization
- **Cost reports** - Financial tracking and optimization
- **Bot efficiency metrics** - Individual bot performance analysis
- **Recommendation engine** - AI-driven optimization suggestions

## Architecture

```
auto-scheduler/
├── src/
│   ├── scheduler/
│   │   ├── bot_manager.py      # Bot management and resource allocation
│   │   └── scheduler.py        # Main scheduling orchestrator
│   ├── backup/
│   │   └── backup_manager.py   # Backup system implementation
│   ├── reporting/
│   │   └── progress_tracker.py # Analytics and reporting
│   └── utils/
│       ├── config.py           # Configuration management
│       └── logging_setup.py    # Logging configuration
├── config/
│   └── config.yaml            # Service configuration
├── data/                      # Database and persistent data
├── logs/                      # Service logs
├── backups/                   # Backup storage
├── main.py                    # FastAPI service entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container configuration
├── start.sh                   # Service startup script
└── stop.sh                    # Service shutdown script
```

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   cd ~/activelog/services/auto-scheduler
   pip3 install -r requirements.txt
   ```

2. **Start the Service**
   ```bash
   ./start.sh
   ```

3. **Access the API**
   - Service URL: http://localhost:8500
   - API Documentation: http://localhost:8500/docs
   - Health Check: http://localhost:8500/health

### Docker Deployment

1. **Using Docker Compose** (from activelog root)
   ```bash
   docker-compose up auto-scheduler
   ```

2. **Direct Docker Build**
   ```bash
   cd services/auto-scheduler
   docker build -t auto-scheduler .
   docker run -p 8500:8500 auto-scheduler
   ```

## Configuration

The service is configured via `config/config.yaml`:

```yaml
service:
  port: 8500
  host: 0.0.0.0

bot_manager:
  night_start_hour: 22           # 10 PM
  night_end_hour: 6              # 6 AM  
  night_acceleration_hour: 3     # 3 AM peak
  night_multiplier: 2.0          # 2x capacity
  default_daily_limit: 5.0       # Hours per bot

backup:
  enabled: true
  backup_path: /path/to/backups
  source_path: /path/to/source
  compression: true
  verification: true

reporting:
  cost_per_bot_hour: 0.50        # $0.50 per hour
  report_retention_days: 90
```

## API Reference

### Task Management

#### Create Task
```bash
POST /tasks
Content-Type: application/json

{
  "name": "System Maintenance",
  "priority": 2,
  "estimated_duration": 1.5,
  "deadline": "2024-01-15T10:00:00",
  "resource_requirements": {
    "capabilities": ["maintenance"]
  }
}
```

#### Get Task Status
```bash
GET /tasks/{task_id}
```

#### Cancel Task
```bash
DELETE /tasks/{task_id}
```

### Bot Management

#### Add Bot
```bash
POST /bots
Content-Type: application/json

{
  "id": "worker-bot-1",
  "name": "Worker Bot 1",
  "daily_limit_hours": 8.0,
  "capabilities": ["backup", "maintenance"]
}
```

#### List Bots
```bash
GET /bots
```

### Backup Operations

#### Create Backup
```bash
POST /backups
Content-Type: application/json

{
  "backup_type": "milestone",
  "metadata": {
    "description": "Monthly milestone backup"
  }
}
```

#### Get Backup Status
```bash
GET /backups/status
```

### Reporting

#### Progress Report
```bash
GET /reports/progress
```

#### Daily Report
```bash
GET /reports/daily
```

#### Get Recommendations
```bash
GET /reports/recommendations
```

### System Status

#### Health Check
```bash
GET /health
```

#### System Status
```bash
GET /status
```

## Bot Configuration

The system supports multiple bot types with different capabilities:

- **Scheduler Bot**: General scheduling and orchestration
- **Backup Bot**: Specialized backup operations
- **Analytics Bot**: Reporting and analytics
- **Maintenance Bot**: System maintenance and cleanup

Each bot has:
- **Daily hour limits** (default 5 hours)
- **Capability tags** for task matching
- **Performance scoring** for optimization
- **Usage tracking** for cost analysis

## Night-Time Acceleration

The system provides enhanced capacity during off-peak hours:

- **Peak Hours**: 3 AM with 2x multiplier
- **Night Window**: 10 PM - 6 AM
- **Gradual Scaling**: Smooth transition around peak time
- **Cost Efficiency**: Reduced per-hour costs during night operations

## Backup Strategy

### Backup Types

1. **Incremental** (Daily at 1 AM)
   - Only changed files since last backup
   - 7-day retention
   - Fast and efficient

2. **Stability** (Weekly on Sunday at 2 AM)
   - Full system snapshot
   - 4-week retention
   - System stability checkpoints

3. **Milestone** (Monthly on 1st at 3 AM)
   - Complete project milestones
   - 12-month retention
   - Cloud sync enabled

4. **Archive** (Bi-annually in Jan/July)
   - Long-term compliance backups
   - 3-year retention
   - Cloud sync enabled

5. **Permanent** (Yearly in January)
   - Permanent archival storage
   - 50-year retention
   - Cloud sync enabled

### Recovery Procedures

```bash
# List available backups
GET /backups/status

# Restore from backup (via API)
POST /backups/restore
{
  "backup_id": "milestone_20240115_030000",
  "target_path": "/restore/location"
}
```

## Monitoring and Analytics

### Performance Metrics
- Task completion rates
- Bot efficiency scores
- System utilization
- Backup success rates
- Storage growth trends

### Cost Analysis
- Per-bot hourly costs
- Task-type cost breakdown
- Efficiency savings from optimization
- Night-time cost reductions

### Recommendations
- Performance optimization suggestions
- Cost reduction opportunities
- Maintenance scheduling advice
- Resource allocation recommendations

## Troubleshooting

### Common Issues

1. **Service Won't Start**
   ```bash
   # Check logs
   tail -f logs/auto-scheduler.log
   
   # Verify dependencies
   pip3 install -r requirements.txt
   
   # Check port availability
   lsof -i :8500
   ```

2. **Backup Failures**
   ```bash
   # Check backup status
   curl http://localhost:8500/backups/status
   
   # Verify backup path permissions
   ls -la /path/to/backups
   ```

3. **High Resource Usage**
   ```bash
   # Check bot status
   curl http://localhost:8500/bots
   
   # Review recommendations
   curl http://localhost:8500/reports/recommendations
   ```

### Log Locations
- Service logs: `logs/auto-scheduler.log`
- Startup logs: `logs/startup.log`
- Backup logs: `logs/backup.log`

## Development

### Running Tests
```bash
cd tests/
python3 -m pytest
```

### Code Structure
- **FastAPI** for REST API
- **AsyncIO** for concurrent operations
- **SQLite** for data persistence
- **Pydantic** for data validation

### Contributing
1. Follow existing code patterns
2. Add comprehensive logging
3. Include error handling
4. Update documentation
5. Add tests for new features

## License

Part of the ActiveLog.ai system.