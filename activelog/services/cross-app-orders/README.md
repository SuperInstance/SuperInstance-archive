# Cross-App Order Routing Service

A comprehensive order routing system that bridges DMLog and MakerLog platforms for 3D printing services.

## Overview

This service manages the complete 3D printing order lifecycle from DMLog customers to MakerLog makers, including:

- **Order Processing Pipeline**: DMLog-to-MakerLog order routing
- **Price Aggregation**: Multi-maker pricing comparison and optimization
- **Proximity Matching**: Geographic maker-customer matching
- **Priority Queuing**: Rush order processing with dynamic pricing
- **Escrow Payments**: Secure payment handling with milestone releases
- **Order Tracking**: Real-time cross-platform order tracking
- **Quality Assurance**: Multi-stage quality control workflow
- **Dispute Resolution**: Automated and manual dispute handling

## Features

### 🔄 Order Processing
- Automated order analysis and feasibility checking
- Intelligent maker matching based on capabilities and location
- Multi-stage quote aggregation from eligible makers
- Priority queue system with rush order support

### 💰 Payment System
- Secure escrow payment system with Stripe integration
- Milestone-based payment releases
- Dispute handling with refund capabilities
- Automatic fee calculation and distribution

### 📍 Location Services
- Proximity-based maker matching within configurable radius
- Geospatial optimization for shipping costs
- Service area analysis and recommendations

### 🚀 Performance
- Redis-backed caching for fast quote retrieval
- Bull queue system for scalable job processing
- Real-time progress tracking and notifications

## Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│     DMLog       │────┤  Order Routing       │────┤   MakerLog      │
│   (Customers)   │    │     Service          │    │   (Makers)      │
└─────────────────┘    └──────────────────────┘    └─────────────────┘
                                  │
                       ┌──────────────────────┐
                       │     Payment          │
                       │     Escrow           │
                       │    (Stripe)          │
                       └──────────────────────┘
```

### Core Services
- **Order Pipeline Service**: Main order processing workflow
- **Pricing Aggregation Service**: Multi-maker quote collection
- **Proximity Matching Service**: Geographic maker discovery
- **Priority Queue Service**: Order prioritization and processing
- **Escrow Payment Service**: Secure payment handling

### Data Models
- **Order**: Complete order lifecycle tracking
- **Maker**: Maker profiles with capabilities and availability

## Quick Start

### Prerequisites
- Node.js 18+
- MongoDB
- Redis
- Stripe account (for payments)

### Installation

```bash
# Clone and install dependencies
cd ~/activelog/services/cross-app-orders
npm install

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration

# Start the service
npm run dev
```

### Environment Variables

Key configuration variables:

```bash
PORT=8301
MONGODB_URI=mongodb://localhost:27017/cross-app-orders
REDIS_URL=redis://localhost:6379
STRIPE_SECRET_KEY=sk_test_your_stripe_key
DMLOG_API_KEY=your_dmlog_api_key
MAKERLOG_API_KEY=your_makerlog_api_key
```

## API Endpoints

### Order Management
- `POST /api/orders/dmlog/create` - Create order from DMLog
- `GET /api/orders/:orderId` - Get order details
- `PUT /api/orders/:orderId/status` - Update order status
- `POST /api/orders/:orderId/maker/select` - Select maker for order

### Payment System
- `POST /api/payments/escrow/create` - Create escrow payment
- `POST /api/payments/escrow/:orderId/capture` - Capture payment
- `PUT /api/payments/escrow/:orderId/milestone` - Update milestones
- `POST /api/payments/escrow/:orderId/dispute` - Initiate dispute

### Maker Discovery
- `GET /api/makers/search` - Search makers by location
- `GET /api/makers/:makerId` - Get maker profile

### Order Tracking
- `GET /api/tracking/:orderId` - Get real-time tracking

## Order Flow

1. **Order Creation**: DMLog sends order to routing service
2. **Analysis**: System analyzes feasibility and requirements
3. **Maker Matching**: Geographic and capability-based matching
4. **Quote Aggregation**: Request and collect quotes from makers
5. **Maker Selection**: Customer selects preferred maker
6. **Payment Processing**: Escrow payment creation and authorization
7. **Production**: Payment capture, order enters production queue
8. **Quality Control**: Multi-stage quality assurance workflow
9. **Shipping**: Order fulfillment and tracking
10. **Completion**: Payment release and order closure

## Payment System

### Escrow Process
1. **Authorization**: Payment authorized but not captured
2. **Capture**: Payment captured when production starts
3. **Hold Period**: 7-day escrow hold after delivery
4. **Release**: Automatic release to maker (or earlier on milestones)
5. **Disputes**: Manual dispute resolution with refund capabilities

### Fee Structure
- Service Fee: 5% of order value
- Stripe Processing: 2.9% + $0.30
- Rush Order Premium: 50%-150% based on urgency

## Development

### Testing
```bash
npm test                # Run test suite
npm run test:watch      # Watch mode
npm run test:coverage   # Coverage report
```

### Code Quality
```bash
npm run lint           # ESLint
npm run lint:fix       # Auto-fix issues
```

### Database Management
```bash
# Seed test data
npm run seed

# Reset database
npm run db:reset
```

## Monitoring

### Health Checks
- `GET /health` - Service health status
- Database connectivity
- Redis connectivity
- Queue system status

### Metrics
- Order processing times
- Payment success rates
- Maker response times
- System performance metrics

### Logging
- Structured JSON logging
- Business event tracking
- Error monitoring with stack traces
- Performance logging

## Security

### Authentication
- JWT tokens for user authentication
- API keys for cross-service communication
- Role-based authorization (customer, maker, admin)

### Payment Security
- PCI DSS compliant payment handling
- Stripe secure vault for payment methods
- End-to-end encryption for sensitive data

### Data Protection
- Order ownership validation
- Maker profile access controls
- Audit trails for all transactions

## Deployment

### Docker Support
```bash
# Build image
docker build -t cross-app-orders .

# Run with docker-compose
docker-compose up -d
```

### Production Configuration
- Environment-based configuration
- Database migrations
- SSL/TLS termination
- Load balancer setup
- Monitoring and alerting

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests for new functionality
4. Ensure code quality checks pass
5. Submit pull request

## License

Proprietary - ActiveLog Inc.

## Support

For technical support or questions:
- Internal Documentation: [Link to internal docs]
- Issue Tracker: [Link to issue tracker]
- Team Chat: [Link to team chat]