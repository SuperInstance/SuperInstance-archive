import { gql } from 'apollo-server-express';

export const organizationTypeDefs = gql`
  extend type Query {
    # Organization queries
    organization(id: ID!): Organization @auth(requires: USER) @complexity(value: 3)
    organizations(
      pagination: PaginationInput
      sort: SortInput
      filter: OrganizationFilterInput
    ): OrganizationConnection! @auth(requires: ADMIN) @complexity(value: 10)
    
    # Organization membership
    myOrganizations: [Organization!]! @auth(requires: USER) @complexity(value: 5)
    organizationMembers(
      organizationId: ID!
      pagination: PaginationInput
      filter: MemberFilterInput
    ): OrganizationMemberConnection! @auth(requires: USER) @complexity(value: 8)
    
    # Organization analytics
    organizationAnalytics(
      organizationId: ID!
      period: AnalyticsPeriod = LAST_30_DAYS
    ): OrganizationAnalytics @auth(requires: USER) @complexity(value: 8)
    
    # Organization billing
    organizationBilling(organizationId: ID!): OrganizationBilling @auth(requires: ADMIN) @complexity(value: 5)
    organizationUsage(
      organizationId: ID!
      period: AnalyticsPeriod = CURRENT_MONTH
    ): OrganizationUsage @auth(requires: USER) @complexity(value: 8)
  }
  
  extend type Mutation {
    # Organization management
    createOrganization(input: CreateOrganizationInput!): CreateOrganizationPayload! @auth(requires: USER)
    updateOrganization(id: ID!, input: UpdateOrganizationInput!): UpdateOrganizationPayload! @auth(requires: ADMIN)
    deleteOrganization(id: ID!): MutationResponse! @auth(requires: ADMIN)
    
    # Organization membership
    inviteUserToOrganization(input: InviteUserInput!): InviteUserPayload! @auth(requires: ADMIN)
    acceptOrganizationInvite(token: String!): MutationResponse! @auth(requires: USER)
    removeUserFromOrganization(organizationId: ID!, userId: ID!): MutationResponse! @auth(requires: ADMIN)
    updateMemberRole(organizationId: ID!, userId: ID!, role: OrganizationRole!): UpdateMemberRolePayload! @auth(requires: ADMIN)
    leaveOrganization(organizationId: ID!): MutationResponse! @auth(requires: USER)
    
    # Organization settings
    updateOrganizationSettings(organizationId: ID!, input: OrganizationSettingsInput!): UpdateSettingsPayload! @auth(requires: ADMIN)
    updateOrganizationBranding(organizationId: ID!, input: OrganizationBrandingInput!): UpdateBrandingPayload! @auth(requires: ADMIN)
    
    # Teams within organization
    createTeam(organizationId: ID!, input: CreateTeamInput!): CreateTeamPayload! @auth(requires: USER)
    updateTeam(teamId: ID!, input: UpdateTeamInput!): UpdateTeamPayload! @auth(requires: USER)
    deleteTeam(teamId: ID!): MutationResponse! @auth(requires: ADMIN)
    addTeamMember(teamId: ID!, userId: ID!): MutationResponse! @auth(requires: USER)
    removeTeamMember(teamId: ID!, userId: ID!): MutationResponse! @auth(requires: USER)
    
    # Organization billing
    updateBillingInfo(organizationId: ID!, input: BillingInfoInput!): UpdateBillingPayload! @auth(requires: ADMIN)
    changePlan(organizationId: ID!, planId: String!): ChangePlanPayload! @auth(requires: ADMIN)
    addPaymentMethod(organizationId: ID!, input: PaymentMethodInput!): AddPaymentMethodPayload! @auth(requires: ADMIN)
    removePaymentMethod(organizationId: ID!, paymentMethodId: String!): MutationResponse! @auth(requires: ADMIN)
  }
  
  extend type Subscription {
    # Organization subscriptions
    organizationUpdated(organizationId: ID!): Organization! @auth(requires: USER)
    memberJoined(organizationId: ID!): OrganizationMember! @auth(requires: USER)
    memberLeft(organizationId: ID!): OrganizationMember! @auth(requires: USER)
    teamUpdated(teamId: ID!): Team! @auth(requires: USER)
  }
  
  type Organization implements Node @key(fields: "id") {
    id: ID!
    name: String!
    slug: String!
    description: String
    website: String
    
    # Organization branding
    logo: String
    coverImage: String
    primaryColor: String
    
    # Organization type and status
    type: OrganizationType!
    status: OrganizationStatus!
    isVerified: Boolean!
    
    # Plan and billing
    plan: OrganizationPlan! @complexity(value: 3)
    billing: OrganizationBilling @auth(requires: ADMIN) @complexity(value: 5)
    usage: OrganizationUsage @complexity(value: 5)
    
    # Organization settings
    settings: OrganizationSettings! @complexity(value: 3)
    
    # Membership
    owner: User! @complexity(value: 2)
    members(
      pagination: PaginationInput
      filter: MemberFilterInput
      sort: MemberSortInput
    ): OrganizationMemberConnection! @complexity(value: 8)
    memberCount: Int!
    
    # Teams
    teams(
      pagination: PaginationInput
      filter: TeamFilterInput
    ): TeamConnection! @complexity(value: 8)
    
    # Current user's membership
    membership: OrganizationMember @auth(requires: USER) @complexity(value: 2)
    canManage: Boolean! @auth(requires: USER)
    
    # Resources
    files(
      pagination: PaginationInput
      filter: FileFilterInput
    ): FileConnection! @complexity(value: 10)
    
    plugins(
      pagination: PaginationInput
      filter: PluginFilterInput
    ): PluginConnection! @complexity(value: 10)
    
    # Analytics and stats
    stats: OrganizationStats! @complexity(value: 5)
    
    # Activity feed
    activities(
      pagination: PaginationInput
      filter: ActivityFilterInput
    ): ActivityConnection! @complexity(value: 8)
    
    # Invitations
    invitations(
      pagination: PaginationInput
      filter: InvitationFilterInput
    ): OrganizationInvitationConnection! @auth(requires: ADMIN) @complexity(value: 5)
    
    # Timestamps
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  type OrganizationConnection {
    edges: [OrganizationEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type OrganizationEdge {
    node: Organization!
    cursor: String!
  }
  
  enum OrganizationType {
    PERSONAL
    BUSINESS
    ENTERPRISE
    NON_PROFIT
    EDUCATION
  }
  
  enum OrganizationStatus {
    ACTIVE
    SUSPENDED
    TRIAL
    CANCELLED
    PENDING
  }
  
  # Organization membership
  type OrganizationMember implements Node {
    id: ID!
    user: User! @complexity(value: 2)
    organization: Organization! @complexity(value: 2)
    role: OrganizationRole!
    permissions: [Permission!]! @complexity(value: 3)
    
    # Membership status
    status: MembershipStatus!
    isActive: Boolean!
    
    # Teams
    teams: [Team!]! @complexity(value: 5)
    
    # Activity
    lastActive: DateTime
    joinedAt: DateTime!
  }
  
  type OrganizationMemberConnection {
    edges: [OrganizationMemberEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type OrganizationMemberEdge {
    node: OrganizationMember!
    cursor: String!
  }
  
  enum OrganizationRole {
    OWNER
    ADMIN
    MANAGER
    MEMBER
    GUEST
  }
  
  enum MembershipStatus {
    ACTIVE
    INVITED
    SUSPENDED
    LEFT
  }
  
  # Teams within organizations
  type Team implements Node {
    id: ID!
    name: String!
    description: String
    slug: String!
    
    # Team properties
    color: String
    isPrivate: Boolean!
    
    # Relationships
    organization: Organization! @complexity(value: 2)
    members: [OrganizationMember!]! @complexity(value: 5)
    memberCount: Int!
    
    # Team lead
    lead: OrganizationMember @complexity(value: 2)
    
    # Team resources
    files(
      pagination: PaginationInput
      filter: FileFilterInput
    ): FileConnection! @complexity(value: 8)
    
    plugins(
      pagination: PaginationInput
      filter: PluginFilterInput
    ): PluginConnection! @complexity(value: 8)
    
    # Current user's membership
    isMember: Boolean! @auth(requires: USER)
    canManage: Boolean! @auth(requires: USER)
    
    # Timestamps
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  type TeamConnection {
    edges: [TeamEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type TeamEdge {
    node: Team!
    cursor: String!
  }
  
  # Organization plans and billing
  type OrganizationPlan {
    id: String!
    name: String!
    tier: PlanTier!
    
    # Pricing
    price: Float!
    currency: String!
    billingPeriod: BillingPeriod!
    
    # Features and limits
    features: [PlanFeature!]!
    limits: PlanLimits!
    
    # Status
    isActive: Boolean!
    trialEndsAt: DateTime
    nextBillingAt: DateTime
  }
  
  enum PlanTier {
    FREE
    STARTER
    PROFESSIONAL
    BUSINESS
    ENTERPRISE
  }
  
  enum BillingPeriod {
    MONTHLY
    YEARLY
  }
  
  type PlanFeature {
    name: String!
    description: String
    enabled: Boolean!
    limit: Int
  }
  
  type PlanLimits {
    users: Int!
    storage: Int! # in GB
    bandwidth: Int! # in GB
    plugins: Int!
    apiCalls: Int!
    fileUploads: Int!
    videoProcessing: Int! # in hours
  }
  
  type OrganizationBilling {
    # Current plan
    plan: OrganizationPlan!
    
    # Payment information
    paymentMethods: [PaymentMethod!]!
    defaultPaymentMethod: PaymentMethod
    
    # Billing details
    billingEmail: String!
    billingAddress: BillingAddress
    taxId: String
    
    # Invoices and payments
    invoices(
      pagination: PaginationInput
      filter: InvoiceFilterInput
    ): InvoiceConnection! @complexity(value: 8)
    
    # Usage and credits
    currentUsage: OrganizationUsage! @complexity(value: 5)
    credits: Int!
    
    # Subscription status
    subscriptionStatus: SubscriptionStatus!
    trialEndsAt: DateTime
    nextBillingAt: DateTime!
    autoRenew: Boolean!
  }
  
  enum SubscriptionStatus {
    ACTIVE
    TRIAL
    PAST_DUE
    CANCELLED
    EXPIRED
  }
  
  type PaymentMethod {
    id: String!
    type: PaymentMethodType!
    last4: String!
    brand: String
    expiryMonth: Int
    expiryYear: Int
    isDefault: Boolean!
    createdAt: DateTime!
  }
  
  enum PaymentMethodType {
    CREDIT_CARD
    DEBIT_CARD
    PAYPAL
    BANK_ACCOUNT
  }
  
  type BillingAddress {
    line1: String!
    line2: String
    city: String!
    state: String!
    postalCode: String!
    country: String!
  }
  
  type Invoice {
    id: String!
    number: String!
    status: InvoiceStatus!
    amount: Float!
    currency: String!
    tax: Float!
    total: Float!
    dueDate: DateTime!
    paidAt: DateTime
    downloadUrl: String!
    items: [InvoiceItem!]!
    createdAt: DateTime!
  }
  
  type InvoiceConnection {
    edges: [InvoiceEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type InvoiceEdge {
    node: Invoice!
    cursor: String!
  }
  
  enum InvoiceStatus {
    DRAFT
    PENDING
    PAID
    OVERDUE
    CANCELLED
  }
  
  type InvoiceItem {
    description: String!
    quantity: Int!
    unitPrice: Float!
    amount: Float!
  }
  
  # Organization usage and analytics
  type OrganizationUsage {
    period: AnalyticsPeriod!
    
    # Resource usage
    users: UsageMetric!
    storage: UsageMetric!
    bandwidth: UsageMetric!
    apiCalls: UsageMetric!
    fileUploads: UsageMetric!
    videoProcessing: UsageMetric!
    
    # Feature usage
    pluginsInstalled: Int!
    activePlugins: Int!
    executionsThisMonth: Int!
    
    # Overage charges
    overages: [UsageOverage!]!
    estimatedBill: Float!
  }
  
  type UsageMetric {
    current: Float!
    limit: Float!
    percentage: Float!
    trend: Float! # percentage change from previous period
  }
  
  type UsageOverage {
    metric: String!
    amount: Float!
    rate: Float!
    cost: Float!
  }
  
  type OrganizationAnalytics {
    organizationId: ID!
    period: AnalyticsPeriod!
    
    # User analytics
    activeUsers: [AnalyticsDataPoint!]!
    newUsers: [AnalyticsDataPoint!]!
    userRetention: RetentionAnalytics!
    
    # Content analytics
    filesUploaded: [AnalyticsDataPoint!]!
    videosProcessed: [AnalyticsDataPoint!]!
    storageUsage: [AnalyticsDataPoint!]!
    
    # Plugin analytics
    pluginUsage: [PluginUsageAnalytics!]!
    topPlugins: [TopPluginAnalytics!]!
    
    # Collaboration analytics
    teamActivity: [TeamActivityAnalytics!]!
    sharing: [SharingAnalytics!]!
  }
  
  type PluginUsageAnalytics {
    plugin: Plugin! @complexity(value: 2)
    executions: Int!
    users: Int!
    successRate: Float!
    trend: Float!
  }
  
  type TopPluginAnalytics {
    plugin: Plugin! @complexity(value: 2)
    rank: Int!
    score: Float!
    executions: Int!
    users: Int!
  }
  
  type TeamActivityAnalytics {
    team: Team! @complexity(value: 2)
    activity: Int!
    files: Int!
    collaborations: Int!
    trend: Float!
  }
  
  type SharingAnalytics {
    internal: Int!
    external: Int!
    public: Int!
    trend: Float!
  }
  
  type OrganizationStats {
    memberCount: Int!
    teamCount: Int!
    fileCount: Int!
    totalStorage: Int!
    pluginCount: Int!
    monthlyActiveUsers: Int!
    
    # Growth metrics
    memberGrowth: Float! # monthly percentage
    storageGrowth: Float!
    activityGrowth: Float!
  }
  
  # Organization settings
  type OrganizationSettings {
    # General settings
    allowPublicSharing: Boolean!
    requireTwoFactor: Boolean!
    allowGuestAccess: Boolean!
    
    # File settings
    maxFileSize: Int!
    allowedFileTypes: [String!]!
    autoDeleteFiles: Boolean!
    autoDeleteDays: Int!
    
    # Plugin settings
    allowPluginInstallation: Boolean!
    allowThirdPartyPlugins: Boolean!
    pluginApprovalRequired: Boolean!
    
    # Security settings
    ipWhitelist: [String!]!
    sessionTimeout: Int!
    passwordPolicy: PasswordPolicy!
    
    # Integration settings
    ssoEnabled: Boolean!
    ssoProvider: String
    webhookUrl: String
    
    # Notification settings
    emailNotifications: Boolean!
    slackIntegration: SlackIntegration
    
    # Branding
    customDomain: String
    customBranding: Boolean!
  }
  
  type PasswordPolicy {
    minLength: Int!
    requireUppercase: Boolean!
    requireLowercase: Boolean!
    requireNumbers: Boolean!
    requireSymbols: Boolean!
    maxAge: Int! # days
  }
  
  type SlackIntegration {
    enabled: Boolean!
    teamName: String
    channel: String
    notifications: [String!]!
  }
  
  # Organization invitations
  type OrganizationInvitation implements Node {
    id: ID!
    organization: Organization! @complexity(value: 2)
    email: String!
    role: OrganizationRole!
    invitedBy: User! @complexity(value: 2)
    
    # Invitation status
    status: InvitationStatus!
    acceptedBy: User @complexity(value: 2)
    
    # Timestamps
    expiresAt: DateTime!
    acceptedAt: DateTime
    createdAt: DateTime!
  }
  
  type OrganizationInvitationConnection {
    edges: [OrganizationInvitationEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type OrganizationInvitationEdge {
    node: OrganizationInvitation!
    cursor: String!
  }
  
  enum InvitationStatus {
    PENDING
    ACCEPTED
    DECLINED
    EXPIRED
    CANCELLED
  }
  
  # Input types
  input CreateOrganizationInput {
    name: String!
    slug: String
    description: String
    type: OrganizationType!
    website: String
    planId: String = "free"
  }
  
  input UpdateOrganizationInput {
    name: String
    slug: String
    description: String
    website: String
    logo: Upload
    coverImage: Upload
    primaryColor: String
  }
  
  input InviteUserInput {
    organizationId: ID!
    email: String!
    role: OrganizationRole!
    teamIds: [ID!]
    message: String
  }
  
  input OrganizationSettingsInput {
    allowPublicSharing: Boolean
    requireTwoFactor: Boolean
    allowGuestAccess: Boolean
    maxFileSize: Int
    allowedFileTypes: [String!]
    autoDeleteFiles: Boolean
    autoDeleteDays: Int
    allowPluginInstallation: Boolean
    allowThirdPartyPlugins: Boolean
    pluginApprovalRequired: Boolean
    ipWhitelist: [String!]
    sessionTimeout: Int
    passwordPolicy: PasswordPolicyInput
    webhookUrl: String
    emailNotifications: Boolean
    customDomain: String
    customBranding: Boolean
  }
  
  input PasswordPolicyInput {
    minLength: Int
    requireUppercase: Boolean
    requireLowercase: Boolean
    requireNumbers: Boolean
    requireSymbols: Boolean
    maxAge: Int
  }
  
  input OrganizationBrandingInput {
    logo: Upload
    coverImage: Upload
    primaryColor: String
    customDomain: String
  }
  
  input CreateTeamInput {
    name: String!
    description: String
    slug: String
    color: String
    isPrivate: Boolean = false
    memberIds: [ID!]
    leadId: ID
  }
  
  input UpdateTeamInput {
    name: String
    description: String
    color: String
    isPrivate: Boolean
    leadId: ID
  }
  
  input BillingInfoInput {
    billingEmail: String!
    billingAddress: BillingAddressInput
    taxId: String
  }
  
  input BillingAddressInput {
    line1: String!
    line2: String
    city: String!
    state: String!
    postalCode: String!
    country: String!
  }
  
  input PaymentMethodInput {
    type: PaymentMethodType!
    token: String! # Payment processor token
    isDefault: Boolean = false
  }
  
  input OrganizationFilterInput {
    name: String
    type: OrganizationType
    status: OrganizationStatus
    planTier: PlanTier
    isVerified: Boolean
    createdAfter: DateTime
    createdBefore: DateTime
  }
  
  input MemberFilterInput {
    role: OrganizationRole
    status: MembershipStatus
    teamId: ID
    joinedAfter: DateTime
    joinedBefore: DateTime
  }
  
  input MemberSortInput {
    field: MemberSortField!
    order: SortOrder = ASC
  }
  
  enum MemberSortField {
    NAME
    ROLE
    JOINED_AT
    LAST_ACTIVE
  }
  
  input TeamFilterInput {
    name: String
    isPrivate: Boolean
    createdAfter: DateTime
    createdBefore: DateTime
  }
  
  input InvitationFilterInput {
    status: InvitationStatus
    role: OrganizationRole
    createdAfter: DateTime
    createdBefore: DateTime
  }
  
  input InvoiceFilterInput {
    status: InvoiceStatus
    dateFrom: DateTime
    dateTo: DateTime
    minAmount: Float
    maxAmount: Float
  }
  
  # Response types
  type CreateOrganizationPayload {
    success: Boolean!
    organization: Organization
    errors: [Error!]
  }
  
  type UpdateOrganizationPayload {
    success: Boolean!
    organization: Organization
    errors: [Error!]
  }
  
  type InviteUserPayload {
    success: Boolean!
    invitation: OrganizationInvitation
    errors: [Error!]
  }
  
  type UpdateMemberRolePayload {
    success: Boolean!
    member: OrganizationMember
    errors: [Error!]
  }
  
  type UpdateSettingsPayload {
    success: Boolean!
    settings: OrganizationSettings
    errors: [Error!]
  }
  
  type UpdateBrandingPayload {
    success: Boolean!
    organization: Organization
    errors: [Error!]
  }
  
  type CreateTeamPayload {
    success: Boolean!
    team: Team
    errors: [Error!]
  }
  
  type UpdateTeamPayload {
    success: Boolean!
    team: Team
    errors: [Error!]
  }
  
  type UpdateBillingPayload {
    success: Boolean!
    billing: OrganizationBilling
    errors: [Error!]
  }
  
  type ChangePlanPayload {
    success: Boolean!
    plan: OrganizationPlan
    prorationAmount: Float
    nextBillingAt: DateTime
    errors: [Error!]
  }
  
  type AddPaymentMethodPayload {
    success: Boolean!
    paymentMethod: PaymentMethod
    errors: [Error!]
  }
`;