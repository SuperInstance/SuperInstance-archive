# Global Pricing & PPP Strategy

**Date:** October 14, 2025
**Objective:** Design purchasing power parity pricing for global markets

---

## Executive Summary

PPP-adjusted pricing can unlock 4 billion+ users in developing markets while $8-30/month tiers remain competitive in US/EU. Based on research of Spotify, Netflix, Steam, and Notion regional pricing strategies.

**Key Decision:** Start US-only, expand to PPP pricing in Phase 2 (12-18 months) once platform stable.

**Reasoning:**
- $8 Basic already cheap in US/EU ($0.27/day)
- VPN abuse prevention requires sophisticated infrastructure
- Focus on product-market fit first, global expansion second
- Can always add regional pricing later

---

## 1. PPP Pricing Research

### Successful Implementations

**Spotify:**
- US: $11/month
- India: $2/month (82% discount)
- Brazil: $5/month (55% discount)
- Result: 46% global conversion rate (industry-leading)

**Netflix:**
- US: $15.49/month (Standard)
- India: $3-7/month
- Philippines: $5-10/month

**Steam:**
- Dynamic regional pricing
- Argentina: 70% cheaper than US
- Turkey: 50% cheaper

**Notion:**
- Recently introduced PPP pricing
- 50-70% discounts in developing countries

### Common Patterns

1. **Discount ranges:** 30-80% below US pricing
2. **Geolocation:** IP-based detection + payment method verification
3. **VPN prevention:** Multi-layer checks (IP, payment, billing address)
4. **Price floors:** Minimum viable price to cover costs

---

## 2. Recommended Regional Pricing

### Tier 1 (High-Income): Standard Pricing

**Countries:** US, Canada, UK, Germany, France, Australia, Japan, Singapore
**Pricing:** $8 (Basic), $30 (Premium)
**No adjustments needed**

### Tier 2 (Upper-Middle Income): 30% Discount

**Countries:** Poland, Czech Republic, Chile, Malaysia, Russia
**Pricing:** $5.50 (Basic), $21 (Premium)
**Rationale:** Moderate purchasing power, some price sensitivity

### Tier 3 (Lower-Middle Income): 60% Discount

**Countries:** Brazil, Mexico, Thailand, Philippines, Indonesia, Vietnam
**Pricing:** $3 (Basic), $12 (Premium)
**Rationale:** High price sensitivity, large markets

### Tier 4 (Low-Income): 70% Discount

**Countries:** India, Pakistan, Nigeria, Bangladesh, Egypt
**Pricing:** $2.50 (Basic), $9 (Premium)
**Rationale:** Extremely price-sensitive, massive TAM (3B+ people)

---

## 3. VPN Abuse Prevention

### Multi-Layer Detection

```typescript
interface GeolocationCheck {
  // Layer 1: IP Address
  ipCountry: string;
  isVPN: boolean;
  isProxy: boolean;
  isTOR: boolean;
  
  // Layer 2: Payment Method
  paymentCountry: string;
  cardBIN: string; // First 6 digits reveal issuing country
  
  // Layer 3: Billing Address
  billingCountry: string;
  billingZIP: string;
  
  // Layer 4: Browser/Device
  browserLanguage: string;
  timezone: string;
  deviceFingerprint: string;
  
  // Consensus
  mostLikelyCountry: string;
  confidence: number; // 0-100%
}

function detectTrueLocation(user: User): GeolocationCheck {
  const ipCheck = checkIPLocation(user.ip);
  const paymentCheck = getPaymentMethodCountry(user.paymentMethod);
  const billingCheck = user.billingAddress.country;
  const browserCheck = user.browserInfo.language;
  
  // If all match, high confidence
  if (ipCheck === paymentCheck && paymentCheck === billingCheck) {
    return {
      mostLikelyCountry: ipCheck,
      confidence: 95,
      isVPN: false
    };
  }
  
  // If IP differs but payment/billing match, likely VPN
  if (paymentCheck === billingCheck && ipCheck !== paymentCheck) {
    return {
      mostLikelyCountry: paymentCheck,
      confidence: 85,
      isVPN: true,
      action: 'charge_based_on_payment_country'
    };
  }
  
  // If nothing matches, flag for review
  return {
    mostLikelyCountry: 'UNKNOWN',
    confidence: 20,
    isVPN: true,
    action: 'manual_review_required'
  };
}
```

### VPN Detection Services

**MaxMind GeoIP2:**
- $0.00045 per lookup
- 99.8% country-level accuracy
- VPN/proxy detection included

**IP2Location:**
- $50-200/month for 500K-2M queries
- Real-time VPN detection

**ParityVend:**
- $99-299/month
- Built-in anti-VPN, anti-TOR, anti-proxy
- Designed for PPP pricing

---

## 4. Implementation Strategy

### Phase 1 (Months 1-12): US-Only

**Reasoning:**
- Simplify operations during MVP
- Prove product-market fit domestically first
- Build stable platform before complexity of global ops
- $8-30 pricing already competitive in US market

**Block international signups?** No.
- Allow international users at US pricing
- Validate demand in other countries
- Gather data for Phase 2 regional pricing

### Phase 2 (Months 13-24): English-Speaking Markets

**Expand to:**
- UK, Canada, Australia (Tier 1 pricing)
- India (Tier 4 pricing - $2.50/$9)
- Philippines (Tier 3 pricing - $3/$12)

**Why these markets:**
- English-speaking (no localization needed)
- India/Philippines: Massive developer communities
- Test PPP pricing with $2.50 tier in India

**Infrastructure needed:**
- VPN detection (MaxMind)
- Multi-currency support (Stripe handles this)
- Regional payment methods (UPI for India, GCash for Philippines)

### Phase 3 (Months 25-36): Global Expansion

**Add:**
- Europe (Tier 1-2)
- Latin America (Tier 2-3)
- Southeast Asia (Tier 3)
- Africa (Tier 4)

**Requirements:**
- Full localization (10+ languages)
- Regional payment methods
- Local compliance (GDPR, etc.)
- 24/7 support across timezones

---

## 5. Pricing Psychology by Market

### US/EU (High Willingness to Pay)

- Focus on value messaging ("Save $X/month vs cloud")
- Premium positioning
- Feature-rich communication
- Annual discounts (10%)

### India/Southeast Asia (Price-Sensitive)

- Lead with cost savings ("$2.50/month, less than a coffee")
- Emphasize affordability
- Local payment methods (UPI, GCash, etc.)
- Mobile-first experience

### Latin America (Mid-Range)

- Balance value + affordability
- Community-focused messaging
- Flexible payment options
- Strong customer support

---

## 6. Revenue Impact Analysis

### Scenario: Without PPP Pricing

```
US users (10,000): $8/mo × 10,000 = $80K MRR
India users (1,000 at US price): $8/mo × 1,000 = $8K MRR
Total: $88K MRR

India conversion: 1% (high price = low conversions)
```

### Scenario: With PPP Pricing

```
US users (10,000): $8/mo × 10,000 = $80K MRR
India users (10,000 at $2.50/mo): $2.50/mo × 10,000 = $25K MRR
Total: $105K MRR (+19%)

India conversion: 5% (affordable price = 5x higher conversions)
India user base: 10x larger (1,000 → 10,000 users)
```

**Key Insight:** Lower price × higher volume = more revenue + market share

---

## 7. Alternative: Country-Agnostic Pricing

### Simpler Approach

**Instead of regional pricing, use usage-based tiers:**

- Free: 20% markup (same globally)
- Basic $8: 5% markup (same globally)
- Premium $30: 0.1% markup (same globally)

**Pros:**
- No VPN abuse concerns
- Simpler operations
- Transparent pricing
- No geolocation complexity

**Cons:**
- Excludes price-sensitive markets (India, Africa)
- Leaves TAM on table (4B people)
- Competitors with PPP pricing gain advantage

**Recommendation:** Start here, add PPP in Phase 2.

---

## 8. Key Recommendations

### Immediate (Phase 1)

1. **Launch US-only** with $8/$30 pricing
2. **Allow international users** at US pricing (gauge demand)
3. **Track geographic distribution** in analytics
4. **Build waitlist** for regional pricing

### 6-12 Months (Phase 2)

1. **Add India** with $2.50/$9 pricing (test PPP)
2. **Implement MaxMind** VPN detection ($0.00045/lookup)
3. **Add UPI** payment method (India)
4. **Monitor conversion rates** vs US pricing

### 12-24 Months (Phase 3)

1. **Expand to 20+ countries** with tier-based pricing
2. **Full localization** (10 languages)
3. **Regional customer support**
4. **A/B test pricing** by country

---

## Conclusion

PPP pricing can unlock billions of users in developing markets, but adds operational complexity. Recommended path:

**Phase 1:** US-only, prove product-market fit
**Phase 2:** Add India ($2.50) to test PPP, validate demand
**Phase 3:** Global expansion with full regional pricing

This balances growth opportunity with operational simplicity, allowing platform to mature before taking on global complexity.

**Bottom Line:** $8 Basic tier is already affordable in US/EU. Don't overcomplicate early. Expand globally once proven domestically.
