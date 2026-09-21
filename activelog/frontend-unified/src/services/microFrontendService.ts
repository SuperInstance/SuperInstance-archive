import { 
  MicroFrontend, 
  MicroFrontendStatus, 
  MicroFrontendConfig, 
  MicroFrontendLoadOptions,
  CrossAppMessage,
  LoadingStrategy 
} from '@/types/microfrontend';
import { getMicroFrontendById } from '@/data/microfrontends';

// BOT_EDUCATION: SuperInstance Integration Service
// This service handles cross-domain communication with the SuperInstance backend
// It provides AI-powered features like automated service discovery, intelligent routing,
// and context-aware micro-frontend loading for the $2/month bot assembly platform

interface SuperInstanceConfig {
  apiGatewayUrl: string;
  authServiceUrl: string;
  metadataServiceUrl: string;
  fileSyncServiceUrl: string;
  enableAIFeatures: boolean;
  enableCrossDomainSync: boolean;
}

// SuperInstance configuration - connects to our backend services
const SUPER_INSTANCE_CONFIG: SuperInstanceConfig = {
  apiGatewayUrl: 'http://localhost:8000',
  authServiceUrl: 'http://localhost:8001', 
  metadataServiceUrl: 'http://localhost:8003',
  fileSyncServiceUrl: 'http://localhost:8015',
  enableAIFeatures: true,
  enableCrossDomainSync: true
};

export class MicroFrontendService {
  private static loadedMicroFrontends: Map<string, HTMLIFrameElement> = new Map();
  private static messageHandlers: Map<string, (message: CrossAppMessage) => void> = new Map();
  private static healthCheckIntervals: Map<string, NodeJS.Timeout> = new Map();
  
  // BOT_EDUCATION: SuperInstance AI-powered features
  // These maps store AI context and cross-domain sync state for intelligent service management
  private static aiContextCache: Map<string, any> = new Map();
  private static crossDomainSyncState: Map<string, any> = new Map();
  private static intelligentRoutingCache: Map<string, string> = new Map();

  // Initialize the micro-frontend service
  static initialize() {
    // Listen for messages from micro-frontends
    window.addEventListener('message', this.handleCrossAppMessage);
    
    // Set up periodic health checks
    this.startHealthChecks();
    
    // BOT_EDUCATION: Initialize SuperInstance AI features
    // This connects the frontend to our intelligent backend services
    this.initializeSuperInstanceIntegration();
    
    // Start AI-powered service discovery
    if (SUPER_INSTANCE_CONFIG.enableAIFeatures) {
      this.startIntelligentServiceDiscovery();
    }
    
    // Initialize cross-domain synchronization
    if (SUPER_INSTANCE_CONFIG.enableCrossDomainSync) {
      this.initializeCrossDomainSync();
    }
  }

  // Load a micro-frontend
  static async loadMicroFrontend(
    microFrontendId: string, 
    options: MicroFrontendLoadOptions
  ): Promise<void> {
    const microFrontend = getMicroFrontendById(microFrontendId);
    if (!microFrontend) {
      throw new Error(`Micro-frontend ${microFrontendId} not found`);
    }

    const container = document.getElementById(options.containerId);
    if (!container) {
      throw new Error(`Container ${options.containerId} not found`);
    }

    try {
      // Check if micro-frontend is available
      const isAvailable = await this.checkMicroFrontendHealth(microFrontend);
      if (!isAvailable) {
        throw new Error(`Micro-frontend ${microFrontendId} is not available`);
      }

      // Remove existing micro-frontend if loaded
      this.unloadMicroFrontend(microFrontendId);

      // Load based on strategy
      switch (microFrontend.loadingStrategy) {
        case LoadingStrategy.IFRAME:
          await this.loadViaIFrame(microFrontend, container, options);
          break;
        case LoadingStrategy.MODULE_FEDERATION:
          await this.loadViaModuleFederation(microFrontend, container, options);
          break;
        case LoadingStrategy.DYNAMIC_IMPORT:
          await this.loadViaDynamicImport(microFrontend, container, options);
          break;
        case LoadingStrategy.WEB_COMPONENTS:
          await this.loadViaWebComponents(microFrontend, container, options);
          break;
        default:
          throw new Error(`Unsupported loading strategy: ${microFrontend.loadingStrategy}`);
      }

      options.onLoad?.();
    } catch (error) {
      console.error(`Failed to load micro-frontend ${microFrontendId}:`, error);
      options.onError?.(error as Error);
      this.showErrorFallback(container, microFrontend, error as Error);
    }
  }

  // Load micro-frontend via iframe
  private static async loadViaIFrame(
    microFrontend: MicroFrontend,
    container: Element,
    options: MicroFrontendLoadOptions
  ): Promise<void> {
    const iframe = document.createElement('iframe');
    
    // Configure iframe
    iframe.src = `${microFrontend.url}${microFrontend.entryPoint}${this.buildQueryParams(options.config)}`;
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.style.borderRadius = '8px';
    iframe.allow = 'camera; microphone; geolocation; encrypted-media; autoplay';
    iframe.sandbox = 'allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads';
    
    // Add loading and error handlers
    iframe.onload = () => {
      console.log(`Micro-frontend ${microFrontend.id} loaded successfully`);
      this.postMessageToMicroFrontend(microFrontend.id, {
        type: 'INIT',
        config: options.config
      });
    };
    
    iframe.onerror = (error) => {
      console.error(`Failed to load iframe for ${microFrontend.id}:`, error);
      throw new Error(`iframe loading failed`);
    };

    // Store reference
    this.loadedMicroFrontends.set(microFrontend.id, iframe);
    
    // Add to container
    container.appendChild(iframe);
  }

  // Load micro-frontend via module federation (future implementation)
  private static async loadViaModuleFederation(
    microFrontend: MicroFrontend,
    container: Element,
    options: MicroFrontendLoadOptions
  ): Promise<void> {
    throw new Error('Module federation loading not yet implemented');
  }

  // Load micro-frontend via dynamic import (future implementation)
  private static async loadViaDynamicImport(
    microFrontend: MicroFrontend,
    container: Element,
    options: MicroFrontendLoadOptions
  ): Promise<void> {
    throw new Error('Dynamic import loading not yet implemented');
  }

  // Load micro-frontend via web components (future implementation)
  private static async loadViaWebComponents(
    microFrontend: MicroFrontend,
    container: Element,
    options: MicroFrontendLoadOptions
  ): Promise<void> {
    throw new Error('Web components loading not yet implemented');
  }

  // Unload a micro-frontend
  static unloadMicroFrontend(microFrontendId: string): void {
    const iframe = this.loadedMicroFrontends.get(microFrontendId);
    if (iframe && iframe.parentNode) {
      iframe.parentNode.removeChild(iframe);
      this.loadedMicroFrontends.delete(microFrontendId);
    }
  }

  // Check micro-frontend health
  static async checkMicroFrontendHealth(microFrontend: MicroFrontend): Promise<boolean> {
    try {
      const healthUrl = `${microFrontend.url}${microFrontend.healthCheckUrl || '/health'}`;
      const response = await fetch(healthUrl, {
        method: 'GET',
        timeout: 5000,
        headers: {
          'Accept': 'application/json'
        }
      });
      return response.ok;
    } catch (error) {
      console.warn(`Health check failed for ${microFrontend.id}:`, error);
      return false;
    }
  }

  // Start periodic health checks
  private static startHealthChecks(): void {
    // Health check every 30 seconds for loaded micro-frontends
    const interval = setInterval(() => {
      this.loadedMicroFrontends.forEach(async (iframe, microFrontendId) => {
        const microFrontend = getMicroFrontendById(microFrontendId);
        if (microFrontend) {
          const isHealthy = await this.checkMicroFrontendHealth(microFrontend);
          if (!isHealthy) {
            console.warn(`Health check failed for loaded micro-frontend: ${microFrontendId}`);
            // Could trigger error handling or reload logic here
          }
        }
      });
    }, 30000);
  }

  // Handle cross-app messages
  private static handleCrossAppMessage = (event: MessageEvent) => {
    try {
      const message: CrossAppMessage = event.data;
      
      // Validate message structure
      if (!message.type || !message.source || !message.timestamp) {
        return; // Invalid message
      }

      // Handle different message types
      switch (message.type) {
        case 'NAVIGATION':
          this.handleNavigationMessage(message);
          break;
        case 'AUTH_TOKEN_REQUEST':
          this.handleAuthTokenRequest(message);
          break;
        case 'NOTIFICATION':
          this.handleNotificationMessage(message);
          break;
        case 'THEME_CHANGE':
          this.handleThemeChange(message);
          break;
        case 'USER_ACTIVITY':
          this.handleUserActivity(message);
          break;
        default:
          // Forward to registered handlers
          const handler = this.messageHandlers.get(message.type);
          if (handler) {
            handler(message);
          }
      }
    } catch (error) {
      console.error('Error handling cross-app message:', error);
    }
  };

  // Post message to micro-frontend
  static postMessageToMicroFrontend(microFrontendId: string, payload: any): void {
    const iframe = this.loadedMicroFrontends.get(microFrontendId);
    if (iframe?.contentWindow) {
      const message: Partial<CrossAppMessage> = {
        type: payload.type || 'MESSAGE',
        source: 'unified-hub',
        target: microFrontendId,
        payload: payload,
        timestamp: Date.now(),
        messageId: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      };
      
      iframe.contentWindow.postMessage(message, '*');
    }
  }

  // Handle navigation messages
  private static handleNavigationMessage(message: CrossAppMessage): void {
    const { path, params } = message.payload;
    console.log(`Navigation request from ${message.source} to ${path}`, params);
    
    // Trigger navigation in the main app
    window.history.pushState({}, '', path);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }

  // Handle auth token requests
  private static handleAuthTokenRequest(message: CrossAppMessage): void {
    const token = localStorage.getItem('accessToken');
    const user = JSON.parse(localStorage.getItem('activelog-auth') || '{}').state?.user;
    
    this.postMessageToMicroFrontend(message.source, {
      type: 'AUTH_TOKEN_RESPONSE',
      token,
      user,
      requestId: message.payload.requestId
    });
  }

  // Handle notification messages
  private static handleNotificationMessage(message: CrossAppMessage): void {
    // Forward to notification system
    window.dispatchEvent(new CustomEvent('micro-frontend-notification', {
      detail: message.payload
    }));
  }

  // Handle theme changes
  private static handleThemeChange(message: CrossAppMessage): void {
    const { theme } = message.payload;
    document.documentElement.setAttribute('data-theme', theme);
    
    // Propagate theme to all loaded micro-frontends
    this.loadedMicroFrontends.forEach((iframe, microFrontendId) => {
      this.postMessageToMicroFrontend(microFrontendId, {
        type: 'THEME_UPDATE',
        theme
      });
    });
  }

  // Handle user activity
  private static handleUserActivity(message: CrossAppMessage): void {
    // Update last activity timestamp
    localStorage.setItem('lastActivity', Date.now().toString());
    
    // Could trigger analytics or session management here
  }

  // Register custom message handler
  static registerMessageHandler(type: string, handler: (message: CrossAppMessage) => void): void {
    this.messageHandlers.set(type, handler);
  }

  // Build query parameters for micro-frontend config
  private static buildQueryParams(config: MicroFrontendConfig): string {
    const params = new URLSearchParams();
    
    if (config.authToken) params.append('token', config.authToken);
    if (config.userId) params.append('userId', config.userId);
    if (config.userRole) params.append('role', config.userRole);
    if (config.theme) params.append('theme', config.theme);
    if (config.language) params.append('lang', config.language);
    
    // Add feature flags
    Object.entries(config.features).forEach(([key, value]) => {
      params.append(`feature_${key}`, value.toString());
    });
    
    return params.toString() ? `?${params.toString()}` : '';
  }

  // Show error fallback UI
  private static showErrorFallback(container: Element, microFrontend: MicroFrontend, error: Error): void {
    container.innerHTML = `
      <div class="flex flex-col items-center justify-center h-full p-8 text-center bg-muted/20 rounded-lg">
        <div class="mb-4 p-4 bg-destructive/10 rounded-full">
          <svg class="w-8 h-8 text-destructive" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold mb-2">Failed to Load ${microFrontend.name}</h3>
        <p class="text-sm text-muted-foreground mb-4">
          ${error.message || 'The service is currently unavailable'}
        </p>
        <div class="flex space-x-2">
          <button onclick="window.location.reload()" class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90">
            Reload Page
          </button>
          <button onclick="history.back()" class="px-4 py-2 bg-secondary text-secondary-foreground rounded-md text-sm hover:bg-secondary/80">
            Go Back
          </button>
        </div>
        <div class="mt-4 text-xs text-muted-foreground">
          Service: ${microFrontend.name} v${microFrontend.version}<br>
          URL: ${microFrontend.url}:${microFrontend.port}
        </div>
      </div>
    `;
  }

  // Get loading status of micro-frontend
  static isLoaded(microFrontendId: string): boolean {
    return this.loadedMicroFrontends.has(microFrontendId);
  }

  // Get all loaded micro-frontends
  static getLoadedMicroFrontends(): string[] {
    return Array.from(this.loadedMicroFrontends.keys());
  }

  // BOT_EDUCATION: SuperInstance AI-powered initialization
  // This method connects the frontend to our intelligent backend services
  // for automated service discovery, context-aware routing, and cross-domain sync
  private static async initializeSuperInstanceIntegration(): Promise<void> {
    try {
      // Authenticate with SuperInstance backend
      const authToken = localStorage.getItem('accessToken');
      if (authToken) {
        // Register this frontend instance with the metadata service
        await this.registerFrontendInstance();
        
        // Load AI context for intelligent routing
        await this.loadAIContext();
        
        console.log('SuperInstance integration initialized successfully');
      }
    } catch (error) {
      console.warn('SuperInstance integration failed to initialize:', error);
    }
  }
  
  // Register this frontend instance with the SuperInstance metadata service
  private static async registerFrontendInstance(): Promise<void> {
    try {
      const response = await fetch(`${SUPER_INSTANCE_CONFIG.metadataServiceUrl}/frontend/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify({
          instanceId: `frontend-${Date.now()}`,
          url: window.location.origin,
          version: '1.0.0',
          capabilities: ['micro-frontend-hosting', 'cross-app-messaging', 'ai-routing'],
          loadedServices: Array.from(this.loadedMicroFrontends.keys())
        })
      });
      
      if (response.ok) {
        console.log('Frontend instance registered with SuperInstance');
      }
    } catch (error) {
      console.warn('Failed to register frontend instance:', error);
    }
  }
  
  // Load AI context for intelligent service routing
  private static async loadAIContext(): Promise<void> {
    try {
      const response = await fetch(`${SUPER_INSTANCE_CONFIG.metadataServiceUrl}/ai/context`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        }
      });
      
      if (response.ok) {
        const aiContext = await response.json();
        this.aiContextCache.set('global', aiContext);
        console.log('AI context loaded for intelligent routing');
      }
    } catch (error) {
      console.warn('Failed to load AI context:', error);
    }
  }
  
  // Start AI-powered service discovery
  private static startIntelligentServiceDiscovery(): void {
    // BOT_EDUCATION: This discovers optimal service routing based on user context
    setInterval(async () => {
      try {
        const user = JSON.parse(localStorage.getItem('activelog-auth') || '{}').state?.user;
        if (!user) return;
        
        const response = await fetch(`${SUPER_INSTANCE_CONFIG.metadataServiceUrl}/ai/discover`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            userId: user.id,
            context: {
              currentPath: window.location.pathname,
              loadedServices: Array.from(this.loadedMicroFrontends.keys()),
              userActivity: this.getUserActivityContext()
            }
          })
        });
        
        if (response.ok) {
          const suggestions = await response.json();
          this.processIntelligentSuggestions(suggestions);
        }
      } catch (error) {
        console.warn('Intelligent service discovery failed:', error);
      }
    }, 60000); // Every minute
  }
  
  // Initialize cross-domain synchronization
  private static initializeCrossDomainSync(): void {
    // BOT_EDUCATION: This enables real-time sync across ActiveLog, PersonalLog, FishingLog, etc.
    setInterval(async () => {
      await this.syncCrossDomainState();
    }, 30000); // Every 30 seconds
  }
  
  // Sync state across different domain services
  private static async syncCrossDomainState(): Promise<void> {
    try {
      const syncData = {
        timestamp: Date.now(),
        loadedServices: Array.from(this.loadedMicroFrontends.keys()),
        userState: this.getUserStateForSync()
      };
      
      const response = await fetch(`${SUPER_INSTANCE_CONFIG.fileSyncServiceUrl}/sync/cross-domain`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify(syncData)
      });
      
      if (response.ok) {
        const syncResponse = await response.json();
        this.applyCrossDomainUpdates(syncResponse);
      }
    } catch (error) {
      console.warn('Cross-domain sync failed:', error);
    }
  }
  
  // Get user activity context for AI analysis
  private static getUserActivityContext(): any {
    return {
      sessionDuration: Date.now() - parseInt(localStorage.getItem('sessionStart') || '0'),
      interactionCount: parseInt(localStorage.getItem('interactionCount') || '0'),
      lastActivity: localStorage.getItem('lastActivity'),
      preferredServices: JSON.parse(localStorage.getItem('preferredServices') || '[]')
    };
  }
  
  // Get user state for cross-domain sync
  private static getUserStateForSync(): any {
    return {
      preferences: JSON.parse(localStorage.getItem('userPreferences') || '{}'),
      theme: document.documentElement.getAttribute('data-theme'),
      language: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    };
  }
  
  // Process AI-powered service suggestions
  private static processIntelligentSuggestions(suggestions: any): void {
    if (suggestions.recommendedServices?.length > 0) {
      // Cache intelligent routing suggestions
      suggestions.recommendedServices.forEach((service: any) => {
        this.intelligentRoutingCache.set(service.context, service.serviceId);
      });
      
      // Trigger notification for recommended services
      window.dispatchEvent(new CustomEvent('ai-service-suggestions', {
        detail: suggestions
      }));
    }
  }
  
  // Apply cross-domain state updates
  private static applyCrossDomainUpdates(syncResponse: any): void {
    if (syncResponse.stateUpdates) {
      // Apply theme updates across all loaded micro-frontends
      if (syncResponse.stateUpdates.theme) {
        this.handleThemeChange({
          type: 'THEME_CHANGE',
          source: 'cross-domain-sync',
          target: 'all',
          payload: { theme: syncResponse.stateUpdates.theme },
          timestamp: Date.now(),
          messageId: `sync_${Date.now()}`
        });
      }
      
      // Update cross-domain sync state
      this.crossDomainSyncState.set('lastSync', Date.now());
      this.crossDomainSyncState.set('syncData', syncResponse);
    }
  }
  
  // Enhanced service loading with AI-powered routing
  static async loadMicroFrontendIntelligent(microFrontendId: string, options: MicroFrontendLoadOptions): Promise<void> {
    // Check for intelligent routing suggestions
    const currentContext = window.location.pathname;
    const suggestedService = this.intelligentRoutingCache.get(currentContext);
    
    if (suggestedService && suggestedService !== microFrontendId) {
      console.log(`AI suggests using ${suggestedService} instead of ${microFrontendId} for context: ${currentContext}`);
      // Could show user a suggestion prompt here
    }
    
    // Load AI context for this specific service
    const aiContext = this.aiContextCache.get(microFrontendId) || this.aiContextCache.get('global');
    if (aiContext) {
      options.config = {
        ...options.config,
        aiContext,
        intelligentRouting: true
      };
    }
    
    // Use standard loading with enhanced config
    return this.loadMicroFrontend(microFrontendId, options);
  }
  
  // Cleanup on page unload
  static cleanup(): void {
    this.loadedMicroFrontends.clear();
    this.messageHandlers.clear();
    this.healthCheckIntervals.forEach(interval => clearInterval(interval));
    this.healthCheckIntervals.clear();
    
    // BOT_EDUCATION: Clean up SuperInstance AI features
    this.aiContextCache.clear();
    this.crossDomainSyncState.clear();
    this.intelligentRoutingCache.clear();
    
    window.removeEventListener('message', this.handleCrossAppMessage);
  }
}

// Initialize on module load
if (typeof window !== 'undefined') {
  MicroFrontendService.initialize();
  
  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    MicroFrontendService.cleanup();
  });
}