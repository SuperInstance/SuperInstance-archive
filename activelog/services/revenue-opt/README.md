# Revenue Optimizer Service

Advanced revenue optimization service with comprehensive features for maximizing business revenue through data-driven strategies.

## Features

- **$1 Monthly Minimum Target** - Configurable revenue targets with real-time monitoring
- **Churn Prediction & Prevention** - ML-powered churn prediction with automated retention campaigns
- **Upsell Opportunity Detection** - AI-driven upsell recommendations and campaign automation
- **Pricing A/B Testing** - Statistical A/B testing framework for pricing optimization
- **Lifetime Value Calculation** - Multiple LTV calculation methods with cohort analysis
- **Acquisition Cost Tracking** - Multi-touch attribution and channel optimization
- **Referral Program Optimization** - Automated referral program management and optimization
- **Conversion Funnel Analysis** - Comprehensive funnel analysis with bottleneck identification
- **Payment Failure Recovery** - Intelligent payment retry and recovery strategies
- **Subscription Optimization** - Dynamic pricing and feature optimization for subscriptions

## Installation

1. Clone the repository:
```bash
cd ~/activelog/services/revenue-opt
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Key environment variables:

- `MONTHLY_TARGET`: Monthly revenue target (default: $1.00)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string for caching
- `STRIPE_SECRET_KEY`: Stripe API key for payment processing
- `CHURN_MODEL_THRESHOLD`: Churn prediction threshold (default: 0.7)
- `AB_TEST_MIN_SAMPLE_SIZE`: Minimum sample size for A/B tests (default: 100)

## Running the Service

Start the service:
```bash
python main.py
```

The service will be available at `http://localhost:8347`

## API Documentation

Once running, visit `http://localhost:8347/docs` for interactive API documentation.

### Key Endpoints

#### Revenue Monitoring
- `POST /api/v1/revenue/record` - Record revenue transaction
- `GET /api/v1/revenue/targets` - Get target status
- `GET /api/v1/revenue/analytics` - Get analytics
- `GET /api/v1/revenue/forecast` - Get forecast

#### Churn Prevention
- `GET /api/v1/churn/predict/{customer_id}` - Predict churn probability
- `GET /api/v1/churn/at-risk` - Get at-risk customers
- `POST /api/v1/churn/retention-campaign/{customer_id}` - Execute retention

#### Upselling
- `GET /api/v1/upsell/opportunities` - Get upsell opportunities
- `POST /api/v1/upsell/campaign/{customer_id}` - Execute upsell campaign

#### A/B Testing
- `POST /api/v1/ab-test/create` - Create A/B test
- `GET /api/v1/ab-test/{test_id}/results` - Get test results

#### LTV Analysis
- `GET /api/v1/ltv/{customer_id}` - Calculate customer LTV
- `GET /api/v1/ltv/high-value` - Get high-value customers

#### Acquisition Tracking
- `POST /api/v1/acquisition/track` - Track acquisition event
- `GET /api/v1/acquisition/cac/{channel}` - Calculate channel CAC

#### Referral Programs
- `POST /api/v1/referral/program` - Create referral program
- `POST /api/v1/referral/link/{user_id}` - Generate referral link

#### Funnel Analysis
- `POST /api/v1/funnel/track/{user_id}` - Track user journey
- `GET /api/v1/funnel/analyze` - Analyze funnel performance

#### Payment Recovery
- `POST /api/v1/payment/failure` - Record payment failure
- `POST /api/v1/payment/retry/{failure_id}` - Retry payment

#### Subscription Optimization
- `POST /api/v1/subscription/plan` - Create subscription plan
- `GET /api/v1/subscription/optimize/pricing/{plan_id}` - Optimize pricing

## Architecture

The service is built with:
- **FastAPI** - Modern, fast web framework
- **Pydantic** - Data validation and settings management
- **SQLAlchemy** - SQL toolkit and ORM
- **Redis** - Caching and session storage
- **Scikit-learn** - Machine learning models
- **NumPy/Pandas** - Data analysis and processing

## Service Structure

```
src/
├── core/           # Core business logic
│   ├── config.py   # Configuration settings
│   └── revenue_monitor.py  # Revenue monitoring engine
├── services/       # Business services
│   ├── churn_predictor.py
│   ├── upsell_detector.py
│   ├── ab_testing.py
│   ├── ltv_calculator.py
│   ├── acquisition_tracker.py
│   ├── referral_optimizer.py
│   ├── funnel_analyzer.py
│   ├── payment_recovery.py
│   └── subscription_optimizer.py
├── models/         # Data models
│   └── customer.py
├── api/           # API routes
│   └── router.py
└── utils/         # Utility functions
```

## Machine Learning Models

The service includes several ML models:

1. **Churn Prediction Model** - Random Forest classifier for predicting customer churn
2. **Upsell Detection Model** - Gradient Boosting classifier for identifying upsell opportunities
3. **Price Elasticity Model** - Linear regression for pricing optimization
4. **LTV Prediction Model** - Multiple methods including cohort and predictive modeling

## Revenue Target System

The service enforces a minimum $1 monthly revenue target and provides:
- Real-time target tracking
- Automated alerts when targets are at risk
- Forecasting based on historical data
- Recommendations for target achievement

## Integration

### External Services
- **Stripe** - Payment processing and subscription management
- **SendGrid** - Email notifications and campaigns
- **Twilio** - SMS notifications
- **Slack** - Alert notifications

### Database Schema
The service expects customer and transaction data in specific formats. See the models directory for schema definitions.

## Monitoring & Alerts

The service provides comprehensive monitoring:
- Revenue target alerts
- Churn risk notifications
- Payment failure alerts
- A/B test result notifications
- Performance metrics tracking

## Testing

Run tests:
```bash
pytest
```

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Use type hints consistently

## License

Proprietary - ActiveLog Revenue Optimization System