import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';
import cron from 'node-cron';

export class BudgetAllocationService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
    }

    async createBudget(orgId, departmentId, period, budgetData) {
        try {
            const budgetId = uuidv4();
            const budget = {
                id: budgetId,
                orgId,
                departmentId,
                period, // 'YYYY-MM' format
                totalBudget: budgetData.totalBudget.toString(),
                allocations: JSON.stringify(budgetData.allocations),
                restrictions: JSON.stringify(budgetData.restrictions || {}),
                approvedBy: budgetData.approvedBy,
                status: 'active',
                createdAt: Date.now()
            };
            
            await this.redis.hset(`budget:${budgetId}`, budget);
            await this.redis.set(`dept_budget:${departmentId}:${period}`, budgetId);
            
            return budget;
        } catch (error) {
            this.logger.error('Error creating budget:', error);
            throw error;
        }
    }

    async trackSpending(departmentId, category, amount, description, userId) {
        const spendingId = uuidv4();
        const period = moment().format('YYYY-MM');
        
        const spendingData = {
            id: spendingId,
            departmentId,
            category,
            amount: amount.toString(),
            description,
            userId,
            period,
            timestamp: Date.now()
        };
        
        await this.redis.hset(`spending:${spendingId}`, spendingData);
        await this.redis.sadd(`dept_spending:${departmentId}:${period}`, spendingId);
        
        // Update running totals
        await this.redis.incrbyfloat(`dept_total_spending:${departmentId}:${period}`, parseFloat(amount.toString()));
        await this.redis.incrbyfloat(`dept_category_spending:${departmentId}:${category}:${period}`, parseFloat(amount.toString()));
        
        // Check budget alerts
        await this.checkBudgetAlerts(departmentId, period);
        
        return spendingData;
    }

    async checkBudgetAlerts(departmentId, period) {
        const budgetId = await this.redis.get(`dept_budget:${departmentId}:${period}`);
        if (!budgetId) return;
        
        const budget = await this.redis.hgetall(`budget:${budgetId}`);
        const totalBudget = new Decimal(budget.totalBudget);
        const currentSpending = new Decimal(await this.redis.get(`dept_total_spending:${departmentId}:${period}`) || '0');
        
        const percentage = currentSpending.div(totalBudget).mul(100);
        
        if (percentage.gte(90) && this.broadcast) {
            this.broadcast(`usage-alerts-${budget.orgId}`, {
                type: 'budget_alert',
                level: 'critical',
                departmentId,
                period,
                percentage: percentage.toFixed(1),
                spent: currentSpending.toString(),
                budget: totalBudget.toString()
            });
        }
    }

    async getDepartmentBudgetStatus(departmentId, period) {
        const budgetId = await this.redis.get(`dept_budget:${departmentId}:${period}`);
        if (!budgetId) return null;
        
        const budget = await this.redis.hgetall(`budget:${budgetId}`);
        const totalSpent = await this.redis.get(`dept_total_spending:${departmentId}:${period}`) || '0';
        
        return {
            ...budget,
            totalSpent,
            remaining: new Decimal(budget.totalBudget).sub(new Decimal(totalSpent)).toString(),
            utilizationRate: new Decimal(totalSpent).div(new Decimal(budget.totalBudget)).mul(100).toFixed(1)
        };
    }

    async getStats() {
        const budgetKeys = await this.redis.keys('budget:*');
        let totalBudgets = new Decimal('0');
        let totalSpent = new Decimal('0');
        
        for (const key of budgetKeys) {
            const budget = await this.redis.hgetall(key);
            if (budget.status === 'active') {
                totalBudgets = totalBudgets.add(new Decimal(budget.totalBudget || '0'));
            }
        }
        
        const spendingKeys = await this.redis.keys('spending:*');
        for (const key of spendingKeys) {
            const spending = await this.redis.hgetall(key);
            totalSpent = totalSpent.add(new Decimal(spending.amount || '0'));
        }
        
        return {
            totalDepartments: budgetKeys.length,
            totalBudgets: totalBudgets.toString(),
            totalSpent: totalSpent.toString(),
            utilizationRate: totalBudgets.gt(0) ? totalSpent.div(totalBudgets).mul(100).toFixed(1) : '0'
        };
    }

    startScheduler() {
        // Monthly budget rollover
        cron.schedule('0 0 1 * *', async () => {
            await this.processBudgetRollover();
        });
    }

    async processBudgetRollover() {
        const currentMonth = moment().format('YYYY-MM');
        const lastMonth = moment().subtract(1, 'month').format('YYYY-MM');
        
        // Process rollover logic
        this.logger.info(`Processing budget rollover from ${lastMonth} to ${currentMonth}`);
    }

    stopScheduler() {
        this.logger.info('Budget allocation scheduler stopped');
    }
}