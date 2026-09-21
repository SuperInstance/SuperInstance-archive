import { EventEmitter } from 'events';

export interface ComputeResource {
  id: string;
  type: 'cpu' | 'gpu' | 'memory' | 'storage' | 'network';
  capacity: number;
  performance: number;
  availability: number;
  location: string;
  provider: string;
}

export interface PricingFactors {
  baseResourceCost: number;
  demandMultiplier: number;
  performanceMultiplier: number;
  locationMultiplier: number;
  availabilityMultiplier: number;
  reputationMultiplier: number;
  marketConditions: MarketConditions;
}

export interface MarketConditions {
  globalDemand: number;
  supplyRatio: number;
  competitiveIndex: number;
  seasonalFactors: number;
  networkCongestion: number;
}

export interface PriceQuote {
  resourceId: string;
  basePrice: number;
  adjustedPrice: number;
  factors: PricingFactors;
  validUntil: Date;
  currency: string;
  breakdown: PriceBreakdown;
}

export interface PriceBreakdown {
  baseCost: number;
  demandAdjustment: number;
  performanceBonus: number;
  locationAdjustment: number;
  availabilityDiscount: number;
  reputationDiscount: number;
  marketAdjustment: number;
  totalAdjustments: number;
}

export interface DynamicPricingConfig {
  basePrices: {
    cpu: { perCore: number; perGHz: number };
    gpu: { perCore: number; perVRAM: number };
    memory: { perGB: number };
    storage: { perGB: number };
    network: { perMbps: number };
  };
  multipliers: {
    demand: { min: 0.5; max: 3.0 };
    performance: { min: 0.8; max: 2.0 };
    location: { min: 0.7; max: 1.5 };
    availability: { min: 0.6; max: 1.2 };
    reputation: { min: 0.9; max: 1.1 };
  };
  marketFactors: {
    demandSensitivity: number;
    supplyElasticity: number;
    competitionWeight: number;
  };
}

export class PricingAlgorithm extends EventEmitter {
  private config: DynamicPricingConfig;
  private marketData: Map<string, MarketConditions> = new Map();
  private priceHistory: Map<string, PriceQuote[]> = new Map();
  private demandForecasts: Map<string, number[]> = new Map();
  private competitorPrices: Map<string, number> = new Map();
  private priceUpdateInterval: NodeJS.Timeout | null = null;

  constructor(config?: Partial<DynamicPricingConfig>) {
    super();
    this.config = this.mergeConfig(config);
    this.startPriceMonitoring();
  }

  private mergeConfig(userConfig?: Partial<DynamicPricingConfig>): DynamicPricingConfig {
    const defaultConfig: DynamicPricingConfig = {
      basePrices: {
        cpu: { perCore: 0.05, perGHz: 0.02 },
        gpu: { perCore: 0.15, perVRAM: 0.01 },
        memory: { perGB: 0.008 },
        storage: { perGB: 0.0001 },
        network: { perMbps: 0.001 }
      },
      multipliers: {
        demand: { min: 0.5, max: 3.0 },
        performance: { min: 0.8, max: 2.0 },
        location: { min: 0.7, max: 1.5 },
        availability: { min: 0.6, max: 1.2 },
        reputation: { min: 0.9, max: 1.1 }
      },
      marketFactors: {
        demandSensitivity: 1.2,
        supplyElasticity: 0.8,
        competitionWeight: 0.3
      }
    };

    return { ...defaultConfig, ...userConfig };
  }

  public async calculatePrice(resource: ComputeResource, duration: number = 1): Promise<PriceQuote> {
    const basePrice = this.calculateBasePrice(resource);
    const factors = await this.calculatePricingFactors(resource);
    const adjustedPrice = this.applyPricingFactors(basePrice, factors);
    const breakdown = this.createPriceBreakdown(basePrice, factors);

    const quote: PriceQuote = {
      resourceId: resource.id,
      basePrice: basePrice * duration,
      adjustedPrice: adjustedPrice * duration,
      factors,
      validUntil: new Date(Date.now() + 15 * 60 * 1000), // 15 minutes
      currency: 'USD',
      breakdown
    };

    await this.recordPriceQuote(quote);
    this.emit('priceCalculated', quote);

    return quote;
  }

  private calculateBasePrice(resource: ComputeResource): number {
    const { basePrices } = this.config;
    let price = 0;

    switch (resource.type) {
      case 'cpu':
        price = basePrices.cpu.perCore * resource.capacity;
        break;
      case 'gpu':
        price = basePrices.gpu.perCore * resource.capacity;
        break;
      case 'memory':
        price = basePrices.memory.perGB * resource.capacity;
        break;
      case 'storage':
        price = basePrices.storage.perGB * resource.capacity;
        break;
      case 'network':
        price = basePrices.network.perMbps * resource.capacity;
        break;
    }

    return price;
  }

  private async calculatePricingFactors(resource: ComputeResource): Promise<PricingFactors> {
    const marketConditions = await this.getMarketConditions(resource.location);
    const demandMultiplier = this.calculateDemandMultiplier(resource, marketConditions);
    const performanceMultiplier = this.calculatePerformanceMultiplier(resource);
    const locationMultiplier = this.calculateLocationMultiplier(resource);
    const availabilityMultiplier = this.calculateAvailabilityMultiplier(resource);
    const reputationMultiplier = await this.calculateReputationMultiplier(resource.provider);

    return {
      baseResourceCost: this.calculateBasePrice(resource),
      demandMultiplier,
      performanceMultiplier,
      locationMultiplier,
      availabilityMultiplier,
      reputationMultiplier,
      marketConditions
    };
  }

  private calculateDemandMultiplier(resource: ComputeResource, market: MarketConditions): number {
    const { multipliers, marketFactors } = this.config;
    const demandFactor = market.globalDemand * marketFactors.demandSensitivity;
    const supplyFactor = 1 / market.supplyRatio;
    const competitiveFactor = 1 - (market.competitiveIndex * marketFactors.competitionWeight);

    const multiplier = demandFactor * supplyFactor * competitiveFactor;
    return Math.max(multipliers.demand.min, Math.min(multipliers.demand.max, multiplier));
  }

  private calculatePerformanceMultiplier(resource: ComputeResource): number {
    const { multipliers } = this.config;
    const performanceFactor = resource.performance / 100; // Normalize to 0-1
    const multiplier = 0.8 + (performanceFactor * 1.2); // Scale to 0.8-2.0
    return Math.max(multipliers.performance.min, Math.min(multipliers.performance.max, multiplier));
  }

  private calculateLocationMultiplier(resource: ComputeResource): number {
    const { multipliers } = this.config;
    // Location-based pricing (simplified)
    const locationFactors: Record<string, number> = {
      'us-east': 1.0,
      'us-west': 1.1,
      'europe': 1.2,
      'asia': 0.8,
      'south-america': 0.7,
      'africa': 0.6
    };

    const factor = locationFactors[resource.location] || 1.0;
    return Math.max(multipliers.location.min, Math.min(multipliers.location.max, factor));
  }

  private calculateAvailabilityMultiplier(resource: ComputeResource): number {
    const { multipliers } = this.config;
    const availabilityFactor = resource.availability / 100; // Normalize to 0-1
    const multiplier = 1.2 - (availabilityFactor * 0.6); // Inverse relationship
    return Math.max(multipliers.availability.min, Math.min(multipliers.availability.max, multiplier));
  }

  private async calculateReputationMultiplier(providerId: string): Promise<number> {
    const { multipliers } = this.config;
    // This would integrate with the reputation system
    const reputation = await this.getProviderReputation(providerId);
    const reputationFactor = reputation / 100; // Normalize to 0-1
    const multiplier = 1.1 - (reputationFactor * 0.2); // Higher reputation = lower prices
    return Math.max(multipliers.reputation.min, Math.min(multipliers.reputation.max, multiplier));
  }

  private applyPricingFactors(basePrice: number, factors: PricingFactors): number {
    return basePrice * 
           factors.demandMultiplier * 
           factors.performanceMultiplier * 
           factors.locationMultiplier * 
           factors.availabilityMultiplier * 
           factors.reputationMultiplier;
  }

  private createPriceBreakdown(basePrice: number, factors: PricingFactors): PriceBreakdown {
    const baseCost = basePrice;
    const demandAdjustment = baseCost * (factors.demandMultiplier - 1);
    const performanceBonus = baseCost * (factors.performanceMultiplier - 1);
    const locationAdjustment = baseCost * (factors.locationMultiplier - 1);
    const availabilityDiscount = baseCost * (factors.availabilityMultiplier - 1);
    const reputationDiscount = baseCost * (factors.reputationMultiplier - 1);
    const marketAdjustment = baseCost * (factors.marketConditions.seasonalFactors - 1);

    return {
      baseCost,
      demandAdjustment,
      performanceBonus,
      locationAdjustment,
      availabilityDiscount,
      reputationDiscount,
      marketAdjustment,
      totalAdjustments: demandAdjustment + performanceBonus + locationAdjustment + 
                       availabilityDiscount + reputationDiscount + marketAdjustment
    };
  }

  public async updateMarketConditions(location: string, conditions: Partial<MarketConditions>): Promise<void> {
    const existing = this.marketData.get(location) || {
      globalDemand: 1.0,
      supplyRatio: 1.0,
      competitiveIndex: 0.5,
      seasonalFactors: 1.0,
      networkCongestion: 0.1
    };

    const updated = { ...existing, ...conditions };
    this.marketData.set(location, updated);
    this.emit('marketConditionsUpdated', location, updated);
  }

  public async forecastDemand(resourceType: string, horizon: number = 24): Promise<number[]> {
    // Simplified demand forecasting
    const historical = this.demandForecasts.get(resourceType) || [];
    const forecast: number[] = [];

    for (let i = 0; i < horizon; i++) {
      const trend = this.calculateDemandTrend(historical, i);
      const seasonal = this.calculateSeasonalFactor(i);
      const noise = (Math.random() - 0.5) * 0.1; // ±5% noise
      forecast.push(Math.max(0, trend * seasonal + noise));
    }

    this.demandForecasts.set(resourceType, forecast);
    return forecast;
  }

  private calculateDemandTrend(historical: number[], offset: number): number {
    if (historical.length < 2) return 1.0;
    
    const recent = historical.slice(-10);
    const average = recent.reduce((sum, val) => sum + val, 0) / recent.length;
    const trend = (recent[recent.length - 1] - recent[0]) / recent.length;
    
    return average + (trend * offset);
  }

  private calculateSeasonalFactor(hourOffset: number): number {
    // Simple daily seasonality (peak during business hours)
    const hour = (new Date().getHours() + hourOffset) % 24;
    if (hour >= 9 && hour <= 17) return 1.2; // Business hours
    if (hour >= 18 && hour <= 22) return 1.1; // Evening
    return 0.8; // Night/early morning
  }

  private async getMarketConditions(location: string): Promise<MarketConditions> {
    return this.marketData.get(location) || {
      globalDemand: 1.0,
      supplyRatio: 1.0,
      competitiveIndex: 0.5,
      seasonalFactors: 1.0,
      networkCongestion: 0.1
    };
  }

  private async getProviderReputation(providerId: string): Promise<number> {
    // This would integrate with the reputation system
    // For now, return a default value
    return 85; // Default reputation score
  }

  private async recordPriceQuote(quote: PriceQuote): Promise<void> {
    const history = this.priceHistory.get(quote.resourceId) || [];
    history.push(quote);
    
    // Keep only last 100 quotes per resource
    if (history.length > 100) {
      history.splice(0, history.length - 100);
    }
    
    this.priceHistory.set(quote.resourceId, history);
  }

  private startPriceMonitoring(): void {
    this.priceUpdateInterval = setInterval(async () => {
      await this.updateCompetitorPrices();
      await this.adjustMarketConditions();
      this.emit('priceUpdate');
    }, 5 * 60 * 1000); // Update every 5 minutes
  }

  private async updateCompetitorPrices(): Promise<void> {
    // Simulate competitor price updates
    for (const [resourceId, currentPrice] of this.competitorPrices) {
      const change = (Math.random() - 0.5) * 0.1; // ±5% change
      const newPrice = currentPrice * (1 + change);
      this.competitorPrices.set(resourceId, Math.max(0, newPrice));
    }
  }

  private async adjustMarketConditions(): Promise<void> {
    // Simulate market condition changes
    for (const [location, conditions] of this.marketData) {
      const updated: MarketConditions = {
        globalDemand: Math.max(0.1, conditions.globalDemand + (Math.random() - 0.5) * 0.05),
        supplyRatio: Math.max(0.1, conditions.supplyRatio + (Math.random() - 0.5) * 0.03),
        competitiveIndex: Math.max(0, Math.min(1, conditions.competitiveIndex + (Math.random() - 0.5) * 0.02)),
        seasonalFactors: Math.max(0.5, Math.min(2, conditions.seasonalFactors + (Math.random() - 0.5) * 0.01)),
        networkCongestion: Math.max(0, Math.min(1, conditions.networkCongestion + (Math.random() - 0.5) * 0.02))
      };
      
      this.marketData.set(location, updated);
    }
  }

  public async getBulkPricing(resources: ComputeResource[], duration: number = 1): Promise<PriceQuote[]> {
    const quotes = await Promise.all(
      resources.map(resource => this.calculatePrice(resource, duration))
    );

    // Apply bulk discount
    const totalValue = quotes.reduce((sum, quote) => sum + quote.adjustedPrice, 0);
    const bulkDiscount = this.calculateBulkDiscount(totalValue, resources.length);

    return quotes.map(quote => ({
      ...quote,
      adjustedPrice: quote.adjustedPrice * (1 - bulkDiscount),
      breakdown: {
        ...quote.breakdown,
        totalAdjustments: quote.breakdown.totalAdjustments - (quote.adjustedPrice * bulkDiscount)
      }
    }));
  }

  private calculateBulkDiscount(totalValue: number, resourceCount: number): number {
    if (resourceCount >= 10) return 0.15; // 15% discount for 10+ resources
    if (resourceCount >= 5) return 0.10;  // 10% discount for 5+ resources
    if (resourceCount >= 3) return 0.05;  // 5% discount for 3+ resources
    return 0; // No discount for smaller orders
  }

  public getPriceHistory(resourceId: string, limit: number = 50): PriceQuote[] {
    const history = this.priceHistory.get(resourceId) || [];
    return history.slice(-limit);
  }

  public async optimizePricing(targetMargin: number = 0.15): Promise<void> {
    // AI-driven price optimization would go here
    // For now, implement basic margin optimization
    const avgMarketPrice = Array.from(this.competitorPrices.values())
      .reduce((sum, price) => sum + price, 0) / this.competitorPrices.size;

    if (avgMarketPrice > 0) {
      const targetPrice = avgMarketPrice * (1 - targetMargin);
      // Adjust base prices to meet target
      this.emit('priceOptimization', { targetPrice, avgMarketPrice, targetMargin });
    }
  }

  public stop(): void {
    if (this.priceUpdateInterval) {
      clearInterval(this.priceUpdateInterval);
      this.priceUpdateInterval = null;
    }
  }
}

export default PricingAlgorithm;