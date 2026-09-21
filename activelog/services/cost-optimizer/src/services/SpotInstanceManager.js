const EventEmitter = require('events');

class SpotInstanceManager extends EventEmitter {
  constructor() {
    super();
    this.spotRequests = new Map();
    this.priceHistory = new Map();
    this.activeInstances = new Map();
    this.strategies = new Map();
    this.interruptionHandlers = new Map();
    this.maxSpotPrice = 0.5;
    this.checkInterval = 30000;
    this.priceCheckTimer = null;
    
    this.initializeStrategies();
    this.startPriceMonitoring();
  }

  initializeStrategies() {
    this.strategies.set('diversified', {
      name: 'Diversified',
      description: 'Spread requests across multiple instance types and AZs',
      execute: (request) => this.executeDiversifiedStrategy(request)
    });

    this.strategies.set('capacity_optimized', {
      name: 'Capacity Optimized',
      description: 'Choose instances with highest availability',
      execute: (request) => this.executeCapacityOptimizedStrategy(request)
    });

    this.strategies.set('price_optimized', {
      name: 'Price Optimized',
      description: 'Choose cheapest available options',
      execute: (request) => this.executePriceOptimizedStrategy(request)
    });

    this.strategies.set('persistent', {
      name: 'Persistent',
      description: 'Automatically replace interrupted instances',
      execute: (request) => this.executePersistentStrategy(request)
    });
  }

  startPriceMonitoring() {
    if (this.priceCheckTimer) {
      clearInterval(this.priceCheckTimer);
    }

    this.priceCheckTimer = setInterval(() => {
      this.checkSpotPrices();
    }, this.checkInterval);

    this.checkSpotPrices();
  }

  stopPriceMonitoring() {
    if (this.priceCheckTimer) {
      clearInterval(this.priceCheckTimer);
      this.priceCheckTimer = null;
    }
  }

  async checkSpotPrices() {
    try {
      const instanceTypes = ['t3.micro', 't3.small', 't3.medium', 'c5.large', 'm5.large'];
      const availabilityZones = ['us-east-1a', 'us-east-1b', 'us-east-1c'];
      
      for (const instanceType of instanceTypes) {
        for (const az of availabilityZones) {
          const priceData = await this.fetchSpotPrice(instanceType, az);
          this.recordPriceHistory(instanceType, az, priceData);
        }
      }

      this.analyzePrice trends();
      this.checkInterruptionWarnings();
    } catch (error) {
      this.emit('error', { type: 'price_check_error', error: error.message });
    }
  }

  async fetchSpotPrice(instanceType, availabilityZone) {
    const basePrice = this.getBasePrice(instanceType);
    const volatility = Math.random() * 0.3;
    const demandFactor = Math.random() * 0.4 + 0.8;
    
    const spotPrice = basePrice * demandFactor * (1 + (Math.random() - 0.5) * volatility);
    const timestamp = new Date().toISOString();
    
    return {
      instanceType,
      availabilityZone,
      price: Math.round(spotPrice * 10000) / 10000,
      timestamp,
      onDemandPrice: basePrice,
      savings: ((basePrice - spotPrice) / basePrice) * 100,
      availability: Math.random() * 0.4 + 0.6
    };
  }

  getBasePrice(instanceType) {
    const prices = {
      't3.micro': 0.0104,
      't3.small': 0.0208,
      't3.medium': 0.0416,
      't3.large': 0.0832,
      'c5.large': 0.085,
      'c5.xlarge': 0.17,
      'm5.large': 0.096,
      'm5.xlarge': 0.192,
      'r5.large': 0.126
    };
    return prices[instanceType] || 0.1;
  }

  recordPriceHistory(instanceType, availabilityZone, priceData) {
    const key = `${instanceType}_${availabilityZone}`;
    
    if (!this.priceHistory.has(key)) {
      this.priceHistory.set(key, []);
    }
    
    const history = this.priceHistory.get(key);
    history.push(priceData);
    
    if (history.length > 1000) {
      history.shift();
    }
    
    this.emit('price_updated', { key, priceData });
  }

  analyzePriceTrends() {
    const trends = new Map();
    
    for (const [key, history] of this.priceHistory) {
      if (history.length < 10) continue;
      
      const recent = history.slice(-20);
      const prices = recent.map(h => h.price);
      
      const trend = this.calculatePriceTrend(prices);
      const volatility = this.calculateVolatility(prices);
      const prediction = this.predictNextPrice(prices);
      
      trends.set(key, {
        current: recent[recent.length - 1],
        trend,
        volatility,
        prediction,
        recommendation: this.generatePriceRecommendation(trend, volatility, prediction)
      });
    }
    
    this.emit('trends_analyzed', trends);
    return trends;
  }

  calculatePriceTrend(prices) {
    if (prices.length < 2) return 0;
    
    const n = prices.length;
    const x = Array.from({ length: n }, (_, i) => i);
    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = prices.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((sum, xi, i) => sum + xi * prices[i], 0);
    const sumXX = x.reduce((sum, xi) => sum + xi * xi, 0);
    
    return (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  }

  calculateVolatility(prices) {
    const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
    const variance = prices.reduce((sum, price) => sum + Math.pow(price - avg, 2), 0) / prices.length;
    return Math.sqrt(variance) / avg;
  }

  predictNextPrice(prices) {
    if (prices.length < 5) return prices[prices.length - 1];
    
    const trend = this.calculatePriceTrend(prices);
    const lastPrice = prices[prices.length - 1];
    const predictedPrice = lastPrice + trend;
    
    return Math.max(0, predictedPrice);
  }

  generatePriceRecommendation(trend, volatility, prediction) {
    if (volatility > 0.3) {
      return { action: 'wait', reason: 'High volatility, wait for stability' };
    }
    
    if (trend > 0.001) {
      return { action: 'buy_now', reason: 'Prices trending upward' };
    }
    
    if (trend < -0.001) {
      return { action: 'wait', reason: 'Prices trending downward' };
    }
    
    return { action: 'buy_now', reason: 'Stable pricing, good time to purchase' };
  }

  createSpotRequest(config) {
    const requestId = `spot_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const request = {
      id: requestId,
      instanceType: config.instanceType,
      maxPrice: config.maxPrice || this.maxSpotPrice,
      targetCapacity: config.targetCapacity || 1,
      strategy: config.strategy || 'diversified',
      availabilityZones: config.availabilityZones || ['us-east-1a', 'us-east-1b'],
      userData: config.userData,
      securityGroups: config.securityGroups,
      keyName: config.keyName,
      imageId: config.imageId,
      persistentRequest: config.persistentRequest || false,
      status: 'pending',
      createdAt: new Date().toISOString(),
      instances: [],
      attempts: 0,
      maxAttempts: config.maxAttempts || 5,
      interruptionCallback: config.interruptionCallback
    };
    
    this.spotRequests.set(requestId, request);
    this.executeSpotStrategy(request);
    
    return request;
  }

  async executeSpotStrategy(request) {
    const strategy = this.strategies.get(request.strategy);
    if (!strategy) {
      throw new Error(`Unknown strategy: ${request.strategy}`);
    }
    
    try {
      request.status = 'launching';
      request.attempts++;
      
      const result = await strategy.execute(request);
      
      if (result.success) {
        request.status = 'active';
        request.instances = result.instances;
        this.trackActiveInstances(request.instances);
        this.emit('spot_request_fulfilled', { requestId: request.id, instances: result.instances });
      } else {
        request.status = 'failed';
        request.lastError = result.error;
        this.emit('spot_request_failed', { requestId: request.id, error: result.error });
      }
    } catch (error) {
      request.status = 'failed';
      request.lastError = error.message;
      this.emit('spot_request_failed', { requestId: request.id, error: error.message });
    }
  }

  async executeDiversifiedStrategy(request) {
    const instances = [];
    const capacityPerAZ = Math.ceil(request.targetCapacity / request.availabilityZones.length);
    
    for (const az of request.availabilityZones) {
      try {
        const instance = await this.launchSpotInstance({
          ...request,
          availabilityZone: az,
          targetCapacity: capacityPerAZ
        });
        instances.push(instance);
      } catch (error) {
        console.warn(`Failed to launch in ${az}: ${error.message}`);
      }
    }
    
    return {
      success: instances.length > 0,
      instances,
      error: instances.length === 0 ? 'No instances launched in any AZ' : null
    };
  }

  async executeCapacityOptimizedStrategy(request) {
    const sortedAZs = request.availabilityZones.sort((a, b) => {
      const historyA = this.priceHistory.get(`${request.instanceType}_${a}`) || [];
      const historyB = this.priceHistory.get(`${request.instanceType}_${b}`) || [];
      
      const availabilityA = historyA.length > 0 ? historyA[historyA.length - 1].availability : 0.5;
      const availabilityB = historyB.length > 0 ? historyB[historyB.length - 1].availability : 0.5;
      
      return availabilityB - availabilityA;
    });
    
    const instances = [];
    let remainingCapacity = request.targetCapacity;
    
    for (const az of sortedAZs) {
      if (remainingCapacity <= 0) break;
      
      try {
        const instance = await this.launchSpotInstance({
          ...request,
          availabilityZone: az,
          targetCapacity: remainingCapacity
        });
        instances.push(instance);
        remainingCapacity -= instance.capacity;
      } catch (error) {
        console.warn(`Failed to launch in ${az}: ${error.message}`);
      }
    }
    
    return {
      success: instances.length > 0,
      instances,
      error: instances.length === 0 ? 'No capacity available' : null
    };
  }

  async executePriceOptimizedStrategy(request) {
    const sortedAZs = request.availabilityZones.sort((a, b) => {
      const priceA = this.getCurrentPrice(request.instanceType, a);
      const priceB = this.getCurrentPrice(request.instanceType, b);
      return priceA - priceB;
    });
    
    for (const az of sortedAZs) {
      const currentPrice = this.getCurrentPrice(request.instanceType, az);
      
      if (currentPrice <= request.maxPrice) {
        try {
          const instance = await this.launchSpotInstance({
            ...request,
            availabilityZone: az
          });
          
          return {
            success: true,
            instances: [instance],
            error: null
          };
        } catch (error) {
          console.warn(`Failed to launch in ${az}: ${error.message}`);
        }
      }
    }
    
    return {
      success: false,
      instances: [],
      error: 'No availability at acceptable price'
    };
  }

  async executePersistentStrategy(request) {
    const result = await this.executeDiversifiedStrategy(request);
    
    if (result.success) {
      result.instances.forEach(instance => {
        this.setupInterruptionHandler(instance, () => {
          console.log(`Instance ${instance.id} interrupted, relaunching...`);
          setTimeout(() => {
            this.executeSpotStrategy(request);
          }, 5000);
        });
      });
    }
    
    return result;
  }

  async launchSpotInstance(config) {
    await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 1000));
    
    const currentPrice = this.getCurrentPrice(config.instanceType, config.availabilityZone);
    
    if (currentPrice > config.maxPrice) {
      throw new Error(`Current price ${currentPrice} exceeds max price ${config.maxPrice}`);
    }
    
    const success = Math.random() > 0.1;
    if (!success) {
      throw new Error('Launch failed - insufficient capacity');
    }
    
    const instance = {
      id: `i-${Math.random().toString(36).substr(2, 17)}`,
      instanceType: config.instanceType,
      availabilityZone: config.availabilityZone,
      spotPrice: currentPrice,
      launchedAt: new Date().toISOString(),
      status: 'running',
      capacity: 1
    };
    
    return instance;
  }

  getCurrentPrice(instanceType, availabilityZone) {
    const key = `${instanceType}_${availabilityZone}`;
    const history = this.priceHistory.get(key);
    
    if (!history || history.length === 0) {
      return this.getBasePrice(instanceType) * 0.5;
    }
    
    return history[history.length - 1].price;
  }

  trackActiveInstances(instances) {
    instances.forEach(instance => {
      this.activeInstances.set(instance.id, instance);
    });
  }

  setupInterruptionHandler(instance, callback) {
    this.interruptionHandlers.set(instance.id, callback);
    
    setTimeout(() => {
      const shouldInterrupt = Math.random() < 0.05;
      if (shouldInterrupt) {
        this.handleInstanceInterruption(instance.id);
      }
    }, Math.random() * 300000 + 60000);
  }

  handleInstanceInterruption(instanceId) {
    const instance = this.activeInstances.get(instanceId);
    if (!instance) return;
    
    instance.status = 'interrupted';
    instance.interruptedAt = new Date().toISOString();
    
    const handler = this.interruptionHandlers.get(instanceId);
    if (handler) {
      handler();
    }
    
    this.emit('instance_interrupted', { instanceId, instance });
    
    this.activeInstances.delete(instanceId);
    this.interruptionHandlers.delete(instanceId);
  }

  checkInterruptionWarnings() {
    for (const [instanceId, instance] of this.activeInstances) {
      const warning = Math.random() < 0.02;
      if (warning) {
        this.emit('interruption_warning', {
          instanceId,
          instance,
          estimatedTime: Math.random() * 120 + 60,
          recommendation: 'Consider migrating workload to on-demand instance'
        });
      }
    }
  }

  getSpotPriceTrends(instanceType, hours = 24) {
    const trends = [];
    const availabilityZones = ['us-east-1a', 'us-east-1b', 'us-east-1c'];
    
    availabilityZones.forEach(az => {
      const key = `${instanceType}_${az}`;
      const history = this.priceHistory.get(key) || [];
      
      const cutoff = new Date(Date.now() - hours * 60 * 60 * 1000);
      const recentHistory = history.filter(h => new Date(h.timestamp) > cutoff);
      
      if (recentHistory.length > 0) {
        const prices = recentHistory.map(h => h.price);
        const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        
        trends.push({
          availabilityZone: az,
          averagePrice: avgPrice,
          minPrice,
          maxPrice,
          volatility: this.calculateVolatility(prices),
          dataPoints: recentHistory.length,
          savings: ((this.getBasePrice(instanceType) - avgPrice) / this.getBasePrice(instanceType)) * 100
        });
      }
    });
    
    return trends;
  }

  getSavingsReport(timeframe = 'day') {
    const multipliers = { hour: 1, day: 24, week: 168, month: 720 };
    const hours = multipliers[timeframe] || 24;
    
    let totalSpotCost = 0;
    let totalOnDemandCost = 0;
    let instanceHours = 0;
    
    for (const [_, instance] of this.activeInstances) {
      const runningHours = Math.min(hours, 
        (Date.now() - new Date(instance.launchedAt).getTime()) / (1000 * 60 * 60)
      );
      
      const spotCost = instance.spotPrice * runningHours;
      const onDemandCost = this.getBasePrice(instance.instanceType) * runningHours;
      
      totalSpotCost += spotCost;
      totalOnDemandCost += onDemandCost;
      instanceHours += runningHours;
    }
    
    return {
      timeframe,
      instanceHours,
      spotCost: Math.round(totalSpotCost * 100) / 100,
      onDemandCost: Math.round(totalOnDemandCost * 100) / 100,
      savings: Math.round((totalOnDemandCost - totalSpotCost) * 100) / 100,
      savingsPercentage: totalOnDemandCost > 0 ? 
        Math.round(((totalOnDemandCost - totalSpotCost) / totalOnDemandCost) * 10000) / 100 : 0
    };
  }

  terminateSpotRequest(requestId) {
    const request = this.spotRequests.get(requestId);
    if (!request) {
      throw new Error(`Spot request ${requestId} not found`);
    }
    
    request.status = 'terminating';
    
    request.instances.forEach(instance => {
      this.terminateInstance(instance.id);
    });
    
    request.status = 'terminated';
    request.terminatedAt = new Date().toISOString();
    
    this.emit('spot_request_terminated', { requestId });
  }

  terminateInstance(instanceId) {
    const instance = this.activeInstances.get(instanceId);
    if (instance) {
      instance.status = 'terminated';
      instance.terminatedAt = new Date().toISOString();
      
      this.activeInstances.delete(instanceId);
      this.interruptionHandlers.delete(instanceId);
      
      this.emit('instance_terminated', { instanceId, instance });
    }
  }

  getActiveInstances() {
    return Array.from(this.activeInstances.values());
  }

  getSpotRequests() {
    return Array.from(this.spotRequests.values());
  }

  exportData(format = 'json') {
    const data = {
      timestamp: new Date().toISOString(),
      spotRequests: Array.from(this.spotRequests.values()),
      activeInstances: Array.from(this.activeInstances.values()),
      priceHistory: Object.fromEntries(this.priceHistory),
      savingsReport: this.getSavingsReport('month')
    };
    
    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    }
    
    return data;
  }
}

module.exports = SpotInstanceManager;