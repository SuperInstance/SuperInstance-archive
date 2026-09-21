export class DataSync {
    constructor() {
        this.config = {};
        this.syncManager = null;
        this.conflictResolver = null;
        this.encryptionManager = null;
        this.syncQueue = [];
        this.isOnline = navigator.onLine;
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
            encryption: 'standard',
            conflictResolution: 'merge',
            syncFrequency: 'realtime',
            offlineSupport: true,
            crossAppSharing: true,
            enableVersioning: false,
            maxRetries: 3,
            retryDelay: 1000,
            ...config
        };

        if (!this.config.enabled) {
            console.log('DataSync disabled by configuration');
            return;
        }

        await this.initializeComponents();
        this.setupEventListeners();
        await this.performInitialSync();

        this.initialized = true;
        console.log('DataSync initialized with provider:', this.config.cloudProvider);
    }

    async initializeComponents() {
        // Initialize sync manager
        const { SyncManager } = await import('./SyncManager.js');
        this.syncManager = new SyncManager(this.config);
        await this.syncManager.init();

        // Initialize conflict resolver
        const { ConflictResolver } = await import('./ConflictResolver.js');
        this.conflictResolver = new ConflictResolver(this.config.conflictResolution);

        // Initialize encryption if enabled
        if (this.config.encryption !== 'none') {
            const { EncryptionManager } = await import('./EncryptionManager.js');
            this.encryptionManager = new EncryptionManager(this.config.encryption);
            await this.encryptionManager.init();
        }
    }

    setupEventListeners() {
        // Online/offline detection
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.emitSyncEvent('connection-restored');
            this.processSyncQueue();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.emitSyncEvent('connection-lost');
        });

        // Data change listeners
        document.addEventListener('data:changed', (event) => {
            this.handleDataChange(event.detail);
        });

        document.addEventListener('data:request-sync', (event) => {
            this.syncData(event.detail);
        });

        // Cross-app data sharing
        if (this.config.crossAppSharing) {
            document.addEventListener('data:share-request', (event) => {
                this.handleShareRequest(event.detail);
            });
        }
    }

    async performInitialSync() {
        if (!this.isOnline) {
            console.log('Offline - skipping initial sync');
            return;
        }

        try {
            this.emitSyncEvent('sync-started', { type: 'initial' });
            
            const lastSyncTime = await this.getLastSyncTime();
            const changes = await this.syncManager.getChanges(lastSyncTime);
            
            if (changes.length > 0) {
                await this.processChanges(changes);
                await this.setLastSyncTime(Date.now());
            }

            this.emitSyncEvent('sync-completed', { 
                type: 'initial', 
                changesProcessed: changes.length 
            });
            
        } catch (error) {
            console.error('Initial sync failed:', error);
            this.emitSyncEvent('sync-error', { type: 'initial', error });
        }
    }

    async syncData(dataSpec) {
        const syncItem = {
            id: this.generateSyncId(),
            timestamp: Date.now(),
            type: dataSpec.type,
            action: dataSpec.action, // 'create', 'update', 'delete'
            data: dataSpec.data,
            metadata: {
                app: window.__APP_CONFIG__?.name || 'unknown',
                user: await this.getCurrentUserId(),
                version: dataSpec.version || 1
            }
        };

        if (this.isOnline && this.config.syncFrequency === 'realtime') {
            await this.performSync(syncItem);
        } else {
            this.queueSync(syncItem);
        }
    }

    async performSync(syncItem) {
        try {
            this.emitSyncEvent('sync-started', { item: syncItem });

            // Encrypt data if enabled
            if (this.encryptionManager) {
                syncItem.data = await this.encryptionManager.encrypt(syncItem.data);
                syncItem.encrypted = true;
            }

            // Send to sync manager
            const result = await this.syncManager.sync(syncItem);

            // Handle conflicts
            if (result.conflict) {
                const resolution = await this.conflictResolver.resolve(
                    syncItem.data,
                    result.serverData,
                    syncItem.metadata
                );
                
                if (resolution.requiresManualResolution) {
                    this.emitSyncEvent('conflict-requires-resolution', {
                        local: syncItem.data,
                        server: result.serverData,
                        resolution
                    });
                    return;
                }

                // Apply automatic resolution
                syncItem.data = resolution.resolved;
                await this.syncManager.sync(syncItem);
            }

            this.emitSyncEvent('sync-completed', { item: syncItem, result });
            
        } catch (error) {
            console.error('Sync failed:', error);
            this.emitSyncEvent('sync-error', { item: syncItem, error });
            
            if (this.config.offlineSupport) {
                this.queueSync(syncItem);
            }
        }
    }

    queueSync(syncItem) {
        this.syncQueue.push(syncItem);
        this.persistSyncQueue();
        
        this.emitSyncEvent('sync-queued', { item: syncItem });
        console.log(`Sync queued: ${syncItem.type} - ${syncItem.action}`);
    }

    async processSyncQueue() {
        if (!this.isOnline || this.syncQueue.length === 0) return;

        this.emitSyncEvent('queue-processing-started', { 
            queueSize: this.syncQueue.length 
        });

        const processed = [];
        const failed = [];

        for (const item of this.syncQueue) {
            try {
                await this.performSync(item);
                processed.push(item);
            } catch (error) {
                console.error('Queue item sync failed:', error);
                failed.push({ item, error });
            }
        }

        // Remove successfully processed items
        this.syncQueue = this.syncQueue.filter(item => 
            !processed.find(p => p.id === item.id)
        );

        this.persistSyncQueue();

        this.emitSyncEvent('queue-processing-completed', {
            processed: processed.length,
            failed: failed.length,
            remaining: this.syncQueue.length
        });
    }

    async handleDataChange(changeEvent) {
        const { type, action, data, options = {} } = changeEvent;

        if (!this.shouldSync(type, options)) {
            return;
        }

        await this.syncData({
            type,
            action,
            data,
            version: options.version,
            priority: options.priority || 'normal'
        });
    }

    shouldSync(dataType, options) {
        // Check if this data type should be synced
        const syncConfig = this.config.syncRules || {};
        const typeConfig = syncConfig[dataType];

        if (typeConfig === false) return false;
        if (options.noSync) return false;
        if (options.localOnly) return false;

        return true;
    }

    async handleShareRequest(shareRequest) {
        if (!this.config.crossAppSharing) {
            throw new Error('Cross-app sharing not enabled');
        }

        const { targetApp, dataType, data, permissions } = shareRequest;

        try {
            const shareToken = await this.createShareToken(data, permissions);
            
            const shareData = {
                id: this.generateSyncId(),
                sourceApp: window.__APP_CONFIG__?.name,
                targetApp,
                dataType,
                data,
                shareToken,
                permissions,
                createdAt: Date.now(),
                expiresAt: Date.now() + (permissions.duration || 24 * 60 * 60 * 1000)
            };

            await this.syncManager.shareData(shareData);
            
            this.emitSyncEvent('data-shared', { shareData });
            
            return shareToken;

        } catch (error) {
            console.error('Data sharing failed:', error);
            this.emitSyncEvent('share-error', { shareRequest, error });
            throw error;
        }
    }

    async accessSharedData(shareToken) {
        if (!this.config.crossAppSharing) {
            throw new Error('Cross-app sharing not enabled');
        }

        try {
            const sharedData = await this.syncManager.getSharedData(shareToken);
            
            if (!sharedData) {
                throw new Error('Shared data not found or expired');
            }

            // Check permissions
            const currentApp = window.__APP_CONFIG__?.name;
            if (sharedData.targetApp !== currentApp) {
                throw new Error('Access denied for this app');
            }

            // Decrypt if necessary
            let data = sharedData.data;
            if (this.encryptionManager && sharedData.encrypted) {
                data = await this.encryptionManager.decrypt(data);
            }

            this.emitSyncEvent('shared-data-accessed', { sharedData });
            
            return {
                data,
                metadata: {
                    sourceApp: sharedData.sourceApp,
                    dataType: sharedData.dataType,
                    permissions: sharedData.permissions,
                    createdAt: sharedData.createdAt
                }
            };

        } catch (error) {
            console.error('Accessing shared data failed:', error);
            this.emitSyncEvent('shared-access-error', { shareToken, error });
            throw error;
        }
    }

    async createShareToken(data, permissions) {
        const tokenData = {
            timestamp: Date.now(),
            permissions,
            checksum: await this.calculateChecksum(data)
        };

        return btoa(JSON.stringify(tokenData)) + '.' + this.generateSyncId();
    }

    async calculateChecksum(data) {
        const jsonString = JSON.stringify(data);
        const encoder = new TextEncoder();
        const dataBuffer = encoder.encode(jsonString);
        const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    async processChanges(changes) {
        for (const change of changes) {
            try {
                // Decrypt if necessary
                let data = change.data;
                if (this.encryptionManager && change.encrypted) {
                    data = await this.encryptionManager.decrypt(data);
                }

                // Apply change locally
                this.emitSyncEvent('change-received', {
                    type: change.type,
                    action: change.action,
                    data
                });

            } catch (error) {
                console.error('Failed to process change:', error);
                this.emitSyncEvent('change-error', { change, error });
            }
        }
    }

    async getCurrentUserId() {
        try {
            const { default: AuthManager } = await import('@auth/AuthManager.js');
            const user = AuthManager.getCurrentUser();
            return user?.id || 'anonymous';
        } catch (error) {
            return 'anonymous';
        }
    }

    generateSyncId() {
        return `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    async getLastSyncTime() {
        const stored = localStorage.getItem('activelog_last_sync');
        return stored ? parseInt(stored) : 0;
    }

    async setLastSyncTime(timestamp) {
        localStorage.setItem('activelog_last_sync', timestamp.toString());
    }

    persistSyncQueue() {
        try {
            localStorage.setItem('activelog_sync_queue', JSON.stringify(this.syncQueue));
        } catch (error) {
            console.warn('Failed to persist sync queue:', error);
        }
    }

    loadSyncQueue() {
        try {
            const stored = localStorage.getItem('activelog_sync_queue');
            if (stored) {
                this.syncQueue = JSON.parse(stored);
            }
        } catch (error) {
            console.warn('Failed to load sync queue:', error);
            this.syncQueue = [];
        }
    }

    getSyncStatus() {
        return {
            enabled: this.config.enabled,
            online: this.isOnline,
            queueSize: this.syncQueue.length,
            lastSync: this.getLastSyncTime(),
            provider: this.config.cloudProvider,
            encryption: this.config.encryption !== 'none'
        };
    }

    async forceSyncAll() {
        this.emitSyncEvent('full-sync-started');
        
        try {
            await this.syncManager.forceSyncAll();
            await this.setLastSyncTime(Date.now());
            this.emitSyncEvent('full-sync-completed');
        } catch (error) {
            console.error('Full sync failed:', error);
            this.emitSyncEvent('full-sync-error', { error });
            throw error;
        }
    }

    emitSyncEvent(eventName, data = {}) {
        const event = new CustomEvent(`sync:${eventName}`, {
            detail: data
        });
        document.dispatchEvent(event);
    }

    onSyncEvent(eventName, callback) {
        document.addEventListener(`sync:${eventName}`, callback);
    }

    offSyncEvent(eventName, callback) {
        document.removeEventListener(`sync:${eventName}`, callback);
    }

    destroy() {
        if (this.syncManager) {
            this.syncManager.destroy();
        }
        
        this.syncQueue = [];
        this.config = {};
        this.initialized = false;
    }
}

export default DataSync.getInstance();