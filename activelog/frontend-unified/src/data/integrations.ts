import { 
  ServiceIntegration, 
  ServiceHub, 
  IntegrationStatus, 
  HubStatus,
  AIServiceIntegration,
  FinancialServiceIntegration,
  DataServiceIntegration,
  MarineServiceIntegration,
  GamingServiceIntegration,
  EducationServiceIntegration,
  DMLogServiceIntegration
} from '@/types/integration';

// Service Hubs Configuration
export const serviceHubs: ServiceHub[] = [
  {
    id: 'ai-orchestrator',
    name: 'AI Orchestrator Hub',
    description: 'Central AI orchestration service with plugin architecture',
    url: 'http://localhost:8010',
    port: 8010,
    status: HubStatus.ONLINE,
    services: ['predictive-ai', 'emotional-ai', 'social-ai', 'education-ai', 'document-ai'],
    apiVersion: 'v1',
    capabilities: ['embeddings', 'analysis', 'image-analysis', 'transcription', 'plugins']
  },
  {
    id: 'activeledger',
    name: 'ActiveLedger Financial Hub',
    description: 'Comprehensive financial platform with compute credits system',
    url: 'http://localhost:8011',
    port: 8011,
    status: HubStatus.ONLINE,
    services: ['expense-tracker', 'investment-portfolio', 'subscription-manager'],
    apiVersion: 'v1',
    capabilities: ['payments', 'subscriptions', 'marketplace', 'compute-credits']
  },
  {
    id: 'data-manager',
    name: 'Data Manager Hub',
    description: 'Comprehensive data management AI with intelligent processing',
    url: 'http://localhost:8009',
    port: 8009,
    status: HubStatus.ONLINE,
    services: ['data-insights', 'metric-aggregator', 'file-organizer'],
    apiVersion: 'v1',
    capabilities: ['classification', 'recommendations', 'quality-monitoring', 'nlp-interface']
  },
  {
    id: 'marine-advanced',
    name: 'Marine Advanced Hub',
    description: 'Professional marine navigation and safety suite',
    url: 'http://localhost:8013',
    port: 8013,
    status: HubStatus.ONLINE,
    services: ['fishing-log', 'tackle-box', 'fishing-spots'],
    apiVersion: 'v1',
    capabilities: ['navigation', 'weather', 'safety', 'compliance', 'fleet-management']
  },
  {
    id: 'playerlog',
    name: 'PlayerLog Gaming Hub',
    description: 'Comprehensive gaming platform with AI-powered analysis',
    url: 'http://localhost:8014',
    port: 8014,
    status: HubStatus.MAINTENANCE,
    services: ['game-tracker', 'performance-analyzer', 'highlight-generator'],
    apiVersion: 'v1',
    capabilities: ['screen-recording', 'gameplay-analysis', 'highlights', 'statistics', 'coaching']
  },
  {
    id: 'studylog',
    name: 'StudyLog Education Hub',
    description: 'Comprehensive educational AI platform',
    url: 'http://localhost:8015',
    port: 8015,
    status: HubStatus.ONLINE,
    services: ['learning-tracker', 'flashcard-system'],
    apiVersion: 'v1',
    capabilities: ['personalized-learning', 'tutoring', 'assessment', 'lms-integration']
  },
  {
    id: 'dmlog-core',
    name: 'DMLog RPG Hub',
    description: 'Complete RPG rules engine and campaign management',
    url: 'http://localhost:8012',
    port: 8012,
    status: HubStatus.ONLINE,
    services: ['dmlog-ai-dm', 'dmlog-characters', 'dmlog-battle', 'dmlog-session', 'dmlog-templates', 'dmlog-world', 'dmlog-player'],
    apiVersion: 'v1',
    capabilities: ['character-management', 'combat-tracker', 'spell-system', 'npc-generation', 'campaign-management']
  }
];

// Service Integrations
export const serviceIntegrations: ServiceIntegration[] = [
  // AI Services
  {
    serviceId: 'predictive-ai',
    hubId: 'ai-orchestrator',
    hubName: 'AI Orchestrator Hub',
    hubUrl: 'http://localhost:8010',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/ai-orchestrator/plugins/predictive.py',
    apiEndpoints: ['/ai/predict', '/ai/analyze/behavioral'],
    dependencies: ['redis', 'postgresql'],
    description: 'Behavioral prediction and analytics'
  },
  {
    serviceId: 'emotional-ai',
    hubId: 'ai-orchestrator',
    hubName: 'AI Orchestrator Hub',
    hubUrl: 'http://localhost:8010',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/ai-orchestrator/plugins/emotional.py',
    apiEndpoints: ['/ai/emotion/analyze', '/ai/mood/track'],
    dependencies: ['redis', 'postgresql'],
    description: 'Mood detection and stress analysis'
  },
  {
    serviceId: 'social-ai',
    hubId: 'ai-orchestrator',
    hubName: 'AI Orchestrator Hub',
    hubUrl: 'http://localhost:8010',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/ai-orchestrator/plugins/social.py',
    apiEndpoints: ['/ai/social/analyze', '/ai/relationships/map'],
    dependencies: ['redis', 'postgresql'],
    description: 'Relationship mapping and social pattern analysis'
  },
  {
    serviceId: 'document-ai',
    hubId: 'ai-orchestrator',
    hubName: 'AI Orchestrator Hub',
    hubUrl: 'http://localhost:8010',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/ai-orchestrator/plugins/document.py',
    apiEndpoints: ['/ai/document/analyze', '/ai/document/extract'],
    dependencies: ['redis', 'minio'],
    description: 'Document processing and analysis'
  },

  // Financial Services
  {
    serviceId: 'expense-tracker',
    hubId: 'activeledger',
    hubName: 'ActiveLedger Financial Hub',
    hubUrl: 'http://localhost:8011',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/activeledger/modules/expenses.py',
    apiEndpoints: ['/finance/expenses', '/finance/budgets', '/finance/categories'],
    dependencies: ['postgresql', 'redis'],
    description: 'Smart expense categorization and budget management'
  },
  {
    serviceId: 'investment-portfolio',
    hubId: 'activeledger',
    hubName: 'ActiveLedger Financial Hub',
    hubUrl: 'http://localhost:8011',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/activeledger/modules/investments.py',
    apiEndpoints: ['/finance/portfolio', '/finance/market-data', '/finance/analysis'],
    dependencies: ['postgresql', 'redis', 'market-data-api'],
    description: 'Portfolio tracking with real-time market data'
  },
  {
    serviceId: 'subscription-manager',
    hubId: 'activeledger',
    hubName: 'ActiveLedger Financial Hub',
    hubUrl: 'http://localhost:8011',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/activeledger/modules/subscriptions.py',
    apiEndpoints: ['/finance/subscriptions', '/finance/renewals', '/finance/cancellations'],
    dependencies: ['postgresql', 'redis'],
    description: 'Track and manage all recurring subscriptions'
  },

  // Data Services
  {
    serviceId: 'data-insights',
    hubId: 'data-manager',
    hubName: 'Data Manager Hub',
    hubUrl: 'http://localhost:8009',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/data-manager/modules/insights.py',
    apiEndpoints: ['/data/insights', '/data/visualizations', '/data/reports'],
    dependencies: ['postgresql', 'elasticsearch', 'redis'],
    description: 'Cross-platform data analysis and visualization'
  },
  {
    serviceId: 'metric-aggregator',
    hubId: 'data-manager',
    hubName: 'Data Manager Hub',
    hubUrl: 'http://localhost:8009',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/data-manager/modules/aggregator.py',
    apiEndpoints: ['/data/metrics', '/data/collect', '/data/correlate'],
    dependencies: ['postgresql', 'redis', 'prometheus'],
    description: 'Automated data collection from all ActiveLog services'
  },
  {
    serviceId: 'file-organizer',
    hubId: 'data-manager',
    hubName: 'Data Manager Hub',
    hubUrl: 'http://localhost:8009',
    status: IntegrationStatus.PENDING,
    configurationPath: '/services/data-manager/modules/organizer.py',
    apiEndpoints: ['/data/organize', '/data/duplicates', '/data/cleanup'],
    dependencies: ['minio', 'ai-orchestrator'],
    description: 'AI-powered file organization and duplicate detection'
  },

  // Marine Services
  {
    serviceId: 'fishing-log',
    hubId: 'marine-advanced',
    hubName: 'Marine Advanced Hub',
    hubUrl: 'http://localhost:8013',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/marine-advanced/modules/fishing.py',
    apiEndpoints: ['/marine/fishing/trips', '/marine/fishing/catches', '/marine/fishing/weather'],
    dependencies: ['postgresql', 'weather-api'],
    description: 'Advanced fishing trip logging with weather and location data'
  },
  {
    serviceId: 'tackle-box',
    hubId: 'marine-advanced',
    hubName: 'Marine Advanced Hub',
    hubUrl: 'http://localhost:8013',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/marine-advanced/modules/tackle.py',
    apiEndpoints: ['/marine/tackle/inventory', '/marine/tackle/recommendations'],
    dependencies: ['postgresql', 'redis'],
    description: 'Digital tackle inventory and gear recommendations'
  },
  {
    serviceId: 'fishing-spots',
    hubId: 'marine-advanced',
    hubName: 'Marine Advanced Hub',
    hubUrl: 'http://localhost:8013',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/marine-advanced/modules/spots.py',
    apiEndpoints: ['/marine/spots', '/marine/spots/reviews', '/marine/spots/species'],
    dependencies: ['postgresql', 'maps-api'],
    description: 'Crowdsourced fishing location database with ratings'
  },

  // Gaming Services
  {
    serviceId: 'game-tracker',
    hubId: 'playerlog',
    hubName: 'PlayerLog Gaming Hub',
    hubUrl: 'http://localhost:8014',
    status: IntegrationStatus.PENDING,
    configurationPath: '/services/playerlog/modules/tracker.py',
    apiEndpoints: ['/gaming/sessions', '/gaming/stats', '/gaming/achievements'],
    dependencies: ['postgresql', 'redis'],
    description: 'Comprehensive game session and performance tracking'
  },
  {
    serviceId: 'performance-analyzer',
    hubId: 'playerlog',
    hubName: 'PlayerLog Gaming Hub',
    hubUrl: 'http://localhost:8014',
    status: IntegrationStatus.PENDING,
    configurationPath: '/services/playerlog/modules/analyzer.py',
    apiEndpoints: ['/gaming/analyze', '/gaming/heatmaps', '/gaming/patterns'],
    dependencies: ['ai-orchestrator', 'screen-capture'],
    description: 'AI-powered gameplay analysis and improvement suggestions'
  },
  {
    serviceId: 'highlight-generator',
    hubId: 'playerlog',
    hubName: 'PlayerLog Gaming Hub',
    hubUrl: 'http://localhost:8014',
    status: IntegrationStatus.PENDING,
    configurationPath: '/services/playerlog/modules/highlights.py',
    apiEndpoints: ['/gaming/highlights', '/gaming/clips', '/gaming/montages'],
    dependencies: ['ai-orchestrator', 'video-processing'],
    description: 'Automated highlight detection and video generation'
  },

  // Education Services
  {
    serviceId: 'learning-tracker',
    hubId: 'studylog',
    hubName: 'StudyLog Education Hub',
    hubUrl: 'http://localhost:8015',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/education-ai/modules/tracker.py',
    apiEndpoints: ['/education/progress', '/education/courses', '/education/achievements'],
    dependencies: ['postgresql', 'redis'],
    description: 'Progress tracking for courses and skill development'
  },
  {
    serviceId: 'flashcard-system',
    hubId: 'studylog',
    hubName: 'StudyLog Education Hub',
    hubUrl: 'http://localhost:8015',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/education-ai/modules/flashcards.py',
    apiEndpoints: ['/education/flashcards', '/education/spaced-repetition', '/education/review'],
    dependencies: ['postgresql', 'ai-orchestrator'],
    description: 'Spaced repetition flashcard system with AI optimization'
  },

  // DMLog Services
  {
    serviceId: 'dmlog-ai-dm',
    hubId: 'dmlog-core',
    hubName: 'DMLog RPG Hub',
    hubUrl: 'http://localhost:8012',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/dmlog-ai-dm/main.py',
    apiEndpoints: ['/dmlog/ai-dm/narrate', '/dmlog/ai-dm/npc', '/dmlog/ai-dm/events'],
    dependencies: ['ai-orchestrator', 'dmlog-core'],
    description: 'AI dungeon master for automated storytelling'
  },
  {
    serviceId: 'dmlog-characters',
    hubId: 'dmlog-core',
    hubName: 'DMLog RPG Hub',
    hubUrl: 'http://localhost:8012',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/dmlog-characters/main.py',
    apiEndpoints: ['/dmlog/characters', '/dmlog/character-sheets', '/dmlog/progression'],
    dependencies: ['dmlog-core', 'postgresql'],
    description: 'Universal character management system'
  },
  {
    serviceId: 'dmlog-battle',
    hubId: 'dmlog-core',
    hubName: 'DMLog RPG Hub',
    hubUrl: 'http://localhost:8012',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/dmlog-battle/main.py',
    apiEndpoints: ['/dmlog/combat', '/dmlog/initiative', '/dmlog/encounters'],
    dependencies: ['dmlog-core', 'dmlog-characters'],
    description: 'Advanced combat encounter system'
  },
  {
    serviceId: 'dmlog-session',
    hubId: 'dmlog-core',
    hubName: 'DMLog RPG Hub',
    hubUrl: 'http://localhost:8012',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/dmlog-session/main.py',
    apiEndpoints: ['/dmlog/sessions', '/dmlog/notes', '/dmlog/timeline'],
    dependencies: ['dmlog-core', 'postgresql'],
    description: 'Session management and campaign tracking'
  },
  {
    serviceId: 'dmlog-templates',
    hubId: 'dmlog-core',
    hubName: 'DMLog RPG Hub',
    hubUrl: 'http://localhost:8012',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/dmlog-templates/main.py',
    apiEndpoints: ['/dmlog/templates', '/dmlog/generators', '/dmlog/adventures'],
    dependencies: ['dmlog-core', 'ai-orchestrator'],
    description: 'Adventure and encounter generators'
  },
  {
    serviceId: 'dmlog-world',
    hubId: 'dmlog-core',
    hubName: 'DMLog RPG Hub',
    hubUrl: 'http://localhost:8012',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/dmlog-world/main.py',
    apiEndpoints: ['/dmlog/world', '/dmlog/locations', '/dmlog/lore'],
    dependencies: ['dmlog-core', 'ai-orchestrator'],
    description: 'World building and lore management tools'
  },
  {
    serviceId: 'dmlog-player',
    hubId: 'dmlog-core',
    hubName: 'DMLog RPG Hub',
    hubUrl: 'http://localhost:8012',
    status: IntegrationStatus.CONNECTED,
    configurationPath: '/services/dmlog-player/main.py',
    apiEndpoints: ['/dmlog/player', '/dmlog/journal', '/dmlog/party'],
    dependencies: ['dmlog-core', 'dmlog-characters'],
    description: 'Player tools and character journal'
  }
];

// Specific Integration Configurations
export const aiServiceIntegration: AIServiceIntegration = {
  orchestratorUrl: 'http://localhost:8010',
  pluginManager: {
    openai: true,
    ollama: true,
    whisper: true
  },
  capabilities: {
    embeddings: true,
    analysis: true,
    imageAnalysis: true,
    audioTranscription: true,
    textGeneration: true
  }
};

export const financialServiceIntegration: FinancialServiceIntegration = {
  activeledgerUrl: 'http://localhost:8011',
  computeCreditsEnabled: true,
  paymentGateways: {
    paypal: true,
    stripe: true,
    googlePay: true
  },
  subscriptionTiers: ['free', 'paid', 'pro', 'enterprise'],
  marketplaceEnabled: true
};

export const dataServiceIntegration: DataServiceIntegration = {
  dataManagerUrl: 'http://localhost:8009',
  metadataServiceUrl: 'http://localhost:8016',
  syncEngineUrl: 'http://localhost:8017',
  capabilities: {
    classification: true,
    recommendations: true,
    qualityMonitoring: true,
    nlpInterface: true
  }
};

export const marineServiceIntegration: MarineServiceIntegration = {
  marineAdvancedUrl: 'http://localhost:8013',
  frontends: {
    cocapn: {
      url: 'http://localhost:3008',
      port: 3008,
      target: 'recreational'
    },
    capitaine: {
      url: 'http://localhost:3009',
      port: 3009,
      target: 'commercial'
    }
  },
  features: {
    navigation: true,
    weather: true,
    safety: true,
    compliance: true
  }
};

export const gamingServiceIntegration: GamingServiceIntegration = {
  playerlogUrl: 'http://localhost:8014',
  features: {
    screenRecording: false,
    gameplayAnalysis: false,
    highlightGeneration: false,
    statsTracking: false,
    coaching: false,
    streaming: false
  }
};

export const educationServiceIntegration: EducationServiceIntegration = {
  studylogUrl: 'http://localhost:8015',
  educationAIUrl: 'http://localhost:8010/education-ai',
  features: {
    personalizedLearning: true,
    intelligentTutoring: true,
    assessment: true,
    lmsIntegration: true
  },
  compliance: {
    ferpa: true,
    coppa: true,
    wcag: true
  }
};

export const dmlogServiceIntegration: DMLogServiceIntegration = {
  coreUrl: 'http://localhost:8012',
  services: {
    aiDM: 'http://localhost:8012/ai-dm',
    characters: 'http://localhost:8012/characters',
    battle: 'http://localhost:8012/battle',
    session: 'http://localhost:8012/session',
    templates: 'http://localhost:8012/templates',
    world: 'http://localhost:8012/world',
    player: 'http://localhost:8012/player'
  },
  gameSystems: ['D&D 5e', 'Pathfinder 2e', 'Call of Cthulhu', 'Savage Worlds'],
  features: {
    characterManagement: true,
    combatTracker: true,
    spellSystem: true,
    npcGenerator: true,
    campaignManagement: true
  }
};

// Helper functions
export const getServicesByHub = (hubId: string): ServiceIntegration[] => {
  return serviceIntegrations.filter(integration => integration.hubId === hubId);
};

export const getHubByService = (serviceId: string): ServiceHub | undefined => {
  const integration = serviceIntegrations.find(int => int.serviceId === serviceId);
  return integration ? serviceHubs.find(hub => hub.id === integration.hubId) : undefined;
};

export const getConnectedServices = (): ServiceIntegration[] => {
  return serviceIntegrations.filter(integration => integration.status === IntegrationStatus.CONNECTED);
};

export const getPendingServices = (): ServiceIntegration[] => {
  return serviceIntegrations.filter(integration => integration.status === IntegrationStatus.PENDING);
};