import { EventEmitter } from 'events';

export interface ProductionMetrics {
  printerId: string;
  jobId: string;
  startTime: Date;
  endTime?: Date;
  materialUsed: number;
  materialCost: number;
  energyCost: number;
  laborCost: number;
  maintenanceCost: number;
  revenue: number;
  profit: number;
  profitMargin: number;
  efficiency: number;
  qualityScore: number;
  customerSatisfaction: number;
}

export interface CostStructure {
  materialCostPerGram: number;
  energyCostPerKWh: number;
  laborCostPerHour: number;
  maintenanceCostPerHour: number;
  overheadCostPerHour: number;
  deprecationCostPerHour: number;
  facilityRent: number;
  insurance: number;
  utilities: number;
}

export interface OptimizationStrategy {
  id: string;
  name: string;
  description: string;
  type: OptimizationType;
  parameters: OptimizationParameters;
  priority: number;
  isActive: boolean;
  expectedImpact: number;
  actualImpact?: number;
  implementationCost: number;
  roi: number;
}

export enum OptimizationType {
  MATERIAL_USAGE = 'material_usage',
  ENERGY_EFFICIENCY = 'energy_efficiency',
  LABOR_OPTIMIZATION = 'labor_optimization',
  QUALITY_IMPROVEMENT = 'quality_improvement',
  THROUGHPUT_MAXIMIZATION = 'throughput_maximization',
  COST_REDUCTION = 'cost_reduction',
  PRICING_OPTIMIZATION = 'pricing_optimization',
  MAINTENANCE_OPTIMIZATION = 'maintenance_optimization'
}

export interface OptimizationParameters {
  targetMetric: string;
  currentValue: number;
  targetValue: number;
  timeframe: number;
  constraints: OptimizationConstraint[];
  variables: OptimizationVariable[];
}

export interface OptimizationConstraint {
  parameter: string;
  operator: 'lt' | 'gt' | 'eq' | 'lte' | 'gte';
  value: number;
  weight: number;
}

export interface OptimizationVariable {
  name: string;
  currentValue: number;
  minValue: number;
  maxValue: number;
  step: number;
  impact: number;
}

export interface ProfitAnalysis {
  totalRevenue: number;
  totalCosts: number;
  grossProfit: number;
  netProfit: number;
  profitMargin: number;
  costBreakdown: {
    materials: number;
    energy: number;
    labor: number;
    maintenance: number;
    overhead: number;
    depreciation: number;
  };
  efficiency: {
    materialEfficiency: number;
    energyEfficiency: number;
    timeEfficiency: number;
    qualityEfficiency: number;
  };
  trends: {
    revenueGrowth: number;
    costGrowth: number;
    profitGrowth: number;
    efficiencyGrowth: number;
  };
}

export interface OptimizationRecommendation {
  id: string;
  title: string;
  description: string;
  category: OptimizationType;
  priority: 'critical' | 'high' | 'medium' | 'low';
  estimatedSavings: number;
  implementationCost: number;
  paybackPeriod: number;
  confidence: number;
  actions: string[];
  metrics: string[];
  timeline: number;
  dependencies: string[];
}

export interface PricingModel {
  id: string;
  name: string;
  description: string;
  basePrice: number;
  materialMultiplier: number;
  complexityMultiplier: number;
  rushOrderMultiplier: number;
  volumeDiscounts: VolumeDiscount[];
  qualityPremiums: QualityPremium[];
  dynamicPricing: boolean;
  marketFactors: MarketFactor[];
}

export interface VolumeDiscount {
  minQuantity: number;
  discount: number;
}

export interface QualityPremium {
  qualityLevel: string;
  premium: number;
}

export interface MarketFactor {
  factor: string;
  weight: number;
  currentValue: number;
  impact: number;
}

export class ProfitOptimizer extends EventEmitter {
  private metrics: Map<string, ProductionMetrics[]> = new Map();
  private costStructure: CostStructure;
  private strategies: Map<string, OptimizationStrategy> = new Map();
  private recommendations: Map<string, OptimizationRecommendation> = new Map();
  private pricingModels: Map<string, PricingModel> = new Map();
  private analysisInterval?: NodeJS.Timeout;
  private optimizationHistory: Map<string, any[]> = new Map();

  constructor(initialCostStructure: Partial<CostStructure> = {}) {
    super();
    
    this.costStructure = {
      materialCostPerGram: 0.05,
      energyCostPerKWh: 0.12,
      laborCostPerHour: 25.00,
      maintenanceCostPerHour: 5.00,
      overheadCostPerHour: 10.00,
      deprecationCostPerHour: 2.50,
      facilityRent: 2000,
      insurance: 500,
      utilities: 300,
      ...initialCostStructure
    };

    this.initializeDefaultStrategies();
    this.initializeDefaultPricingModels();
    this.startContinuousAnalysis();
  }

  private initializeDefaultStrategies(): void {
    const strategies: OptimizationStrategy[] = [
      {
        id: 'material_waste_reduction',
        name: 'Material Waste Reduction',
        description: 'Optimize print settings to reduce material waste',
        type: OptimizationType.MATERIAL_USAGE,
        parameters: {
          targetMetric: 'material_efficiency',
          currentValue: 85,
          targetValue: 95,
          timeframe: 30,
          constraints: [
            { parameter: 'quality_score', operator: 'gte', value: 90, weight: 1.0 }
          ],
          variables: [
            { name: 'infill_density', currentValue: 20, minValue: 10, maxValue: 30, step: 1, impact: 0.8 },
            { name: 'layer_height', currentValue: 0.2, minValue: 0.1, maxValue: 0.3, step: 0.05, impact: 0.6 },
            { name: 'support_density', currentValue: 15, minValue: 10, maxValue: 25, step: 1, impact: 0.7 }
          ]
        },
        priority: 1,
        isActive: true,
        expectedImpact: 12000,
        implementationCost: 2000,
        roi: 6.0
      },
      {
        id: 'energy_optimization',
        name: 'Energy Consumption Optimization',
        description: 'Optimize printer settings for energy efficiency',
        type: OptimizationType.ENERGY_EFFICIENCY,
        parameters: {
          targetMetric: 'energy_efficiency',
          currentValue: 75,
          targetValue: 85,
          timeframe: 60,
          constraints: [
            { parameter: 'print_time', operator: 'lte', value: 1.1, weight: 0.8 }
          ],
          variables: [
            { name: 'hotend_temp', currentValue: 210, minValue: 200, maxValue: 220, step: 5, impact: 0.4 },
            { name: 'bed_temp', currentValue: 60, minValue: 50, maxValue: 70, step: 5, impact: 0.3 },
            { name: 'print_speed', currentValue: 60, minValue: 40, maxValue: 80, step: 5, impact: 0.6 }
          ]
        },
        priority: 2,
        isActive: true,
        expectedImpact: 8000,
        implementationCost: 1500,
        roi: 5.3
      },
      {
        id: 'quality_optimization',
        name: 'Quality Score Improvement',
        description: 'Optimize settings to improve print quality and reduce failures',
        type: OptimizationType.QUALITY_IMPROVEMENT,
        parameters: {
          targetMetric: 'quality_score',
          currentValue: 88,
          targetValue: 95,
          timeframe: 45,
          constraints: [
            { parameter: 'material_cost', operator: 'lte', value: 1.05, weight: 0.7 }
          ],
          variables: [
            { name: 'retraction_distance', currentValue: 5, minValue: 3, maxValue: 7, step: 0.5, impact: 0.5 },
            { name: 'cooling_fan_speed', currentValue: 100, minValue: 80, maxValue: 100, step: 10, impact: 0.4 }
          ]
        },
        priority: 1,
        isActive: true,
        expectedImpact: 15000,
        implementationCost: 3000,
        roi: 5.0
      }
    ];

    strategies.forEach(strategy => {
      this.strategies.set(strategy.id, strategy);
    });
  }

  private initializeDefaultPricingModels(): void {
    const models: PricingModel[] = [
      {
        id: 'standard_pricing',
        name: 'Standard Cost-Plus Pricing',
        description: 'Basic cost-plus pricing with standard margins',
        basePrice: 0.10,
        materialMultiplier: 3.0,
        complexityMultiplier: 1.5,
        rushOrderMultiplier: 1.8,
        volumeDiscounts: [
          { minQuantity: 10, discount: 0.05 },
          { minQuantity: 50, discount: 0.10 },
          { minQuantity: 100, discount: 0.15 }
        ],
        qualityPremiums: [
          { qualityLevel: 'premium', premium: 0.20 },
          { qualityLevel: 'prototype', premium: 0.15 }
        ],
        dynamicPricing: false,
        marketFactors: []
      },
      {
        id: 'dynamic_pricing',
        name: 'Dynamic Market-Based Pricing',
        description: 'AI-driven pricing based on market conditions and demand',
        basePrice: 0.12,
        materialMultiplier: 2.8,
        complexityMultiplier: 1.7,
        rushOrderMultiplier: 2.0,
        volumeDiscounts: [
          { minQuantity: 5, discount: 0.03 },
          { minQuantity: 25, discount: 0.08 },
          { minQuantity: 100, discount: 0.18 }
        ],
        qualityPremiums: [
          { qualityLevel: 'premium', premium: 0.25 },
          { qualityLevel: 'prototype', premium: 0.20 }
        ],
        dynamicPricing: true,
        marketFactors: [
          { factor: 'demand_level', weight: 0.3, currentValue: 0.8, impact: 0.15 },
          { factor: 'competitor_pricing', weight: 0.4, currentValue: 0.9, impact: -0.10 },
          { factor: 'material_cost_trend', weight: 0.3, currentValue: 1.1, impact: 0.08 }
        ]
      }
    ];

    models.forEach(model => {
      this.pricingModels.set(model.id, model);
    });
  }

  public recordProductionMetrics(metrics: ProductionMetrics): void {
    const printerMetrics = this.metrics.get(metrics.printerId) || [];
    printerMetrics.push(metrics);
    this.metrics.set(metrics.printerId, printerMetrics);

    this.emit('metricsRecorded', metrics);
    this.analyzeMetrics(metrics.printerId);
  }

  public calculateJobCost(
    materialWeight: number,
    printTime: number,
    complexity: number = 1.0,
    qualityLevel: 'standard' | 'premium' | 'prototype' = 'standard'
  ): {
    materialCost: number;
    energyCost: number;
    laborCost: number;
    maintenanceCost: number;
    overheadCost: number;
    deprecationCost: number;
    totalCost: number;
  } {
    const materialCost = materialWeight * this.costStructure.materialCostPerGram;
    const energyCost = (printTime / 60) * 0.15 * this.costStructure.energyCostPerKWh; // 150W average
    const laborCost = (printTime / 60) * this.costStructure.laborCostPerHour * 0.1; // 10% labor involvement
    const maintenanceCost = (printTime / 60) * this.costStructure.maintenanceCostPerHour;
    const overheadCost = (printTime / 60) * this.costStructure.overheadCostPerHour;
    const deprecationCost = (printTime / 60) * this.costStructure.deprecationCostPerHour;

    const totalCost = materialCost + energyCost + laborCost + maintenanceCost + overheadCost + deprecationCost;

    return {
      materialCost,
      energyCost,
      laborCost,
      maintenanceCost,
      overheadCost,
      deprecationCost,
      totalCost: totalCost * complexity
    };
  }

  public calculateOptimalPrice(
    jobCost: number,
    complexity: number,
    quantity: number,
    isRushOrder: boolean = false,
    qualityLevel: 'standard' | 'premium' | 'prototype' = 'standard',
    pricingModelId: string = 'standard_pricing'
  ): {
    basePrice: number;
    adjustments: Record<string, number>;
    finalPrice: number;
    margin: number;
    profitability: number;
  } {
    const model = this.pricingModels.get(pricingModelId);
    if (!model) {
      throw new Error(`Pricing model ${pricingModelId} not found`);
    }

    let basePrice = jobCost * model.materialMultiplier;
    basePrice *= Math.pow(complexity, model.complexityMultiplier - 1);

    const adjustments: Record<string, number> = {};

    // Volume discount
    const applicableDiscount = model.volumeDiscounts
      .filter(d => quantity >= d.minQuantity)
      .sort((a, b) => b.discount - a.discount)[0];
    
    if (applicableDiscount) {
      adjustments.volumeDiscount = -basePrice * applicableDiscount.discount;
    }

    // Quality premium
    const qualityPremium = model.qualityPremiums.find(p => p.qualityLevel === qualityLevel);
    if (qualityPremium) {
      adjustments.qualityPremium = basePrice * qualityPremium.premium;
    }

    // Rush order
    if (isRushOrder) {
      adjustments.rushOrder = basePrice * (model.rushOrderMultiplier - 1);
    }

    // Dynamic pricing adjustments
    if (model.dynamicPricing) {
      let dynamicAdjustment = 0;
      model.marketFactors.forEach(factor => {
        dynamicAdjustment += (factor.currentValue - 1) * factor.weight * factor.impact;
      });
      adjustments.marketConditions = basePrice * dynamicAdjustment;
    }

    const totalAdjustments = Object.values(adjustments).reduce((sum, adj) => sum + adj, 0);
    const finalPrice = basePrice + totalAdjustments;
    const margin = finalPrice - jobCost;
    const profitability = margin / finalPrice;

    return {
      basePrice,
      adjustments,
      finalPrice,
      margin,
      profitability
    };
  }

  public generateProfitAnalysis(
    printerId?: string,
    timeframe: number = 30
  ): ProfitAnalysis {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - timeframe);

    let relevantMetrics: ProductionMetrics[] = [];
    
    if (printerId) {
      relevantMetrics = (this.metrics.get(printerId) || [])
        .filter(m => m.startTime >= cutoffDate);
    } else {
      for (const printerMetrics of this.metrics.values()) {
        relevantMetrics.push(...printerMetrics.filter(m => m.startTime >= cutoffDate));
      }
    }

    const totalRevenue = relevantMetrics.reduce((sum, m) => sum + m.revenue, 0);
    const totalMaterialCost = relevantMetrics.reduce((sum, m) => sum + m.materialCost, 0);
    const totalEnergyCost = relevantMetrics.reduce((sum, m) => sum + m.energyCost, 0);
    const totalLaborCost = relevantMetrics.reduce((sum, m) => sum + m.laborCost, 0);
    const totalMaintenanceCost = relevantMetrics.reduce((sum, m) => sum + m.maintenanceCost, 0);
    
    const dailyOverhead = (this.costStructure.facilityRent + 
                          this.costStructure.insurance + 
                          this.costStructure.utilities) / 30;
    const totalOverheadCost = dailyOverhead * timeframe;
    
    const totalDepreciation = relevantMetrics.length * 
                            this.costStructure.deprecationCostPerHour * 2; // Average 2h per job
    
    const totalCosts = totalMaterialCost + totalEnergyCost + totalLaborCost + 
                      totalMaintenanceCost + totalOverheadCost + totalDepreciation;

    // Calculate previous period for trends
    const previousCutoff = new Date(cutoffDate);
    previousCutoff.setDate(previousCutoff.getDate() - timeframe);
    
    let previousMetrics: ProductionMetrics[] = [];
    if (printerId) {
      previousMetrics = (this.metrics.get(printerId) || [])
        .filter(m => m.startTime >= previousCutoff && m.startTime < cutoffDate);
    } else {
      for (const printerMetrics of this.metrics.values()) {
        previousMetrics.push(...printerMetrics
          .filter(m => m.startTime >= previousCutoff && m.startTime < cutoffDate));
      }
    }

    const previousRevenue = previousMetrics.reduce((sum, m) => sum + m.revenue, 0);
    const previousCosts = previousMetrics.reduce((sum, m) => 
      sum + m.materialCost + m.energyCost + m.laborCost + m.maintenanceCost, 0);
    const previousProfit = previousRevenue - previousCosts;

    return {
      totalRevenue,
      totalCosts,
      grossProfit: totalRevenue - totalCosts,
      netProfit: totalRevenue - totalCosts,
      profitMargin: totalRevenue > 0 ? (totalRevenue - totalCosts) / totalRevenue : 0,
      costBreakdown: {
        materials: totalMaterialCost,
        energy: totalEnergyCost,
        labor: totalLaborCost,
        maintenance: totalMaintenanceCost,
        overhead: totalOverheadCost,
        depreciation: totalDepreciation
      },
      efficiency: {
        materialEfficiency: relevantMetrics.length > 0 ? 
          relevantMetrics.reduce((sum, m) => sum + m.efficiency, 0) / relevantMetrics.length : 0,
        energyEfficiency: this.calculateEnergyEfficiency(relevantMetrics),
        timeEfficiency: this.calculateTimeEfficiency(relevantMetrics),
        qualityEfficiency: relevantMetrics.length > 0 ?
          relevantMetrics.reduce((sum, m) => sum + m.qualityScore, 0) / relevantMetrics.length : 0
      },
      trends: {
        revenueGrowth: previousRevenue > 0 ? (totalRevenue - previousRevenue) / previousRevenue : 0,
        costGrowth: previousCosts > 0 ? (totalCosts - previousCosts) / previousCosts : 0,
        profitGrowth: previousProfit > 0 ? ((totalRevenue - totalCosts) - previousProfit) / previousProfit : 0,
        efficiencyGrowth: this.calculateEfficiencyGrowth(relevantMetrics, previousMetrics)
      }
    };
  }

  private calculateEnergyEfficiency(metrics: ProductionMetrics[]): number {
    if (metrics.length === 0) return 0;
    
    const averageEnergyPerGram = metrics.reduce((sum, m) => 
      sum + (m.energyCost / m.materialUsed), 0) / metrics.length;
    
    const benchmarkEnergyPerGram = 0.5; // kWh per gram benchmark
    return Math.min(100, (benchmarkEnergyPerGram / averageEnergyPerGram) * 100);
  }

  private calculateTimeEfficiency(metrics: ProductionMetrics[]): number {
    if (metrics.length === 0) return 0;
    
    const averageTimePerGram = metrics.reduce((sum, m) => {
      if (!m.endTime) return sum;
      const duration = (m.endTime.getTime() - m.startTime.getTime()) / (1000 * 60 * 60);
      return sum + (duration / m.materialUsed);
    }, 0) / metrics.length;
    
    const benchmarkTimePerGram = 0.5; // hours per gram benchmark
    return Math.min(100, (benchmarkTimePerGram / averageTimePerGram) * 100);
  }

  private calculateEfficiencyGrowth(current: ProductionMetrics[], previous: ProductionMetrics[]): number {
    const currentAvgEfficiency = current.length > 0 ? 
      current.reduce((sum, m) => sum + m.efficiency, 0) / current.length : 0;
    const previousAvgEfficiency = previous.length > 0 ? 
      previous.reduce((sum, m) => sum + m.efficiency, 0) / previous.length : 0;
    
    return previousAvgEfficiency > 0 ? 
      (currentAvgEfficiency - previousAvgEfficiency) / previousAvgEfficiency : 0;
  }

  private analyzeMetrics(printerId: string): void {
    const metrics = this.metrics.get(printerId) || [];
    if (metrics.length < 10) return; // Need sufficient data

    const recentMetrics = metrics.slice(-30); // Last 30 jobs
    this.generateOptimizationRecommendations(printerId, recentMetrics);
  }

  private generateOptimizationRecommendations(printerId: string, metrics: ProductionMetrics[]): void {
    const recommendations: OptimizationRecommendation[] = [];

    // Material efficiency analysis
    const avgMaterialEfficiency = metrics.reduce((sum, m) => sum + m.efficiency, 0) / metrics.length;
    if (avgMaterialEfficiency < 85) {
      recommendations.push({
        id: `material_opt_${printerId}_${Date.now()}`,
        title: 'Optimize Material Usage',
        description: `Material efficiency is ${avgMaterialEfficiency.toFixed(1)}%. Target: 90%+`,
        category: OptimizationType.MATERIAL_USAGE,
        priority: avgMaterialEfficiency < 75 ? 'critical' : 'high',
        estimatedSavings: (90 - avgMaterialEfficiency) * 100,
        implementationCost: 500,
        paybackPeriod: 15,
        confidence: 0.85,
        actions: [
          'Review and optimize infill settings',
          'Implement adaptive layer heights',
          'Reduce support material usage',
          'Optimize part orientation'
        ],
        metrics: ['material_efficiency', 'material_cost', 'waste_percentage'],
        timeline: 30,
        dependencies: []
      });
    }

    // Quality analysis
    const avgQuality = metrics.reduce((sum, m) => sum + m.qualityScore, 0) / metrics.length;
    if (avgQuality < 90) {
      recommendations.push({
        id: `quality_opt_${printerId}_${Date.now()}`,
        title: 'Improve Print Quality',
        description: `Quality score is ${avgQuality.toFixed(1)}%. Target: 95%+`,
        category: OptimizationType.QUALITY_IMPROVEMENT,
        priority: avgQuality < 80 ? 'critical' : 'high',
        estimatedSavings: (95 - avgQuality) * 50,
        implementationCost: 800,
        paybackPeriod: 20,
        confidence: 0.80,
        actions: [
          'Calibrate print bed leveling',
          'Optimize temperature settings',
          'Improve cooling configuration',
          'Regular maintenance schedule'
        ],
        metrics: ['quality_score', 'failure_rate', 'rework_percentage'],
        timeline: 45,
        dependencies: ['maintenance_schedule']
      });
    }

    // Profit margin analysis
    const avgProfit = metrics.reduce((sum, m) => sum + m.profit, 0) / metrics.length;
    const avgRevenue = metrics.reduce((sum, m) => sum + m.revenue, 0) / metrics.length;
    const profitMargin = avgRevenue > 0 ? avgProfit / avgRevenue : 0;
    
    if (profitMargin < 0.35) {
      recommendations.push({
        id: `pricing_opt_${printerId}_${Date.now()}`,
        title: 'Optimize Pricing Strategy',
        description: `Profit margin is ${(profitMargin * 100).toFixed(1)}%. Target: 35%+`,
        category: OptimizationType.PRICING_OPTIMIZATION,
        priority: profitMargin < 0.20 ? 'critical' : 'medium',
        estimatedSavings: (0.35 - profitMargin) * avgRevenue * 30,
        implementationCost: 200,
        paybackPeriod: 5,
        confidence: 0.90,
        actions: [
          'Implement dynamic pricing model',
          'Review competitor pricing',
          'Add value-based pricing tiers',
          'Optimize volume discounts'
        ],
        metrics: ['profit_margin', 'average_order_value', 'customer_retention'],
        timeline: 14,
        dependencies: []
      });
    }

    // Store recommendations
    recommendations.forEach(rec => {
      this.recommendations.set(rec.id, rec);
    });

    if (recommendations.length > 0) {
      this.emit('recommendationsGenerated', printerId, recommendations);
    }
  }

  public getOptimizationRecommendations(
    printerId?: string,
    category?: OptimizationType,
    priority?: string
  ): OptimizationRecommendation[] {
    let recommendations = Array.from(this.recommendations.values());

    if (printerId) {
      recommendations = recommendations.filter(r => 
        r.id.includes(printerId));
    }

    if (category) {
      recommendations = recommendations.filter(r => r.category === category);
    }

    if (priority) {
      recommendations = recommendations.filter(r => r.priority === priority);
    }

    return recommendations.sort((a, b) => {
      const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      const aPriority = priorityOrder[a.priority as keyof typeof priorityOrder];
      const bPriority = priorityOrder[b.priority as keyof typeof priorityOrder];
      
      if (aPriority !== bPriority) {
        return bPriority - aPriority;
      }
      
      return b.estimatedSavings - a.estimatedSavings;
    });
  }

  private startContinuousAnalysis(): void {
    this.analysisInterval = setInterval(() => {
      this.runOptimizationCycle();
    }, 3600000); // Run every hour
  }

  private runOptimizationCycle(): void {
    for (const [printerId] of this.metrics) {
      this.analyzeMetrics(printerId);
    }
    
    this.optimizeActiveStrategies();
    this.updateMarketFactors();
    
    this.emit('optimizationCycleComplete');
  }

  private optimizeActiveStrategies(): void {
    for (const [strategyId, strategy] of this.strategies) {
      if (!strategy.isActive) continue;

      // Simulate optimization algorithm
      const improvement = this.simulateOptimization(strategy);
      
      if (improvement > 0) {
        strategy.actualImpact = (strategy.actualImpact || 0) + improvement;
        this.emit('strategyImproved', strategyId, improvement);
      }
    }
  }

  private simulateOptimization(strategy: OptimizationStrategy): number {
    // Simplified optimization simulation
    let totalImprovement = 0;

    strategy.parameters.variables.forEach(variable => {
      const currentValue = variable.currentValue;
      const optimalDirection = variable.impact > 0 ? 1 : -1;
      const step = variable.step * optimalDirection;
      const newValue = Math.max(variable.minValue, 
                      Math.min(variable.maxValue, currentValue + step));
      
      if (newValue !== currentValue) {
        variable.currentValue = newValue;
        totalImprovement += Math.abs(variable.impact * step);
      }
    });

    return totalImprovement;
  }

  private updateMarketFactors(): void {
    for (const [modelId, model] of this.pricingModels) {
      if (!model.dynamicPricing) continue;

      model.marketFactors.forEach(factor => {
        // Simulate market factor updates
        const randomChange = (Math.random() - 0.5) * 0.1;
        factor.currentValue = Math.max(0.5, Math.min(2.0, factor.currentValue + randomChange));
      });
    }
  }

  public shutdown(): void {
    if (this.analysisInterval) {
      clearInterval(this.analysisInterval);
    }
  }
}