export class Layout {
    constructor(config) {
        this.config = config;
        this.container = null;
        this.sidebar = null;
        this.main = null;
        this.header = null;
        this.footer = null;
        this.initialized = false;
    }

    async render() {
        if (this.initialized) return;

        await this.createLayout();
        await this.setupSidebar();
        await this.setupMain();
        this.bindEvents();

        this.initialized = true;
        console.log('Sidebar layout rendered');
    }

    async createLayout() {
        const appContainer = document.getElementById('app');
        if (!appContainer) {
            throw new Error('App container not found');
        }

        appContainer.innerHTML = `
            <div class="layout-container sidebar-layout">
                <div class="layout-sidebar" id="layout-sidebar">
                    <div class="sidebar-content"></div>
                </div>
                <div class="layout-main" id="layout-main">
                    <div class="layout-header" id="layout-header"></div>
                    <div class="layout-content" id="layout-content"></div>
                    <div class="layout-footer" id="layout-footer"></div>
                </div>
            </div>
        `;

        this.container = appContainer.querySelector('.layout-container');
        this.sidebar = appContainer.querySelector('.layout-sidebar');
        this.main = appContainer.querySelector('.layout-main');
        this.header = appContainer.querySelector('.layout-header');
        this.footer = appContainer.querySelector('.layout-footer');

        this.applyLayoutStyles();
    }

    async setupSidebar() {
        const sidebarContent = this.sidebar.querySelector('.sidebar-content');
        
        const navigation = this.createNavigation();
        const userSection = this.createUserSection();
        const appSwitcher = this.createAppSwitcher();
        
        sidebarContent.appendChild(navigation);
        sidebarContent.appendChild(userSection);
        
        if (this.config.features?.crossAppAccess) {
            sidebarContent.appendChild(appSwitcher);
        }
    }

    createNavigation() {
        const nav = document.createElement('nav');
        nav.className = 'sidebar-navigation';
        
        const navItems = this.getNavigationItems();
        
        nav.innerHTML = `
            <div class="nav-header">
                <div class="app-logo">
                    <img src="${this.config.favicon || '/favicon.svg'}" alt="${this.config.name}" />
                    <span class="app-name">${this.config.name}</span>
                </div>
            </div>
            <ul class="nav-list">
                ${navItems.map(item => `
                    <li class="nav-item" data-route="${item.route}">
                        <a href="${item.route}" class="nav-link">
                            <i class="nav-icon ${item.icon}"></i>
                            <span class="nav-text">${item.label}</span>
                        </a>
                    </li>
                `).join('')}
            </ul>
        `;
        
        return nav;
    }

    createUserSection() {
        const userSection = document.createElement('div');
        userSection.className = 'sidebar-user';
        
        userSection.innerHTML = `
            <div class="user-info">
                <div class="user-avatar">
                    <img src="/api/user/avatar" alt="User Avatar" />
                </div>
                <div class="user-details">
                    <div class="user-name">Loading...</div>
                    <div class="user-email">Loading...</div>
                </div>
            </div>
            <div class="user-actions">
                <button class="btn-icon" data-action="settings">
                    <i class="icon-settings"></i>
                </button>
                <button class="btn-icon" data-action="logout">
                    <i class="icon-logout"></i>
                </button>
            </div>
        `;
        
        return userSection;
    }

    createAppSwitcher() {
        const switcher = document.createElement('div');
        switcher.className = 'app-switcher';
        
        switcher.innerHTML = `
            <div class="switcher-header">
                <span>Switch App</span>
                <button class="btn-icon" data-action="toggle-switcher">
                    <i class="icon-grid"></i>
                </button>
            </div>
            <div class="switcher-grid" style="display: none;">
                <!-- Apps will be loaded dynamically -->
            </div>
        `;
        
        return switcher;
    }

    async setupMain() {
        await this.setupHeader();
        await this.setupContent();
        await this.setupFooter();
    }

    async setupHeader() {
        this.header.innerHTML = `
            <div class="header-content">
                <div class="header-left">
                    <button class="sidebar-toggle" data-action="toggle-sidebar">
                        <i class="icon-menu"></i>
                    </button>
                    <div class="page-title">
                        <h1>Dashboard</h1>
                    </div>
                </div>
                <div class="header-right">
                    <div class="search-container">
                        <input type="search" placeholder="Search..." class="search-input" />
                        <i class="search-icon icon-search"></i>
                    </div>
                    <div class="header-actions">
                        <button class="btn-icon" data-action="notifications">
                            <i class="icon-bell"></i>
                            <span class="notification-badge">3</span>
                        </button>
                        <button class="btn-icon" data-action="help">
                            <i class="icon-help"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    async setupContent() {
        const content = document.getElementById('layout-content');
        content.innerHTML = `
            <div class="content-container">
                <div id="module-container">
                    <!-- Modules will be loaded here -->
                </div>
            </div>
        `;
    }

    async setupFooter() {
        if (this.config.features?.showFooter !== false) {
            this.footer.innerHTML = `
                <div class="footer-content">
                    <div class="footer-left">
                        <span>&copy; 2024 ${this.config.name}</span>
                    </div>
                    <div class="footer-right">
                        <a href="/privacy">Privacy</a>
                        <a href="/terms">Terms</a>
                        <a href="/support">Support</a>
                    </div>
                </div>
            `;
        }
    }

    getNavigationItems() {
        const defaultItems = [
            { route: '/', label: 'Dashboard', icon: 'icon-dashboard' },
            { route: '/files', label: 'Files', icon: 'icon-folder' },
            { route: '/settings', label: 'Settings', icon: 'icon-settings' }
        ];

        if (this.config.modules) {
            const moduleItems = this.config.modules
                .filter(module => module.showInNavigation !== false)
                .map(module => ({
                    route: `/${module.name}`,
                    label: module.label || module.name,
                    icon: module.icon || 'icon-module'
                }));
            
            return [...defaultItems, ...moduleItems];
        }

        return defaultItems;
    }

    bindEvents() {
        // Sidebar toggle
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="toggle-sidebar"]')) {
                this.toggleSidebar();
            }
            
            if (e.target.closest('[data-action="toggle-switcher"]')) {
                this.toggleAppSwitcher();
            }
            
            if (e.target.closest('[data-action="logout"]')) {
                this.handleLogout();
            }
        });

        // Navigation handling
        this.container.addEventListener('click', (e) => {
            const navLink = e.target.closest('.nav-link');
            if (navLink) {
                e.preventDefault();
                const route = navLink.getAttribute('href');
                this.navigateTo(route);
            }
        });

        // Search functionality
        const searchInput = this.header.querySelector('.search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.handleSearch(e.target.value);
            });
        }

        // Responsive handling
        window.addEventListener('resize', () => {
            this.handleResize();
        });

        this.handleResize();
    }

    toggleSidebar() {
        this.container.classList.toggle('sidebar-collapsed');
        
        const event = new CustomEvent('layout:sidebar-toggle', {
            detail: { collapsed: this.container.classList.contains('sidebar-collapsed') }
        });
        document.dispatchEvent(event);
    }

    toggleAppSwitcher() {
        const grid = this.sidebar.querySelector('.switcher-grid');
        if (grid) {
            grid.style.display = grid.style.display === 'none' ? 'block' : 'none';
        }
    }

    async handleLogout() {
        const { default: AuthManager } = await import('@auth/AuthManager.js');
        await AuthManager.signOut();
        window.location.href = '/login';
    }

    navigateTo(route) {
        const event = new CustomEvent('layout:navigate', {
            detail: { route }
        });
        document.dispatchEvent(event);
    }

    handleSearch(query) {
        const event = new CustomEvent('layout:search', {
            detail: { query }
        });
        document.dispatchEvent(event);
    }

    handleResize() {
        const width = window.innerWidth;
        
        if (width < 768) {
            this.container.classList.add('mobile');
            this.container.classList.add('sidebar-collapsed');
        } else {
            this.container.classList.remove('mobile');
            if (width > 1024) {
                this.container.classList.remove('sidebar-collapsed');
            }
        }
    }

    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        
        // Update app name and logo
        const appName = this.sidebar.querySelector('.app-name');
        const appLogo = this.sidebar.querySelector('.app-logo img');
        
        if (appName) {
            appName.textContent = this.config.name;
        }
        
        if (appLogo && this.config.favicon) {
            appLogo.src = this.config.favicon;
        }
    }

    applyLayoutStyles() {
        if (!document.getElementById('sidebar-layout-styles')) {
            const styles = document.createElement('style');
            styles.id = 'sidebar-layout-styles';
            styles.textContent = this.getLayoutCSS();
            document.head.appendChild(styles);
        }
    }

    getLayoutCSS() {
        return `
            .sidebar-layout {
                display: flex;
                min-height: 100vh;
                background: var(--background-color);
            }

            .layout-sidebar {
                width: 280px;
                background: var(--surface-color);
                border-right: 1px solid var(--border-color);
                transition: transform 0.3s ease, width 0.3s ease;
                display: flex;
                flex-direction: column;
            }

            .sidebar-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                padding: 1rem;
            }

            .layout-main {
                flex: 1;
                display: flex;
                flex-direction: column;
            }

            .layout-header {
                background: var(--background-color);
                border-bottom: 1px solid var(--border-color);
                padding: 1rem;
                min-height: 60px;
            }

            .header-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .header-left {
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .header-right {
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .layout-content {
                flex: 1;
                padding: 1rem;
                overflow-y: auto;
            }

            .layout-footer {
                background: var(--surface-color);
                border-top: 1px solid var(--border-color);
                padding: 1rem;
            }

            .footer-content {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.875rem;
                color: var(--text-muted);
            }

            .nav-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }

            .nav-item {
                margin-bottom: 0.5rem;
            }

            .nav-link {
                display: flex;
                align-items: center;
                padding: 0.75rem;
                border-radius: var(--radius);
                text-decoration: none;
                color: var(--text-color);
                transition: background-color 0.2s;
            }

            .nav-link:hover {
                background: var(--background-color);
            }

            .nav-icon {
                margin-right: 0.75rem;
                width: 20px;
                text-align: center;
            }

            .sidebar-user {
                margin-top: auto;
                padding-top: 1rem;
                border-top: 1px solid var(--border-color);
            }

            .user-info {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 1rem;
            }

            .user-avatar img {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                object-fit: cover;
            }

            .user-name {
                font-weight: 600;
                color: var(--text-color);
            }

            .user-email {
                font-size: 0.875rem;
                color: var(--text-muted);
            }

            .btn-icon {
                background: none;
                border: none;
                cursor: pointer;
                padding: 0.5rem;
                border-radius: var(--radius);
                color: var(--text-muted);
                transition: background-color 0.2s;
            }

            .btn-icon:hover {
                background: var(--background-color);
                color: var(--text-color);
            }

            .sidebar-collapsed .layout-sidebar {
                width: 80px;
            }

            .sidebar-collapsed .nav-text,
            .sidebar-collapsed .user-details,
            .sidebar-collapsed .app-name {
                display: none;
            }

            @media (max-width: 768px) {
                .mobile.sidebar-collapsed .layout-sidebar {
                    transform: translateX(-100%);
                    position: fixed;
                    z-index: 1000;
                    height: 100vh;
                }
            }

            .search-container {
                position: relative;
                display: flex;
                align-items: center;
            }

            .search-input {
                width: 300px;
                padding: 0.5rem 2.5rem 0.5rem 1rem;
                border: 1px solid var(--border-color);
                border-radius: var(--radius);
                background: var(--background-color);
            }

            .search-icon {
                position: absolute;
                right: 0.75rem;
                color: var(--text-muted);
            }

            .notification-badge {
                position: absolute;
                top: -4px;
                right: -4px;
                background: var(--error-color);
                color: white;
                border-radius: 50%;
                width: 18px;
                height: 18px;
                font-size: 0.75rem;
                display: flex;
                align-items: center;
                justify-content: center;
            }
        `;
    }

    destroy() {
        if (this.container) {
            this.container.remove();
        }
        
        const styles = document.getElementById('sidebar-layout-styles');
        if (styles) {
            styles.remove();
        }
        
        this.initialized = false;
    }
}