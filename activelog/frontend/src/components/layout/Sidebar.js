/**
 * Sidebar Navigation Component
 */

import { Router } from '../../utils/router.js';
import { GlobalEvents } from '../../utils/events.js';

export class Sidebar {
    constructor() {
        this.isCollapsed = false;
        this.currentRoute = '/';
    }

    async render(container) {
        container.innerHTML = `
            <nav class="sidebar ${this.isCollapsed ? 'collapsed' : ''}">
                <div class="sidebar-header">
                    <button class="sidebar-toggle" id="sidebar-toggle">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="3" y1="6" x2="21" y2="6"/>
                            <line x1="3" y1="12" x2="21" y2="12"/>
                            <line x1="3" y1="18" x2="21" y2="18"/>
                        </svg>
                    </button>
                </div>
                
                <div class="sidebar-content">
                    <div class="nav-section">
                        <div class="nav-section-title">Navigation</div>
                        <ul class="nav-list">
                            <li class="nav-item" data-route="dashboard">
                                <a href="/" class="nav-link">
                                    <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <rect x="3" y="3" width="7" height="7"/>
                                        <rect x="14" y="3" width="7" height="7"/>
                                        <rect x="14" y="14" width="7" height="7"/>
                                        <rect x="3" y="14" width="7" height="7"/>
                                    </svg>
                                    <span class="nav-text">Dashboard</span>
                                </a>
                            </li>
                            
                            <li class="nav-item" data-route="files">
                                <a href="/files" class="nav-link">
                                    <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                                    </svg>
                                    <span class="nav-text">Files</span>
                                    <span class="nav-badge" id="files-badge">0</span>
                                </a>
                            </li>
                            
                            <li class="nav-item" data-route="search">
                                <a href="/search" class="nav-link">
                                    <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <circle cx="11" cy="11" r="8"/>
                                        <path d="m21 21-4.35-4.35"/>
                                    </svg>
                                    <span class="nav-text">Search</span>
                                </a>
                            </li>
                            
                            <li class="nav-item" data-route="tags">
                                <a href="/tags" class="nav-link">
                                    <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
                                        <line x1="7" y1="7" x2="7.01" y2="7"/>
                                    </svg>
                                    <span class="nav-text">Tags</span>
                                    <span class="nav-badge" id="tags-badge">0</span>
                                </a>
                            </li>
                        </ul>
                    </div>
                    
                    <div class="nav-section">
                        <div class="nav-section-title">Tools</div>
                        <ul class="nav-list">
                            <li class="nav-item">
                                <a href="#" class="nav-link" id="upload-files">
                                    <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                        <polyline points="17,8 12,3 7,8"/>
                                        <line x1="12" y1="3" x2="12" y2="15"/>
                                    </svg>
                                    <span class="nav-text">Upload Files</span>
                                </a>
                            </li>
                            
                            <li class="nav-item">
                                <a href="#" class="nav-link" id="sync-now">
                                    <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                                        <path d="M21 3v5h-5"/>
                                        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
                                        <path d="M3 21v-5h5"/>
                                    </svg>
                                    <span class="nav-text">Sync Now</span>
                                </a>
                            </li>
                        </ul>
                    </div>
                    
                    <div class="nav-section">
                        <div class="nav-section-title">System</div>
                        <ul class="nav-list">
                            <li class="nav-item" data-route="settings">
                                <a href="/settings" class="nav-link">
                                    <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <circle cx="12" cy="12" r="3"/>
                                        <path d="M12 1v6m0 6v6"/>
                                        <path d="m12 1 4 4-4 4-4-4 4-4z"/>
                                    </svg>
                                    <span class="nav-text">Settings</span>
                                </a>
                            </li>
                        </ul>
                    </div>
                </div>
                
                <div class="sidebar-footer">
                    <div class="sync-status-mini">
                        <div class="sync-indicator-mini" id="sidebar-sync-indicator"></div>
                        <span class="sync-text-mini" id="sidebar-sync-text">Idle</span>
                    </div>
                    
                    <div class="storage-usage" id="storage-usage">
                        <div class="storage-bar">
                            <div class="storage-fill" style="width: 45%"></div>
                        </div>
                        <div class="storage-text">
                            <span class="storage-used">4.5 GB</span>
                            <span class="storage-total">/ 10 GB</span>
                        </div>
                    </div>
                </div>
            </nav>
        `;

        this.attachEventListeners();
        this.updateNavigation();
    }

    attachEventListeners() {
        // Sidebar toggle
        const toggleButton = document.getElementById('sidebar-toggle');
        toggleButton?.addEventListener('click', () => {
            this.toggleSidebar();
        });

        // Upload files
        const uploadButton = document.getElementById('upload-files');
        uploadButton?.addEventListener('click', (e) => {
            e.preventDefault();
            GlobalEvents.emit('showUploadDialog');
        });

        // Sync now
        const syncButton = document.getElementById('sync-now');
        syncButton?.addEventListener('click', (e) => {
            e.preventDefault();
            this.triggerSync();
        });

        // Navigation items
        const navItems = document.querySelectorAll('.nav-item a[href]');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                // Let the router handle navigation
                this.updateActiveNavItem(e.target.closest('.nav-item'));
            });
        });

        // Listen for route changes
        GlobalEvents.on('routeChange', (route) => {
            this.updateNavigation(route);
        });
    }

    toggleSidebar() {
        this.isCollapsed = !this.isCollapsed;
        const sidebar = document.querySelector('.sidebar');
        
        if (this.isCollapsed) {
            sidebar.classList.add('collapsed');
        } else {
            sidebar.classList.remove('collapsed');
        }

        // Save preference
        localStorage.setItem('sidebar_collapsed', this.isCollapsed.toString());
        
        // Emit event for other components to adjust
        GlobalEvents.emit('sidebarToggle', this.isCollapsed);
    }

    updateNavigation(route = null) {
        const currentRoute = route || window.location.pathname;
        
        // Remove active class from all nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to current route
        const routeMap = {
            '/': 'dashboard',
            '/files': 'files',
            '/search': 'search',
            '/tags': 'tags',
            '/settings': 'settings'
        };

        const activeRoute = routeMap[currentRoute];
        if (activeRoute) {
            const activeItem = document.querySelector(`[data-route="${activeRoute}"]`);
            if (activeItem) {
                activeItem.classList.add('active');
            }
        }
    }

    updateActiveNavItem(navItem) {
        // Remove active from all items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active to clicked item
        if (navItem) {
            navItem.classList.add('active');
        }
    }

    async triggerSync() {
        const syncButton = document.getElementById('sync-now');
        const syncIcon = syncButton?.querySelector('.nav-icon');
        
        // Add spinning animation
        if (syncIcon) {
            syncIcon.classList.add('spinning');
        }

        try {
            // Trigger sync via API
            GlobalEvents.emit('triggerSync');
            
            // Remove animation after a delay
            setTimeout(() => {
                if (syncIcon) {
                    syncIcon.classList.remove('spinning');
                }
            }, 2000);
        } catch (error) {
            console.error('Sync failed:', error);
            if (syncIcon) {
                syncIcon.classList.remove('spinning');
            }
        }
    }

    updateFileCount(count) {
        const badge = document.getElementById('files-badge');
        if (badge) {
            badge.textContent = count.toString();
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    updateTagCount(count) {
        const badge = document.getElementById('tags-badge');
        if (badge) {
            badge.textContent = count.toString();
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    updateSyncStatus(status) {
        const indicator = document.getElementById('sidebar-sync-indicator');
        const text = document.getElementById('sidebar-sync-text');
        
        if (indicator && text) {
            indicator.className = `sync-indicator-mini ${status.state}`;
            
            switch (status.state) {
                case 'syncing':
                    text.textContent = 'Syncing...';
                    break;
                case 'synced':
                    text.textContent = 'Synced';
                    break;
                case 'error':
                    text.textContent = 'Error';
                    break;
                default:
                    text.textContent = 'Idle';
            }
        }
    }

    updateStorageUsage(used, total) {
        const usedElement = document.querySelector('.storage-used');
        const totalElement = document.querySelector('.storage-total');
        const fillElement = document.querySelector('.storage-fill');
        
        if (usedElement && totalElement && fillElement) {
            const percentage = (used / total) * 100;
            
            usedElement.textContent = this.formatBytes(used);
            totalElement.textContent = `/ ${this.formatBytes(total)}`;
            fillElement.style.width = `${percentage}%`;
            
            // Change color based on usage
            if (percentage > 90) {
                fillElement.className = 'storage-fill danger';
            } else if (percentage > 75) {
                fillElement.className = 'storage-fill warning';
            } else {
                fillElement.className = 'storage-fill';
            }
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
}