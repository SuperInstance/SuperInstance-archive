const { EventEmitter } = require('events');

class RuleEngine extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      maxRules: options.maxRules || 1000,
      evaluationTimeout: options.evaluationTimeout || 5000,
      enableMetrics: options.enableMetrics || true,
      ...options
    };
    
    this.rules = new Map();
    this.ruleExecutions = new Map();
    this.metrics = {
      rulesEvaluated: 0,
      rulesTriggered: 0,
      evaluationTime: 0,
      errors: 0
    };
    
    this.operators = {
      eq: (a, b) => a === b,
      ne: (a, b) => a !== b,
      gt: (a, b) => a > b,
      gte: (a, b) => a >= b,
      lt: (a, b) => a < b,
      lte: (a, b) => a <= b,
      in: (a, b) => Array.isArray(b) && b.includes(a),
      between: (a, b) => Array.isArray(b) && b.length === 2 && a >= b[0] && a <= b[1],
      contains: (a, b) => typeof a === 'string' && a.includes(b),
      matches: (a, b) => typeof a === 'string' && new RegExp(b).test(a),
      exists: (a) => a !== null && a !== undefined
    };
    
    this.functions = {
      avg: (values) => values.reduce((sum, val) => sum + val, 0) / values.length,
      sum: (values) => values.reduce((sum, val) => sum + val, 0),
      min: (values) => Math.min(...values),
      max: (values) => Math.max(...values),
      count: (values) => values.length,
      unique: (values) => [...new Set(values)],
      round: (value, decimals = 0) => Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals)
    };
    
    this.deviceData = new Map();
    this.dataBuffer = new Map();
    this.ruleGroups = new Map();
    
    this.setupCleanupInterval();
  }

  async createRule(ruleConfig) {
    if (this.rules.size >= this.options.maxRules) {
      throw new Error('Maximum number of rules reached');
    }

    const rule = {
      id: ruleConfig.id || this.generateRuleId(),
      name: ruleConfig.name,
      description: ruleConfig.description,
      enabled: ruleConfig.enabled !== false,
      priority: ruleConfig.priority || 0,
      group: ruleConfig.group || 'default',
      
      // Rule conditions
      conditions: this.validateConditions(ruleConfig.conditions),
      conditionLogic: ruleConfig.conditionLogic || 'AND',
      
      // Actions to execute when rule triggers
      actions: this.validateActions(ruleConfig.actions),
      
      // Trigger settings
      trigger: {
        type: ruleConfig.trigger?.type || 'immediate',
        windowSize: ruleConfig.trigger?.windowSize || 60000,
        frequency: ruleConfig.trigger?.frequency || 'once',
        cooldown: ruleConfig.trigger?.cooldown || 0
      },
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      tags: ruleConfig.tags || [],
      
      // Execution tracking
      executions: 0,
      lastExecution: null,
      lastTrigger: null
    };

    this.rules.set(rule.id, rule);
    
    // Add to rule group
    if (!this.ruleGroups.has(rule.group)) {
      this.ruleGroups.set(rule.group, new Set());
    }
    this.ruleGroups.get(rule.group).add(rule.id);
    
    this.emit('ruleCreated', rule);
    return rule;
  }

  updateRule(ruleId, updates) {
    const rule = this.rules.get(ruleId);
    if (!rule) {
      throw new Error(`Rule ${ruleId} not found`);
    }

    // Validate updates
    if (updates.conditions) {
      updates.conditions = this.validateConditions(updates.conditions);
    }
    if (updates.actions) {
      updates.actions = this.validateActions(updates.actions);
    }

    // Update rule
    const updatedRule = {
      ...rule,
      ...updates,
      updatedAt: new Date()
    };

    this.rules.set(ruleId, updatedRule);
    this.emit('ruleUpdated', updatedRule);
    return updatedRule;
  }

  deleteRule(ruleId) {
    const rule = this.rules.get(ruleId);
    if (!rule) {
      throw new Error(`Rule ${ruleId} not found`);
    }

    this.rules.delete(ruleId);
    this.ruleExecutions.delete(ruleId);
    
    // Remove from rule group
    if (this.ruleGroups.has(rule.group)) {
      this.ruleGroups.get(rule.group).delete(ruleId);
    }
    
    this.emit('ruleDeleted', rule);
    return true;
  }

  async processDeviceData(deviceId, data, metadata = {}) {
    const timestamp = metadata.timestamp || Date.now();
    
    // Store device data
    if (!this.deviceData.has(deviceId)) {
      this.deviceData.set(deviceId, []);
    }
    
    const deviceHistory = this.deviceData.get(deviceId);
    deviceHistory.push({ ...data, timestamp, metadata });
    
    // Limit history size
    if (deviceHistory.length > 1000) {
      deviceHistory.splice(0, deviceHistory.length - 1000);
    }
    
    // Update data buffer for windowed evaluations
    this.updateDataBuffer(deviceId, data, timestamp);
    
    // Evaluate rules
    await this.evaluateRulesForDevice(deviceId, data, metadata);
    
    this.emit('dataProcessed', { deviceId, data, metadata });
  }

  async evaluateRulesForDevice(deviceId, data, metadata = {}) {
    const context = {
      deviceId,
      data,
      metadata,
      timestamp: Date.now(),
      deviceHistory: this.deviceData.get(deviceId) || [],
      bufferData: this.dataBuffer.get(deviceId) || []
    };

    // Get rules sorted by priority
    const sortedRules = Array.from(this.rules.values())
      .filter(rule => rule.enabled)
      .sort((a, b) => b.priority - a.priority);

    for (const rule of sortedRules) {
      try {
        await this.evaluateRule(rule, context);
      } catch (error) {
        this.metrics.errors++;
        this.emit('ruleError', { rule, error, context });
      }
    }
  }

  async evaluateRule(rule, context) {
    const startTime = Date.now();
    
    try {
      // Check cooldown
      if (this.isInCooldown(rule)) {
        return;
      }

      // Evaluate conditions
      const conditionResults = await this.evaluateConditions(rule.conditions, context);
      const ruleTriggered = this.applyConditionLogic(conditionResults, rule.conditionLogic);

      this.metrics.rulesEvaluated++;
      this.metrics.evaluationTime += Date.now() - startTime;

      if (ruleTriggered) {
        await this.executeRuleActions(rule, context);
        this.metrics.rulesTriggered++;
        
        // Update execution tracking
        rule.executions++;
        rule.lastExecution = Date.now();
        rule.lastTrigger = Date.now();
        
        this.emit('ruleTriggered', { rule, context });
      }
      
    } catch (error) {
      this.metrics.errors++;
      throw error;
    }
  }

  async evaluateConditions(conditions, context) {
    const results = [];
    
    for (const condition of conditions) {
      try {
        const result = await this.evaluateCondition(condition, context);
        results.push(result);
      } catch (error) {
        results.push(false);
        this.emit('conditionError', { condition, error, context });
      }
    }
    
    return results;
  }

  async evaluateCondition(condition, context) {
    const { field, operator, value, aggregation, timeWindow } = condition;
    
    let fieldValue;
    
    if (aggregation && timeWindow) {
      // Windowed aggregation
      const windowData = this.getWindowData(context.deviceId, timeWindow);
      const values = windowData.map(item => this.getNestedValue(item.data, field));
      fieldValue = this.functions[aggregation](values);
    } else {
      // Direct field access
      fieldValue = this.getNestedValue(context.data, field);
    }
    
    // Apply operator
    if (!this.operators[operator]) {
      throw new Error(`Unknown operator: ${operator}`);
    }
    
    return this.operators[operator](fieldValue, value);
  }

  applyConditionLogic(results, logic) {
    if (logic === 'AND') {
      return results.every(result => result);
    } else if (logic === 'OR') {
      return results.some(result => result);
    } else if (logic === 'NOT') {
      return !results[0];
    }
    return false;
  }

  async executeRuleActions(rule, context) {
    for (const action of rule.actions) {
      try {
        await this.executeAction(action, context, rule);
      } catch (error) {
        this.emit('actionError', { action, error, context, rule });
      }
    }
  }

  async executeAction(action, context, rule) {
    const { type, config } = action;
    
    switch (type) {
      case 'mqtt_publish':
        await this.executeMqttPublish(config, context, rule);
        break;
        
      case 'http_request':
        await this.executeHttpRequest(config, context, rule);
        break;
        
      case 'device_command':
        await this.executeDeviceCommand(config, context, rule);
        break;
        
      case 'alert':
        await this.executeAlert(config, context, rule);
        break;
        
      case 'data_transform':
        await this.executeDataTransform(config, context, rule);
        break;
        
      case 'rule_chain':
        await this.executeRuleChain(config, context, rule);
        break;
        
      default:
        throw new Error(`Unknown action type: ${type}`);
    }
  }

  async executeMqttPublish(config, context, rule) {
    const topic = this.interpolateTemplate(config.topic, context);
    const payload = this.interpolateTemplate(config.payload, context);
    
    this.emit('mqttPublish', {
      topic,
      payload: typeof payload === 'string' ? payload : JSON.stringify(payload),
      qos: config.qos || 0,
      retain: config.retain || false
    });
  }

  async executeHttpRequest(config, context, rule) {
    const url = this.interpolateTemplate(config.url, context);
    const payload = this.interpolateTemplate(config.payload, context);
    
    this.emit('httpRequest', {
      method: config.method || 'POST',
      url,
      headers: config.headers || {},
      body: payload,
      timeout: config.timeout || 10000
    });
  }

  async executeDeviceCommand(config, context, rule) {
    const deviceId = config.deviceId || context.deviceId;
    const command = this.interpolateTemplate(config.command, context);
    const params = this.interpolateTemplate(config.params, context);
    
    this.emit('deviceCommand', {
      deviceId,
      command,
      params
    });
  }

  async executeAlert(config, context, rule) {
    const message = this.interpolateTemplate(config.message, context);
    
    this.emit('alert', {
      level: config.level || 'warning',
      title: config.title || rule.name,
      message,
      deviceId: context.deviceId,
      ruleId: rule.id,
      timestamp: Date.now(),
      tags: config.tags || []
    });
  }

  async executeDataTransform(config, context, rule) {
    const transformedData = this.transformData(context.data, config.transformations);
    
    this.emit('dataTransform', {
      deviceId: context.deviceId,
      originalData: context.data,
      transformedData,
      ruleId: rule.id
    });
  }

  async executeRuleChain(config, context, rule) {
    const chainRules = config.rules || [];
    
    for (const chainRuleId of chainRules) {
      const chainRule = this.rules.get(chainRuleId);
      if (chainRule && chainRule.enabled) {
        await this.evaluateRule(chainRule, context);
      }
    }
  }

  validateConditions(conditions) {
    if (!Array.isArray(conditions)) {
      throw new Error('Conditions must be an array');
    }
    
    return conditions.map(condition => {
      if (!condition.field || !condition.operator) {
        throw new Error('Condition must have field and operator');
      }
      
      if (!this.operators[condition.operator]) {
        throw new Error(`Unknown operator: ${condition.operator}`);
      }
      
      return condition;
    });
  }

  validateActions(actions) {
    if (!Array.isArray(actions)) {
      throw new Error('Actions must be an array');
    }
    
    const validActionTypes = [
      'mqtt_publish', 'http_request', 'device_command', 
      'alert', 'data_transform', 'rule_chain'
    ];
    
    return actions.map(action => {
      if (!action.type || !validActionTypes.includes(action.type)) {
        throw new Error(`Invalid action type: ${action.type}`);
      }
      
      return action;
    });
  }

  interpolateTemplate(template, context) {
    if (typeof template !== 'string') {
      return template;
    }
    
    return template.replace(/\{\{(\w+(?:\.\w+)*)\}\}/g, (match, path) => {
      return this.getNestedValue(context, path) || match;
    });
  }

  getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
      return current && current[key];
    }, obj);
  }

  transformData(data, transformations) {
    let result = { ...data };
    
    for (const transform of transformations) {
      const { field, operation, params } = transform;
      
      switch (operation) {
        case 'multiply':
          result[field] = result[field] * params.value;
          break;
        case 'add':
          result[field] = result[field] + params.value;
          break;
        case 'round':
          result[field] = this.functions.round(result[field], params.decimals);
          break;
        case 'convert_unit':
          result[field] = this.convertUnit(result[field], params.from, params.to);
          break;
      }
    }
    
    return result;
  }

  convertUnit(value, fromUnit, toUnit) {
    const conversions = {
      'celsius_fahrenheit': (c) => c * 9/5 + 32,
      'fahrenheit_celsius': (f) => (f - 32) * 5/9,
      'meters_feet': (m) => m * 3.28084,
      'feet_meters': (f) => f / 3.28084
    };
    
    const conversionKey = `${fromUnit}_${toUnit}`;
    return conversions[conversionKey] ? conversions[conversionKey](value) : value;
  }

  updateDataBuffer(deviceId, data, timestamp) {
    if (!this.dataBuffer.has(deviceId)) {
      this.dataBuffer.set(deviceId, []);
    }
    
    const buffer = this.dataBuffer.get(deviceId);
    buffer.push({ data, timestamp });
    
    // Keep only last hour of data
    const oneHourAgo = timestamp - 3600000;
    while (buffer.length > 0 && buffer[0].timestamp < oneHourAgo) {
      buffer.shift();
    }
  }

  getWindowData(deviceId, windowSize) {
    const buffer = this.dataBuffer.get(deviceId) || [];
    const windowStart = Date.now() - windowSize;
    
    return buffer.filter(item => item.timestamp >= windowStart);
  }

  isInCooldown(rule) {
    if (!rule.trigger.cooldown || !rule.lastTrigger) {
      return false;
    }
    
    return Date.now() - rule.lastTrigger < rule.trigger.cooldown;
  }

  generateRuleId() {
    return `rule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  setupCleanupInterval() {
    setInterval(() => {
      this.cleanupOldData();
    }, 300000); // Clean up every 5 minutes
  }

  cleanupOldData() {
    const oneHourAgo = Date.now() - 3600000;
    
    // Clean device data
    for (const [deviceId, history] of this.deviceData) {
      const filtered = history.filter(item => item.timestamp > oneHourAgo);
      if (filtered.length === 0) {
        this.deviceData.delete(deviceId);
      } else {
        this.deviceData.set(deviceId, filtered);
      }
    }
    
    // Clean data buffer
    for (const [deviceId, buffer] of this.dataBuffer) {
      const filtered = buffer.filter(item => item.timestamp > oneHourAgo);
      if (filtered.length === 0) {
        this.dataBuffer.delete(deviceId);
      } else {
        this.dataBuffer.set(deviceId, filtered);
      }
    }
  }

  // Rule management methods
  getRules(filters = {}) {
    let rules = Array.from(this.rules.values());
    
    if (filters.group) {
      rules = rules.filter(rule => rule.group === filters.group);
    }
    
    if (filters.enabled !== undefined) {
      rules = rules.filter(rule => rule.enabled === filters.enabled);
    }
    
    if (filters.tags) {
      rules = rules.filter(rule => 
        filters.tags.every(tag => rule.tags.includes(tag))
      );
    }
    
    return rules;
  }

  getRule(ruleId) {
    return this.rules.get(ruleId);
  }

  enableRule(ruleId) {
    return this.updateRule(ruleId, { enabled: true });
  }

  disableRule(ruleId) {
    return this.updateRule(ruleId, { enabled: false });
  }

  getMetrics() {
    return {
      ...this.metrics,
      totalRules: this.rules.size,
      activeRules: Array.from(this.rules.values()).filter(r => r.enabled).length,
      ruleGroups: this.ruleGroups.size,
      devicesTracked: this.deviceData.size
    };
  }

  reset() {
    this.rules.clear();
    this.ruleExecutions.clear();
    this.deviceData.clear();
    this.dataBuffer.clear();
    this.ruleGroups.clear();
    this.metrics = {
      rulesEvaluated: 0,
      rulesTriggered: 0,
      evaluationTime: 0,
      errors: 0
    };
  }
}

module.exports = RuleEngine;