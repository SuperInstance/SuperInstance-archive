import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { 
  Campaign, 
  Quest, 
  QuestSystem, 
  ProcessedQuest,
  QuestObjective,
  QuestStep,
  QuestTrigger,
  QuestCondition,
  QuestReward,
  QuestProgression,
  QuestDependency,
  QuestTracking,
  Character,
  NPC,
  Location,
  Session
} from '../types';

export interface QuestConversionOptions {
  includeStoryQuests: boolean;
  includeSideQuests: boolean;
  includePersonalQuests: boolean;
  generateProgressiveObjectives: boolean;
  createQuestChains: boolean;
  addHints: boolean;
  includeFailureConditions: boolean;
  generateRewards: boolean;
  balanceRewards: boolean;
  createVariations: boolean;
  format: 'json' | 'yaml' | 'xml' | 'lua' | 'cs' | 'gd';
}

export interface QuestChain {
  id: string;
  name: string;
  description: string;
  category: 'main' | 'faction' | 'character' | 'location' | 'seasonal';
  quests: string[];
  prerequisites: QuestChainPrerequisite[];
  rewards: QuestChainReward[];
  narrative: QuestChainNarrative;
}

export interface QuestChainPrerequisite {
  type: 'level' | 'quest' | 'item' | 'location' | 'reputation';
  target: string;
  value: any;
  description: string;
}

export interface QuestChainReward {
  type: 'title' | 'ability' | 'item' | 'access' | 'story';
  reward: string;
  description: string;
}

export interface QuestChainNarrative {
  opening: string;
  progression: string[];
  climax: string;
  resolution: string;
}

export interface QuestLocation {
  id: string;
  name: string;
  type: 'hub' | 'destination' | 'waypoint' | 'secret';
  coordinates?: { x: number; y: number; z?: number };
  radius: number;
  requirements: string[];
  discovery: QuestDiscovery;
}

export interface QuestDiscovery {
  method: 'automatic' | 'interaction' | 'item' | 'dialogue' | 'exploration';
  trigger: string;
  hint: string;
  reward: string;
}

export interface QuestVariation {
  id: string;
  baseQuestId: string;
  conditions: string[];
  modifications: QuestModification[];
  narrative: QuestVariationNarrative;
}

export interface QuestModification {
  target: 'objective' | 'reward' | 'npc' | 'location' | 'time_limit';
  type: 'replace' | 'add' | 'remove' | 'modify';
  value: any;
  description: string;
}

export interface QuestVariationNarrative {
  reason: string;
  dialogue_changes: DialogueChange[];
  outcome_changes: string[];
}

export interface DialogueChange {
  npc: string;
  original: string;
  replacement: string;
  context: string;
}

export interface QuestJournal {
  entries: JournalEntry[];
  categories: JournalCategory[];
  filters: JournalFilter[];
  sorting: JournalSorting;
}

export interface JournalEntry {
  questId: string;
  title: string;
  description: string;
  objectives: JournalObjective[];
  status: string;
  progress: number;
  location: string;
  giver: string;
  timestamp: Date;
  notes: string[];
}

export interface JournalObjective {
  id: string;
  description: string;
  completed: boolean;
  optional: boolean;
  hidden: boolean;
  progress: number;
  maxProgress: number;
}

export interface JournalCategory {
  id: string;
  name: string;
  icon: string;
  color: string;
  filter: string;
}

export interface JournalFilter {
  id: string;
  name: string;
  criteria: FilterCriteria[];
}

export interface FilterCriteria {
  field: string;
  operator: '==' | '!=' | '>' | '<' | 'contains' | 'in';
  value: any;
}

export interface JournalSorting {
  default: 'date' | 'priority' | 'progress' | 'location';
  options: SortOption[];
}

export interface SortOption {
  field: string;
  label: string;
  direction: 'asc' | 'desc';
}

export interface QuestRewardSystem {
  experience: ExperienceRewards;
  items: ItemRewards;
  reputation: ReputationRewards;
  progression: ProgressionRewards;
  story: StoryRewards;
}

export interface ExperienceRewards {
  base: number;
  multipliers: ExperienceMultiplier[];
  bonuses: ExperienceBonus[];
}

export interface ExperienceMultiplier {
  condition: string;
  multiplier: number;
  description: string;
}

export interface ExperienceBonus {
  type: 'completion_speed' | 'optional_objectives' | 'creative_solution' | 'pacifist' | 'perfectionist';
  amount: number;
  description: string;
}

export interface ItemRewards {
  guaranteed: RewardItem[];
  optional: RewardItem[];
  randomTables: RandomRewardTable[];
}

export interface RewardItem {
  id: string;
  name: string;
  type: string;
  rarity: string;
  level: number;
  properties: Record<string, any>;
  conditions: string[];
}

export interface RandomRewardTable {
  id: string;
  name: string;
  entries: RewardTableEntry[];
  rolls: number;
}

export interface RewardTableEntry {
  weight: number;
  item: RewardItem;
  conditions: string[];
}

export interface ReputationRewards {
  factions: FactionReputation[];
  global: number;
  specific: SpecificReputation[];
}

export interface FactionReputation {
  faction: string;
  amount: number;
  conditions: string[];
}

export interface SpecificReputation {
  target: string;
  amount: number;
  description: string;
}

export interface ProgressionRewards {
  unlocks: ProgressionUnlock[];
  abilities: AbilityReward[];
  access: AccessReward[];
}

export interface ProgressionUnlock {
  type: 'area' | 'feature' | 'vendor' | 'quest_line' | 'difficulty';
  target: string;
  description: string;
}

export interface AbilityReward {
  id: string;
  name: string;
  type: string;
  description: string;
  requirements: string[];
}

export interface AccessReward {
  type: 'location' | 'npc' | 'service' | 'information';
  target: string;
  description: string;
}

export interface StoryRewards {
  revelations: StoryRevelation[];
  relationships: RelationshipChange[];
  world_state: WorldStateChange[];
}

export interface StoryRevelation {
  id: string;
  title: string;
  content: string;
  impact: 'minor' | 'moderate' | 'major';
  unlocks: string[];
}

export interface RelationshipChange {
  target: string;
  change: number;
  reason: string;
  permanent: boolean;
}

export interface WorldStateChange {
  variable: string;
  change: any;
  description: string;
  permanent: boolean;
}

export class QuestSystemConverter extends EventEmitter {
  private outputPath: string;
  private questChains: Map<string, QuestChain> = new Map();
  private questLocations: Map<string, QuestLocation> = new Map();
  private questVariations: Map<string, QuestVariation[]> = new Map();
  private rewardSystem: QuestRewardSystem;

  constructor(outputPath: string) {
    super();
    this.outputPath = outputPath;
    this.rewardSystem = this.initializeRewardSystem();
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.outputPath, { recursive: true });
      console.log('📋 Quest system converter initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing quest system converter:', error);
      throw error;
    }
  }

  private initializeRewardSystem(): QuestRewardSystem {
    return {
      experience: {
        base: 100,
        multipliers: [
          { condition: 'quest_difficulty == "hard"', multiplier: 1.5, description: 'Hard quest bonus' },
          { condition: 'player_level < quest_level - 2', multiplier: 1.2, description: 'Underleveled bonus' }
        ],
        bonuses: [
          { type: 'completion_speed', amount: 50, description: 'Completed quickly' },
          { type: 'optional_objectives', amount: 25, description: 'Per optional objective' },
          { type: 'creative_solution', amount: 100, description: 'Found creative solution' }
        ]
      },
      items: {
        guaranteed: [],
        optional: [],
        randomTables: []
      },
      reputation: {
        factions: [],
        global: 0,
        specific: []
      },
      progression: {
        unlocks: [],
        abilities: [],
        access: []
      },
      story: {
        revelations: [],
        relationships: [],
        world_state: []
      }
    };
  }

  public async convertQuestSystem(
    campaign: Campaign,
    options: QuestConversionOptions
  ): Promise<QuestSystem> {
    console.log(`📋 Converting quest system for campaign: ${campaign.name}`);

    // Filter quests based on options
    const questsToProcess = this.filterQuests(campaign.quests, options);

    // Process each quest
    const processedQuests: ProcessedQuest[] = [];
    for (const quest of questsToProcess) {
      const processedQuest = await this.processQuest(quest, campaign, options);
      processedQuests.push(processedQuest);

      // Generate variations if requested
      if (options.createVariations) {
        const variations = await this.generateQuestVariations(quest, campaign);
        this.questVariations.set(quest.id, variations);
      }
    }

    // Create quest chains
    let questChains: QuestChain[] = [];
    if (options.createQuestChains) {
      questChains = await this.createQuestChains(processedQuests, campaign);
    }

    // Build quest progression system
    const progression = this.buildQuestProgression(processedQuests, questChains);

    // Create quest dependencies
    const dependencies = this.analyzeQuestDependencies(processedQuests, campaign);

    // Set up quest tracking
    const tracking = this.setupQuestTracking(processedQuests, options);

    // Generate quest journal
    const journal = this.generateQuestJournal(processedQuests);

    const questSystem: QuestSystem = {
      quests: processedQuests,
      objectives: this.extractAllObjectives(processedQuests),
      progression,
      dependencies,
      rewards: this.rewardSystem,
      tracking
    };

    // Export the quest system
    await this.exportQuestSystem(questSystem, campaign, options);

    console.log(`✅ Converted ${processedQuests.length} quests with ${questChains.length} quest chains`);
    this.emit('quest-system-converted', {
      questCount: processedQuests.length,
      chainCount: questChains.length,
      variations: this.questVariations.size
    });

    return questSystem;
  }

  private filterQuests(quests: Quest[], options: QuestConversionOptions): Quest[] {
    return quests.filter(quest => {
      if (!options.includeStoryQuests && quest.type === 'main') return false;
      if (!options.includeSideQuests && quest.type === 'side') return false;
      if (!options.includePersonalQuests && quest.type === 'personal') return false;
      return true;
    });
  }

  private async processQuest(
    quest: Quest,
    campaign: Campaign,
    options: QuestConversionOptions
  ): Promise<ProcessedQuest> {
    // Convert basic quest information
    const processedQuest: ProcessedQuest = {
      id: quest.id,
      title: quest.title,
      category: this.determineQuestCategory(quest, campaign),
      description: quest.description,
      steps: await this.generateQuestSteps(quest, campaign, options),
      triggers: await this.generateQuestTriggers(quest, campaign),
      conditions: await this.generateQuestConditions(quest, campaign),
      rewards: await this.generateQuestRewards(quest, campaign, options),
      failureConditions: options.includeFailureConditions 
        ? await this.generateFailureConditions(quest, campaign)
        : [],
      timeConstraints: this.analyzeTimeConstraints(quest),
      priority: this.calculateQuestPriority(quest, campaign)
    };

    // Add quest locations
    this.processQuestLocations(quest, campaign);

    return processedQuest;
  }

  private determineQuestCategory(quest: Quest, campaign: Campaign): string {
    // Analyze quest to determine category
    if (quest.type === 'main') return 'main_story';
    if (quest.type === 'side') {
      // Further categorize side quests
      if (quest.giver) {
        const giver = campaign.npcs.find(npc => npc.id === quest.giver);
        if (giver?.role === 'merchant') return 'commerce';
        if (giver?.role === 'ally') return 'favor';
      }
      return 'side_activity';
    }
    if (quest.type === 'personal') return 'character_development';
    
    // Analyze objectives for further categorization
    const objectiveTypes = quest.objectives.map(obj => obj.type);
    if (objectiveTypes.includes('kill')) return 'combat';
    if (objectiveTypes.includes('collect')) return 'collection';
    if (objectiveTypes.includes('escort')) return 'escort';
    if (objectiveTypes.includes('puzzle')) return 'puzzle';
    
    return 'general';
  }

  private async generateQuestSteps(
    quest: Quest,
    campaign: Campaign,
    options: QuestConversionOptions
  ): Promise<QuestStep[]> {
    const steps: QuestStep[] = [];

    // Convert each objective to one or more steps
    for (let i = 0; i < quest.objectives.length; i++) {
      const objective = quest.objectives[i];
      const questSteps = await this.objectiveToSteps(objective, quest, campaign, i);
      steps.push(...questSteps);
    }

    // Add progressive objectives if requested
    if (options.generateProgressiveObjectives) {
      const progressiveSteps = this.generateProgressiveSteps(steps, quest);
      steps.push(...progressiveSteps);
    }

    // Add hint steps if requested
    if (options.addHints) {
      const hintSteps = this.generateHintSteps(quest, campaign);
      steps.unshift(...hintSteps);
    }

    return steps;
  }

  private async objectiveToSteps(
    objective: QuestObjective,
    quest: Quest,
    campaign: Campaign,
    index: number
  ): Promise<QuestStep[]> {
    const steps: QuestStep[] = [];
    
    const baseStep: QuestStep = {
      id: `${quest.id}_step_${index + 1}`,
      description: objective.description,
      type: objective.type,
      target: objective.target,
      quantity: objective.quantity,
      location: objective.location,
      optional: objective.optional,
      hidden: objective.hidden,
      conditions: this.generateStepConditions(objective, quest),
      triggers: this.generateStepTriggers(objective, quest),
      completion: this.generateStepCompletion(objective, quest),
      hints: this.generateStepHints(objective, quest, campaign),
      tracking: this.generateStepTracking(objective)
    };

    steps.push(baseStep);

    // Break down complex objectives into sub-steps
    if (objective.quantity > 1) {
      const subSteps = this.generateSubSteps(baseStep, objective);
      steps.push(...subSteps);
    }

    return steps;
  }

  private generateSubSteps(parentStep: QuestStep, objective: QuestObjective): QuestStep[] {
    const subSteps: QuestStep[] = [];
    
    if (objective.type === 'collect' && objective.quantity > 3) {
      // Break collection into smaller milestones
      const milestones = [
        Math.floor(objective.quantity * 0.25),
        Math.floor(objective.quantity * 0.5),
        Math.floor(objective.quantity * 0.75),
        objective.quantity
      ];

      milestones.forEach((milestone, index) => {
        if (milestone > 0) {
          subSteps.push({
            ...parentStep,
            id: `${parentStep.id}_sub_${index + 1}`,
            description: `Collect ${milestone} ${objective.target}`,
            quantity: milestone,
            type: 'milestone',
            optional: true,
            hidden: false
          });
        }
      });
    }

    return subSteps;
  }

  private async generateQuestTriggers(quest: Quest, campaign: Campaign): Promise<QuestTrigger[]> {
    const triggers: QuestTrigger[] = [];

    // Location-based trigger
    if (quest.prerequisites.some(p => p.type === 'location')) {
      const locationPrereq = quest.prerequisites.find(p => p.type === 'location');
      if (locationPrereq) {
        triggers.push({
          id: `${quest.id}_location_trigger`,
          type: 'location',
          condition: `player.location == "${locationPrereq.target}"`,
          action: 'offer_quest',
          priority: 1
        });
      }
    }

    // NPC interaction trigger
    if (quest.giver) {
      triggers.push({
        id: `${quest.id}_npc_trigger`,
        type: 'dialogue',
        condition: `npc.id == "${quest.giver}" && quest.status == "available"`,
        action: 'show_quest_option',
        priority: 2
      });
    }

    // Level-based trigger
    if (quest.prerequisites.some(p => p.type === 'level')) {
      const levelPrereq = quest.prerequisites.find(p => p.type === 'level');
      if (levelPrereq) {
        triggers.push({
          id: `${quest.id}_level_trigger`,
          type: 'level_up',
          condition: `player.level >= ${levelPrereq.value}`,
          action: 'notify_quest_available',
          priority: 0
        });
      }
    }

    // Time-based trigger
    if (quest.timeLimit) {
      triggers.push({
        id: `${quest.id}_time_trigger`,
        type: 'timer',
        condition: `quest.time_remaining <= 300`, // 5 minutes warning
        action: 'warn_time_limit',
        priority: 3
      });
    }

    return triggers;
  }

  private async generateQuestConditions(quest: Quest, campaign: Campaign): Promise<QuestCondition[]> {
    const conditions: QuestCondition[] = [];

    // Prerequisites as conditions
    quest.prerequisites.forEach(prerequisite => {
      const condition: QuestCondition = {
        id: `${quest.id}_prereq_${prerequisite.type}`,
        type: prerequisite.type,
        description: `Requires ${prerequisite.type}: ${prerequisite.target}`,
        check: this.generateConditionCheck(prerequisite),
        failMessage: this.generateConditionFailMessage(prerequisite)
      };
      conditions.push(condition);
    });

    // Reputation conditions
    const giver = campaign.npcs.find(npc => npc.id === quest.giver);
    if (giver) {
      conditions.push({
        id: `${quest.id}_reputation_check`,
        type: 'reputation',
        description: `Requires good standing with ${giver.name}`,
        check: `player.reputation["${giver.id}"] >= 0`,
        failMessage: `${giver.name} doesn't trust you enough.`
      });
    }

    // Item conditions
    if (quest.objectives.some(obj => obj.type === 'collect')) {
      const collectObjective = quest.objectives.find(obj => obj.type === 'collect');
      if (collectObjective) {
        conditions.push({
          id: `${quest.id}_inventory_space`,
          type: 'inventory',
          description: 'Requires inventory space',
          check: `player.inventory.freeSlots >= ${collectObjective.quantity}`,
          failMessage: 'Not enough inventory space.'
        });
      }
    }

    return conditions;
  }

  private async generateQuestRewards(
    quest: Quest,
    campaign: Campaign,
    options: QuestConversionOptions
  ): Promise<QuestReward[]> {
    if (!options.generateRewards) {
      return quest.rewards || [];
    }

    const rewards: QuestReward[] = [];

    // Base experience reward
    const baseExp = this.calculateBaseExperience(quest, campaign);
    rewards.push({
      type: 'experience',
      experience: baseExp,
      description: `${baseExp} experience points`
    });

    // Gold reward
    const goldAmount = this.calculateGoldReward(quest, campaign, options.balanceRewards);
    if (goldAmount > 0) {
      rewards.push({
        type: 'gold',
        gold: goldAmount,
        description: `${goldAmount} gold pieces`
      });
    }

    // Item rewards
    const itemRewards = await this.generateItemRewards(quest, campaign);
    rewards.push(...itemRewards);

    // Reputation rewards
    if (quest.giver) {
      rewards.push({
        type: 'reputation',
        reputation: { [quest.giver]: 1 },
        description: 'Improved reputation with quest giver'
      });
    }

    // Story rewards
    if (quest.type === 'main') {
      rewards.push({
        type: 'story',
        description: 'Story progression'
      });
    }

    return rewards;
  }

  private calculateBaseExperience(quest: Quest, campaign: Campaign): number {
    let baseExp = 100; // Base experience

    // Modify based on quest type
    switch (quest.type) {
      case 'main': baseExp *= 2; break;
      case 'side': baseExp *= 1.5; break;
      case 'personal': baseExp *= 1.2; break;
    }

    // Modify based on objectives
    const objectiveMultiplier = quest.objectives.length * 0.5 + 0.5;
    baseExp *= objectiveMultiplier;

    // Modify based on difficulty (inferred from prerequisites)
    const difficultyMultiplier = quest.prerequisites.length * 0.3 + 1;
    baseExp *= difficultyMultiplier;

    return Math.round(baseExp);
  }

  private calculateGoldReward(quest: Quest, campaign: Campaign, balance: boolean): number {
    let gold = 50; // Base gold

    // Modify based on quest type
    switch (quest.type) {
      case 'main': gold *= 3; break;
      case 'side': gold *= 2; break;
      case 'personal': gold *= 1; break;
    }

    // Balance based on campaign level (if balancing is enabled)
    if (balance) {
      const avgCharacterLevel = campaign.characters.reduce((sum, char) => sum + char.level, 0) / campaign.characters.length;
      gold *= (avgCharacterLevel / 3 + 0.5);
    }

    return Math.round(gold);
  }

  private async generateItemRewards(quest: Quest, campaign: Campaign): Promise<QuestReward[]> {
    const itemRewards: QuestReward[] = [];

    // Generate items based on quest type and objectives
    if (quest.type === 'main') {
      // Main quests get unique or rare items
      itemRewards.push({
        type: 'item',
        item: this.generateUniqueItem(quest, 'rare'),
        description: 'Rare quest reward item'
      });
    }

    if (quest.objectives.some(obj => obj.type === 'kill')) {
      // Combat quests might reward weapons or armor
      itemRewards.push({
        type: 'item',
        item: this.generateCombatItem(quest),
        description: 'Combat equipment'
      });
    }

    if (quest.objectives.some(obj => obj.type === 'puzzle')) {
      // Puzzle quests might reward utility items
      itemRewards.push({
        type: 'item',
        item: this.generateUtilityItem(quest),
        description: 'Useful tool or trinket'
      });
    }

    return itemRewards;
  }

  private generateUniqueItem(quest: Quest, rarity: string): string {
    const itemNames = [
      `${quest.title.replace(/\s+/g, '')}Medallion`,
      `Relic of ${quest.title}`,
      `${quest.title} Token`,
      `Memento of ${quest.title}`
    ];
    
    return itemNames[Math.floor(Math.random() * itemNames.length)];
  }

  private generateCombatItem(quest: Quest): string {
    const combatItems = [
      'Enhanced Sword',
      'Protective Amulet',
      'Combat Gauntlets',
      'Reinforced Shield',
      'Battle Potion'
    ];
    
    return combatItems[Math.floor(Math.random() * combatItems.length)];
  }

  private generateUtilityItem(quest: Quest): string {
    const utilityItems = [
      'Puzzle Box',
      'Decoder Ring',
      'Magnifying Glass',
      'Lockpick Set',
      'Traveler\'s Map'
    ];
    
    return utilityItems[Math.floor(Math.random() * utilityItems.length)];
  }

  private async generateFailureConditions(quest: Quest, campaign: Campaign): Promise<string[]> {
    const failureConditions: string[] = [];

    // Time-based failure
    if (quest.timeLimit) {
      failureConditions.push(`quest.elapsed_time > ${quest.timeLimit}`);
    }

    // Death of important NPC
    if (quest.giver) {
      failureConditions.push(`npc["${quest.giver}"].alive == false`);
    }

    // Location-based failure
    const locationObjectives = quest.objectives.filter(obj => obj.location);
    locationObjectives.forEach(obj => {
      if (obj.location) {
        failureConditions.push(`location["${obj.location}"].destroyed == true`);
      }
    });

    // Item-based failure (losing required items)
    const collectObjectives = quest.objectives.filter(obj => obj.type === 'collect');
    collectObjectives.forEach(obj => {
      failureConditions.push(`player.inventory.count("${obj.target}") < ${obj.quantity}`);
    });

    return failureConditions;
  }

  private analyzeTimeConstraints(quest: Quest): any {
    return {
      hasTimeLimit: !!quest.timeLimit,
      timeLimit: quest.timeLimit,
      timeType: quest.timeLimit ? 'absolute' : 'none',
      urgency: quest.timeLimit && quest.timeLimit < 86400 ? 'high' : 'normal' // Less than 1 day
    };
  }

  private calculateQuestPriority(quest: Quest, campaign: Campaign): number {
    let priority = 0;

    // Base priority by type
    switch (quest.type) {
      case 'main': priority = 10; break;
      case 'side': priority = 5; break;
      case 'personal': priority = 3; break;
      default: priority = 1;
    }

    // Increase priority based on time constraints
    if (quest.timeLimit) {
      priority += 5;
    }

    // Increase priority based on prerequisites (blocking other content)
    priority += quest.prerequisites.length * 2;

    // Decrease priority based on difficulty (inferred)
    const difficultyPenalty = quest.objectives.length > 5 ? 2 : 0;
    priority = Math.max(1, priority - difficultyPenalty);

    return priority;
  }

  private async createQuestChains(processedQuests: ProcessedQuest[], campaign: Campaign): Promise<QuestChain[]> {
    const chains: QuestChain[] = [];

    // Group quests by common elements
    const questGroups = this.groupQuestsByChain(processedQuests, campaign);

    for (const [chainId, quests] of questGroups.entries()) {
      if (quests.length > 1) {
        const chain = await this.buildQuestChain(chainId, quests, campaign);
        chains.push(chain);
        this.questChains.set(chainId, chain);
      }
    }

    return chains;
  }

  private groupQuestsByChain(processedQuests: ProcessedQuest[], campaign: Campaign): Map<string, ProcessedQuest[]> {
    const groups = new Map<string, ProcessedQuest[]>();

    // Group by quest giver
    const giverGroups = new Map<string, ProcessedQuest[]>();
    processedQuests.forEach(quest => {
      const originalQuest = campaign.quests.find(q => q.id === quest.id);
      if (originalQuest?.giver) {
        if (!giverGroups.has(originalQuest.giver)) {
          giverGroups.set(originalQuest.giver, []);
        }
        giverGroups.get(originalQuest.giver)!.push(quest);
      }
    });

    // Convert giver groups to chains
    for (const [giver, quests] of giverGroups.entries()) {
      if (quests.length > 1) {
        groups.set(`chain_${giver}`, quests);
      }
    }

    // Group by location
    const locationGroups = new Map<string, ProcessedQuest[]>();
    processedQuests.forEach(quest => {
      if (quest.steps.some(step => step.location)) {
        const location = quest.steps.find(step => step.location)?.location;
        if (location) {
          if (!locationGroups.has(location)) {
            locationGroups.set(location, []);
          }
          locationGroups.get(location)!.push(quest);
        }
      }
    });

    // Convert location groups to chains
    for (const [location, quests] of locationGroups.entries()) {
      if (quests.length > 2) {
        groups.set(`chain_${location}`, quests);
      }
    }

    return groups;
  }

  private async buildQuestChain(chainId: string, quests: ProcessedQuest[], campaign: Campaign): Promise<QuestChain> {
    // Sort quests by priority and dependencies
    const sortedQuests = this.sortQuestsByDependencies(quests);

    const chain: QuestChain = {
      id: chainId,
      name: this.generateChainName(chainId, quests, campaign),
      description: this.generateChainDescription(quests),
      category: this.determineChainCategory(quests),
      quests: sortedQuests.map(q => q.id),
      prerequisites: this.generateChainPrerequisites(quests),
      rewards: this.generateChainRewards(quests),
      narrative: this.generateChainNarrative(quests, campaign)
    };

    return chain;
  }

  private sortQuestsByDependencies(quests: ProcessedQuest[]): ProcessedQuest[] {
    // Simple sort by priority for now
    // In a real implementation, this would analyze dependencies between quests
    return quests.sort((a, b) => b.priority - a.priority);
  }

  private generateChainName(chainId: string, quests: ProcessedQuest[], campaign: Campaign): string {
    if (chainId.startsWith('chain_')) {
      const entityId = chainId.replace('chain_', '');
      
      // Try to find NPC name
      const npc = campaign.npcs.find(n => n.id === entityId);
      if (npc) {
        return `${npc.name}'s Questline`;
      }
      
      // Try to find location name
      const location = campaign.locations.find(l => l.id === entityId);
      if (location) {
        return `${location.name} Adventures`;
      }
    }
    
    return `Quest Chain: ${quests[0].title}`;
  }

  private generateChainDescription(quests: ProcessedQuest[]): string {
    const mainThemes = this.extractChainThemes(quests);
    return `A series of interconnected quests involving ${mainThemes.join(', ')}.`;
  }

  private extractChainThemes(quests: ProcessedQuest[]): string[] {
    const themes = new Set<string>();
    
    quests.forEach(quest => {
      if (quest.category) themes.add(quest.category);
      
      // Extract themes from quest descriptions
      const description = quest.description.toLowerCase();
      if (description.includes('combat')) themes.add('combat');
      if (description.includes('mystery')) themes.add('mystery');
      if (description.includes('rescue')) themes.add('rescue');
      if (description.includes('exploration')) themes.add('exploration');
    });
    
    return Array.from(themes).slice(0, 3);
  }

  private determineChainCategory(quests: ProcessedQuest[]): QuestChain['category'] {
    // Determine chain category based on quest categories
    const categories = quests.map(q => q.category);
    
    if (categories.includes('main_story')) return 'main';
    if (categories.every(c => c.includes('character'))) return 'character';
    if (categories.some(c => c.includes('location'))) return 'location';
    
    return 'faction';
  }

  private generateChainPrerequisites(quests: ProcessedQuest[]): QuestChainPrerequisite[] {
    const prerequisites: QuestChainPrerequisite[] = [];
    
    // Get minimum level requirement from all quests
    const levelReqs = quests.flatMap(q => 
      q.conditions.filter(c => c.type === 'level').map(c => parseInt(c.check.match(/\d+/)?.[0] || '1'))
    );
    
    if (levelReqs.length > 0) {
      prerequisites.push({
        type: 'level',
        target: 'player_level',
        value: Math.min(...levelReqs),
        description: `Player must be at least level ${Math.min(...levelReqs)}`
      });
    }
    
    return prerequisites;
  }

  private generateChainRewards(quests: ProcessedQuest[]): QuestChainReward[] {
    const rewards: QuestChainReward[] = [];
    
    // Chain completion title
    rewards.push({
      type: 'title',
      reward: `${quests[0].category.replace('_', ' ')} Champion`,
      description: 'Special title for completing the quest chain'
    });
    
    // Bonus experience for chain completion
    rewards.push({
      type: 'ability',
      reward: 'Chain Completion Bonus',
      description: '50% bonus experience for the final quest'
    });
    
    return rewards;
  }

  private generateChainNarrative(quests: ProcessedQuest[], campaign: Campaign): QuestChainNarrative {
    const opening = quests[0].description;
    const progression = quests.slice(1, -1).map(q => q.description);
    const climax = quests.length > 1 ? quests[quests.length - 1].description : opening;
    const resolution = 'The quest chain reaches its conclusion, with lasting impacts on the world.';
    
    return { opening, progression, climax, resolution };
  }

  // Export methods
  private async exportQuestSystem(
    questSystem: QuestSystem,
    campaign: Campaign,
    options: QuestConversionOptions
  ): Promise<void> {
    const fileName = `quest_system.${this.getFileExtension(options.format)}`;
    const filePath = path.join(this.outputPath, fileName);
    
    let content: string;
    
    switch (options.format) {
      case 'json':
        content = JSON.stringify(questSystem, null, 2);
        break;
      case 'yaml':
        content = yaml.dump(questSystem, { indent: 2 });
        break;
      case 'xml':
        content = this.convertQuestSystemToXML(questSystem);
        break;
      case 'lua':
        content = this.convertQuestSystemToLua(questSystem);
        break;
      case 'cs':
        content = this.convertQuestSystemToCSharp(questSystem);
        break;
      case 'gd':
        content = this.convertQuestSystemToGDScript(questSystem);
        break;
      default:
        content = JSON.stringify(questSystem, null, 2);
    }
    
    await fs.writeFile(filePath, content, 'utf-8');
    console.log(`📋 Quest system exported: ${filePath}`);
  }

  private getFileExtension(format: string): string {
    const extensions = {
      'json': 'json',
      'yaml': 'yml',
      'xml': 'xml',
      'lua': 'lua',
      'cs': 'cs',
      'gd': 'gd'
    };
    return extensions[format as keyof typeof extensions] || 'json';
  }

  // Helper methods for step generation
  private generateStepConditions(objective: QuestObjective, quest: Quest): string[] {
    const conditions: string[] = [];
    
    if (objective.location) {
      conditions.push(`player.location == "${objective.location}"`);
    }
    
    if (!objective.optional) {
      conditions.push(`quest["${quest.id}"].status == "active"`);
    }
    
    return conditions;
  }

  private generateStepTriggers(objective: QuestObjective, quest: Quest): string[] {
    const triggers: string[] = [];
    
    switch (objective.type) {
      case 'kill':
        triggers.push(`on_enemy_death("${objective.target}")`);
        break;
      case 'collect':
        triggers.push(`on_item_acquired("${objective.target}")`);
        break;
      case 'talk':
        triggers.push(`on_dialogue_end("${objective.target}")`);
        break;
      case 'reach':
        triggers.push(`on_location_enter("${objective.target}")`);
        break;
    }
    
    return triggers;
  }

  private generateStepCompletion(objective: QuestObjective, quest: Quest): any {
    return {
      condition: this.generateCompletionCondition(objective),
      message: `${objective.description} completed!`,
      sound: 'quest_step_complete',
      effects: ['ui_flash', 'experience_popup']
    };
  }

  private generateCompletionCondition(objective: QuestObjective): string {
    switch (objective.type) {
      case 'kill':
        return `enemies_killed["${objective.target}"] >= ${objective.quantity}`;
      case 'collect':
        return `inventory.count("${objective.target}") >= ${objective.quantity}`;
      case 'talk':
        return `dialogue_completed["${objective.target}"] == true`;
      case 'reach':
        return `locations_visited.includes("${objective.target}")`;
      default:
        return `objective["${objective.id}"].completed == true`;
    }
  }

  private generateStepHints(objective: QuestObjective, quest: Quest, campaign: Campaign): string[] {
    const hints: string[] = [];
    
    if (objective.location) {
      const location = campaign.locations.find(l => l.name === objective.location);
      if (location) {
        hints.push(`Look for this in ${location.name}`);
        if (location.description) {
          hints.push(location.description.substring(0, 100) + '...');
        }
      }
    }
    
    if (objective.type === 'talk') {
      const npc = campaign.npcs.find(n => n.name === objective.target);
      if (npc) {
        hints.push(`${npc.name} can be found in ${npc.location}`);
      }
    }
    
    return hints;
  }

  private generateStepTracking(objective: QuestObjective): any {
    return {
      trackProgress: objective.quantity > 1,
      showOnMap: !!objective.location,
      showDistance: objective.type === 'reach',
      updateFrequency: objective.type === 'collect' ? 'immediate' : 'on_completion'
    };
  }

  // Additional helper methods
  private processQuestLocations(quest: Quest, campaign: Campaign): void {
    quest.objectives.forEach(objective => {
      if (objective.location) {
        const location = campaign.locations.find(l => l.name === objective.location);
        if (location && !this.questLocations.has(location.id)) {
          const questLocation: QuestLocation = {
            id: location.id,
            name: location.name,
            type: this.determineLocationType(location, quest),
            radius: this.calculateLocationRadius(location, objective),
            requirements: this.generateLocationRequirements(location, quest),
            discovery: {
              method: 'automatic',
              trigger: `quest["${quest.id}"].status == "active"`,
              hint: `${objective.description}`,
              reward: 'map_marker'
            }
          };
          
          this.questLocations.set(location.id, questLocation);
        }
      }
    });
  }

  private determineLocationType(location: any, quest: Quest): QuestLocation['type'] {
    if (quest.type === 'main') return 'destination';
    if (location.type === 'city') return 'hub';
    return 'waypoint';
  }

  private calculateLocationRadius(location: any, objective: QuestObjective): number {
    // Calculate interaction radius based on objective type
    switch (objective.type) {
      case 'reach': return 10; // Small radius for reaching specific spots
      case 'collect': return 50; // Medium radius for finding items
      case 'kill': return 100; // Large radius for combat encounters
      default: return 25;
    }
  }

  private generateLocationRequirements(location: any, quest: Quest): string[] {
    const requirements: string[] = [];
    
    if (quest.prerequisites.length > 0) {
      requirements.push(`quest["${quest.id}"].available == true`);
    }
    
    if (location.type === 'dungeon') {
      requirements.push('player.level >= 5');
      requirements.push('party.size >= 2');
    }
    
    return requirements;
  }

  private async generateQuestVariations(quest: Quest, campaign: Campaign): Promise<QuestVariation[]> {
    const variations: QuestVariation[] = [];
    
    // Create difficulty variations
    variations.push(await this.createDifficultyVariation(quest, 'easy'));
    variations.push(await this.createDifficultyVariation(quest, 'hard'));
    
    // Create seasonal variations if applicable
    if (quest.type === 'side') {
      variations.push(await this.createSeasonalVariation(quest, 'winter'));
    }
    
    return variations;
  }

  private async createDifficultyVariation(quest: Quest, difficulty: 'easy' | 'hard'): Promise<QuestVariation> {
    const multiplier = difficulty === 'easy' ? 0.7 : 1.5;
    
    return {
      id: `${quest.id}_${difficulty}`,
      baseQuestId: quest.id,
      conditions: [`difficulty_setting == "${difficulty}"`],
      modifications: [
        {
          target: 'objective',
          type: 'modify',
          value: { quantity_multiplier: multiplier },
          description: `Adjust objective quantities by ${multiplier}x`
        },
        {
          target: 'reward',
          type: 'modify',
          value: { experience_multiplier: multiplier },
          description: `Adjust experience rewards by ${multiplier}x`
        }
      ],
      narrative: {
        reason: `${difficulty === 'easy' ? 'Simplified' : 'Enhanced'} version of the original quest`,
        dialogue_changes: [],
        outcome_changes: []
      }
    };
  }

  private async createSeasonalVariation(quest: Quest, season: string): Promise<QuestVariation> {
    return {
      id: `${quest.id}_${season}`,
      baseQuestId: quest.id,
      conditions: [`current_season == "${season}"`],
      modifications: [
        {
          target: 'location',
          type: 'modify',
          value: { weather: season, atmosphere: `${season}_themed` },
          description: `Add ${season} theming to quest locations`
        }
      ],
      narrative: {
        reason: `${season} seasonal variation`,
        dialogue_changes: [
          {
            npc: quest.giver || '',
            original: 'The weather is pleasant today.',
            replacement: `The ${season} weather affects everything.`,
            context: 'weather_comment'
          }
        ],
        outcome_changes: [`Quest takes place during ${season} season`]
      }
    };
  }

  private buildQuestProgression(processedQuests: ProcessedQuest[], questChains: QuestChain[]): QuestProgression {
    return {
      linear: this.createLinearProgression(processedQuests),
      branching: this.createBranchingProgression(processedQuests, questChains),
      gating: this.createProgressionGating(processedQuests),
      milestones: this.identifyProgressionMilestones(processedQuests)
    };
  }

  private createLinearProgression(processedQuests: ProcessedQuest[]): any {
    const mainQuests = processedQuests.filter(q => q.category === 'main_story');
    return {
      quests: mainQuests.map(q => q.id),
      order: 'sequential',
      blocking: true
    };
  }

  private createBranchingProgression(processedQuests: ProcessedQuest[], questChains: QuestChain[]): any {
    return {
      chains: questChains.map(chain => ({
        id: chain.id,
        quests: chain.quests,
        parallel: true
      }))
    };
  }

  private createProgressionGating(processedQuests: ProcessedQuest[]): any {
    return {
      level_gates: this.identifyLevelGates(processedQuests),
      story_gates: this.identifyStoryGates(processedQuests),
      area_gates: this.identifyAreaGates(processedQuests)
    };
  }

  private identifyLevelGates(processedQuests: ProcessedQuest[]): any[] {
    const levelGates = [];
    const levels = [5, 10, 15, 20];
    
    levels.forEach(level => {
      const questsAtLevel = processedQuests.filter(q => 
        q.conditions.some(c => c.check.includes(`>= ${level}`))
      );
      
      if (questsAtLevel.length > 0) {
        levelGates.push({
          level,
          quests: questsAtLevel.map(q => q.id),
          description: `Quests unlocked at level ${level}`
        });
      }
    });
    
    return levelGates;
  }

  private identifyStoryGates(processedQuests: ProcessedQuest[]): any[] {
    return processedQuests
      .filter(q => q.category === 'main_story')
      .map(q => ({
        quest: q.id,
        unlocks: processedQuests.filter(other => 
          other.conditions.some(c => c.check.includes(q.id))
        ).map(other => other.id)
      }))
      .filter(gate => gate.unlocks.length > 0);
  }

  private identifyAreaGates(processedQuests: ProcessedQuest[]): any[] {
    // Identify quests that unlock new areas
    return [];
  }

  private identifyProgressionMilestones(processedQuests: ProcessedQuest[]): any[] {
    return [
      {
        name: 'First Quest Complete',
        condition: 'completed_quests.length >= 1',
        rewards: ['tutorial_complete_bonus']
      },
      {
        name: 'Side Quest Explorer',
        condition: 'completed_side_quests.length >= 5',
        rewards: ['explorer_title', 'map_reveal_bonus']
      },
      {
        name: 'Main Story Progress',
        condition: 'completed_main_quests.length >= 3',
        rewards: ['story_progression_bonus']
      }
    ];
  }

  private analyzeQuestDependencies(processedQuests: ProcessedQuest[], campaign: Campaign): QuestDependency[] {
    const dependencies: QuestDependency[] = [];
    
    processedQuests.forEach(quest => {
      // Analyze conditions to find dependencies on other quests
      quest.conditions.forEach(condition => {
        if (condition.check.includes('quest[')) {
          const dependencyMatch = condition.check.match(/quest\["([^"]+)"\]/);
          if (dependencyMatch) {
            dependencies.push({
              id: `${quest.id}_depends_on_${dependencyMatch[1]}`,
              questId: quest.id,
              dependsOn: dependencyMatch[1],
              type: 'completion',
              required: true,
              description: `${quest.title} requires completion of ${dependencyMatch[1]}`
            });
          }
        }
      });
    });
    
    return dependencies;
  }

  private setupQuestTracking(processedQuests: ProcessedQuest[], options: QuestConversionOptions): QuestTracking {
    return {
      ui: {
        showProgress: true,
        showHints: options.addHints,
        showLocations: true,
        showRewards: options.generateRewards
      },
      persistence: {
        saveProgress: true,
        saveObjectives: true,
        saveVariables: true
      },
      notifications: {
        onQuestStart: true,
        onObjectiveComplete: true,
        onQuestComplete: true,
        onQuestFail: options.includeFailureConditions
      }
    };
  }

  private generateQuestJournal(processedQuests: ProcessedQuest[]): QuestJournal {
    const categories = this.generateJournalCategories(processedQuests);
    const filters = this.generateJournalFilters();
    const sorting = this.generateJournalSorting();
    
    const entries = processedQuests.map(quest => ({
      questId: quest.id,
      title: quest.title,
      description: quest.description,
      objectives: quest.steps.map(step => ({
        id: step.id,
        description: step.description,
        completed: false,
        optional: step.optional,
        hidden: step.hidden,
        progress: 0,
        maxProgress: step.quantity
      })),
      status: 'available',
      progress: 0,
      location: quest.steps.find(s => s.location)?.location || '',
      giver: '', // Would need to be populated from original quest
      timestamp: new Date(),
      notes: []
    }));
    
    return { entries, categories, filters, sorting };
  }

  private generateJournalCategories(processedQuests: ProcessedQuest[]): JournalCategory[] {
    const categorySet = new Set(processedQuests.map(q => q.category));
    
    return Array.from(categorySet).map(category => ({
      id: category,
      name: category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      icon: this.getCategoryIcon(category),
      color: this.getCategoryColor(category),
      filter: `category == "${category}"`
    }));
  }

  private getCategoryIcon(category: string): string {
    const icons: Record<string, string> = {
      'main_story': 'book',
      'side_activity': 'star',
      'combat': 'sword',
      'collection': 'bag',
      'character_development': 'person'
    };
    return icons[category] || 'quest';
  }

  private getCategoryColor(category: string): string {
    const colors: Record<string, string> = {
      'main_story': '#FFD700',
      'side_activity': '#87CEEB',
      'combat': '#FF4500',
      'collection': '#32CD32',
      'character_development': '#DDA0DD'
    };
    return colors[category] || '#808080';
  }

  private generateJournalFilters(): JournalFilter[] {
    return [
      {
        id: 'active',
        name: 'Active Quests',
        criteria: [{ field: 'status', operator: '==', value: 'active' }]
      },
      {
        id: 'completed',
        name: 'Completed Quests',
        criteria: [{ field: 'status', operator: '==', value: 'completed' }]
      },
      {
        id: 'main',
        name: 'Main Story',
        criteria: [{ field: 'category', operator: '==', value: 'main_story' }]
      },
      {
        id: 'near_completion',
        name: 'Nearly Complete',
        criteria: [{ field: 'progress', operator: '>', value: 0.8 }]
      }
    ];
  }

  private generateJournalSorting(): JournalSorting {
    return {
      default: 'priority',
      options: [
        { field: 'priority', label: 'Priority', direction: 'desc' },
        { field: 'date', label: 'Date Added', direction: 'desc' },
        { field: 'progress', label: 'Progress', direction: 'desc' },
        { field: 'title', label: 'Name', direction: 'asc' }
      ]
    };
  }

  private extractAllObjectives(processedQuests: ProcessedQuest[]): QuestObjective[] {
    return processedQuests.flatMap(quest => 
      quest.steps.map(step => ({
        id: step.id,
        description: step.description,
        type: step.type,
        target: step.target,
        quantity: step.quantity,
        location: step.location,
        optional: step.optional,
        hidden: step.hidden
      }))
    );
  }

  // Format-specific conversion methods
  private convertQuestSystemToXML(questSystem: QuestSystem): string {
    let xml = `<?xml version="1.0" encoding="UTF-8"?>\n<questSystem>\n`;
    
    xml += `  <quests>\n`;
    questSystem.quests.forEach(quest => {
      xml += `    <quest id="${quest.id}" category="${quest.category}" priority="${quest.priority}">\n`;
      xml += `      <title>${this.escapeXML(quest.title)}</title>\n`;
      xml += `      <description>${this.escapeXML(quest.description)}</description>\n`;
      xml += `    </quest>\n`;
    });
    xml += `  </quests>\n`;
    
    xml += `</questSystem>`;
    return xml;
  }

  private convertQuestSystemToLua(questSystem: QuestSystem): string {
    let lua = `-- Generated Quest System\nlocal QuestSystem = {}\n\n`;
    
    lua += `QuestSystem.quests = {\n`;
    questSystem.quests.forEach(quest => {
      lua += `  ["${quest.id}"] = {\n`;
      lua += `    title = "${quest.title.replace(/"/g, '\\"')}",\n`;
      lua += `    category = "${quest.category}",\n`;
      lua += `    priority = ${quest.priority},\n`;
      lua += `  },\n`;
    });
    lua += `}\n\nreturn QuestSystem`;
    
    return lua;
  }

  private convertQuestSystemToCSharp(questSystem: QuestSystem): string {
    let cs = `using System.Collections.Generic;\n\npublic class QuestSystem\n{\n`;
    
    cs += `    public static Dictionary<string, Quest> Quests = new Dictionary<string, Quest>\n    {\n`;
    questSystem.quests.forEach(quest => {
      cs += `        ["${quest.id}"] = new Quest\n        {\n`;
      cs += `            Id = "${quest.id}",\n`;
      cs += `            Title = "${quest.title.replace(/"/g, '\\"')}",\n`;
      cs += `            Category = "${quest.category}",\n`;
      cs += `            Priority = ${quest.priority}\n`;
      cs += `        },\n`;
    });
    cs += `    };\n}`;
    
    return cs;
  }

  private convertQuestSystemToGDScript(questSystem: QuestSystem): string {
    let gd = `# Generated Quest System\nextends Node\n\n`;
    
    gd += `var quests = {\n`;
    questSystem.quests.forEach(quest => {
      gd += `    "${quest.id}": {\n`;
      gd += `        "title": "${quest.title.replace(/"/g, '\\"')}",\n`;
      gd += `        "category": "${quest.category}",\n`;
      gd += `        "priority": ${quest.priority}\n`;
      gd += `    },\n`;
    });
    gd += `}`;
    
    return gd;
  }

  private escapeXML(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  private generateConditionCheck(prerequisite: any): string {
    switch (prerequisite.type) {
      case 'level':
        return `player.level >= ${prerequisite.value}`;
      case 'quest':
        return `quest["${prerequisite.target}"].status == "completed"`;
      case 'item':
        return `player.inventory.has("${prerequisite.target}")`;
      case 'location':
        return `player.visited_locations.includes("${prerequisite.target}")`;
      default:
        return 'true';
    }
  }

  private generateConditionFailMessage(prerequisite: any): string {
    switch (prerequisite.type) {
      case 'level':
        return `You need to be level ${prerequisite.value} or higher.`;
      case 'quest':
        return `You must complete "${prerequisite.target}" first.`;
      case 'item':
        return `You need "${prerequisite.target}" to proceed.`;
      case 'location':
        return `You must visit "${prerequisite.target}" first.`;
      default:
        return 'Requirements not met.';
    }
  }

  private generateProgressiveSteps(steps: QuestStep[], quest: ProcessedQuest): QuestStep[] {
    // Generate intermediate progress steps for long objectives
    const progressiveSteps: QuestStep[] = [];
    
    steps.forEach(step => {
      if (step.quantity > 5) {
        const milestones = [
          Math.floor(step.quantity * 0.25),
          Math.floor(step.quantity * 0.5),
          Math.floor(step.quantity * 0.75)
        ];
        
        milestones.forEach((milestone, index) => {
          if (milestone > 0) {
            progressiveSteps.push({
              ...step,
              id: `${step.id}_milestone_${index + 1}`,
              description: `${step.description} (${milestone}/${step.quantity})`,
              quantity: milestone,
              optional: true,
              type: 'milestone'
            });
          }
        });
      }
    });
    
    return progressiveSteps;
  }

  private generateHintSteps(quest: ProcessedQuest, campaign: Campaign): QuestStep[] {
    return [{
      id: `${quest.id}_hint`,
      description: `Learn more about: ${quest.title}`,
      type: 'investigate',
      target: quest.id,
      quantity: 1,
      optional: true,
      hidden: false,
      conditions: [],
      triggers: [`quest["${quest.id}"].status == "available"`],
      completion: {
        condition: `quest["${quest.id}"].hints_discovered >= 1`,
        message: 'You have a better understanding of what needs to be done.',
        sound: 'hint_discovered',
        effects: ['journal_update']
      },
      hints: ['Ask around town for more information', 'Check your journal for clues'],
      tracking: {
        trackProgress: false,
        showOnMap: false,
        showDistance: false,
        updateFrequency: 'on_completion'
      }
    }];
  }
}