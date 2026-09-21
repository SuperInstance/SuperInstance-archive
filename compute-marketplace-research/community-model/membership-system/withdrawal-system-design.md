# Withdrawal System Design

**Research Focus:** Withdrawal/payout system for Compute Capital
**Date:** October 14, 2025
**Objective:** Design secure, user-friendly withdrawal system with fraud prevention

---

## Executive Summary

Based on research of YouTube Partner, Twitch, Upwork, Fiverr, PayPal, and Stripe payout systems, the recommended withdrawal structure is:

**MINIMUM THRESHOLD:** $10 (balance accessibility, reduce micro-withdrawals)
**MAXIMUM LIMITS:** $10,000/transaction, $50,000/month (fraud prevention)
**PROCESSING TIME:** 1-3 days standard, 30min instant (+1.75% fee)
**WITHDRAWAL FEES:** Tier-based (Free: locked, Basic: 5%, Premium: 1% → 0.1%)
**FRAUD PREVENTION:** KYC verification, velocity checks, withdrawal holds

---

## 1. Withdrawal Flow & UX

### User Withdrawal Interface

```
┌─────────────────────────────────────────────────────────────┐
│  Withdraw Compute Capital                                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Available Balance: $450.00                                 │
│                                                              │
│  Amount to withdraw: [$__________]  [Max]                   │
│                                                              │
│  Withdrawal Method:                                         │
│  ◉ Bank Transfer (ACH) - Free, 1-3 business days          │
│  ○ PayPal - Free, 1-2 business days                        │
│  ○ Instant Transfer - 1.75% fee, 30 minutes               │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Fee Breakdown:                                         │ │
│  │ Withdrawal amount:        $100.00                      │ │
│  │ Platform fee (1%):         -$1.00                      │ │
│  │ Instant transfer fee:       $0.00                      │ │
│  │ ────────────────────────────────                      │ │
│  │ You'll receive:           $99.00                       │ │
│  │ Estimated arrival: Thu, Oct 17                        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
│  [Cancel]                          [Withdraw $100.00]       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Withdrawal Methods Comparison

| Method | Fee | Processing Time | Limits | Requirements |
|--------|-----|-----------------|--------|--------------|
| **ACH (Bank)** | Free | 1-3 business days | $10-$10K | Bank account verified |
| **PayPal** | Free | 1-2 business days | $1-$10K | PayPal account linked |
| **Instant** | 1.75% | 30 minutes | $10-$1K | Debit card on file |
| **Wire** | $20 flat | Same day | $1K-$50K | For large amounts only |

---

## 2. Withdrawal Limits & Thresholds

### Research-Based Benchmarks

**YouTube Partner Program:**
- Minimum: $100
- Processing: 21st-26th each month
- Hold period: 45-60 days for new accounts

**Twitch:**
- Minimum: $50 (ACH, PayPal), $100 (wire)
- Processing: 15 days after month end
- Processor fee deducted

**Upwork:**
- Minimum: None (can withdraw any amount)
- Fees: Free (ACH), $0.99 (local bank), $2 (instant), $50 (wire)
- $100 minimum for automatic withdrawals

**Fiverr:**
- Minimum: $1 (PayPal/bank), $30 (Fiverr Revenue Card)
- Fees: $0 (PayPal), $1 (standard), $3 (instant)
- Clearing period: 7-14 days based on seller level

### Recommended Limits for Compute Marketplace

```typescript
const WITHDRAWAL_LIMITS = {
  // Minimum thresholds
  minimum: {
    bank: 10,         // $10 minimum
    paypal: 10,
    instant: 10,
    wire: 1000        // $1K minimum for wire
  },

  // Maximum per transaction
  perTransaction: {
    bank: 10000,      // $10K max
    paypal: 10000,
    instant: 1000,    // $1K max for instant (risk mitigation)
    wire: 50000       // $50K max
  },

  // Daily limits (fraud prevention)
  daily: {
    free: 0,          // Cannot withdraw
    basic: 1000,      // $1K/day
    premium: 5000     // $5K/day
  },

  // Monthly limits
  monthly: {
    free: 0,
    basic: 10000,     // $10K/month
    premium: 50000    // $50K/month
  }
};
```

**Rationale:**
- $10 minimum balances accessibility with processing costs
- Daily/monthly limits prevent large-scale fraud
- Instant transfers capped at $1K (higher risk profile)
- Wire transfers for large amounts (enterprise users)

---

## 3. Fraud Prevention & Security

### Multi-Layer Security Approach

#### Layer 1: Identity Verification (KYC)

**Tier-Based Requirements:**

```
Free Tier:
- Email verification only
- Cannot withdraw (no KYC needed)

Basic Tier ($8/month):
- Email + phone verification
- Government ID upload (Stripe Identity)
- Max withdrawal: $1K/day without enhanced KYC

Premium Tier ($30/month):
- Full KYC (ID + proof of address)
- Max withdrawal: $5K/day
- Enhanced KYC for $50K+/month
```

**KYC Integration:**
- **Stripe Identity:** $1.50 per verification
- **Sumsub:** $0.50-2.00 per check
- **Veriff:** 95% pass rate, AI-powered

#### Layer 2: Velocity Checks

```typescript
interface VelocityCheck {
  // Flag suspicious patterns
  rules: {
    // New account withdrawing immediately
    newAccountFlag: {
      condition: 'account age < 30 days && withdrawal > $100',
      action: 'manual_review'
    },

    // Rapid successive withdrawals
    rapidWithdrawalFlag: {
      condition: '3+ withdrawals in 24 hours',
      action: 'temporary_hold'
    },

    // Unusual amount spike
    amountSpikeFlag: {
      condition: 'withdrawal > 5x average',
      action: 'manual_review'
    },

    // Different payout methods
    methodChangeFlag: {
      condition: 'new payout method < 7 days old',
      action: '24hr_hold'
    }
  }
}
```

#### Layer 3: Withdrawal Holds

**Automatic Holds:**
- **New users:** 7-day hold on first withdrawal
- **Large amounts:** 24hr hold for >$1K
- **Method changes:** 24hr hold after updating payout method
- **Suspicious activity:** Manual review (1-3 days)

**Implementation:**
```typescript
function calculateWithdrawalHold(
  user: User,
  amount: number,
  method: string
): { holdDuration: number; reason: string } {
  const accountAge = Date.now() - user.createdAt.getTime();
  const daysSinceCreation = accountAge / (1000 * 60 * 60 * 24);

  // New account hold
  if (daysSinceCreation < 30 && user.totalWithdrawals === 0) {
    return {
      holdDuration: 7 * 24 * 60 * 60 * 1000, // 7 days
      reason: 'First withdrawal from new account (security measure)'
    };
  }

  // Large amount hold
  if (amount > 1000) {
    return {
      holdDuration: 24 * 60 * 60 * 1000, // 24 hours
      reason: 'Large withdrawal amount (routine security check)'
    };
  }

  // New payment method
  const methodAge = getPaymentMethodAge(user, method);
  if (methodAge < 7 * 24 * 60 * 60 * 1000) {
    return {
      holdDuration: 24 * 60 * 60 * 1000,
      reason: 'New withdrawal method (verification period)'
    };
  }

  return { holdDuration: 0, reason: '' };
}
```

#### Layer 4: Device Fingerprinting

**Track:**
- IP addresses (VPN detection)
- Device IDs (prevent account farming)
- Behavioral patterns (typing speed, mouse movements)
- Browser fingerprints

**Tools:**
- **FingerprintJS:** $99-399/month, 99.5% accuracy
- **Sift:** ML-based fraud detection
- **MaxMind:** IP intelligence, VPN detection

#### Layer 5: Transaction Monitoring

**Real-time alerts for:**
- Withdrawals to sanctioned countries
- Multiple accounts same bank account
- Unusual geographic patterns
- Chargeback history on payment methods

---

## 4. Payout Method Integration

### Stripe Connect Integration

```typescript
import Stripe from 'stripe';
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

/**
 * Create payout to user's connected account
 */
async function createPayout(
  userId: string,
  amount: number,
  method: 'standard' | 'instant'
): Promise<Stripe.Payout> {
  const user = await getUser(userId);

  // Validate
  if (!user.stripeConnectedAccountId) {
    throw new Error('No connected account. Please add payment method.');
  }

  // Calculate fees
  const withdrawalFee = calculateWithdrawalFee(amount, user);
  const netAmount = amount - withdrawalFee.fee;

  // Create payout
  const payout = await stripe.payouts.create(
    {
      amount: Math.round(netAmount * 100), // Convert to cents
      currency: 'usd',
      method: method === 'instant' ? 'instant' : 'standard',
      metadata: {
        userId,
        grossAmount: amount,
        fee: withdrawalFee.fee,
        tier: user.tier
      }
    },
    {
      stripeAccount: user.stripeConnectedAccountId
    }
  );

  // Record in database
  await recordWithdrawal({
    userId,
    amount,
    fee: withdrawalFee.fee,
    netAmount,
    method,
    payoutId: payout.id,
    status: 'pending',
    estimatedArrival: payout.arrival_date
  });

  return payout;
}
```

### PayPal Integration

```typescript
/**
 * Create PayPal payout
 */
async function createPayPalPayout(
  userId: string,
  amount: number
): Promise<PayPalPayout> {
  const user = await getUser(userId);

  if (!user.paypalEmail) {
    throw new Error('No PayPal account linked');
  }

  const withdrawalFee = calculateWithdrawalFee(amount, user);
  const netAmount = amount - withdrawalFee.fee;

  // PayPal Payouts API
  const payout = await paypal.payouts.create({
    sender_batch_header: {
      sender_batch_id: `batch-${Date.now()}`,
      email_subject: 'You have a payout from Compute Marketplace'
    },
    items: [
      {
        recipient_type: 'EMAIL',
        amount: {
          value: netAmount.toFixed(2),
          currency: 'USD'
        },
        receiver: user.paypalEmail,
        note: 'Compute Capital withdrawal',
        sender_item_id: `withdrawal-${userId}-${Date.now()}`
      }
    ]
  });

  await recordWithdrawal({
    userId,
    amount,
    fee: withdrawalFee.fee,
    netAmount,
    method: 'paypal',
    payoutId: payout.batch_header.payout_batch_id,
    status: 'pending'
  });

  return payout;
}
```

---

## 5. Withdrawal Dashboard UX

### Withdrawal History Table

```
┌────────────────────────────────────────────────────────────────────────┐
│  Withdrawal History                                                     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Date          Amount    Fee      Net      Method     Status           │
│  ──────────────────────────────────────────────────────────────────   │
│  Oct 12, 2025  $100.00  -$1.00   $99.00   Bank       ✓ Completed      │
│  Oct 8, 2025   $250.00  -$2.50   $247.50  PayPal     ⏳ Processing    │
│  Oct 1, 2025   $50.00   -$2.50   $47.50   Instant    ✓ Completed      │
│  Sep 28, 2025  $75.00   -$3.75   $71.25   Bank       ✓ Completed      │
│                                                                         │
│  Total withdrawn this month: $350.00                                   │
│  Remaining monthly limit: $650.00                                      │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Pending Withdrawal Details

```
┌─────────────────────────────────────────────────────────────┐
│  Withdrawal Pending                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Amount: $250.00                                            │
│  Fee: -$2.50 (1%)                                           │
│  Net: $247.50                                               │
│                                                              │
│  Method: PayPal (user@example.com)                          │
│  Status: Processing                                         │
│  Submitted: Oct 8, 2025 2:30 PM                            │
│  Estimated arrival: Oct 10, 2025                           │
│                                                              │
│  🔒 Security hold: None                                     │
│  📧 Confirmation sent to your email                         │
│                                                              │
│  [Track Status]                    [Contact Support]        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Error Handling & User Communication

### Common Error Messages

**Insufficient Balance:**
```
❌ Insufficient Compute Capital

You're trying to withdraw $150.00, but your available 
balance is only $120.50.

Tip: Earn more by providing compute or wait for pending 
earnings to clear.

[View Balance Details]
```

**Minimum Not Met:**
```
❌ Minimum Withdrawal Not Met

The minimum withdrawal amount is $10.00.
You entered: $5.00

[Update Amount]
```

**Daily Limit Reached:**
```
❌ Daily Limit Reached

You've reached your daily withdrawal limit of $1,000.

Current tier: Basic
Upgrade to Premium for higher limits ($5,000/day)

[Upgrade to Premium]  [Try Again Tomorrow]
```

**KYC Required:**
```
⚠️ Identity Verification Required

To withdraw funds, we need to verify your identity.
This is a one-time process that takes ~2 minutes.

Why? Federal regulations require identity verification 
for withdrawals over $100.

[Verify Identity Now]  [Learn More]
```

**Security Hold:**
```
🔒 Withdrawal Under Review

Your withdrawal of $500.00 is under security review.
This is routine for first withdrawals or large amounts.

Expected resolution: 24-48 hours
We'll email you when complete.

Why? To protect your account from unauthorized access.

[View Details]  [Contact Support]
```

---

## 7. Tax Reporting (1099-K Compliance)

### US Regulation: Form 1099-K

**Threshold (2024+):** $600 annual earnings
**Who receives:** All users earning $600+ per year

**Implementation:**
```typescript
interface TaxReporting {
  // Track annually
  annualEarnings: number;
  annualWithdrawals: number;
  transactionCount: number;

  // Trigger 1099-K if:
  // - Earnings >= $600 AND
  // - Withdrawals > $0
  requires1099K: boolean;

  // Collect TIN (Tax Identification Number)
  tinCollected: boolean;
  tinType: 'SSN' | 'EIN';
}

async function check1099KRequirement(userId: string, year: number): Promise<void> {
  const earnings = await getAnnualEarnings(userId, year);

  if (earnings >= 600) {
    // Require TIN before withdrawal
    const user = await getUser(userId);

    if (!user.tinCollected) {
      blockWithdrawal(userId, {
        reason: 'Tax information required',
        message: 'IRS requires tax info for earnings over $600/year',
        action: '/settings/tax-info'
      });
    } else {
      // File 1099-K by January 31 of following year
      await queue1099KFiling(userId, earnings, year);
    }
  }
}
```

---

## 8. Key Recommendations

### Immediate Implementation (Phase 1)

1. **$10 minimum withdrawal** (balance accessibility + cost efficiency)
2. **3-tier KYC:** Email only (Free), Basic KYC (Basic), Enhanced KYC (Premium)
3. **ACH + PayPal methods** (covers 95%+ of users)
4. **7-day hold on first withdrawal** (fraud prevention)
5. **Velocity checks** (multiple withdrawals/day flagged)

### Phase 2 Enhancements

1. **Instant transfer option** (1.75% fee, 30min arrival)
2. **Wire transfers** for large amounts ($1K+ with $20 fee)
3. **Automated 1099-K filing** (tax compliance)
4. **ML-based fraud detection** (FingerprintJS, Sift)
5. **Cryptocurrency withdrawal** (USDC, 0.5% fee)

### Best Practices

1. **Transparency:** Show all fees upfront, no surprises
2. **Communication:** Email/SMS on every withdrawal status change
3. **Security:** Multi-factor authentication for withdrawals >$500
4. **Compliance:** KYC all users before first withdrawal
5. **User control:** Let users set daily/monthly withdrawal limits

---

## Conclusion

The withdrawal system balances user convenience (low minimums, fast processing) with platform security (KYC verification, velocity checks, holds). Key features:

- **$10 minimum** (accessible, cost-effective)
- **Multiple methods** (ACH, PayPal, instant, wire)
- **Tier-based limits** (Free: locked, Basic: $1K/day, Premium: $5K/day)
- **Fraud prevention** (KYC, velocity checks, device fingerprinting)
- **Transparent fees** (Basic: 5%, Premium: 1% → 0.1%)

This design follows industry best practices from YouTube, Twitch, Upwork, Fiverr, and payment processors while adding compute marketplace-specific features (Compute Capital locking, tier-based access).

**Next Steps:**
1. Implement tier migration system (see tier-migration-optimization.md)
2. Build analytics dashboard (see membership-analytics.md)
3. Design global pricing (see global-pricing-strategy.md)
