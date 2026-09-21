import React, { useState, useEffect } from 'react';
import Dexie, { Table } from 'dexie';
import { Service } from '@/types/service';
import { Notification } from '@/services/webSocketService';
import { MicroFrontend } from '@/types/microfrontend';

// Database schema for offline storage
interface CachedData {
  id: string;
  type: 'service' | 'notification' | 'user_data' | 'app_state';
  data: any;
  lastUpdated: Date;
  expiresAt?: Date;
  syncStatus: 'pending' | 'synced' | 'conflict' | 'error';
  version: number;
}

interface SyncOperation {
  id: string;
  operation: 'create' | 'update' | 'delete';
  entity: string;
  entityId: string;
  data: any;
  timestamp: Date;
  retries: number;
  status: 'pending' | 'completed' | 'failed';
}

interface OfflineCapability {
  serviceId: string;
  capabilities: string[];
  cacheStrategy: 'aggressive' | 'selective' | 'minimal';
  maxCacheSize: number; // in MB
  syncFrequency: number; // in minutes
}

class OfflineDatabase extends Dexie {
  cachedData!: Table<CachedData>;
  syncOperations!: Table<SyncOperation>;
  offlineCapabilities!: Table<OfflineCapability>;

  constructor() {
    super('ActiveLogOfflineDB');
    
    this.version(1).stores({
      cachedData: 'id, type, lastUpdated, expiresAt, syncStatus',
      syncOperations: 'id, operation, entity, entityId, timestamp, status',
      offlineCapabilities: 'serviceId, cacheStrategy'
    });
  }
}

export class OfflineService {
  private db: OfflineDatabase;
  private syncQueue: SyncOperation[] = [];
  private isOnline = navigator.onLine;
  private syncInterval: NodeJS.Timeout | null = null;
  private readonly SYNC_INTERVAL = 30000; // 30 seconds
  private readonly MAX_CACHE_AGE = 24 * 60 * 60 * 1000; // 24 hours
  private readonly MAX_RETRIES = 3;

  constructor() {
    this.db = new OfflineDatabase();
    this.initialize();
  }

  // Initialize offline service
  private initialize() {
    // Listen for online/offline events
    window.addEventListener('online', this.handleOnline.bind(this));
    window.addEventListener('offline', this.handleOffline.bind(this));

    // Start sync process if online
    if (this.isOnline) {
      this.startSyncProcess();
    }

    // Setup service worker for background sync
    this.registerServiceWorker();
  }

  // Handle online event
  private handleOnline() {
    console.log('App is back online');
    this.isOnline = true;
    this.startSyncProcess();
    this.notifyOnlineStatus(true);
  }

  // Handle offline event
  private handleOffline() {
    console.log('App is now offline');
    this.isOnline = false;
    this.stopSyncProcess();
    this.notifyOnlineStatus(false);
  }

  // Cache data for offline access
  async cacheData(type: CachedData['type'], id: string, data: any, expiresIn?: number): Promise<void> {
    try {
      const cachedItem: CachedData = {
        id: `${type}_${id}`,
        type,
        data,
        lastUpdated: new Date(),
        expiresAt: expiresIn ? new Date(Date.now() + expiresIn) : undefined,
        syncStatus: 'synced',
        version: 1
      };

      await this.db.cachedData.put(cachedItem);
    } catch (error) {
      console.error('Failed to cache data:', error);
    }
  }

  // Retrieve cached data
  async getCachedData(type: CachedData['type'], id: string): Promise<any | null> {
    try {
      const cached = await this.db.cachedData.get(`${type}_${id}`);
      
      if (!cached) return null;
      
      // Check if expired
      if (cached.expiresAt && cached.expiresAt < new Date()) {
        await this.db.cachedData.delete(`${type}_${id}`);
        return null;
      }

      return cached.data;
    } catch (error) {
      console.error('Failed to retrieve cached data:', error);
      return null;
    }
  }

  // Cache services for offline access
  async cacheServices(services: Service[]): Promise<void> {
    try {
      for (const service of services) {
        await this.cacheData('service', service.id, service, this.MAX_CACHE_AGE);
      }
    } catch (error) {
      console.error('Failed to cache services:', error);
    }
  }

  // Get cached services
  async getCachedServices(): Promise<Service[]> {
    try {
      const cachedServices = await this.db.cachedData
        .where('type')
        .equals('service')
        .toArray();

      return cachedServices.map(item => item.data as Service);
    } catch (error) {
      console.error('Failed to get cached services:', error);
      return [];
    }
  }

  // Cache notifications for offline access
  async cacheNotification(notification: Notification): Promise<void> {
    await this.cacheData('notification', notification.id, notification, this.MAX_CACHE_AGE);
  }

  // Get cached notifications
  async getCachedNotifications(): Promise<Notification[]> {
    try {
      const cachedNotifications = await this.db.cachedData
        .where('type')
        .equals('notification')
        .toArray();

      return cachedNotifications.map(item => item.data as Notification);
    } catch (error) {
      console.error('Failed to get cached notifications:', error);
      return [];
    }
  }

  // Queue operation for sync when online
  async queueSyncOperation(
    operation: SyncOperation['operation'],
    entity: string,
    entityId: string,
    data: any
  ): Promise<void> {
    try {
      const syncOp: SyncOperation = {
        id: `${operation}_${entity}_${entityId}_${Date.now()}`,
        operation,
        entity,
        entityId,
        data,
        timestamp: new Date(),
        retries: 0,
        status: 'pending'
      };

      await this.db.syncOperations.add(syncOp);
      this.syncQueue.push(syncOp);

      // If online, try to sync immediately
      if (this.isOnline) {
        this.processSyncQueue();
      }
    } catch (error) {
      console.error('Failed to queue sync operation:', error);
    }
  }

  // Start sync process
  private startSyncProcess() {
    if (this.syncInterval) return;

    this.syncInterval = setInterval(() => {
      this.processSyncQueue();
    }, this.SYNC_INTERVAL);

    // Process immediately
    this.processSyncQueue();
  }

  // Stop sync process
  private stopSyncProcess() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  // Process sync queue
  private async processSyncQueue() {
    if (!this.isOnline) return;

    try {
      const pendingOps = await this.db.syncOperations
        .where('status')
        .equals('pending')
        .toArray();

      for (const op of pendingOps) {
        await this.processSyncOperation(op);
      }
    } catch (error) {
      console.error('Failed to process sync queue:', error);
    }
  }

  // Process individual sync operation
  private async processSyncOperation(operation: SyncOperation): Promise<void> {
    try {
      const apiUrl = this.getApiUrlForEntity(operation.entity);
      let response: Response;

      switch (operation.operation) {
        case 'create':
          response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(operation.data)
          });
          break;

        case 'update':
          response = await fetch(`${apiUrl}/${operation.entityId}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(operation.data)
          });
          break;

        case 'delete':
          response = await fetch(`${apiUrl}/${operation.entityId}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
          });
          break;

        default:
          throw new Error(`Unknown operation: ${operation.operation}`);
      }

      if (response.ok) {
        // Mark as completed
        await this.db.syncOperations.update(operation.id, {
          status: 'completed'
        });
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error(`Failed to sync operation ${operation.id}:`, error);
      
      // Increment retry count
      const newRetries = operation.retries + 1;
      
      if (newRetries >= this.MAX_RETRIES) {
        // Mark as failed after max retries
        await this.db.syncOperations.update(operation.id, {
          status: 'failed',
          retries: newRetries
        });
      } else {
        // Retry later
        await this.db.syncOperations.update(operation.id, {
          retries: newRetries
        });
      }
    }
  }

  // Get API URL for entity type
  private getApiUrlForEntity(entity: string): string {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    
    switch (entity) {
      case 'notification':
        return `${baseUrl}/api/notifications`;
      case 'user_data':
        return `${baseUrl}/api/user-data`;
      case 'service':
        return `${baseUrl}/api/services`;
      default:
        return `${baseUrl}/api/${entity}`;
    }
  }

  // Configure offline capabilities for a service
  async configureOfflineCapabilities(capability: OfflineCapability): Promise<void> {
    try {
      await this.db.offlineCapabilities.put(capability);
    } catch (error) {
      console.error('Failed to configure offline capabilities:', error);
    }
  }

  // Get offline capabilities for a service
  async getOfflineCapabilities(serviceId: string): Promise<OfflineCapability | undefined> {
    try {
      return await this.db.offlineCapabilities.get(serviceId);
    } catch (error) {
      console.error('Failed to get offline capabilities:', error);
      return undefined;
    }
  }

  // Clear expired cache
  async clearExpiredCache(): Promise<void> {
    try {
      const now = new Date();
      await this.db.cachedData
        .where('expiresAt')
        .below(now)
        .delete();
    } catch (error) {
      console.error('Failed to clear expired cache:', error);
    }
  }

  // Get cache size
  async getCacheSize(): Promise<{ count: number; sizeEstimate: string }> {
    try {
      const count = await this.db.cachedData.count();
      const items = await this.db.cachedData.toArray();
      const sizeBytes = JSON.stringify(items).length;
      const sizeMB = (sizeBytes / (1024 * 1024)).toFixed(2);
      
      return {
        count,
        sizeEstimate: `${sizeMB} MB`
      };
    } catch (error) {
      console.error('Failed to calculate cache size:', error);
      return { count: 0, sizeEstimate: '0 MB' };
    }
  }

  // Clear all cache
  async clearAllCache(): Promise<void> {
    try {
      await this.db.cachedData.clear();
    } catch (error) {
      console.error('Failed to clear cache:', error);
    }
  }

  // Get sync status
  async getSyncStatus(): Promise<{
    pending: number;
    completed: number;
    failed: number;
  }> {
    try {
      const [pending, completed, failed] = await Promise.all([
        this.db.syncOperations.where('status').equals('pending').count(),
        this.db.syncOperations.where('status').equals('completed').count(),
        this.db.syncOperations.where('status').equals('failed').count()
      ]);

      return { pending, completed, failed };
    } catch (error) {
      console.error('Failed to get sync status:', error);
      return { pending: 0, completed: 0, failed: 0 };
    }
  }

  // Register service worker for background sync
  private async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.log('Service worker registered:', registration);
      } catch (error) {
        console.error('Service worker registration failed:', error);
      }
    }
  }

  // Notify online status change
  private notifyOnlineStatus(online: boolean) {
    window.dispatchEvent(new CustomEvent('online-status-change', {
      detail: { online }
    }));
  }

  // Check if online
  isOnlineStatus(): boolean {
    return this.isOnline;
  }

  // Force sync
  async forceSync(): Promise<void> {
    if (this.isOnline) {
      await this.processSyncQueue();
    }
  }

  // Cleanup old completed sync operations
  async cleanupSyncOperations(): Promise<void> {
    try {
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
      await this.db.syncOperations
        .where('timestamp')
        .below(oneDayAgo)
        .and(item => item.status === 'completed')
        .delete();
    } catch (error) {
      console.error('Failed to cleanup sync operations:', error);
    }
  }
}

// Global offline service instance
export const offlineService = new OfflineService();

// React hook for offline functionality
export function useOffline() {
  const [isOnline, setIsOnline] = useState(offlineService.isOnlineStatus());
  const [syncStatus, setSyncStatus] = useState({ pending: 0, completed: 0, failed: 0 });

  useEffect(() => {
    const handleStatusChange = (event: CustomEvent) => {
      setIsOnline(event.detail.online);
    };

    window.addEventListener('online-status-change', handleStatusChange as EventListener);

    // Update sync status periodically
    const updateSyncStatus = async () => {
      const status = await offlineService.getSyncStatus();
      setSyncStatus(status);
    };

    updateSyncStatus();
    const interval = setInterval(updateSyncStatus, 10000);

    return () => {
      window.removeEventListener('online-status-change', handleStatusChange as EventListener);
      clearInterval(interval);
    };
  }, []);

  return {
    isOnline,
    syncStatus,
    cacheData: offlineService.cacheData.bind(offlineService),
    getCachedData: offlineService.getCachedData.bind(offlineService),
    queueSyncOperation: offlineService.queueSyncOperation.bind(offlineService),
    forceSync: offlineService.forceSync.bind(offlineService),
    clearCache: offlineService.clearAllCache.bind(offlineService),
    getCacheSize: offlineService.getCacheSize.bind(offlineService)
  };
}