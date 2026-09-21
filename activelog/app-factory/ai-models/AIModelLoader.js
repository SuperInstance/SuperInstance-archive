export class AIModelLoader {
    constructor() {
        this.loadedModels = new Map();
        this.modelCache = new Map();
        this.loadingPromises = new Map();
        this.config = {};
        this.initialized = false;
    }

    static instance = null;

    static getInstance() {
        if (!AIModelLoader.instance) {
            AIModelLoader.instance = new AIModelLoader();
        }
        return AIModelLoader.instance;
    }

    async init(config = {}) {
        if (this.initialized) return;

        this.config = {
            baseEndpoint: '/api/ai',
            cacheEnabled: true,
            preloadEnabled: true,
            maxConcurrentLoads: 3,
            retryAttempts: 3,
            retryDelay: 1000,
            ...config
        };

        this.setupEventListeners();
        this.initialized = true;
        
        console.log('AIModelLoader initialized');
    }

    async loadModels(modelConfigs) {
        if (!Array.isArray(modelConfigs)) {
            modelConfigs = [modelConfigs];
        }

        const loadPromises = modelConfigs.map(config => this.loadModel(config));
        
        try {
            const results = await Promise.allSettled(loadPromises);
            
            const successful = results.filter(r => r.status === 'fulfilled').length;
            const failed = results.filter(r => r.status === 'rejected').length;
            
            console.log(`AI Models loaded: ${successful} successful, ${failed} failed`);
            
            if (failed > 0) {
                const errors = results
                    .filter(r => r.status === 'rejected')
                    .map(r => r.reason);
                
                this.emitModelEvent('models-load-partial', {
                    successful,
                    failed,
                    errors
                });
            } else {
                this.emitModelEvent('models-loaded', { count: successful });
            }
            
            return results;
            
        } catch (error) {
            console.error('Failed to load AI models:', error);
            this.emitModelEvent('models-load-error', { error });
            throw error;
        }
    }

    async loadModel(modelConfig) {
        const { name, type, endpoint, features = [], options = {} } = modelConfig;
        
        if (this.loadedModels.has(name)) {
            console.log(`AI model ${name} already loaded`);
            return this.loadedModels.get(name);
        }

        // Check if already loading
        if (this.loadingPromises.has(name)) {
            return this.loadingPromises.get(name);
        }

        // Create loading promise
        const loadingPromise = this._loadModelImplementation(modelConfig);
        this.loadingPromises.set(name, loadingPromise);

        try {
            const model = await loadingPromise;
            this.loadedModels.set(name, model);
            this.loadingPromises.delete(name);
            
            this.emitModelEvent('model-loaded', { name, type, features });
            console.log(`AI model loaded: ${name} (${type})`);
            
            return model;
            
        } catch (error) {
            this.loadingPromises.delete(name);
            console.error(`Failed to load AI model ${name}:`, error);
            this.emitModelEvent('model-load-error', { name, error });
            throw error;
        }
    }

    async _loadModelImplementation(modelConfig) {
        const { name, type, endpoint, features, options } = modelConfig;

        // Create model instance based on type
        const ModelClass = await this.getModelClass(type);
        const model = new ModelClass({
            name,
            endpoint: this.resolveEndpoint(endpoint),
            features,
            ...options
        });

        // Initialize the model
        await model.init();
        
        // Validate model functionality
        await this.validateModel(model, modelConfig);
        
        return model;
    }

    async getModelClass(type) {
        const modelTypes = {
            'text-generation': () => import('./models/TextGenerationModel.js'),
            'text-classification': () => import('./models/TextClassificationModel.js'),
            'image-classification': () => import('./models/ImageClassificationModel.js'),
            'video-analysis': () => import('./models/VideoAnalysisModel.js'),
            'audio-processing': () => import('./models/AudioProcessingModel.js'),
            'document-processing': () => import('./models/DocumentProcessingModel.js'),
            'recommendation': () => import('./models/RecommendationModel.js'),
            'prediction': () => import('./models/PredictionModel.js'),
            'optimization': () => import('./models/OptimizationModel.js'),
            'analytics': () => import('./models/AnalyticsModel.js'),
            'classification': () => import('./models/ClassificationModel.js'),
            'regression': () => import('./models/RegressionModel.js'),
            'time-series': () => import('./models/TimeSeriesModel.js'),
            'pathfinding': () => import('./models/PathfindingModel.js'),
            'advisory': () => import('./models/AdvisoryModel.js'),
            'safety-analysis': () => import('./models/SafetyAnalysisModel.js'),
            'monitoring': () => import('./models/MonitoringModel.js'),
            'super-resolution': () => import('./models/SuperResolutionModel.js'),
            'event-detection': () => import('./models/EventDetectionModel.js'),
            'signal-processing': () => import('./models/SignalProcessingModel.js'),
            'worldbuilding': () => import('./models/WorldbuildingModel.js'),
            'character-generation': () => import('./models/CharacterGenerationModel.js'),
            'game-design': () => import('./models/GameDesignModel.js'),
            'educational': () => import('./models/EducationalModel.js'),
            'text-analysis': () => import('./models/TextAnalysisModel.js')
        };

        const moduleLoader = modelTypes[type];
        if (!moduleLoader) {
            throw new Error(`Unknown AI model type: ${type}`);
        }

        try {
            const module = await moduleLoader();
            return module.default || module[Object.keys(module)[0]];
        } catch (error) {
            console.error(`Failed to load model class for type ${type}:`, error);
            // Fallback to base model
            const { BaseAIModel } = await import('./models/BaseAIModel.js');
            return BaseAIModel;
        }
    }

    resolveEndpoint(endpoint) {
        if (endpoint.startsWith('http')) {
            return endpoint;
        }
        return `${this.config.baseEndpoint}${endpoint}`;
    }

    async validateModel(model, config) {
        // Basic validation
        if (!model.predict && !model.process && !model.analyze) {
            throw new Error(`Model ${config.name} does not implement required methods`);
        }

        // Feature validation
        if (config.features && config.features.length > 0) {
            const supportedFeatures = model.getSupportedFeatures?.() || [];
            const unsupportedFeatures = config.features.filter(
                feature => !supportedFeatures.includes(feature)
            );
            
            if (unsupportedFeatures.length > 0) {
                console.warn(`Model ${config.name} does not support features:`, unsupportedFeatures);
            }
        }

        // Health check
        if (model.healthCheck) {
            try {
                await model.healthCheck();
            } catch (error) {
                console.warn(`Model ${config.name} health check failed:`, error);
            }
        }
    }

    getModel(name) {
        return this.loadedModels.get(name);
    }

    getAllModels() {
        return Array.from(this.loadedModels.entries()).map(([name, model]) => ({
            name,
            type: model.type,
            features: model.features,
            status: model.getStatus?.() || 'loaded'
        }));
    }

    async unloadModel(name) {
        const model = this.loadedModels.get(name);
        if (!model) {
            console.warn(`Model ${name} not found`);
            return;
        }

        try {
            if (model.destroy) {
                await model.destroy();
            }
            
            this.loadedModels.delete(name);
            this.emitModelEvent('model-unloaded', { name });
            console.log(`AI model unloaded: ${name}`);
            
        } catch (error) {
            console.error(`Failed to unload model ${name}:`, error);
            throw error;
        }
    }

    async reloadModel(name) {
        const model = this.loadedModels.get(name);
        if (!model) {
            throw new Error(`Model ${name} not found`);
        }

        const originalConfig = model.config;
        await this.unloadModel(name);
        return this.loadModel(originalConfig);
    }

    async predict(modelName, input, options = {}) {
        const model = this.getModel(modelName);
        if (!model) {
            throw new Error(`Model ${modelName} not loaded`);
        }

        if (!model.predict) {
            throw new Error(`Model ${modelName} does not support prediction`);
        }

        try {
            this.emitModelEvent('prediction-started', { modelName, input });
            
            const result = await model.predict(input, options);
            
            this.emitModelEvent('prediction-completed', { 
                modelName, 
                input, 
                result,
                duration: result.duration 
            });
            
            return result;
            
        } catch (error) {
            this.emitModelEvent('prediction-error', { modelName, input, error });
            throw error;
        }
    }

    async process(modelName, input, options = {}) {
        const model = this.getModel(modelName);
        if (!model) {
            throw new Error(`Model ${modelName} not loaded`);
        }

        if (!model.process) {
            throw new Error(`Model ${modelName} does not support processing`);
        }

        try {
            this.emitModelEvent('processing-started', { modelName, input });
            
            const result = await model.process(input, options);
            
            this.emitModelEvent('processing-completed', { 
                modelName, 
                input, 
                result,
                duration: result.duration 
            });
            
            return result;
            
        } catch (error) {
            this.emitModelEvent('processing-error', { modelName, input, error });
            throw error;
        }
    }

    async batchPredict(modelName, inputs, options = {}) {
        const model = this.getModel(modelName);
        if (!model) {
            throw new Error(`Model ${modelName} not loaded`);
        }

        if (model.batchPredict) {
            // Use model's native batch processing
            return model.batchPredict(inputs, options);
        }

        // Fallback to sequential processing
        const results = [];
        for (const input of inputs) {
            try {
                const result = await this.predict(modelName, input, options);
                results.push(result);
            } catch (error) {
                results.push({ error: error.message });
            }
        }
        
        return results;
    }

    getModelStats(modelName) {
        const model = this.getModel(modelName);
        if (!model || !model.getStats) {
            return null;
        }
        
        return model.getStats();
    }

    async getModelHealth() {
        const healthChecks = [];
        
        for (const [name, model] of this.loadedModels) {
            if (model.healthCheck) {
                try {
                    const health = await model.healthCheck();
                    healthChecks.push({ name, status: 'healthy', ...health });
                } catch (error) {
                    healthChecks.push({ 
                        name, 
                        status: 'unhealthy', 
                        error: error.message 
                    });
                }
            } else {
                healthChecks.push({ name, status: 'unknown' });
            }
        }
        
        return healthChecks;
    }

    setupEventListeners() {
        document.addEventListener('ai:model-request', async (event) => {
            const { modelName, action, input, options } = event.detail;
            
            try {
                let result;
                switch (action) {
                    case 'predict':
                        result = await this.predict(modelName, input, options);
                        break;
                    case 'process':
                        result = await this.process(modelName, input, options);
                        break;
                    default:
                        throw new Error(`Unknown action: ${action}`);
                }
                
                this.emitModelEvent('model-response', {
                    modelName,
                    action,
                    result,
                    requestId: event.detail.requestId
                });
                
            } catch (error) {
                this.emitModelEvent('model-response-error', {
                    modelName,
                    action,
                    error,
                    requestId: event.detail.requestId
                });
            }
        });
    }

    emitModelEvent(eventName, data) {
        const event = new CustomEvent(`ai:${eventName}`, {
            detail: data
        });
        document.dispatchEvent(event);
    }

    onModelEvent(eventName, callback) {
        document.addEventListener(`ai:${eventName}`, callback);
    }

    offModelEvent(eventName, callback) {
        document.removeEventListener(`ai:${eventName}`, callback);
    }

    async clearCache() {
        this.modelCache.clear();
        this.emitModelEvent('cache-cleared');
    }

    getStatus() {
        return {
            initialized: this.initialized,
            modelsLoaded: this.loadedModels.size,
            modelsLoading: this.loadingPromises.size,
            cacheSize: this.modelCache.size
        };
    }

    async destroy() {
        // Unload all models
        const unloadPromises = Array.from(this.loadedModels.keys()).map(name => 
            this.unloadModel(name).catch(error => 
                console.error(`Failed to unload model ${name}:`, error)
            )
        );
        
        await Promise.allSettled(unloadPromises);
        
        // Clear caches
        this.modelCache.clear();
        this.loadingPromises.clear();
        
        this.initialized = false;
        console.log('AIModelLoader destroyed');
    }
}

export default AIModelLoader.getInstance();