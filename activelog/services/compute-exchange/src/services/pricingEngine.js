import { getDb } from '../database/init.js';
import { logger } from '../utils/logger.js';
import moment from 'moment-timezone';
import Decimal from 'decimal.js';

export class PricingEngine {
  constructor() {
    this.basePrices = new Map();
    this.demandMultipliers = new Map();
    this.updateInterval = null;
  }

  async initializePricing() {
    try {
      await this.loadBasePrices();
      await this.calculateDemandMultipliers();
      this.startPriceUpdateScheduler();
      logger.info('Pricing engine initialized');
    } catch (error) {
      logger.error('Failed to initialize pricing engine:', error);
      throw error;
    }
  }

  async loadBasePrices() {
    const db = getDb();
    
    try {
      const prices = await new Promise((resolve, reject) => {
        db.all(`
          SELECT provider_id, job_type, quality_tier, base_rate, 
                 peak_multiplier, off_peak_multiplier, weekend_multiplier,
                 summer_multiplier, bulk_discount_threshold, bulk_discount_rate
          FROM pricing 
          WHERE effective_until IS NULL OR effective_until > datetime('now')
          ORDER BY effective_from DESC
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      this.basePrices.clear();
      prices.forEach(price => {
        const key = `${price.provider_id}-${price.job_type}-${price.quality_tier}`;
        this.basePrices.set(key, price);
      });

      logger.info(`Loaded ${prices.length} base pricing configurations`);
    } catch (error) {
      logger.error('Failed to load base prices:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async calculateDemandMultipliers() {
    const db = getDb();
    
    try {
      // Get current demand metrics for each provider
      const demandData = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            p.id as provider_id,
            COUNT(j.id) as active_jobs,
            COUNT(jq.id) as queued_jobs,
            p.total_cpu_cores,
            p.available_cpu_cores,
            (CAST(p.total_cpu_cores - p.available_cpu_cores AS REAL) / p.total_cpu_cores) as utilization
          FROM providers p
          LEFT JOIN jobs j ON p.id = j.provider_id AND j.status IN ('running', 'queued')
          LEFT JOIN job_queue jq ON j.id = jq.job_id
          WHERE p.status = 'active'
          GROUP BY p.id
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      const surgeThreshold = parseFloat(process.env.DEMAND_SURGE_THRESHOLD) || 0.8;
      const maxSurgeMultiplier = parseFloat(process.env.MAX_SURGE_MULTIPLIER) || 5.0;

      demandData.forEach(data => {
        let multiplier = 1.0;
        
        // Calculate demand multiplier based on utilization
        if (data.utilization > surgeThreshold) {
          const surgeRatio = (data.utilization - surgeThreshold) / (1 - surgeThreshold);
          multiplier = 1 + (surgeRatio * (maxSurgeMultiplier - 1));
        }
        
        // Factor in queue length
        if (data.queued_jobs > 0) {
          const queueMultiplier = Math.min(1 + (data.queued_jobs * 0.1), 2.0);
          multiplier *= queueMultiplier;
        }

        this.demandMultipliers.set(data.provider_id, Math.min(multiplier, maxSurgeMultiplier));
      });

      logger.info(`Updated demand multipliers for ${demandData.length} providers`);
    } catch (error) {
      logger.error('Failed to calculate demand multipliers:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async calculateJobPrice(jobRequest, providerId) {
    try {
      const priceKey = `${providerId}-${jobRequest.job_type}-${jobRequest.quality_tier}`;
      const basePrice = this.basePrices.get(priceKey);
      
      if (!basePrice) {
        throw new Error(`No pricing configuration found for provider ${providerId}, type ${jobRequest.job_type}, tier ${jobRequest.quality_tier}`);
      }

      let rate = new Decimal(basePrice.base_rate);
      
      // Apply time-based multipliers
      const timeMultiplier = await this.getTimeBasedMultiplier(basePrice, jobRequest.scheduled_start);
      rate = rate.mul(timeMultiplier);
      
      // Apply demand multiplier
      const demandMultiplier = this.demandMultipliers.get(providerId) || 1.0;
      rate = rate.mul(demandMultiplier);
      
      // Apply bulk discount if applicable
      const bulkMultiplier = await this.getBulkDiscountMultiplier(basePrice, jobRequest.user_id);
      rate = rate.mul(bulkMultiplier);
      
      // Calculate total cost based on estimated duration
      const estimatedHours = (jobRequest.estimated_duration_minutes || 60) / 60;
      const resourceUnits = this.calculateResourceUnits(jobRequest);
      const totalCost = rate.mul(resourceUnits).mul(estimatedHours);

      return {
        base_rate: basePrice.base_rate,
        current_rate: rate.toFixed(6),
        time_multiplier: timeMultiplier,
        demand_multiplier: demandMultiplier,
        bulk_multiplier: bulkMultiplier,
        estimated_cost: totalCost.toFixed(4),
        resource_units: resourceUnits,
        estimated_hours: estimatedHours
      };
    } catch (error) {
      logger.error('Failed to calculate job price:', error);
      throw error;
    }
  }

  async getTimeBasedMultiplier(basePrice, scheduledStart = null) {
    const now = scheduledStart ? moment(scheduledStart) : moment();
    const timezone = 'America/New_York'; // Default timezone, should be configurable per university
    const localTime = now.tz(timezone);
    
    let multiplier = 1.0;
    
    // Peak hours multiplier
    const peakStart = parseInt(process.env.PEAK_HOURS_START) || 8;
    const peakEnd = parseInt(process.env.PEAK_HOURS_END) || 18;
    const hour = localTime.hour();
    
    if (hour >= peakStart && hour < peakEnd && localTime.day() >= 1 && localTime.day() <= 5) {
      multiplier *= basePrice.peak_multiplier;
    } else {
      multiplier *= basePrice.off_peak_multiplier;
    }
    
    // Weekend multiplier
    if (localTime.day() === 0 || localTime.day() === 6) {
      multiplier *= basePrice.weekend_multiplier;
    }
    
    // Summer/academic break multiplier
    const month = localTime.month() + 1; // moment months are 0-based
    if (month >= 6 && month <= 8) { // Summer months
      multiplier *= basePrice.summer_multiplier;
    }
    
    return multiplier;
  }

  async getBulkDiscountMultiplier(basePrice, userId) {
    const db = getDb();
    
    try {
      // Check user's monthly usage
      const monthlyUsage = await new Promise((resolve, reject) => {
        db.get(`
          SELECT COALESCE(SUM(final_cost), 0) as monthly_spend
          FROM billing
          WHERE user_id = ? 
            AND billing_period_start >= date('now', 'start of month')
            AND billing_status IN ('approved', 'paid')
        `, [userId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      // Check if user qualifies for bulk discount
      if (monthlyUsage.monthly_spend >= basePrice.bulk_discount_threshold) {
        return 1 - basePrice.bulk_discount_rate;
      }

      // Check organization bulk rates
      const bulkRate = await new Promise((resolve, reject) => {
        db.get(`
          SELECT br.discount_percentage
          FROM bulk_rates br
          JOIN users u ON br.university_id = u.university_id
          WHERE u.id = ?
            AND br.status = 'active'
            AND br.contract_start <= datetime('now')
            AND br.contract_end >= datetime('now')
          ORDER BY br.discount_percentage DESC
          LIMIT 1
        `, [userId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (bulkRate) {
        return 1 - (bulkRate.discount_percentage / 100);
      }

      return 1.0;
    } catch (error) {
      logger.error('Failed to calculate bulk discount:', error);
      return 1.0;
    } finally {
      db.close();
    }
  }

  calculateResourceUnits(jobRequest) {
    // Calculate weighted resource units based on CPU, memory, storage, and GPU
    const cpuUnits = jobRequest.cpu_cores || 1;
    const memoryUnits = (jobRequest.memory_gb || 1) / 4; // 4GB = 1 unit
    const storageUnits = (jobRequest.storage_gb || 0) / 100; // 100GB = 1 unit
    const gpuUnits = (jobRequest.gpu_count || 0) * 8; // GPU = 8x CPU multiplier
    
    return Math.max(cpuUnits + memoryUnits + storageUnits + gpuUnits, 1);
  }

  async updatePricing(providerId, jobType, qualityTier, newRate, effectiveFrom = null) {
    const db = getDb();
    
    try {
      const effectiveDate = effectiveFrom || new Date().toISOString();
      
      // End current pricing
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE pricing 
          SET effective_until = ? 
          WHERE provider_id = ? AND job_type = ? AND quality_tier = ?
            AND effective_until IS NULL
        `, [effectiveDate, providerId, jobType, qualityTier], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Create new pricing
      await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO pricing (
            provider_id, job_type, quality_tier, base_rate, current_rate,
            peak_multiplier, off_peak_multiplier, weekend_multiplier,
            summer_multiplier, bulk_discount_threshold, bulk_discount_rate,
            effective_from
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `, [
          providerId, jobType, qualityTier, newRate, newRate,
          parseFloat(process.env.PEAK_MULTIPLIER) || 2.0,
          parseFloat(process.env.OFF_PEAK_MULTIPLIER) || 0.5,
          parseFloat(process.env.WEEKEND_DISCOUNT) || 0.7,
          parseFloat(process.env.SUMMER_DISCOUNT) || 0.6,
          parseFloat(process.env.BULK_DISCOUNT_THRESHOLD) || 1000,
          parseFloat(process.env.BULK_DISCOUNT_RATE) || 0.2,
          effectiveDate
        ], function(err) {
          if (err) reject(err);
          else resolve(this.lastID);
        });
      });

      // Reload base prices
      await this.loadBasePrices();
      
      logger.info(`Updated pricing for provider ${providerId}, ${jobType}, ${qualityTier}: ${newRate}`);
    } catch (error) {
      logger.error('Failed to update pricing:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async getCurrentRates(providerId = null, jobType = null, qualityTier = null) {
    const rates = [];
    
    for (const [key, basePrice] of this.basePrices) {
      const [pId, jType, qTier] = key.split('-');
      
      // Apply filters
      if (providerId && parseInt(pId) !== providerId) continue;
      if (jobType && jType !== jobType) continue;
      if (qualityTier && qTier !== qualityTier) continue;
      
      const demandMultiplier = this.demandMultipliers.get(parseInt(pId)) || 1.0;
      const timeMultiplier = await this.getTimeBasedMultiplier(basePrice);
      const currentRate = new Decimal(basePrice.base_rate)
        .mul(timeMultiplier)
        .mul(demandMultiplier);
      
      rates.push({
        provider_id: parseInt(pId),
        job_type: jType,
        quality_tier: qTier,
        base_rate: basePrice.base_rate,
        current_rate: currentRate.toFixed(6),
        time_multiplier: timeMultiplier,
        demand_multiplier: demandMultiplier,
        updated_at: new Date().toISOString()
      });
    }
    
    return rates;
  }

  startPriceUpdateScheduler() {
    const interval = parseInt(process.env.PRICE_UPDATE_INTERVAL) * 1000 || 300000; // 5 minutes
    
    this.updateInterval = setInterval(async () => {
      try {
        await this.calculateDemandMultipliers();
        logger.debug('Price multipliers updated');
      } catch (error) {
        logger.error('Scheduled price update failed:', error);
      }
    }, interval);
    
    logger.info('Price update scheduler started');
  }

  stopPriceUpdateScheduler() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
      logger.info('Price update scheduler stopped');
    }
  }
}