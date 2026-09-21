// ActiveLog Deployment Dashboard - Client-Side JavaScript

class DeploymentDashboard {
    constructor() {
        this.ws = null;
        this.reconnectInterval = null;
        this.currentSection = 'dashboard';
        this.deployments = [];
        this.systemStatus = null;
        this.charts = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadDashboard();
    }
    
    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('data-section');
                this.showSection(section);
            });
        });
        
        // Sidebar toggle for mobile
        document.getElementById('sidebar-toggle').addEventListener('click', () => {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.toggle('collapsed');
        });
        
        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.refreshData();
        });
        
        // New deployment button
        document.getElementById('new-deployment-btn').addEventListener('click', () => {
            this.showDeploymentWizard();
        });
        
        // Modal close
        document.getElementById('close-modal-btn').addEventListener('click', () => {
            this.closeModal();
        });
        
        // Deployment filter
        document.getElementById('deployment-filter')?.addEventListener('change', (e) => {
            this.filterDeployments(e.target.value);
        });
        
        // Start wizard
        document.getElementById('start-wizard-btn')?.addEventListener('click', () => {
            this.startInteractiveWizard();
        });
        
        // Clear logs
        document.getElementById('clear-logs-btn')?.addEventListener('click', () => {
            this.clearLogs();
        });
        
        // Log deployment selector
        document.getElementById('log-deployment-select')?.addEventListener('change', (e) => {
            this.loadDeploymentLogs(e.target.value);
        });
        
        // Click outside modal to close
        document.getElementById('deployment-modal').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.closeModal();
            }
        });
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            this.updateConnectionStatus(true);
            this.clearReconnectInterval();
        };
        
        this.ws.onclose = () => {
            console.log('❌ WebSocket disconnected');
            this.updateConnectionStatus(false);
            this.scheduleReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('🔥 WebSocket error:', error);
            this.updateConnectionStatus(false);
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'connected':
                this.showNotification('Connected to dashboard', 'success');
                break;
                
            case 'system_status_update':
                this.systemStatus = data.data;
                this.updateSystemStatus();
                break;
                
            case 'deployments_list':
                this.deployments = data.data;
                this.updateDeploymentsList();
                break;
                
            case 'deployment_status_update':
                this.updateDeploymentStatus(data.deploymentId, data.data);
                break;
                
            case 'deployment_output':
                this.appendDeploymentOutput(data.deploymentId, data.output, data.stream);
                break;
                
            case 'deployment_finished':
                this.handleDeploymentFinished(data.deploymentId, data.status);
                break;
                
            default:
                console.log('Unknown message type:', data.type, data);
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectInterval) return;
        
        this.reconnectInterval = setInterval(() => {
            console.log('🔄 Attempting to reconnect...');
            this.connectWebSocket();
        }, 5000);
    }
    
    clearReconnectInterval() {
        if (this.reconnectInterval) {
            clearInterval(this.reconnectInterval);
            this.reconnectInterval = null;
        }
    }
    
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        const dot = statusEl.querySelector('.status-dot');
        const text = statusEl.childNodes[1];
        
        if (connected) {
            dot.className = 'status-dot status-completed';
            text.textContent = ' Connected';
        } else {
            dot.className = 'status-dot status-failed';
            text.textContent = ' Disconnected';
        }
    }
    
    showSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.add('hidden');
        });
        
        // Show target section
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.remove('hidden');
        }
        
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('bg-blue-50', 'text-blue-700');
        });
        
        const activeLink = document.querySelector(`[data-section="${sectionName}"]`);
        if (activeLink) {
            activeLink.classList.add('bg-blue-50', 'text-blue-700');
        }
        
        // Update page title
        const titles = {
            dashboard: 'Dashboard',
            deployments: 'Deployments',
            resources: 'AWS Resources',
            monitoring: 'Monitoring',
            costs: 'Cost Analysis',
            wizard: 'Deploy Wizard',
            logs: 'Logs',
            settings: 'Settings'
        };
        
        document.getElementById('page-title').textContent = titles[sectionName] || 'Dashboard';
        
        this.currentSection = sectionName;
        
        // Load section-specific data
        this.loadSectionData(sectionName);
    }
    
    loadSectionData(sectionName) {
        switch (sectionName) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'deployments':
                this.loadDeployments();
                break;
            case 'resources':
                this.loadResources();
                break;
            case 'monitoring':
                this.loadMonitoring();
                break;
            case 'costs':
                this.loadCostAnalysis();
                break;
        }
    }
    
    async loadDashboard() {
        try {
            // Load system status
            const response = await fetch('/api/status');
            this.systemStatus = await response.json();
            this.updateSystemStatus();
            
            // Load deployments
            await this.loadDeployments();
            
            // Update dashboard cards
            this.updateDashboardCards();
            
            // Initialize charts
            this.initializeDashboardCharts();
            
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showNotification('Error loading dashboard data', 'error');
        }
    }
    
    async loadDeployments() {
        try {
            const response = await fetch('/api/deployments');
            this.deployments = await response.json();
            this.updateDeploymentsList();
            this.updateLogDeploymentSelect();
        } catch (error) {
            console.error('Error loading deployments:', error);
        }
    }
    
    async loadResources() {
        try {
            const response = await fetch('/api/aws/resources?environment=beta');
            const resources = await response.json();
            this.updateResourcesList(resources);
        } catch (error) {
            console.error('Error loading resources:', error);
        }
    }
    
    async loadMonitoring() {
        try {
            // Load different metrics
            const [cpuResponse, memoryResponse, requestsResponse] = await Promise.all([
                fetch('/api/metrics?metric=CPUUtilization'),
                fetch('/api/metrics?metric=MemoryUtilization'),
                fetch('/api/metrics?metric=RequestCount&namespace=AWS/ApplicationELB')
            ]);
            
            const cpuData = await cpuResponse.json();
            const memoryData = await memoryResponse.json();
            const requestsData = await requestsResponse.json();
            
            this.updateMonitoringCharts({
                cpu: cpuData,
                memory: memoryData,
                requests: requestsData
            });
            
        } catch (error) {
            console.error('Error loading monitoring data:', error);
        }
    }
    
    async loadCostAnalysis() {
        try {
            const response = await fetch('/api/cost-estimate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    domains: ['DMLog', 'PersonalLog'],
                    instanceClass: 'balanced',
                    autoScaling: true,
                    maxInstances: 3,
                    costOptimized: true
                })
            });
            
            const costData = await response.json();
            this.updateCostCharts(costData);
            
        } catch (error) {
            console.error('Error loading cost data:', error);
        }
    }
    
    updateSystemStatus() {
        if (!this.systemStatus) return;
        
        const statusEl = document.getElementById('system-status');
        const dot = statusEl.querySelector('.status-dot');
        
        if (this.systemStatus.status === 'healthy') {
            dot.className = 'status-dot status-completed';
            statusEl.innerHTML = `
                <div class="flex items-center">
                    <div class="status-dot status-completed"></div>
                    System: Healthy
                </div>
            `;
        } else if (this.systemStatus.status === 'degraded') {
            dot.className = 'status-dot status-running';
            statusEl.innerHTML = `
                <div class="flex items-center">
                    <div class="status-dot status-running"></div>
                    System: Degraded
                </div>
            `;
        } else {
            dot.className = 'status-dot status-failed';
            statusEl.innerHTML = `
                <div class="flex items-center">
                    <div class="status-dot status-failed"></div>
                    System: Error
                </div>
            `;
        }
    }
    
    updateDashboardCards() {
        // Active deployments
        const activeCount = this.deployments.filter(d => d.status === 'running').length;
        document.getElementById('active-deployments-count').textContent = activeCount;
        
        // Running instances (placeholder)
        document.getElementById('running-instances-count').textContent = '0';
        
        // Monthly cost (placeholder)
        document.getElementById('monthly-cost').textContent = '$0';
        
        // System health
        const health = this.systemStatus?.status === 'healthy' ? '✅' : '⚠️';
        document.getElementById('system-health').textContent = health;
    }
    
    updateDeploymentsList() {
        const container = document.getElementById('deployments-list') || document.getElementById('recent-deployments');
        if (!container) return;
        
        if (this.deployments.length === 0) {
            container.innerHTML = '<div class="text-gray-500 text-center py-4">No deployments found</div>';
            return;
        }
        
        const isRecentList = container.id === 'recent-deployments';
        const deploymentsToShow = isRecentList ? this.deployments.slice(0, 5) : this.deployments;
        
        container.innerHTML = deploymentsToShow.map(deployment => {
            const statusClass = `status-${deployment.status}`;
            const progress = deployment.current_step || 0;
            const totalSteps = deployment.total_steps || 100;
            const progressPercent = Math.round((progress / totalSteps) * 100);
            
            if (isRecentList) {
                return `
                    <div class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg cursor-pointer" onclick="dashboard.showDeploymentDetails('${deployment.deployment_id}')">
                        <div class="flex items-center space-x-3">
                            <div class="status-dot ${statusClass}"></div>
                            <div>
                                <div class="font-medium text-sm">${deployment.deployment_id}</div>
                                <div class="text-xs text-gray-500">${deployment.environment || 'Unknown'}</div>
                            </div>
                        </div>
                        <div class="text-xs text-gray-500">
                            ${this.formatTime(deployment.started_at)}
                        </div>
                    </div>
                `;
            } else {
                return `
                    <div class="p-6 hover:bg-gray-50 cursor-pointer" onclick="dashboard.showDeploymentDetails('${deployment.deployment_id}')">
                        <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center space-x-3">
                                <div class="status-dot ${statusClass}"></div>
                                <div>
                                    <div class="font-semibold">${deployment.deployment_id}</div>
                                    <div class="text-sm text-gray-500">${deployment.environment || 'Unknown Environment'}</div>
                                </div>
                            </div>
                            <div class="text-sm text-gray-500">
                                Started ${this.formatTime(deployment.started_at)}
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            <div class="flex justify-between text-sm mb-1">
                                <span>Progress</span>
                                <span>${progressPercent}%</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-2">
                                <div class="progress-bar h-2 rounded-full" style="width: ${progressPercent}%"></div>
                            </div>
                        </div>
                        
                        <div class="mt-3 flex justify-between items-center">
                            <div class="flex space-x-2">
                                <span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">${deployment.status}</span>
                                ${deployment.config?.domains ? deployment.config.domains.map(d => `<span class="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">${d}</span>`).join('') : ''}
                            </div>
                            <div class="flex space-x-2">
                                <button class="text-blue-600 hover:text-blue-800 text-sm">View Logs</button>
                                ${deployment.status === 'running' ? '<button class="text-red-600 hover:text-red-800 text-sm">Cancel</button>' : ''}
                            </div>
                        </div>
                    </div>
                `;
            }
        }).join('');
    }
    
    updateResourcesList(resources) {
        // EC2 Instances
        const ec2Container = document.getElementById('ec2-instances');
        if (ec2Container && resources.ec2Instances) {
            if (resources.ec2Instances.length === 0) {
                ec2Container.innerHTML = '<div class="text-gray-500">No instances found</div>';
            } else {
                ec2Container.innerHTML = resources.ec2Instances.map(instance => `
                    <div class="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <div>
                            <div class="font-mono text-sm">${instance.instanceId}</div>
                            <div class="text-xs text-gray-500">${instance.instanceType}</div>
                        </div>
                        <span class="px-2 py-1 text-xs ${instance.state === 'running' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'} rounded-full">
                            ${instance.state}
                        </span>
                    </div>
                `).join('');
            }
        }
        
        // Auto Scaling Groups
        const asgContainer = document.getElementById('asg-list');
        if (asgContainer && resources.autoScalingGroups) {
            if (resources.autoScalingGroups.length === 0) {
                asgContainer.innerHTML = '<div class="text-gray-500">No ASGs found</div>';
            } else {
                asgContainer.innerHTML = resources.autoScalingGroups.map(asg => `
                    <div class="p-2 bg-gray-50 rounded">
                        <div class="font-medium text-sm">${asg.Name}</div>
                        <div class="text-xs text-gray-500">
                            ${asg.Instances}/${asg.Desired} instances
                            (${asg.Min}-${asg.Max})
                        </div>
                    </div>
                `).join('');
            }
        }
        
        // Load Balancers
        const albContainer = document.getElementById('alb-list');
        if (albContainer && resources.loadBalancers) {
            if (resources.loadBalancers.length === 0) {
                albContainer.innerHTML = '<div class="text-gray-500">No load balancers found</div>';
            } else {
                albContainer.innerHTML = resources.loadBalancers.map(alb => `
                    <div class="p-2 bg-gray-50 rounded">
                        <div class="font-medium text-sm">${alb.Name}</div>
                        <div class="text-xs text-gray-500">${alb.Type} - ${alb.State}</div>
                    </div>
                `).join('');
            }
        }
    }
    
    initializeDashboardCharts() {
        const ctx = document.getElementById('metrics-chart');
        if (!ctx) return;
        
        if (this.charts.metrics) {
            this.charts.metrics.destroy();
        }
        
        this.charts.metrics = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: 12}, (_, i) => `${i * 5}m ago`).reverse(),
                datasets: [{
                    label: 'CPU Usage (%)',
                    data: Array.from({length: 12}, () => Math.random() * 100),
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.1
                }, {
                    label: 'Memory Usage (%)',
                    data: Array.from({length: 12}, () => Math.random() * 100),
                    borderColor: 'rgb(16, 185, 129)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
    
    updateMonitoringCharts(data) {
        // CPU Chart
        this.updateChart('cpu-chart', 'cpu', {
            label: 'CPU Utilization (%)',
            data: data.cpu.datapoints || [],
            color: 'rgb(59, 130, 246)'
        });
        
        // Memory Chart
        this.updateChart('memory-chart', 'memory', {
            label: 'Memory Utilization (%)',
            data: data.memory.datapoints || [],
            color: 'rgb(16, 185, 129)'
        });
        
        // Requests Chart
        this.updateChart('requests-chart', 'requests', {
            label: 'Requests per Minute',
            data: data.requests.datapoints || [],
            color: 'rgb(139, 92, 246)'
        });
    }
    
    updateChart(canvasId, chartKey, config) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        if (this.charts[chartKey]) {
            this.charts[chartKey].destroy();
        }
        
        const labels = config.data.map(point => 
            new Date(point.Timestamp).toLocaleTimeString()
        );
        const values = config.data.map(point => point.Average || point.Sum || 0);
        
        this.charts[chartKey] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: config.label,
                    data: values,
                    borderColor: config.color,
                    backgroundColor: config.color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    updateCostCharts(costData) {
        // Cost breakdown pie chart
        const costBreakdownCtx = document.getElementById('cost-chart');
        if (costBreakdownCtx) {
            if (this.charts.costBreakdown) {
                this.charts.costBreakdown.destroy();
            }
            
            this.charts.costBreakdown = new Chart(costBreakdownCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Compute', 'Storage', 'Network'],
                    datasets: [{
                        data: [
                            costData.breakdown.compute,
                            costData.breakdown.storage,
                            costData.breakdown.network
                        ],
                        backgroundColor: [
                            'rgb(59, 130, 246)',
                            'rgb(16, 185, 129)',
                            'rgb(245, 158, 11)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
        
        // Cost trend chart
        const costTrendCtx = document.getElementById('cost-trend-chart');
        if (costTrendCtx) {
            if (this.charts.costTrend) {
                this.charts.costTrend.destroy();
            }
            
            // Generate mock trend data
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
            const trendData = months.map(() => costData.monthly * (0.8 + Math.random() * 0.4));
            
            this.charts.costTrend = new Chart(costTrendCtx, {
                type: 'bar',
                data: {
                    labels: months,
                    datasets: [{
                        label: 'Monthly Cost ($)',
                        data: trendData,
                        backgroundColor: 'rgba(59, 130, 246, 0.8)',
                        borderColor: 'rgb(59, 130, 246)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // Update cost recommendations
        this.updateCostRecommendations();
    }
    
    updateCostRecommendations() {
        const container = document.getElementById('cost-recommendations');
        if (!container) return;
        
        const recommendations = [
            {
                type: 'optimization',
                title: 'Enable Auto-Scaling',
                description: 'Save up to 30% by automatically scaling down during off-hours',
                savings: '$150/month',
                priority: 'high'
            },
            {
                type: 'reservation',
                title: 'Reserved Instances',
                description: 'Switch to 1-year reserved instances for predictable workloads',
                savings: '$80/month',
                priority: 'medium'
            },
            {
                type: 'storage',
                title: 'S3 Lifecycle Policies',
                description: 'Automatically move old data to cheaper storage tiers',
                savings: '$25/month',
                priority: 'low'
            }
        ];
        
        container.innerHTML = recommendations.map(rec => {
            const priorityColors = {
                high: 'bg-red-100 text-red-800',
                medium: 'bg-yellow-100 text-yellow-800',
                low: 'bg-green-100 text-green-800'
            };
            
            return `
                <div class="flex items-start p-4 bg-gray-50 rounded-lg">
                    <div class="flex-shrink-0 mr-4">
                        <i class="fas fa-lightbulb text-yellow-500 text-lg"></i>
                    </div>
                    <div class="flex-1">
                        <div class="flex items-center justify-between mb-1">
                            <h4 class="font-medium text-gray-900">${rec.title}</h4>
                            <span class="px-2 py-1 text-xs ${priorityColors[rec.priority]} rounded-full">${rec.priority}</span>
                        </div>
                        <p class="text-sm text-gray-600 mb-2">${rec.description}</p>
                        <div class="flex items-center justify-between">
                            <span class="text-sm font-medium text-green-600">💰 Potential savings: ${rec.savings}</span>
                            <button class="text-sm text-blue-600 hover:text-blue-800">Apply</button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    updateLogDeploymentSelect() {
        const select = document.getElementById('log-deployment-select');
        if (!select) return;
        
        select.innerHTML = '<option value="">Select deployment...</option>' + 
            this.deployments.map(d => `<option value="${d.deployment_id}">${d.deployment_id} (${d.environment})</option>`).join('');
    }
    
    async loadDeploymentLogs(deploymentId) {
        if (!deploymentId) {
            this.clearLogs();
            return;
        }
        
        try {
            const response = await fetch(`/api/deployments/${deploymentId}/logs`);
            const data = await response.json();
            
            const container = document.getElementById('logs-container');
            if (data.logs && data.logs.length > 0) {
                container.innerHTML = data.logs.map(log => {
                    let logClass = '';
                    if (log.includes('ERROR')) logClass = 'log-error';
                    else if (log.includes('WARNING')) logClass = 'log-warning';
                    else if (log.includes('SUCCESS')) logClass = 'log-success';
                    else logClass = 'log-info';
                    
                    return `<div class="${logClass}">${this.escapeHtml(log)}</div>`;
                }).join('');
                
                // Scroll to bottom
                container.scrollTop = container.scrollHeight;
            } else {
                container.innerHTML = '<div class="text-gray-400">No logs available for this deployment.</div>';
            }
        } catch (error) {
            console.error('Error loading logs:', error);
            const container = document.getElementById('logs-container');
            container.innerHTML = '<div class="log-error">Error loading logs: ' + error.message + '</div>';
        }
    }
    
    clearLogs() {
        const container = document.getElementById('logs-container');
        container.innerHTML = '<div class="text-gray-400">Logs cleared.</div>';
    }
    
    showDeploymentDetails(deploymentId) {
        const deployment = this.deployments.find(d => d.deployment_id === deploymentId);
        if (!deployment) return;
        
        const modal = document.getElementById('deployment-modal');
        const content = document.getElementById('deployment-modal-content');
        
        const progress = Math.round((deployment.current_step / deployment.total_steps) * 100) || 0;
        
        content.innerHTML = `
            <div class="space-y-4">
                <div>
                    <h4 class="font-semibold text-gray-800 mb-2">Deployment Information</h4>
                    <dl class="grid grid-cols-2 gap-2 text-sm">
                        <dt class="text-gray-600">ID:</dt>
                        <dd class="font-mono">${deployment.deployment_id}</dd>
                        <dt class="text-gray-600">Environment:</dt>
                        <dd>${deployment.environment || 'Unknown'}</dd>
                        <dt class="text-gray-600">Status:</dt>
                        <dd><span class="px-2 py-1 text-xs bg-${deployment.status === 'running' ? 'yellow' : deployment.status === 'completed' ? 'green' : 'red'}-100 text-${deployment.status === 'running' ? 'yellow' : deployment.status === 'completed' ? 'green' : 'red'}-800 rounded-full">${deployment.status}</span></dd>
                        <dt class="text-gray-600">Started:</dt>
                        <dd>${this.formatTime(deployment.started_at)}</dd>
                    </dl>
                </div>
                
                <div>
                    <h4 class="font-semibold text-gray-800 mb-2">Progress</h4>
                    <div class="w-full bg-gray-200 rounded-full h-3">
                        <div class="progress-bar h-3 rounded-full" style="width: ${progress}%"></div>
                    </div>
                    <p class="text-sm text-gray-600 mt-1">${progress}% complete (${deployment.current_step}/${deployment.total_steps} steps)</p>
                </div>
                
                <div>
                    <h4 class="font-semibold text-gray-800 mb-2">Stages</h4>
                    <div class="space-y-2 max-h-48 overflow-y-auto">
                        ${Object.entries(deployment.stages || {}).map(([stageName, stage]) => `
                            <div class="flex items-center justify-between p-2 bg-gray-50 rounded">
                                <div class="flex items-center space-x-2">
                                    <div class="status-dot status-${stage.status}"></div>
                                    <span class="text-sm">${stageName.replace(/_/g, ' ')}</span>
                                </div>
                                <span class="text-xs text-gray-500">${stage.progress}%</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                ${deployment.errors && deployment.errors.length > 0 ? `
                    <div>
                        <h4 class="font-semibold text-red-600 mb-2">Errors</h4>
                        <div class="space-y-1 max-h-32 overflow-y-auto">
                            ${deployment.errors.map(error => `
                                <div class="text-sm text-red-600 p-2 bg-red-50 rounded">
                                    ${error.message}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
        
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
    
    closeModal() {
        const modal = document.getElementById('deployment-modal');
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
    
    showDeploymentWizard() {
        this.showSection('wizard');
    }
    
    async startInteractiveWizard() {
        try {
            const response = await fetch('/api/wizard', { method: 'POST' });
            const data = await response.json();
            
            this.showNotification('Interactive wizard started!', 'info');
            
            // In a real implementation, this would open a terminal or redirect to the wizard
            const wizardContent = document.getElementById('wizard-content');
            wizardContent.innerHTML = `
                <div class="text-center py-8">
                    <div class="mb-4">
                        <i class="fas fa-terminal text-4xl text-blue-500"></i>
                    </div>
                    <h3 class="text-lg font-semibold mb-2">Terminal Wizard Session</h3>
                    <p class="text-gray-600 mb-4">Session ID: ${data.sessionId}</p>
                    <p class="text-sm text-gray-500 mb-6">
                        The interactive wizard is running in your terminal. Please check your terminal window to continue with the guided deployment setup.
                    </p>
                    <button id="wizard-terminal-btn" class="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-lg">
                        <i class="fas fa-external-link-alt mr-2"></i>
                        Open in Terminal
                    </button>
                </div>
            `;
        } catch (error) {
            console.error('Error starting wizard:', error);
            this.showNotification('Error starting wizard: ' + error.message, 'error');
        }
    }
    
    filterDeployments(status) {
        // This would filter the deployments list based on status
        console.log('Filtering deployments by:', status);
        // Implementation would update the deployments list display
    }
    
    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        
        const notification = document.createElement('div');
        notification.className = `notification bg-white border-l-4 ${
            type === 'success' ? 'border-green-500' :
            type === 'error' ? 'border-red-500' :
            type === 'warning' ? 'border-yellow-500' :
            'border-blue-500'
        } rounded-r-lg shadow-lg p-4`;
        
        const icon = {
            success: 'fas fa-check-circle text-green-500',
            error: 'fas fa-exclamation-circle text-red-500',
            warning: 'fas fa-exclamation-triangle text-yellow-500',
            info: 'fas fa-info-circle text-blue-500'
        }[type];
        
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="${icon} mr-3"></i>
                <div class="flex-1">
                    <p class="text-sm font-medium text-gray-900">${message}</p>
                </div>
                <button class="ml-3 text-gray-400 hover:text-gray-600" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        container.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.parentElement.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }
    
    refreshData() {
        this.loadSectionData(this.currentSection);
        this.showNotification('Data refreshed', 'success');
    }
    
    formatTime(timestamp) {
        if (!timestamp) return 'Unknown';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }
    
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    // WebSocket message sending
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected');
        }
    }
    
    // Update deployment status in real-time
    updateDeploymentStatus(deploymentId, status) {
        const index = this.deployments.findIndex(d => d.deployment_id === deploymentId);
        if (index !== -1) {
            this.deployments[index] = { ...this.deployments[index], ...status };
            this.updateDeploymentsList();
            this.updateDashboardCards();
        }
    }
    
    // Handle deployment output
    appendDeploymentOutput(deploymentId, output, stream) {
        // If logs section is showing this deployment, append to logs
        const logsContainer = document.getElementById('logs-container');
        const selectedDeployment = document.getElementById('log-deployment-select')?.value;
        
        if (selectedDeployment === deploymentId && logsContainer) {
            const logClass = stream === 'stderr' ? 'log-error' : 'log-info';
            const logElement = document.createElement('div');
            logElement.className = logClass;
            logElement.textContent = output.trim();
            
            logsContainer.appendChild(logElement);
            logsContainer.scrollTop = logsContainer.scrollHeight;
        }
    }
    
    // Handle deployment completion
    handleDeploymentFinished(deploymentId, status) {
        const message = status === 'completed' ? 
            `Deployment ${deploymentId} completed successfully!` :
            `Deployment ${deploymentId} failed!`;
        
        const notificationType = status === 'completed' ? 'success' : 'error';
        this.showNotification(message, notificationType);
        
        // Refresh deployments list
        this.loadDeployments();
    }
}

// Initialize dashboard when DOM is ready
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new DeploymentDashboard();
    
    // Make dashboard available globally for onclick handlers
    window.dashboard = dashboard;
});