export class AppFactory {
    constructor(config) {
        this.config = config;
        this.modules = new Map();
        this.components = new Map();
        this.initialized = false;
    }

    async render() {
        if (this.initialized) return;

        const appContainer = document.getElementById('app');
        if (!appContainer) {
            throw new Error('App container not found');
        }

        appContainer.innerHTML = '';
        
        await this.loadLayout();
        await this.loadModules();
        await this.bindEvents();

        this.initialized = true;
    }

    async loadLayout() {
        const layoutType = this.config.layout || 'default';
        const { Layout } = await import(`@themes/layouts/${layoutType}/Layout.js`);
        
        this.layout = new Layout(this.config);
        await this.layout.render();
    }

    async loadModules() {
        const modules = this.config.modules || [];
        
        for (const moduleConfig of modules) {
            try {
                await this.loadModule(moduleConfig);
            } catch (error) {
                console.warn(`Failed to load module ${moduleConfig.name}:`, error);
            }
        }
    }

    async loadModule(moduleConfig) {
        const { name, component, props = {} } = moduleConfig;
        
        const { default: ModuleComponent } = await import(`./modules/${component}.js`);
        const module = new ModuleComponent({ ...props, config: this.config });
        
        this.modules.set(name, module);
        
        if (module.render) {
            await module.render();
        }
        
        console.log(`Loaded module: ${name}`);
    }

    async bindEvents() {
        document.addEventListener('app:module:load', this.handleModuleLoad.bind(this));
        document.addEventListener('app:module:unload', this.handleModuleUnload.bind(this));
        document.addEventListener('app:config:update', this.handleConfigUpdate.bind(this));
    }

    handleModuleLoad(event) {
        const { moduleName, config } = event.detail;
        this.loadModule({ name: moduleName, ...config });
    }

    handleModuleUnload(event) {
        const { moduleName } = event.detail;
        const module = this.modules.get(moduleName);
        
        if (module && module.destroy) {
            module.destroy();
        }
        
        this.modules.delete(moduleName);
    }

    handleConfigUpdate(event) {
        const { config } = event.detail;
        this.config = { ...this.config, ...config };
        
        if (this.layout && this.layout.updateConfig) {
            this.layout.updateConfig(this.config);
        }
        
        for (const [name, module] of this.modules) {
            if (module.updateConfig) {
                module.updateConfig(this.config);
            }
        }
    }

    getModule(name) {
        return this.modules.get(name);
    }

    getAllModules() {
        return Array.from(this.modules.values());
    }

    async reloadModule(name) {
        const module = this.modules.get(name);
        if (!module) return;

        if (module.destroy) {
            module.destroy();
        }

        this.modules.delete(name);
        
        const moduleConfig = this.config.modules.find(m => m.name === name);
        if (moduleConfig) {
            await this.loadModule(moduleConfig);
        }
    }

    destroy() {
        for (const [name, module] of this.modules) {
            if (module.destroy) {
                module.destroy();
            }
        }
        
        this.modules.clear();
        
        if (this.layout && this.layout.destroy) {
            this.layout.destroy();
        }
        
        this.initialized = false;
    }
}