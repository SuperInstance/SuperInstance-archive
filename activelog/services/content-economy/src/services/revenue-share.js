import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';

export class RevenueShareService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
    }

    async createRevenueShare(collaborationId, participants, shares, terms) {
        try {
            const shareId = uuidv4();
            const shareData = {
                id: shareId,
                collaborationId,
                participants: JSON.stringify(participants),
                shares: JSON.stringify(shares),
                terms: JSON.stringify(terms),
                totalRevenue: '0',
                createdAt: Date.now()
            };

            await this.redis.hset(`revenue_share:${shareId}`, shareData);
            return shareData;
        } catch (error) {
            this.logger.error('Error creating revenue share:', error);
            throw error;
        }
    }

    async distributeRevenue(shareId, revenue) {
        try {
            const shareData = await this.redis.hgetall(`revenue_share:${shareId}`);
            const shares = JSON.parse(shareData.shares);
            const totalRevenue = new Decimal(revenue);
            
            const distribution = {};
            for (const [participantId, percentage] of Object.entries(shares)) {
                distribution[participantId] = totalRevenue.mul(new Decimal(percentage)).div(100);
            }
            
            return distribution;
        } catch (error) {
            this.logger.error('Error distributing revenue:', error);
            throw error;
        }
    }

    async getStats() {
        const shareKeys = await this.redis.keys('revenue_share:*');
        let totalShares = shareKeys.length;
        let totalRevenue = new Decimal('0');
        
        for (const key of shareKeys) {
            const share = await this.redis.hgetall(key);
            totalRevenue = totalRevenue.add(new Decimal(share.totalRevenue || '0'));
        }
        
        return { totalShares, totalRevenue: totalRevenue.toString() };
    }
}