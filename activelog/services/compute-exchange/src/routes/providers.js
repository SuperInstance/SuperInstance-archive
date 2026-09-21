import express from 'express';
import Joi from 'joi';
import { ProviderManager } from '../services/providerManager.js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

const router = express.Router();
const providerManager = new ProviderManager();

// Validation schemas
const registerProviderSchema = Joi.object({
  university_id: Joi.number().integer().required(),
  name: Joi.string().min(1).max(255).required(),
  type: Joi.string().valid('slurm', 'kubernetes', 'docker', 'bare_metal').required(),
  endpoint: Joi.string().uri().required(),
  ssh_host: Joi.string().when('type', {
    is: Joi.string().valid('slurm', 'bare_metal'),
    then: Joi.required(),
    otherwise: Joi.optional()
  }),
  ssh_port: Joi.number().integer().min(1).max(65535).default(22),
  ssh_username: Joi.string().when('type', {
    is: Joi.string().valid('slurm', 'bare_metal'),
    then: Joi.required(),
    otherwise: Joi.optional()
  }),
  ssh_key_path: Joi.string(),
  config_data: Joi.object().default({}),
  total_cpu_cores: Joi.number().integer().min(1).required(),
  total_memory_gb: Joi.number().min(1).required(),
  total_storage_gb: Joi.number().min(0).default(0)
});

const updateCapacitySchema = Joi.object({
  available_cpu_cores: Joi.number().integer().min(0).required(),
  available_memory_gb: Joi.number().min(0).required(),
  available_storage_gb: Joi.number().min(0).required(),
  utilization_percent: Joi.number().min(0).max(100).required(),
  cpu_utilization: Joi.number().min(0).max(100),
  memory_utilization: Joi.number().min(0).max(100),
  storage_utilization: Joi.number().min(0).max(100),
  active_jobs: Joi.number().integer().min(0),
  queued_jobs: Joi.number().integer().min(0),
  spare_capacity_percent: Joi.number().min(0).max(100)
});

// Register a new provider
router.post('/', authMiddleware, requireRole(['admin', 'university_admin']), async (req, res) => {
  try {
    const { error, value } = registerProviderSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    // Check if user can register provider for this university
    if (req.user.role === 'university_admin' && req.user.university_id !== value.university_id) {
      return res.status(403).json({ error: 'Cannot register provider for different university' });
    }

    const providerId = await providerManager.registerProvider(value);
    
    logger.info(`Provider registered by user ${req.user.id}:`, { providerId, name: value.name });
    
    res.status(201).json({
      message: 'Provider registered successfully',
      providerId,
      status: 'active'
    });
  } catch (error) {
    logger.error('Provider registration failed:', error);
    res.status(500).json({ error: 'Failed to register provider' });
  }
});

// Get all providers (with optional university filter)
router.get('/', authMiddleware, async (req, res) => {
  try {
    const universityId = req.user.role === 'university_admin' 
      ? req.user.university_id 
      : req.query.university_id;
    
    const providers = await providerManager.getActiveProviders(universityId);
    
    res.json({
      providers: providers.map(provider => ({
        ...provider,
        config_data: undefined // Don't expose sensitive config
      }))
    });
  } catch (error) {
    logger.error('Failed to get providers:', error);
    res.status(500).json({ error: 'Failed to get providers' });
  }
});

// Get specific provider
router.get('/:id', authMiddleware, async (req, res) => {
  try {
    const providerId = parseInt(req.params.id);
    const provider = await providerManager.getProvider(providerId);
    
    if (!provider) {
      return res.status(404).json({ error: 'Provider not found' });
    }

    // Check permissions
    if (req.user.role === 'university_admin' && req.user.university_id !== provider.university_id) {
      return res.status(403).json({ error: 'Access denied' });
    }

    res.json({
      ...provider,
      config_data: req.user.role === 'admin' ? provider.config_data : undefined
    });
  } catch (error) {
    logger.error('Failed to get provider:', error);
    res.status(500).json({ error: 'Failed to get provider' });
  }
});

// Test provider connection
router.post('/:id/test', authMiddleware, requireRole(['admin', 'university_admin']), async (req, res) => {
  try {
    const providerId = parseInt(req.params.id);
    const provider = await providerManager.getProvider(providerId);
    
    if (!provider) {
      return res.status(404).json({ error: 'Provider not found' });
    }

    // Check permissions
    if (req.user.role === 'university_admin' && req.user.university_id !== provider.university_id) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const result = await providerManager.testProviderConnection(providerId);
    
    logger.info(`Connection test for provider ${providerId}:`, result);
    
    res.json(result);
  } catch (error) {
    logger.error('Provider connection test failed:', error);
    res.status(500).json({ error: 'Connection test failed' });
  }
});

// Update provider capacity
router.put('/:id/capacity', authMiddleware, requireRole(['admin', 'university_admin']), async (req, res) => {
  try {
    const providerId = parseInt(req.params.id);
    const { error, value } = updateCapacitySchema.validate(req.body);
    
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const provider = await providerManager.getProvider(providerId);
    
    if (!provider) {
      return res.status(404).json({ error: 'Provider not found' });
    }

    // Check permissions
    if (req.user.role === 'university_admin' && req.user.university_id !== provider.university_id) {
      return res.status(403).json({ error: 'Access denied' });
    }

    await providerManager.updateProviderCapacity(providerId, value);
    
    logger.info(`Capacity updated for provider ${providerId} by user ${req.user.id}`);
    
    res.json({ message: 'Capacity updated successfully' });
  } catch (error) {
    logger.error('Failed to update provider capacity:', error);
    res.status(500).json({ error: 'Failed to update capacity' });
  }
});

// Get provider capacity
router.get('/:id/capacity', authMiddleware, async (req, res) => {
  try {
    const providerId = parseInt(req.params.id);
    const provider = await providerManager.getProvider(providerId);
    
    if (!provider) {
      return res.status(404).json({ error: 'Provider not found' });
    }

    // Check permissions
    if (req.user.role === 'university_admin' && req.user.university_id !== provider.university_id) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const capacity = await providerManager.getProviderCapacity(providerId);
    
    res.json(capacity);
  } catch (error) {
    logger.error('Failed to get provider capacity:', error);
    res.status(500).json({ error: 'Failed to get capacity' });
  }
});

// Get spare capacity
router.get('/spare-capacity', authMiddleware, async (req, res) => {
  try {
    const universityId = req.user.role === 'university_admin' 
      ? req.user.university_id 
      : req.query.university_id;

    const spareCapacity = await providerManager.getSpareCapacity();
    
    // Filter by university if needed
    const filteredCapacity = universityId 
      ? spareCapacity.filter(provider => provider.university_id === parseInt(universityId))
      : spareCapacity;
    
    res.json({ spareCapacity: filteredCapacity });
  } catch (error) {
    logger.error('Failed to get spare capacity:', error);
    res.status(500).json({ error: 'Failed to get spare capacity' });
  }
});

// Update provider status
router.put('/:id/status', authMiddleware, requireRole(['admin', 'university_admin']), async (req, res) => {
  try {
    const providerId = parseInt(req.params.id);
    const { status } = req.body;
    
    if (!['active', 'maintenance', 'offline', 'error'].includes(status)) {
      return res.status(400).json({ error: 'Invalid status' });
    }

    const provider = await providerManager.getProvider(providerId);
    
    if (!provider) {
      return res.status(404).json({ error: 'Provider not found' });
    }

    // Check permissions
    if (req.user.role === 'university_admin' && req.user.university_id !== provider.university_id) {
      return res.status(403).json({ error: 'Access denied' });
    }

    await providerManager.updateProviderStatus(providerId, status);
    
    logger.info(`Provider ${providerId} status changed to ${status} by user ${req.user.id}`);
    
    res.json({ message: 'Status updated successfully', status });
  } catch (error) {
    logger.error('Failed to update provider status:', error);
    res.status(500).json({ error: 'Failed to update status' });
  }
});

export default router;