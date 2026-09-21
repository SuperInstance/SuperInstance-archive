import { gql } from 'apollo-server-express';

export const pluginTypeDefs = gql`
  extend type Query {
    # Plugin queries
    plugin(id: ID!): Plugin @auth(requires: USER) @complexity(value: 3)
    plugins(
      pagination: PaginationInput
      sort: SortInput
      filter: PluginFilterInput
    ): PluginConnection! @complexity(value: 8) @rateLimit(max: 50, window: 60)
    
    # Plugin marketplace
    marketplacePlugins(
      pagination: PaginationInput
      sort: PluginSortInput
      filter: MarketplaceFilterInput
    ): MarketplacePluginConnection! @complexity(value: 10) @rateLimit(max: 100, window: 60)
    
    # Plugin installation
    installedPlugins(
      pagination: PaginationInput
      filter: InstalledPluginFilterInput
    ): PluginInstallationConnection! @auth(requires: USER) @complexity(value: 8)
    
    # Plugin development
    pluginManifest(id: ID!): PluginManifest @auth(requires: USER) @complexity(value: 2)
    pluginVersions(pluginId: ID!): [PluginVersion!]! @auth(requires: USER) @complexity(value: 5)
    
    # Plugin execution
    pluginExecution(id: ID!): PluginExecution @auth(requires: USER) @complexity(value: 3)
    pluginExecutions(
      pagination: PaginationInput
      filter: PluginExecutionFilterInput
    ): PluginExecutionConnection! @auth(requires: USER) @complexity(value: 8)
    
    # Plugin analytics
    pluginAnalytics(
      pluginId: ID!
      period: AnalyticsPeriod = LAST_30_DAYS
    ): PluginAnalytics @auth(requires: USER) @complexity(value: 5)
    
    # Search plugins
    searchPlugins(
      query: String!
      pagination: PaginationInput
      filter: PluginSearchFilterInput
    ): PluginSearchConnection! @complexity(value: 12) @rateLimit(max: 20, window: 60)
  }
  
  extend type Mutation {
    # Plugin installation and management
    installPlugin(input: InstallPluginInput!): InstallPluginPayload! @auth(requires: USER)
    uninstallPlugin(pluginId: ID!): MutationResponse! @auth(requires: USER)
    updatePlugin(pluginId: ID!, version: String): UpdatePluginPayload! @auth(requires: USER)
    
    # Plugin configuration
    configurePlugin(pluginId: ID!, input: PluginConfigInput!): ConfigurePluginPayload! @auth(requires: USER)
    
    # Plugin activation/deactivation
    activatePlugin(pluginId: ID!): MutationResponse! @auth(requires: USER)
    deactivatePlugin(pluginId: ID!): MutationResponse! @auth(requires: USER)
    
    # Plugin execution
    executePlugin(input: ExecutePluginInput!): ExecutePluginPayload! @auth(requires: USER) @rateLimit(max: 10, window: 60)
    cancelPluginExecution(executionId: ID!): MutationResponse! @auth(requires: USER)
    
    # Plugin development
    createPlugin(input: CreatePluginInput!): CreatePluginPayload! @auth(requires: USER)
    updatePluginManifest(pluginId: ID!, input: UpdateManifestInput!): UpdateManifestPayload! @auth(requires: USER)
    publishPlugin(pluginId: ID!, input: PublishPluginInput!): PublishPluginPayload! @auth(requires: USER)
    
    # Plugin marketplace
    submitPluginReview(input: SubmitReviewInput!): SubmitReviewPayload! @auth(requires: USER)
    updatePluginReview(reviewId: ID!, input: UpdateReviewInput!): UpdateReviewPayload! @auth(requires: USER)
    deletePluginReview(reviewId: ID!): MutationResponse! @auth(requires: USER)
    
    # Plugin resource management
    updatePluginQuota(pluginId: ID!, input: PluginQuotaInput!): UpdateQuotaPayload! @auth(requires: ADMIN)
  }
  
  extend type Subscription {
    # Plugin subscriptions
    pluginInstalled(userId: ID!): PluginInstallation! @auth(requires: USER)
    pluginExecutionUpdate(executionId: ID!): PluginExecutionUpdate! @auth(requires: USER)
    pluginStatusChanged(pluginId: ID!): PluginStatusUpdate! @auth(requires: USER)
    marketplaceUpdate: MarketplaceUpdate!
  }
  
  type Plugin implements Node @key(fields: "id") {
    id: ID!
    name: String!
    displayName: String!
    description: String!
    version: String!
    
    # Plugin metadata
    author: PluginAuthor!
    category: PluginCategory!
    tags: [String!]!
    license: String
    homepage: String
    repository: String
    
    # Plugin runtime
    runtime: PluginRuntime!
    
    # Plugin manifest
    manifest: PluginManifest! @complexity(value: 3)
    
    # Plugin permissions and resources
    permissions: PluginPermissions! @complexity(value: 2)
    resources: PluginResources! @complexity(value: 2)
    
    # Plugin status
    status: PluginStatus!
    isPublished: Boolean!
    isVerified: Boolean!
    isFeatured: Boolean!
    
    # Marketplace information
    marketplace: PluginMarketplace @complexity(value: 3)
    
    # Plugin statistics
    stats: PluginStats! @complexity(value: 5)
    
    # User-specific data
    installation: PluginInstallation @auth(requires: USER) @complexity(value: 3)
    isInstalled: Boolean! @auth(requires: USER)
    canInstall: Boolean! @auth(requires: USER)
    
    # Plugin versions
    versions: [PluginVersion!]! @complexity(value: 5)
    latestVersion: String!
    
    # Plugin reviews and ratings
    reviews(
      pagination: PaginationInput
      sort: ReviewSortInput
    ): PluginReviewConnection! @complexity(value: 8)
    rating: PluginRating! @complexity(value: 2)
    
    # Plugin documentation
    documentation: PluginDocumentation @complexity(value: 5)
    
    # Plugin executions (for installed plugins)
    executions(
      pagination: PaginationInput
      filter: PluginExecutionFilterInput
    ): PluginExecutionConnection! @auth(requires: USER) @complexity(value: 8)
    
    # Dependencies
    dependencies: [PluginDependency!]! @complexity(value: 3)
    dependents: [Plugin!]! @complexity(value: 8)
    
    # Timestamps
    createdAt: DateTime!
    updatedAt: DateTime!
    publishedAt: DateTime
  }
  
  type PluginConnection {
    edges: [PluginEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
    facets: PluginFacets!
  }
  
  type PluginEdge {
    node: Plugin!
    cursor: String!
  }
  
  type PluginFacets {
    categories: [CategoryFacet!]!
    runtimes: [RuntimeFacet!]!
    authors: [AuthorFacet!]!
    tags: [TagFacet!]!
  }
  
  type CategoryFacet {
    category: PluginCategory!
    count: Int!
  }
  
  type RuntimeFacet {
    runtime: String!
    count: Int!
  }
  
  type AuthorFacet {
    author: String!
    count: Int!
  }
  
  type TagFacet {
    tag: String!
    count: Int!
  }
  
  enum PluginCategory {
    DATA_IMPORT
    DATA_EXPORT
    ANALYTICS
    AUTOMATION
    INTEGRATION
    UTILITY
    VISUALIZATION
    AI_ML
    SECURITY
    PRODUCTIVITY
  }
  
  enum PluginStatus {
    DRAFT
    REVIEW
    APPROVED
    PUBLISHED
    DEPRECATED
    ARCHIVED
  }
  
  type PluginAuthor {
    name: String!
    email: String
    url: String
    avatar: String
    verified: Boolean!
  }
  
  type PluginRuntime {
    type: RuntimeType!
    version: String
    environment: RuntimeEnvironment
  }
  
  enum RuntimeType {
    TYPESCRIPT
    PYTHON
    DOCKER
    WASM
  }
  
  enum RuntimeEnvironment {
    NODE
    BROWSER
    PYTHON3
    DOCKER
    WASM
  }
  
  type PluginManifest {
    name: String!
    version: String!
    displayName: String!
    description: String!
    main: String!
    runtime: PluginRuntime!
    permissions: PluginPermissions!
    resources: PluginResources
    triggers: [PluginTrigger!]!
    config: PluginConfig
    dependencies: PluginDependencies
    ui: PluginUI
    api: PluginAPI
    compatibility: PluginCompatibility
  }
  
  type PluginPermissions {
    network: NetworkPermissions
    filesystem: FilesystemPermissions
    database: DatabasePermissions
    services: [String!]!
  }
  
  type NetworkPermissions {
    enabled: Boolean!
    domains: [String!]!
    ports: [Int!]!
  }
  
  type FilesystemPermissions {
    read: [String!]!
    write: [String!]!
    temp: Boolean!
  }
  
  type DatabasePermissions {
    read: Boolean!
    write: Boolean!
    tables: [String!]!
  }
  
  type PluginResources {
    cpu: Float!
    memory: String!
    disk: String!
    network: String
    timeout: Int!
  }
  
  type PluginTrigger {
    type: TriggerType!
    config: JSON!
  }
  
  enum TriggerType {
    FILE_UPLOAD
    FILE_CHANGE
    SCHEDULE
    WEBHOOK
    USER_ACTION
    SYSTEM_EVENT
  }
  
  type PluginConfig {
    schema: JSON
    defaults: JSON
  }
  
  type PluginDependencies {
    plugins: JSON
    npm: JSON
    pip: JSON
  }
  
  type PluginUI {
    settings: String
    dashboard: String
    icon: String
  }
  
  type PluginAPI {
    endpoints: [APIEndpoint!]!
  }
  
  type APIEndpoint {
    path: String!
    method: String!
    description: String
  }
  
  type PluginCompatibility {
    activelogVersion: String
    os: [String!]!
    arch: [String!]!
  }
  
  # Plugin marketplace
  type PluginMarketplace {
    pricing: PluginPricing
    featured: Boolean!
    verified: Boolean!
    downloads: Int!
    lastDownload: DateTime
  }
  
  type PluginPricing {
    model: PricingModel!
    price: Float
    currency: String
    trial: Boolean!
    trialDuration: Int
  }
  
  enum PricingModel {
    FREE
    FREEMIUM
    PAID
    SUBSCRIPTION
  }
  
  type MarketplacePluginConnection {
    edges: [MarketplacePluginEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
    facets: PluginFacets!
  }
  
  type MarketplacePluginEdge {
    node: Plugin!
    cursor: String!
    featured: Boolean!
    trending: Boolean!
  }
  
  # Plugin installation
  type PluginInstallation implements Node {
    id: ID!
    plugin: Plugin! @complexity(value: 3)
    user: User! @complexity(value: 2)
    version: String!
    
    # Installation status
    status: InstallationStatus!
    isActive: Boolean!
    
    # Configuration
    config: JSON!
    
    # Usage statistics
    lastUsed: DateTime
    usageCount: Int!
    
    # Resource usage
    resourceUsage: PluginResourceUsage @complexity(value: 3)
    
    # Installation details
    installedAt: DateTime!
    updatedAt: DateTime!
    autoUpdate: Boolean!
  }
  
  type PluginInstallationConnection {
    edges: [PluginInstallationEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type PluginInstallationEdge {
    node: PluginInstallation!
    cursor: String!
  }
  
  enum InstallationStatus {
    INSTALLING
    INSTALLED
    UPDATING
    ERROR
    UNINSTALLING
  }
  
  type PluginResourceUsage {
    cpu: ResourceUsageStats!
    memory: ResourceUsageStats!
    disk: ResourceUsageStats!
    network: ResourceUsageStats!
    executions: Int!
    lastReset: DateTime!
  }
  
  type ResourceUsageStats {
    current: Float!
    peak: Float!
    average: Float!
    limit: Float!
    percentage: Float!
  }
  
  # Plugin versions
  type PluginVersion {
    version: String!
    changelog: String
    isStable: Boolean!
    isDeprecated: Boolean!
    downloadUrl: String!
    packageSize: Int!
    packageHash: String!
    createdAt: DateTime!
  }
  
  # Plugin execution
  type PluginExecution implements Node {
    id: ID!
    plugin: Plugin! @complexity(value: 2)
    user: User! @complexity(value: 2)
    
    # Execution details
    trigger: ExecutionTrigger!
    input: JSON
    output: JSON
    
    # Execution status
    status: ExecutionStatus!
    progress: Float
    
    # Performance metrics
    startedAt: DateTime!
    completedAt: DateTime
    duration: Float
    
    # Resource usage
    resourceUsage: ExecutionResourceUsage
    
    # Error information
    error: String
    stackTrace: String
    
    # Execution context
    environment: JSON
    logs: [ExecutionLog!]! @complexity(value: 5)
  }
  
  type PluginExecutionConnection {
    edges: [PluginExecutionEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type PluginExecutionEdge {
    node: PluginExecution!
    cursor: String!
  }
  
  type ExecutionTrigger {
    type: TriggerType!
    data: JSON
    source: String
  }
  
  enum ExecutionStatus {
    PENDING
    RUNNING
    COMPLETED
    FAILED
    CANCELLED
    TIMEOUT
  }
  
  type ExecutionResourceUsage {
    cpuTime: Float!
    memoryPeak: Int!
    diskRead: Int!
    diskWrite: Int!
    networkIn: Int!
    networkOut: Int!
  }
  
  type ExecutionLog {
    id: ID!
    level: LogLevel!
    message: String!
    timestamp: DateTime!
    metadata: JSON
  }
  
  enum LogLevel {
    DEBUG
    INFO
    WARN
    ERROR
  }
  
  # Plugin statistics
  type PluginStats {
    downloads: Int!
    installations: Int!
    activeInstallations: Int!
    executions: Int!
    successRate: Float!
    averageRating: Float!
    reviewCount: Int!
    
    # Time-based stats
    dailyExecutions: [AnalyticsDataPoint!]!
    weeklyDownloads: [AnalyticsDataPoint!]!
    monthlyUsers: [AnalyticsDataPoint!]!
  }
  
  # Plugin reviews
  type PluginReview implements Node {
    id: ID!
    plugin: Plugin! @complexity(value: 2)
    user: User! @complexity(value: 2)
    
    # Review content
    rating: Int! # 1-5 stars
    title: String!
    comment: String
    
    # Review status
    isVerified: Boolean!
    isHelpful: Int! # helpful votes
    
    # Version reviewed
    version: String!
    
    # Timestamps
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  type PluginReviewConnection {
    edges: [PluginReviewEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
    averageRating: Float!
    ratingDistribution: [RatingDistribution!]!
  }
  
  type PluginReviewEdge {
    node: PluginReview!
    cursor: String!
  }
  
  type RatingDistribution {
    rating: Int!
    count: Int!
    percentage: Float!
  }
  
  type PluginRating {
    average: Float!
    count: Int!
    distribution: [RatingDistribution!]!
  }
  
  # Plugin documentation
  type PluginDocumentation {
    readme: String
    changelog: String
    api: String
    examples: [PluginExample!]!
    guides: [PluginGuide!]!
  }
  
  type PluginExample {
    title: String!
    description: String
    code: String!
    language: String!
  }
  
  type PluginGuide {
    title: String!
    content: String!
    order: Int!
  }
  
  # Plugin dependencies
  type PluginDependency {
    name: String!
    version: String!
    type: DependencyType!
    required: Boolean!
    satisfied: Boolean!
  }
  
  enum DependencyType {
    PLUGIN
    NPM
    PIP
    SYSTEM
  }
  
  # Plugin analytics
  type PluginAnalytics {
    pluginId: ID!
    period: AnalyticsPeriod!
    
    # Usage analytics
    executions: [AnalyticsDataPoint!]!
    users: [AnalyticsDataPoint!]!
    successRate: [AnalyticsDataPoint!]!
    
    # Performance analytics
    averageDuration: [AnalyticsDataPoint!]!
    resourceUsage: PluginResourceAnalytics!
    
    # Error analytics
    errorRate: [AnalyticsDataPoint!]!
    errorTypes: [ErrorAnalytics!]!
    
    # User analytics
    topUsers: [UserAnalytics!]!
    userRetention: RetentionAnalytics!
  }
  
  type PluginResourceAnalytics {
    cpu: [AnalyticsDataPoint!]!
    memory: [AnalyticsDataPoint!]!
    disk: [AnalyticsDataPoint!]!
    network: [AnalyticsDataPoint!]!
  }
  
  type ErrorAnalytics {
    type: String!
    count: Int!
    percentage: Float!
    trend: Float!
  }
  
  type UserAnalytics {
    user: User! @complexity(value: 2)
    executions: Int!
    lastUsed: DateTime!
    successRate: Float!
  }
  
  type RetentionAnalytics {
    day1: Float!
    day7: Float!
    day30: Float!
    day90: Float!
  }
  
  # Search results
  type PluginSearchConnection {
    edges: [PluginSearchEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
    facets: PluginFacets!
    suggestions: [String!]!
  }
  
  type PluginSearchEdge {
    node: Plugin!
    cursor: String!
    score: Float!
    highlights: JSON
  }
  
  # Input types
  input PluginFilterInput {
    category: PluginCategory
    runtime: RuntimeType
    author: String
    tags: [String!]
    isPublished: Boolean
    isVerified: Boolean
    isFeatured: Boolean
    priceMin: Float
    priceMax: Float
    createdAfter: DateTime
    createdBefore: DateTime
  }
  
  input MarketplaceFilterInput {
    category: PluginCategory
    runtime: RuntimeType
    pricing: PricingModel
    verified: Boolean
    featured: Boolean
    minRating: Float
    tags: [String!]
  }
  
  input PluginSortInput {
    field: PluginSortField!
    order: SortOrder = ASC
  }
  
  enum PluginSortField {
    NAME
    CREATED_AT
    UPDATED_AT
    DOWNLOADS
    RATING
    POPULARITY
  }
  
  input InstalledPluginFilterInput {
    status: InstallationStatus
    isActive: Boolean
    category: PluginCategory
    lastUsedAfter: DateTime
    lastUsedBefore: DateTime
  }
  
  input PluginSearchFilterInput {
    category: PluginCategory
    runtime: RuntimeType
    pricing: PricingModel
    minRating: Float
    tags: [String!]
  }
  
  input PluginExecutionFilterInput {
    pluginId: ID
    status: ExecutionStatus
    triggerType: TriggerType
    startedAfter: DateTime
    startedBefore: DateTime
  }
  
  input ReviewSortInput {
    field: ReviewSortField!
    order: SortOrder = DESC
  }
  
  enum ReviewSortField {
    CREATED_AT
    RATING
    HELPFUL
  }
  
  input InstallPluginInput {
    pluginId: ID!
    version: String
    config: JSON
    autoUpdate: Boolean = true
  }
  
  input PluginConfigInput {
    config: JSON!
    validate: Boolean = true
  }
  
  input ExecutePluginInput {
    pluginId: ID!
    trigger: ExecutionTriggerInput!
    input: JSON
    priority: ExecutionPriority = NORMAL
    timeout: Int
  }
  
  input ExecutionTriggerInput {
    type: TriggerType!
    data: JSON
    source: String
  }
  
  enum ExecutionPriority {
    LOW
    NORMAL
    HIGH
    URGENT
  }
  
  input CreatePluginInput {
    name: String!
    displayName: String!
    description: String!
    category: PluginCategory!
    runtime: RuntimeType!
    manifest: PluginManifestInput!
    packageFile: Upload!
  }
  
  input PluginManifestInput {
    version: String!
    main: String!
    permissions: PluginPermissionsInput!
    resources: PluginResourcesInput
    triggers: [PluginTriggerInput!]
    config: PluginConfigSchemaInput
    dependencies: PluginDependenciesInput
    ui: PluginUIInput
    api: PluginAPIInput
    compatibility: PluginCompatibilityInput
  }
  
  input PluginPermissionsInput {
    network: NetworkPermissionsInput
    filesystem: FilesystemPermissionsInput
    database: DatabasePermissionsInput
    services: [String!]
  }
  
  input NetworkPermissionsInput {
    enabled: Boolean!
    domains: [String!]
    ports: [Int!]
  }
  
  input FilesystemPermissionsInput {
    read: [String!]
    write: [String!]
    temp: Boolean
  }
  
  input DatabasePermissionsInput {
    read: Boolean
    write: Boolean
    tables: [String!]
  }
  
  input PluginResourcesInput {
    cpu: Float
    memory: String
    disk: String
    network: String
    timeout: Int
  }
  
  input PluginTriggerInput {
    type: TriggerType!
    config: JSON!
  }
  
  input PluginConfigSchemaInput {
    schema: JSON
    defaults: JSON
  }
  
  input PluginDependenciesInput {
    plugins: JSON
    npm: JSON
    pip: JSON
  }
  
  input PluginUIInput {
    settings: String
    dashboard: String
    icon: String
  }
  
  input PluginAPIInput {
    endpoints: [APIEndpointInput!]
  }
  
  input APIEndpointInput {
    path: String!
    method: String!
    description: String
  }
  
  input PluginCompatibilityInput {
    activelogVersion: String
    os: [String!]
    arch: [String!]
  }
  
  input UpdateManifestInput {
    version: String
    description: String
    permissions: PluginPermissionsInput
    resources: PluginResourcesInput
    triggers: [PluginTriggerInput!]
    config: PluginConfigSchemaInput
    dependencies: PluginDependenciesInput
    ui: PluginUIInput
    api: PluginAPIInput
    compatibility: PluginCompatibilityInput
  }
  
  input PublishPluginInput {
    version: String!
    changelog: String!
    packageFile: Upload
    pricing: PluginPricingInput
  }
  
  input PluginPricingInput {
    model: PricingModel!
    price: Float
    currency: String
    trial: Boolean
    trialDuration: Int
  }
  
  input SubmitReviewInput {
    pluginId: ID!
    rating: Int! # 1-5
    title: String!
    comment: String
    version: String!
  }
  
  input UpdateReviewInput {
    rating: Int
    title: String
    comment: String
  }
  
  input PluginQuotaInput {
    cpu: Float
    memory: String
    disk: String
    network: String
    executions: Int
    resetPeriod: String
  }
  
  # Response types
  type InstallPluginPayload {
    success: Boolean!
    installation: PluginInstallation
    errors: [Error!]
  }
  
  type UpdatePluginPayload {
    success: Boolean!
    installation: PluginInstallation
    changelog: String
    errors: [Error!]
  }
  
  type ConfigurePluginPayload {
    success: Boolean!
    installation: PluginInstallation
    validationErrors: [ValidationError!]
  }
  
  type ValidationError {
    field: String!
    message: String!
    code: String
  }
  
  type ExecutePluginPayload {
    success: Boolean!
    execution: PluginExecution
    errors: [Error!]
  }
  
  type CreatePluginPayload {
    success: Boolean!
    plugin: Plugin
    errors: [Error!]
  }
  
  type UpdateManifestPayload {
    success: Boolean!
    plugin: Plugin
    validationErrors: [ValidationError!]
  }
  
  type PublishPluginPayload {
    success: Boolean!
    plugin: Plugin
    version: PluginVersion
    errors: [Error!]
  }
  
  type SubmitReviewPayload {
    success: Boolean!
    review: PluginReview
    errors: [Error!]
  }
  
  type UpdateReviewPayload {
    success: Boolean!
    review: PluginReview
    errors: [Error!]
  }
  
  type UpdateQuotaPayload {
    success: Boolean!
    quota: PluginQuota
    errors: [Error!]
  }
  
  type PluginQuota {
    pluginId: ID!
    userId: ID!
    cpu: Float!
    memory: String!
    disk: String!
    network: String!
    executions: Int!
    resetPeriod: String!
    currentUsage: PluginResourceUsage!
    resetAt: DateTime!
  }
  
  # Subscription types
  type PluginExecutionUpdate {
    executionId: ID!
    status: ExecutionStatus!
    progress: Float
    output: JSON
    error: String
    resourceUsage: ExecutionResourceUsage
  }
  
  type PluginStatusUpdate {
    pluginId: ID!
    status: PluginStatus!
    installation: PluginInstallation
    message: String
  }
  
  type MarketplaceUpdate {
    type: MarketplaceUpdateType!
    plugin: Plugin!
    data: JSON
  }
  
  enum MarketplaceUpdateType {
    NEW_PLUGIN
    PLUGIN_UPDATED
    PLUGIN_FEATURED
    PLUGIN_VERIFIED
  }
`;