# Marketing Automation System

A comprehensive marketing automation platform with personalized ad serving, affiliate tracking, conversion optimization, and more.

## Features

### 🎯 Personalized Ad Serving
- Real-time ad auctions and bidding
- User profiling and behavioral targeting
- Multiple bidding strategies (CPC, CPA, ROAS)
- Campaign performance analytics
- Cross-device tracking

### 🤝 Affiliate Tracking
- Complete affiliate management system
- Click and conversion tracking with fraud detection
- Multiple attribution models (first-click, last-click, linear, time-decay)
- Commission calculation and payout management
- Real-time performance analytics

### 📊 Conversion Optimization
- Funnel analysis and optimization
- User journey tracking
- Exit-intent and cart abandonment recovery
- Dynamic personalization
- Performance bottleneck identification

### 🧪 A/B Testing
- Statistical testing engine with multiple methods
- Bayesian and frequentist approaches
- Sequential testing with early stopping
- Multivariate testing support
- Automated winner selection

### 📧 Email Campaign Management
- Multi-provider email delivery (SMTP, SendGrid, Mailchimp)
- Advanced personalization and segmentation
- A/B testing for email campaigns
- Automated drip campaigns
- Comprehensive analytics and tracking

### 📱 Social Media Integration
- Multi-platform posting (Facebook, Instagram, Twitter, LinkedIn, YouTube)
- Content optimization for each platform
- Automated scheduling with optimal timing
- Social media analytics and engagement tracking
- Campaign management across platforms

### 🔍 SEO Optimization
- Comprehensive website audits
- Keyword research and tracking
- Ranking monitoring across search engines
- Technical SEO analysis
- Content optimization recommendations

### 📁 "Exposed to Marketers" Folder Processing
- Automatic asset categorization and optimization
- Brand compliance checking
- Multi-format content processing (images, videos, documents)
- Marketing-ready asset generation
- Asset performance tracking

## Installation

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env
```

3. Configure Redis connection and API keys in `.env`

4. Start the service:
```bash
npm start
```

## Configuration

### Environment Variables

```env
# Server Configuration
PORT=8313
NODE_ENV=production

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Email Configuration
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASS=your-password

# API Keys
MAILCHIMP_API_KEY=your-mailchimp-key
SENDGRID_API_KEY=your-sendgrid-key
FACEBOOK_APP_ID=your-facebook-app-id
FACEBOOK_APP_SECRET=your-facebook-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-secret

# Security
ENCRYPTION_KEY=your-32-character-encryption-key
TRACKING_SECRET=your-tracking-secret
```

## API Endpoints

### Exposed Folder Processing
- `POST /api/exposed-folders/process` - Process marketing folder
- `GET /api/exposed-folders/:folderId/assets` - Get folder assets

### Ad Serving
- `POST /api/ads/serve` - Serve personalized ad
- `POST /api/ads/campaigns` - Create ad campaign
- `GET /api/ads/campaigns/:campaignId/performance` - Get campaign performance

### Affiliate Tracking
- `POST /api/affiliates/register` - Register affiliate
- `POST /api/affiliates/track-click` - Track affiliate click
- `GET /api/affiliates/:affiliateId/performance` - Get affiliate performance

### Conversion Optimization
- `POST /api/conversions/track` - Track conversion
- `POST /api/conversions/optimize` - Run optimization analysis

### A/B Testing
- `POST /api/ab-tests/create` - Create A/B test
- `POST /api/ab-tests/:testId/participate` - Participate in test
- `GET /api/ab-tests/:testId/results` - Get test results

### Email Campaigns
- `POST /api/email/campaigns` - Create email campaign
- `POST /api/email/campaigns/:campaignId/send` - Send campaign
- `GET /api/email/campaigns/:campaignId/analytics` - Get campaign analytics

### Social Media
- `POST /api/social/accounts/connect` - Connect social account
- `POST /api/social/posts/schedule` - Schedule social post
- `GET /api/social/analytics/:accountId` - Get social analytics

### SEO Optimization
- `POST /api/seo/analyze` - Analyze page SEO
- `POST /api/seo/keywords/research` - Research keywords
- `GET /api/seo/rankings/:domain` - Track rankings

## Architecture

### Services Overview

1. **ExposedFolderProcessor**: Processes marketing assets from designated folders
2. **PersonalizedAdServer**: Handles ad serving with real-time bidding
3. **AffiliateTracker**: Manages affiliate programs and tracking
4. **ConversionOptimizer**: Analyzes and optimizes conversion funnels
5. **ABTestingEngine**: Runs statistical A/B tests
6. **EmailCampaignManager**: Manages email marketing campaigns
7. **SocialMediaIntegrator**: Handles social media posting and analytics
8. **SEOOptimizer**: Provides SEO analysis and optimization

### Data Flow

```
User Request → Express Router → Service Layer → Redis Cache → Response
                                      ↓
                              WebSocket Updates
                                      ↓
                              Real-time Analytics
```

### WebSocket Events

The system emits real-time events via Socket.IO:

- `campaign_created` - New campaign created
- `ad_served` - Ad served to user
- `conversion_tracked` - Conversion recorded
- `test_result_significant` - A/B test reached significance
- `email_sent` - Email successfully sent
- `post_published` - Social media post published
- `seo_audit_completed` - SEO audit finished

## Usage Examples

### Creating an Ad Campaign
```javascript
const campaign = await fetch('/api/ads/campaigns', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Summer Sale Campaign',
    type: 'display',
    budget: { dailyBudget: 100, currency: 'USD' },
    targeting: {
      demographics: { age: { min: 25, max: 54 } },
      interests: ['shopping', 'fashion'],
      locations: [{ country: 'US' }]
    },
    biddingStrategy: {
      type: 'cpc_maximize_clicks',
      maxBid: 2.50
    }
  })
});
```

### Tracking a Conversion
```javascript
const conversion = await fetch('/api/conversions/track', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    userId: 'user-123',
    funnelId: 'funnel-456',
    eventType: 'purchase',
    value: 99.99,
    properties: {
      product: 'Premium Plan',
      category: 'subscription'
    }
  })
});
```

### Creating an A/B Test
```javascript
const test = await fetch('/api/ab-tests/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Homepage Hero Test',
    hypothesis: 'New hero image will increase conversions',
    variations: [
      {
        name: 'Control',
        changes: [{ selector: '#hero img', attribute: 'src', value: '/hero-old.jpg' }]
      },
      {
        name: 'Treatment',
        changes: [{ selector: '#hero img', attribute: 'src', value: '/hero-new.jpg' }]
      }
    ],
    configuration: {
      confidenceLevel: 95,
      minimumDetectableEffect: 10
    }
  })
});
```

## Monitoring & Analytics

### Dashboard
Access the unified analytics dashboard at:
- `GET /api/analytics/dashboard`

### Health Check
Monitor system health:
- `GET /health`

### Logs
Application logs are stored in the `logs/` directory:
- `logs/combined.log` - All logs
- `logs/error.log` - Error logs only

## Security Features

- Rate limiting on API endpoints
- Credential encryption for third-party integrations
- CSRF protection
- Input validation and sanitization
- Audit trails for all marketing activities

## Performance Optimization

- Redis caching for frequently accessed data
- Connection pooling for database operations
- Lazy loading of heavy marketing assets
- Background processing for analytics
- WebSocket connections for real-time updates

## Compliance

- GDPR compliance for EU users
- CAN-SPAM compliance for email campaigns
- Cookie consent management
- Data retention policies
- Right to be forgotten implementation

## Development

### Running Tests
```bash
npm test
```

### Development Mode
```bash
npm run dev
```

### Docker Support
```bash
docker build -t marketing-automation .
docker run -p 8313:8313 marketing-automation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API examples

---

Built with ❤️ for modern marketing teams.