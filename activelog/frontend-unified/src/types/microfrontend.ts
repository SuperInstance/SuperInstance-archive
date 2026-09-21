export interface MicroFrontend {
  id: string;
  name: string;
  url: string;
  port: number;
  status: MicroFrontendStatus;
  loadingStrategy: LoadingStrategy;
  authentication: AuthenticationConfig;
  features: string[];
  dependencies: string[];
  version: string;
  healthCheckUrl?: string;
  entryPoint: string;
  config: Record<string, any>;
}

export enum MicroFrontendStatus {
  AVAILABLE = 'available',
  LOADING = 'loading',
  LOADED = 'loaded',
  ERROR = 'error',
  OFFLINE = 'offline',
  MAINTENANCE = 'maintenance'
}

export enum LoadingStrategy {
  IFRAME = 'iframe',
  MODULE_FEDERATION = 'module_federation',
  DYNAMIC_IMPORT = 'dynamic_import',
  WEB_COMPONENTS = 'web_components'
}

export interface AuthenticationConfig {
  required: boolean;
  tokenSharing: boolean;
  ssoEnabled: boolean;
  roles: string[];
}

export interface MicroFrontendConfig {
  baseUrl: string;
  authToken?: string;
  userId?: string;
  userRole?: string;
  theme: 'light' | 'dark' | 'auto';
  language: string;
  features: Record<string, boolean>;
}

export interface MicroFrontendLoadOptions {
  containerId: string;
  config: MicroFrontendConfig;
  onLoad?: () => void;
  onError?: (error: Error) => void;
  onMessage?: (message: any) => void;
}

export interface CrossAppMessage {
  type: string;
  source: string;
  target: string;
  payload: any;
  timestamp: number;
  messageId: string;
}

export interface ServiceRoute {
  path: string;
  serviceId: string;
  microFrontendId: string;
  exact?: boolean;
  auth?: boolean;
  roles?: string[];
  title?: string;
  description?: string;
}

// Enhanced service types for micro-frontend integration
export interface EnhancedService {
  id: string;
  name: string;
  microFrontend: MicroFrontend;
  routes: ServiceRoute[];
  navigation: NavigationItem[];
  integrations: string[];
  apiEndpoints: string[];
  permissions: string[];
}

export interface NavigationItem {
  label: string;
  path: string;
  icon?: string;
  children?: NavigationItem[];
  auth?: boolean;
  roles?: string[];
}