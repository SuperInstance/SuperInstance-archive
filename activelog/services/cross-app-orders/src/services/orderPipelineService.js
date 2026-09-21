const Order = require('../models/Order');
const Maker = require('../models/Maker');
const logger = require('../config/logger');
const redis = require('../config/redis');
const { calculateDistance, isPointWithinRadius } = require('geolib');

class OrderPipelineService {
  constructor() {
    this.processingQueue = [];
    this.isProcessing = false;
  }

  /**
   * Main entry point for processing DMLog orders
   * Receives order data from DMLog and initiates the pipeline
   */
  async processDMLogOrder(dmlogOrderData) {
    try {
      logger.logBusinessEvent('dmlog_order_received', {
        dmlogOrderId: dmlogOrderData.orderId,
        customerId: dmlogOrderData.customer.userId
      });

      // Create order record in our system
      const order = await this.createOrder(dmlogOrderData);
      
      // Add to processing queue
      this.addToQueue(order);
      
      // Start processing if not already running
      if (!this.isProcessing) {
        this.processQueue();
      }

      return {
        success: true,
        orderId: order.orderId,
        status: order.status,
        estimatedProcessingTime: '5-15 minutes'
      };
    } catch (error) {
      logger.error('Error processing DMLog order:', error);
      throw error;
    }
  }

  /**
   * Create order record from DMLog data
   */
  async createOrder(dmlogOrderData) {
    try {
      const orderData = {
        dmlogOrderId: dmlogOrderData.orderId,
        status: 'pending',
        
        customer: {
          dmlogUserId: dmlogOrderData.customer.userId,
          email: dmlogOrderData.customer.email,
          name: dmlogOrderData.customer.name,
          shippingAddress: {
            street: dmlogOrderData.shipping.address.street,
            city: dmlogOrderData.shipping.address.city,
            state: dmlogOrderData.shipping.address.state,
            country: dmlogOrderData.shipping.address.country,
            postalCode: dmlogOrderData.shipping.address.postalCode,
            coordinates: dmlogOrderData.shipping.address.coordinates
          }
        },
        
        printSpecs: {
          model: {
            filename: dmlogOrderData.model.filename,
            fileUrl: dmlogOrderData.model.fileUrl,
            fileSize: dmlogOrderData.model.fileSize,
            fileHash: dmlogOrderData.model.fileHash,
            format: dmlogOrderData.model.format
          },
          
          material: {
            type: dmlogOrderData.specifications.material,
            color: dmlogOrderData.specifications.color,
            brand: dmlogOrderData.specifications.brand || 'Generic'
          },
          
          quality: {
            layerHeight: dmlogOrderData.specifications.layerHeight || 0.2,
            infill: dmlogOrderData.specifications.infill || 20,
            supports: dmlogOrderData.specifications.supports || false,
            resolution: dmlogOrderData.specifications.quality || 'normal'
          },
          
          dimensions: dmlogOrderData.dimensions,
          estimates: dmlogOrderData.estimates,
          
          requirements: {
            postProcessing: dmlogOrderData.requirements.postProcessing || [],
            finishQuality: dmlogOrderData.requirements.finishQuality || 'standard',
            urgency: dmlogOrderData.requirements.urgency || 'standard',
            specialInstructions: dmlogOrderData.requirements.notes
          }
        },
        
        metadata: {
          source: dmlogOrderData.source || 'dmlog_web',
          priority: this.determinePriority(dmlogOrderData),
          customerNotes: dmlogOrderData.customerNotes
        }
      };

      const order = new Order(orderData);
      await order.save();
      
      logger.logBusinessEvent('order_created', {
        orderId: order.orderId,
        dmlogOrderId: order.dmlogOrderId,
        material: order.printSpecs.material.type,
        urgency: order.printSpecs.requirements.urgency
      });

      return order;
    } catch (error) {
      logger.error('Error creating order:', error);
      throw error;
    }
  }

  /**
   * Add order to processing queue
   */
  addToQueue(order) {
    // Priority queue - rush orders first
    if (order.isUrgent) {
      this.processingQueue.unshift(order);
    } else {
      this.processingQueue.push(order);
    }

    logger.debug(`Order ${order.orderId} added to processing queue`, {
      queueLength: this.processingQueue.length,
      priority: order.metadata.priority
    });
  }

  /**
   * Process orders in the queue
   */
  async processQueue() {
    if (this.isProcessing || this.processingQueue.length === 0) {
      return;
    }

    this.isProcessing = true;
    logger.info('Starting order processing queue');

    while (this.processingQueue.length > 0) {
      const order = this.processingQueue.shift();
      
      try {
        await this.processOrderPipeline(order);
      } catch (error) {
        logger.error(`Error processing order ${order.orderId}:`, error);
        await this.handleOrderError(order, error);
      }
    }

    this.isProcessing = false;
    logger.info('Order processing queue completed');
  }

  /**
   * Main order processing pipeline
   */
  async processOrderPipeline(order) {
    logger.logBusinessEvent('order_processing_started', {
      orderId: order.orderId,
      status: order.status
    });

    try {
      // Step 1: Analyze order requirements
      await this.analyzeOrder(order);
      
      // Step 2: Find eligible makers
      await this.findEligibleMakers(order);
      
      // Step 3: Request quotes from makers
      await this.requestQuotes(order);
      
      // Step 4: Notify customer about available quotes
      await this.notifyCustomerQuotesReady(order);

    } catch (error) {
      logger.error(`Pipeline error for order ${order.orderId}:`, error);
      throw error;
    }
  }

  /**
   * Step 1: Analyze order requirements and validate feasibility
   */
  async analyzeOrder(order) {
    await order.updateStatus('analyzing', 'Analyzing print requirements and specifications');
    
    try {
      // Validate print specifications
      const analysis = await this.validatePrintSpecs(order.printSpecs);
      
      if (!analysis.feasible) {
        throw new Error(`Order not feasible: ${analysis.issues.join(', ')}`);
      }

      // Estimate complexity and time requirements
      const complexity = this.calculateComplexity(order.printSpecs);
      
      // Update order with analysis results
      order.metadata.analysis = {
        feasible: true,
        complexity: complexity.level,
        estimatedMakers: complexity.estimatedMakers,
        analysisNotes: analysis.notes,
        analyzedAt: new Date()
      };

      await order.save();
      
      logger.logBusinessEvent('order_analyzed', {
        orderId: order.orderId,
        feasible: true,
        complexity: complexity.level
      });

    } catch (error) {
      logger.error(`Analysis failed for order ${order.orderId}:`, error);
      await order.updateStatus('failed', `Analysis failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Step 2: Find eligible makers based on requirements
   */
  async findEligibleMakers(order) {
    await order.updateStatus('matching_makers', 'Finding suitable makers');
    
    try {
      const eligibleMakers = await this.matchMakers(order);
      
      if (eligibleMakers.length === 0) {
        throw new Error('No eligible makers found for this order');
      }

      // Store eligible makers in order
      order.makers.eligible = eligibleMakers;
      await order.save();

      logger.logBusinessEvent('makers_matched', {
        orderId: order.orderId,
        makersFound: eligibleMakers.length,
        averageDistance: this.calculateAverageDistance(eligibleMakers)
      });

    } catch (error) {
      logger.error(`Maker matching failed for order ${order.orderId}:`, error);
      await order.updateStatus('failed', `Maker matching failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Step 3: Request quotes from eligible makers
   */
  async requestQuotes(order) {
    await order.updateStatus('quotes_requested', 'Requesting quotes from makers');
    
    try {
      const quoteRequests = [];
      const maxQuoteRequests = order.isUrgent ? 10 : 5;
      
      // Select top makers for quote requests
      const selectedMakers = order.makers.eligible
        .sort((a, b) => {
          // Sort by rating and proximity
          const aScore = a.ratings.overall * 0.7 + (100 - a.distance) * 0.3;
          const bScore = b.ratings.overall * 0.7 + (100 - b.distance) * 0.3;
          return bScore - aScore;
        })
        .slice(0, maxQuoteRequests);

      // Send quote requests to selected makers
      for (const makerInfo of selectedMakers) {
        const quoteRequest = this.sendQuoteRequest(order, makerInfo);
        quoteRequests.push(quoteRequest);
      }

      // Wait for initial responses (with timeout)
      const timeout = order.isUrgent ? 30000 : 60000; // 30s for urgent, 60s for normal
      await Promise.allSettled(quoteRequests);

      // Check if we have any quotes
      const quotes = await this.getQuotesForOrder(order.orderId);
      
      if (quotes.length === 0) {
        // No immediate quotes, but makers have been notified
        // Set up polling for delayed responses
        await this.setupQuotePolling(order);
      } else {
        await order.updateStatus('quotes_received', `Received ${quotes.length} quotes`);
      }

    } catch (error) {
      logger.error(`Quote request failed for order ${order.orderId}:`, error);
      await order.updateStatus('failed', `Quote request failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Step 4: Notify customer that quotes are available
   */
  async notifyCustomerQuotesReady(order) {
    try {
      // Prepare quote summary for customer
      const quotes = order.pricing.quotes || [];
      const quoteSummary = {
        orderId: order.orderId,
        totalQuotes: quotes.length,
        priceRange: quotes.length > 0 ? {
          min: Math.min(...quotes.map(q => q.quote.totalPrice)),
          max: Math.max(...quotes.map(q => q.quote.totalPrice))
        } : null,
        averageDelivery: this.calculateAverageDelivery(quotes),
        topQuotes: quotes
          .sort((a, b) => a.quote.totalPrice - b.quote.totalPrice)
          .slice(0, 3)
      };

      // Send notification to DMLog
      await this.notifyDMLog('quotes_ready', {
        orderId: order.dmlogOrderId,
        quotes: quoteSummary
      });

      // Add communication record
      await order.addCommunication(
        'system',
        order.customer.dmlogUserId,
        'email',
        'Quotes Ready for Your 3D Print Order',
        `We've received ${quotes.length} quotes for your order. Please review and select your preferred maker.`
      );

    } catch (error) {
      logger.error(`Failed to notify customer for order ${order.orderId}:`, error);
      // Don't throw error as this is not critical for the pipeline
    }
  }

  /**
   * Match makers based on order requirements
   */
  async matchMakers(order) {
    const { printSpecs, customer } = order;
    const customerCoords = customer.shippingAddress.coordinates;
    
    try {
      // Find makers by capability
      const capableMakers = await Maker.findByCapability(
        printSpecs.material.type,
        null // Don't filter by technology for now
      );

      const eligibleMakers = [];
      const maxDistance = order.isUrgent ? 100 : 500; // km radius

      for (const maker of capableMakers) {
        // Check if maker can handle the order
        if (!maker.canHandleOrder(printSpecs)) {
          continue;
        }

        // Calculate distance
        const distance = calculateDistance(
          customerCoords,
          maker.location.coordinates,
          { unit: 'km' }
        );

        if (distance > maxDistance) {
          continue;
        }

        // Check availability
        if (!maker.isAvailable) {
          continue;
        }

        // Add to eligible makers list
        eligibleMakers.push({
          makerId: maker.makerId,
          makerUserId: maker.makerlogUserId,
          businessName: maker.business.name,
          location: {
            city: maker.location.address.city,
            state: maker.location.address.state,
            country: maker.location.address.country,
            coordinates: maker.location.coordinates
          },
          distance: Math.round(distance * 100) / 100,
          capabilities: {
            materials: maker.capabilities.materials.map(m => m.type),
            printers: maker.capabilities.technologies.map(t => t.type),
            maxDimensions: maker.capabilities.printSpecs.maxDimensions,
            postProcessing: maker.capabilities.postProcessing
              .filter(p => p.available)
              .map(p => p.service)
          },
          ratings: {
            overall: maker.performance.ratings.overall,
            quality: maker.performance.ratings.quality,
            delivery: maker.performance.ratings.delivery,
            communication: maker.performance.ratings.communication,
            totalReviews: maker.performance.ratings.totalReviews
          },
          availability: {
            earliestStart: maker.capacity.availability.earliestAvailable || new Date(),
            estimatedCompletion: maker.calculateDeliveryDate(printSpecs),
            queuePosition: maker.capacity.availability.queueLength
          }
        });
      }

      return eligibleMakers.sort((a, b) => {
        // Sort by combination of rating and proximity
        const aScore = (a.ratings.overall * 0.6) + ((100 - a.distance) * 0.4);
        const bScore = (b.ratings.overall * 0.6) + ((100 - b.distance) * 0.4);
        return bScore - aScore;
      });

    } catch (error) {
      logger.error('Error matching makers:', error);
      throw error;
    }
  }

  /**
   * Send quote request to a maker
   */
  async sendQuoteRequest(order, makerInfo) {
    try {
      const quoteRequest = {
        orderId: order.orderId,
        dmlogOrderId: order.dmlogOrderId,
        requestId: `QR-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
        makerId: makerInfo.makerId,
        printSpecs: order.printSpecs,
        deliveryAddress: order.customer.shippingAddress,
        urgency: order.printSpecs.requirements.urgency,
        requestedAt: new Date(),
        expiresAt: new Date(Date.now() + (order.isUrgent ? 2 : 24) * 60 * 60 * 1000)
      };

      // Store quote request in Redis for tracking
      await redis.set(
        `quote_request:${quoteRequest.requestId}`,
        JSON.stringify(quoteRequest),
        3600 * 24 // 24 hour TTL
      );

      // Send notification to MakerLog
      await this.notifyMakerLog('quote_request', quoteRequest);

      logger.logBusinessEvent('quote_requested', {
        orderId: order.orderId,
        makerId: makerInfo.makerId,
        requestId: quoteRequest.requestId
      });

      return quoteRequest;
    } catch (error) {
      logger.error(`Error sending quote request to maker ${makerInfo.makerId}:`, error);
      throw error;
    }
  }

  /**
   * Send notification to DMLog
   */
  async notifyDMLog(eventType, data) {
    try {
      const notification = {
        type: eventType,
        timestamp: new Date().toISOString(),
        data
      };

      // In a real implementation, this would call DMLog's API
      // For now, we'll use Redis pub/sub or HTTP webhook
      await redis.publish('dmlog_notifications', notification);

      logger.debug(`DMLog notification sent: ${eventType}`, { data });
    } catch (error) {
      logger.error(`Failed to notify DMLog: ${eventType}`, error);
      throw error;
    }
  }

  /**
   * Send notification to MakerLog
   */
  async notifyMakerLog(eventType, data) {
    try {
      const notification = {
        type: eventType,
        timestamp: new Date().toISOString(),
        data
      };

      // In a real implementation, this would call MakerLog's API
      // For now, we'll use Redis pub/sub or HTTP webhook
      await redis.publish('makerlog_notifications', notification);

      logger.debug(`MakerLog notification sent: ${eventType}`, { data });
    } catch (error) {
      logger.error(`Failed to notify MakerLog: ${eventType}`, error);
      throw error;
    }
  }

  /**
   * Validate print specifications for feasibility
   */
  async validatePrintSpecs(printSpecs) {
    const issues = [];
    const notes = [];

    try {
      // Check material availability
      const materialAvailable = await this.checkMaterialAvailability(printSpecs.material.type);
      if (!materialAvailable) {
        issues.push(`Material ${printSpecs.material.type} not available`);
      }

      // Check dimensions
      if (!printSpecs.dimensions || !printSpecs.dimensions.volume) {
        issues.push('Missing or invalid dimensions');
      }

      // Check file format
      const supportedFormats = ['stl', 'obj', '3mf', 'ply'];
      if (!supportedFormats.includes(printSpecs.model.format)) {
        issues.push(`Unsupported file format: ${printSpecs.model.format}`);
      }

      // Check print quality settings
      if (printSpecs.quality.layerHeight < 0.1 || printSpecs.quality.layerHeight > 0.4) {
        issues.push('Layer height out of supported range (0.1-0.4mm)');
      }

      // Add recommendations
      if (printSpecs.requirements.urgency === 'rush') {
        notes.push('Rush orders may have limited maker availability');
      }

      return {
        feasible: issues.length === 0,
        issues,
        notes
      };
    } catch (error) {
      logger.error('Error validating print specs:', error);
      throw error;
    }
  }

  /**
   * Calculate order complexity
   */
  calculateComplexity(printSpecs) {
    let complexityScore = 0;
    let factors = [];

    // Volume factor
    const volume = printSpecs.dimensions.volume || 0;
    if (volume > 100000) { // >100 cubic cm
      complexityScore += 2;
      factors.push('large_volume');
    }

    // Material complexity
    const complexMaterials = ['TPU', 'Nylon', 'PC', 'Metal'];
    if (complexMaterials.includes(printSpecs.material.type)) {
      complexityScore += 3;
      factors.push('complex_material');
    }

    // Quality requirements
    if (printSpecs.quality.layerHeight < 0.15) {
      complexityScore += 2;
      factors.push('high_resolution');
    }

    if (printSpecs.quality.infill > 80) {
      complexityScore += 1;
      factors.push('high_infill');
    }

    // Post-processing requirements
    if (printSpecs.requirements.postProcessing.length > 2) {
      complexityScore += 2;
      factors.push('extensive_post_processing');
    }

    // Determine complexity level
    let level;
    let estimatedMakers;
    
    if (complexityScore <= 2) {
      level = 'simple';
      estimatedMakers = 50;
    } else if (complexityScore <= 5) {
      level = 'moderate';
      estimatedMakers = 20;
    } else {
      level = 'complex';
      estimatedMakers = 5;
    }

    return {
      level,
      score: complexityScore,
      factors,
      estimatedMakers
    };
  }

  /**
   * Check if material is available from makers
   */
  async checkMaterialAvailability(materialType) {
    try {
      const count = await Maker.countDocuments({
        'capabilities.materials.type': materialType,
        'capabilities.materials.inStock': true,
        'verification.status': 'verified',
        'capacity.availability.acceptingOrders': true
      });
      
      return count > 0;
    } catch (error) {
      logger.error('Error checking material availability:', error);
      return false;
    }
  }

  /**
   * Determine order priority based on various factors
   */
  determinePriority(dmlogOrderData) {
    if (dmlogOrderData.requirements?.urgency === 'rush') {
      return 'high';
    }
    
    if (dmlogOrderData.customer?.premium) {
      return 'high';
    }
    
    return 'normal';
  }

  /**
   * Calculate average distance of eligible makers
   */
  calculateAverageDistance(makers) {
    if (makers.length === 0) return 0;
    const total = makers.reduce((sum, maker) => sum + maker.distance, 0);
    return Math.round((total / makers.length) * 100) / 100;
  }

  /**
   * Calculate average delivery time from quotes
   */
  calculateAverageDelivery(quotes) {
    if (quotes.length === 0) return null;
    
    const deliveryTimes = quotes.map(q => q.quote.estimatedDelivery);
    const avgTime = deliveryTimes.reduce((sum, time) => sum + time.getTime(), 0) / quotes.length;
    
    return new Date(avgTime);
  }

  /**
   * Get quotes for an order
   */
  async getQuotesForOrder(orderId) {
    try {
      const order = await Order.findOne({ orderId });
      return order?.pricing?.quotes || [];
    } catch (error) {
      logger.error(`Error getting quotes for order ${orderId}:`, error);
      return [];
    }
  }

  /**
   * Setup polling for delayed quote responses
   */
  async setupQuotePolling(order) {
    const pollKey = `quote_poll:${order.orderId}`;
    const pollData = {
      orderId: order.orderId,
      startedAt: new Date(),
      maxWaitTime: order.isUrgent ? 300000 : 3600000 // 5 min urgent, 1 hour normal
    };

    await redis.set(pollKey, JSON.stringify(pollData), 3600); // 1 hour TTL
    
    // Schedule polling check
    setTimeout(() => this.checkQuoteResponses(order), 60000); // Check in 1 minute
  }

  /**
   * Check for delayed quote responses
   */
  async checkQuoteResponses(order) {
    try {
      const quotes = await this.getQuotesForOrder(order.orderId);
      
      if (quotes.length > 0) {
        await order.updateStatus('quotes_received', `Received ${quotes.length} quotes`);
        await this.notifyCustomerQuotesReady(order);
      } else {
        // Continue polling if within time limit
        const pollKey = `quote_poll:${order.orderId}`;
        const pollData = JSON.parse(await redis.get(pollKey) || '{}');
        
        if (pollData.startedAt) {
          const elapsed = Date.now() - new Date(pollData.startedAt).getTime();
          
          if (elapsed < pollData.maxWaitTime) {
            setTimeout(() => this.checkQuoteResponses(order), 60000); // Check again in 1 minute
          } else {
            // Timeout - no quotes received
            await order.updateStatus('failed', 'No quotes received within time limit');
          }
        }
      }
    } catch (error) {
      logger.error(`Error checking quote responses for order ${order.orderId}:`, error);
    }
  }

  /**
   * Handle order processing errors
   */
  async handleOrderError(order, error) {
    try {
      logger.error(`Order ${order.orderId} processing failed:`, error);

      await order.updateStatus('failed', error.message);

      // Notify customer of failure
      await this.notifyDMLog('order_failed', {
        orderId: order.dmlogOrderId,
        error: error.message,
        timestamp: new Date().toISOString()
      });

    } catch (handlingError) {
      logger.error(`Error handling order error for ${order.orderId}:`, handlingError);
    }
  }
}

module.exports = new OrderPipelineService();