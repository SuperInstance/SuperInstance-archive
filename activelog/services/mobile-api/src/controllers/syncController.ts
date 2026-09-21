import { Request, Response } from 'express';
import { Logger } from '@/utils/logger';
import { SyncService } from '@/services/SyncService';
import { BatteryOptimizationService } from '@/services/BatteryOptimizationService';
import { SyncRequest, BatchRequest, ConflictResolution } from '@/types/sync';

const logger = new Logger('SyncController');

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    role: string;
  };
}

export const syncController = {
  async performSync(req: AuthenticatedRequest, res: Response) {
    try {
      const syncService = req.app.locals.services.syncService as SyncService;
      const batteryService = req.app.locals.services.batteryService as BatteryOptimizationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      let syncRequest: SyncRequest = req.body;

      // Validate request
      if (!syncRequest.deviceId || !syncRequest.entityTypes) {
        return res.status(400).json({ error: 'Device ID and entity types required' });
      }

      // Set user ID
      syncRequest.userId = userId;

      // Apply battery optimizations
      syncRequest = await batteryService.optimizeSyncRequest(syncRequest.deviceId, syncRequest);

      // Perform sync
      const response = await syncService.performSync(syncRequest);

      // Record sync event for battery analytics
      if (response.success) {
        await batteryService.recordSyncEvent(syncRequest.deviceId, {
          timestamp: response.serverTimestamp,
          batteryLevel: 100, // Would be provided by client
          connectionType: 1, // Would be provided by client
          syncDuration: Date.now() - response.serverTimestamp + (response.metadata?.transferSizeBytes || 0) / 1000,
          bytesTransferred: response.metadata?.transferSizeBytes || 0,
          success: true
        });
      }

      res.json(response);

    } catch (error) {
      logger.error('Sync failed', error);
      res.status(500).json({ 
        success: false, 
        errorMessage: 'Sync failed',
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
      });
    }
  },

  async processBatchOperations(req: AuthenticatedRequest, res: Response) {
    try {
      const syncService = req.app.locals.services.syncService as SyncService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const batchRequest: BatchRequest = {
        ...req.body,
        userId
      };

      if (!batchRequest.operations || !Array.isArray(batchRequest.operations)) {
        return res.status(400).json({ error: 'Operations array required' });
      }

      const response = await syncService.processBatchOperations(batchRequest);

      res.json(response);

    } catch (error) {
      logger.error('Batch operations failed', error);
      res.status(500).json({
        success: false,
        errorMessage: 'Batch operations failed',
        results: [],
        serverTimestamp: Date.now()
      });
    }
  },

  async processOfflineQueue(req: AuthenticatedRequest, res: Response) {
    try {
      const syncService = req.app.locals.services.syncService as SyncService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const { deviceId } = req.body;

      if (!deviceId) {
        return res.status(400).json({ error: 'Device ID required' });
      }

      const result = await syncService.processOfflineQueue(userId, deviceId);

      res.json({
        success: true,
        processed: result.processed,
        failed: result.failed,
        message: `Processed ${result.processed} operations, ${result.failed} failed`
      });

    } catch (error) {
      logger.error('Offline queue processing failed', error);
      res.status(500).json({ error: 'Failed to process offline queue' });
    }
  },

  async resolveConflict(req: AuthenticatedRequest, res: Response) {
    try {
      const syncService = req.app.locals.services.syncService as SyncService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const conflict: ConflictResolution = req.body;

      if (!conflict.entityId || !conflict.entityType || !conflict.strategy) {
        return res.status(400).json({ error: 'Entity ID, type, and strategy required' });
      }

      const resolved = await syncService.resolveConflict(conflict);

      res.json({
        success: true,
        resolvedEntity: resolved
      });

    } catch (error) {
      logger.error('Conflict resolution failed', error);
      res.status(500).json({ error: 'Failed to resolve conflict' });
    }
  },

  async getSyncStats(req: AuthenticatedRequest, res: Response) {
    try {
      const syncService = req.app.locals.services.syncService as SyncService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const { deviceId } = req.params;

      const stats = await syncService.getSyncStats(userId, deviceId);

      if (!stats) {
        return res.status(404).json({ error: 'No sync stats found for device' });
      }

      res.json(stats);

    } catch (error) {
      logger.error('Failed to get sync stats', error);
      res.status(500).json({ error: 'Failed to get sync stats' });
    }
  }
};