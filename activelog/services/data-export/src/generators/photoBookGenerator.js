const PDFDocument = require('pdfkit');
const fs = require('fs-extra');
const path = require('path');
const sharp = require('sharp');
const moment = require('moment');
const exifReader = require('exif-reader');
const logger = require('../utils/logger');

class PhotoBookGenerator {
  constructor(options = {}) {
    this.options = {
      format: options.format || 'A4', // A4, Letter, Square
      orientation: options.orientation || 'portrait', // portrait, landscape
      theme: options.theme || 'classic', // classic, modern, minimal
      layout: options.layout || 'auto', // auto, grid, magazine, scrapbook
      imagesPerPage: options.imagesPerPage || 4,
      includeMetadata: options.includeMetadata !== false,
      includeTimestamps: options.includeTimestamps !== false,
      includeCaptions: options.includeCaptions !== false,
      imageQuality: options.imageQuality || 300, // DPI
      margins: options.margins || { top: 72, bottom: 72, left: 72, right: 72 },
      fontSize: options.fontSize || 10,
      titleFontSize: options.titleFontSize || 24,
      captionFontSize: options.captionFontSize || 8,
      ...options
    };

    this.pageSize = this.getPageSize();
    this.themes = this.getThemes();
  }

  async createPhotoBook(photos, outputPath, metadata = {}) {
    try {
      const processedPhotos = await this.processPhotos(photos);
      const albumData = this.organizePhotos(processedPhotos, metadata);
      
      const doc = new PDFDocument({
        size: this.pageSize,
        margins: this.options.margins,
        info: this.buildBookInfo(metadata)
      });

      const stream = fs.createWriteStream(outputPath);
      doc.pipe(stream);

      await this.generateCoverPage(doc, albumData);
      await this.generatePhotoPages(doc, albumData);
      
      if (this.options.includeMetadata) {
        await this.generateMetadataPage(doc, albumData);
      }

      doc.end();

      return new Promise((resolve, reject) => {
        stream.on('finish', () => {
          const stats = fs.statSync(outputPath);
          logger.info(`Photo book created: ${outputPath} (${this.formatBytes(stats.size)})`);
          resolve({
            success: true,
            outputPath,
            fileSize: stats.size,
            pageCount: doc._pageBuffer.length,
            photoCount: processedPhotos.length
          });
        });
        stream.on('error', reject);
      });
    } catch (error) {
      logger.error('Photo book creation failed:', error);
      throw error;
    }
  }

  async processPhotos(photos) {
    const processed = [];
    
    for (const photo of photos) {
      try {
        const photoData = await this.processPhoto(photo);
        processed.push(photoData);
      } catch (error) {
        logger.warn(`Failed to process photo: ${photo.path || photo.src}`, error);
      }
    }

    return processed;
  }

  async processPhoto(photo) {
    const photoPath = photo.path || photo.src;
    const metadata = await this.extractPhotoMetadata(photoPath);
    
    // Create thumbnail if needed
    const thumbnailPath = await this.createThumbnail(photoPath);
    
    // Extract colors for theme matching
    const dominantColors = await this.extractDominantColors(photoPath);

    return {
      originalPath: photoPath,
      thumbnailPath,
      filename: path.basename(photoPath),
      caption: photo.caption || '',
      location: photo.location || metadata.location || '',
      dateTaken: photo.dateTaken || metadata.dateTaken || '',
      metadata,
      dominantColors,
      dimensions: metadata.dimensions || {},
      orientation: this.getImageOrientation(metadata.dimensions)
    };
  }

  async extractPhotoMetadata(photoPath) {
    try {
      const imageBuffer = await fs.readFile(photoPath);
      const image = sharp(imageBuffer);
      const sharpMetadata = await image.metadata();
      
      let exifData = {};
      if (sharpMetadata.exif) {
        try {
          exifData = exifReader(sharpMetadata.exif);
        } catch (err) {
          logger.warn(`Failed to read EXIF data for ${photoPath}:`, err);
        }
      }

      return {
        dimensions: {
          width: sharpMetadata.width,
          height: sharpMetadata.height
        },
        format: sharpMetadata.format,
        fileSize: (await fs.stat(photoPath)).size,
        dateTaken: this.extractDateFromExif(exifData),
        location: this.extractLocationFromExif(exifData),
        camera: this.extractCameraFromExif(exifData),
        settings: this.extractCameraSettings(exifData),
        exif: exifData
      };
    } catch (error) {
      logger.error(`Failed to extract metadata from ${photoPath}:`, error);
      return {};
    }
  }

  async createThumbnail(photoPath, size = 400) {
    const thumbnailDir = path.join(path.dirname(photoPath), '.thumbnails');
    await fs.ensureDir(thumbnailDir);
    
    const filename = path.basename(photoPath, path.extname(photoPath));
    const thumbnailPath = path.join(thumbnailDir, `${filename}_thumb.jpg`);
    
    if (await fs.pathExists(thumbnailPath)) {
      return thumbnailPath;
    }

    await sharp(photoPath)
      .resize(size, size, { 
        fit: 'inside',
        withoutEnlargement: true 
      })
      .jpeg({ quality: 85 })
      .toFile(thumbnailPath);

    return thumbnailPath;
  }

  async extractDominantColors(photoPath, numColors = 5) {
    try {
      const { data, info } = await sharp(photoPath)
        .resize(100, 100, { fit: 'cover' })
        .raw()
        .toBuffer({ resolveWithObject: true });

      const colors = this.analyzeDominantColors(data, info, numColors);
      return colors;
    } catch (error) {
      logger.warn(`Failed to extract colors from ${photoPath}:`, error);
      return [];
    }
  }

  analyzeDominantColors(buffer, info, numColors) {
    const colorMap = new Map();
    const { width, height, channels } = info;

    for (let i = 0; i < buffer.length; i += channels) {
      const r = buffer[i];
      const g = buffer[i + 1];
      const b = buffer[i + 2];
      
      const colorKey = `${Math.floor(r/32)*32},${Math.floor(g/32)*32},${Math.floor(b/32)*32}`;
      colorMap.set(colorKey, (colorMap.get(colorKey) || 0) + 1);
    }

    const sortedColors = Array.from(colorMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, numColors)
      .map(([color, count]) => {
        const [r, g, b] = color.split(',').map(Number);
        return { r, g, b, count, hex: this.rgbToHex(r, g, b) };
      });

    return sortedColors;
  }

  organizePhotos(photos, metadata) {
    let organized = [...photos];

    // Sort by date if available
    organized.sort((a, b) => {
      const dateA = new Date(a.dateTaken || 0);
      const dateB = new Date(b.dateTaken || 0);
      return dateA - dateB;
    });

    // Group by time periods or events
    const groups = this.groupPhotosByPeriod(organized);

    return {
      title: metadata.title || 'Photo Album',
      subtitle: metadata.subtitle || '',
      description: metadata.description || '',
      author: metadata.author || '',
      createdAt: moment().format('YYYY-MM-DD'),
      photos: organized,
      groups,
      totalPhotos: photos.length,
      dateRange: this.getDateRange(photos),
      theme: this.selectTheme(photos)
    };
  }

  groupPhotosByPeriod(photos) {
    const groups = [];
    let currentGroup = null;
    
    for (const photo of photos) {
      const photoDate = moment(photo.dateTaken);
      
      if (!currentGroup || 
          !photoDate.isValid() ||
          photoDate.diff(moment(currentGroup.endDate), 'days') > 7) {
        
        if (currentGroup) {
          groups.push(currentGroup);
        }
        
        currentGroup = {
          id: groups.length,
          startDate: photoDate.isValid() ? photoDate.format('YYYY-MM-DD') : null,
          endDate: photoDate.isValid() ? photoDate.format('YYYY-MM-DD') : null,
          photos: [photo],
          title: this.generateGroupTitle(photoDate, photo)
        };
      } else {
        currentGroup.photos.push(photo);
        currentGroup.endDate = photoDate.format('YYYY-MM-DD');
      }
    }
    
    if (currentGroup) {
      groups.push(currentGroup);
    }
    
    return groups;
  }

  async generateCoverPage(doc, albumData) {
    const theme = this.themes[albumData.theme] || this.themes.classic;
    
    // Background
    if (theme.coverBackground) {
      doc.rect(0, 0, doc.page.width, doc.page.height)
         .fill(theme.coverBackground);
    }

    // Title
    doc.fontSize(this.options.titleFontSize)
       .font('Helvetica-Bold')
       .fillColor(theme.titleColor || '#000000')
       .text(albumData.title, {
         align: 'center',
         valign: 'center'
       });

    // Subtitle
    if (albumData.subtitle) {
      doc.moveDown(1)
         .fontSize(this.options.titleFontSize * 0.6)
         .font('Helvetica')
         .text(albumData.subtitle, { align: 'center' });
    }

    // Cover photo if available
    if (albumData.photos.length > 0) {
      const coverPhoto = albumData.photos[0];
      const coverImageSize = Math.min(doc.page.width * 0.6, doc.page.height * 0.4);
      
      try {
        doc.image(coverPhoto.originalPath, {
          fit: [coverImageSize, coverImageSize],
          align: 'center',
          valign: 'center'
        });
      } catch (error) {
        logger.warn('Failed to add cover photo:', error);
      }
    }

    // Album info
    doc.moveDown(2)
       .fontSize(this.options.fontSize)
       .text(`${albumData.totalPhotos} photos`, { align: 'center' });

    if (albumData.dateRange) {
      doc.text(albumData.dateRange, { align: 'center' });
    }

    if (albumData.author) {
      doc.text(`Created by ${albumData.author}`, { align: 'center' });
    }

    doc.addPage();
  }

  async generatePhotoPages(doc, albumData) {
    const layoutHandler = this.getLayoutHandler();
    
    for (const group of albumData.groups) {
      await this.generateGroupPage(doc, group, albumData);
      await layoutHandler(doc, group.photos, albumData);
    }
  }

  async generateGroupPage(doc, group, albumData) {
    if (!group.title) return;

    const theme = this.themes[albumData.theme] || this.themes.classic;
    
    doc.fontSize(18)
       .font('Helvetica-Bold')
       .fillColor(theme.sectionColor || '#333333')
       .text(group.title, { align: 'center' });

    if (group.startDate && group.endDate) {
      doc.moveDown(0.5)
         .fontSize(12)
         .font('Helvetica')
         .text(`${group.startDate} - ${group.endDate}`, { align: 'center' });
    }

    doc.moveDown(1)
       .fontSize(10)
       .text(`${group.photos.length} photos`, { align: 'center' });

    doc.addPage();
  }

  getLayoutHandler() {
    switch (this.options.layout) {
      case 'grid':
        return this.generateGridLayout.bind(this);
      case 'magazine':
        return this.generateMagazineLayout.bind(this);
      case 'scrapbook':
        return this.generateScrapbookLayout.bind(this);
      default:
        return this.generateAutoLayout.bind(this);
    }
  }

  async generateGridLayout(doc, photos, albumData) {
    const cols = Math.ceil(Math.sqrt(this.options.imagesPerPage));
    const rows = Math.ceil(this.options.imagesPerPage / cols);
    
    const availableWidth = doc.page.width - this.options.margins.left - this.options.margins.right;
    const availableHeight = doc.page.height - this.options.margins.top - this.options.margins.bottom;
    
    const cellWidth = availableWidth / cols;
    const cellHeight = availableHeight / rows;
    const padding = 10;

    let photoIndex = 0;
    let currentPage = 0;

    while (photoIndex < photos.length) {
      if (currentPage > 0) {
        doc.addPage();
      }

      for (let row = 0; row < rows && photoIndex < photos.length; row++) {
        for (let col = 0; col < cols && photoIndex < photos.length; col++) {
          const photo = photos[photoIndex];
          const x = this.options.margins.left + (col * cellWidth) + padding;
          const y = this.options.margins.top + (row * cellHeight) + padding;
          const imageWidth = cellWidth - (padding * 2);
          const imageHeight = cellHeight - (padding * 2) - 30; // Space for caption

          try {
            doc.image(photo.originalPath, x, y, {
              fit: [imageWidth, imageHeight],
              align: 'center'
            });

            if (this.options.includeCaptions && photo.caption) {
              doc.fontSize(this.options.captionFontSize)
                 .text(photo.caption, x, y + imageHeight + 5, {
                   width: imageWidth,
                   align: 'center'
                 });
            }
          } catch (error) {
            logger.warn(`Failed to add photo ${photo.filename}:`, error);
          }

          photoIndex++;
        }
      }

      currentPage++;
    }
  }

  async generateMagazineLayout(doc, photos, albumData) {
    // Magazine-style layout with varying photo sizes
    let photoIndex = 0;

    while (photoIndex < photos.length) {
      if (photoIndex > 0) {
        doc.addPage();
      }

      const layoutPattern = this.getMagazinePattern(this.options.imagesPerPage);
      
      for (const layout of layoutPattern) {
        if (photoIndex >= photos.length) break;

        const photo = photos[photoIndex];
        const x = this.options.margins.left + (layout.x * (doc.page.width - this.options.margins.left - this.options.margins.right));
        const y = this.options.margins.top + (layout.y * (doc.page.height - this.options.margins.top - this.options.margins.bottom));
        const width = layout.width * (doc.page.width - this.options.margins.left - this.options.margins.right);
        const height = layout.height * (doc.page.height - this.options.margins.top - this.options.margins.bottom);

        try {
          doc.image(photo.originalPath, x, y, {
            fit: [width, height],
            align: 'center'
          });

          if (this.options.includeCaptions && photo.caption) {
            doc.fontSize(this.options.captionFontSize)
               .text(photo.caption, x, y + height + 5, {
                 width: width,
                 align: 'center'
               });
          }
        } catch (error) {
          logger.warn(`Failed to add photo ${photo.filename}:`, error);
        }

        photoIndex++;
      }
    }
  }

  async generateScrapbookLayout(doc, photos, albumData) {
    // Scrapbook-style with decorative elements and varied positioning
    let photoIndex = 0;

    while (photoIndex < photos.length) {
      if (photoIndex > 0) {
        doc.addPage();
      }

      const photosOnPage = Math.min(this.options.imagesPerPage, photos.length - photoIndex);
      
      for (let i = 0; i < photosOnPage; i++) {
        const photo = photos[photoIndex + i];
        const position = this.getScrapbookPosition(i, photosOnPage);
        
        // Add photo with slight rotation for scrapbook effect
        doc.save();
        doc.rotate(position.rotation, { origin: [position.x + position.width/2, position.y + position.height/2] });
        
        try {
          doc.image(photo.originalPath, position.x, position.y, {
            fit: [position.width, position.height]
          });
        } catch (error) {
          logger.warn(`Failed to add photo ${photo.filename}:`, error);
        }
        
        doc.restore();

        // Add decorative border
        this.addScrapbookBorder(doc, position);

        if (this.options.includeCaptions && photo.caption) {
          doc.fontSize(this.options.captionFontSize)
             .text(photo.caption, position.x, position.y + position.height + 10, {
               width: position.width,
               align: 'center'
             });
        }
      }

      photoIndex += photosOnPage;
    }
  }

  async generateAutoLayout(doc, photos, albumData) {
    // Automatically choose best layout based on photo orientations
    const landscapeCount = photos.filter(p => p.orientation === 'landscape').length;
    const portraitCount = photos.filter(p => p.orientation === 'portrait').length;
    
    if (landscapeCount > portraitCount) {
      return await this.generateMagazineLayout(doc, photos, albumData);
    } else {
      return await this.generateGridLayout(doc, photos, albumData);
    }
  }

  async generateMetadataPage(doc, albumData) {
    doc.addPage();
    
    doc.fontSize(16)
       .font('Helvetica-Bold')
       .text('Photo Information', { align: 'center' });

    doc.moveDown(1)
       .fontSize(10)
       .font('Helvetica');

    for (const photo of albumData.photos) {
      doc.text(`${photo.filename}`, { underline: true });
      
      if (photo.dateTaken) {
        doc.text(`Date: ${photo.dateTaken}`);
      }
      
      if (photo.location) {
        doc.text(`Location: ${photo.location}`);
      }
      
      if (photo.metadata.camera) {
        doc.text(`Camera: ${photo.metadata.camera}`);
      }
      
      if (photo.metadata.settings) {
        doc.text(`Settings: ${photo.metadata.settings}`);
      }
      
      doc.moveDown(0.5);
    }
  }

  getPageSize() {
    const sizes = {
      'A4': [595, 842],
      'Letter': [612, 792],
      'Square': [612, 612]
    };
    
    let size = sizes[this.options.format] || sizes.A4;
    
    if (this.options.orientation === 'landscape') {
      size = [size[1], size[0]];
    }
    
    return size;
  }

  getThemes() {
    return {
      classic: {
        coverBackground: '#ffffff',
        titleColor: '#2c3e50',
        sectionColor: '#34495e',
        accentColor: '#3498db'
      },
      modern: {
        coverBackground: '#2c3e50',
        titleColor: '#ffffff',
        sectionColor: '#ecf0f1',
        accentColor: '#e74c3c'
      },
      minimal: {
        coverBackground: '#ffffff',
        titleColor: '#000000',
        sectionColor: '#666666',
        accentColor: '#cccccc'
      }
    };
  }

  getMagazinePattern(imagesPerPage) {
    const patterns = {
      2: [
        { x: 0, y: 0, width: 0.48, height: 1 },
        { x: 0.52, y: 0, width: 0.48, height: 1 }
      ],
      3: [
        { x: 0, y: 0, width: 0.65, height: 0.6 },
        { x: 0.68, y: 0, width: 0.32, height: 0.3 },
        { x: 0.68, y: 0.35, width: 0.32, height: 0.3 }
      ],
      4: [
        { x: 0, y: 0, width: 0.48, height: 0.48 },
        { x: 0.52, y: 0, width: 0.48, height: 0.48 },
        { x: 0, y: 0.52, width: 0.48, height: 0.48 },
        { x: 0.52, y: 0.52, width: 0.48, height: 0.48 }
      ]
    };
    
    return patterns[imagesPerPage] || patterns[4];
  }

  getScrapbookPosition(index, total) {
    const positions = [
      { x: 50, y: 50, width: 200, height: 150, rotation: -2 },
      { x: 300, y: 80, width: 180, height: 240, rotation: 3 },
      { x: 100, y: 300, width: 220, height: 160, rotation: -1 },
      { x: 350, y: 350, width: 160, height: 200, rotation: 2 }
    ];
    
    return positions[index % positions.length];
  }

  addScrapbookBorder(doc, position) {
    // Add decorative border around photo
    doc.save()
       .strokeColor('#cccccc')
       .lineWidth(2)
       .rect(position.x - 5, position.y - 5, position.width + 10, position.height + 10)
       .stroke()
       .restore();
  }

  buildBookInfo(metadata) {
    return {
      Title: metadata.title || 'Photo Album',
      Author: metadata.author || 'ActiveLog Export Service',
      Subject: 'Photo Book',
      Creator: 'ActiveLog Photo Book Generator',
      Producer: 'ActiveLog Data Export Service',
      CreationDate: new Date(),
      ModDate: new Date()
    };
  }

  extractDateFromExif(exifData) {
    try {
      if (exifData.exif && exifData.exif.DateTimeOriginal) {
        return moment(exifData.exif.DateTimeOriginal, 'YYYY:MM:DD HH:mm:ss').format('YYYY-MM-DD HH:mm:ss');
      }
      if (exifData.exif && exifData.exif.DateTime) {
        return moment(exifData.exif.DateTime, 'YYYY:MM:DD HH:mm:ss').format('YYYY-MM-DD HH:mm:ss');
      }
    } catch (error) {
      logger.warn('Failed to extract date from EXIF:', error);
    }
    return null;
  }

  extractLocationFromExif(exifData) {
    try {
      if (exifData.gps && exifData.gps.GPSLatitude && exifData.gps.GPSLongitude) {
        const lat = this.convertDMSToDD(exifData.gps.GPSLatitude, exifData.gps.GPSLatitudeRef);
        const lon = this.convertDMSToDD(exifData.gps.GPSLongitude, exifData.gps.GPSLongitudeRef);
        return `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
      }
    } catch (error) {
      logger.warn('Failed to extract location from EXIF:', error);
    }
    return null;
  }

  extractCameraFromExif(exifData) {
    try {
      const make = exifData.image?.Make || '';
      const model = exifData.image?.Model || '';
      return make && model ? `${make} ${model}`.trim() : null;
    } catch (error) {
      logger.warn('Failed to extract camera from EXIF:', error);
    }
    return null;
  }

  extractCameraSettings(exifData) {
    try {
      const settings = [];
      
      if (exifData.exif?.ISO) {
        settings.push(`ISO ${exifData.exif.ISO}`);
      }
      
      if (exifData.exif?.FNumber) {
        settings.push(`f/${exifData.exif.FNumber}`);
      }
      
      if (exifData.exif?.ExposureTime) {
        settings.push(`${exifData.exif.ExposureTime}s`);
      }
      
      if (exifData.exif?.FocalLength) {
        settings.push(`${exifData.exif.FocalLength}mm`);
      }
      
      return settings.length > 0 ? settings.join(' • ') : null;
    } catch (error) {
      logger.warn('Failed to extract camera settings from EXIF:', error);
    }
    return null;
  }

  convertDMSToDD(dms, ref) {
    let dd = dms[0] + dms[1]/60 + dms[2]/3600;
    if (ref === 'S' || ref === 'W') dd = dd * -1;
    return dd;
  }

  getImageOrientation(dimensions) {
    if (!dimensions || !dimensions.width || !dimensions.height) {
      return 'unknown';
    }
    return dimensions.width > dimensions.height ? 'landscape' : 'portrait';
  }

  getDateRange(photos) {
    const dates = photos
      .map(p => p.dateTaken)
      .filter(d => d)
      .map(d => new Date(d))
      .sort();

    if (dates.length === 0) return null;
    
    const start = moment(dates[0]).format('YYYY-MM-DD');
    const end = moment(dates[dates.length - 1]).format('YYYY-MM-DD');
    
    return start === end ? start : `${start} to ${end}`;
  }

  selectTheme(photos) {
    // Analyze dominant colors to suggest theme
    const allColors = photos.flatMap(p => p.dominantColors || []);
    const avgBrightness = allColors.reduce((sum, color) => {
      const brightness = (color.r + color.g + color.b) / 3;
      return sum + brightness;
    }, 0) / allColors.length;

    if (avgBrightness > 200) return 'minimal';
    if (avgBrightness < 100) return 'modern';
    return 'classic';
  }

  generateGroupTitle(date, photo) {
    if (!date.isValid()) {
      return photo.location || 'Untitled Collection';
    }
    
    return date.format('MMMM YYYY');
  }

  rgbToHex(r, g, b) {
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }

  formatBytes(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }
}

module.exports = PhotoBookGenerator;