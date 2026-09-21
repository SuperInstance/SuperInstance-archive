const Bull = require('bull');
const redis = require('../config/redis');
const Order = require('../models/Order');
const Maker = require('../models/Maker');
const logger = require('../config/logger');

class PriorityQueueService {
  constructor() {
    this.queues = {
      // High priority queue for rush orders
      rush: new Bull('rush-orders', {
        redis: { 
          host: process.env.REDIS_HOST || 'localhost',
          port: process.env.REDIS_PORT || 6379
        },
        defaultJobOptions: {
          removeOnComplete: 50,
          removeOnFail: 20,
          attempts: 3,
          backoff: {
            type: 'exponential',
            delay: 5000,
          }
        }
      }),
      
      // Standard priority queue
      standard: new Bull('standard-orders', {
        redis: { 
          host: process.env.REDIS_HOST || 'localhost',
          port: process.env.REDIS_PORT || 6379
        },
        defaultJobOptions: {
          removeOnComplete: 100,
          removeOnFail: 50,
          attempts: 5,
          backoff: {
            type: 'exponential',
            delay: 10000,
          }
        }
      }),
      
      // Low priority queue for non-urgent orders
      low: new Bull('low-priority-orders', {
        redis: { 
          host: process.env.REDIS_HOST || 'localhost',
          port: process.env.REDIS_PORT || 6379
        },
        defaultJobOptions: {
          removeOnComplete: 200,
          removeOnFail: 100,
          attempts: 10,
          backoff: {
            type: 'exponential',
            delay: 30000,
          }
        }
      })
    };

    this.rushPriceMultipliers = {
      immediate: 2.5,  // 150% surcharge for immediate processing
      express: 2.0,    // 100% surcharge for express processing
      expedited: 1.5   // 50% surcharge for expedited processing
    };

    this.setupQueueProcessors();
    this.setupQueueEvents();
  }

  /**
   * Add order to appropriate priority queue
   */
  async addOrderToQueue(orderId, priority = 'standard', rushLevel = null) {
    try {
      const order = await Order.findOne({ orderId });
      if (!order) {
        throw new Error(`Order ${orderId} not found`);
      }

      // Determine queue based on priority
      let queueName = 'standard';
      let jobPriority = 0;
      let delay = 0;

      if (priority === 'rush' || order.isUrgent) {
        queueName = 'rush';
        jobPriority = this.calculateRushPriority(order, rushLevel);
        delay = 0; // Immediate processing
      } else if (priority === 'low') {
        queueName = 'low';
        jobPriority = -10;
        delay = 5000; // 5 second delay
      } else {
        jobPriority = this.calculateStandardPriority(order);
        delay = 1000; // 1 second delay
      }

      // Create job data
      const jobData = {
        orderId: order.orderId,
        customerId: order.customer.dmlogUserId,
        priority: priority,
        rushLevel: rushLevel,
        material: order.printSpecs.material.type,
        estimatedValue: order.pricing?.finalPricing?.totalAmount || 0,
        createdAt: order.createdAt,
        urgency: order.printSpecs.requirements.urgency,
        addedToQueue: new Date()
      };

      // Add job to queue
      const job = await this.queues[queueName].add(
        'processOrder',
        jobData,
        {
          priority: jobPriority,
          delay: delay,
          attempts: priority === 'rush' ? 5 : 3,
          removeOnComplete: priority === 'rush' ? 20 : 50
        }
      );

      // Update order with queue information
      order.metadata.queueInfo = {
        queueName,
        jobId: job.id,
        priority: jobPriority,
        rushLevel,
        addedAt: new Date(),
        estimatedProcessing: this.calculateEstimatedProcessingTime(priority, rushLevel)
      };

      await order.save();

      logger.logBusinessEvent('order_added_to_queue', {
        orderId: order.orderId,
        queueName,
        jobId: job.id,
        priority: jobPriority,
        rushLevel
      });

      return {
        queueName,
        jobId: job.id,
        position: await job.getPosition(),
        estimatedWait: await this.calculateEstimatedWaitTime(queueName, job.id),
        rushPricing: rushLevel ? this.calculateRushPricing(order, rushLevel) : null
      };
    } catch (error) {
      logger.error('Error adding order to queue:', error);
      throw error;
    }
  }

  /**
   * Calculate priority for rush orders
   */
  calculateRushPriority(order, rushLevel) {
    let basePriority = 100;

    // Rush level multiplier
    const rushMultipliers = {
      immediate: 50,
      express: 30,
      expedited: 20
    };
    basePriority += rushMultipliers[rushLevel] || 0;

    // Customer tier bonus
    if (order.customer.tier === 'premium') basePriority += 20;
    if (order.customer.tier === 'enterprise') basePriority += 30;

    // Order value bonus
    const orderValue = order.pricing?.finalPricing?.totalAmount || 0;
    if (orderValue > 500) basePriority += 15;
    if (orderValue > 1000) basePriority += 25;

    // Time-based urgency
    const orderAge = Date.now() - new Date(order.createdAt).getTime();
    const ageInHours = orderAge / (1000 * 60 * 60);
    
    if (ageInHours > 24) basePriority += 10; // Older orders get priority
    if (ageInHours > 48) basePriority += 20;

    return basePriority;
  }

  /**
   * Calculate priority for standard orders
   */
  calculateStandardPriority(order) {
    let basePriority = 0;

    // FIFO by default, but with adjustments
    const orderAge = Date.now() - new Date(order.createdAt).getTime();
    const ageInMinutes = orderAge / (1000 * 60);
    basePriority += Math.floor(ageInMinutes / 60); // 1 priority point per hour

    // Customer tier adjustment
    if (order.customer.tier === 'premium') basePriority += 5;
    if (order.customer.tier === 'enterprise') basePriority += 10;

    // Complexity adjustment (simpler orders get slight priority)
    const complexity = order.metadata?.analysis?.complexity;
    if (complexity === 'simple') basePriority += 2;
    else if (complexity === 'complex') basePriority -= 2;

    return basePriority;
  }

  /**
   * Calculate rush pricing
   */
  calculateRushPricing(order, rushLevel) {
    const basePrice = order.pricing?.finalPricing?.totalAmount || 0;
    const multiplier = this.rushPriceMultipliers[rushLevel] || 1.5;
    const rushFee = basePrice * (multiplier - 1);

    return {
      basePrice,
      rushLevel,
      multiplier,
      rushFee: Math.round(rushFee * 100) / 100,
      totalPrice: Math.round((basePrice + rushFee) * 100) / 100,
      estimatedCompletion: this.calculateRushDeliveryTime(rushLevel),
      guarantees: this.getRushGuarantees(rushLevel)
    };
  }

  /**
   * Calculate rush delivery time
   */
  calculateRushDeliveryTime(rushLevel) {
    const now = new Date();
    const deliveryHours = {
      immediate: 6,   // 6 hours
      express: 24,    // 24 hours
      expedited: 72   // 72 hours
    };

    const hours = deliveryHours[rushLevel] || 168; // Default 1 week
    return new Date(now.getTime() + hours * 60 * 60 * 1000);
  }

  /**
   * Get rush service guarantees
   */
  getRushGuarantees(rushLevel) {
    const guarantees = {
      immediate: [
        'Processing starts within 30 minutes',
        'Dedicated maker assignment',
        'Real-time progress updates',
        'Express shipping included',
        'Full refund if delivery is late'
      ],
      express: [
        'Processing starts within 2 hours',
        'Priority maker assignment',
        'Hourly progress updates',
        'Express shipping included',
        '50% refund if delivery is late'
      ],
      expedited: [
        'Processing starts within 12 hours',
        'Priority queue placement',
        'Daily progress updates',
        'Standard shipping included',
        '25% refund if delivery is late'
      ]
    };

    return guarantees[rushLevel] || [];
  }

  /**
   * Get queue position for an order
   */
  async getQueuePosition(orderId) {
    try {
      const order = await Order.findOne({ orderId });
      if (!order?.metadata?.queueInfo) {
        return null;
      }

      const { queueName, jobId } = order.metadata.queueInfo;
      const queue = this.queues[queueName];
      
      if (!queue) {
        throw new Error(`Queue ${queueName} not found`);
      }

      const job = await queue.getJob(jobId);
      if (!job) {
        return null; // Job may have been processed
      }

      const position = await job.getPosition();
      const waitingJobs = await queue.getWaiting();
      
      return {
        position: position + 1, // 1-indexed
        totalWaiting: waitingJobs.length,
        estimatedWait: await this.calculateEstimatedWaitTime(queueName, jobId),
        status: await job.getState()
      };
    } catch (error) {
      logger.error('Error getting queue position:', error);
      throw error;
    }
  }

  /**
   * Calculate estimated wait time
   */
  async calculateEstimatedWaitTime(queueName, jobId) {
    try {
      const queue = this.queues[queueName];
      const job = await queue.getJob(jobId);
      
      if (!job) return null;

      const position = await job.getPosition();
      
      // Get average processing time for this queue
      const avgProcessingTime = await this.getAverageProcessingTime(queueName);
      
      // Calculate estimated wait
      const estimatedMinutes = position * avgProcessingTime;
      const estimatedWait = new Date(Date.now() + estimatedMinutes * 60 * 1000);

      return {
        position: position + 1,
        estimatedMinutes,
        estimatedCompletion: estimatedWait,
        confidence: this.calculateEstimateConfidence(queueName, position)
      };
    } catch (error) {
      logger.error('Error calculating wait time:', error);
      return null;
    }
  }

  /**
   * Get average processing time for a queue
   */
  async getAverageProcessingTime(queueName) {
    try {
      const cacheKey = `avg_processing_time:${queueName}`;
      const cached = await redis.get(cacheKey);
      
      if (cached) {
        return parseFloat(cached);
      }

      // Calculate from completed jobs
      const queue = this.queues[queueName];
      const completed = await queue.getCompleted(0, 100);
      
      if (completed.length === 0) {
        // Default estimates by queue type
        const defaults = {
          rush: 15,     // 15 minutes average
          standard: 45, // 45 minutes average
          low: 120      // 2 hours average
        };
        return defaults[queueName] || 60;
      }

      let totalTime = 0;
      let validJobs = 0;

      completed.forEach(job => {
        const processedOn = job.processedOn;
        const timestamp = job.timestamp;
        
        if (processedOn && timestamp) {
          totalTime += (processedOn - timestamp);
          validJobs++;
        }
      });

      const avgTime = validJobs > 0 ? totalTime / validJobs / (1000 * 60) : 60; // Convert to minutes
      
      // Cache for 1 hour
      await redis.set(cacheKey, avgTime.toString(), 3600);
      
      return Math.max(5, avgTime); // Minimum 5 minutes
    } catch (error) {
      logger.error('Error calculating average processing time:', error);
      return 60; // Default 1 hour
    }
  }

  /**
   * Calculate confidence level for time estimates
   */
  calculateEstimateConfidence(queueName, position) {
    // Confidence decreases with queue position and varies by queue type
    let baseConfidence = 90;
    
    // Position adjustment
    if (position > 50) baseConfidence -= 20;
    else if (position > 20) baseConfidence -= 10;
    else if (position > 5) baseConfidence -= 5;

    // Queue type adjustment
    if (queueName === 'rush') baseConfidence += 5; // Rush queues more predictable
    else if (queueName === 'low') baseConfidence -= 10; // Low priority less predictable

    return Math.max(50, Math.min(95, baseConfidence));
  }

  /**
   * Move order to different priority level
   */
  async changeOrderPriority(orderId, newPriority, rushLevel = null) {
    try {
      const order = await Order.findOne({ orderId });
      if (!order) {
        throw new Error(`Order ${orderId} not found`);
      }

      const currentQueue = order.metadata?.queueInfo;
      if (!currentQueue) {
        throw new Error('Order not in queue');
      }

      // Remove from current queue
      const oldQueue = this.queues[currentQueue.queueName];
      const oldJob = await oldQueue.getJob(currentQueue.jobId);
      
      if (oldJob) {
        await oldJob.remove();
      }

      // Add to new queue with new priority
      const result = await this.addOrderToQueue(orderId, newPriority, rushLevel);

      logger.logBusinessEvent('order_priority_changed', {
        orderId,
        oldPriority: currentQueue.queueName,
        newPriority,
        oldJobId: currentQueue.jobId,
        newJobId: result.jobId
      });

      return result;
    } catch (error) {
      logger.error('Error changing order priority:', error);
      throw error;
    }
  }

  /**
   * Get queue statistics
   */
  async getQueueStats() {
    try {
      const stats = {};

      for (const [name, queue] of Object.entries(this.queues)) {
        const [waiting, active, completed, failed, delayed] = await Promise.all([
          queue.getWaiting(),
          queue.getActive(),
          queue.getCompleted(),
          queue.getFailed(),
          queue.getDelayed()
        ]);

        stats[name] = {
          waiting: waiting.length,
          active: active.length,
          completed: completed.length,
          failed: failed.length,
          delayed: delayed.length,
          avgProcessingTime: await this.getAverageProcessingTime(name)
        };
      }

      // Overall statistics
      const totalWaiting = Object.values(stats).reduce((sum, s) => sum + s.waiting, 0);
      const totalActive = Object.values(stats).reduce((sum, s) => sum + s.active, 0);
      const totalCompleted = Object.values(stats).reduce((sum, s) => sum + s.completed, 0);

      return {
        queues: stats,
        overall: {
          totalWaiting,
          totalActive,
          totalCompleted,
          totalQueues: Object.keys(this.queues).length,
          averageWaitTime: this.calculateOverallAverageWait(stats)
        },
        updated: new Date()
      };
    } catch (error) {
      logger.error('Error getting queue stats:', error);
      throw error;
    }
  }

  /**
   * Calculate estimated processing time based on priority and rush level
   */
  calculateEstimatedProcessingTime(priority, rushLevel) {
    const baseTimes = {
      rush: {
        immediate: 30,   // 30 minutes
        express: 120,    // 2 hours
        expedited: 480   // 8 hours
      },
      standard: 1440,    // 24 hours
      low: 4320          // 72 hours
    };

    if (priority === 'rush' && rushLevel) {
      return baseTimes.rush[rushLevel] || baseTimes.rush.expedited;
    }

    return baseTimes[priority] || baseTimes.standard;
  }

  /**
   * Calculate overall average wait time
   */
  calculateOverallAverageWait(stats) {
    let totalWeight = 0;
    let weightedSum = 0;

    Object.entries(stats).forEach(([queueName, queueStats]) => {
      const weight = queueStats.waiting + queueStats.active;
      if (weight > 0) {
        totalWeight += weight;
        weightedSum += queueStats.avgProcessingTime * weight;
      }
    });

    return totalWeight > 0 ? Math.round(weightedSum / totalWeight) : 0;
  }

  /**
   * Setup queue processors
   */
  setupQueueProcessors() {
    // Rush queue processor
    this.queues.rush.process('processOrder', 10, async (job) => {
      return await this.processOrderJob(job, 'rush');
    });

    // Standard queue processor
    this.queues.standard.process('processOrder', 5, async (job) => {
      return await this.processOrderJob(job, 'standard');
    });

    // Low priority queue processor
    this.queues.low.process('processOrder', 2, async (job) => {
      return await this.processOrderJob(job, 'low');
    });
  }

  /**
   * Process an order job
   */
  async processOrderJob(job, queueType) {
    const { orderId } = job.data;
    
    try {
      logger.logBusinessEvent('queue_job_processing_started', {
        jobId: job.id,
        orderId,
        queueType,
        attempt: job.attemptsMade + 1
      });

      // Update job progress
      await job.progress(10);

      // Get order
      const order = await Order.findOne({ orderId });
      if (!order) {
        throw new Error(`Order ${orderId} not found`);
      }

      await job.progress(25);

      // Process based on current order status
      let result;
      switch (order.status) {
        case 'pending':
          result = await this.processPendingOrder(order, job);
          break;
        case 'analyzing':
          result = await this.processAnalyzingOrder(order, job);
          break;
        case 'matching_makers':
          result = await this.processMatchingOrder(order, job);
          break;
        default:
          result = { status: 'no_action_needed', message: 'Order does not need queue processing' };
      }

      await job.progress(100);

      logger.logBusinessEvent('queue_job_completed', {
        jobId: job.id,
        orderId,
        queueType,
        result: result.status,
        processingTime: Date.now() - job.timestamp
      });

      return result;
    } catch (error) {
      logger.error(`Queue job failed for order ${orderId}:`, error);
      throw error;
    }
  }

  /**
   * Process pending order
   */
  async processPendingOrder(order, job) {
    // Import here to avoid circular dependencies
    const orderPipelineService = require('./orderPipelineService');
    
    await job.progress(50);
    
    // Start the order pipeline
    await orderPipelineService.analyzeOrder(order);
    
    await job.progress(75);
    
    return {
      status: 'analysis_started',
      message: 'Order analysis initiated',
      nextStatus: 'analyzing'
    };
  }

  /**
   * Process analyzing order
   */
  async processAnalyzingOrder(order, job) {
    const orderPipelineService = require('./orderPipelineService');
    
    await job.progress(50);
    
    // Find eligible makers
    await orderPipelineService.findEligibleMakers(order);
    
    await job.progress(75);
    
    return {
      status: 'makers_matched',
      message: 'Eligible makers found',
      nextStatus: 'matching_makers'
    };
  }

  /**
   * Process matching order
   */
  async processMatchingOrder(order, job) {
    const orderPipelineService = require('./orderPipelineService');
    
    await job.progress(50);
    
    // Request quotes from makers
    await orderPipelineService.requestQuotes(order);
    
    await job.progress(75);
    
    return {
      status: 'quotes_requested',
      message: 'Quote requests sent to makers',
      nextStatus: 'quotes_requested'
    };
  }

  /**
   * Setup queue event listeners
   */
  setupQueueEvents() {
    Object.entries(this.queues).forEach(([name, queue]) => {
      queue.on('completed', (job, result) => {
        logger.debug(`Queue ${name} job ${job.id} completed`, { result });
      });

      queue.on('failed', (job, err) => {
        logger.error(`Queue ${name} job ${job.id} failed:`, err);
      });

      queue.on('stalled', (job) => {
        logger.warn(`Queue ${name} job ${job.id} stalled`);
      });

      queue.on('progress', (job, progress) => {
        logger.debug(`Queue ${name} job ${job.id} progress: ${progress}%`);
      });
    });
  }

  /**
   * Cleanup completed and failed jobs
   */
  async cleanupQueues() {
    try {
      for (const [name, queue] of Object.entries(this.queues)) {
        await queue.clean(24 * 60 * 60 * 1000, 'completed'); // Clean completed jobs older than 24h
        await queue.clean(7 * 24 * 60 * 60 * 1000, 'failed'); // Clean failed jobs older than 7 days
        
        logger.debug(`Cleaned up queue: ${name}`);
      }
    } catch (error) {
      logger.error('Error cleaning up queues:', error);
    }
  }

  /**
   * Pause/resume queues for maintenance
   */
  async pauseQueues() {
    for (const queue of Object.values(this.queues)) {
      await queue.pause();
    }
    logger.info('All queues paused for maintenance');
  }

  async resumeQueues() {
    for (const queue of Object.values(this.queues)) {
      await queue.resume();
    }
    logger.info('All queues resumed');
  }

  /**
   * Get queue health status
   */
  async getQueueHealth() {
    const health = {};

    for (const [name, queue] of Object.entries(this.queues)) {
      try {
        const isPaused = await queue.isPaused();
        const waiting = await queue.getWaiting();
        const active = await queue.getActive();
        const failed = await queue.getFailed();

        health[name] = {
          status: isPaused ? 'paused' : 'active',
          waiting: waiting.length,
          active: active.length,
          failed: failed.length,
          healthy: !isPaused && failed.length < 10 // Simple health check
        };
      } catch (error) {
        health[name] = {
          status: 'error',
          error: error.message,
          healthy: false
        };
      }
    }

    return health;
  }
}

module.exports = new PriorityQueueService();