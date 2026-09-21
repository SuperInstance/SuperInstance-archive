export interface UserAction {
  id: string;
  userId: string;
  timestamp: Date;
  actionType: 'file_access' | 'folder_create' | 'search' | 'tag_add' | 'move' | 'delete' | 'share';
  resourcePath: string;
  metadata: Record<string, any>;
  context?: {
    timeOfDay: number;
    dayOfWeek: number;
    month: number;
    location?: string;
    deviceType?: string;
  };
}

export interface UserPattern {
  id: string;
  userId: string;
  patternType: 'temporal' | 'categorical' | 'sequential' | 'contextual';
  confidence: number;
  frequency: number;
  lastSeen: Date;
  pattern: any;
  triggers?: string[];
  outcomes?: string[];
}

export interface Prediction {
  id: string;
  userId: string;
  predictionType: 'folder_suggestion' | 'future_need' | 'file_access' | 'anomaly' | 'lifecycle';
  confidence: number;
  timestamp: Date;
  expiresAt: Date;
  payload: any;
  context: Record<string, any>;
}

export interface RelationshipNode {
  id: string;
  type: 'file' | 'folder' | 'person' | 'event' | 'tag' | 'project';
  properties: Record<string, any>;
  weight: number;
  lastAccessed: Date;
}

export interface RelationshipEdge {
  from: string;
  to: string;
  relationship: 'contains' | 'related_to' | 'precedes' | 'triggers' | 'collaborates_with';
  weight: number;
  confidence: number;
  metadata: Record<string, any>;
}

export interface TemporalCluster {
  id: string;
  userId: string;
  startTime: Date;
  endTime: Date;
  emotionalSignificance: number;
  events: UserAction[];
  tags: string[];
  summary: string;
  relationships: string[];
}

export interface AnomalyAlert {
  id: string;
  userId: string;
  timestamp: Date;
  anomalyType: 'unusual_access' | 'missing_pattern' | 'data_gap' | 'behavioral_shift';
  severity: 'low' | 'medium' | 'high';
  description: string;
  suggestedActions: string[];
  confidence: number;
}

export interface HabitSuggestion {
  id: string;
  userId: string;
  habitType: 'organization' | 'backup' | 'tagging' | 'cleanup' | 'scheduling';
  suggestion: string;
  reasoning: string;
  difficulty: 'easy' | 'medium' | 'hard';
  estimatedBenefit: number;
  implementationSteps: string[];
}