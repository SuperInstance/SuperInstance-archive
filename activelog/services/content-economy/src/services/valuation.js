import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';

export class ValuationService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
        
        this.valuationFactors = {
            'views': { weight: 0.2, formula: 'logarithmic' },
            'engagement': { weight: 0.25, formula: 'linear' },
            'uniqueness': { weight: 0.15, formula: 'exponential' },
            'creator_reputation': { weight: 0.2, formula: 'linear' },
            'market_demand': { weight: 0.2, formula: 'dynamic' }
        };
    }

    async calculateContentValue(contentId, metrics) {
        try {
            let totalScore = new Decimal('0');
            let baseValue = new Decimal('10.00'); // Base value
            
            for (const [factor, config] of Object.entries(this.valuationFactors)) {
                const metricValue = metrics[factor] || 0;
                const score = this.applyFormula(metricValue, config.formula);
                const weightedScore = score.mul(new Decimal(config.weight));
                totalScore = totalScore.add(weightedScore);
            }
            
            // Apply market conditions
            const marketMultiplier = await this.getMarketMultiplier(contentId);
            const finalValue = baseValue.add(totalScore.mul(baseValue)).mul(marketMultiplier);
            
            // Store valuation
            const valuationData = {
                contentId,
                value: finalValue.toString(),
                factors: JSON.stringify(metrics),
                calculatedAt: Date.now()
            };
            
            await this.redis.hset(`content_valuation:${contentId}`, valuationData);
            
            return finalValue;
        } catch (error) {
            this.logger.error('Error calculating content value:', error);
            throw error;
        }
    }
    
    applyFormula(value, formula) {
        const v = new Decimal(value);
        
        switch (formula) {
            case 'logarithmic':
                return new Decimal(Math.log(v.toNumber() + 1));
            case 'linear':
                return v.div(100); // Normalize
            case 'exponential':
                return v.pow(1.5).div(1000);
            case 'dynamic':
                return v.mul(this.getDynamicFactor());
            default:
                return v;
        }
    }
    
    getDynamicFactor() {
        // Market condition factor (0.5 to 2.0)
        return new Decimal(0.5 + Math.random() * 1.5);
    }
    
    async getMarketMultiplier(contentId) {
        // Get category demand, creator popularity, etc.
        const multiplier = await this.redis.get(`market_multiplier:${contentId}`);
        return new Decimal(multiplier || '1.0');
    }

    async updateMarketConditions(category, demandLevel) {
        const multiplier = this.calculateDemandMultiplier(demandLevel);
        await this.redis.set(`category_demand:${category}`, multiplier.toString());
    }
    
    calculateDemandMultiplier(demandLevel) {
        // Convert demand level (0-100) to multiplier (0.5-3.0)
        return new Decimal(0.5).add(new Decimal(demandLevel).div(100).mul(2.5));
    }

    async getContentValuation(contentId) {
        const valuation = await this.redis.hgetall(`content_valuation:${contentId}`);
        if (!valuation.contentId) {
            return null;
        }
        
        return {
            ...valuation,
            factors: JSON.parse(valuation.factors || '{}')
        };
    }

    async getStats() {
        const valuationKeys = await this.redis.keys('content_valuation:*');
        let totalValue = new Decimal('0');
        let highestValue = new Decimal('0');
        
        for (const key of valuationKeys) {
            const valuation = await this.redis.hgetall(key);
            const value = new Decimal(valuation.value || '0');
            totalValue = totalValue.add(value);
            if (value.gt(highestValue)) {
                highestValue = value;
            }
        }
        
        const averageValue = valuationKeys.length > 0 ? 
            totalValue.div(valuationKeys.length) : new Decimal('0');
        
        return {
            totalContentValuations: valuationKeys.length,
            totalMarketValue: totalValue.toString(),
            averageContentValue: averageValue.toString(),
            highestValuedContent: highestValue.toString()
        };
    }
}