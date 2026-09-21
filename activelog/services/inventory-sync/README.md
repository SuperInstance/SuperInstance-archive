# Inventory Sync Service

Real-time inventory management system with multi-location support, POS integration, and automated operations.

## 🚀 Features

### 📊 Real-Time Inventory Tracking
- **Live Updates**: WebSocket-based real-time inventory changes
- **Batch Processing**: Efficient handling of high-volume inventory updates
- **Change Analytics**: Track stock movements, reasons, and patterns
- **Low Stock Alerts**: Automatic notifications for critical inventory levels
- **Movement History**: Detailed audit trail of all inventory changes

### 🏢 Multi-Location Support
- **Location Management**: Register and manage multiple warehouses, stores, and pickup points
- **Inventory Sync**: Real-time synchronization across all locations
- **Transfer Management**: Inter-location inventory transfers with tracking
- **Proximity Search**: Find nearby locations based on coordinates
- **Operating Hours**: Location-specific business hours and timezone support
- **Capacity Management**: Track and optimize location storage capacity

### 📋 Reservation System
- **Customer Holds**: Reserve inventory for customers with automatic expiration
- **Flexible Duration**: Configurable reservation timeouts (30 min to 24 hours)
- **Extension Support**: Extend reservations when needed
- **Automatic Cleanup**: Remove expired reservations automatically
- **Confirmation Tracking**: Convert reservations to actual sales

### 📅 Pickup Scheduling
- **Time Slot Management**: Schedule customer pickups with available slots
- **Working Hours Integration**: Respect location operating hours
- **Buffer Time**: Configurable preparation time between pickups
- **Advanced Booking**: Up to 30 days advance scheduling
- **QR Code Integration**: Generate pickup confirmation QR codes

### 🏷️ QR Code Generation
- **Inventory QR Codes**: Unique codes for each location/item combination
- **Pickup QR Codes**: Customer pickup confirmation codes
- **Batch Generation**: Create QR codes for multiple items at once
- **Customizable Design**: Adjust size, colors, and format
- **Base64 Support**: Generate codes as base64 strings for immediate use

### 🔔 Notification System
- **Multi-Channel**: Email (SendGrid) and SMS (Twilio) notifications
- **Low Stock Alerts**: Notify managers when inventory runs low
- **Pickup Reminders**: Customer pickup notifications
- **Transfer Updates**: Inter-location transfer status updates
- **System Alerts**: Critical system status notifications

### 💳 POS Integration
- **Square Integration**: Direct connection to Square POS systems
- **Stripe Support**: Payment processing with inventory sync
- **Real-Time Sync**: Instant inventory updates from POS transactions
- **Transaction Logging**: Detailed POS transaction tracking
- **Multi-POS Support**: Handle multiple POS systems per location

### 🚚 Supply Chain Tracking
- **Supplier Management**: Track suppliers and their performance
- **Order Tracking**: Monitor purchase orders and deliveries
- **Lead Time Analysis**: Optimize ordering based on supplier performance
- **Quality Tracking**: Monitor supplier quality metrics
- **Cost Analysis**: Track supplier costs and trends

### 🔄 Reorder Automation
- **Smart Thresholds**: AI-powered reorder point calculations
- **Automatic Triggers**: Queue items for reorder when stock is low
- **Priority System**: Critical, normal, and low priority reordering
- **Supplier Integration**: Automatic order placement with approved suppliers
- **Seasonal Adjustments**: Account for seasonal demand patterns

### 💰 Price Optimization
- **Dynamic Pricing**: AI-powered price adjustments based on demand
- **Competitor Analysis**: Monitor competitor pricing automatically
- **Demand Forecasting**: Predict future demand for better pricing
- **Margin Optimization**: Maximize profit margins while staying competitive
- **A/B Price Testing**: Test different pricing strategies

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│   POS Systems   │────┤  Inventory Sync      │────┤   Suppliers     │
│ Square, Stripe  │    │     Service          │    │   & Partners    │
└─────────────────┘    └──────────────────────┘    └─────────────────┘
                                  │
                       ┌──────────────────────┐
                       │    Multi-Location    │
                       │     Warehouses       │
                       │     & Stores         │
                       └──────────────────────┘
                                  │
                       ┌──────────────────────┐
                       │   Real-time WebSocket │
                       │   & Notification     │
                       │      Services        │
                       └──────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- MongoDB (optional - graceful fallback)
- Redis (optional - graceful fallback)
- Square/Stripe accounts (for POS integration)

### Installation

```bash
# Navigate to project
cd ~/activelog/services/inventory-sync

# Install dependencies
npm install

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# Start the service
npm start
```

### Environment Configuration

```bash
PORT=8311
NODE_ENV=development

# Database (Optional)
MONGODB_URI=mongodb://localhost:27017/inventory-sync
REDIS_URL=redis://localhost:6379

# POS Integration
SQUARE_APPLICATION_ID=your-square-app-id
SQUARE_ACCESS_TOKEN=your-square-access-token
STRIPE_SECRET_KEY=sk_test_your_stripe_key

# Notifications
TWILIO_ACCOUNT_SID=your-twilio-account-sid
SENDGRID_API_KEY=your-sendgrid-api-key

# Multi-location Settings
MULTI_LOCATION_ENABLED=true
DEFAULT_TIMEZONE=America/New_York

# Automation
AUTO_REORDER_ENABLED=true
LOW_STOCK_THRESHOLD=10
CRITICAL_STOCK_THRESHOLD=5
```

## 📡 API Endpoints

### Inventory Management
- `GET /api/inventory/status/:locationId/:itemId` - Get real-time inventory status
- `POST /api/inventory/update/:locationId/:itemId` - Update inventory levels
- `GET /api/inventory/multi-location/:itemId` - Get inventory across locations
- `POST /api/inventory/bulk-update/:locationId` - Bulk update multiple items
- `POST /api/inventory/qr-code/:locationId/:itemId` - Generate QR code
- `GET /api/inventory/analytics/:locationId/:itemId` - Movement analytics

### Location Management
- `GET /api/locations/` - Get all locations with filters
- `GET /api/locations/:locationId` - Get specific location details
- `POST /api/locations/` - Register new location
- `POST /api/locations/nearby` - Find locations by coordinates
- `GET /api/locations/:locationId/status` - Check operating status
- `GET /api/locations/:locationId/capacity` - Get capacity information
- `POST /api/locations/transfer` - Transfer inventory between locations

### Reservations
- `POST /api/reservations/create` - Create inventory reservation
- `GET /api/reservations/:reservationId` - Get reservation details
- `POST /api/reservations/:reservationId/confirm` - Confirm reservation
- `POST /api/reservations/:reservationId/cancel` - Cancel reservation
- `POST /api/reservations/:reservationId/extend` - Extend reservation

## 🔌 WebSocket Events

### Real-time Inventory Updates
```javascript
// Join inventory room for location
socket.emit('join_inventory_room', { locationId: 'store_001', userId: 'user123' });

// Listen for inventory updates
socket.on('inventory_update', (update) => {
  console.log('Inventory changed:', update);
});

// Request inventory update
socket.emit('request_inventory_update', {
  locationId: 'store_001',
  itemId: 'item_456',
  updateData: {
    changeType: 'sale',
    oldQuantity: 50,
    newQuantity: 47,
    reason: 'pos_sale'
  }
});
```

### POS Integration
```javascript
// Process POS transaction
socket.emit('pos_transaction', {
  locationId: 'store_001',
  transactionData: {
    transactionId: 'txn_789',
    amount: 29.99,
    items: [
      { itemId: 'item_456', quantitySold: 3, currentStock: 50 }
    ],
    posSystem: 'square'
  }
});

// Listen for transaction results
socket.on('pos_transaction_processed', (result) => {
  console.log('Transaction processed:', result);
});
```

### Stock Alerts
```javascript
// Join alerts room
socket.emit('join_alerts_room', { locationId: 'store_001', userId: 'manager123' });

// Listen for stock alerts
socket.on('stock_alert', (alert) => {
  console.log('Stock alert:', alert);
  // alert.severity: 'low' | 'critical'
  // alert.currentQuantity: number
  // alert.itemId: string
});
```

## 📊 Real-time Inventory Flow

1. **Inventory Change**: Sale, restock, transfer, or manual adjustment
2. **Real-time Update**: Immediate WebSocket broadcast to connected clients
3. **Cache Update**: Redis cache updated for fast retrieval
4. **Batch Processing**: Changes queued for efficient database updates
5. **Alert Check**: Low stock thresholds evaluated automatically
6. **Auto-reorder**: Reorder triggers activated if enabled
7. **Notifications**: Alerts sent via email/SMS if configured

## 🏪 Multi-Location Example

```javascript
// Register a new location
const location = await fetch('/api/locations/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Downtown Store',
    type: 'retail_store',
    address: '123 Main St, New York, NY',
    coordinates: { lat: 40.7128, lng: -74.0060 },
    timezone: 'America/New_York',
    workingHours: {
      monday: { open: '09:00', close: '18:00' },
      tuesday: { open: '09:00', close: '18:00' },
      // ... other days
    },
    capacity: { storage: 10000, staff: 5, equipment: 20 }
  })
});

// Transfer inventory between locations
const transfer = await fetch('/api/locations/transfer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    fromLocationId: 'warehouse_001',
    toLocationId: 'store_001', 
    itemId: 'product_123',
    quantity: 50,
    transferData: {
      requestedBy: 'manager456',
      reason: 'restocking',
      estimatedDelivery: '2025-08-25T14:00:00Z'
    }
  })
});
```

## 📋 Reservation System Example

```javascript
// Create customer reservation
const reservation = await fetch('/api/reservations/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    locationId: 'store_001',
    itemId: 'product_123',
    quantity: 2,
    customerId: 'customer_789',
    duration: 1800000, // 30 minutes
    customerInfo: {
      name: 'John Doe',
      phone: '+1234567890',
      email: 'john@example.com'
    },
    reason: 'customer_pickup'
  })
});

// Confirm reservation (convert to sale)
await fetch(`/api/reservations/${reservation.reservationId}/confirm`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    confirmedBy: 'staff_456',
    orderId: 'order_123'
  })
});
```

## 🏷️ QR Code Generation

```javascript
// Generate QR code for inventory item
const qrCode = await fetch('/api/inventory/qr-code/store_001/product_123', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    size: 300,
    darkColor: '#000000',
    lightColor: '#FFFFFF'
  })
});

// QR code data structure:
{
  type: 'inventory_item',
  locationId: 'store_001',
  itemId: 'product_123', 
  url: 'https://inventory.activelog.com/inventory/store_001/product_123',
  timestamp: '2025-08-24T00:00:00Z'
}
```

## 🔄 Supply Chain Integration

The system includes comprehensive supply chain tracking:

- **Supplier Performance**: Track delivery times, quality, and reliability
- **Purchase Orders**: Monitor PO status from creation to delivery
- **Lead Time Optimization**: Analyze and optimize supplier lead times
- **Quality Metrics**: Track defect rates and returns by supplier
- **Cost Analysis**: Monitor supplier pricing trends and negotiate better rates

## 💰 Price Optimization Features

- **Dynamic Pricing Engine**: Automatically adjust prices based on demand
- **Competitor Monitoring**: Track competitor prices and adjust accordingly
- **Demand Forecasting**: Predict future demand using historical data
- **Margin Optimization**: Balance profit margins with competitive positioning
- **A/B Testing**: Test different price points to find optimal pricing

## 📱 POS System Integrations

### Square Integration
- Real-time inventory sync with Square POS
- Automatic stock deduction on sales
- Transaction logging and reconciliation
- Multi-location Square account support

### Stripe Integration  
- Payment processing with inventory tracking
- Subscription billing with inventory allocation
- Webhook-based inventory updates
- Multi-currency support

## 🔔 Notification Examples

### Low Stock Alert
```javascript
{
  type: 'stock_alert',
  severity: 'critical',
  locationId: 'store_001',
  itemId: 'product_123',
  currentQuantity: 3,
  threshold: 5,
  message: 'Critical: Only 3 units left of Product 123 at Downtown Store'
}
```

### Pickup Reminder
```javascript
{
  type: 'pickup_reminder',
  customerId: 'customer_789',
  pickupId: 'pickup_456',
  locationId: 'store_001', 
  scheduledTime: '2025-08-24T15:30:00Z',
  items: ['product_123', 'product_456'],
  message: 'Reminder: Your pickup is scheduled for today at 3:30 PM'
}
```

## 🏃‍♂️ Performance Features

- **Redis Caching**: Sub-millisecond inventory lookups
- **Batch Processing**: Efficient handling of high-volume updates
- **WebSocket Communication**: Real-time updates with minimal latency
- **Database Optimization**: Indexed queries and connection pooling
- **CDN Integration**: Fast QR code and asset delivery

## 🔒 Security Features

- **JWT Authentication**: Secure API access
- **Rate Limiting**: Prevent API abuse
- **Input Validation**: Comprehensive request validation
- **CORS Protection**: Configurable cross-origin policies
- **Audit Trails**: Complete logging of all inventory changes

## 📊 Monitoring & Analytics

- **Health Checks**: Real-time system health monitoring
- **Performance Metrics**: Response times and throughput tracking
- **Business Intelligence**: Inventory movement analytics
- **Custom Dashboards**: Location-specific reporting
- **Alert Management**: Configurable alert thresholds

---

**Inventory Sync Service** - Complete real-time inventory management for modern businesses! 📦⚡🏪