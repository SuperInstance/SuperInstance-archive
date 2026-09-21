import axios from 'axios';
import logger from '../lib/logger.js';

/**
 * Manages HTTP proxying with load balancing, circuit breaker, and retry logic
 */
export class ProxyManager {
  constructor(options = {}) {
    this.options = {
      timeout: 30000,
      retries: 3,
      retryDelay: 1000,
      circuitBreakerThreshold: 5,
      circuitBreakerTimeout: 60000,
      loadBalancing: true,
      ...options
    };

    this.circuitBreakers = new Map();
    this.loadBalancers = new Map();
  }

  /**
   * Proxy HTTP request to target service
   */
  async proxyRequest(req, baseUrl, targetPath, options = {}) {
    const config = { ...this.options, ...options };
    const fullUrl = this.buildTargetUrl(baseUrl, targetPath, req);
    
    // Check circuit breaker
    if (config.circuitBreaker && this.isCircuitOpen(baseUrl)) {
      throw new Error(`Circuit breaker open for ${baseUrl}`);
    }

    try {
      const response = await this.executeRequest(req, fullUrl, config);
      
      // Reset circuit breaker on success
      if (config.circuitBreaker) {
        this.resetCircuitBreaker(baseUrl);
      }
      
      return response;
    } catch (error) {
      // Record failure for circuit breaker
      if (config.circuitBreaker) {
        this.recordFailure(baseUrl);
      }
      
      throw error;
    }
  }

  /**
   * Execute HTTP request with retry logic
   */
  async executeRequest(req, url, config) {
    let lastError;
    
    for (let attempt = 0; attempt <= config.retries; attempt++) {
      try {
        const axiosConfig = this.buildAxiosConfig(req, config);
        const response = await axios({
          method: req.method,
          url,
          ...axiosConfig
        });
        
        logger.info(`Proxied ${req.method} ${url} - ${response.status}`);
        return response;
        
      } catch (error) {
        lastError = error;
        
        // Don't retry on client errors (4xx)
        if (error.response && error.response.status >= 400 && error.response.status < 500) {
          throw error;
        }
        
        if (attempt < config.retries) {
          const delay = config.retryDelay * Math.pow(2, attempt); // Exponential backoff
          logger.warn(`Request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${config.retries})`);
          await this.sleep(delay);
        }
      }
    }
    
    throw lastError;
  }

  /**
   * Build target URL
   */
  buildTargetUrl(baseUrl, targetPath, req) {
    // Remove trailing slash from baseUrl
    const cleanBaseUrl = baseUrl.replace(/\/$/, '');
    
    // Ensure targetPath starts with /
    const cleanTargetPath = targetPath.startsWith('/') ? targetPath : `/${targetPath}`;
    
    // Replace path parameters
    let finalPath = cleanTargetPath;
    if (req.params) {
      Object.entries(req.params).forEach(([key, value]) => {
        finalPath = finalPath.replace(`:${key}`, encodeURIComponent(value));
      });
    }
    
    // Add query parameters
    let queryString = '';
    if (req.query && Object.keys(req.query).length > 0) {
      const params = new URLSearchParams();
      Object.entries(req.query).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach(v => params.append(key, v));
        } else {
          params.append(key, value);
        }
      });
      queryString = `?${params.toString()}`;
    }
    
    return `${cleanBaseUrl}${finalPath}${queryString}`;
  }

  /**
   * Build axios configuration
   */
  buildAxiosConfig(req, config) {
    const axiosConfig = {
      timeout: config.timeout,
      headers: { ...req.headers },
      validateStatus: () => true // Don't throw on HTTP error status codes
    };

    // Remove hop-by-hop headers
    delete axiosConfig.headers.host;
    delete axiosConfig.headers.connection;
    delete axiosConfig.headers['proxy-connection'];
    delete axiosConfig.headers['proxy-authenticate'];
    delete axiosConfig.headers['proxy-authorization'];
    delete axiosConfig.headers.te;
    delete axiosConfig.headers.trailers;
    delete axiosConfig.headers.upgrade;

    // Add body for non-GET requests
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      if (req.body) {
        axiosConfig.data = req.body;
      }
    }

    // Handle different content types
    const contentType = req.get('content-type');
    if (contentType) {
      axiosConfig.headers['content-type'] = contentType;
    }

    return axiosConfig;
  }

  /**
   * Circuit breaker implementation
   */
  isCircuitOpen(serviceUrl) {
    const breaker = this.circuitBreakers.get(serviceUrl);
    if (!breaker) return false;
    
    if (breaker.state === 'open') {
      // Check if timeout has passed
      if (Date.now() - breaker.lastFailure > this.options.circuitBreakerTimeout) {
        breaker.state = 'half-open';
        breaker.failures = 0;
        logger.info(`Circuit breaker for ${serviceUrl} moved to half-open state`);
        return false;
      }
      return true;
    }
    
    return false;
  }

  /**
   * Record failure for circuit breaker
   */
  recordFailure(serviceUrl) {
    let breaker = this.circuitBreakers.get(serviceUrl);
    if (!breaker) {
      breaker = {
        failures: 0,
        state: 'closed',
        lastFailure: null
      };
      this.circuitBreakers.set(serviceUrl, breaker);
    }
    
    breaker.failures++;
    breaker.lastFailure = Date.now();
    
    if (breaker.failures >= this.options.circuitBreakerThreshold) {
      breaker.state = 'open';
      logger.warn(`Circuit breaker for ${serviceUrl} opened after ${breaker.failures} failures`);
    }
  }

  /**
   * Reset circuit breaker on success
   */
  resetCircuitBreaker(serviceUrl) {
    const breaker = this.circuitBreakers.get(serviceUrl);
    if (breaker && breaker.state !== 'closed') {
      breaker.state = 'closed';
      breaker.failures = 0;
      logger.info(`Circuit breaker for ${serviceUrl} reset to closed state`);
    }
  }

  /**
   * Load balancing for multiple service instances
   */
  getTargetInstance(serviceName, instances) {
    if (!instances || instances.length === 0) {
      throw new Error(`No instances available for service ${serviceName}`);
    }
    
    if (instances.length === 1) {
      return instances[0];
    }
    
    let balancer = this.loadBalancers.get(serviceName);
    if (!balancer) {
      balancer = {
        currentIndex: 0,
        strategy: 'round-robin'
      };
      this.loadBalancers.set(serviceName, balancer);
    }
    
    switch (balancer.strategy) {
      case 'round-robin':
        const instance = instances[balancer.currentIndex];
        balancer.currentIndex = (balancer.currentIndex + 1) % instances.length;
        return instance;
        
      case 'random':
        return instances[Math.floor(Math.random() * instances.length)];
        
      case 'weighted':
        return this.selectWeightedInstance(instances);
        
      default:
        return instances[0];
    }
  }

  /**
   * Select instance based on weights
   */
  selectWeightedInstance(instances) {
    const totalWeight = instances.reduce((sum, instance) => sum + (instance.weight || 1), 0);
    let random = Math.random() * totalWeight;
    
    for (const instance of instances) {
      random -= (instance.weight || 1);
      if (random <= 0) {
        return instance;
      }
    }
    
    return instances[0]; // Fallback
  }

  /**
   * Proxy WebSocket connections
   */
  async proxyWebSocket(ws, targetUrl, options = {}) {
    const WebSocket = (await import('ws')).default;
    
    try {
      const targetWs = new WebSocket(targetUrl, {
        headers: options.headers || {},
        timeout: options.timeout || this.options.timeout
      });
      
      // Forward messages from client to target
      ws.on('message', (data) => {
        if (targetWs.readyState === WebSocket.OPEN) {
          targetWs.send(data);
        }
      });
      
      // Forward messages from target to client
      targetWs.on('message', (data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(data);
        }
      });
      
      // Handle connection close
      ws.on('close', () => {
        targetWs.close();
      });
      
      targetWs.on('close', () => {
        ws.close();
      });
      
      // Handle errors
      ws.on('error', (error) => {
        logger.error('WebSocket client error:', error);
        targetWs.close();
      });
      
      targetWs.on('error', (error) => {
        logger.error('WebSocket target error:', error);
        ws.close();
      });
      
      logger.info(`WebSocket proxy established: ${targetUrl}`);
      
    } catch (error) {
      logger.error('Failed to establish WebSocket proxy:', error);
      ws.close(1011, 'Proxy connection failed');
    }
  }

  /**
   * Proxy Server-Sent Events
   */
  async proxySSE(req, res, targetUrl, options = {}) {
    try {
      const response = await axios({
        method: 'GET',
        url: targetUrl,
        headers: {
          ...req.headers,
          'cache-control': 'no-cache',
          'connection': 'keep-alive'
        },
        responseType: 'stream',
        timeout: 0 // No timeout for SSE
      });
      
      // Set SSE headers
      res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control'
      });
      
      // Pipe the response
      response.data.pipe(res);
      
      // Handle connection close
      req.on('close', () => {
        response.data.destroy();
      });
      
      logger.info(`SSE proxy established: ${targetUrl}`);
      
    } catch (error) {
      logger.error('Failed to establish SSE proxy:', error);
      res.status(500).json({ error: 'SSE proxy failed' });
    }
  }

  /**
   * Health check for target services
   */
  async healthCheck(serviceUrl, healthEndpoint = '/health') {
    try {
      const response = await axios.get(`${serviceUrl}${healthEndpoint}`, {
        timeout: 5000,
        validateStatus: (status) => status < 500
      });
      
      return {
        healthy: response.status === 200,
        status: response.status,
        responseTime: response.headers['x-response-time'] || null,
        data: response.data
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message,
        responseTime: null
      };
    }
  }

  /**
   * Get proxy statistics
   */
  getStats() {
    const circuitBreakers = Object.fromEntries(
      Array.from(this.circuitBreakers.entries()).map(([url, breaker]) => [
        url,
        {
          state: breaker.state,
          failures: breaker.failures,
          lastFailure: breaker.lastFailure
        }
      ])
    );
    
    return {
      circuitBreakers,
      loadBalancers: Object.fromEntries(this.loadBalancers)
    };
  }

  /**
   * Utility function to sleep
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}