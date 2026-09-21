const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');

const MqttBroker = require('./services/MqttBroker');
const DeviceProvisioning = require('./services/DeviceProvisioning');
const FirmwareOTA = require('./services/FirmwareOTA');
const DeviceTwinManager = require('./services/DeviceTwinManager');
const EdgeOrchestrator = require('./services/EdgeOrchestrator');
const RuleEngine = require('./services/RuleEngine');
const DeviceFleetManager = require('./services/DeviceFleetManager');

class IoTGatewayApp {
  constructor() {
    this.app = express();
    this.server = http.createServer(this.app);
    this.wss = new WebSocket.Server({ server: this.server });
    
    this.services = {};
    this.connections = new Map();
    this.setupMiddleware();
    this.initializeServices();
    this.setupRoutes();
    this.setupWebSocketServer();
    this.setupEventListeners();
  }

  setupMiddleware() {
    this.app.use(helmet());
    this.app.use(cors());
    this.app.use(compression());
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true }));
    
    // Request logging
    this.app.use((req, res, next) => {
      console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
      next();
    });
  }

  async initializeServices() {
    try {
      // Initialize core services
      this.services.mqttBroker = new MqttBroker({
        port: 1883,
        wsPort: 8883,
        enableAuth: true,
        enableACL: true
      });

      this.services.deviceProvisioning = new DeviceProvisioning({
        caKeyPath: './certs/ca-key.pem',
        caCertPath: './certs/ca-cert.pem',
        jwtSecret: process.env.JWT_SECRET || 'iot-gateway-secret'
      });

      this.services.firmwareOTA = new FirmwareOTA({
        storageDir: './firmware',
        maxFileSize: 100 * 1024 * 1024, // 100MB
        enableRollback: true
      });

      this.services.deviceTwinManager = new DeviceTwinManager({
        enableSync: true,
        syncInterval: 30000,
        maxTwins: 100000
      });

      this.services.edgeOrchestrator = new EdgeOrchestrator({
        maxNodes: 1000,
        maxFunctions: 10000,
        enableLoadBalancing: true
      });

      this.services.ruleEngine = new RuleEngine({
        maxRules: 1000,
        evaluationTimeout: 5000,
        enableMetrics: true
      });

      this.services.deviceFleetManager = new DeviceFleetManager({
        maxDevices: 100000,
        healthCheckInterval: 300000,
        batchSize: 100
      });

      // Start services
      await this.services.mqttBroker.start();
      console.log('MQTT Broker started on ports 1883 (TCP) and 8883 (WebSocket)');
      
      console.log('All IoT Gateway services initialized successfully');
    } catch (error) {
      console.error('Failed to initialize services:', error);
      process.exit(1);
    }
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: {
          mqttBroker: 'running',
          deviceProvisioning: 'running',
          firmwareOTA: 'running',
          deviceTwinManager: 'running',
          edgeOrchestrator: 'running',
          ruleEngine: 'running',
          deviceFleetManager: 'running'
        }
      });
    });

    // Device Provisioning Routes
    this.app.post('/api/devices/provision', async (req, res) => {
      try {
        const device = await this.services.deviceProvisioning.provisionDevice(req.body);
        res.json(device);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/devices/provision/:deviceId/credentials', async (req, res) => {
      try {
        const credentials = await this.services.deviceProvisioning.getDeviceCredentials(req.params.deviceId);
        res.json(credentials);
      } catch (error) {
        res.status(404).json({ error: error.message });
      }
    });

    this.app.delete('/api/devices/provision/:deviceId', async (req, res) => {
      try {
        await this.services.deviceProvisioning.deprovisionDevice(req.params.deviceId);
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Device Fleet Management Routes
    this.app.post('/api/fleet/devices', async (req, res) => {
      try {
        const device = await this.services.deviceFleetManager.registerDevice(req.body);
        res.json(device);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/fleet/devices', (req, res) => {
      try {
        const devices = this.services.deviceFleetManager.getDevices(req.query);
        res.json(devices);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/fleet/devices/:deviceId', (req, res) => {
      try {
        const device = this.services.deviceFleetManager.getDevice(req.params.deviceId);
        if (!device) {
          return res.status(404).json({ error: 'Device not found' });
        }
        res.json(device);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.put('/api/fleet/devices/:deviceId', async (req, res) => {
      try {
        const device = this.services.deviceFleetManager.updateDevice(req.params.deviceId, req.body);
        res.json(device);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.delete('/api/fleet/devices/:deviceId', async (req, res) => {
      try {
        await this.services.deviceFleetManager.unregisterDevice(req.params.deviceId);
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/fleet/devices/:deviceId/commands', async (req, res) => {
      try {
        const commandId = await this.services.deviceFleetManager.sendCommand(
          req.params.deviceId,
          req.body.command,
          req.body.params,
          req.body.options
        );
        res.json({ commandId });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/fleet/metrics', (req, res) => {
      try {
        const metrics = this.services.deviceFleetManager.getFleetMetrics();
        res.json(metrics);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Device Groups Routes
    this.app.post('/api/fleet/groups', async (req, res) => {
      try {
        const group = this.services.deviceFleetManager.createDeviceGroup(req.body);
        res.json(group);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/fleet/groups', (req, res) => {
      try {
        const groups = this.services.deviceFleetManager.getDeviceGroups();
        res.json(groups);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/fleet/groups/:groupId/commands', async (req, res) => {
      try {
        const results = await this.services.deviceFleetManager.sendGroupCommand(
          req.params.groupId,
          req.body.command,
          req.body.params,
          req.body.options
        );
        res.json({ results });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Firmware OTA Routes
    this.app.post('/api/firmware/packages', async (req, res) => {
      try {
        const firmware = await this.services.firmwareOTA.createFirmware(req.body);
        res.json(firmware);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/firmware/packages', (req, res) => {
      try {
        const packages = this.services.firmwareOTA.getFirmwarePackages();
        res.json(packages);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/firmware/deployments', async (req, res) => {
      try {
        const deployment = await this.services.firmwareOTA.createDeployment(req.body);
        res.json(deployment);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/firmware/deployments/:deploymentId/start', async (req, res) => {
      try {
        await this.services.firmwareOTA.startDeployment(req.params.deploymentId);
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/firmware/deployments', (req, res) => {
      try {
        const deployments = this.services.firmwareOTA.getDeployments();
        res.json(deployments);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Device Twin Routes
    this.app.post('/api/twins/:deviceId', async (req, res) => {
      try {
        const twin = await this.services.deviceTwinManager.createTwin(req.params.deviceId, req.body);
        res.json(twin);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/twins/:deviceId', (req, res) => {
      try {
        const twin = this.services.deviceTwinManager.getTwin(req.params.deviceId);
        if (!twin) {
          return res.status(404).json({ error: 'Device twin not found' });
        }
        res.json(twin);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.patch('/api/twins/:deviceId/desired', async (req, res) => {
      try {
        await this.services.deviceTwinManager.updateDesiredProperties(req.params.deviceId, req.body);
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.patch('/api/twins/:deviceId/reported', async (req, res) => {
      try {
        await this.services.deviceTwinManager.updateReportedProperties(req.params.deviceId, req.body);
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Edge Computing Routes
    this.app.post('/api/edge/nodes', async (req, res) => {
      try {
        const node = await this.services.edgeOrchestrator.registerNode(req.body);
        res.json(node);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/edge/nodes', (req, res) => {
      try {
        const nodes = this.services.edgeOrchestrator.getNodes();
        res.json(nodes);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/edge/functions', async (req, res) => {
      try {
        const func = await this.services.edgeOrchestrator.createFunction(req.body);
        res.json(func);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/edge/functions', (req, res) => {
      try {
        const functions = this.services.edgeOrchestrator.getFunctions();
        res.json(functions);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/edge/functions/:functionId/deploy', async (req, res) => {
      try {
        await this.services.edgeOrchestrator.deployFunction(req.params.functionId, req.body.nodeIds);
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Rule Engine Routes
    this.app.post('/api/rules', async (req, res) => {
      try {
        const rule = await this.services.ruleEngine.createRule(req.body);
        res.json(rule);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/rules', (req, res) => {
      try {
        const rules = this.services.ruleEngine.getRules(req.query);
        res.json(rules);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/rules/:ruleId', (req, res) => {
      try {
        const rule = this.services.ruleEngine.getRule(req.params.ruleId);
        if (!rule) {
          return res.status(404).json({ error: 'Rule not found' });
        }
        res.json(rule);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.put('/api/rules/:ruleId', (req, res) => {
      try {
        const rule = this.services.ruleEngine.updateRule(req.params.ruleId, req.body);
        res.json(rule);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.delete('/api/rules/:ruleId', (req, res) => {
      try {
        this.services.ruleEngine.deleteRule(req.params.ruleId);
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/rules/:ruleId/enable', (req, res) => {
      try {
        const rule = this.services.ruleEngine.enableRule(req.params.ruleId);
        res.json(rule);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/rules/:ruleId/disable', (req, res) => {
      try {
        const rule = this.services.ruleEngine.disableRule(req.params.ruleId);
        res.json(rule);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/rules/metrics', (req, res) => {
      try {
        const metrics = this.services.ruleEngine.getMetrics();
        res.json(metrics);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Deployments Routes
    this.app.post('/api/deployments', async (req, res) => {
      try {
        const deployment = await this.services.deviceFleetManager.createDeployment(req.body);
        res.json(deployment);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/deployments/:deploymentId/start', async (req, res) => {
      try {
        const deployment = await this.services.deviceFleetManager.startDeployment(req.params.deploymentId);
        res.json(deployment);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/deployments', (req, res) => {
      try {
        const deployments = this.services.deviceFleetManager.getDeployments();
        res.json(deployments);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/deployments/:deploymentId', (req, res) => {
      try {
        const deployment = this.services.deviceFleetManager.getDeployment(req.params.deploymentId);
        if (!deployment) {
          return res.status(404).json({ error: 'Deployment not found' });
        }
        res.json(deployment);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Error handling middleware
    this.app.use((error, req, res, next) => {
      console.error('API Error:', error);
      res.status(500).json({ 
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? error.message : undefined
      });
    });

    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({ error: 'Endpoint not found' });
    });
  }

  setupWebSocketServer() {
    this.wss.on('connection', (ws, req) => {
      const connectionId = this.generateConnectionId();
      this.connections.set(connectionId, ws);
      
      console.log(`WebSocket client connected: ${connectionId}`);
      
      ws.on('message', (message) => {
        try {
          const data = JSON.parse(message);
          this.handleWebSocketMessage(ws, data);
        } catch (error) {
          ws.send(JSON.stringify({ error: 'Invalid JSON message' }));
        }
      });
      
      ws.on('close', () => {
        this.connections.delete(connectionId);
        console.log(`WebSocket client disconnected: ${connectionId}`);
      });
      
      // Send welcome message
      ws.send(JSON.stringify({
        type: 'welcome',
        connectionId,
        timestamp: new Date().toISOString()
      }));
    });
  }

  handleWebSocketMessage(ws, data) {
    switch (data.type) {
      case 'subscribe':
        this.handleSubscription(ws, data);
        break;
      case 'unsubscribe':
        this.handleUnsubscription(ws, data);
        break;
      case 'deviceData':
        this.handleDeviceData(data);
        break;
      default:
        ws.send(JSON.stringify({ error: `Unknown message type: ${data.type}` }));
    }
  }

  handleSubscription(ws, data) {
    ws.subscriptions = ws.subscriptions || new Set();
    ws.subscriptions.add(data.topic);
    
    ws.send(JSON.stringify({
      type: 'subscribed',
      topic: data.topic,
      timestamp: new Date().toISOString()
    }));
  }

  handleUnsubscription(ws, data) {
    if (ws.subscriptions) {
      ws.subscriptions.delete(data.topic);
    }
    
    ws.send(JSON.stringify({
      type: 'unsubscribed',
      topic: data.topic,
      timestamp: new Date().toISOString()
    }));
  }

  handleDeviceData(data) {
    // Process device data through rule engine
    if (data.deviceId && data.payload) {
      this.services.ruleEngine.processDeviceData(data.deviceId, data.payload, data.metadata);
      
      // Update device status in fleet manager
      this.services.deviceFleetManager.updateDeviceStatus(data.deviceId, {
        connectivity: { status: 'online', lastSeen: Date.now() },
        messagesReceived: 1
      });
    }
  }

  setupEventListeners() {
    // Rule Engine Events
    this.services.ruleEngine.on('ruleTriggered', (event) => {
      this.broadcastToSubscribers('rules/triggered', event);
    });

    this.services.ruleEngine.on('alert', (alert) => {
      this.broadcastToSubscribers('alerts', alert);
      console.log(`Alert: ${alert.level} - ${alert.message}`);
    });

    this.services.ruleEngine.on('mqttPublish', (message) => {
      this.services.mqttBroker.publish(message.topic, message.payload, {
        qos: message.qos,
        retain: message.retain
      });
    });

    this.services.ruleEngine.on('httpRequest', async (request) => {
      // Handle HTTP requests from rules
      try {
        const response = await this.makeHttpRequest(request);
        console.log(`HTTP request completed: ${request.method} ${request.url} - ${response.status}`);
      } catch (error) {
        console.error(`HTTP request failed: ${request.method} ${request.url} - ${error.message}`);
      }
    });

    this.services.ruleEngine.on('deviceCommand', (command) => {
      this.services.deviceFleetManager.sendCommand(command.deviceId, command.command, command.params);
    });

    // Device Fleet Manager Events
    this.services.deviceFleetManager.on('deviceRegistered', (device) => {
      this.broadcastToSubscribers('devices/registered', device);
    });

    this.services.deviceFleetManager.on('deviceStatusChanged', (event) => {
      this.broadcastToSubscribers('devices/status', event);
    });

    this.services.deviceFleetManager.on('deploymentProgress', (deployment) => {
      this.broadcastToSubscribers('deployments/progress', deployment);
    });

    this.services.deviceFleetManager.on('deploymentCompleted', (deployment) => {
      this.broadcastToSubscribers('deployments/completed', deployment);
    });

    // Device Twin Manager Events
    this.services.deviceTwinManager.on('twinUpdated', (event) => {
      this.broadcastToSubscribers('twins/updated', event);
    });

    this.services.deviceTwinManager.on('syncCompleted', (event) => {
      this.broadcastToSubscribers('twins/sync', event);
    });

    // Firmware OTA Events
    this.services.firmwareOTA.on('deploymentProgress', (deployment) => {
      this.broadcastToSubscribers('firmware/progress', deployment);
    });

    this.services.firmwareOTA.on('deploymentCompleted', (deployment) => {
      this.broadcastToSubscribers('firmware/completed', deployment);
    });

    // Edge Orchestrator Events
    this.services.edgeOrchestrator.on('functionDeployed', (event) => {
      this.broadcastToSubscribers('edge/deployed', event);
    });

    this.services.edgeOrchestrator.on('functionExecuted', (event) => {
      this.broadcastToSubscribers('edge/executed', event);
    });
  }

  broadcastToSubscribers(topic, data) {
    const message = JSON.stringify({
      type: 'event',
      topic,
      data,
      timestamp: new Date().toISOString()
    });

    for (const ws of this.connections.values()) {
      if (ws.readyState === WebSocket.OPEN && 
          ws.subscriptions && ws.subscriptions.has(topic)) {
        ws.send(message);
      }
    }
  }

  async makeHttpRequest(request) {
    const fetch = require('node-fetch');
    
    const response = await fetch(request.url, {
      method: request.method,
      headers: request.headers,
      body: request.body ? JSON.stringify(request.body) : undefined,
      timeout: request.timeout
    });
    
    return {
      status: response.status,
      headers: Object.fromEntries(response.headers),
      body: await response.text()
    };
  }

  generateConnectionId() {
    return `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  async start(port = 8110) {
    return new Promise((resolve, reject) => {
      try {
        this.server.listen(port, () => {
          console.log(`IoT Gateway started on port ${port}`);
          console.log(`WebSocket server available on ws://localhost:${port}`);
          console.log(`API documentation available at http://localhost:${port}/health`);
          resolve();
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  async stop() {
    // Stop all services
    if (this.services.mqttBroker) {
      await this.services.mqttBroker.stop();
    }
    
    // Close WebSocket connections
    for (const ws of this.connections.values()) {
      ws.terminate();
    }
    this.connections.clear();
    
    // Close HTTP server
    return new Promise((resolve) => {
      this.server.close(resolve);
    });
  }
}

// Start the application if this file is run directly
if (require.main === module) {
  const gateway = new IoTGatewayApp();
  
  gateway.start(process.env.PORT || 8110)
    .then(() => {
      console.log('IoT Gateway is running successfully');
    })
    .catch(error => {
      console.error('Failed to start IoT Gateway:', error);
      process.exit(1);
    });
  
  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\nShutting down IoT Gateway...');
    try {
      await gateway.stop();
      console.log('IoT Gateway stopped successfully');
      process.exit(0);
    } catch (error) {
      console.error('Error during shutdown:', error);
      process.exit(1);
    }
  });
}

module.exports = IoTGatewayApp;