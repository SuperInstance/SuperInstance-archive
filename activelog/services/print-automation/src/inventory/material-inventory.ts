import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

export interface MaterialType {
  id: string;
  name: string;
  category: 'thermoplastic' | 'resin' | 'metal' | 'ceramic' | 'composite' | 'support';
  properties: {
    printingTemperature: {
      hotend: { min: number; max: number };
      bed: { min: number; max: number };
      chamber?: { min: number; max: number };
    };
    mechanicalProperties: {
      tensileStrength: number; // MPa
      flexuralStrength: number; // MPa
      impactStrength: number; // kJ/m²
      hardness: string;
      density: number; // g/cm³
    };
    thermalProperties: {
      glassTransitionTemp?: number; // °C
      meltingPoint?: number; // °C
      heatDeflectionTemp?: number; // °C
      thermalConductivity: number; // W/mK
    };
    chemicalProperties: {
      chemicalResistance: string[];
      uvResistance: 'poor' | 'fair' | 'good' | 'excellent';
      foodSafe: boolean;
      biocompatible: boolean;
    };
    printingProperties: {
      shrinkage: number; // %
      warping: 'low' | 'medium' | 'high';
      supportRequired: boolean;
      enclosureRequired: boolean;
      adhesion: 'poor' | 'fair' | 'good' | 'excellent';
      overhangAngle: number; // degrees
      bridgeDistance: number; // mm
    };
  };
  compatiblePrinters: string[];
  applications: string[];
  hazards?: {
    toxicity: string;
    flammability: string;
    handling: string;
    disposal: string;
  };
  certifications?: string[];
  createdAt: Date;
  updatedAt: Date;
}

export interface MaterialSpool {
  id: string;
  materialTypeId: string;
  brand: string;
  productName: string;
  color: string;
  diameter: number; // mm
  weight: {
    original: number; // grams
    current: number; // grams
    used: number; // grams
  };
  length: {
    original?: number; // meters
    current?: number; // meters
    used?: number; // meters
  };
  cost: {
    purchase: number;
    perGram: number;
    perMeter?: number;
  };
  supplier: {
    name: string;
    contactInfo?: string;
    orderNumber?: string;
  };
  qualityData: {
    diameterTolerance: number; // ±mm
    roundnessTolerance: number; // mm
    colorConsistency: 'poor' | 'fair' | 'good' | 'excellent';
    surfaceFinish: 'poor' | 'fair' | 'good' | 'excellent';
  };
  storageConditions: {
    temperature: { min: number; max: number }; // °C
    humidity: { min: number; max: number }; // %
    lightExposure: boolean;
    sealedContainer: boolean;
  };
  batchInfo: {
    lotNumber: string;
    manufactureDate: Date;
    expirationDate?: Date;
    qualityControlPassed: boolean;
  };
  location: {
    facility: string;
    zone: string;
    rack?: string;
    position?: string;
    coordinates?: { x: number; y: number; z: number };
  };
  qrCode?: string;
  rfidTag?: string;
  usageHistory: MaterialUsage[];
  status: 'available' | 'in-use' | 'low-stock' | 'empty' | 'expired' | 'quarantine';
  alerts: MaterialAlert[];
  createdAt: Date;
  updatedAt: Date;
}

export interface MaterialUsage {
  id: string;
  spoolId: string;
  jobId: string;
  printerId: string;
  amountUsed: number; // grams
  lengthUsed?: number; // meters
  usageDate: Date;
  printQuality: 'excellent' | 'good' | 'fair' | 'poor';
  issues?: string[];
  notes?: string;
}

export interface MaterialAlert {
  id: string;
  type: 'low-stock' | 'expired' | 'quality-issue' | 'reorder' | 'storage-condition' | 'compatibility';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  threshold?: number;
  currentValue?: number;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: Date;
  resolved: boolean;
  resolvedBy?: string;
  resolvedAt?: Date;
  createdAt: Date;
}

export interface InventoryOrder {
  id: string;
  materialTypeId: string;
  supplierId: string;
  quantity: number;
  unitCost: number;
  totalCost: number;
  status: 'draft' | 'pending' | 'ordered' | 'shipped' | 'delivered' | 'cancelled';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  orderDate: Date;
  expectedDelivery?: Date;
  actualDelivery?: Date;
  orderNumber?: string;
  trackingNumber?: string;
  notes?: string;
  createdBy: string;
  approvedBy?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface Supplier {
  id: string;
  name: string;
  type: 'manufacturer' | 'distributor' | 'retailer';
  contactInfo: {
    email: string;
    phone?: string;
    website?: string;
    address: {
      street: string;
      city: string;
      state: string;
      country: string;
      postalCode: string;
    };
  };
  materials: string[]; // Material type IDs
  performance: {
    rating: number; // 1-5
    onTimeDelivery: number; // %
    qualityScore: number; // 1-5
    priceCompetitiveness: number; // 1-5
    customerService: number; // 1-5
  };
  terms: {
    paymentTerms: string;
    minOrderAmount?: number;
    leadTimeDays: number;
    shippingCosts: number;
    returnsPolicy: string;
  };
  certifications: string[];
  isActive: boolean;
  lastOrderDate?: Date;
  totalOrders: number;
  totalSpent: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface InventoryReport {
  totalMaterials: number;
  totalValue: number;
  lowStockItems: MaterialSpool[];
  expiredItems: MaterialSpool[];
  utilizationRate: number;
  turnoverRate: number;
  topMaterials: { material: MaterialType; usage: number }[];
  costAnalysis: {
    totalSpent: number;
    averageCostPerGram: number;
    wastePercentage: number;
  };
  qualityMetrics: {
    averageQuality: number;
    issueRate: number;
    supplierPerformance: { supplier: Supplier; score: number }[];
  };
  forecastData: {
    material: MaterialType;
    predictedConsumption: number;
    recommendedOrder: number;
  }[];
}

export class MaterialInventoryManager extends EventEmitter {
  private materialTypes: Map<string, MaterialType> = new Map();
  private spools: Map<string, MaterialSpool> = new Map();
  private suppliers: Map<string, Supplier> = new Map();
  private orders: Map<string, InventoryOrder> = new Map();
  private usageHistory: Map<string, MaterialUsage> = new Map();
  private alerts: Map<string, MaterialAlert> = new Map();
  private monitoringInterval?: NodeJS.Timeout;

  constructor() {
    super();
    this.initializeDefaultData();
    this.startMonitoring();
  }

  private initializeDefaultData(): void {
    this.createDefaultMaterialTypes();
    this.createDefaultSuppliers();
    this.createSampleSpools();
  }

  private createDefaultMaterialTypes(): void {
    const materialTypes: Omit<MaterialType, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'PLA',
        category: 'thermoplastic',
        properties: {
          printingTemperature: {
            hotend: { min: 190, max: 220 },
            bed: { min: 50, max: 70 }
          },
          mechanicalProperties: {
            tensileStrength: 50,
            flexuralStrength: 80,
            impactStrength: 5.5,
            hardness: 'Shore D 75',
            density: 1.24
          },
          thermalProperties: {
            glassTransitionTemp: 60,
            meltingPoint: 150,
            heatDeflectionTemp: 55,
            thermalConductivity: 0.13
          },
          chemicalProperties: {
            chemicalResistance: ['water', 'acids'],
            uvResistance: 'fair',
            foodSafe: true,
            biocompatible: true
          },
          printingProperties: {
            shrinkage: 0.4,
            warping: 'low',
            supportRequired: false,
            enclosureRequired: false,
            adhesion: 'excellent',
            overhangAngle: 45,
            bridgeDistance: 5
          }
        },
        compatiblePrinters: ['all'],
        applications: ['prototyping', 'decorative', 'educational', 'food-containers'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        name: 'ABS',
        category: 'thermoplastic',
        properties: {
          printingTemperature: {
            hotend: { min: 220, max: 280 },
            bed: { min: 80, max: 110 }
          },
          mechanicalProperties: {
            tensileStrength: 40,
            flexuralStrength: 60,
            impactStrength: 15,
            hardness: 'Shore D 85',
            density: 1.04
          },
          thermalProperties: {
            glassTransitionTemp: 105,
            meltingPoint: 200,
            heatDeflectionTemp: 98,
            thermalConductivity: 0.17
          },
          chemicalProperties: {
            chemicalResistance: ['oils', 'bases', 'alcohols'],
            uvResistance: 'poor',
            foodSafe: false,
            biocompatible: false
          },
          printingProperties: {
            shrinkage: 0.8,
            warping: 'high',
            supportRequired: true,
            enclosureRequired: true,
            adhesion: 'fair',
            overhangAngle: 35,
            bridgeDistance: 3
          }
        },
        compatiblePrinters: ['heated-bed', 'enclosure'],
        applications: ['automotive', 'electronics', 'mechanical-parts', 'tools'],
        hazards: {
          toxicity: 'Low - may emit styrene fumes',
          flammability: 'Combustible',
          handling: 'Use ventilation during printing',
          disposal: 'Recyclable - code 7'
        },
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        name: 'PETG',
        category: 'thermoplastic',
        properties: {
          printingTemperature: {
            hotend: { min: 220, max: 250 },
            bed: { min: 70, max: 90 }
          },
          mechanicalProperties: {
            tensileStrength: 50,
            flexuralStrength: 69,
            impactStrength: 8,
            hardness: 'Shore D 85',
            density: 1.27
          },
          thermalProperties: {
            glassTransitionTemp: 88,
            thermalConductivity: 0.15
          },
          chemicalProperties: {
            chemicalResistance: ['acids', 'bases', 'alcohols'],
            uvResistance: 'good',
            foodSafe: true,
            biocompatible: true
          },
          printingProperties: {
            shrinkage: 0.2,
            warping: 'medium',
            supportRequired: false,
            enclosureRequired: false,
            adhesion: 'good',
            overhangAngle: 40,
            bridgeDistance: 4
          }
        },
        compatiblePrinters: ['heated-bed'],
        applications: ['food-containers', 'medical', 'chemical-resistant', 'transparent-parts'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        name: 'TPU',
        category: 'thermoplastic',
        properties: {
          printingTemperature: {
            hotend: { min: 210, max: 230 },
            bed: { min: 40, max: 60 }
          },
          mechanicalProperties: {
            tensileStrength: 35,
            flexuralStrength: 25,
            impactStrength: 50,
            hardness: 'Shore A 95',
            density: 1.2
          },
          thermalProperties: {
            thermalConductivity: 0.25
          },
          chemicalProperties: {
            chemicalResistance: ['oils', 'greases'],
            uvResistance: 'fair',
            foodSafe: false,
            biocompatible: false
          },
          printingProperties: {
            shrinkage: 1.0,
            warping: 'low',
            supportRequired: true,
            enclosureRequired: false,
            adhesion: 'good',
            overhangAngle: 25,
            bridgeDistance: 2
          }
        },
        compatiblePrinters: ['direct-drive'],
        applications: ['gaskets', 'phone-cases', 'footwear', 'flexible-joints'],
        createdAt: new Date(),
        updatedAt: new Date()
      }
    ];

    materialTypes.forEach(typeData => {
      const materialType: MaterialType = {
        ...typeData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.materialTypes.set(materialType.id, materialType);
    });
  }

  private createDefaultSuppliers(): void {
    const suppliers: Omit<Supplier, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Hatchbox',
        type: 'manufacturer',
        contactInfo: {
          email: 'sales@hatchbox3d.com',
          website: 'https://www.hatchbox3d.com',
          address: {
            street: '123 Manufacturing St',
            city: 'Los Angeles',
            state: 'CA',
            country: 'USA',
            postalCode: '90210'
          }
        },
        materials: [], // Will be populated
        performance: {
          rating: 4.5,
          onTimeDelivery: 95,
          qualityScore: 4.7,
          priceCompetitiveness: 4.2,
          customerService: 4.5
        },
        terms: {
          paymentTerms: 'Net 30',
          minOrderAmount: 50,
          leadTimeDays: 3,
          shippingCosts: 15,
          returnsPolicy: '30 days'
        },
        certifications: ['ISO 9001', 'FDA Approved'],
        isActive: true,
        totalOrders: 0,
        totalSpent: 0
      },
      {
        name: 'Overture',
        type: 'manufacturer',
        contactInfo: {
          email: 'support@overture3d.com',
          website: 'https://overture3d.com',
          address: {
            street: '456 Innovation Ave',
            city: 'Seattle',
            state: 'WA',
            country: 'USA',
            postalCode: '98101'
          }
        },
        materials: [],
        performance: {
          rating: 4.3,
          onTimeDelivery: 88,
          qualityScore: 4.4,
          priceCompetitiveness: 4.6,
          customerService: 4.1
        },
        terms: {
          paymentTerms: 'Net 15',
          minOrderAmount: 25,
          leadTimeDays: 5,
          shippingCosts: 12,
          returnsPolicy: '45 days'
        },
        certifications: ['ISO 14001'],
        isActive: true,
        totalOrders: 0,
        totalSpent: 0
      }
    ];

    suppliers.forEach(supplierData => {
      const supplier: Supplier = {
        ...supplierData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.suppliers.set(supplier.id, supplier);
    });
  }

  private createSampleSpools(): void {
    const materialTypeIds = Array.from(this.materialTypes.keys());
    const supplierIds = Array.from(this.suppliers.keys());

    for (let i = 0; i < 15; i++) {
      const materialTypeId = materialTypeIds[Math.floor(Math.random() * materialTypeIds.length)];
      const materialType = this.materialTypes.get(materialTypeId)!;
      const supplierId = supplierIds[Math.floor(Math.random() * supplierIds.length)];
      const supplier = this.suppliers.get(supplierId)!;

      const colors = ['Black', 'White', 'Red', 'Blue', 'Green', 'Yellow', 'Orange', 'Purple', 'Gray', 'Clear'];
      const originalWeight = 1000; // 1kg spools
      const usedWeight = Math.random() * 500; // 0-500g used

      const spool: MaterialSpool = {
        id: uuidv4(),
        materialTypeId,
        brand: supplier.name,
        productName: `${materialType.name} Filament`,
        color: colors[Math.floor(Math.random() * colors.length)],
        diameter: 1.75,
        weight: {
          original: originalWeight,
          current: originalWeight - usedWeight,
          used: usedWeight
        },
        length: {
          original: Math.round(originalWeight / (materialType.properties.mechanicalProperties.density * Math.PI * (0.875) ** 2)),
          current: Math.round((originalWeight - usedWeight) / (materialType.properties.mechanicalProperties.density * Math.PI * (0.875) ** 2)),
          used: Math.round(usedWeight / (materialType.properties.mechanicalProperties.density * Math.PI * (0.875) ** 2))
        },
        cost: {
          purchase: 20 + Math.random() * 30,
          perGram: (20 + Math.random() * 30) / originalWeight
        },
        supplier: {
          name: supplier.name,
          contactInfo: supplier.contactInfo.email
        },
        qualityData: {
          diameterTolerance: 0.02 + Math.random() * 0.03,
          roundnessTolerance: 0.01 + Math.random() * 0.02,
          colorConsistency: ['excellent', 'good', 'fair'][Math.floor(Math.random() * 3)] as any,
          surfaceFinish: ['excellent', 'good', 'fair'][Math.floor(Math.random() * 3)] as any
        },
        storageConditions: {
          temperature: { min: 15, max: 25 },
          humidity: { min: 20, max: 50 },
          lightExposure: false,
          sealedContainer: true
        },
        batchInfo: {
          lotNumber: `LOT${Math.random().toString(36).substr(2, 9).toUpperCase()}`,
          manufactureDate: new Date(Date.now() - Math.random() * 180 * 24 * 60 * 60 * 1000),
          qualityControlPassed: true
        },
        location: {
          facility: Math.random() > 0.5 ? 'Main Warehouse' : 'Secondary Storage',
          zone: `Zone ${String.fromCharCode(65 + Math.floor(Math.random() * 5))}`,
          rack: `R${Math.floor(Math.random() * 10) + 1}`,
          position: `P${Math.floor(Math.random() * 20) + 1}`
        },
        qrCode: `QR${uuidv4().slice(0, 8)}`,
        usageHistory: [],
        status: usedWeight > originalWeight * 0.8 ? 'low-stock' : 
               usedWeight > originalWeight * 0.95 ? 'empty' : 'available',
        alerts: [],
        createdAt: new Date(Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000),
        updatedAt: new Date()
      };

      // Set expiration date for some materials
      if (Math.random() > 0.7) {
        spool.batchInfo.expirationDate = new Date(spool.batchInfo.manufactureDate.getTime() + 365 * 24 * 60 * 60 * 1000);
      }

      this.spools.set(spool.id, spool);

      // Update supplier materials
      if (!supplier.materials.includes(materialTypeId)) {
        supplier.materials.push(materialTypeId);
      }
    }
  }

  private startMonitoring(): void {
    this.monitoringInterval = setInterval(() => {
      this.checkStockLevels();
      this.checkExpirationDates();
      this.checkStorageConditions();
      this.generateReorderAlerts();
    }, 60000); // Check every minute
  }

  private checkStockLevels(): void {
    this.spools.forEach((spool, spoolId) => {
      const usagePercentage = (spool.weight.used / spool.weight.original) * 100;
      
      if (usagePercentage > 90 && spool.status !== 'empty') {
        spool.status = 'empty';
        this.createAlert(spoolId, {
          type: 'low-stock',
          severity: 'critical',
          message: `Material spool ${spool.brand} ${spool.color} ${spool.materialTypeId} is empty`,
          threshold: 90,
          currentValue: usagePercentage
        });
      } else if (usagePercentage > 80 && spool.status === 'available') {
        spool.status = 'low-stock';
        this.createAlert(spoolId, {
          type: 'low-stock',
          severity: 'high',
          message: `Material spool ${spool.brand} ${spool.color} ${spool.materialTypeId} is running low`,
          threshold: 80,
          currentValue: usagePercentage
        });
      }
    });
  }

  private checkExpirationDates(): void {
    const now = new Date();
    const thirtyDaysFromNow = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);

    this.spools.forEach((spool, spoolId) => {
      if (spool.batchInfo.expirationDate) {
        if (spool.batchInfo.expirationDate < now && spool.status !== 'expired') {
          spool.status = 'expired';
          this.createAlert(spoolId, {
            type: 'expired',
            severity: 'critical',
            message: `Material spool ${spool.brand} ${spool.color} has expired`,
            currentValue: spool.batchInfo.expirationDate.getTime()
          });
        } else if (spool.batchInfo.expirationDate < thirtyDaysFromNow) {
          this.createAlert(spoolId, {
            type: 'expired',
            severity: 'medium',
            message: `Material spool ${spool.brand} ${spool.color} expires soon`,
            threshold: thirtyDaysFromNow.getTime(),
            currentValue: spool.batchInfo.expirationDate.getTime()
          });
        }
      }
    });
  }

  private checkStorageConditions(): void {
    // Simulate storage condition monitoring
    this.spools.forEach((spool, spoolId) => {
      // Simulate random storage condition violations
      if (Math.random() < 0.01) { // 1% chance per check
        const violations = [];
        
        if (Math.random() > 0.5) {
          violations.push('Temperature exceeded recommended range');
        }
        
        if (Math.random() > 0.7) {
          violations.push('Humidity too high');
        }

        if (violations.length > 0) {
          this.createAlert(spoolId, {
            type: 'storage-condition',
            severity: 'medium',
            message: `Storage condition violation: ${violations.join(', ')}`
          });
        }
      }
    });
  }

  private generateReorderAlerts(): void {
    // Group spools by material type and calculate total available
    const materialInventory = new Map<string, number>();
    
    this.spools.forEach(spool => {
      if (spool.status === 'available' || spool.status === 'low-stock') {
        const current = materialInventory.get(spool.materialTypeId) || 0;
        materialInventory.set(spool.materialTypeId, current + spool.weight.current);
      }
    });

    // Check if any material type is below reorder threshold
    materialInventory.forEach((totalWeight, materialTypeId) => {
      const reorderThreshold = 2000; // 2kg minimum
      
      if (totalWeight < reorderThreshold) {
        this.createAlert(materialTypeId, {
          type: 'reorder',
          severity: 'high',
          message: `Material type ${materialTypeId} is below reorder threshold`,
          threshold: reorderThreshold,
          currentValue: totalWeight
        });
      }
    });
  }

  private createAlert(entityId: string, alertData: Omit<MaterialAlert, 'id' | 'acknowledged' | 'resolved' | 'createdAt'>): void {
    const alert: MaterialAlert = {
      ...alertData,
      id: uuidv4(),
      acknowledged: false,
      resolved: false,
      createdAt: new Date()
    };

    this.alerts.set(alert.id, alert);

    // Add alert to spool if it's a spool-specific alert
    const spool = this.spools.get(entityId);
    if (spool) {
      spool.alerts.push(alert);
      spool.updatedAt = new Date();
    }

    this.emit('alertCreated', alert);
  }

  async addMaterialType(typeData: Omit<MaterialType, 'id' | 'createdAt' | 'updatedAt'>): Promise<MaterialType> {
    const materialType: MaterialType = {
      ...typeData,
      id: uuidv4(),
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.materialTypes.set(materialType.id, materialType);
    this.emit('materialTypeAdded', materialType);
    
    return materialType;
  }

  async addSpool(spoolData: Omit<MaterialSpool, 'id' | 'usageHistory' | 'alerts' | 'createdAt' | 'updatedAt'>): Promise<MaterialSpool> {
    const spool: MaterialSpool = {
      ...spoolData,
      id: uuidv4(),
      usageHistory: [],
      alerts: [],
      createdAt: new Date(),
      updatedAt: new Date()
    };

    // Generate QR code if not provided
    if (!spool.qrCode) {
      spool.qrCode = `QR${uuidv4().slice(0, 8)}`;
    }

    this.spools.set(spool.id, spool);
    this.emit('spoolAdded', spool);
    
    return spool;
  }

  async useMaterial(spoolId: string, usage: Omit<MaterialUsage, 'id' | 'spoolId' | 'usageDate'>): Promise<MaterialUsage> {
    const spool = this.spools.get(spoolId);
    if (!spool) {
      throw new Error('Spool not found');
    }

    if (spool.weight.current < usage.amountUsed) {
      throw new Error('Insufficient material available');
    }

    const materialUsage: MaterialUsage = {
      ...usage,
      id: uuidv4(),
      spoolId,
      usageDate: new Date()
    };

    // Update spool weights
    spool.weight.current -= usage.amountUsed;
    spool.weight.used += usage.amountUsed;

    // Update length if available
    if (spool.length.current && usage.lengthUsed) {
      spool.length.current -= usage.lengthUsed;
      spool.length.used! += usage.lengthUsed;
    }

    // Add to usage history
    spool.usageHistory.push(materialUsage);
    spool.updatedAt = new Date();

    // Update status if necessary
    const usagePercentage = (spool.weight.used / spool.weight.original) * 100;
    if (usagePercentage > 80 && spool.status === 'available') {
      spool.status = 'low-stock';
    } else if (usagePercentage > 90) {
      spool.status = 'empty';
    }

    this.usageHistory.set(materialUsage.id, materialUsage);
    this.emit('materialUsed', { spool, usage: materialUsage });

    return materialUsage;
  }

  async addSupplier(supplierData: Omit<Supplier, 'id' | 'totalOrders' | 'totalSpent' | 'createdAt' | 'updatedAt'>): Promise<Supplier> {
    const supplier: Supplier = {
      ...supplierData,
      id: uuidv4(),
      totalOrders: 0,
      totalSpent: 0,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.suppliers.set(supplier.id, supplier);
    this.emit('supplierAdded', supplier);
    
    return supplier;
  }

  async createOrder(orderData: Omit<InventoryOrder, 'id' | 'status' | 'createdAt' | 'updatedAt'>): Promise<InventoryOrder> {
    const order: InventoryOrder = {
      ...orderData,
      id: uuidv4(),
      status: 'draft',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.orders.set(order.id, order);
    this.emit('orderCreated', order);
    
    return order;
  }

  async updateOrderStatus(orderId: string, status: InventoryOrder['status'], metadata?: Partial<InventoryOrder>): Promise<boolean> {
    const order = this.orders.get(orderId);
    if (!order) return false;

    order.status = status;
    order.updatedAt = new Date();

    if (metadata) {
      Object.assign(order, metadata);
    }

    if (status === 'delivered') {
      order.actualDelivery = new Date();
      
      // Update supplier performance
      const supplier = this.suppliers.get(order.supplierId);
      if (supplier) {
        supplier.totalOrders++;
        supplier.totalSpent += order.totalCost;
        supplier.lastOrderDate = order.actualDelivery;
        
        // Calculate on-time delivery
        if (order.expectedDelivery && order.actualDelivery <= order.expectedDelivery) {
          // Update performance metrics (simplified)
          supplier.performance.onTimeDelivery = Math.min(100, supplier.performance.onTimeDelivery + 0.1);
        }
      }
    }

    this.emit('orderStatusUpdated', order);
    return true;
  }

  async acknowledgeAlert(alertId: string, userId: string): Promise<boolean> {
    const alert = this.alerts.get(alertId);
    if (!alert) return false;

    alert.acknowledged = true;
    alert.acknowledgedBy = userId;
    alert.acknowledgedAt = new Date();

    this.emit('alertAcknowledged', alert);
    return true;
  }

  async resolveAlert(alertId: string, userId: string): Promise<boolean> {
    const alert = this.alerts.get(alertId);
    if (!alert) return false;

    alert.resolved = true;
    alert.resolvedBy = userId;
    alert.resolvedAt = new Date();

    this.emit('alertResolved', alert);
    return true;
  }

  async generateInventoryReport(): Promise<InventoryReport> {
    const spools = Array.from(this.spools.values());
    const materialTypes = Array.from(this.materialTypes.values());
    const suppliers = Array.from(this.suppliers.values());
    const usage = Array.from(this.usageHistory.values());

    const totalMaterials = spools.length;
    const totalValue = spools.reduce((sum, spool) => sum + (spool.weight.current * spool.cost.perGram), 0);

    const lowStockItems = spools.filter(spool => spool.status === 'low-stock');
    const expiredItems = spools.filter(spool => spool.status === 'expired');

    // Calculate utilization rate
    const totalOriginalWeight = spools.reduce((sum, spool) => sum + spool.weight.original, 0);
    const totalUsedWeight = spools.reduce((sum, spool) => sum + spool.weight.used, 0);
    const utilizationRate = totalOriginalWeight > 0 ? (totalUsedWeight / totalOriginalWeight) * 100 : 0;

    // Calculate turnover rate (usage in last 30 days vs average inventory)
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const recentUsage = usage.filter(u => u.usageDate >= thirtyDaysAgo);
    const recentUsageWeight = recentUsage.reduce((sum, u) => sum + u.amountUsed, 0);
    const averageInventory = spools.reduce((sum, spool) => sum + (spool.weight.original + spool.weight.current) / 2, 0);
    const turnoverRate = averageInventory > 0 ? (recentUsageWeight / averageInventory) * 12 : 0; // Annualized

    // Top materials by usage
    const materialUsage = new Map<string, number>();
    usage.forEach(u => {
      const spool = this.spools.get(u.spoolId);
      if (spool) {
        const current = materialUsage.get(spool.materialTypeId) || 0;
        materialUsage.set(spool.materialTypeId, current + u.amountUsed);
      }
    });

    const topMaterials = Array.from(materialUsage.entries())
      .map(([materialId, usageAmount]) => ({
        material: this.materialTypes.get(materialId)!,
        usage: usageAmount
      }))
      .sort((a, b) => b.usage - a.usage)
      .slice(0, 5);

    // Cost analysis
    const totalSpent = spools.reduce((sum, spool) => sum + spool.cost.purchase, 0);
    const averageCostPerGram = totalOriginalWeight > 0 ? totalSpent / totalOriginalWeight : 0;
    const wastePercentage = 5; // Estimated waste

    // Quality metrics
    const qualityRatings = usage.map(u => {
      switch (u.printQuality) {
        case 'excellent': return 5;
        case 'good': return 4;
        case 'fair': return 3;
        case 'poor': return 2;
        default: return 3;
      }
    });
    const averageQuality = qualityRatings.length > 0 
      ? qualityRatings.reduce((sum, rating) => sum + rating, 0) / qualityRatings.length 
      : 0;
    const issueRate = usage.filter(u => u.issues && u.issues.length > 0).length / Math.max(usage.length, 1) * 100;

    const supplierPerformance = suppliers.map(supplier => ({
      supplier,
      score: (supplier.performance.rating + supplier.performance.qualityScore + 
             supplier.performance.priceCompetitiveness + supplier.performance.customerService) / 4
    })).sort((a, b) => b.score - a.score);

    // Forecast data (simplified prediction)
    const forecastData = materialTypes.slice(0, 5).map(material => {
      const currentInventory = spools
        .filter(spool => spool.materialTypeId === material.id && spool.status === 'available')
        .reduce((sum, spool) => sum + spool.weight.current, 0);
      
      const monthlyUsage = recentUsageWeight / materialTypes.length; // Simplified
      const predictedConsumption = monthlyUsage * 3; // 3 months prediction
      const recommendedOrder = Math.max(0, predictedConsumption - currentInventory + 1000); // 1kg buffer

      return {
        material,
        predictedConsumption,
        recommendedOrder
      };
    });

    return {
      totalMaterials,
      totalValue: Math.round(totalValue * 100) / 100,
      lowStockItems,
      expiredItems,
      utilizationRate: Math.round(utilizationRate * 100) / 100,
      turnoverRate: Math.round(turnoverRate * 100) / 100,
      topMaterials,
      costAnalysis: {
        totalSpent: Math.round(totalSpent * 100) / 100,
        averageCostPerGram: Math.round(averageCostPerGram * 100) / 100,
        wastePercentage
      },
      qualityMetrics: {
        averageQuality: Math.round(averageQuality * 100) / 100,
        issueRate: Math.round(issueRate * 100) / 100,
        supplierPerformance: supplierPerformance.slice(0, 5)
      },
      forecastData
    };
  }

  // Getter methods
  getMaterialType(id: string): MaterialType | undefined {
    return this.materialTypes.get(id);
  }

  getAllMaterialTypes(): MaterialType[] {
    return Array.from(this.materialTypes.values());
  }

  getSpool(id: string): MaterialSpool | undefined {
    return this.spools.get(id);
  }

  getAllSpools(): MaterialSpool[] {
    return Array.from(this.spools.values());
  }

  getAvailableSpools(): MaterialSpool[] {
    return Array.from(this.spools.values()).filter(spool => spool.status === 'available');
  }

  getSpoolsByMaterial(materialTypeId: string): MaterialSpool[] {
    return Array.from(this.spools.values()).filter(spool => spool.materialTypeId === materialTypeId);
  }

  getSupplier(id: string): Supplier | undefined {
    return this.suppliers.get(id);
  }

  getAllSuppliers(): Supplier[] {
    return Array.from(this.suppliers.values());
  }

  getOrder(id: string): InventoryOrder | undefined {
    return this.orders.get(id);
  }

  getAllOrders(): InventoryOrder[] {
    return Array.from(this.orders.values());
  }

  getActiveAlerts(): MaterialAlert[] {
    return Array.from(this.alerts.values()).filter(alert => !alert.resolved);
  }

  getUsageHistory(): MaterialUsage[] {
    return Array.from(this.usageHistory.values());
  }

  destroy(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = undefined;
    }
    
    this.removeAllListeners();
  }
}

export const materialInventory = new MaterialInventoryManager();