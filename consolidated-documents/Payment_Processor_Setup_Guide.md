# Payment Processor Setup Guide

## Overview

Setting up payment processing is crucial for businesses accepting online or in-person payments. This guide covers major payment processors, integration methods, and compliance requirements.

## Major Payment Processors

### 1. Stripe

**Best for:** Online businesses, SaaS, marketplaces
- **Processing Fees:** 2.9% + 30¢ per transaction
- **Setup Time:** Minutes to hours
- **Integration:** API-first, extensive documentation
- **Features:** Subscriptions, marketplaces, international payments

**Account Requirements:**
- Business bank account
- Business license (if required in your state)
- EIN or SSN
- Business website or app

**Integration Options:**
- Stripe Checkout (hosted payment page)
- Stripe Elements (custom forms)
- Payment Intents API (full control)
- Mobile SDKs (iOS/Android)

### 2. Square

**Best for:** Retail, restaurants, service businesses
- **Processing Fees:** 2.6% + 10¢ (online), 2.6% (in-person)
- **Setup Time:** Same day
- **Integration:** Simple APIs, POS hardware
- **Features:** POS systems, invoicing, payroll

**Account Requirements:**
- Business information
- Bank account for deposits
- Identity verification
- Business address

### 3. PayPal

**Best for:** E-commerce, international sales
- **Processing Fees:** 2.9% + 30¢ (domestic), 4.4% + fixed fee (international)
- **Setup Time:** 1-2 business days
- **Integration:** PayPal Checkout, REST APIs
- **Features:** PayPal Credit, international expansion

**Account Requirements:**
- Business PayPal account
- Bank account verification
- Business documentation
- Website or business description

### 4. Authorize.Net

**Best for:** Enterprise, high-volume merchants
- **Processing Fees:** 2.9% + 30¢ + monthly gateway fee
- **Setup Time:** 1-3 business days
- **Integration:** Payment gateway APIs
- **Features:** Fraud detection, recurring billing

## Setup Process for Stripe (Most Common)

### Step 1: Create Stripe Account
1. Visit stripe.com and click "Start now"
2. Enter business email and create password
3. Verify email address
4. Complete business information form

### Step 2: Business Verification
```yaml
Required Information:
  - Legal business name
  - Business type (LLC, Corporation, etc.)
  - Industry classification
  - Business address
  - Website or app URL
  - Expected processing volume
  - Bank account for payouts
  - Tax ID (EIN or SSN)
  - Business representative info
```

### Step 3: Set Up Bank Account
- Add business bank account for deposits
- Verify account with micro-deposits (1-2 business days)
- Set payout schedule (daily, weekly, monthly)

### Step 4: Configure Settings
- Set up webhooks for order notifications
- Configure tax settings
- Set up billing information
- Enable necessary features (subscriptions, etc.)

## Integration Methods

### 1. Stripe Checkout (Easiest)
```html
<!-- Pre-built checkout page -->
<script src="https://js.stripe.com/v3/"></script>
<button id="checkout-button">Pay Now</button>

<script>
const stripe = Stripe('pk_test_...');
document.getElementById('checkout-button').addEventListener('click', async () => {
  const {error} = await stripe.redirectToCheckout({
    lineItems: [{
      price: 'price_1234', // Created in Stripe Dashboard
      quantity: 1,
    }],
    mode: 'payment',
    successUrl: 'https://yourdomain.com/success',
    cancelUrl: 'https://yourdomain.com/cancel',
  });
});
</script>
```

### 2. Stripe Elements (Custom Forms)
```javascript
// Custom payment form
const stripe = Stripe('pk_test_...');
const elements = stripe.elements();

// Create card element
const cardElement = elements.create('card');
cardElement.mount('#card-element');

// Handle form submission
const form = document.getElementById('payment-form');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  
  const {token, error} = await stripe.createToken(cardElement);
  
  if (error) {
    console.error(error);
  } else {
    // Send token to your server
    submitTokenToServer(token);
  }
});
```

### 3. Payment Intents API (Server-side)
```javascript
// Node.js backend example
const stripe = require('stripe')('sk_test_...');

app.post('/create-payment-intent', async (req, res) => {
  const { amount, currency = 'usd' } = req.body;

  try {
    const paymentIntent = await stripe.paymentIntents.create({
      amount: amount * 100, // Convert to cents
      currency,
      automatic_payment_methods: {
        enabled: true,
      },
    });

    res.send({
      clientSecret: paymentIntent.client_secret,
    });
  } catch (error) {
    res.status(400).send({
      error: error.message,
    });
  }
});
```

## Security and Compliance

### PCI Compliance Levels

**Level 1:** 6M+ transactions/year
- Annual on-site security assessment
- Quarterly network scans
- Annual penetration testing

**Level 2:** 1-6M transactions/year
- Annual self-assessment questionnaire
- Quarterly network scans

**Level 3-4:** Under 1M transactions/year
- Annual self-assessment questionnaire
- Quarterly network scans (if storing card data)

### PCI Compliance Strategies

**Option 1: No Card Data Storage (Recommended)**
- Use hosted payment pages (Stripe Checkout, PayPal)
- Tokenization for recurring payments
- Minimal PCI scope
- Simplest compliance path

**Option 2: SAQ A-EP (E-commerce)**
- Custom payment forms with direct API calls
- No card data touches your servers
- Self-assessment questionnaire
- Network scans required

**Option 3: Full PCI Compliance**
- Store encrypted card data
- Extensive security requirements
- Annual assessments
- Not recommended for most businesses

### SSL Certificate Requirements
- Extended Validation (EV) SSL preferred
- TLS 1.2 or higher
- Valid certificate chain
- Proper cipher suites

## Fraud Prevention

### Built-in Fraud Tools

**Stripe Radar:**
- Machine learning fraud detection
- Customizable rules engine
- 3D Secure authentication
- Risk scoring and blocking

**PayPal Fraud Protection:**
- Seller protection for eligible transactions
- Real-time fraud screening
- Advanced risk models

### Additional Fraud Prevention
- Address Verification Service (AVS)
- CVV verification
- Velocity checking
- IP geolocation
- Device fingerprinting

## International Considerations

### Multi-Currency Support
```javascript
// Stripe multi-currency example
const paymentIntent = await stripe.paymentIntents.create({
  amount: 5000, // €50.00
  currency: 'eur',
  payment_method_types: ['card', 'sepa_debit'],
});
```

### Regional Payment Methods
- **Europe:** SEPA Direct Debit, SOFORT, iDEAL
- **Asia:** Alipay, WeChat Pay, FPX
- **Latin America:** OXXO, Boleto
- **Middle East:** KNET, Benefit

### Tax and Regulatory Compliance
- VAT collection for EU sales
- GST for Australia/India
- Local tax registration requirements
- Cross-border transaction reporting

## Subscription and Recurring Payments

### Stripe Subscriptions
```javascript
// Create subscription
const subscription = await stripe.subscriptions.create({
  customer: 'cus_...',
  items: [{
    price: 'price_monthly_plan',
  }],
  payment_behavior: 'default_incomplete',
  expand: ['latest_invoice.payment_intent'],
});
```

### Key Features to Implement
- Proration handling
- Failed payment retry logic
- Dunning management
- Cancellation flows
- Plan upgrades/downgrades

## Testing and Go-Live

### Test Scenarios
- Successful payments
- Declined cards
- Insufficient funds
- Expired cards
- 3D Secure authentication
- Webhooks delivery

### Test Card Numbers
```
Visa: 4242424242424242
Visa (debit): 4000056655665556
Mastercard: 5555555555554444
American Express: 378282246310005
Declined: 4000000000000002
```

### Go-Live Checklist
- [ ] Switch to production API keys
- [ ] Update webhook endpoints
- [ ] Verify SSL certificate
- [ ] Test production transactions
- [ ] Monitor error logs
- [ ] Set up alerting
- [ ] Document integration

## Cost Optimization

### Fee Negotiation Factors
- Processing volume
- Average transaction size
- Industry/risk level
- Integration method
- Additional services used

### Cost-Saving Strategies
- Optimize payment methods by cost
- Reduce chargebacks and disputes
- Use ACH for large transactions
- Negotiate volume discounts
- Minimize international fees

## Common Integration Issues

### 1. Webhook Security
```javascript
// Verify webhook signatures
const sig = request.headers['stripe-signature'];
let event;

try {
  event = stripe.webhooks.constructEvent(
    request.body,
    sig,
    endpointSecret
  );
} catch (err) {
  console.log(`Webhook signature verification failed.`, err.message);
  return response.status(400).send(`Webhook Error: ${err.message}`);
}
```

### 2. Idempotency
```javascript
// Prevent duplicate charges
const paymentIntent = await stripe.paymentIntents.create({
  amount: 2000,
  currency: 'usd',
}, {
  idempotencyKey: 'unique_key_for_this_payment'
});
```

### 3. Error Handling
```javascript
try {
  const charge = await stripe.charges.create({...});
} catch (error) {
  switch (error.type) {
    case 'StripeCardError':
      // Card was declined
      break;
    case 'StripeRateLimitError':
      // Too many requests
      break;
    case 'StripeInvalidRequestError':
      // Invalid parameters
      break;
    case 'StripeAPIError':
      // Stripe API issue
      break;
    case 'StripeConnectionError':
      // Network issue
      break;
    default:
      // Unknown error
      break;
  }
}
```

## Maintenance and Monitoring

### Key Metrics to Monitor
- Transaction success rates
- Average processing time
- Chargeback rates
- Fraud detection accuracy
- Revenue per transaction

### Regular Tasks
- **Daily:**
  - Monitor transaction volumes
  - Check for failed payments
  - Review fraud alerts

- **Weekly:**
  - Analyze payment method performance
  - Review chargeback notifications
  - Update fraud rules

- **Monthly:**
  - Reconcile payments with accounting
  - Review processing fees
  - Analyze customer payment preferences

- **Quarterly:**
  - PCI compliance scans
  - Review payment processor performance
  - Evaluate new features and integrations

## Emergency Procedures

### Payment Processor Outages
- Monitor status pages
- Implement backup payment methods
- Communicate with customers
- Queue transactions for retry

### Security Breaches
- Immediate incident response
- Notify payment processor
- Contact PCI compliance team
- Document and report incident

### Chargeback Management
- Respond within required timeframes
- Gather supporting documentation
- Implement prevention measures
- Monitor dispute trends