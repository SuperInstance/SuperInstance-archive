import { gql } from 'apollo-server-express';

export const analyticsTypeDefs = gql`
  extend type Query {
    # Analytics queries
    analytics(input: AnalyticsQueryInput!): AnalyticsResult! 
      @auth(requires: USER) @complexity(value: 10) @rateLimit(max: 100, window: 300)
    
    # Dashboard analytics
    dashboardAnalytics(
      period: AnalyticsPeriod = LAST_30_DAYS
      timezone: String
    ): DashboardAnalytics! @auth(requires: USER) @complexity(value: 15)
    
    # Real-time analytics
    realtimeAnalytics: RealtimeAnalytics! @auth(requires: USER) @complexity(value: 8) @cache(ttl: 30)
    
    # Funnel analysis
    funnelAnalytics(input: FunnelAnalyticsInput!): FunnelAnalyticsResult! 
      @auth(requires: USER) @complexity(value: 12)
    
    # Cohort analysis
    cohortAnalytics(input: CohortAnalyticsInput!): CohortAnalyticsResult! 
      @auth(requires: USER) @complexity(value: 15)
    
    # Custom reports
    customReport(reportId: ID!): CustomReport! @auth(requires: USER) @complexity(value: 8)
    customReports(
      pagination: PaginationInput
      filter: CustomReportFilterInput
    ): CustomReportConnection! @auth(requires: USER) @complexity(value: 8)
    
    # A/B testing analytics
    experimentAnalytics(experimentId: ID!): ExperimentAnalytics! 
      @auth(requires: USER) @complexity(value: 10)
    
    # Heat maps and session recordings
    heatmapData(input: HeatmapQueryInput!): HeatmapData! 
      @auth(requires: USER) @complexity(value: 12)
    sessionRecordings(
      pagination: PaginationInput
      filter: SessionRecordingFilterInput
    ): SessionRecordingConnection! @auth(requires: USER) @complexity(value: 10)
  }
  
  extend type Mutation {
    # Analytics tracking
    trackEvent(input: TrackEventInput!): MutationResponse! @auth(requires: USER) @rateLimit(max: 1000, window: 60)
    trackEvents(input: [TrackEventInput!]!): BatchMutationResponse! @auth(requires: USER) @rateLimit(max: 100, window: 60)
    
    # Custom reports
    createCustomReport(input: CreateCustomReportInput!): CreateCustomReportPayload! @auth(requires: USER)
    updateCustomReport(id: ID!, input: UpdateCustomReportInput!): UpdateCustomReportPayload! @auth(requires: USER)
    deleteCustomReport(id: ID!): MutationResponse! @auth(requires: USER)
    scheduleReport(id: ID!, input: ScheduleReportInput!): ScheduleReportPayload! @auth(requires: USER)
    
    # Analytics settings
    updateAnalyticsSettings(input: AnalyticsSettingsInput!): UpdateAnalyticsSettingsPayload! @auth(requires: USER)
    
    # Data retention
    purgeAnalyticsData(input: PurgeDataInput!): PurgeDataPayload! @auth(requires: ADMIN)
    exportAnalyticsData(input: ExportDataInput!): ExportDataPayload! @auth(requires: USER)
    
    # Goals and conversions
    createGoal(input: CreateGoalInput!): CreateGoalPayload! @auth(requires: USER)
    updateGoal(id: ID!, input: UpdateGoalInput!): UpdateGoalPayload! @auth(requires: USER)
    deleteGoal(id: ID!): MutationResponse! @auth(requires: USER)
  }
  
  extend type Subscription {
    # Real-time analytics subscriptions
    realtimeUpdates(userId: ID!): RealtimeUpdate! @auth(requires: USER)
    analyticsAlert(alertId: ID!): AnalyticsAlert! @auth(requires: USER)
  }
  
  # Core analytics types
  type AnalyticsResult {
    query: AnalyticsQueryInput!
    data: [AnalyticsDataPoint!]!
    metadata: AnalyticsMetadata!
    summary: AnalyticsSummary!
    timeRange: TimeRange!
    segments: [AnalyticsSegment!]!
  }
  
  type AnalyticsDataPoint {
    timestamp: DateTime!
    value: Float!
    label: String
    dimensions: JSON
    metadata: JSON
  }
  
  enum AnalyticsPeriod {
    LAST_HOUR
    LAST_24_HOURS
    LAST_7_DAYS
    LAST_30_DAYS
    LAST_90_DAYS
    LAST_YEAR
    THIS_WEEK
    THIS_MONTH
    THIS_QUARTER
    THIS_YEAR
    CUSTOM
    CURRENT_MONTH
    PREVIOUS_MONTH
    CURRENT_QUARTER
    PREVIOUS_QUARTER
    CURRENT_YEAR
    PREVIOUS_YEAR
  }
  
  type AnalyticsMetadata {
    totalCount: Int!
    uniqueCount: Int!
    conversionRate: Float
    averageValue: Float
    medianValue: Float
    percentiles: JSON
    trend: TrendAnalysis!
    seasonality: SeasonalityAnalysis
  }
  
  type TrendAnalysis {
    direction: TrendDirection!
    strength: Float! # 0-1
    changePercentage: Float!
    changeAbsolute: Float!
    confidence: Float! # 0-1
    forecast: [AnalyticsDataPoint!]!
  }
  
  enum TrendDirection {
    UP
    DOWN
    STABLE
  }
  
  type SeasonalityAnalysis {
    hasSeasonality: Boolean!
    patterns: [SeasonalPattern!]!
    bestPeriods: [TimeOfDay!]!
    worstPeriods: [TimeOfDay!]!
  }
  
  type SeasonalPattern {
    period: SeasonalPeriod!
    strength: Float!
    description: String!
  }
  
  enum SeasonalPeriod {
    HOURLY
    DAILY
    WEEKLY
    MONTHLY
    QUARTERLY
  }
  
  type TimeOfDay {
    hour: Int!
    dayOfWeek: Int!
    value: Float!
    confidence: Float!
  }
  
  type AnalyticsSummary {
    total: Float!
    change: Float!
    changePercentage: Float!
    previousPeriod: Float!
    benchmark: Float
    targets: [AnalyticsTarget!]!
  }
  
  type AnalyticsTarget {
    name: String!
    value: Float!
    achieved: Boolean!
    progress: Float! # 0-1
  }
  
  type AnalyticsSegment {
    name: String!
    description: String
    filter: JSON!
    data: [AnalyticsDataPoint!]!
    summary: AnalyticsSummary!
    color: String
  }
  
  type TimeRange {
    start: DateTime!
    end: DateTime!
    period: AnalyticsPeriod!
    timezone: String!
  }
  
  # Dashboard analytics
  type DashboardAnalytics {
    # Overview metrics
    overview: OverviewMetrics!
    
    # User analytics
    users: UserAnalytics!
    sessions: SessionAnalytics!
    
    # Content analytics
    files: FileAnalytics!
    videos: VideoAnalytics!
    storage: StorageAnalytics!
    
    # Plugin analytics
    plugins: PluginAnalyticsSummary!
    
    # Performance analytics
    performance: PerformanceAnalytics!
    
    # Engagement analytics
    engagement: EngagementAnalytics!
    
    # Real-time metrics
    realtime: RealtimeMetrics!
    
    # Goals and conversions
    conversions: ConversionAnalytics!
    
    # Period comparison
    comparison: PeriodComparison!
  }
  
  type OverviewMetrics {
    totalUsers: Int!
    activeUsers: Int!
    newUsers: Int!
    totalSessions: Int!
    averageSessionDuration: Float!
    bounceRate: Float!
    pageViews: Int!
    uniquePageViews: Int!
  }
  
  type UserAnalytics {
    total: Int!
    active: Int!
    new: Int!
    returning: Int!
    retention: RetentionMetrics!
    demographics: DemographicsAnalytics!
    behavior: BehaviorAnalytics!
    lifecycle: LifecycleAnalytics!
  }
  
  type RetentionMetrics {
    day1: Float!
    day7: Float!
    day30: Float!
    day90: Float!
    cohorts: [CohortData!]!
  }
  
  type CohortData {
    cohortMonth: String!
    size: Int!
    retentionRates: [Float!]!
  }
  
  type DemographicsAnalytics {
    countries: [CountryAnalytics!]!
    cities: [CityAnalytics!]!
    languages: [LanguageAnalytics!]!
    devices: [DeviceAnalytics!]!
    browsers: [BrowserAnalytics!]!
    operatingSystems: [OSAnalytics!]!
  }
  
  type CountryAnalytics {
    country: String!
    countryCode: String!
    users: Int!
    sessions: Int!
    averageSessionDuration: Float!
    bounceRate: Float!
  }
  
  type CityAnalytics {
    city: String!
    country: String!
    users: Int!
    sessions: Int!
  }
  
  type LanguageAnalytics {
    language: String!
    languageCode: String!
    users: Int!
    percentage: Float!
  }
  
  type DeviceAnalytics {
    device: String!
    category: DeviceCategory!
    users: Int!
    sessions: Int!
    averageSessionDuration: Float!
    bounceRate: Float!
  }
  
  enum DeviceCategory {
    DESKTOP
    MOBILE
    TABLET
  }
  
  type BrowserAnalytics {
    browser: String!
    version: String
    users: Int!
    sessions: Int!
  }
  
  type OSAnalytics {
    operatingSystem: String!
    version: String
    users: Int!
    sessions: Int!
  }
  
  type BehaviorAnalytics {
    averageSessionDuration: Float!
    pagesPerSession: Float!
    bounceRate: Float!
    topPages: [PageAnalytics!]!
    exitPages: [PageAnalytics!]!
    entryPages: [PageAnalytics!]!
  }
  
  type PageAnalytics {
    page: String!
    pageViews: Int!
    uniquePageViews: Int!
    averageTimeOnPage: Float!
    bounceRate: Float!
    exitRate: Float!
  }
  
  type LifecycleAnalytics {
    newUsers: [AnalyticsDataPoint!]!
    returningUsers: [AnalyticsDataPoint!]!
    churnedUsers: [AnalyticsDataPoint!]!
    userLifetime: Float! # average days
    ltv: Float! # lifetime value
  }
  
  type SessionAnalytics {
    total: Int!
    unique: Int!
    averageDuration: Float!
    bounceRate: Float!
    sessionsPerUser: Float!
    timeline: [AnalyticsDataPoint!]!
  }
  
  type FileAnalytics {
    totalFiles: Int!
    newFiles: Int!
    totalDownloads: Int!
    totalViews: Int!
    topFiles: [TopFileAnalytics!]!
    fileTypes: [FileTypeAnalytics!]!
    uploadTrend: [AnalyticsDataPoint!]!
  }
  
  type TopFileAnalytics {
    file: File! @complexity(value: 2)
    views: Int!
    downloads: Int!
    shares: Int!
  }
  
  type FileTypeAnalytics {
    type: String!
    count: Int!
    percentage: Float!
    totalSize: Int!
  }
  
  type VideoAnalytics {
    totalVideos: Int!
    newVideos: Int!
    totalViews: Int!
    totalWatchTime: Float!
    averageWatchTime: Float!
    completionRate: Float!
    topVideos: [TopVideoAnalytics!]!
    qualityDistribution: [QualityDistributionAnalytics!]!
  }
  
  type TopVideoAnalytics {
    video: Video! @complexity(value: 2)
    views: Int!
    watchTime: Float!
    completionRate: Float!
    engagement: Float!
  }
  
  type QualityDistributionAnalytics {
    quality: String!
    views: Int!
    percentage: Float!
  }
  
  type StorageAnalytics {
    totalStorage: Int! # in bytes
    storageUsed: Int!
    storageAvailable: Int!
    storageByType: [StorageByTypeAnalytics!]!
    growthTrend: [AnalyticsDataPoint!]!
  }
  
  type StorageByTypeAnalytics {
    type: String!
    size: Int!
    percentage: Float!
    fileCount: Int!
  }
  
  type PluginAnalyticsSummary {
    totalPlugins: Int!
    activePlugins: Int!
    totalExecutions: Int!
    successfulExecutions: Int!
    failedExecutions: Int!
    averageExecutionTime: Float!
    topPlugins: [TopPluginExecutionAnalytics!]!
    errorRate: [AnalyticsDataPoint!]!
  }
  
  type TopPluginExecutionAnalytics {
    plugin: Plugin! @complexity(value: 2)
    executions: Int!
    successRate: Float!
    averageExecutionTime: Float!
    users: Int!
  }
  
  type PerformanceAnalytics {
    averageLoadTime: Float!
    medianLoadTime: Float!
    p95LoadTime: Float!
    errorRate: Float!
    uptime: Float!
    apdex: Float! # Application Performance Index
    vitals: WebVitals!
    timeline: [PerformanceDataPoint!]!
  }
  
  type WebVitals {
    lcp: Float! # Largest Contentful Paint
    fid: Float! # First Input Delay
    cls: Float! # Cumulative Layout Shift
    fcp: Float! # First Contentful Paint
    ttfb: Float! # Time to First Byte
  }
  
  type PerformanceDataPoint {
    timestamp: DateTime!
    loadTime: Float!
    errorRate: Float!
    throughput: Float!
  }
  
  type EngagementAnalytics {
    totalEngagements: Int!
    engagementRate: Float!
    averageEngagementTime: Float!
    topEngagingContent: [EngagingContentAnalytics!]!
    engagementByType: [EngagementTypeAnalytics!]!
  }
  
  type EngagingContentAnalytics {
    contentId: ID!
    contentType: String!
    title: String!
    engagements: Int!
    engagementRate: Float!
    averageTimeSpent: Float!
  }
  
  type EngagementTypeAnalytics {
    type: String!
    count: Int!
    percentage: Float!
  }
  
  # Real-time analytics
  type RealtimeAnalytics {
    activeUsers: Int!
    activeVisitors: Int!
    pageViews: Int!
    events: Int!
    conversions: Int!
    topPages: [RealtimePageAnalytics!]!
    topEvents: [RealtimeEventAnalytics!]!
    trafficSources: [RealtimeTrafficSource!]!
    geographicData: [RealtimeGeographicData!]!
    timeline: [RealtimeDataPoint!]!
  }
  
  type RealtimePageAnalytics {
    page: String!
    activeUsers: Int!
    pageViews: Int!
  }
  
  type RealtimeEventAnalytics {
    event: String!
    count: Int!
    rate: Float!
  }
  
  type RealtimeTrafficSource {
    source: String!
    medium: String!
    users: Int!
    percentage: Float!
  }
  
  type RealtimeGeographicData {
    country: String!
    users: Int!
    coordinates: [Float!]! # [latitude, longitude]
  }
  
  type RealtimeDataPoint {
    timestamp: DateTime!
    activeUsers: Int!
    pageViews: Int!
    events: Int!
  }
  
  type RealtimeMetrics {
    currentVisitors: Int!
    minutelyPageViews: [AnalyticsDataPoint!]!
    topActivePages: [RealtimePageAnalytics!]!
  }
  
  # Conversion analytics
  type ConversionAnalytics {
    totalConversions: Int!
    conversionRate: Float!
    revenuePerConversion: Float!
    goals: [GoalAnalytics!]!
    funnels: [FunnelSummary!]!
    attributions: [AttributionAnalytics!]!
  }
  
  type GoalAnalytics {
    goal: Goal! @complexity(value: 2)
    conversions: Int!
    conversionRate: Float!
    value: Float!
    progress: Float! # towards target
  }
  
  type Goal {
    id: ID!
    name: String!
    description: String
    type: GoalType!
    target: Float
    value: Float
    conditions: JSON!
    isActive: Boolean!
    createdAt: DateTime!
  }
  
  enum GoalType {
    PAGE_VIEW
    EVENT
    DURATION
    VALUE
  }
  
  type FunnelSummary {
    funnel: Funnel! @complexity(value: 2)
    conversions: Int!
    conversionRate: Float!
    dropoffRate: Float!
    averageTimeToConvert: Float!
  }
  
  type Funnel {
    id: ID!
    name: String!
    steps: [FunnelStep!]!
    totalUsers: Int!
    conversions: Int!
    conversionRate: Float!
  }
  
  type FunnelStep {
    id: ID!
    name: String!
    order: Int!
    condition: JSON!
    users: Int!
    conversionRate: Float!
    dropoffRate: Float!
    averageTimeFromPrevious: Float!
  }
  
  type AttributionAnalytics {
    model: AttributionModel!
    channels: [ChannelAttribution!]!
    conversions: [ConversionPath!]!
  }
  
  enum AttributionModel {
    FIRST_TOUCH
    LAST_TOUCH
    LINEAR
    TIME_DECAY
    POSITION_BASED
  }
  
  type ChannelAttribution {
    channel: String!
    touchpoints: Int!
    conversions: Int!
    revenue: Float!
    attribution: Float! # 0-1
  }
  
  type ConversionPath {
    path: [TouchPoint!]!
    conversions: Int!
    revenue: Float!
    timeToConversion: Float!
  }
  
  type TouchPoint {
    channel: String!
    campaign: String
    timestamp: DateTime!
    value: Float
  }
  
  # Period comparison
  type PeriodComparison {
    current: PeriodMetrics!
    previous: PeriodMetrics!
    change: ChangeMetrics!
  }
  
  type PeriodMetrics {
    users: Int!
    sessions: Int!
    pageViews: Int!
    conversions: Int!
    revenue: Float!
  }
  
  type ChangeMetrics {
    users: Float!
    sessions: Float!
    pageViews: Float!
    conversions: Float!
    revenue: Float!
  }
  
  # Funnel analytics
  type FunnelAnalyticsResult {
    funnel: FunnelAnalyticsInput!
    steps: [FunnelStepAnalytics!]!
    overall: FunnelOverallAnalytics!
    cohorts: [FunnelCohortAnalytics!]!
    segments: [FunnelSegmentAnalytics!]!
  }
  
  type FunnelStepAnalytics {
    step: Int!
    name: String!
    users: Int!
    conversionRate: Float!
    dropoffRate: Float!
    averageTime: Float!
    medianTime: Float!
  }
  
  type FunnelOverallAnalytics {
    totalUsers: Int!
    conversions: Int!
    conversionRate: Float!
    averageTimeToConvert: Float!
    medianTimeToConvert: Float!
  }
  
  type FunnelCohortAnalytics {
    cohort: String!
    users: Int!
    conversions: Int!
    conversionRate: Float!
  }
  
  type FunnelSegmentAnalytics {
    segment: String!
    users: Int!
    conversions: Int!
    conversionRate: Float!
    performance: FunnelSegmentPerformance!
  }
  
  enum FunnelSegmentPerformance {
    ABOVE_AVERAGE
    AVERAGE
    BELOW_AVERAGE
  }
  
  # Cohort analytics
  type CohortAnalyticsResult {
    query: CohortAnalyticsInput!
    cohorts: [CohortAnalytics!]!
    summary: CohortSummaryAnalytics!
  }
  
  type CohortAnalytics {
    cohortPeriod: String!
    size: Int!
    data: [CohortPeriodData!]!
    retention: [Float!]!
    revenue: [Float!]!
  }
  
  type CohortPeriodData {
    period: Int!
    users: Int!
    retentionRate: Float!
    revenue: Float!
    revenuePerUser: Float!
  }
  
  type CohortSummaryAnalytics {
    totalCohorts: Int!
    averageSize: Float!
    overallRetention: Float!
    bestPerformingCohort: String!
    worstPerformingCohort: String!
  }
  
  # Custom reports
  type CustomReport implements Node {
    id: ID!
    name: String!
    description: String
    query: JSON!
    visualizations: [ReportVisualization!]!
    schedule: ReportSchedule
    owner: User! @complexity(value: 2)
    isPublic: Boolean!
    tags: [String!]!
    lastRun: DateTime
    nextRun: DateTime
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  type CustomReportConnection {
    edges: [CustomReportEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type CustomReportEdge {
    node: CustomReport!
    cursor: String!
  }
  
  type ReportVisualization {
    id: ID!
    type: VisualizationType!
    config: JSON!
    position: ReportPosition!
  }
  
  enum VisualizationType {
    LINE_CHART
    BAR_CHART
    PIE_CHART
    TABLE
    METRIC
    HEATMAP
    FUNNEL
    COHORT
  }
  
  type ReportPosition {
    x: Int!
    y: Int!
    width: Int!
    height: Int!
  }
  
  type ReportSchedule {
    frequency: ScheduleFrequency!
    time: String! # HH:MM format
    timezone: String!
    recipients: [String!]!
    format: ReportFormat!
  }
  
  enum ScheduleFrequency {
    DAILY
    WEEKLY
    MONTHLY
    QUARTERLY
  }
  
  enum ReportFormat {
    PDF
    CSV
    EMAIL
    SLACK
  }
  
  # A/B testing analytics
  type ExperimentAnalytics {
    experiment: Experiment! @complexity(value: 2)
    variants: [VariantAnalytics!]!
    results: ExperimentResults!
    statistical: StatisticalAnalysis!
    timeline: [ExperimentDataPoint!]!
  }
  
  type Experiment {
    id: ID!
    name: String!
    description: String
    status: ExperimentStatus!
    startDate: DateTime!
    endDate: DateTime
    trafficAllocation: Float!
    variants: [ExperimentVariant!]!
  }
  
  enum ExperimentStatus {
    DRAFT
    RUNNING
    PAUSED
    COMPLETED
    CANCELLED
  }
  
  type ExperimentVariant {
    id: ID!
    name: String!
    trafficAllocation: Float!
    config: JSON!
  }
  
  type VariantAnalytics {
    variant: ExperimentVariant!
    users: Int!
    conversions: Int!
    conversionRate: Float!
    revenue: Float!
    revenuePerUser: Float!
    confidence: Float!
    significance: Float!
  }
  
  type ExperimentResults {
    winner: ExperimentVariant
    confidence: Float!
    significance: Float!
    pValue: Float!
    effect: Float!
    recommendation: ExperimentRecommendation!
  }
  
  enum ExperimentRecommendation {
    CONTINUE_TEST
    IMPLEMENT_VARIANT
    STOP_TEST
    INCONCLUSIVE
  }
  
  type StatisticalAnalysis {
    sampleSize: Int!
    power: Float!
    minDetectableEffect: Float!
    daysToSignificance: Int
    bayesian: BayesianAnalysis
  }
  
  type BayesianAnalysis {
    probability: Float!
    credibleInterval: CredibleInterval!
    posteriorDistribution: [PosteriorPoint!]!
  }
  
  type CredibleInterval {
    lower: Float!
    upper: Float!
    confidence: Float!
  }
  
  type PosteriorPoint {
    value: Float!
    density: Float!
  }
  
  type ExperimentDataPoint {
    timestamp: DateTime!
    variant: String!
    users: Int!
    conversions: Int!
    conversionRate: Float!
  }
  
  # Heatmap analytics
  type HeatmapData {
    query: HeatmapQueryInput!
    clicks: [HeatmapPoint!]!
    scrolls: [ScrollMapData!]!
    attention: [AttentionMapData!]!
    metadata: HeatmapMetadata!
  }
  
  type HeatmapPoint {
    x: Float!
    y: Float!
    intensity: Float!
    count: Int!
  }
  
  type ScrollMapData {
    depth: Float! # 0-1
    users: Int!
    percentage: Float!
  }
  
  type AttentionMapData {
    element: String!
    attention: Float! # seconds
    interactions: Int!
  }
  
  type HeatmapMetadata {
    totalClicks: Int!
    totalUsers: Int!
    averageScrollDepth: Float!
    maxScrollDepth: Float!
    viewport: ViewportData!
  }
  
  type ViewportData {
    width: Int!
    height: Int!
    deviceType: DeviceCategory!
  }
  
  # Session recordings
  type SessionRecording implements Node {
    id: ID!
    user: User @complexity(value: 2)
    sessionId: String!
    duration: Float!
    pageViews: Int!
    clicks: Int!
    keystrokes: Int!
    scrolls: Int!
    errors: Int!
    url: String!
    timestamp: DateTime!
    device: SessionDevice!
    location: SessionLocation
  }
  
  type SessionRecordingConnection {
    edges: [SessionRecordingEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type SessionRecordingEdge {
    node: SessionRecording!
    cursor: String!
  }
  
  type SessionDevice {
    type: DeviceCategory!
    browser: String!
    os: String!
    viewport: ViewportData!
  }
  
  type SessionLocation {
    country: String!
    city: String
    region: String
    timezone: String!
  }
  
  # Input types
  input AnalyticsQueryInput {
    metric: String!
    dimensions: [String!]
    filters: [AnalyticsFilterInput!]
    timeRange: TimeRangeInput!
    granularity: TimeGranularity = DAY
    limit: Int = 1000
    offset: Int = 0
    orderBy: [OrderByInput!]
    segments: [AnalyticsSegmentInput!]
  }
  
  input AnalyticsFilterInput {
    dimension: String!
    operator: FilterOperator!
    values: [String!]!
  }
  
  enum FilterOperator {
    EQUALS
    NOT_EQUALS
    CONTAINS
    NOT_CONTAINS
    GREATER_THAN
    LESS_THAN
    GREATER_THAN_OR_EQUAL
    LESS_THAN_OR_EQUAL
    IN
    NOT_IN
  }
  
  input TimeRangeInput {
    start: DateTime!
    end: DateTime!
    timezone: String = "UTC"
  }
  
  enum TimeGranularity {
    MINUTE
    HOUR
    DAY
    WEEK
    MONTH
    QUARTER
    YEAR
  }
  
  input OrderByInput {
    field: String!
    direction: SortOrder = DESC
  }
  
  input AnalyticsSegmentInput {
    name: String!
    filters: [AnalyticsFilterInput!]!
    color: String
  }
  
  input TrackEventInput {
    event: String!
    properties: JSON
    userId: ID
    sessionId: String
    timestamp: DateTime
    context: EventContextInput
  }
  
  input EventContextInput {
    page: String
    referrer: String
    userAgent: String
    ip: String
    campaign: CampaignContextInput
  }
  
  input CampaignContextInput {
    source: String
    medium: String
    campaign: String
    term: String
    content: String
  }
  
  input FunnelAnalyticsInput {
    name: String!
    steps: [FunnelStepInput!]!
    timeRange: TimeRangeInput!
    segments: [AnalyticsSegmentInput!]
    window: Int = 30 # days
  }
  
  input FunnelStepInput {
    name: String!
    event: String!
    filters: [AnalyticsFilterInput!]
  }
  
  input CohortAnalyticsInput {
    name: String!
    cohortBy: String! # e.g., "first_seen"
    returnBy: String! # e.g., "login"
    timeRange: TimeRangeInput!
    granularity: CohortGranularity!
    periods: Int = 12
  }
  
  enum CohortGranularity {
    DAILY
    WEEKLY
    MONTHLY
  }
  
  input HeatmapQueryInput {
    url: String!
    timeRange: TimeRangeInput!
    device: DeviceCategory
    filters: [AnalyticsFilterInput!]
  }
  
  input SessionRecordingFilterInput {
    userId: ID
    duration: RangeInput
    errors: RangeInput
    device: DeviceCategory
    country: String
    timeRange: TimeRangeInput
  }
  
  input RangeInput {
    min: Float
    max: Float
  }
  
  input CreateCustomReportInput {
    name: String!
    description: String
    query: JSON!
    visualizations: [ReportVisualizationInput!]!
    tags: [String!]
    isPublic: Boolean = false
  }
  
  input ReportVisualizationInput {
    type: VisualizationType!
    config: JSON!
    position: ReportPositionInput!
  }
  
  input ReportPositionInput {
    x: Int!
    y: Int!
    width: Int!
    height: Int!
  }
  
  input UpdateCustomReportInput {
    name: String
    description: String
    query: JSON
    visualizations: [ReportVisualizationInput!]
    tags: [String!]
    isPublic: Boolean
  }
  
  input ScheduleReportInput {
    frequency: ScheduleFrequency!
    time: String!
    timezone: String!
    recipients: [String!]!
    format: ReportFormat!
  }
  
  input CustomReportFilterInput {
    name: String
    owner: ID
    tags: [String!]
    isPublic: Boolean
    createdAfter: DateTime
    createdBefore: DateTime
  }
  
  input AnalyticsSettingsInput {
    dataRetentionDays: Int
    enableRealtime: Boolean
    enableHeatmaps: Boolean
    enableSessionRecordings: Boolean
    enableCrossDomainTracking: Boolean
    excludeInternalTraffic: Boolean
    anonymizeIPs: Boolean
    cookieConsent: Boolean
  }
  
  input PurgeDataInput {
    dataType: AnalyticsDataType!
    olderThan: DateTime!
    confirm: Boolean!
  }
  
  enum AnalyticsDataType {
    EVENTS
    SESSIONS
    HEATMAPS
    RECORDINGS
    ALL
  }
  
  input ExportDataInput {
    dataType: AnalyticsDataType!
    timeRange: TimeRangeInput!
    format: ExportFormat!
    filters: [AnalyticsFilterInput!]
  }
  
  enum ExportFormat {
    CSV
    JSON
    PARQUET
  }
  
  input CreateGoalInput {
    name: String!
    description: String
    type: GoalType!
    target: Float
    conditions: JSON!
  }
  
  input UpdateGoalInput {
    name: String
    description: String
    target: Float
    conditions: JSON
    isActive: Boolean
  }
  
  # Response types
  type CreateCustomReportPayload {
    success: Boolean!
    report: CustomReport
    errors: [Error!]
  }
  
  type UpdateCustomReportPayload {
    success: Boolean!
    report: CustomReport
    errors: [Error!]
  }
  
  type ScheduleReportPayload {
    success: Boolean!
    report: CustomReport
    errors: [Error!]
  }
  
  type UpdateAnalyticsSettingsPayload {
    success: Boolean!
    settings: AnalyticsSettings
    errors: [Error!]
  }
  
  type AnalyticsSettings {
    dataRetentionDays: Int!
    enableRealtime: Boolean!
    enableHeatmaps: Boolean!
    enableSessionRecordings: Boolean!
    enableCrossDomainTracking: Boolean!
    excludeInternalTraffic: Boolean!
    anonymizeIPs: Boolean!
    cookieConsent: Boolean!
  }
  
  type PurgeDataPayload {
    success: Boolean!
    recordsDeleted: Int!
    errors: [Error!]
  }
  
  type ExportDataPayload {
    success: Boolean!
    downloadUrl: String!
    fileSize: Int!
    recordCount: Int!
    errors: [Error!]
  }
  
  type CreateGoalPayload {
    success: Boolean!
    goal: Goal
    errors: [Error!]
  }
  
  type UpdateGoalPayload {
    success: Boolean!
    goal: Goal
    errors: [Error!]
  }
  
  # Subscription types
  type RealtimeUpdate {
    type: RealtimeUpdateType!
    data: JSON!
    timestamp: DateTime!
  }
  
  enum RealtimeUpdateType {
    ACTIVE_USERS
    PAGE_VIEW
    EVENT
    CONVERSION
  }
  
  type AnalyticsAlert {
    id: ID!
    type: AlertType!
    message: String!
    data: JSON!
    severity: AlertSeverity!
    timestamp: DateTime!
  }
  
  enum AlertType {
    TRAFFIC_SPIKE
    TRAFFIC_DROP
    ERROR_RATE_HIGH
    CONVERSION_RATE_LOW
    GOAL_ACHIEVED
    THRESHOLD_EXCEEDED
  }
  
  enum AlertSeverity {
    LOW
    MEDIUM
    HIGH
    CRITICAL
  }
`;