const fs = require('fs-extra');
const path = require('path');
const moment = require('moment');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');
const PDFExporter = require('./pdfExporter');
const ArchiveExporter = require('./archiveExporter');
const logger = require('../utils/logger');

class GDPRExporter {
  constructor(options = {}) {
    this.options = {
      includeDataProcessingLog: options.includeDataProcessingLog !== false,
      includeLegalBasis: options.includeLegalBasis !== false,
      includeRetentionPolicy: options.includeRetentionPolicy !== false,
      includeDataSources: options.includeDataSources !== false,
      includeThirdPartyProcessors: options.includeThirdPartyProcessors !== false,
      anonymizeIdentifiers: options.anonymizeIdentifiers || false,
      encryptOutput: options.encryptOutput || false,
      generateAuditLog: options.generateAuditLog !== false,
      dataController: options.dataController || 'Data Controller',
      contactEmail: options.contactEmail || 'privacy@example.com',
      ...options
    };

    this.pdfExporter = new PDFExporter();
    this.archiveExporter = new ArchiveExporter();
  }

  async exportGDPRData(userData, outputPath, requestDetails = {}) {
    try {
      const exportId = uuidv4();
      const exportTimestamp = moment().toISOString();

      // Validate and process user data
      const processedData = await this.processUserData(userData, requestDetails);

      // Generate export metadata
      const exportMetadata = this.generateExportMetadata(processedData, requestDetails, exportId, exportTimestamp);

      // Create GDPR-compliant export package
      const exportResult = await this.createExportPackage(processedData, exportMetadata, outputPath);

      // Generate audit log
      if (this.options.generateAuditLog) {
        await this.generateAuditLog(exportId, requestDetails, exportResult);
      }

      logger.info(`GDPR export completed: ${exportId}`);
      return {
        success: true,
        exportId,
        ...exportResult
      };
    } catch (error) {
      logger.error('GDPR export failed:', error);
      throw error;
    }
  }

  async processUserData(userData, requestDetails) {
    const processed = {
      personalData: {},
      systemData: {},
      interactionData: {},
      preferences: {},
      files: [],
      metadata: {}
    };

    // Categorize data according to GDPR categories
    for (const [key, value] of Object.entries(userData)) {
      const category = this.categorizeData(key, value);
      
      if (category === 'personal') {
        processed.personalData[key] = this.sanitizeData(value, requestDetails);
      } else if (category === 'system') {
        processed.systemData[key] = this.sanitizeData(value, requestDetails);
      } else if (category === 'interaction') {
        processed.interactionData[key] = this.sanitizeData(value, requestDetails);
      } else if (category === 'preferences') {
        processed.preferences[key] = this.sanitizeData(value, requestDetails);
      } else if (category === 'file') {
        processed.files.push(this.processFile(value, requestDetails));
      } else {
        processed.metadata[key] = this.sanitizeData(value, requestDetails);
      }
    }

    return processed;
  }

  categorizeData(key, value) {
    const personalDataKeys = [
      'name', 'email', 'phone', 'address', 'birthdate', 'ssn', 'passport',
      'firstName', 'lastName', 'fullName', 'dateOfBirth', 'nationality'
    ];

    const systemDataKeys = [
      'id', 'userId', 'accountId', 'createdAt', 'updatedAt', 'lastLogin',
      'passwordHash', 'apiKeys', 'tokens', 'sessions'
    ];

    const interactionDataKeys = [
      'clicks', 'views', 'purchases', 'searches', 'downloads', 'uploads',
      'messages', 'posts', 'comments', 'likes', 'shares', 'activities'
    ];

    const preferencesKeys = [
      'settings', 'preferences', 'notifications', 'privacy', 'theme',
      'language', 'timezone', 'currency'
    ];

    const lowerKey = key.toLowerCase();

    if (personalDataKeys.some(k => lowerKey.includes(k))) return 'personal';
    if (systemDataKeys.some(k => lowerKey.includes(k))) return 'system';
    if (interactionDataKeys.some(k => lowerKey.includes(k))) return 'interaction';
    if (preferencesKeys.some(k => lowerKey.includes(k))) return 'preferences';
    if (typeof value === 'string' && this.isFilePath(value)) return 'file';

    return 'metadata';
  }

  sanitizeData(data, requestDetails) {
    if (this.options.anonymizeIdentifiers && requestDetails.anonymize) {
      return this.anonymizeData(data);
    }
    return data;
  }

  anonymizeData(data) {
    if (typeof data === 'string') {
      // Anonymize email addresses
      if (data.includes('@')) {
        return data.replace(/^(.{2}).*(@.*)$/, '$1***$2');
      }
      // Anonymize phone numbers
      if (/^\+?[\d\s\-\(\)]+$/.test(data)) {
        return data.replace(/\d/g, '*').slice(0, -4) + data.slice(-4);
      }
      // Anonymize long strings that might be names or addresses
      if (data.length > 10 && !/^\d+$/.test(data)) {
        return data.slice(0, 3) + '*'.repeat(data.length - 6) + data.slice(-3);
      }
    } else if (typeof data === 'object' && data !== null) {
      const anonymized = {};
      for (const [key, value] of Object.entries(data)) {
        anonymized[key] = this.anonymizeData(value);
      }
      return anonymized;
    }
    return data;
  }

  processFile(filePath, requestDetails) {
    return {
      originalPath: filePath,
      filename: path.basename(filePath),
      size: 0, // Will be filled when file is processed
      type: path.extname(filePath),
      lastModified: null,
      includeInExport: true
    };
  }

  generateExportMetadata(processedData, requestDetails, exportId, timestamp) {
    return {
      exportInfo: {
        exportId,
        timestamp,
        requestDate: requestDetails.requestDate || timestamp,
        dataSubject: {
          id: requestDetails.dataSubjectId,
          email: requestDetails.dataSubjectEmail,
          name: requestDetails.dataSubjectName
        },
        requestType: requestDetails.requestType || 'data_portability',
        legalBasis: requestDetails.legalBasis || 'GDPR Article 20 - Right to Data Portability'
      },
      dataController: {
        name: this.options.dataController,
        contactEmail: this.options.contactEmail,
        address: this.options.controllerAddress,
        registrationNumber: this.options.registrationNumber
      },
      dataCategories: {
        personalData: Object.keys(processedData.personalData).length,
        systemData: Object.keys(processedData.systemData).length,
        interactionData: Object.keys(processedData.interactionData).length,
        preferences: Object.keys(processedData.preferences).length,
        files: processedData.files.length
      },
      processingPurposes: this.getProcessingPurposes(),
      legalBases: this.getLegalBases(),
      retentionPeriods: this.getRetentionPeriods(),
      dataSources: this.getDataSources(),
      thirdPartyProcessors: this.getThirdPartyProcessors(),
      dataSubjectRights: this.getDataSubjectRights(),
      technicalMeasures: this.getTechnicalMeasures()
    };
  }

  async createExportPackage(processedData, metadata, outputPath) {
    const tempDir = path.join(path.dirname(outputPath), `gdpr_temp_${Date.now()}`);
    await fs.ensureDir(tempDir);

    try {
      // Generate main data export PDF
      const dataPdfPath = path.join(tempDir, 'personal_data_export.pdf');
      await this.generateDataExportPDF(processedData, dataPdfPath, metadata);

      // Generate metadata document
      const metadataPdfPath = path.join(tempDir, 'export_metadata.pdf');
      await this.generateMetadataPDF(metadata, metadataPdfPath);

      // Generate data processing record
      if (this.options.includeDataProcessingLog) {
        const processingLogPath = path.join(tempDir, 'data_processing_record.pdf');
        await this.generateProcessingLogPDF(metadata, processingLogPath);
      }

      // Copy user files
      const filesDir = path.join(tempDir, 'files');
      await this.copyUserFiles(processedData.files, filesDir);

      // Generate machine-readable data files
      await this.generateMachineReadableFiles(processedData, tempDir);

      // Create final archive
      const sources = await this.collectExportSources(tempDir);
      const archiveResult = await this.archiveExporter.createZipArchive(
        sources,
        outputPath,
        metadata
      );

      // Encrypt if requested
      if (this.options.encryptOutput) {
        const encryptedPath = outputPath + '.encrypted';
        await this.encryptFile(outputPath, encryptedPath, metadata.exportInfo.exportId);
        await fs.remove(outputPath);
        archiveResult.outputPath = encryptedPath;
        archiveResult.encrypted = true;
      }

      await fs.remove(tempDir);

      return archiveResult;
    } catch (error) {
      await fs.remove(tempDir);
      throw error;
    }
  }

  async generateDataExportPDF(processedData, outputPath, metadata) {
    const pdfData = this.structureDataForPDF(processedData, metadata);
    
    const pdfMetadata = {
      title: 'Personal Data Export',
      subject: 'GDPR Article 20 - Right to Data Portability',
      author: this.options.dataController,
      keywords: 'GDPR, Data Export, Personal Data',
      footer: `Export ID: ${metadata.exportInfo.exportId} | Generated: ${metadata.exportInfo.timestamp}`
    };

    return await this.pdfExporter.exportToPDF(pdfData, outputPath, pdfMetadata);
  }

  async generateMetadataPDF(metadata, outputPath) {
    const metadataContent = [
      {
        type: 'text',
        content: 'DATA EXPORT METADATA',
        fontSize: 20,
        font: 'Helvetica-Bold',
        align: 'center',
        spacing: 2
      },
      {
        type: 'metadata',
        data: {
          'Export ID': metadata.exportInfo.exportId,
          'Export Date': metadata.exportInfo.timestamp,
          'Request Date': metadata.exportInfo.requestDate,
          'Data Subject': metadata.exportInfo.dataSubject.name || metadata.exportInfo.dataSubject.email,
          'Request Type': metadata.exportInfo.requestType,
          'Legal Basis': metadata.exportInfo.legalBasis
        }
      },
      {
        type: 'text',
        content: 'DATA CONTROLLER INFORMATION',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 1
      },
      {
        type: 'metadata',
        data: {
          'Name': metadata.dataController.name,
          'Contact Email': metadata.dataController.contactEmail,
          'Address': metadata.dataController.address || 'Not specified',
          'Registration Number': metadata.dataController.registrationNumber || 'Not specified'
        }
      },
      {
        type: 'text',
        content: 'DATA CATEGORIES',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 1
      },
      {
        type: 'metadata',
        data: metadata.dataCategories
      }
    ];

    const pdfMetadata = {
      title: 'Export Metadata',
      subject: 'GDPR Data Export Metadata',
      author: this.options.dataController
    };

    return await this.pdfExporter.exportToPDF(metadataContent, outputPath, pdfMetadata);
  }

  async generateProcessingLogPDF(metadata, outputPath) {
    const processingContent = [
      {
        type: 'text',
        content: 'DATA PROCESSING RECORD',
        fontSize: 20,
        font: 'Helvetica-Bold',
        align: 'center',
        spacing: 2
      },
      {
        type: 'text',
        content: 'PROCESSING PURPOSES',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 1
      }
    ];

    metadata.processingPurposes.forEach(purpose => {
      processingContent.push({
        type: 'text',
        content: `• ${purpose}`,
        fontSize: 12
      });
    });

    processingContent.push({
      type: 'text',
      content: 'LEGAL BASES',
      fontSize: 16,
      font: 'Helvetica-Bold',
      spacing: 2
    });

    metadata.legalBases.forEach(basis => {
      processingContent.push({
        type: 'text',
        content: `• ${basis}`,
        fontSize: 12
      });
    });

    if (this.options.includeRetentionPolicy) {
      processingContent.push({
        type: 'text',
        content: 'RETENTION PERIODS',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 2
      });

      Object.entries(metadata.retentionPeriods).forEach(([category, period]) => {
        processingContent.push({
          type: 'text',
          content: `${category}: ${period}`,
          fontSize: 12
        });
      });
    }

    if (this.options.includeThirdPartyProcessors) {
      processingContent.push({
        type: 'text',
        content: 'THIRD-PARTY PROCESSORS',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 2
      });

      metadata.thirdPartyProcessors.forEach(processor => {
        processingContent.push({
          type: 'text',
          content: `${processor.name} - ${processor.purpose}`,
          fontSize: 12
        });
      });
    }

    const pdfMetadata = {
      title: 'Data Processing Record',
      subject: 'GDPR Data Processing Log',
      author: this.options.dataController
    };

    return await this.pdfExporter.exportToPDF(processingContent, outputPath, pdfMetadata);
  }

  async copyUserFiles(files, filesDir) {
    await fs.ensureDir(filesDir);

    for (const file of files) {
      if (file.includeInExport && await fs.pathExists(file.originalPath)) {
        const targetPath = path.join(filesDir, file.filename);
        await fs.copy(file.originalPath, targetPath);
        
        // Update file info
        const stats = await fs.stat(targetPath);
        file.size = stats.size;
        file.lastModified = stats.mtime.toISOString();
      }
    }
  }

  async generateMachineReadableFiles(processedData, outputDir) {
    // JSON export
    const jsonPath = path.join(outputDir, 'data_export.json');
    await fs.writeFile(jsonPath, JSON.stringify(processedData, null, 2));

    // CSV export for tabular data
    if (Object.keys(processedData.interactionData).length > 0) {
      const csvWriter = require('csv-writer').createObjectCsvWriter;
      const csvPath = path.join(outputDir, 'interaction_data.csv');
      
      // Convert interaction data to CSV format
      const csvData = this.convertToCSVFormat(processedData.interactionData);
      if (csvData.length > 0) {
        const writer = csvWriter({
          path: csvPath,
          header: Object.keys(csvData[0]).map(key => ({ id: key, title: key }))
        });
        await writer.writeRecords(csvData);
      }
    }

    // XML export
    const xml2js = require('xml2js');
    const builder = new xml2js.Builder();
    const xml = builder.buildObject({ gdprExport: processedData });
    const xmlPath = path.join(outputDir, 'data_export.xml');
    await fs.writeFile(xmlPath, xml);
  }

  async collectExportSources(tempDir) {
    const sources = [];
    const files = await fs.readdir(tempDir, { withFileTypes: true });

    for (const file of files) {
      const fullPath = path.join(tempDir, file.name);
      sources.push({
        path: fullPath,
        name: file.name
      });
    }

    return sources;
  }

  structureDataForPDF(processedData, metadata) {
    const pdfData = [
      {
        type: 'text',
        content: 'PERSONAL DATA EXPORT',
        fontSize: 24,
        font: 'Helvetica-Bold',
        align: 'center',
        spacing: 2
      },
      {
        type: 'text',
        content: `Export Date: ${moment().format('YYYY-MM-DD HH:mm:ss')}`,
        fontSize: 12,
        spacing: 1
      },
      {
        type: 'text',
        content: 'This document contains all personal data processed by our service in accordance with GDPR Article 20 - Right to Data Portability.',
        fontSize: 10,
        spacing: 2
      }
    ];

    // Add personal data section
    if (Object.keys(processedData.personalData).length > 0) {
      pdfData.push({
        type: 'text',
        content: 'PERSONAL INFORMATION',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 1
      });
      
      pdfData.push({
        type: 'metadata',
        data: processedData.personalData
      });
    }

    // Add system data section
    if (Object.keys(processedData.systemData).length > 0) {
      pdfData.push({
        type: 'text',
        content: 'SYSTEM DATA',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 1
      });
      
      pdfData.push({
        type: 'metadata',
        data: processedData.systemData
      });
    }

    // Add interaction data section
    if (Object.keys(processedData.interactionData).length > 0) {
      pdfData.push({
        type: 'text',
        content: 'INTERACTION DATA',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 1
      });
      
      // Convert to table format if possible
      const tableData = this.convertToTableFormat(processedData.interactionData);
      if (tableData) {
        pdfData.push({
          type: 'table',
          data: tableData
        });
      } else {
        pdfData.push({
          type: 'metadata',
          data: processedData.interactionData
        });
      }
    }

    // Add preferences section
    if (Object.keys(processedData.preferences).length > 0) {
      pdfData.push({
        type: 'text',
        content: 'PREFERENCES & SETTINGS',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 1
      });
      
      pdfData.push({
        type: 'metadata',
        data: processedData.preferences
      });
    }

    // Add files section
    if (processedData.files.length > 0) {
      pdfData.push({
        type: 'text',
        content: 'FILES & DOCUMENTS',
        fontSize: 16,
        font: 'Helvetica-Bold',
        spacing: 1
      });

      const filesTable = {
        headers: ['Filename', 'Size', 'Type', 'Last Modified'],
        rows: processedData.files.map(file => [
          file.filename,
          this.formatBytes(file.size || 0),
          file.type || 'Unknown',
          file.lastModified || 'Unknown'
        ])
      };

      pdfData.push({
        type: 'table',
        data: filesTable
      });
    }

    return pdfData;
  }

  convertToTableFormat(data) {
    // Try to convert object data to table format
    const entries = Object.entries(data);
    if (entries.length === 0) return null;

    // Check if all values are similar objects (for tabular data)
    const firstValue = entries[0][1];
    if (Array.isArray(firstValue) && firstValue.length > 0 && typeof firstValue[0] === 'object') {
      const headers = Object.keys(firstValue[0]);
      const rows = firstValue.map(item => headers.map(header => String(item[header] || '')));
      return { headers, rows };
    }

    return null;
  }

  convertToCSVFormat(data) {
    const csvData = [];
    
    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value)) {
        value.forEach(item => {
          if (typeof item === 'object') {
            csvData.push({ category: key, ...item });
          } else {
            csvData.push({ category: key, value: String(item) });
          }
        });
      } else if (typeof value === 'object') {
        csvData.push({ category: key, ...value });
      } else {
        csvData.push({ category: key, value: String(value) });
      }
    }
    
    return csvData;
  }

  async encryptFile(inputPath, outputPath, passphrase) {
    const algorithm = 'aes-256-cbc';
    const key = crypto.scryptSync(passphrase, 'salt', 32);
    const iv = crypto.randomBytes(16);

    const cipher = crypto.createCipher(algorithm, key);
    const input = fs.createReadStream(inputPath);
    const output = fs.createWriteStream(outputPath);

    return new Promise((resolve, reject) => {
      input.pipe(cipher).pipe(output);
      output.on('finish', resolve);
      output.on('error', reject);
    });
  }

  async generateAuditLog(exportId, requestDetails, exportResult) {
    const auditEntry = {
      timestamp: moment().toISOString(),
      exportId,
      event: 'gdpr_data_export',
      dataSubject: requestDetails.dataSubjectId,
      requestType: requestDetails.requestType,
      outputPath: exportResult.outputPath,
      fileSize: exportResult.fileSize,
      encrypted: exportResult.encrypted || false,
      success: exportResult.success,
      processingTime: exportResult.processingTime
    };

    const auditLogPath = path.join(__dirname, '../../logs/gdpr_audit.log');
    await fs.ensureDir(path.dirname(auditLogPath));
    await fs.appendFile(auditLogPath, JSON.stringify(auditEntry) + '\n');
  }

  getProcessingPurposes() {
    return [
      'Service provision and account management',
      'Communication with users',
      'Security and fraud prevention',
      'Analytics and service improvement',
      'Legal compliance and record keeping'
    ];
  }

  getLegalBases() {
    return [
      'GDPR Article 6(1)(a) - Consent',
      'GDPR Article 6(1)(b) - Contract performance',
      'GDPR Article 6(1)(c) - Legal obligation',
      'GDPR Article 6(1)(f) - Legitimate interests'
    ];
  }

  getRetentionPeriods() {
    return {
      'Personal Information': '7 years after account closure',
      'System Data': '2 years after last login',
      'Interaction Data': '3 years from collection',
      'Preferences': 'Until account closure',
      'Files': 'As long as account is active'
    };
  }

  getDataSources() {
    return [
      'User registration and profile updates',
      'Service usage and interactions',
      'Customer support communications',
      'Third-party integrations',
      'Publicly available sources'
    ];
  }

  getThirdPartyProcessors() {
    return [
      { name: 'Cloud Storage Provider', purpose: 'Data hosting and backup' },
      { name: 'Analytics Service', purpose: 'Usage analytics and insights' },
      { name: 'Email Service', purpose: 'Communication delivery' },
      { name: 'Payment Processor', purpose: 'Payment processing' }
    ];
  }

  getDataSubjectRights() {
    return [
      'Right of access (Article 15)',
      'Right to rectification (Article 16)',
      'Right to erasure (Article 17)',
      'Right to restrict processing (Article 18)',
      'Right to data portability (Article 20)',
      'Right to object (Article 21)'
    ];
  }

  getTechnicalMeasures() {
    return [
      'Encryption in transit and at rest',
      'Access controls and authentication',
      'Regular security assessments',
      'Data minimization practices',
      'Automated backup and recovery'
    ];
  }

  isFilePath(value) {
    return typeof value === 'string' && 
           (value.includes('/') || value.includes('\\')) &&
           path.extname(value).length > 0;
  }

  formatBytes(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }
}

module.exports = GDPRExporter;