import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import axios from 'axios';
import logger from '../lib/logger.js';
import { ProxyManager } from './ProxyManager.js';
import { RequestTransformer } from './RequestTransformer.js';
import { ResponseTransformer } from './ResponseTransformer.js';
import { AuthenticationManager } from './AuthenticationManager.js';
import { CacheManager } from './CacheManager.js';
import { MetricsCollector } from './MetricsCollector.js';

/**
 * API Wrapper for non-migrated applications
 * Provides seamless integration with legacy systems during migration
 */
export class APIWrapper {
  constructor(options = {}) {
    this.options = {
      port: 8317,
      enableCors: true,
      enableCompression: true,
      enableRateLimit: true,
      enableAuthentication: true,
      enableCaching: true,
      enableMetrics: true,
      enableTransformations: true,
      timeout: 30000,
      retries: 3,
      circuitBreaker: true,
      loadBalancing: true,
      ...options
    };

    this.app = express();
    this.server = null;
    this.isRunning = false;
    
    // Initialize components
    this.proxyManager = new ProxyManager(this.options);
    this.requestTransformer = new RequestTransformer(this.options);
    this.responseTransformer = new ResponseTransformer(this.options);
    this.authManager = new AuthenticationManager(this.options);
    this.cacheManager = new CacheManager(this.options);
    this.metricsCollector = new MetricsCollector(this.options);
    
    // Store registered endpoints and services
    this.registeredServices = new Map();
    this.endpointMappings = new Map();
    this.transformationRules = new Map();
    this.authenticationRules = new Map();
    
    this.setupMiddleware();
    this.setupRoutes();
  }

  /**
   * Setup Express middleware
   */
  setupMiddleware() {
    // Security middleware
    this.app.use(helmet({
      contentSecurityPolicy: false, // Allow for proxying
      crossOriginEmbedderPolicy: false
    }));

    // CORS
    if (this.options.enableCors) {
      this.app.use(cors({
        origin: true,
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key', 'X-Requested-With']
      }));
    }

    // Compression
    if (this.options.enableCompression) {
      this.app.use(compression());
    }

    // Rate limiting
    if (this.options.enableRateLimit) {
      const limiter = rateLimit({
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 1000, // limit each IP to 1000 requests per windowMs
        message: {
          error: 'Too many requests',
          message: 'Rate limit exceeded. Please try again later.'
        },
        standardHeaders: true,
        legacyHeaders: false,
        skip: (req) => {
          // Skip rate limiting for health checks
          return req.path === '/health' || req.path === '/status';
        }
      });
      this.app.use(limiter);
    }

    // Body parsing
    this.app.use(express.json({ limit: '50mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));

    // Request logging and metrics
    this.app.use((req, res, next) => {
      req.startTime = Date.now();
      
      if (this.options.enableMetrics) {
        this.metricsCollector.recordRequest(req);
      }
      
      logger.info(`${req.method} ${req.path}`, {
        userAgent: req.get('user-agent'),
        ip: req.ip,
        headers: req.headers
      });
      
      next();
    });

    // Authentication middleware
    if (this.options.enableAuthentication) {
      this.app.use((req, res, next) => {
        this.authManager.authenticate(req, res, next);
      });
    }
  }

  /**
   * Setup API routes
   */
  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        services: Array.from(this.registeredServices.keys()),
        version: '1.0.0'
      });
    });

    // Status endpoint
    this.app.get('/status', (req, res) => {
      res.json({
        status: 'running',
        services: Object.fromEntries(
          Array.from(this.registeredServices.entries()).map(([name, service]) => [
            name,
            {
              url: service.baseUrl,
              healthy: service.healthy || true,
              lastCheck: service.lastCheck || new Date().toISOString()
            }
          ])
        ),
        metrics: this.options.enableMetrics ? this.metricsCollector.getMetrics() : null
      });
    });

    // Service registration endpoint
    this.app.post('/api/services/register', (req, res) => {
      try {
        const { name, baseUrl, endpoints, authentication, transformations } = req.body;
        
        if (!name || !baseUrl) {
          return res.status(400).json({
            error: 'Missing required fields: name, baseUrl'
          });
        }

        this.registerService(name, {
          baseUrl,
          endpoints: endpoints || [],
          authentication: authentication || {},
          transformations: transformations || {}
        });

        res.json({
          message: `Service ${name} registered successfully`,
          serviceId: name
        });
      } catch (error) {
        logger.error('Error registering service:', error);
        res.status(500).json({
          error: 'Failed to register service',
          message: error.message
        });
      }
    });

    // Service deregistration endpoint
    this.app.delete('/api/services/:serviceName', (req, res) => {
      try {
        const { serviceName } = req.params;
        
        if (this.registeredServices.has(serviceName)) {
          this.deregisterService(serviceName);
          res.json({
            message: `Service ${serviceName} deregistered successfully`
          });
        } else {
          res.status(404).json({
            error: 'Service not found'
          });
        }
      } catch (error) {
        logger.error('Error deregistering service:', error);
        res.status(500).json({
          error: 'Failed to deregister service',
          message: error.message
        });
      }
    });

    // Endpoint mapping endpoint
    this.app.post('/api/mappings', (req, res) => {
      try {
        const { path, serviceName, targetPath, method, transformations, authentication } = req.body;
        
        this.mapEndpoint(path, {
          serviceName,
          targetPath: targetPath || path,
          method: method || 'ALL',
          transformations: transformations || {},
          authentication: authentication || {}
        });

        res.json({
          message: `Endpoint mapping created: ${method || 'ALL'} ${path} -> ${serviceName}${targetPath || path}`
        });
      } catch (error) {
        logger.error('Error creating endpoint mapping:', error);
        res.status(500).json({
          error: 'Failed to create endpoint mapping',
          message: error.message
        });
      }
    });

    // Catch-all proxy route (must be last)
    this.app.all('*', async (req, res) => {
      await this.handleProxyRequest(req, res);
    });

    // Error handling middleware
    this.app.use((error, req, res, next) => {
      logger.error('API Wrapper error:', error);
      
      if (this.options.enableMetrics) {
        this.metricsCollector.recordError(req, error);
      }

      res.status(error.status || 500).json({
        error: 'Internal server error',
        message: error.message || 'An unexpected error occurred',
        requestId: req.id,
        timestamp: new Date().toISOString()
      });
    });
  }

  /**
   * Register a service for proxying
   */
  registerService(name, config) {
    logger.info(`Registering service: ${name}`);
    
    this.registeredServices.set(name, {
      name,
      baseUrl: config.baseUrl,
      endpoints: config.endpoints || [],
      authentication: config.authentication || {},
      transformations: config.transformations || {},
      healthy: true,
      lastCheck: new Date().toISOString(),
      requestCount: 0,
      errorCount: 0
    });

    // Register individual endpoints if provided
    if (config.endpoints && config.endpoints.length > 0) {
      config.endpoints.forEach(endpoint => {
        this.mapEndpoint(endpoint.path, {
          serviceName: name,
          targetPath: endpoint.targetPath || endpoint.path,
          method: endpoint.method || 'ALL',
          transformations: endpoint.transformations || config.transformations || {},
          authentication: endpoint.authentication || config.authentication || {}
        });
      });
    }
  }

  /**
   * Deregister a service
   */
  deregisterService(name) {
    logger.info(`Deregistering service: ${name}`);
    
    this.registeredServices.delete(name);
    
    // Remove endpoint mappings for this service
    for (const [path, mapping] of this.endpointMappings) {
      if (mapping.serviceName === name) {
        this.endpointMappings.delete(path);
      }
    }
  }

  /**
   * Map an endpoint to a service
   */
  mapEndpoint(path, mapping) {
    const key = `${mapping.method}:${path}`;
    logger.info(`Mapping endpoint: ${key} -> ${mapping.serviceName}${mapping.targetPath}`);
    
    this.endpointMappings.set(key, mapping);
    
    // Also add a generic mapping for ALL methods if method is ALL
    if (mapping.method === 'ALL') {
      ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'].forEach(method => {
        this.endpointMappings.set(`${method}:${path}`, mapping);
      });
    }
  }

  /**
   * Handle proxy requests
   */
  async handleProxyRequest(req, res) {
    const startTime = Date.now();
    
    try {
      // Find endpoint mapping
      const mapping = this.findEndpointMapping(req);
      
      if (!mapping) {
        return res.status(404).json({
          error: 'Endpoint not found',
          message: `No service mapped for ${req.method} ${req.path}`,
          availableEndpoints: Array.from(this.endpointMappings.keys())
        });
      }

      // Get target service
      const service = this.registeredServices.get(mapping.serviceName);
      
      if (!service) {
        return res.status(503).json({
          error: 'Service unavailable',
          message: `Service ${mapping.serviceName} is not registered`
        });
      }

      // Transform request if needed
      let transformedReq = req;
      if (this.options.enableTransformations && mapping.transformations) {
        transformedReq = await this.requestTransformer.transform(req, mapping.transformations);
      }

      // Check cache
      let cacheKey = null;
      if (this.options.enableCaching && req.method === 'GET') {
        cacheKey = this.cacheManager.generateKey(req);
        const cachedResponse = await this.cacheManager.get(cacheKey);
        
        if (cachedResponse) {
          logger.info(`Cache hit for ${req.method} ${req.path}`);
          return res.json(cachedResponse);
        }
      }

      // Proxy the request
      const response = await this.proxyManager.proxyRequest(
        transformedReq,
        service.baseUrl,
        mapping.targetPath,
        {
          timeout: this.options.timeout,
          retries: this.options.retries
        }
      );

      // Transform response if needed
      let transformedResponse = response.data;
      if (this.options.enableTransformations && mapping.transformations.response) {
        transformedResponse = await this.responseTransformer.transform(response.data, mapping.transformations.response);
      }

      // Cache response if applicable
      if (cacheKey && req.method === 'GET') {
        await this.cacheManager.set(cacheKey, transformedResponse);
      }

      // Update service metrics
      service.requestCount++;
      service.lastCheck = new Date().toISOString();

      // Record metrics
      if (this.options.enableMetrics) {
        this.metricsCollector.recordResponse(req, {
          status: response.status,
          responseTime: Date.now() - startTime,
          service: mapping.serviceName
        });
      }

      // Send response
      res.status(response.status).json(transformedResponse);

    } catch (error) {
      logger.error('Proxy request failed:', error);
      
      const mapping = this.findEndpointMapping(req);
      if (mapping) {
        const service = this.registeredServices.get(mapping.serviceName);
        if (service) {
          service.errorCount++;
        }
      }

      if (this.options.enableMetrics) {
        this.metricsCollector.recordError(req, error);
      }

      // Handle different error types
      if (error.response) {
        // HTTP error response from target service
        res.status(error.response.status).json({
          error: 'Upstream service error',
          message: error.response.data?.message || error.message,
          status: error.response.status,
          service: mapping?.serviceName
        });
      } else if (error.code === 'ECONNREFUSED') {
        // Connection refused
        res.status(503).json({
          error: 'Service unavailable',
          message: 'Unable to connect to upstream service',
          service: mapping?.serviceName
        });
      } else if (error.code === 'ENOTFOUND') {
        // DNS resolution failed
        res.status(503).json({
          error: 'Service not found',
          message: 'Upstream service could not be resolved',
          service: mapping?.serviceName
        });
      } else if (error.code === 'ETIMEDOUT') {
        // Request timeout
        res.status(504).json({
          error: 'Gateway timeout',
          message: 'Upstream service response timeout',
          service: mapping?.serviceName
        });
      } else {
        // Generic error
        res.status(500).json({
          error: 'Proxy error',
          message: error.message,
          service: mapping?.serviceName
        });
      }
    }
  }

  /**
   * Find endpoint mapping for request
   */
  findEndpointMapping(req) {
    // Try exact match first
    const exactKey = `${req.method}:${req.path}`;
    if (this.endpointMappings.has(exactKey)) {
      return this.endpointMappings.get(exactKey);
    }

    // Try wildcard patterns
    for (const [key, mapping] of this.endpointMappings) {
      const [method, pattern] = key.split(':');
      
      if (method !== req.method && method !== 'ALL') {
        continue;
      }

      // Convert pattern to regex
      const regexPattern = pattern
        .replace(/\*/g, '.*')
        .replace(/:\w+/g, '[^/]+'); // :id -> [^/]+
      
      const regex = new RegExp(`^${regexPattern}$`);
      
      if (regex.test(req.path)) {
        return mapping;
      }
    }

    return null;
  }

  /**
   * Start the API wrapper server
   */
  async start() {
    if (this.isRunning) {
      logger.warn('API Wrapper is already running');
      return;
    }

    return new Promise((resolve, reject) => {
      this.server = this.app.listen(this.options.port, (error) => {
        if (error) {
          logger.error('Failed to start API Wrapper:', error);
          reject(error);
        } else {
          this.isRunning = true;
          logger.info(`API Wrapper started on port ${this.options.port}`);
          
          // Start health checks for registered services
          this.startHealthChecks();
          
          resolve();
        }
      });

      // Handle server errors
      this.server.on('error', (error) => {
        logger.error('API Wrapper server error:', error);
        if (!this.isRunning) {
          reject(error);
        }
      });
    });
  }

  /**
   * Stop the API wrapper server
   */
  async stop() {
    if (!this.isRunning || !this.server) {
      logger.warn('API Wrapper is not running');
      return;
    }

    return new Promise((resolve, reject) => {
      this.server.close((error) => {
        if (error) {
          logger.error('Error stopping API Wrapper:', error);
          reject(error);
        } else {
          this.isRunning = false;
          logger.info('API Wrapper stopped');
          resolve();
        }
      });
    });
  }

  /**
   * Start health checks for registered services
   */
  startHealthChecks() {
    setInterval(async () => {
      for (const [name, service] of this.registeredServices) {
        try {
          const healthEndpoint = service.healthEndpoint || '/health';
          const response = await axios.get(`${service.baseUrl}${healthEndpoint}`, {
            timeout: 5000
          });
          
          service.healthy = response.status === 200;
          service.lastCheck = new Date().toISOString();
          
          if (!service.healthy) {
            logger.warn(`Service ${name} health check failed`);
          }
        } catch (error) {
          service.healthy = false;
          service.lastCheck = new Date().toISOString();
          logger.error(`Health check failed for service ${name}:`, error.message);
        }
      }
    }, 30000); // Check every 30 seconds
  }

  /**
   * Get API wrapper statistics
   */
  getStats() {
    const services = Object.fromEntries(
      Array.from(this.registeredServices.entries()).map(([name, service]) => [
        name,
        {
          healthy: service.healthy,
          requestCount: service.requestCount,
          errorCount: service.errorCount,
          lastCheck: service.lastCheck
        }
      ])
    );

    return {
      uptime: process.uptime(),
      servicesCount: this.registeredServices.size,
      endpointMappingsCount: this.endpointMappings.size,
      services,
      metrics: this.options.enableMetrics ? this.metricsCollector.getMetrics() : null
    };
  }

  /**
   * Load configuration from file
   */
  async loadConfiguration(configPath) {
    try {
      const config = await fs.readJson(configPath);
      
      // Register services from config
      if (config.services) {
        for (const [name, serviceConfig] of Object.entries(config.services)) {
          this.registerService(name, serviceConfig);
        }
      }
      
      // Create endpoint mappings from config
      if (config.mappings) {
        for (const mapping of config.mappings) {
          this.mapEndpoint(mapping.path, mapping);
        }
      }
      
      logger.info(`Configuration loaded from ${configPath}`);
    } catch (error) {
      logger.error('Failed to load configuration:', error);
      throw error;
    }
  }

  /**
   * Save current configuration to file
   */
  async saveConfiguration(configPath) {
    try {
      const config = {
        services: Object.fromEntries(this.registeredServices),
        mappings: Array.from(this.endpointMappings.entries()).map(([key, mapping]) => ({
          path: key.split(':')[1],
          method: key.split(':')[0],
          ...mapping
        }))
      };
      
      await fs.writeJson(configPath, config, { spaces: 2 });
      logger.info(`Configuration saved to ${configPath}`);
    } catch (error) {
      logger.error('Failed to save configuration:', error);
      throw error;
    }
  }
}