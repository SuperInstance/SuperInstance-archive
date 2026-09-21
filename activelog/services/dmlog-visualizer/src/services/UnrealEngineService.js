const { spawn, exec } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');

class UnrealEngineService {
  constructor(config = {}) {
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'logs/unreal-engine.log' })
      ]
    });

    this.enginePath = config.enginePath || process.env.UNREAL_ENGINE_PATH || '/UnrealEngine';
    this.projectPath = config.projectPath || './unreal-projects/dmlog-visualizer';
    this.isInitialized = false;
    this.activeScenes = new Map();
    this.battleInstances = new Map();
    this.renderQueue = [];
    this.isProcessing = false;
  }

  async initialize() {
    try {
      this.logger.info('Initializing Unreal Engine Service');
      
      await this.checkEngineInstallation();
      await this.setupProject();
      await this.loadBattleTemplates();
      
      this.isInitialized = true;
      this.logger.info('Unreal Engine Service initialized successfully');
      return true;
    } catch (error) {
      this.logger.error('Failed to initialize Unreal Engine Service:', error);
      return false;
    }
  }

  async checkEngineInstallation() {
    try {
      const engineExists = await fs.access(this.enginePath).then(() => true).catch(() => false);
      if (!engineExists) {
        this.logger.warn('Unreal Engine not found at specified path, using mock mode');
        this.mockMode = true;
        return;
      }
      
      this.logger.info('Unreal Engine installation verified');
    } catch (error) {
      this.logger.error('Engine installation check failed:', error);
      throw error;
    }
  }

  async setupProject() {
    try {
      const projectExists = await fs.access(this.projectPath).then(() => true).catch(() => false);
      if (!projectExists) {
        await this.createProject();
      }
      
      await this.setupBattleVisualizationAssets();
      await this.configureLighting();
      await this.setupCameraSystems();
      
      this.logger.info('Unreal project setup completed');
    } catch (error) {
      this.logger.error('Project setup failed:', error);
      throw error;
    }
  }

  async createProject() {
    if (this.mockMode) {
      await fs.mkdir(this.projectPath, { recursive: true });
      await fs.writeFile(
        path.join(this.projectPath, 'DMLogVisualizer.uproject'),
        JSON.stringify({
          "FileVersion": 3,
          "EngineAssociation": "5.3",
          "Category": "",
          "Description": "DMLog Battle Visualization Project"
        }, null, 2)
      );
      return;
    }

    return new Promise((resolve, reject) => {
      const createCmd = `"${path.join(this.enginePath, 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe')}" -NewProject -ProjectName=DMLogVisualizer -TemplateName=ThirdPerson -TargetPlatform=Windows -ProjectPath="${this.projectPath}"`;
      
      exec(createCmd, (error, stdout, stderr) => {
        if (error) {
          this.logger.error('Failed to create Unreal project:', error);
          reject(error);
          return;
        }
        
        this.logger.info('Unreal project created successfully');
        resolve();
      });
    });
  }

  async loadBattleTemplates() {
    try {
      this.battleTemplates = {
        medieval: {
          environment: 'Medieval_Castle',
          lighting: 'Dramatic_Indoor',
          effects: ['Torch_Flames', 'Dust_Particles']
        },
        dungeon: {
          environment: 'Dark_Dungeon',
          lighting: 'Moody_Underground',
          effects: ['Water_Drips', 'Fog_Volume']
        },
        forest: {
          environment: 'Enchanted_Forest',
          lighting: 'Dappled_Sunlight',
          effects: ['Leaf_Particles', 'God_Rays']
        },
        tavern: {
          environment: 'Cozy_Tavern',
          lighting: 'Warm_Firelight',
          effects: ['Smoke_Particles', 'Ember_Glow']
        }
      };
      
      this.logger.info('Battle templates loaded');
    } catch (error) {
      this.logger.error('Failed to load battle templates:', error);
      throw error;
    }
  }

  async setupBattleVisualizationAssets() {
    const assetsDir = path.join(this.projectPath, 'Content/DMLog');
    await fs.mkdir(assetsDir, { recursive: true });
    
    const assetCategories = [
      'Characters',
      'Environments',
      'Effects',
      'UI',
      'Audio',
      'Animations'
    ];
    
    for (const category of assetCategories) {
      await fs.mkdir(path.join(assetsDir, category), { recursive: true });
    }
    
    this.logger.info('Battle visualization assets structure created');
  }

  async configureLighting() {
    const lightingConfig = {
      dynamicShadows: true,
      globalIllumination: 'Lumen',
      reflections: 'ScreenSpace',
      atmosphericFog: true,
      volumetricClouds: false
    };
    
    this.lightingConfig = lightingConfig;
    this.logger.info('Lighting configuration set');
  }

  async setupCameraSystems() {
    this.cameraSystems = {
      cinematic: {
        type: 'CineCameraActor',
        settings: {
          focalLength: 35,
          aperture: 2.8,
          focusDistance: 500
        }
      },
      tactical: {
        type: 'TopDownCamera',
        settings: {
          height: 1000,
          angle: 45,
          fov: 90
        }
      },
      firstPerson: {
        type: 'FirstPersonCamera',
        settings: {
          fov: 75,
          stabilization: true
        }
      }
    };
    
    this.logger.info('Camera systems configured');
  }

  async renderBattleScene(sceneData) {
    try {
      const sceneId = `battle_${Date.now()}`;
      this.logger.info(`Starting battle scene render: ${sceneId}`);
      
      if (this.mockMode) {
        return await this.mockRenderBattleScene(sceneData, sceneId);
      }
      
      const scene = await this.createBattleScene(sceneData, sceneId);
      await this.setupCharacters(scene, sceneData.characters);
      await this.configureEnvironment(scene, sceneData.environment);
      await this.setupLighting(scene, sceneData.timeOfDay);
      await this.positionCameras(scene, sceneData.cameraAngles);
      
      const renderResult = await this.executeRender(scene);
      
      this.activeScenes.set(sceneId, scene);
      
      return {
        sceneId,
        status: 'rendered',
        outputPath: renderResult.outputPath,
        duration: renderResult.duration,
        metadata: {
          characters: sceneData.characters.length,
          environment: sceneData.environment,
          renderTime: renderResult.renderTime
        }
      };
    } catch (error) {
      this.logger.error('Battle scene render failed:', error);
      throw error;
    }
  }

  async mockRenderBattleScene(sceneData, sceneId) {
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return {
      sceneId,
      status: 'rendered',
      outputPath: `/tmp/renders/${sceneId}.mp4`,
      duration: 30000,
      metadata: {
        characters: sceneData.characters?.length || 0,
        environment: sceneData.environment || 'default',
        renderTime: 2000
      }
    };
  }

  async createBattleScene(sceneData, sceneId) {
    const template = this.battleTemplates[sceneData.environment] || this.battleTemplates.medieval;
    
    const scene = {
      id: sceneId,
      name: `Battle_${sceneId}`,
      template: template,
      actors: [],
      lighting: null,
      cameras: [],
      timeline: []
    };
    
    this.logger.info(`Created battle scene: ${sceneId}`);
    return scene;
  }

  async setupCharacters(scene, characters) {
    for (const character of characters) {
      const characterActor = {
        id: character.id,
        name: character.name,
        class: character.class,
        mesh: this.getCharacterMesh(character.class),
        materials: this.getCharacterMaterials(character),
        animations: this.getCharacterAnimations(character.actions),
        position: character.position || { x: 0, y: 0, z: 0 },
        rotation: character.rotation || { x: 0, y: 0, z: 0 }
      };
      
      scene.actors.push(characterActor);
    }
    
    this.logger.info(`Set up ${characters.length} characters in scene`);
  }

  getCharacterMesh(characterClass) {
    const meshMap = {
      warrior: '/Game/Characters/Warrior/SK_Warrior',
      mage: '/Game/Characters/Mage/SK_Mage',
      rogue: '/Game/Characters/Rogue/SK_Rogue',
      cleric: '/Game/Characters/Cleric/SK_Cleric',
      ranger: '/Game/Characters/Ranger/SK_Ranger',
      default: '/Game/Characters/Generic/SK_Generic'
    };
    
    return meshMap[characterClass.toLowerCase()] || meshMap.default;
  }

  getCharacterMaterials(character) {
    return {
      skin: `/Game/Materials/Characters/${character.race}_Skin`,
      armor: `/Game/Materials/Armor/${character.armorType}`,
      weapon: `/Game/Materials/Weapons/${character.weaponType}`
    };
  }

  getCharacterAnimations(actions) {
    const animationMap = {
      attack: 'Anim_Attack_Sequence',
      defend: 'Anim_Defensive_Stance',
      cast: 'Anim_Spell_Cast',
      move: 'Anim_Combat_Movement',
      idle: 'Anim_Combat_Idle',
      death: 'Anim_Death_Sequence'
    };
    
    return actions.map(action => animationMap[action] || animationMap.idle);
  }

  async configureEnvironment(scene, environmentType) {
    const template = this.battleTemplates[environmentType] || this.battleTemplates.medieval;
    
    scene.environment = {
      staticMesh: `/Game/Environments/${template.environment}/SM_Environment`,
      materials: `/Game/Materials/Environments/${template.environment}`,
      props: this.getEnvironmentProps(environmentType),
      weatherEffects: this.getWeatherEffects(environmentType)
    };
    
    this.logger.info(`Configured environment: ${environmentType}`);
  }

  getEnvironmentProps(environmentType) {
    const propsMap = {
      medieval: ['Banners', 'Torches', 'Weapons_Racks', 'Stone_Pillars'],
      dungeon: ['Chains', 'Bones', 'Treasure_Chests', 'Spider_Webs'],
      forest: ['Trees', 'Rocks', 'Mushrooms', 'Fallen_Logs'],
      tavern: ['Tables', 'Chairs', 'Barrels', 'Bottles']
    };
    
    return propsMap[environmentType] || propsMap.medieval;
  }

  getWeatherEffects(environmentType) {
    const weatherMap = {
      medieval: { rain: 0.2, wind: 0.3, fog: 0.1 },
      dungeon: { rain: 0.0, wind: 0.1, fog: 0.8 },
      forest: { rain: 0.3, wind: 0.5, fog: 0.3 },
      tavern: { rain: 0.0, wind: 0.0, fog: 0.2 }
    };
    
    return weatherMap[environmentType] || weatherMap.medieval;
  }

  async setupLighting(scene, timeOfDay) {
    const lightingPresets = {
      dawn: { intensity: 0.7, temperature: 3000, shadowSoftness: 0.8 },
      morning: { intensity: 1.0, temperature: 4000, shadowSoftness: 0.6 },
      noon: { intensity: 1.2, temperature: 5500, shadowSoftness: 0.4 },
      evening: { intensity: 0.8, temperature: 2800, shadowSoftness: 0.7 },
      night: { intensity: 0.3, temperature: 2200, shadowSoftness: 0.9 }
    };
    
    const preset = lightingPresets[timeOfDay] || lightingPresets.noon;
    
    scene.lighting = {
      directionalLight: {
        intensity: preset.intensity,
        temperature: preset.temperature,
        shadowSoftness: preset.shadowSoftness,
        cascadedShadowMaps: true
      },
      skyLight: {
        intensity: 0.5,
        color: this.getSkyColor(timeOfDay)
      },
      atmosphericFog: {
        density: 0.02,
        heightFalloff: 0.2,
        inscatteringColor: this.getFogColor(timeOfDay)
      }
    };
    
    this.logger.info(`Set up lighting for: ${timeOfDay}`);
  }

  getSkyColor(timeOfDay) {
    const colorMap = {
      dawn: { r: 1.0, g: 0.8, b: 0.6 },
      morning: { r: 0.8, g: 0.9, b: 1.0 },
      noon: { r: 0.7, g: 0.8, b: 1.0 },
      evening: { r: 1.0, g: 0.7, b: 0.5 },
      night: { r: 0.2, g: 0.3, b: 0.6 }
    };
    
    return colorMap[timeOfDay] || colorMap.noon;
  }

  getFogColor(timeOfDay) {
    const colorMap = {
      dawn: { r: 0.9, g: 0.7, b: 0.5 },
      morning: { r: 0.7, g: 0.8, b: 0.9 },
      noon: { r: 0.8, g: 0.8, b: 0.8 },
      evening: { r: 0.9, g: 0.6, b: 0.4 },
      night: { r: 0.3, g: 0.3, b: 0.5 }
    };
    
    return colorMap[timeOfDay] || colorMap.noon;
  }

  async positionCameras(scene, cameraAngles) {
    for (const angle of cameraAngles) {
      const camera = {
        type: this.cameraSystems[angle.type] || this.cameraSystems.cinematic,
        position: angle.position,
        rotation: angle.rotation,
        target: angle.target,
        settings: {
          ...this.cameraSystems[angle.type]?.settings,
          ...angle.customSettings
        }
      };
      
      scene.cameras.push(camera);
    }
    
    this.logger.info(`Positioned ${cameraAngles.length} cameras`);
  }

  async executeRender(scene) {
    if (this.mockMode) {
      await new Promise(resolve => setTimeout(resolve, 1500));
      return {
        outputPath: `/tmp/renders/${scene.id}.mp4`,
        duration: 30000,
        renderTime: 1500
      };
    }
    
    return new Promise((resolve, reject) => {
      const renderCmd = this.buildRenderCommand(scene);
      const startTime = Date.now();
      
      exec(renderCmd, (error, stdout, stderr) => {
        const renderTime = Date.now() - startTime;
        
        if (error) {
          this.logger.error('Render execution failed:', error);
          reject(error);
          return;
        }
        
        const outputPath = this.getSceneOutputPath(scene.id);
        
        resolve({
          outputPath,
          duration: 30000,
          renderTime
        });
      });
    });
  }

  buildRenderCommand(scene) {
    const outputPath = this.getSceneOutputPath(scene.id);
    return `"${path.join(this.enginePath, 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe')}" "${this.projectPath}" -ExecutePythonScript="Scripts/render_battle_scene.py" -SceneData="${JSON.stringify(scene)}" -OutputPath="${outputPath}" -Quality=Epic -ResX=1920 -ResY=1080`;
  }

  getSceneOutputPath(sceneId) {
    return path.join(this.projectPath, 'Rendered', `${sceneId}.mp4`);
  }

  async updateBattleState(sceneId, battleState) {
    try {
      const scene = this.activeScenes.get(sceneId);
      if (!scene) {
        throw new Error(`Scene not found: ${sceneId}`);
      }
      
      await this.updateCharacterPositions(scene, battleState.characterPositions);
      await this.updateCharacterAnimations(scene, battleState.characterActions);
      await this.updateEffects(scene, battleState.effects);
      
      this.logger.info(`Updated battle state for scene: ${sceneId}`);
      
      return {
        sceneId,
        status: 'updated',
        timestamp: Date.now()
      };
    } catch (error) {
      this.logger.error('Failed to update battle state:', error);
      throw error;
    }
  }

  async updateCharacterPositions(scene, positions) {
    for (const position of positions) {
      const actor = scene.actors.find(a => a.id === position.characterId);
      if (actor) {
        actor.position = position.position;
        actor.rotation = position.rotation;
      }
    }
  }

  async updateCharacterAnimations(scene, actions) {
    for (const action of actions) {
      const actor = scene.actors.find(a => a.id === action.characterId);
      if (actor) {
        actor.currentAnimation = this.getCharacterAnimations([action.action])[0];
        actor.animationStartTime = Date.now();
      }
    }
  }

  async updateEffects(scene, effects) {
    scene.effects = effects.map(effect => ({
      type: effect.type,
      position: effect.position,
      intensity: effect.intensity,
      duration: effect.duration,
      startTime: Date.now()
    }));
  }

  async exportScene(sceneId, format = 'mp4') {
    try {
      const scene = this.activeScenes.get(sceneId);
      if (!scene) {
        throw new Error(`Scene not found: ${sceneId}`);
      }
      
      const exportPath = await this.performExport(scene, format);
      
      this.logger.info(`Scene exported: ${sceneId} to ${exportPath}`);
      
      return {
        sceneId,
        exportPath,
        format,
        timestamp: Date.now()
      };
    } catch (error) {
      this.logger.error('Scene export failed:', error);
      throw error;
    }
  }

  async performExport(scene, format) {
    if (this.mockMode) {
      return `/tmp/exports/${scene.id}.${format}`;
    }
    
    const exportPath = path.join(this.projectPath, 'Exports', `${scene.id}.${format}`);
    
    return new Promise((resolve, reject) => {
      const exportCmd = `"${path.join(this.enginePath, 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe')}" "${this.projectPath}" -ExecutePythonScript="Scripts/export_scene.py" -SceneId="${scene.id}" -Format="${format}" -OutputPath="${exportPath}"`;
      
      exec(exportCmd, (error, stdout, stderr) => {
        if (error) {
          reject(error);
          return;
        }
        
        resolve(exportPath);
      });
    });
  }

  async cleanup() {
    try {
      this.logger.info('Cleaning up Unreal Engine Service');
      
      this.activeScenes.clear();
      this.battleInstances.clear();
      this.renderQueue = [];
      
      this.logger.info('Unreal Engine Service cleanup completed');
    } catch (error) {
      this.logger.error('Cleanup failed:', error);
    }
  }
}

module.exports = UnrealEngineService;