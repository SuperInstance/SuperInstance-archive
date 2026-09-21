/**
 * Vendor Ecosystem Platform Server
 * Comprehensive vendor marketplace with real-time sync and intelligent matching
 */

import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import winston from 'winston';
import dotenv from 'dotenv';

// Import core modules
import { InventorySyncManager } from './inventory/InventorySyncManager.js';
import { OrderingSystem } from './ordering/OrderingSystem.js';
import { CompatibilityChecker } from './compatibility/CompatibilityChecker.js';
import { PriceComparisonEngine } from './pricing/PriceComparisonEngine.js';
import { ShippingOptimizer } from './shipping/ShippingOptimizer.js';
import { AssemblerMatcher } from './assembler/AssemblerMatcher.js';
import { CustomProductDesigner } from './design/CustomProductDesigner.js';
import { ReputationSystem } from './reputation/ReputationSystem.js';
import { PaymentProcessor } from './payment/PaymentProcessor.js';
import { OrderTracker } from './tracking/OrderTracker.js';
import { WarrantyManager } from './warranty/WarrantyManager.js';
import { ReviewSystem } from './reviews/ReviewSystem.js';
import { VendorManager } from './vendors/VendorManager.js';
import { ProductCatalog } from './catalog/ProductCatalog.js';
import { SearchEngine } from './search/SearchEngine.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const PORT = process.env.PORT || 8379;
const NODE_ENV = process.env.NODE_ENV || 'development';

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    new winston.transports.File({ 
      filename: 'logs/error.log', 
      level: 'error' 
    }),
    new winston.transports.File({ 
      filename: 'logs/vendor-ecosystem.log' 
    })
  ]
});

// Express app setup
const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
    methods: ["GET", "POST", "PUT", "DELETE"],
    credentials: true
  },
  transports: ['websocket', 'polling']
});

// Middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "blob:", "https:"],
      mediaSrc: ["'self'", "blob:"],
      connectSrc: ["'self'", "ws:", "wss:"]
    }
  }
}));
app.use(compression());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
  credentials: true
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Static files
app.use('/static', express.static(join(__dirname, '../public')));
app.use('/uploads', express.static(join(__dirname, '../uploads')));

// Initialize core systems
let inventorySyncManager;
let orderingSystem;
let compatibilityChecker;
let priceComparisonEngine;
let shippingOptimizer;
let assemblerMatcher;
let customProductDesigner;
let reputationSystem;
let paymentProcessor;
let orderTracker;
let warrantyManager;
let reviewSystem;
let vendorManager;
let productCatalog;
let searchEngine;

async function initializeSystems() {
  try {
    logger.info('🔄 Initializing Vendor Ecosystem systems...');

    // Initialize core systems in dependency order
    vendorManager = new VendorManager();
    await vendorManager.initialize();

    productCatalog = new ProductCatalog();
    await productCatalog.initialize();

    searchEngine = new SearchEngine();
    await searchEngine.initialize();

    inventorySyncManager = new InventorySyncManager(io);
    await inventorySyncManager.initialize();

    compatibilityChecker = new CompatibilityChecker();
    await compatibilityChecker.initialize();

    priceComparisonEngine = new PriceComparisonEngine();
    await priceComparisonEngine.initialize();

    shippingOptimizer = new ShippingOptimizer();
    await shippingOptimizer.initialize();

    assemblerMatcher = new AssemblerMatcher();
    await assemblerMatcher.initialize();

    customProductDesigner = new CustomProductDesigner();
    await customProductDesigner.initialize();

    reputationSystem = new ReputationSystem();
    await reputationSystem.initialize();

    paymentProcessor = new PaymentProcessor();
    await paymentProcessor.initialize();

    orderTracker = new OrderTracker(io);
    await orderTracker.initialize();

    warrantyManager = new WarrantyManager();
    await warrantyManager.initialize();

    reviewSystem = new ReviewSystem();

    orderingSystem = new OrderingSystem({
      priceComparisonEngine,
      shippingOptimizer,
      compatibilityChecker,
      paymentProcessor,
      orderTracker,
      inventorySyncManager
    });
    await orderingSystem.initialize();

    // Set up inter-system event handlers
    setupSystemEventHandlers();

    logger.info('✅ All Vendor Ecosystem systems initialized successfully');
  } catch (error) {
    logger.error('❌ Failed to initialize systems:', error);
    process.exit(1);
  }
}

function setupSystemEventHandlers() {
  // Inventory sync events
  inventorySyncManager.on('inventory:updated', (data) => {
    io.to(`vendor_${data.vendorId}`).emit('inventory_updated', data);
  });

  // Order events
  orderingSystem.on('order:placed', (order) => {
    orderTracker.trackOrder(order);
    io.to(`user_${order.customerId}`).emit('order_placed', order);
  });

  // Price update events
  priceComparisonEngine.on('price:updated', (data) => {
    io.emit('price_updated', data);
  });

  // Shipping events
  orderTracker.on('tracking:updated', (data) => {
    io.to(`order_${data.orderId}`).emit('tracking_updated', data);
  });

  // Review events
  reviewSystem.on('reviewSubmitted', (review) => {
    io.emit('review_submitted', review);
  });

  reviewSystem.on('reviewPublished', (review) => {
    io.emit('review_published', review);
  });

  reviewSystem.on('reviewFlagged', (data) => {
    io.to('moderators').emit('review_flagged', data);
  });
}

// REST API Routes

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'vendor-ecosystem',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    port: PORT,
    environment: NODE_ENV
  });
});

// Vendor management endpoints
app.post('/api/vendors', async (req, res) => {
  try {
    const vendorData = req.body;
    const vendor = await vendorManager.registerVendor(vendorData);
    
    logger.info(`🏪 Registered vendor: ${vendor.name}`);
    res.json(vendor);
  } catch (error) {
    logger.error('Failed to register vendor:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/vendors', async (req, res) => {
  try {
    const { category, location, rating, verified } = req.query;
    const vendors = await vendorManager.getVendors({
      category,
      location,
      rating: rating ? parseFloat(rating) : null,
      verified: verified === 'true'
    });
    
    res.json(vendors);
  } catch (error) {
    logger.error('Failed to get vendors:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/vendors/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const vendor = await vendorManager.getVendor(id);
    
    if (!vendor) {
      return res.status(404).json({ error: 'Vendor not found' });
    }
    
    res.json(vendor);
  } catch (error) {
    logger.error('Failed to get vendor:', error);
    res.status(500).json({ error: error.message });
  }
});

// Product catalog endpoints
app.get('/api/products/search', async (req, res) => {
  try {
    const { q, category, minPrice, maxPrice, vendor, compatibility, page = 1, limit = 20 } = req.query;
    
    const searchResults = await searchEngine.searchProducts({
      query: q,
      category,
      priceRange: minPrice && maxPrice ? { min: parseFloat(minPrice), max: parseFloat(maxPrice) } : null,
      vendor,
      compatibility,
      page: parseInt(page),
      limit: parseInt(limit)
    });
    
    res.json(searchResults);
  } catch (error) {
    logger.error('Failed to search products:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/products/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const product = await productCatalog.getProduct(id);
    
    if (!product) {
      return res.status(404).json({ error: 'Product not found' });
    }
    
    res.json(product);
  } catch (error) {
    logger.error('Failed to get product:', error);
    res.status(500).json({ error: error.message });
  }
});

// Compatibility checking endpoints
app.post('/api/compatibility/check', async (req, res) => {
  try {
    const { baseProduct, targetProducts } = req.body;
    
    const compatibilityResults = await compatibilityChecker.checkCompatibility(
      baseProduct,
      targetProducts
    );
    
    res.json(compatibilityResults);
  } catch (error) {
    logger.error('Failed to check compatibility:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/compatibility/suggestions/:productId', async (req, res) => {
  try {
    const { productId } = req.params;
    const { category, limit = 10 } = req.query;
    
    const suggestions = await compatibilityChecker.getCompatibleProducts(
      productId,
      { category, limit: parseInt(limit) }
    );
    
    res.json(suggestions);
  } catch (error) {
    logger.error('Failed to get compatibility suggestions:', error);
    res.status(500).json({ error: error.message });
  }
});

// Price comparison endpoints
app.get('/api/pricing/compare/:productId', async (req, res) => {
  try {
    const { productId } = req.params;
    const { includeShipping = false } = req.query;
    
    const priceComparison = await priceComparisonEngine.comparePrice(
      productId,
      { includeShipping: includeShipping === 'true' }
    );
    
    res.json(priceComparison);
  } catch (error) {
    logger.error('Failed to compare prices:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/pricing/bulk-compare', async (req, res) => {
  try {
    const { productIds, shippingAddress } = req.body;
    
    const bulkComparison = await priceComparisonEngine.bulkComparePrice(
      productIds,
      shippingAddress
    );
    
    res.json(bulkComparison);
  } catch (error) {
    logger.error('Failed to bulk compare prices:', error);
    res.status(500).json({ error: error.message });
  }
});

// Shipping optimization endpoints
app.post('/api/shipping/optimize', async (req, res) => {
  try {
    const { items, shippingAddress, preferences } = req.body;
    
    const optimizedShipping = await shippingOptimizer.optimizeShipping(
      items,
      shippingAddress,
      preferences
    );
    
    res.json(optimizedShipping);
  } catch (error) {
    logger.error('Failed to optimize shipping:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/shipping/quote', async (req, res) => {
  try {
    const { items, fromAddress, toAddress, options } = req.body;
    
    const shippingQuote = await shippingOptimizer.getShippingQuote(
      items,
      fromAddress,
      toAddress,
      options
    );
    
    res.json(shippingQuote);
  } catch (error) {
    logger.error('Failed to get shipping quote:', error);
    res.status(500).json({ error: error.message });
  }
});

// Assembler matching endpoints
app.post('/api/assemblers/search', async (req, res) => {
  try {
    const { location, skills, availability, budget } = req.body;
    
    const assemblers = await assemblerMatcher.findAssemblers({
      location,
      skills,
      availability,
      budget
    });
    
    res.json(assemblers);
  } catch (error) {
    logger.error('Failed to search assemblers:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/assemblers/:id/quote', async (req, res) => {
  try {
    const { id } = req.params;
    const { project } = req.body;
    
    const quote = await assemblerMatcher.getAssemblerQuote(id, project);
    
    res.json(quote);
  } catch (error) {
    logger.error('Failed to get assembler quote:', error);
    res.status(500).json({ error: error.message });
  }
});

// Custom product design endpoints
app.post('/api/design/request', async (req, res) => {
  try {
    const designRequest = req.body;
    
    const request = await customProductDesigner.createDesignRequest(designRequest);
    
    logger.info(`🎨 Created design request: ${request.id}`);
    res.json(request);
  } catch (error) {
    logger.error('Failed to create design request:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/design/requests/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const request = await customProductDesigner.getDesignRequest(id);
    
    if (!request) {
      return res.status(404).json({ error: 'Design request not found' });
    }
    
    res.json(request);
  } catch (error) {
    logger.error('Failed to get design request:', error);
    res.status(500).json({ error: error.message });
  }
});

// Ordering system endpoints
app.post('/api/orders', async (req, res) => {
  try {
    const orderData = req.body;
    
    const order = await orderingSystem.createOrder(orderData);
    
    logger.info(`📦 Created order: ${order.id}`);
    res.json(order);
  } catch (error) {
    logger.error('Failed to create order:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/orders/one-click', async (req, res) => {
  try {
    const { customerId, productId, quantity = 1, savedAddressId, savedPaymentId } = req.body;
    
    const order = await orderingSystem.oneClickOrder({
      customerId,
      productId,
      quantity,
      savedAddressId,
      savedPaymentId
    });
    
    logger.info(`⚡ One-click order placed: ${order.id}`);
    res.json(order);
  } catch (error) {
    logger.error('Failed to place one-click order:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/orders/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const order = await orderingSystem.getOrder(id);
    
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }
    
    res.json(order);
  } catch (error) {
    logger.error('Failed to get order:', error);
    res.status(500).json({ error: error.message });
  }
});

// Order tracking endpoints
app.get('/api/orders/:id/tracking', async (req, res) => {
  try {
    const { id } = req.params;
    const tracking = await orderTracker.getOrderTracking(id);
    
    res.json(tracking);
  } catch (error) {
    logger.error('Failed to get order tracking:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/orders/:id/tracking/update', async (req, res) => {
  try {
    const { id } = req.params;
    const { status, location, notes, estimatedDelivery } = req.body;
    
    const trackingUpdate = await orderTracker.updateTracking(id, {
      status,
      location,
      notes,
      estimatedDelivery
    });
    
    res.json(trackingUpdate);
  } catch (error) {
    logger.error('Failed to update order tracking:', error);
    res.status(500).json({ error: error.message });
  }
});

// Payment processing endpoints
app.post('/api/payments/process', async (req, res) => {
  try {
    const { orderId, paymentMethod, amount, currency = 'USD' } = req.body;
    
    const payment = await paymentProcessor.processPayment({
      orderId,
      paymentMethod,
      amount,
      currency
    });
    
    res.json(payment);
  } catch (error) {
    logger.error('Failed to process payment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/payments/methods', async (req, res) => {
  try {
    const { customerId, paymentMethod } = req.body;
    
    const savedMethod = await paymentProcessor.savePaymentMethod(customerId, paymentMethod);
    
    res.json(savedMethod);
  } catch (error) {
    logger.error('Failed to save payment method:', error);
    res.status(500).json({ error: error.message });
  }
});

// Warranty management endpoints
app.post('/api/warranties', async (req, res) => {
  try {
    const warrantyData = req.body;
    
    const warranty = await warrantyManager.createWarranty(warrantyData);
    
    res.json(warranty);
  } catch (error) {
    logger.error('Failed to create warranty:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/warranties/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const warranty = await warrantyManager.getWarranty(id);
    
    if (!warranty) {
      return res.status(404).json({ error: 'Warranty not found' });
    }
    
    res.json(warranty);
  } catch (error) {
    logger.error('Failed to get warranty:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/warranties/:id/claim', async (req, res) => {
  try {
    const { id } = req.params;
    const claimData = req.body;
    
    const claim = await warrantyManager.submitClaim(id, claimData);
    
    logger.info(`🛡️ Warranty claim submitted: ${claim.id}`);
    res.json(claim);
  } catch (error) {
    logger.error('Failed to submit warranty claim:', error);
    res.status(500).json({ error: error.message });
  }
});

// Review system endpoints
app.post('/api/reviews', async (req, res) => {
  try {
    const reviewData = req.body;
    
    const review = await reviewSystem.submitReview(reviewData);
    
    logger.info(`⭐ Review submitted: ${review.review_id}`);
    res.json(review);
  } catch (error) {
    logger.error('Failed to submit review:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/reviews/:targetType/:targetId', async (req, res) => {
  try {
    const { targetType, targetId } = req.params;
    const { 
      page = 1, 
      limit = 20, 
      rating_min, 
      rating_max, 
      verified_only = false,
      sort_by = 'helpful',
      date_from,
      date_to
    } = req.query;
    
    const reviews = await reviewSystem.getReviewsForTarget(targetType, targetId, {
      page: parseInt(page),
      limit: parseInt(limit),
      rating_min: rating_min ? parseFloat(rating_min) : null,
      rating_max: rating_max ? parseFloat(rating_max) : null,
      verified_only: verified_only === 'true',
      sort_by,
      date_from,
      date_to
    });
    
    res.json(reviews);
  } catch (error) {
    logger.error('Failed to get reviews:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/reviews/:reviewId/flag', async (req, res) => {
  try {
    const { reviewId } = req.params;
    const flagData = req.body;
    
    const result = await reviewSystem.flagReview(reviewId, flagData);
    
    logger.info(`🚩 Review flagged: ${reviewId}`);
    res.json(result);
  } catch (error) {
    logger.error('Failed to flag review:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/reviews/:reviewId/helpful', async (req, res) => {
  try {
    const { reviewId } = req.params;
    const { userId, helpful } = req.body;
    
    const result = await reviewSystem.voteOnReviewHelpfulness(reviewId, userId, helpful);
    
    res.json(result);
  } catch (error) {
    logger.error('Failed to vote on review helpfulness:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/reviews/:targetType/:targetId/insights', async (req, res) => {
  try {
    const { targetType, targetId } = req.params;
    
    const insights = await reviewSystem.generateReviewInsights(targetType, targetId);
    
    res.json(insights);
  } catch (error) {
    logger.error('Failed to generate review insights:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/reviews/:reviewId/moderate', async (req, res) => {
  try {
    const { reviewId } = req.params;
    const { moderatorId, action, notes } = req.body;
    
    const result = await reviewSystem.moderateReview(reviewId, moderatorId, action, notes);
    
    logger.info(`🔍 Review moderated: ${reviewId} - ${action}`);
    res.json(result);
  } catch (error) {
    logger.error('Failed to moderate review:', error);
    res.status(500).json({ error: error.message });
  }
});

// Reputation system endpoints
app.get('/api/reputation/:vendorId', async (req, res) => {
  try {
    const { vendorId } = req.params;
    const reputation = await reputationSystem.getVendorReputation(vendorId);
    
    res.json(reputation);
  } catch (error) {
    logger.error('Failed to get vendor reputation:', error);
    res.status(500).json({ error: error.message });
  }
});

// Inventory sync endpoints
app.post('/api/inventory/sync', async (req, res) => {
  try {
    const { vendorId, inventoryData } = req.body;
    
    const syncResult = await inventorySyncManager.syncInventory(vendorId, inventoryData);
    
    res.json(syncResult);
  } catch (error) {
    logger.error('Failed to sync inventory:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/inventory/:vendorId', async (req, res) => {
  try {
    const { vendorId } = req.params;
    const inventory = await inventorySyncManager.getVendorInventory(vendorId);
    
    res.json(inventory);
  } catch (error) {
    logger.error('Failed to get vendor inventory:', error);
    res.status(500).json({ error: error.message });
  }
});

// Socket.IO real-time communication
io.on('connection', (socket) => {
  logger.info(`🔌 Client connected: ${socket.id}`);
  
  // Join vendor room for inventory updates
  socket.on('join_vendor', (vendorId) => {
    socket.join(`vendor_${vendorId}`);
    logger.info(`🏪 Socket ${socket.id} joined vendor: ${vendorId}`);
  });
  
  // Join user room for order updates
  socket.on('join_user', (userId) => {
    socket.join(`user_${userId}`);
    logger.info(`👤 Socket ${socket.id} joined user: ${userId}`);
  });
  
  // Join order room for tracking updates
  socket.on('join_order', (orderId) => {
    socket.join(`order_${orderId}`);
    logger.info(`📦 Socket ${socket.id} joined order: ${orderId}`);
  });
  
  // Real-time inventory updates
  socket.on('inventory_update', async (data) => {
    try {
      await inventorySyncManager.updateInventory(data.vendorId, data.productId, data.quantity);
      socket.to(`vendor_${data.vendorId}`).emit('inventory_updated', data);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  });
  
  // Real-time price alerts
  socket.on('watch_price', (productId) => {
    socket.join(`price_${productId}`);
  });
  
  socket.on('unwatch_price', (productId) => {
    socket.leave(`price_${productId}`);
  });
  
  // Real-time order status updates
  socket.on('order_status_update', (data) => {
    io.to(`order_${data.orderId}`).emit('order_status_changed', {
      orderId: data.orderId,
      status: data.status,
      timestamp: Date.now()
    });
  });
  
  // Handle disconnection
  socket.on('disconnect', () => {
    logger.info(`🔌 Client disconnected: ${socket.id}`);
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    message: NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  logger.info(`📴 Received ${signal}, shutting down gracefully...`);
  
  server.close(() => {
    logger.info('HTTP server closed');
    
    // Close all system connections
    const systems = [
      inventorySyncManager, orderingSystem, compatibilityChecker,
      priceComparisonEngine, shippingOptimizer, assemblerMatcher,
      customProductDesigner, reputationSystem, paymentProcessor,
      orderTracker, warrantyManager, reviewSystem, vendorManager,
      productCatalog, searchEngine
    ];
    
    systems.forEach(system => {
      if (system && typeof system.close === 'function') {
        system.close();
      }
    });
    
    logger.info('All connections closed, exiting...');
    process.exit(0);
  });
  
  // Force close after 30 seconds
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 30000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Start server
async function startServer() {
  try {
    await initializeSystems();
    
    server.listen(PORT, () => {
      logger.info(`🚀 Vendor Ecosystem Platform started on port ${PORT}`);
      logger.info(`🌍 Environment: ${NODE_ENV}`);
      logger.info(`🎯 All systems operational`);
      
      console.log(`
╔══════════════════════════════════════════╗
║          Vendor Ecosystem Platform       ║
║                                          ║
║  🏪 Comprehensive Vendor Marketplace     ║
║  📦 Real-time Inventory Synchronization  ║
║  ⚡ One-click Ordering System            ║
║  🔍 Intelligent Part Compatibility       ║
║  💰 Advanced Price Comparison            ║
║  🚚 Shipping Optimization Engine         ║
║  🔧 Expert Assembler Matching            ║
║  🎨 Custom Product Design Studio         ║
║  ⭐ Comprehensive Reputation System      ║
║  💳 Secure Payment Integration           ║
║  📱 Real-time Order Tracking            ║
║  🛡️ Warranty Management System           ║
║  💬 Advanced Review Platform             ║
║                                          ║
║  Port: ${PORT.toString().padEnd(31)} ║
║  Status: READY                           ║
╚══════════════════════════════════════════╝
      `);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Start the server
startServer();

export { app, server, io };