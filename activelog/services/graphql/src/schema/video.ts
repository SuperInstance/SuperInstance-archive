import { gql } from 'apollo-server-express';

export const videoTypeDefs = gql`
  extend type Query {
    # Video queries
    video(id: ID!): Video @auth(requires: USER) @complexity(value: 3)
    videos(
      pagination: PaginationInput
      sort: SortInput
      filter: VideoFilterInput
    ): VideoConnection! @auth(requires: USER) @complexity(value: 10) @rateLimit(max: 50, window: 60)
    
    # Video processing queries
    videoProcessingJob(id: ID!): VideoProcessingJob @auth(requires: USER) @complexity(value: 2)
    videoProcessingJobs(
      pagination: PaginationInput
      filter: ProcessingJobFilterInput
    ): VideoProcessingJobConnection! @auth(requires: USER) @complexity(value: 8)
    
    # Video analytics
    videoAnalytics(
      videoId: ID!
      period: AnalyticsPeriod = LAST_30_DAYS
    ): VideoAnalytics @auth(requires: USER) @complexity(value: 5)
    
    # Search videos
    searchVideos(
      query: String!
      pagination: PaginationInput
      filter: VideoSearchFilterInput
    ): VideoConnection! @auth(requires: USER) @complexity(value: 12) @rateLimit(max: 20, window: 60)
  }
  
  extend type Mutation {
    # Video upload and processing
    uploadVideo(input: UploadVideoInput!): UploadVideoPayload! @auth(requires: USER) @rateLimit(max: 5, window: 300)
    processVideo(id: ID!, input: VideoProcessingInput!): VideoProcessingPayload! @auth(requires: USER)
    
    # Video management
    updateVideo(id: ID!, input: UpdateVideoInput!): UpdateVideoPayload! @auth(requires: USER)
    deleteVideo(id: ID!): MutationResponse! @auth(requires: USER)
    
    # Video transcoding
    transcodeVideo(id: ID!, input: TranscodeVideoInput!): TranscodeVideoPayload! @auth(requires: USER)
    cancelTranscoding(jobId: ID!): MutationResponse! @auth(requires: USER)
    
    # Video analysis
    analyzeVideo(id: ID!, input: VideoAnalysisInput!): VideoAnalysisPayload! @auth(requires: USER)
    
    # Video streaming
    createVideoStream(id: ID!, input: CreateStreamInput!): CreateStreamPayload! @auth(requires: USER)
    updateVideoStream(id: ID!, input: UpdateStreamInput!): UpdateStreamPayload! @auth(requires: USER)
    
    # Subtitles and captions
    uploadSubtitles(videoId: ID!, input: UploadSubtitlesInput!): UploadSubtitlesPayload! @auth(requires: USER)
    generateSubtitles(videoId: ID!, input: GenerateSubtitlesInput!): GenerateSubtitlesPayload! @auth(requires: USER)
    updateSubtitles(id: ID!, input: UpdateSubtitlesInput!): UpdateSubtitlesPayload! @auth(requires: USER)
    deleteSubtitles(id: ID!): MutationResponse! @auth(requires: USER)
    
    # Video chapters
    addVideoChapter(videoId: ID!, input: AddChapterInput!): AddChapterPayload! @auth(requires: USER)
    updateVideoChapter(id: ID!, input: UpdateChapterInput!): UpdateChapterPayload! @auth(requires: USER)
    deleteVideoChapter(id: ID!): MutationResponse! @auth(requires: USER)
  }
  
  extend type Subscription {
    # Video subscriptions
    videoUploaded(userId: ID!): Video! @auth(requires: USER)
    videoProcessingUpdate(videoId: ID!): VideoProcessingUpdate! @auth(requires: USER)
    videoTranscodingUpdate(jobId: ID!): TranscodingUpdate! @auth(requires: USER)
    videoAnalysisUpdate(videoId: ID!): VideoAnalysisUpdate! @auth(requires: USER)
  }
  
  type Video implements Node @key(fields: "id") {
    id: ID!
    title: String!
    description: String
    
    # File reference
    file: File! @complexity(value: 2)
    
    # Video properties
    duration: Float! # in seconds
    width: Int!
    height: Int!
    aspectRatio: String!
    frameRate: Float!
    bitrate: Int!
    codec: String!
    colorSpace: String
    
    # Audio properties
    hasAudio: Boolean!
    audioCodec: String
    audioChannels: Int
    audioSampleRate: Int
    audioBitrate: Int
    
    # Status and processing
    status: VideoStatus!
    processingStatus: VideoProcessingStatus!
    processingProgress: Float
    
    # Thumbnails and previews
    thumbnail: String @complexity(value: 1)
    poster: String @complexity(value: 1)
    previewGif: String @complexity(value: 1)
    storyboard: String @complexity(value: 1)
    
    # Streaming and playback
    streamingUrls: [StreamingUrl!]! @complexity(value: 3)
    playbackUrl: String! @auth(requires: USER) @complexity(value: 1)
    downloadUrl: String! @auth(requires: USER) @complexity(value: 1)
    
    # Transcoded versions
    transcodes: [VideoTranscode!]! @complexity(value: 5)
    availableQualities: [VideoQuality!]! @complexity(value: 2)
    
    # Analysis and metadata
    analysis: VideoAnalysisResult @complexity(value: 8)
    scenes: [VideoScene!]! @complexity(value: 10)
    objects: [DetectedObject!]! @complexity(value: 10)
    faces: [DetectedFace!]! @complexity(value: 10)
    text: [ExtractedText!]! @complexity(value: 8)
    transcript: AudioTranscript @complexity(value: 8)
    
    # Subtitles and captions
    subtitles: [VideoSubtitle!]! @complexity(value: 5)
    captions: [VideoCaption!]! @complexity(value: 5)
    
    # Chapters and structure
    chapters: [VideoChapter!]! @complexity(value: 3)
    
    # User interactions
    views: Int!
    likes: Int!
    comments: Int!
    shares: Int!
    
    # Privacy and sharing
    visibility: VideoVisibility!
    isPublic: Boolean!
    
    # Relationships
    owner: User! @complexity(value: 2)
    folder: Folder @complexity(value: 2)
    playlist: [Playlist!]! @complexity(value: 5)
    
    # Processing jobs
    processingJobs: [VideoProcessingJob!]! @complexity(value: 8)
    
    # Timestamps
    uploadedAt: DateTime!
    publishedAt: DateTime
    updatedAt: DateTime!
    lastWatchedAt: DateTime
  }
  
  type VideoConnection {
    edges: [VideoEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
    totalDuration: Float!
    totalSize: Int!
  }
  
  type VideoEdge {
    node: Video!
    cursor: String!
  }
  
  enum VideoStatus {
    UPLOADING
    UPLOADED
    PROCESSING
    READY
    ERROR
    ARCHIVED
    DELETED
  }
  
  enum VideoProcessingStatus {
    PENDING
    VALIDATING
    ANALYZING
    TRANSCODING
    GENERATING_THUMBNAILS
    EXTRACTING_AUDIO
    GENERATING_SUBTITLES
    COMPLETED
    FAILED
    CANCELLED
  }
  
  enum VideoVisibility {
    PRIVATE
    UNLISTED
    PUBLIC
    ORGANIZATION
  }
  
  type StreamingUrl {
    quality: VideoQuality!
    url: String!
    format: String!
    bitrate: Int!
    resolution: String!
  }
  
  enum VideoQuality {
    ORIGINAL
    HD_1080P
    HD_720P
    SD_480P
    SD_360P
    SD_240P
    AUDIO_ONLY
  }
  
  type VideoTranscode {
    id: ID!
    quality: VideoQuality!
    format: String!
    width: Int!
    height: Int!
    bitrate: Int!
    fileSize: Int!
    url: String!
    status: TranscodeStatus!
    progress: Float
    createdAt: DateTime!
    completedAt: DateTime
  }
  
  enum TranscodeStatus {
    PENDING
    PROCESSING
    COMPLETED
    FAILED
    CANCELLED
  }
  
  # Analysis types
  type VideoAnalysisResult {
    id: ID!
    videoId: ID!
    
    # Content analysis
    contentScore: Float
    adultContent: Boolean
    violentContent: Boolean
    explicitContent: Boolean
    
    # Quality metrics
    qualityScore: Float
    sharpness: Float
    brightness: Float
    contrast: Float
    colorfulness: Float
    
    # Audio analysis
    audioQuality: Float
    speechDetected: Boolean
    musicDetected: Boolean
    noiseLevel: Float
    
    # Scene analysis
    sceneCount: Int
    averageSceneLength: Float
    sceneChanges: [Float!]!
    
    # Object detection summary
    objectCounts: JSON
    personCount: Int
    faceCount: Int
    
    # Text detection summary
    textRegions: Int
    detectedLanguages: [String!]!
    
    # Timestamps
    analyzedAt: DateTime!
    processingTime: Float!
  }
  
  type VideoScene {
    id: ID!
    videoId: ID!
    startTime: Float!
    endTime: Float!
    duration: Float!
    thumbnail: String
    description: String
    confidence: Float!
    tags: [String!]!
    objects: [String!]!
  }
  
  type DetectedObject {
    id: ID!
    videoId: ID!
    class: String!
    confidence: Float!
    boundingBox: BoundingBox!
    startTime: Float!
    endTime: Float!
    track: String
  }
  
  type DetectedFace {
    id: ID!
    videoId: ID!
    confidence: Float!
    boundingBox: BoundingBox!
    startTime: Float!
    endTime: Float!
    emotions: JSON
    attributes: JSON
    track: String
  }
  
  type BoundingBox {
    x: Float!
    y: Float!
    width: Float!
    height: Float!
  }
  
  type ExtractedText {
    id: ID!
    videoId: ID!
    text: String!
    confidence: Float!
    boundingBox: BoundingBox!
    startTime: Float!
    endTime: Float!
    language: String
    fontSize: Float
  }
  
  type AudioTranscript {
    id: ID!
    videoId: ID!
    text: String!
    language: String!
    confidence: Float!
    segments: [TranscriptSegment!]!
    speakerCount: Int
    createdAt: DateTime!
  }
  
  type TranscriptSegment {
    id: ID!
    text: String!
    startTime: Float!
    endTime: Float!
    confidence: Float!
    speaker: String
    words: [TranscriptWord!]!
  }
  
  type TranscriptWord {
    word: String!
    startTime: Float!
    endTime: Float!
    confidence: Float!
  }
  
  # Subtitles and Captions
  type VideoSubtitle {
    id: ID!
    videoId: ID!
    language: String!
    label: String!
    format: SubtitleFormat!
    url: String!
    isDefault: Boolean!
    isAutoGenerated: Boolean!
    createdAt: DateTime!
  }
  
  type VideoCaption {
    id: ID!
    videoId: ID!
    language: String!
    label: String!
    format: SubtitleFormat!
    url: String!
    isDefault: Boolean!
    createdAt: DateTime!
  }
  
  enum SubtitleFormat {
    SRT
    VTT
    ASS
    SSA
    TTML
  }
  
  # Chapters
  type VideoChapter {
    id: ID!
    videoId: ID!
    title: String!
    startTime: Float!
    endTime: Float!
    thumbnail: String
    description: String
    order: Int!
  }
  
  # Processing Jobs
  type VideoProcessingJob {
    id: ID!
    videoId: ID!
    type: VideoProcessingType!
    status: VideoProcessingStatus!
    progress: Float
    priority: ProcessingPriority!
    
    # Job details
    startedAt: DateTime
    completedAt: DateTime
    processingTime: Float
    
    # Results and errors
    result: JSON
    error: String
    retryCount: Int!
    maxRetries: Int!
    
    # Resource usage
    cpuUsage: Float
    memoryUsage: Float
    
    # Queue information
    queuePosition: Int
    estimatedTimeRemaining: Float
  }
  
  type VideoProcessingJobConnection {
    edges: [VideoProcessingJobEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }
  
  type VideoProcessingJobEdge {
    node: VideoProcessingJob!
    cursor: String!
  }
  
  enum VideoProcessingType {
    VALIDATION
    THUMBNAIL_GENERATION
    TRANSCODING
    ANALYSIS
    SCENE_DETECTION
    OBJECT_DETECTION
    FACE_DETECTION
    TEXT_EXTRACTION
    AUDIO_TRANSCRIPTION
    SUBTITLE_GENERATION
  }
  
  # Analytics
  type VideoAnalytics {
    videoId: ID!
    period: AnalyticsPeriod!
    
    # View analytics
    views: [AnalyticsDataPoint!]!
    uniqueViews: [AnalyticsDataPoint!]!
    watchTime: [AnalyticsDataPoint!]!
    
    # Engagement analytics
    likes: [AnalyticsDataPoint!]!
    shares: [AnalyticsDataPoint!]!
    comments: [AnalyticsDataPoint!]!
    
    # Performance metrics
    loadTime: [AnalyticsDataPoint!]!
    bufferEvents: [AnalyticsDataPoint!]!
    playbackErrors: [AnalyticsDataPoint!]!
    
    # Audience analytics
    demographics: VideoDemographics!
    devices: [DeviceAnalytics!]!
    locations: [LocationAnalytics!]!
    
    # Retention analytics
    retentionCurve: [RetentionPoint!]!
    averageWatchTime: Float!
    completionRate: Float!
    
    # Quality analytics
    qualityDistribution: [QualityAnalytics!]!
    bitrateUsage: [BitrateAnalytics!]!
  }
  
  type VideoDemographics {
    ageGroups: [AgeGroupAnalytics!]!
    genders: [GenderAnalytics!]!
    interests: [InterestAnalytics!]!
  }
  
  type AgeGroupAnalytics {
    ageGroup: String!
    count: Int!
    percentage: Float!
    watchTime: Float!
  }
  
  type GenderAnalytics {
    gender: String!
    count: Int!
    percentage: Float!
    watchTime: Float!
  }
  
  type InterestAnalytics {
    interest: String!
    count: Int!
    relevanceScore: Float!
  }
  
  type DeviceAnalytics {
    device: String!
    count: Int!
    percentage: Float!
    avgWatchTime: Float!
  }
  
  type LocationAnalytics {
    country: String!
    city: String
    count: Int!
    percentage: Float!
    avgWatchTime: Float!
  }
  
  type RetentionPoint {
    timestamp: Float!
    retentionRate: Float!
    viewerCount: Int!
  }
  
  type QualityAnalytics {
    quality: VideoQuality!
    count: Int!
    percentage: Float!
    avgWatchTime: Float!
  }
  
  type BitrateAnalytics {
    bitrate: Int!
    count: Int!
    percentage: Float!
    avgWatchTime: Float!
  }
  
  # Input types
  input UploadVideoInput {
    file: Upload!
    title: String!
    description: String
    folderId: ID
    visibility: VideoVisibility = PRIVATE
    tags: [String!]
    autoProcess: Boolean = true
    generateThumbnails: Boolean = true
    generatePreview: Boolean = true
  }
  
  input UpdateVideoInput {
    title: String
    description: String
    visibility: VideoVisibility
    tags: [String!]
    thumbnailTime: Float
  }
  
  input VideoProcessingInput {
    generateThumbnails: Boolean = true
    generatePreview: Boolean = true
    analyzeContent: Boolean = true
    detectScenes: Boolean = true
    detectObjects: Boolean = false
    detectFaces: Boolean = false
    extractText: Boolean = false
    transcribeAudio: Boolean = false
    generateSubtitles: Boolean = false
    priority: ProcessingPriority = NORMAL
  }
  
  input TranscodeVideoInput {
    qualities: [VideoQuality!]!
    formats: [String!]
    priority: ProcessingPriority = NORMAL
    deleteOriginal: Boolean = false
  }
  
  input VideoAnalysisInput {
    analyzeContent: Boolean = true
    analyzeQuality: Boolean = true
    analyzeAudio: Boolean = true
    detectObjects: Boolean = false
    detectFaces: Boolean = false
    extractText: Boolean = false
  }
  
  input CreateStreamInput {
    title: String!
    description: String
    scheduledAt: DateTime
    autoRecord: Boolean = true
    chatEnabled: Boolean = true
    quality: VideoQuality = HD_720P
  }
  
  input UpdateStreamInput {
    title: String
    description: String
    scheduledAt: DateTime
    chatEnabled: Boolean
    quality: VideoQuality
  }
  
  input UploadSubtitlesInput {
    file: Upload!
    language: String!
    label: String!
    isDefault: Boolean = false
  }
  
  input GenerateSubtitlesInput {
    language: String!
    label: String
    isDefault: Boolean = false
    transcribeAudio: Boolean = true
  }
  
  input UpdateSubtitlesInput {
    label: String
    isDefault: Boolean
    content: String
  }
  
  input AddChapterInput {
    title: String!
    startTime: Float!
    endTime: Float!
    description: String
  }
  
  input UpdateChapterInput {
    title: String
    startTime: Float
    endTime: Float
    description: String
  }
  
  input VideoFilterInput {
    title: String
    ownerId: ID
    folderId: ID
    status: VideoStatus
    visibility: VideoVisibility
    minDuration: Float
    maxDuration: Float
    minViews: Int
    tags: [String!]
    uploadedAfter: DateTime
    uploadedBefore: DateTime
    hasAnalysis: Boolean
    hasSubtitles: Boolean
  }
  
  input VideoSearchFilterInput {
    status: VideoStatus
    visibility: VideoVisibility
    minDuration: Float
    maxDuration: Float
    tags: [String!]
    hasAnalysis: Boolean
    hasSubtitles: Boolean
    uploadedAfter: DateTime
    uploadedBefore: DateTime
  }
  
  input ProcessingJobFilterInput {
    videoId: ID
    type: VideoProcessingType
    status: VideoProcessingStatus
    priority: ProcessingPriority
    startedAfter: DateTime
    startedBefore: DateTime
  }
  
  # Response types
  type UploadVideoPayload {
    success: Boolean!
    video: Video
    errors: [Error!]
  }
  
  type UpdateVideoPayload {
    success: Boolean!
    video: Video
    errors: [Error!]
  }
  
  type VideoProcessingPayload {
    success: Boolean!
    jobs: [VideoProcessingJob!]
    errors: [Error!]
  }
  
  type TranscodeVideoPayload {
    success: Boolean!
    job: VideoProcessingJob
    errors: [Error!]
  }
  
  type VideoAnalysisPayload {
    success: Boolean!
    job: VideoProcessingJob
    errors: [Error!]
  }
  
  type CreateStreamPayload {
    success: Boolean!
    stream: VideoStream
    streamKey: String!
    rtmpUrl: String!
    errors: [Error!]
  }
  
  type UpdateStreamPayload {
    success: Boolean!
    stream: VideoStream
    errors: [Error!]
  }
  
  type UploadSubtitlesPayload {
    success: Boolean!
    subtitles: VideoSubtitle
    errors: [Error!]
  }
  
  type GenerateSubtitlesPayload {
    success: Boolean!
    job: VideoProcessingJob
    errors: [Error!]
  }
  
  type UpdateSubtitlesPayload {
    success: Boolean!
    subtitles: VideoSubtitle
    errors: [Error!]
  }
  
  type AddChapterPayload {
    success: Boolean!
    chapter: VideoChapter
    errors: [Error!]
  }
  
  type UpdateChapterPayload {
    success: Boolean!
    chapter: VideoChapter
    errors: [Error!]
  }
  
  # Subscription types
  type VideoProcessingUpdate {
    videoId: ID!
    jobId: ID!
    type: VideoProcessingType!
    status: VideoProcessingStatus!
    progress: Float
    error: String
    result: JSON
    estimatedTimeRemaining: Float
  }
  
  type TranscodingUpdate {
    jobId: ID!
    videoId: ID!
    quality: VideoQuality!
    status: TranscodeStatus!
    progress: Float
    error: String
    url: String
  }
  
  type VideoAnalysisUpdate {
    videoId: ID!
    type: String!
    progress: Float
    result: JSON
    error: String
  }
  
  # Streaming types
  type VideoStream {
    id: ID!
    title: String!
    description: String
    status: StreamStatus!
    scheduledAt: DateTime
    startedAt: DateTime
    endedAt: DateTime
    streamKey: String!
    rtmpUrl: String!
    playbackUrl: String
    chatEnabled: Boolean!
    quality: VideoQuality!
    viewerCount: Int!
    recordedVideo: Video
    createdAt: DateTime!
  }
  
  enum StreamStatus {
    SCHEDULED
    LIVE
    ENDED
    CANCELLED
  }
  
  # Playlist support
  type Playlist implements Node {
    id: ID!
    title: String!
    description: String
    visibility: PlaylistVisibility!
    videos: [Video!]! @complexity(value: 10)
    videoCount: Int!
    totalDuration: Float!
    thumbnail: String
    owner: User! @complexity(value: 2)
    createdAt: DateTime!
    updatedAt: DateTime!
  }
  
  enum PlaylistVisibility {
    PRIVATE
    UNLISTED
    PUBLIC
  }
`;