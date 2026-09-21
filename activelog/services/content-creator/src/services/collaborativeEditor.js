const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const crypto = require('crypto');

class CollaborativeEditor extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        this.sessions = new Map();
        this.activeUsers = new Map();
        this.operationalTransforms = new Map();
        
        this.sessionTypes = {
            REAL_TIME: 'real_time',
            ASYNC: 'async',
            REVIEW: 'review',
            APPROVAL: 'approval'
        };
        
        this.permissions = {
            OWNER: { edit: true, invite: true, admin: true, view: true },
            EDITOR: { edit: true, invite: false, admin: false, view: true },
            REVIEWER: { edit: false, invite: false, admin: false, view: true, comment: true },
            VIEWER: { edit: false, invite: false, admin: false, view: true }
        };
        
        this.operationTypes = {
            INSERT: 'insert',
            DELETE: 'delete',
            RETAIN: 'retain',
            FORMAT: 'format',
            MOVE: 'move'
        };
        
        this.conflictResolution = {
            LAST_WRITE_WINS: 'last_write_wins',
            OPERATIONAL_TRANSFORM: 'operational_transform',
            MANUAL_MERGE: 'manual_merge',
            BRANCH_MERGE: 'branch_merge'
        };
        
        this.setupEventListeners();
        this.logger.info('Collaborative Editor service initialized');
    }
    
    setupEventListeners() {
        this.on('session_created', (data) => {
            this.io.emit('collaboration_session_created', data);
        });
        
        this.on('user_joined', (data) => {
            this.io.to(`collab_${data.sessionId}`).emit('user_joined', data);
        });
        
        this.on('user_left', (data) => {
            this.io.to(`collab_${data.sessionId}`).emit('user_left', data);
        });
        
        this.on('operation_applied', (data) => {
            this.io.to(`collab_${data.sessionId}`).emit('operation_applied', data);
        });
        
        this.on('conflict_detected', (data) => {
            this.io.to(`collab_${data.sessionId}`).emit('conflict_detected', data);
        });
        
        this.on('document_synced', (data) => {
            this.io.to(`collab_${data.sessionId}`).emit('document_synced', data);
        });
    }
    
    async createCollaborationSession(sessionData) {
        try {
            const sessionId = uuidv4();
            const {
                projectId,
                type,
                title,
                description,
                ownerId,
                settings,
                initialDocument
            } = sessionData;
            
            const session = {
                id: sessionId,
                projectId: projectId || 'unknown',
                type: type || this.sessionTypes.REAL_TIME,
                title: title || 'Untitled Collaboration',
                description: description || '',
                ownerId: ownerId || 'system',
                status: 'active',
                participants: [
                    {
                        userId: ownerId || 'system',
                        role: 'OWNER',
                        permissions: this.permissions.OWNER,
                        joinedAt: new Date(),
                        lastActive: new Date(),
                        cursor: { line: 0, column: 0 },
                        selection: null
                    }
                ],
                document: {
                    content: initialDocument || '',
                    version: 1,
                    operations: [],
                    checkpoints: [],
                    lastModified: new Date()
                },
                settings: {
                    conflictResolution: settings?.conflictResolution || this.conflictResolution.OPERATIONAL_TRANSFORM,
                    autoSave: settings?.autoSave !== false,
                    saveInterval: settings?.saveInterval || 30000,
                    maxParticipants: settings?.maxParticipants || 10,
                    allowAnonymous: settings?.allowAnonymous || false,
                    requireApproval: settings?.requireApproval || false,
                    ...settings
                },
                metadata: {
                    created: new Date(),
                    lastActivity: new Date(),
                    totalOperations: 0,
                    activeUsers: 1
                }
            };
            
            this.sessions.set(sessionId, session);
            await this.redis.setEx(`collab_session:${sessionId}`, 7200, JSON.stringify(session));
            
            // Initialize operational transform state
            this.operationalTransforms.set(sessionId, {
                pendingOps: [],
                acknowledgedOps: new Map(),
                transformQueue: []
            });
            
            this.emit('session_created', { sessionId, session });
            this.logger.info(`Collaboration session created: ${sessionId}`);
            
            return { success: true, sessionId, session };
        } catch (error) {
            this.logger.error('Create collaboration session error:', error);
            throw error;
        }
    }
    
    async inviteCollaborator(inviteData) {
        try {
            const { sessionId, userId, email, role, message } = inviteData;
            const session = await this.getSession(sessionId);
            
            if (!session) {
                throw new Error(`Session ${sessionId} not found`);
            }
            
            const inviteId = uuidv4();
            const invite = {
                id: inviteId,
                sessionId: sessionId,
                invitedBy: inviteData.invitedBy || 'system',
                userId: userId,
                email: email,
                role: role || 'EDITOR',
                permissions: this.permissions[role || 'EDITOR'],
                message: message || '',
                status: 'pending',
                expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
                createdAt: new Date()
            };
            
            await this.redis.setEx(`collab_invite:${inviteId}`, 604800, JSON.stringify(invite));
            
            // Send invitation notification (in real implementation, this would send email)
            this.emit('invitation_sent', { inviteId, invite, session });
            
            this.logger.info(`Collaboration invite sent: ${inviteId} for session ${sessionId}`);
            
            return { success: true, inviteId, invite };
        } catch (error) {
            this.logger.error('Invite collaborator error:', error);
            throw error;
        }
    }
    
    async joinSession(joinData) {
        try {
            const { sessionId, userId, inviteId, username } = joinData;
            const session = await this.getSession(sessionId);
            
            if (!session) {
                throw new Error(`Session ${sessionId} not found`);
            }
            
            // Verify invite if provided
            if (inviteId) {
                const invite = await this.getInvite(inviteId);
                if (!invite || invite.sessionId !== sessionId) {
                    throw new Error('Invalid invitation');
                }
                
                if (invite.status !== 'pending') {
                    throw new Error('Invitation already used or expired');
                }
                
                // Mark invite as used
                invite.status = 'accepted';
                invite.acceptedAt = new Date();
                await this.redis.setEx(`collab_invite:${inviteId}`, 604800, JSON.stringify(invite));
            }
            
            // Check if user is already in session
            const existingParticipant = session.participants.find(p => p.userId === userId);
            if (existingParticipant) {
                existingParticipant.lastActive = new Date();
                existingParticipant.status = 'active';
            } else {
                // Add new participant
                if (session.participants.length >= session.settings.maxParticipants) {
                    throw new Error('Session is full');
                }
                
                const participant = {
                    userId: userId,
                    username: username || `User_${userId.slice(0, 8)}`,
                    role: inviteId ? (await this.getInvite(inviteId)).role : 'VIEWER',
                    permissions: inviteId ? (await this.getInvite(inviteId)).permissions : this.permissions.VIEWER,
                    joinedAt: new Date(),
                    lastActive: new Date(),
                    status: 'active',
                    cursor: { line: 0, column: 0 },
                    selection: null
                };
                
                session.participants.push(participant);
                session.metadata.activeUsers = session.participants.filter(p => p.status === 'active').length;
            }
            
            session.metadata.lastActivity = new Date();
            await this.updateSession(session);
            
            this.activeUsers.set(`${sessionId}:${userId}`, {
                sessionId,
                userId,
                socketId: null,
                joinedAt: new Date()
            });
            
            this.emit('user_joined', { sessionId, userId, session });
            this.logger.info(`User joined session: ${userId} -> ${sessionId}`);
            
            return { success: true, sessionId, participant: session.participants.find(p => p.userId === userId) };
        } catch (error) {
            this.logger.error('Join session error:', error);
            throw error;
        }
    }
    
    async leaveSession(leaveData) {
        try {
            const { sessionId, userId } = leaveData;
            const session = await this.getSession(sessionId);
            
            if (!session) {
                throw new Error(`Session ${sessionId} not found`);
            }
            
            const participant = session.participants.find(p => p.userId === userId);
            if (participant) {
                participant.status = 'inactive';
                participant.leftAt = new Date();
                
                session.metadata.activeUsers = session.participants.filter(p => p.status === 'active').length;
                session.metadata.lastActivity = new Date();
                
                await this.updateSession(session);
            }
            
            this.activeUsers.delete(`${sessionId}:${userId}`);
            
            this.emit('user_left', { sessionId, userId, session });
            this.logger.info(`User left session: ${userId} -> ${sessionId}`);
            
            return { success: true, sessionId, userId };
        } catch (error) {
            this.logger.error('Leave session error:', error);
            throw error;
        }
    }
    
    async applyOperation(operationData) {
        try {
            const { sessionId, userId, operation, clientVersion } = operationData;
            const session = await this.getSession(sessionId);
            
            if (!session) {
                throw new Error(`Session ${sessionId} not found`);
            }
            
            const participant = session.participants.find(p => p.userId === userId);
            if (!participant || !participant.permissions.edit) {
                throw new Error('User does not have edit permissions');
            }
            
            const operationId = uuidv4();
            const op = {
                id: operationId,
                sessionId: sessionId,
                userId: userId,
                type: operation.type,
                position: operation.position,
                content: operation.content,
                length: operation.length,
                clientVersion: clientVersion || session.document.version,
                serverVersion: session.document.version,
                timestamp: new Date(),
                applied: false
            };
            
            // Apply operational transformation if needed
            const transformedOp = await this.transformOperation(sessionId, op);
            
            // Apply operation to document
            const result = await this.applyOperationToDocument(session, transformedOp);
            
            if (result.success) {
                transformedOp.applied = true;
                session.document.operations.push(transformedOp);
                session.document.version++;
                session.document.lastModified = new Date();
                session.metadata.totalOperations++;
                session.metadata.lastActivity = new Date();
                
                // Update participant cursor/selection
                if (operation.cursor) {
                    participant.cursor = operation.cursor;
                }
                if (operation.selection) {
                    participant.selection = operation.selection;
                }
                participant.lastActive = new Date();
                
                await this.updateSession(session);
                
                this.emit('operation_applied', {
                    sessionId,
                    operationId,
                    operation: transformedOp,
                    document: session.document,
                    userId
                });
                
                return { success: true, operationId, transformedOp, newVersion: session.document.version };
            } else {
                throw new Error(`Failed to apply operation: ${result.error}`);
            }
        } catch (error) {
            this.logger.error('Apply operation error:', error);
            throw error;
        }
    }
    
    async transformOperation(sessionId, operation) {
        try {
            const otState = this.operationalTransforms.get(sessionId);
            if (!otState) {
                return operation; // No transformation needed
            }
            
            let transformedOp = { ...operation };
            
            // Transform against all operations that happened after the client's version
            const pendingOps = otState.pendingOps.filter(op => 
                op.serverVersion > operation.clientVersion && op.userId !== operation.userId
            );
            
            for (const pendingOp of pendingOps) {
                transformedOp = this.operationalTransform(transformedOp, pendingOp);
            }
            
            return transformedOp;
        } catch (error) {
            this.logger.error('Transform operation error:', error);
            return operation;
        }
    }
    
    operationalTransform(op1, op2) {
        // Simplified operational transform implementation
        // In a real implementation, this would be more sophisticated
        
        if (op1.type === this.operationTypes.INSERT && op2.type === this.operationTypes.INSERT) {
            if (op2.position <= op1.position) {
                return {
                    ...op1,
                    position: op1.position + (op2.content ? op2.content.length : op2.length || 0)
                };
            }
        } else if (op1.type === this.operationTypes.DELETE && op2.type === this.operationTypes.INSERT) {
            if (op2.position <= op1.position) {
                return {
                    ...op1,
                    position: op1.position + (op2.content ? op2.content.length : op2.length || 0)
                };
            }
        } else if (op1.type === this.operationTypes.INSERT && op2.type === this.operationTypes.DELETE) {
            if (op2.position < op1.position) {
                return {
                    ...op1,
                    position: Math.max(op1.position - (op2.length || 0), op2.position)
                };
            }
        } else if (op1.type === this.operationTypes.DELETE && op2.type === this.operationTypes.DELETE) {
            if (op2.position < op1.position) {
                return {
                    ...op1,
                    position: Math.max(op1.position - (op2.length || 0), op2.position)
                };
            } else if (op2.position < op1.position + (op1.length || 0)) {
                // Overlapping deletes
                const overlapStart = Math.max(op1.position, op2.position);
                const overlapEnd = Math.min(op1.position + (op1.length || 0), op2.position + (op2.length || 0));
                const overlapLength = overlapEnd - overlapStart;
                
                return {
                    ...op1,
                    length: (op1.length || 0) - overlapLength
                };
            }
        }
        
        return op1;
    }
    
    async applyOperationToDocument(session, operation) {
        try {
            let content = session.document.content;
            
            switch (operation.type) {
                case this.operationTypes.INSERT:
                    if (operation.position <= content.length) {
                        session.document.content = 
                            content.slice(0, operation.position) + 
                            operation.content + 
                            content.slice(operation.position);
                        return { success: true };
                    }
                    break;
                    
                case this.operationTypes.DELETE:
                    if (operation.position >= 0 && operation.position + (operation.length || 0) <= content.length) {
                        session.document.content = 
                            content.slice(0, operation.position) + 
                            content.slice(operation.position + (operation.length || 0));
                        return { success: true };
                    }
                    break;
                    
                case this.operationTypes.RETAIN:
                    // Retain operations don't modify content
                    return { success: true };
                    
                default:
                    return { success: false, error: `Unknown operation type: ${operation.type}` };
            }
            
            return { success: false, error: 'Invalid operation parameters' };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async createCheckpoint(checkpointData) {
        try {
            const { sessionId, userId, description } = checkpointData;
            const session = await this.getSession(sessionId);
            
            if (!session) {
                throw new Error(`Session ${sessionId} not found`);
            }
            
            const checkpointId = uuidv4();
            const checkpoint = {
                id: checkpointId,
                version: session.document.version,
                content: session.document.content,
                description: description || `Checkpoint ${session.document.checkpoints.length + 1}`,
                createdBy: userId,
                createdAt: new Date(),
                operations: [...session.document.operations]
            };
            
            session.document.checkpoints.push(checkpoint);
            await this.updateSession(session);
            
            this.emit('checkpoint_created', { sessionId, checkpointId, checkpoint });
            this.logger.info(`Checkpoint created: ${checkpointId} for session ${sessionId}`);
            
            return { success: true, checkpointId, checkpoint };
        } catch (error) {
            this.logger.error('Create checkpoint error:', error);
            throw error;
        }
    }
    
    async restoreCheckpoint(restoreData) {
        try {
            const { sessionId, checkpointId, userId } = restoreData;
            const session = await this.getSession(sessionId);
            
            if (!session) {
                throw new Error(`Session ${sessionId} not found`);
            }
            
            const checkpoint = session.document.checkpoints.find(c => c.id === checkpointId);
            if (!checkpoint) {
                throw new Error(`Checkpoint ${checkpointId} not found`);
            }
            
            // Backup current state before restore
            const backupCheckpoint = {
                id: uuidv4(),
                version: session.document.version,
                content: session.document.content,
                description: 'Auto-backup before restore',
                createdBy: userId,
                createdAt: new Date(),
                operations: [...session.document.operations]
            };
            
            session.document.checkpoints.push(backupCheckpoint);
            
            // Restore checkpoint
            session.document.content = checkpoint.content;
            session.document.version++;
            session.document.lastModified = new Date();
            
            await this.updateSession(session);
            
            this.emit('checkpoint_restored', { sessionId, checkpointId, backupId: backupCheckpoint.id });
            this.logger.info(`Checkpoint restored: ${checkpointId} for session ${sessionId}`);
            
            return { success: true, checkpointId, backupId: backupCheckpoint.id };
        } catch (error) {
            this.logger.error('Restore checkpoint error:', error);
            throw error;
        }
    }
    
    async syncDocument(sessionId, userId) {
        try {
            const session = await this.getSession(sessionId);
            
            if (!session) {
                throw new Error(`Session ${sessionId} not found`);
            }
            
            const participant = session.participants.find(p => p.userId === userId);
            if (!participant) {
                throw new Error(`User ${userId} is not a participant in session ${sessionId}`);
            }
            
            this.emit('document_synced', {
                sessionId,
                userId,
                document: session.document,
                participants: session.participants.filter(p => p.status === 'active')
            });
            
            return {
                success: true,
                document: session.document,
                participants: session.participants.filter(p => p.status === 'active'),
                timestamp: new Date()
            };
        } catch (error) {
            this.logger.error('Sync document error:', error);
            throw error;
        }
    }
    
    async getSession(sessionId) {
        try {
            if (this.sessions.has(sessionId)) {
                return this.sessions.get(sessionId);
            }
            
            const cached = await this.redis.get(`collab_session:${sessionId}`);
            if (cached) {
                const session = JSON.parse(cached);
                this.sessions.set(sessionId, session);
                return session;
            }
            
            return null;
        } catch (error) {
            this.logger.error('Get session error:', error);
            return null;
        }
    }
    
    async getInvite(inviteId) {
        try {
            const cached = await this.redis.get(`collab_invite:${inviteId}`);
            return cached ? JSON.parse(cached) : null;
        } catch (error) {
            this.logger.error('Get invite error:', error);
            return null;
        }
    }
    
    async updateSession(session) {
        try {
            this.sessions.set(session.id, session);
            await this.redis.setEx(`collab_session:${session.id}`, 7200, JSON.stringify(session));
        } catch (error) {
            this.logger.error('Update session error:', error);
        }
    }
    
    async getStats() {
        try {
            const stats = {
                sessionTypes: this.sessionTypes,
                permissions: Object.keys(this.permissions),
                operationTypes: this.operationTypes,
                activeSessions: this.sessions.size,
                activeUsers: this.activeUsers.size,
                totalOperations: 0,
                timestamp: new Date()
            };
            
            // Calculate total operations across all sessions
            for (const session of this.sessions.values()) {
                stats.totalOperations += session.metadata.totalOperations || 0;
            }
            
            return stats;
        } catch (error) {
            this.logger.error('Get stats error:', error);
            throw error;
        }
    }
}

module.exports = CollaborativeEditor;