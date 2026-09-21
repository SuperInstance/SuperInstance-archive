/**
 * Modular Architecture Manager - Dynamic module loading and plugin system
 */

const { EventEmitter } = require('events');
const path = require('path');
const fs = require('fs').promises;

class ModuleManager extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.config = {
            modulesPath: options.modulesPath || path.join(__dirname, '../modules'),
            pluginsPath: options.pluginsPath || path.join(__dirname, '../plugins'),
            enableHotReload: options.enableHotReload ?? true,
            enableSandboxing: options.enableSandboxing ?? true,
            maxModuleMemory: options.maxModuleMemory || 50 * 1024 * 1024, // 50MB per module
            moduleTimeout: options.moduleTimeout || 30000,
            dependencyResolution: options.dependencyResolution ?? true,
            versionControl: options.versionControl ?? true,
            ...options
        };
        
        this.state = {
            loadedModules: new Map(),
            activePlugins: new Map(),
            moduleRegistry: new Map(),
            dependencies: new Map(),
            loadOrder: [],
            moduleStates: new Map(),
            sandboxes: new Map(),
            hotReloadWatchers: new Map(),
            moduleMetrics: new Map()
        };
        
        this.lifecycle = {
            hooks: new Map(),
            middleware: new Map(),
            interceptors: new Map(),
            validators: new Map()
        };
        
        this.api = {
            registry: new Map(),
            endpoints: new Map(),
            schemas: new Map(),
            permissions: new Map()
        };
        
        this.timers = new Map();
        this.watchers = new Set();
        
        this.init();
    }
    
    init() {
        this.setupModuleRegistry();
        this.setupLifecycleHooks();
        this.setupAPI();
        this.setupHotReload();
        this.setupSandboxing();
        this.loadCoreModules();
        
        console.log('🧩 Module Manager initialized');
    }
    
    setupModuleRegistry() {
        this.registry = {
            modules: new Map(),
            plugins: new Map(),
            dependencies: new Map(),
            versions: new Map(),
            metadata: new Map()
        };
        
        // Built-in module types
        this.moduleTypes = new Map([
            ['core', { priority: 1, autoload: true, required: true }],
            ['feature', { priority: 2, autoload: false, required: false }],
            ['plugin', { priority: 3, autoload: false, required: false }],
            ['integration', { priority: 4, autoload: false, required: false }],
            ['extension', { priority: 5, autoload: false, required: false }]
        ]);
    }
    
    setupLifecycleHooks() {
        // Define standard lifecycle hooks
        const standardHooks = [
            'beforeLoad', 'afterLoad',
            'beforeUnload', 'afterUnload',
            'beforeStart', 'afterStart',
            'beforeStop', 'afterStop',
            'onError', 'onUpdate'
        ];
        
        standardHooks.forEach(hook => {
            this.lifecycle.hooks.set(hook, new Set());
        });
        
        // Register core lifecycle handlers
        this.registerHook('beforeLoad', this.validateModule.bind(this));
        this.registerHook('afterLoad', this.registerModuleAPI.bind(this));
        this.registerHook('beforeUnload', this.cleanupModule.bind(this));
        this.registerHook('onError', this.handleModuleError.bind(this));
    }
    
    setupAPI() {
        this.apiManager = {
            routes: new Map(),
            middleware: [],
            validators: new Map(),
            transformers: new Map(),
            rateLimit: new Map()
        };
    }
    
    setupHotReload() {
        if (!this.config.enableHotReload) return;
        
        this.hotReloadManager = {
            watchedFiles: new Set(),
            debounceTime: 1000,
            pendingReloads: new Map(),
            reloadHistory: []
        };
        
        console.log('🔥 Hot reload enabled');
    }
    
    setupSandboxing() {
        if (!this.config.enableSandboxing) return;
        
        this.sandboxManager = {
            contexts: new Map(),
            restrictions: new Map(),
            resourceLimits: new Map(),
            permissions: new Map()
        };
        
        console.log('🏜️ Module sandboxing enabled');
    }
    
    async loadCoreModules() {
        console.log('📦 Loading core modules...');
        
        const coreModules = [
            'logger',
            'config',
            'events',
            'metrics',
            'security'
        ];
        
        for (const moduleName of coreModules) {
            try {
                await this.loadModule(moduleName, 'core');
            } catch (error) {
                console.error(`Failed to load core module ${moduleName}:`, error.message);
                // Core modules are critical - could throw here
            }
        }
        
        console.log('✅ Core modules loaded');
    }
    
    async discoverModules() {
        console.log('🔍 Discovering modules...');
        
        const discovered = {
            modules: [],
            plugins: [],
            errors: []
        };
        
        try {
            // Discover modules
            const moduleFiles = await this.scanDirectory(this.config.modulesPath);
            for (const file of moduleFiles) {
                try {
                    const module = await this.analyzeModule(file);
                    discovered.modules.push(module);
                } catch (error) {
                    discovered.errors.push({ file, error: error.message });
                }
            }
            
            // Discover plugins
            const pluginFiles = await this.scanDirectory(this.config.pluginsPath);
            for (const file of pluginFiles) {
                try {
                    const plugin = await this.analyzePlugin(file);
                    discovered.plugins.push(plugin);
                } catch (error) {
                    discovered.errors.push({ file, error: error.message });
                }
            }
            
        } catch (error) {
            console.error('Module discovery failed:', error.message);
        }
        
        console.log(`📊 Discovery complete: ${discovered.modules.length} modules, ${discovered.plugins.length} plugins`);
        return discovered;
    }
    
    async scanDirectory(dirPath) {
        try {
            const entries = await fs.readdir(dirPath, { withFileTypes: true });
            const files = [];
            
            for (const entry of entries) {
                const fullPath = path.join(dirPath, entry.name);
                
                if (entry.isDirectory()) {
                    // Look for package.json or index.js in subdirectories
                    const subFiles = await this.scanModuleDirectory(fullPath);
                    files.push(...subFiles);
                } else if (entry.name.endsWith('.js') || entry.name === 'package.json') {
                    files.push(fullPath);
                }
            }
            
            return files;
        } catch (error) {
            console.warn(`Could not scan directory ${dirPath}:`, error.message);
            return [];
        }
    }
    
    async scanModuleDirectory(dirPath) {
        const files = [];
        const packagePath = path.join(dirPath, 'package.json');
        const indexPath = path.join(dirPath, 'index.js');
        
        try {
            await fs.access(packagePath);
            files.push(packagePath);
        } catch {}
        
        try {
            await fs.access(indexPath);
            files.push(indexPath);
        } catch {}
        
        return files;
    }
    
    async analyzeModule(filePath) {
        const module = {
            path: filePath,
            name: path.basename(path.dirname(filePath)),
            type: 'module',
            manifest: null,
            dependencies: [],
            version: '1.0.0',
            metadata: {}
        };
        
        if (filePath.endsWith('package.json')) {
            const content = await fs.readFile(filePath, 'utf8');
            const packageJson = JSON.parse(content);
            
            module.name = packageJson.name || module.name;
            module.version = packageJson.version || module.version;
            module.dependencies = Object.keys(packageJson.dependencies || {});
            module.manifest = packageJson;
            module.metadata = packageJson.activelogModule || {};
        }
        
        return module;
    }
    
    async analyzePlugin(filePath) {
        const plugin = {
            path: filePath,
            name: path.basename(path.dirname(filePath)),
            type: 'plugin',
            manifest: null,
            dependencies: [],
            version: '1.0.0',
            metadata: {},
            permissions: []
        };
        
        if (filePath.endsWith('package.json')) {
            const content = await fs.readFile(filePath, 'utf8');
            const packageJson = JSON.parse(content);
            
            plugin.name = packageJson.name || plugin.name;
            plugin.version = packageJson.version || plugin.version;
            plugin.dependencies = Object.keys(packageJson.dependencies || {});
            plugin.manifest = packageJson;
            plugin.metadata = packageJson.activelogPlugin || {};
            plugin.permissions = plugin.metadata.permissions || [];
        }
        
        return plugin;
    }
    
    async loadModule(moduleName, moduleType = 'feature') {
        console.log(`📦 Loading module: ${moduleName} (${moduleType})`);
        
        if (this.state.loadedModules.has(moduleName)) {
            console.log(`⚠️ Module ${moduleName} already loaded`);
            return this.state.loadedModules.get(moduleName);
        }
        
        try {
            // Emit beforeLoad hook
            await this.executeHook('beforeLoad', { moduleName, moduleType });
            
            // Resolve module path
            const modulePath = await this.resolveModulePath(moduleName);
            
            // Load dependencies first
            if (this.config.dependencyResolution) {
                await this.loadDependencies(moduleName);
            }
            
            // Create sandbox if enabled
            let sandbox = null;
            if (this.config.enableSandboxing) {
                sandbox = this.createSandbox(moduleName);
            }
            
            // Load the module
            const moduleInstance = await this.loadModuleInstance(modulePath, sandbox);
            
            // Initialize the module
            await this.initializeModule(moduleInstance, moduleName, moduleType);
            
            // Register the module
            this.registerModule(moduleName, moduleInstance, moduleType);
            
            // Setup hot reload if enabled
            if (this.config.enableHotReload) {
                this.setupModuleHotReload(moduleName, modulePath);
            }
            
            // Emit afterLoad hook
            await this.executeHook('afterLoad', { moduleName, moduleType, instance: moduleInstance });
            
            console.log(`✅ Module ${moduleName} loaded successfully`);
            return moduleInstance;
            
        } catch (error) {
            console.error(`❌ Failed to load module ${moduleName}:`, error.message);
            await this.executeHook('onError', { moduleName, error });
            throw error;
        }
    }
    
    async resolveModulePath(moduleName) {
        const possiblePaths = [
            path.join(this.config.modulesPath, moduleName, 'index.js'),
            path.join(this.config.modulesPath, moduleName + '.js'),
            path.join(this.config.pluginsPath, moduleName, 'index.js'),
            path.join(this.config.pluginsPath, moduleName + '.js')
        ];
        
        for (const modulePath of possiblePaths) {
            try {
                await fs.access(modulePath);
                return modulePath;
            } catch {}
        }
        
        throw new Error(`Module not found: ${moduleName}`);
    }
    
    async loadDependencies(moduleName) {
        const dependencies = this.state.dependencies.get(moduleName) || [];
        
        for (const dependency of dependencies) {
            if (!this.state.loadedModules.has(dependency)) {
                await this.loadModule(dependency);
            }
        }
    }
    
    createSandbox(moduleName) {
        const sandbox = {
            console: console,
            require: this.createRestrictedRequire(moduleName),
            module: { exports: {} },
            exports: {},
            __filename: '',
            __dirname: '',
            Buffer,
            process: this.createRestrictedProcess(),
            setTimeout,
            setInterval,
            clearTimeout,
            clearInterval,
            setImmediate,
            clearImmediate
        };
        
        this.state.sandboxes.set(moduleName, sandbox);
        return sandbox;
    }
    
    createRestrictedRequire(moduleName) {
        const allowedModules = new Set([
            'events', 'util', 'crypto', 'os', 'path',
            'stream', 'buffer', 'string_decoder'
        ]);
        
        return (id) => {
            if (allowedModules.has(id)) {
                return require(id);
            }
            
            if (this.state.loadedModules.has(id)) {
                return this.state.loadedModules.get(id);
            }
            
            throw new Error(`Module '${id}' is not allowed in sandbox for ${moduleName}`);
        };
    }
    
    createRestrictedProcess() {
        return {
            env: { ...process.env },
            version: process.version,
            platform: process.platform,
            arch: process.arch,
            nextTick: process.nextTick.bind(process),
            // Restrict access to system functions
            exit: () => { throw new Error('process.exit() not allowed in sandbox'); },
            kill: () => { throw new Error('process.kill() not allowed in sandbox'); }
        };
    }
    
    async loadModuleInstance(modulePath, sandbox) {
        if (sandbox) {
            // Load in sandbox
            const code = await fs.readFile(modulePath, 'utf8');
            const script = new Function('sandbox', `
                with (sandbox) {
                    ${code}
                    return module.exports;
                }
            `);
            return script(sandbox);
        } else {
            // Load normally
            delete require.cache[require.resolve(modulePath)];
            return require(modulePath);
        }
    }
    
    async initializeModule(moduleInstance, moduleName, moduleType) {
        // Set module metadata
        if (typeof moduleInstance === 'object' && moduleInstance !== null) {
            moduleInstance._moduleName = moduleName;
            moduleInstance._moduleType = moduleType;
            moduleInstance._loadedAt = Date.now();
        }
        
        // Call module init function if it exists
        if (typeof moduleInstance.init === 'function') {
            await moduleInstance.init({
                moduleName,
                moduleType,
                moduleManager: this,
                config: this.config
            });
        }
        
        // Start metrics collection
        this.startModuleMetrics(moduleName);
    }
    
    registerModule(moduleName, moduleInstance, moduleType) {
        this.state.loadedModules.set(moduleName, moduleInstance);
        this.state.moduleStates.set(moduleName, 'loaded');
        
        // Add to registry
        this.registry.modules.set(moduleName, {
            instance: moduleInstance,
            type: moduleType,
            loadedAt: Date.now(),
            version: moduleInstance.version || '1.0.0'
        });
        
        // Update load order
        this.state.loadOrder.push(moduleName);
        
        this.emit('moduleLoaded', { moduleName, moduleType, instance: moduleInstance });
    }
    
    setupModuleHotReload(moduleName, modulePath) {
        const watcher = require('fs').watchFile(modulePath, { interval: 1000 }, async (curr, prev) => {
            if (curr.mtime > prev.mtime) {
                console.log(`🔥 Hot reload triggered for module: ${moduleName}`);
                await this.reloadModule(moduleName);
            }
        });
        
        this.state.hotReloadWatchers.set(moduleName, watcher);
    }
    
    async reloadModule(moduleName) {
        try {
            console.log(`🔄 Reloading module: ${moduleName}`);
            
            // Get current module info
            const currentModule = this.state.loadedModules.get(moduleName);
            const moduleInfo = this.registry.modules.get(moduleName);
            
            if (!currentModule || !moduleInfo) {
                throw new Error(`Module ${moduleName} not found for reload`);
            }
            
            // Stop the module
            await this.stopModule(moduleName);
            
            // Unload the module
            await this.unloadModule(moduleName);
            
            // Reload the module
            await this.loadModule(moduleName, moduleInfo.type);
            
            // Start the module
            await this.startModule(moduleName);
            
            console.log(`✅ Module ${moduleName} reloaded successfully`);
            this.emit('moduleReloaded', { moduleName });
            
        } catch (error) {
            console.error(`❌ Failed to reload module ${moduleName}:`, error.message);
            this.emit('moduleReloadFailed', { moduleName, error });
        }
    }
    
    async unloadModule(moduleName) {
        console.log(`📤 Unloading module: ${moduleName}`);
        
        if (!this.state.loadedModules.has(moduleName)) {
            console.log(`⚠️ Module ${moduleName} not loaded`);
            return;
        }
        
        try {
            // Emit beforeUnload hook
            await this.executeHook('beforeUnload', { moduleName });
            
            // Stop the module if running
            if (this.state.moduleStates.get(moduleName) === 'running') {
                await this.stopModule(moduleName);
            }
            
            // Get module instance
            const moduleInstance = this.state.loadedModules.get(moduleName);
            
            // Call module cleanup function if it exists
            if (typeof moduleInstance.cleanup === 'function') {
                await moduleInstance.cleanup();
            }
            
            // Remove from registry
            this.state.loadedModules.delete(moduleName);
            this.state.moduleStates.delete(moduleName);
            this.registry.modules.delete(moduleName);
            
            // Remove from load order
            const index = this.state.loadOrder.indexOf(moduleName);
            if (index !== -1) {
                this.state.loadOrder.splice(index, 1);
            }
            
            // Cleanup hot reload
            if (this.state.hotReloadWatchers.has(moduleName)) {
                const watcher = this.state.hotReloadWatchers.get(moduleName);
                require('fs').unwatchFile(watcher);
                this.state.hotReloadWatchers.delete(moduleName);
            }
            
            // Cleanup sandbox
            this.state.sandboxes.delete(moduleName);
            
            // Stop metrics collection
            this.stopModuleMetrics(moduleName);
            
            // Emit afterUnload hook
            await this.executeHook('afterUnload', { moduleName });
            
            console.log(`✅ Module ${moduleName} unloaded successfully`);
            this.emit('moduleUnloaded', { moduleName });
            
        } catch (error) {
            console.error(`❌ Failed to unload module ${moduleName}:`, error.message);
            await this.executeHook('onError', { moduleName, error });
            throw error;
        }
    }
    
    async startModule(moduleName) {
        console.log(`▶️ Starting module: ${moduleName}`);
        
        const moduleInstance = this.state.loadedModules.get(moduleName);
        if (!moduleInstance) {
            throw new Error(`Module ${moduleName} not loaded`);
        }
        
        try {
            // Emit beforeStart hook
            await this.executeHook('beforeStart', { moduleName, instance: moduleInstance });
            
            // Call module start function if it exists
            if (typeof moduleInstance.start === 'function') {
                await moduleInstance.start();
            }
            
            // Update state
            this.state.moduleStates.set(moduleName, 'running');
            
            // Emit afterStart hook
            await this.executeHook('afterStart', { moduleName, instance: moduleInstance });
            
            console.log(`✅ Module ${moduleName} started successfully`);
            this.emit('moduleStarted', { moduleName });
            
        } catch (error) {
            console.error(`❌ Failed to start module ${moduleName}:`, error.message);
            await this.executeHook('onError', { moduleName, error });
            throw error;
        }
    }
    
    async stopModule(moduleName) {
        console.log(`⏹️ Stopping module: ${moduleName}`);
        
        const moduleInstance = this.state.loadedModules.get(moduleName);
        if (!moduleInstance) {
            throw new Error(`Module ${moduleName} not loaded`);
        }
        
        try {
            // Emit beforeStop hook
            await this.executeHook('beforeStop', { moduleName, instance: moduleInstance });
            
            // Call module stop function if it exists
            if (typeof moduleInstance.stop === 'function') {
                await moduleInstance.stop();
            }
            
            // Update state
            this.state.moduleStates.set(moduleName, 'stopped');
            
            // Emit afterStop hook
            await this.executeHook('afterStop', { moduleName, instance: moduleInstance });
            
            console.log(`✅ Module ${moduleName} stopped successfully`);
            this.emit('moduleStopped', { moduleName });
            
        } catch (error) {
            console.error(`❌ Failed to stop module ${moduleName}:`, error.message);
            await this.executeHook('onError', { moduleName, error });
            throw error;
        }
    }
    
    registerHook(hookName, handler) {
        if (!this.lifecycle.hooks.has(hookName)) {
            this.lifecycle.hooks.set(hookName, new Set());
        }
        
        this.lifecycle.hooks.get(hookName).add(handler);
    }
    
    unregisterHook(hookName, handler) {
        if (this.lifecycle.hooks.has(hookName)) {
            this.lifecycle.hooks.get(hookName).delete(handler);
        }
    }
    
    async executeHook(hookName, context) {
        const handlers = this.lifecycle.hooks.get(hookName);
        if (!handlers) return;
        
        for (const handler of handlers) {
            try {
                await handler(context);
            } catch (error) {
                console.error(`Hook ${hookName} handler failed:`, error.message);
            }
        }
    }
    
    async validateModule(context) {
        const { moduleName } = context;
        
        // Check if module exists
        const modulePath = await this.resolveModulePath(moduleName).catch(() => null);
        if (!modulePath) {
            throw new Error(`Module ${moduleName} not found`);
        }
        
        // Validate module structure
        // Additional validation logic here
        
        return true;
    }
    
    async registerModuleAPI(context) {
        const { moduleName, instance } = context;
        
        if (!instance || typeof instance !== 'object') return;
        
        // Register public API methods
        if (instance.api && typeof instance.api === 'object') {
            this.api.registry.set(moduleName, instance.api);
        }
        
        // Register endpoints
        if (instance.endpoints && Array.isArray(instance.endpoints)) {
            this.api.endpoints.set(moduleName, instance.endpoints);
        }
        
        console.log(`🔌 API registered for module: ${moduleName}`);
    }
    
    async cleanupModule(context) {
        const { moduleName } = context;
        
        // Cleanup API registrations
        this.api.registry.delete(moduleName);
        this.api.endpoints.delete(moduleName);
        
        // Additional cleanup logic here
        
        console.log(`🧹 Cleanup completed for module: ${moduleName}`);
    }
    
    async handleModuleError(context) {
        const { moduleName, error } = context;
        
        console.error(`💥 Module error in ${moduleName}:`, error.message);
        
        // Attempt recovery
        if (this.shouldAttemptRecovery(moduleName, error)) {
            console.log(`🔧 Attempting recovery for module: ${moduleName}`);
            try {
                await this.reloadModule(moduleName);
                console.log(`✅ Module ${moduleName} recovered successfully`);
            } catch (recoveryError) {
                console.error(`❌ Recovery failed for module ${moduleName}:`, recoveryError.message);
            }
        }
    }
    
    shouldAttemptRecovery(moduleName, error) {
        // Simple recovery logic - in production would be more sophisticated
        return !error.message.includes('ENOENT') && !error.message.includes('SyntaxError');
    }
    
    startModuleMetrics(moduleName) {
        const metrics = {
            startTime: Date.now(),
            memoryUsage: 0,
            cpuUsage: 0,
            callCount: 0,
            errorCount: 0
        };
        
        this.state.moduleMetrics.set(moduleName, metrics);
        
        // Start periodic metrics collection
        const timer = setInterval(() => {
            this.collectModuleMetrics(moduleName);
        }, 10000); // Every 10 seconds
        
        this.timers.set(`metrics_${moduleName}`, timer);
    }
    
    stopModuleMetrics(moduleName) {
        const timer = this.timers.get(`metrics_${moduleName}`);
        if (timer) {
            clearInterval(timer);
            this.timers.delete(`metrics_${moduleName}`);
        }
        
        this.state.moduleMetrics.delete(moduleName);
    }
    
    collectModuleMetrics(moduleName) {
        const metrics = this.state.moduleMetrics.get(moduleName);
        if (!metrics) return;
        
        // Update metrics (simplified - in production would measure actual usage)
        metrics.memoryUsage = process.memoryUsage().heapUsed / 1024 / 1024; // MB
        metrics.cpuUsage = Math.random() * 5; // Simulated CPU usage
        
        this.emit('moduleMetrics', { moduleName, metrics });
    }
    
    // Public API methods
    
    getLoadedModules() {
        return Array.from(this.state.loadedModules.keys());
    }
    
    getModuleInfo(moduleName) {
        const instance = this.state.loadedModules.get(moduleName);
        const state = this.state.moduleStates.get(moduleName);
        const registryInfo = this.registry.modules.get(moduleName);
        const metrics = this.state.moduleMetrics.get(moduleName);
        
        return {
            name: moduleName,
            loaded: !!instance,
            state: state || 'unloaded',
            type: registryInfo?.type || 'unknown',
            version: registryInfo?.version || '1.0.0',
            loadedAt: registryInfo?.loadedAt || null,
            metrics: metrics || null
        };
    }
    
    getAllModulesInfo() {
        return this.getLoadedModules().map(name => this.getModuleInfo(name));
    }
    
    async installModule(modulePath, options = {}) {
        console.log(`📦 Installing module from: ${modulePath}`);
        
        // Implementation for installing modules from external sources
        // This would involve copying files, validating, and registering
        
        throw new Error('Module installation not implemented yet');
    }
    
    async uninstallModule(moduleName) {
        console.log(`🗑️ Uninstalling module: ${moduleName}`);
        
        // First unload if loaded
        if (this.state.loadedModules.has(moduleName)) {
            await this.unloadModule(moduleName);
        }
        
        // Implementation for removing module files
        // This would involve file deletion and registry cleanup
        
        throw new Error('Module uninstallation not implemented yet');
    }
    
    getModuleAPI(moduleName) {
        return this.api.registry.get(moduleName) || null;
    }
    
    callModuleMethod(moduleName, methodName, ...args) {
        const api = this.getModuleAPI(moduleName);
        if (!api || typeof api[methodName] !== 'function') {
            throw new Error(`Method ${methodName} not found in module ${moduleName}`);
        }
        
        return api[methodName](...args);
    }
    
    createModuleSnapshot() {
        return {
            timestamp: Date.now(),
            loadedModules: this.getLoadedModules(),
            moduleStates: Object.fromEntries(this.state.moduleStates),
            loadOrder: [...this.state.loadOrder],
            metrics: Object.fromEntries(this.state.moduleMetrics)
        };
    }
    
    async shutdown() {
        console.log('🔄 Shutting down Module Manager...');
        
        // Stop all running modules
        const runningModules = Array.from(this.state.moduleStates.entries())
            .filter(([, state]) => state === 'running')
            .map(([name]) => name);
        
        for (const moduleName of runningModules) {
            try {
                await this.stopModule(moduleName);
            } catch (error) {
                console.error(`Failed to stop module ${moduleName}:`, error.message);
            }
        }
        
        // Unload all modules (in reverse load order)
        const loadedModules = [...this.state.loadOrder].reverse();
        for (const moduleName of loadedModules) {
            try {
                await this.unloadModule(moduleName);
            } catch (error) {
                console.error(`Failed to unload module ${moduleName}:`, error.message);
            }
        }
        
        // Clear all timers
        for (const timer of this.timers.values()) {
            clearInterval(timer);
        }
        this.timers.clear();
        
        // Cleanup hot reload watchers
        for (const watcher of this.state.hotReloadWatchers.values()) {
            require('fs').unwatchFile(watcher);
        }
        this.state.hotReloadWatchers.clear();
        
        this.emit('shutdown');
        console.log('✅ Module Manager shutdown complete');
    }
}

module.exports = ModuleManager;