const fs = require('fs-extra');
const path = require('path');
const { google } = require('googleapis');
const { Dropbox } = require('dropbox');
const AWS = require('aws-sdk');
const logger = require('../utils/logger');

class CloudProviderManager {
  constructor(options = {}) {
    this.options = options;
    this.providers = {};
    this.initializeProviders();
  }

  async initializeProviders() {
    // Initialize Google Drive
    if (this.options.googleDrive?.enabled) {
      this.providers.googleDrive = new GoogleDriveProvider(this.options.googleDrive);
    }

    // Initialize Dropbox
    if (this.options.dropbox?.enabled) {
      this.providers.dropbox = new DropboxProvider(this.options.dropbox);
    }

    // Initialize AWS S3
    if (this.options.s3?.enabled) {
      this.providers.s3 = new S3Provider(this.options.s3);
    }

    logger.info(`Initialized cloud providers: ${Object.keys(this.providers).join(', ')}`);
  }

  getProvider(providerName) {
    const provider = this.providers[providerName];
    if (!provider) {
      throw new Error(`Cloud provider not found or not enabled: ${providerName}`);
    }
    return provider;
  }

  async uploadToCloud(filePath, providerName, options = {}) {
    const provider = this.getProvider(providerName);
    return await provider.upload(filePath, options);
  }

  async downloadFromCloud(fileId, providerName, localPath, options = {}) {
    const provider = this.getProvider(providerName);
    return await provider.download(fileId, localPath, options);
  }

  async shareFile(fileId, providerName, options = {}) {
    const provider = this.getProvider(providerName);
    return await provider.share(fileId, options);
  }

  async deleteFromCloud(fileId, providerName, options = {}) {
    const provider = this.getProvider(providerName);
    return await provider.delete(fileId, options);
  }

  async listFiles(providerName, options = {}) {
    const provider = this.getProvider(providerName);
    return await provider.listFiles(options);
  }

  getAvailableProviders() {
    return Object.keys(this.providers);
  }
}

class GoogleDriveProvider {
  constructor(config) {
    this.config = config;
    this.auth = null;
    this.drive = null;
    this.initializeAuth();
  }

  async initializeAuth() {
    try {
      if (this.config.serviceAccountKey) {
        // Service Account authentication
        this.auth = new google.auth.GoogleAuth({
          keyFile: this.config.serviceAccountKey,
          scopes: ['https://www.googleapis.com/auth/drive']
        });
      } else if (this.config.clientId && this.config.clientSecret) {
        // OAuth2 authentication
        this.auth = new google.auth.OAuth2(
          this.config.clientId,
          this.config.clientSecret,
          this.config.redirectUri
        );
        
        if (this.config.refreshToken) {
          this.auth.setCredentials({
            refresh_token: this.config.refreshToken
          });
        }
      } else {
        throw new Error('Google Drive authentication configuration missing');
      }

      this.drive = google.drive({ version: 'v3', auth: this.auth });
      logger.info('Google Drive provider initialized');
    } catch (error) {
      logger.error('Failed to initialize Google Drive:', error);
      throw error;
    }
  }

  async upload(filePath, options = {}) {
    try {
      const fileName = options.fileName || path.basename(filePath);
      const folderId = options.folderId || this.config.defaultFolderId;
      const mimeType = this.getMimeType(filePath);

      const fileMetadata = {
        name: fileName,
        parents: folderId ? [folderId] : undefined
      };

      const media = {
        mimeType,
        body: fs.createReadStream(filePath)
      };

      const response = await this.drive.files.create({
        resource: fileMetadata,
        media: media,
        fields: 'id,name,size,mimeType,createdTime,webViewLink'
      });

      logger.info(`File uploaded to Google Drive: ${response.data.id}`);
      return {
        success: true,
        fileId: response.data.id,
        fileName: response.data.name,
        size: response.data.size,
        url: response.data.webViewLink,
        provider: 'googleDrive'
      };
    } catch (error) {
      logger.error('Google Drive upload failed:', error);
      throw new Error(`Google Drive upload failed: ${error.message}`);
    }
  }

  async download(fileId, localPath, options = {}) {
    try {
      const response = await this.drive.files.get({
        fileId: fileId,
        alt: 'media'
      }, { responseType: 'stream' });

      await fs.ensureDir(path.dirname(localPath));
      const writer = fs.createWriteStream(localPath);
      
      return new Promise((resolve, reject) => {
        response.data.pipe(writer);
        writer.on('finish', () => {
          logger.info(`File downloaded from Google Drive: ${fileId} -> ${localPath}`);
          resolve({
            success: true,
            localPath,
            fileId
          });
        });
        writer.on('error', reject);
      });
    } catch (error) {
      logger.error('Google Drive download failed:', error);
      throw new Error(`Google Drive download failed: ${error.message}`);
    }
  }

  async share(fileId, options = {}) {
    try {
      const shareOptions = {
        fileId: fileId,
        resource: {
          role: options.role || 'reader',
          type: options.type || 'anyone'
        }
      };

      if (options.emailAddress) {
        shareOptions.resource.type = 'user';
        shareOptions.resource.emailAddress = options.emailAddress;
      }

      await this.drive.permissions.create(shareOptions);

      const file = await this.drive.files.get({
        fileId: fileId,
        fields: 'webViewLink,webContentLink'
      });

      logger.info(`File shared on Google Drive: ${fileId}`);
      return {
        success: true,
        fileId,
        viewLink: file.data.webViewLink,
        downloadLink: file.data.webContentLink
      };
    } catch (error) {
      logger.error('Google Drive share failed:', error);
      throw new Error(`Google Drive share failed: ${error.message}`);
    }
  }

  async delete(fileId, options = {}) {
    try {
      await this.drive.files.delete({ fileId });
      logger.info(`File deleted from Google Drive: ${fileId}`);
      return { success: true, fileId };
    } catch (error) {
      logger.error('Google Drive delete failed:', error);
      throw new Error(`Google Drive delete failed: ${error.message}`);
    }
  }

  async listFiles(options = {}) {
    try {
      const query = {
        pageSize: options.pageSize || 100,
        fields: 'files(id,name,size,mimeType,createdTime,modifiedTime)',
        orderBy: options.orderBy || 'createdTime desc'
      };

      if (options.folderId) {
        query.q = `'${options.folderId}' in parents`;
      }

      if (options.mimeType) {
        query.q = query.q ? `${query.q} and mimeType='${options.mimeType}'` : `mimeType='${options.mimeType}'`;
      }

      const response = await this.drive.files.list(query);
      
      return {
        success: true,
        files: response.data.files.map(file => ({
          id: file.id,
          name: file.name,
          size: file.size,
          mimeType: file.mimeType,
          createdTime: file.createdTime,
          modifiedTime: file.modifiedTime
        }))
      };
    } catch (error) {
      logger.error('Google Drive list failed:', error);
      throw new Error(`Google Drive list failed: ${error.message}`);
    }
  }

  getMimeType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      '.pdf': 'application/pdf',
      '.zip': 'application/zip',
      '.tar': 'application/x-tar',
      '.gz': 'application/gzip',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.png': 'image/png',
      '.html': 'text/html',
      '.json': 'application/json',
      '.csv': 'text/csv',
      '.xml': 'application/xml'
    };
    return mimeTypes[ext] || 'application/octet-stream';
  }
}

class DropboxProvider {
  constructor(config) {
    this.config = config;
    this.dbx = new Dropbox({
      accessToken: config.accessToken,
      clientId: config.clientId,
      clientSecret: config.clientSecret
    });
    logger.info('Dropbox provider initialized');
  }

  async upload(filePath, options = {}) {
    try {
      const fileName = options.fileName || path.basename(filePath);
      const remotePath = options.remotePath || `/${fileName}`;
      const fileContent = await fs.readFile(filePath);

      const response = await this.dbx.filesUpload({
        path: remotePath,
        contents: fileContent,
        mode: 'overwrite',
        autorename: options.autorename !== false
      });

      logger.info(`File uploaded to Dropbox: ${response.result.path_display}`);
      return {
        success: true,
        fileId: response.result.id,
        fileName: response.result.name,
        path: response.result.path_display,
        size: response.result.size,
        provider: 'dropbox'
      };
    } catch (error) {
      logger.error('Dropbox upload failed:', error);
      throw new Error(`Dropbox upload failed: ${error.message}`);
    }
  }

  async download(filePath, localPath, options = {}) {
    try {
      const response = await this.dbx.filesDownload({ path: filePath });
      
      await fs.ensureDir(path.dirname(localPath));
      await fs.writeFile(localPath, response.result.fileBinary);

      logger.info(`File downloaded from Dropbox: ${filePath} -> ${localPath}`);
      return {
        success: true,
        localPath,
        filePath
      };
    } catch (error) {
      logger.error('Dropbox download failed:', error);
      throw new Error(`Dropbox download failed: ${error.message}`);
    }
  }

  async share(filePath, options = {}) {
    try {
      const response = await this.dbx.sharingCreateSharedLinkWithSettings({
        path: filePath,
        settings: {
          requested_visibility: options.visibility || 'public',
          audience: options.audience || 'public',
          access: options.access || 'viewer'
        }
      });

      logger.info(`File shared on Dropbox: ${filePath}`);
      return {
        success: true,
        filePath,
        shareUrl: response.result.url,
        directUrl: response.result.url.replace('?dl=0', '?dl=1')
      };
    } catch (error) {
      // Try to get existing shared link
      try {
        const existingLinks = await this.dbx.sharingListSharedLinks({
          path: filePath,
          direct_only: true
        });

        if (existingLinks.result.links.length > 0) {
          const link = existingLinks.result.links[0];
          return {
            success: true,
            filePath,
            shareUrl: link.url,
            directUrl: link.url.replace('?dl=0', '?dl=1')
          };
        }
      } catch (linkError) {
        logger.error('Failed to get existing Dropbox link:', linkError);
      }

      logger.error('Dropbox share failed:', error);
      throw new Error(`Dropbox share failed: ${error.message}`);
    }
  }

  async delete(filePath, options = {}) {
    try {
      await this.dbx.filesDeleteV2({ path: filePath });
      logger.info(`File deleted from Dropbox: ${filePath}`);
      return { success: true, filePath };
    } catch (error) {
      logger.error('Dropbox delete failed:', error);
      throw new Error(`Dropbox delete failed: ${error.message}`);
    }
  }

  async listFiles(options = {}) {
    try {
      const response = await this.dbx.filesListFolder({
        path: options.path || '',
        recursive: options.recursive || false,
        limit: options.limit || 100
      });

      return {
        success: true,
        files: response.result.entries
          .filter(entry => entry['.tag'] === 'file')
          .map(file => ({
            id: file.id,
            name: file.name,
            path: file.path_display,
            size: file.size,
            modifiedTime: file.client_modified,
            serverModifiedTime: file.server_modified
          }))
      };
    } catch (error) {
      logger.error('Dropbox list failed:', error);
      throw new Error(`Dropbox list failed: ${error.message}`);
    }
  }
}

class S3Provider {
  constructor(config) {
    this.config = config;
    this.s3 = new AWS.S3({
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey,
      region: config.region,
      endpoint: config.endpoint // For S3-compatible services
    });
    this.bucket = config.bucket;
    logger.info('S3 provider initialized');
  }

  async upload(filePath, options = {}) {
    try {
      const fileName = options.fileName || path.basename(filePath);
      const key = options.key || fileName;
      const fileContent = await fs.readFile(filePath);

      const params = {
        Bucket: this.bucket,
        Key: key,
        Body: fileContent,
        ContentType: this.getMimeType(filePath),
        Metadata: options.metadata || {}
      };

      if (options.public) {
        params.ACL = 'public-read';
      }

      const response = await this.s3.upload(params).promise();

      logger.info(`File uploaded to S3: ${response.Key}`);
      return {
        success: true,
        fileId: response.Key,
        fileName: fileName,
        url: response.Location,
        etag: response.ETag,
        provider: 's3'
      };
    } catch (error) {
      logger.error('S3 upload failed:', error);
      throw new Error(`S3 upload failed: ${error.message}`);
    }
  }

  async download(key, localPath, options = {}) {
    try {
      const params = {
        Bucket: this.bucket,
        Key: key
      };

      const response = await this.s3.getObject(params).promise();
      
      await fs.ensureDir(path.dirname(localPath));
      await fs.writeFile(localPath, response.Body);

      logger.info(`File downloaded from S3: ${key} -> ${localPath}`);
      return {
        success: true,
        localPath,
        key
      };
    } catch (error) {
      logger.error('S3 download failed:', error);
      throw new Error(`S3 download failed: ${error.message}`);
    }
  }

  async share(key, options = {}) {
    try {
      const params = {
        Bucket: this.bucket,
        Key: key,
        Expires: options.expiresIn || 3600 // 1 hour default
      };

      const url = await this.s3.getSignedUrlPromise('getObject', params);

      logger.info(`File shared on S3: ${key}`);
      return {
        success: true,
        key,
        shareUrl: url,
        expiresIn: params.Expires
      };
    } catch (error) {
      logger.error('S3 share failed:', error);
      throw new Error(`S3 share failed: ${error.message}`);
    }
  }

  async delete(key, options = {}) {
    try {
      await this.s3.deleteObject({
        Bucket: this.bucket,
        Key: key
      }).promise();

      logger.info(`File deleted from S3: ${key}`);
      return { success: true, key };
    } catch (error) {
      logger.error('S3 delete failed:', error);
      throw new Error(`S3 delete failed: ${error.message}`);
    }
  }

  async listFiles(options = {}) {
    try {
      const params = {
        Bucket: this.bucket,
        MaxKeys: options.maxKeys || 100,
        Prefix: options.prefix || ''
      };

      const response = await this.s3.listObjectsV2(params).promise();

      return {
        success: true,
        files: response.Contents.map(object => ({
          key: object.Key,
          name: path.basename(object.Key),
          size: object.Size,
          lastModified: object.LastModified,
          etag: object.ETag
        }))
      };
    } catch (error) {
      logger.error('S3 list failed:', error);
      throw new Error(`S3 list failed: ${error.message}`);
    }
  }

  getMimeType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      '.pdf': 'application/pdf',
      '.zip': 'application/zip',
      '.tar': 'application/x-tar',
      '.gz': 'application/gzip',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.png': 'image/png',
      '.html': 'text/html',
      '.json': 'application/json',
      '.csv': 'text/csv',
      '.xml': 'application/xml'
    };
    return mimeTypes[ext] || 'application/octet-stream';
  }
}

// Utility function to upload with progress tracking
async function uploadWithProgress(filePath, providerName, options = {}, progressCallback) {
  const cloudManager = new CloudProviderManager(options.providerConfigs || {});
  
  // Simple progress simulation - in real implementation, you'd use streaming uploads
  const intervals = 10;
  for (let i = 0; i <= intervals; i++) {
    if (progressCallback) {
      progressCallback({
        progress: (i / intervals) * 100,
        stage: i === 0 ? 'starting' : i === intervals ? 'finalizing' : 'uploading'
      });
    }
    
    if (i < intervals) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  return await cloudManager.uploadToCloud(filePath, providerName, options);
}

module.exports = {
  CloudProviderManager,
  GoogleDriveProvider,
  DropboxProvider,
  S3Provider,
  uploadWithProgress
};