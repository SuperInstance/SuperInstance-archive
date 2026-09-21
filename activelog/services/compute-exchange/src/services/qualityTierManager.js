import { getDb } from '../database/init.js';
import { logger } from '../utils/logger.js';

export class QualityTierManager {
  constructor() {
    this.tierConfigurations = new Map();
    this.tierRequirements = new Map();
  }

  async initialize() {
    try {
      await this.loadTierConfigurations();
      logger.info('Quality tier manager initialized');
    } catch (error) {
      logger.error('Failed to initialize quality tier manager:', error);
      throw error;
    }
  }

  async loadTierConfigurations() {
    // Define quality tier configurations
    const tiers = {
      'basic': {
        name: 'Basic',
        description: 'Standard compute resources with basic SLA',
        max_cpu_cores: 8,
        max_memory_gb: 32,
        max_storage_gb: 100,
        max_gpu_count: 0,
        sla_uptime_percent: 95.0,
        sla_response_time_ms: 30000,
        sla_queue_time_minutes: 60,
        priority_weight: 1.0,
        features: {
          dedicated_resources: false,
          priority_support: false,
          backup_included: false,
          monitoring_included: true,
          failover_enabled: false,
          custom_environment: false
        },
        pricing_multiplier: 1.0,
        availability_zones: ['standard'],
        supported_job_types: ['compute', 'memory'],
        max_job_duration_hours: 24
      },
      'standard': {
        name: 'Standard',
        description: 'Enhanced compute resources with improved SLA',
        max_cpu_cores: 32,
        max_memory_gb: 128,
        max_storage_gb: 1000,
        max_gpu_count: 2,
        sla_uptime_percent: 99.0,
        sla_response_time_ms: 10000,
        sla_queue_time_minutes: 30,
        priority_weight: 1.5,
        features: {
          dedicated_resources: false,
          priority_support: true,
          backup_included: true,
          monitoring_included: true,
          failover_enabled: true,
          custom_environment: true
        },
        pricing_multiplier: 1.2,
        availability_zones: ['standard', 'high_performance'],
        supported_job_types: ['compute', 'gpu', 'memory', 'storage'],
        max_job_duration_hours: 72
      },
      'premium': {
        name: 'Premium',
        description: 'High-performance resources with premium SLA',
        max_cpu_cores: 64,
        max_memory_gb: 256,
        max_storage_gb: 5000,
        max_gpu_count: 4,
        sla_uptime_percent: 99.9,
        sla_response_time_ms: 5000,
        sla_queue_time_minutes: 15,
        priority_weight: 2.0,
        features: {
          dedicated_resources: true,
          priority_support: true,
          backup_included: true,
          monitoring_included: true,
          failover_enabled: true,
          custom_environment: true,
          dedicated_network: true,
          premium_storage: true
        },
        pricing_multiplier: 1.8,
        availability_zones: ['standard', 'high_performance', 'premium'],
        supported_job_types: ['compute', 'gpu', 'memory', 'storage', 'network'],
        max_job_duration_hours: 168 // 1 week
      },
      'enterprise': {
        name: 'Enterprise',
        description: 'Enterprise-grade resources with maximum SLA',
        max_cpu_cores: 128,
        max_memory_gb: 512,
        max_storage_gb: 50000,
        max_gpu_count: 8,
        sla_uptime_percent: 99.99,
        sla_response_time_ms: 2000,
        sla_queue_time_minutes: 5,
        priority_weight: 3.0,
        features: {
          dedicated_resources: true,
          priority_support: true,
          backup_included: true,
          monitoring_included: true,
          failover_enabled: true,
          custom_environment: true,
          dedicated_network: true,
          premium_storage: true,
          dedicated_support: true,
          custom_sla: true,
          compliance_certified: true
        },
        pricing_multiplier: 3.0,
        availability_zones: ['standard', 'high_performance', 'premium', 'enterprise'],
        supported_job_types: ['compute', 'gpu', 'memory', 'storage', 'network'],
        max_job_duration_hours: 720, // 1 month
        min_contract_duration_months: 12
      }
    };

    this.tierConfigurations.clear();
    this.tierRequirements.clear();

    for (const [tierName, config] of Object.entries(tiers)) {
      this.tierConfigurations.set(tierName, config);
      this.tierRequirements.set(tierName, {
        max_cpu_cores: config.max_cpu_cores,
        max_memory_gb: config.max_memory_gb,
        max_storage_gb: config.max_storage_gb,
        max_gpu_count: config.max_gpu_count,
        supported_job_types: config.supported_job_types
      });
    }

    logger.info(`Loaded ${this.tierConfigurations.size} quality tier configurations`);
  }

  validateJobForTier(jobRequest, tierName) {
    const tier = this.tierConfigurations.get(tierName);
    if (!tier) {
      throw new Error(`Invalid quality tier: ${tierName}`);
    }

    const violations = [];

    // Check resource limits
    if (jobRequest.cpu_cores > tier.max_cpu_cores) {
      violations.push(`CPU cores (${jobRequest.cpu_cores}) exceeds ${tierName} tier limit (${tier.max_cpu_cores})`);
    }

    if (jobRequest.memory_gb > tier.max_memory_gb) {
      violations.push(`Memory (${jobRequest.memory_gb}GB) exceeds ${tierName} tier limit (${tier.max_memory_gb}GB)`);
    }

    if (jobRequest.storage_gb > tier.max_storage_gb) {
      violations.push(`Storage (${jobRequest.storage_gb}GB) exceeds ${tierName} tier limit (${tier.max_storage_gb}GB)`);
    }

    if (jobRequest.gpu_count > tier.max_gpu_count) {
      violations.push(`GPU count (${jobRequest.gpu_count}) exceeds ${tierName} tier limit (${tier.max_gpu_count})`);
    }

    // Check job type support
    if (!tier.supported_job_types.includes(jobRequest.job_type)) {
      violations.push(`Job type '${jobRequest.job_type}' is not supported in ${tierName} tier`);
    }

    // Check job duration
    if (jobRequest.estimated_duration_minutes > (tier.max_job_duration_hours * 60)) {
      violations.push(`Estimated duration (${Math.round(jobRequest.estimated_duration_minutes/60)}h) exceeds ${tierName} tier limit (${tier.max_job_duration_hours}h)`);
    }

    return {
      is_valid: violations.length === 0,
      violations: violations,
      tier_config: tier
    };
  }

  async checkUserTierEligibility(userId, requestedTier) {
    const db = getDb();
    
    try {
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

      if (!userInfo) {
        throw new Error('User not found');
      }

      const tier = this.tierConfigurations.get(requestedTier);
      if (!tier) {
        throw new Error(`Invalid tier: ${requestedTier}`);
      }

      const eligibility = {
        is_eligible: true,
        restrictions: [],
        requirements_met: true,
        user_role: userInfo.role,
        current_balance: userInfo.current_balance,
        budget_limit: userInfo.budget_limit
      };

      // Role-based restrictions
      if (requestedTier === 'enterprise' && userInfo.role === 'user') {
        eligibility.is_eligible = false;
        eligibility.restrictions.push('Enterprise tier requires admin or university admin role');
      }

      // Budget checks
      const estimatedHourlyCost = 10 * tier.pricing_multiplier; // Simplified calculation
      if (userInfo.max_cost_per_hour && userInfo.max_cost_per_hour < estimatedHourlyCost) {
        eligibility.restrictions.push(`User cost limit ($${userInfo.max_cost_per_hour}/hour) below estimated tier cost ($${estimatedHourlyCost.toFixed(2)}/hour)`);
      }

      // Balance check (simplified)
      if (userInfo.current_balance < estimatedHourlyCost) {
        eligibility.restrictions.push('Insufficient account balance for tier requirements');
      }

      // Check historical usage patterns
      const usageHistory = await this.getUserUsageHistory(userId);
      if (requestedTier === 'premium' || requestedTier === 'enterprise') {
        if (usageHistory.success_rate < 0.9) {
          eligibility.restrictions.push('Premium/Enterprise tiers require 90%+ job success rate');
        }
        if (usageHistory.total_jobs < 10) {
          eligibility.restrictions.push('Premium/Enterprise tiers require minimum usage history');
        }
      }

      eligibility.is_eligible = eligibility.restrictions.length === 0;
      eligibility.requirements_met = eligibility.is_eligible;

      return eligibility;
    } catch (error) {
      logger.error('Failed to check tier eligibility:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async getUserUsageHistory(userId) {
    const db = getDb();
    
    try {
      const history = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(*) as total_jobs,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_jobs,
            AVG(CASE WHEN actual_duration_minutes > 0 THEN actual_duration_minutes END) as avg_duration,
            COUNT(DISTINCT provider_id) as providers_used
          FROM jobs 
          WHERE user_id = ? 
            AND created_at > datetime('now', '-30 days')
        `, [userId], (err, row) => {
          if (err) reject(err);
          else resolve(row || { total_jobs: 0, successful_jobs: 0, avg_duration: 0, providers_used: 0 });
        });
      });

      return {
        ...history,
        success_rate: history.total_jobs > 0 ? history.successful_jobs / history.total_jobs : 0
      };
    } catch (error) {
      logger.error('Failed to get user usage history:', error);
      return { total_jobs: 0, successful_jobs: 0, success_rate: 0, avg_duration: 0, providers_used: 0 };
    } finally {
      db.close();
    }
  }

  async getRecommendedTier(jobRequest, userId) {
    try {
      const userInfo = await new Promise((resolve, reject) => {
        const db = getDb();
        db.get(`
          SELECT u.*, up.preferred_quality_tier, up.max_cost_per_hour
          FROM users u
          LEFT JOIN user_preferences up ON u.id = up.user_id
          WHERE u.id = ?
        `, [userId], (err, row) => {
          db.close();
          if (err) reject(err);
          else resolve(row);
        });
      });

      // Start with user's preferred tier or standard
      let recommendedTier = userInfo?.preferred_quality_tier || 'standard';
      
      // Check if the preferred tier can handle the job requirements
      let validation = this.validateJobForTier(jobRequest, recommendedTier);
      
      // If preferred tier doesn't work, find the minimum tier that does
      if (!validation.is_valid) {
        const tierOrder = ['basic', 'standard', 'premium', 'enterprise'];
        
        for (const tier of tierOrder) {
          validation = this.validateJobForTier(jobRequest, tier);
          if (validation.is_valid) {
            recommendedTier = tier;
            break;
          }
        }
      }

      // Check user eligibility for the recommended tier
      const eligibility = await this.checkUserTierEligibility(userId, recommendedTier);
      
      // If user isn't eligible for recommended tier, downgrade
      if (!eligibility.is_eligible && recommendedTier !== 'basic') {
        const tierOrder = ['basic', 'standard', 'premium', 'enterprise'];
        const currentIndex = tierOrder.indexOf(recommendedTier);
        
        for (let i = currentIndex - 1; i >= 0; i--) {
          const lowerTier = tierOrder[i];
          const lowerValidation = this.validateJobForTier(jobRequest, lowerTier);
          const lowerEligibility = await this.checkUserTierEligibility(userId, lowerTier);
          
          if (lowerValidation.is_valid && lowerEligibility.is_eligible) {
            recommendedTier = lowerTier;
            validation = lowerValidation;
            break;
          }
        }
      }

      const tierConfig = this.tierConfigurations.get(recommendedTier);
      
      return {
        recommended_tier: recommendedTier,
        tier_config: tierConfig,
        validation: validation,
        eligibility: eligibility,
        alternatives: await this.getAlternativeTiers(jobRequest, userId, recommendedTier)
      };
    } catch (error) {
      logger.error('Failed to get recommended tier:', error);
      throw error;
    }
  }

  async getAlternativeTiers(jobRequest, userId, excludeTier) {
    const alternatives = [];
    const tierOrder = ['basic', 'standard', 'premium', 'enterprise'];
    
    for (const tierName of tierOrder) {
      if (tierName === excludeTier) continue;
      
      try {
        const validation = this.validateJobForTier(jobRequest, tierName);
        const eligibility = await this.checkUserTierEligibility(userId, tierName);
        const tierConfig = this.tierConfigurations.get(tierName);
        
        alternatives.push({
          tier_name: tierName,
          tier_config: tierConfig,
          is_valid: validation.is_valid,
          is_eligible: eligibility.is_eligible,
          violations: validation.violations,
          restrictions: eligibility.restrictions,
          estimated_cost_multiplier: tierConfig.pricing_multiplier
        });
      } catch (error) {
        logger.error(`Failed to evaluate alternative tier ${tierName}:`, error);
      }
    }
    
    return alternatives.sort((a, b) => {
      // Sort by validity and eligibility first, then by cost
      if (a.is_valid && a.is_eligible && !(b.is_valid && b.is_eligible)) return -1;
      if (b.is_valid && b.is_eligible && !(a.is_valid && a.is_eligible)) return 1;
      return a.estimated_cost_multiplier - b.estimated_cost_multiplier;
    });
  }

  getTierConfiguration(tierName) {
    return this.tierConfigurations.get(tierName);
  }

  getAllTiers() {
    return Array.from(this.tierConfigurations.entries()).map(([name, config]) => ({
      tier_name: name,
      ...config
    }));
  }

  compareTiers(tierA, tierB) {
    const configA = this.tierConfigurations.get(tierA);
    const configB = this.tierConfigurations.get(tierB);
    
    if (!configA || !configB) {
      throw new Error('Invalid tier name for comparison');
    }
    
    return {
      tier_a: { name: tierA, ...configA },
      tier_b: { name: tierB, ...configB },
      comparison: {
        cpu_cores: { a: configA.max_cpu_cores, b: configB.max_cpu_cores },
        memory_gb: { a: configA.max_memory_gb, b: configB.max_memory_gb },
        storage_gb: { a: configA.max_storage_gb, b: configB.max_storage_gb },
        gpu_count: { a: configA.max_gpu_count, b: configB.max_gpu_count },
        sla_uptime: { a: configA.sla_uptime_percent, b: configB.sla_uptime_percent },
        response_time: { a: configA.sla_response_time_ms, b: configB.sla_response_time_ms },
        queue_time: { a: configA.sla_queue_time_minutes, b: configB.sla_queue_time_minutes },
        pricing_multiplier: { a: configA.pricing_multiplier, b: configB.pricing_multiplier }
      },
      recommendation: this.getBetterTier(configA, configB, tierA, tierB)
    };
  }

  getBetterTier(configA, configB, tierA, tierB) {
    const scoreA = this.calculateTierScore(configA);
    const scoreB = this.calculateTierScore(configB);
    
    if (scoreA > scoreB) {
      return { better_tier: tierA, reason: 'Higher overall capability and SLA' };
    } else if (scoreB > scoreA) {
      return { better_tier: tierB, reason: 'Higher overall capability and SLA' };
    } else {
      return { better_tier: 'equivalent', reason: 'Tiers have equivalent capabilities' };
    }
  }

  calculateTierScore(config) {
    // Simple scoring algorithm - in reality this would be more sophisticated
    return (
      (config.max_cpu_cores / 128) * 25 +
      (config.max_memory_gb / 512) * 25 +
      (config.sla_uptime_percent / 100) * 30 +
      (1 - (config.sla_response_time_ms / 30000)) * 20
    );
  }

  async getTierUsageStatistics() {
    const db = getDb();
    
    try {
      const stats = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            quality_tier,
            COUNT(*) as job_count,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_jobs,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
            AVG(actual_duration_minutes) as avg_duration_minutes,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(DISTINCT provider_id) as providers_used
          FROM jobs 
          WHERE created_at > datetime('now', '-30 days')
          GROUP BY quality_tier
          ORDER BY job_count DESC
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      return stats.map(stat => ({
        ...stat,
        success_rate: stat.job_count > 0 ? (stat.successful_jobs / stat.job_count * 100).toFixed(2) : '0.00',
        avg_duration_hours: stat.avg_duration_minutes ? (stat.avg_duration_minutes / 60).toFixed(2) : '0.00',
        tier_config: this.tierConfigurations.get(stat.quality_tier)
      }));
    } catch (error) {
      logger.error('Failed to get tier usage statistics:', error);
      throw error;
    } finally {
      db.close();
    }
  }
}