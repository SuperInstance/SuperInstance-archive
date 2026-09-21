/**
 * Product Development Manager
 * Handles product creation, R&D, market research, and product lifecycle management
 * Integrates with company operations and digital transformation strategies
 */

import { EventEmitter } from 'events';
import {
  Company,
  Product,
  ResearchProject,
  ProductDevelopmentStrategy,
  MarketResearch,
  ProductLifecycle,
  DevelopmentStage,
  TechnologyStack,
  ProductMetrics,
  CustomerFeedback,
  CompetitiveAnalysis
} from '../types/game-types';
import { EconomyEngine } from '../economy/EconomyEngine';

export interface ProductCategory {
  id: string;
  name: string;
  description: string;
  marketSize: number;
  growthRate: number;
  competitionLevel: 'low' | 'medium' | 'high';
  barriers: string[];
  keySuccessFactors: string[];
  typicalMargins: number;
  developmentComplexity: 'simple' | 'moderate' | 'complex' | 'breakthrough';
}

export interface DevelopmentCost {
  research: number;
  design: number;
  prototyping: number;
  testing: number;
  manufacturing: number;
  marketing: number;
  total: number;
  timeline: number; // months
  resourceRequirements: {
    engineers: number;
    designers: number;
    researchers: number;
    budget: number;
  };
}

export interface MarketOpportunity {
  segment: string;
  size: number;
  growth: number;
  competition: number;
  customerNeed: string;
  pricePoint: number;
  distributionChannels: string[];
  riskFactors: string[];
  successProbability: number;
}

export interface ProductRoadmap {
  companyId: string;
  products: Product[];
  activeProjects: ResearchProject[];
  plannedReleases: Array<{
    productId: string;
    version: string;
    plannedDate: number;
    features: string[];
    targetMarket: string;
  }>;
  resourceAllocation: Record<string, number>;
  strategicGoals: string[];
  competitivePositioning: string;
}

export class ProductDevelopmentManager extends EventEmitter {
  private products: Map<string, Product> = new Map();
  private researchProjects: Map<string, ResearchProject> = new Map();
  private productCategories: Map<string, ProductCategory> = new Map();
  private marketResearch: Map<string, MarketResearch> = new Map();
  private economyEngine: EconomyEngine;

  constructor(economyEngine: EconomyEngine) {
    super();
    this.economyEngine = economyEngine;
    this.initializeProductCategories();
  }

  /**
   * Initialize available product categories
   */
  private initializeProductCategories(): void {
    const categories: ProductCategory[] = [
      {
        id: 'software_saas',
        name: 'Software as a Service',
        description: 'Cloud-based software solutions',
        marketSize: 500000000,
        growthRate: 0.25,
        competitionLevel: 'high',
        barriers: ['technical_expertise', 'customer_acquisition', 'scaling_infrastructure'],
        keySuccessFactors: ['user_experience', 'reliability', 'customer_support', 'feature_innovation'],
        typicalMargins: 0.80,
        developmentComplexity: 'complex'
      },
      {
        id: 'mobile_apps',
        name: 'Mobile Applications',
        description: 'Consumer and business mobile apps',
        marketSize: 200000000,
        growthRate: 0.15,
        competitionLevel: 'high',
        barriers: ['app_store_discovery', 'user_acquisition', 'platform_updates'],
        keySuccessFactors: ['intuitive_design', 'performance', 'viral_features', 'monetization'],
        typicalMargins: 0.60,
        developmentComplexity: 'moderate'
      },
      {
        id: 'iot_devices',
        name: 'IoT Devices',
        description: 'Internet of Things hardware products',
        marketSize: 300000000,
        growthRate: 0.30,
        competitionLevel: 'medium',
        barriers: ['hardware_manufacturing', 'regulatory_compliance', 'connectivity'],
        keySuccessFactors: ['reliability', 'battery_life', 'connectivity', 'data_insights'],
        typicalMargins: 0.45,
        developmentComplexity: 'complex'
      },
      {
        id: 'digital_content',
        name: 'Digital Content',
        description: 'Educational, entertainment, and informational content',
        marketSize: 150000000,
        growthRate: 0.20,
        competitionLevel: 'medium',
        barriers: ['content_quality', 'distribution', 'intellectual_property'],
        keySuccessFactors: ['engagement', 'uniqueness', 'production_quality', 'marketing'],
        typicalMargins: 0.75,
        developmentComplexity: 'moderate'
      },
      {
        id: 'automation_tools',
        name: 'Automation Tools',
        description: 'Business process automation software',
        marketSize: 400000000,
        growthRate: 0.35,
        competitionLevel: 'medium',
        barriers: ['integration_complexity', 'change_management', 'customization'],
        keySuccessFactors: ['ease_of_use', 'integration', 'roi_demonstration', 'support'],
        typicalMargins: 0.70,
        developmentComplexity: 'complex'
      },
      {
        id: 'analytics_platforms',
        name: 'Analytics Platforms',
        description: 'Data analysis and business intelligence tools',
        marketSize: 250000000,
        growthRate: 0.22,
        competitionLevel: 'high',
        barriers: ['data_expertise', 'visualization', 'scalability'],
        keySuccessFactors: ['insights_quality', 'ease_of_use', 'real_time_processing', 'visualization'],
        typicalMargins: 0.65,
        developmentComplexity: 'complex'
      },
      {
        id: 'ecommerce_solutions',
        name: 'E-commerce Solutions',
        description: 'Online commerce platforms and tools',
        marketSize: 600000000,
        growthRate: 0.18,
        competitionLevel: 'high',
        barriers: ['payment_processing', 'security', 'scalability'],
        keySuccessFactors: ['user_experience', 'payment_options', 'mobile_optimization', 'security'],
        typicalMargins: 0.50,
        developmentComplexity: 'moderate'
      }
    ];

    categories.forEach(category => {
      this.productCategories.set(category.id, category);
    });
  }

  /**
   * Research market opportunities for a company
   */
  async conductMarketResearch(
    companyId: string,
    category: string,
    budget: number
  ): Promise<MarketOpportunity[]> {
    const company = await this.getCompany(companyId);
    if (!company) {
      throw new Error('Company not found');
    }

    if (company.cashFlow < budget) {
      throw new Error('Insufficient budget for market research');
    }

    const productCategory = this.productCategories.get(category);
    if (!productCategory) {
      throw new Error(`Unknown product category: ${category}`);
    }

    // Deduct research cost
    company.cashFlow -= budget;

    // Generate market opportunities based on budget and company capabilities
    const opportunities = this.generateMarketOpportunities(company, productCategory, budget);

    // Store market research
    const research: MarketResearch = {
      id: `research_${companyId}_${Date.now()}`,
      companyId,
      category,
      budget,
      opportunities,
      competitiveAnalysis: this.analyzeCompetition(productCategory),
      trends: this.identifyMarketTrends(productCategory),
      conductedAt: Date.now(),
      validUntil: Date.now() + (90 * 24 * 60 * 60 * 1000) // Valid for 90 days
    };

    this.marketResearch.set(research.id, research);

    this.emit('market:research:completed', {
      companyId,
      research,
      opportunitiesFound: opportunities.length
    });

    return opportunities;
  }

  /**
   * Start product development project
   */
  async startDevelopment(
    companyId: string,
    productConcept: {
      name: string;
      category: string;
      targetMarket: string;
      features: string[];
      differentiators: string[];
      pricePoint: number;
    },
    strategy: ProductDevelopmentStrategy
  ): Promise<ResearchProject> {
    const company = await this.getCompany(companyId);
    if (!company) {
      throw new Error('Company not found');
    }

    const cost = this.calculateDevelopmentCost(productConcept, strategy);

    if (company.cashFlow < cost.total) {
      throw new Error(`Insufficient funds. Required: $${cost.total.toLocaleString()}, Available: $${company.cashFlow.toLocaleString()}`);
    }

    // Check resource availability
    if (!this.checkResourceAvailability(company, cost.resourceRequirements)) {
      throw new Error('Insufficient resources for development project');
    }

    // Create research project
    const project: ResearchProject = {
      id: `project_${companyId}_${Date.now()}`,
      companyId,
      name: productConcept.name,
      category: productConcept.category,
      stage: 'concept',
      progress: 0,
      budget: cost.total,
      spent: 0,
      timeline: cost.timeline,
      startDate: Date.now(),
      estimatedCompletion: Date.now() + (cost.timeline * 30 * 24 * 60 * 60 * 1000),
      team: this.assembleTeam(cost.resourceRequirements),
      milestones: this.generateMilestones(cost.timeline),
      risks: this.assessDevelopmentRisks(productConcept, strategy),
      expectedOutcome: {
        product: productConcept,
        marketPotential: this.estimateMarketPotential(productConcept),
        roi: this.calculateExpectedROI(productConcept, cost)
      }
    };

    // Allocate initial budget
    company.cashFlow -= Math.floor(cost.total * 0.2); // 20% upfront
    project.spent = Math.floor(cost.total * 0.2);

    this.researchProjects.set(project.id, project);

    this.emit('development:started', {
      companyId,
      project,
      initialBudget: Math.floor(cost.total * 0.2)
    });

    return project;
  }

  /**
   * Advance development project
   */
  async advanceDevelopment(projectId: string): Promise<{
    success: boolean;
    newStage: DevelopmentStage;
    progress: number;
    costs: number;
    milestone?: string;
    issues?: string[];
  }> {
    const project = this.researchProjects.get(projectId);
    if (!project) {
      throw new Error('Project not found');
    }

    const company = await this.getCompany(project.companyId);
    if (!company) {
      throw new Error('Company not found');
    }

    // Calculate advancement cost (monthly burn rate)
    const monthlyBurn = project.budget / project.timeline;
    const issues: string[] = [];

    // Check if company can fund next phase
    if (company.cashFlow < monthlyBurn) {
      issues.push('Insufficient funds to continue development');
      return {
        success: false,
        newStage: project.stage,
        progress: project.progress,
        costs: 0,
        issues
      };
    }

    // Deduct costs
    company.cashFlow -= monthlyBurn;
    project.spent += monthlyBurn;

    // Advance progress
    const progressIncrement = 100 / project.timeline;
    project.progress += progressIncrement;

    // Check for stage transitions
    const newStage = this.determineStage(project.progress);
    const stageChanged = newStage !== project.stage;
    
    if (stageChanged) {
      project.stage = newStage;
      this.emit('development:stage:changed', {
        projectId,
        oldStage: project.stage,
        newStage,
        progress: project.progress
      });
    }

    // Check for milestone completion
    let milestone: string | undefined;
    const nextMilestone = project.milestones.find(m => 
      !m.completed && project.progress >= m.targetProgress
    );

    if (nextMilestone) {
      nextMilestone.completed = true;
      nextMilestone.completedAt = Date.now();
      milestone = nextMilestone.description;
    }

    // Handle random events and risks
    const randomEvents = this.processRandomEvents(project);
    issues.push(...randomEvents);

    // Check for completion
    if (project.progress >= 100) {
      const product = await this.completeProduct(project);
      this.emit('development:completed', {
        projectId,
        product,
        totalCost: project.spent,
        timeline: Date.now() - project.startDate
      });
    }

    return {
      success: true,
      newStage,
      progress: project.progress,
      costs: monthlyBurn,
      milestone,
      issues: issues.length > 0 ? issues : undefined
    };
  }

  /**
   * Launch product to market
   */
  async launchProduct(
    productId: string,
    launchStrategy: {
      marketingBudget: number;
      pricingStrategy: 'penetration' | 'skimming' | 'competitive' | 'premium';
      distributionChannels: string[];
      targetCustomers: string[];
      launchEvents: string[];
    }
  ): Promise<{
    success: boolean;
    initialSales: number;
    marketReception: 'poor' | 'average' | 'good' | 'excellent';
    feedback: CustomerFeedback[];
    nextSteps: string[];
  }> {
    const product = this.products.get(productId);
    if (!product) {
      throw new Error('Product not found');
    }

    const company = await this.getCompany(product.companyId);
    if (!company) {
      throw new Error('Company not found');
    }

    if (company.cashFlow < launchStrategy.marketingBudget) {
      throw new Error('Insufficient marketing budget');
    }

    // Deduct marketing costs
    company.cashFlow -= launchStrategy.marketingBudget;

    // Calculate launch success factors
    const successFactors = this.calculateLaunchSuccess(product, launchStrategy);
    const marketReception = this.determineMarketReception(successFactors);
    
    // Generate initial sales based on reception and strategy
    const initialSales = this.calculateInitialSales(
      product,
      launchStrategy,
      marketReception,
      successFactors
    );

    // Generate customer feedback
    const feedback = this.generateCustomerFeedback(product, marketReception);

    // Update product status
    product.lifecycle = 'introduction';
    product.launchDate = Date.now();
    product.salesMetrics = {
      totalSales: initialSales,
      monthlyRecurring: product.businessModel === 'subscription' ? initialSales * 0.8 : 0,
      conversionRate: 0.02 + (successFactors * 0.03),
      churnRate: product.businessModel === 'subscription' ? 0.05 : 0,
      averageOrderValue: product.price,
      customerAcquisitionCost: launchStrategy.marketingBudget / Math.max(1, initialSales / product.price)
    };

    // Add revenue to company
    company.revenue = (company.revenue || 0) + (initialSales * product.price);
    company.cashFlow += (initialSales * product.price * 0.7); // 30% goes to costs

    const nextSteps = this.generateNextSteps(product, marketReception, feedback);

    this.emit('product:launched', {
      productId,
      companyId: product.companyId,
      initialSales,
      marketReception,
      revenue: initialSales * product.price
    });

    return {
      success: true,
      initialSales,
      marketReception,
      feedback,
      nextSteps
    };
  }

  /**
   * Generate market opportunities based on research
   */
  private generateMarketOpportunities(
    company: Company,
    category: ProductCategory,
    budget: number
  ): MarketOpportunity[] {
    const opportunities: MarketOpportunity[] = [];
    const researchQuality = Math.min(1, budget / 100000); // Better research with higher budget

    // Generate 3-7 opportunities based on budget
    const numOpportunities = Math.floor(3 + (researchQuality * 4));

    for (let i = 0; i < numOpportunities; i++) {
      const segmentSize = category.marketSize * (0.05 + Math.random() * 0.25);
      const competition = Math.random();
      const customerNeed = this.generateCustomerNeed(category);

      opportunities.push({
        segment: this.generateSegmentName(category, i),
        size: Math.floor(segmentSize),
        growth: category.growthRate + (Math.random() - 0.5) * 0.1,
        competition,
        customerNeed,
        pricePoint: this.estimatePricePoint(category, competition),
        distributionChannels: this.suggestDistributionChannels(category),
        riskFactors: this.identifyRiskFactors(category, competition),
        successProbability: this.calculateSuccessProbability(company, category, competition)
      });
    }

    return opportunities.sort((a, b) => (b.size * b.successProbability) - (a.size * a.successProbability));
  }

  /**
   * Calculate development cost breakdown
   */
  private calculateDevelopmentCost(
    concept: any,
    strategy: ProductDevelopmentStrategy
  ): DevelopmentCost {
    const category = this.productCategories.get(concept.category);
    if (!category) {
      throw new Error(`Unknown category: ${concept.category}`);
    }

    // Base costs by complexity
    const baseCosts = {
      simple: 50000,
      moderate: 150000,
      complex: 400000,
      breakthrough: 800000
    };

    const baseCost = baseCosts[category.developmentComplexity];
    const featureMultiplier = 1 + (concept.features.length * 0.15);
    const strategyMultiplier = this.getStrategyMultiplier(strategy);

    const research = Math.floor(baseCost * 0.2 * featureMultiplier * strategyMultiplier);
    const design = Math.floor(baseCost * 0.25 * featureMultiplier);
    const prototyping = Math.floor(baseCost * 0.3 * featureMultiplier);
    const testing = Math.floor(baseCost * 0.15 * featureMultiplier);
    const manufacturing = Math.floor(baseCost * 0.1 * featureMultiplier);

    const total = research + design + prototyping + testing + manufacturing;
    const marketing = Math.floor(total * 0.3); // 30% of dev cost for marketing

    // Timeline based on complexity and strategy
    const baseTimeline = {
      simple: 3,
      moderate: 6,
      complex: 12,
      breakthrough: 18
    };

    const timeline = Math.floor(baseTimeline[category.developmentComplexity] * strategyMultiplier);

    // Resource requirements
    const resourceRequirements = {
      engineers: Math.ceil(concept.features.length * 0.5),
      designers: Math.ceil(concept.features.length * 0.2),
      researchers: category.developmentComplexity === 'breakthrough' ? 2 : 1,
      budget: total + marketing
    };

    return {
      research,
      design,
      prototyping,
      testing,
      manufacturing,
      marketing,
      total: total + marketing,
      timeline,
      resourceRequirements
    };
  }

  // Helper methods (simplified implementations)
  private getStrategyMultiplier(strategy: ProductDevelopmentStrategy): number {
    return 1; // Simplified - would analyze strategy details
  }

  private checkResourceAvailability(company: Company, requirements: any): boolean {
    // Simplified - would check actual company resources
    return company.employees >= requirements.engineers + requirements.designers + requirements.researchers;
  }

  private assembleTeam(requirements: any): any[] {
    // Simplified - would create actual team structure
    return [];
  }

  private generateMilestones(timeline: number): any[] {
    const milestones = [];
    const stages = ['concept', 'design', 'prototype', 'alpha', 'beta', 'release'];
    
    stages.forEach((stage, index) => {
      milestones.push({
        stage,
        description: `Complete ${stage} phase`,
        targetProgress: ((index + 1) / stages.length) * 100,
        completed: false
      });
    });

    return milestones;
  }

  private assessDevelopmentRisks(concept: any, strategy: ProductDevelopmentStrategy): any[] {
    return []; // Simplified
  }

  private estimateMarketPotential(concept: any): number {
    return 1000000; // Simplified
  }

  private calculateExpectedROI(concept: any, cost: DevelopmentCost): number {
    return 0.3; // Simplified 30% ROI
  }

  private determineStage(progress: number): DevelopmentStage {
    if (progress < 20) return 'concept';
    if (progress < 40) return 'design';
    if (progress < 60) return 'development';
    if (progress < 80) return 'testing';
    return 'launch';
  }

  private processRandomEvents(project: ResearchProject): string[] {
    const events: string[] = [];
    
    // 10% chance of random event each advancement
    if (Math.random() < 0.1) {
      const randomEvents = [
        'Key team member left the project',
        'Technical breakthrough reduces timeline',
        'Competitor announced similar product',
        'New regulation affects product requirements',
        'Customer feedback suggests pivot needed'
      ];
      events.push(randomEvents[Math.floor(Math.random() * randomEvents.length)]);
    }

    return events;
  }

  private async completeProduct(project: ResearchProject): Promise<Product> {
    const product: Product = {
      id: `product_${project.companyId}_${Date.now()}`,
      companyId: project.companyId,
      name: project.name,
      category: project.category,
      version: '1.0',
      price: 100, // Simplified
      developmentCost: project.spent,
      lifecycle: 'development',
      businessModel: 'one_time',
      features: [],
      targetMarket: 'general',
      competitiveAdvantages: [],
      createdAt: Date.now()
    };

    this.products.set(product.id, product);
    return product;
  }

  private calculateLaunchSuccess(product: Product, strategy: any): number {
    return Math.random(); // Simplified success factor calculation
  }

  private determineMarketReception(successFactors: number): 'poor' | 'average' | 'good' | 'excellent' {
    if (successFactors > 0.8) return 'excellent';
    if (successFactors > 0.6) return 'good';
    if (successFactors > 0.4) return 'average';
    return 'poor';
  }

  private calculateInitialSales(product: Product, strategy: any, reception: string, successFactors: number): number {
    const baseMultiplier = {
      poor: 0.1,
      average: 0.3,
      good: 0.6,
      excellent: 1.0
    };

    return Math.floor(1000 * baseMultiplier[reception as keyof typeof baseMultiplier] * (1 + successFactors));
  }

  private generateCustomerFeedback(product: Product, reception: string): CustomerFeedback[] {
    return []; // Simplified
  }

  private generateNextSteps(product: Product, reception: string, feedback: CustomerFeedback[]): string[] {
    const steps = ['Monitor sales performance', 'Gather customer feedback'];
    
    if (reception === 'poor') {
      steps.push('Consider product improvements', 'Revise marketing strategy');
    } else if (reception === 'excellent') {
      steps.push('Scale production', 'Expand to new markets');
    }

    return steps;
  }

  // Additional helper methods (simplified)
  private analyzeCompetition(category: ProductCategory): CompetitiveAnalysis {
    return {} as CompetitiveAnalysis;
  }

  private identifyMarketTrends(category: ProductCategory): string[] {
    return [];
  }

  private generateCustomerNeed(category: ProductCategory): string {
    return 'Improve efficiency';
  }

  private generateSegmentName(category: ProductCategory, index: number): string {
    return `${category.name} Segment ${index + 1}`;
  }

  private estimatePricePoint(category: ProductCategory, competition: number): number {
    return 100;
  }

  private suggestDistributionChannels(category: ProductCategory): string[] {
    return ['online', 'direct_sales'];
  }

  private identifyRiskFactors(category: ProductCategory, competition: number): string[] {
    return ['market_saturation', 'technology_changes'];
  }

  private calculateSuccessProbability(company: Company, category: ProductCategory, competition: number): number {
    return Math.random() * 0.8 + 0.2; // 20-100%
  }

  private async getCompany(companyId: string): Promise<Company | null> {
    return null; // Placeholder
  }

  /**
   * Public API methods
   */
  getProduct(productId: string): Product | null {
    return this.products.get(productId) || null;
  }

  getCompanyProducts(companyId: string): Product[] {
    return Array.from(this.products.values()).filter(p => p.companyId === companyId);
  }

  getResearchProject(projectId: string): ResearchProject | null {
    return this.researchProjects.get(projectId) || null;
  }

  getCompanyResearchProjects(companyId: string): ResearchProject[] {
    return Array.from(this.researchProjects.values()).filter(p => p.companyId === companyId);
  }

  getProductCategories(): ProductCategory[] {
    return Array.from(this.productCategories.values());
  }

  getMarketResearch(companyId: string, category?: string): MarketResearch[] {
    return Array.from(this.marketResearch.values()).filter(r => 
      r.companyId === companyId && (!category || r.category === category)
    );
  }

  generateProductRoadmap(companyId: string): ProductRoadmap {
    const products = this.getCompanyProducts(companyId);
    const activeProjects = this.getCompanyResearchProjects(companyId);

    return {
      companyId,
      products,
      activeProjects,
      plannedReleases: [],
      resourceAllocation: {},
      strategicGoals: [],
      competitivePositioning: 'follower'
    };
  }
}