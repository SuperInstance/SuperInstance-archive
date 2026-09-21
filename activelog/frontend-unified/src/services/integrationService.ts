import { ServiceHub, ServiceIntegration, IntegrationStatus } from '@/types/integration';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class IntegrationService {
  
  // AI Orchestrator Integration
  static async connectAIServices(serviceIds: string[]): Promise<void> {
    const aiOrchestratorUrl = 'http://localhost:8010';
    
    for (const serviceId of serviceIds) {
      try {
        // Register service with AI orchestrator
        const response = await fetch(`${aiOrchestratorUrl}/api/v1/services/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            serviceId,
            capabilities: this.getAICapabilities(serviceId),
            endpoints: this.getAIEndpoints(serviceId)
          })
        });
        
        if (!response.ok) {
          throw new Error(`Failed to connect ${serviceId} to AI orchestrator`);
        }
        
        // Configure service-specific AI features
        await this.configureAIFeatures(serviceId, aiOrchestratorUrl);
        
        console.log(`Successfully connected ${serviceId} to AI orchestrator`);
      } catch (error) {
        console.error(`Error connecting ${serviceId} to AI orchestrator:`, error);
        throw error;
      }
    }
  }

  // Financial Services Integration
  static async linkFinancialServices(serviceIds: string[]): Promise<void> {
    const activeledgerUrl = 'http://localhost:8011';
    
    for (const serviceId of serviceIds) {
      try {
        // Register service with ActiveLedger
        const response = await fetch(`${activeledgerUrl}/api/v1/services/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            serviceId,
            features: this.getFinancialFeatures(serviceId),
            computeCreditsEnabled: true,
            paymentMethods: ['paypal', 'stripe', 'google-pay']
          })
        });
        
        if (!response.ok) {
          throw new Error(`Failed to link ${serviceId} to ActiveLedger`);
        }
        
        // Configure financial features
        await this.configureFinancialFeatures(serviceId, activeledgerUrl);
        
        console.log(`Successfully linked ${serviceId} to ActiveLedger`);
      } catch (error) {
        console.error(`Error linking ${serviceId} to ActiveLedger:`, error);
        throw error;
      }
    }
  }

  // Data Manager Integration
  static async connectDataServices(serviceIds: string[]): Promise<void> {
    const dataManagerUrl = 'http://localhost:8009';
    
    for (const serviceId of serviceIds) {
      try {
        // Register service with Data Manager
        const response = await fetch(`${dataManagerUrl}/api/v1/services/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            serviceId,
            dataTypes: this.getDataTypes(serviceId),
            syncEnabled: true,
            analyticsEnabled: true
          })
        });
        
        if (!response.ok) {
          throw new Error(`Failed to connect ${serviceId} to Data Manager`);
        }
        
        // Configure data processing pipeline
        await this.configureDataPipeline(serviceId, dataManagerUrl);
        
        console.log(`Successfully connected ${serviceId} to Data Manager`);
      } catch (error) {
        console.error(`Error connecting ${serviceId} to Data Manager:`, error);
        throw error;
      }
    }
  }

  // Marine Services Integration
  static async integrateMarineServices(): Promise<void> {
    const marineAdvancedUrl = 'http://localhost:8013';
    const marineServices = ['fishing-log', 'tackle-box', 'fishing-spots'];
    
    try {
      // Configure CoCapn.ai (recreational)
      await fetch(`${marineAdvancedUrl}/api/v1/frontends/cocapn/configure`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify({
          target: 'recreational',
          features: ['basic-navigation', 'weather', 'fishing-spots', 'simple-logbook'],
          port: 3008
        })
      });
      
      // Configure Capitaine.ai (commercial)
      await fetch(`${marineAdvancedUrl}/api/v1/frontends/capitaine/configure`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify({
          target: 'commercial',
          features: ['advanced-navigation', 'ecdis', 'fleet-management', 'compliance', 'safety-systems'],
          port: 3009
        })
      });
      
      // Link all marine services
      for (const serviceId of marineServices) {
        await fetch(`${marineAdvancedUrl}/api/v1/services/integrate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({ serviceId })
        });
      }
      
      console.log('Successfully integrated all marine services');
    } catch (error) {
      console.error('Error integrating marine services:', error);
      throw error;
    }
  }

  // Gaming Services Integration
  static async linkGamingServices(serviceIds: string[]): Promise<void> {
    const playerlogUrl = 'http://localhost:8014';
    
    try {
      // First ensure PlayerLog service is running
      await this.ensureServiceRunning(playerlogUrl);
      
      for (const serviceId of serviceIds) {
        const response = await fetch(`${playerlogUrl}/api/v1/services/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            serviceId,
            features: this.getGamingFeatures(serviceId),
            aiIntegration: true
          })
        });
        
        if (!response.ok) {
          throw new Error(`Failed to link ${serviceId} to PlayerLog`);
        }
      }
      
      console.log('Successfully linked gaming services to PlayerLog');
    } catch (error) {
      console.error('Error linking gaming services:', error);
      throw error;
    }
  }

  // Education Services Integration
  static async connectEducationServices(serviceIds: string[]): Promise<void> {
    const studylogUrl = 'http://localhost:8015';
    const educationAIUrl = 'http://localhost:8010/education-ai';
    
    for (const serviceId of serviceIds) {
      try {
        // Register with StudyLog
        const studylogResponse = await fetch(`${studylogUrl}/api/v1/services/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            serviceId,
            features: this.getEducationFeatures(serviceId),
            aiEnabled: true
          })
        });
        
        if (!studylogResponse.ok) {
          throw new Error(`Failed to connect ${serviceId} to StudyLog`);
        }
        
        // Connect to Education AI
        const aiResponse = await fetch(`${educationAIUrl}/api/v1/services/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            serviceId,
            aiFeatures: this.getEducationAIFeatures(serviceId)
          })
        });
        
        if (!aiResponse.ok) {
          throw new Error(`Failed to connect ${serviceId} to Education AI`);
        }
        
        console.log(`Successfully connected ${serviceId} to education services`);
      } catch (error) {
        console.error(`Error connecting ${serviceId} to education services:`, error);
        throw error;
      }
    }
  }

  // DMLog Services Integration
  static async integrateDMLogServices(): Promise<void> {
    const dmlogCoreUrl = 'http://localhost:8012';
    const dmlogServices = [
      'dmlog-ai-dm',
      'dmlog-characters', 
      'dmlog-battle',
      'dmlog-session',
      'dmlog-templates',
      'dmlog-world',
      'dmlog-player'
    ];
    
    try {
      // First verify DMLog core is running
      await this.ensureServiceRunning(dmlogCoreUrl);
      
      // Register all DMLog services with the core
      for (const serviceId of dmlogServices) {
        const response = await fetch(`${dmlogCoreUrl}/api/v1/services/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({
            serviceId,
            capabilities: this.getDMLogCapabilities(serviceId)
          })
        });
        
        if (!response.ok) {
          throw new Error(`Failed to integrate ${serviceId} with DMLog core`);
        }
      }
      
      // Configure cross-service communication
      await this.configureDMLogCommunication(dmlogCoreUrl);
      
      console.log('Successfully integrated all DMLog services');
    } catch (error) {
      console.error('Error integrating DMLog services:', error);
      throw error;
    }
  }

  // Health Check
  static async healthCheck(hubUrl: string): Promise<boolean> {
    try {
      const response = await fetch(`${hubUrl}/health`, {
        method: 'GET',
        timeout: 5000
      });
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  // Test Integration
  static async testIntegration(serviceId: string, hubUrl: string): Promise<boolean> {
    try {
      const response = await fetch(`${hubUrl}/api/v1/services/${serviceId}/test`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        }
      });
      return response.ok;
    } catch (error) {
      console.error(`Error testing integration for ${serviceId}:`, error);
      return false;
    }
  }

  // Helper Methods
  private static async ensureServiceRunning(url: string): Promise<void> {
    const isRunning = await this.healthCheck(url);
    if (!isRunning) {
      throw new Error(`Service at ${url} is not running`);
    }
  }

  private static getAICapabilities(serviceId: string): string[] {
    const aiCapabilities: Record<string, string[]> = {
      'predictive-ai': ['behavioral-analysis', 'trend-prediction'],
      'emotional-ai': ['mood-detection', 'stress-analysis'],
      'social-ai': ['relationship-mapping', 'social-patterns'],
      'document-ai': ['text-analysis', 'document-processing']
    };
    return aiCapabilities[serviceId] || [];
  }

  private static getAIEndpoints(serviceId: string): string[] {
    const endpoints: Record<string, string[]> = {
      'predictive-ai': ['/predict', '/analyze/behavioral'],
      'emotional-ai': ['/emotion/analyze', '/mood/track'],
      'social-ai': ['/social/analyze', '/relationships/map'],
      'document-ai': ['/document/analyze', '/document/extract']
    };
    return endpoints[serviceId] || [];
  }

  private static async configureAIFeatures(serviceId: string, orchestratorUrl: string): Promise<void> {
    // Configure service-specific AI features
    await fetch(`${orchestratorUrl}/api/v1/services/${serviceId}/configure`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({
        enabledFeatures: this.getAICapabilities(serviceId),
        plugins: ['openai', 'ollama', 'whisper']
      })
    });
  }

  private static getFinancialFeatures(serviceId: string): string[] {
    const features: Record<string, string[]> = {
      'expense-tracker': ['categorization', 'budgeting', 'reporting'],
      'investment-portfolio': ['market-data', 'analysis', 'tracking'],
      'subscription-manager': ['tracking', 'alerts', 'cancellation']
    };
    return features[serviceId] || [];
  }

  private static async configureFinancialFeatures(serviceId: string, activeledgerUrl: string): Promise<void> {
    await fetch(`${activeledgerUrl}/api/v1/services/${serviceId}/configure`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({
        computeCredits: true,
        paymentGateways: ['paypal', 'stripe', 'google-pay'],
        features: this.getFinancialFeatures(serviceId)
      })
    });
  }

  private static getDataTypes(serviceId: string): string[] {
    const dataTypes: Record<string, string[]> = {
      'data-insights': ['analytics', 'visualizations', 'reports'],
      'metric-aggregator': ['metrics', 'aggregations', 'correlations'],
      'file-organizer': ['files', 'metadata', 'classifications']
    };
    return dataTypes[serviceId] || [];
  }

  private static async configureDataPipeline(serviceId: string, dataManagerUrl: string): Promise<void> {
    await fetch(`${dataManagerUrl}/api/v1/services/${serviceId}/pipeline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({
        dataTypes: this.getDataTypes(serviceId),
        sync: true,
        analytics: true
      })
    });
  }

  private static getGamingFeatures(serviceId: string): string[] {
    const features: Record<string, string[]> = {
      'game-tracker': ['session-tracking', 'statistics', 'achievements'],
      'performance-analyzer': ['gameplay-analysis', 'improvement-suggestions'],
      'highlight-generator': ['auto-highlights', 'video-processing']
    };
    return features[serviceId] || [];
  }

  private static getEducationFeatures(serviceId: string): string[] {
    const features: Record<string, string[]> = {
      'learning-tracker': ['progress-tracking', 'skill-development'],
      'flashcard-system': ['spaced-repetition', 'ai-optimization']
    };
    return features[serviceId] || [];
  }

  private static getEducationAIFeatures(serviceId: string): string[] {
    return ['personalized-learning', 'intelligent-tutoring', 'assessment'];
  }

  private static getDMLogCapabilities(serviceId: string): string[] {
    const capabilities: Record<string, string[]> = {
      'dmlog-ai-dm': ['storytelling', 'npc-behavior', 'event-generation'],
      'dmlog-characters': ['character-sheets', 'progression-tracking'],
      'dmlog-battle': ['combat-management', 'initiative-tracking'],
      'dmlog-session': ['session-notes', 'timeline-tracking'],
      'dmlog-templates': ['adventure-generation', 'encounter-creation'],
      'dmlog-world': ['world-building', 'lore-management'],
      'dmlog-player': ['player-tools', 'character-journal']
    };
    return capabilities[serviceId] || [];
  }

  private static async configureDMLogCommunication(dmlogCoreUrl: string): Promise<void> {
    await fetch(`${dmlogCoreUrl}/api/v1/configure/communication`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({
        enableCrossServiceCommunication: true,
        sharedDatabase: true,
        eventSystem: true
      })
    });
  }
}