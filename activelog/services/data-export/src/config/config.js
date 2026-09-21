const path = require('path');

module.exports = {
  server: {
    port: process.env.PORT || 8009,
    host: process.env.HOST || 'localhost'
  },

  cors: {
    origin: process.env.CORS_ORIGIN || '*',
    credentials: true
  },

  upload: {
    maxFileSize: parseInt(process.env.MAX_FILE_SIZE) || 100 * 1024 * 1024, // 100MB
    allowedTypes: [
      'application/pdf',
      'application/zip',
      'application/x-tar',
      'application/gzip',
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/bmp',
      'image/tiff',
      'text/plain',
      'text/csv',
      'text/html',
      'application/json',
      'application/xml',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ]
  },

  bulkExport: {
    maxConcurrentJobs: parseInt(process.env.BULK_MAX_CONCURRENT) || 3,
    jobTimeout: parseInt(process.env.BULK_JOB_TIMEOUT) || 30 * 60 * 1000, // 30 minutes
    retryAttempts: parseInt(process.env.BULK_RETRY_ATTEMPTS) || 3,
    retryDelay: parseInt(process.env.BULK_RETRY_DELAY) || 5000,
    progressUpdateInterval: parseInt(process.env.BULK_PROGRESS_INTERVAL) || 1000,
    enableScheduling: process.env.BULK_ENABLE_SCHEDULING === 'true',
    tempDir: process.env.BULK_TEMP_DIR || path.join(__dirname, '../../temp')
  },

  cloudProviders: {
    googleDrive: {
      enabled: process.env.GOOGLE_DRIVE_ENABLED === 'true',
      serviceAccountKey: process.env.GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY,
      clientId: process.env.GOOGLE_DRIVE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_DRIVE_CLIENT_SECRET,
      redirectUri: process.env.GOOGLE_DRIVE_REDIRECT_URI,
      refreshToken: process.env.GOOGLE_DRIVE_REFRESH_TOKEN,
      defaultFolderId: process.env.GOOGLE_DRIVE_DEFAULT_FOLDER
    },

    dropbox: {
      enabled: process.env.DROPBOX_ENABLED === 'true',
      accessToken: process.env.DROPBOX_ACCESS_TOKEN,
      clientId: process.env.DROPBOX_CLIENT_ID,
      clientSecret: process.env.DROPBOX_CLIENT_SECRET
    },

    s3: {
      enabled: process.env.S3_ENABLED === 'true',
      accessKeyId: process.env.S3_ACCESS_KEY_ID,
      secretAccessKey: process.env.S3_SECRET_ACCESS_KEY,
      region: process.env.S3_REGION || 'us-east-1',
      bucket: process.env.S3_BUCKET,
      endpoint: process.env.S3_ENDPOINT // For S3-compatible services
    }
  },

  exportOptions: {
    pdf: {
      pageSize: process.env.PDF_PAGE_SIZE || 'A4',
      orientation: process.env.PDF_ORIENTATION || 'portrait',
      margins: {
        top: parseInt(process.env.PDF_MARGIN_TOP) || 50,
        bottom: parseInt(process.env.PDF_MARGIN_BOTTOM) || 50,
        left: parseInt(process.env.PDF_MARGIN_LEFT) || 50,
        right: parseInt(process.env.PDF_MARGIN_RIGHT) || 50
      },
      font: process.env.PDF_FONT || 'Helvetica',
      preserveMetadata: process.env.PDF_PRESERVE_METADATA !== 'false',
      includeTimestamps: process.env.PDF_INCLUDE_TIMESTAMPS !== 'false'
    },

    archive: {
      compressionLevel: parseInt(process.env.ARCHIVE_COMPRESSION_LEVEL) || 6,
      includeMetadata: process.env.ARCHIVE_INCLUDE_METADATA !== 'false',
      preservePermissions: process.env.ARCHIVE_PRESERVE_PERMISSIONS !== 'false',
      generateChecksum: process.env.ARCHIVE_GENERATE_CHECKSUM !== 'false',
      maxFileSize: parseInt(process.env.ARCHIVE_MAX_FILE_SIZE) || 1024 * 1024 * 1024 // 1GB
    },

    website: {
      theme: process.env.WEBSITE_THEME || 'default',
      includeSearch: process.env.WEBSITE_INCLUDE_SEARCH !== 'false',
      generateSitemap: process.env.WEBSITE_GENERATE_SITEMAP !== 'false',
      optimizeImages: process.env.WEBSITE_OPTIMIZE_IMAGES !== 'false',
      responsiveDesign: process.env.WEBSITE_RESPONSIVE !== 'false',
      baseUrl: process.env.WEBSITE_BASE_URL
    },

    photobook: {
      format: process.env.PHOTOBOOK_FORMAT || 'A4',
      orientation: process.env.PHOTOBOOK_ORIENTATION || 'portrait',
      theme: process.env.PHOTOBOOK_THEME || 'classic',
      layout: process.env.PHOTOBOOK_LAYOUT || 'auto',
      imagesPerPage: parseInt(process.env.PHOTOBOOK_IMAGES_PER_PAGE) || 4,
      includeMetadata: process.env.PHOTOBOOK_INCLUDE_METADATA !== 'false',
      imageQuality: parseInt(process.env.PHOTOBOOK_IMAGE_QUALITY) || 300
    },

    gdpr: {
      includeDataProcessingLog: process.env.GDPR_INCLUDE_PROCESSING_LOG !== 'false',
      includeLegalBasis: process.env.GDPR_INCLUDE_LEGAL_BASIS !== 'false',
      includeRetentionPolicy: process.env.GDPR_INCLUDE_RETENTION !== 'false',
      includeThirdPartyProcessors: process.env.GDPR_INCLUDE_THIRD_PARTY !== 'false',
      anonymizeIdentifiers: process.env.GDPR_ANONYMIZE === 'true',
      encryptOutput: process.env.GDPR_ENCRYPT === 'true',
      generateAuditLog: process.env.GDPR_GENERATE_AUDIT !== 'false',
      dataController: process.env.GDPR_DATA_CONTROLLER || 'Data Controller',
      contactEmail: process.env.GDPR_CONTACT_EMAIL || 'privacy@example.com',
      controllerAddress: process.env.GDPR_CONTROLLER_ADDRESS,
      registrationNumber: process.env.GDPR_REGISTRATION_NUMBER
    }
  },

  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || path.join(__dirname, '../../logs/app.log'),
    maxFiles: parseInt(process.env.LOG_MAX_FILES) || 5,
    maxSize: process.env.LOG_MAX_SIZE || '10m'
  },

  security: {
    rateLimitWindow: parseInt(process.env.RATE_LIMIT_WINDOW) || 15 * 60 * 1000, // 15 minutes
    rateLimitMax: parseInt(process.env.RATE_LIMIT_MAX) || 100,
    exportRateLimitPoints: parseInt(process.env.EXPORT_RATE_LIMIT_POINTS) || 10,
    exportRateLimitDuration: parseInt(process.env.EXPORT_RATE_LIMIT_DURATION) || 60, // seconds
    enableHelmet: process.env.ENABLE_HELMET !== 'false',
    enableCompression: process.env.ENABLE_COMPRESSION !== 'false'
  },

  cleanup: {
    tempFileRetention: parseInt(process.env.TEMP_FILE_RETENTION) || 24 * 60 * 60 * 1000, // 24 hours
    outputFileRetention: parseInt(process.env.OUTPUT_FILE_RETENTION) || 24 * 60 * 60 * 1000, // 24 hours
    cleanupInterval: parseInt(process.env.CLEANUP_INTERVAL) || 60 * 60 * 1000, // 1 hour
    jobHistoryRetention: parseInt(process.env.JOB_HISTORY_RETENTION) || 7 * 24 * 60 * 60 * 1000 // 7 days
  }
};