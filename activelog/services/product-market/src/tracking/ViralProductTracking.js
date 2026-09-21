import { EventEmitter } from 'events';
import crypto from 'crypto';

class ViralProductTracking extends EventEmitter {
    constructor() {
        super();
        this.products = new Map();
        this.viralEvents = new Map();
        this.influencers = new Map();
        this.campaigns = new Map();
        this.socialMetrics = new Map();
        this.trendAnalysis = new Map();
        this.viralPredictions = new Map();
        this.referralChains = new Map();
        this.contentTracking = new Map();
        this.platformMetrics = new Map();
        
        this.initializeData();
    }

    initializeData() {
        // Initialize sample viral products
        const sampleProducts = [
            {
                id: 'viral_product_001',
                name: 'AI Fish Counter Pro',
                original_design_id: 'community_design_001',
                creator_id: 'user_003',
                launch_date: new Date('2024-07-01'),
                viral_score: 8.7,
                peak_viral_date: new Date('2024-08-15'),
                current_status: 'trending',
                total_shares: 15420,
                total_views: 234567,
                total_sales: 1847,
                conversion_rate: 0.79,
                geographic_reach: ['US', 'CA', 'AU', 'UK', 'DE', 'FR', 'JP'],
                viral_triggers: [
                    'Featured in TechCrunch article',
                    'Shared by @TechReviewPro (235K followers)',
                    'Viral TikTok demo video (1.2M views)',
                    'Reddit r/DIY top post (45K upvotes)'
                ],
                platforms: {
                    'twitter': { shares: 4520, reach: 89000, engagement: 12.4 },
                    'tiktok': { shares: 8900, reach: 1200000, engagement: 8.9 },
                    'reddit': { shares: 1200, reach: 456000, engagement: 15.2 },
                    'youtube': { shares: 800, reach: 67000, engagement: 22.1 }
                },
                sentiment_analysis: {
                    positive: 78.5,
                    neutral: 18.2,
                    negative: 3.3
                }
            },
            {
                id: 'viral_product_002',
                name: 'Solar Camera Mesh System',
                original_design_id: 'community_design_002',
                creator_id: 'user_002',
                launch_date: new Date('2024-06-15'),
                viral_score: 7.4,
                peak_viral_date: new Date('2024-07-28'),
                current_status: 'declining',
                total_shares: 8930,
                total_views: 156789,
                total_sales: 923,
                conversion_rate: 0.59,
                geographic_reach: ['US', 'CA', 'AU', 'UK', 'NL', 'SE'],
                viral_triggers: [
                    'Featured on Popular Mechanics',
                    'Shared by solar energy communities',
                    'YouTube review by Tech Insider (890K views)'
                ],
                platforms: {
                    'twitter': { shares: 2340, reach: 45000, engagement: 9.8 },
                    'youtube': { shares: 4200, reach: 890000, engagement: 18.7 },
                    'linkedin': { shares: 1890, reach: 23000, engagement: 14.3 },
                    'facebook': { shares: 500, reach: 12000, engagement: 6.2 }
                },
                sentiment_analysis: {
                    positive: 82.1,
                    neutral: 15.4,
                    negative: 2.5
                }
            }
        ];

        sampleProducts.forEach(product => {
            this.products.set(product.id, product);
        });

        // Initialize sample influencers
        const sampleInfluencers = [
            {
                id: 'influencer_001',
                username: 'TechReviewPro',
                platform: 'twitter',
                followers: 235000,
                engagement_rate: 12.4,
                niche: ['electronics', 'IoT', 'hardware'],
                viral_coefficient: 8.9,
                average_shares: 1250,
                collaboration_history: [
                    { product_id: 'viral_product_001', date: new Date('2024-08-10'), reach: 89000 }
                ],
                contact_info: {
                    email: 'collab@techreviewpro.com',
                    rate_per_post: '$500'
                },
                verification_status: 'verified',
                reputation_score: 9.2
            },
            {
                id: 'influencer_002',
                username: 'DIYTechGuru',
                platform: 'youtube',
                followers: 450000,
                engagement_rate: 18.7,
                niche: ['diy', 'electronics', 'tutorials'],
                viral_coefficient: 12.3,
                average_shares: 2100,
                collaboration_history: [
                    { product_id: 'viral_product_002', date: new Date('2024-07-20'), reach: 890000 }
                ],
                contact_info: {
                    email: 'business@diytechguru.com',
                    rate_per_post: '$1200'
                },
                verification_status: 'verified',
                reputation_score: 9.8
            },
            {
                id: 'influencer_003',
                username: 'FishingTechReviews',
                platform: 'tiktok',
                followers: 180000,
                engagement_rate: 8.9,
                niche: ['fishing', 'marine', 'technology'],
                viral_coefficient: 6.7,
                average_shares: 890,
                collaboration_history: [
                    { product_id: 'viral_product_001', date: new Date('2024-08-12'), reach: 1200000 }
                ],
                contact_info: {
                    email: 'partnerships@fishingtech.com',
                    rate_per_post: '$300'
                },
                verification_status: 'verified',
                reputation_score: 8.5
            }
        ];

        sampleInfluencers.forEach(influencer => {
            this.influencers.set(influencer.id, influencer);
        });

        // Initialize sample viral campaigns
        const sampleCampaigns = [
            {
                id: 'campaign_001',
                name: 'Fish Counter Launch Campaign',
                product_id: 'viral_product_001',
                start_date: new Date('2024-08-01'),
                end_date: new Date('2024-08-31'),
                status: 'active',
                budget: 5000,
                spent: 3200,
                target_reach: 500000,
                actual_reach: 789000,
                target_conversions: 1000,
                actual_conversions: 1847,
                influencers: ['influencer_001', 'influencer_003'],
                platforms: ['twitter', 'tiktok', 'reddit'],
                content_types: ['demo_videos', 'tutorials', 'reviews'],
                hashtags: ['#FishTech', '#AIcounting', '#MarineInnovation'],
                performance_metrics: {
                    impressions: 1200000,
                    clicks: 89000,
                    shares: 15420,
                    comments: 3456,
                    saves: 7890
                }
            },
            {
                id: 'campaign_002',
                name: 'Solar Camera Summer Push',
                product_id: 'viral_product_002',
                start_date: new Date('2024-07-15'),
                end_date: new Date('2024-08-15'),
                status: 'completed',
                budget: 3500,
                spent: 3500,
                target_reach: 300000,
                actual_reach: 456000,
                target_conversions: 600,
                actual_conversions: 923,
                influencers: ['influencer_002'],
                platforms: ['youtube', 'linkedin'],
                content_types: ['reviews', 'installations', 'comparisons'],
                hashtags: ['#SolarTech', '#GreenEnergy', '#SecurityCameras'],
                performance_metrics: {
                    impressions: 890000,
                    clicks: 45000,
                    shares: 8930,
                    comments: 2100,
                    saves: 4560
                }
            }
        ];

        sampleCampaigns.forEach(campaign => {
            this.campaigns.set(campaign.id, campaign);
        });

        // Initialize sample viral events
        const sampleViralEvents = [
            {
                id: 'event_001',
                product_id: 'viral_product_001',
                event_type: 'viral_spike',
                timestamp: new Date('2024-08-15T14:30:00Z'),
                trigger: 'TikTok demo video went viral',
                metrics: {
                    shares_before: 2340,
                    shares_after: 8900,
                    growth_rate: 280.5,
                    duration_hours: 18
                },
                platform: 'tiktok',
                geographic_impact: ['US', 'CA', 'UK', 'AU'],
                influencer_id: 'influencer_003'
            },
            {
                id: 'event_002',
                product_id: 'viral_product_001',
                event_type: 'media_feature',
                timestamp: new Date('2024-08-10T09:00:00Z'),
                trigger: 'Featured in TechCrunch article',
                metrics: {
                    views_before: 45000,
                    views_after: 156000,
                    growth_rate: 246.7,
                    duration_hours: 72
                },
                platform: 'web',
                geographic_impact: ['US', 'CA', 'UK', 'DE', 'FR'],
                media_outlet: 'TechCrunch'
            }
        ];

        sampleViralEvents.forEach(event => {
            this.viralEvents.set(event.id, event);
        });

        // Initialize trending topics and hashtags
        this.initializeTrendingData();
    }

    initializeTrendingData() {
        this.trendingTopics = [
            { topic: 'AI Fish Counting', mentions: 12340, growth: 156.7 },
            { topic: 'Solar Security', mentions: 8920, growth: 89.4 },
            { topic: 'DIY Electronics', mentions: 15670, growth: 45.2 },
            { topic: 'Marine Technology', mentions: 6780, growth: 234.1 },
            { topic: 'IoT Sensors', mentions: 23450, growth: 67.8 }
        ];

        this.trendingHashtags = [
            { hashtag: '#FishTech', uses: 34567, engagement: 8.9 },
            { hashtag: '#SolarPower', uses: 78901, engagement: 6.4 },
            { hashtag: '#DIYElectronics', uses: 156789, engagement: 12.3 },
            { hashtag: '#TechReview', uses: 234567, engagement: 15.7 },
            { hashtag: '#Innovation', uses: 345678, engagement: 9.2 }
        ];
    }

    generateId(prefix) {
        return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
    }

    // Product Viral Tracking
    async trackProduct(productData) {
        try {
            const product = {
                id: this.generateId('viral_product'),
                name: productData.name,
                original_design_id: productData.design_id,
                creator_id: productData.creator_id,
                launch_date: new Date(),
                viral_score: 0,
                peak_viral_date: null,
                current_status: 'tracking',
                total_shares: 0,
                total_views: 0,
                total_sales: 0,
                conversion_rate: 0,
                geographic_reach: [],
                viral_triggers: [],
                platforms: {},
                sentiment_analysis: {
                    positive: 0,
                    neutral: 0,
                    negative: 0
                },
                tracking_settings: {
                    keywords: productData.keywords || [],
                    hashtags: productData.hashtags || [],
                    monitoring_platforms: productData.platforms || ['twitter', 'tiktok', 'youtube', 'reddit'],
                    alert_thresholds: {
                        viral_spike: 100,
                        negative_sentiment: 20,
                        reach_milestone: 10000
                    }
                }
            };

            this.products.set(product.id, product);
            this.emit('product_tracking_started', product);

            return {
                success: true,
                product_id: product.id,
                message: 'Product viral tracking initialized'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async updateViralMetrics(productId, metrics) {
        try {
            const product = this.products.get(productId);
            if (!product) {
                throw new Error('Product not found');
            }

            const oldViralScore = product.viral_score;
            
            // Update metrics
            Object.keys(metrics).forEach(key => {
                if (product.hasOwnProperty(key)) {
                    product[key] = metrics[key];
                }
            });

            // Recalculate viral score
            product.viral_score = this.calculateViralScore(product);
            
            // Check for viral events
            if (product.viral_score > oldViralScore + 2) {
                this.recordViralEvent(productId, 'viral_spike', {
                    old_score: oldViralScore,
                    new_score: product.viral_score,
                    trigger: 'Significant metric improvement'
                });
            }

            // Update peak viral date if new peak
            if (product.viral_score > (product.peak_viral_score || 0)) {
                product.peak_viral_date = new Date();
                product.peak_viral_score = product.viral_score;
            }

            // Update status based on viral score
            product.current_status = this.determineViralStatus(product.viral_score);

            this.products.set(productId, product);
            this.emit('viral_metrics_updated', { product_id: productId, metrics });

            return {
                success: true,
                viral_score: product.viral_score,
                status: product.current_status
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    calculateViralScore(product) {
        // Weighted scoring algorithm
        const shareWeight = 0.3;
        const viewWeight = 0.2;
        const conversionWeight = 0.3;
        const engagementWeight = 0.2;

        const shareScore = Math.min(product.total_shares / 1000, 10);
        const viewScore = Math.min(product.total_views / 10000, 10);
        const conversionScore = Math.min(product.conversion_rate * 100, 10);
        
        let engagementScore = 0;
        const platformCount = Object.keys(product.platforms).length;
        if (platformCount > 0) {
            const avgEngagement = Object.values(product.platforms)
                .reduce((sum, p) => sum + (p.engagement || 0), 0) / platformCount;
            engagementScore = Math.min(avgEngagement, 10);
        }

        const rawScore = (shareScore * shareWeight) + 
                        (viewScore * viewWeight) + 
                        (conversionScore * conversionWeight) + 
                        (engagementScore * engagementWeight);

        return Math.round(rawScore * 10) / 10;
    }

    determineViralStatus(viralScore) {
        if (viralScore >= 8) return 'viral';
        if (viralScore >= 6) return 'trending';
        if (viralScore >= 4) return 'growing';
        if (viralScore >= 2) return 'emerging';
        return 'tracking';
    }

    recordViralEvent(productId, eventType, details) {
        const event = {
            id: this.generateId('event'),
            product_id: productId,
            event_type: eventType,
            timestamp: new Date(),
            ...details
        };

        this.viralEvents.set(event.id, event);
        this.emit('viral_event_recorded', event);
    }

    // Influencer Management
    async identifyInfluencers(criteria = {}) {
        try {
            let influencers = Array.from(this.influencers.values());

            // Apply filters
            if (criteria.niche) {
                influencers = influencers.filter(inf => 
                    inf.niche.some(n => n.toLowerCase().includes(criteria.niche.toLowerCase()))
                );
            }

            if (criteria.min_followers) {
                influencers = influencers.filter(inf => inf.followers >= criteria.min_followers);
            }

            if (criteria.min_engagement) {
                influencers = influencers.filter(inf => inf.engagement_rate >= criteria.min_engagement);
            }

            if (criteria.platform) {
                influencers = influencers.filter(inf => inf.platform === criteria.platform);
            }

            if (criteria.budget_range) {
                influencers = influencers.filter(inf => {
                    const rate = parseInt(inf.contact_info.rate_per_post.replace(/[$,]/g, ''));
                    return rate >= criteria.budget_range.min && rate <= criteria.budget_range.max;
                });
            }

            // Calculate influence score
            influencers = influencers.map(inf => ({
                ...inf,
                influence_score: this.calculateInfluenceScore(inf),
                estimated_reach: this.estimateReach(inf),
                collaboration_fit: this.assessCollaborationFit(inf, criteria)
            }));

            // Sort by influence score
            influencers.sort((a, b) => b.influence_score - a.influence_score);

            return {
                success: true,
                influencers: influencers,
                total_found: influencers.length,
                search_criteria: criteria
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    calculateInfluenceScore(influencer) {
        const followerScore = Math.min(influencer.followers / 10000, 10);
        const engagementScore = Math.min(influencer.engagement_rate, 10);
        const viralScore = Math.min(influencer.viral_coefficient, 10);
        const reputationScore = influencer.reputation_score;

        return Math.round(((followerScore * 0.3) + 
                         (engagementScore * 0.3) + 
                         (viralScore * 0.2) + 
                         (reputationScore * 0.2)) * 10) / 10;
    }

    estimateReach(influencer) {
        return Math.round(influencer.followers * (influencer.engagement_rate / 100) * 
                         (influencer.viral_coefficient / 10));
    }

    assessCollaborationFit(influencer, criteria) {
        let score = 5; // Base score

        if (criteria.niche && influencer.niche.includes(criteria.niche)) score += 2;
        if (influencer.verification_status === 'verified') score += 1;
        if (influencer.reputation_score >= 9) score += 1;
        if (influencer.collaboration_history.length > 0) score += 1;

        return Math.min(score, 10);
    }

    // Campaign Management
    async createViralCampaign(campaignData) {
        try {
            const campaign = {
                id: this.generateId('campaign'),
                name: campaignData.name,
                product_id: campaignData.product_id,
                start_date: campaignData.start_date || new Date(),
                end_date: campaignData.end_date,
                status: 'planning',
                budget: campaignData.budget || 0,
                spent: 0,
                target_reach: campaignData.target_reach || 100000,
                actual_reach: 0,
                target_conversions: campaignData.target_conversions || 500,
                actual_conversions: 0,
                influencers: campaignData.influencers || [],
                platforms: campaignData.platforms || [],
                content_types: campaignData.content_types || [],
                hashtags: campaignData.hashtags || [],
                performance_metrics: {
                    impressions: 0,
                    clicks: 0,
                    shares: 0,
                    comments: 0,
                    saves: 0
                },
                content_calendar: [],
                roi_target: campaignData.roi_target || 3.0,
                kpis: campaignData.kpis || ['reach', 'engagement', 'conversions']
            };

            this.campaigns.set(campaign.id, campaign);
            this.emit('viral_campaign_created', campaign);

            return {
                success: true,
                campaign_id: campaign.id,
                message: 'Viral campaign created successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async updateCampaignMetrics(campaignId, metrics) {
        try {
            const campaign = this.campaigns.get(campaignId);
            if (!campaign) {
                throw new Error('Campaign not found');
            }

            // Update metrics
            Object.keys(metrics).forEach(key => {
                if (campaign.hasOwnProperty(key)) {
                    campaign[key] = metrics[key];
                } else if (campaign.performance_metrics.hasOwnProperty(key)) {
                    campaign.performance_metrics[key] = metrics[key];
                }
            });

            // Calculate ROI
            if (campaign.spent > 0 && campaign.actual_conversions > 0) {
                const revenue = campaign.actual_conversions * (metrics.average_order_value || 200);
                campaign.roi = Math.round((revenue / campaign.spent) * 100) / 100;
            }

            campaign.last_updated = new Date();
            this.campaigns.set(campaignId, campaign);

            this.emit('campaign_metrics_updated', { campaign_id: campaignId, metrics });

            return {
                success: true,
                roi: campaign.roi || 0,
                performance: this.assessCampaignPerformance(campaign)
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    assessCampaignPerformance(campaign) {
        const reachPerformance = (campaign.actual_reach / campaign.target_reach) * 100;
        const conversionPerformance = (campaign.actual_conversions / campaign.target_conversions) * 100;
        const budgetEfficiency = ((campaign.budget - campaign.spent) / campaign.budget) * 100;

        let overallScore = 0;
        let assessments = [];

        if (reachPerformance >= 100) {
            overallScore += 3;
            assessments.push('Excellent reach performance');
        } else if (reachPerformance >= 80) {
            overallScore += 2;
            assessments.push('Good reach performance');
        } else {
            overallScore += 1;
            assessments.push('Below target reach');
        }

        if (conversionPerformance >= 100) {
            overallScore += 3;
            assessments.push('Excellent conversion performance');
        } else if (conversionPerformance >= 80) {
            overallScore += 2;
            assessments.push('Good conversion performance');
        } else {
            overallScore += 1;
            assessments.push('Below target conversions');
        }

        if (campaign.roi && campaign.roi >= campaign.roi_target) {
            overallScore += 2;
            assessments.push('ROI target achieved');
        } else if (campaign.roi && campaign.roi >= campaign.roi_target * 0.8) {
            overallScore += 1;
            assessments.push('ROI approaching target');
        }

        return {
            score: overallScore,
            max_score: 8,
            percentage: Math.round((overallScore / 8) * 100),
            assessments: assessments,
            reach_performance: Math.round(reachPerformance),
            conversion_performance: Math.round(conversionPerformance),
            roi: campaign.roi || 0
        };
    }

    // Trend Analysis
    async analyzeTrends(timeframe = '30d') {
        try {
            const now = new Date();
            let startDate;

            switch (timeframe) {
                case '7d':
                    startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    break;
                case '30d':
                    startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                    break;
                case '90d':
                    startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                    break;
                default:
                    startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
            }

            // Analyze viral events in timeframe
            const recentEvents = Array.from(this.viralEvents.values())
                .filter(event => event.timestamp >= startDate);

            // Identify trending products
            const trendingProducts = Array.from(this.products.values())
                .filter(product => product.viral_score >= 5)
                .sort((a, b) => b.viral_score - a.viral_score);

            // Platform performance analysis
            const platformPerformance = this.analyzePlatformTrends(recentEvents);

            // Content type analysis
            const contentAnalysis = this.analyzeContentTrends();

            // Hashtag performance
            const hashtagTrends = this.analyzeHashtagTrends();

            const analysis = {
                timeframe: timeframe,
                period: { start: startDate, end: now },
                viral_events: recentEvents.length,
                trending_products: trendingProducts.slice(0, 10),
                platform_performance: platformPerformance,
                content_trends: contentAnalysis,
                hashtag_trends: hashtagTrends,
                emerging_topics: this.identifyEmergingTopics(),
                predictions: this.generateViralPredictions(trendingProducts),
                recommendations: this.generateTrendRecommendations(trendingProducts, platformPerformance)
            };

            this.trendAnalysis.set(this.generateId('analysis'), analysis);

            return {
                success: true,
                trend_analysis: analysis
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    analyzePlatformTrends(events) {
        const platforms = {};
        
        events.forEach(event => {
            if (event.platform) {
                if (!platforms[event.platform]) {
                    platforms[event.platform] = {
                        events: 0,
                        total_growth: 0,
                        avg_duration: 0
                    };
                }
                platforms[event.platform].events += 1;
                platforms[event.platform].total_growth += event.metrics?.growth_rate || 0;
                platforms[event.platform].avg_duration += event.metrics?.duration_hours || 0;
            }
        });

        // Calculate averages
        Object.keys(platforms).forEach(platform => {
            const data = platforms[platform];
            data.avg_growth_rate = data.events > 0 ? data.total_growth / data.events : 0;
            data.avg_duration = data.events > 0 ? data.avg_duration / data.events : 0;
        });

        return platforms;
    }

    analyzeContentTrends() {
        // Analyze which content types perform best
        return {
            'demo_videos': { effectiveness: 8.7, viral_potential: 9.2 },
            'tutorials': { effectiveness: 7.8, viral_potential: 6.4 },
            'reviews': { effectiveness: 8.1, viral_potential: 7.8 },
            'comparisons': { effectiveness: 7.3, viral_potential: 5.9 },
            'installations': { effectiveness: 6.9, viral_potential: 4.2 }
        };
    }

    analyzeHashtagTrends() {
        return this.trendingHashtags.map(hashtag => ({
            ...hashtag,
            trend_direction: Math.random() > 0.5 ? 'rising' : 'stable',
            viral_potential: Math.round((hashtag.engagement * 0.7 + Math.random() * 3) * 10) / 10
        }));
    }

    identifyEmergingTopics() {
        return [
            { topic: 'Sustainable Electronics', momentum: 7.8, growth_rate: 156.3 },
            { topic: 'AI-Powered Tools', momentum: 8.9, growth_rate: 234.7 },
            { topic: 'Open Source Hardware', momentum: 6.4, growth_rate: 89.2 },
            { topic: 'Marine Conservation Tech', momentum: 8.1, growth_rate: 178.9 }
        ];
    }

    generateViralPredictions(trendingProducts) {
        return trendingProducts.slice(0, 5).map(product => ({
            product_id: product.id,
            name: product.name,
            current_viral_score: product.viral_score,
            predicted_peak_score: Math.min(product.viral_score * 1.3, 10),
            confidence: Math.round(Math.random() * 40 + 60), // 60-100%
            timeline: '7-14 days',
            key_factors: [
                'Strong engagement rate',
                'Multi-platform presence',
                'Positive sentiment trend'
            ]
        }));
    }

    generateTrendRecommendations(trendingProducts, platformPerformance) {
        const recommendations = [];

        // Platform recommendations
        const topPlatform = Object.entries(platformPerformance)
            .sort(([,a], [,b]) => b.avg_growth_rate - a.avg_growth_rate)[0];
        
        if (topPlatform) {
            recommendations.push(`Focus on ${topPlatform[0]} - showing highest growth rate of ${topPlatform[1].avg_growth_rate.toFixed(1)}%`);
        }

        // Content recommendations
        recommendations.push('Demo videos show highest viral potential - prioritize video content');
        recommendations.push('Cross-platform campaigns perform 40% better than single-platform');

        // Timing recommendations
        recommendations.push('Viral events typically peak within 18-24 hours of trigger');

        return recommendations;
    }

    // Real-time Monitoring
    async getViralDashboard() {
        try {
            const currentlyViral = Array.from(this.products.values())
                .filter(p => p.current_status === 'viral' || p.current_status === 'trending')
                .sort((a, b) => b.viral_score - a.viral_score);

            const recentEvents = Array.from(this.viralEvents.values())
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                .slice(0, 10);

            const activeCampaigns = Array.from(this.campaigns.values())
                .filter(c => c.status === 'active');

            const dashboard = {
                summary: {
                    viral_products: currentlyViral.length,
                    trending_products: currentlyViral.filter(p => p.current_status === 'trending').length,
                    active_campaigns: activeCampaigns.length,
                    total_reach_today: this.calculateDailyReach(),
                    viral_events_today: recentEvents.filter(e => 
                        new Date(e.timestamp).toDateString() === new Date().toDateString()
                    ).length
                },
                top_viral_products: currentlyViral.slice(0, 5),
                recent_viral_events: recentEvents,
                campaign_performance: activeCampaigns.map(c => ({
                    id: c.id,
                    name: c.name,
                    performance: this.assessCampaignPerformance(c)
                })),
                trending_hashtags: this.trendingHashtags.slice(0, 10),
                platform_activity: this.getPlatformActivity(),
                alerts: this.generateViralAlerts()
            };

            return {
                success: true,
                dashboard: dashboard,
                last_updated: new Date()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    calculateDailyReach() {
        const today = new Date().toDateString();
        return Array.from(this.products.values())
            .filter(p => new Date(p.launch_date).toDateString() === today)
            .reduce((sum, p) => sum + p.total_views, 0);
    }

    getPlatformActivity() {
        return {
            'twitter': { active_posts: 156, engagement: 12.4, reach: 89000 },
            'tiktok': { active_posts: 89, engagement: 8.9, reach: 456000 },
            'youtube': { active_posts: 23, engagement: 18.7, reach: 123000 },
            'reddit': { active_posts: 45, engagement: 15.2, reach: 67000 }
        };
    }

    generateViralAlerts() {
        const alerts = [];
        const now = new Date();

        // Check for viral spikes
        Array.from(this.products.values()).forEach(product => {
            if (product.viral_score >= 8 && product.current_status === 'viral') {
                alerts.push({
                    type: 'viral_spike',
                    product_id: product.id,
                    product_name: product.name,
                    message: `${product.name} is going viral! Score: ${product.viral_score}`,
                    severity: 'high',
                    timestamp: now
                });
            }
        });

        // Check for campaign underperformance
        Array.from(this.campaigns.values())
            .filter(c => c.status === 'active')
            .forEach(campaign => {
                const performance = this.assessCampaignPerformance(campaign);
                if (performance.percentage < 50) {
                    alerts.push({
                        type: 'campaign_underperforming',
                        campaign_id: campaign.id,
                        campaign_name: campaign.name,
                        message: `Campaign "${campaign.name}" is underperforming at ${performance.percentage}%`,
                        severity: 'medium',
                        timestamp: now
                    });
                }
            });

        return alerts;
    }
}

export default ViralProductTracking;