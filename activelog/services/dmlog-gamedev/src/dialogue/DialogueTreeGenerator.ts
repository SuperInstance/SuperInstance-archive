import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { 
  Campaign, 
  NPC, 
  DialogueTree, 
  DialogueNode, 
  DialogueOption,
  DialogueCondition,
  DialogueVariable,
  Session,
  DialogueEntry,
  Quest
} from '../types';

export interface DialogueTreeOptions {
  maxDepth: number;
  branchingFactor: number;
  includeSkillChecks: boolean;
  includeVariables: boolean;
  generateAudioCues: boolean;
  localizationSupport: boolean;
  format: 'json' | 'yaml' | 'xml' | 'ink' | 'twine' | 'chatmapper' | 'articy';
}

export interface ConversationFlow {
  id: string;
  npcId: string;
  context: ConversationContext;
  nodes: ProcessedDialogueNode[];
  variables: DialogueVariable[];
  conditions: DialogueCondition[];
  branches: ConversationBranch[];
  metadata: ConversationMetadata;
}

export interface ConversationContext {
  location: string;
  questState: string[];
  relationshipLevel: number;
  previousConversations: string[];
  timeOfDay: string;
  seasonalEvents: string[];
  playerReputation: Record<string, number>;
}

export interface ProcessedDialogueNode {
  id: string;
  parentId?: string;
  speaker: string;
  text: string;
  audioFile?: string;
  animation: string;
  emotion: string;
  voice: VoiceSettings;
  timing: TimingSettings;
  options: DialogueOption[];
  conditions: string[];
  consequences: DialogueConsequence[];
  metadata: NodeMetadata;
}

export interface VoiceSettings {
  pitch: number; // -1.0 to 1.0
  speed: number; // 0.5 to 2.0
  volume: number; // 0.0 to 1.0
  emphasis: EmphasisMarker[];
  pause: PauseMarker[];
}

export interface EmphasisMarker {
  start: number;
  end: number;
  type: 'stress' | 'whisper' | 'shout' | 'sarcasm';
  intensity: number; // 0.0 to 1.0
}

export interface PauseMarker {
  position: number;
  duration: number; // seconds
  type: 'breath' | 'dramatic' | 'thought';
}

export interface TimingSettings {
  displaySpeed: number; // characters per second
  autoAdvance: boolean;
  pauseAfter: number; // seconds
  interruptible: boolean;
}

export interface DialogueConsequence {
  type: 'relationship' | 'variable' | 'quest' | 'item' | 'reputation' | 'mood';
  target: string;
  operation: 'set' | 'add' | 'multiply' | 'toggle';
  value: any;
  permanent: boolean;
  scope: 'local' | 'global' | 'session';
}

export interface ConversationBranch {
  id: string;
  triggerCondition: string;
  priority: number;
  rootNodeId: string;
  description: string;
  oneTime: boolean;
}

export interface ConversationMetadata {
  complexity: 'simple' | 'moderate' | 'complex';
  averageLength: number;
  branchingPaths: number;
  skillChecks: number;
  characterDevelopment: boolean;
  questImpact: string[];
  emotionalRange: string[];
  topics: string[];
}

export interface NodeMetadata {
  significance: 'low' | 'medium' | 'high';
  category: 'greeting' | 'quest' | 'lore' | 'personal' | 'farewell' | 'combat' | 'trade';
  mood: string;
  difficulty: number; // reading level
  culturalContext: string[];
  playerChoiceWeight: number; // impact of this choice
}

export interface SkillCheckNode extends ProcessedDialogueNode {
  skillCheck: {
    skill: string;
    difficulty: number;
    successNode: string;
    failureNode: string;
    criticalSuccess?: string;
    criticalFailure?: string;
    modifiers: SkillCheckModifier[];
  };
}

export interface SkillCheckModifier {
  condition: string;
  bonus: number;
  description: string;
}

export interface LocalizationData {
  nodeId: string;
  language: string;
  text: string;
  audioFile?: string;
  culturalNotes: string;
}

export class DialogueTreeGenerator extends EventEmitter {
  private outputPath: string;
  private conversations: Map<string, ConversationFlow> = new Map();
  private variables: Map<string, DialogueVariable> = new Map();
  private globalConditions: Map<string, DialogueCondition> = new Map();

  constructor(outputPath: string) {
    super();
    this.outputPath = outputPath;
    this.initializeGlobalVariables();
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.outputPath, { recursive: true });
      console.log('💬 Dialogue tree generator initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing dialogue tree generator:', error);
      throw error;
    }
  }

  private initializeGlobalVariables(): void {
    // Initialize common dialogue variables
    this.variables.set('player_name', {
      name: 'player_name',
      type: 'string',
      value: 'Hero',
      scope: 'global'
    });

    this.variables.set('current_location', {
      name: 'current_location',
      type: 'string',
      value: '',
      scope: 'session'
    });

    this.variables.set('party_reputation', {
      name: 'party_reputation',
      type: 'number',
      value: 0,
      scope: 'global'
    });

    this.variables.set('conversation_count', {
      name: 'conversation_count',
      type: 'number',
      value: 0,
      scope: 'global'
    });
  }

  public async generateDialogueTrees(
    campaign: Campaign,
    options: DialogueTreeOptions
  ): Promise<string[]> {
    console.log(`💬 Generating dialogue trees for campaign: ${campaign.name}`);

    const generatedFiles: string[] = [];

    // Process each NPC
    for (const npc of campaign.npcs) {
      try {
        const conversationFlow = await this.processNPCDialogue(npc, campaign, options);
        if (conversationFlow.nodes.length > 0) {
          this.conversations.set(npc.id, conversationFlow);
          
          const filePath = await this.exportConversationFlow(conversationFlow, options);
          generatedFiles.push(filePath);
          
          console.log(`✅ Generated dialogue tree for: ${npc.name}`);
        }
      } catch (error) {
        console.error(`Error processing NPC ${npc.name}:`, error);
      }
    }

    // Generate master conversation index
    const indexPath = await this.generateConversationIndex(campaign, options);
    generatedFiles.push(indexPath);

    // Generate localization files if requested
    if (options.localizationSupport) {
      const localizationFiles = await this.generateLocalizationFiles(options);
      generatedFiles.push(...localizationFiles);
    }

    console.log(`✅ Generated ${generatedFiles.length} dialogue tree files`);
    this.emit('trees-generated', { count: generatedFiles.length, files: generatedFiles });

    return generatedFiles;
  }

  private async processNPCDialogue(
    npc: NPC,
    campaign: Campaign,
    options: DialogueTreeOptions
  ): Promise<ConversationFlow> {
    // Extract dialogue data from sessions
    const npcDialogue = this.extractNPCDialogue(npc, campaign.sessions);
    
    // Build conversation context
    const context = this.buildConversationContext(npc, campaign);
    
    // Generate dialogue nodes
    const nodes = await this.generateDialogueNodes(npc, npcDialogue, context, options);
    
    // Create conversation branches
    const branches = this.createConversationBranches(npc, nodes, campaign);
    
    // Analyze metadata
    const metadata = this.analyzeConversationMetadata(nodes, branches);

    return {
      id: `conv_${npc.id}`,
      npcId: npc.id,
      context,
      nodes,
      variables: this.extractLocalVariables(npc, nodes),
      conditions: this.extractLocalConditions(npc, nodes),
      branches,
      metadata
    };
  }

  private extractNPCDialogue(npc: NPC, sessions: Session[]): DialogueEntry[] {
    const npcDialogue: DialogueEntry[] = [];
    
    sessions.forEach(session => {
      session.dialogue.forEach(dialogue => {
        if (dialogue.speaker.toLowerCase() === npc.name.toLowerCase()) {
          npcDialogue.push(dialogue);
        }
      });
    });
    
    return npcDialogue;
  }

  private buildConversationContext(npc: NPC, campaign: Campaign): ConversationContext {
    return {
      location: npc.location,
      questState: campaign.quests
        .filter(q => q.giver === npc.id)
        .map(q => `${q.id}:${q.status}`),
      relationshipLevel: this.calculateRelationshipLevel(npc, campaign),
      previousConversations: [],
      timeOfDay: 'any',
      seasonalEvents: [],
      playerReputation: this.calculatePlayerReputation(campaign)
    };
  }

  private async generateDialogueNodes(
    npc: NPC,
    dialogue: DialogueEntry[],
    context: ConversationContext,
    options: DialogueTreeOptions
  ): Promise<ProcessedDialogueNode[]> {
    const nodes: ProcessedDialogueNode[] = [];
    
    // Generate greeting node
    const greetingNode = await this.createGreetingNode(npc, context, options);
    nodes.push(greetingNode);
    
    // Process existing dialogue into nodes
    const topicNodes = await this.processDialogueIntoTopics(npc, dialogue, options);
    nodes.push(...topicNodes);
    
    // Generate quest-related nodes
    const questNodes = await this.generateQuestNodes(npc, context, options);
    nodes.push(...questNodes);
    
    // Generate farewell nodes
    const farewellNode = await this.createFarewellNode(npc, context, options);
    nodes.push(farewellNode);
    
    // Connect nodes with options
    this.connectNodesWithOptions(nodes, options);
    
    // Add skill check nodes if requested
    if (options.includeSkillChecks) {
      const skillCheckNodes = await this.addSkillCheckNodes(npc, nodes, options);
      nodes.push(...skillCheckNodes);
    }
    
    return nodes;
  }

  private async createGreetingNode(
    npc: NPC,
    context: ConversationContext,
    options: DialogueTreeOptions
  ): Promise<ProcessedDialogueNode> {
    const greetings = this.generateContextualGreetings(npc, context);
    const selectedGreeting = greetings[0] || `Hello there, traveler.`;
    
    return {
      id: `${npc.id}_greeting_01`,
      speaker: npc.name,
      text: selectedGreeting,
      audioFile: options.generateAudioCues ? `audio/${npc.id}_greeting_01.wav` : undefined,
      animation: this.selectAnimation(npc, 'greeting'),
      emotion: this.inferEmotionFromPersonality(npc, 'greeting'),
      voice: this.generateVoiceSettings(npc, 'greeting'),
      timing: this.generateTimingSettings('greeting'),
      options: [], // Will be populated by connectNodesWithOptions
      conditions: this.generateGreetingConditions(npc, context),
      consequences: [
        {
          type: 'variable',
          target: 'conversation_count',
          operation: 'add',
          value: 1,
          permanent: false,
          scope: 'global'
        }
      ],
      metadata: {
        significance: 'low',
        category: 'greeting',
        mood: npc.personality.temperament,
        difficulty: 1,
        culturalContext: this.getCulturalContext(npc),
        playerChoiceWeight: 0.1
      }
    };
  }

  private generateContextualGreetings(npc: NPC, context: ConversationContext): string[] {
    const greetings: string[] = [];
    const personality = npc.personality;
    
    // Base greeting based on personality
    if (personality.temperament === 'friendly') {
      greetings.push(`Well hello there! Good to see you.`);
      greetings.push(`Greetings, friend! What brings you my way?`);
    } else if (personality.temperament === 'suspicious') {
      greetings.push(`What do you want?`);
      greetings.push(`I don't know you. State your business.`);
    } else if (personality.temperament === 'scholarly') {
      greetings.push(`Ah, a visitor. How may I assist you?`);
      greetings.push(`Good day. I trust you come seeking knowledge?`);
    } else {
      greetings.push(`Hello.`);
      greetings.push(`Good day, traveler.`);
    }
    
    // Context-specific greetings
    if (context.questState.some(q => q.includes('active'))) {
      greetings.unshift(`Ah, you've returned! Any progress on that matter we discussed?`);
    }
    
    if (context.relationshipLevel > 5) {
      greetings.unshift(`My friend! Always a pleasure to see you.`);
    } else if (context.relationshipLevel < -3) {
      greetings.unshift(`You again... What is it this time?`);
    }
    
    return greetings;
  }

  private async processDialogueIntoTopics(
    npc: NPC,
    dialogue: DialogueEntry[],
    options: DialogueTreeOptions
  ): Promise<ProcessedDialogueNode[]> {
    const nodes: ProcessedDialogueNode[] = [];
    
    // Group dialogue by topic/context
    const topics = this.groupDialogueByTopic(dialogue);
    
    for (const [topic, entries] of topics.entries()) {
      const topicNodes = await this.createTopicNodes(npc, topic, entries, options);
      nodes.push(...topicNodes);
    }
    
    return nodes;
  }

  private groupDialogueByTopic(dialogue: DialogueEntry[]): Map<string, DialogueEntry[]> {
    const topics = new Map<string, DialogueEntry[]>();
    
    dialogue.forEach(entry => {
      const topic = this.extractTopicFromDialogue(entry);
      
      if (!topics.has(topic)) {
        topics.set(topic, []);
      }
      topics.get(topic)!.push(entry);
    });
    
    return topics;
  }

  private extractTopicFromDialogue(entry: DialogueEntry): string {
    const text = entry.text.toLowerCase();
    const context = entry.context?.toLowerCase() || '';
    
    // Topic inference based on keywords
    if (text.includes('quest') || context.includes('quest')) return 'quest';
    if (text.includes('shop') || text.includes('buy') || text.includes('sell')) return 'trade';
    if (text.includes('lore') || text.includes('history') || context.includes('lore')) return 'lore';
    if (text.includes('personal') || context.includes('personal')) return 'personal';
    if (text.includes('rumor') || text.includes('news')) return 'rumors';
    
    // Default topic
    return 'general';
  }

  private async createTopicNodes(
    npc: NPC,
    topic: string,
    entries: DialogueEntry[],
    options: DialogueTreeOptions
  ): Promise<ProcessedDialogueNode[]> {
    const nodes: ProcessedDialogueNode[] = [];
    
    entries.forEach((entry, index) => {
      const node: ProcessedDialogueNode = {
        id: `${npc.id}_${topic}_${index + 1}`,
        speaker: npc.name,
        text: this.enhanceDialogueText(entry.text, npc),
        audioFile: options.generateAudioCues ? `audio/${npc.id}_${topic}_${index + 1}.wav` : undefined,
        animation: this.selectAnimation(npc, topic),
        emotion: entry.emotion || this.inferEmotionFromText(entry.text),
        voice: this.generateVoiceSettings(npc, topic),
        timing: this.generateTimingSettings(topic),
        options: [],
        conditions: this.generateTopicConditions(topic, entry),
        consequences: this.generateTopicConsequences(topic, entry, npc),
        metadata: {
          significance: this.assessDialogueSignificance(entry),
          category: topic as any,
          mood: entry.emotion || 'neutral',
          difficulty: this.assessTextDifficulty(entry.text),
          culturalContext: this.getCulturalContext(npc),
          playerChoiceWeight: this.assessChoiceWeight(topic, entry)
        }
      };
      
      nodes.push(node);
    });
    
    return nodes;
  }

  private async generateQuestNodes(
    npc: NPC,
    context: ConversationContext,
    options: DialogueTreeOptions
  ): Promise<ProcessedDialogueNode[]> {
    const nodes: ProcessedDialogueNode[] = [];
    
    // Extract quest IDs from context
    const questIds = context.questState.map(qs => qs.split(':')[0]);
    
    questIds.forEach((questId, index) => {
      // Quest offer node
      const offerNode: ProcessedDialogueNode = {
        id: `${npc.id}_quest_offer_${questId}`,
        speaker: npc.name,
        text: this.generateQuestOfferText(npc, questId),
        audioFile: options.generateAudioCues ? `audio/${npc.id}_quest_offer_${questId}.wav` : undefined,
        animation: 'talk_serious',
        emotion: 'determined',
        voice: this.generateVoiceSettings(npc, 'quest'),
        timing: this.generateTimingSettings('quest'),
        options: [
          {
            text: 'I accept this quest.',
            targetNode: `${npc.id}_quest_accept_${questId}`,
            conditions: [],
            consequences: [
              {
                type: 'quest',
                target: questId,
                operation: 'set',
                value: 'active',
                permanent: true,
                scope: 'global'
              }
            ]
          },
          {
            text: 'I need to think about it.',
            targetNode: `${npc.id}_quest_defer_${questId}`,
            conditions: [],
            consequences: []
          }
        ],
        conditions: [`quest_${questId}_status != "completed"`],
        consequences: [],
        metadata: {
          significance: 'high',
          category: 'quest',
          mood: 'serious',
          difficulty: 3,
          culturalContext: this.getCulturalContext(npc),
          playerChoiceWeight: 0.8
        }
      };
      
      nodes.push(offerNode);
      
      // Quest completion node
      const completionNode: ProcessedDialogueNode = {
        id: `${npc.id}_quest_complete_${questId}`,
        speaker: npc.name,
        text: this.generateQuestCompletionText(npc, questId),
        audioFile: options.generateAudioCues ? `audio/${npc.id}_quest_complete_${questId}.wav` : undefined,
        animation: 'talk_happy',
        emotion: 'grateful',
        voice: this.generateVoiceSettings(npc, 'quest_complete'),
        timing: this.generateTimingSettings('quest_complete'),
        options: [
          {
            text: 'You\'re welcome.',
            targetNode: `${npc.id}_farewell_01`,
            conditions: [],
            consequences: [
              {
                type: 'relationship',
                target: npc.id,
                operation: 'add',
                value: 2,
                permanent: true,
                scope: 'global'
              }
            ]
          }
        ],
        conditions: [`quest_${questId}_status == "completed"`],
        consequences: [
          {
            type: 'quest',
            target: questId,
            operation: 'set',
            value: 'rewarded',
            permanent: true,
            scope: 'global'
          }
        ],
        metadata: {
          significance: 'high',
          category: 'quest',
          mood: 'grateful',
          difficulty: 2,
          culturalContext: this.getCulturalContext(npc),
          playerChoiceWeight: 0.6
        }
      };
      
      nodes.push(completionNode);
    });
    
    return nodes;
  }

  private async createFarewellNode(
    npc: NPC,
    context: ConversationContext,
    options: DialogueTreeOptions
  ): Promise<ProcessedDialogueNode> {
    const farewells = this.generateContextualFarewells(npc, context);
    const selectedFarewell = farewells[0] || `Farewell, traveler.`;
    
    return {
      id: `${npc.id}_farewell_01`,
      speaker: npc.name,
      text: selectedFarewell,
      audioFile: options.generateAudioCues ? `audio/${npc.id}_farewell_01.wav` : undefined,
      animation: this.selectAnimation(npc, 'farewell'),
      emotion: this.inferEmotionFromPersonality(npc, 'farewell'),
      voice: this.generateVoiceSettings(npc, 'farewell'),
      timing: this.generateTimingSettings('farewell'),
      options: [], // End conversation
      conditions: [],
      consequences: [
        {
          type: 'variable',
          target: 'last_conversation_npc',
          operation: 'set',
          value: npc.id,
          permanent: false,
          scope: 'session'
        }
      ],
      metadata: {
        significance: 'low',
        category: 'farewell',
        mood: npc.personality.temperament,
        difficulty: 1,
        culturalContext: this.getCulturalContext(npc),
        playerChoiceWeight: 0.1
      }
    };
  }

  private generateContextualFarewells(npc: NPC, context: ConversationContext): string[] {
    const farewells: string[] = [];
    const personality = npc.personality;
    
    if (personality.temperament === 'friendly') {
      farewells.push(`Take care, friend! Come back anytime.`);
      farewells.push(`Safe travels! I hope to see you again soon.`);
    } else if (personality.temperament === 'formal') {
      farewells.push(`Good day to you. May your journey be prosperous.`);
      farewells.push(`Until we meet again, fare thee well.`);
    } else {
      farewells.push(`Goodbye.`);
      farewells.push(`Until next time.`);
    }
    
    return farewells;
  }

  private connectNodesWithOptions(nodes: ProcessedDialogueNode[], options: DialogueTreeOptions): void {
    // Create a topic-based navigation system
    const topicNodes = this.groupNodesByCategory(nodes);
    
    // Add options to greeting node
    const greetingNode = nodes.find(n => n.metadata.category === 'greeting');
    if (greetingNode) {
      greetingNode.options = [];
      
      // Add options for each topic
      for (const [category, categoryNodes] of topicNodes.entries()) {
        if (category !== 'greeting' && category !== 'farewell' && categoryNodes.length > 0) {
          greetingNode.options.push({
            text: this.generateTopicOptionText(category),
            targetNode: categoryNodes[0].id,
            conditions: this.generateTopicConditions(category),
            consequences: []
          });
        }
      }
      
      // Add farewell option
      const farewellNode = nodes.find(n => n.metadata.category === 'farewell');
      if (farewellNode) {
        greetingNode.options.push({
          text: 'I should be going.',
          targetNode: farewellNode.id,
          conditions: [],
          consequences: []
        });
      }
    }
    
    // Connect topic nodes to each other and back to main menu
    this.connectTopicNodes(nodes, topicNodes, options);
  }

  private groupNodesByCategory(nodes: ProcessedDialogueNode[]): Map<string, ProcessedDialogueNode[]> {
    const grouped = new Map<string, ProcessedDialogueNode[]>();
    
    nodes.forEach(node => {
      const category = node.metadata.category;
      if (!grouped.has(category)) {
        grouped.set(category, []);
      }
      grouped.get(category)!.push(node);
    });
    
    return grouped;
  }

  private connectTopicNodes(
    allNodes: ProcessedDialogueNode[],
    topicNodes: Map<string, ProcessedDialogueNode[]>,
    options: DialogueTreeOptions
  ): void {
    for (const [category, nodes] of topicNodes.entries()) {
      if (category === 'greeting' || category === 'farewell') continue;
      
      nodes.forEach((node, index) => {
        // If not the last node in the topic, connect to next
        if (index < nodes.length - 1) {
          node.options.push({
            text: 'Continue...',
            targetNode: nodes[index + 1].id,
            conditions: [],
            consequences: []
          });
        } else {
          // Last node in topic - provide navigation options
          node.options.push({
            text: 'Is there anything else?',
            targetNode: allNodes.find(n => n.metadata.category === 'greeting')?.id || '',
            conditions: [],
            consequences: []
          });
        }
        
        // Add farewell option to all nodes
        const farewellNode = allNodes.find(n => n.metadata.category === 'farewell');
        if (farewellNode) {
          node.options.push({
            text: 'I should go.',
            targetNode: farewellNode.id,
            conditions: [],
            consequences: []
          });
        }
      });
    }
  }

  private async exportConversationFlow(
    flow: ConversationFlow,
    options: DialogueTreeOptions
  ): Promise<string> {
    const fileName = `${flow.npcId}_conversation.${this.getFileExtension(options.format)}`;
    const filePath = path.join(this.outputPath, fileName);
    
    let content: string;
    
    switch (options.format) {
      case 'json':
        content = JSON.stringify(flow, null, 2);
        break;
      case 'yaml':
        content = yaml.dump(flow, { indent: 2 });
        break;
      case 'xml':
        content = this.convertToXML(flow);
        break;
      case 'ink':
        content = await this.convertToInk(flow);
        break;
      case 'twine':
        content = await this.convertToTwine(flow);
        break;
      case 'chatmapper':
        content = await this.convertToChatMapper(flow);
        break;
      case 'articy':
        content = await this.convertToArticy(flow);
        break;
      default:
        content = JSON.stringify(flow, null, 2);
    }
    
    await fs.writeFile(filePath, content, 'utf-8');
    return filePath;
  }

  private async convertToInk(flow: ConversationFlow): Promise<string> {
    let ink = `=== ${flow.npcId}_conversation ===\n\n`;
    
    // Variables
    if (flow.variables.length > 0) {
      ink += `// Variables\n`;
      flow.variables.forEach(variable => {
        ink += `VAR ${variable.name} = ${JSON.stringify(variable.value)}\n`;
      });
      ink += `\n`;
    }
    
    // Main conversation flow
    const rootNode = flow.nodes.find(n => n.metadata.category === 'greeting');
    if (rootNode) {
      ink += await this.nodeToInk(rootNode, flow.nodes);
    }
    
    return ink;
  }

  private async nodeToInk(node: ProcessedDialogueNode, allNodes: ProcessedDialogueNode[]): Promise<string> {
    let ink = `= ${node.id}\n`;
    
    // Conditions
    if (node.conditions.length > 0) {
      ink += `{ ${node.conditions.join(' && ')} :\n`;
    }
    
    // Speaker and text
    ink += `${node.speaker}: ${node.text}\n`;
    
    // Options
    if (node.options.length > 0) {
      node.options.forEach(option => {
        ink += `* ${option.text}\n`;
        if (option.consequences.length > 0) {
          option.consequences.forEach(consequence => {
            if (consequence.type === 'variable') {
              ink += `  ~ ${consequence.target} ${consequence.operation === 'add' ? '+=' : '='} ${consequence.value}\n`;
            }
          });
        }
        ink += `  -> ${option.targetNode}\n`;
      });
    } else {
      ink += `-> END\n`;
    }
    
    if (node.conditions.length > 0) {
      ink += `}\n`;
    }
    
    ink += `\n`;
    
    return ink;
  }

  // Helper methods for dialogue tree generation
  private calculateRelationshipLevel(npc: NPC, campaign: Campaign): number {
    // Calculate based on character relationships and quest history
    let level = 0;
    
    // Check character relationships
    campaign.characters.forEach(character => {
      const relationship = character.relationships?.find(r => r.targetId === npc.id);
      if (relationship) {
        level += relationship.strength / 20; // Convert -100/100 to -5/5 range
      }
    });
    
    // Check quest completion history
    const npcQuests = campaign.quests.filter(q => q.giver === npc.id);
    npcQuests.forEach(quest => {
      if (quest.status === 'completed') level += 1;
      if (quest.status === 'failed') level -= 1;
    });
    
    return Math.max(-10, Math.min(10, level));
  }

  private calculatePlayerReputation(campaign: Campaign): Record<string, number> {
    const reputation: Record<string, number> = {
      general: 0,
      nobility: 0,
      merchants: 0,
      criminals: 0,
      scholars: 0
    };
    
    // Calculate based on completed quests and their consequences
    campaign.quests.forEach(quest => {
      if (quest.status === 'completed') {
        quest.consequences.forEach(consequence => {
          if (consequence.effect.toLowerCase().includes('reputation')) {
            reputation.general += 1;
          }
        });
      }
    });
    
    return reputation;
  }

  private generateVoiceSettings(npc: NPC, context: string): VoiceSettings {
    const personality = npc.personality;
    
    let pitch = 0;
    let speed = 1.0;
    let volume = 0.8;
    
    // Adjust based on personality
    if (personality.temperament === 'aggressive') {
      pitch += 0.2;
      speed += 0.2;
      volume += 0.1;
    } else if (personality.temperament === 'scholarly') {
      pitch -= 0.1;
      speed -= 0.1;
    } else if (personality.temperament === 'timid') {
      pitch -= 0.2;
      speed -= 0.2;
      volume -= 0.2;
    }
    
    // Adjust based on context
    if (context === 'quest') {
      volume += 0.1;
      speed -= 0.1; // More deliberate
    } else if (context === 'farewell') {
      speed -= 0.2;
      volume -= 0.1;
    }
    
    return {
      pitch: Math.max(-1.0, Math.min(1.0, pitch)),
      speed: Math.max(0.5, Math.min(2.0, speed)),
      volume: Math.max(0.0, Math.min(1.0, volume)),
      emphasis: [],
      pause: []
    };
  }

  private generateTimingSettings(context: string): TimingSettings {
    const baseSettings: TimingSettings = {
      displaySpeed: 50, // characters per second
      autoAdvance: false,
      pauseAfter: 2,
      interruptible: true
    };
    
    switch (context) {
      case 'greeting':
        baseSettings.displaySpeed = 60;
        baseSettings.autoAdvance = false;
        break;
      case 'quest':
        baseSettings.displaySpeed = 40; // Slower for important info
        baseSettings.pauseAfter = 3;
        break;
      case 'farewell':
        baseSettings.displaySpeed = 45;
        baseSettings.autoAdvance = true;
        break;
    }
    
    return baseSettings;
  }

  private selectAnimation(npc: NPC, context: string): string {
    const personalityAnimations = {
      'friendly': {
        'greeting': 'wave',
        'quest': 'talk_animated',
        'farewell': 'wave'
      },
      'formal': {
        'greeting': 'bow_slight',
        'quest': 'talk_serious',
        'farewell': 'bow_slight'
      },
      'aggressive': {
        'greeting': 'arms_crossed',
        'quest': 'point',
        'farewell': 'dismiss'
      }
    };
    
    const temperament = npc.personality.temperament;
    const animationSet = personalityAnimations[temperament as keyof typeof personalityAnimations];
    
    return animationSet?.[context as keyof typeof animationSet] || 'talk_neutral';
  }

  private inferEmotionFromPersonality(npc: NPC, context: string): string {
    const personality = npc.personality;
    
    if (context === 'greeting') {
      if (personality.temperament === 'friendly') return 'happy';
      if (personality.temperament === 'suspicious') return 'cautious';
      if (personality.temperament === 'scholarly') return 'curious';
    }
    
    return 'neutral';
  }

  private inferEmotionFromText(text: string): string {
    const lowercaseText = text.toLowerCase();
    
    if (lowercaseText.includes('!')) return 'excited';
    if (lowercaseText.includes('...')) return 'thoughtful';
    if (lowercaseText.includes('?')) return 'curious';
    if (lowercaseText.includes('danger') || lowercaseText.includes('careful')) return 'concerned';
    if (lowercaseText.includes('thank') || lowercaseText.includes('grateful')) return 'grateful';
    
    return 'neutral';
  }

  private getCulturalContext(npc: NPC): string[] {
    const context = [npc.race.toLowerCase()];
    
    if (npc.occupation) {
      context.push(npc.occupation.toLowerCase());
    }
    
    if (npc.location) {
      context.push(npc.location.toLowerCase().replace(/\s+/g, '_'));
    }
    
    return context;
  }

  // Additional helper methods would continue...
  // Due to length constraints, I'll provide the key structure and methods
  
  private getFileExtension(format: string): string {
    const extensions = {
      'json': 'json',
      'yaml': 'yml',
      'xml': 'xml',
      'ink': 'ink',
      'twine': 'tw2',
      'chatmapper': 'cmp',
      'articy': 'adf'
    };
    return extensions[format as keyof typeof extensions] || 'json';
  }

  private enhanceDialogueText(text: string, npc: NPC): string {
    // Add personality-based speech patterns
    let enhanced = text;
    
    // Add speech quirks based on personality
    if (npc.personality.quirks) {
      // This would apply character-specific speech patterns
    }
    
    return enhanced;
  }

  private generateGreetingConditions(npc: NPC, context: ConversationContext): string[] {
    const conditions = ['first_meeting != true'];
    
    if (context.relationshipLevel < 0) {
      conditions.push(`${npc.id}_relationship < 0`);
    }
    
    return conditions;
  }

  private generateTopicConditions(topic: string, entry?: DialogueEntry): string[] {
    const conditions: string[] = [];
    
    switch (topic) {
      case 'quest':
        conditions.push('player_level >= 1');
        break;
      case 'trade':
        conditions.push('player_gold > 0');
        break;
      case 'lore':
        conditions.push('player_intelligence >= 12');
        break;
    }
    
    return conditions;
  }

  private generateTopicConsequences(topic: string, entry: DialogueEntry, npc: NPC): DialogueConsequence[] {
    const consequences: DialogueConsequence[] = [];
    
    if (topic === 'personal') {
      consequences.push({
        type: 'relationship',
        target: npc.id,
        operation: 'add',
        value: 1,
        permanent: true,
        scope: 'global'
      });
    }
    
    return consequences;
  }

  private generateQuestOfferText(npc: NPC, questId: string): string {
    const personalityText = {
      'friendly': `I have a favor to ask of you, if you're willing.`,
      'formal': `I have a task that requires someone of your capabilities.`,
      'desperate': `Please, I need your help with something urgent.`,
      'business': `I have a proposition that could benefit us both.`
    };
    
    const temperament = npc.personality.temperament as keyof typeof personalityText;
    return personalityText[temperament] || personalityText.formal;
  }

  private generateQuestCompletionText(npc: NPC, questId: string): string {
    return `Excellent work! You've done exactly what I hoped for.`;
  }

  private generateTopicOptionText(category: string): string {
    const optionTexts = {
      'quest': 'Do you have any work for me?',
      'trade': 'What do you have for sale?',
      'lore': 'Tell me about this place.',
      'personal': 'How are you doing?',
      'rumors': 'Any interesting news?'
    };
    
    return optionTexts[category as keyof typeof optionTexts] || 'Let\'s talk.';
  }

  private assessDialogueSignificance(entry: DialogueEntry): 'low' | 'medium' | 'high' {
    if (entry.context?.toLowerCase().includes('important')) return 'high';
    if (entry.text.length > 100) return 'medium';
    return 'low';
  }

  private assessTextDifficulty(text: string): number {
    // Simple reading level assessment
    const words = text.split(/\s+/);
    const avgWordLength = words.reduce((sum, word) => sum + word.length, 0) / words.length;
    
    if (avgWordLength > 6) return 4;
    if (avgWordLength > 4) return 3;
    return 2;
  }

  private assessChoiceWeight(topic: string, entry: DialogueEntry): number {
    const weights = {
      'quest': 0.9,
      'personal': 0.7,
      'lore': 0.5,
      'trade': 0.4,
      'rumors': 0.3
    };
    
    return weights[topic as keyof typeof weights] || 0.5;
  }

  // Export format converters
  private convertToXML(flow: ConversationFlow): string {
    let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    xml += `<conversation id="${flow.id}" npc="${flow.npcId}">\n`;
    
    // Nodes
    xml += `  <nodes>\n`;
    flow.nodes.forEach(node => {
      xml += `    <node id="${node.id}" speaker="${this.escapeXML(node.speaker)}">\n`;
      xml += `      <text>${this.escapeXML(node.text)}</text>\n`;
      xml += `      <emotion>${node.emotion}</emotion>\n`;
      xml += `      <animation>${node.animation}</animation>\n`;
      
      if (node.options.length > 0) {
        xml += `      <options>\n`;
        node.options.forEach(option => {
          xml += `        <option target="${option.targetNode}">${this.escapeXML(option.text)}</option>\n`;
        });
        xml += `      </options>\n`;
      }
      
      xml += `    </node>\n`;
    });
    xml += `  </nodes>\n`;
    xml += `</conversation>`;
    
    return xml;
  }

  private escapeXML(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  private async convertToTwine(flow: ConversationFlow): Promise<string> {
    // Twine 2 format conversion would go here
    return `<!-- Twine conversation for ${flow.npcId} -->`;
  }

  private async convertToChatMapper(flow: ConversationFlow): Promise<string> {
    // ChatMapper format conversion would go here
    return `<!-- ChatMapper conversation for ${flow.npcId} -->`;
  }

  private async convertToArticy(flow: ConversationFlow): Promise<string> {
    // Articy Draft format conversion would go here
    return `<!-- Articy conversation for ${flow.npcId} -->`;
  }

  private async generateConversationIndex(campaign: Campaign, options: DialogueTreeOptions): Promise<string> {
    const index = {
      campaign: campaign.name,
      conversations: Array.from(this.conversations.keys()),
      generated_at: new Date().toISOString(),
      options: options
    };
    
    const indexPath = path.join(this.outputPath, 'conversation_index.json');
    await fs.writeFile(indexPath, JSON.stringify(index, null, 2));
    
    return indexPath;
  }

  private async generateLocalizationFiles(options: DialogueTreeOptions): Promise<string[]> {
    const localizationFiles: string[] = [];
    
    // Generate base localization file for all dialogue text
    const localizationData: LocalizationData[] = [];
    
    for (const flow of this.conversations.values()) {
      flow.nodes.forEach(node => {
        localizationData.push({
          nodeId: node.id,
          language: options.language,
          text: node.text,
          audioFile: node.audioFile,
          culturalNotes: ''
        });
      });
    }
    
    const locPath = path.join(this.outputPath, `localization_${options.language}.json`);
    await fs.writeFile(locPath, JSON.stringify(localizationData, null, 2));
    localizationFiles.push(locPath);
    
    return localizationFiles;
  }

  private extractLocalVariables(npc: NPC, nodes: ProcessedDialogueNode[]): DialogueVariable[] {
    const variables: DialogueVariable[] = [];
    
    // Extract variables specific to this NPC's conversation
    variables.push({
      name: `${npc.id}_relationship`,
      type: 'number',
      value: 0,
      scope: 'global'
    });
    
    variables.push({
      name: `${npc.id}_conversations`,
      type: 'number',
      value: 0,
      scope: 'global'
    });
    
    return variables;
  }

  private extractLocalConditions(npc: NPC, nodes: ProcessedDialogueNode[]): DialogueCondition[] {
    return [
      {
        id: `${npc.id}_met`,
        type: 'variable',
        parameters: { variable: `${npc.id}_conversations`, operator: '>', value: 0 }
      }
    ];
  }

  private createConversationBranches(npc: NPC, nodes: ProcessedDialogueNode[], campaign: Campaign): ConversationBranch[] {
    const branches: ConversationBranch[] = [];
    
    // Create main conversation branch
    branches.push({
      id: `${npc.id}_main`,
      triggerCondition: 'true',
      priority: 1,
      rootNodeId: nodes.find(n => n.metadata.category === 'greeting')?.id || nodes[0].id,
      description: 'Main conversation flow',
      oneTime: false
    });
    
    // Create quest-specific branches
    const questNodes = nodes.filter(n => n.metadata.category === 'quest');
    questNodes.forEach((questNode, index) => {
      branches.push({
        id: `${npc.id}_quest_${index}`,
        triggerCondition: `quest_available_${npc.id}`,
        priority: 10,
        rootNodeId: questNode.id,
        description: `Quest-related conversation branch`,
        oneTime: true
      });
    });
    
    return branches;
  }

  private analyzeConversationMetadata(nodes: ProcessedDialogueNode[], branches: ConversationBranch[]): ConversationMetadata {
    const complexity = nodes.length > 20 ? 'complex' : nodes.length > 10 ? 'moderate' : 'simple';
    const averageLength = nodes.reduce((sum, node) => sum + node.text.length, 0) / nodes.length;
    const branchingPaths = branches.length;
    const skillChecks = nodes.filter(n => n.conditions.length > 0).length;
    const characterDevelopment = nodes.some(n => n.metadata.category === 'personal');
    const questImpact = [...new Set(nodes.filter(n => n.metadata.category === 'quest').map(n => n.id))];
    const emotionalRange = [...new Set(nodes.map(n => n.emotion))];
    const topics = [...new Set(nodes.map(n => n.metadata.category))];
    
    return {
      complexity,
      averageLength,
      branchingPaths,
      skillChecks,
      characterDevelopment,
      questImpact,
      emotionalRange,
      topics
    };
  }

  private async addSkillCheckNodes(npc: NPC, nodes: ProcessedDialogueNode[], options: DialogueTreeOptions): Promise<ProcessedDialogueNode[]> {
    const skillCheckNodes: ProcessedDialogueNode[] = [];
    
    // Add persuasion check for certain dialogue options
    const persuasionNode: SkillCheckNode = {
      id: `${npc.id}_persuasion_check`,
      speaker: npc.name,
      text: `I'm not sure about that... you'll have to convince me.`,
      animation: 'talk_skeptical',
      emotion: 'skeptical',
      voice: this.generateVoiceSettings(npc, 'skill_check'),
      timing: this.generateTimingSettings('skill_check'),
      options: [],
      conditions: [],
      consequences: [],
      metadata: {
        significance: 'medium',
        category: 'personal',
        mood: 'skeptical',
        difficulty: 3,
        culturalContext: this.getCulturalContext(npc),
        playerChoiceWeight: 0.7
      },
      skillCheck: {
        skill: 'persuasion',
        difficulty: 15,
        successNode: `${npc.id}_persuasion_success`,
        failureNode: `${npc.id}_persuasion_failure`,
        modifiers: [
          {
            condition: `${npc.id}_relationship > 3`,
            bonus: 2,
            description: 'NPC likes you'
          }
        ]
      }
    };
    
    skillCheckNodes.push(persuasionNode as ProcessedDialogueNode);
    
    return skillCheckNodes;
  }
}