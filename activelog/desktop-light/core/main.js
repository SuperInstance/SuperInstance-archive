/**
 * ActiveLog Desktop Light - Main Application Entry Point
 * Ultra-lightweight desktop client with game-friendly performance
 */

const ResourceManager = require('./resource-manager');
const BackgroundService = require('./background-service');
const FeatureLoader = require('./feature-loader');
const StreamOptimizer = require('./stream-optimizer');

class ActiveLogDesktopLight {
    constructor(options = {}) {
        this.config = {
            mode: options.mode || 'minimal', // minimal, gaming, stealth
            autoStart: options.autoStart ?? true,
            systemTray: options.systemTray ?? true,
            notifications: options.notifications ?? false,
            telemetry: options.telemetry ?? false,
            updateCheck: options.updateCheck ?? false,
            port: options.port || 8381,
            ...options
        };
        
        this.components = new Map();
        this.state = {
            initialized: false,
            running: false,
            hidden: false,
            resourceUsage: {},
            lastActivity: Date.now(),
            sessionId: this.generateSessionId()
        };
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing ActiveLog Desktop Light');
        console.log(`📊 Mode: ${this.config.mode}`);
        console.log(`🆔 Session: ${this.state.sessionId}`);
        
        try {
            // Initialize core components
            await this.initializeResourceManager();
            await this.initializeBackgroundService();
            await this.initializeFeatureLoader();
            await this.initializeStreamOptimizer();
            
            // Setup inter-component communication
            this.setupComponentIntegration();
            
            // Setup application lifecycle
            this.setupLifecycle();
            
            // Configure mode-specific settings
            this.applyModeConfiguration();
            
            this.state.initialized = true;
            console.log('✅ ActiveLog Desktop Light initialized successfully');
            
            if (this.config.autoStart) {
                await this.start();
            }
            
        } catch (error) {
            console.error('❌ Failed to initialize application:', error);
            process.exit(1);
        }
    }
    
    async initializeResourceManager() {
        console.log('🔧 Initializing Resource Manager...');
        
        const resourceConfig = {
            maxMemoryUsage: this.config.mode === 'minimal' ? 50 * 1024 * 1024 : 100 * 1024 * 1024,
            maxCpuUsage: this.config.mode === 'gaming' ? 2 : 5,
            batteryOptimization: true,
            gameMode: this.config.mode === 'gaming'
        };
        
        const resourceManager = new ResourceManager(resourceConfig);
        this.components.set('resourceManager', resourceManager);
        
        // Monitor resource changes
        resourceManager.on('gameModeEnabled', () => {
            console.log('🎮 Game mode activated - Reducing resource usage');
            this.onGameModeChange(true);
        });
        
        resourceManager.on('gameModeDisabled', () => {
            console.log('🎮 Game mode deactivated - Restoring normal operation');
            this.onGameModeChange(false);
        });
        
        resourceManager.on('lowPowerModeEnabled', () => {
            console.log('🔋 Low power mode activated');
            this.onPowerModeChange(true);
        });
        
        resourceManager.on('memoryCleanup', (data) => {
            console.log(`🧹 Memory cleanup: ${Math.round(data.beforeMemory / 1024 / 1024)}MB → ${Math.round(data.afterMemory / 1024 / 1024)}MB`);
        });
    }
    
    async initializeBackgroundService() {
        console.log('🔧 Initializing Background Service...');
        
        const backgroundConfig = {
            minimalMode: this.config.mode === 'minimal',
            stealthMode: this.config.mode === 'stealth',
            backgroundPriority: 'low',
            maxBackgroundTasks: this.config.mode === 'minimal' ? 2 : 3
        };
        
        const backgroundService = new BackgroundService(backgroundConfig);
        this.components.set('backgroundService', backgroundService);
        
        // Schedule essential tasks
        this.scheduleEssentialTasks();
    }
    
    async initializeFeatureLoader() {
        console.log('🔧 Initializing Feature Loader...');
        
        const featureConfig = {
            lazyLoading: true,
            preloadCritical: true,
            cacheModules: this.config.mode !== 'minimal',
            featureDirectory: './shared/components'
        };
        
        const featureLoader = new FeatureLoader(featureConfig);
        this.components.set('featureLoader', featureLoader);
        
        // Load mode-specific features
        await this.loadModeFeatures();
    }
    
    async initializeStreamOptimizer() {
        console.log('🔧 Initializing Stream Optimizer...');
        
        const streamConfig = {
            compression: this.config.mode !== 'gaming',
            adaptiveBitrate: true,
            bufferSize: this.config.mode === 'minimal' ? 32 * 1024 : 64 * 1024,
            networkQualityThreshold: 0.8
        };
        
        const streamOptimizer = new StreamOptimizer(streamConfig);
        this.components.set('streamOptimizer', streamOptimizer);
    }
    
    setupComponentIntegration() {
        console.log('🔗 Setting up component integration...');
        
        const resourceManager = this.components.get('resourceManager');
        const backgroundService = this.components.get('backgroundService');
        const featureLoader = this.components.get('featureLoader');
        const streamOptimizer = this.components.get('streamOptimizer');
        
        // Resource manager → Background service
        resourceManager.on('metricsUpdated', (metrics) => {
            this.state.resourceUsage = metrics;
            
            // Adjust background service based on resources
            if (metrics.memoryUsage > resourceManager.config.maxMemoryUsage * 0.8) {
                backgroundService.pause();
                setTimeout(() => backgroundService.resume(), 30000);
            }
        });
        
        // Feature loader → Resource manager
        featureLoader.on('featureLoaded', (data) => {
            resourceManager.enableFeature(data.name);
        });
        
        featureLoader.on('featureUnloaded', (data) => {
            resourceManager.disableFeature(data.name);
        });
        
        // Stream optimizer → Resource manager
        streamOptimizer.on('streamsOptimized', () => {
            // Trigger garbage collection after stream optimization
            if (global.gc) {
                global.gc();
            }
        });
    }
    
    setupLifecycle() {
        // Graceful shutdown handlers
        const shutdown = async () => {
            console.log('🔄 Shutting down application...');
            await this.shutdown();
        };
        
        process.on('SIGINT', shutdown);
        process.on('SIGTERM', shutdown);
        process.on('exit', () => {
            console.log('👋 ActiveLog Desktop Light exited');
        });
        
        // Uncaught exception handler
        process.on('uncaughtException', (error) => {
            console.error('💥 Uncaught exception:', error);
            this.handleCriticalError(error);
        });
        
        // Unhandled rejection handler
        process.on('unhandledRejection', (reason, promise) => {
            console.error('💥 Unhandled rejection at:', promise, 'reason:', reason);
            this.handleCriticalError(new Error(`Unhandled rejection: ${reason}`));
        });
    }
    
    applyModeConfiguration() {
        console.log(`⚙️ Applying ${this.config.mode} mode configuration...`);
        
        switch (this.config.mode) {
            case 'minimal':
                this.applyMinimalMode();
                break;
            case 'gaming':
                this.applyGamingMode();
                break;
            case 'stealth':
                this.applyStealthMode();
                break;
            default:
                console.warn(`Unknown mode: ${this.config.mode}`);
        }
    }
    
    applyMinimalMode() {
        console.log('🎯 Applying minimal mode settings');
        
        // Disable non-essential features
        this.config.notifications = false;
        this.config.telemetry = false;
        this.config.updateCheck = false;
        
        // Reduce resource usage
        const resourceManager = this.components.get('resourceManager');
        resourceManager.setResourceLimit('memory', 30 * 1024 * 1024); // 30MB
        resourceManager.setResourceLimit('cpu', 3); // 3%
        
        // Minimal UI
        this.hideFromTaskbar();
    }
    
    applyGamingMode() {
        console.log('🎮 Applying gaming mode settings');
        
        // Ultra-low resource usage
        const resourceManager = this.components.get('resourceManager');
        resourceManager.setResourceLimit('memory', 25 * 1024 * 1024); // 25MB
        resourceManager.setResourceLimit('cpu', 1); // 1%
        
        // Low process priority
        try {
            process.priority = 19; // Lowest priority
        } catch (error) {
            console.warn('Could not set low priority:', error.message);
        }
        
        // Disable background activities
        const backgroundService = this.components.get('backgroundService');
        backgroundService.pause();
        
        // No visible elements
        this.hideFromTaskbar();
        this.hideTrayIcon();
    }
    
    applyStealthMode() {
        console.log('👻 Applying stealth mode settings');
        
        // Completely hidden operation
        this.hideFromTaskbar();
        this.hideTrayIcon();
        
        // Minimal logging
        console.log = () => {}; // Disable console output
        console.warn = () => {};
        console.error = () => {};
        
        // Encrypted communication
        this.config.encrypted = true;
        
        // Random delays to avoid detection
        this.enableAntiDetection();
    }
    
    async loadModeFeatures() {
        const featureLoader = this.components.get('featureLoader');
        const essentialFeatures = ['core', 'security', 'network'];
        
        let modeFeatures = [];
        switch (this.config.mode) {
            case 'minimal':
                modeFeatures = ['sync-minimal'];
                break;
            case 'gaming':
                modeFeatures = ['game-detector', 'performance-monitor'];
                break;
            case 'stealth':
                modeFeatures = ['encryption', 'obfuscation'];
                break;
        }
        
        try {
            await featureLoader.preloadFeatures([...essentialFeatures, ...modeFeatures]);
        } catch (error) {
            console.warn('Some features failed to load:', error.message);
        }
    }
    
    scheduleEssentialTasks() {
        const backgroundService = this.components.get('backgroundService');
        
        // Health check task
        backgroundService.scheduleTask({
            name: 'health_check',
            category: 'monitoring',
            execute: async () => {
                const health = await this.performHealthCheck();
                return { healthy: health, timestamp: Date.now() };
            },
            retryable: true
        }, 'normal');
        
        // Resource cleanup task (low priority)
        backgroundService.scheduleTask({
            name: 'resource_cleanup',
            category: 'maintenance',
            execute: async () => {
                await this.performResourceCleanup();
                return { cleaned: true, timestamp: Date.now() };
            },
            retryable: false
        }, 'low');
        
        // Connectivity check task (idle priority)
        if (this.config.mode !== 'stealth') {
            backgroundService.scheduleTask({
                name: 'connectivity_check',
                category: 'network',
                execute: async () => {
                    const connected = await this.checkConnectivity();
                    return { connected, timestamp: Date.now() };
                },
                retryable: true
            }, 'idle');
        }
    }
    
    async start() {
        if (this.state.running) {
            console.log('Application already running');
            return;
        }
        
        console.log('▶️ Starting ActiveLog Desktop Light...');
        
        try {
            // Start all components
            const backgroundService = this.components.get('backgroundService');
            // Components start automatically in their constructors
            
            this.state.running = true;
            this.state.lastActivity = Date.now();
            
            console.log('✅ Application started successfully');
            console.log(`📊 Memory usage: ${Math.round(process.memoryUsage().heapUsed / 1024 / 1024)}MB`);
            console.log(`⚡ CPU usage: ~${this.state.resourceUsage.cpuUsage || 0}%`);
            
            // Start activity monitoring
            this.startActivityMonitoring();
            
        } catch (error) {
            console.error('❌ Failed to start application:', error);
            throw error;
        }
    }
    
    startActivityMonitoring() {
        setInterval(() => {
            const resourceManager = this.components.get('resourceManager');
            const backgroundService = this.components.get('backgroundService');
            const streamOptimizer = this.components.get('streamOptimizer');
            
            const status = {
                memory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
                resources: resourceManager.getResourceUsage(),
                background: backgroundService.getStatus(),
                streams: streamOptimizer.getGlobalStats(),
                uptime: Date.now() - this.state.lastActivity
            };
            
            // Log status periodically (only in non-stealth mode)
            if (this.config.mode !== 'stealth' && status.uptime % 300000 === 0) {
                console.log(`📊 Status: ${status.memory}MB RAM, ${status.resources.cpu.usage.toFixed(1)}% CPU, ${status.background.activeTasks} tasks, ${status.streams.activeStreams} streams`);
            }
            
        }, 60000); // Every minute
    }
    
    onGameModeChange(enabled) {
        const backgroundService = this.components.get('backgroundService');
        const streamOptimizer = this.components.get('streamOptimizer');
        
        if (enabled) {
            // Pause non-essential operations
            backgroundService.pause();
            
            // Reduce stream quality
            streamOptimizer.state.networkQuality = 0.3;
        } else {
            // Resume operations
            setTimeout(() => {
                backgroundService.resume();
            }, 5000); // Wait 5 seconds after game closes
        }
    }
    
    onPowerModeChange(lowPower) {
        const featureLoader = this.components.get('featureLoader');
        
        if (lowPower) {
            // Unload non-essential features
            const nonEssential = ['analytics', 'telemetry', 'animations'];
            nonEssential.forEach(feature => {
                if (featureLoader.isLoaded(feature)) {
                    featureLoader.unloadFeature(feature);
                }
            });
        }
    }
    
    async performHealthCheck() {
        try {
            const resourceManager = this.components.get('resourceManager');
            const usage = resourceManager.getResourceUsage();
            
            // Check if within resource limits
            if (usage.memory.percentage > 90 || usage.cpu.usage > 10) {
                return false;
            }
            
            // Check component health
            const components = Array.from(this.components.values());
            for (const component of components) {
                if (component.getStatus && !component.getStatus().healthy) {
                    return false;
                }
            }
            
            return true;
            
        } catch (error) {
            console.error('Health check failed:', error.message);
            return false;
        }
    }
    
    async performResourceCleanup() {
        try {
            // Trigger garbage collection
            if (global.gc) {
                global.gc();
            }
            
            // Clean component caches
            const featureLoader = this.components.get('featureLoader');
            featureLoader.cleanupUnusedFeatures();
            
            // Clean stream optimizer caches
            const streamOptimizer = this.components.get('streamOptimizer');
            streamOptimizer.compressionCache.clear();
            
            console.log('🧹 Resource cleanup completed');
            
        } catch (error) {
            console.error('Resource cleanup failed:', error.message);
        }
    }
    
    async checkConnectivity() {
        try {
            // Simple connectivity check
            const dns = require('dns');
            
            return new Promise((resolve) => {
                dns.resolve('google.com', (err) => {
                    resolve(!err);
                });
            });
            
        } catch (error) {
            return false;
        }
    }
    
    hideFromTaskbar() {
        // Platform-specific implementation would go here
        console.log('👻 Hiding from taskbar');
    }
    
    hideTrayIcon() {
        // Platform-specific implementation would go here
        console.log('👻 Hiding tray icon');
    }
    
    enableAntiDetection() {
        // Add random delays to operations
        const originalScheduleTask = this.components.get('backgroundService').scheduleTask;
        
        this.components.get('backgroundService').scheduleTask = function(task, priority, delay = 0) {
            const randomDelay = delay + Math.random() * 5000; // 0-5 second random delay
            return originalScheduleTask.call(this, task, priority, randomDelay);
        };
        
        console.log('🔒 Anti-detection measures enabled');
    }
    
    handleCriticalError(error) {
        console.error('💥 Critical error occurred:', error);
        
        // Try to save state and shutdown gracefully
        this.emergencyShutdown().catch(() => {
            process.exit(1);
        });
    }
    
    async emergencyShutdown() {
        console.log('🚨 Emergency shutdown initiated...');
        
        try {
            // Force shutdown all components
            for (const [name, component] of this.components) {
                if (component.shutdown) {
                    await Promise.race([
                        component.shutdown(),
                        new Promise(resolve => setTimeout(resolve, 2000)) // 2 second timeout
                    ]);
                }
            }
            
            process.exit(0);
            
        } catch (error) {
            console.error('Emergency shutdown failed:', error.message);
            process.exit(1);
        }
    }
    
    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    // Public API methods
    
    getStatus() {
        return {
            initialized: this.state.initialized,
            running: this.state.running,
            mode: this.config.mode,
            sessionId: this.state.sessionId,
            uptime: Date.now() - this.state.lastActivity,
            memory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
            components: Array.from(this.components.keys()),
            resourceUsage: this.state.resourceUsage
        };
    }
    
    async pause() {
        console.log('⏸️ Pausing application...');
        
        const backgroundService = this.components.get('backgroundService');
        backgroundService.pause();
        
        // Pause other components as needed
    }
    
    async resume() {
        console.log('▶️ Resuming application...');
        
        const backgroundService = this.components.get('backgroundService');
        backgroundService.resume();
    }
    
    async hide() {
        console.log('👻 Hiding application...');
        
        this.state.hidden = true;
        this.hideFromTaskbar();
        this.hideTrayIcon();
        
        // Reduce activity to minimum
        const backgroundService = this.components.get('backgroundService');
        backgroundService.hide();
    }
    
    async show() {
        console.log('👁️ Showing application...');
        
        this.state.hidden = false;
        
        const backgroundService = this.components.get('backgroundService');
        backgroundService.show();
    }
    
    async shutdown() {
        if (!this.state.running) {
            return;
        }
        
        console.log('🔄 Shutting down ActiveLog Desktop Light...');
        this.state.running = false;
        
        try {
            // Shutdown components in reverse order
            const components = ['streamOptimizer', 'featureLoader', 'backgroundService', 'resourceManager'];
            
            for (const componentName of components) {
                const component = this.components.get(componentName);
                if (component && component.shutdown) {
                    console.log(`🔄 Shutting down ${componentName}...`);
                    await component.shutdown();
                }
            }
            
            this.components.clear();
            
            console.log('✅ Shutdown complete');
            
        } catch (error) {
            console.error('❌ Error during shutdown:', error.message);
        }
    }
}

// Export for use as module or run directly
module.exports = ActiveLogDesktopLight;

if (require.main === module) {
    // Parse command line arguments
    const args = process.argv.slice(2);
    const config = {};
    
    args.forEach(arg => {
        if (arg.startsWith('--mode=')) {
            config.mode = arg.split('=')[1];
        } else if (arg === '--no-autostart') {
            config.autoStart = false;
        } else if (arg === '--stealth') {
            config.mode = 'stealth';
        } else if (arg === '--gaming') {
            config.mode = 'gaming';
        } else if (arg === '--minimal') {
            config.mode = 'minimal';
        }
    });
    
    // Create and run application
    const app = new ActiveLogDesktopLight(config);
    
    console.log('🌟 ActiveLog Desktop Light started');
    console.log('💡 Use Ctrl+C to exit gracefully');
}