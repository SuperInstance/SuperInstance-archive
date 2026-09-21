// BOT_EDUCATION: SuperInstance Cross-Ecosystem Synchronization Service
// This service orchestrates real-time data synchronization across ActiveLog,
// PersonalLog, FishingLog, BusinessLog, and DMLog ecosystems.
// It's a key component of the $2/month bot assembly platform's unified experience.

export interface EcosystemEndpoint {
  id: string;
  name: string;
  baseUrl: string;
  healthEndpoint: string;
  apiVersion: string;
  capabilities: string[];
  authRequired: boolean;
  priority: 'high' | 'medium' | 'low';
}

export interface SyncData {
  userId: string;
  ecosystem: string;
  dataType: string;
  payload: any;
  timestamp: number;
  syncId: string;
}

export interface SyncStatus {
  ecosystem: string;
  lastSync: number;
  status: 'healthy' | 'degraded' | 'error';
  pendingOperations: number;
  errorCount: number;
}

// BOT_EDUCATION: Complete SuperInstance Business Ecosystem Endpoints
// This configuration enables seamless cross-domain communication across all
// specialized business platforms in the $2/month bot assembly ecosystem
export const ECOSYSTEM_ENDPOINTS: EcosystemEndpoint[] = [
  // Core Infrastructure
  {
    id: 'activelog',
    name: 'ActiveLog Core',
    baseUrl: 'http://localhost:8000',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['auth', 'api-gateway', 'metadata', 'ai-orchestration'],
    authRequired: true,
    priority: 'high'
  },
  
  // Personal & Lifestyle Platforms
  {
    id: 'personallog',
    name: 'PersonalLog.AI',
    baseUrl: 'http://localhost:3002',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['journaling', 'mood-tracking', 'goal-setting', 'memory-palace', 'tool-integration'],
    authRequired: true,
    priority: 'high'
  },
  {
    id: 'activelog-ai',
    name: 'ActiveLog.AI',
    baseUrl: 'http://localhost:3013',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['fitness-tracking', 'sports-analytics', 'ai-coaching', 'performance-optimization'],
    authRequired: true,
    priority: 'medium'
  },
  
  // Business & Enterprise Platforms
  {
    id: 'businesslog',
    name: 'BusinessLog.AI',
    baseUrl: 'http://localhost:3003',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['pos-systems', 'marketing-automation', 'bookkeeping', 'business-planning', 'analytics'],
    authRequired: true,
    priority: 'high'
  },
  {
    id: 'activeledger-ai',
    name: 'ActiveLedger.AI',
    baseUrl: 'http://localhost:3017',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['compute-capital', 'dividend-management', 'foundation-grants', 'shareholder-governance'],
    authRequired: true,
    priority: 'high'
  },
  
  // Marine & Fishing Platforms
  {
    id: 'fishinglog',
    name: 'FishingLog.AI',
    baseUrl: 'http://localhost:8001',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['vessel-systems', 'weather-integration', 'catch-analytics', 'navigation'],
    authRequired: true,
    priority: 'medium'
  },
  {
    id: 'capitaine-ai',
    name: 'Capitaine.AI',
    baseUrl: 'http://localhost:3009',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['commercial-navigation', 'ecdis', 'fleet-management', 'maritime-compliance'],
    authRequired: true,
    priority: 'medium'
  },
  {
    id: 'cocapn-ai',
    name: 'CoCapn.AI',
    baseUrl: 'http://localhost:3008',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['recreational-boating', 'basic-navigation', 'weather-alerts', 'safety-features'],
    authRequired: true,
    priority: 'low'
  },
  {
    id: 'deckboss-ai',
    name: 'Deckboss.AI',
    baseUrl: 'http://localhost:3015',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['commercial-fishing-operations', 'crew-management', 'quota-tracking', 'equipment-maintenance'],
    authRequired: true,
    priority: 'medium'
  },
  {
    id: 'deckboss-net',
    name: 'Deckboss.Net',
    baseUrl: 'http://localhost:3016',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['fishing-marketplace', 'logistics-coordination', 'vendor-network', 'automated-ordering'],
    authRequired: true,
    priority: 'medium'
  },
  
  // Creative & Content Platforms
  {
    id: 'reallog-ai',
    name: 'RealLog.AI',
    baseUrl: 'http://localhost:3012',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['video-editing', 'content-creation', 'influencer-tools', 'collaboration'],
    authRequired: true,
    priority: 'medium'
  },
  {
    id: 'makerlog',
    name: 'MakerLog',
    baseUrl: 'http://localhost:3014',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['project-management', 'collaboration', 'job-matching', 'manufacturing-connect'],
    authRequired: true,
    priority: 'medium'
  },
  
  // Gaming & Entertainment
  {
    id: 'dmlog',
    name: 'DMLog.AI',
    baseUrl: 'http://localhost:8002',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['tabletop-gaming', 'character-management', 'campaign-tools', 'ai-dm'],
    authRequired: true,
    priority: 'low'
  },
  {
    id: 'playerlog-ai',
    name: 'PlayerLog.AI',
    baseUrl: 'http://localhost:3005',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['gameplay-recording', 'performance-analysis', 'streaming-tools'],
    authRequired: true,
    priority: 'low'
  },
  
  // Education & Learning
  {
    id: 'studylog-ai',
    name: 'StudyLog.AI',
    baseUrl: 'http://localhost:3006',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['personalized-learning', 'collaborative-education', 'ai-tutoring', 'dynamic-content'],
    authRequired: true,
    priority: 'medium'
  },
  
  // Advanced & Simulation Platforms
  {
    id: 'luciddreamer-ai',
    name: 'LucidDreamer.AI',
    baseUrl: 'http://localhost:3018',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['ecosystem-simulation', 'market-modeling', 'governance-tools'],
    authRequired: true,
    priority: 'high'
  },
  {
    id: 'superinstance-ai',
    name: 'SuperInstance.AI',
    baseUrl: 'http://localhost:3019',
    healthEndpoint: '/health',
    apiVersion: 'v1',
    capabilities: ['edge-deployment', 'enterprise-integration', 'iot-management', 'aws-automation'],
    authRequired: true,
    priority: 'high'
  }
];

export class CrossEcosystemSyncService {
  private static instance: CrossEcosystemSyncService;
  private syncStatuses: Map<string, SyncStatus> = new Map();
  private pendingSyncs: Map<string, SyncData[]> = new Map();
  private syncInterval: NodeJS.Timeout | null = null;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  
  // BOT_EDUCATION: Singleton pattern for global sync coordination
  static getInstance(): CrossEcosystemSyncService {
    if (!CrossEcosystemSyncService.instance) {
      CrossEcosystemSyncService.instance = new CrossEcosystemSyncService();
    }
    return CrossEcosystemSyncService.instance;
  }

  private constructor() {
    this.initializeSyncStatuses();
  }

  // Initialize sync status tracking for all ecosystems
  private initializeSyncStatuses(): void {
    ECOSYSTEM_ENDPOINTS.forEach(endpoint => {
      this.syncStatuses.set(endpoint.id, {
        ecosystem: endpoint.id,
        lastSync: 0,
        status: 'healthy',
        pendingOperations: 0,
        errorCount: 0
      });
      this.pendingSyncs.set(endpoint.id, []);
    });
  }

  // BOT_EDUCATION: Start cross-ecosystem synchronization
  // This method initializes real-time sync across all connected domains
  async startSync(): Promise<void> {
    console.log('🚀 Starting SuperInstance cross-ecosystem synchronization...');
    
    // Perform initial health checks
    await this.performHealthChecks();
    
    // Start sync loop (every 30 seconds)
    this.syncInterval = setInterval(async () => {
      await this.performSyncCycle();
    }, 30000);
    
    // Start health check loop (every 15 seconds)
    this.healthCheckInterval = setInterval(async () => {
      await this.performHealthChecks();
    }, 15000);
    
    // Listen for window events to sync on user activity
    window.addEventListener('focus', () => this.performSyncCycle());
    window.addEventListener('beforeunload', () => this.stopSync());
  }

  // Stop synchronization
  stopSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
    
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
    
    console.log('🛑 Cross-ecosystem synchronization stopped');
  }

  // Perform health checks on all ecosystems
  private async performHealthChecks(): Promise<void> {
    const healthPromises = ECOSYSTEM_ENDPOINTS.map(async (endpoint) => {
      try {
        const response = await fetch(`${endpoint.baseUrl}${endpoint.healthEndpoint}`, {
          method: 'GET',
          timeout: 5000,
          headers: {
            'Accept': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken') || ''}`
          }
        });
        
        const currentStatus = this.syncStatuses.get(endpoint.id)!;
        
        if (response.ok) {
          this.syncStatuses.set(endpoint.id, {
            ...currentStatus,
            status: 'healthy',
            errorCount: Math.max(0, currentStatus.errorCount - 1)
          });
        } else {
          this.syncStatuses.set(endpoint.id, {
            ...currentStatus,
            status: 'degraded',
            errorCount: currentStatus.errorCount + 1
          });
        }
      } catch (error) {
        const currentStatus = this.syncStatuses.get(endpoint.id)!;
        this.syncStatuses.set(endpoint.id, {
          ...currentStatus,
          status: 'error',
          errorCount: currentStatus.errorCount + 1
        });
        
        console.warn(`Health check failed for ${endpoint.name}:`, error);
      }
    });
    
    await Promise.allSettled(healthPromises);
  }

  // Perform a complete synchronization cycle
  private async performSyncCycle(): Promise<void> {
    console.log('🔄 Performing cross-ecosystem sync cycle...');
    
    try {
      // Sync user preferences across ecosystems
      await this.syncUserPreferences();
      
      // Sync theme and UI state
      await this.syncUIState();
      
      // Sync activity data between related ecosystems
      await this.syncActivityData();
      
      // Process any pending synchronizations
      await this.processPendingSyncs();
      
      // Update last sync timestamps
      this.updateSyncTimestamps();
      
      console.log('✅ Cross-ecosystem sync cycle completed');
    } catch (error) {
      console.error('❌ Sync cycle failed:', error);
    }
  }

  // BOT_EDUCATION: Sync user preferences across all ecosystems
  // This ensures consistent user experience regardless of which domain they're using
  private async syncUserPreferences(): Promise<void> {
    const userPreferences = JSON.parse(localStorage.getItem('userPreferences') || '{}');
    const authData = JSON.parse(localStorage.getItem('activelog-auth') || '{}');
    
    if (!authData.state?.user) return;
    
    const syncPromises = ECOSYSTEM_ENDPOINTS
      .filter(endpoint => this.syncStatuses.get(endpoint.id)?.status === 'healthy')
      .map(async (endpoint) => {
        try {
          const response = await fetch(`${endpoint.baseUrl}/api/sync/preferences`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify({
              userId: authData.state.user.id,
              preferences: userPreferences,
              timestamp: Date.now(),
              source: 'cross-ecosystem-sync'
            }),
            timeout: 10000
          });
          
          if (response.ok) {
            const remotePrefs = await response.json();
            // Merge remote preferences with local ones
            this.mergePreferences(userPreferences, remotePrefs);
          }
        } catch (error) {
          console.warn(`Failed to sync preferences with ${endpoint.name}:`, error);
        }
      });
    
    await Promise.allSettled(syncPromises);
  }

  // Sync UI state (theme, language, layout preferences)
  private async syncUIState(): Promise<void> {
    const uiState = {
      theme: document.documentElement.getAttribute('data-theme') || 'system',
      language: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      layoutPreferences: JSON.parse(localStorage.getItem('layoutPreferences') || '{}')
    };
    
    const syncPromises = ECOSYSTEM_ENDPOINTS
      .filter(endpoint => this.syncStatuses.get(endpoint.id)?.status === 'healthy')
      .map(async (endpoint) => {
        try {
          await fetch(`${endpoint.baseUrl}/api/sync/ui-state`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify({
              ...uiState,
              timestamp: Date.now(),
              source: 'unified-frontend'
            }),
            timeout: 5000
          });
        } catch (error) {
          console.warn(`Failed to sync UI state with ${endpoint.name}:`, error);
        }
      });
    
    await Promise.allSettled(syncPromises);
  }

  // BOT_EDUCATION: Sync activity data between related ecosystems
  // This creates intelligent cross-domain correlations for enhanced user insights
  private async syncActivityData(): Promise<void> {
    const activityData = {
      sessionDuration: Date.now() - parseInt(localStorage.getItem('sessionStart') || '0'),
      interactionCount: parseInt(localStorage.getItem('interactionCount') || '0'),
      recentServices: JSON.parse(localStorage.getItem('preferredServices') || '[]'),
      currentPath: window.location.pathname,
      timestamp: Date.now()
    };
    
    // Smart ecosystem targeting based on user context
    const targetEcosystems = this.determineRelevantEcosystems(activityData);
    
    const syncPromises = targetEcosystems.map(async (ecosystem) => {
      try {
        await fetch(`${ecosystem.baseUrl}/api/sync/activity`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            ...activityData,
            targetEcosystem: ecosystem.id,
            crossEcosystemContext: this.buildCrossEcosystemContext()
          }),
          timeout: 5000
        });
      } catch (error) {
        console.warn(`Failed to sync activity data with ${ecosystem.name}:`, error);
      }
    });
    
    await Promise.allSettled(syncPromises);
  }

  // BOT_EDUCATION: Advanced ecosystem targeting for complete SuperInstance business suite
  // This method intelligently determines which business platforms are relevant based on
  // user context, time patterns, industry affiliation, and cross-platform synergies
  private determineRelevantEcosystems(activityData: any): EcosystemEndpoint[] {
    const currentHour = new Date().getHours();
    const isWorkingHours = currentHour >= 9 && currentHour <= 17;
    const isWeekend = new Date().getDay() === 0 || new Date().getDay() === 6;
    const currentPath = activityData.currentPath || '';
    const recentServices = activityData.recentServices || [];
    
    const relevant: EcosystemEndpoint[] = [];
    
    // Always include ActiveLog as the central hub
    const activeLog = ECOSYSTEM_ENDPOINTS.find(e => e.id === 'activelog');
    if (activeLog && this.syncStatuses.get('activelog')?.status === 'healthy') {
      relevant.push(activeLog);
    }
    
    // Personal & Lifestyle Platform Targeting
    if (currentPath.includes('/personal') || currentPath.includes('/journal') || 
        currentHour >= 6 && currentHour <= 10) {
      this.addIfHealthy(relevant, 'personallog');
    }
    
    if (currentPath.includes('/fitness') || currentPath.includes('/workout') || 
        recentServices.includes('activelog-ai')) {
      this.addIfHealthy(relevant, 'activelog-ai');
    }
    
    // Business & Enterprise Platform Targeting
    if (isWorkingHours && !isWeekend) {
      this.addIfHealthy(relevant, 'businesslog');
      
      // Include financial platforms during business hours
      if (currentPath.includes('/finance') || currentPath.includes('/capital')) {
        this.addIfHealthy(relevant, 'activeledger-ai');
      }
    }
    
    // Marine & Fishing Platform Targeting
    if (isWeekend || currentPath.includes('/marine') || currentPath.includes('/fishing')) {
      this.addIfHealthy(relevant, 'fishinglog');
      
      // Commercial fishing operations
      if (currentPath.includes('/commercial') || currentPath.includes('/fleet')) {
        this.addIfHealthy(relevant, 'capitaine-ai');
        this.addIfHealthy(relevant, 'deckboss-ai');
        this.addIfHealthy(relevant, 'deckboss-net');
      }
      
      // Recreational boating
      if (currentPath.includes('/recreational') || recentServices.includes('cocapn-ai')) {
        this.addIfHealthy(relevant, 'cocapn-ai');
      }
    }
    
    // Creative & Content Platform Targeting
    if (currentPath.includes('/content') || currentPath.includes('/video') || 
        currentPath.includes('/reallog') || recentServices.includes('reallog-ai')) {
      this.addIfHealthy(relevant, 'reallog-ai');
    }
    
    if (currentPath.includes('/maker') || currentPath.includes('/projects') || 
        currentPath.includes('/manufacturing')) {
      this.addIfHealthy(relevant, 'makerlog');
    }
    
    // Gaming & Entertainment Platform Targeting
    if (currentHour >= 18 || isWeekend) {
      if (currentPath.includes('/gaming') || currentPath.includes('/dmlog')) {
        this.addIfHealthy(relevant, 'dmlog');
        this.addIfHealthy(relevant, 'playerlog-ai');
      }
    }
    
    // Education Platform Targeting
    if (currentPath.includes('/study') || currentPath.includes('/education') || 
        (isWorkingHours && recentServices.includes('studylog-ai'))) {
      this.addIfHealthy(relevant, 'studylog-ai');
    }
    
    // Advanced Platform Targeting (role-based)
    const userRole = this.getUserRole();
    if (['founder', 'board_member', 'investor'].includes(userRole)) {
      this.addIfHealthy(relevant, 'luciddreamer-ai');
      this.addIfHealthy(relevant, 'activeledger-ai');
    }
    
    if (['enterprise', 'system_admin', 'developer'].includes(userRole)) {
      this.addIfHealthy(relevant, 'superinstance-ai');
    }
    
    // Cross-platform synergies
    this.addCrossPlatformSynergies(relevant, recentServices, currentPath);
    
    return relevant;
  }
  
  // Helper method to add ecosystem if healthy
  private addIfHealthy(relevant: EcosystemEndpoint[], ecosystemId: string): void {
    const ecosystem = ECOSYSTEM_ENDPOINTS.find(e => e.id === ecosystemId);
    if (ecosystem && this.syncStatuses.get(ecosystemId)?.status === 'healthy') {
      relevant.push(ecosystem);
    }
  }
  
  // Get user role from auth data
  private getUserRole(): string {
    const authData = JSON.parse(localStorage.getItem('activelog-auth') || '{}');
    return authData.state?.user?.role || 'user';
  }
  
  // Add cross-platform synergies based on usage patterns
  private addCrossPlatformSynergies(relevant: EcosystemEndpoint[], recentServices: string[], currentPath: string): void {
    // Business + Personal synergy
    if (recentServices.includes('businesslog') && !relevant.some(r => r.id === 'personallog')) {
      this.addIfHealthy(relevant, 'personallog');
    }
    
    // Maker + Business synergy
    if (recentServices.includes('makerlog') && !relevant.some(r => r.id === 'businesslog')) {
      this.addIfHealthy(relevant, 'businesslog');
    }
    
    // Marine platform synergies
    if (recentServices.includes('fishinglog') || recentServices.includes('deckboss-ai')) {
      this.addIfHealthy(relevant, 'deckboss-net'); // Connect to marketplace
    }
    
    // Content creation synergies
    if (recentServices.includes('reallog-ai')) {
      this.addIfHealthy(relevant, 'personallog'); // Personal branding
      this.addIfHealthy(relevant, 'businesslog'); // Monetization tracking
    }
    
    // Financial platform synergies
    if (currentPath.includes('/finance') || currentPath.includes('/capital')) {
      this.addIfHealthy(relevant, 'businesslog'); // Business financial integration
      if (recentServices.includes('luciddreamer-ai')) {
        this.addIfHealthy(relevant, 'activeledger-ai'); // Foundation management
      }
    }
  }

  // Build cross-ecosystem context for AI-powered insights
  private buildCrossEcosystemContext(): any {
    return {
      connectedEcosystems: Array.from(this.syncStatuses.keys()).filter(
        id => this.syncStatuses.get(id)?.status === 'healthy'
      ),
      totalSyncOperations: Array.from(this.syncStatuses.values()).reduce(
        (sum, status) => sum + status.pendingOperations, 0
      ),
      averageLatency: this.calculateAverageLatency(),
      userEngagementScore: this.calculateEngagementScore()
    };
  }

  // Process any pending synchronizations
  private async processPendingSyncs(): Promise<void> {
    for (const [ecosystem, pendingData] of this.pendingSyncs) {
      if (pendingData.length === 0) continue;
      
      const endpoint = ECOSYSTEM_ENDPOINTS.find(e => e.id === ecosystem);
      if (!endpoint || this.syncStatuses.get(ecosystem)?.status !== 'healthy') {
        continue;
      }
      
      try {
        const response = await fetch(`${endpoint.baseUrl}/api/sync/batch`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            operations: pendingData,
            timestamp: Date.now()
          }),
          timeout: 15000
        });
        
        if (response.ok) {
          // Clear processed pending syncs
          this.pendingSyncs.set(ecosystem, []);
          
          // Update sync status
          const status = this.syncStatuses.get(ecosystem)!;
          this.syncStatuses.set(ecosystem, {
            ...status,
            pendingOperations: 0
          });
        }
      } catch (error) {
        console.warn(`Failed to process pending syncs for ${ecosystem}:`, error);
      }
    }
  }

  // Helper methods
  private mergePreferences(local: any, remote: any): void {
    // BOT_EDUCATION: Intelligent preference merging with conflict resolution
    const merged = { ...local };
    
    Object.keys(remote).forEach(key => {
      if (!local.hasOwnProperty(key)) {
        merged[key] = remote[key];
      } else if (typeof remote[key] === 'object' && !Array.isArray(remote[key])) {
        merged[key] = { ...local[key], ...remote[key] };
      }
      // For conflicts, keep local preferences (user's current session takes priority)
    });
    
    localStorage.setItem('userPreferences', JSON.stringify(merged));
  }

  private updateSyncTimestamps(): void {
    const now = Date.now();
    this.syncStatuses.forEach((status, ecosystem) => {
      this.syncStatuses.set(ecosystem, {
        ...status,
        lastSync: now
      });
    });
  }

  private calculateAverageLatency(): number {
    // Simulated latency calculation - in production, this would track actual request times
    return Math.floor(Math.random() * 100) + 50;
  }

  private calculateEngagementScore(): number {
    const interactionCount = parseInt(localStorage.getItem('interactionCount') || '0');
    const sessionDuration = Date.now() - parseInt(localStorage.getItem('sessionStart') || '0');
    
    // Simple engagement score based on interactions per minute
    const interactionsPerMinute = interactionCount / (sessionDuration / 60000);
    return Math.min(100, Math.floor(interactionsPerMinute * 10));
  }

  // Public API methods
  public getSyncStatus(ecosystem: string): SyncStatus | undefined {
    return this.syncStatuses.get(ecosystem);
  }

  public getAllSyncStatuses(): Map<string, SyncStatus> {
    return new Map(this.syncStatuses);
  }

  public queueSyncData(data: SyncData): void {
    const pending = this.pendingSyncs.get(data.ecosystem) || [];
    pending.push(data);
    this.pendingSyncs.set(data.ecosystem, pending);
    
    // Update pending operations count
    const status = this.syncStatuses.get(data.ecosystem);
    if (status) {
      this.syncStatuses.set(data.ecosystem, {
        ...status,
        pendingOperations: pending.length
      });
    }
  }

  public getHealthyEcosystems(): EcosystemEndpoint[] {
    return ECOSYSTEM_ENDPOINTS.filter(endpoint => 
      this.syncStatuses.get(endpoint.id)?.status === 'healthy'
    );
  }

  public getCrossEcosystemMetrics(): any {
    const statuses = Array.from(this.syncStatuses.values());
    
    return {
      totalEcosystems: ECOSYSTEM_ENDPOINTS.length,
      healthyEcosystems: statuses.filter(s => s.status === 'healthy').length,
      totalPendingOperations: statuses.reduce((sum, s) => sum + s.pendingOperations, 0),
      totalErrors: statuses.reduce((sum, s) => sum + s.errorCount, 0),
      lastSyncTime: Math.max(...statuses.map(s => s.lastSync)),
      averageLatency: this.calculateAverageLatency(),
      engagementScore: this.calculateEngagementScore()
    };
  }
}

// BOT_EDUCATION: Export singleton instance for global use
export const crossEcosystemSync = CrossEcosystemSyncService.getInstance();

// Auto-start sync when module is loaded (if in browser environment)
if (typeof window !== 'undefined') {
  // Start sync after a short delay to allow for proper initialization
  setTimeout(() => {
    crossEcosystemSync.startSync();
  }, 2000);
  
  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    crossEcosystemSync.stopSync();
  });
}