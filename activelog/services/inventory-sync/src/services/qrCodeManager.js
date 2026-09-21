const { v4: uuidv4 } = require('uuid');
const QRCode = require('qrcode');
const sharp = require('sharp');
const fs = require('fs').promises;
const path = require('path');
const logger = require('../config/logger');
const redis = require('../config/redis');

class QRCodeManager {
    constructor(socketIO) {
        this.io = socketIO;
        this.redis = redis.client;
        this.qrCodesPath = path.join(process.cwd(), 'public', 'qr-codes');
        this.qrCodeCache = new Map();
        this.scanHistory = new Map();
        this.qrCodeTypes = {
            ITEM: 'item',
            RESERVATION: 'reservation',
            PICKUP: 'pickup',
            LOCATION: 'location',
            INVENTORY_CHECK: 'inventory_check',
            TRANSFER: 'transfer',
            QUICK_ACTION: 'quick_action'
        };

        this.initializeQRCodeDirectory();
    }

    async initializeQRCodeDirectory() {
        try {
            await fs.mkdir(this.qrCodesPath, { recursive: true });
            logger.info('QR codes directory initialized', { path: this.qrCodesPath });
        } catch (error) {
            logger.error('Failed to initialize QR codes directory', { error: error.message });
        }
    }

    async generateItemQRCode(itemData, options = {}) {
        try {
            const {
                locationId,
                itemId,
                itemName,
                sku,
                currentStock,
                price,
                category,
                includeMetadata = true,
                customSize = 200,
                includeTitle = true,
                logoPath = null
            } = itemData;

            const qrId = uuidv4();
            const timestamp = new Date();

            // Create QR code data payload
            const qrData = {
                type: this.qrCodeTypes.ITEM,
                qrId,
                itemId,
                locationId,
                sku,
                timestamp: timestamp.toISOString(),
                url: `${process.env.BASE_URL || 'http://localhost:8311'}/inventory/item/${locationId}/${itemId}`,
                metadata: includeMetadata ? {
                    itemName,
                    currentStock,
                    price,
                    category,
                    lastUpdated: timestamp.toISOString()
                } : null
            };

            // Generate QR code
            const qrCodeBuffer = await QRCode.toBuffer(JSON.stringify(qrData), {
                type: 'png',
                width: customSize,
                height: customSize,
                margin: 2,
                color: {
                    dark: '#000000',
                    light: '#FFFFFF'
                },
                errorCorrectionLevel: 'M'
            });

            // Create enhanced QR code with title and logo if requested
            let finalBuffer = qrCodeBuffer;

            if (includeTitle || logoPath) {
                finalBuffer = await this.enhanceQRCode(qrCodeBuffer, {
                    title: includeTitle ? itemName || `Item: ${itemId}` : null,
                    subtitle: includeTitle ? `SKU: ${sku}` : null,
                    logoPath,
                    size: customSize
                });
            }

            // Save QR code file
            const filename = `item_${locationId}_${itemId}_${Date.now()}.png`;
            const filepath = path.join(this.qrCodesPath, filename);
            await fs.writeFile(filepath, finalBuffer);

            // Store QR code information
            const qrCodeInfo = {
                qrId,
                type: this.qrCodeTypes.ITEM,
                itemId,
                locationId,
                filename,
                filepath,
                url: `/qr-codes/${filename}`,
                data: qrData,
                createdAt: timestamp.toISOString(),
                scanCount: 0,
                lastScanned: null,
                isActive: true,
                options
            };

            await this.storeQRCodeInfo(qrCodeInfo);

            logger.logInventoryEvent('qr_code_generated', locationId, 'system', {
                qrId,
                itemId,
                type: 'item',
                filename
            });

            return qrCodeInfo;

        } catch (error) {
            logger.error('Failed to generate item QR code', {
                itemData,
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    async generateReservationQRCode(reservationData, options = {}) {
        try {
            const {
                reservationId,
                customerId,
                customerName,
                locationId,
                items,
                expiresAt,
                totalValue,
                customSize = 200,
                includeTitle = true
            } = reservationData;

            const qrId = uuidv4();
            const timestamp = new Date();

            // Create QR code data payload
            const qrData = {
                type: this.qrCodeTypes.RESERVATION,
                qrId,
                reservationId,
                customerId,
                locationId,
                timestamp: timestamp.toISOString(),
                url: `${process.env.BASE_URL || 'http://localhost:8311'}/reservations/${reservationId}`,
                metadata: {
                    customerName,
                    itemCount: items.length,
                    totalValue,
                    expiresAt
                }
            };

            // Generate QR code
            const qrCodeBuffer = await QRCode.toBuffer(JSON.stringify(qrData), {
                type: 'png',
                width: customSize,
                height: customSize,
                margin: 2,
                color: {
                    dark: '#1976d2',
                    light: '#FFFFFF'
                },
                errorCorrectionLevel: 'M'
            });

            // Enhance with reservation details
            let finalBuffer = qrCodeBuffer;

            if (includeTitle) {
                finalBuffer = await this.enhanceQRCode(qrCodeBuffer, {
                    title: `Reservation: ${reservationId.substring(0, 8).toUpperCase()}`,
                    subtitle: customerName,
                    additionalText: `Items: ${items.length} | Expires: ${new Date(expiresAt).toLocaleDateString()}`,
                    size: customSize,
                    titleColor: '#1976d2'
                });
            }

            // Save QR code file
            const filename = `reservation_${reservationId}_${Date.now()}.png`;
            const filepath = path.join(this.qrCodesPath, filename);
            await fs.writeFile(filepath, finalBuffer);

            // Store QR code information
            const qrCodeInfo = {
                qrId,
                type: this.qrCodeTypes.RESERVATION,
                reservationId,
                customerId,
                locationId,
                filename,
                filepath,
                url: `/qr-codes/${filename}`,
                data: qrData,
                createdAt: timestamp.toISOString(),
                scanCount: 0,
                lastScanned: null,
                isActive: true,
                expiresAt,
                options
            };

            await this.storeQRCodeInfo(qrCodeInfo);

            logger.logInventoryEvent('qr_code_generated', locationId, customerId, {
                qrId,
                reservationId,
                type: 'reservation',
                filename
            });

            return qrCodeInfo;

        } catch (error) {
            logger.error('Failed to generate reservation QR code', {
                reservationData,
                error: error.message
            });
            throw error;
        }
    }

    async generatePickupQRCode(pickupData, options = {}) {
        try {
            const {
                pickupId,
                reservationId,
                customerId,
                customerName,
                locationId,
                scheduledDate,
                timeSlot,
                items,
                customSize = 200,
                includeTitle = true
            } = pickupData;

            const qrId = uuidv4();
            const timestamp = new Date();

            // Create QR code data payload
            const qrData = {
                type: this.qrCodeTypes.PICKUP,
                qrId,
                pickupId,
                reservationId,
                customerId,
                locationId,
                timestamp: timestamp.toISOString(),
                url: `${process.env.BASE_URL || 'http://localhost:8311'}/pickups/${pickupId}`,
                metadata: {
                    customerName,
                    scheduledDate,
                    timeSlot,
                    itemCount: items.length
                }
            };

            // Generate QR code
            const qrCodeBuffer = await QRCode.toBuffer(JSON.stringify(qrData), {
                type: 'png',
                width: customSize,
                height: customSize,
                margin: 2,
                color: {
                    dark: '#388e3c',
                    light: '#FFFFFF'
                },
                errorCorrectionLevel: 'M'
            });

            // Enhance with pickup details
            let finalBuffer = qrCodeBuffer;

            if (includeTitle) {
                finalBuffer = await this.enhanceQRCode(qrCodeBuffer, {
                    title: `Pickup: ${pickupId.substring(0, 8).toUpperCase()}`,
                    subtitle: customerName,
                    additionalText: `${scheduledDate} at ${timeSlot.startTime}`,
                    size: customSize,
                    titleColor: '#388e3c'
                });
            }

            // Save QR code file
            const filename = `pickup_${pickupId}_${Date.now()}.png`;
            const filepath = path.join(this.qrCodesPath, filename);
            await fs.writeFile(filepath, finalBuffer);

            // Store QR code information
            const qrCodeInfo = {
                qrId,
                type: this.qrCodeTypes.PICKUP,
                pickupId,
                reservationId,
                customerId,
                locationId,
                filename,
                filepath,
                url: `/qr-codes/${filename}`,
                data: qrData,
                createdAt: timestamp.toISOString(),
                scanCount: 0,
                lastScanned: null,
                isActive: true,
                options
            };

            await this.storeQRCodeInfo(qrCodeInfo);

            logger.logInventoryEvent('qr_code_generated', locationId, customerId, {
                qrId,
                pickupId,
                type: 'pickup',
                filename
            });

            return qrCodeInfo;

        } catch (error) {
            logger.error('Failed to generate pickup QR code', {
                pickupData,
                error: error.message
            });
            throw error;
        }
    }

    async generateLocationQRCode(locationData, options = {}) {
        try {
            const {
                locationId,
                locationName,
                address,
                operatingHours,
                contactInfo,
                customSize = 200,
                includeTitle = true,
                logoPath = null
            } = locationData;

            const qrId = uuidv4();
            const timestamp = new Date();

            // Create QR code data payload
            const qrData = {
                type: this.qrCodeTypes.LOCATION,
                qrId,
                locationId,
                timestamp: timestamp.toISOString(),
                url: `${process.env.BASE_URL || 'http://localhost:8311'}/locations/${locationId}`,
                metadata: {
                    locationName,
                    address,
                    operatingHours,
                    contactInfo
                }
            };

            // Generate QR code
            const qrCodeBuffer = await QRCode.toBuffer(JSON.stringify(qrData), {
                type: 'png',
                width: customSize,
                height: customSize,
                margin: 2,
                color: {
                    dark: '#ff5722',
                    light: '#FFFFFF'
                },
                errorCorrectionLevel: 'M'
            });

            // Enhance with location details
            let finalBuffer = qrCodeBuffer;

            if (includeTitle) {
                finalBuffer = await this.enhanceQRCode(qrCodeBuffer, {
                    title: locationName,
                    subtitle: 'Location Info & Inventory',
                    logoPath,
                    size: customSize,
                    titleColor: '#ff5722'
                });
            }

            // Save QR code file
            const filename = `location_${locationId}_${Date.now()}.png`;
            const filepath = path.join(this.qrCodesPath, filename);
            await fs.writeFile(filepath, finalBuffer);

            // Store QR code information
            const qrCodeInfo = {
                qrId,
                type: this.qrCodeTypes.LOCATION,
                locationId,
                filename,
                filepath,
                url: `/qr-codes/${filename}`,
                data: qrData,
                createdAt: timestamp.toISOString(),
                scanCount: 0,
                lastScanned: null,
                isActive: true,
                options
            };

            await this.storeQRCodeInfo(qrCodeInfo);

            logger.logInventoryEvent('qr_code_generated', locationId, 'system', {
                qrId,
                type: 'location',
                filename
            });

            return qrCodeInfo;

        } catch (error) {
            logger.error('Failed to generate location QR code', {
                locationData,
                error: error.message
            });
            throw error;
        }
    }

    async generateQuickActionQRCode(actionData, options = {}) {
        try {
            const {
                action, // 'check_stock', 'quick_sale', 'inventory_count', etc.
                locationId,
                itemId = null,
                parameters = {},
                customSize = 200,
                includeTitle = true,
                expiresIn = 24 // hours
            } = actionData;

            const qrId = uuidv4();
            const timestamp = new Date();
            const expiresAt = new Date(Date.now() + (expiresIn * 60 * 60 * 1000));

            // Create QR code data payload
            const qrData = {
                type: this.qrCodeTypes.QUICK_ACTION,
                qrId,
                action,
                locationId,
                itemId,
                parameters,
                timestamp: timestamp.toISOString(),
                expiresAt: expiresAt.toISOString(),
                url: `${process.env.BASE_URL || 'http://localhost:8311'}/actions/${qrId}`,
                metadata: {
                    action,
                    description: this.getActionDescription(action),
                    expiresIn: `${expiresIn}h`
                }
            };

            // Generate QR code
            const qrCodeBuffer = await QRCode.toBuffer(JSON.stringify(qrData), {
                type: 'png',
                width: customSize,
                height: customSize,
                margin: 2,
                color: {
                    dark: '#9c27b0',
                    light: '#FFFFFF'
                },
                errorCorrectionLevel: 'M'
            });

            // Enhance with action details
            let finalBuffer = qrCodeBuffer;

            if (includeTitle) {
                finalBuffer = await this.enhanceQRCode(qrCodeBuffer, {
                    title: 'Quick Action',
                    subtitle: this.getActionDescription(action),
                    additionalText: `Expires: ${expiresAt.toLocaleDateString()}`,
                    size: customSize,
                    titleColor: '#9c27b0'
                });
            }

            // Save QR code file
            const filename = `action_${action}_${qrId}_${Date.now()}.png`;
            const filepath = path.join(this.qrCodesPath, filename);
            await fs.writeFile(filepath, finalBuffer);

            // Store QR code information
            const qrCodeInfo = {
                qrId,
                type: this.qrCodeTypes.QUICK_ACTION,
                action,
                locationId,
                itemId,
                filename,
                filepath,
                url: `/qr-codes/${filename}`,
                data: qrData,
                createdAt: timestamp.toISOString(),
                expiresAt: expiresAt.toISOString(),
                scanCount: 0,
                lastScanned: null,
                isActive: true,
                options
            };

            await this.storeQRCodeInfo(qrCodeInfo);

            logger.logInventoryEvent('qr_code_generated', locationId, 'system', {
                qrId,
                action,
                type: 'quick_action',
                filename
            });

            return qrCodeInfo;

        } catch (error) {
            logger.error('Failed to generate quick action QR code', {
                actionData,
                error: error.message
            });
            throw error;
        }
    }

    async scanQRCode(qrCodeData, scanContext = {}) {
        try {
            const {
                scannedBy,
                locationId,
                deviceId,
                scanMethod = 'manual', // 'manual', 'automated', 'mobile_app'
                clientInfo = {}
            } = scanContext;

            let parsedData;

            // Parse QR code data
            try {
                parsedData = typeof qrCodeData === 'string' ? JSON.parse(qrCodeData) : qrCodeData;
            } catch (parseError) {
                throw new Error('Invalid QR code data format');
            }

            // Validate QR code structure
            if (!parsedData.type || !parsedData.qrId) {
                throw new Error('Missing required QR code fields');
            }

            // Check if QR code is still active
            const qrCodeInfo = await this.getQRCodeInfo(parsedData.qrId);
            if (!qrCodeInfo) {
                throw new Error('QR code not found or invalid');
            }

            if (!qrCodeInfo.isActive) {
                throw new Error('QR code is no longer active');
            }

            // Check expiration for time-sensitive QR codes
            if (qrCodeInfo.expiresAt && new Date() > new Date(qrCodeInfo.expiresAt)) {
                await this.deactivateQRCode(parsedData.qrId, 'expired');
                throw new Error('QR code has expired');
            }

            const timestamp = new Date();
            const scanId = uuidv4();

            // Create scan record
            const scanRecord = {
                scanId,
                qrId: parsedData.qrId,
                type: parsedData.type,
                scannedBy,
                locationId,
                deviceId,
                scanMethod,
                clientInfo,
                scannedAt: timestamp.toISOString(),
                data: parsedData,
                result: 'success'
            };

            // Update QR code scan statistics
            qrCodeInfo.scanCount += 1;
            qrCodeInfo.lastScanned = timestamp.toISOString();
            await this.storeQRCodeInfo(qrCodeInfo);

            // Store scan record
            await this.storeScanRecord(scanRecord);

            // Process scan based on QR code type
            const processResult = await this.processQRCodeScan(parsedData, scanContext);

            // Emit real-time scan event
            this.io.to(`location:${locationId}`).emit('qr_code_scanned', {
                scanId,
                qrId: parsedData.qrId,
                type: parsedData.type,
                scannedBy,
                result: processResult,
                timestamp: timestamp.toISOString()
            });

            logger.logInventoryEvent('qr_code_scanned', locationId, scannedBy, {
                scanId,
                qrId: parsedData.qrId,
                type: parsedData.type,
                scanMethod
            });

            return {
                scanId,
                qrId: parsedData.qrId,
                type: parsedData.type,
                result: processResult,
                scannedAt: timestamp.toISOString()
            };

        } catch (error) {
            logger.error('Failed to process QR code scan', {
                qrCodeData: typeof qrCodeData === 'string' ? qrCodeData.substring(0, 200) : 'object',
                scanContext,
                error: error.message
            });
            throw error;
        }
    }

    async processQRCodeScan(qrData, scanContext) {
        const { scannedBy, locationId } = scanContext;

        switch (qrData.type) {
            case this.qrCodeTypes.ITEM:
                return await this.processItemScan(qrData, scanContext);

            case this.qrCodeTypes.RESERVATION:
                return await this.processReservationScan(qrData, scanContext);

            case this.qrCodeTypes.PICKUP:
                return await this.processPickupScan(qrData, scanContext);

            case this.qrCodeTypes.LOCATION:
                return await this.processLocationScan(qrData, scanContext);

            case this.qrCodeTypes.QUICK_ACTION:
                return await this.processQuickActionScan(qrData, scanContext);

            default:
                return { action: 'unknown', message: 'Unknown QR code type' };
        }
    }

    async processItemScan(qrData, scanContext) {
        const { itemId, locationId } = qrData;

        // Redirect to item details or inventory check
        return {
            action: 'show_item_details',
            itemId,
            locationId,
            redirect: `/inventory/item/${locationId}/${itemId}`,
            message: `Item ${itemId} details loaded`
        };
    }

    async processReservationScan(qrData, scanContext) {
        const { reservationId, customerId } = qrData;

        // Check reservation status and provide next action
        return {
            action: 'show_reservation_details',
            reservationId,
            customerId,
            redirect: `/reservations/${reservationId}`,
            message: `Reservation ${reservationId} loaded`,
            suggestedActions: ['confirm_arrival', 'start_pickup', 'cancel_reservation']
        };
    }

    async processPickupScan(qrData, scanContext) {
        const { pickupId, customerId } = qrData;

        // Process pickup scan - could trigger arrival confirmation
        return {
            action: 'customer_arrival',
            pickupId,
            customerId,
            redirect: `/pickups/${pickupId}`,
            message: `Customer arrival registered for pickup ${pickupId}`,
            suggestedActions: ['confirm_items', 'start_fulfillment']
        };
    }

    async processLocationScan(qrData, scanContext) {
        const { locationId } = qrData;

        // Show location information and inventory
        return {
            action: 'show_location_info',
            locationId,
            redirect: `/locations/${locationId}`,
            message: `Location ${locationId} information loaded`,
            suggestedActions: ['view_inventory', 'schedule_pickup', 'check_stock']
        };
    }

    async processQuickActionScan(qrData, scanContext) {
        const { action, locationId, itemId, parameters } = qrData;

        // Execute quick action
        switch (action) {
            case 'check_stock':
                return {
                    action: 'check_stock',
                    locationId,
                    itemId,
                    redirect: `/inventory/check/${locationId}${itemId ? `/${itemId}` : ''}`,
                    message: 'Stock check initiated'
                };

            case 'quick_sale':
                return {
                    action: 'quick_sale',
                    locationId,
                    itemId,
                    redirect: `/pos/quick-sale/${locationId}${itemId ? `?item=${itemId}` : ''}`,
                    message: 'Quick sale interface loaded'
                };

            case 'inventory_count':
                return {
                    action: 'inventory_count',
                    locationId,
                    redirect: `/inventory/count/${locationId}`,
                    message: 'Inventory count interface loaded'
                };

            default:
                return {
                    action: 'custom_action',
                    parameters,
                    message: `Action ${action} triggered`
                };
        }
    }

    async enhanceQRCode(qrCodeBuffer, options = {}) {
        try {
            const {
                title,
                subtitle,
                additionalText,
                logoPath,
                size = 200,
                titleColor = '#000000',
                backgroundColor = '#FFFFFF'
            } = options;

            const padding = 60;
            const titleHeight = title ? 30 : 0;
            const subtitleHeight = subtitle ? 25 : 0;
            const additionalHeight = additionalText ? 20 : 0;
            const logoSize = 40;
            
            const totalHeight = size + titleHeight + subtitleHeight + additionalHeight + padding * 2;
            const totalWidth = Math.max(size + padding * 2, 300);

            // Create SVG with title and QR code
            let svg = `
                <svg width="${totalWidth}" height="${totalHeight}" xmlns="http://www.w3.org/2000/svg">
                    <rect width="100%" height="100%" fill="${backgroundColor}"/>
            `;

            let currentY = padding;

            // Add title
            if (title) {
                svg += `
                    <text x="${totalWidth / 2}" y="${currentY + 20}" 
                          text-anchor="middle" 
                          font-family="Arial, sans-serif" 
                          font-size="16" 
                          font-weight="bold" 
                          fill="${titleColor}">${title}</text>
                `;
                currentY += titleHeight;
            }

            // Add subtitle
            if (subtitle) {
                svg += `
                    <text x="${totalWidth / 2}" y="${currentY + 15}" 
                          text-anchor="middle" 
                          font-family="Arial, sans-serif" 
                          font-size="12" 
                          fill="#666666">${subtitle}</text>
                `;
                currentY += subtitleHeight;
            }

            svg += `</svg>`;

            // Convert SVG to buffer
            const svgBuffer = Buffer.from(svg);

            // Composite the QR code and text
            let composite = [
                {
                    input: qrCodeBuffer,
                    top: currentY,
                    left: (totalWidth - size) / 2
                }
            ];

            // Add logo if provided
            if (logoPath) {
                try {
                    const resizedLogo = await sharp(logoPath)
                        .resize(logoSize, logoSize)
                        .png()
                        .toBuffer();

                    composite.push({
                        input: resizedLogo,
                        top: currentY + (size - logoSize) / 2,
                        left: (totalWidth - logoSize) / 2
                    });
                } catch (logoError) {
                    logger.warn('Failed to add logo to QR code', { logoPath, error: logoError.message });
                }
            }

            const enhancedBuffer = await sharp(svgBuffer)
                .composite(composite)
                .png()
                .toBuffer();

            // Add additional text at the bottom
            if (additionalText) {
                const finalSvg = `
                    <svg width="${totalWidth}" height="${totalHeight}" xmlns="http://www.w3.org/2000/svg">
                        <rect width="100%" height="100%" fill="transparent"/>
                        <text x="${totalWidth / 2}" y="${totalHeight - padding + 15}" 
                              text-anchor="middle" 
                              font-family="Arial, sans-serif" 
                              font-size="10" 
                              fill="#888888">${additionalText}</text>
                    </svg>
                `;

                const finalSvgBuffer = Buffer.from(finalSvg);
                
                return await sharp(enhancedBuffer)
                    .composite([{ input: finalSvgBuffer, top: 0, left: 0 }])
                    .png()
                    .toBuffer();
            }

            return enhancedBuffer;

        } catch (error) {
            logger.error('Failed to enhance QR code', { error: error.message });
            return qrCodeBuffer; // Return original if enhancement fails
        }
    }

    async storeQRCodeInfo(qrCodeInfo) {
        const qrKey = `qrcode:${qrCodeInfo.qrId}`;
        
        await this.redis.hmset(qrKey, {
            qrId: qrCodeInfo.qrId,
            type: qrCodeInfo.type,
            filename: qrCodeInfo.filename,
            filepath: qrCodeInfo.filepath,
            url: qrCodeInfo.url,
            data: JSON.stringify(qrCodeInfo.data),
            createdAt: qrCodeInfo.createdAt,
            expiresAt: qrCodeInfo.expiresAt || '',
            scanCount: qrCodeInfo.scanCount,
            lastScanned: qrCodeInfo.lastScanned || '',
            isActive: qrCodeInfo.isActive.toString(),
            options: JSON.stringify(qrCodeInfo.options),
            // Type-specific fields
            itemId: qrCodeInfo.itemId || '',
            locationId: qrCodeInfo.locationId || '',
            reservationId: qrCodeInfo.reservationId || '',
            pickupId: qrCodeInfo.pickupId || '',
            customerId: qrCodeInfo.customerId || '',
            action: qrCodeInfo.action || ''
        });

        // Set expiration for the key if QR code expires
        if (qrCodeInfo.expiresAt) {
            const expiresIn = Math.max(0, Math.floor((new Date(qrCodeInfo.expiresAt) - new Date()) / 1000));
            if (expiresIn > 0) {
                await this.redis.expire(qrKey, expiresIn);
            }
        }

        // Update in-memory cache
        this.qrCodeCache.set(qrCodeInfo.qrId, qrCodeInfo);
    }

    async storeScanRecord(scanRecord) {
        const scanKey = `scan:${scanRecord.scanId}`;
        
        await this.redis.hmset(scanKey, {
            scanId: scanRecord.scanId,
            qrId: scanRecord.qrId,
            type: scanRecord.type,
            scannedBy: scanRecord.scannedBy,
            locationId: scanRecord.locationId,
            deviceId: scanRecord.deviceId || '',
            scanMethod: scanRecord.scanMethod,
            clientInfo: JSON.stringify(scanRecord.clientInfo),
            scannedAt: scanRecord.scannedAt,
            data: JSON.stringify(scanRecord.data),
            result: scanRecord.result
        });

        // Set expiration (30 days)
        await this.redis.expire(scanKey, 86400 * 30);

        // Update scan history
        if (!this.scanHistory.has(scanRecord.qrId)) {
            this.scanHistory.set(scanRecord.qrId, []);
        }
        
        const history = this.scanHistory.get(scanRecord.qrId);
        history.push(scanRecord);
        
        // Keep only last 100 scans per QR code
        if (history.length > 100) {
            this.scanHistory.set(scanRecord.qrId, history.slice(-100));
        }
    }

    async getQRCodeInfo(qrId) {
        if (this.qrCodeCache.has(qrId)) {
            return this.qrCodeCache.get(qrId);
        }

        // Load from Redis
        const qrKey = `qrcode:${qrId}`;
        const qrData = await this.redis.hgetall(qrKey);

        if (Object.keys(qrData).length === 0) {
            return null;
        }

        const qrCodeInfo = {
            ...qrData,
            data: JSON.parse(qrData.data || '{}'),
            options: JSON.parse(qrData.options || '{}'),
            scanCount: parseInt(qrData.scanCount, 10),
            isActive: qrData.isActive === 'true'
        };

        this.qrCodeCache.set(qrId, qrCodeInfo);
        return qrCodeInfo;
    }

    async deactivateQRCode(qrId, reason = 'manual') {
        const qrCodeInfo = await this.getQRCodeInfo(qrId);
        if (!qrCodeInfo) return false;

        qrCodeInfo.isActive = false;
        qrCodeInfo.deactivatedAt = new Date().toISOString();
        qrCodeInfo.deactivationReason = reason;

        await this.storeQRCodeInfo(qrCodeInfo);

        logger.logInventoryEvent('qr_code_deactivated', qrCodeInfo.locationId || 'unknown', 'system', {
            qrId,
            type: qrCodeInfo.type,
            reason
        });

        return true;
    }

    async getQRCodesByType(type, locationId = null, isActive = true) {
        const pattern = 'qrcode:*';
        const keys = await this.redis.keys(pattern);
        
        const qrCodes = [];

        for (const key of keys) {
            const qrData = await this.redis.hgetall(key);
            if (Object.keys(qrData).length > 0) {
                const qrCodeInfo = {
                    ...qrData,
                    data: JSON.parse(qrData.data || '{}'),
                    options: JSON.parse(qrData.options || '{}'),
                    scanCount: parseInt(qrData.scanCount, 10),
                    isActive: qrData.isActive === 'true'
                };

                if (qrCodeInfo.type === type &&
                    (!locationId || qrCodeInfo.locationId === locationId) &&
                    (!isActive || qrCodeInfo.isActive)) {
                    qrCodes.push(qrCodeInfo);
                }
            }
        }

        // Sort by creation date (most recent first)
        qrCodes.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

        return qrCodes;
    }

    async getScanHistory(qrId, limit = 50) {
        const history = this.scanHistory.get(qrId) || [];
        return history.slice(-limit).reverse(); // Most recent first
    }

    getActionDescription(action) {
        const descriptions = {
            'check_stock': 'Check Stock Levels',
            'quick_sale': 'Quick Sale',
            'inventory_count': 'Inventory Count',
            'receive_shipment': 'Receive Shipment',
            'transfer_items': 'Transfer Items',
            'adjust_inventory': 'Adjust Inventory'
        };

        return descriptions[action] || 'Custom Action';
    }

    async generateBatchQRCodes(items, batchOptions = {}) {
        const {
            type = this.qrCodeTypes.ITEM,
            locationId,
            outputFormat = 'individual', // 'individual', 'sheet', 'labels'
            sheetLayout = { rows: 5, cols: 4 },
            includeTitle = true,
            customSize = 150
        } = batchOptions;

        try {
            const qrCodes = [];
            const batchId = uuidv4();

            for (const item of items) {
                let qrCodeInfo;

                switch (type) {
                    case this.qrCodeTypes.ITEM:
                        qrCodeInfo = await this.generateItemQRCode({
                            ...item,
                            locationId,
                            customSize,
                            includeTitle
                        });
                        break;

                    case this.qrCodeTypes.QUICK_ACTION:
                        qrCodeInfo = await this.generateQuickActionQRCode({
                            ...item,
                            locationId,
                            customSize,
                            includeTitle
                        });
                        break;

                    default:
                        throw new Error(`Batch generation not supported for type: ${type}`);
                }

                qrCodes.push(qrCodeInfo);
            }

            // Create batch sheet if requested
            if (outputFormat === 'sheet') {
                const sheetInfo = await this.createQRCodeSheet(qrCodes, sheetLayout);
                
                return {
                    batchId,
                    type: 'sheet',
                    qrCodes,
                    sheet: sheetInfo,
                    totalGenerated: qrCodes.length
                };
            }

            return {
                batchId,
                type: 'individual',
                qrCodes,
                totalGenerated: qrCodes.length
            };

        } catch (error) {
            logger.error('Failed to generate batch QR codes', {
                itemCount: items.length,
                batchOptions,
                error: error.message
            });
            throw error;
        }
    }

    async createQRCodeSheet(qrCodes, layout) {
        try {
            const { rows, cols } = layout;
            const qrSize = 120;
            const padding = 20;
            const titleHeight = 30;
            
            const cellWidth = qrSize + padding * 2;
            const cellHeight = qrSize + titleHeight + padding * 2;
            
            const sheetWidth = cols * cellWidth;
            const sheetHeight = rows * cellHeight;

            // Create composite array for sharp
            const compositeImages = [];

            for (let i = 0; i < Math.min(qrCodes.length, rows * cols); i++) {
                const row = Math.floor(i / cols);
                const col = i % cols;
                
                const qrCode = qrCodes[i];
                const left = col * cellWidth + padding;
                const top = row * cellHeight + padding;

                // Read QR code file
                const qrBuffer = await fs.readFile(qrCode.filepath);
                
                compositeImages.push({
                    input: qrBuffer,
                    top,
                    left
                });
            }

            // Create white background
            const background = await sharp({
                create: {
                    width: sheetWidth,
                    height: sheetHeight,
                    channels: 3,
                    background: { r: 255, g: 255, b: 255 }
                }
            })
            .composite(compositeImages)
            .png()
            .toBuffer();

            // Save sheet
            const filename = `qr_sheet_${Date.now()}.png`;
            const filepath = path.join(this.qrCodesPath, filename);
            await fs.writeFile(filepath, background);

            return {
                filename,
                filepath,
                url: `/qr-codes/${filename}`,
                layout,
                totalCodes: Math.min(qrCodes.length, rows * cols)
            };

        } catch (error) {
            logger.error('Failed to create QR code sheet', { error: error.message });
            throw error;
        }
    }

    async getQRCodeMetrics(options = {}) {
        const {
            locationId = null,
            startDate = new Date(Date.now() - 24 * 60 * 60 * 1000), // 24 hours ago
            endDate = new Date()
        } = options;

        const metrics = {
            totalQRCodes: 0,
            activeQRCodes: 0,
            totalScans: 0,
            uniqueScans: 0,
            typeBreakdown: {},
            scansByDay: [],
            topScannedCodes: [],
            timestamp: new Date().toISOString()
        };

        // Get all QR codes
        const pattern = 'qrcode:*';
        const keys = await this.redis.keys(pattern);

        const scanCounts = new Map();

        for (const key of keys) {
            const qrData = await this.redis.hgetall(key);
            if (Object.keys(qrData).length > 0) {
                const createdAt = new Date(qrData.createdAt);
                
                // Filter by date range and location
                if (createdAt >= startDate && createdAt <= endDate) {
                    if (!locationId || qrData.locationId === locationId) {
                        metrics.totalQRCodes++;
                        
                        if (qrData.isActive === 'true') {
                            metrics.activeQRCodes++;
                        }

                        const scanCount = parseInt(qrData.scanCount, 10);
                        metrics.totalScans += scanCount;

                        // Type breakdown
                        const type = qrData.type;
                        if (!metrics.typeBreakdown[type]) {
                            metrics.typeBreakdown[type] = { count: 0, scans: 0 };
                        }
                        metrics.typeBreakdown[type].count++;
                        metrics.typeBreakdown[type].scans += scanCount;

                        // Track for top scanned codes
                        if (scanCount > 0) {
                            scanCounts.set(qrData.qrId, {
                                qrId: qrData.qrId,
                                type: qrData.type,
                                scanCount,
                                itemId: qrData.itemId,
                                locationId: qrData.locationId
                            });
                        }
                    }
                }
            }
        }

        // Get top scanned codes
        metrics.topScannedCodes = Array.from(scanCounts.values())
            .sort((a, b) => b.scanCount - a.scanCount)
            .slice(0, 10);

        return metrics;
    }
}

module.exports = QRCodeManager;