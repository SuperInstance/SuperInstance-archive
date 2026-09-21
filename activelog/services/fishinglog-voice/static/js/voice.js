// Voice Bridge Control JavaScript

class VoiceBridgeClient {
    constructor() {
        this.socket = io();
        this.voiceEnabled = false;
        this.listening = false;
        this.currentLanguage = 'en';
        this.pendingConfirmation = null;
        
        this.init();
    }
    
    init() {
        this.setupSocketListeners();
        this.setupUIControls();
        this.loadSystemStatus();
    }
    
    setupSocketListeners() {
        this.socket.on('connect', () => {
            console.log('Connected to voice bridge');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from voice bridge');
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('connected', (data) => {
            this.updateSystemStatus(data.voice_status);
        });
        
        this.socket.on('voice_command_executed', (data) => {
            this.handleCommandExecuted(data);
        });
        
        this.socket.on('voice_response', (data) => {
            this.displayVoiceResponse(data.text);
        });
        
        this.socket.on('voice_activation', (data) => {
            this.updateListeningStatus(data.active);
        });
        
        this.socket.on('emergency_alert', (data) => {
            this.handleEmergencyAlert(data);
        });
        
        this.socket.on('confirmation_required', (data) => {
            this.showConfirmationDialog(data);
        });
    }
    
    setupUIControls() {
        // Voice toggle button
        const voiceToggle = document.getElementById('voice-toggle');
        voiceToggle.addEventListener('click', () => {
            this.toggleVoiceControl();
        });
        
        // Language selector
        const languageSelect = document.getElementById('language-select');
        languageSelect.addEventListener('change', (e) => {
            this.changeLanguage(e.target.value);
        });
        
        // Sensitivity slider
        const sensitivitySlider = document.getElementById('sensitivity-slider');
        sensitivitySlider.addEventListener('input', (e) => {
            this.updateSensitivity(e.target.value);
        });
        
        // Confirmation buttons
        document.getElementById('confirm-btn').addEventListener('click', () => {
            this.confirmCommand();
        });
        
        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.cancelCommand();
        });
        
        // Quick command buttons
        document.querySelectorAll('.quick-cmd-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const command = e.target.dataset.cmd;
                this.sendVoiceCommand(command);
            });
        });
        
        // Emergency MOB button
        document.getElementById('emergency-mob').addEventListener('click', () => {
            this.emergencyMOB();
        });
        
        // Test voice button
        document.getElementById('test-voice').addEventListener('click', () => {
            this.testVoice();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    }
    
    toggleVoiceControl() {
        const endpoint = this.voiceEnabled ? '/api/voice/disable' : '/api/voice/enable';
        
        fetch(endpoint, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.voiceEnabled = !this.voiceEnabled;
                    this.updateVoiceToggleUI();
                    this.displayVoiceResponse(data.message);
                }
            })
            .catch(error => {
                console.error('Voice toggle error:', error);
            });
    }
    
    changeLanguage(language) {
        fetch('/api/voice/language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: language })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.currentLanguage = language;
                this.displayVoiceResponse(`Language changed to ${language}`);
            }
        });
    }
    
    updateSensitivity(sensitivity) {
        this.socket.emit('voice_settings', {
            sensitivity: parseFloat(sensitivity)
        });
    }
    
    sendVoiceCommand(command) {
        this.displayCommand(command);
        this.socket.emit('voice_command', { command: command });
        this.logCommand(command, 'manual');
    }
    
    emergencyMOB() {
        // Emergency commands bypass confirmation
        this.sendVoiceCommand('man overboard');
        this.flashEmergencyAlert('MOB MARKED');
    }
    
    testVoice() {
        fetch('/api/voice/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: 'Voice system test successful' })
        })
        .then(response => response.json())
        .then(data => {
            this.displayVoiceResponse('Voice test completed');
        });
    }
    
    handleCommandExecuted(data) {
        const { command, response } = data;
        
        this.displayCommand(command.original_text || 'Command executed');
        
        if (response) {
            this.displayVoiceResponse(response.message || 'Command completed');
            
            // Update confidence meter
            const confidence = command.confidence || 0;
            this.updateConfidenceMeter(confidence);
        }
        
        this.logCommand(command.original_text, 'voice', response);
    }
    
    displayCommand(command) {
        const commandDiv = document.getElementById('current-command');
        commandDiv.textContent = command;
        
        // Animate command display
        commandDiv.style.transform = 'scale(1.05)';
        setTimeout(() => {
            commandDiv.style.transform = 'scale(1)';
        }, 200);
    }
    
    displayVoiceResponse(text) {
        const responseDiv = document.getElementById('response-text');
        responseDiv.textContent = text;
        
        // Auto-clear after 5 seconds
        setTimeout(() => {
            responseDiv.textContent = '';
        }, 5000);
    }
    
    updateConfidenceMeter(confidence) {
        const confidenceBar = document.querySelector('.confidence-bar');
        confidenceBar.style.width = `${confidence * 100}%`;
        
        // Update color based on confidence
        if (confidence >= 0.8) {
            confidenceBar.style.background = '#00FF00';
        } else if (confidence >= 0.6) {
            confidenceBar.style.background = '#FFAA00';
        } else {
            confidenceBar.style.background = '#FF0000';
        }
    }
    
    showConfirmationDialog(data) {
        const confirmationPanel = document.getElementById('confirmation-panel');
        const confirmationText = document.getElementById('confirmation-text');
        
        confirmationText.textContent = data.message || 'Confirm this command?';
        confirmationPanel.classList.remove('hidden');
        
        this.pendingConfirmation = data;
        
        // Update confirmation indicator
        const indicator = document.getElementById('confirmation-indicator');
        indicator.classList.add('warning');
    }
    
    confirmCommand() {
        if (this.pendingConfirmation) {
            this.socket.emit('confirmation_response', {
                response: 'confirm',
                confirmation_id: this.pendingConfirmation.id
            });
            
            this.hideConfirmationDialog();
        }
    }
    
    cancelCommand() {
        if (this.pendingConfirmation) {
            this.socket.emit('confirmation_response', {
                response: 'cancel',
                confirmation_id: this.pendingConfirmation.id
            });
            
            this.hideConfirmationDialog();
        }
    }
    
    hideConfirmationDialog() {
        const confirmationPanel = document.getElementById('confirmation-panel');
        confirmationPanel.classList.add('hidden');
        
        const indicator = document.getElementById('confirmation-indicator');
        indicator.classList.remove('warning');
        
        this.pendingConfirmation = null;
    }
    
    updateListeningStatus(listening) {
        this.listening = listening;
        
        const indicator = document.getElementById('listening-indicator');
        const listeningDiv = indicator.classList;
        
        if (listening) {
            listeningDiv.add('active', 'voice-active');
        } else {
            listeningDiv.remove('active', 'voice-active');
        }
    }
    
    updateVoiceToggleUI() {
        const toggleBtn = document.getElementById('voice-toggle');
        
        if (this.voiceEnabled) {
            toggleBtn.textContent = 'Disable';
            toggleBtn.classList.add('active');
        } else {
            toggleBtn.textContent = 'Enable';
            toggleBtn.classList.remove('active');
        }
    }
    
    updateConnectionStatus(connected) {
        const indicator = document.getElementById('listening-indicator');
        
        if (connected) {
            indicator.classList.remove('danger');
        } else {
            indicator.classList.add('danger');
        }
    }
    
    updateSystemStatus(status) {
        if (status) {
            this.voiceEnabled = status.voice_enabled;
            this.listening = status.listening;
            this.currentLanguage = status.current_language;
            
            this.updateVoiceToggleUI();
            this.updateListeningStatus(this.listening);
            
            // Update language selector
            document.getElementById('language-select').value = this.currentLanguage;
            
            // Update sensitivity slider
            document.getElementById('sensitivity-slider').value = status.voice_sensitivity;
            
            // Update component status
            if (status.components) {
                this.updateComponentStatus(status.components);
            }
        }
    }
    
    updateComponentStatus(components) {
        // Update autopilot status
        if (components.autopilot) {
            document.getElementById('autopilot-status').textContent = 
                components.autopilot.autopilot_engaged ? 'Engaged' : 'Standby';
        }
        
        // Update follow vessel status
        if (components.follow_vessel) {
            document.getElementById('follow-status').textContent = 
                components.follow_vessel.following_enabled ? 'Active' : 'Disabled';
        }
        
        // Update noise level
        if (components.noise_filter) {
            const noiseLevel = components.noise_filter.current_noise_level;
            let levelText = 'Normal';
            
            if (noiseLevel > 0.8) levelText = 'High';
            else if (noiseLevel > 0.6) levelText = 'Moderate';
            else if (noiseLevel < 0.2) levelText = 'Low';
            
            document.getElementById('noise-level').textContent = levelText;
        }
    }
    
    handleEmergencyAlert(data) {
        this.flashEmergencyAlert(`EMERGENCY: ${data.type.toUpperCase()}`);
        this.displayVoiceResponse(`Emergency procedures activated: ${data.type}`);
        
        // Log emergency
        this.logCommand(`EMERGENCY: ${data.type}`, 'emergency', data);
    }
    
    flashEmergencyAlert(message) {
        // Flash screen red for emergency
        document.body.style.backgroundColor = '#FF0000';
        document.body.style.color = '#FFFFFF';
        
        // Show emergency message
        const commandDiv = document.getElementById('current-command');
        const originalText = commandDiv.textContent;
        commandDiv.textContent = message;
        commandDiv.style.fontSize = '28px';
        commandDiv.style.fontWeight = 'bold';
        
        // Restore after 3 seconds
        setTimeout(() => {
            document.body.style.backgroundColor = '';
            document.body.style.color = '';
            commandDiv.textContent = originalText;
            commandDiv.style.fontSize = '';
            commandDiv.style.fontWeight = '';
        }, 3000);
    }
    
    logCommand(command, source, response) {
        const logEntries = document.getElementById('log-entries');
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        const timestamp = new Date().toLocaleTimeString();
        const responseText = response ? 
            (response.message || response.status || 'Completed') : '';
        
        entry.innerHTML = `
            <div class="timestamp">${timestamp}</div>
            <div class="command">${command}</div>
            <div class="response">${responseText}</div>
        `;
        
        logEntries.insertBefore(entry, logEntries.firstChild);
        
        // Limit log entries
        while (logEntries.children.length > 20) {
            logEntries.removeChild(logEntries.lastChild);
        }
    }
    
    handleKeyboardShortcuts(e) {
        // Ctrl+V: Toggle voice
        if (e.ctrlKey && e.key === 'v') {
            e.preventDefault();
            this.toggleVoiceControl();
        }
        
        // Ctrl+M: Emergency MOB
        if (e.ctrlKey && e.key === 'm') {
            e.preventDefault();
            this.emergencyMOB();
        }
        
        // Space: PTT (Push to Talk) - future feature
        if (e.code === 'Space' && !e.repeat) {
            e.preventDefault();
            // Start listening
        }
        
        // Enter: Confirm pending command
        if (e.key === 'Enter' && this.pendingConfirmation) {
            e.preventDefault();
            this.confirmCommand();
        }
        
        // Escape: Cancel pending command
        if (e.key === 'Escape' && this.pendingConfirmation) {
            e.preventDefault();
            this.cancelCommand();
        }
    }
    
    loadSystemStatus() {
        fetch('/api/voice/status')
            .then(response => response.json())
            .then(status => {
                this.updateSystemStatus(status);
            })
            .catch(error => {
                console.error('Failed to load system status:', error);
            });
    }
}

// Initialize voice bridge client
const voiceBridge = new VoiceBridgeClient();