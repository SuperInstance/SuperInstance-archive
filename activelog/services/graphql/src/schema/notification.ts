import { gql } from 'apollo-server-express';

export const notificationTypeDefs = gql`
  extend type Query {
    # Notification queries
    notifications(
      pagination: PaginationInput
      filter: NotificationFilterInput
    ): NotificationConnection! @auth(requires: USER) @complexity(value: 8) @rateLimit(max: 100, window: 60)
    
    notification(id: ID!): Notification @auth(requires: USER) @complexity(value: 2)
    
    # Notification settings
    notificationSettings: NotificationSettings! @auth(requires: USER) @complexity(value: 3)
    
    # Unread count
    unreadNotificationCount: Int! @auth(requires: USER) @complexity(value: 1) @cache(ttl: 60)
  }
  
  extend type Mutation {
    # Notification actions
    markNotificationRead(id: ID!): MutationResponse! @auth(requires: USER)
    markNotificationsRead(ids: [ID!]!): BatchMutationResponse! @auth(requires: USER)
    markAllNotificationsRead: MutationResponse! @auth(requires: USER)
    deleteNotification(id: ID!): MutationResponse! @auth(requires: USER)
    deleteNotifications(ids: [ID!]!): BatchMutationResponse! @auth(requires: USER)
    
    # Settings
    updateNotificationSettings(input: UpdateNotificationSettingsInput!): UpdateNotificationSettingsPayload! @auth(requires: USER)
    
    # Subscription management
    subscribeToNotifications(input: SubscribeToNotificationsInput!): SubscriptionPayload! @auth(requires: USER)
    unsubscribeFromNotifications(input: UnsubscribeFromNotificationsInput!): MutationResponse! @auth(requires: USER)
    
    # Device tokens
    registerDeviceToken(input: RegisterDeviceTokenInput!): MutationResponse! @auth(requires: USER)
    unregisterDeviceToken(token: String!): MutationResponse! @auth(requires: USER)
  }
  
  extend type Subscription {
    # Real-time notifications
    notificationReceived(userId: ID!): Notification! @auth(requires: USER)
    notificationRead(userId: ID!): NotificationReadUpdate! @auth(requires: USER)
    unreadCountChanged(userId: ID!): UnreadCountUpdate! @auth(requires: USER)
  }
  
  type Notification implements Node @key(fields: "id") {
    id: ID!
    type: NotificationType!
    title: String!
    message: String!
    
    # Status
    isRead: Boolean!
    priority: NotificationPriority!
    
    # Content
    data: JSON
    actionUrl: String
    imageUrl: String
    
    # Relationships
    recipient: User! @complexity(value: 2)
    sender: User @complexity(value: 2)
    relatedEntity: NotificationEntity
    
    # Delivery
    channels: [NotificationChannel!]!
    deliveryStatus: [NotificationDelivery!]! @complexity(value: 3)
    
    # Timestamps
    createdAt: DateTime!
    readAt: DateTime
    expiresAt: DateTime
  }
  
  type NotificationConnection {
    edges: [NotificationEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
    unreadCount: Int!
  }
  
  type NotificationEdge {
    node: Notification!
    cursor: String!
  }
  
  enum NotificationType {
    SYSTEM
    FILE_UPLOAD
    FILE_SHARED
    FILE_PROCESSED
    VIDEO_READY
    PLUGIN_INSTALLED
    PLUGIN_UPDATE
    ORGANIZATION_INVITE
    TEAM_MEMBER_ADDED
    BILLING_REMINDER
    PLAN_EXPIRED
    USAGE_LIMIT
    SECURITY_ALERT
    COMMENT_ADDED
    MENTION
    TASK_ASSIGNED
    DEADLINE_REMINDER
    ACHIEVEMENT
    WELCOME
  }
  
  enum NotificationPriority {
    LOW
    NORMAL
    HIGH
    URGENT
  }
  
  enum NotificationChannel {
    IN_APP
    EMAIL
    SMS
    PUSH
    WEBHOOK
    SLACK
  }
  
  union NotificationEntity = File | Video | Plugin | Organization | User | Comment | Task
  
  type NotificationDelivery {
    channel: NotificationChannel!
    status: DeliveryStatus!
    sentAt: DateTime
    deliveredAt: DateTime
    failureReason: String
    attempts: Int!
    nextRetry: DateTime
  }
  
  enum DeliveryStatus {
    PENDING
    SENT
    DELIVERED
    FAILED
    EXPIRED
  }
  
  type NotificationSettings {
    # Global settings
    enabled: Boolean!
    quietHours: QuietHours
    
    # Channel preferences
    emailNotifications: ChannelSettings!
    pushNotifications: ChannelSettings!
    smsNotifications: ChannelSettings!
    
    # Type preferences
    systemNotifications: TypeSettings!
    fileNotifications: TypeSettings!
    videoNotifications: TypeSettings!
    pluginNotifications: TypeSettings!
    organizationNotifications: TypeSettings!
    securityNotifications: TypeSettings!
    
    # Frequency settings
    digestFrequency: DigestFrequency!
    instantNotifications: [NotificationType!]!
    
    # Device tokens
    deviceTokens: [DeviceToken!]!
  }
  
  type QuietHours {
    enabled: Boolean!
    startTime: String!
    endTime: String!
    timezone: String!
    weekendsOnly: Boolean!
  }
  
  type ChannelSettings {
    enabled: Boolean!
    types: [NotificationType!]!
    frequency: NotificationFrequency!
  }
  
  type TypeSettings {
    enabled: Boolean!
    channels: [NotificationChannel!]!
    priority: NotificationPriority!
  }
  
  enum NotificationFrequency {
    INSTANT
    HOURLY
    DAILY
    WEEKLY
    NEVER
  }
  
  enum DigestFrequency {
    NEVER
    DAILY
    WEEKLY
    MONTHLY
  }
  
  type DeviceToken {
    id: ID!
    token: String!
    platform: DevicePlatform!
    deviceName: String
    appVersion: String
    isActive: Boolean!
    lastUsed: DateTime!
    createdAt: DateTime!
  }
  
  enum DevicePlatform {
    IOS
    ANDROID
    WEB
    DESKTOP
  }
  
  # Input types
  input NotificationFilterInput {
    types: [NotificationType!]
    priorities: [NotificationPriority!]
    isRead: Boolean
    channels: [NotificationChannel!]
    createdAfter: DateTime
    createdBefore: DateTime
    hasAction: Boolean
  }
  
  input UpdateNotificationSettingsInput {
    enabled: Boolean
    quietHours: QuietHoursInput
    emailNotifications: ChannelSettingsInput
    pushNotifications: ChannelSettingsInput
    smsNotifications: ChannelSettingsInput
    systemNotifications: TypeSettingsInput
    fileNotifications: TypeSettingsInput
    videoNotifications: TypeSettingsInput
    pluginNotifications: TypeSettingsInput
    organizationNotifications: TypeSettingsInput
    securityNotifications: TypeSettingsInput
    digestFrequency: DigestFrequency
    instantNotifications: [NotificationType!]
  }
  
  input QuietHoursInput {
    enabled: Boolean!
    startTime: String!
    endTime: String!
    timezone: String!
    weekendsOnly: Boolean!
  }
  
  input ChannelSettingsInput {
    enabled: Boolean!
    types: [NotificationType!]!
    frequency: NotificationFrequency!
  }
  
  input TypeSettingsInput {
    enabled: Boolean!
    channels: [NotificationChannel!]!
    priority: NotificationPriority!
  }
  
  input SubscribeToNotificationsInput {
    types: [NotificationType!]!
    channels: [NotificationChannel!]!
    entityId: ID
    entityType: String
  }
  
  input UnsubscribeFromNotificationsInput {
    types: [NotificationType!]!
    channels: [NotificationChannel!]!
    entityId: ID
    entityType: String
  }
  
  input RegisterDeviceTokenInput {
    token: String!
    platform: DevicePlatform!
    deviceName: String
    appVersion: String
  }
  
  # Response types
  type UpdateNotificationSettingsPayload {
    success: Boolean!
    settings: NotificationSettings
    errors: [Error!]
  }
  
  type SubscriptionPayload {
    success: Boolean!
    subscription: NotificationSubscription
    errors: [Error!]
  }
  
  type NotificationSubscription {
    id: ID!
    userId: ID!
    types: [NotificationType!]!
    channels: [NotificationChannel!]!
    entityId: ID
    entityType: String
    createdAt: DateTime!
  }
  
  # Subscription response types
  type NotificationReadUpdate {
    notificationId: ID!
    isRead: Boolean!
    readAt: DateTime
  }
  
  type UnreadCountUpdate {
    userId: ID!
    count: Int!
    updatedAt: DateTime!
  }
`;