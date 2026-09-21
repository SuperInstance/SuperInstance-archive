import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';

export class AnalyticsService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
    }

    async trackEvent(eventType, userId, contentId, metadata = {}) {
        try {
            const eventId = uuidv4();
            const timestamp = Date.now();
            
            const eventData = {
                id: eventId,
                type: eventType,
                userId,
                contentId,
                metadata: JSON.stringify(metadata),
                timestamp
            };
            
            // Store event
            await this.redis.hset(`analytics_event:${eventId}`, eventData);
            
            // Update aggregates
            const today = moment().format('YYYY-MM-DD');
            await this.redis.incr(`daily_events:${eventType}:${today}`);
            await this.redis.incr(`content_events:${contentId}:${eventType}`);
            await this.redis.incr(`user_events:${userId}:${eventType}`);
            
            return eventData;
        } catch (error) {
            this.logger.error('Error tracking event:', error);
            throw error;
        }
    }

    async getCreatorDashboard(creatorId, timeframe = '30d') {
        try {
            const cutoffTime = Date.now() - (timeframe === '7d' ? 7 : 30) * 24 * 60 * 60 * 1000;
            
            // Get earnings data
            const earnings = await this.getCreatorEarnings(creatorId, cutoffTime);
            
            // Get content performance
            const contentPerformance = await this.getContentPerformance(creatorId, cutoffTime);
            
            // Get audience insights
            const audienceInsights = await this.getAudienceInsights(creatorId);
            
            // Get engagement metrics
            const engagement = await this.getEngagementMetrics(creatorId, cutoffTime);
            
            return {
                creatorId,
                timeframe,
                earnings,
                contentPerformance,
                audienceInsights,
                engagement,
                generatedAt: Date.now()
            };
        } catch (error) {
            this.logger.error('Error generating creator dashboard:', error);
            throw error;
        }
    }

    async getCreatorEarnings(creatorId, cutoffTime) {
        let totalEarnings = new Decimal('0');
        const earningsSources = {
            payToPlay: new Decimal('0'),
            coffee: new Decimal('0'),
            subscriptions: new Decimal('0'),
            donations: new Decimal('0'),
            licensing: new Decimal('0'),
            royalties: new Decimal('0')
        };
        
        // Get pay-to-play earnings
        const accessKeys = await this.redis.keys('pay_to_play:*');
        for (const key of accessKeys) {
            const access = await this.redis.hgetall(key);
            if (access.creatorId === creatorId && 
                parseInt(access.createdAt) >= cutoffTime && 
                access.status === 'active') {
                const amount = new Decimal(access.cost || '0');
                earningsSources.payToPlay = earningsSources.payToPlay.add(amount);
                totalEarnings = totalEarnings.add(amount);
            }
        }
        
        // Get coffee earnings
        const coffeeKeys = await this.redis.keys('coffee_purchase:*');
        for (const key of coffeeKeys) {
            const coffee = await this.redis.hgetall(key);
            if (coffee.creatorId === creatorId && 
                parseInt(coffee.createdAt) >= cutoffTime && 
                coffee.status === 'completed') {
                const amount = new Decimal(coffee.amount || '0');
                earningsSources.coffee = earningsSources.coffee.add(amount);
                totalEarnings = totalEarnings.add(amount);
            }
        }
        
        // Convert to strings for JSON serialization
        const formattedSources = {};
        for (const [source, amount] of Object.entries(earningsSources)) {
            formattedSources[source] = amount.toString();
        }
        
        return {
            total: totalEarnings.toString(),
            sources: formattedSources,
            currency: 'USD'
        };
    }

    async getContentPerformance(creatorId, cutoffTime) {
        const performance = {
            totalViews: 0,
            totalDownloads: 0,
            totalShares: 0,
            topContent: [],
            recentContent: []
        };
        
        // Get aggregated metrics from Redis
        const contentKeys = await this.redis.keys('content_events:*');
        const contentMetrics = {};
        
        for (const key of contentKeys) {
            const parts = key.split(':');
            const contentId = parts[1];
            const eventType = parts[2];
            const count = await this.redis.get(key) || '0';
            
            if (!contentMetrics[contentId]) {
                contentMetrics[contentId] = { views: 0, downloads: 0, shares: 0 };
            }
            contentMetrics[contentId][eventType] = parseInt(count);
        }
        
        // Calculate totals and sort by performance
        const contentPerformanceArray = [];
        for (const [contentId, metrics] of Object.entries(contentMetrics)) {
            performance.totalViews += metrics.views || 0;
            performance.totalDownloads += metrics.downloads || 0;
            performance.totalShares += metrics.shares || 0;
            
            const score = (metrics.views || 0) + (metrics.downloads || 0) * 5 + (metrics.shares || 0) * 3;
            contentPerformanceArray.push({ contentId, ...metrics, score });
        }
        
        // Sort and get top content
        contentPerformanceArray.sort((a, b) => b.score - a.score);
        performance.topContent = contentPerformanceArray.slice(0, 10);
        
        return performance;
    }

    async getAudienceInsights(creatorId) {
        return {
            totalFollowers: await this.redis.scard(`creator_followers:${creatorId}`) || 0,
            activeSubscribers: await this.redis.scard(`creator_subscribers:${creatorId}`) || 0,
            returningVisitors: 0, // Would calculate from user analytics
            demographics: {
                regions: {},
                ageGroups: {},
                interests: []
            }
        };
    }

    async getEngagementMetrics(creatorId, cutoffTime) {
        const today = moment().format('YYYY-MM-DD');
        const yesterday = moment().subtract(1, 'day').format('YYYY-MM-DD');
        
        return {
            dailyActive: await this.redis.get(`daily_active:${creatorId}:${today}`) || '0',
            weeklyActive: await this.redis.get(`weekly_active:${creatorId}`) || '0',
            engagementRate: '0.0', // Would calculate from interaction data
            avgSessionDuration: '0', // Would track session lengths
            bounceRate: '0.0' // Would track single-page sessions
        };
    }

    async generateReports(creatorId, reportType, timeframe) {
        switch (reportType) {
            case 'revenue':
                return await this.generateRevenueReport(creatorId, timeframe);
            case 'audience':
                return await this.generateAudienceReport(creatorId, timeframe);
            case 'content':
                return await this.generateContentReport(creatorId, timeframe);
            default:
                throw new Error(`Unknown report type: ${reportType}`);
        }
    }

    async generateRevenueReport(creatorId, timeframe) {
        const cutoffTime = Date.now() - this.getTimeframeMs(timeframe);
        const earnings = await this.getCreatorEarnings(creatorId, cutoffTime);
        
        return {
            reportType: 'revenue',
            creatorId,
            timeframe,
            data: earnings,
            generatedAt: Date.now()
        };
    }

    getTimeframeMs(timeframe) {
        switch (timeframe) {
            case '7d': return 7 * 24 * 60 * 60 * 1000;
            case '30d': return 30 * 24 * 60 * 60 * 1000;
            case '90d': return 90 * 24 * 60 * 60 * 1000;
            case '1y': return 365 * 24 * 60 * 60 * 1000;
            default: return 30 * 24 * 60 * 60 * 1000;
        }
    }

    async getStats() {
        const eventKeys = await this.redis.keys('analytics_event:*');
        const totalEvents = eventKeys.length;
        
        const today = moment().format('YYYY-MM-DD');
        const dailyEvents = {};
        
        const eventTypes = ['views', 'downloads', 'purchases', 'shares'];
        for (const eventType of eventTypes) {
            const count = await this.redis.get(`daily_events:${eventType}:${today}`) || '0';
            dailyEvents[eventType] = parseInt(count);
        }
        
        return {
            totalEventsTracked: totalEvents,
            dailyEvents,
            activeCreators: await this.redis.scard('active_creators') || 0,
            totalRevenue: '0' // Would aggregate from all revenue sources
        };
    }
}