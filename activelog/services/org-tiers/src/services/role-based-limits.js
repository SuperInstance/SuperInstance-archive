import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';

export class RoleBasedLimitsService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
        
        this.defaultRoleLimits = {
            'admin': { cpu: 1000, gpu: 500, memory: 2000, storage: 10000, priority: 'high' },
            'manager': { cpu: 500, gpu: 100, memory: 1000, storage: 5000, priority: 'medium' },
            'developer': { cpu: 200, gpu: 50, memory: 500, storage: 2000, priority: 'medium' },
            'analyst': { cpu: 100, gpu: 20, memory: 200, storage: 1000, priority: 'low' },
            'viewer': { cpu: 10, gpu: 0, memory: 50, storage: 100, priority: 'low' }
        };
    }

    async setRoleLimits(orgId, role, limits) {
        const limitsData = {
            orgId,
            role,
            limits: JSON.stringify(limits),
            updatedAt: Date.now()
        };
        
        await this.redis.hset(`role_limits:${orgId}:${role}`, limitsData);
        return limitsData;
    }

    async getUserLimits(userId, role, orgId) {
        const orgLimits = await this.redis.hgetall(`role_limits:${orgId}:${role}`);
        if (orgLimits.limits) {
            return JSON.parse(orgLimits.limits);
        }
        
        return this.defaultRoleLimits[role] || this.defaultRoleLimits['viewer'];
    }

    async validateResourceRequest(userId, role, orgId, resourceType, requestedAmount) {
        const limits = await this.getUserLimits(userId, role, orgId);
        const userLimit = limits[resourceType] || 0;
        
        if (new Decimal(requestedAmount).gt(userLimit)) {
            return {
                allowed: false,
                reason: `Requested ${requestedAmount} ${resourceType} exceeds role limit of ${userLimit}`,
                limit: userLimit
            };
        }
        
        return { allowed: true, limit: userLimit };
    }

    async getStats() {
        const limitKeys = await this.redis.keys('role_limits:*');
        const roleStats = {};
        
        for (const key of limitKeys) {
            const parts = key.split(':');
            const role = parts[2];
            roleStats[role] = (roleStats[role] || 0) + 1;
        }
        
        return {
            totalRoleConfigurations: limitKeys.length,
            roleDistribution: roleStats
        };
    }
}