import express from 'express';
import Joi from 'joi';
import { JobQueue } from '../services/jobQueue.js';
import { authMiddleware } from '../middleware/auth.js';
import { getDb } from '../database/init.js';
import { logger } from '../utils/logger.js';

const router = express.Router();
const jobQueue = new JobQueue();

// Initialize job queue
jobQueue.initialize().catch(error => {
  logger.error('Failed to initialize job queue:', error);
});

// Validation schemas
const submitJobSchema = Joi.object({
  job_name: Joi.string().min(1).max(255).required(),
  job_type: Joi.string().valid('compute', 'gpu', 'memory', 'storage', 'network').required(),
  priority: Joi.number().integer().min(1).max(10).default(5),
  cpu_cores: Joi.number().integer().min(1).required(),
  memory_gb: Joi.number().min(1).required(),
  storage_gb: Joi.number().min(0).default(0),
  gpu_count: Joi.number().integer().min(0).default(0),
  estimated_duration_minutes: Joi.number().integer().min(1).default(60),
  max_cost: Joi.number().min(0).optional(),
  quality_tier: Joi.string().valid('basic', 'standard', 'premium', 'enterprise').default('standard'),
  command: Joi.string().required(),
  environment_vars: Joi.object().default({}),
  docker_image: Joi.string().optional(),
  scheduled_start: Joi.date().iso().optional()
});

// Submit a new job
router.post('/', authMiddleware, async (req, res) => {
  try {
    const { error, value } = submitJobSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    // Check user's budget/balance if max_cost is set
    if (value.max_cost) {
      const user = await getUserById(req.user.id);
      if (user && user.current_balance < value.max_cost) {
        return res.status(400).json({ 
          error: 'Insufficient balance for maximum job cost',
          current_balance: user.current_balance,
          required_cost: value.max_cost
        });
      }
    }

    const result = await jobQueue.submitJob(value, req.user.id);
    
    logger.info(`Job submitted by user ${req.user.id}:`, { 
      jobId: result.job_id, 
      jobName: value.job_name 
    });
    
    res.status(201).json({
      message: 'Job submitted successfully',
      job_id: result.job_id,
      priority_score: result.priority_score,
      status: result.status,
      estimated_start: await getEstimatedStartTime(result.job_id)
    });
  } catch (error) {
    logger.error('Job submission failed:', error);
    res.status(500).json({ error: 'Failed to submit job' });
  }
});

// Get user's jobs
router.get('/', authMiddleware, async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);
    const offset = (page - 1) * limit;
    const status = req.query.status;

    const jobs = await getUserJobs(req.user.id, offset, limit, status);
    const totalJobs = await getUserJobsCount(req.user.id, status);
    
    res.json({
      jobs,
      pagination: {
        current_page: page,
        total_pages: Math.ceil(totalJobs / limit),
        total_jobs: totalJobs,
        per_page: limit
      }
    });
  } catch (error) {
    logger.error('Failed to get user jobs:', error);
    res.status(500).json({ error: 'Failed to get jobs' });
  }
});

// Get specific job
router.get('/:id', authMiddleware, async (req, res) => {
  try {
    const jobId = parseInt(req.params.id);
    const job = await getJobById(jobId);
    
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    // Check ownership or admin access
    if (job.user_id !== req.user.id && !['admin', 'university_admin'].includes(req.user.role)) {
      return res.status(403).json({ error: 'Access denied' });
    }

    // Get queue information if job is queued
    let queueInfo = null;
    if (job.status === 'queued') {
      queueInfo = await getJobQueueInfo(jobId);
    }

    res.json({
      ...job,
      queue_info: queueInfo,
      environment_vars: job.environment_vars ? JSON.parse(job.environment_vars) : {}
    });
  } catch (error) {
    logger.error('Failed to get job:', error);
    res.status(500).json({ error: 'Failed to get job' });
  }
});

// Cancel job
router.delete('/:id', authMiddleware, async (req, res) => {
  try {
    const jobId = parseInt(req.params.id);
    const job = await getJobById(jobId);
    
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    // Check ownership
    if (job.user_id !== req.user.id) {
      return res.status(403).json({ error: 'Access denied' });
    }

    // Check if job can be cancelled
    if (!['pending', 'queued', 'running'].includes(job.status)) {
      return res.status(400).json({ 
        error: 'Job cannot be cancelled',
        current_status: job.status
      });
    }

    await cancelJob(jobId);
    
    logger.info(`Job ${jobId} cancelled by user ${req.user.id}`);
    
    res.json({ 
      message: 'Job cancelled successfully',
      job_id: jobId
    });
  } catch (error) {
    logger.error('Job cancellation failed:', error);
    res.status(500).json({ error: 'Failed to cancel job' });
  }
});

// Get job queue status
router.get('/queue/status', authMiddleware, async (req, res) => {
  try {
    const includePersonal = req.query.personal === 'true';
    const userId = includePersonal ? req.user.id : null;
    
    const queueStatus = await jobQueue.getQueueStatus(userId);
    
    res.json(queueStatus);
  } catch (error) {
    logger.error('Failed to get queue status:', error);
    res.status(500).json({ error: 'Failed to get queue status' });
  }
});

// Get job statistics
router.get('/stats', authMiddleware, async (req, res) => {
  try {
    const stats = await getJobStatistics(req.user.id);
    res.json(stats);
  } catch (error) {
    logger.error('Failed to get job statistics:', error);
    res.status(500).json({ error: 'Failed to get statistics' });
  }
});

// Requeue failed job
router.post('/:id/requeue', authMiddleware, async (req, res) => {
  try {
    const jobId = parseInt(req.params.id);
    const job = await getJobById(jobId);
    
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    if (job.user_id !== req.user.id) {
      return res.status(403).json({ error: 'Access denied' });
    }

    if (job.status !== 'failed') {
      return res.status(400).json({ 
        error: 'Only failed jobs can be requeued',
        current_status: job.status
      });
    }

    // Create new job based on failed job
    const newJobData = {
      job_name: `${job.job_name} (Requeued)`,
      job_type: job.job_type,
      priority: job.priority,
      cpu_cores: job.cpu_cores,
      memory_gb: job.memory_gb,
      storage_gb: job.storage_gb,
      gpu_count: job.gpu_count,
      estimated_duration_minutes: job.estimated_duration_minutes,
      max_cost: job.max_cost,
      quality_tier: job.quality_tier,
      command: job.command,
      environment_vars: JSON.parse(job.environment_vars || '{}'),
      docker_image: job.docker_image
    };

    const result = await jobQueue.submitJob(newJobData, req.user.id);
    
    logger.info(`Job ${jobId} requeued as ${result.job_id} by user ${req.user.id}`);
    
    res.json({
      message: 'Job requeued successfully',
      original_job_id: jobId,
      new_job_id: result.job_id,
      priority_score: result.priority_score
    });
  } catch (error) {
    logger.error('Job requeue failed:', error);
    res.status(500).json({ error: 'Failed to requeue job' });
  }
});

// Helper functions
async function getUserById(userId) {
  const db = getDb();
  try {
    return await new Promise((resolve, reject) => {
      db.get('SELECT * FROM users WHERE id = ?', [userId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  } catch (error) {
    logger.error('Failed to get user:', error);
    return null;
  } finally {
    db.close();
  }
}

async function getJobById(jobId) {
  const db = getDb();
  try {
    return await new Promise((resolve, reject) => {
      db.get('SELECT * FROM jobs WHERE id = ?', [jobId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  } catch (error) {
    logger.error('Failed to get job:', error);
    return null;
  } finally {
    db.close();
  }
}

async function getUserJobs(userId, offset = 0, limit = 20, status = null) {
  const db = getDb();
  try {
    const statusFilter = status ? 'AND j.status = ?' : '';
    const params = status ? [userId, status, limit, offset] : [userId, limit, offset];
    
    return await new Promise((resolve, reject) => {
      db.all(`
        SELECT j.*, p.name as provider_name, p.university_id as provider_university_id
        FROM jobs j
        LEFT JOIN providers p ON j.provider_id = p.id
        WHERE j.user_id = ? ${statusFilter}
        ORDER BY j.created_at DESC
        LIMIT ? OFFSET ?
      `, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  } finally {
    db.close();
  }
}

async function getUserJobsCount(userId, status = null) {
  const db = getDb();
  try {
    const statusFilter = status ? 'AND status = ?' : '';
    const params = status ? [userId, status] : [userId];
    
    const result = await new Promise((resolve, reject) => {
      db.get(`
        SELECT COUNT(*) as count FROM jobs 
        WHERE user_id = ? ${statusFilter}
      `, params, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    
    return result.count;
  } finally {
    db.close();
  }
}

async function getJobQueueInfo(jobId) {
  const db = getDb();
  try {
    return await new Promise((resolve, reject) => {
      db.get(
        'SELECT * FROM job_queue WHERE job_id = ?',
        [jobId],
        (err, row) => {
          if (err) reject(err);
          else resolve(row);
        }
      );
    });
  } finally {
    db.close();
  }
}

async function getEstimatedStartTime(jobId) {
  const queueInfo = await getJobQueueInfo(jobId);
  if (!queueInfo) return null;
  
  const estimatedStart = new Date();
  estimatedStart.setMinutes(estimatedStart.getMinutes() + queueInfo.estimated_wait_minutes);
  
  return estimatedStart.toISOString();
}

async function cancelJob(jobId) {
  const db = getDb();
  try {
    await new Promise((resolve, reject) => {
      db.run(
        'UPDATE jobs SET status = "cancelled", updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        [jobId],
        (err) => {
          if (err) reject(err);
          else resolve();
        }
      );
    });

    // Remove from queue if still queued
    await new Promise((resolve, reject) => {
      db.run('DELETE FROM job_queue WHERE job_id = ?', [jobId], (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  } finally {
    db.close();
  }
}

async function getJobStatistics(userId) {
  const db = getDb();
  try {
    const stats = await new Promise((resolve, reject) => {
      db.get(`
        SELECT 
          COUNT(*) as total_jobs,
          SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_jobs,
          SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
          SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_jobs,
          SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) as queued_jobs,
          AVG(CASE WHEN actual_duration_minutes > 0 THEN actual_duration_minutes ELSE NULL END) as avg_duration,
          MIN(created_at) as first_job,
          MAX(completed_at) as last_completed
        FROM jobs 
        WHERE user_id = ?
      `, [userId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    const successRate = stats.total_jobs > 0 
      ? (stats.completed_jobs / stats.total_jobs * 100).toFixed(1)
      : 0;

    return {
      ...stats,
      success_rate_percent: parseFloat(successRate),
      avg_duration_minutes: Math.round(stats.avg_duration || 0)
    };
  } finally {
    db.close();
  }
}

export default router;