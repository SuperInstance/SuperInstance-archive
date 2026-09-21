# Fee Calculation Engine: Real-Time Implementation

**Research Focus:** Real-time fee calculation with transparent display
**Date:** October 14, 2025
**Objective:** Build accurate, transparent, real-time fee calculator for all membership tiers

---

## Executive Summary

This document provides production-ready code for calculating platform fees, membership costs, and withdrawal fees across all tiers. The engine handles progressive pricing (Premium tier's 1% → 0.1% structure), prorated membership fees, and real-time cost estimation similar to Uber's fare calculator.

**Key Features:**
- Real-time fee calculation as user consumes compute
- Transparent fee breakdown (no hidden costs)
- Automatic tier upgrade suggestions when cost-effective
- Prorated membership handling for mid-month changes
- Edge case coverage (refunds, credits, limits)

---

## 1. Core Fee Calculation Engine

### TypeScript Implementation

```typescript
/**
 * Fee Calculation Engine for Compute Marketplace
 * Handles all fee calculations across Free, Basic, and Premium tiers
 */

// Types and Interfaces
interface User {
  id: string;
  tier: 'free' | 'basic' | 'premium';
  membershipStartDate: Date;
  billingCycle: 'monthly' | 'annual';
  computeCapitalBalance: number;
  monthlySpendToDate: number;
}

interface ComputeJob {
  baseCost: number;          // Actual hardware cost
  duration: number;          // Hours
  resourceType: string;      // 'cpu', 'gpu-4090', 'gpu-h100', etc.
}

interface FeeBreakdown {
  baseCost: number;
  platformMarkup: number;
  platformMarkupRate: number;
  membershipFee: number;      // Prorated if applicable
  totalCost: number;
  effectiveFeeRate: number;   // As percentage
  savingsVsFreeTier: number;
  computeCapitalEarned: number;
  breakdown: {
    description: string;
    amount: number;
  }[];
}

interface WithdrawalFee {
  amount: number;
  fee: number;
  feeRate: number;
  netAmount: number;
  method: 'bank' | 'paypal' | 'instant';
  processingTime: string;
}

// Constants
const MEMBERSHIP_FEES = {
  free: 0,
  basic: 8,
  premium: 30
} as const;

const ANNUAL_DISCOUNT = 0.10; // 10% discount

const MARKUP_RATES = {
  free: 0.20,      // 20%
  basic: 0.05,     // 5%
  premium: {
    tier1: 0.01,   // 1% up to $200
    tier2: 0.001,  // 0.1% after $200
    threshold: 200
  }
} as const;

const WITHDRAWAL_FEES = {
  free: null,      // Cannot withdraw
  basic: 0.05,     // 5%
  premium: {
    tier1: 0.01,   // 1% up to $200
    tier2: 0.001,  // 0.1% after $200
    threshold: 200
  }
} as const;

/**
 * Calculate platform fee for a compute job
 */
function calculatePlatformFee(
  job: ComputeJob,
  user: User
): FeeBreakdown {
  const { baseCost } = job;
  const { tier, membershipStartDate, billingCycle, monthlySpendToDate } = user;

  let platformMarkup = 0;
  let platformMarkupRate = 0;
  const breakdown: { description: string; amount: number; }[] = [];

  // Calculate markup based on tier
  if (tier === 'free') {
    platformMarkupRate = MARKUP_RATES.free;
    platformMarkup = baseCost * platformMarkupRate;
    breakdown.push({
      description: 'Platform fee (20%)',
      amount: platformMarkup
    });
  } else if (tier === 'basic') {
    platformMarkupRate = MARKUP_RATES.basic;
    platformMarkup = baseCost * platformMarkupRate;
    breakdown.push({
      description: 'Platform fee (5%)',
      amount: platformMarkup
    });
  } else if (tier === 'premium') {
    // Progressive pricing for Premium tier
    const { tier1, tier2, threshold } = MARKUP_RATES.premium;
    const previousSpend = monthlySpendToDate;
    const newTotalSpend = previousSpend + baseCost;

    if (newTotalSpend <= threshold) {
      // Entirely in tier 1 (1% rate)
      platformMarkup = baseCost * tier1;
      platformMarkupRate = tier1;
      breakdown.push({
        description: `Platform fee (1% - under $${threshold})`,
        amount: platformMarkup
      });
    } else if (previousSpend >= threshold) {
      // Entirely in tier 2 (0.1% rate)
      platformMarkup = baseCost * tier2;
      platformMarkupRate = tier2;
      breakdown.push({
        description: `Platform fee (0.1% - over $${threshold})`,
        amount: platformMarkup
      });
    } else {
      // Split across both tiers
      const tier1Amount = threshold - previousSpend;
      const tier2Amount = baseCost - tier1Amount;
      const tier1Fee = tier1Amount * tier1;
      const tier2Fee = tier2Amount * tier2;
      platformMarkup = tier1Fee + tier2Fee;
      platformMarkupRate = platformMarkup / baseCost;

      breakdown.push({
        description: `Platform fee (1% on first $${tier1Amount.toFixed(2)})`,
        amount: tier1Fee
      });
      breakdown.push({
        description: `Platform fee (0.1% on remaining $${tier2Amount.toFixed(2)})`,
        amount: tier2Fee
      });
    }
  }

  // Calculate prorated membership fee (if applicable)
  const membershipFee = calculateProratedMembership(user);
  if (membershipFee > 0) {
    breakdown.push({
      description: `${tier.charAt(0).toUpperCase() + tier.slice(1)} membership (prorated)`,
      amount: membershipFee
    });
  }

  // Calculate totals
  const totalCost = baseCost + platformMarkup + membershipFee;
  const effectiveFeeRate = ((totalCost - baseCost) / baseCost) * 100;

  // Calculate savings vs Free tier
  const freeTierCost = baseCost * (1 + MARKUP_RATES.free);
  const savingsVsFreeTier = Math.max(0, freeTierCost - totalCost);

  // Compute Capital earned (equals platform markup)
  const computeCapitalEarned = platformMarkup;

  return {
    baseCost,
    platformMarkup,
    platformMarkupRate,
    membershipFee,
    totalCost,
    effectiveFeeRate,
    savingsVsFreeTier,
    computeCapitalEarned,
    breakdown
  };
}

/**
 * Calculate prorated membership fee
 * Only charges when membership fee is due (monthly or annual)
 */
function calculateProratedMembership(user: User): number {
  if (user.tier === 'free') return 0;

  const now = new Date();
  const startDate = user.membershipStartDate;
  const monthsSinceMembership =
    (now.getFullYear() - startDate.getFullYear()) * 12 +
    (now.getMonth() - startDate.getMonth());

  // Check if membership fee is due this month
  if (user.billingCycle === 'monthly') {
    // Charge monthly fee (already paid if membership active)
    return 0; // Fee handled separately by billing system
  } else {
    // Annual billing
    if (monthsSinceMembership % 12 === 0) {
      return 0; // Fee handled separately by billing system
    }
    return 0;
  }

  // Note: Membership fees are handled by separate billing system
  // This function is for display purposes only
}

/**
 * Calculate withdrawal fee and net amount
 */
function calculateWithdrawalFee(
  amount: number,
  user: User,
  method: 'bank' | 'paypal' | 'instant' = 'bank'
): WithdrawalFee {
  const { tier, monthlySpendToDate } = user;

  if (tier === 'free') {
    throw new Error('Free tier users cannot withdraw Compute Capital as cash');
  }

  let feeRate = 0;
  let fee = 0;
  let processingTime = '1-3 business days';

  // Calculate base withdrawal fee
  if (tier === 'basic') {
    feeRate = WITHDRAWAL_FEES.basic;
    fee = amount * feeRate;
  } else if (tier === 'premium') {
    const { tier1, tier2, threshold } = WITHDRAWAL_FEES.premium;

    if (amount <= threshold) {
      feeRate = tier1;
      fee = amount * feeRate;
    } else {
      const tier1Amount = threshold;
      const tier2Amount = amount - threshold;
      const tier1Fee = tier1Amount * tier1;
      const tier2Fee = tier2Amount * tier2;
      fee = tier1Fee + tier2Fee;
      feeRate = fee / amount; // Effective rate
    }
  }

  // Add method-specific fees
  let methodFee = 0;
  if (method === 'paypal') {
    methodFee = 0; // PayPal doesn't charge from platform side
    processingTime = '1-2 business days';
  } else if (method === 'instant') {
    methodFee = amount * 0.0175; // 1.75% instant transfer fee (PayPal/Stripe)
    processingTime = '30 minutes or less';
  }

  const totalFee = fee + methodFee;
  const netAmount = amount - totalFee;

  return {
    amount,
    fee: totalFee,
    feeRate: totalFee / amount,
    netAmount,
    method,
    processingTime
  };
}

/**
 * Real-time running total calculator
 * Shows user their current month costs as they use compute
 */
function calculateMonthToDateTotal(user: User): {
  totalSpent: number;
  platformFeesTotal: number;
  membershipFee: number;
  computeCapitalEarned: number;
  projectedMonthEnd: number;
  suggestedTier: 'free' | 'basic' | 'premium' | null;
  potentialSavings: number;
} {
  const now = new Date();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const dayOfMonth = now.getDate();
  const daysRemaining = daysInMonth - dayOfMonth;

  const totalSpent = user.monthlySpendToDate;

  // Calculate membership fee
  const membershipFee = user.tier === 'free' ? 0 :
    user.billingCycle === 'monthly' ? MEMBERSHIP_FEES[user.tier] :
    MEMBERSHIP_FEES[user.tier] * (1 - ANNUAL_DISCOUNT) / 12;

  // Platform fees already paid this month
  let platformFeesTotal = 0;
  if (user.tier === 'free') {
    platformFeesTotal = totalSpent * MARKUP_RATES.free;
  } else if (user.tier === 'basic') {
    platformFeesTotal = totalSpent * MARKUP_RATES.basic;
  } else if (user.tier === 'premium') {
    const { tier1, tier2, threshold } = MARKUP_RATES.premium;
    if (totalSpent <= threshold) {
      platformFeesTotal = totalSpent * tier1;
    } else {
      platformFeesTotal = threshold * tier1 + (totalSpent - threshold) * tier2;
    }
  }

  // Compute Capital earned (equals platform fees for providers)
  const computeCapitalEarned = platformFeesTotal;

  // Project month-end spend (simple linear projection)
  const dailyAverage = totalSpent / dayOfMonth;
  const projectedMonthEnd = dailyAverage * daysInMonth;

  // Suggest optimal tier
  const { suggestedTier, potentialSavings } = suggestOptimalTier(
    projectedMonthEnd,
    user.tier
  );

  return {
    totalSpent: totalSpent + membershipFee,
    platformFeesTotal,
    membershipFee,
    computeCapitalEarned,
    projectedMonthEnd,
    suggestedTier,
    potentialSavings
  };
}

/**
 * Suggest optimal tier based on usage
 */
function suggestOptimalTier(
  monthlySpend: number,
  currentTier: 'free' | 'basic' | 'premium'
): {
  suggestedTier: 'free' | 'basic' | 'premium' | null;
  potentialSavings: number;
} {
  // Calculate cost for each tier
  const freeCost = monthlySpend * (1 + MARKUP_RATES.free);
  const basicCost = monthlySpend * (1 + MARKUP_RATES.basic) + MEMBERSHIP_FEES.basic;

  let premiumCost: number;
  const { tier1, tier2, threshold } = MARKUP_RATES.premium;
  if (monthlySpend <= threshold) {
    premiumCost = monthlySpend * (1 + tier1) + MEMBERSHIP_FEES.premium;
  } else {
    const tier1Cost = threshold * (1 + tier1);
    const tier2Cost = (monthlySpend - threshold) * (1 + tier2);
    premiumCost = tier1Cost + tier2Cost + MEMBERSHIP_FEES.premium;
  }

  // Find cheapest tier
  const costs = [
    { tier: 'free' as const, cost: freeCost },
    { tier: 'basic' as const, cost: basicCost },
    { tier: 'premium' as const, cost: premiumCost }
  ];

  costs.sort((a, b) => a.cost - b.cost);
  const optimal = costs[0];
  const current = costs.find(c => c.tier === currentTier)!;

  if (optimal.tier === currentTier) {
    return { suggestedTier: null, potentialSavings: 0 };
  }

  return {
    suggestedTier: optimal.tier,
    potentialSavings: current.cost - optimal.cost
  };
}

/**
 * Calculate tier upgrade/downgrade impact
 * Used when user wants to change tier mid-month
 */
function calculateTierChangeImpact(
  user: User,
  newTier: 'free' | 'basic' | 'premium'
): {
  creditFromCurrentTier: number;
  costForNewTier: number;
  netCost: number;
  effectiveDate: Date;
  impactOnComputeCapital: string;
  warnings: string[];
} {
  const now = new Date();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const dayOfMonth = now.getDate();
  const daysRemaining = daysInMonth - dayOfMonth;

  const warnings: string[] = [];

  // Calculate prorated credit from current tier
  let creditFromCurrentTier = 0;
  if (user.tier !== 'free' && user.billingCycle === 'monthly') {
    const monthlyFee = MEMBERSHIP_FEES[user.tier];
    const dailyRate = monthlyFee / daysInMonth;
    creditFromCurrentTier = dailyRate * daysRemaining;
  }

  // Calculate prorated cost for new tier
  let costForNewTier = 0;
  if (newTier !== 'free') {
    const monthlyFee = MEMBERSHIP_FEES[newTier];
    const dailyRate = monthlyFee / daysInMonth;
    costForNewTier = dailyRate * daysRemaining;
  }

  const netCost = costForNewTier - creditFromCurrentTier;

  // Check Compute Capital impact
  let impactOnComputeCapital = 'No impact';
  if (user.tier !== 'free' && newTier === 'free') {
    impactOnComputeCapital = 'Your Compute Capital will be LOCKED. You cannot withdraw it as cash.';
    warnings.push(
      `⚠️ Downgrading to Free tier will lock your $${user.computeCapitalBalance.toFixed(2)} Compute Capital.`,
      'You will only be able to use it for compute, not cash withdrawal.'
    );
  }

  if (newTier !== 'free' && user.computeCapitalBalance > 0 && user.tier === 'free') {
    impactOnComputeCapital = `Your $${user.computeCapitalBalance.toFixed(2)} Compute Capital will be UNLOCKED for cash withdrawal!`;
  }

  // Warn about tier changes
  if (newTier === 'free' && user.monthlySpendToDate > 40) {
    warnings.push(
      `💡 Based on your usage ($${user.monthlySpendToDate.toFixed(2)} this month), ` +
      `you'd save money with Basic tier ($8/month, 5% fees).`
    );
  }

  if (newTier === 'basic' && user.monthlySpendToDate > 200) {
    warnings.push(
      `💡 Based on your usage ($${user.monthlySpendToDate.toFixed(2)} this month), ` +
      `you'd save significantly with Premium tier ($30/month, 0.1% fees after $200).`
    );
  }

  return {
    creditFromCurrentTier,
    costForNewTier,
    netCost,
    effectiveDate: now,
    impactOnComputeCapital,
    warnings
  };
}

// Export all functions
export {
  calculatePlatformFee,
  calculateWithdrawalFee,
  calculateMonthToDateTotal,
  suggestOptimalTier,
  calculateTierChangeImpact,
  type FeeBreakdown,
  type WithdrawalFee,
  type User,
  type ComputeJob
};
```

---

## 2. Python Implementation (Alternative)

```python
"""
Fee Calculation Engine for Compute Marketplace
Python implementation for backend services
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Optional, List, Dict
from decimal import Decimal

# Type definitions
TierType = Literal['free', 'basic', 'premium']
BillingCycle = Literal['monthly', 'annual']
WithdrawalMethod = Literal['bank', 'paypal', 'instant']

# Constants
MEMBERSHIP_FEES = {
    'free': Decimal('0'),
    'basic': Decimal('8'),
    'premium': Decimal('30')
}

ANNUAL_DISCOUNT = Decimal('0.10')  # 10%

MARKUP_RATES = {
    'free': Decimal('0.20'),
    'basic': Decimal('0.05'),
    'premium': {
        'tier1': Decimal('0.01'),
        'tier2': Decimal('0.001'),
        'threshold': Decimal('200')
    }
}

WITHDRAWAL_FEES = {
    'free': None,
    'basic': Decimal('0.05'),
    'premium': {
        'tier1': Decimal('0.01'),
        'tier2': Decimal('0.001'),
        'threshold': Decimal('200')
    }
}

@dataclass
class User:
    id: str
    tier: TierType
    membership_start_date: datetime
    billing_cycle: BillingCycle
    compute_capital_balance: Decimal
    monthly_spend_to_date: Decimal

@dataclass
class ComputeJob:
    base_cost: Decimal
    duration: float  # hours
    resource_type: str

@dataclass
class FeeBreakdown:
    base_cost: Decimal
    platform_markup: Decimal
    platform_markup_rate: Decimal
    membership_fee: Decimal
    total_cost: Decimal
    effective_fee_rate: Decimal
    savings_vs_free_tier: Decimal
    compute_capital_earned: Decimal
    breakdown: List[Dict[str, any]]

@dataclass
class WithdrawalFee:
    amount: Decimal
    fee: Decimal
    fee_rate: Decimal
    net_amount: Decimal
    method: WithdrawalMethod
    processing_time: str


def calculate_platform_fee(job: ComputeJob, user: User) -> FeeBreakdown:
    """Calculate platform fee for a compute job"""
    base_cost = job.base_cost
    tier = user.tier
    monthly_spend = user.monthly_spend_to_date

    platform_markup = Decimal('0')
    platform_markup_rate = Decimal('0')
    breakdown = []

    # Calculate markup based on tier
    if tier == 'free':
        platform_markup_rate = MARKUP_RATES['free']
        platform_markup = base_cost * platform_markup_rate
        breakdown.append({
            'description': 'Platform fee (20%)',
            'amount': float(platform_markup)
        })

    elif tier == 'basic':
        platform_markup_rate = MARKUP_RATES['basic']
        platform_markup = base_cost * platform_markup_rate
        breakdown.append({
            'description': 'Platform fee (5%)',
            'amount': float(platform_markup)
        })

    elif tier == 'premium':
        # Progressive pricing for Premium tier
        tier1_rate = MARKUP_RATES['premium']['tier1']
        tier2_rate = MARKUP_RATES['premium']['tier2']
        threshold = MARKUP_RATES['premium']['threshold']

        previous_spend = monthly_spend
        new_total_spend = previous_spend + base_cost

        if new_total_spend <= threshold:
            # Entirely in tier 1
            platform_markup = base_cost * tier1_rate
            platform_markup_rate = tier1_rate
            breakdown.append({
                'description': f'Platform fee (1% - under ${threshold})',
                'amount': float(platform_markup)
            })
        elif previous_spend >= threshold:
            # Entirely in tier 2
            platform_markup = base_cost * tier2_rate
            platform_markup_rate = tier2_rate
            breakdown.append({
                'description': f'Platform fee (0.1% - over ${threshold})',
                'amount': float(platform_markup)
            })
        else:
            # Split across both tiers
            tier1_amount = threshold - previous_spend
            tier2_amount = base_cost - tier1_amount
            tier1_fee = tier1_amount * tier1_rate
            tier2_fee = tier2_amount * tier2_rate
            platform_markup = tier1_fee + tier2_fee
            platform_markup_rate = platform_markup / base_cost

            breakdown.append({
                'description': f'Platform fee (1% on first ${tier1_amount:.2f})',
                'amount': float(tier1_fee)
            })
            breakdown.append({
                'description': f'Platform fee (0.1% on remaining ${tier2_amount:.2f})',
                'amount': float(tier2_fee)
            })

    # Membership fee (handled separately by billing system)
    membership_fee = Decimal('0')

    # Calculate totals
    total_cost = base_cost + platform_markup + membership_fee
    effective_fee_rate = ((total_cost - base_cost) / base_cost) * 100

    # Savings vs Free tier
    free_tier_cost = base_cost * (1 + MARKUP_RATES['free'])
    savings_vs_free = max(Decimal('0'), free_tier_cost - total_cost)

    # Compute Capital earned
    compute_capital_earned = platform_markup

    return FeeBreakdown(
        base_cost=base_cost,
        platform_markup=platform_markup,
        platform_markup_rate=platform_markup_rate,
        membership_fee=membership_fee,
        total_cost=total_cost,
        effective_fee_rate=effective_fee_rate,
        savings_vs_free_tier=savings_vs_free,
        compute_capital_earned=compute_capital_earned,
        breakdown=breakdown
    )


def calculate_withdrawal_fee(
    amount: Decimal,
    user: User,
    method: WithdrawalMethod = 'bank'
) -> WithdrawalFee:
    """Calculate withdrawal fee and net amount"""

    if user.tier == 'free':
        raise ValueError('Free tier users cannot withdraw Compute Capital as cash')

    fee_rate = Decimal('0')
    fee = Decimal('0')
    processing_time = '1-3 business days'

    # Calculate base withdrawal fee
    if user.tier == 'basic':
        fee_rate = WITHDRAWAL_FEES['basic']
        fee = amount * fee_rate

    elif user.tier == 'premium':
        tier1_rate = WITHDRAWAL_FEES['premium']['tier1']
        tier2_rate = WITHDRAWAL_FEES['premium']['tier2']
        threshold = WITHDRAWAL_FEES['premium']['threshold']

        if amount <= threshold:
            fee_rate = tier1_rate
            fee = amount * fee_rate
        else:
            tier1_amount = threshold
            tier2_amount = amount - threshold
            tier1_fee = tier1_amount * tier1_rate
            tier2_fee = tier2_amount * tier2_rate
            fee = tier1_fee + tier2_fee
            fee_rate = fee / amount

    # Add method-specific fees
    method_fee = Decimal('0')
    if method == 'paypal':
        processing_time = '1-2 business days'
    elif method == 'instant':
        method_fee = amount * Decimal('0.0175')  # 1.75%
        processing_time = '30 minutes or less'

    total_fee = fee + method_fee
    net_amount = amount - total_fee

    return WithdrawalFee(
        amount=amount,
        fee=total_fee,
        fee_rate=total_fee / amount,
        net_amount=net_amount,
        method=method,
        processing_time=processing_time
    )


def suggest_optimal_tier(
    monthly_spend: Decimal,
    current_tier: TierType
) -> tuple[Optional[TierType], Decimal]:
    """Suggest optimal tier based on usage"""

    # Calculate cost for each tier
    free_cost = monthly_spend * (1 + MARKUP_RATES['free'])
    basic_cost = monthly_spend * (1 + MARKUP_RATES['basic']) + MEMBERSHIP_FEES['basic']

    # Premium calculation
    tier1_rate = MARKUP_RATES['premium']['tier1']
    tier2_rate = MARKUP_RATES['premium']['tier2']
    threshold = MARKUP_RATES['premium']['threshold']

    if monthly_spend <= threshold:
        premium_cost = monthly_spend * (1 + tier1_rate) + MEMBERSHIP_FEES['premium']
    else:
        tier1_cost = threshold * (1 + tier1_rate)
        tier2_cost = (monthly_spend - threshold) * (1 + tier2_rate)
        premium_cost = tier1_cost + tier2_cost + MEMBERSHIP_FEES['premium']

    # Find cheapest
    costs = [
        ('free', free_cost),
        ('basic', basic_cost),
        ('premium', premium_cost)
    ]
    costs.sort(key=lambda x: x[1])

    optimal_tier, optimal_cost = costs[0]
    current_cost = next(cost for tier, cost in costs if tier == current_tier)

    if optimal_tier == current_tier:
        return None, Decimal('0')

    return optimal_tier, current_cost - optimal_cost
```

---

## 3. Real-Time Fee Display (Frontend Components)

### React Component Example

```tsx
import React, { useState, useEffect } from 'react';
import { calculatePlatformFee, calculateMonthToDateTotal } from './feeCalculator';

interface JobCostEstimatorProps {
  baseCost: number;
  user: User;
  onEstimateUpdate: (estimate: FeeBreakdown) => void;
}

/**
 * Real-time job cost estimator
 * Shows fee breakdown as user configures job
 */
const JobCostEstimator: React.FC<JobCostEstimatorProps> = ({
  baseCost,
  user,
  onEstimateUpdate
}) => {
  const [estimate, setEstimate] = useState<FeeBreakdown | null>(null);

  useEffect(() => {
    const job: ComputeJob = { baseCost, duration: 1, resourceType: 'gpu' };
    const breakdown = calculatePlatformFee(job, user);
    setEstimate(breakdown);
    onEstimateUpdate(breakdown);
  }, [baseCost, user]);

  if (!estimate) return <div>Calculating...</div>;

  return (
    <div className="fee-estimator">
      <h3>Cost Estimate</h3>

      <div className="cost-breakdown">
        <div className="line-item">
          <span>Base compute cost:</span>
          <span>${estimate.baseCost.toFixed(2)}</span>
        </div>

        {estimate.breakdown.map((item, idx) => (
          <div key={idx} className="line-item sub-item">
            <span>{item.description}</span>
            <span>+${item.amount.toFixed(2)}</span>
          </div>
        ))}

        <div className="line-item total">
          <span><strong>Total cost:</strong></span>
          <span><strong>${estimate.totalCost.toFixed(2)}</strong></span>
        </div>

        <div className="line-item savings">
          <span>Savings vs Free tier:</span>
          <span className="positive">-${estimate.savingsVsFreeTier.toFixed(2)}</span>
        </div>
      </div>

      <div className="compute-capital-earned">
        <p>💰 You'll earn ${estimate.computeCapitalEarned.toFixed(2)} in Compute Capital</p>
      </div>

      {estimate.effectiveFeeRate < 10 && (
        <div className="optimization-tip">
          <p>✨ Great value! Effective fee rate: {estimate.effectiveFeeRate.toFixed(2)}%</p>
        </div>
      )}
    </div>
  );
};

/**
 * Monthly usage dashboard
 * Shows running total and suggests tier upgrades
 */
const MonthlyUsageDashboard: React.FC<{ user: User }> = ({ user }) => {
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const monthStats = calculateMonthToDateTotal(user);
    setStats(monthStats);
  }, [user]);

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="usage-dashboard">
      <h2>This Month's Usage</h2>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Spent</div>
          <div className="stat-value">${stats.totalSpent.toFixed(2)}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Platform Fees</div>
          <div className="stat-value">${stats.platformFeesTotal.toFixed(2)}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Compute Capital Earned</div>
          <div className="stat-value">${stats.computeCapitalEarned.toFixed(2)}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Projected Month-End</div>
          <div className="stat-value">${stats.projectedMonthEnd.toFixed(2)}</div>
        </div>
      </div>

      {stats.suggestedTier && (
        <div className="tier-suggestion">
          <h3>💡 Optimization Suggestion</h3>
          <p>
            Based on your usage, you could save <strong>${stats.potentialSavings.toFixed(2)}/month</strong>
            {' '}by upgrading to <strong>{stats.suggestedTier.toUpperCase()}</strong> tier!
          </p>
          <button className="btn-primary">Upgrade Now</button>
        </div>
      )}

      {!stats.suggestedTier && (
        <div className="tier-optimal">
          <p>✅ You're on the optimal tier for your usage level!</p>
        </div>
      )}
    </div>
  );
};

export { JobCostEstimator, MonthlyUsageDashboard };
```

---

## 4. Edge Cases & Handling

### Edge Case 1: Mid-Month Tier Change

**Scenario:** User upgrades from Basic to Premium on day 15 of 30-day month.

**Solution:**
```typescript
// Prorate both tiers
const daysRemaining = 15;
const daysInMonth = 30;

const basicRefund = (MEMBERSHIP_FEES.basic / daysInMonth) * daysRemaining;
// = ($8 / 30) * 15 = $4

const premiumCharge = (MEMBERSHIP_FEES.premium / daysInMonth) * daysRemaining;
// = ($30 / 30) * 15 = $15

const netCharge = premiumCharge - basicRefund;
// = $15 - $4 = $11

// User pays $11 to upgrade for remaining 15 days
```

### Edge Case 2: Refund Request Within 30 Days

**Scenario:** User requests refund of Basic membership 10 days after subscribing.

**Policy:**
- Full refund if <7 days and <$50 compute usage
- Prorated refund if 7-30 days
- No refund if >30 days

**Implementation:**
```typescript
function calculateRefund(user: User, cancelDate: Date): number {
  const daysSinceMembership =
    (cancelDate.getTime() - user.membershipStartDate.getTime()) / (1000 * 60 * 60 * 24);

  if (daysSinceMembership < 7 && user.monthlySpendToDate < 50) {
    // Full refund
    return MEMBERSHIP_FEES[user.tier];
  } else if (daysSinceMembership <= 30) {
    // Prorated refund
    const daysInMonth = 30;
    const daysRemaining = daysInMonth - daysSinceMembership;
    const dailyRate = MEMBERSHIP_FEES[user.tier] / daysInMonth;
    return dailyRate * daysRemaining;
  } else {
    // No refund
    return 0;
  }
}
```

### Edge Case 3: Premium User Crosses $200 Threshold Mid-Job

**Scenario:** User at $180 spend starts a $40 job.

**Solution:**
```typescript
// Previous spend: $180
// New job: $40
// Total: $220

// Split calculation:
// First $20 of job at 1% (to reach $200 threshold)
// Remaining $20 of job at 0.1%

const tier1Portion = 200 - 180; // $20
const tier2Portion = 40 - tier1Portion; // $20

const tier1Fee = tier1Portion * 0.01; // $0.20
const tier2Fee = tier2Portion * 0.001; // $0.02

const totalFee = tier1Fee + tier2Fee; // $0.22

// Breakdown displayed to user:
// "Platform fee (1% on first $20.00): $0.20"
// "Platform fee (0.1% on remaining $20.00): $0.02"
```

### Edge Case 4: Annual Subscriber Cancels Mid-Year

**Scenario:** User paid $324 annual Premium, cancels after 6 months.

**Policy:**
- No refunds on annual subscriptions
- Service continues until end of paid period
- Can downgrade effective next billing cycle

**Implementation:**
```typescript
function handleAnnualCancellation(user: User, cancelDate: Date): {
  refundAmount: number;
  serviceEndsOn: Date;
  message: string;
} {
  if (user.billingCycle !== 'annual') {
    throw new Error('Not an annual subscription');
  }

  const anniversaryDate = new Date(user.membershipStartDate);
  anniversaryDate.setFullYear(anniversaryDate.getFullYear() + 1);

  return {
    refundAmount: 0,
    serviceEndsOn: anniversaryDate,
    message: `Your ${user.tier.toUpperCase()} membership will remain active until ${anniversaryDate.toLocaleDateString()}. No refund is provided for annual subscriptions.`
  };
}
```

### Edge Case 5: Withdrawal Amount Exceeds Balance

**Scenario:** User tries to withdraw $500 but only has $400 Compute Capital.

**Solution:**
```typescript
function validateWithdrawal(amount: number, balance: number): void {
  if (amount > balance) {
    throw new Error(
      `Insufficient Compute Capital balance. ` +
      `Requested: $${amount.toFixed(2)}, ` +
      `Available: $${balance.toFixed(2)}`
    );
  }

  if (amount < 10) {
    throw new Error('Minimum withdrawal amount is $10');
  }

  if (amount > 10000) {
    throw new Error('Maximum single withdrawal is $10,000. Contact support for larger withdrawals.');
  }
}
```

### Edge Case 6: Negative Compute Capital Balance

**Scenario:** System error causes negative balance.

**Solution:**
```typescript
function reconcileNegativeBalance(user: User): void {
  if (user.computeCapitalBalance < 0) {
    console.error(`User ${user.id} has negative balance: ${user.computeCapitalBalance}`);

    // Alert finance team
    notifyFinanceTeam({
      userId: user.id,
      balance: user.computeCapitalBalance,
      severity: 'high'
    });

    // Prevent withdrawals until resolved
    lockWithdrawals(user.id);

    // Show user message
    showUserMessage(
      user.id,
      'Your account is under review. Withdrawals temporarily disabled. Support has been notified.'
    );
  }
}
```

---

## 5. Testing & Validation

### Unit Tests (Jest/TypeScript)

```typescript
import { describe, test, expect } from '@jest/globals';
import { calculatePlatformFee, suggestOptimalTier } from './feeCalculator';

describe('Fee Calculator', () => {
  test('Free tier: 20% markup', () => {
    const user: User = {
      id: '1',
      tier: 'free',
      membershipStartDate: new Date(),
      billingCycle: 'monthly',
      computeCapitalBalance: 0,
      monthlySpendToDate: 0
    };

    const job: ComputeJob = { baseCost: 100, duration: 1, resourceType: 'cpu' };
    const result = calculatePlatformFee(job, user);

    expect(result.platformMarkup).toBe(20);
    expect(result.totalCost).toBe(120);
    expect(result.effectiveFeeRate).toBe(20);
  });

  test('Basic tier: 5% markup + $8 membership', () => {
    const user: User = {
      id: '2',
      tier: 'basic',
      membershipStartDate: new Date(),
      billingCycle: 'monthly',
      computeCapitalBalance: 50,
      monthlySpendToDate: 100
    };

    const job: ComputeJob = { baseCost: 100, duration: 1, resourceType: 'cpu' };
    const result = calculatePlatformFee(job, user);

    expect(result.platformMarkup).toBe(5);
    // Membership fee handled separately
    expect(result.baseCost + result.platformMarkup).toBe(105);
  });

  test('Premium tier: Progressive rates', () => {
    const user: User = {
      id: '3',
      tier: 'premium',
      membershipStartDate: new Date(),
      billingCycle: 'monthly',
      computeCapitalBalance: 200,
      monthlySpendToDate: 180 // Close to $200 threshold
    };

    const job: ComputeJob = { baseCost: 40, duration: 1, resourceType: 'gpu' };
    const result = calculatePlatformFee(job, user);

    // $20 at 1% + $20 at 0.1%
    // = $0.20 + $0.02 = $0.22
    expect(result.platformMarkup).toBeCloseTo(0.22, 2);
  });

  test('Tier suggestion: Free → Basic at $40+', () => {
    const [suggestedTier, savings] = suggestOptimalTier(50, 'free');

    expect(suggestedTier).toBe('basic');
    expect(savings).toBeGreaterThan(0);
  });

  test('Tier suggestion: Basic → Premium at $200+', () => {
    const [suggestedTier, savings] = suggestOptimalTier(500, 'basic');

    expect(suggestedTier).toBe('premium');
    expect(savings).toBeGreaterThan(300);
  });
});
```

---

## 6. Integration with Billing System

### Stripe Integration Example

```typescript
import Stripe from 'stripe';
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

/**
 * Create or update subscription when user changes tier
 */
async function updateUserSubscription(
  userId: string,
  newTier: 'basic' | 'premium',
  billingCycle: 'monthly' | 'annual'
): Promise<void> {
  const user = await getUserFromDatabase(userId);

  // Determine price ID
  let priceId: string;
  if (newTier === 'basic') {
    priceId = billingCycle === 'monthly'
      ? process.env.STRIPE_BASIC_MONTHLY_PRICE_ID!
      : process.env.STRIPE_BASIC_ANNUAL_PRICE_ID!;
  } else {
    priceId = billingCycle === 'monthly'
      ? process.env.STRIPE_PREMIUM_MONTHLY_PRICE_ID!
      : process.env.STRIPE_PREMIUM_ANNUAL_PRICE_ID!;
  }

  if (!user.stripeSubscriptionId) {
    // Create new subscription
    const subscription = await stripe.subscriptions.create({
      customer: user.stripeCustomerId,
      items: [{ price: priceId }],
      proration_behavior: 'create_prorations',
      metadata: {
        userId,
        tier: newTier
      }
    });

    await updateDatabaseSubscription(userId, subscription.id, newTier);
  } else {
    // Update existing subscription
    const subscription = await stripe.subscriptions.retrieve(user.stripeSubscriptionId);

    await stripe.subscriptions.update(user.stripeSubscriptionId, {
      items: [{
        id: subscription.items.data[0].id,
        price: priceId
      }],
      proration_behavior: 'create_prorations'
    });

    await updateDatabaseSubscription(userId, subscription.id, newTier);
  }
}

/**
 * Handle successful payment
 */
async function handlePaymentSuccess(
  userId: string,
  amount: number,
  tier: 'basic' | 'premium'
): Promise<void> {
  await updateDatabaseMembershipStatus(userId, {
    tier,
    membershipActive: true,
    lastPaymentDate: new Date(),
    lastPaymentAmount: amount
  });

  // Send confirmation email
  await sendEmail(userId, {
    template: 'membership_confirmed',
    data: { tier, amount }
  });
}
```

---

## 7. Key Recommendations

### Implementation Priority

**Phase 1 (MVP):**
1. Core fee calculation (Free, Basic, Premium)
2. Real-time job cost estimator
3. Monthly usage dashboard
4. Basic tier suggestions

**Phase 2 (Production):**
1. Withdrawal fee calculator
2. Prorated membership handling
3. Tier change impact calculator
4. Advanced analytics

**Phase 3 (Optimization):**
1. Predictive tier recommendations (ML-based)
2. Custom pricing rules for enterprise
3. A/B testing for tier thresholds
4. Dynamic fee optimization

### Transparency Best Practices

1. **Always show fee breakdown** (never just total)
2. **Explain each line item** (plain English)
3. **Show savings vs alternatives** (comparison)
4. **Display Compute Capital earned** (positive framing)
5. **Warn before costly actions** (tier downgrades)

### Performance Optimization

1. **Cache calculations** (same user, same job = same result)
2. **Batch database updates** (don't update on every cent)
3. **Use Decimal/BigDecimal** (avoid floating point errors)
4. **Async notifications** (don't block on tier suggestions)

---

## Conclusion

This fee calculation engine provides production-ready code for accurately calculating all platform fees, membership costs, and withdrawal fees. Key features include:

- **Real-time calculation** as users consume compute
- **Transparent breakdown** of all fees
- **Automatic tier suggestions** at optimal breakpoints
- **Prorated handling** for mid-cycle changes
- **Comprehensive edge case coverage**

The engine integrates with Stripe for billing and provides both TypeScript and Python implementations for flexibility across tech stacks.

**Next Steps:**
1. Implement withdrawal system (see withdrawal-system-design.md)
2. Design tier migration UX (see tier-migration-optimization.md)
3. Build analytics dashboard (see membership-analytics.md)
