export interface Service {
  id: string;
  name: string;
  description: string;
  category: ServiceCategory;
  status: ServiceStatus;
  icon: string;
  url: string;
  version: string;
  tags: string[];
  features: string[];
  isActive: boolean;
  lastUpdated: string;
  popularity: number;
}

export enum ServiceCategory {
  PERSONAL = 'personal',
  BUSINESS = 'business',
  FISHING = 'fishing',
  HEALTH = 'health',
  FINANCE = 'finance',
  TRAVEL = 'travel',
  EDUCATION = 'education',
  ENTERTAINMENT = 'entertainment',
  PRODUCTIVITY = 'productivity',
  COMMUNICATION = 'communication',
  DEVELOPMENT = 'development',
  ANALYTICS = 'analytics',
  UTILITIES = 'utilities',
  SECURITY = 'security',
  INTEGRATION = 'integration'
}

export enum ServiceStatus {
  ACTIVE = 'active',
  MAINTENANCE = 'maintenance',
  DEPRECATED = 'deprecated',
  BETA = 'beta',
  COMING_SOON = 'coming_soon'
}

export interface ServiceMetrics {
  totalServices: number;
  activeServices: number;
  categoryCounts: Record<ServiceCategory, number>;
  popularServices: Service[];
}