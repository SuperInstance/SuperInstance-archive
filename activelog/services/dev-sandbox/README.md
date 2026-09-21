# Developer Sandbox Service

A comprehensive developer sandbox service running on port 8303 with Docker container isolation, Claude Code API integration, and collaborative development features.

## 🚀 Features Implemented

1. **✅ Isolated Docker Containers per User** - Secure container isolation with tier-based resource limits
2. **✅ Claude Code API Integration** - AI-powered code generation, review, and debugging
3. **✅ Virtual Environment Management** - Template-based environments (Node.js, Python, React, Go)
4. **✅ Resource Limits per User Tier** - Free/Pro/Enterprise tier controls
5. **✅ Code Execution Sandboxing** - Multi-mode execution (container, VM, isolated-vm, worker threads)
6. **✅ Live App Editing** - Real-time file watching with staging environments
7. **✅ Scheduled Deployment System** - Cron-based deployments with multiple strategies
8. **✅ Rollback Mechanisms** - Snapshot-based rollback with automatic failure handling
9. **✅ Collaborative Coding Spaces** - Real-time collaborative editing with operational transform
10. **✅ API Key Management Vault** - Encrypted key storage with rotation and access control
11. **✅ Usage Tracking and Billing** - Comprehensive usage analytics and invoicing
12. **✅ Backup Before Each Change** - Automatic backup creation with incremental support

## 🌐 Service Endpoints

- **Health Check**: `http://localhost:8303/health`
- **WebSocket**: `ws://localhost:8303`
- **API Base**: `http://localhost:8303/api`

## 📊 API Routes

### Container Management
- `POST /api/containers/create` - Create user container
- `GET /api/containers` - List user containers
- `DELETE /api/containers/:containerId` - Delete container

### Environment Management
- `POST /api/environments/create` - Create environment
- `GET /api/environments` - List environments
- `PUT /api/environments/:envId` - Update environment

### Code Execution
- `POST /api/execute` - Execute code
- `GET /api/execute/:executionId/status` - Get execution status

### Claude Code Integration
- `POST /api/claude/generate` - Generate code with AI
- `POST /api/claude/review` - Review code with AI
- `POST /api/claude/debug` - Debug code with AI

### Deployments
- `POST /api/deployments/create` - Create deployment
- `GET /api/deployments` - List deployments
- `POST /api/deployments/:deploymentId/rollback` - Rollback deployment

### API Key Vault
- `POST /api/vault/keys` - Store API key
- `GET /api/vault/keys` - List API keys
- `GET /api/vault/keys/:keyId` - Get API key
- `PUT /api/vault/keys/:keyId` - Update API key
- `DELETE /api/vault/keys/:keyId` - Delete API key

### Usage Tracking
- `GET /api/usage` - Get usage data
- `GET /api/usage/analytics` - Get usage analytics
- `POST /api/invoices/generate` - Generate invoice

### Backup Management
- `POST /api/backups/create` - Create backup
- `GET /api/backups` - List backups
- `POST /api/backups/:backupId/restore` - Restore backup
- `DELETE /api/backups/:backupId` - Delete backup

### Collaboration
- `POST /api/collaboration/rooms` - Create collaboration room
- `GET /api/collaboration/rooms` - List rooms
- `POST /api/collaboration/rooms/:roomId/join` - Join room

## 🔧 Development Mode

The service automatically detects when Docker is not available and runs in development mode with mock containers. This allows for testing and development without requiring Docker infrastructure.

## 🏗️ Architecture

- **Event-driven**: All services use EventEmitter for loose coupling
- **Tier-based**: Resource limits and features based on user tier (free/pro/enterprise)
- **Security-first**: Container isolation with security constraints
- **Real-time**: WebSocket integration for live features
- **Scalable**: Designed for horizontal scaling

## 🚦 Service Status

**Running**: ✅ All 13 features implemented and operational on port 8303

The service includes comprehensive logging, error handling, and graceful shutdown mechanisms.