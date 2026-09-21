import { gql } from 'apollo-server-express';

export const subscriptionTypeDefs = gql`
  extend type Query {
    # Subscription management
    activeSubscriptions: [ActiveSubscription!]! @auth(requires: USER) @complexity(value: 5)
    subscriptionPlans: [SubscriptionPlan!]! @complexity(value: 3) @cache(ttl: 3600)
    currentSubscription: Subscription @auth(requires: USER) @complexity(value: 3)
    
    # Usage and billing
    usageMetrics(
      period: UsagePeriod = CURRENT_MONTH
      organizationId: ID
    ): UsageMetrics! @auth(requires: USER) @complexity(value: 8)
    
    billingHistory(
      pagination: PaginationInput
      filter: BillingHistoryFilterInput
    ): BillingHistoryConnection! @auth(requires: USER) @complexity(value: 8)
    
    # Payment methods
    paymentMethods: [PaymentMethod!]! @auth(requires: USER) @complexity(value: 3)
    
    # Invoices
    invoice(id: ID!): Invoice @auth(requires: USER) @complexity(value: 3)
    upcomingInvoice: Invoice @auth(requires: USER) @complexity(value: 5)
  }
  
  extend type Mutation {
    # Subscription management
    createSubscription(input: CreateSubscriptionInput!): CreateSubscriptionPayload! @auth(requires: USER)
    updateSubscription(input: UpdateSubscriptionInput!): UpdateSubscriptionPayload! @auth(requires: USER)
    cancelSubscription(input: CancelSubscriptionInput!): CancelSubscriptionPayload! @auth(requires: USER)
    reactivateSubscription(subscriptionId: ID!): ReactivateSubscriptionPayload! @auth(requires: USER)
    
    # Plan changes
    changePlan(input: ChangePlanInput!): ChangePlanPayload! @auth(requires: USER)
    upgradeToAnnual(subscriptionId: ID!): UpgradePayload! @auth(requires: USER)
    downgradeToMonthly(subscriptionId: ID!): DowngradePayload! @auth(requires: USER)
    
    # Payment methods
    addPaymentMethod(input: AddPaymentMethodInput!): AddPaymentMethodPayload! @auth(requires: USER)
    updatePaymentMethod(id: ID!, input: UpdatePaymentMethodInput!): UpdatePaymentMethodPayload! @auth(requires: USER)
    deletePaymentMethod(id: ID!): MutationResponse! @auth(requires: USER)
    setDefaultPaymentMethod(id: ID!): MutationResponse! @auth(requires: USER)
    
    # Billing
    retryPayment(invoiceId: ID!): RetryPaymentPayload! @auth(requires: USER)
    downloadInvoice(id: ID!): DownloadInvoicePayload! @auth(requires: USER)
    
    # Credits and coupons
    applyCoupon(code: String!): ApplyCouponPayload! @auth(requires: USER)
    removeCoupon(subscriptionId: ID!): MutationResponse! @auth(requires: USER)
    
    # Usage tracking
    recordUsage(input: RecordUsageInput!): MutationResponse! @auth(requires: SYSTEM)
    resetUsageMetrics(input: ResetUsageInput!): MutationResponse! @auth(requires: ADMIN)
  }
  
  extend type Subscription {
    # Subscription events
    subscriptionUpdated(userId: ID!): SubscriptionUpdate! @auth(requires: USER)
    usageThresholdReached(organizationId: ID!): UsageAlert! @auth(requires: USER)
    paymentFailed(userId: ID!): PaymentFailure! @auth(requires: USER)
    invoiceGenerated(userId: ID!): Invoice! @auth(requires: USER)
  }
  
  type Subscription implements Node @key(fields: "id") {
    id: ID!
    status: SubscriptionStatus!
    
    # Plan details
    plan: SubscriptionPlan! @complexity(value: 2)
    billing: BillingDetails!
    
    # Relationships
    user: User @complexity(value: 2)
    organization: Organization @complexity(value: 2)
    
    # Usage and limits
    usage: SubscriptionUsage! @complexity(value: 5)
    limits: SubscriptionLimits! @complexity(value: 3)
    
    # Payment
    paymentMethod: PaymentMethod @complexity(value: 2)
    nextBillingDate: DateTime
    
    # Discounts
    coupon: Coupon @complexity(value: 2)
    discount: SubscriptionDiscount
    
    # Lifecycle
    currentPeriodStart: DateTime!
    currentPeriodEnd: DateTime!
    trialStart: DateTime
    trialEnd: DateTime
    canceledAt: DateTime
    cancelAtPeriodEnd: Boolean!
    
    # Timestamps
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  enum SubscriptionStatus {
    ACTIVE
    TRIAL
    PAST_DUE
    CANCELED
    UNPAID
    INCOMPLETE
    INCOMPLETE_EXPIRED
  }
  
  type SubscriptionPlan {
    id: ID!
    name: String!
    description: String!
    
    # Pricing
    price: Money!
    currency: String!
    interval: BillingInterval!
    intervalCount: Int!
    
    # Trial
    trialPeriodDays: Int
    
    # Limits and features
    features: [PlanFeature!]!
    limits: PlanLimits!
    
    # Metadata
    isActive: Boolean!
    isPopular: Boolean!
    metadata: JSON
    
    # Timestamps
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  enum BillingInterval {
    DAY
    WEEK
    MONTH
    YEAR
  }
  
  type Money {
    amount: Int!
    currency: String!
    formatted: String!
  }
  
  type PlanFeature {
    id: ID!
    name: String!
    description: String!
    included: Boolean!
    limit: Int
    unlimited: Boolean!
  }
  
  type PlanLimits {
    storage: UsageLimit!
    bandwidth: UsageLimit!
    fileUploads: UsageLimit!
    videoProcessing: UsageLimit!
    teamMembers: UsageLimit!
    organizations: UsageLimit!
    plugins: UsageLimit!
    apiCalls: UsageLimit!
  }
  
  type UsageLimit {
    limit: Int
    unlimited: Boolean!
    resetPeriod: ResetPeriod!
  }
  
  enum ResetPeriod {
    NEVER
    DAILY
    MONTHLY
    YEARLY
  }
  
  type BillingDetails {
    interval: BillingInterval!
    intervalCount: Int!
    amount: Money!
    taxRate: Float
    discountAmount: Money
    totalAmount: Money!
  }
  
  type SubscriptionUsage {
    storage: UsageMetric!
    bandwidth: UsageMetric!
    fileUploads: UsageMetric!
    videoProcessing: UsageMetric!
    teamMembers: UsageMetric!
    organizations: UsageMetric!
    plugins: UsageMetric!
    apiCalls: UsageMetric!
    
    # Period
    periodStart: DateTime!
    periodEnd: DateTime!
    lastUpdated: DateTime!
  }
  
  type UsageMetric {
    current: Int!
    limit: Int
    unlimited: Boolean!
    percentage: Float!
    remaining: Int
  }
  
  type SubscriptionLimits {
    storage: Int
    bandwidth: Int
    fileUploads: Int
    videoProcessing: Int
    teamMembers: Int
    organizations: Int
    plugins: Int
    apiCalls: Int
  }
  
  type PaymentMethod {
    id: ID!
    type: PaymentMethodType!
    
    # Card details (for card type)
    card: CardDetails
    
    # Bank details (for bank type)
    bank: BankDetails
    
    # Status
    isDefault: Boolean!
    isVerified: Boolean!
    
    # Metadata
    fingerprint: String
    
    # Timestamps
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  enum PaymentMethodType {
    CARD
    BANK_ACCOUNT
    PAYPAL
    APPLE_PAY
    GOOGLE_PAY
  }
  
  type CardDetails {
    brand: String!
    last4: String!
    expiryMonth: Int!
    expiryYear: Int!
    country: String
  }
  
  type BankDetails {
    bankName: String!
    accountType: String!
    last4: String!
    country: String!
  }
  
  type Invoice {
    id: ID!
    number: String!
    status: InvoiceStatus!
    
    # Amounts
    subtotal: Money!
    tax: Money
    discount: Money
    total: Money!
    amountPaid: Money!
    amountDue: Money!
    
    # Details
    description: String
    currency: String!
    
    # Line items
    lineItems: [InvoiceLineItem!]!
    
    # Payment
    paymentMethod: PaymentMethod
    paidAt: DateTime
    
    # PDF
    pdfUrl: String
    
    # Dates
    periodStart: DateTime!
    periodEnd: DateTime!
    dueDate: DateTime!
    createdAt: DateTime!
  }
  
  enum InvoiceStatus {
    DRAFT
    OPEN
    PAID
    VOID
    UNCOLLECTIBLE
  }
  
  type InvoiceLineItem {
    id: ID!
    description: String!
    quantity: Int!
    unitAmount: Money!
    amount: Money!
    period: Period
  }
  
  type Period {
    start: DateTime!
    end: DateTime!
  }
  
  type Coupon {
    id: ID!
    code: String!
    name: String!
    
    # Discount
    percentOff: Float
    amountOff: Money
    duration: CouponDuration!
    durationInMonths: Int
    
    # Validity
    isValid: Boolean!
    expiresAt: DateTime
    maxRedemptions: Int
    timesRedeemed: Int!
    
    # Constraints
    minAmount: Money
    applicableProducts: [String!]
    
    createdAt: DateTime!
  }
  
  enum CouponDuration {
    ONCE
    REPEATING
    FOREVER
  }
  
  type SubscriptionDiscount {
    coupon: Coupon!
    start: DateTime!
    end: DateTime
  }
  
  type UsageMetrics {
    period: UsagePeriod!
    organization: Organization @complexity(value: 2)
    
    # Current usage
    storage: DetailedUsageMetric!
    bandwidth: DetailedUsageMetric!
    fileUploads: DetailedUsageMetric!
    videoProcessing: DetailedUsageMetric!
    apiCalls: DetailedUsageMetric!
    
    # Historical data
    dailyUsage: [DailyUsage!]! @complexity(value: 5)
    
    # Projections
    projectedUsage: ProjectedUsage @complexity(value: 3)
    
    lastUpdated: DateTime!
  }
  
  enum UsagePeriod {
    CURRENT_MONTH
    LAST_MONTH
    LAST_3_MONTHS
    LAST_6_MONTHS
    LAST_YEAR
    CUSTOM
  }
  
  type DetailedUsageMetric {
    current: Int!
    limit: Int
    unlimited: Boolean!
    percentage: Float!
    remaining: Int
    trend: UsageTrend!
    dailyAverage: Float!
    peakDay: DateTime
    peakValue: Int!
  }
  
  enum UsageTrend {
    INCREASING
    DECREASING
    STABLE
  }
  
  type DailyUsage {
    date: DateTime!
    storage: Int!
    bandwidth: Int!
    fileUploads: Int!
    videoProcessing: Int!
    apiCalls: Int!
  }
  
  type ProjectedUsage {
    endOfPeriod: ProjectedMetrics!
    willExceedLimit: Boolean!
    estimatedOverage: Money
  }
  
  type ProjectedMetrics {
    storage: Int!
    bandwidth: Int!
    fileUploads: Int!
    videoProcessing: Int!
    apiCalls: Int!
  }
  
  type ActiveSubscription {
    subscription: Subscription!
    isActive: Boolean!
    daysUntilRenewal: Int
    upcomingChanges: [SubscriptionChange!]!
  }
  
  type SubscriptionChange {
    type: ChangeType!
    effectiveDate: DateTime!
    newPlan: SubscriptionPlan
    description: String!
  }
  
  enum ChangeType {
    PLAN_CHANGE
    CANCELLATION
    REACTIVATION
    TRIAL_END
  }
  
  type BillingHistoryConnection {
    edges: [BillingHistoryEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type BillingHistoryEdge {
    node: BillingHistoryItem!
    cursor: String!
  }
  
  union BillingHistoryItem = Invoice | PaymentEvent | SubscriptionEvent
  
  type PaymentEvent {
    id: ID!
    type: PaymentEventType!
    amount: Money!
    status: PaymentStatus!
    invoice: Invoice
    createdAt: DateTime!
  }
  
  enum PaymentEventType {
    PAYMENT_SUCCEEDED
    PAYMENT_FAILED
    REFUND
    CHARGEBACK
  }
  
  enum PaymentStatus {
    SUCCEEDED
    FAILED
    PENDING
    CANCELED
    REQUIRES_ACTION
  }
  
  type SubscriptionEvent {
    id: ID!
    type: SubscriptionEventType!
    subscription: Subscription!
    previousPlan: SubscriptionPlan
    newPlan: SubscriptionPlan
    createdAt: DateTime!
  }
  
  enum SubscriptionEventType {
    CREATED
    UPDATED
    CANCELED
    REACTIVATED
    TRIAL_STARTED
    TRIAL_ENDED
    PLAN_CHANGED
  }
  
  # Input types
  input CreateSubscriptionInput {
    planId: ID!
    paymentMethodId: ID!
    organizationId: ID
    couponCode: String
    trialDays: Int
  }
  
  input UpdateSubscriptionInput {
    subscriptionId: ID!
    paymentMethodId: ID
    couponCode: String
  }
  
  input CancelSubscriptionInput {
    subscriptionId: ID!
    reason: CancellationReason!
    feedback: String
    cancelAtPeriodEnd: Boolean = true
  }
  
  enum CancellationReason {
    TOO_EXPENSIVE
    MISSING_FEATURES
    TOO_COMPLEX
    NOT_USED_ENOUGH
    FOUND_ALTERNATIVE
    OTHER
  }
  
  input ChangePlanInput {
    subscriptionId: ID!
    newPlanId: ID!
    prorationBehavior: ProrationBehavior = CREATE_PRORATIONS
  }
  
  enum ProrationBehavior {
    CREATE_PRORATIONS
    NONE
    ALWAYS_INVOICE
  }
  
  input AddPaymentMethodInput {
    type: PaymentMethodType!
    token: String!
    setAsDefault: Boolean = false
  }
  
  input UpdatePaymentMethodInput {
    expiryMonth: Int
    expiryYear: Int
  }
  
  input BillingHistoryFilterInput {
    types: [BillingHistoryItemType!]
    status: [PaymentStatus!]
    dateFrom: DateTime
    dateTo: DateTime
  }
  
  enum BillingHistoryItemType {
    INVOICE
    PAYMENT
    SUBSCRIPTION_EVENT
  }
  
  input RecordUsageInput {
    organizationId: ID!
    metric: UsageMetricType!
    amount: Int!
    timestamp: DateTime
  }
  
  enum UsageMetricType {
    STORAGE
    BANDWIDTH
    FILE_UPLOADS
    VIDEO_PROCESSING
    API_CALLS
  }
  
  input ResetUsageInput {
    organizationId: ID!
    metrics: [UsageMetricType!]!
    period: UsagePeriod!
  }
  
  # Response types
  type CreateSubscriptionPayload {
    success: Boolean!
    subscription: Subscription
    requiresAction: Boolean!
    clientSecret: String
    errors: [Error!]
  }
  
  type UpdateSubscriptionPayload {
    success: Boolean!
    subscription: Subscription
    errors: [Error!]
  }
  
  type CancelSubscriptionPayload {
    success: Boolean!
    subscription: Subscription
    refundAmount: Money
    errors: [Error!]
  }
  
  type ReactivateSubscriptionPayload {
    success: Boolean!
    subscription: Subscription
    errors: [Error!]
  }
  
  type ChangePlanPayload {
    success: Boolean!
    subscription: Subscription
    prorationInvoice: Invoice
    errors: [Error!]
  }
  
  type UpgradePayload {
    success: Boolean!
    subscription: Subscription
    savings: Money!
    errors: [Error!]
  }
  
  type DowngradePayload {
    success: Boolean!
    subscription: Subscription
    refund: Money
    errors: [Error!]
  }
  
  type AddPaymentMethodPayload {
    success: Boolean!
    paymentMethod: PaymentMethod
    errors: [Error!]
  }
  
  type UpdatePaymentMethodPayload {
    success: Boolean!
    paymentMethod: PaymentMethod
    errors: [Error!]
  }
  
  type RetryPaymentPayload {
    success: Boolean!
    invoice: Invoice
    requiresAction: Boolean!
    clientSecret: String
    errors: [Error!]
  }
  
  type DownloadInvoicePayload {
    success: Boolean!
    downloadUrl: String
    errors: [Error!]
  }
  
  type ApplyCouponPayload {
    success: Boolean!
    subscription: Subscription
    discount: SubscriptionDiscount
    savings: Money
    errors: [Error!]
  }
  
  # Subscription response types
  type SubscriptionUpdate {
    subscription: Subscription!
    changeType: ChangeType!
    previousState: JSON
  }
  
  type UsageAlert {
    organizationId: ID!
    metric: UsageMetricType!
    threshold: Float!
    currentUsage: Int!
    limit: Int!
    severity: AlertSeverity!
  }
  
  enum AlertSeverity {
    INFO
    WARNING
    CRITICAL
  }
  
  type PaymentFailure {
    invoiceId: ID!
    amount: Money!
    reason: String!
    nextRetryAt: DateTime
    attemptsRemaining: Int!
  }
`;