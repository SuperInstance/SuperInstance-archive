export class Layout {
    constructor(config) {
        this.config = config;
        this.container = null;
        this.sidebar = null;
        this.main = null;
        this.header = null;
        this.footer = null;
    }

    async render() {
        const appContainer = document.getElementById('app');
        
        this.container = document.createElement('div');
        this.container.className = 'app-layout default-layout';
        this.container.innerHTML = `
            <div class="layout-header">
                <div class="header-content">
                    <div class="app-logo">
                        <h1>${this.config.name || 'ActiveLog'}</h1>
                    </div>
                    <div class="header-nav">
                        <nav class="main-nav"></nav>
                        <div class="user-menu"></div>
                    </div>
                </div>
            </div>
            
            <div class="layout-body">
                <div class="layout-sidebar">
                    <div class="sidebar-content"></div>
                </div>
                <div class="layout-main">
                    <div class="main-content"></div>
                </div>
            </div>
            
            <div class="layout-footer">
                <div class="footer-content">
                    <p>&copy; 2024 ${this.config.name || 'ActiveLog'}. All rights reserved.</p>
                </div>
            </div>
        `;

        appContainer.appendChild(this.container);

        this.header = this.container.querySelector('.layout-header');
        this.sidebar = this.container.querySelector('.layout-sidebar');
        this.main = this.container.querySelector('.layout-main');
        this.footer = this.container.querySelector('.layout-footer');

        await this.setupNavigation();
        await this.setupUserMenu();
    }

    async setupNavigation() {
        const nav = this.container.querySelector('.main-nav');
        const navItems = this.config.navigation || [];

        nav.innerHTML = navItems.map(item => `
            <a href="${item.href || '#'}" class="nav-item" data-module="${item.module || ''}">
                ${item.icon ? `<i class="${item.icon}"></i>` : ''}
                ${item.label}
            </a>
        `).join('');

        nav.addEventListener('click', this.handleNavigation.bind(this));
    }

    async setupUserMenu() {
        const userMenu = this.container.querySelector('.user-menu');
        
        userMenu.innerHTML = `
            <div class="user-profile">
                <button class="user-button">
                    <div class="user-avatar"></div>
                    <span class="user-name">Guest</span>
                </button>
                <div class="user-dropdown">
                    <a href="#" class="dropdown-item" data-action="profile">Profile</a>
                    <a href="#" class="dropdown-item" data-action="settings">Settings</a>
                    <hr class="dropdown-divider">
                    <a href="#" class="dropdown-item" data-action="signout">Sign Out</a>
                </div>
            </div>
        `;

        userMenu.addEventListener('click', this.handleUserMenu.bind(this));
    }

    handleNavigation(event) {
        event.preventDefault();
        const target = event.target.closest('.nav-item');
        if (!target) return;

        const module = target.dataset.module;
        if (module) {
            this.activateModule(module);
        }
    }

    handleUserMenu(event) {
        event.preventDefault();
        const target = event.target.closest('.dropdown-item');
        if (!target) return;

        const action = target.dataset.action;
        
        switch (action) {
            case 'profile':
                this.showProfile();
                break;
            case 'settings':
                this.showSettings();
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

    showProfile() {
        document.dispatchEvent(new CustomEvent('app:profile:show'));
    }

    showSettings() {
        document.dispatchEvent(new CustomEvent('app:settings:show'));
    }

    signOut() {
        document.dispatchEvent(new CustomEvent('auth:signout:request'));
    }

    getMainContent() {
        return this.container.querySelector('.main-content');
    }

    getSidebarContent() {
        return this.container.querySelector('.sidebar-content');
    }

    updateConfig(config) {
        this.config = { ...this.config, ...config };
        
        const title = this.container.querySelector('.app-logo h1');
        if (title) {
            title.textContent = this.config.name || 'ActiveLog';
        }
    }

    destroy() {
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
    }
}