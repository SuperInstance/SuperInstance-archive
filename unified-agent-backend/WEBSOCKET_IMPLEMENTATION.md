# WebSocket Implementation for Unified Agent Backend

This document provides a comprehensive overview of the WebSocket implementation for real-time updates in the unified-agent-backend project.

## Overview

The WebSocket implementation provides real-time communication capabilities for the unified agent backend, enabling live updates for workflow executions, agent monitoring, and system notifications.

## Features

### Core Functionality
- **Connection Management**: Handles multiple concurrent WebSocket connections with lifecycle management
- **Room-Based Subscriptions**: Clients can subscribe to specific topics (executions, agents, workflows)
- **Message Broadcasting**: Targeted messaging to rooms, users, or specific connections
- **Authentication & Authorization**: Secure WebSocket connections with JWT/API key authentication
- **Error Handling**: Comprehensive error handling and automatic cleanup of stale connections

### Real-Time Updates
- **Workflow Execution Updates**: Live progress, node status, and completion notifications
- **Agent Monitoring**: Health status, task assignments, and performance metrics
- **System Notifications**: User notifications and system announcements
- **Custom Events**: Extensible event system for custom real-time features

## Architecture

### Components

#### 1. WebSocket Manager (`/src/app/websocket/manager.py`)
- **Purpose**: Main coordinator for all WebSocket functionality
- **Features**: Connection handling, message processing, integration with other components
- **Usage**: Singleton instance used throughout the application

#### 2. Connection Manager (`/src/app/websocket/connection_manager.py`)
- **Purpose**: Manages individual WebSocket connections
- **Features**: Connection lifecycle, ping/pong, cleanup of dead connections
- **Monitoring**: Tracks connection statistics and health

#### 3. Room Manager (`/src/app/websocket/room_manager.py`)
- **Purpose**: Manages room-based subscriptions
- **Features**: Room creation, subscription management, message broadcasting
- **Optimization**: Automatic cleanup of empty rooms

#### 4. Authentication (`/src/app/websocket/auth.py`)
- **Purpose**: Handles WebSocket authentication and authorization
- **Features**: JWT validation, API key authentication, permission checking
- **Security**: Room-level authorization for resource access

#### 5. Integrations (`/src/app/websocket/integrations.py`)
- **Purpose**: Integration utilities for different services
- **Components**: Workflow executor, agent service, notification service integrations
- **Usage**: Easy integration with existing backend services

### API Endpoints

#### General WebSocket Endpoint
```
WS /api/v1/websocket/ws
```
- General-purpose WebSocket connection
- Support for custom room subscriptions
- Authentication via query parameters or headers

#### Execution-Specific Endpoint
```
WS /api/v1/websocket/ws/executions/{execution_id}
```
- Auto-subscription to execution updates
- Real-time execution progress and status
- Requires execution access permissions

#### Agent Monitoring Endpoint
```
WS /api/v1/websocket/ws/agents/{agent_id}
```
- Auto-subscription to agent updates
- Health monitoring and task notifications
- Requires agent access permissions

#### Workflow Updates Endpoint
```
WS /api/v1/websocket/ws/workflows/{workflow_id}
```
- Auto-subscription to workflow changes
- Real-time workflow validation and deployment updates
- Requires workflow access permissions

#### HTTP API Endpoints
```
GET  /api/v1/websocket/stats
POST /api/v1/websocket/broadcast/{room_id}
POST /api/v1/websocket/notify/user/{user_id}
```

## Message Schemas

### Message Types
- **Connection Management**: `welcome`, `ping`, `pong`, `error`
- **Subscription Management**: `subscribe`, `unsubscribe`, `subscription_confirmed`
- **Execution Updates**: `execution_started`, `execution_progress`, `execution_completed`, `execution_failed`
- **Node Updates**: `node_started`, `node_completed`, `node_failed`
- **Agent Updates**: `agent_status_changed`, `agent_health_update`, `agent_task_assigned`
- **Workflow Updates**: `workflow_updated`, `workflow_validation_result`
- **Notifications**: `notification`, `system_announcement`

### Message Format
```json
{
  "type": "message_type",
  "timestamp": 1234567890.123,
  "data": {
    // Message-specific data
  },
  "room_id": "optional_room_id",
  "connection_id": "optional_connection_id"
}
```

## Usage Examples

### Client Connection (JavaScript)
```javascript
// General WebSocket connection
const ws = new WebSocket('ws://localhost:8000/api/v1/websocket/ws?token=your_jwt_token');

ws.onopen = () => {
  console.log('Connected to WebSocket');

  // Subscribe to execution updates
  ws.send(JSON.stringify({
    type: 'subscribe',
    data: {
      room_id: 'execution:execution-123',
      room_type: 'execution',
      resource_id: 'execution-123'
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);

  switch (message.type) {
    case 'execution_progress':
      updateProgressBar(message.data.progress_percentage);
      break;
    case 'execution_completed':
      showCompletionMessage(message.data);
      break;
  }
};
```

### Server-Side Integration
```python
from app.websocket.integrations import WorkflowExecutorWebSocketIntegration

# Create integration instance
ws_integration = WorkflowExecutorWebSocketIntegration()

# Notify about execution start
await ws_integration.notify_execution_started(
    execution_id="exec-123",
    workflow_id="workflow-456",
    user_id="user-789",
    input_data={"param": "value"}
)

# Notify about progress
await ws_integration.notify_execution_progress(
    execution_id="exec-123",
    workflow_id="workflow-456",
    progress_percentage=45.0,
    current_node_id="node-1",
    completed_nodes=2,
    total_nodes=5
)
```

### Broadcasting Messages
```python
from app.websocket.manager import websocket_manager

# Broadcast to room
await websocket_manager.broadcast_to_room(
    "execution:exec-123",
    {"type": "custom_update", "data": {"message": "Hello!"}}
)

# Send notification to user
await websocket_manager.send_message_to_user(
    "user-123",
    {"type": "notification", "title": "Alert", "message": "Something happened"}
)
```

## Room Types

### Execution Rooms
- **Format**: `execution:{execution_id}`
- **Purpose**: Real-time execution updates
- **Messages**: Progress, node status, completion, errors
- **Authorization**: Execution access permissions

### Agent Rooms
- **Format**: `agent:{agent_id}`
- **Purpose**: Agent monitoring and task updates
- **Messages**: Status changes, health updates, task assignments
- **Authorization**: Agent monitoring permissions

### Workflow Rooms
- **Format**: `workflow:{workflow_id}`
- **Purpose**: Workflow change notifications
- **Messages**: Updates, validation results, deployments
- **Authorization**: Workflow access permissions

### User Rooms
- **Format**: `user:{user_id}`
- **Purpose**: User-specific notifications
- **Messages**: Personal notifications, system announcements
- **Authorization**: User identity verification

### Global Rooms
- **Format**: `global`
- **Purpose**: System-wide announcements
- **Messages**: Maintenance notices, system updates
- **Authorization**: Authenticated users only

## Security Features

### Authentication
- **JWT Tokens**: Bearer token authentication
- **API Keys**: Alternative authentication method
- **Development Mode**: Simplified authentication for development

### Authorization
- **Room-Level Security**: Permission checking for room subscriptions
- **Resource Access**: Validation of access to executions, agents, workflows
- **User Isolation**: Users can only access their own resources unless admin

### Connection Security
- **Rate Limiting**: Prevention of connection flooding
- **Connection Validation**: Validation of connection parameters
- **Automatic Cleanup**: Removal of stale or malicious connections

## Performance Considerations

### Scalability
- **Connection Pooling**: Efficient management of multiple connections
- **Message Queuing**: Non-blocking message delivery
- **Memory Management**: Cleanup of old connections and empty rooms

### Optimization
- **Room Broadcasting**: Efficient multi-cast messaging
- **Connection Filtering**: Targeted message delivery
- **Background Tasks**: Async cleanup and maintenance

### Monitoring
- **Connection Statistics**: Real-time connection metrics
- **Room Analytics**: Subscription and message statistics
- **Performance Metrics**: Latency and throughput monitoring

## Configuration

### Environment Variables
```bash
# WebSocket settings
WEBSOCKET_REQUIRE_AUTH=true
WEBSOCKET_PING_INTERVAL=30
WEBSOCKET_MAX_CONNECTION_AGE=3600
WEBSOCKET_ROOM_CLEANUP_INTERVAL=300
```

### Application Settings
```python
# In settings.py
WEBSOCKET_SETTINGS = {
    "require_auth": True,
    "ping_interval": 30,
    "max_connection_age": 3600,
    "cleanup_interval": 300
}
```

## Testing

### Unit Tests
```bash
# Run WebSocket tests
pytest tests/websocket/

# Run specific test files
pytest tests/websocket/test_connection_manager.py
pytest tests/websocket/test_room_manager.py
pytest tests/websocket/test_websocket_endpoints.py
pytest tests/websocket/test_integration.py
```

### Demo Application
```bash
# Run the WebSocket demo
python examples/websocket_demo.py
```

The demo showcases:
- Basic connection handling
- Room subscriptions
- Message broadcasting
- Workflow execution integration
- Agent monitoring

## Integration Guide

### Adding WebSocket Notifications to Your Service

1. **Import Integration Classes**
```python
from app.websocket.integrations import YourServiceWebSocketIntegration
```

2. **Create Integration Instance**
```python
ws_integration = YourServiceWebSocketIntegration()
```

3. **Add Notifications to Your Events**
```python
# On service event
await ws_integration.notify_your_event(
    resource_id="id",
    event_data=data,
    user_id=user_id
)
```

4. **Define Message Schemas**
```python
# In app/schemas/websocket.py
class YourEventMessage(BaseModel):
    type: str = Field(default=MessageType.YOUR_EVENT)
    # Define your message fields
```

### Custom Room Types

1. **Define Room Type**
```python
class RoomType(str, Enum):
    YOUR_TYPE = "your_type"
```

2. **Add Authorization**
```python
async def _authorize_your_subscription(self, user_id, resource_id):
    # Implement your authorization logic
    return True
```

3. **Create Integration Methods**
```python
async def notify_your_event(self, resource_id, event_data):
    message = YourEventMessage(**event_data)
    room_id = f"your_type:{resource_id}"
    await self.ws_manager.broadcast_to_room(room_id, message.dict())
```

## Troubleshooting

### Common Issues

1. **Connection Fails**
   - Check authentication tokens
   - Verify WebSocket endpoint URLs
   - Check CORS settings

2. **Messages Not Received**
   - Verify room subscriptions
   - Check message format
   - Review authorization permissions

3. **Performance Issues**
   - Monitor connection counts
   - Check message frequency
   - Review room cleanup settings

### Debug Logging
```python
# Enable debug logging for WebSocket
import logging
logging.getLogger('app.websocket').setLevel(logging.DEBUG)
```

### Health Checks
```python
# Get WebSocket manager statistics
stats = websocket_manager.get_stats()
print(f"Active connections: {stats['connection_stats']['total_connections']}")
print(f"Active rooms: {stats['room_stats']['total_rooms']}")
```

## Future Enhancements

### Planned Features
- **Message Persistence**: Store and replay missed messages
- **Connection Clustering**: Scale across multiple instances
- **Advanced Filtering**: Client-side message filtering
- **Metrics Dashboard**: Real-time WebSocket metrics

### Extensions
- **File Transfer**: WebSocket-based file uploads/downloads
- **Streaming**: Real-time data streaming capabilities
- **Collaboration**: Multi-user real-time collaboration features
- **Analytics**: WebSocket usage analytics and reporting

## Support

For questions, issues, or contributions related to the WebSocket implementation:

1. Check the test files for usage examples
2. Run the demo application to see functionality
3. Review the integration guide for adding new features
4. Consult the API documentation for endpoint details

The WebSocket implementation is designed to be extensible, performant, and production-ready for real-time applications.