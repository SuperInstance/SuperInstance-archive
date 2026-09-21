import { Service, ServiceCategory, ServiceStatus } from '@/types/service';

export const services: Service[] = [
  // Personal Services
  {
    id: 'personal-log',
    name: 'PersonalLog',
    description: 'Comprehensive personal life tracking and journaling',
    category: ServiceCategory.PERSONAL,
    status: ServiceStatus.ACTIVE,
    icon: 'User',
    url: '/personal',
    version: '2.1.0',
    tags: ['journaling', 'tracking', 'personal'],
    features: ['Daily Logs', 'Mood Tracking', 'Goal Setting', 'Memory Palace'],
    isActive: true,
    lastUpdated: '2024-01-15',
    popularity: 95
  },
  {
    id: 'dream-log',
    name: 'DreamLog',
    description: 'Dream journal with pattern analysis and lucid dreaming tools',
    category: ServiceCategory.PERSONAL,
    status: ServiceStatus.ACTIVE,
    icon: 'Moon',
    url: '/dreams',
    version: '1.3.0',
    tags: ['dreams', 'analysis', 'sleep'],
    features: ['Dream Recording', 'Pattern Analysis', 'Lucid Training'],
    isActive: true,
    lastUpdated: '2024-01-12',
    popularity: 78
  },
  {
    id: 'mood-tracker',
    name: 'MoodTracker',
    description: 'Advanced emotional state monitoring and analysis',
    category: ServiceCategory.PERSONAL,
    status: ServiceStatus.ACTIVE,
    icon: 'Heart',
    url: '/mood',
    version: '1.8.0',
    tags: ['mood', 'emotions', 'wellness'],
    features: ['Mood Graphs', 'Trigger Analysis', 'Wellness Tips'],
    isActive: true,
    lastUpdated: '2024-01-10',
    popularity: 82
  },

  // Business Services
  {
    id: 'business-log',
    name: 'BusinessLog',
    description: 'Enterprise-grade business activity and performance tracking',
    category: ServiceCategory.BUSINESS,
    status: ServiceStatus.ACTIVE,
    icon: 'Building2',
    url: '/business',
    version: '3.2.0',
    tags: ['business', 'analytics', 'performance'],
    features: ['KPI Tracking', 'Team Analytics', 'Revenue Analysis'],
    isActive: true,
    lastUpdated: '2024-01-18',
    popularity: 91
  },
  {
    id: 'project-manager',
    name: 'ProjectManager',
    description: 'Agile project management with timeline tracking',
    category: ServiceCategory.BUSINESS,
    status: ServiceStatus.ACTIVE,
    icon: 'Briefcase',
    url: '/projects',
    version: '2.5.0',
    tags: ['projects', 'agile', 'management'],
    features: ['Kanban Boards', 'Gantt Charts', 'Team Collaboration'],
    isActive: true,
    lastUpdated: '2024-01-14',
    popularity: 87
  },
  {
    id: 'inventory-tracker',
    name: 'InventoryTracker',
    description: 'Real-time inventory management and stock optimization',
    category: ServiceCategory.BUSINESS,
    status: ServiceStatus.ACTIVE,
    icon: 'Package',
    url: '/inventory',
    version: '2.0.0',
    tags: ['inventory', 'stock', 'optimization'],
    features: ['Stock Alerts', 'Demand Forecasting', 'Supplier Management'],
    isActive: true,
    lastUpdated: '2024-01-16',
    popularity: 79
  },

  // Fishing Services
  {
    id: 'fishing-log',
    name: 'FishingLog',
    description: 'Advanced fishing trip logging with weather and location data',
    category: ServiceCategory.FISHING,
    status: ServiceStatus.ACTIVE,
    icon: 'Fish',
    url: '/fishing',
    version: '2.8.0',
    tags: ['fishing', 'outdoors', 'tracking'],
    features: ['Trip Logs', 'Weather Integration', 'Catch Statistics'],
    isActive: true,
    lastUpdated: '2024-01-17',
    popularity: 88
  },
  {
    id: 'tackle-box',
    name: 'TackleBox',
    description: 'Digital tackle inventory and gear recommendations',
    category: ServiceCategory.FISHING,
    status: ServiceStatus.ACTIVE,
    icon: 'Box',
    url: '/tackle',
    version: '1.5.0',
    tags: ['tackle', 'gear', 'inventory'],
    features: ['Gear Tracking', 'Recommendations', 'Purchase History'],
    isActive: true,
    lastUpdated: '2024-01-13',
    popularity: 74
  },
  {
    id: 'fishing-spots',
    name: 'FishingSpots',
    description: 'Crowdsourced fishing location database with ratings',
    category: ServiceCategory.FISHING,
    status: ServiceStatus.ACTIVE,
    icon: 'MapPin',
    url: '/spots',
    version: '1.9.0',
    tags: ['locations', 'community', 'maps'],
    features: ['Spot Reviews', 'GPS Coordinates', 'Fish Species Data'],
    isActive: true,
    lastUpdated: '2024-01-11',
    popularity: 81
  },

  // Health Services
  {
    id: 'health-tracker',
    name: 'HealthTracker',
    description: 'Comprehensive health metrics and wellness monitoring',
    category: ServiceCategory.HEALTH,
    status: ServiceStatus.ACTIVE,
    icon: 'Activity',
    url: '/health',
    version: '2.3.0',
    tags: ['health', 'fitness', 'monitoring'],
    features: ['Vital Signs', 'Exercise Tracking', 'Nutrition Logs'],
    isActive: true,
    lastUpdated: '2024-01-19',
    popularity: 93
  },
  {
    id: 'medication-manager',
    name: 'MedicationManager',
    description: 'Smart medication scheduling and interaction checker',
    category: ServiceCategory.HEALTH,
    status: ServiceStatus.ACTIVE,
    icon: 'Pill',
    url: '/medications',
    version: '1.7.0',
    tags: ['medication', 'reminders', 'health'],
    features: ['Dose Reminders', 'Interaction Alerts', 'Refill Tracking'],
    isActive: true,
    lastUpdated: '2024-01-08',
    popularity: 85
  },

  // Finance Services
  {
    id: 'expense-tracker',
    name: 'ExpenseTracker',
    description: 'Smart expense categorization and budget management',
    category: ServiceCategory.FINANCE,
    status: ServiceStatus.ACTIVE,
    icon: 'DollarSign',
    url: '/expenses',
    version: '3.1.0',
    tags: ['finance', 'budgets', 'expenses'],
    features: ['Auto Categorization', 'Budget Alerts', 'Spending Analysis'],
    isActive: true,
    lastUpdated: '2024-01-20',
    popularity: 89
  },
  {
    id: 'investment-portfolio',
    name: 'InvestmentPortfolio',
    description: 'Portfolio tracking with real-time market data',
    category: ServiceCategory.FINANCE,
    status: ServiceStatus.ACTIVE,
    icon: 'TrendingUp',
    url: '/investments',
    version: '2.4.0',
    tags: ['investments', 'portfolio', 'markets'],
    features: ['Real-time Quotes', 'Performance Analytics', 'Risk Assessment'],
    isActive: true,
    lastUpdated: '2024-01-16',
    popularity: 86
  },

  // Travel Services
  {
    id: 'travel-log',
    name: 'TravelLog',
    description: 'Digital travel journal with photo integration',
    category: ServiceCategory.TRAVEL,
    status: ServiceStatus.ACTIVE,
    icon: 'Plane',
    url: '/travel',
    version: '2.0.0',
    tags: ['travel', 'journal', 'photos'],
    features: ['Trip Planning', 'Photo Albums', 'Expense Tracking'],
    isActive: true,
    lastUpdated: '2024-01-14',
    popularity: 77
  },
  {
    id: 'itinerary-planner',
    name: 'ItineraryPlanner',
    description: 'AI-powered travel itinerary optimization',
    category: ServiceCategory.TRAVEL,
    status: ServiceStatus.BETA,
    icon: 'Calendar',
    url: '/itinerary',
    version: '0.8.0',
    tags: ['planning', 'ai', 'optimization'],
    features: ['Smart Routing', 'Local Recommendations', 'Time Optimization'],
    isActive: true,
    lastUpdated: '2024-01-12',
    popularity: 72
  },

  // Education Services
  {
    id: 'learning-tracker',
    name: 'LearningTracker',
    description: 'Progress tracking for courses and skill development',
    category: ServiceCategory.EDUCATION,
    status: ServiceStatus.ACTIVE,
    icon: 'BookOpen',
    url: '/learning',
    version: '1.6.0',
    tags: ['education', 'progress', 'skills'],
    features: ['Course Progress', 'Skill Trees', 'Achievement System'],
    isActive: true,
    lastUpdated: '2024-01-13',
    popularity: 83
  },
  {
    id: 'flashcard-system',
    name: 'FlashcardSystem',
    description: 'Spaced repetition flashcard system with AI optimization',
    category: ServiceCategory.EDUCATION,
    status: ServiceStatus.ACTIVE,
    icon: 'Brain',
    url: '/flashcards',
    version: '2.2.0',
    tags: ['flashcards', 'memory', 'ai'],
    features: ['Spaced Repetition', 'Smart Scheduling', 'Progress Analytics'],
    isActive: true,
    lastUpdated: '2024-01-09',
    popularity: 80
  },

  // Entertainment Services
  {
    id: 'movie-tracker',
    name: 'MovieTracker',
    description: 'Personal movie and TV show watchlist with recommendations',
    category: ServiceCategory.ENTERTAINMENT,
    status: ServiceStatus.ACTIVE,
    icon: 'Film',
    url: '/movies',
    version: '1.9.0',
    tags: ['movies', 'tv', 'recommendations'],
    features: ['Watchlist', 'Rating System', 'Personal Reviews'],
    isActive: true,
    lastUpdated: '2024-01-11',
    popularity: 76
  },
  {
    id: 'book-library',
    name: 'BookLibrary',
    description: 'Digital book collection with reading progress tracking',
    category: ServiceCategory.ENTERTAINMENT,
    status: ServiceStatus.ACTIVE,
    icon: 'Library',
    url: '/books',
    version: '2.1.0',
    tags: ['books', 'reading', 'library'],
    features: ['Reading Progress', 'Book Reviews', 'Reading Goals'],
    isActive: true,
    lastUpdated: '2024-01-15',
    popularity: 84
  },

  // Productivity Services
  {
    id: 'task-manager',
    name: 'TaskManager',
    description: 'GTD-based task management with smart prioritization',
    category: ServiceCategory.PRODUCTIVITY,
    status: ServiceStatus.ACTIVE,
    icon: 'CheckSquare',
    url: '/tasks',
    version: '3.0.0',
    tags: ['tasks', 'gtd', 'productivity'],
    features: ['Smart Priorities', 'Context Switching', 'Time Tracking'],
    isActive: true,
    lastUpdated: '2024-01-18',
    popularity: 92
  },
  {
    id: 'habit-tracker',
    name: 'HabitTracker',
    description: 'Habit formation with streaks and behavioral analytics',
    category: ServiceCategory.PRODUCTIVITY,
    status: ServiceStatus.ACTIVE,
    icon: 'Repeat',
    url: '/habits',
    version: '2.7.0',
    tags: ['habits', 'streaks', 'behavior'],
    features: ['Streak Tracking', 'Habit Chains', 'Behavioral Insights'],
    isActive: true,
    lastUpdated: '2024-01-17',
    popularity: 90
  },
  {
    id: 'time-tracker',
    name: 'TimeTracker',
    description: 'Detailed time tracking with automatic categorization',
    category: ServiceCategory.PRODUCTIVITY,
    status: ServiceStatus.ACTIVE,
    icon: 'Clock',
    url: '/time',
    version: '2.3.0',
    tags: ['time', 'tracking', 'productivity'],
    features: ['Auto Detection', 'Project Allocation', 'Time Reports'],
    isActive: true,
    lastUpdated: '2024-01-16',
    popularity: 87
  },

  // Communication Services
  {
    id: 'contact-manager',
    name: 'ContactManager',
    description: 'Advanced contact management with interaction history',
    category: ServiceCategory.COMMUNICATION,
    status: ServiceStatus.ACTIVE,
    icon: 'Users',
    url: '/contacts',
    version: '1.8.0',
    tags: ['contacts', 'crm', 'communication'],
    features: ['Interaction History', 'Relationship Tracking', 'Follow-up Reminders'],
    isActive: true,
    lastUpdated: '2024-01-14',
    popularity: 78
  },
  {
    id: 'message-center',
    name: 'MessageCenter',
    description: 'Unified messaging across all communication channels',
    category: ServiceCategory.COMMUNICATION,
    status: ServiceStatus.ACTIVE,
    icon: 'MessageSquare',
    url: '/messages',
    version: '2.5.0',
    tags: ['messaging', 'unified', 'communication'],
    features: ['Multi-platform', 'Smart Filtering', 'Auto Responses'],
    isActive: true,
    lastUpdated: '2024-01-19',
    popularity: 85
  },

  // Development Services
  {
    id: 'code-tracker',
    name: 'CodeTracker',
    description: 'Development time tracking with repository integration',
    category: ServiceCategory.DEVELOPMENT,
    status: ServiceStatus.ACTIVE,
    icon: 'Code',
    url: '/code',
    version: '1.4.0',
    tags: ['development', 'coding', 'git'],
    features: ['Commit Analysis', 'Language Stats', 'Project Insights'],
    isActive: true,
    lastUpdated: '2024-01-15',
    popularity: 81
  },
  {
    id: 'api-monitor',
    name: 'APIMonitor',
    description: 'Real-time API performance and uptime monitoring',
    category: ServiceCategory.DEVELOPMENT,
    status: ServiceStatus.ACTIVE,
    icon: 'Monitor',
    url: '/api-monitor',
    version: '2.1.0',
    tags: ['api', 'monitoring', 'performance'],
    features: ['Uptime Monitoring', 'Performance Metrics', 'Alert System'],
    isActive: true,
    lastUpdated: '2024-01-20',
    popularity: 79
  },

  // Analytics Services
  {
    id: 'data-insights',
    name: 'DataInsights',
    description: 'Cross-platform data analysis and visualization',
    category: ServiceCategory.ANALYTICS,
    status: ServiceStatus.ACTIVE,
    icon: 'BarChart3',
    url: '/insights',
    version: '3.1.0',
    tags: ['analytics', 'data', 'visualization'],
    features: ['Custom Dashboards', 'Predictive Analysis', 'Export Tools'],
    isActive: true,
    lastUpdated: '2024-01-21',
    popularity: 94
  },
  {
    id: 'metric-aggregator',
    name: 'MetricAggregator',
    description: 'Automated data collection from all ActiveLog services',
    category: ServiceCategory.ANALYTICS,
    status: ServiceStatus.ACTIVE,
    icon: 'Database',
    url: '/metrics',
    version: '2.6.0',
    tags: ['metrics', 'aggregation', 'automation'],
    features: ['Auto Collection', 'Data Correlation', 'Trend Analysis'],
    isActive: true,
    lastUpdated: '2024-01-18',
    popularity: 88
  },

  // Utilities Services
  {
    id: 'qr-generator',
    name: 'QRGenerator',
    description: 'QR code generation with custom branding options',
    category: ServiceCategory.UTILITIES,
    status: ServiceStatus.ACTIVE,
    icon: 'QrCode',
    url: '/qr',
    version: '1.2.0',
    tags: ['qr', 'generator', 'utility'],
    features: ['Custom Logos', 'Batch Generation', 'Analytics Tracking'],
    isActive: true,
    lastUpdated: '2024-01-10',
    popularity: 65
  },
  {
    id: 'password-manager',
    name: 'PasswordManager',
    description: 'Secure password storage with breach monitoring',
    category: ServiceCategory.UTILITIES,
    status: ServiceStatus.ACTIVE,
    icon: 'Key',
    url: '/passwords',
    version: '2.8.0',
    tags: ['security', 'passwords', 'encryption'],
    features: ['Breach Monitoring', 'Password Generation', '2FA Support'],
    isActive: true,
    lastUpdated: '2024-01-19',
    popularity: 91
  },
  {
    id: 'file-organizer',
    name: 'FileOrganizer',
    description: 'AI-powered file organization and duplicate detection',
    category: ServiceCategory.UTILITIES,
    status: ServiceStatus.BETA,
    icon: 'FolderOpen',
    url: '/files',
    version: '0.9.0',
    tags: ['files', 'organization', 'ai'],
    features: ['Smart Sorting', 'Duplicate Detection', 'Bulk Operations'],
    isActive: true,
    lastUpdated: '2024-01-12',
    popularity: 73
  },

  // Security Services
  {
    id: 'security-audit',
    name: 'SecurityAudit',
    description: 'Comprehensive security assessment across all services',
    category: ServiceCategory.SECURITY,
    status: ServiceStatus.ACTIVE,
    icon: 'Shield',
    url: '/security',
    version: '1.5.0',
    tags: ['security', 'audit', 'vulnerability'],
    features: ['Vulnerability Scans', 'Access Reviews', 'Compliance Reports'],
    isActive: true,
    lastUpdated: '2024-01-17',
    popularity: 82
  },
  {
    id: 'privacy-monitor',
    name: 'PrivacyMonitor',
    description: 'Data privacy tracking and consent management',
    category: ServiceCategory.SECURITY,
    status: ServiceStatus.ACTIVE,
    icon: 'Eye',
    url: '/privacy',
    version: '1.3.0',
    tags: ['privacy', 'gdpr', 'consent'],
    features: ['Consent Tracking', 'Data Mapping', 'Privacy Reports'],
    isActive: true,
    lastUpdated: '2024-01-13',
    popularity: 77
  },

  // Integration Services
  {
    id: 'webhook-manager',
    name: 'WebhookManager',
    description: 'Webhook configuration and monitoring for all services',
    category: ServiceCategory.INTEGRATION,
    status: ServiceStatus.ACTIVE,
    icon: 'Webhook',
    url: '/webhooks',
    version: '2.2.0',
    tags: ['webhooks', 'integration', 'automation'],
    features: ['Endpoint Management', 'Retry Logic', 'Event Filtering'],
    isActive: true,
    lastUpdated: '2024-01-16',
    popularity: 75
  },
  {
    id: 'api-gateway',
    name: 'APIGateway',
    description: 'Unified API access point with rate limiting and auth',
    category: ServiceCategory.INTEGRATION,
    status: ServiceStatus.ACTIVE,
    icon: 'Globe',
    url: '/api-gateway',
    version: '3.0.0',
    tags: ['api', 'gateway', 'authentication'],
    features: ['Rate Limiting', 'API Keys', 'Request Routing'],
    isActive: true,
    lastUpdated: '2024-01-20',
    popularity: 89
  },
  {
    id: 'data-sync',
    name: 'DataSync',
    description: 'Cross-service data synchronization and backup',
    category: ServiceCategory.INTEGRATION,
    status: ServiceStatus.ACTIVE,
    icon: 'RefreshCw',
    url: '/sync',
    version: '2.4.0',
    tags: ['sync', 'backup', 'data'],
    features: ['Real-time Sync', 'Conflict Resolution', 'Backup Scheduling'],
    isActive: true,
    lastUpdated: '2024-01-18',
    popularity: 86
  },

  // Additional Specialized Services
  {
    id: 'weather-station',
    name: 'WeatherStation',
    description: 'Personal weather tracking with IoT sensor integration',
    category: ServiceCategory.UTILITIES,
    status: ServiceStatus.ACTIVE,
    icon: 'Cloud',
    url: '/weather',
    version: '1.7.0',
    tags: ['weather', 'iot', 'sensors'],
    features: ['Local Weather', 'Historical Data', 'Sensor Integration'],
    isActive: true,
    lastUpdated: '2024-01-14',
    popularity: 68
  },
  {
    id: 'garden-tracker',
    name: 'GardenTracker',
    description: 'Plant care scheduling and garden management',
    category: ServiceCategory.PERSONAL,
    status: ServiceStatus.ACTIVE,
    icon: 'Leaf',
    url: '/garden',
    version: '1.4.0',
    tags: ['gardening', 'plants', 'scheduling'],
    features: ['Plant Database', 'Care Reminders', 'Growth Tracking'],
    isActive: true,
    lastUpdated: '2024-01-11',
    popularity: 71
  },
  {
    id: 'recipe-manager',
    name: 'RecipeManager',
    description: 'Recipe collection with meal planning and nutrition',
    category: ServiceCategory.PERSONAL,
    status: ServiceStatus.ACTIVE,
    icon: 'ChefHat',
    url: '/recipes',
    version: '2.0.0',
    tags: ['recipes', 'cooking', 'nutrition'],
    features: ['Recipe Storage', 'Meal Planning', 'Nutrition Analysis'],
    isActive: true,
    lastUpdated: '2024-01-15',
    popularity: 79
  },
  {
    id: 'workout-planner',
    name: 'WorkoutPlanner',
    description: 'Personalized workout routines with progress tracking',
    category: ServiceCategory.HEALTH,
    status: ServiceStatus.ACTIVE,
    icon: 'Dumbbell',
    url: '/workout',
    version: '2.5.0',
    tags: ['fitness', 'workout', 'exercise'],
    features: ['Custom Routines', 'Progress Photos', 'Exercise Library'],
    isActive: true,
    lastUpdated: '2024-01-19',
    popularity: 88
  },
  {
    id: 'sleep-tracker',
    name: 'SleepTracker',
    description: 'Sleep quality monitoring with smart wake-up',
    category: ServiceCategory.HEALTH,
    status: ServiceStatus.ACTIVE,
    icon: 'Moon',
    url: '/sleep',
    version: '1.9.0',
    tags: ['sleep', 'health', 'monitoring'],
    features: ['Sleep Stages', 'Smart Alarms', 'Sleep Hygiene Tips'],
    isActive: true,
    lastUpdated: '2024-01-16',
    popularity: 85
  },
  {
    id: 'pet-tracker',
    name: 'PetTracker',
    description: 'Comprehensive pet care and health monitoring',
    category: ServiceCategory.PERSONAL,
    status: ServiceStatus.ACTIVE,
    icon: 'Heart',
    url: '/pets',
    version: '1.6.0',
    tags: ['pets', 'health', 'care'],
    features: ['Vet Appointments', 'Vaccination Records', 'Feeding Schedule'],
    isActive: true,
    lastUpdated: '2024-01-13',
    popularity: 74
  },
  {
    id: 'car-maintenance',
    name: 'CarMaintenance',
    description: 'Vehicle maintenance scheduling and expense tracking',
    category: ServiceCategory.UTILITIES,
    status: ServiceStatus.ACTIVE,
    icon: 'Car',
    url: '/car',
    version: '1.8.0',
    tags: ['automotive', 'maintenance', 'expenses'],
    features: ['Service Reminders', 'Expense Tracking', 'Fuel Efficiency'],
    isActive: true,
    lastUpdated: '2024-01-12',
    popularity: 69
  },
  {
    id: 'subscription-manager',
    name: 'SubscriptionManager',
    description: 'Track and manage all recurring subscriptions',
    category: ServiceCategory.FINANCE,
    status: ServiceStatus.ACTIVE,
    icon: 'CreditCard',
    url: '/subscriptions',
    version: '1.5.0',
    tags: ['subscriptions', 'finance', 'recurring'],
    features: ['Renewal Alerts', 'Cost Analysis', 'Cancellation Tracking'],
    isActive: true,
    lastUpdated: '2024-01-14',
    popularity: 76
  },
  {
    id: 'energy-monitor',
    name: 'EnergyMonitor',
    description: 'Home energy usage tracking and optimization',
    category: ServiceCategory.UTILITIES,
    status: ServiceStatus.BETA,
    icon: 'Zap',
    url: '/energy',
    version: '0.7.0',
    tags: ['energy', 'smart-home', 'optimization'],
    features: ['Usage Tracking', 'Cost Optimization', 'Device Monitoring'],
    isActive: true,
    lastUpdated: '2024-01-10',
    popularity: 67
  },
  {
    id: 'universal-translator',
    name: 'UniversalTranslator',
    description: 'Multi-modal translation system for text, speech, and more',
    category: ServiceCategory.COMMUNICATION,
    status: ServiceStatus.ACTIVE,
    icon: 'Languages',
    url: '/translator',
    version: '1.0.0',
    tags: ['translation', 'ai', 'multilingual'],
    features: ['Speech Translation', 'Document Translation', 'Sign Language'],
    isActive: true,
    lastUpdated: '2024-01-21',
    popularity: 92
  }
];

export const getServicesByCategory = (category: ServiceCategory): Service[] => {
  return services.filter(service => service.category === category);
};

export const getActiveServices = (): Service[] => {
  return services.filter(service => service.isActive && service.status === ServiceStatus.ACTIVE);
};

export const getPopularServices = (limit: number = 10): Service[] => {
  return services
    .sort((a, b) => b.popularity - a.popularity)
    .slice(0, limit);
};

export const searchServices = (query: string): Service[] => {
  const lowercaseQuery = query.toLowerCase();
  return services.filter(service =>
    service.name.toLowerCase().includes(lowercaseQuery) ||
    service.description.toLowerCase().includes(lowercaseQuery) ||
    service.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery))
  );
};