const Aedes = require('aedes');
const { EventEmitter } = require('events');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

class MqttBroker extends EventEmitter {
  constructor(options = {}) {
    super();
    this.port = options.port || 1883;
    this.wsPort = options.wsPort || 8883;
    this.options = {
      id: 'activelog-iot-gateway',
      heartbeatInterval: 30000,
      connectTimeout: 10000,
      ...options
    };
    
    this.broker = null;
    this.server = null;
    this.wsServer = null;
    this.clients = new Map();
    this.subscriptions = new Map();
    this.messageStats = new Map();
    this.authentication = new Map();
    this.acl = new Map();
    
    this.initializeBroker();
  }

  initializeBroker() {
    this.broker = new Aedes({
      id: this.options.id,
      heartbeatInterval: this.options.heartbeatInterval,
      connectTimeout: this.options.connectTimeout,
      authenticate: this.authenticate.bind(this),
      authorizePublish: this.authorizePublish.bind(this),
      authorizeSubscribe: this.authorizeSubscribe.bind(this),
      published: this.onPublished.bind(this)
    });

    this.setupBrokerEvents();
    this.initializeSystemTopics();
  }

  setupBrokerEvents() {
    this.broker.on('client', (client) => {
      this.onClientConnected(client);
    });

    this.broker.on('clientDisconnect', (client) => {
      this.onClientDisconnected(client);
    });

    this.broker.on('clientError', (client, error) => {
      this.onClientError(client, error);
    });

    this.broker.on('subscribe', (subscriptions, client) => {
      this.onClientSubscribe(subscriptions, client);
    });

    this.broker.on('unsubscribe', (subscriptions, client) => {
      this.onClientUnsubscribe(subscriptions, client);
    });

    this.broker.on('publish', (packet, client) => {
      this.onMessagePublished(packet, client);
    });

    this.broker.on('ping', (packet, client) => {
      this.onClientPing(client);
    });
  }

  initializeSystemTopics() {
    // System topics for IoT gateway management
    this.systemTopics = {
      device: {
        status: '$system/device/{deviceId}/status',
        config: '$system/device/{deviceId}/config',
        twin: '$system/device/{deviceId}/twin',
        ota: '$system/device/{deviceId}/ota',
        logs: '$system/device/{deviceId}/logs'
      },
      gateway: {
        status: '$system/gateway/status',
        metrics: '$system/gateway/metrics',
        rules: '$system/gateway/rules'
      }
    };
  }

  async start() {
    return new Promise((resolve, reject) => {
      try {
        // Start TCP MQTT server
        this.server = require('net').createServer(this.broker.handle);
        this.server.listen(this.port, () => {
          console.log(`📡 MQTT Broker started on port ${this.port}`);
          
          // Start WebSocket MQTT server
          this.startWebSocketServer();
          
          // Publish gateway status
          this.publishGatewayStatus('online');
          
          resolve();
        });

        this.server.on('error', (error) => {
          console.error('MQTT server error:', error);
          reject(error);
        });

      } catch (error) {
        reject(error);
      }
    });
  }

  startWebSocketServer() {
    const WebSocket = require('ws');
    this.wsServer = new WebSocket.Server({ port: this.wsPort });
    
    this.wsServer.on('connection', (ws) => {
      const stream = require('websocket-stream')(ws);
      this.broker.handle(stream);
    });

    console.log(`🌐 MQTT WebSocket server started on port ${this.wsPort}`);
  }

  async stop() {
    return new Promise((resolve) => {
      this.publishGatewayStatus('offline');
      
      if (this.wsServer) {
        this.wsServer.close();
      }
      
      if (this.server) {
        this.server.close(() => {
          if (this.broker) {
            this.broker.close(() => {
              console.log('🛑 MQTT Broker stopped');
              resolve();
            });
          } else {
            resolve();
          }
        });
      } else {
        resolve();
      }
    });
  }

  // Authentication
  authenticate(client, username, password, callback) {
    const deviceId = client.id;
    const passwordString = password ? password.toString() : '';

    // Check if device is registered
    if (!this.authentication.has(deviceId)) {
      console.log(`❌ Authentication failed: Device ${deviceId} not registered`);
      return callback(new Error('Device not registered'), false);
    }

    const deviceAuth = this.authentication.get(deviceId);
    
    // JWT token authentication
    if (deviceAuth.authType === 'jwt') {
      try {
        const decoded = jwt.verify(passwordString, deviceAuth.secret);
        if (decoded.deviceId === deviceId) {
          console.log(`✅ JWT authentication successful for device ${deviceId}`);
          return callback(null, true);
        }
      } catch (error) {
        console.log(`❌ JWT authentication failed for device ${deviceId}:`, error.message);
        return callback(new Error('Invalid JWT token'), false);
      }
    }
    
    // Certificate-based authentication
    else if (deviceAuth.authType === 'certificate') {
      // In real implementation, verify client certificate
      if (client.conn && client.conn.getPeerCertificate) {
        const cert = client.conn.getPeerCertificate();
        if (this.verifyCertificate(cert, deviceAuth)) {
          console.log(`✅ Certificate authentication successful for device ${deviceId}`);
          return callback(null, true);
        }
      }
    }
    
    // PSK (Pre-shared key) authentication
    else if (deviceAuth.authType === 'psk') {
      const expectedPassword = crypto
        .createHmac('sha256', deviceAuth.secret)
        .update(deviceId)
        .digest('hex');
      
      if (passwordString === expectedPassword) {
        console.log(`✅ PSK authentication successful for device ${deviceId}`);
        return callback(null, true);
      }
    }

    console.log(`❌ Authentication failed for device ${deviceId}`);
    callback(new Error('Authentication failed'), false);
  }

  authorizePublish(client, packet, callback) {
    const deviceId = client.id;
    const topic = packet.topic;

    // Check device ACL
    if (this.acl.has(deviceId)) {
      const deviceAcl = this.acl.get(deviceId);
      const allowed = this.checkTopicPermission(topic, deviceAcl.publish || []);
      
      if (!allowed) {
        console.log(`❌ Publish denied: Device ${deviceId} to topic ${topic}`);
        return callback(new Error('Publish not authorized'));
      }
    }

    // Allow system topics for registered devices
    if (topic.startsWith('$system/device/' + deviceId)) {
      return callback(null);
    }

    callback(null);
  }

  authorizeSubscribe(client, subscription, callback) {
    const deviceId = client.id;
    const topic = subscription.topic;

    // Check device ACL
    if (this.acl.has(deviceId)) {
      const deviceAcl = this.acl.get(deviceId);
      const allowed = this.checkTopicPermission(topic, deviceAcl.subscribe || []);
      
      if (!allowed) {
        console.log(`❌ Subscribe denied: Device ${deviceId} to topic ${topic}`);
        return callback(new Error('Subscribe not authorized'));
      }
    }

    // Allow system topics for registered devices
    if (topic.startsWith('$system/device/' + deviceId)) {
      return callback(null, subscription);
    }

    callback(null, subscription);
  }

  checkTopicPermission(topic, allowedPatterns) {
    return allowedPatterns.some(pattern => {
      // Convert MQTT wildcards to regex
      const regexPattern = pattern
        .replace(/\+/g, '[^/]+')
        .replace(/#$/, '.*')
        .replace(/\//g, '\\/');
      
      const regex = new RegExp(`^${regexPattern}$`);
      return regex.test(topic);
    });
  }

  verifyCertificate(cert, deviceAuth) {
    // In real implementation, verify certificate against CA and device fingerprint
    return cert && cert.fingerprint === deviceAuth.fingerprint;
  }

  // Event handlers
  onClientConnected(client) {
    const deviceId = client.id;
    const clientInfo = {
      deviceId,
      connected: true,
      connectedAt: new Date(),
      lastSeen: new Date(),
      ip: client.conn ? client.conn.remoteAddress : 'unknown',
      version: client.version || 4,
      keepAlive: client.keepalive || 60,
      clean: client.clean || false
    };

    this.clients.set(deviceId, clientInfo);
    console.log(`📱 Device connected: ${deviceId}`);

    // Publish device status
    this.publishDeviceStatus(deviceId, 'online');

    this.emit('device_connected', clientInfo);
  }

  onClientDisconnected(client) {
    const deviceId = client.id;
    const clientInfo = this.clients.get(deviceId);
    
    if (clientInfo) {
      clientInfo.connected = false;
      clientInfo.disconnectedAt = new Date();
      console.log(`📱 Device disconnected: ${deviceId}`);
      
      // Publish device status
      this.publishDeviceStatus(deviceId, 'offline');
      
      this.emit('device_disconnected', clientInfo);
    }
  }

  onClientError(client, error) {
    const deviceId = client.id;
    console.error(`❌ Client error for ${deviceId}:`, error.message);
    
    this.emit('device_error', { deviceId, error });
  }

  onClientSubscribe(subscriptions, client) {
    const deviceId = client.id;
    const clientInfo = this.clients.get(deviceId);
    
    if (clientInfo) {
      clientInfo.lastSeen = new Date();
      
      subscriptions.forEach(sub => {
        console.log(`📨 Device ${deviceId} subscribed to: ${sub.topic}`);
        
        if (!this.subscriptions.has(deviceId)) {
          this.subscriptions.set(deviceId, new Set());
        }
        this.subscriptions.get(deviceId).add(sub.topic);
      });
    }

    this.emit('device_subscribed', { deviceId, subscriptions });
  }

  onClientUnsubscribe(subscriptions, client) {
    const deviceId = client.id;
    
    subscriptions.forEach(topic => {
      console.log(`📭 Device ${deviceId} unsubscribed from: ${topic}`);
      
      if (this.subscriptions.has(deviceId)) {
        this.subscriptions.get(deviceId).delete(topic);
      }
    });

    this.emit('device_unsubscribed', { deviceId, subscriptions });
  }

  onMessagePublished(packet, client) {
    const deviceId = client ? client.id : 'system';
    const topic = packet.topic;
    const payload = packet.payload;

    // Update client last seen
    if (client) {
      const clientInfo = this.clients.get(deviceId);
      if (clientInfo) {
        clientInfo.lastSeen = new Date();
      }
    }

    // Update message statistics
    this.updateMessageStats(deviceId, topic, 'published');

    console.log(`📤 Message published by ${deviceId} to ${topic}:`, payload.length, 'bytes');

    this.emit('message_published', { deviceId, topic, payload, timestamp: new Date() });
  }

  onPublished(packet, client) {
    // This is called after the message is published to subscribers
    this.updateMessageStats(packet.topic, 'delivered');
  }

  onClientPing(client) {
    const deviceId = client.id;
    const clientInfo = this.clients.get(deviceId);
    
    if (clientInfo) {
      clientInfo.lastSeen = new Date();
    }
  }

  // Device management
  registerDevice(deviceConfig) {
    const { deviceId, authType, secret, acl, metadata } = deviceConfig;

    // Store authentication info
    this.authentication.set(deviceId, {
      authType: authType || 'psk',
      secret,
      registeredAt: new Date(),
      metadata: metadata || {}
    });

    // Store ACL
    if (acl) {
      this.acl.set(deviceId, {
        publish: acl.publish || [`devices/${deviceId}/+`, `$system/device/${deviceId}/+`],
        subscribe: acl.subscribe || [`devices/${deviceId}/+`, `$system/device/${deviceId}/+`]
      });
    }

    console.log(`📝 Device registered: ${deviceId}`);
    return { deviceId, registered: true };
  }

  unregisterDevice(deviceId) {
    this.authentication.delete(deviceId);
    this.acl.delete(deviceId);
    this.clients.delete(deviceId);
    this.subscriptions.delete(deviceId);
    
    // Disconnect if currently connected
    const client = this.broker.clients[deviceId];
    if (client) {
      client.close();
    }

    console.log(`🗑️ Device unregistered: ${deviceId}`);
    return { deviceId, unregistered: true };
  }

  // Message publishing
  publishToDevice(deviceId, topic, payload, options = {}) {
    const fullTopic = topic.includes('{deviceId}') 
      ? topic.replace('{deviceId}', deviceId)
      : `devices/${deviceId}/${topic}`;

    this.broker.publish({
      topic: fullTopic,
      payload: Buffer.from(JSON.stringify(payload)),
      qos: options.qos || 1,
      retain: options.retain || false
    }, (error) => {
      if (error) {
        console.error(`❌ Failed to publish to device ${deviceId}:`, error);
      } else {
        console.log(`📤 Published to device ${deviceId} on topic ${fullTopic}`);
      }
    });
  }

  publishToTopic(topic, payload, options = {}) {
    this.broker.publish({
      topic,
      payload: Buffer.from(typeof payload === 'string' ? payload : JSON.stringify(payload)),
      qos: options.qos || 1,
      retain: options.retain || false
    }, (error) => {
      if (error) {
        console.error(`❌ Failed to publish to topic ${topic}:`, error);
      } else {
        console.log(`📤 Published to topic ${topic}`);
      }
    });
  }

  publishDeviceStatus(deviceId, status) {
    const topic = this.systemTopics.device.status.replace('{deviceId}', deviceId);
    const payload = {
      deviceId,
      status,
      timestamp: new Date().toISOString()
    };

    this.publishToTopic(topic, payload, { retain: true });
  }

  publishGatewayStatus(status) {
    const topic = this.systemTopics.gateway.status;
    const payload = {
      gatewayId: this.options.id,
      status,
      timestamp: new Date().toISOString(),
      connectedDevices: this.getConnectedDevicesCount(),
      uptime: process.uptime()
    };

    this.publishToTopic(topic, payload, { retain: true });
  }

  // Statistics and monitoring
  updateMessageStats(deviceId, topic, type) {
    const key = `${deviceId}:${type}`;
    
    if (!this.messageStats.has(key)) {
      this.messageStats.set(key, { count: 0, lastUpdate: new Date() });
    }

    const stats = this.messageStats.get(key);
    stats.count++;
    stats.lastUpdate = new Date();
  }

  getConnectedDevicesCount() {
    return Array.from(this.clients.values()).filter(client => client.connected).length;
  }

  getConnectedDevices() {
    return Array.from(this.clients.values()).filter(client => client.connected);
  }

  getDeviceInfo(deviceId) {
    const clientInfo = this.clients.get(deviceId);
    const subscriptions = this.subscriptions.get(deviceId);
    const auth = this.authentication.get(deviceId);

    return {
      deviceId,
      client: clientInfo,
      subscriptions: subscriptions ? Array.from(subscriptions) : [],
      auth: auth ? { authType: auth.authType, registeredAt: auth.registeredAt } : null
    };
  }

  getBrokerStats() {
    const connectedDevices = this.getConnectedDevicesCount();
    const totalDevices = this.clients.size;
    const totalSubscriptions = Array.from(this.subscriptions.values())
      .reduce((total, subs) => total + subs.size, 0);

    return {
      connectedDevices,
      totalDevices,
      totalSubscriptions,
      messageStats: Object.fromEntries(this.messageStats),
      uptime: process.uptime(),
      timestamp: new Date().toISOString()
    };
  }

  // Rule engine integration
  addMessageHandler(pattern, handler) {
    this.on('message_published', (data) => {
      if (this.matchesTopic(data.topic, pattern)) {
        handler(data);
      }
    });
  }

  matchesTopic(topic, pattern) {
    const regexPattern = pattern
      .replace(/\+/g, '[^/]+')
      .replace(/#$/, '.*')
      .replace(/\//g, '\\/');
    
    const regex = new RegExp(`^${regexPattern}$`);
    return regex.test(topic);
  }

  // Bulk operations
  publishToDeviceGroup(deviceIds, topic, payload, options = {}) {
    deviceIds.forEach(deviceId => {
      this.publishToDevice(deviceId, topic, payload, options);
    });
  }

  disconnectDevice(deviceId, reason = 'Administrative disconnect') {
    const client = this.broker.clients[deviceId];
    if (client) {
      console.log(`🚫 Disconnecting device ${deviceId}: ${reason}`);
      client.close();
      return true;
    }
    return false;
  }

  // Security operations
  rotateDeviceSecret(deviceId, newSecret) {
    if (this.authentication.has(deviceId)) {
      const auth = this.authentication.get(deviceId);
      auth.secret = newSecret;
      auth.secretUpdatedAt = new Date();
      
      console.log(`🔄 Secret rotated for device ${deviceId}`);
      return true;
    }
    return false;
  }

  updateDeviceACL(deviceId, newAcl) {
    this.acl.set(deviceId, newAcl);
    console.log(`🔐 ACL updated for device ${deviceId}`);
    return true;
  }
}

module.exports = MqttBroker;