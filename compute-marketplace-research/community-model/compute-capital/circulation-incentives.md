# Circulation Incentives - Keeping Compute Capital Flowing

**Document Version:** 1.0
**Date:** October 14, 2025
**Status:** Research Complete - Ready for Implementation

---

## Executive Summary

The health of the Compute Capital economy depends on **velocity** - how quickly CC circulates through the ecosystem. High velocity = thriving economy. Low velocity = stagnation and hoarding.

**Goal:** Design incentive mechanisms that encourage users to **spend CC** (for compute) rather than **hoard CC** (as speculation) or **withdraw CC** (to fiat).

**Target Velocity:** 8-12 (each CC changes hands 8-12 times per year)

**Inspiration:**
- Demurrage currencies (Chiemgauer) - Value decays if not used
- Gaming economies (Robux) - Difficult to withdraw, easy to spend
- Token economics (Helium) - Burn-mint equilibrium ties usage to rewards

---

## Table of Contents

1. [Understanding Velocity](#understanding-velocity)
2. [Demurrage and Time Decay](#demurrage-and-time-decay)
3. [Velocity Bonuses](#velocity-bonuses)
4. [Stake Rewards](#stake-rewards)
5. [Withdrawal Fee Optimization](#withdrawal-fee-optimization)
6. [Gamification and Achievements](#gamification-and-achievements)
7. [Game Theory Analysis](#game-theory-analysis)
8. [Implementation Roadmap](#implementation-roadmap)

---

## Understanding Velocity

### What is CC Velocity?

```
Velocity = Total CC Transacted / Average CC Balance

Example:
- Total CC in circulation: 1,000,000 CC
- Daily CC transactions: 50,000 CC
- Daily velocity: 50,000 / 1,000,000 = 0.05 (5%)
- Annual velocity: 0.05 × 365 = 18.25

Interpretation: Each CC is spent 18.25 times per year
```

### Velocity Benchmarks

| Economy Type | Typical Velocity | Example |
|--------------|------------------|---------|
| Stagnant | 1-3 | Hoard economy, low activity |
| Healthy | 8-12 | Active trading, good circulation |
| Hyperactive | 20+ | Gaming economies, high turnover |
| Unstable | 50+ | Hyperinflation, rush to spend |

**Target for CC: 8-12** (healthy circulation without instability)

### Why Velocity Matters

**High Velocity (Good):**
```
✅ More compute transactions = more platform fees
✅ Users actively using CC = network effects
✅ Price stability (fewer hoards = less panic selling)
✅ Liquidity (always someone buying/selling)
```

**Low Velocity (Bad):**
```
❌ CC sitting idle = wasted capital
❌ Users hoarding = waiting for price increase = speculative behavior
❌ Thin markets = high spreads, poor pricing
❌ Low platform revenue = unsustainable business
```

---

## Demurrage and Time Decay

### Concept: Negative Interest Rate

**Demurrage** = Currency loses value over time if not used

**Historical Example: Chiemgauer (German Regional Currency)**
```
- 6% annual demurrage rate
- Every 3 months, currency holders pay 2% to reactivate notes
- Result: Circulates 2.5x faster than Euro
- Users spend quickly to avoid decay
```

### CC Demurrage Design Options

#### Option 1: Explicit Demurrage (AGGRESSIVE)

```
CC balance decays 0.5% per month if not used

Example:
- User A has 1,000 CC
- Doesn't spend for 1 month
- Balance decays to 995 CC (5 CC burned)
- After 12 months of inactivity: 1,000 × (0.995)^12 = 941 CC (5.9% loss)

Calculation:
balance(t) = balance(0) × (1 - decay_rate)^t

Where:
- decay_rate = 0.005 (0.5% per month)
- t = months of inactivity
```

**Implementation:**

```python
class DemurrageSystem:
    DECAY_RATE_MONTHLY = 0.005  # 0.5% per month
    GRACE_PERIOD_DAYS = 30  # No decay first 30 days

    def apply_demurrage(self, user_id):
        """
        Apply demurrage to idle CC balances.

        Runs daily as a cron job.
        """
        user = db.get_user(user_id)
        cc_balance = user["cc_balance"]
        last_activity = user["last_cc_transaction"]

        # Calculate days since last activity
        days_inactive = (datetime.now() - last_activity).days

        if days_inactive < self.GRACE_PERIOD_DAYS:
            return  # No decay during grace period

        # Calculate monthly decay periods
        months_inactive = days_inactive / 30

        # Apply decay
        decayed_balance = cc_balance * ((1 - self.DECAY_RATE_MONTHLY) ** months_inactive)
        decay_amount = cc_balance - decayed_balance

        if decay_amount > 0:
            # Burn decayed CC
            user["cc_balance"] = decayed_balance
            burn_cc(decay_amount)

            # Log for transparency
            db.insert("demurrage_log", {
                "user_id": user_id,
                "original_balance": cc_balance,
                "decayed_balance": decayed_balance,
                "decay_amount": decay_amount,
                "months_inactive": months_inactive,
                "timestamp": datetime.now()
            })

            # Notify user
            notify_user(user_id, {
                "type": "demurrage_applied",
                "amount": decay_amount,
                "reason": "Inactive balance for {} days".format(days_inactive)
            })
```

**Pros:**
- ✅ Powerful incentive to spend
- ✅ Reduces hoarding dramatically
- ✅ Proven to work (Chiemgauer, Freigeld)

**Cons:**
- ❌ User backlash ("my money is disappearing!")
- ❌ Feels punitive
- ❌ Complexity in explanation
- ❌ May discourage new users

#### Option 2: Soft Demurrage (MODERATE - RECOMMENDED)

```
No balance decay, but inactive users lose rewards/bonuses

Benefits lost after 90 days of inactivity:
- No referral bonuses
- No velocity rewards
- No staking rewards
- Reduced reputation score
- Lower priority in compute queue

This "nudges" users to stay active without punishing them directly
```

**Implementation:**

```python
class SoftDemurrageSystem:
    ACTIVITY_THRESHOLD_DAYS = 90

    def calculate_activity_multiplier(self, user_id):
        """
        Calculate user's activity bonus multiplier.

        Returns:
            1.0 = Active user (within 90 days)
            0.5 = Moderate inactivity (90-180 days)
            0.0 = Inactive (>180 days)
        """
        user = db.get_user(user_id)
        days_since_activity = (datetime.now() - user["last_cc_transaction"]).days

        if days_since_activity < 90:
            return 1.0  # Full benefits
        elif days_since_activity < 180:
            return 0.5  # Reduced benefits
        else:
            return 0.0  # No benefits (reactivation required)

    def apply_activity_penalties(self, user_id):
        """
        Reduce benefits for inactive users (without burning their CC).
        """
        multiplier = self.calculate_activity_multiplier(user_id)

        user = db.get_user(user_id)
        user["activity_multiplier"] = multiplier

        # Apply to various systems
        if multiplier < 1.0:
            # Reputation decays
            user["reputation_score"] *= (0.9 + 0.1 * multiplier)

            # Compute priority drops
            user["queue_priority"] = "low" if multiplier == 0.0 else "medium"

            # Notify user
            if multiplier == 0.5:
                notify_user(user_id, "You've been less active. Stay engaged to maintain full benefits!")
            elif multiplier == 0.0:
                notify_user(user_id, "Your account is inactive. Make a transaction to reactivate bonuses.")

        db.update_user(user)
```

**Pros:**
- ✅ Less aggressive, more user-friendly
- ✅ No direct balance loss
- ✅ Encourages activity without punishment
- ✅ Easier to explain

**Cons:**
- ❌ Less effective at reducing hoarding
- ❌ May not move needle enough on velocity

#### Option 3: No Demurrage (CONSERVATIVE)

```
Rely entirely on other incentive mechanisms (rewards, bonuses, gamification)

Pro: No user backlash
Con: May not achieve high velocity goals
```

**Recommendation: Start with Option 2 (Soft Demurrage), escalate to Option 1 if velocity remains low (<6)**

---

## Velocity Bonuses

### Concept: Reward Fast Spenders

**Opposite of demurrage:** Bonus CC for users who spend quickly

### Velocity Tiers

```
Tier 1 - Slow Spender (velocity < 4):
- Base rate (no bonus)
- Standard fees

Tier 2 - Active User (velocity 4-8):
- +5% bonus CC on all transactions
- Example: Rent compute for 10 CC → Charged 9.5 CC (5% off)

Tier 3 - Power User (velocity 8-12):
- +10% bonus CC on all transactions
- Priority support
- Custom profile badge

Tier 4 - Velocity Champion (velocity >12):
- +15% bonus CC
- Featured in marketplace
- Invitation to beta features
```

**Calculation:**

```python
def calculate_user_velocity(user_id, lookback_days=90):
    """
    Calculate user's personal velocity over lookback period.

    Formula:
    velocity = total_cc_transacted / average_cc_balance
    """
    transactions = db.query("""
        SELECT SUM(cc_amount) as total_transacted,
               AVG(cc_balance_after) as avg_balance
        FROM transactions
        WHERE user_id = %s
          AND timestamp > NOW() - INTERVAL '%s days'
    """, (user_id, lookback_days))

    if transactions["total_transacted"] and transactions["avg_balance"]:
        velocity = transactions["total_transacted"] / transactions["avg_balance"]
    else:
        velocity = 0

    return velocity


def apply_velocity_bonus(user_id, transaction_amount):
    """
    Apply velocity bonus to a transaction.

    High-velocity users pay less for compute.
    """
    velocity = calculate_user_velocity(user_id)

    if velocity >= 12:
        bonus_rate = 0.15  # 15% discount
    elif velocity >= 8:
        bonus_rate = 0.10  # 10% discount
    elif velocity >= 4:
        bonus_rate = 0.05  # 5% discount
    else:
        bonus_rate = 0.0  # No bonus

    discount_amount = transaction_amount * bonus_rate
    final_amount = transaction_amount - discount_amount

    return {
        "original_amount": transaction_amount,
        "discount_amount": discount_amount,
        "final_amount": final_amount,
        "velocity": velocity,
        "bonus_rate": bonus_rate
    }
```

**Example:**

```
User A (Slow Spender):
- Velocity: 3
- Wants to rent 10 CC of compute
- Pays: 10 CC (no discount)

User B (Power User):
- Velocity: 9
- Wants to rent 10 CC of compute
- Pays: 9 CC (10% bonus)
- Savings: 1 CC per transaction

Over 100 transactions:
- User A pays: 1,000 CC
- User B pays: 900 CC
- User B saves: 100 CC (10%)
```

---

## Stake Rewards

### Concept: Earn Interest by Locking CC

**Staking** = Lock CC for fixed period, earn rewards

**Why stake?**
- Reduces circulating supply (supports price)
- Demonstrates long-term commitment
- Provides passive income

### Staking Tiers

```
┌──────────────────────────────────────────────────────┐
│ 30-Day Stake                                         │
│ - Lock period: 30 days                               │
│ - Reward: +2% bonus CC at unlock                     │
│ - Use case: Short-term holders                       │
│                                                       │
│ Example: Stake 1,000 CC → Receive 1,020 CC (30 days) │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ 90-Day Stake                                         │
│ - Lock period: 90 days                               │
│ - Reward: +8% bonus CC at unlock                     │
│ - Use case: Moderate commitment                      │
│                                                       │
│ Example: Stake 1,000 CC → Receive 1,080 CC (90 days) │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ 180-Day Stake                                        │
│ - Lock period: 180 days                              │
│ - Reward: +18% bonus CC at unlock                    │
│ - Use case: Long-term believers                      │
│                                                       │
│ Example: Stake 1,000 CC → Receive 1,180 CC (6 months)│
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ 365-Day Stake                                        │
│ - Lock period: 365 days                              │
│ - Reward: +40% bonus CC at unlock                    │
│ - Use case: Maximum commitment                       │
│                                                       │
│ Example: Stake 1,000 CC → Receive 1,400 CC (1 year)  │
└──────────────────────────────────────────────────────┘
```

**Implementation:**

```python
class StakingSystem:
    STAKE_TIERS = {
        30: 0.02,   # 2% APY
        90: 0.08,   # 8% APY
        180: 0.18,  # 18% APY
        365: 0.40   # 40% APY
    }

    def stake_cc(self, user_id, cc_amount, lock_days):
        """
        User stakes CC for rewards.
        """
        if lock_days not in self.STAKE_TIERS:
            raise InvalidStakePeriodError()

        user = db.get_user(user_id)
        if user["cc_balance"] < cc_amount:
            raise InsufficientFundsError()

        # Calculate reward
        reward_rate = self.STAKE_TIERS[lock_days]
        reward_amount = cc_amount * reward_rate

        # Lock user's CC
        user["cc_balance"] -= cc_amount
        user["cc_staked"] = user.get("cc_staked", 0) + cc_amount

        # Create stake record
        stake = {
            "id": generate_uuid(),
            "user_id": user_id,
            "cc_amount": cc_amount,
            "reward_amount": reward_amount,
            "lock_days": lock_days,
            "stake_start": datetime.now(),
            "stake_end": datetime.now() + timedelta(days=lock_days),
            "status": "active"
        }
        db.insert("stakes", stake)
        db.update_user(user)

        return stake

    def unstake_cc(self, stake_id):
        """
        User unstakes CC after lock period.
        """
        stake = db.get("stakes", stake_id)

        if stake["status"] != "active":
            raise StakeNotActiveError()

        # Check if lock period complete
        if datetime.now() < stake["stake_end"]:
            raise StakeStillLockedError(f"Unlock at {stake['stake_end']}")

        # Return principal + reward
        user = db.get_user(stake["user_id"])
        total_return = stake["cc_amount"] + stake["reward_amount"]

        user["cc_balance"] += total_return
        user["cc_staked"] -= stake["cc_amount"]

        # Update stake status
        stake["status"] = "completed"
        stake["completed_at"] = datetime.now()
        db.update("stakes", stake)
        db.update_user(user)

        # Notify user
        notify_user(stake["user_id"], {
            "type": "stake_completed",
            "principal": stake["cc_amount"],
            "reward": stake["reward_amount"],
            "total": total_return
        })

        return total_return

    def emergency_unstake(self, stake_id):
        """
        User unstakes early (with penalty).

        Penalty: Lose all rewards + 5% of principal
        """
        stake = db.get("stakes", stake_id)

        if stake["status"] != "active":
            raise StakeNotActiveError()

        penalty_rate = 0.05  # 5% penalty
        penalty_amount = stake["cc_amount"] * penalty_rate

        # Return principal minus penalty (no rewards)
        user = db.get_user(stake["user_id"])
        returned_amount = stake["cc_amount"] - penalty_amount

        user["cc_balance"] += returned_amount
        user["cc_staked"] -= stake["cc_amount"]

        # Burn penalty
        burn_cc(penalty_amount)

        # Update stake
        stake["status"] = "emergency_unstaked"
        stake["penalty_paid"] = penalty_amount
        stake["completed_at"] = datetime.now()
        db.update("stakes", stake)
        db.update_user(user)

        # Notify user
        notify_user(stake["user_id"], {
            "type": "emergency_unstake",
            "returned": returned_amount,
            "penalty": penalty_amount,
            "warning": "You lost your rewards and paid a 5% penalty"
        })

        return returned_amount
```

**Benefits to Ecosystem:**

```
Example: 30% of circulating CC gets staked
- Total supply: 1M CC
- Staked: 300K CC
- Active circulation: 700K CC

Effects:
✅ Reduced sell pressure (stakers can't sell)
✅ Price support (less supply = higher price)
✅ Demonstrates confidence (users believe in future)
✅ Platform gains time (locked funds = predictable runway)
```

---

## Withdrawal Fee Optimization

### Goal: Make Withdrawals "Expensive Enough" to Discourage, But Not Punitive

**Current Plan (from membership design):**
```
$8/month tier: 5% withdrawal fee
$30/month tier: 1% → 0.1% after $200 withdrawn
```

### Behavioral Economics Approach

**Principle:** Fees should be:
1. **High enough** to make staying in CC attractive
2. **Low enough** to avoid "trapped money" perception
3. **Progressive** to reward large, infrequent withdrawals over small, frequent ones

### Optimized Fee Structure

```
┌────────────────────────────────────────────────────────┐
│ WITHDRAWAL FEE SCHEDULE                                │
├────────────────────────────────────────────────────────┤
│ Small Withdrawals (<$50):                              │
│   Fee: 8% (discourage frequent small cashouts)         │
│                                                         │
│ Medium Withdrawals ($50-$200):                         │
│   Fee: 5% (standard rate)                              │
│                                                         │
│ Large Withdrawals ($200-$1000):                        │
│   Fee: 3% (reward batching)                            │
│                                                         │
│ Bulk Withdrawals (>$1000):                             │
│   Fee: 1% (best rate for serious users)               │
└────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
def calculate_withdrawal_fee(usd_amount, user_tier):
    """
    Calculate withdrawal fee based on amount and user tier.

    Progressive fee structure encourages larger, less frequent withdrawals.
    """
    # Base fee by amount (encourages batching)
    if usd_amount < 50:
        base_fee_rate = 0.08  # 8% for small amounts
    elif usd_amount < 200:
        base_fee_rate = 0.05  # 5% for medium amounts
    elif usd_amount < 1000:
        base_fee_rate = 0.03  # 3% for large amounts
    else:
        base_fee_rate = 0.01  # 1% for bulk withdrawals

    # Tier discount
    if user_tier == "premium":  # $30/month
        tier_discount = 0.5  # 50% off fees
    elif user_tier == "basic":  # $8/month
        tier_discount = 0.0  # No discount
    else:  # Free tier
        tier_discount = 0.0  # No discount, highest fees

    # Apply discount
    final_fee_rate = base_fee_rate * (1 - tier_discount)

    # Calculate fee
    fee_amount = usd_amount * final_fee_rate
    net_amount = usd_amount - fee_amount

    return {
        "gross_amount": usd_amount,
        "fee_rate": final_fee_rate,
        "fee_amount": fee_amount,
        "net_amount": net_amount
    }
```

**Example Comparisons:**

```
User A (Basic tier) withdraws $20:
- Fee: $20 × 8% = $1.60
- Net: $18.40
- Effective loss: 8%
→ Ouch! Better to save up

User B (Basic tier) withdraws $500:
- Fee: $500 × 3% = $15
- Net: $485
- Effective loss: 3%
→ Much better rate

User C (Premium tier) withdraws $500:
- Fee: $500 × 3% × 50% = $7.50
- Net: $492.50
- Effective loss: 1.5%
→ Best rate

Lesson: Batch withdrawals + upgrade tier = minimize fees
```

### Withdrawal Velocity Limits

```
Limit withdrawal frequency to discourage "cashflow arbitrage"

Rules:
- Free tier: 1 withdrawal per month
- Basic tier ($8/month): 2 withdrawals per month
- Premium tier ($30/month): 4 withdrawals per month

Exceeding limit:
- Additional +5% penalty per extra withdrawal

This encourages:
✅ Planning ahead (batch withdrawals)
✅ Keeping CC in ecosystem (earn + spend, not earn + cashout)
❌ Prevents treating platform as "instant ATM"
```

---

## Gamification and Achievements

### Concept: Make CC Usage Fun

**Insight:** People engage more with systems that feel like games

### Achievement System

```
🏆 COMPUTE CAPITAL ACHIEVEMENTS 🏆

┌────────────────────────────────────────────────────┐
│ SPENDER ACHIEVEMENTS                               │
├────────────────────────────────────────────────────┤
│ 🥉 Bronze Spender - Spend 100 CC                  │
│    Reward: +10 bonus CC                            │
│                                                     │
│ 🥈 Silver Spender - Spend 1,000 CC                │
│    Reward: +100 bonus CC + "Active User" badge    │
│                                                     │
│ 🥇 Gold Spender - Spend 10,000 CC                 │
│    Reward: +1,000 bonus CC + "Power User" badge   │
│                                                     │
│ 💎 Diamond Spender - Spend 100,000 CC             │
│    Reward: +10,000 bonus CC + VIP status          │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ VELOCITY ACHIEVEMENTS                              │
├────────────────────────────────────────────────────┤
│ ⚡ Speed Demon - Velocity > 15 for 30 days        │
│    Reward: Permanent +5% transaction bonus        │
│                                                     │
│ 🌪️ Whirlwind - Velocity > 20 for 30 days         │
│    Reward: Featured profile + custom badge        │
│                                                     │
│ 🚀 Hyperdrive - Velocity > 30 for 30 days         │
│    Reward: 1 month free Premium membership        │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ COMMUNITY ACHIEVEMENTS                             │
├────────────────────────────────────────────────────┤
│ 👥 Circle Builder - Form a compute circle         │
│    Reward: +50 CC + "Circle Member" badge         │
│                                                     │
│ 🤝 Super Connector - Refer 10 users               │
│    Reward: +500 CC + "Connector" badge            │
│                                                     │
│ 🌍 Global Citizen - Trade with users in 3 continents │
│    Reward: +200 CC + "Global Trader" badge        │
└────────────────────────────────────────────────────┘
```

### Leaderboards

```
📊 MONTHLY LEADERBOARDS

Top Spenders (Total CC Used):
1. Alice: 15,000 CC → 1,000 CC prize
2. Bob: 12,500 CC → 500 CC prize
3. Carol: 10,200 CC → 250 CC prize

Top Velocity (Highest Personal Velocity):
1. Dave: 28.5 velocity → 1,000 CC prize
2. Eve: 22.1 velocity → 500 CC prize
3. Frank: 19.8 velocity → 250 CC prize

Top Circle (Best Utilization):
1. Circle #42: 98.5% utilization → 2,000 CC shared prize
2. Circle #17: 96.2% utilization → 1,000 CC shared prize
3. Circle #89: 94.8% utilization → 500 CC shared prize

Prizes reset monthly to encourage ongoing competition
```

---

## Game Theory Analysis

### Nash Equilibrium: What's the Rational Strategy?

**Scenario:** User has 1,000 CC. What should they do?

#### Strategy 1: Hoard (Wait for Price Increase)

```
Payoff:
- If CC price increases 20%: Profit $20 (1,000 × $0.02)
- If CC price stays flat: $0 gain
- If CC price decreases 10%: Loss $10
- Demurrage cost: -6% per year = -$6/year

Expected value: Low to negative (depends on price movement)
Risk: High (speculative)
Opportunity cost: Miss out on compute usage benefits
```

#### Strategy 2: Spend (Use for Compute)

```
Payoff:
- Get compute value: 1,000 hours on reference machine
- Market value: $100-150 (vs. AWS equivalent $300+)
- Velocity bonus: If velocity > 8, get +10% discount
- Achievement bonuses: +100 CC for milestones

Expected value: High (tangible compute benefit)
Risk: Low (you needed compute anyway)
Opportunity cost: None (you're using the platform as intended)
```

#### Strategy 3: Trade (Arbitrage)

```
Payoff:
- Buy CC when undervalued (< $0.09)
- Sell CC when overvalued (> $0.11)
- Profit margin: $0.02 per CC per cycle
- Frequency: 2-3 cycles per month = $40-60 profit

Expected value: Medium (requires skill and timing)
Risk: Medium (market could move against you)
Opportunity cost: Time spent monitoring markets
```

#### Strategy 4: Stake (Earn Passive Income)

```
Payoff:
- Stake 1,000 CC for 365 days
- Earn 40% return = +400 CC
- Total after 1 year: 1,400 CC

Expected value: +40% guaranteed (high)
Risk: Low (locked in return)
Opportunity cost: No liquidity for 1 year
```

### Dominant Strategy Analysis

**For most users, Strategy 2 (Spend) or Strategy 4 (Stake) dominates:**

```
If you need compute:
→ Spend is optimal (you get utility + bonuses)

If you don't need compute:
→ Stake is optimal (guaranteed return > hoarding)

Only if you're a skilled trader:
→ Trade might beat staking (but risky)

Hoarding is NEVER optimal:
→ Demurrage + opportunity cost + no bonuses = worst outcome
```

**System Design Goal Achieved:** Rational users prefer spending or staking over hoarding ✅

---

## Implementation Roadmap

### Phase 1: Foundation (Months 1-6)

**Features:**
- ✅ Velocity tracking (measure baseline)
- ✅ Basic withdrawal fees (5-8%)
- ✅ Simple achievements (spend milestones)
- ❌ No demurrage (too aggressive for MVP)

**Metrics:**
- Baseline velocity: 4-6 (typical for new platforms)
- Withdrawal rate: <20% of earned CC

### Phase 2: Incentives (Months 7-12)

**Features:**
- ✅ Velocity bonuses (tiered discounts)
- ✅ Staking system (30/90/180/365 day tiers)
- ✅ Soft demurrage (benefit loss, not balance loss)
- ✅ Achievement rewards

**Metrics:**
- Target velocity: 8-10
- Withdrawal rate: <15%
- Staking ratio: 20-30% of circulating supply

### Phase 3: Optimization (Months 13-24)

**Features:**
- ✅ Leaderboards and competitions
- ✅ Advanced gamification
- ✅ Hard demurrage (if velocity still low)
- ✅ Dynamic fee adjustments

**Metrics:**
- Target velocity: 10-12
- Withdrawal rate: <10%
- Staking ratio: 30-40%

---

## Conclusion

Circulation velocity is the lifeblood of the Compute Capital economy. By implementing:

1. **Soft demurrage** - Benefit loss (not balance loss) for inactivity
2. **Velocity bonuses** - Discounts for active spenders
3. **Staking rewards** - Guaranteed returns for long-term holders
4. **Progressive withdrawal fees** - Encourage batching and staying in-system
5. **Gamification** - Make CC usage engaging and fun

We create a system where the **rational strategy** is to **use CC** (not hoard or withdraw), leading to:

✅ High velocity (8-12 target)
✅ Thriving marketplace
✅ Sustainable platform revenue
✅ Network effects and growth

**See Also:**
- `compute-capital-currency-design.md` - Token fundamentals
- `internal-marketplace-design.md` - Trading mechanisms
- `timezone-arbitrage-system.md` - Utility-driven usage

---

**Document End**
