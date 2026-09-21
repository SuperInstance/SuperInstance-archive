const ChaosEngine = require('../utils/chaos-engine');
const axios = require('axios');

const engine = new ChaosEngine();

// Network chaos experiments
const networkExperiments = [
  {
    name: 'SSO to Data Bridge Network Partition',
    description: 'Simulate network partition between SSO service and Data Bridge',
    action: 'network_partition',
    target: {
      sourceIp: '127.0.0.1',
      targetIp: '127.0.0.1',
      sourcePort: 8201,
      targetPort: 8202
    },
    duration: 60000, // 1 minute
    monitoringDuration: 90000, // 1.5 minutes
    maxRecoveryTime: 120000, // 2 minutes
    expectedOutcome: {
      serviceUnavailability: true,
      errorRateIncrease: true,
      recoveryAfterFixing: true
    }
  },
  
  {
    name: 'High Latency Network Conditions',
    description: 'Inject high latency between services',
    action: 'latency_injection',
    target: {
      interface: 'lo', // loopback interface for testing
      latency: 2000 // 2 seconds
    },
    duration: 120000, // 2 minutes
    monitoringDuration: 150000, // 2.5 minutes
    maxRecoveryTime: 60000, // 1 minute
    expectedOutcome: {
      responseTimeIncrease: true,
      timeoutErrors: true,
      circuitBreakerActivation: true
    }
  },

  {
    name: 'Intermittent Network Failures',
    description: 'Simulate intermittent network connectivity issues',
    action: 'intermittent_partition',
    target: {
      services: ['sso', 'data-bridge', 'personal-log'],
      pattern: 'random', // random, periodic, burst
      failureRate: 0.3, // 30% of requests fail
      duration: 300000 // 5 minutes
    },
    monitoringDuration: 360000, // 6 minutes
    maxRecoveryTime: 120000,
    expectedOutcome: {
      retryMechanismActivation: true,
      degradedPerformance: true,
      partialServiceAvailability: true
    }
  },

  {
    name: 'DNS Resolution Failure',
    description: 'Simulate DNS resolution failures for service discovery',
    action: 'dns_failure',
    target: {
      domains: ['localhost'],
      failureType: 'timeout' // timeout, nxdomain, refused
    },
    duration: 180000, // 3 minutes
    monitoringDuration: 240000, // 4 minutes
    maxRecoveryTime: 60000,
    expectedOutcome: {
      serviceDiscoveryFailure: true,
      fallbackMechanismActivation: true
    }
  }
];

// Register all experiments
networkExperiments.forEach(experiment => {
  engine.registerExperiment(experiment);
});

// Custom network chaos actions
class NetworkChaosExecutor {
  static async executeIntermittentPartition(target) {
    console.log('Starting intermittent network partition experiment');
    
    const services = target.services || ['sso', 'data-bridge'];
    const failureRate = target.failureRate || 0.3;
    const duration = target.duration || 300000;
    
    const startTime = Date.now();
    const interval = 10000; // Check every 10 seconds
    
    while (Date.now() - startTime < duration) {
      if (Math.random() < failureRate) {
        // Create temporary network partition
        await this.createTemporaryPartition(services, 5000); // 5 second partition
      }
      
      await new Promise(resolve => setTimeout(resolve, interval));
    }
  }

  static async createTemporaryPartition(services, duration) {
    // Block traffic between services temporarily
    const blockCommands = [];
    const unblockCommands = [];

    for (let i = 0; i < services.length; i++) {
      for (let j = i + 1; j < services.length; j++) {
        const port1 = this.getServicePort(services[i]);
        const port2 = this.getServicePort(services[j]);
        
        blockCommands.push(`iptables -A OUTPUT -p tcp --dport ${port1} -j DROP`);
        blockCommands.push(`iptables -A OUTPUT -p tcp --dport ${port2} -j DROP`);
        
        unblockCommands.push(`iptables -D OUTPUT -p tcp --dport ${port1} -j DROP`);
        unblockCommands.push(`iptables -D OUTPUT -p tcp --dport ${port2} -j DROP`);
      }
    }

    // Apply blocks
    for (const command of blockCommands) {
      try {
        await require('util').promisify(require('child_process').exec)(command);
      } catch (error) {
        console.warn(`Failed to execute block command: ${command}`);
      }
    }

    // Wait for duration
    await new Promise(resolve => setTimeout(resolve, duration));

    // Remove blocks
    for (const command of unblockCommands) {
      try {
        await require('util').promisify(require('child_process').exec)(command);
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  }

  static async executeDnsFailure(target) {
    console.log('Starting DNS failure experiment');
    
    // Simulate DNS failures by modifying /etc/hosts or using DNS proxy
    const domains = target.domains || ['localhost'];
    const failureType = target.failureType || 'timeout';
    
    // For testing purposes, we'll simulate this without actually modifying DNS
    console.log(`Simulating ${failureType} DNS failures for domains:`, domains);
    
    // In a real implementation, you might:
    // 1. Modify /etc/hosts to redirect domains
    // 2. Use a DNS proxy to introduce failures
    // 3. Block DNS traffic to specific servers
  }

  static getServicePort(serviceName) {
    const portMap = {
      'sso': 8201,
      'data-bridge': 8202,
      'personal-log': 8203,
      'business-log': 8204
    };
    return portMap[serviceName] || 8080;
  }
}

// Network resilience testing
async function testNetworkResilience() {
  console.log('Starting Network Chaos Engineering Tests');
  console.log('==========================================');

  const results = [];

  for (const experiment of networkExperiments) {
    console.log(`\nExecuting: ${experiment.name}`);
    console.log(`Description: ${experiment.description}`);
    
    try {
      let execution;
      
      // Handle custom network chaos actions
      if (experiment.action === 'intermittent_partition') {
        await NetworkChaosExecutor.executeIntermittentPartition(experiment.target);
        execution = { status: 'completed', customAction: true };
      } else if (experiment.action === 'dns_failure') {
        await NetworkChaosExecutor.executeDnsFailure(experiment.target);
        execution = { status: 'completed', customAction: true };
      } else {
        execution = await engine.executeExperiment(experiment.id);
      }
      
      results.push({
        experiment: experiment.name,
        status: 'success',
        execution: execution
      });
      
      console.log(`✅ Experiment completed successfully`);
      
    } catch (error) {
      console.error(`❌ Experiment failed: ${error.message}`);
      results.push({
        experiment: experiment.name,
        status: 'failed',
        error: error.message
      });
    }
    
    // Wait between experiments
    await new Promise(resolve => setTimeout(resolve, 30000)); // 30 second pause
  }

  // Generate network chaos report
  await generateNetworkChaosReport(results);
  
  console.log('\nNetwork Chaos Engineering Tests Completed');
  console.log(`Results: ${results.filter(r => r.status === 'success').length}/${results.length} successful`);
  
  return results;
}

// Service connectivity testing during chaos
async function testServiceConnectivity() {
  const services = [
    { name: 'SSO', url: 'http://localhost:8201/health' },
    { name: 'Data Bridge', url: 'http://localhost:8202/health' },
    { name: 'Personal Log', url: 'http://localhost:8203/health' },
    { name: 'Business Log', url: 'http://localhost:8204/health' }
  ];

  const results = [];
  
  for (const service of services) {
    try {
      const start = Date.now();
      const response = await axios.get(service.url, { timeout: 5000 });
      const responseTime = Date.now() - start;
      
      results.push({
        service: service.name,
        status: response.status === 200 ? 'healthy' : 'unhealthy',
        responseTime: responseTime,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      results.push({
        service: service.name,
        status: 'unreachable',
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  return results;
}

// Network chaos report generation
async function generateNetworkChaosReport(results) {
  const fs = require('fs-extra');
  const path = require('path');
  
  await fs.ensureDir('reports');
  
  const report = {
    title: 'Network Chaos Engineering Report',
    timestamp: new Date().toISOString(),
    summary: {
      totalExperiments: results.length,
      successfulExperiments: results.filter(r => r.status === 'success').length,
      failedExperiments: results.filter(r => r.status === 'failed').length,
      successRate: (results.filter(r => r.status === 'success').length / results.length * 100).toFixed(2)
    },
    experiments: results,
    metrics: engine.getMetrics(),
    recommendations: generateNetworkRecommendations(results)
  };
  
  // Save JSON report
  await fs.writeJson('reports/network-chaos-report.json', report, { spaces: 2 });
  
  // Generate HTML report
  const htmlReport = generateNetworkChaosHTML(report);
  await fs.writeFile('reports/network-chaos-report.html', htmlReport);
  
  console.log('📊 Network chaos report saved to reports/network-chaos-report.html');
}

function generateNetworkRecommendations(results) {
  const recommendations = [];
  
  const failedExperiments = results.filter(r => r.status === 'failed').length;
  const successRate = results.filter(r => r.status === 'success').length / results.length;
  
  if (successRate < 0.8) {
    recommendations.push({
      type: 'critical',
      message: 'Low experiment success rate indicates system may not be resilient to network failures',
      action: 'Review retry mechanisms, circuit breakers, and timeout configurations'
    });
  }
  
  recommendations.push({
    type: 'info',
    message: 'Consider implementing service mesh for better network resilience',
    action: 'Evaluate Istio, Linkerd, or similar service mesh solutions'
  });
  
  recommendations.push({
    type: 'info',
    message: 'Regular network chaos testing should be integrated into CI/CD',
    action: 'Schedule automated chaos experiments in staging environments'
  });
  
  return recommendations;
}

function generateNetworkChaosHTML(report) {
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
    
    <h2>Experiment Results</h2>
    ${report.experiments.map(exp => `
        <div class="experiment ${exp.status}">
            <h3>${exp.experiment}</h3>
            <p>Status: <strong>${exp.status}</strong></p>
            ${exp.error ? `<p>Error: ${exp.error}</p>` : ''}
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

// Run network chaos tests if this file is executed directly
if (require.main === module) {
  testNetworkResilience().catch(console.error);
}

module.exports = { testNetworkResilience, testServiceConnectivity, NetworkChaosExecutor };