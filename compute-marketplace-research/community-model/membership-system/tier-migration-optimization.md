# Tier Migration & Upgrade Optimization

**Date:** October 14, 2025
**Objective:** Design intelligent tier migration system with auto-upgrade suggestions

---

## Executive Summary

Tier migration system that automatically suggests upgrades when cost-effective, prevents gaming through lock-in periods, and uses behavioral economics to drive conversions. Based on research of Netflix, credit card tiers, and SaaS subscription models.

**Key Features:**
- Auto-suggest upgrades at breakeven points ($40 for Basic, $200 for Premium)
- Immediate upgrades, end-of-cycle downgrades (prevent gaming)
- 30-day minimum tier duration (lock-in prevents constant switching)
- Loss aversion messaging for downgrades (warn about locked Compute Capital)

---

## 1. Upgrade Triggers & Timing

### Automatic Upgrade Suggestions

```typescript
function evaluateUpgradeOpportunity(user: User): UpgradeSuggestion | null {
  const monthlySpend = user.monthlySpendToDate;
  const projectedSpend = projectMonthEndSpend(user);

  // Free → Basic suggestion
  if (user.tier === 'free' && projectedSpend >= 40) {
    const monthlySavings = calculateSavings('free', 'basic', projectedSpend);

    if (monthlySavings > 0) {
      return {
        currentTier: 'free',
        suggestedTier: 'basic',
        trigger: 'usage_threshold',
        monthlySavings,
        annualSavings: monthlySavings * 12,
        message: `You're spending ~$${projectedSpend}/month. Upgrade to Basic and save $${monthlySavings}/month + unlock cash withdrawals!`,
        notificationTiming: 'after_2_consecutive_months'
      };
    }
  }

  // Basic → Premium suggestion
  if (user.tier === 'basic' && projectedSpend >= 200) {
    const monthlySavings = calculateSavings('basic', 'premium', projectedSpend);

    if (monthlySavings > 50) { // Significant savings threshold
      return {
        currentTier: 'basic',
        suggestedTier: 'premium',
        trigger: 'high_usage',
        monthlySavings,
        annualSavings: monthlySavings * 12,
        message: `Heavy users like you save $${monthlySavings}/month with Premium (0.1% fees after $200). That's $${(monthlySavings * 12).toFixed(0)}/year!`,
        notificationTiming: 'after_1_month'
      };
    }
  }

  return null;
}
```

### Notification Schedule

**Conservative approach (avoid spam):**

1. **First notification:** After 2 consecutive months of qualifying spend
2. **Second reminder:** After 3 months if still qualifying
3. **Final nudge:** After 6 months
4. **Then:** Dashboard banner only (no active notifications)

**Channels:**
- Email (high priority, opens dashboard link)
- In-app notification (banner on dashboard)
- SMS (opt-in only, for significant savings >$50/month)

---

## 2. Tier Change Policies

### Upgrade Policy: Immediate Effect

```
User upgrades from Basic → Premium on Oct 15:

1. Immediate access to Premium features
2. Prorated charge for current month:
   - Basic refund: ($8 / 30 days) × 15 days = $4.00
   - Premium charge: ($30 / 30 days) × 15 days = $15.00
   - Net charge: $11.00

3. Next month: Full Premium charge ($30)
4. Benefits apply immediately:
   - Lower compute fees (0.1% after $200)
   - Lower withdrawal fees (1% → 0.1%)
   - Dedicated account manager
```

**Rationale:** Immediate upgrades drive revenue and user satisfaction.

### Downgrade Policy: End-of-Cycle

```
User downgrades from Premium → Basic on Oct 15:

1. Continue Premium features until Oct 31 (end of cycle)
2. No prorated refund (already paid for full month)
3. Nov 1: Basic tier takes effect
4. Warning shown before confirmation:
   "Your Premium benefits will end on Oct 31. You'll lose:
    - Ultra-low fees (0.1% after $200)
    - Dedicated account manager
    - Advanced analytics"
```

**Rationale:** Prevents gaming (upgrade for big job, immediate downgrade).

### Lock-In Period: 30 Days

```typescript
function canChangeTier(user: User, newTier: string): {
  allowed: boolean;
  reason?: string;
  earliestChangeDate?: Date;
} {
  const daysSinceLastChange =
    (Date.now() - user.lastTierChangeDate.getTime()) / (1000 * 60 * 60 * 24);

  if (daysSinceLastChange < 30) {
    const earliestDate = new Date(user.lastTierChangeDate);
    earliestDate.setDate(earliestDate.getDate() + 30);

    return {
      allowed: false,
      reason: 'You can change tiers once every 30 days to prevent gaming.',
      earliestChangeDate: earliestDate
    };
  }

  return { allowed: true };
}
```

**Exception:** Upgrades always allowed (no lock-in for upgrades).

---

## 3. Behavioral Economics in Tier Migration

### Loss Aversion for Downgrades

**Free → Basic → Premium pathway creates sunk costs:**

When user downgrades Basic → Free:
```
⚠️ Warning: Downgrading Will Lock Your Compute Capital

You have $245.50 in Compute Capital. Downgrading to Free tier means:

❌ You CAN'T withdraw it as cash anymore
❌ You CAN only use it for compute
❌ You'll pay 20% fees (vs current 5%)

At your usage level ($85/month), you'd lose $15/month by downgrading.

Are you sure you want to downgrade?

[Cancel]  [Yes, Downgrade Anyway]
```

### Anchoring: Show Savings from Current Tier

```
┌──────────────────────────────────────────────────────────┐
│  Your Current Savings (Basic Tier)                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  This month, you've saved:                               │
│  • $15.00 in lower compute fees (5% vs 20%)              │
│  • $12.50 from withdrawing Compute Capital               │
│                                                           │
│  Total saved: $27.50 this month                          │
│  Annual savings: ~$330                                    │
│                                                           │
│  Your Basic membership ($8/month) paid for itself!       │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Social Proof for Upgrades

```
💡 78% of users with $200+/month usage choose Premium

"I was skeptical about Premium at first, but the 0.1% fees
 saved me $180 last month alone. Worth every penny!"
 — Alex M., ML Engineer

[Upgrade to Premium]  [Calculate My Savings]
```

---

## 4. Tier Optimization Dashboard

### Real-Time Tier Recommendation Widget

```
┌──────────────────────────────────────────────────────────┐
│  💡 Tier Optimization                                     │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Current tier: Basic ($8/month)                          │
│  This month's spend: $520                                │
│                                                           │
│  ⚡ Recommendation: Upgrade to Premium                   │
│                                                           │
│  You'd save this month:                                  │
│  • Current cost: $554 (compute + membership)            │
│  • Premium cost: $235 (compute + membership)            │
│  • Savings: $319 this month!                            │
│                                                           │
│  Annual savings: ~$3,828                                 │
│                                                           │
│  [Upgrade Now]  [See Breakdown]  [Remind Me Later]      │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Historical Savings Tracker

```
┌──────────────────────────────────────────────────────────┐
│  Your Savings History                                     │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  October 2025:   Saved $27 vs Free tier                  │
│  September 2025: Saved $31 vs Free tier                  │
│  August 2025:    Saved $25 vs Free tier                  │
│  July 2025:      Saved $29 vs Free tier                  │
│                                                           │
│  Total saved (4 months): $112                            │
│  Basic membership cost: $32 ($8 × 4)                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  Net benefit: +$80                                        │
│                                                           │
│  ✅ Your Basic tier has saved you money!                 │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Tier Change Flow (UX)

### Upgrade Flow (Frictionless)

```
Step 1: User clicks "Upgrade to Premium"
  ↓
Step 2: Show benefits + immediate savings
  ┌─────────────────────────────────────────────────┐
  │ Upgrade to Premium                               │
  │                                                  │
  │ ✓ Ultra-low fees (0.1% after $200)             │
  │ ✓ Minimal withdrawal fees (0.1% after $200)    │
  │ ✓ Dedicated account manager                     │
  │ ✓ Advanced analytics                            │
  │                                                  │
  │ First charge: $11 (prorated for Oct 15-31)     │
  │ Then: $30/month (or $324/year, save $36)       │
  │                                                  │
  │ Based on your usage, you'll save $319 this mo! │
  │                                                  │
  │ [◉ Monthly $30]  [○ Annual $324 (save $36)]    │
  │                                                  │
  │ [Cancel]           [Confirm Upgrade]            │
  └─────────────────────────────────────────────────┘
  ↓
Step 3: Process payment (Stripe)
  ↓
Step 4: Immediate access
  "✅ Welcome to Premium! Your benefits are active now."
```

### Downgrade Flow (Add Friction)

```
Step 1: User clicks "Downgrade to Basic"
  ↓
Step 2: Show what they'll lose + retention offer
  ┌─────────────────────────────────────────────────┐
  │ ⚠️ Are you sure you want to downgrade?          │
  │                                                  │
  │ You'll lose:                                     │
  │ ❌ Ultra-low fees (0.1% → 5%)                   │
  │ ❌ Dedicated account manager                     │
  │ ❌ Advanced analytics                            │
  │                                                  │
  │ At your usage level ($450/month), downgrading   │
  │ will cost you ~$300/month more in fees!         │
  │                                                  │
  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
  │                                                  │
  │ 💡 Special offer: Stay on Premium for 50% off  │
  │    next month ($15 instead of $30)              │
  │                                                  │
  │ [Keep Premium 50% Off]  [Still Downgrade]      │
  └─────────────────────────────────────────────────┘
  ↓
Step 3 (if still downgrading): Confirm
  "Downgrade will take effect Nov 1. You'll keep Premium
   benefits until then."
```

---

## 6. Churn Prevention Strategies

### Exit Intent Offers

When user hovers over "Cancel Membership":

```
┌─────────────────────────────────────────────────────────┐
│  Before you go... 👋                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  We'd hate to see you leave! Here's what we can do:    │
│                                                          │
│  1️⃣ Pause membership (2 months, keep your benefits)   │
│  2️⃣ 50% off for 3 months ($4/month for Basic)         │
│  3️⃣ Downgrade instead of cancel (keep some benefits)  │
│                                                          │
│  Your feedback matters. Why are you leaving?            │
│  ○ Too expensive                                        │
│  ○ Not using it enough                                  │
│  ○ Found alternative                                    │
│  ○ Technical issues                                     │
│  ○ Other: [________]                                    │
│                                                          │
│  [Pause 2 Months]  [Get 50% Off]  [Still Cancel]      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Win-Back Campaigns

For users who cancel, send automated sequence:

**Day 7:** "We miss you! Here's what's new..."
**Day 30:** "50% off for 3 months if you return"
**Day 90:** "Your Compute Capital is still here ($X available)"

---

## 7. A/B Testing Framework

### Test Variables

1. **Breakeven thresholds:** $40 vs $50 vs $60 for Basic
2. **Notification timing:** After 1 month vs 2 months
3. **Messaging:** Savings-focused vs feature-focused
4. **Social proof:** With vs without testimonials
5. **Annual discount:** 10% vs 15% vs 17%

### Success Metrics

- Conversion rate (Free → Basic, Basic → Premium)
- Time to upgrade (days from signup to first upgrade)
- Downgrade rate (% who downgrade within 90 days)
- Net Revenue Retention (NRR)
- Lifetime Value (LTV) by cohort

---

## 8. Key Recommendations

### Immediate Implementation

1. **Auto-suggest upgrades** at $40 and $200 thresholds
2. **Immediate upgrades, end-of-cycle downgrades**
3. **30-day lock-in** (prevents gaming)
4. **Loss aversion warnings** on downgrades
5. **Savings dashboard** (show tier value)

### Phase 2 Enhancements

1. **ML-based predictions** (predict churn, offer retention)
2. **Dynamic breakeven** (adjust by user behavior)
3. **A/B test everything** (messaging, timing, offers)
4. **Referral bonuses** (1 month free for referrals)
5. **Usage alerts** ("You're at $180, $20 more triggers Premium savings!")

---

## Conclusion

Intelligent tier migration system that:
- **Maximizes upgrades** through timely, relevant suggestions
- **Minimizes downgrades** through loss aversion and retention offers
- **Prevents gaming** via lock-in periods and end-of-cycle changes
- **Drives value** by showing savings transparently

This approach balances user autonomy with platform revenue optimization.
