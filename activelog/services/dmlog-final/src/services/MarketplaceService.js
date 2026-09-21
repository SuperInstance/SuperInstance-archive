import axios from 'axios';
import fs from 'fs/promises';
import path from 'path';
import archiver from 'archiver';
import { v4 as uuidv4 } from 'uuid';
import Stripe from 'stripe';

class MarketplaceService {
  constructor() {
    this.stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
    this.printers = new Map();
    this.materials = new Map();
    this.orders = new Map();
    this.vendors = new Map();
    
    this.initialize();
  }

  async initialize() {
    // Load supported 3D printers and materials
    await this.loadPrinters();
    await this.loadMaterials();
    await this.loadVendors();
  }

  async loadPrinters() {
    const printers = [
      {
        id: 'ender3-pro',
        name: 'Creality Ender 3 Pro',
        buildVolume: { x: 220, y: 220, z: 250 },
        layerHeight: { min: 0.1, max: 0.3 },
        nozzleDiameter: 0.4,
        materials: ['PLA', 'ABS', 'PETG'],
        cost: 0.10 // per gram
      },
      {
        id: 'prusa-i3-mk3s',
        name: 'Prusa i3 MK3S+',
        buildVolume: { x: 250, y: 210, z: 210 },
        layerHeight: { min: 0.05, max: 0.35 },
        nozzleDiameter: 0.4,
        materials: ['PLA', 'ABS', 'PETG', 'TPU', 'WOOD', 'METAL'],
        cost: 0.12
      },
      {
        id: 'formlabs-form3',
        name: 'Formlabs Form 3',
        buildVolume: { x: 145, y: 145, z: 185 },
        layerHeight: { min: 0.025, max: 0.3 },
        technology: 'SLA',
        materials: ['Standard Resin', 'Tough Resin', 'Flexible Resin', 'Castable Resin'],
        cost: 0.25
      },
      {
        id: 'ultimaker-s5',
        name: 'Ultimaker S5',
        buildVolume: { x: 330, y: 240, z: 300 },
        layerHeight: { min: 0.06, max: 0.6 },
        dualExtrusion: true,
        materials: ['PLA', 'ABS', 'PETG', 'TPU', 'PVA', 'HIPS', 'PC'],
        cost: 0.15
      }
    ];
    
    printers.forEach(printer => {
      this.printers.set(printer.id, printer);
    });
  }

  async loadMaterials() {
    const materials = [
      {
        id: 'pla-basic',
        name: 'PLA Basic',
        type: 'PLA',
        colors: ['White', 'Black', 'Red', 'Blue', 'Green', 'Yellow', 'Orange', 'Purple'],
        properties: {
          strength: 'Medium',
          flexibility: 'Low',
          printability: 'Excellent',
          postProcessing: 'Easy'
        },
        cost: 25.00, // per kg
        minOrderQuantity: 0.1 // kg
      },
      {
        id: 'abs-premium',
        name: 'ABS Premium',
        type: 'ABS',
        colors: ['White', 'Black', 'Red', 'Blue', 'Green'],
        properties: {
          strength: 'High',
          flexibility: 'Medium',
          printability: 'Good',
          postProcessing: 'Moderate'
        },
        cost: 35.00,
        minOrderQuantity: 0.1
      },
      {
        id: 'petg-clear',
        name: 'PETG Crystal Clear',
        type: 'PETG',
        colors: ['Clear', 'White', 'Black'],
        properties: {
          strength: 'High',
          flexibility: 'Medium',
          printability: 'Good',
          postProcessing: 'Easy'
        },
        cost: 40.00,
        minOrderQuantity: 0.1
      },
      {
        id: 'wood-fill',
        name: 'Wood Fill PLA',
        type: 'WOOD',
        colors: ['Natural Wood', 'Cherry', 'Ebony'],
        properties: {
          strength: 'Medium',
          flexibility: 'Low',
          printability: 'Good',
          postProcessing: 'Excellent (Sandable, Stainable)'
        },
        cost: 50.00,
        minOrderQuantity: 0.1
      },
      {
        id: 'metal-fill',
        name: 'Metal Fill PLA',
        type: 'METAL',
        colors: ['Bronze', 'Copper', 'Steel', 'Aluminum'],
        properties: {
          strength: 'High',
          flexibility: 'Low',
          printability: 'Moderate',
          postProcessing: 'Excellent (Polishable)'
        },
        cost: 75.00,
        minOrderQuantity: 0.1
      },
      {
        id: 'standard-resin',
        name: 'Standard Photopolymer Resin',
        type: 'RESIN',
        colors: ['Clear', 'White', 'Black', 'Gray'],
        technology: 'SLA',
        properties: {
          strength: 'Medium',
          flexibility: 'Low',
          detail: 'Excellent',
          postProcessing: 'Required (Washing, Curing)'
        },
        cost: 120.00, // per liter
        minOrderQuantity: 0.1
      }
    ];
    
    materials.forEach(material => {
      this.materials.set(material.id, material);
    });
  }

  async loadVendors() {
    const vendors = [
      {
        id: 'heroforge',
        name: 'Hero Forge',
        type: 'miniatures',
        apiUrl: 'https://api.heroforge.com',
        specialties: ['Custom Character Miniatures', 'Detailed Sculpting'],
        materials: ['Premium Plastic', 'Steel', 'Bronze'],
        pricing: {
          base: 30.00,
          premium: 50.00,
          metal: 100.00
        }
      },
      {
        id: 'printablescenery',
        name: 'Printable Scenery',
        type: 'terrain',
        specialties: ['Modular Terrain', 'Dungeon Tiles', 'Buildings'],
        materials: ['PLA', 'ABS', 'PETG'],
        pricing: {
          perFile: 5.00,
          bundle: 25.00,
          subscription: 15.00 // monthly
        }
      },
      {
        id: 'fatdragongames',
        name: 'Fat Dragon Games',
        type: 'terrain',
        specialties: ['DragonLock System', 'Modular Terrain'],
        materials: ['PLA', 'ABS'],
        pricing: {
          perFile: 3.00,
          bundle: 20.00
        }
      },
      {
        id: 'desktopminis',
        name: 'Desktop Miniatures',
        type: 'miniatures',
        specialties: ['Character Miniatures', 'Monster Sets'],
        materials: ['PLA', 'Resin'],
        pricing: {
          individual: 2.00,
          set: 15.00
        }
      }
    ];
    
    vendors.forEach(vendor => {
      this.vendors.set(vendor.id, vendor);
    });
  }

  async analyzeModel(modelData) {
    const { sceneId, modelType, dimensions } = modelData;
    
    // Calculate volume and material requirements
    const volume = this.calculateVolume(dimensions);
    const weight = this.calculateWeight(volume, modelData.material || 'PLA');
    
    // Check printability
    const printabilityChecks = this.checkPrintability(dimensions, modelData);
    
    // Estimate print time
    const printTime = this.estimatePrintTime(volume, modelData.layerHeight || 0.2);
    
    // Calculate costs
    const materialCost = this.calculateMaterialCost(weight, modelData.material || 'PLA');
    const printingCost = this.calculatePrintingCost(printTime, modelData.printer || 'ender3-pro');
    
    return {
      volume: Math.round(volume * 100) / 100, // cm³
      weight: Math.round(weight * 10) / 10, // grams
      printTime: Math.round(printTime), // minutes
      materialCost: Math.round(materialCost * 100) / 100,
      printingCost: Math.round(printingCost * 100) / 100,
      totalCost: Math.round((materialCost + printingCost) * 100) / 100,
      printability: printabilityChecks,
      recommendations: this.generateRecommendations(printabilityChecks, dimensions)
    };
  }

  calculateVolume(dimensions) {
    // Simplified volume calculation
    return dimensions.width * dimensions.height * dimensions.depth;
  }

  calculateWeight(volume, materialType) {
    const densities = {
      'PLA': 1.25, // g/cm³
      'ABS': 1.05,
      'PETG': 1.27,
      'TPU': 1.20,
      'WOOD': 1.15,
      'METAL': 1.30,
      'RESIN': 1.10
    };
    
    const density = densities[materialType] || 1.25;
    const infillFactor = 0.20; // Assuming 20% infill
    
    return volume * density * infillFactor;
  }

  checkPrintability(dimensions, modelData) {
    const checks = {
      overhangs: this.checkOverhangs(modelData),
      supports: this.checkSupports(modelData),
      bridging: this.checkBridging(modelData),
      layerAdhesion: this.checkLayerAdhesion(dimensions),
      warping: this.checkWarping(modelData.material, dimensions),
      resolution: this.checkResolution(dimensions, modelData.layerHeight)
    };
    
    const score = Object.values(checks).reduce((sum, check) => sum + check.score, 0) / Object.keys(checks).length;
    
    return {
      ...checks,
      overallScore: Math.round(score * 100) / 100,
      difficulty: score > 0.8 ? 'Easy' : score > 0.6 ? 'Medium' : 'Hard'
    };
  }

  checkOverhangs(modelData) {
    // Simplified overhang detection
    // In a real implementation, this would analyze the 3D geometry
    return {
      score: 0.8,
      issues: [],
      recommendations: ['Consider adding supports for angles > 45°']
    };
  }

  checkSupports(modelData) {
    return {
      score: 0.9,
      issues: [],
      recommendations: ['Tree supports recommended for complex geometries']
    };
  }

  checkBridging(modelData) {
    return {
      score: 0.7,
      issues: ['Long bridges detected'],
      recommendations: ['Enable cooling fan for better bridge quality']
    };
  }

  checkLayerAdhesion(dimensions) {
    const aspectRatio = Math.max(dimensions.width, dimensions.depth) / dimensions.height;
    const score = aspectRatio > 10 ? 0.5 : aspectRatio > 5 ? 0.7 : 0.9;
    
    return {
      score,
      issues: aspectRatio > 10 ? ['High aspect ratio may cause layer adhesion issues'] : [],
      recommendations: aspectRatio > 10 ? ['Consider printing orientation adjustment'] : []
    };
  }

  checkWarping(material, dimensions) {
    const warpingRisk = {
      'PLA': 0.1,
      'ABS': 0.7,
      'PETG': 0.3,
      'TPU': 0.2
    };
    
    const baseRisk = warpingRisk[material] || 0.3;
    const sizeMultiplier = Math.max(dimensions.width, dimensions.depth) / 100;
    const finalRisk = Math.min(baseRisk * sizeMultiplier, 1);
    
    return {
      score: 1 - finalRisk,
      issues: finalRisk > 0.5 ? ['High warping risk'] : [],
      recommendations: finalRisk > 0.5 ? ['Use heated bed and enclosure'] : []
    };
  }

  checkResolution(dimensions, layerHeight) {
    const minFeatureSize = Math.min(dimensions.width, dimensions.depth, dimensions.height);
    const recommendedLayers = minFeatureSize / (layerHeight || 0.2);
    
    return {
      score: recommendedLayers > 5 ? 1 : recommendedLayers > 2 ? 0.7 : 0.4,
      issues: recommendedLayers < 2 ? ['Features may be too small for selected layer height'] : [],
      recommendations: recommendedLayers < 2 ? ['Reduce layer height or increase feature size'] : []
    };
  }

  estimatePrintTime(volume, layerHeight) {
    // Simplified print time estimation (minutes)
    const baseTime = volume * 2; // 2 minutes per cm³
    const layerMultiplier = 0.2 / layerHeight; // Adjusted for layer height
    
    return baseTime * layerMultiplier;
  }

  calculateMaterialCost(weight, materialType) {
    const material = Array.from(this.materials.values()).find(m => m.type === materialType);
    if (!material) return 0;
    
    return (weight / 1000) * material.cost; // Convert grams to kg
  }

  calculatePrintingCost(printTime, printerType) {
    const printer = this.printers.get(printerType);
    if (!printer) return 0;
    
    const hourlyRate = printer.cost * 60; // Convert per gram to hourly
    return (printTime / 60) * hourlyRate;
  }

  generateRecommendations(printability, dimensions) {
    const recommendations = [];
    
    if (printability.overallScore < 0.7) {
      recommendations.push({
        type: 'difficulty',
        message: 'This model may be challenging to print',
        solutions: ['Consider splitting into smaller parts', 'Use higher quality printer']
      });
    }
    
    if (dimensions.height > 100) {
      recommendations.push({
        type: 'size',
        message: 'Tall models are more prone to printing failures',
        solutions: ['Add more supports', 'Reduce print speed', 'Check bed leveling']
      });
    }
    
    if (Math.max(dimensions.width, dimensions.depth) > 200) {
      recommendations.push({
        type: 'size',
        message: 'Large footprint may cause warping',
        solutions: ['Use heated bed', 'Add brim or raft', 'Print with ABS or PETG']
      });
    }
    
    return recommendations;
  }

  async findCompatiblePrinters(modelData) {
    const { dimensions } = modelData;
    const compatiblePrinters = [];
    
    for (const [id, printer] of this.printers) {
      const fits = dimensions.width <= printer.buildVolume.x &&
                   dimensions.depth <= printer.buildVolume.y &&
                   dimensions.height <= printer.buildVolume.z;
      
      if (fits) {
        compatiblePrinters.push({
          ...printer,
          id,
          costEstimate: this.calculatePrintingCost(
            this.estimatePrintTime(this.calculateVolume(dimensions), 0.2),
            id
          )
        });
      }
    }
    
    return compatiblePrinters.sort((a, b) => a.costEstimate - b.costEstimate);
  }

  async searchMarketplace(query) {
    const { type, category, priceRange, materials } = query;
    
    // In a real implementation, this would query external marketplaces
    const mockResults = [
      {
        id: 'dwarf-fighter-001',
        title: 'Dwarf Fighter Miniature',
        description: 'Detailed dwarf fighter with axe and shield',
        category: 'miniatures',
        vendor: 'heroforge',
        price: 25.00,
        materials: ['Premium Plastic', 'Steel'],
        rating: 4.8,
        downloads: 1250,
        images: ['/api/images/dwarf-fighter-001.jpg'],
        tags: ['dwarf', 'fighter', 'warrior', 'axe', 'shield']
      },
      {
        id: 'dungeon-tile-set-001',
        title: 'Medieval Dungeon Tile Set',
        description: 'Modular dungeon tiles compatible with 28mm miniatures',
        category: 'terrain',
        vendor: 'printablescenery',
        price: 15.00,
        materials: ['PLA', 'ABS', 'PETG'],
        rating: 4.6,
        downloads: 890,
        images: ['/api/images/dungeon-tiles-001.jpg'],
        tags: ['dungeon', 'tiles', 'modular', 'medieval', 'stone']
      },
      {
        id: 'dragon-miniature-001',
        title: 'Ancient Red Dragon',
        description: 'Massive red dragon miniature with detailed scales',
        category: 'miniatures',
        vendor: 'desktopminis',
        price: 35.00,
        materials: ['PLA', 'Resin'],
        rating: 4.9,
        downloads: 2100,
        images: ['/api/images/red-dragon-001.jpg'],
        tags: ['dragon', 'red', 'ancient', 'boss', 'scales']
      }
    ];
    
    // Filter results based on query
    let filteredResults = mockResults;
    
    if (type) {
      filteredResults = filteredResults.filter(item => 
        item.category === type || item.tags.includes(type)
      );
    }
    
    if (category) {
      filteredResults = filteredResults.filter(item => item.category === category);
    }
    
    if (priceRange) {
      filteredResults = filteredResults.filter(item => 
        item.price >= priceRange.min && item.price <= priceRange.max
      );
    }
    
    return {
      results: filteredResults,
      total: filteredResults.length,
      facets: {
        categories: [...new Set(mockResults.map(item => item.category))],
        vendors: [...new Set(mockResults.map(item => item.vendor))],
        priceRanges: [
          { label: '$0-$10', min: 0, max: 10 },
          { label: '$10-$25', min: 10, max: 25 },
          { label: '$25-$50', min: 25, max: 50 },
          { label: '$50+', min: 50, max: 1000 }
        ]
      }
    };
  }

  async createOrder(orderData) {
    const { userId, items, shippingAddress, printOptions } = orderData;
    const orderId = uuidv4();
    
    let totalCost = 0;
    const processedItems = [];
    
    for (const item of items) {
      const analysis = await this.analyzeModel(item.modelData);
      const itemCost = analysis.totalCost * item.quantity;
      totalCost += itemCost;
      
      processedItems.push({
        ...item,
        analysis,
        cost: itemCost
      });
    }
    
    // Add shipping cost
    const shippingCost = this.calculateShipping(shippingAddress, totalCost);
    totalCost += shippingCost;
    
    const order = {
      id: orderId,
      userId,
      items: processedItems,
      shippingAddress,
      printOptions,
      costs: {
        subtotal: totalCost - shippingCost,
        shipping: shippingCost,
        total: totalCost
      },
      status: 'pending',
      createdAt: new Date(),
      estimatedDelivery: this.calculateDeliveryDate(shippingAddress)
    };
    
    this.orders.set(orderId, order);
    
    return order;
  }

  calculateShipping(address, orderValue) {
    // Simplified shipping calculation
    const baseShipping = 15.00;
    const freeShippingThreshold = 100.00;
    
    if (orderValue >= freeShippingThreshold) {
      return 0;
    }
    
    // International shipping
    if (address.country !== 'US') {
      return baseShipping * 2;
    }
    
    return baseShipping;
  }

  calculateDeliveryDate(address) {
    const now = new Date();
    const processingDays = 3; // 3 days processing
    const shippingDays = address.country === 'US' ? 5 : 14;
    
    const deliveryDate = new Date(now);
    deliveryDate.setDate(now.getDate() + processingDays + shippingDays);
    
    return deliveryDate;
  }

  async processPayment(orderId, paymentMethod) {
    const order = this.orders.get(orderId);
    if (!order) throw new Error('Order not found');
    
    try {
      // Create Stripe payment intent
      const paymentIntent = await this.stripe.paymentIntents.create({
        amount: Math.round(order.costs.total * 100), // Convert to cents
        currency: 'usd',
        payment_method: paymentMethod,
        confirmation_method: 'manual',
        confirm: true,
        metadata: {
          orderId: orderId,
          userId: order.userId
        }
      });
      
      if (paymentIntent.status === 'succeeded') {
        order.status = 'paid';
        order.paymentId = paymentIntent.id;
        order.paidAt = new Date();
        
        // Queue for printing
        await this.queueForPrinting(orderId);
        
        return { success: true, paymentIntent };
      } else {
        return { success: false, error: 'Payment failed' };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async queueForPrinting(orderId) {
    const order = this.orders.get(orderId);
    if (!order) throw new Error('Order not found');
    
    // In a real implementation, this would:
    // 1. Generate G-code files
    // 2. Queue items on appropriate printers
    // 3. Send notifications to print operators
    // 4. Update order status
    
    order.status = 'printing';
    order.queuedAt = new Date();
    
    // Mock print queue
    setTimeout(() => {
      order.status = 'completed';
      order.completedAt = new Date();
    }, 30000); // 30 seconds for demo
    
    return true;
  }

  async generateSTL(modelData) {
    // In a real implementation, this would:
    // 1. Take the 3D model data
    // 2. Generate STL file format
    // 3. Optimize for 3D printing
    // 4. Return file buffer
    
    const mockSTL = `solid model
      facet normal 0 0 1
        outer loop
          vertex 0 0 0
          vertex 1 0 0
          vertex 1 1 0
        endloop
      endfacet
      facet normal 0 0 1
        outer loop
          vertex 0 0 0
          vertex 1 1 0
          vertex 0 1 0
        endloop
      endfacet
    endsolid model`;
    
    return {
      filename: `model-${Date.now()}.stl`,
      data: Buffer.from(mockSTL),
      size: mockSTL.length
    };
  }

  async generateGCode(stlData, printSettings) {
    // In a real implementation, this would use a slicing engine
    // like Cura Engine or PrusaSlicer to generate G-code
    
    const mockGCode = `; Generated by DMLog Marketplace
G28 ; Home all axes
G1 Z15.0 F6000 ; Move the platform down 15mm
G92 E0 ; Reset extruder
G1 F200 E3 ; Extrude 3mm of filament
G92 E0 ; Reset extruder
G1 F6000
; Start printing
G1 X10 Y10 Z0.2 F3000
G1 E2 F300
; ... printing commands would follow
M104 S0 ; Turn off temperature
G28 X0 ; Home X axis
M84 ; Disable motors`;
    
    return {
      filename: `model-${Date.now()}.gcode`,
      data: Buffer.from(mockGCode),
      size: mockGCode.length,
      printTime: printSettings.estimatedTime || 120, // minutes
      filamentUsage: printSettings.filamentUsage || 50 // grams
    };
  }

  async getOrderStatus(orderId) {
    const order = this.orders.get(orderId);
    if (!order) throw new Error('Order not found');
    
    return {
      id: order.id,
      status: order.status,
      createdAt: order.createdAt,
      estimatedDelivery: order.estimatedDelivery,
      items: order.items.map(item => ({
        name: item.name,
        quantity: item.quantity,
        status: order.status
      }))
    };
  }

  async getPopularModels() {
    // Return trending/popular models from marketplace
    return [
      {
        id: 'popular-001',
        title: 'Modular Dungeon Starter Set',
        category: 'terrain',
        price: 20.00,
        rating: 4.8,
        downloads: 5400,
        trending: true
      },
      {
        id: 'popular-002',
        title: 'Character Miniature Bundle',
        category: 'miniatures',
        price: 35.00,
        rating: 4.7,
        downloads: 3200,
        trending: true
      }
    ];
  }
}

export default MarketplaceService;