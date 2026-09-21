const Bull = require('bull');
const logger = require('./logger');
const { redisClient } = require('./redis');

// Queue configurations
const queueConfig = {
  redis: {
    port: process.env.REDIS_PORT || 6379,
    host: process.env.REDIS_HOST || 'localhost',
    password: process.env.REDIS_PASSWORD || undefined,
    db: process.env.REDIS_QUEUE_DB || 1
  },
  defaultJobOptions: {
    removeOnComplete: 10,
    removeOnFail: 50,
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 2000
    }
  }
};

// Initialize queues
const queues = {};

// AI Generation Queue - for processing AI requests
const aiQueue = new Bull('ai-generation', queueConfig);

// Auto-save Queue - for processing auto-saves
const autoSaveQueue = new Bull('auto-save', queueConfig);

// Collaboration Queue - for real-time collaboration updates
const collaborationQueue = new Bull('collaboration', queueConfig);

// Version Control Queue - for version control operations
const versionControlQueue = new Bull('version-control', queueConfig);

// File Processing Queue - for image uploads, etc.
const fileProcessingQueue = new Bull('file-processing', queueConfig);

// Notification Queue - for sending notifications
const notificationQueue = new Bull('notifications', queueConfig);

// Store queues
queues.ai = aiQueue;
queues.autoSave = autoSaveQueue;
queues.collaboration = collaborationQueue;
queues.versionControl = versionControlQueue;
queues.fileProcessing = fileProcessingQueue;
queues.notifications = notificationQueue;

// AI Generation Job Processors
aiQueue.process('generate-adventure', 2, async (job) => {
  const { prompt, options, userId, worldId } = job.data;
  
  logger.ai('Processing adventure generation', { userId, worldId, prompt: prompt.substring(0, 100) });
  
  try {
    const aiAssistant = require('../services/aiAssistant');
    const result = await aiAssistant.generateAdventure(prompt, options);
    
    logger.ai('Adventure generation completed', { 
      userId, 
      worldId, 
      adventureTitle: result.adventure.title 
    });
    
    // Emit result via socket if available
    const io = require('../server').io;
    if (io) {
      io.to(`world:${worldId}`).emit('ai-generation-complete', {
        type: 'adventure',
        result: result.adventure,
        jobId: job.id,
        userId
      });
    }
    
    return result;
    
  } catch (error) {
    logger.error('AI adventure generation failed:', error);
    throw error;
  }
});

aiQueue.process('generate-npcs', 2, async (job) => {
  const { characterBackstories, worldContext, userId, worldId } = job.data;
  
  logger.ai('Processing NPC generation', { userId, worldId, backstoryCount: characterBackstories.length });
  
  try {
    const aiAssistant = require('../services/aiAssistant');
    const result = await aiAssistant.generateNPCsFromBackstories(characterBackstories, worldContext);
    
    logger.ai('NPC generation completed', { 
      userId, 
      worldId, 
      npcCount: result.npcs.length 
    });
    
    const io = require('../server').io;
    if (io) {
      io.to(`world:${worldId}`).emit('ai-generation-complete', {
        type: 'npcs',
        result: result.npcs,
        jobId: job.id,
        userId
      });
    }
    
    return result;
    
  } catch (error) {
    logger.error('AI NPC generation failed:', error);
    throw error;
  }
});

aiQueue.process('balance-encounter', 3, async (job) => {
  const { encounter, partyLevel, partySize, userId, worldId } = job.data;
  
  logger.ai('Processing encounter balancing', { userId, worldId, partyLevel, partySize });
  
  try {
    const aiAssistant = require('../services/aiAssistant');
    const result = await aiAssistant.balanceEncounter(encounter, partyLevel, partySize);
    
    logger.ai('Encounter balancing completed', { userId, worldId });
    
    const io = require('../server').io;
    if (io) {
      io.to(`world:${worldId}`).emit('ai-generation-complete', {
        type: 'encounter-balance',
        result: result.encounter,
        jobId: job.id,
        userId
      });
    }
    
    return result;
    
  } catch (error) {
    logger.error('AI encounter balancing failed:', error);
    throw error;
  }
});

aiQueue.process('generate-complete-world', 1, async (job) => {
  const { concept, playerCount, experienceLevel, userId } = job.data;
  
  logger.ai('Processing complete world generation', { userId, concept, playerCount, experienceLevel });
  
  try {
    const aiAssistant = require('../services/aiAssistant');
    const result = await aiAssistant.generateCompleteWorld(concept, playerCount, experienceLevel);
    
    logger.ai('Complete world generation completed', { 
      userId, 
      worldName: result.world.overview 
    });
    
    const io = require('../server').io;
    if (io) {
      io.emit('ai-world-complete', {
        result: result.world,
        jobId: job.id,
        userId
      });
    }
    
    return result;
    
  } catch (error) {
    logger.error('AI complete world generation failed:', error);
    throw error;
  }
});

// Auto-save Job Processors
autoSaveQueue.process('world-auto-save', 5, async (job) => {
  const { worldId, worldData, userId, timestamp } = job.data;
  
  try {
    const World = require('../models/World');
    const world = await World.findOne({ worldId });
    
    if (!world) {
      throw new Error(`World ${worldId} not found`);
    }
    
    // Update world data
    Object.assign(world, worldData);
    world.lastModified = new Date(timestamp);
    world.lastModifiedBy = userId;
    
    await world.save();
    
    // Cache updated world
    if (redisClient.isConnected) {
      await redisClient.cacheWorld(worldId, world, 3600);
    }
    
    logger.info(`Auto-save completed for world ${worldId}`, { userId });
    
    return { success: true, timestamp };
    
  } catch (error) {
    logger.error('Auto-save failed:', error);
    throw error;
  }
});

// Collaboration Job Processors
collaborationQueue.process('sync-collaborator-state', 10, async (job) => {
  const { worldId, userId, state } = job.data;
  
  try {
    // Update collaborator state in Redis
    await redisClient.addCollaborator(worldId, userId, {
      ...state,
      lastSync: new Date()
    });
    
    // Broadcast state update to other collaborators
    const io = require('../server').io;
    if (io) {
      io.to(`world:${worldId}`).emit('collaborator-state-synced', {
        userId,
        state,
        timestamp: new Date()
      });
    }
    
    return { success: true };
    
  } catch (error) {
    logger.error('Collaborator state sync failed:', error);
    throw error;
  }
});

// Version Control Job Processors
versionControlQueue.process('create-version-snapshot', 3, async (job) => {
  const { worldId, versionId, userId } = job.data;
  
  try {
    const World = require('../models/World');
    const world = await World.findOne({ worldId });
    
    if (!world) {
      throw new Error(`World ${worldId} not found`);
    }
    
    const version = world.versions.find(v => v.versionId === versionId);
    if (!version) {
      throw new Error(`Version ${versionId} not found`);
    }
    
    // Create full snapshot for this version
    version.snapshot = {
      content: JSON.parse(JSON.stringify(world.content)),
      metadata: {
        name: world.name,
        description: world.description,
        theme: world.theme,
        lastModified: world.lastModified
      },
      createdAt: new Date()
    };
    
    await world.save();
    
    logger.version(`Snapshot created for version ${versionId}`, { worldId, userId });
    
    return { success: true, snapshotSize: JSON.stringify(version.snapshot).length };
    
  } catch (error) {
    logger.error('Version snapshot creation failed:', error);
    throw error;
  }
});

// File Processing Job Processors
fileProcessingQueue.process('process-image-upload', 2, async (job) => {
  const { filePath, fileName, userId, worldId } = job.data;
  
  try {
    const sharp = require('sharp');
    const path = require('path');
    const fs = require('fs').promises;
    
    // Create thumbnails and optimized versions
    const baseName = path.parse(fileName).name;
    const uploadsDir = path.join(__dirname, '../../uploads');
    
    // Ensure uploads directory exists
    await fs.mkdir(uploadsDir, { recursive: true });
    
    // Process original image
    const originalBuffer = await fs.readFile(filePath);
    
    // Create thumbnail (200x200)
    const thumbnailPath = path.join(uploadsDir, `${baseName}_thumb.webp`);
    await sharp(originalBuffer)
      .resize(200, 200, { fit: 'cover' })
      .webp({ quality: 80 })
      .toFile(thumbnailPath);
    
    // Create medium size (800x600)
    const mediumPath = path.join(uploadsDir, `${baseName}_medium.webp`);
    await sharp(originalBuffer)
      .resize(800, 600, { fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 85 })
      .toFile(mediumPath);
    
    // Optimize original
    const optimizedPath = path.join(uploadsDir, `${baseName}_optimized.webp`);
    await sharp(originalBuffer)
      .webp({ quality: 90 })
      .toFile(optimizedPath);
    
    // Remove original file
    await fs.unlink(filePath);
    
    const result = {
      thumbnail: `/uploads/${baseName}_thumb.webp`,
      medium: `/uploads/${baseName}_medium.webp`,
      optimized: `/uploads/${baseName}_optimized.webp`,
      originalName: fileName
    };
    
    logger.info(`Image processing completed: ${fileName}`, { userId, worldId });
    
    // Notify client
    const io = require('../server').io;
    if (io && worldId) {
      io.to(`world:${worldId}`).emit('file-processed', {
        jobId: job.id,
        result,
        userId
      });
    }
    
    return result;
    
  } catch (error) {
    logger.error('Image processing failed:', error);
    throw error;
  }
});

// Notification Job Processors
notificationQueue.process('send-email', 3, async (job) => {
  const { to, subject, body, type, userId } = job.data;
  
  try {
    // In a real implementation, you would send email here
    logger.info(`Email notification sent: ${subject}`, { to, type, userId });
    
    return { success: true, sentAt: new Date() };
    
  } catch (error) {
    logger.error('Email notification failed:', error);
    throw error;
  }
});

notificationQueue.process('send-push', 5, async (job) => {
  const { userId, title, body, data } = job.data;
  
  try {
    // In a real implementation, you would send push notification here
    logger.info(`Push notification sent: ${title}`, { userId });
    
    return { success: true, sentAt: new Date() };
    
  } catch (error) {
    logger.error('Push notification failed:', error);
    throw error;
  }
});

// Queue event handlers
Object.entries(queues).forEach(([name, queue]) => {
  queue.on('completed', (job, result) => {
    logger.info(`Queue ${name}: Job ${job.id} completed`, { 
      jobData: job.data, 
      result: typeof result === 'object' ? 'object' : result 
    });
  });
  
  queue.on('failed', (job, error) => {
    logger.error(`Queue ${name}: Job ${job.id} failed`, { 
      error: error.message,
      jobData: job.data,
      attempts: job.attemptsMade
    });
  });
  
  queue.on('stalled', (job) => {
    logger.warn(`Queue ${name}: Job ${job.id} stalled`, { jobData: job.data });
  });
});

// Queue management functions
async function addAIGenerationJob(type, data, options = {}) {
  try {
    const job = await aiQueue.add(type, data, {
      ...queueConfig.defaultJobOptions,
      ...options
    });
    
    logger.ai(`AI generation job added: ${type}`, { jobId: job.id, userId: data.userId });
    
    return job;
  } catch (error) {
    logger.error(`Failed to add AI job: ${type}`, error);
    throw error;
  }
}

async function addAutoSaveJob(worldId, worldData, userId) {
  try {
    const job = await autoSaveQueue.add('world-auto-save', {
      worldId,
      worldData,
      userId,
      timestamp: new Date()
    }, {
      delay: 1000, // Delay by 1 second to batch rapid changes
      removeOnComplete: 5
    });
    
    return job;
  } catch (error) {
    logger.error('Failed to add auto-save job:', error);
    throw error;
  }
}

async function addCollaborationJob(type, data) {
  try {
    const job = await collaborationQueue.add(type, data, {
      priority: 1, // High priority for real-time updates
      removeOnComplete: 3
    });
    
    return job;
  } catch (error) {
    logger.error(`Failed to add collaboration job: ${type}`, error);
    throw error;
  }
}

async function addVersionControlJob(type, data) {
  try {
    const job = await versionControlQueue.add(type, data, {
      removeOnComplete: 10
    });
    
    return job;
  } catch (error) {
    logger.error(`Failed to add version control job: ${type}`, error);
    throw error;
  }
}

async function addFileProcessingJob(type, data) {
  try {
    const job = await fileProcessingQueue.add(type, data, {
      removeOnComplete: 5,
      removeOnFail: 10
    });
    
    return job;
  } catch (error) {
    logger.error(`Failed to add file processing job: ${type}`, error);
    throw error;
  }
}

async function addNotificationJob(type, data) {
  try {
    const job = await notificationQueue.add(type, data, {
      removeOnComplete: 20,
      removeOnFail: 50
    });
    
    return job;
  } catch (error) {
    logger.error(`Failed to add notification job: ${type}`, error);
    throw error;
  }
}

// Queue health check
async function getQueueStats() {
  const stats = {};
  
  for (const [name, queue] of Object.entries(queues)) {
    try {
      const waiting = await queue.waiting();
      const active = await queue.active();
      const completed = await queue.completed();
      const failed = await queue.failed();
      
      stats[name] = {
        waiting: waiting.length,
        active: active.length,
        completed: completed.length,
        failed: failed.length
      };
    } catch (error) {
      stats[name] = { error: error.message };
    }
  }
  
  return stats;
}

// Clean up old jobs
async function cleanupQueues() {
  for (const [name, queue] of Object.entries(queues)) {
    try {
      await queue.clean(24 * 60 * 60 * 1000, 'completed'); // Remove completed jobs older than 24 hours
      await queue.clean(72 * 60 * 60 * 1000, 'failed'); // Remove failed jobs older than 72 hours
      
      logger.info(`Cleaned up queue: ${name}`);
    } catch (error) {
      logger.error(`Failed to clean queue ${name}:`, error);
    }
  }
}

// Initialize queues
async function initializeQueues() {
  try {
    logger.info('Initializing background job queues...');
    
    // Start cleanup job (runs every hour)
    setInterval(cleanupQueues, 60 * 60 * 1000);
    
    logger.info('Background job queues initialized successfully');
    
    return queues;
  } catch (error) {
    logger.error('Failed to initialize queues:', error);
    throw error;
  }
}

// Graceful shutdown
async function shutdownQueues() {
  logger.info('Shutting down queues...');
  
  for (const [name, queue] of Object.entries(queues)) {
    try {
      await queue.close();
      logger.info(`Queue ${name} closed`);
    } catch (error) {
      logger.error(`Error closing queue ${name}:`, error);
    }
  }
}

module.exports = {
  queues,
  initializeQueues,
  shutdownQueues,
  addAIGenerationJob,
  addAutoSaveJob,
  addCollaborationJob,
  addVersionControlJob,
  addFileProcessingJob,
  addNotificationJob,
  getQueueStats,
  cleanupQueues
};