import Redis from 'ioredis';
import { EventEmitter } from 'events';
import * as zlib from 'zlib';
import { promisify } from 'util';
import { v4 as uuidv4 } from 'uuid';
import { Logger } from '@/utils/logger';
import { 
  SyncRequest, 
  SyncResponse, 
  EntityUpdate, 
  EntityDelete, 
  OfflineOperation, 
  ConflictResolution,
  BatchRequest,
  BatchResponse,
  OperationType,
  ConflictStrategy,
  ConnectionState,
  SyncStats
} from '@/types/sync';

const gzip = promisify(zlib.gzip);
const gunzip = promisify(zlib.gunzip);

export interface SyncConfig {
  redis: {
    host: string;
    port: number;
    password?: string;
  };
  maxBatchSize: number;
  compressionThreshold: number;
  conflictRetentionDays: number;
  maxQueueSize: number;
  syncTimeoutMs: number;
}

export class SyncService extends EventEmitter {
  private redis: Redis;
  private logger: Logger;
  private config: SyncConfig;
  private syncLocks: Map<string, boolean> = new Map();

  constructor(config: SyncConfig) {
    super();
    this.config = config;
    this.logger = new Logger('SyncService');
    this.redis = new Redis({
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password,
      retryDelayOnFailover: 100,
      enableReadyCheck: false,
      maxRetriesPerRequest: null
    });
  }

  async performSync(request: SyncRequest): Promise<SyncResponse> {
    const startTime = Date.now();
    const lockKey = `sync_lock:${request.userId}:${request.deviceId}`;
    
    try {
      // Acquire sync lock to prevent concurrent syncs
      const acquired = await this.acquireSyncLock(lockKey);
      if (!acquired) {
        throw new Error('Sync already in progress for this device');
      }

      this.logger.info(`Starting sync for user ${request.userId}, device ${request.deviceId}`);

      // Get incremental changes since last sync
      const updates = await this.getIncrementalUpdates(
        request.userId,
        request.lastSyncTimestamp,
        request.entityTypes,
        request.options
      );

      // Get deletions since last sync
      const deletes = await this.getIncrementalDeletes(
        request.userId,
        request.lastSyncTimestamp,
        request.entityTypes
      );

      // Prepare response
      const serverTimestamp = Date.now();
      let responseData = { updates, deletes };

      // Apply compression if enabled and data is large enough
      let compressed = false;
      if (request.options?.compress && this.shouldCompress(responseData)) {
        responseData = await this.compressData(responseData);
        compressed = true;
      }

      // Calculate transfer size
      const transferSize = Buffer.byteLength(JSON.stringify(responseData));

      const response: SyncResponse = {
        success: true,
        errorMessage: null,
        serverTimestamp,
        updates: responseData.updates,
        deletes: responseData.deletes,
        metadata: {
          totalUpdates: updates.length,
          totalDeletes: deletes.length,
          nextSyncToken: serverTimestamp,
          hasMore: false, // Would implement pagination for large syncs
          compressionRatio: compressed ? Math.round((1 - transferSize / Buffer.byteLength(JSON.stringify({ updates, deletes }))) * 100) : 0,
          transferSizeBytes: transferSize
        }
      };

      // Update sync timestamp for device
      await this.updateDeviceSyncTimestamp(request.userId, request.deviceId, serverTimestamp);

      // Record sync statistics
      await this.recordSyncStats(request.userId, request.deviceId, {
        duration: Date.now() - startTime,
        updatesCount: updates.length,
        deletesCount: deletes.length,
        transferSize,
        compressed
      });

      this.logger.info(`Sync completed for user ${request.userId}, device ${request.deviceId}: ${updates.length} updates, ${deletes.length} deletes`);

      return response;

    } catch (error) {
      this.logger.error(`Sync failed for user ${request.userId}, device ${request.deviceId}`, error);
      
      return {
        success: false,
        errorMessage: error instanceof Error ? error.message : 'Unknown sync error',
        serverTimestamp: Date.now(),
        updates: [],
        deletes: [],
        metadata: {
          totalUpdates: 0,
          totalDeletes: 0,
          nextSyncToken: 0,
          hasMore: false,
          compressionRatio: 0,
          transferSizeBytes: 0
        }
      };

    } finally {
      // Release sync lock
      await this.releaseSyncLock(lockKey);
    }
  }

  async processBatchOperations(request: BatchRequest): Promise<BatchResponse> {
    const results: any[] = [];
    const serverTimestamp = Date.now();

    try {
      // Process operations in transaction if requested
      if (request.transactional) {
        const multi = this.redis.multi();
        
        for (const operation of request.operations) {
          await this.processBatchOperation(operation, multi);
        }
        
        await multi.exec();
      } else {
        // Process operations individually
        for (const operation of request.operations) {
          const result = await this.processBatchOperation(operation);
          results.push(result);
        }
      }

      return {
        success: true,
        errorMessage: null,
        results,
        serverTimestamp
      };

    } catch (error) {
      this.logger.error('Batch operation failed', error);
      
      return {
        success: false,
        errorMessage: error instanceof Error ? error.message : 'Batch operation failed',
        results: [],
        serverTimestamp
      };
    }
  }

  private async processBatchOperation(operation: any, multi?: any): Promise<any> {
    const version = Date.now();
    const entityKey = `entity:${operation.entityType}:${operation.entityId}`;
    
    try {
      switch (operation.operation) {
        case OperationType.CREATE:
        case OperationType.UPDATE:
          const data = operation.data;
          const serializedData = JSON.stringify(data);
          
          if (multi) {
            multi.hset(entityKey, {
              data: serializedData,
              version: version.toString(),
              updatedAt: new Date().toISOString(),
              operation: operation.operation.toString()
            });
          } else {
            await this.redis.hset(entityKey, {
              data: serializedData,
              version: version.toString(),
              updatedAt: new Date().toISOString(),
              operation: operation.operation.toString()
            });
          }
          
          // Add to change log
          await this.addToChangeLog(operation.entityType, operation.entityId, operation.operation, version);
          
          return {
            operationId: operation.operationId,
            success: true,
            errorMessage: null,
            entityId: operation.entityId,
            version,
            resultData: Buffer.from(serializedData)
          };

        case OperationType.DELETE:
          if (multi) {
            multi.del(entityKey);
          } else {
            await this.redis.del(entityKey);
          }
          
          // Add to deletion log
          await this.addToDeleteLog(operation.entityType, operation.entityId, version);
          
          return {
            operationId: operation.operationId,
            success: true,
            errorMessage: null,
            entityId: operation.entityId,
            version,
            resultData: null
          };

        default:
          throw new Error(`Unsupported operation: ${operation.operation}`);
      }
    } catch (error) {
      return {
        operationId: operation.operationId,
        success: false,
        errorMessage: error instanceof Error ? error.message : 'Operation failed',
        entityId: operation.entityId,
        version: 0,
        resultData: null
      };
    }
  }

  async queueOfflineOperation(userId: string, deviceId: string, operation: OfflineOperation): Promise<void> {
    const queueKey = `offline_queue:${userId}:${deviceId}`;
    
    // Check queue size limit
    const queueSize = await this.redis.llen(queueKey);
    if (queueSize >= this.config.maxQueueSize) {
      // Remove oldest operation
      await this.redis.lpop(queueKey);
    }
    
    // Add operation to queue
    const serializedOperation = JSON.stringify(operation);
    await this.redis.rpush(queueKey, serializedOperation);
    
    this.logger.info(`Queued offline operation for user ${userId}, device ${deviceId}: ${operation.entityType}:${operation.entityId}`);
  }

  async processOfflineQueue(userId: string, deviceId: string): Promise<{ processed: number; failed: number }> {
    const queueKey = `offline_queue:${userId}:${deviceId}`;
    let processed = 0;
    let failed = 0;

    try {
      while (true) {
        // Get next operation from queue
        const serializedOperation = await this.redis.lpop(queueKey);
        if (!serializedOperation) {
          break; // Queue is empty
        }

        try {
          const operation: OfflineOperation = JSON.parse(serializedOperation);
          
          // Process the operation
          await this.processBatchOperation({
            operationId: operation.id,
            entityType: operation.entityType,
            entityId: operation.entityId,
            operation: operation.operation,
            data: operation.data,
            metadata: {}
          });
          
          processed++;
          
        } catch (error) {
          this.logger.error('Failed to process offline operation', error);
          failed++;
          
          // Put operation back in queue for retry (with retry limit)
          const operation: OfflineOperation = JSON.parse(serializedOperation);
          if (operation.retryCount < 3) {
            operation.retryCount++;
            await this.redis.rpush(queueKey, JSON.stringify(operation));
          }
        }
      }

      this.logger.info(`Processed offline queue for user ${userId}, device ${deviceId}: ${processed} processed, ${failed} failed`);
      
      return { processed, failed };

    } catch (error) {
      this.logger.error('Failed to process offline queue', error);
      return { processed, failed };
    }
  }

  async resolveConflict(conflict: ConflictResolution): Promise<EntityUpdate> {
    const version = Date.now();
    let resolvedData: any;

    switch (conflict.strategy) {
      case ConflictStrategy.CLIENT_WINS:
        resolvedData = conflict.clientData;
        break;
        
      case ConflictStrategy.SERVER_WINS:
        resolvedData = conflict.serverData;
        break;
        
      case ConflictStrategy.LAST_WRITE_WINS:
        resolvedData = conflict.clientVersion > conflict.serverVersion 
          ? conflict.clientData 
          : conflict.serverData;
        break;
        
      case ConflictStrategy.MERGE:
        // Simple merge strategy - in practice, this would be entity-specific
        const clientData = JSON.parse(conflict.clientData.toString());
        const serverData = JSON.parse(conflict.serverData.toString());
        resolvedData = { ...serverData, ...clientData };
        break;
        
      default:
        throw new Error(`Unsupported conflict resolution strategy: ${conflict.strategy}`);
    }

    // Save resolved entity
    const entityKey = `entity:${conflict.entityType}:${conflict.entityId}`;
    const serializedData = JSON.stringify(resolvedData);
    
    await this.redis.hset(entityKey, {
      data: serializedData,
      version: version.toString(),
      updatedAt: new Date().toISOString(),
      operation: OperationType.UPDATE.toString()
    });

    // Add to change log
    await this.addToChangeLog(conflict.entityType, conflict.entityId, OperationType.UPDATE, version);

    // Remove from conflicts list
    await this.removeConflict(conflict.entityId);

    return {
      entityType: conflict.entityType,
      entityId: conflict.entityId,
      data: Buffer.from(serializedData),
      version,
      operation: OperationType.UPDATE,
      updatedAt: new Date(),
      metadata: { resolvedConflict: true }
    };
  }

  private async getIncrementalUpdates(
    userId: string,
    lastSyncTimestamp: number,
    entityTypes: string[],
    options?: any
  ): Promise<EntityUpdate[]> {
    const updates: EntityUpdate[] = [];
    
    for (const entityType of entityTypes) {
      const changeLogKey = `changelog:${entityType}`;
      
      // Get changes since last sync
      const changes = await this.redis.zrangebyscore(
        changeLogKey,
        lastSyncTimestamp + 1,
        '+inf',
        'WITHSCORES'
      );
      
      for (let i = 0; i < changes.length; i += 2) {
        const entityId = changes[i];
        const timestamp = parseInt(changes[i + 1]);
        
        // Check if entity belongs to user
        if (await this.entityBelongsToUser(entityType, entityId, userId)) {
          const entityData = await this.getEntityData(entityType, entityId);
          
          if (entityData) {
            updates.push({
              entityType,
              entityId,
              data: Buffer.from(entityData.data),
              version: parseInt(entityData.version),
              operation: parseInt(entityData.operation) as OperationType,
              updatedAt: new Date(entityData.updatedAt),
              metadata: {}
            });
          }
        }
      }
    }
    
    return updates;
  }

  private async getIncrementalDeletes(
    userId: string,
    lastSyncTimestamp: number,
    entityTypes: string[]
  ): Promise<EntityDelete[]> {
    const deletes: EntityDelete[] = [];
    
    for (const entityType of entityTypes) {
      const deleteLogKey = `deletelog:${entityType}`;
      
      // Get deletions since last sync
      const deletions = await this.redis.zrangebyscore(
        deleteLogKey,
        lastSyncTimestamp + 1,
        '+inf',
        'WITHSCORES'
      );
      
      for (let i = 0; i < deletions.length; i += 2) {
        const entityId = deletions[i];
        const timestamp = parseInt(deletions[i + 1]);
        
        // Check if deletion was for this user's entity
        if (await this.deletionBelongsToUser(entityType, entityId, userId, timestamp)) {
          deletes.push({
            entityType,
            entityId,
            version: timestamp,
            deletedAt: new Date(timestamp)
          });
        }
      }
    }
    
    return deletes;
  }

  private async addToChangeLog(entityType: string, entityId: string, operation: OperationType, version: number): Promise<void> {
    const changeLogKey = `changelog:${entityType}`;
    await this.redis.zadd(changeLogKey, version, entityId);
  }

  private async addToDeleteLog(entityType: string, entityId: string, version: number): Promise<void> {
    const deleteLogKey = `deletelog:${entityType}`;
    await this.redis.zadd(deleteLogKey, version, entityId);
  }

  private async entityBelongsToUser(entityType: string, entityId: string, userId: string): Promise<boolean> {
    // This would implement user ownership checks based on entity type
    // For now, return true (in practice, this would query the entity's owner)
    return true;
  }

  private async deletionBelongsToUser(entityType: string, entityId: string, userId: string, timestamp: number): Promise<boolean> {
    // This would check if the deleted entity belonged to the user
    // For now, return true
    return true;
  }

  private async getEntityData(entityType: string, entityId: string): Promise<any | null> {
    const entityKey = `entity:${entityType}:${entityId}`;
    const data = await this.redis.hgetall(entityKey);
    
    return Object.keys(data).length > 0 ? data : null;
  }

  private shouldCompress(data: any): boolean {
    const dataSize = Buffer.byteLength(JSON.stringify(data));
    return dataSize > this.config.compressionThreshold;
  }

  private async compressData(data: any): Promise<any> {
    const jsonData = JSON.stringify(data);
    const compressed = await gzip(jsonData);
    
    return {
      compressed: true,
      data: compressed.toString('base64')
    };
  }

  private async acquireSyncLock(lockKey: string): Promise<boolean> {
    const result = await this.redis.set(lockKey, '1', 'EX', 300, 'NX'); // 5 minute lock
    return result === 'OK';
  }

  private async releaseSyncLock(lockKey: string): Promise<void> {
    await this.redis.del(lockKey);
  }

  private async updateDeviceSyncTimestamp(userId: string, deviceId: string, timestamp: number): Promise<void> {
    const key = `device_sync:${userId}:${deviceId}`;
    await this.redis.hset(key, 'lastSyncTimestamp', timestamp.toString());
  }

  private async recordSyncStats(userId: string, deviceId: string, stats: any): Promise<void> {
    const key = `sync_stats:${userId}:${deviceId}`;
    const existing = await this.redis.hgetall(key);
    
    const updatedStats = {
      lastSyncTimestamp: Date.now().toString(),
      successfulSyncs: (parseInt(existing.successfulSyncs || '0') + 1).toString(),
      totalBytesDownloaded: (parseInt(existing.totalBytesDownloaded || '0') + stats.transferSize).toString(),
      averageSyncDurationMs: stats.duration.toString()
    };
    
    await this.redis.hset(key, updatedStats);
  }

  private async removeConflict(entityId: string): Promise<void> {
    const conflictKey = `conflict:${entityId}`;
    await this.redis.del(conflictKey);
  }

  async getSyncStats(userId: string, deviceId: string): Promise<SyncStats | null> {
    const key = `sync_stats:${userId}:${deviceId}`;
    const stats = await this.redis.hgetall(key);
    
    if (Object.keys(stats).length === 0) {
      return null;
    }
    
    return {
      lastSyncTimestamp: parseInt(stats.lastSyncTimestamp || '0'),
      successfulSyncs: parseInt(stats.successfulSyncs || '0'),
      failedSyncs: parseInt(stats.failedSyncs || '0'),
      totalBytesDownloaded: parseInt(stats.totalBytesDownloaded || '0'),
      totalBytesUploaded: parseInt(stats.totalBytesUploaded || '0'),
      conflictsResolved: parseInt(stats.conflictsResolved || '0'),
      operationsQueued: parseInt(stats.operationsQueued || '0'),
      averageSyncDurationMs: parseFloat(stats.averageSyncDurationMs || '0')
    };
  }

  async cleanup(): Promise<void> {
    await this.redis.quit();
    this.logger.info('Sync service cleanup completed');
  }
}