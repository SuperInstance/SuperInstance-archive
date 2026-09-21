const EventEmitter = require('events');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class SupplyChainTracker extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.suppliers = new Map();
        this.shipments = new Map();
        this.trackingProviders = new Map();
        this.deliveryZones = new Map();
        this.contractTerms = new Map();
        
        this.setupEventHandlers();
        this.setupTrackingProviders();
        this.startShipmentMonitoring();
    }

    setupEventHandlers() {
        this.on('shipment_created', this.handleShipmentCreated.bind(this));
        this.on('shipment_updated', this.handleShipmentUpdated.bind(this));
        this.on('delivery_delayed', this.handleDeliveryDelayed.bind(this));
        this.on('supplier_performance_alert', this.handleSupplierAlert.bind(this));
    }

    setupTrackingProviders() {
        this.trackingProviders.set('fedex', {
            name: 'FedEx',
            endpoint: 'https://apis.fedex.com/track/v1/trackingnumbers',
            apiKey: process.env.FEDEX_API_KEY,
            authMethod: 'oauth'
        });
        
        this.trackingProviders.set('ups', {
            name: 'UPS',
            endpoint: 'https://onlinetools.ups.com/api/track/v1/details',
            apiKey: process.env.UPS_API_KEY,
            authMethod: 'basic'
        });
        
        this.trackingProviders.set('dhl', {
            name: 'DHL',
            endpoint: 'https://api-eu.dhl.com/track/shipments',
            apiKey: process.env.DHL_API_KEY,
            authMethod: 'apikey'
        });
        
        this.trackingProviders.set('usps', {
            name: 'USPS',
            endpoint: 'https://secure.shippingapis.com/ShippingAPI.dll',
            apiKey: process.env.USPS_USER_ID,
            authMethod: 'userid'
        });
    }

    async registerSupplier(supplierData) {
        try {
            const supplierId = uuidv4();
            const supplier = {
                id: supplierId,
                name: supplierData.name,
                code: supplierData.code || this.generateSupplierCode(supplierData.name),
                contact: {
                    email: supplierData.contact.email,
                    phone: supplierData.contact.phone,
                    address: supplierData.contact.address,
                    contactPerson: supplierData.contact.contactPerson
                },
                capabilities: {
                    products: supplierData.products || [],
                    leadTimes: supplierData.leadTimes || {},
                    minimumOrderQuantities: supplierData.minimumOrderQuantities || {},
                    shippingMethods: supplierData.shippingMethods || ['standard']
                },
                performance: {
                    onTimeDeliveryRate: 100,
                    qualityScore: 100,
                    totalOrders: 0,
                    totalValue: 0,
                    averageLeadTime: 0,
                    defectRate: 0
                },
                status: 'active',
                registeredAt: new Date(),
                lastOrderDate: null,
                contractTerms: supplierData.contractTerms || {},
                certifications: supplierData.certifications || [],
                riskScore: this.calculateSupplierRisk(supplierData)
            };

            this.suppliers.set(supplierId, supplier);
            await this.redis.hset('suppliers', supplierId, JSON.stringify(supplier));
            
            this.logger.info('Supplier registered successfully', { 
                supplierId, 
                name: supplier.name, 
                code: supplier.code 
            });
            
            this.io.emit('supplier_registered', {
                supplierId,
                name: supplier.name,
                code: supplier.code,
                status: supplier.status
            });
            
            return { success: true, supplierId, supplier: this.sanitizeSupplierData(supplier) };
        } catch (error) {
            this.logger.error('Failed to register supplier', { error: error.message, supplierData });
            throw new Error(`Supplier registration failed: ${error.message}`);
        }
    }

    async createPurchaseOrder(orderData) {
        try {
            const orderId = uuidv4();
            const order = {
                id: orderId,
                supplierId: orderData.supplierId,
                locationId: orderData.locationId,
                orderNumber: orderData.orderNumber || this.generateOrderNumber(),
                items: orderData.items.map(item => ({
                    id: uuidv4(),
                    sku: item.sku,
                    name: item.name,
                    quantity: item.quantity,
                    unitCost: item.unitCost,
                    totalCost: item.quantity * item.unitCost,
                    expectedDeliveryDate: item.expectedDeliveryDate
                })),
                status: 'pending',
                totalAmount: orderData.items.reduce((sum, item) => sum + (item.quantity * item.unitCost), 0),
                currency: orderData.currency || 'USD',
                expectedDeliveryDate: orderData.expectedDeliveryDate,
                shippingAddress: orderData.shippingAddress,
                terms: orderData.terms || {},
                createdAt: new Date(),
                createdBy: orderData.createdBy,
                notes: orderData.notes || '',
                trackingInfo: null
            };

            await this.redis.hset('purchase_orders', orderId, JSON.stringify(order));
            
            const supplier = this.suppliers.get(orderData.supplierId);
            if (supplier) {
                await this.sendOrderToSupplier(supplier, order);
            }
            
            this.logger.info('Purchase order created', { 
                orderId, 
                supplierId: orderData.supplierId, 
                total: order.totalAmount 
            });
            
            this.io.to(`location_${orderData.locationId}`).emit('purchase_order_created', {
                orderId,
                orderNumber: order.orderNumber,
                supplierId: orderData.supplierId,
                total: order.totalAmount,
                expectedDelivery: order.expectedDeliveryDate
            });
            
            return { success: true, orderId, order: this.sanitizeOrderData(order) };
        } catch (error) {
            this.logger.error('Failed to create purchase order', { error: error.message, orderData });
            throw new Error(`Purchase order creation failed: ${error.message}`);
        }
    }

    async trackShipment(shipmentData) {
        try {
            const shipmentId = uuidv4();
            const shipment = {
                id: shipmentId,
                orderId: shipmentData.orderId,
                trackingNumber: shipmentData.trackingNumber,
                carrier: shipmentData.carrier,
                supplierId: shipmentData.supplierId,
                locationId: shipmentData.locationId,
                origin: shipmentData.origin,
                destination: shipmentData.destination,
                status: 'in_transit',
                estimatedDelivery: shipmentData.estimatedDelivery,
                actualDelivery: null,
                items: shipmentData.items || [],
                events: [{
                    timestamp: new Date(),
                    status: 'shipped',
                    location: shipmentData.origin,
                    description: 'Package shipped from supplier',
                    source: 'manual'
                }],
                createdAt: new Date(),
                lastTracked: new Date(),
                delays: [],
                metadata: shipmentData.metadata || {}
            };

            this.shipments.set(shipmentId, shipment);
            await this.redis.hset('shipments', shipmentId, JSON.stringify(shipment));
            
            this.scheduleTrackingUpdates(shipmentId);
            
            this.logger.info('Shipment tracking started', { 
                shipmentId, 
                trackingNumber: shipment.trackingNumber, 
                carrier: shipment.carrier 
            });
            
            this.io.to(`location_${shipmentData.locationId}`).emit('shipment_created', {
                shipmentId,
                trackingNumber: shipment.trackingNumber,
                carrier: shipment.carrier,
                estimatedDelivery: shipment.estimatedDelivery
            });
            
            this.emit('shipment_created', shipment);
            
            return { success: true, shipmentId, shipment: this.sanitizeShipmentData(shipment) };
        } catch (error) {
            this.logger.error('Failed to track shipment', { error: error.message, shipmentData });
            throw new Error(`Shipment tracking failed: ${error.message}`);
        }
    }

    async updateShipmentStatus(shipmentId, trackingData) {
        try {
            const shipment = this.shipments.get(shipmentId) || 
                JSON.parse(await this.redis.hget('shipments', shipmentId));
            
            if (!shipment) {
                throw new Error(`Shipment ${shipmentId} not found`);
            }
            
            const previousStatus = shipment.status;
            shipment.status = trackingData.status;
            shipment.lastTracked = new Date();
            
            if (trackingData.estimatedDelivery && trackingData.estimatedDelivery !== shipment.estimatedDelivery) {
                const originalDelivery = new Date(shipment.estimatedDelivery);
                const newDelivery = new Date(trackingData.estimatedDelivery);
                
                if (newDelivery > originalDelivery) {
                    const delayHours = Math.round((newDelivery - originalDelivery) / (1000 * 60 * 60));
                    shipment.delays.push({
                        detectedAt: new Date(),
                        originalDelivery: shipment.estimatedDelivery,
                        newDelivery: trackingData.estimatedDelivery,
                        delayHours,
                        reason: trackingData.delayReason || 'Unknown'
                    });
                    
                    this.emit('delivery_delayed', {
                        shipmentId,
                        delayHours,
                        reason: trackingData.delayReason
                    });
                }
                
                shipment.estimatedDelivery = trackingData.estimatedDelivery;
            }
            
            if (trackingData.events) {
                shipment.events.push(...trackingData.events.map(event => ({
                    ...event,
                    timestamp: new Date(event.timestamp),
                    source: 'carrier_api'
                })));
            }
            
            if (trackingData.status === 'delivered') {
                shipment.actualDelivery = new Date();
                await this.processDelivery(shipment);
            }
            
            this.shipments.set(shipmentId, shipment);
            await this.redis.hset('shipments', shipmentId, JSON.stringify(shipment));
            
            if (previousStatus !== shipment.status) {
                this.io.to(`location_${shipment.locationId}`).emit('shipment_status_updated', {
                    shipmentId,
                    status: shipment.status,
                    estimatedDelivery: shipment.estimatedDelivery,
                    events: shipment.events.slice(-3)
                });
                
                this.emit('shipment_updated', { shipment, previousStatus });
            }
            
            return { success: true, shipment: this.sanitizeShipmentData(shipment) };
        } catch (error) {
            this.logger.error('Failed to update shipment status', { error: error.message, shipmentId });
            throw new Error(`Shipment update failed: ${error.message}`);
        }
    }

    async processDelivery(shipment) {
        try {
            for (const item of shipment.items) {
                const inventoryUpdate = {
                    locationId: shipment.locationId,
                    itemId: item.sku,
                    change: {
                        type: 'delivery',
                        quantity: item.quantity,
                        reference: `SHIPMENT-${shipment.id}`,
                        timestamp: shipment.actualDelivery,
                        unitCost: item.unitCost,
                        supplierId: shipment.supplierId
                    },
                    source: 'supply_chain',
                    shipmentId: shipment.id
                };
                
                await this.redis.lpush(
                    `inventory_updates:${shipment.locationId}`, 
                    JSON.stringify(inventoryUpdate)
                );
            }
            
            await this.updateSupplierPerformance(shipment.supplierId, shipment);
            
            this.logger.info('Delivery processed successfully', { 
                shipmentId: shipment.id, 
                items: shipment.items.length 
            });
            
            this.io.to(`location_${shipment.locationId}`).emit('delivery_completed', {
                shipmentId: shipment.id,
                items: shipment.items.length,
                deliveredAt: shipment.actualDelivery
            });
            
        } catch (error) {
            this.logger.error('Failed to process delivery', { error: error.message, shipmentId: shipment.id });
            throw error;
        }
    }

    async updateSupplierPerformance(supplierId, shipment) {
        const supplier = this.suppliers.get(supplierId) || 
            JSON.parse(await this.redis.hget('suppliers', supplierId));
        
        if (!supplier) return;
        
        supplier.performance.totalOrders++;
        supplier.performance.totalValue += shipment.items.reduce((sum, item) => 
            sum + (item.quantity * item.unitCost), 0);
        
        const expectedDelivery = new Date(shipment.estimatedDelivery);
        const actualDelivery = new Date(shipment.actualDelivery);
        const deliveredOnTime = actualDelivery <= expectedDelivery;
        
        const currentRate = supplier.performance.onTimeDeliveryRate;
        const totalOrders = supplier.performance.totalOrders;
        supplier.performance.onTimeDeliveryRate = 
            ((currentRate * (totalOrders - 1)) + (deliveredOnTime ? 100 : 0)) / totalOrders;
        
        const leadTimeHours = (actualDelivery - new Date(shipment.createdAt)) / (1000 * 60 * 60);
        supplier.performance.averageLeadTime = 
            ((supplier.performance.averageLeadTime * (totalOrders - 1)) + leadTimeHours) / totalOrders;
        
        supplier.lastOrderDate = new Date();
        
        this.suppliers.set(supplierId, supplier);
        await this.redis.hset('suppliers', supplierId, JSON.stringify(supplier));
        
        if (supplier.performance.onTimeDeliveryRate < 85) {
            this.emit('supplier_performance_alert', {
                supplierId,
                metric: 'on_time_delivery',
                value: supplier.performance.onTimeDeliveryRate,
                threshold: 85
            });
        }
    }

    async getShipmentTracking(trackingNumber, carrier) {
        try {
            const provider = this.trackingProviders.get(carrier.toLowerCase());
            if (!provider) {
                throw new Error(`Tracking provider not supported: ${carrier}`);
            }
            
            let trackingData;
            switch (carrier.toLowerCase()) {
                case 'fedex':
                    trackingData = await this.trackFedExPackage(trackingNumber, provider);
                    break;
                case 'ups':
                    trackingData = await this.trackUPSPackage(trackingNumber, provider);
                    break;
                case 'dhl':
                    trackingData = await this.trackDHLPackage(trackingNumber, provider);
                    break;
                case 'usps':
                    trackingData = await this.trackUSPSPackage(trackingNumber, provider);
                    break;
                default:
                    throw new Error(`Unsupported carrier: ${carrier}`);
            }
            
            return trackingData;
        } catch (error) {
            this.logger.error('Failed to get shipment tracking', { 
                error: error.message, 
                trackingNumber, 
                carrier 
            });
            throw error;
        }
    }

    async trackFedExPackage(trackingNumber, provider) {
        const response = await axios.post(provider.endpoint, {
            trackingInfo: [{
                trackingNumberInfo: {
                    trackingNumber
                }
            }]
        }, {
            headers: {
                'Authorization': `Bearer ${await this.getFedExToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        const trackInfo = response.data.output.completeTrackResults[0].trackResults[0];
        return this.parseFedExTracking(trackInfo);
    }

    async trackUPSPackage(trackingNumber, provider) {
        const response = await axios.get(`${provider.endpoint}/${trackingNumber}`, {
            headers: {
                'Authorization': `Basic ${Buffer.from(`${provider.username}:${provider.password}`).toString('base64')}`,
                'Content-Type': 'application/json'
            }
        });
        
        return this.parseUPSTracking(response.data);
    }

    async getSupplyChainMetrics(locationId, timeframe = '30d') {
        const startDate = moment().subtract(30, 'days').toDate();
        const endDate = new Date();
        
        const metrics = {
            totalOrders: 0,
            totalValue: 0,
            averageLeadTime: 0,
            onTimeDeliveryRate: 0,
            activeShipments: 0,
            delayedShipments: 0,
            topSuppliers: [],
            categoryBreakdown: {},
            monthlyTrends: {}
        };
        
        const orderKeys = await this.redis.hkeys('purchase_orders');
        const shipmentKeys = await this.redis.hkeys('shipments');
        
        const orders = [];
        const shipments = [];
        
        for (const key of orderKeys) {
            const orderData = await this.redis.hget('purchase_orders', key);
            if (orderData) {
                const order = JSON.parse(orderData);
                if (order.locationId === locationId && 
                    new Date(order.createdAt) >= startDate) {
                    orders.push(order);
                }
            }
        }
        
        for (const key of shipmentKeys) {
            const shipmentData = await this.redis.hget('shipments', key);
            if (shipmentData) {
                const shipment = JSON.parse(shipmentData);
                if (shipment.locationId === locationId) {
                    shipments.push(shipment);
                }
            }
        }
        
        metrics.totalOrders = orders.length;
        metrics.totalValue = orders.reduce((sum, order) => sum + order.totalAmount, 0);
        
        const deliveredShipments = shipments.filter(s => s.actualDelivery);
        const onTimeDeliveries = deliveredShipments.filter(s => 
            new Date(s.actualDelivery) <= new Date(s.estimatedDelivery));
        
        metrics.onTimeDeliveryRate = deliveredShipments.length > 0 
            ? (onTimeDeliveries.length / deliveredShipments.length) * 100 
            : 0;
        
        metrics.activeShipments = shipments.filter(s => 
            ['in_transit', 'out_for_delivery'].includes(s.status)).length;
        
        metrics.delayedShipments = shipments.filter(s => 
            s.delays && s.delays.length > 0).length;
        
        const supplierMap = new Map();
        for (const order of orders) {
            const current = supplierMap.get(order.supplierId) || { orders: 0, value: 0 };
            current.orders++;
            current.value += order.totalAmount;
            supplierMap.set(order.supplierId, current);
        }
        
        metrics.topSuppliers = Array.from(supplierMap.entries())
            .map(([supplierId, data]) => ({ supplierId, ...data }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);
        
        return metrics;
    }

    async scheduleTrackingUpdates(shipmentId) {
        const updateInterval = setInterval(async () => {
            try {
                const shipment = this.shipments.get(shipmentId) || 
                    JSON.parse(await this.redis.hget('shipments', shipmentId));
                
                if (!shipment || ['delivered', 'cancelled'].includes(shipment.status)) {
                    clearInterval(updateInterval);
                    return;
                }
                
                const trackingData = await this.getShipmentTracking(
                    shipment.trackingNumber, 
                    shipment.carrier
                );
                
                await this.updateShipmentStatus(shipmentId, trackingData);
                
            } catch (error) {
                this.logger.error('Tracking update failed', { 
                    error: error.message, 
                    shipmentId 
                });
            }
        }, 30 * 60 * 1000); // Update every 30 minutes
        
        setTimeout(() => {
            clearInterval(updateInterval);
        }, 7 * 24 * 60 * 60 * 1000); // Stop after 7 days
    }

    startShipmentMonitoring() {
        setInterval(async () => {
            try {
                await this.checkOverdueShipments();
                await this.updateAllActiveShipments();
            } catch (error) {
                this.logger.error('Shipment monitoring error', { error: error.message });
            }
        }, 15 * 60 * 1000); // Check every 15 minutes
    }

    async checkOverdueShipments() {
        const now = new Date();
        const overdueThreshold = 24 * 60 * 60 * 1000; // 24 hours
        
        for (const [shipmentId, shipment] of this.shipments) {
            if (shipment.status === 'in_transit' && 
                shipment.estimatedDelivery && 
                now - new Date(shipment.estimatedDelivery) > overdueThreshold) {
                
                this.io.to(`location_${shipment.locationId}`).emit('shipment_overdue', {
                    shipmentId,
                    trackingNumber: shipment.trackingNumber,
                    hoursOverdue: Math.round((now - new Date(shipment.estimatedDelivery)) / (1000 * 60 * 60))
                });
            }
        }
    }

    generateSupplierCode(name) {
        return name.toUpperCase()
            .replace(/[^A-Z0-9]/g, '')
            .substring(0, 6) + 
            Math.random().toString(36).substring(2, 5).toUpperCase();
    }

    generateOrderNumber() {
        return 'PO-' + moment().format('YYYYMMDD') + '-' + 
            Math.random().toString(36).substring(2, 8).toUpperCase();
    }

    calculateSupplierRisk(supplierData) {
        let riskScore = 0;
        
        if (!supplierData.certifications || supplierData.certifications.length === 0) {
            riskScore += 20;
        }
        
        if (!supplierData.contact.address) {
            riskScore += 15;
        }
        
        if (!supplierData.contractTerms || Object.keys(supplierData.contractTerms).length === 0) {
            riskScore += 25;
        }
        
        return Math.min(riskScore, 100);
    }

    sanitizeSupplierData(supplier) {
        const { credentials, ...sanitized } = supplier;
        return sanitized;
    }

    sanitizeOrderData(order) {
        return order;
    }

    sanitizeShipmentData(shipment) {
        return shipment;
    }

    handleShipmentCreated(shipment) {
        this.logger.info('Shipment tracking initiated', { 
            shipmentId: shipment.id,
            trackingNumber: shipment.trackingNumber 
        });
    }

    handleShipmentUpdated(data) {
        this.logger.info('Shipment status updated', { 
            shipmentId: data.shipment.id,
            status: data.shipment.status,
            previousStatus: data.previousStatus 
        });
    }

    handleDeliveryDelayed(data) {
        this.logger.warn('Delivery delayed', data);
        
        this.io.emit('delivery_delay_alert', {
            shipmentId: data.shipmentId,
            delayHours: data.delayHours,
            reason: data.reason
        });
    }

    handleSupplierAlert(data) {
        this.logger.warn('Supplier performance alert', data);
        
        this.io.emit('supplier_performance_alert', data);
    }
}

module.exports = SupplyChainTracker;