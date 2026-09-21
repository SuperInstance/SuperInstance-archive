require('dotenv').config();

const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');

const logger = require('./config/logger');
const database = require('./config/database');
const redis = require('./config/redis');

// Import services
const realTimeInventoryService = require('./services/realTimeInventoryService');
const multiLocationService = require('./services/multiLocationService');

// Import routes
const inventoryRoutes = require('./controllers/inventoryController');
const locationRoutes = require('./controllers/locationController');
const reservationRoutes = require('./controllers/reservationController');

// Import middleware
const { errorHandler } = require('./middleware/errorHandler');

class InventorySyncService {
  constructor() {
    this.app = express();
    this.server = http.createServer(this.app);
    this.io = socketIo(this.server, {
      cors: {
        origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:3001'],
        methods: ['GET', 'POST']
      }
    });
    this.port = process.env.PORT || 8311;
    this.setupMiddleware();
    this.setupRoutes();
    this.setupSocketIO();
    this.setupErrorHandling();
  }

  setupMiddleware() {
    // Security middleware
    this.app.use(helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          scriptSrc: ["'self'"],
          imgSrc: ["'self'", "data:", "https:"],
          connectSrc: ["'self'", "wss:", "ws:"]
        }
      }
    }));

    // CORS configuration  
    this.app.use(cors({
      origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:3001'],
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
    }));

    // Compression
    this.app.use(compression({
      filter: (req, res) => {
        if (req.headers['x-no-compression']) return false;
        return compression.filter(req, res);
      },
      threshold: 1024
    }));

    // Rate limiting
    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: process.env.NODE_ENV === 'production' ? 1000 : 2000,
      message: {
        error: 'Too many requests, please try again later',
        retryAfter: '15 minutes'
      },
      standardHeaders: true,
      legacyHeaders: false
    });
    this.app.use(limiter);

    // Body parsing middleware
    this.app.use(express.json({ 
      limit: '10mb',
      verify: (req, res, buf) => {
        req.rawBody = buf;
      }
    }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Serve static files (QR codes, etc.)
    this.app.use('/qr-codes', express.static(path.join(process.cwd(), 'public', 'qr-codes')));

    // Request logging
    this.app.use((req, res, next) => {
      logger.http(req, res);
      next();
    });

    // Request ID middleware
    this.app.use((req, res, next) => {
      req.id = req.headers['x-request-id'] || require('uuid').v4();
      res.setHeader('X-Request-ID', req.id);
      next();
    });

    // Health check endpoint
    this.app.get('/health', async (req, res) => {
      try {
        const dbHealth = await database.healthCheck();
        const redisHealth = await redis.healthCheck();
        
        const health = {
          status: 'ok',
          timestamp: new Date().toISOString(),
          service: 'inventory-sync',
          version: process.env.npm_package_version || '1.0.0',
          uptime: process.uptime(),
          database: dbHealth,
          redis: redisHealth,
          memory: process.memoryUsage(),
          pid: process.pid,
          features: [
            'real_time_tracking',
            'multi_location_support',
            'reservation_system',
            'pickup_scheduling',
            'qr_code_generation',
            'pos_integration',
            'supply_chain_tracking',
            'reorder_automation',
            'price_optimization'
          ]
        };

        const isHealthy = dbHealth.healthy && redisHealth.healthy;
        res.status(isHealthy ? 200 : 503).json(health);
      } catch (error) {
        logger.error('Health check failed:', error);
        res.status(503).json({
          status: 'error',
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    });

    // API info endpoint
    this.app.get('/', (req, res) => {
      res.json({
        service: 'Inventory Sync Service',
        description: 'Real-time inventory management system with multi-location support and POS integration',
        version: process.env.npm_package_version || '1.0.0',
        features: {
          real_time_tracking: 'Live inventory updates with WebSocket support',
          multi_location_support: 'Manage inventory across multiple locations and warehouses',
          reservation_system: 'Hold inventory for customers with automatic expiration',
          pickup_scheduling: 'Schedule customer pickups with time slot management',
          qr_code_generation: 'Generate QR codes for inventory items and pickups',
          pos_integration: 'Integrate with Square, Stripe, and other POS systems',
          supply_chain_tracking: 'Track suppliers, orders, and deliveries',
          reorder_automation: 'Automatic reordering based on stock levels',
          price_optimization: 'AI-powered dynamic pricing and competitor analysis'
        },
        capabilities: [
          'Real-time stock level monitoring',
          'Multi-location inventory sync',
          'Customer reservation management',
          'QR code generation and scanning',
          'POS system integration',
          'Supply chain visibility',
          'Automated reorder triggers',
          'Dynamic pricing optimization',
          'Pickup scheduling and management',
          'Low stock alerts and notifications'
        ],
        documentation: '/api/docs',
        health: '/health',
        websocket: '/socket.io/',
        timestamp: new Date().toISOString()
      });
    });
  }

  setupRoutes() {
    // API routes
    this.app.use('/api/inventory', inventoryRoutes);
    this.app.use('/api/locations', locationRoutes);
    this.app.use('/api/reservations', reservationRoutes);

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Route not found',
        method: req.method,
        path: req.originalUrl,
        available_endpoints: [
          'GET /api/inventory/status/:locationId/:itemId',
          'POST /api/inventory/update/:locationId/:itemId',
          'GET /api/inventory/multi-location/:itemId',
          'POST /api/locations/nearby',
          'GET /api/locations/:locationId/status',
          'POST /api/reservations/create',
          'GET /api/reservations/:reservationId'
        ],
        timestamp: new Date().toISOString()
      });
    });
  }

  setupSocketIO() {
    // Set Socket.IO instance for real-time services
    realTimeInventoryService.setSocketIO(this.io);

    this.io.on('connection', (socket) => {
      logger.info('New socket connection', { 
        socketId: socket.id,
        remoteAddress: socket.handshake.address
      });

      // Join inventory room for specific location
      socket.on('join_inventory_room', (data) => {
        const { locationId, userId } = data;
        const roomId = `inventory:${locationId}`;
        socket.join(roomId);
        
        logger.logInventoryEvent('inventory_room_joined', locationId, 'socket', {
          roomId,
          userId,
          socketId: socket.id
        });

        socket.emit('room_joined', { roomId, locationId });
      });

      // Join global inventory room
      socket.on('join_global_inventory', (data) => {
        const { userId } = data;
        socket.join('inventory:all');
        
        logger.logInventoryEvent('global_inventory_joined', 'all', 'socket', {
          userId,
          socketId: socket.id
        });

        socket.emit('global_room_joined', { roomId: 'inventory:all' });
      });

      // Handle inventory update requests
      socket.on('request_inventory_update', async (data) => {
        const { locationId, itemId, updateData } = data;
        
        try {
          const update = await realTimeInventoryService.trackInventoryChange(
            locationId, 
            itemId, 
            updateData
          );
          
          socket.emit('inventory_update_success', { update });
        } catch (error) {
          socket.emit('inventory_update_error', { 
            error: error.message,
            locationId,
            itemId 
          });
        }
      });

      // Join alerts room for location
      socket.on('join_alerts_room', (data) => {
        const { locationId, userId } = data;
        const alertsRoom = `alerts:${locationId}`;
        socket.join(alertsRoom);
        
        logger.logInventoryEvent('alerts_room_joined', locationId, 'socket', {
          alertsRoom,
          userId,
          socketId: socket.id
        });

        socket.emit('alerts_room_joined', { roomId: alertsRoom, locationId });
      });

      // Handle POS integration events
      socket.on('pos_transaction', async (data) => {
        const { locationId, transactionData } = data;
        
        try {
          // Process POS transaction and update inventory
          logger.logPOSTransaction(transactionData.transactionId, locationId, transactionData.amount, {
            items: transactionData.items,
            socketId: socket.id
          });
          
          // Update inventory for each item in transaction
          for (const item of transactionData.items || []) {
            await realTimeInventoryService.trackInventoryChange(
              locationId,
              item.itemId,
              {
                changeType: 'sale',
                oldQuantity: item.currentStock,
                newQuantity: item.currentStock - item.quantitySold,
                reason: 'pos_sale',
                userId: transactionData.userId,
                transactionId: transactionData.transactionId,
                metadata: { posSystem: transactionData.posSystem }
              }
            );
          }
          
          socket.emit('pos_transaction_processed', { 
            transactionId: transactionData.transactionId,
            status: 'success' 
          });
        } catch (error) {
          socket.emit('pos_transaction_error', { 
            error: error.message,
            transactionId: transactionData.transactionId 
          });
        }
      });

      // Handle pickup notifications
      socket.on('pickup_update', (data) => {
        const { pickupId, locationId, status, customerId } = data;
        
        // Broadcast to location staff
        socket.to(`location:${locationId}`).emit('pickup_status_update', {
          pickupId,
          status,
          customerId,
          timestamp: new Date().toISOString()
        });
        
        logger.logPickupEvent('pickup_status_update', pickupId, {
          locationId,
          status,
          customerId,
          socketId: socket.id
        });
      });

      socket.on('disconnect', () => {
        logger.info('Socket disconnected', { socketId: socket.id });
      });
    });
  }

  setupErrorHandling() {
    this.app.use(errorHandler);

    // Global error handlers
    process.on('uncaughtException', (error) => {
      console.error('Uncaught Exception:', error);
      this.gracefulShutdown('SIGTERM');
    });

    process.on('unhandledRejection', (reason, promise) => {
      console.error('Unhandled Rejection at:', promise, 'reason:', reason);
      this.gracefulShutdown('SIGTERM');
    });

    process.on('SIGTERM', () => {
      console.log('SIGTERM received, shutting down gracefully');
      this.gracefulShutdown('SIGTERM');
    });

    process.on('SIGINT', () => {
      console.log('SIGINT received, shutting down gracefully');
      this.gracefulShutdown('SIGINT');
    });
  }

  async start() {
    try {
      // Connect to databases
      await database.connect();
      await redis.connect();

      // Start HTTP server with Socket.IO
      this.server.listen(this.port, () => {
        logger.info('Inventory Sync Service started', {
          port: this.port,
          environment: process.env.NODE_ENV || 'development',
          pid: process.pid,
          features: [
            'real_time_inventory_tracking',
            'multi_location_support',
            'reservation_system',
            'pickup_scheduling',
            'qr_code_generation',
            'pos_integration',
            'supply_chain_tracking',
            'reorder_automation',
            'price_optimization'
          ],
          integrations: ['Square', 'Stripe', 'AWS', 'Twilio', 'SendGrid'],
          timestamp: new Date().toISOString()
        });
      });

      // Setup server timeouts
      this.server.timeout = 30000; // 30 seconds
      this.server.keepAliveTimeout = 65000; // 65 seconds
      this.server.headersTimeout = 66000; // 66 seconds

      return this.server;
    } catch (error) {
      logger.error('Failed to start service:', error);
      process.exit(1);
    }
  }

  async gracefulShutdown(signal) {
    logger.info(`${signal} received, starting graceful shutdown...`);

    // Stop accepting new requests
    if (this.server) {
      this.server.close(async () => {
        logger.info('HTTP server closed');

        try {
          // Close Socket.IO connections
          this.io.close();
          
          // Close database connections
          await database.disconnect();
          await redis.disconnect();

          logger.info('All connections closed, exiting process');
          process.exit(0);
        } catch (error) {
          logger.error('Error during graceful shutdown:', error);
          process.exit(1);
        }
      });

      // Force shutdown after timeout
      setTimeout(() => {
        logger.error('Graceful shutdown timeout, forcing exit');
        process.exit(1);
      }, 30000);
    } else {
      process.exit(0);
    }
  }
}

// Start the service if this file is run directly
if (require.main === module) {
  const service = new InventorySyncService();
  service.start().catch((error) => {
    logger.error('Service startup failed:', error);
    process.exit(1);
  });
}

module.exports = InventorySyncService;