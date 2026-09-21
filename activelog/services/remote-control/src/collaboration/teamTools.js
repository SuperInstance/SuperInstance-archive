const EventEmitter = require('events');
const logger = require('../core/logger');
const { v4: uuidv4 } = require('uuid');

class TeamTools extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Session management
      maxSessionDuration: options.maxSessionDuration || 28800000, // 8 hours
      maxParticipants: options.maxParticipants || 50,
      allowGuestAccess: options.allowGuestAccess !== false,
      
      // Screen sharing
      enableScreenSharing: options.enableScreenSharing !== false,
      multiplePresenterMode: options.multiplePresenterMode || false,
      screenShareQuality: options.screenShareQuality || 'high',
      
      // Remote control
      enableRemoteControl: options.enableRemoteControl !== false,
      requireControlPermission: options.requireControlPermission !== false,
      controlTimeouts: options.controlTimeouts || 300000, // 5 minutes
      
      // Collaboration features
      enableWhiteboard: options.enableWhiteboard !== false,
      enableFileSharing: options.enableFileSharing !== false,
      enableChat: options.enableChat !== false,
      enableAnnotations: options.enableAnnotations !== false,
      
      // Recording
      enableRecording: options.enableRecording !== false,
      autoRecordSessions: options.autoRecordSessions || false,
      recordingRetentionDays: options.recordingRetentionDays || 30,
      
      // Security
      requireAuthentication: options.requireAuthentication !== false,
      encryptCommunications: options.encryptCommunications !== false,
      sessionPasswords: options.sessionPasswords || false,
      
      // Permissions
      defaultParticipantPermissions: options.defaultParticipantPermissions || {
        canShare: false,
        canControl: false,
        canAnnotate: true,
        canChat: true,
        canUploadFiles: false
      },
      
      ...options
    };

    // Active sessions
    this.activeSessions = new Map(); // sessionId -> session
    this.userSessions = new Map(); // userId -> sessionIds[]
    this.sessionParticipants = new Map(); // sessionId -> participants[]
    
    // Session features
    this.whiteboards = new Map(); // sessionId -> whiteboard data
    this.chatHistory = new Map(); // sessionId -> messages[]
    this.sharedFiles = new Map(); // sessionId -> files[]
    this.annotations = new Map(); // sessionId -> annotations[]
    this.recordings = new Map(); // sessionId -> recording info
    
    // Control and permissions
    this.controlRequests = new Map(); // requestId -> request
    this.activeControls = new Map(); // sessionId -> controller info
    this.permissionOverrides = new Map(); // sessionId -> userId -> permissions
    
    // Metrics
    this.metrics = {
      totalSessions: 0,
      activeSessionsCount: 0,
      totalParticipants: 0,
      screensShared: 0,
      controlRequestsProcessed: 0,
      messagesExchanged: 0,
      filesShared: 0,
      recordingMinutes: 0
    };
  }

  async initialize() {
    logger.info('Initializing Team Tools system...');
    
    try {
      // Setup session management
      this.startSessionMonitoring();
      
      // Setup cleanup routines
      this.startCleanupRoutines();
      
      logger.info('Team Tools system initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Team Tools system:', error);
      throw error;
    }
  }

  async createSession(hostUserId, sessionInfo) {
    const sessionId = uuidv4();
    const now = Date.now();
    
    const session = {
      id: sessionId,
      hostUserId,
      title: sessionInfo.title || 'Team Collaboration Session',
      description: sessionInfo.description || '',
      
      // Timing
      createdAt: now,
      startedAt: null,
      endedAt: null,
      scheduledStart: sessionInfo.scheduledStart || now,
      scheduledDuration: sessionInfo.scheduledDuration || this.options.maxSessionDuration,
      
      // Configuration
      maxParticipants: Math.min(sessionInfo.maxParticipants || this.options.maxParticipants, this.options.maxParticipants),
      requiresPassword: sessionInfo.password ? true : false,
      password: sessionInfo.password,
      allowGuestAccess: sessionInfo.allowGuestAccess ?? this.options.allowGuestAccess,
      
      // Features enabled
      features: {
        screenSharing: sessionInfo.features?.screenSharing ?? this.options.enableScreenSharing,
        remoteControl: sessionInfo.features?.remoteControl ?? this.options.enableRemoteControl,
        whiteboard: sessionInfo.features?.whiteboard ?? this.options.enableWhiteboard,
        fileSharing: sessionInfo.features?.fileSharing ?? this.options.enableFileSharing,
        chat: sessionInfo.features?.chat ?? this.options.enableChat,
        annotations: sessionInfo.features?.annotations ?? this.options.enableAnnotations,
        recording: sessionInfo.features?.recording ?? this.options.enableRecording
      },
      
      // Current state
      status: 'created', // created, active, paused, ended
      currentPresenter: null,
      presenters: [], // Users currently presenting
      activeControllers: [], // Users with remote control
      
      // Statistics
      participantCount: 0,
      maxConcurrentParticipants: 0,
      totalJoins: 0,
      messagesCount: 0,
      filesSharedCount: 0,
      
      // Metadata
      tags: sessionInfo.tags || [],
      department: sessionInfo.department,
      project: sessionInfo.project
    };

    this.activeSessions.set(sessionId, session);
    this.metrics.totalSessions++;

    // Initialize session features
    if (session.features.whiteboard) {
      this.whiteboards.set(sessionId, {
        elements: [],
        history: [],
        activeUsers: new Set()
      });
    }

    if (session.features.chat) {
      this.chatHistory.set(sessionId, []);
    }

    if (session.features.fileSharing) {
      this.sharedFiles.set(sessionId, []);
    }

    if (session.features.annotations) {
      this.annotations.set(sessionId, []);
    }

    logger.info(`Team session created: ${session.title}`, {
      sessionId,
      hostUserId,
      features: Object.keys(session.features).filter(k => session.features[k])
    });

    this.emit('session-created', session);
    return session;
  }

  async joinSession(userId, sessionId, userInfo = {}, password = null) {
    const session = this.activeSessions.get(sessionId);
    if (!session) {
      throw new Error('Session not found');
    }

    // Check if session has ended
    if (session.status === 'ended') {
      throw new Error('Session has ended');
    }

    // Check password if required
    if (session.requiresPassword && session.password !== password) {
      throw new Error('Invalid session password');
    }

    // Check participant limit
    if (session.participantCount >= session.maxParticipants) {
      throw new Error('Session is full');
    }

    // Check guest access
    if (!session.allowGuestAccess && !userInfo.isAuthenticated) {
      throw new Error('Guest access not allowed');
    }

    const participant = {
      userId,
      displayName: userInfo.displayName || `User ${userId.substr(0, 8)}`,
      email: userInfo.email,
      role: userId === session.hostUserId ? 'host' : 'participant',
      permissions: this.getParticipantPermissions(sessionId, userId),
      
      // Status
      joinedAt: Date.now(),
      status: 'joined', // joined, presenting, controlling, away
      lastActivity: Date.now(),
      
      // Capabilities
      hasAudio: userInfo.hasAudio || false,
      hasVideo: userInfo.hasVideo || false,
      hasScreenShare: userInfo.hasScreenShare || false,
      
      // Connection info
      connectionInfo: {
        ip: userInfo.ip,
        userAgent: userInfo.userAgent,
        platform: userInfo.platform
      }
    };

    // Add participant
    let participants = this.sessionParticipants.get(sessionId) || [];
    
    // Remove existing participation (rejoin case)
    participants = participants.filter(p => p.userId !== userId);
    participants.push(participant);
    
    this.sessionParticipants.set(sessionId, participants);

    // Update session stats
    session.participantCount = participants.length;
    session.maxConcurrentParticipants = Math.max(session.maxConcurrentParticipants, session.participantCount);
    session.totalJoins++;

    // Start session if not already started
    if (session.status === 'created' && userId === session.hostUserId) {
      session.status = 'active';
      session.startedAt = Date.now();
      this.emit('session-started', session);
    }

    // Update user sessions
    const userSessionIds = this.userSessions.get(userId) || [];
    if (!userSessionIds.includes(sessionId)) {
      userSessionIds.push(sessionId);
      this.userSessions.set(userId, userSessionIds);
    }

    this.metrics.totalParticipants++;
    this.updateMetrics();

    logger.info(`User joined session: ${participant.displayName}`, {
      userId,
      sessionId,
      sessionTitle: session.title,
      role: participant.role
    });

    this.emit('participant-joined', { sessionId, participant, session });

    return {
      sessionId,
      participant,
      session: this.sanitizeSessionForUser(session, userId),
      participants: participants.map(p => this.sanitizeParticipant(p))
    };
  }

  async leaveSession(userId, sessionId) {
    const session = this.activeSessions.get(sessionId);
    if (!session) return false;

    let participants = this.sessionParticipants.get(sessionId) || [];
    const participant = participants.find(p => p.userId === userId);
    
    if (!participant) return false;

    // Remove participant
    participants = participants.filter(p => p.userId !== userId);
    this.sessionParticipants.set(sessionId, participants);

    // Update session
    session.participantCount = participants.length;

    // Stop any active presentations/control by this user
    await this.stopPresentation(userId, sessionId);
    await this.releaseRemoteControl(userId, sessionId);

    // Update user sessions
    const userSessionIds = this.userSessions.get(userId) || [];
    const filteredSessions = userSessionIds.filter(id => id !== sessionId);
    this.userSessions.set(userId, filteredSessions);

    // End session if host left and no other participants
    if (userId === session.hostUserId && participants.length === 0) {
      await this.endSession(sessionId);
    } else if (userId === session.hostUserId && participants.length > 0) {
      // Transfer host to longest-serving participant
      const newHost = participants.sort((a, b) => a.joinedAt - b.joinedAt)[0];
      session.hostUserId = newHost.userId;
      newHost.role = 'host';
      
      logger.info(`Host transferred to: ${newHost.displayName}`, {
        sessionId,
        newHostUserId: newHost.userId
      });

      this.emit('host-transferred', { sessionId, oldHostUserId: userId, newHost });
    }

    logger.info(`User left session: ${participant.displayName}`, {
      userId,
      sessionId,
      remainingParticipants: participants.length
    });

    this.emit('participant-left', { sessionId, participant, session });
    return true;
  }

  async startScreenSharing(userId, sessionId, options = {}) {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.features.screenSharing) {
      throw new Error('Screen sharing not available');
    }

    const participant = this.getParticipant(sessionId, userId);
    if (!participant) {
      throw new Error('User not in session');
    }

    // Check permissions
    if (!participant.permissions.canShare) {
      throw new Error('No permission to share screen');
    }

    // Check if multiple presenters allowed
    if (!this.options.multiplePresenterMode && session.presenters.length > 0) {
      throw new Error('Another user is already presenting');
    }

    // Start presentation
    participant.status = 'presenting';
    if (!session.presenters.includes(userId)) {
      session.presenters.push(userId);
    }

    if (!session.currentPresenter) {
      session.currentPresenter = userId;
    }

    const presentation = {
      userId,
      displayName: participant.displayName,
      startedAt: Date.now(),
      type: options.type || 'screen', // screen, window, application
      quality: options.quality || this.options.screenShareQuality,
      includeAudio: options.includeAudio || false,
      monitorId: options.monitorId || 0
    };

    this.metrics.screensShared++;

    logger.info(`Screen sharing started: ${participant.displayName}`, {
      userId,
      sessionId,
      type: presentation.type
    });

    this.emit('screen-sharing-started', { sessionId, userId, presentation });

    return presentation;
  }

  async stopPresentation(userId, sessionId) {
    const session = this.activeSessions.get(sessionId);
    if (!session) return false;

    const participant = this.getParticipant(sessionId, userId);
    if (!participant) return false;

    // Remove from presenters
    session.presenters = session.presenters.filter(id => id !== userId);
    participant.status = 'joined';

    // Update current presenter
    if (session.currentPresenter === userId) {
      session.currentPresenter = session.presenters[0] || null;
    }

    logger.info(`Screen sharing stopped: ${participant.displayName}`, {
      userId,
      sessionId
    });

    this.emit('screen-sharing-stopped', { sessionId, userId });
    return true;
  }

  async requestRemoteControl(requesterUserId, sessionId, targetUserId) {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.features.remoteControl) {
      throw new Error('Remote control not available');
    }

    const requester = this.getParticipant(sessionId, requesterUserId);
    if (!requester || !requester.permissions.canControl) {
      throw new Error('No permission for remote control');
    }

    const target = this.getParticipant(sessionId, targetUserId);
    if (!target) {
      throw new Error('Target user not found');
    }

    const requestId = uuidv4();
    const request = {
      id: requestId,
      sessionId,
      requesterUserId,
      requesterName: requester.displayName,
      targetUserId,
      targetName: target.displayName,
      requestedAt: Date.now(),
      status: 'pending',
      expiresAt: Date.now() + 30000 // 30 seconds to respond
    };

    this.controlRequests.set(requestId, request);

    // Notify target user
    this.emit('remote-control-requested', request);

    logger.info(`Remote control requested: ${requester.displayName} → ${target.displayName}`, {
      requestId,
      sessionId
    });

    return request;
  }

  async respondToControlRequest(requestId, targetUserId, approved) {
    const request = this.controlRequests.get(requestId);
    if (!request || request.targetUserId !== targetUserId) {
      throw new Error('Control request not found');
    }

    if (Date.now() > request.expiresAt) {
      this.controlRequests.delete(requestId);
      throw new Error('Control request expired');
    }

    request.status = approved ? 'approved' : 'denied';
    request.respondedAt = Date.now();

    if (approved) {
      await this.grantRemoteControl(request.requesterUserId, request.sessionId, targetUserId);
    }

    this.controlRequests.delete(requestId);
    this.metrics.controlRequestsProcessed++;

    logger.info(`Control request ${approved ? 'approved' : 'denied'}`, {
      requestId,
      requesterUserId: request.requesterUserId,
      targetUserId
    });

    this.emit('remote-control-responded', { request, approved });

    return request;
  }

  async grantRemoteControl(controllerUserId, sessionId, targetUserId) {
    const session = this.activeSessions.get(sessionId);
    if (!session) throw new Error('Session not found');

    const controller = this.getParticipant(sessionId, controllerUserId);
    const target = this.getParticipant(sessionId, targetUserId);

    if (!controller || !target) {
      throw new Error('Participants not found');
    }

    const controlInfo = {
      controllerId: controllerUserId,
      controllerName: controller.displayName,
      targetId: targetUserId,
      targetName: target.displayName,
      grantedAt: Date.now(),
      expiresAt: Date.now() + this.options.controlTimeouts
    };

    this.activeControls.set(sessionId, controlInfo);
    controller.status = 'controlling';

    logger.info(`Remote control granted: ${controller.displayName} → ${target.displayName}`, {
      sessionId,
      controllerUserId,
      targetUserId
    });

    this.emit('remote-control-granted', { sessionId, controlInfo });

    return controlInfo;
  }

  async releaseRemoteControl(userId, sessionId) {
    const controlInfo = this.activeControls.get(sessionId);
    if (!controlInfo || controlInfo.controllerId !== userId) return false;

    this.activeControls.delete(sessionId);

    const controller = this.getParticipant(sessionId, userId);
    if (controller) {
      controller.status = 'joined';
    }

    logger.info(`Remote control released`, {
      sessionId,
      controllerId: userId
    });

    this.emit('remote-control-released', { sessionId, userId });
    return true;
  }

  async sendChatMessage(userId, sessionId, message, options = {}) {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.features.chat) {
      throw new Error('Chat not available');
    }

    const participant = this.getParticipant(sessionId, userId);
    if (!participant || !participant.permissions.canChat) {
      throw new Error('No permission to send messages');
    }

    const chatMessage = {
      id: uuidv4(),
      userId,
      displayName: participant.displayName,
      message: message.trim(),
      timestamp: Date.now(),
      type: options.type || 'text', // text, system, file, emoji
      edited: false,
      reactions: new Map()
    };

    const chatHistory = this.chatHistory.get(sessionId) || [];
    chatHistory.push(chatMessage);
    this.chatHistory.set(sessionId, chatHistory);

    session.messagesCount++;
    this.metrics.messagesExchanged++;

    logger.debug(`Chat message sent in session ${sessionId}`, {
      userId,
      messageLength: message.length
    });

    this.emit('chat-message', { sessionId, message: chatMessage });

    return chatMessage;
  }

  async shareFile(userId, sessionId, fileInfo) {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.features.fileSharing) {
      throw new Error('File sharing not available');
    }

    const participant = this.getParticipant(sessionId, userId);
    if (!participant || !participant.permissions.canUploadFiles) {
      throw new Error('No permission to share files');
    }

    const sharedFile = {
      id: uuidv4(),
      userId,
      displayName: participant.displayName,
      filename: fileInfo.filename,
      size: fileInfo.size,
      type: fileInfo.type,
      uploadedAt: Date.now(),
      downloadCount: 0,
      path: fileInfo.path // Server file path
    };

    const sharedFiles = this.sharedFiles.get(sessionId) || [];
    sharedFiles.push(sharedFile);
    this.sharedFiles.set(sessionId, sharedFiles);

    session.filesSharedCount++;
    this.metrics.filesShared++;

    logger.info(`File shared: ${fileInfo.filename}`, {
      userId,
      sessionId,
      fileSize: fileInfo.size
    });

    this.emit('file-shared', { sessionId, file: sharedFile });

    return sharedFile;
  }

  async addAnnotation(userId, sessionId, annotation) {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.features.annotations) {
      throw new Error('Annotations not available');
    }

    const participant = this.getParticipant(sessionId, userId);
    if (!participant || !participant.permissions.canAnnotate) {
      throw new Error('No permission to annotate');
    }

    const annotationData = {
      id: uuidv4(),
      userId,
      displayName: participant.displayName,
      type: annotation.type, // arrow, circle, rectangle, text, pen
      coordinates: annotation.coordinates,
      properties: annotation.properties, // color, thickness, text, etc.
      createdAt: Date.now(),
      visible: true
    };

    const annotations = this.annotations.get(sessionId) || [];
    annotations.push(annotationData);
    this.annotations.set(sessionId, annotations);

    this.emit('annotation-added', { sessionId, annotation: annotationData });

    return annotationData;
  }

  async startRecording(userId, sessionId, options = {}) {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.features.recording) {
      throw new Error('Recording not available');
    }

    const participant = this.getParticipant(sessionId, userId);
    if (!participant || participant.role !== 'host') {
      throw new Error('Only host can start recording');
    }

    const recording = {
      id: uuidv4(),
      sessionId,
      startedBy: userId,
      startedAt: Date.now(),
      status: 'recording',
      includeAudio: options.includeAudio !== false,
      includeScreenShare: options.includeScreenShare !== false,
      includeParticipants: options.includeParticipants !== false,
      quality: options.quality || 'high'
    };

    this.recordings.set(sessionId, recording);

    logger.info(`Recording started for session: ${session.title}`, {
      recordingId: recording.id,
      sessionId,
      startedBy: userId
    });

    this.emit('recording-started', { sessionId, recording });

    return recording;
  }

  async endSession(sessionId, endedBy = null) {
    const session = this.activeSessions.get(sessionId);
    if (!session) return false;

    const now = Date.now();
    session.status = 'ended';
    session.endedAt = now;

    // Stop any active recordings
    const recording = this.recordings.get(sessionId);
    if (recording && recording.status === 'recording') {
      recording.status = 'completed';
      recording.endedAt = now;
      recording.duration = now - recording.startedAt;
      this.metrics.recordingMinutes += Math.round(recording.duration / 60000);
    }

    // Clear active controls
    this.activeControls.delete(sessionId);

    // Notify all participants
    const participants = this.sessionParticipants.get(sessionId) || [];
    for (const participant of participants) {
      this.emit('participant-left', { sessionId, participant, session });
      
      // Update user sessions
      const userSessionIds = this.userSessions.get(participant.userId) || [];
      const filteredSessions = userSessionIds.filter(id => id !== sessionId);
      this.userSessions.set(participant.userId, filteredSessions);
    }

    this.updateMetrics();

    logger.info(`Session ended: ${session.title}`, {
      sessionId,
      duration: now - (session.startedAt || session.createdAt),
      participantCount: session.maxConcurrentParticipants,
      messagesCount: session.messagesCount,
      endedBy
    });

    this.emit('session-ended', { session, endedBy });

    return true;
  }

  getParticipant(sessionId, userId) {
    const participants = this.sessionParticipants.get(sessionId) || [];
    return participants.find(p => p.userId === userId);
  }

  getParticipantPermissions(sessionId, userId) {
    const session = this.activeSessions.get(sessionId);
    if (!session) return this.options.defaultParticipantPermissions;

    // Host gets all permissions
    if (userId === session.hostUserId) {
      return {
        canShare: true,
        canControl: true,
        canAnnotate: true,
        canChat: true,
        canUploadFiles: true
      };
    }

    // Check for permission overrides
    const overrides = this.permissionOverrides.get(sessionId);
    if (overrides && overrides.has(userId)) {
      return { ...this.options.defaultParticipantPermissions, ...overrides.get(userId) };
    }

    return this.options.defaultParticipantPermissions;
  }

  sanitizeSessionForUser(session, userId) {
    const participant = this.getParticipant(session.id, userId);
    const isHost = userId === session.hostUserId;
    
    return {
      id: session.id,
      title: session.title,
      description: session.description,
      status: session.status,
      startedAt: session.startedAt,
      participantCount: session.participantCount,
      maxParticipants: session.maxParticipants,
      features: session.features,
      currentPresenter: session.currentPresenter,
      presenters: session.presenters,
      isHost,
      userRole: participant?.role,
      userPermissions: participant?.permissions
    };
  }

  sanitizeParticipant(participant) {
    return {
      userId: participant.userId,
      displayName: participant.displayName,
      role: participant.role,
      status: participant.status,
      joinedAt: participant.joinedAt,
      hasAudio: participant.hasAudio,
      hasVideo: participant.hasVideo,
      hasScreenShare: participant.hasScreenShare
    };
  }

  startSessionMonitoring() {
    // Check session timeouts and cleanup
    setInterval(() => {
      for (const [sessionId, session] of this.activeSessions) {
        const sessionDuration = Date.now() - (session.startedAt || session.createdAt);
        
        // Auto-end sessions that exceed max duration
        if (sessionDuration > this.options.maxSessionDuration) {
          logger.info(`Auto-ending session due to duration limit: ${session.title}`);
          this.endSession(sessionId, 'system');
        }
        
        // Check for empty sessions
        const participants = this.sessionParticipants.get(sessionId) || [];
        if (session.status === 'active' && participants.length === 0) {
          logger.info(`Auto-ending empty session: ${session.title}`);
          this.endSession(sessionId, 'system');
        }
      }

      // Clean up expired control requests
      for (const [requestId, request] of this.controlRequests) {
        if (Date.now() > request.expiresAt) {
          this.controlRequests.delete(requestId);
        }
      }

      // Clean up expired controls
      for (const [sessionId, controlInfo] of this.activeControls) {
        if (Date.now() > controlInfo.expiresAt) {
          this.releaseRemoteControl(controlInfo.controllerId, sessionId);
        }
      }
    }, 60000); // Every minute
  }

  startCleanupRoutines() {
    // Clean up ended sessions after retention period
    setInterval(() => {
      const cutoffTime = Date.now() - (24 * 60 * 60 * 1000); // 24 hours
      
      for (const [sessionId, session] of this.activeSessions) {
        if (session.status === 'ended' && session.endedAt < cutoffTime) {
          this.activeSessions.delete(sessionId);
          this.sessionParticipants.delete(sessionId);
          this.whiteboards.delete(sessionId);
          this.chatHistory.delete(sessionId);
          this.sharedFiles.delete(sessionId);
          this.annotations.delete(sessionId);
          this.recordings.delete(sessionId);
        }
      }
    }, 3600000); // Every hour
  }

  updateMetrics() {
    this.metrics.activeSessionsCount = Array.from(this.activeSessions.values())
      .filter(s => s.status === 'active').length;
  }

  // Public API methods
  getActiveSessions(userId = null) {
    const sessions = Array.from(this.activeSessions.values())
      .filter(s => s.status === 'active');
    
    if (userId) {
      return sessions
        .filter(s => this.getParticipant(s.id, userId))
        .map(s => this.sanitizeSessionForUser(s, userId));
    }
    
    return sessions.map(s => ({
      id: s.id,
      title: s.title,
      participantCount: s.participantCount,
      maxParticipants: s.maxParticipants,
      startedAt: s.startedAt,
      features: s.features
    }));
  }

  getSessionDetails(sessionId, userId) {
    const session = this.activeSessions.get(sessionId);
    if (!session) return null;

    const participant = this.getParticipant(sessionId, userId);
    if (!participant) return null;

    const participants = this.sessionParticipants.get(sessionId) || [];
    const chatHistory = this.chatHistory.get(sessionId) || [];
    const sharedFiles = this.sharedFiles.get(sessionId) || [];
    const annotations = this.annotations.get(sessionId) || [];

    return {
      session: this.sanitizeSessionForUser(session, userId),
      participants: participants.map(p => this.sanitizeParticipant(p)),
      chatHistory: chatHistory.slice(-50), // Last 50 messages
      sharedFiles,
      annotations,
      activeControl: this.activeControls.get(sessionId)
    };
  }

  getUserSessions(userId) {
    const sessionIds = this.userSessions.get(userId) || [];
    return sessionIds.map(sessionId => {
      const session = this.activeSessions.get(sessionId);
      return session ? this.sanitizeSessionForUser(session, userId) : null;
    }).filter(Boolean);
  }

  getMetrics() {
    this.updateMetrics();
    return {
      ...this.metrics,
      totalActiveSessions: this.activeSessions.size,
      totalActiveParticipants: Array.from(this.sessionParticipants.values())
        .reduce((total, participants) => total + participants.length, 0)
    };
  }

  async cleanup() {
    // End all active sessions
    for (const [sessionId] of this.activeSessions) {
      await this.endSession(sessionId, 'system');
    }

    // Clear all data
    this.activeSessions.clear();
    this.userSessions.clear();
    this.sessionParticipants.clear();
    this.whiteboards.clear();
    this.chatHistory.clear();
    this.sharedFiles.clear();
    this.annotations.clear();
    this.recordings.clear();
    this.controlRequests.clear();
    this.activeControls.clear();
    this.permissionOverrides.clear();

    this.removeAllListeners();
    logger.info('Team Tools system cleaned up');
  }
}

module.exports = TeamTools;