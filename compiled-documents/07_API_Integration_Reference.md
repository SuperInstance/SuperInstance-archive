# API Integration Reference
## ActiveLog Technologies, Inc.

**Document Version:** 1.0  
**Effective Date:** [DATE]  
**Last Updated:** [DATE]  
**Next Review:** [DATE + 6 months]  
**Owner:** VP of Engineering and API Platform Team  

---

## Table of Contents

1. [Platform API Overview](#platform-api-overview)
2. [Authentication and Authorization](#authentication-and-authorization)
3. [Core Service APIs](#core-service-apis)
4. [Sync and Real-time Collaboration](#sync-and-real-time-collaboration)
5. [Search and Analytics APIs](#search-and-analytics-apis)
6. [File Management APIs](#file-management-apis)
7. [Integration Patterns](#integration-patterns)
8. [SDK and Client Libraries](#sdk-and-client-libraries)
9. [Webhook System](#webhook-system)
10. [Rate Limiting and Error Handling](#rate-limiting-and-error-handling)
11. [Environment Configuration](#environment-configuration)
12. [Best Practices and Examples](#best-practices-and-examples)

---

## Platform API Overview

### 1.1 API Architecture

ActiveLog provides a comprehensive RESTful API ecosystem built on a microservices architecture. The platform supports multiple API versions and environments to ensure reliability and backwards compatibility.

**API Endpoints:**
```yaml
Production Environment:
  Base URL: https://api.activelog.com/v1
  WebSocket: wss://api.activelog.com/ws/v1
  Status: Coming Soon

Beta Environment:
  Base URL: https://beta-api.activelog.dev/v1
  WebSocket: wss://beta-api.activelog.dev/ws/v1
  Status: Currently Active

Development Environment:
  Base URL: http://localhost:8000/api/v1
  Individual Services:
    - API Gateway: http://localhost:8000
    - Auth Service: http://localhost:8001
    - Metadata Service: http://localhost:8002
    - Analytics Service: http://localhost:8003
    - Notification Service: http://localhost:8004
```

**Service Architecture:**
```yaml
API Gateway (Port 8000):
  - Request routing and load balancing
  - Authentication and authorization
  - Rate limiting and request validation
  - API versioning and deprecation management

Core Services:
  Auth Service (Port 8001):
    - User authentication and session management
    - JWT token generation and validation
    - OAuth 2.0 and SSO integration
    - Role-based access control (RBAC)
  
  Metadata Service (Port 8002):
    - File metadata management
    - Search indexing and vector embeddings
    - Tag management and relationships
    - Content analysis and extraction
  
  Analytics Service (Port 8003):
    - Usage analytics and reporting
    - Performance metrics collection
    - User behavior analysis
    - Custom dashboard generation
  
  Notification Service (Port 8004):
    - Email and push notifications
    - Real-time alerts and updates
    - Webhook delivery management
    - Communication preferences

Support Services:
  - PostgreSQL (Port 5432): Primary database
  - Redis (Port 6379): Caching and session storage
  - Elasticsearch (Port 9200): Search and analytics
  - MinIO (Port 9000): Object storage
  - RabbitMQ (Port 5672): Message queuing
```

### 1.2 API Standards and Conventions

**HTTP Methods and Status Codes:**
```yaml
HTTP Methods:
  GET: Retrieve resources (idempotent)
  POST: Create new resources
  PUT: Update entire resources (idempotent)
  PATCH: Update partial resources
  DELETE: Remove resources (idempotent)

Standard Status Codes:
  200 OK: Request successful
  201 Created: Resource created successfully
  400 Bad Request: Invalid request parameters
  401 Unauthorized: Invalid or missing authentication
  403 Forbidden: Insufficient permissions
  404 Not Found: Resource not found
  409 Conflict: Resource conflict (e.g., duplicate)
  422 Validation Error: Request validation failed
  429 Too Many Requests: Rate limit exceeded
  500 Internal Server Error: Server-side error
```

**Request/Response Format:**
```json
// Standard API Response Format
{
  "data": {
    // Response payload
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0",
    "request_id": "req_abc123"
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5,
    "has_more": true
  }
}

// Error Response Format
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "req_abc123",
    "documentation": "https://docs.activelog.com/api/errors"
  }
}
```

---

## Authentication and Authorization

### 2.1 Authentication Methods

**JWT Bearer Token Authentication:**
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Content-Type: application/json
```

**API Key Authentication (for server-to-server):**
```http
Authorization: ApiKey al_1234567890abcdef
Content-Type: application/json
```

**OAuth 2.0 Flow (for third-party integrations):**
```http
Authorization: Bearer oauth_token_here
Content-Type: application/json
```

### 2.2 Auth Service API

**Token Generation:**
```http
POST /auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_string",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_string",
  "user": {
    "id": "user_123",
    "username": "user@example.com",
    "email": "user@example.com",
    "roles": ["user", "beta_tester"]
  }
}
```

**Token Refresh:**
```http
POST /auth/refresh
Authorization: Bearer current_access_token

{
  "refresh_token": "refresh_token_string",
  "expires_in": 2592000
}
```

**Token Validation:**
```http
GET /auth/validate
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "valid": true,
  "expires_at": "2024-02-15T10:30:00Z",
  "scopes": ["read", "write"],
  "user_id": "user_123"
}
```

### 2.3 User Management

**Get Current User:**
```http
GET /auth/me
Authorization: Bearer jwt_token
```

**Update User Profile:**
```http
PUT /auth/me
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "full_name": "Updated Name",
  "email": "newemail@example.com",
  "preferences": {
    "theme": "dark",
    "language": "en",
    "notifications": {
      "email": true,
      "push": false
    }
  }
}
```

**Password Management:**
```http
POST /auth/change-password
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "current_password": "old_password",
  "new_password": "new_secure_password",
  "confirm_password": "new_secure_password"
}
```

**Password Reset Flow:**
```http
# Request password reset
POST /auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}

# Reset password with token
POST /auth/reset-password
Content-Type: application/json

{
  "reset_token": "token_from_email",
  "new_password": "new_secure_password",
  "confirm_password": "new_secure_password"
}
```

### 2.4 Role-Based Access Control

**Available Roles:**
```yaml
User Roles:
  - user: Standard user with basic access
  - premium: Premium features access
  - admin: Administrative privileges
  - beta_tester: Beta feature access
  - developer: API and integration access
  - enterprise: Enterprise features access

Permission Scopes:
  - read: Read access to resources
  - write: Create and update resources
  - delete: Delete resources
  - admin: Administrative operations
  - beta: Beta feature access
```

**Role Management (Admin Only):**
```http
# List all users
GET /auth/users?page=1&per_page=20&role=user
Authorization: Bearer admin_jwt_token

# Update user roles
PUT /auth/users/{user_id}/roles
Authorization: Bearer admin_jwt_token
Content-Type: application/json

{
  "roles": ["user", "premium", "beta_tester"]
}
```

### 2.5 Two-Factor Authentication

**Enable 2FA:**
```http
POST /auth/2fa/enable
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "secret": "JBSWY3DPEHPK3PXP",
  "backup_codes": [
    "12345678",
    "87654321",
    "11111111",
    "22222222",
    "33333333"
  ]
}
```

**Verify 2FA Setup:**
```http
POST /auth/2fa/verify
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "totp_code": "123456"
}
```

**Disable 2FA:**
```http
POST /auth/2fa/disable
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "password": "current_password",
  "totp_code": "123456"
}
```

---

## Core Service APIs

### 3.1 Account and Usage Management

**Get Account Information:**
```http
GET /account
Authorization: Bearer jwt_token
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

**Get Usage Statistics:**
```http
GET /account/usage?period=30d
Authorization: Bearer jwt_token
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
  },
  "usage_by_service": {
    "file_uploads": 1240,
    "search_queries": 89,
    "ai_operations": 156,
    "sync_operations": 2341
  }
}
```

### 3.2 Project and Workspace Management

**Create Project:**
```http
POST /projects
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "name": "My Beta Project",
  "description": "Testing new features",
  "settings": {
    "private": true,
    "features": ["ai_insights", "real_time_sync"],
    "default_permissions": "read"
  },
  "metadata": {
    "category": "development",
    "priority": "high"
  }
}
```

**List Projects:**
```http
GET /projects?limit=25&sort=created_at&order=desc&filter=active
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "projects": [
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
        "files": 15,
        "storage": 104857600,
        "collaborators": 3,
        "last_activity": "2024-01-15T10:30:00Z"
      },
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:22:00Z"
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

**Project Collaboration:**
```http
# List collaborators
GET /projects/{project_id}/collaborators
Authorization: Bearer jwt_token

# Add collaborator
POST /projects/{project_id}/collaborators
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "email": "collaborator@example.com",
  "role": "editor",
  "permissions": ["read", "write", "comment"],
  "send_invitation": true
}

# Update collaborator permissions
PUT /projects/{project_id}/collaborators/{user_id}
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "role": "admin",
  "permissions": ["read", "write", "delete", "manage"]
}

# Remove collaborator
DELETE /projects/{project_id}/collaborators/{user_id}
Authorization: Bearer jwt_token
```

---

## Sync and Real-time Collaboration

### 4.1 ActiveLog Sync Service v2

The Sync Service provides advanced device synchronization with intelligent conflict resolution, bandwidth awareness, and real-time collaboration capabilities.

**Base URL:** `https://sync.activelog.ai/api/v2`

### 4.2 Device Registration and Management

**Register Device:**
```http
POST /devices/register
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "device_id": "phone-001",
  "device_type": "phone",
  "capabilities": "mobile",
  "name": "iPhone 15",
  "platform": "ios",
  "version": "1.0.0",
  "user_id": "user123"
}
```

**Response:**
```json
{
  "status": "success",
  "device_id": "phone-001",
  "session_id": "sess_abc123",
  "server_capabilities": [
    "selective_sync",
    "conflict_resolution", 
    "compression",
    "mobile_optimization"
  ]
}
```

**Get Device Status:**
```http
GET /devices/{device_id}/status
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "device_id": "phone-001",
  "is_online": true,
  "last_seen": "2024-01-01T12:00:00Z",
  "sync_status": "synced",
  "pending_items": 0,
  "conflicts": 2,
  "network_profile": {
    "current_type": "wifi",
    "bandwidth_limit": null,
    "is_metered": false
  }
}
```

### 4.3 Synchronization Operations

**Sync Items:**
```http
POST /sync/items
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "device_id": "phone-001",
  "last_sync_timestamp": "2024-01-01T10:00:00Z",
  "sync_direction": "bidirectional",
  "max_items": 50,
  "content_filters": ["exclude_media"],
  "priority_threshold": 5
}
```

**Response:**
```json
{
  "items": [
    {
      "item_id": "item-001",
      "content_type": "text",
      "data": {
        "title": "My Note",
        "content": "Note content here"
      },
      "version": 2,
      "modified_at": "2024-01-01T11:00:00Z",
      "device_origin": "desktop-001"
    }
  ],
  "conflicts": [
    {
      "conflict_id": "conflict-001",
      "item_id": "item-002", 
      "conflict_type": "concurrent_edit",
      "severity": "medium",
      "conflicting_versions": [
        {
          "version_id": "v1",
          "device_name": "iPhone 15",
          "timestamp": "2024-01-01T10:30:00Z"
        },
        {
          "version_id": "v2", 
          "device_name": "MacBook Pro",
          "timestamp": "2024-01-01T10:31:00Z"
        }
      ]
    }
  ],
  "next_sync_token": "token_def456",
  "has_more": false,
  "server_timestamp": "2024-01-01T12:00:00Z"
}
```

**Upload Item:**
```http
POST /sync/upload
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "item": {
    "item_id": "new-item-001",
    "content_type": "text",
    "data": {
      "title": "New Note",
      "content": "New note content"
    },
    "priority": 7,
    "tags": ["important", "work"],
    "metadata": {
      "created_by": "user123",
      "project_id": "proj_456"
    }
  }
}
```

### 4.4 Conflict Resolution

**Get Conflicts:**
```http
GET /conflicts?device_id={device_id}&severity=medium,high
Authorization: Bearer jwt_token
```

**Resolve Conflict:**
```http
POST /conflicts/{conflict_id}/resolve
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "strategy": "smart_merge",
  "user_input": {
    "preferred_version": "v2",
    "custom_merge": null,
    "merge_strategy_params": {
      "prefer_latest": true,
      "preserve_formatting": true
    }
  }
}
```

**Response:**
```json
{
  "status": "resolved",
  "conflict_id": "conflict-001",
  "strategy_used": "smart_merge",
  "merged_data": {
    "content": "Merged content from both versions"
  },
  "confidence_score": 0.85,
  "manual_review_required": false
}
```

### 4.5 Real-time Collaboration

**Start Collaboration Session:**
```http
POST /collaboration/sessions
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "document_id": "doc-001",
  "user_id": "user123",
  "session_type": "edit",
  "permissions": ["read", "write", "comment"]
}
```

**Response:**
```json
{
  "session_id": "session_abc123",
  "document_id": "doc-001",
  "websocket_url": "wss://sync.activelog.ai/ws/v2",
  "current_revision": 42,
  "participants": [
    {
      "user_id": "user123",
      "user_name": "Alice",
      "color": "#007AFF",
      "cursor_position": 125,
      "last_seen": "2024-01-01T12:00:00Z"
    }
  ]
}
```

**WebSocket Connection:**
```javascript
// Connect to WebSocket for real-time collaboration
const ws = new WebSocket('wss://sync.activelog.ai/ws/v2');

// Join session
ws.send(JSON.stringify({
  "type": "join_session",
  "document_id": "doc-001",
  "session_id": "session_abc123",
  "user_info": {
    "user_id": "user123",
    "user_name": "Alice",
    "color": "#007AFF"
  }
}));

// Send operation
ws.send(JSON.stringify({
  "type": "operation_batch",
  "batch": {
    "batch_id": "batch_123",
    "operations": [
      {
        "op_type": "insert",
        "position": 10,
        "content": "Hello World",
        "author_id": "user123"
      }
    ],
    "document_id": "doc-001",
    "base_revision": 42
  }
}));

// Handle incoming messages
ws.onmessage = function(event) {
  const message = JSON.parse(event.data);
  
  switch(message.type) {
    case 'operation_batch':
      // Apply operations to document
      break;
    case 'cursor_update':
      // Update other users' cursor positions
      break;
    case 'user_joined':
      // Show new user joined
      break;
    case 'user_left':
      // Remove user from participant list
      break;
  }
};
```

---

## Search and Analytics APIs

### 5.1 Metadata Service Search API

**Global Search:**
```http
GET /search?q=machine+learning&type=files&limit=20&page=1
Authorization: Bearer jwt_token
```

**Query Parameters:**
```yaml
Search Parameters:
  q: Search query text (required)
  type: Resource type filter (files, projects, users)
  page: Page number (default: 1)
  per_page: Results per page (default: 20, max: 100)
  file_types: File type filter (pdf,docx,txt)
  tags: Tag filter (work,important)
  date_from: Start date filter (ISO format)
  date_to: End date filter (ISO format)
  size_min: Minimum file size in bytes
  size_max: Maximum file size in bytes
  sort: Sort order (relevance, date_asc, date_desc, size_asc, size_desc)
  project_id: Limit search to specific project
  author: Filter by file author
  modified_by: Filter by last modifier
```

**Response:**
```json
{
  "query": "machine learning",
  "results": [
    {
      "type": "file",
      "id": "file_789012",
      "name": "ml-research-paper.pdf",
      "project_id": "proj_123456",
      "score": 0.95,
      "highlights": [
        "This paper discusses <mark>machine learning</mark> applications...",
        "Advanced <mark>machine learning</mark> techniques for..."
      ],
      "metadata": {
        "title": "Machine Learning Research Paper",
        "author": "Dr. Smith",
        "created_date": "2024-01-01T00:00:00Z"
      },
      "tags": ["research", "ai", "machine-learning"]
    }
  ],
  "facets": {
    "file_types": {
      "pdf": 45,
      "docx": 23,
      "txt": 12
    },
    "tags": {
      "research": 34,
      "ai": 28,
      "machine-learning": 15
    },
    "projects": {
      "proj_123": 20,
      "proj_456": 15,
      "proj_789": 10
    }
  },
  "total": 45,
  "took": 23
}
```

### 5.2 Advanced Search

**Advanced Search with Complex Filters:**
```http
POST /search/advanced
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "content": "financial report quarterly"
          }
        }
      ],
      "filter": [
        {
          "terms": {
            "tags": ["finance", "quarterly", "report"]
          }
        },
        {
          "range": {
            "file_size": {
              "gte": 1000000,
              "lte": 50000000
            }
          }
        },
        {
          "range": {
            "created_date": {
              "gte": "2024-01-01",
              "lte": "2024-03-31"
            }
          }
        }
      ],
      "must_not": [
        {
          "match": {
            "tags": "draft"
          }
        }
      ]
    }
  },
  "sort": [
    {
      "_score": {
        "order": "desc"
      }
    },
    {
      "created_at": {
        "order": "desc"
      }
    }
  ],
  "page": 1,
  "per_page": 20,
  "highlight": {
    "fields": {
      "content": {},
      "title": {}
    }
  }
}
```

### 5.3 Vector Embeddings and Semantic Search

**Generate Vector Embeddings:**
```http
POST /embeddings/generate
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "file_id": "file_unique_id",
  "content": "This document discusses artificial intelligence and machine learning applications in modern business environments.",
  "model": "text-embedding-ada-002",
  "chunk_size": 1000,
  "overlap": 100
}
```

**Response:**
```json
{
  "message": "Embeddings generated successfully",
  "embedding_id": "embedding_unique_id",
  "dimensions": 1536,
  "model": "text-embedding-ada-002",
  "chunks_processed": 5,
  "processing_time_ms": 1250
}
```

**Semantic Search:**
```http
POST /embeddings/search
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "query": "Find documents about artificial intelligence and automation in business processes",
  "limit": 20,
  "threshold": 0.7,
  "include_metadata": true,
  "filters": {
    "file_types": ["pdf", "docx"],
    "tags": ["business", "ai"],
    "date_range": {
      "from": "2024-01-01",
      "to": "2024-12-31"
    }
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "file_id": "file_unique_id",
      "filename": "ai-business-automation.pdf",
      "similarity_score": 0.89,
      "metadata": {
        "title": "AI-Driven Business Process Automation",
        "author": "Technology Team",
        "created_date": "2024-03-15T00:00:00Z"
      },
      "tags": ["ai", "automation", "business"],
      "excerpt": "This document explores the implementation of artificial intelligence in business process automation...",
      "chunk_info": {
        "chunk_id": "chunk_123",
        "start_position": 1250,
        "end_position": 2250
      }
    }
  ],
  "query_embedding_time_ms": 45,
  "search_time_ms": 123,
  "total_results": 15
}
```

### 5.4 Analytics Dashboard API

**Get Analytics Dashboard:**
```http
GET /analytics/dashboard?period=30d&metrics=uploads,searches,collaboration
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "period": "30d",
  "summary": {
    "total_files": 1547,
    "total_storage": 5368709120,
    "total_searches": 234,
    "total_downloads": 456,
    "active_collaborations": 12,
    "api_requests": 8934
  },
  "charts": {
    "uploads_over_time": [
      {"date": "2024-01-01", "count": 15, "size": 104857600},
      {"date": "2024-01-02", "count": 23, "size": 157286400},
      {"date": "2024-01-03", "count": 18, "size": 125829120}
    ],
    "file_types": [
      {"type": "pdf", "count": 456, "percentage": 29.5},
      {"type": "docx", "count": 234, "percentage": 15.1},
      {"type": "jpg", "count": 189, "percentage": 12.2}
    ],
    "search_trends": [
      {"query": "machine learning", "count": 23},
      {"query": "financial report", "count": 18},
      {"query": "project documentation", "count": 15}
    ],
    "collaboration_activity": [
      {"date": "2024-01-01", "sessions": 5, "participants": 12},
      {"date": "2024-01-02", "sessions": 8, "participants": 18}
    ]
  },
  "insights": {
    "storage_growth_rate": "+12.5%",
    "most_active_hours": [9, 10, 14, 15],
    "peak_collaboration_days": ["Tuesday", "Wednesday", "Thursday"],
    "top_file_categories": ["documents", "images", "presentations"]
  }
}
```

**Export Analytics:**
```http
POST /analytics/export
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "period": "90d",
  "format": "csv",
  "include": ["files", "searches", "downloads", "collaborations"],
  "filters": {
    "project_ids": ["proj_123", "proj_456"],
    "user_ids": ["user_123", "user_456"]
  },
  "email_when_ready": true
}
```

---

## File Management APIs

### 6.1 File Upload and Management

**Upload File:**
```http
POST /files
Authorization: Bearer jwt_token
Content-Type: multipart/form-data

file: [binary data]
project_id: "proj_123456"
folder_path: "/Documents/Reports"
metadata: '{"tags": ["report", "q4", "financial"], "category": "business"}'
auto_ocr: true
generate_thumbnail: true
```

**Response:**
```json
{
  "id": "file_789012",
  "name": "quarterly-report.pdf",
  "size": 2048576,
  "mime_type": "application/pdf",
  "checksum": "sha256:abc123def456...",
  "project_id": "proj_123456",
  "folder_path": "/Documents/Reports",
  "metadata": {
    "tags": ["report", "q4", "financial"],
    "category": "business",
    "auto_extracted": {
      "page_count": 24,
      "word_count": 5420,
      "language": "en"
    }
  },
  "urls": {
    "download": "https://files.activelog.dev/file_789012",
    "preview": "https://preview.activelog.dev/file_789012",
    "thumbnail": "https://thumbs.activelog.dev/file_789012"
  },
  "processing_status": {
    "ocr": "completed",
    "thumbnail": "completed",
    "indexing": "in_progress",
    "virus_scan": "completed"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**List Files:**
```http
GET /files?limit=50&offset=0&project_id=proj_123456&folder_path=/Documents&tags=report,financial&sort=modified_date&order=desc
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "files": [
    {
      "id": "file_789012",
      "name": "quarterly-report.pdf",
      "size": 2048576,
      "mime_type": "application/pdf",
      "project_id": "proj_123456",
      "folder_path": "/Documents/Reports",
      "metadata": {
        "tags": ["report", "q4", "financial"],
        "category": "business"
      },
      "thumbnail": "https://thumbs.activelog.dev/file_789012",
      "created_at": "2024-01-15T10:30:00Z",
      "modified_at": "2024-01-15T14:22:00Z",
      "last_accessed": "2024-01-15T16:45:00Z"
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 50,
    "offset": 0,
    "has_more": true
  },
  "facets": {
    "file_types": {
      "pdf": 45,
      "docx": 23,
      "xlsx": 12
    },
    "sizes": {
      "small": 89,
      "medium": 45,
      "large": 22
    }
  }
}
```

**Get File Details:**
```http
GET /files/{file_id}?include_content=false&include_relationships=true
Authorization: Bearer jwt_token
```

### 6.2 File Metadata Management

**Update File Metadata:**
```http
PATCH /files/{file_id}
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "name": "updated-quarterly-report.pdf",
  "metadata": {
    "tags": ["report", "q4", "financial", "reviewed"],
    "category": "business",
    "status": "approved",
    "approval_date": "2024-01-16T10:00:00Z",
    "approved_by": "user_456"
  },
  "folder_path": "/Documents/Reports/Approved"
}
```

**Bulk File Operations:**
```http
POST /files/bulk
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "operation": "update_metadata",
  "file_ids": ["file_123", "file_456", "file_789"],
  "data": {
    "metadata": {
      "tags": ["archived", "2024"],
      "status": "archived"
    },
    "folder_path": "/Archive/2024"
  }
}
```

### 6.3 File Sharing and Permissions

**Share File:**
```http
POST /files/{file_id}/share
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "share_type": "link",
  "permissions": ["read", "download"],
  "expires_at": "2024-02-15T00:00:00Z",
  "password_protected": true,
  "password": "secure_share_password",
  "allow_anonymous": false,
  "notify_recipients": true,
  "recipients": [
    {
      "email": "colleague@example.com",
      "permissions": ["read", "comment"]
    },
    {
      "user_id": "user_789",
      "permissions": ["read", "write"]
    }
  ]
}
```

**Response:**
```json
{
  "share_id": "share_abc123",
  "share_url": "https://share.activelog.com/s/abc123def456",
  "share_type": "link",
  "permissions": ["read", "download"],
  "expires_at": "2024-02-15T00:00:00Z",
  "password_protected": true,
  "created_at": "2024-01-15T10:30:00Z",
  "recipients": [
    {
      "email": "colleague@example.com",
      "status": "pending",
      "invited_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 6.4 File Processing and Analysis

**Process File with AI:**
```http
POST /files/{file_id}/process
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "operations": [
    "extract_text",
    "generate_summary",
    "classify_content",
    "extract_entities",
    "generate_keywords"
  ],
  "ai_model": "gpt-3.5-turbo",
  "language": "en",
  "custom_prompts": {
    "summary": "Provide a 2-paragraph executive summary of this document",
    "classification": "Classify this document into business categories"
  }
}
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "queued",
  "estimated_completion": "2024-01-15T10:35:00Z",
  "operations_requested": [
    "extract_text",
    "generate_summary", 
    "classify_content",
    "extract_entities",
    "generate_keywords"
  ]
}
```

**Get Processing Results:**
```http
GET /files/{file_id}/processing/{job_id}
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "completed_at": "2024-01-15T10:34:23Z",
  "results": {
    "extract_text": {
      "status": "completed",
      "text": "Full extracted text content...",
      "confidence": 0.95,
      "pages": 24,
      "word_count": 5420
    },
    "generate_summary": {
      "status": "completed",
      "summary": "This quarterly financial report shows strong performance across all business units...",
      "key_points": [
        "Revenue increased by 15% year-over-year",
        "Profit margins improved to 22%",
        "Strong growth in digital services"
      ]
    },
    "classify_content": {
      "status": "completed",
      "categories": [
        {"name": "Financial Report", "confidence": 0.92},
        {"name": "Quarterly Business Review", "confidence": 0.88},
        {"name": "Executive Summary", "confidence": 0.76}
      ]
    },
    "extract_entities": {
      "status": "completed",
      "entities": {
        "organizations": ["ActiveLog Inc.", "Finance Department"],
        "dates": ["Q4 2023", "December 2023", "January 2024"],
        "monetary_values": ["$2.5M", "$450K", "15%"],
        "people": ["John Smith (CFO)", "Jane Doe (VP Finance)"]
      }
    },
    "generate_keywords": {
      "status": "completed",
      "keywords": [
        {"keyword": "financial performance", "relevance": 0.95},
        {"keyword": "quarterly results", "relevance": 0.89},
        {"keyword": "revenue growth", "relevance": 0.82}
      ]
    }
  },
  "processing_time_ms": 12340,
  "cost_estimate": "$0.15"
}
```

---

## Integration Patterns

### 7.1 Third-Party Service Integrations

**List Available Integrations:**
```http
GET /integrations
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "integrations": [
    {
      "id": "google-drive",
      "name": "Google Drive",
      "description": "Sync files with Google Drive",
      "category": "storage",
      "status": "available",
      "beta": false,
      "configuration_required": ["client_id", "client_secret"],
      "supported_operations": ["sync", "upload", "download", "list"]
    },
    {
      "id": "notion-sync",
      "name": "Notion Sync",
      "description": "Advanced Notion integration with real-time sync",
      "category": "productivity",
      "status": "available", 
      "beta": true,
      "configuration_required": ["api_token", "database_id"],
      "supported_operations": ["sync", "create", "update", "search"]
    },
    {
      "id": "slack-notifications",
      "name": "Slack Notifications",
      "description": "Send notifications to Slack channels",
      "category": "communication",
      "status": "available",
      "beta": false,
      "configuration_required": ["webhook_url", "channel"],
      "supported_operations": ["notify", "status_update", "alert"]
    }
  ]
}
```

**Enable Integration:**
```http
POST /integrations/{integration_id}/enable
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "config": {
    "sync_frequency": "hourly",
    "folders": ["Documents", "Projects"],
    "file_types": ["pdf", "docx", "txt"],
    "conflict_resolution": "keep_both",
    "notifications": {
      "enabled": true,
      "channel": "#file-updates"
    }
  },
  "credentials": {
    "api_token": "encrypted_token_here",
    "database_id": "notion_database_id"
  }
}
```

**Get Integration Status:**
```http
GET /integrations/{integration_id}
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "id": "notion-sync",
  "name": "Notion Sync",
  "status": "active",
  "enabled_at": "2024-01-15T10:30:00Z",
  "last_sync": "2024-01-15T16:00:00Z",
  "next_sync": "2024-01-15T17:00:00Z",
  "config": {
    "sync_frequency": "hourly",
    "folders": ["Documents", "Projects"],
    "file_types": ["pdf", "docx", "txt"]
  },
  "stats": {
    "files_synced": 234,
    "last_sync_duration_ms": 5420,
    "errors_last_24h": 0,
    "data_transferred_bytes": 104857600
  },
  "health": {
    "status": "healthy",
    "last_error": null,
    "uptime_percentage": 99.8
  }
}
```

### 7.2 Custom Integration Development

**Integration Framework Example:**
```python
# Example: Custom CRM Integration
from activelog.integrations import BaseIntegration
import requests

class CRMIntegration(BaseIntegration):
    name = "custom-crm"
    display_name = "Custom CRM System"
    description = "Sync customer documents with CRM"
    version = "1.0.0"
    
    def __init__(self, config):
        super().__init__(config)
        self.api_base = config.get('api_base')
        self.api_key = config.get('api_key')
        
    def authenticate(self):
        """Authenticate with the CRM system"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f'{self.api_base}/auth/validate', headers=headers)
        return response.status_code == 200
    
    def sync_customer_documents(self, customer_id):
        """Sync documents for a specific customer"""
        # Get customer files from ActiveLog
        files = self.activelog_client.files.list(
            filters={'tags': [f'customer-{customer_id}']},
            limit=100
        )
        
        # Upload to CRM system
        for file in files:
            crm_response = self.upload_to_crm(customer_id, file)
            
            if crm_response.success:
                # Update file metadata in ActiveLog
                self.activelog_client.files.update_metadata(
                    file.id,
                    {'crm_sync_status': 'synced', 'crm_id': crm_response.id}
                )
    
    def upload_to_crm(self, customer_id, file):
        """Upload file to CRM system"""
        files_data = {
            'file': (file.name, file.download(), file.mime_type)
        }
        
        data = {
            'customer_id': customer_id,
            'document_type': file.metadata.get('category', 'general'),
            'tags': ','.join(file.tags)
        }
        
        response = requests.post(
            f'{self.api_base}/customers/{customer_id}/documents',
            headers={'Authorization': f'Bearer {self.api_key}'},
            files=files_data,
            data=data
        )
        
        return response
    
    def webhook_handler(self, webhook_data):
        """Handle webhooks from CRM system"""
        event_type = webhook_data.get('event_type')
        
        if event_type == 'customer_updated':
            customer_id = webhook_data['customer_id']
            self.sync_customer_documents(customer_id)
        elif event_type == 'document_deleted':
            # Handle document deletion
            crm_document_id = webhook_data['document_id']
            self.handle_crm_document_deletion(crm_document_id)
```

### 7.3 OAuth 2.0 Integration Pattern

**OAuth Flow Implementation:**
```javascript
// OAuth 2.0 Integration with Third-Party Service
class OAuth2Integration {
    constructor(clientId, clientSecret, redirectUri) {
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.redirectUri = redirectUri;
        this.authUrl = 'https://provider.com/oauth/authorize';
        this.tokenUrl = 'https://provider.com/oauth/token';
    }
    
    // Step 1: Generate authorization URL
    getAuthorizationUrl(scopes = [], state = null) {
        const params = new URLSearchParams({
            response_type: 'code',
            client_id: this.clientId,
            redirect_uri: this.redirectUri,
            scope: scopes.join(' '),
            state: state || this.generateState()
        });
        
        return `${this.authUrl}?${params.toString()}`;
    }
    
    // Step 2: Exchange authorization code for access token
    async exchangeCodeForToken(authorizationCode) {
        const response = await fetch(this.tokenUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': `Basic ${btoa(`${this.clientId}:${this.clientSecret}`)}`
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code: authorizationCode,
                redirect_uri: this.redirectUri
            })
        });
        
        const tokenData = await response.json();
        
        if (response.ok) {
            // Store tokens securely
            await this.storeTokens(tokenData);
            return tokenData;
        } else {
            throw new Error(`Token exchange failed: ${tokenData.error}`);
        }
    }
    
    // Step 3: Refresh access token when needed
    async refreshAccessToken(refreshToken) {
        const response = await fetch(this.tokenUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': `Basic ${btoa(`${this.clientId}:${this.clientSecret}`)}`
            },
            body: new URLSearchParams({
                grant_type: 'refresh_token',
                refresh_token: refreshToken
            })
        });
        
        const tokenData = await response.json();
        
        if (response.ok) {
            await this.storeTokens(tokenData);
            return tokenData;
        } else {
            throw new Error(`Token refresh failed: ${tokenData.error}`);
        }
    }
    
    // Make authenticated API requests
    async makeAuthenticatedRequest(url, options = {}) {
        const tokens = await this.getStoredTokens();
        
        if (!tokens || this.isTokenExpired(tokens)) {
            if (tokens.refresh_token) {
                await this.refreshAccessToken(tokens.refresh_token);
                tokens = await this.getStoredTokens();
            } else {
                throw new Error('Authentication required');
            }
        }
        
        const headers = {
            'Authorization': `Bearer ${tokens.access_token}`,
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        return fetch(url, {
            ...options,
            headers
        });
    }
    
    // Helper methods
    generateState() {
        return Math.random().toString(36).substring(2, 15) + 
               Math.random().toString(36).substring(2, 15);
    }
    
    isTokenExpired(tokens) {
        const now = Date.now() / 1000;
        const expiresAt = tokens.created_at + tokens.expires_in;
        return now >= (expiresAt - 300); // Refresh 5 minutes early
    }
    
    async storeTokens(tokenData) {
        // Store tokens securely in your system
        const tokensWithTimestamp = {
            ...tokenData,
            created_at: Math.floor(Date.now() / 1000)
        };
        
        // Save to database or secure storage
        await this.saveToSecureStorage('oauth_tokens', tokensWithTimestamp);
    }
    
    async getStoredTokens() {
        return await this.getFromSecureStorage('oauth_tokens');
    }
}
```

---

## SDK and Client Libraries

### 8.1 Official SDKs

**JavaScript/TypeScript SDK:**
```typescript
import { ActiveLogClient } from '@activelog/sdk';

// Initialize client
const client = new ActiveLogClient({
    apiToken: process.env.ACTIVELOG_API_KEY,
    baseUrl: 'https://beta-api.activelog.dev/v1',
    timeout: 30000,
    retries: 3
});

// Upload file
const file = await client.files.upload({
    file: fs.createReadStream('document.pdf'),
    projectId: 'proj_123',
    metadata: {
        tags: ['important', 'Q4'],
        category: 'report'
    },
    options: {
        generateThumbnail: true,
        autoOCR: true
    }
});

// Search files
const searchResults = await client.search.query({
    query: 'quarterly financial report',
    filters: {
        fileTypes: ['pdf', 'docx'],
        dateFrom: '2024-01-01',
        tags: ['financial']
    },
    limit: 20,
    includeHighlights: true
});

// Create project
const project = await client.projects.create({
    name: 'Q4 Analytics Project',
    description: 'End-of-year analysis and reporting',
    settings: {
        private: false,
        features: ['ai_insights', 'real_time_sync']
    }
});

// Real-time collaboration
const collaboration = await client.collaboration.startSession({
    documentId: 'doc_123',
    permissions: ['read', 'write', 'comment']
});

collaboration.on('userJoined', (user) => {
    console.log(`${user.name} joined the session`);
});

collaboration.on('operation', (op) => {
    // Handle real-time document operations
    applyOperationToDocument(op);
});
```

**Python SDK:**
```python
from activelog import ActiveLogClient
import asyncio

# Initialize client
client = ActiveLogClient(
    api_token=os.getenv('ACTIVELOG_API_KEY'),
    base_url='https://beta-api.activelog.dev/v1',
    timeout=30,
    max_retries=3
)

# Upload file with metadata
async def upload_file():
    with open('financial-report.pdf', 'rb') as f:
        file = await client.files.upload(
            file=f,
            project_id='proj_123',
            metadata={
                'tags': ['financial', 'Q4', 'report'],
                'category': 'business',
                'department': 'finance'
            },
            auto_ocr=True,
            generate_thumbnail=True
        )
    
    print(f"File uploaded: {file.id}")
    return file

# Advanced search
async def search_documents():
    results = await client.search.advanced({
        'query': {
            'bool': {
                'must': [
                    {'match': {'content': 'revenue growth'}},
                    {'terms': {'tags': ['financial', 'report']}}
                ],
                'filter': [
                    {'range': {'file_size': {'gte': 100000}}},
                    {'range': {'created_date': {'gte': '2024-01-01'}}}
                ]
            }
        },
        'sort': [{'_score': {'order': 'desc'}}],
        'limit': 50
    })
    
    return results

# Bulk operations
async def bulk_update_metadata():
    file_ids = ['file_123', 'file_456', 'file_789']
    
    result = await client.files.bulk_update({
        'file_ids': file_ids,
        'metadata': {
            'tags': ['archived', '2024'],
            'status': 'processed'
        },
        'folder_path': '/Archive/2024'
    })
    
    return result

# Analytics and reporting
async def generate_analytics():
    analytics = await client.analytics.dashboard({
        'period': '30d',
        'metrics': ['uploads', 'searches', 'storage'],
        'breakdown': ['file_type', 'project', 'user']
    })
    
    return analytics

# Run async operations
async def main():
    # Upload file
    file = await upload_file()
    
    # Search documents
    search_results = await search_documents()
    print(f"Found {len(search_results.results)} documents")
    
    # Generate analytics
    analytics = await generate_analytics()
    print(f"Total files: {analytics.summary.total_files}")

if __name__ == "__main__":
    asyncio.run(main())
```

**PHP SDK:**
```php
<?php
require_once 'vendor/autoload.php';

use ActiveLog\Client;
use ActiveLog\Configuration;

// Initialize client
$config = new Configuration();
$config->setApiKey(getenv('ACTIVELOG_API_KEY'));
$config->setBaseUrl('https://beta-api.activelog.dev/v1');
$config->setTimeout(30);

$client = new Client($config);

// Upload file
function uploadFile($client) {
    $file = new \SplFileInfo('quarterly-report.pdf');
    
    $upload = $client->files()->upload([
        'file' => $file,
        'project_id' => 'proj_123',
        'metadata' => [
            'tags' => ['quarterly', 'financial', 'report'],
            'category' => 'business',
            'author' => 'Finance Team'
        ],
        'auto_ocr' => true,
        'generate_thumbnail' => true
    ]);
    
    return $upload;
}

// Search files
function searchFiles($client) {
    $results = $client->search()->query([
        'q' => 'financial quarterly report',
        'file_types' => ['pdf', 'xlsx'],
        'tags' => ['financial'],
        'date_from' => '2024-01-01',
        'limit' => 25,
        'sort' => 'relevance'
    ]);
    
    return $results;
}

// Create project
function createProject($client) {
    $project = $client->projects()->create([
        'name' => 'Financial Analysis 2024',
        'description' => 'Comprehensive financial analysis project',
        'settings' => [
            'private' => false,
            'features' => ['ai_insights', 'collaboration']
        ]
    ]);
    
    return $project;
}

// Get analytics
function getAnalytics($client) {
    $analytics = $client->analytics()->dashboard([
        'period' => '60d',
        'include' => ['uploads', 'searches', 'storage', 'users']
    ]);
    
    return $analytics;
}

// Error handling
try {
    $file = uploadFile($client);
    echo "File uploaded successfully: " . $file->getId() . "\n";
    
    $results = searchFiles($client);
    echo "Search found " . count($results->getResults()) . " files\n";
    
    $project = createProject($client);
    echo "Project created: " . $project->getId() . "\n";
    
    $analytics = getAnalytics($client);
    echo "Total storage used: " . $analytics->getSummary()->getTotalStorage() . " bytes\n";
    
} catch (ActiveLog\Exception\ApiException $e) {
    echo "API Error: " . $e->getMessage() . "\n";
    echo "Error Code: " . $e->getCode() . "\n";
} catch (Exception $e) {
    echo "General Error: " . $e->getMessage() . "\n";
}
?>
```

### 8.2 SDK Configuration and Best Practices

**Environment Configuration:**
```yaml
# .env configuration for SDKs
ACTIVELOG_API_KEY=al_your_api_key_here
ACTIVELOG_BASE_URL=https://beta-api.activelog.dev/v1
ACTIVELOG_TIMEOUT=30
ACTIVELOG_MAX_RETRIES=3
ACTIVELOG_RETRY_DELAY=1000
ACTIVELOG_DEBUG=false

# Rate limiting configuration
ACTIVELOG_RATE_LIMIT_ENABLED=true
ACTIVELOG_RATE_LIMIT_REQUESTS=1000
ACTIVELOG_RATE_LIMIT_WINDOW=3600

# Caching configuration
ACTIVELOG_CACHE_ENABLED=true
ACTIVELOG_CACHE_TTL=300
ACTIVELOG_CACHE_MAX_SIZE=100
```

**Error Handling Best Practices:**
```typescript
import { ActiveLogClient, ActiveLogError } from '@activelog/sdk';

const client = new ActiveLogClient({
    apiToken: process.env.ACTIVELOG_API_KEY,
    retryConfig: {
        retries: 3,
        retryDelay: 1000,
        retryCondition: (error) => {
            // Retry on network errors and 5xx server errors
            return !error.response || error.response.status >= 500;
        }
    }
});

// Comprehensive error handling
async function uploadFileWithErrorHandling(filePath: string) {
    try {
        const file = await client.files.upload({
            file: fs.createReadStream(filePath),
            projectId: 'proj_123'
        });
        
        return file;
        
    } catch (error) {
        if (error instanceof ActiveLogError) {
            switch (error.code) {
                case 'RATE_LIMIT_EXCEEDED':
                    console.warn('Rate limit exceeded, waiting before retry...');
                    await sleep(error.retryAfter * 1000);
                    return uploadFileWithErrorHandling(filePath);
                    
                case 'VALIDATION_ERROR':
                    console.error('Validation failed:', error.details);
                    throw error;
                    
                case 'STORAGE_QUOTA_EXCEEDED':
                    console.error('Storage quota exceeded, cannot upload file');
                    throw error;
                    
                case 'FILE_TOO_LARGE':
                    console.error(`File too large: ${filePath}`);
                    throw error;
                    
                default:
                    console.error('API Error:', error.message);
                    throw error;
            }
        } else {
            console.error('Unexpected error:', error);
            throw error;
        }
    }
}
```

---

## Webhook System

### 9.1 Webhook Configuration

**Create Webhook:**
```http
POST /webhooks
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "url": "https://your-app.com/webhooks/activelog",
  "events": [
    "file.uploaded",
    "file.deleted",
    "project.created",
    "project.updated",
    "user.invited",
    "integration.synced"
  ],
  "secret": "your-webhook-secret-key",
  "active": true,
  "description": "Main application webhook",
  "retry_config": {
    "max_attempts": 3,
    "backoff_multiplier": 2,
    "initial_delay": 1000
  },
  "filters": {
    "project_ids": ["proj_123", "proj_456"],
    "user_ids": ["user_789"]
  }
}
```

**Response:**
```json
{
  "id": "webhook_abc123",
  "url": "https://your-app.com/webhooks/activelog",
  "events": [
    "file.uploaded",
    "file.deleted",
    "project.created",
    "project.updated",
    "user.invited",
    "integration.synced"
  ],
  "secret": "webhook-secret-preview",
  "active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_delivery": null,
  "delivery_stats": {
    "success_count": 0,
    "failure_count": 0,
    "last_success": null,
    "last_failure": null
  }
}
```

### 9.2 Webhook Events

**Available Events:**
```yaml
File Events:
  file.uploaded: New file uploaded to the platform
  file.updated: File metadata or content updated
  file.deleted: File moved to trash or permanently deleted
  file.shared: File shared with users or made public
  file.downloaded: File accessed or downloaded
  file.processed: File processing (OCR, AI analysis) completed

Project Events:
  project.created: New project created
  project.updated: Project settings or metadata changed
  project.deleted: Project deleted
  project.member_added: User added to project
  project.member_removed: User removed from project
  project.shared: Project shared with external users

User Events:
  user.registered: New user account created
  user.login: User authentication event
  user.profile_updated: User profile information changed
  user.invited: User invited to project or organization

Integration Events:
  integration.enabled: Third-party integration activated
  integration.disabled: Third-party integration deactivated
  integration.synced: Integration sync operation completed
  integration.error: Integration encountered an error

System Events:
  quota.warning: Approaching storage or usage limits
  quota.exceeded: Storage or usage limits reached
  security.suspicious_activity: Potential security issue detected
  maintenance.scheduled: Scheduled maintenance notification
```

### 9.3 Webhook Payload Format

**Standard Webhook Payload:**
```json
{
  "event": "file.uploaded",
  "event_id": "evt_abc123def456",
  "timestamp": "2024-01-15T10:30:00Z",
  "webhook_id": "webhook_abc123",
  "data": {
    "file": {
      "id": "file_789012",
      "name": "quarterly-report.pdf",
      "size": 2048576,
      "mime_type": "application/pdf",
      "project_id": "proj_123456",
      "metadata": {
        "tags": ["report", "Q4", "financial"],
        "category": "business"
      },
      "urls": {
        "download": "https://files.activelog.dev/file_789012",
        "preview": "https://preview.activelog.dev/file_789012"
      },
      "created_at": "2024-01-15T10:30:00Z"
    },
    "user": {
      "id": "user_123456",
      "email": "user@example.com",
      "name": "John Doe"
    },
    "project": {
      "id": "proj_123456",
      "name": "Financial Analysis Project"
    }
  },
  "previous_data": null,
  "context": {
    "source": "web_app",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
  }
}
```

**Project Updated Event:**
```json
{
  "event": "project.updated",
  "event_id": "evt_def789ghi012",
  "timestamp": "2024-01-15T14:22:00Z",
  "webhook_id": "webhook_abc123",
  "data": {
    "project": {
      "id": "proj_123456",
      "name": "Updated Financial Analysis Project",
      "description": "Q4 2024 comprehensive financial analysis",
      "settings": {
        "private": false,
        "features": ["ai_insights", "real_time_sync", "advanced_analytics"]
      }
    },
    "user": {
      "id": "user_123456",
      "email": "user@example.com",
      "name": "John Doe"
    },
    "changes": {
      "name": {
        "old": "Financial Analysis Project",
        "new": "Updated Financial Analysis Project"
      },
      "settings.features": {
        "old": ["ai_insights", "real_time_sync"],
        "new": ["ai_insights", "real_time_sync", "advanced_analytics"]
      }
    }
  }
}
```

### 9.4 Webhook Security and Verification

**Webhook Signature Verification:**
```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
    const expectedSignature = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');
    
    const expectedSignatureWithPrefix = `sha256=${expectedSignature}`;
    
    return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignatureWithPrefix)
    );
}

// Express.js webhook handler
app.post('/webhooks/activelog', express.raw({type: 'application/json'}), (req, res) => {
    const signature = req.headers['x-activelog-signature'];
    const payload = req.body;
    
    if (!verifyWebhookSignature(payload, signature, process.env.WEBHOOK_SECRET)) {
        console.error('Invalid webhook signature');
        return res.status(401).send('Unauthorized');
    }
    
    const event = JSON.parse(payload.toString());
    
    // Process webhook event
    handleWebhookEvent(event);
    
    res.status(200).send('OK');
});

function handleWebhookEvent(event) {
    console.log(`Received webhook event: ${event.event}`);
    
    switch (event.event) {
        case 'file.uploaded':
            handleFileUploaded(event.data);
            break;
        case 'project.updated':
            handleProjectUpdated(event.data);
            break;
        case 'user.invited':
            handleUserInvited(event.data);
            break;
        default:
            console.log(`Unhandled event type: ${event.event}`);
    }
}

function handleFileUploaded(data) {
    const file = data.file;
    const user = data.user;
    
    console.log(`File uploaded: ${file.name} by ${user.name}`);
    
    // Trigger custom business logic
    if (file.metadata.tags.includes('important')) {
        sendSlackNotification(`Important file uploaded: ${file.name}`);
    }
    
    // Update external systems
    updateCRMSystem(file, user);
}

function handleProjectUpdated(data) {
    const project = data.project;
    const changes = data.changes;
    
    console.log(`Project updated: ${project.name}`);
    console.log('Changes:', changes);
    
    // Notify team members
    notifyProjectMembers(project.id, changes);
}
```

**Webhook Retry Logic:**
```python
import requests
import time
from typing import Dict, Any

class WebhookDelivery:
    def __init__(self, webhook_url: str, secret: str, max_attempts: int = 3):
        self.webhook_url = webhook_url
        self.secret = secret
        self.max_attempts = max_attempts
        self.backoff_multiplier = 2
        self.initial_delay = 1
    
    def deliver_webhook(self, payload: Dict[Any, Any]) -> bool:
        """Deliver webhook with exponential backoff retry logic"""
        import json
        import hmac
        import hashlib
        
        payload_json = json.dumps(payload)
        signature = hmac.new(
            self.secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Content-Type': 'application/json',
            'X-ActiveLog-Signature': f'sha256={signature}',
            'X-ActiveLog-Event': payload['event'],
            'X-ActiveLog-Delivery-ID': payload['event_id']
        }
        
        for attempt in range(self.max_attempts):
            try:
                response = requests.post(
                    self.webhook_url,
                    data=payload_json,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return True
                elif response.status_code >= 500:
                    # Server error, retry
                    pass
                else:
                    # Client error, don't retry
                    return False
                    
            except requests.exceptions.RequestException as e:
                print(f"Webhook delivery attempt {attempt + 1} failed: {e}")
            
            if attempt < self.max_attempts - 1:
                delay = self.initial_delay * (self.backoff_multiplier ** attempt)
                time.sleep(delay)
        
        return False
```

### 9.5 Webhook Management

**List Webhooks:**
```http
GET /webhooks?active=true&limit=50
Authorization: Bearer jwt_token
```

**Update Webhook:**
```http
PUT /webhooks/{webhook_id}
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "events": [
    "file.uploaded",
    "file.updated",
    "project.created"
  ],
  "active": false,
  "retry_config": {
    "max_attempts": 5,
    "backoff_multiplier": 3
  }
}
```

**Test Webhook:**
```http
POST /webhooks/{webhook_id}/test
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "event_type": "test",
  "include_sample_data": true
}
```

**Webhook Delivery Logs:**
```http
GET /webhooks/{webhook_id}/deliveries?limit=100&status=failed
Authorization: Bearer jwt_token
```

**Response:**
```json
{
  "deliveries": [
    {
      "id": "delivery_abc123",
      "event_id": "evt_def456",
      "event_type": "file.uploaded",
      "status": "success",
      "response_status": 200,
      "response_time_ms": 245,
      "attempts": 1,
      "delivered_at": "2024-01-15T10:30:05Z",
      "next_retry_at": null
    },
    {
      "id": "delivery_ghi789",
      "event_id": "evt_jkl012",
      "event_type": "project.updated",
      "status": "failed",
      "response_status": 500,
      "response_time_ms": 30000,
      "attempts": 3,
      "last_attempt_at": "2024-01-15T10:35:00Z",
      "next_retry_at": "2024-01-15T10:40:00Z",
      "error_message": "Internal Server Error"
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 100,
    "offset": 0,
    "has_more": true
  },
  "stats": {
    "success_rate": 0.94,
    "average_response_time_ms": 312,
    "total_deliveries": 1547
  }
}
```

---

## Rate Limiting and Error Handling

### 10.1 Rate Limiting

**Rate Limit Configuration:**
```yaml
Default Rate Limits (Beta):
  General API: 10,000 requests/hour
  Burst Allowance: 100 requests/minute
  File Uploads: 50 uploads/hour (up to 1GB each)
  Search Queries: 1,000 queries/hour
  WebSocket Connections: 10 concurrent connections/user

Premium Rate Limits:
  General API: 50,000 requests/hour
  Burst Allowance: 500 requests/minute
  File Uploads: 200 uploads/hour (up to 5GB each)
  Search Queries: 5,000 queries/hour
  WebSocket Connections: 25 concurrent connections/user

Enterprise Rate Limits:
  Custom limits based on contract
  Dedicated rate limit pools
  Priority queuing for API requests
  SLA guarantees for response times
```

**Rate Limit Headers:**
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9995
X-RateLimit-Reset: 1642694400
X-RateLimit-Reset-After: 3540
X-RateLimit-Burst-Limit: 100
X-RateLimit-Burst-Remaining: 99
Retry-After: 60
```

**Rate Limit Exceeded Response:**
```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642694400
Retry-After: 3540

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 10000,
      "remaining": 0,
      "reset_at": "2024-01-15T11:00:00Z",
      "retry_after": 3540
    },
    "request_id": "req_abc123def456",
    "documentation": "https://docs.activelog.com/api/rate-limits"
  }
}
```

### 10.2 Error Response Format

**Standard Error Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format",
        "code": "INVALID_FORMAT"
      },
      {
        "field": "password",
        "message": "Password must be at least 8 characters",
        "code": "TOO_SHORT"
      }
    ],
    "request_id": "req_abc123def456",
    "timestamp": "2024-01-15T10:30:00Z",
    "documentation": "https://docs.activelog.com/api/errors#validation-error",
    "support_url": "https://support.activelog.com/new-ticket?request_id=req_abc123def456"
  }
}
```

### 10.3 Common Error Codes

**Authentication and Authorization Errors:**
```yaml
INVALID_TOKEN:
  Status: 401
  Description: API token is invalid or malformed
  Resolution: Generate a new API token

EXPIRED_TOKEN:
  Status: 401
  Description: API token has expired
  Resolution: Refresh token or generate new one

INSUFFICIENT_PERMISSIONS:
  Status: 403
  Description: Token lacks required permissions for this operation
  Resolution: Check token scopes or request elevated permissions

ACCOUNT_SUSPENDED:
  Status: 403
  Description: User account has been suspended
  Resolution: Contact support for account reinstatement
```

**Request Validation Errors:**
```yaml
VALIDATION_ERROR:
  Status: 422
  Description: Request validation failed
  Resolution: Fix request parameters according to API documentation

MISSING_REQUIRED_FIELD:
  Status: 400
  Description: Required field is missing from request
  Resolution: Include all required fields

INVALID_FIELD_FORMAT:
  Status: 400
  Description: Field value format is invalid
  Resolution: Use correct format for field values

FIELD_TOO_LONG:
  Status: 400
  Description: Field value exceeds maximum length
  Resolution: Reduce field value length
```

**Resource Errors:**
```yaml
RESOURCE_NOT_FOUND:
  Status: 404
  Description: Requested resource does not exist
  Resolution: Verify resource ID is correct

RESOURCE_ALREADY_EXISTS:
  Status: 409
  Description: Resource with same identifier already exists
  Resolution: Use different identifier or update existing resource

RESOURCE_IN_USE:
  Status: 409
  Description: Resource cannot be deleted as it's being used
  Resolution: Remove dependencies before deleting

RESOURCE_LOCKED:
  Status: 423
  Description: Resource is locked and cannot be modified
  Resolution: Wait for lock to release or contact support
```

**Quota and Limit Errors:**
```yaml
STORAGE_QUOTA_EXCEEDED:
  Status: 413
  Description: Account storage limit has been reached
  Resolution: Delete files or upgrade storage plan

FILE_TOO_LARGE:
  Status: 413
  Description: File size exceeds upload limit
  Resolution: Reduce file size or upgrade plan for larger uploads

API_QUOTA_EXCEEDED:
  Status: 429
  Description: API usage quota exceeded for current period
  Resolution: Wait for quota reset or upgrade plan

CONCURRENT_REQUESTS_EXCEEDED:
  Status: 429
  Description: Too many concurrent requests
  Resolution: Reduce concurrent request count
```

### 10.4 Error Handling Best Practices

**Client-Side Error Handling:**
```typescript
import { ActiveLogClient, ActiveLogError } from '@activelog/sdk';

class APIErrorHandler {
    static async handleWithRetry<T>(
        operation: () => Promise<T>,
        maxRetries: number = 3,
        baseDelay: number = 1000
    ): Promise<T> {
        let lastError: ActiveLogError;
        
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                lastError = error as ActiveLogError;
                
                // Don't retry on certain error types
                if (this.shouldNotRetry(lastError)) {
                    throw lastError;
                }
                
                // For rate limiting, use the retry-after header
                if (lastError.code === 'RATE_LIMIT_EXCEEDED') {
                    const retryAfter = lastError.retryAfter || baseDelay;
                    await this.sleep(retryAfter * 1000);
                    continue;
                }
                
                // For other retryable errors, use exponential backoff
                if (attempt < maxRetries && this.isRetryable(lastError)) {
                    const delay = baseDelay * Math.pow(2, attempt);
                    await this.sleep(delay);
                    continue;
                }
                
                throw lastError;
            }
        }
        
        throw lastError;
    }
    
    static shouldNotRetry(error: ActiveLogError): boolean {
        const nonRetryableCodes = [
            'INVALID_TOKEN',
            'EXPIRED_TOKEN',
            'INSUFFICIENT_PERMISSIONS',
            'VALIDATION_ERROR',
            'RESOURCE_NOT_FOUND',
            'STORAGE_QUOTA_EXCEEDED',
            'FILE_TOO_LARGE'
        ];
        
        return nonRetryableCodes.includes(error.code);
    }
    
    static isRetryable(error: ActiveLogError): boolean {
        const retryableCodes = [
            'INTERNAL_SERVER_ERROR',
            'SERVICE_UNAVAILABLE',
            'TIMEOUT',
            'NETWORK_ERROR'
        ];
        
        return retryableCodes.includes(error.code) || 
               (error.status >= 500 && error.status < 600);
    }
    
    static sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    static logError(error: ActiveLogError, context: any = {}): void {
        console.error('ActiveLog API Error:', {
            code: error.code,
            message: error.message,
            status: error.status,
            requestId: error.requestId,
            timestamp: new Date().toISOString(),
            context
        });
        
        // Send to error tracking service
        if (process.env.NODE_ENV === 'production') {
            this.sendToErrorTracking(error, context);
        }
    }
    
    private static sendToErrorTracking(error: ActiveLogError, context: any): void {
        // Send to your error tracking service (Sentry, Rollbar, etc.)
        // errorTracker.captureException(error, { extra: context });
    }
}

// Usage example
async function uploadFileWithErrorHandling(filePath: string) {
    try {
        const result = await APIErrorHandler.handleWithRetry(async () => {
            return client.files.upload({
                file: fs.createReadStream(filePath),
                projectId: 'proj_123',
                metadata: { tags: ['important'] }
            });
        }, 3, 1000);
        
        console.log('File uploaded successfully:', result.id);
        return result;
        
    } catch (error) {
        APIErrorHandler.logError(error as ActiveLogError, { filePath });
        
        // Handle specific error types
        switch (error.code) {
            case 'STORAGE_QUOTA_EXCEEDED':
                throw new Error('Cannot upload file: Storage quota exceeded. Please upgrade your plan or delete some files.');
            case 'FILE_TOO_LARGE':
                throw new Error('Cannot upload file: File is too large for your current plan.');
            case 'INVALID_TOKEN':
                throw new Error('Authentication failed: Please check your API token.');
            default:
                throw new Error(`Upload failed: ${error.message}`);
        }
    }
}
```

---

## Environment Configuration

### 11.1 Environment Variables Reference

ActiveLog services use environment variables for configuration. Here's a comprehensive reference organized by category:

**Database Configuration:**
```bash
# PostgreSQL Database
POSTGRES_HOST=localhost          # Database server hostname
POSTGRES_PORT=5432              # Database server port
POSTGRES_DB=activelog           # Database name
POSTGRES_USER=postgres          # Database username
POSTGRES_PASSWORD=password      # Database password
DATABASE_URL=postgresql://user:pass@host:5432/db  # Full connection string

# Connection Pool Settings
DB_POOL_MIN_SIZE=5              # Minimum connections in pool
DB_POOL_MAX_SIZE=20             # Maximum connections in pool
DB_POOL_MAX_OVERFLOW=10         # Additional connections allowed
DB_POOL_TIMEOUT=30              # Connection timeout (seconds)
DB_POOL_RECYCLE=3600           # Connection recycle time (seconds)
```

**Cache Configuration:**
```bash
# Redis Cache
REDIS_URL=redis://localhost:6379/0  # Redis connection string
REDIS_HOST=localhost            # Redis server hostname
REDIS_PORT=6379                 # Redis server port
REDIS_DB=0                      # Redis database number
REDIS_PASSWORD=                 # Redis password (if required)

# Cache Behavior
CACHE_TTL_DEFAULT=3600         # Default cache expiration (seconds)
CACHE_TTL_SHORT=300            # Short-lived cache (seconds)
CACHE_TTL_LONG=86400           # Long-lived cache (seconds)
CACHE_MAX_MEMORY=256mb         # Max memory usage
```

**Storage Configuration:**
```bash
# Object Storage (S3/MinIO)
STORAGE_BACKEND=minio          # Storage backend type (s3, minio, gcs, azure)
STORAGE_ENDPOINT=http://minio:9000  # Storage endpoint URL
STORAGE_ACCESS_KEY=minio_admin  # Access key ID
STORAGE_SECRET_KEY=minio_password  # Secret access key
STORAGE_BUCKET_NAME=activelog  # Primary bucket name
STORAGE_REGION=us-east-1       # Storage region

# File Upload Limits
MAX_FILE_SIZE=104857600        # Maximum file size (bytes)
MAX_FILES_PER_UPLOAD=100       # Max files per batch upload
UPLOAD_TIMEOUT=300             # Upload timeout (seconds)
ALLOWED_FILE_TYPES=*           # Comma-separated extensions or *
```

**Authentication & Security:**
```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key  # JWT signing key (required)
JWT_ALGORITHM=HS256            # JWT signing algorithm
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15  # Access token expiration
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7     # Refresh token expiration
JWT_ISSUER=activelog           # Token issuer

# Password Security
PASSWORD_MIN_LENGTH=8          # Minimum password length
PASSWORD_REQUIRE_UPPERCASE=true # Require uppercase letter
PASSWORD_REQUIRE_LOWERCASE=true # Require lowercase letter
PASSWORD_REQUIRE_NUMBERS=true  # Require numbers
PASSWORD_REQUIRE_SYMBOLS=false # Require symbols
PASSWORD_BCRYPT_ROUNDS=12      # Bcrypt hash rounds

# Rate Limiting
RATE_LIMIT_ENABLED=true        # Enable rate limiting
RATE_LIMIT_REQUESTS=100        # Requests per window
RATE_LIMIT_WINDOW=3600         # Time window (seconds)
```

**AI & ML Configuration:**
```bash
# OpenAI Integration
OPENAI_API_KEY=sk-proj-...     # OpenAI API key
OPENAI_MODEL=gpt-3.5-turbo     # Default model to use
OPENAI_MAX_TOKENS=2048         # Max tokens per request
OPENAI_TEMPERATURE=0.7         # Response creativity
OPENAI_TIMEOUT=30              # Request timeout (seconds)

# Embedding Models
EMBEDDING_MODEL=text-embedding-ada-002  # Default embedding model
EMBEDDING_DIMENSIONS=1536      # Embedding dimensions
EMBEDDING_BATCH_SIZE=100       # Batch processing size
VECTOR_DB_TYPE=pinecone        # Vector database type

# Document Processing
OCR_ENABLED=true               # Enable OCR processing
OCR_LANGUAGE=eng               # OCR language
OCR_CONFIDENCE_THRESHOLD=0.7   # Min confidence level
TEXT_EXTRACTION_TIMEOUT=120    # Processing timeout (seconds)
```

**Search Configuration:**
```bash
# Elasticsearch Settings
ELASTICSEARCH_URL=http://elasticsearch:9200  # Elasticsearch endpoint
ELASTICSEARCH_USERNAME=        # Authentication username
ELASTICSEARCH_PASSWORD=        # Authentication password
ELASTICSEARCH_INDEX_PREFIX=activelog  # Index name prefix

# Search Behavior
SEARCH_RESULTS_PER_PAGE=20     # Results per page
SEARCH_MAX_RESULTS=1000        # Maximum total results
SEARCH_TIMEOUT=30              # Search timeout (seconds)
SEARCH_MIN_SCORE=0.1           # Minimum relevance score
```

**Application Configuration:**
```bash
# General Settings
ENVIRONMENT=development        # Deployment environment
DEBUG=false                    # Enable debug mode
SECRET_KEY=your-secret-key     # Application secret key
APP_NAME=ActiveLog            # Application name
APP_VERSION=1.0.0             # Application version

# API Configuration
API_PREFIX=/api/v1            # API URL prefix
API_DOCS_URL=/docs            # API documentation URL
API_REDOC_URL=/redoc          # ReDoc documentation URL
API_OPENAPI_URL=/openapi.json # OpenAPI spec URL

# CORS Configuration
CORS_ALLOW_ORIGINS=*          # Allowed origins
CORS_ALLOW_METHODS=*          # Allowed HTTP methods
CORS_ALLOW_HEADERS=*          # Allowed headers
CORS_ALLOW_CREDENTIALS=true   # Allow credentials
```

### 11.2 Environment-Specific Configurations

**Development Environment (.env.development):**
```bash
DEBUG=true
LOG_LEVEL=DEBUG
CORS_ALLOW_ORIGINS=*
CACHE_TTL_DEFAULT=300
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=5
METRICS_ENABLED=false
TRACING_ENABLED=false
RATE_LIMIT_ENABLED=false
OCR_ENABLED=false
AI_FEATURES_ENABLED=false
```

**Staging Environment (.env.staging):**
```bash
DEBUG=false
LOG_LEVEL=INFO
CORS_ALLOW_ORIGINS=https://staging.activelog.com
CACHE_TTL_DEFAULT=1800
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=15
METRICS_ENABLED=true
TRACING_ENABLED=true
RATE_LIMIT_ENABLED=true
OCR_ENABLED=true
AI_FEATURES_ENABLED=true
```

**Production Environment (.env.production):**
```bash
DEBUG=false
LOG_LEVEL=WARNING
CORS_ALLOW_ORIGINS=https://app.activelog.com
CACHE_TTL_DEFAULT=3600
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=50
METRICS_ENABLED=true
TRACING_ENABLED=true
RATE_LIMIT_ENABLED=true
SESSION_SECURE=true
PASSWORD_REQUIRE_SYMBOLS=true
OCR_ENABLED=true
AI_FEATURES_ENABLED=true
```

### 11.3 Configuration Validation

**Environment Variable Validation Script:**
```bash
#!/bin/bash
# validate-config.sh

set -e

echo "🔍 Validating ActiveLog environment configuration..."

# Required variables
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "JWT_SECRET_KEY" 
    "STORAGE_SECRET_KEY"
    "SECRET_KEY"
)

# Check required variables
echo "Checking required variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "❌ Error: Required variable $var is not set"
        exit 1
    else
        echo "✅ $var is set"
    fi
done

# Security validation
echo "Validating security configuration..."

if [[ "$JWT_SECRET_KEY" == "your-super-secret-jwt-key" ]] || [[ ${#JWT_SECRET_KEY} -lt 32 ]]; then
    echo "❌ Error: JWT_SECRET_KEY is using default value or is too short (< 32 chars)"
    exit 1
fi

if [[ "$POSTGRES_PASSWORD" == "password" ]] && [[ "$ENVIRONMENT" == "production" ]]; then
    echo "❌ Error: Using default database password in production!"
    exit 1
fi

if [[ "$ENVIRONMENT" == "production" ]]; then
    if [[ "$DEBUG" == "true" ]]; then
        echo "⚠️  Warning: DEBUG mode enabled in production"
    fi
    
    if [[ "$CORS_ALLOW_ORIGINS" == "*" ]]; then
        echo "⚠️  Warning: CORS allows all origins in production"
    fi
    
    if [[ "$SESSION_SECURE" != "true" ]]; then
        echo "❌ Error: SESSION_SECURE should be true in production"
        exit 1
    fi
fi

# Database connectivity test
echo "Testing database connectivity..."
if command -v psql &> /dev/null; then
    if psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
        echo "✅ Database connection successful"
    else
        echo "❌ Error: Cannot connect to database"
        exit 1
    fi
else
    echo "⚠️  Warning: psql not found, skipping database connectivity test"
fi

# Redis connectivity test
echo "Testing Redis connectivity..."
if command -v redis-cli &> /dev/null; then
    if redis-cli -u "$REDIS_URL" ping | grep -q "PONG"; then
        echo "✅ Redis connection successful"
    else
        echo "❌ Error: Cannot connect to Redis"
        exit 1
    fi
else
    echo "⚠️  Warning: redis-cli not found, skipping Redis connectivity test"
fi

echo "✅ Configuration validation completed successfully!"
```

---

## Best Practices and Examples

### 12.1 API Design Patterns

**Pagination Best Practices:**
```javascript
// Cursor-based pagination for large datasets
async function getAllFiles(projectId) {
    const allFiles = [];
    let cursor = null;
    
    do {
        const response = await client.files.list({
            project_id: projectId,
            limit: 100,
            cursor: cursor
        });
        
        allFiles.push(...response.files);
        cursor = response.pagination.next_cursor;
        
    } while (response.pagination.has_more);
    
    return allFiles;
}

// Offset-based pagination for smaller datasets
async function getFilesPaginated(projectId, page = 1, perPage = 20) {
    const response = await client.files.list({
        project_id: projectId,
        limit: perPage,
        offset: (page - 1) * perPage,
        include_total: true
    });
    
    return {
        files: response.files,
        pagination: {
            current_page: page,
            per_page: perPage,
            total: response.pagination.total,
            total_pages: Math.ceil(response.pagination.total / perPage),
            has_more: response.pagination.has_more
        }
    };
}
```

**Batch Operations:**
```typescript
// Efficient batch file uploads
async function batchUploadFiles(files: File[], projectId: string) {
    const BATCH_SIZE = 5;
    const results = [];
    
    for (let i = 0; i < files.length; i += BATCH_SIZE) {
        const batch = files.slice(i, i + BATCH_SIZE);
        
        // Process batch concurrently
        const batchPromises = batch.map(async (file) => {
            try {
                const result = await client.files.upload({
                    file: file,
                    project_id: projectId,
                    metadata: {
                        batch_id: `batch_${Date.now()}`,
                        batch_index: i + batch.indexOf(file)
                    }
                });
                
                return { success: true, file: result };
            } catch (error) {
                return { success: false, error: error.message, filename: file.name };
            }
        });
        
        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults);
        
        // Rate limiting between batches
        if (i + BATCH_SIZE < files.length) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
    
    return results;
}

// Bulk metadata updates
async function bulkUpdateMetadata(fileIds: string[], metadata: any) {
    const CHUNK_SIZE = 50;
    const results = [];
    
    for (let i = 0; i < fileIds.length; i += CHUNK_SIZE) {
        const chunk = fileIds.slice(i, i + CHUNK_SIZE);
        
        try {
            const result = await client.files.bulkUpdate({
                file_ids: chunk,
                metadata: metadata
            });
            
            results.push(result);
        } catch (error) {
            console.error(`Bulk update failed for chunk ${i / CHUNK_SIZE + 1}:`, error);
            results.push({ error: error.message, file_ids: chunk });
        }
    }
    
    return results;
}
```

### 12.2 Performance Optimization

**Caching Strategies:**
```python
import asyncio
import time
from typing import Dict, Any, Optional
from functools import wraps

class APICache:
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry['expires_at']:
                return entry['data']
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, data: Any, ttl: int = None) -> None:
        if ttl is None:
            ttl = self.default_ttl
        
        self._cache[key] = {
            'data': data,
            'expires_at': time.time() + ttl
        }
    
    def clear(self) -> None:
        self._cache.clear()

# Cache decorator for API responses
cache = APICache(default_ttl=300)

def cached_api_call(ttl: int = 300, key_func=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call API and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

# Usage example
@cached_api_call(ttl=600, key_func=lambda project_id: f"project_files:{project_id}")
async def get_project_files(project_id: str):
    response = await client.files.list(project_id=project_id, limit=100)
    return response.files

@cached_api_call(ttl=3600, key_func=lambda user_id: f"user_projects:{user_id}")
async def get_user_projects(user_id: str):
    response = await client.projects.list(limit=50)
    return response.projects
```

**Connection Pooling and Reuse:**
```typescript
import { ActiveLogClient } from '@activelog/sdk';
import pLimit from 'p-limit';

class OptimizedActiveLogClient {
    private client: ActiveLogClient;
    private concurrencyLimit = pLimit(10); // Limit concurrent requests
    
    constructor(config: any) {
        this.client = new ActiveLogClient({
            ...config,
            // Connection pooling settings
            httpAgent: {
                keepAlive: true,
                maxSockets: 50,
                maxFreeSockets: 10,
                timeout: 60000,
                keepAliveMsecs: 1000
            },
            // Retry configuration
            retryConfig: {
                retries: 3,
                retryDelay: (retryNumber: number) => Math.pow(2, retryNumber) * 1000,
                retryCondition: (error: any) => {
                    return !error.response || error.response.status >= 500;
                }
            }
        });
    }
    
    // Throttled file upload with progress tracking
    async uploadWithThrottling<T>(
        uploadFunction: () => Promise<T>,
        onProgress?: (progress: number) => void
    ): Promise<T> {
        return this.concurrencyLimit(async () => {
            const startTime = Date.now();
            
            try {
                const result = await uploadFunction();
                const duration = Date.now() - startTime;
                
                // Log performance metrics
                console.log(`Upload completed in ${duration}ms`);
                
                if (onProgress) {
                    onProgress(100);
                }
                
                return result;
            } catch (error) {
                const duration = Date.now() - startTime;
                console.error(`Upload failed after ${duration}ms:`, error);
                throw error;
            }
        });
    }
    
    // Batch search with deduplication
    async batchSearch(queries: string[], options: any = {}) {
        // Deduplicate queries
        const uniqueQueries = [...new Set(queries)];
        
        // Process in parallel with concurrency limit
        const searchPromises = uniqueQueries.map(query =>
            this.concurrencyLimit(() =>
                this.client.search.query({
                    q: query,
                    ...options
                })
            )
        );
        
        const results = await Promise.all(searchPromises);
        
        // Rebuild results for original query order
        const resultMap = new Map();
        uniqueQueries.forEach((query, index) => {
            resultMap.set(query, results[index]);
        });
        
        return queries.map(query => resultMap.get(query));
    }
    
    // Smart file synchronization
    async syncFiles(localFiles: any[], remoteFiles: any[]) {
        const localFileMap = new Map(localFiles.map(f => [f.checksum, f]));
        const remoteFileMap = new Map(remoteFiles.map(f => [f.checksum, f]));
        
        const toUpload = localFiles.filter(f => !remoteFileMap.has(f.checksum));
        const toDownload = remoteFiles.filter(f => !localFileMap.has(f.checksum));
        const toDelete = localFiles.filter(f => f.deleted && remoteFileMap.has(f.checksum));
        
        // Process operations in optimal order
        const deletePromises = toDelete.map(f =>
            this.concurrencyLimit(() => this.client.files.delete(f.id))
        );
        
        const uploadPromises = toUpload.map(f =>
            this.uploadWithThrottling(() => this.client.files.upload(f))
        );
        
        const downloadPromises = toDownload.map(f =>
            this.concurrencyLimit(() => this.client.files.download(f.id))
        );
        
        // Execute operations
        await Promise.all(deletePromises);
        await Promise.all(uploadPromises);
        await Promise.all(downloadPromises);
        
        return {
            uploaded: toUpload.length,
            downloaded: toDownload.length,
            deleted: toDelete.length
        };
    }
}
```

### 12.3 Security Best Practices

**Secure API Token Management:**
```typescript
interface TokenConfig {
    apiToken: string;
    refreshToken?: string;
    expiresAt?: Date;
    scopes?: string[];
}

class SecureTokenManager {
    private tokenConfig: TokenConfig | null = null;
    private refreshInProgress: Promise<void> | null = null;
    
    constructor(private storage: SecureStorage) {}
    
    async getValidToken(): Promise<string> {
        // Load token from secure storage
        if (!this.tokenConfig) {
            this.tokenConfig = await this.storage.getToken();
        }
        
        // Check if token is expired or expires soon (5 minutes buffer)
        if (this.tokenConfig && this.tokenConfig.expiresAt) {
            const expirationTime = this.tokenConfig.expiresAt.getTime();
            const currentTime = Date.now();
            const bufferTime = 5 * 60 * 1000; // 5 minutes
            
            if (currentTime >= (expirationTime - bufferTime)) {
                await this.refreshToken();
            }
        }
        
        return this.tokenConfig?.apiToken || '';
    }
    
    async refreshToken(): Promise<void> {
        // Prevent multiple simultaneous refresh attempts
        if (this.refreshInProgress) {
            await this.refreshInProgress;
            return;
        }
        
        this.refreshInProgress = this.performTokenRefresh();
        await this.refreshInProgress;
        this.refreshInProgress = null;
    }
    
    private async performTokenRefresh(): Promise<void> {
        try {
            if (!this.tokenConfig?.refreshToken) {
                throw new Error('No refresh token available');
            }
            
            const response = await fetch('/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    refresh_token: this.tokenConfig.refreshToken
                })
            });
            
            if (!response.ok) {
                throw new Error('Token refresh failed');
            }
            
            const tokenData = await response.json();
            
            this.tokenConfig = {
                apiToken: tokenData.access_token,
                refreshToken: tokenData.refresh_token || this.tokenConfig.refreshToken,
                expiresAt: new Date(Date.now() + (tokenData.expires_in * 1000)),
                scopes: tokenData.scopes
            };
            
            // Save to secure storage
            await this.storage.saveToken(this.tokenConfig);
            
        } catch (error) {
            console.error('Token refresh failed:', error);
            // Clear invalid token
            this.tokenConfig = null;
            await this.storage.clearToken();
            throw error;
        }
    }
    
    async revokeToken(): Promise<void> {
        if (this.tokenConfig?.apiToken) {
            try {
                await fetch('/auth/revoke', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.tokenConfig.apiToken}`,
                        'Content-Type': 'application/json'
                    }
                });
            } catch (error) {
                console.warn('Token revocation failed:', error);
            }
        }
        
        this.tokenConfig = null;
        await this.storage.clearToken();
    }
}

interface SecureStorage {
    getToken(): Promise<TokenConfig | null>;
    saveToken(token: TokenConfig): Promise<void>;
    clearToken(): Promise<void>;
}

class BrowserSecureStorage implements SecureStorage {
    private readonly key = 'activelog_token';
    
    async getToken(): Promise<TokenConfig | null> {
        try {
            const encrypted = localStorage.getItem(this.key);
            if (!encrypted) return null;
            
            const decrypted = await this.decrypt(encrypted);
            return JSON.parse(decrypted);
        } catch (error) {
            console.error('Failed to get token from storage:', error);
            return null;
        }
    }
    
    async saveToken(token: TokenConfig): Promise<void> {
        try {
            const serialized = JSON.stringify(token);
            const encrypted = await this.encrypt(serialized);
            localStorage.setItem(this.key, encrypted);
        } catch (error) {
            console.error('Failed to save token to storage:', error);
            throw error;
        }
    }
    
    async clearToken(): Promise<void> {
        localStorage.removeItem(this.key);
    }
    
    private async encrypt(data: string): Promise<string> {
        // Implement encryption using Web Crypto API
        const encoder = new TextEncoder();
        const key = await window.crypto.subtle.importKey(
            'raw',
            encoder.encode('your-encryption-key-32-chars!!!'),
            'AES-GCM',
            false,
            ['encrypt']
        );
        
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const encrypted = await window.crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            encoder.encode(data)
        );
        
        const combined = new Uint8Array(iv.length + encrypted.byteLength);
        combined.set(iv);
        combined.set(new Uint8Array(encrypted), iv.length);
        
        return btoa(String.fromCharCode(...combined));
    }
    
    private async decrypt(encryptedData: string): Promise<string> {
        // Implement decryption using Web Crypto API
        const decoder = new TextDecoder();
        const combined = new Uint8Array(atob(encryptedData).split('').map(c => c.charCodeAt(0)));
        
        const iv = combined.slice(0, 12);
        const encrypted = combined.slice(12);
        
        const key = await window.crypto.subtle.importKey(
            'raw',
            new TextEncoder().encode('your-encryption-key-32-chars!!!'),
            'AES-GCM',
            false,
            ['decrypt']
        );
        
        const decrypted = await window.crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            encrypted
        );
        
        return decoder.decode(decrypted);
    }
}
```

### 12.4 Integration Testing

**Comprehensive API Test Suite:**
```python
import pytest
import asyncio
from unittest.mock import Mock, patch
from activelog import ActiveLogClient
import tempfile
import os

class TestActiveLogAPI:
    @pytest.fixture
    async def client(self):
        return ActiveLogClient(
            api_token=os.getenv('ACTIVELOG_TEST_TOKEN', 'test_token'),
            base_url=os.getenv('ACTIVELOG_TEST_URL', 'http://localhost:8000/api/v1')
        )
    
    @pytest.fixture
    async def test_project(self, client):
        # Create test project
        project = await client.projects.create({
            'name': 'Test Project',
            'description': 'Automated test project'
        })
        
        yield project
        
        # Cleanup
        try:
            await client.projects.delete(project.id)
        except:
            pass  # May already be deleted
    
    async def test_authentication_flow(self, client):
        """Test complete authentication flow"""
        # Test token validation
        auth_status = await client.auth.validate()
        assert auth_status['valid'] is True
        
        # Test user info retrieval
        user = await client.auth.me()
        assert user['id'] is not None
        assert '@' in user['email']
    
    async def test_file_upload_and_management(self, client, test_project):
        """Test complete file lifecycle"""
        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('Test file content for API testing')
            test_file_path = f.name
        
        try:
            # Upload file
            uploaded_file = await client.files.upload({
                'file': open(test_file_path, 'rb'),
                'project_id': test_project.id,
                'metadata': {
                    'tags': ['test', 'automated'],
                    'category': 'testing'
                }
            })
            
            assert uploaded_file['id'] is not None
            assert uploaded_file['name'].endswith('.txt')
            assert uploaded_file['project_id'] == test_project.id
            
            # Get file details
            file_details = await client.files.get(uploaded_file['id'])
            assert file_details['id'] == uploaded_file['id']
            assert 'test' in file_details['metadata']['tags']
            
            # Update file metadata
            updated_file = await client.files.update(uploaded_file['id'], {
                'metadata': {
                    'tags': ['test', 'automated', 'updated'],
                    'status': 'processed'
                }
            })
            assert 'updated' in updated_file['metadata']['tags']
            
            # Search for file
            search_results = await client.search.query({
                'q': 'test automated',
                'project_id': test_project.id
            })
            assert len(search_results['results']) > 0
            
            file_found = any(
                result['id'] == uploaded_file['id'] 
                for result in search_results['results']
            )
            assert file_found
            
            # Delete file
            await client.files.delete(uploaded_file['id'])
            
            # Verify deletion
            with pytest.raises(Exception):  # Should raise 404
                await client.files.get(uploaded_file['id'])
                
        finally:
            os.unlink(test_file_path)
    
    async def test_bulk_operations(self, client, test_project):
        """Test bulk file operations"""
        # Create multiple test files
        test_files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as f:
                f.write(f'Test file content {i}')
                test_files.append(f.name)
        
        try:
            # Bulk upload
            uploaded_files = []
            for file_path in test_files:
                uploaded_file = await client.files.upload({
                    'file': open(file_path, 'rb'),
                    'project_id': test_project.id,
                    'metadata': {'tags': ['bulk_test']}
                })
                uploaded_files.append(uploaded_file)
            
            file_ids = [f['id'] for f in uploaded_files]
            
            # Bulk metadata update
            bulk_result = await client.files.bulk_update({
                'file_ids': file_ids,
                'metadata': {
                    'tags': ['bulk_test', 'processed'],
                    'status': 'completed'
                }
            })
            
            assert bulk_result['successful'] == len(file_ids)
            assert bulk_result['failed'] == 0
            
            # Verify updates
            for file_id in file_ids:
                file_details = await client.files.get(file_id)
                assert 'processed' in file_details['metadata']['tags']
                assert file_details['metadata']['status'] == 'completed'
            
            # Bulk delete
            await client.files.bulk_delete({'file_ids': file_ids})
            
        finally:
            for file_path in test_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    async def test_error_handling(self, client):
        """Test API error handling"""
        # Test 404 error
        with pytest.raises(Exception) as exc_info:
            await client.files.get('nonexistent_file_id')
        assert '404' in str(exc_info.value) or 'not found' in str(exc_info.value).lower()
        
        # Test validation error
        with pytest.raises(Exception) as exc_info:
            await client.projects.create({
                'name': '',  # Invalid empty name
                'description': 'Test project'
            })
        assert 'validation' in str(exc_info.value).lower() or '400' in str(exc_info.value)
        
        # Test unauthorized access
        unauthorized_client = ActiveLogClient(
            api_token='invalid_token',
            base_url=client.base_url
        )
        
        with pytest.raises(Exception) as exc_info:
            await unauthorized_client.auth.me()
        assert '401' in str(exc_info.value) or 'unauthorized' in str(exc_info.value).lower()
    
    async def test_rate_limiting_behavior(self, client):
        """Test rate limiting handling"""
        # Make rapid requests to trigger rate limiting
        tasks = []
        for i in range(20):
            tasks.append(client.auth.validate())
        
        # Some requests should succeed, rate limiting should be handled gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count > 0  # At least some requests should succeed
        
        # Rate limit errors should be handled properly
        rate_limit_errors = [
            r for r in results 
            if isinstance(r, Exception) and '429' in str(r)
        ]
        # Rate limiting behavior depends on current API load
    
    async def test_webhook_functionality(self, client):
        """Test webhook creation and management"""
        webhook = await client.webhooks.create({
            'url': 'https://httpbin.org/post',
            'events': ['file.uploaded', 'project.created'],
            'description': 'Test webhook'
        })
        
        assert webhook['id'] is not None
        assert webhook['url'] == 'https://httpbin.org/post'
        assert 'file.uploaded' in webhook['events']
        
        # Test webhook
        test_result = await client.webhooks.test(webhook['id'])
        assert test_result['status'] == 'sent' or test_result['status'] == 'delivered'
        
        # List webhooks
        webhooks = await client.webhooks.list()
        webhook_found = any(w['id'] == webhook['id'] for w in webhooks['webhooks'])
        assert webhook_found
        
        # Delete webhook
        await client.webhooks.delete(webhook['id'])
        
        # Verify deletion
        webhooks_after = await client.webhooks.list()
        webhook_still_exists = any(w['id'] == webhook['id'] for w in webhooks_after['webhooks'])
        assert not webhook_still_exists
    
    @pytest.mark.performance
    async def test_performance_benchmarks(self, client, test_project):
        """Test API performance benchmarks"""
        import time
        
        # File upload performance
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('x' * 10000)  # 10KB file
            test_file_path = f.name
        
        try:
            start_time = time.time()
            uploaded_file = await client.files.upload({
                'file': open(test_file_path, 'rb'),
                'project_id': test_project.id
            })
            upload_time = time.time() - start_time
            
            # Upload should complete within reasonable time
            assert upload_time < 10.0, f"Upload took too long: {upload_time}s"
            
            # Search performance
            start_time = time.time()
            search_results = await client.search.query({
                'q': 'test',
                'limit': 50
            })
            search_time = time.time() - start_time
            
            # Search should be fast
            assert search_time < 5.0, f"Search took too long: {search_time}s"
            
            # Cleanup
            await client.files.delete(uploaded_file['id'])
            
        finally:
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
    
    async def test_integration_with_third_party_services(self, client):
        """Test integration capabilities"""
        # List available integrations
        integrations = await client.integrations.list()
        assert isinstance(integrations['integrations'], list)
        
        # Test integration status (without actually enabling)
        if integrations['integrations']:
            first_integration = integrations['integrations'][0]
            status = await client.integrations.get_status(first_integration['id'])
            assert 'status' in status
            assert 'enabled' in status or 'disabled' in status['status']

if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])
```

---

## Conclusion

This API Integration Reference provides comprehensive documentation for ActiveLog's API ecosystem, covering everything from basic authentication to advanced integration patterns. The platform's RESTful API design, extensive SDK support, and robust webhook system enable developers to build powerful integrations and applications.

**Key API Capabilities:**
- ✅ **Complete CRUD Operations** - Full file and project management capabilities
- ✅ **Advanced Search and Analytics** - Powerful search with AI-powered semantic understanding  
- ✅ **Real-time Collaboration** - WebSocket-based live collaboration features
- ✅ **Comprehensive Authentication** - JWT, OAuth 2.0, and API key support
- ✅ **Robust Error Handling** - Detailed error responses and retry mechanisms
- ✅ **Extensive Integration Support** - SDKs, webhooks, and third-party service connections
- ✅ **Performance Optimization** - Rate limiting, caching, and batch operations
- ✅ **Security Best Practices** - Token management, encryption, and secure storage

**Next Steps for Developers:**
1. **Get Started** - Obtain API credentials and explore the interactive API documentation
2. **Choose Your SDK** - Use official SDKs for JavaScript, Python, or PHP
3. **Build Integrations** - Connect ActiveLog with your existing systems and workflows  
4. **Implement Webhooks** - Set up real-time notifications and event-driven automation
5. **Optimize Performance** - Use batch operations, caching, and connection pooling
6. **Join the Community** - Connect with other developers and share integration experiences

**Support and Resources:**
- **API Documentation:** https://api.activelog.com/docs
- **SDK Repositories:** https://github.com/activelog/sdks
- **Developer Support:** api-support@activelog.com  
- **Community Forum:** https://community.activelog.com/developers

---

*This API Integration Reference represents the complete guide to ActiveLog's API ecosystem. For the most current API changes and updates, please refer to our online documentation and changelog.*

**Document Classification:** Public  
**Last Updated:** [DATE]  
**Next Review:** [DATE + 6 months]