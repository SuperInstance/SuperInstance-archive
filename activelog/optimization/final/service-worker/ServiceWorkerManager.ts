/**
 * Service Worker Management System
 * Handles registration, updates, communication, and lifecycle management
 */

interface ServiceWorkerConfig {
  swUrl: string;
  scope?: string;
  updateCheckInterval?: number;
  enableBackgroundSync?: boolean;
  enablePushNotifications?: boolean;
  debug?: boolean;
}

interface CacheStats {
  totalSize: number;
  cacheNames: string[];
  entriesCount: Record<string, number>;
}

interface SyncData {
  id: string;
  type: 'file-upload' | 'api-request' | 'user-action';
  data: any;
  timestamp: number;
  retries: number;
}

class ServiceWorkerManager {
  private registration: ServiceWorkerRegistration | null = null;
  private config: Required<ServiceWorkerConfig>;
  private messageChannel: MessageChannel | null = null;
  private updateCheckTimer: NodeJS.Timeout | null = null;
  private pendingSyncData: Map<string, SyncData> = new Map();
  private eventListeners: Map<string, Function[]> = new Map();

  constructor(config: ServiceWorkerConfig) {
    this.config = {
      scope: '/',
      updateCheckInterval: 60000, // 1 minute
      enableBackgroundSync: true,
      enablePushNotifications: false,
      debug: false,
      ...config,
    };

    this.initializeEventListeners();
  }

  /**
   * Initialize Service Worker
   */
  async initialize(): Promise<void> {
    if (!('serviceWorker' in navigator)) {
      throw new Error('Service Worker not supported');
    }

    try {
      this.registration = await navigator.serviceWorker.register(
        this.config.swUrl,
        { scope: this.config.scope }
      );

      this.log('✅ Service Worker registered successfully');
      
      // Setup event listeners
      this.setupRegistrationEventListeners();
      
      // Setup message channel for communication
      this.setupMessageChannel();
      
      // Start update checks
      this.startUpdateChecks();
      
      // Initialize push notifications if enabled
      if (this.config.enablePushNotifications) {
        await this.initializePushNotifications();
      }

      this.emit('initialized', { registration: this.registration });
    } catch (error) {
      this.log('❌ Service Worker registration failed:', error);
      throw error;
    }
  }

  /**
   * Setup event listeners for the registration
   */
  private setupRegistrationEventListeners(): void {
    if (!this.registration) return;

    this.registration.addEventListener('updatefound', () => {
      this.log('🔄 Service Worker update found');
      const newWorker = this.registration!.installing;
      
      if (newWorker) {
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              this.log('📦 New Service Worker installed, waiting for activation');
              this.emit('updateavailable', { newWorker });
            } else {
              this.log('✅ Service Worker installed for the first time');
              this.emit('firstinstall', { newWorker });
            }
          }
        });
      }
    });

    navigator.serviceWorker.addEventListener('controllerchange', () => {
      this.log('🔄 Service Worker controller changed');
      this.emit('controllerchange');
      
      // Reload the page to ensure all assets are from the new service worker
      if (!this.config.debug) {
        window.location.reload();
      }
    });
  }

  /**
   * Setup message channel for two-way communication
   */
  private setupMessageChannel(): void {
    this.messageChannel = new MessageChannel();
    
    this.messageChannel.port1.addEventListener('message', (event) => {
      const { type, payload } = event.data;
      this.handleServiceWorkerMessage(type, payload);
    });
    
    this.messageChannel.port1.start();

    // Send port to service worker
    navigator.serviceWorker.controller?.postMessage(
      { type: 'INIT_PORT' },
      [this.messageChannel.port2]
    );
  }

  /**
   * Handle messages from Service Worker
   */
  private handleServiceWorkerMessage(type: string, payload: any): void {
    switch (type) {
      case 'CACHE_SIZE':
        this.emit('cachesize', payload);
        break;
      case 'CACHE_CLEARED':
        this.emit('cachecleared', { cacheName: payload });
        break;
      case 'SYNC_COMPLETE':
        this.handleSyncComplete(payload);
        break;
      case 'SYNC_FAILED':
        this.handleSyncFailed(payload);
        break;
      default:
        this.log('Unknown message from SW:', type, payload);
    }
  }

  /**
   * Activate waiting Service Worker
   */
  async activateWaitingServiceWorker(): Promise<void> {
    if (!this.registration || !this.registration.waiting) {
      throw new Error('No waiting Service Worker found');
    }

    this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
  }

  /**
   * Check for Service Worker updates
   */
  async checkForUpdates(): Promise<boolean> {
    if (!this.registration) return false;

    try {
      await this.registration.update();
      return !!this.registration.waiting;
    } catch (error) {
      this.log('Update check failed:', error);
      return false;
    }
  }

  /**
   * Start automatic update checks
   */
  private startUpdateChecks(): void {
    if (this.updateCheckTimer) {
      clearInterval(this.updateCheckTimer);
    }

    this.updateCheckTimer = setInterval(
      () => this.checkForUpdates(),
      this.config.updateCheckInterval
    );
  }

  /**
   * Get cache statistics
   */
  async getCacheStats(): Promise<CacheStats> {
    return new Promise((resolve) => {
      if (!this.messageChannel) {
        resolve({ totalSize: 0, cacheNames: [], entriesCount: {} });
        return;
      }

      const handleResponse = (event: MessageEvent) => {
        if (event.data.type === 'CACHE_SIZE') {
          this.messageChannel!.port1.removeEventListener('message', handleResponse);
          resolve(event.data.payload);
        }
      };

      this.messageChannel.port1.addEventListener('message', handleResponse);
      navigator.serviceWorker.controller?.postMessage({ type: 'GET_CACHE_SIZE' });
    });
  }

  /**
   * Clear specific cache
   */
  async clearCache(cacheName: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.messageChannel) {
        reject(new Error('Message channel not available'));
        return;
      }

      const handleResponse = (event: MessageEvent) => {
        if (event.data.type === 'CACHE_CLEARED') {
          this.messageChannel!.port1.removeEventListener('message', handleResponse);
          resolve();
        }
      };

      this.messageChannel.port1.addEventListener('message', handleResponse);
      navigator.serviceWorker.controller?.postMessage({
        type: 'CLEAR_CACHE',
        payload: { cacheName }
      });
    });
  }

  /**
   * Preload routes for faster navigation
   */
  async preloadRoutes(routes: string[]): Promise<void> {
    navigator.serviceWorker.controller?.postMessage({
      type: 'PRELOAD_ROUTES',
      payload: { routes }
    });
  }

  /**
   * Initialize push notifications
   */
  async initializePushNotifications(): Promise<void> {
    if (!('Notification' in window) || !('PushManager' in window)) {
      throw new Error('Push notifications not supported');
    }

    // Request permission
    const permission = await Notification.requestPermission();
    
    if (permission !== 'granted') {
      throw new Error('Push notification permission denied');
    }

    // Get push subscription
    const subscription = await this.registration?.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: await this.getVAPIDKey()
    });

    if (subscription) {
      await this.sendSubscriptionToServer(subscription);
      this.log('✅ Push notifications initialized');
      this.emit('pushinitialized', { subscription });
    }
  }

  /**
   * Schedule background sync
   */
  async scheduleSync(syncData: Omit<SyncData, 'id' | 'timestamp' | 'retries'>): Promise<string> {
    if (!this.config.enableBackgroundSync) {
      throw new Error('Background sync not enabled');
    }

    const id = this.generateId();
    const data: SyncData = {
      id,
      timestamp: Date.now(),
      retries: 0,
      ...syncData
    };

    this.pendingSyncData.set(id, data);

    // Try to register background sync
    try {
      await this.registration?.sync.register(syncData.type);
      this.log('📤 Background sync scheduled:', syncData.type);
    } catch (error) {
      // Fallback: try to sync immediately
      this.log('Background sync not available, attempting immediate sync');
      await this.performImmediateSync(data);
    }

    return id;
  }

  /**
   * Handle sync completion
   */
  private handleSyncComplete(payload: any): void {
    const syncData = this.pendingSyncData.get(payload.id);
    if (syncData) {
      this.pendingSyncData.delete(payload.id);
      this.emit('synccomplete', { syncData, result: payload });
    }
  }

  /**
   * Handle sync failure
   */
  private handleSyncFailed(payload: any): void {
    const syncData = this.pendingSyncData.get(payload.id);
    if (syncData) {
      syncData.retries++;
      
      if (syncData.retries < 3) {
        // Retry sync
        setTimeout(() => {
          this.performImmediateSync(syncData);
        }, 1000 * syncData.retries);
      } else {
        // Give up after 3 retries
        this.pendingSyncData.delete(payload.id);
        this.emit('syncfailed', { syncData, error: payload.error });
      }
    }
  }

  /**
   * Perform immediate sync (fallback when background sync unavailable)
   */
  private async performImmediateSync(syncData: SyncData): Promise<void> {
    try {
      switch (syncData.type) {
        case 'api-request':
          await this.performApiRequest(syncData.data);
          break;
        case 'file-upload':
          await this.performFileUpload(syncData.data);
          break;
        case 'user-action':
          await this.performUserAction(syncData.data);
          break;
      }
      
      this.handleSyncComplete({ id: syncData.id });
    } catch (error) {
      this.handleSyncFailed({ id: syncData.id, error: (error as Error).message });
    }
  }

  /**
   * Perform API request sync
   */
  private async performApiRequest(data: any): Promise<void> {
    const response = await fetch(data.url, {
      method: data.method,
      headers: data.headers,
      body: data.body
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
  }

  /**
   * Perform file upload sync
   */
  private async performFileUpload(data: any): Promise<void> {
    const formData = new FormData();
    formData.append('file', data.file);
    
    if (data.metadata) {
      formData.append('metadata', JSON.stringify(data.metadata));
    }

    const response = await fetch('/api/files/upload', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`File upload failed: ${response.status}`);
    }
  }

  /**
   * Perform user action sync
   */
  private async performUserAction(data: any): Promise<void> {
    const { action, payload } = data;
    
    const response = await fetch(`/api/actions/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`User action failed: ${response.status}`);
    }
  }

  /**
   * Event system methods
   */
  on(event: string, callback: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(callback);
  }

  off(event: string, callback: Function): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit(event: string, data?: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => callback(data));
    }
  }

  /**
   * Initialize default event listeners
   */
  private initializeEventListeners(): void {
    // Online/offline detection
    window.addEventListener('online', () => {
      this.log('🌐 Back online');
      this.emit('online');
      this.retryFailedSyncs();
    });

    window.addEventListener('offline', () => {
      this.log('📴 Gone offline');
      this.emit('offline');
    });

    // Page visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        this.checkForUpdates();
      }
    });
  }

  /**
   * Retry failed syncs when coming back online
   */
  private retryFailedSyncs(): void {
    this.pendingSyncData.forEach((syncData) => {
      if (syncData.retries > 0) {
        this.performImmediateSync(syncData);
      }
    });
  }

  /**
   * Get VAPID key for push notifications
   */
  private async getVAPIDKey(): Promise<Uint8Array> {
    // This would typically be fetched from your server
    const response = await fetch('/api/vapid-key');
    const { publicKey } = await response.json();
    
    return this.urlBase64ToUint8Array(publicKey);
  }

  /**
   * Convert URL-safe base64 to Uint8Array
   */
  private urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
  }

  /**
   * Send push subscription to server
   */
  private async sendSubscriptionToServer(subscription: PushSubscription): Promise<void> {
    await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subscription)
    });
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
  }

  /**
   * Logging utility
   */
  private log(...args: any[]): void {
    if (this.config.debug) {
      console.log('[ServiceWorkerManager]', ...args);
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.updateCheckTimer) {
      clearInterval(this.updateCheckTimer);
      this.updateCheckTimer = null;
    }

    if (this.messageChannel) {
      this.messageChannel.port1.close();
      this.messageChannel = null;
    }

    this.eventListeners.clear();
    this.pendingSyncData.clear();
  }

  /**
   * Get current status
   */
  getStatus(): {
    isRegistered: boolean;
    hasWaiting: boolean;
    isOnline: boolean;
    pendingSyncCount: number;
  } {
    return {
      isRegistered: !!this.registration,
      hasWaiting: !!this.registration?.waiting,
      isOnline: navigator.onLine,
      pendingSyncCount: this.pendingSyncData.size,
    };
  }
}

// React Hook for Service Worker management
export const useServiceWorker = (config: ServiceWorkerConfig) => {
  const [swManager] = React.useState(() => new ServiceWorkerManager(config));
  const [status, setStatus] = React.useState({
    isInitialized: false,
    isOnline: navigator.onLine,
    hasUpdate: false,
    cacheSize: 0,
    error: null as string | null,
  });

  React.useEffect(() => {
    const updateStatus = () => {
      const swStatus = swManager.getStatus();
      setStatus(prev => ({
        ...prev,
        isOnline: navigator.onLine,
        hasUpdate: swStatus.hasWaiting,
      }));
    };

    // Initialize service worker
    swManager.initialize()
      .then(() => {
        setStatus(prev => ({ ...prev, isInitialized: true }));
      })
      .catch((error) => {
        setStatus(prev => ({ ...prev, error: error.message }));
      });

    // Setup event listeners
    swManager.on('updateavailable', () => {
      setStatus(prev => ({ ...prev, hasUpdate: true }));
    });

    swManager.on('online', updateStatus);
    swManager.on('offline', updateStatus);

    return () => swManager.destroy();
  }, [swManager]);

  const activateUpdate = React.useCallback(async () => {
    try {
      await swManager.activateWaitingServiceWorker();
    } catch (error) {
      setStatus(prev => ({ ...prev, error: (error as Error).message }));
    }
  }, [swManager]);

  const clearCache = React.useCallback(async (cacheName: string) => {
    try {
      await swManager.clearCache(cacheName);
    } catch (error) {
      setStatus(prev => ({ ...prev, error: (error as Error).message }));
    }
  }, [swManager]);

  const scheduleSync = React.useCallback(async (
    type: SyncData['type'],
    data: any
  ) => {
    try {
      return await swManager.scheduleSync({ type, data });
    } catch (error) {
      setStatus(prev => ({ ...prev, error: (error as Error).message }));
      throw error;
    }
  }, [swManager]);

  return {
    status,
    activateUpdate,
    clearCache,
    scheduleSync,
    manager: swManager,
  };
};

export default ServiceWorkerManager;