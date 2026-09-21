import EventEmitter from 'events';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default class OrderTracker extends EventEmitter {
    constructor(logger) {
        super();
        this.logger = logger;
        this.orders = new Map();
        this.trackingProviders = new Map();
        this.orderStatuses = new Map();
        this.milestones = new Map();
        this.notifications = new Map();
        this.delays = new Map();
        this.deliveryEstimates = new Map();
        this.customerCommunication = new Map();
        this.analytics = new Map();
        this.integrations = new Map();
        this.automationRules = new Map();
        this.slaMonitoring = new Map();

        this.initializeTrackingSystem();
        this.initializeOrderStatuses();
        this.initializeTrackingProviders();
        this.initializeAutomationRules();
        this.initializeSLAMonitoring();
    }

    async initializeTrackingSystem() {
        try {
            const trackingPath = path.join(__dirname, '../data/tracking-config.json');
            const trackingData = await fs.readFile(trackingPath, 'utf8');
            const config = JSON.parse(trackingData);
            
            // Load existing orders if any
            if (config.orders) {
                for (const order of config.orders) {
                    this.orders.set(order.id, order);
                }
            }
            
            this.logger.info(`Loaded tracking configuration with ${this.orders.size} orders`);
        } catch (error) {
            this.logger.warn('Could not load tracking configuration, using defaults');
            this.initializeDefaultConfiguration();
        }
    }

    initializeDefaultConfiguration() {
        // Initialize with sample tracking data
        const sampleOrder = {
            id: 'order_sample_001',
            customer_id: 'customer_001',
            vendor_id: 'techparts_direct',
            status: 'in_transit',
            items: [
                {
                    id: 'item_001',
                    name: 'PCB Assembly',
                    quantity: 10,
                    unit_price: 25.00
                }
            ],
            created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
            shipped_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
            estimated_delivery: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000),
            tracking_number: 'TRK123456789',
            carrier: 'fedex',
            shipping_address: {
                name: 'John Doe',
                address: '123 Main St',
                city: 'San Francisco',
                state: 'CA',
                zip: '94105',
                country: 'US'
            }
        };

        this.orders.set(sampleOrder.id, sampleOrder);
    }

    initializeOrderStatuses() {
        const statuses = [
            {
                id: 'pending',
                name: 'Pending',
                description: 'Order received and awaiting processing',
                customer_message: 'Your order has been received and is being processed.',
                next_statuses: ['confirmed', 'cancelled'],
                sla_hours: 2,
                color: '#FFA500'
            },
            {
                id: 'confirmed',
                name: 'Confirmed',
                description: 'Order confirmed and inventory allocated',
                customer_message: 'Your order has been confirmed and inventory has been allocated.',
                next_statuses: ['processing', 'backordered'],
                sla_hours: 24,
                color: '#1E90FF'
            },
            {
                id: 'processing',
                name: 'Processing',
                description: 'Order is being prepared for shipment',
                customer_message: 'Your order is being prepared for shipment.',
                next_statuses: ['shipped', 'delayed'],
                sla_hours: 48,
                color: '#FF8C00'
            },
            {
                id: 'shipped',
                name: 'Shipped',
                description: 'Order has been shipped',
                customer_message: 'Your order has been shipped and is on its way.',
                next_statuses: ['in_transit', 'exception'],
                sla_hours: 2,
                color: '#32CD32'
            },
            {
                id: 'in_transit',
                name: 'In Transit',
                description: 'Package is in transit to destination',
                customer_message: 'Your package is on its way to you.',
                next_statuses: ['out_for_delivery', 'exception', 'delayed'],
                sla_hours: null, // Carrier dependent
                color: '#4169E1'
            },
            {
                id: 'out_for_delivery',
                name: 'Out for Delivery',
                description: 'Package is out for delivery',
                customer_message: 'Your package is out for delivery and should arrive today.',
                next_statuses: ['delivered', 'delivery_attempted'],
                sla_hours: 12,
                color: '#228B22'
            },
            {
                id: 'delivered',
                name: 'Delivered',
                description: 'Package has been delivered',
                customer_message: 'Your order has been successfully delivered.',
                next_statuses: [],
                sla_hours: null,
                color: '#008000'
            },
            {
                id: 'cancelled',
                name: 'Cancelled',
                description: 'Order has been cancelled',
                customer_message: 'Your order has been cancelled.',
                next_statuses: [],
                sla_hours: null,
                color: '#DC143C'
            },
            {
                id: 'returned',
                name: 'Returned',
                description: 'Package has been returned',
                customer_message: 'Your package has been returned to the sender.',
                next_statuses: ['refunded', 'replacement_sent'],
                sla_hours: 72,
                color: '#8B0000'
            },
            {
                id: 'exception',
                name: 'Exception',
                description: 'Delivery exception occurred',
                customer_message: 'There has been an exception with your delivery. We are working to resolve it.',
                next_statuses: ['in_transit', 'delivered', 'returned'],
                sla_hours: 24,
                color: '#FF4500'
            }
        ];

        statuses.forEach(status => {
            this.orderStatuses.set(status.id, status);
        });
    }

    initializeTrackingProviders() {
        const providers = [
            {
                id: 'fedex',
                name: 'FedEx',
                api_endpoint: 'https://apis.fedex.com/track/v1/trackingnumbers',
                api_key_env: 'FEDEX_API_KEY',
                auth_type: 'oauth2',
                tracking_url_template: 'https://www.fedex.com/fedextrack/?trknbr={tracking_number}',
                supported_services: ['fedex_ground', 'fedex_express', 'fedex_overnight'],
                update_frequency: 15, // minutes
                features: ['real_time_tracking', 'delivery_signature', 'photo_on_delivery'],
                status_mapping: {
                    'Picked up': 'shipped',
                    'In transit': 'in_transit',
                    'Out for delivery': 'out_for_delivery',
                    'Delivered': 'delivered',
                    'Exception': 'exception'
                }
            },
            {
                id: 'ups',
                name: 'UPS',
                api_endpoint: 'https://onlinetools.ups.com/track/v1/details',
                api_key_env: 'UPS_API_KEY',
                auth_type: 'oauth2',
                tracking_url_template: 'https://www.ups.com/track?tracknum={tracking_number}',
                supported_services: ['ups_ground', 'ups_air', 'ups_next_day'],
                update_frequency: 20, // minutes
                features: ['real_time_tracking', 'delivery_notification', 'access_point_delivery'],
                status_mapping: {
                    'Order Processed': 'confirmed',
                    'In Transit': 'in_transit',
                    'Out For Delivery': 'out_for_delivery',
                    'Delivered': 'delivered',
                    'Exception': 'exception'
                }
            },
            {
                id: 'usps',
                name: 'USPS',
                api_endpoint: 'https://secure.shippingapis.com/ShippingAPI.dll',
                api_key_env: 'USPS_API_KEY',
                auth_type: 'api_key',
                tracking_url_template: 'https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}',
                supported_services: ['priority_mail', 'priority_express', 'ground_advantage'],
                update_frequency: 30, // minutes
                features: ['basic_tracking', 'delivery_notification'],
                status_mapping: {
                    'Accepted': 'confirmed',
                    'In Transit': 'in_transit',
                    'Out for Delivery': 'out_for_delivery',
                    'Delivered': 'delivered'
                }
            },
            {
                id: 'dhl',
                name: 'DHL Express',
                api_endpoint: 'https://api-eu.dhl.com/track/shipments',
                api_key_env: 'DHL_API_KEY',
                auth_type: 'api_key',
                tracking_url_template: 'https://www.dhl.com/en/express/tracking.html?AWB={tracking_number}',
                supported_services: ['dhl_express', 'dhl_express_12', 'dhl_express_worldwide'],
                update_frequency: 10, // minutes
                features: ['real_time_tracking', 'international_tracking', 'customs_clearance'],
                status_mapping: {
                    'Shipment picked up': 'shipped',
                    'Transit': 'in_transit',
                    'With delivery courier': 'out_for_delivery',
                    'Delivered': 'delivered',
                    'Clearance event': 'in_transit'
                }
            },
            {
                id: 'amazon_logistics',
                name: 'Amazon Logistics',
                api_endpoint: 'https://sellingpartnerapi-na.amazon.com/orders/v0/orders',
                api_key_env: 'AMAZON_SP_API_KEY',
                auth_type: 'aws_signature',
                tracking_url_template: 'https://track.amazon.com/tracking/{tracking_number}',
                supported_services: ['amazon_standard', 'amazon_same_day'],
                update_frequency: 5, // minutes
                features: ['real_time_tracking', 'delivery_photo', 'safe_place_delivery'],
                status_mapping: {
                    'Preparing for shipment': 'processing',
                    'Shipped': 'shipped',
                    'In transit': 'in_transit',
                    'Out for delivery': 'out_for_delivery',
                    'Delivered': 'delivered'
                }
            }
        ];

        providers.forEach(provider => {
            this.trackingProviders.set(provider.id, provider);
        });

        this.logger.info(`Initialized ${providers.length} tracking providers`);
    }

    initializeAutomationRules() {
        const rules = [
            {
                id: 'delayed_order_notification',
                name: 'Delayed Order Notification',
                description: 'Notify customer when order is delayed beyond estimated delivery',
                trigger: 'delivery_date_passed',
                conditions: {
                    status_not_in: ['delivered', 'cancelled', 'returned'],
                    hours_past_estimate: 6
                },
                actions: [
                    { type: 'send_notification', template: 'delivery_delay' },
                    { type: 'update_status', new_status: 'delayed' },
                    { type: 'escalate_to_support', priority: 'medium' }
                ],
                enabled: true
            },
            {
                id: 'delivery_confirmation',
                name: 'Delivery Confirmation',
                description: 'Send delivery confirmation and request feedback',
                trigger: 'status_change',
                conditions: {
                    new_status: 'delivered'
                },
                actions: [
                    { type: 'send_notification', template: 'delivery_confirmation' },
                    { type: 'schedule_feedback_request', delay_hours: 24 },
                    { type: 'update_vendor_performance', metric: 'delivery_success' }
                ],
                enabled: true
            },
            {
                id: 'exception_handling',
                name: 'Exception Handling',
                description: 'Handle delivery exceptions automatically',
                trigger: 'status_change',
                conditions: {
                    new_status: 'exception'
                },
                actions: [
                    { type: 'send_notification', template: 'delivery_exception' },
                    { type: 'create_support_ticket', priority: 'high' },
                    { type: 'attempt_redelivery', max_attempts: 3 }
                ],
                enabled: true
            },
            {
                id: 'proactive_communication',
                name: 'Proactive Communication',
                description: 'Send proactive updates at key milestones',
                trigger: 'status_change',
                conditions: {
                    new_status_in: ['shipped', 'in_transit', 'out_for_delivery']
                },
                actions: [
                    { type: 'send_notification', template: 'status_update' },
                    { type: 'update_delivery_estimate' }
                ],
                enabled: true
            }
        ];

        rules.forEach(rule => {
            this.automationRules.set(rule.id, rule);
        });
    }

    initializeSLAMonitoring() {
        this.slaMonitoring.set('order_processing', {
            metric: 'processing_time',
            target: 24, // hours
            warning_threshold: 18,
            breach_threshold: 30
        });

        this.slaMonitoring.set('shipping_time', {
            metric: 'shipping_preparation',
            target: 48, // hours
            warning_threshold: 36,
            breach_threshold: 72
        });

        this.slaMonitoring.set('delivery_accuracy', {
            metric: 'on_time_delivery',
            target: 0.95, // 95%
            warning_threshold: 0.90,
            breach_threshold: 0.85
        });
    }

    async createOrder(orderData) {
        try {
            const order = {
                id: orderData.id || this.generateOrderId(),
                customer_id: orderData.customer_id,
                vendor_id: orderData.vendor_id,
                assembler_id: orderData.assembler_id,
                status: 'pending',
                priority: orderData.priority || 'normal',
                type: orderData.type || 'standard', // 'standard', 'rush', 'custom'
                items: orderData.items,
                total_amount: orderData.total_amount,
                currency: orderData.currency || 'USD',
                shipping_address: orderData.shipping_address,
                billing_address: orderData.billing_address,
                shipping_method: orderData.shipping_method,
                estimated_ship_date: orderData.estimated_ship_date,
                estimated_delivery: orderData.estimated_delivery,
                special_instructions: orderData.special_instructions,
                created_at: new Date(),
                updated_at: new Date(),
                timeline: [],
                notifications_sent: [],
                metadata: orderData.metadata || {}
            };

            // Initialize tracking timeline
            order.timeline.push({
                status: 'pending',
                timestamp: new Date(),
                message: 'Order created and pending processing',
                location: 'Order Management System',
                automated: true
            });

            // Store the order
            this.orders.set(order.id, order);

            // Start SLA monitoring
            await this.startSLAMonitoring(order.id);

            // Send initial confirmation
            await this.sendNotification(order.id, 'order_created');

            this.emit('order_created', {
                order_id: order.id,
                customer_id: order.customer_id,
                vendor_id: order.vendor_id,
                amount: order.total_amount
            });

            this.logger.info(`Order created: ${order.id}`);

            return order;

        } catch (error) {
            this.logger.error('Order creation failed:', error);
            throw error;
        }
    }

    async updateOrderStatus(orderId, newStatus, updateData = {}) {
        const order = this.orders.get(orderId);
        if (!order) {
            throw new Error(`Order ${orderId} not found`);
        }

        const statusInfo = this.orderStatuses.get(newStatus);
        if (!statusInfo) {
            throw new Error(`Invalid status: ${newStatus}`);
        }

        const previousStatus = order.status;
        order.status = newStatus;
        order.updated_at = new Date();

        // Add to timeline
        const timelineEntry = {
            status: newStatus,
            previous_status: previousStatus,
            timestamp: new Date(),
            message: updateData.message || statusInfo.customer_message,
            location: updateData.location || 'System Update',
            details: updateData.details || {},
            automated: updateData.automated !== false
        };

        order.timeline.push(timelineEntry);

        // Update tracking information if provided
        if (updateData.tracking_number) {
            order.tracking_number = updateData.tracking_number;
        }

        if (updateData.carrier) {
            order.carrier = updateData.carrier;
        }

        if (updateData.estimated_delivery) {
            order.estimated_delivery = new Date(updateData.estimated_delivery);
        }

        // Handle status-specific updates
        await this.handleStatusSpecificUpdates(order, newStatus, updateData);

        // Run automation rules
        await this.executeAutomationRules('status_change', order, {
            previous_status: previousStatus,
            new_status: newStatus
        });

        // Update SLA monitoring
        await this.updateSLAMonitoring(order);

        this.emit('order_status_updated', {
            order_id: orderId,
            previous_status: previousStatus,
            new_status: newStatus,
            customer_id: order.customer_id
        });

        this.logger.info(`Order ${orderId} status updated: ${previousStatus} → ${newStatus}`);

        return order;
    }

    async handleStatusSpecificUpdates(order, status, updateData) {
        switch (status) {
            case 'confirmed':
                order.confirmed_at = new Date();
                if (updateData.inventory_allocated) {
                    order.inventory_allocated = updateData.inventory_allocated;
                }
                break;

            case 'processing':
                order.processing_started_at = new Date();
                if (updateData.production_schedule) {
                    order.production_schedule = updateData.production_schedule;
                }
                break;

            case 'shipped':
                order.shipped_at = new Date();
                if (updateData.tracking_number && updateData.carrier) {
                    await this.enableTrackingUpdates(order.id, updateData.tracking_number, updateData.carrier);
                }
                break;

            case 'delivered':
                order.delivered_at = new Date();
                if (updateData.delivery_signature) {
                    order.delivery_signature = updateData.delivery_signature;
                }
                if (updateData.delivery_photo) {
                    order.delivery_photo = updateData.delivery_photo;
                }
                break;

            case 'exception':
                order.exception_details = updateData.exception_details || {};
                if (updateData.resolution_plan) {
                    order.resolution_plan = updateData.resolution_plan;
                }
                break;

            case 'cancelled':
                order.cancelled_at = new Date();
                order.cancellation_reason = updateData.reason || 'Customer request';
                break;
        }
    }

    async enableTrackingUpdates(orderId, trackingNumber, carrier) {
        const provider = this.trackingProviders.get(carrier);
        if (!provider) {
            this.logger.warn(`Tracking provider not found for carrier: ${carrier}`);
            return;
        }

        // Start periodic tracking updates
        const trackingInfo = {
            order_id: orderId,
            tracking_number: trackingNumber,
            carrier: carrier,
            provider: provider,
            last_update: new Date(),
            update_frequency: provider.update_frequency * 60 * 1000, // Convert to milliseconds
            next_update: new Date(Date.now() + provider.update_frequency * 60 * 1000)
        };

        // Store tracking info
        this.integrations.set(`tracking_${orderId}`, trackingInfo);

        // Schedule first update
        setTimeout(() => this.updateTrackingFromProvider(orderId), 30000); // 30 seconds delay

        this.logger.info(`Enabled tracking updates for order ${orderId} with ${carrier}`);
    }

    async updateTrackingFromProvider(orderId) {
        try {
            const trackingInfo = this.integrations.get(`tracking_${orderId}`);
            if (!trackingInfo) return;

            const order = this.orders.get(orderId);
            if (!order || ['delivered', 'cancelled', 'returned'].includes(order.status)) {
                // Stop tracking for completed orders
                this.integrations.delete(`tracking_${orderId}`);
                return;
            }

            // Fetch tracking updates from provider
            const trackingUpdate = await this.fetchTrackingFromProvider(
                trackingInfo.tracking_number,
                trackingInfo.carrier
            );

            if (trackingUpdate && trackingUpdate.events.length > 0) {
                await this.processTrackingUpdate(orderId, trackingUpdate);
            }

            // Schedule next update
            trackingInfo.last_update = new Date();
            trackingInfo.next_update = new Date(Date.now() + trackingInfo.update_frequency);
            
            setTimeout(() => this.updateTrackingFromProvider(orderId), trackingInfo.update_frequency);

        } catch (error) {
            this.logger.error(`Tracking update failed for order ${orderId}:`, error);
            
            // Retry in 5 minutes on error
            setTimeout(() => this.updateTrackingFromProvider(orderId), 5 * 60 * 1000);
        }
    }

    async fetchTrackingFromProvider(trackingNumber, carrier) {
        const provider = this.trackingProviders.get(carrier);
        if (!provider) return null;

        // Mock tracking data fetch
        const mockEvents = [
            {
                status: 'In Transit',
                location: 'Memphis, TN',
                timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
                description: 'Package departed facility'
            },
            {
                status: 'In Transit',
                location: 'Oakland, CA',
                timestamp: new Date(Date.now() - 30 * 60 * 1000),
                description: 'Package arrived at facility'
            }
        ];

        return {
            tracking_number: trackingNumber,
            carrier: carrier,
            status: 'In Transit',
            estimated_delivery: new Date(Date.now() + 24 * 60 * 60 * 1000),
            events: mockEvents,
            last_updated: new Date()
        };
    }

    async processTrackingUpdate(orderId, trackingUpdate) {
        const order = this.orders.get(orderId);
        const provider = this.trackingProviders.get(order.carrier);

        // Process each new tracking event
        for (const event of trackingUpdate.events) {
            // Map provider status to our status
            const mappedStatus = provider.status_mapping[event.status] || order.status;
            
            // Check if this is a new status
            if (mappedStatus !== order.status) {
                await this.updateOrderStatus(orderId, mappedStatus, {
                    message: event.description,
                    location: event.location,
                    automated: true,
                    tracking_event: event
                });
            } else {
                // Add timeline entry for location update
                order.timeline.push({
                    status: order.status,
                    timestamp: event.timestamp,
                    message: event.description,
                    location: event.location,
                    automated: true,
                    tracking_update: true
                });
            }
        }

        // Update estimated delivery if provided
        if (trackingUpdate.estimated_delivery) {
            order.estimated_delivery = new Date(trackingUpdate.estimated_delivery);
        }

        order.updated_at = new Date();
        this.orders.set(orderId, order);
    }

    async executeAutomationRules(trigger, order, context = {}) {
        for (const [ruleId, rule] of this.automationRules) {
            if (!rule.enabled || rule.trigger !== trigger) continue;

            // Check conditions
            const conditionsMet = await this.evaluateRuleConditions(rule.conditions, order, context);
            if (!conditionsMet) continue;

            // Execute actions
            for (const action of rule.actions) {
                try {
                    await this.executeRuleAction(action, order, context);
                } catch (error) {
                    this.logger.error(`Rule action failed for ${ruleId}:`, error);
                }
            }

            this.logger.info(`Executed automation rule: ${ruleId} for order ${order.id}`);
        }
    }

    async evaluateRuleConditions(conditions, order, context) {
        for (const [key, value] of Object.entries(conditions)) {
            switch (key) {
                case 'status_not_in':
                    if (value.includes(order.status)) return false;
                    break;
                    
                case 'new_status':
                    if (context.new_status !== value) return false;
                    break;
                    
                case 'new_status_in':
                    if (!value.includes(context.new_status)) return false;
                    break;
                    
                case 'hours_past_estimate':
                    if (!order.estimated_delivery) return false;
                    const hoursPast = (Date.now() - new Date(order.estimated_delivery).getTime()) / (1000 * 60 * 60);
                    if (hoursPast < value) return false;
                    break;
                    
                default:
                    // Custom condition evaluation could be added here
                    break;
            }
        }
        return true;
    }

    async executeRuleAction(action, order, context) {
        switch (action.type) {
            case 'send_notification':
                await this.sendNotification(order.id, action.template, action.data);
                break;
                
            case 'update_status':
                await this.updateOrderStatus(order.id, action.new_status, {
                    message: action.message || `Status updated by automation rule`,
                    automated: true
                });
                break;
                
            case 'escalate_to_support':
                await this.createSupportTicket(order, action.priority || 'medium');
                break;
                
            case 'schedule_feedback_request':
                await this.scheduleFeedbackRequest(order.id, action.delay_hours || 24);
                break;
                
            case 'update_vendor_performance':
                await this.updateVendorPerformance(order.vendor_id, action.metric);
                break;
                
            case 'create_support_ticket':
                await this.createSupportTicket(order, action.priority || 'low');
                break;
                
            case 'attempt_redelivery':
                await this.attemptRedelivery(order.id, action.max_attempts || 1);
                break;
                
            case 'update_delivery_estimate':
                await this.updateDeliveryEstimate(order.id);
                break;
        }
    }

    async sendNotification(orderId, template, additionalData = {}) {
        const order = this.orders.get(orderId);
        if (!order) return;

        const notification = {
            id: this.generateNotificationId(),
            order_id: orderId,
            customer_id: order.customer_id,
            template,
            timestamp: new Date(),
            channels: ['email'], // Could be email, sms, push
            data: {
                ...additionalData,
                order_id: orderId,
                tracking_number: order.tracking_number,
                status: order.status,
                estimated_delivery: order.estimated_delivery
            },
            status: 'sent'
        };

        this.notifications.set(notification.id, notification);
        
        // Add to order's notification history
        order.notifications_sent.push(notification.id);

        this.emit('notification_sent', {
            notification_id: notification.id,
            order_id: orderId,
            customer_id: order.customer_id,
            template
        });

        this.logger.info(`Notification sent: ${template} for order ${orderId}`);
    }

    async createSupportTicket(order, priority = 'medium') {
        const ticket = {
            id: this.generateTicketId(),
            order_id: order.id,
            customer_id: order.customer_id,
            vendor_id: order.vendor_id,
            priority,
            subject: `Order Issue - ${order.id}`,
            description: `Automated ticket for order ${order.id} with status ${order.status}`,
            status: 'open',
            created_at: new Date(),
            assigned_to: null
        };

        // In a real system, this would create a ticket in the support system
        this.logger.info(`Support ticket created: ${ticket.id} for order ${order.id}`);
        
        return ticket;
    }

    async scheduleFeedbackRequest(orderId, delayHours) {
        setTimeout(async () => {
            await this.sendNotification(orderId, 'feedback_request', {
                delay_reason: `Scheduled ${delayHours} hours after delivery`
            });
        }, delayHours * 60 * 60 * 1000);
    }

    async updateVendorPerformance(vendorId, metric) {
        // Mock vendor performance update
        this.logger.info(`Updated vendor ${vendorId} performance metric: ${metric}`);
    }

    async attemptRedelivery(orderId, maxAttempts) {
        const order = this.orders.get(orderId);
        if (!order) return;

        const attempts = order.redelivery_attempts || 0;
        if (attempts >= maxAttempts) {
            await this.updateOrderStatus(orderId, 'returned', {
                message: `Maximum redelivery attempts (${maxAttempts}) exceeded`,
                automated: true
            });
            return;
        }

        order.redelivery_attempts = attempts + 1;
        await this.updateOrderStatus(orderId, 'in_transit', {
            message: `Redelivery attempt ${order.redelivery_attempts}/${maxAttempts}`,
            automated: true
        });
    }

    async updateDeliveryEstimate(orderId) {
        const order = this.orders.get(orderId);
        if (!order || !order.tracking_number) return;

        // Fetch updated estimate from carrier
        const trackingUpdate = await this.fetchTrackingFromProvider(order.tracking_number, order.carrier);
        
        if (trackingUpdate && trackingUpdate.estimated_delivery) {
            const oldEstimate = order.estimated_delivery;
            order.estimated_delivery = new Date(trackingUpdate.estimated_delivery);
            
            // Notify if estimate changed significantly
            if (oldEstimate) {
                const timeDiff = Math.abs(new Date(order.estimated_delivery) - new Date(oldEstimate));
                const hoursDiff = timeDiff / (1000 * 60 * 60);
                
                if (hoursDiff > 4) { // More than 4 hours difference
                    await this.sendNotification(orderId, 'delivery_estimate_updated', {
                        old_estimate: oldEstimate,
                        new_estimate: order.estimated_delivery
                    });
                }
            }
        }
    }

    async startSLAMonitoring(orderId) {
        const order = this.orders.get(orderId);
        if (!order) return;

        const slaMonitor = {
            order_id: orderId,
            created_at: new Date(),
            milestones: {},
            alerts: []
        };

        // Set up milestone monitoring
        for (const [metricId, metric] of this.slaMonitoring) {
            slaMonitor.milestones[metricId] = {
                target: metric.target,
                warning_threshold: metric.warning_threshold,
                breach_threshold: metric.breach_threshold,
                status: 'on_track',
                started_at: new Date()
            };
        }

        this.slaMonitoring.set(`monitor_${orderId}`, slaMonitor);
    }

    async updateSLAMonitoring(order) {
        const monitor = this.slaMonitoring.get(`monitor_${order.id}`);
        if (!monitor) return;

        const now = new Date();
        
        // Check processing time SLA
        if (order.status === 'processing' && !monitor.milestones.order_processing.completed) {
            const hoursInProcessing = (now - new Date(order.created_at)) / (1000 * 60 * 60);
            const processingMetric = monitor.milestones.order_processing;
            
            if (hoursInProcessing > processingMetric.breach_threshold) {
                processingMetric.status = 'breached';
                await this.handleSLABreach(order, 'order_processing', hoursInProcessing);
            } else if (hoursInProcessing > processingMetric.warning_threshold) {
                processingMetric.status = 'warning';
                await this.handleSLAWarning(order, 'order_processing', hoursInProcessing);
            }
        }

        // Mark processing milestone as completed when shipped
        if (order.status === 'shipped' && !monitor.milestones.order_processing.completed) {
            monitor.milestones.order_processing.completed = true;
            monitor.milestones.order_processing.completed_at = now;
            monitor.milestones.order_processing.actual_duration = 
                (now - new Date(order.created_at)) / (1000 * 60 * 60);
        }

        // Check delivery accuracy
        if (order.status === 'delivered') {
            const deliveryMetric = monitor.milestones.delivery_accuracy;
            const onTime = new Date(order.delivered_at) <= new Date(order.estimated_delivery);
            
            deliveryMetric.completed = true;
            deliveryMetric.completed_at = now;
            deliveryMetric.on_time = onTime;
            
            if (!onTime) {
                await this.handleDeliveryDelay(order);
            }
        }

        this.slaMonitoring.set(`monitor_${order.id}`, monitor);
    }

    async handleSLABreach(order, metric, actualValue) {
        await this.sendNotification(order.id, 'sla_breach', {
            metric,
            target: this.slaMonitoring.get(metric)?.target,
            actual: actualValue
        });

        await this.createSupportTicket(order, 'high');
        
        this.logger.warn(`SLA breach for order ${order.id}: ${metric} = ${actualValue}`);
    }

    async handleSLAWarning(order, metric, actualValue) {
        await this.sendNotification(order.id, 'sla_warning', {
            metric,
            warning_threshold: this.slaMonitoring.get(metric)?.warning_threshold,
            actual: actualValue
        });
        
        this.logger.warn(`SLA warning for order ${order.id}: ${metric} = ${actualValue}`);
    }

    async handleDeliveryDelay(order) {
        const delayHours = (new Date(order.delivered_at) - new Date(order.estimated_delivery)) / (1000 * 60 * 60);
        
        await this.sendNotification(order.id, 'delivery_delay_apology', {
            delay_hours: Math.round(delayHours)
        });

        // Update vendor performance metrics
        await this.updateVendorPerformance(order.vendor_id, 'late_delivery');
    }

    async getOrderTracking(orderId) {
        const order = this.orders.get(orderId);
        if (!order) {
            throw new Error(`Order ${orderId} not found`);
        }

        const provider = order.carrier ? this.trackingProviders.get(order.carrier) : null;
        
        return {
            order_id: orderId,
            status: order.status,
            current_location: this.getCurrentLocation(order),
            estimated_delivery: order.estimated_delivery,
            tracking_number: order.tracking_number,
            carrier: order.carrier,
            tracking_url: provider && order.tracking_number ? 
                provider.tracking_url_template.replace('{tracking_number}', order.tracking_number) : null,
            timeline: order.timeline,
            last_update: order.updated_at,
            delivery_attempts: order.redelivery_attempts || 0,
            special_instructions: order.special_instructions,
            notifications_sent: order.notifications_sent.length,
            sla_status: await this.getSLAStatus(orderId)
        };
    }

    getCurrentLocation(order) {
        // Find most recent location from timeline
        const locationEvents = order.timeline.filter(event => event.location);
        return locationEvents.length > 0 ? 
            locationEvents[locationEvents.length - 1].location : 
            'Unknown';
    }

    async getSLAStatus(orderId) {
        const monitor = this.slaMonitoring.get(`monitor_${orderId}`);
        if (!monitor) return null;

        const slaStatus = {
            overall_status: 'on_track',
            milestones: {}
        };

        for (const [metricId, milestone] of Object.entries(monitor.milestones)) {
            slaStatus.milestones[metricId] = {
                status: milestone.status,
                target: milestone.target,
                completed: milestone.completed || false
            };

            if (milestone.status === 'breached') {
                slaStatus.overall_status = 'breached';
            } else if (milestone.status === 'warning' && slaStatus.overall_status === 'on_track') {
                slaStatus.overall_status = 'warning';
            }
        }

        return slaStatus;
    }

    async getOrderAnalytics(filters = {}) {
        const analytics = {
            total_orders: this.orders.size,
            status_distribution: {},
            average_processing_time: 0,
            on_time_delivery_rate: 0,
            carrier_performance: {},
            sla_compliance: {},
            generated_at: new Date()
        };

        // Filter orders
        let orders = Array.from(this.orders.values());
        
        if (filters.date_range) {
            const startDate = new Date(filters.date_range.start);
            const endDate = new Date(filters.date_range.end);
            orders = orders.filter(order => {
                const orderDate = new Date(order.created_at);
                return orderDate >= startDate && orderDate <= endDate;
            });
        }

        if (filters.vendor_id) {
            orders = orders.filter(order => order.vendor_id === filters.vendor_id);
        }

        if (filters.customer_id) {
            orders = orders.filter(order => order.customer_id === filters.customer_id);
        }

        // Calculate analytics
        analytics.total_orders = orders.length;

        // Status distribution
        orders.forEach(order => {
            analytics.status_distribution[order.status] = 
                (analytics.status_distribution[order.status] || 0) + 1;
        });

        // Processing time
        const processedOrders = orders.filter(order => order.shipped_at);
        if (processedOrders.length > 0) {
            const totalProcessingTime = processedOrders.reduce((sum, order) => {
                return sum + (new Date(order.shipped_at) - new Date(order.created_at));
            }, 0);
            
            analytics.average_processing_time = 
                totalProcessingTime / processedOrders.length / (1000 * 60 * 60); // Convert to hours
        }

        // On-time delivery rate
        const deliveredOrders = orders.filter(order => order.status === 'delivered');
        if (deliveredOrders.length > 0) {
            const onTimeDeliveries = deliveredOrders.filter(order => 
                new Date(order.delivered_at) <= new Date(order.estimated_delivery)
            );
            
            analytics.on_time_delivery_rate = onTimeDeliveries.length / deliveredOrders.length;
        }

        // Carrier performance
        const ordersByCarrier = orders.filter(order => order.carrier)
            .reduce((acc, order) => {
                if (!acc[order.carrier]) acc[order.carrier] = [];
                acc[order.carrier].push(order);
                return acc;
            }, {});

        for (const [carrier, carrierOrders] of Object.entries(ordersByCarrier)) {
            const delivered = carrierOrders.filter(order => order.status === 'delivered');
            const onTime = delivered.filter(order => 
                new Date(order.delivered_at) <= new Date(order.estimated_delivery)
            );

            analytics.carrier_performance[carrier] = {
                total_orders: carrierOrders.length,
                delivered_orders: delivered.length,
                on_time_rate: delivered.length > 0 ? onTime.length / delivered.length : 0,
                average_transit_time: this.calculateAverageTransitTime(delivered)
            };
        }

        return analytics;
    }

    calculateAverageTransitTime(orders) {
        if (orders.length === 0) return 0;
        
        const totalTransitTime = orders.reduce((sum, order) => {
            if (order.shipped_at && order.delivered_at) {
                return sum + (new Date(order.delivered_at) - new Date(order.shipped_at));
            }
            return sum;
        }, 0);

        return totalTransitTime / orders.length / (1000 * 60 * 60 * 24); // Convert to days
    }

    // Utility methods
    generateOrderId() {
        return `order_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateNotificationId() {
        return `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateTicketId() {
        return `ticket_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    async getOrder(orderId) {
        const order = this.orders.get(orderId);
        if (!order) {
            throw new Error(`Order ${orderId} not found`);
        }
        return order;
    }

    async searchOrders(searchCriteria) {
        let orders = Array.from(this.orders.values());

        if (searchCriteria.customer_id) {
            orders = orders.filter(order => order.customer_id === searchCriteria.customer_id);
        }

        if (searchCriteria.vendor_id) {
            orders = orders.filter(order => order.vendor_id === searchCriteria.vendor_id);
        }

        if (searchCriteria.status) {
            orders = orders.filter(order => order.status === searchCriteria.status);
        }

        if (searchCriteria.tracking_number) {
            orders = orders.filter(order => 
                order.tracking_number && 
                order.tracking_number.includes(searchCriteria.tracking_number)
            );
        }

        return orders;
    }
}