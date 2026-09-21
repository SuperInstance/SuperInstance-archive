import { AppFactory } from './components/AppFactory.js';
import { AuthManager } from '@auth/AuthManager.js';
import { ThemeManager } from '@themes/ThemeManager.js';
import { SettingsSync } from '@settings/SettingsSync.js';
import { DataSync } from '@sync/DataSync.js';

class BaseApp {
    constructor() {
        this.config = window.__APP_CONFIG__ || {};
        this.appName = this.config.name || 'ActiveLog';
        this.factory = null;
        this.initialized = false;
    }

    async init() {
        try {
            console.log(`Initializing ${this.appName}...`);
            
            await this.initializeCore();
            await this.loadAppSpecific();
            await this.initializeUI();
            
            this.initialized = true;
            console.log(`${this.appName} initialized successfully`);
            
        } catch (error) {
            console.error(`Failed to initialize ${this.appName}:`, error);
            this.showErrorScreen(error);
        }
    }

    async initializeCore() {
        await AuthManager.init(this.config.auth || {});
        
        ThemeManager.setTheme(this.config.theme || 'default');
        
        await SettingsSync.init(this.config.settings || {});
        
        await DataSync.init(this.config.dataSync || {});
    }

    async loadAppSpecific() {
        const { aiModels, customModules } = this.config;
        
        if (aiModels && aiModels.length > 0) {
            const { AIModelLoader } = await import('@ai/AIModelLoader.js');
            await AIModelLoader.loadModels(aiModels);
        }
        
        if (customModules && customModules.length > 0) {
            await this.loadCustomModules(customModules);
        }
    }

    async loadCustomModules(modules) {
        for (const module of modules) {
            try {
                await import(module.path);
                console.log(`Loaded custom module: ${module.name}`);
            } catch (error) {
                console.warn(`Failed to load custom module ${module.name}:`, error);
            }
        }
    }

    async initializeUI() {
        this.factory = new AppFactory(this.config);
        await this.factory.render();
        
        document.title = this.config.title || this.appName;
        
        if (this.config.favicon) {
            this.updateFavicon(this.config.favicon);
        }
    }

    updateFavicon(faviconUrl) {
        const link = document.querySelector("link[rel*='icon']") || document.createElement('link');
        link.type = 'image/x-icon';
        link.rel = 'shortcut icon';
        link.href = faviconUrl;
        document.getElementsByTagName('head')[0].appendChild(link);
    }

    showErrorScreen(error) {
        const errorContainer = document.createElement('div');
        errorContainer.className = 'error-container';
        errorContainer.innerHTML = `
            <div class="error-content">
                <h1>⚠️ Application Error</h1>
                <p>Failed to initialize ${this.appName}</p>
                <details>
                    <summary>Error Details</summary>
                    <pre>${error.stack || error.message}</pre>
                </details>
                <button onclick="location.reload()">Reload Application</button>
            </div>
        `;
        
        document.body.innerHTML = '';
        document.body.appendChild(errorContainer);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const app = new BaseApp();
    await app.init();
});

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});