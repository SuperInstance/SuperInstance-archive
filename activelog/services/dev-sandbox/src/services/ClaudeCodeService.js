const axios = require('axios');
const { EventEmitter } = require('events');
const crypto = require('crypto');

class ClaudeCodeService extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      apiKey: config.apiKey || process.env.CLAUDE_API_KEY,
      apiUrl: config.apiUrl || process.env.CLAUDE_API_URL || 'https://api.anthropic.com/v1/messages',
      model: config.model || process.env.CLAUDE_MODEL || 'claude-3-sonnet-20240229',
      maxTokens: config.maxTokens || 4096,
      temperature: config.temperature || 0.3,
      
      // Rate limiting
      rateLimits: {
        free: { requests: 10, window: 60000 }, // 10 requests per minute
        pro: { requests: 100, window: 60000 }, // 100 requests per minute
        enterprise: { requests: 1000, window: 60000 } // 1000 requests per minute
      },
      
      // Request timeout
      timeout: config.timeout || 30000,
      
      // Context management
      maxContextLength: config.maxContextLength || 100000,
      enableContextOptimization: config.enableContextOptimization ?? true,
      
      ...config
    };

    this.requestCounts = new Map(); // userId -> { count, windowStart }
    this.conversations = new Map(); // conversationId -> messages[]
    this.activeRequests = new Map(); // requestId -> request info
    
    this.stats = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      avgResponseTime: 0,
      totalTokensUsed: 0,
      rateLimitHits: 0
    };

    // Initialize axios instance
    this.httpClient = axios.create({
      baseURL: this.config.apiUrl.replace('/messages', ''),
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.config.apiKey,
        'anthropic-version': '2023-06-01'
      }
    });

    this.setupRequestInterceptors();
  }

  // Setup axios request/response interceptors
  setupRequestInterceptors() {
    this.httpClient.interceptors.request.use(
      (config) => {
        config.metadata = { startTime: Date.now() };
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.httpClient.interceptors.response.use(
      (response) => {
        const responseTime = Date.now() - response.config.metadata.startTime;
        this.updateStats(responseTime, true, response.data.usage);
        return response;
      },
      (error) => {
        const responseTime = Date.now() - error.config?.metadata?.startTime || 0;
        this.updateStats(responseTime, false);
        return Promise.reject(error);
      }
    );
  }

  // Generate code with Claude
  async generateCode(userId, userTier, request) {
    const requestId = crypto.randomUUID();
    
    try {
      // Check rate limits
      if (!this.checkRateLimit(userId, userTier)) {
        this.stats.rateLimitHits++;
        throw new Error('Rate limit exceeded');
      }

      // Track active request
      this.activeRequests.set(requestId, {
        userId,
        userTier,
        startTime: Date.now(),
        type: 'code_generation'
      });

      const prompt = this.buildCodeGenerationPrompt(request);
      const response = await this.sendClaudeRequest(prompt, request.options);
      
      const result = {
        requestId,
        userId,
        code: this.extractCodeFromResponse(response.content),
        explanation: this.extractExplanationFromResponse(response.content),
        language: request.language,
        tokensUsed: response.usage?.input_tokens + response.usage?.output_tokens,
        timestamp: new Date().toISOString()
      };

      this.emit('codeGenerated', result);
      return result;
      
    } catch (error) {
      this.emit('codeGenerationError', { requestId, userId, error });
      throw error;
    } finally {
      this.activeRequests.delete(requestId);
    }
  }

  // Review code with Claude
  async reviewCode(userId, userTier, codeReview) {
    const requestId = crypto.randomUUID();
    
    try {
      if (!this.checkRateLimit(userId, userTier)) {
        this.stats.rateLimitHits++;
        throw new Error('Rate limit exceeded');
      }

      this.activeRequests.set(requestId, {
        userId,
        userTier,
        startTime: Date.now(),
        type: 'code_review'
      });

      const prompt = this.buildCodeReviewPrompt(codeReview);
      const response = await this.sendClaudeRequest(prompt, codeReview.options);
      
      const result = {
        requestId,
        userId,
        review: this.parseCodeReview(response.content),
        suggestions: this.extractSuggestions(response.content),
        score: this.extractScore(response.content),
        tokensUsed: response.usage?.input_tokens + response.usage?.output_tokens,
        timestamp: new Date().toISOString()
      };

      this.emit('codeReviewed', result);
      return result;
      
    } catch (error) {
      this.emit('codeReviewError', { requestId, userId, error });
      throw error;
    } finally {
      this.activeRequests.delete(requestId);
    }
  }

  // Debug code with Claude
  async debugCode(userId, userTier, debugRequest) {
    const requestId = crypto.randomUUID();
    
    try {
      if (!this.checkRateLimit(userId, userTier)) {
        this.stats.rateLimitHits++;
        throw new Error('Rate limit exceeded');
      }

      this.activeRequests.set(requestId, {
        userId,
        userTier,
        startTime: Date.now(),
        type: 'code_debug'
      });

      const prompt = this.buildDebugPrompt(debugRequest);
      const response = await this.sendClaudeRequest(prompt, debugRequest.options);
      
      const result = {
        requestId,
        userId,
        diagnosis: this.extractDiagnosis(response.content),
        fixes: this.extractFixes(response.content),
        explanation: this.extractDebugExplanation(response.content),
        tokensUsed: response.usage?.input_tokens + response.usage?.output_tokens,
        timestamp: new Date().toISOString()
      };

      this.emit('codeDebugged', result);
      return result;
      
    } catch (error) {
      this.emit('codeDebugError', { requestId, userId, error });
      throw error;
    } finally {
      this.activeRequests.delete(requestId);
    }
  }

  // Start conversational coding session
  async startConversation(userId, userTier, initialPrompt) {
    const conversationId = crypto.randomUUID();
    
    try {
      if (!this.checkRateLimit(userId, userTier)) {
        this.stats.rateLimitHits++;
        throw new Error('Rate limit exceeded');
      }

      const systemPrompt = this.buildSystemPrompt();
      const conversation = {
        id: conversationId,
        userId,
        userTier,
        createdAt: Date.now(),
        messages: [
          {
            role: 'system',
            content: systemPrompt
          },
          {
            role: 'user',
            content: initialPrompt
          }
        ],
        context: {
          language: 'javascript',
          framework: null,
          project: null
        }
      };

      // Send initial request to Claude
      const response = await this.sendClaudeRequest(conversation.messages);
      
      conversation.messages.push({
        role: 'assistant',
        content: response.content,
        timestamp: Date.now()
      });

      this.conversations.set(conversationId, conversation);
      
      const result = {
        conversationId,
        response: response.content,
        tokensUsed: response.usage?.input_tokens + response.usage?.output_tokens
      };

      this.emit('conversationStarted', result);
      return result;
      
    } catch (error) {
      this.emit('conversationError', { conversationId, userId, error });
      throw error;
    }
  }

  // Continue conversation
  async continueConversation(conversationId, userMessage, options = {}) {
    try {
      const conversation = this.conversations.get(conversationId);
      if (!conversation) {
        throw new Error('Conversation not found');
      }

      if (!this.checkRateLimit(conversation.userId, conversation.userTier)) {
        this.stats.rateLimitHits++;
        throw new Error('Rate limit exceeded');
      }

      // Add user message
      conversation.messages.push({
        role: 'user',
        content: userMessage,
        timestamp: Date.now()
      });

      // Optimize context if needed
      if (this.config.enableContextOptimization) {
        this.optimizeConversationContext(conversation);
      }

      // Send to Claude
      const response = await this.sendClaudeRequest(conversation.messages, options);
      
      // Add assistant response
      conversation.messages.push({
        role: 'assistant',
        content: response.content,
        timestamp: Date.now()
      });

      const result = {
        conversationId,
        response: response.content,
        tokensUsed: response.usage?.input_tokens + response.usage?.output_tokens,
        messageCount: conversation.messages.length
      };

      this.emit('conversationContinued', result);
      return result;
      
    } catch (error) {
      this.emit('conversationError', { conversationId, error });
      throw error;
    }
  }

  // Send request to Claude API
  async sendClaudeRequest(messages, options = {}) {
    this.stats.totalRequests++;
    
    const requestBody = {
      model: options.model || this.config.model,
      max_tokens: options.maxTokens || this.config.maxTokens,
      temperature: options.temperature || this.config.temperature,
      messages: Array.isArray(messages) ? messages.filter(m => m.role !== 'system') : [{
        role: 'user',
        content: messages
      }],
      ...options
    };

    // Add system message if present
    const systemMessage = Array.isArray(messages) ? 
      messages.find(m => m.role === 'system') : null;
    
    if (systemMessage) {
      requestBody.system = systemMessage.content;
    }

    try {
      const response = await this.httpClient.post('/messages', requestBody);
      return response.data;
    } catch (error) {
      this.handleAPIError(error);
      throw error;
    }
  }

  // Build code generation prompt
  buildCodeGenerationPrompt(request) {
    const { description, language, framework, requirements, context } = request;
    
    let prompt = `Generate ${language} code for the following requirement:\n\n`;
    prompt += `Description: ${description}\n\n`;
    
    if (framework) {
      prompt += `Framework: ${framework}\n\n`;
    }
    
    if (requirements && requirements.length > 0) {
      prompt += `Requirements:\n${requirements.map(req => `- ${req}`).join('\n')}\n\n`;
    }
    
    if (context) {
      prompt += `Additional Context: ${context}\n\n`;
    }
    
    prompt += `Please provide:\n`;
    prompt += `1. Clean, production-ready code\n`;
    prompt += `2. Proper error handling\n`;
    prompt += `3. Clear comments explaining key functionality\n`;
    prompt += `4. Brief explanation of the approach\n\n`;
    prompt += `Format your response with the code in markdown code blocks.`;
    
    return prompt;
  }

  // Build code review prompt
  buildCodeReviewPrompt(codeReview) {
    const { code, language, focusAreas, context } = codeReview;
    
    let prompt = `Please review the following ${language} code:\n\n`;
    prompt += `\`\`\`${language}\n${code}\n\`\`\`\n\n`;
    
    if (focusAreas && focusAreas.length > 0) {
      prompt += `Focus areas for review:\n${focusAreas.map(area => `- ${area}`).join('\n')}\n\n`;
    }
    
    if (context) {
      prompt += `Context: ${context}\n\n`;
    }
    
    prompt += `Please provide:\n`;
    prompt += `1. Overall assessment and score (1-10)\n`;
    prompt += `2. Identified issues and their severity\n`;
    prompt += `3. Specific suggestions for improvement\n`;
    prompt += `4. Best practices recommendations\n`;
    prompt += `5. Security considerations if applicable\n\n`;
    prompt += `Structure your response with clear sections for each area.`;
    
    return prompt;
  }

  // Build debug prompt
  buildDebugPrompt(debugRequest) {
    const { code, error, language, expectedBehavior, context } = debugRequest;
    
    let prompt = `Help debug the following ${language} code issue:\n\n`;
    prompt += `Code:\n\`\`\`${language}\n${code}\n\`\`\`\n\n`;
    
    if (error) {
      prompt += `Error encountered: ${error}\n\n`;
    }
    
    if (expectedBehavior) {
      prompt += `Expected behavior: ${expectedBehavior}\n\n`;
    }
    
    if (context) {
      prompt += `Additional context: ${context}\n\n`;
    }
    
    prompt += `Please provide:\n`;
    prompt += `1. Diagnosis of the issue\n`;
    prompt += `2. Root cause analysis\n`;
    prompt += `3. Step-by-step fix with corrected code\n`;
    prompt += `4. Prevention strategies for similar issues\n\n`;
    prompt += `Include corrected code in markdown code blocks.`;
    
    return prompt;
  }

  // Build system prompt for conversations
  buildSystemPrompt() {
    return `You are Claude Code, an expert programming assistant integrated into a developer sandbox environment. You help developers write, review, debug, and improve code across multiple programming languages and frameworks.

Your capabilities include:
- Writing clean, efficient, and well-documented code
- Reviewing code for bugs, performance issues, and best practices
- Debugging complex issues with detailed explanations
- Suggesting architectural improvements and design patterns
- Providing step-by-step guidance for implementation

Guidelines:
- Always provide production-ready code with proper error handling
- Include clear comments explaining complex logic
- Follow language-specific best practices and conventions
- Consider security implications in your recommendations
- Offer multiple approaches when appropriate
- Be concise but thorough in explanations

You are working within a sandboxed development environment where users can execute code safely.`;
  }

  // Extract code from Claude's response
  extractCodeFromResponse(content) {
    const codeBlockRegex = /```[\w]*\n([\s\S]*?)\n```/g;
    const matches = [];
    let match;
    
    while ((match = codeBlockRegex.exec(content)) !== null) {
      matches.push(match[1].trim());
    }
    
    return matches.length > 0 ? matches : [content];
  }

  // Extract explanation from response
  extractExplanationFromResponse(content) {
    // Remove code blocks and return remaining text
    const withoutCode = content.replace(/```[\w]*\n[\s\S]*?\n```/g, '').trim();
    return withoutCode || 'No explanation provided.';
  }

  // Parse code review from response
  parseCodeReview(content) {
    const sections = {
      assessment: this.extractSection(content, /overall assessment|assessment|score/i),
      issues: this.extractSection(content, /issues|problems|bugs/i),
      suggestions: this.extractSection(content, /suggestions|recommendations|improvements/i),
      security: this.extractSection(content, /security|vulnerabilities/i)
    };
    
    return {
      fullReview: content,
      ...sections
    };
  }

  // Extract suggestions from response
  extractSuggestions(content) {
    const suggestionRegex = /(?:suggestion|recommendation):\s*(.*?)(?=\n|$)/gi;
    const suggestions = [];
    let match;
    
    while ((match = suggestionRegex.exec(content)) !== null) {
      suggestions.push(match[1].trim());
    }
    
    return suggestions;
  }

  // Extract score from review
  extractScore(content) {
    const scoreRegex = /score[:\s]*(\d+(?:\.\d+)?)\s*(?:\/\s*10)?/i;
    const match = content.match(scoreRegex);
    return match ? parseFloat(match[1]) : null;
  }

  // Extract diagnosis from debug response
  extractDiagnosis(content) {
    return this.extractSection(content, /diagnosis|issue|problem/i) || content;
  }

  // Extract fixes from debug response
  extractFixes(content) {
    const fixes = this.extractCodeFromResponse(content);
    return fixes.length > 0 ? fixes : null;
  }

  // Extract debug explanation
  extractDebugExplanation(content) {
    return this.extractSection(content, /explanation|cause|analysis/i) || 
           this.extractExplanationFromResponse(content);
  }

  // Extract section from content
  extractSection(content, regex) {
    const lines = content.split('\n');
    let startIndex = -1;
    let endIndex = lines.length;
    
    // Find section start
    for (let i = 0; i < lines.length; i++) {
      if (regex.test(lines[i])) {
        startIndex = i;
        break;
      }
    }
    
    if (startIndex === -1) return null;
    
    // Find section end (next heading or code block)
    for (let i = startIndex + 1; i < lines.length; i++) {
      if (lines[i].match(/^#+\s/) || lines[i].match(/^\d+\./)) {
        endIndex = i;
        break;
      }
    }
    
    return lines.slice(startIndex, endIndex).join('\n').trim();
  }

  // Check rate limits
  checkRateLimit(userId, userTier) {
    const limits = this.config.rateLimits[userTier] || this.config.rateLimits.free;
    const now = Date.now();
    
    if (!this.requestCounts.has(userId)) {
      this.requestCounts.set(userId, { count: 0, windowStart: now });
    }
    
    const userLimits = this.requestCounts.get(userId);
    
    // Reset window if expired
    if (now - userLimits.windowStart > limits.window) {
      userLimits.count = 0;
      userLimits.windowStart = now;
    }
    
    // Check if under limit
    if (userLimits.count >= limits.requests) {
      return false;
    }
    
    userLimits.count++;
    return true;
  }

  // Optimize conversation context
  optimizeConversationContext(conversation) {
    const totalLength = conversation.messages.reduce(
      (sum, msg) => sum + msg.content.length, 0
    );
    
    if (totalLength > this.config.maxContextLength) {
      // Keep system message and recent messages
      const systemMessage = conversation.messages.find(m => m.role === 'system');
      const recentMessages = conversation.messages.slice(-10); // Keep last 10 messages
      
      conversation.messages = systemMessage ? 
        [systemMessage, ...recentMessages.filter(m => m.role !== 'system')] :
        recentMessages;
    }
  }

  // Handle API errors
  handleAPIError(error) {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;
      
      switch (status) {
        case 400:
          throw new Error(`Invalid request: ${data.error?.message || 'Bad request'}`);
        case 401:
          throw new Error('Invalid API key or authentication failed');
        case 403:
          throw new Error('Access forbidden - check permissions');
        case 429:
          throw new Error('Rate limit exceeded - please try again later');
        case 500:
          throw new Error('Claude API server error - please try again');
        default:
          throw new Error(`API error (${status}): ${data.error?.message || 'Unknown error'}`);
      }
    } else if (error.request) {
      throw new Error('Network error - unable to reach Claude API');
    } else {
      throw new Error(`Request setup error: ${error.message}`);
    }
  }

  // Update statistics
  updateStats(responseTime, success, usage = {}) {
    if (success) {
      this.stats.successfulRequests++;
      this.stats.totalTokensUsed += (usage.input_tokens || 0) + (usage.output_tokens || 0);
    } else {
      this.stats.failedRequests++;
    }
    
    // Update average response time
    const totalRequests = this.stats.successfulRequests + this.stats.failedRequests;
    this.stats.avgResponseTime = (
      (this.stats.avgResponseTime * (totalRequests - 1) + responseTime) / totalRequests
    );
  }

  // Get user statistics
  getUserStats(userId) {
    const userRequests = this.requestCounts.get(userId);
    const activeRequest = Array.from(this.activeRequests.values())
      .find(req => req.userId === userId);
    
    return {
      requestsThisWindow: userRequests?.count || 0,
      windowResetTime: userRequests ? userRequests.windowStart + this.config.rateLimits.free.window : null,
      hasActiveRequest: !!activeRequest,
      activeRequestType: activeRequest?.type,
      conversations: Array.from(this.conversations.values())
        .filter(conv => conv.userId === userId).length
    };
  }

  // Get service statistics
  getServiceStats() {
    return {
      ...this.stats,
      successRate: this.stats.totalRequests > 0 ? 
        ((this.stats.successfulRequests / this.stats.totalRequests) * 100).toFixed(2) + '%' :
        '0%',
      avgTokensPerRequest: this.stats.successfulRequests > 0 ?
        Math.round(this.stats.totalTokensUsed / this.stats.successfulRequests) :
        0,
      activeConversations: this.conversations.size,
      activeRequests: this.activeRequests.size,
      rateLimitHitRate: this.stats.totalRequests > 0 ?
        ((this.stats.rateLimitHits / this.stats.totalRequests) * 100).toFixed(2) + '%' :
        '0%'
    };
  }

  // Health check
  async healthCheck() {
    try {
      // Test with a simple request
      const testResponse = await this.sendClaudeRequest('Hello, Claude. Please respond with "OK" if you can receive this message.');
      
      return {
        healthy: true,
        apiConnected: true,
        responseTime: this.stats.avgResponseTime,
        stats: this.getServiceStats(),
        testResponse: testResponse.content.includes('OK')
      };
      
    } catch (error) {
      return {
        healthy: false,
        apiConnected: false,
        error: error.message
      };
    }
  }

  // Cleanup expired conversations
  cleanupExpiredConversations() {
    const now = Date.now();
    const maxAge = 24 * 60 * 60 * 1000; // 24 hours
    const expiredConversations = [];
    
    for (const [conversationId, conversation] of this.conversations.entries()) {
      if (now - conversation.createdAt > maxAge) {
        expiredConversations.push(conversationId);
      }
    }
    
    for (const conversationId of expiredConversations) {
      this.conversations.delete(conversationId);
    }
    
    this.emit('conversationsCleanedUp', { count: expiredConversations.length });
  }
}

module.exports = ClaudeCodeService;