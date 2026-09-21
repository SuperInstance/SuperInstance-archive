const EventEmitter = require('events');
const logger = require('../core/logger');

class VoiceControl extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Voice recognition settings
      language: options.language || 'en-US',
      continuous: options.continuous !== false,
      interimResults: options.interimResults !== false,
      maxAlternatives: options.maxAlternatives || 3,
      
      // Command processing
      confidenceThreshold: options.confidenceThreshold || 0.7,
      commandTimeout: options.commandTimeout || 5000,
      
      // Security settings
      requireActivation: options.requireActivation !== false,
      activationPhrase: options.activationPhrase || 'hey remote',
      allowedCommands: options.allowedCommands || 'all',
      
      ...options
    };

    // Voice commands registry
    this.commands = new Map();
    this.isListening = false;
    this.isActive = false;
    this.currentSession = null;
    
    // Processing state
    this.recognitionEngine = null;
    this.commandQueue = [];
    this.lastCommand = null;
    
    // Metrics
    this.metrics = {
      totalCommands: 0,
      successfulCommands: 0,
      failedCommands: 0,
      averageConfidence: 0,
      recognitionErrors: 0,
      activationCount: 0
    };
    
    // Initialize default commands
    this.initializeDefaultCommands();
  }

  async initialize() {
    logger.info('Initializing Voice Control system...');
    
    try {
      // Initialize speech recognition (simulated for demo)
      await this.initializeSpeechRecognition();
      
      // Setup command processing
      this.setupCommandProcessing();
      
      logger.info('Voice Control system initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Voice Control:', error);
      throw error;
    }
  }

  async initializeSpeechRecognition() {
    // In a real implementation, this would initialize Web Speech API or native speech recognition
    logger.info('Speech recognition engine initialized (simulated)');
    
    this.recognitionEngine = {
      lang: this.options.language,
      continuous: this.options.continuous,
      interimResults: this.options.interimResults,
      maxAlternatives: this.options.maxAlternatives,
      
      // Simulated methods
      start: () => {
        this.isListening = true;
        logger.debug('Speech recognition started');
        this.emit('listening-started');
      },
      
      stop: () => {
        this.isListening = false;
        logger.debug('Speech recognition stopped');
        this.emit('listening-stopped');
      }
    };
  }

  initializeDefaultCommands() {
    // Navigation commands
    this.registerCommand('scroll up', this.scrollUp.bind(this), 'navigation');
    this.registerCommand('scroll down', this.scrollDown.bind(this), 'navigation');
    this.registerCommand('go back', this.goBack.bind(this), 'navigation');
    this.registerCommand('go forward', this.goForward.bind(this), 'navigation');
    this.registerCommand('refresh page', this.refreshPage.bind(this), 'navigation');
    
    // Window management
    this.registerCommand('minimize window', this.minimizeWindow.bind(this), 'window');
    this.registerCommand('maximize window', this.maximizeWindow.bind(this), 'window');
    this.registerCommand('close window', this.closeWindow.bind(this), 'window');
    this.registerCommand('next window', this.nextWindow.bind(this), 'window');
    this.registerCommand('switch to desktop', this.switchToDesktop.bind(this), 'window');
    
    // System commands
    this.registerCommand('open calculator', () => this.openApplication('calculator'), 'system');
    this.registerCommand('open notepad', () => this.openApplication('notepad'), 'system');
    this.registerCommand('open browser', () => this.openApplication('browser'), 'system');
    this.registerCommand('lock screen', this.lockScreen.bind(this), 'system');
    
    // Remote control specific
    this.registerCommand('stop sharing', this.stopSharing.bind(this), 'remote');
    this.registerCommand('start sharing', this.startSharing.bind(this), 'remote');
    this.registerCommand('pause streaming', this.pauseStreaming.bind(this), 'remote');
    this.registerCommand('resume streaming', this.resumeStreaming.bind(this), 'remote');
    this.registerCommand('disconnect all', this.disconnectAll.bind(this), 'remote');
    
    // Voice control
    this.registerCommand('stop listening', this.stopListening.bind(this), 'voice');
    this.registerCommand('sleep', this.deactivate.bind(this), 'voice');
    
    logger.info(`Registered ${this.commands.size} default voice commands`);
  }

  registerCommand(phrase, handler, category = 'custom') {
    const command = {
      phrase: phrase.toLowerCase(),
      handler,
      category,
      registered: Date.now(),
      usage: 0,
      lastUsed: null
    };
    
    this.commands.set(phrase.toLowerCase(), command);
    
    logger.debug(`Registered voice command: "${phrase}" (${category})`);
    return command;
  }

  unregisterCommand(phrase) {
    const removed = this.commands.delete(phrase.toLowerCase());
    if (removed) {
      logger.debug(`Unregistered voice command: "${phrase}"`);
    }
    return removed;
  }

  async startListening() {
    if (this.isListening) {
      logger.warn('Voice recognition already listening');
      return;
    }

    try {
      this.recognitionEngine.start();
      logger.info('Voice recognition started');
      
      // Simulate speech recognition events
      this.simulateSpeechRecognition();
      
    } catch (error) {
      logger.error('Failed to start voice recognition:', error);
      throw error;
    }
  }

  async stopListening() {
    if (!this.isListening) {
      logger.warn('Voice recognition not currently listening');
      return;
    }

    try {
      this.recognitionEngine.stop();
      logger.info('Voice recognition stopped');
    } catch (error) {
      logger.error('Failed to stop voice recognition:', error);
    }
  }

  async activate() {
    if (this.isActive) return;
    
    this.isActive = true;
    this.metrics.activationCount++;
    
    logger.info('Voice control activated');
    this.emit('activated');
    
    if (!this.isListening) {
      await this.startListening();
    }
  }

  async deactivate() {
    if (!this.isActive) return;
    
    this.isActive = false;
    
    if (this.isListening) {
      await this.stopListening();
    }
    
    logger.info('Voice control deactivated');
    this.emit('deactivated');
  }

  simulateSpeechRecognition() {
    // Simulate occasional voice commands for demo
    if (!this.isListening) return;
    
    const commands = [
      'scroll down',
      'minimize window',
      'open browser',
      'stop sharing',
      'refresh page'
    ];
    
    setTimeout(() => {
      if (this.isListening && Math.random() > 0.8) {
        const command = commands[Math.floor(Math.random() * commands.length)];
        this.processRecognitionResult({
          transcript: command,
          confidence: 0.8 + Math.random() * 0.2,
          isFinal: true
        });
      }
      
      // Continue simulation
      if (this.isListening) {
        this.simulateSpeechRecognition();
      }
    }, 3000 + Math.random() * 7000); // 3-10 seconds
  }

  async processRecognitionResult(result) {
    try {
      const { transcript, confidence, isFinal } = result;
      
      if (!isFinal || confidence < this.options.confidenceThreshold) {
        return;
      }
      
      const cleanTranscript = transcript.toLowerCase().trim();
      
      // Check for activation phrase
      if (this.options.requireActivation && !this.isActive) {
        if (cleanTranscript.includes(this.options.activationPhrase)) {
          await this.activate();
          return;
        }
        return; // Ignore commands when not activated
      }
      
      // Find matching command
      const command = this.findMatchingCommand(cleanTranscript);
      
      if (command) {
        await this.executeCommand(command, transcript, confidence);
      } else {
        logger.debug(`No matching command found for: "${cleanTranscript}"`);
        this.handleUnknownCommand(cleanTranscript, confidence);
      }
      
    } catch (error) {
      logger.error('Error processing recognition result:', error);
      this.metrics.recognitionErrors++;
    }
  }

  findMatchingCommand(transcript) {
    // Exact match first
    if (this.commands.has(transcript)) {
      return this.commands.get(transcript);
    }
    
    // Fuzzy matching - find commands that are contained in the transcript
    for (const [phrase, command] of this.commands) {
      if (transcript.includes(phrase) || phrase.includes(transcript)) {
        return command;
      }
    }
    
    // Partial word matching
    const words = transcript.split(' ');
    for (const [phrase, command] of this.commands) {
      const commandWords = phrase.split(' ');
      const matchCount = commandWords.filter(word => words.includes(word)).length;
      
      if (matchCount >= Math.ceil(commandWords.length * 0.7)) {
        return command;
      }
    }
    
    return null;
  }

  async executeCommand(command, originalTranscript, confidence) {
    const startTime = Date.now();
    
    try {
      logger.info(`Executing voice command: "${command.phrase}"`, {
        originalTranscript,
        confidence: confidence.toFixed(2)
      });
      
      // Check if command is allowed
      if (this.options.allowedCommands !== 'all' && 
          !this.options.allowedCommands.includes(command.category)) {
        logger.warn(`Command category '${command.category}' not allowed`);
        return { success: false, error: 'Command not allowed' };
      }
      
      // Execute the command
      const result = await command.handler(originalTranscript, confidence);
      
      // Update command statistics
      command.usage++;
      command.lastUsed = Date.now();
      
      // Update metrics
      this.metrics.totalCommands++;
      this.metrics.successfulCommands++;
      this.metrics.averageConfidence = (this.metrics.averageConfidence + confidence) / 2;
      
      const executionTime = Date.now() - startTime;
      
      this.emit('command-executed', {
        command: command.phrase,
        originalTranscript,
        confidence,
        executionTime,
        result
      });
      
      return { success: true, result, executionTime };
      
    } catch (error) {
      logger.error(`Command execution failed: ${command.phrase}`, error);
      
      this.metrics.failedCommands++;
      
      this.emit('command-failed', {
        command: command.phrase,
        originalTranscript,
        error: error.message
      });
      
      return { success: false, error: error.message };
    }
  }

  handleUnknownCommand(transcript, confidence) {
    this.emit('unknown-command', {
      transcript,
      confidence
    });
    
    // Could implement learning or suggestion features here
    logger.debug('Unknown command could be learned or suggested');
  }

  setupCommandProcessing() {
    // Process queued commands
    setInterval(() => {
      if (this.commandQueue.length > 0) {
        const { command, transcript, confidence } = this.commandQueue.shift();
        this.executeCommand(command, transcript, confidence);
      }
    }, 100);
  }

  // Default command implementations
  async scrollUp() {
    this.emit('scroll-command', { direction: 'up', amount: 3 });
    return { action: 'scroll', direction: 'up' };
  }

  async scrollDown() {
    this.emit('scroll-command', { direction: 'down', amount: 3 });
    return { action: 'scroll', direction: 'down' };
  }

  async goBack() {
    this.emit('navigation-command', { action: 'back' });
    return { action: 'navigation', direction: 'back' };
  }

  async goForward() {
    this.emit('navigation-command', { action: 'forward' });
    return { action: 'navigation', direction: 'forward' };
  }

  async refreshPage() {
    this.emit('navigation-command', { action: 'refresh' });
    return { action: 'refresh' };
  }

  async minimizeWindow() {
    this.emit('window-command', { action: 'minimize' });
    return { action: 'window', operation: 'minimize' };
  }

  async maximizeWindow() {
    this.emit('window-command', { action: 'maximize' });
    return { action: 'window', operation: 'maximize' };
  }

  async closeWindow() {
    this.emit('window-command', { action: 'close' });
    return { action: 'window', operation: 'close' };
  }

  async nextWindow() {
    this.emit('window-command', { action: 'next' });
    return { action: 'window', operation: 'next' };
  }

  async switchToDesktop() {
    this.emit('window-command', { action: 'desktop' });
    return { action: 'window', operation: 'desktop' };
  }

  async openApplication(appName) {
    this.emit('app-command', { action: 'open', application: appName });
    return { action: 'application', operation: 'open', app: appName };
  }

  async lockScreen() {
    this.emit('system-command', { action: 'lock' });
    return { action: 'system', operation: 'lock' };
  }

  async stopSharing() {
    this.emit('remote-command', { action: 'stop-sharing' });
    return { action: 'remote', operation: 'stop-sharing' };
  }

  async startSharing() {
    this.emit('remote-command', { action: 'start-sharing' });
    return { action: 'remote', operation: 'start-sharing' };
  }

  async pauseStreaming() {
    this.emit('remote-command', { action: 'pause-streaming' });
    return { action: 'remote', operation: 'pause-streaming' };
  }

  async resumeStreaming() {
    this.emit('remote-command', { action: 'resume-streaming' });
    return { action: 'remote', operation: 'resume-streaming' };
  }

  async disconnectAll() {
    this.emit('remote-command', { action: 'disconnect-all' });
    return { action: 'remote', operation: 'disconnect-all' };
  }

  // Public API methods
  getCommands() {
    return Array.from(this.commands.values()).map(cmd => ({
      phrase: cmd.phrase,
      category: cmd.category,
      usage: cmd.usage,
      lastUsed: cmd.lastUsed
    }));
  }

  getCommandsByCategory(category) {
    return Array.from(this.commands.values())
      .filter(cmd => cmd.category === category)
      .map(cmd => ({
        phrase: cmd.phrase,
        usage: cmd.usage,
        lastUsed: cmd.lastUsed
      }));
  }

  isListeningActive() {
    return this.isListening;
  }

  isVoiceActive() {
    return this.isActive;
  }

  getMetrics() {
    return {
      ...this.metrics,
      totalCommands: this.commands.size,
      isListening: this.isListening,
      isActive: this.isActive
    };
  }

  async cleanup() {
    await this.stopListening();
    this.deactivate();
    
    this.commands.clear();
    this.commandQueue = [];
    
    this.removeAllListeners();
    logger.info('Voice Control system cleaned up');
  }
}

module.exports = VoiceControl;