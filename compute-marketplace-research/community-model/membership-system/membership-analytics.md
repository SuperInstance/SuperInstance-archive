# Membership Analytics & Dashboards

**Date:** October 14, 2025
**Objective:** Design comprehensive analytics framework for membership tiers

---

## Executive Summary

Analytics framework tracking key metrics across membership tiers: MRR, ARR, churn, LTV, CAC, cohort analysis. Based on SaaS best practices and marketplace-specific KPIs.

**Key Metrics:**
- Monthly Recurring Revenue (MRR) by tier
- Churn rate (target: <5% monthly)
- LTV:CAC ratio (target: >3:1)
- Tier conversion rates (Free→Basic: 4%, Basic→Premium: 12%)
- Net Revenue Retention (NRR target: >100%)

---

## 1. Core SaaS Metrics

### MRR (Monthly Recurring Revenue)

```typescript
interface MRRMetrics {
  totalMRR: number;
  byTier: {
    basic: number;     // $8 × basic_users
    premium: number;   // $30 × premium_users
  };
  
  // MRR Movement
  newMRR: number;      // New subscriptions
  expansionMRR: number; // Upgrades (Basic→Premium)
  contractionMRR: number; // Downgrades
  churnedMRR: number;  // Cancellations
  
  // Net New MRR
  netNewMRR: number;   // new + expansion - contraction - churn
}

function calculateMRR(month: Date): MRRMetrics {
  const basic Users = countActiveUsers('basic', month);
  const premiumUsers = countActiveUsers('premium', month);
  
  return {
    totalMRR: (basicUsers * 8) + (premiumUsers * 30),
    byTier: {
      basic: basicUsers * 8,
      premium: premiumUsers * 30
    },
    newMRR: countNewSubscriptions(month) * avgTierPrice,
    expansionMRR: countUpgrades(month) * (30 - 8), // Basic→Premium
    contractionMRR: countDowngrades(month) * (30 - 8),
    churnedMRR: countCancellations(month) * avgTierPrice,
    netNewMRR: calculateNetNew(month)
  };
}
```

### ARR (Annual Recurring Revenue)

```
ARR = MRR × 12

Target Growth:
- Month 6: $50K MRR → $600K ARR
- Month 12: $150K MRR → $1.8M ARR  
- Month 18: $300K MRR → $3.6M ARR
- Month 24: $500K MRR → $6M ARR
```

### Churn Rate

```typescript
interface ChurnMetrics {
  customerChurn: number;  // % of users who cancel
  revenueChurn: number;   // % of MRR lost
  
  byTier: {
    basic: number;
    premium: number;
  };
  
  // Voluntary vs Involuntary
  voluntary: number;      // User cancels
  involuntary: number;    // Payment fails
}

function calculateChurn(month: Date): ChurnMetrics {
  const startUsers = countUsersAtStart(month);
  const canceledUsers = countCancellations(month);
  
  return {
    customerChurn: (canceledUsers / startUsers) * 100,
    revenueChurn: (churnedMRR / startMRR) * 100,
    byTier: {
      basic: (basicCancellations / basicUsers) * 100,
      premium: (premiumCancellations / premiumUsers) * 100
    },
    voluntary: voluntaryCancellations / canceledUsers,
    involuntary: involuntaryCancellations / canceledUsers
  };
}

// Target: <5% monthly churn (60% annual retention)
// Excellent: <3% monthly churn (70%+ annual retention)
```

---

## 2. Unit Economics

### LTV (Lifetime Value)

```typescript
function calculateLTV(tier: 'basic' | 'premium'): number {
  const avgMonthlyRevenue = tier === 'basic' ? 8 : 30;
  const avgCustomerLifespan = 1 / monthlyChurnRate; // months
  const grossMargin = 0.60; // 60% after costs
  
  return avgMonthlyRevenue * avgCustomerLifespan * grossMargin;
}

// Example:
// Basic tier: $8/mo × 20 months × 0.60 = $96 LTV
// Premium tier: $30/mo × 30 months × 0.60 = $540 LTV
```

### CAC (Customer Acquisition Cost)

```typescript
function calculateCAC(month: Date): {
  overall: number;
  byChannel: Record<string, number>;
  paybackPeriod: number;
} {
  const marketingSpend = getTotalMarketingSpend(month);
  const salesSpend = getSalesTeamCost(month);
  const newCustomers = countNewPaidUsers(month);
  
  const cac = (marketingSpend + salesSpend) / newCustomers;
  
  return {
    overall: cac,
    byChannel: {
      organic: calculateChannelCAC('organic'),
      paidAds: calculateChannelCAC('paid_ads'),
      referral: calculateChannelCAC('referral'),
      content: calculateChannelCAC('content')
    },
    paybackPeriod: cac / avgMonthlyRevenue // months to payback
  };
}

// Target: LTV:CAC > 3:1
// Good: LTV:CAC > 4:1
// Excellent: LTV:CAC > 5:1
```

### NRR (Net Revenue Retention)

```typescript
function calculateNRR(cohortMonth: Date, currentMonth: Date): number {
  const cohortStartMRR = getMRRForCohort(cohortMonth, cohortMonth);
  const cohortCurrentMRR = getMRRForCohort(cohortMonth, currentMonth);
  
  // Includes expansion (upgrades) but excludes new customers
  return (cohortCurrentMRR / cohortStartMRR) * 100;
}

// Target: NRR > 100% (expansion offsets churn)
// Good: NRR > 110%
// Excellent: NRR > 120% (indicates strong upsell)
```

---

## 3. Cohort Analysis

### Monthly Cohorts

```
Cohort: Users who joined in January 2025

Month 0 (Jan): 100 users, $800 MRR
Month 1 (Feb): 95 users (5% churn), $760 MRR
Month 2 (Mar): 92 users (3% churn), $850 MRR (upgrades!)
Month 3 (Apr): 88 users (4% churn), $920 MRR (more upgrades)
...
Month 12 (Dec): 70 users (30% annual churn), $1,200 MRR (71% NRR!)

Key insight: Despite churn, MRR grows due to upgrades (Basic→Premium)
```

### Cohort Retention Table

```
┌──────────┬────────────────────────────────────────────────┐
│  Cohort  │  M0   M1   M2   M3   M6   M12  M18  M24      │
├──────────┼────────────────────────────────────────────────┤
│ Jan 2025 │ 100%  95%  92%  88%  78%  70%  65%  62%      │
│ Feb 2025 │ 100%  96%  93%  90%  80%  72%  --   --       │
│ Mar 2025 │ 100%  94%  91%  87%  79%  --   --   --       │
│ Apr 2025 │ 100%  95%  92%  89%  --   --   --   --       │
│ May 2025 │ 100%  96%  93%  --   --   --   --   --       │
│ Jun 2025 │ 100%  95%  --   --   --   --   --   --       │
└──────────┴────────────────────────────────────────────────┘

Target: 70% retention at M12 (equivalent to 5% monthly churn)
```

---

## 4. Conversion Funnels

### Free → Paid Conversion

```
Step 1: Free tier signup
  ↓ 100 users
Step 2: Active usage (>1 compute job)
  ↓ 80 users (80% activation)
Step 3: Reach $40 monthly spend (Basic trigger)
  ↓ 30 users (38% reach threshold)
Step 4: See upgrade notification
  ↓ 25 users (83% see it)
Step 5: Click "Learn More"
  ↓ 15 users (60% click)
Step 6: Start checkout
  ↓ 8 users (53% start)
Step 7: Complete purchase (Basic)
  ↓ 6 users (75% complete)

Overall conversion: 6%
Bottleneck: Step 3 (only 38% reach $40 threshold)

Optimization: Target AI researchers with higher usage patterns
```

### Basic → Premium Upgrade

```
Step 1: Basic tier user
  ↓ 100 users
Step 2: Reach $200 monthly spend (Premium trigger)
  ↓ 25 users (25% are high-usage)
Step 3: See Premium suggestion
  ↓ 25 users (100% see it)
Step 4: View savings calculator
  ↓ 18 users (72% engage)
Step 5: Start upgrade
  ↓ 15 users (83% convert!)
Step 6: Complete upgrade
  ↓ 15 users (100% complete)

Overall upgrade rate: 15% of Basic users
High intent: Once users see savings, 83% upgrade
```

---

## 5. Analytics Dashboard Design

### Executive Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Membership Overview - October 2025                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MRR: $485,000  ↑ 12% MoM        ARR: $5.82M               │
│  Active Users: 18,200  ↑ 8% MoM                            │
│                                                              │
│  ┌──────────────┬──────────────┬──────────────┐           │
│  │ FREE         │ BASIC        │ PREMIUM      │           │
│  │ 15,000 users │ 2,800 users  │ 400 users    │           │
│  │ 82.4%        │ 15.4%        │ 2.2%         │           │
│  │ $0 MRR       │ $22,400 MRR  │ $12,000 MRR  │           │
│  └──────────────┴──────────────┴──────────────┘           │
│                                                              │
│  Key Metrics:                                               │
│  • Churn rate: 4.2%  ✓ (target: <5%)                      │
│  • LTV:CAC: 4.1:1  ✓ (target: >3:1)                       │
│  • NRR: 112%  ✓ (target: >100%)                           │
│  • Free→Paid: 4.5%  ✓ (target: 4%)                        │
│  • Basic→Premium: 14.3%  ✓ (target: 12%)                  │
│                                                              │
│  [View Detailed Reports] [Export Data] [Set Alerts]        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Revenue Breakdown

```
┌─────────────────────────────────────────────────────────────┐
│  Revenue Sources - October 2025                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Total Revenue: $1,235,000                                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │  Membership Fees: $485,000 (39%)                    │   │
│  │  ■■■■■■■■■■■■■■■■■■                              │   │
│  │                                                      │   │
│  │  Platform Fees: $650,000 (53%)                      │   │
│  │  ■■■■■■■■■■■■■■■■■■■■■■■■■                      │   │
│  │                                                      │   │
│  │  Withdrawal Fees: $100,000 (8%)                     │   │
│  │  ■■■■                                                │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  YoY Growth: +145%                                          │
│  MoM Growth: +12%                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Tier Performance Comparison

```
┌─────────────────────────────────────────────────────────────┐
│  Tier Performance Metrics                                    │
├──────────┬─────────┬─────────┬─────────┬───────────────────┤
│ Metric   │  FREE   │  BASIC  │ PREMIUM │ Platform Avg      │
├──────────┼─────────┼─────────┼─────────┼───────────────────┤
│ Users    │ 15,000  │ 2,800   │ 400     │ 18,200            │
│ MRR      │ $0      │ $22.4K  │ $12K    │ $485K total       │
│ ARPU     │ $0      │ $8      │ $30     │ $26.65            │
│ LTV      │ $0      │ $96     │ $540    │ $156              │
│ Churn    │ 8%      │ 4%      │ 2%      │ 4.2% weighted     │
│ Avg Spend│ $15/mo  │ $85/mo  │ $650/mo │ $125/mo           │
│ CAC      │ $20     │ $35     │ $120    │ $42 blended       │
│ LTV:CAC  │ N/A     │ 2.7:1   │ 4.5:1   │ 3.7:1             │
└──────────┴─────────┴─────────┴─────────┴───────────────────┘

Insights:
• Premium users have lowest churn (2%) - high satisfaction
• Premium LTV:CAC (4.5:1) exceeds target (3:1)
• Basic tier has low LTV:CAC (2.7:1) - needs improvement
• Free tier drives volume but needs better conversion
```

---

## 6. Alerts & Monitoring

### Automated Alerts

```typescript
interface Alert {
  metric: string;
  threshold: number;
  current: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  action: string;
}

const ALERT_RULES = [
  {
    metric: 'monthly_churn',
    condition: 'churn > 6%',
    severity: 'high',
    action: 'Investigate churn reasons, launch retention campaign'
  },
  {
    metric: 'ltv_cac_ratio',
    condition: 'LTV:CAC < 3:1',
    severity: 'medium',
    action: 'Reduce CAC or improve retention to increase LTV'
  },
  {
    metric: 'conversion_rate',
    condition: 'Free→Basic < 3%',
    severity: 'medium',
    action: 'Review upgrade messaging, A/B test improvements'
  },
  {
    metric: 'payment_failures',
    condition: 'failed_payments > 5%',
    severity: 'critical',
    action: 'Email users to update payment methods immediately'
  },
  {
    metric: 'nrr',
    condition: 'NRR < 100%',
    severity: 'high',
    action: 'Focus on upsells, reduce downgrades'
  }
];
```

---

## 7. Key Recommendations

### Metrics to Track (Priority Order)

**Critical (Daily):**
1. MRR / ARR
2. Churn rate
3. New subscriptions
4. Payment failures

**Important (Weekly):**
5. Conversion rates (Free→Basic, Basic→Premium)
6. LTV:CAC ratio
7. NRR
8. Cohort retention

**Strategic (Monthly):**
9. ARPU by tier
10. Revenue mix (membership vs platform fees)
11. Geographic distribution
12. Tier distribution trends

### Dashboard Tools

**Recommended Stack:**
- **Chargebee/Paddle:** Subscription management + analytics
- **Baremetrics:** SaaS metrics specialized
- **Mixpanel/Amplitude:** User behavior analytics
- **Metabase/Redash:** Custom SQL dashboards
- **Google Sheets:** Executive summaries

---

## Conclusion

Comprehensive analytics framework tracking:
- **Financial health:** MRR, ARR, churn, NRR
- **Unit economics:** LTV, CAC, payback period
- **User behavior:** Conversion funnels, cohort retention
- **Tier performance:** ARPU, churn, LTV by tier
- **Growth trends:** MoM, YoY, cohort analysis

This enables data-driven decisions on pricing, features, and growth strategies.
