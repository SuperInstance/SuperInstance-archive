const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');
const crypto = require('crypto');

class AffiliateTracker extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.affiliates = new Map();
        this.programs = new Map();
        this.clicks = new Map();
        this.conversions = new Map();
        this.commissions = new Map();
        this.payouts = new Map();
        this.fraudDetection = new Map();
        
        this.setupEventHandlers();
        this.startFraudDetection();
        this.startCommissionCalculation();
        this.initializeAttributionModels();
    }

    setupEventHandlers() {
        this.on('affiliate_registered', this.handleAffiliateRegistered.bind(this));
        this.on('click_tracked', this.handleClickTracked.bind(this));
        this.on('conversion_tracked', this.handleConversionTracked.bind(this));
        this.on('fraud_detected', this.handleFraudDetected.bind(this));
        this.on('commission_calculated', this.handleCommissionCalculated.bind(this));
    }

    initializeAttributionModels() {
        this.attributionModels = {
            'first_click': {
                name: 'First Click',
                description: 'Credits the first affiliate click',
                calculate: (clicks) => clicks.length > 0 ? [{ ...clicks[0], weight: 1.0 }] : []
            },
            'last_click': {
                name: 'Last Click',
                description: 'Credits the last affiliate click',
                calculate: (clicks) => clicks.length > 0 ? [{ ...clicks[clicks.length - 1], weight: 1.0 }] : []
            },
            'linear': {
                name: 'Linear Attribution',
                description: 'Credits all clicks equally',
                calculate: (clicks) => clicks.map(click => ({ ...click, weight: 1.0 / clicks.length }))
            },
            'time_decay': {
                name: 'Time Decay',
                description: 'Credits recent clicks more heavily',
                calculate: (clicks) => {
                    if (clicks.length === 0) return [];
                    const now = Date.now();
                    const totalWeight = clicks.reduce((sum, click) => {
                        const age = now - new Date(click.timestamp).getTime();
                        return sum + Math.exp(-age / (7 * 24 * 60 * 60 * 1000)); // 7 day half-life
                    }, 0);
                    return clicks.map(click => {
                        const age = now - new Date(click.timestamp).getTime();
                        const weight = Math.exp(-age / (7 * 24 * 60 * 60 * 1000)) / totalWeight;
                        return { ...click, weight };
                    });
                }
            }
        };
    }

    async registerAffiliate(affiliateData) {
        try {
            const affiliateId = uuidv4();
            const affiliate = {
                id: affiliateId,
                email: affiliateData.email,
                name: affiliateData.name || '',
                company: affiliateData.company || '',
                website: affiliateData.website || '',
                phone: affiliateData.phone || '',
                address: affiliateData.address || {},
                taxInfo: {
                    taxId: affiliateData.taxInfo?.taxId || '',
                    vatNumber: affiliateData.taxInfo?.vatNumber || '',
                    w9Submitted: false,
                    requiresTax: affiliateData.taxInfo?.requiresTax || false
                },
                paymentInfo: {
                    method: affiliateData.paymentInfo?.method || 'bank_transfer',
                    bankAccount: affiliateData.paymentInfo?.bankAccount || {},
                    paypalEmail: affiliateData.paymentInfo?.paypalEmail || '',
                    minimumPayout: affiliateData.paymentInfo?.minimumPayout || 50
                },
                status: 'pending', // pending, active, suspended, banned
                tier: affiliateData.tier || 'bronze',
                referralCode: this.generateReferralCode(affiliateData.name || affiliateData.email),
                trackingLinks: {},
                performance: {
                    totalClicks: 0,
                    totalConversions: 0,
                    totalRevenue: 0,
                    totalCommissions: 0,
                    conversionRate: 0,
                    averageOrderValue: 0,
                    clickThroughRate: 0
                },
                createdAt: new Date(),
                approvedAt: null,
                lastActive: null,
                fraudScore: 0,
                notes: affiliateData.notes || '',
                programs: [], // Program IDs they're enrolled in
                customFields: affiliateData.customFields || {}
            };

            // Generate tracking links for default program
            if (affiliateData.programId) {
                affiliate.trackingLinks[affiliateData.programId] = this.generateTrackingLink(
                    affiliateId, 
                    affiliateData.programId
                );
                affiliate.programs.push(affiliateData.programId);
            }

            this.affiliates.set(affiliateId, affiliate);
            await this.redis.hset('affiliates', affiliateId, JSON.stringify(affiliate));
            
            this.logger.info('Affiliate registered', { 
                affiliateId, 
                email: affiliate.email,
                referralCode: affiliate.referralCode 
            });
            
            this.io.emit('affiliate_registered', {
                affiliateId,
                email: affiliate.email,
                referralCode: affiliate.referralCode,
                status: affiliate.status
            });
            
            this.emit('affiliate_registered', affiliate);
            
            return { 
                success: true, 
                affiliateId, 
                affiliate: this.sanitizeAffiliateData(affiliate) 
            };
        } catch (error) {
            this.logger.error('Failed to register affiliate', { error: error.message, affiliateData });
            throw new Error(`Affiliate registration failed: ${error.message}`);
        }
    }

    async createProgram(programData) {
        try {
            const programId = uuidv4();
            const program = {
                id: programId,
                name: programData.name,
                description: programData.description || '',
                type: programData.type || 'standard', // standard, influencer, enterprise
                status: 'active',
                commissionStructure: {
                    type: programData.commissionStructure?.type || 'percentage', // percentage, fixed, tiered
                    rate: programData.commissionStructure?.rate || 5, // 5%
                    tiers: programData.commissionStructure?.tiers || [],
                    bonuses: programData.commissionStructure?.bonuses || []
                },
                cookieWindow: programData.cookieWindow || 30, // days
                attributionModel: programData.attributionModel || 'last_click',
                targetAudience: programData.targetAudience || [],
                allowedTrafficSources: programData.allowedTrafficSources || ['all'],
                restrictions: {
                    geoRestrictions: programData.restrictions?.geoRestrictions || [],
                    deviceRestrictions: programData.restrictions?.deviceRestrictions || [],
                    timeRestrictions: programData.restrictions?.timeRestrictions || null
                },
                payoutSchedule: {
                    frequency: programData.payoutSchedule?.frequency || 'monthly', // weekly, biweekly, monthly
                    minimumPayout: programData.payoutSchedule?.minimumPayout || 50,
                    holdingPeriod: programData.payoutSchedule?.holdingPeriod || 30 // days
                },
                fraudProtection: {
                    enabled: true,
                    maxClicksPerHour: programData.fraudProtection?.maxClicksPerHour || 100,
                    maxConversionsPerDay: programData.fraudProtection?.maxConversionsPerDay || 50,
                    requireUniqueIPs: programData.fraudProtection?.requireUniqueIPs !== false,
                    blockVPN: programData.fraudProtection?.blockVPN || false
                },
                createdAt: new Date(),
                createdBy: programData.createdBy,
                affiliateCount: 0,
                performance: {
                    totalClicks: 0,
                    totalConversions: 0,
                    totalRevenue: 0,
                    totalCommissions: 0,
                    conversionRate: 0
                }
            };

            this.programs.set(programId, program);
            await this.redis.hset('affiliate_programs', programId, JSON.stringify(program));
            
            this.logger.info('Affiliate program created', { 
                programId, 
                name: program.name 
            });
            
            return { success: true, programId, program };
        } catch (error) {
            this.logger.error('Failed to create program', { error: error.message, programData });
            throw new Error(`Program creation failed: ${error.message}`);
        }
    }

    async trackClick(clickData) {
        try {
            const clickId = uuidv4();
            const timestamp = new Date();
            
            // Decode tracking link to get affiliate and program info
            const trackingInfo = this.decodeTrackingLink(clickData.trackingLink || clickData.affiliateCode);
            
            if (!trackingInfo) {
                throw new Error('Invalid tracking link or affiliate code');
            }
            
            const affiliate = this.affiliates.get(trackingInfo.affiliateId);
            const program = this.programs.get(trackingInfo.programId);
            
            if (!affiliate || !program) {
                throw new Error('Affiliate or program not found');
            }
            
            // Check for fraud
            const fraudCheck = await this.checkForFraud(trackingInfo.affiliateId, clickData);
            if (fraudCheck.isFraud) {
                this.logger.warn('Fraudulent click detected', { 
                    clickId, 
                    affiliateId: trackingInfo.affiliateId,
                    reason: fraudCheck.reason 
                });
                
                this.emit('fraud_detected', {
                    type: 'click',
                    affiliateId: trackingInfo.affiliateId,
                    clickId,
                    reason: fraudCheck.reason,
                    data: clickData
                });
                
                return { success: false, reason: 'Fraudulent click detected' };
            }
            
            const click = {
                id: clickId,
                affiliateId: trackingInfo.affiliateId,
                programId: trackingInfo.programId,
                sessionId: this.generateSessionId(clickData),
                timestamp,
                ipAddress: clickData.ipAddress || '',
                userAgent: clickData.userAgent || '',
                referrer: clickData.referrer || '',
                landingPage: clickData.landingPage || '',
                location: {
                    country: clickData.location?.country || '',
                    region: clickData.location?.region || '',
                    city: clickData.location?.city || ''
                },
                device: {
                    type: clickData.device?.type || 'desktop',
                    os: clickData.device?.os || '',
                    browser: clickData.device?.browser || ''
                },
                source: clickData.source || 'direct',
                medium: clickData.medium || 'affiliate',
                campaign: clickData.campaign || '',
                keywords: clickData.keywords || [],
                customParameters: clickData.customParameters || {},
                converted: false,
                conversionId: null,
                fraudScore: fraudCheck.score || 0
            };

            this.clicks.set(clickId, click);
            await this.redis.hset('affiliate_clicks', clickId, JSON.stringify(click));
            
            // Set cookie for conversion tracking
            await this.setTrackingCookie(clickId, trackingInfo, program.cookieWindow);
            
            // Update affiliate performance
            affiliate.performance.totalClicks++;
            affiliate.lastActive = timestamp;
            await this.redis.hset('affiliates', affiliate.id, JSON.stringify(affiliate));
            
            // Update program performance
            program.performance.totalClicks++;
            await this.redis.hset('affiliate_programs', program.id, JSON.stringify(program));
            
            this.logger.info('Click tracked', { 
                clickId, 
                affiliateId: trackingInfo.affiliateId,
                programId: trackingInfo.programId 
            });
            
            this.io.to(`affiliate_${trackingInfo.affiliateId}`).emit('click_tracked', {
                clickId,
                timestamp,
                source: click.source,
                landingPage: click.landingPage
            });
            
            this.emit('click_tracked', click);
            
            return { 
                success: true, 
                clickId, 
                sessionId: click.sessionId,
                redirectUrl: clickData.destinationUrl || '/'
            };
        } catch (error) {
            this.logger.error('Failed to track click', { error: error.message, clickData });
            throw new Error(`Click tracking failed: ${error.message}`);
        }
    }

    async trackConversion(conversionData) {
        try {
            const conversionId = uuidv4();
            const timestamp = new Date();
            
            // Find associated clicks using session ID or tracking cookie
            const associatedClicks = await this.findAssociatedClicks(
                conversionData.sessionId || conversionData.userId,
                conversionData.orderId
            );
            
            if (associatedClicks.length === 0) {
                return { success: false, reason: 'No associated affiliate clicks found' };
            }
            
            // Apply attribution model
            const program = this.programs.get(associatedClicks[0].programId);
            const attributionModel = this.attributionModels[program.attributionModel];
            const attributedClicks = attributionModel.calculate(associatedClicks);
            
            const conversion = {
                id: conversionId,
                orderId: conversionData.orderId,
                customerId: conversionData.customerId || '',
                sessionId: conversionData.sessionId || '',
                timestamp,
                orderValue: conversionData.orderValue || 0,
                currency: conversionData.currency || 'USD',
                products: conversionData.products || [],
                couponCode: conversionData.couponCode || '',
                discountAmount: conversionData.discountAmount || 0,
                shippingAmount: conversionData.shippingAmount || 0,
                taxAmount: conversionData.taxAmount || 0,
                netRevenue: (conversionData.orderValue || 0) - (conversionData.discountAmount || 0),
                attributedClicks,
                commissions: [],
                status: 'pending', // pending, approved, rejected, paid
                fraudScore: 0
            };

            // Check for conversion fraud
            const fraudCheck = await this.checkConversionFraud(conversion, associatedClicks);
            conversion.fraudScore = fraudCheck.score;
            
            if (fraudCheck.isFraud) {
                conversion.status = 'rejected';
                this.logger.warn('Fraudulent conversion detected', { 
                    conversionId, 
                    reason: fraudCheck.reason 
                });
                
                this.emit('fraud_detected', {
                    type: 'conversion',
                    conversionId,
                    reason: fraudCheck.reason,
                    data: conversionData
                });
            }
            
            this.conversions.set(conversionId, conversion);
            await this.redis.hset('affiliate_conversions', conversionId, JSON.stringify(conversion));
            
            // Mark associated clicks as converted
            for (const click of associatedClicks) {
                click.converted = true;
                click.conversionId = conversionId;
                await this.redis.hset('affiliate_clicks', click.id, JSON.stringify(click));
            }
            
            // Calculate commissions
            if (!fraudCheck.isFraud) {
                await this.calculateCommissions(conversion, program);
            }
            
            this.logger.info('Conversion tracked', { 
                conversionId, 
                orderId: conversion.orderId,
                orderValue: conversion.orderValue,
                attributedClicks: attributedClicks.length 
            });
            
            // Notify affiliates
            for (const click of attributedClicks) {
                this.io.to(`affiliate_${click.affiliateId}`).emit('conversion_tracked', {
                    conversionId,
                    orderId: conversion.orderId,
                    orderValue: conversion.orderValue,
                    weight: click.weight
                });
            }
            
            this.emit('conversion_tracked', conversion);
            
            return { 
                success: true, 
                conversionId,
                conversion: this.sanitizeConversionData(conversion)
            };
        } catch (error) {
            this.logger.error('Failed to track conversion', { error: error.message, conversionData });
            throw new Error(`Conversion tracking failed: ${error.message}`);
        }
    }

    async calculateCommissions(conversion, program) {
        try {
            for (const attributedClick of conversion.attributedClicks) {
                const affiliate = this.affiliates.get(attributedClick.affiliateId);
                if (!affiliate) continue;
                
                let commissionAmount = 0;
                
                // Calculate commission based on structure type
                switch (program.commissionStructure.type) {
                    case 'percentage':
                        commissionAmount = (conversion.netRevenue * program.commissionStructure.rate / 100) * attributedClick.weight;
                        break;
                    case 'fixed':
                        commissionAmount = program.commissionStructure.rate * attributedClick.weight;
                        break;
                    case 'tiered':
                        commissionAmount = this.calculateTieredCommission(
                            affiliate, 
                            conversion.netRevenue, 
                            program.commissionStructure.tiers,
                            attributedClick.weight
                        );
                        break;
                }
                
                // Apply bonuses
                const bonusAmount = this.calculateBonuses(
                    affiliate, 
                    conversion, 
                    program.commissionStructure.bonuses
                );
                
                const commission = {
                    id: uuidv4(),
                    affiliateId: attributedClick.affiliateId,
                    conversionId: conversion.id,
                    clickId: attributedClick.id,
                    programId: program.id,
                    amount: commissionAmount,
                    bonusAmount,
                    totalAmount: commissionAmount + bonusAmount,
                    currency: conversion.currency,
                    rate: program.commissionStructure.rate,
                    weight: attributedClick.weight,
                    status: 'pending', // pending, approved, rejected, paid
                    createdAt: new Date(),
                    payoutDate: moment().add(program.payoutSchedule.holdingPeriod, 'days').toDate(),
                    metadata: {
                        orderValue: conversion.orderValue,
                        netRevenue: conversion.netRevenue,
                        commissionType: program.commissionStructure.type
                    }
                };
                
                this.commissions.set(commission.id, commission);
                await this.redis.hset('affiliate_commissions', commission.id, JSON.stringify(commission));
                
                conversion.commissions.push(commission.id);
                
                // Update affiliate performance
                affiliate.performance.totalCommissions += commission.totalAmount;
                affiliate.performance.totalRevenue += conversion.netRevenue * attributedClick.weight;
                affiliate.performance.totalConversions++;
                affiliate.performance.conversionRate = 
                    affiliate.performance.totalConversions / Math.max(affiliate.performance.totalClicks, 1);
                affiliate.performance.averageOrderValue = 
                    affiliate.performance.totalRevenue / Math.max(affiliate.performance.totalConversions, 1);
                
                await this.redis.hset('affiliates', affiliate.id, JSON.stringify(affiliate));
                
                this.emit('commission_calculated', {
                    commission,
                    affiliate,
                    conversion
                });
            }
            
            // Update conversion with commission IDs
            await this.redis.hset('affiliate_conversions', conversion.id, JSON.stringify(conversion));
            
            // Update program performance
            program.performance.totalConversions++;
            program.performance.totalRevenue += conversion.netRevenue;
            program.performance.totalCommissions += conversion.commissions.reduce((sum, commId) => {
                const comm = this.commissions.get(commId);
                return sum + (comm ? comm.totalAmount : 0);
            }, 0);
            program.performance.conversionRate = 
                program.performance.totalConversions / Math.max(program.performance.totalClicks, 1);
            
            await this.redis.hset('affiliate_programs', program.id, JSON.stringify(program));
            
        } catch (error) {
            this.logger.error('Commission calculation failed', { 
                error: error.message, 
                conversionId: conversion.id 
            });
        }
    }

    calculateTieredCommission(affiliate, orderValue, tiers, weight) {
        // Find appropriate tier based on affiliate performance
        const totalRevenue = affiliate.performance.totalRevenue;
        
        let applicableTier = tiers[0]; // Default to first tier
        for (const tier of tiers) {
            if (totalRevenue >= tier.threshold) {
                applicableTier = tier;
            } else {
                break;
            }
        }
        
        return (orderValue * applicableTier.rate / 100) * weight;
    }

    calculateBonuses(affiliate, conversion, bonuses) {
        let totalBonus = 0;
        
        for (const bonus of bonuses) {
            switch (bonus.type) {
                case 'first_conversion':
                    if (affiliate.performance.totalConversions === 0) {
                        totalBonus += bonus.amount;
                    }
                    break;
                case 'volume_bonus':
                    if (conversion.orderValue >= bonus.threshold) {
                        totalBonus += bonus.amount;
                    }
                    break;
                case 'milestone_bonus':
                    if (affiliate.performance.totalConversions + 1 === bonus.conversionCount) {
                        totalBonus += bonus.amount;
                    }
                    break;
            }
        }
        
        return totalBonus;
    }

    async checkForFraud(affiliateId, clickData) {
        let fraudScore = 0;
        const reasons = [];
        
        // Check click frequency
        const recentClicks = await this.getRecentClicks(affiliateId, 1); // Last hour
        if (recentClicks.length > 50) {
            fraudScore += 30;
            reasons.push('High click frequency');
        }
        
        // Check IP diversity
        const uniqueIPs = new Set(recentClicks.map(c => c.ipAddress));
        if (uniqueIPs.size < Math.max(recentClicks.length * 0.1, 1)) {
            fraudScore += 20;
            reasons.push('Low IP diversity');
        }
        
        // Check for bot-like patterns
        if (clickData.userAgent && this.isBotUserAgent(clickData.userAgent)) {
            fraudScore += 40;
            reasons.push('Bot-like user agent');
        }
        
        // Check referrer
        if (!clickData.referrer || clickData.referrer === clickData.landingPage) {
            fraudScore += 10;
            reasons.push('Missing or suspicious referrer');
        }
        
        return {
            score: fraudScore,
            isFraud: fraudScore >= 60,
            reason: reasons.join(', ')
        };
    }

    async checkConversionFraud(conversion, clicks) {
        let fraudScore = 0;
        const reasons = [];
        
        // Check time between click and conversion
        const firstClick = clicks[0];
        const timeDiff = conversion.timestamp - new Date(firstClick.timestamp);
        if (timeDiff < 30000) { // Less than 30 seconds
            fraudScore += 25;
            reasons.push('Conversion too soon after click');
        }
        
        // Check order value reasonableness
        if (conversion.orderValue > 10000) {
            fraudScore += 15;
            reasons.push('Unusually high order value');
        }
        
        // Check for duplicate orders
        const existingConversions = Array.from(this.conversions.values())
            .filter(c => c.customerId === conversion.customerId && 
                        Math.abs(c.orderValue - conversion.orderValue) < 0.01);
        
        if (existingConversions.length > 0) {
            fraudScore += 35;
            reasons.push('Duplicate conversion detected');
        }
        
        return {
            score: fraudScore,
            isFraud: fraudScore >= 50,
            reason: reasons.join(', ')
        };
    }

    async getAffiliatePerformance(affiliateId) {
        try {
            const affiliate = this.affiliates.get(affiliateId) || 
                JSON.parse(await this.redis.hget('affiliates', affiliateId));
            
            if (!affiliate) {
                throw new Error(`Affiliate ${affiliateId} not found`);
            }
            
            // Get recent performance data
            const recentClicks = await this.getRecentClicks(affiliateId, 30 * 24); // Last 30 days
            const recentConversions = await this.getRecentConversions(affiliateId, 30 * 24);
            
            // Calculate period-over-period changes
            const previousClicks = await this.getRecentClicks(affiliateId, 60 * 24, 30 * 24); // Previous 30 days
            const previousConversions = await this.getRecentConversions(affiliateId, 60 * 24, 30 * 24);
            
            const clickGrowth = this.calculateGrowth(recentClicks.length, previousClicks.length);
            const conversionGrowth = this.calculateGrowth(recentConversions.length, previousConversions.length);
            
            return {
                affiliateId,
                affiliate: {
                    name: affiliate.name,
                    email: affiliate.email,
                    status: affiliate.status,
                    tier: affiliate.tier,
                    referralCode: affiliate.referralCode
                },
                performance: {
                    ...affiliate.performance,
                    period: {
                        clicks: recentClicks.length,
                        conversions: recentConversions.length,
                        revenue: recentConversions.reduce((sum, c) => sum + c.netRevenue, 0),
                        commissions: recentConversions.reduce((sum, c) => {
                            return sum + c.commissions.reduce((commSum, commId) => {
                                const comm = this.commissions.get(commId);
                                return commSum + (comm ? comm.totalAmount : 0);
                            }, 0);
                        }, 0)
                    },
                    growth: {
                        clicks: clickGrowth,
                        conversions: conversionGrowth
                    }
                },
                payouts: {
                    pending: await this.getPendingPayouts(affiliateId),
                    total: await this.getTotalPayouts(affiliateId)
                }
            };
        } catch (error) {
            this.logger.error('Failed to get affiliate performance', { 
                error: error.message, 
                affiliateId 
            });
            throw error;
        }
    }

    // Helper methods
    generateReferralCode(identifier) {
        return identifier.replace(/[^a-zA-Z0-9]/g, '').substring(0, 10).toUpperCase() + 
               Math.random().toString(36).substring(2, 6).toUpperCase();
    }

    generateTrackingLink(affiliateId, programId) {
        const data = `${affiliateId}:${programId}:${Date.now()}`;
        const signature = crypto.createHmac('sha256', process.env.TRACKING_SECRET || 'default-secret')
                               .update(data)
                               .digest('hex');
        
        return Buffer.from(`${data}:${signature}`).toString('base64');
    }

    decodeTrackingLink(trackingLink) {
        try {
            const decoded = Buffer.from(trackingLink, 'base64').toString('ascii');
            const [affiliateId, programId, timestamp, signature] = decoded.split(':');
            
            // Verify signature
            const data = `${affiliateId}:${programId}:${timestamp}`;
            const expectedSignature = crypto.createHmac('sha256', process.env.TRACKING_SECRET || 'default-secret')
                                           .update(data)
                                           .digest('hex');
            
            if (signature !== expectedSignature) {
                throw new Error('Invalid signature');
            }
            
            return { affiliateId, programId, timestamp: parseInt(timestamp) };
        } catch (error) {
            this.logger.error('Failed to decode tracking link', { error: error.message });
            return null;
        }
    }

    generateSessionId(clickData) {
        const data = `${clickData.ipAddress}:${clickData.userAgent}:${Date.now()}`;
        return crypto.createHash('md5').update(data).digest('hex');
    }

    async setTrackingCookie(clickId, trackingInfo, cookieWindow) {
        const cookieData = {
            clickId,
            affiliateId: trackingInfo.affiliateId,
            programId: trackingInfo.programId,
            timestamp: Date.now(),
            expiresAt: Date.now() + (cookieWindow * 24 * 60 * 60 * 1000)
        };
        
        await this.redis.setex(
            `tracking_cookie:${clickId}`, 
            cookieWindow * 24 * 60 * 60, 
            JSON.stringify(cookieData)
        );
    }

    async findAssociatedClicks(sessionId, orderId) {
        // This is a simplified implementation
        // In production, you'd use more sophisticated matching
        const clicks = Array.from(this.clicks.values())
            .filter(c => c.sessionId === sessionId)
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        return clicks;
    }

    isBotUserAgent(userAgent) {
        const botPatterns = [
            /bot/i, /crawler/i, /spider/i, /scraper/i,
            /headless/i, /phantom/i, /selenium/i
        ];
        
        return botPatterns.some(pattern => pattern.test(userAgent));
    }

    calculateGrowth(current, previous) {
        if (previous === 0) return current > 0 ? 100 : 0;
        return ((current - previous) / previous) * 100;
    }

    startFraudDetection() {
        setInterval(async () => {
            try {
                await this.runFraudDetection();
            } catch (error) {
                this.logger.error('Fraud detection error', { error: error.message });
            }
        }, 30 * 60 * 1000); // Every 30 minutes
    }

    startCommissionCalculation() {
        setInterval(async () => {
            try {
                await this.processCommissionApprovals();
            } catch (error) {
                this.logger.error('Commission processing error', { error: error.message });
            }
        }, 60 * 60 * 1000); // Every hour
    }

    async getOverallStats() {
        return {
            totalAffiliates: this.affiliates.size,
            activeAffiliates: Array.from(this.affiliates.values()).filter(a => a.status === 'active').length,
            totalPrograms: this.programs.size,
            totalClicks: Array.from(this.affiliates.values()).reduce((sum, a) => sum + a.performance.totalClicks, 0),
            totalConversions: Array.from(this.affiliates.values()).reduce((sum, a) => sum + a.performance.totalConversions, 0),
            totalCommissions: Array.from(this.affiliates.values()).reduce((sum, a) => sum + a.performance.totalCommissions, 0)
        };
    }

    // Event handlers
    handleAffiliateRegistered(affiliate) {
        this.logger.info('Affiliate registration processed', {
            affiliateId: affiliate.id,
            email: affiliate.email
        });
    }

    handleClickTracked(click) {
        this.logger.info('Click tracking processed', {
            clickId: click.id,
            affiliateId: click.affiliateId
        });
    }

    handleConversionTracked(conversion) {
        this.logger.info('Conversion tracking processed', {
            conversionId: conversion.id,
            orderValue: conversion.orderValue
        });
    }

    handleFraudDetected(data) {
        this.logger.warn('Fraud detected and blocked', data);
    }

    handleCommissionCalculated(data) {
        this.logger.info('Commission calculated', {
            commissionId: data.commission.id,
            amount: data.commission.totalAmount
        });
    }

    // Data sanitization
    sanitizeAffiliateData(affiliate) {
        const { taxInfo, paymentInfo, ...sanitized } = affiliate;
        return {
            ...sanitized,
            // Only include non-sensitive payment info
            paymentMethod: paymentInfo.method,
            minimumPayout: paymentInfo.minimumPayout
        };
    }

    sanitizeConversionData(conversion) {
        return {
            ...conversion,
            // Remove sensitive customer data if needed
        };
    }
}

module.exports = AffiliateTracker;