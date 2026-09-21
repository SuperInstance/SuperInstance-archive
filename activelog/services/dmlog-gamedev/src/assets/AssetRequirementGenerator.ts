import { EventEmitter } from 'events';
import fs from 'fs-extra';
import path from 'path';
import { Campaign, Character, Map, Encounter, Asset } from '../types';

export interface AssetCategory {
  id: string;
  name: string;
  type: 'model' | 'texture' | 'audio' | 'animation' | 'ui' | 'effect' | 'script';
  priority: 'critical' | 'important' | 'nice_to_have' | 'optional';
  assets: AssetRequirement[];
  estimatedCost: number;
  estimatedTime: number;
}

export interface AssetRequirement {
  id: string;
  name: string;
  description: string;
  type: 'model' | 'texture' | 'audio' | 'animation' | 'ui' | 'effect' | 'script';
  category: string;
  subcategory?: string;
  specifications: AssetSpecification;
  usage: AssetUsage;
  alternatives: AssetAlternative[];
  dependencies: string[];
  priority: 'critical' | 'important' | 'nice_to_have' | 'optional';
  estimatedCost: number;
  estimatedTimeHours: number;
  technicalRequirements: TechnicalRequirement[];
  sources: AssetSource[];
}

export interface AssetSpecification {
  dimensions?: {
    width?: number;
    height?: number;
    depth?: number;
    units: 'pixels' | 'meters' | 'units';
  };
  resolution?: {
    width: number;
    height: number;
    dpi?: number;
  };
  format: string[];
  quality: 'low' | 'medium' | 'high' | 'ultra';
  polyCount?: {
    min: number;
    max: number;
    target: number;
  };
  textureSize?: number;
  duration?: number;
  sampleRate?: number;
  bitRate?: number;
  channels?: number;
  frameRate?: number;
  colorSpace?: string;
  compression?: string;
  mipmaps?: boolean;
  animations?: string[];
  bones?: number;
  morphTargets?: number;
}

export interface AssetUsage {
  scenes: string[];
  characters: string[];
  frequency: 'once' | 'rare' | 'common' | 'constant';
  context: 'gameplay' | 'cutscene' | 'ui' | 'ambient' | 'combat';
  platforms: string[];
  performanceImpact: 'low' | 'medium' | 'high';
  memoryFootprint: number;
  loadingFrequency: 'preload' | 'streaming' | 'on_demand';
}

export interface AssetAlternative {
  type: 'substitute' | 'procedural' | 'simplified' | 'placeholder';
  description: string;
  costReduction: number;
  qualityImpact: number;
  implementationNotes: string;
}

export interface TechnicalRequirement {
  platform: 'unity' | 'godot' | 'unreal' | 'web' | 'mobile' | 'console';
  version?: string;
  plugins?: string[];
  shaders?: string[];
  scripts?: string[];
  performance?: {
    maxPolyCount: number;
    maxTextureSize: number;
    maxFileSize: number;
    targetFPS: number;
  };
}

export interface AssetSource {
  type: 'create' | 'purchase' | 'free' | 'existing' | 'procedural';
  provider?: string;
  url?: string;
  license: 'commercial' | 'royalty_free' | 'creative_commons' | 'public_domain' | 'custom';
  cost: number;
  notes?: string;
}

export interface AssetBudget {
  totalEstimatedCost: number;
  breakdown: {
    models: number;
    textures: number;
    audio: number;
    animations: number;
    ui: number;
    effects: number;
    scripts: number;
  };
  timeEstimate: {
    totalHours: number;
    breakdown: {
      modeling: number;
      texturing: number;
      animation: number;
      audio: number;
      programming: number;
      testing: number;
    };
  };
  riskFactors: RiskFactor[];
}

export interface RiskFactor {
  category: string;
  description: string;
  probability: number;
  impact: number;
  mitigation: string;
}

export interface AssetPipeline {
  workflows: PipelineWorkflow[];
  tools: PipelineTool[];
  standards: QualityStandard[];
  deliverables: Deliverable[];
}

export interface PipelineWorkflow {
  stage: string;
  input: string[];
  output: string[];
  tools: string[];
  duration: number;
  dependencies: string[];
  quality_gates: QualityGate[];
}

export interface PipelineTool {
  name: string;
  type: 'modeling' | 'texturing' | 'animation' | 'audio' | 'programming' | 'pipeline';
  cost: number;
  alternatives: string[];
  learning_curve: 'easy' | 'medium' | 'hard';
}

export interface QualityStandard {
  category: string;
  metric: string;
  target: number | string;
  measurement: string;
  acceptance_criteria: string;
}

export interface QualityGate {
  name: string;
  criteria: QualityCriterion[];
  automated: boolean;
  blocking: boolean;
}

export interface QualityCriterion {
  metric: string;
  operator: '>' | '<' | '=' | '>=' | '<=';
  value: number | string;
  unit?: string;
}

export interface Deliverable {
  name: string;
  format: string;
  location: string;
  approval_required: boolean;
  stakeholders: string[];
}

export interface AssetExportOptions {
  format: 'json' | 'yaml' | 'csv' | 'xlsx' | 'pdf' | 'html';
  includeCosts: boolean;
  includeTimeEstimates: boolean;
  includeSpecs: boolean;
  includeAlternatives: boolean;
  includePipeline: boolean;
  groupBy: 'category' | 'priority' | 'type' | 'scene';
  sortBy: 'name' | 'priority' | 'cost' | 'time';
  filterBy?: {
    category?: string[];
    priority?: string[];
    type?: string[];
  };
}

export class AssetRequirementGenerator extends EventEmitter {
  private assetDatabase: Map<string, AssetRequirement> = new Map();
  private costDatabase: Map<string, number> = new Map();
  private timeDatabase: Map<string, number> = new Map();

  constructor() {
    super();
    this.initializeDatabases();
  }

  async generateAssetRequirements(campaign: Campaign, options: any = {}): Promise<AssetCategory[]> {
    this.emit('generation:started', { campaignId: campaign.id });

    const categories: AssetCategory[] = [];

    categories.push(...await this.generateCharacterAssets(campaign));
    categories.push(...await this.generateEnvironmentAssets(campaign));
    categories.push(...await this.generateAudioAssets(campaign));
    categories.push(...await this.generateUIAssets(campaign));
    categories.push(...await this.generateEffectAssets(campaign));
    categories.push(...await this.generateAnimationAssets(campaign));
    categories.push(...await this.generateGameplayAssets(campaign));

    for (const category of categories) {
      category.estimatedCost = this.calculateCategoryCost(category);
      category.estimatedTime = this.calculateCategoryTime(category);
    }

    this.emit('generation:completed', { categories });
    return categories;
  }

  private async generateCharacterAssets(campaign: Campaign): Promise<AssetCategory[]> {
    const playerCharacters: AssetRequirement[] = [];
    const npcAssets: AssetRequirement[] = [];
    const enemyAssets: AssetRequirement[] = [];
    
    campaign.characters?.forEach(character => {
      const characterAssets = this.generateCharacterAssetRequirements(character);
      
      if (character.type === 'player') {
        playerCharacters.push(...characterAssets);
      } else if (character.type === 'npc') {
        npcAssets.push(...characterAssets);
      } else {
        enemyAssets.push(...characterAssets);
      }
    });

    return [
      {
        id: 'player_characters',
        name: 'Player Characters',
        type: 'model',
        priority: 'critical',
        assets: playerCharacters,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'npcs',
        name: 'Non-Player Characters',
        type: 'model',
        priority: 'important',
        assets: npcAssets,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'enemies',
        name: 'Enemies and Creatures',
        type: 'model',
        priority: 'critical',
        assets: enemyAssets,
        estimatedCost: 0,
        estimatedTime: 0
      }
    ];
  }

  private generateCharacterAssetRequirements(character: Character): AssetRequirement[] {
    const assets: AssetRequirement[] = [];
    const baseId = `char_${character.id}`;

    // Base character model
    assets.push({
      id: `${baseId}_model`,
      name: `${character.name} - Base Model`,
      description: `3D character model for ${character.name} (${character.race} ${character.class})`,
      type: 'model',
      category: 'characters',
      subcategory: character.type,
      specifications: {
        polyCount: { min: 2000, max: 8000, target: 4000 },
        format: ['fbx', 'obj', 'gltf'],
        quality: 'high',
        bones: 60,
        animations: ['idle', 'walk', 'run', 'attack', 'cast', 'death'],
        textureSize: 1024
      },
      usage: {
        scenes: this.getCharacterScenes(character),
        characters: [character.id],
        frequency: character.type === 'player' ? 'constant' : 'common',
        context: 'gameplay',
        platforms: ['pc', 'console'],
        performanceImpact: 'medium',
        memoryFootprint: 8,
        loadingFrequency: 'preload'
      },
      alternatives: [
        {
          type: 'simplified',
          description: 'Lower poly version for distant viewing',
          costReduction: 0.3,
          qualityImpact: 0.2,
          implementationNotes: 'Use LOD system'
        }
      ],
      dependencies: [`${baseId}_texture`, `${baseId}_rig`],
      priority: character.type === 'player' ? 'critical' : 'important',
      estimatedCost: this.getAssetCost('character_model', character.type),
      estimatedTimeHours: this.getAssetTime('character_model', character.type),
      technicalRequirements: [
        {
          platform: 'unity',
          plugins: ['Humanoid Rig'],
          performance: { maxPolyCount: 8000, maxTextureSize: 1024, maxFileSize: 10, targetFPS: 60 }
        }
      ],
      sources: [
        {
          type: 'create',
          license: 'commercial',
          cost: this.getAssetCost('character_model', character.type)
        }
      ]
    });

    // Character textures
    assets.push({
      id: `${baseId}_texture`,
      name: `${character.name} - Textures`,
      description: `Diffuse, normal, and specular maps for ${character.name}`,
      type: 'texture',
      category: 'characters',
      subcategory: character.type,
      specifications: {
        resolution: { width: 1024, height: 1024 },
        format: ['png', 'tga', 'dds'],
        quality: 'high',
        mipmaps: true,
        compression: 'dxt5'
      },
      usage: {
        scenes: this.getCharacterScenes(character),
        characters: [character.id],
        frequency: character.type === 'player' ? 'constant' : 'common',
        context: 'gameplay',
        platforms: ['pc', 'console'],
        performanceImpact: 'low',
        memoryFootprint: 4,
        loadingFrequency: 'preload'
      },
      alternatives: [
        {
          type: 'procedural',
          description: 'Procedurally generated textures',
          costReduction: 0.6,
          qualityImpact: 0.4,
          implementationNotes: 'Use substance designer'
        }
      ],
      dependencies: [`${baseId}_model`],
      priority: character.type === 'player' ? 'critical' : 'important',
      estimatedCost: this.getAssetCost('character_texture', character.type),
      estimatedTimeHours: this.getAssetTime('character_texture', character.type),
      technicalRequirements: [
        {
          platform: 'unity',
          performance: { maxTextureSize: 1024, maxFileSize: 2, targetFPS: 60 }
        }
      ],
      sources: [
        {
          type: 'create',
          license: 'commercial',
          cost: this.getAssetCost('character_texture', character.type)
        }
      ]
    });

    // Equipment models
    character.equipment?.forEach((equipment, index) => {
      assets.push({
        id: `${baseId}_equipment_${index}`,
        name: `${character.name} - ${equipment.name}`,
        description: `${equipment.type} model for ${character.name}`,
        type: 'model',
        category: 'equipment',
        subcategory: equipment.type,
        specifications: {
          polyCount: { min: 200, max: 1000, target: 500 },
          format: ['fbx', 'obj'],
          quality: 'medium',
          textureSize: 512
        },
        usage: {
          scenes: this.getCharacterScenes(character),
          characters: [character.id],
          frequency: 'common',
          context: 'gameplay',
          platforms: ['pc', 'console'],
          performanceImpact: 'low',
          memoryFootprint: 2,
          loadingFrequency: 'on_demand'
        },
        alternatives: [
          {
            type: 'substitute',
            description: 'Generic equipment model',
            costReduction: 0.8,
            qualityImpact: 0.6,
            implementationNotes: 'Use modular system'
          }
        ],
        dependencies: [],
        priority: 'nice_to_have',
        estimatedCost: this.getAssetCost('equipment_model'),
        estimatedTimeHours: this.getAssetTime('equipment_model'),
        technicalRequirements: [
          {
            platform: 'unity',
            performance: { maxPolyCount: 1000, maxTextureSize: 512, maxFileSize: 2, targetFPS: 60 }
          }
        ],
        sources: [
          {
            type: 'purchase',
            provider: 'Unity Asset Store',
            license: 'royalty_free',
            cost: this.getAssetCost('equipment_model') * 0.3
          }
        ]
      });
    });

    return assets;
  }

  private async generateEnvironmentAssets(campaign: Campaign): Promise<AssetCategory[]> {
    const environments: AssetRequirement[] = [];
    const props: AssetRequirement[] = [];
    const architecture: AssetRequirement[] = [];

    campaign.maps?.forEach(map => {
      const mapAssets = this.generateMapAssetRequirements(map);
      environments.push(...mapAssets.environments);
      props.push(...mapAssets.props);
      architecture.push(...mapAssets.architecture);
    });

    return [
      {
        id: 'environments',
        name: 'Environment Art',
        type: 'texture',
        priority: 'critical',
        assets: environments,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'props',
        name: 'Environment Props',
        type: 'model',
        priority: 'important',
        assets: props,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'architecture',
        name: 'Architecture',
        type: 'model',
        priority: 'critical',
        assets: architecture,
        estimatedCost: 0,
        estimatedTime: 0
      }
    ];
  }

  private generateMapAssetRequirements(map: Map): any {
    const baseId = `map_${map.id}`;
    const environments: AssetRequirement[] = [];
    const props: AssetRequirement[] = [];
    const architecture: AssetRequirement[] = [];

    // Terrain/Ground textures
    environments.push({
      id: `${baseId}_terrain`,
      name: `${map.name} - Terrain`,
      description: `Ground textures and materials for ${map.name}`,
      type: 'texture',
      category: 'environments',
      subcategory: map.environment,
      specifications: {
        resolution: { width: 2048, height: 2048 },
        format: ['png', 'tga'],
        quality: 'high',
        mipmaps: true
      },
      usage: {
        scenes: [map.id],
        characters: [],
        frequency: 'constant',
        context: 'gameplay',
        platforms: ['pc', 'console'],
        performanceImpact: 'medium',
        memoryFootprint: 16,
        loadingFrequency: 'preload'
      },
      alternatives: [
        {
          type: 'procedural',
          description: 'Procedural terrain generation',
          costReduction: 0.7,
          qualityImpact: 0.3,
          implementationNotes: 'Use terrain generation tools'
        }
      ],
      dependencies: [],
      priority: 'critical',
      estimatedCost: this.getAssetCost('terrain_texture', map.environment),
      estimatedTimeHours: this.getAssetTime('terrain_texture', map.environment),
      technicalRequirements: [
        {
          platform: 'unity',
          plugins: ['Terrain Tools'],
          performance: { maxTextureSize: 2048, maxFileSize: 8, targetFPS: 60 }
        }
      ],
      sources: [
        {
          type: 'create',
          license: 'commercial',
          cost: this.getAssetCost('terrain_texture', map.environment)
        }
      ]
    });

    // Props and decorative elements
    map.rooms?.forEach((room, index) => {
      room.features?.forEach((feature, featureIndex) => {
        props.push({
          id: `${baseId}_prop_${index}_${featureIndex}`,
          name: `${map.name} - ${feature}`,
          description: `${feature} prop for room ${index + 1}`,
          type: 'model',
          category: 'props',
          subcategory: feature,
          specifications: {
            polyCount: { min: 100, max: 2000, target: 800 },
            format: ['fbx', 'obj'],
            quality: 'medium',
            textureSize: 512
          },
          usage: {
            scenes: [map.id],
            characters: [],
            frequency: 'common',
            context: 'gameplay',
            platforms: ['pc', 'console'],
            performanceImpact: 'low',
            memoryFootprint: 3,
            loadingFrequency: 'streaming'
          },
          alternatives: [
            {
              type: 'substitute',
              description: 'Generic prop model',
              costReduction: 0.9,
              qualityImpact: 0.7,
              implementationNotes: 'Use modular prop system'
            }
          ],
          dependencies: [],
          priority: 'nice_to_have',
          estimatedCost: this.getAssetCost('environment_prop'),
          estimatedTimeHours: this.getAssetTime('environment_prop'),
          technicalRequirements: [
            {
              platform: 'unity',
              performance: { maxPolyCount: 2000, maxTextureSize: 512, maxFileSize: 3, targetFPS: 60 }
            }
          ],
          sources: [
            {
              type: 'purchase',
              provider: 'Unity Asset Store',
              license: 'royalty_free',
              cost: this.getAssetCost('environment_prop') * 0.4
            }
          ]
        });
      });
    });

    return { environments, props, architecture };
  }

  private async generateAudioAssets(campaign: Campaign): Promise<AssetCategory[]> {
    const music: AssetRequirement[] = [];
    const soundEffects: AssetRequirement[] = [];
    const voice: AssetRequirement[] = [];
    const ambient: AssetRequirement[] = [];

    // Background music for different scenes/moods
    const musicNeeds = this.identifyMusicNeeds(campaign);
    musicNeeds.forEach((mood, index) => {
      music.push({
        id: `music_${mood.replace(/\s+/g, '_').toLowerCase()}`,
        name: `${mood} Music`,
        description: `Background music for ${mood} scenes`,
        type: 'audio',
        category: 'music',
        subcategory: mood,
        specifications: {
          duration: 120,
          sampleRate: 44100,
          bitRate: 320,
          channels: 2,
          format: ['ogg', 'wav', 'mp3']
        },
        usage: {
          scenes: this.getScenesWithMood(campaign, mood),
          characters: [],
          frequency: 'common',
          context: 'ambient',
          platforms: ['pc', 'console'],
          performanceImpact: 'low',
          memoryFootprint: 5,
          loadingFrequency: 'streaming'
        },
        alternatives: [
          {
            type: 'free',
            description: 'Creative Commons music',
            costReduction: 1.0,
            qualityImpact: 0.3,
            implementationNotes: 'Check licensing requirements'
          }
        ],
        dependencies: [],
        priority: mood === 'combat' ? 'critical' : 'important',
        estimatedCost: this.getAssetCost('background_music'),
        estimatedTimeHours: this.getAssetTime('background_music'),
        technicalRequirements: [
          {
            platform: 'unity',
            plugins: ['Audio Mixer'],
            performance: { maxFileSize: 5, targetFPS: 60 }
          }
        ],
        sources: [
          {
            type: 'purchase',
            provider: 'AudioJungle',
            license: 'royalty_free',
            cost: this.getAssetCost('background_music')
          }
        ]
      });
    });

    // Sound effects for combat, spells, interactions
    const sfxNeeds = this.identifySoundEffectNeeds(campaign);
    sfxNeeds.forEach(sfx => {
      soundEffects.push({
        id: `sfx_${sfx.id}`,
        name: sfx.name,
        description: sfx.description,
        type: 'audio',
        category: 'sound_effects',
        subcategory: sfx.category,
        specifications: {
          duration: sfx.duration,
          sampleRate: 44100,
          bitRate: 192,
          channels: 1,
          format: ['ogg', 'wav']
        },
        usage: {
          scenes: sfx.scenes,
          characters: sfx.characters,
          frequency: sfx.frequency,
          context: 'gameplay',
          platforms: ['pc', 'console'],
          performanceImpact: 'low',
          memoryFootprint: 1,
          loadingFrequency: 'on_demand'
        },
        alternatives: [
          {
            type: 'free',
            description: 'Freesound.org library',
            costReduction: 1.0,
            qualityImpact: 0.4,
            implementationNotes: 'May require audio processing'
          }
        ],
        dependencies: [],
        priority: sfx.priority,
        estimatedCost: this.getAssetCost('sound_effect'),
        estimatedTimeHours: this.getAssetTime('sound_effect'),
        technicalRequirements: [
          {
            platform: 'unity',
            performance: { maxFileSize: 1, targetFPS: 60 }
          }
        ],
        sources: [
          {
            type: 'create',
            license: 'commercial',
            cost: this.getAssetCost('sound_effect')
          }
        ]
      });
    });

    return [
      {
        id: 'music',
        name: 'Background Music',
        type: 'audio',
        priority: 'important',
        assets: music,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'sound_effects',
        name: 'Sound Effects',
        type: 'audio',
        priority: 'critical',
        assets: soundEffects,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'voice_acting',
        name: 'Voice Acting',
        type: 'audio',
        priority: 'optional',
        assets: voice,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'ambient_audio',
        name: 'Ambient Audio',
        type: 'audio',
        priority: 'nice_to_have',
        assets: ambient,
        estimatedCost: 0,
        estimatedTime: 0
      }
    ];
  }

  private async generateUIAssets(campaign: Campaign): Promise<AssetCategory[]> {
    const interface: AssetRequirement[] = [];
    const icons: AssetRequirement[] = [];
    const fonts: AssetRequirement[] = [];

    // Main UI elements
    const uiElements = [
      'main_menu', 'pause_menu', 'inventory_screen', 'character_sheet',
      'dialogue_box', 'combat_hud', 'minimap', 'quest_log', 'settings_menu'
    ];

    uiElements.forEach(element => {
      interface.push({
        id: `ui_${element}`,
        name: `${element.replace(/_/g, ' ')} Interface`,
        description: `User interface for ${element.replace(/_/g, ' ')}`,
        type: 'ui',
        category: 'interface',
        subcategory: element,
        specifications: {
          resolution: { width: 1920, height: 1080 },
          format: ['psd', 'png', 'svg'],
          quality: 'high'
        },
        usage: {
          scenes: ['all'],
          characters: [],
          frequency: element.includes('hud') ? 'constant' : 'common',
          context: 'ui',
          platforms: ['pc', 'console'],
          performanceImpact: 'low',
          memoryFootprint: 2,
          loadingFrequency: 'preload'
        },
        alternatives: [
          {
            type: 'simplified',
            description: 'Minimalist UI design',
            costReduction: 0.4,
            qualityImpact: 0.2,
            implementationNotes: 'Use simple geometric shapes'
          }
        ],
        dependencies: [],
        priority: element.includes('hud') || element.includes('menu') ? 'critical' : 'important',
        estimatedCost: this.getAssetCost('ui_element'),
        estimatedTimeHours: this.getAssetTime('ui_element'),
        technicalRequirements: [
          {
            platform: 'unity',
            plugins: ['UI Toolkit'],
            performance: { maxTextureSize: 1024, maxFileSize: 2, targetFPS: 60 }
          }
        ],
        sources: [
          {
            type: 'create',
            license: 'commercial',
            cost: this.getAssetCost('ui_element')
          }
        ]
      });
    });

    return [
      {
        id: 'interface',
        name: 'User Interface',
        type: 'ui',
        priority: 'critical',
        assets: interface,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'icons',
        name: 'Icons and Symbols',
        type: 'ui',
        priority: 'important',
        assets: icons,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'fonts',
        name: 'Typography',
        type: 'ui',
        priority: 'nice_to_have',
        assets: fonts,
        estimatedCost: 0,
        estimatedTime: 0
      }
    ];
  }

  private async generateEffectAssets(campaign: Campaign): Promise<AssetCategory[]> {
    const particles: AssetRequirement[] = [];
    const shaders: AssetRequirement[] = [];
    const lighting: AssetRequirement[] = [];

    // Spell and ability effects
    campaign.characters?.forEach(character => {
      character.abilities?.forEach((ability, index) => {
        if (ability.type === 'spell' || ability.type === 'ability') {
          particles.push({
            id: `effect_${character.id}_${ability.id || index}`,
            name: `${ability.name} - Visual Effect`,
            description: `Particle effect for ${character.name}'s ${ability.name}`,
            type: 'effect',
            category: 'particles',
            subcategory: ability.school || ability.type,
            specifications: {
              format: ['prefab', 'vfx'],
              quality: 'high',
              duration: ability.duration || 3,
              frameRate: 30
            },
            usage: {
              scenes: this.getAbilityScenes(campaign, ability),
              characters: [character.id],
              frequency: 'common',
              context: 'combat',
              platforms: ['pc', 'console'],
              performanceImpact: 'medium',
              memoryFootprint: 4,
              loadingFrequency: 'on_demand'
            },
            alternatives: [
              {
                type: 'simplified',
                description: 'Basic particle effect',
                costReduction: 0.6,
                qualityImpact: 0.4,
                implementationNotes: 'Use built-in particle systems'
              }
            ],
            dependencies: [],
            priority: 'important',
            estimatedCost: this.getAssetCost('particle_effect'),
            estimatedTimeHours: this.getAssetTime('particle_effect'),
            technicalRequirements: [
              {
                platform: 'unity',
                plugins: ['Visual Effect Graph'],
                performance: { maxFileSize: 5, targetFPS: 60 }
              }
            ],
            sources: [
              {
                type: 'create',
                license: 'commercial',
                cost: this.getAssetCost('particle_effect')
              }
            ]
          });
        }
      });
    });

    return [
      {
        id: 'particles',
        name: 'Particle Effects',
        type: 'effect',
        priority: 'important',
        assets: particles,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'shaders',
        name: 'Shaders',
        type: 'effect',
        priority: 'nice_to_have',
        assets: shaders,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'lighting',
        name: 'Lighting Effects',
        type: 'effect',
        priority: 'important',
        assets: lighting,
        estimatedCost: 0,
        estimatedTime: 0
      }
    ];
  }

  private async generateAnimationAssets(campaign: Campaign): Promise<AssetCategory[]> {
    const characterAnimations: AssetRequirement[] = [];
    const cinematics: AssetRequirement[] = [];

    // Character animations
    campaign.characters?.forEach(character => {
      const animationsNeeded = this.getRequiredAnimations(character);
      
      animationsNeeded.forEach(animType => {
        characterAnimations.push({
          id: `anim_${character.id}_${animType}`,
          name: `${character.name} - ${animType} Animation`,
          description: `${animType} animation for ${character.name}`,
          type: 'animation',
          category: 'character_animations',
          subcategory: animType,
          specifications: {
            duration: this.getAnimationDuration(animType),
            frameRate: 30,
            format: ['fbx', 'anim'],
            quality: 'high',
            bones: 60
          },
          usage: {
            scenes: this.getCharacterScenes(character),
            characters: [character.id],
            frequency: this.getAnimationFrequency(animType),
            context: 'gameplay',
            platforms: ['pc', 'console'],
            performanceImpact: 'low',
            memoryFootprint: 2,
            loadingFrequency: 'preload'
          },
          alternatives: [
            {
              type: 'procedural',
              description: 'Procedural animation system',
              costReduction: 0.7,
              qualityImpact: 0.3,
              implementationNotes: 'Use inverse kinematics'
            }
          ],
          dependencies: [`char_${character.id}_model`],
          priority: this.getAnimationPriority(animType),
          estimatedCost: this.getAssetCost('character_animation'),
          estimatedTimeHours: this.getAssetTime('character_animation'),
          technicalRequirements: [
            {
              platform: 'unity',
              plugins: ['Animator Controller'],
              performance: { maxFileSize: 2, targetFPS: 60 }
            }
          ],
          sources: [
            {
              type: 'create',
              license: 'commercial',
              cost: this.getAssetCost('character_animation')
            }
          ]
        });
      });
    });

    return [
      {
        id: 'character_animations',
        name: 'Character Animations',
        type: 'animation',
        priority: 'critical',
        assets: characterAnimations,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'cinematics',
        name: 'Cinematic Sequences',
        type: 'animation',
        priority: 'optional',
        assets: cinematics,
        estimatedCost: 0,
        estimatedTime: 0
      }
    ];
  }

  private async generateGameplayAssets(campaign: Campaign): Promise<AssetCategory[]> {
    const scripts: AssetRequirement[] = [];
    const data: AssetRequirement[] = [];

    // Core gameplay scripts
    const gameplayFeatures = [
      'combat_system', 'dialogue_system', 'inventory_management',
      'quest_system', 'save_load', 'settings_manager', 'input_handler'
    ];

    gameplayFeatures.forEach(feature => {
      scripts.push({
        id: `script_${feature}`,
        name: `${feature.replace(/_/g, ' ')} Script`,
        description: `Core gameplay script for ${feature.replace(/_/g, ' ')}`,
        type: 'script',
        category: 'gameplay_scripts',
        subcategory: feature,
        specifications: {
          format: ['cs', 'js', 'gd'],
          quality: 'high'
        },
        usage: {
          scenes: ['all'],
          characters: [],
          frequency: 'constant',
          context: 'gameplay',
          platforms: ['pc', 'console'],
          performanceImpact: 'low',
          memoryFootprint: 1,
          loadingFrequency: 'preload'
        },
        alternatives: [
          {
            type: 'existing',
            description: 'Use existing framework/library',
            costReduction: 0.8,
            qualityImpact: 0.1,
            implementationNotes: 'Integrate third-party solution'
          }
        ],
        dependencies: [],
        priority: 'critical',
        estimatedCost: this.getAssetCost('gameplay_script'),
        estimatedTimeHours: this.getAssetTime('gameplay_script'),
        technicalRequirements: [
          {
            platform: 'unity',
            plugins: [],
            performance: { targetFPS: 60 }
          }
        ],
        sources: [
          {
            type: 'create',
            license: 'commercial',
            cost: this.getAssetCost('gameplay_script')
          }
        ]
      });
    });

    return [
      {
        id: 'gameplay_scripts',
        name: 'Gameplay Scripts',
        type: 'script',
        priority: 'critical',
        assets: scripts,
        estimatedCost: 0,
        estimatedTime: 0
      },
      {
        id: 'game_data',
        name: 'Game Data Files',
        type: 'script',
        priority: 'critical',
        assets: data,
        estimatedCost: 0,
        estimatedTime: 0
      }
    ];
  }

  async generateBudget(categories: AssetCategory[]): Promise<AssetBudget> {
    const totalEstimatedCost = categories.reduce((sum, cat) => sum + cat.estimatedCost, 0);
    
    const breakdown = {
      models: categories.filter(c => c.type === 'model').reduce((sum, c) => sum + c.estimatedCost, 0),
      textures: categories.filter(c => c.type === 'texture').reduce((sum, c) => sum + c.estimatedCost, 0),
      audio: categories.filter(c => c.type === 'audio').reduce((sum, c) => sum + c.estimatedCost, 0),
      animations: categories.filter(c => c.type === 'animation').reduce((sum, c) => sum + c.estimatedCost, 0),
      ui: categories.filter(c => c.type === 'ui').reduce((sum, c) => sum + c.estimatedCost, 0),
      effects: categories.filter(c => c.type === 'effect').reduce((sum, c) => sum + c.estimatedCost, 0),
      scripts: categories.filter(c => c.type === 'script').reduce((sum, c) => sum + c.estimatedCost, 0)
    };

    const totalHours = categories.reduce((sum, cat) => sum + cat.estimatedTime, 0);
    
    const timeEstimate = {
      totalHours,
      breakdown: {
        modeling: totalHours * 0.3,
        texturing: totalHours * 0.2,
        animation: totalHours * 0.2,
        audio: totalHours * 0.1,
        programming: totalHours * 0.15,
        testing: totalHours * 0.05
      }
    };

    const riskFactors: RiskFactor[] = [
      {
        category: 'technical',
        description: 'Complex character rigging requirements',
        probability: 0.6,
        impact: 0.3,
        mitigation: 'Use proven rigging workflows'
      },
      {
        category: 'scope',
        description: 'Asset requirements may expand during development',
        probability: 0.8,
        impact: 0.5,
        mitigation: 'Plan for 20% contingency budget'
      },
      {
        category: 'quality',
        description: 'Art style iteration may require rework',
        probability: 0.4,
        impact: 0.4,
        mitigation: 'Create style guide early'
      }
    ];

    return {
      totalEstimatedCost,
      breakdown,
      timeEstimate,
      riskFactors
    };
  }

  async generatePipeline(): Promise<AssetPipeline> {
    const workflows: PipelineWorkflow[] = [
      {
        stage: 'concept',
        input: ['brief', 'references'],
        output: ['concept_art', 'style_guide'],
        tools: ['photoshop', 'illustrator'],
        duration: 40,
        dependencies: [],
        quality_gates: [
          {
            name: 'art_direction_approval',
            criteria: [
              { metric: 'stakeholder_approval', operator: '=', value: 'approved' }
            ],
            automated: false,
            blocking: true
          }
        ]
      },
      {
        stage: 'modeling',
        input: ['concept_art'],
        output: ['base_mesh', 'uv_maps'],
        tools: ['blender', 'maya', '3ds_max'],
        duration: 80,
        dependencies: ['concept'],
        quality_gates: [
          {
            name: 'poly_count_check',
            criteria: [
              { metric: 'poly_count', operator: '<=', value: 8000 }
            ],
            automated: true,
            blocking: true
          }
        ]
      }
    ];

    const tools: PipelineTool[] = [
      {
        name: 'Blender',
        type: 'modeling',
        cost: 0,
        alternatives: ['Maya', '3ds Max'],
        learning_curve: 'medium'
      },
      {
        name: 'Substance Painter',
        type: 'texturing',
        cost: 50,
        alternatives: ['Photoshop', 'GIMP'],
        learning_curve: 'medium'
      }
    ];

    const standards: QualityStandard[] = [
      {
        category: 'modeling',
        metric: 'poly_count',
        target: 4000,
        measurement: 'triangle_count',
        acceptance_criteria: 'Must be under maximum for target platform'
      }
    ];

    const deliverables: Deliverable[] = [
      {
        name: 'Final Asset Package',
        format: 'Unity Package',
        location: '/assets/final/',
        approval_required: true,
        stakeholders: ['art_director', 'technical_director']
      }
    ];

    return { workflows, tools, standards, deliverables };
  }

  async exportAssetRequirements(
    categories: AssetCategory[],
    outputPath: string,
    options: AssetExportOptions
  ): Promise<void> {
    this.emit('export:started', { format: options.format, outputPath });

    const filteredCategories = this.filterCategories(categories, options);
    const sortedCategories = this.sortCategories(filteredCategories, options);

    switch (options.format) {
      case 'json':
        await this.exportAsJSON(sortedCategories, outputPath, options);
        break;
      case 'csv':
        await this.exportAsCSV(sortedCategories, outputPath, options);
        break;
      case 'xlsx':
        await this.exportAsExcel(sortedCategories, outputPath, options);
        break;
      case 'pdf':
        await this.exportAsPDF(sortedCategories, outputPath, options);
        break;
      case 'html':
        await this.exportAsHTML(sortedCategories, outputPath, options);
        break;
    }

    this.emit('export:completed', { format: options.format, outputPath });
  }

  // Helper methods implementation
  private initializeDatabases(): void {
    // Asset cost database (in USD)
    this.costDatabase.set('character_model:player', 800);
    this.costDatabase.set('character_model:npc', 400);
    this.costDatabase.set('character_model:enemy', 300);
    this.costDatabase.set('character_texture:player', 200);
    this.costDatabase.set('character_texture:npc', 100);
    this.costDatabase.set('character_texture:enemy', 80);
    this.costDatabase.set('equipment_model', 50);
    this.costDatabase.set('terrain_texture', 150);
    this.costDatabase.set('environment_prop', 75);
    this.costDatabase.set('background_music', 100);
    this.costDatabase.set('sound_effect', 25);
    this.costDatabase.set('ui_element', 150);
    this.costDatabase.set('particle_effect', 100);
    this.costDatabase.set('character_animation', 200);
    this.costDatabase.set('gameplay_script', 1000);

    // Time estimate database (in hours)
    this.timeDatabase.set('character_model:player', 40);
    this.timeDatabase.set('character_model:npc', 20);
    this.timeDatabase.set('character_model:enemy', 15);
    this.timeDatabase.set('character_texture:player', 10);
    this.timeDatabase.set('character_texture:npc', 6);
    this.timeDatabase.set('character_texture:enemy', 4);
    this.timeDatabase.set('equipment_model', 3);
    this.timeDatabase.set('terrain_texture', 8);
    this.timeDatabase.set('environment_prop', 4);
    this.timeDatabase.set('background_music', 8);
    this.timeDatabase.set('sound_effect', 2);
    this.timeDatabase.set('ui_element', 6);
    this.timeDatabase.set('particle_effect', 5);
    this.timeDatabase.set('character_animation', 12);
    this.timeDatabase.set('gameplay_script', 40);
  }

  private getAssetCost(type: string, subtype?: string): number {
    const key = subtype ? `${type}:${subtype}` : type;
    return this.costDatabase.get(key) || this.costDatabase.get(type) || 100;
  }

  private getAssetTime(type: string, subtype?: string): number {
    const key = subtype ? `${type}:${subtype}` : type;
    return this.timeDatabase.get(key) || this.timeDatabase.get(type) || 8;
  }

  private calculateCategoryCost(category: AssetCategory): number {
    return category.assets.reduce((sum, asset) => sum + asset.estimatedCost, 0);
  }

  private calculateCategoryTime(category: AssetCategory): number {
    return category.assets.reduce((sum, asset) => sum + asset.estimatedTimeHours, 0);
  }

  private getCharacterScenes(character: Character): string[] {
    return ['main_game']; // Simplified - would analyze campaign scenes
  }

  private identifyMusicNeeds(campaign: Campaign): string[] {
    const moods = new Set<string>();
    moods.add('exploration');
    moods.add('combat');
    moods.add('dialogue');
    moods.add('menu');
    
    if (campaign.setting?.includes('dark')) moods.add('dark_atmosphere');
    if (campaign.setting?.includes('magic')) moods.add('magical');
    
    return Array.from(moods);
  }

  private getScenesWithMood(campaign: Campaign, mood: string): string[] {
    return ['scene_' + mood]; // Simplified implementation
  }

  private identifySoundEffectNeeds(campaign: Campaign): any[] {
    return [
      {
        id: 'sword_swing',
        name: 'Sword Swing',
        description: 'Sound of sword being swung',
        category: 'combat',
        duration: 1,
        scenes: ['combat'],
        characters: [],
        frequency: 'common',
        priority: 'critical'
      }
    ];
  }

  private getAbilityScenes(campaign: Campaign, ability: any): string[] {
    return ['combat']; // Simplified
  }

  private getRequiredAnimations(character: Character): string[] {
    const animations = ['idle', 'walk', 'run'];
    
    if (character.type === 'player' || character.type === 'npc') {
      animations.push('talk', 'gesture');
    }
    
    if (character.equipment?.some(e => e.type === 'weapon')) {
      animations.push('attack', 'block');
    }
    
    if (character.abilities?.some(a => a.type === 'spell')) {
      animations.push('cast_spell');
    }
    
    return animations;
  }

  private getAnimationDuration(animType: string): number {
    const durations: { [key: string]: number } = {
      idle: 2, walk: 1, run: 0.8, attack: 1.5, cast_spell: 2.5, death: 3
    };
    return durations[animType] || 1.5;
  }

  private getAnimationFrequency(animType: string): AssetUsage['frequency'] {
    if (animType === 'idle' || animType === 'walk') return 'constant';
    if (animType === 'run' || animType === 'attack') return 'common';
    return 'rare';
  }

  private getAnimationPriority(animType: string): AssetRequirement['priority'] {
    if (animType === 'idle' || animType === 'walk') return 'critical';
    if (animType === 'run' || animType === 'attack') return 'important';
    return 'nice_to_have';
  }

  private filterCategories(categories: AssetCategory[], options: AssetExportOptions): AssetCategory[] {
    if (!options.filterBy) return categories;
    
    return categories.filter(category => {
      if (options.filterBy!.category && !options.filterBy!.category.includes(category.id)) return false;
      if (options.filterBy!.priority && !options.filterBy!.priority.includes(category.priority)) return false;
      if (options.filterBy!.type && !options.filterBy!.type.includes(category.type)) return false;
      return true;
    });
  }

  private sortCategories(categories: AssetCategory[], options: AssetExportOptions): AssetCategory[] {
    return categories.sort((a, b) => {
      switch (options.sortBy) {
        case 'name': return a.name.localeCompare(b.name);
        case 'priority':
          const priorities = { critical: 4, important: 3, nice_to_have: 2, optional: 1 };
          return priorities[b.priority] - priorities[a.priority];
        case 'cost': return b.estimatedCost - a.estimatedCost;
        case 'time': return b.estimatedTime - a.estimatedTime;
        default: return 0;
      }
    });
  }

  private async exportAsJSON(categories: AssetCategory[], outputPath: string, options: AssetExportOptions): Promise<void> {
    await fs.writeJSON(outputPath, categories, { spaces: 2 });
  }

  private async exportAsCSV(categories: AssetCategory[], outputPath: string, options: AssetExportOptions): Promise<void> {
    const headers = ['Category', 'Asset Name', 'Type', 'Priority'];
    if (options.includeCosts) headers.push('Cost');
    if (options.includeTimeEstimates) headers.push('Hours');

    const rows = [headers.join(',')];
    
    categories.forEach(category => {
      category.assets.forEach(asset => {
        const row = [category.name, asset.name, asset.type, asset.priority];
        if (options.includeCosts) row.push(asset.estimatedCost.toString());
        if (options.includeTimeEstimates) row.push(asset.estimatedTimeHours.toString());
        rows.push(row.map(cell => `"${cell}"`).join(','));
      });
    });

    await fs.writeFile(outputPath, rows.join('\n'));
  }

  private async exportAsExcel(categories: AssetCategory[], outputPath: string, options: AssetExportOptions): Promise<void> {
    // Excel export would require a library like xlsx
    console.log('Excel export not implemented yet');
  }

  private async exportAsPDF(categories: AssetCategory[], outputPath: string, options: AssetExportOptions): Promise<void> {
    // PDF export would require a library like puppeteer or jsPDF
    console.log('PDF export not implemented yet');
  }

  private async exportAsHTML(categories: AssetCategory[], outputPath: string, options: AssetExportOptions): Promise<void> {
    let html = `
<!DOCTYPE html>
<html>
<head>
    <title>Asset Requirements</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .category { font-weight: bold; background-color: #e6f3ff; }
        .priority-critical { color: red; }
        .priority-important { color: orange; }
        .priority-nice_to_have { color: blue; }
        .priority-optional { color: gray; }
    </style>
</head>
<body>
    <h1>Asset Requirements</h1>
    <table>
        <tr>
            <th>Category</th>
            <th>Asset Name</th>
            <th>Type</th>
            <th>Priority</th>`;
    
    if (options.includeCosts) html += '<th>Cost ($)</th>';
    if (options.includeTimeEstimates) html += '<th>Hours</th>';
    html += '</tr>';

    categories.forEach(category => {
      html += `<tr class="category"><td colspan="4">${category.name}</td></tr>`;
      category.assets.forEach(asset => {
        html += `<tr>
            <td>${category.name}</td>
            <td>${asset.name}</td>
            <td>${asset.type}</td>
            <td class="priority-${asset.priority}">${asset.priority}</td>`;
        
        if (options.includeCosts) html += `<td>$${asset.estimatedCost}</td>`;
        if (options.includeTimeEstimates) html += `<td>${asset.estimatedTimeHours}</td>`;
        html += '</tr>';
      });
    });

    html += `
    </table>
</body>
</html>`;

    await fs.writeFile(outputPath, html);
  }
}