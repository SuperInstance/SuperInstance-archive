# ActiveLog Batch Import Service

A comprehensive file import and processing service that monitors designated import folders, processes files in chunks to avoid memory issues, extracts metadata, generates thumbnails, and manages duplicate detection with MinIO storage integration.

## Features

- **File Monitoring**: Real-time monitoring of import queue using watchdog
- **Chunked Processing**: Memory-efficient file processing with configurable chunk sizes
- **Metadata Extraction**: 
  - EXIF data from images
  - ID3 tags from audio files
  - Video metadata using ffmpeg
  - Document properties from PDFs and Office files
- **Thumbnail Generation**: 
  - Multiple sizes for images using Pillow
  - Video frame extraction using ffmpeg
- **Duplicate Detection**: SHA256 hash-based duplicate detection
- **MinIO Integration**: Organized file storage with proper path structure
- **Import Reporting**: Detailed JSON/CSV reports with success/failure statistics
- **RESTful API**: Comprehensive FastAPI-based REST API
- **Background Processing**: Asynchronous batch processing with configurable workers

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install system dependencies:
```bash
# For image processing
sudo apt-get install libjpeg-dev libpng-dev

# For video processing (optional)
sudo apt-get install ffmpeg

# For audio metadata
sudo apt-get install libmagic1
```

3. Configure environment variables in `.env`:
```env
# Service Configuration
BATCH_IMPORT_API_HOST=0.0.0.0
BATCH_IMPORT_API_PORT=8004
BATCH_IMPORT_DEBUG=false

# Import Configuration
BATCH_IMPORT_IMPORT_QUEUE_PATH=/home/activeloguser/activelog/import-queue
BATCH_IMPORT_PROCESSING_CHUNK_SIZE=1048576
BATCH_IMPORT_MAX_FILE_SIZE=5368709120

# MinIO Configuration
BATCH_IMPORT_MINIO_ENDPOINT=localhost:9000
BATCH_IMPORT_MINIO_ACCESS_KEY=minioadmin
BATCH_IMPORT_MINIO_SECRET_KEY=minioadmin
BATCH_IMPORT_MINIO_BUCKET_NAME=activelog-imports

# Database Configuration
BATCH_IMPORT_DATABASE_URL=postgresql://activeloguser:SecurePass123!@localhost:5432/activelog

# Processing Configuration
BATCH_IMPORT_BATCH_SIZE=10
BATCH_IMPORT_CONCURRENT_WORKERS=3
BATCH_IMPORT_ENABLE_DUPLICATE_DETECTION=true
```

## Usage

### Start the Service

```bash
python main.py
```

The service will start on port 8004 and begin monitoring the import queue directory.

### API Endpoints

#### Health and Status
- `GET /health` - Service health check
- `GET /api/v1/monitor/status` - Import monitor status
- `GET /api/v1/stats` - Comprehensive service statistics
- `GET /api/v1/config` - Service configuration

#### Monitor Control
- `POST /api/v1/monitor/start` - Start import monitoring
- `POST /api/v1/monitor/stop` - Stop import monitoring

#### Processing
- `POST /api/v1/process/trigger` - Manually trigger batch processing
- `GET /api/v1/batches` - Get recent batch information
- `GET /api/v1/batches/{batch_id}` - Get detailed batch information
- `POST /api/v1/batches/{batch_id}/retry` - Retry failed files in a batch

#### Reports
- `POST /api/v1/reports/{batch_id}?format=json|csv` - Generate batch report
- `GET /api/v1/reports` - Get list of recent reports
- `DELETE /api/v1/reports/cleanup?days=30` - Clean up old reports

### Using the Import Queue

1. **Drop files** into the import queue directory: `/home/activeloguser/activelog/import-queue/`

2. **Supported formats**:
   - **Images**: jpg, jpeg, png, gif, bmp, tiff, webp, heic
   - **Videos**: mp4, avi, mov, mkv, wmv, flv, webm, m4v
   - **Audio**: mp3, wav, flac, aac, ogg, m4a, wma
   - **Documents**: pdf, doc, docx, xls, xlsx, ppt, pptx, txt

3. **File Processing Flow**:
   - Files are detected by the monitor
   - Stability check ensures files are completely uploaded
   - Files are batched for processing
   - Metadata is extracted and thumbnails generated
   - Files are uploaded to MinIO with organized paths
   - Duplicate detection prevents redundant storage
   - Processing reports are generated

## Configuration

### File Processing Settings
- `PROCESSING_CHUNK_SIZE`: Chunk size for reading files (default: 1MB)
- `MAX_FILE_SIZE`: Maximum file size allowed (default: 5GB)
- `BATCH_SIZE`: Number of files per processing batch (default: 10)
- `CONCURRENT_WORKERS`: Number of concurrent processing workers (default: 3)

### Thumbnail Settings
- `THUMBNAIL_SIZES`: List of thumbnail dimensions (default: [(150,150), (300,300), (800,600)])
- `THUMBNAIL_QUALITY`: JPEG quality for thumbnails (default: 85)
- `VIDEO_THUMBNAIL_TIME`: Time in seconds for video thumbnail extraction (default: 5)

### File Stability
- `FILE_STABILITY_TIMEOUT`: Seconds to wait for file stability (default: 30)
- `FILE_CHECK_INTERVAL`: Interval between stability checks (default: 5)

## Architecture

### Core Components

1. **Import Monitor** (`services/import_monitor.py`)
   - Watches import queue directory using watchdog
   - Implements file stability detection
   - Manages file batching for processing

2. **Batch Processor** (`services/batch_processor.py`)
   - Processes files with chunked reading
   - Manages concurrent processing with semaphores
   - Handles retries and error recovery

3. **Metadata Extractor** (`services/metadata_extractor.py`)
   - Extracts EXIF from images using Pillow
   - Extracts ID3 tags from audio using mutagen
   - Extracts video metadata using ffmpeg-python
   - Extracts document properties using PyPDF2 and zipfile

4. **Thumbnail Generator** (`services/thumbnail_generator.py`)
   - Generates multiple thumbnail sizes for images
   - Extracts video frames using ffmpeg
   - Handles format conversion and optimization

5. **MinIO Client** (`services/minio_client.py`)
   - Manages file uploads to MinIO object storage
   - Organizes files with date-based directory structure
   - Generates presigned URLs for file access

6. **Report Service** (`services/report_service.py`)
   - Generates comprehensive batch reports
   - Supports JSON and CSV formats
   - Includes detailed error analysis and statistics

### Database Schema

The service uses PostgreSQL with the following tables:

- `import_batches`: Batch processing information
- `import_files`: Individual file processing records
- `file_hashes`: Hash-based duplicate detection

## Monitoring and Troubleshooting

### Logs
- Structured logging using structlog
- Configurable log levels and formats
- JSON output for production environments

### Statistics
- Real-time processing statistics via `/api/v1/stats`
- Monitor file counts, processing rates, and error rates
- Database and MinIO connection status

### Error Handling
- Comprehensive error categorization in reports
- Automatic retry mechanisms for failed files
- Graceful handling of unsupported file types

## Development

### Running Tests
```bash
pytest tests/
```

### Code Structure
```
batch-import/
├── core/               # Configuration and logging
├── services/           # Core processing services
├── api/               # FastAPI routes and models
├── models/            # Pydantic models
├── main.py            # Application entry point
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

### Adding New File Types
1. Add extension to supported formats in `core/config.py`
2. Implement metadata extraction in `services/metadata_extractor.py`
3. Add thumbnail generation if applicable in `services/thumbnail_generator.py`

## Performance Tuning

### Memory Usage
- Adjust `PROCESSING_CHUNK_SIZE` for memory vs. speed tradeoff
- Configure `CONCURRENT_WORKERS` based on available CPU cores
- Monitor batch sizes to prevent memory exhaustion

### Processing Speed
- Increase `CONCURRENT_WORKERS` for CPU-bound operations
- Optimize `BATCH_SIZE` for I/O throughput
- Consider SSD storage for import queue and processing directories

### Network Optimization
- Configure MinIO endpoint for optimal network performance
- Use MinIO distributed mode for high availability
- Monitor MinIO bucket policies and access patterns

## Security Considerations

- Configure MinIO access keys securely
- Use environment variables for sensitive configuration
- Implement proper file validation and sanitization
- Monitor for malicious file uploads
- Configure appropriate CORS policies for production

## License

This service is part of the ActiveLog platform. See main project license for details.