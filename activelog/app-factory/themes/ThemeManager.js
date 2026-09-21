export class ThemeManager {
    constructor() {
        this.currentTheme = null;
        this.availableThemes = new Map();
        this.customThemes = new Map();
        this.themeCache = new Map();
        this.initialized = false;
    }

    static instance = null;

    static getInstance() {
        if (!ThemeManager.instance) {
            ThemeManager.instance = new ThemeManager();
        }
        return ThemeManager.instance;
    }

    async init() {
        if (this.initialized) return;

        await this.loadAvailableThemes();
        await this.loadCustomThemes();
        this.bindEvents();

        this.initialized = true;
        console.log('ThemeManager initialized with themes:', Array.from(this.availableThemes.keys()));
    }

    async loadAvailableThemes() {
        const themeManifests = [
            'consumer',
            'professional', 
            'marine',
            'pro-dark',
            'academic',
            'gaming',
            'industrial',
            'nautical-simple',
            'nautical-professional',
            'fantasy'
        ];

        for (const themeName of themeManifests) {
            try {
                const theme = await this.loadTheme(themeName);
                this.availableThemes.set(themeName, theme);
                console.log(`Loaded theme: ${themeName}`);
            } catch (error) {
                console.warn(`Failed to load theme ${themeName}:`, error);
            }
        }
    }

    async loadTheme(themeName) {
        if (this.themeCache.has(themeName)) {
            return this.themeCache.get(themeName);
        }

        try {
            const { default: themeConfig } = await import(`./themes/${themeName}/theme.js`);
            this.themeCache.set(themeName, themeConfig);
            return themeConfig;
        } catch (error) {
            console.warn(`Theme ${themeName} not found, using default configuration`);
            return this.getDefaultTheme(themeName);
        }
    }

    getDefaultTheme(themeName) {
        const baseThemes = {
            consumer: {
                name: 'Consumer',
                colors: {
                    primary: '#3b82f6',
                    secondary: '#64748b',
                    success: '#10b981',
                    warning: '#f59e0b',
                    error: '#ef4444',
                    background: '#ffffff',
                    surface: '#f8fafc',
                    text: '#1e293b',
                    textMuted: '#64748b'
                },
                typography: {
                    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    fontSize: '16px',
                    lineHeight: '1.6'
                },
                spacing: {
                    unit: '0.25rem',
                    small: '0.5rem',
                    medium: '1rem',
                    large: '2rem'
                }
            },
            professional: {
                name: 'Professional',
                colors: {
                    primary: '#1e40af',
                    secondary: '#475569',
                    success: '#059669',
                    warning: '#d97706',
                    error: '#dc2626',
                    background: '#ffffff',
                    surface: '#f1f5f9',
                    text: '#0f172a',
                    textMuted: '#475569'
                },
                typography: {
                    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
                    fontSize: '14px',
                    lineHeight: '1.5'
                }
            },
            marine: {
                name: 'Marine',
                colors: {
                    primary: '#0891b2',
                    secondary: '#0f766e',
                    success: '#059669',
                    warning: '#ea580c',
                    error: '#dc2626',
                    background: '#f0f9ff',
                    surface: '#e0f2fe',
                    text: '#0c4a6e',
                    textMuted: '#0e7490'
                }
            },
            gaming: {
                name: 'Gaming',
                colors: {
                    primary: '#8b5cf6',
                    secondary: '#a855f7',
                    success: '#22c55e',
                    warning: '#f59e0b',
                    error: '#ef4444',
                    background: '#0f0f23',
                    surface: '#1e1e3f',
                    text: '#e2e8f0',
                    textMuted: '#94a3b8'
                }
            },
            fantasy: {
                name: 'Fantasy',
                colors: {
                    primary: '#7c3aed',
                    secondary: '#a855f7',
                    success: '#059669',
                    warning: '#d97706',
                    error: '#dc2626',
                    background: '#1e1b4b',
                    surface: '#312e81',
                    text: '#e0e7ff',
                    textMuted: '#c7d2fe'
                }
            }
        };

        return baseThemes[themeName] || baseThemes.consumer;
    }

    async loadCustomThemes() {
        try {
            const savedThemes = localStorage.getItem('activelog_custom_themes');
            if (savedThemes) {
                const themes = JSON.parse(savedThemes);
                for (const [name, config] of Object.entries(themes)) {
                    this.customThemes.set(name, config);
                }
                console.log(`Loaded ${this.customThemes.size} custom themes`);
            }
        } catch (error) {
            console.warn('Failed to load custom themes:', error);
        }
    }

    async setTheme(themeName, options = {}) {
        let theme;
        
        if (this.customThemes.has(themeName)) {
            theme = this.customThemes.get(themeName);
        } else if (this.availableThemes.has(themeName)) {
            theme = this.availableThemes.get(themeName);
        } else {
            console.warn(`Theme ${themeName} not found, loading default`);
            theme = await this.loadTheme(themeName);
        }

        this.currentTheme = {
            ...theme,
            name: themeName,
            ...options
        };

        await this.applyTheme();
        this.saveCurrentTheme();
        
        this.emitThemeEvent('theme-changed', {
            theme: themeName,
            config: this.currentTheme
        });

        console.log(`Applied theme: ${themeName}`);
    }

    async applyTheme() {
        if (!this.currentTheme) return;

        await this.applyCSSVariables();
        await this.loadThemeAssets();
        this.applyThemeClass();
    }

    async applyCSSVariables() {
        const root = document.documentElement;
        const { colors, typography, spacing } = this.currentTheme;

        if (colors) {
            for (const [key, value] of Object.entries(colors)) {
                const cssVar = `--${key.replace(/([A-Z])/g, '-$1').toLowerCase()}-color`;
                root.style.setProperty(cssVar, value);
            }
        }

        if (typography) {
            for (const [key, value] of Object.entries(typography)) {
                const cssVar = `--${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
                root.style.setProperty(cssVar, value);
            }
        }

        if (spacing) {
            for (const [key, value] of Object.entries(spacing)) {
                const cssVar = `--spacing-${key}`;
                root.style.setProperty(cssVar, value);
            }
        }
    }

    async loadThemeAssets() {
        const { assets } = this.currentTheme;
        if (!assets) return;

        if (assets.css) {
            await this.loadCSS(assets.css);
        }

        if (assets.fonts) {
            await this.loadFonts(assets.fonts);
        }

        if (assets.icons) {
            await this.loadIcons(assets.icons);
        }
    }

    async loadCSS(cssFiles) {
        for (const cssFile of cssFiles) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = cssFile;
            link.setAttribute('data-theme-css', '');
            
            document.head.appendChild(link);
            
            await new Promise((resolve, reject) => {
                link.onload = resolve;
                link.onerror = reject;
            });
        }
    }

    async loadFonts(fonts) {
        for (const font of fonts) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = font.url;
            link.setAttribute('data-theme-font', '');
            document.head.appendChild(link);
        }
    }

    async loadIcons(iconConfig) {
        if (iconConfig.type === 'font') {
            await this.loadCSS([iconConfig.url]);
        } else if (iconConfig.type === 'svg') {
            // Load SVG sprite or icon set
            const response = await fetch(iconConfig.url);
            const svgContent = await response.text();
            
            const container = document.createElement('div');
            container.style.display = 'none';
            container.innerHTML = svgContent;
            container.setAttribute('data-theme-icons', '');
            
            document.body.appendChild(container);
        }
    }

    applyThemeClass() {
        const body = document.body;
        
        // Remove existing theme classes
        body.classList.forEach(className => {
            if (className.startsWith('theme-')) {
                body.classList.remove(className);
            }
        });

        // Add new theme class
        body.classList.add(`theme-${this.currentTheme.name}`);
        
        // Set data attribute for CSS targeting
        body.setAttribute('data-theme', this.currentTheme.name);
    }

    saveCurrentTheme() {
        if (this.currentTheme) {
            localStorage.setItem('activelog_current_theme', this.currentTheme.name);
        }
    }

    getCurrentTheme() {
        return this.currentTheme;
    }

    getAvailableThemes() {
        const themes = new Map();
        
        // Add built-in themes
        for (const [name, config] of this.availableThemes) {
            themes.set(name, {
                name: config.name || name,
                type: 'built-in',
                preview: config.preview
            });
        }
        
        // Add custom themes
        for (const [name, config] of this.customThemes) {
            themes.set(name, {
                name: config.name || name,
                type: 'custom',
                preview: config.preview
            });
        }
        
        return Array.from(themes.entries()).map(([key, value]) => ({
            key,
            ...value
        }));
    }

    async createCustomTheme(name, baseTheme, customizations) {
        const base = this.availableThemes.get(baseTheme) || this.getDefaultTheme('consumer');
        
        const customTheme = {
            ...base,
            name,
            ...customizations,
            type: 'custom',
            createdAt: new Date().toISOString()
        };

        this.customThemes.set(name, customTheme);
        this.saveCustomThemes();
        
        this.emitThemeEvent('theme-created', { name, theme: customTheme });
        
        return customTheme;
    }

    deleteCustomTheme(name) {
        if (this.customThemes.has(name)) {
            this.customThemes.delete(name);
            this.saveCustomThemes();
            
            this.emitThemeEvent('theme-deleted', { name });
            return true;
        }
        return false;
    }

    saveCustomThemes() {
        try {
            const themes = Object.fromEntries(this.customThemes);
            localStorage.setItem('activelog_custom_themes', JSON.stringify(themes));
        } catch (error) {
            console.error('Failed to save custom themes:', error);
        }
    }

    async restoreTheme() {
        try {
            const savedTheme = localStorage.getItem('activelog_current_theme');
            if (savedTheme) {
                await this.setTheme(savedTheme);
                return true;
            }
        } catch (error) {
            console.warn('Failed to restore theme:', error);
        }
        return false;
    }

    bindEvents() {
        // Listen for system theme changes
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            darkModeQuery.addEventListener('change', (e) => {
                this.emitThemeEvent('system-theme-changed', { 
                    prefersDark: e.matches 
                });
            });
        }

        // Listen for theme switch requests
        document.addEventListener('theme:switch', (event) => {
            const { theme, options } = event.detail;
            this.setTheme(theme, options);
        });
    }

    emitThemeEvent(eventName, data) {
        const event = new CustomEvent(`theme:${eventName}`, { 
            detail: data 
        });
        document.dispatchEvent(event);
    }

    onThemeEvent(eventName, callback) {
        document.addEventListener(`theme:${eventName}`, callback);
    }

    offThemeEvent(eventName, callback) {
        document.removeEventListener(`theme:${eventName}`, callback);
    }

    cleanup() {
        // Remove theme-specific assets
        document.querySelectorAll('[data-theme-css]').forEach(el => el.remove());
        document.querySelectorAll('[data-theme-font]').forEach(el => el.remove());
        document.querySelectorAll('[data-theme-icons]').forEach(el => el.remove());
        
        // Remove theme classes
        document.body.classList.forEach(className => {
            if (className.startsWith('theme-')) {
                document.body.classList.remove(className);
            }
        });
        
        document.body.removeAttribute('data-theme');
    }

    destroy() {
        this.cleanup();
        this.currentTheme = null;
        this.availableThemes.clear();
        this.customThemes.clear();
        this.themeCache.clear();
        this.initialized = false;
    }
}

export default ThemeManager.getInstance();