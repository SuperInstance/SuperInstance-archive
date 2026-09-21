import { gql } from 'apollo-server-express';

export const userTypeDefs = gql`
  extend type Query {
    # User queries
    user(id: ID!): User @auth(requires: USER) @complexity(value: 2)
    users(
      pagination: PaginationInput
      sort: SortInput
      filter: UserFilterInput
    ): UserConnection! @auth(requires: ADMIN) @complexity(value: 10) @rateLimit(max: 100, window: 60)
    me: User @auth(requires: USER) @complexity(value: 1) @cache(ttl: 300)
    
    # Search users
    searchUsers(query: String!, limit: Int = 10): [User!]! 
      @auth(requires: USER) @complexity(value: 5) @rateLimit(max: 20, window: 60)
  }
  
  extend type Mutation {
    # Authentication
    login(input: LoginInput!): AuthPayload!
    logout: MutationResponse! @auth(requires: USER)
    refreshToken(token: String!): AuthPayload!
    
    # User management
    createUser(input: CreateUserInput!): CreateUserPayload! @auth(requires: ADMIN)
    updateUser(id: ID!, input: UpdateUserInput!): UpdateUserPayload! @auth(requires: USER)
    deleteUser(id: ID!): MutationResponse! @auth(requires: ADMIN)
    
    # Profile management
    updateProfile(input: UpdateProfileInput!): UpdateProfilePayload! @auth(requires: USER)
    changePassword(input: ChangePasswordInput!): MutationResponse! @auth(requires: USER)
    uploadAvatar(file: Upload!): UploadAvatarPayload! @auth(requires: USER)
    
    # User preferences
    updatePreferences(input: UserPreferencesInput!): UpdatePreferencesPayload! @auth(requires: USER)
    
    # Account actions
    verifyEmail(token: String!): MutationResponse!
    requestPasswordReset(email: String!): MutationResponse!
    resetPassword(input: ResetPasswordInput!): MutationResponse!
  }
  
  extend type Subscription {
    # User subscriptions
    userUpdated(userId: ID!): User! @auth(requires: USER)
    userOnline(userId: ID!): UserOnlineStatus! @auth(requires: USER)
  }
  
  type User implements Node @key(fields: "id") {
    id: ID!
    username: String!
    email: String!
    firstName: String
    lastName: String
    fullName: String
    avatar: String
    bio: String
    website: String
    location: String
    timezone: String
    language: String
    
    # Account status
    isVerified: Boolean!
    isActive: Boolean!
    lastLoginAt: DateTime
    createdAt: DateTime!
    updatedAt: DateTime!
    
    # Computed fields
    displayName: String!
    initials: String!
    
    # User preferences
    preferences: UserPreferences!
    
    # User statistics
    stats: UserStats! @complexity(value: 3)
    
    # Relationships
    organization: Organization @complexity(value: 2)
    files(
      pagination: PaginationInput
      sort: SortInput
      filter: FileFilterInput
    ): FileConnection! @complexity(value: 5)
    
    plugins(
      pagination: PaginationInput
      filter: PluginFilterInput
    ): PluginConnection! @complexity(value: 5)
    
    notifications(
      pagination: PaginationInput
      filter: NotificationFilterInput
    ): NotificationConnection! @complexity(value: 5)
    
    # Activity feed
    activities(
      pagination: PaginationInput
      filter: ActivityFilterInput
    ): ActivityConnection! @complexity(value: 8)
    
    # Permissions
    permissions: [Permission!]! @auth(requires: ADMIN) @complexity(value: 3)
    hasPermission(permission: String!): Boolean! @complexity(value: 1)
  }
  
  type UserConnection {
    edges: [UserEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type UserEdge {
    node: User!
    cursor: String!
  }
  
  type UserPreferences {
    theme: String
    language: String
    timezone: String
    emailNotifications: Boolean!
    pushNotifications: Boolean!
    marketingEmails: Boolean!
    weeklyDigest: Boolean!
    dashboardLayout: JSON
    privacy: PrivacySettings!
  }
  
  type PrivacySettings {
    profileVisibility: VisibilityLevel!
    activityVisibility: VisibilityLevel!
    showEmail: Boolean!
    showLocation: Boolean!
  }
  
  enum VisibilityLevel {
    PUBLIC
    ORGANIZATION
    PRIVATE
  }
  
  type UserStats {
    filesUploaded: Int!
    totalFileSize: Int!
    videosProcessed: Int!
    pluginsInstalled: Int!
    activeDays: Int!
    lastActivity: DateTime
  }
  
  type UserOnlineStatus {
    userId: ID!
    isOnline: Boolean!
    lastSeen: DateTime
  }
  
  # Input types
  input LoginInput {
    email: String!
    password: String!
    rememberMe: Boolean = false
  }
  
  input CreateUserInput {
    username: String!
    email: String!
    password: String!
    firstName: String
    lastName: String
    organizationId: ID
    role: String = "user"
    sendWelcomeEmail: Boolean = true
  }
  
  input UpdateUserInput {
    username: String
    email: String
    firstName: String
    lastName: String
    bio: String
    website: String
    location: String
    timezone: String
    language: String
    isActive: Boolean
  }
  
  input UpdateProfileInput {
    firstName: String
    lastName: String
    bio: String
    website: String
    location: String
    timezone: String
    language: String
  }
  
  input ChangePasswordInput {
    currentPassword: String!
    newPassword: String!
    confirmPassword: String!
  }
  
  input ResetPasswordInput {
    token: String!
    password: String!
    confirmPassword: String!
  }
  
  input UserPreferencesInput {
    theme: String
    language: String
    timezone: String
    emailNotifications: Boolean
    pushNotifications: Boolean
    marketingEmails: Boolean
    weeklyDigest: Boolean
    dashboardLayout: JSON
    privacy: PrivacySettingsInput
  }
  
  input PrivacySettingsInput {
    profileVisibility: VisibilityLevel
    activityVisibility: VisibilityLevel
    showEmail: Boolean
    showLocation: Boolean
  }
  
  input UserFilterInput {
    username: String
    email: String
    isVerified: Boolean
    isActive: Boolean
    organizationId: ID
    role: String
    createdAfter: DateTime
    createdBefore: DateTime
  }
  
  # Response types
  type AuthPayload {
    token: String!
    refreshToken: String!
    user: User!
    expiresAt: DateTime!
  }
  
  type CreateUserPayload {
    success: Boolean!
    user: User
    errors: [Error!]
  }
  
  type UpdateUserPayload {
    success: Boolean!
    user: User
    errors: [Error!]
  }
  
  type UpdateProfilePayload {
    success: Boolean!
    user: User
    errors: [Error!]
  }
  
  type UploadAvatarPayload {
    success: Boolean!
    avatarUrl: String
    errors: [Error!]
  }
  
  type UpdatePreferencesPayload {
    success: Boolean!
    preferences: UserPreferences
    errors: [Error!]
  }
  
  # Permission system
  type Permission {
    id: ID!
    name: String!
    description: String
    resource: String!
    action: String!
    conditions: JSON
  }
  
  # Activity system
  type Activity implements Node {
    id: ID!
    userId: ID!
    type: String!
    action: String!
    resource: String
    resourceId: ID
    metadata: JSON
    ipAddress: String
    userAgent: String
    createdAt: DateTime!
  }
  
  type ActivityConnection {
    edges: [ActivityEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type ActivityEdge {
    node: Activity!
    cursor: String!
  }
  
  input ActivityFilterInput {
    type: String
    action: String
    resource: String
    resourceId: ID
    dateFrom: DateTime
    dateTo: DateTime
  }
`;