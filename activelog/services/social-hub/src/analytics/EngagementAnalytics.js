import { EventEmitter } from 'events';
import crypto from 'crypto';

class EngagementAnalytics extends EventEmitter {
    constructor(config = {}) {
        super();
        this.metrics = new Map();
        this.campaigns = new Map();
        this.reports = new Map();
        this.benchmarks = new Map();
        this.insights = new Map();
        this.predictions = new Map();
        this.realTimeData = new Map();
        this.audienceSegments = new Map();
        this.competitorData = new Map();

        this.initializeSystem();
    }

    initializeSystem() {
        this.initializeBenchmarks();
        this.initializeAudienceSegments();
        this.startRealTimeTracking();
        
        this.emit('analytics_system_initialized');
    }

    initializeBenchmarks() {
        const benchmarks = {
            twitter: {
                engagement_rate: { excellent: 3.0, good: 1.5, average: 0.9, poor: 0.5 },
                click_through_rate: { excellent: 1.5, good: 0.8, average: 0.5, poor: 0.2 },
                retweet_rate: { excellent: 1.2, good: 0.6, average: 0.3, poor: 0.1 },
                reply_rate: { excellent: 0.8, good: 0.4, average: 0.2, poor: 0.05 }
            },
            linkedin: {
                engagement_rate: { excellent: 4.0, good: 2.5, average: 1.5, poor: 0.8 },
                click_through_rate: { excellent: 0.8, good: 0.5, average: 0.3, poor: 0.15 },
                share_rate: { excellent: 0.6, good: 0.3, average: 0.15, poor: 0.05 },
                comment_rate: { excellent: 1.0, good: 0.5, average: 0.25, poor: 0.1 }
            },
            facebook: {
                engagement_rate: { excellent: 1.5, good: 0.9, average: 0.6, poor: 0.3 },
                click_through_rate: { excellent: 1.2, good: 0.7, average: 0.4, poor: 0.2 },
                share_rate: { excellent: 0.4, good: 0.2, average: 0.1, poor: 0.05 },
                reaction_rate: { excellent: 2.0, good: 1.0, average: 0.6, poor: 0.3 }
            },
            instagram: {
                engagement_rate: { excellent: 6.0, good: 3.5, average: 2.0, poor: 1.0 },
                like_rate: { excellent: 5.0, good: 3.0, average: 1.8, poor: 0.8 },
                comment_rate: { excellent: 0.8, good: 0.4, average: 0.2, poor: 0.08 },
                save_rate: { excellent: 1.2, good: 0.6, average: 0.3, poor: 0.1 }
            },
            youtube: {
                view_through_rate: { excellent: 60, good: 45, average: 30, poor: 15 },
                engagement_rate: { excellent: 8.0, good: 5.0, average: 3.0, poor: 1.5 },
                subscriber_conversion: { excellent: 2.5, good: 1.5, average: 0.8, poor: 0.3 },
                comment_rate: { excellent: 1.5, good: 0.8, average: 0.4, poor: 0.15 }
            }
        };

        Object.entries(benchmarks).forEach(([platform, metrics]) => {
            this.benchmarks.set(platform, metrics);
        });
    }

    initializeAudienceSegments() {
        const segments = [
            {
                id: 'tech_enthusiasts',
                name: 'Tech Enthusiasts',
                demographics: { age_range: '25-44', interests: ['technology', 'innovation', 'gadgets'] },
                behavior: { high_engagement_times: ['09:00', '12:00', '18:00'], preferred_content: 'educational' }
            },
            {
                id: 'makers_builders',
                name: 'Makers & Builders',
                demographics: { age_range: '20-50', interests: ['diy', 'hardware', 'programming'] },
                behavior: { high_engagement_times: ['10:00', '14:00', '20:00'], preferred_content: 'tutorials' }
            },
            {
                id: 'business_professionals',
                name: 'Business Professionals',
                demographics: { age_range: '30-55', interests: ['business', 'productivity', 'innovation'] },
                behavior: { high_engagement_times: ['08:00', '12:00', '17:00'], preferred_content: 'insights' }
            }
        ];

        segments.forEach(segment => {
            this.audienceSegments.set(segment.id, segment);
        });
    }

    startRealTimeTracking() {
        // Simulate real-time metric collection
        setInterval(() => {
            this.collectRealTimeMetrics();
        }, 60000); // Every minute
    }

    // Core analytics methods
    async trackEngagement(postData) {
        try {
            const metricId = crypto.randomBytes(16).toString('hex');
            const timestamp = new Date();

            const metric = {
                id: metricId,
                post_id: postData.post_id,
                platform: postData.platform,
                timestamp: timestamp,
                content_type: postData.content_type || 'text',
                metrics: {
                    impressions: postData.metrics.impressions || 0,
                    reach: postData.metrics.reach || 0,
                    engagement: postData.metrics.engagement || 0,
                    likes: postData.metrics.likes || 0,
                    comments: postData.metrics.comments || 0,
                    shares: postData.metrics.shares || 0,
                    clicks: postData.metrics.clicks || 0,
                    saves: postData.metrics.saves || 0
                },
                calculated_metrics: {}
            };

            // Calculate derived metrics
            metric.calculated_metrics = this.calculateDerivedMetrics(metric.metrics);

            // Add performance scoring
            metric.performance_score = this.calculatePerformanceScore(metric, postData.platform);

            // Store metric
            this.metrics.set(metricId, metric);

            // Update real-time data
            this.updateRealTimeData(metric);

            this.emit('engagement_tracked', { metric_id: metricId, metric });

            return {
                success: true,
                metric_id: metricId,
                performance_score: metric.performance_score
            };

        } catch (error) {
            this.emit('tracking_error', { postData, error });
            return { success: false, error: error.message };
        }
    }

    calculateDerivedMetrics(rawMetrics) {
        const derived = {};

        // Engagement rate
        if (rawMetrics.impressions > 0) {
            derived.engagement_rate = ((rawMetrics.engagement / rawMetrics.impressions) * 100).toFixed(2);
        }

        // Click-through rate
        if (rawMetrics.impressions > 0) {
            derived.click_through_rate = ((rawMetrics.clicks / rawMetrics.impressions) * 100).toFixed(2);
        }

        // Reach rate
        if (rawMetrics.impressions > 0) {
            derived.reach_rate = ((rawMetrics.reach / rawMetrics.impressions) * 100).toFixed(2);
        }

        // Share rate
        if (rawMetrics.reach > 0) {
            derived.share_rate = ((rawMetrics.shares / rawMetrics.reach) * 100).toFixed(2);
        }

        // Comment rate
        if (rawMetrics.reach > 0) {
            derived.comment_rate = ((rawMetrics.comments / rawMetrics.reach) * 100).toFixed(2);
        }

        // Save rate (for platforms that support it)
        if (rawMetrics.reach > 0 && rawMetrics.saves !== undefined) {
            derived.save_rate = ((rawMetrics.saves / rawMetrics.reach) * 100).toFixed(2);
        }

        return derived;
    }

    calculatePerformanceScore(metric, platform) {
        const benchmarks = this.benchmarks.get(platform);
        if (!benchmarks) return 50; // Default neutral score

        let score = 0;
        let weightSum = 0;

        // Score engagement rate
        if (metric.calculated_metrics.engagement_rate && benchmarks.engagement_rate) {
            const engagementScore = this.scoreAgainstBenchmark(
                parseFloat(metric.calculated_metrics.engagement_rate),
                benchmarks.engagement_rate
            );
            score += engagementScore * 0.4; // 40% weight
            weightSum += 0.4;
        }

        // Score CTR
        if (metric.calculated_metrics.click_through_rate && benchmarks.click_through_rate) {
            const ctrScore = this.scoreAgainstBenchmark(
                parseFloat(metric.calculated_metrics.click_through_rate),
                benchmarks.click_through_rate
            );
            score += ctrScore * 0.3; // 30% weight
            weightSum += 0.3;
        }

        // Score share/retweet rate
        if (metric.calculated_metrics.share_rate) {
            const shareRateBenchmark = benchmarks.share_rate || benchmarks.retweet_rate;
            if (shareRateBenchmark) {
                const shareScore = this.scoreAgainstBenchmark(
                    parseFloat(metric.calculated_metrics.share_rate),
                    shareRateBenchmark
                );
                score += shareScore * 0.2; // 20% weight
                weightSum += 0.2;
            }
        }

        // Score comment rate
        if (metric.calculated_metrics.comment_rate && benchmarks.comment_rate) {
            const commentScore = this.scoreAgainstBenchmark(
                parseFloat(metric.calculated_metrics.comment_rate),
                benchmarks.comment_rate
            );
            score += commentScore * 0.1; // 10% weight
            weightSum += 0.1;
        }

        return weightSum > 0 ? Math.round(score / weightSum) : 50;
    }

    scoreAgainstBenchmark(value, benchmark) {
        if (value >= benchmark.excellent) return 90;
        if (value >= benchmark.good) return 75;
        if (value >= benchmark.average) return 60;
        if (value >= benchmark.poor) return 40;
        return 25;
    }

    updateRealTimeData(metric) {
        const platform = metric.platform;
        const hour = new Date().getHours();

        if (!this.realTimeData.has(platform)) {
            this.realTimeData.set(platform, {
                hourly_metrics: new Array(24).fill(null).map(() => ({
                    impressions: 0,
                    engagement: 0,
                    posts: 0
                })),
                daily_totals: {
                    impressions: 0,
                    engagement: 0,
                    posts: 0,
                    avg_performance: 0
                }
            });
        }

        const platformData = this.realTimeData.get(platform);
        
        // Update hourly data
        platformData.hourly_metrics[hour].impressions += metric.metrics.impressions;
        platformData.hourly_metrics[hour].engagement += metric.metrics.engagement;
        platformData.hourly_metrics[hour].posts += 1;

        // Update daily totals
        platformData.daily_totals.impressions += metric.metrics.impressions;
        platformData.daily_totals.engagement += metric.metrics.engagement;
        platformData.daily_totals.posts += 1;
        platformData.daily_totals.avg_performance = 
            (platformData.daily_totals.avg_performance + metric.performance_score) / 2;

        this.realTimeData.set(platform, platformData);
    }

    // Campaign analytics
    async createCampaignTracking(campaignData) {
        try {
            const campaignId = crypto.randomBytes(16).toString('hex');

            const campaign = {
                id: campaignId,
                name: campaignData.name,
                start_date: new Date(campaignData.start_date),
                end_date: new Date(campaignData.end_date),
                platforms: campaignData.platforms || [],
                goals: campaignData.goals || {},
                target_metrics: campaignData.target_metrics || {},
                posts: [],
                metrics: {
                    total_impressions: 0,
                    total_engagement: 0,
                    total_clicks: 0,
                    total_conversions: 0
                },
                performance_by_platform: {},
                roi_tracking: {
                    investment: campaignData.investment || 0,
                    revenue: 0,
                    roi: 0
                },
                created_at: new Date()
            };

            this.campaigns.set(campaignId, campaign);
            this.emit('campaign_tracking_created', { campaign_id: campaignId });

            return {
                success: true,
                campaign_id: campaignId
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async addPostToCampaign(campaignId, postData) {
        try {
            const campaign = this.campaigns.get(campaignId);
            if (!campaign) {
                throw new Error('Campaign not found');
            }

            campaign.posts.push({
                post_id: postData.post_id,
                platform: postData.platform,
                timestamp: new Date(),
                content_type: postData.content_type
            });

            this.campaigns.set(campaignId, campaign);

            return { success: true };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async getCampaignAnalytics(campaignId) {
        try {
            const campaign = this.campaigns.get(campaignId);
            if (!campaign) {
                throw new Error('Campaign not found');
            }

            // Get metrics for all posts in campaign
            const campaignMetrics = this.getCampaignMetrics(campaign);
            
            // Calculate performance insights
            const insights = this.generateCampaignInsights(campaign, campaignMetrics);
            
            // Calculate ROI if applicable
            if (campaign.roi_tracking.investment > 0) {
                campaign.roi_tracking.roi = 
                    ((campaign.roi_tracking.revenue - campaign.roi_tracking.investment) / 
                     campaign.roi_tracking.investment * 100).toFixed(2);
            }

            return {
                success: true,
                campaign: campaign,
                metrics: campaignMetrics,
                insights: insights,
                roi: campaign.roi_tracking
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    getCampaignMetrics(campaign) {
        const metrics = {
            total_posts: campaign.posts.length,
            platform_breakdown: {},
            time_series: [],
            top_performing_posts: [],
            engagement_trends: []
        };

        // Get all metrics for campaign posts
        const campaignPostMetrics = Array.from(this.metrics.values())
            .filter(metric => 
                campaign.posts.some(post => post.post_id === metric.post_id)
            );

        // Calculate totals
        metrics.total_impressions = campaignPostMetrics.reduce((sum, m) => sum + m.metrics.impressions, 0);
        metrics.total_engagement = campaignPostMetrics.reduce((sum, m) => sum + m.metrics.engagement, 0);
        metrics.total_clicks = campaignPostMetrics.reduce((sum, m) => sum + m.metrics.clicks, 0);
        metrics.avg_engagement_rate = campaignPostMetrics.length > 0 ?
            campaignPostMetrics.reduce((sum, m) => sum + parseFloat(m.calculated_metrics.engagement_rate || 0), 0) / campaignPostMetrics.length :
            0;

        // Platform breakdown
        campaign.platforms.forEach(platform => {
            const platformMetrics = campaignPostMetrics.filter(m => m.platform === platform);
            metrics.platform_breakdown[platform] = {
                posts: platformMetrics.length,
                impressions: platformMetrics.reduce((sum, m) => sum + m.metrics.impressions, 0),
                engagement: platformMetrics.reduce((sum, m) => sum + m.metrics.engagement, 0),
                avg_performance: platformMetrics.length > 0 ?
                    platformMetrics.reduce((sum, m) => sum + m.performance_score, 0) / platformMetrics.length : 0
            };
        });

        // Top performing posts
        metrics.top_performing_posts = campaignPostMetrics
            .sort((a, b) => b.performance_score - a.performance_score)
            .slice(0, 5)
            .map(m => ({
                post_id: m.post_id,
                platform: m.platform,
                performance_score: m.performance_score,
                engagement_rate: m.calculated_metrics.engagement_rate
            }));

        return metrics;
    }

    generateCampaignInsights(campaign, metrics) {
        const insights = [];

        // Performance insights
        const avgPerformance = Object.values(metrics.platform_breakdown)
            .reduce((sum, p) => sum + p.avg_performance, 0) / campaign.platforms.length;

        if (avgPerformance >= 75) {
            insights.push({
                type: 'success',
                message: 'Campaign is performing excellently across all platforms',
                metric: 'overall_performance',
                value: avgPerformance.toFixed(1)
            });
        } else if (avgPerformance < 50) {
            insights.push({
                type: 'warning',
                message: 'Campaign performance is below expectations',
                metric: 'overall_performance',
                value: avgPerformance.toFixed(1),
                recommendation: 'Consider adjusting content strategy or posting times'
            });
        }

        // Platform insights
        const bestPlatform = Object.entries(metrics.platform_breakdown)
            .sort(([,a], [,b]) => b.avg_performance - a.avg_performance)[0];

        if (bestPlatform) {
            insights.push({
                type: 'info',
                message: `${bestPlatform[0]} is your best performing platform`,
                metric: 'platform_performance',
                value: bestPlatform[1].avg_performance.toFixed(1),
                recommendation: 'Consider increasing content frequency on this platform'
            });
        }

        // Engagement insights
        if (metrics.avg_engagement_rate > 3) {
            insights.push({
                type: 'success',
                message: 'High engagement rate achieved',
                metric: 'engagement_rate',
                value: `${metrics.avg_engagement_rate.toFixed(2)}%`
            });
        }

        return insights;
    }

    // Audience analytics
    async analyzeAudience(platform, timeframe = '30d') {
        try {
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(endDate.getDate() - (timeframe === '30d' ? 30 : 7));

            const platformMetrics = Array.from(this.metrics.values())
                .filter(m => m.platform === platform && m.timestamp >= startDate);

            const analysis = {
                platform: platform,
                timeframe: timeframe,
                total_posts: platformMetrics.length,
                engagement_patterns: this.analyzeEngagementPatterns(platformMetrics),
                content_performance: this.analyzeContentPerformance(platformMetrics),
                optimal_timing: this.findOptimalTiming(platformMetrics),
                audience_insights: this.generateAudienceInsights(platformMetrics)
            };

            return {
                success: true,
                analysis: analysis
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    analyzeEngagementPatterns(metrics) {
        const hourlyEngagement = new Array(24).fill(0);
        const dailyEngagement = new Array(7).fill(0);

        metrics.forEach(metric => {
            const date = new Date(metric.timestamp);
            const hour = date.getHours();
            const day = date.getDay();

            const engagementRate = parseFloat(metric.calculated_metrics.engagement_rate || 0);
            
            hourlyEngagement[hour] = (hourlyEngagement[hour] + engagementRate) / 2;
            dailyEngagement[day] = (dailyEngagement[day] + engagementRate) / 2;
        });

        return {
            hourly: hourlyEngagement.map((rate, hour) => ({ hour, engagement_rate: rate.toFixed(2) })),
            daily: dailyEngagement.map((rate, day) => ({ 
                day: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][day], 
                engagement_rate: rate.toFixed(2) 
            }))
        };
    }

    analyzeContentPerformance(metrics) {
        const contentTypes = {};

        metrics.forEach(metric => {
            const type = metric.content_type || 'text';
            
            if (!contentTypes[type]) {
                contentTypes[type] = {
                    count: 0,
                    total_engagement: 0,
                    total_impressions: 0,
                    avg_performance: 0
                };
            }

            contentTypes[type].count += 1;
            contentTypes[type].total_engagement += metric.metrics.engagement;
            contentTypes[type].total_impressions += metric.metrics.impressions;
            contentTypes[type].avg_performance = 
                (contentTypes[type].avg_performance + metric.performance_score) / 2;
        });

        // Calculate averages
        Object.values(contentTypes).forEach(type => {
            type.avg_engagement_rate = type.total_impressions > 0 ?
                ((type.total_engagement / type.total_impressions) * 100).toFixed(2) : 0;
        });

        return contentTypes;
    }

    findOptimalTiming(metrics) {
        const performanceByHour = {};

        metrics.forEach(metric => {
            const hour = new Date(metric.timestamp).getHours();
            
            if (!performanceByHour[hour]) {
                performanceByHour[hour] = {
                    posts: 0,
                    total_performance: 0,
                    avg_performance: 0
                };
            }

            performanceByHour[hour].posts += 1;
            performanceByHour[hour].total_performance += metric.performance_score;
            performanceByHour[hour].avg_performance = 
                performanceByHour[hour].total_performance / performanceByHour[hour].posts;
        });

        const bestHours = Object.entries(performanceByHour)
            .filter(([hour, data]) => data.posts >= 3) // Minimum 3 posts for statistical relevance
            .sort(([,a], [,b]) => b.avg_performance - a.avg_performance)
            .slice(0, 5)
            .map(([hour, data]) => ({
                hour: parseInt(hour),
                avg_performance: data.avg_performance.toFixed(1),
                sample_size: data.posts
            }));

        return {
            best_hours: bestHours,
            recommendation: bestHours.length > 0 ?
                `Post between ${bestHours[0].hour}:00-${bestHours[0].hour + 1}:00 for best performance` :
                'Insufficient data for timing recommendations'
        };
    }

    generateAudienceInsights(metrics) {
        const insights = [];

        // Engagement consistency
        const performanceScores = metrics.map(m => m.performance_score);
        const avgScore = performanceScores.reduce((sum, score) => sum + score, 0) / performanceScores.length;
        const variance = performanceScores.reduce((sum, score) => sum + Math.pow(score - avgScore, 2), 0) / performanceScores.length;

        if (variance < 100) {
            insights.push('Your audience engagement is very consistent');
        } else if (variance > 400) {
            insights.push('Your audience engagement varies significantly - consider A/B testing content types');
        }

        // Content preference
        const contentPerformance = this.analyzeContentPerformance(metrics);
        const bestContentType = Object.entries(contentPerformance)
            .sort(([,a], [,b]) => b.avg_performance - a.avg_performance)[0];

        if (bestContentType) {
            insights.push(`Your audience engages best with ${bestContentType[0]} content`);
        }

        return insights;
    }

    // Real-time monitoring
    collectRealTimeMetrics() {
        // Simulate real-time metric collection
        const platforms = ['twitter', 'linkedin', 'facebook', 'instagram'];
        
        platforms.forEach(platform => {
            if (Math.random() > 0.7) { // 30% chance of activity
                const mockMetric = this.generateMockMetric(platform);
                this.updateRealTimeData(mockMetric);
            }
        });

        this.emit('real_time_update', {
            timestamp: new Date(),
            platforms: Object.fromEntries(this.realTimeData)
        });
    }

    generateMockMetric(platform) {
        const baseMetrics = {
            twitter: { impressions: 500, engagement: 25, clicks: 8 },
            linkedin: { impressions: 300, engagement: 20, clicks: 6 },
            facebook: { impressions: 800, engagement: 35, clicks: 12 },
            instagram: { impressions: 600, engagement: 45, clicks: 10 }
        };

        const base = baseMetrics[platform];
        return {
            platform: platform,
            metrics: {
                impressions: base.impressions + Math.floor(Math.random() * 200),
                engagement: base.engagement + Math.floor(Math.random() * 20),
                clicks: base.clicks + Math.floor(Math.random() * 10)
            },
            performance_score: 50 + Math.floor(Math.random() * 40) // 50-90
        };
    }

    // Reporting
    async generateReport(reportConfig) {
        try {
            const reportId = crypto.randomBytes(16).toString('hex');
            const report = {
                id: reportId,
                type: reportConfig.type || 'platform_summary',
                period: reportConfig.period || '7d',
                platforms: reportConfig.platforms || ['twitter', 'linkedin'],
                generated_at: new Date(),
                data: {}
            };

            switch (report.type) {
                case 'platform_summary':
                    report.data = await this.generatePlatformSummaryReport(report.platforms, report.period);
                    break;
                case 'campaign_performance':
                    report.data = await this.generateCampaignPerformanceReport(reportConfig.campaign_id);
                    break;
                case 'audience_insights':
                    report.data = await this.generateAudienceReport(report.platforms, report.period);
                    break;
                case 'competitive_analysis':
                    report.data = await this.generateCompetitiveAnalysisReport(reportConfig);
                    break;
            }

            this.reports.set(reportId, report);
            this.emit('report_generated', { report_id: reportId, type: report.type });

            return {
                success: true,
                report_id: reportId,
                report: report
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async generatePlatformSummaryReport(platforms, period) {
        const endDate = new Date();
        const startDate = new Date();
        const days = period === '30d' ? 30 : 7;
        startDate.setDate(endDate.getDate() - days);

        const summary = {};

        for (const platform of platforms) {
            const platformMetrics = Array.from(this.metrics.values())
                .filter(m => m.platform === platform && m.timestamp >= startDate);

            summary[platform] = {
                total_posts: platformMetrics.length,
                total_impressions: platformMetrics.reduce((sum, m) => sum + m.metrics.impressions, 0),
                total_engagement: platformMetrics.reduce((sum, m) => sum + m.metrics.engagement, 0),
                avg_engagement_rate: platformMetrics.length > 0 ?
                    platformMetrics.reduce((sum, m) => sum + parseFloat(m.calculated_metrics.engagement_rate || 0), 0) / platformMetrics.length : 0,
                avg_performance_score: platformMetrics.length > 0 ?
                    platformMetrics.reduce((sum, m) => sum + m.performance_score, 0) / platformMetrics.length : 0,
                best_performing_post: platformMetrics.length > 0 ?
                    platformMetrics.sort((a, b) => b.performance_score - a.performance_score)[0] : null,
                growth_trend: this.calculateGrowthTrend(platformMetrics)
            };
        }

        return {
            period: { start: startDate, end: endDate },
            platform_summary: summary,
            overall_insights: this.generateOverallInsights(summary)
        };
    }

    calculateGrowthTrend(metrics) {
        if (metrics.length < 2) return 'insufficient_data';

        const sortedMetrics = metrics.sort((a, b) => a.timestamp - b.timestamp);
        const firstHalf = sortedMetrics.slice(0, Math.floor(sortedMetrics.length / 2));
        const secondHalf = sortedMetrics.slice(Math.floor(sortedMetrics.length / 2));

        const firstHalfAvg = firstHalf.reduce((sum, m) => sum + m.performance_score, 0) / firstHalf.length;
        const secondHalfAvg = secondHalf.reduce((sum, m) => sum + m.performance_score, 0) / secondHalf.length;

        const growthRate = ((secondHalfAvg - firstHalfAvg) / firstHalfAvg * 100);

        if (growthRate > 10) return 'improving';
        if (growthRate < -10) return 'declining';
        return 'stable';
    }

    generateOverallInsights(summary) {
        const insights = [];
        const platforms = Object.keys(summary);

        // Best performing platform
        const bestPlatform = platforms.reduce((best, current) => 
            summary[current].avg_performance_score > summary[best].avg_performance_score ? current : best
        );
        
        insights.push(`${bestPlatform} is your best performing platform with an average score of ${summary[bestPlatform].avg_performance_score.toFixed(1)}`);

        // Engagement insights
        const avgEngagement = platforms.reduce((sum, platform) => 
            sum + summary[platform].avg_engagement_rate, 0) / platforms.length;
        
        if (avgEngagement > 3) {
            insights.push('Excellent engagement rates across all platforms');
        } else if (avgEngagement < 1) {
            insights.push('Engagement rates need improvement - consider content strategy adjustment');
        }

        return insights;
    }

    // Utility methods
    getRealTimeDashboard() {
        const dashboard = {
            timestamp: new Date(),
            platforms: {},
            overall_metrics: {
                total_impressions: 0,
                total_engagement: 0,
                total_posts: 0,
                avg_performance: 0
            }
        };

        for (const [platform, data] of this.realTimeData) {
            dashboard.platforms[platform] = {
                daily_totals: data.daily_totals,
                current_hour: data.hourly_metrics[new Date().getHours()],
                trend: this.calculateHourlyTrend(data.hourly_metrics)
            };

            dashboard.overall_metrics.total_impressions += data.daily_totals.impressions;
            dashboard.overall_metrics.total_engagement += data.daily_totals.engagement;
            dashboard.overall_metrics.total_posts += data.daily_totals.posts;
        }

        const platformCount = Object.keys(dashboard.platforms).length;
        if (platformCount > 0) {
            dashboard.overall_metrics.avg_performance = 
                Object.values(dashboard.platforms)
                    .reduce((sum, p) => sum + p.daily_totals.avg_performance, 0) / platformCount;
        }

        return dashboard;
    }

    calculateHourlyTrend(hourlyMetrics) {
        const currentHour = new Date().getHours();
        const currentMetric = hourlyMetrics[currentHour];
        const previousMetric = hourlyMetrics[currentHour - 1] || { engagement: 0 };

        if (previousMetric.engagement === 0) return 'no_data';
        
        const change = ((currentMetric.engagement - previousMetric.engagement) / previousMetric.engagement) * 100;
        
        if (change > 20) return 'rising';
        if (change < -20) return 'falling';
        return 'stable';
    }

    getAnalyticsOverview() {
        return {
            total_metrics_tracked: this.metrics.size,
            active_campaigns: Array.from(this.campaigns.values()).filter(c => 
                new Date() >= c.start_date && new Date() <= c.end_date
            ).length,
            reports_generated: this.reports.size,
            real_time_platforms: this.realTimeData.size,
            last_updated: new Date()
        };
    }
}

export default EngagementAnalytics;