/**
 * Dashboard Component
 */

import { ApiClient } from '../../utils/api.js';
import { WebSocketManager } from '../../utils/websocket.js';
import { GlobalEvents } from '../../utils/events.js';

export class Dashboard {
    constructor() {
        this.stats = {};
        this.recentFiles = [];
        this.recentActivity = [];
        this.systemStatus = {};
    }

    async render(container) {
        container.innerHTML = `
            <div class="dashboard">
                <div class="dashboard-header">
                    <h1>Dashboard</h1>
                    <p class="dashboard-subtitle">Welcome back! Here's what's happening with your files.</p>
                </div>
                
                <div class="dashboard-grid">
                    <!-- Statistics Cards -->
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-icon">📁</div>
                            <div class="stat-content">
                                <div class="stat-value" id="total-files">-</div>
                                <div class="stat-label">Total Files</div>
                            </div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">💾</div>
                            <div class="stat-content">
                                <div class="stat-value" id="total-size">-</div>
                                <div class="stat-label">Total Size</div>
                            </div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">🏷️</div>
                            <div class="stat-content">
                                <div class="stat-value" id="total-tags">-</div>
                                <div class="stat-label">Tags</div>
                            </div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">🔄</div>
                            <div class="stat-content">
                                <div class="stat-value" id="sync-status">-</div>
                                <div class="stat-label">Sync Status</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recent Files -->
                    <div class="dashboard-section">
                        <div class="section-header">
                            <h2>Recent Files</h2>
                            <a href="/files" class="section-link">View All</a>
                        </div>
                        <div class="recent-files" id="recent-files">
                            <div class="loading-placeholder">Loading recent files...</div>
                        </div>
                    </div>
                    
                    <!-- System Status -->
                    <div class="dashboard-section">
                        <div class="section-header">
                            <h2>System Status</h2>
                            <button class="refresh-button" id="refresh-status">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                                    <path d="M21 3v5h-5"/>
                                    <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
                                    <path d="M3 21v-5h5"/>
                                </svg>
                            </button>
                        </div>
                        <div class="system-status" id="system-status">
                            <div class="loading-placeholder">Loading system status...</div>
                        </div>
                    </div>
                    
                    <!-- Recent Activity -->
                    <div class="dashboard-section">
                        <div class="section-header">
                            <h2>Recent Activity</h2>
                        </div>
                        <div class="activity-feed" id="activity-feed">
                            <div class="loading-placeholder">Loading activity...</div>
                        </div>
                    </div>
                    
                    <!-- Quick Actions -->
                    <div class="dashboard-section">
                        <div class="section-header">
                            <h2>Quick Actions</h2>
                        </div>
                        <div class="quick-actions">
                            <button class="quick-action-card" id="upload-files">
                                <div class="action-icon">📤</div>
                                <div class="action-content">
                                    <div class="action-title">Upload Files</div>
                                    <div class="action-description">Add new files to your library</div>
                                </div>
                            </button>
                            
                            <button class="quick-action-card" id="sync-now">
                                <div class="action-icon">🔄</div>
                                <div class="action-content">
                                    <div class="action-title">Sync Now</div>
                                    <div class="action-description">Force synchronization</div>
                                </div>
                            </button>
                            
                            <button class="quick-action-card" id="create-tag">
                                <div class="action-icon">🏷️</div>
                                <div class="action-content">
                                    <div class="action-title">Create Tag</div>
                                    <div class="action-description">Organize with new tags</div>
                                </div>
                            </button>
                            
                            <button class="quick-action-card" id="search-files">
                                <div class="action-icon">🔍</div>
                                <div class="action-content">
                                    <div class="action-title">Search</div>
                                    <div class="action-description">Find files quickly</div>
                                </div>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
        await this.loadDashboardData();
        this.setupRealTimeUpdates();
    }

    attachEventListeners() {
        // Quick actions
        document.getElementById('upload-files')?.addEventListener('click', () => {
            GlobalEvents.emit('showUploadDialog');
        });

        document.getElementById('sync-now')?.addEventListener('click', () => {
            this.triggerSync();
        });

        document.getElementById('create-tag')?.addEventListener('click', () => {
            window.location.hash = '/tags';
        });

        document.getElementById('search-files')?.addEventListener('click', () => {
            window.location.hash = '/search';
        });

        // Refresh status
        document.getElementById('refresh-status')?.addEventListener('click', () => {
            this.loadSystemStatus();
        });
    }

    async loadDashboardData() {
        try {
            // Load all dashboard data in parallel
            await Promise.all([
                this.loadStats(),
                this.loadRecentFiles(),
                this.loadSystemStatus(),
                this.loadRecentActivity()
            ]);
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    async loadStats() {
        try {
            const stats = await ApiClient.get('/metadata/stats');
            this.stats = stats;
            this.renderStats();
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    async loadRecentFiles() {
        try {
            const response = await ApiClient.get('/metadata/files?limit=5&sort=modified&order=desc');
            this.recentFiles = response.files || [];
            this.renderRecentFiles();
        } catch (error) {
            console.error('Failed to load recent files:', error);
        }
    }

    async loadSystemStatus() {
        try {
            const status = await ApiClient.get('/health');
            this.systemStatus = status;
            this.renderSystemStatus();
        } catch (error) {
            console.error('Failed to load system status:', error);
            this.renderSystemStatus({ error: 'Failed to load status' });
        }
    }

    async loadRecentActivity() {
        try {
            const activity = await ApiClient.get('/metadata/activity?limit=10');
            this.recentActivity = activity.activities || [];
            this.renderRecentActivity();
        } catch (error) {
            console.error('Failed to load recent activity:', error);
        }
    }

    renderStats() {
        document.getElementById('total-files').textContent = this.stats.total_files || '0';
        document.getElementById('total-size').textContent = this.formatFileSize(this.stats.total_size || 0);
        document.getElementById('total-tags').textContent = this.stats.total_tags || '0';
        document.getElementById('sync-status').textContent = this.stats.sync_status || 'Unknown';
    }

    renderRecentFiles() {
        const container = document.getElementById('recent-files');
        
        if (this.recentFiles.length === 0) {
            container.innerHTML = '<div class="empty-state">No recent files</div>';
            return;
        }

        container.innerHTML = this.recentFiles.map(file => `
            <div class="recent-file-item" data-file-id="${file.id}">
                <div class="file-icon">${this.getFileIcon(file)}</div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                        <span class="file-date">${this.formatRelativeDate(file.modified_at)}</span>
                    </div>
                </div>
                <div class="sync-status sync-${file.sync_status}" title="${file.sync_status}">
                    ${this.getSyncStatusIcon(file.sync_status)}
                </div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.recent-file-item').forEach(item => {
            item.addEventListener('click', () => {
                const fileId = item.dataset.fileId;
                this.openFile(fileId);
            });
        });
    }

    renderSystemStatus() {
        const container = document.getElementById('system-status');
        
        if (this.systemStatus.error) {
            container.innerHTML = `
                <div class="status-error">
                    <div class="status-icon">⚠️</div>
                    <div class="status-message">Unable to load system status</div>
                </div>
            `;
            return;
        }

        const services = Object.entries(this.systemStatus).map(([service, status]) => `
            <div class="service-status ${status.status || 'unknown'}">
                <div class="service-name">${service}</div>
                <div class="service-indicator">
                    <div class="status-dot"></div>
                    <span class="status-text">${status.status || 'Unknown'}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = services || '<div class="empty-state">No services found</div>';
    }

    renderRecentActivity() {
        const container = document.getElementById('activity-feed');
        
        if (this.recentActivity.length === 0) {
            container.innerHTML = '<div class="empty-state">No recent activity</div>';
            return;
        }

        container.innerHTML = this.recentActivity.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">${this.getActivityIcon(activity.type)}</div>
                <div class="activity-content">
                    <div class="activity-message">${activity.message}</div>
                    <div class="activity-time">${this.formatRelativeDate(activity.timestamp)}</div>
                </div>
            </div>
        `).join('');
    }

    setupRealTimeUpdates() {
        // Subscribe to WebSocket events
        WebSocketManager.subscribeToFileEvents();
        WebSocketManager.subscribeToSyncStatus();

        // Listen for real-time updates
        WebSocketManager.on('fileChange', (data) => {
            this.handleFileChange(data);
        });

        WebSocketManager.on('syncStatus', (data) => {
            this.handleSyncStatusUpdate(data);
        });

        // Refresh data periodically
        setInterval(() => {
            this.loadStats();
        }, 30000); // Every 30 seconds
    }

    handleFileChange(data) {
        // Update stats
        this.loadStats();
        
        // Add to recent activity
        this.recentActivity.unshift({
            type: 'file_change',
            message: `${data.event_type}: ${data.file_path}`,
            timestamp: new Date().toISOString()
        });
        
        // Keep only last 10 items
        this.recentActivity = this.recentActivity.slice(0, 10);
        this.renderRecentActivity();
    }

    handleSyncStatusUpdate(data) {
        // Update sync status in stats
        if (this.stats) {
            this.stats.sync_status = data.status;
            this.renderStats();
        }
        
        // Update recent files sync status
        this.recentFiles.forEach(file => {
            if (data.files && data.files[file.id]) {
                file.sync_status = data.files[file.id];
            }
        });
        this.renderRecentFiles();
    }

    async triggerSync() {
        try {
            const button = document.getElementById('sync-now');
            const icon = button.querySelector('svg');
            
            // Add spinning animation
            icon.classList.add('spinning');
            
            await ApiClient.post('/sync/trigger');
            
            // Remove animation after delay
            setTimeout(() => {
                icon.classList.remove('spinning');
            }, 2000);
            
        } catch (error) {
            console.error('Sync failed:', error);
        }
    }

    async openFile(fileId) {
        // Navigate to file details or open file viewer
        window.location.hash = `/files?selected=${fileId}`;
    }

    // Utility methods
    getFileIcon(file) {
        const iconMap = {
            'folder': '📁',
            'image': '🖼️',
            'video': '🎥',
            'audio': '🎵',
            'document': '📄',
            'pdf': '📕',
            'archive': '📦',
            'code': '💻',
            'default': '📄'
        };
        return iconMap[file.type] || iconMap.default;
    }

    getSyncStatusIcon(status) {
        const statusMap = {
            'local': 'L',
            'cloud': 'C',
            'synced': 'S',
            'error': '!',
            'syncing': '⏳'
        };
        return statusMap[status] || '?';
    }

    getActivityIcon(type) {
        const iconMap = {
            'file_change': '📝',
            'upload': '📤',
            'download': '📥',
            'sync': '🔄',
            'tag': '🏷️',
            'delete': '🗑️',
            'default': '📋'
        };
        return iconMap[type] || iconMap.default;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatRelativeDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays < 7) {
            return `${diffDays} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
}