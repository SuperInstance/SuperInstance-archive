export class BaseModule {
    constructor(props = {}) {
        this.props = props;
        this.config = props.config || {};
        this.container = null;
        this.initialized = false;
        this.events = new Map();
    }

    async render() {
        if (this.initialized) return;

        this.container = document.createElement('div');
        this.container.className = `module ${this.getModuleName()}`;
        
        await this.buildContent();
        await this.bindEvents();
        
        this.initialized = true;
    }

    async buildContent() {
        this.container.innerHTML = `
            <div class="module-header">
                <h2 class="module-title">${this.getTitle()}</h2>
                <div class="module-actions">
                    ${this.getHeaderActions()}
                </div>
            </div>
            <div class="module-content">
                ${this.getContent()}
            </div>
        `;
    }

    async bindEvents() {
        const actions = this.container.querySelectorAll('[data-action]');
        actions.forEach(action => {
            action.addEventListener('click', this.handleAction.bind(this));
        });
    }

    handleAction(event) {
        const action = event.target.dataset.action;
        const method = `handle${action.charAt(0).toUpperCase()}${action.slice(1)}`;
        
        if (typeof this[method] === 'function') {
            this[method](event);
        }
    }

    getModuleName() {
        return this.constructor.name.toLowerCase().replace('module', '');
    }

    getTitle() {
        return this.props.title || this.getModuleName();
    }

    getHeaderActions() {
        return `
            <button class="module-action" data-action="refresh" title="Refresh">🔄</button>
            <button class="module-action" data-action="settings" title="Settings">⚙️</button>
        `;
    }

    getContent() {
        return `<p>Module content goes here...</p>`;
    }

    handleRefresh() {
        this.refresh();
    }

    handleSettings() {
        this.showSettings();
    }

    async refresh() {
        console.log(`Refreshing ${this.getModuleName()} module`);
        await this.loadData();
    }

    showSettings() {
        document.dispatchEvent(new CustomEvent('app:module:settings', {
            detail: { module: this.getModuleName() }
        }));
    }

    async loadData() {
        // Override in subclasses
    }

    updateConfig(config) {
        this.config = { ...this.config, ...config };
        if (this.initialized) {
            this.refresh();
        }
    }

    show() {
        if (this.container) {
            this.container.style.display = 'block';
        }
    }

    hide() {
        if (this.container) {
            this.container.style.display = 'none';
        }
    }

    emit(eventName, data) {
        document.dispatchEvent(new CustomEvent(`module:${this.getModuleName()}:${eventName}`, {
            detail: data
        }));
    }

    on(eventName, callback) {
        const fullEventName = `module:${this.getModuleName()}:${eventName}`;
        document.addEventListener(fullEventName, callback);
        
        if (!this.events.has(eventName)) {
            this.events.set(eventName, []);
        }
        this.events.get(eventName).push({ callback, fullEventName });
    }

    off(eventName, callback) {
        const handlers = this.events.get(eventName);
        if (handlers) {
            const handler = handlers.find(h => h.callback === callback);
            if (handler) {
                document.removeEventListener(handler.fullEventName, callback);
                handlers.splice(handlers.indexOf(handler), 1);
            }
        }
    }

    destroy() {
        for (const [eventName, handlers] of this.events) {
            handlers.forEach(handler => {
                document.removeEventListener(handler.fullEventName, handler.callback);
            });
        }
        
        this.events.clear();
        
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        
        this.initialized = false;
    }
}