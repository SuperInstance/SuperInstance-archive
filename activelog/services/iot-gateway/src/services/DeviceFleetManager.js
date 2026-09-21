const { EventEmitter } = require('events');

class DeviceFleetManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      maxDevices: options.maxDevices || 100000,
      healthCheckInterval: options.healthCheckInterval || 300000,
      batchSize: options.batchSize || 100,
      commandTimeout: options.commandTimeout || 30000,
      ...options
    };
    
    this.devices = new Map();
    this.deviceGroups = new Map();
    this.deployments = new Map();
    this.commands = new Map();
    this.healthChecks = new Map();
    this.deviceMetrics = new Map();
    
    this.setupHealthCheckInterval();
  }

  // Device Registration and Management
  async registerDevice(deviceConfig) {
    const device = {
      id: deviceConfig.id,
      name: deviceConfig.name || deviceConfig.id,
      type: deviceConfig.type,
      model: deviceConfig.model,
      firmware: {
        version: deviceConfig.firmware?.version,
        updateChannel: deviceConfig.firmware?.updateChannel || 'stable',
        autoUpdate: deviceConfig.firmware?.autoUpdate || false
      },
      
      // Device attributes
      attributes: deviceConfig.attributes || {},
      tags: deviceConfig.tags || [],
      location: deviceConfig.location,
      
      // Connection info
      connectivity: {
        protocol: deviceConfig.connectivity?.protocol || 'mqtt',
        endpoint: deviceConfig.connectivity?.endpoint,
        lastSeen: null,
        status: 'offline',
        signalStrength: null
      },
      
      // Device capabilities
      capabilities: deviceConfig.capabilities || [],
      
      // Groups membership
      groups: deviceConfig.groups || ['default'],
      
      // Security
      security: {
        certificateId: deviceConfig.security?.certificateId,
        keyId: deviceConfig.security?.keyId,
        permissions: deviceConfig.security?.permissions || []
      },
      
      // Metadata
      registeredAt: new Date(),
      lastUpdated: new Date(),
      
      // Operational data
      status: {
        health: 'unknown',
        battery: null,
        temperature: null,
        uptime: null,
        errorCount: 0,
        lastError: null
      }
    };

    if (this.devices.size >= this.options.maxDevices) {
      throw new Error('Maximum device limit reached');
    }

    this.devices.set(device.id, device);
    
    // Add to groups
    for (const groupName of device.groups) {
      this.addDeviceToGroup(device.id, groupName);
    }
    
    // Initialize metrics
    this.deviceMetrics.set(device.id, {
      messagesReceived: 0,
      messagesSent: 0,
      commandsExecuted: 0,
      errors: 0,
      uptime: 0,
      lastSeen: null
    });
    
    this.emit('deviceRegistered', device);
    return device;
  }

  updateDevice(deviceId, updates) {
    const device = this.devices.get(deviceId);
    if (!device) {
      throw new Error(`Device ${deviceId} not found`);
    }

    const updatedDevice = {
      ...device,
      ...updates,
      lastUpdated: new Date()
    };

    // Handle group changes
    if (updates.groups) {
      // Remove from old groups
      for (const groupName of device.groups) {
        this.removeDeviceFromGroup(deviceId, groupName);
      }
      // Add to new groups
      for (const groupName of updates.groups) {
        this.addDeviceToGroup(deviceId, groupName);
      }
    }

    this.devices.set(deviceId, updatedDevice);
    this.emit('deviceUpdated', updatedDevice);
    return updatedDevice;
  }

  unregisterDevice(deviceId) {
    const device = this.devices.get(deviceId);
    if (!device) {
      throw new Error(`Device ${deviceId} not found`);
    }

    // Remove from groups
    for (const groupName of device.groups) {
      this.removeDeviceFromGroup(deviceId, groupName);
    }

    this.devices.delete(deviceId);
    this.deviceMetrics.delete(deviceId);
    this.healthChecks.delete(deviceId);
    
    this.emit('deviceUnregistered', device);
    return true;
  }

  // Device Groups Management
  createDeviceGroup(groupConfig) {
    const group = {
      id: groupConfig.id,
      name: groupConfig.name || groupConfig.id,
      description: groupConfig.description,
      
      // Group criteria
      criteria: groupConfig.criteria || {},
      
      // Group settings
      settings: {
        autoUpdate: groupConfig.settings?.autoUpdate || false,
        updateChannel: groupConfig.settings?.updateChannel || 'stable',
        healthCheckInterval: groupConfig.settings?.healthCheckInterval || this.options.healthCheckInterval,
        commandTimeout: groupConfig.settings?.commandTimeout || this.options.commandTimeout
      },
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      
      // Devices in group
      devices: new Set(),
      
      // Group policies
      policies: groupConfig.policies || []
    };

    this.deviceGroups.set(group.id, group);
    this.emit('groupCreated', group);
    return group;
  }

  updateDeviceGroup(groupId, updates) {
    const group = this.deviceGroups.get(groupId);
    if (!group) {
      throw new Error(`Device group ${groupId} not found`);
    }

    const updatedGroup = {
      ...group,
      ...updates,
      updatedAt: new Date()
    };

    this.deviceGroups.set(groupId, updatedGroup);
    this.emit('groupUpdated', updatedGroup);
    return updatedGroup;
  }

  deleteDeviceGroup(groupId) {
    const group = this.deviceGroups.get(groupId);
    if (!group) {
      throw new Error(`Device group ${groupId} not found`);
    }

    // Update devices to remove group membership
    for (const deviceId of group.devices) {
      const device = this.devices.get(deviceId);
      if (device) {
        device.groups = device.groups.filter(g => g !== groupId);
        this.devices.set(deviceId, device);
      }
    }

    this.deviceGroups.delete(groupId);
    this.emit('groupDeleted', group);
    return true;
  }

  addDeviceToGroup(deviceId, groupName) {
    if (!this.deviceGroups.has(groupName)) {
      this.createDeviceGroup({ id: groupName, name: groupName });
    }
    
    const group = this.deviceGroups.get(groupName);
    group.devices.add(deviceId);
    
    const device = this.devices.get(deviceId);
    if (device && !device.groups.includes(groupName)) {
      device.groups.push(groupName);
    }
  }

  removeDeviceFromGroup(deviceId, groupName) {
    const group = this.deviceGroups.get(groupName);
    if (group) {
      group.devices.delete(deviceId);
    }
    
    const device = this.devices.get(deviceId);
    if (device) {
      device.groups = device.groups.filter(g => g !== groupName);
    }
  }

  // Device Commands and Control
  async sendCommand(deviceId, command, params = {}, options = {}) {
    const device = this.devices.get(deviceId);
    if (!device) {
      throw new Error(`Device ${deviceId} not found`);
    }

    if (device.connectivity.status !== 'online') {
      throw new Error(`Device ${deviceId} is offline`);
    }

    const commandId = this.generateCommandId();
    const commandObj = {
      id: commandId,
      deviceId,
      command,
      params,
      status: 'pending',
      createdAt: Date.now(),
      timeout: options.timeout || this.options.commandTimeout,
      retries: options.retries || 0,
      maxRetries: options.maxRetries || 3,
      priority: options.priority || 'normal'
    };

    this.commands.set(commandId, commandObj);
    
    // Set timeout for command
    setTimeout(() => {
      this.handleCommandTimeout(commandId);
    }, commandObj.timeout);

    this.emit('commandSent', commandObj);
    return commandId;
  }

  async sendGroupCommand(groupId, command, params = {}, options = {}) {
    const group = this.deviceGroups.get(groupId);
    if (!group) {
      throw new Error(`Device group ${groupId} not found`);
    }

    const results = [];
    const batchSize = options.batchSize || this.options.batchSize;
    const deviceIds = Array.from(group.devices);
    
    // Process in batches
    for (let i = 0; i < deviceIds.length; i += batchSize) {
      const batch = deviceIds.slice(i, i + batchSize);
      const batchPromises = batch.map(deviceId => 
        this.sendCommand(deviceId, command, params, options)
          .then(commandId => ({ deviceId, commandId, success: true }))
          .catch(error => ({ deviceId, error: error.message, success: false }))
      );
      
      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);
      
      // Add delay between batches if specified
      if (options.batchDelay && i + batchSize < deviceIds.length) {
        await this.delay(options.batchDelay);
      }
    }

    this.emit('groupCommandSent', { groupId, command, results });
    return results;
  }

  handleCommandResponse(commandId, response) {
    const command = this.commands.get(commandId);
    if (!command) {
      return;
    }

    command.status = response.success ? 'completed' : 'failed';
    command.response = response;
    command.completedAt = Date.now();

    if (response.success) {
      // Update device metrics
      const metrics = this.deviceMetrics.get(command.deviceId);
      if (metrics) {
        metrics.commandsExecuted++;
      }
    } else {
      // Handle retry logic
      if (command.retries < command.maxRetries) {
        command.retries++;
        command.status = 'retrying';
        
        setTimeout(() => {
          this.retryCommand(commandId);
        }, Math.pow(2, command.retries) * 1000); // Exponential backoff
      } else {
        command.status = 'failed';
        this.updateDeviceErrorCount(command.deviceId);
      }
    }

    this.emit('commandResponse', command);
  }

  handleCommandTimeout(commandId) {
    const command = this.commands.get(commandId);
    if (!command || command.status !== 'pending') {
      return;
    }

    if (command.retries < command.maxRetries) {
      command.retries++;
      command.status = 'retrying';
      
      setTimeout(() => {
        this.retryCommand(commandId);
      }, Math.pow(2, command.retries) * 1000);
    } else {
      command.status = 'timeout';
      command.completedAt = Date.now();
      this.updateDeviceErrorCount(command.deviceId);
      this.emit('commandTimeout', command);
    }
  }

  async retryCommand(commandId) {
    const command = this.commands.get(commandId);
    if (!command) {
      return;
    }

    command.status = 'pending';
    this.emit('commandRetry', command);
    
    // Reset timeout
    setTimeout(() => {
      this.handleCommandTimeout(commandId);
    }, command.timeout);
  }

  // Device Health Monitoring
  updateDeviceStatus(deviceId, statusUpdate) {
    const device = this.devices.get(deviceId);
    if (!device) {
      return;
    }

    const oldStatus = device.connectivity.status;
    
    // Update connectivity
    if (statusUpdate.connectivity) {
      Object.assign(device.connectivity, statusUpdate.connectivity);
      device.connectivity.lastSeen = Date.now();
    }
    
    // Update device status
    if (statusUpdate.status) {
      Object.assign(device.status, statusUpdate.status);
    }
    
    // Update metrics
    const metrics = this.deviceMetrics.get(deviceId);
    if (metrics) {
      metrics.lastSeen = Date.now();
      if (statusUpdate.messagesReceived) {
        metrics.messagesReceived += statusUpdate.messagesReceived;
      }
      if (statusUpdate.messagesSent) {
        metrics.messagesSent += statusUpdate.messagesSent;
      }
    }

    device.lastUpdated = new Date();
    
    // Emit status change event
    if (oldStatus !== device.connectivity.status) {
      this.emit('deviceStatusChanged', {
        deviceId,
        oldStatus,
        newStatus: device.connectivity.status,
        device
      });
    }
    
    this.emit('deviceUpdated', device);
  }

  async performHealthCheck(deviceId) {
    const device = this.devices.get(deviceId);
    if (!device) {
      return null;
    }

    const healthCheck = {
      deviceId,
      timestamp: Date.now(),
      status: 'pending'
    };

    this.healthChecks.set(deviceId, healthCheck);

    try {
      // Send health check command
      const commandId = await this.sendCommand(deviceId, 'health_check', {}, {
        timeout: 10000,
        priority: 'high'
      });
      
      healthCheck.commandId = commandId;
      healthCheck.status = 'sent';
      
      this.emit('healthCheckStarted', healthCheck);
      return healthCheck;
      
    } catch (error) {
      healthCheck.status = 'error';
      healthCheck.error = error.message;
      this.emit('healthCheckError', healthCheck);
      return healthCheck;
    }
  }

  setupHealthCheckInterval() {
    setInterval(async () => {
      await this.performBulkHealthCheck();
    }, this.options.healthCheckInterval);
  }

  async performBulkHealthCheck() {
    const onlineDevices = Array.from(this.devices.values())
      .filter(device => device.connectivity.status === 'online');
    
    const batchSize = this.options.batchSize;
    
    for (let i = 0; i < onlineDevices.length; i += batchSize) {
      const batch = onlineDevices.slice(i, i + batchSize);
      
      const healthCheckPromises = batch.map(device => 
        this.performHealthCheck(device.id).catch(error => ({
          deviceId: device.id,
          error: error.message
        }))
      );
      
      await Promise.all(healthCheckPromises);
      
      // Add delay between batches
      if (i + batchSize < onlineDevices.length) {
        await this.delay(1000);
      }
    }
  }

  // Deployment Management
  async createDeployment(deploymentConfig) {
    const deployment = {
      id: deploymentConfig.id || this.generateDeploymentId(),
      name: deploymentConfig.name,
      description: deploymentConfig.description,
      
      // Target devices/groups
      targets: {
        devices: deploymentConfig.targets?.devices || [],
        groups: deploymentConfig.targets?.groups || [],
        criteria: deploymentConfig.targets?.criteria || {}
      },
      
      // Deployment content
      type: deploymentConfig.type, // 'firmware', 'config', 'command'
      content: deploymentConfig.content,
      
      // Deployment strategy
      strategy: {
        type: deploymentConfig.strategy?.type || 'immediate',
        batchSize: deploymentConfig.strategy?.batchSize || this.options.batchSize,
        batchDelay: deploymentConfig.strategy?.batchDelay || 0,
        rollbackOnFailure: deploymentConfig.strategy?.rollbackOnFailure || true,
        maxFailures: deploymentConfig.strategy?.maxFailures || 10
      },
      
      // Status
      status: 'pending',
      progress: {
        total: 0,
        completed: 0,
        failed: 0,
        inProgress: 0
      },
      
      // Metadata
      createdAt: new Date(),
      startedAt: null,
      completedAt: null,
      
      // Results
      results: []
    };

    // Calculate target devices
    const targetDevices = this.resolveDeploymentTargets(deployment.targets);
    deployment.progress.total = targetDevices.size;

    this.deployments.set(deployment.id, deployment);
    this.emit('deploymentCreated', deployment);
    
    return deployment;
  }

  async startDeployment(deploymentId) {
    const deployment = this.deployments.get(deploymentId);
    if (!deployment) {
      throw new Error(`Deployment ${deploymentId} not found`);
    }

    if (deployment.status !== 'pending') {
      throw new Error(`Deployment ${deploymentId} is not in pending state`);
    }

    deployment.status = 'running';
    deployment.startedAt = new Date();
    
    const targetDevices = this.resolveDeploymentTargets(deployment.targets);
    
    this.emit('deploymentStarted', deployment);
    
    // Execute deployment based on strategy
    if (deployment.strategy.type === 'immediate') {
      await this.executeImmediateDeployment(deployment, targetDevices);
    } else if (deployment.strategy.type === 'batched') {
      await this.executeBatchedDeployment(deployment, targetDevices);
    } else if (deployment.strategy.type === 'canary') {
      await this.executeCanaryDeployment(deployment, targetDevices);
    }
    
    return deployment;
  }

  async executeImmediateDeployment(deployment, targetDevices) {
    const deviceIds = Array.from(targetDevices);
    
    const promises = deviceIds.map(deviceId => 
      this.executeDeploymentOnDevice(deployment, deviceId)
    );
    
    const results = await Promise.allSettled(promises);
    this.processDeploymentResults(deployment, results, deviceIds);
  }

  async executeBatchedDeployment(deployment, targetDevices) {
    const deviceIds = Array.from(targetDevices);
    const batchSize = deployment.strategy.batchSize;
    
    for (let i = 0; i < deviceIds.length; i += batchSize) {
      const batch = deviceIds.slice(i, i + batchSize);
      
      const promises = batch.map(deviceId => 
        this.executeDeploymentOnDevice(deployment, deviceId)
      );
      
      const results = await Promise.allSettled(promises);
      this.processDeploymentResults(deployment, results, batch);
      
      // Check if we should continue
      if (deployment.progress.failed > deployment.strategy.maxFailures) {
        deployment.status = 'failed';
        this.emit('deploymentFailed', deployment);
        return;
      }
      
      // Add delay between batches
      if (deployment.strategy.batchDelay && i + batchSize < deviceIds.length) {
        await this.delay(deployment.strategy.batchDelay);
      }
    }
    
    deployment.status = 'completed';
    deployment.completedAt = new Date();
    this.emit('deploymentCompleted', deployment);
  }

  async executeDeploymentOnDevice(deployment, deviceId) {
    const device = this.devices.get(deviceId);
    if (!device || device.connectivity.status !== 'online') {
      throw new Error(`Device ${deviceId} is not available`);
    }

    let command, params;
    
    switch (deployment.type) {
      case 'firmware':
        command = 'firmware_update';
        params = { firmwareUrl: deployment.content.url, version: deployment.content.version };
        break;
      case 'config':
        command = 'update_config';
        params = deployment.content;
        break;
      case 'command':
        command = deployment.content.command;
        params = deployment.content.params;
        break;
      default:
        throw new Error(`Unknown deployment type: ${deployment.type}`);
    }

    return await this.sendCommand(deviceId, command, params, {
      timeout: 120000, // 2 minutes for deployments
      maxRetries: 2
    });
  }

  processDeploymentResults(deployment, results, deviceIds) {
    results.forEach((result, index) => {
      const deviceId = deviceIds[index];
      
      if (result.status === 'fulfilled') {
        deployment.progress.completed++;
        deployment.results.push({
          deviceId,
          status: 'success',
          commandId: result.value
        });
      } else {
        deployment.progress.failed++;
        deployment.results.push({
          deviceId,
          status: 'failed',
          error: result.reason.message
        });
      }
    });
    
    this.emit('deploymentProgress', deployment);
  }

  resolveDeploymentTargets(targets) {
    const deviceIds = new Set();
    
    // Add specific devices
    if (targets.devices) {
      targets.devices.forEach(id => deviceIds.add(id));
    }
    
    // Add devices from groups
    if (targets.groups) {
      targets.groups.forEach(groupId => {
        const group = this.deviceGroups.get(groupId);
        if (group) {
          group.devices.forEach(id => deviceIds.add(id));
        }
      });
    }
    
    // Filter by criteria
    if (targets.criteria && Object.keys(targets.criteria).length > 0) {
      const filteredIds = new Set();
      for (const deviceId of deviceIds) {
        const device = this.devices.get(deviceId);
        if (device && this.matchesCriteria(device, targets.criteria)) {
          filteredIds.add(deviceId);
        }
      }
      return filteredIds;
    }
    
    return deviceIds;
  }

  matchesCriteria(device, criteria) {
    if (criteria.type && device.type !== criteria.type) {
      return false;
    }
    
    if (criteria.model && device.model !== criteria.model) {
      return false;
    }
    
    if (criteria.firmwareVersion) {
      if (criteria.firmwareVersion.operator === 'lt' && 
          !this.compareVersions(device.firmware.version, criteria.firmwareVersion.value, '<')) {
        return false;
      }
    }
    
    if (criteria.tags) {
      if (!criteria.tags.every(tag => device.tags.includes(tag))) {
        return false;
      }
    }
    
    return true;
  }

  compareVersions(v1, v2, operator) {
    const compare = (a, b) => {
      const aParts = a.split('.').map(n => parseInt(n));
      const bParts = b.split('.').map(n => parseInt(n));
      
      for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
        const aPart = aParts[i] || 0;
        const bPart = bParts[i] || 0;
        
        if (aPart < bPart) return -1;
        if (aPart > bPart) return 1;
      }
      return 0;
    };
    
    const result = compare(v1, v2);
    
    switch (operator) {
      case '<': return result < 0;
      case '<=': return result <= 0;
      case '>': return result > 0;
      case '>=': return result >= 0;
      case '==': return result === 0;
      default: return false;
    }
  }

  // Utility Methods
  updateDeviceErrorCount(deviceId) {
    const device = this.devices.get(deviceId);
    if (device) {
      device.status.errorCount++;
      device.status.lastError = new Date();
    }
    
    const metrics = this.deviceMetrics.get(deviceId);
    if (metrics) {
      metrics.errors++;
    }
  }

  generateCommandId() {
    return `cmd_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateDeploymentId() {
    return `deploy_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Query and Analytics Methods
  getDevices(filters = {}) {
    let devices = Array.from(this.devices.values());
    
    if (filters.status) {
      devices = devices.filter(device => device.connectivity.status === filters.status);
    }
    
    if (filters.type) {
      devices = devices.filter(device => device.type === filters.type);
    }
    
    if (filters.group) {
      devices = devices.filter(device => device.groups.includes(filters.group));
    }
    
    if (filters.tags) {
      devices = devices.filter(device => 
        filters.tags.every(tag => device.tags.includes(tag))
      );
    }
    
    return devices;
  }

  getDevice(deviceId) {
    return this.devices.get(deviceId);
  }

  getDeviceGroups() {
    return Array.from(this.deviceGroups.values());
  }

  getDeviceGroup(groupId) {
    return this.deviceGroups.get(groupId);
  }

  getDeployments() {
    return Array.from(this.deployments.values());
  }

  getDeployment(deploymentId) {
    return this.deployments.get(deploymentId);
  }

  getFleetMetrics() {
    const devices = Array.from(this.devices.values());
    const onlineDevices = devices.filter(d => d.connectivity.status === 'online');
    const offlineDevices = devices.filter(d => d.connectivity.status === 'offline');
    
    return {
      totalDevices: devices.length,
      onlineDevices: onlineDevices.length,
      offlineDevices: offlineDevices.length,
      devicesByType: this.getDevicesByType(),
      devicesByGroup: this.getDevicesByGroup(),
      healthyDevices: devices.filter(d => d.status.health === 'healthy').length,
      totalGroups: this.deviceGroups.size,
      activeDeployments: Array.from(this.deployments.values()).filter(d => d.status === 'running').length,
      pendingCommands: Array.from(this.commands.values()).filter(c => c.status === 'pending').length
    };
  }

  getDevicesByType() {
    const typeCount = {};
    for (const device of this.devices.values()) {
      typeCount[device.type] = (typeCount[device.type] || 0) + 1;
    }
    return typeCount;
  }

  getDevicesByGroup() {
    const groupCount = {};
    for (const group of this.deviceGroups.values()) {
      groupCount[group.name] = group.devices.size;
    }
    return groupCount;
  }

  reset() {
    this.devices.clear();
    this.deviceGroups.clear();
    this.deployments.clear();
    this.commands.clear();
    this.healthChecks.clear();
    this.deviceMetrics.clear();
  }
}

module.exports = DeviceFleetManager;