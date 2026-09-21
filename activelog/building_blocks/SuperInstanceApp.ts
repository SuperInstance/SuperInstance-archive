// SuperInstance Building Block Interface
// Universal interface for bot-assemblable applications

export interface AppMetadata {
  readonly name: string;
  readonly version: string;
  readonly category: 'personal' | 'business' | 'gaming' | 'productivity' | 'entertainment' | 'utility';
  readonly description: string;
  readonly buildingBlocks: string[];
  readonly author: string;
  readonly license: string;
  readonly tags: string[];
}

export interface AppRequirements {
  readonly ports: number[];
  readonly environment: Record<string, string>;
  readonly dependencies: string[];
  readonly resources: {
    memory: string;
    cpu: string; 
    storage: string;
  };
  readonly database?: {
    type: 'postgresql' | 'sqlite' | 'redis' | 'none';
    schemas: string[];
  };
}

export interface AppCapabilities {
  readonly apis: APIEndpoint[];
  readonly features: string[];
  readonly integrations: string[];
  readonly dataProcessing: DataProcessingCapability[];
  readonly uiComponents: UIComponent[];
  readonly realtime: boolean;
  readonly offline: boolean;
}

export interface APIEndpoint {
  readonly path: string;
  readonly method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  readonly description: string;
  readonly parameters?: Record<string, any>;
  readonly response: Record<string, any>;
}

export interface DataProcessingCapability {
  readonly type: 'import' | 'export' | 'transform' | 'analyze' | 'visualize';
  readonly formats: string[];
  readonly description: string;
}

export interface UIComponent {
  readonly name: string;
  readonly type: 'page' | 'widget' | 'modal' | 'form' | 'chart' | 'table';
  readonly description: string;
  readonly props: Record<string, any>;
  readonly responsive: boolean;
  readonly accessible: boolean;
}

export interface AssemblyContext {
  readonly targetPlatform: 'web' | 'mobile' | 'desktop';
  readonly theme: 'light' | 'dark' | 'auto';
  readonly userPreferences: Record<string, any>;
  readonly existingComponents: string[];
  readonly integrations: Record<string, any>;
  readonly constraints: {
    maxMemory?: string;
    maxCPU?: string;
    offline?: boolean;
  };
}

export interface AppConfig {
  readonly port: number;
  readonly environment: Record<string, string>;
  readonly features: string[];
  readonly theme: Record<string, any>;
  readonly integrations: Record<string, any>;
  readonly customizations: Record<string, any>;
}

export interface BuildingBlock {
  readonly id: string;
  readonly name: string;
  readonly category: string;
  readonly version: string;
  readonly description: string;
  readonly component: React.ComponentType<any>;
  readonly props: Record<string, any>;
  readonly dependencies: string[];
  readonly compatible: string[];
  readonly examples: any[];
}

export interface HealthStatus {
  readonly status: 'healthy' | 'degraded' | 'unhealthy';
  readonly checks: HealthCheck[];
  readonly lastUpdated: Date;
  readonly metrics: Record<string, number>;
}

export interface HealthCheck {
  readonly name: string;
  readonly status: 'pass' | 'warn' | 'fail';
  readonly message?: string;
  readonly duration?: number;
}

export interface CustomerDocumentation {
  readonly overview: string;
  readonly gettingStarted: string;
  readonly apiReference: string;
  readonly examples: Example[];
  readonly troubleshooting: string;
  readonly changelog: string;
}

export interface Example {
  readonly title: string;
  readonly description: string;
  readonly code: string;
  readonly demo?: string;
}

/**
 * Universal SuperInstance Application Interface
 * All launch applications must implement this interface for bot assembly compatibility
 */
export abstract class SuperInstanceApp {
  abstract readonly metadata: AppMetadata;
  
  /**
   * Get available building blocks that this app provides
   */
  abstract getBuildingBlocks(): BuildingBlock[];
  
  /**
   * Configure the app for bot assembly in a specific context
   */
  abstract configureForAssembly(context: AssemblyContext): AppConfig;
  
  /**
   * Get app requirements for deployment
   */
  abstract getRequirements(): AppRequirements;
  
  /**
   * Get app capabilities and features
   */
  abstract getCapabilities(): AppCapabilities;
  
  /**
   * Perform health check
   */
  abstract healthCheck(): Promise<HealthStatus>;
  
  /**
   * Get customer-facing documentation
   */
  abstract getDocumentation(): CustomerDocumentation;
  
  /**
   * Initialize the app with given configuration
   */
  abstract initialize(config: AppConfig): Promise<void>;
  
  /**
   * Shut down the app gracefully
   */
  abstract shutdown(): Promise<void>;
  
  /**
   * Handle assembly events from the bot system
   */
  abstract onAssemblyEvent(event: AssemblyEvent): void;
}

export interface AssemblyEvent {
  readonly type: 'component_added' | 'component_removed' | 'config_changed' | 'integration_updated';
  readonly data: any;
  readonly timestamp: Date;
  readonly source: string;
}

/**
 * Bot Assembly Engine Interface
 * Core system for analyzing requests and selecting building blocks
 */
export interface BotAssemblyEngine {
  /**
   * Convert natural language request into component plan
   */
  analyzeRequest(userRequest: string): Promise<ComponentPlan>;
  
  /**
   * Select optimal building blocks from available library
   */
  selectComponents(plan: ComponentPlan): Promise<BuildingBlock[]>;
  
  /**
   * Assemble components into working application
   */
  assembleApplication(components: BuildingBlock[], context: AssemblyContext): Promise<AssembledApplication>;
  
  /**
   * Validate assembly for compatibility and performance
   */
  validateAssembly(assembly: AssembledApplication): Promise<ValidationResult>;
  
  /**
   * Deploy assembled application
   */
  deployAssembly(assembly: AssembledApplication): Promise<DeploymentResult>;
}

export interface ComponentPlan {
  readonly requirements: string[];
  readonly suggestedComponents: string[];
  readonly layout: LayoutSuggestion;
  readonly integrations: string[];
  readonly constraints: Record<string, any>;
}

export interface LayoutSuggestion {
  readonly type: 'dashboard' | 'form' | 'table' | 'charts' | 'custom';
  readonly components: ComponentLayout[];
  readonly responsive: boolean;
}

export interface ComponentLayout {
  readonly component: string;
  readonly position: { x: number; y: number; w: number; h: number };
  readonly props: Record<string, any>;
}

export interface AssembledApplication {
  readonly id: string;
  readonly name: string;
  readonly components: BuildingBlock[];
  readonly config: AppConfig;
  readonly layout: LayoutSuggestion;
  readonly metadata: AppMetadata;
}

export interface ValidationResult {
  readonly valid: boolean;
  readonly errors: ValidationError[];
  readonly warnings: ValidationWarning[];
  readonly suggestions: string[];
}

export interface ValidationError {
  readonly component: string;
  readonly message: string;
  readonly severity: 'error' | 'warning';
}

export interface ValidationWarning {
  readonly component: string;
  readonly message: string;
  readonly suggestion: string;
}

export interface DeploymentResult {
  readonly success: boolean;
  readonly url?: string;
  readonly port?: number;
  readonly errors?: string[];
  readonly logs: string[];
  readonly healthStatus: HealthStatus;
}

/**
 * Component Registry Interface
 * Central repository for discovering and managing building blocks
 */
export interface ComponentRegistry {
  /**
   * Register a new building block
   */
  registerComponent(component: BuildingBlock): Promise<void>;
  
  /**
   * Find components matching criteria
   */
  findComponents(criteria: ComponentCriteria): Promise<BuildingBlock[]>;
  
  /**
   * Get component by ID
   */
  getComponent(id: string): Promise<BuildingBlock | null>;
  
  /**
   * Check component compatibility
   */
  checkCompatibility(componentIds: string[]): Promise<CompatibilityResult>;
  
  /**
   * Get component usage statistics
   */
  getComponentStats(id: string): Promise<ComponentStats>;
}

export interface ComponentCriteria {
  readonly category?: string;
  readonly tags?: string[];
  readonly compatible?: string[];
  readonly search?: string;
}

export interface CompatibilityResult {
  readonly compatible: boolean;
  readonly conflicts: ComponentConflict[];
  readonly suggestions: string[];
}

export interface ComponentConflict {
  readonly component1: string;
  readonly component2: string;
  readonly reason: string;
  readonly severity: 'error' | 'warning';
}

export interface ComponentStats {
  readonly downloads: number;
  readonly rating: number;
  readonly reviews: number;
  readonly lastUsed: Date;
  readonly popularity: number;
}