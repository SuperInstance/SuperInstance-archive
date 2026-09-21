export class SyncManager {
    constructor(config) {
        this.config = config;
        this.apiEndpoint = this.getApiEndpoint();
        this.headers = {
            'Content-Type': 'application/json'
        };
    }

    async init() {
        // Initialize authentication headers
        await this.updateAuthHeaders();
        
        // Test connection
        if (navigator.onLine) {
            try {
                await this.testConnection();
                console.log('SyncManager connected to:', this.apiEndpoint);
            } catch (error) {
                console.warn('SyncManager connection test failed:', error);
            }
        }
    }

    getApiEndpoint() {
        const providers = {
            'activelog-cloud': '/api/sync',
            'activelog-cloud-business': '/api/business/sync',
            'activelog-cloud-pro': '/api/pro/sync',
            'activelog-cloud-edu': '/api/edu/sync',
            'activelog-cloud-gaming': '/api/gaming/sync',
            'activelog-cloud-manufacturing': '/api/manufacturing/sync',
            'activelog-cloud-maritime': '/api/maritime/sync'
        };

        return providers[this.config.cloudProvider] || providers['activelog-cloud'];
    }

    async updateAuthHeaders() {
        try {
            const { default: AuthManager } = await import('@auth/AuthManager.js');
            const user = AuthManager.getCurrentUser();
            
            if (user) {
                const token = await AuthManager.tokenManager.getValidToken();
                this.headers['Authorization'] = `Bearer ${token}`;
            }
        } catch (error) {
            console.warn('Failed to update auth headers:', error);
        }
    }

    async testConnection() {
        const response = await fetch(`${this.apiEndpoint}/health`, {
            method: 'GET',
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`Connection test failed: ${response.status}`);
        }

        return response.json();
    }

    async sync(syncItem) {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/items`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(syncItem)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Sync failed' }));
            throw new Error(error.message || `Sync failed: ${response.status}`);
        }

        const result = await response.json();
        
        // Handle conflicts
        if (result.status === 'conflict') {
            return {
                conflict: true,
                serverData: result.serverData,
                conflictInfo: result.conflictInfo
            };
        }

        return {
            success: true,
            syncId: result.syncId,
            timestamp: result.timestamp,
            version: result.version
        };
    }

    async getChanges(since) {
        await this.updateAuthHeaders();

        const params = new URLSearchParams();
        if (since) {
            params.append('since', since.toString());
        }

        const response = await fetch(`${this.apiEndpoint}/changes?${params}`, {
            method: 'GET',
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`Failed to get changes: ${response.status}`);
        }

        const result = await response.json();
        return result.changes || [];
    }

    async shareData(shareData) {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/share`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(shareData)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Share failed' }));
            throw new Error(error.message || `Share failed: ${response.status}`);
        }

        return response.json();
    }

    async getSharedData(shareToken) {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/shared/${shareToken}`, {
            method: 'GET',
            headers: this.headers
        });

        if (response.status === 404) {
            return null; // Share not found or expired
        }

        if (!response.ok) {
            throw new Error(`Failed to get shared data: ${response.status}`);
        }

        return response.json();
    }

    async forceSyncAll() {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/sync-all`, {
            method: 'POST',
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`Full sync failed: ${response.status}`);
        }

        return response.json();
    }

    async deleteData(dataType, dataId) {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/items/${dataType}/${dataId}`, {
            method: 'DELETE',
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`Delete failed: ${response.status}`);
        }

        return response.json();
    }

    async getData(dataType, options = {}) {
        await this.updateAuthHeaders();

        const params = new URLSearchParams();
        if (options.limit) params.append('limit', options.limit.toString());
        if (options.offset) params.append('offset', options.offset.toString());
        if (options.filter) params.append('filter', JSON.stringify(options.filter));
        if (options.sort) params.append('sort', options.sort);

        const response = await fetch(
            `${this.apiEndpoint}/items/${dataType}?${params}`,
            {
                method: 'GET',
                headers: this.headers
            }
        );

        if (!response.ok) {
            throw new Error(`Get data failed: ${response.status}`);
        }

        return response.json();
    }

    async getSyncHistory(options = {}) {
        await this.updateAuthHeaders();

        const params = new URLSearchParams();
        if (options.limit) params.append('limit', options.limit.toString());
        if (options.since) params.append('since', options.since.toString());
        if (options.type) params.append('type', options.type);

        const response = await fetch(`${this.apiEndpoint}/history?${params}`, {
            method: 'GET',
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`Get sync history failed: ${response.status}`);
        }

        return response.json();
    }

    async resolveConflict(conflictId, resolution) {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/conflicts/${conflictId}`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ resolution })
        });

        if (!response.ok) {
            throw new Error(`Conflict resolution failed: ${response.status}`);
        }

        return response.json();
    }

    async getConflicts() {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/conflicts`, {
            method: 'GET',
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`Get conflicts failed: ${response.status}`);
        }

        return response.json();
    }

    async exportData(options = {}) {
        await this.updateAuthHeaders();

        const params = new URLSearchParams();
        if (options.format) params.append('format', options.format);
        if (options.types) params.append('types', options.types.join(','));
        if (options.since) params.append('since', options.since.toString());
        if (options.until) params.append('until', options.until.toString());

        const response = await fetch(`${this.apiEndpoint}/export?${params}`, {
            method: 'GET',
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`Export failed: ${response.status}`);
        }

        if (options.format === 'json') {
            return response.json();
        } else {
            return response.blob();
        }
    }

    async importData(data, options = {}) {
        await this.updateAuthHeaders();

        const formData = new FormData();
        
        if (data instanceof File || data instanceof Blob) {
            formData.append('file', data);
        } else {
            formData.append('data', JSON.stringify(data));
        }

        if (options.format) {
            formData.append('format', options.format);
        }

        if (options.merge !== undefined) {
            formData.append('merge', options.merge.toString());
        }

        const headers = { ...this.headers };
        delete headers['Content-Type']; // Let browser set multipart headers

        const response = await fetch(`${this.apiEndpoint}/import`, {
            method: 'POST',
            headers,
            body: formData
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Import failed' }));
            throw new Error(error.message || `Import failed: ${response.status}`);
        }

        return response.json();
    }

    async getStorageUsage() {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/usage`, {
            method: 'GET',
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`Get storage usage failed: ${response.status}`);
        }

        return response.json();
    }

    async cleanup(options = {}) {
        await this.updateAuthHeaders();

        const response = await fetch(`${this.apiEndpoint}/cleanup`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(options)
        });

        if (!response.ok) {
            throw new Error(`Cleanup failed: ${response.status}`);
        }

        return response.json();
    }

    destroy() {
        this.headers = {};
        this.config = null;
    }
}