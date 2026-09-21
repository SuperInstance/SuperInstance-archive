# Billing & Subscription Management System

## Overview

This module handles all billing, subscription management, usage tracking, and payment processing for the Swarm Intelligence Platform.

## Architecture

```
billing/
├── stripe_integration.py      # Stripe API integration
├── subscription_manager.py    # Subscription lifecycle management
├── usage_tracker.py           # Agent-hour and API usage tracking
├── pricing_engine.py          # Dynamic pricing and upgrades
├── invoice_generator.py       # Invoice and receipt generation
├── payment_processor.py       # Payment method handling
├── webhook_handler.py         # Stripe webhook processing
├── models.py                  # Database models
├── schemas.py                 # Pydantic validation schemas
└── tests/                     # Unit and integration tests
```

## Features

### 1. Subscription Management
- Create, update, cancel subscriptions
- Plan upgrades and downgrades
- Prorated billing
- Trial management
- Usage-based billing

### 2. Usage Tracking
- Real-time agent-hour metering
- API call counting
- Storage usage monitoring
- Overage calculation
- Usage forecasting

### 3. Payment Processing
- Multiple payment methods (credit card, bank transfer)
- Automatic retry on failed payments
- Payment method updates
- Invoice generation
- Receipt email delivery

### 4. Billing Analytics
- MRR/ARR tracking
- Churn analysis
- Revenue by plan
- Customer lifetime value
- Cohort analysis

## Technologies

- **Payment Gateway**: Stripe
- **Database**: PostgreSQL
- **Cache**: Redis (usage tracking)
- **Queue**: Celery (async billing tasks)
- **API**: FastAPI

## Setup

```bash
# Install dependencies
pip install stripe fastapi sqlalchemy redis celery

# Set environment variables
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...

# Run migrations
alembic upgrade head

# Start webhook listener
python -m billing.webhook_handler

# Start usage aggregation worker
celery -A billing.tasks worker --loglevel=info
```

## Usage Examples

### Create Subscription
```python
from billing.subscription_manager import SubscriptionManager

manager = SubscriptionManager()
subscription = manager.create_subscription(
    user_id="user_123",
    plan="pro",
    payment_method_id="pm_xxx"
)
```

### Track Usage
```python
from billing.usage_tracker import UsageTracker

tracker = UsageTracker()
tracker.record_agent_hours(
    user_id="user_123",
    swarm_id="swarm_456",
    agent_hours=2.5
)
```

### Upgrade Plan
```python
from billing.subscription_manager import SubscriptionManager

manager = SubscriptionManager()
manager.upgrade_subscription(
    user_id="user_123",
    new_plan="team",
    seats=5
)
```

## API Endpoints

### Subscription Management
- `POST /api/billing/subscribe` - Create subscription
- `GET /api/billing/subscription` - Get current subscription
- `PUT /api/billing/subscription/upgrade` - Upgrade plan
- `DELETE /api/billing/subscription/cancel` - Cancel subscription

### Payment Methods
- `POST /api/billing/payment-method` - Add payment method
- `GET /api/billing/payment-methods` - List payment methods
- `PUT /api/billing/payment-method/default` - Set default
- `DELETE /api/billing/payment-method/{id}` - Remove method

### Usage & Billing
- `GET /api/billing/usage` - Current usage
- `GET /api/billing/invoices` - List invoices
- `GET /api/billing/invoice/{id}` - Get invoice details
- `POST /api/billing/invoice/{id}/pay` - Pay invoice

### Webhooks
- `POST /api/billing/webhook` - Stripe webhook handler

## Database Schema

### subscriptions
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    stripe_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN,
    seats INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### usage_records
```sql
CREATE TABLE usage_records (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    subscription_id UUID,
    resource_type VARCHAR(50), -- agent_hours, api_calls, storage_gb
    quantity DECIMAL(10, 4),
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);
```

### invoices
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    subscription_id UUID,
    stripe_invoice_id VARCHAR(255),
    amount_due INTEGER, -- cents
    amount_paid INTEGER,
    status VARCHAR(50),
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    invoice_pdf_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Pricing Configuration

```python
PRICING_PLANS = {
    "free": {
        "price": 0,
        "agent_hours": 100,
        "api_calls": 100,
        "storage_gb": 1,
        "swarms": 3,
        "features": ["community_support", "public_projects"]
    },
    "hobbyist": {
        "price": 900,  # cents
        "agent_hours": 1000,
        "api_calls": 1000,
        "storage_gb": 10,
        "swarms": 10,
        "features": ["email_support", "private_projects", "ide_integrations"]
    },
    "pro": {
        "price": 4900,
        "agent_hours": 10000,
        "api_calls": 10000,
        "storage_gb": 100,
        "swarms": -1,  # unlimited
        "features": ["priority_support", "analytics", "webhooks", "sso"]
    },
    "team": {
        "price": 19900,  # per seat
        "agent_hours": 100000,  # shared pool
        "api_calls": -1,  # unlimited
        "storage_gb": 1000,
        "swarms": -1,
        "features": ["24_7_support", "team_management", "audit_logs", "rbac"]
    }
}

OVERAGE_PRICING = {
    "agent_hours": 10,  # cents per 100 agent-hours
    "api_calls": 5,     # cents per 1000 calls
    "storage_gb": 25    # cents per GB per month
}
```

## Billing Cycle

```
Day 1: Subscription starts
    ↓
Daily: Usage tracked in real-time
    ↓
Day 28: Usage alert at 80%
    ↓
Day 30: Billing period ends
    ↓
    → Calculate usage
    → Generate invoice
    → Charge payment method
    → Email invoice
    ↓
Day 31: New billing period starts
```

## Failed Payment Handling

```
Payment Fails
    ↓
Retry immediately
    ↓
Retry after 3 days
    ↓
Email warning + retry
    ↓
Retry after 7 days (final attempt)
    ↓
Downgrade to free tier
    ↓
After 30 days: Suspend account
    ↓
After 60 days: Delete data (with warning)
```

## Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests (requires Stripe test mode)
pytest tests/integration/

# Test webhook handling
stripe listen --forward-to localhost:8000/api/billing/webhook
```

## Security

- All Stripe API keys stored in environment variables
- Webhook signature verification required
- Payment data never stored (PCI compliance)
- Rate limiting on billing endpoints
- Audit logging for all billing operations

## Monitoring

- Alert on failed payments (>10% failure rate)
- Track subscription churn rate
- Monitor usage anomalies
- Revenue tracking dashboards
- Overage alerts

## Documentation

- Stripe integration guide: `/docs/stripe-integration.md`
- Billing API reference: `/docs/api/billing.md`
- Subscription lifecycle: `/docs/subscription-lifecycle.md`
- Usage tracking: `/docs/usage-tracking.md`

## Support

For billing issues:
- Email: billing@swarmintel.dev
- Slack: #billing-support
- On-call: PagerDuty escalation

## Roadmap

### Q1 2025
- [x] Stripe integration
- [x] Basic subscription management
- [x] Usage tracking
- [ ] Invoice generation

### Q2 2025
- [ ] Multiple payment methods
- [ ] Annual billing (20% discount)
- [ ] Enterprise invoicing (PO, wire transfer)
- [ ] Usage forecasting

### Q3 2025
- [ ] Multi-currency support
- [ ] Tax calculation (Stripe Tax)
- [ ] Dunning management
- [ ] Revenue recognition automation

### Q4 2025
- [ ] Partner revenue sharing
- [ ] Marketplace billing integration
- [ ] Custom enterprise pricing
- [ ] Billing analytics dashboard
