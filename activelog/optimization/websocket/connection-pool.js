const WebSocket = require('ws');
const { EventEmitter } = require('events');
const crypto = require('crypto');

class WebSocketConnectionPool extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      // Pool configuration
      maxConnections: config.maxConnections || 1000,
      minConnections: config.minConnections || 10,
      connectionTimeout: config.connectionTimeout || 30000, // 30 seconds
      heartbeatInterval: config.heartbeatInterval || 30000, // 30 seconds
      
      // Connection limits per client
      maxConnectionsPerClient: config.maxConnectionsPerClient || 5,
      maxConnectionsPerIP: config.maxConnectionsPerIP || 20,
      
      // Message handling
      maxMessageSize: config.maxMessageSize || 1024 * 1024, // 1MB
      messageQueueSize: config.messageQueueSize || 1000,
      enableMessageCompression: config.enableMessageCompression ?? true,
      
      // Security
      enableRateLimit: config.enableRateLimit ?? true,
      rateLimitWindow: config.rateLimitWindow || 60000, // 1 minute
      rateLimitMax: config.rateLimitMax || 100, // messages per window
      
      // Performance
      enableConnectionReuse: config.enableConnectionReuse ?? true,
      enableLoadBalancing: config.enableLoadBalancing ?? true,
      loadBalancingStrategy: config.loadBalancingStrategy || 'round-robin', // round-robin, least-connections, weighted
      
      // Monitoring
      enableMetrics: config.enableMetrics ?? true,
      enableLogging: config.enableLogging ?? true,
      
      ...config
    };

    this.connections = new Map(); // connectionId -> connection
    this.clientConnections = new Map(); // clientId -> Set of connectionIds
    this.ipConnections = new Map(); // ip -> Set of connectionIds
    this.messageQueues = new Map(); // connectionId -> message queue
    this.rateLimiters = new Map(); // connectionId -> rate limiter
    
    this.stats = {
      totalConnections: 0,
      activeConnections: 0,
      totalMessages: 0,
      messagesPerSecond: 0,
      bytesTransferred: 0,
      connectionsCreated: 0,
      connectionsDestroyed: 0,
      errors: 0
    };

    this.heartbeatTimer = null;
    this.loadBalancerIndex = 0;
    
    this.startHeartbeat();
    this.startMetricsCollection();
  }

  // Create new WebSocket server
  createServer(options = {}) {
    const serverOptions = {
      port: options.port || 8080,
      perMessageDeflate: this.config.enableMessageCompression,
      maxPayload: this.config.maxMessageSize,
      ...options
    };

    const wss = new WebSocket.Server(serverOptions);
    
    wss.on('connection', (ws, req) => {
      this.handleNewConnection(ws, req);
    });

    wss.on('error', (error) => {
      this.emit('serverError', error);
    });

    this.emit('serverCreated', { port: serverOptions.port });
    return wss;
  }

  // Handle new connection
  handleNewConnection(ws, req) {
    const connectionId = crypto.randomUUID();
    const clientIP = this.getClientIP(req);
    const clientId = this.getClientId(req); // From auth headers, etc.

    // Check connection limits
    if (!this.canAcceptConnection(clientId, clientIP)) {
      ws.close(1008, 'Connection limit exceeded');
      return;
    }

    // Create connection object
    const connection = {
      id: connectionId,
      ws,
      clientId,
      clientIP,
      connectedAt: Date.now(),
      lastActivity: Date.now(),
      messageCount: 0,
      bytesReceived: 0,
      bytesSent: 0,
      isAlive: true,
      metadata: this.extractConnectionMetadata(req)
    };

    // Store connection
    this.connections.set(connectionId, connection);
    this.addToClientMap(clientId, connectionId);
    this.addToIPMap(clientIP, connectionId);
    
    // Initialize message queue
    this.messageQueues.set(connectionId, []);
    
    // Initialize rate limiter
    if (this.config.enableRateLimit) {
      this.rateLimiters.set(connectionId, {
        messages: [],
        windowStart: Date.now()
      });
    }

    // Setup connection handlers
    this.setupConnectionHandlers(connection);
    
    // Update stats
    this.stats.connectionsCreated++;
    this.stats.activeConnections = this.connections.size;
    
    this.emit('connectionCreated', connection);
  }

  // Setup WebSocket event handlers
  setupConnectionHandlers(connection) {
    const { ws, id } = connection;

    ws.on('message', (data) => {
      this.handleMessage(connection, data);
    });

    ws.on('close', (code, reason) => {
      this.handleDisconnection(connection, code, reason);
    });

    ws.on('error', (error) => {
      this.handleConnectionError(connection, error);
    });

    ws.on('pong', () => {
      connection.isAlive = true;
      connection.lastActivity = Date.now();
    });
  }

  // Handle incoming message
  async handleMessage(connection, data) {
    try {
      connection.lastActivity = Date.now();
      connection.messageCount++;
      connection.bytesReceived += data.length;
      
      this.stats.totalMessages++;
      this.stats.bytesTransferred += data.length;

      // Rate limiting
      if (this.config.enableRateLimit && !this.checkRateLimit(connection)) {
        connection.ws.close(1008, 'Rate limit exceeded');
        return;
      }

      // Message size validation
      if (data.length > this.config.maxMessageSize) {
        connection.ws.close(1009, 'Message too large');
        return;
      }

      // Parse message
      let message;
      try {
        message = JSON.parse(data.toString());
      } catch (parseError) {
        this.emit('messageParseError', { connection, error: parseError });
        return;
      }

      // Add to message queue if needed
      const queue = this.messageQueues.get(connection.id);
      if (queue && queue.length < this.config.messageQueueSize) {
        queue.push({
          message,
          timestamp: Date.now(),
          size: data.length
        });
      }

      this.emit('message', { connection, message, rawData: data });

    } catch (error) {
      this.handleConnectionError(connection, error);
    }
  }

  // Handle connection disconnection
  handleDisconnection(connection, code, reason) {
    const { id, clientId, clientIP } = connection;
    
    // Remove from maps
    this.connections.delete(id);
    this.removeFromClientMap(clientId, id);
    this.removeFromIPMap(clientIP, id);
    
    // Cleanup resources
    this.messageQueues.delete(id);
    this.rateLimiters.delete(id);
    
    // Update stats
    this.stats.connectionsDestroyed++;
    this.stats.activeConnections = this.connections.size;
    
    this.emit('connectionDestroyed', { connection, code, reason });
  }

  // Handle connection error
  handleConnectionError(connection, error) {
    this.stats.errors++;
    this.emit('connectionError', { connection, error });
    
    // Close connection if it's a fatal error
    if (connection.ws.readyState === WebSocket.OPEN) {
      connection.ws.close(1011, 'Internal error');
    }
  }

  // Check if new connection can be accepted
  canAcceptConnection(clientId, clientIP) {
    // Check total connection limit
    if (this.connections.size >= this.config.maxConnections) {
      return false;
    }

    // Check per-client limit
    const clientConnections = this.clientConnections.get(clientId);
    if (clientConnections && clientConnections.size >= this.config.maxConnectionsPerClient) {
      return false;
    }

    // Check per-IP limit
    const ipConnections = this.ipConnections.get(clientIP);
    if (ipConnections && ipConnections.size >= this.config.maxConnectionsPerIP) {
      return false;
    }

    return true;
  }

  // Rate limiting check
  checkRateLimit(connection) {
    const rateLimiter = this.rateLimiters.get(connection.id);
    if (!rateLimiter) return true;

    const now = Date.now();
    const windowStart = rateLimiter.windowStart;

    // Reset window if needed
    if (now - windowStart > this.config.rateLimitWindow) {
      rateLimiter.messages = [];
      rateLimiter.windowStart = now;
    }

    // Add current message
    rateLimiter.messages.push(now);

    // Check limit
    if (rateLimiter.messages.length > this.config.rateLimitMax) {
      return false;
    }

    return true;
  }

  // Send message to specific connection
  async sendToConnection(connectionId, message, options = {}) {
    const connection = this.connections.get(connectionId);
    if (!connection || connection.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      let data = typeof message === 'string' ? message : JSON.stringify(message);
      
      // Compress if enabled and beneficial
      if (this.config.enableMessageCompression && data.length > 1024) {
        // WebSocket per-message-deflate handles this automatically
      }

      connection.ws.send(data);
      connection.bytesSent += data.length;
      this.stats.bytesTransferred += data.length;
      
      return true;
    } catch (error) {
      this.handleConnectionError(connection, error);
      return false;
    }
  }

  // Broadcast message to all connections
  async broadcast(message, options = {}) {
    const data = typeof message === 'string' ? message : JSON.stringify(message);
    const results = [];

    for (const connection of this.connections.values()) {
      const sent = await this.sendToConnection(connection.id, data, options);
      results.push({ connectionId: connection.id, sent });
    }

    this.emit('broadcast', { message, results });
    return results;
  }

  // Send message to specific client (all their connections)
  async sendToClient(clientId, message, options = {}) {
    const connections = this.clientConnections.get(clientId);
    if (!connections || connections.size === 0) {
      return [];
    }

    const results = [];
    for (const connectionId of connections) {
      const sent = await this.sendToConnection(connectionId, message, options);
      results.push({ connectionId, sent });
    }

    return results;
  }

  // Send message with load balancing
  async sendToClientBalanced(clientId, message, options = {}) {
    const connections = this.clientConnections.get(clientId);
    if (!connections || connections.size === 0) {
      return null;
    }

    const connectionId = this.selectConnectionForLoadBalancing(Array.from(connections));
    return await this.sendToConnection(connectionId, message, options);
  }

  // Load balancing connection selection
  selectConnectionForLoadBalancing(connectionIds) {
    switch (this.config.loadBalancingStrategy) {
      case 'round-robin':
        const index = this.loadBalancerIndex % connectionIds.length;
        this.loadBalancerIndex++;
        return connectionIds[index];

      case 'least-connections':
        return connectionIds.reduce((best, current) => {
          const bestConn = this.connections.get(best);
          const currentConn = this.connections.get(current);
          
          return (currentConn.messageCount < bestConn.messageCount) ? current : best;
        });

      case 'weighted':
        // Implement weighted selection based on connection health
        return connectionIds.reduce((best, current) => {
          const bestConn = this.connections.get(best);
          const currentConn = this.connections.get(current);
          
          const bestScore = this.calculateConnectionScore(bestConn);
          const currentScore = this.calculateConnectionScore(currentConn);
          
          return (currentScore > bestScore) ? current : best;
        });

      default:
        return connectionIds[0];
    }
  }

  // Calculate connection health score for weighted load balancing
  calculateConnectionScore(connection) {
    const age = Date.now() - connection.connectedAt;
    const activity = Date.now() - connection.lastActivity;
    const messageRate = connection.messageCount / (age / 1000);
    
    // Higher score = better connection
    let score = 100;
    score -= Math.min(50, activity / 1000); // Penalize inactive connections
    score -= Math.min(30, messageRate); // Penalize overloaded connections
    
    return Math.max(0, score);
  }

  // Start heartbeat/ping mechanism
  startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      this.performHeartbeat();
    }, this.config.heartbeatInterval);
  }

  // Perform heartbeat check
  performHeartbeat() {
    const deadConnections = [];
    
    for (const connection of this.connections.values()) {
      if (!connection.isAlive) {
        deadConnections.push(connection);
        continue;
      }

      connection.isAlive = false;
      
      if (connection.ws.readyState === WebSocket.OPEN) {
        connection.ws.ping();
      }
    }

    // Close dead connections
    for (const connection of deadConnections) {
      connection.ws.close(1001, 'Connection timeout');
    }

    this.emit('heartbeat', { 
      totalConnections: this.connections.size, 
      deadConnections: deadConnections.length 
    });
  }

  // Start metrics collection
  startMetricsCollection() {
    if (!this.config.enableMetrics) return;

    setInterval(() => {
      this.calculateMetrics();
    }, 1000); // Every second
  }

  // Calculate real-time metrics
  calculateMetrics() {
    const now = Date.now();
    
    // Calculate messages per second
    const recentMessages = Array.from(this.connections.values())
      .reduce((total, conn) => total + conn.messageCount, 0);
    
    this.stats.messagesPerSecond = recentMessages; // Simplified - should track over time window
    
    // Update active connections
    this.stats.activeConnections = this.connections.size;
    
    this.emit('metricsUpdated', this.stats);
  }

  // Get client IP from request
  getClientIP(req) {
    return req.headers['x-forwarded-for']?.split(',')[0] || 
           req.headers['x-real-ip'] || 
           req.connection.remoteAddress ||
           req.socket.remoteAddress;
  }

  // Extract client ID from request
  getClientId(req) {
    // Extract from authorization header, query params, etc.
    const authHeader = req.headers.authorization;
    if (authHeader) {
      // Parse JWT or other auth token
      try {
        const token = authHeader.replace('Bearer ', '');
        // Decode token and extract user ID
        return this.decodeClientId(token);
      } catch (error) {
        // Fallback to IP if auth fails
      }
    }
    
    return this.getClientIP(req);
  }

  // Decode client ID from token (implement based on your auth system)
  decodeClientId(token) {
    // This should decode JWT or other auth token
    // For demo purposes, returning a hash of the token
    return crypto.createHash('md5').update(token).digest('hex');
  }

  // Extract connection metadata
  extractConnectionMetadata(req) {
    return {
      userAgent: req.headers['user-agent'],
      origin: req.headers.origin,
      referer: req.headers.referer,
      acceptLanguage: req.headers['accept-language'],
      timestamp: Date.now()
    };
  }

  // Helper methods for connection maps
  addToClientMap(clientId, connectionId) {
    if (!this.clientConnections.has(clientId)) {
      this.clientConnections.set(clientId, new Set());
    }
    this.clientConnections.get(clientId).add(connectionId);
  }

  removeFromClientMap(clientId, connectionId) {
    const connections = this.clientConnections.get(clientId);
    if (connections) {
      connections.delete(connectionId);
      if (connections.size === 0) {
        this.clientConnections.delete(clientId);
      }
    }
  }

  addToIPMap(ip, connectionId) {
    if (!this.ipConnections.has(ip)) {
      this.ipConnections.set(ip, new Set());
    }
    this.ipConnections.get(ip).add(connectionId);
  }

  removeFromIPMap(ip, connectionId) {
    const connections = this.ipConnections.get(ip);
    if (connections) {
      connections.delete(connectionId);
      if (connections.size === 0) {
        this.ipConnections.delete(ip);
      }
    }
  }

  // Get connection statistics
  getConnectionStats() {
    return {
      ...this.stats,
      poolUtilization: `${((this.stats.activeConnections / this.config.maxConnections) * 100).toFixed(2)}%`,
      avgMessagesPerConnection: this.stats.activeConnections > 0 
        ? (this.stats.totalMessages / this.stats.activeConnections).toFixed(2) 
        : 0,
      connectionsByClient: this.clientConnections.size,
      connectionsByIP: this.ipConnections.size
    };
  }

  // Get detailed connection info
  getConnectionDetails(connectionId) {
    const connection = this.connections.get(connectionId);
    if (!connection) return null;

    return {
      id: connection.id,
      clientId: connection.clientId,
      clientIP: connection.clientIP,
      connectedAt: new Date(connection.connectedAt).toISOString(),
      uptime: Date.now() - connection.connectedAt,
      lastActivity: new Date(connection.lastActivity).toISOString(),
      messageCount: connection.messageCount,
      bytesReceived: connection.bytesReceived,
      bytesSent: connection.bytesSent,
      isAlive: connection.isAlive,
      state: connection.ws.readyState,
      metadata: connection.metadata
    };
  }

  // Close specific connection
  closeConnection(connectionId, code = 1000, reason = 'Server initiated close') {
    const connection = this.connections.get(connectionId);
    if (connection && connection.ws.readyState === WebSocket.OPEN) {
      connection.ws.close(code, reason);
      return true;
    }
    return false;
  }

  // Close all connections for a client
  closeClientConnections(clientId, code = 1000, reason = 'Client terminated') {
    const connections = this.clientConnections.get(clientId);
    if (!connections) return 0;

    let closed = 0;
    for (const connectionId of connections) {
      if (this.closeConnection(connectionId, code, reason)) {
        closed++;
      }
    }

    return closed;
  }

  // Health check
  async healthCheck() {
    const healthy = this.stats.activeConnections < this.config.maxConnections * 0.9;
    
    return {
      healthy,
      status: healthy ? 'ok' : 'warning',
      stats: this.getConnectionStats(),
      thresholds: {
        maxConnections: this.config.maxConnections,
        currentUtilization: this.stats.activeConnections / this.config.maxConnections
      }
    };
  }

  // Graceful shutdown
  async shutdown() {
    console.log('Shutting down WebSocket connection pool...');
    
    // Stop heartbeat
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    // Close all connections gracefully
    const closePromises = [];
    for (const connection of this.connections.values()) {
      if (connection.ws.readyState === WebSocket.OPEN) {
        connection.ws.close(1001, 'Server shutdown');
        closePromises.push(
          new Promise(resolve => {
            connection.ws.on('close', resolve);
            setTimeout(resolve, 5000); // Force close after 5 seconds
          })
        );
      }
    }

    await Promise.all(closePromises);
    
    // Clear all data structures
    this.connections.clear();
    this.clientConnections.clear();
    this.ipConnections.clear();
    this.messageQueues.clear();
    this.rateLimiters.clear();
    
    this.emit('shutdown');
  }
}

// WebSocket client pool for outgoing connections
class WebSocketClientPool extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      maxClients: config.maxClients || 100,
      reconnectInterval: config.reconnectInterval || 5000,
      maxReconnectAttempts: config.maxReconnectAttempts || 10,
      connectionTimeout: config.connectionTimeout || 30000,
      enableAutoReconnect: config.enableAutoReconnect ?? true,
      ...config
    };

    this.clients = new Map();
    this.reconnectTimers = new Map();
  }

  // Create client connection
  async createClient(url, options = {}) {
    const clientId = options.id || crypto.randomUUID();
    
    if (this.clients.has(clientId)) {
      throw new Error(`Client ${clientId} already exists`);
    }

    const client = {
      id: clientId,
      url,
      ws: null,
      options,
      reconnectAttempts: 0,
      connected: false,
      lastReconnect: 0
    };

    this.clients.set(clientId, client);
    await this.connectClient(client);
    
    return clientId;
  }

  // Connect individual client
  async connectClient(client) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(client.url, client.options.protocols, client.options);
      
      const timeout = setTimeout(() => {
        ws.terminate();
        reject(new Error('Connection timeout'));
      }, this.config.connectionTimeout);

      ws.on('open', () => {
        clearTimeout(timeout);
        client.ws = ws;
        client.connected = true;
        client.reconnectAttempts = 0;
        
        this.setupClientHandlers(client);
        this.emit('clientConnected', client);
        resolve(client);
      });

      ws.on('error', (error) => {
        clearTimeout(timeout);
        this.handleClientError(client, error);
        reject(error);
      });
    });
  }

  // Setup client event handlers
  setupClientHandlers(client) {
    const { ws } = client;

    ws.on('message', (data) => {
      this.emit('clientMessage', { client, data });
    });

    ws.on('close', () => {
      client.connected = false;
      this.emit('clientDisconnected', client);
      
      if (this.config.enableAutoReconnect) {
        this.scheduleReconnect(client);
      }
    });

    ws.on('error', (error) => {
      this.handleClientError(client, error);
    });
  }

  // Handle client errors
  handleClientError(client, error) {
    client.connected = false;
    this.emit('clientError', { client, error });
    
    if (this.config.enableAutoReconnect) {
      this.scheduleReconnect(client);
    }
  }

  // Schedule reconnection
  scheduleReconnect(client) {
    if (client.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.emit('clientReconnectFailed', client);
      return;
    }

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, client.reconnectAttempts),
      30000 // Max 30 seconds
    );

    const timer = setTimeout(() => {
      client.reconnectAttempts++;
      client.lastReconnect = Date.now();
      
      this.connectClient(client).catch(() => {
        // Reconnection will be scheduled again by error handler
      });
    }, delay);

    this.reconnectTimers.set(client.id, timer);
  }

  // Send message via client
  async sendViaClient(clientId, message) {
    const client = this.clients.get(clientId);
    if (!client || !client.connected) {
      return false;
    }

    try {
      const data = typeof message === 'string' ? message : JSON.stringify(message);
      client.ws.send(data);
      return true;
    } catch (error) {
      this.handleClientError(client, error);
      return false;
    }
  }

  // Close client connection
  closeClient(clientId) {
    const client = this.clients.get(clientId);
    if (!client) return false;

    // Cancel reconnect timer
    const timer = this.reconnectTimers.get(clientId);
    if (timer) {
      clearTimeout(timer);
      this.reconnectTimers.delete(clientId);
    }

    // Close WebSocket
    if (client.ws) {
      client.ws.close();
    }

    this.clients.delete(clientId);
    this.emit('clientRemoved', client);
    
    return true;
  }

  // Get client stats
  getClientStats() {
    const connected = Array.from(this.clients.values()).filter(c => c.connected).length;
    const reconnecting = this.reconnectTimers.size;
    
    return {
      totalClients: this.clients.size,
      connectedClients: connected,
      reconnectingClients: reconnecting,
      disconnectedClients: this.clients.size - connected
    };
  }
}

module.exports = {
  WebSocketConnectionPool,
  WebSocketClientPool
};