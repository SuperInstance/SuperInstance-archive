const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');
const EventEmitter = require('events');

class SceneGeneratorService extends EventEmitter {
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
        new winston.transports.File({ filename: 'logs/scene-generator.log' })
      ]
    });

    this.aiService = null;
    this.sceneTemplates = new Map();
    this.generationQueue = [];
    this.isProcessing = false;
    this.generatedScenes = new Map();
    this.contextHistory = [];
    
    this.setupAIService();
  }

  setupAIService() {
    try {
      if (process.env.OPENAI_API_KEY) {
        const { OpenAI } = require('openai');
        this.aiService = new OpenAI({
          apiKey: process.env.OPENAI_API_KEY
        });
      }
      
      this.logger.info('AI service configured');
    } catch (error) {
      this.logger.warn('AI service unavailable, using template-based generation:', error.message);
      this.mockMode = true;
    }
  }

  async initialize() {
    try {
      this.logger.info('Initializing Scene Generator Service');
      
      await this.loadSceneTemplates();
      await this.setupGenerationRules();
      await this.loadNarrativePatterns();
      
      this.logger.info('Scene Generator Service initialized successfully');
      return true;
    } catch (error) {
      this.logger.error('Failed to initialize Scene Generator Service:', error);
      return false;
    }
  }

  async loadSceneTemplates() {
    this.sceneTemplates.set('tavern', {
      type: 'social',
      environment: {
        setting: 'indoor',
        lighting: 'warm',
        atmosphere: 'cozy',
        soundscape: ['crackling fire', 'conversation murmur', 'clinking glasses']
      },
      characters: {
        npcs: ['bartender', 'patron', 'bard'],
        maxCapacity: 12,
        interactionTypes: ['conversation', 'drinking', 'listening to music']
      },
      objects: ['tables', 'chairs', 'bar', 'fireplace', 'barrels', 'candles'],
      cameraAngles: [
        { name: 'wide_shot', position: { x: 0, y: 3, z: -8 }, target: { x: 0, y: 1, z: 0 } },
        { name: 'medium_shot', position: { x: 2, y: 2, z: -4 }, target: { x: 0, y: 1.5, z: 0 } },
        { name: 'close_up', position: { x: 1, y: 1.8, z: -2 }, target: { x: 0, y: 1.7, z: 0 } }
      ]
    });

    this.sceneTemplates.set('dungeon_corridor', {
      type: 'exploration',
      environment: {
        setting: 'underground',
        lighting: 'dim',
        atmosphere: 'ominous',
        soundscape: ['dripping water', 'distant echoes', 'stone footsteps']
      },
      characters: {
        npcs: [],
        maxCapacity: 6,
        interactionTypes: ['exploration', 'trap detection', 'combat']
      },
      objects: ['torches', 'stone walls', 'doors', 'pressure plates', 'cobwebs'],
      cameraAngles: [
        { name: 'first_person', position: { x: 0, y: 1.7, z: 0 }, target: { x: 0, y: 1.7, z: 5 } },
        { name: 'over_shoulder', position: { x: -1, y: 2, z: -2 }, target: { x: 0, y: 1.5, z: 5 } },
        { name: 'wide_corridor', position: { x: 0, y: 4, z: -5 }, target: { x: 0, y: 1, z: 10 } }
      ]
    });

    this.sceneTemplates.set('forest_clearing', {
      type: 'outdoor',
      environment: {
        setting: 'outdoor',
        lighting: 'natural',
        atmosphere: 'mystical',
        soundscape: ['wind through trees', 'bird songs', 'rustling leaves']
      },
      characters: {
        npcs: ['forest creatures', 'druids', 'wildlife'],
        maxCapacity: 8,
        interactionTypes: ['nature communion', 'tracking', 'camping']
      },
      objects: ['trees', 'rocks', 'streams', 'flowers', 'logs', 'mushrooms'],
      cameraAngles: [
        { name: 'canopy_view', position: { x: 0, y: 12, z: -8 }, target: { x: 0, y: 0, z: 0 } },
        { name: 'ground_level', position: { x: 0, y: 2, z: -6 }, target: { x: 0, y: 1, z: 0 } },
        { name: 'through_trees', position: { x: 5, y: 3, z: -5 }, target: { x: 0, y: 1, z: 2 } }
      ]
    });

    this.sceneTemplates.set('throne_room', {
      type: 'political',
      environment: {
        setting: 'indoor',
        lighting: 'dramatic',
        atmosphere: 'imposing',
        soundscape: ['echoing footsteps', 'ceremonial music', 'whispered conversations']
      },
      characters: {
        npcs: ['monarch', 'guards', 'courtiers', 'advisors'],
        maxCapacity: 20,
        interactionTypes: ['audience', 'negotiation', 'ceremony']
      },
      objects: ['throne', 'banners', 'pillars', 'red carpet', 'weapons displays'],
      cameraAngles: [
        { name: 'throne_perspective', position: { x: 0, y: 3, z: -15 }, target: { x: 0, y: 2, z: 0 } },
        { name: 'subject_view', position: { x: 0, y: 1.8, z: 12 }, target: { x: 0, y: 3, z: 0 } },
        { name: 'side_angle', position: { x: 8, y: 2, z: 0 }, target: { x: 0, y: 2, z: 0 } }
      ]
    });

    this.logger.info('Scene templates loaded');
  }

  async setupGenerationRules() {
    this.generationRules = {
      contextWeight: 0.7,
      templateWeight: 0.3,
      minimumElements: 3,
      maximumElements: 15,
      coherenceThreshold: 0.8,
      diversityFactor: 0.6
    };

    this.elementWeights = {
      characters: 0.3,
      environment: 0.25,
      objects: 0.2,
      lighting: 0.1,
      audio: 0.1,
      camera: 0.05
    };

    this.transitionTypes = {
      cut: { weight: 0.4, description: 'Immediate scene change' },
      fade: { weight: 0.3, description: 'Gradual transition' },
      dissolve: { weight: 0.2, description: 'Overlapping transition' },
      wipe: { weight: 0.1, description: 'Directional transition' }
    };

    this.logger.info('Generation rules configured');
  }

  async loadNarrativePatterns() {
    this.narrativePatterns = {
      sceneStarters: [
        "As you enter {location}, {description}",
        "The scene opens with {characters} in {location}",
        "You find yourself in {location}, where {action}",
        "The camera reveals {location}, {atmosphere}"
      ],
      characterIntroductions: [
        "A {character_type} {action} near {object}",
        "You notice {character_description} {character_type}",
        "From {direction} comes {character_type}",
        "Standing by {object} is {character_description}"
      ],
      environmentDescriptions: [
        "The {lighting} light {light_action} across {surface}",
        "The atmosphere is {atmosphere}, with {sound_elements}",
        "The {weather} creates {visual_effect} throughout {location}",
        "You can {sense} the {environmental_quality} of this place"
      ],
      actionPrompts: [
        "What do you do as {situation}?",
        "How do you respond to {event}?",
        "The {character} {action}. What is your reaction?",
        "You notice {detail}. What's your next move?"
      ]
    };

    this.logger.info('Narrative patterns loaded');
  }

  async generateSceneFromVoice(voiceData) {
    try {
      this.logger.info('Generating scene from voice input');
      
      const sceneId = `generated_${Date.now()}`;
      const analysis = voiceData.analysis;
      const context = voiceData.sceneData;
      
      let sceneDescription;
      
      if (this.aiService && !this.mockMode) {
        sceneDescription = await this.generateWithAI(analysis, context);
      } else {
        sceneDescription = await this.generateWithTemplate(analysis, context);
      }
      
      const visualScene = await this.convertToVisualScene(sceneDescription, context);
      
      this.generatedScenes.set(sceneId, {
        id: sceneId,
        description: sceneDescription,
        visualScene,
        sourceAnalysis: analysis,
        context,
        timestamp: Date.now()
      });
      
      this.updateContextHistory(sceneDescription, context);
      
      this.emit('sceneGenerated', {
        sceneId,
        sceneDescription,
        visualScene,
        timestamp: Date.now()
      });
      
      return {
        sceneId,
        status: 'generated',
        description: sceneDescription,
        visualScene,
        metadata: {
          sourceType: 'voice',
          aiGenerated: !this.mockMode,
          elementCount: this.countSceneElements(visualScene)
        }
      };
    } catch (error) {
      this.logger.error('Scene generation from voice failed:', error);
      throw error;
    }
  }

  async generateWithAI(analysis, context) {
    try {
      const prompt = this.buildAIPrompt(analysis, context);
      
      const completion = await this.aiService.chat.completions.create({
        model: "gpt-4",
        messages: [
          {
            role: "system",
            content: "You are a master dungeon master creating vivid, immersive scenes for a tabletop RPG. Generate detailed scene descriptions that can be visualized in 3D engines."
          },
          {
            role: "user",
            content: prompt
          }
        ],
        max_tokens: 500,
        temperature: 0.8
      });
      
      return completion.choices[0].message.content;
    } catch (error) {
      this.logger.error('AI scene generation failed:', error);
      return await this.generateWithTemplate(analysis, context);
    }
  }

  buildAIPrompt(analysis, context) {
    let prompt = "Generate a detailed D&D scene description based on this context:\n\n";
    
    if (analysis.keywords && analysis.keywords.length > 0) {
      prompt += `Key elements mentioned: ${analysis.keywords.map(k => k.keyword).join(', ')}\n`;
    }
    
    if (context.location) {
      prompt += `Location: ${context.location}\n`;
    }
    
    if (context.characters && context.characters.length > 0) {
      prompt += `Characters present: ${context.characters.map(c => c.name).join(', ')}\n`;
    }
    
    if (context.atmosphere) {
      prompt += `Atmosphere: ${context.atmosphere}\n`;
    }
    
    if (this.contextHistory.length > 0) {
      const recentContext = this.contextHistory.slice(-2);
      prompt += `\nRecent scene context: ${recentContext.map(h => h.summary).join(' -> ')}\n`;
    }
    
    prompt += "\nGenerate a scene that includes:\n";
    prompt += "1. Environmental details (lighting, weather, atmosphere)\n";
    prompt += "2. Character positions and actions\n";
    prompt += "3. Notable objects or props\n";
    prompt += "4. Sensory details (sounds, smells, textures)\n";
    prompt += "5. Potential interaction points\n";
    prompt += "\nKeep it concise but vivid, suitable for 3D visualization.";
    
    return prompt;
  }

  async generateWithTemplate(analysis, context) {
    let template = this.selectBestTemplate(analysis, context);
    let description = "";
    
    const location = context.location || template.environment.setting;
    const atmosphere = context.atmosphere || template.environment.atmosphere;
    const lighting = context.lighting || template.environment.lighting;
    
    const sceneStarter = this.selectRandomPattern(this.narrativePatterns.sceneStarters);
    description = sceneStarter
      .replace('{location}', location)
      .replace('{description}', `the ${atmosphere} atmosphere is enhanced by ${lighting} lighting`)
      .replace('{atmosphere}', atmosphere);
    
    if (context.characters && context.characters.length > 0) {
      description += " ";
      const characterIntro = this.selectRandomPattern(this.narrativePatterns.characterIntroductions);
      const character = context.characters[0];
      description += characterIntro
        .replace('{character_type}', character.name)
        .replace('{action}', 'stands ready')
        .replace('{object}', template.objects[0] || 'nearby structure')
        .replace('{character_description}', 'formidable')
        .replace('{direction}', 'the shadows');
    }
    
    description += " ";
    const envDescription = this.selectRandomPattern(this.narrativePatterns.environmentDescriptions);
    description += envDescription
      .replace('{lighting}', lighting)
      .replace('{light_action}', 'dances')
      .replace('{surface}', 'the surroundings')
      .replace('{atmosphere}', atmosphere)
      .replace('{sound_elements}', template.environment.soundscape.join(' and '))
      .replace('{weather}', 'ambient conditions')
      .replace('{visual_effect}', 'interesting shadows')
      .replace('{location}', location)
      .replace('{sense}', 'feel')
      .replace('{environmental_quality}', 'unique character');
    
    return description;
  }

  selectBestTemplate(analysis, context) {
    if (context.location) {
      const templateKey = this.findTemplateKeyByLocation(context.location);
      if (templateKey && this.sceneTemplates.has(templateKey)) {
        return this.sceneTemplates.get(templateKey);
      }
    }
    
    if (analysis.keywords && analysis.keywords.length > 0) {
      for (const keyword of analysis.keywords) {
        const templateKey = this.findTemplateKeyByKeyword(keyword.keyword);
        if (templateKey && this.sceneTemplates.has(templateKey)) {
          return this.sceneTemplates.get(templateKey);
        }
      }
    }
    
    const templateKeys = Array.from(this.sceneTemplates.keys());
    const randomKey = templateKeys[Math.floor(Math.random() * templateKeys.length)];
    return this.sceneTemplates.get(randomKey);
  }

  findTemplateKeyByLocation(location) {
    const locationMappings = {
      'tavern': 'tavern',
      'inn': 'tavern',
      'bar': 'tavern',
      'dungeon': 'dungeon_corridor',
      'cave': 'dungeon_corridor',
      'corridor': 'dungeon_corridor',
      'forest': 'forest_clearing',
      'woods': 'forest_clearing',
      'clearing': 'forest_clearing',
      'throne room': 'throne_room',
      'palace': 'throne_room',
      'court': 'throne_room'
    };
    
    return locationMappings[location.toLowerCase()];
  }

  findTemplateKeyByKeyword(keyword) {
    const keywordMappings = {
      'drink': 'tavern',
      'ale': 'tavern',
      'bartender': 'tavern',
      'trap': 'dungeon_corridor',
      'stone': 'dungeon_corridor',
      'torch': 'dungeon_corridor',
      'tree': 'forest_clearing',
      'nature': 'forest_clearing',
      'wildlife': 'forest_clearing',
      'king': 'throne_room',
      'queen': 'throne_room',
      'royal': 'throne_room'
    };
    
    return keywordMappings[keyword.toLowerCase()];
  }

  selectRandomPattern(patterns) {
    return patterns[Math.floor(Math.random() * patterns.length)];
  }

  async convertToVisualScene(description, context) {
    const visualScene = {
      environment: {
        type: context.location || 'generic',
        lighting: context.lighting || 'normal',
        atmosphere: context.atmosphere || 'neutral',
        weather: null,
        timeOfDay: this.extractTimeOfDay(description)
      },
      characters: this.extractCharactersFromDescription(description, context),
      objects: this.extractObjectsFromDescription(description, context),
      effects: this.extractEffectsFromDescription(description),
      cameraSettings: this.generateCameraSettings(context),
      audio: this.generateAudioSettings(description, context)
    };
    
    return visualScene;
  }

  extractTimeOfDay(description) {
    const timeKeywords = {
      'dawn': ['dawn', 'sunrise', 'early morning'],
      'morning': ['morning', 'daybreak'],
      'noon': ['noon', 'midday', 'bright'],
      'evening': ['evening', 'dusk', 'sunset'],
      'night': ['night', 'moonlight', 'darkness', 'midnight']
    };
    
    const lowerDescription = description.toLowerCase();
    
    for (const [time, keywords] of Object.entries(timeKeywords)) {
      for (const keyword of keywords) {
        if (lowerDescription.includes(keyword)) {
          return time;
        }
      }
    }
    
    return 'day';
  }

  extractCharactersFromDescription(description, context) {
    const characters = [];
    
    if (context.characters) {
      for (const character of context.characters) {
        characters.push({
          id: character.name.toLowerCase().replace(/\s+/g, '_'),
          name: character.name,
          type: character.type || 'humanoid',
          position: this.generateRandomPosition(),
          animation: 'idle',
          scale: 1.0
        });
      }
    }
    
    const npcKeywords = ['bartender', 'guard', 'merchant', 'wizard', 'knight', 'rogue'];
    const lowerDescription = description.toLowerCase();
    
    for (const npc of npcKeywords) {
      if (lowerDescription.includes(npc) && !characters.find(c => c.name.toLowerCase().includes(npc))) {
        characters.push({
          id: npc,
          name: npc.charAt(0).toUpperCase() + npc.slice(1),
          type: 'npc',
          position: this.generateRandomPosition(),
          animation: 'idle',
          scale: 1.0
        });
      }
    }
    
    return characters;
  }

  extractObjectsFromDescription(description, context) {
    const objects = [];
    const objectKeywords = [
      'table', 'chair', 'torch', 'door', 'chest', 'barrel', 'tree', 'rock',
      'pillar', 'throne', 'altar', 'fire', 'water', 'bridge', 'stairs'
    ];
    
    const lowerDescription = description.toLowerCase();
    
    for (const obj of objectKeywords) {
      if (lowerDescription.includes(obj)) {
        objects.push({
          type: obj,
          position: this.generateRandomPosition(),
          scale: this.getObjectScale(obj),
          rotation: { x: 0, y: Math.random() * 360, z: 0 }
        });
      }
    }
    
    return objects.slice(0, 8);
  }

  extractEffectsFromDescription(description) {
    const effects = [];
    const effectKeywords = {
      'fire': { type: 'fire', intensity: 0.8, color: '#FF4500' },
      'smoke': { type: 'smoke', intensity: 0.6, color: '#666666' },
      'light': { type: 'light', intensity: 1.0, color: '#FFFFFF' },
      'magic': { type: 'magic', intensity: 0.9, color: '#800080' },
      'water': { type: 'water', intensity: 0.7, color: '#0066CC' }
    };
    
    const lowerDescription = description.toLowerCase();
    
    for (const [keyword, config] of Object.entries(effectKeywords)) {
      if (lowerDescription.includes(keyword)) {
        effects.push({
          type: config.type,
          position: this.generateRandomPosition(),
          intensity: config.intensity,
          color: config.color,
          duration: -1
        });
      }
    }
    
    return effects;
  }

  generateRandomPosition() {
    return {
      x: (Math.random() - 0.5) * 20,
      y: 0,
      z: (Math.random() - 0.5) * 20
    };
  }

  getObjectScale(objectType) {
    const scales = {
      'table': 1.0,
      'chair': 1.0,
      'torch': 1.0,
      'door': 1.0,
      'chest': 1.2,
      'barrel': 1.0,
      'tree': 3.0,
      'rock': 1.5,
      'pillar': 2.0,
      'throne': 1.5,
      'altar': 1.0,
      'fire': 0.8,
      'water': 1.0,
      'bridge': 2.0,
      'stairs': 1.0
    };
    
    return scales[objectType] || 1.0;
  }

  generateCameraSettings(context) {
    const template = this.selectBestTemplate({ keywords: [] }, context);
    
    return {
      defaultAngle: template.cameraAngles[0],
      availableAngles: template.cameraAngles,
      transitionType: this.selectCameraTransition(),
      focusTarget: context.characters && context.characters.length > 0 ? context.characters[0].name : null
    };
  }

  selectCameraTransition() {
    const transitions = Object.keys(this.transitionTypes);
    const weights = transitions.map(t => this.transitionTypes[t].weight);
    
    let random = Math.random();
    for (let i = 0; i < transitions.length; i++) {
      random -= weights[i];
      if (random <= 0) {
        return transitions[i];
      }
    }
    
    return 'cut';
  }

  generateAudioSettings(description, context) {
    const template = this.selectBestTemplate({ keywords: [] }, context);
    
    return {
      soundscape: template.environment.soundscape,
      musicMood: this.determineMusicMood(context.atmosphere),
      volume: 0.7,
      spatialAudio: true
    };
  }

  determineMusicMood(atmosphere) {
    const moodMappings = {
      'cozy': 'peaceful',
      'ominous': 'tense',
      'mystical': 'mysterious',
      'imposing': 'dramatic',
      'peaceful': 'calm',
      'threatening': 'action'
    };
    
    return moodMappings[atmosphere] || 'ambient';
  }

  countSceneElements(visualScene) {
    return (
      (visualScene.characters?.length || 0) +
      (visualScene.objects?.length || 0) +
      (visualScene.effects?.length || 0) +
      1
    );
  }

  updateContextHistory(description, context) {
    this.contextHistory.push({
      summary: description.substring(0, 100) + (description.length > 100 ? '...' : ''),
      context,
      timestamp: Date.now()
    });
    
    if (this.contextHistory.length > 10) {
      this.contextHistory = this.contextHistory.slice(-5);
    }
  }

  async getGeneratedScene(sceneId) {
    const scene = this.generatedScenes.get(sceneId);
    if (!scene) {
      throw new Error(`Scene not found: ${sceneId}`);
    }
    
    return scene;
  }

  async getAllGeneratedScenes() {
    return Array.from(this.generatedScenes.values());
  }

  async cleanup() {
    try {
      this.logger.info('Cleaning up Scene Generator Service');
      
      this.sceneTemplates.clear();
      this.generatedScenes.clear();
      this.generationQueue = [];
      this.contextHistory = [];
      this.isProcessing = false;
      
      this.logger.info('Scene Generator Service cleanup completed');
    } catch (error) {
      this.logger.error('Scene Generator Service cleanup failed:', error);
    }
  }
}

module.exports = SceneGeneratorService;