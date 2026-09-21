/**
 * Core Game Type Definitions
 * Empire building game with business simulation mechanics
 */

export interface Player {
  id: string;
  name: string;
  email?: string;
  avatar?: string;
  level: DifficultyLevel;
  
  // Financial Status
  cash: number;
  assets: number;
  liabilities: number;
  netWorth: number;
  creditScore: number;
  
  // Game Progress
  position: number; // Board position (Monopoly-style)
  turnOrder: number;
  roundsPlayed: number;
  
  // Career & Education
  career: CareerPath;
  education: EducationLevel;
  skills: PlayerSkills;
  
  // Business Portfolio
  companies: Company[];
  properties: Property[];
  equipment: Equipment[];
  contracts: Contract[];
  
  // Game Stats
  totalIncome: number;
  totalExpenses: number;
  passiveIncome: number;
  activeIncome: number;
  
  // Multiplayer
  isOnline: boolean;
  lastActive: Date;
  gameRoomId?: string;
}

export interface Company {
  id: string;
  name: string;
  type: CompanyType;
  industry: Industry;
  foundedDate: Date;
  
  // Financial
  revenue: number;
  expenses: number;
  profit: number;
  valuation: number;
  shares: number;
  sharesOwned: number; // By player
  
  // Operations
  employees: number;
  digitalTransformation: number; // 0-100% brick to digital
  productionCapacity: number;
  marketShare: number;
  
  // Equipment & Assets
  equipment: Equipment[];
  properties: Property[];
  
  // Status
  isPublic: boolean;
  ipoDate?: Date;
  isAcquired: boolean;
  acquiredBy?: string;
  
  // Development
  researchPoints: number;
  products: Product[];
  
  // Location & Operations
  headquarters: string;
  locations: string[];
}

export interface Equipment {
  id: string;
  name: string;
  type: EquipmentType;
  category: EquipmentCategory;
  
  // Financial
  purchasePrice: number;
  currentValue: number;
  depreciation: number;
  maintenanceCost: number;
  
  // Performance
  productivity: number;
  efficiency: number;
  reliability: number;
  
  // Lifecycle
  purchaseDate: Date;
  warranty: number; // months
  expectedLifespan: number; // years
  condition: number; // 0-100%
  
  // Specifications
  specifications: Record<string, any>;
  powerConsumption?: number;
  spaceRequired?: number;
  
  // Business Impact
  revenueGeneration: number;
  costSavings: number;
  digitalTransformationBonus: number;
}

export interface Property {
  id: string;
  name: string;
  type: PropertyType;
  address: string;
  
  // Financial
  purchasePrice: number;
  currentValue: number;
  marketValue: number;
  
  // Rental Details
  monthlyRent?: number;
  occupancyRate: number;
  tenants: Tenant[];
  
  // Physical Details
  squareFootage: number;
  floors: number;
  yearBuilt: number;
  condition: number; // 0-100%
  
  // Improvements
  improvements: PropertyImprovement[];
  totalImprovementCost: number;
  
  // Business Use
  businessUse: BusinessUseType;
  digitalInfrastructure: number; // 0-100% digital readiness
}

export interface Contract {
  id: string;
  title: string;
  type: ContractType;
  
  // Parties
  clientId: string;
  clientName: string;
  vendorId: string; // Player or company ID
  
  // Terms
  value: number;
  duration: number; // months
  startDate: Date;
  endDate: Date;
  
  // Payments
  paymentSchedule: PaymentSchedule;
  paymentsReceived: number;
  paymentsRemaining: number;
  
  // Performance
  deliverables: Deliverable[];
  milestones: Milestone[];
  performance: number; // 0-100%
  
  // Negotiation
  negotiatedTerms: NegotiatedTerm[];
  renegotiationOpportunity: boolean;
  
  // Risk
  riskLevel: RiskLevel;
  penalties: ContractPenalty[];
  bonuses: ContractBonus[];
}

export interface Product {
  id: string;
  name: string;
  type: ProductType;
  category: ProductCategory;
  
  // Development
  developmentStage: DevelopmentStage;
  developmentCost: number;
  timeToMarket: number; // months
  
  // Market
  targetMarket: string[];
  marketSize: number;
  competitorCount: number;
  marketShare: number;
  
  // Pricing
  costToManufacture: number;
  sellingPrice: number;
  marginPercent: number;
  
  // Performance
  qualityRating: number; // 0-100
  customerSatisfaction: number; // 0-100
  salesVolume: number;
  
  // Digital Transformation
  digitalFeatures: number; // 0-100%
  onlineChannel: boolean;
  subscriptionModel: boolean;
}

export interface GameBoard {
  id: string;
  name: string;
  size: number; // Number of spaces
  spaces: BoardSpace[];
  
  // Special Locations
  startSpace: number;
  jailSpace: number;
  freeSpaces: number[];
  
  // Economic Zones
  businessDistricts: BusinessDistrict[];
  industrialZones: IndustrialZone[];
  residentialAreas: ResidentialArea[];
}

export interface BoardSpace {
  id: number;
  name: string;
  type: SpaceType;
  
  // Monopoly-style Actions
  action: SpaceAction;
  cost?: number;
  rent?: number;
  
  // Business Opportunities
  businessOpportunity?: BusinessOpportunity;
  eventCard?: EventCard;
  
  // Location Properties
  district: string;
  zone: ZoneType;
  developmentLevel: number;
}

export interface CashflowStatement {
  playerId: string;
  month: number;
  year: number;
  
  // Income
  salary: number;
  businessIncome: number;
  passiveIncome: number;
  capitalGains: number;
  otherIncome: number;
  totalIncome: number;
  
  // Expenses
  taxes: number;
  livingExpenses: number;
  businessExpenses: number;
  debtService: number;
  otherExpenses: number;
  totalExpenses: number;
  
  // Cash Flow
  netCashFlow: number;
  cumulativeCashFlow: number;
  
  // Ratios
  savingsRate: number;
  debtToIncomeRatio: number;
  expenseRatio: number;
}

export interface GameSession {
  id: string;
  name: string;
  mode: GameMode;
  
  // Players
  players: Player[];
  maxPlayers: number;
  currentPlayerIndex: number;
  
  // Game State
  currentRound: number;
  currentTurn: number;
  gamePhase: GamePhase;
  isActive: boolean;
  isPaused: boolean;
  
  // Settings
  difficulty: DifficultyLevel;
  gameSpeed: GameSpeed;
  rules: GameRules;
  
  // Board & Economy
  board: GameBoard;
  economy: EconomyState;
  
  // Time Management
  createdAt: Date;
  startedAt?: Date;
  lastActivity: Date;
  estimatedDuration: number; // minutes
  
  // Multiplayer
  hostId: string;
  isPublic: boolean;
  password?: string;
  spectators: string[];
}

// Enums and Supporting Types

export enum DifficultyLevel {
  KID = 'kid',
  TEEN = 'teen',
  ADULT = 'adult',
  BUSINESS = 'business',
  MBA = 'mba'
}

export enum CareerPath {
  ASSEMBLER = 'assembler',
  EDUCATOR = 'educator',
  ENTREPRENEUR = 'entrepreneur',
  EXECUTIVE = 'executive',
  INVESTOR = 'investor',
  CONSULTANT = 'consultant'
}

export enum EducationLevel {
  HIGH_SCHOOL = 'high_school',
  ASSOCIATE = 'associate',
  BACHELOR = 'bachelor',
  MASTER = 'master',
  PHD = 'phd',
  MBA = 'mba'
}

export enum CompanyType {
  STARTUP = 'startup',
  SMALL_BUSINESS = 'small_business',
  CORPORATION = 'corporation',
  FRANCHISE = 'franchise',
  NONPROFIT = 'nonprofit'
}

export enum Industry {
  TECHNOLOGY = 'technology',
  MANUFACTURING = 'manufacturing',
  RETAIL = 'retail',
  EDUCATION = 'education',
  HEALTHCARE = 'healthcare',
  FINANCE = 'finance',
  REAL_ESTATE = 'real_estate',
  ENERGY = 'energy',
  TRANSPORTATION = 'transportation',
  ENTERTAINMENT = 'entertainment'
}

export enum EquipmentType {
  PRINTER = 'printer',
  SERVER = 'server',
  COMPUTER = 'computer',
  MACHINERY = 'machinery',
  VEHICLE = 'vehicle',
  FURNITURE = 'furniture',
  SOFTWARE = 'software'
}

export enum EquipmentCategory {
  PRODUCTION = 'production',
  IT_INFRASTRUCTURE = 'it_infrastructure',
  OFFICE = 'office',
  TRANSPORTATION = 'transportation',
  RESEARCH = 'research'
}

export enum PropertyType {
  OFFICE = 'office',
  WAREHOUSE = 'warehouse',
  RETAIL = 'retail',
  RESIDENTIAL = 'residential',
  MIXED_USE = 'mixed_use',
  LAND = 'land'
}

export enum ContractType {
  SERVICE = 'service',
  PRODUCT = 'product',
  CONSULTING = 'consulting',
  LICENSING = 'licensing',
  PARTNERSHIP = 'partnership',
  EDUCATION = 'education'
}

export enum GameMode {
  SINGLE_PLAYER = 'single_player',
  LOCAL_MULTIPLAYER = 'local_multiplayer',
  ONLINE_MULTIPLAYER = 'online_multiplayer',
  TUTORIAL = 'tutorial'
}

export enum GamePhase {
  SETUP = 'setup',
  PLAYING = 'playing',
  PAUSED = 'paused',
  COMPLETED = 'completed'
}

export enum GameSpeed {
  SLOW = 'slow',
  NORMAL = 'normal',
  FAST = 'fast',
  BLITZ = 'blitz'
}

export enum SpaceType {
  START = 'start',
  PROPERTY = 'property',
  BUSINESS = 'business',
  EVENT = 'event',
  TAX = 'tax',
  JAIL = 'jail',
  FREE_PARKING = 'free_parking',
  GO_TO_JAIL = 'go_to_jail'
}

export enum RiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  EXTREME = 'extreme'
}

// Supporting Interfaces

export interface PlayerSkills {
  leadership: number;
  negotiation: number;
  marketing: number;
  finance: number;
  technology: number;
  operations: number;
}

export interface Tenant {
  name: string;
  monthlyRent: number;
  leaseEndDate: Date;
  creditRating: number;
}

export interface PropertyImprovement {
  name: string;
  cost: number;
  valueIncrease: number;
  dateCompleted: Date;
}

export interface Deliverable {
  name: string;
  description: string;
  dueDate: Date;
  completed: boolean;
  qualityScore: number;
}

export interface Milestone {
  name: string;
  description: string;
  dueDate: Date;
  completed: boolean;
  paymentAmount: number;
}

export interface NegotiatedTerm {
  term: string;
  originalValue: any;
  negotiatedValue: any;
  impact: number; // -100 to +100
}

export interface ContractPenalty {
  condition: string;
  amount: number;
  triggered: boolean;
}

export interface ContractBonus {
  condition: string;
  amount: number;
  earned: boolean;
}

export interface BusinessOpportunity {
  type: string;
  description: string;
  cost: number;
  potentialReturn: number;
  riskLevel: RiskLevel;
  duration: number; // months
}

export interface EventCard {
  id: string;
  title: string;
  description: string;
  type: 'positive' | 'negative' | 'neutral';
  effect: GameEffect;
}

export interface GameEffect {
  type: 'money' | 'property' | 'skill' | 'reputation' | 'opportunity';
  amount: number;
  target?: string;
  duration?: number;
}

export interface EconomyState {
  gdpGrowth: number;
  inflationRate: number;
  unemploymentRate: number;
  interestRate: number;
  stockMarketIndex: number;
  realEstateIndex: number;
  
  // Business Cycles
  economicCycle: EconomicCycle;
  sectorPerformance: Record<Industry, number>;
  
  // Market Conditions
  creditAvailability: number;
  businessConfidence: number;
  consumerSpending: number;
}

export enum EconomicCycle {
  RECESSION = 'recession',
  RECOVERY = 'recovery',
  EXPANSION = 'expansion',
  PEAK = 'peak'
}

export interface GameRules {
  startingCash: number;
  salaryAmount: number;
  maxCompanies: number;
  maxProperties: number;
  bankruptcyThreshold: number;
  winConditions: WinCondition[];
}

export interface WinCondition {
  type: 'net_worth' | 'passive_income' | 'companies_owned' | 'market_share' | 'time_limit';
  target: number;
  description: string;
}

// Additional supporting types
export type BusinessUseType = 'headquarters' | 'production' | 'retail' | 'warehouse' | 'mixed';
export type PaymentSchedule = 'monthly' | 'quarterly' | 'milestone' | 'completion';
export type ProductType = 'physical' | 'digital' | 'service' | 'hybrid';
export type ProductCategory = 'consumer' | 'business' | 'enterprise' | 'government';
export type DevelopmentStage = 'concept' | 'prototype' | 'testing' | 'production' | 'market' | 'mature';
export type SpaceAction = 'purchase' | 'pay_rent' | 'draw_card' | 'pay_tax' | 'jail' | 'collect';
export type ZoneType = 'business' | 'industrial' | 'residential' | 'commercial' | 'mixed';

export interface BusinessDistrict {
  name: string;
  spaces: number[];
  businessType: Industry;
  developmentBonus: number;
}

export interface IndustrialZone {
  name: string;
  spaces: number[];
  productionBonus: number;
  environmentalImpact: number;
}

export interface ResidentialArea {
  name: string;
  spaces: number[];
  populationDensity: number;
  averageIncome: number;
}