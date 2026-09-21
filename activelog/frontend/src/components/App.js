/**
 * Main Application Component
 */

import { AuthManager } from '../utils/auth.js';
import { Router } from '../utils/router.js';
import { AuthView } from './auth/AuthView.js';
import { Dashboard } from './dashboard/Dashboard.js';
import { FileManager } from './files/FileManager.js';
import { TagManager } from './tags/TagManager.js';
import { SearchView } from './search/SearchView.js';
import { SettingsView } from './settings/SettingsView.js';
import { Sidebar } from './layout/Sidebar.js';
import { Header } from './layout/Header.js';
import { NotificationManager } from '../utils/notifications.js';
import { ServiceStatusIndicator } from './common/ServiceStatusIndicator.js';
import { ErrorBoundary } from './common/ErrorBoundary.js';

export class App {
    constructor() {
        this.router = new Router();
        this.currentView = null;
        this.isAuthenticated = false;
    }

    async init() {
        this.setupRoutes();
        this.setupEventListeners();
        
        // Check authentication status
        this.isAuthenticated = AuthManager.isAuthenticated();
        
        if (this.isAuthenticated) {
            await this.renderMainApp();
        } else {
            await this.renderAuthView();
        }
        
        // Start router
        this.router.start();
    }

    setupRoutes() {
        this.router.addRoute('/', () => this.showDashboard());
        this.router.addRoute('/files', () => this.showFileManager());
        this.router.addRoute('/tags', () => this.showTagManager());
        this.router.addRoute('/search', () => this.showSearchView());
        this.router.addRoute('/settings', () => this.showSettingsView());
        this.router.addRoute('/login', () => this.showAuthView());
        this.router.addRoute('/register', () => this.showAuthView('register'));
    }

    setupEventListeners() {
        // Listen for authentication changes
        AuthManager.on('login', () => this.onLogin());
        AuthManager.on('logout', () => this.onLogout());
        
        // Listen for route changes
        this.router.on('routeChange', (route) => this.onRouteChange(route));
    }

    async onLogin() {
        this.isAuthenticated = true;
        await this.renderMainApp();
        this.router.navigate('/');
        NotificationManager.success('Welcome back!');
    }

    async onLogout() {
        this.isAuthenticated = false;
        await this.renderAuthView();
        this.router.navigate('/login');
        NotificationManager.info('You have been logged out');
    }

    onRouteChange(route) {
        if (!this.isAuthenticated && route !== '/login' && route !== '/register') {
            this.router.navigate('/login');
            return;
        }
        
        // Update active navigation
        this.updateActiveNavigation(route);
    }

    async renderMainApp() {
        const container = document.getElementById('app') || document.body;
        
        container.innerHTML = `
            <div class="app-container">
                <div id="header">
                    <div class="header-content">
                        <div class="header-left"></div>
                        <div class="header-right">
                            <div id="service-status-indicator"></div>
                        </div>
                    </div>
                </div>
                <div class="main-content">
                    <div id="sidebar"></div>
                    <div id="main-view" class="view-container"></div>
                </div>
                <div id="notifications"></div>
            </div>
        `;

        // Add basic app container styles
        container.innerHTML += `
            <style>
                .app-container {
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                }
                
                #header {
                    background: #fff;
                    border-bottom: 1px solid #dee2e6;
                    padding: 0;
                    flex-shrink: 0;
                }
                
                .header-content {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 12px 20px;
                    max-width: 1200px;
                    margin: 0 auto;
                }
                
                .header-right {
                    display: flex;
                    align-items: center;
                    gap: 15px;
                }
                
                .main-content {
                    display: flex;
                    flex: 1;
                    overflow: hidden;
                }
                
                #sidebar {
                    width: 250px;
                    background: #f8f9fa;
                    border-right: 1px solid #dee2e6;
                    flex-shrink: 0;
                    overflow-y: auto;
                }
                
                #main-view {
                    flex: 1;
                    overflow: auto;
                    background: #fff;
                }
                
                #notifications {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 1000;
                }
                
                @media (max-width: 768px) {
                    #sidebar {
                        width: 200px;
                    }
                    
                    .header-content {
                        padding: 10px 15px;
                    }
                }
                
                @media (max-width: 600px) {
                    #sidebar {
                        position: absolute;
                        left: -250px;
                        transition: left 0.3s ease;
                        z-index: 100;
                        height: 100%;
                    }
                    
                    #sidebar.open {
                        left: 0;
                    }
                }
            </style>
        `;

        // Initialize layout components
        this.header = new Header();
        await this.header.render(document.querySelector('.header-left'));

        this.sidebar = new Sidebar();
        await this.sidebar.render(document.getElementById('sidebar'));

        // Initialize service status indicator
        this.serviceStatusIndicator = new ServiceStatusIndicator();
        this.serviceStatusIndicator.render(document.getElementById('service-status-indicator'));

        // Initialize notification manager
        NotificationManager.init(document.getElementById('notifications'));
    }

    async renderAuthView(mode = 'login') {
        const container = document.getElementById('app') || document.body;
        
        this.authView = new AuthView(mode);
        await this.authView.render(container);
    }

    async showDashboard() {
        if (!this.isAuthenticated) return;
        
        const mainView = document.getElementById('main-view');
        if (!mainView) return;

        const errorBoundary = new ErrorBoundary({
            context: 'Dashboard Component'
        });

        try {
            this.currentView = new Dashboard();
            await errorBoundary.wrap(mainView, () => this.currentView.render(mainView));
        } catch (error) {
            console.error('Dashboard rendering failed:', error);
            mainView.innerHTML = errorBoundary.getDefaultFallbackUI(error, 'Dashboard');
        }
    }

    async showFileManager() {
        if (!this.isAuthenticated) return;
        
        const mainView = document.getElementById('main-view');
        if (!mainView) return;

        const errorBoundary = new ErrorBoundary({ context: 'File Manager Component' });
        try {
            this.currentView = new FileManager();
            await errorBoundary.wrap(mainView, () => this.currentView.render(mainView));
        } catch (error) {
            console.error('FileManager rendering failed:', error);
            mainView.innerHTML = errorBoundary.getDefaultFallbackUI(error, 'File Manager');
        }
    }

    async showTagManager() {
        if (!this.isAuthenticated) return;
        
        const mainView = document.getElementById('main-view');
        if (!mainView) return;

        const errorBoundary = new ErrorBoundary({ context: 'Tag Manager Component' });
        try {
            this.currentView = new TagManager();
            await errorBoundary.wrap(mainView, () => this.currentView.render(mainView));
        } catch (error) {
            console.error('TagManager rendering failed:', error);
            mainView.innerHTML = errorBoundary.getDefaultFallbackUI(error, 'Tag Manager');
        }
    }

    async showSearchView() {
        if (!this.isAuthenticated) return;
        
        const mainView = document.getElementById('main-view');
        if (!mainView) return;

        const errorBoundary = new ErrorBoundary({ context: 'Search View Component' });
        try {
            this.currentView = new SearchView();
            await errorBoundary.wrap(mainView, () => this.currentView.render(mainView));
        } catch (error) {
            console.error('SearchView rendering failed:', error);
            mainView.innerHTML = errorBoundary.getDefaultFallbackUI(error, 'Search View');
        }
    }

    async showSettingsView() {
        if (!this.isAuthenticated) return;
        
        const mainView = document.getElementById('main-view');
        if (!mainView) return;

        const errorBoundary = new ErrorBoundary({ context: 'Settings View Component' });
        try {
            this.currentView = new SettingsView();
            await errorBoundary.wrap(mainView, () => this.currentView.render(mainView));
        } catch (error) {
            console.error('SettingsView rendering failed:', error);
            mainView.innerHTML = errorBoundary.getDefaultFallbackUI(error, 'Settings View');
        }
    }

    async showAuthView(mode = 'login') {
        await this.renderAuthView(mode);
    }

    updateActiveNavigation(route) {
        // Remove active class from all nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to current route
        const routeMap = {
            '/': 'dashboard',
            '/files': 'files',
            '/tags': 'tags',
            '/search': 'search',
            '/settings': 'settings'
        };

        const activeId = routeMap[route];
        if (activeId) {
            const activeItem = document.querySelector(`[data-route="${activeId}"]`);
            if (activeItem) {
                activeItem.classList.add('active');
            }
        }
    }
}