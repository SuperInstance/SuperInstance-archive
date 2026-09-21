// Core Swarm Types
export interface Agent {
  id: string;
  type: AgentType;
  name: string;
  status: AgentStatus;
  position?: { x: number; y: number; z?: number };
  specialization: string;
  performance: AgentPerformance;
  createdAt: Date;
}

export type AgentType =
  | 'security'
  | 'performance'
  | 'style'
  | 'testing'
  | 'docs'
  | 'research'
  | 'creative'
  | 'analysis'
  | 'optimization'
  | 'custom';

export type AgentStatus =
  | 'idle'
  | 'working'
  | 'coordinating'
  | 'waiting'
  | 'error'
  | 'offline';

export interface AgentPerformance {
  tasksCompleted: number;
  successRate: number;
  avgResponseTime: number;
  currentLoad: number;
}

export interface Swarm {
  id: string;
  name: string;
  description: string;
  templateId?: string;
  agents: Agent[];
  status: SwarmStatus;
  coordinationType: CoordinationType;
  metrics: SwarmMetrics;
  createdAt: Date;
  updatedAt: Date;
}

export type SwarmStatus =
  | 'initializing'
  | 'running'
  | 'paused'
  | 'stopped'
  | 'error'
  | 'deploying';

export type CoordinationType =
  | 'democratic'
  | 'firefly'
  | 'pheromone'
  | 'hierarchical'
  | 'stigmergy';

export interface SwarmMetrics {
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  averageResponseTime: number;
  throughput: number;
  efficiency: number;
  uptime: number;
  cost: number;
}

export interface SwarmTemplate {
  id: string;
  name: string;
  category: TemplateCategory;
  description: string;
  icon: string;
  agentCount: number;
  agentTypes: AgentType[];
  coordinationType: CoordinationType;
  tags: string[];
  popularity: number;
  rating: number;
  costPerHour: number;
  estimatedSetupTime: number;
  complexity: 'beginner' | 'intermediate' | 'advanced';
  useCases: string[];
}

export type TemplateCategory =
  | 'developer_tools'
  | 'creative'
  | 'business'
  | 'research'
  | 'education'
  | 'gaming'
  | 'data_analysis'
  | 'automation';

export interface Connection {
  id: string;
  source: string;
  target: string;
  type: 'coordination' | 'data' | 'pheromone';
  strength: number;
  bidirectional: boolean;
}

export interface PheromoneTrail {
  id: string;
  path: string[];
  strength: number;
  decay: number;
  createdAt: Date;
  successRate: number;
}

export interface Task {
  id: string;
  type: string;
  description: string;
  priority: number;
  status: 'pending' | 'assigned' | 'in_progress' | 'completed' | 'failed';
  assignedAgent?: string;
  startedAt?: Date;
  completedAt?: Date;
  result?: any;
  error?: string;
}

export interface DeploymentConfig {
  templateId?: string;
  name: string;
  agentCount: number;
  coordinationType: CoordinationType;
  resources: ResourceConfig;
  autoScale: boolean;
  costLimit?: number;
}

export interface ResourceConfig {
  cpuPerAgent: number;
  memoryPerAgent: string;
  minAgents: number;
  maxAgents: number;
}

export interface WebSocketMessage {
  type: MessageType;
  data: any;
  timestamp: Date;
}

export type MessageType =
  | 'agent_status'
  | 'task_update'
  | 'metric_update'
  | 'swarm_status'
  | 'error'
  | 'pheromone_update';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: 'developer' | 'manager' | 'researcher' | 'creator' | 'analyst';
  industry: string;
  preferences: UserPreferences;
  usage: UsageStats;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  notifications: boolean;
  autoSave: boolean;
  defaultCoordination: CoordinationType;
}

export interface UsageStats {
  totalSwarms: number;
  totalTasks: number;
  favoriteTemplates: string[];
  monthlySpend: number;
}

export interface NaturalLanguageQuery {
  query: string;
  intent?: string;
  entities?: Record<string, any>;
  suggestedConfig?: DeploymentConfig;
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  action?: {
    label: string;
    url: string;
  };
}
