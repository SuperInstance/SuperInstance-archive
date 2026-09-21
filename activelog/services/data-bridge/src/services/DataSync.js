const { EventEmitter } = require('events');
const crypto = require('crypto');
const diff = require('diff');

class DataSync extends EventEmitter {
    constructor(options = {}) {
        super();
        this.services = new Map();
        this.syncRules = new Map();
        this.syncQueue = [];
        this.activeSyncs = new Map();
        this.syncHistory = [];
        this.conflictResolver = options.conflictResolver;
        this.batchSize = options.batchSize || 100;
        this.maxRetries = options.maxRetries || 3;
        this.syncInterval = options.syncInterval || 30000; // 30 seconds
        this.isRunning = false;
        
        this.setupSync();
    }

    registerService(serviceName, config) {
        const serviceInfo = {
            name: serviceName,
            endpoint: config.endpoint,
            apiKey: config.apiKey,
            syncEnabled: config.syncEnabled !== false,
            lastSync: null,
            syncStrategy: config.syncStrategy || 'bidirectional',
            entityTypes: config.entityTypes || [],
            transformRules: config.transformRules || {},
            rateLimits: config.rateLimits || { requests: 1000, window: 3600000 },
            priority: config.priority || 5,
            metadata: config.metadata || {},
            registeredAt: new Date()
        };

        this.services.set(serviceName, serviceInfo);
        this.emit('service:registered', serviceInfo);
        return this;
    }

    createSyncRule(ruleId, config) {
        const rule = {
            id: ruleId,
            sourceService: config.sourceService,
            targetServices: config.targetServices || [],
            entityType: config.entityType,
            syncMode: config.syncMode || 'realtime', // realtime, batch, scheduled
            frequency: config.frequency || 300000, // 5 minutes
            filters: config.filters || {},
            transformations: config.transformations || [],
            conflictResolution: config.conflictResolution || 'timestamp',
            enabled: config.enabled !== false,
            conditions: config.conditions || {},
            webhook: config.webhook,
            createdAt: new Date(),
            lastExecuted: null,
            successCount: 0,
            errorCount: 0
        };

        this.syncRules.set(ruleId, rule);
        this.emit('sync-rule:created', rule);
        return rule;
    }

    async syncEntity(entityType, entityId, sourceService, options = {}) {
        const syncId = crypto.randomUUID();
        const syncInfo = {
            id: syncId,
            entityType,
            entityId,
            sourceService,
            targetServices: options.targetServices || this.getTargetServices(sourceService, entityType),
            status: 'pending',
            startTime: new Date(),
            retryCount: 0,
            errors: [],
            results: {}
        };

        this.activeSyncs.set(syncId, syncInfo);

        try {
            // Fetch entity from source service
            const sourceEntity = await this.fetchEntity(sourceService, entityType, entityId);
            if (!sourceEntity) {
                throw new Error(`Entity not found: ${entityType}/${entityId} in ${sourceService}`);
            }

            syncInfo.sourceData = sourceEntity;
            syncInfo.status = 'syncing';

            // Sync to each target service
            const syncPromises = syncInfo.targetServices.map(async (targetService) => {
                return this.syncToService(syncId, sourceEntity, targetService, options);
            });

            const results = await Promise.allSettled(syncPromises);
            syncInfo.results = this.processSyncResults(results, syncInfo.targetServices);
            
            // Determine overall sync status
            const hasFailures = results.some(r => r.status === 'rejected');
            syncInfo.status = hasFailures ? 'partial' : 'completed';
            syncInfo.endTime = new Date();

            this.syncHistory.push({
                ...syncInfo,
                duration: syncInfo.endTime - syncInfo.startTime
            });

            this.emit('sync:completed', syncInfo);
            return syncInfo;

        } catch (error) {
            syncInfo.status = 'failed';
            syncInfo.errors.push(error.message);
            syncInfo.endTime = new Date();
            
            this.emit('sync:failed', syncInfo);
            throw error;
        } finally {
            this.activeSyncs.delete(syncId);
        }
    }

    async syncToService(syncId, sourceEntity, targetService, options = {}) {
        const service = this.services.get(targetService);
        if (!service) {
            throw new Error(`Target service not found: ${targetService}`);
        }

        try {
            // Check if entity exists in target service
            const existingEntity = await this.fetchEntity(
                targetService, 
                sourceEntity.type, 
                sourceEntity.id
            ).catch(() => null);

            let result;
            if (existingEntity) {
                // Handle conflict if entity exists
                result = await this.handleConflict(
                    sourceEntity,
                    existingEntity,
                    targetService,
                    options
                );
            } else {
                // Create new entity in target service
                result = await this.createEntity(targetService, sourceEntity);
            }

            return {
                service: targetService,
                action: existingEntity ? 'updated' : 'created',
                success: true,
                result
            };

        } catch (error) {
            this.emit('sync:service-error', {
                syncId,
                service: targetService,
                error: error.message,
                entity: sourceEntity
            });

            return {
                service: targetService,
                success: false,
                error: error.message
            };
        }
    }

    async handleConflict(sourceEntity, targetEntity, targetService, options = {}) {
        const conflictInfo = {
            sourceEntity,
            targetEntity,
            targetService,
            detectedAt: new Date(),
            conflictType: this.detectConflictType(sourceEntity, targetEntity)
        };

        this.emit('conflict:detected', conflictInfo);

        // Use configured conflict resolution strategy
        const service = this.services.get(targetService);
        const strategy = options.conflictResolution || 
                        service.conflictResolution || 
                        'timestamp';

        switch (strategy) {
            case 'source-wins':
                return await this.updateEntity(targetService, sourceEntity);
            
            case 'target-wins':
                return targetEntity;
            
            case 'timestamp':
                const sourceTime = new Date(sourceEntity.updatedAt);
                const targetTime = new Date(targetEntity.updatedAt);
                if (sourceTime > targetTime) {
                    return await this.updateEntity(targetService, sourceEntity);
                }
                return targetEntity;
            
            case 'merge':
                const merged = this.mergeEntities(sourceEntity, targetEntity);
                return await this.updateEntity(targetService, merged);
            
            case 'manual':
                return await this.escalateConflict(conflictInfo);
            
            case 'custom':
                if (this.conflictResolver) {
                    return await this.conflictResolver(conflictInfo);
                }
                throw new Error('Custom conflict resolver not configured');
            
            default:
                throw new Error(`Unknown conflict resolution strategy: ${strategy}`);
        }
    }

    detectConflictType(sourceEntity, targetEntity) {
        const sourceMod = new Date(sourceEntity.updatedAt);
        const targetMod = new Date(targetEntity.updatedAt);
        
        if (Math.abs(sourceMod - targetMod) < 1000) {
            return 'concurrent';
        }
        
        if (sourceMod > targetMod) {
            return 'source-newer';
        } else if (targetMod > sourceMod) {
            return 'target-newer';
        }
        
        return 'unknown';
    }

    mergeEntities(sourceEntity, targetEntity) {
        const merged = { ...targetEntity };
        
        // Merge non-system fields
        const systemFields = ['id', 'createdAt', 'version'];
        for (const [key, value] of Object.entries(sourceEntity)) {
            if (!systemFields.includes(key)) {
                if (value !== null && value !== undefined) {
                    merged[key] = value;
                }
            }
        }
        
        // Update system fields appropriately
        merged.updatedAt = new Date().toISOString();
        merged.version = this.incrementVersion(targetEntity.version);
        
        return merged;
    }

    incrementVersion(version) {
        if (!version) return '1.0.1';
        const parts = version.split('.').map(Number);
        parts[2] = (parts[2] || 0) + 1;
        return parts.join('.');
    }

    async batchSync(entityType, serviceFrom, serviceTo, options = {}) {
        const batchId = crypto.randomUUID();
        const batchInfo = {
            id: batchId,
            entityType,
            serviceFrom,
            serviceTo,
            startTime: new Date(),
            processed: 0,
            successful: 0,
            failed: 0,
            errors: []
        };

        this.emit('batch-sync:started', batchInfo);

        try {
            const entities = await this.fetchEntitiesBatch(serviceFrom, entityType, options);
            batchInfo.total = entities.length;

            // Process in batches
            for (let i = 0; i < entities.length; i += this.batchSize) {
                const batch = entities.slice(i, i + this.batchSize);
                const batchPromises = batch.map(async (entity) => {
                    try {
                        await this.syncEntity(entityType, entity.id, serviceFrom, {
                            targetServices: [serviceTo]
                        });
                        batchInfo.successful++;
                    } catch (error) {
                        batchInfo.failed++;
                        batchInfo.errors.push({
                            entityId: entity.id,
                            error: error.message
                        });
                    }
                    batchInfo.processed++;
                });

                await Promise.allSettled(batchPromises);

                this.emit('batch-sync:progress', {
                    batchId,
                    processed: batchInfo.processed,
                    total: batchInfo.total,
                    progress: (batchInfo.processed / batchInfo.total) * 100
                });
            }

            batchInfo.endTime = new Date();
            batchInfo.duration = batchInfo.endTime - batchInfo.startTime;

            this.emit('batch-sync:completed', batchInfo);
            return batchInfo;

        } catch (error) {
            batchInfo.status = 'failed';
            batchInfo.error = error.message;
            this.emit('batch-sync:failed', batchInfo);
            throw error;
        }
    }

    async fetchEntity(serviceName, entityType, entityId) {
        const service = this.services.get(serviceName);
        if (!service) {
            throw new Error(`Service not found: ${serviceName}`);
        }

        // Mock implementation - replace with actual HTTP calls
        const response = await this.makeServiceCall(service, 'GET', `/api/${entityType}/${entityId}`);
        return response.data;
    }

    async fetchEntitiesBatch(serviceName, entityType, options = {}) {
        const service = this.services.get(serviceName);
        if (!service) {
            throw new Error(`Service not found: ${serviceName}`);
        }

        const params = new URLSearchParams();
        if (options.limit) params.append('limit', options.limit);
        if (options.offset) params.append('offset', options.offset);
        if (options.since) params.append('since', options.since);

        const response = await this.makeServiceCall(
            service, 
            'GET', 
            `/api/${entityType}?${params}`
        );
        return response.data;
    }

    async createEntity(serviceName, entity) {
        const service = this.services.get(serviceName);
        const response = await this.makeServiceCall(
            service,
            'POST',
            `/api/${entity.type}`,
            entity
        );
        return response.data;
    }

    async updateEntity(serviceName, entity) {
        const service = this.services.get(serviceName);
        const response = await this.makeServiceCall(
            service,
            'PUT',
            `/api/${entity.type}/${entity.id}`,
            entity
        );
        return response.data;
    }

    async makeServiceCall(service, method, path, data = null) {
        // Mock implementation - replace with actual HTTP client
        return {
            status: 200,
            data: data || { id: crypto.randomUUID(), status: 'success' }
        };
    }

    getTargetServices(sourceService, entityType) {
        const targets = [];
        for (const [serviceName, service] of this.services) {
            if (serviceName !== sourceService && 
                service.syncEnabled &&
                service.entityTypes.includes(entityType)) {
                targets.push(serviceName);
            }
        }
        return targets;
    }

    processSyncResults(results, targetServices) {
        const processed = {};
        results.forEach((result, index) => {
            const serviceName = targetServices[index];
            if (result.status === 'fulfilled') {
                processed[serviceName] = result.value;
            } else {
                processed[serviceName] = {
                    success: false,
                    error: result.reason.message
                };
            }
        });
        return processed;
    }

    async escalateConflict(conflictInfo) {
        // Store conflict for manual resolution
        const conflictId = crypto.randomUUID();
        const conflict = {
            id: conflictId,
            ...conflictInfo,
            status: 'pending',
            escalatedAt: new Date()
        };

        // Store in conflict queue (would be a database in real implementation)
        this.emit('conflict:escalated', conflict);
        
        // Return target entity unchanged for now
        return conflictInfo.targetEntity;
    }

    setupSync() {
        // Periodic sync execution
        this.syncTimer = setInterval(() => {
            if (this.isRunning) {
                this.executeScheduledSyncs();
            }
        }, this.syncInterval);

        // Process sync queue
        this.queueTimer = setInterval(() => {
            this.processSyncQueue();
        }, 5000);
    }

    async executeScheduledSyncs() {
        const now = new Date();
        for (const [ruleId, rule] of this.syncRules) {
            if (!rule.enabled || rule.syncMode !== 'scheduled') {
                continue;
            }

            const nextExecution = rule.lastExecuted 
                ? new Date(rule.lastExecuted.getTime() + rule.frequency)
                : now;

            if (now >= nextExecution) {
                try {
                    await this.executeRule(rule);
                    rule.lastExecuted = now;
                    rule.successCount++;
                } catch (error) {
                    rule.errorCount++;
                    this.emit('rule:error', { ruleId, error: error.message });
                }
            }
        }
    }

    async executeRule(rule) {
        // Execute sync rule based on configuration
        if (rule.entityType && rule.sourceService) {
            await this.batchSync(
                rule.entityType,
                rule.sourceService,
                rule.targetServices,
                { filters: rule.filters }
            );
        }
    }

    processSyncQueue() {
        if (this.syncQueue.length === 0) return;

        const batch = this.syncQueue.splice(0, this.batchSize);
        batch.forEach(async (syncTask) => {
            try {
                await this.syncEntity(
                    syncTask.entityType,
                    syncTask.entityId,
                    syncTask.sourceService,
                    syncTask.options
                );
            } catch (error) {
                this.emit('queue:error', { task: syncTask, error: error.message });
            }
        });
    }

    queueSync(entityType, entityId, sourceService, options = {}) {
        this.syncQueue.push({
            entityType,
            entityId,
            sourceService,
            options,
            queuedAt: new Date()
        });
    }

    start() {
        this.isRunning = true;
        this.emit('sync:started');
    }

    stop() {
        this.isRunning = false;
        if (this.syncTimer) clearInterval(this.syncTimer);
        if (this.queueTimer) clearInterval(this.queueTimer);
        this.emit('sync:stopped');
    }

    getStats() {
        return {
            services: this.services.size,
            syncRules: this.syncRules.size,
            activeSyncs: this.activeSyncs.size,
            queueSize: this.syncQueue.length,
            historySize: this.syncHistory.length,
            isRunning: this.isRunning
        };
    }

    getSyncHistory(limit = 100) {
        return this.syncHistory
            .sort((a, b) => b.startTime - a.startTime)
            .slice(0, limit);
    }

    reset() {
        this.stop();
        this.services.clear();
        this.syncRules.clear();
        this.syncQueue.length = 0;
        this.activeSyncs.clear();
        this.syncHistory.length = 0;
        this.emit('reset');
    }
}

module.exports = DataSync;