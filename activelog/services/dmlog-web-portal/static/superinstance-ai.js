/**
 * SuperInstance AI Voice Widget
 * Universal Claude-powered AI assistant for all SuperInstance apps and websites
 * 
 * Features:
 * - Push-to-talk voice interface
 * - Interface customization with Claude AI
 * - Data analysis and manipulation
 * - Admin developer mode
 * - Cross-platform compatibility
 */

class SuperInstanceAI {
    constructor(options = {}) {
        this.config = {
            apiEndpoint: options.apiEndpoint || 'http://172.22.219.126:8099',
            userId: options.userId || 'web_user',
            adminMode: options.adminMode || false,
            theme: options.theme || 'lightning-dark',
            position: options.position || 'bottom-right',
            autoShow: options.autoShow !== false,
            ...options
        };

        this.isListening = false;
        this.isProcessing = false;
        this.recognition = null;
        this.widget = null;
        this.chatContainer = null;
        this.messages = [];
        this.isAdmin = false;
        this.isDeveloperMode = false;

        this.init();
    }

    init() {
        this.createWidget();
        this.setupVoiceRecognition();
        this.checkAdminStatus();
        this.injectStyles();
        
        if (this.config.autoShow) {
            this.show();
        }
    }

    injectStyles() {
        const styles = `
            .superinstance-ai-widget {
                position: fixed;
                z-index: 10000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .superinstance-ai-widget.bottom-right {
                bottom: 20px;
                right: 20px;
            }

            .superinstance-ai-widget.bottom-left {
                bottom: 20px;
                left: 20px;
            }

            .superinstance-ai-toggle {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #FF6B6B, #4ECDC4);
                border: none;
                cursor: pointer;
                box-shadow: 0 8px 32px rgba(255, 107, 107, 0.3);
                backdrop-filter: blur(10px);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 24px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }

            .superinstance-ai-toggle:hover {
                transform: scale(1.1);
                box-shadow: 0 12px 40px rgba(255, 107, 107, 0.4);
            }

            .superinstance-ai-toggle.listening {
                background: linear-gradient(135deg, #FF6B6B, #FF006E);
                animation: pulse 1.5s infinite;
            }

            .superinstance-ai-toggle.processing {
                background: linear-gradient(135deg, #FFD93D, #FFBE0B);
                animation: spin 2s linear infinite;
            }

            .superinstance-ai-toggle.admin {
                background: linear-gradient(135deg, #06FFA5, #4ECDC4);
                box-shadow: 0 8px 32px rgba(6, 255, 165, 0.3);
            }

            @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.05); opacity: 0.8; }
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            .superinstance-ai-chat {
                position: absolute;
                bottom: 80px;
                right: 0;
                width: 400px;
                max-width: 90vw;
                height: 500px;
                max-height: 70vh;
                background: rgba(10, 14, 26, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(20px);
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                display: none;
                flex-direction: column;
                overflow: hidden;
            }

            .superinstance-ai-chat.visible {
                display: flex;
                animation: slideUp 0.3s ease;
            }

            @keyframes slideUp {
                from { transform: translateY(20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }

            .superinstance-ai-header {
                padding: 16px 20px;
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .superinstance-ai-title {
                color: #F8F9FA;
                font-size: 16px;
                font-weight: 600;
                margin: 0;
            }

            .superinstance-ai-status {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
                color: #ADB5BD;
            }

            .superinstance-ai-status.admin {
                color: #06FFA5;
            }

            .superinstance-ai-indicator {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #06FFA5;
                box-shadow: 0 0 8px rgba(6, 255, 165, 0.5);
            }

            .superinstance-ai-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .superinstance-ai-message {
                max-width: 80%;
                padding: 12px 16px;
                border-radius: 16px;
                font-size: 14px;
                line-height: 1.4;
                animation: messageSlide 0.3s ease;
            }

            @keyframes messageSlide {
                from { transform: translateX(-10px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            .superinstance-ai-message.user {
                align-self: flex-end;
                background: linear-gradient(135deg, rgba(255, 107, 107, 0.2), rgba(255, 107, 107, 0.1));
                border: 1px solid rgba(255, 107, 107, 0.3);
                color: #F8F9FA;
                border-bottom-right-radius: 4px;
            }

            .superinstance-ai-message.ai {
                align-self: flex-start;
                background: linear-gradient(135deg, rgba(78, 205, 196, 0.2), rgba(78, 205, 196, 0.1));
                border: 1px solid rgba(78, 205, 196, 0.3);
                color: #F8F9FA;
                border-bottom-left-radius: 4px;
            }

            .superinstance-ai-message.admin {
                border: 1px solid rgba(6, 255, 165, 0.3);
                background: linear-gradient(135deg, rgba(6, 255, 165, 0.2), rgba(6, 255, 165, 0.1));
            }

            .superinstance-ai-input-area {
                padding: 16px;
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .superinstance-ai-input {
                flex: 1;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                padding: 12px 16px;
                color: #F8F9FA;
                font-size: 14px;
                outline: none;
                transition: all 0.3s ease;
            }

            .superinstance-ai-input::placeholder {
                color: #6C757D;
            }

            .superinstance-ai-input:focus {
                border-color: rgba(78, 205, 196, 0.5);
                box-shadow: 0 0 0 2px rgba(78, 205, 196, 0.2);
            }

            .superinstance-ai-voice-btn, .superinstance-ai-send-btn {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 16px;
                transition: all 0.3s ease;
            }

            .superinstance-ai-voice-btn {
                background: linear-gradient(135deg, #4ECDC4, #06FFA5);
            }

            .superinstance-ai-voice-btn:hover {
                transform: scale(1.1);
            }

            .superinstance-ai-voice-btn.listening {
                background: linear-gradient(135deg, #FF6B6B, #FF006E);
                animation: pulse 1s infinite;
            }

            .superinstance-ai-send-btn {
                background: linear-gradient(135deg, #FFD93D, #FFBE0B);
            }

            .superinstance-ai-send-btn:hover {
                transform: scale(1.1);
            }

            .superinstance-ai-send-btn:disabled {
                background: rgba(108, 117, 125, 0.3);
                cursor: not-allowed;
                transform: none;
            }

            .superinstance-ai-close {
                background: none;
                border: none;
                color: #ADB5BD;
                cursor: pointer;
                font-size: 16px;
                padding: 4px;
                border-radius: 4px;
                transition: color 0.3s ease;
            }

            .superinstance-ai-close:hover {
                color: #F8F9FA;
            }

            /* Mobile responsive */
            @media (max-width: 480px) {
                .superinstance-ai-chat {
                    width: calc(100vw - 40px);
                    height: calc(100vh - 100px);
                    bottom: 80px;
                    right: 20px;
                }
            }

            /* Visual Assets Styles */
            .superinstance-ai-message.visual-assets {
                max-width: 400px;
            }

            .visual-theme-result, .visual-image-result {
                padding: 12px;
            }

            .visual-theme-result h4 {
                margin: 0 0 12px 0;
                color: #06FFA5;
                font-size: 16px;
                font-weight: bold;
            }

            .theme-assets {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .asset-item {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 8px;
            }

            .asset-item p {
                margin: 0 0 8px 0;
                font-weight: bold;
                color: #F8F9FA;
            }

            .asset-item img {
                width: 100%;
                max-width: 200px;
                border-radius: 6px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            }

            .visual-image-result p {
                margin: 0 0 8px 0;
                color: #F8F9FA;
            }

            .visual-image-result em {
                color: #ADB5BD;
                font-size: 13px;
            }

            .visual-image-result small {
                color: #6C757D;
                font-size: 12px;
            }

            .visual-image-result img {
                max-width: 100%;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            }
        `;

        const styleSheet = document.createElement('style');
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }

    createWidget() {
        this.widget = document.createElement('div');
        this.widget.className = `superinstance-ai-widget ${this.config.position}`;
        
        const toggleButton = document.createElement('button');
        toggleButton.className = 'superinstance-ai-toggle';
        toggleButton.innerHTML = '🎙️';
        toggleButton.addEventListener('click', () => this.toggleChat());
        
        this.chatContainer = document.createElement('div');
        this.chatContainer.className = 'superinstance-ai-chat';
        this.createChatInterface();
        
        this.widget.appendChild(toggleButton);
        this.widget.appendChild(this.chatContainer);
        document.body.appendChild(this.widget);
        
        this.toggleButton = toggleButton;
    }

    createChatInterface() {
        const header = document.createElement('div');
        header.className = 'superinstance-ai-header';
        
        const title = document.createElement('h3');
        title.className = 'superinstance-ai-title';
        title.textContent = 'SuperInstance AI';
        
        const status = document.createElement('div');
        status.className = 'superinstance-ai-status';
        
        const indicator = document.createElement('div');
        indicator.className = 'superinstance-ai-indicator';
        
        const statusText = document.createElement('span');
        statusText.textContent = 'Ready';
        
        const closeButton = document.createElement('button');
        closeButton.className = 'superinstance-ai-close';
        closeButton.innerHTML = '✕';
        closeButton.addEventListener('click', () => this.hide());
        
        status.appendChild(indicator);
        status.appendChild(statusText);
        
        header.appendChild(title);
        header.appendChild(status);
        header.appendChild(closeButton);
        
        const messages = document.createElement('div');
        messages.className = 'superinstance-ai-messages';
        
        const inputArea = document.createElement('div');
        inputArea.className = 'superinstance-ai-input-area';
        
        const input = document.createElement('input');
        input.className = 'superinstance-ai-input';
        input.type = 'text';
        input.placeholder = 'Ask AI to help with interface, data, or D&D...';
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.isProcessing) {
                this.sendMessage(input.value);
            }
        });
        
        const voiceBtn = document.createElement('button');
        voiceBtn.className = 'superinstance-ai-voice-btn';
        voiceBtn.innerHTML = '🎤';
        voiceBtn.addEventListener('mousedown', () => this.startVoiceInput());
        voiceBtn.addEventListener('mouseup', () => this.stopVoiceInput());
        voiceBtn.addEventListener('mouseleave', () => this.stopVoiceInput());
        voiceBtn.addEventListener('touchstart', () => this.startVoiceInput());
        voiceBtn.addEventListener('touchend', () => this.stopVoiceInput());
        
        const sendBtn = document.createElement('button');
        sendBtn.className = 'superinstance-ai-send-btn';
        sendBtn.innerHTML = '➤';
        sendBtn.addEventListener('click', () => this.sendMessage(input.value));
        
        inputArea.appendChild(input);
        inputArea.appendChild(voiceBtn);
        inputArea.appendChild(sendBtn);
        
        this.chatContainer.appendChild(header);
        this.chatContainer.appendChild(messages);
        this.chatContainer.appendChild(inputArea);
        
        this.messagesContainer = messages;
        this.input = input;
        this.voiceBtn = voiceBtn;
        this.sendBtn = sendBtn;
        this.statusElement = status;
        
        // Add welcome message
        this.addMessage('Welcome to SuperInstance AI! I can help you customize interfaces, analyze data, or assist with D&D. Try saying "enable developer mode" if you\'re an admin.', 'ai');
    }

    setupVoiceRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                this.isListening = true;
                this.voiceBtn.classList.add('listening');
                this.toggleButton.classList.add('listening');
                this.updateStatus('Listening...', 'listening');
            };
            
            this.recognition.onresult = (event) => {
                const results = event.results;
                const lastResult = results[results.length - 1];
                
                if (lastResult.isFinal) {
                    const transcript = lastResult[0].transcript.trim();
                    this.sendMessage(transcript, true);
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.stopVoiceInput();
            };
            
            this.recognition.onend = () => {
                this.stopVoiceInput();
            };
        } else {
            console.warn('Speech recognition not supported in this browser');
        }
    }

    async checkAdminStatus() {
        try {
            const response = await fetch(`${this.config.apiEndpoint}/admin/status/${this.config.userId}`);
            const data = await response.json();
            
            if (data.success) {
                this.isAdmin = data.is_admin;
                this.isDeveloperMode = data.is_developer_mode;
                
                if (this.isAdmin) {
                    this.toggleButton.classList.add('admin');
                    this.statusElement.classList.add('admin');
                    this.updateStatus(this.isDeveloperMode ? 'Admin Dev Mode' : 'Admin Mode', 'admin');
                }
            }
        } catch (error) {
            console.log('Admin status check failed:', error);
        }
    }

    startVoiceInput() {
        if (this.recognition && !this.isListening && !this.isProcessing) {
            this.recognition.start();
        }
    }

    stopVoiceInput() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.isListening = false;
            this.voiceBtn.classList.remove('listening');
            this.toggleButton.classList.remove('listening');
            this.updateStatus('Ready', 'ready');
        }
    }

    async sendMessage(text, isVoice = false) {
        if (!text.trim() || this.isProcessing) return;
        
        this.addMessage(text, 'user');
        this.input.value = '';
        this.isProcessing = true;
        this.toggleButton.classList.add('processing');
        this.updateStatus('Processing...', 'processing');
        
        try {
            const endpoint = this.isAdmin ? '/admin/chat' : '/chat/message';
            const response = await fetch(`${this.config.apiEndpoint}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: text,
                    user_id: this.config.userId,
                    context: {
                        input_method: isVoice ? 'voice' : 'text',
                        is_web_widget: true,
                        current_url: window.location.href,
                        user_agent: navigator.userAgent
                    }
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addMessage(data.response, 'ai', data.capabilities);
                
                // Update admin state
                if (data.is_admin !== undefined) {
                    this.isAdmin = data.is_admin;
                }
                if (data.is_developer_mode !== undefined) {
                    this.isDeveloperMode = data.is_developer_mode;
                }
                
                // Handle UI customization requests
                if (data.is_ui_request && data.capabilities === 'full_admin') {
                    this.handleUICustomization(data);
                }
                
                // Handle visual generation requests
                if (data.is_visual_request && data.visual_assets && data.capabilities === 'full_admin') {
                    this.handleVisualGeneration(data);
                }
            } else {
                this.addMessage('Sorry, I encountered an error processing your request.', 'ai');
            }
        } catch (error) {
            console.error('Message send error:', error);
            this.addMessage('Connection error. Please check your network and try again.', 'ai');
        } finally {
            this.isProcessing = false;
            this.toggleButton.classList.remove('processing');
            this.updateStatus('Ready', 'ready');
        }
    }

    addMessage(text, sender, capabilities = null) {
        const message = document.createElement('div');
        message.className = `superinstance-ai-message ${sender}`;
        
        if (capabilities === 'full_admin' || capabilities === 'admin_basic') {
            message.classList.add('admin');
        }
        
        message.textContent = text;
        
        this.messagesContainer.appendChild(message);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    handleUICustomization(data) {
        // This would contain code generation and UI modification logic
        console.log('UI Customization request:', data);
        // Implementation would parse Claude's response for UI changes
    }

    handleVisualGeneration(data) {
        console.log('Visual generation result:', data.visual_assets);
        
        // Display generated visual assets
        if (data.visual_assets && data.visual_assets.success) {
            if (data.visual_assets.theme_id) {
                // Theme generation
                this.displayThemeAssets(data.visual_assets);
            } else if (data.visual_assets.image_url) {
                // Single image generation
                this.displayGeneratedImage(data.visual_assets);
            }
        } else if (data.visual_assets && data.visual_assets.error) {
            this.addMessage(`⚠️ Visual generation error: ${data.visual_assets.error}`, 'ai');
        }
    }

    displayThemeAssets(themeData) {
        const message = document.createElement('div');
        message.className = 'superinstance-ai-message ai visual-assets';
        
        let content = `<div class="visual-theme-result">
            <h4>🎨 Generated Theme: ${themeData.description}</h4>
            <div class="theme-assets">`;
        
        if (themeData.assets) {
            if (themeData.assets.background) {
                content += `<div class="asset-item">
                    <p><strong>Background:</strong></p>
                    <img src="${themeData.assets.background}" alt="Generated background" style="max-width: 200px; border-radius: 8px;">
                </div>`;
            }
            
            if (themeData.assets.components) {
                content += `<div class="asset-item">
                    <p><strong>Components:</strong></p>
                    <img src="${themeData.assets.components}" alt="Generated components" style="max-width: 200px; border-radius: 8px;">
                </div>`;
            }
            
            if (themeData.assets.icons) {
                content += `<div class="asset-item">
                    <p><strong>Icons:</strong></p>
                    <img src="${themeData.assets.icons}" alt="Generated icons" style="max-width: 200px; border-radius: 8px;">
                </div>`;
            }
        }
        
        content += `</div></div>`;
        message.innerHTML = content;
        
        this.messagesContainer.appendChild(message);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    displayGeneratedImage(imageData) {
        const message = document.createElement('div');
        message.className = 'superinstance-ai-message ai visual-assets';
        
        message.innerHTML = `<div class="visual-image-result">
            <p><strong>🖼️ Generated Image</strong></p>
            <p><em>${imageData.prompt}</em></p>
            <img src="${imageData.image_url}" alt="Generated image" style="max-width: 300px; border-radius: 8px; margin-top: 8px;">
            <p><small>Model: ${imageData.model}</small></p>
        </div>`;
        
        this.messagesContainer.appendChild(message);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    updateStatus(text, type) {
        const statusText = this.statusElement.querySelector('span');
        if (statusText) {
            statusText.textContent = text;
        }
        
        this.statusElement.className = `superinstance-ai-status ${type}`;
    }

    toggleChat() {
        if (this.chatContainer.classList.contains('visible')) {
            this.hide();
        } else {
            this.show();
        }
    }

    show() {
        this.chatContainer.classList.add('visible');
        this.input.focus();
    }

    hide() {
        this.chatContainer.classList.remove('visible');
    }

    destroy() {
        if (this.widget) {
            this.widget.remove();
        }
        if (this.recognition) {
            this.recognition.abort();
        }
    }
}

// Auto-initialize if configuration is found
if (typeof window !== 'undefined') {
    window.SuperInstanceAI = SuperInstanceAI;
    
    // Auto-initialize from data attributes or global config
    document.addEventListener('DOMContentLoaded', () => {
        const autoInit = document.querySelector('[data-superinstance-ai]');
        if (autoInit || window.SuperInstanceAIConfig) {
            const config = window.SuperInstanceAIConfig || {};
            if (autoInit) {
                Object.assign(config, autoInit.dataset);
            }
            new SuperInstanceAI(config);
        }
    });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SuperInstanceAI;
}