const database = require('../config/database');
const logger = require('../utils/logger');
const { USAGE_RATES } = require('../config/stripe');

class CreditsService {

  // Get user's credit balance
  async getUserCreditBalance(userId) {
    try {
      const currentMonth = new Date();
      currentMonth.setDate(1);
      currentMonth.setHours(0, 0, 0, 0);

      // Get current usage metrics
      const usage = await database('usage_metrics')
        .where('user_id', userId)
        .where('period_start', '>=', currentMonth)
        .first();

      const available = usage?.compute_credits_available || 0;
      const used = usage?.compute_credits_used || 0;
      const total = available + used;

      return {
        available,
        used,
        total,
        lastUpdated: usage?.updated_at || new Date(),
        expiresAt: null // Credits don't expire by default
      };
    } catch (error) {
      logger.error('Failed to get user credit balance:', error);
      throw error;
    }
  }

  // Get credit usage history
  async getCreditUsageHistory(userId, options = {}) {
    try {
      const { page = 1, limit = 20, type, startDate, endDate } = options;
      const offset = (page - 1) * limit;

      let query = database('compute_credit_transactions')
        .where('user_id', userId);

      if (type) {
        query = query.where('transaction_type', type);
      }

      if (startDate && endDate) {
        query = query.whereBetween('created_at', [startDate, endDate]);
      }

      const [transactions, [{ count }]] = await Promise.all([
        query
          .orderBy('created_at', 'desc')
          .limit(limit)
          .offset(offset)
          .select('*'),
        
        query.clone().count('* as count')
      ]);

      return {
        data: transactions,
        total: parseInt(count)
      };
    } catch (error) {
      logger.error('Failed to get credit usage history:', error);
      throw error;
    }
  }

  // Spend credits
  async spendCredits(userId, spendData) {
    const transaction = await database.transaction();
    
    try {
      const { credits, serviceName, description, metadata = {}, operationId } = spendData;

      // Check if user has sufficient credits
      const balance = await this.getUserCreditBalance(userId);
      if (balance.available < credits) {
        throw new Error(`Insufficient credits. Available: ${balance.available}, Required: ${credits}`);
      }

      // Record the transaction
      const creditTransaction = await database('compute_credit_transactions')
        .insert({
          user_id: userId,
          transaction_type: 'usage',
          credits: -credits, // Negative for spending
          service_name: serviceName,
          description: description,
          metadata: JSON.stringify(metadata),
          operation_id: operationId,
          status: 'completed',
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      // Update user's credit balance
      await database('usage_metrics')
        .where('user_id', userId)
        .where('period_start', '>=', new Date(new Date().getFullYear(), new Date().getMonth(), 1))
        .increment('compute_credits_used', credits)
        .decrement('compute_credits_available', credits);

      const newBalance = balance.available - credits;
      
      await transaction.commit();

      logger.info('Credits spent successfully', {
        userId,
        credits,
        serviceName,
        transactionId: creditTransaction.id,
        newBalance
      });

      return {
        ...creditTransaction,
        remaining_balance: newBalance
      };
    } catch (error) {
      await transaction.rollback();
      logger.error('Failed to spend credits:', error);
      throw error;
    }
  }

  // Add credits to user account
  async addCredits(userId, creditData) {
    const transaction = await database.transaction();
    
    try {
      const { credits, reason, description, expiresAt, metadata = {} } = creditData;

      // Record the transaction
      const creditTransaction = await database('compute_credit_transactions')
        .insert({
          user_id: userId,
          transaction_type: 'addition',
          credits: credits, // Positive for adding
          description: description || reason,
          metadata: JSON.stringify(metadata),
          expires_at: expiresAt,
          status: 'completed',
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      // Update user's credit balance
      const currentMonth = new Date();
      currentMonth.setDate(1);
      currentMonth.setHours(0, 0, 0, 0);

      await database('usage_metrics')
        .where('user_id', userId)
        .where('period_start', currentMonth)
        .increment('compute_credits_available', credits)
        .orInsert({
          user_id: userId,
          period_start: currentMonth,
          period_end: new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0),
          compute_credits_available: credits,
          compute_credits_used: 0,
          storage_gb: 0,
          api_calls_current_month: 0,
          active_users: 1,
          bandwidth_gb: 0,
          created_at: new Date(),
          updated_at: new Date()
        });

      const balance = await this.getUserCreditBalance(userId);

      await transaction.commit();

      logger.info('Credits added successfully', {
        userId,
        credits,
        reason,
        transactionId: creditTransaction.id,
        newBalance: balance.available
      });

      return {
        ...creditTransaction,
        new_balance: balance.available
      };
    } catch (error) {
      await transaction.rollback();
      logger.error('Failed to add credits:', error);
      throw error;
    }
  }

  // Get credit pricing packages
  getCreditPricingPackages() {
    return {
      packages: [
        {
          credits: 1000,
          price: USAGE_RATES.computeCredits.ratePer100Credits * 10,
          popular: false,
          savings: 0
        },
        {
          credits: 5000,
          price: Math.round(USAGE_RATES.computeCredits.ratePer100Credits * 50 * 0.85),
          popular: true,
          savings: 15
        },
        {
          credits: 10000,
          price: Math.round(USAGE_RATES.computeCredits.ratePer100Credits * 100 * 0.8),
          popular: false,
          savings: 20
        }
      ],
      bulkDiscounts: USAGE_RATES.computeCredits.bulkDiscounts,
      baseRate: USAGE_RATES.computeCredits.ratePer100Credits,
      currency: 'usd'
    };
  }

  // Get service rates for different operations
  getServiceRates() {
    return [
      {
        name: 'ai_generation',
        displayName: 'AI Content Generation',
        category: 'AI Services',
        rateType: 'per_request',
        baseRate: 10,
        tiers: [
          { requests: 0, rate: 10 },
          { requests: 1000, rate: 8 },
          { requests: 5000, rate: 6 }
        ],
        description: 'Generate text, images, or other AI content',
        examples: ['Blog post generation: ~50 credits', 'Image creation: ~25 credits']
      },
      {
        name: 'data_processing',
        displayName: 'Data Processing',
        category: 'Compute Services',
        rateType: 'per_gb',
        baseRate: 5,
        tiers: [
          { gb: 0, rate: 5 },
          { gb: 100, rate: 4 },
          { gb: 1000, rate: 3 }
        ],
        description: 'Process large datasets',
        examples: ['1GB CSV processing: ~5 credits', '10GB log analysis: ~40 credits']
      },
      {
        name: 'api_calls',
        displayName: 'External API Calls',
        category: 'Integration Services',
        rateType: 'per_call',
        baseRate: 1,
        tiers: [
          { calls: 0, rate: 1 },
          { calls: 10000, rate: 0.8 },
          { calls: 100000, rate: 0.6 }
        ],
        description: 'Make calls to external APIs',
        examples: ['Weather API call: ~1 credit', 'Payment processing: ~2 credits']
      }
    ];
  }

  // Estimate credits needed for an operation
  async estimateCreditsNeeded(serviceName, operationType, parameters = {}) {
    try {
      const serviceRates = this.getServiceRates();
      const service = serviceRates.find(s => s.name === serviceName);

      if (!service) {
        throw new Error('Unknown service');
      }

      let estimatedCredits = service.baseRate;
      let confidence = 'medium';
      let factors = [];

      // Service-specific calculations
      switch (serviceName) {
        case 'ai_generation':
          if (parameters.length) {
            estimatedCredits = Math.ceil(parameters.length / 100) * service.baseRate;
            factors.push(`Content length: ${parameters.length} characters`);
          }
          if (parameters.complexity === 'high') {
            estimatedCredits *= 1.5;
            factors.push('High complexity multiplier: 1.5x');
          }
          break;

        case 'data_processing':
          if (parameters.dataSizeGB) {
            estimatedCredits = Math.ceil(parameters.dataSizeGB) * service.baseRate;
            factors.push(`Data size: ${parameters.dataSizeGB}GB`);
          }
          if (parameters.processingType === 'ml') {
            estimatedCredits *= 2;
            factors.push('ML processing multiplier: 2x');
          }
          break;

        case 'api_calls':
          if (parameters.callCount) {
            estimatedCredits = parameters.callCount * service.baseRate;
            factors.push(`API calls: ${parameters.callCount}`);
          }
          break;

        default:
          confidence = 'low';
          factors.push('Using base rate for unknown operation');
      }

      // Apply tier discounts if applicable
      const tierDiscount = this.calculateTierDiscount(service, parameters);
      if (tierDiscount < 1) {
        estimatedCredits = Math.round(estimatedCredits * tierDiscount);
        factors.push(`Tier discount: ${((1 - tierDiscount) * 100).toFixed(1)}%`);
      }

      return {
        credits: Math.max(1, Math.round(estimatedCredits)),
        breakdown: {
          baseRate: service.baseRate,
          quantity: this.getQuantityFromParameters(serviceName, parameters),
          multipliers: factors,
          tierDiscount
        },
        confidence,
        factors
      };
    } catch (error) {
      logger.error('Failed to estimate credits:', error);
      throw error;
    }
  }

  // Calculate tier discount based on usage volume
  calculateTierDiscount(service, parameters) {
    if (!service.tiers || service.tiers.length === 0) {
      return 1; // No discount
    }

    let quantity = this.getQuantityFromParameters(service.name, parameters);
    
    // Find applicable tier
    let applicableTier = service.tiers[0];
    for (const tier of service.tiers) {
      const tierThreshold = tier.requests || tier.gb || tier.calls || 0;
      if (quantity >= tierThreshold) {
        applicableTier = tier;
      }
    }

    return applicableTier.rate / service.baseRate;
  }

  // Extract quantity from parameters based on service type
  getQuantityFromParameters(serviceName, parameters) {
    switch (serviceName) {
      case 'ai_generation':
        return parameters.requestCount || 1;
      case 'data_processing':
        return parameters.dataSizeGB || 1;
      case 'api_calls':
        return parameters.callCount || 1;
      default:
        return 1;
    }
  }

  // Get credit analytics for user
  async getCreditAnalytics(userId, options = {}) {
    try {
      const { period = '30d', groupBy = 'service' } = options;
      const dateFilter = this.parsePeriod(period);

      // Get usage statistics
      const [totalUsed, totalPurchased, serviceBreakdown, dailyUsage] = await Promise.all([
        database('compute_credit_transactions')
          .where('user_id', userId)
          .where('transaction_type', 'usage')
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .sum('credits as total')
          .first(),

        database('compute_credit_transactions')
          .where('user_id', userId)
          .where('transaction_type', 'purchase')
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .sum('credits as total')
          .first(),

        database('compute_credit_transactions')
          .where('user_id', userId)
          .where('transaction_type', 'usage')
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .groupBy('service_name')
          .select('service_name')
          .sum('credits as total')
          .orderBy('total', 'desc'),

        this.getDailyCreditUsage(userId, dateFilter)
      ]);

      const totalCreditsUsed = Math.abs(parseInt(totalUsed.total) || 0);
      const totalCreditsPurchased = parseInt(totalPurchased.total) || 0;
      const efficiency = totalCreditsPurchased > 0 ? (totalCreditsUsed / totalCreditsPurchased) * 100 : 0;

      return {
        period: dateFilter,
        totalUsed: totalCreditsUsed,
        totalPurchased: totalCreditsPurchased,
        efficiency: parseFloat(efficiency.toFixed(2)),
        topServices: serviceBreakdown.slice(0, 5).map(service => ({
          name: service.service_name,
          credits: Math.abs(service.total),
          percentage: totalCreditsUsed > 0 ? (Math.abs(service.total) / totalCreditsUsed) * 100 : 0
        })),
        dailyUsage,
        projectedUsage: this.calculateProjectedUsage(dailyUsage),
        recommendations: this.generateUsageRecommendations(serviceBreakdown, efficiency)
      };
    } catch (error) {
      logger.error('Failed to get credit analytics:', error);
      throw error;
    }
  }

  // Parse period string to date range
  parsePeriod(period) {
    const end = new Date();
    const start = new Date();

    if (period === '7d') {
      start.setDate(start.getDate() - 7);
    } else if (period === '30d') {
      start.setDate(start.getDate() - 30);
    } else if (period === '90d') {
      start.setDate(start.getDate() - 90);
    }

    return { start, end, period };
  }

  // Get daily credit usage
  async getDailyCreditUsage(userId, dateFilter) {
    try {
      return await database('compute_credit_transactions')
        .where('user_id', userId)
        .where('transaction_type', 'usage')
        .whereBetween('created_at', [dateFilter.start, dateFilter.end])
        .select(database.raw('DATE(created_at) as date'))
        .sum('credits as credits')
        .groupBy(database.raw('DATE(created_at)'))
        .orderBy('date')
        .then(results => results.map(row => ({
          date: row.date,
          credits: Math.abs(row.credits)
        })));
    } catch (error) {
      logger.error('Failed to get daily credit usage:', error);
      return [];
    }
  }

  // Calculate projected monthly usage
  calculateProjectedUsage(dailyUsage) {
    if (!dailyUsage.length) return 0;

    const totalDays = dailyUsage.length;
    const totalUsage = dailyUsage.reduce((sum, day) => sum + day.credits, 0);
    const avgDailyUsage = totalUsage / totalDays;
    
    return Math.round(avgDailyUsage * 30); // Project for 30 days
  }

  // Generate usage recommendations
  generateUsageRecommendations(serviceBreakdown, efficiency) {
    const recommendations = [];

    if (efficiency < 50) {
      recommendations.push({
        type: 'efficiency',
        message: 'You\'re using less than 50% of purchased credits. Consider a smaller package.',
        priority: 'medium'
      });
    }

    if (efficiency > 90) {
      recommendations.push({
        type: 'capacity',
        message: 'You\'re using most of your credits. Consider purchasing more to avoid running out.',
        priority: 'high'
      });
    }

    // Service-specific recommendations
    const topService = serviceBreakdown[0];
    if (topService && topService.total > 1000) {
      recommendations.push({
        type: 'optimization',
        message: `Consider optimizing ${topService.service_name} usage to reduce credit consumption.`,
        priority: 'low'
      });
    }

    return recommendations;
  }

  // Set credit alert
  async setCreditAlert(userId, alertConfig) {
    try {
      const existing = await database('credit_alerts')
        .where('user_id', userId)
        .where('alert_type', alertConfig.type)
        .first();

      if (existing) {
        return await database('credit_alerts')
          .where('id', existing.id)
          .update({
            threshold: alertConfig.threshold,
            enabled: alertConfig.enabled,
            notification_method: alertConfig.notificationMethod,
            updated_at: new Date()
          })
          .returning('*')
          .first();
      } else {
        return await database('credit_alerts')
          .insert({
            user_id: userId,
            alert_type: alertConfig.type,
            threshold: alertConfig.threshold,
            enabled: alertConfig.enabled,
            notification_method: alertConfig.notificationMethod,
            created_at: new Date(),
            updated_at: new Date()
          })
          .returning('*')
          .first();
      }
    } catch (error) {
      logger.error('Failed to set credit alert:', error);
      throw error;
    }
  }

  // Get credit alerts
  async getCreditAlerts(userId) {
    try {
      return await database('credit_alerts')
        .where('user_id', userId)
        .orderBy('created_at', 'desc')
        .select('*');
    } catch (error) {
      logger.error('Failed to get credit alerts:', error);
      throw error;
    }
  }

  // Transfer credits between users
  async transferCredits(fromUserId, toUserId, credits, message = null) {
    const transaction = await database.transaction();
    
    try {
      // Check if sender has sufficient credits
      const senderBalance = await this.getUserCreditBalance(fromUserId);
      if (senderBalance.available < credits) {
        throw new Error('Insufficient credits for transfer');
      }

      // Check if recipient exists
      const recipient = await database('users').where('id', toUserId).first();
      if (!recipient) {
        throw new Error('Recipient user not found');
      }

      // Create transfer record
      const transfer = await database('credit_transfers')
        .insert({
          sender_user_id: fromUserId,
          recipient_user_id: toUserId,
          credits: credits,
          message: message,
          status: 'completed',
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      // Deduct from sender
      await this.spendCredits(fromUserId, {
        credits,
        serviceName: 'transfer',
        description: `Transfer to user ${toUserId}`,
        metadata: { transferId: transfer.id, recipientUserId: toUserId }
      });

      // Add to recipient
      await this.addCredits(toUserId, {
        credits,
        reason: 'transfer_received',
        description: `Transfer from user ${fromUserId}`,
        metadata: { transferId: transfer.id, senderUserId: fromUserId }
      });

      await transaction.commit();

      logger.audit('Credits transferred', {
        fromUserId,
        toUserId,
        credits,
        transferId: transfer.id
      });

      return transfer;
    } catch (error) {
      await transaction.rollback();
      logger.error('Failed to transfer credits:', error);
      throw error;
    }
  }

  // Get credit transfer history
  async getCreditTransferHistory(userId, options = {}) {
    try {
      const { page = 1, limit = 20, type = 'all' } = options;
      const offset = (page - 1) * limit;

      let query = database('credit_transfers');

      if (type === 'sent') {
        query = query.where('sender_user_id', userId);
      } else if (type === 'received') {
        query = query.where('recipient_user_id', userId);
      } else {
        query = query.where(function() {
          this.where('sender_user_id', userId).orWhere('recipient_user_id', userId);
        });
      }

      const [transfers, [{ count }]] = await Promise.all([
        query
          .orderBy('created_at', 'desc')
          .limit(limit)
          .offset(offset)
          .select('*'),
        
        query.clone().count('* as count')
      ]);

      return {
        data: transfers,
        total: parseInt(count)
      };
    } catch (error) {
      logger.error('Failed to get transfer history:', error);
      throw error;
    }
  }
}

module.exports = CreditsService;