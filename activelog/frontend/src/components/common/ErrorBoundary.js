/**
 * Error Boundary Component
 * Catches JavaScript errors anywhere in the component tree
 */

export class ErrorBoundary {
    constructor(options = {}) {
        this.options = {
            fallbackUI: options.fallbackUI || this.getDefaultFallbackUI,
            onError: options.onError || this.defaultErrorHandler,
            context: options.context || 'Unknown Component'
        };
        this.hasError = false;
        this.error = null;
        this.errorInfo = null;
    }

    wrap(element, renderFunction) {
        try {
            // If there's an existing error, show fallback UI
            if (this.hasError) {
                return this.renderFallbackUI();
            }

            // Try to render the component
            const result = renderFunction();
            
            // Handle both sync and async rendering
            if (result instanceof Promise) {
                return result.catch(error => {
                    this.handleError(error);
                    return this.renderFallbackUI();
                });
            }
            
            return result;
        } catch (error) {
            this.handleError(error);
            return this.renderFallbackUI();
        }
    }

    handleError(error, errorInfo = null) {
        this.hasError = true;
        this.error = error;
        this.errorInfo = errorInfo;

        // Log error
        console.error(`Error in ${this.options.context}:`, error);
        if (errorInfo) {
            console.error('Error Info:', errorInfo);
        }

        // Call custom error handler
        this.options.onError(error, errorInfo, this.options.context);
    }

    renderFallbackUI() {
        const fallbackElement = document.createElement('div');
        fallbackElement.innerHTML = this.options.fallbackUI(this.error, this.options.context);
        return fallbackElement;
    }

    getDefaultFallbackUI(error, context) {
        const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

        return `
            <div class="error-boundary" style="
                padding: 20px;
                margin: 10px 0;
                background: #fff5f5;
                border: 1px solid #fed7d7;
                border-radius: 8px;
                color: #c53030;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            ">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                    <span style="font-size: 24px;">⚠️</span>
                    <div>
                        <h3 style="margin: 0; color: #c53030; font-size: 16px;">Something went wrong</h3>
                        <p style="margin: 5px 0 0 0; font-size: 14px; color: #e53e3e;">Error in ${context}</p>
                    </div>
                </div>
                
                ${isDevelopment ? `
                    <details style="margin: 15px 0;">
                        <summary style="cursor: pointer; font-weight: 600; color: #c53030;">
                            Technical Details
                        </summary>
                        <div style="
                            margin-top: 10px;
                            padding: 15px;
                            background: #fed7d7;
                            border-radius: 4px;
                            font-family: monospace;
                            font-size: 12px;
                            white-space: pre-wrap;
                            overflow-x: auto;
                        ">${error?.message || 'Unknown error'}\n\n${error?.stack || ''}</div>
                    </details>
                ` : ''}
                
                <div style="margin-top: 15px;">
                    <button onclick="this.closest('.error-boundary').style.display='none'" style="
                        background: #c53030;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        margin-right: 10px;
                        font-size: 14px;
                    ">Hide Error</button>
                    
                    <button onclick="location.reload()" style="
                        background: #2d3748;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 14px;
                    ">Reload Page</button>
                </div>
            </div>
        `;
    }

    defaultErrorHandler(error, errorInfo, context) {
        // Send error to logging service (if available)
        const errorReport = {
            message: error.message,
            stack: error.stack,
            context: context,
            url: window.location.href,
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString(),
            errorInfo: errorInfo
        };

        // Try to send to backend error reporting
        try {
            fetch('/api/errors', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(errorReport)
            }).catch(() => {
                // Silently fail if error reporting is not available
            });
        } catch (e) {
            // Silently fail
        }

        // Store error locally for debugging
        const errors = JSON.parse(localStorage.getItem('app_errors') || '[]');
        errors.push(errorReport);
        
        // Keep only last 10 errors
        if (errors.length > 10) {
            errors.splice(0, errors.length - 10);
        }
        
        localStorage.setItem('app_errors', JSON.stringify(errors));
    }

    reset() {
        this.hasError = false;
        this.error = null;
        this.errorInfo = null;
    }

    // Static method to create a wrapped component
    static wrap(renderFunction, options = {}) {
        const errorBoundary = new ErrorBoundary(options);
        return () => errorBoundary.wrap(null, renderFunction);
    }

    // Static method to wrap an async function
    static wrapAsync(asyncFunction, options = {}) {
        const errorBoundary = new ErrorBoundary(options);
        
        return async (...args) => {
            try {
                return await asyncFunction(...args);
            } catch (error) {
                errorBoundary.handleError(error);
                
                // Show user-friendly error notification
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #fed7d7;
                    color: #c53030;
                    padding: 15px 20px;
                    border-radius: 8px;
                    border: 1px solid #feb2b2;
                    z-index: 10000;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    max-width: 400px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                    animation: slideIn 0.3s ease;
                `;
                
                notification.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 20px;">⚠️</span>
                        <div>
                            <div style="font-weight: 600;">Operation Failed</div>
                            <div style="font-size: 14px; margin-top: 2px;">
                                ${error.message || 'An unexpected error occurred'}
                            </div>
                        </div>
                        <button onclick="this.parentNode.parentNode.remove()" style="
                            background: none;
                            border: none;
                            color: #c53030;
                            cursor: pointer;
                            font-size: 18px;
                            margin-left: auto;
                        ">×</button>
                    </div>
                `;

                document.body.appendChild(notification);
                
                // Auto remove after 5 seconds
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 5000);

                // Re-throw if needed for further handling
                throw error;
            }
        };
    }
}

// Global error boundary for uncaught errors
window.addEventListener('error', (event) => {
    const errorBoundary = new ErrorBoundary({
        context: 'Global Error Handler'
    });
    errorBoundary.handleError(event.error || new Error(event.message));
});

// Global error boundary for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    const errorBoundary = new ErrorBoundary({
        context: 'Unhandled Promise Rejection'
    });
    errorBoundary.handleError(event.reason || new Error('Unhandled promise rejection'));
});

// Add styles for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(100%); }
        to { opacity: 1; transform: translateX(0); }
    }
`;
document.head.appendChild(style);