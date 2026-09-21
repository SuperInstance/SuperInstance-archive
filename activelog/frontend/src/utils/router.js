/**
 * Simple client-side router
 */

import { EventEmitter } from './events.js';

export class Router extends EventEmitter {
    constructor() {
        super();
        this.routes = new Map();
        this.currentRoute = '';
        this.isStarted = false;
    }

    addRoute(path, handler) {
        this.routes.set(path, handler);
    }

    removeRoute(path) {
        this.routes.delete(path);
    }

    start() {
        if (this.isStarted) return;
        
        this.isStarted = true;
        
        // Listen for popstate events (back/forward buttons)
        window.addEventListener('popstate', () => {
            this.handleRoute(window.location.pathname);
        });
        
        // Handle current route
        this.handleRoute(window.location.pathname);
        
        // Intercept link clicks
        this.interceptLinks();
    }

    stop() {
        this.isStarted = false;
        window.removeEventListener('popstate', this.handlePopState);
    }

    navigate(path) {
        if (path === this.currentRoute) return;
        
        window.history.pushState({}, '', path);
        this.handleRoute(path);
    }

    replace(path) {
        window.history.replaceState({}, '', path);
        this.handleRoute(path);
    }

    back() {
        window.history.back();
    }

    forward() {
        window.history.forward();
    }

    handleRoute(path) {
        const route = this.findRoute(path);
        
        if (route) {
            this.currentRoute = path;
            this.emit('routeChange', path);
            
            try {
                route.handler();
            } catch (error) {
                console.error(`Error handling route '${path}':`, error);
            }
        } else {
            console.warn(`No route found for '${path}'`);
            // Redirect to home or 404 page
            this.navigate('/');
        }
    }

    findRoute(path) {
        // Exact match first
        if (this.routes.has(path)) {
            return { handler: this.routes.get(path) };
        }

        // Pattern matching for dynamic routes
        for (const [routePath, handler] of this.routes) {
            const params = this.matchRoute(routePath, path);
            if (params !== null) {
                return { handler, params };
            }
        }

        return null;
    }

    matchRoute(routePath, actualPath) {
        // Simple pattern matching - can be extended for more complex patterns
        if (routePath === actualPath) {
            return {};
        }

        // Handle wildcard routes
        if (routePath.includes('*')) {
            const regexPattern = routePath.replace(/\*/g, '.*');
            const regex = new RegExp(`^${regexPattern}$`);
            return regex.test(actualPath) ? {} : null;
        }

        // Handle parameter routes (:param)
        if (routePath.includes(':')) {
            const routeParts = routePath.split('/');
            const pathParts = actualPath.split('/');
            
            if (routeParts.length !== pathParts.length) {
                return null;
            }

            const params = {};
            for (let i = 0; i < routeParts.length; i++) {
                const routePart = routeParts[i];
                const pathPart = pathParts[i];
                
                if (routePart.startsWith(':')) {
                    const paramName = routePart.substring(1);
                    params[paramName] = pathPart;
                } else if (routePart !== pathPart) {
                    return null;
                }
            }
            
            return params;
        }

        return null;
    }

    interceptLinks() {
        document.addEventListener('click', (event) => {
            // Only handle left clicks
            if (event.button !== 0) return;
            
            // Only handle links
            const link = event.target.closest('a');
            if (!link) return;
            
            const href = link.getAttribute('href');
            
            // Only handle internal links
            if (!href || href.startsWith('http') || href.startsWith('//')) return;
            
            // Don't handle links with target="_blank"
            if (link.getAttribute('target') === '_blank') return;
            
            // Don't handle if modifier keys are pressed
            if (event.ctrlKey || event.metaKey || event.shiftKey) return;
            
            event.preventDefault();
            this.navigate(href);
        });
    }

    getCurrentRoute() {
        return this.currentRoute;
    }

    getQueryParams() {
        return new URLSearchParams(window.location.search);
    }

    setQueryParam(key, value) {
        const url = new URL(window.location);
        url.searchParams.set(key, value);
        window.history.replaceState({}, '', url);
    }

    removeQueryParam(key) {
        const url = new URL(window.location);
        url.searchParams.delete(key);
        window.history.replaceState({}, '', url);
    }
}