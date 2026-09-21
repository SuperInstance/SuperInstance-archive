const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const { createProxyMiddleware } = require('http-proxy-middleware');
const winston = require('winston');
const cron = require('node-cron');
const axios = require('axios');
const WebSocket = require('ws');

const app = express();
const PORT = process.env.PORT || 8383;

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'service-orchestrator' },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    })
  ]
});

// Service Registry
const services = {
  'screen-intelligence': {
    name: 'Screen Intelligence & Radar System',
    port: 8369,
    url: 'http://localhost:8369',
    health: '/health',
    status: 'active',
    capabilities: ['collision-detection', 'radar-tracking', 'threat-assessment']
  },
  'remote-control': {
    name: 'Remote Control System',
    port: 8370,
    url: 'http://localhost:8370',
    health: '/health',
    status: 'active',
    capabilities: ['device-control', 'authentication', 'session-management']
  },
  'trek-computer': {
    name: 'Trek Computer Interface',
    port: 8377,
    url: 'http://localhost:8377',
    health: '/health',
    status: 'active',
    capabilities: ['ambient-monitoring', 'sensor-fusion', 'predictive-modeling']
  },
  'ad-engine': {
    name: 'Ad Monetization Engine',
    port: 8382,
    url: 'http://localhost:8382',
    health: '/health',
    status: 'active',
    capabilities: ['ad-serving', 'ccc-credits', 'parent-child-controls', 'review-system']
  }
};

// Middleware setup
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
}));

app.use(cors({
  origin: process.env.NODE_ENV === 'production' 
    ? ['https://activelog.com', 'https://app.activelog.com']
    : true,
  credentials: true
}));

app.use(compression());
app.use(morgan('combined'));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000,
  message: 'Too many requests from this IP',
  standardHeaders: true,
  legacyHeaders: false
});

app.use(limiter);
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Service Health Monitoring
const checkServiceHealth = async (service) => {
  try {
    const response = await axios.get(`${service.url}${service.health}`, {
      timeout: 5000,
      validateStatus: (status) => status < 500
    });
    
    return {
      name: service.name,
      port: service.port,
      status: response.status === 200 ? 'healthy' : 'degraded',
      responseTime: response.duration || 'N/A',
      lastCheck: new Date().toISOString(),
      capabilities: service.capabilities
    };
  } catch (error) {
    return {
      name: service.name,
      port: service.port,
      status: 'unhealthy',
      error: error.message,
      lastCheck: new Date().toISOString(),
      capabilities: service.capabilities
    };
  }
};

// System Health Endpoint
app.get('/health', async (req, res) => {
  const healthChecks = await Promise.all(
    Object.values(services).map(checkServiceHealth)
  );
  
  const systemHealth = {
    status: 'healthy',
    service: 'service-orchestrator',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: '1.0.0',
    services: healthChecks,
    summary: {
      total: healthChecks.length,
      healthy: healthChecks.filter(s => s.status === 'healthy').length,
      degraded: healthChecks.filter(s => s.status === 'degraded').length,
      unhealthy: healthChecks.filter(s => s.status === 'unhealthy').length
    }
  };
  
  // Determine overall system status
  if (systemHealth.summary.unhealthy > 0) {
    systemHealth.status = 'degraded';
  }
  if (systemHealth.summary.healthy === 0) {
    systemHealth.status = 'critical';
  }
  
  res.json(systemHealth);
});

// Service Discovery Endpoint
app.get('/services', (req, res) => {
  const serviceList = Object.entries(services).map(([key, service]) => ({
    id: key,
    name: service.name,
    port: service.port,
    url: service.url,
    status: service.status,
    capabilities: service.capabilities
  }));
  
  res.json({
    services: serviceList,
    count: serviceList.length,
    timestamp: new Date().toISOString()
  });
});

// Cross-Service Communication Hub
app.post('/orchestrate/:action', async (req, res) => {
  const { action } = req.params;
  const { services: targetServices, payload, userId } = req.body;
  
  try {
    logger.info(`Orchestrating action: ${action}`, { 
      targetServices, 
      userId,
      timestamp: new Date().toISOString() 
    });
    
    const results = {};
    
    switch (action) {
      case 'emergency-collision-response':
        // Screen Intelligence detects collision threat
        // Trek Computer adjusts environmental parameters
        // Remote Control initiates emergency protocols
        if (targetServices.includes('screen-intelligence')) {
          const radarResponse = await axios.post(
            `${services['screen-intelligence'].url}/api/radar/emergency`,
            payload
          );
          results['screen-intelligence'] = radarResponse.data;
        }
        
        if (targetServices.includes('trek-computer')) {
          const trekResponse = await axios.post(
            `${services['trek-computer'].url}/api/ambient/emergency-mode`,
            payload
          );
          results['trek-computer'] = trekResponse.data;
        }
        
        if (targetServices.includes('remote-control')) {
          const remoteResponse = await axios.post(
            `${services['remote-control'].url}/api/emergency/protocol`,
            payload
          );
          results['remote-control'] = remoteResponse.data;
        }
        break;
        
      case 'compute-credit-flow':
        // Ad Engine manages CCC credits
        // Trek Computer consumes credits for heavy operations
        if (targetServices.includes('ad-engine')) {
          const adResponse = await axios.post(
            `${services['ad-engine'].url}/api/users/${userId}/compute/request`,
            payload
          );
          results['ad-engine'] = adResponse.data;
        }
        
        if (targetServices.includes('trek-computer') && results['ad-engine']?.approved) {
          const computeResponse = await axios.post(
            `${services['trek-computer'].url}/api/operations/execute`,
            { ...payload, credits: results['ad-engine'].creditsUsed }
          );
          results['trek-computer'] = computeResponse.data;
        }
        break;
        
      case 'cross-system-sync':
        // Sync user data across all services
        const syncPromises = targetServices.map(async (serviceName) => {
          if (services[serviceName]) {
            try {
              const response = await axios.post(
                `${services[serviceName].url}/api/sync/user`,
                { userId, data: payload }
              );
              return { service: serviceName, success: true, data: response.data };
            } catch (error) {
              return { service: serviceName, success: false, error: error.message };
            }
          }
        });
        
        const syncResults = await Promise.all(syncPromises);
        results.syncResults = syncResults;
        break;
        
      default:
        return res.status(400).json({
          error: 'Unknown orchestration action',
          availableActions: [
            'emergency-collision-response',
            'compute-credit-flow',
            'cross-system-sync'
          ]
        });
    }
    
    res.json({
      action,
      status: 'completed',
      results,
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    logger.error('Orchestration error:', error);
    res.status(500).json({
      error: 'Orchestration failed',
      message: error.message,
      action,
      timestamp: new Date().toISOString()
    });
  }
});

// API Gateway - Proxy requests to services
Object.entries(services).forEach(([serviceKey, service]) => {
  const proxyMiddleware = createProxyMiddleware({
    target: service.url,
    changeOrigin: true,
    pathRewrite: {
      [`^/${serviceKey}`]: ''
    },
    onProxyReq: (proxyReq, req, res) => {
      logger.info(`Proxying request to ${service.name}`, {
        originalUrl: req.originalUrl,
        method: req.method,
        target: service.url
      });
    },
    onError: (err, req, res) => {
      logger.error(`Proxy error for ${service.name}:`, err.message);
      res.status(503).json({
        error: 'Service unavailable',
        service: service.name,
        message: 'The requested service is temporarily unavailable'
      });
    }
  });
  
  app.use(`/${serviceKey}`, proxyMiddleware);
});

// WebSocket Hub for Real-time Communication
const server = require('http').createServer(app);
const wss = new WebSocket.Server({ server });

const connections = new Map();

wss.on('connection', (ws, req) => {
  const connectionId = require('uuid').v4();
  connections.set(connectionId, ws);
  
  logger.info(`WebSocket connection established: ${connectionId}`);
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      
      // Route messages between services
      if (data.type === 'service-broadcast') {
        // Broadcast to all connected clients
        connections.forEach((client, id) => {
          if (client !== ws && client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
              type: 'service-event',
              source: data.source,
              event: data.event,
              data: data.data,
              timestamp: new Date().toISOString()
            }));
          }
        });
      }
      
      // Handle specific orchestration requests via WebSocket
      if (data.type === 'orchestrate') {
        handleWebSocketOrchestration(ws, data);
      }
      
    } catch (error) {
      logger.error('WebSocket message error:', error);
      ws.send(JSON.stringify({
        type: 'error',
        message: 'Invalid message format'
      }));
    }
  });
  
  ws.on('close', () => {
    connections.delete(connectionId);
    logger.info(`WebSocket connection closed: ${connectionId}`);
  });
  
  // Send welcome message
  ws.send(JSON.stringify({
    type: 'connected',
    connectionId,
    availableServices: Object.keys(services),
    timestamp: new Date().toISOString()
  }));
});

const handleWebSocketOrchestration = async (ws, data) => {
  // Handle real-time orchestration requests
  try {
    const result = await orchestrateAction(data.action, data.payload);
    ws.send(JSON.stringify({
      type: 'orchestration-result',
      requestId: data.requestId,
      result,
      timestamp: new Date().toISOString()
    }));
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'orchestration-error',
      requestId: data.requestId,
      error: error.message,
      timestamp: new Date().toISOString()
    }));
  }
};

// Scheduled Health Monitoring
cron.schedule('*/30 * * * * *', async () => {
  // Check all services every 30 seconds
  const healthChecks = await Promise.all(
    Object.values(services).map(checkServiceHealth)
  );
  
  const unhealthyServices = healthChecks.filter(s => s.status === 'unhealthy');
  
  if (unhealthyServices.length > 0) {
    logger.warn('Unhealthy services detected:', {
      services: unhealthyServices.map(s => s.name),
      count: unhealthyServices.length
    });
    
    // Broadcast health alert via WebSocket
    const healthAlert = {
      type: 'health-alert',
      unhealthyServices: unhealthyServices.map(s => ({
        name: s.name,
        port: s.port,
        error: s.error
      })),
      timestamp: new Date().toISOString()
    };
    
    connections.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(healthAlert));
      }
    });
  }
});

// API Documentation
app.get('/docs', (req, res) => {
  res.json({
    service: 'ActiveLog Service Orchestrator',
    version: '1.0.0',
    description: 'Central orchestration and API gateway for ActiveLog ecosystem',
    
    endpoints: {
      health: {
        path: '/health',
        method: 'GET',
        description: 'System and service health status'
      },
      services: {
        path: '/services',
        method: 'GET',
        description: 'Service discovery and registry'
      },
      orchestrate: {
        path: '/orchestrate/:action',
        method: 'POST',
        description: 'Cross-service orchestration actions',
        actions: [
          'emergency-collision-response',
          'compute-credit-flow',
          'cross-system-sync'
        ]
      },
      proxy: {
        path: '/:service/*',
        method: 'ANY',
        description: 'Proxy requests to individual services',
        services: Object.keys(services)
      }
    },
    
    websocket: {
      url: `ws://localhost:${PORT}`,
      description: 'Real-time communication hub',
      messageTypes: [
        'service-broadcast',
        'orchestrate',
        'health-alert'
      ]
    },
    
    registeredServices: services
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Endpoint not found',
    message: 'The requested resource was not found',
    availableEndpoints: {
      health: '/health',
      services: '/services',
      docs: '/docs',
      orchestrate: '/orchestrate/:action'
    },
    registeredServices: Object.keys(services)
  });
});

// Error handler
app.use((error, req, res, next) => {
  logger.error('Unhandled error:', {
    error: error.message,
    stack: error.stack,
    url: req.url,
    method: req.method
  });
  
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'production' 
      ? 'Something went wrong' 
      : error.message,
    timestamp: new Date().toISOString()
  });
});

// Start server
server.listen(PORT, () => {
  logger.info(`🚀 Service Orchestrator running on port ${PORT}`);
  logger.info(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
  logger.info(`🔗 API Documentation: http://localhost:${PORT}/docs`);
  logger.info(`❤️  Health Check: http://localhost:${PORT}/health`);
  logger.info(`📡 WebSocket Hub: ws://localhost:${PORT}`);
  
  console.log(`
╔════════════════════════════════════════════════════╗
║              ActiveLog Orchestrator               ║
║                                                    ║
║  🎯 Service Mesh & API Gateway                    ║
║  🔄 Cross-Service Communication                   ║
║  📡 Real-time WebSocket Hub                       ║
║  ❤️  Health Monitoring & Alerts                   ║
║  🛡️  Request Routing & Load Balancing            ║
║                                                    ║
║  Port: ${PORT.toString().padEnd(42)} ║
║  Health: http://localhost:${PORT}/health${' '.repeat(16)} ║
║  Docs: http://localhost:${PORT}/docs${' '.repeat(18)} ║
║  WebSocket: ws://localhost:${PORT}${' '.repeat(15)} ║
╚════════════════════════════════════════════════════╝

🔗 Connected Services:
${Object.entries(services).map(([key, service]) => 
  `   • ${service.name} (Port ${service.port})`
).join('\n')}
  `);
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  logger.info(`Received ${signal}. Starting graceful shutdown...`);
  
  server.close(() => {
    logger.info('HTTP server closed');
    
    // Close all WebSocket connections
    connections.forEach((ws) => {
      ws.close();
    });
    
    logger.info('All WebSocket connections closed');
    logger.info('Graceful shutdown completed');
    process.exit(0);
  });
  
  // Force shutdown after timeout
  setTimeout(() => {
    logger.error('Shutdown timeout exceeded, forcing exit');
    process.exit(1);
  }, 10000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

module.exports = app;