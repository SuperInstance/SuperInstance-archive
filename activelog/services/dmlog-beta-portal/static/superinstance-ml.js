/**
 * SuperInstance ML Integration
 * Universal client-side ML integration for all apps
 * Provides real-time input interpretation, UI optimization, and learning
 */

class SuperInstanceML {
    constructor(userId, appName) {
        this.userId = userId;
        this.appName = appName;
        this.mlActive = false;
        this.suggestions = [];
        this.inputBuffer = new Map(); // Track input corrections
        this.navigationSession = null;
        this.optimizationActive = false;
        this.learningAcceleratorActive = false;
        this.performanceMetrics = {};
        this.predictivePreloader = null;
        this.preloadedElements = new Set();
        this.userPatterns = {};
        
        // Initialize
        this.init();
    }
    
    async init() {
        console.log('🧠 Initializing SuperInstance ML...');
        
        // Check ML system status
        try {
            const response = await fetch('/api/ml/ecosystem/status');
            const data = await response.json();
            
            if (data.success) {
                this.mlActive = data.status.ml_systems_available;
                console.log(`✅ ML Systems: ${this.mlActive ? 'ACTIVE' : 'BASIC MODE'}`);
                
                if (this.mlActive) {
                    console.log('🎯 Active Systems:', data.status.active_systems.join(', '));
                    this.startNavigationTracking();
                    this.startInputInterception();
                    this.loadUISuggestions();
                    this.startOptimizationMonitoring();
                    this.startLearningAcceleration();
                    this.startPredictiveUIPreloading();
                }
            }
        } catch (error) {
            console.warn('⚠️ ML system check failed:', error);
            this.mlActive = false;
        }
    }
    
    // Navigation Intelligence
    startNavigationTracking() {
        console.log('🗺️ Starting navigation intelligence...');
        
        // Track page visits
        this.trackNavigation(window.location.pathname, 'page_visit');
        
        // Track clicks
        document.addEventListener('click', (event) => {
            const element = event.target;
            const elementId = element.id || element.className;
            const elementText = element.textContent?.substring(0, 50) || '';
            
            this.trackNavigation(
                window.location.pathname, 
                'click', 
                elementId, 
                elementText
            );
        });
        
        // Track hovers (for struggle detection)
        let hoverTimer;
        document.addEventListener('mouseover', (event) => {
            const startTime = Date.now();
            hoverTimer = setTimeout(() => {
                const element = event.target;
                const elementId = element.id || element.className;
                const timeSpent = (Date.now() - startTime) / 1000;
                
                if (timeSpent > 3) { // Long hover - user might be struggling
                    this.trackNavigation(
                        window.location.pathname,
                        'hover',
                        elementId,
                        element.textContent?.substring(0, 50) || '',
                        timeSpent
                    );
                }
            }, 3000);
        });
        
        document.addEventListener('mouseout', () => {
            clearTimeout(hoverTimer);
        });
        
        // Track back button usage (struggle indicator)
        window.addEventListener('popstate', () => {
            this.trackNavigation(window.location.pathname, 'back');
        });
    }
    
    async trackNavigation(pagePath, action, elementId = '', elementText = '', timeSpent = 0) {
        if (!this.mlActive) return;
        
        try {
            const response = await fetch('/api/navigation/track', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    page_path: pagePath,
                    action: action,
                    element_id: elementId,
                    element_text: elementText,
                    time_spent: timeSpent
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.navigationSession = data.session_id;
            }
        } catch (error) {
            console.debug('Navigation tracking failed:', error);
        }
    }
    
    // Input Intelligence
    startInputInterception() {
        console.log('⌨️ Starting input interpretation...');
        
        // Intercept all text inputs and textareas
        document.querySelectorAll('input[type="text"], textarea').forEach(input => {
            this.attachInputInterpreter(input);
        });
        
        // Handle dynamically added inputs
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) { // Element node
                        const inputs = node.querySelectorAll ? 
                            node.querySelectorAll('input[type="text"], textarea') : [];
                        inputs.forEach(input => this.attachInputInterpreter(input));
                        
                        if (node.matches && node.matches('input[type="text"], textarea')) {
                            this.attachInputInterpreter(node);
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    attachInputInterpreter(inputElement) {
        let lastValue = '';
        let correctionTimer;
        
        inputElement.addEventListener('input', async (event) => {
            const currentValue = event.target.value;
            
            // Detect corrections (backspacing)
            if (currentValue.length < lastValue.length) {
                // User backspaced - potential correction learning
                clearTimeout(correctionTimer);
                correctionTimer = setTimeout(async () => {
                    const finalValue = event.target.value;
                    if (finalValue !== lastValue && finalValue.trim()) {
                        await this.reportCorrection(lastValue, finalValue);
                    }
                }, 2000); // Wait 2 seconds after user stops typing
            }
            
            // Real-time interpretation for longer inputs
            if (currentValue.length > 5 && currentValue !== lastValue) {
                const interpretation = await this.interpretInput(currentValue);
                
                if (interpretation.corrected_text !== currentValue && 
                    interpretation.confidence > 0.7) {
                    this.showInputSuggestion(inputElement, interpretation);
                }
            }
            
            lastValue = currentValue;
        });
    }
    
    async interpretInput(text) {
        if (!this.mlActive) return {corrected_text: text, confidence: 1.0, corrections_applied: []};
        
        try {
            const response = await fetch('/api/input/interpret', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    text: text,
                    app_name: this.appName
                })
            });
            
            const data = await response.json();
            return data.success ? data : {corrected_text: text, confidence: 1.0, corrections_applied: []};
        } catch (error) {
            console.debug('Input interpretation failed:', error);
            return {corrected_text: text, confidence: 1.0, corrections_applied: []};
        }
    }
    
    async reportCorrection(original, corrected) {
        if (!this.mlActive) return;
        
        console.log(`📚 Learning: "${original}" → "${corrected}"`);
        
        // Report to system for learning
        try {
            await fetch('/api/input/interpret', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    original: original,
                    corrected: corrected,
                    action: 'report_correction',
                    app_name: this.appName
                })
            });
        } catch (error) {
            console.debug('Correction reporting failed:', error);
        }
    }
    
    showInputSuggestion(inputElement, interpretation) {
        // Create subtle suggestion UI
        let suggestionDiv = document.getElementById('ml-input-suggestion');
        
        if (!suggestionDiv) {
            suggestionDiv = document.createElement('div');
            suggestionDiv.id = 'ml-input-suggestion';
            suggestionDiv.style.cssText = `
                position: absolute;
                background: #2563eb;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                z-index: 10000;
                max-width: 300px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                opacity: 0;
                transition: opacity 0.2s;
                pointer-events: none;
            `;
            document.body.appendChild(suggestionDiv);
        }
        
        const rect = inputElement.getBoundingClientRect();
        suggestionDiv.style.left = rect.left + 'px';
        suggestionDiv.style.top = (rect.bottom + 5) + 'px';
        suggestionDiv.innerHTML = `
            💡 <strong>Suggestion:</strong> "${interpretation.corrected_text}"<br>
            <small>Corrections: ${interpretation.corrections_applied.join(', ')}</small>
        `;
        suggestionDiv.style.opacity = '1';
        
        // Auto-hide after 4 seconds
        setTimeout(() => {
            suggestionDiv.style.opacity = '0';
        }, 4000);
    }
    
    // UI Optimization
    async loadUISuggestions() {
        if (!this.mlActive) return;
        
        try {
            const response = await fetch('/api/ui/suggestions');
            const data = await response.json();
            
            if (data.success && data.suggestions.length > 0) {
                console.log(`💡 ${data.suggestions.length} UI optimizations available`);
                this.suggestions = data.suggestions;
                this.showUISuggestions();
            }
        } catch (error) {
            console.debug('UI suggestions loading failed:', error);
        }
    }
    
    showUISuggestions() {
        if (this.suggestions.length === 0) return;
        
        // Show highest confidence suggestion
        const topSuggestion = this.suggestions.reduce((prev, current) => 
            (prev.confidence > current.confidence) ? prev : current
        );
        
        this.createSuggestionPopup(topSuggestion);
    }
    
    createSuggestionPopup(suggestion) {
        const popup = document.createElement('div');
        popup.id = 'ml-ui-suggestion';
        popup.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            max-width: 350px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
            z-index: 10001;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            animation: slideInUp 0.3s ease;
        `;
        
        popup.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 24px;">🤖</div>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 8px 0; font-size: 16px;">${suggestion.title}</h4>
                    <p style="margin: 0 0 12px 0; font-size: 14px; opacity: 0.9;">
                        ${suggestion.description}
                    </p>
                    <p style="margin: 0 0 16px 0; font-size: 12px; opacity: 0.8;">
                        💪 ${suggestion.expected_benefit}
                    </p>
                    <div style="display: flex; gap: 8px;">
                        <button id="accept-suggestion" style="
                            background: rgba(255,255,255,0.2);
                            border: 1px solid rgba(255,255,255,0.3);
                            color: white;
                            padding: 8px 16px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 12px;
                        ">✅ Accept</button>
                        <button id="dismiss-suggestion" style="
                            background: rgba(0,0,0,0.2);
                            border: 1px solid rgba(255,255,255,0.2);
                            color: white;
                            padding: 8px 16px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 12px;
                        ">❌ Dismiss</button>
                    </div>
                </div>
            </div>
        `;
        
        // Add animation keyframes
        if (!document.getElementById('ml-animations')) {
            const style = document.createElement('style');
            style.id = 'ml-animations';
            style.textContent = `
                @keyframes slideInUp {
                    from { transform: translateY(100px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @keyframes slideOutDown {
                    from { transform: translateY(0); opacity: 1; }
                    to { transform: translateY(100px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(popup);
        
        // Handle responses
        popup.querySelector('#accept-suggestion').addEventListener('click', () => {
            this.respondToSuggestion(suggestion.id, 'accept');
            this.removeSuggestionPopup(popup);
        });
        
        popup.querySelector('#dismiss-suggestion').addEventListener('click', () => {
            this.respondToSuggestion(suggestion.id, 'dismiss');
            this.removeSuggestionPopup(popup);
        });
        
        // Auto-dismiss after 30 seconds
        setTimeout(() => {
            if (document.body.contains(popup)) {
                this.removeSuggestionPopup(popup);
            }
        }, 30000);
    }
    
    async respondToSuggestion(suggestionId, response) {
        if (!this.mlActive) return;
        
        try {
            await fetch(`/api/ui/suggestions/${suggestionId}/respond`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({response: response})
            });
            
            console.log(`📝 UI suggestion ${response}ed:`, suggestionId);
        } catch (error) {
            console.debug('Suggestion response failed:', error);
        }
    }
    
    removeSuggestionPopup(popup) {
        popup.style.animation = 'slideOutDown 0.3s ease';
        setTimeout(() => {
            if (document.body.contains(popup)) {
                document.body.removeChild(popup);
            }
        }, 300);
    }
    
    // ML Performance Optimization
    startOptimizationMonitoring() {
        if (!this.mlActive) return;
        
        console.log('⚡ Starting ML performance optimization monitoring...');
        this.optimizationActive = true;
        
        // Monitor performance every 30 seconds
        setInterval(async () => {
            if (this.optimizationActive) {
                await this.checkAndOptimizePerformance();
            }
        }, 30000);
        
        // Trigger initial optimization
        setTimeout(() => this.optimizeMLPerformance(), 5000);
    }
    
    async optimizeMLPerformance() {
        if (!this.mlActive) return;
        
        try {
            const response = await fetch('/api/ml/performance/optimize', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            if (data.success) {
                console.log('⚡ ML Performance optimized:', data.optimization);
                this.performanceMetrics.lastOptimization = Date.now();
            }
        } catch (error) {
            console.debug('Performance optimization failed:', error);
        }
    }
    
    async checkAndOptimizePerformance() {
        try {
            const response = await fetch('/api/ml/performance/report');
            const data = await response.json();
            
            if (data.success && data.report.needs_optimization) {
                console.log('🔧 Automatic performance optimization triggered');
                await this.optimizeMLPerformance();
            }
        } catch (error) {
            console.debug('Performance check failed:', error);
        }
    }
    
    // Real-time Learning Acceleration
    startLearningAcceleration() {
        if (!this.mlActive) return;
        
        console.log('🚀 Starting real-time learning acceleration...');
        this.learningAcceleratorActive = true;
        
        // Monitor user interactions for learning opportunities
        document.addEventListener('keydown', (event) => {
            this.accelerateInputLearning(event);
        });
        
        document.addEventListener('click', (event) => {
            this.accelerateNavigationLearning(event);
        });
        
        // Periodic learning acceleration
        setInterval(async () => {
            if (this.learningAcceleratorActive) {
                await this.triggerLearningAcceleration('periodic_optimization');
            }
        }, 60000); // Every minute
    }
    
    async accelerateInputLearning(event) {
        if (!this.learningAcceleratorActive) return;
        
        // Trigger learning acceleration for input patterns
        if (event.target.matches('input, textarea')) {
            try {
                await fetch('/api/ml/learning/accelerate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        event_type: 'input_interaction',
                        context: {
                            element_type: event.target.tagName.toLowerCase(),
                            key: event.key,
                            timestamp: Date.now()
                        }
                    })
                });
            } catch (error) {
                console.debug('Input learning acceleration failed:', error);
            }
        }
    }
    
    async accelerateNavigationLearning(event) {
        if (!this.learningAcceleratorActive) return;
        
        // Trigger learning acceleration for navigation patterns
        try {
            await fetch('/api/ml/learning/accelerate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    event_type: 'navigation_interaction',
                    context: {
                        element_id: event.target.id || event.target.className,
                        element_text: event.target.textContent?.substring(0, 50) || '',
                        page_path: window.location.pathname,
                        timestamp: Date.now()
                    }
                })
            });
        } catch (error) {
            console.debug('Navigation learning acceleration failed:', error);
        }
    }
    
    async triggerLearningAcceleration(eventType) {
        try {
            const response = await fetch('/api/ml/learning/accelerate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    event_type: eventType
                })
            });
            
            const data = await response.json();
            if (data.success && data.acceleration.learning_accelerated) {
                console.log('🚀 Learning accelerated:', data.acceleration);
            }
        } catch (error) {
            console.debug('Learning acceleration trigger failed:', error);
        }
    }
    
    async applyAcceleratedImprovements(text) {
        if (!this.learningAcceleratorActive) return text;
        
        try {
            const response = await fetch('/api/ml/learning/apply', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text})
            });
            
            const data = await response.json();
            if (data.success && data.improvements_applied) {
                console.log('✨ Applied learning improvements:', {
                    original: data.original_text,
                    improved: data.improved_text
                });
                return data.improved_text;
            }
        } catch (error) {
            console.debug('Learning improvements failed:', error);
        }
        
        return text;
    }
    
    async getLearningInsights() {
        if (!this.learningAcceleratorActive) return null;
        
        try {
            const response = await fetch('/api/ml/learning/insights');
            const data = await response.json();
            
            if (data.success) {
                return data.insights;
            }
        } catch (error) {
            console.debug('Learning insights failed:', error);
        }
        
        return null;
    }
    
    // Predictive UI Pre-loading
    startPredictiveUIPreloading() {
        if (!this.mlActive) return;
        
        console.log('🎯 Starting predictive UI pre-loading...');
        
        this.predictivePreloader = {
            active: true,
            patterns: new Map(),
            predictions: new Map(),
            lastUpdate: Date.now()
        };
        
        // Track user navigation patterns
        this.trackNavigationPatterns();
        
        // Predictive preloading based on patterns
        setInterval(() => {
            if (this.predictivePreloader.active) {
                this.predictAndPreload();
            }
        }, 10000); // Every 10 seconds
        
        // Immediate pattern analysis
        setTimeout(() => this.analyzeUserPatterns(), 3000);
    }
    
    trackNavigationPatterns() {
        // Track page transitions
        let lastPage = window.location.pathname;
        let pageStartTime = Date.now();
        
        setInterval(() => {
            const currentPage = window.location.pathname;
            if (currentPage !== lastPage) {
                const timeSpent = Date.now() - pageStartTime;
                
                // Record transition pattern
                const pattern = `${lastPage}→${currentPage}`;
                if (!this.userPatterns[pattern]) {
                    this.userPatterns[pattern] = { count: 0, avgTime: 0 };
                }
                
                this.userPatterns[pattern].count++;
                this.userPatterns[pattern].avgTime = 
                    (this.userPatterns[pattern].avgTime + timeSpent) / 2;
                
                console.log(`📊 Pattern learned: ${pattern} (${this.userPatterns[pattern].count} times)`);
                
                lastPage = currentPage;
                pageStartTime = Date.now();
            }
        }, 1000);
        
        // Track element interaction patterns
        document.addEventListener('click', (event) => {
            const element = event.target;
            const href = element.getAttribute('href') || 
                        element.closest('a')?.getAttribute('href');
            
            if (href && href.startsWith('/')) {
                const pattern = `click:${window.location.pathname}→${href}`;
                if (!this.userPatterns[pattern]) {
                    this.userPatterns[pattern] = { count: 0, likelihood: 0 };
                }
                
                this.userPatterns[pattern].count++;
                this.userPatterns[pattern].likelihood = 
                    Math.min(this.userPatterns[pattern].count * 0.1, 1.0);
            }
        });
    }
    
    analyzeUserPatterns() {
        console.log('🔍 Analyzing user navigation patterns...');
        
        // Find most frequent patterns
        const sortedPatterns = Object.entries(this.userPatterns)
            .sort(([,a], [,b]) => b.count - a.count)
            .slice(0, 5);
        
        console.log('📈 Top navigation patterns:', sortedPatterns);
        
        // Predict next likely pages
        const currentPage = window.location.pathname;
        const likelyNextPages = [];
        
        for (const [pattern, data] of Object.entries(this.userPatterns)) {
            if (pattern.includes(currentPage) && data.count >= 2) {
                const targetPage = pattern.split('→')[1];
                if (targetPage && targetPage !== currentPage) {
                    likelyNextPages.push({
                        page: targetPage,
                        probability: data.likelihood || (data.count * 0.1),
                        pattern: pattern
                    });
                }
            }
        }
        
        // Sort by probability
        likelyNextPages.sort((a, b) => b.probability - a.probability);
        
        if (likelyNextPages.length > 0) {
            console.log('🎯 Predicted next pages:', likelyNextPages.slice(0, 3));
            this.preloadLikelyPages(likelyNextPages.slice(0, 2));
        }
    }
    
    predictAndPreload() {
        this.analyzeUserPatterns();
        
        // Predict based on current context
        const currentTime = new Date().getHours();
        const currentPage = window.location.pathname;
        
        // Time-based predictions
        let timeBasedPredictions = [];
        if (currentTime >= 9 && currentTime <= 17) { // Business hours
            timeBasedPredictions = ['/dashboard', '/gaming-interface'];
        } else { // Evening/night
            timeBasedPredictions = ['/gaming-interface'];
        }
        
        // Preload predicted resources
        for (const prediction of timeBasedPredictions) {
            if (prediction !== currentPage) {
                this.preloadPage(prediction, 'time_based');
            }
        }
    }
    
    preloadPage(pagePath, reason = 'pattern_based') {
        if (this.preloadedElements.has(pagePath)) {
            return; // Already preloaded
        }
        
        console.log(`⚡ Pre-loading ${pagePath} (${reason})`);
        
        // Create invisible link to trigger preload
        const preloadLink = document.createElement('link');
        preloadLink.rel = 'prefetch';
        preloadLink.href = pagePath;
        preloadLink.dataset.mlPreload = reason;
        
        document.head.appendChild(preloadLink);
        this.preloadedElements.add(pagePath);
        
        // Also preload likely static resources
        this.preloadStaticResources(pagePath);
        
        // Remove after 5 minutes to prevent memory buildup
        setTimeout(() => {
            if (document.head.contains(preloadLink)) {
                document.head.removeChild(preloadLink);
                this.preloadedElements.delete(pagePath);
            }
        }, 300000);
    }
    
    preloadStaticResources(pagePath) {
        // Common resources that might be needed
        const commonResources = [
            '/static/style.css',
            '/static/superinstance-ml.js'
        ];
        
        // Page-specific resources
        const pageResources = {
            '/gaming-interface': [
                '/static/gaming-styles.css',
                '/static/voice-interface.js'
            ],
            '/dashboard': [
                '/static/dashboard-scripts.js'
            ]
        };
        
        const resourcesToPreload = [
            ...commonResources,
            ...(pageResources[pagePath] || [])
        ];
        
        resourcesToPreload.forEach(resource => {
            if (!this.preloadedElements.has(resource)) {
                const link = document.createElement('link');
                link.rel = 'preload';
                link.href = resource;
                link.as = resource.endsWith('.css') ? 'style' : 'script';
                link.dataset.mlPreload = 'static_resource';
                
                document.head.appendChild(link);
                this.preloadedElements.add(resource);
                
                // Clean up after 5 minutes
                setTimeout(() => {
                    if (document.head.contains(link)) {
                        document.head.removeChild(link);
                        this.preloadedElements.delete(resource);
                    }
                }, 300000);
            }
        });
    }
    
    preloadLikelyPages(predictions) {
        predictions.forEach(prediction => {
            if (prediction.probability > 0.3) { // High confidence threshold
                this.preloadPage(prediction.page, `predicted_${prediction.probability.toFixed(2)}`);
            }
        });
    }
    
    // Utility Methods
    getSystemStatus() {
        return {
            mlActive: this.mlActive,
            userId: this.userId,
            appName: this.appName,
            suggestionsCount: this.suggestions.length,
            navigationSession: this.navigationSession,
            optimizationActive: this.optimizationActive,
            learningAcceleratorActive: this.learningAcceleratorActive,
            performanceMetrics: this.performanceMetrics,
            predictivePreloader: this.predictivePreloader,
            preloadedCount: this.preloadedElements.size,
            learnedPatterns: Object.keys(this.userPatterns).length
        };
    }
}

// Auto-initialize for SuperInstance apps
document.addEventListener('DOMContentLoaded', () => {
    // Check if we have user context
    const userId = window.currentUser?.id || window.username || 'anonymous';
    const appName = window.currentApp || 'dmlog';
    
    // Initialize ML system
    window.SuperInstanceML = new SuperInstanceML(userId, appName);
    
    console.log('🚀 SuperInstance ML Integration loaded');
    console.log('📊 Status:', window.SuperInstanceML.getSystemStatus());
});

// Export for manual initialization
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SuperInstanceML;
}