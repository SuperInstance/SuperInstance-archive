# Data Export Service

A comprehensive data export service providing multiple export formats, cloud integration, and GDPR-compliant data portability features.

## Features

- **Multiple Export Formats**
  - PDF documents with metadata preservation
  - ZIP and TAR.GZ archives
  - Static website generation
  - Photo books and albums
  - GDPR-compliant data exports

- **Cloud Integration**
  - Google Drive
  - Dropbox
  - Amazon S3 / S3-compatible services

- **Bulk Operations**
  - Batch export processing
  - Progress tracking with real-time updates
  - Job scheduling and management
  - Retry mechanisms and error handling

- **Security & Compliance**
  - GDPR Article 20 compliance
  - Data anonymization options
  - Encryption support
  - Rate limiting and access controls

## Quick Start

### Installation

```bash
cd ~/activelog/services/data-export
npm install
```

### Configuration

Copy the environment template and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

### Start the Service

```bash
npm start
```

The service will be available at `http://localhost:8009`

## API Documentation

### Export Endpoints

#### PDF Export
```http
POST /api/export/pdf
Content-Type: multipart/form-data

Parameters:
- file: Input file (optional)
- data: JSON data to export (optional)
- metadata: Export metadata (JSON string)
- options: PDF options (JSON string)
```

**Example:**
```bash
curl -X POST http://localhost:8009/api/export/pdf \
  -F "data={\"title\":\"My Document\",\"content\":\"Hello World\"}" \
  -F "metadata={\"title\":\"Export Document\",\"author\":\"User\"}" \
  -F "options={\"pageSize\":\"A4\",\"orientation\":\"portrait\"}"
```

#### Archive Export
```http
POST /api/export/archive
Content-Type: multipart/form-data

Parameters:
- files: Multiple files to archive
- format: 'zip' or 'tar.gz' (default: zip)
- metadata: Archive metadata (JSON string)
- options: Archive options (JSON string)
```

**Example:**
```bash
curl -X POST http://localhost:8009/api/export/archive \
  -F "files=@file1.pdf" \
  -F "files=@file2.jpg" \
  -F "format=zip" \
  -F "metadata={\"title\":\"My Archive\"}"
```

#### Website Generation
```http
POST /api/generate/website
Content-Type: application/json

{
  "data": {
    "pages": [...],
    "assets": [...]
  },
  "metadata": {
    "title": "My Website",
    "description": "Generated website"
  },
  "options": {
    "theme": "default",
    "includeSearch": true
  }
}
```

#### Photo Book Generation
```http
POST /api/generate/photobook
Content-Type: multipart/form-data

Parameters:
- photos: Multiple photo files
- metadata: Book metadata (JSON string)
- options: Photo book options (JSON string)
```

**Example:**
```bash
curl -X POST http://localhost:8009/api/generate/photobook \
  -F "photos=@photo1.jpg" \
  -F "photos=@photo2.jpg" \
  -F "metadata={\"title\":\"Family Photos\",\"author\":\"John Doe\"}" \
  -F "options={\"format\":\"A4\",\"theme\":\"classic\",\"layout\":\"grid\"}"
```

#### GDPR Export
```http
POST /api/export/gdpr
Content-Type: application/json

{
  "userData": {
    "personalData": {...},
    "systemData": {...},
    "files": [...]
  },
  "requestDetails": {
    "dataSubjectId": "user123",
    "dataSubjectEmail": "user@example.com",
    "requestType": "data_portability"
  },
  "options": {
    "includeDataProcessingLog": true,
    "anonymizeIdentifiers": false
  }
}
```

### Bulk Export Operations

#### Create Bulk Export Job
```http
POST /api/bulk/export
Content-Type: application/json

{
  "type": "bulk_export",
  "name": "Monthly Data Export",
  "items": [
    {
      "id": "item1",
      "data": {...},
      "metadata": {...}
    }
  ],
  "exporters": [
    {
      "type": "pdf",
      "options": {...}
    },
    {
      "type": "zip",
      "options": {...}
    }
  ],
  "options": {
    "consolidateOutputs": true,
    "consolidationType": "zip"
  }
}
```

#### Get Job Status
```http
GET /api/bulk/job/{jobId}
```

#### Cancel Job
```http
POST /api/bulk/job/{jobId}/cancel
```

#### Get Metrics
```http
GET /api/bulk/metrics
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "totalJobs": 25,
    "completedJobs": 20,
    "failedJobs": 2,
    "successRate": 80,
    "avgProcessingTimeSeconds": 45,
    "queueStatus": {
      "queueLength": 3,
      "activeJobs": 2,
      "maxConcurrentJobs": 3
    }
  }
}
```

### Cloud Provider Integration

#### Upload to Cloud
```http
POST /api/cloud/upload
Content-Type: multipart/form-data

Parameters:
- file: File to upload
- provider: 'googleDrive', 'dropbox', or 's3'
- options: Provider-specific options (JSON string)
```

**Example:**
```bash
curl -X POST http://localhost:8009/api/cloud/upload \
  -F "file=@document.pdf" \
  -F "provider=googleDrive" \
  -F "options={\"folderId\":\"1234567890\",\"fileName\":\"My Document.pdf\"}"
```

#### Share File
```http
POST /api/cloud/share/{provider}/{fileId}
Content-Type: application/json

{
  "options": {
    "role": "reader",
    "type": "anyone"
  }
}
```

#### Get Available Providers
```http
GET /api/cloud/providers
```

### File Download
```http
GET /api/download/{filename}
```

Downloaded files are automatically cleaned up after 1 minute.

### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "services": {
    "bulkExporter": "running",
    "cloudProviders": ["googleDrive", "dropbox"],
    "uptime": 3600
  }
}
```

## Real-time Progress Updates

The service provides real-time progress updates via WebSocket for bulk export operations:

```javascript
const socket = io('http://localhost:8009');

// Subscribe to job updates
socket.emit('subscribe_job', jobId);

// Listen for progress updates
socket.on('progress', (data) => {
  console.log(`Job ${data.jobId}: ${data.progress}% - ${data.status}`);
});

// Listen for job completion
socket.on('completed', (job) => {
  console.log(`Job ${job.id} completed successfully`);
});

// Listen for job failures
socket.on('failed', (job) => {
  console.log(`Job ${job.id} failed:`, job.errors);
});
```

## Configuration

### Environment Variables

Key configuration options:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8009 | Server port |
| `MAX_FILE_SIZE` | 104857600 | Max upload size (100MB) |
| `BULK_MAX_CONCURRENT` | 3 | Max concurrent bulk jobs |
| `GOOGLE_DRIVE_ENABLED` | false | Enable Google Drive integration |
| `DROPBOX_ENABLED` | false | Enable Dropbox integration |
| `S3_ENABLED` | false | Enable S3 integration |
| `GDPR_ENCRYPT` | false | Encrypt GDPR exports |
| `LOG_LEVEL` | info | Logging level |

See `.env.example` for complete list of configuration options.

### Export Options

#### PDF Export
- Page size: A4, Letter, Legal
- Orientation: portrait, landscape
- Fonts: Helvetica, Times-Roman, Courier
- Metadata preservation
- Watermarks and headers/footers

#### Archive Export
- Compression levels 1-9
- Metadata inclusion
- Permission preservation
- Checksum generation
- File size limits

#### Website Generation
- Multiple themes: default, modern, minimal
- Responsive design
- Search functionality
- Sitemap generation
- Image optimization

#### Photo Book
- Formats: A4, Letter, Square
- Themes: classic, modern, minimal
- Layouts: grid, magazine, scrapbook, auto
- EXIF metadata inclusion
- Image enhancement options

#### GDPR Export
- Data categorization
- Legal basis documentation
- Retention policy inclusion
- Third-party processor lists
- Anonymization options
- Audit logging

## Cloud Provider Setup

### Google Drive

1. Create a Google Cloud Project
2. Enable Google Drive API
3. Create service account or OAuth2 credentials
4. Configure environment variables:

```env
GOOGLE_DRIVE_ENABLED=true
GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY=path/to/service-account.json
# OR for OAuth2:
GOOGLE_DRIVE_CLIENT_ID=your_client_id
GOOGLE_DRIVE_CLIENT_SECRET=your_client_secret
GOOGLE_DRIVE_REFRESH_TOKEN=your_refresh_token
```

### Dropbox

1. Create a Dropbox App
2. Generate access token
3. Configure environment variables:

```env
DROPBOX_ENABLED=true
DROPBOX_ACCESS_TOKEN=your_access_token
```

### Amazon S3

1. Create AWS account and S3 bucket
2. Create IAM user with S3 permissions
3. Configure environment variables:

```env
S3_ENABLED=true
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_ACCESS_KEY=your_secret_key
S3_REGION=us-east-1
S3_BUCKET=your_bucket_name
```

## Error Handling

The service provides comprehensive error handling:

- Input validation
- File type and size restrictions
- Rate limiting
- Timeout handling
- Retry mechanisms
- Detailed error messages

Common error responses:

```json
{
  "success": false,
  "error": "File too large",
  "details": "Maximum file size is 100MB"
}
```

## Performance Considerations

- **Concurrent Jobs**: Limited to 3 by default to prevent resource exhaustion
- **File Size Limits**: 100MB per file, 1GB for archives
- **Rate Limiting**: 100 requests per 15 minutes, 10 export operations per minute
- **Memory Usage**: Files processed in streams where possible
- **Cleanup**: Automatic cleanup of temporary and output files

## Security Features

- **Helmet.js**: Security headers
- **CORS**: Configurable cross-origin policies
- **Rate Limiting**: Multiple levels of rate limiting
- **File Validation**: Type and size validation
- **Encryption**: Optional output encryption for GDPR exports
- **Access Logs**: Comprehensive request logging

## Monitoring and Metrics

Monitor service health and performance:

- Health check endpoint
- Real-time job metrics
- Processing statistics
- Error tracking
- Resource usage monitoring

## Development

### Running in Development

```bash
npm run dev
```

### Testing

```bash
npm test
```

### Code Linting

```bash
npm run lint
```

### Cleanup

```bash
npm run clean
```

## Examples

### Basic PDF Export

```bash
curl -X POST http://localhost:8009/api/export/pdf \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {
        "type": "text",
        "content": "My Document Title",
        "fontSize": 20,
        "font": "Helvetica-Bold"
      },
      {
        "type": "text", 
        "content": "This is the document content."
      }
    ],
    "metadata": {
      "title": "My Document",
      "author": "John Doe"
    }
  }'
```

### Bulk Photo Book Generation

```javascript
const jobConfig = {
  type: 'bulk_export',
  name: 'Family Photo Books',
  items: [
    {
      id: 'vacation_2023',
      data: {
        photos: ['photo1.jpg', 'photo2.jpg'],
        metadata: { title: 'Vacation 2023' }
      }
    },
    {
      id: 'birthday_party',
      data: {
        photos: ['party1.jpg', 'party2.jpg'],
        metadata: { title: 'Birthday Party' }
      }
    }
  ],
  exporters: [{
    type: 'photobook',
    options: {
      format: 'A4',
      theme: 'classic',
      layout: 'magazine'
    }
  }],
  options: {
    consolidateOutputs: true
  }
};

fetch('http://localhost:8009/api/bulk/export', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(jobConfig)
});
```

### GDPR Data Export

```javascript
const userData = {
  personalData: {
    name: 'John Doe',
    email: 'john@example.com',
    phone: '+1234567890'
  },
  systemData: {
    userId: 'user_123',
    accountCreated: '2020-01-15',
    lastLogin: '2025-01-15'
  },
  interactionData: {
    loginHistory: [...],
    purchases: [...],
    preferences: {...}
  },
  files: [
    { path: '/path/to/user/file1.pdf', name: 'document.pdf' },
    { path: '/path/to/user/photo.jpg', name: 'profile.jpg' }
  ]
};

const requestDetails = {
  dataSubjectId: 'user_123',
  dataSubjectEmail: 'john@example.com',
  dataSubjectName: 'John Doe',
  requestType: 'data_portability',
  requestDate: '2025-01-15T10:00:00Z'
};

fetch('http://localhost:8009/api/export/gdpr', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    userData,
    requestDetails,
    options: {
      includeDataProcessingLog: true,
      encryptOutput: true,
      anonymizeIdentifiers: false
    }
  })
});
```

## License

This project is licensed under the MIT License.