# ActiveLog Video Processing Pipeline

A comprehensive, production-ready video processing pipeline service for ActiveLog.ai that provides advanced video analysis, transcoding, and AI-powered insights.

## Features

### Core Video Processing
- **Video Validation**: Comprehensive file validation with corruption detection and security scanning
- **Multi-format Transcoding**: Support for MP4, WebM with multiple resolutions and quality settings
- **Thumbnail Generation**: Automatic thumbnail extraction at configurable intervals
- **Video Optimization**: Web-optimized encoding with streaming support

### AI-Powered Analysis
- **Scene Detection**: Automatic scene segmentation with visual analysis
- **Object Detection**: YOLO-based object recognition and tracking
- **Face Detection**: Face identification with attribute analysis
- **OCR Processing**: Text extraction from video frames with multi-language support
- **Speech-to-Text**: Whisper-based audio transcription with sentiment analysis
- **Content Classification**: Automatic categorization and rating

### Advanced Features
- **Async Processing**: NATS-based message queue for scalable processing
- **Distributed Workers**: Multi-worker architecture for parallel processing
- **Cloud Storage**: MinIO integration for scalable file storage
- **Search Integration**: Elasticsearch indexing for content discovery
- **Monitoring**: Prometheus metrics and comprehensive health checks
- **API Gateway Integration**: Seamless integration with ActiveLog services

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│  Video Pipeline  │────│   Workers Pool  │
│     (8088)      │    │      (8004)      │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
            ┌───────▼───┐  ┌────▼────┐  ┌───▼────┐
            │   NATS    │  │  MinIO  │  │ Postgres│
            │ (Queue)   │  │(Storage)│  │  (DB)   │
            └───────────┘  └─────────┘  └────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- Redis, PostgreSQL, MinIO, Elasticsearch, NATS (via ActiveLog infrastructure)

### Installation

1. **Clone and navigate**:
   ```bash
   cd ~/activelog/services/video-pipeline
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Build and start**:
   ```bash
   docker-compose up -d
   ```

4. **Verify health**:
   ```bash
   curl http://localhost:8004/health
   ```

### API Usage

#### Upload Video
```bash
curl -X POST "http://localhost:8004/api/videos/upload" \
  -F "video_file=@/path/to/video.mp4" \
  -F "title=My Video" \
  -F "user_id=user123" \
  -F "enable_analysis=true"
```

#### Check Status
```bash
curl "http://localhost:8004/api/videos/{video_id}/status"
```

#### Request Analysis
```bash
curl -X POST "http://localhost:8004/api/videos/{video_id}/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_types": ["comprehensive"],
    "priority": 1
  }'
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8004 | API server port |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | - | Redis connection string |
| `MINIO_ENDPOINT` | - | MinIO server endpoint |
| `NATS_URL` | - | NATS server URL |
| `MAX_FILE_SIZE_MB` | 2048 | Maximum upload size |
| `ENABLE_SCENE_DETECTION` | true | Enable scene analysis |
| `ENABLE_OBJECT_DETECTION` | true | Enable object detection |
| `WHISPER_MODEL` | base | Whisper model size |

### Processing Options

**Transcoding Settings**:
- Formats: MP4, WebM
- Resolutions: 480p, 720p, 1080p
- Quality presets: fast, medium, slow

**Analysis Settings**:
- Scene detection threshold: 0.3
- Object detection confidence: 0.5
- OCR confidence threshold: 0.6
- Supported languages: EN, ES, FR, DE, IT

## API Documentation

### Core Endpoints

#### Video Management
- `POST /api/videos/upload` - Upload video file
- `GET /api/videos/{id}` - Get video information  
- `GET /api/videos/{id}/status` - Get processing status
- `GET /api/videos` - List videos with filtering

#### Processing Operations
- `POST /api/videos/{id}/transcode` - Request transcoding
- `POST /api/videos/{id}/analyze` - Request analysis
- `GET /api/jobs/{id}` - Get job status

#### System Operations
- `GET /health` - Basic health check
- `GET /health/detailed` - Comprehensive health check
- `GET /metrics` - Prometheus metrics
- `GET /api/status` - Service statistics

### WebSocket Events

Connect to `ws://localhost:8004/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8004/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Processing update:', data);
};
```

## Integration with ActiveLog Services

### Authentication
Integrates with ActiveLog auth service for user validation and permission checks.

### Metadata Service
Automatically creates searchable metadata records and content embeddings.

### AI Orchestrator
Routes complex AI analysis tasks through the centralized orchestrator.

### File Sync
Monitors file changes and triggers reprocessing when needed.

## Monitoring and Observability

### Health Checks
- System resource monitoring (CPU, memory, disk)
- Database connectivity
- Message queue status
- External service health
- Processing capacity assessment

### Metrics (Prometheus)
- `video_uploads_total` - Total uploads by status
- `video_processing_duration_seconds` - Processing time by operation
- `active_jobs` - Current processing jobs
- `system_cpu_usage_percent` - System CPU usage
- `queue_size` - Message queue sizes

### Logging
Structured JSON logging with correlation IDs for request tracking.

## Performance and Scaling

### Resource Requirements

**Minimum**:
- CPU: 2 cores
- Memory: 4GB
- Storage: 50GB
- Network: 1Gbps

**Recommended**:
- CPU: 4+ cores
- Memory: 8GB+
- Storage: 500GB+ SSD
- GPU: Optional for ML acceleration

### Scaling Options

1. **Horizontal Worker Scaling**:
   ```bash
   docker-compose up --scale video-worker-1=3 --scale video-worker-2=3
   ```

2. **Resource Optimization**:
   - Adjust transcoding quality settings
   - Configure analysis intervals
   - Tune worker concurrency

3. **Storage Optimization**:
   - Implement file compression
   - Configure retention policies
   - Use CDN for delivery

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8004
```

### Testing
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Quality
```bash
# Format code
black src/

# Lint
flake8 src/

# Type checking
mypy src/
```

## Troubleshooting

### Common Issues

**High Memory Usage**:
- Reduce concurrent workers
- Lower video processing quality
- Increase swap space

**Slow Processing**:
- Check CPU/GPU utilization
- Verify storage I/O performance
- Monitor network bandwidth

**Failed Jobs**:
- Check worker logs: `docker-compose logs video-worker-1`
- Verify external service connectivity
- Check disk space availability

### Debug Mode
Set `DEBUG=true` in environment for detailed logging and error traces.

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is part of ActiveLog.ai and follows the main project's licensing terms.

## Support

For issues and questions:
- Check the [troubleshooting guide](docs/troubleshooting.md)
- Review [API documentation](docs/api.md)
- Contact the ActiveLog development team