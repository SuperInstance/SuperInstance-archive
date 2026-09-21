# METRICS DASHBOARD - BUSINESS INTELLIGENCE FRAMEWORK

**Document Classification**: Business Intelligence & Analytics
**Version**: 1.0
**Date**: 2025-10-14
**Purpose**: Track, measure, and optimize business performance

---

## OVERVIEW

This document defines the metrics tracking framework for the Swarm Intelligence Platform, covering acquisition, activation, retention, revenue, and referral (AARRR framework).

**Tools Stack**:
- **Analytics**: Mixpanel (product analytics)
- **Business Intelligence**: Metabase or Tableau
- **Data Warehouse**: Snowflake or BigQuery
- **Real-time**: Redis + custom dashboard
- **Reporting**: Automated weekly/monthly reports

---

## NORTH STAR METRIC

### Active Swarms Created Per Week

**Definition**: Number of swarms created and executed by active users each week

**Why This Metric**:
- Measures real product value delivery
- Leading indicator of retention and engagement
- Correlates directly with revenue potential
- Reflects product-market fit

**Targets**:
- Month 3: 500 swarms/week
- Month 6: 2,000 swarms/week
- Month 12: 10,000 swarms/week
- Year 2: 50,000 swarms/week

**Dashboard Visualization**:
- Line chart (weekly trend)
- Breakdown by user tier (Free, Hobbyist, Pro, Team, Enterprise)
- Breakdown by use case (testing, creative, development, etc.)
- Cohort analysis (retention by signup month)

---

## ACQUISITION METRICS

### 1. Website Traffic

**Metrics**:
- **Unique visitors per month**
- **Page views**
- **Traffic sources** (organic, direct, referral, paid, social)
- **Bounce rate**
- **Time on site**

**Targets**:
- Month 1: 5,000 visitors
- Month 3: 25,000 visitors
- Month 6: 75,000 visitors
- Month 12: 250,000 visitors

**Data Sources**: Google Analytics, Cloudflare Analytics

**Dashboard**:
```
┌─────────────────────────────────────┐
│  Traffic Overview - Last 30 Days    │
├─────────────────────────────────────┤
│  Total Visitors:     125,340  (+18%)│
│  Organic:            65,230   (52%) │
│  Direct:             30,150   (24%) │
│  Referral:           18,960   (15%) │
│  Social:              8,000   (6%)  │
│  Paid:                3,000   (3%)  │
├─────────────────────────────────────┤
│  [Line chart: Daily traffic]         │
│  [Funnel: Visitor → Signup]         │
└─────────────────────────────────────┘
```

---

### 2. Signup Conversion

**Metrics**:
- **Signup rate** (% of visitors who sign up)
- **Time to signup** (from first visit)
- **Signup drop-off** (form field analysis)
- **Source quality** (signup rate by channel)

**Targets**:
- Month 1: 8% conversion
- Month 6: 15% conversion
- Month 12: 25% conversion

**Optimization**:
- A/B test signup forms
- Reduce friction (social login)
- Clear value proposition
- Trust signals (testimonials, logos)

---

### 3. Customer Acquisition Cost (CAC)

**Formula**: Total Marketing + Sales Spend / New Customers Acquired

**Breakdown by Channel**:
- **Organic** (content, SEO): $5-10 CAC
- **Social** (community, referrals): $15-20 CAC
- **Paid** (ads): $40-60 CAC
- **Sales** (enterprise): $10,000-15,000 CAC

**Targets**:
- Blended CAC: $35 (Year 1)
- Maintain CAC < LTV/3 (healthy ratio)

**Dashboard**:
```
┌─────────────────────────────────────┐
│  CAC by Channel - Q2 2025          │
├─────────────────────────────────────┤
│  Organic:      $8   (2,500 users)   │
│  Social:       $18  (1,200 users)   │
│  Paid:         $52  (800 users)     │
│  Enterprise:   $12K (5 customers)   │
├─────────────────────────────────────┤
│  Blended CAC:  $35                  │
│  [Bar chart: CAC trend over time]   │
└─────────────────────────────────────┘
```

---

## ACTIVATION METRICS

### 1. Time to First Swarm

**Definition**: Minutes from signup to first swarm execution

**Target**: <10 minutes (90th percentile)

**Why It Matters**: Users who create their first swarm quickly are 5x more likely to convert to paid

**Optimization**:
- Onboarding tutorial
- Pre-built templates
- Example prompts
- Quick-start wizard

---

### 2. Activation Rate

**Definition**: % of signups who complete key activation events

**Key Activation Events**:
1. Create first swarm (80% target)
2. Execute swarm successfully (70% target)
3. Use swarm output (60% target)
4. Create second swarm (50% target)
5. Invite team member (20% target for Team tier)

**Dashboard**:
```
┌─────────────────────────────────────┐
│  Activation Funnel - Last 30 Days   │
├─────────────────────────────────────┤
│  Signups:              5,000  (100%)│
│  ↓                                   │
│  First swarm:          4,100  (82%) │
│  ↓                                   │
│  Swarm success:        3,600  (72%) │
│  ↓                                   │
│  Use output:           3,000  (60%) │
│  ↓                                   │
│  Second swarm:         2,400  (48%) │
│  ↓                                   │
│  3+ swarms (power user): 1,800 (36%)│
└─────────────────────────────────────┘
```

---

### 3. "Aha Moment" Tracking

**Definition**: The moment users realize the product's value

**Identified "Aha Moments"**:
1. First swarm completes in <30 seconds (speed wow)
2. Swarm finds a bug they missed (quality wow)
3. Generate 100 variations in 1 minute (scale wow)
4. See swarm self-heal after agent failure (reliability wow)

**Measurement**: Survey users + correlation analysis

---

## RETENTION METRICS

### 1. Retention Curves

**Cohort Retention**:
- Day 1, 7, 14, 30, 60, 90, 180, 365
- Tracked by signup month
- Breakdown by user tier

**Targets**:
- Day 7: 60%
- Day 30: 45%
- Month 3: 35%
- Month 12: 25% (annual retention: 90%)

**Dashboard**:
```
┌─────────────────────────────────────┐
│  Retention Curves by Cohort         │
├─────────────────────────────────────┤
│  [Line chart showing:]               │
│  Jan cohort: 60% → 45% → 35%        │
│  Feb cohort: 62% → 48% → 38%        │
│  Mar cohort: 65% → 52% → ?          │
│                                      │
│  Retention improving! (+5% MoM)     │
└─────────────────────────────────────┘
```

---

### 2. Churn Analysis

**Monthly Churn Rate**: % of users who cancel or downgrade

**Target**: <5% monthly churn (<45% annual)

**Churn Breakdown**:
- **Voluntary**: User cancels (80% of churn)
- **Involuntary**: Payment failure (20% of churn)

**Churn Reasons** (exit survey):
1. Too expensive (price sensitivity)
2. Not using enough (activation failure)
3. Missing features (product gaps)
4. Better alternative (competitive)
5. Project ended (expected churn)

**Churn Prevention**:
- Usage alerts (80% of limit → upgrade prompt)
- Win-back campaigns (30 days after cancel)
- Downgrade option (don't lose completely)
- Customer success outreach (high-value accounts)

---

### 3. Engagement Metrics

**Daily Active Users (DAU) / Monthly Active Users (MAU)**

**Target**: 35% DAU/MAU ratio

**Definition of "Active"**:
- Logged in + executed at least one swarm

**Power User Metrics**:
- % users creating 5+ swarms/week
- % users using 3+ features
- % users with 50%+ limit usage
- % users who refer others

---

### 4. Net Revenue Retention (NRR)

**Formula**: (Starting MRR + Expansion - Churn - Downgrade) / Starting MRR

**Target**: 120% NRR (20% expansion annually)

**Expansion Sources**:
- Tier upgrades (Hobbyist → Pro)
- Seat expansion (Team tier)
- Usage overages
- Add-on purchases (marketplace templates)

**Best-in-Class**: 120%+ NRR indicates product-market fit

---

## REVENUE METRICS

### 1. Monthly Recurring Revenue (MRR)

**Components**:
- **New MRR**: From new customers
- **Expansion MRR**: Upgrades, upsells
- **Contraction MRR**: Downgrades
- **Churn MRR**: Cancellations

**Net New MRR** = New + Expansion - Contraction - Churn

**Targets**:
- Month 3: $5K MRR
- Month 6: $15K MRR
- Month 12: $100K MRR
- Month 18: $500K MRR

**Growth Rate**: 15-20% MoM (Year 1)

**Dashboard**:
```
┌─────────────────────────────────────┐
│  MRR Breakdown - September 2025     │
├─────────────────────────────────────┤
│  Starting MRR:       $45,000        │
│  + New MRR:          $12,000        │
│  + Expansion MRR:    $3,500         │
│  - Contraction MRR:  -$1,200        │
│  - Churn MRR:        -$2,300        │
│  = Ending MRR:       $57,000 (+27%) │
├─────────────────────────────────────┤
│  [Waterfall chart showing flow]     │
│  [Line chart: MRR trend]            │
└─────────────────────────────────────┘
```

---

### 2. Annual Recurring Revenue (ARR)

**Formula**: MRR × 12 (approximation)

**Accurate ARR**: Sum of all annual contracts + (monthly × 12)

**Targets**:
- Year 1: $1.8M ARR
- Year 2: $12M ARR
- Year 3: $57M ARR
- Year 5: $100M+ ARR

---

### 3. Average Revenue Per User (ARPU)

**Formula**: Total MRR / Total Paying Customers

**Breakdown by Tier**:
- Hobbyist: $9
- Pro: $49
- Team: $597 avg (3 seats)
- Enterprise: $4,167 avg ($50K/year)

**Blended ARPU Target**: $28 (Year 1)

**Growth Strategy**: Increase via upgrades and seat expansion

---

### 4. Customer Lifetime Value (LTV)

**Formula**: ARPU × Gross Margin × (1 / Monthly Churn Rate)

**Example Calculation**:
- ARPU: $28
- Gross Margin: 87%
- Monthly Churn: 5%
- **LTV** = $28 × 0.87 × (1/0.05) = **$487**

**Targets by Tier**:
- Hobbyist: $108 (12-month avg lifetime)
- Pro: $882 (18-month avg lifetime)
- Team: $7,164 (36-month avg lifetime)
- Enterprise: $360,000 (60-month avg lifetime)

**Blended LTV**: $525

---

### 5. LTV:CAC Ratio

**Formula**: Lifetime Value / Customer Acquisition Cost

**Targets**:
- Month 6: 8:1 (early, inefficient)
- Month 12: 15:1 (healthy, scaling)
- Year 2: 20:1 (mature, efficient)

**Benchmarks**:
- <1:1 → Unsustainable
- 1-3:1 → Be cautious, watch closely
- 3-5:1 → Healthy and scalable
- >5:1 → Very healthy, can invest more in growth

**Our Target**: 15:1 (excellent SaaS ratio)

---

### 6. Payback Period

**Definition**: Months to recover CAC

**Formula**: CAC / (ARPU × Gross Margin)

**Example**:
- CAC: $35
- ARPU: $28
- Gross Margin: 87%
- **Payback** = $35 / ($28 × 0.87) = **1.4 months**

**Target**: <6 months (ours is 1.4 months - exceptional)

---

### 7. Revenue by Channel

**Breakdown**:
- **Subscriptions**: 80%
- **Marketplace**: 15%
- **Services**: 5%

**Monthly Tracking**:
```
┌─────────────────────────────────────┐
│  Revenue by Channel - October 2025  │
├─────────────────────────────────────┤
│  Subscriptions:   $48,000 (80%)     │
│    ├─ Free:       $0                │
│    ├─ Hobbyist:   $8,100            │
│    ├─ Pro:        $24,500           │
│    ├─ Team:       $11,400           │
│    └─ Enterprise: $4,000            │
│                                      │
│  Marketplace:     $9,000 (15%)      │
│  Services:        $3,000 (5%)       │
│                                      │
│  Total MRR:       $60,000           │
└─────────────────────────────────────┘
```

---

## REFERRAL & GROWTH METRICS

### 1. Viral Coefficient (K-Factor)

**Formula**: (Invites Sent × Conversion Rate) per User

**Target**: K > 1.0 (exponential viral growth)

**Our Target**: 1.3x (healthy viral growth)

**Example**:
- Average user sends 4 invites
- 30% conversion rate
- K = 4 × 0.30 = **1.2** (viral growth!)

**Tracking**:
- Invites sent per user
- Invite acceptance rate
- Referral signup to activation rate
- Referral source attribution

---

### 2. Net Promoter Score (NPS)

**Question**: "How likely are you to recommend us to a friend?" (0-10)

**Calculation**:
- Promoters (9-10): % of these
- Passives (7-8): Ignore
- Detractors (0-6): % of these
- **NPS** = % Promoters - % Detractors

**Targets**:
- Month 6: NPS 50+
- Month 12: NPS 60+
- Year 2: NPS 70+ (world-class)

**Action Items**:
- Follow up with detractors (understand issues)
- Leverage promoters (testimonials, case studies)
- Close the loop on feedback

---

### 3. Referral Program Performance

**Metrics**:
- Referrals made
- Referral conversions
- Referral revenue attribution
- Reward redemption rate

**Our Program**: 3 months free for referrer and referred

**Target**: 15% of users refer at least 1 person

---

## OPERATIONAL METRICS

### 1. Infrastructure Costs

**Tracking**:
- Cost per user (total infra cost / total users)
- Cost per agent-hour
- Cost by instance type
- Utilization rate (% of provisioned capacity used)

**Targets**:
- Cost per user: <$0.50/month (free tier)
- Cost per user: <$2/month (paid tiers)
- Gross margin: 87%+

**Dashboard**:
```
┌─────────────────────────────────────┐
│  Infrastructure Costs - October     │
├─────────────────────────────────────┤
│  Total Users:        50,000         │
│  Paid Users:         3,000          │
│                                      │
│  AWS Costs:          $8,500         │
│  Cost per User:      $0.17          │
│  Cost per Paid User: $2.83          │
│                                      │
│  Revenue:            $60,000        │
│  Infra Cost:         $8,500         │
│  Gross Margin:       86%            │
└─────────────────────────────────────┘
```

---

### 2. System Performance

**Metrics**:
- Uptime (target: 99.9%)
- API response time (target: <100ms p95)
- Swarm coordination latency (target: <100ms)
- Error rate (target: <0.1%)
- Agent success rate (target: >95%)

**Alerting**: PagerDuty for critical issues

---

### 3. Support Metrics

**Response Time**:
- Critical: <1 hour (Enterprise)
- High: <4 hours (Team/Pro)
- Medium: <24 hours (Hobbyist)
- Low: <48 hours

**Customer Satisfaction**: Target 4.5/5 stars

**Ticket Volume**: Track by issue type, identify product gaps

---

## COHORT ANALYSIS

### Cohort Retention Table

**Structure**:
```
Cohort  | Users | M0   | M1   | M2   | M3   | M6   | M12
--------|-------|------|------|------|------|------|------
Jan 25  | 500   | 100% | 65%  | 52%  | 45%  | 35%  | 28%
Feb 25  | 800   | 100% | 68%  | 55%  | 48%  | 38%  | -
Mar 25  | 1200  | 100% | 70%  | 58%  | 50%  | -    | -
Apr 25  | 1800  | 100% | 72%  | 60%  | -    | -    | -
```

**Insights**:
- Cohorts improving over time (product-market fit)
- Month 3 retention most predictive of LTV
- Seasonal patterns (Q4 higher retention?)

---

### Revenue Cohort Analysis

**Track**: MRR contribution by signup cohort over time

**Insight**: Which cohorts are most valuable? Which expand vs. churn?

---

## FUNNEL ANALYSIS

### Signup Funnel

```
Homepage visit (100%)
  ↓
Features page (40%)
  ↓
Pricing page (25%)
  ↓
Signup page (18%)
  ↓
Account created (15%)
```

**Optimization**: Improve each step by 5% → 2x signups

---

### Free-to-Paid Conversion Funnel

```
Free user (100%)
  ↓
Uses 50% of limit (30%)
  ↓
Uses 80% of limit (15%)
  ↓
Sees upgrade prompt (12%)
  ↓
Clicks upgrade (8%)
  ↓
Converts to paid (5%)
```

**Target**: 5% → 8% conversion (60% improvement)

---

## DASHBOARD IMPLEMENTATIONS

### Executive Dashboard (Weekly Review)

**Top Metrics**:
1. MRR and growth rate
2. New users and conversion rate
3. Churn rate
4. LTV:CAC ratio
5. North Star Metric (swarms/week)

**Format**: 1-page PDF, emailed Monday mornings

---

### Product Dashboard (Daily Monitoring)

**Metrics**:
1. DAU/MAU
2. Feature adoption rates
3. Error rates and system health
4. Activation funnel
5. User feedback highlights

**Tool**: Mixpanel + custom internal dashboard

---

### Sales Dashboard (Real-Time)

**Metrics**:
1. Pipeline value
2. Deals in progress
3. Win rate
4. Average deal size
5. Sales cycle length

**Tool**: HubSpot or Salesforce

---

### Financial Dashboard (Monthly Close)

**Metrics**:
1. Revenue (breakdown by tier, channel)
2. Costs (COGS, OpEx breakdown)
3. Burn rate and runway
4. Cash balance
5. Budget vs. actual

**Tool**: QuickBooks + custom reporting

---

## AUTOMATION & ALERTS

### Automated Alerts

**Critical Alerts** (immediate):
- System downtime >5 minutes
- Error rate >1%
- Payment processing failures >10%

**Important Alerts** (same day):
- Churn rate spike (>10% week-over-week)
- CAC increase (>20% month-over-month)
- Negative MRR growth

**Info Alerts** (weekly digest):
- MRR milestones achieved
- User milestones (10K, 50K, 100K)
- Feature adoption changes

---

### Automated Reports

**Daily**:
- Revenue snapshot (Slack notification)
- New user signups
- System health summary

**Weekly**:
- Executive dashboard (PDF email)
- Team performance summaries
- User feedback highlights

**Monthly**:
- Board report (full business review)
- Financial statements
- Cohort analysis update

**Quarterly**:
- Investor update
- Strategic review
- OKR progress

---

## DATA INFRASTRUCTURE

### Data Pipeline

```
Application Events
  ↓
Segment (event tracking)
  ↓
├─> Mixpanel (product analytics)
├─> Snowflake (data warehouse)
├─> Customer.io (marketing automation)
└─> Metabase (business intelligence)
```

### Key Events to Track

**User Actions**:
- `signup`, `login`, `logout`
- `swarm_created`, `swarm_executed`, `swarm_failed`
- `template_used`, `template_created`
- `upgrade_clicked`, `subscription_started`
- `invite_sent`, `team_member_added`

**System Events**:
- `agent_spawned`, `agent_completed`, `agent_failed`
- `coordination_success`, `coordination_failure`
- `pheromone_trail_created`, `pheromone_trail_followed`

**Revenue Events**:
- `subscription_created`, `subscription_upgraded`, `subscription_canceled`
- `payment_succeeded`, `payment_failed`
- `invoice_generated`, `invoice_paid`

---

## EXPERIMENTATION FRAMEWORK

### A/B Testing

**Test Types**:
1. **Pricing tests**: $9 vs. $12 for Hobbyist tier
2. **Feature tests**: New onboarding flow vs. old
3. **Copy tests**: Landing page headlines
4. **UI tests**: Upgrade button placement

**Statistical Significance**: 95% confidence, 80% power

**Duration**: Minimum 2 weeks or 1,000 conversions

**Tool**: Optimizely or internal A/B framework

---

## CONCLUSION

This metrics framework provides:

1. **Visibility**: Real-time tracking of business health
2. **Accountability**: Clear targets and ownership
3. **Optimization**: Data-driven decision making
4. **Scalability**: Metrics that grow with the business

**Next Steps**:
1. Implement event tracking (Segment integration)
2. Build executive dashboard (Week 1)
3. Set up automated alerts (Week 2)
4. Create weekly reporting cadence (Week 3)
5. Establish experimentation framework (Month 2)

---

**Document Owner**: Head of Analytics & Business Intelligence
**Review Frequency**: Quarterly (update targets and definitions)
**Last Updated**: 2025-10-14
**Status**: Ready for Implementation
