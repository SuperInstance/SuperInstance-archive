const Docker = require('dockerode');
const { EventEmitter } = require('events');
const fs = require('fs').promises;
const path = require('path');
const tar = require('tar');
const crypto = require('crypto');

class ContainerManager extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      developmentMode: config.developmentMode || process.env.NODE_ENV === 'development' || false,
      dockerHost: config.dockerHost || process.env.DOCKER_HOST || 'unix:///var/run/docker.sock',
      networkName: config.networkName || process.env.DOCKER_NETWORK || 'dev-sandbox-network',
      registryUrl: config.registryUrl || process.env.CONTAINER_REGISTRY_URL,
      registryAuth: config.registryAuth || {
        username: process.env.CONTAINER_REGISTRY_USERNAME,
        password: process.env.CONTAINER_REGISTRY_PASSWORD
      },
      
      // Resource limits by tier
      resourceLimits: {
        free: {
          cpuLimit: parseFloat(process.env.FREE_TIER_CPU_LIMIT) || 0.5,
          memoryLimit: process.env.FREE_TIER_MEMORY_LIMIT || '512m',
          storageLimit: process.env.FREE_TIER_STORAGE_LIMIT || '1g',
          executionTimeLimit: parseInt(process.env.FREE_TIER_EXECUTION_TIME_LIMIT) || 30,
          maxContainers: parseInt(process.env.FREE_TIER_MAX_CONTAINERS) || 2
        },
        pro: {
          cpuLimit: parseFloat(process.env.PRO_TIER_CPU_LIMIT) || 2,
          memoryLimit: process.env.PRO_TIER_MEMORY_LIMIT || '2g',
          storageLimit: process.env.PRO_TIER_STORAGE_LIMIT || '10g',
          executionTimeLimit: parseInt(process.env.PRO_TIER_EXECUTION_TIME_LIMIT) || 300,
          maxContainers: parseInt(process.env.PRO_TIER_MAX_CONTAINERS) || 10
        },
        enterprise: {
          cpuLimit: parseFloat(process.env.ENTERPRISE_TIER_CPU_LIMIT) || 8,
          memoryLimit: process.env.ENTERPRISE_TIER_MEMORY_LIMIT || '8g',
          storageLimit: process.env.ENTERPRISE_TIER_STORAGE_LIMIT || '100g',
          executionTimeLimit: parseInt(process.env.ENTERPRISE_TIER_EXECUTION_TIME_LIMIT) || 3600,
          maxContainers: parseInt(process.env.ENTERPRISE_TIER_MAX_CONTAINERS) || 50
        }
      },
      
      // Security settings
      enableSeccomp: config.enableSeccomp ?? true,
      enableAppArmor: config.enableAppArmor ?? true,
      readOnlyRootFs: config.readOnlyRootFs ?? true,
      nonRootUser: config.nonRootUser ?? true,
      
      ...config
    };

    this.docker = this.config.developmentMode ? null : new Docker({ socketPath: this.config.dockerHost });
    this.containers = new Map(); // userId -> containers[]
    this.networks = new Map();
    this.volumes = new Map();
    this.executionQueues = new Map(); // userId -> execution queue
    
    this.stats = {
      totalContainers: 0,
      activeContainers: 0,
      totalExecutions: 0,
      failedExecutions: 0,
      avgExecutionTime: 0
    };

    if (!this.config.developmentMode) {
      this.initializeNetwork();
    } else {
      console.log('🔧 ContainerManager running in development mode (Docker disabled)');
    }
  }

  // Initialize Docker network for sandboxes
  async initializeNetwork() {
    try {
      const networks = await this.docker.listNetworks();
      const existingNetwork = networks.find(n => n.Name === this.config.networkName);
      
      if (!existingNetwork) {
        const network = await this.docker.createNetwork({
          Name: this.config.networkName,
          Driver: 'bridge',
          Internal: false,
          IPAM: {
            Config: [{
              Subnet: '172.20.0.0/16',
              Gateway: '172.20.0.1'
            }]
          },
          Options: {
            'com.docker.network.bridge.enable_icc': 'true',
            'com.docker.network.bridge.host_binding_ipv4': '0.0.0.0'
          }
        });
        
        console.log(`Created Docker network: ${this.config.networkName}`);
        this.emit('networkCreated', { networkId: network.id });
      }
    } catch (error) {
      console.error('Failed to initialize Docker network:', error);
      this.emit('error', { type: 'network_init', error });
    }
  }

  // Create isolated container for user
  async createUserContainer(userId, userTier, options = {}) {
    try {
      // Development mode - return mock container
      if (this.config.developmentMode) {
        const mockContainerId = `mock-${userId}-${crypto.randomBytes(4).toString('hex')}`;
        const mockContainer = {
          containerId: mockContainerId,
          name: `sandbox-${userId}-mock`,
          status: 'running',
          created: new Date(),
          tier: userTier,
          mode: 'development'
        };
        
        const userContainers = this.containers.get(userId) || [];
        userContainers.push(mockContainer);
        this.containers.set(userId, userContainers);
        
        console.log(`🔧 Created mock container for user ${userId}: ${mockContainerId}`);
        return mockContainer;
      }
      const limits = this.config.resourceLimits[userTier] || this.config.resourceLimits.free;
      
      // Check container limits
      const userContainers = this.containers.get(userId) || [];
      if (userContainers.length >= limits.maxContainers) {
        throw new Error(`Container limit exceeded for ${userTier} tier: ${limits.maxContainers}`);
      }

      // Generate unique container name
      const containerName = `sandbox-${userId}-${crypto.randomBytes(4).toString('hex')}`;
      
      // Create volume for user data
      const volumeName = `${containerName}-data`;
      await this.createUserVolume(volumeName, limits.storageLimit);

      // Prepare container configuration
      const containerConfig = {
        Image: options.image || 'node:18-alpine',
        name: containerName,
        Hostname: containerName,
        User: this.config.nonRootUser ? '1000:1000' : undefined,
        WorkingDir: '/workspace',
        
        // Resource limits
        HostConfig: {
          Memory: this.parseMemoryLimit(limits.memoryLimit),
          CpuShares: Math.floor(limits.cpuLimit * 1024),
          PidsLimit: 100,
          ReadonlyRootfs: this.config.readOnlyRootFs,
          
          // Security settings
          SecurityOpt: this.buildSecurityOptions(),
          CapDrop: ['ALL'],
          CapAdd: ['CHOWN', 'SETUID', 'SETGID'],
          
          // Network settings
          NetworkMode: this.config.networkName,
          
          // Volume mounts
          Binds: [
            `${volumeName}:/workspace`,
            '/tmp:/tmp:rw,noexec,nosuid,size=100m'
          ],
          
          // Ulimits
          Ulimits: [
            { Name: 'nofile', Soft: 1024, Hard: 1024 },
            { Name: 'nproc', Soft: 32, Hard: 32 }
          ]
        },
        
        // Environment variables
        Env: [
          'NODE_ENV=sandbox',
          `USER_ID=${userId}`,
          `TIER=${userTier}`,
          'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        ],
        
        // Exposed ports
        ExposedPorts: {
          '3000/tcp': {},
          '8080/tcp': {}
        },
        
        // Labels for identification
        Labels: {
          'sandbox.user-id': userId,
          'sandbox.tier': userTier,
          'sandbox.created': new Date().toISOString(),
          'sandbox.type': 'development'
        },
        
        // Attach streams
        AttachStdout: true,
        AttachStderr: true,
        AttachStdin: false,
        
        ...options.containerConfig
      };

      // Create container
      const container = await this.docker.createContainer(containerConfig);
      
      // Start container
      await container.start();
      
      // Get container info
      const containerInfo = await container.inspect();
      
      const sandboxContainer = {
        id: container.id,
        name: containerName,
        userId,
        userTier,
        container,
        containerInfo,
        volumeName,
        createdAt: new Date(),
        lastActivity: new Date(),
        status: 'running',
        executions: 0,
        limits
      };

      // Store container reference
      if (!this.containers.has(userId)) {
        this.containers.set(userId, []);
      }
      this.containers.get(userId).push(sandboxContainer);
      this.volumes.set(volumeName, { userId, containerId: container.id });

      this.stats.totalContainers++;
      this.stats.activeContainers++;

      this.emit('containerCreated', sandboxContainer);
      
      return sandboxContainer;
      
    } catch (error) {
      this.emit('containerError', { userId, userTier, error });
      throw error;
    }
  }

  // Create user data volume
  async createUserVolume(volumeName, sizeLimit) {
    try {
      await this.docker.createVolume({
        Name: volumeName,
        Driver: 'local',
        DriverOpts: {
          type: 'tmpfs',
          device: 'tmpfs',
          o: `size=${sizeLimit},uid=1000,gid=1000`
        },
        Labels: {
          'sandbox.volume': 'true',
          'sandbox.created': new Date().toISOString()
        }
      });
    } catch (error) {
      console.error(`Failed to create volume ${volumeName}:`, error);
      throw error;
    }
  }

  // Execute code in user container
  async executeCode(userId, containerId, code, options = {}) {
    try {
      const userContainers = this.containers.get(userId) || [];
      const sandboxContainer = userContainers.find(c => c.id === containerId);
      
      if (!sandboxContainer) {
        throw new Error('Container not found');
      }

      // Check execution limits
      const limits = sandboxContainer.limits;
      const executionTimeout = (options.timeout || limits.executionTimeLimit) * 1000;

      // Update last activity
      sandboxContainer.lastActivity = new Date();
      sandboxContainer.executions++;

      const startTime = Date.now();
      
      // Create execution context
      const execConfig = {
        AttachStdout: true,
        AttachStderr: true,
        AttachStdin: true,
        Tty: false,
        Cmd: this.buildExecutionCommand(code, options),
        Env: [
          `EXECUTION_ID=${crypto.randomUUID()}`,
          `TIMEOUT=${options.timeout || limits.executionTimeLimit}`,
          ...this.buildSandboxEnvironment(userId, options)
        ],
        User: this.config.nonRootUser ? '1000:1000' : undefined,
        WorkingDir: options.workingDir || '/workspace'
      };

      // Execute in container
      const exec = await sandboxContainer.container.exec(execConfig);
      const stream = await exec.start({ Detach: false, Tty: false });

      // Collect output
      let stdout = '';
      let stderr = '';
      
      return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          stream.destroy();
          reject(new Error(`Execution timeout after ${executionTimeout}ms`));
        }, executionTimeout);

        // Demultiplex Docker stream
        this.docker.modem.demuxStream(stream, 
          // stdout
          (chunk) => { stdout += chunk.toString(); },
          // stderr  
          (chunk) => { stderr += chunk.toString(); }
        );

        stream.on('end', async () => {
          clearTimeout(timeoutId);
          
          try {
            const inspectResult = await exec.inspect();
            const executionTime = Date.now() - startTime;
            
            // Update stats
            this.stats.totalExecutions++;
            this.stats.avgExecutionTime = (
              (this.stats.avgExecutionTime * (this.stats.totalExecutions - 1) + executionTime) / 
              this.stats.totalExecutions
            );

            const result = {
              executionId: execConfig.Env[0].split('=')[1],
              exitCode: inspectResult.ExitCode,
              stdout: stdout.trim(),
              stderr: stderr.trim(),
              executionTime,
              containerId,
              userId,
              timestamp: new Date().toISOString()
            };

            this.emit('codeExecuted', result);
            resolve(result);
            
          } catch (inspectError) {
            this.stats.failedExecutions++;
            reject(inspectError);
          }
        });

        stream.on('error', (error) => {
          clearTimeout(timeoutId);
          this.stats.failedExecutions++;
          reject(error);
        });
      });

    } catch (error) {
      this.stats.failedExecutions++;
      this.emit('executionError', { userId, containerId, error });
      throw error;
    }
  }

  // Build execution command based on code type
  buildExecutionCommand(code, options = {}) {
    const language = options.language || 'javascript';
    
    // Create temporary file with code
    const filename = `/tmp/code_${Date.now()}.${this.getFileExtension(language)}`;
    
    switch (language) {
      case 'javascript':
      case 'node':
        return [
          'sh', '-c', 
          `echo '${this.escapeCode(code)}' > ${filename} && timeout ${options.timeout || 30} node ${filename}`
        ];
        
      case 'python':
        return [
          'sh', '-c',
          `echo '${this.escapeCode(code)}' > ${filename} && timeout ${options.timeout || 30} python3 ${filename}`
        ];
        
      case 'bash':
      case 'shell':
        return [
          'sh', '-c',
          `echo '${this.escapeCode(code)}' > ${filename} && timeout ${options.timeout || 30} bash ${filename}`
        ];
        
      case 'go':
        return [
          'sh', '-c',
          `echo '${this.escapeCode(code)}' > ${filename} && timeout ${options.timeout || 30} go run ${filename}`
        ];
        
      default:
        throw new Error(`Unsupported language: ${language}`);
    }
  }

  // Build sandbox environment variables
  buildSandboxEnvironment(userId, options = {}) {
    return [
      'HOME=/tmp',
      'TMPDIR=/tmp',
      'NO_UPDATE_NOTIFIER=1',
      'NODE_ENV=sandbox',
      'PYTHONDONTWRITEBYTECODE=1',
      'PYTHONUNBUFFERED=1',
      'GO111MODULE=on',
      `SANDBOX_USER_ID=${userId}`,
      ...Object.entries(options.env || {}).map(([key, value]) => `${key}=${value}`)
    ];
  }

  // Get file extension for language
  getFileExtension(language) {
    const extensions = {
      'javascript': 'js',
      'node': 'js',
      'python': 'py',
      'bash': 'sh',
      'shell': 'sh',
      'go': 'go',
      'typescript': 'ts'
    };
    
    return extensions[language] || 'txt';
  }

  // Escape code for shell execution
  escapeCode(code) {
    return code.replace(/'/g, "'\"'\"'");
  }

  // Build security options
  buildSecurityOptions() {
    const options = [];
    
    if (this.config.enableSeccomp) {
      options.push('seccomp=unconfined'); // Could use custom seccomp profile
    }
    
    if (this.config.enableAppArmor) {
      options.push('apparmor=unconfined'); // Could use custom AppArmor profile
    }
    
    return options;
  }

  // Parse memory limit string to bytes
  parseMemoryLimit(memoryStr) {
    const units = { 'k': 1024, 'm': 1024 * 1024, 'g': 1024 * 1024 * 1024 };
    const match = memoryStr.toString().toLowerCase().match(/^(\d+)([kmg]?)$/);
    
    if (!match) return 512 * 1024 * 1024; // Default 512MB
    
    const value = parseInt(match[1]);
    const unit = match[2] || '';
    
    return value * (units[unit] || 1);
  }

  // Stop and remove user container
  async removeContainer(userId, containerId) {
    try {
      const userContainers = this.containers.get(userId) || [];
      const containerIndex = userContainers.findIndex(c => c.id === containerId);
      
      if (containerIndex === -1) {
        throw new Error('Container not found');
      }

      const sandboxContainer = userContainers[containerIndex];
      
      // Stop container
      try {
        await sandboxContainer.container.stop({ t: 10 });
      } catch (stopError) {
        // Container might already be stopped
        console.warn('Container stop warning:', stopError.message);
      }

      // Remove container
      await sandboxContainer.container.remove({ force: true });
      
      // Remove volume
      try {
        const volume = this.docker.getVolume(sandboxContainer.volumeName);
        await volume.remove();
        this.volumes.delete(sandboxContainer.volumeName);
      } catch (volumeError) {
        console.warn('Volume removal warning:', volumeError.message);
      }

      // Remove from tracking
      userContainers.splice(containerIndex, 1);
      if (userContainers.length === 0) {
        this.containers.delete(userId);
      }

      this.stats.activeContainers--;
      
      this.emit('containerRemoved', { userId, containerId });
      
      return true;
      
    } catch (error) {
      this.emit('containerError', { userId, containerId, error });
      throw error;
    }
  }

  // Get user containers
  getUserContainers(userId) {
    const containers = this.containers.get(userId) || [];
    
    return containers.map(container => ({
      id: container.id,
      name: container.name,
      status: container.status,
      createdAt: container.createdAt,
      lastActivity: container.lastActivity,
      executions: container.executions,
      tier: container.userTier,
      limits: container.limits
    }));
  }

  // Get container logs
  async getContainerLogs(userId, containerId, options = {}) {
    try {
      const userContainers = this.containers.get(userId) || [];
      const sandboxContainer = userContainers.find(c => c.id === containerId);
      
      if (!sandboxContainer) {
        throw new Error('Container not found');
      }

      const logOptions = {
        follow: options.follow || false,
        stdout: options.stdout !== false,
        stderr: options.stderr !== false,
        timestamps: options.timestamps || false,
        tail: options.tail || 100,
        since: options.since || 0
      };

      const logStream = await sandboxContainer.container.logs(logOptions);
      
      if (options.follow) {
        return logStream;
      }
      
      // Return logs as string
      return logStream.toString();
      
    } catch (error) {
      this.emit('containerError', { userId, containerId, error });
      throw error;
    }
  }

  // Monitor container resources
  async getContainerStats(userId, containerId) {
    try {
      const userContainers = this.containers.get(userId) || [];
      const sandboxContainer = userContainers.find(c => c.id === containerId);
      
      if (!sandboxContainer) {
        throw new Error('Container not found');
      }

      const statsStream = await sandboxContainer.container.stats({ stream: false });
      
      return {
        containerId,
        userId,
        stats: statsStream,
        timestamp: new Date().toISOString()
      };
      
    } catch (error) {
      this.emit('containerError', { userId, containerId, error });
      throw error;
    }
  }

  // Clean up expired containers
  async cleanupExpiredContainers() {
    const now = new Date();
    const expiredContainers = [];
    
    for (const [userId, containers] of this.containers.entries()) {
      for (const container of containers) {
        const idleTime = now - container.lastActivity;
        const maxIdleTime = 2 * 60 * 60 * 1000; // 2 hours
        
        if (idleTime > maxIdleTime) {
          expiredContainers.push({ userId, containerId: container.id });
        }
      }
    }

    // Remove expired containers
    for (const { userId, containerId } of expiredContainers) {
      try {
        await this.removeContainer(userId, containerId);
        console.log(`Cleaned up expired container: ${containerId}`);
      } catch (error) {
        console.error(`Failed to cleanup container ${containerId}:`, error);
      }
    }

    this.emit('cleanupCompleted', { removedContainers: expiredContainers.length });
  }

  // Get system statistics
  getSystemStats() {
    return {
      ...this.stats,
      totalUsers: this.containers.size,
      containersByTier: this.getContainersByTier(),
      averageContainersPerUser: this.stats.activeContainers / Math.max(this.containers.size, 1),
      successRate: this.stats.totalExecutions > 0 ? 
        ((this.stats.totalExecutions - this.stats.failedExecutions) / this.stats.totalExecutions * 100).toFixed(2) + '%' :
        '0%'
    };
  }

  // Get container distribution by tier
  getContainersByTier() {
    const tierCount = { free: 0, pro: 0, enterprise: 0 };
    
    for (const containers of this.containers.values()) {
      for (const container of containers) {
        tierCount[container.userTier] = (tierCount[container.userTier] || 0) + 1;
      }
    }
    
    return tierCount;
  }

  // Health check
  async healthCheck() {
    try {
      await this.docker.ping();
      
      return {
        healthy: true,
        dockerConnected: true,
        stats: this.getSystemStats(),
        networkExists: await this.checkNetworkExists()
      };
      
    } catch (error) {
      return {
        healthy: false,
        dockerConnected: false,
        error: error.message
      };
    }
  }

  // Check if network exists
  async checkNetworkExists() {
    try {
      const networks = await this.docker.listNetworks();
      return networks.some(n => n.Name === this.config.networkName);
    } catch (error) {
      return false;
    }
  }

  // Graceful shutdown
  async shutdown() {
    console.log('Shutting down Container Manager...');
    
    // Stop all containers
    const containerPromises = [];
    for (const [userId, containers] of this.containers.entries()) {
      for (const container of containers) {
        containerPromises.push(this.removeContainer(userId, container.id));
      }
    }
    
    await Promise.all(containerPromises);
    
    // Clean up network (optional - can be left for reuse)
    // await this.cleanupNetwork();
    
    this.emit('shutdown');
  }
}

module.exports = ContainerManager;