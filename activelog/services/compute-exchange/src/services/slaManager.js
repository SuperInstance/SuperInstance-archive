import { getDb } from '../database/init.js';
import { ReputationManager } from './reputationManager.js';
import { logger } from '../utils/logger.js';
import cron from 'node-cron';
import Decimal from 'decimal.js';

export class SLAManager {
  constructor() {
    this.reputationManager = new ReputationManager();
    this.monitoringInterval = null;
    this.slaConfigurations = new Map();
  }

  async initialize() {
    try {
      await this.loadSLAConfigurations();
      await this.reputationManager.initialize();
      this.startSLAMonitoring();
      this.startSLAReporting();
      logger.info('SLA manager initialized');
    } catch (error) {
      logger.error('Failed to initialize SLA manager:', error);
      throw error;
    }
  }

  async loadSLAConfigurations() {
    // Load default SLA configurations for each quality tier
    const defaultSLAs = {
      'basic': {
        uptime_guarantee: parseFloat(process.env.BASIC_TIER_SLA) || 95.0,
        max_response_time_ms: 30000,
        max_queue_time_minutes: 60,
        penalty_rate: 0.05,
        compensation_method: 'credit'
      },
      'standard': {
        uptime_guarantee: parseFloat(process.env.STANDARD_TIER_SLA) || 99.0,
        max_response_time_ms: 10000,
        max_queue_time_minutes: 30,
        penalty_rate: 0.1,
        compensation_method: 'credit'
      },
      'premium': {
        uptime_guarantee: parseFloat(process.env.PREMIUM_TIER_SLA) || 99.9,
        max_response_time_ms: 5000,
        max_queue_time_minutes: 15,
        penalty_rate: 0.15,
        compensation_method: 'refund'
      },
      'enterprise': {
        uptime_guarantee: parseFloat(process.env.ENTERPRISE_TIER_SLA) || 99.99,
        max_response_time_ms: 2000,
        max_queue_time_minutes: 5,
        penalty_rate: 0.25,
        compensation_method: 'refund'
      }
    };

    this.slaConfigurations.clear();
    for (const [tier, config] of Object.entries(defaultSLAs)) {
      this.slaConfigurations.set(tier, config);
    }

    // Load custom SLA agreements from database
    await this.loadCustomSLAs();

    logger.info(`Loaded SLA configurations for ${this.slaConfigurations.size} tiers`);
  }

  async loadCustomSLAs() {
    const db = getDb();
    
    try {
      const customSLAs = await new Promise((resolve, reject) => {
        db.all(`
          SELECT * FROM sla_agreements 
          WHERE status = 'active'
            AND effective_from <= datetime('now')
            AND (effective_until IS NULL OR effective_until > datetime('now'))
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      for (const sla of customSLAs) {
        const key = `${sla.provider_id}-${sla.quality_tier}`;
        this.slaConfigurations.set(key, {
          provider_id: sla.provider_id,
          quality_tier: sla.quality_tier,
          uptime_guarantee: sla.uptime_guarantee,
          max_response_time_ms: sla.max_response_time_ms,
          max_queue_time_minutes: sla.max_queue_time_minutes,
          penalty_rate: sla.penalty_rate,
          compensation_method: sla.compensation_method
        });
      }

      logger.info(`Loaded ${customSLAs.length} custom SLA agreements`);
    } catch (error) {
      logger.error('Failed to load custom SLAs:', error);
    } finally {
      db.close();
    }
  }

  getSLAForJob(job) {
    // Check for provider-specific SLA first
    const providerSLA = this.slaConfigurations.get(`${job.provider_id}-${job.quality_tier}`);
    if (providerSLA) {
      return providerSLA;
    }

    // Fall back to tier default SLA
    return this.slaConfigurations.get(job.quality_tier);
  }

  async checkJobSLACompliance(jobId) {
    const db = getDb();
    
    try {
      // Get job details with timing information
      const job = await new Promise((resolve, reject) => {
        db.get(`
          SELECT j.*, 
            (julianday(j.started_at) - julianday(j.created_at)) * 24 * 60 * 60 * 1000 as response_time_ms,
            (julianday(j.started_at) - julianday(j.created_at)) * 24 * 60 as queue_time_minutes,
            jq.estimated_wait_minutes
          FROM jobs j
          LEFT JOIN job_queue jq ON j.id = jq.job_id
          WHERE j.id = ? AND j.status IN ('running', 'completed', 'failed')
        `, [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!job) {
        return null;
      }

      const sla = this.getSLAForJob(job);
      if (!sla) {
        logger.debug(`No SLA configuration found for job ${jobId} (${job.quality_tier} tier)`);
        return null;
      }

      const violations = [];

      // Check response time (time from submission to start)
      if (job.response_time_ms && job.response_time_ms > sla.max_response_time_ms) {
        violations.push({
          type: 'response_time',
          expected_value: sla.max_response_time_ms,
          actual_value: job.response_time_ms,
          severity: this.calculateViolationSeverity(
            job.response_time_ms, 
            sla.max_response_time_ms, 
            'response_time'
          )
        });
      }

      // Check queue time
      if (job.queue_time_minutes && job.queue_time_minutes > sla.max_queue_time_minutes) {
        violations.push({
          type: 'queue_time',
          expected_value: sla.max_queue_time_minutes,
          actual_value: job.queue_time_minutes,
          severity: this.calculateViolationSeverity(
            job.queue_time_minutes,
            sla.max_queue_time_minutes,
            'queue_time'
          )
        });
      }

      // Check for availability violations (job failed due to provider issues)
      if (job.status === 'failed' && this.isProviderFailure(job.error_message)) {
        violations.push({
          type: 'availability',
          expected_value: sla.uptime_guarantee,
          actual_value: 0, // Complete failure
          severity: 'high'
        });
      }

      // Record violations
      if (violations.length > 0) {
        await this.recordSLAViolations(job, violations, sla);
      }

      return {
        job_id: jobId,
        sla_compliance: violations.length === 0,
        violations: violations,
        sla_config: sla
      };
    } catch (error) {
      logger.error(`Failed to check SLA compliance for job ${jobId}:`, error);
      return null;
    } finally {
      db.close();
    }
  }

  calculateViolationSeverity(actualValue, expectedValue, violationType) {
    const ratio = actualValue / expectedValue;
    
    if (ratio <= 1.2) return 'low';
    if (ratio <= 1.5) return 'medium';
    if (ratio <= 2.0) return 'high';
    return 'critical';
  }

  isProviderFailure(errorMessage) {
    if (!errorMessage) return false;
    
    const providerErrorIndicators = [
      'connection refused', 'timeout', 'network error', 'provider unavailable',
      'resource allocation failed', 'system error', 'internal server error',
      'service unavailable', 'provider error'
    ];
    
    const lowerError = errorMessage.toLowerCase();
    return providerErrorIndicators.some(indicator => lowerError.includes(indicator));
  }

  async recordSLAViolations(job, violations, sla) {
    const db = getDb();
    
    try {
      for (const violation of violations) {
        // Check if violation already recorded
        const existingViolation = await new Promise((resolve, reject) => {
          db.get(`
            SELECT id FROM sla_violations 
            WHERE job_id = ? AND violation_type = ? AND status != 'resolved'
          `, [job.id, violation.type], (err, row) => {
            if (err) reject(err);
            else resolve(row);
          });
        });

        if (existingViolation) {
          continue; // Skip if already recorded
        }

        // Find SLA agreement ID
        const slaAgreement = await new Promise((resolve, reject) => {
          db.get(`
            SELECT id FROM sla_agreements 
            WHERE provider_id = ? AND quality_tier = ? AND status = 'active'
            ORDER BY effective_from DESC LIMIT 1
          `, [job.provider_id, job.quality_tier], (err, row) => {
            if (err) reject(err);
            else resolve(row);
          });
        });

        // Calculate compensation
        const compensation = await this.calculateCompensation(job, violation, sla);

        // Record violation
        const violationId = await new Promise((resolve, reject) => {
          db.run(`
            INSERT INTO sla_violations (
              job_id, provider_id, sla_agreement_id, violation_type,
              expected_value, actual_value, impact_severity,
              compensation_amount, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'detected')
          `, [
            job.id, job.provider_id, slaAgreement?.id,
            violation.type, violation.expected_value, violation.actual_value,
            violation.severity, compensation.amount
          ], function(err) {
            if (err) reject(err);
            else resolve(this.lastID);
          });
        });

        // Record reputation impact
        const reputationRating = this.getSeverityReputationRating(violation.severity);
        await this.reputationManager.recordSLAViolation(
          job.provider_id, 
          job.id, 
          violation.type, 
          violation.severity
        );

        logger.warn(`SLA violation recorded: Job ${job.id}, Provider ${job.provider_id}, Type: ${violation.type}, Severity: ${violation.severity}`);
      }
    } catch (error) {
      logger.error('Failed to record SLA violations:', error);
    } finally {
      db.close();
    }
  }

  getSeverityReputationRating(severity) {
    const severityRatings = {
      'low': 4.0,
      'medium': 3.0,
      'high': 2.0,
      'critical': 1.0
    };
    return severityRatings[severity] || 3.0;
  }

  async calculateCompensation(job, violation, sla) {
    try {
      // Get job billing information
      const billing = await this.getJobBilling(job.id);
      if (!billing) {
        return { amount: 0, method: sla.compensation_method };
      }

      const jobCost = new Decimal(billing.final_cost || 0);
      const penaltyRate = new Decimal(sla.penalty_rate || 0.1);
      
      // Apply severity multiplier
      const severityMultipliers = {
        'low': 0.5,
        'medium': 1.0,
        'high': 1.5,
        'critical': 2.0
      };
      
      const severityMultiplier = new Decimal(severityMultipliers[violation.severity] || 1.0);
      const compensationAmount = jobCost.mul(penaltyRate).mul(severityMultiplier);

      return {
        amount: compensationAmount.toFixed(4),
        method: sla.compensation_method,
        calculation: {
          job_cost: jobCost.toString(),
          penalty_rate: penaltyRate.toString(),
          severity_multiplier: severityMultiplier.toString(),
          total: compensationAmount.toString()
        }
      };
    } catch (error) {
      logger.error('Failed to calculate SLA compensation:', error);
      return { amount: 0, method: sla.compensation_method };
    }
  }

  async getJobBilling(jobId) {
    const db = getDb();
    
    try {
      return await new Promise((resolve, reject) => {
        db.get(
          'SELECT * FROM billing WHERE job_id = ? ORDER BY created_at DESC LIMIT 1',
          [jobId],
          (err, row) => {
            if (err) reject(err);
            else resolve(row);
          }
        );
      });
    } catch (error) {
      logger.error('Failed to get job billing:', error);
      return null;
    } finally {
      db.close();
    }
  }

  async getProviderSLAMetrics(providerId, days = 30) {
    const db = getDb();
    
    try {
      // Get overall job statistics
      const jobStats = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(*) as total_jobs,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
            AVG(CASE WHEN started_at IS NOT NULL 
                THEN (julianday(started_at) - julianday(created_at)) * 24 * 60 * 60 * 1000 
                END) as avg_response_time_ms,
            AVG(CASE WHEN started_at IS NOT NULL 
                THEN (julianday(started_at) - julianday(created_at)) * 24 * 60 
                END) as avg_queue_time_minutes
          FROM jobs 
          WHERE provider_id = ?
            AND created_at > datetime('now', '-${days} days')
        `, [providerId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      // Get SLA violations
      const violations = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            violation_type,
            COUNT(*) as violation_count,
            AVG(compensation_amount) as avg_compensation,
            MAX(impact_severity) as max_severity
          FROM sla_violations 
          WHERE provider_id = ?
            AND detected_at > datetime('now', '-${days} days')
          GROUP BY violation_type
        `, [providerId], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      // Calculate uptime percentage
      const uptimePercent = jobStats.total_jobs > 0 
        ? (jobStats.completed_jobs / jobStats.total_jobs * 100)
        : 100;

      // Get SLA configuration for default quality tier
      const defaultSLA = this.slaConfigurations.get('standard') || {};

      return {
        provider_id: providerId,
        period_days: days,
        overall_metrics: {
          total_jobs: jobStats.total_jobs,
          success_rate: uptimePercent.toFixed(2),
          avg_response_time_ms: Math.round(jobStats.avg_response_time_ms || 0),
          avg_queue_time_minutes: Math.round(jobStats.avg_queue_time_minutes || 0)
        },
        sla_compliance: {
          uptime_target: defaultSLA.uptime_guarantee || 99.0,
          uptime_actual: uptimePercent,
          uptime_compliant: uptimePercent >= (defaultSLA.uptime_guarantee || 99.0),
          response_time_target: defaultSLA.max_response_time_ms || 10000,
          response_time_actual: Math.round(jobStats.avg_response_time_ms || 0),
          response_time_compliant: (jobStats.avg_response_time_ms || 0) <= (defaultSLA.max_response_time_ms || 10000)
        },
        violations: violations,
        violation_summary: {
          total_violations: violations.reduce((sum, v) => sum + v.violation_count, 0),
          total_compensation: violations.reduce((sum, v) => sum + (parseFloat(v.avg_compensation) || 0), 0).toFixed(4)
        }
      };
    } catch (error) {
      logger.error(`Failed to get SLA metrics for provider ${providerId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async generateSLAReport(universityId = null, startDate = null, endDate = null) {
    const db = getDb();
    
    try {
      const start = startDate || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      const end = endDate || new Date().toISOString();

      // Build query conditions
      let whereClause = 'WHERE sv.detected_at BETWEEN ? AND ?';
      let params = [start, end];
      
      if (universityId) {
        whereClause += ' AND p.university_id = ?';
        params.push(universityId);
      }

      const reportData = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            p.id as provider_id, p.name as provider_name, p.university_id,
            u.name as university_name,
            sv.violation_type, sv.impact_severity,
            COUNT(*) as violation_count,
            AVG(sv.compensation_amount) as avg_compensation,
            SUM(sv.compensation_amount) as total_compensation,
            MIN(sv.detected_at) as first_violation,
            MAX(sv.detected_at) as last_violation
          FROM sla_violations sv
          JOIN providers p ON sv.provider_id = p.id
          JOIN universities u ON p.university_id = u.id
          ${whereClause}
          GROUP BY p.id, sv.violation_type, sv.impact_severity
          ORDER BY total_compensation DESC
        `, params, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      // Calculate summary statistics
      const summary = reportData.reduce((acc, row) => {
        acc.total_violations += row.violation_count;
        acc.total_compensation += parseFloat(row.total_compensation);
        acc.affected_providers.add(row.provider_id);
        acc.affected_universities.add(row.university_id);
        return acc;
      }, {
        total_violations: 0,
        total_compensation: 0,
        affected_providers: new Set(),
        affected_universities: new Set()
      });

      return {
        report_period: { start_date: start, end_date: end },
        summary: {
          total_violations: summary.total_violations,
          total_compensation: summary.total_compensation.toFixed(4),
          affected_providers: summary.affected_providers.size,
          affected_universities: summary.affected_universities.size
        },
        violations_by_provider: reportData,
        generated_at: new Date().toISOString()
      };
    } catch (error) {
      logger.error('Failed to generate SLA report:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async resolveSLAViolation(violationId, resolutionNotes = '') {
    const db = getDb();
    
    try {
      // Get violation details
      const violation = await new Promise((resolve, reject) => {
        db.get(
          'SELECT * FROM sla_violations WHERE id = ?',
          [violationId],
          (err, row) => {
            if (err) reject(err);
            else resolve(row);
          }
        );
      });

      if (!violation) {
        throw new Error('SLA violation not found');
      }

      // Update violation status
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE sla_violations 
          SET status = 'resolved', 
              resolution_notes = ?,
              resolved_at = CURRENT_TIMESTAMP
          WHERE id = ?
        `, [resolutionNotes, violationId], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Apply compensation if applicable
      if (violation.compensation_amount > 0) {
        await this.applyCompensation(violation);
      }

      logger.info(`SLA violation ${violationId} resolved with compensation $${violation.compensation_amount}`);
      
      return {
        violation_id: violationId,
        resolution_status: 'resolved',
        compensation_applied: violation.compensation_amount,
        resolved_at: new Date().toISOString()
      };
    } catch (error) {
      logger.error(`Failed to resolve SLA violation ${violationId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async applyCompensation(violation) {
    const db = getDb();
    
    try {
      // Get job and user information
      const jobInfo = await new Promise((resolve, reject) => {
        db.get(`
          SELECT j.user_id, j.id as job_id, u.current_balance
          FROM jobs j
          JOIN users u ON j.user_id = u.id
          WHERE j.id = ?
        `, [violation.job_id], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!jobInfo) {
        throw new Error('Job information not found for compensation');
      }

      // Apply compensation based on method
      if (violation.compensation_method === 'credit') {
        // Add credit to user account
        await new Promise((resolve, reject) => {
          db.run(
            'UPDATE users SET current_balance = current_balance + ? WHERE id = ?',
            [violation.compensation_amount, jobInfo.user_id],
            (err) => {
              if (err) reject(err);
              else resolve();
            }
          );
        });

        logger.info(`Applied SLA credit compensation: $${violation.compensation_amount} to user ${jobInfo.user_id}`);
      } else if (violation.compensation_method === 'refund') {
        // Process refund (simplified - in practice would integrate with payment processor)
        logger.info(`SLA refund compensation processed: $${violation.compensation_amount} for user ${jobInfo.user_id}`);
      }
    } catch (error) {
      logger.error('Failed to apply SLA compensation:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async startSLAMonitoring() {
    const checkInterval = parseInt(process.env.SLA_CHECK_INTERVAL) * 1000 || 300000; // Default 5 minutes
    
    this.monitoringInterval = setInterval(async () => {
      try {
        await this.monitorActiveSLAs();
      } catch (error) {
        logger.error('SLA monitoring error:', error);
      }
    }, checkInterval);
    
    logger.info('SLA monitoring started');
  }

  async monitorActiveSLAs() {
    const db = getDb();
    
    try {
      // Get recently completed/failed jobs that need SLA checking
      const recentJobs = await new Promise((resolve, reject) => {
        db.all(`
          SELECT DISTINCT j.id
          FROM jobs j
          LEFT JOIN sla_violations sv ON j.id = sv.job_id
          WHERE j.status IN ('completed', 'failed')
            AND j.updated_at > datetime('now', '-1 hour')
            AND sv.id IS NULL
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      for (const job of recentJobs) {
        try {
          await this.checkJobSLACompliance(job.id);
        } catch (error) {
          logger.error(`Failed to check SLA compliance for job ${job.id}:`, error);
        }
      }

      if (recentJobs.length > 0) {
        logger.debug(`Checked SLA compliance for ${recentJobs.length} jobs`);
      }
    } catch (error) {
      logger.error('Failed to monitor active SLAs:', error);
    } finally {
      db.close();
    }
  }

  startSLAReporting() {
    // Generate daily SLA reports at 7 AM
    cron.schedule('0 7 * * *', async () => {
      try {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        
        const report = await this.generateSLAReport(
          null, 
          yesterday.toISOString().split('T')[0],
          new Date().toISOString().split('T')[0]
        );
        
        if (report.summary.total_violations > 0) {
          logger.warn(`Daily SLA Report: ${report.summary.total_violations} violations, $${report.summary.total_compensation} in compensation`);
        } else {
          logger.info('Daily SLA Report: No violations detected');
        }
      } catch (error) {
        logger.error('Daily SLA report generation failed:', error);
      }
    });

    // Generate weekly SLA summary on Mondays at 8 AM
    cron.schedule('0 8 * * 1', async () => {
      try {
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        
        const report = await this.generateSLAReport(
          null,
          weekAgo.toISOString().split('T')[0],
          new Date().toISOString().split('T')[0]
        );
        
        logger.info(`Weekly SLA Summary: ${report.summary.total_violations} violations, ${report.summary.affected_providers} providers affected`);
      } catch (error) {
        logger.error('Weekly SLA report generation failed:', error);
      }
    });
    
    logger.info('SLA reporting scheduler started');
  }

  stop() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    logger.info('SLA manager stopped');
  }
}