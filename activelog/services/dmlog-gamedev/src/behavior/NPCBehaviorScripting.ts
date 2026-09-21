import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as yaml from 'js-yaml';
import {
  Campaign,
  NPC,
  NPCBehavior,
  BehaviorNode,
  BehaviorTree,
  NPCState,
  StateTransition,
  ReactionTrigger,
  InteractionType,
  PathfindingData,
  CombatBehavior
} from '../types';

export interface BehaviorScriptingOptions {
  complexity: 'simple' | 'moderate' | 'complex';
  includePathfinding: boolean;
  includeCombatBehavior: boolean;
  includeEmotionalResponses: boolean;
  includeMemory: boolean;
  includeSchedules: boolean;
  generateVisualScripting: boolean;
  format: 'json' | 'yaml' | 'xml' | 'lua' | 'cs' | 'gd' | 'visual' | 'bt';
}

export interface AIPersonality {
  traits: PersonalityTraits;
  preferences: NPCPreferences;
  reactions: EmotionalReactions;
  memory: MemorySystem;
  relationships: RelationshipSystem;
}

export interface PersonalityTraits {
  openness: number; // 0-100
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
  intelligence: number;
  aggression: number;
  curiosity: number;
  loyalty: number;
  humor: number;
}

export interface NPCPreferences {
  topics: TopicPreference[];
  activities: ActivityPreference[];
  locations: LocationPreference[];
  items: ItemPreference[];
  weather: WeatherPreference;
  timeOfDay: TimePreference;
}

export interface TopicPreference {
  topic: string;
  interest: number; // -100 to 100
  knowledge: number; // 0-100
  willingness: number; // 0-100 (willingness to discuss)
}

export interface ActivityPreference {
  activity: string;
  enjoyment: number; // -100 to 100
  frequency: 'never' | 'rarely' | 'sometimes' | 'often' | 'always';
  conditions: string[];
}

export interface LocationPreference {
  location: string;
  comfort: number; // -100 to 100
  familiarity: number; // 0-100
  avoidance: boolean;
}

export interface ItemPreference {
  item: string;
  desire: number; // -100 to 100
  value: number; // How much they value it
  willing_to_trade: boolean;
}

export interface WeatherPreference {
  sunny: number;
  rainy: number;
  cloudy: number;
  stormy: number;
  snowy: number;
}

export interface TimePreference {
  morning: number; // -100 to 100
  afternoon: number;
  evening: number;
  night: number;
}

export interface EmotionalReactions {
  triggers: EmotionalTrigger[];
  expressions: EmotionalExpression[];
  recovery: EmotionalRecovery;
  contagion: EmotionalContagion;
}

export interface EmotionalTrigger {
  stimulus: string;
  emotion: string;
  intensity: number; // 0-100
  duration: number; // seconds
  conditions: string[];
}

export interface EmotionalExpression {
  emotion: string;
  verbal: string[];
  nonverbal: string[];
  behavioral: string[];
  physiological: string[];
}

export interface EmotionalRecovery {
  baseRecoveryRate: number; // points per second
  factors: RecoveryFactor[];
  activities: RecoveryActivity[];
}

export interface RecoveryFactor {
  condition: string;
  modifier: number;
  description: string;
}

export interface RecoveryActivity {
  activity: string;
  recovery_bonus: number;
  requirements: string[];
}

export interface EmotionalContagion {
  susceptibility: number; // 0-100
  influence: number; // 0-100 (how much they influence others)
  emotions: string[];
}

export interface MemorySystem {
  shortTerm: MemoryConfiguration;
  longTerm: MemoryConfiguration;
  events: EventMemory[];
  relationships: RelationshipMemory[];
  locations: LocationMemory[];
  items: ItemMemory[];
}

export interface MemoryConfiguration {
  capacity: number;
  duration: number; // seconds
  decay_rate: number;
  importance_threshold: number;
}

export interface EventMemory {
  id: string;
  description: string;
  participants: string[];
  location: string;
  timestamp: Date;
  importance: number;
  emotional_impact: number;
  tags: string[];
}

export interface RelationshipMemory {
  target: string;
  interactions: InteractionMemory[];
  sentiment: number; // -100 to 100
  trust: number; // 0-100
  last_seen: Date;
  context: string[];
}

export interface InteractionMemory {
  type: string;
  outcome: string;
  emotional_impact: number;
  timestamp: Date;
}

export interface LocationMemory {
  location: string;
  visits: number;
  experiences: LocationExperience[];
  safety: number; // -100 to 100
  comfort: number; // -100 to 100
}

export interface LocationExperience {
  description: string;
  timestamp: Date;
  emotional_impact: number;
  companions: string[];
}

export interface ItemMemory {
  item: string;
  encounters: ItemEncounter[];
  associations: ItemAssociation[];
  value_estimate: number;
}

export interface ItemEncounter {
  context: string;
  location: string;
  timestamp: Date;
  outcome: string;
}

export interface ItemAssociation {
  target: string; // person, place, or concept
  strength: number; // -100 to 100
  context: string;
}

export interface RelationshipSystem {
  dynamics: RelationshipDynamic[];
  tracking: RelationshipTracking;
  development: RelationshipDevelopment;
}

export interface RelationshipDynamic {
  target: string;
  relationship_type: string;
  strength: number; // -100 to 100
  stability: number; // 0-100
  history: RelationshipHistory[];
  influences: RelationshipInfluence[];
}

export interface RelationshipHistory {
  event: string;
  impact: number;
  timestamp: Date;
  context: string;
}

export interface RelationshipInfluence {
  factor: string;
  weight: number;
  description: string;
}

export interface RelationshipTracking {
  update_frequency: number; // seconds
  factors: TrackingFactor[];
  memory_integration: boolean;
}

export interface TrackingFactor {
  name: string;
  impact: number;
  conditions: string[];
}

export interface RelationshipDevelopment {
  stages: DevelopmentStage[];
  milestones: RelationshipMilestone[];
  barriers: RelationshipBarrier[];
}

export interface DevelopmentStage {
  name: string;
  threshold: number;
  characteristics: string[];
  unlocks: string[];
}

export interface RelationshipMilestone {
  name: string;
  requirements: string[];
  effects: string[];
  dialogue_changes: string[];
}

export interface RelationshipBarrier {
  name: string;
  condition: string;
  impact: string;
  resolution: string[];
}

export interface AdvancedBehaviorTree {
  nodes: BehaviorTreeNode[];
  blackboard: BlackboardVariable[];
  services: BehaviorService[];
  decorators: BehaviorDecorator[];
  composites: BehaviorComposite[];
}

export interface BehaviorTreeNode {
  id: string;
  type: 'composite' | 'decorator' | 'task' | 'condition';
  name: string;
  description: string;
  parent?: string;
  children: string[];
  properties: Record<string, any>;
  position: { x: number; y: number };
  status: 'success' | 'failure' | 'running' | 'aborted';
}

export interface BlackboardVariable {
  name: string;
  type: 'boolean' | 'integer' | 'float' | 'string' | 'vector' | 'object';
  value: any;
  scope: 'tree' | 'subtree' | 'global';
  persistence: 'session' | 'permanent' | 'temporary';
}

export interface BehaviorService {
  id: string;
  name: string;
  interval: number; // seconds
  node_scope: string;
  actions: ServiceAction[];
}

export interface ServiceAction {
  type: string;
  parameters: Record<string, any>;
  conditions: string[];
}

export interface BehaviorDecorator {
  id: string;
  name: string;
  type: 'cooldown' | 'repeat' | 'blackboard' | 'force_success' | 'force_failure' | 'inverter';
  properties: Record<string, any>;
}

export interface BehaviorComposite {
  id: string;
  name: string;
  type: 'selector' | 'sequence' | 'parallel' | 'random';
  properties: Record<string, any>;
}

export class NPCBehaviorScripting extends EventEmitter {
  private outputPath: string;
  private behaviorTrees: Map<string, AdvancedBehaviorTree> = new Map();
  private personalities: Map<string, AIPersonality> = new Map();

  constructor(outputPath: string) {
    super();
    this.outputPath = outputPath;
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.outputPath, { recursive: true });
      console.log('🤖 NPC behavior scripting initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing NPC behavior scripting:', error);
      throw error;
    }
  }

  public async generateNPCBehaviors(
    campaign: Campaign,
    options: BehaviorScriptingOptions
  ): Promise<NPCBehavior[]> {
    console.log(`🤖 Generating NPC behaviors for campaign: ${campaign.name}`);

    const behaviors: NPCBehavior[] = [];

    for (const npc of campaign.npcs) {
      try {
        const behavior = await this.generateNPCBehavior(npc, campaign, options);
        behaviors.push(behavior);

        // Generate advanced behavior tree if requested
        if (options.complexity !== 'simple') {
          const advancedTree = await this.generateAdvancedBehaviorTree(npc, behavior, options);
          this.behaviorTrees.set(npc.id, advancedTree);
        }

        // Generate AI personality if requested
        if (options.includeEmotionalResponses || options.includeMemory) {
          const personality = await this.generateAIPersonality(npc, campaign, options);
          this.personalities.set(npc.id, personality);
        }

        console.log(`✅ Generated behavior for: ${npc.name}`);
      } catch (error) {
        console.error(`Error processing NPC ${npc.name}:`, error);
      }
    }

    // Export all behaviors
    await this.exportBehaviors(behaviors, campaign, options);

    console.log(`✅ Generated ${behaviors.length} NPC behaviors`);
    this.emit('behaviors-generated', { count: behaviors.length });

    return behaviors;
  }

  private async generateNPCBehavior(
    npc: NPC,
    campaign: Campaign,
    options: BehaviorScriptingOptions
  ): Promise<NPCBehavior> {
    // Create behavior tree
    const behaviorTree = await this.createBehaviorTree(npc, campaign, options);

    // Generate states
    const states = this.generateNPCStates(npc, options);

    // Create state transitions
    const transitions = this.generateStateTransitions(npc, states, options);

    // Generate reaction triggers
    const reactions = this.generateReactionTriggers(npc, campaign, options);

    // Define interaction types
    const interactions = this.generateInteractionTypes(npc, campaign);

    // Generate pathfinding data if requested
    const pathfinding = options.includePathfinding 
      ? this.generatePathfindingData(npc, campaign)
      : this.createBasicPathfinding();

    // Generate combat behavior if requested
    const combat = options.includeCombatBehavior
      ? this.generateCombatBehavior(npc, campaign)
      : this.createBasicCombatBehavior();

    return {
      id: `behavior_${npc.id}`,
      npcId: npc.id,
      behaviorTree,
      states,
      transitions,
      reactions,
      interactions,
      pathfinding,
      combat
    };
  }

  private async createBehaviorTree(
    npc: NPC,
    campaign: Campaign,
    options: BehaviorScriptingOptions
  ): Promise<BehaviorNode> {
    const complexity = options.complexity;
    
    // Create root behavior node
    const rootNode: BehaviorNode = {
      id: `${npc.id}_root`,
      type: 'selector',
      name: 'NPC Root Behavior',
      children: [],
      parameters: {
        npc_id: npc.id,
        role: npc.role
      },
      priority: 1
    };

    // Add child behaviors based on NPC role and complexity
    const childBehaviors = await this.generateChildBehaviors(npc, campaign, complexity);
    rootNode.children = childBehaviors;

    return rootNode;
  }

  private async generateChildBehaviors(
    npc: NPC,
    campaign: Campaign,
    complexity: string
  ): Promise<BehaviorNode[]> {
    const behaviors: BehaviorNode[] = [];

    // Emergency behaviors (highest priority)
    behaviors.push(this.createEmergencyBehavior(npc));

    // Role-specific behaviors
    switch (npc.role) {
      case 'quest_giver':
        behaviors.push(...this.createQuestGiverBehaviors(npc, campaign));
        break;
      case 'merchant':
        behaviors.push(...this.createMerchantBehaviors(npc, campaign));
        break;
      case 'guard':
        behaviors.push(...this.createGuardBehaviors(npc, campaign));
        break;
      case 'companion':
        behaviors.push(...this.createCompanionBehaviors(npc, campaign));
        break;
      default:
        behaviors.push(...this.createGenericBehaviors(npc, campaign));
    }

    // Social behaviors
    if (complexity !== 'simple') {
      behaviors.push(this.createSocialBehavior(npc));
    }

    // Idle behaviors (lowest priority)
    behaviors.push(this.createIdleBehavior(npc));

    return behaviors;
  }

  private createEmergencyBehavior(npc: NPC): BehaviorNode {
    return {
      id: `${npc.id}_emergency`,
      type: 'selector',
      name: 'Emergency Response',
      children: [
        {
          id: `${npc.id}_flee_danger`,
          type: 'action',
          name: 'Flee from Danger',
          children: [],
          parameters: {
            condition: 'health < 0.3 || threat_level > 8',
            action: 'flee',
            target: 'safe_location'
          },
          priority: 10
        },
        {
          id: `${npc.id}_call_help`,
          type: 'action',
          name: 'Call for Help',
          children: [],
          parameters: {
            condition: 'threat_level > 5',
            action: 'shout',
            message: 'Help! Someone help me!'
          },
          priority: 9
        }
      ],
      parameters: {},
      priority: 10
    };
  }

  private createQuestGiverBehaviors(npc: NPC, campaign: Campaign): BehaviorNode[] {
    const behaviors: BehaviorNode[] = [];

    // Check for players needing quests
    behaviors.push({
      id: `${npc.id}_offer_quest`,
      type: 'sequence',
      name: 'Offer Quest',
      children: [
        {
          id: `${npc.id}_check_quest_available`,
          type: 'condition',
          name: 'Check Quest Available',
          children: [],
          parameters: {
            condition: 'has_available_quest && player_qualified'
          },
          priority: 1
        },
        {
          id: `${npc.id}_approach_player`,
          type: 'action',
          name: 'Approach Player',
          children: [],
          parameters: {
            action: 'move_to_target',
            target: 'nearest_player',
            distance: 3
          },
          priority: 1
        },
        {
          id: `${npc.id}_initiate_quest_dialogue`,
          type: 'action',
          name: 'Start Quest Dialogue',
          children: [],
          parameters: {
            action: 'start_dialogue',
            dialogue_tree: `${npc.id}_quest_offer`
          },
          priority: 1
        }
      ],
      parameters: {},
      priority: 8
    });

    // Check quest progress
    behaviors.push({
      id: `${npc.id}_check_progress`,
      type: 'sequence',
      name: 'Check Quest Progress',
      children: [
        {
          id: `${npc.id}_recognize_player`,
          type: 'condition',
          name: 'Recognize Player',
          children: [],
          parameters: {
            condition: 'player_has_active_quest_from_me'
          },
          priority: 1
        },
        {
          id: `${npc.id}_progress_dialogue`,
          type: 'action',
          name: 'Progress Dialogue',
          children: [],
          parameters: {
            action: 'start_dialogue',
            dialogue_tree: `${npc.id}_quest_progress`
          },
          priority: 1
        }
      ],
      parameters: {},
      priority: 7
    });

    return behaviors;
  }

  private createMerchantBehaviors(npc: NPC, campaign: Campaign): BehaviorNode[] {
    return [
      {
        id: `${npc.id}_manage_shop`,
        type: 'sequence',
        name: 'Manage Shop',
        children: [
          {
            id: `${npc.id}_greet_customer`,
            type: 'action',
            name: 'Greet Customer',
            children: [],
            parameters: {
              condition: 'player_nearby && !in_conversation',
              action: 'start_dialogue',
              dialogue_tree: `${npc.id}_merchant_greeting`
            },
            priority: 1
          },
          {
            id: `${npc.id}_show_wares`,
            type: 'action',
            name: 'Show Wares',
            children: [],
            parameters: {
              action: 'open_shop_interface'
            },
            priority: 1
          }
        ],
        parameters: {},
        priority: 6
      },
      {
        id: `${npc.id}_restock_items`,
        type: 'action',
        name: 'Restock Items',
        children: [],
        parameters: {
          condition: 'time_of_day == "morning" && !shop_full',
          action: 'restock_inventory',
          frequency: 'daily'
        },
        priority: 3
      }
    ];
  }

  private createGuardBehaviors(npc: NPC, campaign: Campaign): BehaviorNode[] {
    return [
      {
        id: `${npc.id}_patrol`,
        type: 'sequence',
        name: 'Patrol Route',
        children: [
          {
            id: `${npc.id}_check_route`,
            type: 'condition',
            name: 'Check Patrol Route',
            children: [],
            parameters: {
              condition: 'on_duty && !threat_detected'
            },
            priority: 1
          },
          {
            id: `${npc.id}_walk_patrol`,
            type: 'action',
            name: 'Walk Patrol',
            children: [],
            parameters: {
              action: 'follow_path',
              path: `${npc.id}_patrol_route`,
              speed: 'walk'
            },
            priority: 1
          }
        ],
        parameters: {},
        priority: 5
      },
      {
        id: `${npc.id}_investigate_disturbance`,
        type: 'sequence',
        name: 'Investigate Disturbance',
        children: [
          {
            id: `${npc.id}_detect_threat`,
            type: 'condition',
            name: 'Detect Threat',
            children: [],
            parameters: {
              condition: 'threat_level > 2'
            },
            priority: 1
          },
          {
            id: `${npc.id}_move_to_threat`,
            type: 'action',
            name: 'Move to Threat',
            children: [],
            parameters: {
              action: 'move_to_target',
              target: 'threat_location',
              speed: 'run'
            },
            priority: 1
          },
          {
            id: `${npc.id}_confront_threat`,
            type: 'action',
            name: 'Confront Threat',
            children: [],
            parameters: {
              action: 'start_dialogue',
              dialogue_tree: `${npc.id}_challenge`
            },
            priority: 1
          }
        ],
        parameters: {},
        priority: 8
      }
    ];
  }

  private createCompanionBehaviors(npc: NPC, campaign: Campaign): BehaviorNode[] {
    return [
      {
        id: `${npc.id}_follow_leader`,
        type: 'action',
        name: 'Follow Leader',
        children: [],
        parameters: {
          condition: 'has_leader && leader_moving',
          action: 'follow_target',
          target: 'leader',
          distance: 2
        },
        priority: 7
      },
      {
        id: `${npc.id}_assist_combat`,
        type: 'sequence',
        name: 'Assist in Combat',
        children: [
          {
            id: `${npc.id}_detect_combat`,
            type: 'condition',
            name: 'Detect Combat',
            children: [],
            parameters: {
              condition: 'leader_in_combat || allies_in_combat'
            },
            priority: 1
          },
          {
            id: `${npc.id}_engage_enemy`,
            type: 'action',
            name: 'Engage Enemy',
            children: [],
            parameters: {
              action: 'enter_combat',
              target: 'nearest_enemy'
            },
            priority: 1
          }
        ],
        parameters: {},
        priority: 9
      },
      {
        id: `${npc.id}_provide_advice`,
        type: 'action',
        name: 'Provide Advice',
        children: [],
        parameters: {
          condition: 'leader_needs_advice && relationship > 50',
          action: 'start_dialogue',
          dialogue_tree: `${npc.id}_advice`
        },
        priority: 4
      }
    ];
  }

  private createGenericBehaviors(npc: NPC, campaign: Campaign): BehaviorNode[] {
    return [
      {
        id: `${npc.id}_respond_to_player`,
        type: 'sequence',
        name: 'Respond to Player',
        children: [
          {
            id: `${npc.id}_player_interaction`,
            type: 'condition',
            name: 'Player Wants to Interact',
            children: [],
            parameters: {
              condition: 'player_initiated_interaction'
            },
            priority: 1
          },
          {
            id: `${npc.id}_general_dialogue`,
            type: 'action',
            name: 'General Dialogue',
            children: [],
            parameters: {
              action: 'start_dialogue',
              dialogue_tree: `${npc.id}_general`
            },
            priority: 1
          }
        ],
        parameters: {},
        priority: 6
      }
    ];
  }

  private createSocialBehavior(npc: NPC): BehaviorNode {
    return {
      id: `${npc.id}_social`,
      type: 'selector',
      name: 'Social Behavior',
      children: [
        {
          id: `${npc.id}_greet_friends`,
          type: 'action',
          name: 'Greet Friends',
          children: [],
          parameters: {
            condition: 'nearby_friends && !already_greeted',
            action: 'wave_at_target',
            target: 'nearest_friend'
          },
          priority: 1
        },
        {
          id: `${npc.id}_avoid_enemies`,
          type: 'action',
          name: 'Avoid Enemies',
          children: [],
          parameters: {
            condition: 'nearby_enemies',
            action: 'move_away_from_target',
            target: 'nearest_enemy'
          },
          priority: 1
        },
        {
          id: `${npc.id}_chat_with_npcs`,
          type: 'action',
          name: 'Chat with Other NPCs',
          children: [],
          parameters: {
            condition: 'nearby_friendly_npcs && bored',
            action: 'start_npc_conversation',
            target: 'nearest_friendly_npc'
          },
          priority: 1
        }
      ],
      parameters: {},
      priority: 3
    };
  }

  private createIdleBehavior(npc: NPC): BehaviorNode {
    const idleActivities = this.generateIdleActivities(npc);
    
    return {
      id: `${npc.id}_idle`,
      type: 'selector',
      name: 'Idle Behavior',
      children: idleActivities,
      parameters: {},
      priority: 1
    };
  }

  private generateIdleActivities(npc: NPC): BehaviorNode[] {
    const activities: BehaviorNode[] = [];
    
    // Role-based idle activities
    switch (npc.role) {
      case 'merchant':
        activities.push({
          id: `${npc.id}_organize_wares`,
          type: 'action',
          name: 'Organize Wares',
          children: [],
          parameters: {
            action: 'play_animation',
            animation: 'organizing'
          },
          priority: 1
        });
        break;
        
      case 'guard':
        activities.push({
          id: `${npc.id}_stand_watch`,
          type: 'action',
          name: 'Stand Watch',
          children: [],
          parameters: {
            action: 'look_around',
            duration: 5
          },
          priority: 1
        });
        break;
        
      default:
        activities.push({
          id: `${npc.id}_wander`,
          type: 'action',
          name: 'Wander Around',
          children: [],
          parameters: {
            action: 'random_walk',
            radius: 10
          },
          priority: 1
        });
    }
    
    // Personality-based activities
    if (npc.personality.traits.includes('curious')) {
      activities.push({
        id: `${npc.id}_examine_objects`,
        type: 'action',
        name: 'Examine Objects',
        children: [],
        parameters: {
          action: 'look_at_nearest_object',
          duration: 3
        },
        priority: 1
      });
    }
    
    if (npc.personality.traits.includes('restless')) {
      activities.push({
        id: `${npc.id}_pace`,
        type: 'action',
        name: 'Pace Back and Forth',
        children: [],
        parameters: {
          action: 'pace',
          distance: 5
        },
        priority: 1
      });
    }
    
    return activities;
  }

  private generateNPCStates(npc: NPC, options: BehaviorScriptingOptions): NPCState[] {
    const states: NPCState[] = [];
    
    // Basic states
    states.push(
      {
        id: 'idle',
        name: 'Idle',
        description: 'NPC is not engaged in any specific activity',
        behaviors: ['wander', 'look_around', 'idle_animation'],
        transitions: ['player_approach', 'threat_detected', 'schedule_change'],
        variables: { alertness: 0.1, energy: 1.0 }
      },
      {
        id: 'alert',
        name: 'Alert',
        description: 'NPC is aware of something interesting',
        behaviors: ['investigate', 'focus_attention'],
        transitions: ['threat_detected', 'return_to_idle', 'start_interaction'],
        variables: { alertness: 0.7, energy: 0.9 }
      },
      {
        id: 'conversing',
        name: 'In Conversation',
        description: 'NPC is talking with someone',
        behaviors: ['dialogue', 'face_target', 'gesture'],
        transitions: ['conversation_end', 'interrupted'],
        variables: { alertness: 0.6, energy: 0.8 }
      }
    );
    
    // Role-specific states
    switch (npc.role) {
      case 'merchant':
        states.push(
          {
            id: 'selling',
            name: 'Selling Items',
            description: 'NPC is in merchant mode',
            behaviors: ['show_wares', 'negotiate', 'transaction'],
            transitions: ['customer_leaves', 'shop_closes'],
            variables: { business_mode: true, alertness: 0.8 }
          },
          {
            id: 'restocking',
            name: 'Restocking Inventory',
            description: 'NPC is managing inventory',
            behaviors: ['organize_items', 'check_stock'],
            transitions: ['shop_opens', 'customer_arrives'],
            variables: { busy: true, alertness: 0.3 }
          }
        );
        break;
        
      case 'guard':
        states.push(
          {
            id: 'patrolling',
            name: 'On Patrol',
            description: 'NPC is patrolling their assigned route',
            behaviors: ['follow_patrol_route', 'scan_for_threats'],
            transitions: ['threat_detected', 'shift_end'],
            variables: { on_duty: true, alertness: 0.9 }
          },
          {
            id: 'investigating',
            name: 'Investigating',
            description: 'NPC is investigating a disturbance',
            behaviors: ['search_area', 'question_witnesses'],
            transitions: ['threat_found', 'investigation_complete'],
            variables: { investigating: true, alertness: 1.0 }
          }
        );
        break;
        
      case 'companion':
        states.push(
          {
            id: 'following',
            name: 'Following Leader',
            description: 'NPC is following their leader',
            behaviors: ['maintain_formation', 'watch_for_threats'],
            transitions: ['combat_starts', 'leader_stops'],
            variables: { following: true, alertness: 0.7 }
          },
          {
            id: 'assisting',
            name: 'Assisting',
            description: 'NPC is actively helping',
            behaviors: ['provide_support', 'coordinate_actions'],
            transitions: ['assistance_complete', 'new_priority'],
            variables: { assisting: true, alertness: 0.8 }
          }
        );
        break;
    }
    
    // Emotional states if requested
    if (options.includeEmotionalResponses) {
      states.push(
        {
          id: 'happy',
          name: 'Happy',
          description: 'NPC is in a positive emotional state',
          behaviors: ['smile', 'positive_dialogue', 'helpful_actions'],
          transitions: ['negative_event', 'time_decay'],
          variables: { mood: 0.8, sociability: 1.2 }
        },
        {
          id: 'angry',
          name: 'Angry',
          description: 'NPC is upset or hostile',
          behaviors: ['aggressive_posture', 'harsh_dialogue', 'avoid_player'],
          transitions: ['calm_down', 'escalate'],
          variables: { mood: -0.8, aggression: 1.5 }
        },
        {
          id: 'fearful',
          name: 'Fearful',
          description: 'NPC is afraid or anxious',
          behaviors: ['defensive_posture', 'nervous_dialogue', 'seek_safety'],
          transitions: ['threat_passes', 'find_safety'],
          variables: { mood: -0.6, alertness: 1.3, flee_threshold: 0.3 }
        }
      );
    }
    
    // Combat states if requested
    if (options.includeCombatBehavior) {
      states.push(
        {
          id: 'combat',
          name: 'In Combat',
          description: 'NPC is engaged in combat',
          behaviors: ['attack', 'defend', 'use_abilities'],
          transitions: ['combat_end', 'flee'],
          variables: { in_combat: true, alertness: 1.0, aggression: 1.0 }
        },
        {
          id: 'fleeing',
          name: 'Fleeing',
          description: 'NPC is trying to escape danger',
          behaviors: ['run_away', 'call_for_help', 'hide'],
          transitions: ['reach_safety', 'caught'],
          variables: { fleeing: true, panic: 0.9, speed: 1.5 }
        }
      );
    }
    
    return states;
  }

  private generateStateTransitions(
    npc: NPC,
    states: NPCState[],
    options: BehaviorScriptingOptions
  ): StateTransition[] {
    const transitions: StateTransition[] = [];
    
    // Basic transitions
    transitions.push(
      {
        id: 'idle_to_alert',
        from: 'idle',
        to: 'alert',
        condition: 'player_nearby || interesting_event',
        priority: 5,
        duration: 0,
        effects: ['increase_alertness']
      },
      {
        id: 'alert_to_conversing',
        from: 'alert',
        to: 'conversing',
        condition: 'player_initiated_dialogue',
        priority: 8,
        duration: 0,
        effects: ['face_player', 'start_dialogue']
      },
      {
        id: 'conversing_to_idle',
        from: 'conversing',
        to: 'idle',
        condition: 'dialogue_ended',
        priority: 3,
        duration: 1,
        effects: ['reset_alertness']
      }
    );
    
    // Role-specific transitions
    if (npc.role === 'merchant') {
      transitions.push(
        {
          id: 'idle_to_selling',
          from: 'idle',
          to: 'selling',
          condition: 'player_wants_to_trade',
          priority: 9,
          duration: 0,
          effects: ['open_shop_interface']
        },
        {
          id: 'selling_to_idle',
          from: 'selling',
          to: 'idle',
          condition: 'trade_complete || player_leaves',
          priority: 5,
          duration: 2,
          effects: ['close_shop_interface']
        }
      );
    }
    
    if (npc.role === 'guard') {
      transitions.push(
        {
          id: 'patrolling_to_investigating',
          from: 'patrolling',
          to: 'investigating',
          condition: 'disturbance_detected',
          priority: 10,
          duration: 0,
          effects: ['stop_patrol', 'move_to_disturbance']
        },
        {
          id: 'investigating_to_patrolling',
          from: 'investigating',
          to: 'patrolling',
          condition: 'investigation_complete',
          priority: 6,
          duration: 3,
          effects: ['resume_patrol']
        }
      );
    }
    
    // Emotional transitions if requested
    if (options.includeEmotionalResponses) {
      transitions.push(
        {
          id: 'any_to_happy',
          from: '*',
          to: 'happy',
          condition: 'positive_interaction || received_gift',
          priority: 7,
          duration: 0,
          effects: ['increase_mood', 'smile_animation']
        },
        {
          id: 'any_to_angry',
          from: '*',
          to: 'angry',
          condition: 'insulted || attacked || stolen_from',
          priority: 9,
          duration: 0,
          effects: ['decrease_mood', 'angry_animation']
        },
        {
          id: 'angry_to_idle',
          from: 'angry',
          to: 'idle',
          condition: 'time_passed > 60 && no_recent_negative_events',
          priority: 4,
          duration: 5,
          effects: ['calm_down_animation']
        }
      );
    }
    
    // Combat transitions if requested
    if (options.includeCombatBehavior) {
      transitions.push(
        {
          id: 'any_to_combat',
          from: '*',
          to: 'combat',
          condition: 'attacked || ally_attacked',
          priority: 10,
          duration: 0,
          effects: ['draw_weapon', 'face_enemy']
        },
        {
          id: 'combat_to_fleeing',
          from: 'combat',
          to: 'fleeing',
          condition: 'health < 25% || overwhelmed',
          priority: 9,
          duration: 0,
          effects: ['flee_animation', 'call_for_help']
        },
        {
          id: 'fleeing_to_idle',
          from: 'fleeing',
          to: 'idle',
          condition: 'reached_safety && no_immediate_threat',
          priority: 6,
          duration: 10,
          effects: ['catch_breath_animation']
        }
      );
    }
    
    return transitions;
  }

  private generateReactionTriggers(
    npc: NPC,
    campaign: Campaign,
    options: BehaviorScriptingOptions
  ): ReactionTrigger[] {
    const triggers: ReactionTrigger[] = [];
    
    // Basic reaction triggers
    triggers.push(
      {
        id: 'player_approach',
        event: 'player_enters_radius',
        condition: 'distance_to_player < 5',
        reaction: 'acknowledge_player',
        priority: 5,
        cooldown: 30
      },
      {
        id: 'greeting',
        event: 'player_greeting',
        condition: 'player_said_hello',
        reaction: 'respond_greeting',
        priority: 8,
        cooldown: 5
      },
      {
        id: 'insult',
        event: 'player_insult',
        condition: 'player_said_insult',
        reaction: 'become_angry',
        priority: 9,
        cooldown: 300
      }
    );
    
    // Personality-based reactions
    if (npc.personality.traits.includes('curious')) {
      triggers.push({
        id: 'new_item_interest',
        event: 'player_shows_item',
        condition: 'item_is_interesting',
        reaction: 'ask_about_item',
        priority: 6,
        cooldown: 60
      });
    }
    
    if (npc.personality.traits.includes('fearful')) {
      triggers.push({
        id: 'weapon_fear',
        event: 'player_draws_weapon',
        condition: 'weapon_is_threatening',
        reaction: 'cower_or_flee',
        priority: 10,
        cooldown: 0
      });
    }
    
    if (npc.personality.traits.includes('helpful')) {
      triggers.push({
        id: 'offer_assistance',
        event: 'player_looks_lost',
        condition: 'player_wandering_aimlessly',
        reaction: 'offer_directions',
        priority: 4,
        cooldown: 180
      });
    }
    
    // Role-specific reactions
    if (npc.role === 'merchant') {
      triggers.push({
        id: 'potential_customer',
        event: 'player_examines_goods',
        condition: 'player_looking_at_merchandise',
        reaction: 'sales_pitch',
        priority: 7,
        cooldown: 30
      });
    }
    
    if (npc.role === 'guard') {
      triggers.push(
        {
          id: 'suspicious_behavior',
          event: 'player_acting_suspicious',
          condition: 'player_sneaking || player_has_stolen_goods',
          reaction: 'investigate_player',
          priority: 9,
          cooldown: 0
        },
        {
          id: 'crime_witnessed',
          event: 'witnessed_crime',
          condition: 'saw_player_commit_crime',
          reaction: 'arrest_player',
          priority: 10,
          cooldown: 0
        }
      );
    }
    
    // Weather and time reactions if complex behavior
    if (options.complexity === 'complex') {
      triggers.push(
        {
          id: 'rain_reaction',
          event: 'weather_change',
          condition: 'weather == "rain"',
          reaction: 'seek_shelter',
          priority: 6,
          cooldown: 0
        },
        {
          id: 'night_reaction',
          event: 'time_change',
          condition: 'time_of_day == "night"',
          reaction: 'prepare_for_sleep',
          priority: 3,
          cooldown: 0
        }
      );
    }
    
    return triggers;
  }

  private generateInteractionTypes(npc: NPC, campaign: Campaign): InteractionType[] {
    const interactions: InteractionType[] = [];
    
    // Basic interactions
    interactions.push(
      {
        id: 'dialogue',
        name: 'Talk',
        description: 'Start a conversation',
        available: true,
        conditions: ['npc_not_busy', 'player_friendly'],
        effects: ['start_dialogue_tree'],
        icon: 'chat_bubble'
      },
      {
        id: 'examine',
        name: 'Look At',
        description: 'Get information about the NPC',
        available: true,
        conditions: [],
        effects: ['show_npc_info'],
        icon: 'magnifying_glass'
      }
    );
    
    // Role-specific interactions
    switch (npc.role) {
      case 'merchant':
        interactions.push(
          {
            id: 'trade',
            name: 'Trade',
            description: 'Buy or sell items',
            available: true,
            conditions: ['shop_open', 'has_money_or_items'],
            effects: ['open_trade_interface'],
            icon: 'coin'
          },
          {
            id: 'browse',
            name: 'Browse Wares',
            description: 'Look at available items',
            available: true,
            conditions: ['shop_open'],
            effects: ['show_merchant_inventory'],
            icon: 'bag'
          }
        );
        break;
        
      case 'quest_giver':
        interactions.push({
          id: 'ask_for_work',
          name: 'Ask for Work',
          description: 'Inquire about available quests',
          available: true,
          conditions: ['has_available_quest'],
          effects: ['show_quest_dialogue'],
          icon: 'scroll'
        });
        break;
        
      case 'companion':
        interactions.push(
          {
            id: 'follow_me',
            name: 'Follow Me',
            description: 'Ask companion to follow',
            available: true,
            conditions: ['not_already_following', 'good_relationship'],
            effects: ['start_following'],
            icon: 'footsteps'
          },
          {
            id: 'wait_here',
            name: 'Wait Here',
            description: 'Ask companion to stay in place',
            available: true,
            conditions: ['currently_following'],
            effects: ['stop_following'],
            icon: 'hand_stop'
          }
        );
        break;
    }
    
    // Personality-based interactions
    if (npc.personality.traits.includes('knowledgeable')) {
      interactions.push({
        id: 'ask_advice',
        name: 'Ask for Advice',
        description: 'Seek guidance or information',
        available: true,
        conditions: ['good_relationship'],
        effects: ['give_advice_dialogue'],
        icon: 'lightbulb'
      });
    }
    
    // Gift giving if complex behavior
    if (npc.personality.traits.includes('materialistic') || npc.personality.traits.includes('friendly')) {
      interactions.push({
        id: 'give_gift',
        name: 'Give Gift',
        description: 'Offer an item as a gift',
        available: true,
        conditions: ['has_suitable_item'],
        effects: ['accept_gift', 'improve_relationship'],
        icon: 'gift'
      });
    }
    
    return interactions;
  }

  private generatePathfindingData(npc: NPC, campaign: Campaign): PathfindingData {
    // Find NPC's location in campaign
    const npcLocation = campaign.locations.find(loc => loc.name === npc.location);
    
    return {
      homeLocation: npc.location,
      preferredPaths: this.generatePreferredPaths(npc, campaign),
      avoidedAreas: this.generateAvoidedAreas(npc, campaign),
      movementSpeed: this.calculateMovementSpeed(npc),
      navigationMesh: npcLocation?.levelDesign?.layout || 'default',
      pathfindingBehavior: {
        algorithm: 'a_star',
        heuristic: 'manhattan',
        smoothing: true,
        dynamic_obstacles: true
      }
    };
  }

  private generatePreferredPaths(npc: NPC, campaign: Campaign): any[] {
    const paths = [];
    
    // Add paths based on NPC schedule and role
    if (npc.role === 'guard') {
      paths.push({
        name: 'patrol_route',
        waypoints: this.generatePatrolWaypoints(npc, campaign),
        priority: 10
      });
    }
    
    if (npc.role === 'merchant') {
      paths.push({
        name: 'supply_route',
        waypoints: this.generateSupplyRoutes(npc, campaign),
        priority: 8
      });
    }
    
    return paths;
  }

  private generateAvoidedAreas(npc: NPC, campaign: Campaign): string[] {
    const avoidedAreas = [];
    
    // Add areas based on personality and relationships
    if (npc.personality.traits.includes('fearful')) {
      avoidedAreas.push('dark_alleys', 'dangerous_districts');
    }
    
    // Add areas with hostile NPCs
    const enemies = npc.relationships?.filter(rel => rel.type === 'enemy');
    enemies?.forEach(enemy => {
      const enemyNPC = campaign.npcs.find(n => n.id === enemy.targetId);
      if (enemyNPC) {
        avoidedAreas.push(enemyNPC.location);
      }
    });
    
    return avoidedAreas;
  }

  private calculateMovementSpeed(npc: NPC): any {
    let baseSpeed = 3.0; // meters per second
    
    // Modify based on personality
    if (npc.personality.traits.includes('energetic')) {
      baseSpeed *= 1.2;
    }
    if (npc.personality.traits.includes('lazy')) {
      baseSpeed *= 0.8;
    }
    
    return {
      walk: baseSpeed,
      run: baseSpeed * 2,
      sneak: baseSpeed * 0.5
    };
  }

  private createBasicPathfinding(): PathfindingData {
    return {
      homeLocation: 'default',
      preferredPaths: [],
      avoidedAreas: [],
      movementSpeed: { walk: 3.0, run: 6.0, sneak: 1.5 },
      navigationMesh: 'default',
      pathfindingBehavior: {
        algorithm: 'a_star',
        heuristic: 'euclidean',
        smoothing: false,
        dynamic_obstacles: false
      }
    };
  }

  private generateCombatBehavior(npc: NPC, campaign: Campaign): CombatBehavior {
    return {
      combatStyle: this.determineCombatStyle(npc),
      abilities: this.extractNPCAbilities(npc),
      tactics: this.generateCombatTactics(npc),
      threat_assessment: this.createThreatAssessment(npc),
      ai_difficulty: this.calculateAIDifficulty(npc)
    };
  }

  private determineCombatStyle(npc: NPC): string {
    // Determine combat style based on class, personality, and role
    if (npc.personality.traits.includes('aggressive')) {
      return 'aggressive';
    } else if (npc.personality.traits.includes('cautious')) {
      return 'defensive';
    } else if (npc.role === 'guard') {
      return 'tactical';
    }
    return 'balanced';
  }

  private extractNPCAbilities(npc: NPC): string[] {
    // Extract abilities from NPC data
    // This would be populated from the original D&D character data
    return ['basic_attack', 'defend'];
  }

  private generateCombatTactics(npc: NPC): any {
    return {
      opening_move: 'assess_threat',
      preferred_range: npc.role === 'guard' ? 'melee' : 'ranged',
      retreat_threshold: 0.3,
      aggression_level: npc.personality.traits.includes('aggressive') ? 0.8 : 0.5
    };
  }

  private createThreatAssessment(npc: NPC): any {
    return {
      factors: ['enemy_level', 'enemy_equipment', 'numerical_advantage'],
      weights: { player: 1.0, other_npcs: 0.7, monsters: 1.2 },
      reassessment_frequency: 5 // seconds
    };
  }

  private calculateAIDifficulty(npc: NPC): string {
    // Calculate AI difficulty based on NPC importance and level
    if (npc.role === 'enemy' || npc.role === 'guard') {
      return 'hard';
    } else if (npc.role === 'companion') {
      return 'medium';
    }
    return 'easy';
  }

  private createBasicCombatBehavior(): CombatBehavior {
    return {
      combatStyle: 'passive',
      abilities: ['flee'],
      tactics: { opening_move: 'flee', preferred_range: 'none', retreat_threshold: 1.0, aggression_level: 0.0 },
      threat_assessment: { factors: [], weights: {}, reassessment_frequency: 1 },
      ai_difficulty: 'easy'
    };
  }

  private async generateAdvancedBehaviorTree(
    npc: NPC,
    behavior: NPCBehavior,
    options: BehaviorScriptingOptions
  ): Promise<AdvancedBehaviorTree> {
    const nodes = await this.convertToAdvancedNodes(behavior.behaviorTree);
    const blackboard = this.generateBlackboardVariables(npc, behavior);
    const services = this.generateBehaviorServices(npc, options);
    const decorators = this.generateBehaviorDecorators(options);
    const composites = this.generateBehaviorComposites(options);
    
    return {
      nodes,
      blackboard,
      services,
      decorators,
      composites
    };
  }

  private async convertToAdvancedNodes(rootNode: BehaviorNode): Promise<BehaviorTreeNode[]> {
    const nodes: BehaviorTreeNode[] = [];
    
    const convertNode = (node: BehaviorNode, parent?: string, position = { x: 0, y: 0 }): void => {
      const advancedNode: BehaviorTreeNode = {
        id: node.id,
        type: this.mapNodeType(node.type),
        name: node.name || node.id,
        description: `${node.type} node for NPC behavior`,
        parent,
        children: node.children.map(child => typeof child === 'string' ? child : child.id),
        properties: node.parameters,
        position,
        status: 'success'
      };
      
      nodes.push(advancedNode);
      
      // Convert child nodes
      if (Array.isArray(node.children)) {
        node.children.forEach((child, index) => {
          if (typeof child !== 'string') {
            convertNode(child, node.id, {
              x: position.x + (index - node.children.length / 2) * 200,
              y: position.y + 150
            });
          }
        });
      }
    };
    
    convertNode(rootNode);
    return nodes;
  }

  private mapNodeType(oldType: string): BehaviorTreeNode['type'] {
    switch (oldType) {
      case 'selector': return 'composite';
      case 'sequence': return 'composite';
      case 'action': return 'task';
      case 'condition': return 'condition';
      default: return 'task';
    }
  }

  private generateBlackboardVariables(npc: NPC, behavior: NPCBehavior): BlackboardVariable[] {
    return [
      {
        name: 'npc_id',
        type: 'string',
        value: npc.id,
        scope: 'tree',
        persistence: 'permanent'
      },
      {
        name: 'current_state',
        type: 'string',
        value: 'idle',
        scope: 'tree',
        persistence: 'session'
      },
      {
        name: 'alertness_level',
        type: 'float',
        value: 0.1,
        scope: 'tree',
        persistence: 'temporary'
      },
      {
        name: 'target_player',
        type: 'object',
        value: null,
        scope: 'subtree',
        persistence: 'temporary'
      },
      {
        name: 'last_interaction_time',
        type: 'float',
        value: 0,
        scope: 'tree',
        persistence: 'session'
      }
    ];
  }

  private generateBehaviorServices(npc: NPC, options: BehaviorScriptingOptions): BehaviorService[] {
    const services: BehaviorService[] = [];
    
    // Perception service
    services.push({
      id: 'perception_service',
      name: 'Perception Update',
      interval: 0.5,
      node_scope: 'root',
      actions: [
        {
          type: 'scan_for_players',
          parameters: { radius: 10 },
          conditions: ['not_in_conversation']
        },
        {
          type: 'update_alertness',
          parameters: { decay_rate: 0.1 },
          conditions: []
        }
      ]
    });
    
    // Memory service if requested
    if (options.includeMemory) {
      services.push({
        id: 'memory_service',
        name: 'Memory Management',
        interval: 5.0,
        node_scope: 'root',
        actions: [
          {
            type: 'update_memories',
            parameters: {},
            conditions: []
          },
          {
            type: 'decay_short_term_memory',
            parameters: { decay_rate: 0.05 },
            conditions: []
          }
        ]
      });
    }
    
    // Schedule service if requested
    if (options.includeSchedules) {
      services.push({
        id: 'schedule_service',
        name: 'Schedule Management',
        interval: 60.0,
        node_scope: 'root',
        actions: [
          {
            type: 'check_schedule',
            parameters: {},
            conditions: []
          },
          {
            type: 'transition_activities',
            parameters: {},
            conditions: ['schedule_changed']
          }
        ]
      });
    }
    
    return services;
  }

  private generateBehaviorDecorators(options: BehaviorScriptingOptions): BehaviorDecorator[] {
    return [
      {
        id: 'cooldown_decorator',
        name: 'Cooldown',
        type: 'cooldown',
        properties: { duration: 5.0 }
      },
      {
        id: 'repeat_decorator',
        name: 'Repeat',
        type: 'repeat',
        properties: { count: -1 } // Infinite repeat
      },
      {
        id: 'blackboard_decorator',
        name: 'Blackboard Check',
        type: 'blackboard',
        properties: { key: 'alertness_level', operator: '>', value: 0.5 }
      }
    ];
  }

  private generateBehaviorComposites(options: BehaviorScriptingOptions): BehaviorComposite[] {
    return [
      {
        id: 'selector_composite',
        name: 'Selector',
        type: 'selector',
        properties: {}
      },
      {
        id: 'sequence_composite',
        name: 'Sequence',
        type: 'sequence',
        properties: {}
      },
      {
        id: 'parallel_composite',
        name: 'Parallel',
        type: 'parallel',
        properties: { success_policy: 'require_one', failure_policy: 'require_all' }
      }
    ];
  }

  private async generateAIPersonality(
    npc: NPC,
    campaign: Campaign,
    options: BehaviorScriptingOptions
  ): Promise<AIPersonality> {
    const traits = this.extractPersonalityTraits(npc);
    const preferences = this.generateNPCPreferences(npc, campaign);
    const reactions = this.generateEmotionalReactions(npc, options);
    const memory = this.generateMemorySystem(npc, options);
    const relationships = this.generateRelationshipSystem(npc, campaign);
    
    return {
      traits,
      preferences,
      reactions,
      memory,
      relationships
    };
  }

  private extractPersonalityTraits(npc: NPC): PersonalityTraits {
    // Convert D&D personality to Big Five + additional traits
    const traits: PersonalityTraits = {
      openness: 50,
      conscientiousness: 50,
      extraversion: 50,
      agreeableness: 50,
      neuroticism: 50,
      intelligence: 50,
      aggression: 30,
      curiosity: 50,
      loyalty: 50,
      humor: 50
    };
    
    // Modify based on existing personality traits
    if (npc.personality.traits.includes('curious')) {
      traits.openness = 80;
      traits.curiosity = 90;
    }
    if (npc.personality.traits.includes('brave')) {
      traits.neuroticism = 20;
      traits.aggression = 60;
    }
    if (npc.personality.traits.includes('friendly')) {
      traits.extraversion = 80;
      traits.agreeableness = 80;
    }
    if (npc.personality.traits.includes('intelligent')) {
      traits.intelligence = 90;
    }
    
    return traits;
  }

  private generateNPCPreferences(npc: NPC, campaign: Campaign): NPCPreferences {
    const preferences: NPCPreferences = {
      topics: this.generateTopicPreferences(npc),
      activities: this.generateActivityPreferences(npc),
      locations: this.generateLocationPreferences(npc, campaign),
      items: this.generateItemPreferences(npc),
      weather: this.generateWeatherPreferences(npc),
      timeOfDay: this.generateTimePreferences(npc)
    };
    
    return preferences;
  }

  // Helper methods for preference generation
  private generateTopicPreferences(npc: NPC): TopicPreference[] {
    const topics: TopicPreference[] = [];
    
    // Role-based topic preferences
    switch (npc.role) {
      case 'merchant':
        topics.push(
          { topic: 'trade', interest: 90, knowledge: 85, willingness: 95 },
          { topic: 'prices', interest: 80, knowledge: 90, willingness: 90 },
          { topic: 'rare_items', interest: 85, knowledge: 70, willingness: 80 }
        );
        break;
      case 'guard':
        topics.push(
          { topic: 'security', interest: 95, knowledge: 80, willingness: 70 },
          { topic: 'law', interest: 80, knowledge: 75, willingness: 85 },
          { topic: 'crime', interest: 70, knowledge: 85, willingness: 60 }
        );
        break;
      case 'scholar':
        topics.push(
          { topic: 'history', interest: 95, knowledge: 90, willingness: 90 },
          { topic: 'magic', interest: 85, knowledge: 80, willingness: 85 },
          { topic: 'books', interest: 90, knowledge: 85, willingness: 80 }
        );
        break;
    }
    
    // Personality-based adjustments
    if (npc.personality.traits.includes('gossipy')) {
      topics.push({ topic: 'rumors', interest: 85, knowledge: 60, willingness: 95 });
    }
    if (npc.personality.traits.includes('secretive')) {
      topics.forEach(topic => topic.willingness *= 0.7);
    }
    
    return topics;
  }

  private generateActivityPreferences(npc: NPC): ActivityPreference[] {
    // This would generate activity preferences based on NPC role and personality
    return [
      {
        activity: 'conversation',
        enjoyment: npc.personality.traits.includes('social') ? 80 : 40,
        frequency: 'often',
        conditions: ['not_busy', 'friendly_person']
      }
    ];
  }

  private generateLocationPreferences(npc: NPC, campaign: Campaign): LocationPreference[] {
    const preferences: LocationPreference[] = [];
    
    // Home location has highest comfort
    preferences.push({
      location: npc.location,
      comfort: 90,
      familiarity: 100,
      avoidance: false
    });
    
    // Add preferences for other locations based on connections and experiences
    campaign.locations.forEach(location => {
      if (location.name !== npc.location) {
        let comfort = 50; // Neutral default
        let familiarity = 20; // Low default
        
        // Adjust based on location type and NPC personality
        if (location.type === 'city' && npc.personality.traits.includes('social')) {
          comfort += 20;
        }
        if (location.type === 'wilderness' && npc.personality.traits.includes('reclusive')) {
          comfort += 30;
        }
        if (location.type === 'dungeon') {
          comfort -= 40; // Most NPCs uncomfortable in dungeons
        }
        
        preferences.push({
          location: location.name,
          comfort,
          familiarity,
          avoidance: comfort < 20
        });
      }
    });
    
    return preferences;
  }

  private generateItemPreferences(npc: NPC): ItemPreference[] {
    // Generate item preferences based on role and personality
    const preferences: ItemPreference[] = [];
    
    if (npc.role === 'merchant') {
      preferences.push(
        { item: 'gold', desire: 95, value: 100, willing_to_trade: true },
        { item: 'rare_goods', desire: 80, value: 90, willing_to_trade: true }
      );
    }
    
    if (npc.personality.traits.includes('materialistic')) {
      preferences.push(
        { item: 'jewelry', desire: 85, value: 80, willing_to_trade: false },
        { item: 'luxury_items', desire: 90, value: 85, willing_to_trade: false }
      );
    }
    
    return preferences;
  }

  private generateWeatherPreferences(npc: NPC): WeatherPreference {
    // Generate weather preferences based on personality
    return {
      sunny: npc.personality.traits.includes('optimistic') ? 80 : 60,
      rainy: npc.personality.traits.includes('melancholic') ? 70 : 40,
      cloudy: 50,
      stormy: npc.personality.traits.includes('dramatic') ? 60 : 20,
      snowy: npc.personality.traits.includes('winter_born') ? 80 : 30
    };
  }

  private generateTimePreferences(npc: NPC): TimePreference {
    // Generate time of day preferences
    let preferences = {
      morning: 50,
      afternoon: 50,
      evening: 50,
      night: 30 // Most NPCs less active at night
    };
    
    // Adjust based on role
    if (npc.role === 'guard') {
      preferences.night = 70; // Guards work night shifts
    }
    if (npc.role === 'merchant') {
      preferences.afternoon = 80; // Peak business hours
    }
    
    // Adjust based on personality
    if (npc.personality.traits.includes('early_riser')) {
      preferences.morning = 90;
      preferences.night = 10;
    }
    if (npc.personality.traits.includes('night_owl')) {
      preferences.night = 80;
      preferences.morning = 20;
    }
    
    return preferences;
  }

  private generateEmotionalReactions(npc: NPC, options: BehaviorScriptingOptions): EmotionalReactions {
    // This would be a complex system generating emotional reactions
    // For brevity, providing structure
    return {
      triggers: [],
      expressions: [],
      recovery: {
        baseRecoveryRate: 1.0,
        factors: [],
        activities: []
      },
      contagion: {
        susceptibility: 50,
        influence: 50,
        emotions: ['happy', 'angry', 'fearful']
      }
    };
  }

  private generateMemorySystem(npc: NPC, options: BehaviorScriptingOptions): MemorySystem {
    // Generate memory system configuration
    return {
      shortTerm: {
        capacity: 10,
        duration: 300, // 5 minutes
        decay_rate: 0.1,
        importance_threshold: 0.3
      },
      longTerm: {
        capacity: 100,
        duration: 86400 * 7, // 1 week
        decay_rate: 0.01,
        importance_threshold: 0.7
      },
      events: [],
      relationships: [],
      locations: [],
      items: []
    };
  }

  private generateRelationshipSystem(npc: NPC, campaign: Campaign): RelationshipSystem {
    // Generate relationship management system
    return {
      dynamics: npc.relationships?.map(rel => ({
        target: rel.targetId,
        relationship_type: rel.type,
        strength: rel.strength,
        stability: 70,
        history: [],
        influences: []
      })) || [],
      tracking: {
        update_frequency: 60,
        factors: [],
        memory_integration: true
      },
      development: {
        stages: [],
        milestones: [],
        barriers: []
      }
    };
  }

  // Export methods
  private async exportBehaviors(
    behaviors: NPCBehavior[],
    campaign: Campaign,
    options: BehaviorScriptingOptions
  ): Promise<void> {
    // Export individual behavior files
    for (const behavior of behaviors) {
      await this.exportSingleBehavior(behavior, options);
    }
    
    // Export advanced behavior trees if generated
    if (this.behaviorTrees.size > 0) {
      await this.exportAdvancedBehaviorTrees(options);
    }
    
    // Export AI personalities if generated
    if (this.personalities.size > 0) {
      await this.exportAIPersonalities(options);
    }
    
    // Export master behavior index
    await this.exportBehaviorIndex(behaviors, campaign, options);
    
    console.log(`📤 Exported ${behaviors.length} NPC behaviors`);
  }

  private async exportSingleBehavior(
    behavior: NPCBehavior,
    options: BehaviorScriptingOptions
  ): Promise<void> {
    const fileName = `npc_${behavior.npcId}.${this.getFileExtension(options.format)}`;
    const filePath = path.join(this.outputPath, fileName);
    
    let content = '';
    
    switch (options.format) {
      case 'json':
        content = JSON.stringify(behavior, null, 2);
        break;
      case 'yaml':
        content = yaml.dump(behavior, { indent: 2 });
        break;
      case 'xml':
        content = this.convertBehaviorToXML(behavior);
        break;
      case 'lua':
        content = this.convertBehaviorToLua(behavior);
        break;
      case 'cs':
        content = this.convertBehaviorToCSharp(behavior);
        break;
      case 'gd':
        content = this.convertBehaviorToGDScript(behavior);
        break;
      case 'visual':
        content = this.convertBehaviorToVisualScript(behavior);
        break;
      case 'bt':
        content = this.convertBehaviorToBT(behavior);
        break;
    }
    
    await fs.writeFile(filePath, content, 'utf-8');
  }

  private getFileExtension(format: string): string {
    const extensions = {
      'json': 'json',
      'yaml': 'yml',
      'xml': 'xml',
      'lua': 'lua',
      'cs': 'cs',
      'gd': 'gd',
      'visual': 'json', // Visual scripting format
      'bt': 'bt' // Behavior tree format
    };
    return extensions[format as keyof typeof extensions] || 'json';
  }

  // Format conversion methods (simplified for brevity)
  private convertBehaviorToXML(behavior: NPCBehavior): string {
    return `<!-- XML behavior for ${behavior.npcId} -->`;
  }

  private convertBehaviorToLua(behavior: NPCBehavior): string {
    return `-- Lua behavior for ${behavior.npcId}`;
  }

  private convertBehaviorToCSharp(behavior: NPCBehavior): string {
    return `// C# behavior for ${behavior.npcId}`;
  }

  private convertBehaviorToGDScript(behavior: NPCBehavior): string {
    return `# GDScript behavior for ${behavior.npcId}`;
  }

  private convertBehaviorToVisualScript(behavior: NPCBehavior): string {
    return JSON.stringify({
      visual_script: true,
      npc_id: behavior.npcId,
      nodes: [], // Visual scripting nodes would go here
      connections: []
    }, null, 2);
  }

  private convertBehaviorToBT(behavior: NPCBehavior): string {
    return `// Behavior Tree for ${behavior.npcId}`;
  }

  private async exportAdvancedBehaviorTrees(options: BehaviorScriptingOptions): Promise<void> {
    const treesData = Object.fromEntries(this.behaviorTrees);
    const filePath = path.join(this.outputPath, `behavior_trees.${this.getFileExtension(options.format)}`);
    
    let content = '';
    switch (options.format) {
      case 'json':
        content = JSON.stringify(treesData, null, 2);
        break;
      case 'yaml':
        content = yaml.dump(treesData, { indent: 2 });
        break;
      default:
        content = JSON.stringify(treesData, null, 2);
    }
    
    await fs.writeFile(filePath, content, 'utf-8');
  }

  private async exportAIPersonalities(options: BehaviorScriptingOptions): Promise<void> {
    const personalitiesData = Object.fromEntries(this.personalities);
    const filePath = path.join(this.outputPath, `ai_personalities.${this.getFileExtension(options.format)}`);
    
    let content = '';
    switch (options.format) {
      case 'json':
        content = JSON.stringify(personalitiesData, null, 2);
        break;
      case 'yaml':
        content = yaml.dump(personalitiesData, { indent: 2 });
        break;
      default:
        content = JSON.stringify(personalitiesData, null, 2);
    }
    
    await fs.writeFile(filePath, content, 'utf-8');
  }

  private async exportBehaviorIndex(
    behaviors: NPCBehavior[],
    campaign: Campaign,
    options: BehaviorScriptingOptions
  ): Promise<void> {
    const index = {
      campaign: campaign.name,
      generated_at: new Date().toISOString(),
      behavior_count: behaviors.length,
      options,
      behaviors: behaviors.map(b => ({
        npc_id: b.npcId,
        states: b.states.length,
        transitions: b.transitions.length,
        reactions: b.reactions.length
      })),
      advanced_trees: this.behaviorTrees.size,
      personalities: this.personalities.size
    };
    
    const filePath = path.join(this.outputPath, 'behavior_index.json');
    await fs.writeFile(filePath, JSON.stringify(index, null, 2), 'utf-8');
  }

  // Additional helper methods
  private generatePatrolWaypoints(npc: NPC, campaign: Campaign): any[] {
    // Generate patrol waypoints for guard NPCs
    return [
      { x: 0, y: 0, action: 'look_around' },
      { x: 10, y: 0, action: 'pause' },
      { x: 10, y: 10, action: 'look_around' },
      { x: 0, y: 10, action: 'pause' }
    ];
  }

  private generateSupplyRoutes(npc: NPC, campaign: Campaign): any[] {
    // Generate supply routes for merchant NPCs
    return [
      { location: 'warehouse', action: 'collect_goods' },
      { location: 'shop', action: 'stock_shelves' }
    ];
  }
}