export class DataSync {
    constructor() {
        this.config = {};
        this.syncQueue = [];
        this.syncInProgress = false;
        this.lastSyncTime = null;
        this.syncErrors = [];
        this.initialized = false;
    }

    static instance = null;

    static getInstance() {
        if (!DataSync.instance) {
            DataSync.instance = new DataSync();
        }
        return DataSync.instance;
    }

    async init(config = {}) {
        if (this.initialized) return;

        this.config = {
            enabled: true,
            cloudProvider: 'activelog-cloud',
            encryption: 'client-side',
            conflictResolution: 'merge',
            syncFrequency: 'realtime',
            offlineSupport: true,
            maxRetries: 3,
            retryDelay: 1000,
            ...config
        };

        if (!this.config.enabled) {
            console.log('DataSync disabled by configuration');
            return;
        }

        await this.loadSyncState();
        await this.setupSyncStrategy();
        this.bindEvents();

        this.initialized = true;
        console.log('DataSync initialized');
    }

    async loadSyncState() {
        try {
            const state = localStorage.getItem('activelog_sync_state');
            if (state) {
                const parsed = JSON.parse(state);
                this.lastSyncTime = parsed.lastSyncTime;
                this.syncQueue = parsed.queue || [];
            }
        } catch (error) {
            console.warn('Failed to load sync state:', error);
        }
    }

    async setupSyncStrategy() {
        switch (this.config.syncFrequency) {
            case 'realtime':
                this.enableRealtimeSync();
                break;
            case 'hourly':
                setInterval(() => this.syncAll(), 60 * 60 * 1000);
                break;
            case 'daily':
                setInterval(() => this.syncAll(), 24 * 60 * 60 * 1000);
                break;
        }

        if (this.config.offlineSupport) {
            window.addEventListener('online', () => {
                if (this.syncQueue.length > 0) {
                    this.syncAll();
                }
            });

            window.addEventListener('offline', () => {
                console.log('Offline mode: operations will be queued');
            });
        }
    }

    enableRealtimeSync() {
        let syncTimer = null;
        const debouncedSync = () => {
            clearTimeout(syncTimer);
            syncTimer = setTimeout(() => this.syncAll(), 2000);
        };

        document.addEventListener('data:changed', debouncedSync);
        document.addEventListener('data:created', debouncedSync);
        document.addEventListener('data:updated', debouncedSync);
        document.addEventListener('data:deleted', debouncedSync);
    }

    bindEvents() {
        document.addEventListener('sync:force', () => {
            this.syncAll();
        });

        document.addEventListener('data:create', (event) => {
            this.queueOperation('create', event.detail);
        });

        document.addEventListener('data:update', (event) => {
            this.queueOperation('update', event.detail);
        });

        document.addEventListener('data:delete', (event) => {
            this.queueOperation('delete', event.detail);
        });

        document.addEventListener('app:cache:clear', () => {
            this.clearCache();
        });
    }

    queueOperation(type, data) {
        const operation = {
            id: crypto.randomUUID(),
            type,
            data,
            timestamp: Date.now(),
            retries: 0
        };

        this.syncQueue.push(operation);
        this.saveSyncState();

        if (this.config.syncFrequency === 'realtime' && navigator.onLine) {
            this.syncAll();
        }

        this.emitSyncEvent('operation-queued', { operation });
    }

    async syncAll() {
        if (this.syncInProgress || this.syncQueue.length === 0) return;

        this.syncInProgress = true;

        try {
            if (!navigator.onLine && this.config.offlineSupport) {
                console.log('Offline: sync queued');
                return;
            }

            const operations = [...this.syncQueue];
            this.syncQueue = [];

            const results = await this.performBatchSync(operations);
            
            this.lastSyncTime = Date.now();
            this.saveSyncState();

            this.emitSyncEvent('sync-completed', { 
                operations: operations.length,
                results 
            });

            console.log(`Synced ${operations.length} operations`);

        } catch (error) {
            console.error('Sync failed:', error);
            this.syncErrors.push({
                timestamp: Date.now(),
                error: error.message
            });

            this.emitSyncEvent('sync-error', { error: error.message });
            
        } finally {
            this.syncInProgress = false;
        }
    }

    async performBatchSync(operations) {
        const batches = this.batchOperations(operations);
        const results = [];

        for (const batch of batches) {
            try {
                const result = await this.syncBatch(batch);
                results.push(...result);
            } catch (error) {
                console.error('Batch sync failed:', error);
                
                for (const op of batch) {
                    if (op.retries < this.config.maxRetries) {
                        op.retries++;
                        this.syncQueue.push(op);
                    }
                }
                
                await this.delay(this.config.retryDelay);
            }
        }

        return results;
    }

    batchOperations(operations) {
        const batches = [];
        const batchSize = 50;

        for (let i = 0; i < operations.length; i += batchSize) {
            batches.push(operations.slice(i, i + batchSize));
        }

        return batches;
    }

    async syncBatch(operations) {
        const syncData = {
            operations,
            clientId: this.getClientId(),
            timestamp: Date.now(),
            lastSyncTime: this.lastSyncTime
        };

        if (this.config.encryption === 'client-side') {
            syncData.encrypted = await this.encryptOperations(operations);
            delete syncData.operations;
        }

        const response = await fetch('/api/data/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': await this.getAuthToken()
            },
            body: JSON.stringify(syncData)
        });

        if (!response.ok) {
            throw new Error(`Sync failed: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.conflicts && result.conflicts.length > 0) {
            await this.resolveConflicts(result.conflicts);
        }

        if (result.serverOperations && result.serverOperations.length > 0) {
            await this.applyServerOperations(result.serverOperations);
        }

        return result.results || [];
    }

    async resolveConflicts(conflicts) {
        for (const conflict of conflicts) {
            const resolution = await this.resolveConflict(conflict);
            this.emitDataEvent('data-resolved', {
                id: conflict.id,
                resolution
            });
        }

        this.emitSyncEvent('conflicts-resolved', { count: conflicts.length });
    }

    async resolveConflict(conflict) {
        switch (this.config.conflictResolution) {
            case 'client-wins':
                return this.applyClientOperation(conflict.clientOperation);
            
            case 'server-wins':
                return this.applyServerOperation(conflict.serverOperation);
            
            case 'latest-wins':
                const clientTime = conflict.clientOperation.timestamp;
                const serverTime = conflict.serverOperation.timestamp;
                return clientTime > serverTime
                    ? this.applyClientOperation(conflict.clientOperation)
                    : this.applyServerOperation(conflict.serverOperation);
            
            case 'merge':
                return this.mergeOperations(conflict);
            
            default:
                return this.applyClientOperation(conflict.clientOperation);
        }
    }

    async mergeOperations(conflict) {
        const { clientOperation, serverOperation } = conflict;
        
        if (clientOperation.type === 'update' && serverOperation.type === 'update') {
            const merged = {
                ...serverOperation.data,
                ...clientOperation.data,
                _mergedAt: Date.now()
            };
            
            return this.applyDataOperation('update', merged);
        }

        return this.applyClientOperation(clientOperation);
    }

    async applyServerOperations(operations) {
        for (const operation of operations) {
            await this.applyServerOperation(operation);
        }

        this.emitSyncEvent('server-operations-applied', { 
            count: operations.length 
        });
    }

    async applyClientOperation(operation) {
        return this.applyDataOperation(operation.type, operation.data);
    }

    async applyServerOperation(operation) {
        return this.applyDataOperation(operation.type, operation.data);
    }

    async applyDataOperation(type, data) {
        switch (type) {
            case 'create':
                return this.createLocalData(data);
            case 'update':
                return this.updateLocalData(data);
            case 'delete':
                return this.deleteLocalData(data);
            default:
                console.warn(`Unknown operation type: ${type}`);
                return null;
        }
    }

    async createLocalData(data) {
        const storageKey = this.getStorageKey(data.type, data.id);
        const existing = localStorage.getItem(storageKey);
        
        if (!existing) {
            localStorage.setItem(storageKey, JSON.stringify(data));
            this.emitDataEvent('data-created', data);
        }
        
        return data;
    }

    async updateLocalData(data) {
        const storageKey = this.getStorageKey(data.type, data.id);
        const existing = localStorage.getItem(storageKey);
        
        if (existing) {
            const merged = { ...JSON.parse(existing), ...data };
            localStorage.setItem(storageKey, JSON.stringify(merged));
            this.emitDataEvent('data-updated', merged);
            return merged;
        }
        
        return this.createLocalData(data);
    }

    async deleteLocalData(data) {
        const storageKey = this.getStorageKey(data.type, data.id);
        localStorage.removeItem(storageKey);
        this.emitDataEvent('data-deleted', data);
        return data;
    }

    getStorageKey(type, id) {
        return `activelog_data_${type}_${id}`;
    }

    async clearCache() {
        const keys = Object.keys(localStorage);
        const dataKeys = keys.filter(key => key.startsWith('activelog_data_'));
        
        dataKeys.forEach(key => localStorage.removeItem(key));
        
        this.emitSyncEvent('cache-cleared', { 
            keysCleared: dataKeys.length 
        });
    }

    saveSyncState() {
        try {
            const state = {
                lastSyncTime: this.lastSyncTime,
                queue: this.syncQueue
            };
            localStorage.setItem('activelog_sync_state', JSON.stringify(state));
        } catch (error) {
            console.error('Failed to save sync state:', error);
        }
    }

    getClientId() {
        let clientId = localStorage.getItem('activelog_client_id');
        if (!clientId) {
            clientId = crypto.randomUUID();
            localStorage.setItem('activelog_client_id', clientId);
        }
        return clientId;
    }

    async getAuthToken() {
        try {
            const authManager = window.AuthManager || (await import('../auth/AuthManager.js')).default;
            const token = await authManager.tokenManager?.getValidToken();
            return token ? `Bearer ${token}` : '';
        } catch (error) {
            console.warn('Failed to get auth token:', error);
            return '';
        }
    }

    async encryptOperations(operations) {
        if (!crypto.subtle) {
            console.warn('Web Crypto API not available, storing unencrypted');
            return operations;
        }

        try {
            const key = await this.getEncryptionKey();
            const iv = crypto.getRandomValues(new Uint8Array(12));
            const encoded = new TextEncoder().encode(JSON.stringify(operations));
            
            const encrypted = await crypto.subtle.encrypt(
                { name: 'AES-GCM', iv },
                key,
                encoded
            );

            return {
                encrypted: Array.from(new Uint8Array(encrypted)),
                iv: Array.from(iv)
            };
        } catch (error) {
            console.warn('Encryption failed, sending unencrypted:', error);
            return operations;
        }
    }

    async getEncryptionKey() {
        const keyMaterial = await crypto.subtle.importKey(
            'raw',
            new TextEncoder().encode(this.getClientId()),
            { name: 'PBKDF2' },
            false,
            ['deriveKey']
        );

        return crypto.subtle.deriveKey(
            {
                name: 'PBKDF2',
                salt: new TextEncoder().encode('activelog-data'),
                iterations: 100000,
                hash: 'SHA-256'
            },
            keyMaterial,
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt', 'decrypt']
        );
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    emitSyncEvent(eventName, data = {}) {
        document.dispatchEvent(new CustomEvent(`sync:${eventName}`, {
            detail: data
        }));
    }

    emitDataEvent(eventName, data = {}) {
        document.dispatchEvent(new CustomEvent(`data:${eventName}`, {
            detail: data
        }));
    }

    onSyncEvent(eventName, callback) {
        document.addEventListener(`sync:${eventName}`, callback);
        return () => document.removeEventListener(`sync:${eventName}`, callback);
    }

    onDataEvent(eventName, callback) {
        document.addEventListener(`data:${eventName}`, callback);
        return () => document.removeEventListener(`data:${eventName}`, callback);
    }

    getStatus() {
        return {
            initialized: this.initialized,
            syncing: this.syncInProgress,
            queueLength: this.syncQueue.length,
            lastSyncTime: this.lastSyncTime,
            online: navigator.onLine,
            errors: this.syncErrors.slice(-10)
        };
    }

    async exportData() {
        const keys = Object.keys(localStorage);
        const dataKeys = keys.filter(key => key.startsWith('activelog_data_'));
        const data = {};

        dataKeys.forEach(key => {
            try {
                data[key] = JSON.parse(localStorage.getItem(key));
            } catch (error) {
                console.warn(`Failed to parse data for key ${key}:`, error);
            }
        });

        const exportData = {
            data,
            timestamp: Date.now(),
            version: '1.0',
            app: this.config.appName || 'ActiveLog'
        };

        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `${exportData.app}-data-${new Date().toISOString().split('T')[0]}.json`;
        link.click();
    }

    destroy() {
        this.syncQueue = [];
        this.syncInProgress = false;
        this.lastSyncTime = null;
        this.syncErrors = [];
        this.initialized = false;
    }
}

export default DataSync.getInstance();