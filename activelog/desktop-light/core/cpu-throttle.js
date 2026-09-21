/**
 * Advanced CPU Throttling Controller - Intelligent CPU usage management and optimization
 */

const { EventEmitter } = require('events');
const os = require('os');
const cluster = require('cluster');

class CPUThrottleController extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.config = {
            maxCpuUsage: options.maxCpuUsage || 5, // 5% default limit
            throttleInterval: options.throttleInterval || 1000,
            adaptiveThrottling: options.adaptiveThrottling ?? true,
            gameDetection: options.gameDetection ?? true,
            thermalThrottling: options.thermalThrottling ?? true,
            workloadPrioritization: options.workloadPrioritization ?? true,
            multiCoreOptimization: options.multiCoreOptimization ?? true,
            ...options
        };
        
        this.state = {
            currentCpuUsage: 0,
            targetCpuUsage: this.config.maxCpuUsage,
            isThrottling: false,
            throttleLevel: 0,
            coreUsage: [],
            processQueue: new Map(),
            activeWorkers: new Set(),
            suspendedTasks: new Set(),
            lastMeasurement: Date.now(),
            thermalState: 'normal',
            workloadProfile: 'balanced'
        };
        
        this.metrics = {
            throttleEvents: 0,
            throttleDuration: 0,
            cpuSaved: 0,
            taskCompletions: 0,
            taskTimeouts: 0,
            thermalEvents: 0,
            coreBalancing: 0,
            adaptations: 0
        };
        
        this.systemInfo = {
            cpuCount: os.cpus().length,
            architecture: os.arch(),
            platform: os.platform(),
            loadAverage: [0, 0, 0],
            maxFrequency: 0,
            currentFrequency: 0
        };
        
        this.workloads = {
            high: [], // Time-critical tasks
            normal: [], // Standard tasks
            low: [], // Background tasks
            idle: [] // Idle-time tasks
        };
        
        this.timers = new Map();
        this.watchers = new Set();
        
        this.init();
    }
    
    init() {
        this.detectSystemCapabilities();
        this.startCpuMonitoring();
        this.setupThrottlingMechanisms();
        this.setupWorkloadManagement();
        this.setupAdaptiveControl();
        this.setupThermalManagement();
        
        console.log(`🔧 CPU Throttle Controller initialized (${this.systemInfo.cpuCount} cores)`);
    }
    
    detectSystemCapabilities() {
        const cpus = os.cpus();
        this.systemInfo.cpuCount = cpus.length;
        
        if (cpus.length > 0) {
            this.systemInfo.maxFrequency = cpus[0].speed;
            this.systemInfo.currentFrequency = cpus[0].speed;
        }
        
        // Initialize per-core usage tracking
        this.state.coreUsage = new Array(this.systemInfo.cpuCount).fill(0);
        
        console.log(`💻 Detected ${this.systemInfo.cpuCount}-core ${this.systemInfo.architecture} system`);
    }
    
    startCpuMonitoring() {
        this.cpuMonitor = {
            measurements: [],
            baseline: 0,
            trend: 0,
            lastCheck: Date.now()
        };
        
        this.timers.set('cpuMonitor', setInterval(() => {
            this.measureCpuUsage();
            this.updateLoadAverage();
            this.analyzeUsagePatterns();
            this.adjustThrottling();
        }, this.config.throttleInterval));
        
        // Initial measurement
        this.measureCpuUsage();
    }
    
    measureCpuUsage() {
        const startTime = process.hrtime();
        const startCpuUsage = process.cpuUsage();
        
        setTimeout(() => {
            const elapsedTime = process.hrtime(startTime);
            const cpuUsage = process.cpuUsage(startCpuUsage);
            
            // Calculate CPU percentage
            const totalTime = elapsedTime[0] * 1000000 + elapsedTime[1] / 1000; // microseconds
            const cpuTime = cpuUsage.user + cpuUsage.system;
            const cpuPercent = (cpuTime / totalTime) * 100;
            
            this.state.currentCpuUsage = Math.min(100, Math.max(0, cpuPercent));
            
            // Update measurements history
            this.cpuMonitor.measurements.push({
                timestamp: Date.now(),
                usage: this.state.currentCpuUsage,
                userTime: cpuUsage.user,
                systemTime: cpuUsage.system
            });
            
            // Keep only last 60 measurements (1 minute at 1s intervals)
            if (this.cpuMonitor.measurements.length > 60) {
                this.cpuMonitor.measurements.shift();
            }
            
            this.emit('cpuUsageUpdated', {
                usage: this.state.currentCpuUsage,
                target: this.state.targetCpuUsage,
                isThrottling: this.state.isThrottling
            });
            
        }, 100); // 100ms measurement window
    }
    
    updateLoadAverage() {
        this.systemInfo.loadAverage = os.loadavg();
        
        // Detect system load pressure
        const avgLoad = this.systemInfo.loadAverage[0];
        const loadPerCore = avgLoad / this.systemInfo.cpuCount;
        
        if (loadPerCore > 0.8) {
            console.log(`⚠️ High system load detected: ${loadPerCore.toFixed(2)} per core`);
            this.handleHighSystemLoad();
        }
    }
    
    analyzeUsagePatterns() {
        if (this.cpuMonitor.measurements.length < 5) return;
        
        const recent = this.cpuMonitor.measurements.slice(-5);
        const average = recent.reduce((sum, m) => sum + m.usage, 0) / recent.length;
        const trend = this.calculateTrend(recent);
        
        this.cpuMonitor.baseline = average;
        this.cpuMonitor.trend = trend;
        
        // Predict future usage
        const predicted = average + (trend * 3);
        
        if (predicted > this.state.targetCpuUsage * 1.2) {
            console.log(`📈 CPU usage trending up: ${predicted.toFixed(1)}% predicted`);
            this.preemptiveThrottle();
        }
    }
    
    calculateTrend(measurements) {
        if (measurements.length < 2) return 0;
        
        const first = measurements[0].usage;
        const last = measurements[measurements.length - 1].usage;
        return (last - first) / measurements.length;
    }
    
    adjustThrottling() {
        const usage = this.state.currentCpuUsage;
        const target = this.state.targetCpuUsage;
        
        if (usage > target && !this.state.isThrottling) {
            this.enableThrottling();
        } else if (usage <= target * 0.7 && this.state.isThrottling) {
            this.disableThrottling();
        } else if (this.state.isThrottling) {
            this.adjustThrottleLevel(usage, target);
        }
    }
    
    enableThrottling() {
        this.state.isThrottling = true;
        this.state.throttleLevel = 1;
        this.metrics.throttleEvents++;
        
        console.log(`🎛️ CPU throttling enabled (${this.state.currentCpuUsage.toFixed(1)}% > ${this.state.targetCpuUsage}%)`);
        
        // Apply throttling mechanisms
        this.applyProcessThrottling();
        this.suspendLowPriorityTasks();
        this.redistributeWorkload();
        
        this.emit('throttlingEnabled', {
            usage: this.state.currentCpuUsage,
            target: this.state.targetCpuUsage,
            level: this.state.throttleLevel
        });
    }
    
    disableThrottling() {
        const wasThrottling = this.state.isThrottling;
        this.state.isThrottling = false;
        this.state.throttleLevel = 0;
        
        if (wasThrottling) {
            console.log(`🎛️ CPU throttling disabled (${this.state.currentCpuUsage.toFixed(1)}% <= ${this.state.targetCpuUsage * 0.7}%)`);
            
            // Remove throttling mechanisms
            this.removeProcessThrottling();
            this.resumeSuspendedTasks();
            
            this.emit('throttlingDisabled', {
                usage: this.state.currentCpuUsage,
                target: this.state.targetCpuUsage
            });
        }
    }
    
    adjustThrottleLevel(currentUsage, targetUsage) {
        const overage = currentUsage - targetUsage;
        const newLevel = Math.min(5, Math.ceil(overage / targetUsage));
        
        if (newLevel !== this.state.throttleLevel) {
            console.log(`🎛️ Adjusting throttle level: ${this.state.throttleLevel} → ${newLevel}`);
            this.state.throttleLevel = newLevel;
            
            // Apply appropriate throttling level
            this.applyThrottleLevel(newLevel);
            
            this.emit('throttleLevelChanged', {
                oldLevel: this.state.throttleLevel,
                newLevel,
                usage: currentUsage,
                overage
            });
        }
    }
    
    applyThrottleLevel(level) {
        switch (level) {
            case 1: // Light throttling
                this.setTaskDelays(10);
                this.limitConcurrentTasks(Math.ceil(this.systemInfo.cpuCount * 0.8));
                break;
                
            case 2: // Moderate throttling
                this.setTaskDelays(25);
                this.limitConcurrentTasks(Math.ceil(this.systemInfo.cpuCount * 0.6));
                this.suspendIdleTasks();
                break;
                
            case 3: // Heavy throttling
                this.setTaskDelays(50);
                this.limitConcurrentTasks(Math.ceil(this.systemInfo.cpuCount * 0.4));
                this.suspendLowPriorityTasks();
                break;
                
            case 4: // Severe throttling
                this.setTaskDelays(100);
                this.limitConcurrentTasks(2);
                this.suspendNormalTasks();
                break;
                
            case 5: // Emergency throttling
                this.setTaskDelays(250);
                this.limitConcurrentTasks(1);
                this.suspendAllButCritical();
                break;
        }
    }
    
    setupThrottlingMechanisms() {
        this.throttlingMechanisms = {
            processNice: new Map(),
            taskDelays: new Map(),
            concurrencyLimits: new Map(),
            yieldIntervals: new Map()
        };
    }
    
    applyProcessThrottling() {
        // Adjust process priority
        try {
            if (process.platform !== 'win32') {
                const currentNice = process.getpriority();
                const newNice = Math.min(19, currentNice + this.state.throttleLevel);
                process.setpriority(newNice);
                this.throttlingMechanisms.processNice.set('main', { old: currentNice, new: newNice });
            }
        } catch (error) {
            console.warn('Could not adjust process priority:', error.message);
        }
        
        // Apply task-level throttling
        this.applyTaskThrottling();
    }
    
    removeProcessThrottling() {
        // Restore process priority
        for (const [pid, priority] of this.throttlingMechanisms.processNice) {
            try {
                process.setpriority(priority.old);
            } catch (error) {
                console.warn('Could not restore process priority:', error.message);
            }
        }
        this.throttlingMechanisms.processNice.clear();
        
        // Remove task-level throttling
        this.removeTaskThrottling();
    }
    
    applyTaskThrottling() {
        // Add delays to task execution
        for (const [taskId, task] of this.state.processQueue) {
            if (!task.delay) {
                task.delay = this.calculateTaskDelay(task.priority);
            }
        }
        
        // Limit concurrent task execution
        this.enforceConcurrencyLimits();
    }
    
    removeTaskThrottling() {
        // Remove delays from tasks
        for (const [taskId, task] of this.state.processQueue) {
            delete task.delay;
        }
        
        // Remove concurrency limits
        this.throttlingMechanisms.concurrencyLimits.clear();
    }
    
    calculateTaskDelay(priority) {
        const baseDelay = this.state.throttleLevel * 10; // Base delay in ms
        
        switch (priority) {
            case 'high':
                return baseDelay * 0.1;
            case 'normal':
                return baseDelay;
            case 'low':
                return baseDelay * 2;
            case 'idle':
                return baseDelay * 5;
            default:
                return baseDelay;
        }
    }
    
    setTaskDelays(baseDelay) {
        for (const [priority, tasks] of Object.entries(this.workloads)) {
            const multiplier = {
                high: 0.1,
                normal: 1,
                low: 2,
                idle: 5
            }[priority] || 1;
            
            const delay = baseDelay * multiplier;
            this.throttlingMechanisms.taskDelays.set(priority, delay);
        }
    }
    
    limitConcurrentTasks(maxConcurrent) {
        this.throttlingMechanisms.concurrencyLimits.set('global', maxConcurrent);
        
        // Distribute across priorities
        const highPriorityLimit = Math.ceil(maxConcurrent * 0.6);
        const normalPriorityLimit = Math.ceil(maxConcurrent * 0.3);
        const lowPriorityLimit = Math.ceil(maxConcurrent * 0.1);
        
        this.throttlingMechanisms.concurrencyLimits.set('high', highPriorityLimit);
        this.throttlingMechanisms.concurrencyLimits.set('normal', normalPriorityLimit);
        this.throttlingMechanisms.concurrencyLimits.set('low', lowPriorityLimit);
    }
    
    enforceConcurrencyLimits() {
        const globalLimit = this.throttlingMechanisms.concurrencyLimits.get('global') || this.systemInfo.cpuCount;
        let activeTaskCount = 0;
        
        // Count and potentially suspend active tasks
        for (const [priority, tasks] of Object.entries(this.workloads)) {
            const priorityLimit = this.throttlingMechanisms.concurrencyLimits.get(priority) || tasks.length;
            let priorityActiveCount = 0;
            
            for (const task of tasks) {
                if (task.status === 'running') {
                    if (priorityActiveCount >= priorityLimit || activeTaskCount >= globalLimit) {
                        this.suspendTask(task);
                    } else {
                        priorityActiveCount++;
                        activeTaskCount++;
                    }
                }
            }
        }
    }
    
    suspendIdleTasks() {
        this.workloads.idle.forEach(task => {
            if (task.status === 'running') {
                this.suspendTask(task);
            }
        });
    }
    
    suspendLowPriorityTasks() {
        ['idle', 'low'].forEach(priority => {
            this.workloads[priority].forEach(task => {
                if (task.status === 'running') {
                    this.suspendTask(task);
                }
            });
        });
    }
    
    suspendNormalTasks() {
        ['idle', 'low', 'normal'].forEach(priority => {
            this.workloads[priority].forEach(task => {
                if (task.status === 'running') {
                    this.suspendTask(task);
                }
            });
        });
    }
    
    suspendAllButCritical() {
        ['idle', 'low', 'normal'].forEach(priority => {
            this.workloads[priority].forEach(task => {
                if (task.status === 'running' && !task.critical) {
                    this.suspendTask(task);
                }
            });
        });
    }
    
    suspendTask(task) {
        if (task.status === 'running') {
            task.status = 'suspended';
            task.suspendedAt = Date.now();
            this.state.suspendedTasks.add(task.id);
            
            // Notify task to yield
            if (task.controller && typeof task.controller.suspend === 'function') {
                task.controller.suspend();
            }
            
            console.log(`⏸️ Suspended task: ${task.name} (${task.priority})`);
        }
    }
    
    resumeSuspendedTasks() {
        for (const taskId of this.state.suspendedTasks) {
            this.resumeTask(taskId);
        }
    }
    
    resumeTask(taskId) {
        // Find task across all priority levels
        for (const tasks of Object.values(this.workloads)) {
            const task = tasks.find(t => t.id === taskId);
            if (task && task.status === 'suspended') {
                task.status = 'running';
                task.resumedAt = Date.now();
                this.state.suspendedTasks.delete(taskId);
                
                // Calculate suspension duration
                const suspensionDuration = task.resumedAt - task.suspendedAt;
                task.totalSuspensionTime = (task.totalSuspensionTime || 0) + suspensionDuration;
                
                // Notify task to resume
                if (task.controller && typeof task.controller.resume === 'function') {
                    task.controller.resume();
                }
                
                console.log(`▶️ Resumed task: ${task.name} (suspended for ${suspensionDuration}ms)`);
                break;
            }
        }
    }
    
    setupWorkloadManagement() {
        this.workloadManager = {
            scheduler: null,
            loadBalancer: null,
            priorityQueue: new Map(),
            affinityMap: new Map() // CPU core affinity
        };
        
        if (this.config.multiCoreOptimization) {
            this.setupCoreAffinity();
        }
    }
    
    setupCoreAffinity() {
        // Distribute workloads across CPU cores
        for (let i = 0; i < this.systemInfo.cpuCount; i++) {
            this.workloadManager.affinityMap.set(i, {
                load: 0,
                tasks: [],
                temperature: 25,
                efficiency: 1.0
            });
        }
    }
    
    redistributeWorkload() {
        if (!this.config.multiCoreOptimization) return;
        
        console.log('🔄 Redistributing workload across cores...');
        
        // Find least loaded cores
        const coreLoads = Array.from(this.workloadManager.affinityMap.entries())
            .sort(([, a], [, b]) => a.load - b.load);
        
        let redistributedTasks = 0;
        
        // Move tasks from overloaded to underloaded cores
        for (const [coreId, coreInfo] of coreLoads) {
            if (coreInfo.load > 0.8 && coreInfo.tasks.length > 0) {
                // Find a less loaded core
                const targetCore = coreLoads.find(([id, info]) => info.load < 0.4);
                if (targetCore) {
                    const task = coreInfo.tasks.pop();
                    targetCore[1].tasks.push(task);
                    coreInfo.load -= 0.1;
                    targetCore[1].load += 0.1;
                    redistributedTasks++;
                }
            }
        }
        
        if (redistributedTasks > 0) {
            this.metrics.coreBalancing++;
            console.log(`✅ Redistributed ${redistributedTasks} tasks across cores`);
        }
    }
    
    setupAdaptiveControl() {
        if (!this.config.adaptiveThrottling) return;
        
        this.adaptiveController = {
            learningRate: 0.1,
            predictions: new Map(),
            adjustments: [],
            confidence: 0.5
        };
        
        this.timers.set('adaptiveControl', setInterval(() => {
            this.adaptThrottlingStrategy();
        }, 30000)); // Every 30 seconds
    }
    
    adaptThrottlingStrategy() {
        const recentMeasurements = this.cpuMonitor.measurements.slice(-10);
        if (recentMeasurements.length < 5) return;
        
        const avgUsage = recentMeasurements.reduce((sum, m) => sum + m.usage, 0) / recentMeasurements.length;
        const variance = this.calculateVariance(recentMeasurements.map(m => m.usage));
        
        // Adapt target based on stability
        if (variance < 2 && avgUsage < this.state.targetCpuUsage * 0.8) {
            // Stable and low usage - can increase target
            this.state.targetCpuUsage = Math.min(this.config.maxCpuUsage * 1.2, this.state.targetCpuUsage * 1.05);
            console.log(`📈 Adaptive: Increased CPU target to ${this.state.targetCpuUsage.toFixed(1)}%`);
        } else if (variance > 5 || avgUsage > this.state.targetCpuUsage) {
            // Unstable or high usage - decrease target
            this.state.targetCpuUsage = Math.max(this.config.maxCpuUsage * 0.5, this.state.targetCpuUsage * 0.95);
            console.log(`📉 Adaptive: Decreased CPU target to ${this.state.targetCpuUsage.toFixed(1)}%`);
        }
        
        this.metrics.adaptations++;
    }
    
    calculateVariance(values) {
        const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
        const squaredDiffs = values.map(val => Math.pow(val - mean, 2));
        return squaredDiffs.reduce((sum, diff) => sum + diff, 0) / values.length;
    }
    
    setupThermalManagement() {
        if (!this.config.thermalThrottling) return;
        
        this.thermalManager = {
            temperature: 25,
            threshold: 70,
            critical: 85,
            coolingRate: 0.5,
            heatingRate: 0.3
        };
        
        this.timers.set('thermalManagement', setInterval(() => {
            this.updateThermalState();
            this.handleThermalThrottling();
        }, 5000));
    }
    
    updateThermalState() {
        // Simulate CPU temperature based on usage
        const targetTemp = 25 + (this.state.currentCpuUsage / 100) * 40;
        
        if (this.thermalManager.temperature < targetTemp) {
            this.thermalManager.temperature = Math.min(targetTemp, 
                this.thermalManager.temperature + this.thermalManager.heatingRate);
        } else {
            this.thermalManager.temperature = Math.max(targetTemp,
                this.thermalManager.temperature - this.thermalManager.coolingRate);
        }
    }
    
    handleThermalThrottling() {
        const temp = this.thermalManager.temperature;
        
        if (temp > this.thermalManager.critical && this.state.thermalState !== 'critical') {
            console.log(`🌡️ Critical temperature: ${temp.toFixed(1)}°C - Emergency throttling`);
            this.state.thermalState = 'critical';
            this.state.targetCpuUsage = Math.min(this.state.targetCpuUsage, 2);
            this.metrics.thermalEvents++;
            this.emit('thermalCritical', { temperature: temp });
            
        } else if (temp > this.thermalManager.threshold && this.state.thermalState === 'normal') {
            console.log(`🌡️ High temperature: ${temp.toFixed(1)}°C - Thermal throttling enabled`);
            this.state.thermalState = 'throttling';
            this.state.targetCpuUsage = Math.min(this.state.targetCpuUsage, 3);
            this.metrics.thermalEvents++;
            this.emit('thermalThrottling', { temperature: temp });
            
        } else if (temp < this.thermalManager.threshold - 5 && this.state.thermalState !== 'normal') {
            console.log(`🌡️ Temperature normalized: ${temp.toFixed(1)}°C - Disabling thermal throttling`);
            this.state.thermalState = 'normal';
            this.state.targetCpuUsage = this.config.maxCpuUsage;
            this.emit('thermalNormal', { temperature: temp });
        }
    }
    
    handleHighSystemLoad() {
        // Temporary aggressive throttling during high system load
        const originalTarget = this.state.targetCpuUsage;
        this.state.targetCpuUsage = Math.min(this.state.targetCpuUsage, 2);
        
        console.log(`⚠️ High system load - Temporarily reducing CPU target to ${this.state.targetCpuUsage}%`);
        
        // Restore after 30 seconds
        setTimeout(() => {
            this.state.targetCpuUsage = originalTarget;
            console.log(`✅ System load normalized - Restored CPU target to ${originalTarget}%`);
        }, 30000);
    }
    
    preemptiveThrottle() {
        if (!this.state.isThrottling) {
            console.log('🔮 Preemptive throttling activated based on usage trend');
            this.enableThrottling();
            
            // Schedule review in 10 seconds
            setTimeout(() => {
                if (this.state.currentCpuUsage < this.state.targetCpuUsage * 0.8) {
                    console.log('🔮 Preemptive throttling was successful');
                    this.disableThrottling();
                }
            }, 10000);
        }
    }
    
    // Public API methods
    
    getCpuStatus() {
        return {
            usage: this.state.currentCpuUsage,
            target: this.state.targetCpuUsage,
            isThrottling: this.state.isThrottling,
            throttleLevel: this.state.throttleLevel,
            coreCount: this.systemInfo.cpuCount,
            loadAverage: this.systemInfo.loadAverage,
            thermalState: this.state.thermalState,
            temperature: this.thermalManager?.temperature || 25,
            workloadProfile: this.state.workloadProfile,
            suspendedTasks: this.state.suspendedTasks.size
        };
    }
    
    getCpuMetrics() {
        return {
            ...this.metrics,
            efficiency: this.calculateCpuEfficiency(),
            throttlingRatio: this.calculateThrottlingRatio(),
            thermalEfficiency: this.calculateThermalEfficiency()
        };
    }
    
    calculateCpuEfficiency() {
        const targetUtilization = this.state.targetCpuUsage / 100;
        const actualUtilization = this.state.currentCpuUsage / 100;
        
        if (actualUtilization <= targetUtilization) {
            return 1.0; // Perfect efficiency
        } else {
            return targetUtilization / actualUtilization;
        }
    }
    
    calculateThrottlingRatio() {
        if (this.metrics.throttleEvents === 0) return 0;
        
        const totalRuntime = Date.now() - (this.state.lastMeasurement || Date.now());
        return this.metrics.throttleDuration / totalRuntime;
    }
    
    calculateThermalEfficiency() {
        if (!this.thermalManager) return 1.0;
        
        const temp = this.thermalManager.temperature;
        const maxSafeTemp = this.thermalManager.threshold;
        
        return Math.max(0, 1 - (Math.max(0, temp - maxSafeTemp) / maxSafeTemp));
    }
    
    scheduleTask(task) {
        const taskId = `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const priority = task.priority || 'normal';
        
        const taskWrapper = {
            id: taskId,
            name: task.name || 'unnamed_task',
            priority,
            execute: task.execute,
            cancel: task.cancel,
            critical: task.critical || false,
            status: 'queued',
            createdAt: Date.now(),
            delay: this.throttlingMechanisms.taskDelays.get(priority) || 0,
            totalSuspensionTime: 0
        };
        
        this.workloads[priority].push(taskWrapper);
        this.state.processQueue.set(taskId, taskWrapper);
        
        this.emit('taskScheduled', taskWrapper);
        return taskId;
    }
    
    cancelTask(taskId) {
        const task = this.state.processQueue.get(taskId);
        if (task) {
            // Remove from appropriate workload queue
            const workloadQueue = this.workloads[task.priority];
            const index = workloadQueue.findIndex(t => t.id === taskId);
            if (index !== -1) {
                workloadQueue.splice(index, 1);
            }
            
            this.state.processQueue.delete(taskId);
            this.state.suspendedTasks.delete(taskId);
            
            if (task.cancel) {
                task.cancel();
            }
            
            this.emit('taskCancelled', task);
            return true;
        }
        return false;
    }
    
    setMaxCpuUsage(percentage) {
        this.config.maxCpuUsage = Math.max(1, Math.min(100, percentage));
        this.state.targetCpuUsage = this.config.maxCpuUsage;
        console.log(`🎛️ CPU limit updated to ${percentage}%`);
        this.emit('cpuLimitChanged', { limit: percentage });
    }
    
    enableGameMode() {
        this.state.workloadProfile = 'gaming';
        this.setMaxCpuUsage(2); // Very low CPU usage for gaming
        console.log('🎮 Game mode enabled - CPU throttling optimized for gaming');
        this.emit('gameModeEnabled');
    }
    
    disableGameMode() {
        this.state.workloadProfile = 'balanced';
        this.setMaxCpuUsage(5); // Normal CPU usage
        console.log('🎮 Game mode disabled - CPU throttling restored to normal');
        this.emit('gameModeDisabled');
    }
    
    createCpuSnapshot() {
        return {
            timestamp: Date.now(),
            status: this.getCpuStatus(),
            metrics: this.getCpuMetrics(),
            measurements: [...this.cpuMonitor.measurements]
        };
    }
    
    async shutdown() {
        console.log('🔄 Shutting down CPU Throttle Controller...');
        
        // Disable throttling
        if (this.state.isThrottling) {
            this.disableThrottling();
        }
        
        // Clear all timers
        for (const timer of this.timers.values()) {
            clearInterval(timer);
        }
        this.timers.clear();
        
        // Cancel all pending tasks
        for (const taskId of this.state.processQueue.keys()) {
            this.cancelTask(taskId);
        }
        
        this.emit('shutdown');
        console.log('✅ CPU Throttle Controller shutdown complete');
    }
}

module.exports = CPUThrottleController;