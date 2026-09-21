const cron = require('cron');
const { EventEmitter } = require('events');
const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');

class DeploymentService extends EventEmitter {
  constructor(environmentManager, containerManager, config = {}) {
    super();
    
    this.environmentManager = environmentManager;
    this.containerManager = containerManager;
    this.config = {
      // Deployment settings
      enableScheduledDeployments: config.enableScheduledDeployments ?? true,
      defaultDeploymentStrategy: config.defaultDeploymentStrategy || 'rolling', // rolling, blue-green, canary
      maxConcurrentDeployments: config.maxConcurrentDeployments || 5,
      deploymentTimeout: config.deploymentTimeout || 600000, // 10 minutes
      
      // Environment stages
      stages: config.stages || ['development', 'staging', 'production'],
      requireApproval: config.requireApproval || {
        staging: false,
        production: true
      },
      
      // Deployment targets
      targets: config.targets || {
        development: { type: 'container', replicas: 1 },
        staging: { type: 'container', replicas: 2 },
        production: { type: 'container', replicas: 3 }
      },
      
      // Webhooks and notifications
      webhookUrl: config.webhookUrl || process.env.DEPLOYMENT_WEBHOOK_URL,
      enableNotifications: config.enableNotifications ?? true,
      
      // Health checks
      enableHealthChecks: config.enableHealthChecks ?? true,
      healthCheckPath: config.healthCheckPath || '/health',
      healthCheckTimeout: config.healthCheckTimeout || 30000,
      healthCheckRetries: config.healthCheckRetries || 3,
      
      // Rollback settings
      enableAutoRollback: config.enableAutoRollback ?? true,
      rollbackThreshold: config.rollbackThreshold || 0.1, // 10% failure rate
      rollbackDelay: config.rollbackDelay || 60000, // 1 minute
      
      ...config
    };

    this.deploymentQueue = [];
    this.activeDeployments = new Map(); // deploymentId -> deployment info
    this.deploymentHistory = new Map(); // projectId -> deployments[]
    this.cronJobs = new Map(); // jobId -> cron job
    this.deploymentTemplates = new Map(); // templateId -> template
    
    this.stats = {
      totalDeployments: 0,
      successfulDeployments: 0,
      failedDeployments: 0,
      rollbacks: 0,
      avgDeploymentTime: 0,
      deploymentsByStage: {
        development: 0,
        staging: 0,
        production: 0
      }
    };

    this.initializeDeploymentTemplates();
  }

  // Initialize deployment templates
  initializeDeploymentTemplates() {
    const templates = [
      {
        id: 'node-webapp',
        name: 'Node.js Web Application',
        language: 'javascript',
        buildSteps: [
          'npm install',
          'npm run build',
          'npm run test'
        ],
        healthCheck: '/health',
        environment: {
          NODE_ENV: 'production',
          PORT: '3000'
        }
      },
      {
        id: 'python-api',
        name: 'Python API',
        language: 'python',
        buildSteps: [
          'pip install -r requirements.txt',
          'python -m pytest',
          'python manage.py collectstatic --noinput'
        ],
        healthCheck: '/api/health',
        environment: {
          PYTHONPATH: '/app',
          FLASK_ENV: 'production'
        }
      },
      {
        id: 'react-spa',
        name: 'React Single Page Application',
        language: 'javascript',
        buildSteps: [
          'npm install',
          'npm run build',
          'npm run test:ci'
        ],
        healthCheck: '/',
        staticFiles: true,
        environment: {
          NODE_ENV: 'production'
        }
      }
    ];

    templates.forEach(template => {
      this.deploymentTemplates.set(template.id, template);
    });
  }

  // Schedule deployment
  async scheduleDeployment(userId, deploymentConfig) {
    try {
      const deploymentId = crypto.randomUUID();
      
      const deployment = {
        id: deploymentId,
        userId,
        projectId: deploymentConfig.projectId,
        environmentId: deploymentConfig.environmentId,
        stage: deploymentConfig.stage || 'development',
        strategy: deploymentConfig.strategy || this.config.defaultDeploymentStrategy,
        template: deploymentConfig.template || 'node-webapp',
        
        // Scheduling
        scheduledAt: deploymentConfig.scheduledAt ? new Date(deploymentConfig.scheduledAt) : new Date(),
        cronExpression: deploymentConfig.cronExpression,
        
        // Configuration
        config: {
          buildSteps: deploymentConfig.buildSteps,
          environment: deploymentConfig.environment || {},
          healthCheck: deploymentConfig.healthCheck,
          requireApproval: deploymentConfig.requireApproval ?? this.config.requireApproval[deploymentConfig.stage],
          ...deploymentConfig.config
        },
        
        // State
        status: 'scheduled',
        createdAt: new Date(),
        updatedAt: new Date(),
        approvals: [],
        logs: []
      };

      // Add to queue or schedule with cron
      if (deploymentConfig.cronExpression) {
        await this.scheduleCronDeployment(deployment);
      } else {
        this.deploymentQueue.push(deployment);
        this.processDeploymentQueue();
      }

      // Store deployment
      this.activeDeployments.set(deploymentId, deployment);
      
      if (!this.deploymentHistory.has(deployment.projectId)) {
        this.deploymentHistory.set(deployment.projectId, []);
      }
      this.deploymentHistory.get(deployment.projectId).push(deployment);

      this.emit('deploymentScheduled', deployment);
      
      return deployment;
      
    } catch (error) {
      this.emit('deploymentError', { userId, error });
      throw error;
    }
  }

  // Schedule cron deployment
  async scheduleCronDeployment(deployment) {
    try {
      const cronJob = new cron.CronJob(
        deployment.cronExpression,
        async () => {
          await this.executeCronDeployment(deployment);
        },
        null,
        false,
        'UTC'
      );

      this.cronJobs.set(deployment.id, cronJob);
      cronJob.start();

      deployment.status = 'cron_scheduled';
      this.emit('cronDeploymentScheduled', deployment);
      
    } catch (error) {
      deployment.status = 'cron_error';
      deployment.logs.push(`Cron scheduling failed: ${error.message}`);
      throw error;
    }
  }

  // Execute cron deployment
  async executeCronDeployment(deployment) {
    try {
      // Create new deployment instance for this execution
      const executionId = crypto.randomUUID();
      const execution = {
        ...deployment,
        id: executionId,
        parentId: deployment.id,
        status: 'queued',
        createdAt: new Date(),
        executionNumber: (deployment.executionCount || 0) + 1
      };

      deployment.executionCount = execution.executionNumber;
      deployment.lastExecution = new Date();

      this.deploymentQueue.push(execution);
      this.activeDeployments.set(executionId, execution);
      
      this.processDeploymentQueue();
      
    } catch (error) {
      this.emit('cronExecutionError', { deploymentId: deployment.id, error });
    }
  }

  // Process deployment queue
  async processDeploymentQueue() {
    if (this.deploymentQueue.length === 0) return;
    if (this.activeDeployments.size >= this.config.maxConcurrentDeployments) return;

    const deployment = this.deploymentQueue.shift();
    
    try {
      await this.executeDeployment(deployment);
    } catch (error) {
      console.error(`Deployment ${deployment.id} failed:`, error);
    }

    // Process next deployment
    setTimeout(() => this.processDeploymentQueue(), 1000);
  }

  // Execute deployment
  async executeDeployment(deployment) {
    const startTime = Date.now();
    
    try {
      deployment.status = 'running';
      deployment.startedAt = new Date();
      deployment.updatedAt = new Date();

      this.emit('deploymentStarted', deployment);

      // Check if approval is required
      if (deployment.config.requireApproval && !this.isApproved(deployment)) {
        deployment.status = 'awaiting_approval';
        this.emit('deploymentAwaitingApproval', deployment);
        return;
      }

      // Get deployment template
      const template = this.deploymentTemplates.get(deployment.template);
      if (!template) {
        throw new Error(`Deployment template not found: ${deployment.template}`);
      }

      // Prepare environment
      const environment = await this.environmentManager.getEnvironmentInfo(
        deployment.userId, 
        deployment.environmentId
      );
      
      if (!environment) {
        throw new Error('Environment not found');
      }

      // Execute deployment steps
      await this.runBuildSteps(deployment, template);
      await this.runHealthChecks(deployment, template);
      await this.deployToTarget(deployment, template);
      
      // Verify deployment
      if (this.config.enableHealthChecks) {
        await this.verifyDeployment(deployment);
      }

      // Complete deployment
      deployment.status = 'completed';
      deployment.completedAt = new Date();
      deployment.duration = Date.now() - startTime;

      this.stats.totalDeployments++;
      this.stats.successfulDeployments++;
      this.stats.deploymentsByStage[deployment.stage]++;
      
      // Update average deployment time
      const avgTime = this.stats.avgDeploymentTime;
      const totalDeployments = this.stats.totalDeployments;
      this.stats.avgDeploymentTime = (avgTime * (totalDeployments - 1) + deployment.duration) / totalDeployments;

      this.emit('deploymentCompleted', deployment);
      
      // Send webhook notification
      if (this.config.webhookUrl) {
        await this.sendWebhookNotification(deployment);
      }
      
    } catch (error) {
      deployment.status = 'failed';
      deployment.error = error.message;
      deployment.completedAt = new Date();
      deployment.duration = Date.now() - startTime;
      deployment.logs.push(`Deployment failed: ${error.message}`);

      this.stats.totalDeployments++;
      this.stats.failedDeployments++;

      this.emit('deploymentFailed', deployment);

      // Auto-rollback if enabled
      if (this.config.enableAutoRollback && deployment.stage === 'production') {
        setTimeout(() => {
          this.initiateRollback(deployment.userId, deployment.id, 'Auto-rollback due to deployment failure');
        }, this.config.rollbackDelay);
      }
    }
  }

  // Run build steps
  async runBuildSteps(deployment, template) {
    const buildSteps = deployment.config.buildSteps || template.buildSteps;
    
    if (!buildSteps || buildSteps.length === 0) {
      deployment.logs.push('No build steps defined, skipping build phase');
      return;
    }

    deployment.logs.push('Starting build phase');
    
    for (const [index, step] of buildSteps.entries()) {
      deployment.logs.push(`Build Step ${index + 1}: ${step}`);
      
      try {
        const result = await this.environmentManager.executeInEnvironment(
          deployment.userId,
          deployment.environmentId,
          step,
          { 
            language: 'bash',
            timeout: 300 // 5 minutes per step
          }
        );

        if (result.exitCode !== 0) {
          throw new Error(`Build step failed: ${result.stderr || result.stdout}`);
        }

        deployment.logs.push(`Build Step ${index + 1} completed successfully`);
        
      } catch (error) {
        deployment.logs.push(`Build Step ${index + 1} failed: ${error.message}`);
        throw error;
      }
    }

    deployment.logs.push('Build phase completed successfully');
  }

  // Run health checks
  async runHealthChecks(deployment, template) {
    if (!this.config.enableHealthChecks) {
      return;
    }

    const healthCheckPath = deployment.config.healthCheck || template.healthCheck;
    
    if (!healthCheckPath) {
      deployment.logs.push('No health check defined, skipping');
      return;
    }

    deployment.logs.push(`Running health check: ${healthCheckPath}`);
    
    // This would typically make HTTP requests to the application
    // For now, we'll simulate with a command execution
    const healthCheckCommand = `curl -f -s -o /dev/null -w "%{http_code}" http://localhost:3000${healthCheckPath} || echo "000"`;
    
    try {
      const result = await this.environmentManager.executeInEnvironment(
        deployment.userId,
        deployment.environmentId,
        healthCheckCommand,
        { language: 'bash' }
      );

      const httpCode = result.stdout.trim();
      
      if (httpCode !== '200') {
        throw new Error(`Health check failed with HTTP ${httpCode}`);
      }

      deployment.logs.push('Health check passed');
      
    } catch (error) {
      deployment.logs.push(`Health check failed: ${error.message}`);
      throw error;
    }
  }

  // Deploy to target environment
  async deployToTarget(deployment, template) {
    const target = this.config.targets[deployment.stage];
    
    if (!target) {
      throw new Error(`No deployment target configured for stage: ${deployment.stage}`);
    }

    deployment.logs.push(`Deploying to ${deployment.stage} (${target.type})`);

    switch (target.type) {
      case 'container':
        await this.deployToContainer(deployment, template, target);
        break;
      case 'kubernetes':
        await this.deployToKubernetes(deployment, template, target);
        break;
      case 'serverless':
        await this.deployToServerless(deployment, template, target);
        break;
      default:
        throw new Error(`Unsupported deployment target type: ${target.type}`);
    }

    deployment.logs.push('Deployment to target completed');
  }

  // Deploy to container
  async deployToContainer(deployment, template, target) {
    try {
      // Create deployment snapshot
      const snapshot = await this.environmentManager.createSnapshot(
        deployment.environmentId,
        `Deployment ${deployment.id} to ${deployment.stage}`
      );

      deployment.snapshotId = snapshot.id;
      deployment.logs.push(`Created deployment snapshot: ${snapshot.id}`);

      // Scale containers based on target replicas
      const replicas = target.replicas || 1;
      deployment.logs.push(`Scaling to ${replicas} replicas`);

      // This would typically involve container orchestration
      // For now, we'll simulate the deployment
      await this.simulateContainerDeployment(deployment, replicas);
      
    } catch (error) {
      deployment.logs.push(`Container deployment failed: ${error.message}`);
      throw error;
    }
  }

  // Simulate container deployment
  async simulateContainerDeployment(deployment, replicas) {
    for (let i = 0; i < replicas; i++) {
      deployment.logs.push(`Starting replica ${i + 1}/${replicas}`);
      
      // Simulate deployment delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      deployment.logs.push(`Replica ${i + 1} started successfully`);
    }
  }

  // Deploy to Kubernetes
  async deployToKubernetes(deployment, template, target) {
    // This would implement actual Kubernetes deployment
    deployment.logs.push('Kubernetes deployment not implemented in this demo');
    throw new Error('Kubernetes deployment not implemented');
  }

  // Deploy to serverless
  async deployToServerless(deployment, template, target) {
    // This would implement serverless deployment (AWS Lambda, etc.)
    deployment.logs.push('Serverless deployment not implemented in this demo');
    throw new Error('Serverless deployment not implemented');
  }

  // Verify deployment
  async verifyDeployment(deployment) {
    deployment.logs.push('Verifying deployment health');
    
    let retries = 0;
    const maxRetries = this.config.healthCheckRetries;
    
    while (retries < maxRetries) {
      try {
        await this.runHealthChecks(deployment, this.deploymentTemplates.get(deployment.template));
        deployment.logs.push('Deployment verification successful');
        return;
        
      } catch (error) {
        retries++;
        deployment.logs.push(`Verification attempt ${retries} failed: ${error.message}`);
        
        if (retries < maxRetries) {
          deployment.logs.push(`Retrying in 10 seconds... (${retries}/${maxRetries})`);
          await new Promise(resolve => setTimeout(resolve, 10000));
        }
      }
    }
    
    throw new Error('Deployment verification failed after maximum retries');
  }

  // Approve deployment
  async approveDeployment(userId, deploymentId, approvalNote = '') {
    try {
      const deployment = this.activeDeployments.get(deploymentId);
      if (!deployment) {
        throw new Error('Deployment not found');
      }

      if (deployment.status !== 'awaiting_approval') {
        throw new Error('Deployment is not awaiting approval');
      }

      // Add approval
      deployment.approvals.push({
        userId,
        approvedAt: new Date(),
        note: approvalNote
      });

      deployment.status = 'approved';
      deployment.updatedAt = new Date();
      deployment.logs.push(`Approved by user ${userId}: ${approvalNote}`);

      // Resume deployment
      this.deploymentQueue.unshift(deployment); // Add to front of queue
      this.processDeploymentQueue();

      this.emit('deploymentApproved', deployment);
      
      return deployment;
      
    } catch (error) {
      this.emit('deploymentError', { userId, deploymentId, error });
      throw error;
    }
  }

  // Reject deployment
  async rejectDeployment(userId, deploymentId, rejectionReason = '') {
    try {
      const deployment = this.activeDeployments.get(deploymentId);
      if (!deployment) {
        throw new Error('Deployment not found');
      }

      deployment.status = 'rejected';
      deployment.updatedAt = new Date();
      deployment.logs.push(`Rejected by user ${userId}: ${rejectionReason}`);

      this.emit('deploymentRejected', deployment);
      
      return deployment;
      
    } catch (error) {
      this.emit('deploymentError', { userId, deploymentId, error });
      throw error;
    }
  }

  // Check if deployment is approved
  isApproved(deployment) {
    return deployment.approvals && deployment.approvals.length > 0;
  }

  // Initiate rollback
  async initiateRollback(userId, deploymentId, reason = '') {
    try {
      const deployment = this.activeDeployments.get(deploymentId) || 
                        this.findDeploymentInHistory(deploymentId);
      
      if (!deployment) {
        throw new Error('Deployment not found');
      }

      const rollbackId = crypto.randomUUID();
      
      const rollback = {
        id: rollbackId,
        originalDeploymentId: deploymentId,
        userId,
        projectId: deployment.projectId,
        environmentId: deployment.environmentId,
        stage: deployment.stage,
        reason,
        status: 'running',
        startedAt: new Date(),
        logs: [`Rollback initiated: ${reason}`]
      };

      // Find previous successful deployment
      const previousDeployment = this.findPreviousSuccessfulDeployment(
        deployment.projectId, 
        deployment.stage
      );
      
      if (!previousDeployment) {
        throw new Error('No previous successful deployment found for rollback');
      }

      rollback.targetSnapshotId = previousDeployment.snapshotId;
      rollback.logs.push(`Rolling back to snapshot: ${previousDeployment.snapshotId}`);

      // Execute rollback
      await this.executeRollback(rollback);
      
      rollback.status = 'completed';
      rollback.completedAt = new Date();
      this.stats.rollbacks++;

      this.emit('rollbackCompleted', rollback);
      
      return rollback;
      
    } catch (error) {
      this.emit('rollbackError', { userId, deploymentId, error });
      throw error;
    }
  }

  // Execute rollback
  async executeRollback(rollback) {
    try {
      // Restore environment from snapshot
      if (rollback.targetSnapshotId) {
        await this.environmentManager.restoreFromSnapshot(
          rollback.userId,
          rollback.environmentId,
          rollback.targetSnapshotId
        );
        
        rollback.logs.push('Environment restored from snapshot');
      }

      // Redeploy previous version
      rollback.logs.push('Redeploying previous version');
      await this.simulateContainerDeployment(rollback, 1);
      
      rollback.logs.push('Rollback deployment completed');
      
    } catch (error) {
      rollback.status = 'failed';
      rollback.logs.push(`Rollback failed: ${error.message}`);
      throw error;
    }
  }

  // Find deployment in history
  findDeploymentInHistory(deploymentId) {
    for (const deployments of this.deploymentHistory.values()) {
      const deployment = deployments.find(d => d.id === deploymentId);
      if (deployment) return deployment;
    }
    return null;
  }

  // Find previous successful deployment
  findPreviousSuccessfulDeployment(projectId, stage) {
    const deployments = this.deploymentHistory.get(projectId) || [];
    const stageDeployments = deployments
      .filter(d => d.stage === stage && d.status === 'completed')
      .sort((a, b) => new Date(b.completedAt) - new Date(a.completedAt));
    
    return stageDeployments[1]; // Second most recent (skip current)
  }

  // Send webhook notification
  async sendWebhookNotification(deployment) {
    try {
      const payload = {
        event: 'deployment_completed',
        deployment: {
          id: deployment.id,
          projectId: deployment.projectId,
          stage: deployment.stage,
          status: deployment.status,
          startedAt: deployment.startedAt,
          completedAt: deployment.completedAt,
          duration: deployment.duration
        }
      };

      // This would make actual HTTP request
      console.log(`Webhook notification sent for deployment ${deployment.id}`);
      
    } catch (error) {
      console.error('Webhook notification failed:', error);
    }
  }

  // Cancel deployment
  async cancelDeployment(userId, deploymentId) {
    try {
      const deployment = this.activeDeployments.get(deploymentId);
      if (!deployment) {
        throw new Error('Deployment not found');
      }

      if (deployment.userId !== userId) {
        throw new Error('Unauthorized to cancel this deployment');
      }

      if (!['scheduled', 'queued', 'awaiting_approval'].includes(deployment.status)) {
        throw new Error('Cannot cancel deployment in current status');
      }

      deployment.status = 'cancelled';
      deployment.updatedAt = new Date();
      deployment.logs.push(`Deployment cancelled by user ${userId}`);

      // Remove from queue
      const queueIndex = this.deploymentQueue.findIndex(d => d.id === deploymentId);
      if (queueIndex !== -1) {
        this.deploymentQueue.splice(queueIndex, 1);
      }

      // Stop cron job if exists
      const cronJob = this.cronJobs.get(deploymentId);
      if (cronJob) {
        cronJob.stop();
        this.cronJobs.delete(deploymentId);
      }

      this.emit('deploymentCancelled', deployment);
      
      return deployment;
      
    } catch (error) {
      this.emit('deploymentError', { userId, deploymentId, error });
      throw error;
    }
  }

  // Get deployment status
  getDeploymentStatus(deploymentId) {
    const deployment = this.activeDeployments.get(deploymentId) || 
                      this.findDeploymentInHistory(deploymentId);
    
    if (!deployment) return null;

    return {
      id: deployment.id,
      projectId: deployment.projectId,
      stage: deployment.stage,
      status: deployment.status,
      strategy: deployment.strategy,
      createdAt: deployment.createdAt,
      startedAt: deployment.startedAt,
      completedAt: deployment.completedAt,
      duration: deployment.duration,
      approvals: deployment.approvals?.length || 0,
      logs: deployment.logs.slice(-10), // Last 10 log entries
      error: deployment.error
    };
  }

  // Get user deployments
  getUserDeployments(userId) {
    const deployments = [];
    
    // Active deployments
    for (const deployment of this.activeDeployments.values()) {
      if (deployment.userId === userId) {
        deployments.push(this.getDeploymentStatus(deployment.id));
      }
    }
    
    // Historical deployments
    for (const projectDeployments of this.deploymentHistory.values()) {
      for (const deployment of projectDeployments) {
        if (deployment.userId === userId && !this.activeDeployments.has(deployment.id)) {
          deployments.push(this.getDeploymentStatus(deployment.id));
        }
      }
    }
    
    return deployments.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  }

  // Get project deployments
  getProjectDeployments(projectId) {
    const projectDeployments = this.deploymentHistory.get(projectId) || [];
    
    return projectDeployments
      .map(d => this.getDeploymentStatus(d.id))
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  }

  // Get service statistics
  getServiceStats() {
    return {
      ...this.stats,
      successRate: this.stats.totalDeployments > 0 ? 
        ((this.stats.successfulDeployments / this.stats.totalDeployments) * 100).toFixed(2) + '%' :
        '0%',
      queuedDeployments: this.deploymentQueue.length,
      activeDeployments: this.activeDeployments.size,
      scheduledJobs: this.cronJobs.size,
      avgDeploymentTimeMinutes: Math.round(this.stats.avgDeploymentTime / 1000 / 60)
    };
  }

  // Health check
  async healthCheck() {
    try {
      return {
        healthy: true,
        stats: this.getServiceStats(),
        queueProcessing: this.deploymentQueue.length < this.config.maxConcurrentDeployments,
        environmentManagerHealthy: await this.environmentManager.healthCheck().then(h => h.healthy)
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message
      };
    }
  }

  // Cleanup service
  async cleanup() {
    console.log('Shutting down Deployment Service...');
    
    // Stop all cron jobs
    for (const [jobId, cronJob] of this.cronJobs) {
      try {
        cronJob.stop();
        console.log(`Stopped cron job: ${jobId}`);
      } catch (error) {
        console.warn(`Failed to stop cron job ${jobId}:`, error.message);
      }
    }
    this.cronJobs.clear();

    // Cancel queued deployments
    for (const deployment of this.deploymentQueue) {
      deployment.status = 'cancelled';
      deployment.logs.push('Deployment cancelled due to service shutdown');
    }
    this.deploymentQueue = [];

    this.emit('cleanup');
  }
}

module.exports = DeploymentService;