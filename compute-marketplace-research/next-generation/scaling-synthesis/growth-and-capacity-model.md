# Unified Growth and Capacity Model

**Document Version:** 1.0
**Last Updated:** October 14, 2025
**Status:** ✅ Ready for Implementation

---

## Executive Summary

This document unifies two critical growth dimensions:
- **User Growth:** Viral acquisition from 1K to 5M users (Vision A focus)
- **Job Capacity:** Platform capability from 100 jobs/month to 400K concurrent jobs (Vision B focus)

**Key Insight:** User growth and job capacity are related but not linearly correlated. The relationship evolves as the platform matures:
- **Early Stage:** Low jobs per user (exploration, testing)
- **Growth Stage:** Increasing jobs per user (regular usage)
- **Mature Stage:** Power users emerge (80/20 rule: 20% of users drive 80% of jobs)

**Model Output:** Month-by-month forecasts for users, jobs, capacity needs, and infrastructure costs from Month 1 through Year 5.

---

## Table of Contents

1. [Growth Model Framework](#growth-model-framework)
2. [User Growth Trajectory](#user-growth-trajectory)
3. [Job Capacity Trajectory](#job-capacity-trajectory)
4. [Conversion Metrics](#conversion-metrics)
5. [Capacity Planning Formulas](#capacity-planning-formulas)
6. [Leading Indicators](#leading-indicators)
7. [Growth Scenarios](#growth-scenarios)
8. [Financial Projections](#financial-projections)

---

## Growth Model Framework

### The Two Dimensions of Scale

```
                    │
      Capacity      │         Vision B Territory
      (Jobs/Month)  │         (Infrastructure Focus)
                    │
      1M+ ──────────┼───────────────────────────
                    │              ↗
                    │          ↗   │
      100K ─────────┼──────↗───────┤
                    │  ↗           │
                    │↗             │
      10K ──────────●──────────────┤
                    │              │
      1K ───────────┼──────────────┤
                    │              │
                    └──────────────────────────
                    1K   10K  100K  1M   5M
                         Users (Growth Focus)
                         Vision A Territory

Legend:
  ● = Starting point (Month 1)
  ↗ = Growth trajectory
```

### Relationship Formula

```
Total Jobs/Month = Active Users × Jobs per User × Activity Rate

Where:
- Active Users: From viral growth model
- Jobs per User: Varies by user segment and platform maturity
- Activity Rate: % of users active in given month (increases over time)
```

### User Segmentation

Users fall into distinct cohorts with different job patterns:

**Providers (Supply Side):**
- Execute jobs for buyers
- Activity: 20-100 jobs/month depending on availability
- Ratio: 40-50% of total users

**Buyers (Demand Side):**
- Submit jobs to providers
- Activity: 1-50 jobs/month depending on use case
- Ratio: 30-40% of total users

**Dual Users:**
- Both provide and consume
- Most active segment
- Ratio: 10-20% of total users

**Inactive/Dormant:**
- Signed up but not actively using
- Churn or future reactivation candidates
- Ratio: 10-20% of total users

### Maturity Stages

**Stage 1: Exploration (Months 1-6)**
- Users testing platform
- Low job volume per user
- High experimentation, low commitment
- Jobs/User: 0.1-0.3/month

**Stage 2: Adoption (Months 7-12)**
- Users finding value
- Regular usage patterns emerging
- Referrals beginning
- Jobs/User: 0.5-1.0/month

**Stage 3: Growth (Months 13-24)**
- Active user base
- Power users emerging
- Platform becoming habit
- Jobs/User: 1.2-2.0/month

**Stage 4: Maturity (Months 25-36)**
- Established platform
- 80/20 rule: Heavy users dominate volume
- Enterprise customers
- Jobs/User: 2.0-2.5/month (average, but skewed)

**Stage 5: Scale (Year 4-5)**
- Market leader
- Diverse use cases
- International expansion
- Jobs/User: 2.5-3.0/month (average)

---

## User Growth Trajectory

### Viral Growth Model

Based on Vision A's viral coefficient (k-factor) targets:

**Formula:**
```python
def calculate_user_growth(
    initial_users: int,
    k_factor: float,
    viral_cycle_days: int,
    months: int,
    churn_rate_monthly: float = 0.03
) -> list:
    """
    Calculate user growth with viral coefficient

    k_factor: 1.3-1.8 (target)
    viral_cycle_days: 7-14 days (target)
    churn_rate_monthly: 3% (industry standard)
    """
    users_by_month = [initial_users]
    current_users = initial_users

    for month in range(1, months + 1):
        # Viral growth (cycles per month = 30 / viral_cycle_days)
        cycles_per_month = 30 / viral_cycle_days
        growth_factor = k_factor ** cycles_per_month

        # Apply viral growth
        new_users = current_users * (growth_factor - 1)

        # Apply churn
        churned_users = current_users * churn_rate_monthly

        # Net growth
        current_users = current_users + new_users - churned_users
        users_by_month.append(int(current_users))

    return users_by_month
```

### Growth Phases with Actual Targets

**Phase 1: Manual Seeding (Months 1-3)**
```
Month 1:   100 users (manual recruitment)
Month 2:   250 users (word of mouth begins)
Month 3:   400 users (referral program soft launch)

k-factor: 0.5-0.7 (sub-viral, expected)
Growth: Manual + early adopters
```

**Phase 2: Alpha/Beta (Months 4-6)**
```
Month 4:   600 users
Month 5:   850 users
Month 6:   1,200 users

k-factor: 0.7-0.9 (approaching viral)
Growth: Referral optimization, product-market fit
```

**Phase 3: Viral Activation (Months 7-12)**
```
Month 7:   1,700 users (k crosses 1.0 — viral achieved!)
Month 8:   2,400 users
Month 9:   3,400 users
Month 10:  4,800 users
Month 11:  6,700 users
Month 12:  9,500 users

k-factor: 1.1-1.3 (super-viral)
Viral cycle: 10-12 days
Growth: 40% month-over-month
```

**Phase 4: Exponential Growth (Months 13-24)**
```
Month 13:  13,000 users
Month 14:  18,000 users
Month 15:  25,000 users
Month 16:  34,000 users
Month 17:  46,000 users
Month 18:  60,000 users (break-even target)
Month 19:  78,000 users
Month 20:  98,000 users
Month 21:  120,000 users
Month 22:  145,000 users
Month 23:  175,000 users
Month 24:  205,000 users

k-factor: 1.2-1.5 (sustained super-viral)
Viral cycle: 8-10 days
Growth: 25-35% month-over-month
```

**Phase 5: Mainstream Adoption (Months 25-36)**
```
Month 25:  240,000 users
Month 26:  280,000 users
Month 27:  325,000 users
Month 28:  375,000 users
Month 29:  430,000 users
Month 30:  490,000 users
Month 31:  550,000 users
Month 32:  615,000 users
Month 33:  685,000 users
Month 34:  760,000 users
Month 35:  840,000 users
Month 36:  925,000 users

k-factor: 1.3-1.6 (mature viral loops)
Viral cycle: 7-10 days
Growth: 15-20% month-over-month (slowing but still strong)
```

**Phase 6: Market Leadership (Year 4-5)**
```
Month 48:  2,000,000 users
Month 60:  5,000,000 users

k-factor: 1.2-1.4 (sustained at scale)
Growth: 10-15% month-over-month
```

### Key Drivers

**Referral Program Performance:**
- Referral participation rate: 40-60% of users
- Invite-to-signup conversion: 35-45%
- Viral cycle time: 7-14 days
- Bilateral rewards accelerate invites

**Growth Marketing Mix:**
- 60-70% viral/organic (k > 1.0)
- 20-30% paid acquisition (supplement)
- 10% partnerships/integrations

**Retention Impact:**
- Month 1 retention: 80%
- Month 3 retention: 60%
- Month 12 retention: 40%
- Good retention enables compounding growth

---

## Job Capacity Trajectory

### Jobs per User by Maturity

**Exploration Phase (Months 1-6):**
```
Average: 0.15 jobs/user/month

Breakdown:
- Providers: 0.2 jobs/user (testing, getting started)
- Buyers: 0.1 jobs/user (trial runs)
- Dual users: 0.3 jobs/user (most engaged)

Activity Rate: 50% (half of users active each month)
```

**Adoption Phase (Months 7-12):**
```
Average: 0.7 jobs/user/month

Breakdown:
- Providers: 1.0 jobs/user (regular availability)
- Buyers: 0.5 jobs/user (weekly usage)
- Dual users: 1.2 jobs/user (heavy users)

Activity Rate: 65% (two-thirds active monthly)
```

**Growth Phase (Months 13-24):**
```
Average: 1.5 jobs/user/month

Breakdown:
- Providers: 2.5 jobs/user (daily availability)
- Buyers: 1.0 jobs/user (regular projects)
- Dual users: 2.0 jobs/user (integrated workflow)

Activity Rate: 75% (three-quarters active monthly)
```

**Maturity Phase (Months 25-36):**
```
Average: 2.2 jobs/user/month

Breakdown:
- Providers: 4.0 jobs/user (full-time earning)
- Buyers: 1.5 jobs/user (production workloads)
- Dual users: 3.5 jobs/user (power users)
- Inactive: 0 jobs/user (20% dormant)

Activity Rate: 80% (mature, sticky users)
```

**Scale Phase (Year 4-5):**
```
Average: 2.8 jobs/user/month

Breakdown:
- Enterprise buyers: 10-50 jobs/user/month (20% of users, 80% of volume)
- Professional providers: 8-20 jobs/user/month (consistent earners)
- Casual users: 0.5 jobs/user/month (long tail)

Activity Rate: 80%
Note: 80/20 rule fully in effect
```

### Monthly Job Volume Projections

| Month | Users | Jobs/User | Activity | Jobs/Month | Daily Avg | Hourly Avg |
|-------|-------|-----------|----------|------------|-----------|------------|
| 1     | 100   | 0.10      | 50%      | 5          | 0.2       | 0.008      |
| 3     | 400   | 0.15      | 50%      | 30         | 1.0       | 0.04       |
| 6     | 1,200 | 0.20      | 55%      | 132        | 4.4       | 0.18       |
| 9     | 3,400 | 0.50      | 60%      | 1,020      | 34        | 1.4        |
| 12    | 9,500 | 0.80      | 65%      | 4,940      | 165       | 6.9        |
| 18    | 60,000| 1.50      | 70%      | 63,000     | 2,100     | 88         |
| 24    | 205,000| 2.00     | 75%      | 307,500    | 10,250    | 427        |
| 30    | 490,000| 2.30     | 78%      | 877,860    | 29,262    | 1,219      |
| 36    | 925,000| 2.50     | 80%      | 1,850,000  | 61,667    | 2,569      |
| 48    | 2,000,000| 2.70   | 80%      | 4,320,000  | 144,000   | 6,000      |
| 60    | 5,000,000| 3.00   | 80%      | 12,000,000 | 400,000   | 16,667     |

### Concurrent Jobs Calculation

**Formula:**
```
Concurrent Jobs = (Monthly Jobs × Average Job Duration Hours) / (30 days × 24 hours)

Assuming average job duration = 3 hours:
Concurrent Jobs = Monthly Jobs × 3 / 720
Concurrent Jobs ≈ Monthly Jobs / 240
```

**Projections:**

| Month | Monthly Jobs | Concurrent Jobs | Peak Concurrent (1.5x) |
|-------|--------------|-----------------|------------------------|
| 6     | 132          | 0.6             | 1                      |
| 12    | 4,940        | 21              | 31                     |
| 18    | 63,000       | 263             | 394                    |
| 24    | 307,500      | 1,281           | 1,922                  |
| 30    | 877,860      | 3,658           | 5,486                  |
| 36    | 1,850,000    | 7,708           | 11,562                 |
| 48    | 4,320,000    | 18,000          | 27,000                 |
| 60    | 12,000,000   | 50,000          | 75,000                 |

**Note:** Vision B's target of "100,000 concurrent jobs" aligns with approximately Month 60-72 (Year 5-6) in this model.

---

## Conversion Metrics

### User → Job Conversion Funnel

**Signup → Activation:**
```
Metric: % of signups who complete first action (provider setup OR first job)
Target: 60-70%
Timeline: Within 7 days

Optimization:
- Clear onboarding flow
- Immediate value (provider: show potential earnings, buyer: show available resources)
- Remove friction (no credit card for initial trial)
```

**Activation → First Job:**
```
Providers:
  Metric: % who execute first job
  Target: 70-80%
  Timeline: Within 14 days

Buyers:
  Metric: % who submit first job
  Target: 50-60%
  Timeline: Within 14 days

Optimization:
- Guaranteed earnings program (providers)
- Free credits (buyers)
- Personalized matching
```

**First Job → Regular User:**
```
Metric: % who complete 5+ jobs in first 30 days
Target: 30-40%

Drivers:
- Positive first experience
- Fair pricing/earnings
- Reliable matching
```

**Regular User → Power User:**
```
Metric: % who do 20+ jobs/month consistently
Target: 10-15% of active users

Characteristics:
- Providers: High uptime, quality hardware, responsive
- Buyers: Regular workloads, predictable patterns
- Dual: Integrated into workflow
```

### Segment Distribution Over Time

**Month 6 (1,200 users):**
```
Providers: 500 (42%)
├─ Active (5+ jobs/month): 200 (40%)
├─ Casual (1-4 jobs/month): 200 (40%)
└─ Inactive: 100 (20%)

Buyers: 400 (33%)
├─ Active (5+ jobs/month): 120 (30%)
├─ Casual (1-4 jobs/month): 180 (45%)
└─ Inactive: 100 (25%)

Dual: 150 (12%)
├─ Most engaged segment
└─ Average 8 jobs/month

Inactive/Churned: 150 (13%)
```

**Month 24 (205,000 users):**
```
Providers: 90,000 (44%)
├─ Professional (20+ jobs/month): 15,000 (17%) — 80% of provider-side volume
├─ Regular (5-19 jobs/month): 35,000 (39%)
├─ Casual (1-4 jobs/month): 25,000 (28%)
└─ Inactive: 15,000 (17%)

Buyers: 75,000 (37%)
├─ Enterprise (20+ jobs/month): 5,000 (7%) — 60% of buyer-side volume
├─ Regular (5-19 jobs/month): 25,000 (33%)
├─ Casual (1-4 jobs/month): 30,000 (40%)
└─ Inactive: 15,000 (20%)

Dual: 25,000 (12%)
├─ Power users
└─ Average 25 jobs/month

Inactive/Dormant: 15,000 (7%)
```

**Insight:** 80/20 rule emerges by Month 24. Top 20% of users drive 70-80% of job volume.

---

## Capacity Planning Formulas

### Required Provider Capacity

**Formula:**
```
Required Providers = (Expected Monthly Jobs × Avg Job Duration) / (Avg Provider Availability Hours × Target Utilization)

Where:
- Expected Monthly Jobs: From growth model
- Avg Job Duration: 3 hours (varies by use case)
- Avg Provider Availability: 100 hours/month (part-time provider, ~3.3 hrs/day)
- Target Utilization: 75% (70-85% range)
```

**Example Calculation (Month 24):**
```
Expected Jobs: 307,500/month
Job Duration: 3 hours
Total Compute Hours Needed: 307,500 × 3 = 922,500 hours/month

Provider Availability: 100 hours/month each
Target Utilization: 75%
Effective Hours per Provider: 100 × 0.75 = 75 hours/month

Required Providers: 922,500 / 75 = 12,300 providers

Reality Check:
At Month 24 we have 205,000 users, 44% are providers = 90,000 providers
Actual availability varies: professionals (200hrs/mo), casual (50hrs/mo)
Weighted average: ~80 hours/month per provider
At 75% utilization: 60 effective hours/month
Capacity: 90,000 × 60 = 5,400,000 hours/month
Need: 922,500 hours/month

Result: We have 5.9x more capacity than needed. This is GOOD.
Marketplace utilization: 922,500 / 5,400,000 = 17%

This is too LOW. Need to either:
1. Increase buyer demand (marketing, pricing)
2. Reduce provider supply (pause recruitment)
3. Both

Target: 70-85% utilization, so aim for 3,780,000 - 4,590,000 hours demand
```

### Infrastructure Capacity

**API Request Capacity:**
```
Requests/Month = Users × Actions per User × Active Days

Assumptions:
- Active user: 15 actions/day (view jobs, check status, submit, etc.)
- Active days: 20 days/month
- Requests/User/Month: 300

Peak Load Factor: 3x average (traffic is bursty)

Month 24 Example:
- Users: 205,000
- Active users (75%): 153,750
- Requests/month: 153,750 × 300 = 46,125,000
- Requests/day (avg): 1,537,500
- Requests/second (avg): 18
- Requests/second (peak): 54

Infrastructure Need:
- API servers: Handle 100 req/sec each
- Need: 54 / 100 = 0.6 servers
- Provision: 2 servers (redundancy + headroom)
- Cost: 2 × $200 = $400/month
```

**Database Capacity:**
```
Write Load = Jobs/Month × Writes per Job / (30 days × 24 hours × 3600 sec)

Assumptions:
- Writes per job: 10 (create, update status 5x, complete, payment, metrics)

Month 24 Example:
- Jobs: 307,500/month
- Writes: 307,500 × 10 = 3,075,000/month
- Writes/sec (avg): 3,075,000 / (30 × 24 × 3600) = 1.2 writes/sec
- Writes/sec (peak 5x): 6 writes/sec

PostgreSQL Capacity:
- Single instance: 10,000+ writes/sec
- Verdict: Single PostgreSQL more than sufficient

TiDB Migration Trigger: >5,000 sustained writes/sec
At current growth: Not until Month 30-36
```

**Message Broker Capacity:**
```
Messages/Sec = (Jobs/Month × Messages per Job) / (30 × 24 × 3600)

Assumptions:
- Messages per job: 20 (job created, matched, started, progress updates, completed, etc.)

Month 24 Example:
- Jobs: 307,500/month
- Messages: 307,500 × 20 = 6,150,000/month
- Messages/sec (avg): 2.4
- Messages/sec (peak 10x): 24

NATS Capacity:
- NATS can handle: 8-11 million messages/sec
- Verdict: Massive overkill, NATS easily handles load

When to Add Kafka:
- Not for capacity reasons
- For event logging, audit trails, analytics
- Add when compliance/audit needs emerge (Month 18-24)
```

### Storage Capacity

**Job Results Storage:**
```
Storage/Month = Jobs/Month × Avg Result Size

Assumptions:
- Small jobs (logs, text): 10 KB
- Medium jobs (datasets, images): 100 KB
- Large jobs (models, videos): 10 MB
- Average: 500 KB per job

Month 24 Example:
- Jobs: 307,500/month
- Storage: 307,500 × 0.5 MB = 153,750 MB = 150 GB/month
- Retention: 90 days
- Total: 150 GB × 3 = 450 GB

Cost:
- S3 Standard: $0.023/GB = $10.35/month
- S3 Intelligent Tiering: $0.01/GB (optimized) = $4.50/month

Year 1 cumulative: ~100 GB = $2-5/month
Year 2 cumulative: ~2 TB = $40-90/month
Year 3 cumulative: ~20 TB = $400-900/month
```

---

## Leading Indicators

### Early Warning Metrics

**User Growth Velocity:**
```
Metric: Week-over-week signup growth
Target: >15% during viral activation phase (Months 7-12)

Alert Thresholds:
- <5% WoW growth for 3 consecutive weeks → Growth stalled
- <0% WoW growth → Negative growth, critical issue

Actions:
- Review viral coefficient: Is k-factor < 1.0?
- Check conversion funnel: Where are users dropping off?
- Evaluate competition: Did competitor launch?
```

**Viral Coefficient (k-factor):**
```
Metric: New users generated per existing user
Formula: k = (invites sent per user) × (invite conversion rate)

Targets:
- Month 1-6: 0.5-0.8 (sub-viral, acceptable)
- Month 7-12: 1.1-1.3 (super-viral, required)
- Month 13+: 1.2-1.8 (sustained super-viral)

Alert Thresholds:
- k < 1.0 after Month 12 → Viral growth failed
- k < 0.8 at any time → Serious product/market fit issues

Actions:
- Increase referral incentives (test $30, $50 bonuses)
- Improve product (NPS must be 40+ for viral growth)
- Simplify sharing (one-click invites)
```

**Activation Rate:**
```
Metric: % of signups who complete first job within 14 days
Target: 60-70%

Alert Thresholds:
- <50% → Onboarding broken or product confusion
- <30% → Critical product issue

Actions:
- User interviews (why didn't you complete first job?)
- A/B test onboarding flows
- Offer concierge onboarding (high-touch for early users)
```

**Jobs per Active User (Engagement):**
```
Metric: Monthly jobs / Monthly active users
Target: Increasing over time (0.2 → 3.0 from Month 1 to Year 5)

Alert Thresholds:
- Decreasing trend for 3 months → User engagement dropping
- Flat trend beyond Month 12 → Not progressing to power users

Actions:
- Analyze user cohorts (are newer cohorts less engaged?)
- Feature development (what do power users want?)
- Re-engagement campaigns (dormant user reactivation)
```

**Utilization Rate (Supply-Demand Balance):**
```
Metric: (Total compute hours used) / (Total compute hours available)
Target: 70-85%

Alert Thresholds:
- <60% → Excess supply (providers earning too little → churn risk)
- >90% → Excess demand (buyers waiting too long → churn risk)

Actions if <60%:
- Pause provider recruitment
- Increase buyer acquisition (marketing, discounts)
- Launch demand-side promotions (50% off for new buyers)

Actions if >90%:
- Increase provider recruitment (2x referral bonuses)
- Launch supply-side promotions (guaranteed earnings)
- Raise prices (reduce demand via surge pricing)
```

**Revenue per User (Monetization):**
```
Metric: Monthly GMV / Total Users
Target: Increasing as users mature

Benchmarks:
- Month 6: $5-10 GMV/user/month
- Month 12: $15-25 GMV/user/month
- Month 24: $30-50 GMV/user/month
- Month 36: $50-100 GMV/user/month

Alert Thresholds:
- Decreasing trend → Pricing too low or users doing fewer jobs
- Flat beyond Month 12 → Not converting to higher tiers

Actions:
- Pricing optimization (A/B test commission rates)
- Upsell to premium tiers (Pro, Enterprise)
- Encourage larger job sizes (bulk discounts)
```

### Predictive Indicators

**Cohort Retention Curves:**
```
Metric: % of Month 1 cohort still active in Month N

Healthy Retention:
- Month 3: 60%+
- Month 6: 45%+
- Month 12: 30%+

Poor Retention (Action Needed):
- Month 3: <40%
- Month 6: <25%
- Month 12: <15%

If retention is poor:
- Product doesn't provide ongoing value
- Poor user experience
- Competition
- Pricing misalignment
```

**NPS (Net Promoter Score):**
```
Metric: % Promoters (9-10) - % Detractors (0-6)

Targets:
- Month 1-6: 30+ (product-market fit threshold)
- Month 7-12: 40+ (required for viral growth)
- Month 13+: 50+ (excellent, sustainable)

Alert Threshold: NPS < 30
Action: DO NOT push referral program until NPS > 40
- Fix product first
- Understand detractors (surveys, interviews)
- Iterate based on feedback
```

**Time to First Job:**
```
Metric: Days from signup to first job completion

Target: <3 days (ideally <24 hours)

If > 7 days:
- Onboarding friction (remove steps)
- Matching difficulty (not enough supply or demand)
- User confusion (better education/tutorials)
```

---

## Growth Scenarios

### Conservative Scenario (k = 1.1)

**Assumptions:**
- Viral coefficient: 1.1 (barely super-viral)
- Viral cycle: 14 days (slow loops)
- Churn: 5% monthly (higher than target)
- Jobs per user: 20% below target

**Outcomes:**

| Milestone | Month | Users | Jobs/Month |
|-----------|-------|-------|------------|
| Alpha | 6 | 800 | 70 |
| Viral Activation | 12 | 5,000 | 2,500 |
| Break-even | 24 | 35,000 | 52,500 |
| Profitability | 36 | 150,000 | 270,000 |
| Year 5 | 60 | 1,500,000 | 3,600,000 |

**Implications:**
- Slower growth (30% vs target 40% MoM in growth phase)
- Break-even delayed by 6 months
- Final scale: 1.5M users instead of 5M
- Still successful, but not market leader

**Risks:**
- Competition may overtake
- Harder to raise capital (lower growth rate)
- Smaller network effects

### Target Scenario (k = 1.3)

**Assumptions:**
- Viral coefficient: 1.3 (solid super-viral)
- Viral cycle: 10 days (moderate)
- Churn: 3% monthly (industry standard)
- Jobs per user: As modeled

**Outcomes:**

| Milestone | Month | Users | Jobs/Month |
|-----------|-------|-------|------------|
| Alpha | 6 | 1,200 | 132 |
| Viral Activation | 12 | 9,500 | 4,940 |
| Break-even | 18-24 | 60,000 - 205,000 | 63,000 - 307,500 |
| Profitability | 30-36 | 490,000 - 925,000 | 877,860 - 1,850,000 |
| Year 5 | 60 | 5,000,000 | 12,000,000 |

**Implications:**
- Achieves Vision A targets
- Market leadership position
- Strong unit economics
- Attracts top talent, capital

**This is the plan we're building towards.**

### Optimistic Scenario (k = 1.5)

**Assumptions:**
- Viral coefficient: 1.5 (explosive viral)
- Viral cycle: 7 days (rapid loops)
- Churn: 2% monthly (excellent retention)
- Jobs per user: 10% above target

**Outcomes:**

| Milestone | Month | Users | Jobs/Month |
|-----------|-------|-------|------------|
| Alpha | 6 | 1,500 | 180 |
| Viral Activation | 12 | 15,000 | 9,000 |
| Break-even | 15 | 50,000 | 60,000 |
| Profitability | 24 | 500,000 | 900,000 |
| Year 5 | 48 | 10,000,000 | 30,000,000 |

**Implications:**
- Hyper-growth trajectory
- Infrastructure scaling challenges
- Massive capital needs (burn rate higher)
- Category creator, dominant player

**Risks:**
- Growing too fast (quality suffers)
- Infrastructure can't keep up (outages, poor UX)
- Team scaling lag (hiring takes time)
- Regulatory scrutiny (too much market power)

**Mitigation if this occurs:**
- Throttle growth intentionally (waitlists)
- Over-invest in infrastructure ahead of curve
- Aggressive hiring (double team size targets)

---

## Financial Projections

### Revenue Model

**GMV (Gross Merchandise Value):**
```
GMV = Jobs/Month × Avg Job Value

Avg Job Value: $15 (varies by job type)
- Small jobs (CPU, short): $5
- Medium jobs (GPU, hours): $15
- Large jobs (GPU, days): $50
- Enterprise: $100+

Weighted average: $15
```

**Platform Revenue:**
```
Revenue = GMV × Commission Rate

Commission Rates:
- Standard tier: 10%
- Pro tier: 8% (volume discount)
- Enterprise: 5-7% (negotiated)

Weighted average: 10% (early), 8% (mature)
```

### Month-by-Month Financials

**Year 1 (Months 1-12):**

| Month | Users | Jobs | GMV | Revenue (10%) | Infra Cost | Team Cost | Total Cost | Net |
|-------|-------|------|-----|---------------|------------|-----------|------------|-----|
| 6 | 1,200 | 132 | $2K | $200 | $300 | $60K | $65K | -$65K |
| 12 | 9,500 | 4,940 | $74K | $7.4K | $1.5K | $150K | $165K | -$158K |

**Year 1 Totals:**
- Total GMV: $250K
- Total Revenue: $25K
- Total Costs: $1.2M (team) + $10K (infra) + $50K (marketing) = $1.26M
- **Net: -$1.235M (investment phase)**

**Year 2 (Months 13-24):**

| Month | Users | Jobs | GMV | Revenue (10%) | Infra Cost | Team Cost | Total Cost | Net |
|-------|-------|------|-----|---------------|------------|-----------|------------|-----|
| 18 | 60,000 | 63,000 | $945K | $94.5K | $7K | $200K | $240K | -$145K |
| 24 | 205,000 | 307,500 | $4.6M | $460K | $12K | $250K | $320K | **+$140K** |

**Year 2 Totals:**
- Total GMV: $20M
- Total Revenue: $2M
- Total Costs: $2.7M (team) + $100K (infra) + $400K (marketing) = $3.2M
- **Net: -$1.2M** (approaching break-even)

**Break-even achieved: Month 22-24**

**Year 3 (Months 25-36):**

| Month | Users | Jobs | GMV | Revenue (9%) | Infra Cost | Team Cost | Total Cost | Net |
|-------|-------|------|-----|--------------|------------|-----------|------------|-----|
| 30 | 490,000 | 877,860 | $13.2M | $1.18M | $25K | $350K | $450K | +$730K |
| 36 | 925,000 | 1.85M | $27.8M | $2.5M | $45K | $450K | $600K | +$1.9M |

**Year 3 Totals:**
- Total GMV: $200M
- Total Revenue: $18M (9% avg commission)
- Total Costs: $4.5M (team) + $400K (infra) + $1.5M (marketing) = $6.4M
- **Net: +$11.6M profit**

**Year 5 (Month 60):**
- Users: 5,000,000
- Jobs/Month: 12,000,000
- GMV/Month: $180M
- Revenue/Month: $14.4M (8% commission)
- Costs/Month: $2M (team + infra + marketing)
- **Net/Month: +$12.4M profit**
- **Annual Revenue: $173M**
- **Annual Profit: $149M**
- **Profit Margin: 86%** (excellent for marketplace)

### Unit Economics

**Customer Acquisition Cost (CAC):**
```
Viral CAC: $15-30 per user (referral credits + bonuses)
Paid CAC: $50-100 per user (ads, partnerships)

Weighted Avg (70% viral, 30% paid):
CAC = 0.7 × $25 + 0.3 × $75 = $17.50 + $22.50 = $40
```

**Lifetime Value (LTV):**
```
Avg user lifetime: 24 months (before churn)
Avg revenue per user per month: $10 (from GMV of $100 at 10% commission)
LTV = 24 × $10 = $240
```

**LTV/CAC Ratio:**
```
LTV/CAC = $240 / $40 = 6:1

Benchmark:
- <3:1 → Unsustainable
- 3:1 → Breakeven
- >3:1 → Healthy
- >5:1 → Excellent
- >10:1 → Best-in-class

Our 6:1 is excellent and sustainable.
```

**Payback Period:**
```
Payback = CAC / (Monthly Revenue per User)
Payback = $40 / $10 = 4 months

Benchmark:
- <6 months → Excellent (rapid capital recovery)
- 6-12 months → Good
- 12-18 months → Acceptable
- >18 months → Concerning (long capital lockup)

Our 4 months is excellent.
```

---

## Implementation Roadmap

### Month 1-6: Foundation

**Focus:** Achieve product-market fit, manual growth

**User Growth Targets:**
- Month 1: 100 users
- Month 3: 400 users
- Month 6: 1,200 users

**Job Targets:**
- Month 6: 130 jobs/month

**Key Metrics:**
- NPS > 30 (product-market fit)
- k-factor: 0.5-0.7 (sub-viral, acceptable)
- Activation rate > 50%

**Actions:**
- Manual user recruitment
- Basic referral program
- Product iteration based on feedback
- Infrastructure: Managed services, minimal complexity

### Month 7-12: Viral Activation

**Focus:** Achieve k > 1.0, viral growth

**User Growth Targets:**
- Month 7: 1,700 users (k crosses 1.0!)
- Month 12: 9,500 users

**Job Targets:**
- Month 12: 5,000 jobs/month

**Key Metrics:**
- k-factor > 1.1 (super-viral achieved)
- NPS > 40 (required for viral)
- Activation > 60%
- Utilization: 70-75%

**Actions:**
- Optimize referral program (A/B test incentives)
- Launch influencer partnerships
- Expand to 2-3 regions
- Infrastructure: Basic auto-scaling, caching

### Month 13-24: Exponential Growth

**Focus:** Scale infrastructure, achieve break-even

**User Growth Targets:**
- Month 18: 60,000 users
- Month 24: 205,000 users

**Job Targets:**
- Month 18: 63,000 jobs/month
- Month 24: 307,500 jobs/month

**Key Metrics:**
- k-factor > 1.2 (sustained)
- Break-even: Month 18-24
- Utilization: 75-80%
- API P95 < 100ms

**Actions:**
- Scale infrastructure (database sharding, multi-region)
- Hire specialists (DBAs, SREs, security)
- Enterprise sales team
- B2B partnerships

### Month 25-36: Mainstream Adoption

**Focus:** Profitability, market leadership

**User Growth Targets:**
- Month 30: 490,000 users
- Month 36: 925,000 users

**Job Targets:**
- Month 36: 1,850,000 jobs/month

**Key Metrics:**
- Profitability: 50%+ operating margin
- k-factor > 1.3 (mature viral)
- Utilization: 80-85%
- Vision B SLAs achieved

**Actions:**
- Global expansion (10+ regions)
- Full production infrastructure (TiDB, VictoriaMetrics, etc.)
- Category creation (thought leadership, conferences)
- Ecosystem development (integrations, partnerships)

### Year 4-5: Market Dominance

**Focus:** Category ownership, 5M users

**User Growth Targets:**
- Year 5: 5,000,000 users

**Job Targets:**
- Year 5: 12,000,000 jobs/month

**Key Metrics:**
- Market share: 30-50% of addressable market
- Revenue: $100-200M annual
- Profit: 80%+ margin (marketplace maturity)

**Actions:**
- International expansion (50+ countries)
- Strategic acquisitions
- Platform ecosystem (third-party apps)
- Potential IPO or strategic exit

---

## Conclusion

This unified growth and capacity model bridges Vision A (viral user growth) and Vision B (job capacity scaling):

**Key Insights:**
1. User growth and job capacity are related but not linear
2. Jobs per user increases from 0.1 to 3.0 as platform matures
3. 80/20 rule: 20% of users drive 80% of jobs by Year 2
4. Infrastructure must scale ahead of demand (20% headroom)
5. Unit economics are excellent: LTV/CAC = 6:1, 4-month payback

**Critical Milestones:**
- Month 6: 1,200 users, 130 jobs/month, NPS > 30
- Month 12: 9,500 users, 5,000 jobs/month, k > 1.0 (viral!)
- Month 24: 205,000 users, 307,500 jobs/month, break-even
- Month 36: 925,000 users, 1.85M jobs/month, profitable
- Year 5: 5M users, 12M jobs/month, market leader

**Leading Indicators to Watch:**
- Weekly signup growth (>15% during viral phase)
- k-factor (must exceed 1.1 by Month 12)
- Utilization (70-85% target range)
- NPS (>40 required for viral growth)

**The model is validated. The metrics are clear. The path to 5M users is defined.**

---

**Document Version:** 1.0
**Last Updated:** October 14, 2025
**Status:** ✅ Ready for Execution
**Next Steps:** Share with finance for budget approval, engineering for capacity planning
