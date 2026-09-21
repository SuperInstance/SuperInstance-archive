export interface ServiceIntegration {
  serviceId: string;
  hubId: string;
  hubName: string;
  hubUrl: string;
  status: IntegrationStatus;
  configurationPath: string;
  apiEndpoints: string[];
  dependencies: string[];
  description: string;
}

export enum IntegrationStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  PENDING = 'pending',
  ERROR = 'error',
  CONFIGURING = 'configuring'
}

export interface ServiceHub {
  id: string;
  name: string;
  description: string;
  url: string;
  port: number;
  status: HubStatus;
  services: string[];
  apiVersion: string;
  capabilities: string[];
}

export enum HubStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  MAINTENANCE = 'maintenance',
  ERROR = 'error'
}

// AI Services Integration
export interface AIServiceIntegration {
  orchestratorUrl: string;
  pluginManager: {
    openai: boolean;
    ollama: boolean;
    whisper: boolean;
  };
  capabilities: {
    embeddings: boolean;
    analysis: boolean;
    imageAnalysis: boolean;
    audioTranscription: boolean;
    textGeneration: boolean;
  };
}

// Financial Services Integration
export interface FinancialServiceIntegration {
  activeledgerUrl: string;
  computeCreditsEnabled: boolean;
  paymentGateways: {
    paypal: boolean;
    stripe: boolean;
    googlePay: boolean;
  };
  subscriptionTiers: string[];
  marketplaceEnabled: boolean;
}

// Data Services Integration
export interface DataServiceIntegration {
  dataManagerUrl: string;
  metadataServiceUrl: string;
  syncEngineUrl: string;
  capabilities: {
    classification: boolean;
    recommendations: boolean;
    qualityMonitoring: boolean;
    nlpInterface: boolean;
  };
}

// Marine Services Integration
export interface MarineServiceIntegration {
  marineAdvancedUrl: string;
  frontends: {
    cocapn: {
      url: string;
      port: number;
      target: 'recreational';
    };
    capitaine: {
      url: string;
      port: number;
      target: 'commercial';
    };
  };
  features: {
    navigation: boolean;
    weather: boolean;
    safety: boolean;
    compliance: boolean;
  };
}

// Gaming Services Integration
export interface GamingServiceIntegration {
  playerlogUrl: string;
  features: {
    screenRecording: boolean;
    gameplayAnalysis: boolean;
    highlightGeneration: boolean;
    statsTracking: boolean;
    coaching: boolean;
    streaming: boolean;
  };
}

// Education Services Integration
export interface EducationServiceIntegration {
  studylogUrl: string;
  educationAIUrl: string;
  features: {
    personalizedLearning: boolean;
    intelligentTutoring: boolean;
    assessment: boolean;
    lmsIntegration: boolean;
  };
  compliance: {
    ferpa: boolean;
    coppa: boolean;
    wcag: boolean;
  };
}

// DMLog Services Integration
export interface DMLogServiceIntegration {
  coreUrl: string;
  services: {
    aiDM: string;
    characters: string;
    battle: string;
    session: string;
    templates: string;
    world: string;
    player: string;
  };
  gameSystems: string[];
  features: {
    characterManagement: boolean;
    combatTracker: boolean;
    spellSystem: boolean;
    npcGenerator: boolean;
    campaignManagement: boolean;
  };
}