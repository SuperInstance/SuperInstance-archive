// Core D&D Campaign Types
export interface Campaign {
  id: string;
  name: string;
  description: string;
  setting: string;
  theme: string;
  genre: string;
  title: string;
  sessions: Session[];
  characters: Character[];
  npcs: NPC[];
  locations: Location[];
  quests: Quest[];
  items: Item[];
  encounters: Encounter[];
  scenes?: any[];
  maps?: any[];
  currentArc?: string;
  worldbuilding: Worldbuilding;
  mechanics: CampaignMechanics;
  notes: string[];
  assets: Asset[];
}

export interface Session {
  id: string;
  number: number;
  title: string;
  date: Date;
  duration: number; // minutes
  summary: string;
  events: SessionEvent[];
  dialogue: DialogueEntry[];
  combats: CombatEncounter[];
  discoveries: Discovery[];
  characterDevelopment: CharacterDevelopment[];
  plotAdvancement: PlotPoint[];
}

export interface Character {
  id: string;
  name: string;
  race: string;
  class: string;
  level: number;
  background: string;
  personality: PersonalityTraits;
  backstory: string;
  goals: string[];
  relationships: Relationship[];
  stats: CharacterStats;
  abilities: Ability[];
  inventory: Item[];
  progression: LevelProgression[];
  voiceLines: string[];
  characterArc: CharacterArc;
  type?: string;
  importance?: string;
}

export interface NPC {
  id: string;
  name: string;
  role: 'quest_giver' | 'merchant' | 'ally' | 'enemy' | 'neutral' | 'companion';
  race: string;
  occupation: string;
  location: string;
  personality: PersonalityTraits;
  motivations: string[];
  relationships: Relationship[];
  dialogue: DialogueTree;
  quests: string[];
  behavior: BehaviorTree;
  appearance: AppearanceDescription;
  voice: VoiceCharacteristics;
  schedule: NPCSchedule[];
}

export interface Location {
  id: string;
  name: string;
  type: 'city' | 'dungeon' | 'wilderness' | 'building' | 'landmark' | 'plane';
  description: string;
  atmosphere: string;
  connections: LocationConnection[];
  features: LocationFeature[];
  npcs: string[];
  encounters: string[];
  secrets: Secret[];
  levelDesign: LevelDesignData;
  ambience: AmbienceSettings;
}

export interface Quest {
  id: string;
  title: string;
  type: 'main' | 'side' | 'personal' | 'fetch' | 'kill' | 'escort' | 'puzzle';
  description: string;
  objectives: QuestObjective[];
  prerequisites: QuestPrerequisite[];
  rewards: QuestReward[];
  giver: string; // NPC ID
  status: 'available' | 'active' | 'completed' | 'failed' | 'abandoned';
  priority: number;
  timeLimit?: number;
  consequences: QuestConsequence[];
  branches: QuestBranch[];
}

// Game Development Conversion Types
export interface GameProject {
  id: string;
  name: string;
  engine: 'unity' | 'godot' | 'unreal' | 'custom';
  genre: GameGenre;
  platform: Platform[];
  sourceData: Campaign;
  narrative: NarrativeStructure;
  gameplay: GameplayMechanics;
  technical: TechnicalSpecs;
  assets: AssetRequirements;
  monetization: MonetizationPlan;
  testing: TestingFramework;
  timeline: DevelopmentTimeline;
}

export interface NarrativeStructure {
  mainStory: StoryAct[];
  sideQuests: Quest[];
  dialogueTrees: DialogueTree[];
  characterArcs: CharacterArc[];
  worldLore: WorldLore;
  cutscenes: CutsceneScript[];
  narrativeChoices: Choice[];
}

export interface DialogueTree {
  id: string;
  npcId: string;
  rootNode: DialogueNode;
  conditions: DialogueCondition[];
  variables: DialogueVariable[];
  branches: DialogueBranch[];
}

export interface DialogueNode {
  id: string;
  speaker: string;
  text: string;
  emotion: string;
  animation: string;
  options: DialogueOption[];
  conditions: string[];
  consequences: string[];
  audioFile?: string;
  subtitles: string;
}

export interface QuestSystem {
  quests: ProcessedQuest[];
  objectives: QuestObjective[];
  progression: QuestProgression;
  dependencies: QuestDependency[];
  rewards: QuestRewardSystem;
  tracking: QuestTracking;
}

export interface ProcessedQuest {
  id: string;
  title: string;
  category: string;
  description: string;
  steps: QuestStep[];
  triggers: QuestTrigger[];
  conditions: QuestCondition[];
  rewards: QuestReward[];
  failureConditions: string[];
  timeConstraints: TimeConstraint;
  priority: number;
}

export interface NPCBehavior {
  id: string;
  npcId: string;
  behaviorTree: BehaviorNode;
  states: NPCState[];
  transitions: StateTransition[];
  reactions: ReactionTrigger[];
  interactions: InteractionType[];
  pathfinding: PathfindingData;
  combat: CombatBehavior;
}

export interface LevelDesign {
  id: string;
  name: string;
  type: LevelType;
  layout: LevelLayout;
  geometry: GeometryData;
  gameplay: GameplayElements;
  narrative: NarrativeElements;
  technical: TechnicalConstraints;
  flow: PlayerFlow;
  pacing: PacingCurve;
}

export interface CombatSystem {
  type: CombatType;
  mechanics: CombatMechanic[];
  abilities: CombatAbility[];
  stats: StatSystem;
  progression: ProgressionSystem;
  balancing: BalanceParameters;
  ai: CombatAI;
  feedback: FeedbackSystem;
}

export interface AssetRequirements {
  models: ModelRequirement[];
  textures: TextureRequirement[];
  audio: AudioRequirement[];
  animations: AnimationRequirement[];
  ui: UIRequirement[];
  effects: EffectRequirement[];
  environments: EnvironmentRequirement[];
  characters: CharacterAsset[];
}

export interface EngineTemplate {
  engine: 'unity' | 'godot' | 'unreal';
  version: string;
  projectStructure: ProjectStructure;
  scripts: ScriptTemplate[];
  scenes: SceneTemplate[];
  prefabs: PrefabTemplate[];
  systems: SystemTemplate[];
  build: BuildConfiguration;
}

export interface PlaytestingPlan {
  phases: TestingPhase[];
  metrics: TestingMetric[];
  feedback: FeedbackCategory[];
  automation: AutomatedTest[];
  participants: TesterProfile[];
  scenarios: TestScenario[];
  reporting: ReportingSystem;
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  category: AchievementCategory;
  type: AchievementType;
  requirements: AchievementRequirement[];
  rewards: AchievementReward[];
  rarity: AchievementRarity;
  hidden: boolean;
  progression: ProgressionData;
}

export interface SaveSystem {
  format: SaveFormat;
  structure: SaveStructure;
  compression: CompressionSettings;
  encryption: EncryptionSettings;
  versioning: VersioningSystem;
  cloud: CloudSaveSettings;
  checkpoints: CheckpointSystem;
  validation: ValidationRules;
}

export interface MonetizationModel {
  type: MonetizationType[];
  primary_model: MonetizationType;
  pricing: PricingStrategy;
  content: ContentStrategy;
  analytics: MonetizationAnalytics;
  compliance: ComplianceRequirements;
  platforms: PlatformMonetization[];
}

export interface PricingStrategy {
  base_price?: number;
  currency: string;
  regional_pricing: any[];
  discount_strategy: any;
  subscription_tiers?: any[];
  microtransaction_ranges: any[];
  psychological_pricing: any;
  competitive_analysis: any;
}

export interface ContentStrategy {
  content_categories: any[];
  release_schedule: any;
  dlc_roadmap: any[];
  seasonal_content: any[];
  user_generated_content: any;
  content_lifecycle: any;
}

export interface MonetizationAnalytics {
  kpis: any[];
  tracking_events: any[];
  reporting_schedule: any;
  segmentation_strategy: any;
  ab_testing_framework: any;
  revenue_attribution: any;
}

export interface ComplianceRequirements {
  regional_regulations: any[];
  age_restrictions: any[];
  gambling_compliance: any;
  data_protection: any;
  platform_policies: any[];
}

export interface PlatformMonetization {
  platform: string;
  revenue_share: number;
  platform_features: any[];
  integration_requirements: string[];
  certification_process: string;
}

// Supporting Types
export interface PersonalityTraits {
  traits: string[];
  ideals: string[];
  bonds: string[];
  flaws: string[];
  alignment: string;
  temperament: string;
  speechPattern: string;
  quirks: string[];
}

export interface Relationship {
  targetId: string;
  type: 'ally' | 'enemy' | 'neutral' | 'romantic' | 'family' | 'mentor';
  strength: number; // -100 to 100
  history: string;
  dynamics: string[];
}

export interface CharacterStats {
  attributes: Record<string, number>;
  skills: Record<string, number>;
  saves: Record<string, number>;
  hitPoints: { current: number; maximum: number };
  armorClass: number;
  speed: number;
  proficiencyBonus: number;
}

export interface BehaviorTree {
  rootNode: BehaviorNode;
  variables: BehaviorVariable[];
  conditions: BehaviorCondition[];
}

export interface BehaviorNode {
  id: string;
  type: 'selector' | 'sequence' | 'action' | 'condition' | 'decorator';
  name: string;
  children: BehaviorNode[];
  parameters: Record<string, any>;
  priority: number;
}

export interface LocationConnection {
  targetId: string;
  type: 'path' | 'portal' | 'door' | 'transition';
  requirements: string[];
  description: string;
}

export interface QuestObjective {
  id: string;
  description: string;
  type: 'kill' | 'collect' | 'talk' | 'reach' | 'protect' | 'discover';
  target: string;
  quantity: number;
  location?: string;
  optional: boolean;
  hidden: boolean;
}

export interface StoryAct {
  id: string;
  title: string;
  description: string;
  scenes: StoryScene[];
  climax: string;
  resolution: string;
  themes: string[];
}

export interface GameplayMechanics {
  core: CoreMechanic[];
  progression: ProgressionMechanic[];
  combat: CombatMechanic[];
  exploration: ExplorationMechanic[];
  social: SocialMechanic[];
  crafting?: CraftingMechanic[];
  economy?: EconomyMechanic[];
}

export interface TechnicalSpecs {
  targetPlatforms: Platform[];
  requirements: SystemRequirement[];
  performance: PerformanceTarget[];
  graphics: GraphicsSettings;
  audio: AudioSettings;
  networking?: NetworkingSpecs;
  analytics: AnalyticsSpecs;
}

export interface DevelopmentTimeline {
  phases: DevelopmentPhase[];
  milestones: Milestone[];
  resources: ResourceAllocation[];
  dependencies: PhaseDependency[];
  risks: RiskAssessment[];
}

// Enums and Constants
export type GameGenre = 'rpg' | 'action' | 'adventure' | 'strategy' | 'simulation' | 'puzzle' | 'platform';
export type Platform = 'pc' | 'mobile' | 'console' | 'web' | 'vr' | 'ar';
export type CombatType = 'turn_based' | 'real_time' | 'hybrid' | 'tactical' | 'action';
export type LevelType = 'linear' | 'hub' | 'open_world' | 'dungeon' | 'arena' | 'puzzle';
export type MonetizationType = 'premium' | 'freemium' | 'subscription' | 'ads' | 'dlc' | 'cosmetics';
export type AchievementCategory = 'story' | 'exploration' | 'combat' | 'social' | 'collection' | 'skill';
export type AchievementType = 'single' | 'progressive' | 'secret' | 'seasonal' | 'multiplayer';
export type AchievementRarity = 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
export type SaveFormat = 'json' | 'binary' | 'xml' | 'database';

// Additional interfaces for comprehensive typing
export interface SessionEvent {
  id: string;
  type: string;
  timestamp: Date;
  description: string;
  participants: string[];
  location?: string;
  consequences: string[];
}

export interface DialogueEntry {
  speaker: string;
  text: string;
  context: string;
  emotion?: string;
  timestamp: Date;
}

export interface CombatEncounter {
  id: string;
  enemies: string[];
  location: string;
  difficulty: string;
  outcome: string;
  duration: number;
  tactics: string[];
}

export interface Discovery {
  type: string;
  description: string;
  location: string;
  significance: string;
  impact: string[];
}

export interface CharacterDevelopment {
  characterId: string;
  type: string;
  description: string;
  impact: string[];
}

export interface PlotPoint {
  type: string;
  description: string;
  significance: string;
  consequences: string[];
}

export interface Ability {
  name: string;
  description: string;
  type: string;
  uses: string;
  level: number;
}

export interface Item {
  id: string;
  name: string;
  type: string;
  rarity: string;
  description: string;
  properties: Record<string, any>;
  value: number;
}

export interface LevelProgression {
  level: number;
  experience: number;
  features: string[];
  abilityScoreImprovements: Record<string, number>;
}

export interface CharacterArc {
  phases: ArcPhase[];
  growth: GrowthMoment[];
  conflicts: ConflictMoment[];
  resolution: string;
}

export interface ArcPhase {
  name: string;
  description: string;
  goals: string[];
  challenges: string[];
}

export interface GrowthMoment {
  description: string;
  trigger: string;
  impact: string;
}

export interface ConflictMoment {
  description: string;
  type: string;
  resolution: string;
}

export interface VoiceCharacteristics {
  pitch: string;
  tone: string;
  accent: string;
  pace: string;
  volume: string;
}

export interface AppearanceDescription {
  physicalTraits: string[];
  clothing: string[];
  accessories: string[];
  mannerisms: string[];
}

export interface NPCSchedule {
  time: string;
  location: string;
  activity: string;
  interaction: boolean;
}

export interface LocationFeature {
  name: string;
  description: string;
  interactive: boolean;
  properties: Record<string, any>;
}

export interface Secret {
  description: string;
  trigger: string;
  reward?: string;
  hint?: string;
}

export interface LevelDesignData {
  layout: string;
  paths: string[];
  encounters: string[];
  secrets: string[];
  lighting: string;
  atmosphere: string;
}

export interface AmbienceSettings {
  sounds: string[];
  music: string;
  lighting: string;
  weather?: string;
  effects: string[];
}

export interface QuestPrerequisite {
  type: string;
  target: string;
  value?: any;
}

export interface QuestReward {
  type: string;
  item?: string;
  experience?: number;
  gold?: number;
  reputation?: Record<string, number>;
}

export interface QuestConsequence {
  condition: string;
  effect: string;
  permanent: boolean;
}

export interface QuestBranch {
  condition: string;
  outcome: string;
  followup?: string;
}

export interface Encounter {
  id: string;
  type: string;
  location: string;
  participants: string[];
  description: string;
  outcome: string;
}

export interface Worldbuilding {
  history: HistoricalEvent[];
  politics: PoliticalStructure[];
  religion: Religion[];
  culture: CulturalAspect[];
  economy: EconomicSystem[];
  geography: GeographicFeature[];
}

export interface HistoricalEvent {
  date: string;
  title: string;
  description: string;
  impact: string[];
}

export interface PoliticalStructure {
  name: string;
  type: string;
  leaders: string[];
  territory: string[];
  relationships: Record<string, string>;
}

export interface Religion {
  name: string;
  deities: string[];
  beliefs: string[];
  practices: string[];
  followers: string[];
}

export interface CulturalAspect {
  group: string;
  values: string[];
  customs: string[];
  traditions: string[];
  taboos: string[];
}

export interface EconomicSystem {
  type: string;
  currency: string;
  trade: string[];
  resources: string[];
  guilds: string[];
}

export interface GeographicFeature {
  name: string;
  type: string;
  location: string;
  description: string;
  significance: string;
}

export interface CampaignMechanics {
  houseRules: string[];
  customSystems: string[];
  modifications: string[];
  balanceChanges: string[];
}

export interface Asset {
  id: string;
  type: string;
  name: string;
  path: string;
  description: string;
  metadata: Record<string, any>;
}

export interface DialogueCondition {
  id: string;
  type: string;
  parameters: Record<string, any>;
}

export interface DialogueVariable {
  name: string;
  type: string;
  value: any;
  scope: string;
}

export interface DialogueBranch {
  id: string;
  condition: string;
  targetNode: string;
}

export interface DialogueOption {
  text: string;
  targetNode: string;
  conditions: string[];
  consequences: string[];
  skillCheck?: SkillCheck;
}

export interface SkillCheck {
  skill: string;
  difficulty: number;
  successNode: string;
  failureNode: string;
}

export interface WorldLore {
  entries: LoreEntry[];
  categories: string[];
  connections: LoreConnection[];
}

export interface LoreEntry {
  id: string;
  title: string;
  category: string;
  content: string;
  sources: string[];
}

export interface LoreConnection {
  from: string;
  to: string;
  relationship: string;
}

export interface CutsceneScript {
  id: string;
  trigger: string;
  duration: number;
  shots: CutsceneShot[];
  audio: AudioTrack[];
  objectives: string[];
}

export interface CutsceneShot {
  duration: number;
  camera: CameraMovement;
  characters: CharacterAction[];
  effects: VisualEffect[];
}

export interface CameraMovement {
  type: string;
  start: Position3D;
  end: Position3D;
  focus: string;
}

export interface CharacterAction {
  characterId: string;
  animation: string;
  dialogue?: string;
  emotion: string;
}

export interface VisualEffect {
  type: string;
  parameters: Record<string, any>;
  timing: EffectTiming;
}

export interface EffectTiming {
  start: number;
  duration: number;
  fadeIn: number;
  fadeOut: number;
}

export interface Position3D {
  x: number;
  y: number;
  z: number;
}

export interface AudioTrack {
  file: string;
  volume: number;
  startTime: number;
  loop: boolean;
}

export interface Choice {
  id: string;
  context: string;
  options: ChoiceOption[];
  consequences: ChoiceConsequence[];
}

export interface ChoiceOption {
  text: string;
  requirements: string[];
  outcome: string;
}

export interface ChoiceConsequence {
  choice: string;
  immediate: string[];
  longTerm: string[];
}