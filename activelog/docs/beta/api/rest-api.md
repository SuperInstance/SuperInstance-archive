# REST API Reference

Complete reference for ActiveLog's REST API. The beta version includes enhanced endpoints, extended rate limits, and access to experimental features.

## 🌐 Base Information

### Base URLs
- **Beta Environment**: `https://beta-api.activelog.dev/v1`
- **Production** (Coming Soon): `https://api.activelog.dev/v1`

### Authentication
```http
Authorization: Bearer YOUR_API_TOKEN
Content-Type: application/json
```

### Rate Limits (Beta)
- **Requests**: 10,000/hour
- **Burst**: 100/minute
- **File Uploads**: 50/hour (up to 1GB each)

## 📚 Table of Contents

1. [Authentication](#authentication)
2. [Users & Account](#users--account)
3. [Files & Documents](#files--documents)
4. [Projects & Workspaces](#projects--workspaces)
5. [Search & Analytics](#search--analytics)
6. [Integrations](#integrations)
7. [Beta Features](#beta-features)
8. [Webhooks](#webhooks)
9. [Error Handling](#error-handling)

---

## 🔐 Authentication

### Generate API Token
```http
POST /auth/tokens
Content-Type: application/json

{
  "name": "My Integration",
  "scopes": ["read", "write"],
  "expires_in": 2592000
}
```

**Response:**
```json
{
  "token": "al_1234567890abcdef",
  "name": "My Integration",
  "scopes": ["read", "write"],
  "expires_at": "2024-02-15T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Validate Token
```http
GET /auth/validate
Authorization: Bearer al_1234567890abcdef
```

**Response:**
```json
{
  "valid": true,
  "expires_at": "2024-02-15T10:30:00Z",
  "scopes": ["read", "write"],
  "user_id": "user_123456"
}
```

### Refresh Token
```http
POST /auth/refresh
Authorization: Bearer al_1234567890abcdef

{
  "expires_in": 2592000
}
```

---

## 👤 Users & Account

### Get Current User
```http
GET /account
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "id": "user_123456",
  "email": "user@example.com",
  "name": "John Doe",
  "avatar": "https://avatars.activelog.dev/user_123456.png",
  "plan": "beta",
  "created_at": "2024-01-01T00:00:00Z",
  "settings": {
    "timezone": "UTC",
    "language": "en",
    "notifications": {
      "email": true,
      "push": false
    }
  },
  "beta": {
    "tier": "premium",
    "features": ["ai_insights", "real_time_sync"],
    "expires_at": "2024-06-01T00:00:00Z"
  }
}
```

### Update User Profile
```http
PATCH /account
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "Jane Doe",
  "settings": {
    "timezone": "America/New_York",
    "notifications": {
      "email": false
    }
  }
}
```

### Get Usage Statistics
```http
GET /account/usage?period=30d
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "period": "30d",
  "api_requests": 1547,
  "storage_used": 2147483648,
  "files_uploaded": 23,
  "projects_created": 3,
  "limits": {
    "api_requests": 300000,
    "storage": 10737418240,
    "projects": 100
  }
}
```

---

## 📁 Files & Documents

### Upload File
```http
POST /files
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

file: [binary data]
project_id: "proj_123456" (optional)
metadata: '{"tags": ["document", "important"]}'
```

**Response:**
```json
{
  "id": "file_789012",
  "name": "document.pdf",
  "size": 1048576,
  "mime_type": "application/pdf",
  "checksum": "sha256:abc123...",
  "project_id": "proj_123456",
  "metadata": {
    "tags": ["document", "important"]
  },
  "urls": {
    "download": "https://files.activelog.dev/file_789012",
    "preview": "https://preview.activelog.dev/file_789012",
    "thumbnail": "https://thumbs.activelog.dev/file_789012"
  },
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get File Details
```http
GET /files/{file_id}
Authorization: Bearer YOUR_TOKEN
```

### Download File
```http
GET /files/{file_id}/download
Authorization: Bearer YOUR_TOKEN
```

**Headers:**
```http
Content-Type: application/pdf
Content-Disposition: attachment; filename="document.pdf"
Content-Length: 1048576
```

### List Files
```http
GET /files?limit=50&offset=0&project_id=proj_123456&tags=document
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "files": [
    {
      "id": "file_789012",
      "name": "document.pdf",
      "size": 1048576,
      "mime_type": "application/pdf",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

### Update File Metadata
```http
PATCH /files/{file_id}
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "renamed-document.pdf",
  "metadata": {
    "tags": ["document", "important", "reviewed"],
    "category": "legal"
  }
}
```

### Delete File
```http
DELETE /files/{file_id}
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "deleted": true,
  "id": "file_789012"
}
```

### Bulk Operations
```http
POST /files/bulk
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "operation": "delete",
  "file_ids": ["file_123", "file_456", "file_789"]
}
```

---

## 📊 Projects & Workspaces

### Create Project
```http
POST /projects
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "My Beta Project",
  "description": "Testing new features",
  "settings": {
    "private": true,
    "features": ["ai_insights", "real_time_sync"]
  }
}
```

**Response:**
```json
{
  "id": "proj_123456",
  "name": "My Beta Project",
  "description": "Testing new features",
  "owner_id": "user_123456",
  "settings": {
    "private": true,
    "features": ["ai_insights", "real_time_sync"]
  },
  "stats": {
    "files": 0,
    "storage": 0,
    "collaborators": 1
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Get Project
```http
GET /projects/{project_id}
Authorization: Bearer YOUR_TOKEN
```

### List Projects
```http
GET /projects?limit=25&sort=created_at&order=desc
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "projects": [
    {
      "id": "proj_123456",
      "name": "My Beta Project",
      "description": "Testing new features",
      "stats": {
        "files": 15,
        "storage": 104857600,
        "collaborators": 3
      },
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 8,
    "limit": 25,
    "offset": 0,
    "has_more": false
  }
}
```

### Update Project
```http
PATCH /projects/{project_id}
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "Updated Project Name",
  "settings": {
    "features": ["ai_insights", "real_time_sync", "advanced_analytics"]
  }
}
```

### Delete Project
```http
DELETE /projects/{project_id}
Authorization: Bearer YOUR_TOKEN
```

### Project Collaborators
```http
# List collaborators
GET /projects/{project_id}/collaborators

# Add collaborator
POST /projects/{project_id}/collaborators
{
  "email": "collaborator@example.com",
  "role": "editor"
}

# Remove collaborator
DELETE /projects/{project_id}/collaborators/{user_id}
```

---

## 🔍 Search & Analytics

### Global Search
```http
GET /search?q=document&type=files&limit=20
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "query": "document",
  "results": [
    {
      "type": "file",
      "id": "file_789012",
      "name": "important-document.pdf",
      "project_id": "proj_123456",
      "score": 0.95,
      "highlights": ["<mark>document</mark>.pdf"]
    }
  ],
  "total": 45,
  "took": 23
}
```

### Advanced Search
```http
POST /search/advanced
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "query": {
    "text": "financial report",
    "filters": {
      "type": ["pdf", "docx"],
      "size": {"min": 1000000, "max": 10000000},
      "created": {"after": "2024-01-01"}
    },
    "sort": "relevance"
  },
  "limit": 50
}
```

### Analytics Dashboard
```http
GET /analytics/dashboard?period=30d
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "period": "30d",
  "summary": {
    "total_files": 156,
    "total_storage": 5368709120,
    "total_searches": 89,
    "total_downloads": 234
  },
  "charts": {
    "uploads_over_time": [
      {"date": "2024-01-01", "count": 5},
      {"date": "2024-01-02", "count": 8}
    ],
    "file_types": [
      {"type": "pdf", "count": 45},
      {"type": "docx", "count": 32}
    ]
  }
}
```

### Export Analytics
```http
POST /analytics/export
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "period": "90d",
  "format": "csv",
  "include": ["files", "searches", "downloads"]
}
```

---

## 🔗 Integrations

### List Available Integrations
```http
GET /integrations
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "integrations": [
    {
      "id": "google-drive",
      "name": "Google Drive",
      "description": "Sync files with Google Drive",
      "status": "available",
      "beta": false
    },
    {
      "id": "notion-sync",
      "name": "Notion Sync",
      "description": "Advanced Notion integration",
      "status": "available", 
      "beta": true
    }
  ]
}
```

### Enable Integration
```http
POST /integrations/{integration_id}/enable
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "config": {
    "sync_frequency": "hourly",
    "folders": ["Documents", "Projects"]
  }
}
```

### Get Integration Status
```http
GET /integrations/{integration_id}
Authorization: Bearer YOUR_TOKEN
```

### Sync Integration
```http
POST /integrations/{integration_id}/sync
Authorization: Bearer YOUR_TOKEN
```

---

## 🧪 Beta Features

### AI-Powered Insights
```http
POST /beta/ai/insights
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "file_ids": ["file_123", "file_456"],
  "analysis_type": "content_summary"
}
```

**Response:**
```json
{
  "insights": [
    {
      "file_id": "file_123",
      "summary": "Financial report for Q4 2023 showing 15% growth...",
      "keywords": ["financial", "growth", "revenue"],
      "sentiment": "positive",
      "confidence": 0.87
    }
  ],
  "processing_time": 2.3
}
```

### Real-time Collaboration
```http
GET /beta/collaboration/{project_id}/sessions
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "active_sessions": [
    {
      "user_id": "user_456",
      "user_name": "Jane Doe",
      "file_id": "file_789",
      "started_at": "2024-01-15T14:30:00Z",
      "activity": "editing"
    }
  ],
  "total_active": 3
}
```

### Advanced Analytics
```http
GET /beta/analytics/advanced?metrics=engagement,usage,performance
Authorization: Bearer YOUR_TOKEN
```

### Feature Flag Status
```http
GET /beta/features
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "features": {
    "ai_insights": {"enabled": true, "tier": "premium"},
    "real_time_sync": {"enabled": true, "tier": "standard"},
    "advanced_search": {"enabled": false, "tier": "enterprise"}
  }
}
```

---

## 🎣 Webhooks

### Create Webhook
```http
POST /webhooks
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "url": "https://your-app.com/webhooks/activelog",
  "events": ["file.uploaded", "project.created"],
  "secret": "your-webhook-secret"
}
```

### List Webhooks
```http
GET /webhooks
Authorization: Bearer YOUR_TOKEN
```

### Test Webhook
```http
POST /webhooks/{webhook_id}/test
Authorization: Bearer YOUR_TOKEN
```

### Webhook Events
Available events:
- `file.uploaded`
- `file.deleted`
- `project.created`
- `project.updated`
- `user.invited`
- `integration.synced`

**Example Payload:**
```json
{
  "event": "file.uploaded",
  "data": {
    "file": {
      "id": "file_789012",
      "name": "document.pdf",
      "project_id": "proj_123456"
    },
    "user": {
      "id": "user_123456",
      "email": "user@example.com"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🚨 Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "name",
        "message": "Name is required"
      }
    ],
    "request_id": "req_123456789",
    "documentation": "https://docs.activelog.dev/api/errors#validation-error"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Invalid or missing API token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict (e.g., duplicate) |
| 422 | Validation Error | Request validation failed |
| 429 | Rate Limited | Too many requests |
| 500 | Server Error | Internal server error |

### Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `INVALID_TOKEN` | API token is invalid | Generate new token |
| `EXPIRED_TOKEN` | API token has expired | Refresh or generate new token |
| `INSUFFICIENT_PERMISSIONS` | Missing required permissions | Check token scopes |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded | Wait and retry |
| `VALIDATION_ERROR` | Request validation failed | Fix request parameters |
| `RESOURCE_NOT_FOUND` | Requested resource not found | Verify resource ID |
| `DUPLICATE_RESOURCE` | Resource already exists | Use different identifier |
| `STORAGE_QUOTA_EXCEEDED` | Storage limit reached | Delete files or upgrade plan |
| `FEATURE_NOT_AVAILABLE` | Feature not available in current plan | Upgrade plan or wait for general availability |

### Beta-Specific Errors

| Code | Description | Resolution |
|------|-------------|------------|
| `BETA_FEATURE_DISABLED` | Beta feature is disabled | Check feature flags |
| `BETA_ACCESS_EXPIRED` | Beta access has expired | Contact beta support |
| `EXPERIMENTAL_FEATURE_ERROR` | Experimental feature error | Report to beta team |

---

## 📖 Code Examples

### JavaScript/Node.js
```javascript
const axios = require('axios');

const api = axios.create({
  baseURL: 'https://beta-api.activelog.dev/v1',
  headers: {
    'Authorization': `Bearer ${process.env.ACTIVELOG_API_KEY}`,
    'Content-Type': 'application/json'
  }
});

// Upload file
const formData = new FormData();
formData.append('file', fs.createReadStream('document.pdf'));
formData.append('project_id', 'proj_123456');

const response = await api.post('/files', formData, {
  headers: {
    'Content-Type': 'multipart/form-data'
  }
});
```

### Python
```python
import requests
import os

API_BASE = 'https://beta-api.activelog.dev/v1'
HEADERS = {
    'Authorization': f'Bearer {os.getenv("ACTIVELOG_API_KEY")}',
    'Content-Type': 'application/json'
}

# Create project
response = requests.post(
    f'{API_BASE}/projects',
    headers=HEADERS,
    json={
        'name': 'My Python Project',
        'description': 'Created via Python API'
    }
)

project = response.json()
print(f'Created project: {project["id"]}')
```

### PHP
```php
<?php
$apiKey = getenv('ACTIVELOG_API_KEY');
$baseUrl = 'https://beta-api.activelog.dev/v1';

$curl = curl_init();
curl_setopt_array($curl, [
    CURLOPT_URL => $baseUrl . '/account',
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'Authorization: Bearer ' . $apiKey,
        'Content-Type: application/json'
    ]
]);

$response = curl_exec($curl);
$account = json_decode($response, true);

echo 'Account ID: ' . $account['id'];
curl_close($curl);
?>
```

### cURL Examples
```bash
# Get account info
curl -H "Authorization: Bearer $ACTIVELOG_API_KEY" \
     https://beta-api.activelog.dev/v1/account

# Upload file
curl -X POST \
     -H "Authorization: Bearer $ACTIVELOG_API_KEY" \
     -F "file=@document.pdf" \
     -F "project_id=proj_123456" \
     https://beta-api.activelog.dev/v1/files

# Create project
curl -X POST \
     -H "Authorization: Bearer $ACTIVELOG_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"My Project","description":"Test project"}' \
     https://beta-api.activelog.dev/v1/projects
```

---

## 🔄 Pagination

### Standard Pagination
```http
GET /files?limit=50&offset=100
```

### Cursor-based Pagination (for large datasets)
```http
GET /files?limit=50&cursor=eyJpZCI6ImZpbGVfMTIzIn0
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "has_more": true,
    "next_cursor": "eyJpZCI6ImZpbGVfNDU2In0",
    "total": 1547
  }
}
```

---

## 📊 Best Practices

### Rate Limit Handling
```javascript
async function apiRequest(url, options) {
  const response = await fetch(url, options);
  
  if (response.status === 429) {
    const resetTime = response.headers.get('X-RateLimit-Reset');
    const waitTime = (resetTime * 1000) - Date.now();
    
    await new Promise(resolve => setTimeout(resolve, waitTime));
    return apiRequest(url, options); // Retry
  }
  
  return response;
}
```

### Error Handling
```javascript
try {
  const response = await api.post('/files', fileData);
  return response.data;
} catch (error) {
  if (error.response?.status === 422) {
    // Handle validation errors
    const errors = error.response.data.error.details;
    console.error('Validation errors:', errors);
  } else {
    // Handle other errors
    console.error('API error:', error.message);
  }
  throw error;
}
```

### Bulk Operations
```javascript
// Instead of individual requests
const files = await Promise.all(
  fileIds.map(id => api.get(`/files/${id}`))
);

// Use bulk endpoint
const files = await api.post('/files/bulk-get', {
  file_ids: fileIds
});
```

---

Ready to start building? Try the [Interactive API Explorer](https://beta-api.activelog.dev/docs) or check out our [SDK Libraries](sdks.md) for your preferred language.

*Last Updated: [Current Date] | API Version: 1.0.0-beta.42*