const Maker = require('../models/Maker');
const Order = require('../models/Order');
const logger = require('../config/logger');
const redis = require('../config/redis');

class PricingAggregationService {
  constructor() {
    this.priceUpdateInterval = 300000; // 5 minutes
    this.quoteValidityPeriod = 48 * 60 * 60 * 1000; // 48 hours
    this.rushPriceMultiplier = 1.5;
    this.serviceFeeRate = 0.05; // 5%
  }

  /**
   * Aggregate pricing from multiple makers for an order
   */
  async aggregatePricing(orderId, eligibleMakers) {
    try {
      logger.logBusinessEvent('pricing_aggregation_started', {
        orderId,
        makersCount: eligibleMakers.length
      });

      const quotes = [];
      const pricingPromises = [];

      // Request quotes from all eligible makers
      for (const makerInfo of eligibleMakers) {
        const quotePromise = this.getQuoteFromMaker(orderId, makerInfo);
        pricingPromises.push(quotePromise);
      }

      // Wait for all quotes with timeout
      const results = await Promise.allSettled(pricingPromises);
      
      // Process results
      for (let i = 0; i < results.length; i++) {
        const result = results[i];
        const makerInfo = eligibleMakers[i];

        if (result.status === 'fulfilled' && result.value) {
          quotes.push({
            makerId: makerInfo.makerId,
            makerName: makerInfo.businessName,
            quote: result.value,
            quotedAt: new Date(),
            makerRating: makerInfo.ratings.overall,
            distance: makerInfo.distance,
            estimatedDelivery: result.value.estimatedDelivery
          });
        } else {
          logger.warn(`Failed to get quote from maker ${makerInfo.makerId}:`, result.reason);
        }
      }

      // Sort quotes by various criteria
      const sortedQuotes = this.sortQuotes(quotes);
      
      // Calculate price statistics
      const priceStats = this.calculatePriceStatistics(quotes);
      
      // Generate pricing recommendations
      const recommendations = this.generatePricingRecommendations(sortedQuotes, priceStats);

      const aggregation = {
        orderId,
        totalQuotes: quotes.length,
        quotes: sortedQuotes,
        priceStatistics: priceStats,
        recommendations,
        aggregatedAt: new Date(),
        validUntil: new Date(Date.now() + this.quoteValidityPeriod)
      };

      // Cache the aggregated pricing
      await this.cachePricingAggregation(orderId, aggregation);

      logger.logBusinessEvent('pricing_aggregation_completed', {
        orderId,
        quotesReceived: quotes.length,
        priceRange: `$${priceStats.min} - $${priceStats.max}`,
        averagePrice: `$${priceStats.average}`
      });

      return aggregation;
    } catch (error) {
      logger.error('Error aggregating pricing:', error);
      throw error;
    }
  }

  /**
   * Get quote from a specific maker
   */
  async getQuoteFromMaker(orderId, makerInfo) {
    try {
      // Get order details
      const order = await Order.findOne({ orderId });
      if (!order) {
        throw new Error(`Order ${orderId} not found`);
      }

      // Get maker details
      const maker = await Maker.findOne({ makerId: makerInfo.makerId });
      if (!maker) {
        throw new Error(`Maker ${makerInfo.makerId} not found`);
      }

      // Calculate base quote
      const baseQuote = maker.calculateQuote(order.printSpecs);
      
      // Apply service-specific adjustments
      const adjustedQuote = this.applyPricingAdjustments(baseQuote, order, maker);
      
      // Add shipping costs
      const shippingCost = await this.calculateShipping(maker, order.customer.shippingAddress);
      adjustedQuote.shippingCost = shippingCost;
      adjustedQuote.totalPrice += shippingCost;

      // Cache individual quote
      await this.cacheIndividualQuote(orderId, makerInfo.makerId, adjustedQuote);

      return adjustedQuote;
    } catch (error) {
      logger.error(`Error getting quote from maker ${makerInfo.makerId}:`, error);
      return null;
    }
  }

  /**
   * Apply pricing adjustments based on various factors
   */
  applyPricingAdjustments(baseQuote, order, maker) {
    const adjustedQuote = { ...baseQuote };
    let adjustmentFactors = [];

    // Rush order pricing
    if (order.printSpecs.requirements.urgency === 'rush' && maker.pricing.rushPricing.available) {
      const rushFee = (baseQuote.materialCost + baseQuote.laborCost) * 
                     (maker.pricing.rushPricing.multiplier - 1);
      adjustedQuote.rushFee = rushFee;
      adjustedQuote.totalPrice += rushFee;
      adjustmentFactors.push(`rush_${maker.pricing.rushPricing.multiplier}x`);
    }

    // Quality premium
    if (order.printSpecs.requirements.finishQuality === 'premium') {
      const qualityPremium = adjustedQuote.totalPrice * 0.25; // 25% premium
      adjustedQuote.qualityPremium = qualityPremium;
      adjustedQuote.totalPrice += qualityPremium;
      adjustmentFactors.push('premium_quality');
    }

    // Material premium
    const premiumMaterials = ['Nylon', 'PC', 'Metal', 'Ceramic'];
    if (premiumMaterials.includes(order.printSpecs.material.type)) {
      const materialPremium = adjustedQuote.materialCost * 0.15; // 15% premium
      adjustedQuote.materialPremium = materialPremium;
      adjustedQuote.totalPrice += materialPremium;
      adjustmentFactors.push('premium_material');
    }

    // Complex geometry surcharge
    if (order.printSpecs.requirements.postProcessing.length > 2) {
      const complexityFee = adjustedQuote.totalPrice * 0.1; // 10% surcharge
      adjustedQuote.complexityFee = complexityFee;
      adjustedQuote.totalPrice += complexityFee;
      adjustmentFactors.push('complex_geometry');
    }

    // Volume discount
    const volume = order.printSpecs.dimensions.volume || 0;
    if (volume > 500000) { // >500 cubic cm
      const volumeDiscount = adjustedQuote.totalPrice * 0.05; // 5% discount
      adjustedQuote.volumeDiscount = -volumeDiscount;
      adjustedQuote.totalPrice -= volumeDiscount;
      adjustmentFactors.push('volume_discount');
    }

    // Maker experience premium/discount
    const makerRating = maker.performance.ratings.overall;
    if (makerRating >= 4.5) {
      const experiencePremium = adjustedQuote.totalPrice * 0.05; // 5% premium for top makers
      adjustedQuote.experiencePremium = experiencePremium;
      adjustedQuote.totalPrice += experiencePremium;
      adjustmentFactors.push('expert_premium');
    } else if (makerRating < 3.5) {
      const newMakerDiscount = adjustedQuote.totalPrice * 0.1; // 10% discount for new makers
      adjustedQuote.newMakerDiscount = -newMakerDiscount;
      adjustedQuote.totalPrice -= newMakerDiscount;
      adjustmentFactors.push('new_maker_discount');
    }

    // Distance-based adjustment
    const distance = maker.location.coordinates && order.customer.shippingAddress.coordinates ?
      this.calculateDistance(maker.location.coordinates, order.customer.shippingAddress.coordinates) : 0;
    
    if (distance > 100) { // >100km
      const distanceSurcharge = Math.min(distance * 0.1, adjustedQuote.totalPrice * 0.05);
      adjustedQuote.distanceSurcharge = distanceSurcharge;
      adjustedQuote.totalPrice += distanceSurcharge;
      adjustmentFactors.push('distance_surcharge');
    }

    // Market demand adjustment would be calculated here
    // Note: Simplified for initial implementation
    const demandMultiplier = 1.0; // Static for now
    if (demandMultiplier !== 1.0) {
      const demandAdjustment = adjustedQuote.totalPrice * (demandMultiplier - 1);
      adjustedQuote.demandAdjustment = demandAdjustment;
      adjustedQuote.totalPrice += demandAdjustment;
      adjustmentFactors.push(`market_demand_${demandMultiplier}x`);
    }

    adjustedQuote.adjustmentFactors = adjustmentFactors;
    adjustedQuote.originalPrice = baseQuote.totalPrice;
    adjustedQuote.finalPrice = Math.round(adjustedQuote.totalPrice * 100) / 100;
    adjustedQuote.totalPrice = adjustedQuote.finalPrice;

    return adjustedQuote;
  }

  /**
   * Calculate shipping cost between maker and customer
   */
  async calculateShipping(maker, shippingAddress) {
    try {
      // Find matching shipping zone
      const shippingZone = maker.location.shippingZones.find(zone => 
        zone.regions.includes(shippingAddress.country) ||
        zone.regions.includes(shippingAddress.state) ||
        zone.regions.includes('worldwide')
      );

      if (shippingZone) {
        return shippingZone.baseRate;
      }

      // Calculate distance-based shipping
      const distance = this.calculateDistance(
        maker.location.coordinates,
        shippingAddress.coordinates
      );

      // Base shipping rates by distance
      if (distance < 50) return 5.00;
      if (distance < 100) return 10.00;
      if (distance < 500) return 20.00;
      if (distance < 1000) return 35.00;
      return 50.00; // International or very long distance

    } catch (error) {
      logger.error('Error calculating shipping:', error);
      return 15.00; // Default shipping cost
    }
  }

  /**
   * Sort quotes by various criteria
   */
  sortQuotes(quotes) {
    const sortOptions = {
      byPrice: [...quotes].sort((a, b) => a.quote.totalPrice - b.quote.totalPrice),
      byRating: [...quotes].sort((a, b) => b.makerRating - a.makerRating),
      byDelivery: [...quotes].sort((a, b) => 
        new Date(a.quote.estimatedDelivery) - new Date(b.quote.estimatedDelivery)
      ),
      byDistance: [...quotes].sort((a, b) => a.distance - b.distance),
      byValue: [...quotes].sort((a, b) => {
        // Value score combines price and rating
        const aValue = (a.makerRating / a.quote.totalPrice) * 1000;
        const bValue = (b.makerRating / b.quote.totalPrice) * 1000;
        return bValue - aValue;
      })
    };

    // Default sort is by value (best combination of price and quality)
    return {
      recommended: sortOptions.byValue,
      byPrice: sortOptions.byPrice,
      byRating: sortOptions.byRating,
      byDelivery: sortOptions.byDelivery,
      byDistance: sortOptions.byDistance
    };
  }

  /**
   * Calculate price statistics
   */
  calculatePriceStatistics(quotes) {
    if (quotes.length === 0) {
      return {
        min: 0,
        max: 0,
        average: 0,
        median: 0,
        standardDeviation: 0,
        distribution: {}
      };
    }

    const prices = quotes.map(q => q.quote.totalPrice).sort((a, b) => a - b);
    
    const min = prices[0];
    const max = prices[prices.length - 1];
    const sum = prices.reduce((acc, price) => acc + price, 0);
    const average = sum / prices.length;
    
    const median = prices.length % 2 === 0
      ? (prices[prices.length / 2 - 1] + prices[prices.length / 2]) / 2
      : prices[Math.floor(prices.length / 2)];

    // Calculate standard deviation
    const variance = prices.reduce((acc, price) => acc + Math.pow(price - average, 2), 0) / prices.length;
    const standardDeviation = Math.sqrt(variance);

    // Price distribution
    const priceRanges = {
      budget: prices.filter(p => p <= average - standardDeviation).length,
      standard: prices.filter(p => p > average - standardDeviation && p < average + standardDeviation).length,
      premium: prices.filter(p => p >= average + standardDeviation).length
    };

    return {
      min: Math.round(min * 100) / 100,
      max: Math.round(max * 100) / 100,
      average: Math.round(average * 100) / 100,
      median: Math.round(median * 100) / 100,
      standardDeviation: Math.round(standardDeviation * 100) / 100,
      distribution: priceRanges,
      savingsOpportunity: Math.round((max - min) * 100) / 100
    };
  }

  /**
   * Generate pricing recommendations
   */
  generatePricingRecommendations(sortedQuotes, priceStats) {
    const recommendations = {
      bestValue: null,
      cheapest: null,
      fastest: null,
      highest_quality: null,
      closest: null,
      insights: []
    };

    if (sortedQuotes.recommended.length === 0) {
      return recommendations;
    }

    // Best overall value
    recommendations.bestValue = {
      quote: sortedQuotes.recommended[0],
      reason: 'Best combination of price, quality, and delivery time'
    };

    // Cheapest option
    recommendations.cheapest = {
      quote: sortedQuotes.byPrice[0],
      reason: `Lowest price - save $${(priceStats.max - priceStats.min).toFixed(2)} compared to most expensive`
    };

    // Fastest delivery
    recommendations.fastest = {
      quote: sortedQuotes.byDelivery[0],
      reason: 'Fastest delivery time'
    };

    // Highest quality (best rating)
    recommendations.highest_quality = {
      quote: sortedQuotes.byRating[0],
      reason: `Highest rated maker (${sortedQuotes.byRating[0].makerRating}/5.0 stars)`
    };

    // Closest maker
    recommendations.closest = {
      quote: sortedQuotes.byDistance[0],
      reason: `Closest maker (${sortedQuotes.byDistance[0].distance}km away)`
    };

    // Generate insights
    const insights = [];

    // Price spread insight
    if (priceStats.savingsOpportunity > 20) {
      insights.push({
        type: 'savings',
        message: `You could save up to $${priceStats.savingsOpportunity} by choosing the most affordable option`
      });
    }

    // Quality vs price insight
    const budgetHighQuality = sortedQuotes.recommended.find(q => 
      q.quote.totalPrice <= priceStats.average && q.makerRating >= 4.0
    );
    if (budgetHighQuality) {
      insights.push({
        type: 'value',
        message: 'High-quality option available at below-average price'
      });
    }

    // Rush delivery insight
    const rushQuotes = sortedQuotes.recommended.filter(q => q.quote.rushFee > 0);
    if (rushQuotes.length > 0) {
      insights.push({
        type: 'delivery',
        message: `${rushQuotes.length} makers offer rush delivery for an additional fee`
      });
    }

    // Geographic insight
    const localQuotes = sortedQuotes.recommended.filter(q => q.distance < 50);
    if (localQuotes.length > 0) {
      insights.push({
        type: 'local',
        message: `${localQuotes.length} local makers available within 50km`
      });
    }

    recommendations.insights = insights;

    return recommendations;
  }

  /**
   * Get market demand multiplier for materials
   */
  async getMarketDemandMultiplier(materialType) {
    try {
      // Check cached demand data
      const cacheKey = `market_demand:${materialType}`;
      const cachedData = await redis.get(cacheKey);
      
      if (cachedData) {
        const data = JSON.parse(cachedData);
        return data.multiplier;
      }

      // Calculate current demand based on recent orders
      const recentOrders = await Order.countDocuments({
        'printSpecs.material.type': materialType,
        createdAt: { $gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) } // Last 7 days
      });

      const availableMakers = await Maker.countDocuments({
        'capabilities.materials.type': materialType,
        'capabilities.materials.inStock': true,
        'verification.status': 'verified'
      });

      // Calculate demand/supply ratio
      const demandSupplyRatio = availableMakers > 0 ? recentOrders / availableMakers : 1;
      
      let multiplier = 1.0;
      if (demandSupplyRatio > 2) {
        multiplier = 1.2; // High demand
      } else if (demandSupplyRatio > 1.5) {
        multiplier = 1.1; // Medium-high demand
      } else if (demandSupplyRatio < 0.5) {
        multiplier = 0.95; // Low demand discount
      }

      // Cache the result
      await redis.set(cacheKey, JSON.stringify({
        multiplier,
        calculatedAt: new Date(),
        recentOrders,
        availableMakers
      }), 3600); // Cache for 1 hour

      return multiplier;
    } catch (error) {
      logger.error('Error calculating market demand:', error);
      return 1.0; // Default multiplier
    }
  }

  /**
   * Cache pricing aggregation results
   */
  async cachePricingAggregation(orderId, aggregation) {
    try {
      const cacheKey = `pricing_aggregation:${orderId}`;
      await redis.set(
        cacheKey, 
        JSON.stringify(aggregation), 
        this.quoteValidityPeriod / 1000 // TTL in seconds
      );

      logger.debug(`Cached pricing aggregation for order ${orderId}`);
    } catch (error) {
      logger.error('Error caching pricing aggregation:', error);
    }
  }

  /**
   * Cache individual quote
   */
  async cacheIndividualQuote(orderId, makerId, quote) {
    try {
      const cacheKey = `quote:${orderId}:${makerId}`;
      await redis.set(
        cacheKey,
        JSON.stringify({
          quote,
          cachedAt: new Date()
        }),
        this.quoteValidityPeriod / 1000
      );
    } catch (error) {
      logger.error('Error caching individual quote:', error);
    }
  }

  /**
   * Get cached pricing aggregation
   */
  async getCachedPricingAggregation(orderId) {
    try {
      const cacheKey = `pricing_aggregation:${orderId}`;
      const cached = await redis.get(cacheKey);
      
      if (cached) {
        const data = JSON.parse(cached);
        
        // Check if still valid
        if (new Date(data.validUntil) > new Date()) {
          return data;
        }
      }
      
      return null;
    } catch (error) {
      logger.error('Error getting cached pricing aggregation:', error);
      return null;
    }
  }

  /**
   * Update real-time pricing for active quotes
   */
  async updateRealTimePricing() {
    try {
      // Get all active orders waiting for quotes
      const activeOrders = await Order.find({
        status: { $in: ['quotes_requested', 'quotes_received'] },
        createdAt: { $gte: new Date(Date.now() - 24 * 60 * 60 * 1000) }
      });

      for (const order of activeOrders) {
        // Refresh pricing aggregation
        const makers = order.makers.eligible || [];
        if (makers.length > 0) {
          const updatedAggregation = await this.aggregatePricing(order.orderId, makers);
          
          // Update order with new pricing
          order.pricing.quotes = updatedAggregation.quotes.recommended;
          order.pricing.priceStatistics = updatedAggregation.priceStatistics;
          order.pricing.lastUpdated = new Date();
          
          await order.save();
          
          logger.debug(`Updated pricing for order ${order.orderId}`);
        }
      }

      logger.info(`Updated real-time pricing for ${activeOrders.length} orders`);
    } catch (error) {
      logger.error('Error updating real-time pricing:', error);
    }
  }

  /**
   * Calculate distance between two coordinates (simple implementation)
   */
  calculateDistance(coords1, coords2) {
    const R = 6371; // Earth's radius in km
    const dLat = (coords2.latitude - coords1.latitude) * Math.PI / 180;
    const dLon = (coords2.longitude - coords1.longitude) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(coords1.latitude * Math.PI / 180) * Math.cos(coords2.latitude * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  /**
   * Start periodic price updates
   */
  startPriceUpdateScheduler() {
    setInterval(() => {
      this.updateRealTimePricing();
    }, this.priceUpdateInterval);
    
    logger.info('Started price update scheduler');
  }

  /**
   * Get pricing history for analysis
   */
  async getPricingHistory(materialType, days = 30) {
    try {
      const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
      
      const history = await Order.aggregate([
        {
          $match: {
            'printSpecs.material.type': materialType,
            'pricing.quotes.0': { $exists: true },
            createdAt: { $gte: startDate }
          }
        },
        {
          $unwind: '$pricing.quotes'
        },
        {
          $group: {
            _id: {
              $dateToString: { format: '%Y-%m-%d', date: '$createdAt' }
            },
            averagePrice: { $avg: '$pricing.quotes.quote.totalPrice' },
            minPrice: { $min: '$pricing.quotes.quote.totalPrice' },
            maxPrice: { $max: '$pricing.quotes.quote.totalPrice' },
            orderCount: { $sum: 1 }
          }
        },
        {
          $sort: { _id: 1 }
        }
      ]);

      return history;
    } catch (error) {
      logger.error('Error getting pricing history:', error);
      throw error;
    }
  }
}

module.exports = new PricingAggregationService();