const Docker = require('dockerode');
const { exec } = require('child_process');
const { promisify } = require('util');
const winston = require('winston');
const fs = require('fs-extra');
const path = require('path');

const execAsync = promisify(exec);
const docker = new Docker();

// Configure logger for chaos testing
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'reports/chaos-error.log', level: 'error' }),
    new winston.transports.File({ filename: 'reports/chaos.log' }),
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    })
  ]
});

class ChaosEngine {
  constructor() {
    this.experiments = [];
    this.activeExperiments = new Map();
    this.metrics = {
      experimentsRun: 0,
      successfulExperiments: 0,
      failedExperiments: 0,
      systemRecoveries: 0,
      meanRecoveryTime: 0
    };
  }

  // Register a chaos experiment
  registerExperiment(experiment) {
    this.experiments.push({
      id: this.generateExperimentId(),
      ...experiment,
      status: 'registered',
      createdAt: new Date().toISOString()
    });
    logger.info(`Registered experiment: ${experiment.name}`);
  }

  // Execute a chaos experiment
  async executeExperiment(experimentId, options = {}) {
    const experiment = this.experiments.find(exp => exp.id === experimentId);
    if (!experiment) {
      throw new Error(`Experiment ${experimentId} not found`);
    }

    logger.info(`Starting chaos experiment: ${experiment.name}`);
    
    const execution = {
      experimentId,
      startTime: Date.now(),
      status: 'running',
      metrics: {},
      logs: []
    };

    this.activeExperiments.set(experimentId, execution);
    this.metrics.experimentsRun++;

    try {
      // Pre-experiment health check
      const preHealthy = await this.checkSystemHealth();
      execution.logs.push({ timestamp: Date.now(), event: 'pre-health-check', healthy: preHealthy });

      if (!preHealthy && !options.allowUnhealthyStart) {
        throw new Error('System is not healthy before experiment start');
      }

      // Execute the chaos action
      await this.executeAction(experiment, execution);

      // Monitor system during chaos
      const monitoringResults = await this.monitorSystem(experiment, execution);
      execution.metrics = { ...execution.metrics, ...monitoringResults };

      // Post-experiment recovery check
      const recovered = await this.waitForRecovery(experiment, execution);
      if (recovered) {
        this.metrics.successfulExperiments++;
        this.metrics.systemRecoveries++;
      } else {
        throw new Error('System failed to recover after experiment');
      }

      execution.status = 'completed';
      execution.endTime = Date.now();
      execution.duration = execution.endTime - execution.startTime;

      logger.info(`Completed chaos experiment: ${experiment.name} in ${execution.duration}ms`);
      
      return execution;

    } catch (error) {
      execution.status = 'failed';
      execution.error = error.message;
      execution.endTime = Date.now();
      execution.duration = execution.endTime - execution.startTime;
      
      this.metrics.failedExperiments++;
      logger.error(`Chaos experiment failed: ${experiment.name}`, error);
      
      // Attempt cleanup
      await this.cleanup(experiment, execution);
      
      throw error;
    } finally {
      this.activeExperiments.delete(experimentId);
      await this.saveExperimentReport(execution);
    }
  }

  // Execute the chaos action based on experiment type
  async executeAction(experiment, execution) {
    logger.info(`Executing chaos action: ${experiment.action}`);

    switch (experiment.action) {
      case 'kill_container':
        await this.killContainer(experiment.target);
        break;
      case 'network_partition':
        await this.createNetworkPartition(experiment.target);
        break;
      case 'resource_stress':
        await this.stressResources(experiment.target);
        break;
      case 'dependency_failure':
        await this.simulateDependencyFailure(experiment.target);
        break;
      case 'data_corruption':
        await this.simulateDataCorruption(experiment.target);
        break;
      case 'latency_injection':
        await this.injectLatency(experiment.target);
        break;
      default:
        throw new Error(`Unknown chaos action: ${experiment.action}`);
    }

    execution.logs.push({
      timestamp: Date.now(),
      event: 'chaos-action-executed',
      action: experiment.action,
      target: experiment.target
    });
  }

  // Kill container chaos
  async killContainer(target) {
    const container = docker.getContainer(target.containerId);
    await container.kill();
    logger.info(`Killed container: ${target.containerId}`);
  }

  // Network partition chaos
  async createNetworkPartition(target) {
    const commands = [
      `iptables -A INPUT -s ${target.sourceIp} -j DROP`,
      `iptables -A OUTPUT -d ${target.targetIp} -j DROP`
    ];

    for (const command of commands) {
      await execAsync(command);
    }
    
    logger.info(`Created network partition between ${target.sourceIp} and ${target.targetIp}`);
  }

  // Resource stress chaos
  async stressResources(target) {
    const stressCommands = {
      cpu: `stress-ng --cpu ${target.cpuCores || 2} --timeout ${target.duration || 60}s`,
      memory: `stress-ng --vm ${target.memoryWorkers || 1} --vm-bytes ${target.memorySize || '1G'} --timeout ${target.duration || 60}s`,
      disk: `stress-ng --hdd ${target.diskWorkers || 1} --hdd-bytes ${target.diskSize || '1G'} --timeout ${target.duration || 60}s`
    };

    const command = stressCommands[target.type] || stressCommands.cpu;
    await execAsync(command);
    
    logger.info(`Applied resource stress: ${target.type} for ${target.duration}s`);
  }

  // Dependency failure simulation
  async simulateDependencyFailure(target) {
    switch (target.type) {
      case 'database':
        await this.stopDatabaseConnection(target);
        break;
      case 'redis':
        await this.stopRedisConnection(target);
        break;
      case 'elasticsearch':
        await this.stopElasticsearchConnection(target);
        break;
      case 'external_api':
        await this.blockExternalAPI(target);
        break;
      default:
        throw new Error(`Unknown dependency type: ${target.type}`);
    }
  }

  // Data corruption simulation
  async simulateDataCorruption(target) {
    if (target.type === 'database') {
      // Simulate database corruption (safely in test environment)
      logger.warn('Simulating database corruption - TEST MODE ONLY');
      // In real implementation, this would introduce controlled data inconsistencies
    }
  }

  // Latency injection
  async injectLatency(target) {
    const command = `tc qdisc add dev ${target.interface} root netem delay ${target.latency}ms`;
    await execAsync(command);
    logger.info(`Injected ${target.latency}ms latency on interface ${target.interface}`);
  }

  // System health checking
  async checkSystemHealth() {
    try {
      const services = [
        { name: 'sso', url: 'http://localhost:8201/health' },
        { name: 'data-bridge', url: 'http://localhost:8202/health' },
        { name: 'personal-log', url: 'http://localhost:8203/health' },
        { name: 'business-log', url: 'http://localhost:8204/health' }
      ];

      const axios = require('axios');
      const healthChecks = await Promise.allSettled(
        services.map(async service => {
          const response = await axios.get(service.url, { timeout: 5000 });
          return { service: service.name, healthy: response.status === 200 };
        })
      );

      const healthyServices = healthChecks.filter(check => 
        check.status === 'fulfilled' && check.value.healthy
      ).length;

      return healthyServices >= Math.ceil(services.length * 0.7); // 70% services must be healthy
    } catch (error) {
      logger.error('Health check failed', error);
      return false;
    }
  }

  // Monitor system during chaos
  async monitorSystem(experiment, execution) {
    const monitoringDuration = experiment.monitoringDuration || 30000; // 30 seconds default
    const interval = 5000; // 5 seconds
    const metrics = {
      responseTimeSpikes: 0,
      errorRateIncrease: 0,
      serviceUnavailability: 0,
      recoveryTime: 0
    };

    const startTime = Date.now();
    
    while (Date.now() - startTime < monitoringDuration) {
      const health = await this.checkSystemHealth();
      const timestamp = Date.now();
      
      execution.logs.push({
        timestamp,
        event: 'health-check',
        healthy: health
      });

      if (!health) {
        metrics.serviceUnavailability++;
      }

      await new Promise(resolve => setTimeout(resolve, interval));
    }

    return metrics;
  }

  // Wait for system recovery
  async waitForRecovery(experiment, execution) {
    const maxWaitTime = experiment.maxRecoveryTime || 120000; // 2 minutes default
    const checkInterval = 5000; // 5 seconds
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTime) {
      const healthy = await this.checkSystemHealth();
      
      if (healthy) {
        const recoveryTime = Date.now() - startTime;
        execution.recoveryTime = recoveryTime;
        
        // Update mean recovery time
        this.updateMeanRecoveryTime(recoveryTime);
        
        logger.info(`System recovered in ${recoveryTime}ms`);
        return true;
      }

      await new Promise(resolve => setTimeout(resolve, checkInterval));
    }

    logger.warn('System failed to recover within timeout');
    return false;
  }

  // Cleanup after experiment
  async cleanup(experiment, execution) {
    logger.info('Cleaning up after chaos experiment');

    try {
      // Cleanup based on experiment type
      switch (experiment.action) {
        case 'network_partition':
          await this.cleanupNetworkRules(experiment.target);
          break;
        case 'latency_injection':
          await this.cleanupLatencyInjection(experiment.target);
          break;
        case 'resource_stress':
          await execAsync('pkill -f stress-ng');
          break;
      }
    } catch (error) {
      logger.error('Cleanup failed', error);
    }
  }

  // Cleanup network rules
  async cleanupNetworkRules(target) {
    const cleanupCommands = [
      `iptables -D INPUT -s ${target.sourceIp} -j DROP`,
      `iptables -D OUTPUT -d ${target.targetIp} -j DROP`
    ];

    for (const command of cleanupCommands) {
      try {
        await execAsync(command);
      } catch (error) {
        // Ignore errors - rule might not exist
      }
    }
  }

  // Cleanup latency injection
  async cleanupLatencyInjection(target) {
    const command = `tc qdisc del dev ${target.interface} root`;
    try {
      await execAsync(command);
    } catch (error) {
      // Ignore errors - rule might not exist
    }
  }

  // Helper methods
  generateExperimentId() {
    return `chaos_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  }

  updateMeanRecoveryTime(newRecoveryTime) {
    if (this.metrics.systemRecoveries === 0) {
      this.metrics.meanRecoveryTime = newRecoveryTime;
    } else {
      this.metrics.meanRecoveryTime = 
        (this.metrics.meanRecoveryTime * (this.metrics.systemRecoveries - 1) + newRecoveryTime) / 
        this.metrics.systemRecoveries;
    }
  }

  async saveExperimentReport(execution) {
    const reportPath = path.join('reports', `chaos-experiment-${execution.experimentId}.json`);
    await fs.ensureDir('reports');
    await fs.writeJson(reportPath, execution, { spaces: 2 });
  }

  // Stop database connections
  async stopDatabaseConnection(target) {
    // This would typically involve stopping database containers or blocking connections
    logger.warn(`Simulating database failure for ${target.database}`);
  }

  // Stop Redis connections
  async stopRedisConnection(target) {
    logger.warn(`Simulating Redis failure for ${target.instance}`);
  }

  // Stop Elasticsearch connections
  async stopElasticsearchConnection(target) {
    logger.warn(`Simulating Elasticsearch failure for ${target.cluster}`);
  }

  // Block external API
  async blockExternalAPI(target) {
    const command = `iptables -A OUTPUT -d ${target.host} -j DROP`;
    await execAsync(command);
    logger.info(`Blocked access to external API: ${target.host}`);
  }

  // Get experiment metrics
  getMetrics() {
    return this.metrics;
  }

  // List active experiments
  getActiveExperiments() {
    return Array.from(this.activeExperiments.entries());
  }
}

module.exports = ChaosEngine;