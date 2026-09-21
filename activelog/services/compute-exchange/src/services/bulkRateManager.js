import { getDb } from '../database/init.js';
import { logger } from '../utils/logger.js';
import Decimal from 'decimal.js';

export class BulkRateManager {
  constructor() {
    this.activeBulkRates = new Map();
  }

  async initialize() {
    try {
      await this.loadActiveBulkRates();
      this.startBulkRateMonitoring();
      logger.info('Bulk rate manager initialized');
    } catch (error) {
      logger.error('Failed to initialize bulk rate manager:', error);
      throw error;
    }
  }

  async loadActiveBulkRates() {
    const db = getDb();
    
    try {
      const bulkRates = await new Promise((resolve, reject) => {
        db.all(`
          SELECT br.*, u.name as university_name
          FROM bulk_rates br
          JOIN universities u ON br.university_id = u.id
          WHERE br.status = 'active'
            AND br.contract_start <= datetime('now')
            AND br.contract_end >= datetime('now')
          ORDER BY br.discount_percentage DESC
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      this.activeBulkRates.clear();
      bulkRates.forEach(rate => {
        const key = `${rate.university_id}-${rate.provider_id || 'all'}`;
        this.activeBulkRates.set(key, rate);
      });

      logger.info(`Loaded ${bulkRates.length} active bulk rate agreements`);
    } catch (error) {
      logger.error('Failed to load bulk rates:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async createBulkRateAgreement(agreementData) {
    const db = getDb();
    
    try {
      // Validate agreement data
      await this.validateBulkRateAgreement(agreementData);
      
      const result = await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO bulk_rates (
            university_id, provider_id, tier_name, minimum_monthly_spend,
            discount_percentage, cpu_hour_commitment, gpu_hour_commitment,
            contract_start, contract_end, auto_renew, status
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        `, [
          agreementData.university_id,
          agreementData.provider_id || null,
          agreementData.tier_name,
          agreementData.minimum_monthly_spend,
          agreementData.discount_percentage,
          agreementData.cpu_hour_commitment || 0,
          agreementData.gpu_hour_commitment || 0,
          agreementData.contract_start,
          agreementData.contract_end,
          agreementData.auto_renew ? 1 : 0
        ], function(err) {
          if (err) reject(err);
          else resolve({ id: this.lastID });
        });
      });

      // Reload active rates
      await this.loadActiveBulkRates();
      
      logger.info(`Bulk rate agreement created: ${result.id} for university ${agreementData.university_id}`);
      
      return result.id;
    } catch (error) {
      logger.error('Failed to create bulk rate agreement:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async validateBulkRateAgreement(agreementData) {
    const db = getDb();
    
    try {
      // Check university exists
      const university = await new Promise((resolve, reject) => {
        db.get('SELECT id FROM universities WHERE id = ? AND status = "active"', 
          [agreementData.university_id], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!university) {
        throw new Error('Invalid or inactive university ID');
      }

      // Check provider exists if specified
      if (agreementData.provider_id) {
        const provider = await new Promise((resolve, reject) => {
          db.get('SELECT id FROM providers WHERE id = ? AND status = "active"', 
            [agreementData.provider_id], (err, row) => {
            if (err) reject(err);
            else resolve(row);
          });
        });

        if (!provider) {
          throw new Error('Invalid or inactive provider ID');
        }
      }

      // Validate discount percentage
      if (agreementData.discount_percentage <= 0 || agreementData.discount_percentage > 50) {
        throw new Error('Discount percentage must be between 0.1 and 50');
      }

      // Validate minimum spend
      if (agreementData.minimum_monthly_spend < 100) {
        throw new Error('Minimum monthly spend must be at least $100');
      }

      // Validate contract dates
      const startDate = new Date(agreementData.contract_start);
      const endDate = new Date(agreementData.contract_end);
      const now = new Date();

      if (startDate >= endDate) {
        throw new Error('Contract end date must be after start date');
      }

      if (endDate <= now) {
        throw new Error('Contract end date must be in the future');
      }

      // Check for overlapping agreements
      const overlapping = await new Promise((resolve, reject) => {
        db.get(`
          SELECT id FROM bulk_rates 
          WHERE university_id = ? 
            AND (provider_id = ? OR provider_id IS NULL OR ? IS NULL)
            AND status = 'active'
            AND NOT (contract_end <= ? OR contract_start >= ?)
        `, [
          agreementData.university_id,
          agreementData.provider_id,
          agreementData.provider_id,
          agreementData.contract_start,
          agreementData.contract_end
        ], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (overlapping) {
        throw new Error('Overlapping bulk rate agreement already exists');
      }

    } catch (error) {
      throw error;
    } finally {
      db.close();
    }
  }

  async getBulkDiscount(universityId, providerId = null, monthlySpend = 0) {
    try {
      // Look for specific provider agreement first
      let bulkRate = null;
      
      if (providerId) {
        const providerKey = `${universityId}-${providerId}`;
        bulkRate = this.activeBulkRates.get(providerKey);
      }
      
      // If no provider-specific rate, look for university-wide rate
      if (!bulkRate) {
        const universityKey = `${universityId}-all`;
        bulkRate = this.activeBulkRates.get(universityKey);
      }
      
      if (!bulkRate) {
        return {
          has_bulk_rate: false,
          discount_percentage: 0,
          discount_multiplier: 1.0
        };
      }
      
      // Check if minimum spend requirement is met
      const meetsMinimum = monthlySpend >= parseFloat(bulkRate.minimum_monthly_spend);
      
      // Check commitment requirements if applicable
      let meetsCommitment = true;
      if (bulkRate.cpu_hour_commitment > 0 || bulkRate.gpu_hour_commitment > 0) {
        meetsCommitment = await this.checkCommitmentRequirements(universityId, bulkRate);
      }
      
      const qualifiesForDiscount = meetsMinimum && meetsCommitment;
      
      return {
        has_bulk_rate: true,
        qualifies_for_discount: qualifiesForDiscount,
        tier_name: bulkRate.tier_name,
        discount_percentage: qualifiesForDiscount ? bulkRate.discount_percentage : 0,
        discount_multiplier: qualifiesForDiscount ? (1 - bulkRate.discount_percentage / 100) : 1.0,
        minimum_monthly_spend: bulkRate.minimum_monthly_spend,
        current_monthly_spend: monthlySpend,
        cpu_hour_commitment: bulkRate.cpu_hour_commitment,
        gpu_hour_commitment: bulkRate.gpu_hour_commitment,
        contract_end: bulkRate.contract_end,
        provider_specific: !!providerId && !!bulkRate.provider_id
      };
    } catch (error) {
      logger.error('Failed to get bulk discount:', error);
      return {
        has_bulk_rate: false,
        discount_percentage: 0,
        discount_multiplier: 1.0,
        error: error.message
      };
    }
  }

  async checkCommitmentRequirements(universityId, bulkRate) {
    const db = getDb();
    
    try {
      const usage = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COALESCE(SUM(cpu_hours), 0) as total_cpu_hours,
            COALESCE(SUM(gpu_hours), 0) as total_gpu_hours
          FROM billing b
          JOIN users u ON b.user_id = u.id
          WHERE u.university_id = ?
            AND b.billing_period_start >= date('now', 'start of month')
            AND b.billing_status IN ('approved', 'paid')
        `, [universityId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      const cpuCommitmentMet = bulkRate.cpu_hour_commitment === 0 || 
                             usage.total_cpu_hours >= bulkRate.cpu_hour_commitment;
      const gpuCommitmentMet = bulkRate.gpu_hour_commitment === 0 || 
                             usage.total_gpu_hours >= bulkRate.gpu_hour_commitment;

      return cpuCommitmentMet && gpuCommitmentMet;
    } catch (error) {
      logger.error('Failed to check commitment requirements:', error);
      return false;
    } finally {
      db.close();
    }
  }

  async getUniversityBulkRates(universityId) {
    const db = getDb();
    
    try {
      const bulkRates = await new Promise((resolve, reject) => {
        db.all(`
          SELECT br.*, p.name as provider_name
          FROM bulk_rates br
          LEFT JOIN providers p ON br.provider_id = p.id
          WHERE br.university_id = ?
          ORDER BY br.contract_start DESC
        `, [universityId], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      // Add usage information for active agreements
      for (const rate of bulkRates) {
        if (rate.status === 'active') {
          const usage = await this.getBulkRateUsage(universityId, rate.id);
          rate.usage_info = usage;
        }
      }

      return bulkRates;
    } catch (error) {
      logger.error('Failed to get university bulk rates:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async getBulkRateUsage(universityId, bulkRateId) {
    const db = getDb();
    
    try {
      const usage = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(DISTINCT b.user_id) as active_users,
            COUNT(b.id) as total_jobs,
            COALESCE(SUM(b.final_cost), 0) as total_spend,
            COALESCE(SUM(b.cpu_hours), 0) as total_cpu_hours,
            COALESCE(SUM(b.gpu_hours), 0) as total_gpu_hours,
            COALESCE(AVG(b.final_cost), 0) as avg_job_cost
          FROM billing b
          JOIN users u ON b.user_id = u.id
          WHERE u.university_id = ?
            AND b.billing_period_start >= date('now', 'start of month')
            AND b.billing_status IN ('approved', 'paid')
        `, [universityId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      return {
        ...usage,
        total_spend: parseFloat(usage.total_spend).toFixed(4),
        avg_job_cost: parseFloat(usage.avg_job_cost).toFixed(4)
      };
    } catch (error) {
      logger.error('Failed to get bulk rate usage:', error);
      return null;
    } finally {
      db.close();
    }
  }

  async updateBulkRateStatus(bulkRateId, status, notes = '') {
    const db = getDb();
    
    try {
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE bulk_rates 
          SET status = ?, updated_at = CURRENT_TIMESTAMP 
          WHERE id = ?
        `, [status, bulkRateId], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Reload active rates if this was an active agreement
      if (status === 'suspended' || status === 'expired') {
        await this.loadActiveBulkRates();
      }

      logger.info(`Bulk rate ${bulkRateId} status updated to: ${status}`);
    } catch (error) {
      logger.error('Failed to update bulk rate status:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async renewBulkRate(bulkRateId, newEndDate, updateTerms = {}) {
    const db = getDb();
    
    try {
      // Get current bulk rate
      const currentRate = await new Promise((resolve, reject) => {
        db.get('SELECT * FROM bulk_rates WHERE id = ?', [bulkRateId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!currentRate) {
        throw new Error('Bulk rate not found');
      }

      // Create new agreement with updated terms
      const renewalData = {
        university_id: currentRate.university_id,
        provider_id: currentRate.provider_id,
        tier_name: updateTerms.tier_name || currentRate.tier_name,
        minimum_monthly_spend: updateTerms.minimum_monthly_spend || currentRate.minimum_monthly_spend,
        discount_percentage: updateTerms.discount_percentage || currentRate.discount_percentage,
        cpu_hour_commitment: updateTerms.cpu_hour_commitment !== undefined ? updateTerms.cpu_hour_commitment : currentRate.cpu_hour_commitment,
        gpu_hour_commitment: updateTerms.gpu_hour_commitment !== undefined ? updateTerms.gpu_hour_commitment : currentRate.gpu_hour_commitment,
        contract_start: currentRate.contract_end,
        contract_end: newEndDate,
        auto_renew: updateTerms.auto_renew !== undefined ? updateTerms.auto_renew : currentRate.auto_renew
      };

      const newRateId = await this.createBulkRateAgreement(renewalData);
      
      // Mark old agreement as expired
      await this.updateBulkRateStatus(bulkRateId, 'expired', 'Renewed with new agreement');
      
      logger.info(`Bulk rate ${bulkRateId} renewed as ${newRateId}`);
      
      return newRateId;
    } catch (error) {
      logger.error('Failed to renew bulk rate:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  startBulkRateMonitoring() {
    // Check for expiring agreements daily at 9 AM
    const checkExpiringRates = async () => {
      try {
        const db = getDb();
        
        // Find agreements expiring in 30 days
        const expiringRates = await new Promise((resolve, reject) => {
          db.all(`
            SELECT br.*, u.name as university_name, u.admin_email
            FROM bulk_rates br
            JOIN universities u ON br.university_id = u.id
            WHERE br.status = 'active'
              AND br.contract_end <= date('now', '+30 days')
              AND br.contract_end > date('now')
          `, (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
          });
        });

        for (const rate of expiringRates) {
          logger.warn(`Bulk rate agreement ${rate.id} for ${rate.university_name} expires on ${rate.contract_end}`);
          
          // Auto-renew if enabled
          if (rate.auto_renew) {
            try {
              const newEndDate = new Date(rate.contract_end);
              newEndDate.setFullYear(newEndDate.getFullYear() + 1);
              
              await this.renewBulkRate(rate.id, newEndDate.toISOString());
              logger.info(`Auto-renewed bulk rate ${rate.id} until ${newEndDate.toISOString()}`);
            } catch (error) {
              logger.error(`Failed to auto-renew bulk rate ${rate.id}:`, error);
            }
          }
        }
        
        db.close();
      } catch (error) {
        logger.error('Bulk rate monitoring error:', error);
      }
    };

    // Run daily at 9 AM
    setInterval(checkExpiringRates, 24 * 60 * 60 * 1000);
    
    // Run immediately on startup
    checkExpiringRates();
    
    logger.info('Bulk rate monitoring started');
  }

  async generateBulkRateReport(universityId, startDate, endDate) {
    const db = getDb();
    
    try {
      const report = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(b.id) as total_jobs,
            COUNT(DISTINCT b.user_id) as unique_users,
            COALESCE(SUM(b.base_cost), 0) as total_base_cost,
            COALESCE(SUM(b.discount_applied), 0) as total_discount,
            COALESCE(SUM(b.final_cost), 0) as total_final_cost,
            COALESCE(SUM(b.cpu_hours), 0) as total_cpu_hours,
            COALESCE(SUM(b.gpu_hours), 0) as total_gpu_hours,
            COALESCE(AVG(b.discount_applied / NULLIF(b.base_cost, 0) * 100), 0) as avg_discount_percent
          FROM billing b
          JOIN users u ON b.user_id = u.id
          WHERE u.university_id = ?
            AND b.billing_period_start >= ?
            AND b.billing_period_end <= ?
            AND b.billing_status IN ('approved', 'paid')
            AND b.discount_applied > 0
        `, [universityId, startDate, endDate], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      const bulkRates = await this.getUniversityBulkRates(universityId);
      const activeBulkRates = bulkRates.filter(rate => rate.status === 'active');

      return {
        period: { start_date: startDate, end_date: endDate },
        university_id: universityId,
        bulk_rate_summary: {
          active_agreements: activeBulkRates.length,
          total_potential_savings: parseFloat(report.total_discount).toFixed(4),
          average_discount_percent: parseFloat(report.avg_discount_percent).toFixed(2)
        },
        usage_summary: {
          ...report,
          total_base_cost: parseFloat(report.total_base_cost).toFixed(4),
          total_discount: parseFloat(report.total_discount).toFixed(4),
          total_final_cost: parseFloat(report.total_final_cost).toFixed(4),
          savings_percent: report.total_base_cost > 0 
            ? ((report.total_discount / report.total_base_cost) * 100).toFixed(2)
            : '0.00'
        },
        active_agreements: activeBulkRates
      };
    } catch (error) {
      logger.error('Failed to generate bulk rate report:', error);
      throw error;
    } finally {
      db.close();
    }
  }
}