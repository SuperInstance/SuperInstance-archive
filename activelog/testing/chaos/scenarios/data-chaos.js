const ChaosEngine = require('../utils/chaos-engine');
const { MongoClient } = require('mongodb');
const fs = require('fs-extra');
const path = require('path');

const engine = new ChaosEngine();

// Data chaos experiments
const dataExperiments = [
  {
    name: 'Database Connection Interruption',
    description: 'Simulate abrupt database connection loss during transactions',
    action: 'data_corruption',
    target: {
      type: 'database',
      database: 'activelog',
      scenario: 'connection_loss',
      duration: 180000, // 3 minutes
      transactionTypes: ['create', 'update', 'delete']
    },
    monitoringDuration: 240000,
    maxRecoveryTime: 120000,
    expectedOutcome: {
      transactionRollback: true,
      dataConsistency: true,
      automaticRetry: true,
      noDataLoss: true
    }
  },

  {
    name: 'Partial Data Corruption',
    description: 'Simulate partial data corruption and test recovery mechanisms',
    action: 'data_corruption',
    target: {
      type: 'database',
      database: 'activelog',
      scenario: 'partial_corruption',
      collections: ['users', 'logs', 'projects'],
      corruptionRate: 0.05, // 5% of documents
      corruptionType: 'field_modification'
    },
    monitoringDuration: 300000,
    maxRecoveryTime: 180000,
    expectedOutcome: {
      corruptionDetection: true,
      dataValidationFailure: true,
      backupRestore: true,
      integrityChecks: true
    }
  },

  {
    name: 'Disk Space Exhaustion During Write',
    description: 'Test behavior when disk space runs out during write operations',
    action: 'disk_exhaustion',
    target: {
      type: 'storage',
      path: '/tmp/chaos-disk-test',
      initialSize: '100MB',
      fillRate: '10MB/s',
      duration: 240000 // 4 minutes
    },
    monitoringDuration: 300000,
    maxRecoveryTime: 120000,
    expectedOutcome: {
      writeFailures: true,
      errorHandling: true,
      spaceCleaning: true,
      serviceRecovery: true
    }
  },

  {
    name: 'Concurrent Write Conflicts',
    description: 'Simulate high concurrent writes to test race conditions',
    action: 'concurrency_chaos',
    target: {
      type: 'database',
      database: 'activelog',
      scenario: 'write_conflicts',
      concurrentWrites: 50,
      targetCollection: 'logs',
      duration: 300000 // 5 minutes
    },
    monitoringDuration: 360000,
    maxRecoveryTime: 60000,
    expectedOutcome: {
      lockContention: true,
      deadlockDetection: true,
      optimisticLocking: true,
      dataIntegrity: true
    }
  },

  {
    name: 'Backup System Failure',
    description: 'Test system behavior when backup mechanisms fail',
    action: 'backup_failure',
    target: {
      type: 'backup',
      backupType: 'incremental',
      failurePoint: 'during_backup',
      duration: 180000 // 3 minutes
    },
    monitoringDuration: 240000,
    maxRecoveryTime: 120000,
    expectedOutcome: {
      backupFailureDetection: true,
      alternativeBackupUse: true,
      dataProtectionMaintained: true,
      alertGeneration: true
    }
  },

  {
    name: 'Data Migration Interruption',
    description: 'Interrupt data migration process to test rollback mechanisms',
    action: 'migration_chaos',
    target: {
      type: 'migration',
      migrationScript: 'user_schema_update',
      interruptionPoint: '50%', // Interrupt at 50% completion
      rollbackRequired: true
    },
    monitoringDuration: 360000,
    maxRecoveryTime: 300000, // Longer recovery for migration rollback
    expectedOutcome: {
      migrationRollback: true,
      schemaConsistency: true,
      noDataLoss: true,
      systemStability: true
    }
  }
];

// Register all experiments
dataExperiments.forEach(experiment => {
  engine.registerExperiment(experiment);
});

// Data chaos executor
class DataChaosExecutor {
  static async executeDataCorruption(target) {
    console.log('Starting data corruption experiment');
    
    const scenario = target.scenario;
    
    switch (scenario) {
      case 'connection_loss':
        await this.simulateConnectionLoss(target);
        break;
      case 'partial_corruption':
        await this.simulatePartialCorruption(target);
        break;
      default:
        throw new Error(`Unknown data corruption scenario: ${scenario}`);
    }
  }

  static async simulateConnectionLoss(target) {
    const duration = target.duration || 180000;
    const transactionTypes = target.transactionTypes || ['create', 'update'];
    
    console.log('Simulating database connection loss during transactions');
    
    // Start background transactions
    const transactionPromises = [];
    const startTime = Date.now();
    
    while (Date.now() - startTime < duration / 2) {
      for (const txType of transactionTypes) {
        const promise = this.executeBackgroundTransaction(txType);
        transactionPromises.push(promise);
      }
      
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    // Interrupt connections abruptly
    console.log('Interrupting database connections');
    await this.interruptDatabaseConnections(duration / 2);
    
    // Wait for all transactions to complete or fail
    const results = await Promise.allSettled(transactionPromises);
    
    console.log(`Transaction results: ${results.filter(r => r.status === 'fulfilled').length} successful, ${results.filter(r => r.status === 'rejected').length} failed`);
  }

  static async simulatePartialCorruption(target) {
    const collections = target.collections || ['users'];
    const corruptionRate = target.corruptionRate || 0.05;
    const corruptionType = target.corruptionType || 'field_modification';
    
    console.log(`Simulating partial data corruption in collections: ${collections.join(', ')}`);
    
    for (const collection of collections) {
      await this.corruptCollectionData(collection, corruptionRate, corruptionType);
    }
  }

  static async corruptCollectionData(collectionName, corruptionRate, corruptionType) {
    // In a real implementation, this would carefully corrupt data in a test environment
    console.log(`Corrupting ${(corruptionRate * 100)}% of documents in ${collectionName} collection`);
    
    // Simulate corruption without actually modifying production data
    const simulatedDocuments = 1000;
    const documentsToCorrupt = Math.floor(simulatedDocuments * corruptionRate);
    
    console.log(`Would corrupt ${documentsToCorrupt} documents using ${corruptionType} method`);
    
    // In a real test environment, you might:
    // 1. Connect to test database
    // 2. Randomly select documents
    // 3. Apply controlled corruption
    // 4. Monitor for detection mechanisms
  }

  static async executeBackgroundTransaction(transactionType) {
    // Simulate background transaction execution
    return new Promise(async (resolve, reject) => {
      try {
        // Simulate transaction work
        await new Promise(r => setTimeout(r, Math.random() * 5000));
        
        // Random chance of transaction failure during chaos
        if (Math.random() < 0.3) {
          reject(new Error(`Transaction ${transactionType} failed due to connection issue`));
        } else {
          resolve(`Transaction ${transactionType} completed successfully`);
        }
      } catch (error) {
        reject(error);
      }
    });
  }

  static async interruptDatabaseConnections(duration) {
    // Block database ports to simulate connection loss
    const { exec } = require('child_process');
    const { promisify } = require('util');
    const execAsync = promisify(exec);
    
    const dbPorts = [27017, 5432, 3306]; // MongoDB, PostgreSQL, MySQL
    
    try {
      for (const port of dbPorts) {
        await execAsync(`iptables -A INPUT -p tcp --dport ${port} -j DROP`);
        await execAsync(`iptables -A OUTPUT -p tcp --dport ${port} -j DROP`);
      }
      
      console.log('Blocked database connections');
      await new Promise(resolve => setTimeout(resolve, duration));
      
    } finally {
      // Restore connections
      for (const port of dbPorts) {
        try {
          await execAsync(`iptables -D INPUT -p tcp --dport ${port} -j DROP`);
          await execAsync(`iptables -D OUTPUT -p tcp --dport ${port} -j DROP`);
        } catch (error) {
          // Ignore cleanup errors
        }
      }
      console.log('Restored database connections');
    }
  }

  static async executeDiskExhaustion(target) {
    console.log('Starting disk space exhaustion experiment');
    
    const testPath = target.path || '/tmp/chaos-disk-test';
    const initialSize = target.initialSize || '100MB';
    const fillRate = target.fillRate || '10MB/s';
    const duration = target.duration || 240000;
    
    await fs.ensureDir(testPath);
    
    try {
      // Fill disk space gradually
      await this.fillDiskSpace(testPath, initialSize, fillRate, duration);
    } finally {
      // Cleanup
      await fs.remove(testPath);
      console.log('Cleaned up disk space test files');
    }
  }

  static async fillDiskSpace(testPath, initialSize, fillRate, duration) {
    const sizeInMB = parseInt(initialSize);
    const rateInMB = parseInt(fillRate);
    const intervalMs = 1000; // 1 second intervals
    const mbPerInterval = rateInMB * (intervalMs / 1000);
    
    let currentSize = 0;
    const startTime = Date.now();
    
    while (Date.now() - startTime < duration && currentSize < sizeInMB) {
      // Create a file chunk
      const chunkSize = Math.min(mbPerInterval, sizeInMB - currentSize);
      const fileName = path.join(testPath, `chaos-fill-${Date.now()}.dat`);
      
      // Create file filled with zeros
      const buffer = Buffer.alloc(chunkSize * 1024 * 1024, 0);
      await fs.writeFile(fileName, buffer);
      
      currentSize += chunkSize;
      console.log(`Filled ${currentSize}MB of ${sizeInMB}MB`);
      
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }
    
    console.log(`Disk filling completed: ${currentSize}MB`);
  }

  static async executeConcurrencyChaos(target) {
    console.log('Starting concurrency chaos experiment');
    
    const concurrentWrites = target.concurrentWrites || 50;
    const duration = target.duration || 300000;
    const targetCollection = target.targetCollection || 'logs';
    
    await this.simulateConcurrentWrites(targetCollection, concurrentWrites, duration);
  }

  static async simulateConcurrentWrites(collection, concurrency, duration) {
    const startTime = Date.now();
    const writePromises = [];
    
    console.log(`Starting ${concurrency} concurrent writers for ${duration}ms`);
    
    for (let i = 0; i < concurrency; i++) {
      const promise = this.continuousWriter(collection, i, startTime, duration);
      writePromises.push(promise);
    }
    
    const results = await Promise.allSettled(writePromises);
    const successful = results.filter(r => r.status === 'fulfilled').length;
    const failed = results.filter(r => r.status === 'rejected').length;
    
    console.log(`Concurrent write results: ${successful} successful, ${failed} failed`);
  }

  static async continuousWriter(collection, writerId, startTime, duration) {
    let writeCount = 0;
    let errorCount = 0;
    
    while (Date.now() - startTime < duration) {
      try {
        // Simulate write operation
        await this.simulateWrite(collection, writerId, writeCount);
        writeCount++;
        
        // Random delay between writes
        await new Promise(resolve => setTimeout(resolve, Math.random() * 100));
        
      } catch (error) {
        errorCount++;
        console.warn(`Writer ${writerId} error:`, error.message);
        
        // Brief pause after error
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    
    return { writerId, writeCount, errorCount };
  }

  static async simulateWrite(collection, writerId, writeCount) {
    // Simulate database write operation
    // In real implementation, this would perform actual database writes
    
    const writeTime = Math.random() * 50; // 0-50ms
    await new Promise(resolve => setTimeout(resolve, writeTime));
    
    // Simulate occasional write conflicts
    if (Math.random() < 0.1) { // 10% chance of conflict
      throw new Error(`Write conflict in ${collection} by writer ${writerId}`);
    }
    
    return { collection, writerId, writeCount, timestamp: Date.now() };
  }

  static async executeBackupFailure(target) {
    console.log('Starting backup failure experiment');
    
    const backupType = target.backupType || 'incremental';
    const failurePoint = target.failurePoint || 'during_backup';
    const duration = target.duration || 180000;
    
    await this.simulateBackupFailure(backupType, failurePoint, duration);
  }

  static async simulateBackupFailure(backupType, failurePoint, duration) {
    console.log(`Simulating ${backupType} backup failure at ${failurePoint}`);
    
    if (failurePoint === 'during_backup') {
      // Start backup process
      const backupPromise = this.simulateBackupProcess(backupType, duration);
      
      // Interrupt backup midway
      setTimeout(() => {
        console.log('Interrupting backup process');
        // In real implementation, would kill backup process
      }, duration / 2);
      
      try {
        await backupPromise;
      } catch (error) {
        console.log('Backup failed as expected:', error.message);
      }
    }
  }

  static async simulateBackupProcess(backupType, duration) {
    console.log(`Starting ${backupType} backup process`);
    
    const totalSteps = 10;
    const stepDuration = duration / totalSteps;
    
    for (let step = 1; step <= totalSteps; step++) {
      await new Promise(resolve => setTimeout(resolve, stepDuration));
      console.log(`Backup progress: ${step}/${totalSteps} (${(step/totalSteps*100).toFixed(0)}%)`);
      
      // Simulate failure at random point
      if (Math.random() < 0.2) { // 20% chance of failure per step
        throw new Error(`Backup failed at step ${step}`);
      }
    }
    
    console.log('Backup completed successfully');
  }

  static async executeMigrationChaos(target) {
    console.log('Starting migration chaos experiment');
    
    const migrationScript = target.migrationScript || 'test_migration';
    const interruptionPoint = target.interruptionPoint || '50%';
    const rollbackRequired = target.rollbackRequired || true;
    
    await this.simulateMigrationInterruption(migrationScript, interruptionPoint, rollbackRequired);
  }

  static async simulateMigrationInterruption(migrationScript, interruptionPoint, rollbackRequired) {
    console.log(`Starting migration: ${migrationScript}`);
    
    const totalSteps = 20;
    const interruptAt = parseInt(interruptionPoint) / 100 * totalSteps;
    const stepDuration = 5000; // 5 seconds per step
    
    try {
      for (let step = 1; step <= totalSteps; step++) {
        await new Promise(resolve => setTimeout(resolve, stepDuration));
        console.log(`Migration progress: ${step}/${totalSteps} (${(step/totalSteps*100).toFixed(0)}%)`);
        
        // Interrupt at specified point
        if (step >= interruptAt) {
          throw new Error(`Migration interrupted at ${(step/totalSteps*100).toFixed(0)}%`);
        }
      }
      
      console.log('Migration completed successfully');
      
    } catch (error) {
      console.log('Migration interrupted:', error.message);
      
      if (rollbackRequired) {
        await this.simulateMigrationRollback(migrationScript, Math.floor(interruptAt));
      }
    }
  }

  static async simulateMigrationRollback(migrationScript, completedSteps) {
    console.log(`Starting rollback for migration: ${migrationScript}`);
    console.log(`Rolling back ${completedSteps} completed steps`);
    
    for (let step = completedSteps; step >= 1; step--) {
      await new Promise(resolve => setTimeout(resolve, 2000)); // 2 seconds per rollback step
      console.log(`Rollback progress: ${completedSteps - step + 1}/${completedSteps} (${((completedSteps - step + 1)/completedSteps*100).toFixed(0)}%)`);
    }
    
    console.log('Migration rollback completed successfully');
  }
}

// Data integrity monitoring
class DataIntegrityMonitor {
  static async checkDataIntegrity() {
    const checks = [
      { name: 'Database Connections', check: () => this.checkDatabaseConnections() },
      { name: 'Data Consistency', check: () => this.checkDataConsistency() },
      { name: 'Backup Systems', check: () => this.checkBackupSystems() },
      { name: 'Disk Space', check: () => this.checkDiskSpace() }
    ];

    const results = [];
    
    for (const check of checks) {
      try {
        const startTime = Date.now();
        const result = await check.check();
        const checkTime = Date.now() - startTime;
        
        results.push({
          check: check.name,
          status: 'passed',
          result: result,
          checkTime: checkTime,
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        results.push({
          check: check.name,
          status: 'failed',
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    }
    
    return results;
  }

  static async checkDatabaseConnections() {
    const client = new MongoClient(process.env.MONGODB_URL || 'mongodb://localhost:27017');
    try {
      await client.connect();
      await client.db().admin().ping();
      await client.close();
      return { status: 'healthy', connections: 'available' };
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }

  static async checkDataConsistency() {
    // Simulate data consistency checks
    return {
      status: 'consistent',
      checks: {
        referentialIntegrity: 'passed',
        constraints: 'passed',
        duplicates: 'none_found'
      }
    };
  }

  static async checkBackupSystems() {
    // Simulate backup system checks
    const lastBackup = new Date(Date.now() - 3600000); // 1 hour ago
    return {
      status: 'operational',
      lastBackup: lastBackup.toISOString(),
      backupAge: '1 hour',
      backupSize: '450MB'
    };
  }

  static async checkDiskSpace() {
    const { exec } = require('child_process');
    const { promisify } = require('util');
    const execAsync = promisify(exec);
    
    try {
      const { stdout } = await execAsync("df -h / | tail -1 | awk '{print $4, $5}'");
      const [available, used] = stdout.trim().split(' ');
      
      return {
        status: 'adequate',
        available: available,
        used: used
      };
    } catch (error) {
      return {
        status: 'unknown',
        error: error.message
      };
    }
  }
}

// Data resilience testing
async function testDataResilience() {
  console.log('Starting Data Chaos Engineering Tests');
  console.log('======================================');

  const results = [];

  for (const experiment of dataExperiments) {
    console.log(`\nExecuting: ${experiment.name}`);
    console.log(`Description: ${experiment.description}`);
    
    // Check data integrity before experiment
    const preIntegrityCheck = await DataIntegrityMonitor.checkDataIntegrity();
    
    try {
      let execution;
      
      // Handle custom data chaos actions
      switch (experiment.action) {
        case 'data_corruption':
          await DataChaosExecutor.executeDataCorruption(experiment.target);
          execution = { status: 'completed', customAction: true };
          break;
        case 'disk_exhaustion':
          await DataChaosExecutor.executeDiskExhaustion(experiment.target);
          execution = { status: 'completed', customAction: true };
          break;
        case 'concurrency_chaos':
          await DataChaosExecutor.executeConcurrencyChaos(experiment.target);
          execution = { status: 'completed', customAction: true };
          break;
        case 'backup_failure':
          await DataChaosExecutor.executeBackupFailure(experiment.target);
          execution = { status: 'completed', customAction: true };
          break;
        case 'migration_chaos':
          await DataChaosExecutor.executeMigrationChaos(experiment.target);
          execution = { status: 'completed', customAction: true };
          break;
        default:
          execution = await engine.executeExperiment(experiment.id);
      }
      
      // Check data integrity after experiment
      const postIntegrityCheck = await DataIntegrityMonitor.checkDataIntegrity();
      
      results.push({
        experiment: experiment.name,
        status: 'success',
        execution: execution,
        preIntegrityCheck: preIntegrityCheck,
        postIntegrityCheck: postIntegrityCheck,
        integrityComparison: this.compareIntegrityChecks(preIntegrityCheck, postIntegrityCheck)
      });
      
      console.log(`✅ Experiment completed successfully`);
      
    } catch (error) {
      console.error(`❌ Experiment failed: ${error.message}`);
      
      const postIntegrityCheck = await DataIntegrityMonitor.checkDataIntegrity();
      
      results.push({
        experiment: experiment.name,
        status: 'failed',
        error: error.message,
        preIntegrityCheck: preIntegrityCheck,
        postIntegrityCheck: postIntegrityCheck,
        integrityComparison: this.compareIntegrityChecks(preIntegrityCheck, postIntegrityCheck)
      });
    }
    
    // Recovery period between experiments
    console.log('Waiting for data systems recovery...');
    await new Promise(resolve => setTimeout(resolve, 120000)); // 2 minute recovery
  }

  // Generate data chaos report
  await generateDataChaosReport(results);
  
  console.log('\nData Chaos Engineering Tests Completed');
  console.log(`Results: ${results.filter(r => r.status === 'success').length}/${results.length} successful`);
  
  return results;
}

function compareIntegrityChecks(preChecks, postChecks) {
  const comparison = {
    maintained: [],
    degraded: [],
    improved: [],
    unchanged: []
  };

  const preMap = new Map(preChecks.map(c => [c.check, c]));
  
  for (const postCheck of postChecks) {
    const preCheck = preMap.get(postCheck.check);
    
    if (!preCheck) {
      comparison.unchanged.push(postCheck.check);
      continue;
    }

    if (preCheck.status === postCheck.status) {
      comparison.unchanged.push(postCheck.check);
    } else if (preCheck.status === 'passed' && postCheck.status === 'failed') {
      comparison.degraded.push(postCheck.check);
    } else if (preCheck.status === 'failed' && postCheck.status === 'passed') {
      comparison.improved.push(postCheck.check);
    } else {
      comparison.maintained.push(postCheck.check);
    }
  }

  return comparison;
}

// Generate data chaos report
async function generateDataChaosReport(results) {
  await fs.ensureDir('reports');
  
  const report = {
    title: 'Data Chaos Engineering Report',
    timestamp: new Date().toISOString(),
    summary: {
      totalExperiments: results.length,
      successfulExperiments: results.filter(r => r.status === 'success').length,
      failedExperiments: results.filter(r => r.status === 'failed').length,
      successRate: (results.filter(r => r.status === 'success').length / results.length * 100).toFixed(2)
    },
    experiments: results,
    metrics: engine.getMetrics(),
    dataIntegrityAnalysis: analyzeDataIntegrity(results),
    recommendations: generateDataRecommendations(results)
  };
  
  // Save JSON report
  await fs.writeJson('reports/data-chaos-report.json', report, { spaces: 2 });
  
  // Generate HTML report
  const htmlReport = generateDataChaosHTML(report);
  await fs.writeFile('reports/data-chaos-report.html', htmlReport);
  
  console.log('📊 Data chaos report saved to reports/data-chaos-report.html');
}

function analyzeDataIntegrity(results) {
  const analysis = {
    integrityMaintained: 0,
    integrityDegraded: 0,
    integrityImproved: 0,
    totalChecks: 0,
    criticalFailures: 0
  };

  results.forEach(result => {
    if (result.integrityComparison) {
      analysis.integrityMaintained += result.integrityComparison.maintained.length;
      analysis.integrityDegraded += result.integrityComparison.degraded.length;
      analysis.integrityImproved += result.integrityComparison.improved.length;
      analysis.totalChecks += result.preIntegrityCheck.length;
      
      if (result.integrityComparison.degraded.length > 0) {
        analysis.criticalFailures++;
      }
    }
  });

  return analysis;
}

function generateDataRecommendations(results) {
  const recommendations = [];
  
  const failedExperiments = results.filter(r => r.status === 'failed').length;
  const integrityIssues = results.filter(r => 
    r.integrityComparison && r.integrityComparison.degraded.length > 0
  ).length;
  
  if (failedExperiments > 0) {
    recommendations.push({
      type: 'critical',
      message: 'Some data chaos experiments failed unexpectedly',
      action: 'Review data handling, transaction management, and error recovery mechanisms'
    });
  }

  if (integrityIssues > 0) {
    recommendations.push({
      type: 'critical',
      message: 'Data integrity was compromised during experiments',
      action: 'Implement stronger consistency checks, validation, and recovery procedures'
    });
  }

  recommendations.push({
    type: 'warning',
    message: 'Ensure robust backup and recovery procedures',
    action: 'Test backup restoration and implement automated backup validation'
  });

  recommendations.push({
    type: 'info',
    message: 'Regular data chaos testing prevents data loss incidents',
    action: 'Schedule periodic data resilience testing in staging environments'
  });

  recommendations.push({
    type: 'info',
    message: 'Implement comprehensive data monitoring',
    action: 'Set up real-time data integrity monitoring and alerting systems'
  });

  return recommendations;
}

function generateDataChaosHTML(report) {
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
        .integrity-status { margin: 10px 0; padding: 10px; background: #fff; border: 1px solid #ddd; }
        .maintained { color: #28a745; }
        .degraded { color: #dc3545; }
        .improved { color: #007bff; }
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
    
    <h2>Data Integrity Analysis</h2>
    <div class="integrity-status">
        <p><strong>Integrity Maintained:</strong> ${report.dataIntegrityAnalysis.integrityMaintained}</p>
        <p><strong>Integrity Degraded:</strong> ${report.dataIntegrityAnalysis.integrityDegraded}</p>
        <p><strong>Integrity Improved:</strong> ${report.dataIntegrityAnalysis.integrityImproved}</p>
        <p><strong>Critical Failures:</strong> ${report.dataIntegrityAnalysis.criticalFailures}</p>
    </div>
    
    <h2>Experiment Results</h2>
    ${report.experiments.map(exp => `
        <div class="experiment ${exp.status}">
            <h3>${exp.experiment}</h3>
            <p>Status: <strong>${exp.status}</strong></p>
            ${exp.error ? `<p>Error: ${exp.error}</p>` : ''}
            ${exp.integrityComparison ? `
                <div class="integrity-status">
                    <h4>Data Integrity Impact:</h4>
                    <p class="maintained">Maintained: ${exp.integrityComparison.maintained.join(', ') || 'None'}</p>
                    <p class="degraded">Degraded: ${exp.integrityComparison.degraded.join(', ') || 'None'}</p>
                    <p class="improved">Improved: ${exp.integrityComparison.improved.join(', ') || 'None'}</p>
                    <p>Unchanged: ${exp.integrityComparison.unchanged.join(', ') || 'None'}</p>
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

// Run data chaos tests if this file is executed directly
if (require.main === module) {
  testDataResilience().catch(console.error);
}

module.exports = { testDataResilience, DataIntegrityMonitor, DataChaosExecutor };