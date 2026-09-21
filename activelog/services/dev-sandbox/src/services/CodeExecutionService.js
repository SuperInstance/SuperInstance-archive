const vm = require('vm');
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');
const isolatedVm = require('isolated-vm');
const crypto = require('crypto');
const { EventEmitter } = require('events');
const fs = require('fs').promises;
const path = require('path');

class CodeExecutionService extends EventEmitter {
  constructor(containerManager, config = {}) {
    super();
    
    this.containerManager = containerManager;
    this.config = {
      // Execution modes
      defaultMode: config.defaultMode || 'container', // container, vm, isolated-vm, worker
      
      // Security settings
      enableSandboxing: config.enableSandboxing ?? true,
      maxExecutionTime: config.maxExecutionTime || 30000, // 30 seconds
      maxMemoryUsage: config.maxMemoryUsage || 128 * 1024 * 1024, // 128MB
      maxOutputSize: config.maxOutputSize || 1024 * 1024, // 1MB
      
      // Resource limits by tier
      resourceLimits: {
        free: {
          maxExecutionTime: 10000,
          maxMemoryUsage: 64 * 1024 * 1024,
          maxOutputSize: 512 * 1024,
          concurrentExecutions: 2
        },
        pro: {
          maxExecutionTime: 60000,
          maxMemoryUsage: 256 * 1024 * 1024,
          maxOutputSize: 2 * 1024 * 1024,
          concurrentExecutions: 5
        },
        enterprise: {
          maxExecutionTime: 300000,
          maxMemoryUsage: 1024 * 1024 * 1024,
          maxOutputSize: 10 * 1024 * 1024,
          concurrentExecutions: 20
        }
      },
      
      // VM configuration
      vmGlobals: config.vmGlobals || {
        console: console,
        setTimeout: setTimeout,
        clearTimeout: clearTimeout,
        setInterval: setInterval,
        clearInterval: clearInterval,
        Buffer: Buffer,
        process: {
          env: {},
          version: process.version,
          platform: process.platform
        }
      },
      
      // Blocked modules and functions
      blockedModules: config.blockedModules || [
        'fs', 'child_process', 'cluster', 'worker_threads', 'os',
        'net', 'dgram', 'dns', 'http', 'https', 'url', 'crypto'
      ],
      blockedGlobals: config.blockedGlobals || [
        'require', 'module', 'exports', '__filename', '__dirname', 'global'
      ],
      
      ...config
    };

    this.executionQueues = new Map(); // userId -> execution queue
    this.activeExecutions = new Map(); // executionId -> execution info
    this.workerPool = new Map(); // workerId -> worker instance
    this.isolates = new Map(); // isolateId -> isolated-vm instance
    
    this.stats = {
      totalExecutions: 0,
      successfulExecutions: 0,
      failedExecutions: 0,
      timeoutExecutions: 0,
      avgExecutionTime: 0,
      executionsByMode: {
        container: 0,
        vm: 0,
        'isolated-vm': 0,
        worker: 0
      }
    };

    this.initializeWorkerPool();
  }

  // Initialize worker thread pool
  async initializeWorkerPool() {
    if (!isMainThread) return;
    
    const poolSize = this.config.workerPoolSize || 4;
    
    for (let i = 0; i < poolSize; i++) {
      await this.createWorker(`worker-${i}`);
    }
  }

  // Create a worker thread
  async createWorker(workerId) {
    try {
      const worker = new Worker(__filename, {
        workerData: { isWorker: true, workerId }
      });

      worker.on('message', (result) => {
        this.handleWorkerResult(result);
      });

      worker.on('error', (error) => {
        this.emit('workerError', { workerId, error });
        // Recreate worker
        setTimeout(() => this.createWorker(workerId), 1000);
      });

      worker.on('exit', (code) => {
        if (code !== 0) {
          console.warn(`Worker ${workerId} exited with code ${code}`);
          // Recreate worker
          setTimeout(() => this.createWorker(workerId), 1000);
        }
      });

      this.workerPool.set(workerId, {
        worker,
        busy: false,
        currentExecution: null
      });

    } catch (error) {
      console.error(`Failed to create worker ${workerId}:`, error);
    }
  }

  // Execute code with automatic mode selection
  async executeCode(userId, userTier, codeRequest) {
    const executionId = crypto.randomUUID();
    const limits = this.config.resourceLimits[userTier] || this.config.resourceLimits.free;
    
    try {
      // Check concurrent execution limits
      const userQueue = this.executionQueues.get(userId) || [];
      if (userQueue.length >= limits.concurrentExecutions) {
        throw new Error(`Concurrent execution limit exceeded: ${limits.concurrentExecutions}`);
      }

      // Create execution context
      const execution = {
        id: executionId,
        userId,
        userTier,
        code: codeRequest.code,
        language: codeRequest.language || 'javascript',
        mode: codeRequest.mode || this.selectExecutionMode(codeRequest),
        options: {
          ...codeRequest.options,
          timeout: Math.min(codeRequest.options?.timeout || limits.maxExecutionTime, limits.maxExecutionTime),
          memoryLimit: Math.min(codeRequest.options?.memoryLimit || limits.maxMemoryUsage, limits.maxMemoryUsage)
        },
        startTime: Date.now(),
        status: 'queued'
      };

      // Add to user queue
      if (!this.executionQueues.has(userId)) {
        this.executionQueues.set(userId, []);
      }
      this.executionQueues.get(userId).push(execution);
      this.activeExecutions.set(executionId, execution);

      this.emit('executionQueued', execution);

      // Execute based on mode
      const result = await this.executeByMode(execution);
      
      // Update statistics
      this.updateExecutionStats(execution, result);
      
      return result;
      
    } catch (error) {
      this.stats.failedExecutions++;
      this.emit('executionError', { executionId, userId, error });
      throw error;
    } finally {
      this.cleanupExecution(userId, executionId);
    }
  }

  // Select optimal execution mode
  selectExecutionMode(codeRequest) {
    const { language, requiresFileSystem, requiresNetwork, requiresModules } = codeRequest;
    
    // Complex code requiring full environment
    if (requiresFileSystem || requiresNetwork || requiresModules) {
      return 'container';
    }
    
    // Simple JavaScript - use isolated VM for maximum security
    if (language === 'javascript' && !requiresModules) {
      return 'isolated-vm';
    }
    
    // Medium complexity - use worker thread
    if (language === 'javascript') {
      return 'worker';
    }
    
    // Other languages need container
    return 'container';
  }

  // Execute code based on selected mode
  async executeByMode(execution) {
    execution.status = 'running';
    
    switch (execution.mode) {
      case 'container':
        return await this.executeInContainer(execution);
      case 'vm':
        return await this.executeInVM(execution);
      case 'isolated-vm':
        return await this.executeInIsolatedVM(execution);
      case 'worker':
        return await this.executeInWorker(execution);
      default:
        throw new Error(`Unsupported execution mode: ${execution.mode}`);
    }
  }

  // Execute in Docker container (most secure, supports all languages)
  async executeInContainer(execution) {
    try {
      const { userId, userTier, code, language, options } = execution;
      
      // Get user container or create one
      const userContainers = this.containerManager.getUserContainers(userId);
      let container = userContainers[0]; // Use first available container
      
      if (!container) {
        // Create temporary container for execution
        const containerInfo = await this.containerManager.createUserContainer(userId, userTier, {
          image: this.getLanguageImage(language)
        });
        container = containerInfo;
      }

      // Execute code in container
      const result = await this.containerManager.executeCode(
        userId,
        container.id,
        code,
        {
          language,
          timeout: options.timeout / 1000, // Convert to seconds
          ...options
        }
      );

      this.stats.executionsByMode.container++;
      
      return this.formatExecutionResult(execution, result);
      
    } catch (error) {
      throw new Error(`Container execution failed: ${error.message}`);
    }
  }

  // Execute in Node.js VM (moderate security, JavaScript only)
  async executeInVM(execution) {
    try {
      const { code, options } = execution;
      
      if (execution.language !== 'javascript') {
        throw new Error('VM execution only supports JavaScript');
      }

      let output = '';
      let errorOutput = '';
      
      // Create sandboxed context
      const sandbox = {
        ...this.config.vmGlobals,
        console: {
          log: (...args) => { output += args.join(' ') + '\n'; },
          error: (...args) => { errorOutput += args.join(' ') + '\n'; },
          warn: (...args) => { output += 'WARN: ' + args.join(' ') + '\n'; },
          info: (...args) => { output += 'INFO: ' + args.join(' ') + '\n'; }
        }
      };

      // Remove blocked globals
      for (const blocked of this.config.blockedGlobals) {
        delete sandbox[blocked];
      }

      const vmContext = vm.createContext(sandbox);
      
      // Execute with timeout
      const result = await this.executeWithTimeout(async () => {
        return vm.runInContext(code, vmContext, {
          timeout: options.timeout,
          displayErrors: true,
          breakOnSigint: true
        });
      }, options.timeout);

      this.stats.executionsByMode.vm++;
      
      return this.formatExecutionResult(execution, {
        executionId: execution.id,
        exitCode: 0,
        stdout: output,
        stderr: errorOutput,
        result: result,
        executionTime: Date.now() - execution.startTime
      });
      
    } catch (error) {
      if (error.message.includes('timeout')) {
        this.stats.timeoutExecutions++;
      }
      throw new Error(`VM execution failed: ${error.message}`);
    }
  }

  // Execute in isolated VM (maximum security, JavaScript only)
  async executeInIsolatedVM(execution) {
    try {
      const { code, options } = execution;
      
      if (execution.language !== 'javascript') {
        throw new Error('Isolated VM execution only supports JavaScript');
      }

      const isolateId = crypto.randomUUID();
      
      // Create new isolate
      const isolate = new isolatedVm.Isolate({
        memoryLimit: Math.floor(options.memoryLimit / 1024 / 1024) // Convert to MB
      });
      
      this.isolates.set(isolateId, isolate);
      
      // Create context
      const context = await isolate.createContext();
      
      let output = '';
      
      // Setup console in isolate
      const consoleRef = await isolate.compileScript(`
        globalThis.console = {
          log: function(...args) {
            return $0.apply(undefined, [args.join(' ')]);
          }
        };
      `);
      
      await consoleRef.run(context, [
        (message) => { output += message + '\n'; }
      ]);

      // Compile and run code
      const script = await isolate.compileScript(code);
      
      // Execute with timeout
      const result = await this.executeWithTimeout(async () => {
        return await script.run(context, {
          timeout: options.timeout,
          copy: true
        });
      }, options.timeout);

      // Cleanup
      context.release();
      isolate.dispose();
      this.isolates.delete(isolateId);
      
      this.stats.executionsByMode['isolated-vm']++;
      
      return this.formatExecutionResult(execution, {
        executionId: execution.id,
        exitCode: 0,
        stdout: output,
        stderr: '',
        result: result,
        executionTime: Date.now() - execution.startTime
      });
      
    } catch (error) {
      if (error.message.includes('timeout') || error.message.includes('Script execution timed out')) {
        this.stats.timeoutExecutions++;
      }
      throw new Error(`Isolated VM execution failed: ${error.message}`);
    }
  }

  // Execute in worker thread
  async executeInWorker(execution) {
    try {
      const { code, options } = execution;
      
      if (execution.language !== 'javascript') {
        throw new Error('Worker execution only supports JavaScript');
      }

      // Find available worker
      const availableWorker = Array.from(this.workerPool.values())
        .find(w => !w.busy);
        
      if (!availableWorker) {
        throw new Error('No workers available');
      }

      // Mark worker as busy
      availableWorker.busy = true;
      availableWorker.currentExecution = execution.id;

      // Send execution request to worker
      return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          availableWorker.busy = false;
          availableWorker.currentExecution = null;
          this.stats.timeoutExecutions++;
          reject(new Error('Worker execution timeout'));
        }, options.timeout);

        // Store resolver for worker response
        execution.resolve = (result) => {
          clearTimeout(timeoutId);
          availableWorker.busy = false;
          availableWorker.currentExecution = null;
          this.stats.executionsByMode.worker++;
          resolve(this.formatExecutionResult(execution, result));
        };

        execution.reject = (error) => {
          clearTimeout(timeoutId);
          availableWorker.busy = false;
          availableWorker.currentExecution = null;
          reject(error);
        };

        // Send to worker
        availableWorker.worker.postMessage({
          executionId: execution.id,
          code,
          options,
          timeout: options.timeout
        });
      });
      
    } catch (error) {
      throw new Error(`Worker execution failed: ${error.message}`);
    }
  }

  // Handle worker thread results
  handleWorkerResult(result) {
    const execution = this.activeExecutions.get(result.executionId);
    if (!execution) return;

    if (result.error) {
      execution.reject(new Error(result.error));
    } else {
      execution.resolve(result);
    }
  }

  // Execute function with timeout
  async executeWithTimeout(fn, timeout) {
    return Promise.race([
      fn(),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Execution timeout')), timeout);
      })
    ]);
  }

  // Format execution result
  formatExecutionResult(execution, rawResult) {
    const executionTime = Date.now() - execution.startTime;
    
    return {
      executionId: execution.id,
      userId: execution.userId,
      mode: execution.mode,
      language: execution.language,
      exitCode: rawResult.exitCode || 0,
      stdout: this.truncateOutput(rawResult.stdout || ''),
      stderr: this.truncateOutput(rawResult.stderr || ''),
      result: rawResult.result,
      executionTime,
      memoryUsed: rawResult.memoryUsed || 0,
      status: rawResult.exitCode === 0 ? 'success' : 'error',
      timestamp: new Date().toISOString()
    };
  }

  // Truncate output to prevent memory issues
  truncateOutput(output) {
    if (output.length <= this.config.maxOutputSize) {
      return output;
    }
    
    return output.substring(0, this.config.maxOutputSize) + '\n... [output truncated]';
  }

  // Get Docker image for language
  getLanguageImage(language) {
    const images = {
      javascript: 'node:18-alpine',
      python: 'python:3.11-slim',
      go: 'golang:1.21-alpine',
      rust: 'rust:1.75-slim',
      java: 'openjdk:17-alpine',
      php: 'php:8.2-cli-alpine',
      ruby: 'ruby:3.2-slim',
      c: 'gcc:latest',
      cpp: 'gcc:latest'
    };
    
    return images[language] || 'ubuntu:22.04';
  }

  // Update execution statistics
  updateExecutionStats(execution, result) {
    this.stats.totalExecutions++;
    
    if (result.status === 'success') {
      this.stats.successfulExecutions++;
    } else {
      this.stats.failedExecutions++;
    }
    
    // Update average execution time
    const avgTime = this.stats.avgExecutionTime;
    const totalExecs = this.stats.totalExecutions;
    this.stats.avgExecutionTime = (avgTime * (totalExecs - 1) + result.executionTime) / totalExecs;
  }

  // Cleanup execution from queues
  cleanupExecution(userId, executionId) {
    // Remove from active executions
    this.activeExecutions.delete(executionId);
    
    // Remove from user queue
    const userQueue = this.executionQueues.get(userId);
    if (userQueue) {
      const index = userQueue.findIndex(exec => exec.id === executionId);
      if (index !== -1) {
        userQueue.splice(index, 1);
      }
      
      if (userQueue.length === 0) {
        this.executionQueues.delete(userId);
      }
    }
  }

  // Execute code with streaming output
  async executeCodeWithStreaming(userId, userTier, codeRequest, streamCallback) {
    const executionId = crypto.randomUUID();
    const limits = this.config.resourceLimits[userTier] || this.config.resourceLimits.free;
    
    try {
      // Only container mode supports streaming
      if (codeRequest.mode && codeRequest.mode !== 'container') {
        throw new Error('Streaming execution only available in container mode');
      }

      const execution = {
        id: executionId,
        userId,
        userTier,
        code: codeRequest.code,
        language: codeRequest.language || 'javascript',
        mode: 'container',
        options: {
          ...codeRequest.options,
          timeout: Math.min(codeRequest.options?.timeout || limits.maxExecutionTime, limits.maxExecutionTime)
        },
        startTime: Date.now(),
        status: 'streaming'
      };

      this.activeExecutions.set(executionId, execution);

      // Get container
      const userContainers = this.containerManager.getUserContainers(userId);
      let container = userContainers[0];
      
      if (!container) {
        const containerInfo = await this.containerManager.createUserContainer(userId, userTier);
        container = containerInfo;
      }

      // Execute with streaming
      const logStream = await this.containerManager.getContainerLogs(
        userId, 
        container.id, 
        { follow: true, tail: 0 }
      );

      // Stream output to callback
      logStream.on('data', (chunk) => {
        streamCallback({
          type: 'output',
          data: chunk.toString(),
          executionId,
          timestamp: Date.now()
        });
      });

      logStream.on('end', () => {
        streamCallback({
          type: 'end',
          executionId,
          timestamp: Date.now()
        });
      });

      // Execute the code
      const result = await this.containerManager.executeCode(
        userId,
        container.id,
        codeRequest.code,
        {
          language: execution.language,
          timeout: execution.options.timeout / 1000
        }
      );

      return this.formatExecutionResult(execution, result);
      
    } catch (error) {
      streamCallback({
        type: 'error',
        error: error.message,
        executionId,
        timestamp: Date.now()
      });
      throw error;
    } finally {
      this.activeExecutions.delete(executionId);
    }
  }

  // Get execution status
  getExecutionStatus(executionId) {
    const execution = this.activeExecutions.get(executionId);
    if (!execution) {
      return null;
    }

    return {
      id: execution.id,
      userId: execution.userId,
      status: execution.status,
      mode: execution.mode,
      language: execution.language,
      startTime: execution.startTime,
      runningTime: Date.now() - execution.startTime
    };
  }

  // Cancel execution
  async cancelExecution(userId, executionId) {
    const execution = this.activeExecutions.get(executionId);
    if (!execution || execution.userId !== userId) {
      throw new Error('Execution not found or unauthorized');
    }

    execution.status = 'cancelled';
    
    // Cancel based on mode
    switch (execution.mode) {
      case 'container':
        // Would need to kill container process
        break;
      case 'worker':
        // Find and terminate worker
        const worker = Array.from(this.workerPool.values())
          .find(w => w.currentExecution === executionId);
        if (worker) {
          worker.busy = false;
          worker.currentExecution = null;
        }
        break;
      case 'isolated-vm':
        // Isolate disposal happens automatically on timeout
        break;
    }

    this.cleanupExecution(userId, executionId);
    this.emit('executionCancelled', { executionId, userId });
    
    return { cancelled: true, executionId };
  }

  // Get user execution statistics
  getUserStats(userId) {
    const userQueue = this.executionQueues.get(userId) || [];
    const activeExecs = Array.from(this.activeExecutions.values())
      .filter(exec => exec.userId === userId);

    return {
      queuedExecutions: userQueue.length,
      activeExecutions: activeExecs.length,
      totalActiveTime: activeExecs.reduce((total, exec) => 
        total + (Date.now() - exec.startTime), 0
      )
    };
  }

  // Get service statistics
  getServiceStats() {
    return {
      ...this.stats,
      successRate: this.stats.totalExecutions > 0 ? 
        ((this.stats.successfulExecutions / this.stats.totalExecutions) * 100).toFixed(2) + '%' :
        '0%',
      timeoutRate: this.stats.totalExecutions > 0 ?
        ((this.stats.timeoutExecutions / this.stats.totalExecutions) * 100).toFixed(2) + '%' :
        '0%',
      activeExecutions: this.activeExecutions.size,
      busyWorkers: Array.from(this.workerPool.values()).filter(w => w.busy).length,
      totalWorkers: this.workerPool.size,
      activeIsolates: this.isolates.size
    };
  }

  // Health check
  async healthCheck() {
    try {
      return {
        healthy: true,
        stats: this.getServiceStats(),
        workersHealthy: this.workerPool.size > 0,
        containerManagerHealthy: await this.containerManager.healthCheck().then(h => h.healthy)
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message
      };
    }
  }

  // Cleanup resources
  async cleanup() {
    // Cleanup isolates
    for (const isolate of this.isolates.values()) {
      try {
        isolate.dispose();
      } catch (error) {
        console.warn('Error disposing isolate:', error.message);
      }
    }
    this.isolates.clear();

    // Cleanup workers
    for (const { worker } of this.workerPool.values()) {
      try {
        await worker.terminate();
      } catch (error) {
        console.warn('Error terminating worker:', error.message);
      }
    }
    this.workerPool.clear();

    this.emit('cleanup');
  }
}

// Worker thread code for isolated JavaScript execution
if (!isMainThread && workerData?.isWorker) {
  parentPort.on('message', async ({ executionId, code, options, timeout }) => {
    try {
      let output = '';
      let errorOutput = '';
      
      // Create sandboxed console
      const sandboxConsole = {
        log: (...args) => { output += args.join(' ') + '\n'; },
        error: (...args) => { errorOutput += args.join(' ') + '\n'; },
        warn: (...args) => { output += 'WARN: ' + args.join(' ') + '\n'; },
        info: (...args) => { output += 'INFO: ' + args.join(' ') + '\n'; }
      };

      // Create sandbox
      const sandbox = {
        console: sandboxConsole,
        setTimeout: setTimeout,
        clearTimeout: clearTimeout,
        setInterval: setInterval,
        clearInterval: clearInterval,
        Buffer: Buffer,
        JSON: JSON,
        Math: Math,
        Date: Date,
        RegExp: RegExp,
        Array: Array,
        Object: Object,
        String: String,
        Number: Number,
        Boolean: Boolean
      };

      // Execute with timeout
      const result = await new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          reject(new Error('Worker execution timeout'));
        }, timeout);

        try {
          const vmContext = vm.createContext(sandbox);
          const vmResult = vm.runInContext(code, vmContext, {
            timeout: timeout,
            displayErrors: true
          });
          
          clearTimeout(timeoutId);
          resolve(vmResult);
        } catch (error) {
          clearTimeout(timeoutId);
          reject(error);
        }
      });

      parentPort.postMessage({
        executionId,
        exitCode: 0,
        stdout: output,
        stderr: errorOutput,
        result: result,
        executionTime: 0 // Would be calculated by main thread
      });

    } catch (error) {
      parentPort.postMessage({
        executionId,
        error: error.message
      });
    }
  });
}

module.exports = CodeExecutionService;