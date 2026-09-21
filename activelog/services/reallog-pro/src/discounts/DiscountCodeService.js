import logger from '../lib/logger.js';
import config from '../config/config.js';

class DiscountCodeService {
  constructor(redis) {
    this.redis = redis;
    this.discountCodes = new Map();
    this.campaigns = new Map();
    this.usage = new Map();
    this.analytics = {
      totalCodes: 0,
      totalRedemptions: 0,
      totalSavings: 0,
      averageDiscount: 0
    };
  }

  async initialize() {
    try {
      await this.loadDiscountCampaigns();
      this.startUsageTracking();
      
      logger.info('Discount Code Service initialized');
    } catch (error) {
      logger.error('Failed to initialize Discount Code Service:', error);
      throw error;
    }
  }

  async loadDiscountCampaigns() {
    // Load default discount campaigns
    this.campaigns.set('welcome_series', {
      name: 'Welcome Series',
      description: 'Welcome discount for new users',
      discountType: 'percentage',
      defaultValue: 15,
      maxUses: 1000,
      enabled: true
    });

    this.campaigns.set('seasonal_sale', {
      name: 'Seasonal Sale',
      description: 'Seasonal promotional discounts',
      discountType: 'percentage',
      defaultValue: 25,
      maxUses: 500,
      enabled: true
    });
  }

  startUsageTracking() {
    logger.info('Discount usage tracking started');
  }

  async createDiscountCode(codeData) {
    try {
      const codeId = `disc_${Date.now()}`;
      const code = codeData.code || this.generateRandomCode();
      
      const discountCode = {
        id: codeId,
        code: code.toUpperCase(),
        name: codeData.name || '',
        description: codeData.description || '',
        type: codeData.type || 'percentage', // percentage, fixed, free_shipping
        value: codeData.value || 10,
        currency: codeData.currency || 'USD',
        minimumOrder: codeData.minimumOrder || 0,
        maximumDiscount: codeData.maximumDiscount || null,
        maxUses: codeData.maxUses || null,
        maxUsesPerUser: codeData.maxUsesPerUser || 1,
        startDate: new Date(codeData.startDate || Date.now()),
        endDate: codeData.endDate ? new Date(codeData.endDate) : null,
        campaign: codeData.campaign || 'general',
        applicableProducts: codeData.applicableProducts || [],
        excludedProducts: codeData.excludedProducts || [],
        userSegments: codeData.userSegments || [],
        status: 'active',
        createdAt: new Date(),
        usageCount: 0,
        totalSavings: 0
      };

      this.discountCodes.set(code.toUpperCase(), discountCode);
      this.analytics.totalCodes++;
      
      await this.redis.set(
        `discount_code:${code.toUpperCase()}`,
        JSON.stringify(discountCode),
        'EX',
        60 * 60 * 24 * 365 // 1 year
      );

      logger.info(`Discount code created: ${code}`);
      return { codeId, discountCode };
    } catch (error) {
      logger.error('Failed to create discount code:', error);
      throw error;
    }
  }

  generateRandomCode(length = 8) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
  }

  async validateDiscountCode(code, orderData = {}) {
    try {
      const discountCode = await this.getDiscountCode(code.toUpperCase());
      if (!discountCode) {
        return { valid: false, error: 'Invalid discount code' };
      }

      // Check if code is active
      if (discountCode.status !== 'active') {
        return { valid: false, error: 'Discount code is not active' };
      }

      // Check start and end dates
      const now = new Date();
      if (discountCode.startDate > now) {
        return { valid: false, error: 'Discount code is not yet valid' };
      }
      if (discountCode.endDate && discountCode.endDate < now) {
        return { valid: false, error: 'Discount code has expired' };
      }

      // Check usage limits
      if (discountCode.maxUses && discountCode.usageCount >= discountCode.maxUses) {
        return { valid: false, error: 'Discount code usage limit reached' };
      }

      // Check minimum order amount
      if (orderData.total && orderData.total < discountCode.minimumOrder) {
        return { 
          valid: false, 
          error: `Minimum order amount is ${discountCode.currency}${discountCode.minimumOrder}` 
        };
      }

      // Check user usage limits (if user provided)
      if (orderData.userId && discountCode.maxUsesPerUser) {
        const userUsage = await this.getUserUsage(code.toUpperCase(), orderData.userId);
        if (userUsage >= discountCode.maxUsesPerUser) {
          return { valid: false, error: 'User usage limit reached for this code' };
        }
      }

      // Calculate discount amount
      const discountAmount = this.calculateDiscount(discountCode, orderData);

      return {
        valid: true,
        discountCode,
        discountAmount,
        message: `Discount of ${discountCode.currency}${discountAmount.toFixed(2)} applied`
      };
    } catch (error) {
      logger.error('Failed to validate discount code:', error);
      return { valid: false, error: 'Error validating discount code' };
    }
  }

  calculateDiscount(discountCode, orderData) {
    let discount = 0;
    const orderTotal = orderData.total || 0;

    switch (discountCode.type) {
      case 'percentage':
        discount = (orderTotal * discountCode.value) / 100;
        break;
      case 'fixed':
        discount = discountCode.value;
        break;
      case 'free_shipping':
        discount = orderData.shippingCost || 0;
        break;
      default:
        discount = 0;
    }

    // Apply maximum discount limit
    if (discountCode.maximumDiscount && discount > discountCode.maximumDiscount) {
      discount = discountCode.maximumDiscount;
    }

    // Ensure discount doesn't exceed order total
    if (discount > orderTotal) {
      discount = orderTotal;
    }

    return Math.max(0, discount);
  }

  async redeemDiscountCode(code, orderData) {
    try {
      const validation = await this.validateDiscountCode(code, orderData);
      if (!validation.valid) {
        return validation;
      }

      const discountCode = validation.discountCode;
      const discountAmount = validation.discountAmount;
      const redemptionId = `redemption_${Date.now()}`;

      // Create redemption record
      const redemption = {
        id: redemptionId,
        code: code.toUpperCase(),
        userId: orderData.userId || null,
        orderId: orderData.orderId || null,
        discountAmount,
        orderTotal: orderData.total || 0,
        timestamp: new Date(),
        metadata: orderData.metadata || {}
      };

      // Update usage statistics
      discountCode.usageCount++;
      discountCode.totalSavings += discountAmount;
      this.discountCodes.set(code.toUpperCase(), discountCode);
      
      // Track usage
      this.usage.set(redemptionId, redemption);
      this.analytics.totalRedemptions++;
      this.analytics.totalSavings += discountAmount;
      
      // Update average discount
      if (this.analytics.totalRedemptions > 0) {
        this.analytics.averageDiscount = this.analytics.totalSavings / this.analytics.totalRedemptions;
      }

      // Store in Redis
      await Promise.all([
        this.redis.set(
          `discount_code:${code.toUpperCase()}`,
          JSON.stringify(discountCode),
          'EX',
          60 * 60 * 24 * 365
        ),
        this.redis.set(
          `discount_redemption:${redemptionId}`,
          JSON.stringify(redemption),
          'EX',
          60 * 60 * 24 * 90 // 90 days
        )
      ]);

      logger.info(`Discount code redeemed: ${code}`, { discountAmount, orderId: orderData.orderId });
      
      return {
        success: true,
        redemptionId,
        discountAmount,
        message: validation.message
      };
    } catch (error) {
      logger.error('Failed to redeem discount code:', error);
      throw error;
    }
  }

  async getDiscountCode(code) {
    if (this.discountCodes.has(code.toUpperCase())) {
      return this.discountCodes.get(code.toUpperCase());
    }

    try {
      const cachedCode = await this.redis.get(`discount_code:${code.toUpperCase()}`);
      if (cachedCode) {
        const discountCode = JSON.parse(cachedCode);
        this.discountCodes.set(code.toUpperCase(), discountCode);
        return discountCode;
      }
    } catch (error) {
      logger.warn(`Failed to load discount code from cache: ${code}`, error.message);
    }

    return null;
  }

  async getUserUsage(code, userId) {
    try {
      const usageKey = `user_discount_usage:${userId}:${code.toUpperCase()}`;
      const usage = await this.redis.get(usageKey);
      return usage ? parseInt(usage) : 0;
    } catch (error) {
      logger.warn('Failed to get user usage:', error);
      return 0;
    }
  }

  async updateDiscountCode(code, updates) {
    try {
      const discountCode = await this.getDiscountCode(code);
      if (!discountCode) {
        throw new Error('Discount code not found');
      }

      const updatedCode = { ...discountCode, ...updates, updatedAt: new Date() };
      this.discountCodes.set(code.toUpperCase(), updatedCode);

      await this.redis.set(
        `discount_code:${code.toUpperCase()}`,
        JSON.stringify(updatedCode),
        'EX',
        60 * 60 * 24 * 365
      );

      logger.info(`Discount code updated: ${code}`);
      return updatedCode;
    } catch (error) {
      logger.error('Failed to update discount code:', error);
      throw error;
    }
  }

  async deleteDiscountCode(code) {
    try {
      this.discountCodes.delete(code.toUpperCase());
      await this.redis.del(`discount_code:${code.toUpperCase()}`);
      
      this.analytics.totalCodes--;
      
      logger.info(`Discount code deleted: ${code}`);
      return { deleted: true };
    } catch (error) {
      logger.error('Failed to delete discount code:', error);
      throw error;
    }
  }

  async getDiscountCodes(filters = {}) {
    let codes = Array.from(this.discountCodes.values());

    if (filters.status) {
      codes = codes.filter(code => code.status === filters.status);
    }

    if (filters.campaign) {
      codes = codes.filter(code => code.campaign === filters.campaign);
    }

    if (filters.type) {
      codes = codes.filter(code => code.type === filters.type);
    }

    return codes;
  }

  async getCodePerformance(code, timeRange = '30d') {
    try {
      const discountCode = await this.getDiscountCode(code);
      if (!discountCode) {
        throw new Error('Discount code not found');
      }

      const performance = {
        ...discountCode,
        conversionRate: discountCode.usageCount > 0 ? (discountCode.usageCount / 100) * 100 : 0, // Mock data
        averageOrderValue: discountCode.totalSavings > 0 ? (discountCode.totalSavings * 5) : 0, // Mock calculation
        customerRetention: Math.random() * 0.3 + 0.2, // 20-50%
        timeRange
      };

      return performance;
    } catch (error) {
      logger.error('Failed to get code performance:', error);
      throw error;
    }
  }

  async getAnalytics() {
    return {
      ...this.analytics,
      activeCodes: Array.from(this.discountCodes.values()).filter(code => code.status === 'active').length,
      campaigns: this.campaigns.size,
      totalUsage: this.usage.size
    };
  }

  setSocketIO(io) {
    this.io = io;
  }

  async shutdown() {
    logger.info('Discount Code Service shutting down');
  }
}

export default DiscountCodeService;