const logger = require('../utils/logger');
const World = require('../models/World');
const { generateUniqueId } = require('../utils/helpers');

class CollaborationService {
  constructor() {
    this.activeSessions = new Map(); // userId -> sessionData
    this.worldSessions = new Map(); // worldId -> Set of userIds
    this.operationQueue = new Map(); // worldId -> operations[]
  }

  // Handle real-time collaboration for a socket connection
  handleCollaboration(socket, io) {
    // User joins a world for collaboration
    socket.on('join-collaboration', async (data) => {
      try {
        const { worldId, userId, userName, permissions } = data;
        
        // Validate world exists and user has access
        const world = await World.findOne({ worldId });
        if (!world) {
          socket.emit('collaboration-error', { error: 'World not found' });
          return;
        }

        // Check permissions
        if (!this.hasPermission(world, userId, 'view')) {
          socket.emit('collaboration-error', { error: 'Access denied' });
          return;
        }

        // Join socket room
        socket.join(`world:${worldId}`);
        socket.worldId = worldId;
        socket.userId = userId;

        // Add to active sessions
        const sessionData = {
          userId,
          userName,
          worldId,
          socketId: socket.id,
          joinedAt: new Date(),
          lastActivity: new Date(),
          currentContext: { type: 'world' },
          cursor: { x: 0, y: 0 },
          permissions: permissions || this.getDefaultPermissions(world, userId)
        };

        this.activeSessions.set(userId, sessionData);

        // Track world sessions
        if (!this.worldSessions.has(worldId)) {
          this.worldSessions.set(worldId, new Set());
        }
        this.worldSessions.get(worldId).add(userId);

        // Update world document with collaborator info
        await world.addCollaborator(userId, userName, sessionData.permissions);
        await world.save();

        // Notify other collaborators
        socket.to(`world:${worldId}`).emit('collaborator-joined', {
          userId,
          userName,
          timestamp: new Date()
        });

        // Send current collaborators list to new user
        const activeCollaborators = Array.from(this.worldSessions.get(worldId))
          .map(uid => this.activeSessions.get(uid))
          .filter(Boolean);

        socket.emit('collaboration-state', {
          collaborators: activeCollaborators,
          worldState: await this.getWorldSnapshot(worldId)
        });

        logger.info(`User ${userId} joined collaboration for world ${worldId}`);

      } catch (error) {
        logger.error('Join collaboration error:', error);
        socket.emit('collaboration-error', { error: error.message });
      }
    });

    // Handle context switching (character -> map -> story, etc.)
    socket.on('switch-context', async (data) => {
      try {
        const { worldId, fromContext, toContext, contextData } = data;
        const userId = socket.userId;

        if (!userId || !this.activeSessions.has(userId)) {
          socket.emit('collaboration-error', { error: 'Not in collaboration session' });
          return;
        }

        const session = this.activeSessions.get(userId);
        session.currentContext = {
          type: toContext,
          ...contextData
        };
        session.lastActivity = new Date();

        // Broadcast context switch to other collaborators
        socket.to(`world:${worldId}`).emit('collaborator-context-changed', {
          userId,
          userName: session.userName,
          fromContext,
          toContext,
          contextData,
          timestamp: new Date()
        });

        // Update cursor position if provided
        if (contextData.cursor) {
          session.cursor = contextData.cursor;
          socket.to(`world:${worldId}`).emit('collaborator-cursor-moved', {
            userId,
            cursor: contextData.cursor
          });
        }

        logger.info(`User ${userId} switched context from ${fromContext} to ${toContext}`);

      } catch (error) {
        logger.error('Context switch error:', error);
        socket.emit('collaboration-error', { error: error.message });
      }
    });

    // Handle real-time content updates
    socket.on('content-change', async (data) => {
      try {
        const { worldId, operation, path, value, metadata } = data;
        const userId = socket.userId;

        if (!userId || !this.activeSessions.has(userId)) {
          socket.emit('collaboration-error', { error: 'Not in collaboration session' });
          return;
        }

        const session = this.activeSessions.get(userId);
        
        // Check edit permissions
        if (!session.permissions.edit) {
          socket.emit('collaboration-error', { error: 'No edit permission' });
          return;
        }

        // Create operation object
        const operationId = generateUniqueId();
        const operationData = {
          id: operationId,
          userId,
          userName: session.userName,
          timestamp: new Date(),
          type: operation, // 'create', 'update', 'delete'
          path, // JSON path like 'content.locations.0.name'
          value,
          oldValue: null, // Will be populated when applying
          metadata
        };

        // Queue operation for processing
        if (!this.operationQueue.has(worldId)) {
          this.operationQueue.set(worldId, []);
        }
        this.operationQueue.get(worldId).push(operationData);

        // Process operation queue
        await this.processOperationQueue(worldId);

        // Broadcast to other collaborators immediately for real-time feel
        socket.to(`world:${worldId}`).emit('content-updated', operationData);

        logger.info(`Content change by ${userId} in world ${worldId}: ${operation} at ${path}`);

      } catch (error) {
        logger.error('Content change error:', error);
        socket.emit('collaboration-error', { error: error.message });
      }
    });

    // Handle cursor movement for real-time presence
    socket.on('cursor-move', (data) => {
      const { worldId, x, y, context } = data;
      const userId = socket.userId;

      if (!userId || !this.activeSessions.has(userId)) return;

      const session = this.activeSessions.get(userId);
      session.cursor = { x, y };
      session.lastActivity = new Date();

      // Broadcast cursor position
      socket.to(`world:${worldId}`).emit('collaborator-cursor-moved', {
        userId,
        userName: session.userName,
        cursor: { x, y },
        context
      });
    });

    // Handle selection changes (for highlighting what user is editing)
    socket.on('selection-change', (data) => {
      const { worldId, selection } = data;
      const userId = socket.userId;

      if (!userId || !this.activeSessions.has(userId)) return;

      socket.to(`world:${worldId}`).emit('collaborator-selection-changed', {
        userId,
        userName: this.activeSessions.get(userId).userName,
        selection,
        timestamp: new Date()
      });
    });

    // Handle disconnection
    socket.on('disconnect', async () => {
      await this.handleDisconnection(socket);
    });

    socket.on('leave-collaboration', async () => {
      await this.handleDisconnection(socket);
    });
  }

  // Process queued operations for a world
  async processOperationQueue(worldId) {
    const queue = this.operationQueue.get(worldId);
    if (!queue || queue.length === 0) return;

    try {
      const world = await World.findOne({ worldId });
      if (!world) return;

      // Process all queued operations
      const operations = [...queue];
      this.operationQueue.set(worldId, []); // Clear queue

      for (const operation of operations) {
        await this.applyOperation(world, operation);
      }

      // Save world with all changes
      await world.save();

    } catch (error) {
      logger.error(`Error processing operation queue for world ${worldId}:`, error);
      // Re-add operations to queue if save failed
      const currentQueue = this.operationQueue.get(worldId) || [];
      this.operationQueue.set(worldId, [...operations, ...currentQueue]);
    }
  }

  // Apply a single operation to the world document
  async applyOperation(world, operation) {
    const { type, path, value } = operation;

    try {
      // Get current value for undo functionality
      const currentValue = this.getValueAtPath(world, path);
      operation.oldValue = currentValue;

      switch (type) {
        case 'create':
          this.setValueAtPath(world, path, value);
          break;
        case 'update':
          this.setValueAtPath(world, path, value);
          break;
        case 'delete':
          this.deleteValueAtPath(world, path);
          break;
        default:
          throw new Error(`Unknown operation type: ${type}`);
      }

    } catch (error) {
      logger.error('Error applying operation:', error);
      throw error;
    }
  }

  // Utility functions for JSON path operations
  getValueAtPath(obj, path) {
    return path.split('.').reduce((current, key) => {
      if (current && typeof current === 'object') {
        return current[key];
      }
      return undefined;
    }, obj);
  }

  setValueAtPath(obj, path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((current, key) => {
      if (!current[key]) current[key] = {};
      return current[key];
    }, obj);
    
    target[lastKey] = value;
  }

  deleteValueAtPath(obj, path) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((current, key) => current && current[key], obj);
    
    if (target) {
      delete target[lastKey];
    }
  }

  // Handle user disconnection
  async handleDisconnection(socket) {
    const { userId, worldId } = socket;
    
    if (!userId) return;

    try {
      // Remove from active sessions
      this.activeSessions.delete(userId);

      if (worldId) {
        // Remove from world session
        const worldSession = this.worldSessions.get(worldId);
        if (worldSession) {
          worldSession.delete(userId);
          if (worldSession.size === 0) {
            this.worldSessions.delete(worldId);
          }
        }

        // Update world document
        const world = await World.findOne({ worldId });
        if (world) {
          world.removeCollaborator(userId);
          await world.save();
        }

        // Notify other collaborators
        socket.to(`world:${worldId}`).emit('collaborator-left', {
          userId,
          timestamp: new Date()
        });

        logger.info(`User ${userId} left collaboration for world ${worldId}`);
      }

    } catch (error) {
      logger.error('Disconnection handling error:', error);
    }
  }

  // Check user permissions
  hasPermission(world, userId, permission) {
    // Check if user is creator
    if (world.creator === userId) return true;

    // Check admin users
    if (world.permissions.adminUsers.includes(userId)) return true;

    // Check specific permission lists
    switch (permission) {
      case 'view':
        return world.permissions.public || 
               world.permissions.viewUsers.includes(userId) ||
               world.permissions.editUsers.includes(userId);
      case 'edit':
        return world.permissions.editUsers.includes(userId);
      case 'admin':
        return world.permissions.adminUsers.includes(userId);
      default:
        return false;
    }
  }

  // Get default permissions for user
  getDefaultPermissions(world, userId) {
    return {
      edit: this.hasPermission(world, userId, 'edit'),
      create: this.hasPermission(world, userId, 'edit'),
      delete: this.hasPermission(world, userId, 'admin'),
      ai: this.hasPermission(world, userId, 'edit')
    };
  }

  // Get current world snapshot for new collaborators
  async getWorldSnapshot(worldId) {
    try {
      const world = await World.findOne({ worldId }).lean();
      if (!world) return null;

      // Return relevant data for collaboration
      return {
        worldId: world.worldId,
        name: world.name,
        description: world.description,
        currentVersion: world.currentVersion,
        lastModified: world.lastModified,
        content: world.content
      };

    } catch (error) {
      logger.error('Error getting world snapshot:', error);
      return null;
    }
  }

  // Get active collaborators for a world
  getActiveCollaborators(worldId) {
    const worldSession = this.worldSessions.get(worldId);
    if (!worldSession) return [];

    return Array.from(worldSession)
      .map(userId => this.activeSessions.get(userId))
      .filter(Boolean);
  }

  // Force save all pending operations for a world
  async forceSave(worldId) {
    await this.processOperationQueue(worldId);
  }
}

// Export singleton instance
const collaborationService = new CollaborationService();

module.exports = {
  CollaborationService,
  handleCollaboration: (socket, io) => collaborationService.handleCollaboration(socket, io),
  getActiveCollaborators: (worldId) => collaborationService.getActiveCollaborators(worldId),
  forceSave: (worldId) => collaborationService.forceSave(worldId)
};