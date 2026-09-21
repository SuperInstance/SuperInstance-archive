// Sync Protocol Types
export interface SyncRequest {
  userId: string;
  deviceId: string;
  lastSyncTimestamp: number;
  entityTypes: string[];
  options?: SyncOptions;
}

export interface SyncOptions {
  incremental?: boolean;
  compress?: boolean;
  batchSize?: number;
  includeMetadata?: boolean;
  fields?: string[];
  batteryOptimization?: BatteryOptimization;
}

export interface BatteryOptimization {
  enabled: boolean;
  syncIntervalMinutes: number;
  wifiOnly: boolean;
  lowPowerMode: boolean;
  maxConcurrentOperations: number;
}

export interface SyncResponse {
  success: boolean;
  errorMessage: string | null;
  serverTimestamp: number;
  updates: EntityUpdate[];
  deletes: EntityDelete[];
  metadata: SyncMetadata;
}

export interface SyncMetadata {
  totalUpdates: number;
  totalDeletes: number;
  nextSyncToken: number;
  hasMore: boolean;
  compressionRatio: number;
  transferSizeBytes: number;
}

export interface EntityUpdate {
  entityType: string;
  entityId: string;
  data: Buffer;
  version: number;
  operation: OperationType;
  updatedAt: Date;
  metadata: { [key: string]: any };
}

export interface EntityDelete {
  entityType: string;
  entityId: string;
  version: number;
  deletedAt: Date;
}

export enum OperationType {
  CREATE = 0,
  UPDATE = 1,
  DELETE = 2,
  PARTIAL_UPDATE = 3
}

export interface ConflictResolution {
  entityId: string;
  entityType: string;
  strategy: ConflictStrategy;
  clientData: Buffer;
  serverData: Buffer;
  clientVersion: number;
  serverVersion: number;
}

export enum ConflictStrategy {
  CLIENT_WINS = 0,
  SERVER_WINS = 1,
  MERGE = 2,
  MANUAL = 3,
  LAST_WRITE_WINS = 4
}

export interface OfflineOperation {
  id: string;
  entityType: string;
  entityId: string;
  operation: OperationType;
  data: Buffer;
  createdAt: Date;
  retryCount: number;
  requiresNetwork: boolean;
  priority: number;
}

export interface BatchRequest {
  userId: string;
  deviceId: string;
  operations: BatchOperation[];
  transactional: boolean;
}

export interface BatchOperation {
  operationId: string;
  entityType: string;
  entityId: string;
  operation: OperationType;
  data: Buffer;
  metadata: { [key: string]: string };
}

export interface BatchResponse {
  success: boolean;
  errorMessage: string | null;
  results: BatchResult[];
  serverTimestamp: number;
}

export interface BatchResult {
  operationId: string;
  success: boolean;
  errorMessage: string | null;
  entityId: string;
  version: number;
  resultData: Buffer | null;
}

export interface ConnectionState {
  online: boolean;
  connectionType: ConnectionType;
  bandwidthKbps: number;
  latencyMs: number;
  meteredConnection: boolean;
  batteryLevel: number;
  lowPowerMode: boolean;
}

export enum ConnectionType {
  UNKNOWN = 0,
  WIFI = 1,
  CELLULAR = 2,
  ETHERNET = 3,
  BLUETOOTH = 4
}

export interface SyncStats {
  lastSyncTimestamp: number;
  successfulSyncs: number;
  failedSyncs: number;
  totalBytesDownloaded: number;
  totalBytesUploaded: number;
  conflictsResolved: number;
  operationsQueued: number;
  averageSyncDurationMs: number;
}