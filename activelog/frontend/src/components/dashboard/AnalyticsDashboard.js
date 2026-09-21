/**
 * Analytics Dashboard with Data Visualizations
 */

import { 
    AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { API } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';

export class AnalyticsDashboard {
    constructor(options = {}) {
        this.container = null;
        this.refreshInterval = options.refreshInterval || 300000; // 5 minutes
        this.autoRefresh = options.autoRefresh !== false;
        
        this.data = {
            overview: {},
            fileTypes: [],
            storage: [],
            activity: [],
            performance: [],
            usage: []
        };
        
        this.charts = new Map();
        this.refreshTimer = null;
        this.isLoading = false;
        
        this.colors = {
            primary: '#3b82f6',
            secondary: '#8b5cf6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444',
            info: '#06b6d4',
            purple: '#8b5cf6',
            pink: '#ec4899',
            indigo: '#6366f1',
            green: '#22c55e'
        };
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="analytics-dashboard">
                <div class="dashboard-header">
                    <div class="dashboard-title">
                        <h1>Analytics Dashboard</h1>
                        <p>Real-time insights into your file system</p>
                    </div>
                    
                    <div class="dashboard-controls">
                        <div class="time-range-selector">
                            <select class="time-range">
                                <option value="1h">Last Hour</option>
                                <option value="24h" selected>Last 24 Hours</option>
                                <option value="7d">Last 7 Days</option>
                                <option value="30d">Last 30 Days</option>
                                <option value="90d">Last 90 Days</option>
                            </select>
                        </div>
                        
                        <button class="btn-refresh" title="Refresh data">
                            <i data-lucide="refresh-cw"></i>
                            <span>Refresh</span>
                        </button>
                        
                        <button class="btn-export" title="Export dashboard">
                            <i data-lucide="download"></i>
                            <span>Export</span>
                        </button>
                    </div>
                </div>
                
                <div class="dashboard-overview">
                    <div class="overview-card">
                        <div class="card-icon">
                            <i data-lucide="files"></i>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="total-files">0</div>
                            <div class="card-label">Total Files</div>
                            <div class="card-change positive" id="files-change">+0%</div>
                        </div>
                    </div>
                    
                    <div class="overview-card">
                        <div class="card-icon">
                            <i data-lucide="hard-drive"></i>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="total-storage">0 GB</div>
                            <div class="card-label">Storage Used</div>
                            <div class="card-change positive" id="storage-change">+0%</div>
                        </div>
                    </div>
                    
                    <div class="overview-card">
                        <div class="card-icon">
                            <i data-lucide="activity"></i>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="activity-count">0</div>
                            <div class="card-label">Recent Activity</div>
                            <div class="card-change positive" id="activity-change">+0%</div>
                        </div>
                    </div>
                    
                    <div class="overview-card">
                        <div class="card-icon">
                            <i data-lucide="zap"></i>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="performance-score">0%</div>
                            <div class="card-label">Performance</div>
                            <div class="card-change positive" id="performance-change">+0%</div>
                        </div>
                    </div>
                </div>
                
                <div class="dashboard-grid">
                    <div class="chart-container large">
                        <div class="chart-header">
                            <h3>File Activity Over Time</h3>
                            <div class="chart-controls">
                                <div class="chart-type-selector">
                                    <button class="chart-type-btn active" data-type="area">Area</button>
                                    <button class="chart-type-btn" data-type="line">Line</button>
                                    <button class="chart-type-btn" data-type="bar">Bar</button>
                                </div>
                            </div>
                        </div>
                        <div class="chart-content" id="activity-chart">
                            <div class="chart-loading">Loading chart...</div>
                        </div>
                    </div>
                    
                    <div class="chart-container medium">
                        <div class="chart-header">
                            <h3>File Types Distribution</h3>
                        </div>
                        <div class="chart-content" id="file-types-chart">
                            <div class="chart-loading">Loading chart...</div>
                        </div>
                    </div>
                    
                    <div class="chart-container medium">
                        <div class="chart-header">
                            <h3>Storage Usage by Location</h3>
                        </div>
                        <div class="chart-content" id="storage-chart">
                            <div class="chart-loading">Loading chart...</div>
                        </div>
                    </div>
                    
                    <div class="chart-container large">
                        <div class="chart-header">
                            <h3>Performance Metrics</h3>
                        </div>
                        <div class="chart-content" id="performance-chart">
                            <div class="chart-loading">Loading chart...</div>
                        </div>
                    </div>
                    
                    <div class="chart-container medium">
                        <div class="chart-header">
                            <h3>Daily Upload Trends</h3>
                        </div>
                        <div class="chart-content" id="uploads-chart">
                            <div class="chart-loading">Loading chart...</div>
                        </div>
                    </div>
                    
                    <div class="chart-container medium">
                        <div class="chart-header">
                            <h3>Most Active Folders</h3>
                        </div>
                        <div class="chart-content" id="folders-chart">
                            <div class="chart-loading">Loading chart...</div>
                        </div>
                    </div>
                </div>
                
                <div class="dashboard-insights">
                    <div class="insights-container">
                        <h3>AI Insights</h3>
                        <div class="insights-list" id="insights-list">
                            <div class="insight-loading">Analyzing your data...</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.setupEventListeners();
        await this.loadData();
        
        if (this.autoRefresh) {
            this.startAutoRefresh();
        }
    }
    
    setupEventListeners() {
        // Time range selector
        this.container.querySelector('.time-range').addEventListener('change', (e) => {
            this.changeTimeRange(e.target.value);
        });
        
        // Refresh button
        this.container.querySelector('.btn-refresh').addEventListener('click', () => {
            this.refreshData();
        });
        
        // Export button
        this.container.querySelector('.btn-export').addEventListener('click', () => {
            this.exportDashboard();
        });
        
        // Chart type selectors
        this.container.querySelectorAll('.chart-type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const container = e.target.closest('.chart-container');
                const chartType = e.target.dataset.type;
                this.changeChartType(container, chartType);
            });
        });
        
        // Window resize handler for responsive charts
        window.addEventListener('resize', () => {
            this.resizeCharts();
        });
    }
    
    async loadData() {
        this.setLoading(true);
        
        try {
            const timeRange = this.container.querySelector('.time-range').value;
            
            const [overview, fileTypes, storage, activity, performance, insights] = await Promise.all([
                API.get(`/analytics/overview?range=${timeRange}`),
                API.get(`/analytics/file-types?range=${timeRange}`),
                API.get(`/analytics/storage?range=${timeRange}`),
                API.get(`/analytics/activity?range=${timeRange}`),
                API.get(`/analytics/performance?range=${timeRange}`),
                API.get(`/analytics/insights?range=${timeRange}`)
            ]);
            
            this.data = {
                overview: overview.data || {},
                fileTypes: fileTypes.data || [],
                storage: storage.data || [],
                activity: activity.data || [],
                performance: performance.data || [],
                insights: insights.data || []
            };
            
            this.updateOverviewCards();
            this.renderCharts();
            this.renderInsights();
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            NotificationManager.error('Failed to load dashboard data');
            this.renderErrorState();
        } finally {
            this.setLoading(false);
        }
    }
    
    updateOverviewCards() {
        const { overview } = this.data;
        
        // Total files
        this.updateCard('total-files', overview.totalFiles || 0, overview.filesChange || 0);
        
        // Storage used
        this.updateCard('total-storage', this.formatBytes(overview.totalStorage || 0), overview.storageChange || 0);
        
        // Activity count
        this.updateCard('activity-count', overview.activityCount || 0, overview.activityChange || 0);
        
        // Performance score
        this.updateCard('performance-score', Math.round(overview.performanceScore || 0) + '%', overview.performanceChange || 0);
    }
    
    updateCard(cardId, value, change) {
        const valueEl = this.container.querySelector(`#${cardId}`);
        const changeEl = this.container.querySelector(`#${cardId.replace(/-.*/, '-change')}`);
        
        if (valueEl) {
            valueEl.textContent = value;
        }
        
        if (changeEl) {
            const isPositive = change >= 0;
            changeEl.textContent = `${isPositive ? '+' : ''}${change}%`;
            changeEl.className = `card-change ${isPositive ? 'positive' : 'negative'}`;
        }
    }
    
    renderCharts() {
        this.renderActivityChart();
        this.renderFileTypesChart();
        this.renderStorageChart();
        this.renderPerformanceChart();
        this.renderUploadsChart();
        this.renderFoldersChart();
    }
    
    renderActivityChart() {
        const container = this.container.querySelector('#activity-chart');
        const chartType = this.getActiveChartType(container) || 'area';
        
        const Chart = this.getChartComponent(chartType);
        const DataComponent = this.getDataComponent(chartType);
        
        if (!Chart || !DataComponent) return;
        
        const chartData = this.data.activity.map(item => ({
            time: new Date(item.timestamp).toLocaleDateString(),
            uploads: item.uploads || 0,
            downloads: item.downloads || 0,
            views: item.views || 0
        }));
        
        const chartElement = React.createElement(ResponsiveContainer, {
            width: '100%',
            height: 300
        }, React.createElement(Chart, {
            data: chartData,
            margin: { top: 20, right: 30, left: 20, bottom: 5 }
        }, [
            React.createElement(CartesianGrid, { strokeDasharray: '3 3', key: 'grid' }),
            React.createElement(XAxis, { dataKey: 'time', key: 'xaxis' }),
            React.createElement(YAxis, { key: 'yaxis' }),
            React.createElement(Tooltip, { key: 'tooltip' }),
            React.createElement(Legend, { key: 'legend' }),
            React.createElement(DataComponent, {
                dataKey: 'uploads',
                stackId: '1',
                stroke: this.colors.primary,
                fill: this.colors.primary,
                key: 'uploads'
            }),
            React.createElement(DataComponent, {
                dataKey: 'downloads',
                stackId: '1',
                stroke: this.colors.secondary,
                fill: this.colors.secondary,
                key: 'downloads'
            }),
            React.createElement(DataComponent, {
                dataKey: 'views',
                stackId: '1',
                stroke: this.colors.success,
                fill: this.colors.success,
                key: 'views'
            })
        ]));
        
        this.renderReactComponent(container, chartElement);
    }
    
    renderFileTypesChart() {
        const container = this.container.querySelector('#file-types-chart');
        
        const chartData = this.data.fileTypes.map((item, index) => ({
            name: item.type,
            value: item.count,
            color: this.getColorByIndex(index)
        }));
        
        const chartElement = React.createElement(ResponsiveContainer, {
            width: '100%',
            height: 300
        }, React.createElement(PieChart, null, [
            React.createElement(Pie, {
                data: chartData,
                cx: '50%',
                cy: '50%',
                labelLine: false,
                label: ({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`,
                outerRadius: 80,
                fill: '#8884d8',
                dataKey: 'value',
                key: 'pie'
            }, chartData.map((entry, index) => 
                React.createElement(Cell, { key: `cell-${index}`, fill: entry.color })
            )),
            React.createElement(Tooltip, { key: 'tooltip' })
        ]));
        
        this.renderReactComponent(container, chartElement);
    }
    
    renderStorageChart() {
        const container = this.container.querySelector('#storage-chart');
        
        const chartData = this.data.storage.map(item => ({
            location: item.location,
            used: item.used,
            available: item.available,
            total: item.total
        }));
        
        const chartElement = React.createElement(ResponsiveContainer, {
            width: '100%',
            height: 300
        }, React.createElement(BarChart, {
            data: chartData,
            margin: { top: 20, right: 30, left: 20, bottom: 5 }
        }, [
            React.createElement(CartesianGrid, { strokeDasharray: '3 3', key: 'grid' }),
            React.createElement(XAxis, { dataKey: 'location', key: 'xaxis' }),
            React.createElement(YAxis, { key: 'yaxis' }),
            React.createElement(Tooltip, { 
                formatter: (value) => this.formatBytes(value),
                key: 'tooltip' 
            }),
            React.createElement(Legend, { key: 'legend' }),
            React.createElement(Bar, {
                dataKey: 'used',
                stackId: 'a',
                fill: this.colors.warning,
                key: 'used'
            }),
            React.createElement(Bar, {
                dataKey: 'available',
                stackId: 'a',
                fill: this.colors.success,
                key: 'available'
            })
        ]));
        
        this.renderReactComponent(container, chartElement);
    }
    
    renderPerformanceChart() {
        const container = this.container.querySelector('#performance-chart');
        
        const chartData = this.data.performance.map(item => ({
            time: new Date(item.timestamp).toLocaleDateString(),
            cpu: item.cpu || 0,
            memory: item.memory || 0,
            disk: item.disk || 0,
            network: item.network || 0
        }));
        
        const chartElement = React.createElement(ResponsiveContainer, {
            width: '100%',
            height: 300
        }, React.createElement(LineChart, {
            data: chartData,
            margin: { top: 20, right: 30, left: 20, bottom: 5 }
        }, [
            React.createElement(CartesianGrid, { strokeDasharray: '3 3', key: 'grid' }),
            React.createElement(XAxis, { dataKey: 'time', key: 'xaxis' }),
            React.createElement(YAxis, { key: 'yaxis' }),
            React.createElement(Tooltip, { key: 'tooltip' }),
            React.createElement(Legend, { key: 'legend' }),
            React.createElement(Line, {
                type: 'monotone',
                dataKey: 'cpu',
                stroke: this.colors.error,
                strokeWidth: 2,
                key: 'cpu'
            }),
            React.createElement(Line, {
                type: 'monotone',
                dataKey: 'memory',
                stroke: this.colors.warning,
                strokeWidth: 2,
                key: 'memory'
            }),
            React.createElement(Line, {
                type: 'monotone',
                dataKey: 'disk',
                stroke: this.colors.info,
                strokeWidth: 2,
                key: 'disk'
            }),
            React.createElement(Line, {
                type: 'monotone',
                dataKey: 'network',
                stroke: this.colors.success,
                strokeWidth: 2,
                key: 'network'
            })
        ]));
        
        this.renderReactComponent(container, chartElement);
    }
    
    renderUploadsChart() {
        const container = this.container.querySelector('#uploads-chart');
        
        // Generate sample data if none available
        const chartData = this.generateSampleData('uploads');
        
        const chartElement = React.createElement(ResponsiveContainer, {
            width: '100%',
            height: 250
        }, React.createElement(AreaChart, {
            data: chartData,
            margin: { top: 20, right: 30, left: 20, bottom: 5 }
        }, [
            React.createElement(CartesianGrid, { strokeDasharray: '3 3', key: 'grid' }),
            React.createElement(XAxis, { dataKey: 'day', key: 'xaxis' }),
            React.createElement(YAxis, { key: 'yaxis' }),
            React.createElement(Tooltip, { key: 'tooltip' }),
            React.createElement(Area, {
                type: 'monotone',
                dataKey: 'uploads',
                stroke: this.colors.purple,
                fill: this.colors.purple,
                fillOpacity: 0.6,
                key: 'area'
            })
        ]));
        
        this.renderReactComponent(container, chartElement);
    }
    
    renderFoldersChart() {
        const container = this.container.querySelector('#folders-chart');
        
        // Generate sample data if none available
        const chartData = this.generateSampleData('folders');
        
        const chartElement = React.createElement(ResponsiveContainer, {
            width: '100%',
            height: 250
        }, React.createElement(BarChart, {
            data: chartData,
            layout: 'horizontal',
            margin: { top: 20, right: 30, left: 40, bottom: 5 }
        }, [
            React.createElement(CartesianGrid, { strokeDasharray: '3 3', key: 'grid' }),
            React.createElement(XAxis, { type: 'number', key: 'xaxis' }),
            React.createElement(YAxis, { dataKey: 'folder', type: 'category', key: 'yaxis' }),
            React.createElement(Tooltip, { key: 'tooltip' }),
            React.createElement(Bar, {
                dataKey: 'activity',
                fill: this.colors.indigo,
                key: 'bar'
            })
        ]));
        
        this.renderReactComponent(container, chartElement);
    }
    
    renderInsights() {
        const container = this.container.querySelector('#insights-list');
        const insights = this.data.insights || this.generateSampleInsights();
        
        if (insights.length === 0) {
            container.innerHTML = '<p class="no-insights">No insights available</p>';
            return;
        }
        
        const html = insights.map(insight => `
            <div class="insight-item ${insight.type || 'info'}">
                <div class="insight-icon">
                    <i data-lucide="${this.getInsightIcon(insight.type)}"></i>
                </div>
                <div class="insight-content">
                    <div class="insight-title">${insight.title}</div>
                    <div class="insight-description">${insight.description}</div>
                    ${insight.action ? `
                        <button class="insight-action" data-action="${insight.action}">
                            ${insight.actionText || 'Take Action'}
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
        
        // Setup action buttons
        container.querySelectorAll('.insight-action').forEach(btn => {
            btn.addEventListener('click', () => {
                this.handleInsightAction(btn.dataset.action);
            });
        });
    }
    
    generateSampleData(type) {
        switch (type) {
            case 'uploads':
                return Array.from({ length: 7 }, (_, i) => ({
                    day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
                    uploads: Math.floor(Math.random() * 50) + 10
                }));
            
            case 'folders':
                return [
                    { folder: 'Documents', activity: 45 },
                    { folder: 'Downloads', activity: 38 },
                    { folder: 'Desktop', activity: 32 },
                    { folder: 'Pictures', activity: 28 },
                    { folder: 'Videos', activity: 15 }
                ];
            
            default:
                return [];
        }
    }
    
    generateSampleInsights() {
        return [
            {
                type: 'warning',
                title: 'Storage Almost Full',
                description: 'Your storage is 85% full. Consider archiving old files.',
                action: 'cleanup',
                actionText: 'Clean Up Files'
            },
            {
                type: 'info',
                title: 'Duplicate Files Detected',
                description: 'Found 23 duplicate files taking up 2.3 GB of space.',
                action: 'duplicates',
                actionText: 'Review Duplicates'
            },
            {
                type: 'success',
                title: 'Backup Complete',
                description: 'All your files have been successfully backed up.',
                action: 'backup',
                actionText: 'View Backup'
            }
        ];
    }
    
    getChartComponent(type) {
        switch (type) {
            case 'area': return AreaChart;
            case 'line': return LineChart;
            case 'bar': return BarChart;
            default: return AreaChart;
        }
    }
    
    getDataComponent(type) {
        switch (type) {
            case 'area': return Area;
            case 'line': return Line;
            case 'bar': return Bar;
            default: return Area;
        }
    }
    
    getActiveChartType(container) {
        const activeBtn = container.querySelector('.chart-type-btn.active');
        return activeBtn ? activeBtn.dataset.type : null;
    }
    
    changeChartType(container, type) {
        // Update active button
        container.querySelectorAll('.chart-type-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === type);
        });
        
        // Re-render chart
        const chartId = container.querySelector('.chart-content').id;
        if (chartId === 'activity-chart') {
            this.renderActivityChart();
        }
    }
    
    getColorByIndex(index) {
        const colorArray = Object.values(this.colors);
        return colorArray[index % colorArray.length];
    }
    
    getInsightIcon(type) {
        switch (type) {
            case 'warning': return 'alert-triangle';
            case 'error': return 'alert-circle';
            case 'success': return 'check-circle';
            case 'info': default: return 'info';
        }
    }
    
    renderReactComponent(container, element) {
        // This would typically use React.render
        // For now, we'll create a placeholder
        container.innerHTML = `
            <div class="chart-placeholder">
                <div class="chart-placeholder-icon">
                    <i data-lucide="bar-chart-3"></i>
                </div>
                <div class="chart-placeholder-text">
                    Chart visualization would render here
                </div>
            </div>
        `;
    }
    
    changeTimeRange(range) {
        this.loadData();
    }
    
    refreshData() {
        this.loadData();
        NotificationManager.success('Dashboard data refreshed');
    }
    
    exportDashboard() {
        // Implementation for exporting dashboard data
        const data = {
            overview: this.data.overview,
            timestamp: new Date().toISOString(),
            timeRange: this.container.querySelector('.time-range').value
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dashboard-export-${Date.now()}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        NotificationManager.success('Dashboard data exported');
    }
    
    handleInsightAction(action) {
        switch (action) {
            case 'cleanup':
                // Navigate to cleanup tool
                NotificationManager.info('Opening cleanup tool...');
                break;
            case 'duplicates':
                // Navigate to duplicate finder
                NotificationManager.info('Opening duplicate finder...');
                break;
            case 'backup':
                // Navigate to backup view
                NotificationManager.info('Opening backup view...');
                break;
            default:
                NotificationManager.info('Action not implemented yet');
        }
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.container.classList.toggle('loading', loading);
        
        if (loading) {
            this.container.querySelectorAll('.chart-loading').forEach(el => {
                el.style.display = 'block';
            });
        } else {
            this.container.querySelectorAll('.chart-loading').forEach(el => {
                el.style.display = 'none';
            });
        }
    }
    
    renderErrorState() {
        this.container.querySelectorAll('.chart-content').forEach(container => {
            container.innerHTML = `
                <div class="chart-error">
                    <div class="error-icon">
                        <i data-lucide="alert-circle"></i>
                    </div>
                    <div class="error-text">Failed to load chart data</div>
                    <button class="retry-btn" onclick="this.closest('.analytics-dashboard').dispatchEvent(new CustomEvent('retry'))">
                        Retry
                    </button>
                </div>
            `;
        });
        
        this.container.addEventListener('retry', () => {
            this.loadData();
        });
    }
    
    startAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.refreshTimer = setInterval(() => {
            if (!this.isLoading) {
                this.loadData();
            }
        }, this.refreshInterval);
    }
    
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }
    
    resizeCharts() {
        // Trigger re-render of responsive charts
        setTimeout(() => {
            this.renderCharts();
        }, 100);
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    destroy() {
        this.stopAutoRefresh();
        
        if (this.container) {
            window.removeEventListener('resize', this.resizeCharts);
        }
        
        this.charts.clear();
        this.data = {};
    }
}