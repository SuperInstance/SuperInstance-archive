# Marketing Analytics & Tracking Plan
## Swarm Intelligence Platform Launch

**Version:** 1.0
**Date:** 2025-10-14
**Owner:** Growth Team

---

## EXECUTIVE SUMMARY

This document outlines the complete analytics strategy for tracking user acquisition, activation, conversion, and retention throughout the Swarm Intelligence platform launch and beyond.

**Goal:** Data-driven optimization of every stage of the user journey from first touch to paying customer to advocate.

---

## TABLE OF CONTENTS

1. [Tracking Infrastructure](#tracking-infrastructure)
2. [UTM Parameter Strategy](#utm-parameter-strategy)
3. [Conversion Events](#conversion-events)
4. [Attribution Model](#attribution-model)
5. [KPI Dashboard](#kpi-dashboard)
6. [A/B Testing Plan](#ab-testing-plan)
7. [Launch Day Monitoring](#launch-day-monitoring)
8. [Tools & Integrations](#tools-integrations)

---

## TRACKING INFRASTRUCTURE

### Primary Analytics Platform

**Google Analytics 4 (GA4)**
- Universal tracking across website, docs, demo
- Enhanced e-commerce tracking for subscription flow
- Custom events for swarm-specific actions
- Real-time monitoring during launch

**Implementation:**
```html
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Secondary Platforms

**Mixpanel**
- Product analytics
- Funnel analysis
- Cohort retention tracking
- User journey mapping

**Segment**
- Centralized data collection
- Multi-platform distribution
- Customer data platform (CDP)

**Hotjar**
- Heatmaps and session recordings
- Conversion funnel visualization
- User feedback widgets

### Custom Event Tracking

**Backend Events (via API):**
```python
# Track swarm deployments
analytics.track(
    user_id=user.id,
    event='swarm_deployed',
    properties={
        'agent_count': swarm.agent_count,
        'template': swarm.template_name,
        'deployment_time': swarm.deploy_duration_ms,
        'plan': user.subscription_tier
    }
)
```

---

## UTM PARAMETER STRATEGY

### Standard UTM Structure

All marketing links must include UTM parameters:

```
https://www.swarmintel.dev?utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}&utm_term={term}
```

### Parameter Definitions

**utm_source:** Traffic source
- `producthunt` - ProductHunt
- `hackernews` - Hacker News
- `reddit` - Reddit
- `twitter` - Twitter
- `linkedin` - LinkedIn
- `google` - Google Ads
- `newsletter` - Email campaigns
- `github` - GitHub

**utm_medium:** Marketing medium
- `social` - Organic social
- `paid_social` - Paid social ads
- `organic` - Organic search
- `paid_search` - PPC
- `email` - Email marketing
- `referral` - Referral link
- `community` - Community posts

**utm_campaign:** Specific campaign
- `launch_2025` - Main launch campaign
- `producthunt_launch` - ProductHunt specific
- `startup_program` - Startup outreach
- `edu_program` - Education program
- `holiday_2025` - Holiday promotion
- `webinar_{date}` - Webinar series

**utm_content:** Content variant
- `hero_cta` - Hero section button
- `pricing_free` - Free tier CTA
- `pricing_pro` - Pro tier CTA
- `blog_post` - Blog post link
- `banner_top` - Top banner
- `popup_exit` - Exit intent popup

**utm_term:** Keyword (for paid search)
- Specific keywords for Google Ads campaigns

### Launch Day UTM Examples

**ProductHunt:**
```
https://www.swarmintel.dev?utm_source=producthunt&utm_medium=social&utm_campaign=launch_2025&utm_content=ph_main_link
```

**Twitter Thread:**
```
https://www.swarmintel.dev?utm_source=twitter&utm_medium=social&utm_campaign=launch_2025&utm_content=founder_thread
```

**Hacker News:**
```
https://www.swarmintel.dev?utm_source=hackernews&utm_medium=community&utm_campaign=launch_2025&utm_content=show_hn
```

**Reddit (r/MachineLearning):**
```
https://www.swarmintel.dev?utm_source=reddit&utm_medium=community&utm_campaign=launch_2025&utm_content=ml_subreddit
```

### UTM Parameter Spreadsheet

Maintain master spreadsheet: `utm_parameters.xlsx`

| Channel | Source | Medium | Campaign | Content | Full URL | QR Code |
|---------|--------|--------|----------|---------|----------|---------|
| ProductHunt | producthunt | social | launch_2025 | ph_main_link | [URL] | [QR] |
| Twitter | twitter | social | launch_2025 | founder_thread | [URL] | [QR] |
| Email | newsletter | email | launch_2025 | welcome_email | [URL] | - |

---

## CONVERSION EVENTS

### Awareness Stage

**Event:** `page_view`
**Properties:**
- page_url
- referrer
- utm_parameters
- device_type
- location

**Event:** `video_watched`
**Properties:**
- video_id (hero, demo, tutorial)
- watch_percentage (25%, 50%, 75%, 100%)
- watch_duration_seconds

**Event:** `documentation_viewed`
**Properties:**
- doc_page
- time_on_page
- scroll_depth

### Consideration Stage

**Event:** `signup_started`
**Properties:**
- signup_method (email, google, github)
- referral_source
- utm_campaign

**Event:** `signup_completed`
**Properties:**
- user_id
- signup_duration_seconds
- plan_selected (free, pro)
- payment_method (if pro)

**Event:** `demo_viewed`
**Properties:**
- demo_type (visual_designer, live_swarm, code_example)
- interaction_count
- time_spent

**Event:** `pricing_viewed`
**Properties:**
- plans_compared (free_vs_pro, pro_vs_team)
- calculator_used (boolean)
- time_on_pricing

### Activation Stage

**Event:** `first_swarm_created`
**Properties:**
- user_id
- time_to_first_swarm (from signup)
- swarm_type (template_based, custom)
- template_used (if applicable)
- agent_count

**Event:** `swarm_deployed`
**Properties:**
- user_id
- swarm_id
- deployment_success (boolean)
- deployment_time_ms
- agent_count
- cost_per_minute

**Event:** `template_explored`
**Properties:**
- template_category
- templates_viewed_count
- template_deployed (boolean)

**Event:** `visual_designer_used`
**Properties:**
- session_duration
- agents_added
- connections_made
- export_attempted (boolean)

### Conversion Stage

**Event:** `upgrade_initiated`
**Properties:**
- from_plan (free)
- to_plan (hobbyist, pro, team)
- trigger_point (usage_limit, feature_lock, manual)

**Event:** `payment_info_entered`
**Properties:**
- plan_selected
- billing_frequency (monthly, annual)
- coupon_applied (if any)

**Event:** `subscription_created`
**Properties:**
- user_id
- plan_tier
- mrr_value
- billing_frequency
- payment_method
- days_from_signup

**Event:** `subscription_failed`
**Properties:**
- error_reason
- payment_method
- plan_attempted
- retry_count

### Revenue Events

**Event:** `purchase_completed`
**Properties:**
- transaction_id
- revenue_usd
- plan_tier
- billing_frequency
- coupon_code
- ltv_estimate

**Event:** `upsell_completed`
**Properties:**
- previous_plan
- new_plan
- mrr_increase
- trigger (manual, usage_based, sales_assisted)

**Event:** `marketplace_purchase`
**Properties:**
- template_id
- template_category
- price_usd
- creator_id

### Retention Events

**Event:** `daily_active_user`
**Properties:**
- user_id
- swarms_active
- agent_hours_used
- features_accessed

**Event:** `weekly_active_user`
**Properties:**
- user_id
- days_active_this_week
- swarms_created_this_week
- engagement_score

**Event:** `subscription_renewed`
**Properties:**
- user_id
- plan_tier
- renewal_count
- churn_risk_score

**Event:** `churn_risk_detected`
**Properties:**
- user_id
- risk_score (0-100)
- risk_factors (low_usage, support_tickets, competitor_research)
- days_since_last_active

**Event:** `subscription_cancelled`
**Properties:**
- user_id
- plan_tier
- cancellation_reason
- subscriber_duration_days
- total_revenue_usd
- win_back_eligible (boolean)

### Advocacy Events

**Event:** `referral_sent`
**Properties:**
- referrer_user_id
- referral_method (link, email, social)
- referral_campaign

**Event:** `referral_converted`
**Properties:**
- referrer_user_id
- referred_user_id
- conversion_value_usd
- referrer_reward_usd

**Event:** `review_submitted`
**Properties:**
- platform (producthunt, g2, capterra)
- rating (1-5)
- review_text_length
- user_tenure_days

**Event:** `social_share`
**Properties:**
- platform (twitter, linkedin, facebook)
- content_type (achievement, creation, review)
- reach_estimate

---

## ATTRIBUTION MODEL

### Multi-Touch Attribution

**Model:** Time Decay with Custom Weighting

**Reasoning:** Give more credit to touchpoints closer to conversion, but don't ignore early awareness touches.

**Weighting:**
- First Touch: 20%
- Middle Touches: 30% (distributed)
- Last Touch: 50%

**Example:**
User journey: ProductHunt → Blog → Demo → Pricing → Signup → Activate

Attribution:
- ProductHunt: 20% of conversion value
- Blog: 10%
- Demo: 10%
- Pricing: 10%
- Signup: 25%
- Activate: 25%

### Attribution Windows

**Click-Through Attribution:** 30 days
- User has 30 days from clicking link to convert

**View-Through Attribution:** 7 days
- User has 7 days from viewing ad to convert (for paid ads only)

**Email Attribution:** 14 days
- Email campaigns get 14-day attribution window

### Custom Attribution Rules

**Rule 1: Direct Intent Override**
If user directly visits pricing page and converts within 24 hours, attribute 80% to last touch.

**Rule 2: ProductHunt Boost**
During launch week, ProductHunt gets +10% attribution weight for all conversions.

**Rule 3: Referral Priority**
Referral conversions attribute 70% to referrer, 30% to last touch.

---

## KPI DASHBOARD

### North Star Metric

**Active Swarms Deployed Per Week**

Target: 1,000 by Month 3, 10,000 by Month 12

Why: Best indicator of actual product value delivery and user engagement.

### Primary KPIs

**Acquisition (Week 1 Targets):**
- Website visitors: 10,000
- Unique visitors: 7,500
- Signup conversion rate: 10%
- Signups: 750

**Activation (Week 1 Targets):**
- First swarm created: 80% of signups
- Time to first swarm: <10 minutes (median)
- Successful deployments: 90%

**Revenue (Month 1 Targets):**
- MRR: $5,000
- Free → Paid conversion: 5%
- ARPU: $28
- LTV: $525
- CAC: $35

**Retention (Month 1 Targets):**
- Day 1 retention: 60%
- Day 7 retention: 40%
- Day 30 retention: 25%
- Monthly churn: <8%

**Engagement (Week 1 Targets):**
- DAU/MAU ratio: 30%
- Avg swarms per user: 3
- Avg agent-hours used: 40% of quota
- Support tickets per 100 users: <5

### Secondary KPIs

**Traffic Sources (Week 1):**
- ProductHunt: 4,000 visits (40%)
- Hacker News: 2,000 visits (20%)
- Reddit: 1,500 visits (15%)
- Twitter: 1,000 visits (10%)
- Direct: 1,500 visits (15%)

**Content Performance:**
- Blog post views: 5,000
- Demo video completions: 60%
- Documentation page views: 3,000

**Product Metrics:**
- Templates used: 200+ different templates
- Visual designer usage: 40% of users
- API calls: 100,000+
- Average swarm size: 150 agents

**Customer Acquisition:**
- Organic signups: 70%
- Paid signups: 20%
- Referral signups: 10%
- Blended CAC: $35

---

## A/B TESTING PLAN

### Homepage Tests

**Test 1: Hero CTA Text**
- **Variant A (Control):** "Start Free - No Credit Card"
- **Variant B:** "Deploy Your First Swarm in 60 Seconds"
- **Variant C:** "Try 1,000 AI Agents Free"
- **Metric:** Signup conversion rate
- **Duration:** 7 days
- **Traffic split:** 25/25/25/25

**Test 2: Value Proposition Order**
- **Variant A (Control):** Cost → Speed → Intelligence
- **Variant B:** Speed → Cost → Intelligence
- **Variant C:** Intelligence → Cost → Speed
- **Metric:** Time on page, scroll depth, signup rate
- **Duration:** 14 days
- **Traffic split:** 33/33/34

**Test 3: Social Proof Placement**
- **Variant A (Control):** Below hero
- **Variant B:** Within hero (testimonial quote)
- **Variant C:** Above hero (trust badges)
- **Metric:** Signup conversion rate
- **Duration:** 7 days
- **Traffic split:** 33/33/34

### Pricing Page Tests

**Test 4: Pricing Anchor**
- **Variant A (Control):** 3 tiers (Free, Pro, Enterprise)
- **Variant B:** 4 tiers (Free, Hobbyist, Pro, Enterprise)
- **Variant C:** 3 tiers with annual discount highlighted
- **Metric:** Plan selection rate, upgrade rate
- **Duration:** 14 days
- **Traffic split:** 33/33/34

**Test 5: Feature Comparison**
- **Variant A (Control):** Feature list per plan
- **Variant B:** Comparison table (check marks)
- **Variant C:** "Most popular" badge on Pro plan
- **Metric:** Pro plan selection rate
- **Duration:** 7 days
- **Traffic split:** 33/33/34

**Test 6: ROI Calculator**
- **Variant A (Control):** No calculator
- **Variant B:** Simple cost comparison calculator
- **Variant C:** Detailed ROI calculator with time savings
- **Metric:** Time on pricing page, conversion rate
- **Duration:** 14 days
- **Traffic split:** 33/33/34

### Onboarding Tests

**Test 7: Signup Flow**
- **Variant A (Control):** Email → Password → Confirm
- **Variant B:** Social auth only (Google, GitHub)
- **Variant C:** Email only (passwordless link)
- **Metric:** Signup completion rate
- **Duration:** 14 days
- **Traffic split:** 33/33/34

**Test 8: First Swarm Experience**
- **Variant A (Control):** Template selection
- **Variant B:** Guided tutorial
- **Variant C:** Interactive demo + template
- **Metric:** Time to first swarm, activation rate
- **Duration:** 14 days
- **Traffic split:** 33/33/34

**Test 9: Upgrade Prompt Timing**
- **Variant A (Control):** At 80% usage
- **Variant B:** After 5 successful swarms
- **Variant C:** 7 days after signup (proactive)
- **Metric:** Free → Paid conversion rate
- **Duration:** 30 days
- **Traffic split:** 33/33/34

### Email Tests

**Test 10: Welcome Email CTA**
- **Variant A (Control):** "Deploy Your First Swarm"
- **Variant B:** "Explore Templates"
- **Variant C:** "Watch Tutorial Video"
- **Metric:** Email open rate, CTR, activation rate
- **Duration:** 30 days
- **Traffic split:** 33/33/34

---

## LAUNCH DAY MONITORING

### Real-Time Dashboard

**Monitor every 15 minutes:**

**Traffic Metrics:**
- Current visitors (real-time)
- Traffic sources breakdown
- Geographic distribution
- Device breakdown (desktop/mobile)

**Conversion Metrics:**
- Signups (cumulative and rate)
- Activations (first swarm)
- Upgrade rate
- Revenue

**Technical Metrics:**
- Page load times
- API response times
- Error rates
- Deployment success rates

**Engagement Metrics:**
- ProductHunt ranking
- ProductHunt upvotes
- Hacker News points
- Reddit upvotes
- Social shares

**Support Metrics:**
- Support ticket volume
- Average response time
- Common issues

### Hourly Goals (Launch Day)

| Hour | Visitors | Signups | Activations | Revenue | PH Votes |
|------|----------|---------|-------------|---------|----------|
| 1 | 500 | 50 | 40 | $100 | 50 |
| 3 | 1,500 | 150 | 120 | $300 | 150 |
| 6 | 3,000 | 300 | 240 | $600 | 300 |
| 12 | 6,000 | 600 | 480 | $1,200 | 600 |
| 24 | 10,000 | 1,000 | 800 | $2,000 | 1,000 |

### Alert Thresholds

**Critical Alerts (Immediate Action):**
- Site down (>5% error rate)
- Conversion rate <5% (vs target 10%)
- Payment processing failures >10%
- API response time >2 seconds
- Signup completion rate <50%

**Warning Alerts (Monitor Closely):**
- Conversion rate <8%
- Bounce rate >60%
- Average session duration <2 minutes
- Activation rate <70%

**Opportunity Alerts:**
- Viral spike detected (traffic +500% in 1 hour)
- High-value user segment identified
- Unexpected geographic hotspot
- Competitor user influx

---

## TOOLS & INTEGRATIONS

### Analytics Stack

**Measurement:**
- Google Analytics 4 (web analytics)
- Mixpanel (product analytics)
- Segment (data pipeline)
- Hotjar (session recordings)

**Attribution:**
- Attribution.io (multi-touch attribution)
- Google Ads conversion tracking
- Facebook Pixel
- LinkedIn Insight Tag

**Monitoring:**
- Datadog (infrastructure monitoring)
- Sentry (error tracking)
- FullStory (session replay)
- LogRocket (product analytics + replay)

**Email:**
- SendGrid (transactional)
- Mailchimp (marketing campaigns)
- Customer.io (lifecycle emails)

**Support:**
- Intercom (live chat + help center)
- Zendesk (ticket system)
- Slack (internal alerts)

### Integration Map

```
User Action → Segment → [
    Google Analytics 4 (web analytics)
    Mixpanel (product analytics)
    Customer.io (email triggers)
    Intercom (support context)
    Slack (internal alerts)
    Data Warehouse (BigQuery)
]
```

### Data Pipeline

**Real-Time Events:**
Segment → Mixpanel (instant)
Segment → GA4 (instant)
Segment → Customer.io (instant)

**Batch Processing:**
Segment → BigQuery (hourly)
BigQuery → Looker (BI dashboards)
BigQuery → ML Models (daily)

### Custom Dashboards

**Launch Dashboard (Klipfolio):**
- Real-time traffic and conversions
- ProductHunt ranking
- Social media metrics
- Revenue and MRR

**Growth Dashboard (Mixpanel):**
- Funnel analysis
- Cohort retention
- Feature adoption
- User journeys

**Revenue Dashboard (ChartMogul):**
- MRR and ARR
- Churn analysis
- Upgrade/downgrade trends
- LTV:CAC ratio

**Product Dashboard (Amplitude):**
- Feature usage
- Activation metrics
- Engagement scores
- Power user analysis

---

## PRIVACY & COMPLIANCE

### GDPR Compliance

**Consent Management:**
- Cookie consent banner (OneTrust)
- Granular tracking preferences
- Easy opt-out mechanism
- Data deletion requests honored within 30 days

**Data Minimization:**
- Only collect necessary data
- Anonymize IP addresses
- No PII in URL parameters
- Regular data audits

### CCPA Compliance

**User Rights:**
- Right to know what data collected
- Right to deletion
- Right to opt-out of sale (N/A - we don't sell data)

**Disclosures:**
- Privacy policy prominently linked
- Clear data collection notice
- Third-party tracking disclosed

---

## REPORTING CADENCE

**Daily (During Launch Week):**
- Traffic, signups, activations
- Revenue and MRR
- Top acquisition sources
- Critical issues and resolution

**Weekly (Post-Launch):**
- Cohort retention analysis
- Funnel conversion rates
- A/B test results
- Content performance
- Support ticket analysis

**Monthly:**
- Full funnel metrics
- LTV:CAC analysis
- Churn analysis and prevention
- Feature adoption
- Competitive analysis

**Quarterly:**
- Strategic KPI review
- Market trends analysis
- Attribution model refinement
- Technology stack review

---

## SUCCESS CRITERIA

**Week 1:**
- 1,000+ signups
- 10% signup conversion rate
- 75% activation rate
- $5K MRR
- #1 Product of the Day on ProductHunt

**Month 1:**
- 5,000+ signups
- 250+ paying customers
- $15K MRR
- 3% free-to-paid conversion
- 80% Day-7 retention

**Month 3:**
- 15,000+ signups
- 1,000+ paying customers
- $50K MRR
- 5% free-to-paid conversion
- Top 3 in category

**Month 6:**
- 40,000+ signups
- 2,000+ paying customers
- $100K MRR
- Category leadership established
- Profitable CAC:LTV unit economics

---

**Document Owner:** Growth Team
**Last Updated:** 2025-10-14
**Next Review:** Launch + 7 days
**Version:** 1.0
