import { getDb } from '../database/init.js';
import { ProviderManager } from './providerManager.js';
import { ReputationManager } from './reputationManager.js';
import { PricingEngine } from './pricingEngine.js';
import { logger } from '../utils/logger.js';

export class FailoverManager {
  constructor() {
    this.providerManager = new ProviderManager();
    this.reputationManager = new ReputationManager();
    this.pricingEngine = new PricingEngine();
    this.failoverEnabled = process.env.FAILOVER_ENABLED === 'true';
    this.failoverThresholdSeconds = parseInt(process.env.FAILOVER_THRESHOLD_SECONDS) || 30;
    this.maxFailoverAttempts = parseInt(process.env.MAX_FAILOVER_ATTEMPTS) || 3;
    this.failoverCooldownMinutes = parseInt(process.env.FAILOVER_COOLDOWN_MINUTES) || 5;
    this.monitoringInterval = null;
    this.failoverCooldowns = new Map(); // Track cooldowns per provider
  }

  async initialize() {
    try {
      if (this.failoverEnabled) {
        await this.startFailoverMonitoring();
        logger.info('Failover manager initialized and enabled');
      } else {
        logger.info('Failover manager initialized but disabled');
      }
    } catch (error) {
      logger.error('Failed to initialize failover manager:', error);
      throw error;
    }
  }

  async checkJobForFailover(jobId) {
    const db = getDb();
    
    try {
      // Get job details
      const job = await new Promise((resolve, reject) => {
        db.get(`
          SELECT j.*, up.auto_failover
          FROM jobs j
          JOIN users u ON j.user_id = u.id
          LEFT JOIN user_preferences up ON u.id = up.user_id
          WHERE j.id = ? AND j.status = 'running'
        `, [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!job) {
        return null;
      }

      // Check if user has auto-failover enabled
      if (!job.auto_failover) {
        logger.debug(`Job ${jobId} - user has auto-failover disabled`);
        return null;
      }

      // Check if job has been running too long without updates
      const startTime = new Date(job.started_at);
      const now = new Date();
      const runningSeconds = (now - startTime) / 1000;

      // Define failover triggers
      const shouldFailover = await this.evaluateFailoverConditions(job, runningSeconds);
      
      if (shouldFailover.trigger) {
        return await this.initiateFailover(jobId, shouldFailover.reason);
      }

      return null;
    } catch (error) {
      logger.error(`Failed to check job ${jobId} for failover:`, error);
      return null;
    } finally {
      db.close();
    }
  }

  async evaluateFailoverConditions(job, runningSeconds) {
    try {
      const reasons = [];

      // 1. Check for provider unresponsiveness
      const providerHealth = await this.checkProviderHealth(job.provider_id);
      if (!providerHealth.responsive) {
        reasons.push(`Provider unresponsive: ${providerHealth.reason}`);
      }

      // 2. Check for excessive runtime (2x estimated duration)
      if (job.estimated_duration_minutes && runningSeconds > (job.estimated_duration_minutes * 60 * 2)) {
        reasons.push(`Job running 2x longer than estimated (${Math.round(runningSeconds/60)} min vs ${job.estimated_duration_minutes} min estimated)`);
      }

      // 3. Check for resource constraints
      const capacity = await this.providerManager.getProviderCapacity(job.provider_id);
      if (capacity && capacity.utilization_percent > 95) {
        reasons.push(`Provider at critical utilization: ${capacity.utilization_percent}%`);
      }

      // 4. Check provider reputation
      const provider = await this.providerManager.getProvider(job.provider_id);
      if (provider && provider.reputation_score < 3.0) {
        reasons.push(`Provider reputation below threshold: ${provider.reputation_score}/5.0`);
      }

      // 5. Check for recent failures on this provider
      const recentFailures = await this.getRecentFailures(job.provider_id);
      if (recentFailures.failure_rate > 0.3) { // 30% failure rate
        reasons.push(`High recent failure rate on provider: ${(recentFailures.failure_rate * 100).toFixed(1)}%`);
      }

      return {
        trigger: reasons.length > 0,
        reason: reasons.join('; '),
        severity: this.calculateFailoverSeverity(reasons)
      };
    } catch (error) {
      logger.error('Failed to evaluate failover conditions:', error);
      return { trigger: false, reason: 'Evaluation error' };
    }
  }

  calculateFailoverSeverity(reasons) {
    // Simple severity calculation based on reason types
    let severity = 'low';
    
    for (const reason of reasons) {
      if (reason.includes('unresponsive') || reason.includes('critical')) {
        severity = 'high';
        break;
      } else if (reason.includes('2x longer') || reason.includes('failure rate')) {
        severity = 'medium';
      }
    }
    
    return severity;
  }

  async checkProviderHealth(providerId) {
    try {
      const testResult = await this.providerManager.testProviderConnection(providerId);
      
      if (!testResult.success) {
        return {
          responsive: false,
          reason: testResult.error || 'Connection test failed'
        };
      }

      // Check recent heartbeat
      const provider = await this.providerManager.getProvider(providerId);
      if (provider.last_heartbeat) {
        const lastHeartbeat = new Date(provider.last_heartbeat);
        const now = new Date();
        const minutesSinceHeartbeat = (now - lastHeartbeat) / (1000 * 60);
        
        if (minutesSinceHeartbeat > 10) { // No heartbeat for 10 minutes
          return {
            responsive: false,
            reason: `No heartbeat for ${Math.round(minutesSinceHeartbeat)} minutes`
          };
        }
      }

      return { responsive: true };
    } catch (error) {
      return {
        responsive: false,
        reason: `Health check error: ${error.message}`
      };
    }
  }

  async getRecentFailures(providerId) {
    const db = getDb();
    
    try {
      const stats = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(*) as total_jobs,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs
          FROM jobs 
          WHERE provider_id = ?
            AND started_at > datetime('now', '-2 hours')
        `, [providerId], (err, row) => {
          if (err) reject(err);
          else resolve(row || { total_jobs: 0, failed_jobs: 0 });
        });
      });

      return {
        total_jobs: stats.total_jobs,
        failed_jobs: stats.failed_jobs,
        failure_rate: stats.total_jobs > 0 ? stats.failed_jobs / stats.total_jobs : 0
      };
    } catch (error) {
      logger.error('Failed to get recent failures:', error);
      return { total_jobs: 0, failed_jobs: 0, failure_rate: 0 };
    } finally {
      db.close();
    }
  }

  async initiateFailover(jobId, reason) {
    const db = getDb();
    
    try {
      // Get job and check failover attempts
      const job = await new Promise((resolve, reject) => {
        db.get(`
          SELECT j.*, 
            COUNT(fe.id) as failover_attempts
          FROM jobs j
          LEFT JOIN failover_events fe ON j.id = fe.job_id
          WHERE j.id = ?
          GROUP BY j.id
        `, [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!job) {
        throw new Error(`Job ${jobId} not found`);
      }

      if (job.failover_attempts >= this.maxFailoverAttempts) {
        logger.warn(`Job ${jobId} has exceeded maximum failover attempts (${this.maxFailoverAttempts})`);
        await this.failJob(jobId, `Maximum failover attempts exceeded: ${reason}`);
        return { success: false, reason: 'Max failover attempts exceeded' };
      }

      // Check cooldown
      if (this.isInCooldown(job.provider_id)) {
        logger.debug(`Provider ${job.provider_id} is in failover cooldown`);
        return { success: false, reason: 'Provider in cooldown' };
      }

      // Find alternative provider
      const alternativeProvider = await this.findAlternativeProvider(job);
      
      if (!alternativeProvider) {
        logger.warn(`No alternative provider found for job ${jobId}`);
        return { success: false, reason: 'No alternative provider available' };
      }

      // Execute failover
      const failoverResult = await this.executeFailover(job, alternativeProvider, reason);
      
      if (failoverResult.success) {
        // Set cooldown for original provider
        this.setCooldown(job.provider_id);
        
        logger.info(`Successfully failed over job ${jobId} from provider ${job.provider_id} to ${alternativeProvider.id}: ${reason}`);
      }

      return failoverResult;
    } catch (error) {
      logger.error(`Failover initiation failed for job ${jobId}:`, error);
      return { success: false, reason: error.message };
    } finally {
      db.close();
    }
  }

  async findAlternativeProvider(originalJob) {
    try {
      // Get all active providers except the current one
      const providers = await this.providerManager.getActiveProviders();
      const alternativeProviders = providers.filter(p => p.id !== originalJob.provider_id);

      if (alternativeProviders.length === 0) {
        return null;
      }

      // Filter providers by capacity requirements
      const suitableProviders = alternativeProviders.filter(provider => 
        provider.available_cpu_cores >= originalJob.cpu_cores &&
        provider.available_memory_gb >= originalJob.memory_gb &&
        provider.available_storage_gb >= (originalJob.storage_gb || 0)
      );

      if (suitableProviders.length === 0) {
        return null;
      }

      // Score providers based on multiple factors
      const scoredProviders = await Promise.all(
        suitableProviders.map(async (provider) => {
          const score = await this.calculateProviderScore(provider, originalJob);
          return { provider, score };
        })
      );

      // Sort by score (highest first) and return the best provider
      scoredProviders.sort((a, b) => b.score - a.score);
      
      return scoredProviders[0]?.provider || null;
    } catch (error) {
      logger.error('Failed to find alternative provider:', error);
      return null;
    }
  }

  async calculateProviderScore(provider, job) {
    try {
      let score = 0;

      // Base score from reputation (0-50 points)
      score += (provider.reputation_score || 0) * 10;

      // Capacity score (0-25 points)
      const cpuCapacityRatio = provider.available_cpu_cores / Math.max(provider.total_cpu_cores, 1);
      const memCapacityRatio = provider.available_memory_gb / Math.max(provider.total_memory_gb, 1);
      score += Math.min(cpuCapacityRatio, memCapacityRatio) * 25;

      // Uptime score (0-15 points)
      score += (provider.uptime_percent || 95) * 0.15;

      // Pricing score (0-10 points) - lower cost = higher score
      try {
        const pricing = await this.pricingEngine.calculateJobPrice({
          job_type: job.job_type,
          quality_tier: job.quality_tier,
          cpu_cores: job.cpu_cores,
          memory_gb: job.memory_gb,
          storage_gb: job.storage_gb || 0,
          gpu_count: job.gpu_count || 0,
          estimated_duration_minutes: job.estimated_duration_minutes || 60,
          user_id: job.user_id
        }, provider.id);
        
        // Inverse pricing score (lower cost = higher score)
        const baseCost = parseFloat(pricing.estimated_cost) || 10;
        score += Math.max(0, 10 - (baseCost / 10));
      } catch (error) {
        logger.debug(`Failed to get pricing for provider ${provider.id}:`, error.message);
      }

      return Math.round(score);
    } catch (error) {
      logger.error('Failed to calculate provider score:', error);
      return 0;
    }
  }

  async executeFailover(originalJob, newProvider, reason) {
    const db = getDb();
    const startTime = new Date();
    
    try {
      // Record failover event
      const failoverEventId = await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO failover_events (
            job_id, original_provider_id, failover_provider_id, 
            trigger_reason, success
          ) VALUES (?, ?, ?, ?, 0)
        `, [originalJob.id, originalJob.provider_id, newProvider.id, reason], function(err) {
          if (err) reject(err);
          else resolve(this.lastID);
        });
      });

      // Stop job on original provider (simplified - in practice would need provider-specific stop logic)
      await this.stopJobOnProvider(originalJob.id, originalJob.provider_id);

      // Update job to use new provider
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE jobs SET 
            provider_id = ?, 
            started_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
          WHERE id = ?
        `, [newProvider.id, originalJob.id], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Start job on new provider (simplified - in practice would need provider-specific start logic)
      const startResult = await this.startJobOnProvider(originalJob, newProvider);
      
      if (!startResult.success) {
        throw new Error(`Failed to start job on new provider: ${startResult.error}`);
      }

      // Update failover event as successful
      const endTime = new Date();
      const responseTimeMs = endTime - startTime;
      
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE failover_events SET 
            success = 1, 
            response_time_ms = ?
          WHERE id = ?
        `, [responseTimeMs, failoverEventId], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Update provider capacities
      await this.updateProviderCapacityAfterFailover(originalJob, newProvider.id);

      return {
        success: true,
        new_provider_id: newProvider.id,
        response_time_ms: responseTimeMs,
        failover_event_id: failoverEventId
      };
    } catch (error) {
      // Mark failover as failed
      try {
        await new Promise((resolve, reject) => {
          db.run(`
            UPDATE failover_events SET 
              success = 0, 
              error_message = ?
            WHERE job_id = ? AND original_provider_id = ? AND failover_provider_id = ?
            ORDER BY id DESC LIMIT 1
          `, [error.message, originalJob.id, originalJob.provider_id, newProvider.id], (err) => {
            if (err) logger.error('Failed to update failover event:', err);
            resolve();
          });
        });
      } catch (updateError) {
        logger.error('Failed to update failover event after failure:', updateError);
      }

      return {
        success: false,
        error: error.message,
        new_provider_id: newProvider.id
      };
    } finally {
      db.close();
    }
  }

  async stopJobOnProvider(jobId, providerId) {
    // This would contain provider-specific logic to stop the job
    // For now, just log the action
    logger.info(`Stopping job ${jobId} on provider ${providerId}`);
    
    // In a real implementation, this would:
    // 1. Connect to the provider
    // 2. Send cancellation/stop command
    // 3. Wait for confirmation
    // 4. Clean up resources
    
    return { success: true };
  }

  async startJobOnProvider(job, provider) {
    // This would contain provider-specific logic to start the job
    // For now, just log the action and simulate success
    logger.info(`Starting job ${job.id} on provider ${provider.id}`);
    
    // In a real implementation, this would:
    // 1. Connect to the provider
    // 2. Submit job with requirements
    // 3. Wait for job to start
    // 4. Return job status
    
    return { 
      success: true, 
      external_job_id: `failover_${job.id}_${Date.now()}` 
    };
  }

  async updateProviderCapacityAfterFailover(job, newProviderId) {
    try {
      // Free up resources on original provider
      await this.providerManager.updateProviderCapacity(job.provider_id, {
        available_cpu_cores: job.cpu_cores, // Add back the resources
        available_memory_gb: job.memory_gb,
        available_storage_gb: job.storage_gb || 0,
        utilization_percent: 0 // This would be calculated properly
      });

      // Allocate resources on new provider
      const newProvider = await this.providerManager.getProvider(newProviderId);
      if (newProvider) {
        await this.providerManager.updateProviderCapacity(newProviderId, {
          available_cpu_cores: Math.max(0, newProvider.available_cpu_cores - job.cpu_cores),
          available_memory_gb: Math.max(0, newProvider.available_memory_gb - job.memory_gb),
          available_storage_gb: Math.max(0, newProvider.available_storage_gb - (job.storage_gb || 0)),
          utilization_percent: 0 // This would be calculated properly
        });
      }
    } catch (error) {
      logger.error('Failed to update provider capacities after failover:', error);
    }
  }

  async failJob(jobId, reason) {
    const db = getDb();
    
    try {
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE jobs SET 
            status = 'failed', 
            completed_at = CURRENT_TIMESTAMP,
            error_message = ?,
            updated_at = CURRENT_TIMESTAMP
          WHERE id = ?
        `, [reason, jobId], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      logger.info(`Job ${jobId} marked as failed: ${reason}`);
    } catch (error) {
      logger.error(`Failed to mark job ${jobId} as failed:`, error);
    } finally {
      db.close();
    }
  }

  isInCooldown(providerId) {
    const cooldownTime = this.failoverCooldowns.get(providerId);
    if (!cooldownTime) return false;
    
    const now = new Date();
    return now < cooldownTime;
  }

  setCooldown(providerId) {
    const cooldownEnd = new Date();
    cooldownEnd.setMinutes(cooldownEnd.getMinutes() + this.failoverCooldownMinutes);
    this.failoverCooldowns.set(providerId, cooldownEnd);
    
    logger.info(`Set failover cooldown for provider ${providerId} until ${cooldownEnd.toISOString()}`);
  }

  async getFailoverStatistics() {
    const db = getDb();
    
    try {
      const stats = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(*) as total_failovers,
            COUNT(CASE WHEN success = 1 THEN 1 END) as successful_failovers,
            AVG(response_time_ms) as avg_response_time,
            COUNT(DISTINCT job_id) as jobs_affected,
            COUNT(DISTINCT original_provider_id) as providers_failed_from,
            MIN(created_at) as first_failover,
            MAX(created_at) as last_failover
          FROM failover_events
          WHERE created_at > datetime('now', '-30 days')
        `, (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      const successRate = stats.total_failovers > 0 
        ? (stats.successful_failovers / stats.total_failovers * 100).toFixed(2)
        : '0.00';

      return {
        ...stats,
        success_rate_percent: parseFloat(successRate),
        avg_response_time_ms: Math.round(stats.avg_response_time || 0)
      };
    } catch (error) {
      logger.error('Failed to get failover statistics:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async startFailoverMonitoring() {
    if (!this.failoverEnabled) return;

    const interval = 30000; // Check every 30 seconds
    
    this.monitoringInterval = setInterval(async () => {
      try {
        await this.monitorRunningJobs();
      } catch (error) {
        logger.error('Failover monitoring error:', error);
      }
    }, interval);
    
    logger.info('Failover monitoring started');
  }

  async monitorRunningJobs() {
    const db = getDb();
    
    try {
      const runningJobs = await new Promise((resolve, reject) => {
        db.all(`
          SELECT id
          FROM jobs 
          WHERE status = 'running'
            AND started_at < datetime('now', '-${this.failoverThresholdSeconds} seconds')
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      for (const job of runningJobs) {
        try {
          await this.checkJobForFailover(job.id);
        } catch (error) {
          logger.error(`Failed to check job ${job.id} for failover:`, error);
        }
      }
    } catch (error) {
      logger.error('Failed to monitor running jobs:', error);
    } finally {
      db.close();
    }
  }

  stop() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    logger.info('Failover manager stopped');
  }
}