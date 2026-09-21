const WebSocket = require('ws');
const { EventEmitter } = require('events');
const crypto = require('crypto');

class CollaborationService extends EventEmitter {
  constructor(environmentManager, liveEditingService, config = {}) {
    super();
    
    this.environmentManager = environmentManager;
    this.liveEditingService = liveEditingService;
    this.config = {
      // Collaboration settings
      maxCollaboratorsPerProject: config.maxCollaboratorsPerProject || 10,
      enableRealTimeEditing: config.enableRealTimeEditing ?? true,
      enableVoiceChat: config.enableVoiceChat ?? false,
      enableScreenSharing: config.enableScreenSharing ?? false,
      
      // Permissions
      defaultRole: config.defaultRole || 'viewer', // owner, admin, editor, viewer
      enableRoleBasedAccess: config.enableRoleBasedAccess ?? true,
      
      // Real-time features
      enableCursors: config.enableCursors ?? true,
      enableSelections: config.enableSelections ?? true,
      enableComments: config.enableComments ?? true,
      enableChat: config.enableChat ?? true,
      
      // Conflict resolution
      enableOperationalTransform: config.enableOperationalTransform ?? true,
      conflictResolutionStrategy: config.conflictResolutionStrategy || 'last-write-wins', // ot, lww, manual
      
      // Session management
      sessionTimeout: config.sessionTimeout || 24 * 60 * 60 * 1000, // 24 hours
      inactivityTimeout: config.inactivityTimeout || 30 * 60 * 1000, // 30 minutes
      
      ...config
    };

    this.collaborationSpaces = new Map(); // spaceId -> space info
    this.userSessions = new Map(); // userId -> session info
    this.documentStates = new Map(); // documentId -> operational transform state
    this.activeOperations = new Map(); // operationId -> operation
    this.chatRooms = new Map(); // spaceId -> chat messages
    this.comments = new Map(); // documentId -> comments
    
    this.stats = {
      totalSpaces: 0,
      activeSpaces: 0,
      totalCollaborators: 0,
      activeCollaborators: 0,
      messagesExchanged: 0,
      operationsApplied: 0,
      conflictsResolved: 0
    };

    this.operationQueue = new Map(); // spaceId -> operation queue
    this.setupOperationalTransform();
  }

  // Setup operational transformation
  setupOperationalTransform() {
    if (!this.config.enableOperationalTransform) return;
    
    // Process operation queues periodically
    setInterval(() => {
      this.processOperationQueues();
    }, 100); // Process every 100ms
  }

  // Create collaboration space
  async createCollaborationSpace(userId, spaceConfig) {
    try {
      const spaceId = crypto.randomUUID();
      
      const space = {
        id: spaceId,
        name: spaceConfig.name || 'Untitled Project',
        description: spaceConfig.description || '',
        ownerId: userId,
        environmentId: spaceConfig.environmentId,
        
        // Collaboration settings
        settings: {
          isPublic: spaceConfig.isPublic || false,
          allowGuests: spaceConfig.allowGuests || false,
          maxCollaborators: spaceConfig.maxCollaborators || this.config.maxCollaboratorsPerProject,
          requireApproval: spaceConfig.requireApproval || false,
          ...spaceConfig.settings
        },
        
        // Members and roles
        members: new Map([[userId, {
          userId,
          role: 'owner',
          permissions: this.getPermissions('owner'),
          joinedAt: new Date(),
          lastActivity: new Date(),
          isActive: true
        }]]),
        
        // Active sessions
        activeSessions: new Map(),
        
        // Documents being edited
        documents: new Map(),
        
        // State
        createdAt: new Date(),
        lastActivity: new Date(),
        status: 'active'
      };

      this.collaborationSpaces.set(spaceId, space);
      this.chatRooms.set(spaceId, []);
      this.operationQueue.set(spaceId, []);
      
      this.stats.totalSpaces++;
      this.stats.activeSpaces++;

      this.emit('spaceCreated', space);
      
      return space;
      
    } catch (error) {
      this.emit('spaceError', { userId, error });
      throw error;
    }
  }

  // Join collaboration space
  async joinCollaborationSpace(userId, spaceId, joinConfig = {}) {
    try {
      const space = this.collaborationSpaces.get(spaceId);
      if (!space) {
        throw new Error('Collaboration space not found');
      }

      // Check permissions
      if (!space.settings.isPublic && !space.members.has(userId)) {
        if (!space.settings.allowGuests && !joinConfig.inviteToken) {
          throw new Error('Access denied: space is private');
        }
      }

      // Check member limit
      if (space.members.size >= space.settings.maxCollaborators) {
        throw new Error('Collaboration space is full');
      }

      // Add member if not already exists
      if (!space.members.has(userId)) {
        const role = joinConfig.role || this.config.defaultRole;
        space.members.set(userId, {
          userId,
          role,
          permissions: this.getPermissions(role),
          joinedAt: new Date(),
          lastActivity: new Date(),
          isActive: true,
          invitedBy: joinConfig.invitedBy
        });
      }

      // Create collaboration session
      const sessionId = crypto.randomUUID();
      const session = {
        id: sessionId,
        userId,
        spaceId,
        joinedAt: new Date(),
        lastActivity: new Date(),
        cursor: null,
        selection: null,
        currentDocument: null,
        isActive: true
      };

      space.activeSessions.set(sessionId, session);
      this.userSessions.set(userId, session);
      
      // Update member activity
      const member = space.members.get(userId);
      member.lastActivity = new Date();
      member.isActive = true;

      space.lastActivity = new Date();
      this.stats.activeCollaborators++;

      // Notify other collaborators
      this.broadcastToSpace(spaceId, {
        type: 'collaboratorJoined',
        userId,
        sessionId,
        member: this.serializeMember(member),
        timestamp: Date.now()
      }, userId);

      this.emit('collaboratorJoined', { spaceId, userId, sessionId });
      
      return { space: this.serializeSpace(space), session };
      
    } catch (error) {
      this.emit('collaborationError', { userId, spaceId, error });
      throw error;
    }
  }

  // Leave collaboration space
  async leaveCollaborationSpace(userId, spaceId) {
    try {
      const space = this.collaborationSpaces.get(spaceId);
      if (!space) {
        throw new Error('Collaboration space not found');
      }

      const session = this.userSessions.get(userId);
      if (!session || session.spaceId !== spaceId) {
        throw new Error('User not in this collaboration space');
      }

      // Remove active session
      space.activeSessions.delete(session.id);
      this.userSessions.delete(userId);
      
      // Update member status
      const member = space.members.get(userId);
      if (member) {
        member.isActive = false;
        member.lastActivity = new Date();
      }

      this.stats.activeCollaborators--;

      // Notify other collaborators
      this.broadcastToSpace(spaceId, {
        type: 'collaboratorLeft',
        userId,
        sessionId: session.id,
        timestamp: Date.now()
      });

      this.emit('collaboratorLeft', { spaceId, userId });
      
      return { success: true };
      
    } catch (error) {
      this.emit('collaborationError', { userId, spaceId, error });
      throw error;
    }
  }

  // Start document editing session
  async startDocumentEditing(userId, spaceId, documentPath) {
    try {
      const space = this.collaborationSpaces.get(spaceId);
      if (!space) {
        throw new Error('Collaboration space not found');
      }

      const session = this.userSessions.get(userId);
      if (!session || session.spaceId !== spaceId) {
        throw new Error('User not in collaboration space');
      }

      // Check permissions
      const member = space.members.get(userId);
      if (!this.hasPermission(member, 'edit')) {
        throw new Error('Insufficient permissions to edit documents');
      }

      const documentId = `${spaceId}:${documentPath}`;
      
      // Initialize document state if not exists
      if (!this.documentStates.has(documentId)) {
        // Get current document content
        const fileContent = await this.environmentManager.readEnvironmentFile(
          space.ownerId, // Use owner's environment
          space.environmentId,
          documentPath
        );

        this.documentStates.set(documentId, {
          documentId,
          spaceId,
          documentPath,
          content: fileContent.content,
          version: 0,
          operations: [],
          editors: new Set(),
          cursors: new Map(),
          selections: new Map(),
          lastModified: new Date()
        });

        space.documents.set(documentPath, documentId);
      }

      const documentState = this.documentStates.get(documentId);
      documentState.editors.add(userId);
      session.currentDocument = documentId;

      this.emit('documentEditingStarted', { userId, spaceId, documentId, documentPath });
      
      return {
        documentId,
        content: documentState.content,
        version: documentState.version,
        editors: Array.from(documentState.editors)
      };
      
    } catch (error) {
      this.emit('collaborationError', { userId, spaceId, error });
      throw error;
    }
  }

  // Apply document operation (for real-time editing)
  async applyDocumentOperation(userId, operation) {
    try {
      const { documentId, type, position, content, length } = operation;
      
      const documentState = this.documentStates.get(documentId);
      if (!documentState) {
        throw new Error('Document not found');
      }

      const space = this.collaborationSpaces.get(documentState.spaceId);
      if (!space) {
        throw new Error('Collaboration space not found');
      }

      // Check permissions
      const member = space.members.get(userId);
      if (!this.hasPermission(member, 'edit')) {
        throw new Error('Insufficient permissions');
      }

      // Create operation with unique ID
      const operationId = crypto.randomUUID();
      const transformedOperation = {
        id: operationId,
        userId,
        documentId,
        type, // 'insert', 'delete', 'replace'
        position,
        content,
        length,
        timestamp: Date.now(),
        version: documentState.version
      };

      // Add to operation queue for transformation
      const queue = this.operationQueue.get(documentState.spaceId);
      queue.push(transformedOperation);

      this.activeOperations.set(operationId, transformedOperation);
      
      // Process operation immediately if using last-write-wins
      if (this.config.conflictResolutionStrategy === 'last-write-wins') {
        await this.processOperationImmediate(transformedOperation);
      }

      this.emit('operationApplied', transformedOperation);
      
      return { operationId, version: documentState.version };
      
    } catch (error) {
      this.emit('operationError', { userId, operation, error });
      throw error;
    }
  }

  // Process operation queues (for operational transform)
  async processOperationQueues() {
    for (const [spaceId, queue] of this.operationQueue) {
      if (queue.length === 0) continue;

      const operations = queue.splice(0); // Take all operations
      
      if (this.config.enableOperationalTransform) {
        await this.processOperationsWithOT(spaceId, operations);
      } else {
        await this.processOperationsLWW(spaceId, operations);
      }
    }
  }

  // Process operations with Operational Transform
  async processOperationsWithOT(spaceId, operations) {
    try {
      // Group operations by document
      const operationsByDocument = new Map();
      
      for (const operation of operations) {
        if (!operationsByDocument.has(operation.documentId)) {
          operationsByDocument.set(operation.documentId, []);
        }
        operationsByDocument.get(operation.documentId).push(operation);
      }

      // Transform and apply operations for each document
      for (const [documentId, documentOps] of operationsByDocument) {
        await this.transformAndApplyOperations(documentId, documentOps);
      }
      
    } catch (error) {
      console.error('Operational transform error:', error);
    }
  }

  // Transform and apply operations to document
  async transformAndApplyOperations(documentId, operations) {
    const documentState = this.documentStates.get(documentId);
    if (!documentState) return;

    // Sort operations by timestamp
    operations.sort((a, b) => a.timestamp - b.timestamp);

    let currentContent = documentState.content;
    const transformedOperations = [];

    for (const operation of operations) {
      // Transform operation against previous operations
      const transformed = await this.transformOperation(operation, transformedOperations);
      
      // Apply transformation to content
      currentContent = this.applyOperationToContent(currentContent, transformed);
      transformedOperations.push(transformed);
      
      documentState.version++;
      this.stats.operationsApplied++;
    }

    // Update document state
    documentState.content = currentContent;
    documentState.operations.push(...transformedOperations);
    documentState.lastModified = new Date();

    // Keep only recent operations
    if (documentState.operations.length > 1000) {
      documentState.operations = documentState.operations.slice(-500);
    }

    // Save to environment
    await this.saveDocumentToEnvironment(documentState);

    // Broadcast changes to collaborators
    this.broadcastDocumentChanges(documentState, transformedOperations);
  }

  // Process operations with Last-Write-Wins
  async processOperationsLWW(spaceId, operations) {
    for (const operation of operations) {
      await this.processOperationImmediate(operation);
    }
  }

  // Process operation immediately
  async processOperationImmediate(operation) {
    const documentState = this.documentStates.get(operation.documentId);
    if (!documentState) return;

    // Apply operation to content
    documentState.content = this.applyOperationToContent(documentState.content, operation);
    documentState.version++;
    documentState.lastModified = new Date();
    documentState.operations.push(operation);

    this.stats.operationsApplied++;

    // Save to environment
    await this.saveDocumentToEnvironment(documentState);

    // Broadcast to collaborators
    this.broadcastDocumentChanges(documentState, [operation]);
  }

  // Transform operation (simplified OT)
  async transformOperation(operation, previousOperations) {
    let transformed = { ...operation };

    for (const prevOp of previousOperations) {
      if (prevOp.userId === operation.userId) continue; // Same user operations don't conflict
      
      transformed = this.transformAgainstOperation(transformed, prevOp);
    }

    return transformed;
  }

  // Transform operation against another operation
  transformAgainstOperation(op1, op2) {
    // Simplified transformation logic
    if (op1.position >= op2.position) {
      if (op2.type === 'insert') {
        op1.position += op2.content.length;
      } else if (op2.type === 'delete') {
        op1.position -= op2.length;
      }
    }

    return op1;
  }

  // Apply operation to content string
  applyOperationToContent(content, operation) {
    switch (operation.type) {
      case 'insert':
        return content.slice(0, operation.position) + 
               operation.content + 
               content.slice(operation.position);
               
      case 'delete':
        return content.slice(0, operation.position) + 
               content.slice(operation.position + operation.length);
               
      case 'replace':
        return content.slice(0, operation.position) + 
               operation.content + 
               content.slice(operation.position + operation.length);
               
      default:
        return content;
    }
  }

  // Save document to environment
  async saveDocumentToEnvironment(documentState) {
    try {
      const space = this.collaborationSpaces.get(documentState.spaceId);
      if (!space) return;

      await this.environmentManager.updateEnvironmentFile(
        space.ownerId,
        space.environmentId,
        documentState.documentPath,
        documentState.content
      );
      
    } catch (error) {
      console.error('Failed to save document to environment:', error);
    }
  }

  // Broadcast document changes
  broadcastDocumentChanges(documentState, operations) {
    this.broadcastToSpace(documentState.spaceId, {
      type: 'documentChanged',
      documentId: documentState.documentId,
      documentPath: documentState.documentPath,
      version: documentState.version,
      operations: operations.map(op => ({
        id: op.id,
        userId: op.userId,
        type: op.type,
        position: op.position,
        content: op.content,
        length: op.length,
        timestamp: op.timestamp
      })),
      timestamp: Date.now()
    });
  }

  // Update cursor position
  updateCursor(userId, spaceId, cursorData) {
    try {
      const session = this.userSessions.get(userId);
      if (!session || session.spaceId !== spaceId) {
        throw new Error('User not in collaboration space');
      }

      const { documentId, line, column } = cursorData;
      
      if (documentId) {
        const documentState = this.documentStates.get(documentId);
        if (documentState) {
          documentState.cursors.set(userId, { line, column, timestamp: Date.now() });
        }
      }

      session.cursor = cursorData;

      // Broadcast cursor update
      this.broadcastToSpace(spaceId, {
        type: 'cursorUpdate',
        userId,
        cursor: cursorData,
        timestamp: Date.now()
      }, userId);

      return { success: true };
      
    } catch (error) {
      this.emit('collaborationError', { userId, spaceId, error });
      throw error;
    }
  }

  // Send chat message
  async sendChatMessage(userId, spaceId, message) {
    try {
      const space = this.collaborationSpaces.get(spaceId);
      if (!space) {
        throw new Error('Collaboration space not found');
      }

      const member = space.members.get(userId);
      if (!member) {
        throw new Error('User not a member of this space');
      }

      const messageId = crypto.randomUUID();
      const chatMessage = {
        id: messageId,
        userId,
        username: member.username || `User ${userId}`,
        content: message.content,
        type: message.type || 'text', // text, code, file
        timestamp: Date.now(),
        edited: false,
        reactions: new Map()
      };

      // Add to chat room
      const chatRoom = this.chatRooms.get(spaceId);
      chatRoom.push(chatMessage);

      // Keep only recent messages
      if (chatRoom.length > 1000) {
        chatRoom.splice(0, chatRoom.length - 500);
      }

      this.stats.messagesExchanged++;

      // Broadcast message
      this.broadcastToSpace(spaceId, {
        type: 'chatMessage',
        message: chatMessage,
        timestamp: Date.now()
      });

      this.emit('chatMessage', { spaceId, messageId, userId });
      
      return chatMessage;
      
    } catch (error) {
      this.emit('collaborationError', { userId, spaceId, error });
      throw error;
    }
  }

  // Add comment to document
  async addComment(userId, spaceId, commentData) {
    try {
      const space = this.collaborationSpaces.get(spaceId);
      if (!space) {
        throw new Error('Collaboration space not found');
      }

      const member = space.members.get(userId);
      if (!this.hasPermission(member, 'comment')) {
        throw new Error('Insufficient permissions to add comments');
      }

      const commentId = crypto.randomUUID();
      const { documentId, line, column, content, thread } = commentData;
      
      const comment = {
        id: commentId,
        userId,
        username: member.username || `User ${userId}`,
        documentId,
        line,
        column,
        content,
        thread: thread || commentId, // Thread ID for replies
        timestamp: Date.now(),
        resolved: false,
        replies: []
      };

      // Add to comments
      if (!this.comments.has(documentId)) {
        this.comments.set(documentId, []);
      }
      this.comments.get(documentId).push(comment);

      // Broadcast comment
      this.broadcastToSpace(spaceId, {
        type: 'commentAdded',
        comment,
        timestamp: Date.now()
      });

      this.emit('commentAdded', { spaceId, commentId, documentId });
      
      return comment;
      
    } catch (error) {
      this.emit('collaborationError', { userId, spaceId, error });
      throw error;
    }
  }

  // Get permissions for role
  getPermissions(role) {
    const permissions = {
      owner: ['read', 'write', 'edit', 'delete', 'invite', 'admin', 'comment', 'deploy'],
      admin: ['read', 'write', 'edit', 'delete', 'invite', 'comment', 'deploy'],
      editor: ['read', 'write', 'edit', 'comment'],
      viewer: ['read', 'comment']
    };
    
    return permissions[role] || permissions.viewer;
  }

  // Check if member has permission
  hasPermission(member, permission) {
    if (!member) return false;
    return member.permissions.includes(permission);
  }

  // Broadcast message to space
  broadcastToSpace(spaceId, message, excludeUserId = null) {
    const space = this.collaborationSpaces.get(spaceId);
    if (!space) return;

    let sentCount = 0;
    
    for (const session of space.activeSessions.values()) {
      if (session.userId !== excludeUserId) {
        // This would send via WebSocket in real implementation
        // For now, we emit events
        this.emit('broadcastMessage', {
          userId: session.userId,
          sessionId: session.id,
          message
        });
        sentCount++;
      }
    }
    
    return sentCount;
  }

  // Serialize space for client
  serializeSpace(space) {
    return {
      id: space.id,
      name: space.name,
      description: space.description,
      ownerId: space.ownerId,
      settings: space.settings,
      members: Array.from(space.members.values()).map(this.serializeMember),
      activeSessions: space.activeSessions.size,
      documents: Array.from(space.documents.keys()),
      createdAt: space.createdAt,
      lastActivity: space.lastActivity,
      status: space.status
    };
  }

  // Serialize member for client
  serializeMember(member) {
    return {
      userId: member.userId,
      role: member.role,
      permissions: member.permissions,
      joinedAt: member.joinedAt,
      lastActivity: member.lastActivity,
      isActive: member.isActive
    };
  }

  // Get space info
  getSpaceInfo(spaceId, userId = null) {
    const space = this.collaborationSpaces.get(spaceId);
    if (!space) return null;

    // Check if user has access
    if (userId && !space.settings.isPublic && !space.members.has(userId)) {
      return null;
    }

    return this.serializeSpace(space);
  }

  // Get user spaces
  getUserSpaces(userId) {
    const spaces = [];
    
    for (const space of this.collaborationSpaces.values()) {
      if (space.members.has(userId)) {
        spaces.push(this.serializeSpace(space));
      }
    }
    
    return spaces.sort((a, b) => new Date(b.lastActivity) - new Date(a.lastActivity));
  }

  // Get chat history
  getChatHistory(spaceId, userId, limit = 50) {
    const space = this.collaborationSpaces.get(spaceId);
    if (!space || !space.members.has(userId)) {
      throw new Error('Access denied');
    }

    const chatRoom = this.chatRooms.get(spaceId) || [];
    return chatRoom.slice(-limit);
  }

  // Get document comments
  getDocumentComments(documentId, userId) {
    const documentState = this.documentStates.get(documentId);
    if (!documentState) {
      throw new Error('Document not found');
    }

    const space = this.collaborationSpaces.get(documentState.spaceId);
    if (!space || !space.members.has(userId)) {
      throw new Error('Access denied');
    }

    return this.comments.get(documentId) || [];
  }

  // Get service statistics
  getServiceStats() {
    return {
      ...this.stats,
      activeSpacesCount: this.collaborationSpaces.size,
      totalDocuments: this.documentStates.size,
      totalChatMessages: Array.from(this.chatRooms.values()).reduce((total, room) => total + room.length, 0),
      totalComments: Array.from(this.comments.values()).reduce((total, comments) => total + comments.length, 0),
      avgCollaboratorsPerSpace: this.stats.totalCollaborators / Math.max(this.stats.totalSpaces, 1)
    };
  }

  // Health check
  async healthCheck() {
    try {
      return {
        healthy: true,
        stats: this.getServiceStats(),
        operationQueuesSize: Array.from(this.operationQueue.values()).reduce((total, queue) => total + queue.length, 0),
        environmentManagerHealthy: await this.environmentManager.healthCheck().then(h => h.healthy)
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message
      };
    }
  }

  // Cleanup inactive sessions
  cleanupInactiveSessions() {
    const now = Date.now();
    const inactiveThreshold = this.config.inactivityTimeout;
    
    for (const [spaceId, space] of this.collaborationSpaces) {
      const inactiveSessions = [];
      
      for (const [sessionId, session] of space.activeSessions) {
        if (now - session.lastActivity.getTime() > inactiveThreshold) {
          inactiveSessions.push(sessionId);
        }
      }
      
      // Remove inactive sessions
      for (const sessionId of inactiveSessions) {
        const session = space.activeSessions.get(sessionId);
        if (session) {
          space.activeSessions.delete(sessionId);
          this.userSessions.delete(session.userId);
          
          // Update member status
          const member = space.members.get(session.userId);
          if (member) {
            member.isActive = false;
          }
          
          this.stats.activeCollaborators--;
          
          this.broadcastToSpace(spaceId, {
            type: 'collaboratorInactive',
            userId: session.userId,
            sessionId,
            timestamp: Date.now()
          });
        }
      }
    }
  }

  // Cleanup service
  async cleanup() {
    console.log('Shutting down Collaboration Service...');
    
    // Notify all active collaborators
    for (const space of this.collaborationSpaces.values()) {
      this.broadcastToSpace(space.id, {
        type: 'serviceShutdown',
        message: 'Collaboration service is shutting down',
        timestamp: Date.now()
      });
    }

    this.emit('cleanup');
  }
}

module.exports = CollaborationService;