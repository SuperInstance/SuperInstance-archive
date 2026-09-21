import { MicroFrontend, MicroFrontendStatus, LoadingStrategy, EnhancedService, ServiceRoute } from '@/types/microfrontend';

export const microFrontends: MicroFrontend[] = [
  // Personal Services
  {
    id: 'personal-log',
    name: 'PersonalLog',
    url: 'http://localhost:3002',
    port: 3002,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['user', 'premium']
    },
    features: ['journaling', 'mood-tracking', 'goal-setting', 'memory-palace'],
    dependencies: ['auth', 'ai-orchestrator'],
    version: '2.1.0',
    healthCheckUrl: '/health',
    entryPoint: '/app',
    config: {
      theme: 'adaptive',
      features: {
        aiAssistant: true,
        voiceNotes: true,
        photoIntegration: true
      }
    }
  },
  
  // Business Services
  {
    id: 'business-log',
    name: 'BusinessLog',
    url: 'http://localhost:3003',
    port: 3003,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['business', 'enterprise']
    },
    features: ['analytics', 'reporting', 'team-management', 'kpi-tracking'],
    dependencies: ['auth', 'activeledger', 'data-manager'],
    version: '3.2.0',
    healthCheckUrl: '/health',
    entryPoint: '/dashboard',
    config: {
      theme: 'professional',
      features: {
        advancedAnalytics: true,
        teamCollaboration: true,
        customReporting: true
      }
    }
  },
  
  // Marine Services
  {
    id: 'fishing-log',
    name: 'FishingLog',
    url: 'http://localhost:3004',
    port: 3004,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['user', 'angler']
    },
    features: ['trip-logging', 'weather-integration', 'catch-statistics', 'spot-sharing'],
    dependencies: ['auth', 'marine-advanced'],
    version: '2.8.0',
    healthCheckUrl: '/health',
    entryPoint: '/fishing',
    config: {
      theme: 'marine',
      features: {
        gpsIntegration: true,
        weatherAlerts: true,
        socialSharing: true
      }
    }
  },
  
  {
    id: 'cocapn-ai',
    name: 'CoCapn.ai',
    url: 'http://localhost:3008',
    port: 3008,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['user', 'recreational_boater']
    },
    features: ['simple-navigation', 'weather', 'basic-charts', 'safety-alerts'],
    dependencies: ['auth', 'marine-advanced'],
    version: '1.5.0',
    healthCheckUrl: '/health',
    entryPoint: '/cocapn',
    config: {
      theme: 'recreational',
      target: 'recreational',
      features: {
        simplifiedUI: true,
        basicNavigation: true,
        weatherIntegration: true
      }
    }
  },
  
  {
    id: 'capitaine-ai',
    name: 'Capitaine.ai',
    url: 'http://localhost:3009',
    port: 3009,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['commercial_captain', 'fleet_manager']
    },
    features: ['advanced-navigation', 'ecdis', 'fleet-management', 'compliance', 'safety-systems'],
    dependencies: ['auth', 'marine-advanced'],
    version: '2.1.0',
    healthCheckUrl: '/health',
    entryPoint: '/capitaine',
    config: {
      theme: 'professional',
      target: 'commercial',
      features: {
        ecdisIntegration: true,
        fleetManagement: true,
        complianceTracking: true,
        advancedSafety: true
      }
    }
  },
  
  // Gaming Services
  {
    id: 'playerlog-ai',
    name: 'PlayerLog.ai',
    url: 'http://localhost:3005',
    port: 3005,
    status: MicroFrontendStatus.MAINTENANCE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['gamer', 'streamer', 'esports']
    },
    features: ['gameplay-recording', 'performance-analysis', 'highlight-generation', 'streaming'],
    dependencies: ['auth', 'playerlog'],
    version: '1.8.0',
    healthCheckUrl: '/health',
    entryPoint: '/gaming',
    config: {
      theme: 'gaming',
      features: {
        screenRecording: true,
        aiAnalysis: true,
        streamIntegration: true,
        tournamentMode: true
      }
    }
  },
  
  // Education Services
  {
    id: 'studylog-ai',
    name: 'StudyLog.ai',
    url: 'http://localhost:3006',
    port: 3006,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['student', 'educator', 'parent']
    },
    features: ['personalized-learning', 'progress-tracking', 'ai-tutoring', 'assessment'],
    dependencies: ['auth', 'studylog', 'education-ai'],
    version: '2.3.0',
    healthCheckUrl: '/health',
    entryPoint: '/study',
    config: {
      theme: 'educational',
      features: {
        aiTutor: true,
        progressAnalytics: true,
        parentalControls: true,
        lmsIntegration: true
      }
    }
  },
  
  // DMLog Services
  {
    id: 'dmlog-frontend',
    name: 'DMLog RPG Suite',
    url: 'http://localhost:3007',
    port: 3007,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['dm', 'player', 'rpg_enthusiast']
    },
    features: ['character-management', 'campaign-tools', 'dice-rolling', 'ai-dm', 'virtual-tabletop'],
    dependencies: ['auth', 'dmlog-core'],
    version: '3.1.0',
    healthCheckUrl: '/health',
    entryPoint: '/dmlog',
    config: {
      theme: 'fantasy',
      features: {
        aiDungeonMaster: true,
        virtualTabletop: true,
        characterBuilder: true,
        campaignManager: true
      }
    }
  },
  
  // Health Services
  {
    id: 'health-tracker',
    name: 'HealthTracker',
    url: 'http://localhost:3010',
    port: 3010,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['user', 'premium']
    },
    features: ['vital-tracking', 'fitness-monitoring', 'nutrition-logging', 'health-insights'],
    dependencies: ['auth', 'ai-orchestrator'],
    version: '2.3.0',
    healthCheckUrl: '/health',
    entryPoint: '/health',
    config: {
      theme: 'health',
      features: {
        wearableSync: true,
        aiInsights: true,
        doctorSharing: true
      }
    }
  },
  
  // Finance Services
  {
    id: 'expense-tracker',
    name: 'ExpenseTracker',
    url: 'http://localhost:3011',
    port: 3011,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['user', 'premium']
    },
    features: ['expense-categorization', 'budget-management', 'financial-reporting', 'investment-tracking'],
    dependencies: ['auth', 'activeledger'],
    version: '3.1.0',
    healthCheckUrl: '/health',
    entryPoint: '/finance',
    config: {
      theme: 'financial',
      features: {
        bankSync: true,
        aiCategorization: true,
        budgetAlerts: true,
        investmentAnalysis: true
      }
    }
  },
  
  // BOT_EDUCATION: Expanded SuperInstance Business Platform Ecosystem
  // The following microfrontends represent the complete SuperInstance business suite
  // designed for the $2/month bot assembly platform serving diverse industries
  
  // RealLog.AI - Reality TV and Influencer Platform
  {
    id: 'reallog-ai',
    name: 'RealLog.AI',
    url: 'http://localhost:3012',
    port: 3012,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['creator', 'producer', 'influencer', 'premium']
    },
    features: ['video-editing', 'content-scheduling', 'analytics', 'ai-story-generation', 'collaboration-tools'],
    dependencies: ['auth', 'ai-orchestrator', 'file-sync'],
    version: '1.0.0',
    healthCheckUrl: '/health',
    entryPoint: '/reallog',
    config: {
      theme: 'creative',
      target: 'content_creators',
      features: {
        finalCutProMode: true,
        aiStoryGeneration: true,
        realTimeCollaboration: true,
        socialMediaIntegration: true,
        monetizationTracking: true
      }
    }
  },
  
  // ActiveLog.AI - Fitness and Sports Platform
  {
    id: 'activelog-ai',
    name: 'ActiveLog.AI',
    url: 'http://localhost:3013',
    port: 3013,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['athlete', 'coach', 'fitness_enthusiast', 'premium']
    },
    features: ['workout-tracking', 'nutrition-planning', 'performance-analytics', 'ai-coaching', 'social-challenges'],
    dependencies: ['auth', 'ai-orchestrator', 'health-tracker'],
    version: '2.5.0',
    healthCheckUrl: '/health',
    entryPoint: '/fitness',
    config: {
      theme: 'athletic',
      features: {
        wearableSync: true,
        aiPersonalTrainer: true,
        competitiveLeaderboards: true,
        injuryPrevention: true,
        performanceOptimization: true
      }
    }
  },
  
  // MakerLog - Creative and Manufacturing Platform
  {
    id: 'makerlog',
    name: 'MakerLog',
    url: 'http://localhost:3014',
    port: 3014,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['maker', 'developer', 'artist', 'manufacturer', 'job_seeker']
    },
    features: ['project-management', 'collaboration-tools', 'marketplace', 'job-board', 'ai-design-assistant'],
    dependencies: ['auth', 'ai-orchestrator', 'business-log'],
    version: '1.8.0',
    healthCheckUrl: '/health',
    entryPoint: '/maker',
    config: {
      theme: 'maker',
      features: {
        projectCollaboration: true,
        aiDesignAssistant: true,
        marketplaceIntegration: true,
        jobMatching: true,
        skillAssessment: true,
        manufacturingConnect: true
      }
    }
  },
  
  // Deckboss.AI - Commercial Fishing Back Office
  {
    id: 'deckboss-ai',
    name: 'Deckboss.AI',
    url: 'http://localhost:3015',
    port: 3015,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['commercial_fisherman', 'fleet_manager', 'boat_owner']
    },
    features: ['fleet-management', 'catch-reporting', 'crew-scheduling', 'equipment-tracking', 'regulatory-compliance'],
    dependencies: ['auth', 'business-log', 'fishing-log'],
    version: '2.2.0',
    healthCheckUrl: '/health',
    entryPoint: '/deckboss',
    config: {
      theme: 'commercial_marine',
      features: {
        fleetTracking: true,
        crewManagement: true,
        quotaTracking: true,
        maintenanceScheduling: true,
        profitAnalysis: true
      }
    }
  },
  
  // Deckboss.Net - Commercial Fishing Network Platform
  {
    id: 'deckboss-net',
    name: 'Deckboss.Net',
    url: 'http://localhost:3016',
    port: 3016,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['fisherman', 'buyer', 'vendor', 'logistics', 'truck_driver']
    },
    features: ['marketplace', 'logistics-coordination', 'networking', 'automated-ordering', 'dynamic-pricing'],
    dependencies: ['auth', 'business-log', 'deckboss-ai'],
    version: '1.5.0',
    healthCheckUrl: '/health',
    entryPoint: '/network',
    config: {
      theme: 'marketplace',
      features: {
        fishMarketplace: true,
        logisticsMatching: true,
        vendorConnect: true,
        automaticOrdering: true,
        priceOptimization: true,
        qualityTracking: true
      }
    }
  },
  
  // ActiveLedger.AI - Compute Capital Financial Hub
  {
    id: 'activeledger-ai',
    name: 'ActiveLedger.AI',
    url: 'http://localhost:3017',
    port: 3017,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['investor', 'financial_analyst', 'accountant', 'premium']
    },
    features: ['compute-capital-tracking', 'dividend-management', 'investment-analysis', 'foundation-grants', 'shareholder-voting'],
    dependencies: ['auth', 'activeledger', 'superinstance-foundation'],
    version: '3.0.0',
    healthCheckUrl: '/health',
    entryPoint: '/capital',
    config: {
      theme: 'financial_hub',
      features: {
        computeCapitalTracking: true,
        dividendDistribution: true,
        foundationGrants: true,
        shareholderGovernance: true,
        investmentPortfolio: true
      }
    }
  },
  
  // LucidDreamer.AI - SuperInstance Ecosystem Simulation
  {
    id: 'luciddreamer-ai',
    name: 'LucidDreamer.AI',
    url: 'http://localhost:3018',
    port: 3018,
    status: MicroFrontendStatus.DEVELOPMENT,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['founder', 'investor', 'board_member', 'premium']
    },
    features: ['ecosystem-simulation', 'market-modeling', 'foundation-management', 'share-trading', 'grant-allocation'],
    dependencies: ['auth', 'activeledger-ai', 'ai-orchestrator'],
    version: '0.9.0',
    healthCheckUrl: '/health',
    entryPoint: '/simulation',
    config: {
      theme: 'simulation',
      features: {
        ecosystemModeling: true,
        marketSimulation: true,
        foundationManagement: true,
        shareTrading: true,
        grantAllocation: true,
        boardVoting: true
      }
    }
  },
  
  // SuperInstance.AI - Edge Devices and Embedded Systems
  {
    id: 'superinstance-ai',
    name: 'SuperInstance.AI',
    url: 'http://localhost:3019',
    port: 3019,
    status: MicroFrontendStatus.AVAILABLE,
    loadingStrategy: LoadingStrategy.IFRAME,
    authentication: {
      required: true,
      tokenSharing: true,
      ssoEnabled: true,
      roles: ['enterprise', 'developer', 'system_admin']
    },
    features: ['edge-deployment', 'aws-integration', 'company-server-setup', 'embedded-systems', 'iot-management'],
    dependencies: ['auth', 'api-gateway', 'all-ecosystems'],
    version: '1.0.0',
    healthCheckUrl: '/health',
    entryPoint: '/portal',
    config: {
      theme: 'enterprise',
      features: {
        edgeDeployment: true,
        awsIntegration: true,
        companyServerSetup: true,
        iotManagement: true,
        embeddedSystems: true,
        enterpriseSecurity: true
      }
    }
  }
];

// BOT_EDUCATION: Expanded service routes for complete SuperInstance business ecosystem
// These routes map URL paths to specific business platforms and their capabilities

// Service routes mapping
export const serviceRoutes: ServiceRoute[] = [
  // PersonalLog routes
  { path: '/personal/*', serviceId: 'personal-log', microFrontendId: 'personal-log', auth: true, title: 'Personal Life Tracking' },
  { path: '/journal/*', serviceId: 'personal-log', microFrontendId: 'personal-log', auth: true, title: 'Journal & Diary' },
  { path: '/mood/*', serviceId: 'mood-tracker', microFrontendId: 'personal-log', auth: true, title: 'Mood Tracking' },
  
  // BusinessLog routes
  { path: '/business/*', serviceId: 'business-log', microFrontendId: 'business-log', auth: true, roles: ['business', 'enterprise'], title: 'Business Analytics' },
  { path: '/analytics/*', serviceId: 'business-log', microFrontendId: 'business-log', auth: true, title: 'Business Intelligence' },
  { path: '/teams/*', serviceId: 'business-log', microFrontendId: 'business-log', auth: true, title: 'Team Management' },
  
  // Marine routes
  { path: '/fishing/*', serviceId: 'fishing-log', microFrontendId: 'fishing-log', auth: true, title: 'Fishing Adventures' },
  { path: '/marine/*', serviceId: 'fishing-log', microFrontendId: 'fishing-log', auth: true, title: 'Marine Navigation' },
  { path: '/cocapn/*', serviceId: 'cocapn-ai', microFrontendId: 'cocapn-ai', auth: true, title: 'Recreational Boating' },
  { path: '/capitaine/*', serviceId: 'capitaine-ai', microFrontendId: 'capitaine-ai', auth: true, roles: ['commercial_captain'], title: 'Commercial Navigation' },
  
  // Gaming routes
  { path: '/gaming/*', serviceId: 'playerlog-ai', microFrontendId: 'playerlog-ai', auth: true, title: 'Gaming Performance' },
  { path: '/esports/*', serviceId: 'playerlog-ai', microFrontendId: 'playerlog-ai', auth: true, title: 'Esports Analytics' },
  
  // Education routes
  { path: '/study/*', serviceId: 'studylog-ai', microFrontendId: 'studylog-ai', auth: true, title: 'Personal Learning' },
  { path: '/education/*', serviceId: 'studylog-ai', microFrontendId: 'studylog-ai', auth: true, title: 'Educational Tools' },
  { path: '/learn/*', serviceId: 'studylog-ai', microFrontendId: 'studylog-ai', auth: true, title: 'AI-Powered Learning' },
  
  // DMLog routes
  { path: '/dmlog/*', serviceId: 'dmlog-frontend', microFrontendId: 'dmlog-frontend', auth: true, title: 'D&D Campaign Manager' },
  { path: '/rpg/*', serviceId: 'dmlog-frontend', microFrontendId: 'dmlog-frontend', auth: true, title: 'RPG Tools' },
  { path: '/campaigns/*', serviceId: 'dmlog-frontend', microFrontendId: 'dmlog-frontend', auth: true, title: 'Campaign Management' },
  
  // Health routes
  { path: '/health/*', serviceId: 'health-tracker', microFrontendId: 'health-tracker', auth: true, title: 'Health & Wellness' },
  { path: '/fitness/*', serviceId: 'health-tracker', microFrontendId: 'health-tracker', auth: true, title: 'Fitness Tracking' },
  
  // Finance routes
  { path: '/finance/*', serviceId: 'expense-tracker', microFrontendId: 'expense-tracker', auth: true, title: 'Financial Management' },
  { path: '/expenses/*', serviceId: 'expense-tracker', microFrontendId: 'expense-tracker', auth: true, title: 'Expense Tracking' },
  { path: '/investments/*', serviceId: 'investment-portfolio', microFrontendId: 'expense-tracker', auth: true, title: 'Investment Portfolio' },
  
  // RealLog.AI routes - Reality TV and Influencer Platform
  { path: '/reallog/*', serviceId: 'reallog-ai', microFrontendId: 'reallog-ai', auth: true, title: 'Reality TV Production' },
  { path: '/content/*', serviceId: 'reallog-ai', microFrontendId: 'reallog-ai', auth: true, title: 'Content Creation' },
  { path: '/influencer/*', serviceId: 'reallog-ai', microFrontendId: 'reallog-ai', auth: true, title: 'Influencer Tools' },
  { path: '/video-editing/*', serviceId: 'reallog-ai', microFrontendId: 'reallog-ai', auth: true, title: 'Professional Video Editing' },
  
  // ActiveLog.AI routes - Fitness and Sports
  { path: '/fitness/*', serviceId: 'activelog-ai', microFrontendId: 'activelog-ai', auth: true, title: 'Fitness & Sports' },
  { path: '/workout/*', serviceId: 'activelog-ai', microFrontendId: 'activelog-ai', auth: true, title: 'Workout Tracking' },
  { path: '/sports/*', serviceId: 'activelog-ai', microFrontendId: 'activelog-ai', auth: true, title: 'Sports Analytics' },
  { path: '/coaching/*', serviceId: 'activelog-ai', microFrontendId: 'activelog-ai', auth: true, title: 'AI Coaching' },
  
  // MakerLog routes - Creative and Manufacturing
  { path: '/maker/*', serviceId: 'makerlog', microFrontendId: 'makerlog', auth: true, title: 'Maker Community' },
  { path: '/projects/*', serviceId: 'makerlog', microFrontendId: 'makerlog', auth: true, title: 'Project Management' },
  { path: '/jobs/*', serviceId: 'makerlog', microFrontendId: 'makerlog', auth: true, title: 'Manufacturing Jobs' },
  { path: '/marketplace/*', serviceId: 'makerlog', microFrontendId: 'makerlog', auth: true, title: 'Maker Marketplace' },
  { path: '/manufacturing/*', serviceId: 'makerlog', microFrontendId: 'makerlog', auth: true, title: 'Manufacturing Hub' },
  
  // Deckboss.AI routes - Commercial Fishing Back Office
  { path: '/deckboss/*', serviceId: 'deckboss-ai', microFrontendId: 'deckboss-ai', auth: true, roles: ['commercial_fisherman'], title: 'Commercial Fishing Management' },
  { path: '/fleet/*', serviceId: 'deckboss-ai', microFrontendId: 'deckboss-ai', auth: true, title: 'Fleet Management' },
  { path: '/crew/*', serviceId: 'deckboss-ai', microFrontendId: 'deckboss-ai', auth: true, title: 'Crew Scheduling' },
  { path: '/compliance/*', serviceId: 'deckboss-ai', microFrontendId: 'deckboss-ai', auth: true, title: 'Regulatory Compliance' },
  
  // Deckboss.Net routes - Commercial Fishing Network
  { path: '/network/*', serviceId: 'deckboss-net', microFrontendId: 'deckboss-net', auth: true, title: 'Fishing Industry Network' },
  { path: '/fish-market/*', serviceId: 'deckboss-net', microFrontendId: 'deckboss-net', auth: true, title: 'Fish Marketplace' },
  { path: '/logistics/*', serviceId: 'deckboss-net', microFrontendId: 'deckboss-net', auth: true, title: 'Logistics Coordination' },
  { path: '/vendors/*', serviceId: 'deckboss-net', microFrontendId: 'deckboss-net', auth: true, title: 'Vendor Network' },
  
  // ActiveLedger.AI routes - Compute Capital Financial Hub
  { path: '/capital/*', serviceId: 'activeledger-ai', microFrontendId: 'activeledger-ai', auth: true, title: 'Compute Capital Hub' },
  { path: '/dividends/*', serviceId: 'activeledger-ai', microFrontendId: 'activeledger-ai', auth: true, title: 'Dividend Management' },
  { path: '/foundation/*', serviceId: 'activeledger-ai', microFrontendId: 'activeledger-ai', auth: true, title: 'Foundation Grants' },
  { path: '/shares/*', serviceId: 'activeledger-ai', microFrontendId: 'activeledger-ai', auth: true, title: 'Share Management' },
  
  // LucidDreamer.AI routes - Ecosystem Simulation
  { path: '/simulation/*', serviceId: 'luciddreamer-ai', microFrontendId: 'luciddreamer-ai', auth: true, roles: ['founder', 'board_member'], title: 'Ecosystem Simulation' },
  { path: '/modeling/*', serviceId: 'luciddreamer-ai', microFrontendId: 'luciddreamer-ai', auth: true, title: 'Market Modeling' },
  { path: '/governance/*', serviceId: 'luciddreamer-ai', microFrontendId: 'luciddreamer-ai', auth: true, title: 'Board Governance' },
  
  // SuperInstance.AI routes - Edge and Enterprise
  { path: '/portal/*', serviceId: 'superinstance-ai', microFrontendId: 'superinstance-ai', auth: true, roles: ['enterprise'], title: 'Enterprise Portal' },
  { path: '/edge/*', serviceId: 'superinstance-ai', microFrontendId: 'superinstance-ai', auth: true, title: 'Edge Deployment' },
  { path: '/aws/*', serviceId: 'superinstance-ai', microFrontendId: 'superinstance-ai', auth: true, title: 'AWS Integration' },
  { path: '/embedded/*', serviceId: 'superinstance-ai', microFrontendId: 'superinstance-ai', auth: true, title: 'Embedded Systems' }
];

// Helper functions
export const getMicroFrontendById = (id: string): MicroFrontend | undefined => {
  return microFrontends.find(mf => mf.id === id);
};

export const getMicroFrontendByServiceId = (serviceId: string): MicroFrontend | undefined => {
  const route = serviceRoutes.find(r => r.serviceId === serviceId);
  return route ? getMicroFrontendById(route.microFrontendId) : undefined;
};

export const getAvailableMicroFrontends = (): MicroFrontend[] => {
  return microFrontends.filter(mf => mf.status === MicroFrontendStatus.AVAILABLE);
};

export const getRoutesForMicroFrontend = (microFrontendId: string): ServiceRoute[] => {
  return serviceRoutes.filter(route => route.microFrontendId === microFrontendId);
};

export const getServiceRouteByPath = (path: string): ServiceRoute | undefined => {
  return serviceRoutes.find(route => {
    if (route.exact) {
      return route.path === path;
    }
    return path.startsWith(route.path.replace('/*', ''));
  });
};