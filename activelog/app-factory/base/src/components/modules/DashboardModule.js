import { BaseModule } from './BaseModule.js';

export default class DashboardModule extends BaseModule {
    constructor(props = {}) {
        super(props);
        this.widgets = new Map();
        this.layout = props.layout || 'grid';
    }

    getTitle() {
        return 'Dashboard';
    }

    getHeaderActions() {
        return `
            ${super.getHeaderActions()}
            <button class="module-action" data-action="addWidget" title="Add Widget">➕</button>
            <button class="module-action" data-action="customize" title="Customize">🎨</button>
        `;
    }

    getContent() {
        return `
            <div class="dashboard-container">
                <div class="dashboard-grid" data-layout="${this.layout}">
                    <div class="widget-placeholder">
                        <div class="placeholder-content">
                            <div class="placeholder-icon">📊</div>
                            <h3>Welcome to your Dashboard</h3>
                            <p>Add widgets to get started with your personalized dashboard</p>
                            <button class="btn-primary" data-action="addWidget">Add Your First Widget</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async buildContent() {
        await super.buildContent();
        await this.loadWidgets();
    }

    async loadWidgets() {
        const savedWidgets = this.loadSavedWidgets();
        
        if (savedWidgets.length === 0) {
            await this.loadDefaultWidgets();
        } else {
            for (const widgetConfig of savedWidgets) {
                await this.addWidget(widgetConfig);
            }
        }
    }

    loadSavedWidgets() {
        try {
            const saved = localStorage.getItem(`dashboard_widgets_${this.config.name}`);
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.warn('Failed to load saved widgets:', error);
            return [];
        }
    }

    async loadDefaultWidgets() {
        const defaultWidgets = this.getDefaultWidgets();
        
        for (const widget of defaultWidgets) {
            await this.addWidget(widget);
        }
    }

    getDefaultWidgets() {
        const appName = this.config.name?.toLowerCase() || '';
        
        const baseWidgets = [
            {
                id: 'welcome',
                type: 'welcome',
                title: 'Welcome',
                size: 'large',
                position: { x: 0, y: 0 }
            },
            {
                id: 'quick-stats',
                type: 'stats',
                title: 'Quick Stats',
                size: 'medium',
                position: { x: 1, y: 0 }
            },
            {
                id: 'recent-activity',
                type: 'activity',
                title: 'Recent Activity',
                size: 'medium',
                position: { x: 0, y: 1 }
            }
        ];

        if (appName.includes('personal')) {
            return [
                ...baseWidgets,
                {
                    id: 'mood-tracker',
                    type: 'mood',
                    title: 'Mood Tracker',
                    size: 'small',
                    position: { x: 1, y: 1 }
                },
                {
                    id: 'memory-timeline',
                    type: 'timeline',
                    title: 'Memory Timeline',
                    size: 'large',
                    position: { x: 0, y: 2 }
                }
            ];
        } else if (appName.includes('business')) {
            return [
                ...baseWidgets,
                {
                    id: 'inventory-summary',
                    type: 'inventory',
                    title: 'Inventory Summary',
                    size: 'medium',
                    position: { x: 1, y: 1 }
                },
                {
                    id: 'financial-overview',
                    type: 'financial',
                    title: 'Financial Overview',
                    size: 'large',
                    position: { x: 0, y: 2 }
                }
            ];
        } else if (appName.includes('fishing')) {
            return [
                ...baseWidgets,
                {
                    id: 'weather-conditions',
                    type: 'weather',
                    title: 'Weather & Conditions',
                    size: 'medium',
                    position: { x: 1, y: 1 }
                },
                {
                    id: 'catch-log',
                    type: 'catch',
                    title: 'Recent Catches',
                    size: 'large',
                    position: { x: 0, y: 2 }
                }
            ];
        }

        return baseWidgets;
    }

    async addWidget(widgetConfig) {
        const widget = await this.createWidget(widgetConfig);
        if (!widget) return;

        this.widgets.set(widgetConfig.id, widget);
        
        const grid = this.container.querySelector('.dashboard-grid');
        const placeholder = grid.querySelector('.widget-placeholder');
        
        if (placeholder && this.widgets.size === 1) {
            placeholder.style.display = 'none';
        }
        
        grid.appendChild(widget.element);
        
        this.saveWidgets();
    }

    async createWidget(config) {
        try {
            const { WidgetFactory } = await import('./widgets/WidgetFactory.js');
            return await WidgetFactory.create(config, this.config);
        } catch (error) {
            console.warn(`Failed to create widget ${config.type}:`, error);
            return this.createFallbackWidget(config);
        }
    }

    createFallbackWidget(config) {
        const element = document.createElement('div');
        element.className = `widget widget-${config.type} widget-${config.size || 'medium'}`;
        element.innerHTML = `
            <div class="widget-header">
                <h3 class="widget-title">${config.title}</h3>
                <div class="widget-actions">
                    <button class="widget-action" data-action="remove" data-widget="${config.id}">×</button>
                </div>
            </div>
            <div class="widget-content">
                <div class="widget-error">
                    <p>Widget "${config.type}" is not available</p>
                </div>
            </div>
        `;

        element.addEventListener('click', this.handleWidgetAction.bind(this));
        
        return { element, config };
    }

    handleAddWidget() {
        this.showWidgetSelector();
    }

    handleCustomize() {
        this.showDashboardCustomizer();
    }

    handleWidgetAction(event) {
        const action = event.target.dataset.action;
        const widgetId = event.target.dataset.widget;
        
        if (action === 'remove' && widgetId) {
            this.removeWidget(widgetId);
        }
    }

    removeWidget(widgetId) {
        const widget = this.widgets.get(widgetId);
        if (!widget) return;

        if (widget.element && widget.element.parentNode) {
            widget.element.parentNode.removeChild(widget.element);
        }
        
        this.widgets.delete(widgetId);
        
        if (this.widgets.size === 0) {
            const placeholder = this.container.querySelector('.widget-placeholder');
            if (placeholder) {
                placeholder.style.display = 'block';
            }
        }
        
        this.saveWidgets();
    }

    showWidgetSelector() {
        document.dispatchEvent(new CustomEvent('app:widget:selector:show', {
            detail: { dashboard: this }
        }));
    }

    showDashboardCustomizer() {
        document.dispatchEvent(new CustomEvent('app:dashboard:customize', {
            detail: { dashboard: this }
        }));
    }

    saveWidgets() {
        try {
            const widgetConfigs = Array.from(this.widgets.values()).map(w => w.config);
            localStorage.setItem(`dashboard_widgets_${this.config.name}`, JSON.stringify(widgetConfigs));
        } catch (error) {
            console.warn('Failed to save widgets:', error);
        }
    }

    updateLayout(newLayout) {
        this.layout = newLayout;
        const grid = this.container.querySelector('.dashboard-grid');
        if (grid) {
            grid.setAttribute('data-layout', newLayout);
        }
    }

    async refresh() {
        for (const widget of this.widgets.values()) {
            if (widget.refresh) {
                try {
                    await widget.refresh();
                } catch (error) {
                    console.warn(`Failed to refresh widget ${widget.config.id}:`, error);
                }
            }
        }
    }

    destroy() {
        for (const widget of this.widgets.values()) {
            if (widget.destroy) {
                widget.destroy();
            }
        }
        this.widgets.clear();
        super.destroy();
    }
}