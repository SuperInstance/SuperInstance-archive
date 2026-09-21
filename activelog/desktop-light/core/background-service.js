/**
 * Background Service - Minimal footprint background operations
 */

const { EventEmitter } = require('events');
const ResourceManager = require('./resource-manager');

class BackgroundService extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.config = {
            minimalMode: options.minimalMode ?? true,
            stealthMode: options.stealthMode ?? false,
            backgroundPriority: options.backgroundPriority || 'low',
            maxBackgroundTasks: options.maxBackgroundTasks || 3,
            taskTimeout: options.taskTimeout || 30000,
            heartbeatInterval: options.heartbeatInterval || 60000,
            ...options
        };
        
        this.resourceManager = new ResourceManager({
            gameMode: true,
            batteryOptimization: true,
            maxCpuUsage: 2,
            maxMemoryUsage: 50 * 1024 * 1024 // 50MB
        });
        
        this.state = {
            isRunning: false,
            isPaused: false,
            isHidden: false,
            lastActivity: Date.now(),
            backgroundTasks: new Map(),
            scheduledTasks: new Map(),
            activeConnections: new Set(),
            serviceWorkers: new Map()
        };
        
        this.queues = {
            high: [],
            normal: [],
            low: [],
            idle: []
        };
        
        this.init();
    }
    
    init() {
        this.setupResourceMonitoring();
        this.setupTaskScheduling();
        this.setupHeartbeat();
        this.setupGameModeHandling();
        this.setupStealthMode();
        
        // OS integration
        this.setupSystemTray();
        this.setupWindowManagement();
        
        console.log('🔧 Background Service initialized in minimal mode');
    }
    
    setupResourceMonitoring() {
        this.resourceManager.on('gameModeEnabled', () => {
            this.enterGameFriendlyMode();
        });
        
        this.resourceManager.on('gameModeDisabled', () => {
            this.exitGameFriendlyMode();
        });
        
        this.resourceManager.on('lowPowerModeEnabled', () => {
            this.enterPowerSavingMode();
        });
        
        this.resourceManager.on('memoryCleanup', () => {
            this.performBackgroundCleanup();
        });
    }
    
    setupTaskScheduling() {
        this.scheduler = {
            running: false,
            currentTask: null,
            taskHistory: [],
            failedTasks: new Map()
        };
        
        // Start task processing loop
        this.startTaskProcessor();
    }
    
    startTaskProcessor() {
        const processNext = async () => {
            if (this.state.isPaused || !this.state.isRunning) {
                setTimeout(processNext, 5000);
                return;
            }
            
            const task = this.getNextTask();
            if (task) {
                await this.executeTask(task);
            }
            
            // Adaptive scheduling based on system state
            const delay = this.calculateNextTaskDelay();
            setTimeout(processNext, delay);
        };
        
        this.state.isRunning = true;
        processNext();
    }
    
    getNextTask() {
        // Priority-based task selection
        for (const priority of ['high', 'normal', 'low', 'idle']) {
            if (this.queues[priority].length > 0) {
                // Check if we can run this priority level
                if (this.canExecutePriority(priority)) {
                    return this.queues[priority].shift();
                }
            }
        }
        return null;
    }
    
    canExecutePriority(priority) {
        const usage = this.resourceManager.getResourceUsage();
        
        switch (priority) {
            case 'high':
                return true; // Always allow high priority
                
            case 'normal':
                return usage.cpu.usage < 3 && !usage.game.detected;
                
            case 'low':
                return usage.cpu.usage < 2 && !usage.game.detected && !usage.battery.lowPowerMode;
                
            case 'idle':
                return usage.cpu.usage < 1 && !usage.game.detected && !usage.battery.lowPowerMode;
                
            default:
                return false;
        }
    }
    
    async executeTask(task) {
        const startTime = Date.now();
        
        try {
            this.scheduler.currentTask = task;
            console.log(`🔄 Executing background task: ${task.name}`);
            
            // Set timeout for task
            const timeout = setTimeout(() => {
                task.cancel?.();
                this.emit('taskTimeout', task);
            }, this.config.taskTimeout);
            
            // Execute task with resource monitoring
            const result = await task.execute();
            
            clearTimeout(timeout);
            
            // Update task history
            this.scheduler.taskHistory.push({
                name: task.name,
                duration: Date.now() - startTime,
                result: 'success',
                timestamp: Date.now()
            });
            
            this.emit('taskCompleted', { task, result });
            
        } catch (error) {
            console.error(`❌ Background task failed: ${task.name}`, error);
            
            // Handle failed tasks
            const failCount = this.scheduler.failedTasks.get(task.name) || 0;
            this.scheduler.failedTasks.set(task.name, failCount + 1);
            
            // Retry logic
            if (failCount < 3 && task.retryable) {
                this.scheduleTask(task, 'low', 30000); // Retry in 30 seconds
            }
            
            this.emit('taskFailed', { task, error });
            
        } finally {
            this.scheduler.currentTask = null;
        }
    }
    
    calculateNextTaskDelay() {
        const usage = this.resourceManager.getResourceUsage();
        
        // Adaptive delay based on system state
        if (usage.game.detected) {
            return 30000; // 30 seconds when gaming
        } else if (usage.battery.lowPowerMode) {
            return 60000; // 1 minute on low battery
        } else if (usage.cpu.usage > 5) {
            return 10000; // 10 seconds under high load
        } else {
            return 5000; // 5 seconds normally
        }
    }
    
    setupHeartbeat() {
        this.heartbeat = {
            interval: null,
            lastBeat: Date.now(),
            missedBeats: 0,
            isHealthy: true
        };
        
        this.heartbeat.interval = setInterval(() => {
            this.sendHeartbeat();
        }, this.config.heartbeatInterval);
    }
    
    sendHeartbeat() {
        const now = Date.now();
        const timeSinceLastBeat = now - this.heartbeat.lastBeat;
        
        if (timeSinceLastBeat > this.config.heartbeatInterval * 1.5) {
            this.heartbeat.missedBeats++;
            
            if (this.heartbeat.missedBeats > 3) {
                this.heartbeat.isHealthy = false;
                this.emit('serviceUnhealthy');
            }
        } else {
            this.heartbeat.missedBeats = 0;
            this.heartbeat.isHealthy = true;
        }
        
        this.heartbeat.lastBeat = now;
        this.emit('heartbeat', {
            timestamp: now,
            healthy: this.heartbeat.isHealthy,
            resourceUsage: this.resourceManager.getResourceUsage(),
            activeTasks: this.state.backgroundTasks.size
        });
    }
    
    setupGameModeHandling() {
        // Game-friendly behavior
        this.gameMode = {
            originalPriority: null,
            pausedFeatures: new Set(),
            reducedActivity: false
        };
    }
    
    enterGameFriendlyMode() {
        console.log('🎮 Entering game-friendly mode');
        
        // Lower process priority
        try {
            if (process.platform === 'win32') {
                // Windows priority classes
                process.priority = 19; // Lowest priority
            } else {
                // Unix nice values
                process.nice?.(19);
            }
        } catch (error) {
            console.warn('Could not set process priority:', error.message);
        }
        
        // Pause non-essential background tasks
        this.pauseNonEssentialTasks();
        
        // Reduce resource usage
        this.config.maxBackgroundTasks = 1;
        this.config.heartbeatInterval = 120000; // 2 minutes
        
        this.gameMode.reducedActivity = true;
        this.emit('gameModeActivated');
    }
    
    exitGameFriendlyMode() {
        console.log('🎮 Exiting game-friendly mode');
        
        // Restore normal priority
        try {
            if (process.platform === 'win32') {
                process.priority = 0; // Normal priority
            } else {
                process.nice?.(0);
            }
        } catch (error) {
            console.warn('Could not restore process priority:', error.message);
        }
        
        // Resume tasks
        this.resumeTasks();
        
        // Restore normal settings
        this.config.maxBackgroundTasks = 3;
        this.config.heartbeatInterval = 60000;
        
        this.gameMode.reducedActivity = false;
        this.emit('gameModeDeactivated');
    }
    
    enterPowerSavingMode() {
        console.log('🔋 Entering power saving mode');
        
        // Reduce activity even further
        this.config.maxBackgroundTasks = 1;
        this.config.heartbeatInterval = 300000; // 5 minutes
        
        // Pause most background operations
        this.state.isPaused = true;
        
        setTimeout(() => {
            this.state.isPaused = false;
        }, 60000); // Resume after 1 minute
        
        this.emit('powerSavingModeActivated');
    }
    
    setupStealthMode() {
        if (!this.config.stealthMode) return;
        
        this.stealth = {
            hideFromTaskManager: true,
            minimalTrayPresence: true,
            suppressNotifications: true,
            encryptedCommunication: true
        };
    }
    
    setupSystemTray() {
        // Minimal system tray integration
        this.tray = {
            visible: !this.config.stealthMode,
            tooltip: 'ActiveLog (Background)',
            menu: [
                { label: 'Status', enabled: false },
                { label: 'Pause', click: () => this.pause() },
                { label: 'Exit', click: () => this.shutdown() }
            ]
        };
        
        if (this.config.minimalMode) {
            this.tray.visible = false;
        }
    }
    
    setupWindowManagement() {
        // No visible windows in background mode
        this.windowManager = {
            hasVisibleWindows: false,
            hiddenWindows: new Set(),
            allowedToShow: false
        };
    }
    
    pauseNonEssentialTasks() {
        const nonEssential = ['sync', 'analytics', 'telemetry', 'updates'];
        
        this.queues.low = this.queues.low.filter(task => {
            if (nonEssential.includes(task.category)) {
                this.gameMode.pausedFeatures.add(task);
                return false;
            }
            return true;
        });
        
        this.queues.idle = []; // Clear all idle tasks
    }
    
    resumeTasks() {
        // Restore paused tasks
        this.gameMode.pausedFeatures.forEach(task => {
            this.scheduleTask(task, 'low');
        });
        
        this.gameMode.pausedFeatures.clear();
    }
    
    performBackgroundCleanup() {
        console.log('🧹 Performing background cleanup');
        
        // Clean task history
        if (this.scheduler.taskHistory.length > 100) {
            this.scheduler.taskHistory = this.scheduler.taskHistory.slice(-50);
        }
        
        // Clean failed tasks
        this.scheduler.failedTasks.clear();
        
        // Clean connections
        this.state.activeConnections.forEach(conn => {
            if (!conn.isAlive?.()) {
                this.state.activeConnections.delete(conn);
            }
        });
    }
    
    // Public API methods
    
    scheduleTask(task, priority = 'normal', delay = 0) {
        const taskWrapper = {
            id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            name: task.name || 'unnamed_task',
            category: task.category || 'general',
            priority,
            execute: task.execute,
            cancel: task.cancel,
            retryable: task.retryable ?? true,
            scheduledAt: Date.now(),
            delay
        };
        
        if (delay > 0) {
            setTimeout(() => {
                this.queues[priority].push(taskWrapper);
            }, delay);
        } else {
            this.queues[priority].push(taskWrapper);
        }
        
        this.emit('taskScheduled', taskWrapper);
        return taskWrapper.id;
    }
    
    cancelTask(taskId) {
        for (const priority in this.queues) {
            const index = this.queues[priority].findIndex(task => task.id === taskId);
            if (index !== -1) {
                const task = this.queues[priority].splice(index, 1)[0];
                task.cancel?.();
                this.emit('taskCancelled', task);
                return true;
            }
        }
        return false;
    }
    
    pause() {
        this.state.isPaused = true;
        console.log('⏸️ Background service paused');
        this.emit('paused');
    }
    
    resume() {
        this.state.isPaused = false;
        console.log('▶️ Background service resumed');
        this.emit('resumed');
    }
    
    hide() {
        this.state.isHidden = true;
        this.tray.visible = false;
        this.windowManager.hasVisibleWindows = false;
        console.log('👻 Background service hidden');
        this.emit('hidden');
    }
    
    show() {
        this.state.isHidden = false;
        this.tray.visible = !this.config.stealthMode;
        console.log('👁️ Background service visible');
        this.emit('shown');
    }
    
    getStatus() {
        return {
            isRunning: this.state.isRunning,
            isPaused: this.state.isPaused,
            isHidden: this.state.isHidden,
            gameMode: this.gameMode.reducedActivity,
            resourceUsage: this.resourceManager.getResourceUsage(),
            taskQueues: {
                high: this.queues.high.length,
                normal: this.queues.normal.length,
                low: this.queues.low.length,
                idle: this.queues.idle.length
            },
            activeTasks: this.state.backgroundTasks.size,
            lastActivity: this.state.lastActivity,
            heartbeat: this.heartbeat.isHealthy
        };
    }
    
    getPerformanceMetrics() {
        return {
            uptime: Date.now() - this.state.lastActivity,
            tasksCompleted: this.scheduler.taskHistory.length,
            tasksSuccessRate: this.calculateSuccessRate(),
            averageTaskDuration: this.calculateAverageTaskDuration(),
            resourceEfficiency: this.calculateResourceEfficiency(),
            memoryFootprint: process.memoryUsage().heapUsed,
            cpuUsage: this.resourceManager.getMetrics().cpuUsage
        };
    }
    
    calculateSuccessRate() {
        const successful = this.scheduler.taskHistory.filter(t => t.result === 'success').length;
        return successful / Math.max(this.scheduler.taskHistory.length, 1);
    }
    
    calculateAverageTaskDuration() {
        const durations = this.scheduler.taskHistory.map(t => t.duration);
        return durations.reduce((a, b) => a + b, 0) / Math.max(durations.length, 1);
    }
    
    calculateResourceEfficiency() {
        const usage = this.resourceManager.getResourceUsage();
        const memoryEfficiency = 1 - (usage.memory.percentage / 100);
        const cpuEfficiency = 1 - (usage.cpu.usage / usage.cpu.limit);
        return (memoryEfficiency + cpuEfficiency) / 2;
    }
    
    async shutdown() {
        console.log('🔄 Shutting down Background Service...');
        
        this.state.isRunning = false;
        
        // Stop heartbeat
        if (this.heartbeat.interval) {
            clearInterval(this.heartbeat.interval);
        }
        
        // Cancel all pending tasks
        for (const priority in this.queues) {
            this.queues[priority].forEach(task => {
                task.cancel?.();
            });
            this.queues[priority] = [];
        }
        
        // Shutdown resource manager
        await this.resourceManager.shutdown();
        
        // Clean up connections
        this.state.activeConnections.clear();
        
        this.emit('shutdown');
        console.log('✅ Background Service shutdown complete');
    }
}

module.exports = BackgroundService;