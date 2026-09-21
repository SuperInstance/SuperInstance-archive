// Core Data Types
export interface Position {
  latitude: number;
  longitude: number;
  altitude?: number;
  accuracy?: number;
  timestamp: Date;
}

export interface InstrumentData {
  speed: number;
  heading: number;
  depth: number;
  waterTemp: number;
  windSpeed: number;
  windDirection: number;
  gpsAccuracy: number;
  timestamp: Date;
}

export interface WeatherData {
  temperature: number;
  humidity: number;
  pressure: number;
  windSpeed: number;
  windDirection: number;
  visibility: number;
  waveHeight?: number;
  conditions: string;
  timestamp: Date;
}

// Fish Logging
export interface FishCatch {
  id: string;
  species: string;
  length?: number;
  weight?: number;
  location: Position;
  timestamp: Date;
  photos: string[];
  notes: string;
  bait?: string;
  lure?: string;
  depth?: number;
  waterTemp?: number;
  weather?: string;
  released: boolean;
}

export interface FishingTrip {
  id: string;
  name: string;
  startTime: Date;
  endTime?: Date;
  catches: FishCatch[];
  locations: Position[];
  notes: string;
  crew: string[];
  weather: WeatherData[];
}

// Anchor Watch
export interface AnchorWatch {
  id: string;
  anchorPosition: Position;
  radius: number;
  isActive: boolean;
  startTime: Date;
  alerts: AnchorAlert[];
}

export interface AnchorAlert {
  id: string;
  timestamp: Date;
  distance: number;
  position: Position;
  acknowledged: boolean;
}

// Emergency
export interface EmergencyContact {
  id: string;
  name: string;
  phone: string;
  type: 'coastguard' | 'marina' | 'family' | 'crew' | 'other';
  priority: number;
}

export interface EmergencyAlert {
  id: string;
  type: 'mayday' | 'pan' | 'securite' | 'man_overboard' | 'fire' | 'collision' | 'medical';
  timestamp: Date;
  position: Position;
  description: string;
  status: 'active' | 'resolved' | 'false_alarm';
  contacts_notified: string[];
}

// Crew & Tasks
export interface CrewMember {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  role: string;
  certifications: string[];
  medical_notes?: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  assignedTo?: string;
  dueDate?: Date;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'in_progress' | 'completed' | 'overdue';
  category: 'maintenance' | 'safety' | 'navigation' | 'provisions' | 'other';
  createdAt: Date;
  completedAt?: Date;
}

// Maintenance
export interface MaintenanceItem {
  id: string;
  system: string;
  component: string;
  description: string;
  interval_hours?: number;
  interval_days?: number;
  last_service: Date;
  next_service: Date;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'current' | 'due' | 'overdue';
  notes: string;
  cost?: number;
}

// Tanks & Monitoring
export interface Tank {
  id: string;
  name: string;
  type: 'fuel' | 'water' | 'waste' | 'ballast';
  capacity: number;
  current_level: number;
  unit: 'gallons' | 'liters';
  low_warning: number;
  critical_warning: number;
  last_updated: Date;
}

export interface TankReading {
  id: string;
  tank_id: string;
  level: number;
  timestamp: Date;
  notes?: string;
}

// Provisions
export interface ProvisionItem {
  id: string;
  name: string;
  category: 'food' | 'beverage' | 'safety' | 'medical' | 'tools' | 'spare_parts' | 'other';
  quantity: number;
  unit: string;
  location: string;
  expiry_date?: Date;
  minimum_stock?: number;
  notes?: string;
  last_updated: Date;
}

export interface ProvisionTransaction {
  id: string;
  item_id: string;
  type: 'add' | 'remove' | 'consume' | 'expire';
  quantity: number;
  timestamp: Date;
  notes?: string;
}

// Remote Desktop Control
export interface DesktopSession {
  id: string;
  name: string;
  host: string;
  port: number;
  status: 'connected' | 'disconnected' | 'connecting' | 'error';
  last_connected?: Date;
  quality: 'low' | 'medium' | 'high' | 'auto';
}

export interface RemoteControl {
  session_id: string;
  action: 'click' | 'drag' | 'scroll' | 'key' | 'zoom';
  x?: number;
  y?: number;
  key?: string;
  data?: any;
}

// Voice Commands
export interface VoiceCommand {
  id: string;
  phrase: string;
  action: string;
  parameters?: { [key: string]: any };
  enabled: boolean;
}

export interface VoiceSession {
  id: string;
  start_time: Date;
  end_time?: Date;
  commands_processed: number;
  errors: number;
}

// App Settings
export interface AppSettings {
  theme: 'light' | 'dark' | 'auto';
  units: {
    distance: 'nm' | 'km' | 'mi';
    speed: 'kts' | 'mph' | 'kmh';
    depth: 'ft' | 'm' | 'fathoms';
    temperature: 'f' | 'c';
    volume: 'gal' | 'l';
  };
  notifications: {
    anchor_watch: boolean;
    maintenance_due: boolean;
    tank_levels: boolean;
    weather_alerts: boolean;
    emergency: boolean;
  };
  voice: {
    enabled: boolean;
    wake_word: string;
    language: string;
    sensitivity: number;
  };
  remote_desktop: {
    auto_connect: boolean;
    default_quality: 'low' | 'medium' | 'high' | 'auto';
    keep_alive: boolean;
  };
}

// Navigation Types
export type RootStackParamList = {
  Home: undefined;
  HelmControl: undefined;
  RemoteDesktop: undefined;
  Instruments: undefined;
  AnchorWatch: undefined;
  FishLog: undefined;
  Weather: undefined;
  Emergency: undefined;
  CrewTasks: undefined;
  Maintenance: undefined;
  TankMonitoring: undefined;
  Provisions: undefined;
  Settings: undefined;
};