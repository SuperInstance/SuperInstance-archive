import { getDb } from '../database/init.js';
import { getRedisClient } from '../utils/redis.js';
import { logger } from '../utils/logger.js';
import { PricingEngine } from './pricingEngine.js';

export class JobQueue {
  constructor() {
    this.pricingEngine = new PricingEngine();
    this.processingInterval = null;
  }

  async initialize() {
    try {
      await this.pricingEngine.initializePricing();
      await this.processQueuedJobs();
      this.startQueueProcessor();
      logger.info('Job queue initialized');
    } catch (error) {
      logger.error('Failed to initialize job queue:', error);
      throw error;
    }
  }

  async submitJob(jobData, userId) {
    const db = getDb();
    
    try {
      // Validate job requirements
      await this.validateJobRequirements(jobData);
      
      // Calculate priority score
      const priorityScore = await this.calculatePriorityScore(jobData, userId);
      
      // Create job record
      const jobId = await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO jobs (
            user_id, job_name, job_type, priority, cpu_cores, memory_gb,
            storage_gb, gpu_count, estimated_duration_minutes, max_cost,
            quality_tier, command, environment_vars, docker_image,
            scheduled_start, status
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        `, [
          userId, jobData.job_name, jobData.job_type, jobData.priority,
          jobData.cpu_cores, jobData.memory_gb, jobData.storage_gb,
          jobData.gpu_count, jobData.estimated_duration_minutes,
          jobData.max_cost, jobData.quality_tier, jobData.command,
          JSON.stringify(jobData.environment_vars || {}),
          jobData.docker_image, jobData.scheduled_start
        ], function(err) {
          if (err) reject(err);
          else resolve(this.lastID);
        });
      });

      // Add to queue
      await this.addToQueue(jobId, priorityScore);
      
      logger.info(`Job ${jobId} submitted by user ${userId} with priority score ${priorityScore}`);
      
      return {
        job_id: jobId,
        priority_score: priorityScore,
        status: 'pending'
      };
    } catch (error) {
      logger.error('Job submission failed:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async addToQueue(jobId, priorityScore) {
    const db = getDb();
    const redis = getRedisClient();
    
    try {
      // Get current queue position
      const queuePosition = await new Promise((resolve, reject) => {
        db.get(
          'SELECT COUNT(*) + 1 as position FROM job_queue WHERE priority_score >= ?',
          [priorityScore],
          (err, row) => {
            if (err) reject(err);
            else resolve(row.position);
          }
        );
      });

      // Estimate wait time
      const estimatedWaitMinutes = await this.estimateWaitTime(queuePosition, priorityScore);

      // Add to database queue
      await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO job_queue (job_id, queue_position, priority_score, estimated_wait_minutes)
          VALUES (?, ?, ?, ?)
        `, [jobId, queuePosition, priorityScore, estimatedWaitMinutes], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Add to Redis for fast processing
      await redis.zadd('job_queue', priorityScore, jobId.toString());
      
      // Update job status
      await new Promise((resolve, reject) => {
        db.run(
          'UPDATE jobs SET status = "queued" WHERE id = ?',
          [jobId],
          (err) => {
            if (err) reject(err);
            else resolve();
          }
        );
      });

      logger.info(`Job ${jobId} added to queue at position ${queuePosition}`);
    } catch (error) {
      logger.error('Failed to add job to queue:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async calculatePriorityScore(jobData, userId) {
    const db = getDb();
    
    try {
      // Get user preferences and history
      const userInfo = await new Promise((resolve, reject) => {
        db.get(`
          SELECT u.*, up.preferred_quality_tier, up.max_cost_per_hour
          FROM users u
          LEFT JOIN user_preferences up ON u.id = up.user_id
          WHERE u.id = ?
        `, [userId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      let score = 0;

      // Base priority from job request (1-10)
      score += (jobData.priority || 5) * 10;

      // Quality tier bonus
      const qualityMultipliers = {
        'enterprise': 40,
        'premium': 30,
        'standard': 20,
        'basic': 10
      };
      score += qualityMultipliers[jobData.quality_tier] || 20;

      // User role bonus
      const roleMultipliers = {
        'admin': 50,
        'university_admin': 40,
        'user': 0
      };
      score += roleMultipliers[userInfo?.role] || 0;

      // Time sensitivity bonus (scheduled jobs get lower priority)
      if (!jobData.scheduled_start) {
        score += 25; // Immediate execution bonus
      } else {
        const scheduledTime = new Date(jobData.scheduled_start);
        const now = new Date();
        const hoursUntilExecution = (scheduledTime - now) / (1000 * 60 * 60);
        
        if (hoursUntilExecution < 1) {
          score += 20; // Very soon
        } else if (hoursUntilExecution < 24) {
          score += 10; // Within 24 hours
        }
      }

      // Resource efficiency bonus (smaller jobs get slight priority)
      const resourceUnits = this.calculateResourceUnits(jobData);
      if (resourceUnits <= 4) {
        score += 15; // Small job bonus
      } else if (resourceUnits <= 8) {
        score += 10; // Medium job bonus
      }

      // User history bonus (reliable users get priority)
      const userHistory = await this.getUserHistory(userId);
      score += Math.min(userHistory.successRate * 20, 20);
      score += Math.min(userHistory.avgRating * 5, 25);

      // Time-of-day modifier
      const hour = new Date().getHours();
      if (hour >= 22 || hour <= 6) {
        score += 15; // Off-hours bonus
      }

      return Math.round(score);
    } catch (error) {
      logger.error('Failed to calculate priority score:', error);
      return 50; // Default priority
    } finally {
      db.close();
    }
  }

  calculateResourceUnits(jobData) {
    const cpuUnits = jobData.cpu_cores || 1;
    const memoryUnits = (jobData.memory_gb || 1) / 4;
    const storageUnits = (jobData.storage_gb || 0) / 100;
    const gpuUnits = (jobData.gpu_count || 0) * 8;
    
    return cpuUnits + memoryUnits + storageUnits + gpuUnits;
  }

  async getUserHistory(userId) {
    const db = getDb();
    
    try {
      const history = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(*) as total_jobs,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_jobs,
            AVG(CASE WHEN status = 'completed' THEN 5.0 ELSE 3.0 END) as avg_rating
          FROM jobs 
          WHERE user_id = ? AND created_at > datetime('now', '-30 days')
        `, [userId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      const successRate = history.total_jobs > 0 
        ? history.completed_jobs / history.total_jobs 
        : 0.8; // Default for new users

      return {
        successRate,
        avgRating: history.avg_rating || 4.0,
        totalJobs: history.total_jobs
      };
    } catch (error) {
      logger.error('Failed to get user history:', error);
      return { successRate: 0.8, avgRating: 4.0, totalJobs: 0 };
    } finally {
      db.close();
    }
  }

  async estimateWaitTime(queuePosition, priorityScore) {
    const db = getDb();
    
    try {
      // Get average job duration for similar priority jobs
      const avgDuration = await new Promise((resolve, reject) => {
        db.get(`
          SELECT AVG(actual_duration_minutes) as avg_duration
          FROM jobs j
          JOIN job_queue jq ON j.id = jq.job_id
          WHERE jq.priority_score BETWEEN ? AND ?
            AND j.status = 'completed'
            AND j.completed_at > datetime('now', '-7 days')
        `, [priorityScore - 10, priorityScore + 10], (err, row) => {
          if (err) reject(err);
          else resolve(row?.avg_duration || 60);
        });
      });

      // Estimate based on queue position and average duration
      const estimatedMinutes = Math.max((queuePosition - 1) * (avgDuration * 0.8), 0);
      
      return Math.round(estimatedMinutes);
    } catch (error) {
      logger.error('Failed to estimate wait time:', error);
      return queuePosition * 30; // Fallback: 30 minutes per position
    } finally {
      db.close();
    }
  }

  async validateJobRequirements(jobData) {
    // Validate resource requirements against system limits
    const maxCpuCores = parseInt(process.env.MAX_CPU_CORES_PER_JOB) || 128;
    const maxMemoryGb = parseInt(process.env.MAX_MEMORY_GB_PER_JOB) || 512;
    const maxStorageGb = parseInt(process.env.MAX_STORAGE_GB_PER_JOB) || 10000;
    const maxGpuCount = parseInt(process.env.MAX_GPU_COUNT_PER_JOB) || 8;

    if (jobData.cpu_cores > maxCpuCores) {
      throw new Error(`CPU cores exceeds maximum limit: ${maxCpuCores}`);
    }
    if (jobData.memory_gb > maxMemoryGb) {
      throw new Error(`Memory exceeds maximum limit: ${maxMemoryGb} GB`);
    }
    if (jobData.storage_gb > maxStorageGb) {
      throw new Error(`Storage exceeds maximum limit: ${maxStorageGb} GB`);
    }
    if (jobData.gpu_count > maxGpuCount) {
      throw new Error(`GPU count exceeds maximum limit: ${maxGpuCount}`);
    }

    // Validate quality tier matches resource requirements
    const tierRequirements = {
      'basic': { maxCpu: 8, maxMemory: 32, maxGpu: 0 },
      'standard': { maxCpu: 32, maxMemory: 128, maxGpu: 2 },
      'premium': { maxCpu: 64, maxMemory: 256, maxGpu: 4 },
      'enterprise': { maxCpu: 128, maxMemory: 512, maxGpu: 8 }
    };

    const tier = tierRequirements[jobData.quality_tier];
    if (tier) {
      if (jobData.cpu_cores > tier.maxCpu ||
          jobData.memory_gb > tier.maxMemory ||
          jobData.gpu_count > tier.maxGpu) {
        throw new Error(`Resource requirements exceed ${jobData.quality_tier} tier limits`);
      }
    }
  }

  async getQueueStatus(userId = null) {
    const db = getDb();
    const redis = getRedisClient();
    
    try {
      // Get queue statistics
      const queueStats = await new Promise((resolve, reject) => {
        const query = userId 
          ? `SELECT 
               COUNT(*) as total_queued,
               AVG(priority_score) as avg_priority,
               AVG(estimated_wait_minutes) as avg_wait
             FROM job_queue jq
             JOIN jobs j ON jq.job_id = j.id
             WHERE j.user_id = ?`
          : `SELECT 
               COUNT(*) as total_queued,
               AVG(priority_score) as avg_priority,
               AVG(estimated_wait_minutes) as avg_wait
             FROM job_queue`;
        
        const params = userId ? [userId] : [];
        
        db.get(query, params, (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      // Get active jobs count
      const activeJobs = await redis.zcard('job_queue');

      return {
        total_queued: queueStats.total_queued,
        active_queue_size: activeJobs,
        average_priority: Math.round(queueStats.avg_priority || 0),
        average_wait_minutes: Math.round(queueStats.avg_wait || 0),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      logger.error('Failed to get queue status:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async processQueuedJobs() {
    const redis = getRedisClient();
    
    try {
      // Get highest priority jobs from Redis
      const jobs = await redis.zrevrange('job_queue', 0, 9); // Top 10 jobs
      
      for (const jobId of jobs) {
        try {
          await this.matchJobToProvider(parseInt(jobId));
        } catch (error) {
          logger.error(`Failed to process job ${jobId}:`, error);
        }
      }
    } catch (error) {
      logger.error('Queue processing failed:', error);
    }
  }

  async matchJobToProvider(jobId) {
    const db = getDb();
    
    try {
      // Get job details
      const job = await new Promise((resolve, reject) => {
        db.get('SELECT * FROM jobs WHERE id = ?', [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!job || job.status !== 'queued') {
        return;
      }

      // Find suitable providers
      const providers = await this.findSuitableProviders(job);
      
      if (providers.length === 0) {
        logger.warn(`No suitable providers found for job ${jobId}`);
        return;
      }

      // Select best provider (lowest cost or highest priority based on user preference)
      const selectedProvider = await this.selectBestProvider(providers, job);
      
      // Assign job to provider
      await this.assignJobToProvider(jobId, selectedProvider.id);
      
      logger.info(`Job ${jobId} assigned to provider ${selectedProvider.id}`);
    } catch (error) {
      logger.error(`Job matching failed for job ${jobId}:`, error);
    } finally {
      db.close();
    }
  }

  async findSuitableProviders(job) {
    const db = getDb();
    
    try {
      const providers = await new Promise((resolve, reject) => {
        db.all(`
          SELECT * FROM providers 
          WHERE status = 'active'
            AND available_cpu_cores >= ?
            AND available_memory_gb >= ?
            AND available_storage_gb >= ?
          ORDER BY reputation_score DESC
        `, [job.cpu_cores, job.memory_gb, job.storage_gb], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      return providers;
    } catch (error) {
      logger.error('Failed to find suitable providers:', error);
      return [];
    } finally {
      db.close();
    }
  }

  async selectBestProvider(providers, job) {
    // Get price estimates for each provider
    const estimates = await Promise.all(providers.map(async (provider) => {
      try {
        const estimate = await this.pricingEngine.calculateJobPrice(job, provider.id);
        return { provider, estimate };
      } catch (error) {
        logger.warn(`Failed to get estimate for provider ${provider.id}:`, error);
        return null;
      }
    }));

    const validEstimates = estimates.filter(e => e !== null);
    
    if (validEstimates.length === 0) {
      throw new Error('No valid price estimates available');
    }

    // Sort by cost (ascending) and reputation (descending)
    validEstimates.sort((a, b) => {
      const costDiff = parseFloat(a.estimate.estimated_cost) - parseFloat(b.estimate.estimated_cost);
      if (Math.abs(costDiff) < 0.01) { // If costs are very similar, prefer higher reputation
        return b.provider.reputation_score - a.provider.reputation_score;
      }
      return costDiff;
    });

    return validEstimates[0].provider;
  }

  async assignJobToProvider(jobId, providerId) {
    const db = getDb();
    const redis = getRedisClient();
    
    try {
      // Update job with provider
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE jobs 
          SET provider_id = ?, status = 'running', started_at = CURRENT_TIMESTAMP
          WHERE id = ?
        `, [providerId, jobId], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Remove from queue
      await new Promise((resolve, reject) => {
        db.run('DELETE FROM job_queue WHERE job_id = ?', [jobId], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      await redis.zrem('job_queue', jobId.toString());
      
      // Update provider capacity (simplified - should be more sophisticated)
      const job = await new Promise((resolve, reject) => {
        db.get('SELECT * FROM jobs WHERE id = ?', [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE providers 
          SET available_cpu_cores = available_cpu_cores - ?,
              available_memory_gb = available_memory_gb - ?
          WHERE id = ?
        `, [job.cpu_cores, job.memory_gb, providerId], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

    } catch (error) {
      logger.error('Failed to assign job to provider:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  startQueueProcessor() {
    const interval = 30000; // Process every 30 seconds
    
    this.processingInterval = setInterval(async () => {
      try {
        await this.processQueuedJobs();
      } catch (error) {
        logger.error('Queue processing error:', error);
      }
    }, interval);
    
    logger.info('Queue processor started');
  }

  stopQueueProcessor() {
    if (this.processingInterval) {
      clearInterval(this.processingInterval);
      this.processingInterval = null;
      logger.info('Queue processor stopped');
    }
  }
}