const ChaosEngine = require('../utils/chaos-engine');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);
const engine = new ChaosEngine();

// Resource chaos experiments
const resourceExperiments = [
  {
    name: 'High CPU Load on SSO Service',
    description: 'Stress CPU resources to test service degradation under high load',
    action: 'resource_stress',
    target: {
      type: 'cpu',
      cpuCores: 4,
      duration: 120, // 2 minutes
      intensity: 95 // 95% CPU utilization
    },
    monitoringDuration: 180000, // 3 minutes
    maxRecoveryTime: 60000, // 1 minute
    expectedOutcome: {
      responseTimeIncrease: true,
      requestQueueing: true,
      autoScalingTrigger: true
    }
  },

  {
    name: 'Memory Exhaustion Attack',
    description: 'Consume available memory to test OOM handling and recovery',
    action: 'resource_stress',
    target: {
      type: 'memory',
      memoryWorkers: 2,
      memorySize: '2G',
      duration: 180, // 3 minutes
      pattern: 'gradual' // gradual, burst, sustained
    },
    monitoringDuration: 240000, // 4 minutes
    maxRecoveryTime: 120000, // 2 minutes
    expectedOutcome: {
      memoryPressure: true,
      swapUsage: true,
      oomKillerActivation: true,
      serviceRestart: true
    }
  },

  {
    name: 'Disk I/O Saturation',
    description: 'Saturate disk I/O to test storage bottlenecks',
    action: 'resource_stress',
    target: {
      type: 'disk',
      diskWorkers: 4,
      diskSize: '5G',
      duration: 240, // 4 minutes,
      ioPattern: 'random' // random, sequential
    },
    monitoringDuration: 300000, // 5 minutes
    maxRecoveryTime: 180000, // 3 minutes
    expectedOutcome: {
      diskLatencyIncrease: true,
      databaseSlowdown: true,
      logWriteDelays: true
    }
  },

  {
    name: 'File Descriptor Exhaustion',
    description: 'Exhaust available file descriptors to test resource limit handling',
    action: 'fd_exhaustion',
    target: {
      maxFds: 1024,
      duration: 300000, // 5 minutes
      strategy: 'gradual' // gradual, immediate
    },
    monitoringDuration: 360000, // 6 minutes
    maxRecoveryTime: 120000,
    expectedOutcome: {
      connectionRefusal: true,
      fileOpenFailures: true,
      resourceLimitErrors: true
    }
  },

  {
    name: 'Network Bandwidth Exhaustion',
    description: 'Consume network bandwidth to test network resource limits',
    action: 'bandwidth_exhaustion',
    target: {
      interface: 'lo',
      bandwidth: '100Mbps',
      duration: 180000, // 3 minutes
      trafficType: 'tcp' // tcp, udp, mixed
    },
    monitoringDuration: 240000,
    maxRecoveryTime: 60000,
    expectedOutcome: {
      networkLatencyIncrease: true,
      packetLoss: true,
      connectionTimeouts: true
    }
  }
];

// Register all experiments
resourceExperiments.forEach(experiment => {
  engine.registerExperiment(experiment);
});

// Custom resource chaos executor
class ResourceChaosExecutor {
  static async executeFileDescriptorExhaustion(target) {
    console.log('Starting file descriptor exhaustion experiment');
    
    const maxFds = target.maxFds || 1024;
    const duration = target.duration || 300000;
    const strategy = target.strategy || 'gradual';
    
    if (strategy === 'gradual') {
      await this.gradualFdExhaustion(maxFds, duration);
    } else {
      await this.immediateFdExhaustion(maxFds, duration);
    }
  }

  static async gradualFdExhaustion(maxFds, duration) {
    const startTime = Date.now();
    const interval = duration / maxFds; // Spread over duration
    const openFiles = [];
    
    try {
      while (Date.now() - startTime < duration && openFiles.length < maxFds) {
        // Open file descriptors gradually
        const tempFile = `/tmp/chaos_fd_${Date.now()}_${Math.random()}`;
        const fd = require('fs').openSync(tempFile, 'w');
        openFiles.push({ fd, file: tempFile });
        
        await new Promise(resolve => setTimeout(resolve, interval));
      }
      
      // Keep files open for a while
      await new Promise(resolve => setTimeout(resolve, 30000));
      
    } finally {
      // Cleanup
      openFiles.forEach(({ fd, file }) => {
        try {
          require('fs').closeSync(fd);
          require('fs').unlinkSync(file);
        } catch (error) {
          // Ignore cleanup errors
        }
      });
    }
  }

  static async immediateFdExhaustion(maxFds, duration) {
    const openFiles = [];
    
    try {
      // Open all file descriptors immediately
      for (let i = 0; i < maxFds; i++) {
        const tempFile = `/tmp/chaos_fd_${Date.now()}_${i}`;
        const fd = require('fs').openSync(tempFile, 'w');
        openFiles.push({ fd, file: tempFile });
      }
      
      // Keep files open for duration
      await new Promise(resolve => setTimeout(resolve, duration));
      
    } finally {
      // Cleanup
      openFiles.forEach(({ fd, file }) => {
        try {
          require('fs').closeSync(fd);
          require('fs').unlinkSync(file);
        } catch (error) {
          // Ignore cleanup errors
        }
      });
    }
  }

  static async executeBandwidthExhaustion(target) {
    console.log('Starting bandwidth exhaustion experiment');
    
    const interface = target.interface || 'lo';
    const bandwidth = target.bandwidth || '100Mbps';
    const duration = target.duration || 180000;
    const trafficType = target.trafficType || 'tcp';
    
    // Use traffic control to limit bandwidth
    try {
      await execAsync(`tc qdisc add dev ${interface} root handle 1: htb default 10`);
      await execAsync(`tc class add dev ${interface} parent 1: classid 1:1 htb rate ${bandwidth}`);
      await execAsync(`tc class add dev ${interface} parent 1:1 classid 1:10 htb rate ${bandwidth} ceil ${bandwidth}`);
      
      // Generate traffic to consume bandwidth
      await this.generateTraffic(trafficType, duration);
      
    } finally {
      // Cleanup traffic control rules
      try {
        await execAsync(`tc qdisc del dev ${interface} root`);
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  }

  static async generateTraffic(trafficType, duration) {
    // Generate network traffic to consume bandwidth
    const startTime = Date.now();
    
    while (Date.now() - startTime < duration) {
      if (trafficType === 'tcp' || trafficType === 'mixed') {
        // Generate TCP traffic
        this.generateTcpTraffic();
      }
      
      if (trafficType === 'udp' || trafficType === 'mixed') {
        // Generate UDP traffic
        this.generateUdpTraffic();
      }
      
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  static generateTcpTraffic() {
    // Simulate TCP traffic generation
    const net = require('net');
    const client = new net.Socket();
    
    client.connect(8999, 'localhost', () => {
      // Send data to consume bandwidth
      const data = Buffer.alloc(64 * 1024, 'A'); // 64KB chunk
      client.write(data);
    });
    
    client.on('error', () => {
      // Ignore connection errors
    });
    
    setTimeout(() => client.destroy(), 1000);
  }

  static generateUdpTraffic() {
    // Simulate UDP traffic generation
    const dgram = require('dgram');
    const client = dgram.createSocket('udp4');
    
    const data = Buffer.alloc(32 * 1024, 'B'); // 32KB chunk
    client.send(data, 8999, 'localhost', (error) => {
      client.close();
    });
  }
}

// System resource monitoring
class ResourceMonitor {
  static async getSystemResources() {
    try {
      const { stdout: cpuInfo } = await execAsync("top -bn1 | grep 'Cpu(s)' | head -1 | awk '{print $2}' | sed 's/%us,//'");
      const { stdout: memInfo } = await execAsync("free | grep Mem | awk '{printf \"%.2f\", $3/$2 * 100.0}'");
      const { stdout: diskInfo } = await execAsync("df / | tail -1 | awk '{print $5}' | sed 's/%//'");
      const { stdout: loadAvg } = await execAsync("uptime | awk -F'load average:' '{print $2}'");
      
      return {
        cpu: parseFloat(cpuInfo.trim()),
        memory: parseFloat(memInfo.trim()),
        disk: parseFloat(diskInfo.trim()),
        loadAverage: loadAvg.trim(),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Failed to get system resources:', error);
      return {
        cpu: 0,
        memory: 0,
        disk: 0,
        loadAverage: '0.00, 0.00, 0.00',
        timestamp: new Date().toISOString(),
        error: error.message
      };
    }
  }

  static async monitorResourcesDuring(duration, interval = 5000) {
    const readings = [];
    const startTime = Date.now();
    
    while (Date.now() - startTime < duration) {
      const resources = await this.getSystemResources();
      readings.push(resources);
      
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    
    return readings;
  }
}

// Resource resilience testing
async function testResourceResilience() {
  console.log('Starting Resource Chaos Engineering Tests');
  console.log('===========================================');

  const results = [];

  for (const experiment of resourceExperiments) {
    console.log(`\nExecuting: ${experiment.name}`);
    console.log(`Description: ${experiment.description}`);
    
    // Start resource monitoring
    const monitoringPromise = ResourceMonitor.monitorResourcesDuring(
      experiment.monitoringDuration || 300000
    );
    
    try {
      let execution;
      
      // Handle custom resource chaos actions
      if (experiment.action === 'fd_exhaustion') {
        await ResourceChaosExecutor.executeFileDescriptorExhaustion(experiment.target);
        execution = { status: 'completed', customAction: true };
      } else if (experiment.action === 'bandwidth_exhaustion') {
        await ResourceChaosExecutor.executeBandwidthExhaustion(experiment.target);
        execution = { status: 'completed', customAction: true };
      } else {
        execution = await engine.executeExperiment(experiment.id);
      }
      
      // Wait for monitoring to complete
      const resourceReadings = await monitoringPromise;
      
      results.push({
        experiment: experiment.name,
        status: 'success',
        execution: execution,
        resourceReadings: resourceReadings,
        metrics: this.analyzeResourceMetrics(resourceReadings)
      });
      
      console.log(`✅ Experiment completed successfully`);
      
    } catch (error) {
      console.error(`❌ Experiment failed: ${error.message}`);
      
      // Still get the monitoring results
      const resourceReadings = await monitoringPromise;
      
      results.push({
        experiment: experiment.name,
        status: 'failed',
        error: error.message,
        resourceReadings: resourceReadings,
        metrics: this.analyzeResourceMetrics(resourceReadings)
      });
    }
    
    // Cool down period between experiments
    console.log('Waiting for system recovery...');
    await new Promise(resolve => setTimeout(resolve, 60000)); // 1 minute cooldown
  }

  // Generate resource chaos report
  await generateResourceChaosReport(results);
  
  console.log('\nResource Chaos Engineering Tests Completed');
  console.log(`Results: ${results.filter(r => r.status === 'success').length}/${results.length} successful`);
  
  return results;
}

function analyzeResourceMetrics(readings) {
  if (!readings || readings.length === 0) {
    return { error: 'No resource readings available' };
  }

  const validReadings = readings.filter(r => !r.error);
  if (validReadings.length === 0) {
    return { error: 'No valid resource readings' };
  }

  const cpuReadings = validReadings.map(r => r.cpu);
  const memReadings = validReadings.map(r => r.memory);
  const diskReadings = validReadings.map(r => r.disk);

  return {
    cpu: {
      max: Math.max(...cpuReadings),
      min: Math.min(...cpuReadings),
      average: cpuReadings.reduce((a, b) => a + b, 0) / cpuReadings.length,
      spikes: cpuReadings.filter(c => c > 80).length
    },
    memory: {
      max: Math.max(...memReadings),
      min: Math.min(...memReadings),
      average: memReadings.reduce((a, b) => a + b, 0) / memReadings.length,
      pressure: memReadings.filter(m => m > 90).length
    },
    disk: {
      max: Math.max(...diskReadings),
      min: Math.min(...diskReadings),
      average: diskReadings.reduce((a, b) => a + b, 0) / diskReadings.length,
      highUsage: diskReadings.filter(d => d > 85).length
    },
    duration: validReadings.length,
    dataPoints: validReadings.length
  };
}

// Resource chaos report generation
async function generateResourceChaosReport(results) {
  const fs = require('fs-extra');
  
  await fs.ensureDir('reports');
  
  const report = {
    title: 'Resource Chaos Engineering Report',
    timestamp: new Date().toISOString(),
    summary: {
      totalExperiments: results.length,
      successfulExperiments: results.filter(r => r.status === 'success').length,
      failedExperiments: results.filter(r => r.status === 'failed').length,
      successRate: (results.filter(r => r.status === 'success').length / results.length * 100).toFixed(2)
    },
    experiments: results,
    metrics: engine.getMetrics(),
    systemImpact: analyzeSystemImpact(results),
    recommendations: generateResourceRecommendations(results)
  };
  
  // Save JSON report
  await fs.writeJson('reports/resource-chaos-report.json', report, { spaces: 2 });
  
  // Generate HTML report
  const htmlReport = generateResourceChaosHTML(report);
  await fs.writeFile('reports/resource-chaos-report.html', htmlReport);
  
  console.log('📊 Resource chaos report saved to reports/resource-chaos-report.html');
}

function analyzeSystemImpact(results) {
  const impact = {
    highCpuEvents: 0,
    memoryPressureEvents: 0,
    diskLatencyEvents: 0,
    systemRecoveryTime: 0
  };

  results.forEach(result => {
    if (result.metrics && !result.metrics.error) {
      if (result.metrics.cpu && result.metrics.cpu.spikes > 0) {
        impact.highCpuEvents += result.metrics.cpu.spikes;
      }
      if (result.metrics.memory && result.metrics.memory.pressure > 0) {
        impact.memoryPressureEvents += result.metrics.memory.pressure;
      }
      if (result.metrics.disk && result.metrics.disk.highUsage > 0) {
        impact.diskLatencyEvents += result.metrics.disk.highUsage;
      }
    }
  });

  return impact;
}

function generateResourceRecommendations(results) {
  const recommendations = [];
  
  const failedExperiments = results.filter(r => r.status === 'failed');
  const highResourceUsage = results.filter(r => 
    r.metrics && r.metrics.cpu && r.metrics.cpu.max > 90
  );

  if (failedExperiments.length > 0) {
    recommendations.push({
      type: 'critical',
      message: 'Some resource stress experiments failed',
      action: 'Review system resource limits and implement proper resource management'
    });
  }

  if (highResourceUsage.length > 0) {
    recommendations.push({
      type: 'warning',
      message: 'High resource usage detected during experiments',
      action: 'Consider implementing resource throttling and auto-scaling policies'
    });
  }

  recommendations.push({
    type: 'info',
    message: 'Implement comprehensive resource monitoring',
    action: 'Set up alerts for CPU, memory, and disk usage thresholds'
  });

  recommendations.push({
    type: 'info',
    message: 'Regular resource chaos testing helps identify bottlenecks',
    action: 'Schedule periodic resource stress tests in staging environment'
  });

  return recommendations;
}

function generateResourceChaosHTML(report) {
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
        .resource-chart { margin: 10px 0; padding: 10px; background: #fff; border: 1px solid #ddd; }
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
    
    <h2>System Impact Analysis</h2>
    <div class="resource-chart">
        <p><strong>High CPU Events:</strong> ${report.systemImpact.highCpuEvents}</p>
        <p><strong>Memory Pressure Events:</strong> ${report.systemImpact.memoryPressureEvents}</p>
        <p><strong>Disk Latency Events:</strong> ${report.systemImpact.diskLatencyEvents}</p>
    </div>
    
    <h2>Experiment Results</h2>
    ${report.experiments.map(exp => `
        <div class="experiment ${exp.status}">
            <h3>${exp.experiment}</h3>
            <p>Status: <strong>${exp.status}</strong></p>
            ${exp.error ? `<p>Error: ${exp.error}</p>` : ''}
            ${exp.metrics && !exp.metrics.error ? `
                <div class="resource-chart">
                    <h4>Resource Metrics:</h4>
                    ${exp.metrics.cpu ? `<p>CPU: Max ${exp.metrics.cpu.max.toFixed(1)}%, Avg ${exp.metrics.cpu.average.toFixed(1)}%</p>` : ''}
                    ${exp.metrics.memory ? `<p>Memory: Max ${exp.metrics.memory.max.toFixed(1)}%, Avg ${exp.metrics.memory.average.toFixed(1)}%</p>` : ''}
                    ${exp.metrics.disk ? `<p>Disk: Max ${exp.metrics.disk.max.toFixed(1)}%, Avg ${exp.metrics.disk.average.toFixed(1)}%</p>` : ''}
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

// Run resource chaos tests if this file is executed directly
if (require.main === module) {
  testResourceResilience().catch(console.error);
}

module.exports = { testResourceResilience, ResourceMonitor, ResourceChaosExecutor };