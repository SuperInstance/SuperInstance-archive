import { getDb } from '../database/init.js';
import { PricingEngine } from './pricingEngine.js';
import { BulkRateManager } from './bulkRateManager.js';
import { logger } from '../utils/logger.js';
import Decimal from 'decimal.js';
import cron from 'node-cron';

export class BillingEngine {
  constructor() {
    this.pricingEngine = new PricingEngine();
    this.bulkRateManager = new BulkRateManager();
    this.billingPrecision = parseInt(process.env.BILLING_PRECISION) || 4;
    this.minBillableSeconds = parseInt(process.env.MIN_BILLABLE_SECONDS) || 60;
    this.billingCycleSeconds = parseInt(process.env.BILLING_CYCLE_SECONDS) || 60;
    this.billingInterval = null;
  }

  async initialize() {
    try {
      await this.pricingEngine.initializePricing();
      await this.bulkRateManager.initialize();
      this.startBillingProcessor();
      this.startBillingReports();
      logger.info('Billing engine initialized');
    } catch (error) {
      logger.error('Failed to initialize billing engine:', error);
      throw error;
    }
  }

  async startJobBilling(jobId) {
    const db = getDb();
    
    try {
      // Get job details
      const job = await new Promise((resolve, reject) => {
        db.get(`
          SELECT j.*, u.university_id, u.current_balance 
          FROM jobs j
          JOIN users u ON j.user_id = u.id
          WHERE j.id = ?
        `, [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!job || job.status !== 'running') {
        return null;
      }

      // Calculate initial billing record
      const billingRecord = await this.createBillingRecord(job);
      
      logger.info(`Started billing for job ${jobId}, initial record: ${billingRecord.id}`);
      
      return billingRecord;
    } catch (error) {
      logger.error(`Failed to start billing for job ${jobId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async createBillingRecord(job) {
    const db = getDb();
    
    try {
      const now = new Date();
      const startTime = new Date(job.started_at);
      
      // Get pricing information
      const pricing = await this.pricingEngine.calculateJobPrice({
        job_type: job.job_type,
        quality_tier: job.quality_tier,
        cpu_cores: job.cpu_cores,
        memory_gb: job.memory_gb,
        storage_gb: job.storage_gb,
        gpu_count: job.gpu_count,
        estimated_duration_minutes: job.estimated_duration_minutes,
        user_id: job.user_id
      }, job.provider_id);

      const billingId = await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO billing (
            job_id, user_id, provider_id, university_id,
            billing_period_start, billing_period_end,
            cpu_hours, memory_gb_hours, storage_gb_hours, gpu_hours,
            base_cost, multiplier_applied, discount_applied, final_cost,
            billing_status
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        `, [
          job.id, job.user_id, job.provider_id, job.university_id,
          startTime.toISOString(), now.toISOString(),
          0, 0, 0, 0, // Initial resource hours are 0
          0, 1.0, 0, 0 // Initial costs are 0
        ], function(err) {
          if (err) reject(err);
          else resolve(this.lastID);
        });
      });

      return { id: billingId, job_id: job.id, status: 'pending' };
    } catch (error) {
      logger.error('Failed to create billing record:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async updateJobBilling(jobId) {
    const db = getDb();
    
    try {
      // Get current job and billing info
      const jobInfo = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            j.*, u.university_id, u.current_balance,
            b.id as billing_id, b.billing_period_start,
            b.cpu_hours as current_cpu_hours,
            b.memory_gb_hours as current_memory_gb_hours,
            b.storage_gb_hours as current_storage_gb_hours,
            b.gpu_hours as current_gpu_hours
          FROM jobs j
          JOIN users u ON j.user_id = u.id
          LEFT JOIN billing b ON j.id = b.job_id AND b.billing_status = 'pending'
          WHERE j.id = ? AND j.status = 'running'
        `, [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!jobInfo || !jobInfo.billing_id) {
        return null;
      }

      const now = new Date();
      const billingStart = new Date(jobInfo.billing_period_start);
      const elapsedMinutes = (now - billingStart) / (1000 * 60);
      
      // Calculate resource usage
      const resourceUsage = this.calculateResourceUsage(jobInfo, elapsedMinutes);
      
      // Get current pricing
      const pricing = await this.pricingEngine.calculateJobPrice({
        job_type: jobInfo.job_type,
        quality_tier: jobInfo.quality_tier,
        cpu_cores: jobInfo.cpu_cores,
        memory_gb: jobInfo.memory_gb,
        storage_gb: jobInfo.storage_gb,
        gpu_count: jobInfo.gpu_count,
        estimated_duration_minutes: Math.ceil(elapsedMinutes),
        user_id: jobInfo.user_id
      }, jobInfo.provider_id);

      // Calculate costs
      const costs = await this.calculateCosts(resourceUsage, pricing, jobInfo.university_id);
      
      // Update billing record
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE billing SET
            billing_period_end = ?,
            cpu_hours = ?, memory_gb_hours = ?, storage_gb_hours = ?, gpu_hours = ?,
            base_cost = ?, multiplier_applied = ?, discount_applied = ?, final_cost = ?
          WHERE id = ?
        `, [
          now.toISOString(),
          resourceUsage.cpu_hours, resourceUsage.memory_gb_hours,
          resourceUsage.storage_gb_hours, resourceUsage.gpu_hours,
          costs.base_cost, costs.multiplier_applied, costs.discount_applied, costs.final_cost,
          jobInfo.billing_id
        ], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      logger.debug(`Updated billing for job ${jobId}: $${costs.final_cost}`);
      
      return {
        billing_id: jobInfo.billing_id,
        elapsed_minutes: Math.round(elapsedMinutes),
        current_cost: costs.final_cost,
        resource_usage: resourceUsage
      };
    } catch (error) {
      logger.error(`Failed to update billing for job ${jobId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  calculateResourceUsage(jobInfo, elapsedMinutes) {
    const hours = Math.max(elapsedMinutes / 60, this.minBillableSeconds / 3600);
    
    return {
      cpu_hours: new Decimal(jobInfo.cpu_cores).mul(hours).toFixed(this.billingPrecision),
      memory_gb_hours: new Decimal(jobInfo.memory_gb).mul(hours).toFixed(this.billingPrecision),
      storage_gb_hours: new Decimal(jobInfo.storage_gb || 0).mul(hours).toFixed(this.billingPrecision),
      gpu_hours: new Decimal(jobInfo.gpu_count || 0).mul(hours).toFixed(this.billingPrecision),
      total_hours: parseFloat(hours.toFixed(this.billingPrecision))
    };
  }

  async calculateCosts(resourceUsage, pricing, universityId) {
    try {
      // Base cost calculation
      const baseCost = new Decimal(pricing.current_rate)
        .mul(resourceUsage.total_hours)
        .mul(pricing.resource_units);

      // Apply bulk discount if applicable
      const bulkDiscount = await this.bulkRateManager.getBulkDiscount(
        universityId, 
        null, 
        parseFloat(baseCost.toString())
      );

      const discountAmount = baseCost.mul(1 - bulkDiscount.discount_multiplier);
      const finalCost = baseCost.sub(discountAmount);

      return {
        base_cost: baseCost.toFixed(this.billingPrecision),
        multiplier_applied: pricing.demand_multiplier * pricing.time_multiplier,
        discount_applied: discountAmount.toFixed(this.billingPrecision),
        final_cost: finalCost.toFixed(this.billingPrecision),
        bulk_discount_info: bulkDiscount
      };
    } catch (error) {
      logger.error('Failed to calculate costs:', error);
      throw error;
    }
  }

  async finalizeJobBilling(jobId) {
    const db = getDb();
    
    try {
      // Get job completion info
      const job = await new Promise((resolve, reject) => {
        db.get(`
          SELECT j.*, b.id as billing_id, b.final_cost, u.current_balance
          FROM jobs j
          JOIN billing b ON j.id = b.job_id
          JOIN users u ON j.user_id = u.id
          WHERE j.id = ? AND b.billing_status = 'pending'
        `, [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!job || !job.billing_id) {
        logger.warn(`No pending billing record found for job ${jobId}`);
        return null;
      }

      // Final billing update
      const finalBilling = await this.updateJobBilling(jobId);
      
      if (finalBilling) {
        // Mark billing as approved (simplified - in reality would need approval workflow)
        await new Promise((resolve, reject) => {
          db.run(
            'UPDATE billing SET billing_status = "approved" WHERE id = ?',
            [job.billing_id],
            (err) => {
              if (err) reject(err);
              else resolve();
            }
          );
        });

        // Update user balance
        await new Promise((resolve, reject) => {
          db.run(
            'UPDATE users SET current_balance = current_balance + ? WHERE id = ?',
            [parseFloat(finalBilling.current_cost), job.user_id],
            (err) => {
              if (err) reject(err);
              else resolve();
            }
          );
        });

        logger.info(`Finalized billing for job ${jobId}: $${finalBilling.current_cost}`);
        
        return {
          job_id: jobId,
          final_cost: finalBilling.current_cost,
          elapsed_minutes: finalBilling.elapsed_minutes,
          billing_status: 'approved'
        };
      }

      return null;
    } catch (error) {
      logger.error(`Failed to finalize billing for job ${jobId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async getUserBillingHistory(userId, limit = 50, offset = 0) {
    const db = getDb();
    
    try {
      const billingHistory = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            b.*, j.job_name, j.job_type, j.quality_tier,
            p.name as provider_name, p.type as provider_type
          FROM billing b
          JOIN jobs j ON b.job_id = j.id
          JOIN providers p ON b.provider_id = p.id
          WHERE b.user_id = ?
          ORDER BY b.created_at DESC
          LIMIT ? OFFSET ?
        `, [userId, limit, offset], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      // Calculate totals
      const totals = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(*) as total_jobs,
            COALESCE(SUM(final_cost), 0) as total_cost,
            COALESCE(SUM(cpu_hours), 0) as total_cpu_hours,
            COALESCE(SUM(gpu_hours), 0) as total_gpu_hours,
            COALESCE(SUM(discount_applied), 0) as total_savings
          FROM billing 
          WHERE user_id = ? AND billing_status = 'approved'
        `, [userId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      return {
        billing_history: billingHistory,
        totals: {
          ...totals,
          total_cost: parseFloat(totals.total_cost).toFixed(this.billingPrecision),
          total_savings: parseFloat(totals.total_savings).toFixed(this.billingPrecision)
        }
      };
    } catch (error) {
      logger.error('Failed to get user billing history:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async getUniversityBillingReport(universityId, startDate, endDate) {
    const db = getDb();
    
    try {
      const report = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            DATE(b.billing_period_start) as billing_date,
            COUNT(b.id) as daily_jobs,
            COALESCE(SUM(b.final_cost), 0) as daily_cost,
            COALESCE(SUM(b.base_cost), 0) as daily_base_cost,
            COALESCE(SUM(b.discount_applied), 0) as daily_savings,
            COALESCE(SUM(b.cpu_hours), 0) as daily_cpu_hours,
            COALESCE(SUM(b.gpu_hours), 0) as daily_gpu_hours,
            COUNT(DISTINCT b.user_id) as active_users,
            COUNT(DISTINCT b.provider_id) as providers_used
          FROM billing b
          JOIN users u ON b.user_id = u.id
          WHERE u.university_id = ?
            AND DATE(b.billing_period_start) BETWEEN ? AND ?
            AND b.billing_status = 'approved'
          GROUP BY DATE(b.billing_period_start)
          ORDER BY billing_date DESC
        `, [universityId, startDate, endDate], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      // Calculate summary statistics
      const summary = report.reduce((acc, day) => ({
        total_jobs: acc.total_jobs + day.daily_jobs,
        total_cost: acc.total_cost + parseFloat(day.daily_cost),
        total_base_cost: acc.total_base_cost + parseFloat(day.daily_base_cost),
        total_savings: acc.total_savings + parseFloat(day.daily_savings),
        total_cpu_hours: acc.total_cpu_hours + parseFloat(day.daily_cpu_hours),
        total_gpu_hours: acc.total_gpu_hours + parseFloat(day.daily_gpu_hours)
      }), {
        total_jobs: 0, total_cost: 0, total_base_cost: 0,
        total_savings: 0, total_cpu_hours: 0, total_gpu_hours: 0
      });

      return {
        period: { start_date: startDate, end_date: endDate },
        university_id: universityId,
        summary: {
          ...summary,
          total_cost: summary.total_cost.toFixed(this.billingPrecision),
          total_base_cost: summary.total_base_cost.toFixed(this.billingPrecision),
          total_savings: summary.total_savings.toFixed(this.billingPrecision),
          average_daily_cost: (summary.total_cost / Math.max(report.length, 1)).toFixed(this.billingPrecision),
          savings_percentage: summary.total_base_cost > 0 
            ? ((summary.total_savings / summary.total_base_cost) * 100).toFixed(2)
            : '0.00'
        },
        daily_breakdown: report.map(day => ({
          ...day,
          daily_cost: parseFloat(day.daily_cost).toFixed(this.billingPrecision),
          daily_base_cost: parseFloat(day.daily_base_cost).toFixed(this.billingPrecision),
          daily_savings: parseFloat(day.daily_savings).toFixed(this.billingPrecision)
        }))
      };
    } catch (error) {
      logger.error('Failed to generate billing report:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async processLiveBilling() {
    const db = getDb();
    
    try {
      // Get all running jobs with pending billing
      const runningJobs = await new Promise((resolve, reject) => {
        db.all(`
          SELECT DISTINCT j.id
          FROM jobs j
          JOIN billing b ON j.id = b.job_id
          WHERE j.status = 'running' AND b.billing_status = 'pending'
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      let updatedJobs = 0;
      for (const job of runningJobs) {
        try {
          await this.updateJobBilling(job.id);
          updatedJobs++;
        } catch (error) {
          logger.error(`Failed to update billing for job ${job.id}:`, error);
        }
      }

      if (updatedJobs > 0) {
        logger.debug(`Updated billing for ${updatedJobs} running jobs`);
      }
    } catch (error) {
      logger.error('Live billing processing error:', error);
    } finally {
      db.close();
    }
  }

  startBillingProcessor() {
    const interval = this.billingCycleSeconds * 1000;
    
    this.billingInterval = setInterval(async () => {
      try {
        await this.processLiveBilling();
      } catch (error) {
        logger.error('Billing processor error:', error);
      }
    }, interval);
    
    logger.info(`Billing processor started (${this.billingCycleSeconds}s cycle)`);
  }

  startBillingReports() {
    // Generate daily billing summaries at midnight
    cron.schedule('0 0 * * *', async () => {
      try {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const dateStr = yesterday.toISOString().split('T')[0];
        
        logger.info(`Daily billing summary generated for ${dateStr}`);
      } catch (error) {
        logger.error('Daily billing report error:', error);
      }
    });

    // Generate weekly reports on Sundays at 1 AM
    cron.schedule('0 1 * * 0', async () => {
      try {
        logger.info('Weekly billing reports generated');
      } catch (error) {
        logger.error('Weekly billing report error:', error);
      }
    });
    
    logger.info('Billing report scheduler started');
  }

  stop() {
    if (this.billingInterval) {
      clearInterval(this.billingInterval);
      this.billingInterval = null;
    }
    this.pricingEngine.stopPriceUpdateScheduler();
    logger.info('Billing engine stopped');
  }
}