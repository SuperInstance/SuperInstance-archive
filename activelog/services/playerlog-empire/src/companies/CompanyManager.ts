/**
 * Company Acquisition and Management System
 * Handles company creation, acquisition, mergers, and valuation
 */

import { EventEmitter } from 'events';
import {
  Company,
  Player,
  Industry,
  CompanyType,
  Equipment,
  Product,
  Contract,
  DifficultyLevel
} from '../types/game-types';
import { EconomyEngine } from '../economy/EconomyEngine';

export interface CompanyValuation {
  bookValue: number;
  marketValue: number;
  liquidationValue: number;
  intrinsicValue: number;
  synergisticValue: number;
  multiples: {
    priceToEarnings: number;
    priceToBook: number;
    priceToSales: number;
    evToEbitda: number;
    enterpriseValue: number;
  };
  dcfAnalysis: {
    presentValue: number;
    terminalValue: number;
    wacc: number; // Weighted Average Cost of Capital
    growthRate: number;
    freeGashFlow: number[];
  };
  comparableCompanies: {
    averageMultiples: Record<string, number>;
    industryMedian: number;
    premiumDiscount: number;
  };
}

export interface AcquisitionOffer {
  id: string;
  buyerId: string;
  sellerId: string;
  targetCompanyId: string;
  offerPrice: number;
  offerType: 'cash' | 'stock' | 'mixed';
  stockPercentage?: number;
  contingencies: string[];
  dueDiligenceCompleted: boolean;
  regulatoryApproval: boolean;
  financingSecured: boolean;
  timeline: {
    offerDate: Date;
    responseDeadline: Date;
    expectedClosing: Date;
  };
  terms: {
    earnOut: number;
    employmentContracts: boolean;
    nonCompeteClause: boolean;
    warrantyPeriod: number; // months
  };
  status: 'pending' | 'accepted' | 'rejected' | 'negotiating' | 'completed' | 'cancelled';
}

export interface MergerSynergy {
  costSynergies: {
    duplicatedRoles: number;
    sharedResources: number;
    economies: number;
    totalSavings: number;
  };
  revenueSynergies: {
    crossSelling: number;
    marketExpansion: number;
    pricingPower: number;
    totalIncrease: number;
  };
  financialSynergies: {
    taxBenefits: number;
    capitalEfficiency: number;
    debtCapacity: number;
    totalValue: number;
  };
  riskFactors: {
    integrationRisk: number;
    culturalClash: number;
    customerLoss: number;
    regulatoryRisk: number;
    totalRisk: number;
  };
}

export class CompanyManager extends EventEmitter {
  private companies: Map<string, Company> = new Map();
  private acquisitionOffers: Map<string, AcquisitionOffer> = new Map();
  private economyEngine: EconomyEngine;
  private nextCompanyId = 1;

  constructor(economyEngine: EconomyEngine) {
    super();
    this.economyEngine = economyEngine;
    this.generateMarketCompanies();
  }

  /**
   * Create a new company for a player
   */
  createCompany(
    playerId: string, 
    name: string, 
    industry: Industry, 
    type: CompanyType,
    initialCapital: number
  ): Company {
    const companyId = `comp_${this.nextCompanyId++}`;
    
    const company: Company = {
      id: companyId,
      name,
      type,
      industry,
      foundedDate: new Date(),
      
      // Financial starting state
      revenue: 0,
      expenses: initialCapital * 0.1, // 10% monthly burn rate initially
      profit: -initialCapital * 0.1,
      valuation: initialCapital,
      shares: 1000000, // 1M shares
      sharesOwned: type === CompanyType.STARTUP ? 1000000 : Math.floor(1000000 * 0.6), // 60% for non-startups
      
      // Operations
      employees: this.getInitialEmployees(type),
      digitalTransformation: this.getInitialDigitalLevel(industry),
      productionCapacity: 100,
      marketShare: 0,
      
      // Assets
      equipment: [],
      properties: [],
      
      // Status
      isPublic: false,
      isAcquired: false,
      
      // Development
      researchPoints: 0,
      products: [],
      
      // Location
      headquarters: this.getRandomLocation(),
      locations: []
    };

    this.companies.set(companyId, company);
    
    this.emit('company:created', {
      playerId,
      company,
      initialCapital
    });

    console.log(`🏢 Created ${type} company: ${name} in ${industry} industry`);
    return company;
  }

  /**
   * Calculate comprehensive company valuation
   */
  calculateValuation(companyId: string): CompanyValuation {
    const company = this.companies.get(companyId);
    if (!company) {
      throw new Error('Company not found');
    }

    // Book value calculation
    const assets = this.calculateTotalAssets(company);
    const liabilities = this.calculateTotalLiabilities(company);
    const bookValue = assets - liabilities;

    // Market multiples from industry
    const industryMultiples = this.getIndustryMultiples(company.industry);
    const marketValue = this.calculateMarketValue(company, industryMultiples);

    // DCF Analysis
    const dcfAnalysis = this.performDCFAnalysis(company);

    // Liquidation value
    const liquidationValue = assets * 0.6 - liabilities; // 60% asset recovery

    // Intrinsic value (combination of DCF and other factors)
    const intrinsicValue = (dcfAnalysis.presentValue + marketValue) / 2;

    // Synergistic value (potential value in acquisition)
    const synergisticValue = intrinsicValue * (1 + this.calculateSynergyPotential(company));

    // Comparable companies analysis
    const comparableCompanies = this.getComparableAnalysis(company);

    return {
      bookValue,
      marketValue,
      liquidationValue,
      intrinsicValue,
      synergisticValue,
      multiples: this.calculateValuationMultiples(company),
      dcfAnalysis,
      comparableCompanies
    };
  }

  /**
   * Make acquisition offer
   */
  makeAcquisitionOffer(
    buyerId: string,
    targetCompanyId: string,
    offerPrice: number,
    offerType: 'cash' | 'stock' | 'mixed',
    terms: Partial<AcquisitionOffer['terms']> = {}
  ): AcquisitionOffer {
    const company = this.companies.get(targetCompanyId);
    if (!company) {
      throw new Error('Target company not found');
    }

    if (company.isAcquired) {
      throw new Error('Company is already acquired');
    }

    const offerId = `offer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const offer: AcquisitionOffer = {
      id: offerId,
      buyerId,
      sellerId: this.findCompanyOwner(targetCompanyId),
      targetCompanyId,
      offerPrice,
      offerType,
      stockPercentage: offerType === 'mixed' ? 30 : offerType === 'stock' ? 100 : 0,
      contingencies: this.generateContingencies(company),
      dueDiligenceCompleted: false,
      regulatoryApproval: this.requiresRegulatoryApproval(company),
      financingSecured: false,
      timeline: {
        offerDate: new Date(),
        responseDeadline: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        expectedClosing: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000) // 90 days
      },
      terms: {
        earnOut: terms.earnOut || 0,
        employmentContracts: terms.employmentContracts || false,
        nonCompeteClause: terms.nonCompeteClause || true,
        warrantyPeriod: terms.warrantyPeriod || 12
      },
      status: 'pending'
    };

    this.acquisitionOffers.set(offerId, offer);

    this.emit('acquisition:offer', {
      offer,
      valuation: this.calculateValuation(targetCompanyId),
      synergies: this.calculateMergerSynergies(buyerId, targetCompanyId)
    });

    console.log(`💰 Acquisition offer made for ${company.name}: $${offerPrice.toLocaleString()}`);
    return offer;
  }

  /**
   * Process acquisition offer response
   */
  respondToAcquisitionOffer(
    offerId: string, 
    response: 'accept' | 'reject' | 'counter',
    counterOffer?: {
      price: number;
      terms: Partial<AcquisitionOffer['terms']>;
    }
  ): void {
    const offer = this.acquisitionOffers.get(offerId);
    if (!offer) {
      throw new Error('Offer not found');
    }

    switch (response) {
      case 'accept':
        offer.status = 'accepted';
        this.processDueDiligence(offerId);
        break;
        
      case 'reject':
        offer.status = 'rejected';
        this.emit('acquisition:rejected', { offerId, offer });
        break;
        
      case 'counter':
        if (!counterOffer) {
          throw new Error('Counter offer details required');
        }
        
        offer.status = 'negotiating';
        offer.offerPrice = counterOffer.price;
        offer.terms = { ...offer.terms, ...counterOffer.terms };
        
        this.emit('acquisition:counter', { offerId, offer, counterOffer });
        break;
    }

    console.log(`📝 Acquisition offer ${response}: ${offer.id}`);
  }

  /**
   * Complete acquisition
   */
  completeAcquisition(offerId: string): {
    success: boolean;
    acquiredCompany: Company;
    totalCost: number;
    synergies: MergerSynergy;
  } {
    const offer = this.acquisitionOffers.get(offerId);
    if (!offer || offer.status !== 'accepted') {
      throw new Error('Offer not ready for completion');
    }

    const company = this.companies.get(offer.targetCompanyId);
    if (!company) {
      throw new Error('Target company not found');
    }

    // Calculate final costs including fees
    const totalCost = this.calculateTotalAcquisitionCost(offer);

    // Mark company as acquired
    company.isAcquired = true;
    company.acquiredBy = offer.buyerId;

    // Calculate synergies
    const synergies = this.calculateMergerSynergies(offer.buyerId, offer.targetCompanyId);

    // Process integration
    this.processPostAcquisitionIntegration(offer.buyerId, company, synergies);

    offer.status = 'completed';

    this.emit('acquisition:completed', {
      offerId,
      buyerId: offer.buyerId,
      company,
      totalCost,
      synergies
    });

    console.log(`✅ Acquisition completed: ${company.name} acquired for $${totalCost.toLocaleString()}`);
    
    return {
      success: true,
      acquiredCompany: company,
      totalCost,
      synergies
    };
  }

  /**
   * Calculate merger synergies
   */
  calculateMergerSynergies(buyerId: string, targetCompanyId: string): MergerSynergy {
    const targetCompany = this.companies.get(targetCompanyId);
    if (!targetCompany) {
      throw new Error('Target company not found');
    }

    const buyerCompanies = this.getPlayerCompanies(buyerId);
    const buyerRevenue = buyerCompanies.reduce((sum, comp) => sum + comp.revenue, 0);
    const buyerEmployees = buyerCompanies.reduce((sum, comp) => sum + comp.employees, 0);

    // Cost synergies
    const duplicatedRoles = Math.min(targetCompany.employees * 0.15, 50); // 15% overlap max
    const sharedResources = (buyerRevenue + targetCompany.revenue) * 0.02; // 2% savings
    const economies = Math.sqrt(buyerRevenue * targetCompany.revenue) * 0.001; // Scale economies
    
    const costSynergies = {
      duplicatedRoles: duplicatedRoles * 75000, // $75k average salary
      sharedResources,
      economies,
      totalSavings: 0
    };
    costSynergies.totalSavings = costSynergies.duplicatedRoles + costSynergies.sharedResources + costSynergies.economies;

    // Revenue synergies
    const crossSelling = buyerRevenue * 0.05 + targetCompany.revenue * 0.05; // 5% cross-sell opportunity
    const marketExpansion = targetCompany.revenue * 0.1; // 10% market expansion
    const pricingPower = (buyerRevenue + targetCompany.revenue) * 0.02; // 2% pricing power
    
    const revenueSynergies = {
      crossSelling,
      marketExpansion,
      pricingPower,
      totalIncrease: crossSelling + marketExpansion + pricingPower
    };

    // Financial synergies
    const taxBenefits = Math.max(0, targetCompany.revenue * 0.03); // 3% tax optimization
    const capitalEfficiency = (buyerRevenue + targetCompany.revenue) * 0.01; // 1% capital efficiency
    const debtCapacity = targetCompany.valuation * 0.1; // 10% additional debt capacity
    
    const financialSynergies = {
      taxBenefits,
      capitalEfficiency,
      debtCapacity,
      totalValue: taxBenefits + capitalEfficiency + debtCapacity
    };

    // Risk factors
    const integrationRisk = (costSynergies.totalSavings + revenueSynergies.totalIncrease) * 0.2; // 20% integration risk
    const culturalClash = this.assessCulturalRisk(buyerCompanies, targetCompany);
    const customerLoss = targetCompany.revenue * 0.05; // 5% customer churn risk
    const regulatoryRisk = targetCompany.valuation * 0.02; // 2% regulatory risk
    
    const riskFactors = {
      integrationRisk,
      culturalClash,
      customerLoss,
      regulatoryRisk,
      totalRisk: integrationRisk + culturalClash + customerLoss + regulatoryRisk
    };

    return {
      costSynergies,
      revenueSynergies,
      financialSynergies,
      riskFactors
    };
  }

  /**
   * Generate AI-driven acquisition recommendations
   */
  getAcquisitionRecommendations(playerId: string): {
    targets: Array<{
      company: Company;
      attractiveness: number;
      strategicFit: number;
      valuation: CompanyValuation;
      synergies: MergerSynergy;
      recommendedOffer: number;
      reasoning: string[];
    }>;
    marketTrends: string[];
    timing: 'excellent' | 'good' | 'fair' | 'poor';
  } {
    const playerCompanies = this.getPlayerCompanies(playerId);
    const availableTargets = Array.from(this.companies.values())
      .filter(company => !company.isAcquired && this.findCompanyOwner(company.id) !== playerId);

    const targets = availableTargets.map(company => {
      const valuation = this.calculateValuation(company.id);
      const synergies = this.calculateMergerSynergies(playerId, company.id);
      const strategicFit = this.calculateStrategicFit(playerCompanies, company);
      const attractiveness = this.calculateAttractiveness(company, valuation);
      
      // AI-driven pricing recommendation
      const recommendedOffer = this.calculateRecommendedOffer(company, valuation, synergies, strategicFit);
      
      const reasoning = this.generateAcquisitionReasoning(company, valuation, synergies, strategicFit);

      return {
        company,
        attractiveness,
        strategicFit,
        valuation,
        synergies,
        recommendedOffer,
        reasoning
      };
    })
    .filter(target => target.attractiveness > 0.3) // Only show reasonably attractive targets
    .sort((a, b) => (b.attractiveness + b.strategicFit) - (a.attractiveness + a.strategicFit))
    .slice(0, 10); // Top 10 recommendations

    const marketTrends = this.getAcquisitionMarketTrends();
    const timing = this.assessAcquisitionTiming();

    return {
      targets,
      marketTrends,
      timing
    };
  }

  /**
   * Simulate competitive bidding process
   */
  simulateAuction(targetCompanyId: string, minBidders: number = 2): {
    bids: Array<{
      bidderId: string;
      bidAmount: number;
      bidType: 'strategic' | 'financial';
      probability: number;
    }>;
    recommendedResponse: {
      bidAmount: number;
      strategy: string;
      timeline: string;
    };
  } {
    const company = this.companies.get(targetCompanyId);
    if (!company) {
      throw new Error('Company not found');
    }

    const valuation = this.calculateValuation(targetCompanyId);
    const baseValue = valuation.marketValue;

    // Generate competitive bids
    const bids = Array.from({ length: minBidders + Math.floor(Math.random() * 3) }, (_, i) => {
      const isStrategic = Math.random() < 0.6; // 60% strategic, 40% financial buyers
      const bidMultiplier = isStrategic ? 1.1 + Math.random() * 0.4 : 1.0 + Math.random() * 0.2; // Strategic buyers pay more
      
      return {
        bidderId: `bidder_${i + 1}`,
        bidAmount: baseValue * bidMultiplier,
        bidType: isStrategic ? 'strategic' as const : 'financial' as const,
        probability: Math.random() * 0.8 + 0.2 // 20-100% probability
      };
    }).sort((a, b) => b.bidAmount - a.bidAmount);

    // Recommend response strategy
    const highestBid = bids[0];
    const recommendedBid = highestBid.bidAmount * 1.05; // 5% above highest bid

    return {
      bids,
      recommendedResponse: {
        bidAmount: recommendedBid,
        strategy: 'Competitive bidding requires 5% premium above highest known bid',
        timeline: 'Submit bid within 48 hours to maintain competitiveness'
      }
    };
  }

  /**
   * Helper methods for calculations
   */
  private calculateTotalAssets(company: Company): number {
    const equipmentValue = company.equipment.reduce((sum, eq) => sum + eq.currentValue, 0);
    const propertyValue = company.properties.reduce((sum, prop) => sum + prop.currentValue, 0);
    const cashEquivalent = company.revenue * 0.2; // Assume 20% cash reserves
    const inventoryValue = company.revenue * 0.15; // Assume 15% inventory
    const receivables = company.revenue * 0.12; // Assume 12% receivables
    
    return equipmentValue + propertyValue + cashEquivalent + inventoryValue + receivables;
  }

  private calculateTotalLiabilities(company: Company): number {
    const accountsPayable = company.expenses * 0.3; // 30% of expenses in payables
    const debtEstimate = company.valuation * 0.2; // Assume 20% debt-to-value ratio
    const accruedExpenses = company.expenses * 0.1; // 10% accrued
    
    return accountsPayable + debtEstimate + accruedExpenses;
  }

  private getIndustryMultiples(industry: Industry): Record<string, number> {
    const multiples = {
      [Industry.TECHNOLOGY]: { pe: 25, pb: 4, ps: 8, ev_ebitda: 15 },
      [Industry.HEALTHCARE]: { pe: 18, pb: 3, ps: 4, ev_ebitda: 12 },
      [Industry.FINANCE]: { pe: 12, pb: 1.2, ps: 2, ev_ebitda: 8 },
      [Industry.RETAIL]: { pe: 15, pb: 2, ps: 1.5, ev_ebitda: 6 },
      [Industry.MANUFACTURING]: { pe: 14, pb: 1.8, ps: 1.2, ev_ebitda: 8 },
      [Industry.REAL_ESTATE]: { pe: 16, pb: 1.5, ps: 3, ev_ebitda: 10 },
      [Industry.EDUCATION]: { pe: 20, pb: 2.5, ps: 3, ev_ebitda: 12 },
      [Industry.ENERGY]: { pe: 10, pb: 1.1, ps: 1, ev_ebitda: 5 },
      [Industry.TRANSPORTATION]: { pe: 13, pb: 1.6, ps: 1.8, ev_ebitda: 7 },
      [Industry.ENTERTAINMENT]: { pe: 22, pb: 3.5, ps: 5, ev_ebitda: 14 }
    };
    
    return multiples[industry] || multiples[Industry.MANUFACTURING];
  }

  private calculateMarketValue(company: Company, multiples: Record<string, number>): number {
    const earnings = Math.max(company.profit, company.revenue * 0.05); // Minimum 5% margin
    const sales = company.revenue;
    const book = this.calculateTotalAssets(company) - this.calculateTotalLiabilities(company);
    
    const peValue = earnings * multiples.pe;
    const psValue = sales * multiples.ps;
    const pbValue = book * multiples.pb;
    
    // Weighted average of multiples
    return (peValue * 0.4 + psValue * 0.3 + pbValue * 0.3);
  }

  private performDCFAnalysis(company: Company): CompanyValuation['dcfAnalysis'] {
    const currentFCF = Math.max(company.profit * 0.8, company.revenue * 0.02); // Free cash flow proxy
    const growthRate = Math.min(0.15, Math.max(-0.05, company.profit / Math.max(1, company.revenue) + 0.05)); // 5% base growth
    const terminalGrowthRate = 0.025; // 2.5% perpetual growth
    const wacc = 0.10; // 10% weighted average cost of capital
    const projectionYears = 5;
    
    const freeGashFlow: number[] = [];
    let presentValue = 0;
    
    for (let year = 1; year <= projectionYears; year++) {
      const yearFCF = currentFCF * Math.pow(1 + growthRate, year);
      freeGashFlow.push(yearFCF);
      presentValue += yearFCF / Math.pow(1 + wacc, year);
    }
    
    const terminalValue = (freeGashFlow[projectionYears - 1] * (1 + terminalGrowthRate)) / (wacc - terminalGrowthRate);
    const terminalPV = terminalValue / Math.pow(1 + wacc, projectionYears);
    
    return {
      presentValue: presentValue + terminalPV,
      terminalValue: terminalPV,
      wacc,
      growthRate,
      freeGashFlow
    };
  }

  private calculateValuationMultiples(company: Company): CompanyValuation['multiples'] {
    const earnings = Math.max(company.profit, 1);
    const book = Math.max(this.calculateTotalAssets(company) - this.calculateTotalLiabilities(company), 1);
    const sales = Math.max(company.revenue, 1);
    const ebitda = Math.max(earnings + company.expenses * 0.1, 1); // Rough EBITDA
    const enterpriseValue = company.valuation + company.valuation * 0.2; // Add debt estimate
    
    return {
      priceToEarnings: company.valuation / earnings,
      priceToBook: company.valuation / book,
      priceToSales: company.valuation / sales,
      evToEbitda: enterpriseValue / ebitda,
      enterpriseValue
    };
  }

  // Additional helper methods (continued in next part due to length)
  private generateMarketCompanies(): void {
    // Generate initial market companies for acquisition opportunities
    const marketCompanies = [
      { name: "TechStart Solutions", industry: Industry.TECHNOLOGY, type: CompanyType.STARTUP },
      { name: "HealthCare Plus", industry: Industry.HEALTHCARE, type: CompanyType.SMALL_BUSINESS },
      { name: "Manufacturing Corp", industry: Industry.MANUFACTURING, type: CompanyType.CORPORATION },
      { name: "EduTech Academy", industry: Industry.EDUCATION, type: CompanyType.SMALL_BUSINESS },
      { name: "Green Energy Co", industry: Industry.ENERGY, type: CompanyType.STARTUP }
    ];

    marketCompanies.forEach(comp => {
      this.createCompany('market', comp.name, comp.industry, comp.type, 100000 + Math.random() * 900000);
    });
  }

  private getInitialEmployees(type: CompanyType): number {
    const employeeMap = {
      [CompanyType.STARTUP]: 5 + Math.floor(Math.random() * 15),
      [CompanyType.SMALL_BUSINESS]: 20 + Math.floor(Math.random() * 80),
      [CompanyType.CORPORATION]: 100 + Math.floor(Math.random() * 400),
      [CompanyType.FRANCHISE]: 10 + Math.floor(Math.random() * 40),
      [CompanyType.NONPROFIT]: 5 + Math.floor(Math.random() * 25)
    };
    return employeeMap[type] || 10;
  }

  private getInitialDigitalLevel(industry: Industry): number {
    const digitalMap = {
      [Industry.TECHNOLOGY]: 80 + Math.random() * 20,
      [Industry.FINANCE]: 60 + Math.random() * 30,
      [Industry.RETAIL]: 40 + Math.random() * 40,
      [Industry.EDUCATION]: 30 + Math.random() * 40,
      [Industry.HEALTHCARE]: 25 + Math.random() * 35,
      [Industry.MANUFACTURING]: 20 + Math.random() * 30,
      [Industry.ENERGY]: 15 + Math.random() * 25,
      [Industry.REAL_ESTATE]: 35 + Math.random() * 35,
      [Industry.TRANSPORTATION]: 25 + Math.random() * 30,
      [Industry.ENTERTAINMENT]: 50 + Math.random() * 35
    };
    return Math.round(digitalMap[industry] || 30);
  }

  private getRandomLocation(): string {
    const locations = [
      'San Francisco, CA', 'New York, NY', 'Austin, TX', 'Seattle, WA', 'Boston, MA',
      'Chicago, IL', 'Los Angeles, CA', 'Denver, CO', 'Atlanta, GA', 'Miami, FL'
    ];
    return locations[Math.floor(Math.random() * locations.length)];
  }

  private getPlayerCompanies(playerId: string): Company[] {
    return Array.from(this.companies.values()).filter(company => 
      this.findCompanyOwner(company.id) === playerId
    );
  }

  private findCompanyOwner(companyId: string): string {
    // This would be implemented to find the actual owner
    return 'player_1'; // Placeholder
  }

  private generateContingencies(company: Company): string[] {
    const contingencies: string[] = [];
    
    if (company.revenue < 1000000) {
      contingencies.push('Revenue verification through 3rd party audit');
    }
    
    if (company.employees > 50) {
      contingencies.push('Key employee retention agreements');
    }
    
    if (company.industry === Industry.HEALTHCARE || company.industry === Industry.FINANCE) {
      contingencies.push('Regulatory compliance verification');
    }
    
    contingencies.push('Clean legal and IP audit');
    contingencies.push('Financial statement verification');
    
    return contingencies;
  }

  private requiresRegulatoryApproval(company: Company): boolean {
    return company.revenue > 10000000 || 
           company.industry === Industry.FINANCE || 
           company.industry === Industry.HEALTHCARE ||
           company.marketShare > 0.15; // >15% market share
  }

  private calculateSynergyPotential(company: Company): number {
    // Base synergy potential on industry, size, and digital transformation
    let potential = 0.1; // 10% base
    
    if (company.industry === Industry.TECHNOLOGY) potential += 0.05;
    if (company.digitalTransformation > 50) potential += 0.03;
    if (company.employees > 100) potential += 0.02;
    
    return Math.min(0.3, potential); // Cap at 30%
  }

  private getComparableAnalysis(company: Company): CompanyValuation['comparableCompanies'] {
    // Simplified comparable company analysis
    const industryMultiples = this.getIndustryMultiples(company.industry);
    const averageMultiples = {
      pe: industryMultiples.pe,
      pb: industryMultiples.pb,
      ps: industryMultiples.ps
    };
    
    const industryMedian = company.revenue * industryMultiples.ps;
    const premiumDiscount = (company.valuation - industryMedian) / industryMedian;
    
    return {
      averageMultiples,
      industryMedian,
      premiumDiscount
    };
  }

  private processDueDiligence(offerId: string): void {
    // Simulate due diligence process
    setTimeout(() => {
      const offer = this.acquisitionOffers.get(offerId);
      if (offer) {
        offer.dueDiligenceCompleted = true;
        offer.financingSecured = true;
        this.emit('due_diligence:completed', { offerId });
      }
    }, 5000); // 5 second simulation
  }

  private calculateTotalAcquisitionCost(offer: AcquisitionOffer): number {
    const baseCost = offer.offerPrice;
    const legalFees = baseCost * 0.02; // 2% legal fees
    const bankingFees = baseCost * 0.015; // 1.5% investment banking fees
    const dueDiligenceCosts = 50000; // $50k DD costs
    
    return baseCost + legalFees + bankingFees + dueDiligenceCosts;
  }

  private processPostAcquisitionIntegration(buyerId: string, company: Company, synergies: MergerSynergy): void {
    // Apply integration effects over time
    setTimeout(() => {
      company.digitalTransformation = Math.min(100, company.digitalTransformation + 10);
      company.productionCapacity *= 1.1;
      this.emit('integration:progress', { buyerId, companyId: company.id, progress: 25 });
    }, 30000); // 30 seconds
  }

  private assessCulturalRisk(buyerCompanies: Company[], targetCompany: Company): number {
    // Simple cultural risk assessment
    const sizeDifference = Math.abs(
      Math.log(buyerCompanies.reduce((sum, c) => sum + c.employees, 0)) - 
      Math.log(targetCompany.employees)
    );
    
    const industryMatch = buyerCompanies.some(c => c.industry === targetCompany.industry);
    
    let risk = sizeDifference * 50000; // Size mismatch risk
    if (!industryMatch) risk += 100000; // Industry mismatch risk
    
    return risk;
  }

  private calculateStrategicFit(buyerCompanies: Company[], target: Company): number {
    let fit = 0.5; // Base fit
    
    // Industry synergy
    const sameIndustry = buyerCompanies.some(c => c.industry === target.industry);
    if (sameIndustry) fit += 0.2;
    
    // Complementary capabilities
    const buyerDigitalAvg = buyerCompanies.reduce((sum, c) => sum + c.digitalTransformation, 0) / buyerCompanies.length;
    if (Math.abs(buyerDigitalAvg - target.digitalTransformation) > 20) fit += 0.1; // Complementary digital levels
    
    // Geographic expansion
    const buyerLocations = new Set(buyerCompanies.flatMap(c => c.locations));
    if (!buyerLocations.has(target.headquarters)) fit += 0.15; // New market
    
    return Math.min(1.0, fit);
  }

  private calculateAttractiveness(company: Company, valuation: CompanyValuation): number {
    let attractiveness = 0.5; // Base attractiveness
    
    // Profitability
    const margin = company.profit / Math.max(company.revenue, 1);
    if (margin > 0.1) attractiveness += 0.2; // >10% margin
    if (margin > 0.2) attractiveness += 0.1; // >20% margin
    
    // Growth
    if (company.revenue > 0) attractiveness += 0.1; // Revenue positive
    
    // Digital transformation
    if (company.digitalTransformation > 60) attractiveness += 0.1;
    
    // Valuation attractiveness
    if (valuation.marketValue < valuation.intrinsicValue) attractiveness += 0.2; // Undervalued
    
    return Math.min(1.0, attractiveness);
  }

  private calculateRecommendedOffer(
    company: Company, 
    valuation: CompanyValuation, 
    synergies: MergerSynergy, 
    strategicFit: number
  ): number {
    const baseValue = valuation.intrinsicValue;
    const synergyValue = (synergies.costSynergies.totalSavings + synergies.revenueSynergies.totalIncrease) * 3; // 3x multiple on synergies
    const strategicPremium = baseValue * strategicFit * 0.2; // Up to 20% strategic premium
    
    return baseValue + synergyValue * 0.5 + strategicPremium; // Share synergy value 50/50
  }

  private generateAcquisitionReasoning(
    company: Company,
    valuation: CompanyValuation,
    synergies: MergerSynergy,
    strategicFit: number
  ): string[] {
    const reasons: string[] = [];
    
    if (strategicFit > 0.7) {
      reasons.push(`Strong strategic fit (${(strategicFit * 100).toFixed(0)}% compatibility)`);
    }
    
    if (synergies.costSynergies.totalSavings > 100000) {
      reasons.push(`Significant cost synergies of $${Math.round(synergies.costSynergies.totalSavings / 1000)}k annually`);
    }
    
    if (company.digitalTransformation < 40) {
      reasons.push('Digital transformation opportunity to modernize operations');
    }
    
    if (company.marketShare > 0.05) {
      reasons.push(`Established market position with ${(company.marketShare * 100).toFixed(1)}% market share`);
    }
    
    if (valuation.marketValue < valuation.intrinsicValue) {
      reasons.push('Undervalued based on DCF analysis');
    }
    
    if (reasons.length === 0) {
      reasons.push('Standard acquisition opportunity');
    }
    
    return reasons;
  }

  private getAcquisitionMarketTrends(): string[] {
    const economyState = this.economyEngine.getState();
    const trends: string[] = [];
    
    if (economyState.interestRate < 5) {
      trends.push('Low interest rates favor leveraged acquisitions');
    }
    
    if (economyState.stockMarketIndex > 10000) {
      trends.push('Strong equity markets support stock-based deals');
    }
    
    if (economyState.gdpGrowth > 3) {
      trends.push('Economic expansion creates acquisition opportunities');
    }
    
    if (economyState.creditAvailability > 80) {
      trends.push('High credit availability supports large transactions');
    }
    
    return trends;
  }

  private assessAcquisitionTiming(): 'excellent' | 'good' | 'fair' | 'poor' {
    const economyState = this.economyEngine.getState();
    
    let score = 0;
    if (economyState.interestRate < 5) score += 1;
    if (economyState.gdpGrowth > 2) score += 1;
    if (economyState.creditAvailability > 70) score += 1;
    if (economyState.businessConfidence > 70) score += 1;
    
    if (score >= 3) return 'excellent';
    if (score >= 2) return 'good';
    if (score >= 1) return 'fair';
    return 'poor';
  }

  // Public methods
  public getCompany(id: string): Company | undefined {
    return this.companies.get(id);
  }

  public getAllCompanies(): Company[] {
    return Array.from(this.companies.values());
  }

  public getAcquisitionOffer(id: string): AcquisitionOffer | undefined {
    return this.acquisitionOffers.get(id);
  }
}