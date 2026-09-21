export class Layout {
    constructor(config) {
        this.config = config;
        this.container = null;
        this.sidebar = null;
        this.main = null;
        this.sidebarCollapsed = false;
    }

    async render() {
        const appContainer = document.getElementById('app');
        
        this.container = document.createElement('div');
        this.container.className = 'app-layout sidebar-layout';
        this.container.innerHTML = `
            <div class="layout-sidebar">
                <div class="sidebar-header">
                    <div class="app-logo">
                        <img src="${this.config.favicon || '/favicon.svg'}" alt="Logo" class="logo-icon">
                        <h1 class="logo-text">${this.config.name || 'ActiveLog'}</h1>
                    </div>
                    <button class="sidebar-toggle" aria-label="Toggle sidebar">
                        <i class="toggle-icon">☰</i>
                    </button>
                </div>
                
                <nav class="sidebar-nav">
                    <div class="nav-section primary">
                        <div class="nav-items"></div>
                    </div>
                    <div class="nav-section secondary">
                        <div class="nav-items secondary-items"></div>
                    </div>
                </nav>
                
                <div class="sidebar-footer">
                    <div class="user-profile">
                        <div class="user-avatar"></div>
                        <div class="user-info">
                            <span class="user-name">Guest</span>
                            <span class="user-status">Offline</span>
                        </div>
                        <button class="user-menu-toggle">⋯</button>
                    </div>
                </div>
            </div>
            
            <div class="layout-main">
                <div class="main-header">
                    <div class="breadcrumb"></div>
                    <div class="header-actions">
                        <button class="quick-search" title="Quick Search">🔍</button>
                        <button class="notifications" title="Notifications">🔔</button>
                        <button class="settings" title="Settings">⚙️</button>
                    </div>
                </div>
                
                <div class="main-content">
                    <div class="content-area"></div>
                </div>
            </div>
            
            <div class="user-dropdown">
                <a href="#" class="dropdown-item" data-action="profile">Profile</a>
                <a href="#" class="dropdown-item" data-action="settings">Settings</a>
                <a href="#" class="dropdown-item" data-action="help">Help</a>
                <hr class="dropdown-divider">
                <a href="#" class="dropdown-item" data-action="signout">Sign Out</a>
            </div>
        `;

        appContainer.appendChild(this.container);

        this.sidebar = this.container.querySelector('.layout-sidebar');
        this.main = this.container.querySelector('.layout-main');

        await this.setupNavigation();
        await this.setupEvents();
        await this.updateUserInfo();
    }

    async setupNavigation() {
        const primaryNav = this.container.querySelector('.nav-items');
        const secondaryNav = this.container.querySelector('.secondary-items');
        
        const modules = this.config.modules || [];
        const primaryModules = modules.filter(m => !m.secondary);
        const secondaryModules = modules.filter(m => m.secondary);

        this.renderNavItems(primaryNav, primaryModules);
        this.renderNavItems(secondaryNav, secondaryModules);
    }

    renderNavItems(container, modules) {
        container.innerHTML = modules.map(module => `
            <a href="#" class="nav-item" data-module="${module.name}" title="${module.description || module.name}">
                <i class="nav-icon">${this.getModuleIcon(module.name)}</i>
                <span class="nav-label">${module.label || module.name}</span>
                ${module.badge ? `<span class="nav-badge">${module.badge}</span>` : ''}
            </a>
        `).join('');
    }

    getModuleIcon(moduleName) {
        const iconMap = {
            journal: '📝',
            photos: '📷',
            timeline: '📅',
            quickCapture: '⚡',
            insights: '📊',
            social: '👥',
            settings: '⚙️',
            inventory: '📦',
            payroll: '💰',
            fishing: '🎣',
            video: '🎬',
            study: '📚',
            gaming: '🎮',
            maker: '🔧',
            navigation: '🧭',
            rpg: '🎲'
        };
        return iconMap[moduleName] || '📋';
    }

    async setupEvents() {
        const sidebarToggle = this.container.querySelector('.sidebar-toggle');
        const navItems = this.container.querySelectorAll('.nav-item');
        const headerActions = this.container.querySelectorAll('.header-actions button');
        const userMenuToggle = this.container.querySelector('.user-menu-toggle');
        const userDropdown = this.container.querySelector('.user-dropdown');

        sidebarToggle.addEventListener('click', this.toggleSidebar.bind(this));
        
        navItems.forEach(item => {
            item.addEventListener('click', this.handleNavigation.bind(this));
        });

        headerActions.forEach(button => {
            button.addEventListener('click', this.handleHeaderAction.bind(this));
        });

        userMenuToggle.addEventListener('click', this.toggleUserMenu.bind(this));
        
        userDropdown.addEventListener('click', this.handleUserMenu.bind(this));

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.user-profile')) {
                userDropdown.classList.remove('open');
            }
        });
    }

    toggleSidebar() {
        this.sidebarCollapsed = !this.sidebarCollapsed;
        this.container.classList.toggle('sidebar-collapsed', this.sidebarCollapsed);
        
        const toggleIcon = this.container.querySelector('.toggle-icon');
        toggleIcon.textContent = this.sidebarCollapsed ? '→' : '☰';
    }

    handleNavigation(event) {
        event.preventDefault();
        const target = event.target.closest('.nav-item');
        if (!target) return;

        const module = target.dataset.module;
        
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        target.classList.add('active');

        this.activateModule(module);
        this.updateBreadcrumb(module);
    }

    handleHeaderAction(event) {
        const action = event.target.className;
        
        switch (action) {
            case 'quick-search':
                this.showQuickSearch();
                break;
            case 'notifications':
                this.showNotifications();
                break;
            case 'settings':
                this.showSettings();
                break;
        }
    }

    toggleUserMenu() {
        const dropdown = this.container.querySelector('.user-dropdown');
        dropdown.classList.toggle('open');
    }

    handleUserMenu(event) {
        event.preventDefault();
        const target = event.target.closest('.dropdown-item');
        if (!target) return;

        const action = target.dataset.action;
        const dropdown = this.container.querySelector('.user-dropdown');
        dropdown.classList.remove('open');
        
        switch (action) {
            case 'profile':
                this.showProfile();
                break;
            case 'settings':
                this.showSettings();
                break;
            case 'help':
                this.showHelp();
                break;
            case 'signout':
                this.signOut();
                break;
        }
    }

    activateModule(moduleName) {
        document.dispatchEvent(new CustomEvent('app:module:activate', {
            detail: { moduleName }
        }));
    }

    updateBreadcrumb(module) {
        const breadcrumb = this.container.querySelector('.breadcrumb');
        const moduleConfig = this.config.modules?.find(m => m.name === module);
        const label = moduleConfig?.label || module;
        
        breadcrumb.innerHTML = `
            <span class="breadcrumb-item">${this.config.name}</span>
            <span class="breadcrumb-separator">›</span>
            <span class="breadcrumb-item active">${label}</span>
        `;
    }

    async updateUserInfo() {
        const userName = this.container.querySelector('.user-name');
        const userStatus = this.container.querySelector('.user-status');
        const userAvatar = this.container.querySelector('.user-avatar');

        document.addEventListener('auth:sign-in', (event) => {
            const user = event.detail;
            userName.textContent = user.name || user.email;
            userStatus.textContent = 'Online';
            userAvatar.style.backgroundImage = user.avatar ? `url(${user.avatar})` : '';
        });

        document.addEventListener('auth:sign-out', () => {
            userName.textContent = 'Guest';
            userStatus.textContent = 'Offline';
            userAvatar.style.backgroundImage = '';
        });
    }

    showQuickSearch() {
        document.dispatchEvent(new CustomEvent('app:search:show'));
    }

    showNotifications() {
        document.dispatchEvent(new CustomEvent('app:notifications:show'));
    }

    showSettings() {
        document.dispatchEvent(new CustomEvent('app:settings:show'));
    }

    showProfile() {
        document.dispatchEvent(new CustomEvent('app:profile:show'));
    }

    showHelp() {
        document.dispatchEvent(new CustomEvent('app:help:show'));
    }

    signOut() {
        document.dispatchEvent(new CustomEvent('auth:signout:request'));
    }

    getMainContent() {
        return this.container.querySelector('.content-area');
    }

    getSidebarContent() {
        return this.container.querySelector('.sidebar-nav');
    }

    updateConfig(config) {
        this.config = { ...this.config, ...config };
        
        const title = this.container.querySelector('.logo-text');
        if (title) {
            title.textContent = this.config.name || 'ActiveLog';
        }

        this.setupNavigation();
    }

    destroy() {
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
    }
}