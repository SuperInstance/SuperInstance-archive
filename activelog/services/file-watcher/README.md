# ActiveLog File Watcher Service

A high-performance file monitoring service that watches directories for changes and queues events for synchronization.

## Features

- **Real-time File Monitoring**: Uses inotify (via watchdog) to monitor file system changes
- **Smart Ignore Patterns**: Supports .gitignore style patterns for filtering files
- **Event Debouncing**: Prevents duplicate events during rapid file changes
- **Batch Processing**: Efficiently handles large imports and high-frequency changes
- **Multiple Queue Backends**: NATS JetStream, Redis, and local fallback
- **Comprehensive Monitoring**: Health checks, metrics, and system monitoring
- **Throttling**: Prevents system overload during bulk operations

## Quick Start

### Using Docker Compose

```bash
# Create required directories
mkdir -p /tmp/activelog-test /tmp/activelog-downloads

# Start the service stack
docker-compose up -d

# Check service health
curl http://localhost:8005/health
```

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export WATCH_DIRECTORIES="/path/to/watch"
export NATS_URL="nats://localhost:4222"
export REDIS_HOST="localhost"

# Run the service
python main.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCH_DIRECTORIES` | `/tmp/activelog-test` | Comma-separated list of directories to watch |
| `WATCH_RECURSIVE` | `true` | Watch subdirectories recursively |
| `INCLUDE_PATTERNS` | - | Comma-separated include patterns |
| `EXCLUDE_PATTERNS` | - | Comma-separated exclude patterns |
| `BATCH_SIZE` | `100` | Number of events per batch |
| `BATCH_TIMEOUT` | `5` | Batch timeout in seconds |
| `DEBOUNCE_DELAY` | `1` | Debounce delay in seconds |
| `MAX_EVENTS_PER_SECOND` | `1000` | Rate limiting threshold |
| `NATS_URL` | `nats://localhost:4222` | NATS server URL |
| `REDIS_HOST` | `localhost` | Redis server host |
| `SYNC_ENGINE_URL` | `http://localhost:8004` | Sync engine URL |

### Ignore Patterns

The service supports .gitignore style patterns:

- Global patterns in configuration
- Directory-specific `.activelog-ignore` files
- Automatic `.gitignore` file loading
- Runtime pattern management via API

## API Endpoints

### Health & Monitoring

- `GET /health` - Basic health check
- `GET /monitoring/health-check` - Detailed health check
- `GET /monitoring/detailed` - Comprehensive monitoring data
- `GET /monitoring/system` - System metrics
- `GET /stats` - Service statistics
- `GET /metrics` - Prometheus-style metrics

### Directory Management

- `POST /watch/add` - Add directory to watch
- `DELETE /watch/remove` - Remove directory from watch
- `GET /watch/directories` - List watched directories

### Pattern Management

- `POST /ignore/add` - Add ignore pattern
- `DELETE /ignore/remove` - Remove ignore pattern
- `GET /ignore/patterns` - List ignore patterns

### Batch Operations

- `POST /import/batch` - Start batch directory import
- `GET /import/stats` - Get import statistics
- `POST /rescan` - Force directory rescan

### Queue Management

- `POST /queue/flush` - Flush local queue
- `POST /queue/reconnect` - Reconnect to external queues

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   File System   │───▶│ File Watcher │───▶│ Event Queue │
└─────────────────┘    └──────────────┘    └─────────────┘
                              │                     │
                              ▼                     ▼
                       ┌──────────────┐    ┌─────────────┐
                       │   Debouncer  │    │ NATS/Redis  │
                       └──────────────┘    └─────────────┘
                              │                     │
                              ▼                     ▼
                       ┌──────────────┐    ┌─────────────┐
                       │    Batcher   │    │ Sync Engine │
                       └──────────────┘    └─────────────┘
```

### Components

1. **File Watcher**: Core monitoring using watchdog library
2. **Ignore Manager**: Pattern-based filtering system
3. **Event Debouncer**: Prevents duplicate events
4. **Batch Processor**: Groups events for efficiency
5. **Event Queue**: Multi-backend event delivery
6. **Throttle Controller**: Rate limiting and system protection

## Performance

### Benchmarks

- **Events/second**: Up to 10,000 events/second
- **Memory usage**: ~50MB baseline + 1KB per pending event
- **Latency**: <100ms event detection to queue
- **Batch efficiency**: 99%+ deduplication during rapid changes

### Tuning

```bash
# High throughput
BATCH_SIZE=1000
BATCH_TIMEOUT=1
MAX_EVENTS_PER_SECOND=10000

# Low latency
BATCH_SIZE=50
BATCH_TIMEOUT=0.5
DEBOUNCE_DELAY=0.1

# Large imports
BATCH_SIZE=2000
MAX_EVENTS_PER_SECOND=5000
```

## Integration

### Sync Engine

Events are automatically forwarded to the sync engine:

```json
{
  "file_path": "/path/to/file.txt",
  "event_type": "modified",
  "metadata": {
    "file_size": 1024,
    "file_hash": "sha256...",
    "detected_at": "2024-01-01T12:00:00Z"
  }
}
```

### NATS JetStream

Events are published to the `file.events` subject with persistence and delivery guarantees.

### Monitoring

Prometheus metrics available at `/metrics`:

- `file_watcher_events_processed_total`
- `file_watcher_events_per_second`
- `file_watcher_pending_events`
- `file_watcher_memory_usage_mb`

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Local Development

```bash
# Install in development mode
pip install -e .

# Start with debug logging
LOG_LEVEL=DEBUG python main.py
```

## Troubleshooting

### Common Issues

1. **High memory usage**: Reduce `BATCH_SIZE` and `MAX_QUEUE_SIZE`
2. **Missing events**: Check ignore patterns and permissions
3. **Queue backlog**: Verify NATS/Redis connectivity
4. **Performance issues**: Tune debounce and throttle settings

### Logs

```bash
# View service logs
docker-compose logs -f file-watcher

# Check specific issues
grep "ERROR\|WARNING" /var/log/file-watcher/watcher.log
```

### Monitoring

```bash
# Check service health
curl http://localhost:8005/monitoring/health-check

# Get detailed stats
curl http://localhost:8005/monitoring/detailed

# View current configuration
curl http://localhost:8005/config
```