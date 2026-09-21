const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');
const WebSocket = require('ws');
const EventEmitter = require('events');

class VoiceListenerService extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'logs/voice-listener.log' })
      ]
    });

    this.audioBufferSize = config.audioBufferSize || 4096;
    this.sampleRate = config.sampleRate || 16000;
    this.channels = config.channels || 1;
    this.isListening = false;
    this.audioBuffer = [];
    this.transcriptionQueue = [];
    this.activeConnections = new Map();
    this.dmProfiles = new Map();
    this.sceneContext = null;
    
    this.speechServices = {
      google: null,
      openai: null,
      azure: null,
      aws: null
    };
    
    this.setupSpeechServices();
  }

  setupSpeechServices() {
    try {
      if (process.env.GOOGLE_CLOUD_SPEECH_API_KEY) {
        const speech = require('@google-cloud/speech');
        this.speechServices.google = new speech.SpeechClient({
          keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS
        });
      }

      if (process.env.OPENAI_API_KEY) {
        const { OpenAI } = require('openai');
        this.speechServices.openai = new OpenAI({
          apiKey: process.env.OPENAI_API_KEY
        });
      }

      if (process.env.AZURE_SPEECH_KEY) {
        const speechSDK = require('microsoft-cognitiveservices-speech-sdk');
        this.speechServices.azure = speechSDK.SpeechConfig.fromSubscription(
          process.env.AZURE_SPEECH_KEY,
          process.env.AZURE_SPEECH_REGION || 'eastus'
        );
      }

      this.logger.info('Speech services configured');
    } catch (error) {
      this.logger.warn('Some speech services unavailable:', error.message);
      this.mockMode = true;
    }
  }

  async initialize() {
    try {
      this.logger.info('Initializing Voice Listener Service');
      
      await this.setupAudioProcessing();
      await this.loadDMProfiles();
      await this.setupKeywordDetection();
      await this.setupNaturalLanguageProcessing();
      
      this.logger.info('Voice Listener Service initialized successfully');
      return true;
    } catch (error) {
      this.logger.error('Failed to initialize Voice Listener Service:', error);
      return false;
    }
  }

  async setupAudioProcessing() {
    this.audioConfig = {
      sampleRate: this.sampleRate,
      channels: this.channels,
      bitDepth: 16,
      bufferSize: this.audioBufferSize,
      format: 'LINEAR16'
    };
    
    this.voiceActivityDetection = {
      threshold: 0.01,
      minSilenceDuration: 500,
      maxSilenceDuration: 2000,
      active: false,
      silenceStart: null
    };
    
    this.logger.info('Audio processing configured');
  }

  async loadDMProfiles() {
    this.dmProfiles.set('default', {
      id: 'default',
      name: 'Default DM',
      voiceCharacteristics: {
        pitch: 'medium',
        speed: 'normal',
        accent: 'neutral'
      },
      vocabulary: this.getDefaultDMVocabulary(),
      speakingPatterns: this.getDefaultSpeakingPatterns(),
      preferences: {
        descriptiveStyle: 'detailed',
        narrativePacing: 'moderate',
        characterVoices: true
      }
    });
    
    this.logger.info('DM profiles loaded');
  }

  getDefaultDMVocabulary() {
    return {
      actions: [
        'roll', 'attack', 'cast', 'move', 'defend', 'heal', 'dodge', 'block',
        'investigate', 'persuade', 'stealth', 'perception', 'insight'
      ],
      creatures: [
        'goblin', 'orc', 'dragon', 'skeleton', 'zombie', 'wizard', 'knight',
        'troll', 'giant', 'wolf', 'bear', 'spider', 'demon', 'angel'
      ],
      locations: [
        'tavern', 'dungeon', 'forest', 'castle', 'cave', 'mountain', 'village',
        'city', 'ruins', 'temple', 'bridge', 'tower', 'chamber', 'hall'
      ],
      items: [
        'sword', 'shield', 'potion', 'scroll', 'armor', 'bow', 'arrow',
        'staff', 'wand', 'ring', 'amulet', 'treasure', 'key', 'torch'
      ],
      emotions: [
        'angry', 'scared', 'excited', 'confused', 'determined', 'surprised',
        'suspicious', 'confident', 'worried', 'pleased', 'frustrated'
      ]
    };
  }

  getDefaultSpeakingPatterns() {
    return {
      narrativeMarkers: [
        'as you enter', 'you see', 'you hear', 'you feel', 'you notice',
        'suddenly', 'meanwhile', 'in the distance', 'from behind', 'above you'
      ],
      transitionPhrases: [
        'moving on', 'next', 'then', 'after that', 'meanwhile',
        'at the same time', 'shortly after', 'moments later'
      ],
      questionPatterns: [
        'what do you do', 'how do you respond', 'what\'s your action',
        'roll for', 'give me a', 'make a', 'what do you want to'
      ],
      characterVoiceMarkers: [
        'he says', 'she whispers', 'it growls', 'they shout', 'the voice echoes',
        'speaking in', 'with a', 'tone', 'accent'
      ]
    };
  }

  async setupKeywordDetection() {
    this.keywordDetector = {
      sceneTransitions: [
        'new scene', 'scene change', 'cut to', 'meanwhile', 'elsewhere',
        'back to', 'switching to', 'in another', 'later'
      ],
      combatTriggers: [
        'roll initiative', 'combat begins', 'battle starts', 'attack',
        'fighting', 'initiative order', 'round one'
      ],
      characterActions: [
        'casts spell', 'swings sword', 'shoots arrow', 'uses ability',
        'moves to', 'attacks', 'defends', 'hides'
      ],
      environmentalCues: [
        'room description', 'you enter', 'you see', 'the area',
        'lighting', 'atmosphere', 'weather', 'terrain'
      ]
    };
    
    this.logger.info('Keyword detection configured');
  }

  async setupNaturalLanguageProcessing() {
    this.nlpConfig = {
      sentimentAnalysis: true,
      intentRecognition: true,
      entityExtraction: true,
      contextualUnderstanding: true
    };
    
    this.contextTracking = {
      currentScene: null,
      activeCharacters: [],
      currentLocation: null,
      sceneMetadata: {},
      conversationHistory: [],
      lastSpeaker: null
    };
    
    this.logger.info('Natural language processing configured');
  }

  async startListening(connectionId, audioConfig = {}) {
    try {
      this.logger.info(`Starting voice listening for connection: ${connectionId}`);
      
      const connection = {
        id: connectionId,
        audioConfig: { ...this.audioConfig, ...audioConfig },
        isActive: true,
        startTime: Date.now(),
        transcriptionBuffer: [],
        lastActivity: Date.now()
      };
      
      this.activeConnections.set(connectionId, connection);
      this.isListening = true;
      
      this.emit('listeningStarted', { connectionId, timestamp: Date.now() });
      
      if (this.mockMode) {
        this.simulateVoiceInput(connectionId);
      }
      
      return {
        connectionId,
        status: 'listening',
        audioConfig: connection.audioConfig
      };
    } catch (error) {
      this.logger.error('Failed to start voice listening:', error);
      throw error;
    }
  }

  async simulateVoiceInput(connectionId) {
    const mockNarrations = [
      "You enter a dimly lit tavern. The air is thick with smoke and the sound of conversation.",
      "A hooded figure approaches your table, their footsteps barely audible on the wooden floor.",
      "Roll for initiative! A group of bandits bursts through the door, weapons drawn.",
      "The wizard begins casting a spell, arcane energy crackling around their hands.",
      "You hear the sound of metal on stone as the rogue attempts to pick the lock.",
      "The dragon's roar echoes through the mountain pass as it descends from above."
    ];
    
    let index = 0;
    const interval = setInterval(() => {
      if (!this.activeConnections.has(connectionId)) {
        clearInterval(interval);
        return;
      }
      
      const narration = mockNarrations[index % mockNarrations.length];
      this.processTranscription(connectionId, narration);
      index++;
    }, 5000);
  }

  async processAudioStream(connectionId, audioData) {
    try {
      const connection = this.activeConnections.get(connectionId);
      if (!connection) {
        throw new Error(`Connection not found: ${connectionId}`);
      }
      
      connection.lastActivity = Date.now();
      
      const isVoiceActive = this.detectVoiceActivity(audioData);
      
      if (isVoiceActive) {
        this.audioBuffer.push(audioData);
        
        if (this.audioBuffer.length >= 10) {
          const audioChunk = Buffer.concat(this.audioBuffer);
          this.audioBuffer = [];
          
          const transcription = await this.transcribeAudio(audioChunk);
          if (transcription && transcription.trim().length > 0) {
            await this.processTranscription(connectionId, transcription);
          }
        }
      }
      
      this.emit('audioProcessed', {
        connectionId,
        voiceActive: isVoiceActive,
        bufferSize: this.audioBuffer.length
      });
    } catch (error) {
      this.logger.error('Audio stream processing failed:', error);
    }
  }

  detectVoiceActivity(audioData) {
    if (!audioData || audioData.length === 0) return false;
    
    let sum = 0;
    for (let i = 0; i < audioData.length; i += 2) {
      const sample = audioData.readInt16LE(i);
      sum += Math.abs(sample);
    }
    
    const average = sum / (audioData.length / 2);
    const normalizedLevel = average / 32768;
    
    const isActive = normalizedLevel > this.voiceActivityDetection.threshold;
    
    if (!isActive) {
      if (this.voiceActivityDetection.active && !this.voiceActivityDetection.silenceStart) {
        this.voiceActivityDetection.silenceStart = Date.now();
      } else if (this.voiceActivityDetection.silenceStart) {
        const silenceDuration = Date.now() - this.voiceActivityDetection.silenceStart;
        if (silenceDuration > this.voiceActivityDetection.minSilenceDuration) {
          this.voiceActivityDetection.active = false;
          this.voiceActivityDetection.silenceStart = null;
        }
      }
    } else {
      this.voiceActivityDetection.active = true;
      this.voiceActivityDetection.silenceStart = null;
    }
    
    return this.voiceActivityDetection.active;
  }

  async transcribeAudio(audioBuffer) {
    try {
      if (this.mockMode) {
        return this.generateMockTranscription();
      }
      
      if (this.speechServices.openai) {
        return await this.transcribeWithOpenAI(audioBuffer);
      } else if (this.speechServices.google) {
        return await this.transcribeWithGoogle(audioBuffer);
      } else if (this.speechServices.azure) {
        return await this.transcribeWithAzure(audioBuffer);
      }
      
      return null;
    } catch (error) {
      this.logger.error('Audio transcription failed:', error);
      return null;
    }
  }

  generateMockTranscription() {
    const mockPhrases = [
      "The goblin attacks with its rusty sword",
      "You notice a glint of gold in the corner",
      "The wizard casts fireball at the enemies",
      "Roll a perception check",
      "The door creaks open slowly",
      "You hear footsteps approaching"
    ];
    
    return mockPhrases[Math.floor(Math.random() * mockPhrases.length)];
  }

  async transcribeWithOpenAI(audioBuffer) {
    try {
      const audioFile = Buffer.from(audioBuffer);
      
      const transcription = await this.speechServices.openai.audio.transcriptions.create({
        file: audioFile,
        model: "whisper-1",
        language: "en"
      });
      
      return transcription.text;
    } catch (error) {
      this.logger.error('OpenAI transcription failed:', error);
      return null;
    }
  }

  async transcribeWithGoogle(audioBuffer) {
    try {
      const audio = {
        content: audioBuffer.toString('base64')
      };
      
      const config = {
        encoding: 'LINEAR16',
        sampleRateHertz: this.sampleRate,
        languageCode: 'en-US',
        enableAutomaticPunctuation: true,
        model: 'latest_long'
      };
      
      const request = {
        audio: audio,
        config: config
      };
      
      const [response] = await this.speechServices.google.recognize(request);
      
      if (response.results && response.results.length > 0) {
        return response.results[0].alternatives[0].transcript;
      }
      
      return null;
    } catch (error) {
      this.logger.error('Google Speech transcription failed:', error);
      return null;
    }
  }

  async transcribeWithAzure(audioBuffer) {
    try {
      const audioConfig = require('microsoft-cognitiveservices-speech-sdk').AudioConfig.fromWavFileInput(audioBuffer);
      const recognizer = new (require('microsoft-cognitiveservices-speech-sdk').SpeechRecognizer)(
        this.speechServices.azure,
        audioConfig
      );
      
      return new Promise((resolve, reject) => {
        recognizer.recognizeOnceAsync(
          (result) => {
            recognizer.close();
            resolve(result.text);
          },
          (error) => {
            recognizer.close();
            reject(error);
          }
        );
      });
    } catch (error) {
      this.logger.error('Azure Speech transcription failed:', error);
      return null;
    }
  }

  async processTranscription(connectionId, transcription) {
    try {
      this.logger.info(`Processing transcription: ${transcription.substring(0, 100)}...`);
      
      const connection = this.activeConnections.get(connectionId);
      if (!connection) return;
      
      const analysis = await this.analyzeNarration(transcription);
      const sceneData = await this.extractSceneInformation(transcription, analysis);
      
      this.updateContextTracking(analysis, sceneData);
      
      connection.transcriptionBuffer.push({
        text: transcription,
        timestamp: Date.now(),
        analysis,
        sceneData
      });
      
      this.emit('transcriptionProcessed', {
        connectionId,
        transcription,
        analysis,
        sceneData,
        timestamp: Date.now()
      });
      
      if (analysis.triggerVisualization) {
        this.emit('visualizationTrigger', {
          connectionId,
          sceneData,
          analysis,
          timestamp: Date.now()
        });
      }
    } catch (error) {
      this.logger.error('Transcription processing failed:', error);
    }
  }

  async analyzeNarration(text) {
    const analysis = {
      type: 'narration',
      confidence: 0.8,
      intent: null,
      entities: [],
      sentiment: 'neutral',
      keywords: [],
      triggerVisualization: false,
      sceneType: null,
      actionRequired: false
    };
    
    const lowercaseText = text.toLowerCase();
    
    for (const [category, keywords] of Object.entries(this.keywordDetector)) {
      for (const keyword of keywords) {
        if (lowercaseText.includes(keyword.toLowerCase())) {
          analysis.keywords.push({ category, keyword, confidence: 0.9 });
          
          if (category === 'sceneTransitions') {
            analysis.type = 'scene_transition';
            analysis.triggerVisualization = true;
          } else if (category === 'combatTriggers') {
            analysis.type = 'combat_start';
            analysis.triggerVisualization = true;
          } else if (category === 'characterActions') {
            analysis.type = 'character_action';
            analysis.triggerVisualization = true;
          } else if (category === 'environmentalCues') {
            analysis.type = 'environment_description';
            analysis.triggerVisualization = true;
          }
        }
      }
    }
    
    analysis.entities = this.extractEntities(text);
    analysis.sentiment = this.analyzeSentiment(text);
    analysis.intent = this.determineIntent(text, analysis);
    
    return analysis;
  }

  extractEntities(text) {
    const entities = [];
    const vocabulary = this.dmProfiles.get('default').vocabulary;
    
    for (const [category, words] of Object.entries(vocabulary)) {
      for (const word of words) {
        const regex = new RegExp(`\\b${word}\\b`, 'gi');
        const matches = text.match(regex);
        if (matches) {
          entities.push({
            type: category,
            value: word,
            confidence: 0.8,
            occurrences: matches.length
          });
        }
      }
    }
    
    return entities;
  }

  analyzeSentiment(text) {
    const positiveWords = ['good', 'great', 'excellent', 'wonderful', 'amazing', 'success', 'victory'];
    const negativeWords = ['bad', 'terrible', 'awful', 'horrible', 'danger', 'threat', 'death', 'fear'];
    
    const lowercaseText = text.toLowerCase();
    let positiveCount = 0;
    let negativeCount = 0;
    
    for (const word of positiveWords) {
      if (lowercaseText.includes(word)) positiveCount++;
    }
    
    for (const word of negativeWords) {
      if (lowercaseText.includes(word)) negativeCount++;
    }
    
    if (positiveCount > negativeCount) return 'positive';
    if (negativeCount > positiveCount) return 'negative';
    return 'neutral';
  }

  determineIntent(text, analysis) {
    if (analysis.keywords.some(k => k.category === 'combatTriggers')) {
      return 'start_combat';
    } else if (analysis.keywords.some(k => k.category === 'sceneTransitions')) {
      return 'change_scene';
    } else if (analysis.keywords.some(k => k.category === 'characterActions')) {
      return 'character_action';
    } else if (text.includes('?') || analysis.keywords.some(k => k.keyword.includes('roll'))) {
      return 'request_action';
    } else {
      return 'narrate';
    }
  }

  async extractSceneInformation(text, analysis) {
    const sceneData = {
      location: null,
      characters: [],
      objects: [],
      atmosphere: null,
      lighting: 'normal',
      weather: null,
      timeOfDay: null,
      actions: [],
      dialogue: []
    };
    
    sceneData.location = this.extractLocation(text);
    sceneData.characters = this.extractCharacters(text, analysis);
    sceneData.objects = this.extractObjects(text, analysis);
    sceneData.atmosphere = this.extractAtmosphere(text);
    sceneData.lighting = this.extractLighting(text);
    sceneData.actions = this.extractActions(text, analysis);
    
    return sceneData;
  }

  extractLocation(text) {
    const locationKeywords = this.dmProfiles.get('default').vocabulary.locations;
    
    for (const location of locationKeywords) {
      if (text.toLowerCase().includes(location)) {
        return location;
      }
    }
    
    return null;
  }

  extractCharacters(text, analysis) {
    const characters = [];
    const creatureEntities = analysis.entities.filter(e => e.type === 'creatures');
    
    for (const entity of creatureEntities) {
      characters.push({
        type: entity.value,
        name: entity.value,
        count: entity.occurrences || 1
      });
    }
    
    return characters;
  }

  extractObjects(text, analysis) {
    const objects = [];
    const itemEntities = analysis.entities.filter(e => e.type === 'items');
    
    for (const entity of itemEntities) {
      objects.push({
        type: entity.value,
        name: entity.value,
        description: null
      });
    }
    
    return objects;
  }

  extractAtmosphere(text) {
    const atmosphereKeywords = {
      dark: ['dark', 'gloomy', 'shadowy', 'dim'],
      bright: ['bright', 'luminous', 'radiant', 'brilliant'],
      mysterious: ['mysterious', 'enigmatic', 'strange', 'eerie'],
      peaceful: ['peaceful', 'calm', 'serene', 'quiet'],
      threatening: ['threatening', 'menacing', 'dangerous', 'hostile']
    };
    
    const lowercaseText = text.toLowerCase();
    
    for (const [atmosphere, keywords] of Object.entries(atmosphereKeywords)) {
      for (const keyword of keywords) {
        if (lowercaseText.includes(keyword)) {
          return atmosphere;
        }
      }
    }
    
    return 'neutral';
  }

  extractLighting(text) {
    const lightingKeywords = {
      dim: ['dim', 'dimly', 'faint', 'flickering'],
      bright: ['bright', 'brilliant', 'blazing', 'glowing'],
      dark: ['dark', 'pitch black', 'unlit', 'shadowy']
    };
    
    const lowercaseText = text.toLowerCase();
    
    for (const [lighting, keywords] of Object.entries(lightingKeywords)) {
      for (const keyword of keywords) {
        if (lowercaseText.includes(keyword)) {
          return lighting;
        }
      }
    }
    
    return 'normal';
  }

  extractActions(text, analysis) {
    const actions = [];
    const actionEntities = analysis.entities.filter(e => e.type === 'actions');
    
    for (const entity of actionEntities) {
      actions.push({
        type: entity.value,
        description: text,
        timestamp: Date.now()
      });
    }
    
    return actions;
  }

  updateContextTracking(analysis, sceneData) {
    if (sceneData.location) {
      this.contextTracking.currentLocation = sceneData.location;
    }
    
    if (sceneData.characters.length > 0) {
      this.contextTracking.activeCharacters = sceneData.characters;
    }
    
    this.contextTracking.conversationHistory.push({
      analysis,
      sceneData,
      timestamp: Date.now()
    });
    
    if (this.contextTracking.conversationHistory.length > 50) {
      this.contextTracking.conversationHistory = this.contextTracking.conversationHistory.slice(-25);
    }
  }

  async stopListening(connectionId) {
    try {
      const connection = this.activeConnections.get(connectionId);
      if (!connection) {
        throw new Error(`Connection not found: ${connectionId}`);
      }
      
      connection.isActive = false;
      this.activeConnections.delete(connectionId);
      
      if (this.activeConnections.size === 0) {
        this.isListening = false;
      }
      
      this.emit('listeningStopped', { connectionId, timestamp: Date.now() });
      
      this.logger.info(`Voice listening stopped for connection: ${connectionId}`);
      
      return {
        connectionId,
        status: 'stopped',
        duration: Date.now() - connection.startTime,
        transcriptionCount: connection.transcriptionBuffer.length
      };
    } catch (error) {
      this.logger.error('Failed to stop voice listening:', error);
      throw error;
    }
  }

  async getTranscriptionHistory(connectionId, limit = 10) {
    const connection = this.activeConnections.get(connectionId);
    if (!connection) {
      throw new Error(`Connection not found: ${connectionId}`);
    }
    
    return connection.transcriptionBuffer.slice(-limit);
  }

  async getContextualData() {
    return {
      currentContext: this.contextTracking,
      activeConnections: Array.from(this.activeConnections.keys()),
      isListening: this.isListening,
      lastUpdate: Date.now()
    };
  }

  async cleanup() {
    try {
      this.logger.info('Cleaning up Voice Listener Service');
      
      for (const connectionId of this.activeConnections.keys()) {
        await this.stopListening(connectionId);
      }
      
      this.activeConnections.clear();
      this.audioBuffer = [];
      this.transcriptionQueue = [];
      this.isListening = false;
      
      this.logger.info('Voice Listener Service cleanup completed');
    } catch (error) {
      this.logger.error('Voice Listener Service cleanup failed:', error);
    }
  }
}

module.exports = VoiceListenerService;