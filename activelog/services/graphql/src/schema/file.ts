import { gql } from 'apollo-server-express';

export const fileTypeDefs = gql`
  extend type Query {
    # File queries
    file(id: ID!): File @auth(requires: USER) @complexity(value: 2)
    files(
      pagination: PaginationInput
      sort: SortInput
      filter: FileFilterInput
    ): FileConnection! @auth(requires: USER) @complexity(value: 8) @rateLimit(max: 50, window: 60)
    
    # Search files
    searchFiles(
      query: String!
      pagination: PaginationInput
      filter: FileSearchFilterInput
    ): FileConnection! @auth(requires: USER) @complexity(value: 10) @rateLimit(max: 20, window: 60)
    
    # File analytics
    fileAnalytics(
      fileId: ID!
      period: AnalyticsPeriod = LAST_30_DAYS
    ): FileAnalytics @auth(requires: USER) @complexity(value: 5)
    
    # Shared files
    sharedFiles(
      pagination: PaginationInput
      filter: SharedFileFilterInput
    ): SharedFileConnection! @auth(requires: USER) @complexity(value: 8)
  }
  
  extend type Mutation {
    # File upload and management
    uploadFile(input: UploadFileInput!): UploadFilePayload! @auth(requires: USER) @rateLimit(max: 10, window: 60)
    uploadFiles(input: [UploadFileInput!]!): UploadFilesPayload! @auth(requires: USER) @rateLimit(max: 5, window: 60)
    
    # File operations
    updateFile(id: ID!, input: UpdateFileInput!): UpdateFilePayload! @auth(requires: USER)
    deleteFile(id: ID!): MutationResponse! @auth(requires: USER)
    deleteFiles(ids: [ID!]!): BatchMutationResponse! @auth(requires: USER)
    
    # File organization
    moveFile(id: ID!, folderId: ID): MoveFilePayload! @auth(requires: USER)
    copyFile(id: ID!, input: CopyFileInput!): CopyFilePayload! @auth(requires: USER)
    
    # File sharing
    shareFile(id: ID!, input: ShareFileInput!): ShareFilePayload! @auth(requires: USER)
    updateFileSharing(id: ID!, input: UpdateSharingInput!): UpdateSharingPayload! @auth(requires: USER)
    revokeFileSharing(id: ID!): MutationResponse! @auth(requires: USER)
    
    # File processing
    processFile(id: ID!, input: ProcessFileInput!): ProcessFilePayload! @auth(requires: USER)
    cancelProcessing(id: ID!): MutationResponse! @auth(requires: USER)
    
    # Folder management
    createFolder(input: CreateFolderInput!): CreateFolderPayload! @auth(requires: USER)
    updateFolder(id: ID!, input: UpdateFolderInput!): UpdateFolderPayload! @auth(requires: USER)
    deleteFolder(id: ID!): MutationResponse! @auth(requires: USER)
  }
  
  extend type Subscription {
    # File subscriptions
    fileUploaded(userId: ID!): File! @auth(requires: USER)
    fileProcessed(fileId: ID!): FileProcessingUpdate! @auth(requires: USER)
    fileShared(userId: ID!): SharedFile! @auth(requires: USER)
    folderUpdated(folderId: ID!): Folder! @auth(requires: USER)
  }
  
  type File implements Node @key(fields: "id") {
    id: ID!
    filename: String!
    originalName: String!
    path: String!
    url: String! @complexity(value: 1)
    downloadUrl: String! @auth(requires: USER) @complexity(value: 1)
    thumbnailUrl: String @complexity(value: 1)
    
    # File properties
    mimeType: String!
    size: Int!
    sizeFormatted: String!
    checksum: String!
    
    # File status
    status: FileStatus!
    uploadProgress: Float
    processingStatus: ProcessingStatus
    
    # Metadata
    metadata: FileMetadata!
    tags: [String!]!
    description: String
    
    # Relationships
    owner: User! @complexity(value: 2)
    folder: Folder @complexity(value: 2)
    
    # Permissions and sharing
    permissions: FilePermissions! @complexity(value: 2)
    shares: [FileShare!]! @complexity(value: 3)
    isShared: Boolean!
    
    # Processing and analysis
    processing: [ProcessingJob!]! @complexity(value: 5)
    analysis: FileAnalysisResult @complexity(value: 5)
    
    # Versions
    versions: [FileVersion!]! @complexity(value: 3)
    currentVersion: Int!
    
    # Timestamps
    uploadedAt: DateTime!
    updatedAt: DateTime!
    lastAccessedAt: DateTime
    
    # Activity
    activities: [FileActivity!]! @complexity(value: 5)
    downloadCount: Int!
    viewCount: Int!
  }
  
  type FileConnection {
    edges: [FileEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
    totalSize: Int!
  }
  
  type FileEdge {
    node: File!
    cursor: String!
  }
  
  enum FileStatus {
    UPLOADING
    UPLOADED
    PROCESSING
    READY
    ERROR
    ARCHIVED
    DELETED
  }
  
  enum ProcessingStatus {
    PENDING
    PROCESSING
    COMPLETED
    FAILED
    CANCELLED
  }
  
  type FileMetadata {
    # Common metadata
    width: Int
    height: Int
    duration: Float
    bitrate: Int
    frameRate: Float
    
    # Media-specific
    codec: String
    colorSpace: String
    hasAudio: Boolean
    audioCodec: String
    audioChannels: Int
    audioSampleRate: Int
    
    # Document metadata
    pageCount: Int
    wordCount: Int
    language: String
    
    # EXIF data
    exif: JSON
    
    # Custom metadata
    custom: JSON
  }
  
  type FilePermissions {
    canRead: Boolean!
    canWrite: Boolean!
    canDelete: Boolean!
    canShare: Boolean!
    canDownload: Boolean!
  }
  
  type FileShare {
    id: ID!
    file: File!
    sharedBy: User!
    sharedWith: User
    shareType: ShareType!
    permissions: SharePermissions!
    expiresAt: DateTime
    accessCount: Int!
    lastAccessedAt: DateTime
    createdAt: DateTime!
  }
  
  enum ShareType {
    DIRECT
    LINK
    PUBLIC
    ORGANIZATION
  }
  
  type SharePermissions {
    canView: Boolean!
    canDownload: Boolean!
    canComment: Boolean!
  }
  
  type ProcessingJob {
    id: ID!
    type: ProcessingType!
    status: ProcessingStatus!
    progress: Float
    startedAt: DateTime
    completedAt: DateTime
    error: String
    result: JSON
  }
  
  enum ProcessingType {
    THUMBNAIL_GENERATION
    VIDEO_TRANSCODING
    AUDIO_ANALYSIS
    TEXT_EXTRACTION
    IMAGE_ANALYSIS
    VIRUS_SCAN
    METADATA_EXTRACTION
  }
  
  type FileAnalysisResult {
    id: ID!
    fileId: ID!
    analysisType: String!
    result: JSON!
    confidence: Float
    createdAt: DateTime!
  }
  
  type FileVersion {
    id: ID!
    version: Int!
    filename: String!
    size: Int!
    checksum: String!
    uploadedBy: User!
    uploadedAt: DateTime!
    changes: String
  }
  
  type FileActivity {
    id: ID!
    action: FileAction!
    user: User
    ipAddress: String
    metadata: JSON
    createdAt: DateTime!
  }
  
  enum FileAction {
    UPLOADED
    DOWNLOADED
    VIEWED
    SHARED
    MOVED
    RENAMED
    DELETED
    RESTORED
  }
  
  type FileAnalytics {
    fileId: ID!
    period: AnalyticsPeriod!
    views: [AnalyticsDataPoint!]!
    downloads: [AnalyticsDataPoint!]!
    shares: [AnalyticsDataPoint!]!
    totalViews: Int!
    totalDownloads: Int!
    totalShares: Int!
    uniqueViewers: Int!
  }
  
  # Folder types
  type Folder implements Node @key(fields: "id") {
    id: ID!
    name: String!
    path: String!
    
    # Folder properties
    color: String
    icon: String
    description: String
    
    # Relationships
    parent: Folder
    children: [Folder!]! @complexity(value: 5)
    files(
      pagination: PaginationInput
      filter: FileFilterInput
    ): FileConnection! @complexity(value: 8)
    owner: User! @complexity(value: 2)
    
    # Permissions
    permissions: FolderPermissions! @complexity(value: 2)
    shares: [FolderShare!]! @complexity(value: 3)
    isShared: Boolean!
    
    # Statistics
    fileCount: Int!
    totalSize: Int!
    
    # Timestamps
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  type FolderPermissions {
    canRead: Boolean!
    canWrite: Boolean!
    canDelete: Boolean!
    canShare: Boolean!
    canUpload: Boolean!
  }
  
  type FolderShare {
    id: ID!
    folder: Folder!
    sharedBy: User!
    sharedWith: User
    permissions: FolderSharePermissions!
    expiresAt: DateTime
    createdAt: DateTime!
  }
  
  type FolderSharePermissions {
    canView: Boolean!
    canUpload: Boolean!
    canCreateFolders: Boolean!
  }
  
  # Shared files
  type SharedFile {
    id: ID!
    file: File!
    shareUrl: String!
    sharedBy: User!
    accessCount: Int!
    maxAccess: Int
    expiresAt: DateTime
    password: Boolean!
    createdAt: DateTime!
  }
  
  type SharedFileConnection {
    edges: [SharedFileEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type SharedFileEdge {
    node: SharedFile!
    cursor: String!
  }
  
  # Input types
  input UploadFileInput {
    file: Upload!
    folderId: ID
    description: String
    tags: [String!]
    isPrivate: Boolean = false
    processImmediately: Boolean = true
  }
  
  input UpdateFileInput {
    filename: String
    description: String
    tags: [String!]
    folderId: ID
    metadata: JSON
  }
  
  input CopyFileInput {
    folderId: ID
    filename: String
    description: String
  }
  
  input ShareFileInput {
    shareType: ShareType!
    userIds: [ID!]
    permissions: SharePermissionsInput!
    expiresAt: DateTime
    password: String
    maxAccess: Int
  }
  
  input SharePermissionsInput {
    canView: Boolean!
    canDownload: Boolean!
    canComment: Boolean!
  }
  
  input UpdateSharingInput {
    permissions: SharePermissionsInput
    expiresAt: DateTime
    maxAccess: Int
  }
  
  input ProcessFileInput {
    type: ProcessingType!
    options: JSON
    priority: ProcessingPriority = NORMAL
  }
  
  enum ProcessingPriority {
    LOW
    NORMAL
    HIGH
    URGENT
  }
  
  input CreateFolderInput {
    name: String!
    parentId: ID
    color: String
    icon: String
    description: String
  }
  
  input UpdateFolderInput {
    name: String
    color: String
    icon: String
    description: String
  }
  
  input FileFilterInput {
    filename: String
    mimeType: String
    minSize: Int
    maxSize: Int
    folderId: ID
    ownerId: ID
    tags: [String!]
    status: FileStatus
    uploadedAfter: DateTime
    uploadedBefore: DateTime
  }
  
  input FileSearchFilterInput {
    mimeTypes: [String!]
    tags: [String!]
    minSize: Int
    maxSize: Int
    uploadedAfter: DateTime
    uploadedBefore: DateTime
    hasAnalysis: Boolean
  }
  
  input SharedFileFilterInput {
    shareType: ShareType
    active: Boolean
    expiringBefore: DateTime
  }
  
  # Response types
  type UploadFilePayload {
    success: Boolean!
    file: File
    errors: [Error!]
  }
  
  type UploadFilesPayload {
    success: Boolean!
    files: [File!]
    failed: [UploadError!]
    successCount: Int!
    failedCount: Int!
  }
  
  type UploadError {
    filename: String!
    error: String!
  }
  
  type UpdateFilePayload {
    success: Boolean!
    file: File
    errors: [Error!]
  }
  
  type MoveFilePayload {
    success: Boolean!
    file: File
    errors: [Error!]
  }
  
  type CopyFilePayload {
    success: Boolean!
    file: File
    errors: [Error!]
  }
  
  type ShareFilePayload {
    success: Boolean!
    share: FileShare
    shareUrl: String
    errors: [Error!]
  }
  
  type UpdateSharingPayload {
    success: Boolean!
    share: FileShare
    errors: [Error!]
  }
  
  type ProcessFilePayload {
    success: Boolean!
    job: ProcessingJob
    errors: [Error!]
  }
  
  type CreateFolderPayload {
    success: Boolean!
    folder: Folder
    errors: [Error!]
  }
  
  type UpdateFolderPayload {
    success: Boolean!
    folder: Folder
    errors: [Error!]
  }
  
  type BatchMutationResponse {
    success: Boolean!
    successCount: Int!
    failedCount: Int!
    errors: [BatchError!]
  }
  
  type BatchError {
    id: ID!
    error: String!
  }
  
  # Subscription types
  type FileProcessingUpdate {
    fileId: ID!
    status: ProcessingStatus!
    progress: Float
    error: String
    result: JSON
  }
`;