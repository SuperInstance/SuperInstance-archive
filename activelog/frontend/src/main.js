/**
 * ActiveLog.ai Frontend Application
 * Main entry point
 */

import { App } from './components/App.js';
import { AuthManager } from './utils/auth.js';
import { WebSocketManager } from './utils/websocket.js';
import { ServiceStatusManager } from './utils/serviceStatus.js';
import { LoadingProgress } from './components/common/LoadingProgress.js';

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    const loadingProgress = new LoadingProgress();
    
    try {
        // Show loading progress
        loadingProgress.show();
        
        // Step 1: Initialize service status monitoring
        loadingProgress.updateProgress(10, 'Initializing service monitoring...');
        await ServiceStatusManager.init();
        
        // Step 2: Check service availability
        loadingProgress.updateProgress(25, 'Checking service availability...');
        await ServiceStatusManager.checkAllServices();
        const serviceStatus = ServiceStatusManager.getStatus();
        loadingProgress.updateProgress(40, 'Services checked', serviceStatus);
        
        // Step 3: Initialize authentication
        loadingProgress.updateProgress(50, 'Initializing authentication...');
        try {
            await AuthManager.init();
            loadingProgress.updateProgress(65, 'Authentication ready');
        } catch (authError) {
            console.warn('Authentication initialization failed:', authError);
            loadingProgress.updateProgress(65, 'Authentication unavailable - continuing in demo mode');
            ServiceStatusManager.enableMockMode();
        }
        
        // Step 4: Initialize WebSocket connection (non-blocking)
        loadingProgress.updateProgress(75, 'Establishing real-time connection...');
        try {
            WebSocketManager.init();
            loadingProgress.updateProgress(85, 'Real-time connection ready');
        } catch (wsError) {
            console.warn('WebSocket initialization failed:', wsError);
            loadingProgress.updateProgress(85, 'Real-time features unavailable');
        }
        
        // Step 5: Initialize main app
        loadingProgress.updateProgress(90, 'Loading application interface...');
        const app = new App();
        await app.init();
        
        // Final step
        loadingProgress.updateProgress(100, 'Application ready!');
        
        // Small delay to show completion
        setTimeout(() => {
            loadingProgress.hide();
            console.log('ActiveLog.ai Frontend initialized successfully');
        }, 500);
        
    } catch (error) {
        console.error('Failed to initialize application:', error);
        loadingProgress.showError(error);
        
        // Also show a fallback error page after a delay
        setTimeout(() => {
            loadingProgress.hide();
            document.body.innerHTML = `
                <div class="error-container" style="
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    padding: 20px;
                    text-align: center;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                ">
                    <div style="
                        background: rgba(255, 255, 255, 0.1);
                        padding: 40px;
                        border-radius: 15px;
                        backdrop-filter: blur(10px);
                        max-width: 500px;
                    ">
                        <h1 style="margin: 0 0 20px 0; font-size: 2.5em;">⚠️ Startup Error</h1>
                        <p style="margin: 0 0 15px 0; font-size: 1.2em;">Failed to initialize ActiveLog.ai</p>
                        <div style="
                            background: rgba(255, 107, 107, 0.2);
                            padding: 15px;
                            border-radius: 8px;
                            border: 1px solid rgba(255, 107, 107, 0.3);
                            margin: 20px 0;
                            font-family: monospace;
                        ">${error.message}</div>
                        <button onclick="location.reload()" style="
                            background: #4facfe;
                            color: white;
                            border: none;
                            padding: 12px 24px;
                            border-radius: 8px;
                            cursor: pointer;
                            font-size: 1.1em;
                            margin: 0 10px;
                            transition: background 0.3s ease;
                        " onmouseover="this.style.background='#2196f3'" 
                           onmouseout="this.style.background='#4facfe'">Reload Application</button>
                        <button onclick="ServiceStatusManager?.enableMockMode(); location.reload()" style="
                            background: transparent;
                            color: white;
                            border: 1px solid rgba(255, 255, 255, 0.5);
                            padding: 12px 24px;
                            border-radius: 8px;
                            cursor: pointer;
                            font-size: 1.1em;
                            margin: 0 10px;
                            transition: all 0.3s ease;
                        " onmouseover="this.style.background='rgba(255, 255, 255, 0.1)'" 
                           onmouseout="this.style.background='transparent'">Try Demo Mode</button>
                    </div>
                </div>
            `;
        }, 3000);
    }
});

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});