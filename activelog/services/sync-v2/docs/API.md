# ActiveLog Sync Service v2 API Documentation

## Overview

The ActiveLog Sync Service v2 provides advanced device synchronization with intelligent conflict resolution, bandwidth awareness, and real-time collaboration capabilities.

## Base URL

```
https://sync.activelog.ai/api/v2
```

## Authentication

All API requests require authentication using Bearer tokens:

```http
Authorization: Bearer <your-access-token>
```

## Device Registration

### Register Device

Register a new device for synchronization.

```http
POST /devices/register
```

**Request Body:**
```json
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

### Get Device Status

```http
GET /devices/{device_id}/status
```

**Response:**
```json
{
  "device_id": "phone-001",
  "is_online": true,
  "last_seen": "2024-01-01T12:00:00Z",
  "sync_status": "synced",
  "pending_items": 0,
  "conflicts": 2
}
```

## Synchronization

### Sync Items

Perform synchronization for a device.

```http
POST /sync/items
```

**Request Body:**
```json
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
      "modified_at": "2024-01-01T11:00:00Z"
    }
  ],
  "conflicts": [
    {
      "conflict_id": "conflict-001",
      "item_id": "item-002", 
      "conflict_type": "concurrent_edit",
      "severity": "medium"
    }
  ],
  "next_sync_token": "token_def456",
  "has_more": false,
  "server_timestamp": "2024-01-01T12:00:00Z"
}
```

### Upload Item

Upload a single item.

```http
POST /sync/upload
```

**Request Body:**
```json
{
  "item": {
    "item_id": "new-item-001",
    "content_type": "text",
    "data": {
      "title": "New Note",
      "content": "New note content"
    },
    "priority": 7,
    "tags": ["important"]
  }
}
```

**Response:**
```json
{
  "status": "uploaded",
  "item_id": "new-item-001", 
  "server_version": 1,
  "conflicts": []
}
```

## Conflict Resolution

### Get Conflicts

```http
GET /conflicts?device_id={device_id}
```

**Response:**
```json
{
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
          "timestamp": "2024-01-01T10:30:00Z",
          "data": {"content": "Version from iPhone"}
        },
        {
          "version_id": "v2", 
          "device_name": "MacBook Pro",
          "timestamp": "2024-01-01T10:31:00Z",
          "data": {"content": "Version from MacBook"}
        }
      ],
      "suggested_resolution": "smart_merge",
      "auto_resolvable": false
    }
  ]
}
```

### Resolve Conflict

```http
POST /conflicts/{conflict_id}/resolve
```

**Request Body:**
```json
{
  "strategy": "smart_merge",
  "user_input": {
    "preferred_version": "v2",
    "custom_merge": null
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
  "confidence_score": 0.85
}
```

## Real-time Collaboration

### Start Collaboration Session

```http
POST /collaboration/sessions
```

**Request Body:**
```json
{
  "document_id": "doc-001",
  "user_id": "user123"
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
      "color": "#007AFF"
    }
  ]
}
```

### WebSocket Connection

Connect to WebSocket for real-time collaboration:

```
wss://sync.activelog.ai/ws/v2
```

**Join Session Message:**
```json
{
  "type": "join_session",
  "document_id": "doc-001",
  "user_info": {
    "user_id": "user123",
    "user_name": "Alice",
    "color": "#007AFF"
  }
}
```

**Operation Message:**
```json
{
  "type": "operation_batch",
  "batch": {
    "batch_id": "batch_123",
    "operations": [
      {
        "op_type": "insert",
        "position": 10,
        "content": "Hello",
        "author_id": "user123"
      }
    ],
    "document_id": "doc-001",
    "base_revision": 42
  }
}
```

## Device Capabilities & Optimization

### Get Device Capabilities

```http
GET /devices/{device_id}/capabilities
```

**Response:**
```json
{
  "device_type": "phone",
  "capabilities": "mobile",
  "constraints": {
    "max_file_size": 52428800,
    "max_concurrent_syncs": 3,
    "compress_images": true,
    "defer_videos": true
  },
  "network_profile": {
    "current_type": "wifi",
    "bandwidth_limit": null,
    "is_metered": false
  },
  "sync_preferences": {
    "wifi_only_large_files": true,
    "battery_aware_sync": true,
    "background_sync": true
  }
}
```

### Update Network Status

```http
PUT /devices/{device_id}/network
```

**Request Body:**
```json
{
  "network_type": "cellular",
  "bandwidth_down": 5.2,
  "bandwidth_up": 1.8,
  "latency": 45,
  "is_metered": true,
  "battery_level": 25
}
```

## Monitoring & Statistics

### Get Sync Statistics

```http
GET /stats
```

**Response:**
```json
{
  "items_synced": 15420,
  "conflicts_resolved": 23,
  "bytes_transferred": 104857600,
  "sync_sessions": 1250,
  "active_devices": 156,
  "collaboration_sessions": 8,
  "uptime_seconds": 86400
}
```

### Get Device Statistics

```http
GET /devices/{device_id}/stats
```

**Response:**
```json
{
  "device_id": "phone-001",
  "items_synced": 234,
  "last_sync": "2024-01-01T12:00:00Z",
  "sync_frequency": "every_30_seconds",
  "bandwidth_usage": 2048576,
  "conflicts_encountered": 1,
  "sync_efficiency": 0.95
}
```

## Error Responses

All API endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "invalid_request",
  "message": "Missing required field: device_id",
  "details": {
    "field": "device_id",
    "required": true
  }
}
```

### 401 Unauthorized
```json
{
  "error": "unauthorized",
  "message": "Invalid or expired access token"
}
```

### 429 Too Many Requests
```json
{
  "error": "rate_limit_exceeded", 
  "message": "Too many requests",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "error": "internal_error",
  "message": "An internal server error occurred",
  "request_id": "req_abc123"
}
```

## Rate Limits

- **General API**: 60 requests per minute
- **Sync operations**: 10 requests per minute  
- **WebSocket connections**: 5 connections per device
- **Burst allowance**: 10 requests

## SDK Examples

### JavaScript/TypeScript

```typescript
import { SyncClient } from '@activelog/sync-v2';

const client = new SyncClient({
  apiKey: 'your-api-key',
  endpoint: 'https://sync.activelog.ai/api/v2'
});

// Register device
await client.registerDevice({
  deviceId: 'web-001',
  deviceType: 'web', 
  capabilities: 'standard',
  name: 'Chrome Browser'
});

// Sync items
const response = await client.syncItems({
  deviceId: 'web-001',
  maxItems: 50
});
```

### Python

```python
from activelog_sync import SyncClient

client = SyncClient(
    api_key='your-api-key',
    endpoint='https://sync.activelog.ai/api/v2'
)

# Register device
await client.register_device(
    device_id='desktop-001',
    device_type='desktop',
    capabilities='full',
    name='MacBook Pro'
)

# Sync items
response = await client.sync_items(
    device_id='desktop-001',
    max_items=100
)
```

### Swift (iOS)

```swift
import ActiveLogSync

let client = SyncClient(
    apiKey: "your-api-key",
    endpoint: URL(string: "https://sync.activelog.ai/api/v2")!
)

// Register device
try await client.registerDevice(
    deviceId: "ios-001",
    deviceType: .phone,
    capabilities: .mobile,
    name: "iPhone 15"
)

// Sync items
let response = try await client.syncItems(
    deviceId: "ios-001",
    maxItems: 30
)
```

## WebSocket Events

### Connection Events
- `connection_established` - WebSocket connection successful
- `session_joined` - Joined collaboration session
- `user_joined` - Another user joined session
- `user_left` - User left session

### Collaboration Events  
- `operation_batch` - Operational transform batch
- `cursor_update` - User cursor position change
- `presence_update` - User presence change

### Sync Events
- `item_updated` - Item synchronized
- `conflict_detected` - Sync conflict detected
- `sync_completed` - Sync operation completed

For more examples and detailed integration guides, see the [Integration Documentation](./INTEGRATION.md).