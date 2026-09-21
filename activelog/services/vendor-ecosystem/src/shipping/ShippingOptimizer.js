import EventEmitter from 'events';
import axios from 'axios';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default class ShippingOptimizer extends EventEmitter {
    constructor(logger) {
        super();
        this.logger = logger;
        this.carriers = new Map();
        this.rateCache = new Map();
        this.routeOptimizer = new Map();
        this.consolidationRules = new Map();
        this.zoneMap = new Map();
        this.weatherService = null;
        this.trafficService = null;
        this.cacheTimeout = 30 * 60 * 1000; // 30 minutes
        this.carbonFootprintCalculator = new Map();
        this.dimensionalWeightFactor = 166; // Standard DIM factor for domestic shipping
        
        this.initializeCarriers();
        this.initializeZoneMapping();
        this.initializeConsolidationRules();
        this.initializeCarbonCalculator();
    }

    async initializeCarriers() {
        try {
            const carriersPath = path.join(__dirname, '../data/carriers.json');
            const carriersData = await fs.readFile(carriersPath, 'utf8');
            const carriers = JSON.parse(carriersData);
            
            for (const carrier of carriers) {
                this.carriers.set(carrier.id, carrier);
            }
            
            this.logger.info(`Loaded ${this.carriers.size} shipping carriers`);
        } catch (error) {
            this.logger.warn('Could not load carriers file, using defaults');
            this.loadDefaultCarriers();
        }
    }

    loadDefaultCarriers() {
        const defaultCarriers = [
            {
                id: 'fedex',
                name: 'FedEx',
                api_endpoint: 'https://apis.fedex.com/ship/v1/shipments',
                api_key_env: 'FEDEX_API_KEY',
                secret_env: 'FEDEX_SECRET',
                services: [
                    { code: 'FEDEX_GROUND', name: 'FedEx Ground', transit_time: '1-5 days', cost_multiplier: 1.0 },
                    { code: 'FEDEX_2_DAY', name: 'FedEx 2Day', transit_time: '2 days', cost_multiplier: 1.8 },
                    { code: 'FEDEX_OVERNIGHT', name: 'FedEx Standard Overnight', transit_time: '1 day', cost_multiplier: 3.2 },
                    { code: 'FIRST_OVERNIGHT', name: 'FedEx First Overnight', transit_time: '1 day', cost_multiplier: 4.1 }
                ],
                max_weight: 150,
                max_dimensions: { length: 108, width: 70, height: 70 },
                zones: [1, 2, 3, 4, 5, 6, 7, 8],
                signature_required: false,
                insurance_available: true,
                tracking: true,
                pickup_service: true
            },
            {
                id: 'ups',
                name: 'UPS',
                api_endpoint: 'https://wwwcie.ups.com/rest/Rate',
                api_key_env: 'UPS_API_KEY',
                username_env: 'UPS_USERNAME',
                password_env: 'UPS_PASSWORD',
                services: [
                    { code: 'UPS_GROUND', name: 'UPS Ground', transit_time: '1-5 days', cost_multiplier: 0.98 },
                    { code: 'UPS_2_DAY_AIR', name: 'UPS 2nd Day Air', transit_time: '2 days', cost_multiplier: 1.75 },
                    { code: 'UPS_NEXT_DAY_AIR', name: 'UPS Next Day Air', transit_time: '1 day', cost_multiplier: 3.1 },
                    { code: 'UPS_NEXT_DAY_AIR_SAVER', name: 'UPS Next Day Air Saver', transit_time: '1 day', cost_multiplier: 2.8 }
                ],
                max_weight: 150,
                max_dimensions: { length: 108, width: 70, height: 70 },
                zones: [1, 2, 3, 4, 5, 6, 7, 8],
                signature_required: false,
                insurance_available: true,
                tracking: true,
                pickup_service: true
            },
            {
                id: 'usps',
                name: 'USPS',
                api_endpoint: 'https://secure.shippingapis.com/ShippingAPI.dll',
                api_key_env: 'USPS_API_KEY',
                services: [
                    { code: 'PRIORITY_MAIL', name: 'USPS Priority Mail', transit_time: '1-3 days', cost_multiplier: 0.85 },
                    { code: 'PRIORITY_EXPRESS', name: 'USPS Priority Express', transit_time: '1-2 days', cost_multiplier: 2.1 },
                    { code: 'GROUND_ADVANTAGE', name: 'USPS Ground Advantage', transit_time: '2-5 days', cost_multiplier: 0.75 },
                    { code: 'FIRST_CLASS', name: 'USPS First Class', transit_time: '1-3 days', cost_multiplier: 0.60 }
                ],
                max_weight: 70,
                max_dimensions: { length: 108, width: 70, height: 70 },
                zones: [1, 2, 3, 4, 5, 6, 7, 8, 9],
                signature_required: false,
                insurance_available: true,
                tracking: true,
                pickup_service: false
            },
            {
                id: 'dhl',
                name: 'DHL Express',
                api_endpoint: 'https://express.api.dhl.com/mydhlapi/shipments',
                api_key_env: 'DHL_API_KEY',
                secret_env: 'DHL_SECRET',
                services: [
                    { code: 'DHL_EXPRESS_WORLDWIDE', name: 'DHL Express Worldwide', transit_time: '1-3 days', cost_multiplier: 4.5 },
                    { code: 'DHL_EXPRESS_12', name: 'DHL Express 12:00', transit_time: '1-2 days', cost_multiplier: 5.2 },
                    { code: 'DHL_EXPRESS_10', name: 'DHL Express 10:30', transit_time: '1 day', cost_multiplier: 6.1 }
                ],
                max_weight: 154,
                max_dimensions: { length: 120, width: 80, height: 80 },
                international: true,
                customs_forms: true,
                signature_required: true,
                insurance_available: true,
                tracking: true,
                pickup_service: true
            }
        ];

        defaultCarriers.forEach(carrier => {
            this.carriers.set(carrier.id, carrier);
        });
    }

    initializeZoneMapping() {
        // Simplified zone mapping based on ZIP code ranges
        this.zoneMap.set('zone_1', { zip_ranges: ['00000-19999'], base_cost: 8.50 });
        this.zoneMap.set('zone_2', { zip_ranges: ['20000-39999'], base_cost: 9.25 });
        this.zoneMap.set('zone_3', { zip_ranges: ['40000-59999'], base_cost: 10.75 });
        this.zoneMap.set('zone_4', { zip_ranges: ['60000-79999'], base_cost: 12.50 });
        this.zoneMap.set('zone_5', { zip_ranges: ['80000-99999'], base_cost: 15.25 });
    }

    initializeConsolidationRules() {
        this.consolidationRules.set('same_destination', {
            max_weight: 50,
            max_packages: 5,
            cost_reduction: 0.15,
            description: 'Consolidate packages to same destination'
        });

        this.consolidationRules.set('regional_hub', {
            max_weight: 100,
            max_packages: 10,
            cost_reduction: 0.25,
            description: 'Route through regional consolidation hub'
        });

        this.consolidationRules.set('bulk_shipment', {
            min_weight: 150,
            cost_reduction: 0.30,
            description: 'Bulk shipment discounts for heavy orders'
        });
    }

    initializeCarbonCalculator() {
        // Carbon footprint per mile by carrier type (kg CO2)
        this.carbonFootprintCalculator.set('ground', 0.15);
        this.carbonFootprintCalculator.set('air', 0.85);
        this.carbonFootprintCalculator.set('express', 1.25);
        this.carbonFootprintCalculator.set('overnight', 1.55);
    }

    async optimizeShipping(shipment, options = {}) {
        try {
            const optimization = {
                original_shipment: shipment,
                options,
                optimized_routes: [],
                consolidation_opportunities: [],
                cost_analysis: {},
                environmental_impact: {},
                recommendations: [],
                timestamp: new Date()
            };

            // Calculate package dimensions and weights
            const packages = this.calculatePackaging(shipment.items);
            
            // Get shipping rates from all carriers
            const rates = await this.getAllCarrierRates(packages, shipment.origin, shipment.destination, options);
            
            // Apply consolidation logic
            const consolidatedOptions = await this.findConsolidationOpportunities(packages, rates, shipment);
            
            // Optimize routes
            const routeOptimizations = await this.optimizeRoutes(shipment, rates, options);
            
            // Calculate environmental impact
            const environmentalImpact = this.calculateEnvironmentalImpact(rates, shipment);
            
            // Generate recommendations
            const recommendations = this.generateShippingRecommendations(rates, consolidatedOptions, routeOptimizations, options);

            optimization.optimized_routes = routeOptimizations;
            optimization.consolidation_opportunities = consolidatedOptions;
            optimization.cost_analysis = this.performCostAnalysis(rates);
            optimization.environmental_impact = environmentalImpact;
            optimization.recommendations = recommendations;

            this.emit('shipping_optimized', {
                shipment_id: shipment.id,
                optimization
            });

            this.logger.info(`Shipping optimization completed for shipment ${shipment.id}: ${recommendations.length} recommendations`);

            return optimization;

        } catch (error) {
            this.logger.error('Shipping optimization failed:', error);
            throw error;
        }
    }

    calculatePackaging(items) {
        const packages = [];
        let currentPackage = {
            items: [],
            weight: 0,
            dimensions: { length: 0, width: 0, height: 0 },
            volume: 0,
            fragile: false,
            hazardous: false
        };

        for (const item of items) {
            const itemWeight = item.weight || 1;
            const itemVolume = (item.dimensions?.length || 6) * (item.dimensions?.width || 4) * (item.dimensions?.height || 2);
            
            // Check if item fits in current package
            if (currentPackage.weight + itemWeight <= 50 && currentPackage.volume + itemVolume <= 12000) {
                currentPackage.items.push(item);
                currentPackage.weight += itemWeight;
                currentPackage.volume += itemVolume;
                currentPackage.fragile = currentPackage.fragile || item.fragile;
                currentPackage.hazardous = currentPackage.hazardous || item.hazardous;
                
                // Update dimensions (simplified - assume stacking)
                currentPackage.dimensions.length = Math.max(currentPackage.dimensions.length, item.dimensions?.length || 6);
                currentPackage.dimensions.width = Math.max(currentPackage.dimensions.width, item.dimensions?.width || 4);
                currentPackage.dimensions.height += item.dimensions?.height || 2;
            } else {
                // Start new package
                if (currentPackage.items.length > 0) {
                    packages.push(this.finalizePackage(currentPackage));
                }
                
                currentPackage = {
                    items: [item],
                    weight: itemWeight,
                    dimensions: {
                        length: item.dimensions?.length || 6,
                        width: item.dimensions?.width || 4,
                        height: item.dimensions?.height || 2
                    },
                    volume: itemVolume,
                    fragile: item.fragile || false,
                    hazardous: item.hazardous || false
                };
            }
        }

        // Add final package
        if (currentPackage.items.length > 0) {
            packages.push(this.finalizePackage(currentPackage));
        }

        return packages;
    }

    finalizePackage(packageData) {
        // Add padding and packaging material
        const paddingFactor = packageData.fragile ? 1.5 : 1.2;
        
        return {
            ...packageData,
            dimensions: {
                length: Math.ceil(packageData.dimensions.length * paddingFactor),
                width: Math.ceil(packageData.dimensions.width * paddingFactor),
                height: Math.ceil(packageData.dimensions.height * paddingFactor)
            },
            weight: packageData.weight + 0.5, // Add packaging weight
            dimensional_weight: this.calculateDimensionalWeight(packageData.dimensions, paddingFactor),
            package_type: this.determinePackageType(packageData)
        };
    }

    calculateDimensionalWeight(dimensions, paddingFactor = 1.2) {
        const adjustedDims = {
            length: dimensions.length * paddingFactor,
            width: dimensions.width * paddingFactor,
            height: dimensions.height * paddingFactor
        };
        
        return (adjustedDims.length * adjustedDims.width * adjustedDims.height) / this.dimensionalWeightFactor;
    }

    determinePackageType(packageData) {
        if (packageData.fragile) return 'fragile';
        if (packageData.hazardous) return 'hazardous';
        if (packageData.weight > 20) return 'heavy';
        if (packageData.volume > 8000) return 'oversized';
        return 'standard';
    }

    async getAllCarrierRates(packages, origin, destination, options) {
        const cacheKey = `${origin}-${destination}-${JSON.stringify(packages)}-${JSON.stringify(options)}`;
        
        // Check cache
        if (this.rateCache.has(cacheKey)) {
            const cached = this.rateCache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.rates;
            }
        }

        const ratePromises = [];
        
        for (const [carrierId, carrier] of this.carriers) {
            if (options.exclude_carriers && options.exclude_carriers.includes(carrierId)) {
                continue;
            }

            // Check if carrier supports international shipping if needed
            if (this.isInternationalShipment(origin, destination) && !carrier.international) {
                continue;
            }

            ratePromises.push(this.getCarrierRates(carrier, packages, origin, destination, options));
        }

        const results = await Promise.allSettled(ratePromises);
        const rates = results
            .filter(result => result.status === 'fulfilled' && result.value)
            .flatMap(result => result.value);

        // Cache results
        this.rateCache.set(cacheKey, {
            rates,
            timestamp: Date.now()
        });

        return rates;
    }

    async getCarrierRates(carrier, packages, origin, destination, options) {
        try {
            if (carrier.api_endpoint) {
                return await this.getApiRates(carrier, packages, origin, destination, options);
            } else {
                return this.calculateEstimatedRates(carrier, packages, origin, destination, options);
            }
        } catch (error) {
            this.logger.warn(`Failed to get rates from ${carrier.name}:`, error.message);
            return [];
        }
    }

    async getApiRates(carrier, packages, origin, destination, options) {
        // Mock API call - in real implementation, would call actual carrier APIs
        const rates = [];
        
        for (const service of carrier.services) {
            for (const packageData of packages) {
                const billableWeight = Math.max(packageData.weight, packageData.dimensional_weight);
                const zone = this.calculateShippingZone(origin, destination);
                const baseRate = this.zoneMap.get(zone)?.base_cost || 10;
                const rate = baseRate * service.cost_multiplier * (1 + (billableWeight - 1) * 0.5);
                
                rates.push({
                    carrier_id: carrier.id,
                    carrier_name: carrier.name,
                    service_code: service.code,
                    service_name: service.name,
                    cost: parseFloat(rate.toFixed(2)),
                    transit_time: service.transit_time,
                    delivery_date: this.calculateDeliveryDate(service.transit_time, options.ship_date),
                    package_id: packageData.id || `pkg_${packages.indexOf(packageData)}`,
                    weight: packageData.weight,
                    dimensional_weight: packageData.dimensional_weight,
                    billable_weight: billableWeight,
                    zone: zone,
                    tracking_available: carrier.tracking,
                    insurance_available: carrier.insurance_available,
                    signature_required: carrier.signature_required || packageData.fragile,
                    special_handling: packageData.hazardous ? ['hazmat'] : packageData.fragile ? ['fragile'] : []
                });
            }
        }
        
        return rates;
    }

    calculateEstimatedRates(carrier, packages, origin, destination, options) {
        const rates = [];
        
        for (const service of carrier.services) {
            for (const packageData of packages) {
                const billableWeight = Math.max(packageData.weight, packageData.dimensional_weight);
                const zone = this.calculateShippingZone(origin, destination);
                const baseRate = this.zoneMap.get(zone)?.base_cost || 10;
                let rate = baseRate * service.cost_multiplier * (1 + (billableWeight - 1) * 0.5);
                
                // Add surcharges
                if (packageData.fragile) rate *= 1.15;
                if (packageData.hazardous) rate *= 1.35;
                if (this.isInternationalShipment(origin, destination)) rate *= 2.5;
                if (options.signature_required) rate += 5.95;
                if (options.insurance_value) rate += options.insurance_value * 0.01;
                
                rates.push({
                    carrier_id: carrier.id,
                    carrier_name: carrier.name,
                    service_code: service.code,
                    service_name: service.name,
                    cost: parseFloat(rate.toFixed(2)),
                    transit_time: service.transit_time,
                    delivery_date: this.calculateDeliveryDate(service.transit_time, options.ship_date),
                    package_id: packageData.id || `pkg_${packages.indexOf(packageData)}`,
                    weight: packageData.weight,
                    dimensional_weight: packageData.dimensional_weight,
                    billable_weight: billableWeight,
                    zone: zone,
                    estimated: true,
                    tracking_available: carrier.tracking,
                    insurance_available: carrier.insurance_available,
                    signature_required: carrier.signature_required || packageData.fragile,
                    special_handling: packageData.hazardous ? ['hazmat'] : packageData.fragile ? ['fragile'] : []
                });
            }
        }
        
        return rates;
    }

    calculateShippingZone(origin, destination) {
        // Simplified zone calculation based on ZIP codes
        const originZip = parseInt(origin.zip_code || origin.postal_code || '10001');
        const destZip = parseInt(destination.zip_code || destination.postal_code || '10001');
        
        const distance = Math.abs(originZip - destZip);
        
        if (distance < 10000) return 'zone_1';
        if (distance < 20000) return 'zone_2';
        if (distance < 40000) return 'zone_3';
        if (distance < 60000) return 'zone_4';
        return 'zone_5';
    }

    calculateDeliveryDate(transitTime, shipDate = new Date()) {
        const days = this.parseTransitTimeToDays(transitTime);
        const deliveryDate = new Date(shipDate);
        deliveryDate.setDate(deliveryDate.getDate() + days);
        
        // Skip weekends for ground services
        while (deliveryDate.getDay() === 0 || deliveryDate.getDay() === 6) {
            deliveryDate.setDate(deliveryDate.getDate() + 1);
        }
        
        return deliveryDate;
    }

    parseTransitTimeToDays(transitTime) {
        if (!transitTime) return 5;
        
        const text = transitTime.toLowerCase();
        if (text.includes('same day')) return 0;
        if (text.includes('1 day') || text.includes('next day') || text.includes('overnight')) return 1;
        if (text.includes('2 day') || text.includes('2-day')) return 2;
        if (text.includes('1-3 days')) return 2;
        if (text.includes('2-3 days')) return 2;
        if (text.includes('3-5 days')) return 4;
        if (text.includes('1-5 days')) return 3;
        if (text.includes('5-7 days')) return 6;
        
        // Try to extract number
        const match = text.match(/(\d+)/);
        return match ? parseInt(match[1]) : 5;
    }

    isInternationalShipment(origin, destination) {
        const originCountry = origin.country_code || origin.country || 'US';
        const destCountry = destination.country_code || destination.country || 'US';
        return originCountry.toUpperCase() !== destCountry.toUpperCase();
    }

    async findConsolidationOpportunities(packages, rates, shipment) {
        const opportunities = [];
        
        // Same destination consolidation
        if (packages.length > 1) {
            const consolidatedWeight = packages.reduce((sum, pkg) => sum + pkg.weight, 0);
            const consolidatedVolume = packages.reduce((sum, pkg) => sum + pkg.volume, 0);
            
            if (consolidatedWeight <= 50 && consolidatedVolume <= 15000) {
                const singlePackageCost = await this.calculateConsolidatedShippingCost(packages, rates);
                const separateCosts = rates.reduce((sum, rate) => sum + rate.cost, 0);
                
                if (singlePackageCost < separateCosts * 0.85) {
                    opportunities.push({
                        type: 'same_destination_consolidation',
                        packages: packages.map(p => p.id || packages.indexOf(p)),
                        savings: separateCosts - singlePackageCost,
                        consolidated_weight: consolidatedWeight,
                        description: 'Consolidate all packages into single shipment',
                        cost_reduction: (separateCosts - singlePackageCost) / separateCosts
                    });
                }
            }
        }

        // Regional hub consolidation
        const hubConsolidation = await this.checkRegionalHubConsolidation(shipment, rates);
        if (hubConsolidation.viable) {
            opportunities.push(hubConsolidation);
        }

        return opportunities;
    }

    async calculateConsolidatedShippingCost(packages, rates) {
        const totalWeight = packages.reduce((sum, pkg) => sum + pkg.weight, 0);
        const maxDimensions = {
            length: Math.max(...packages.map(p => p.dimensions.length)),
            width: Math.max(...packages.map(p => p.dimensions.width)),
            height: packages.reduce((sum, p) => sum + p.dimensions.height, 0)
        };
        
        const consolidatedDimWeight = this.calculateDimensionalWeight(maxDimensions);
        const billableWeight = Math.max(totalWeight, consolidatedDimWeight);
        
        // Use cheapest available rate for consolidated shipment
        const cheapestRate = rates.sort((a, b) => a.cost - b.cost)[0];
        if (!cheapestRate) return 0;
        
        const zone = cheapestRate.zone;
        const baseRate = this.zoneMap.get(zone)?.base_cost || 10;
        
        return baseRate * (1 + (billableWeight - 1) * 0.5);
    }

    async checkRegionalHubConsolidation(shipment, rates) {
        // Mock regional hub consolidation check
        const nearbyHubs = await this.findNearbyConsolidationHubs(shipment.destination);
        
        if (nearbyHubs.length > 0) {
            const hubShipping = nearbyHubs[0];
            const potentialSavings = rates[0]?.cost * 0.25 || 0;
            
            return {
                viable: potentialSavings > 5,
                type: 'regional_hub_consolidation',
                hub: hubShipping,
                savings: potentialSavings,
                additional_transit_time: '1 day',
                description: 'Route through regional consolidation hub for cost savings'
            };
        }
        
        return { viable: false };
    }

    async findNearbyConsolidationHubs(destination) {
        // Mock hub lookup
        return [
            {
                id: 'hub_central_us',
                name: 'Central US Distribution Hub',
                location: { city: 'Chicago', state: 'IL', zip: '60601' },
                distance_miles: 150,
                services: ['consolidation', 'cross_dock', 'last_mile']
            }
        ];
    }

    async optimizeRoutes(shipment, rates, options) {
        const optimizations = [];
        
        // Multi-stop optimization
        if (shipment.multiple_destinations) {
            const multiStopOptimization = await this.optimizeMultiStopRoute(shipment, rates);
            optimizations.push(multiStopOptimization);
        }
        
        // Time-based optimization
        if (options.flexible_delivery) {
            const timeOptimization = this.optimizeByDeliveryTime(rates, options);
            optimizations.push(timeOptimization);
        }
        
        // Cost-based optimization
        const costOptimization = this.optimizeByCost(rates, options);
        optimizations.push(costOptimization);
        
        return optimizations;
    }

    async optimizeMultiStopRoute(shipment, rates) {
        // Mock multi-stop route optimization using nearest neighbor algorithm
        const destinations = shipment.multiple_destinations || [shipment.destination];
        const optimizedRoute = this.calculateOptimalRoute(shipment.origin, destinations);
        
        const originalCost = rates.reduce((sum, rate) => sum + rate.cost, 0);
        const optimizedCost = originalCost * 0.85; // Assume 15% savings through route optimization
        
        return {
            type: 'multi_stop_route',
            original_route: destinations,
            optimized_route: optimizedRoute,
            cost_savings: originalCost - optimizedCost,
            time_savings: '0.5 days',
            total_distance_saved: 50,
            description: 'Optimized delivery sequence for multiple destinations'
        };
    }

    calculateOptimalRoute(origin, destinations) {
        // Simplified nearest neighbor algorithm for route optimization
        const route = [origin];
        const unvisited = [...destinations];
        let current = origin;
        
        while (unvisited.length > 0) {
            let nearest = unvisited[0];
            let nearestDistance = this.calculateDistance(current, nearest);
            
            for (const destination of unvisited) {
                const distance = this.calculateDistance(current, destination);
                if (distance < nearestDistance) {
                    nearest = destination;
                    nearestDistance = distance;
                }
            }
            
            route.push(nearest);
            unvisited.splice(unvisited.indexOf(nearest), 1);
            current = nearest;
        }
        
        return route;
    }

    calculateDistance(point1, point2) {
        // Simplified distance calculation using ZIP codes
        const zip1 = parseInt(point1.zip_code || point1.postal_code || '10001');
        const zip2 = parseInt(point2.zip_code || point2.postal_code || '10001');
        return Math.abs(zip1 - zip2) / 1000; // Rough miles estimate
    }

    optimizeByDeliveryTime(rates, options) {
        const timePreference = options.delivery_preference || 'balanced';
        let sortedRates;
        
        switch (timePreference) {
            case 'fastest':
                sortedRates = rates.sort((a, b) => 
                    this.parseTransitTimeToDays(a.transit_time) - this.parseTransitTimeToDays(b.transit_time)
                );
                break;
            case 'cheapest':
                sortedRates = rates.sort((a, b) => a.cost - b.cost);
                break;
            default: // balanced
                sortedRates = rates.sort((a, b) => {
                    const timeA = this.parseTransitTimeToDays(a.transit_time);
                    const timeB = this.parseTransitTimeToDays(b.transit_time);
                    const scoreA = a.cost + (timeA * 5); // Weight time as $5 per day
                    const scoreB = b.cost + (timeB * 5);
                    return scoreA - scoreB;
                });
                break;
        }
        
        return {
            type: 'delivery_time_optimization',
            preference: timePreference,
            recommended_option: sortedRates[0],
            all_options: sortedRates,
            description: `Optimized for ${timePreference} delivery preference`
        };
    }

    optimizeByCost(rates, options) {
        const budgetConstraint = options.max_shipping_cost;
        let eligibleRates = rates;
        
        if (budgetConstraint) {
            eligibleRates = rates.filter(rate => rate.cost <= budgetConstraint);
        }
        
        const sortedByValue = eligibleRates.sort((a, b) => {
            const timeA = this.parseTransitTimeToDays(a.transit_time);
            const timeB = this.parseTransitTimeToDays(b.transit_time);
            const valueA = timeA / a.cost; // Lower is better (faster per dollar)
            const valueB = timeB / b.cost;
            return valueA - valueB;
        });
        
        return {
            type: 'cost_optimization',
            budget_constraint: budgetConstraint,
            eligible_options: eligibleRates.length,
            recommended_option: sortedByValue[0],
            potential_savings: rates[0]?.cost - (sortedByValue[0]?.cost || 0),
            description: 'Best value shipping option within budget constraints'
        };
    }

    calculateEnvironmentalImpact(rates, shipment) {
        const impact = {
            carbon_footprint_by_option: [],
            eco_friendly_recommendations: [],
            offset_opportunities: []
        };
        
        for (const rate of rates) {
            const distance = this.estimateShippingDistance(shipment.origin, shipment.destination);
            let carbonFactor = this.carbonFootprintCalculator.get('ground');
            
            // Determine carbon factor based on service type
            if (rate.service_name.toLowerCase().includes('overnight') || 
                rate.service_name.toLowerCase().includes('express')) {
                carbonFactor = this.carbonFootprintCalculator.get('overnight');
            } else if (rate.service_name.toLowerCase().includes('air') || 
                       rate.transit_time.includes('1 day')) {
                carbonFactor = this.carbonFootprintCalculator.get('air');
            } else if (rate.service_name.toLowerCase().includes('2 day')) {
                carbonFactor = this.carbonFootprintCalculator.get('express');
            }
            
            const carbonFootprint = distance * carbonFactor * rate.weight;
            
            impact.carbon_footprint_by_option.push({
                carrier: rate.carrier_name,
                service: rate.service_name,
                carbon_footprint_kg: carbonFootprint,
                distance_miles: distance,
                carbon_per_mile: carbonFactor,
                eco_rating: this.calculateEcoRating(carbonFootprint, rate.cost)
            });
        }
        
        // Find most eco-friendly option
        const ecoFriendly = impact.carbon_footprint_by_option
            .sort((a, b) => a.carbon_footprint_kg - b.carbon_footprint_kg)[0];
        
        if (ecoFriendly) {
            impact.eco_friendly_recommendations.push({
                recommended_option: ecoFriendly,
                carbon_savings: Math.max(...impact.carbon_footprint_by_option.map(o => o.carbon_footprint_kg)) - ecoFriendly.carbon_footprint_kg,
                description: 'Lowest carbon footprint shipping option'
            });
        }
        
        // Calculate offset opportunities
        const totalCarbon = impact.carbon_footprint_by_option.reduce((sum, option) => 
            sum + option.carbon_footprint_kg, 0) / impact.carbon_footprint_by_option.length;
        
        impact.offset_opportunities = [
            {
                carbon_to_offset_kg: totalCarbon,
                offset_cost_usd: totalCarbon * 0.02, // $0.02 per kg CO2
                offset_projects: ['reforestation', 'renewable_energy', 'carbon_capture'],
                description: 'Carbon offset options to neutralize shipping impact'
            }
        ];
        
        return impact;
    }

    estimateShippingDistance(origin, destination) {
        // Simplified distance estimation
        const originZip = parseInt(origin.zip_code || origin.postal_code || '10001');
        const destZip = parseInt(destination.zip_code || destination.postal_code || '10001');
        
        return Math.abs(originZip - destZip) / 100; // Rough miles estimate
    }

    calculateEcoRating(carbonFootprint, cost) {
        // Lower carbon per dollar spent = higher eco rating
        const carbonPerDollar = carbonFootprint / cost;
        
        if (carbonPerDollar < 0.1) return 'excellent';
        if (carbonPerDollar < 0.2) return 'good';
        if (carbonPerDollar < 0.4) return 'fair';
        return 'poor';
    }

    generateShippingRecommendations(rates, consolidationOpportunities, routeOptimizations, options) {
        const recommendations = [];
        
        if (rates.length === 0) return recommendations;
        
        // Best overall value recommendation
        const bestValue = this.findBestValueOption(rates, options);
        recommendations.push({
            type: 'best_value',
            option: bestValue,
            reason: 'Best balance of cost, speed, and reliability',
            confidence: 0.9
        });
        
        // Cheapest option
        const cheapest = rates.sort((a, b) => a.cost - b.cost)[0];
        if (cheapest.carrier_id !== bestValue.carrier_id || cheapest.service_code !== bestValue.service_code) {
            recommendations.push({
                type: 'lowest_cost',
                option: cheapest,
                savings: bestValue.cost - cheapest.cost,
                reason: 'Lowest shipping cost available',
                confidence: 0.95
            });
        }
        
        // Fastest option
        const fastest = rates.sort((a, b) => 
            this.parseTransitTimeToDays(a.transit_time) - this.parseTransitTimeToDays(b.transit_time))[0];
        if (fastest.carrier_id !== bestValue.carrier_id || fastest.service_code !== bestValue.service_code) {
            recommendations.push({
                type: 'fastest_delivery',
                option: fastest,
                time_saved: this.parseTransitTimeToDays(bestValue.transit_time) - this.parseTransitTimeToDays(fastest.transit_time),
                reason: 'Fastest available delivery time',
                confidence: 0.85
            });
        }
        
        // Consolidation recommendations
        for (const opportunity of consolidationOpportunities) {
            recommendations.push({
                type: 'consolidation_opportunity',
                opportunity,
                reason: opportunity.description,
                savings: opportunity.savings,
                confidence: 0.8
            });
        }
        
        // Route optimization recommendations
        for (const optimization of routeOptimizations) {
            if (optimization.cost_savings > 5) {
                recommendations.push({
                    type: 'route_optimization',
                    optimization,
                    reason: optimization.description,
                    savings: optimization.cost_savings,
                    confidence: 0.75
                });
            }
        }
        
        // Eco-friendly recommendation
        const ecoRates = rates.map(rate => ({
            ...rate,
            eco_score: this.calculateEcoScore(rate)
        })).sort((a, b) => b.eco_score - a.eco_score);
        
        if (ecoRates.length > 0) {
            recommendations.push({
                type: 'eco_friendly',
                option: ecoRates[0],
                reason: 'Most environmentally friendly shipping option',
                eco_benefits: 'Reduced carbon footprint',
                confidence: 0.7
            });
        }
        
        return recommendations;
    }

    findBestValueOption(rates, options) {
        const weightCost = options.prioritize_cost ? 0.7 : 0.4;
        const weightTime = options.prioritize_speed ? 0.7 : 0.4;
        const weightReliability = 0.2;
        
        return rates.map(rate => {
            const costScore = 1 - (rate.cost / Math.max(...rates.map(r => r.cost)));
            const timeScore = 1 - (this.parseTransitTimeToDays(rate.transit_time) / 7);
            const reliabilityScore = this.getCarrierReliability(rate.carrier_id);
            
            const totalScore = (costScore * weightCost) + (timeScore * weightTime) + (reliabilityScore * weightReliability);
            
            return { ...rate, value_score: totalScore };
        }).sort((a, b) => b.value_score - a.value_score)[0];
    }

    getCarrierReliability(carrierId) {
        const carrier = this.carriers.get(carrierId);
        return carrier?.reliability_score || 0.8;
    }

    calculateEcoScore(rate) {
        // Simple eco score based on transit time (ground = better, overnight = worse)
        const transitDays = this.parseTransitTimeToDays(rate.transit_time);
        return Math.min(1, transitDays / 7); // Normalize to 0-1, slower = better for environment
    }

    performCostAnalysis(rates) {
        if (rates.length === 0) return {};
        
        const costs = rates.map(r => r.cost);
        const transitTimes = rates.map(r => this.parseTransitTimeToDays(r.transit_time));
        
        return {
            price_range: {
                lowest: Math.min(...costs),
                highest: Math.max(...costs),
                average: costs.reduce((sum, cost) => sum + cost, 0) / costs.length,
                median: costs.sort((a, b) => a - b)[Math.floor(costs.length / 2)]
            },
            time_range: {
                fastest: Math.min(...transitTimes),
                slowest: Math.max(...transitTimes),
                average: transitTimes.reduce((sum, time) => sum + time, 0) / transitTimes.length
            },
            carrier_breakdown: this.groupRatesByCarrier(rates),
            cost_per_day_analysis: this.analyzeCostPerDay(rates),
            savings_opportunities: this.identifySavingsOpportunities(rates)
        };
    }

    groupRatesByCarrier(rates) {
        const breakdown = new Map();
        
        for (const rate of rates) {
            if (!breakdown.has(rate.carrier_id)) {
                breakdown.set(rate.carrier_id, {
                    carrier_name: rate.carrier_name,
                    services: [],
                    cost_range: { min: Infinity, max: 0 },
                    avg_cost: 0,
                    service_count: 0
                });
            }
            
            const carrierData = breakdown.get(rate.carrier_id);
            carrierData.services.push(rate);
            carrierData.cost_range.min = Math.min(carrierData.cost_range.min, rate.cost);
            carrierData.cost_range.max = Math.max(carrierData.cost_range.max, rate.cost);
            carrierData.service_count++;
        }
        
        // Calculate averages
        for (const [carrierId, data] of breakdown) {
            data.avg_cost = data.services.reduce((sum, rate) => sum + rate.cost, 0) / data.services.length;
        }
        
        return Object.fromEntries(breakdown);
    }

    analyzeCostPerDay(rates) {
        return rates.map(rate => ({
            carrier: rate.carrier_name,
            service: rate.service_name,
            cost: rate.cost,
            transit_days: this.parseTransitTimeToDays(rate.transit_time),
            cost_per_day: rate.cost / Math.max(1, this.parseTransitTimeToDays(rate.transit_time)),
            value_rating: this.calculateValueRating(rate)
        })).sort((a, b) => a.cost_per_day - b.cost_per_day);
    }

    calculateValueRating(rate) {
        const costScore = 1 / (rate.cost / 10); // Normalize by $10
        const timeScore = 1 / this.parseTransitTimeToDays(rate.transit_time);
        const reliabilityScore = this.getCarrierReliability(rate.carrier_id);
        
        return (costScore + timeScore + reliabilityScore) / 3;
    }

    identifySavingsOpportunities(rates) {
        const opportunities = [];
        const costs = rates.map(r => r.cost).sort((a, b) => a - b);
        
        if (costs.length >= 2) {
            const cheapest = costs[0];
            const mostExpensive = costs[costs.length - 1];
            const median = costs[Math.floor(costs.length / 2)];
            
            opportunities.push({
                type: 'carrier_comparison',
                potential_savings: mostExpensive - cheapest,
                percentage_savings: ((mostExpensive - cheapest) / mostExpensive) * 100,
                description: 'Switch to cheapest carrier option'
            });
            
            if (median - cheapest > 5) {
                opportunities.push({
                    type: 'below_median_options',
                    count: costs.filter(c => c < median).length,
                    avg_savings: median - cheapest,
                    description: 'Multiple options available below median cost'
                });
            }
        }
        
        return opportunities;
    }

    async trackShipment(trackingNumber, carrierId) {
        const carrier = this.carriers.get(carrierId);
        if (!carrier) {
            throw new Error(`Carrier ${carrierId} not found`);
        }
        
        // Mock tracking data
        return {
            tracking_number: trackingNumber,
            carrier: carrier.name,
            status: 'in_transit',
            estimated_delivery: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000),
            location: 'Distribution Center - Chicago, IL',
            events: [
                {
                    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
                    status: 'picked_up',
                    location: 'Origin Facility'
                },
                {
                    timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000),
                    status: 'in_transit',
                    location: 'Sort Facility - Indianapolis, IN'
                },
                {
                    timestamp: new Date(),
                    status: 'in_transit',
                    location: 'Distribution Center - Chicago, IL'
                }
            ]
        };
    }
}