/**
 * Universal Accessibility Enhancement Script
 * ========================================
 * 
 * This script can be injected into any frontend to make it more accessible
 * for both young and elderly users. It provides:
 * 
 * - Text size controls (larger fonts)
 * - High contrast mode
 * - Simplified navigation
 * - Voice control integration
 * - Keyboard shortcuts
 * - Screen reader optimization
 * - Reduced motion options
 * - Clear focus indicators
 * - Larger click targets
 * - Simple language mode
 */

(function() {
    'use strict';

    // Accessibility state
    let a11ySettings = {
        largeText: false,
        extraLargeText: false,
        highContrast: false,
        reduceMotion: false,
        simplifiedNav: false,
        voiceControl: false,
        simpleLanguage: false
    };

    // Create accessibility panel
    function createAccessibilityPanel() {
        const panel = document.createElement('div');
        panel.id = 'universal-a11y-panel';
        panel.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                background: white;
                border: 2px solid #3b82f6;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                max-width: 320px;
                font-family: Arial, sans-serif;
                display: none;
            ">
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 16px;
                    padding-bottom: 12px;
                    border-bottom: 1px solid #e5e7eb;
                ">
                    <h3 style="
                        font-size: 18px;
                        font-weight: bold;
                        margin: 0;
                        color: #1f2937;
                    ">♿ Easy Access</h3>
                    <button id="close-a11y-panel" style="
                        background: none;
                        border: none;
                        font-size: 24px;
                        cursor: pointer;
                        padding: 4px;
                        color: #6b7280;
                    " aria-label="Close accessibility panel">×</button>
                </div>

                <div style="space-y: 12px;">
                    <label style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 16px;
                        cursor: pointer;
                        margin-bottom: 12px;
                    ">
                        <input type="checkbox" id="large-text" style="
                            width: 18px;
                            height: 18px;
                            cursor: pointer;
                        ">
                        <span>🔤 Larger Text</span>
                    </label>

                    <label style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 16px;
                        cursor: pointer;
                        margin-bottom: 12px;
                    ">
                        <input type="checkbox" id="extra-large-text" style="
                            width: 18px;
                            height: 18px;
                            cursor: pointer;
                        ">
                        <span>📝 Extra Large Text</span>
                    </label>

                    <label style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 16px;
                        cursor: pointer;
                        margin-bottom: 12px;
                    ">
                        <input type="checkbox" id="high-contrast" style="
                            width: 18px;
                            height: 18px;
                            cursor: pointer;
                        ">
                        <span>🎨 High Contrast</span>
                    </label>

                    <label style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 16px;
                        cursor: pointer;
                        margin-bottom: 12px;
                    ">
                        <input type="checkbox" id="reduce-motion" style="
                            width: 18px;
                            height: 18px;
                            cursor: pointer;
                        ">
                        <span>🎯 Less Animation</span>
                    </label>

                    <label style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 16px;
                        cursor: pointer;
                        margin-bottom: 12px;
                    ">
                        <input type="checkbox" id="simplified-nav" style="
                            width: 18px;
                            height: 18px;
                            cursor: pointer;
                        ">
                        <span>🧭 Simple Navigation</span>
                    </label>

                    <label style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 16px;
                        cursor: pointer;
                        margin-bottom: 12px;
                    ">
                        <input type="checkbox" id="voice-control" style="
                            width: 18px;
                            height: 18px;
                            cursor: pointer;
                        ">
                        <span>🎙️ Voice Control</span>
                    </label>

                    <div style="
                        margin-top: 16px;
                        padding-top: 12px;
                        border-top: 1px solid #e5e7eb;
                    ">
                        <button id="help-shortcuts" style="
                            width: 100%;
                            background: #3b82f6;
                            color: white;
                            border: none;
                            padding: 12px;
                            border-radius: 8px;
                            font-size: 16px;
                            cursor: pointer;
                            margin-bottom: 8px;
                        ">📖 Quick Help</button>
                        
                        <button id="reset-settings" style="
                            width: 100%;
                            background: #6b7280;
                            color: white;
                            border: none;
                            padding: 8px;
                            border-radius: 6px;
                            font-size: 14px;
                            cursor: pointer;
                        ">🔄 Reset All</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(panel);
        return panel;
    }

    // Create accessibility toggle button
    function createAccessibilityToggle() {
        const toggle = document.createElement('button');
        toggle.id = 'universal-a11y-toggle';
        toggle.innerHTML = '♿';
        toggle.setAttribute('aria-label', 'Open accessibility options');
        toggle.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            background: #3b82f6;
            color: white;
            border: none;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
            transition: all 0.3s ease;
        `;

        toggle.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
            this.style.boxShadow = '0 6px 20px rgba(59, 130, 246, 0.6)';
        });

        toggle.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
            this.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.4)';
        });

        document.body.appendChild(toggle);
        return toggle;
    }

    // Apply accessibility styles
    function injectAccessibilityStyles() {
        const styles = document.createElement('style');
        styles.innerHTML = `
            /* Universal Accessibility Styles */
            .a11y-large-text * { font-size: 1.25em !important; line-height: 1.6 !important; }
            .a11y-extra-large-text * { font-size: 1.5em !important; line-height: 1.7 !important; }
            
            .a11y-high-contrast {
                filter: contrast(200%) !important;
                background: white !important;
                color: black !important;
            }
            
            .a11y-high-contrast * {
                background: white !important;
                color: black !important;
                border-color: black !important;
            }
            
            .a11y-high-contrast button,
            .a11y-high-contrast a {
                background: black !important;
                color: white !important;
                border: 2px solid black !important;
            }
            
            .a11y-reduce-motion * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
                transform: none !important;
            }
            
            .a11y-big-buttons button,
            .a11y-big-buttons a,
            .a11y-big-buttons input,
            .a11y-big-buttons select {
                min-height: 48px !important;
                min-width: 48px !important;
                padding: 12px 16px !important;
                font-size: 16px !important;
                border-radius: 8px !important;
                margin: 4px !important;
            }
            
            .a11y-focus-visible *:focus {
                outline: 3px solid #3b82f6 !important;
                outline-offset: 2px !important;
                box-shadow: 0 0 0 6px rgba(59, 130, 246, 0.3) !important;
            }
            
            .a11y-simplified-nav nav > * {
                display: none !important;
            }
            
            .a11y-simplified-nav nav > *:nth-child(-n+3) {
                display: block !important;
                font-size: 18px !important;
                padding: 12px !important;
                margin: 8px !important;
            }

            /* Screen reader helpers */
            .sr-only {
                position: absolute !important;
                width: 1px !important;
                height: 1px !important;
                padding: 0 !important;
                margin: -1px !important;
                overflow: hidden !important;
                clip: rect(0, 0, 0, 0) !important;
                white-space: nowrap !important;
                border: 0 !important;
            }
        `;
        document.head.appendChild(styles);
    }

    // Apply accessibility settings
    function applyAccessibilitySettings() {
        const body = document.body;
        
        // Remove all accessibility classes first
        body.className = body.className.replace(/a11y-\w+/g, '');
        
        // Apply current settings
        if (a11ySettings.largeText) {
            body.classList.add('a11y-large-text', 'a11y-big-buttons', 'a11y-focus-visible');
        }
        
        if (a11ySettings.extraLargeText) {
            body.classList.add('a11y-extra-large-text', 'a11y-big-buttons', 'a11y-focus-visible');
        }
        
        if (a11ySettings.highContrast) {
            body.classList.add('a11y-high-contrast');
        }
        
        if (a11ySettings.reduceMotion) {
            body.classList.add('a11y-reduce-motion');
        }
        
        if (a11ySettings.simplifiedNav) {
            body.classList.add('a11y-simplified-nav');
        }

        // Announce changes
        announceToScreenReader('Accessibility settings updated');
        
        // Save settings
        localStorage.setItem('universalA11ySettings', JSON.stringify(a11ySettings));
    }

    // Screen reader announcements
    function announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }

    // Voice control (simplified)
    function initializeVoiceControl() {
        if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        // Voice commands
        const commands = {
            'scroll up': () => window.scrollBy(0, -300),
            'scroll down': () => window.scrollBy(0, 300),
            'go back': () => window.history.back(),
            'click button': () => {
                const button = document.querySelector('button');
                if (button) button.click();
            },
            'open menu': () => {
                const menu = document.querySelector('[data-lucide="menu"], .menu-toggle, #sidebar-toggle');
                if (menu) menu.click();
            }
        };

        recognition.onresult = function(event) {
            const command = event.results[0][0].transcript.toLowerCase().trim();
            
            if (commands[command]) {
                commands[command]();
                announceToScreenReader(`Executed: ${command}`);
            } else {
                announceToScreenReader('Command not recognized');
            }
        };

        // Start listening when voice control is enabled
        function startListening() {
            if (a11ySettings.voiceControl) {
                recognition.start();
            }
        }

        // Add global voice activation
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.shiftKey && e.key === 'V') {
                e.preventDefault();
                startListening();
            }
        });
    }

    // Keyboard shortcuts
    function initializeKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Alt + A: Open accessibility panel
            if (e.altKey && e.key === 'a') {
                e.preventDefault();
                document.getElementById('universal-a11y-toggle').click();
            }

            // Alt + H: Show help
            if (e.altKey && e.key === 'h') {
                e.preventDefault();
                showHelp();
            }

            // Alt + T: Toggle large text
            if (e.altKey && e.key === 't') {
                e.preventDefault();
                const toggle = document.getElementById('large-text');
                if (toggle) {
                    toggle.checked = !toggle.checked;
                    toggle.dispatchEvent(new Event('change'));
                }
            }

            // Alt + C: Toggle high contrast
            if (e.altKey && e.key === 'c') {
                e.preventDefault();
                const toggle = document.getElementById('high-contrast');
                if (toggle) {
                    toggle.checked = !toggle.checked;
                    toggle.dispatchEvent(new Event('change'));
                }
            }
        });
    }

    // Show help modal
    function showHelp() {
        const help = document.createElement('div');
        help.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 10001;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: Arial, sans-serif;
        `;
        
        help.innerHTML = `
            <div style="
                background: white;
                padding: 30px;
                border-radius: 12px;
                max-width: 500px;
                max-height: 80vh;
                overflow-y: auto;
            ">
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 1px solid #e5e7eb;
                ">
                    <h2 style="
                        font-size: 24px;
                        font-weight: bold;
                        margin: 0;
                        color: #1f2937;
                    ">📖 Quick Help</h2>
                    <button onclick="this.closest('[style*=fixed]').remove()" style="
                        background: none;
                        border: none;
                        font-size: 28px;
                        cursor: pointer;
                        color: #6b7280;
                    ">×</button>
                </div>
                
                <div style="space-y: 15px;">
                    <div style="margin-bottom: 15px;">
                        <h3 style="font-size: 18px; font-weight: bold; color: #3b82f6; margin-bottom: 5px;">⌨️ Keyboard Shortcuts</h3>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Alt + A:</strong> Open accessibility options</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Alt + H:</strong> Show this help</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Alt + T:</strong> Toggle large text</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Alt + C:</strong> Toggle high contrast</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Ctrl + Shift + V:</strong> Voice control</p>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <h3 style="font-size: 18px; font-weight: bold; color: #059669; margin-bottom: 5px;">🎙️ Voice Commands</h3>
                        <p style="margin: 5px 0; font-size: 14px;">"scroll up" or "scroll down"</p>
                        <p style="margin: 5px 0; font-size: 14px;">"go back"</p>
                        <p style="margin: 5px 0; font-size: 14px;">"click button"</p>
                        <p style="margin: 5px 0; font-size: 14px;">"open menu"</p>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <h3 style="font-size: 18px; font-weight: bold; color: #dc2626; margin-bottom: 5px;">♿ Accessibility Features</h3>
                        <p style="margin: 5px 0; font-size: 14px;">• Larger text sizes for easier reading</p>
                        <p style="margin: 5px 0; font-size: 14px;">• High contrast mode for better visibility</p>
                        <p style="margin: 5px 0; font-size: 14px;">• Reduced animations for comfort</p>
                        <p style="margin: 5px 0; font-size: 14px;">• Simplified navigation options</p>
                        <p style="margin: 5px 0; font-size: 14px;">• Voice control for hands-free use</p>
                    </div>
                </div>
                
                <div style="
                    margin-top: 20px;
                    padding-top: 15px;
                    border-top: 1px solid #e5e7eb;
                    text-align: center;
                ">
                    <button onclick="this.closest('[style*=fixed]').remove()" style="
                        background: #3b82f6;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 8px;
                        font-size: 16px;
                        cursor: pointer;
                    ">Got it!</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(help);
        
        // Focus the close button
        const closeBtn = help.querySelector('button');
        if (closeBtn) closeBtn.focus();
    }

    // Initialize everything
    function init() {
        // Load saved settings
        const saved = localStorage.getItem('universalA11ySettings');
        if (saved) {
            a11ySettings = { ...a11ySettings, ...JSON.parse(saved) };
        }

        // Create UI
        injectAccessibilityStyles();
        const toggle = createAccessibilityToggle();
        const panel = createAccessibilityPanel();

        // Set up toggle
        toggle.addEventListener('click', function() {
            const isOpen = panel.firstElementChild.style.display !== 'none';
            panel.firstElementChild.style.display = isOpen ? 'none' : 'block';
            this.setAttribute('aria-expanded', !isOpen);
        });

        // Set up close button
        document.getElementById('close-a11y-panel').addEventListener('click', function() {
            panel.firstElementChild.style.display = 'none';
            toggle.setAttribute('aria-expanded', 'false');
        });

        // Set up checkboxes
        const checkboxes = {
            'large-text': 'largeText',
            'extra-large-text': 'extraLargeText',
            'high-contrast': 'highContrast',
            'reduce-motion': 'reduceMotion',
            'simplified-nav': 'simplifiedNav',
            'voice-control': 'voiceControl'
        };

        Object.entries(checkboxes).forEach(([id, setting]) => {
            const checkbox = document.getElementById(id);
            if (checkbox) {
                checkbox.checked = a11ySettings[setting];
                checkbox.addEventListener('change', function() {
                    a11ySettings[setting] = this.checked;
                    applyAccessibilitySettings();
                });
            }
        });

        // Set up help and reset buttons
        document.getElementById('help-shortcuts').addEventListener('click', showHelp);
        document.getElementById('reset-settings').addEventListener('click', function() {
            Object.keys(a11ySettings).forEach(key => {
                a11ySettings[key] = false;
                const checkbox = document.getElementById(key.replace(/([A-Z])/g, '-$1').toLowerCase());
                if (checkbox) checkbox.checked = false;
            });
            applyAccessibilitySettings();
        });

        // Initialize features
        initializeKeyboardShortcuts();
        initializeVoiceControl();
        
        // Apply saved settings
        applyAccessibilitySettings();

        // Announce initialization
        setTimeout(() => {
            announceToScreenReader('Accessibility features are now available. Press Alt + A to open options.');
        }, 1000);

        console.log('Universal Accessibility Enhancer loaded successfully');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();