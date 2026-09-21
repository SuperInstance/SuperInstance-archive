const chokidar = require('chokidar');
const WebSocket = require('ws');
const { EventEmitter } = require('events');
const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');

class LiveEditingService extends EventEmitter {
  constructor(environmentManager, containerManager, config = {}) {
    super();
    
    this.environmentManager = environmentManager;
    this.containerManager = containerManager;
    this.config = {
      // Live editing settings
      enableHotReload: config.enableHotReload ?? true,
      enableAutoSave: config.enableAutoSave ?? true,
      autoSaveInterval: config.autoSaveInterval || 2000, // 2 seconds
      
      // Change tracking
      enableChangeTracking: config.enableChangeTracking ?? true,
      maxChangeHistory: config.maxChangeHistory || 100,
      
      // Production isolation
      enableStagingMode: config.enableStagingMode ?? true,
      stagingBranchPrefix: config.stagingBranchPrefix || 'sandbox/',
      
      // File watching
      watchPatterns: config.watchPatterns || ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx', '**/*.py', '**/*.go'],
      ignorePatterns: config.ignorePatterns || ['node_modules/**', '.git/**', 'dist/**', 'build/**'],
      
      // WebSocket settings
      wsPort: config.wsPort || 8304,
      enableCompression: config.enableCompression ?? true,
      
      ...config
    };

    this.projectSessions = new Map(); // projectId -> session info
    this.fileWatchers = new Map(); // sessionId -> watcher
    this.changeHistory = new Map(); // sessionId -> changes[]
    this.autoSaveTimers = new Map(); // sessionId -> timer
    this.wsServer = null;
    this.connections = new Map(); // connectionId -> websocket
    
    this.stats = {
      activeSessions: 0,
      totalChanges: 0,
      autoSaves: 0,
      hotReloads: 0,
      filesWatched: 0
    };

    this.initializeWebSocketServer();
  }

  // Initialize WebSocket server for real-time communication
  initializeWebSocketServer() {
    try {
      this.wsServer = new WebSocket.Server({
        port: this.config.wsPort,
        perMessageDeflate: this.config.enableCompression
      });

      this.wsServer.on('connection', (ws, request) => {
        this.handleWebSocketConnection(ws, request);
      });

      this.wsServer.on('error', (error) => {
        this.emit('wsError', error);
      });

      console.log(`Live editing WebSocket server started on port ${this.config.wsPort}`);
      
    } catch (error) {
      console.error('Failed to initialize WebSocket server:', error);
      this.emit('error', { type: 'ws_init', error });
    }
  }

  // Handle new WebSocket connection
  handleWebSocketConnection(ws, request) {
    const connectionId = crypto.randomUUID();
    
    // Extract user info from connection (you'd implement auth here)
    const userId = this.extractUserIdFromRequest(request);
    
    const connection = {
      id: connectionId,
      ws,
      userId,
      sessionId: null,
      connectedAt: new Date(),
      lastActivity: new Date()
    };

    this.connections.set(connectionId, connection);

    ws.on('message', (data) => {
      this.handleWebSocketMessage(connection, data);
    });

    ws.on('close', () => {
      this.handleWebSocketDisconnection(connection);
    });

    ws.on('error', (error) => {
      this.emit('connectionError', { connectionId, error });
    });

    // Send welcome message
    this.sendToConnection(connectionId, {
      type: 'connected',
      connectionId,
      timestamp: Date.now()
    });

    this.emit('connectionEstablished', { connectionId, userId });
  }

  // Start live editing session
  async startLiveEditingSession(userId, projectConfig) {
    try {
      const sessionId = crypto.randomUUID();
      
      // Get or create environment
      let environment = await this.getOrCreateEnvironment(userId, projectConfig);
      
      // Create staging version if production isolation is enabled
      if (this.config.enableStagingMode) {
        environment = await this.createStagingEnvironment(environment, sessionId);
      }

      const session = {
        id: sessionId,
        userId,
        environmentId: environment.id,
        environment,
        projectConfig,
        startedAt: new Date(),
        lastActivity: new Date(),
        status: 'active',
        changes: [],
        collaborators: new Set([userId]),
        settings: {
          hotReload: this.config.enableHotReload,
          autoSave: this.config.enableAutoSave,
          changeTracking: this.config.enableChangeTracking
        }
      };

      this.projectSessions.set(sessionId, session);
      this.stats.activeSessions++;

      // Start file watching
      if (this.config.enableChangeTracking) {
        await this.startFileWatching(session);
      }

      // Setup auto-save if enabled
      if (this.config.enableAutoSave) {
        this.setupAutoSave(session);
      }

      this.emit('sessionStarted', session);
      
      return session;
      
    } catch (error) {
      this.emit('sessionError', { userId, error });
      throw error;
    }
  }

  // Get or create environment for live editing
  async getOrCreateEnvironment(userId, projectConfig) {
    // Check if environment already exists
    const userEnvironments = this.environmentManager.getUserEnvironments(userId);
    let environment = userEnvironments.find(env => 
      env.name === projectConfig.projectName || 
      env.id === projectConfig.environmentId
    );

    if (!environment) {
      // Create new environment
      environment = await this.environmentManager.createEnvironment(
        userId,
        projectConfig.userTier || 'free',
        {
          name: projectConfig.projectName,
          templateId: projectConfig.templateId || 'node-basic',
          description: `Live editing environment for ${projectConfig.projectName}`,
          ...projectConfig
        }
      );
    }

    return environment;
  }

  // Create staging environment for production isolation
  async createStagingEnvironment(baseEnvironment, sessionId) {
    try {
      // Create snapshot of base environment
      const snapshot = await this.environmentManager.createSnapshot(
        baseEnvironment.id,
        `Staging snapshot for session ${sessionId}`
      );

      // Create staging branch/version
      const stagingEnvironment = {
        ...baseEnvironment,
        id: `${baseEnvironment.id}-staging-${sessionId}`,
        name: `${baseEnvironment.name} (Staging)`,
        isStaging: true,
        baseEnvironmentId: baseEnvironment.id,
        stagingSnapshot: snapshot,
        sessionId
      };

      return stagingEnvironment;
      
    } catch (error) {
      console.warn('Failed to create staging environment, using base:', error.message);
      return baseEnvironment;
    }
  }

  // Start file watching for environment
  async startFileWatching(session) {
    try {
      const environment = session.environment;
      
      // Create file watcher in container
      const watchCommand = `find /workspace -type f \\( ${this.config.watchPatterns.map(p => `-name "${p}"`).join(' -o ')} \\) | head -100`;
      
      const result = await this.containerManager.executeCode(
        session.userId,
        environment.container?.id,
        watchCommand,
        { language: 'bash' }
      );

      if (result.exitCode === 0) {
        const filesToWatch = result.stdout.trim().split('\n').filter(f => f.length > 0);
        this.stats.filesWatched += filesToWatch.length;
      }

      // Setup periodic file change checking
      const watchInterval = setInterval(async () => {
        await this.checkFileChanges(session);
      }, 1000); // Check every second

      this.fileWatchers.set(session.id, {
        type: 'interval',
        interval: watchInterval,
        lastCheck: Date.now()
      });

      this.emit('fileWatchingStarted', { 
        sessionId: session.id, 
        filesWatched: this.stats.filesWatched 
      });
      
    } catch (error) {
      console.error('Failed to start file watching:', error);
    }
  }

  // Check for file changes in environment
  async checkFileChanges(session) {
    try {
      // Get current file listing with timestamps
      const listCommand = `find /workspace -type f -exec stat -c "%Y %n" {} + 2>/dev/null | sort -n`;
      
      const result = await this.containerManager.executeCode(
        session.userId,
        session.environment.container?.id,
        listCommand,
        { language: 'bash' }
      );

      if (result.exitCode === 0) {
        const currentFiles = this.parseFileListWithTimestamps(result.stdout);
        const watcher = this.fileWatchers.get(session.id);
        
        if (watcher && watcher.lastFiles) {
          const changes = this.detectFileChanges(watcher.lastFiles, currentFiles);
          
          if (changes.length > 0) {
            await this.processFileChanges(session, changes);
          }
        }
        
        if (watcher) {
          watcher.lastFiles = currentFiles;
        }
      }
      
    } catch (error) {
      console.warn('File change check failed:', error.message);
    }
  }

  // Parse file list with timestamps
  parseFileListWithTimestamps(output) {
    const files = new Map();
    const lines = output.trim().split('\n').filter(line => line.length > 0);
    
    for (const line of lines) {
      const parts = line.split(' ');
      if (parts.length >= 2) {
        const timestamp = parseInt(parts[0]);
        const filePath = parts.slice(1).join(' ');
        files.set(filePath, timestamp);
      }
    }
    
    return files;
  }

  // Detect file changes
  detectFileChanges(oldFiles, newFiles) {
    const changes = [];
    
    // Check for new or modified files
    for (const [filePath, timestamp] of newFiles) {
      const oldTimestamp = oldFiles.get(filePath);
      
      if (!oldTimestamp) {
        changes.push({
          type: 'created',
          filePath,
          timestamp: new Date(timestamp * 1000)
        });
      } else if (timestamp > oldTimestamp) {
        changes.push({
          type: 'modified',
          filePath,
          timestamp: new Date(timestamp * 1000)
        });
      }
    }
    
    // Check for deleted files
    for (const [filePath] of oldFiles) {
      if (!newFiles.has(filePath)) {
        changes.push({
          type: 'deleted',
          filePath,
          timestamp: new Date()
        });
      }
    }
    
    return changes;
  }

  // Process file changes
  async processFileChanges(session, changes) {
    try {
      for (const change of changes) {
        // Record change in history
        if (this.config.enableChangeTracking) {
          this.recordChange(session, change);
        }

        // Notify connected clients
        this.broadcastToSession(session.id, {
          type: 'fileChange',
          change,
          sessionId: session.id,
          timestamp: Date.now()
        });

        // Trigger hot reload if applicable
        if (this.config.enableHotReload && this.shouldTriggerHotReload(change)) {
          await this.triggerHotReload(session, change);
        }
      }

      this.stats.totalChanges += changes.length;
      session.lastActivity = new Date();
      
    } catch (error) {
      this.emit('changeProcessingError', { sessionId: session.id, error });
    }
  }

  // Record change in session history
  recordChange(session, change) {
    if (!this.changeHistory.has(session.id)) {
      this.changeHistory.set(session.id, []);
    }

    const history = this.changeHistory.get(session.id);
    history.push({
      ...change,
      id: crypto.randomUUID(),
      recordedAt: new Date()
    });

    // Keep only recent changes
    if (history.length > this.config.maxChangeHistory) {
      history.shift();
    }
  }

  // Check if change should trigger hot reload
  shouldTriggerHotReload(change) {
    if (change.type === 'deleted') return false;
    
    // Hot reload for specific file types
    const hotReloadExtensions = ['.js', '.jsx', '.ts', '.tsx', '.css', '.scss'];
    const ext = path.extname(change.filePath);
    
    return hotReloadExtensions.includes(ext);
  }

  // Trigger hot reload
  async triggerHotReload(session, change) {
    try {
      // Get file content
      const fileContent = await this.environmentManager.readEnvironmentFile(
        session.userId,
        session.environmentId,
        change.filePath.replace('/workspace/', '')
      );

      // Broadcast hot reload event
      this.broadcastToSession(session.id, {
        type: 'hotReload',
        filePath: change.filePath,
        content: fileContent.content,
        sessionId: session.id,
        timestamp: Date.now()
      });

      this.stats.hotReloads++;
      this.emit('hotReloadTriggered', { sessionId: session.id, filePath: change.filePath });
      
    } catch (error) {
      console.error('Hot reload failed:', error);
    }
  }

  // Setup auto-save for session
  setupAutoSave(session) {
    const timer = setInterval(async () => {
      await this.performAutoSave(session);
    }, this.config.autoSaveInterval);

    this.autoSaveTimers.set(session.id, timer);
  }

  // Perform auto-save
  async performAutoSave(session) {
    try {
      // Create snapshot of current state
      const snapshot = await this.environmentManager.createSnapshot(
        session.environmentId,
        `Auto-save at ${new Date().toISOString()}`
      );

      this.stats.autoSaves++;
      
      // Notify clients
      this.broadcastToSession(session.id, {
        type: 'autoSave',
        snapshot: {
          id: snapshot.id,
          createdAt: snapshot.createdAt
        },
        sessionId: session.id,
        timestamp: Date.now()
      });

      this.emit('autoSaveCompleted', { sessionId: session.id, snapshotId: snapshot.id });
      
    } catch (error) {
      this.emit('autoSaveError', { sessionId: session.id, error });
    }
  }

  // Handle WebSocket messages
  handleWebSocketMessage(connection, data) {
    try {
      const message = JSON.parse(data.toString());
      connection.lastActivity = new Date();

      switch (message.type) {
        case 'joinSession':
          this.handleJoinSession(connection, message);
          break;
        case 'leaveSession':
          this.handleLeaveSession(connection, message);
          break;
        case 'fileEdit':
          this.handleFileEdit(connection, message);
          break;
        case 'executeCode':
          this.handleCodeExecution(connection, message);
          break;
        case 'requestFileContent':
          this.handleFileContentRequest(connection, message);
          break;
        default:
          this.sendToConnection(connection.id, {
            type: 'error',
            message: `Unknown message type: ${message.type}`
          });
      }
      
    } catch (error) {
      this.sendToConnection(connection.id, {
        type: 'error',
        message: 'Invalid message format'
      });
    }
  }

  // Handle session join
  async handleJoinSession(connection, message) {
    try {
      const { sessionId } = message;
      const session = this.projectSessions.get(sessionId);
      
      if (!session) {
        return this.sendToConnection(connection.id, {
          type: 'error',
          message: 'Session not found'
        });
      }

      // Add user to session collaborators
      session.collaborators.add(connection.userId);
      connection.sessionId = sessionId;

      // Send session info
      this.sendToConnection(connection.id, {
        type: 'sessionJoined',
        session: {
          id: session.id,
          projectName: session.projectConfig.projectName,
          collaborators: Array.from(session.collaborators),
          startedAt: session.startedAt,
          settings: session.settings
        },
        timestamp: Date.now()
      });

      // Notify other collaborators
      this.broadcastToSession(sessionId, {
        type: 'collaboratorJoined',
        userId: connection.userId,
        sessionId,
        timestamp: Date.now()
      }, connection.id);

      this.emit('collaboratorJoined', { sessionId, userId: connection.userId });
      
    } catch (error) {
      this.sendToConnection(connection.id, {
        type: 'error',
        message: 'Failed to join session'
      });
    }
  }

  // Handle file edit
  async handleFileEdit(connection, message) {
    try {
      const { sessionId, filePath, content, operation } = message;
      const session = this.projectSessions.get(sessionId);
      
      if (!session || !session.collaborators.has(connection.userId)) {
        return this.sendToConnection(connection.id, {
          type: 'error',
          message: 'Unauthorized or session not found'
        });
      }

      // Apply file edit
      await this.environmentManager.updateEnvironmentFile(
        connection.userId,
        session.environmentId,
        filePath,
        content
      );

      // Broadcast change to other collaborators
      this.broadcastToSession(sessionId, {
        type: 'fileEdited',
        filePath,
        content,
        operation,
        editedBy: connection.userId,
        sessionId,
        timestamp: Date.now()
      }, connection.id);

      session.lastActivity = new Date();
      
    } catch (error) {
      this.sendToConnection(connection.id, {
        type: 'error',
        message: 'File edit failed'
      });
    }
  }

  // Handle code execution request
  async handleCodeExecution(connection, message) {
    try {
      const { sessionId, code, language } = message;
      const session = this.projectSessions.get(sessionId);
      
      if (!session || !session.collaborators.has(connection.userId)) {
        return this.sendToConnection(connection.id, {
          type: 'error',
          message: 'Unauthorized or session not found'
        });
      }

      // Execute code in environment
      const result = await this.environmentManager.executeInEnvironment(
        connection.userId,
        session.environmentId,
        code,
        { language }
      );

      // Send result to requester
      this.sendToConnection(connection.id, {
        type: 'executionResult',
        result,
        sessionId,
        timestamp: Date.now()
      });

      // Optionally broadcast to all collaborators
      if (message.broadcast) {
        this.broadcastToSession(sessionId, {
          type: 'codeExecuted',
          code,
          result,
          executedBy: connection.userId,
          sessionId,
          timestamp: Date.now()
        }, connection.id);
      }
      
    } catch (error) {
      this.sendToConnection(connection.id, {
        type: 'executionError',
        error: error.message,
        sessionId,
        timestamp: Date.now()
      });
    }
  }

  // Handle file content request
  async handleFileContentRequest(connection, message) {
    try {
      const { sessionId, filePath } = message;
      const session = this.projectSessions.get(sessionId);
      
      if (!session || !session.collaborators.has(connection.userId)) {
        return this.sendToConnection(connection.id, {
          type: 'error',
          message: 'Unauthorized or session not found'
        });
      }

      const fileContent = await this.environmentManager.readEnvironmentFile(
        connection.userId,
        session.environmentId,
        filePath
      );

      this.sendToConnection(connection.id, {
        type: 'fileContent',
        filePath,
        content: fileContent.content,
        size: fileContent.size,
        sessionId,
        timestamp: Date.now()
      });
      
    } catch (error) {
      this.sendToConnection(connection.id, {
        type: 'fileNotFound',
        filePath: message.filePath,
        error: error.message,
        sessionId: message.sessionId,
        timestamp: Date.now()
      });
    }
  }

  // Handle WebSocket disconnection
  handleWebSocketDisconnection(connection) {
    // Remove from session collaborators
    if (connection.sessionId) {
      const session = this.projectSessions.get(connection.sessionId);
      if (session) {
        session.collaborators.delete(connection.userId);
        
        // Notify remaining collaborators
        this.broadcastToSession(connection.sessionId, {
          type: 'collaboratorLeft',
          userId: connection.userId,
          sessionId: connection.sessionId,
          timestamp: Date.now()
        });
      }
    }

    this.connections.delete(connection.id);
    this.emit('connectionClosed', { connectionId: connection.id });
  }

  // Send message to specific connection
  sendToConnection(connectionId, message) {
    const connection = this.connections.get(connectionId);
    if (connection && connection.ws.readyState === WebSocket.OPEN) {
      connection.ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  // Broadcast message to all session participants
  broadcastToSession(sessionId, message, excludeConnectionId = null) {
    let sentCount = 0;
    
    for (const [connectionId, connection] of this.connections) {
      if (connection.sessionId === sessionId && connectionId !== excludeConnectionId) {
        if (this.sendToConnection(connectionId, message)) {
          sentCount++;
        }
      }
    }
    
    return sentCount;
  }

  // End live editing session
  async endSession(userId, sessionId) {
    try {
      const session = this.projectSessions.get(sessionId);
      if (!session || !session.collaborators.has(userId)) {
        throw new Error('Session not found or unauthorized');
      }

      // Clear auto-save timer
      const autoSaveTimer = this.autoSaveTimers.get(sessionId);
      if (autoSaveTimer) {
        clearInterval(autoSaveTimer);
        this.autoSaveTimers.delete(sessionId);
      }

      // Clear file watcher
      const watcher = this.fileWatchers.get(sessionId);
      if (watcher) {
        if (watcher.type === 'interval') {
          clearInterval(watcher.interval);
        }
        this.fileWatchers.delete(sessionId);
      }

      // Final auto-save
      if (this.config.enableAutoSave) {
        await this.performAutoSave(session);
      }

      // Merge staging changes back to production (if applicable)
      if (session.environment.isStaging) {
        await this.mergeStagingToProduction(session);
      }

      // Notify all connections
      this.broadcastToSession(sessionId, {
        type: 'sessionEnded',
        sessionId,
        endedBy: userId,
        timestamp: Date.now()
      });

      // Cleanup
      this.projectSessions.delete(sessionId);
      this.changeHistory.delete(sessionId);
      this.stats.activeSessions--;

      this.emit('sessionEnded', { sessionId, userId });
      
      return { success: true, sessionId };
      
    } catch (error) {
      this.emit('sessionError', { userId, sessionId, error });
      throw error;
    }
  }

  // Merge staging changes to production
  async mergeStagingToProduction(session) {
    try {
      if (!session.environment.isStaging || !session.environment.baseEnvironmentId) {
        return;
      }

      // This would implement actual merging logic
      // For now, we'll just create a snapshot with merge info
      const mergeSnapshot = await this.environmentManager.createSnapshot(
        session.environment.baseEnvironmentId,
        `Merged changes from staging session ${session.id}`
      );

      this.emit('stagingMerged', {
        sessionId: session.id,
        baseEnvironmentId: session.environment.baseEnvironmentId,
        mergeSnapshot: mergeSnapshot.id
      });
      
    } catch (error) {
      console.error('Failed to merge staging to production:', error);
    }
  }

  // Extract user ID from WebSocket request
  extractUserIdFromRequest(request) {
    // You'd implement actual authentication here
    // This is a simplified version
    const url = new URL(request.url, 'ws://localhost');
    return url.searchParams.get('userId') || 'anonymous';
  }

  // Get session info
  getSessionInfo(sessionId) {
    const session = this.projectSessions.get(sessionId);
    if (!session) return null;

    return {
      id: session.id,
      userId: session.userId,
      projectName: session.projectConfig.projectName,
      startedAt: session.startedAt,
      lastActivity: session.lastActivity,
      status: session.status,
      collaborators: Array.from(session.collaborators),
      changeCount: this.changeHistory.get(sessionId)?.length || 0,
      environment: {
        id: session.environmentId,
        name: session.environment.name,
        isStaging: session.environment.isStaging || false
      }
    };
  }

  // Get user sessions
  getUserSessions(userId) {
    const sessions = [];
    
    for (const session of this.projectSessions.values()) {
      if (session.collaborators.has(userId)) {
        sessions.push(this.getSessionInfo(session.id));
      }
    }
    
    return sessions;
  }

  // Get service statistics
  getServiceStats() {
    return {
      ...this.stats,
      activeConnections: this.connections.size,
      totalSessions: this.projectSessions.size,
      avgCollaboratorsPerSession: Array.from(this.projectSessions.values())
        .reduce((total, session) => total + session.collaborators.size, 0) / 
        Math.max(this.projectSessions.size, 1)
    };
  }

  // Health check
  async healthCheck() {
    try {
      return {
        healthy: true,
        wsServerRunning: this.wsServer !== null,
        stats: this.getServiceStats(),
        environmentManagerHealthy: await this.environmentManager.healthCheck().then(h => h.healthy)
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message
      };
    }
  }

  // Cleanup service
  async cleanup() {
    console.log('Shutting down Live Editing Service...');
    
    // Clear all timers
    for (const timer of this.autoSaveTimers.values()) {
      clearInterval(timer);
    }
    this.autoSaveTimers.clear();

    // Clear file watchers
    for (const watcher of this.fileWatchers.values()) {
      if (watcher.type === 'interval') {
        clearInterval(watcher.interval);
      }
    }
    this.fileWatchers.clear();

    // Close all WebSocket connections
    for (const connection of this.connections.values()) {
      connection.ws.close();
    }
    this.connections.clear();

    // Close WebSocket server
    if (this.wsServer) {
      this.wsServer.close();
    }

    this.emit('cleanup');
  }
}

module.exports = LiveEditingService;