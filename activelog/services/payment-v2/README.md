# ActiveLog Payment System v2

Enhanced payment system with compute credit economics, affiliate management, bulk organization billing, and comprehensive financial features.

## 🚀 Features

### 💻 **Compute Credit Economics**
- **Multi-tier resource pricing** (CPU, GPU, Storage, Bandwidth)
- **Credit reservation system** for long-running jobs
- **Auto-recharge capabilities** with configurable thresholds
- **Usage analytics and forecasting**
- **Real-time cost estimation**

### 🤝 **Affiliate Commission Structure**
- **5-tier affiliate program**: Bronze → Silver → Gold → Platinum → Diamond
- **Progressive commission rates**: 10% → 12% → 15% → 20% → 25%
- **Automatic tier upgrades** based on performance
- **Referral bonuses and welcome credits**
- **Comprehensive analytics and leaderboards**

### 🏢 **Bulk Organization Billing**
- **Volume-based discounts** (up to 20% for enterprise usage)
- **Automated invoice generation** with PDF export
- **Usage forecasting** for budget planning
- **Flexible credit distribution** across team members
- **Enterprise payment terms** and credit limits

### 👥 **Credit Pooling for Groups**
- **Shared credit pools** for teams and organizations
- **Budget allocation and management**
- **Usage tracking per team member**
- **Automated credit distribution**

### 🔄 **Automatic Credit Purchasing**
- **Configurable auto-recharge** when balance drops below threshold
- **Multiple payment methods** support
- **Purchase history and analytics**
- **Failure handling and retry logic**

### 🌍 **International Currency Support**
- **Multi-currency support**: USD, EUR, GBP, JPY, CAD, AUD
- **Real-time exchange rates** via external APIs
- **Currency hedging** for price stability
- **Regional pricing adjustments**

### 📊 **Tax Calculation per Region**
- **Automated tax calculation** for global compliance
- **VAT/GST handling** for EU and other regions
- **Regional tax rate management**
- **Tax reporting and documentation**

### 🧾 **Invoice Generation System**
- **Professional invoice templates** with company branding
- **PDF generation and email delivery**
- **Automated billing cycles**
- **Payment tracking and reminders**
- **Multi-currency invoicing**

### 📅 **Subscription with Credits Integration**
- **Flexible billing cycles**: Monthly, Quarterly, Annual
- **Credit allocation per subscription cycle**
- **Usage overage handling**
- **Subscription analytics and management**

### 🔒 **Marketplace Escrow System**
- **Secure escrow** for marketplace transactions
- **Multi-party transaction support**
- **Dispute resolution workflow**
- **Automated release conditions**
- **Transaction history and auditing**

## 🏗️ Architecture

The system is built with a microservices architecture:

```
payment-v2/
├── src/
│   ├── main.py                 # FastAPI application (Port 8325)
│   ├── database.py            # Database models and connection
│   ├── credits/               # Compute credit economics
│   │   ├── economics.py       # Credit pricing and consumption logic
│   │   ├── routes.py          # Credit management API endpoints  
│   │   └── schemas.py         # Pydantic models for credits
│   ├── affiliates/            # Affiliate program management
│   │   ├── manager.py         # Affiliate logic and tier management
│   │   ├── routes.py          # Affiliate API endpoints
│   │   └── schemas.py         # Affiliate data models
│   ├── billing/               # Bulk billing for organizations
│   │   ├── bulk_manager.py    # Enterprise billing logic
│   │   └── routes.py          # Billing API endpoints
│   ├── groups/                # Credit pooling system
│   ├── autopurchase/          # Automatic credit purchasing
│   ├── currency/              # International currency support
│   ├── tax/                   # Regional tax calculations
│   ├── invoicing/             # Invoice generation and management
│   ├── subscriptions/         # Subscription billing with credits
│   └── escrow/                # Marketplace escrow transactions
└── static/                    # Static files and uploads
```

## 📊 Database Schema

### Core Models:
- **Users & Organizations**: User management with org relationships
- **ComputeCredit**: Credit balances and auto-recharge settings
- **CreditTransaction**: All credit movements and usage tracking
- **CreditPricing**: Tiered pricing for different resource types

### Affiliate System:
- **AffiliateProgram**: Affiliate configurations and tier levels
- **AffiliateCommission**: Commission transactions and payouts

### Billing System:
- **Invoice**: Generated invoices with line items
- **Subscription**: Recurring billing with credit allocation
- **CreditPool**: Shared credit pools for organizations

### International Support:
- **CurrencyRate**: Exchange rates for currency conversion
- **TaxRate**: Regional tax rates and regulations

### Marketplace:
- **EscrowTransaction**: Secure marketplace transactions
- **PaymentMethod**: User payment methods and preferences

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Installation

1. **Navigate to payment-v2 directory**
```bash
cd ~/activelog/services/payment-v2
```

2. **Start the system**
```bash
./start.sh
```

3. **Alternative manual start**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8325 --reload
```

The system will be available at `http://localhost:8325`

## 📖 API Documentation

### Credit Management
```http
GET /api/credits/balance/{user_id}     # Get user credit balance
POST /api/credits/consume              # Consume credits for compute usage
POST /api/credits/purchase             # Purchase credits with payment
GET /api/credits/analytics             # Usage analytics and insights
POST /api/credits/reserve              # Reserve credits for jobs
```

### Affiliate System
```http
POST /api/affiliates/program           # Create affiliate program
POST /api/affiliates/referral          # Process referral signup
GET /api/affiliates/stats/{id}         # Get affiliate statistics  
GET /api/affiliates/leaderboard        # Top affiliates ranking
POST /api/affiliates/commission        # Process commission payment
```

### Organization Billing
```http
POST /api/billing/organization/setup   # Configure org billing
GET /api/billing/usage-breakdown/{id}  # Detailed usage analysis
GET /api/billing/forecasts/{id}        # Usage and cost forecasting
POST /api/billing/process              # Process bulk billing cycle
```

### Currency & Tax
```http
GET /api/currency/rates                # Current exchange rates
POST /api/currency/convert             # Convert between currencies
GET /api/tax/rates/{region}            # Regional tax rates
POST /api/tax/calculate                # Calculate taxes for amount
```

### Invoicing & Subscriptions
```http
POST /api/invoicing/generate           # Generate professional invoice
GET /api/invoicing/{id}/pdf            # Download invoice PDF
POST /api/subscriptions/create         # Create credit subscription
GET /api/subscriptions/{id}            # Get subscription details
```

### Marketplace Escrow
```http
POST /api/escrow/create                # Create escrow transaction
POST /api/escrow/{id}/release          # Release funds to seller
POST /api/escrow/{id}/dispute          # Create dispute
```

## 🔧 Configuration

### Environment Variables
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/activelog_payment_v2

# Redis
REDIS_URL=redis://localhost:6379/1

# Server
HOST=0.0.0.0
PORT=8325
DEBUG=True

# External APIs
STRIPE_SECRET_KEY=sk_test_...
PAYPAL_CLIENT_ID=...
EXCHANGE_RATE_API_KEY=...

# Security
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
```

### Credit Economics Configuration
- **Base exchange rate**: 100 credits = $1 USD
- **Resource pricing**: Configurable per resource type and tier
- **Bulk discounts**: 5% ($100+) to 20% ($1000+)
- **Auto-recharge**: Configurable thresholds and amounts

### Affiliate Tiers
| Tier | Commission | Requirements | Benefits |
|------|------------|--------------|----------|
| Bronze | 10% | None | Base rate |
| Silver | 12% | $1K earnings, 10 referrals | Analytics |
| Gold | 15% | $5K earnings, 25 referrals | Custom materials |
| Platinum | 20% | $15K earnings, 50 referrals | Account manager |
| Diamond | 25% | $50K earnings, 100 referrals | Partnership |

## 🔗 Integration

This payment system integrates with the existing ActiveLog ecosystem:

- **ActiveLedger** (port 8122): Core financial ledger
- **Financial Management** (port 8080): QuickBooks and payroll
- **API Gateway** (port 8001): Request routing and auth
- **Auth Service** (port 8020): User authentication
- **Multiple Apps**: DMLog, StudyLog, MakerLog, etc.

## 🚦 Health Monitoring

The system includes comprehensive health monitoring:

```http
GET /health                    # Basic health check
GET /api/overview             # System capabilities overview
GET /api/credits/pricing      # Current pricing structure
GET /api/affiliates/tiers     # Affiliate tier information
```

## 📈 Analytics & Reporting

Built-in analytics provide insights into:
- **Credit usage patterns** by user, organization, resource type
- **Affiliate performance** with conversion tracking
- **Billing forecasts** based on historical usage
- **Revenue analytics** across all payment streams

## 🔐 Security & Compliance

- **PCI DSS compliance** for payment processing
- **GDPR compliance** for international users  
- **SOC 2 Type II** security standards
- **Regional tax compliance** (VAT, GST, Sales Tax)
- **Audit trails** for all financial transactions

## 📞 Support

For technical support or feature requests:
- **Documentation**: Available at `/docs` endpoint
- **Health Status**: Monitor at `/health` endpoint
- **API Reference**: Interactive docs at `/docs`

---

**ActiveLog Payment System v2** - Powering the future of compute economics and financial automation.