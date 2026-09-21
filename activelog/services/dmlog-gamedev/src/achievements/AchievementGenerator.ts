import { EventEmitter } from 'events';
import fs from 'fs-extra';
import path from 'path';
import { Campaign, Character, Map, Encounter } from '../types';

export interface Achievement {
  id: string;
  name: string;
  description: string;
  category: AchievementCategory;
  type: AchievementType;
  rarity: AchievementRarity;
  points: number;
  icon: string;
  hidden: boolean;
  prerequisites: string[];
  conditions: AchievementCondition[];
  rewards: AchievementReward[];
  metadata: AchievementMetadata;
  localization: AchievementLocalization[];
  tracking: AchievementTracking;
  progression?: ProgressionData;
}

export type AchievementCategory = 
  | 'story' 
  | 'combat' 
  | 'exploration' 
  | 'collection' 
  | 'social' 
  | 'skill' 
  | 'time' 
  | 'special' 
  | 'secret'
  | 'meta';

export type AchievementType = 
  | 'single' 
  | 'incremental' 
  | 'tiered' 
  | 'conditional' 
  | 'time_limited' 
  | 'sequence'
  | 'meta_achievement';

export type AchievementRarity = 
  | 'common' 
  | 'uncommon' 
  | 'rare' 
  | 'epic' 
  | 'legendary';

export interface AchievementCondition {
  id: string;
  type: ConditionType;
  target: string;
  operator: ComparisonOperator;
  value: number | string | boolean;
  modifiers?: ConditionModifier[];
  timeframe?: TimeframeConstraint;
  context?: ContextConstraint[];
}

export type ConditionType = 
  | 'stat_reached' 
  | 'event_triggered' 
  | 'item_collected' 
  | 'location_visited'
  | 'character_interaction' 
  | 'combat_victory' 
  | 'quest_completed' 
  | 'skill_used'
  | 'time_spent' 
  | 'death_count' 
  | 'damage_dealt' 
  | 'damage_taken'
  | 'level_reached' 
  | 'experience_gained' 
  | 'resource_gathered'
  | 'achievement_unlocked' 
  | 'playtime_reached' 
  | 'session_count';

export type ComparisonOperator = 
  | '==' 
  | '!=' 
  | '>' 
  | '<' 
  | '>=' 
  | '<=' 
  | 'contains' 
  | 'not_contains'
  | 'between' 
  | 'consecutive' 
  | 'within_timeframe';

export interface ConditionModifier {
  type: 'multiplier' | 'bonus' | 'penalty' | 'override';
  value: number;
  condition: string;
  description: string;
}

export interface TimeframeConstraint {
  type: 'single_session' | 'single_day' | 'single_week' | 'single_month' | 'lifetime';
  duration?: number;
  unit?: 'seconds' | 'minutes' | 'hours' | 'days';
}

export interface ContextConstraint {
  type: 'location' | 'character' | 'difficulty' | 'mode' | 'equipment' | 'status';
  value: string;
  required: boolean;
}

export interface AchievementReward {
  type: RewardType;
  item_id?: string;
  quantity: number;
  description: string;
  permanent: boolean;
}

export type RewardType = 
  | 'experience' 
  | 'currency' 
  | 'item' 
  | 'title' 
  | 'cosmetic' 
  | 'unlock' 
  | 'bonus'
  | 'badge' 
  | 'points' 
  | 'buff';

export interface AchievementMetadata {
  created_date: Date;
  difficulty_rating: number;
  estimated_completion_time: number;
  completion_percentage: number;
  design_notes: string;
  balance_notes: string;
  testing_notes: string;
  version_added: string;
  tags: string[];
}

export interface AchievementLocalization {
  language: string;
  name: string;
  description: string;
  flavor_text?: string;
  hint?: string;
}

export interface AchievementTracking {
  track_progress: boolean;
  progress_text: string;
  progress_format: 'percentage' | 'fraction' | 'count';
  milestone_notifications: boolean;
  analytics_events: string[];
  debug_logging: boolean;
}

export interface ProgressionData {
  current_value: number;
  target_value: number;
  milestones: ProgressionMilestone[];
  incremental_rewards: boolean;
}

export interface ProgressionMilestone {
  threshold: number;
  reward?: AchievementReward;
  notification: string;
}

export interface AchievementSystem {
  id: string;
  name: string;
  campaign_id: string;
  achievements: Achievement[];
  categories: AchievementCategoryDefinition[];
  global_settings: AchievementGlobalSettings;
  balance_config: AchievementBalanceConfig;
  integration_config: AchievementIntegrationConfig;
  analytics_config: AchievementAnalyticsConfig;
}

export interface AchievementCategoryDefinition {
  id: AchievementCategory;
  name: string;
  description: string;
  icon: string;
  color: string;
  sort_order: number;
  unlocked_by_default: boolean;
}

export interface AchievementGlobalSettings {
  notifications_enabled: boolean;
  sound_effects_enabled: boolean;
  popup_duration: number;
  max_concurrent_popups: number;
  retroactive_unlock: boolean;
  offline_progress: boolean;
  cloud_sync: boolean;
  achievements_per_page: number;
  show_completion_percentage: boolean;
  show_rarity_distribution: boolean;
}

export interface AchievementBalanceConfig {
  point_multipliers: { [rarity in AchievementRarity]: number };
  category_weights: { [category in AchievementCategory]: number };
  difficulty_scaling: DifficultyScaling;
  reward_scaling: RewardScaling;
  time_decay_factors: TimeDecayFactors;
}

export interface DifficultyScaling {
  base_difficulty: number;
  scaling_factor: number;
  max_difficulty: number;
  category_modifiers: { [category in AchievementCategory]: number };
}

export interface RewardScaling {
  base_rewards: { [type in RewardType]: number };
  rarity_multipliers: { [rarity in AchievementRarity]: number };
  category_bonuses: { [category in AchievementCategory]: number };
}

export interface TimeDecayFactors {
  enabled: boolean;
  decay_rate: number;
  minimum_multiplier: number;
  categories_affected: AchievementCategory[];
}

export interface AchievementIntegrationConfig {
  steam_integration: boolean;
  platform_achievements: boolean;
  leaderboards: boolean;
  social_sharing: boolean;
  export_formats: string[];
  api_endpoints: string[];
}

export interface AchievementAnalyticsConfig {
  track_unlock_events: boolean;
  track_progress_events: boolean;
  track_attempt_events: boolean;
  funnel_analysis: boolean;
  difficulty_analysis: boolean;
  completion_time_analysis: boolean;
  custom_events: CustomAnalyticsEvent[];
}

export interface CustomAnalyticsEvent {
  name: string;
  description: string;
  parameters: string[];
  frequency: 'always' | 'milestone' | 'completion';
}

export interface AchievementGenerationOptions {
  categories: AchievementCategory[];
  difficulty_range: [number, number];
  rarity_distribution: { [rarity in AchievementRarity]: number };
  include_hidden: boolean;
  include_meta: boolean;
  include_time_limited: boolean;
  progression_achievements: boolean;
  social_achievements: boolean;
  platform_integration: boolean;
  localization_languages: string[];
  custom_conditions: AchievementCondition[];
  reward_pool: AchievementReward[];
}

export interface AchievementExportOptions {
  format: 'json' | 'xml' | 'yaml' | 'csv' | 'steam' | 'unity' | 'unreal' | 'godot';
  include_metadata: boolean;
  include_localization: boolean;
  include_analytics: boolean;
  include_balance_data: boolean;
  minified: boolean;
  separate_files_per_category: boolean;
}

export class AchievementGenerator extends EventEmitter {
  private templates: Map<string, any> = new Map();
  private balanceData: Map<string, any> = new Map();
  private localizationData: Map<string, any> = new Map();

  constructor() {
    super();
    this.initializeTemplates();
    this.initializeBalanceData();
  }

  async generateAchievementSystem(
    campaign: Campaign,
    options: AchievementGenerationOptions = {} as AchievementGenerationOptions
  ): Promise<AchievementSystem> {
    this.emit('generation:started', { campaignId: campaign.id });

    // Set default options
    const defaultOptions: AchievementGenerationOptions = {
      categories: ['story', 'combat', 'exploration', 'collection', 'skill'],
      difficulty_range: [1, 10],
      rarity_distribution: {
        common: 0.5,
        uncommon: 0.3,
        rare: 0.15,
        epic: 0.04,
        legendary: 0.01
      },
      include_hidden: true,
      include_meta: true,
      include_time_limited: false,
      progression_achievements: true,
      social_achievements: false,
      platform_integration: true,
      localization_languages: ['en'],
      custom_conditions: [],
      reward_pool: []
    };

    const finalOptions = { ...defaultOptions, ...options };

    // Generate achievements
    const achievements = await this.generateAchievements(campaign, finalOptions);
    
    // Generate category definitions
    const categories = this.generateCategoryDefinitions(finalOptions.categories);
    
    // Generate system configuration
    const globalSettings = this.generateGlobalSettings(campaign, finalOptions);
    const balanceConfig = this.generateBalanceConfig(campaign, finalOptions);
    const integrationConfig = this.generateIntegrationConfig(finalOptions);
    const analyticsConfig = this.generateAnalyticsConfig(campaign, finalOptions);

    const achievementSystem: AchievementSystem = {
      id: `achievements_${campaign.id}`,
      name: `${campaign.title} Achievement System`,
      campaign_id: campaign.id,
      achievements,
      categories,
      global_settings: globalSettings,
      balance_config: balanceConfig,
      integration_config: integrationConfig,
      analytics_config: analyticsConfig
    };

    this.emit('generation:completed', { achievementSystem });
    return achievementSystem;
  }

  private async generateAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Promise<Achievement[]> {
    const achievements: Achievement[] = [];

    // Story achievements
    if (options.categories.includes('story')) {
      achievements.push(...this.generateStoryAchievements(campaign, options));
    }

    // Combat achievements
    if (options.categories.includes('combat')) {
      achievements.push(...this.generateCombatAchievements(campaign, options));
    }

    // Exploration achievements
    if (options.categories.includes('exploration')) {
      achievements.push(...this.generateExplorationAchievements(campaign, options));
    }

    // Collection achievements
    if (options.categories.includes('collection')) {
      achievements.push(...this.generateCollectionAchievements(campaign, options));
    }

    // Skill achievements
    if (options.categories.includes('skill')) {
      achievements.push(...this.generateSkillAchievements(campaign, options));
    }

    // Time-based achievements
    if (options.categories.includes('time')) {
      achievements.push(...this.generateTimeAchievements(campaign, options));
    }

    // Social achievements
    if (options.social_achievements) {
      achievements.push(...this.generateSocialAchievements(campaign, options));
    }

    // Meta achievements
    if (options.include_meta) {
      achievements.push(...this.generateMetaAchievements(campaign, achievements, options));
    }

    // Secret achievements
    if (options.include_hidden) {
      achievements.push(...this.generateSecretAchievements(campaign, options));
    }

    // Assign rarities and balance
    return this.balanceAchievements(achievements, options);
  }

  private generateStoryAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    // Main story progression
    if (campaign.scenes && campaign.scenes.length > 0) {
      const majorMilestones = Math.ceil(campaign.scenes.length / 3);
      for (let i = 1; i <= majorMilestones; i++) {
        const scenesRequired = Math.floor((campaign.scenes.length * i) / majorMilestones);
        achievements.push({
          id: `story_chapter_${i}`,
          name: `Chapter ${i} Complete`,
          description: `Complete Chapter ${i} of the main story`,
          category: 'story',
          type: 'single',
          rarity: 'common',
          points: 50 * i,
          icon: 'story_chapter',
          hidden: false,
          prerequisites: i > 1 ? [`story_chapter_${i - 1}`] : [],
          conditions: [
            {
              id: 'scenes_completed',
              type: 'quest_completed',
              target: 'main_story_scenes',
              operator: '>=',
              value: scenesRequired
            }
          ],
          rewards: [
            {
              type: 'experience',
              quantity: 500 * i,
              description: `Bonus XP for completing Chapter ${i}`,
              permanent: true
            }
          ],
          metadata: {
            created_date: new Date(),
            difficulty_rating: i * 2,
            estimated_completion_time: i * 120,
            completion_percentage: 0.9 - (i * 0.1),
            design_notes: `Story milestone achievement for chapter ${i}`,
            balance_notes: 'Standard story progression reward',
            testing_notes: 'Test with full story playthrough',
            version_added: '1.0.0',
            tags: ['story', 'progression', 'main_quest']
          },
          localization: [
            {
              language: 'en',
              name: `Chapter ${i} Complete`,
              description: `Complete Chapter ${i} of the main story`,
              flavor_text: `Another chapter in your legendary tale...`
            }
          ],
          tracking: {
            track_progress: true,
            progress_text: `Progress: {current}/{target} scenes`,
            progress_format: 'fraction',
            milestone_notifications: true,
            analytics_events: ['story_milestone_reached'],
            debug_logging: true
          }
        });
      }
    }

    // Character development
    if (campaign.characters) {
      const mainCharacters = campaign.characters.filter(c => c.type === 'player' || c.importance === 'main');
      mainCharacters.forEach((character, index) => {
        achievements.push({
          id: `character_development_${character.id}`,
          name: `${character.name}'s Journey`,
          description: `Complete ${character.name}'s character development arc`,
          category: 'story',
          type: 'single',
          rarity: 'uncommon',
          points: 75,
          icon: 'character_development',
          hidden: false,
          prerequisites: [],
          conditions: [
            {
              id: 'character_arc_complete',
              type: 'character_interaction',
              target: character.id,
              operator: '>=',
              value: 10
            }
          ],
          rewards: [
            {
              type: 'title',
              quantity: 1,
              description: `Unlock "${character.name}'s Companion" title`,
              permanent: true
            }
          ],
          metadata: {
            created_date: new Date(),
            difficulty_rating: 5,
            estimated_completion_time: 300,
            completion_percentage: 0.4,
            design_notes: `Character-specific story achievement for ${character.name}`,
            balance_notes: 'Rewards meaningful character interaction',
            testing_notes: 'Ensure all character interactions are trackable',
            version_added: '1.0.0',
            tags: ['story', 'character', 'relationship']
          },
          localization: [
            {
              language: 'en',
              name: `${character.name}'s Journey`,
              description: `Complete ${character.name}'s character development arc`
            }
          ],
          tracking: {
            track_progress: true,
            progress_text: `${character.name} interactions: {current}/{target}`,
            progress_format: 'fraction',
            milestone_notifications: false,
            analytics_events: ['character_development_progress'],
            debug_logging: false
          }
        });
      });
    }

    return achievements;
  }

  private generateCombatAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    // Victory achievements
    achievements.push({
      id: 'first_victory',
      name: 'First Blood',
      description: 'Win your first combat encounter',
      category: 'combat',
      type: 'single',
      rarity: 'common',
      points: 25,
      icon: 'first_victory',
      hidden: false,
      prerequisites: [],
      conditions: [
        {
          id: 'combat_victories',
          type: 'combat_victory',
          target: 'any',
          operator: '>=',
          value: 1
        }
      ],
      rewards: [
        {
          type: 'experience',
          quantity: 100,
          description: 'First victory bonus',
          permanent: true
        }
      ],
      metadata: this.createDefaultMetadata('First combat victory achievement', 1, 30, 0.95),
      localization: [
        {
          language: 'en',
          name: 'First Blood',
          description: 'Win your first combat encounter',
          flavor_text: 'Every hero must start somewhere...'
        }
      ],
      tracking: this.createDefaultTracking('combat_victories', 'count')
    });

    // Combat mastery
    const combatMilestones = [10, 50, 100, 250, 500];
    combatMilestones.forEach((milestone, index) => {
      const rarity = index < 2 ? 'common' : index < 4 ? 'uncommon' : 'rare';
      achievements.push({
        id: `combat_veteran_${milestone}`,
        name: `Combat Veteran ${milestone}`,
        description: `Win ${milestone} combat encounters`,
        category: 'combat',
        type: 'incremental',
        rarity,
        points: 25 * (index + 1),
        icon: 'combat_veteran',
        hidden: false,
        prerequisites: index > 0 ? [`combat_veteran_${combatMilestones[index - 1]}`] : [],
        conditions: [
          {
            id: 'total_victories',
            type: 'combat_victory',
            target: 'any',
            operator: '>=',
            value: milestone
          }
        ],
        rewards: [
          {
            type: 'currency',
            quantity: 100 * (index + 1),
            description: `Combat mastery reward`,
            permanent: true
          }
        ],
        metadata: this.createDefaultMetadata(`Combat milestone for ${milestone} victories`, 3 + index, 60 * milestone, 0.8 - (index * 0.15)),
        localization: [
          {
            language: 'en',
            name: `Combat Veteran ${milestone}`,
            description: `Win ${milestone} combat encounters`
          }
        ],
        tracking: this.createProgressiveTracking('combat_victories', milestone, 'fraction'),
        progression: {
          current_value: 0,
          target_value: milestone,
          milestones: [],
          incremental_rewards: false
        }
      });
    });

    // Perfect combat
    achievements.push({
      id: 'perfect_combat',
      name: 'Flawless Victory',
      description: 'Win a combat encounter without taking any damage',
      category: 'combat',
      type: 'single',
      rarity: 'rare',
      points: 100,
      icon: 'perfect_combat',
      hidden: false,
      prerequisites: [],
      conditions: [
        {
          id: 'flawless_victory',
          type: 'combat_victory',
          target: 'any',
          operator: '==',
          value: 1,
          modifiers: [
            {
              type: 'override',
              value: 0,
              condition: 'damage_taken == 0',
              description: 'No damage taken during combat'
            }
          ]
        }
      ],
      rewards: [
        {
          type: 'title',
          quantity: 1,
          description: 'Unlock "The Untouchable" title',
          permanent: true
        }
      ],
      metadata: this.createDefaultMetadata('Perfect combat achievement requiring no damage taken', 8, 180, 0.15),
      localization: [
        {
          language: 'en',
          name: 'Flawless Victory',
          description: 'Win a combat encounter without taking any damage',
          flavor_text: 'Perfection in combat is an art form'
        }
      ],
      tracking: this.createDefaultTracking('flawless_victories', 'count')
    });

    return achievements;
  }

  private generateExplorationAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    if (campaign.maps && campaign.maps.length > 0) {
      // Map discovery
      campaign.maps.forEach((map, index) => {
        achievements.push({
          id: `explore_${map.id}`,
          name: `Explorer of ${map.name}`,
          description: `Fully explore the ${map.name} area`,
          category: 'exploration',
          type: 'single',
          rarity: 'common',
          points: 30,
          icon: 'map_exploration',
          hidden: false,
          prerequisites: [],
          conditions: [
            {
              id: 'map_exploration',
              type: 'location_visited',
              target: map.id,
              operator: '>=',
              value: 100,
              context: [
                {
                  type: 'location',
                  value: map.id,
                  required: true
                }
              ]
            }
          ],
          rewards: [
            {
              type: 'experience',
              quantity: 250,
              description: `Exploration bonus for ${map.name}`,
              permanent: true
            }
          ],
          metadata: this.createDefaultMetadata(`Exploration achievement for ${map.name}`, 3, 120, 0.7),
          localization: [
            {
              language: 'en',
              name: `Explorer of ${map.name}`,
              description: `Fully explore the ${map.name} area`
            }
          ],
          tracking: this.createProgressiveTracking('exploration_percentage', 100, 'percentage')
        });
      });

      // Master explorer
      achievements.push({
        id: 'master_explorer',
        name: 'Master Explorer',
        description: 'Fully explore all available areas',
        category: 'exploration',
        type: 'single',
        rarity: 'epic',
        points: 200,
        icon: 'master_explorer',
        hidden: false,
        prerequisites: campaign.maps.map(m => `explore_${m.id}`),
        conditions: [
          {
            id: 'all_maps_explored',
            type: 'location_visited',
            target: 'all',
            operator: '>=',
            value: campaign.maps.length
          }
        ],
        rewards: [
          {
            type: 'title',
            quantity: 1,
            description: 'Unlock "Master Explorer" title',
            permanent: true
          },
          {
            type: 'currency',
            quantity: 1000,
            description: 'Master explorer reward',
            permanent: true
          }
        ],
        metadata: this.createDefaultMetadata('Master exploration achievement', 7, 600, 0.25),
        localization: [
          {
            language: 'en',
            name: 'Master Explorer',
            description: 'Fully explore all available areas',
            flavor_text: 'No corner of the world remains unknown to you'
          }
        ],
        tracking: this.createProgressiveTracking('maps_explored', campaign.maps.length, 'fraction')
      });
    }

    return achievements;
  }

  private generateCollectionAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    // Item collection milestones
    const collectionMilestones = [10, 25, 50, 100, 250];
    collectionMilestones.forEach((milestone, index) => {
      achievements.push({
        id: `collector_${milestone}`,
        name: `Collector ${milestone}`,
        description: `Collect ${milestone} unique items`,
        category: 'collection',
        type: 'incremental',
        rarity: index < 3 ? 'common' : index < 4 ? 'uncommon' : 'rare',
        points: 20 * (index + 1),
        icon: 'item_collector',
        hidden: false,
        prerequisites: [],
        conditions: [
          {
            id: 'unique_items_collected',
            type: 'item_collected',
            target: 'unique',
            operator: '>=',
            value: milestone
          }
        ],
        rewards: [
          {
            type: 'currency',
            quantity: 50 * (index + 1),
            description: 'Collection milestone reward',
            permanent: true
          }
        ],
        metadata: this.createDefaultMetadata(`Collection milestone for ${milestone} items`, 2 + index, 90 * milestone, 0.6 - (index * 0.1)),
        localization: [
          {
            language: 'en',
            name: `Collector ${milestone}`,
            description: `Collect ${milestone} unique items`
          }
        ],
        tracking: this.createProgressiveTracking('unique_items', milestone, 'fraction'),
        progression: {
          current_value: 0,
          target_value: milestone,
          milestones: [],
          incremental_rewards: true
        }
      });
    });

    return achievements;
  }

  private generateSkillAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    // Level progression
    const levelMilestones = [5, 10, 20, 30, 50];
    levelMilestones.forEach((level, index) => {
      achievements.push({
        id: `level_${level}`,
        name: `Level ${level} Achieved`,
        description: `Reach character level ${level}`,
        category: 'skill',
        type: 'single',
        rarity: index < 2 ? 'common' : index < 4 ? 'uncommon' : 'rare',
        points: 25 * (index + 1),
        icon: 'level_up',
        hidden: false,
        prerequisites: [],
        conditions: [
          {
            id: 'character_level',
            type: 'level_reached',
            target: 'player',
            operator: '>=',
            value: level
          }
        ],
        rewards: [
          {
            type: 'experience',
            quantity: 100 * level,
            description: `Level milestone bonus`,
            permanent: true
          }
        ],
        metadata: this.createDefaultMetadata(`Level progression milestone`, 2 + index, 60 * level, 0.8 - (index * 0.15)),
        localization: [
          {
            language: 'en',
            name: `Level ${level} Achieved`,
            description: `Reach character level ${level}`
          }
        ],
        tracking: this.createDefaultTracking('character_level', 'count')
      });
    });

    return achievements;
  }

  private generateTimeAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    // Playtime milestones
    const playtimeMilestones = [60, 300, 600, 1200, 3600]; // in minutes
    playtimeMilestones.forEach((minutes, index) => {
      achievements.push({
        id: `playtime_${minutes}`,
        name: `Dedicated Player ${Math.floor(minutes / 60)}h`,
        description: `Play for ${Math.floor(minutes / 60)} hours total`,
        category: 'time',
        type: 'incremental',
        rarity: 'common',
        points: 15 * (index + 1),
        icon: 'time_played',
        hidden: false,
        prerequisites: [],
        conditions: [
          {
            id: 'total_playtime',
            type: 'playtime_reached',
            target: 'total',
            operator: '>=',
            value: minutes * 60 // Convert to seconds
          }
        ],
        rewards: [
          {
            type: 'currency',
            quantity: 25 * (index + 1),
            description: 'Dedication reward',
            permanent: true
          }
        ],
        metadata: this.createDefaultMetadata(`Playtime milestone achievement`, 1, minutes * 60, 0.9 - (index * 0.1)),
        localization: [
          {
            language: 'en',
            name: `Dedicated Player ${Math.floor(minutes / 60)}h`,
            description: `Play for ${Math.floor(minutes / 60)} hours total`
          }
        ],
        tracking: this.createProgressiveTracking('playtime_seconds', minutes * 60, 'fraction'),
        progression: {
          current_value: 0,
          target_value: minutes * 60,
          milestones: [],
          incremental_rewards: false
        }
      });
    });

    // Speed run achievements
    if (campaign.scenes && campaign.scenes.length > 0) {
      achievements.push({
        id: 'speed_runner',
        name: 'Speed Runner',
        description: 'Complete the main story in under 2 hours',
        category: 'time',
        type: 'conditional',
        rarity: 'epic',
        points: 250,
        icon: 'speed_runner',
        hidden: false,
        prerequisites: [],
        conditions: [
          {
            id: 'story_completion_time',
            type: 'quest_completed',
            target: 'main_story',
            operator: '<',
            value: 7200, // 2 hours in seconds
            timeframe: {
              type: 'single_session',
              duration: 7200,
              unit: 'seconds'
            }
          }
        ],
        rewards: [
          {
            type: 'title',
            quantity: 1,
            description: 'Unlock "Speed Demon" title',
            permanent: true
          }
        ],
        metadata: this.createDefaultMetadata('Speed run achievement for experienced players', 9, 120, 0.05),
        localization: [
          {
            language: 'en',
            name: 'Speed Runner',
            description: 'Complete the main story in under 2 hours',
            flavor_text: 'Time is just a number for true masters'
          }
        ],
        tracking: this.createDefaultTracking('story_completion_time', 'time')
      });
    }

    return achievements;
  }

  private generateSocialAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    achievements.push({
      id: 'helpful_player',
      name: 'Helpful Player',
      description: 'Help another player complete a quest',
      category: 'social',
      type: 'single',
      rarity: 'uncommon',
      points: 50,
      icon: 'helpful_player',
      hidden: false,
      prerequisites: [],
      conditions: [
        {
          id: 'multiplayer_assistance',
          type: 'character_interaction',
          target: 'other_player',
          operator: '>=',
          value: 1,
          context: [
            {
              type: 'mode',
              value: 'multiplayer',
              required: true
            }
          ]
        }
      ],
      rewards: [
        {
          type: 'experience',
          quantity: 200,
          description: 'Cooperation bonus',
          permanent: true
        }
      ],
      metadata: this.createDefaultMetadata('Social cooperation achievement', 4, 180, 0.3),
      localization: [
        {
          language: 'en',
          name: 'Helpful Player',
          description: 'Help another player complete a quest',
          flavor_text: 'True heroes lift others up'
        }
      ],
      tracking: this.createDefaultTracking('multiplayer_assists', 'count')
    });

    return achievements;
  }

  private generateMetaAchievements(
    campaign: Campaign,
    baseAchievements: Achievement[],
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    // Achievement hunter milestones
    const achievementMilestones = [10, 25, 50, 75, baseAchievements.length];
    achievementMilestones.forEach((count, index) => {
      achievements.push({
        id: `achievement_hunter_${count}`,
        name: `Achievement Hunter ${count}`,
        description: `Unlock ${count} achievements`,
        category: 'meta',
        type: 'incremental',
        rarity: index < 3 ? 'uncommon' : 'rare',
        points: 30 * (index + 1),
        icon: 'achievement_hunter',
        hidden: false,
        prerequisites: [],
        conditions: [
          {
            id: 'achievements_unlocked',
            type: 'achievement_unlocked',
            target: 'any',
            operator: '>=',
            value: count
          }
        ],
        rewards: [
          {
            type: 'title',
            quantity: 1,
            description: `Unlock "Achievement Hunter" title`,
            permanent: true
          }
        ],
        metadata: this.createDefaultMetadata(`Meta achievement for unlocking ${count} achievements`, 5 + index, 300 * count, 0.6 - (index * 0.1)),
        localization: [
          {
            language: 'en',
            name: `Achievement Hunter ${count}`,
            description: `Unlock ${count} achievements`
          }
        ],
        tracking: this.createProgressiveTracking('achievements_unlocked', count, 'fraction'),
        progression: {
          current_value: 0,
          target_value: count,
          milestones: [],
          incremental_rewards: false
        }
      });
    });

    return achievements;
  }

  private generateSecretAchievements(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): Achievement[] {
    const achievements: Achievement[] = [];

    achievements.push({
      id: 'easter_egg_finder',
      name: '???',
      description: 'Find a hidden easter egg',
      category: 'secret',
      type: 'single',
      rarity: 'rare',
      points: 100,
      icon: 'easter_egg',
      hidden: true,
      prerequisites: [],
      conditions: [
        {
          id: 'easter_egg_found',
          type: 'event_triggered',
          target: 'easter_egg_interaction',
          operator: '>=',
          value: 1
        }
      ],
      rewards: [
        {
          type: 'cosmetic',
          quantity: 1,
          description: 'Unlock special cosmetic item',
          permanent: true
        }
      ],
      metadata: this.createDefaultMetadata('Hidden easter egg discovery achievement', 6, 600, 0.1),
      localization: [
        {
          language: 'en',
          name: 'Secrets Revealed',
          description: 'Find a hidden easter egg',
          flavor_text: 'Some secrets are worth searching for...'
        }
      ],
      tracking: this.createDefaultTracking('easter_eggs_found', 'count')
    });

    return achievements;
  }

  private balanceAchievements(
    achievements: Achievement[],
    options: AchievementGenerationOptions
  ): Achievement[] {
    // Apply rarity distribution
    const sortedAchievements = achievements.sort((a, b) => a.metadata.difficulty_rating - b.metadata.difficulty_rating);
    
    let rarityIndex = 0;
    const rarityKeys = Object.keys(options.rarity_distribution) as AchievementRarity[];
    const rarityValues = Object.values(options.rarity_distribution);
    
    sortedAchievements.forEach((achievement, index) => {
      const progressThrough = index / sortedAchievements.length;
      let cumulativeProbability = 0;
      
      for (let i = 0; i < rarityValues.length; i++) {
        cumulativeProbability += rarityValues[i];
        if (progressThrough <= cumulativeProbability) {
          achievement.rarity = rarityKeys[i];
          break;
        }
      }
      
      // Adjust points based on rarity
      const rarityMultipliers = {
        common: 1.0,
        uncommon: 1.5,
        rare: 2.0,
        epic: 3.0,
        legendary: 5.0
      };
      
      achievement.points = Math.floor(achievement.points * rarityMultipliers[achievement.rarity]);
    });

    return achievements;
  }

  private generateCategoryDefinitions(categories: AchievementCategory[]): AchievementCategoryDefinition[] {
    const definitions: { [key in AchievementCategory]: AchievementCategoryDefinition } = {
      story: {
        id: 'story',
        name: 'Story',
        description: 'Achievements related to story progression and narrative milestones',
        icon: 'book',
        color: '#4CAF50',
        sort_order: 1,
        unlocked_by_default: true
      },
      combat: {
        id: 'combat',
        name: 'Combat',
        description: 'Achievements for combat prowess and battle victories',
        icon: 'sword',
        color: '#F44336',
        sort_order: 2,
        unlocked_by_default: true
      },
      exploration: {
        id: 'exploration',
        name: 'Exploration',
        description: 'Achievements for discovering new areas and locations',
        icon: 'map',
        color: '#2196F3',
        sort_order: 3,
        unlocked_by_default: true
      },
      collection: {
        id: 'collection',
        name: 'Collection',
        description: 'Achievements for gathering items and collectibles',
        icon: 'treasure',
        color: '#FF9800',
        sort_order: 4,
        unlocked_by_default: true
      },
      social: {
        id: 'social',
        name: 'Social',
        description: 'Achievements for multiplayer and cooperative activities',
        icon: 'people',
        color: '#9C27B0',
        sort_order: 5,
        unlocked_by_default: false
      },
      skill: {
        id: 'skill',
        name: 'Skill',
        description: 'Achievements for character development and mastery',
        icon: 'star',
        color: '#FFEB3B',
        sort_order: 6,
        unlocked_by_default: true
      },
      time: {
        id: 'time',
        name: 'Time',
        description: 'Achievements based on time played or speed of completion',
        icon: 'clock',
        color: '#607D8B',
        sort_order: 7,
        unlocked_by_default: true
      },
      special: {
        id: 'special',
        name: 'Special',
        description: 'Unique achievements for special events and occasions',
        icon: 'special',
        color: '#E91E63',
        sort_order: 8,
        unlocked_by_default: false
      },
      secret: {
        id: 'secret',
        name: 'Secret',
        description: 'Hidden achievements for those who seek the unknown',
        icon: 'mystery',
        color: '#3F51B5',
        sort_order: 9,
        unlocked_by_default: false
      },
      meta: {
        id: 'meta',
        name: 'Meta',
        description: 'Achievements about achievements and overall progress',
        icon: 'achievement',
        color: '#795548',
        sort_order: 10,
        unlocked_by_default: true
      }
    };

    return categories.map(category => definitions[category]);
  }

  private generateGlobalSettings(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): AchievementGlobalSettings {
    return {
      notifications_enabled: true,
      sound_effects_enabled: true,
      popup_duration: 3000,
      max_concurrent_popups: 3,
      retroactive_unlock: true,
      offline_progress: true,
      cloud_sync: options.platform_integration,
      achievements_per_page: 20,
      show_completion_percentage: true,
      show_rarity_distribution: true
    };
  }

  private generateBalanceConfig(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): AchievementBalanceConfig {
    return {
      point_multipliers: {
        common: 1.0,
        uncommon: 1.5,
        rare: 2.0,
        epic: 3.0,
        legendary: 5.0
      },
      category_weights: {
        story: 1.2,
        combat: 1.0,
        exploration: 0.8,
        collection: 0.6,
        social: 1.1,
        skill: 1.0,
        time: 0.7,
        special: 2.0,
        secret: 3.0,
        meta: 1.5
      },
      difficulty_scaling: {
        base_difficulty: 1.0,
        scaling_factor: 1.2,
        max_difficulty: 10.0,
        category_modifiers: {
          story: 0.8,
          combat: 1.2,
          exploration: 0.9,
          collection: 0.7,
          social: 1.1,
          skill: 1.0,
          time: 1.5,
          special: 1.8,
          secret: 2.0,
          meta: 1.3
        }
      },
      reward_scaling: {
        base_rewards: {
          experience: 100,
          currency: 50,
          item: 1,
          title: 1,
          cosmetic: 1,
          unlock: 1,
          bonus: 1,
          badge: 1,
          points: 25,
          buff: 1
        },
        rarity_multipliers: {
          common: 1.0,
          uncommon: 1.5,
          rare: 2.5,
          epic: 4.0,
          legendary: 6.0
        },
        category_bonuses: {
          story: 1.2,
          combat: 1.0,
          exploration: 0.8,
          collection: 0.9,
          social: 1.1,
          skill: 1.0,
          time: 0.7,
          special: 2.0,
          secret: 2.5,
          meta: 1.5
        }
      },
      time_decay_factors: {
        enabled: false,
        decay_rate: 0.95,
        minimum_multiplier: 0.5,
        categories_affected: ['time']
      }
    };
  }

  private generateIntegrationConfig(options: AchievementGenerationOptions): AchievementIntegrationConfig {
    return {
      steam_integration: options.platform_integration,
      platform_achievements: options.platform_integration,
      leaderboards: true,
      social_sharing: options.social_achievements,
      export_formats: ['json', 'xml'],
      api_endpoints: ['/api/achievements', '/api/progress']
    };
  }

  private generateAnalyticsConfig(
    campaign: Campaign,
    options: AchievementGenerationOptions
  ): AchievementAnalyticsConfig {
    return {
      track_unlock_events: true,
      track_progress_events: true,
      track_attempt_events: false,
      funnel_analysis: true,
      difficulty_analysis: true,
      completion_time_analysis: true,
      custom_events: [
        {
          name: 'achievement_milestone',
          description: 'Track major achievement milestones',
          parameters: ['achievement_id', 'category', 'progress'],
          frequency: 'milestone'
        },
        {
          name: 'achievement_unlock_failed',
          description: 'Track failed achievement attempts',
          parameters: ['achievement_id', 'reason'],
          frequency: 'always'
        }
      ]
    };
  }

  async exportAchievementSystem(
    achievementSystem: AchievementSystem,
    outputPath: string,
    options: AchievementExportOptions
  ): Promise<void> {
    this.emit('export:started', { format: options.format, outputPath });

    switch (options.format) {
      case 'json':
        await this.exportAsJSON(achievementSystem, outputPath, options);
        break;
      case 'xml':
        await this.exportAsXML(achievementSystem, outputPath, options);
        break;
      case 'yaml':
        await this.exportAsYAML(achievementSystem, outputPath, options);
        break;
      case 'csv':
        await this.exportAsCSV(achievementSystem, outputPath, options);
        break;
      case 'steam':
        await this.exportForSteam(achievementSystem, outputPath, options);
        break;
      case 'unity':
        await this.exportForUnity(achievementSystem, outputPath, options);
        break;
      case 'godot':
        await this.exportForGodot(achievementSystem, outputPath, options);
        break;
      case 'unreal':
        await this.exportForUnreal(achievementSystem, outputPath, options);
        break;
    }

    this.emit('export:completed', { format: options.format, outputPath });
  }

  // Helper methods
  private initializeTemplates(): void {
    // Initialize achievement templates and patterns
  }

  private initializeBalanceData(): void {
    // Initialize balance and progression data
  }

  private createDefaultMetadata(
    designNotes: string,
    difficulty: number,
    estimatedTime: number,
    completionPercentage: number
  ): AchievementMetadata {
    return {
      created_date: new Date(),
      difficulty_rating: difficulty,
      estimated_completion_time: estimatedTime,
      completion_percentage: completionPercentage,
      design_notes: designNotes,
      balance_notes: 'Standard achievement balance',
      testing_notes: 'Requires testing with full gameplay',
      version_added: '1.0.0',
      tags: []
    };
  }

  private createDefaultTracking(metric: string, format: 'count' | 'time' | 'percentage' | 'fraction'): AchievementTracking {
    return {
      track_progress: format !== 'count',
      progress_text: `{current}/${format === 'percentage' ? '100%' : '{target}'}`,
      progress_format: format,
      milestone_notifications: false,
      analytics_events: [`${metric}_progress`],
      debug_logging: false
    };
  }

  private createProgressiveTracking(metric: string, target: number, format: 'count' | 'time' | 'percentage' | 'fraction'): AchievementTracking {
    return {
      track_progress: true,
      progress_text: `Progress: {current}/${format === 'percentage' ? '100%' : target}`,
      progress_format: format,
      milestone_notifications: true,
      analytics_events: [`${metric}_milestone`],
      debug_logging: false
    };
  }

  private async exportAsJSON(system: AchievementSystem, outputPath: string, options: AchievementExportOptions): Promise<void> {
    const data = options.minified ? system : system;
    await fs.writeJSON(outputPath, data, { spaces: options.minified ? 0 : 2 });
  }

  private async exportAsXML(system: AchievementSystem, outputPath: string, options: AchievementExportOptions): Promise<void> {
    // XML export implementation would go here
    console.log('XML export not fully implemented yet');
  }

  private async exportAsYAML(system: AchievementSystem, outputPath: string, options: AchievementExportOptions): Promise<void> {
    // YAML export implementation would go here
    console.log('YAML export not fully implemented yet');
  }

  private async exportAsCSV(system: AchievementSystem, outputPath: string, options: AchievementExportOptions): Promise<void> {
    const headers = ['ID', 'Name', 'Description', 'Category', 'Type', 'Rarity', 'Points', 'Hidden'];
    const rows = [headers.join(',')];
    
    system.achievements.forEach(achievement => {
      const row = [
        achievement.id,
        `"${achievement.name}"`,
        `"${achievement.description}"`,
        achievement.category,
        achievement.type,
        achievement.rarity,
        achievement.points.toString(),
        achievement.hidden.toString()
      ];
      rows.push(row.join(','));
    });

    await fs.writeFile(outputPath, rows.join('\n'));
  }

  private async exportForSteam(system: AchievementSystem, outputPath: string, options: AchievementExportOptions): Promise<void> {
    const steamAchievements = system.achievements.map(achievement => ({
      name: achievement.id,
      displayName: achievement.name,
      description: achievement.description,
      icon: achievement.icon,
      hidden: achievement.hidden ? 1 : 0
    }));

    await fs.writeJSON(outputPath, { achievements: steamAchievements }, { spaces: 2 });
  }

  private async exportForUnity(system: AchievementSystem, outputPath: string, options: AchievementExportOptions): Promise<void> {
    // Generate Unity-compatible achievement data and scripts
    const unityData = {
      achievementSystem: system,
      scriptTemplate: this.generateUnityAchievementScript(system)
    };

    await fs.writeJSON(outputPath, unityData, { spaces: 2 });
  }

  private async exportForGodot(system: AchievementSystem, outputPath: string, options: AchievementExportOptions): Promise<void> {
    // Generate Godot-compatible achievement resource and script
    const godotScript = this.generateGodotAchievementScript(system);
    await fs.writeFile(outputPath, godotScript);
  }

  private async exportForUnreal(system: AchievementSystem, outputPath: string, options: AchievementExportOptions): Promise<void> {
    // Generate Unreal-compatible achievement data
    const unrealData = {
      achievementSystem: system,
      blueprintData: this.generateUnrealAchievementBlueprint(system)
    };

    await fs.writeJSON(outputPath, unrealData, { spaces: 2 });
  }

  private generateUnityAchievementScript(system: AchievementSystem): string {
    return `// Generated Achievement System for Unity
using UnityEngine;
using System.Collections.Generic;

[System.Serializable]
public class Achievement
{
    public string id;
    public string name;
    public string description;
    public string category;
    public bool unlocked = false;
    public float progress = 0f;
}

public class AchievementManager : MonoBehaviour
{
    [SerializeField]
    private List<Achievement> achievements = new List<Achievement>();
    
    public static AchievementManager Instance { get; private set; }
    
    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
            InitializeAchievements();
        }
        else
        {
            Destroy(gameObject);
        }
    }
    
    private void InitializeAchievements()
    {
        // Initialize ${system.achievements.length} achievements
        ${system.achievements.map(a => `achievements.Add(new Achievement { id = "${a.id}", name = "${a.name}", description = "${a.description}", category = "${a.category}" });`).join('\n        ')}
    }
    
    public void UnlockAchievement(string achievementId)
    {
        Achievement achievement = achievements.Find(a => a.id == achievementId);
        if (achievement != null && !achievement.unlocked)
        {
            achievement.unlocked = true;
            Debug.Log("Achievement Unlocked: " + achievement.name);
            // Trigger UI notification
        }
    }
}`;
  }

  private generateGodotAchievementScript(system: AchievementSystem): string {
    return `# Generated Achievement System for Godot
extends Node

signal achievement_unlocked(achievement_id)

var achievements = {}
var unlocked_achievements = []

func _ready():
    initialize_achievements()

func initialize_achievements():
    ${system.achievements.map(a => `achievements["${a.id}"] = {
        "name": "${a.name}",
        "description": "${a.description}",
        "category": "${a.category}",
        "unlocked": false,
        "progress": 0.0
    }`).join('\n    ')}

func unlock_achievement(achievement_id: String):
    if achievements.has(achievement_id) and not achievements[achievement_id]["unlocked"]:
        achievements[achievement_id]["unlocked"] = true
        unlocked_achievements.append(achievement_id)
        emit_signal("achievement_unlocked", achievement_id)
        print("Achievement Unlocked: ", achievements[achievement_id]["name"])

func get_achievement_progress(achievement_id: String) -> float:
    if achievements.has(achievement_id):
        return achievements[achievement_id]["progress"]
    return 0.0

func set_achievement_progress(achievement_id: String, progress: float):
    if achievements.has(achievement_id):
        achievements[achievement_id]["progress"] = progress
        if progress >= 1.0:
            unlock_achievement(achievement_id)`;
  }

  private generateUnrealAchievementBlueprint(system: AchievementSystem): any {
    return {
      achievementNodes: system.achievements.map(achievement => ({
        id: achievement.id,
        name: achievement.name,
        description: achievement.description,
        blueprintNode: `Achievement_${achievement.id}`,
        conditions: achievement.conditions
      })),
      managerBlueprint: 'BP_AchievementManager',
      eventSystem: 'Achievement Event Dispatcher'
    };
  }
}