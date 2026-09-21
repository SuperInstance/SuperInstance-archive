/**
 * Loading Progress Indicator
 */

export class LoadingProgress {
    constructor() {
        this.steps = [
            { name: 'Connecting to services...', duration: 1000 },
            { name: 'Checking authentication...', duration: 800 },
            { name: 'Loading user preferences...', duration: 600 },
            { name: 'Initializing interface...', duration: 400 }
        ];
        this.currentStep = 0;
        this.element = null;
    }

    show() {
        // Remove any existing progress indicator
        this.hide();

        // Create progress container
        this.element = document.createElement('div');
        this.element.id = 'loading-progress';
        this.element.innerHTML = `
            <div class="loading-container">
                <div class="loading-header">
                    <h1>ActiveLog.ai</h1>
                    <div class="loading-logo">📊</div>
                </div>
                
                <div class="loading-content">
                    <div class="progress-bar-container">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progress-fill"></div>
                        </div>
                        <div class="progress-percentage" id="progress-percentage">0%</div>
                    </div>
                    
                    <div class="loading-step" id="loading-step">Starting up...</div>
                    
                    <div class="service-status" id="service-status">
                        <div class="status-item">
                            <span class="status-icon">🔄</span>
                            <span class="status-text">Checking services...</span>
                        </div>
                    </div>
                    
                    <div class="loading-tips">
                        <div class="tip" id="loading-tip">
                            💡 Tip: Use Ctrl+K to open the command palette for quick navigation
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add styles
        this.element.innerHTML += this.getStyles();
        
        document.body.appendChild(this.element);
        
        return this.element;
    }

    updateProgress(percentage, step, serviceStatus = null) {
        const progressFill = document.getElementById('progress-fill');
        const progressPercentage = document.getElementById('progress-percentage');
        const loadingStep = document.getElementById('loading-step');
        const serviceStatusEl = document.getElementById('service-status');

        if (progressFill) {
            progressFill.style.width = `${percentage}%`;
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = `${Math.round(percentage)}%`;
        }
        
        if (loadingStep && step) {
            loadingStep.textContent = step;
        }

        if (serviceStatus && serviceStatusEl) {
            this.updateServiceStatus(serviceStatus);
        }

        // Update tips occasionally
        if (Math.random() < 0.3) {
            this.updateTip();
        }
    }

    updateServiceStatus(status) {
        const serviceStatusEl = document.getElementById('service-status');
        if (!serviceStatusEl) return;

        let statusHtml = '';
        const services = status.services || {};
        
        Object.entries(services).forEach(([name, service]) => {
            let icon = '🔄';
            let statusText = 'Checking...';
            
            switch (service.status) {
                case 'online':
                    icon = '🟢';
                    statusText = 'Online';
                    break;
                case 'offline':
                    icon = '🔴';
                    statusText = 'Offline';
                    break;
                case 'error':
                    icon = '🟡';
                    statusText = 'Error';
                    break;
            }

            statusHtml += `
                <div class="status-item">
                    <span class="status-icon">${icon}</span>
                    <span class="status-text">${name}: ${statusText}</span>
                </div>
            `;
        });

        if (status.mockMode) {
            statusHtml += `
                <div class="status-item mock-mode">
                    <span class="status-icon">🧪</span>
                    <span class="status-text">Demo mode active - Limited functionality</span>
                </div>
            `;
        }

        serviceStatusEl.innerHTML = statusHtml;
    }

    updateTip() {
        const tips = [
            '💡 Tip: Use Ctrl+K to open the command palette for quick navigation',
            '🔍 Tip: The search bar supports semantic queries and file content search',
            '📁 Tip: Drag and drop files to upload them instantly',
            '🏷️ Tip: Tag your files for better organization and discovery',
            '⚡ Tip: Use keyboard shortcuts to navigate faster',
            '🎯 Tip: Filter files by type, date, or custom criteria',
            '🔄 Tip: Files are automatically synced across all your devices'
        ];

        const tipEl = document.getElementById('loading-tip');
        if (tipEl) {
            const randomTip = tips[Math.floor(Math.random() * tips.length)];
            tipEl.textContent = randomTip;
        }
    }

    async animateSteps() {
        let totalProgress = 0;
        const stepIncrement = 100 / this.steps.length;

        for (let i = 0; i < this.steps.length; i++) {
            const step = this.steps[i];
            this.updateProgress(totalProgress, step.name);
            
            // Animate progress for this step
            const startProgress = totalProgress;
            const endProgress = totalProgress + stepIncrement;
            const duration = step.duration;
            const startTime = Date.now();

            await new Promise(resolve => {
                const animate = () => {
                    const elapsed = Date.now() - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    const currentProgress = startProgress + (endProgress - startProgress) * progress;
                    
                    this.updateProgress(currentProgress, step.name);
                    
                    if (progress < 1) {
                        requestAnimationFrame(animate);
                    } else {
                        totalProgress = endProgress;
                        resolve();
                    }
                };
                animate();
            });
        }

        this.updateProgress(100, 'Ready!');
    }

    showError(error) {
        const loadingStep = document.getElementById('loading-step');
        if (loadingStep) {
            loadingStep.innerHTML = `
                <div class="error-message">
                    ⚠️ ${error.message || 'Startup failed'}
                    <button onclick="location.reload()" class="retry-button">Retry</button>
                </div>
            `;
        }
    }

    hide() {
        const existing = document.getElementById('loading-progress');
        if (existing) {
            existing.remove();
        }
        this.element = null;
    }

    getStyles() {
        return `
            <style>
                #loading-progress {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 10000;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                    color: white;
                }

                .loading-container {
                    text-align: center;
                    max-width: 500px;
                    padding: 40px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 25px 45px rgba(0, 0, 0, 0.1);
                }

                .loading-header {
                    margin-bottom: 40px;
                }

                .loading-header h1 {
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 300;
                    margin-bottom: 10px;
                }

                .loading-logo {
                    font-size: 3em;
                    margin-bottom: 20px;
                    animation: pulse 2s ease-in-out infinite;
                }

                @keyframes pulse {
                    0%, 100% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.1); opacity: 0.8; }
                }

                .progress-bar-container {
                    margin: 30px 0;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                }

                .progress-bar {
                    flex: 1;
                    height: 8px;
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 10px;
                    overflow: hidden;
                }

                .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
                    border-radius: 10px;
                    transition: width 0.3s ease;
                    box-shadow: 0 0 10px rgba(79, 172, 254, 0.5);
                }

                .progress-percentage {
                    font-weight: 600;
                    font-size: 1.1em;
                    min-width: 50px;
                }

                .loading-step {
                    font-size: 1.2em;
                    margin: 20px 0;
                    min-height: 1.5em;
                    animation: fadeIn 0.5s ease-in-out;
                }

                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .service-status {
                    margin: 25px 0;
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 15px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }

                .status-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin: 8px 0;
                    font-size: 0.95em;
                }

                .status-icon {
                    font-size: 1.2em;
                }

                .mock-mode {
                    background: rgba(255, 193, 7, 0.2);
                    padding: 8px 12px;
                    border-radius: 8px;
                    border: 1px solid rgba(255, 193, 7, 0.3);
                }

                .loading-tips {
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid rgba(255, 255, 255, 0.2);
                }

                .tip {
                    font-size: 0.9em;
                    opacity: 0.8;
                    font-style: italic;
                    animation: fadeIn 0.5s ease-in-out;
                }

                .error-message {
                    color: #ff6b6b;
                    background: rgba(255, 107, 107, 0.1);
                    padding: 15px;
                    border-radius: 10px;
                    border: 1px solid rgba(255, 107, 107, 0.3);
                    margin: 10px 0;
                }

                .retry-button {
                    background: #4facfe;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 5px;
                    margin-left: 10px;
                    cursor: pointer;
                    font-size: 0.9em;
                    transition: background 0.3s ease;
                }

                .retry-button:hover {
                    background: #2196f3;
                }

                /* Mobile responsiveness */
                @media (max-width: 600px) {
                    .loading-container {
                        margin: 20px;
                        padding: 30px 20px;
                    }
                    
                    .loading-header h1 {
                        font-size: 2em;
                    }
                    
                    .loading-logo {
                        font-size: 2.5em;
                    }
                }
            </style>
        `;
    }
}