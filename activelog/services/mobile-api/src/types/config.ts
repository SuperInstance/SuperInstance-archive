// App Configuration Types
export interface AppConfig {
  version: string;
  minVersionCode: number;
  forceUpdate: boolean;
  updateUrl: string;
  features: FeatureFlags;
  endpoints: ApiEndpoints;
  imageOptimization: ImageOptimization;
  syncConfig: SyncConfiguration;
  security: SecuritySettings;
  updatedAt: Date;
}

export interface FeatureFlags {
  flags: Map<string, boolean>;
  experiments: ExperimentFlag[];
}

export interface ExperimentFlag {
  name: string;
  enabled: boolean;
  rolloutPercentage: number;
  targetGroups: string[];
}

export interface ApiEndpoints {
  baseUrl: string;
  graphqlUrl: string;
  uploadUrl: string;
  cdnUrl: string;
  wsUrl: string;
  serviceUrls: Map<string, string>;
}

export interface ImageOptimization {
  sizes: ImageSize[];
  formats: string[];
  quality: number;
  progressive: boolean;
  webpEnabled: boolean;
}

export interface ImageSize {
  name: string;
  width: number;
  height: number;
  crop: boolean;
}

export interface SyncConfiguration {
  batchSize: number;
  retryAttempts: number;
  retryDelayMs: number;
  timeoutMs: number;
  compressionEnabled: boolean;
  maxQueueSize: number;
}

export interface SecuritySettings {
  certificatePinning: boolean;
  sessionTimeoutMinutes: number;
  biometricAuth: boolean;
  maxLoginAttempts: number;
  lockoutDurationMinutes: number;
}