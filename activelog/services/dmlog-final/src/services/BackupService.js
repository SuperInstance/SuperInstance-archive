import archiver from 'archiver';
import fs from 'fs/promises';
import path from 'path';
import AWS from 'aws-sdk';
import { PDFDocument, rgb } from 'pdf-lib';
import sharp from 'sharp';
import mongoose from 'mongoose';
import cron from 'node-cron';

class BackupService {
  constructor() {
    this.backupPath = path.join(process.cwd(), 'backups');
    this.s3 = null;
    this.scheduledJobs = new Map();
    
    this.initializeAWS();
    this.ensureBackupDirectory();
    this.setupScheduledBackups();
  }

  async initializeAWS() {
    if (process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY) {
      this.s3 = new AWS.S3({
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
        region: process.env.AWS_REGION || 'us-east-1'
      });
    }
  }

  async ensureBackupDirectory() {
    try {
      await fs.mkdir(this.backupPath, { recursive: true });
      await fs.mkdir(path.join(this.backupPath, 'campaigns'), { recursive: true });
      await fs.mkdir(path.join(this.backupPath, 'characters'), { recursive: true });
      await fs.mkdir(path.join(this.backupPath, 'exports'), { recursive: true });
      await fs.mkdir(path.join(this.backupPath, 'assets'), { recursive: true });
    } catch (error) {
      console.error('Failed to create backup directories:', error);
    }
  }

  setupScheduledBackups() {
    // Daily incremental backup at 2 AM
    this.scheduledJobs.set('daily', cron.schedule('0 2 * * *', async () => {
      await this.performDailyBackup();
    }, { scheduled: false }));

    // Weekly full backup on Sundays at 1 AM
    this.scheduledJobs.set('weekly', cron.schedule('0 1 * * 0', async () => {
      await this.performFullBackup();
    }, { scheduled: false }));

    // Monthly archive on the 1st at midnight
    this.scheduledJobs.set('monthly', cron.schedule('0 0 1 * *', async () => {
      await this.performMonthlyArchive();
    }, { scheduled: false }));
  }

  startScheduledBackups() {
    this.scheduledJobs.forEach((job) => job.start());
  }

  stopScheduledBackups() {
    this.scheduledJobs.forEach((job) => job.stop());
  }

  async performDailyBackup() {
    const backupId = `daily_${new Date().toISOString().split('T')[0]}`;
    
    try {
      // Backup recent campaign data (last 7 days)
      const recentCampaigns = await this.getRecentCampaigns(7);
      const recentCharacters = await this.getRecentCharacters(7);
      
      const backup = {
        id: backupId,
        type: 'incremental',
        timestamp: new Date().toISOString(),
        campaigns: recentCampaigns,
        characters: recentCharacters,
        metadata: {
          version: '2.0.0',
          totalCampaigns: recentCampaigns.length,
          totalCharacters: recentCharacters.length
        }
      };

      const backupPath = await this.createBackupArchive(backup, 'daily');
      
      if (this.s3) {
        await this.uploadToS3(backupPath, `dmlog-backups/daily/${backupId}.zip`);
      }

      return {
        success: true,
        backupId,
        path: backupPath,
        size: await this.getFileSize(backupPath)
      };
    } catch (error) {
      console.error('Daily backup failed:', error);
      throw error;
    }
  }

  async performFullBackup() {
    const backupId = `full_${new Date().toISOString().split('T')[0]}`;
    
    try {
      // Backup all data
      const allCampaigns = await this.getAllCampaigns();
      const allCharacters = await this.getAllCharacters();
      const userSettings = await this.getUserSettings();
      const marketplaceData = await this.getMarketplaceData();
      
      const backup = {
        id: backupId,
        type: 'full',
        timestamp: new Date().toISOString(),
        campaigns: allCampaigns,
        characters: allCharacters,
        userSettings,
        marketplaceData,
        metadata: {
          version: '2.0.0',
          totalCampaigns: allCampaigns.length,
          totalCharacters: allCharacters.length,
          totalUsers: userSettings.length
        }
      };

      const backupPath = await this.createBackupArchive(backup, 'weekly');
      
      if (this.s3) {
        await this.uploadToS3(backupPath, `dmlog-backups/weekly/${backupId}.zip`);
      }

      // Clean up old daily backups (keep last 7 days)
      await this.cleanupOldBackups('daily', 7);

      return {
        success: true,
        backupId,
        path: backupPath,
        size: await this.getFileSize(backupPath)
      };
    } catch (error) {
      console.error('Full backup failed:', error);
      throw error;
    }
  }

  async performMonthlyArchive() {
    const archiveId = `archive_${new Date().getFullYear()}_${String(new Date().getMonth() + 1).padStart(2, '0')}`;
    
    try {
      // Create comprehensive archive with exports
      const allData = await this.getAllData();
      
      // Generate PDF exports for campaigns
      const campaignPDFs = await Promise.all(
        allData.campaigns.map(campaign => this.exportCampaignToPDF(campaign))
      );

      // Generate character sheet PDFs
      const characterPDFs = await Promise.all(
        allData.characters.map(character => this.exportCharacterToPDF(character))
      );

      const archive = {
        id: archiveId,
        type: 'archive',
        timestamp: new Date().toISOString(),
        data: allData,
        exports: {
          campaignPDFs,
          characterPDFs
        },
        metadata: {
          version: '2.0.0',
          archiveYear: new Date().getFullYear(),
          archiveMonth: new Date().getMonth() + 1
        }
      };

      const archivePath = await this.createBackupArchive(archive, 'monthly');
      
      if (this.s3) {
        await this.uploadToS3(archivePath, `dmlog-backups/archives/${archiveId}.zip`);
      }

      // Clean up old weekly backups (keep last 4 weeks)
      await this.cleanupOldBackups('weekly', 4);

      return {
        success: true,
        archiveId,
        path: archivePath,
        size: await this.getFileSize(archivePath)
      };
    } catch (error) {
      console.error('Monthly archive failed:', error);
      throw error;
    }
  }

  async createBackupArchive(data, type) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${type}_backup_${timestamp}.zip`;
    const archivePath = path.join(this.backupPath, filename);

    return new Promise((resolve, reject) => {
      const output = require('fs').createWriteStream(archivePath);
      const archive = archiver('zip', { zlib: { level: 9 } });

      output.on('close', () => resolve(archivePath));
      archive.on('error', reject);

      archive.pipe(output);

      // Add data as JSON
      archive.append(JSON.stringify(data, null, 2), { name: 'backup.json' });

      // Add asset files if they exist
      if (data.campaigns) {
        data.campaigns.forEach((campaign, index) => {
          if (campaign.assets) {
            campaign.assets.forEach((asset) => {
              if (asset.localPath) {
                archive.file(asset.localPath, { name: `campaigns/${index}/assets/${asset.filename}` });
              }
            });
          }
        });
      }

      // Add exports if they exist
      if (data.exports) {
        if (data.exports.campaignPDFs) {
          data.exports.campaignPDFs.forEach((pdf, index) => {
            archive.append(pdf.buffer, { name: `exports/campaigns/${pdf.filename}` });
          });
        }
        if (data.exports.characterPDFs) {
          data.exports.characterPDFs.forEach((pdf, index) => {
            archive.append(pdf.buffer, { name: `exports/characters/${pdf.filename}` });
          });
        }
      }

      archive.finalize();
    });
  }

  async exportCampaignToPDF(campaign) {
    const pdfDoc = await PDFDocument.create();
    let page = pdfDoc.addPage([595, 842]); // A4 size

    const fontSize = 12;
    const titleFontSize = 18;
    let yPosition = 800;

    // Title
    page.drawText(campaign.name || 'Campaign', {
      x: 50,
      y: yPosition,
      size: titleFontSize,
      color: rgb(0.2, 0.2, 0.8)
    });
    yPosition -= 40;

    // Campaign details
    const details = [
      `Created: ${new Date(campaign.createdAt).toLocaleDateString()}`,
      `Players: ${campaign.players ? campaign.players.length : 0}`,
      `Sessions: ${campaign.sessions ? campaign.sessions.length : 0}`,
      `Status: ${campaign.status || 'Active'}`
    ];

    details.forEach(detail => {
      page.drawText(detail, { x: 50, y: yPosition, size: fontSize });
      yPosition -= 20;
    });

    yPosition -= 20;

    // Campaign description
    if (campaign.description) {
      page.drawText('Description:', {
        x: 50,
        y: yPosition,
        size: fontSize + 2,
        color: rgb(0.3, 0.3, 0.3)
      });
      yPosition -= 25;

      const descriptionLines = this.wrapText(campaign.description, 80);
      descriptionLines.forEach(line => {
        if (yPosition < 50) {
          page = pdfDoc.addPage([595, 842]);
          yPosition = 800;
        }
        page.drawText(line, { x: 50, y: yPosition, size: fontSize });
        yPosition -= 18;
      });
    }

    // Session summaries
    if (campaign.sessions && campaign.sessions.length > 0) {
      yPosition -= 20;
      page.drawText('Session History:', {
        x: 50,
        y: yPosition,
        size: fontSize + 2,
        color: rgb(0.3, 0.3, 0.3)
      });
      yPosition -= 25;

      campaign.sessions.slice(-10).forEach((session, index) => {
        if (yPosition < 100) {
          page = pdfDoc.addPage([595, 842]);
          yPosition = 800;
        }

        page.drawText(`Session ${session.number || index + 1}: ${session.title || 'Untitled'}`, {
          x: 50,
          y: yPosition,
          size: fontSize,
          color: rgb(0.2, 0.2, 0.6)
        });
        yPosition -= 20;

        if (session.summary) {
          const summaryLines = this.wrapText(session.summary, 70);
          summaryLines.slice(0, 3).forEach(line => {
            page.drawText(`  ${line}`, { x: 70, y: yPosition, size: fontSize - 1 });
            yPosition -= 16;
          });
        }
        yPosition -= 10;
      });
    }

    const pdfBytes = await pdfDoc.save();
    return {
      filename: `${campaign.name || 'campaign'}_${campaign._id}.pdf`,
      buffer: Buffer.from(pdfBytes)
    };
  }

  async exportCharacterToPDF(character) {
    const pdfDoc = await PDFDocument.create();
    const page = pdfDoc.addPage([595, 842]);

    const fontSize = 10;
    const titleFontSize = 16;
    let yPosition = 800;

    // Character name and basic info
    page.drawText(character.name || 'Character', {
      x: 50,
      y: yPosition,
      size: titleFontSize,
      color: rgb(0.8, 0.2, 0.2)
    });
    yPosition -= 30;

    const basicInfo = [
      `Race: ${character.race || 'Unknown'}`,
      `Class: ${character.class || 'Unknown'}`,
      `Level: ${character.level || 1}`,
      `Background: ${character.background || 'Unknown'}`
    ];

    basicInfo.forEach(info => {
      page.drawText(info, { x: 50, y: yPosition, size: fontSize });
      yPosition -= 18;
    });

    yPosition -= 20;

    // Ability Scores
    page.drawText('Ability Scores:', {
      x: 50,
      y: yPosition,
      size: fontSize + 2,
      color: rgb(0.3, 0.3, 0.3)
    });
    yPosition -= 25;

    const abilities = character.abilityScores || {
      strength: 10,
      dexterity: 10,
      constitution: 10,
      intelligence: 10,
      wisdom: 10,
      charisma: 10
    };

    Object.entries(abilities).forEach(([ability, score]) => {
      const modifier = Math.floor((score - 10) / 2);
      page.drawText(`${ability.charAt(0).toUpperCase() + ability.slice(1)}: ${score} (${modifier >= 0 ? '+' : ''}${modifier})`, {
        x: 70,
        y: yPosition,
        size: fontSize
      });
      yPosition -= 16;
    });

    // Skills and Features
    if (character.skills || character.features) {
      yPosition -= 20;
      page.drawText('Skills & Features:', {
        x: 50,
        y: yPosition,
        size: fontSize + 2,
        color: rgb(0.3, 0.3, 0.3)
      });
      yPosition -= 25;

      if (character.skills) {
        character.skills.forEach(skill => {
          page.drawText(`• ${skill}`, { x: 70, y: yPosition, size: fontSize });
          yPosition -= 16;
        });
      }

      if (character.features) {
        character.features.forEach(feature => {
          page.drawText(`• ${feature.name}: ${feature.description}`, { x: 70, y: yPosition, size: fontSize });
          yPosition -= 16;
        });
      }
    }

    // Equipment
    if (character.equipment && character.equipment.length > 0) {
      yPosition -= 20;
      page.drawText('Equipment:', {
        x: 50,
        y: yPosition,
        size: fontSize + 2,
        color: rgb(0.3, 0.3, 0.3)
      });
      yPosition -= 25;

      character.equipment.forEach(item => {
        page.drawText(`• ${item.name} ${item.quantity ? `(x${item.quantity})` : ''}`, {
          x: 70,
          y: yPosition,
          size: fontSize
        });
        yPosition -= 16;
      });
    }

    const pdfBytes = await pdfDoc.save();
    return {
      filename: `${character.name || 'character'}_${character._id}.pdf`,
      buffer: Buffer.from(pdfBytes)
    };
  }

  wrapText(text, maxCharsPerLine) {
    const words = text.split(' ');
    const lines = [];
    let currentLine = '';

    words.forEach(word => {
      if ((currentLine + word).length <= maxCharsPerLine) {
        currentLine += (currentLine ? ' ' : '') + word;
      } else {
        if (currentLine) lines.push(currentLine);
        currentLine = word;
      }
    });

    if (currentLine) lines.push(currentLine);
    return lines;
  }

  async uploadToS3(filePath, s3Key) {
    if (!this.s3) return null;

    try {
      const fileContent = await fs.readFile(filePath);
      
      const params = {
        Bucket: process.env.AWS_S3_BUCKET || 'dmlog-backups',
        Key: s3Key,
        Body: fileContent,
        ContentType: 'application/zip',
        ServerSideEncryption: 'AES256'
      };

      const result = await this.s3.upload(params).promise();
      return result.Location;
    } catch (error) {
      console.error('S3 upload failed:', error);
      throw error;
    }
  }

  async restoreFromBackup(backupPath, options = {}) {
    try {
      const { overwrite = false, selectiveTables = [] } = options;
      
      // Extract backup
      const extractPath = path.join(this.backupPath, 'restore_temp');
      await fs.mkdir(extractPath, { recursive: true });
      
      // Read backup data
      const backupData = JSON.parse(await fs.readFile(path.join(extractPath, 'backup.json'), 'utf-8'));
      
      const restoration = {
        campaigns: 0,
        characters: 0,
        userSettings: 0,
        errors: []
      };

      // Restore campaigns
      if (backupData.campaigns && (selectiveTables.length === 0 || selectiveTables.includes('campaigns'))) {
        for (const campaign of backupData.campaigns) {
          try {
            if (overwrite) {
              await mongoose.model('Campaign').replaceOne(
                { _id: campaign._id },
                campaign,
                { upsert: true }
              );
            } else {
              const existing = await mongoose.model('Campaign').findById(campaign._id);
              if (!existing) {
                await mongoose.model('Campaign').create(campaign);
              }
            }
            restoration.campaigns++;
          } catch (error) {
            restoration.errors.push(`Campaign ${campaign.name}: ${error.message}`);
          }
        }
      }

      // Restore characters
      if (backupData.characters && (selectiveTables.length === 0 || selectiveTables.includes('characters'))) {
        for (const character of backupData.characters) {
          try {
            if (overwrite) {
              await mongoose.model('Character').replaceOne(
                { _id: character._id },
                character,
                { upsert: true }
              );
            } else {
              const existing = await mongoose.model('Character').findById(character._id);
              if (!existing) {
                await mongoose.model('Character').create(character);
              }
            }
            restoration.characters++;
          } catch (error) {
            restoration.errors.push(`Character ${character.name}: ${error.message}`);
          }
        }
      }

      // Clean up temporary files
      await fs.rmdir(extractPath, { recursive: true });

      return restoration;
    } catch (error) {
      console.error('Restore failed:', error);
      throw error;
    }
  }

  async getBackupsList() {
    try {
      const files = await fs.readdir(this.backupPath);
      const backups = [];

      for (const file of files) {
        if (file.endsWith('.zip')) {
          const filePath = path.join(this.backupPath, file);
          const stats = await fs.stat(filePath);
          
          backups.push({
            filename: file,
            size: stats.size,
            created: stats.birthtime,
            modified: stats.mtime,
            type: file.includes('daily') ? 'daily' : 
                  file.includes('weekly') ? 'weekly' : 
                  file.includes('archive') ? 'archive' : 'manual'
          });
        }
      }

      return backups.sort((a, b) => b.created - a.created);
    } catch (error) {
      console.error('Failed to get backups list:', error);
      return [];
    }
  }

  async cleanupOldBackups(type, keepCount) {
    try {
      const files = await fs.readdir(this.backupPath);
      const backupFiles = files
        .filter(file => file.includes(type) && file.endsWith('.zip'))
        .map(file => ({
          name: file,
          path: path.join(this.backupPath, file),
          stats: null
        }));

      // Get file stats
      for (const backup of backupFiles) {
        backup.stats = await fs.stat(backup.path);
      }

      // Sort by creation time (newest first)
      backupFiles.sort((a, b) => b.stats.birthtime - a.stats.birthtime);

      // Delete old backups
      const toDelete = backupFiles.slice(keepCount);
      for (const backup of toDelete) {
        await fs.unlink(backup.path);
      }

      return {
        cleaned: toDelete.length,
        remaining: backupFiles.length - toDelete.length
      };
    } catch (error) {
      console.error('Backup cleanup failed:', error);
      throw error;
    }
  }

  async getFileSize(filePath) {
    try {
      const stats = await fs.stat(filePath);
      return stats.size;
    } catch (error) {
      return 0;
    }
  }

  // Database query helpers
  async getRecentCampaigns(days) {
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    try {
      return await mongoose.model('Campaign').find({
        $or: [
          { updatedAt: { $gte: cutoff } },
          { createdAt: { $gte: cutoff } }
        ]
      }).lean();
    } catch (error) {
      console.warn('Could not fetch recent campaigns:', error.message);
      return [];
    }
  }

  async getRecentCharacters(days) {
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    try {
      return await mongoose.model('Character').find({
        $or: [
          { updatedAt: { $gte: cutoff } },
          { createdAt: { $gte: cutoff } }
        ]
      }).lean();
    } catch (error) {
      console.warn('Could not fetch recent characters:', error.message);
      return [];
    }
  }

  async getAllCampaigns() {
    try {
      return await mongoose.model('Campaign').find({}).lean();
    } catch (error) {
      console.warn('Could not fetch all campaigns:', error.message);
      return [];
    }
  }

  async getAllCharacters() {
    try {
      return await mongoose.model('Character').find({}).lean();
    } catch (error) {
      console.warn('Could not fetch all characters:', error.message);
      return [];
    }
  }

  async getUserSettings() {
    try {
      return await mongoose.model('User').find({}).select('-password').lean();
    } catch (error) {
      console.warn('Could not fetch user settings:', error.message);
      return [];
    }
  }

  async getMarketplaceData() {
    try {
      return await mongoose.model('MarketplaceItem').find({}).lean();
    } catch (error) {
      console.warn('Could not fetch marketplace data:', error.message);
      return [];
    }
  }

  async getAllData() {
    return {
      campaigns: await this.getAllCampaigns(),
      characters: await this.getAllCharacters(),
      users: await this.getUserSettings(),
      marketplace: await this.getMarketplaceData()
    };
  }
}

export default BackupService;