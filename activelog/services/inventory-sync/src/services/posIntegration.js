const EventEmitter = require('events');
const axios = require('axios');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');

class POSIntegrationManager extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.connectedSystems = new Map();
        this.transactionQueue = [];
        this.syncStatus = new Map();
        this.retryAttempts = new Map();
        
        this.setupEventHandlers();
        this.startTransactionProcessor();
    }

    setupEventHandlers() {
        this.on('transaction_completed', this.handleTransactionCompleted.bind(this));
        this.on('inventory_updated', this.handleInventoryUpdate.bind(this));
        this.on('sync_failed', this.handleSyncFailure.bind(this));
    }

    async registerPOSSystem(systemConfig) {
        try {
            const systemId = uuidv4();
            const posSystem = {
                id: systemId,
                type: systemConfig.type,
                locationId: systemConfig.locationId,
                name: systemConfig.name,
                endpoint: systemConfig.endpoint,
                credentials: this.encryptCredentials(systemConfig.credentials),
                settings: {
                    syncInterval: systemConfig.syncInterval || 30000,
                    autoInventoryUpdate: systemConfig.autoInventoryUpdate !== false,
                    taxSettings: systemConfig.taxSettings || {},
                    discountRules: systemConfig.discountRules || []
                },
                status: 'pending_connection',
                registeredAt: new Date(),
                lastSync: null,
                metrics: {
                    totalTransactions: 0,
                    totalSales: 0,
                    syncErrors: 0,
                    lastError: null
                }
            };

            await this.testConnection(posSystem);
            posSystem.status = 'connected';
            
            this.connectedSystems.set(systemId, posSystem);
            await this.redis.hset('pos_systems', systemId, JSON.stringify(posSystem));
            
            this.logger.info('POS system registered successfully', { systemId, type: posSystem.type, locationId: posSystem.locationId });
            
            this.io.to(`location_${posSystem.locationId}`).emit('pos_system_connected', {
                systemId,
                type: posSystem.type,
                name: posSystem.name,
                status: 'connected'
            });

            return { success: true, systemId, system: this.sanitizeSystemData(posSystem) };
        } catch (error) {
            this.logger.error('Failed to register POS system', { error: error.message, config: systemConfig });
            throw new Error(`POS registration failed: ${error.message}`);
        }
    }

    async processTransaction(transactionData) {
        try {
            const transactionId = uuidv4();
            const transaction = {
                id: transactionId,
                posSystemId: transactionData.posSystemId,
                locationId: transactionData.locationId,
                type: transactionData.type || 'sale',
                items: transactionData.items,
                customer: transactionData.customer || null,
                payment: {
                    method: transactionData.payment.method,
                    amount: transactionData.payment.amount,
                    currency: transactionData.payment.currency || 'USD',
                    reference: transactionData.payment.reference
                },
                tax: transactionData.tax || 0,
                discount: transactionData.discount || 0,
                total: transactionData.total,
                timestamp: new Date(),
                status: 'processing',
                metadata: transactionData.metadata || {}
            };

            await this.redis.hset('pos_transactions', transactionId, JSON.stringify(transaction));
            
            this.transactionQueue.push(transaction);
            
            this.logger.info('Transaction queued for processing', { transactionId, posSystemId: transaction.posSystemId });
            
            return { success: true, transactionId, status: 'queued' };
        } catch (error) {
            this.logger.error('Failed to process transaction', { error: error.message, transactionData });
            throw new Error(`Transaction processing failed: ${error.message}`);
        }
    }

    async processTransactionQueue() {
        if (this.transactionQueue.length === 0) return;
        
        const transaction = this.transactionQueue.shift();
        
        try {
            await this.validateTransaction(transaction);
            await this.updateInventoryFromTransaction(transaction);
            await this.recordSale(transaction);
            
            transaction.status = 'completed';
            transaction.completedAt = new Date();
            
            await this.redis.hset('pos_transactions', transaction.id, JSON.stringify(transaction));
            
            const posSystem = this.connectedSystems.get(transaction.posSystemId);
            if (posSystem) {
                posSystem.metrics.totalTransactions++;
                posSystem.metrics.totalSales += transaction.total;
                await this.redis.hset('pos_systems', transaction.posSystemId, JSON.stringify(posSystem));
            }
            
            this.emit('transaction_completed', transaction);
            
            this.io.to(`location_${transaction.locationId}`).emit('transaction_completed', {
                transactionId: transaction.id,
                total: transaction.total,
                items: transaction.items.length,
                timestamp: transaction.timestamp
            });
            
        } catch (error) {
            transaction.status = 'failed';
            transaction.error = error.message;
            transaction.failedAt = new Date();
            
            await this.redis.hset('pos_transactions', transaction.id, JSON.stringify(transaction));
            
            this.logger.error('Transaction processing failed', { 
                transactionId: transaction.id, 
                error: error.message 
            });
            
            this.handleTransactionFailure(transaction, error);
        }
    }

    async updateInventoryFromTransaction(transaction) {
        const inventoryUpdates = [];
        
        for (const item of transaction.items) {
            const updateData = {
                locationId: transaction.locationId,
                itemId: item.itemId || item.sku,
                change: {
                    type: transaction.type === 'sale' ? 'sale' : transaction.type,
                    quantity: -(item.quantity), // Negative for sales
                    reference: `POS-${transaction.id}`,
                    timestamp: transaction.timestamp,
                    unitPrice: item.price,
                    total: item.price * item.quantity
                },
                source: 'pos_integration',
                posSystemId: transaction.posSystemId
            };
            
            inventoryUpdates.push(updateData);
            
            await this.redis.lpush(
                `inventory_updates:${transaction.locationId}`, 
                JSON.stringify(updateData)
            );
        }
        
        this.emit('inventory_updated', {
            locationId: transaction.locationId,
            updates: inventoryUpdates,
            transactionId: transaction.id
        });
        
        return inventoryUpdates;
    }

    async recordSale(transaction) {
        const saleRecord = {
            id: transaction.id,
            posSystemId: transaction.posSystemId,
            locationId: transaction.locationId,
            customerId: transaction.customer?.id || null,
            items: transaction.items.map(item => ({
                itemId: item.itemId || item.sku,
                name: item.name,
                quantity: item.quantity,
                unitPrice: item.price,
                total: item.price * item.quantity,
                category: item.category || null
            })),
            subtotal: transaction.total - transaction.tax + transaction.discount,
            tax: transaction.tax,
            discount: transaction.discount,
            total: transaction.total,
            paymentMethod: transaction.payment.method,
            timestamp: transaction.timestamp,
            metadata: transaction.metadata
        };
        
        await this.redis.hset('sales_records', transaction.id, JSON.stringify(saleRecord));
        
        const dailySalesKey = `daily_sales:${transaction.locationId}:${this.getDateKey(transaction.timestamp)}`;
        await this.redis.hincrby(dailySalesKey, 'total_amount', Math.round(transaction.total * 100));
        await this.redis.hincrby(dailySalesKey, 'transaction_count', 1);
        await this.redis.expire(dailySalesKey, 86400 * 90); // Keep for 90 days
        
        return saleRecord;
    }

    async syncWithPOSSystem(systemId) {
        const posSystem = this.connectedSystems.get(systemId);
        if (!posSystem) {
            throw new Error(`POS system ${systemId} not found`);
        }
        
        try {
            this.syncStatus.set(systemId, 'syncing');
            
            const syncData = await this.fetchPOSData(posSystem);
            
            await this.processSyncData(posSystem, syncData);
            
            posSystem.lastSync = new Date();
            posSystem.status = 'connected';
            this.syncStatus.set(systemId, 'completed');
            
            await this.redis.hset('pos_systems', systemId, JSON.stringify(posSystem));
            
            this.logger.info('POS sync completed', { systemId, itemsCount: syncData.items?.length || 0 });
            
            return { success: true, syncedAt: posSystem.lastSync, itemsCount: syncData.items?.length || 0 };
            
        } catch (error) {
            posSystem.metrics.syncErrors++;
            posSystem.metrics.lastError = error.message;
            this.syncStatus.set(systemId, 'failed');
            
            await this.redis.hset('pos_systems', systemId, JSON.stringify(posSystem));
            
            this.emit('sync_failed', { systemId, error: error.message });
            
            this.logger.error('POS sync failed', { systemId, error: error.message });
            throw error;
        }
    }

    async fetchPOSData(posSystem) {
        const credentials = this.decryptCredentials(posSystem.credentials);
        
        switch (posSystem.type) {
            case 'square':
                return await this.fetchSquareData(posSystem, credentials);
            case 'stripe':
                return await this.fetchStripeData(posSystem, credentials);
            case 'shopify_pos':
                return await this.fetchShopifyPOSData(posSystem, credentials);
            case 'clover':
                return await this.fetchCloverData(posSystem, credentials);
            default:
                return await this.fetchGenericPOSData(posSystem, credentials);
        }
    }

    async fetchSquareData(posSystem, credentials) {
        const headers = {
            'Authorization': `Bearer ${credentials.accessToken}`,
            'Square-Version': '2023-10-18',
            'Content-Type': 'application/json'
        };
        
        const [itemsResponse, paymentsResponse] = await Promise.all([
            axios.get(`${posSystem.endpoint}/v2/catalog/list?types=ITEM`, { headers }),
            axios.get(`${posSystem.endpoint}/v2/payments?location_id=${posSystem.locationId}&limit=100`, { headers })
        ]);
        
        return {
            items: itemsResponse.data.objects || [],
            payments: paymentsResponse.data.payments || [],
            type: 'square'
        };
    }

    async fetchStripeData(posSystem, credentials) {
        const headers = {
            'Authorization': `Bearer ${credentials.secretKey}`,
            'Content-Type': 'application/json'
        };
        
        const [productsResponse, paymentsResponse] = await Promise.all([
            axios.get('https://api.stripe.com/v1/products?limit=100', { headers }),
            axios.get('https://api.stripe.com/v1/payment_intents?limit=100', { headers })
        ]);
        
        return {
            items: productsResponse.data.data || [],
            payments: paymentsResponse.data.data || [],
            type: 'stripe'
        };
    }

    async fetchGenericPOSData(posSystem, credentials) {
        const headers = {
            'Authorization': credentials.authHeader || `Bearer ${credentials.token}`,
            'Content-Type': 'application/json',
            ...credentials.customHeaders
        };
        
        const response = await axios.get(`${posSystem.endpoint}/api/sync`, { headers });
        return response.data;
    }

    async getTransactionHistory(locationId, options = {}) {
        const { startDate, endDate, posSystemId, limit = 100, offset = 0 } = options;
        
        const transactionKeys = await this.redis.hkeys('pos_transactions');
        const transactions = [];
        
        for (const key of transactionKeys.slice(offset, offset + limit)) {
            const transactionData = await this.redis.hget('pos_transactions', key);
            if (transactionData) {
                const transaction = JSON.parse(transactionData);
                
                if (transaction.locationId === locationId) {
                    if (posSystemId && transaction.posSystemId !== posSystemId) continue;
                    if (startDate && new Date(transaction.timestamp) < new Date(startDate)) continue;
                    if (endDate && new Date(transaction.timestamp) > new Date(endDate)) continue;
                    
                    transactions.push(transaction);
                }
            }
        }
        
        return transactions.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }

    async getSalesAnalytics(locationId, dateRange) {
        const analytics = {
            totalSales: 0,
            totalTransactions: 0,
            averageTransaction: 0,
            topItems: [],
            salesByHour: new Array(24).fill(0),
            salesByDay: {},
            paymentMethods: {}
        };
        
        const transactions = await this.getTransactionHistory(locationId, dateRange);
        
        const itemSales = new Map();
        
        for (const transaction of transactions) {
            analytics.totalSales += transaction.total;
            analytics.totalTransactions++;
            
            const hour = new Date(transaction.timestamp).getHours();
            analytics.salesByHour[hour] += transaction.total;
            
            const dayKey = this.getDateKey(transaction.timestamp);
            analytics.salesByDay[dayKey] = (analytics.salesByDay[dayKey] || 0) + transaction.total;
            
            analytics.paymentMethods[transaction.payment.method] = 
                (analytics.paymentMethods[transaction.payment.method] || 0) + 1;
            
            for (const item of transaction.items) {
                const itemId = item.itemId || item.sku;
                const current = itemSales.get(itemId) || { name: item.name, quantity: 0, revenue: 0 };
                current.quantity += item.quantity;
                current.revenue += item.price * item.quantity;
                itemSales.set(itemId, current);
            }
        }
        
        analytics.averageTransaction = analytics.totalTransactions > 0 
            ? analytics.totalSales / analytics.totalTransactions 
            : 0;
        
        analytics.topItems = Array.from(itemSales.entries())
            .map(([itemId, data]) => ({ itemId, ...data }))
            .sort((a, b) => b.revenue - a.revenue)
            .slice(0, 10);
        
        return analytics;
    }

    async validateTransaction(transaction) {
        if (!transaction.items || transaction.items.length === 0) {
            throw new Error('Transaction must contain at least one item');
        }
        
        if (!transaction.payment || !transaction.payment.amount) {
            throw new Error('Transaction must include payment information');
        }
        
        if (transaction.total <= 0) {
            throw new Error('Transaction total must be greater than zero');
        }
        
        const posSystem = this.connectedSystems.get(transaction.posSystemId);
        if (!posSystem) {
            throw new Error(`POS system ${transaction.posSystemId} not found or disconnected`);
        }
        
        return true;
    }

    async testConnection(posSystem) {
        try {
            const credentials = this.decryptCredentials(posSystem.credentials);
            
            switch (posSystem.type) {
                case 'square':
                    await this.testSquareConnection(posSystem, credentials);
                    break;
                case 'stripe':
                    await this.testStripeConnection(posSystem, credentials);
                    break;
                default:
                    await this.testGenericConnection(posSystem, credentials);
            }
            
            return true;
        } catch (error) {
            throw new Error(`Connection test failed: ${error.message}`);
        }
    }

    async testSquareConnection(posSystem, credentials) {
        const response = await axios.get(`${posSystem.endpoint}/v2/locations`, {
            headers: {
                'Authorization': `Bearer ${credentials.accessToken}`,
                'Square-Version': '2023-10-18'
            }
        });
        
        if (!response.data.locations) {
            throw new Error('Invalid Square API response');
        }
    }

    async testStripeConnection(posSystem, credentials) {
        const response = await axios.get('https://api.stripe.com/v1/account', {
            headers: {
                'Authorization': `Bearer ${credentials.secretKey}`
            }
        });
        
        if (!response.data.id) {
            throw new Error('Invalid Stripe API response');
        }
    }

    encryptCredentials(credentials) {
        const key = process.env.ENCRYPTION_KEY || 'default-key-change-in-production';
        const cipher = crypto.createCipher('aes256', key);
        let encrypted = cipher.update(JSON.stringify(credentials), 'utf8', 'hex');
        encrypted += cipher.final('hex');
        return encrypted;
    }

    decryptCredentials(encryptedCredentials) {
        const key = process.env.ENCRYPTION_KEY || 'default-key-change-in-production';
        const decipher = crypto.createDecipher('aes256', key);
        let decrypted = decipher.update(encryptedCredentials, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        return JSON.parse(decrypted);
    }

    startTransactionProcessor() {
        setInterval(async () => {
            try {
                await this.processTransactionQueue();
            } catch (error) {
                this.logger.error('Transaction processor error', { error: error.message });
            }
        }, 1000);
    }

    handleTransactionCompleted(transaction) {
        this.logger.info('Transaction completed successfully', { 
            transactionId: transaction.id, 
            total: transaction.total 
        });
    }

    handleInventoryUpdate(updateData) {
        this.io.to(`location_${updateData.locationId}`).emit('inventory_updated_from_pos', {
            updates: updateData.updates,
            transactionId: updateData.transactionId
        });
    }

    handleTransactionFailure(transaction, error) {
        const retryKey = transaction.id;
        const currentRetries = this.retryAttempts.get(retryKey) || 0;
        
        if (currentRetries < 3) {
            this.retryAttempts.set(retryKey, currentRetries + 1);
            setTimeout(() => {
                this.transactionQueue.unshift(transaction);
            }, Math.pow(2, currentRetries) * 1000);
            
            this.logger.warn('Retrying failed transaction', { 
                transactionId: transaction.id, 
                attempt: currentRetries + 1 
            });
        } else {
            this.logger.error('Transaction failed after max retries', { 
                transactionId: transaction.id, 
                error: error.message 
            });
            
            this.io.to(`location_${transaction.locationId}`).emit('transaction_failed', {
                transactionId: transaction.id,
                error: error.message
            });
        }
    }

    sanitizeSystemData(posSystem) {
        const { credentials, ...sanitized } = posSystem;
        return sanitized;
    }

    getDateKey(date) {
        return new Date(date).toISOString().split('T')[0];
    }

    async getSystemStatus() {
        const systems = Array.from(this.connectedSystems.values()).map(system => ({
            id: system.id,
            type: system.type,
            name: system.name,
            locationId: system.locationId,
            status: system.status,
            lastSync: system.lastSync,
            metrics: system.metrics
        }));
        
        return {
            connectedSystems: systems.length,
            queuedTransactions: this.transactionQueue.length,
            systems
        };
    }
}

module.exports = POSIntegrationManager;