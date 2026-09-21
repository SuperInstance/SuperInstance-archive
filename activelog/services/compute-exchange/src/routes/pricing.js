import express from 'express';
import Joi from 'joi';
import { PricingEngine } from '../services/pricingEngine.js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

const router = express.Router();
const pricingEngine = new PricingEngine();

// Initialize pricing engine
pricingEngine.initializePricing().catch(error => {
  logger.error('Failed to initialize pricing engine:', error);
});

// Validation schemas
const priceEstimateSchema = Joi.object({
  provider_id: Joi.number().integer().required(),
  job_type: Joi.string().valid('compute', 'gpu', 'memory', 'storage', 'network').required(),
  quality_tier: Joi.string().valid('basic', 'standard', 'premium', 'enterprise').required(),
  cpu_cores: Joi.number().integer().min(1).required(),
  memory_gb: Joi.number().min(1).required(),
  storage_gb: Joi.number().min(0).default(0),
  gpu_count: Joi.number().integer().min(0).default(0),
  estimated_duration_minutes: Joi.number().integer().min(1).default(60),
  scheduled_start: Joi.date().iso().optional()
});

const updatePricingSchema = Joi.object({
  provider_id: Joi.number().integer().required(),
  job_type: Joi.string().valid('compute', 'gpu', 'memory', 'storage', 'network').required(),
  quality_tier: Joi.string().valid('basic', 'standard', 'premium', 'enterprise').required(),
  base_rate: Joi.number().min(0).precision(6).required(),
  effective_from: Joi.date().iso().optional()
});

// Get price estimate for a job
router.post('/estimate', authMiddleware, async (req, res) => {
  try {
    const { error, value } = priceEstimateSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    // Add user_id for bulk discount calculation
    value.user_id = req.user.id;

    const estimate = await pricingEngine.calculateJobPrice(value, value.provider_id);
    
    res.json({
      estimate,
      job_requirements: {
        cpu_cores: value.cpu_cores,
        memory_gb: value.memory_gb,
        storage_gb: value.storage_gb,
        gpu_count: value.gpu_count,
        estimated_duration_minutes: value.estimated_duration_minutes
      },
      provider_id: value.provider_id,
      job_type: value.job_type,
      quality_tier: value.quality_tier
    });
  } catch (error) {
    logger.error('Price estimate failed:', error);
    res.status(500).json({ error: 'Failed to calculate price estimate' });
  }
});

// Get current rates for all providers or specific filters
router.get('/rates', authMiddleware, async (req, res) => {
  try {
    const providerId = req.query.provider_id ? parseInt(req.query.provider_id) : null;
    const jobType = req.query.job_type || null;
    const qualityTier = req.query.quality_tier || null;

    const rates = await pricingEngine.getCurrentRates(providerId, jobType, qualityTier);
    
    res.json({
      rates,
      timestamp: new Date().toISOString(),
      filters: {
        provider_id: providerId,
        job_type: jobType,
        quality_tier: qualityTier
      }
    });
  } catch (error) {
    logger.error('Failed to get current rates:', error);
    res.status(500).json({ error: 'Failed to get rates' });
  }
});

// Compare prices across providers for a specific job
router.post('/compare', authMiddleware, async (req, res) => {
  try {
    const { error, value } = priceEstimateSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    // Get all active providers if not specified
    let providerIds = [];
    if (value.provider_id) {
      providerIds = [value.provider_id];
    } else {
      // Get providers from database - simplified for now
      providerIds = [1, 2, 3]; // This should query the database for active providers
    }

    value.user_id = req.user.id;
    const comparisons = [];

    for (const providerId of providerIds) {
      try {
        const estimate = await pricingEngine.calculateJobPrice(value, providerId);
        comparisons.push({
          provider_id: providerId,
          estimate
        });
      } catch (error) {
        logger.warn(`Failed to get estimate for provider ${providerId}:`, error.message);
        comparisons.push({
          provider_id: providerId,
          error: error.message
        });
      }
    }

    // Sort by estimated cost
    comparisons.sort((a, b) => {
      if (a.error && !b.error) return 1;
      if (!a.error && b.error) return -1;
      if (a.error && b.error) return 0;
      return parseFloat(a.estimate.estimated_cost) - parseFloat(b.estimate.estimated_cost);
    });

    res.json({
      job_requirements: {
        job_type: value.job_type,
        quality_tier: value.quality_tier,
        cpu_cores: value.cpu_cores,
        memory_gb: value.memory_gb,
        storage_gb: value.storage_gb,
        gpu_count: value.gpu_count,
        estimated_duration_minutes: value.estimated_duration_minutes
      },
      comparisons,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('Price comparison failed:', error);
    res.status(500).json({ error: 'Failed to compare prices' });
  }
});

// Update pricing (admin only)
router.put('/rates', authMiddleware, requireRole(['admin']), async (req, res) => {
  try {
    const { error, value } = updatePricingSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    await pricingEngine.updatePricing(
      value.provider_id,
      value.job_type,
      value.quality_tier,
      value.base_rate,
      value.effective_from
    );

    logger.info(`Pricing updated by admin ${req.user.id}:`, value);

    res.json({
      message: 'Pricing updated successfully',
      provider_id: value.provider_id,
      job_type: value.job_type,
      quality_tier: value.quality_tier,
      new_base_rate: value.base_rate,
      effective_from: value.effective_from || new Date().toISOString()
    });
  } catch (error) {
    logger.error('Pricing update failed:', error);
    res.status(500).json({ error: 'Failed to update pricing' });
  }
});

// Get pricing history for a specific provider/type/tier
router.get('/history', authMiddleware, requireRole(['admin', 'university_admin']), async (req, res) => {
  try {
    const { provider_id, job_type, quality_tier } = req.query;
    
    if (!provider_id || !job_type || !quality_tier) {
      return res.status(400).json({ 
        error: 'provider_id, job_type, and quality_tier are required' 
      });
    }

    // This would query the pricing table for historical data
    // Simplified implementation for now
    res.json({
      message: 'Pricing history endpoint - implementation needed',
      filters: { provider_id, job_type, quality_tier }
    });
  } catch (error) {
    logger.error('Failed to get pricing history:', error);
    res.status(500).json({ error: 'Failed to get pricing history' });
  }
});

// Get demand multipliers (admin only)
router.get('/demand', authMiddleware, requireRole(['admin']), async (req, res) => {
  try {
    const multipliers = [];
    for (const [providerId, multiplier] of pricingEngine.demandMultipliers) {
      multipliers.push({
        provider_id: providerId,
        demand_multiplier: multiplier
      });
    }

    res.json({
      demand_multipliers: multipliers,
      timestamp: new Date().toISOString(),
      surge_threshold: parseFloat(process.env.DEMAND_SURGE_THRESHOLD) || 0.8,
      max_surge_multiplier: parseFloat(process.env.MAX_SURGE_MULTIPLIER) || 5.0
    });
  } catch (error) {
    logger.error('Failed to get demand multipliers:', error);
    res.status(500).json({ error: 'Failed to get demand data' });
  }
});

// Bulk pricing for organizations
router.get('/bulk-rates', authMiddleware, async (req, res) => {
  try {
    // Get bulk rates for user's university or all if admin
    const universityId = req.user.role === 'admin' 
      ? req.query.university_id 
      : req.user.university_id;

    // This would query bulk_rates table
    // Simplified for now
    res.json({
      message: 'Bulk rates endpoint - implementation needed',
      university_id: universityId
    });
  } catch (error) {
    logger.error('Failed to get bulk rates:', error);
    res.status(500).json({ error: 'Failed to get bulk rates' });
  }
});

export default router;