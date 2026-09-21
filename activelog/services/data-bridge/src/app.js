const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const WebSocket = require('ws');
const http = require('http');

// Import all services
const UnifiedSchema = require('./schemas/UnifiedSchema');
const DataSync = require('./services/DataSync');
const ConflictResolver = require('./services/ConflictResolver');
const DataTransformer = require('./adapters/DataTransformer');
const PrivacyManager = require('./services/PrivacyManager');
const SearchIndex = require('./services/SearchIndex');
const LineageTracker = require('./services/LineageTracker');
const ChangeDataCapture = require('./services/ChangeDataCapture');
const EventSourcing = require('./services/EventSourcing');
const DataMigrator = require('./services/DataMigrator');

class DataBridge {
    constructor(options = {}) {
        this.port = options.port || 8202;
        this.env = options.env || 'development';
        
        // Initialize Express app
        this.app = express();
        this.server = http.createServer(this.app);
        
        // Initialize services
        this.initializeServices();
        this.setupMiddleware();
        this.setupRoutes();
        this.setupWebSocket();
        this.setupEventListeners();
        
        console.log('Data Bridge initialized');
    }

    initializeServices() {
        // Initialize all data bridge services
        this.unifiedSchema = new UnifiedSchema();
        this.dataSync = new DataSync({
            conflictResolver: this.conflictResolver
        });
        this.conflictResolver = new ConflictResolver();
        this.dataTransformer = new DataTransformer();
        this.privacyManager = new PrivacyManager();
        this.searchIndex = new SearchIndex();
        this.lineageTracker = new LineageTracker();
        this.changeDataCapture = new ChangeDataCapture();
        this.eventSourcing = new EventSourcing();
        this.dataMigrator = new DataMigrator();

        console.log('All services initialized');
    }

    setupMiddleware() {
        // Security middleware
        this.app.use(helmet());
        this.app.use(cors({
            origin: process.env.CORS_ORIGIN || '*',
            credentials: true
        }));

        // Compression middleware
        this.app.use(compression());

        // Rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 100, // Limit each IP to 100 requests per windowMs
            message: 'Too many requests from this IP'
        });
        this.app.use('/api/', limiter);

        // Body parsing middleware
        this.app.use(express.json({ limit: '10mb' }));
        this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

        // Request logging
        this.app.use((req, res, next) => {
            console.log(`${req.method} ${req.path} - ${new Date().toISOString()}`);
            next();
        });
    }

    setupRoutes() {
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                version: '1.0.0',
                services: {
                    unifiedSchema: this.unifiedSchema.getStats(),
                    dataSync: this.dataSync.getStats(),
                    conflictResolver: this.conflictResolver.getStats(),
                    dataTransformer: this.dataTransformer.getStats(),
                    privacyManager: this.privacyManager.getStats(),
                    searchIndex: this.searchIndex.getStats(),
                    lineageTracker: this.lineageTracker.getStats(),
                    changeDataCapture: this.changeDataCapture.getStats(),
                    eventSourcing: this.eventSourcing.getStats(),
                    dataMigrator: this.dataMigrator.getStats()
                }
            });
        });

        // Unified Schema Routes
        this.setupSchemaRoutes();
        
        // Data Sync Routes
        this.setupSyncRoutes();
        
        // Conflict Resolution Routes
        this.setupConflictRoutes();
        
        // Data Transformation Routes
        this.setupTransformationRoutes();
        
        // Privacy Management Routes
        this.setupPrivacyRoutes();
        
        // Search Index Routes
        this.setupSearchRoutes();
        
        // Lineage Tracking Routes
        this.setupLineageRoutes();
        
        // Change Data Capture Routes
        this.setupCDCRoutes();
        
        // Event Sourcing Routes
        this.setupEventSourcingRoutes();
        
        // Data Migration Routes
        this.setupMigrationRoutes();

        // Error handling middleware
        this.app.use((error, req, res, next) => {
            console.error('Error:', error);
            res.status(500).json({
                error: 'Internal Server Error',
                message: error.message,
                timestamp: new Date().toISOString()
            });
        });

        // 404 handler
        this.app.use('*', (req, res) => {
            res.status(404).json({
                error: 'Not Found',
                message: `Route ${req.originalUrl} not found`,
                timestamp: new Date().toISOString()
            });
        });
    }

    setupSchemaRoutes() {
        const router = express.Router();

        // Get all schemas
        router.get('/', (req, res) => {
            res.json(this.unifiedSchema.getAllSchemas());
        });

        // Get specific schema
        router.get('/:entityType', (req, res) => {
            const schema = this.unifiedSchema.getSchema(req.params.entityType);
            if (schema) {
                res.json(schema);
            } else {
                res.status(404).json({ error: 'Schema not found' });
            }
        });

        // Validate entity
        router.post('/validate', (req, res) => {
            try {
                const { entityType, data, options } = req.body;
                const result = this.unifiedSchema.validateEntity(entityType, data, options);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Transform entity between types
        router.post('/transform', (req, res) => {
            try {
                const { data, fromType, toType, options } = req.body;
                const result = this.unifiedSchema.transformEntity(data, fromType, toType, options);
                res.json({ success: true, data: result });
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        this.app.use('/api/schema', router);
    }

    setupSyncRoutes() {
        const router = express.Router();

        // Register service
        router.post('/services', (req, res) => {
            try {
                const { serviceName, config } = req.body;
                const result = this.dataSync.registerService(serviceName, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Create sync rule
        router.post('/rules', (req, res) => {
            try {
                const { ruleId, config } = req.body;
                const result = this.dataSync.createSyncRule(ruleId, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Sync entity
        router.post('/sync', async (req, res) => {
            try {
                const { entityType, entityId, sourceService, options } = req.body;
                const result = await this.dataSync.syncEntity(entityType, entityId, sourceService, options);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Batch sync
        router.post('/batch-sync', async (req, res) => {
            try {
                const { entityType, serviceFrom, serviceTo, options } = req.body;
                const result = await this.dataSync.batchSync(entityType, serviceFrom, serviceTo, options);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get sync history
        router.get('/history', (req, res) => {
            const limit = parseInt(req.query.limit) || 100;
            const history = this.dataSync.getSyncHistory(limit);
            res.json(history);
        });

        this.app.use('/api/sync', router);
    }

    setupConflictRoutes() {
        const router = express.Router();

        // Resolve conflict
        router.post('/resolve', async (req, res) => {
            try {
                const { conflict, strategyName } = req.body;
                const result = await this.conflictResolver.resolveConflict(conflict, strategyName);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Define resolution rule
        router.post('/rules', (req, res) => {
            try {
                const { ruleId, config } = req.body;
                const result = this.conflictResolver.defineRule(ruleId, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get conflict history
        router.get('/history', (req, res) => {
            const limit = parseInt(req.query.limit) || 100;
            const history = this.conflictResolver.getConflictHistory(limit);
            res.json(history);
        });

        this.app.use('/api/conflicts', router);
    }

    setupTransformationRoutes() {
        const router = express.Router();

        // Transform data
        router.post('/transform', async (req, res) => {
            try {
                const { data, sourceFormat, targetFormat, options } = req.body;
                const result = await this.dataTransformer.transform(data, sourceFormat, targetFormat, options);
                res.json({ success: true, data: result });
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // List adapters
        router.get('/adapters', (req, res) => {
            const adapters = this.dataTransformer.listAdapters();
            res.json(adapters);
        });

        // Get adapter info
        router.get('/adapters/:adapterId', (req, res) => {
            const adapter = this.dataTransformer.getAdapterInfo(req.params.adapterId);
            if (adapter) {
                res.json(adapter);
            } else {
                res.status(404).json({ error: 'Adapter not found' });
            }
        });

        this.app.use('/api/transform', router);
    }

    setupPrivacyRoutes() {
        const router = express.Router();

        // Process data sharing
        router.post('/share', async (req, res) => {
            try {
                const { data, sourceApp, targetApp, options } = req.body;
                const result = await this.privacyManager.processDataSharing(data, sourceApp, targetApp, options);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Create privacy policy
        router.post('/policies', (req, res) => {
            try {
                const { policyId, config } = req.body;
                const result = this.privacyManager.createPrivacyPolicy(policyId, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Record consent
        router.post('/consent', (req, res) => {
            try {
                const { userId, dataType, purposes, options } = req.body;
                const result = this.privacyManager.recordConsent(userId, dataType, purposes, options);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get privacy report
        router.get('/report', (req, res) => {
            const report = this.privacyManager.getPrivacyReport();
            res.json(report);
        });

        this.app.use('/api/privacy', router);
    }

    setupSearchRoutes() {
        const router = express.Router();

        // Create index
        router.post('/indices', async (req, res) => {
            try {
                const { indexName, mapping, settings } = req.body;
                const result = await this.searchIndex.createIndex(indexName, mapping, settings);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Index document
        router.post('/indices/:indexName/documents', async (req, res) => {
            try {
                const { document, options } = req.body;
                const result = await this.searchIndex.indexDocument(req.params.indexName, document, options);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Search
        router.post('/search', async (req, res) => {
            try {
                const { query, options } = req.body;
                const result = await this.searchIndex.search(query, options);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get search analytics
        router.get('/analytics', (req, res) => {
            const options = {
                since: req.query.since
            };
            const analytics = this.searchIndex.getSearchAnalytics(options);
            res.json(analytics);
        });

        this.app.use('/api/search', router);
    }

    setupLineageRoutes() {
        const router = express.Router();

        // Track entity creation
        router.post('/entities', (req, res) => {
            try {
                const { entityId, entityInfo } = req.body;
                const result = this.lineageTracker.trackEntityCreation(entityId, entityInfo);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Track transformation
        router.post('/transformations', (req, res) => {
            try {
                const { sourceEntityId, targetEntityId, transformationInfo } = req.body;
                const result = this.lineageTracker.trackDataTransformation(sourceEntityId, targetEntityId, transformationInfo);
                res.json({ transformationId: result });
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get lineage
        router.get('/entities/:entityId', (req, res) => {
            try {
                const options = {
                    direction: req.query.direction,
                    maxDepth: parseInt(req.query.maxDepth),
                    includeTransformations: req.query.includeTransformations !== 'false'
                };
                const result = this.lineageTracker.getLineage(req.params.entityId, options);
                if (result) {
                    res.json(result);
                } else {
                    res.status(404).json({ error: 'Entity not found in lineage' });
                }
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Perform impact analysis
        router.post('/impact-analysis', async (req, res) => {
            try {
                const { entityId, changeType } = req.body;
                const result = await this.lineageTracker.performImpactAnalysis(entityId, changeType);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        this.app.use('/api/lineage', router);
    }

    setupCDCRoutes() {
        const router = express.Router();

        // Create watcher
        router.post('/watchers', (req, res) => {
            try {
                const { watcherId, config } = req.body;
                const result = this.changeDataCapture.createWatcher(watcherId, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Start watcher
        router.post('/watchers/:watcherId/start', (req, res) => {
            try {
                const result = this.changeDataCapture.startWatcher(req.params.watcherId);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Stop watcher
        router.post('/watchers/:watcherId/stop', (req, res) => {
            try {
                const result = this.changeDataCapture.stopWatcher(req.params.watcherId);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Subscribe to changes
        router.post('/subscriptions', (req, res) => {
            try {
                const { subscriberId, config } = req.body;
                const result = this.changeDataCapture.subscribe(subscriberId, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get changes
        router.get('/changes', (req, res) => {
            const options = {
                watcherId: req.query.watcherId,
                changeTypes: req.query.changeTypes?.split(','),
                since: req.query.since,
                until: req.query.until,
                limit: parseInt(req.query.limit)
            };
            const changes = this.changeDataCapture.getChanges(options);
            res.json(changes);
        });

        this.app.use('/api/cdc', router);
    }

    setupEventSourcingRoutes() {
        const router = express.Router();

        // Append events
        router.post('/streams/:streamId/events', async (req, res) => {
            try {
                const { events, expectedVersion } = req.body;
                const result = await this.eventSourcing.appendEvents(
                    req.params.streamId,
                    events,
                    expectedVersion
                );
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get events
        router.get('/streams/:streamId/events', async (req, res) => {
            try {
                const fromEventNumber = parseInt(req.query.from) || 0;
                const maxCount = parseInt(req.query.limit) || null;
                const result = await this.eventSourcing.getEvents(
                    req.params.streamId,
                    fromEventNumber,
                    maxCount
                );
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Handle command
        router.post('/commands', async (req, res) => {
            try {
                const command = req.body;
                const result = await this.eventSourcing.handleCommand(command);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Create projection
        router.post('/projections', (req, res) => {
            try {
                const { projectionId, config } = req.body;
                const result = this.eventSourcing.createProjection(projectionId, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get projection state
        router.get('/projections/:projectionId', (req, res) => {
            const result = this.eventSourcing.getProjectionState(req.params.projectionId);
            if (result) {
                res.json(result);
            } else {
                res.status(404).json({ error: 'Projection not found' });
            }
        });

        this.app.use('/api/events', router);
    }

    setupMigrationRoutes() {
        const router = express.Router();

        // Register data source
        router.post('/sources', (req, res) => {
            try {
                const { sourceId, config } = req.body;
                const result = this.dataMigrator.registerDataSource(sourceId, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Create migration
        router.post('/migrations', (req, res) => {
            try {
                const { migrationId, config } = req.body;
                const result = this.dataMigrator.createMigration(migrationId, config);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Execute migration
        router.post('/migrations/:migrationId/execute', async (req, res) => {
            try {
                const options = req.body || {};
                const result = await this.dataMigrator.executeMigration(req.params.migrationId, options);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // Get migration status
        router.get('/migrations/:migrationId/status', (req, res) => {
            const result = this.dataMigrator.getMigrationStatus(req.params.migrationId);
            if (result) {
                res.json(result);
            } else {
                res.status(404).json({ error: 'Migration not found' });
            }
        });

        // Get migration progress
        router.get('/migrations/:migrationId/progress', (req, res) => {
            const result = this.dataMigrator.getMigrationProgress(req.params.migrationId);
            if (result) {
                res.json(result);
            } else {
                res.status(404).json({ error: 'Migration not running or not found' });
            }
        });

        this.app.use('/api/migrate', router);
    }

    setupWebSocket() {
        this.wss = new WebSocket.Server({ server: this.server });

        this.wss.on('connection', (ws, req) => {
            console.log(`WebSocket client connected: ${req.connection.remoteAddress}`);
            
            ws.on('message', (message) => {
                try {
                    const data = JSON.parse(message);
                    this.handleWebSocketMessage(ws, data);
                } catch (error) {
                    ws.send(JSON.stringify({
                        type: 'error',
                        message: 'Invalid JSON message'
                    }));
                }
            });

            ws.on('close', () => {
                console.log('WebSocket client disconnected');
            });

            // Send welcome message
            ws.send(JSON.stringify({
                type: 'welcome',
                message: 'Connected to Data Bridge WebSocket',
                timestamp: new Date().toISOString()
            }));
        });
    }

    handleWebSocketMessage(ws, data) {
        switch (data.type) {
            case 'subscribe':
                // Subscribe to real-time updates
                this.subscribeToUpdates(ws, data.topics || []);
                break;
            case 'unsubscribe':
                // Unsubscribe from updates
                this.unsubscribeFromUpdates(ws, data.topics || []);
                break;
            case 'ping':
                ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
                break;
            default:
                ws.send(JSON.stringify({
                    type: 'error',
                    message: `Unknown message type: ${data.type}`
                }));
        }
    }

    subscribeToUpdates(ws, topics) {
        if (!ws.subscriptions) {
            ws.subscriptions = new Set();
        }
        
        topics.forEach(topic => ws.subscriptions.add(topic));
        
        ws.send(JSON.stringify({
            type: 'subscribed',
            topics,
            timestamp: new Date().toISOString()
        }));
    }

    unsubscribeFromUpdates(ws, topics) {
        if (ws.subscriptions) {
            topics.forEach(topic => ws.subscriptions.delete(topic));
        }
        
        ws.send(JSON.stringify({
            type: 'unsubscribed',
            topics,
            timestamp: new Date().toISOString()
        }));
    }

    broadcastToSubscribers(topic, data) {
        this.wss.clients.forEach(ws => {
            if (ws.readyState === WebSocket.OPEN && 
                ws.subscriptions && 
                ws.subscriptions.has(topic)) {
                ws.send(JSON.stringify({
                    type: 'update',
                    topic,
                    data,
                    timestamp: new Date().toISOString()
                }));
            }
        });
    }

    setupEventListeners() {
        // Data Sync Events
        this.dataSync.on('sync:completed', (info) => {
            this.broadcastToSubscribers('sync', {
                event: 'sync:completed',
                data: info
            });
        });

        // Conflict Resolution Events
        this.conflictResolver.on('conflict:resolved', (info) => {
            this.broadcastToSubscribers('conflicts', {
                event: 'conflict:resolved',
                data: info
            });
        });

        // Privacy Management Events
        this.privacyManager.on('sharing:completed', (info) => {
            this.broadcastToSubscribers('privacy', {
                event: 'sharing:completed',
                data: info
            });
        });

        // Search Index Events
        this.searchIndex.on('document:indexed', (info) => {
            this.broadcastToSubscribers('search', {
                event: 'document:indexed',
                data: info
            });
        });

        // Lineage Tracking Events
        this.lineageTracker.on('entity:created', (info) => {
            this.broadcastToSubscribers('lineage', {
                event: 'entity:created',
                data: info
            });
        });

        // Change Data Capture Events
        this.changeDataCapture.on('changes:processed', (info) => {
            this.broadcastToSubscribers('cdc', {
                event: 'changes:processed',
                data: info
            });
        });

        // Event Sourcing Events
        this.eventSourcing.on('events:appended', (info) => {
            this.broadcastToSubscribers('events', {
                event: 'events:appended',
                data: info
            });
        });

        // Data Migration Events
        this.dataMigrator.on('migration:completed', (info) => {
            this.broadcastToSubscribers('migrations', {
                event: 'migration:completed',
                data: info
            });
        });
    }

    start() {
        return new Promise((resolve, reject) => {
            this.server.listen(this.port, (error) => {
                if (error) {
                    console.error('Failed to start Data Bridge server:', error);
                    reject(error);
                } else {
                    console.log(`🚀 Data Bridge server running on port ${this.port}`);
                    console.log(`📊 Health check available at: http://localhost:${this.port}/health`);
                    console.log(`🔌 WebSocket available at: ws://localhost:${this.port}`);
                    resolve();
                }
            });
        });
    }

    stop() {
        return new Promise((resolve) => {
            this.server.close(() => {
                console.log('Data Bridge server stopped');
                resolve();
            });
        });
    }

    getServiceStats() {
        return {
            uptime: process.uptime(),
            memory: process.memoryUsage(),
            activeConnections: this.wss.clients.size,
            services: {
                unifiedSchema: this.unifiedSchema.getStats(),
                dataSync: this.dataSync.getStats(),
                conflictResolver: this.conflictResolver.getStats(),
                dataTransformer: this.dataTransformer.getStats(),
                privacyManager: this.privacyManager.getStats(),
                searchIndex: this.searchIndex.getStats(),
                lineageTracker: this.lineageTracker.getStats(),
                changeDataCapture: this.changeDataCapture.getStats(),
                eventSourcing: this.eventSourcing.getStats(),
                dataMigrator: this.dataMigrator.getStats()
            }
        };
    }
}

// Start the server if this file is run directly
if (require.main === module) {
    const dataBridge = new DataBridge({
        port: process.env.PORT || 8202,
        env: process.env.NODE_ENV || 'development'
    });

    dataBridge.start().catch(error => {
        console.error('Failed to start Data Bridge:', error);
        process.exit(1);
    });

    // Graceful shutdown
    process.on('SIGINT', async () => {
        console.log('Received SIGINT, shutting down gracefully...');
        await dataBridge.stop();
        process.exit(0);
    });

    process.on('SIGTERM', async () => {
        console.log('Received SIGTERM, shutting down gracefully...');
        await dataBridge.stop();
        process.exit(0);
    });
}

module.exports = DataBridge;