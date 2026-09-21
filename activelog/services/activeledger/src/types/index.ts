import { Decimal } from 'decimal.js';

// Core Financial Types
export interface ComputeCredit {
  id: string;
  userId: string;
  amount: Decimal;
  currency: CurrencyCode;
  sourceType: 'purchase' | 'ad_revenue' | 'affiliate' | 'refund' | 'bonus' | 'compute_refund';
  sourceId?: string;
  expiresAt?: Date;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  metadata?: Record<string, any>;
}

export interface CCTransaction {
  id: string;
  userId: string;
  type: 'debit' | 'credit';
  amount: Decimal;
  currency: CurrencyCode;
  description: string;
  category: TransactionCategory;
  sourceType: string;
  sourceId?: string;
  balanceAfter: Decimal;
  exchangeRate?: Decimal;
  originalAmount?: Decimal;
  originalCurrency?: CurrencyCode;
  createdAt: Date;
  metadata?: Record<string, any>;
}

export interface CCWallet {
  id: string;
  userId: string;
  primaryCurrency: CurrencyCode;
  balances: Record<CurrencyCode, Decimal>;
  totalBalanceUSD: Decimal;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

// Subscription and Billing Types
export interface Subscription {
  id: string;
  userId: string;
  planId: string;
  status: SubscriptionStatus;
  tier: SubscriptionTier;
  billingCycle: BillingCycle;
  storageLimit: number; // in GB
  computeCreditsIncluded: Decimal;
  currentPeriodStart: Date;
  currentPeriodEnd: Date;
  cancelAtPeriodEnd: boolean;
  paymentMethodId?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  tier: SubscriptionTier;
  storageLimit: number; // in GB
  computeCreditsIncluded: Decimal;
  priceMonthly: Decimal;
  priceYearly: Decimal;
  features: string[];
  isActive: boolean;
  createdAt: Date;
}

// Payment and Gateway Types
export interface PaymentMethod {
  id: string;
  userId: string;
  type: PaymentType;
  provider: PaymentProvider;
  providerPaymentMethodId: string;
  isDefault: boolean;
  last4?: string;
  expiryMonth?: number;
  expiryYear?: number;
  brand?: string;
  country?: string;
  isActive: boolean;
  createdAt: Date;
}

export interface Payment {
  id: string;
  userId: string;
  amount: Decimal;
  currency: CurrencyCode;
  status: PaymentStatus;
  provider: PaymentProvider;
  providerTransactionId: string;
  paymentMethodId: string;
  purpose: PaymentPurpose;
  purposeId: string;
  ccCreditsAwarded?: Decimal;
  createdAt: Date;
  updatedAt: Date;
  metadata?: Record<string, any>;
}

// Ad Revenue Types
export interface AdRevenue {
  id: string;
  userId: string;
  adNetworkId: string;
  impressions: number;
  clicks: number;
  revenue: Decimal;
  currency: CurrencyCode;
  userShare: Decimal; // 90% of revenue
  platformShare: Decimal; // 10% of revenue
  ccCreditsAwarded: Decimal;
  reportingPeriod: Date;
  status: 'pending' | 'confirmed' | 'paid';
  createdAt: Date;
  updatedAt: Date;
}

export interface AdNetwork {
  id: string;
  name: string;
  apiKey: string;
  revenueSharePercentage: number; // Platform's share (10%)
  minPayoutThreshold: Decimal;
  isActive: boolean;
  createdAt: Date;
}

// Affiliate Program Types
export interface AffiliateProgram {
  id: string;
  userId: string;
  affiliateCode: string;
  tier: AffiliateTier;
  totalReferrals: number;
  totalEarnings: Decimal;
  currentMonthEarnings: Decimal;
  commissionRate: Decimal;
  status: AffiliateStatus;
  payoutMethod?: PaymentProvider;
  createdAt: Date;
  updatedAt: Date;
}

export interface AffiliateReferral {
  id: string;
  affiliateUserId: string;
  referredUserId: string;
  affiliateCode: string;
  conversionType: 'signup' | 'subscription' | 'purchase';
  conversionValue: Decimal;
  commissionAmount: Decimal;
  ccCreditsAwarded: Decimal;
  status: 'pending' | 'confirmed' | 'paid';
  createdAt: Date;
  paidAt?: Date;
}

// Compute Rental Types
export interface ComputeInstance {
  id: string;
  userId: string;
  instanceType: EC2InstanceType;
  region: AWSRegion;
  status: ComputeStatus;
  launchedAt: Date;
  terminatedAt?: Date;
  hourlyRate: Decimal;
  totalCost: Decimal;
  ccDebited: Decimal;
  purpose: 'development' | 'production' | 'testing' | 'processing';
  autoTerminateAt?: Date;
  awsInstanceId?: string;
  publicIP?: string;
  privateIP?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface ComputeUsage {
  id: string;
  userId: string;
  instanceId: string;
  usageType: 'compute' | 'storage' | 'bandwidth' | 'backup';
  quantity: Decimal;
  unit: string;
  rate: Decimal;
  cost: Decimal;
  billingPeriodStart: Date;
  billingPeriodEnd: Date;
  createdAt: Date;
}

// Marketplace Types
export interface MarketplaceListing {
  id: string;
  sellerId: string;
  title: string;
  description: string;
  category: MarketplaceCategory;
  price: Decimal;
  currency: CurrencyCode;
  acceptsCCPayment: boolean;
  listingType: 'product' | 'service' | 'digital';
  status: ListingStatus;
  inventory?: number;
  images: string[];
  tags: string[];
  averageRating?: number;
  totalReviews: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface MarketplaceTransaction {
  id: string;
  listingId: string;
  sellerId: string;
  buyerId: string;
  quantity: number;
  totalAmount: Decimal;
  currency: CurrencyCode;
  paymentMethod: 'cc_credits' | 'card' | 'paypal';
  status: TransactionStatus;
  platformFee: Decimal;
  sellerPayout: Decimal;
  ccDebited?: Decimal;
  escrowReleaseAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

// Review and Reputation Types
export interface Review {
  id: string;
  reviewerId: string;
  revieweeId: string;
  transactionId?: string;
  listingId?: string;
  type: 'buyer' | 'seller' | 'service';
  rating: number; // 1-5
  title: string;
  content: string;
  isVerified: boolean;
  response?: string;
  responseDate?: Date;
  helpfulVotes: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface ReputationScore {
  id: string;
  userId: string;
  overallScore: number;
  buyerScore: number;
  sellerScore: number;
  serviceScore: number;
  totalReviews: number;
  positiveReviews: number;
  neutralReviews: number;
  negativeReviews: number;
  badges: string[];
  verificationLevel: VerificationLevel;
  lastCalculated: Date;
}

// Enterprise Billing Types
export interface EnterpriseAccount {
  id: string;
  organizationName: string;
  primaryContactUserId: string;
  billingContactEmail: string;
  taxId?: string;
  billingAddress: Address;
  paymentTerms: number; // days
  creditLimit: Decimal;
  customPricing: boolean;
  dedicatedSupport: boolean;
  slaLevel: 'standard' | 'premium' | 'enterprise';
  status: 'active' | 'suspended' | 'pending';
  createdAt: Date;
  updatedAt: Date;
}

export interface EnterpriseInvoice {
  id: string;
  enterpriseAccountId: string;
  invoiceNumber: string;
  amount: Decimal;
  currency: CurrencyCode;
  status: InvoiceStatus;
  dueDate: Date;
  issuedAt: Date;
  paidAt?: Date;
  lineItems: InvoiceLineItem[];
  taxAmount?: Decimal;
  discountAmount?: Decimal;
  totalAmount: Decimal;
  paymentMethod?: string;
  createdAt: Date;
}

export interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: Decimal;
  unitPrice: Decimal;
  totalPrice: Decimal;
  category: string;
  metadata?: Record<string, any>;
}

// Cost Calculator Types
export interface CostCalculation {
  id: string;
  userId?: string;
  service: string;
  region?: AWSRegion;
  configuration: Record<string, any>;
  estimatedMonthlyCost: Decimal;
  breakdown: CostBreakdown[];
  markup: Decimal;
  markupPercentage: Decimal;
  finalPrice: Decimal;
  validUntil: Date;
  createdAt: Date;
}

export interface CostBreakdown {
  category: string;
  description: string;
  baseCost: Decimal;
  markup: Decimal;
  finalCost: Decimal;
  unit: string;
  quantity: Decimal;
}

// Currency and Exchange Types
export interface ExchangeRate {
  id: string;
  fromCurrency: CurrencyCode;
  toCurrency: CurrencyCode;
  rate: Decimal;
  source: string;
  validFrom: Date;
  validTo: Date;
  createdAt: Date;
}

export interface CurrencyConversion {
  id: string;
  userId: string;
  fromAmount: Decimal;
  fromCurrency: CurrencyCode;
  toAmount: Decimal;
  toCurrency: CurrencyCode;
  exchangeRate: Decimal;
  fee: Decimal;
  status: 'pending' | 'completed' | 'failed';
  createdAt: Date;
  completedAt?: Date;
}

// Dashboard and Analytics Types
export interface FinancialSummary {
  userId: string;
  ccBalance: Decimal;
  monthlySpend: Decimal;
  monthlyEarnings: Decimal;
  activeSubscriptions: number;
  runningInstances: number;
  totalTransactions: number;
  generatedAt: Date;
}

export interface UsageMetrics {
  userId: string;
  period: 'daily' | 'weekly' | 'monthly';
  storageUsed: number; // GB
  computeHours: Decimal;
  bandwidthUsed: number; // GB
  apiCalls: number;
  costs: Record<string, Decimal>;
  period_start: Date;
  period_end: Date;
}

// Common Types and Enums
export type CurrencyCode = 'USD' | 'EUR' | 'GBP' | 'JPY' | 'CAD' | 'AUD' | 'CHF' | 'CNY' | 'INR' | 'BRL';

export type SubscriptionTier = 'free' | 'pro' | 'premium' | 'enterprise';

export type SubscriptionStatus = 'active' | 'canceled' | 'past_due' | 'unpaid' | 'trialing';

export type BillingCycle = 'monthly' | 'yearly';

export type PaymentType = 'card' | 'bank_account' | 'digital_wallet';

export type PaymentProvider = 'stripe' | 'paypal' | 'google_pay' | 'venmo' | 'zelle' | 'apple_pay';

export type PaymentStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'canceled' | 'refunded';

export type PaymentPurpose = 'subscription' | 'cc_purchase' | 'marketplace' | 'compute' | 'enterprise';

export type TransactionCategory = 'subscription' | 'compute' | 'marketplace' | 'affiliate' | 'ad_revenue' | 'refund';

export type ComputeStatus = 'launching' | 'running' | 'stopping' | 'stopped' | 'terminated' | 'failed';

export type EC2InstanceType = 't3.micro' | 't3.small' | 't3.medium' | 't3.large' | 't3.xlarge' | 
                              'm5.large' | 'm5.xlarge' | 'm5.2xlarge' | 'm5.4xlarge' | 'c5.large' | 'c5.xlarge';

export type AWSRegion = 'us-east-1' | 'us-west-2' | 'eu-west-1' | 'eu-central-1' | 'ap-southeast-1' | 'ap-northeast-1';

export type MarketplaceCategory = 'digital_products' | 'services' | 'templates' | 'code' | 'data' | 'other';

export type ListingStatus = 'active' | 'inactive' | 'sold_out' | 'removed';

export type TransactionStatus = 'pending' | 'processing' | 'completed' | 'disputed' | 'refunded' | 'failed';

export type AffiliateTier = 'bronze' | 'silver' | 'gold' | 'platinum';

export type AffiliateStatus = 'active' | 'inactive' | 'suspended' | 'pending_approval';

export type VerificationLevel = 'unverified' | 'email' | 'phone' | 'identity' | 'full';

export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'void';

export interface Address {
  street: string;
  city: string;
  state: string;
  postalCode: string;
  country: string;
}

// API Response Types
export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  pagination?: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface PaginationOptions {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// Configuration Types
export interface DatabaseConfig {
  uri: string;
  options: Record<string, any>;
}

export interface PaymentGatewayConfig {
  stripe: {
    publishableKey: string;
    secretKey: string;
    webhookSecret: string;
  };
  paypal: {
    clientId: string;
    clientSecret: string;
    environment: 'sandbox' | 'production';
  };
}

export interface AWSConfig {
  accessKeyId: string;
  secretAccessKey: string;
  region: string;
  ec2: {
    defaultSecurityGroup: string;
    defaultKeyPair: string;
  };
}

export interface EmailConfig {
  provider: 'mailgun' | 'sendgrid' | 'ses';
  apiKey: string;
  domain: string;
  fromAddress: string;
}