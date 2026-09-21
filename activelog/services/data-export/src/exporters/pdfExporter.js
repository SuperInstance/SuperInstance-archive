const PDFDocument = require('pdfkit');
const fs = require('fs-extra');
const path = require('path');
const moment = require('moment');
const sharp = require('sharp');
const logger = require('../utils/logger');

class PDFExporter {
  constructor(options = {}) {
    this.options = {
      pageSize: options.pageSize || 'A4',
      margins: options.margins || { top: 50, bottom: 50, left: 50, right: 50 },
      font: options.font || 'Helvetica',
      preserveMetadata: options.preserveMetadata !== false,
      includeTimestamps: options.includeTimestamps !== false,
      watermark: options.watermark || null,
      ...options
    };
  }

  async exportToPDF(data, outputPath, metadata = {}) {
    try {
      const doc = new PDFDocument({
        size: this.options.pageSize,
        margins: this.options.margins,
        info: this.buildPDFInfo(metadata)
      });

      const stream = fs.createWriteStream(outputPath);
      doc.pipe(stream);

      if (this.options.watermark) {
        this.addWatermark(doc, this.options.watermark);
      }

      await this.generateContent(doc, data, metadata);

      doc.end();

      return new Promise((resolve, reject) => {
        stream.on('finish', () => {
          logger.info(`PDF exported successfully: ${outputPath}`);
          resolve({
            success: true,
            outputPath,
            fileSize: fs.statSync(outputPath).size,
            pageCount: doc._pageBuffer.length
          });
        });
        stream.on('error', reject);
      });
    } catch (error) {
      logger.error('PDF export failed:', error);
      throw error;
    }
  }

  buildPDFInfo(metadata) {
    const info = {
      Title: metadata.title || 'Data Export',
      Author: metadata.author || 'ActiveLog Export Service',
      Subject: metadata.subject || 'Exported Data',
      Creator: 'ActiveLog Data Export Service',
      Producer: 'ActiveLog PDF Exporter',
      CreationDate: new Date(),
      ModDate: new Date()
    };

    if (this.options.preserveMetadata && metadata.originalMetadata) {
      Object.assign(info, metadata.originalMetadata);
    }

    return info;
  }

  async generateContent(doc, data, metadata) {
    this.addHeader(doc, metadata);

    if (Array.isArray(data)) {
      for (const item of data) {
        await this.addDataItem(doc, item);
      }
    } else if (typeof data === 'object') {
      await this.addDataObject(doc, data);
    } else {
      doc.text(String(data), { align: 'left' });
    }

    this.addFooter(doc, metadata);
  }

  addHeader(doc, metadata) {
    doc.fontSize(20)
       .font('Helvetica-Bold')
       .text(metadata.title || 'Data Export', { align: 'center' });

    if (metadata.subtitle) {
      doc.fontSize(14)
         .font('Helvetica')
         .text(metadata.subtitle, { align: 'center' });
    }

    if (this.options.includeTimestamps) {
      doc.fontSize(10)
         .text(`Generated: ${moment().format('YYYY-MM-DD HH:mm:ss')}`, { align: 'right' });
    }

    doc.moveDown(2);
  }

  async addDataItem(doc, item) {
    if (item.type === 'text') {
      this.addTextContent(doc, item);
    } else if (item.type === 'image') {
      await this.addImageContent(doc, item);
    } else if (item.type === 'table') {
      this.addTableContent(doc, item);
    } else if (item.type === 'metadata') {
      this.addMetadataContent(doc, item);
    } else {
      this.addGenericContent(doc, item);
    }
  }

  addTextContent(doc, item) {
    doc.fontSize(item.fontSize || 12)
       .font(item.font || this.options.font)
       .text(item.content, {
         align: item.align || 'left',
         width: item.width || undefined
       });
    
    if (item.spacing) {
      doc.moveDown(item.spacing);
    }
  }

  async addImageContent(doc, item) {
    try {
      let imagePath = item.path;
      
      if (item.resize) {
        imagePath = await this.resizeImage(item.path, item.resize);
      }

      const imageOptions = {
        fit: item.fit || [400, 300],
        align: item.align || 'center'
      };

      if (item.caption) {
        doc.image(imagePath, imageOptions);
        doc.fontSize(10)
           .text(item.caption, { align: 'center' });
      } else {
        doc.image(imagePath, imageOptions);
      }

      if (this.options.preserveMetadata && item.metadata) {
        this.addImageMetadata(doc, item.metadata);
      }

      doc.moveDown();
    } catch (error) {
      logger.error(`Failed to add image: ${item.path}`, error);
      doc.text(`[Image not available: ${item.path}]`, { align: 'center' });
    }
  }

  addTableContent(doc, item) {
    const table = item.data;
    const cellPadding = 5;
    const tableWidth = doc.page.width - doc.page.margins.left - doc.page.margins.right;
    const colWidth = tableWidth / table.headers.length;

    doc.fontSize(10);

    // Headers
    const headerY = doc.y;
    table.headers.forEach((header, index) => {
      const x = doc.page.margins.left + (index * colWidth);
      doc.rect(x, headerY, colWidth, 20)
         .stroke()
         .text(header, x + cellPadding, headerY + cellPadding, {
           width: colWidth - 2 * cellPadding,
           height: 20 - 2 * cellPadding
         });
    });

    doc.y = headerY + 20;

    // Rows
    table.rows.forEach(row => {
      const rowY = doc.y;
      row.forEach((cell, index) => {
        const x = doc.page.margins.left + (index * colWidth);
        doc.rect(x, rowY, colWidth, 20)
           .stroke()
           .text(String(cell), x + cellPadding, rowY + cellPadding, {
             width: colWidth - 2 * cellPadding,
             height: 20 - 2 * cellPadding
           });
      });
      doc.y = rowY + 20;
    });

    doc.moveDown();
  }

  addMetadataContent(doc, item) {
    doc.fontSize(12)
       .font('Helvetica-Bold')
       .text('Metadata:', { underline: true });

    doc.fontSize(10)
       .font('Helvetica');

    Object.entries(item.data).forEach(([key, value]) => {
      doc.text(`${key}: ${value}`);
    });

    doc.moveDown();
  }

  addGenericContent(doc, item) {
    if (typeof item === 'object') {
      doc.text(JSON.stringify(item, null, 2));
    } else {
      doc.text(String(item));
    }
    doc.moveDown();
  }

  async addDataObject(doc, data) {
    for (const [key, value] of Object.entries(data)) {
      doc.fontSize(14)
         .font('Helvetica-Bold')
         .text(key, { underline: true });

      if (Array.isArray(value)) {
        for (const item of value) {
          await this.addDataItem(doc, item);
        }
      } else if (typeof value === 'object') {
        doc.fontSize(10)
           .font('Helvetica')
           .text(JSON.stringify(value, null, 2));
      } else {
        doc.fontSize(12)
           .font('Helvetica')
           .text(String(value));
      }

      doc.moveDown();
    }
  }

  addFooter(doc, metadata) {
    const pages = doc.bufferedPageRange();
    for (let i = 0; i < pages.count; i++) {
      doc.switchToPage(i);
      
      const bottom = doc.page.height - doc.page.margins.bottom;
      doc.fontSize(8)
         .text(`Page ${i + 1} of ${pages.count}`, 
               doc.page.margins.left, 
               bottom + 10, 
               { align: 'center' });

      if (metadata.footer) {
        doc.text(metadata.footer, 
                doc.page.margins.left, 
                bottom + 25, 
                { align: 'center' });
      }
    }
  }

  addWatermark(doc, watermark) {
    doc.save()
       .opacity(0.1)
       .fontSize(50)
       .rotate(45, { origin: [doc.page.width / 2, doc.page.height / 2] })
       .text(watermark, doc.page.width / 2 - 100, doc.page.height / 2, {
         align: 'center'
       })
       .restore();
  }

  async resizeImage(imagePath, options) {
    const outputPath = path.join(
      path.dirname(imagePath),
      `resized_${path.basename(imagePath)}`
    );

    await sharp(imagePath)
      .resize(options.width, options.height, {
        fit: options.fit || 'inside',
        withoutEnlargement: true
      })
      .toFile(outputPath);

    return outputPath;
  }

  addImageMetadata(doc, metadata) {
    doc.fontSize(8)
       .text(`EXIF: ${JSON.stringify(metadata, null, 1)}`, { 
         align: 'left',
         color: 'gray'
       });
  }

  async exportGDPRCompliantPDF(userData, outputPath, options = {}) {
    const gdprMetadata = {
      title: 'Personal Data Export',
      subject: 'GDPR Article 20 - Right to Data Portability',
      author: options.dataController || 'Data Controller',
      footer: 'This export was generated in compliance with GDPR Article 20'
    };

    const structuredData = this.structureGDPRData(userData);
    
    return await this.exportToPDF(structuredData, outputPath, gdprMetadata);
  }

  structureGDPRData(userData) {
    return [
      {
        type: 'text',
        content: 'PERSONAL DATA EXPORT',
        fontSize: 20,
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
        content: 'This document contains all personal data processed by our service in accordance with GDPR Article 20.',
        fontSize: 10,
        spacing: 2
      },
      {
        type: 'metadata',
        data: {
          'Data Subject': userData.name || 'N/A',
          'Email': userData.email || 'N/A',
          'User ID': userData.id || 'N/A',
          'Account Created': userData.createdAt || 'N/A',
          'Last Login': userData.lastLogin || 'N/A'
        }
      },
      ...this.convertUserDataToItems(userData)
    ];
  }

  convertUserDataToItems(userData) {
    const items = [];
    
    Object.entries(userData).forEach(([key, value]) => {
      if (key !== 'name' && key !== 'email' && key !== 'id' && key !== 'createdAt' && key !== 'lastLogin') {
        items.push({
          type: 'text',
          content: `${key.toUpperCase()}`,
          fontSize: 14,
          font: 'Helvetica-Bold',
          spacing: 1
        });

        if (Array.isArray(value)) {
          value.forEach(item => {
            items.push({
              type: 'text',
              content: typeof item === 'object' ? JSON.stringify(item, null, 2) : String(item),
              fontSize: 10
            });
          });
        } else if (typeof value === 'object') {
          items.push({
            type: 'text',
            content: JSON.stringify(value, null, 2),
            fontSize: 10
          });
        } else {
          items.push({
            type: 'text',
            content: String(value),
            fontSize: 12
          });
        }
        
        items.push({ type: 'text', content: '', spacing: 1 });
      }
    });

    return items;
  }
}

module.exports = PDFExporter;