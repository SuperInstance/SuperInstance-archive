/**
 * Selective Feature Loader - Load only what's needed when it's needed
 */

const { EventEmitter } = require('events');
const path = require('path');
const fs = require('fs').promises;

class FeatureLoader extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.config = {
            lazyLoading: options.lazyLoading ?? true,
            preloadCritical: options.preloadCritical ?? true,
            maxLoadTime: options.maxLoadTime || 5000,
            cacheModules: options.cacheModules ?? true,
            dynamicImports: options.dynamicImports ?? true,
            featureDirectory: options.featureDirectory || './shared/components',
            ...options
        };
        
        this.features = {
            available: new Map(),
            loaded: new Map(),
            loading: new Map(),
            failed: new Map(),
            critical: new Set(['core', 'security', 'error-handling']),
            optional: new Set(['analytics', 'telemetry', 'animations', 'notifications'])
        };
        
        this.loadState = {
            totalFeatures: 0,
            loadedFeatures: 0,
            failedFeatures: 0,
            loadingTime: 0,
            lastLoadTime: 0
        };
        
        this.moduleCache = new Map();
        this.dependencyGraph = new Map();
        
        this.init();
    }
    
    async init() {
        console.log('🔧 Initializing Feature Loader');
        
        await this.discoverFeatures();
        await this.buildDependencyGraph();
        
        if (this.config.preloadCritical) {
            await this.loadCriticalFeatures();
        }
        
        this.setupLazyLoading();
        this.setupMemoryManagement();
        
        console.log(`✅ Feature Loader ready - ${this.features.available.size} features available`);
    }
    
    async discoverFeatures() {
        try {
            const featurePath = path.resolve(this.config.featureDirectory);
            const items = await fs.readdir(featurePath, { withFileTypes: true });
            
            for (const item of items) {
                if (item.isDirectory()) {
                    await this.registerFeature(item.name, path.join(featurePath, item.name));
                } else if (item.isFile() && item.name.endsWith('.js')) {
                    const featureName = path.basename(item.name, '.js');
                    await this.registerFeature(featureName, path.join(featurePath, item.name));
                }
            }
            
            this.loadState.totalFeatures = this.features.available.size;
            
        } catch (error) {
            console.warn('⚠️ Could not discover features:', error.message);
        }
    }
    
    async registerFeature(name, featurePath) {
        try {
            // Read feature manifest if exists
            const manifestPath = path.join(featurePath, 'manifest.json');
            let manifest = {};
            
            try {
                const manifestData = await fs.readFile(manifestPath, 'utf8');
                manifest = JSON.parse(manifestData);
            } catch {
                // No manifest file, use defaults
            }
            
            const feature = {
                name,
                path: featurePath,
                manifest: {
                    version: manifest.version || '1.0.0',
                    description: manifest.description || `${name} feature`,
                    dependencies: manifest.dependencies || [],
                    optional: manifest.optional ?? true,
                    critical: manifest.critical ?? false,
                    loadOnDemand: manifest.loadOnDemand ?? true,
                    memoryFootprint: manifest.memoryFootprint || 'small',
                    cpuUsage: manifest.cpuUsage || 'low',
                    networkUsage: manifest.networkUsage || 'none',
                    permissions: manifest.permissions || [],
                    gameCompatible: manifest.gameCompatible ?? true,
                    batteryFriendly: manifest.batteryFriendly ?? true,
                    ...manifest
                },
                state: 'available',
                loadedAt: null,
                instance: null,
                loadCount: 0,
                lastAccessed: null,
                memoryUsage: 0
            };
            
            this.features.available.set(name, feature);
            
            // Categorize feature
            if (feature.manifest.critical) {
                this.features.critical.add(name);
            }
            
            if (feature.manifest.optional) {
                this.features.optional.add(name);
            }
            
            console.log(`📦 Registered feature: ${name}`);
            
        } catch (error) {
            console.error(`❌ Failed to register feature ${name}:`, error.message);
            this.features.failed.set(name, { error: error.message, path: featurePath });
        }
    }
    
    async buildDependencyGraph() {
        console.log('🔗 Building dependency graph');
        
        for (const [name, feature] of this.features.available) {
            if (feature.manifest.dependencies.length > 0) {
                this.dependencyGraph.set(name, feature.manifest.dependencies);
            }
        }
        
        // Validate dependencies
        this.validateDependencies();
    }
    
    validateDependencies() {
        for (const [feature, dependencies] of this.dependencyGraph) {
            for (const dep of dependencies) {
                if (!this.features.available.has(dep)) {
                    console.warn(`⚠️ Feature ${feature} depends on missing feature: ${dep}`);
                    
                    // Mark feature as having missing dependencies
                    const featureInfo = this.features.available.get(feature);
                    if (featureInfo) {
                        featureInfo.missingDependencies = featureInfo.missingDependencies || [];
                        featureInfo.missingDependencies.push(dep);
                    }
                }
            }
        }
    }
    
    async loadCriticalFeatures() {
        console.log('🚀 Loading critical features');
        
        const criticalFeatures = Array.from(this.features.critical);
        const loadPromises = criticalFeatures.map(feature => this.loadFeature(feature));
        
        try {
            await Promise.all(loadPromises);
            console.log(`✅ ${criticalFeatures.length} critical features loaded`);
        } catch (error) {
            console.error('❌ Failed to load critical features:', error);
            throw error;
        }
    }
    
    async loadFeature(featureName, options = {}) {
        const startTime = Date.now();
        
        try {
            // Check if already loaded
            if (this.features.loaded.has(featureName)) {
                const feature = this.features.loaded.get(featureName);
                feature.lastAccessed = Date.now();
                feature.loadCount++;
                return feature.instance;
            }
            
            // Check if currently loading
            if (this.features.loading.has(featureName)) {
                return await this.features.loading.get(featureName);
            }
            
            // Get feature info
            const featureInfo = this.features.available.get(featureName);
            if (!featureInfo) {
                throw new Error(`Feature not found: ${featureName}`);
            }
            
            // Check dependencies
            if (featureInfo.missingDependencies?.length > 0) {
                throw new Error(`Missing dependencies: ${featureInfo.missingDependencies.join(', ')}`);
            }
            
            console.log(`📥 Loading feature: ${featureName}`);
            
            // Create loading promise
            const loadingPromise = this.performFeatureLoad(featureInfo, options);
            this.features.loading.set(featureName, loadingPromise);
            
            const instance = await loadingPromise;
            
            // Store loaded feature
            const loadedFeature = {
                ...featureInfo,
                instance,
                state: 'loaded',
                loadedAt: Date.now(),
                loadTime: Date.now() - startTime,
                lastAccessed: Date.now(),
                loadCount: 1,
                memoryUsage: this.estimateMemoryUsage(instance)
            };
            
            this.features.loaded.set(featureName, loadedFeature);
            this.features.loading.delete(featureName);
            
            this.loadState.loadedFeatures++;
            this.loadState.lastLoadTime = Date.now() - startTime;
            
            this.emit('featureLoaded', {
                name: featureName,
                loadTime: loadedFeature.loadTime,
                memoryUsage: loadedFeature.memoryUsage
            });
            
            console.log(`✅ Feature loaded: ${featureName} (${loadedFeature.loadTime}ms)`);
            
            return instance;
            
        } catch (error) {
            console.error(`❌ Failed to load feature ${featureName}:`, error.message);
            
            this.features.loading.delete(featureName);
            this.features.failed.set(featureName, {
                error: error.message,
                timestamp: Date.now(),
                loadTime: Date.now() - startTime
            });
            
            this.loadState.failedFeatures++;
            
            this.emit('featureLoadFailed', {
                name: featureName,
                error: error.message,
                loadTime: Date.now() - startTime
            });
            
            throw error;
        }
    }
    
    async performFeatureLoad(featureInfo, options) {
        const { name, path: featurePath, manifest } = featureInfo;
        
        // Load dependencies first
        if (manifest.dependencies.length > 0) {
            await this.loadDependencies(manifest.dependencies);
        }
        
        // Check resource constraints
        if (!this.canLoadFeature(featureInfo)) {
            throw new Error(`Resource constraints prevent loading ${name}`);
        }
        
        // Load the actual feature
        let instance;
        
        if (this.config.dynamicImports && featurePath.endsWith('.js')) {
            // Dynamic import for single file features
            const module = await import(featurePath);
            instance = new (module.default || module)(options);
        } else {
            // Require for directory-based features
            const modulePath = featurePath.endsWith('.js') ? featurePath : path.join(featurePath, 'index.js');
            
            // Check cache first
            if (this.config.cacheModules && this.moduleCache.has(modulePath)) {
                const CachedModule = this.moduleCache.get(modulePath);
                instance = new CachedModule(options);
            } else {
                delete require.cache[require.resolve(modulePath)];
                const Module = require(modulePath);
                
                if (this.config.cacheModules) {
                    this.moduleCache.set(modulePath, Module);
                }
                
                instance = new Module(options);
            }
        }
        
        // Initialize if needed
        if (typeof instance.init === 'function') {
            await instance.init();
        }
        
        return instance;
    }
    
    async loadDependencies(dependencies) {
        const loadPromises = dependencies.map(dep => this.loadFeature(dep));
        await Promise.all(loadPromises);
    }
    
    canLoadFeature(featureInfo) {
        const currentMemory = process.memoryUsage().heapUsed;
        const estimatedSize = this.estimateFeatureSize(featureInfo);
        
        // Memory check
        if (currentMemory + estimatedSize > 200 * 1024 * 1024) { // 200MB limit
            return false;
        }
        
        // Game mode check
        if (this.isGameModeActive() && !featureInfo.manifest.gameCompatible) {
            return false;
        }
        
        // Battery check
        if (this.isLowPower() && !featureInfo.manifest.batteryFriendly) {
            return false;
        }
        
        return true;
    }
    
    estimateFeatureSize(featureInfo) {
        const sizeMap = {
            'tiny': 1024 * 1024,      // 1MB
            'small': 5 * 1024 * 1024,  // 5MB
            'medium': 20 * 1024 * 1024, // 20MB
            'large': 50 * 1024 * 1024,  // 50MB
            'huge': 100 * 1024 * 1024   // 100MB
        };
        
        return sizeMap[featureInfo.manifest.memoryFootprint] || sizeMap['small'];
    }
    
    estimateMemoryUsage(instance) {
        // Simple memory estimation
        try {
            return JSON.stringify(instance).length * 2; // Rough estimate
        } catch {
            return 1024 * 1024; // 1MB default
        }
    }
    
    setupLazyLoading() {
        if (!this.config.lazyLoading) return;
        
        console.log('🔄 Setting up lazy loading');
        
        // Create proxy for feature access
        this.lazyProxy = new Proxy({}, {
            get: (target, featureName) => {
                if (typeof featureName === 'string' && this.features.available.has(featureName)) {
                    return this.getLazyFeature(featureName);
                }
                return target[featureName];
            }
        });
    }
    
    getLazyFeature(featureName) {
        return new Proxy({}, {
            get: async (target, method) => {
                const instance = await this.loadFeature(featureName);
                return instance[method];
            }
        });
    }
    
    setupMemoryManagement() {
        // Cleanup unused features periodically
        setInterval(() => {
            this.cleanupUnusedFeatures();
        }, 300000); // Every 5 minutes
        
        // Monitor memory usage
        setInterval(() => {
            this.monitorMemoryUsage();
        }, 60000); // Every minute
    }
    
    cleanupUnusedFeatures() {
        const now = Date.now();
        const unusedThreshold = 10 * 60 * 1000; // 10 minutes
        
        const toUnload = [];
        
        for (const [name, feature] of this.features.loaded) {
            if (
                !this.features.critical.has(name) &&
                feature.lastAccessed &&
                (now - feature.lastAccessed) > unusedThreshold
            ) {
                toUnload.push(name);
            }
        }
        
        if (toUnload.length > 0) {
            console.log(`🧹 Cleaning up ${toUnload.length} unused features`);
            toUnload.forEach(name => this.unloadFeature(name));
        }
    }
    
    monitorMemoryUsage() {
        const memUsage = process.memoryUsage();
        const totalFeatureMemory = Array.from(this.features.loaded.values())
            .reduce((sum, feature) => sum + feature.memoryUsage, 0);
        
        if (memUsage.heapUsed > 150 * 1024 * 1024) { // 150MB threshold
            console.log('⚠️ High memory usage detected, unloading optional features');
            this.unloadOptionalFeatures();
        }
        
        this.emit('memoryStats', {
            total: memUsage.heapUsed,
            features: totalFeatureMemory,
            loadedCount: this.features.loaded.size
        });
    }
    
    unloadOptionalFeatures() {
        const optional = Array.from(this.features.loaded.keys())
            .filter(name => this.features.optional.has(name));
        
        optional.forEach(name => this.unloadFeature(name));
    }
    
    unloadFeature(featureName) {
        const feature = this.features.loaded.get(featureName);
        if (!feature) return false;
        
        try {
            // Call cleanup if available
            if (feature.instance && typeof feature.instance.destroy === 'function') {
                feature.instance.destroy();
            }
            
            // Remove from loaded features
            this.features.loaded.delete(featureName);
            
            // Clear from module cache
            const modulePath = feature.path;
            if (this.moduleCache.has(modulePath)) {
                this.moduleCache.delete(modulePath);
            }
            
            // Clear require cache
            delete require.cache[require.resolve(modulePath)];
            
            this.loadState.loadedFeatures--;
            
            console.log(`📤 Feature unloaded: ${featureName}`);
            
            this.emit('featureUnloaded', { name: featureName });
            
            return true;
            
        } catch (error) {
            console.error(`❌ Error unloading feature ${featureName}:`, error.message);
            return false;
        }
    }
    
    isGameModeActive() {
        // Check if game mode is active (would integrate with ResourceManager)
        return process.env.NODE_ENV === 'game' || false;
    }
    
    isLowPower() {
        // Check if low power mode is active
        return process.env.LOW_POWER === 'true' || false;
    }
    
    // Public API methods
    
    async require(featureName, options = {}) {
        return await this.loadFeature(featureName, options);
    }
    
    isLoaded(featureName) {
        return this.features.loaded.has(featureName);
    }
    
    isAvailable(featureName) {
        return this.features.available.has(featureName);
    }
    
    getFeatureInfo(featureName) {
        return this.features.available.get(featureName) || 
               this.features.loaded.get(featureName) ||
               this.features.failed.get(featureName);
    }
    
    listFeatures() {
        return {
            available: Array.from(this.features.available.keys()),
            loaded: Array.from(this.features.loaded.keys()),
            critical: Array.from(this.features.critical),
            optional: Array.from(this.features.optional),
            failed: Array.from(this.features.failed.keys())
        };
    }
    
    getLoadStats() {
        return {
            ...this.loadState,
            successRate: this.loadState.loadedFeatures / (this.loadState.loadedFeatures + this.loadState.failedFeatures),
            averageLoadTime: this.calculateAverageLoadTime(),
            memoryEfficiency: this.calculateMemoryEfficiency()
        };
    }
    
    calculateAverageLoadTime() {
        const loadTimes = Array.from(this.features.loaded.values()).map(f => f.loadTime);
        return loadTimes.reduce((sum, time) => sum + time, 0) / Math.max(loadTimes.length, 1);
    }
    
    calculateMemoryEfficiency() {
        const totalMemory = process.memoryUsage().heapUsed;
        const featureMemory = Array.from(this.features.loaded.values())
            .reduce((sum, feature) => sum + feature.memoryUsage, 0);
        
        return featureMemory / totalMemory;
    }
    
    async preloadFeatures(featureNames) {
        console.log(`🚀 Preloading ${featureNames.length} features`);
        
        const loadPromises = featureNames.map(name => this.loadFeature(name).catch(err => {
            console.warn(`Failed to preload ${name}:`, err.message);
            return null;
        }));
        
        const results = await Promise.all(loadPromises);
        const successful = results.filter(r => r !== null).length;
        
        console.log(`✅ Preloaded ${successful}/${featureNames.length} features`);
        
        return { successful, total: featureNames.length };
    }
    
    async shutdown() {
        console.log('🔄 Shutting down Feature Loader...');
        
        // Unload all features
        const loadedFeatures = Array.from(this.features.loaded.keys());
        for (const featureName of loadedFeatures) {
            await this.unloadFeature(featureName);
        }
        
        // Clear caches
        this.moduleCache.clear();
        this.dependencyGraph.clear();
        
        console.log('✅ Feature Loader shutdown complete');
    }
}

module.exports = FeatureLoader;