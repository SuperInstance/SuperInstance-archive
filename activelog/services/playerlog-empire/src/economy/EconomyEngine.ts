/**
 * CCC-Based Economy Simulation Engine
 * Comprehensive economic modeling with business cycles and market dynamics
 */

import { EventEmitter } from 'events';
import { 
  EconomyState, 
  EconomicCycle, 
  Industry, 
  DifficultyLevel,
  Company,
  Property
} from '../types/game-types';

export interface MarketConditions {
  demandLevels: Record<Industry, number>;
  supplyConstraints: Record<Industry, number>;
  priceIndices: Record<Industry, number>;
  competitionLevel: Record<Industry, number>;
  barriers: Record<Industry, number>;
  regulations: Record<Industry, number>;
}

export interface EconomicIndicators {
  leadingIndicators: {
    stockMarketPerformance: number;
    businessInvestment: number;
    consumerConfidence: number;
    manufacturingIndex: number;
  };
  laggingIndicators: {
    unemploymentRate: number;
    cpiInflation: number;
    corporateProfits: number;
    averageWages: number;
  };
  coincidentIndicators: {
    industrialProduction: number;
    retailSales: number;
    personalIncome: number;
    gdpGrowth: number;
  };
}

export class EconomyEngine extends EventEmitter {
  private state: EconomyState;
  private marketConditions: MarketConditions;
  private indicators: EconomicIndicators;
  private cycleTimer?: NodeJS.Timeout;
  private volatilityLevel: number;
  private shockProbability: number;
  
  // CCC Model Parameters (Cash Conversion Cycle)
  private cccFactors = {
    receivablesCollection: 45, // Days to collect receivables
    inventoryTurnover: 60, // Days inventory on hand
    payablesPeriod: 30, // Days to pay suppliers
    seasonality: 0.1, // Seasonal variation factor
    industryMultipliers: {
      [Industry.TECHNOLOGY]: 0.8, // Faster cash cycles
      [Industry.MANUFACTURING]: 1.2, // Slower cycles
      [Industry.RETAIL]: 0.9,
      [Industry.HEALTHCARE]: 1.1,
      [Industry.FINANCE]: 0.7,
      [Industry.REAL_ESTATE]: 1.5,
      [Industry.EDUCATION]: 1.0,
      [Industry.ENERGY]: 1.3,
      [Industry.TRANSPORTATION]: 1.1,
      [Industry.ENTERTAINMENT]: 0.9
    }
  };

  constructor(private difficulty: DifficultyLevel) {
    super();
    
    this.volatilityLevel = this.getVolatilityByDifficulty(difficulty);
    this.shockProbability = this.getShockProbabilityByDifficulty(difficulty);
    
    this.state = this.initializeEconomyState();
    this.marketConditions = this.initializeMarketConditions();
    this.indicators = this.initializeIndicators();
  }

  /**
   * Initialize economy with base state
   */
  initialize(): void {
    console.log(`🏦 Initializing Economy Engine (${this.difficulty} difficulty)`);
    
    // Start economic cycle simulation
    this.startCycleSimulation();
    
    // Process initial economic conditions
    this.updateEconomicCycle();
    
    this.emit('economy:initialized', this.state);
  }

  /**
   * Initialize base economy state
   */
  private initializeEconomyState(): EconomyState {
    return {
      gdpGrowth: 2.5 + (Math.random() - 0.5) * 2, // 1.5% to 3.5%
      inflationRate: 2.0 + (Math.random() - 0.5) * 1, // 1.5% to 2.5%
      unemploymentRate: 4.0 + Math.random() * 3, // 4% to 7%
      interestRate: 3.0 + Math.random() * 4, // 3% to 7%
      stockMarketIndex: 10000 + Math.random() * 2000, // Base market index
      realEstateIndex: 100 + Math.random() * 20, // Property price index
      
      economicCycle: EconomicCycle.EXPANSION,
      sectorPerformance: this.initializeSectorPerformance(),
      
      creditAvailability: 70 + Math.random() * 30, // 70-100% availability
      businessConfidence: 60 + Math.random() * 40, // 60-100 confidence index
      consumerSpending: 80 + Math.random() * 20, // 80-100% of normal
      
      communityFund: 0
    };
  }

  /**
   * Initialize market conditions for all industries
   */
  private initializeMarketConditions(): MarketConditions {
    const industries = Object.values(Industry);
    
    return {
      demandLevels: this.generateIndustryData(industries, 70, 130),
      supplyConstraints: this.generateIndustryData(industries, 80, 120),
      priceIndices: this.generateIndustryData(industries, 90, 110),
      competitionLevel: this.generateIndustryData(industries, 60, 140),
      barriers: this.generateIndustryData(industries, 20, 80),
      regulations: this.generateIndustryData(industries, 30, 90)
    };
  }

  /**
   * Generate economic indicators
   */
  private initializeIndicators(): EconomicIndicators {
    return {
      leadingIndicators: {
        stockMarketPerformance: 100 + (Math.random() - 0.5) * 20,
        businessInvestment: 100 + (Math.random() - 0.5) * 15,
        consumerConfidence: 100 + (Math.random() - 0.5) * 30,
        manufacturingIndex: 100 + (Math.random() - 0.5) * 25
      },
      laggingIndicators: {
        unemploymentRate: this.state.unemploymentRate,
        cpiInflation: this.state.inflationRate,
        corporateProfits: 100 + (Math.random() - 0.5) * 40,
        averageWages: 50000 + Math.random() * 30000
      },
      coincidentIndicators: {
        industrialProduction: 100 + (Math.random() - 0.5) * 20,
        retailSales: 100 + (Math.random() - 0.5) * 25,
        personalIncome: 100 + (Math.random() - 0.5) * 15,
        gdpGrowth: this.state.gdpGrowth
      }
    };
  }

  /**
   * Start economic cycle simulation
   */
  private startCycleSimulation(): void {
    const updateInterval = this.getUpdateIntervalByDifficulty();
    
    this.cycleTimer = setInterval(() => {
      this.processEconomicUpdate();
    }, updateInterval);
  }

  /**
   * Process regular economic updates
   */
  private processEconomicUpdate(): void {
    // Update business cycle
    this.updateEconomicCycle();
    
    // Update market conditions
    this.updateMarketConditions();
    
    // Update economic indicators
    this.updateEconomicIndicators();
    
    // Check for economic shocks
    if (Math.random() < this.shockProbability) {
      this.processEconomicShock();
    }
    
    // Emit update event
    this.emit('economy:updated', this.state);
    
    console.log(`📊 Economy Update: GDP ${this.state.gdpGrowth.toFixed(1)}%, Inflation ${this.state.inflationRate.toFixed(1)}%, Cycle: ${this.state.economicCycle}`);
  }

  /**
   * Update economic cycle based on indicators
   */
  private updateEconomicCycle(): void {
    const cycleProbabilities = this.calculateCycleTransitionProbabilities();
    const random = Math.random();
    
    let cumulativeProbability = 0;
    const cycles = Object.values(EconomicCycle);
    
    for (const cycle of cycles) {
      cumulativeProbability += cycleProbabilities[cycle] || 0;
      if (random <= cumulativeProbability) {
        if (cycle !== this.state.economicCycle) {
          console.log(`🔄 Economic cycle transition: ${this.state.economicCycle} → ${cycle}`);
          this.state.economicCycle = cycle;
          this.processCycleTransition(cycle);
        }
        break;
      }
    }
  }

  /**
   * Calculate probabilities for cycle transitions
   */
  private calculateCycleTransitionProbabilities(): Record<EconomicCycle, number> {
    const currentCycle = this.state.economicCycle;
    const baseProbs = { stay: 0.85, transition: 0.15 };
    
    // Adjust probabilities based on economic indicators
    const gdpTrend = this.state.gdpGrowth > 2.5 ? 'positive' : 'negative';
    const inflationTrend = this.state.inflationRate > 3.0 ? 'high' : 'normal';
    const unemploymentTrend = this.state.unemploymentRate > 6.0 ? 'high' : 'normal';
    
    switch (currentCycle) {
      case EconomicCycle.RECESSION:
        return {
          [EconomicCycle.RECESSION]: gdpTrend === 'negative' ? 0.8 : 0.3,
          [EconomicCycle.RECOVERY]: gdpTrend === 'positive' ? 0.6 : 0.2,
          [EconomicCycle.EXPANSION]: 0.1,
          [EconomicCycle.PEAK]: 0.05
        };
        
      case EconomicCycle.RECOVERY:
        return {
          [EconomicCycle.RECESSION]: gdpTrend === 'negative' ? 0.3 : 0.05,
          [EconomicCycle.RECOVERY]: 0.5,
          [EconomicCycle.EXPANSION]: gdpTrend === 'positive' ? 0.4 : 0.2,
          [EconomicCycle.PEAK]: 0.05
        };
        
      case EconomicCycle.EXPANSION:
        return {
          [EconomicCycle.RECESSION]: 0.05,
          [EconomicCycle.RECOVERY]: 0.1,
          [EconomicCycle.EXPANSION]: inflationTrend === 'high' ? 0.3 : 0.7,
          [EconomicCycle.PEAK]: inflationTrend === 'high' ? 0.5 : 0.15
        };
        
      case EconomicCycle.PEAK:
        return {
          [EconomicCycle.RECESSION]: inflationTrend === 'high' ? 0.4 : 0.2,
          [EconomicCycle.RECOVERY]: 0.05,
          [EconomicCycle.EXPANSION]: 0.25,
          [EconomicCycle.PEAK]: 0.3
        };
        
      default:
        return {
          [EconomicCycle.RECESSION]: 0.25,
          [EconomicCycle.RECOVERY]: 0.25,
          [EconomicCycle.EXPANSION]: 0.25,
          [EconomicCycle.PEAK]: 0.25
        };
    }
  }

  /**
   * Process cycle transition effects
   */
  private processCycleTransition(newCycle: EconomicCycle): void {
    switch (newCycle) {
      case EconomicCycle.RECESSION:
        this.state.gdpGrowth = Math.max(-2, this.state.gdpGrowth - 2 - Math.random() * 2);
        this.state.unemploymentRate = Math.min(12, this.state.unemploymentRate + 1 + Math.random() * 2);
        this.state.businessConfidence = Math.max(20, this.state.businessConfidence - 20 - Math.random() * 20);
        this.state.creditAvailability = Math.max(20, this.state.creditAvailability - 30);
        break;
        
      case EconomicCycle.RECOVERY:
        this.state.gdpGrowth = Math.max(-0.5, this.state.gdpGrowth + 0.5 + Math.random() * 1);
        this.state.businessConfidence = Math.min(100, this.state.businessConfidence + 10 + Math.random() * 15);
        this.state.creditAvailability = Math.min(100, this.state.creditAvailability + 15);
        break;
        
      case EconomicCycle.EXPANSION:
        this.state.gdpGrowth = Math.min(6, this.state.gdpGrowth + 1 + Math.random() * 2);
        this.state.unemploymentRate = Math.max(3, this.state.unemploymentRate - 0.5 - Math.random() * 1);
        this.state.businessConfidence = Math.min(100, this.state.businessConfidence + 15 + Math.random() * 10);
        this.state.stockMarketIndex *= (1 + (Math.random() * 0.1));
        break;
        
      case EconomicCycle.PEAK:
        this.state.inflationRate = Math.min(8, this.state.inflationRate + 1 + Math.random() * 2);
        this.state.interestRate = Math.min(12, this.state.interestRate + 1 + Math.random() * 2);
        this.state.businessConfidence = Math.max(50, this.state.businessConfidence - 5 - Math.random() * 10);
        break;
    }
    
    // Update sector performance based on cycle
    this.updateSectorPerformanceForCycle(newCycle);
    
    this.emit('cycle:changed', {
      newCycle,
      state: this.state,
      impacts: this.calculateCycleImpacts(newCycle)
    });
  }

  /**
   * Update market conditions
   */
  private updateMarketConditions(): void {
    const volatility = this.volatilityLevel * (0.5 + Math.random());
    
    Object.values(Industry).forEach(industry => {
      // Update demand based on economic cycle and consumer spending
      const demandMultiplier = this.getDemandMultiplier(industry);
      this.marketConditions.demandLevels[industry] *= (1 + (Math.random() - 0.5) * volatility * demandMultiplier);
      this.marketConditions.demandLevels[industry] = Math.max(20, Math.min(200, this.marketConditions.demandLevels[industry]));
      
      // Update supply constraints
      this.marketConditions.supplyConstraints[industry] *= (1 + (Math.random() - 0.5) * volatility * 0.5);
      this.marketConditions.supplyConstraints[industry] = Math.max(50, Math.min(150, this.marketConditions.supplyConstraints[industry]));
      
      // Update price indices based on supply/demand
      const demandSupplyRatio = this.marketConditions.demandLevels[industry] / this.marketConditions.supplyConstraints[industry];
      const priceChange = (demandSupplyRatio - 1) * 0.1 + (Math.random() - 0.5) * 0.05;
      this.marketConditions.priceIndices[industry] *= (1 + priceChange);
      this.marketConditions.priceIndices[industry] = Math.max(50, Math.min(200, this.marketConditions.priceIndices[industry]));
    });
  }

  /**
   * Calculate Cash Conversion Cycle for a company
   */
  calculateCCC(company: Company): {
    daysReceivables: number;
    daysInventory: number;
    daysPayables: number;
    cashConversionCycle: number;
    workingCapitalNeed: number;
    industryBenchmark: number;
    performance: 'excellent' | 'good' | 'average' | 'poor' | 'critical';
  } {
    // Base CCC components
    const industryMultiplier = this.cccFactors.industryMultipliers[company.industry] || 1.0;
    const digitalBonus = (company.digitalTransformation / 100) * 0.3; // 30% improvement potential
    const scaleBonus = Math.min(0.2, company.employees / 5000); // Large companies are more efficient
    
    // Calculate days receivables (how long to collect money)
    const daysReceivables = Math.max(15, 
      this.cccFactors.receivablesCollection * 
      industryMultiplier * 
      (1 - digitalBonus) * 
      (1 - scaleBonus) *
      (1 + (Math.random() - 0.5) * 0.2) // ±10% variation
    );
    
    // Calculate days inventory (how long inventory sits)
    const daysInventory = Math.max(10,
      this.cccFactors.inventoryTurnover * 
      industryMultiplier * 
      (1 - digitalBonus * 0.5) * // Digital helps less with physical inventory
      (1 - scaleBonus) *
      (1 + (Math.random() - 0.5) * 0.3) // ±15% variation
    );
    
    // Calculate days payables (how long to pay suppliers)
    const daysPayables = Math.max(15,
      this.cccFactors.payablesPeriod * 
      (1 + scaleBonus * 2) * // Larger companies get better payment terms
      (1 + (company.creditScore || 650) / 1000) * // Better credit = better terms
      (1 + (Math.random() - 0.5) * 0.15) // ±7.5% variation
    );
    
    // Cash Conversion Cycle = Days Receivables + Days Inventory - Days Payables
    const cashConversionCycle = daysReceivables + daysInventory - daysPayables;
    
    // Calculate working capital need
    const dailyRevenue = company.revenue / 365;
    const workingCapitalNeed = cashConversionCycle * dailyRevenue;
    
    // Industry benchmark
    const industryBenchmark = (this.cccFactors.receivablesCollection + this.cccFactors.inventoryTurnover - this.cccFactors.payablesPeriod) * industryMultiplier;
    
    // Performance rating
    let performance: 'excellent' | 'good' | 'average' | 'poor' | 'critical';
    const benchmarkRatio = cashConversionCycle / industryBenchmark;
    
    if (benchmarkRatio < 0.7) performance = 'excellent';
    else if (benchmarkRatio < 0.9) performance = 'good';
    else if (benchmarkRatio < 1.1) performance = 'average';
    else if (benchmarkRatio < 1.4) performance = 'poor';
    else performance = 'critical';
    
    return {
      daysReceivables: Math.round(daysReceivables),
      daysInventory: Math.round(daysInventory),
      daysPayables: Math.round(daysPayables),
      cashConversionCycle: Math.round(cashConversionCycle),
      workingCapitalNeed: Math.round(workingCapitalNeed),
      industryBenchmark: Math.round(industryBenchmark),
      performance
    };
  }

  /**
   * Process economic shock events
   */
  private processEconomicShock(): void {
    const shockTypes = [
      'market_crash',
      'oil_crisis',
      'tech_bubble',
      'credit_crunch',
      'supply_shortage',
      'geopolitical_crisis',
      'pandemic',
      'natural_disaster'
    ];
    
    const shockType = shockTypes[Math.floor(Math.random() * shockTypes.length)];
    const intensity = Math.random() * 0.3 + 0.1; // 10-40% impact
    
    console.log(`⚡ Economic shock: ${shockType} (intensity: ${(intensity * 100).toFixed(1)}%)`);
    
    this.applyEconomicShock(shockType, intensity);
    
    this.emit('economic:shock', {
      type: shockType,
      intensity,
      state: this.state,
      duration: Math.floor(Math.random() * 12) + 3 // 3-15 months
    });
  }

  /**
   * Apply economic shock effects
   */
  private applyEconomicShock(shockType: string, intensity: number): void {
    switch (shockType) {
      case 'market_crash':
        this.state.stockMarketIndex *= (1 - intensity);
        this.state.businessConfidence *= (1 - intensity * 0.8);
        this.state.creditAvailability *= (1 - intensity * 0.6);
        break;
        
      case 'oil_crisis':
        this.state.inflationRate += intensity * 5;
        this.marketConditions.priceIndices[Industry.ENERGY] *= (1 + intensity * 2);
        this.marketConditions.priceIndices[Industry.TRANSPORTATION] *= (1 + intensity * 1.5);
        break;
        
      case 'credit_crunch':
        this.state.creditAvailability *= (1 - intensity * 1.2);
        this.state.interestRate += intensity * 6;
        break;
        
      case 'pandemic':
        this.state.gdpGrowth -= intensity * 8;
        this.state.unemploymentRate += intensity * 6;
        this.marketConditions.demandLevels[Industry.HEALTHCARE] *= (1 + intensity * 2);
        this.marketConditions.demandLevels[Industry.ENTERTAINMENT] *= (1 - intensity * 1.5);
        break;
    }
    
    // Apply general effects
    this.state.gdpGrowth -= intensity * 3;
    this.state.businessConfidence *= (1 - intensity * 0.5);
    this.state.consumerSpending *= (1 - intensity * 0.4);
  }

  /**
   * Get market forecast for planning
   */
  getMarketForecast(industry: Industry, months: number = 12): {
    demandForecast: number[];
    priceForecast: number[];
    competitionForecast: number[];
    confidence: number;
    keyFactors: string[];
  } {
    const currentDemand = this.marketConditions.demandLevels[industry];
    const currentPrice = this.marketConditions.priceIndices[industry];
    const currentCompetition = this.marketConditions.competitionLevel[industry];
    
    const demandForecast: number[] = [];
    const priceForecast: number[] = [];
    const competitionForecast: number[] = [];
    
    // Base trend calculation
    const cycleMultiplier = this.getCycleForecastMultiplier();
    const industryTrend = this.getIndustryTrend(industry);
    
    for (let month = 1; month <= months; month++) {
      // Demand forecast with seasonality
      const seasonalFactor = 1 + Math.sin((month / 12) * 2 * Math.PI) * this.cccFactors.seasonality;
      const demandGrowth = (industryTrend * cycleMultiplier + (Math.random() - 0.5) * 0.1) * (month / 12);
      demandForecast.push(currentDemand * (1 + demandGrowth) * seasonalFactor);
      
      // Price forecast
      const priceGrowth = (this.state.inflationRate / 100 + industryTrend * 0.5) * (month / 12);
      priceForecast.push(currentPrice * (1 + priceGrowth));
      
      // Competition forecast
      const competitionGrowth = Math.max(-0.2, industryTrend * 0.3) * (month / 12);
      competitionForecast.push(currentCompetition * (1 + competitionGrowth));
    }
    
    const confidence = Math.max(0.3, 0.9 - (this.volatilityLevel * 2));
    
    return {
      demandForecast,
      priceForecast,
      competitionForecast,
      confidence,
      keyFactors: this.getKeyMarketFactors(industry)
    };
  }

  /**
   * Helper methods
   */
  private getVolatilityByDifficulty(difficulty: DifficultyLevel): number {
    const volatilityMap = {
      [DifficultyLevel.KID]: 0.02,
      [DifficultyLevel.TEEN]: 0.05,
      [DifficultyLevel.ADULT]: 0.08,
      [DifficultyLevel.BUSINESS]: 0.12,
      [DifficultyLevel.MBA]: 0.15
    };
    return volatilityMap[difficulty] || 0.08;
  }

  private getShockProbabilityByDifficulty(difficulty: DifficultyLevel): number {
    const shockMap = {
      [DifficultyLevel.KID]: 0.001,
      [DifficultyLevel.TEEN]: 0.003,
      [DifficultyLevel.ADULT]: 0.005,
      [DifficultyLevel.BUSINESS]: 0.008,
      [DifficultyLevel.MBA]: 0.012
    };
    return shockMap[difficulty] || 0.005;
  }

  private getUpdateIntervalByDifficulty(): number {
    const intervalMap = {
      [DifficultyLevel.KID]: 60000, // 1 minute
      [DifficultyLevel.TEEN]: 45000, // 45 seconds
      [DifficultyLevel.ADULT]: 30000, // 30 seconds
      [DifficultyLevel.BUSINESS]: 20000, // 20 seconds
      [DifficultyLevel.MBA]: 15000 // 15 seconds
    };
    return intervalMap[this.difficulty] || 30000;
  }

  private initializeSectorPerformance(): Record<Industry, number> {
    const performance: Record<Industry, number> = {} as Record<Industry, number>;
    Object.values(Industry).forEach(industry => {
      performance[industry] = 95 + Math.random() * 10; // 95-105% of baseline
    });
    return performance;
  }

  private generateIndustryData(industries: Industry[], min: number, max: number): Record<Industry, number> {
    const data: Record<Industry, number> = {} as Record<Industry, number>;
    industries.forEach(industry => {
      data[industry] = min + Math.random() * (max - min);
    });
    return data;
  }

  private getDemandMultiplier(industry: Industry): number {
    const cycleMultipliers = {
      [EconomicCycle.RECESSION]: 0.7,
      [EconomicCycle.RECOVERY]: 0.9,
      [EconomicCycle.EXPANSION]: 1.2,
      [EconomicCycle.PEAK]: 1.0
    };
    
    const spendingEffect = this.state.consumerSpending / 100;
    return (cycleMultipliers[this.state.economicCycle] || 1.0) * spendingEffect;
  }

  private updateSectorPerformanceForCycle(cycle: EconomicCycle): void {
    const adjustments = {
      [EconomicCycle.RECESSION]: {
        [Industry.TECHNOLOGY]: -0.05,
        [Industry.FINANCE]: -0.15,
        [Industry.REAL_ESTATE]: -0.20,
        [Industry.HEALTHCARE]: 0.05,
        [Industry.EDUCATION]: -0.05
      },
      [EconomicCycle.RECOVERY]: {
        [Industry.TECHNOLOGY]: 0.10,
        [Industry.MANUFACTURING]: 0.08,
        [Industry.FINANCE]: 0.05
      },
      [EconomicCycle.EXPANSION]: {
        [Industry.REAL_ESTATE]: 0.15,
        [Industry.RETAIL]: 0.10,
        [Industry.ENTERTAINMENT]: 0.12
      },
      [EconomicCycle.PEAK]: {
        [Industry.ENERGY]: 0.08,
        [Industry.FINANCE]: -0.05
      }
    };

    const cycleAdjustments = adjustments[cycle] || {};
    Object.entries(cycleAdjustments).forEach(([industry, adjustment]) => {
      this.state.sectorPerformance[industry as Industry] *= (1 + adjustment);
      this.state.sectorPerformance[industry as Industry] = Math.max(50, Math.min(200, this.state.sectorPerformance[industry as Industry]));
    });
  }

  private updateEconomicIndicators(): void {
    const trend = (Math.random() - 0.5) * 0.02;
    
    // Leading indicators
    this.indicators.leadingIndicators.stockMarketPerformance *= (1 + trend * 2);
    this.indicators.leadingIndicators.businessInvestment *= (1 + trend);
    this.indicators.leadingIndicators.consumerConfidence *= (1 + trend * 1.5);
    
    // Update state based on indicators
    this.state.stockMarketIndex = this.indicators.leadingIndicators.stockMarketPerformance * 100;
    this.state.businessConfidence = this.indicators.leadingIndicators.consumerConfidence;
  }

  private calculateCycleImpacts(cycle: EconomicCycle): Record<string, number> {
    return {
      businessFormation: cycle === EconomicCycle.EXPANSION ? 1.5 : cycle === EconomicCycle.RECESSION ? 0.5 : 1.0,
      creditCost: cycle === EconomicCycle.PEAK ? 1.8 : cycle === EconomicCycle.RECESSION ? 2.5 : 1.0,
      propertyValues: cycle === EconomicCycle.EXPANSION ? 1.3 : cycle === EconomicCycle.RECESSION ? 0.7 : 1.0,
      wages: cycle === EconomicCycle.EXPANSION ? 1.2 : cycle === EconomicCycle.RECESSION ? 0.9 : 1.0
    };
  }

  private getCycleForecastMultiplier(): number {
    const multipliers = {
      [EconomicCycle.RECESSION]: -0.1,
      [EconomicCycle.RECOVERY]: 0.05,
      [EconomicCycle.EXPANSION]: 0.1,
      [EconomicCycle.PEAK]: 0.02
    };
    return multipliers[this.state.economicCycle] || 0;
  }

  private getIndustryTrend(industry: Industry): number {
    const trends = {
      [Industry.TECHNOLOGY]: 0.15,
      [Industry.HEALTHCARE]: 0.08,
      [Industry.EDUCATION]: 0.05,
      [Industry.ENERGY]: 0.03,
      [Industry.MANUFACTURING]: 0.02,
      [Industry.FINANCE]: 0.04,
      [Industry.RETAIL]: -0.02,
      [Industry.REAL_ESTATE]: 0.06,
      [Industry.TRANSPORTATION]: 0.01,
      [Industry.ENTERTAINMENT]: 0.07
    };
    return trends[industry] || 0;
  }

  private getKeyMarketFactors(industry: Industry): string[] {
    const factors = {
      [Industry.TECHNOLOGY]: ['Innovation pace', 'Regulatory environment', 'Talent availability', 'Investment climate'],
      [Industry.HEALTHCARE]: ['Aging population', 'Insurance coverage', 'Regulatory approval', 'Research funding'],
      [Industry.EDUCATION]: ['Government funding', 'Technology adoption', 'Demographics', 'Economic conditions'],
      [Industry.RETAIL]: ['Consumer spending', 'E-commerce growth', 'Supply chain', 'Competition']
    };
    return factors[industry] || ['Market demand', 'Competition', 'Regulations', 'Economic conditions'];
  }

  // Public methods
  public getState(): EconomyState { return { ...this.state }; }
  public getMarketConditions(): MarketConditions { return { ...this.marketConditions }; }
  public getIndicators(): EconomicIndicators { return { ...this.indicators }; }
  public stop(): void { if (this.cycleTimer) clearInterval(this.cycleTimer); }
}