const EventEmitter = require('events');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const sharp = require('sharp');
const cheerio = require('cheerio');

class ExposedFolderProcessor extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.exposedFolders = new Map();
        this.marketingAssets = new Map();
        this.contentCategories = new Map();
        this.processingQueue = [];
        
        this.setupEventHandlers();
        this.startProcessingWorker();
        this.initializeContentCategories();
    }

    setupEventHandlers() {
        this.on('folder_processed', this.handleFolderProcessed.bind(this));
        this.on('asset_categorized', this.handleAssetCategorized.bind(this));
        this.on('marketing_ready', this.handleMarketingReady.bind(this));
        this.on('content_updated', this.handleContentUpdated.bind(this));
    }

    initializeContentCategories() {
        this.contentCategories.set('images', {
            name: 'Images & Graphics',
            extensions: ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp'],
            marketingUse: ['social_media', 'display_ads', 'email_headers', 'website_banners'],
            processingNeeded: true
        });
        
        this.contentCategories.set('videos', {
            name: 'Video Content',
            extensions: ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'],
            marketingUse: ['video_ads', 'social_stories', 'product_demos', 'testimonials'],
            processingNeeded: true
        });
        
        this.contentCategories.set('documents', {
            name: 'Marketing Documents',
            extensions: ['.pdf', '.doc', '.docx', '.ppt', '.pptx'],
            marketingUse: ['lead_magnets', 'whitepapers', 'case_studies', 'presentations'],
            processingNeeded: false
        });
        
        this.contentCategories.set('audio', {
            name: 'Audio Content',
            extensions: ['.mp3', '.wav', '.ogg', '.m4a'],
            marketingUse: ['podcast_ads', 'voice_overs', 'jingles', 'audio_testimonials'],
            processingNeeded: false
        });
        
        this.contentCategories.set('web', {
            name: 'Web Content',
            extensions: ['.html', '.css', '.js'],
            marketingUse: ['landing_pages', 'email_templates', 'widgets', 'tracking_codes'],
            processingNeeded: true
        });
        
        this.contentCategories.set('data', {
            name: 'Marketing Data',
            extensions: ['.csv', '.json', '.xml', '.xlsx'],
            marketingUse: ['customer_lists', 'analytics_data', 'campaign_data', 'leads'],
            processingNeeded: true
        });
    }

    async processFolder(folderData) {
        try {
            const folderId = uuidv4();
            const exposedFolder = {
                id: folderId,
                name: folderData.name || 'Unnamed Folder',
                path: folderData.path,
                description: folderData.description || '',
                marketingPurpose: folderData.marketingPurpose || 'general',
                targetAudience: folderData.targetAudience || [],
                brandGuidelines: folderData.brandGuidelines || {},
                permissions: {
                    canUseInAds: folderData.permissions?.canUseInAds !== false,
                    canUseInEmail: folderData.permissions?.canUseInEmail !== false,
                    canUseInSocial: folderData.permissions?.canUseInSocial !== false,
                    requiresApproval: folderData.permissions?.requiresApproval || false,
                    expiryDate: folderData.permissions?.expiryDate || null
                },
                status: 'processing',
                createdAt: new Date(),
                processedAt: null,
                assets: [],
                analytics: {
                    totalFiles: 0,
                    processedFiles: 0,
                    categorizedAssets: 0,
                    marketingReadyAssets: 0,
                    errors: []
                }
            };

            this.exposedFolders.set(folderId, exposedFolder);
            await this.redis.hset('exposed_folders', folderId, JSON.stringify(exposedFolder));
            
            // Queue for processing
            this.processingQueue.push(folderId);
            
            this.logger.info('Folder queued for processing', { 
                folderId, 
                folderName: exposedFolder.name 
            });
            
            this.io.emit('folder_processing_started', {
                folderId,
                name: exposedFolder.name,
                status: 'processing'
            });
            
            return { success: true, folderId, status: 'queued_for_processing' };
        } catch (error) {
            this.logger.error('Failed to process folder', { error: error.message, folderData });
            throw new Error(`Folder processing failed: ${error.message}`);
        }
    }

    async processFolderContents(folderId) {
        try {
            const exposedFolder = this.exposedFolders.get(folderId) || 
                JSON.parse(await this.redis.hget('exposed_folders', folderId));
            
            if (!exposedFolder) {
                throw new Error(`Exposed folder ${folderId} not found`);
            }
            
            // Scan folder contents
            const folderContents = await this.scanFolderRecursively(exposedFolder.path);
            exposedFolder.analytics.totalFiles = folderContents.length;
            
            const processedAssets = [];
            
            for (const filePath of folderContents) {
                try {
                    const asset = await this.processFile(filePath, exposedFolder);
                    if (asset) {
                        processedAssets.push(asset);
                        exposedFolder.analytics.processedFiles++;
                        
                        if (asset.marketingReady) {
                            exposedFolder.analytics.marketingReadyAssets++;
                        }
                        
                        // Emit progress
                        this.io.emit('folder_processing_progress', {
                            folderId,
                            processed: exposedFolder.analytics.processedFiles,
                            total: exposedFolder.analytics.totalFiles,
                            currentFile: path.basename(filePath)
                        });
                    }
                } catch (error) {
                    exposedFolder.analytics.errors.push({
                        file: filePath,
                        error: error.message,
                        timestamp: new Date()
                    });
                    this.logger.error('File processing error', { filePath, error: error.message });
                }
            }
            
            exposedFolder.assets = processedAssets;
            exposedFolder.analytics.categorizedAssets = processedAssets.length;
            exposedFolder.status = 'completed';
            exposedFolder.processedAt = new Date();
            
            // Update in storage
            this.exposedFolders.set(folderId, exposedFolder);
            await this.redis.hset('exposed_folders', folderId, JSON.stringify(exposedFolder));
            
            // Create marketing asset entries
            await this.createMarketingAssets(folderId, processedAssets);
            
            this.emit('folder_processed', { folderId, exposedFolder });
            
            return { success: true, processedAssets: processedAssets.length };
        } catch (error) {
            this.logger.error('Failed to process folder contents', { error: error.message, folderId });
            
            // Update folder status to failed
            const exposedFolder = this.exposedFolders.get(folderId);
            if (exposedFolder) {
                exposedFolder.status = 'failed';
                exposedFolder.analytics.errors.push({
                    error: error.message,
                    timestamp: new Date()
                });
                this.exposedFolders.set(folderId, exposedFolder);
                await this.redis.hset('exposed_folders', folderId, JSON.stringify(exposedFolder));
            }
            
            throw error;
        }
    }

    async scanFolderRecursively(folderPath) {
        const files = [];
        
        try {
            const entries = await fs.readdir(folderPath, { withFileTypes: true });
            
            for (const entry of entries) {
                const fullPath = path.join(folderPath, entry.name);
                
                if (entry.isDirectory()) {
                    // Skip hidden directories and common non-marketing folders
                    if (!entry.name.startsWith('.') && 
                        !['node_modules', 'build', 'dist', '.git'].includes(entry.name)) {
                        const subFiles = await this.scanFolderRecursively(fullPath);
                        files.push(...subFiles);
                    }
                } else if (entry.isFile()) {
                    // Skip hidden files
                    if (!entry.name.startsWith('.')) {
                        files.push(fullPath);
                    }
                }
            }
        } catch (error) {
            this.logger.warn('Failed to scan directory', { folderPath, error: error.message });
        }
        
        return files;
    }

    async processFile(filePath, exposedFolder) {
        const fileStats = await fs.stat(filePath);
        const fileName = path.basename(filePath);
        const fileExt = path.extname(fileName).toLowerCase();
        const relativePath = path.relative(exposedFolder.path, filePath);
        
        // Determine content category
        const category = this.getFileCategory(fileExt);
        if (!category) {
            return null; // Skip unsupported file types
        }
        
        const asset = {
            id: uuidv4(),
            folderId: exposedFolder.id,
            fileName,
            filePath,
            relativePath,
            fileSize: fileStats.size,
            category: category.name,
            extension: fileExt,
            marketingUses: category.marketingUse,
            createdAt: fileStats.birthtime,
            modifiedAt: fileStats.mtime,
            processedAt: new Date(),
            metadata: {},
            marketingReady: false,
            optimizedVersions: [],
            tags: [],
            brandCompliance: {
                checked: false,
                compliant: null,
                issues: []
            }
        };
        
        // Process file based on category
        if (category.processingNeeded) {
            await this.processAssetByType(asset, category);
        }
        
        // Check brand compliance
        await this.checkBrandCompliance(asset, exposedFolder.brandGuidelines);
        
        // Generate tags
        asset.tags = await this.generateAssetTags(asset);
        
        // Mark as marketing ready if appropriate
        asset.marketingReady = this.isMarketingReady(asset);
        
        this.emit('asset_categorized', { asset, category });
        
        return asset;
    }

    async processAssetByType(asset, category) {
        try {
            switch (category.name) {
                case 'Images & Graphics':
                    await this.processImageAsset(asset);
                    break;
                case 'Video Content':
                    await this.processVideoAsset(asset);
                    break;
                case 'Web Content':
                    await this.processWebAsset(asset);
                    break;
                case 'Marketing Data':
                    await this.processDataAsset(asset);
                    break;
            }
        } catch (error) {
            this.logger.error('Asset processing error', { 
                assetId: asset.id, 
                error: error.message 
            });
        }
    }

    async processImageAsset(asset) {
        try {
            const imageBuffer = await fs.readFile(asset.filePath);
            const imageMetadata = await sharp(imageBuffer).metadata();
            
            asset.metadata = {
                width: imageMetadata.width,
                height: imageMetadata.height,
                format: imageMetadata.format,
                hasAlpha: imageMetadata.hasAlpha,
                colorSpace: imageMetadata.space,
                density: imageMetadata.density
            };
            
            // Generate optimized versions for different marketing channels
            const optimizedVersions = await this.generateImageOptimizations(imageBuffer, asset);
            asset.optimizedVersions = optimizedVersions;
            
            // Extract colors for brand analysis
            const colorAnalysis = await this.analyzeImageColors(imageBuffer);
            asset.metadata.dominantColors = colorAnalysis.dominantColors;
            asset.metadata.colorPalette = colorAnalysis.palette;
            
        } catch (error) {
            this.logger.error('Image processing error', { 
                assetId: asset.id, 
                error: error.message 
            });
        }
    }

    async generateImageOptimizations(imageBuffer, asset) {
        const optimizations = [];
        
        // Social media sizes
        const socialSizes = [
            { name: 'instagram_square', width: 1080, height: 1080 },
            { name: 'instagram_story', width: 1080, height: 1920 },
            { name: 'facebook_post', width: 1200, height: 630 },
            { name: 'twitter_header', width: 1500, height: 500 },
            { name: 'linkedin_post', width: 1200, height: 627 }
        ];
        
        // Ad sizes (IAB standard)
        const adSizes = [
            { name: 'banner', width: 728, height: 90 },
            { name: 'rectangle', width: 300, height: 250 },
            { name: 'skyscraper', width: 160, height: 600 },
            { name: 'mobile_banner', width: 320, height: 50 }
        ];
        
        const allSizes = [...socialSizes, ...adSizes];
        
        for (const size of allSizes) {
            try {
                const optimizedBuffer = await sharp(imageBuffer)
                    .resize(size.width, size.height, { 
                        fit: 'cover',
                        position: 'center'
                    })
                    .jpeg({ quality: 85 })
                    .toBuffer();
                
                // In a real implementation, you'd save to a CDN or cloud storage
                optimizations.push({
                    name: size.name,
                    width: size.width,
                    height: size.height,
                    format: 'jpeg',
                    size: optimizedBuffer.length,
                    url: `/optimized/${asset.id}/${size.name}.jpg`,
                    createdAt: new Date()
                });
            } catch (error) {
                this.logger.error('Image optimization error', { 
                    sizeName: size.name, 
                    error: error.message 
                });
            }
        }
        
        return optimizations;
    }

    async analyzeImageColors(imageBuffer) {
        try {
            // Use sharp to extract dominant colors
            const { dominant } = await sharp(imageBuffer).stats();
            
            return {
                dominantColors: [
                    `rgb(${dominant.r}, ${dominant.g}, ${dominant.b})`
                ],
                palette: [
                    { color: `rgb(${dominant.r}, ${dominant.g}, ${dominant.b})`, percentage: 100 }
                ]
            };
        } catch (error) {
            this.logger.error('Color analysis error', { error: error.message });
            return { dominantColors: [], palette: [] };
        }
    }

    async processVideoAsset(asset) {
        try {
            // Basic video metadata (would use ffprobe in production)
            asset.metadata = {
                format: asset.extension.substring(1),
                estimatedDuration: 'unknown',
                hasAudio: true,
                isLandscape: true
            };
            
            // Generate video thumbnails and previews
            asset.optimizedVersions = [
                {
                    name: 'thumbnail',
                    width: 320,
                    height: 180,
                    format: 'jpeg',
                    url: `/thumbnails/${asset.id}/thumb.jpg`,
                    createdAt: new Date()
                },
                {
                    name: 'preview_gif',
                    width: 480,
                    height: 270,
                    format: 'gif',
                    url: `/previews/${asset.id}/preview.gif`,
                    createdAt: new Date()
                }
            ];
        } catch (error) {
            this.logger.error('Video processing error', { 
                assetId: asset.id, 
                error: error.message 
            });
        }
    }

    async processWebAsset(asset) {
        try {
            if (asset.extension === '.html') {
                const htmlContent = await fs.readFile(asset.filePath, 'utf-8');
                const $ = cheerio.load(htmlContent);
                
                asset.metadata = {
                    title: $('title').text() || '',
                    description: $('meta[name="description"]').attr('content') || '',
                    hasForm: $('form').length > 0,
                    hasVideo: $('video').length > 0,
                    hasImages: $('img').length > 0,
                    externalLinks: $('a[href^="http"]').length,
                    marketingPixels: this.detectMarketingPixels($),
                    seoScore: this.calculateBasicSEOScore($)
                };
            } else if (asset.extension === '.css') {
                const cssContent = await fs.readFile(asset.filePath, 'utf-8');
                asset.metadata = {
                    responsive: cssContent.includes('@media'),
                    animations: cssContent.includes('animation') || cssContent.includes('transition'),
                    variables: cssContent.includes('--') || cssContent.includes('var('),
                    framework: this.detectCSSFramework(cssContent)
                };
            } else if (asset.extension === '.js') {
                const jsContent = await fs.readFile(asset.filePath, 'utf-8');
                asset.metadata = {
                    hasAnalytics: this.detectAnalyticsCode(jsContent),
                    framework: this.detectJSFramework(jsContent),
                    minified: jsContent.length > 1000 && !jsContent.includes('\n'),
                    hasEvents: jsContent.includes('addEventListener') || jsContent.includes('onClick')
                };
            }
        } catch (error) {
            this.logger.error('Web asset processing error', { 
                assetId: asset.id, 
                error: error.message 
            });
        }
    }

    async processDataAsset(asset) {
        try {
            if (asset.extension === '.csv') {
                const csvContent = await fs.readFile(asset.filePath, 'utf-8');
                const lines = csvContent.split('\n').filter(line => line.trim());
                const headers = lines[0] ? lines[0].split(',').map(h => h.trim()) : [];
                
                asset.metadata = {
                    rowCount: lines.length - 1,
                    columnCount: headers.length,
                    headers,
                    hasEmailColumn: headers.some(h => h.toLowerCase().includes('email')),
                    hasPhoneColumn: headers.some(h => h.toLowerCase().includes('phone')),
                    hasNameColumn: headers.some(h => h.toLowerCase().includes('name')),
                    dataType: 'customer_data'
                };
                
                // Check for PII data
                asset.metadata.containsPII = asset.metadata.hasEmailColumn || 
                                           asset.metadata.hasPhoneColumn || 
                                           asset.metadata.hasNameColumn;
            } else if (asset.extension === '.json') {
                const jsonContent = await fs.readFile(asset.filePath, 'utf-8');
                const jsonData = JSON.parse(jsonContent);
                
                asset.metadata = {
                    isArray: Array.isArray(jsonData),
                    objectCount: Array.isArray(jsonData) ? jsonData.length : 1,
                    topLevelKeys: typeof jsonData === 'object' ? Object.keys(jsonData) : [],
                    dataType: this.inferJSONDataType(jsonData)
                };
            }
        } catch (error) {
            this.logger.error('Data asset processing error', { 
                assetId: asset.id, 
                error: error.message 
            });
        }
    }

    async checkBrandCompliance(asset, brandGuidelines) {
        asset.brandCompliance.checked = true;
        asset.brandCompliance.compliant = true;
        asset.brandCompliance.issues = [];
        
        if (!brandGuidelines || Object.keys(brandGuidelines).length === 0) {
            return; // No guidelines to check against
        }
        
        // Check color compliance for images
        if (asset.category === 'Images & Graphics' && asset.metadata.dominantColors) {
            if (brandGuidelines.allowedColors && brandGuidelines.allowedColors.length > 0) {
                const hasApprovedColors = asset.metadata.dominantColors.some(color =>
                    brandGuidelines.allowedColors.includes(color)
                );
                
                if (!hasApprovedColors) {
                    asset.brandCompliance.issues.push('Colors not in brand palette');
                    asset.brandCompliance.compliant = false;
                }
            }
        }
        
        // Check file naming conventions
        if (brandGuidelines.namingConvention) {
            const regex = new RegExp(brandGuidelines.namingConvention);
            if (!regex.test(asset.fileName)) {
                asset.brandCompliance.issues.push('File name does not follow brand naming convention');
                asset.brandCompliance.compliant = false;
            }
        }
        
        // Check file size limits
        if (brandGuidelines.maxFileSize && asset.fileSize > brandGuidelines.maxFileSize) {
            asset.brandCompliance.issues.push('File size exceeds brand guidelines');
            asset.brandCompliance.compliant = false;
        }
    }

    async generateAssetTags(asset) {
        const tags = [];
        
        // Add category-based tags
        tags.push(asset.category.toLowerCase().replace(/ & /g, '-').replace(/ /g, '-'));
        
        // Add extension tag
        tags.push(asset.extension.substring(1));
        
        // Add size-based tags for images
        if (asset.metadata.width && asset.metadata.height) {
            if (asset.metadata.width === asset.metadata.height) {
                tags.push('square');
            } else if (asset.metadata.width > asset.metadata.height) {
                tags.push('landscape');
            } else {
                tags.push('portrait');
            }
            
            // Resolution tags
            const pixels = asset.metadata.width * asset.metadata.height;
            if (pixels >= 1920 * 1080) {
                tags.push('high-resolution');
            } else if (pixels <= 800 * 600) {
                tags.push('low-resolution');
            }
        }
        
        // Add marketing use tags
        tags.push(...asset.marketingUses.map(use => use.replace(/_/g, '-')));
        
        // Add date-based tags
        const month = asset.createdAt.getMonth() + 1;
        const year = asset.createdAt.getFullYear();
        tags.push(`${year}`, `${year}-${month.toString().padStart(2, '0')}`);
        
        return [...new Set(tags)]; // Remove duplicates
    }

    isMarketingReady(asset) {
        // Basic criteria for marketing readiness
        let ready = true;
        
        // Must be brand compliant
        if (!asset.brandCompliance.compliant) {
            ready = false;
        }
        
        // Images must have optimized versions
        if (asset.category === 'Images & Graphics' && asset.optimizedVersions.length === 0) {
            ready = false;
        }
        
        // Data assets with PII need special handling
        if (asset.category === 'Marketing Data' && asset.metadata.containsPII) {
            ready = false; // Requires manual review
        }
        
        return ready;
    }

    getFileCategory(extension) {
        for (const [key, category] of this.contentCategories) {
            if (category.extensions.includes(extension)) {
                return category;
            }
        }
        return null;
    }

    // Helper methods for web asset processing
    detectMarketingPixels($) {
        const pixels = [];
        
        // Google Analytics
        if ($('script[src*="google-analytics.com"]').length > 0 || 
            $('script:contains("gtag")').length > 0) {
            pixels.push('google_analytics');
        }
        
        // Facebook Pixel
        if ($('script:contains("fbq")').length > 0) {
            pixels.push('facebook_pixel');
        }
        
        // LinkedIn Insight
        if ($('script:contains("_linkedin_partner_id")').length > 0) {
            pixels.push('linkedin_insight');
        }
        
        return pixels;
    }

    calculateBasicSEOScore($) {
        let score = 0;
        
        // Title tag (20 points)
        const title = $('title').text();
        if (title && title.length >= 30 && title.length <= 60) {
            score += 20;
        } else if (title) {
            score += 10;
        }
        
        // Meta description (20 points)
        const description = $('meta[name="description"]').attr('content');
        if (description && description.length >= 120 && description.length <= 160) {
            score += 20;
        } else if (description) {
            score += 10;
        }
        
        // Headings (20 points)
        if ($('h1').length === 1) score += 10;
        if ($('h2').length > 0) score += 10;
        
        // Images with alt text (20 points)
        const images = $('img');
        const imagesWithAlt = $('img[alt]');
        if (images.length > 0 && imagesWithAlt.length === images.length) {
            score += 20;
        } else if (imagesWithAlt.length > 0) {
            score += 10;
        }
        
        // Internal links (10 points)
        if ($('a[href^="/"]').length > 0) score += 10;
        
        // Schema markup (10 points)
        if ($('script[type="application/ld+json"]').length > 0) score += 10;
        
        return score;
    }

    detectCSSFramework(cssContent) {
        if (cssContent.includes('bootstrap')) return 'Bootstrap';
        if (cssContent.includes('tailwind')) return 'Tailwind CSS';
        if (cssContent.includes('foundation')) return 'Foundation';
        if (cssContent.includes('material')) return 'Material Design';
        return 'Custom';
    }

    detectJSFramework(jsContent) {
        if (jsContent.includes('React') || jsContent.includes('react')) return 'React';
        if (jsContent.includes('Vue') || jsContent.includes('vue')) return 'Vue.js';
        if (jsContent.includes('Angular') || jsContent.includes('angular')) return 'Angular';
        if (jsContent.includes('jQuery') || jsContent.includes('$')) return 'jQuery';
        return 'Vanilla JS';
    }

    detectAnalyticsCode(jsContent) {
        const analyticsPatterns = [
            'gtag', 'ga(', 'google-analytics',
            'fbq', '_fbq', 'facebook.com/tr',
            '_linkedin_partner_id', 'snap.tr',
            'ttq.load', 'tiktok_pixel'
        ];
        
        return analyticsPatterns.some(pattern => jsContent.includes(pattern));
    }

    inferJSONDataType(jsonData) {
        if (Array.isArray(jsonData) && jsonData.length > 0) {
            const sample = jsonData[0];
            if (sample.email || sample.phone) return 'contact_list';
            if (sample.price || sample.cost) return 'product_data';
            if (sample.clicks || sample.impressions) return 'analytics_data';
        }
        
        if (typeof jsonData === 'object') {
            const keys = Object.keys(jsonData);
            if (keys.includes('campaigns') || keys.includes('ads')) return 'campaign_data';
            if (keys.includes('users') || keys.includes('customers')) return 'user_data';
        }
        
        return 'unknown';
    }

    async createMarketingAssets(folderId, processedAssets) {
        for (const asset of processedAssets) {
            if (asset.marketingReady) {
                const marketingAsset = {
                    id: uuidv4(),
                    originalAssetId: asset.id,
                    folderId,
                    name: asset.fileName,
                    category: asset.category,
                    marketingUses: asset.marketingUses,
                    tags: asset.tags,
                    optimizedVersions: asset.optimizedVersions,
                    metadata: asset.metadata,
                    usage: {
                        timesUsed: 0,
                        campaigns: [],
                        lastUsed: null,
                        performance: {}
                    },
                    createdAt: new Date(),
                    status: 'available'
                };
                
                this.marketingAssets.set(marketingAsset.id, marketingAsset);
                await this.redis.hset('marketing_assets', marketingAsset.id, JSON.stringify(marketingAsset));
                
                this.emit('marketing_ready', { folderId, asset: marketingAsset });
            }
        }
    }

    async getFolderAssets(folderId) {
        try {
            const exposedFolder = this.exposedFolders.get(folderId) || 
                JSON.parse(await this.redis.hget('exposed_folders', folderId));
            
            if (!exposedFolder) {
                throw new Error(`Exposed folder ${folderId} not found`);
            }
            
            return {
                folder: {
                    id: exposedFolder.id,
                    name: exposedFolder.name,
                    status: exposedFolder.status,
                    processedAt: exposedFolder.processedAt,
                    analytics: exposedFolder.analytics
                },
                assets: exposedFolder.assets,
                marketingAssets: Array.from(this.marketingAssets.values())
                    .filter(asset => asset.folderId === folderId)
            };
        } catch (error) {
            this.logger.error('Failed to get folder assets', { error: error.message, folderId });
            throw error;
        }
    }

    startProcessingWorker() {
        setInterval(async () => {
            if (this.processingQueue.length > 0) {
                const folderId = this.processingQueue.shift();
                try {
                    await this.processFolderContents(folderId);
                } catch (error) {
                    this.logger.error('Processing worker error', { 
                        error: error.message, 
                        folderId 
                    });
                }
            }
        }, 5000); // Process every 5 seconds
    }

    // Event handlers
    handleFolderProcessed(data) {
        this.logger.info('Folder processing completed', {
            folderId: data.folderId,
            assetsProcessed: data.exposedFolder.analytics.processedFiles,
            marketingReady: data.exposedFolder.analytics.marketingReadyAssets
        });
        
        this.io.emit('folder_processing_completed', {
            folderId: data.folderId,
            status: 'completed',
            analytics: data.exposedFolder.analytics
        });
    }

    handleAssetCategorized(data) {
        this.logger.info('Asset categorized', {
            assetId: data.asset.id,
            category: data.category.name,
            marketingUses: data.asset.marketingUses
        });
    }

    handleMarketingReady(data) {
        this.logger.info('Marketing asset ready', {
            assetId: data.asset.id,
            folderId: data.folderId,
            category: data.asset.category
        });
        
        this.io.emit('marketing_asset_ready', {
            folderId: data.folderId,
            asset: {
                id: data.asset.id,
                name: data.asset.name,
                category: data.asset.category,
                marketingUses: data.asset.marketingUses
            }
        });
    }

    handleContentUpdated(data) {
        this.logger.info('Content updated', data);
    }
}

module.exports = ExposedFolderProcessor;