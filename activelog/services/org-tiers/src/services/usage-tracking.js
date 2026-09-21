import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';

export class UsageTrackingService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
    }

    async trackDepartmentUsage(orgId, departmentId, userId, resourceType, amount, metadata = {}) {
        try {
            const usageId = uuidv4();
            const timestamp = Date.now();
            const period = moment().format('YYYY-MM');
            const day = moment().format('YYYY-MM-DD');
            
            const usageData = {
                id: usageId,
                orgId,
                departmentId,
                userId,
                resourceType,
                amount: amount.toString(),
                metadata: JSON.stringify(metadata),
                timestamp,
                period,
                day
            };
            
            await this.redis.hset(`usage_record:${usageId}`, usageData);
            
            // Update aggregated metrics
            await this.updateUsageAggregates(orgId, departmentId, userId, resourceType, amount, period, day);
            
            return usageData;
        } catch (error) {
            this.logger.error('Error tracking department usage:', error);
            throw error;
        }
    }

    async updateUsageAggregates(orgId, departmentId, userId, resourceType, amount, period, day) {
        const amountFloat = parseFloat(amount.toString());
        
        // Organization level
        await this.redis.incrbyfloat(`org_usage:${orgId}:${resourceType}:${period}`, amountFloat);
        await this.redis.incrbyfloat(`org_usage_daily:${orgId}:${resourceType}:${day}`, amountFloat);
        
        // Department level
        await this.redis.incrbyfloat(`dept_usage:${departmentId}:${resourceType}:${period}`, amountFloat);
        await this.redis.incrbyfloat(`dept_usage_daily:${departmentId}:${resourceType}:${day}`, amountFloat);
        
        // User level
        await this.redis.incrbyfloat(`user_usage:${userId}:${resourceType}:${period}`, amountFloat);
        await this.redis.incrbyfloat(`user_usage_daily:${userId}:${resourceType}:${day}`, amountFloat);
        
        // Track unique users per department
        await this.redis.sadd(`dept_active_users:${departmentId}:${period}`, userId);
        await this.redis.sadd(`dept_active_users_daily:${departmentId}:${day}`, userId);
    }

    async getDepartmentUsageReport(departmentId, period = null, resourceType = null) {
        try {
            const reportPeriod = period || moment().format('YYYY-MM');
            const report = {
                departmentId,
                period: reportPeriod,
                totalUsage: {},
                userBreakdown: {},
                dailyTrends: {},
                topUsers: [],
                activeUsers: 0
            };
            
            const resourceTypes = resourceType ? [resourceType] : ['cpu', 'gpu', 'memory', 'storage', 'bandwidth'];
            
            for (const type of resourceTypes) {
                // Total department usage
                const totalUsage = await this.redis.get(`dept_usage:${departmentId}:${type}:${reportPeriod}`) || '0';
                report.totalUsage[type] = totalUsage;
                
                // Daily trends for the month
                const dailyTrends = {};
                const startDate = moment(reportPeriod, 'YYYY-MM').startOf('month');
                const endDate = moment(reportPeriod, 'YYYY-MM').endOf('month');
                
                for (let date = startDate.clone(); date.isSameOrBefore(endDate); date.add(1, 'day')) {
                    const day = date.format('YYYY-MM-DD');
                    const dailyUsage = await this.redis.get(`dept_usage_daily:${departmentId}:${type}:${day}`) || '0';
                    dailyTrends[day] = dailyUsage;
                }
                report.dailyTrends[type] = dailyTrends;
            }
            
            // Active users count
            report.activeUsers = await this.redis.scard(`dept_active_users:${departmentId}:${reportPeriod}`);
            
            // Top users by usage
            const activeUserIds = await this.redis.smembers(`dept_active_users:${departmentId}:${reportPeriod}`);
            const userUsageData = [];
            
            for (const userId of activeUserIds) {
                let totalUserUsage = new Decimal('0');
                const userBreakdown = {};
                
                for (const type of resourceTypes) {
                    const userUsage = await this.redis.get(`user_usage:${userId}:${type}:${reportPeriod}`) || '0';
                    userBreakdown[type] = userUsage;
                    totalUserUsage = totalUserUsage.add(new Decimal(userUsage));
                }
                
                userUsageData.push({
                    userId,
                    totalUsage: totalUserUsage.toString(),
                    breakdown: userBreakdown
                });
                
                report.userBreakdown[userId] = userBreakdown;
            }
            
            // Sort and get top 10 users
            report.topUsers = userUsageData
                .sort((a, b) => new Decimal(b.totalUsage).cmp(new Decimal(a.totalUsage)))
                .slice(0, 10);
            
            return report;
        } catch (error) {
            this.logger.error('Error generating department usage report:', error);
            throw error;
        }
    }

    async getOrganizationUsageReport(orgId, period = null) {
        try {
            const reportPeriod = period || moment().format('YYYY-MM');
            const report = {
                orgId,
                period: reportPeriod,
                totalUsage: {},
                departmentBreakdown: {},
                trends: {},
                summary: {
                    totalCost: new Decimal('0'),
                    totalUsers: 0,
                    totalDepartments: 0
                }
            };
            
            const resourceTypes = ['cpu', 'gpu', 'memory', 'storage', 'bandwidth'];
            
            // Get organization total usage
            for (const type of resourceTypes) {
                const totalUsage = await this.redis.get(`org_usage:${orgId}:${type}:${reportPeriod}`) || '0';
                report.totalUsage[type] = totalUsage;
            }
            
            // Get department breakdown
            const departments = await this.getOrganizationDepartments(orgId);
            report.summary.totalDepartments = departments.length;
            
            for (const deptId of departments) {
                const deptReport = await this.getDepartmentUsageReport(deptId, reportPeriod);
                report.departmentBreakdown[deptId] = deptReport;
                report.summary.totalUsers += deptReport.activeUsers;
            }
            
            return report;
        } catch (error) {
            this.logger.error('Error generating organization usage report:', error);
            throw error;
        }
    }

    async getOrganizationDepartments(orgId) {
        // This would typically come from organization service
        return await this.redis.smembers(`org_departments:${orgId}`) || [];
    }

    async setUsageLimits(departmentId, limits) {
        const limitsData = {
            departmentId,
            limits: JSON.stringify(limits),
            updatedAt: Date.now()
        };
        
        await this.redis.hset(`dept_usage_limits:${departmentId}`, limitsData);
        return limitsData;
    }

    async checkUsageLimits(departmentId, resourceType) {
        const limitsData = await this.redis.hgetall(`dept_usage_limits:${departmentId}`);
        if (!limitsData.limits) return { withinLimits: true };
        
        const limits = JSON.parse(limitsData.limits);
        const currentPeriod = moment().format('YYYY-MM');
        const currentUsage = await this.redis.get(`dept_usage:${departmentId}:${resourceType}:${currentPeriod}`) || '0';
        
        const limit = limits[resourceType];
        if (!limit) return { withinLimits: true };
        
        const usage = new Decimal(currentUsage);
        const limitAmount = new Decimal(limit.toString());
        
        return {
            withinLimits: usage.lte(limitAmount),
            currentUsage: usage.toString(),
            limit: limitAmount.toString(),
            percentageUsed: limitAmount.gt(0) ? usage.div(limitAmount).mul(100).toFixed(1) : '0'
        };
    }

    async getStats() {
        try {
            const currentPeriod = moment().format('YYYY-MM');
            const stats = {
                totalRecords: 0,
                totalDepartments: 0,
                totalActiveUsers: 0,
                resourceUsageTotals: {},
                topDepartmentsByUsage: []
            };
            
            // Count usage records
            const recordKeys = await this.redis.keys('usage_record:*');
            stats.totalRecords = recordKeys.length;
            
            // Count departments with usage
            const deptUsageKeys = await this.redis.keys(`dept_usage:*:*:${currentPeriod}`);
            const uniqueDepts = new Set(deptUsageKeys.map(key => key.split(':')[1]));
            stats.totalDepartments = uniqueDepts.size;
            
            // Calculate resource totals
            const resourceTypes = ['cpu', 'gpu', 'memory', 'storage', 'bandwidth'];
            for (const type of resourceTypes) {
                const orgUsageKeys = await this.redis.keys(`org_usage:*:${type}:${currentPeriod}`);
                let totalUsage = new Decimal('0');
                
                for (const key of orgUsageKeys) {
                    const usage = await this.redis.get(key) || '0';
                    totalUsage = totalUsage.add(new Decimal(usage));
                }
                
                stats.resourceUsageTotals[type] = totalUsage.toString();
            }
            
            return stats;
        } catch (error) {
            this.logger.error('Error getting usage tracking stats:', error);
            return {};
        }
    }
}