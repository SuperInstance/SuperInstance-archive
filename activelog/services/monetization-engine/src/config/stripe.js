const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const logger = require('../utils/logger');

// Configure Stripe API version
stripe.apiVersion = process.env.STRIPE_API_VERSION || '2023-08-16';

// Pricing configurations
const PRICING_PLANS = {
  free: {
    name: 'Free',
    price: 0,
    features: {
      storageGB: 1,
      apiCallsPerMonth: 1000,
      usersLimit: 1,
      supportLevel: 'community',
      adSupported: true,
      backupRetention: 7, // days
      computeCredits: 0
    },
    stripeProductId: null // Free tier doesn't need Stripe product
  },
  pro: {
    name: 'Professional',
    price: 2999, // $29.99 in cents
    priceId: process.env.STRIPE_PRO_PRICE_ID,
    interval: 'month',
    features: {
      storageGB: 100,
      apiCallsPerMonth: 50000,
      usersLimit: 10,
      supportLevel: 'email',
      adSupported: false,
      backupRetention: 30,
      computeCredits: 1000
    },
    stripeProductId: process.env.STRIPE_PRO_PRODUCT_ID
  },
  enterprise: {
    name: 'Enterprise',
    price: 9999, // $99.99 in cents
    priceId: process.env.STRIPE_ENTERPRISE_PRICE_ID,
    interval: 'month',
    features: {
      storageGB: -1, // unlimited
      apiCallsPerMonth: -1, // unlimited
      usersLimit: -1, // unlimited
      supportLevel: 'priority',
      adSupported: false,
      backupRetention: 365,
      computeCredits: 10000,
      whiteLabel: true,
      customIntegrations: true,
      dedicatedSupport: true
    },
    stripeProductId: process.env.STRIPE_ENTERPRISE_PRODUCT_ID
  }
};

// White-label pricing tiers
const WHITE_LABEL_TIERS = {
  starter: {
    name: 'White-Label Starter',
    price: 19999, // $199.99
    priceId: process.env.STRIPE_WL_STARTER_PRICE_ID,
    features: {
      brandingCustomization: 'basic',
      domainMapping: true,
      logoUpload: true,
      colorScheme: 'limited',
      userLimit: 100,
      supportLevel: 'standard'
    }
  },
  professional: {
    name: 'White-Label Professional',
    price: 49999, // $499.99
    priceId: process.env.STRIPE_WL_PRO_PRICE_ID,
    features: {
      brandingCustomization: 'full',
      domainMapping: true,
      logoUpload: true,
      colorScheme: 'unlimited',
      userLimit: 1000,
      supportLevel: 'priority',
      customCSS: true,
      apiIntegrations: true
    }
  },
  enterprise: {
    name: 'White-Label Enterprise',
    price: 'custom', // Contact for pricing
    features: {
      brandingCustomization: 'complete',
      domainMapping: true,
      logoUpload: true,
      colorScheme: 'unlimited',
      userLimit: -1,
      supportLevel: 'dedicated',
      customCSS: true,
      apiIntegrations: true,
      sourceCodeAccess: true,
      dedicatedInfrastructure: true
    }
  }
};

// Usage-based pricing rates
const USAGE_RATES = {
  storage: {
    freeGB: 1,
    ratePerGB: 50, // $0.50 per GB per month in cents
    overageThreshold: 1
  },
  apiCalls: {
    freeAmount: 1000,
    ratePerThousand: 10, // $0.10 per 1000 calls in cents
    overageThreshold: 1000
  },
  computeCredits: {
    ratePer100Credits: 100, // $1.00 per 100 credits in cents
    bulkDiscounts: {
      1000: 0.9, // 10% discount for 1000+ credits
      5000: 0.85, // 15% discount for 5000+ credits
      10000: 0.8 // 20% discount for 10000+ credits
    }
  },
  bandwidth: {
    freeGB: 10,
    ratePerGB: 20, // $0.20 per GB
    overageThreshold: 10
  }
};

// Marketplace fee structure
const MARKETPLACE_FEES = {
  commission: {
    digital: 0.15, // 15% for digital products
    physical: 0.08, // 8% for physical products
    services: 0.12, // 12% for services
    subscriptions: 0.10 // 10% for subscription products
  },
  paymentProcessing: {
    stripe: 0.029, // 2.9% + $0.30
    stripeFee: 30, // $0.30 in cents
    paypal: 0.032, // 3.2% for PayPal
    paypalFee: 0
  },
  minimumFee: 50 // $0.50 minimum fee in cents
};

// Tax rates by region (fallback if tax service unavailable)
const TAX_RATES = {
  US: {
    default: 0.08, // 8% average sales tax
    states: {
      'CA': 0.0725,
      'NY': 0.08,
      'TX': 0.0625,
      'FL': 0.06,
      'WA': 0.065,
      // Add more states as needed
    }
  },
  EU: {
    default: 0.20, // 20% VAT
    countries: {
      'DE': 0.19,
      'FR': 0.20,
      'IT': 0.22,
      'ES': 0.21,
      'NL': 0.21,
      'GB': 0.20,
      // Add more countries as needed
    }
  },
  CA: {
    default: 0.13, // 13% HST
    provinces: {
      'ON': 0.13, // HST
      'BC': 0.12, // PST + GST
      'AB': 0.05, // GST only
      'QC': 0.14975, // GST + QST
      // Add more provinces as needed
    }
  }
};

// Webhook endpoints configuration
const WEBHOOK_EVENTS = [
  'payment_intent.succeeded',
  'payment_intent.payment_failed',
  'invoice.payment_succeeded',
  'invoice.payment_failed',
  'customer.subscription.created',
  'customer.subscription.updated',
  'customer.subscription.deleted',
  'setup_intent.succeeded',
  'charge.dispute.created',
  'charge.dispute.closed'
];

// Test Stripe configuration on startup
if (process.env.NODE_ENV !== 'test') {
  stripe.balance.retrieve()
    .then(() => {
      logger.info('Stripe API connection established successfully');
    })
    .catch(err => {
      logger.error('Stripe API connection failed:', err.message);
      if (process.env.NODE_ENV === 'production') {
        process.exit(1);
      }
    });
}

module.exports = {
  stripe,
  PRICING_PLANS,
  WHITE_LABEL_TIERS,
  USAGE_RATES,
  MARKETPLACE_FEES,
  TAX_RATES,
  WEBHOOK_EVENTS
};