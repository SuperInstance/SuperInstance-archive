const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');
const nodemailer = require('nodemailer');

class EmailCampaignManager extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.campaigns = new Map();
        this.templates = new Map();
        this.lists = new Map();
        this.automations = new Map();
        this.deliveries = new Map();
        this.suppressions = new Map();
        
        this.setupEventHandlers();
        this.initializeEmailProviders();
        this.startAutomationEngine();
        this.startDeliveryProcessor();
    }

    setupEventHandlers() {
        this.on('campaign_created', this.handleCampaignCreated.bind(this));
        this.on('email_sent', this.handleEmailSent.bind(this));
        this.on('email_opened', this.handleEmailOpened.bind(this));
        this.on('email_clicked', this.handleEmailClicked.bind(this));
        this.on('email_bounced', this.handleEmailBounced.bind(this));
        this.on('unsubscribed', this.handleUnsubscribed.bind(this));
    }

    initializeEmailProviders() {
        // Configure different email providers
        this.emailProviders = {
            smtp: {
                name: 'SMTP',
                transporter: nodemailer.createTransporter({
                    host: process.env.SMTP_HOST || 'localhost',
                    port: process.env.SMTP_PORT || 587,
                    secure: false,
                    auth: {
                        user: process.env.SMTP_USER || '',
                        pass: process.env.SMTP_PASS || ''
                    }
                }),
                rateLimit: 100 // emails per minute
            },
            mailchimp: {
                name: 'Mailchimp',
                apiKey: process.env.MAILCHIMP_API_KEY || '',
                rateLimit: 1000
            },
            sendgrid: {
                name: 'SendGrid',
                apiKey: process.env.SENDGRID_API_KEY || '',
                rateLimit: 10000
            },
            ses: {
                name: 'Amazon SES',
                region: process.env.AWS_REGION || 'us-east-1',
                accessKeyId: process.env.AWS_ACCESS_KEY_ID || '',
                secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || '',
                rateLimit: 14 // per second for SES
            }
        };
    }

    async createCampaign(campaignData) {
        try {
            const campaignId = uuidv4();
            const campaign = {
                id: campaignId,
                name: campaignData.name,
                description: campaignData.description || '',
                type: campaignData.type || 'regular', // regular, automated, drip, transactional
                status: 'draft', // draft, scheduled, sending, sent, paused, cancelled
                subject: campaignData.subject || '',
                preheader: campaignData.preheader || '',
                fromName: campaignData.fromName || '',
                fromEmail: campaignData.fromEmail || '',
                replyTo: campaignData.replyTo || campaignData.fromEmail,
                content: {
                    html: campaignData.content?.html || '',
                    text: campaignData.content?.text || '',
                    templateId: campaignData.content?.templateId || null,
                    personalization: campaignData.content?.personalization || {}
                },
                targeting: {
                    lists: campaignData.targeting?.lists || [],
                    segments: campaignData.targeting?.segments || [],
                    filters: campaignData.targeting?.filters || [],
                    excludeLists: campaignData.targeting?.excludeLists || []
                },
                settings: {
                    trackOpens: campaignData.settings?.trackOpens !== false,
                    trackClicks: campaignData.settings?.trackClicks !== false,
                    enableUnsubscribe: campaignData.settings?.enableUnsubscribe !== false,
                    timezone: campaignData.settings?.timezone || 'UTC',
                    emailProvider: campaignData.settings?.emailProvider || 'smtp',
                    testMode: campaignData.settings?.testMode || false
                },
                scheduling: {
                    type: campaignData.scheduling?.type || 'immediate', // immediate, scheduled, optimized, recurring
                    sendDate: campaignData.scheduling?.sendDate || null,
                    optimizeFor: campaignData.scheduling?.optimizeFor || 'opens', // opens, clicks, conversions
                    recurringPattern: campaignData.scheduling?.recurringPattern || null,
                    timeZoneDelivery: campaignData.scheduling?.timeZoneDelivery || false
                },
                abTesting: {
                    enabled: campaignData.abTesting?.enabled || false,
                    testType: campaignData.abTesting?.testType || 'subject', // subject, content, send_time
                    variants: campaignData.abTesting?.variants || [],
                    trafficSplit: campaignData.abTesting?.trafficSplit || 50,
                    testDuration: campaignData.abTesting?.testDuration || 24 // hours
                },
                createdAt: new Date(),
                createdBy: campaignData.createdBy,
                analytics: {
                    recipients: 0,
                    delivered: 0,
                    opens: 0,
                    uniqueOpens: 0,
                    clicks: 0,
                    uniqueClicks: 0,
                    unsubscribes: 0,
                    bounces: 0,
                    complaints: 0,
                    conversions: 0,
                    deliveryRate: 0,
                    openRate: 0,
                    clickRate: 0,
                    clickToOpenRate: 0,
                    conversionRate: 0
                }
            };

            this.campaigns.set(campaignId, campaign);
            await this.redis.hset('email_campaigns', campaignId, JSON.stringify(campaign));
            
            this.logger.info('Email campaign created', { 
                campaignId, 
                name: campaign.name,
                type: campaign.type 
            });
            
            this.io.emit('campaign_created', {
                campaignId,
                name: campaign.name,
                type: campaign.type,
                status: campaign.status
            });
            
            this.emit('campaign_created', campaign);
            
            return { success: true, campaignId, campaign: this.sanitizeCampaignData(campaign) };
        } catch (error) {
            this.logger.error('Failed to create email campaign', { error: error.message, campaignData });
            throw new Error(`Email campaign creation failed: ${error.message}`);
        }
    }

    async createTemplate(templateData) {
        try {
            const templateId = uuidv4();
            const template = {
                id: templateId,
                name: templateData.name,
                description: templateData.description || '',
                category: templateData.category || 'general',
                type: templateData.type || 'html', // html, text, hybrid
                content: {
                    html: templateData.content?.html || '',
                    text: templateData.content?.text || '',
                    css: templateData.content?.css || '',
                    variables: templateData.content?.variables || []
                },
                design: {
                    layout: templateData.design?.layout || 'single-column',
                    colors: templateData.design?.colors || {},
                    fonts: templateData.design?.fonts || {},
                    responsive: templateData.design?.responsive !== false
                },
                personalization: {
                    fields: templateData.personalization?.fields || [],
                    dynamicContent: templateData.personalization?.dynamicContent || [],
                    conditions: templateData.personalization?.conditions || []
                },
                previewSettings: {
                    previewText: templateData.previewSettings?.previewText || '',
                    fallbackText: templateData.previewSettings?.fallbackText || ''
                },
                createdAt: new Date(),
                createdBy: templateData.createdBy,
                lastModified: new Date(),
                status: 'active',
                usage: {
                    timesUsed: 0,
                    campaigns: [],
                    lastUsed: null
                }
            };

            this.templates.set(templateId, template);
            await this.redis.hset('email_templates', templateId, JSON.stringify(template));
            
            this.logger.info('Email template created', { 
                templateId, 
                name: template.name,
                category: template.category 
            });
            
            return { success: true, templateId, template };
        } catch (error) {
            this.logger.error('Failed to create email template', { error: error.message, templateData });
            throw error;
        }
    }

    async createList(listData) {
        try {
            const listId = uuidv4();
            const list = {
                id: listId,
                name: listData.name,
                description: listData.description || '',
                type: listData.type || 'static', // static, dynamic, segment
                source: listData.source || 'manual', // manual, import, api, form
                subscribers: [],
                fields: listData.fields || [
                    { name: 'email', type: 'email', required: true },
                    { name: 'first_name', type: 'text', required: false },
                    { name: 'last_name', type: 'text', required: false }
                ],
                settings: {
                    doubleOptIn: listData.settings?.doubleOptIn !== false,
                    confirmationEmail: listData.settings?.confirmationEmail || null,
                    welcomeEmail: listData.settings?.welcomeEmail || null,
                    unsubscribeUrl: listData.settings?.unsubscribeUrl || '',
                    gdprCompliant: listData.settings?.gdprCompliant !== false
                },
                segmentRules: listData.segmentRules || [],
                createdAt: new Date(),
                createdBy: listData.createdBy,
                analytics: {
                    totalSubscribers: 0,
                    activeSubscribers: 0,
                    unsubscribed: 0,
                    bounced: 0,
                    growthRate: 0,
                    churnRate: 0
                }
            };

            this.lists.set(listId, list);
            await this.redis.hset('email_lists', listId, JSON.stringify(list));
            
            this.logger.info('Email list created', { 
                listId, 
                name: list.name,
                type: list.type 
            });
            
            return { success: true, listId, list };
        } catch (error) {
            this.logger.error('Failed to create email list', { error: error.message, listData });
            throw error;
        }
    }

    async addSubscribers(listId, subscribers) {
        try {
            const list = this.lists.get(listId) || 
                JSON.parse(await this.redis.hget('email_lists', listId));
            
            if (!list) {
                throw new Error(`Email list ${listId} not found`);
            }
            
            const addedSubscribers = [];
            const errors = [];
            
            for (const subscriberData of subscribers) {
                try {
                    // Validate email
                    if (!this.isValidEmail(subscriberData.email)) {
                        errors.push({ email: subscriberData.email, error: 'Invalid email format' });
                        continue;
                    }
                    
                    // Check for existing subscriber
                    const existingIndex = list.subscribers.findIndex(s => s.email === subscriberData.email);
                    
                    const subscriber = {
                        id: uuidv4(),
                        email: subscriberData.email.toLowerCase(),
                        fields: subscriberData.fields || {},
                        status: 'subscribed', // subscribed, unsubscribed, bounced, pending
                        source: subscriberData.source || 'manual',
                        subscribedAt: new Date(),
                        ipAddress: subscriberData.ipAddress || '',
                        doubleOptInConfirmed: !list.settings.doubleOptIn,
                        preferences: subscriberData.preferences || {},
                        tags: subscriberData.tags || []
                    };
                    
                    if (existingIndex >= 0) {
                        // Update existing subscriber
                        list.subscribers[existingIndex] = { ...list.subscribers[existingIndex], ...subscriber };
                        addedSubscribers.push(list.subscribers[existingIndex]);
                    } else {
                        // Add new subscriber
                        list.subscribers.push(subscriber);
                        addedSubscribers.push(subscriber);
                    }
                    
                    // Send double opt-in email if required
                    if (list.settings.doubleOptIn && !subscriber.doubleOptInConfirmed) {
                        await this.sendDoubleOptInEmail(list, subscriber);
                    }
                    
                } catch (error) {
                    errors.push({ email: subscriberData.email, error: error.message });
                }
            }
            
            // Update list analytics
            list.analytics.totalSubscribers = list.subscribers.length;
            list.analytics.activeSubscribers = list.subscribers.filter(s => s.status === 'subscribed').length;
            
            // Save updated list
            this.lists.set(listId, list);
            await this.redis.hset('email_lists', listId, JSON.stringify(list));
            
            this.logger.info('Subscribers added to email list', { 
                listId, 
                added: addedSubscribers.length,
                errors: errors.length 
            });
            
            return { 
                success: true, 
                added: addedSubscribers.length, 
                errors,
                subscribers: addedSubscribers.map(s => ({ id: s.id, email: s.email, status: s.status }))
            };
        } catch (error) {
            this.logger.error('Failed to add subscribers', { error: error.message, listId });
            throw error;
        }
    }

    async sendCampaign(campaignId, options = {}) {
        try {
            const campaign = this.campaigns.get(campaignId) || 
                JSON.parse(await this.redis.hget('email_campaigns', campaignId));
            
            if (!campaign) {
                throw new Error(`Campaign ${campaignId} not found`);
            }
            
            if (campaign.status !== 'draft' && campaign.status !== 'scheduled') {
                throw new Error(`Campaign ${campaignId} cannot be sent from status ${campaign.status}`);
            }
            
            // Get recipients
            const recipients = await this.getRecipients(campaign);
            
            if (recipients.length === 0) {
                throw new Error('No recipients found for campaign');
            }
            
            // Create A/B test variations if enabled
            let variations = [];
            if (campaign.abTesting.enabled) {
                variations = await this.createABTestVariations(campaign, recipients);
            } else {
                variations = [{
                    id: uuidv4(),
                    name: 'Main',
                    recipients,
                    campaign
                }];
            }
            
            // Update campaign status
            campaign.status = 'sending';
            campaign.analytics.recipients = recipients.length;
            campaign.sentAt = new Date();
            
            await this.redis.hset('email_campaigns', campaignId, JSON.stringify(campaign));
            
            // Queue emails for delivery
            const deliveryId = uuidv4();
            const delivery = {
                id: deliveryId,
                campaignId,
                variations,
                totalEmails: recipients.length,
                sentEmails: 0,
                status: 'queued',
                startedAt: new Date(),
                provider: campaign.settings.emailProvider
            };
            
            this.deliveries.set(deliveryId, delivery);
            await this.redis.hset('email_deliveries', deliveryId, JSON.stringify(delivery));
            
            // Start delivery process
            await this.processDelivery(deliveryId);
            
            this.logger.info('Email campaign sending started', { 
                campaignId, 
                deliveryId,
                recipients: recipients.length,
                variations: variations.length
            });
            
            this.io.emit('campaign_sending_started', {
                campaignId,
                deliveryId,
                recipients: recipients.length,
                estimatedDuration: Math.ceil(recipients.length / this.getProviderRateLimit(campaign.settings.emailProvider))
            });
            
            return { 
                success: true, 
                deliveryId, 
                recipients: recipients.length,
                variations: variations.length
            };
        } catch (error) {
            this.logger.error('Failed to send campaign', { error: error.message, campaignId });
            throw error;
        }
    }

    async getRecipients(campaign) {
        const recipients = new Set();
        
        // Add recipients from lists
        for (const listId of campaign.targeting.lists) {
            const list = this.lists.get(listId) || 
                JSON.parse(await this.redis.hget('email_lists', listId));
            
            if (list) {
                for (const subscriber of list.subscribers) {
                    if (subscriber.status === 'subscribed' && 
                        !this.isEmailSuppressed(subscriber.email)) {
                        recipients.add(subscriber);
                    }
                }
            }
        }
        
        // Remove excluded recipients
        for (const excludeListId of campaign.targeting.excludeLists) {
            const excludeList = this.lists.get(excludeListId);
            if (excludeList) {
                for (const subscriber of excludeList.subscribers) {
                    // Find and remove from recipients
                    for (const recipient of recipients) {
                        if (recipient.email === subscriber.email) {
                            recipients.delete(recipient);
                            break;
                        }
                    }
                }
            }
        }
        
        // Apply filters
        let filteredRecipients = Array.from(recipients);
        
        for (const filter of campaign.targeting.filters) {
            filteredRecipients = this.applyFilter(filteredRecipients, filter);
        }
        
        return filteredRecipients;
    }

    async processDelivery(deliveryId) {
        try {
            const delivery = this.deliveries.get(deliveryId);
            if (!delivery) return;
            
            delivery.status = 'sending';
            
            const provider = this.emailProviders[delivery.provider];
            const rateLimit = provider.rateLimit;
            const batchSize = Math.min(rateLimit, 50); // Process in batches
            
            for (const variation of delivery.variations) {
                const batches = this.chunkArray(variation.recipients, batchSize);
                
                for (const batch of batches) {
                    await this.sendEmailBatch(batch, variation.campaign, variation.id);
                    delivery.sentEmails += batch.length;
                    
                    // Rate limiting
                    await this.sleep(60000 / rateLimit * batch.length);
                    
                    // Update progress
                    this.io.emit('delivery_progress', {
                        deliveryId,
                        campaignId: delivery.campaignId,
                        progress: delivery.sentEmails / delivery.totalEmails,
                        sentEmails: delivery.sentEmails,
                        totalEmails: delivery.totalEmails
                    });
                }
            }
            
            delivery.status = 'completed';
            delivery.completedAt = new Date();
            
            // Update campaign status
            const campaign = this.campaigns.get(delivery.campaignId);
            if (campaign) {
                campaign.status = 'sent';
                await this.redis.hset('email_campaigns', campaign.id, JSON.stringify(campaign));
            }
            
            this.logger.info('Email delivery completed', { 
                deliveryId, 
                campaignId: delivery.campaignId,
                totalSent: delivery.sentEmails 
            });
            
        } catch (error) {
            this.logger.error('Email delivery failed', { error: error.message, deliveryId });
        }
    }

    async sendEmailBatch(recipients, campaign, variationId) {
        const provider = this.emailProviders[campaign.settings.emailProvider];
        
        for (const recipient of recipients) {
            try {
                // Personalize email content
                const personalizedContent = await this.personalizeEmail(campaign, recipient);
                
                // Add tracking pixels and links
                const trackedContent = await this.addTracking(personalizedContent, campaign.id, recipient.id, variationId);
                
                // Send email based on provider
                await this.sendEmail(provider, {
                    to: recipient.email,
                    from: {
                        name: campaign.fromName,
                        email: campaign.fromEmail
                    },
                    replyTo: campaign.replyTo,
                    subject: personalizedContent.subject,
                    html: trackedContent.html,
                    text: trackedContent.text,
                    headers: {
                        'X-Campaign-ID': campaign.id,
                        'X-Recipient-ID': recipient.id,
                        'X-Variation-ID': variationId
                    }
                });
                
                // Track email sent
                await this.trackEmailSent(campaign.id, recipient.id, variationId);
                
                this.emit('email_sent', {
                    campaignId: campaign.id,
                    recipientId: recipient.id,
                    email: recipient.email,
                    variationId
                });
                
            } catch (error) {
                this.logger.error('Failed to send email', { 
                    error: error.message, 
                    campaignId: campaign.id,
                    recipientEmail: recipient.email 
                });
            }
        }
    }

    async personalizeEmail(campaign, recipient) {
        let subject = campaign.subject;
        let html = campaign.content.html;
        let text = campaign.content.text;
        
        // Replace personalization tokens
        const personalizations = {
            '{{first_name}}': recipient.fields.first_name || '',
            '{{last_name}}': recipient.fields.last_name || '',
            '{{email}}': recipient.email,
            '{{full_name}}': `${recipient.fields.first_name || ''} ${recipient.fields.last_name || ''}`.trim(),
            ...campaign.content.personalization
        };
        
        for (const [token, value] of Object.entries(personalizations)) {
            subject = subject.replace(new RegExp(token, 'g'), value);
            html = html.replace(new RegExp(token, 'g'), value);
            text = text.replace(new RegExp(token, 'g'), value);
        }
        
        return { subject, html, text };
    }

    async addTracking(content, campaignId, recipientId, variationId) {
        const trackingId = uuidv4();
        const baseUrl = process.env.BASE_URL || 'http://localhost:8313';
        
        // Add open tracking pixel
        const openTrackingPixel = `<img src="${baseUrl}/api/email/track/open/${trackingId}" width="1" height="1" style="display:none;">`;
        
        let html = content.html;
        let text = content.text;
        
        // Add pixel to HTML
        if (html.includes('</body>')) {
            html = html.replace('</body>', `${openTrackingPixel}</body>`);
        } else {
            html += openTrackingPixel;
        }
        
        // Track click tracking
        const linkRegex = /<a[^>]+href="([^"]+)"[^>]*>/g;
        html = html.replace(linkRegex, (match, url) => {
            const trackedUrl = `${baseUrl}/api/email/track/click/${trackingId}?url=${encodeURIComponent(url)}`;
            return match.replace(url, trackedUrl);
        });
        
        // Store tracking information
        await this.redis.hset('email_tracking', trackingId, JSON.stringify({
            campaignId,
            recipientId,
            variationId,
            createdAt: new Date()
        }));
        
        return { html, text };
    }

    async sendEmail(provider, emailData) {
        switch (provider.name) {
            case 'SMTP':
                return await provider.transporter.sendMail({
                    from: `"${emailData.from.name}" <${emailData.from.email}>`,
                    to: emailData.to,
                    replyTo: emailData.replyTo,
                    subject: emailData.subject,
                    html: emailData.html,
                    text: emailData.text,
                    headers: emailData.headers
                });
            
            case 'SendGrid':
                // SendGrid API implementation would go here
                break;
            
            case 'Mailchimp':
                // Mailchimp API implementation would go here
                break;
            
            default:
                throw new Error(`Unsupported email provider: ${provider.name}`);
        }
    }

    async trackEmailOpen(trackingId) {
        try {
            const trackingData = await this.redis.hget('email_tracking', trackingId);
            if (!trackingData) return;
            
            const tracking = JSON.parse(trackingData);
            
            // Record open event
            const openEvent = {
                id: uuidv4(),
                trackingId,
                campaignId: tracking.campaignId,
                recipientId: tracking.recipientId,
                variationId: tracking.variationId,
                type: 'open',
                timestamp: new Date(),
                userAgent: '',
                ipAddress: ''
            };
            
            await this.redis.lpush(`email_events:${tracking.campaignId}`, JSON.stringify(openEvent));
            
            // Update campaign analytics
            await this.updateCampaignAnalytics(tracking.campaignId, 'open');
            
            this.emit('email_opened', openEvent);
            
            return openEvent;
        } catch (error) {
            this.logger.error('Failed to track email open', { error: error.message, trackingId });
        }
    }

    async trackEmailClick(trackingId, clickedUrl) {
        try {
            const trackingData = await this.redis.hget('email_tracking', trackingId);
            if (!trackingData) return;
            
            const tracking = JSON.parse(trackingData);
            
            // Record click event
            const clickEvent = {
                id: uuidv4(),
                trackingId,
                campaignId: tracking.campaignId,
                recipientId: tracking.recipientId,
                variationId: tracking.variationId,
                type: 'click',
                url: clickedUrl,
                timestamp: new Date(),
                userAgent: '',
                ipAddress: ''
            };
            
            await this.redis.lpush(`email_events:${tracking.campaignId}`, JSON.stringify(clickEvent));
            
            // Update campaign analytics
            await this.updateCampaignAnalytics(tracking.campaignId, 'click');
            
            this.emit('email_clicked', clickEvent);
            
            return clickEvent;
        } catch (error) {
            this.logger.error('Failed to track email click', { error: error.message, trackingId });
        }
    }

    async getCampaignAnalytics(campaignId) {
        try {
            const campaign = this.campaigns.get(campaignId) || 
                JSON.parse(await this.redis.hget('email_campaigns', campaignId));
            
            if (!campaign) {
                throw new Error(`Campaign ${campaignId} not found`);
            }
            
            // Get events for detailed analysis
            const events = await this.redis.lrange(`email_events:${campaignId}`, 0, -1);
            const parsedEvents = events.map(e => JSON.parse(e));
            
            // Calculate analytics
            const opens = parsedEvents.filter(e => e.type === 'open');
            const clicks = parsedEvents.filter(e => e.type === 'click');
            const uniqueOpens = new Set(opens.map(e => e.recipientId)).size;
            const uniqueClicks = new Set(clicks.map(e => e.recipientId)).size;
            
            const analytics = {
                ...campaign.analytics,
                opens: opens.length,
                clicks: clicks.length,
                uniqueOpens,
                uniqueClicks,
                openRate: campaign.analytics.recipients > 0 ? uniqueOpens / campaign.analytics.recipients : 0,
                clickRate: campaign.analytics.recipients > 0 ? uniqueClicks / campaign.analytics.recipients : 0,
                clickToOpenRate: uniqueOpens > 0 ? uniqueClicks / uniqueOpens : 0
            };
            
            // Time-based analytics
            const hourlyStats = this.generateHourlyStats(parsedEvents);
            const deviceStats = this.generateDeviceStats(parsedEvents);
            const locationStats = this.generateLocationStats(parsedEvents);
            
            return {
                campaign: {
                    id: campaign.id,
                    name: campaign.name,
                    status: campaign.status,
                    sentAt: campaign.sentAt
                },
                analytics,
                timeline: hourlyStats,
                devices: deviceStats,
                locations: locationStats,
                topLinks: this.getTopClickedLinks(clicks),
                unsubscribes: campaign.analytics.unsubscribes,
                bounces: campaign.analytics.bounces
            };
        } catch (error) {
            this.logger.error('Failed to get campaign analytics', { error: error.message, campaignId });
            throw error;
        }
    }

    // Helper methods
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    isEmailSuppressed(email) {
        return this.suppressions.has(email.toLowerCase());
    }

    applyFilter(recipients, filter) {
        switch (filter.type) {
            case 'field_equals':
                return recipients.filter(r => r.fields[filter.field] === filter.value);
            case 'field_contains':
                return recipients.filter(r => r.fields[filter.field]?.includes(filter.value));
            case 'tag':
                return recipients.filter(r => r.tags?.includes(filter.value));
            default:
                return recipients;
        }
    }

    chunkArray(array, size) {
        const chunks = [];
        for (let i = 0; i < array.length; i += size) {
            chunks.push(array.slice(i, i + size));
        }
        return chunks;
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    getProviderRateLimit(providerName) {
        return this.emailProviders[providerName]?.rateLimit || 100;
    }

    startAutomationEngine() {
        // Check for automated campaigns every 5 minutes
        setInterval(async () => {
            try {
                await this.processAutomations();
            } catch (error) {
                this.logger.error('Automation engine error', { error: error.message });
            }
        }, 5 * 60 * 1000);
    }

    startDeliveryProcessor() {
        // Process pending deliveries every minute
        setInterval(async () => {
            try {
                await this.processDeliveries();
            } catch (error) {
                this.logger.error('Delivery processor error', { error: error.message });
            }
        }, 60 * 1000);
    }

    async getOverallStats() {
        const totalCampaigns = this.campaigns.size;
        const activeCampaigns = Array.from(this.campaigns.values()).filter(c => c.status === 'sending').length;
        const totalLists = this.lists.size;
        
        let totalSubscribers = 0;
        let totalEmailsSent = 0;
        let totalOpens = 0;
        let totalClicks = 0;
        
        for (const list of this.lists.values()) {
            totalSubscribers += list.analytics.totalSubscribers;
        }
        
        for (const campaign of this.campaigns.values()) {
            totalEmailsSent += campaign.analytics.recipients;
            totalOpens += campaign.analytics.opens;
            totalClicks += campaign.analytics.clicks;
        }
        
        return {
            totalCampaigns,
            activeCampaigns,
            totalLists,
            totalSubscribers,
            totalEmailsSent,
            totalOpens,
            totalClicks,
            overallOpenRate: totalEmailsSent > 0 ? totalOpens / totalEmailsSent : 0,
            overallClickRate: totalEmailsSent > 0 ? totalClicks / totalEmailsSent : 0
        };
    }

    // Event handlers
    handleCampaignCreated(campaign) {
        this.logger.info('Email campaign created and configured', {
            campaignId: campaign.id,
            name: campaign.name,
            type: campaign.type
        });
    }

    handleEmailSent(data) {
        this.logger.info('Email sent successfully', {
            campaignId: data.campaignId,
            recipientEmail: data.email
        });
    }

    handleEmailOpened(event) {
        this.logger.info('Email opened', {
            campaignId: event.campaignId,
            recipientId: event.recipientId
        });
    }

    handleEmailClicked(event) {
        this.logger.info('Email link clicked', {
            campaignId: event.campaignId,
            recipientId: event.recipientId,
            url: event.url
        });
    }

    handleEmailBounced(event) {
        this.logger.warn('Email bounced', {
            campaignId: event.campaignId,
            recipientId: event.recipientId,
            reason: event.reason
        });
    }

    handleUnsubscribed(event) {
        this.logger.info('Recipient unsubscribed', {
            email: event.email,
            campaignId: event.campaignId
        });
    }

    // Data sanitization
    sanitizeCampaignData(campaign) {
        return {
            ...campaign,
            // Remove sensitive data if needed
        };
    }
}

module.exports = EmailCampaignManager;