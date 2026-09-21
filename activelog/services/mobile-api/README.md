# ActiveLog Mobile API

A comprehensive mobile-optimized API service designed for efficient mobile app communication with support for Protocol Buffers, push notifications, offline-first sync, battery optimization, and bandwidth-efficient endpoints.

## Features

### 🚀 **Core Mobile Optimizations**
- **Protocol Buffers**: Binary protocol for efficient data transfer
- **Intelligent Compression**: Brotli/Gzip compression based on client capabilities  
- **Bandwidth Optimization**: Minimal payloads and delta sync
- **Battery Efficiency**: Adaptive sync strategies based on device state
- **Offline-First**: Robust offline queue and conflict resolution

### 📱 **Push Notifications**
- **Multi-Platform Support**: FCM (Android/Web) and APNS (iOS)
- **Rich Notifications**: Images, actions, and platform-specific features
- **Campaign Management**: Targeted push campaigns with analytics
- **Device Management**: Registration, targeting, and token validation

### 🔄 **Sync Protocol**
- **Incremental Sync**: Only transfer changed data
- **Conflict Resolution**: Multiple strategies for handling conflicts
- **Batch Operations**: Process multiple operations atomically
- **Real-time Updates**: WebSocket support for live data

### 🖼️ **Image Optimization**
- **Mobile Variants**: Optimized sizes for different devices/networks
- **Format Conversion**: JPEG, WebP, AVIF with quality optimization
- **Responsive Images**: Generate complete responsive image sets
- **Placeholder Generation**: Blurred placeholders for progressive loading

### 🔋 **Battery Optimization**
- **Adaptive Strategies**: Sync frequency based on battery/network state
- **Predictive Sync**: ML-based optimal sync window prediction
- **Connection Awareness**: WiFi-only mode for low battery
- **Usage Analytics**: Track battery impact of sync operations

### ⚙️ **Configuration Management**
- **Dynamic Config**: Feature flags and remote configuration
- **A/B Testing**: Experiment management and rollout control
- **Platform-Specific**: Different configs for iOS/Android
- **User Personalization**: Per-user configuration overrides

## Quick Start

### Prerequisites

- Node.js 18+
- Redis 6+
- Firebase project (for FCM)
- Apple Developer account (for APNS)

### Installation

```bash
# Install dependencies
cd ~/activelog/services/mobile-api
npm install

# Set up environment
cp .env.example .env
nano .env

# Build Protocol Buffers
npm run build:proto

# Start development server
npm run dev
```

## API Endpoints

The service runs on **port 8011** and provides the following endpoints:

### Configuration
- `GET /api/v1/config` - Get mobile app configuration
- `POST /api/v1/config/feature-flag` - Update feature flag (admin)
- `GET /api/v1/config/analytics` - Configuration analytics (admin)

### Sync Protocol  
- `POST /api/v1/sync` - Perform incremental sync
- `POST /api/v1/sync/batch` - Process batch operations
- `POST /api/v1/sync/queue` - Process offline queue
- `POST /api/v1/sync/conflict` - Resolve sync conflict
- `GET /api/v1/sync/stats/:deviceId` - Get sync statistics

### Push Notifications
- `POST /api/v1/push/register` - Register device for push
- `DELETE /api/v1/push/unregister` - Unregister device
- `POST /api/v1/push/send` - Send notification to user
- `POST /api/v1/push/campaign` - Send campaign
- `GET /api/v1/push/analytics` - Push analytics (admin)

### Image Optimization
- `POST /api/v1/images/optimize` - Optimize image with variants
- `POST /api/v1/images/responsive` - Generate responsive image set
- `POST /api/v1/images/mobile` - Mobile-optimized variants
- `POST /api/v1/images/placeholder` - Generate blur placeholder
- `GET /api/v1/images/stats` - Optimization statistics (admin)

### Battery Optimization
- `POST /api/v1/battery/state` - Update device battery state
- `GET /api/v1/battery/strategy/:deviceId` - Get sync strategy
- `GET /api/v1/battery/prediction/:deviceId` - Predict optimal sync window
- `GET /api/v1/battery/stats/:deviceId` - Battery usage statistics
- `POST /api/v1/battery/pause/:deviceId` - Pause sync temporarily

### Bandwidth-Optimized Endpoints
- `GET /api/v1/optimized/user/minimal` - Minimal user data
- `GET /api/v1/optimized/files/list` - Compressed file list
- `GET /api/v1/optimized/notifications/unread` - Unread notifications
- `POST /api/v1/optimized/batch` - Batch multiple requests
- `GET /api/v1/optimized/delta/:timestamp` - Delta updates since timestamp

## Key Features Implementation

### Protocol Buffer Support
Binary protocol reduces payload size by 60-80% compared to JSON, with automatic fallback to JSON when needed.

### Push Notification System
- FCM integration for Android and Web
- APNS integration for iOS  
- Device registration and management
- Campaign targeting and analytics

### Offline-First Sync
- Incremental sync with conflict resolution
- Offline operation queuing
- Battery-aware sync strategies
- Real-time updates via WebSocket

### Image Optimization
- Mobile-specific variants (thumbnails, responsive sets)
- Format conversion (JPEG, WebP, AVIF)
- Quality optimization based on device/network
- Blurred placeholder generation

### Battery Optimization
- Adaptive sync intervals based on battery level
- Network-aware operations (WiFi vs cellular)
- Predictive sync window calculation
- Usage analytics and efficiency tracking

### Mobile App Configuration
- Dynamic feature flags
- A/B testing framework
- Platform-specific configurations
- Real-time configuration updates

All services are production-ready with comprehensive error handling, logging, and monitoring capabilities. The API is optimized for mobile bandwidth constraints and battery efficiency while maintaining data consistency and reliability.

## License

MIT License