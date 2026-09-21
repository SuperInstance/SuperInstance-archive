const express = require('express');
const WebSocket = require('ws');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const EventEmitter = require('events');

// Import all services
const ContainerManager = require('./src/services/ContainerManager');
const ClaudeCodeService = require('./src/services/ClaudeCodeService');
const EnvironmentManager = require('./src/services/EnvironmentManager');
const CodeExecutionService = require('./src/services/CodeExecutionService');
const LiveEditingService = require('./src/services/LiveEditingService');
const DeploymentService = require('./src/services/DeploymentService');
const CollaborationService = require('./src/services/CollaborationService');
const APIKeyVault = require('./src/services/APIKeyVault');
const UsageTracker = require('./src/services/UsageTracker');
const BackupService = require('./src/services/BackupService');

class DevSandboxServer extends EventEmitter {
    constructor() {
        super();
        this.port = process.env.PORT || 8303;
        this.app = express();
        this.server = http.createServer(this.app);
        this.wss = new WebSocket.Server({ server: this.server });
        
        // Initialize services
        this.containerManager = null;
        this.claudeCodeService = null;
        this.environmentManager = null;
        this.codeExecutionService = null;
        this.liveEditingService = null;
        this.deploymentService = null;
        this.collaborationService = null;
        this.apiKeyVault = null;
        this.usageTracker = null;
        this.backupService = null;
        
        this.connectedUsers = new Map();
        this.userSessions = new Map();
    }

    async initialize() {
        console.log('🚀 Initializing Developer Sandbox Server...');
        
        try {
            await this.initializeServices();
            this.setupMiddleware();
            this.setupRoutes();
            this.setupWebSocketHandlers();
            this.setupEventHandlers();
            
            console.log('✅ All services initialized successfully');
        } catch (error) {
            console.error('❌ Failed to initialize server:', error);
            throw error;
        }
    }

    async initializeServices() {
        console.log('📦 Initializing services...');
        
        // Initialize core services
        this.containerManager = new ContainerManager({
            dockerSocket: process.env.DOCKER_SOCKET || '/var/run/docker.sock',
            developmentMode: process.env.NODE_ENV === 'development' || true
        });
        
        this.claudeCodeService = new ClaudeCodeService({
            apiKey: process.env.CLAUDE_API_KEY,
            baseURL: process.env.CLAUDE_BASE_URL
        });
        
        this.environmentManager = new EnvironmentManager({
            templatesDir: './src/templates',
            workspaceDir: process.env.WORKSPACE_DIR || '/tmp/dev-sandbox-workspaces'
        });
        
        this.codeExecutionService = new CodeExecutionService({
            containerManager: this.containerManager,
            maxExecutionTime: 300000 // 5 minutes
        });
        
        this.liveEditingService = new LiveEditingService({
            workspaceDir: process.env.WORKSPACE_DIR || '/tmp/dev-sandbox-workspaces'
        });
        
        this.deploymentService = new DeploymentService({
            containerManager: this.containerManager,
            environmentManager: this.environmentManager
        });
        
        this.collaborationService = new CollaborationService({
            maxCollaborators: 100
        });
        
        this.apiKeyVault = new APIKeyVault({
            encryptionKey: process.env.VAULT_ENCRYPTION_KEY
        });
        
        this.usageTracker = new UsageTracker({
            billingCycle: 'monthly'
        });
        
        this.backupService = new BackupService({
            backupDir: process.env.BACKUP_DIR || '/tmp/dev-sandbox-backups',
            maxBackups: 50
        });
        
        console.log('✅ All services initialized');
    }

    setupMiddleware() {
        // Security middleware
        this.app.use(helmet());
        this.app.use(cors({
            origin: process.env.ALLOWED_ORIGINS ? process.env.ALLOWED_ORIGINS.split(',') : '*',
            credentials: true
        }));
        
        // Rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 1000, // limit each IP to 1000 requests per windowMs
            message: 'Too many requests from this IP'
        });
        this.app.use('/api/', limiter);
        
        // Body parsing
        this.app.use(express.json({ limit: '10mb' }));
        this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));
        
        // Request logging
        this.app.use((req, res, next) => {
            console.log(`${new Date().toISOString()} ${req.method} ${req.url}`);
            next();
        });
        
        // User session middleware
        this.app.use(this.authMiddleware.bind(this));
    }

    authMiddleware(req, res, next) {
        // Simple auth middleware - in production, use proper JWT or session management
        const userId = req.headers['x-user-id'] || req.query.userId || 'demo-user';
        const userTier = req.headers['x-user-tier'] || req.query.userTier || 'free';
        
        req.user = { id: userId, tier: userTier };
        next();
    }

    setupRoutes() {
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({ 
                status: 'healthy', 
                timestamp: new Date(),
                services: {
                    container: !!this.containerManager,
                    claude: !!this.claudeCodeService,
                    environment: !!this.environmentManager,
                    execution: !!this.codeExecutionService,
                    liveEditing: !!this.liveEditingService,
                    deployment: !!this.deploymentService,
                    collaboration: !!this.collaborationService,
                    vault: !!this.apiKeyVault,
                    usage: !!this.usageTracker,
                    backup: !!this.backupService
                }
            });
        });

        // Container management routes
        this.app.post('/api/containers/create', this.handleCreateContainer.bind(this));
        this.app.get('/api/containers', this.handleListContainers.bind(this));
        this.app.delete('/api/containers/:containerId', this.handleDeleteContainer.bind(this));

        // Environment management routes
        this.app.post('/api/environments/create', this.handleCreateEnvironment.bind(this));
        this.app.get('/api/environments', this.handleListEnvironments.bind(this));
        this.app.put('/api/environments/:envId', this.handleUpdateEnvironment.bind(this));

        // Code execution routes
        this.app.post('/api/execute', this.handleExecuteCode.bind(this));
        this.app.get('/api/execute/:executionId/status', this.handleGetExecutionStatus.bind(this));

        // Claude Code API routes
        this.app.post('/api/claude/generate', this.handleClaudeGenerate.bind(this));
        this.app.post('/api/claude/review', this.handleClaudeReview.bind(this));
        this.app.post('/api/claude/debug', this.handleClaudeDebug.bind(this));

        // Deployment routes
        this.app.post('/api/deployments/create', this.handleCreateDeployment.bind(this));
        this.app.get('/api/deployments', this.handleListDeployments.bind(this));
        this.app.post('/api/deployments/:deploymentId/rollback', this.handleRollbackDeployment.bind(this));

        // API Key vault routes
        this.app.post('/api/vault/keys', this.handleStoreAPIKey.bind(this));
        this.app.get('/api/vault/keys', this.handleListAPIKeys.bind(this));
        this.app.get('/api/vault/keys/:keyId', this.handleGetAPIKey.bind(this));
        this.app.put('/api/vault/keys/:keyId', this.handleUpdateAPIKey.bind(this));
        this.app.delete('/api/vault/keys/:keyId', this.handleDeleteAPIKey.bind(this));

        // Usage tracking routes
        this.app.get('/api/usage', this.handleGetUsage.bind(this));
        this.app.get('/api/usage/analytics', this.handleGetUsageAnalytics.bind(this));
        this.app.post('/api/invoices/generate', this.handleGenerateInvoice.bind(this));

        // Backup routes
        this.app.post('/api/backups/create', this.handleCreateBackup.bind(this));
        this.app.get('/api/backups', this.handleListBackups.bind(this));
        this.app.post('/api/backups/:backupId/restore', this.handleRestoreBackup.bind(this));
        this.app.delete('/api/backups/:backupId', this.handleDeleteBackup.bind(this));

        // Collaboration routes
        this.app.post('/api/collaboration/rooms', this.handleCreateRoom.bind(this));
        this.app.get('/api/collaboration/rooms', this.handleListRooms.bind(this));
        this.app.post('/api/collaboration/rooms/:roomId/join', this.handleJoinRoom.bind(this));
    }

    setupWebSocketHandlers() {
        this.wss.on('connection', (ws, req) => {
            const userId = req.url.split('userId=')[1]?.split('&')[0] || 'anonymous';
            
            console.log(`📡 WebSocket connection established for user: ${userId}`);
            
            this.connectedUsers.set(userId, ws);
            
            // Setup message handlers
            ws.on('message', async (message) => {
                try {
                    const data = JSON.parse(message);
                    await this.handleWebSocketMessage(ws, userId, data);
                } catch (error) {
                    console.error('WebSocket message error:', error);
                    ws.send(JSON.stringify({ error: error.message }));
                }
            });

            ws.on('close', () => {
                console.log(`📡 WebSocket disconnected for user: ${userId}`);
                this.connectedUsers.delete(userId);
            });

            // Send welcome message
            ws.send(JSON.stringify({ 
                type: 'connected', 
                userId, 
                timestamp: new Date() 
            }));
        });
    }

    async handleWebSocketMessage(ws, userId, data) {
        switch (data.type) {
            case 'collaboration':
                await this.handleCollaborationMessage(ws, userId, data);
                break;
            case 'live-editing':
                await this.handleLiveEditingMessage(ws, userId, data);
                break;
            case 'execution-status':
                // Handle real-time execution updates
                break;
            default:
                ws.send(JSON.stringify({ error: 'Unknown message type' }));
        }
    }

    async handleCollaborationMessage(ws, userId, data) {
        // Delegate to collaboration service
        if (this.collaborationService) {
            // Handle collaboration events through WebSocket
            const result = await this.collaborationService.handleMessage(userId, data);
            
            // Broadcast to room participants
            if (data.roomId) {
                const room = this.collaborationService.getRoom(data.roomId);
                if (room) {
                    room.participants.forEach(participantId => {
                        const participantWs = this.connectedUsers.get(participantId);
                        if (participantWs && participantWs !== ws) {
                            participantWs.send(JSON.stringify(result));
                        }
                    });
                }
            }
        }
    }

    async handleLiveEditingMessage(ws, userId, data) {
        if (this.liveEditingService) {
            const result = await this.liveEditingService.handleWebSocketMessage(userId, data);
            ws.send(JSON.stringify(result));
        }
    }

    setupEventHandlers() {
        // Setup event handlers for all services
        this.usageTracker.on('usage-recorded', (data) => {
            this.broadcastToUser(data.userId, { type: 'usage-update', data });
        });

        this.deploymentService.on('deployment-completed', (data) => {
            this.broadcastToUser(data.userId, { type: 'deployment-update', data });
        });

        this.backupService.on('backup-created', (data) => {
            this.broadcastToUser(data.userId, { type: 'backup-created', data });
        });

        this.collaborationService.on('document-updated', (data) => {
            // Broadcast document updates to all participants
            if (data.roomId) {
                this.broadcastToRoom(data.roomId, { type: 'document-update', data });
            }
        });
    }

    broadcastToUser(userId, message) {
        const ws = this.connectedUsers.get(userId);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        }
    }

    broadcastToRoom(roomId, message) {
        const room = this.collaborationService.getRoom(roomId);
        if (room) {
            room.participants.forEach(userId => {
                this.broadcastToUser(userId, message);
            });
        }
    }

    // Route handlers
    async handleCreateContainer(req, res) {
        try {
            const { options } = req.body;
            const result = await this.containerManager.createUserContainer(
                req.user.id, 
                req.user.tier, 
                options
            );
            
            // Track usage
            this.usageTracker.startUsageTracking(
                req.user.id, 
                req.user.tier, 
                'cpu', 
                result.containerId
            );
            
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleListContainers(req, res) {
        try {
            const containers = await this.containerManager.listUserContainers(req.user.id);
            res.json(containers);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleDeleteContainer(req, res) {
        try {
            const { containerId } = req.params;
            await this.containerManager.stopUserContainer(req.user.id, containerId);
            res.json({ success: true });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleCreateEnvironment(req, res) {
        try {
            const { name, template, config } = req.body;
            const result = await this.environmentManager.createEnvironment(
                req.user.id,
                name,
                template,
                config
            );
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleListEnvironments(req, res) {
        try {
            const environments = await this.environmentManager.listUserEnvironments(req.user.id);
            res.json(environments);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleUpdateEnvironment(req, res) {
        try {
            const { envId } = req.params;
            const { updates } = req.body;
            
            // Create backup before update
            await this.backupService.createBackupBeforeChange(
                req.user.id,
                `/environments/${envId}`,
                'Environment update'
            );
            
            const result = await this.environmentManager.updateEnvironment(
                req.user.id,
                envId,
                updates
            );
            
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleExecuteCode(req, res) {
        try {
            const { code, language, environment, options } = req.body;
            
            // Check limits
            const limits = this.usageTracker.checkUserLimits(req.user.id, req.user.tier, 'apiCalls');
            if (!limits.withinLimits) {
                return res.status(429).json({ error: 'API call limit exceeded' });
            }
            
            const trackingId = this.usageTracker.startUsageTracking(
                req.user.id,
                req.user.tier,
                'api',
                'code-execution'
            );
            
            const result = await this.codeExecutionService.executeCode(
                req.user.id,
                req.user.tier,
                { code, language, environment, ...options }
            );
            
            this.usageTracker.stopUsageTracking(trackingId);
            
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleGetExecutionStatus(req, res) {
        try {
            const { executionId } = req.params;
            const status = this.codeExecutionService.getExecutionStatus(executionId);
            res.json(status);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleClaudeGenerate(req, res) {
        try {
            const { request } = req.body;
            
            const limits = this.usageTracker.checkUserLimits(req.user.id, req.user.tier, 'apiCalls');
            if (!limits.withinLimits) {
                return res.status(429).json({ error: 'API call limit exceeded' });
            }
            
            const trackingId = this.usageTracker.startUsageTracking(
                req.user.id,
                req.user.tier,
                'api',
                'claude-generate'
            );
            
            const result = await this.claudeCodeService.generateCode(
                req.user.id,
                req.user.tier,
                request
            );
            
            this.usageTracker.stopUsageTracking(trackingId);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleClaudeReview(req, res) {
        try {
            const { code, options } = req.body;
            
            const trackingId = this.usageTracker.startUsageTracking(
                req.user.id,
                req.user.tier,
                'api',
                'claude-review'
            );
            
            const result = await this.claudeCodeService.reviewCode(
                req.user.id,
                req.user.tier,
                code,
                options
            );
            
            this.usageTracker.stopUsageTracking(trackingId);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleClaudeDebug(req, res) {
        try {
            const { code, error, context } = req.body;
            
            const trackingId = this.usageTracker.startUsageTracking(
                req.user.id,
                req.user.tier,
                'api',
                'claude-debug'
            );
            
            const result = await this.claudeCodeService.debugCode(
                req.user.id,
                req.user.tier,
                code,
                error,
                context
            );
            
            this.usageTracker.stopUsageTracking(trackingId);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleCreateDeployment(req, res) {
        try {
            const { deploymentConfig } = req.body;
            
            // Create backup before deployment
            if (deploymentConfig.projectPath) {
                await this.backupService.createBackupBeforeChange(
                    req.user.id,
                    deploymentConfig.projectPath,
                    `Deployment: ${deploymentConfig.name || 'unnamed'}`
                );
            }
            
            const trackingId = this.usageTracker.startUsageTracking(
                req.user.id,
                req.user.tier,
                'deployment',
                deploymentConfig.name || 'unnamed'
            );
            
            const result = await this.deploymentService.createDeployment(
                req.user.id,
                req.user.tier,
                deploymentConfig
            );
            
            this.usageTracker.stopUsageTracking(trackingId);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleListDeployments(req, res) {
        try {
            const deployments = await this.deploymentService.getUserDeployments(req.user.id);
            res.json(deployments);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleRollbackDeployment(req, res) {
        try {
            const { deploymentId } = req.params;
            const { targetVersion } = req.body;
            
            const result = await this.deploymentService.rollbackDeployment(
                req.user.id,
                deploymentId,
                targetVersion
            );
            
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleStoreAPIKey(req, res) {
        try {
            const { keyConfig } = req.body;
            const result = await this.apiKeyVault.storeAPIKey(
                req.user.id,
                req.user.tier,
                keyConfig
            );
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleListAPIKeys(req, res) {
        try {
            const keys = this.apiKeyVault.getUserKeys(req.user.id);
            res.json(keys);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleGetAPIKey(req, res) {
        try {
            const { keyId } = req.params;
            const key = await this.apiKeyVault.retrieveAPIKey(
                req.user.id,
                keyId,
                { operation: 'read' }
            );
            res.json(key);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleUpdateAPIKey(req, res) {
        try {
            const { keyId } = req.params;
            const { updates } = req.body;
            const result = await this.apiKeyVault.updateAPIKey(
                req.user.id,
                keyId,
                updates
            );
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleDeleteAPIKey(req, res) {
        try {
            const { keyId } = req.params;
            const result = await this.apiKeyVault.deleteAPIKey(req.user.id, keyId);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleGetUsage(req, res) {
        try {
            const { period } = req.query;
            const usage = this.usageTracker.getUserUsage(req.user.id, period);
            res.json(usage);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleGetUsageAnalytics(req, res) {
        try {
            const analytics = this.usageTracker.getUsageAnalytics(req.user.id);
            res.json(analytics);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleGenerateInvoice(req, res) {
        try {
            const { period } = req.body;
            const invoice = await this.usageTracker.generateInvoice(req.user.id, period);
            res.json(invoice);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleCreateBackup(req, res) {
        try {
            const { projectPath, changeDescription, options } = req.body;
            const result = await this.backupService.createBackupBeforeChange(
                req.user.id,
                projectPath,
                changeDescription,
                options
            );
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleListBackups(req, res) {
        try {
            const { projectPath } = req.query;
            const backups = this.backupService.getUserBackups(req.user.id, projectPath);
            res.json(backups);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleRestoreBackup(req, res) {
        try {
            const { backupId } = req.params;
            const { restorePath, options } = req.body;
            const result = await this.backupService.restoreFromBackup(
                req.user.id,
                backupId,
                restorePath,
                options
            );
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleDeleteBackup(req, res) {
        try {
            const { backupId } = req.params;
            const result = await this.backupService.deleteBackup(req.user.id, backupId);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleCreateRoom(req, res) {
        try {
            const { name, projectPath, permissions } = req.body;
            const result = await this.collaborationService.createRoom(
                req.user.id,
                name,
                projectPath,
                permissions
            );
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleListRooms(req, res) {
        try {
            const rooms = this.collaborationService.getUserRooms(req.user.id);
            res.json(rooms);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async handleJoinRoom(req, res) {
        try {
            const { roomId } = req.params;
            const result = await this.collaborationService.joinRoom(req.user.id, roomId);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }

    async start() {
        await this.initialize();
        
        return new Promise((resolve) => {
            this.server.listen(this.port, () => {
                console.log(`🚀 Developer Sandbox Server running on port ${this.port}`);
                console.log(`📊 Health check: http://localhost:${this.port}/health`);
                console.log(`🔗 WebSocket endpoint: ws://localhost:${this.port}`);
                console.log(`📚 API documentation: http://localhost:${this.port}/api`);
                resolve();
            });
        });
    }

    async stop() {
        console.log('🛑 Shutting down Developer Sandbox Server...');
        
        // Close WebSocket connections
        this.wss.clients.forEach(ws => ws.close());
        
        // Shutdown services
        if (this.usageTracker) this.usageTracker.shutdown();
        if (this.backupService) this.backupService.shutdown();
        if (this.deploymentService) this.deploymentService.shutdown();
        if (this.containerManager) await this.containerManager.cleanup();
        if (this.apiKeyVault) this.apiKeyVault.shutdown();
        
        return new Promise((resolve) => {
            this.server.close(() => {
                console.log('✅ Server shutdown complete');
                resolve();
            });
        });
    }
}

// Handle graceful shutdown
process.on('SIGTERM', async () => {
    console.log('Received SIGTERM signal');
    if (global.server) {
        await global.server.stop();
    }
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('Received SIGINT signal');
    if (global.server) {
        await global.server.stop();
    }
    process.exit(0);
});

// Start server if this file is run directly
if (require.main === module) {
    const server = new DevSandboxServer();
    global.server = server;
    
    server.start().catch(error => {
        console.error('Failed to start server:', error);
        process.exit(1);
    });
}

module.exports = DevSandboxServer;