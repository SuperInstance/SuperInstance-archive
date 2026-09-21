const QRCode = require('qrcode');
const logger = require('../config/logger');
const path = require('path');
const fs = require('fs').promises;

class QRCodeService {
  constructor() {
    this.baseUrl = process.env.QR_CODE_BASE_URL || 'https://inventory.activelog.com';
    this.defaultSize = parseInt(process.env.QR_CODE_SIZE) || 200;
    this.defaultFormat = process.env.QR_CODE_FORMAT || 'png';
    this.outputDir = path.join(process.cwd(), 'public', 'qr-codes');
    
    this.initializeOutputDirectory();
  }

  async initializeOutputDirectory() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
    } catch (error) {
      logger.error('Error creating QR code directory:', error);
    }
  }

  /**
   * Generate QR code for inventory item
   */
  async generateInventoryQR(locationId, itemId, options = {}) {
    try {
      const qrData = {
        type: 'inventory_item',
        locationId,
        itemId,
        url: `${this.baseUrl}/inventory/${locationId}/${itemId}`,
        timestamp: new Date().toISOString()
      };

      const qrString = JSON.stringify(qrData);
      const fileName = `inventory_${locationId}_${itemId}.${this.defaultFormat}`;
      const filePath = path.join(this.outputDir, fileName);

      const qrOptions = {
        width: options.size || this.defaultSize,
        margin: options.margin || 2,
        color: {
          dark: options.darkColor || '#000000',
          light: options.lightColor || '#FFFFFF'
        }
      };

      await QRCode.toFile(filePath, qrString, qrOptions);

      const result = {
        qrCodeId: `inv_${locationId}_${itemId}`,
        fileName,
        filePath,
        url: `${this.baseUrl}/qr-codes/${fileName}`,
        data: qrData,
        generatedAt: new Date().toISOString()
      };

      logger.logInventoryEvent('qr_code_generated', locationId, itemId, {
        qrCodeId: result.qrCodeId,
        fileName: result.fileName
      });

      return result;
    } catch (error) {
      logger.error('Error generating inventory QR code:', error);
      throw error;
    }
  }

  /**
   * Generate QR code for pickup
   */
  async generatePickupQR(pickupId, pickupData, options = {}) {
    try {
      const qrData = {
        type: 'pickup',
        pickupId,
        locationId: pickupData.locationId,
        customerId: pickupData.customerId,
        items: pickupData.items,
        url: `${this.baseUrl}/pickup/${pickupId}`,
        scheduledTime: pickupData.scheduledTime,
        timestamp: new Date().toISOString()
      };

      const qrString = JSON.stringify(qrData);
      const fileName = `pickup_${pickupId}.${this.defaultFormat}`;
      const filePath = path.join(this.outputDir, fileName);

      const qrOptions = {
        width: options.size || this.defaultSize,
        margin: options.margin || 2,
        color: {
          dark: options.darkColor || '#000000',
          light: options.lightColor || '#FFFFFF'
        }
      };

      await QRCode.toFile(filePath, qrString, qrOptions);

      const result = {
        qrCodeId: `pickup_${pickupId}`,
        fileName,
        filePath,
        url: `${this.baseUrl}/qr-codes/${fileName}`,
        data: qrData,
        generatedAt: new Date().toISOString()
      };

      logger.logPickupEvent('pickup_qr_generated', pickupId, {
        qrCodeId: result.qrCodeId,
        fileName: result.fileName,
        locationId: pickupData.locationId
      });

      return result;
    } catch (error) {
      logger.error('Error generating pickup QR code:', error);
      throw error;
    }
  }

  /**
   * Generate QR code as base64 string
   */
  async generateQRAsBase64(data, options = {}) {
    try {
      const qrOptions = {
        width: options.size || this.defaultSize,
        margin: options.margin || 2,
        color: {
          dark: options.darkColor || '#000000',
          light: options.lightColor || '#FFFFFF'
        }
      };

      const qrString = typeof data === 'string' ? data : JSON.stringify(data);
      const base64 = await QRCode.toDataURL(qrString, qrOptions);

      return {
        base64,
        data: qrString,
        generatedAt: new Date().toISOString()
      };
    } catch (error) {
      logger.error('Error generating QR code as base64:', error);
      throw error;
    }
  }

  /**
   * Batch generate QR codes for multiple items
   */
  async batchGenerateInventoryQRs(locationId, itemIds, options = {}) {
    try {
      const results = [];
      
      for (const itemId of itemIds) {
        try {
          const qrResult = await this.generateInventoryQR(locationId, itemId, options);
          results.push({ success: true, itemId, qrResult });
        } catch (error) {
          results.push({ success: false, itemId, error: error.message });
        }
      }

      logger.logInventoryEvent('batch_qr_generation', locationId, 'batch', {
        totalItems: itemIds.length,
        successCount: results.filter(r => r.success).length,
        errorCount: results.filter(r => !r.success).length
      });

      return {
        locationId,
        totalItems: itemIds.length,
        results,
        generatedAt: new Date().toISOString()
      };
    } catch (error) {
      logger.error('Error in batch QR generation:', error);
      throw error;
    }
  }

  /**
   * Decode QR code data
   */
  decodeQRData(qrString) {
    try {
      const data = JSON.parse(qrString);
      return {
        success: true,
        data,
        type: data.type,
        decodedAt: new Date().toISOString()
      };
    } catch (error) {
      return {
        success: false,
        error: 'Invalid QR code format',
        rawData: qrString
      };
    }
  }
}

module.exports = new QRCodeService();