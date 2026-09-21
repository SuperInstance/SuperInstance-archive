/**
 * ActiveLog Plugin SDK - Type Definitions
 */

export interface PluginManifest {
  name: string;
  version: string;
  displayName?: string;
  description: string;
  author: {
    name: string;
    email?: string;
    url?: string;
  };
  license?: string;
  keywords?: string[];
  category: PluginCategory;
  main: string;
  runtime: PluginRuntime;
  permissions: PluginPermissions;
  resources?: PluginResources;
  triggers?: PluginTrigger[];
  config?: PluginConfig;
  dependencies?: PluginDependencies;
  ui?: PluginUI;
  api?: PluginAPI;
  compatibility?: PluginCompatibility;
  marketplace?: PluginMarketplace;
}

export type PluginCategory =
  | 'data-import'
  | 'data-export'
  | 'analytics'
  | 'automation'
  | 'integration'
  | 'utility'
  | 'visualization'
  | 'ai-ml'
  | 'security'
  | 'productivity';

export interface PluginRuntime {
  type: 'typescript' | 'python' | 'docker' | 'wasm';
  version?: string;
  environment?: 'node' | 'browser' | 'python3' | 'docker' | 'wasm';
}

export interface PluginPermissions {
  network?: {
    enabled?: boolean;
    domains?: string[];
    ports?: number[];
  };
  filesystem?: {
    read?: string[];
    write?: string[];
    temp?: boolean;
  };
  database?: {
    read?: boolean;
    write?: boolean;
    tables?: string[];
  };
  services?: ActiveLogService[];
}

export type ActiveLogService =
  | 'auth'
  | 'metadata'
  | 'file-sync'
  | 'ai-orchestrator'
  | 'video-pipeline'
  | 'analytics'
  | 'notifications';

export interface PluginResources {
  cpu?: number;
  memory?: string;
  disk?: string;
  network?: string;
  timeout?: number;
}

export interface PluginTrigger {
  type: TriggerType;
  config?: Record<string, any>;
}

export type TriggerType =
  | 'file-upload'
  | 'file-change'
  | 'schedule'
  | 'webhook'
  | 'user-action'
  | 'system-event';

export interface PluginConfig {
  schema?: Record<string, any>;
  defaults?: Record<string, any>;
}

export interface PluginDependencies {
  plugins?: Record<string, string>;
  npm?: Record<string, string>;
  pip?: Record<string, string>;
}

export interface PluginUI {
  settings?: string;
  dashboard?: string;
  icon?: string;
}

export interface PluginAPI {
  endpoints?: APIEndpoint[];
}

export interface APIEndpoint {
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  description?: string;
}

export interface PluginCompatibility {
  activelogVersion?: string;
  os?: ('linux' | 'windows' | 'macos' | 'any')[];
  arch?: ('x64' | 'arm64' | 'any')[];
}

export interface PluginMarketplace {
  pricing?: {
    model: 'free' | 'freemium' | 'paid' | 'subscription';
    price?: number;
    currency?: string;
  };
  featured?: boolean;
  verified?: boolean;
}

// Plugin Context and Runtime Types
export interface PluginContext {
  readonly manifest: PluginManifest;
  readonly config: Record<string, any>;
  readonly logger: PluginLogger;
  readonly storage: PluginStorage;
  readonly http: PluginHTTP;
  readonly database: PluginDatabase;
  readonly services: PluginServices;
  readonly events: PluginEvents;
  readonly user: UserContext;
  readonly organization: OrganizationContext;
}

export interface PluginLogger {
  debug(message: string, ...args: any[]): void;
  info(message: string, ...args: any[]): void;
  warn(message: string, ...args: any[]): void;
  error(message: string, error?: Error, ...args: any[]): void;
}

export interface PluginStorage {
  get(key: string): Promise<any>;
  set(key: string, value: any, ttl?: number): Promise<void>;
  delete(key: string): Promise<void>;
  exists(key: string): Promise<boolean>;
  keys(pattern?: string): Promise<string[]>;
  clear(): Promise<void>;
}

export interface PluginHTTP {
  get(url: string, options?: HTTPOptions): Promise<HTTPResponse>;
  post(url: string, data?: any, options?: HTTPOptions): Promise<HTTPResponse>;
  put(url: string, data?: any, options?: HTTPOptions): Promise<HTTPResponse>;
  delete(url: string, options?: HTTPOptions): Promise<HTTPResponse>;
  patch(url: string, data?: any, options?: HTTPOptions): Promise<HTTPResponse>;
}

export interface HTTPOptions {
  headers?: Record<string, string>;
  timeout?: number;
  retries?: number;
}

export interface HTTPResponse {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: any;
}

export interface PluginDatabase {
  query(sql: string, params?: any[]): Promise<DatabaseResult>;
  select(table: string, where?: Record<string, any>): Promise<DatabaseResult>;
  insert(table: string, data: Record<string, any>): Promise<DatabaseResult>;
  update(table: string, data: Record<string, any>, where?: Record<string, any>): Promise<DatabaseResult>;
  delete(table: string, where: Record<string, any>): Promise<DatabaseResult>;
}

export interface DatabaseResult {
  rows: Record<string, any>[];
  rowCount: number;
  fields: DatabaseField[];
}

export interface DatabaseField {
  name: string;
  type: string;
}

export interface PluginServices {
  auth: AuthService;
  metadata: MetadataService;
  fileSync: FileSyncService;
  aiOrchestrator: AIService;
  videoPipeline: VideoService;
  analytics: AnalyticsService;
  notifications: NotificationService;
}

export interface AuthService {
  getCurrentUser(): Promise<UserContext>;
  validateToken(token: string): Promise<boolean>;
  hasPermission(permission: string): Promise<boolean>;
}

export interface MetadataService {
  search(query: string, filters?: Record<string, any>): Promise<SearchResult>;
  getFile(fileId: string): Promise<FileMetadata>;
  updateFile(fileId: string, metadata: Partial<FileMetadata>): Promise<void>;
  createEmbedding(text: string): Promise<number[]>;
}

export interface SearchResult {
  total: number;
  results: FileMetadata[];
  aggregations?: Record<string, any>;
}

export interface FileMetadata {
  id: string;
  name: string;
  path: string;
  size: number;
  type: string;
  createdAt: Date;
  updatedAt: Date;
  metadata: Record<string, any>;
  tags: string[];
}

export interface FileSyncService {
  watch(path: string, callback: (event: FileEvent) => void): Promise<string>;
  unwatch(watchId: string): Promise<void>;
  sync(path: string): Promise<void>;
}

export interface FileEvent {
  type: 'created' | 'modified' | 'deleted';
  path: string;
  metadata?: FileMetadata;
}

export interface AIService {
  analyze(data: any, analysisType: string): Promise<AnalysisResult>;
  getJobStatus(jobId: string): Promise<JobStatus>;
  cancelJob(jobId: string): Promise<void>;
}

export interface AnalysisResult {
  jobId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

export interface JobStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result?: any;
  error?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface VideoService {
  upload(file: File): Promise<VideoUploadResult>;
  getStatus(videoId: string): Promise<VideoStatus>;
  transcode(videoId: string, options: TranscodeOptions): Promise<string>;
}

export interface VideoUploadResult {
  videoId: string;
  status: string;
  url: string;
}

export interface VideoStatus {
  videoId: string;
  status: string;
  progress: number;
  error?: string;
}

export interface TranscodeOptions {
  formats: string[];
  resolutions: string[];
  quality: string;
}

export interface AnalyticsService {
  track(event: string, properties?: Record<string, any>): Promise<void>;
  query(query: AnalyticsQuery): Promise<AnalyticsResult>;
}

export interface AnalyticsQuery {
  metric: string;
  dimensions?: string[];
  filters?: Record<string, any>;
  dateRange?: {
    start: Date;
    end: Date;
  };
}

export interface AnalyticsResult {
  data: Record<string, any>[];
  total: number;
  aggregations?: Record<string, any>;
}

export interface NotificationService {
  send(notification: NotificationRequest): Promise<string>;
  getStatus(notificationId: string): Promise<NotificationStatus>;
}

export interface NotificationRequest {
  type: 'email' | 'push' | 'in-app';
  recipient: string;
  title: string;
  message: string;
  data?: Record<string, any>;
}

export interface NotificationStatus {
  id: string;
  status: 'pending' | 'sent' | 'failed';
  sentAt?: Date;
  error?: string;
}

export interface PluginEvents {
  on(event: string, listener: (...args: any[]) => void): void;
  off(event: string, listener: (...args: any[]) => void): void;
  emit(event: string, ...args: any[]): void;
  once(event: string, listener: (...args: any[]) => void): void;
}

export interface UserContext {
  id: string;
  username: string;
  email: string;
  name: string;
  avatar?: string;
  permissions: string[];
  preferences: Record<string, any>;
}

export interface OrganizationContext {
  id: string;
  name: string;
  plan: string;
  features: string[];
  limits: Record<string, number>;
}

// Plugin Base Class Interface
export interface PluginInterface {
  /**
   * Called when the plugin is first loaded
   */
  onLoad?(context: PluginContext): Promise<void>;

  /**
   * Called when the plugin is activated
   */
  onActivate?(context: PluginContext): Promise<void>;

  /**
   * Called when the plugin is deactivated
   */
  onDeactivate?(context: PluginContext): Promise<void>;

  /**
   * Called when the plugin is unloaded
   */
  onUnload?(context: PluginContext): Promise<void>;

  /**
   * Called when configuration changes
   */
  onConfigChange?(config: Record<string, any>, context: PluginContext): Promise<void>;

  /**
   * Called when a trigger event occurs
   */
  onTrigger?(event: TriggerEvent, context: PluginContext): Promise<TriggerResult>;

  /**
   * Called for API endpoint handlers
   */
  handleAPI?(path: string, method: string, data: any, context: PluginContext): Promise<any>;
}

export interface TriggerEvent {
  type: TriggerType;
  data: Record<string, any>;
  timestamp: Date;
}

export interface TriggerResult {
  success: boolean;
  data?: any;
  error?: string;
}

// Error Types
export class PluginError extends Error {
  constructor(
    message: string,
    public code?: string,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'PluginError';
  }
}

export class PermissionError extends PluginError {
  constructor(permission: string) {
    super(`Permission denied: ${permission}`, 'PERMISSION_DENIED', { permission });
    this.name = 'PermissionError';
  }
}

export class ResourceLimitError extends PluginError {
  constructor(resource: string, limit: string) {
    super(`Resource limit exceeded: ${resource} (${limit})`, 'RESOURCE_LIMIT', { resource, limit });
    this.name = 'ResourceLimitError';
  }
}

export class ValidationError extends PluginError {
  constructor(field: string, message: string) {
    super(`Validation error: ${field} - ${message}`, 'VALIDATION_ERROR', { field });
    this.name = 'ValidationError';
  }
}