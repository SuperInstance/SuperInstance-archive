/**
 * Advanced Resource Manager - Minimal usage with maximum efficiency
 */

const os = require('os');
const process = require('process');
const { EventEmitter } = require('events');

class ResourceManager extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.config = {
            maxMemoryUsage: options.maxMemoryUsage || 100 * 1024 * 1024, // 100MB
            maxCpuUsage: options.maxCpuUsage || 5, // 5% CPU
            batteryOptimization: options.batteryOptimization ?? true,
            gameMode: options.gameMode ?? false,
            throttleInterval: options.throttleInterval || 1000,
            ...options
        };
        
        this.metrics = {
            memoryUsage: 0,
            cpuUsage: 0,
            batteryLevel: 100,
            networkLatency: 0,
            gameDetected: false,
            activeFeatures: new Set(),
            startTime: Date.now()
        };
        
        this.throttles = new Map();
        this.scheduledTasks = new Map();
        this.resourceLimits = new Map();
        
        this.init();
    }
    
    init() {
        this.startResourceMonitoring();
        this.setupCpuThrottling();
        this.setupMemoryManagement();
        this.setupBatteryOptimization();
        this.setupGameDetection();
        
        // Graceful shutdown
        process.on('SIGINT', () => this.shutdown());
        process.on('SIGTERM', () => this.shutdown());
    }
    
    startResourceMonitoring() {
        const monitor = () => {
            this.updateMetrics();
            this.enforceResourceLimits();
            this.optimizePerformance();
            
            // Emit metrics update
            this.emit('metricsUpdated', this.metrics);
            
            // Schedule next monitoring cycle
            setTimeout(monitor, this.config.throttleInterval);
        };
        
        monitor();
    }
    
    updateMetrics() {
        // Memory usage
        const memUsage = process.memoryUsage();
        this.metrics.memoryUsage = memUsage.heapUsed;
        
        // CPU usage (simplified estimation)
        const cpuUsage = process.cpuUsage();
        this.metrics.cpuUsage = this.calculateCpuPercentage(cpuUsage);
        
        // Battery status (if available)
        this.updateBatteryStatus();
        
        // Game detection
        this.detectRunningGames();
    }
    
    calculateCpuPercentage(cpuUsage) {
        // Simplified CPU percentage calculation
        const totalTime = cpuUsage.user + cpuUsage.system;
        const elapsedTime = Date.now() - this.metrics.startTime;
        return Math.min((totalTime / (elapsedTime * 1000)) * 100, 100);
    }
    
    updateBatteryStatus() {
        // Battery optimization logic
        if (this.config.batteryOptimization) {
            // Simulate battery level detection
            // In real implementation, would use native APIs
            this.metrics.batteryLevel = Math.max(
                0, 
                100 - ((Date.now() - this.metrics.startTime) / 3600000) * 2
            );
        }
    }
    
    detectRunningGames() {
        // Game detection logic
        const gameProcesses = [
            'steam.exe', 'discord.exe', 'obs64.exe', 'twitch.exe',
            'csgo.exe', 'valorant.exe', 'lol.exe', 'dota2.exe',
            'wow.exe', 'minecraft.exe', 'fortnite.exe'
        ];
        
        // Simplified detection (in production would use actual process monitoring)
        this.metrics.gameDetected = Math.random() < 0.1; // 10% chance for demo
        
        if (this.metrics.gameDetected && !this.config.gameMode) {
            this.enableGameMode();
        } else if (!this.metrics.gameDetected && this.config.gameMode) {
            this.disableGameMode();
        }
    }
    
    enableGameMode() {
        console.log('🎮 Game detected - Enabling game-friendly mode');
        this.config.gameMode = true;
        
        // Reduce background activity
        this.config.throttleInterval = 5000; // Slower monitoring
        this.config.maxCpuUsage = 2; // Lower CPU limit
        
        // Pause non-essential features
        this.pauseNonEssentialFeatures();
        
        this.emit('gameModeEnabled');
    }
    
    disableGameMode() {
        console.log('🎮 Game closed - Disabling game mode');
        this.config.gameMode = false;
        
        // Restore normal activity
        this.config.throttleInterval = 1000;
        this.config.maxCpuUsage = 5;
        
        // Resume features
        this.resumeFeatures();
        
        this.emit('gameModeDisabled');
    }
    
    setupCpuThrottling() {
        this.cpuThrottle = {
            isThrottled: false,
            throttleLevel: 0,
            lastCheck: Date.now()
        };
    }
    
    setupMemoryManagement() {
        this.memoryManager = {
            cache: new Map(),
            gcInterval: setInterval(() => {
                if (this.metrics.memoryUsage > this.config.maxMemoryUsage * 0.8) {
                    this.performGarbageCollection();
                }
            }, 30000), // Check every 30 seconds
            
            compressionEnabled: true,
            cacheLimit: 50 * 1024 * 1024 // 50MB cache limit
        };
    }
    
    performGarbageCollection() {
        console.log('🧹 Performing memory cleanup');
        
        // Clear caches
        this.memoryManager.cache.clear();
        
        // Force garbage collection if available
        if (global.gc) {
            global.gc();
        }
        
        // Clear throttles
        this.throttles.clear();
        
        this.emit('memoryCleanup', {
            beforeMemory: this.metrics.memoryUsage,
            afterMemory: process.memoryUsage().heapUsed
        });
    }
    
    setupBatteryOptimization() {
        if (!this.config.batteryOptimization) return;
        
        this.batteryOptimizer = {
            lowPowerMode: false,
            checkInterval: setInterval(() => {
                if (this.metrics.batteryLevel < 20 && !this.batteryOptimizer.lowPowerMode) {
                    this.enableLowPowerMode();
                } else if (this.metrics.batteryLevel > 50 && this.batteryOptimizer.lowPowerMode) {
                    this.disableLowPowerMode();
                }
            }, 60000) // Check every minute
        };
    }
    
    enableLowPowerMode() {
        console.log('🔋 Low battery detected - Enabling power saving mode');
        this.batteryOptimizer.lowPowerMode = true;
        
        // Reduce resource limits
        this.config.maxCpuUsage = 2;
        this.config.throttleInterval = 10000;
        
        // Disable non-essential features
        this.pauseNonEssentialFeatures();
        
        this.emit('lowPowerModeEnabled');
    }
    
    disableLowPowerMode() {
        console.log('🔋 Battery level restored - Disabling power saving mode');
        this.batteryOptimizer.lowPowerMode = false;
        
        // Restore normal limits
        this.config.maxCpuUsage = 5;
        this.config.throttleInterval = 1000;
        
        // Resume features
        this.resumeFeatures();
        
        this.emit('lowPowerModeDisabled');
    }
    
    pauseNonEssentialFeatures() {
        const nonEssential = [
            'backgroundSync', 'analytics', 'telemetry',
            'autoUpdate', 'notifications', 'animations'
        ];
        
        nonEssential.forEach(feature => {
            if (this.metrics.activeFeatures.has(feature)) {
                this.metrics.activeFeatures.delete(feature);
                this.emit('featurePaused', feature);
            }
        });
    }
    
    resumeFeatures() {
        const essential = [
            'coreSync', 'errorReporting', 'security'
        ];
        
        essential.forEach(feature => {
            this.metrics.activeFeatures.add(feature);
            this.emit('featureResumed', feature);
        });
    }
    
    enforceResourceLimits() {
        // CPU throttling
        if (this.metrics.cpuUsage > this.config.maxCpuUsage) {
            this.applyCpuThrottling();
        }
        
        // Memory limits
        if (this.metrics.memoryUsage > this.config.maxMemoryUsage) {
            this.applyMemoryThrottling();
        }
    }
    
    applyCpuThrottling() {
        if (!this.cpuThrottle.isThrottled) {
            console.log('⚠️ CPU usage exceeded limit - Applying throttling');
            this.cpuThrottle.isThrottled = true;
            this.cpuThrottle.throttleLevel = Math.min(this.cpuThrottle.throttleLevel + 1, 5);
            
            // Increase intervals
            this.config.throttleInterval *= 1.5;
            
            this.emit('cpuThrottled', this.cpuThrottle.throttleLevel);
        }
    }
    
    applyMemoryThrottling() {
        console.log('⚠️ Memory usage exceeded limit - Applying throttling');
        
        // Immediate cleanup
        this.performGarbageCollection();
        
        // Reduce cache sizes
        if (this.memoryManager.cache.size > 100) {
            const keysToDelete = Array.from(this.memoryManager.cache.keys()).slice(0, 50);
            keysToDelete.forEach(key => this.memoryManager.cache.delete(key));
        }
        
        this.emit('memoryThrottled');
    }
    
    optimizePerformance() {
        // Performance optimizations based on current state
        if (this.config.gameMode) {
            this.optimizeForGaming();
        } else if (this.batteryOptimizer?.lowPowerMode) {
            this.optimizeForBattery();
        } else {
            this.optimizeForNormal();
        }
    }
    
    optimizeForGaming() {
        // Gaming optimizations
        process.nextTick(() => {
            // Yield CPU to games
            setTimeout(() => {}, 10);
        });
    }
    
    optimizeForBattery() {
        // Battery optimizations
        // Reduce background processing
        this.config.throttleInterval = Math.max(this.config.throttleInterval, 15000);
    }
    
    optimizeForNormal() {
        // Normal optimizations
        if (this.cpuThrottle.isThrottled && this.metrics.cpuUsage < this.config.maxCpuUsage * 0.7) {
            this.cpuThrottle.isThrottled = false;
            this.cpuThrottle.throttleLevel = Math.max(this.cpuThrottle.throttleLevel - 1, 0);
            this.config.throttleInterval = 1000;
            
            this.emit('cpuThrottleReleased');
        }
    }
    
    // Public API methods
    
    getMetrics() {
        return { ...this.metrics };
    }
    
    getResourceUsage() {
        return {
            memory: {
                used: this.metrics.memoryUsage,
                limit: this.config.maxMemoryUsage,
                percentage: (this.metrics.memoryUsage / this.config.maxMemoryUsage) * 100
            },
            cpu: {
                usage: this.metrics.cpuUsage,
                limit: this.config.maxCpuUsage,
                throttled: this.cpuThrottle.isThrottled
            },
            battery: {
                level: this.metrics.batteryLevel,
                lowPowerMode: this.batteryOptimizer?.lowPowerMode || false
            },
            game: {
                detected: this.metrics.gameDetected,
                gameMode: this.config.gameMode
            }
        };
    }
    
    setResourceLimit(resource, limit) {
        switch (resource) {
            case 'memory':
                this.config.maxMemoryUsage = limit;
                break;
            case 'cpu':
                this.config.maxCpuUsage = limit;
                break;
            default:
                console.warn(`Unknown resource type: ${resource}`);
        }
    }
    
    enableFeature(feature) {
        if (!this.metrics.activeFeatures.has(feature)) {
            this.metrics.activeFeatures.add(feature);
            this.emit('featureEnabled', feature);
            return true;
        }
        return false;
    }
    
    disableFeature(feature) {
        if (this.metrics.activeFeatures.has(feature)) {
            this.metrics.activeFeatures.delete(feature);
            this.emit('featureDisabled', feature);
            return true;
        }
        return false;
    }
    
    isFeatureEnabled(feature) {
        return this.metrics.activeFeatures.has(feature);
    }
    
    async shutdown() {
        console.log('🔄 Shutting down Resource Manager...');
        
        // Clear all intervals
        if (this.memoryManager?.gcInterval) {
            clearInterval(this.memoryManager.gcInterval);
        }
        
        if (this.batteryOptimizer?.checkInterval) {
            clearInterval(this.batteryOptimizer.checkInterval);
        }
        
        // Clean up resources
        this.throttles.clear();
        this.scheduledTasks.clear();
        this.resourceLimits.clear();
        
        // Final garbage collection
        this.performGarbageCollection();
        
        this.emit('shutdown');
        console.log('✅ Resource Manager shutdown complete');
    }
}

module.exports = ResourceManager;