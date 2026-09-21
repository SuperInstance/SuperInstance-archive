const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const axios = require('axios');
const cors = require('cors');
const winston = require('winston');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 8384;

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { service: 'monitoring-dashboard' },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    })
  ]
});

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Service endpoints
const services = {
  orchestrator: 'http://localhost:8383',
  'screen-intelligence': 'http://localhost:8369',
  'remote-control': 'http://localhost:8370',
  'trek-computer': 'http://localhost:8377',
  'ad-engine': 'http://localhost:8382'
};

// Fetch service health data
const fetchServiceHealth = async () => {
  try {
    const response = await axios.get(`${services.orchestrator}/health`, { timeout: 5000 });
    return response.data;
  } catch (error) {
    logger.error('Failed to fetch service health:', error.message);
    return null;
  }
};

// Fetch individual service metrics
const fetchServiceMetrics = async (serviceName, serviceUrl) => {
  try {
    const endpoints = {
      'screen-intelligence': '/api/radar/status',
      'trek-computer': '/api/ambient/metrics',
      'ad-engine': '/api/status',
      'remote-control': '/health'
    };
    
    const endpoint = endpoints[serviceName] || '/health';
    const response = await axios.get(`${serviceUrl}${endpoint}`, { timeout: 3000 });
    
    return {
      service: serviceName,
      status: 'active',
      data: response.data,
      responseTime: response.duration || 'N/A',
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    return {
      service: serviceName,
      status: 'error',
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
};

// Dashboard route
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'dashboard.html'));
});

// API routes
app.get('/api/health', async (req, res) => {
  const healthData = await fetchServiceHealth();
  res.json(healthData);
});

app.get('/api/metrics', async (req, res) => {
  const metricsPromises = Object.entries(services)
    .filter(([name]) => name !== 'orchestrator')
    .map(([name, url]) => fetchServiceMetrics(name, url));
  
  const metrics = await Promise.all(metricsPromises);
  res.json(metrics);
});

// WebSocket connections for real-time updates
io.on('connection', (socket) => {
  logger.info(`Client connected: ${socket.id}`);
  
  socket.on('subscribe', (data) => {
    logger.info(`Client ${socket.id} subscribed to: ${data.type}`);
  });
  
  socket.on('disconnect', () => {
    logger.info(`Client disconnected: ${socket.id}`);
  });
});

// Real-time data broadcasting
const broadcastSystemStatus = async () => {
  try {
    const [healthData, metricsData] = await Promise.all([
      fetchServiceHealth(),
      Promise.all(
        Object.entries(services)
          .filter(([name]) => name !== 'orchestrator')
          .map(([name, url]) => fetchServiceMetrics(name, url))
      )
    ]);
    
    const systemStatus = {
      health: healthData,
      metrics: metricsData,
      timestamp: new Date().toISOString()
    };
    
    io.emit('system-status', systemStatus);
    
  } catch (error) {
    logger.error('Failed to broadcast system status:', error.message);
  }
};

// Start broadcasting every 5 seconds
setInterval(broadcastSystemStatus, 5000);

server.listen(PORT, () => {
  logger.info(`🚀 Monitoring Dashboard running on port ${PORT}`);
  logger.info(`📊 Dashboard URL: http://localhost:${PORT}`);
  logger.info(`📡 WebSocket connections active`);
  
  console.log(`
╔════════════════════════════════════════════════════╗
║            ActiveLog Monitoring Dashboard         ║
║                                                    ║
║  📊 Real-time Service Monitoring                  ║
║  📈 Performance Metrics & Analytics               ║
║  ⚡ Live Health Status Updates                    ║
║  🎯 System Overview & Alerts                      ║
║                                                    ║
║  Port: ${PORT.toString().padEnd(42)} ║
║  Dashboard: http://localhost:${PORT}${' '.repeat(14)} ║
╚════════════════════════════════════════════════════╝
  `);
  
  // Initial broadcast
  setTimeout(broadcastSystemStatus, 2000);
});

module.exports = app;