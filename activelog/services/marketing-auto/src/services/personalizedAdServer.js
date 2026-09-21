const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');
const axios = require('axios');

class PersonalizedAdServer extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.campaigns = new Map();
        this.adGroups = new Map();
        this.advertisements = new Map();
        this.audiences = new Map();
        this.userProfiles = new Map();
        this.adServing = new Map();
        this.biddingStrategies = new Map();
        
        this.setupEventHandlers();
        this.initializeBiddingStrategies();
        this.startAdServingEngine();
        this.startPerformanceTracking();
    }

    setupEventHandlers() {
        this.on('ad_served', this.handleAdServed.bind(this));
        this.on('ad_clicked', this.handleAdClicked.bind(this));
        this.on('conversion_tracked', this.handleConversionTracked.bind(this));
        this.on('budget_threshold', this.handleBudgetThreshold.bind(this));
    }

    initializeBiddingStrategies() {
        this.biddingStrategies.set('cpc_maximize_clicks', {
            name: 'Maximize Clicks (CPC)',
            type: 'cpc',
            optimization: 'clicks',
            bidAdjustment: (basebid, performance) => {
                const ctr = performance.clicks / Math.max(performance.impressions, 1);
                return basebid * (1 + (ctr - 0.02) / 0.02 * 0.5); // Adjust based on CTR
            }
        });
        
        this.biddingStrategies.set('cpa_target_conversions', {
            name: 'Target CPA',
            type: 'cpa',
            optimization: 'conversions',
            bidAdjustment: (basebid, performance, targetCPA) => {
                const currentCPA = performance.cost / Math.max(performance.conversions, 1);
                return basebid * (targetCPA / Math.max(currentCPA, 1));
            }
        });
        
        this.biddingStrategies.set('roas_target', {
            name: 'Target ROAS',
            type: 'roas',
            optimization: 'revenue',
            bidAdjustment: (basebid, performance, targetROAS) => {
                const currentROAS = performance.revenue / Math.max(performance.cost, 1);
                return basebid * (currentROAS / Math.max(targetROAS, 1));
            }
        });
    }

    async createCampaign(campaignData) {
        try {
            const campaignId = uuidv4();
            const campaign = {
                id: campaignId,
                name: campaignData.name,
                type: campaignData.type || 'search', // search, display, video, shopping
                status: 'active',
                budget: {
                    dailyBudget: campaignData.budget.dailyBudget,
                    totalBudget: campaignData.budget.totalBudget || null,
                    currency: campaignData.budget.currency || 'USD',
                    spent: 0,
                    remaining: campaignData.budget.dailyBudget
                },
                targeting: {
                    locations: campaignData.targeting?.locations || [],
                    demographics: campaignData.targeting?.demographics || {},
                    interests: campaignData.targeting?.interests || [],
                    keywords: campaignData.targeting?.keywords || [],
                    devices: campaignData.targeting?.devices || ['desktop', 'mobile', 'tablet'],
                    languages: campaignData.targeting?.languages || ['en']
                },
                schedule: {
                    startDate: new Date(campaignData.schedule?.startDate || Date.now()),
                    endDate: campaignData.schedule?.endDate ? new Date(campaignData.schedule.endDate) : null,
                    dayParting: campaignData.schedule?.dayParting || {},
                    timezone: campaignData.schedule?.timezone || 'UTC'
                },
                biddingStrategy: {
                    type: campaignData.biddingStrategy?.type || 'cpc_maximize_clicks',
                    targetCPA: campaignData.biddingStrategy?.targetCPA || null,
                    targetROAS: campaignData.biddingStrategy?.targetROAS || null,
                    maxBid: campaignData.biddingStrategy?.maxBid || 10,
                    baseBid: campaignData.biddingStrategy?.baseBid || 1
                },
                createdAt: new Date(),
                createdBy: campaignData.createdBy,
                performance: {
                    impressions: 0,
                    clicks: 0,
                    conversions: 0,
                    cost: 0,
                    revenue: 0,
                    ctr: 0,
                    cpc: 0,
                    cpa: 0,
                    roas: 0
                },
                adGroups: [],
                settings: {
                    frequencyCapping: campaignData.settings?.frequencyCapping || { impressions: 3, period: 'day' },
                    optimizationGoal: campaignData.settings?.optimizationGoal || 'clicks',
                    attribution: campaignData.settings?.attribution || 'last_click',
                    experiments: campaignData.settings?.experiments || []
                }
            };

            this.campaigns.set(campaignId, campaign);
            await this.redis.hset('ad_campaigns', campaignId, JSON.stringify(campaign));
            
            this.logger.info('Campaign created', { 
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
            
            return { success: true, campaignId, campaign: this.sanitizeCampaignData(campaign) };
        } catch (error) {
            this.logger.error('Failed to create campaign', { error: error.message, campaignData });
            throw new Error(`Campaign creation failed: ${error.message}`);
        }
    }

    async createAdGroup(adGroupData) {
        try {
            const adGroupId = uuidv4();
            const adGroup = {
                id: adGroupId,
                campaignId: adGroupData.campaignId,
                name: adGroupData.name,
                status: 'active',
                bidding: {
                    maxBid: adGroupData.bidding?.maxBid || 5,
                    bidAdjustments: adGroupData.bidding?.bidAdjustments || {}
                },
                targeting: {
                    keywords: adGroupData.targeting?.keywords || [],
                    negativeKeywords: adGroupData.targeting?.negativeKeywords || [],
                    placements: adGroupData.targeting?.placements || [],
                    audiences: adGroupData.targeting?.audiences || []
                },
                createdAt: new Date(),
                performance: {
                    impressions: 0,
                    clicks: 0,
                    conversions: 0,
                    cost: 0,
                    revenue: 0
                },
                ads: []
            };

            this.adGroups.set(adGroupId, adGroup);
            await this.redis.hset('ad_groups', adGroupId, JSON.stringify(adGroup));
            
            // Update campaign
            const campaign = this.campaigns.get(adGroupData.campaignId);
            if (campaign) {
                campaign.adGroups.push(adGroupId);
                await this.redis.hset('ad_campaigns', adGroupData.campaignId, JSON.stringify(campaign));
            }
            
            this.logger.info('Ad group created', { 
                adGroupId, 
                campaignId: adGroupData.campaignId,
                name: adGroup.name 
            });
            
            return { success: true, adGroupId, adGroup: this.sanitizeAdGroupData(adGroup) };
        } catch (error) {
            this.logger.error('Failed to create ad group', { error: error.message, adGroupData });
            throw new Error(`Ad group creation failed: ${error.message}`);
        }
    }

    async createAdvertisement(adData) {
        try {
            const adId = uuidv4();
            const advertisement = {
                id: adId,
                adGroupId: adData.adGroupId,
                campaignId: adData.campaignId,
                type: adData.type || 'text', // text, image, video, responsive
                status: 'active',
                creative: {
                    headline1: adData.creative?.headline1 || '',
                    headline2: adData.creative?.headline2 || '',
                    headline3: adData.creative?.headline3 || '',
                    description1: adData.creative?.description1 || '',
                    description2: adData.creative?.description2 || '',
                    displayUrl: adData.creative?.displayUrl || '',
                    finalUrl: adData.creative?.finalUrl || '',
                    images: adData.creative?.images || [],
                    videos: adData.creative?.videos || [],
                    callToAction: adData.creative?.callToAction || 'Learn More'
                },
                personalization: {
                    dynamicText: adData.personalization?.dynamicText || false,
                    audienceSpecific: adData.personalization?.audienceSpecific || false,
                    locationBased: adData.personalization?.locationBased || false,
                    deviceOptimized: adData.personalization?.deviceOptimized || true
                },
                createdAt: new Date(),
                performance: {
                    impressions: 0,
                    clicks: 0,
                    conversions: 0,
                    cost: 0,
                    revenue: 0,
                    qualityScore: 5
                },
                experiments: [],
                scheduling: adData.scheduling || {}
            };

            this.advertisements.set(adId, advertisement);
            await this.redis.hset('advertisements', adId, JSON.stringify(advertisement));
            
            // Update ad group
            const adGroup = this.adGroups.get(adData.adGroupId);
            if (adGroup) {
                adGroup.ads.push(adId);
                await this.redis.hset('ad_groups', adData.adGroupId, JSON.stringify(adGroup));
            }
            
            this.logger.info('Advertisement created', { 
                adId, 
                adGroupId: adData.adGroupId,
                type: advertisement.type 
            });
            
            return { success: true, adId, advertisement: this.sanitizeAdData(advertisement) };
        } catch (error) {
            this.logger.error('Failed to create advertisement', { error: error.message, adData });
            throw new Error(`Advertisement creation failed: ${error.message}`);
        }
    }

    async serveAd(requestData) {
        try {
            const userId = requestData.userId || this.generateAnonymousId();
            const context = {
                location: requestData.location || {},
                device: requestData.device || 'desktop',
                placement: requestData.placement || 'sidebar',
                keywords: requestData.keywords || [],
                pageUrl: requestData.pageUrl || '',
                referrer: requestData.referrer || '',
                timestamp: new Date(),
                sessionId: requestData.sessionId || uuidv4()
            };

            // Get or create user profile
            let userProfile = await this.getUserProfile(userId);
            if (!userProfile) {
                userProfile = await this.createUserProfile(userId, requestData.userData || {});
            }
            
            // Update user context
            await this.updateUserContext(userId, context);
            
            // Find eligible campaigns
            const eligibleCampaigns = await this.findEligibleCampaigns(userProfile, context);
            
            if (eligibleCampaigns.length === 0) {
                return { success: false, reason: 'No eligible campaigns' };
            }
            
            // Run ad auction
            const auctionResult = await this.runAdAuction(eligibleCampaigns, userProfile, context);
            
            if (!auctionResult.winningAd) {
                return { success: false, reason: 'No winning ad in auction' };
            }
            
            // Personalize the ad
            const personalizedAd = await this.personalizeAd(auctionResult.winningAd, userProfile, context);
            
            // Track ad serving
            await this.trackAdServing(personalizedAd, userProfile, context, auctionResult);
            
            // Increment impressions
            await this.incrementImpressions(personalizedAd.id, personalizedAd.adGroupId, personalizedAd.campaignId);
            
            this.emit('ad_served', {
                adId: personalizedAd.id,
                userId,
                context,
                auctionResult
            });
            
            return {
                success: true,
                ad: {
                    id: personalizedAd.id,
                    type: personalizedAd.type,
                    creative: personalizedAd.personalizedCreative || personalizedAd.creative,
                    trackingUrls: {
                        impression: `/api/ads/track/impression/${personalizedAd.id}`,
                        click: `/api/ads/track/click/${personalizedAd.id}`
                    }
                },
                metadata: {
                    campaignId: personalizedAd.campaignId,
                    adGroupId: personalizedAd.adGroupId,
                    auctionId: auctionResult.id,
                    timestamp: context.timestamp
                }
            };
        } catch (error) {
            this.logger.error('Failed to serve ad', { error: error.message, requestData });
            return { success: false, error: error.message };
        }
    }

    async getUserProfile(userId) {
        try {
            const profileData = await this.redis.hget('user_profiles', userId);
            return profileData ? JSON.parse(profileData) : null;
        } catch (error) {
            this.logger.error('Failed to get user profile', { error: error.message, userId });
            return null;
        }
    }

    async createUserProfile(userId, userData = {}) {
        try {
            const profile = {
                id: userId,
                demographics: {
                    age: userData.age || null,
                    gender: userData.gender || null,
                    location: userData.location || null,
                    income: userData.income || null
                },
                interests: userData.interests || [],
                behaviors: {
                    clickHistory: [],
                    conversionHistory: [],
                    pageViews: [],
                    searchQueries: [],
                    purchaseHistory: []
                },
                segmentation: {
                    lifetimeValue: 0,
                    engagementLevel: 'low',
                    conversionProbability: 0.5,
                    customSegments: []
                },
                preferences: {
                    adFrequency: 'normal',
                    contentTypes: [],
                    optOut: false
                },
                createdAt: new Date(),
                lastUpdated: new Date(),
                sessions: 1,
                totalImpressions: 0,
                totalClicks: 0
            };

            this.userProfiles.set(userId, profile);
            await this.redis.hset('user_profiles', userId, JSON.stringify(profile));
            
            return profile;
        } catch (error) {
            this.logger.error('Failed to create user profile', { error: error.message, userId });
            throw error;
        }
    }

    async updateUserContext(userId, context) {
        try {
            const profile = this.userProfiles.get(userId) || 
                JSON.parse(await this.redis.hget('user_profiles', userId));
            
            if (!profile) return;
            
            // Update page views
            profile.behaviors.pageViews.push({
                url: context.pageUrl,
                timestamp: context.timestamp,
                device: context.device
            });
            
            // Keep only last 50 page views
            if (profile.behaviors.pageViews.length > 50) {
                profile.behaviors.pageViews = profile.behaviors.pageViews.slice(-50);
            }
            
            // Update location if provided
            if (context.location.country) {
                profile.demographics.location = context.location;
            }
            
            // Update engagement level based on activity
            profile.segmentation.engagementLevel = this.calculateEngagementLevel(profile);
            
            profile.lastUpdated = new Date();
            
            this.userProfiles.set(userId, profile);
            await this.redis.hset('user_profiles', userId, JSON.stringify(profile));
        } catch (error) {
            this.logger.error('Failed to update user context', { error: error.message, userId });
        }
    }

    async findEligibleCampaigns(userProfile, context) {
        const eligibleCampaigns = [];
        
        for (const [campaignId, campaign] of this.campaigns) {
            if (campaign.status !== 'active') continue;
            
            // Check budget
            if (campaign.budget.spent >= campaign.budget.dailyBudget) continue;
            
            // Check schedule
            if (!this.isWithinSchedule(campaign.schedule, context.timestamp)) continue;
            
            // Check targeting
            if (!this.matchesTargeting(campaign.targeting, userProfile, context)) continue;
            
            // Check frequency capping
            if (!this.checkFrequencyCapping(campaign, userProfile)) continue;
            
            // Get active ad groups and ads
            const activeAdGroups = campaign.adGroups
                .map(id => this.adGroups.get(id))
                .filter(ag => ag && ag.status === 'active');
            
            if (activeAdGroups.length === 0) continue;
            
            const activeAds = [];
            for (const adGroup of activeAdGroups) {
                const ads = adGroup.ads
                    .map(id => this.advertisements.get(id))
                    .filter(ad => ad && ad.status === 'active');
                activeAds.push(...ads);
            }
            
            if (activeAds.length === 0) continue;
            
            eligibleCampaigns.push({
                campaign,
                adGroups: activeAdGroups,
                ads: activeAds
            });
        }
        
        return eligibleCampaigns;
    }

    async runAdAuction(eligibleCampaigns, userProfile, context) {
        const auctionId = uuidv4();
        const bids = [];
        
        // Calculate bids for each ad
        for (const { campaign, ads } of eligibleCampaigns) {
            for (const ad of ads) {
                const bid = await this.calculateBid(campaign, ad, userProfile, context);
                bids.push({
                    ad,
                    campaign,
                    bid,
                    qualityScore: ad.performance.qualityScore,
                    adRank: bid * ad.performance.qualityScore
                });
            }
        }
        
        // Sort by ad rank (bid * quality score)
        bids.sort((a, b) => b.adRank - a.adRank);
        
        const winningBid = bids[0];
        const secondPrice = bids[1] ? bids[1].bid : 0;
        
        return {
            id: auctionId,
            winningAd: winningBid?.ad || null,
            winningCampaign: winningBid?.campaign || null,
            winningBid: winningBid?.bid || 0,
            actualCPC: Math.min(winningBid?.bid || 0, secondPrice + 0.01),
            qualityScore: winningBid?.qualityScore || 0,
            adRank: winningBid?.adRank || 0,
            totalBids: bids.length,
            timestamp: new Date()
        };
    }

    async calculateBid(campaign, ad, userProfile, context) {
        const biddingStrategy = this.biddingStrategies.get(campaign.biddingStrategy.type);
        const baseBid = campaign.biddingStrategy.baseBid;
        const maxBid = campaign.biddingStrategy.maxBid;
        
        // Get performance data
        const performance = {
            impressions: ad.performance.impressions,
            clicks: ad.performance.clicks,
            conversions: ad.performance.conversions,
            cost: ad.performance.cost,
            revenue: ad.performance.revenue
        };
        
        // Apply bidding strategy
        let adjustedBid = baseBid;
        
        if (biddingStrategy && biddingStrategy.bidAdjustment) {
            if (campaign.biddingStrategy.type === 'cpa_target_conversions') {
                adjustedBid = biddingStrategy.bidAdjustment(
                    baseBid, 
                    performance, 
                    campaign.biddingStrategy.targetCPA
                );
            } else if (campaign.biddingStrategy.type === 'roas_target') {
                adjustedBid = biddingStrategy.bidAdjustment(
                    baseBid, 
                    performance, 
                    campaign.biddingStrategy.targetROAS
                );
            } else {
                adjustedBid = biddingStrategy.bidAdjustment(baseBid, performance);
            }
        }
        
        // Apply demographic adjustments
        adjustedBid *= this.getDemographicAdjustment(userProfile.demographics);
        
        // Apply device adjustments
        adjustedBid *= this.getDeviceAdjustment(context.device);
        
        // Apply time-of-day adjustments
        adjustedBid *= this.getTimeAdjustment(context.timestamp);
        
        // Apply conversion probability adjustment
        adjustedBid *= (1 + userProfile.segmentation.conversionProbability * 0.5);
        
        // Cap at maximum bid
        return Math.min(Math.max(adjustedBid, 0.01), maxBid);
    }

    async personalizeAd(ad, userProfile, context) {
        const personalizedAd = { ...ad };
        
        if (!ad.personalization.dynamicText) {
            return personalizedAd;
        }
        
        const personalizedCreative = { ...ad.creative };
        
        // Personalize based on user demographics
        if (userProfile.demographics.location?.city) {
            personalizedCreative.headline1 = personalizedCreative.headline1
                .replace('{city}', userProfile.demographics.location.city);
            personalizedCreative.description1 = personalizedCreative.description1
                .replace('{city}', userProfile.demographics.location.city);
        }
        
        // Personalize based on interests
        if (userProfile.interests.length > 0) {
            const topInterest = userProfile.interests[0];
            personalizedCreative.headline2 = personalizedCreative.headline2
                .replace('{interest}', topInterest);
        }
        
        // Personalize based on time of day
        const hour = context.timestamp.getHours();
        let timeGreeting = 'today';
        if (hour < 12) timeGreeting = 'this morning';
        else if (hour < 18) timeGreeting = 'this afternoon';
        else timeGreeting = 'this evening';
        
        personalizedCreative.description1 = personalizedCreative.description1
            .replace('{time_of_day}', timeGreeting);
        
        // Personalize CTA based on user behavior
        if (userProfile.behaviors.conversionHistory.length > 0) {
            personalizedCreative.callToAction = 'Buy Again';
        } else if (userProfile.behaviors.clickHistory.length > 5) {
            personalizedCreative.callToAction = 'Get Started';
        }
        
        personalizedAd.personalizedCreative = personalizedCreative;
        return personalizedAd;
    }

    async trackAdServing(ad, userProfile, context, auctionResult) {
        const servingRecord = {
            id: uuidv4(),
            adId: ad.id,
            userId: userProfile.id,
            campaignId: ad.campaignId,
            adGroupId: ad.adGroupId,
            auctionId: auctionResult.id,
            context,
            bid: auctionResult.winningBid,
            actualCPC: auctionResult.actualCPC,
            qualityScore: auctionResult.qualityScore,
            timestamp: context.timestamp,
            events: {
                served: context.timestamp,
                clicked: null,
                converted: null
            }
        };
        
        this.adServing.set(servingRecord.id, servingRecord);
        await this.redis.hset('ad_serving', servingRecord.id, JSON.stringify(servingRecord));
        
        // Update user profile
        userProfile.totalImpressions++;
        await this.redis.hset('user_profiles', userProfile.id, JSON.stringify(userProfile));
    }

    async incrementImpressions(adId, adGroupId, campaignId) {
        // Update advertisement performance
        const ad = this.advertisements.get(adId);
        if (ad) {
            ad.performance.impressions++;
            ad.performance.ctr = ad.performance.clicks / Math.max(ad.performance.impressions, 1);
            await this.redis.hset('advertisements', adId, JSON.stringify(ad));
        }
        
        // Update ad group performance
        const adGroup = this.adGroups.get(adGroupId);
        if (adGroup) {
            adGroup.performance.impressions++;
            await this.redis.hset('ad_groups', adGroupId, JSON.stringify(adGroup));
        }
        
        // Update campaign performance
        const campaign = this.campaigns.get(campaignId);
        if (campaign) {
            campaign.performance.impressions++;
            campaign.performance.ctr = campaign.performance.clicks / Math.max(campaign.performance.impressions, 1);
            await this.redis.hset('ad_campaigns', campaignId, JSON.stringify(campaign));
        }
    }

    // Helper methods
    generateAnonymousId() {
        return 'anon_' + uuidv4().substring(0, 8);
    }

    calculateEngagementLevel(profile) {
        const clickRate = profile.totalClicks / Math.max(profile.totalImpressions, 1);
        const pageViewsPerSession = profile.behaviors.pageViews.length / Math.max(profile.sessions, 1);
        
        if (clickRate > 0.05 && pageViewsPerSession > 3) return 'high';
        if (clickRate > 0.02 || pageViewsPerSession > 2) return 'medium';
        return 'low';
    }

    isWithinSchedule(schedule, timestamp) {
        const now = moment(timestamp);
        
        // Check date range
        if (schedule.startDate && now.isBefore(moment(schedule.startDate))) return false;
        if (schedule.endDate && now.isAfter(moment(schedule.endDate))) return false;
        
        // Check day parting
        if (schedule.dayParting && Object.keys(schedule.dayParting).length > 0) {
            const dayOfWeek = now.format('dddd').toLowerCase();
            const hour = now.hour();
            
            const daySettings = schedule.dayParting[dayOfWeek];
            if (daySettings) {
                const startHour = parseInt(daySettings.start.split(':')[0]);
                const endHour = parseInt(daySettings.end.split(':')[0]);
                
                if (hour < startHour || hour >= endHour) return false;
            }
        }
        
        return true;
    }

    matchesTargeting(targeting, userProfile, context) {
        // Location targeting
        if (targeting.locations.length > 0 && userProfile.demographics.location) {
            const userLocation = userProfile.demographics.location;
            const matchesLocation = targeting.locations.some(loc => 
                loc.country === userLocation.country ||
                loc.state === userLocation.state ||
                loc.city === userLocation.city
            );
            if (!matchesLocation) return false;
        }
        
        // Demographic targeting
        if (targeting.demographics.age) {
            const userAge = userProfile.demographics.age;
            if (userAge && (userAge < targeting.demographics.age.min || userAge > targeting.demographics.age.max)) {
                return false;
            }
        }
        
        if (targeting.demographics.gender && userProfile.demographics.gender) {
            if (targeting.demographics.gender !== userProfile.demographics.gender) {
                return false;
            }
        }
        
        // Interest targeting
        if (targeting.interests.length > 0) {
            const hasMatchingInterest = targeting.interests.some(interest => 
                userProfile.interests.includes(interest)
            );
            if (!hasMatchingInterest) return false;
        }
        
        // Device targeting
        if (targeting.devices.length > 0) {
            if (!targeting.devices.includes(context.device)) return false;
        }
        
        return true;
    }

    checkFrequencyCapping(campaign, userProfile) {
        const frequencyCap = campaign.settings.frequencyCapping;
        if (!frequencyCap) return true;
        
        // Simple frequency capping implementation
        // In production, you'd track this more precisely
        const impressionsToday = userProfile.totalImpressions; // Simplified
        
        return impressionsToday < frequencyCap.impressions;
    }

    getDemographicAdjustment(demographics) {
        let adjustment = 1.0;
        
        // Age adjustments
        if (demographics.age) {
            if (demographics.age >= 25 && demographics.age <= 54) {
                adjustment *= 1.2; // Prime advertising demographic
            }
        }
        
        // Gender adjustments (example)
        if (demographics.gender === 'female') {
            adjustment *= 1.1; // Adjust based on campaign targeting
        }
        
        return adjustment;
    }

    getDeviceAdjustment(device) {
        switch (device) {
            case 'mobile': return 1.0;
            case 'desktop': return 1.1;
            case 'tablet': return 0.9;
            default: return 1.0;
        }
    }

    getTimeAdjustment(timestamp) {
        const hour = timestamp.getHours();
        
        // Higher bids during peak hours
        if (hour >= 9 && hour <= 11) return 1.2; // Morning peak
        if (hour >= 14 && hour <= 16) return 1.1; // Afternoon peak
        if (hour >= 19 && hour <= 21) return 1.3; // Evening peak
        
        return 1.0;
    }

    startAdServingEngine() {
        // Update bid strategies every hour
        setInterval(async () => {
            try {
                await this.optimizeBiddingStrategies();
            } catch (error) {
                this.logger.error('Bid optimization error', { error: error.message });
            }
        }, 60 * 60 * 1000);
    }

    startPerformanceTracking() {
        // Update performance metrics every 5 minutes
        setInterval(async () => {
            try {
                await this.updatePerformanceMetrics();
            } catch (error) {
                this.logger.error('Performance tracking error', { error: error.message });
            }
        }, 5 * 60 * 1000);
    }

    async getCampaignPerformance(campaignId) {
        const campaign = this.campaigns.get(campaignId);
        if (!campaign) {
            throw new Error(`Campaign ${campaignId} not found`);
        }
        
        return {
            campaignId,
            name: campaign.name,
            performance: campaign.performance,
            budget: campaign.budget,
            dates: {
                startDate: campaign.schedule.startDate,
                endDate: campaign.schedule.endDate
            }
        };
    }

    async getOverallPerformance() {
        const totalPerformance = {
            campaigns: this.campaigns.size,
            impressions: 0,
            clicks: 0,
            conversions: 0,
            cost: 0,
            revenue: 0,
            averageCTR: 0,
            averageCPC: 0,
            averageCPA: 0,
            averageROAS: 0
        };
        
        for (const campaign of this.campaigns.values()) {
            totalPerformance.impressions += campaign.performance.impressions;
            totalPerformance.clicks += campaign.performance.clicks;
            totalPerformance.conversions += campaign.performance.conversions;
            totalPerformance.cost += campaign.performance.cost;
            totalPerformance.revenue += campaign.performance.revenue;
        }
        
        totalPerformance.averageCTR = totalPerformance.clicks / Math.max(totalPerformance.impressions, 1);
        totalPerformance.averageCPC = totalPerformance.cost / Math.max(totalPerformance.clicks, 1);
        totalPerformance.averageCPA = totalPerformance.cost / Math.max(totalPerformance.conversions, 1);
        totalPerformance.averageROAS = totalPerformance.revenue / Math.max(totalPerformance.cost, 1);
        
        return totalPerformance;
    }

    // Event handlers
    handleAdServed(data) {
        this.logger.info('Ad served', {
            adId: data.adId,
            userId: data.userId,
            auctionId: data.auctionResult.id
        });
    }

    handleAdClicked(data) {
        this.logger.info('Ad clicked', data);
    }

    handleConversionTracked(data) {
        this.logger.info('Conversion tracked', data);
    }

    handleBudgetThreshold(data) {
        this.logger.warn('Budget threshold reached', data);
    }

    // Data sanitization methods
    sanitizeCampaignData(campaign) {
        return {
            ...campaign,
            // Remove sensitive data if needed
        };
    }

    sanitizeAdGroupData(adGroup) {
        return {
            ...adGroup,
            // Remove sensitive data if needed
        };
    }

    sanitizeAdData(ad) {
        return {
            ...ad,
            // Remove sensitive data if needed
        };
    }
}

module.exports = PersonalizedAdServer;