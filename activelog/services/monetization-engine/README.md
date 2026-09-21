# Monetization Engine

A comprehensive monetization and billing system for the ActiveLog platform, providing subscription management, usage-based billing, affiliate programs, and enterprise licensing.

## Features

### 🔧 Core Payment Processing
- **Stripe Integration**: Full payment processing with webhooks
- **Subscription Management**: Free/Pro/Enterprise tiers with automatic billing
- **Usage-based Billing**: Compute credits, API calls, storage overages
- **Tax Calculation**: Automatic tax calculation for US/EU/CA

### 🤝 Affiliate Program
- **Multi-tier Commission Structure**: Bronze/Silver/Gold/Platinum tiers
- **Advanced Tracking**: Click tracking, conversion attribution
- **Marketing Materials**: Banners, links, promotional content
- **Automated Payouts**: Monthly payout processing

### 💰 Enterprise Features
- **White-label Licensing**: Custom branding and deployment options
- **Enterprise Tiers**: Custom pricing and features for large organizations
- **Marketplace Fees**: Transaction fee calculation for marketplace transactions

### 📊 Analytics & Reporting
- **Revenue Analytics**: MRR, churn, growth metrics
- **Usage Analytics**: Credit usage patterns and optimization
- **Financial Reporting**: Automated report generation
- **Billing Alerts**: Spend limits and usage notifications

### 🎯 Ad Integration
- **Google AdSense**: Free tier ad serving with revenue sharing
- **Ad Performance**: Impression and click tracking
- **User Controls**: Ad preferences and blocking options

## Quick Start

### Prerequisites
- Node.js 16+
- PostgreSQL 13+
- Redis 6+
- Stripe account with API keys

### Installation

1. **Clone and install dependencies**:
```bash
cd /home/activeloguser/activelog/services/monetization-engine
npm install
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Set up database**:
```bash
npm run migrate
```

4. **Start the server**:
```bash
npm run dev  # Development
npm start    # Production
```

The server will start on port 8300.

## Environment Variables

### Required Configuration
```bash
# Server
PORT=8300
NODE_ENV=development
SECRET_KEY=your-super-secret-key
JWT_SECRET=your-jwt-secret

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/monetization_db
REDIS_URL=redis://localhost:6379

# Stripe
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
```

## API Endpoints

### Authentication
All endpoints (except webhooks and public endpoints) require JWT authentication via `Authorization: Bearer <token>` header.

### Stripe & Payments
- `POST /api/stripe/payment-intent` - Create payment intent
- `POST /api/stripe/subscription` - Create subscription
- `POST /api/stripe/webhook` - Stripe webhook handler
- `GET /api/stripe/pricing` - Get pricing plans

### Subscriptions
- `GET /api/subscriptions/current` - Get user's current subscription
- `GET /api/subscriptions/usage` - Get usage metrics and limits
- `PUT /api/subscriptions/plan` - Change subscription plan
- `DELETE /api/subscriptions/cancel` - Cancel subscription

### Billing
- `GET /api/billing/usage-calculation` - Calculate current usage costs
- `POST /api/billing/credits/purchase` - Purchase compute credits
- `GET /api/billing/history` - Get billing history
- `POST /api/billing/alerts` - Set billing alerts

### Affiliate Program
- `POST /api/affiliate/register` - Register as affiliate
- `GET /api/affiliate/dashboard` - Get affiliate dashboard
- `POST /api/affiliate/links` - Generate affiliate links
- `GET /api/affiliate/click/:linkId` - Track affiliate clicks
- `POST /api/affiliate/conversion` - Track conversions

### Compute Credits
- `GET /api/credits/balance` - Get credit balance
- `POST /api/credits/spend` - Spend credits for service
- `GET /api/credits/pricing` - Get credit pricing packages
- `GET /api/credits/analytics` - Get usage analytics

### AdSense Integration
- `GET /api/adsense/config` - Get ad configuration
- `POST /api/adsense/impression` - Track ad impression
- `POST /api/adsense/click` - Track ad click
- `GET /api/adsense/earnings` - Get ad earnings (free tier)

## Database Schema

### Core Tables
- `users` - User accounts
- `subscriptions` - User subscriptions
- `stripe_customers` - Stripe customer data
- `usage_metrics` - Usage tracking per user/period
- `billing_history` - All billing transactions

### Affiliate Tables
- `affiliates` - Affiliate accounts
- `affiliate_links` - Generated affiliate links
- `affiliate_clicks` - Click tracking
- `affiliate_conversions` - Conversion tracking
- `affiliate_payouts` - Payout management

### Credit System
- `compute_credit_transactions` - Credit purchases and usage
- `credit_alerts` - Usage alert configuration
- `credit_transfers` - Credit transfers between users

## Subscription Tiers

### Free Tier
- 1GB storage
- 1,000 API calls/month
- Ad-supported
- Community support
- 7-day backup retention

### Pro Tier ($29.99/month)
- 100GB storage
- 50,000 API calls/month
- No ads
- Email support
- 30-day backup retention
- 1,000 compute credits

### Enterprise Tier ($99.99/month)
- Unlimited storage & API calls
- Priority support
- 365-day backup retention
- 10,000 compute credits
- White-label options
- Custom integrations

## Usage-Based Billing

### Overage Rates
- **Storage**: $0.50/GB over plan limit
- **API Calls**: $0.10/1,000 calls over plan limit
- **Bandwidth**: $0.20/GB over 10GB free allowance

### Compute Credits
- **Base Rate**: $1.00/100 credits
- **Bulk Discounts**: 
  - 1,000+ credits: 10% off
  - 5,000+ credits: 15% off
  - 10,000+ credits: 20% off

## Affiliate Program

### Commission Structure
- **Bronze** (Default): 15% commission
- **Silver** (20+ conversions, $20+ earnings): 17% commission
- **Gold** (50+ conversions, $50+ earnings): 20% commission
- **Platinum** (100+ conversions, $100+ earnings): 25% commission

### Tracking
- 30-day attribution window
- Real-time click and conversion tracking
- Detailed performance analytics
- Marketing materials and tools

## Development

### Project Structure
```
src/
├── config/          # Database, Redis, Stripe configuration
├── middleware/      # Authentication, error handling
├── models/          # Database models (if using ORM)
├── routes/          # API route handlers
├── services/        # Business logic services
├── utils/           # Utilities and helpers
├── jobs/            # Background job definitions
└── server.js        # Main application entry point
```

### Available Scripts
```bash
npm start          # Start production server
npm run dev        # Start development server with nodemon
npm test           # Run test suite
npm run lint       # Run ESLint
npm run migrate    # Run database migrations
npm run seed       # Run database seeds
```

### Adding New Features
1. Create route handlers in `src/routes/`
2. Implement business logic in `src/services/`
3. Add database migrations if needed
4. Update API documentation
5. Add tests for new functionality

## Background Jobs

The system includes several cron jobs for automated processing:

- **Monthly Billing** (1st of month, 2 AM): Process subscription renewals
- **Expired Credits Cleanup** (Daily, 3 AM): Mark expired credits
- **Affiliate Payouts** (1st of month, 4 AM): Process affiliate payments
- **Billing Alerts** (Daily, 8 AM): Send usage and spending alerts
- **Affiliate Tier Updates** (1st of month, 5 AM): Update commission tiers
- **Daily Reports** (Daily, 6 AM): Generate revenue reports
- **Payment Sync** (Every 15 minutes): Sync payment status with Stripe

## Security Features

- **JWT Authentication**: Secure API access
- **Rate Limiting**: Prevent abuse
- **Input Validation**: Sanitize all inputs
- **SQL Injection Protection**: Parameterized queries
- **CORS Configuration**: Cross-origin request handling
- **Webhook Verification**: Stripe webhook signature validation

## Monitoring & Logging

- **Structured Logging**: JSON-formatted logs with context
- **Log Rotation**: Daily rotation with compression
- **Audit Trail**: Track all financial transactions
- **Error Tracking**: Comprehensive error logging
- **Performance Metrics**: Request duration and success rates

## Deployment

### Production Checklist
- [ ] Set `NODE_ENV=production`
- [ ] Configure production database
- [ ] Set up Redis cluster
- [ ] Configure HTTPS/SSL
- [ ] Set up log aggregation
- [ ] Configure monitoring alerts
- [ ] Test webhook endpoints
- [ ] Verify Stripe webhook signatures
- [ ] Set up backup procedures

### Health Checks
The `/health` endpoint provides system status:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "uptime": 3600,
  "memory": {...},
  "version": "1.0.0"
}
```

## Support

For technical support or questions:
- Create an issue in the project repository
- Contact the development team
- Check the API documentation for endpoint details

## License

This project is licensed under the MIT License.