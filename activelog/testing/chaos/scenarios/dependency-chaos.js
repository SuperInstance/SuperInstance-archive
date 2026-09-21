const ChaosEngine = require('../utils/chaos-engine');
const Docker = require('dockerode');
const redis = require('redis');
const { MongoClient } = require('mongodb');
const { Client: ElasticClient } = require('@elastic/elasticsearch');

const engine = new ChaosEngine();
const docker = new Docker();

// Dependency chaos experiments
const dependencyExperiments = [
  {
    name: 'Redis Cache Failure',
    description: 'Simulate Redis cache service failure to test cache-less operation',
    action: 'dependency_failure',
    target: {
      type: 'redis',
      instance: 'primary',
      failureMode: 'complete_outage', // complete_outage, intermittent, slow_response
      duration: 180000 // 3 minutes
    },
    monitoringDuration: 240000, // 4 minutes
    maxRecoveryTime: 120000, // 2 minutes
    expectedOutcome: {
      cacheMissIncrease: true,
      directDatabaseQueries: true,
      responseTimeIncrease: true,
      gracefulDegradation: true
    }
  },

  {
    name: 'Database Connection Pool Exhaustion',
    description: 'Exhaust database connection pool to test connection management',
    action: 'dependency_failure',
    target: {
      type: 'database',
      database: 'postgresql',
      failureMode: 'connection_exhaustion',
      maxConnections: 10,
      duration: 300000 // 5 minutes
    },
    monitoringDuration: 360000, // 6 minutes
    maxRecoveryTime: 180000, // 3 minutes
    expectedOutcome: {
      connectionQueueing: true,
      connectionTimeouts: true,
      transactionFailures: true,
      circuitBreakerActivation: true
    }
  },

  {
    name: 'Elasticsearch Cluster Partition',
    description: 'Simulate Elasticsearch cluster split-brain scenario',
    action: 'dependency_failure',
    target: {
      type: 'elasticsearch',
      cluster: 'search-cluster',
      failureMode: 'split_brain',
      nodeFailures: ['node-1', 'node-2'],
      duration: 240000 // 4 minutes
    },
    monitoringDuration: 300000, // 5 minutes
    maxRecoveryTime: 240000, // 4 minutes
    expectedOutcome: {
      searchDegradation: true,
      indexingFailures: true,
      clusterRecovery: true,
      dataConsistencyIssues: false
    }
  },

  {
    name: 'External API Service Timeout',
    description: 'Simulate external API timeouts and failures',
    action: 'dependency_failure',
    target: {
      type: 'external_api',
      host: 'api.external-service.com',
      failureMode: 'timeout',
      timeoutMs: 30000,
      failureRate: 0.8, // 80% failure rate
      duration: 360000 // 6 minutes
    },
    monitoringDuration: 420000, // 7 minutes
    maxRecoveryTime: 120000,
    expectedOutcome: {
      retryMechanismActivation: true,
      circuitBreakerOpen: true,
      fallbackServiceUsage: true,
      userExperienceImpact: 'minimal'
    }
  },

  {
    name: 'Message Queue Overflow',
    description: 'Simulate message queue overflow and processing delays',
    action: 'dependency_failure',
    target: {
      type: 'message_queue',
      queue: 'event_processing',
      failureMode: 'overflow',
      maxMessages: 1000,
      processingDelay: 10000, // 10 second delay
      duration: 300000 // 5 minutes
    },
    monitoringDuration: 360000,
    maxRecoveryTime: 180000,
    expectedOutcome: {
      messageBacklog: true,
      processingDelay: true,
      backpressure: true,
      eventualConsistency: true
    }
  },

  {
    name: 'Cascading Service Failures',
    description: 'Test cascade failure handling when multiple dependencies fail',
    action: 'cascading_failure',
    target: {
      primaryService: 'data-bridge',
      dependentServices: ['redis', 'elasticsearch', 'database'],
      failureSequence: [
        { service: 'redis', delay: 0 },
        { service: 'database', delay: 30000 }, // 30s after redis
        { service: 'elasticsearch', delay: 60000 } // 1m after redis
      ],
      duration: 240000 // 4 minutes
    },
    monitoringDuration: 300000,
    maxRecoveryTime: 300000, // 5 minutes for cascading recovery
    expectedOutcome: {
      gracefulDegradation: true,
      circuitBreakerActivation: true,
      serviceIsolation: true,
      partialServiceAvailability: true
    }
  }
];

// Register all experiments
dependencyExperiments.forEach(experiment => {
  engine.registerExperiment(experiment);
});

// Dependency chaos executor
class DependencyChaosExecutor {
  static async executeRedisFailure(target) {
    console.log('Starting Redis failure experiment');
    
    const failureMode = target.failureMode || 'complete_outage';
    const duration = target.duration || 180000;
    
    switch (failureMode) {
      case 'complete_outage':
        await this.simulateRedisOutage(duration);
        break;
      case 'intermittent':
        await this.simulateIntermittentRedis(duration);
        break;
      case 'slow_response':
        await this.simulateSlowRedis(duration);
        break;
    }
  }

  static async simulateRedisOutage(duration) {
    // Find and stop Redis container
    try {
      const containers = await docker.listContainers();
      const redisContainer = containers.find(container => 
        container.Image.includes('redis') || container.Names.some(name => name.includes('redis'))
      );

      if (redisContainer) {
        const container = docker.getContainer(redisContainer.Id);
        await container.stop();
        console.log('Stopped Redis container');
        
        // Wait for duration
        await new Promise(resolve => setTimeout(resolve, duration));
        
        // Restart Redis
        await container.start();
        console.log('Restarted Redis container');
      } else {
        // Simulate by blocking Redis port
        await this.blockPort(6379, duration);
      }
    } catch (error) {
      console.warn('Could not control Redis container, using port blocking');
      await this.blockPort(6379, duration);
    }
  }

  static async simulateIntermittentRedis(duration) {
    const startTime = Date.now();
    const failureInterval = 30000; // 30 second intervals
    const failureDuration = 10000; // 10 second failures
    
    while (Date.now() - startTime < duration) {
      // Create temporary failure
      const blockPromise = this.blockPort(6379, failureDuration);
      
      // Wait for failure to resolve
      await new Promise(resolve => setTimeout(resolve, failureDuration));
      
      // Wait before next failure
      await new Promise(resolve => setTimeout(resolve, failureInterval - failureDuration));
    }
  }

  static async simulateSlowRedis(duration) {
    // Use traffic control to add latency to Redis port
    const { exec } = require('child_process');
    const { promisify } = require('util');
    const execAsync = promisify(exec);
    
    try {
      await execAsync('tc qdisc add dev lo root netem delay 5000ms');
      console.log('Added 5s delay to localhost traffic');
      
      await new Promise(resolve => setTimeout(resolve, duration));
      
    } finally {
      try {
        await execAsync('tc qdisc del dev lo root');
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  }

  static async executeDatabaseFailure(target) {
    console.log('Starting database failure experiment');
    
    const failureMode = target.failureMode || 'connection_exhaustion';
    const duration = target.duration || 300000;
    
    if (failureMode === 'connection_exhaustion') {
      await this.exhaustDatabaseConnections(target, duration);
    }
  }

  static async exhaustDatabaseConnections(target, duration) {
    const maxConnections = target.maxConnections || 10;
    const connections = [];
    
    try {
      // Create maximum connections to exhaust pool
      for (let i = 0; i < maxConnections; i++) {
        try {
          const client = new MongoClient(process.env.MONGODB_URL || 'mongodb://localhost:27017');
          await client.connect();
          connections.push(client);
        } catch (error) {
          console.warn(`Failed to create connection ${i}: ${error.message}`);
        }
      }
      
      console.log(`Exhausted ${connections.length} database connections`);
      
      // Keep connections open for duration
      await new Promise(resolve => setTimeout(resolve, duration));
      
    } finally {
      // Close all connections
      for (const client of connections) {
        try {
          await client.close();
        } catch (error) {
          // Ignore close errors
        }
      }
      console.log('Released all database connections');
    }
  }

  static async executeElasticsearchFailure(target) {
    console.log('Starting Elasticsearch failure experiment');
    
    const failureMode = target.failureMode || 'split_brain';
    const duration = target.duration || 240000;
    
    if (failureMode === 'split_brain') {
      await this.simulateElasticsearchSplitBrain(target, duration);
    }
  }

  static async simulateElasticsearchSplitBrain(target, duration) {
    // Simulate by stopping specific Elasticsearch nodes or blocking network
    try {
      const containers = await docker.listContainers();
      const esContainers = containers.filter(container => 
        container.Image.includes('elasticsearch') || 
        container.Names.some(name => name.includes('elasticsearch'))
      );

      if (esContainers.length > 0) {
        // Stop half the containers to simulate split-brain
        const containersToStop = esContainers.slice(0, Math.ceil(esContainers.length / 2));
        
        for (const containerInfo of containersToStop) {
          const container = docker.getContainer(containerInfo.Id);
          await container.stop();
          console.log(`Stopped Elasticsearch container: ${containerInfo.Names[0]}`);
        }
        
        // Wait for duration
        await new Promise(resolve => setTimeout(resolve, duration));
        
        // Restart containers
        for (const containerInfo of containersToStop) {
          const container = docker.getContainer(containerInfo.Id);
          await container.start();
          console.log(`Restarted Elasticsearch container: ${containerInfo.Names[0]}`);
        }
      } else {
        // Block Elasticsearch port
        await this.blockPort(9200, duration);
      }
    } catch (error) {
      console.warn('Could not control Elasticsearch containers, using port blocking');
      await this.blockPort(9200, duration);
    }
  }

  static async executeExternalApiFailure(target) {
    console.log('Starting external API failure experiment');
    
    const host = target.host;
    const failureMode = target.failureMode || 'timeout';
    const duration = target.duration || 360000;
    
    // Block outgoing connections to external API
    const { exec } = require('child_process');
    const { promisify } = require('util');
    const execAsync = promisify(exec);
    
    try {
      await execAsync(`iptables -A OUTPUT -d ${host} -j DROP`);
      console.log(`Blocked outgoing connections to ${host}`);
      
      await new Promise(resolve => setTimeout(resolve, duration));
      
    } finally {
      try {
        await execAsync(`iptables -D OUTPUT -d ${host} -j DROP`);
        console.log(`Restored connections to ${host}`);
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  }

  static async executeCascadingFailure(target) {
    console.log('Starting cascading failure experiment');
    
    const failureSequence = target.failureSequence || [];
    const duration = target.duration || 240000;
    
    // Start failures in sequence
    const failurePromises = [];
    
    for (const failure of failureSequence) {
      const promise = new Promise(async (resolve) => {
        // Wait for delay
        await new Promise(r => setTimeout(r, failure.delay));
        
        // Execute failure
        console.log(`Triggering failure for service: ${failure.service}`);
        await this.triggerServiceFailure(failure.service, duration - failure.delay);
        
        resolve();
      });
      
      failurePromises.push(promise);
    }
    
    // Wait for all failures to complete
    await Promise.all(failurePromises);
  }

  static async triggerServiceFailure(serviceName, duration) {
    switch (serviceName) {
      case 'redis':
        await this.simulateRedisOutage(duration);
        break;
      case 'database':
        await this.blockPort(27017, duration); // MongoDB port
        break;
      case 'elasticsearch':
        await this.blockPort(9200, duration);
        break;
      default:
        console.warn(`Unknown service: ${serviceName}`);
    }
  }

  static async blockPort(port, duration) {
    const { exec } = require('child_process');
    const { promisify } = require('util');
    const execAsync = promisify(exec);
    
    try {
      await execAsync(`iptables -A INPUT -p tcp --dport ${port} -j DROP`);
      await execAsync(`iptables -A OUTPUT -p tcp --dport ${port} -j DROP`);
      console.log(`Blocked port ${port}`);
      
      await new Promise(resolve => setTimeout(resolve, duration));
      
    } finally {
      try {
        await execAsync(`iptables -D INPUT -p tcp --dport ${port} -j DROP`);
        await execAsync(`iptables -D OUTPUT -p tcp --dport ${port} -j DROP`);
        console.log(`Unblocked port ${port}`);
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  }
}

// Dependency health monitoring
class DependencyMonitor {
  static async checkDependencyHealth() {
    const dependencies = [
      { name: 'Redis', check: () => this.checkRedis() },
      { name: 'Database', check: () => this.checkDatabase() },
      { name: 'Elasticsearch', check: () => this.checkElasticsearch() },
      { name: 'External API', check: () => this.checkExternalAPI() }
    ];

    const results = [];
    
    for (const dep of dependencies) {
      try {
        const startTime = Date.now();
        const healthy = await dep.check();
        const responseTime = Date.now() - startTime;
        
        results.push({
          dependency: dep.name,
          healthy: healthy,
          responseTime: responseTime,
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        results.push({
          dependency: dep.name,
          healthy: false,
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    }
    
    return results;
  }

  static async checkRedis() {
    const client = redis.createClient({ url: 'redis://localhost:6379' });
    try {
      await client.connect();
      await client.ping();
      await client.disconnect();
      return true;
    } catch (error) {
      return false;
    }
  }

  static async checkDatabase() {
    const client = new MongoClient(process.env.MONGODB_URL || 'mongodb://localhost:27017');
    try {
      await client.connect();
      await client.db().admin().ping();
      await client.close();
      return true;
    } catch (error) {
      return false;
    }
  }

  static async checkElasticsearch() {
    const client = new ElasticClient({ node: 'http://localhost:9200' });
    try {
      await client.ping();
      return true;
    } catch (error) {
      return false;
    }
  }

  static async checkExternalAPI() {
    const axios = require('axios');
    try {
      await axios.get('http://httpbin.org/status/200', { timeout: 5000 });
      return true;
    } catch (error) {
      return false;
    }
  }
}

// Dependency resilience testing
async function testDependencyResilience() {
  console.log('Starting Dependency Chaos Engineering Tests');
  console.log('=============================================');

  const results = [];

  for (const experiment of dependencyExperiments) {
    console.log(`\nExecuting: ${experiment.name}`);
    console.log(`Description: ${experiment.description}`);
    
    // Monitor dependencies before experiment
    const preHealth = await DependencyMonitor.checkDependencyHealth();
    
    try {
      let execution;
      
      // Handle custom dependency chaos actions
      if (experiment.action === 'dependency_failure') {
        switch (experiment.target.type) {
          case 'redis':
            await DependencyChaosExecutor.executeRedisFailure(experiment.target);
            break;
          case 'database':
            await DependencyChaosExecutor.executeDatabaseFailure(experiment.target);
            break;
          case 'elasticsearch':
            await DependencyChaosExecutor.executeElasticsearchFailure(experiment.target);
            break;
          case 'external_api':
            await DependencyChaosExecutor.executeExternalApiFailure(experiment.target);
            break;
        }
        execution = { status: 'completed', customAction: true };
      } else if (experiment.action === 'cascading_failure') {
        await DependencyChaosExecutor.executeCascadingFailure(experiment.target);
        execution = { status: 'completed', customAction: true };
      } else {
        execution = await engine.executeExperiment(experiment.id);
      }
      
      // Monitor dependencies after experiment
      const postHealth = await DependencyMonitor.checkDependencyHealth();
      
      results.push({
        experiment: experiment.name,
        status: 'success',
        execution: execution,
        preHealth: preHealth,
        postHealth: postHealth,
        healthComparison: this.compareDependencyHealth(preHealth, postHealth)
      });
      
      console.log(`✅ Experiment completed successfully`);
      
    } catch (error) {
      console.error(`❌ Experiment failed: ${error.message}`);
      
      const postHealth = await DependencyMonitor.checkDependencyHealth();
      
      results.push({
        experiment: experiment.name,
        status: 'failed',
        error: error.message,
        preHealth: preHealth,
        postHealth: postHealth,
        healthComparison: this.compareDependencyHealth(preHealth, postHealth)
      });
    }
    
    // Recovery period between experiments
    console.log('Waiting for system recovery...');
    await new Promise(resolve => setTimeout(resolve, 90000)); // 90 second recovery
  }

  // Generate dependency chaos report
  await generateDependencyChaosReport(results);
  
  console.log('\nDependency Chaos Engineering Tests Completed');
  console.log(`Results: ${results.filter(r => r.status === 'success').length}/${results.length} successful`);
  
  return results;
}

function compareDependencyHealth(preHealth, postHealth) {
  const comparison = {
    recovered: [],
    degraded: [],
    unchanged: []
  };

  const preMap = new Map(preHealth.map(h => [h.dependency, h]));
  
  for (const postDep of postHealth) {
    const preDep = preMap.get(postDep.dependency);
    
    if (!preDep) {
      comparison.unchanged.push(postDep.dependency);
      continue;
    }

    if (preDep.healthy === postDep.healthy) {
      comparison.unchanged.push(postDep.dependency);
    } else if (!preDep.healthy && postDep.healthy) {
      comparison.recovered.push(postDep.dependency);
    } else if (preDep.healthy && !postDep.healthy) {
      comparison.degraded.push(postDep.dependency);
    }
  }

  return comparison;
}

// Generate dependency chaos report
async function generateDependencyChaosReport(results) {
  const fs = require('fs-extra');
  
  await fs.ensureDir('reports');
  
  const report = {
    title: 'Dependency Chaos Engineering Report',
    timestamp: new Date().toISOString(),
    summary: {
      totalExperiments: results.length,
      successfulExperiments: results.filter(r => r.status === 'success').length,
      failedExperiments: results.filter(r => r.status === 'failed').length,
      successRate: (results.filter(r => r.status === 'success').length / results.length * 100).toFixed(2)
    },
    experiments: results,
    metrics: engine.getMetrics(),
    dependencyAnalysis: analyzeDependencyImpact(results),
    recommendations: generateDependencyRecommendations(results)
  };
  
  // Save JSON report
  await fs.writeJson('reports/dependency-chaos-report.json', report, { spaces: 2 });
  
  // Generate HTML report
  const htmlReport = generateDependencyChaosHTML(report);
  await fs.writeFile('reports/dependency-chaos-report.html', htmlReport);
  
  console.log('📊 Dependency chaos report saved to reports/dependency-chaos-report.html');
}

function analyzeDependencyImpact(results) {
  const impact = {
    totalRecoveries: 0,
    totalDegradations: 0,
    affectedDependencies: new Set(),
    cascadeFailures: 0
  };

  results.forEach(result => {
    if (result.healthComparison) {
      impact.totalRecoveries += result.healthComparison.recovered.length;
      impact.totalDegradations += result.healthComparison.degraded.length;
      
      result.healthComparison.degraded.forEach(dep => impact.affectedDependencies.add(dep));
      
      if (result.experiment.includes('Cascading')) {
        impact.cascadeFailures++;
      }
    }
  });

  return {
    ...impact,
    affectedDependencies: Array.from(impact.affectedDependencies)
  };
}

function generateDependencyRecommendations(results) {
  const recommendations = [];
  
  const failedExperiments = results.filter(r => r.status === 'failed').length;
  const cascadeFailures = results.filter(r => r.experiment.includes('Cascading')).length;
  
  if (failedExperiments > 0) {
    recommendations.push({
      type: 'critical',
      message: 'Some dependency failure experiments failed',
      action: 'Review circuit breakers, retry mechanisms, and fallback strategies'
    });
  }

  if (cascadeFailures > 0) {
    recommendations.push({
      type: 'warning',
      message: 'Cascading failures detected',
      action: 'Implement bulkhead pattern and service isolation strategies'
    });
  }

  recommendations.push({
    type: 'info',
    message: 'Implement comprehensive dependency monitoring',
    action: 'Set up health checks and alerting for all critical dependencies'
  });

  recommendations.push({
    type: 'info',
    message: 'Regular dependency chaos testing builds resilience',
    action: 'Include dependency failure scenarios in regular testing cycles'
  });

  return recommendations;
}

function generateDependencyChaosHTML(report) {
  return `
<!DOCTYPE html>
<html>
<head>
    <title>${report.title}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .summary { display: flex; justify-content: space-around; margin: 20px 0; }
        .metric { text-align: center; padding: 10px; background: #e9ecef; border-radius: 5px; }
        .experiment { margin: 15px 0; padding: 15px; border-left: 4px solid #007acc; background: #f8f9fa; }
        .success { border-left-color: #28a745; }
        .failed { border-left-color: #dc3545; }
        .health-status { margin: 10px 0; padding: 10px; background: #fff; border: 1px solid #ddd; }
        .healthy { color: #28a745; }
        .unhealthy { color: #dc3545; }
        .recommendations { margin: 20px 0; }
        .recommendation { padding: 10px; margin: 5px 0; border-radius: 5px; }
        .critical { background: #f8d7da; border: 1px solid #f5c6cb; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; }
        .info { background: #d1ecf1; border: 1px solid #bee5eb; }
    </style>
</head>
<body>
    <div class="header">
        <h1>${report.title}</h1>
        <p>Generated: ${report.timestamp}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>${report.summary.totalExperiments}</h3>
            <p>Total Experiments</p>
        </div>
        <div class="metric">
            <h3>${report.summary.successfulExperiments}</h3>
            <p>Successful</p>
        </div>
        <div class="metric">
            <h3>${report.summary.failedExperiments}</h3>
            <p>Failed</p>
        </div>
        <div class="metric">
            <h3>${report.summary.successRate}%</h3>
            <p>Success Rate</p>
        </div>
    </div>
    
    <h2>Dependency Impact Analysis</h2>
    <div class="health-status">
        <p><strong>Total Recoveries:</strong> ${report.dependencyAnalysis.totalRecoveries}</p>
        <p><strong>Total Degradations:</strong> ${report.dependencyAnalysis.totalDegradations}</p>
        <p><strong>Affected Dependencies:</strong> ${report.dependencyAnalysis.affectedDependencies.join(', ') || 'None'}</p>
        <p><strong>Cascade Failures:</strong> ${report.dependencyAnalysis.cascadeFailures}</p>
    </div>
    
    <h2>Experiment Results</h2>
    ${report.experiments.map(exp => `
        <div class="experiment ${exp.status}">
            <h3>${exp.experiment}</h3>
            <p>Status: <strong>${exp.status}</strong></p>
            ${exp.error ? `<p>Error: ${exp.error}</p>` : ''}
            ${exp.healthComparison ? `
                <div class="health-status">
                    <h4>Health Impact:</h4>
                    <p>Recovered: ${exp.healthComparison.recovered.join(', ') || 'None'}</p>
                    <p>Degraded: ${exp.healthComparison.degraded.join(', ') || 'None'}</p>
                    <p>Unchanged: ${exp.healthComparison.unchanged.join(', ') || 'None'}</p>
                </div>
            ` : ''}
        </div>
    `).join('')}
    
    <h2>Recommendations</h2>
    <div class="recommendations">
        ${report.recommendations.map(rec => `
            <div class="recommendation ${rec.type}">
                <strong>${rec.message}</strong><br>
                <em>Action: ${rec.action}</em>
            </div>
        `).join('')}
    </div>
</body>
</html>
  `;
}

// Run dependency chaos tests if this file is executed directly
if (require.main === module) {
  testDependencyResilience().catch(console.error);
}

module.exports = { testDependencyResilience, DependencyMonitor, DependencyChaosExecutor };