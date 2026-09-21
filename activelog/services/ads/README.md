# ActiveLog Ad Serving System

A comprehensive advertising system that integrates Google AdSense, affiliate marketing, and intelligent ad placement with privacy-first design and revenue optimization.

## 🚀 Features

### Core Ad Management
- **Dynamic Ad Frequency** - Smart frequency capping based on user activity and tier
- **User Banner Preferences** - Users can choose 1 or 2 banner placements
- **Ad-Free Zones** - Automatic ad removal for premium/enterprise users and sensitive pages
- **Revenue Tracking** - Detailed per-user revenue analytics and reporting
- **Intelligent Placement** - Context-aware ad positioning based on page type and user behavior

### Google AdSense Integration
- **Auto-Optimization** - AI-powered performance monitoring and optimization
- **Compliance Monitoring** - Automatic policy compliance checking
- **A/B Testing** - Built-in testing for ad placement and formats
- **Performance Analytics** - Real-time revenue and engagement metrics
- **Fraud Detection** - Suspicious activity monitoring and alerts

### Affiliate Marketing
- **Multi-Network Support** - Amazon Associates, Commission Junction, ShareASale, and more
- **Smart Link Generation** - Automatic affiliate link creation with tracking
- **Contextual Recommendations** - AI-powered product recommendations based on user activity
- **Commission Tracking** - Detailed commission analytics and performance metrics
- **Revenue Optimization** - Intelligent network selection and product targeting

### Privacy & Compliance
- **GDPR Compliance** - User consent management and data protection
- **Ad-Free Options** - Complete ad removal for paid users
- **Targeted Ad Controls** - User-configurable ad personalization
- **Content Policy Monitoring** - Automatic compliance checking for AdSense policies

## 📁 Project Structure

```
/services/ads/
├── core/
│   └── ad_manager.py           # Core ad management system
├── integrations/
│   └── adsense_integration.py  # Google AdSense API integration
├── affiliate/
│   └── affiliate_manager.py    # Affiliate marketing system
├── tracking/
│   └── revenue_tracker.py      # Revenue tracking and analytics
├── ad_service.py              # Main service orchestrator
└── README.md                  # This file
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- asyncio support
- Google AdSense account (for production)
- Affiliate network accounts (optional)

### Quick Start

1. **Navigate to the ad service directory:**
   ```bash
   cd ~/activelog/services/ads/
   ```

2. **Test the core ad system:**
   ```bash
   python3 core/ad_manager.py
   ```

3. **Test AdSense integration:**
   ```bash
   python3 integrations/adsense_integration.py
   ```

4. **Test affiliate system:**
   ```bash
   python3 affiliate/affiliate_manager.py
   ```

5. **Run the full ad service:**
   ```bash
   python3 ad_service.py
   ```

## 📚 Usage Examples

### Basic Ad Serving

```python
from ad_service import AdService, AdServiceConfig
from core.ad_manager import UserTier

# Initialize ad service
config = AdServiceConfig(
    adsense_enabled=True,
    affiliate_enabled=True,
    frequency_optimization=True
)

ad_service = AdService(config)
await ad_service.initialize()

# Get ads for a page
ads = await ad_service.get_page_ads(
    user_id="user123",
    page_path="/dashboard",
    user_tier=UserTier.FREE,
    page_type="dashboard",
    is_mobile=False,
    usage_hours_today=4.5
)

print(f"Serving {ads['total_ads']} ads with ${ads['estimated_revenue']:.3f} potential revenue")
```

### User Preference Management

```python
# Set user ad preferences
await ad_service.update_user_ad_preferences("user123", {
    "banner_count": 2,        # 1 or 2 banners
    "ad_free_enabled": False, # Premium ad-free option
    "targeted_ads": True      # Personalized ads
})

# Get user analytics
analytics = await ad_service.get_user_analytics("user123")
print(f"User revenue: ${analytics['combined_metrics']['total_revenue']:.2f}")
```

### Affiliate Link Generation

```python
from affiliate.affiliate_manager import AffiliateManager

affiliate_manager = AffiliateManager()

# Generate affiliate link
link_result = await affiliate_manager.generate_affiliate_link(
    "https://www.amazon.com/dp/B08N5WRWNW",
    user_id="user123",
    campaign="fishing_module"
)

if link_result["success"]:
    print(f"Affiliate link: {link_result['affiliate_link']['affiliate_url']}")
    print(f"Commission rate: {link_result['estimated_commission_rate']}%")
```

### Smart Product Recommendations

```python
# Get contextual recommendations
recommendations = await affiliate_manager.get_smart_recommendations(
    user_id="user123",
    module="fishing",
    context="fishing_trip"
)

for rec in recommendations:
    product = rec["product"]
    print(f"{product['name']}: ${product['price']} - {rec['recommendation_reason']}")
```

## 🔧 Configuration

### Ad Service Configuration

```python
config = AdServiceConfig(
    adsense_enabled=True,          # Enable Google AdSense
    affiliate_enabled=True,        # Enable affiliate marketing
    frequency_optimization=True,   # Dynamic frequency adjustment
    compliance_monitoring=True,    # Automatic policy compliance
    revenue_tracking=True,         # Detailed revenue analytics
    debug_mode=False              # Debug logging
)
```

### User Tier Settings

```python
# Frequency caps by user tier
frequency_caps = {
    UserTier.FREE: 8,        # 8 ads per hour
    UserTier.PREMIUM: 3,     # 3 ads per hour  
    UserTier.ENTERPRISE: 0   # No ads
}
```

### Ad-Free Zones

```python
ad_free_zones = {
    'payment_pages': ['/billing', '/payment', '/checkout'],
    'user_privacy': ['/privacy', '/data-export', '/account-delete'],
    'admin_areas': ['/admin', '/system', '/diagnostics'],
    'premium_features': ['/premium/', '/enterprise/']
}
```

## 📊 Analytics & Reporting

### Revenue Summary
```python
# Get revenue summary
revenue_summary = await ad_service.get_revenue_summary()

print(f"Total Revenue: ${revenue_summary['total_revenue']}")
print(f"AdSense: {revenue_summary['revenue_breakdown']['adsense_percentage']}%")
print(f"Affiliate: {revenue_summary['revenue_breakdown']['affiliate_percentage']}%")
```

### User Analytics
```python
# Individual user analytics
user_analytics = await ad_service.get_user_analytics("user123")

metrics = user_analytics["combined_metrics"]
print(f"Revenue: ${metrics['total_revenue']:.4f}")
print(f"Clicks: {metrics['total_clicks']}")
print(f"Impressions: {metrics['total_impressions']}")
```

### Performance Optimization
```python
# Run optimization cycle
optimization = await ad_service.run_optimization_cycle()

for recommendation in optimization["overall_recommendations"]:
    print(f"Priority {recommendation['priority']}: {recommendation['recommendation']}")
```

## 🔗 API Endpoints

### Core Ad Serving
- `GET /ads/page` - Get ads for a specific page
- `POST /ads/preferences` - Update user ad preferences
- `POST /ads/interaction` - Record ad interactions (clicks, conversions)

### Analytics
- `GET /ads/analytics/user/{user_id}` - User-specific analytics
- `GET /ads/analytics/revenue` - Revenue summary
- `GET /ads/analytics/performance` - Performance metrics

### Affiliate Management
- `POST /ads/affiliate/generate` - Generate affiliate link
- `GET /ads/affiliate/recommendations` - Get product recommendations
- `POST /ads/affiliate/interaction` - Record affiliate interactions

### Service Management
- `GET /ads/health` - Service health status
- `POST /ads/optimize` - Run optimization cycle
- `POST /ads/compliance` - Check content compliance

## 🎯 Ad Placement Strategy

### Page Types and Optimal Placements

**Dashboard Pages:**
- Header leaderboard (728x90)
- Sidebar rectangle (300x250)
- Contextual affiliate recommendations

**Module Pages:**
- Content rectangle (300x250)
- Sidebar skyscraper (160x600)
- Module-specific product recommendations

**Mobile Pages:**
- Mobile banner (320x50)
- Native ads integrated with content
- Swipeable product recommendations

### User Tier Strategies

**Free Users:**
- Maximum ad frequency for revenue optimization
- 1-2 banner options based on preference
- Full affiliate recommendations

**Premium Users:**
- Reduced ad frequency (3 per hour)
- Option for complete ad removal
- Premium-relevant affiliate content only

**Enterprise Users:**
- Complete ad-free experience
- No tracking or analytics collection
- Focus on core platform functionality

## 🛡️ Privacy & Compliance

### GDPR Compliance
- User consent management for targeted ads
- Data minimization and purpose limitation
- Right to withdraw consent and delete data
- Transparent privacy controls

### AdSense Policy Compliance
- Automatic content scanning for policy violations
- Traffic quality monitoring and fraud detection
- Placement compliance checking
- Invalid click detection and prevention

### Affiliate Compliance
- FTC disclosure requirements
- Transparent affiliate relationship indication
- Geographic compliance for international users
- Network-specific terms compliance

## 📈 Revenue Optimization

### Dynamic Frequency Adjustment
```python
# Frequency based on user activity
if usage_hours_today > 8:
    frequency = min(base_frequency + 3, 10)  # More active = more ads
elif usage_hours_today > 4:
    frequency = base_frequency
else:
    frequency = max(base_frequency - 2, 2)   # Less active = fewer ads
```

### Contextual Product Matching
```python
# Module-specific recommendations
module_products = {
    "fishing": ["fishing_gear", "marine_equipment"],
    "business": ["business_tools", "software"],
    "study": ["education", "productivity_tools"],
    "gaming": ["gaming_gear", "streaming_tools"]
}
```

### Network Performance Optimization
```python
# Automatic network selection based on performance
best_network = max(networks, key=lambda n: n.average_commission_rate * n.conversion_rate)
```

## 🔍 Monitoring & Alerts

### Performance Monitoring
- Real-time revenue tracking
- Conversion rate monitoring
- Click-through rate analysis
- User engagement metrics

### Compliance Alerts
- Policy violation detection
- Suspicious traffic patterns
- Invalid click activity
- Content policy breaches

### Revenue Alerts
- Daily revenue targets
- Commission payment notifications
- Performance degradation warnings
- Optimization opportunities

## 🚀 Advanced Features

### A/B Testing
```python
# Test different ad placements
test_variants = {
    "control": {"header": True, "sidebar": False},
    "variant_a": {"header": False, "sidebar": True},
    "variant_b": {"header": True, "sidebar": True}
}
```

### Machine Learning Integration
- User behavior prediction for optimal ad timing
- Content analysis for contextual ad placement
- Revenue prediction and optimization
- Fraud detection using ML models

### Multi-Language Support
- Localized ad content and affiliate products
- Regional compliance management
- Currency conversion and reporting
- Cultural sensitivity in ad placement

## 📞 Support & Maintenance

### Health Monitoring
```bash
# Check service health
python3 ad_service.py health

# Run diagnostics
python3 ad_service.py diagnose

# Performance analysis
python3 ad_service.py analyze --days 30
```

### Common Issues
1. **Low Revenue**: Check ad placement, user tiers, and frequency settings
2. **Compliance Violations**: Review content and traffic quality
3. **Poor Performance**: Run optimization cycle and adjust targeting
4. **Integration Errors**: Verify API keys and network configurations

## 📄 License

This ad serving system is part of the ActiveLog platform and follows the same licensing terms.

---

**Note**: This system is designed for production use with proper API keys and affiliate network accounts. The examples shown use mock data for testing purposes.