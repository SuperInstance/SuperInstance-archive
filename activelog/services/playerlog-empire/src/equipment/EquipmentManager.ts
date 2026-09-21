/**
 * Equipment Purchasing and Management System
 * Handles printers, servers, computers, and business equipment
 */

import { EventEmitter } from 'events';
import {
  Equipment,
  EquipmentType,
  EquipmentCategory,
  Player,
  Company,
  Industry
} from '../types/game-types';
import { EconomyEngine } from '../economy/EconomyEngine';

export interface EquipmentCatalog {
  id: string;
  name: string;
  type: EquipmentType;
  category: EquipmentCategory;
  basePrice: number;
  specifications: EquipmentSpecs;
  manufacturer: string;
  model: string;
  releaseYear: number;
  supportedIndustries: Industry[];
  businessImpact: BusinessImpact;
  maintenanceRequirements: MaintenanceRequirements;
  upgradeOptions: UpgradeOption[];
  availability: 'in_stock' | 'limited' | 'backorder' | 'discontinued';
}

export interface EquipmentSpecs {
  // Common specs
  powerConsumption: number; // watts
  dimensions: { width: number; height: number; depth: number }; // cm
  weight: number; // kg
  warranty: number; // months
  
  // Printer specific
  printSpeed?: number; // pages per minute
  printResolution?: string; // dpi
  paperCapacity?: number; // sheets
  colorCapable?: boolean;
  duplexPrinting?: boolean;
  
  // Server specific
  cpuCores?: number;
  ramGB?: number;
  storageGB?: number;
  networkPorts?: number;
  rackUnits?: number;
  maxConnections?: number;
  
  // Computer specific
  processorSpeed?: number; // GHz
  graphicsCard?: string;
  ports?: string[];
  operatingSystem?: string;
  
  // Machinery specific
  productionRate?: number; // units per hour
  accuracy?: number; // percentage
  automation?: boolean;
  compatibility?: string[];
}

export interface BusinessImpact {
  productivityIncrease: number; // percentage
  costSavingsAnnual: number; // dollars
  revenueGenerationPotential: number; // dollars
  employeeEfficiencyGain: number; // percentage
  digitalTransformationPoints: number; // 0-100
  marketingValue: number; // brand value increase
  customerSatisfactionImpact: number; // percentage
  competitiveAdvantage: number; // 0-100 score
}

export interface MaintenanceRequirements {
  dailyCost: number;
  weeklyCost: number;
  monthlyCost: number;
  annualServiceCost: number;
  expectedLifespan: number; // years
  depreciation: number; // percentage per year
  repairFrequency: number; // times per year
  downtimeHours: number; // hours per repair
}

export interface UpgradeOption {
  id: string;
  name: string;
  cost: number;
  impactOnSpecs: Partial<EquipmentSpecs>;
  impactOnBusiness: Partial<BusinessImpact>;
  prerequisite?: string[];
}

export interface EquipmentLease {
  id: string;
  equipmentId: string;
  lesseeId: string; // Player or Company ID
  lessorId: string;
  monthlyPayment: number;
  termMonths: number;
  remainingPayments: number;
  buyoutOption: number;
  startDate: Date;
  endDate: Date;
  maintenanceIncluded: boolean;
  upgradeOptions: boolean;
  status: 'active' | 'completed' | 'defaulted' | 'bought_out';
}

export interface EquipmentFinancing {
  type: 'loan' | 'lease' | 'rent_to_own' | 'subscription';
  downPayment: number;
  monthlyPayment: number;
  term: number; // months
  interestRate: number;
  totalCost: number;
  creditRequirement: number;
  earlyPayoffPenalty?: number;
  taxBenefits: number;
}

export class EquipmentManager extends EventEmitter {
  private catalog: Map<string, EquipmentCatalog> = new Map();
  private playerEquipment: Map<string, Equipment[]> = new Map();
  private companyEquipment: Map<string, Equipment[]> = new Map();
  private leases: Map<string, EquipmentLease> = new Map();
  private economyEngine: EconomyEngine;
  private marketTrends: Map<EquipmentType, number> = new Map(); // Price multipliers
  private technologyCycles: Map<EquipmentType, number> = new Map(); // Innovation cycles
  
  constructor(economyEngine: EconomyEngine) {
    super();
    this.economyEngine = economyEngine;
    this.initializeCatalog();
    this.startMarketUpdates();
  }

  /**
   * Initialize equipment catalog with various types
   */
  private initializeCatalog(): void {
    console.log('🛒 Initializing equipment catalog...');
    
    // Printers
    this.addToCatalog({
      id: 'printer_hp_laserjet_pro',
      name: 'HP LaserJet Pro 4050',
      type: EquipmentType.PRINTER,
      category: EquipmentCategory.OFFICE,
      basePrice: 299,
      specifications: {
        powerConsumption: 600,
        dimensions: { width: 42, height: 38, depth: 43 },
        weight: 18,
        warranty: 12,
        printSpeed: 38,
        printResolution: '1200x1200 dpi',
        paperCapacity: 350,
        colorCapable: false,
        duplexPrinting: true
      },
      manufacturer: 'HP',
      model: 'LaserJet Pro 4050',
      releaseYear: 2023,
      supportedIndustries: [Industry.TECHNOLOGY, Industry.FINANCE, Industry.EDUCATION],
      businessImpact: {
        productivityIncrease: 15,
        costSavingsAnnual: 1200,
        revenueGenerationPotential: 0,
        employeeEfficiencyGain: 8,
        digitalTransformationPoints: 10,
        marketingValue: 500,
        customerSatisfactionImpact: 5,
        competitiveAdvantage: 20
      },
      maintenanceRequirements: {
        dailyCost: 2,
        weeklyCost: 10,
        monthlyCost: 45,
        annualServiceCost: 120,
        expectedLifespan: 5,
        depreciation: 20,
        repairFrequency: 1,
        downtimeHours: 2
      },
      upgradeOptions: [
        {
          id: 'toner_upgrade',
          name: 'High Capacity Toner',
          cost: 150,
          impactOnSpecs: { printSpeed: 42 },
          impactOnBusiness: { costSavingsAnnual: 1500 }
        }
      ],
      availability: 'in_stock'
    });

    // High-end color printer for marketing
    this.addToCatalog({
      id: 'printer_canon_imagepress',
      name: 'Canon ImagePRESS C165',
      type: EquipmentType.PRINTER,
      category: EquipmentCategory.PRODUCTION,
      basePrice: 15000,
      specifications: {
        powerConsumption: 2200,
        dimensions: { width: 85, height: 125, depth: 75 },
        weight: 180,
        warranty: 24,
        printSpeed: 65,
        printResolution: '2400x2400 dpi',
        paperCapacity: 3500,
        colorCapable: true,
        duplexPrinting: true
      },
      manufacturer: 'Canon',
      model: 'ImagePRESS C165',
      releaseYear: 2023,
      supportedIndustries: [Industry.ENTERTAINMENT, Industry.RETAIL, Industry.EDUCATION],
      businessImpact: {
        productivityIncrease: 45,
        costSavingsAnnual: 8000,
        revenueGenerationPotential: 25000,
        employeeEfficiencyGain: 30,
        digitalTransformationPoints: 25,
        marketingValue: 15000,
        customerSatisfactionImpact: 40,
        competitiveAdvantage: 65
      },
      maintenanceRequirements: {
        dailyCost: 15,
        weeklyCost: 80,
        monthlyCost: 350,
        annualServiceCost: 2500,
        expectedLifespan: 7,
        depreciation: 15,
        repairFrequency: 3,
        downtimeHours: 4
      },
      upgradeOptions: [],
      availability: 'in_stock'
    });

    // Servers
    this.addToCatalog({
      id: 'server_dell_poweredge',
      name: 'Dell PowerEdge R750',
      type: EquipmentType.SERVER,
      category: EquipmentCategory.IT_INFRASTRUCTURE,
      basePrice: 8500,
      specifications: {
        powerConsumption: 750,
        dimensions: { width: 48, height: 8.7, depth: 68 },
        weight: 28,
        warranty: 36,
        cpuCores: 16,
        ramGB: 64,
        storageGB: 2000,
        networkPorts: 4,
        rackUnits: 2,
        maxConnections: 1000
      },
      manufacturer: 'Dell',
      model: 'PowerEdge R750',
      releaseYear: 2023,
      supportedIndustries: [Industry.TECHNOLOGY, Industry.FINANCE, Industry.HEALTHCARE],
      businessImpact: {
        productivityIncrease: 60,
        costSavingsAnnual: 12000,
        revenueGenerationPotential: 50000,
        employeeEfficiencyGain: 45,
        digitalTransformationPoints: 80,
        marketingValue: 10000,
        customerSatisfactionImpact: 35,
        competitiveAdvantage: 75
      },
      maintenanceRequirements: {
        dailyCost: 8,
        weeklyCost: 45,
        monthlyCost: 200,
        annualServiceCost: 1200,
        expectedLifespan: 5,
        depreciation: 25,
        repairFrequency: 1,
        downtimeHours: 8
      },
      upgradeOptions: [
        {
          id: 'ram_upgrade_128gb',
          name: 'RAM Upgrade to 128GB',
          cost: 2000,
          impactOnSpecs: { ramGB: 128 },
          impactOnBusiness: { productivityIncrease: 75, revenueGenerationPotential: 60000 }
        },
        {
          id: 'storage_upgrade_4tb',
          name: 'Storage Upgrade to 4TB NVMe',
          cost: 1500,
          impactOnSpecs: { storageGB: 4000 },
          impactOnBusiness: { digitalTransformationPoints: 90 }
        }
      ],
      availability: 'in_stock'
    });

    // High-performance workstation computers
    this.addToCatalog({
      id: 'computer_mac_studio',
      name: 'Apple Mac Studio M2 Ultra',
      type: EquipmentType.COMPUTER,
      category: EquipmentCategory.OFFICE,
      basePrice: 4999,
      specifications: {
        powerConsumption: 215,
        dimensions: { width: 19.7, height: 9.5, depth: 19.7 },
        weight: 3.7,
        warranty: 12,
        cpuCores: 20,
        ramGB: 64,
        storageGB: 1000,
        processorSpeed: 3.5,
        graphicsCard: 'M2 Ultra GPU (76-core)',
        ports: ['4x Thunderbolt 4', '2x USB-A', '1x HDMI', '1x Ethernet'],
        operatingSystem: 'macOS'
      },
      manufacturer: 'Apple',
      model: 'Mac Studio M2 Ultra',
      releaseYear: 2023,
      supportedIndustries: [Industry.TECHNOLOGY, Industry.ENTERTAINMENT, Industry.EDUCATION],
      businessImpact: {
        productivityIncrease: 80,
        costSavingsAnnual: 3000,
        revenueGenerationPotential: 15000,
        employeeEfficiencyGain: 60,
        digitalTransformationPoints: 70,
        marketingValue: 8000,
        customerSatisfactionImpact: 25,
        competitiveAdvantage: 85
      },
      maintenanceRequirements: {
        dailyCost: 3,
        weeklyCost: 15,
        monthlyCost: 60,
        annualServiceCost: 300,
        expectedLifespan: 4,
        depreciation: 30,
        repairFrequency: 0.5,
        downtimeHours: 1
      },
      upgradeOptions: [],
      availability: 'in_stock'
    });

    // Manufacturing machinery
    this.addToCatalog({
      id: 'machinery_cnc_mill',
      name: 'Haas VF-2SS CNC Mill',
      type: EquipmentType.MACHINERY,
      category: EquipmentCategory.PRODUCTION,
      basePrice: 85000,
      specifications: {
        powerConsumption: 15000,
        dimensions: { width: 254, height: 254, depth: 213 },
        weight: 4300,
        warranty: 12,
        productionRate: 120,
        accuracy: 99.8,
        automation: true,
        compatibility: ['Steel', 'Aluminum', 'Plastic', 'Titanium']
      },
      manufacturer: 'Haas',
      model: 'VF-2SS',
      releaseYear: 2023,
      supportedIndustries: [Industry.MANUFACTURING, Industry.ENERGY, Industry.TRANSPORTATION],
      businessImpact: {
        productivityIncrease: 200,
        costSavingsAnnual: 45000,
        revenueGenerationPotential: 150000,
        employeeEfficiencyGain: 150,
        digitalTransformationPoints: 60,
        marketingValue: 25000,
        customerSatisfactionImpact: 80,
        competitiveAdvantage: 90
      },
      maintenanceRequirements: {
        dailyCost: 50,
        weeklyCost: 300,
        monthlyCost: 1200,
        annualServiceCost: 8500,
        expectedLifespan: 15,
        depreciation: 10,
        repairFrequency: 4,
        downtimeHours: 12
      },
      upgradeOptions: [
        {
          id: 'automation_upgrade',
          name: 'Full Automation Package',
          cost: 25000,
          impactOnSpecs: { productionRate: 180, automation: true },
          impactOnBusiness: { productivityIncrease: 300, revenueGenerationPotential: 200000 }
        }
      ],
      availability: 'in_stock'
    });

    // Office furniture - chairs, desks
    this.addToCatalog({
      id: 'furniture_herman_miller_chair',
      name: 'Herman Miller Aeron Chair',
      type: EquipmentType.FURNITURE,
      category: EquipmentCategory.OFFICE,
      basePrice: 1395,
      specifications: {
        powerConsumption: 0,
        dimensions: { width: 68, height: 94, depth: 67 },
        weight: 19,
        warranty: 144 // 12 years
      },
      manufacturer: 'Herman Miller',
      model: 'Aeron Chair Size B',
      releaseYear: 2023,
      supportedIndustries: Object.values(Industry), // All industries benefit
      businessImpact: {
        productivityIncrease: 5,
        costSavingsAnnual: 200,
        revenueGenerationPotential: 0,
        employeeEfficiencyGain: 8,
        digitalTransformationPoints: 0,
        marketingValue: 1000,
        customerSatisfactionImpact: 15,
        competitiveAdvantage: 10
      },
      maintenanceRequirements: {
        dailyCost: 0.1,
        weeklyCost: 0.5,
        monthlyCost: 2,
        annualServiceCost: 25,
        expectedLifespan: 12,
        depreciation: 8,
        repairFrequency: 0.1,
        downtimeHours: 0.5
      },
      upgradeOptions: [],
      availability: 'in_stock'
    });

    // Enterprise software
    this.addToCatalog({
      id: 'software_salesforce_enterprise',
      name: 'Salesforce Enterprise CRM',
      type: EquipmentType.SOFTWARE,
      category: EquipmentCategory.IT_INFRASTRUCTURE,
      basePrice: 300, // Monthly subscription per user
      specifications: {
        powerConsumption: 0,
        dimensions: { width: 0, height: 0, depth: 0 },
        weight: 0,
        warranty: 0, // Ongoing support
        maxConnections: 10000
      },
      manufacturer: 'Salesforce',
      model: 'Enterprise Edition',
      releaseYear: 2023,
      supportedIndustries: Object.values(Industry),
      businessImpact: {
        productivityIncrease: 35,
        costSavingsAnnual: 8000,
        revenueGenerationPotential: 25000,
        employeeEfficiencyGain: 40,
        digitalTransformationPoints: 85,
        marketingValue: 5000,
        customerSatisfactionImpact: 50,
        competitiveAdvantage: 70
      },
      maintenanceRequirements: {
        dailyCost: 10, // Per user per month
        weeklyCost: 70,
        monthlyCost: 300,
        annualServiceCost: 0, // Included in subscription
        expectedLifespan: 999, // Software doesn't depreciate physically
        depreciation: 0,
        repairFrequency: 0,
        downtimeHours: 0.1
      },
      upgradeOptions: [
        {
          id: 'ai_upgrade',
          name: 'Einstein AI Analytics',
          cost: 75, // Additional monthly per user
          impactOnSpecs: {},
          impactOnBusiness: { 
            productivityIncrease: 50, 
            revenueGenerationPotential: 35000,
            digitalTransformationPoints: 95
          }
        }
      ],
      availability: 'in_stock'
    });

    console.log(`✅ Equipment catalog initialized with ${this.catalog.size} items`);
  }

  /**
   * Purchase equipment for player or company
   */
  async purchaseEquipment(
    buyerId: string, 
    equipmentId: string, 
    quantity: number = 1,
    financing?: EquipmentFinancing
  ): Promise<{
    success: boolean;
    equipment?: Equipment[];
    totalCost: number;
    financing?: EquipmentFinancing;
    error?: string;
  }> {
    const catalogItem = this.catalog.get(equipmentId);
    if (!catalogItem) {
      return { success: false, totalCost: 0, error: 'Equipment not found in catalog' };
    }

    if (catalogItem.availability === 'discontinued') {
      return { success: false, totalCost: 0, error: 'Equipment is discontinued' };
    }

    // Calculate current market price
    const marketPrice = this.calculateMarketPrice(catalogItem);
    const totalCost = marketPrice * quantity;

    // Apply financing if provided
    let actualPayment = totalCost;
    if (financing) {
      actualPayment = financing.downPayment;
      
      // Validate financing terms
      const validationResult = this.validateFinancing(buyerId, totalCost, financing);
      if (!validationResult.approved) {
        return { success: false, totalCost, error: validationResult.reason };
      }
    }

    // Check if buyer can afford
    const affordabilityCheck = await this.checkAffordability(buyerId, actualPayment);
    if (!affordabilityCheck.canAfford) {
      return { 
        success: false, 
        totalCost, 
        error: `Insufficient funds. Need $${actualPayment.toLocaleString()}, have $${affordabilityCheck.availableFunds.toLocaleString()}` 
      };
    }

    // Create equipment instances
    const equipmentInstances: Equipment[] = [];
    for (let i = 0; i < quantity; i++) {
      const equipment: Equipment = {
        id: `${equipmentId}_${Date.now()}_${i}`,
        name: catalogItem.name,
        type: catalogItem.type,
        category: catalogItem.category,
        purchasePrice: marketPrice,
        currentValue: marketPrice,
        depreciation: catalogItem.maintenanceRequirements.depreciation,
        maintenanceCost: catalogItem.maintenanceRequirements.monthlyCost,
        productivity: catalogItem.businessImpact.productivityIncrease,
        efficiency: catalogItem.businessImpact.employeeEfficiencyGain,
        reliability: 100 - (catalogItem.maintenanceRequirements.repairFrequency * 10),
        purchaseDate: new Date(),
        warranty: catalogItem.specifications.warranty,
        expectedLifespan: catalogItem.maintenanceRequirements.expectedLifespan,
        condition: 100,
        specifications: catalogItem.specifications,
        powerConsumption: catalogItem.specifications.powerConsumption,
        spaceRequired: this.calculateSpaceRequired(catalogItem.specifications.dimensions),
        revenueGeneration: catalogItem.businessImpact.revenueGenerationPotential / 12, // Monthly
        costSavings: catalogItem.businessImpact.costSavingsAnnual / 12, // Monthly
        digitalTransformationBonus: catalogItem.businessImpact.digitalTransformationPoints
      };
      
      equipmentInstances.push(equipment);
    }

    // Process payment
    await this.processPayment(buyerId, actualPayment);

    // Add to appropriate inventory
    if (buyerId.startsWith('player_')) {
      const currentEquipment = this.playerEquipment.get(buyerId) || [];
      this.playerEquipment.set(buyerId, [...currentEquipment, ...equipmentInstances]);
    } else if (buyerId.startsWith('comp_')) {
      const currentEquipment = this.companyEquipment.get(buyerId) || [];
      this.companyEquipment.set(buyerId, [...currentEquipment, ...equipmentInstances]);
    }

    // Process financing if applicable
    if (financing) {
      await this.setupFinancing(buyerId, equipmentInstances[0].id, financing);
    }

    // Update catalog availability
    if (catalogItem.availability === 'limited') {
      // Simulate stock reduction
      if (Math.random() < 0.3) { // 30% chance to go to backorder
        catalogItem.availability = 'backorder';
      }
    }

    this.emit('equipment:purchased', {
      buyerId,
      equipment: equipmentInstances,
      totalCost,
      financing,
      catalogItem
    });

    console.log(`🛒 ${catalogItem.name} x${quantity} purchased by ${buyerId} for $${totalCost.toLocaleString()}`);

    return {
      success: true,
      equipment: equipmentInstances,
      totalCost,
      financing
    };
  }

  /**
   * Get equipment financing options
   */
  getFinancingOptions(
    buyerId: string, 
    equipmentId: string, 
    purchasePrice: number
  ): EquipmentFinancing[] {
    const catalogItem = this.catalog.get(equipmentId);
    if (!catalogItem) {
      return [];
    }

    const creditScore = this.getCreditScore(buyerId);
    const baseInterestRate = this.economyEngine.getState().interestRate + 2; // Equipment financing premium
    const creditAdjustment = (750 - creditScore) / 100; // Higher credit = lower rate
    
    const options: EquipmentFinancing[] = [];

    // Traditional Equipment Loan (2-7 years)
    [24, 36, 48, 60, 84].forEach(months => {
      const interestRate = (baseInterestRate + creditAdjustment) / 100;
      const monthlyPayment = this.calculateLoanPayment(purchasePrice * 0.9, interestRate, months); // 90% LTV
      
      options.push({
        type: 'loan',
        downPayment: purchasePrice * 0.1,
        monthlyPayment,
        term: months,
        interestRate: interestRate * 100,
        totalCost: (monthlyPayment * months) + (purchasePrice * 0.1),
        creditRequirement: 600,
        earlyPayoffPenalty: purchasePrice * 0.02, // 2% prepayment penalty
        taxBenefits: monthlyPayment * months * 0.21 // 21% depreciation tax benefit
      });
    });

    // Equipment Lease (2-5 years)
    [24, 36, 48, 60].forEach(months => {
      const residualValue = purchasePrice * Math.pow(1 - catalogItem.maintenanceRequirements.depreciation / 100, months / 12);
      const monthlyPayment = (purchasePrice - residualValue) / months + (purchasePrice * 0.02 / 12); // Money factor
      
      options.push({
        type: 'lease',
        downPayment: monthlyPayment * 2, // First and last month
        monthlyPayment,
        term: months,
        interestRate: 2, // Implied rate in lease factor
        totalCost: (monthlyPayment * months) + (monthlyPayment * 2),
        creditRequirement: 650,
        taxBenefits: monthlyPayment * months // Full deduction for business use
      });
    });

    // Rent-to-Own (Higher payments, lower credit requirements)
    [36, 48].forEach(months => {
      const monthlyPayment = purchasePrice * 1.4 / months; // 40% markup
      
      options.push({
        type: 'rent_to_own',
        downPayment: monthlyPayment,
        monthlyPayment,
        term: months,
        interestRate: 0, // Built into payment
        totalCost: monthlyPayment * (months + 1),
        creditRequirement: 550,
        taxBenefits: 0
      });
    });

    // Software Subscription (for software only)
    if (catalogItem.type === EquipmentType.SOFTWARE) {
      options.push({
        type: 'subscription',
        downPayment: 0,
        monthlyPayment: catalogItem.basePrice,
        term: 12,
        interestRate: 0,
        totalCost: catalogItem.basePrice * 12,
        creditRequirement: 0,
        taxBenefits: catalogItem.basePrice * 12 // Fully deductible
      });
    }

    // Filter based on credit score
    return options.filter(option => creditScore >= option.creditRequirement);
  }

  /**
   * Upgrade existing equipment
   */
  async upgradeEquipment(
    ownerId: string, 
    equipmentId: string, 
    upgradeId: string
  ): Promise<{
    success: boolean;
    upgradedEquipment?: Equipment;
    cost: number;
    error?: string;
  }> {
    const equipment = this.findEquipment(ownerId, equipmentId);
    if (!equipment) {
      return { success: false, cost: 0, error: 'Equipment not found' };
    }

    const catalogItem = this.catalog.get(equipment.name.toLowerCase().replace(/\s+/g, '_'));
    if (!catalogItem) {
      return { success: false, cost: 0, error: 'Original catalog item not found' };
    }

    const upgrade = catalogItem.upgradeOptions.find(u => u.id === upgradeId);
    if (!upgrade) {
      return { success: false, cost: 0, error: 'Upgrade option not found' };
    }

    // Check affordability
    const affordabilityCheck = await this.checkAffordability(ownerId, upgrade.cost);
    if (!affordabilityCheck.canAfford) {
      return { 
        success: false, 
        cost: upgrade.cost, 
        error: 'Insufficient funds for upgrade' 
      };
    }

    // Process payment
    await this.processPayment(ownerId, upgrade.cost);

    // Apply upgrade to equipment
    if (upgrade.impactOnSpecs) {
      equipment.specifications = { ...equipment.specifications, ...upgrade.impactOnSpecs };
    }

    if (upgrade.impactOnBusiness) {
      if (upgrade.impactOnBusiness.productivityIncrease) {
        equipment.productivity += upgrade.impactOnBusiness.productivityIncrease;
      }
      if (upgrade.impactOnBusiness.costSavingsAnnual) {
        equipment.costSavings += upgrade.impactOnBusiness.costSavingsAnnual / 12;
      }
      if (upgrade.impactOnBusiness.revenueGenerationPotential) {
        equipment.revenueGeneration += upgrade.impactOnBusiness.revenueGenerationPotential / 12;
      }
    }

    // Increase equipment value
    equipment.currentValue += upgrade.cost * 0.7; // 70% value retention

    this.emit('equipment:upgraded', {
      ownerId,
      equipment,
      upgrade,
      cost: upgrade.cost
    });

    console.log(`⬆️ ${equipment.name} upgraded with ${upgrade.name} for $${upgrade.cost.toLocaleString()}`);

    return {
      success: true,
      upgradedEquipment: equipment,
      cost: upgrade.cost
    };
  }

  /**
   * Calculate ROI for equipment purchase
   */
  calculateROI(
    equipmentId: string, 
    analysisYears: number = 5
  ): {
    equipment: EquipmentCatalog;
    investment: number;
    annualBenefits: number;
    totalBenefits: number;
    netPresentValue: number;
    internalRateOfReturn: number;
    paybackPeriod: number; // years
    profitabilityIndex: number;
    riskAdjustedReturn: number;
    recommendation: 'strongly_recommended' | 'recommended' | 'neutral' | 'not_recommended';
  } | null {
    const catalogItem = this.catalog.get(equipmentId);
    if (!catalogItem) {
      return null;
    }

    const currentPrice = this.calculateMarketPrice(catalogItem);
    const annualBenefits = catalogItem.businessImpact.costSavingsAnnual + 
                          catalogItem.businessImpact.revenueGenerationPotential;
    const annualCosts = catalogItem.maintenanceRequirements.annualServiceCost +
                       (catalogItem.maintenanceRequirements.monthlyCost * 12);
    const netAnnualBenefits = annualBenefits - annualCosts;
    
    // NPV calculation
    const discountRate = 0.1; // 10% WACC
    let npv = -currentPrice; // Initial investment
    for (let year = 1; year <= analysisYears; year++) {
      const yearBenefit = netAnnualBenefits * Math.pow(0.95, year - 1); // 5% degradation per year
      npv += yearBenefit / Math.pow(1 + discountRate, year);
    }

    // Add terminal value (resale value)
    const terminalValue = currentPrice * Math.pow(1 - catalogItem.maintenanceRequirements.depreciation / 100, analysisYears);
    npv += terminalValue / Math.pow(1 + discountRate, analysisYears);

    // IRR calculation (simplified)
    let irr = 0.1; // Starting guess
    for (let iteration = 0; iteration < 100; iteration++) {
      let f = -currentPrice;
      let df = 0;
      
      for (let year = 1; year <= analysisYears; year++) {
        const yearBenefit = netAnnualBenefits * Math.pow(0.95, year - 1);
        f += yearBenefit / Math.pow(1 + irr, year);
        df -= year * yearBenefit / Math.pow(1 + irr, year + 1);
      }
      
      f += terminalValue / Math.pow(1 + irr, analysisYears);
      df -= analysisYears * terminalValue / Math.pow(1 + irr, analysisYears + 1);
      
      const newIrr = irr - f / df;
      if (Math.abs(newIrr - irr) < 0.0001) {
        irr = newIrr;
        break;
      }
      irr = newIrr;
    }

    // Payback period
    let cumulativeCashFlow = -currentPrice;
    let paybackPeriod = analysisYears;
    for (let year = 1; year <= analysisYears; year++) {
      cumulativeCashFlow += netAnnualBenefits * Math.pow(0.95, year - 1);
      if (cumulativeCashFlow >= 0 && paybackPeriod === analysisYears) {
        paybackPeriod = year - 1 + (-cumulativeCashFlow + netAnnualBenefits * Math.pow(0.95, year - 1)) / (netAnnualBenefits * Math.pow(0.95, year - 1));
        break;
      }
    }

    // Profitability Index
    const profitabilityIndex = (npv + currentPrice) / currentPrice;

    // Risk adjustment based on equipment type and age
    const riskFactor = this.calculateRiskFactor(catalogItem);
    const riskAdjustedReturn = irr - riskFactor;

    // Recommendation logic
    let recommendation: 'strongly_recommended' | 'recommended' | 'neutral' | 'not_recommended';
    if (npv > currentPrice * 0.3 && irr > 0.2 && paybackPeriod < 3) {
      recommendation = 'strongly_recommended';
    } else if (npv > 0 && irr > discountRate && paybackPeriod < 4) {
      recommendation = 'recommended';
    } else if (npv > -currentPrice * 0.1 && irr > 0) {
      recommendation = 'neutral';
    } else {
      recommendation = 'not_recommended';
    }

    return {
      equipment: catalogItem,
      investment: currentPrice,
      annualBenefits: netAnnualBenefits,
      totalBenefits: netAnnualBenefits * analysisYears,
      netPresentValue: npv,
      internalRateOfReturn: irr,
      paybackPeriod,
      profitabilityIndex,
      riskAdjustedReturn,
      recommendation
    };
  }

  /**
   * Get equipment maintenance schedule and costs
   */
  getMaintenanceSchedule(
    ownerId: string, 
    equipmentId: string
  ): {
    equipment: Equipment;
    schedule: Array<{
      date: Date;
      type: 'daily' | 'weekly' | 'monthly' | 'annual' | 'repair';
      description: string;
      cost: number;
      duration: number; // hours
      critical: boolean;
    }>;
    totalAnnualCost: number;
    predictedDowntime: number; // hours per year
  } | null {
    const equipment = this.findEquipment(ownerId, equipmentId);
    if (!equipment) {
      return null;
    }

    const schedule: Array<{
      date: Date;
      type: 'daily' | 'weekly' | 'monthly' | 'annual' | 'repair';
      description: string;
      cost: number;
      duration: number;
      critical: boolean;
    }> = [];

    const now = new Date();
    
    // Daily maintenance
    for (let day = 1; day <= 365; day++) {
      const date = new Date(now);
      date.setDate(date.getDate() + day);
      
      schedule.push({
        date,
        type: 'daily',
        description: 'Daily inspection and cleaning',
        cost: equipment.maintenanceCost / 30, // Daily portion of monthly cost
        duration: 0.25, // 15 minutes
        critical: false
      });
    }

    // Weekly maintenance
    for (let week = 1; week <= 52; week++) {
      const date = new Date(now);
      date.setDate(date.getDate() + (week * 7));
      
      schedule.push({
        date,
        type: 'weekly',
        description: 'Weekly calibration and performance check',
        cost: equipment.maintenanceCost * 0.25, // 25% of monthly cost
        duration: 2,
        critical: equipment.type === EquipmentType.MACHINERY || equipment.type === EquipmentType.SERVER
      });
    }

    // Monthly maintenance
    for (let month = 1; month <= 12; month++) {
      const date = new Date(now);
      date.setMonth(date.getMonth() + month);
      
      schedule.push({
        date,
        type: 'monthly',
        description: 'Comprehensive monthly service',
        cost: equipment.maintenanceCost,
        duration: 4,
        critical: true
      });
    }

    // Annual service
    const annualDate = new Date(now);
    annualDate.setFullYear(annualDate.getFullYear() + 1);
    
    schedule.push({
      date: annualDate,
      type: 'annual',
      description: 'Annual comprehensive service and certification',
      cost: equipment.maintenanceCost * 3, // 3 months worth
      duration: 8,
      critical: true
    });

    // Predicted repairs based on reliability
    const repairFrequency = (100 - equipment.reliability) / 10; // Repairs per year
    for (let i = 0; i < Math.ceil(repairFrequency); i++) {
      const repairDate = new Date(now);
      repairDate.setDate(repairDate.getDate() + Math.floor(Math.random() * 365));
      
      schedule.push({
        date: repairDate,
        type: 'repair',
        description: 'Unplanned repair and replacement',
        cost: equipment.purchasePrice * 0.05, // 5% of purchase price
        duration: equipment.type === EquipmentType.MACHINERY ? 12 : 4,
        critical: true
      });
    }

    const totalAnnualCost = schedule.reduce((sum, item) => sum + item.cost, 0);
    const predictedDowntime = schedule
      .filter(item => item.critical)
      .reduce((sum, item) => sum + item.duration, 0);

    return {
      equipment,
      schedule: schedule.sort((a, b) => a.date.getTime() - b.date.getTime()),
      totalAnnualCost,
      predictedDowntime
    };
  }

  /**
   * Start market updates for equipment pricing
   */
  private startMarketUpdates(): void {
    setInterval(() => {
      this.updateMarketConditions();
    }, 60000); // Update every minute
  }

  /**
   * Update market conditions and pricing
   */
  private updateMarketConditions(): void {
    const economyState = this.economyEngine.getState();
    
    Object.values(EquipmentType).forEach(type => {
      let marketMultiplier = 1.0;
      
      // Economic cycle effects
      switch (economyState.economicCycle) {
        case 'recession':
          marketMultiplier *= 0.85; // 15% discount during recession
          break;
        case 'expansion':
          marketMultiplier *= 1.15; // 15% premium during expansion
          break;
      }
      
      // Technology advancement effects
      const currentCycle = this.technologyCycles.get(type) || 0;
      this.technologyCycles.set(type, currentCycle + 0.1);
      
      if (type === EquipmentType.COMPUTER || type === EquipmentType.SERVER) {
        marketMultiplier *= (1 - currentCycle * 0.02); // Technology gets cheaper over time
      }
      
      // Supply and demand fluctuations
      marketMultiplier *= (0.95 + Math.random() * 0.1); // ±5% random variation
      
      this.marketTrends.set(type, marketMultiplier);
    });
  }

  /**
   * Helper methods
   */
  private addToCatalog(item: EquipmentCatalog): void {
    this.catalog.set(item.id, item);
  }

  private calculateMarketPrice(catalogItem: EquipmentCatalog): number {
    const marketMultiplier = this.marketTrends.get(catalogItem.type) || 1.0;
    return Math.round(catalogItem.basePrice * marketMultiplier);
  }

  private calculateSpaceRequired(dimensions: { width: number; height: number; depth: number }): number {
    return (dimensions.width * dimensions.depth) / 10000; // Convert cm² to m²
  }

  private calculateLoanPayment(principal: number, monthlyRate: number, terms: number): number {
    if (monthlyRate === 0) return principal / terms;
    return principal * (monthlyRate * Math.pow(1 + monthlyRate, terms)) / (Math.pow(1 + monthlyRate, terms) - 1);
  }

  private getCreditScore(buyerId: string): number {
    // Simplified credit score calculation
    // In real implementation, this would query player/company credit history
    return 650 + Math.floor(Math.random() * 200); // 650-850 range
  }

  private validateFinancing(buyerId: string, amount: number, financing: EquipmentFinancing): { approved: boolean; reason?: string } {
    const creditScore = this.getCreditScore(buyerId);
    
    if (creditScore < financing.creditRequirement) {
      return { approved: false, reason: 'Credit score too low' };
    }
    
    if (financing.downPayment < amount * 0.05) {
      return { approved: false, reason: 'Down payment too low (minimum 5%)' };
    }
    
    return { approved: true };
  }

  private async checkAffordability(buyerId: string, amount: number): Promise<{ canAfford: boolean; availableFunds: number }> {
    // In real implementation, this would check actual player/company cash
    const availableFunds = Math.floor(Math.random() * 100000) + 10000; // $10k-$110k
    return {
      canAfford: availableFunds >= amount,
      availableFunds
    };
  }

  private async processPayment(buyerId: string, amount: number): Promise<void> {
    // In real implementation, this would deduct from actual player/company funds
    console.log(`💳 Processed payment of $${amount.toLocaleString()} from ${buyerId}`);
  }

  private async setupFinancing(buyerId: string, equipmentId: string, financing: EquipmentFinancing): Promise<void> {
    // Create financing record for monthly payments
    console.log(`📄 Set up ${financing.type} financing for ${equipmentId}: $${financing.monthlyPayment.toLocaleString()}/month`);
  }

  private findEquipment(ownerId: string, equipmentId: string): Equipment | undefined {
    const playerEquipment = this.playerEquipment.get(ownerId);
    const companyEquipment = this.companyEquipment.get(ownerId);
    
    const allEquipment = [...(playerEquipment || []), ...(companyEquipment || [])];
    return allEquipment.find(eq => eq.id === equipmentId);
  }

  private calculateRiskFactor(catalogItem: EquipmentCatalog): number {
    let risk = 0.02; // Base 2% risk
    
    if (catalogItem.type === EquipmentType.MACHINERY) risk += 0.03;
    if (catalogItem.releaseYear < 2020) risk += 0.02;
    if (catalogItem.maintenanceRequirements.repairFrequency > 2) risk += 0.01;
    
    return risk;
  }

  // Public methods
  public getCatalog(): EquipmentCatalog[] {
    return Array.from(this.catalog.values());
  }

  public getEquipmentByCategory(category: EquipmentCategory): EquipmentCatalog[] {
    return Array.from(this.catalog.values()).filter(item => item.category === category);
  }

  public getEquipmentByType(type: EquipmentType): EquipmentCatalog[] {
    return Array.from(this.catalog.values()).filter(item => item.type === type);
  }

  public getPlayerEquipment(playerId: string): Equipment[] {
    return this.playerEquipment.get(playerId) || [];
  }

  public getCompanyEquipment(companyId: string): Equipment[] {
    return this.companyEquipment.get(companyId) || [];
  }
}