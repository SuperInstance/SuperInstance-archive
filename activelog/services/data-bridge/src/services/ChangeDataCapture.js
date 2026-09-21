const { EventEmitter } = require('events');
const crypto = require('crypto');
const { diff } = require('diff');

class ChangeDataCapture extends EventEmitter {
    constructor(options = {}) {
        super();
        this.watchers = new Map();
        this.changeLog = [];
        this.snapshots = new Map();
        this.subscribers = new Map();
        this.processors = new Map();
        this.filters = new Map();
        
        this.batchSize = options.batchSize || 100;
        this.maxLogSize = options.maxLogSize || 10000;
        this.snapshotInterval = options.snapshotInterval || 3600000; // 1 hour
        this.retentionPeriod = options.retentionPeriod || 86400000 * 7; // 7 days
        this.enableBatching = options.enableBatching !== false;
        
        this.setupEventHandlers();
        this.startSnapshotTimer();
    }

    createWatcher(watcherId, config) {
        const watcher = {
            id: watcherId,
            name: config.name || watcherId,
            dataSource: config.dataSource,
            tableName: config.tableName,
            primaryKey: config.primaryKey || 'id',
            watchedFields: config.watchedFields || '*', // '*' for all fields
            changeTypes: config.changeTypes || ['INSERT', 'UPDATE', 'DELETE'],
            filters: config.filters || {},
            transformations: config.transformations || {},
            batchingEnabled: config.batchingEnabled !== false,
            realTimeEnabled: config.realTimeEnabled !== false,
            snapshotEnabled: config.snapshotEnabled !== false,
            lastProcessedTimestamp: config.lastProcessedTimestamp || new Date(),
            metadata: config.metadata || {},
            createdAt: new Date(),
            isActive: false,
            totalChanges: 0,
            lastChange: null
        };

        this.watchers.set(watcherId, watcher);
        this.emit('watcher:created', watcher);
        return watcher;
    }

    startWatcher(watcherId) {
        const watcher = this.watchers.get(watcherId);
        if (!watcher) {
            throw new Error(`Watcher not found: ${watcherId}`);
        }

        if (watcher.isActive) {
            return watcher;
        }

        watcher.isActive = true;
        watcher.startedAt = new Date();

        // In a real implementation, this would connect to database change streams
        // For now, we'll simulate periodic polling
        watcher.pollingInterval = setInterval(() => {
            this.pollForChanges(watcherId);
        }, 5000); // Poll every 5 seconds

        this.emit('watcher:started', watcher);
        return watcher;
    }

    stopWatcher(watcherId) {
        const watcher = this.watchers.get(watcherId);
        if (!watcher) {
            throw new Error(`Watcher not found: ${watcherId}`);
        }

        if (!watcher.isActive) {
            return watcher;
        }

        watcher.isActive = false;
        watcher.stoppedAt = new Date();

        if (watcher.pollingInterval) {
            clearInterval(watcher.pollingInterval);
            delete watcher.pollingInterval;
        }

        this.emit('watcher:stopped', watcher);
        return watcher;
    }

    async pollForChanges(watcherId) {
        const watcher = this.watchers.get(watcherId);
        if (!watcher || !watcher.isActive) {
            return;
        }

        try {
            // Simulate fetching changes from data source
            const changes = await this.fetchChanges(watcher);
            
            if (changes.length > 0) {
                await this.processChanges(watcherId, changes);
                watcher.lastProcessedTimestamp = new Date();
            }

        } catch (error) {
            this.emit('watcher:error', {
                watcherId,
                error: error.message,
                timestamp: new Date()
            });
        }
    }

    async fetchChanges(watcher) {
        // Mock implementation - in reality this would query the actual data source
        // This could be database change logs, API polling, file monitoring, etc.
        
        const mockChanges = [];
        
        // Occasionally generate mock changes for demonstration
        if (Math.random() < 0.1) { // 10% chance of changes
            const changeId = crypto.randomUUID();
            const mockChange = {
                id: changeId,
                watcherId: watcher.id,
                changeType: ['INSERT', 'UPDATE', 'DELETE'][Math.floor(Math.random() * 3)],
                tableName: watcher.tableName,
                primaryKey: watcher.primaryKey,
                recordId: crypto.randomUUID(),
                timestamp: new Date(),
                oldData: null,
                newData: {
                    id: crypto.randomUUID(),
                    name: `Mock Record ${Math.floor(Math.random() * 1000)}`,
                    status: 'active',
                    updatedAt: new Date().toISOString()
                },
                metadata: {
                    source: watcher.dataSource,
                    batchId: null,
                    sequence: watcher.totalChanges + 1
                }
            };

            if (mockChange.changeType === 'UPDATE') {
                mockChange.oldData = {
                    ...mockChange.newData,
                    name: `Old Mock Record ${Math.floor(Math.random() * 1000)}`,
                    updatedAt: new Date(Date.now() - 3600000).toISOString()
                };
            } else if (mockChange.changeType === 'DELETE') {
                mockChange.oldData = mockChange.newData;
                mockChange.newData = null;
            }

            mockChanges.push(mockChange);
        }

        return mockChanges;
    }

    async processChanges(watcherId, changes) {
        const watcher = this.watchers.get(watcherId);
        if (!watcher) {
            return;
        }

        const processedChanges = [];

        for (const change of changes) {
            try {
                // Apply filters
                if (!this.passesFilters(change, watcher.filters)) {
                    continue;
                }

                // Apply transformations
                const transformedChange = await this.applyTransformations(change, watcher.transformations);

                // Enhance change with additional metadata
                const enrichedChange = this.enrichChange(transformedChange, watcher);

                processedChanges.push(enrichedChange);
                
                watcher.totalChanges++;
                watcher.lastChange = enrichedChange;

            } catch (error) {
                this.emit('change:processing-error', {
                    watcherId,
                    change,
                    error: error.message
                });
            }
        }

        if (processedChanges.length > 0) {
            // Add to change log
            this.changeLog.push(...processedChanges);
            this.trimChangeLog();

            // Process in batches or real-time
            if (watcher.batchingEnabled && this.enableBatching) {
                await this.processBatch(watcherId, processedChanges);
            } else if (watcher.realTimeEnabled) {
                for (const change of processedChanges) {
                    await this.processRealTimeChange(watcherId, change);
                }
            }

            this.emit('changes:processed', {
                watcherId,
                changeCount: processedChanges.length,
                timestamp: new Date()
            });
        }
    }

    passesFilters(change, filters) {
        for (const [filterName, filterValue] of Object.entries(filters)) {
            switch (filterName) {
                case 'changeTypes':
                    if (!filterValue.includes(change.changeType)) {
                        return false;
                    }
                    break;
                case 'fields':
                    // Check if any of the specified fields were changed
                    if (change.changeType === 'UPDATE' && change.fieldChanges) {
                        const hasRelevantChanges = filterValue.some(field => 
                            change.fieldChanges.hasOwnProperty(field)
                        );
                        if (!hasRelevantChanges) {
                            return false;
                        }
                    }
                    break;
                case 'conditions':
                    // Apply custom condition filters
                    for (const condition of filterValue) {
                        if (!this.evaluateCondition(change, condition)) {
                            return false;
                        }
                    }
                    break;
            }
        }
        return true;
    }

    evaluateCondition(change, condition) {
        const { field, operator, value } = condition;
        const data = change.newData || change.oldData;
        
        if (!data || !data.hasOwnProperty(field)) {
            return false;
        }

        const fieldValue = data[field];

        switch (operator) {
            case 'equals':
                return fieldValue === value;
            case 'not_equals':
                return fieldValue !== value;
            case 'greater_than':
                return fieldValue > value;
            case 'less_than':
                return fieldValue < value;
            case 'contains':
                return String(fieldValue).includes(value);
            case 'matches':
                return new RegExp(value).test(String(fieldValue));
            default:
                return true;
        }
    }

    async applyTransformations(change, transformations) {
        let transformedChange = { ...change };

        for (const [transformationType, transformConfig] of Object.entries(transformations)) {
            switch (transformationType) {
                case 'fieldMapping':
                    transformedChange = this.applyFieldMapping(transformedChange, transformConfig);
                    break;
                case 'enrichment':
                    transformedChange = await this.applyEnrichment(transformedChange, transformConfig);
                    break;
                case 'anonymization':
                    transformedChange = this.applyAnonymization(transformedChange, transformConfig);
                    break;
                case 'aggregation':
                    transformedChange = this.applyAggregation(transformedChange, transformConfig);
                    break;
            }
        }

        return transformedChange;
    }

    applyFieldMapping(change, mapping) {
        const mappedChange = { ...change };
        
        if (mappedChange.newData) {
            mappedChange.newData = this.mapFields(mappedChange.newData, mapping);
        }
        if (mappedChange.oldData) {
            mappedChange.oldData = this.mapFields(mappedChange.oldData, mapping);
        }

        return mappedChange;
    }

    mapFields(data, mapping) {
        const mapped = {};
        for (const [sourceField, targetField] of Object.entries(mapping)) {
            if (data.hasOwnProperty(sourceField)) {
                mapped[targetField] = data[sourceField];
            }
        }
        return { ...data, ...mapped };
    }

    async applyEnrichment(change, enrichmentConfig) {
        const enrichedChange = { ...change };

        for (const enrichment of enrichmentConfig) {
            switch (enrichment.type) {
                case 'lookup':
                    enrichedChange.enrichedData = await this.performLookup(change, enrichment);
                    break;
                case 'calculation':
                    enrichedChange.calculatedFields = this.performCalculation(change, enrichment);
                    break;
                case 'geolocation':
                    enrichedChange.geoData = await this.enrichWithGeolocation(change, enrichment);
                    break;
            }
        }

        return enrichedChange;
    }

    async performLookup(change, config) {
        // Mock lookup implementation
        return {
            lookupType: config.lookupType,
            result: `Looked up data for ${change.recordId}`,
            timestamp: new Date()
        };
    }

    performCalculation(change, config) {
        const calculations = {};
        const data = change.newData || change.oldData || {};

        for (const calc of config.calculations) {
            try {
                switch (calc.operation) {
                    case 'sum':
                        calculations[calc.name] = calc.fields.reduce((sum, field) => sum + (data[field] || 0), 0);
                        break;
                    case 'average':
                        const values = calc.fields.map(field => data[field] || 0);
                        calculations[calc.name] = values.reduce((sum, val) => sum + val, 0) / values.length;
                        break;
                    case 'concatenate':
                        calculations[calc.name] = calc.fields.map(field => data[field] || '').join(calc.separator || ' ');
                        break;
                }
            } catch (error) {
                calculations[calc.name] = null;
            }
        }

        return calculations;
    }

    async enrichWithGeolocation(change, config) {
        // Mock geolocation enrichment
        return {
            country: 'US',
            region: 'California',
            city: 'San Francisco',
            coordinates: { lat: 37.7749, lng: -122.4194 }
        };
    }

    applyAnonymization(change, config) {
        const anonymizedChange = { ...change };

        const anonymizeData = (data) => {
            if (!data) return data;
            
            const anonymized = { ...data };
            for (const field of config.fields || []) {
                if (anonymized[field]) {
                    switch (config.method) {
                        case 'hash':
                            anonymized[field] = crypto.createHash('sha256').update(String(anonymized[field])).digest('hex').substring(0, 8);
                            break;
                        case 'mask':
                            const value = String(anonymized[field]);
                            anonymized[field] = '*'.repeat(Math.max(value.length - 4, 0)) + value.slice(-4);
                            break;
                        case 'remove':
                            anonymized[field] = '[REDACTED]';
                            break;
                    }
                }
            }
            return anonymized;
        };

        if (anonymizedChange.newData) {
            anonymizedChange.newData = anonymizeData(anonymizedChange.newData);
        }
        if (anonymizedChange.oldData) {
            anonymizedChange.oldData = anonymizeData(anonymizedChange.oldData);
        }

        return anonymizedChange;
    }

    applyAggregation(change, config) {
        // Aggregation would typically be handled at a higher level
        // This is a placeholder for aggregation logic
        return {
            ...change,
            aggregationMetadata: {
                aggregationType: config.type,
                windowSize: config.windowSize,
                timestamp: new Date()
            }
        };
    }

    enrichChange(change, watcher) {
        const enriched = {
            ...change,
            watcherId: watcher.id,
            watcherName: watcher.name,
            processedAt: new Date(),
            sequence: watcher.totalChanges + 1
        };

        // Add field-level change detection for updates
        if (change.changeType === 'UPDATE' && change.oldData && change.newData) {
            enriched.fieldChanges = this.detectFieldChanges(change.oldData, change.newData);
        }

        // Add change size estimation
        enriched.changeSize = this.estimateChangeSize(change);

        return enriched;
    }

    detectFieldChanges(oldData, newData) {
        const changes = {};
        
        // Find all unique fields
        const allFields = new Set([...Object.keys(oldData), ...Object.keys(newData)]);
        
        for (const field of allFields) {
            const oldValue = oldData[field];
            const newValue = newData[field];
            
            if (oldValue !== newValue) {
                changes[field] = {
                    oldValue,
                    newValue,
                    changeType: oldValue === undefined ? 'added' : 
                               newValue === undefined ? 'removed' : 'modified'
                };
            }
        }
        
        return changes;
    }

    estimateChangeSize(change) {
        const oldSize = change.oldData ? Buffer.byteLength(JSON.stringify(change.oldData)) : 0;
        const newSize = change.newData ? Buffer.byteLength(JSON.stringify(change.newData)) : 0;
        
        return {
            oldSize,
            newSize,
            deltaSize: newSize - oldSize
        };
    }

    async processBatch(watcherId, changes) {
        const batchId = crypto.randomUUID();
        const batch = {
            id: batchId,
            watcherId,
            changes,
            size: changes.length,
            createdAt: new Date(),
            processedAt: null,
            status: 'pending'
        };

        this.emit('batch:created', batch);

        try {
            // Process the batch
            await this.executeBatchProcessing(batch);
            
            batch.status = 'completed';
            batch.processedAt = new Date();
            
            this.emit('batch:completed', batch);

        } catch (error) {
            batch.status = 'failed';
            batch.error = error.message;
            
            this.emit('batch:failed', batch);
        }
    }

    async executeBatchProcessing(batch) {
        // Notify subscribers
        for (const [subscriberId, subscriber] of this.subscribers) {
            try {
                if (subscriber.batchEnabled && this.matchesSubscription(batch, subscriber)) {
                    await this.notifySubscriber(subscriberId, { type: 'batch', data: batch });
                }
            } catch (error) {
                this.emit('subscriber:notification-failed', {
                    subscriberId,
                    error: error.message,
                    batch: batch.id
                });
            }
        }

        // Apply processors
        for (const [processorId, processor] of this.processors) {
            try {
                if (processor.batchEnabled) {
                    await processor.process(batch);
                }
            } catch (error) {
                this.emit('processor:failed', {
                    processorId,
                    error: error.message,
                    batch: batch.id
                });
            }
        }
    }

    async processRealTimeChange(watcherId, change) {
        this.emit('change:real-time', { watcherId, change });

        // Notify real-time subscribers
        for (const [subscriberId, subscriber] of this.subscribers) {
            try {
                if (subscriber.realTimeEnabled && this.matchesSubscription(change, subscriber)) {
                    await this.notifySubscriber(subscriberId, { type: 'change', data: change });
                }
            } catch (error) {
                this.emit('subscriber:notification-failed', {
                    subscriberId,
                    error: error.message,
                    change: change.id
                });
            }
        }

        // Apply real-time processors
        for (const [processorId, processor] of this.processors) {
            try {
                if (processor.realTimeEnabled) {
                    await processor.process(change);
                }
            } catch (error) {
                this.emit('processor:failed', {
                    processorId,
                    error: error.message,
                    change: change.id
                });
            }
        }
    }

    subscribe(subscriberId, config) {
        const subscription = {
            id: subscriberId,
            name: config.name || subscriberId,
            watcherIds: config.watcherIds || [],
            changeTypes: config.changeTypes || ['INSERT', 'UPDATE', 'DELETE'],
            filters: config.filters || {},
            endpoint: config.endpoint,
            callback: config.callback,
            realTimeEnabled: config.realTimeEnabled !== false,
            batchEnabled: config.batchEnabled !== false,
            maxRetries: config.maxRetries || 3,
            retryDelay: config.retryDelay || 5000,
            createdAt: new Date(),
            totalNotifications: 0,
            failedNotifications: 0,
            lastNotification: null
        };

        this.subscribers.set(subscriberId, subscription);
        this.emit('subscriber:registered', subscription);
        return subscription;
    }

    unsubscribe(subscriberId) {
        const subscription = this.subscribers.get(subscriberId);
        if (subscription) {
            this.subscribers.delete(subscriberId);
            this.emit('subscriber:unregistered', subscription);
        }
        return subscription;
    }

    async notifySubscriber(subscriberId, notification) {
        const subscriber = this.subscribers.get(subscriberId);
        if (!subscriber) {
            return;
        }

        try {
            if (subscriber.callback) {
                // Direct callback
                await subscriber.callback(notification);
            } else if (subscriber.endpoint) {
                // HTTP webhook (mock implementation)
                await this.sendWebhook(subscriber.endpoint, notification);
            }

            subscriber.totalNotifications++;
            subscriber.lastNotification = new Date();

        } catch (error) {
            subscriber.failedNotifications++;
            throw error;
        }
    }

    async sendWebhook(endpoint, payload) {
        // Mock webhook implementation
        console.log(`Sending webhook to ${endpoint}:`, payload);
        return { status: 200, sent: true };
    }

    matchesSubscription(item, subscription) {
        // Check watcher IDs
        if (subscription.watcherIds.length > 0) {
            const watcherId = item.watcherId || (item.changes && item.changes[0]?.watcherId);
            if (!subscription.watcherIds.includes(watcherId)) {
                return false;
            }
        }

        // Check change types
        const changeTypes = item.changeType ? [item.changeType] : 
                          (item.changes ? item.changes.map(c => c.changeType) : []);
        
        if (!changeTypes.some(type => subscription.changeTypes.includes(type))) {
            return false;
        }

        // Apply additional filters
        return this.passesFilters(item, subscription.filters);
    }

    registerProcessor(processorId, processor) {
        const processorWrapper = {
            id: processorId,
            name: processor.name || processorId,
            process: processor.process,
            realTimeEnabled: processor.realTimeEnabled !== false,
            batchEnabled: processor.batchEnabled !== false,
            priority: processor.priority || 5,
            metadata: processor.metadata || {},
            registeredAt: new Date(),
            totalProcessed: 0,
            totalErrors: 0,
            lastProcessed: null
        };

        this.processors.set(processorId, processorWrapper);
        this.emit('processor:registered', processorWrapper);
        return processorWrapper;
    }

    unregisterProcessor(processorId) {
        const processor = this.processors.get(processorId);
        if (processor) {
            this.processors.delete(processorId);
            this.emit('processor:unregistered', processor);
        }
        return processor;
    }

    createSnapshot(watcherId) {
        const watcher = this.watchers.get(watcherId);
        if (!watcher) {
            throw new Error(`Watcher not found: ${watcherId}`);
        }

        const snapshotId = crypto.randomUUID();
        const snapshot = {
            id: snapshotId,
            watcherId,
            timestamp: new Date(),
            metadata: {
                totalChanges: watcher.totalChanges,
                lastProcessedTimestamp: watcher.lastProcessedTimestamp,
                status: watcher.isActive ? 'active' : 'inactive'
            },
            // In a real implementation, this would contain actual data snapshot
            data: {
                recordCount: Math.floor(Math.random() * 1000),
                checksum: crypto.randomBytes(16).toString('hex')
            }
        };

        this.snapshots.set(snapshotId, snapshot);
        this.emit('snapshot:created', snapshot);
        return snapshot;
    }

    getChanges(options = {}) {
        let changes = [...this.changeLog];

        // Apply filters
        if (options.watcherId) {
            changes = changes.filter(c => c.watcherId === options.watcherId);
        }

        if (options.changeTypes) {
            changes = changes.filter(c => options.changeTypes.includes(c.changeType));
        }

        if (options.since) {
            const since = new Date(options.since);
            changes = changes.filter(c => c.timestamp >= since);
        }

        if (options.until) {
            const until = new Date(options.until);
            changes = changes.filter(c => c.timestamp <= until);
        }

        // Sort and limit
        changes.sort((a, b) => b.timestamp - a.timestamp);
        
        if (options.limit) {
            changes = changes.slice(0, options.limit);
        }

        return changes;
    }

    getChangeStatistics(watcherId = null) {
        const changes = watcherId ? 
            this.changeLog.filter(c => c.watcherId === watcherId) : 
            this.changeLog;

        const stats = {
            totalChanges: changes.length,
            changeTypes: {},
            recentActivity: {},
            averageChangeSize: 0,
            watchers: watcherId ? 1 : new Set(changes.map(c => c.watcherId)).size
        };

        let totalSize = 0;
        for (const change of changes) {
            // Count change types
            stats.changeTypes[change.changeType] = (stats.changeTypes[change.changeType] || 0) + 1;

            // Calculate size
            if (change.changeSize) {
                totalSize += change.changeSize.newSize || 0;
            }

            // Recent activity (last 24 hours grouped by hour)
            const hour = new Date(change.timestamp).toISOString().substring(0, 13);
            stats.recentActivity[hour] = (stats.recentActivity[hour] || 0) + 1;
        }

        stats.averageChangeSize = changes.length > 0 ? totalSize / changes.length : 0;

        return stats;
    }

    trimChangeLog() {
        if (this.changeLog.length > this.maxLogSize) {
            const excess = this.changeLog.length - this.maxLogSize;
            this.changeLog.splice(0, excess);
            
            this.emit('changelog:trimmed', {
                removedEntries: excess,
                remainingEntries: this.changeLog.length
            });
        }
    }

    startSnapshotTimer() {
        this.snapshotTimer = setInterval(() => {
            for (const [watcherId, watcher] of this.watchers) {
                if (watcher.snapshotEnabled && watcher.isActive) {
                    try {
                        this.createSnapshot(watcherId);
                    } catch (error) {
                        this.emit('snapshot:error', {
                            watcherId,
                            error: error.message
                        });
                    }
                }
            }
        }, this.snapshotInterval);
    }

    setupEventHandlers() {
        this.on('changes:processed', (info) => {
            console.log(`Processed ${info.changeCount} changes for watcher ${info.watcherId}`);
        });

        this.on('batch:completed', (batch) => {
            console.log(`Batch completed: ${batch.id} with ${batch.size} changes`);
        });

        this.on('subscriber:registered', (subscription) => {
            console.log(`Subscriber registered: ${subscription.id}`);
        });
    }

    getStats() {
        return {
            watchers: this.watchers.size,
            activeWatchers: Array.from(this.watchers.values()).filter(w => w.isActive).length,
            totalChanges: this.changeLog.length,
            subscribers: this.subscribers.size,
            processors: this.processors.size,
            snapshots: this.snapshots.size
        };
    }

    getWatchers() {
        return Array.from(this.watchers.values());
    }

    getSubscribers() {
        return Array.from(this.subscribers.values());
    }

    getProcessors() {
        return Array.from(this.processors.values());
    }

    getSnapshots(watcherId = null) {
        const snapshots = Array.from(this.snapshots.values());
        return watcherId ? 
            snapshots.filter(s => s.watcherId === watcherId) : 
            snapshots;
    }

    cleanup() {
        const cutoff = new Date(Date.now() - this.retentionPeriod);
        
        let cleaned = 0;
        this.changeLog = this.changeLog.filter(change => {
            if (change.timestamp < cutoff) {
                cleaned++;
                return false;
            }
            return true;
        });

        // Clean old snapshots
        let cleanedSnapshots = 0;
        for (const [snapshotId, snapshot] of this.snapshots) {
            if (snapshot.timestamp < cutoff) {
                this.snapshots.delete(snapshotId);
                cleanedSnapshots++;
            }
        }

        this.emit('cleanup:completed', {
            cleanedChanges: cleaned,
            cleanedSnapshots,
            timestamp: new Date()
        });

        return { cleanedChanges: cleaned, cleanedSnapshots };
    }

    reset() {
        // Stop all watchers
        for (const [watcherId, watcher] of this.watchers) {
            if (watcher.isActive) {
                this.stopWatcher(watcherId);
            }
        }

        this.watchers.clear();
        this.changeLog.length = 0;
        this.snapshots.clear();
        this.subscribers.clear();
        this.processors.clear();
        this.filters.clear();

        if (this.snapshotTimer) {
            clearInterval(this.snapshotTimer);
        }

        this.emit('reset');
    }
}

module.exports = ChangeDataCapture;