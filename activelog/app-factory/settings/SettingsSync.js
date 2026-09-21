export class SettingsSync {
    constructor() {
        this.settings = new Map();
        this.syncEnabled = true;
        this.encryptionEnabled = false;
        this.crossAppEnabled = true;
        this.localStorageKey = 'activelog_settings';
        this.syncEndpoint = '/api/settings';
        this.initialized = false;
        this.syncQueue = [];
        this.isOnline = navigator.onLine;
    }

    static instance = null;

    static getInstance() {
        if (!SettingsSync.instance) {
            SettingsSync.instance = new SettingsSync();
        }
        return SettingsSync.instance;
    }

    async init(config = {}) {
        if (this.initialized) return;

        this.config = {
            syncEnabled: true,
            encryptionEnabled: false,
            crossAppEnabled: true,
            autoSync: true,
            syncInterval: 30000, // 30 seconds
            conflictResolution: 'merge',
            ...config
        };

        this.syncEnabled = this.config.syncEnabled;
        this.encryptionEnabled = this.config.encryptionEnabled;
        this.crossAppEnabled = this.config.crossAppEnabled;

        await this.loadSettings();
        this.setupEventListeners();
        
        if (this.config.autoSync) {
            this.startAutoSync();
        }

        this.initialized = true;
        console.log('SettingsSync initialized');
    }

    async loadSettings() {
        try {
            // Load from local storage first
            await this.loadLocalSettings();
            
            // Then sync from server if online
            if (this.isOnline && this.syncEnabled) {
                await this.syncFromServer();
            }
            
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    async loadLocalSettings() {
        try {
            const stored = localStorage.getItem(this.localStorageKey);
            if (stored) {
                const data = JSON.parse(stored);
                
                if (this.encryptionEnabled && data.encrypted) {
                    const decrypted = await this.decrypt(data.settings);
                    this.settings = new Map(Object.entries(decrypted));
                } else {
                    this.settings = new Map(Object.entries(data.settings || {}));
                }
                
                console.log('Settings loaded from local storage');
            }
        } catch (error) {
            console.error('Failed to load local settings:', error);
            this.settings = new Map();
        }
    }

    async syncFromServer() {
        try {
            const response = await this.makeAuthenticatedRequest('GET', this.syncEndpoint);
            
            if (response.ok) {
                const serverSettings = await response.json();
                await this.mergeSettings(serverSettings);
                console.log('Settings synced from server');
            }
            
        } catch (error) {
            console.error('Failed to sync settings from server:', error);
        }
    }

    async mergeSettings(serverSettings) {
        const localTimestamp = this.get('_lastModified', 0);
        const serverTimestamp = serverSettings._lastModified || 0;

        if (serverTimestamp > localTimestamp) {
            // Server has newer settings
            for (const [key, value] of Object.entries(serverSettings)) {
                if (key !== '_lastModified') {
                    this.settings.set(key, value);
                }
            }
            this.settings.set('_lastModified', serverTimestamp);
            await this.saveLocal();
            
            this.emitSettingsEvent('settings-synced', { source: 'server' });
        } else if (localTimestamp > serverTimestamp) {
            // Local has newer settings - push to server
            await this.syncToServer();
        }
    }

    get(key, defaultValue = null) {
        return this.settings.get(key) ?? defaultValue;
    }

    async set(key, value, options = {}) {
        const oldValue = this.settings.get(key);
        
        if (oldValue === value) {
            return; // No change
        }

        this.settings.set(key, value);
        this.settings.set('_lastModified', Date.now());

        // Save locally
        await this.saveLocal();

        // Emit change event
        this.emitSettingsEvent('setting-changed', {
            key,
            value,
            oldValue,
            options
        });

        // Queue for sync if enabled
        if (this.syncEnabled && !options.noSync) {
            this.queueSync(key, value, options);
        }

        console.log(`Setting updated: ${key} =`, value);
    }

    async setMultiple(settingsObject, options = {}) {
        const changes = [];

        for (const [key, value] of Object.entries(settingsObject)) {
            const oldValue = this.settings.get(key);
            if (oldValue !== value) {
                this.settings.set(key, value);
                changes.push({ key, value, oldValue });
            }
        }

        if (changes.length === 0) {
            return; // No changes
        }

        this.settings.set('_lastModified', Date.now());
        await this.saveLocal();

        // Emit events for all changes
        changes.forEach(change => {
            this.emitSettingsEvent('setting-changed', {
                ...change,
                options
            });
        });

        this.emitSettingsEvent('settings-batch-changed', {
            changes,
            options
        });

        // Queue for sync
        if (this.syncEnabled && !options.noSync) {
            this.queueBatchSync(settingsObject, options);
        }
    }

    async remove(key, options = {}) {
        if (!this.settings.has(key)) {
            return;
        }

        const oldValue = this.settings.get(key);
        this.settings.delete(key);
        this.settings.set('_lastModified', Date.now());

        await this.saveLocal();

        this.emitSettingsEvent('setting-removed', {
            key,
            oldValue,
            options
        });

        if (this.syncEnabled && !options.noSync) {
            this.queueSync(key, null, { ...options, deleted: true });
        }
    }

    async clear(options = {}) {
        const oldSettings = new Map(this.settings);
        this.settings.clear();
        this.settings.set('_lastModified', Date.now());

        await this.saveLocal();

        this.emitSettingsEvent('settings-cleared', {
            oldSettings,
            options
        });

        if (this.syncEnabled && !options.noSync) {
            await this.syncToServer();
        }
    }

    has(key) {
        return this.settings.has(key);
    }

    keys() {
        return Array.from(this.settings.keys()).filter(key => key !== '_lastModified');
    }

    values() {
        const result = {};
        for (const [key, value] of this.settings) {
            if (key !== '_lastModified') {
                result[key] = value;
            }
        }
        return result;
    }

    async saveLocal() {
        try {
            const settingsObject = Object.fromEntries(this.settings);
            
            let dataToStore = { settings: settingsObject };
            
            if (this.encryptionEnabled) {
                const encrypted = await this.encrypt(settingsObject);
                dataToStore = {
                    settings: encrypted,
                    encrypted: true
                };
            }

            localStorage.setItem(this.localStorageKey, JSON.stringify(dataToStore));
            
        } catch (error) {
            console.error('Failed to save settings locally:', error);
        }
    }

    queueSync(key, value, options = {}) {
        const syncItem = {
            id: `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            key,
            value,
            timestamp: Date.now(),
            options
        };

        this.syncQueue.push(syncItem);
        this.processyncQueue();
    }

    queueBatchSync(settingsObject, options = {}) {
        const syncItem = {
            id: `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            batch: settingsObject,
            timestamp: Date.now(),
            options
        };

        this.syncQueue.push(syncItem);
        this.processyncQueue();
    }

    async processyncQueue() {
        if (!this.isOnline || this.syncQueue.length === 0) {
            return;
        }

        // Debounce rapid changes
        clearTimeout(this.syncTimeout);
        this.syncTimeout = setTimeout(async () => {
            await this.syncToServer();
        }, 1000);
    }

    async syncToServer() {
        if (!this.isOnline || !this.syncEnabled) {
            return;
        }

        try {
            const settingsToSync = Object.fromEntries(this.settings);
            
            const response = await this.makeAuthenticatedRequest('PUT', this.syncEndpoint, {
                settings: settingsToSync,
                timestamp: Date.now()
            });

            if (response.ok) {
                this.syncQueue = []; // Clear queue on successful sync
                this.emitSettingsEvent('settings-synced', { source: 'local' });
                console.log('Settings synced to server');
            } else {
                throw new Error(`Sync failed: ${response.status}`);
            }

        } catch (error) {
            console.error('Failed to sync settings to server:', error);
            this.emitSettingsEvent('sync-error', { error });
        }
    }

    async shareSettings(targetApp, settingsKeys, permissions = {}) {
        if (!this.crossAppEnabled) {
            throw new Error('Cross-app settings sharing not enabled');
        }

        const settingsToShare = {};
        settingsKeys.forEach(key => {
            if (this.settings.has(key)) {
                settingsToShare[key] = this.settings.get(key);
            }
        });

        try {
            const response = await this.makeAuthenticatedRequest('POST', `${this.syncEndpoint}/share`, {
                targetApp,
                settings: settingsToShare,
                permissions: {
                    read: true,
                    write: false,
                    duration: 24 * 60 * 60 * 1000, // 24 hours
                    ...permissions
                }
            });

            if (!response.ok) {
                throw new Error(`Settings sharing failed: ${response.status}`);
            }

            const result = await response.json();
            this.emitSettingsEvent('settings-shared', {
                targetApp,
                settingsKeys,
                shareToken: result.shareToken
            });

            return result.shareToken;

        } catch (error) {
            console.error('Failed to share settings:', error);
            throw error;
        }
    }

    async accessSharedSettings(shareToken) {
        if (!this.crossAppEnabled) {
            throw new Error('Cross-app settings sharing not enabled');
        }

        try {
            const response = await this.makeAuthenticatedRequest(
                'GET', 
                `${this.syncEndpoint}/shared/${shareToken}`
            );

            if (!response.ok) {
                throw new Error(`Access shared settings failed: ${response.status}`);
            }

            const sharedData = await response.json();
            
            this.emitSettingsEvent('shared-settings-accessed', {
                sourceApp: sharedData.sourceApp,
                settings: sharedData.settings,
                permissions: sharedData.permissions
            });

            return sharedData;

        } catch (error) {
            console.error('Failed to access shared settings:', error);
            throw error;
        }
    }

    async export(format = 'json', options = {}) {
        const settingsData = {
            settings: this.values(),
            metadata: {
                exportDate: new Date().toISOString(),
                appName: window.__APP_CONFIG__?.name || 'ActiveLog',
                version: window.__APP_CONFIG__?.version || '1.0.0'
            }
        };

        switch (format) {
            case 'json':
                return JSON.stringify(settingsData, null, 2);
            
            case 'csv':
                return this.exportToCSV(settingsData.settings);
            
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }
    }

    exportToCSV(settings) {
        const rows = [['Key', 'Value', 'Type']];
        
        for (const [key, value] of Object.entries(settings)) {
            rows.push([
                key,
                typeof value === 'object' ? JSON.stringify(value) : String(value),
                typeof value
            ]);
        }

        return rows.map(row => 
            row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
        ).join('\n');
    }

    async import(data, format = 'json', options = {}) {
        let settingsData;

        try {
            switch (format) {
                case 'json':
                    const parsed = typeof data === 'string' ? JSON.parse(data) : data;
                    settingsData = parsed.settings || parsed;
                    break;
                
                default:
                    throw new Error(`Unsupported import format: ${format}`);
            }

            if (options.merge) {
                await this.setMultiple(settingsData, { noSync: options.noSync });
            } else {
                await this.clear({ noSync: true });
                await this.setMultiple(settingsData, { noSync: options.noSync });
            }

            this.emitSettingsEvent('settings-imported', {
                format,
                count: Object.keys(settingsData).length,
                options
            });

            console.log(`Settings imported from ${format}`);

        } catch (error) {
            console.error('Failed to import settings:', error);
            throw error;
        }
    }

    setupEventListeners() {
        // Online/offline detection
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.processyncQueue();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
        });

        // Cross-app settings requests
        document.addEventListener('settings:request', (event) => {
            const { key, callback } = event.detail;
            callback(this.get(key));
        });

        document.addEventListener('settings:set', (event) => {
            const { key, value, options } = event.detail;
            this.set(key, value, options);
        });
    }

    startAutoSync() {
        if (this.autoSyncInterval) {
            clearInterval(this.autoSyncInterval);
        }

        this.autoSyncInterval = setInterval(() => {
            if (this.isOnline && this.syncEnabled) {
                this.syncFromServer();
            }
        }, this.config.syncInterval);
    }

    stopAutoSync() {
        if (this.autoSyncInterval) {
            clearInterval(this.autoSyncInterval);
            this.autoSyncInterval = null;
        }
    }

    async makeAuthenticatedRequest(method, endpoint, data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        // Add authentication
        try {
            const { default: AuthManager } = await import('@auth/AuthManager.js');
            const user = AuthManager.getCurrentUser();
            
            if (user) {
                const token = await AuthManager.tokenManager.getValidToken();
                options.headers['Authorization'] = `Bearer ${token}`;
            }
        } catch (error) {
            console.warn('Failed to add auth headers:', error);
        }

        return fetch(endpoint, options);
    }

    async encrypt(data) {
        // Placeholder for encryption implementation
        return btoa(JSON.stringify(data));
    }

    async decrypt(encryptedData) {
        // Placeholder for decryption implementation
        return JSON.parse(atob(encryptedData));
    }

    emitSettingsEvent(eventName, data) {
        const event = new CustomEvent(`settings:${eventName}`, {
            detail: data
        });
        document.dispatchEvent(event);
    }

    onSettingsEvent(eventName, callback) {
        document.addEventListener(`settings:${eventName}`, callback);
    }

    offSettingsEvent(eventName, callback) {
        document.removeEventListener(`settings:${eventName}`, callback);
    }

    getStatus() {
        return {
            initialized: this.initialized,
            syncEnabled: this.syncEnabled,
            online: this.isOnline,
            settingsCount: this.settings.size - 1, // Exclude _lastModified
            queueSize: this.syncQueue.length,
            lastModified: this.get('_lastModified')
        };
    }

    destroy() {
        this.stopAutoSync();
        clearTimeout(this.syncTimeout);
        
        this.settings.clear();
        this.syncQueue = [];
        this.initialized = false;
        
        console.log('SettingsSync destroyed');
    }
}

export default SettingsSync.getInstance();