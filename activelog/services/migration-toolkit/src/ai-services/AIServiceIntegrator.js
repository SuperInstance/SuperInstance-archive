import axios from 'axios';
import logger from '../lib/logger.js';
import { EventEmitter } from 'events';
import { createReadStream, createWriteStream } from 'fs';
import FormData from 'form-data';

/**
 * Seamless AI Service Integration
 * Provides unified interface for various AI services and models
 */
export class AIServiceIntegrator extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      timeout: 120000, // 2 minutes for AI requests
      retries: 3,
      enableCaching: true,
      enableMetrics: true,
      defaultProvider: 'openai',
      fallbackProviders: ['anthropic', 'cohere'],
      rateLimiting: true,
      costTracking: true,
      ...options
    };

    this.providers = new Map();
    this.models = new Map();
    this.requestQueue = [];
    this.activeRequests = new Map();
    this.cache = new Map();
    this.metrics = {
      requests: 0,
      successes: 0,
      failures: 0,
      totalCost: 0,
      averageResponseTime: 0,
      providerUsage: {}
    };
    
    this.setupProviders();
    this.startQueueProcessor();
  }

  /**
   * Setup AI service providers
   */
  setupProviders() {
    // OpenAI Provider
    this.registerProvider('openai', {
      name: 'OpenAI',
      baseUrl: 'https://api.openai.com/v1',
      supportedModels: [
        'gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo',
        'dall-e-3', 'dall-e-2', 'whisper-1', 'tts-1'
      ],
      endpoints: {
        chat: '/chat/completions',
        completions: '/completions',
        embeddings: '/embeddings',
        images: '/images/generations',
        audio: '/audio',
        files: '/files',
        fineTuning: '/fine_tuning'
      },
      authentication: 'bearer',
      costPerToken: {
        'gpt-4': { input: 0.03, output: 0.06 },
        'gpt-4-turbo': { input: 0.01, output: 0.03 },
        'gpt-3.5-turbo': { input: 0.001, output: 0.002 }
      }
    });

    // Anthropic Provider
    this.registerProvider('anthropic', {
      name: 'Anthropic',
      baseUrl: 'https://api.anthropic.com/v1',
      supportedModels: [
        'claude-3-opus-20240229',
        'claude-3-sonnet-20240229',
        'claude-3-haiku-20240307'
      ],
      endpoints: {
        messages: '/messages',
        completions: '/complete'
      },
      authentication: 'api-key',
      costPerToken: {
        'claude-3-opus-20240229': { input: 0.015, output: 0.075 },
        'claude-3-sonnet-20240229': { input: 0.003, output: 0.015 },
        'claude-3-haiku-20240307': { input: 0.00025, output: 0.00125 }
      }
    });

    // Local AI Provider (for edge deployment)
    this.registerProvider('local', {
      name: 'Local AI',
      baseUrl: 'http://localhost:8080',
      supportedModels: ['llama2', 'codellama', 'mistral'],
      endpoints: {
        completions: '/v1/completions',
        chat: '/v1/chat/completions',
        embeddings: '/v1/embeddings'
      },
      authentication: 'none',
      costPerToken: {} // No cost for local models
    });

    // Custom AI Provider (for company-specific models)
    this.registerProvider('custom', {
      name: 'Custom AI',
      baseUrl: process.env.CUSTOM_AI_BASE_URL || 'http://localhost:8081',
      supportedModels: ['custom-model-v1', 'domain-specific-model'],
      endpoints: {
        inference: '/inference',
        training: '/training',
        evaluation: '/evaluation'
      },
      authentication: 'bearer',
      costPerToken: {}
    });
  }

  /**
   * Register AI service provider
   */
  registerProvider(name, config) {
    logger.info(`Registering AI provider: ${name}`);
    
    this.providers.set(name, {
      ...config,
      healthy: true,
      lastCheck: new Date().toISOString(),
      requestCount: 0,
      errorCount: 0,
      averageResponseTime: 0
    });

    // Initialize metrics for this provider
    this.metrics.providerUsage[name] = {
      requests: 0,
      successes: 0,
      failures: 0,
      cost: 0
    };

    // Register models
    config.supportedModels.forEach(model => {
      this.models.set(model, name);
    });
  }

  /**
   * Generate text completion
   */
  async generateCompletion(request) {
    const {
      model = 'gpt-3.5-turbo',
      prompt,
      messages,
      maxTokens = 1000,
      temperature = 0.7,
      provider = null,
      stream = false,
      ...otherParams
    } = request;

    try {
      // Determine provider
      const selectedProvider = provider || this.selectProvider(model);
      const providerConfig = this.providers.get(selectedProvider);
      
      if (!providerConfig) {
        throw new Error(`Provider ${selectedProvider} not found`);
      }

      // Check rate limits
      if (this.options.rateLimiting && !await this.checkRateLimit(selectedProvider)) {
        throw new Error(`Rate limit exceeded for provider ${selectedProvider}`);
      }

      // Build request payload
      const payload = this.buildCompletionPayload(
        selectedProvider,
        model,
        { prompt, messages, maxTokens, temperature, stream, ...otherParams }
      );

      // Check cache
      const cacheKey = this.generateCacheKey('completion', payload);
      if (this.options.enableCaching && !stream) {
        const cached = this.cache.get(cacheKey);
        if (cached) {
          logger.info('Cache hit for completion request');
          return cached;
        }
      }

      // Make request
      const startTime = Date.now();
      const response = await this.makeRequest(selectedProvider, 'completion', payload);
      const responseTime = Date.now() - startTime;

      // Process response
      const result = this.processCompletionResponse(selectedProvider, response, model);
      
      // Update metrics
      this.updateMetrics(selectedProvider, 'success', responseTime, result.usage);
      
      // Cache result
      if (this.options.enableCaching && !stream) {
        this.cache.set(cacheKey, result);
      }

      // Track costs
      if (this.options.costTracking) {
        this.trackCosts(selectedProvider, model, result.usage);
      }

      this.emit('completion', {
        provider: selectedProvider,
        model,
        responseTime,
        usage: result.usage
      });

      return result;

    } catch (error) {
      logger.error('AI completion failed:', error);
      
      // Try fallback providers
      if (!provider && this.options.fallbackProviders.length > 0) {
        for (const fallbackProvider of this.options.fallbackProviders) {
          try {
            return await this.generateCompletion({ 
              ...request, 
              provider: fallbackProvider 
            });
          } catch (fallbackError) {
            logger.warn(`Fallback provider ${fallbackProvider} also failed:`, fallbackError);
          }
        }
      }

      throw error;
    }
  }

  /**
   * Generate embeddings
   */
  async generateEmbeddings(request) {
    const {
      input,
      model = 'text-embedding-ada-002',
      provider = null,
      dimensions = null
    } = request;

    try {
      const selectedProvider = provider || this.selectProvider(model);
      const providerConfig = this.providers.get(selectedProvider);

      if (!providerConfig) {
        throw new Error(`Provider ${selectedProvider} not found`);
      }

      const payload = this.buildEmbeddingPayload(selectedProvider, model, input, dimensions);
      
      // Check cache
      const cacheKey = this.generateCacheKey('embedding', payload);
      if (this.options.enableCaching) {
        const cached = this.cache.get(cacheKey);
        if (cached) {
          return cached;
        }
      }

      const startTime = Date.now();
      const response = await this.makeRequest(selectedProvider, 'embedding', payload);
      const responseTime = Date.now() - startTime;

      const result = this.processEmbeddingResponse(selectedProvider, response);
      
      this.updateMetrics(selectedProvider, 'success', responseTime, result.usage);
      
      if (this.options.enableCaching) {
        this.cache.set(cacheKey, result);
      }

      return result;

    } catch (error) {
      logger.error('AI embedding generation failed:', error);
      throw error;
    }
  }

  /**
   * Generate image
   */
  async generateImage(request) {
    const {
      prompt,
      model = 'dall-e-3',
      size = '1024x1024',
      quality = 'standard',
      style = 'vivid',
      provider = null,
      n = 1
    } = request;

    try {
      const selectedProvider = provider || this.selectProvider(model);
      const providerConfig = this.providers.get(selectedProvider);

      if (!providerConfig) {
        throw new Error(`Provider ${selectedProvider} not found`);
      }

      const payload = this.buildImagePayload(selectedProvider, {
        prompt, model, size, quality, style, n
      });

      const startTime = Date.now();
      const response = await this.makeRequest(selectedProvider, 'image', payload);
      const responseTime = Date.now() - startTime;

      const result = this.processImageResponse(selectedProvider, response);
      
      this.updateMetrics(selectedProvider, 'success', responseTime, result.usage);

      return result;

    } catch (error) {
      logger.error('AI image generation failed:', error);
      throw error;
    }
  }

  /**
   * Transcribe audio
   */
  async transcribeAudio(audioFile, options = {}) {
    const {
      model = 'whisper-1',
      language = null,
      prompt = null,
      responseFormat = 'json',
      temperature = 0,
      provider = null
    } = options;

    try {
      const selectedProvider = provider || this.selectProvider(model);
      const providerConfig = this.providers.get(selectedProvider);

      if (!providerConfig) {
        throw new Error(`Provider ${selectedProvider} not found`);
      }

      const formData = new FormData();
      formData.append('file', createReadStream(audioFile));
      formData.append('model', model);
      if (language) formData.append('language', language);
      if (prompt) formData.append('prompt', prompt);
      formData.append('response_format', responseFormat);
      formData.append('temperature', temperature.toString());

      const startTime = Date.now();
      const response = await this.makeMultipartRequest(selectedProvider, 'audio', formData);
      const responseTime = Date.now() - startTime;

      const result = this.processAudioResponse(selectedProvider, response);
      
      this.updateMetrics(selectedProvider, 'success', responseTime, result.usage);

      return result;

    } catch (error) {
      logger.error('AI audio transcription failed:', error);
      throw error;
    }
  }

  /**
   * Fine-tune model
   */
  async fineTuneModel(request) {
    const {
      trainingFile,
      validationFile = null,
      model = 'gpt-3.5-turbo',
      epochs = 3,
      batchSize = null,
      learningRateMultiplier = null,
      provider = null
    } = request;

    try {
      const selectedProvider = provider || this.selectProvider(model);
      const providerConfig = this.providers.get(selectedProvider);

      if (!providerConfig) {
        throw new Error(`Provider ${selectedProvider} not found`);
      }

      const payload = {
        training_file: trainingFile,
        validation_file: validationFile,
        model,
        hyperparameters: {
          n_epochs: epochs,
          batch_size: batchSize,
          learning_rate_multiplier: learningRateMultiplier
        }
      };

      const response = await this.makeRequest(selectedProvider, 'fineTuning', payload);
      const result = this.processFineTuningResponse(selectedProvider, response);

      return result;

    } catch (error) {
      logger.error('AI model fine-tuning failed:', error);
      throw error;
    }
  }

  /**
   * Select best provider for model
   */
  selectProvider(model) {
    const provider = this.models.get(model);
    if (!provider) {
      // Try default provider
      const defaultProvider = this.providers.get(this.options.defaultProvider);
      if (defaultProvider && defaultProvider.supportedModels.includes(model)) {
        return this.options.defaultProvider;
      }
      throw new Error(`No provider found for model: ${model}`);
    }
    
    // Check if provider is healthy
    const providerConfig = this.providers.get(provider);
    if (!providerConfig.healthy) {
      // Try fallback providers
      for (const fallbackProvider of this.options.fallbackProviders) {
        const fallbackConfig = this.providers.get(fallbackProvider);
        if (fallbackConfig && fallbackConfig.healthy && fallbackConfig.supportedModels.includes(model)) {
          return fallbackProvider;
        }
      }
    }
    
    return provider;
  }

  /**
   * Build completion request payload
   */
  buildCompletionPayload(provider, model, params) {
    const basePayload = {
      model,
      max_tokens: params.maxTokens,
      temperature: params.temperature,
      stream: params.stream || false
    };

    switch (provider) {
      case 'openai':
        if (params.messages) {
          return { ...basePayload, messages: params.messages };
        } else {
          return { ...basePayload, prompt: params.prompt };
        }

      case 'anthropic':
        return {
          model,
          max_tokens: params.maxTokens,
          temperature: params.temperature,
          messages: params.messages || [{ role: 'user', content: params.prompt }],
          stream: params.stream || false
        };

      case 'local':
      case 'custom':
        return {
          model,
          prompt: params.prompt || this.messagesToPrompt(params.messages),
          max_tokens: params.maxTokens,
          temperature: params.temperature,
          stream: params.stream || false
        };

      default:
        return basePayload;
    }
  }

  /**
   * Build embedding request payload
   */
  buildEmbeddingPayload(provider, model, input, dimensions) {
    switch (provider) {
      case 'openai':
        const payload = { model, input };
        if (dimensions) payload.dimensions = dimensions;
        return payload;

      case 'local':
      case 'custom':
        return { model, input };

      default:
        return { model, input };
    }
  }

  /**
   * Build image generation payload
   */
  buildImagePayload(provider, params) {
    switch (provider) {
      case 'openai':
        return {
          model: params.model,
          prompt: params.prompt,
          size: params.size,
          quality: params.quality,
          style: params.style,
          n: params.n
        };

      default:
        return {
          prompt: params.prompt,
          size: params.size,
          n: params.n
        };
    }
  }

  /**
   * Make HTTP request to AI service
   */
  async makeRequest(provider, endpoint, payload) {
    const providerConfig = this.providers.get(provider);
    const endpointUrl = this.getEndpointUrl(provider, endpoint);
    
    const config = {
      method: 'POST',
      url: endpointUrl,
      headers: this.buildHeaders(provider),
      data: payload,
      timeout: this.options.timeout,
      validateStatus: () => true
    };

    let lastError;
    for (let attempt = 0; attempt <= this.options.retries; attempt++) {
      try {
        const response = await axios(config);
        
        if (response.status >= 400) {
          throw new Error(`HTTP ${response.status}: ${response.data?.error?.message || response.statusText}`);
        }
        
        providerConfig.requestCount++;
        return response.data;
        
      } catch (error) {
        lastError = error;
        providerConfig.errorCount++;
        
        if (attempt < this.options.retries) {
          const delay = Math.pow(2, attempt) * 1000;
          logger.warn(`AI request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${this.options.retries})`);
          await this.sleep(delay);
        }
      }
    }
    
    this.updateMetrics(provider, 'failure');
    throw lastError;
  }

  /**
   * Make multipart request (for file uploads)
   */
  async makeMultipartRequest(provider, endpoint, formData) {
    const providerConfig = this.providers.get(provider);
    const endpointUrl = this.getEndpointUrl(provider, endpoint);
    
    const headers = this.buildHeaders(provider);
    delete headers['content-type']; // Let axios set multipart headers
    
    const config = {
      method: 'POST',
      url: endpointUrl,
      headers,
      data: formData,
      timeout: this.options.timeout,
      validateStatus: () => true
    };

    const response = await axios(config);
    
    if (response.status >= 400) {
      throw new Error(`HTTP ${response.status}: ${response.data?.error?.message || response.statusText}`);
    }
    
    return response.data;
  }

  /**
   * Get endpoint URL for provider
   */
  getEndpointUrl(provider, endpointType) {
    const providerConfig = this.providers.get(provider);
    const baseUrl = providerConfig.baseUrl;
    
    switch (endpointType) {
      case 'completion':
        if (providerConfig.endpoints.chat) {
          return `${baseUrl}${providerConfig.endpoints.chat}`;
        }
        return `${baseUrl}${providerConfig.endpoints.completions}`;
        
      case 'embedding':
        return `${baseUrl}${providerConfig.endpoints.embeddings}`;
        
      case 'image':
        return `${baseUrl}${providerConfig.endpoints.images}`;
        
      case 'audio':
        return `${baseUrl}${providerConfig.endpoints.audio}/transcriptions`;
        
      case 'fineTuning':
        return `${baseUrl}${providerConfig.endpoints.fineTuning}/jobs`;
        
      default:
        throw new Error(`Unknown endpoint type: ${endpointType}`);
    }
  }

  /**
   * Build request headers for provider
   */
  buildHeaders(provider) {
    const providerConfig = this.providers.get(provider);
    const headers = {
      'Content-Type': 'application/json',
      'User-Agent': 'ActiveLog-Migration-Toolkit/1.0'
    };

    switch (providerConfig.authentication) {
      case 'bearer':
        const apiKey = process.env[`${provider.toUpperCase()}_API_KEY`];
        if (apiKey) {
          headers['Authorization'] = `Bearer ${apiKey}`;
        }
        break;

      case 'api-key':
        const anthropicKey = process.env[`${provider.toUpperCase()}_API_KEY`];
        if (anthropicKey) {
          headers['x-api-key'] = anthropicKey;
          headers['anthropic-version'] = '2023-06-01';
        }
        break;

      case 'none':
        // No authentication required
        break;
    }

    return headers;
  }

  /**
   * Process completion response
   */
  processCompletionResponse(provider, response, model) {
    switch (provider) {
      case 'openai':
        return {
          text: response.choices[0].message?.content || response.choices[0].text,
          usage: response.usage,
          model: response.model,
          finishReason: response.choices[0].finish_reason
        };

      case 'anthropic':
        return {
          text: response.content[0].text,
          usage: response.usage,
          model: response.model,
          finishReason: response.stop_reason
        };

      case 'local':
      case 'custom':
        return {
          text: response.choices[0].text || response.choices[0].message?.content,
          usage: response.usage || { total_tokens: 0 },
          model: response.model || model,
          finishReason: response.choices[0].finish_reason
        };

      default:
        return response;
    }
  }

  /**
   * Process embedding response
   */
  processEmbeddingResponse(provider, response) {
    switch (provider) {
      case 'openai':
        return {
          embeddings: response.data.map(item => item.embedding),
          usage: response.usage,
          model: response.model
        };

      case 'local':
      case 'custom':
        return {
          embeddings: response.data || response.embeddings,
          usage: response.usage || { total_tokens: 0 },
          model: response.model
        };

      default:
        return response;
    }
  }

  /**
   * Process image response
   */
  processImageResponse(provider, response) {
    switch (provider) {
      case 'openai':
        return {
          images: response.data.map(item => ({
            url: item.url,
            b64Json: item.b64_json,
            revisedPrompt: item.revised_prompt
          })),
          created: response.created
        };

      default:
        return response;
    }
  }

  /**
   * Process audio transcription response
   */
  processAudioResponse(provider, response) {
    switch (provider) {
      case 'openai':
        return {
          text: response.text,
          language: response.language,
          duration: response.duration,
          segments: response.segments
        };

      default:
        return response;
    }
  }

  /**
   * Process fine-tuning response
   */
  processFineTuningResponse(provider, response) {
    switch (provider) {
      case 'openai':
        return {
          id: response.id,
          status: response.status,
          model: response.model,
          fineTunedModel: response.fine_tuned_model,
          createdAt: response.created_at
        };

      default:
        return response;
    }
  }

  /**
   * Update metrics
   */
  updateMetrics(provider, status, responseTime = 0, usage = {}) {
    this.metrics.requests++;
    this.metrics.providerUsage[provider].requests++;

    if (status === 'success') {
      this.metrics.successes++;
      this.metrics.providerUsage[provider].successes++;
      
      // Update average response time
      const totalTime = this.metrics.averageResponseTime * (this.metrics.successes - 1) + responseTime;
      this.metrics.averageResponseTime = totalTime / this.metrics.successes;
    } else {
      this.metrics.failures++;
      this.metrics.providerUsage[provider].failures++;
    }
  }

  /**
   * Track costs
   */
  trackCosts(provider, model, usage) {
    if (!this.options.costTracking || !usage) return;

    const providerConfig = this.providers.get(provider);
    const modelCosts = providerConfig.costPerToken[model];
    
    if (!modelCosts) return;

    const inputCost = (usage.prompt_tokens || 0) * (modelCosts.input / 1000);
    const outputCost = (usage.completion_tokens || 0) * (modelCosts.output / 1000);
    const totalCost = inputCost + outputCost;

    this.metrics.totalCost += totalCost;
    this.metrics.providerUsage[provider].cost += totalCost;

    logger.info(`AI request cost: $${totalCost.toFixed(6)} (${provider}/${model})`);
  }

  /**
   * Check rate limits
   */
  async checkRateLimit(provider) {
    // Simplified rate limiting - implement proper rate limiting based on provider limits
    const now = Date.now();
    const windowMs = 60000; // 1 minute window
    const maxRequests = 100; // requests per minute
    
    if (!this.rateLimitWindows) {
      this.rateLimitWindows = new Map();
    }
    
    const window = this.rateLimitWindows.get(provider) || [];
    const recentRequests = window.filter(time => now - time < windowMs);
    
    if (recentRequests.length >= maxRequests) {
      return false;
    }
    
    recentRequests.push(now);
    this.rateLimitWindows.set(provider, recentRequests);
    return true;
  }

  /**
   * Generate cache key
   */
  generateCacheKey(type, payload) {
    const crypto = require('crypto');
    const data = JSON.stringify({ type, payload });
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  /**
   * Convert messages to prompt (for local models)
   */
  messagesToPrompt(messages) {
    if (!messages) return '';
    
    return messages.map(msg => {
      const role = msg.role === 'assistant' ? 'Assistant' : 'Human';
      return `${role}: ${msg.content}`;
    }).join('\n\n');
  }

  /**
   * Start queue processor for batching requests
   */
  startQueueProcessor() {
    setInterval(() => {
      this.processRequestQueue();
    }, 100); // Process every 100ms
  }

  /**
   * Process request queue
   */
  async processRequestQueue() {
    if (this.requestQueue.length === 0) return;
    
    const batch = this.requestQueue.splice(0, 10); // Process up to 10 requests
    
    for (const request of batch) {
      try {
        const result = await request.handler();
        request.resolve(result);
      } catch (error) {
        request.reject(error);
      }
    }
  }

  /**
   * Health check for providers
   */
  async healthCheck() {
    const results = {};
    
    for (const [name, config] of this.providers) {
      try {
        // Simple health check - try to get models list or make a minimal request
        const response = await axios.get(`${config.baseUrl}/models`, {
          headers: this.buildHeaders(name),
          timeout: 5000
        });
        
        results[name] = {
          healthy: response.status === 200,
          responseTime: response.headers['x-response-time'] || null,
          models: response.data?.data?.length || 0
        };
        
        config.healthy = results[name].healthy;
        config.lastCheck = new Date().toISOString();
        
      } catch (error) {
        results[name] = {
          healthy: false,
          error: error.message
        };
        
        config.healthy = false;
        config.lastCheck = new Date().toISOString();
      }
    }
    
    return results;
  }

  /**
   * Get AI service statistics
   */
  getStats() {
    return {
      metrics: this.metrics,
      providers: Object.fromEntries(
        Array.from(this.providers.entries()).map(([name, config]) => [
          name,
          {
            healthy: config.healthy,
            requestCount: config.requestCount,
            errorCount: config.errorCount,
            lastCheck: config.lastCheck,
            supportedModels: config.supportedModels.length
          }
        ])
      ),
      cache: {
        size: this.cache.size,
        hitRate: this.cacheHits / (this.cacheHits + this.cacheMisses) || 0
      },
      queueSize: this.requestQueue.length,
      activeRequests: this.activeRequests.size
    };
  }

  /**
   * Utility function to sleep
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}