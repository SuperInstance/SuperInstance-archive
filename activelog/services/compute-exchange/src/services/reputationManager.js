import { getDb } from '../database/init.js';
import { logger } from '../utils/logger.js';
import cron from 'node-cron';

export class ReputationManager {
  constructor() {
    this.reputationWeights = {
      uptime: 0.35,
      performance: 0.25,
      reliability: 0.20,
      support: 0.10,
      pricing: 0.05,
      sla_compliance: 0.05
    };
    this.updateInterval = null;
  }

  async initialize() {
    try {
      await this.loadReputationWeights();
      await this.initializeProviderReputations();
      this.startReputationUpdater();
      logger.info('Reputation manager initialized');
    } catch (error) {
      logger.error('Failed to initialize reputation manager:', error);
      throw error;
    }
  }

  async loadReputationWeights() {
    // Load from environment or database configuration
    this.reputationWeights = {
      uptime: parseFloat(process.env.REPUTATION_UPTIME_WEIGHT) || 0.35,
      performance: parseFloat(process.env.REPUTATION_PERFORMANCE_WEIGHT) || 0.25,
      reliability: parseFloat(process.env.REPUTATION_RELIABILITY_WEIGHT) || 0.20,
      support: parseFloat(process.env.REPUTATION_SUPPORT_WEIGHT) || 0.10,
      pricing: parseFloat(process.env.REPUTATION_PRICING_WEIGHT) || 0.05,
      sla_compliance: parseFloat(process.env.REPUTATION_SLA_WEIGHT) || 0.05
    };
    
    logger.info('Reputation weights loaded:', this.reputationWeights);
  }

  async initializeProviderReputations() {
    const db = getDb();
    
    try {
      // Get all providers without reputation scores
      const providers = await new Promise((resolve, reject) => {
        db.all(`
          SELECT id, name FROM providers 
          WHERE reputation_score IS NULL OR reputation_score = 0
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      for (const provider of providers) {
        await this.calculateInitialReputation(provider.id);
      }

      if (providers.length > 0) {
        logger.info(`Initialized reputation for ${providers.length} providers`);
      }
    } catch (error) {
      logger.error('Failed to initialize provider reputations:', error);
    } finally {
      db.close();
    }
  }

  async calculateInitialReputation(providerId) {
    // Set initial reputation to neutral (5.0) for new providers
    await this.updateProviderReputation(providerId, 5.0);
    logger.info(`Set initial reputation for provider ${providerId}: 5.0`);
  }

  async recordReputationEvent(providerId, jobId, eventType, rating, notes = '') {
    const db = getDb();
    
    try {
      if (rating < 1.0 || rating > 5.0) {
        throw new Error('Rating must be between 1.0 and 5.0');
      }

      const validEventTypes = ['uptime', 'performance', 'reliability', 'support', 'pricing', 'sla_compliance'];
      if (!validEventTypes.includes(eventType)) {
        throw new Error(`Invalid event type: ${eventType}`);
      }

      const impactWeight = this.reputationWeights[eventType] || 1.0;

      const eventId = await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO provider_reputation (
            provider_id, job_id, rating, factor_type, impact_weight, notes
          ) VALUES (?, ?, ?, ?, ?, ?)
        `, [providerId, jobId, rating, eventType, impactWeight, notes], function(err) {
          if (err) reject(err);
          else resolve(this.lastID);
        });
      });

      // Trigger reputation recalculation
      await this.updateProviderReputationScore(providerId);

      logger.info(`Recorded reputation event ${eventType} for provider ${providerId}: ${rating}/5.0`);
      
      return eventId;
    } catch (error) {
      logger.error(`Failed to record reputation event for provider ${providerId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async updateProviderReputationScore(providerId) {
    const db = getDb();
    
    try {
      // Get all reputation events for the provider in the last 90 days
      const events = await new Promise((resolve, reject) => {
        db.all(`
          SELECT factor_type, rating, impact_weight, recorded_at
          FROM provider_reputation 
          WHERE provider_id = ?
            AND recorded_at > datetime('now', '-90 days')
          ORDER BY recorded_at DESC
        `, [providerId], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      if (events.length === 0) {
        // No recent events, maintain current score or set to neutral
        const currentProvider = await new Promise((resolve, reject) => {
          db.get('SELECT reputation_score FROM providers WHERE id = ?', [providerId], (err, row) => {
            if (err) reject(err);
            else resolve(row);
          });
        });

        if (!currentProvider?.reputation_score) {
          await this.updateProviderReputation(providerId, 5.0);
        }
        return;
      }

      // Calculate weighted scores by factor type
      const factorScores = {};
      const factorCounts = {};

      for (const event of events) {
        if (!factorScores[event.factor_type]) {
          factorScores[event.factor_type] = 0;
          factorCounts[event.factor_type] = 0;
        }
        
        // Apply time decay (more recent events have more weight)
        const daysOld = (new Date() - new Date(event.recorded_at)) / (1000 * 60 * 60 * 24);
        const timeWeight = Math.exp(-daysOld / 30); // 30-day half-life
        
        factorScores[event.factor_type] += event.rating * event.impact_weight * timeWeight;
        factorCounts[event.factor_type] += event.impact_weight * timeWeight;
      }

      // Calculate average scores for each factor
      const averageScores = {};
      for (const factor in factorScores) {
        averageScores[factor] = factorCounts[factor] > 0 
          ? factorScores[factor] / factorCounts[factor]
          : 5.0; // Default to neutral if no data
      }

      // Calculate overall reputation score
      let overallScore = 0;
      let totalWeight = 0;

      for (const [factor, weight] of Object.entries(this.reputationWeights)) {
        const score = averageScores[factor] || 5.0; // Default to neutral
        overallScore += score * weight;
        totalWeight += weight;
      }

      const finalScore = totalWeight > 0 ? overallScore / totalWeight : 5.0;
      const roundedScore = Math.round(finalScore * 100) / 100; // Round to 2 decimal places
      const clampedScore = Math.max(1.0, Math.min(5.0, roundedScore)); // Clamp between 1.0 and 5.0

      await this.updateProviderReputation(providerId, clampedScore);
      
      logger.info(`Updated reputation for provider ${providerId}: ${clampedScore}/5.0`);
      
      return clampedScore;
    } catch (error) {
      logger.error(`Failed to update reputation score for provider ${providerId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async updateProviderReputation(providerId, reputationScore) {
    const db = getDb();
    
    try {
      await new Promise((resolve, reject) => {
        db.run(
          'UPDATE providers SET reputation_score = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
          [reputationScore, providerId],
          (err) => {
            if (err) reject(err);
            else resolve();
          }
        );
      });
    } catch (error) {
      logger.error('Failed to update provider reputation:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async recordJobCompletion(jobId) {
    const db = getDb();
    
    try {
      // Get job details
      const job = await new Promise((resolve, reject) => {
        db.get(`
          SELECT j.*, 
            (julianday(j.completed_at) - julianday(j.started_at)) * 1440 as actual_duration,
            j.estimated_duration_minutes
          FROM jobs j
          WHERE j.id = ? AND j.status IN ('completed', 'failed')
        `, [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!job || !job.provider_id) {
        return;
      }

      // Record performance rating based on execution
      if (job.status === 'completed') {
        // Performance rating based on duration accuracy
        let performanceRating = 5.0;
        if (job.estimated_duration_minutes && job.actual_duration) {
          const durationRatio = job.actual_duration / job.estimated_duration_minutes;
          if (durationRatio <= 1.1) {
            performanceRating = 5.0; // Excellent - finished on time or early
          } else if (durationRatio <= 1.3) {
            performanceRating = 4.0; // Good - slight overrun
          } else if (durationRatio <= 1.5) {
            performanceRating = 3.0; // Average - moderate overrun
          } else if (durationRatio <= 2.0) {
            performanceRating = 2.0; // Poor - significant overrun
          } else {
            performanceRating = 1.0; // Very poor - major overrun
          }
        }

        await this.recordReputationEvent(
          job.provider_id, 
          jobId, 
          'performance', 
          performanceRating,
          `Job completed, duration ratio: ${job.actual_duration ? (job.actual_duration / (job.estimated_duration_minutes || 60)).toFixed(2) : 'N/A'}`
        );

        // Record reliability rating (successful completion)
        await this.recordReputationEvent(
          job.provider_id, 
          jobId, 
          'reliability', 
          5.0,
          'Job completed successfully'
        );
      } else if (job.status === 'failed') {
        // Record poor reliability rating for failed jobs
        let reliabilityRating = 2.0;
        
        // Check if failure was due to provider issues vs user issues
        if (job.error_message && 
            (job.error_message.includes('timeout') || 
             job.error_message.includes('connection') ||
             job.error_message.includes('resource'))) {
          reliabilityRating = 1.0; // Provider-related failure
        }

        await this.recordReputationEvent(
          job.provider_id, 
          jobId, 
          'reliability', 
          reliabilityRating,
          `Job failed: ${job.error_message || 'Unknown error'}`
        );
      }

      logger.debug(`Recorded reputation events for job ${jobId} completion`);
    } catch (error) {
      logger.error(`Failed to record job completion reputation for job ${jobId}:`, error);
    } finally {
      db.close();
    }
  }

  async recordUptimeEvent(providerId, isUp, responseTimeMs = null) {
    try {
      const uptimeRating = isUp ? 5.0 : 1.0;
      const notes = isUp 
        ? `Provider responding${responseTimeMs ? `, response time: ${responseTimeMs}ms` : ''}` 
        : 'Provider not responding';

      await this.recordReputationEvent(
        providerId, 
        null, 
        'uptime', 
        uptimeRating, 
        notes
      );

      // Also record performance rating based on response time
      if (isUp && responseTimeMs) {
        let performanceRating = 5.0;
        if (responseTimeMs > 10000) {
          performanceRating = 2.0; // Very slow response
        } else if (responseTimeMs > 5000) {
          performanceRating = 3.0; // Slow response
        } else if (responseTimeMs > 2000) {
          performanceRating = 4.0; // Acceptable response
        }

        if (performanceRating < 5.0) {
          await this.recordReputationEvent(
            providerId, 
            null, 
            'performance', 
            performanceRating,
            `Response time: ${responseTimeMs}ms`
          );
        }
      }
    } catch (error) {
      logger.error(`Failed to record uptime event for provider ${providerId}:`, error);
    }
  }

  async recordSLAViolation(providerId, jobId, violationType, severity) {
    try {
      let slaRating = 3.0; // Default to average
      
      switch (severity) {
        case 'low':
          slaRating = 4.0;
          break;
        case 'medium':
          slaRating = 3.0;
          break;
        case 'high':
          slaRating = 2.0;
          break;
        case 'critical':
          slaRating = 1.0;
          break;
      }

      await this.recordReputationEvent(
        providerId, 
        jobId, 
        'sla_compliance', 
        slaRating,
        `SLA violation: ${violationType} (${severity})`
      );

      logger.info(`Recorded SLA violation for provider ${providerId}: ${violationType} (${severity})`);
    } catch (error) {
      logger.error(`Failed to record SLA violation for provider ${providerId}:`, error);
    }
  }

  async getProviderReputationDetails(providerId) {
    const db = getDb();
    
    try {
      // Get current reputation score
      const provider = await new Promise((resolve, reject) => {
        db.get(
          'SELECT id, name, reputation_score, uptime_percent FROM providers WHERE id = ?',
          [providerId],
          (err, row) => {
            if (err) reject(err);
            else resolve(row);
          }
        );
      });

      if (!provider) {
        throw new Error('Provider not found');
      }

      // Get reputation breakdown by factor
      const factorBreakdown = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            factor_type,
            COUNT(*) as event_count,
            AVG(rating) as avg_rating,
            MIN(rating) as min_rating,
            MAX(rating) as max_rating,
            MAX(recorded_at) as last_event
          FROM provider_reputation 
          WHERE provider_id = ?
            AND recorded_at > datetime('now', '-90 days')
          GROUP BY factor_type
          ORDER BY factor_type
        `, [providerId], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      // Get recent reputation events
      const recentEvents = await new Promise((resolve, reject) => {
        db.all(`
          SELECT pr.*, j.job_name
          FROM provider_reputation pr
          LEFT JOIN jobs j ON pr.job_id = j.id
          WHERE pr.provider_id = ?
          ORDER BY pr.recorded_at DESC
          LIMIT 20
        `, [providerId], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      // Calculate reputation trend (last 30 days vs previous 30 days)
      const trend = await this.calculateReputationTrend(providerId);

      return {
        provider: {
          id: provider.id,
          name: provider.name,
          current_reputation: provider.reputation_score,
          uptime_percent: provider.uptime_percent
        },
        factor_breakdown: factorBreakdown.map(factor => ({
          ...factor,
          avg_rating: parseFloat(factor.avg_rating).toFixed(2),
          weight: this.reputationWeights[factor.factor_type] || 0
        })),
        recent_events: recentEvents,
        reputation_trend: trend,
        reputation_weights: this.reputationWeights
      };
    } catch (error) {
      logger.error(`Failed to get reputation details for provider ${providerId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async calculateReputationTrend(providerId) {
    const db = getDb();
    
    try {
      // Get average reputation for last 30 days
      const recentAvg = await new Promise((resolve, reject) => {
        db.get(`
          SELECT AVG(rating) as avg_rating
          FROM provider_reputation 
          WHERE provider_id = ?
            AND recorded_at > datetime('now', '-30 days')
        `, [providerId], (err, row) => {
          if (err) reject(err);
          else resolve(row?.avg_rating || null);
        });
      });

      // Get average reputation for previous 30 days (31-60 days ago)
      const previousAvg = await new Promise((resolve, reject) => {
        db.get(`
          SELECT AVG(rating) as avg_rating
          FROM provider_reputation 
          WHERE provider_id = ?
            AND recorded_at BETWEEN datetime('now', '-60 days') AND datetime('now', '-30 days')
        `, [providerId], (err, row) => {
          if (err) reject(err);
          else resolve(row?.avg_rating || null);
        });
      });

      if (!recentAvg || !previousAvg) {
        return { trend: 'insufficient_data', change: 0 };
      }

      const change = recentAvg - previousAvg;
      let trend = 'stable';
      
      if (change > 0.2) {
        trend = 'improving';
      } else if (change < -0.2) {
        trend = 'declining';
      }

      return {
        trend: trend,
        change: parseFloat(change.toFixed(2)),
        recent_avg: parseFloat(recentAvg.toFixed(2)),
        previous_avg: parseFloat(previousAvg.toFixed(2))
      };
    } catch (error) {
      logger.error('Failed to calculate reputation trend:', error);
      return { trend: 'error', change: 0 };
    } finally {
      db.close();
    }
  }

  async getTopProviders(limit = 10) {
    const db = getDb();
    
    try {
      const topProviders = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            p.id, p.name, p.type, p.university_id, p.reputation_score,
            p.uptime_percent, p.total_cpu_cores, p.total_memory_gb,
            COUNT(DISTINCT j.id) as total_jobs,
            COUNT(DISTINCT CASE WHEN j.status = 'completed' THEN j.id END) as successful_jobs
          FROM providers p
          LEFT JOIN jobs j ON p.id = j.provider_id AND j.created_at > datetime('now', '-30 days')
          WHERE p.status = 'active' AND p.reputation_score IS NOT NULL
          GROUP BY p.id, p.name, p.type, p.university_id, p.reputation_score, p.uptime_percent
          ORDER BY p.reputation_score DESC, p.uptime_percent DESC
          LIMIT ?
        `, [limit], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      return topProviders.map((provider, index) => ({
        rank: index + 1,
        ...provider,
        success_rate: provider.total_jobs > 0 
          ? ((provider.successful_jobs / provider.total_jobs) * 100).toFixed(1)
          : 'N/A'
      }));
    } catch (error) {
      logger.error('Failed to get top providers:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  startReputationUpdater() {
    const updateInterval = parseInt(process.env.REPUTATION_UPDATE_INTERVAL) || 3600000; // Default 1 hour
    
    this.updateInterval = setInterval(async () => {
      try {
        const providers = await this.getActiveProviders();
        
        for (const provider of providers) {
          try {
            await this.updateProviderReputationScore(provider.id);
          } catch (error) {
            logger.error(`Failed to update reputation for provider ${provider.id}:`, error);
          }
        }
        
        logger.debug(`Updated reputation scores for ${providers.length} providers`);
      } catch (error) {
        logger.error('Reputation update error:', error);
      }
    }, updateInterval);

    // Schedule daily reputation reports
    cron.schedule('0 6 * * *', async () => {
      try {
        const topProviders = await this.getTopProviders(5);
        logger.info(`Daily reputation report - Top providers: ${topProviders.map(p => `${p.name} (${p.reputation_score})`).join(', ')}`);
      } catch (error) {
        logger.error('Daily reputation report error:', error);
      }
    });

    logger.info('Reputation updater started');
  }

  async getActiveProviders() {
    const db = getDb();
    
    try {
      return await new Promise((resolve, reject) => {
        db.all('SELECT id, name FROM providers WHERE status = "active"', (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });
    } catch (error) {
      logger.error('Failed to get active providers:', error);
      return [];
    } finally {
      db.close();
    }
  }

  stop() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
    logger.info('Reputation manager stopped');
  }
}