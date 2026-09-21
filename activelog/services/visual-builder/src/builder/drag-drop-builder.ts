import { EventEmitter } from 'events';

export interface ComponentDefinition {
  id: string;
  name: string;
  category: ComponentCategory;
  version: string;
  description: string;
  icon: string;
  tags: string[];
  properties: ComponentProperty[];
  events: ComponentEvent[];
  slots: ComponentSlot[];
  children?: ComponentInstance[];
  isContainer: boolean;
  isLeaf: boolean;
  defaultProps: Record<string, any>;
  styles: ComponentStyles;
  responsiveBreakpoints: ResponsiveBreakpoint[];
  accessibility: AccessibilityFeatures;
  seo: SEOFeatures;
  performance: PerformanceHints;
}

export enum ComponentCategory {
  LAYOUT = 'layout',
  NAVIGATION = 'navigation',
  FORMS = 'forms',
  DATA_DISPLAY = 'data_display',
  MEDIA = 'media',
  INTERACTIVE = 'interactive',
  CHARTS = 'charts',
  ECOMMERCE = 'ecommerce',
  SOCIAL = 'social',
  CUSTOM = 'custom'
}

export interface ComponentProperty {
  name: string;
  type: PropertyType;
  label: string;
  description: string;
  defaultValue: any;
  required: boolean;
  validation: PropertyValidation;
  options?: PropertyOption[];
  category: string;
  isBindable: boolean;
  bindingType?: DataBindingType;
}

export enum PropertyType {
  STRING = 'string',
  NUMBER = 'number',
  BOOLEAN = 'boolean',
  COLOR = 'color',
  URL = 'url',
  IMAGE = 'image',
  ICON = 'icon',
  SELECT = 'select',
  MULTI_SELECT = 'multi_select',
  DATE = 'date',
  TIME = 'time',
  DATETIME = 'datetime',
  JSON = 'json',
  CODE = 'code',
  RICH_TEXT = 'rich_text',
  ARRAY = 'array',
  OBJECT = 'object'
}

export interface PropertyValidation {
  min?: number;
  max?: number;
  pattern?: string;
  required?: boolean;
  custom?: string;
}

export interface PropertyOption {
  label: string;
  value: any;
  icon?: string;
  description?: string;
}

export enum DataBindingType {
  STATIC = 'static',
  DYNAMIC = 'dynamic',
  COMPUTED = 'computed',
  API = 'api',
  STATE = 'state',
  PROPS = 'props'
}

export interface ComponentEvent {
  name: string;
  description: string;
  parameters: EventParameter[];
  defaultHandler?: string;
}

export interface EventParameter {
  name: string;
  type: string;
  description: string;
}

export interface ComponentSlot {
  name: string;
  description: string;
  acceptedComponents?: string[];
  maxComponents?: number;
  required: boolean;
}

export interface ComponentInstance {
  id: string;
  definitionId: string;
  name: string;
  props: Record<string, any>;
  styles: ComponentStyles;
  position: ComponentPosition;
  children: ComponentInstance[];
  parent?: string;
  locked: boolean;
  hidden: boolean;
  conditions: DisplayCondition[];
  animations: ComponentAnimation[];
  interactions: ComponentInteraction[];
  dataBinding: DataBinding[];
}

export interface ComponentStyles {
  width?: string;
  height?: string;
  margin?: string;
  padding?: string;
  backgroundColor?: string;
  color?: string;
  fontSize?: string;
  fontFamily?: string;
  fontWeight?: string;
  textAlign?: string;
  border?: string;
  borderRadius?: string;
  boxShadow?: string;
  opacity?: number;
  zIndex?: number;
  position?: 'static' | 'relative' | 'absolute' | 'fixed' | 'sticky';
  top?: string;
  left?: string;
  right?: string;
  bottom?: string;
  display?: string;
  flexDirection?: string;
  justifyContent?: string;
  alignItems?: string;
  gap?: string;
  gridTemplateColumns?: string;
  gridTemplateRows?: string;
  gridGap?: string;
  transform?: string;
  transition?: string;
  cursor?: string;
  overflow?: string;
  customCSS?: string;
}

export interface ComponentPosition {
  x: number;
  y: number;
  z: number;
  rotation: number;
  scale: number;
}

export interface ResponsiveBreakpoint {
  name: string;
  minWidth: number;
  maxWidth?: number;
  styles: ComponentStyles;
  hidden?: boolean;
}

export interface AccessibilityFeatures {
  ariaLabel?: string;
  ariaDescribedBy?: string;
  role?: string;
  tabIndex?: number;
  altText?: string;
  keyboardNavigation: boolean;
  screenReaderSupport: boolean;
  highContrast: boolean;
}

export interface SEOFeatures {
  title?: string;
  description?: string;
  keywords?: string[];
  canonicalUrl?: string;
  structuredData?: Record<string, any>;
  ogTags?: Record<string, string>;
  twitterCards?: Record<string, string>;
}

export interface PerformanceHints {
  lazyLoad: boolean;
  critical: boolean;
  preload: boolean;
  caching: CachingStrategy;
  bundleSize: number;
  renderTime: number;
}

export enum CachingStrategy {
  NONE = 'none',
  BROWSER = 'browser',
  CDN = 'cdn',
  SERVICE_WORKER = 'service_worker'
}

export interface DisplayCondition {
  id: string;
  type: ConditionType;
  property: string;
  operator: ConditionOperator;
  value: any;
  logicalOperator?: LogicalOperator;
}

export enum ConditionType {
  PROPERTY = 'property',
  STATE = 'state',
  USER_ROLE = 'user_role',
  DEVICE = 'device',
  TIME = 'time',
  CUSTOM = 'custom'
}

export enum ConditionOperator {
  EQUALS = 'equals',
  NOT_EQUALS = 'not_equals',
  GREATER_THAN = 'greater_than',
  LESS_THAN = 'less_than',
  CONTAINS = 'contains',
  STARTS_WITH = 'starts_with',
  ENDS_WITH = 'ends_with',
  IS_EMPTY = 'is_empty',
  IS_NOT_EMPTY = 'is_not_empty'
}

export enum LogicalOperator {
  AND = 'and',
  OR = 'or'
}

export interface ComponentAnimation {
  id: string;
  name: string;
  type: AnimationType;
  trigger: AnimationTrigger;
  duration: number;
  delay: number;
  easing: string;
  iterations: number | 'infinite';
  direction: AnimationDirection;
  fillMode: AnimationFillMode;
  keyframes: AnimationKeyframe[];
}

export enum AnimationType {
  FADE = 'fade',
  SLIDE = 'slide',
  SCALE = 'scale',
  ROTATE = 'rotate',
  BOUNCE = 'bounce',
  SHAKE = 'shake',
  PULSE = 'pulse',
  CUSTOM = 'custom'
}

export enum AnimationTrigger {
  ON_LOAD = 'on_load',
  ON_HOVER = 'on_hover',
  ON_CLICK = 'on_click',
  ON_SCROLL = 'on_scroll',
  ON_FOCUS = 'on_focus',
  CUSTOM = 'custom'
}

export enum AnimationDirection {
  NORMAL = 'normal',
  REVERSE = 'reverse',
  ALTERNATE = 'alternate',
  ALTERNATE_REVERSE = 'alternate-reverse'
}

export enum AnimationFillMode {
  NONE = 'none',
  FORWARDS = 'forwards',
  BACKWARDS = 'backwards',
  BOTH = 'both'
}

export interface AnimationKeyframe {
  offset: number;
  properties: Record<string, any>;
  easing?: string;
}

export interface ComponentInteraction {
  id: string;
  event: string;
  action: InteractionAction;
  target?: string;
  parameters: Record<string, any>;
  conditions: DisplayCondition[];
}

export interface InteractionAction {
  type: ActionType;
  payload: any;
  async?: boolean;
  debounce?: number;
  throttle?: number;
}

export enum ActionType {
  NAVIGATE = 'navigate',
  SHOW_MODAL = 'show_modal',
  HIDE_MODAL = 'hide_modal',
  UPDATE_STATE = 'update_state',
  API_CALL = 'api_call',
  FORM_SUBMIT = 'form_submit',
  SCROLL_TO = 'scroll_to',
  PLAY_ANIMATION = 'play_animation',
  CUSTOM_CODE = 'custom_code'
}

export interface DataBinding {
  property: string;
  source: DataSource;
  path: string;
  transform?: DataTransform;
  fallback?: any;
  refresh?: RefreshStrategy;
}

export interface DataSource {
  type: DataSourceType;
  config: Record<string, any>;
  authentication?: AuthenticationConfig;
  caching?: DataCachingConfig;
}

export enum DataSourceType {
  STATIC = 'static',
  API = 'api',
  DATABASE = 'database',
  LOCAL_STORAGE = 'local_storage',
  SESSION_STORAGE = 'session_storage',
  URL_PARAMS = 'url_params',
  FORM_DATA = 'form_data',
  USER_INPUT = 'user_input',
  COMPUTED = 'computed'
}

export interface AuthenticationConfig {
  type: 'none' | 'bearer' | 'basic' | 'oauth' | 'api_key';
  credentials: Record<string, string>;
}

export interface DataCachingConfig {
  enabled: boolean;
  ttl: number;
  strategy: 'memory' | 'localStorage' | 'sessionStorage';
}

export interface DataTransform {
  type: 'map' | 'filter' | 'sort' | 'group' | 'custom';
  config: Record<string, any>;
  code?: string;
}

export interface RefreshStrategy {
  type: 'manual' | 'interval' | 'event' | 'dependency';
  config: Record<string, any>;
}

export interface CanvasState {
  components: Map<string, ComponentInstance>;
  selectedComponents: string[];
  clipboard: ComponentInstance[];
  history: HistoryEntry[];
  historyIndex: number;
  zoom: number;
  pan: { x: number; y: number };
  grid: GridSettings;
  guides: GuideSettings;
  viewport: ViewportSettings;
}

export interface HistoryEntry {
  id: string;
  action: string;
  timestamp: Date;
  before: any;
  after: any;
  description: string;
}

export interface GridSettings {
  enabled: boolean;
  size: number;
  snap: boolean;
  color: string;
  opacity: number;
}

export interface GuideSettings {
  enabled: boolean;
  snapDistance: number;
  color: string;
  showDistances: boolean;
  showAlignments: boolean;
}

export interface ViewportSettings {
  width: number;
  height: number;
  device: DevicePreset;
  orientation: 'portrait' | 'landscape';
  scale: number;
}

export interface DevicePreset {
  name: string;
  width: number;
  height: number;
  pixelRatio: number;
  userAgent: string;
}

export class DragDropBuilder extends EventEmitter {
  private canvasState: CanvasState;
  private componentDefinitions: Map<string, ComponentDefinition> = new Map();
  private dragState: DragState | null = null;
  private selectionBox: SelectionBox | null = null;
  private clipboard: ComponentInstance[] = [];
  private undoRedoManager: UndoRedoManager;

  constructor() {
    super();
    
    this.canvasState = {
      components: new Map(),
      selectedComponents: [],
      clipboard: [],
      history: [],
      historyIndex: -1,
      zoom: 1,
      pan: { x: 0, y: 0 },
      grid: {
        enabled: true,
        size: 10,
        snap: true,
        color: '#e0e0e0',
        opacity: 0.5
      },
      guides: {
        enabled: true,
        snapDistance: 5,
        color: '#007bff',
        showDistances: true,
        showAlignments: true
      },
      viewport: {
        width: 1920,
        height: 1080,
        device: {
          name: 'Desktop',
          width: 1920,
          height: 1080,
          pixelRatio: 1,
          userAgent: 'desktop'
        },
        orientation: 'landscape',
        scale: 1
      }
    };

    this.undoRedoManager = new UndoRedoManager(this);
    this.initializeDefaultComponents();
  }

  private initializeDefaultComponents(): void {
    const defaultComponents: ComponentDefinition[] = [
      {
        id: 'text',
        name: 'Text',
        category: ComponentCategory.DATA_DISPLAY,
        version: '1.0.0',
        description: 'Display text content',
        icon: 'text',
        tags: ['text', 'typography', 'content'],
        properties: [
          {
            name: 'text',
            type: PropertyType.RICH_TEXT,
            label: 'Text Content',
            description: 'The text to display',
            defaultValue: 'Sample text',
            required: true,
            validation: { required: true },
            category: 'content',
            isBindable: true,
            bindingType: DataBindingType.DYNAMIC
          },
          {
            name: 'fontSize',
            type: PropertyType.SELECT,
            label: 'Font Size',
            description: 'Text size',
            defaultValue: '16px',
            required: false,
            validation: {},
            options: [
              { label: 'Small', value: '12px' },
              { label: 'Medium', value: '16px' },
              { label: 'Large', value: '20px' },
              { label: 'Extra Large', value: '24px' }
            ],
            category: 'styling',
            isBindable: false
          }
        ],
        events: [
          {
            name: 'onClick',
            description: 'Triggered when text is clicked',
            parameters: [
              { name: 'event', type: 'MouseEvent', description: 'Click event' }
            ]
          }
        ],
        slots: [],
        isContainer: false,
        isLeaf: true,
        defaultProps: {
          text: 'Sample text',
          fontSize: '16px'
        },
        styles: {
          color: '#333',
          fontSize: '16px',
          fontFamily: 'Arial, sans-serif'
        },
        responsiveBreakpoints: [],
        accessibility: {
          keyboardNavigation: false,
          screenReaderSupport: true,
          highContrast: true
        },
        seo: {
          structuredData: { '@type': 'Text' }
        },
        performance: {
          lazyLoad: false,
          critical: true,
          preload: false,
          caching: CachingStrategy.BROWSER,
          bundleSize: 1024,
          renderTime: 1
        }
      },
      {
        id: 'button',
        name: 'Button',
        category: ComponentCategory.INTERACTIVE,
        version: '1.0.0',
        description: 'Interactive button component',
        icon: 'button',
        tags: ['button', 'interactive', 'action'],
        properties: [
          {
            name: 'label',
            type: PropertyType.STRING,
            label: 'Button Label',
            description: 'Text displayed on the button',
            defaultValue: 'Click me',
            required: true,
            validation: { required: true },
            category: 'content',
            isBindable: true,
            bindingType: DataBindingType.DYNAMIC
          },
          {
            name: 'variant',
            type: PropertyType.SELECT,
            label: 'Button Style',
            description: 'Button appearance variant',
            defaultValue: 'primary',
            required: false,
            validation: {},
            options: [
              { label: 'Primary', value: 'primary' },
              { label: 'Secondary', value: 'secondary' },
              { label: 'Success', value: 'success' },
              { label: 'Danger', value: 'danger' }
            ],
            category: 'styling',
            isBindable: false
          },
          {
            name: 'disabled',
            type: PropertyType.BOOLEAN,
            label: 'Disabled',
            description: 'Whether the button is disabled',
            defaultValue: false,
            required: false,
            validation: {},
            category: 'behavior',
            isBindable: true,
            bindingType: DataBindingType.COMPUTED
          }
        ],
        events: [
          {
            name: 'onClick',
            description: 'Triggered when button is clicked',
            parameters: [
              { name: 'event', type: 'MouseEvent', description: 'Click event' }
            ],
            defaultHandler: 'handleButtonClick'
          },
          {
            name: 'onMouseEnter',
            description: 'Triggered when mouse enters button',
            parameters: [
              { name: 'event', type: 'MouseEvent', description: 'Mouse enter event' }
            ]
          }
        ],
        slots: [],
        isContainer: false,
        isLeaf: true,
        defaultProps: {
          label: 'Click me',
          variant: 'primary',
          disabled: false
        },
        styles: {
          padding: '8px 16px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        },
        responsiveBreakpoints: [],
        accessibility: {
          keyboardNavigation: true,
          screenReaderSupport: true,
          highContrast: true,
          role: 'button',
          tabIndex: 0
        },
        seo: {
          structuredData: { '@type': 'Action' }
        },
        performance: {
          lazyLoad: false,
          critical: true,
          preload: false,
          caching: CachingStrategy.BROWSER,
          bundleSize: 2048,
          renderTime: 2
        }
      },
      {
        id: 'container',
        name: 'Container',
        category: ComponentCategory.LAYOUT,
        version: '1.0.0',
        description: 'Layout container for other components',
        icon: 'container',
        tags: ['container', 'layout', 'wrapper'],
        properties: [
          {
            name: 'direction',
            type: PropertyType.SELECT,
            label: 'Layout Direction',
            description: 'How child components are arranged',
            defaultValue: 'column',
            required: false,
            validation: {},
            options: [
              { label: 'Vertical', value: 'column' },
              { label: 'Horizontal', value: 'row' }
            ],
            category: 'layout',
            isBindable: false
          },
          {
            name: 'gap',
            type: PropertyType.NUMBER,
            label: 'Gap',
            description: 'Space between child components',
            defaultValue: 16,
            required: false,
            validation: { min: 0, max: 100 },
            category: 'layout',
            isBindable: false
          },
          {
            name: 'padding',
            type: PropertyType.NUMBER,
            label: 'Padding',
            description: 'Internal spacing',
            defaultValue: 16,
            required: false,
            validation: { min: 0, max: 100 },
            category: 'layout',
            isBindable: false
          }
        ],
        events: [],
        slots: [
          {
            name: 'default',
            description: 'Default slot for child components',
            required: false
          }
        ],
        isContainer: true,
        isLeaf: false,
        defaultProps: {
          direction: 'column',
          gap: 16,
          padding: 16
        },
        styles: {
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          padding: '16px',
          border: '1px dashed #ccc',
          minHeight: '100px'
        },
        responsiveBreakpoints: [],
        accessibility: {
          keyboardNavigation: false,
          screenReaderSupport: false,
          highContrast: false
        },
        seo: {},
        performance: {
          lazyLoad: false,
          critical: true,
          preload: false,
          caching: CachingStrategy.NONE,
          bundleSize: 512,
          renderTime: 0.5
        }
      },
      {
        id: 'image',
        name: 'Image',
        category: ComponentCategory.MEDIA,
        version: '1.0.0',
        description: 'Display images with responsive features',
        icon: 'image',
        tags: ['image', 'media', 'visual'],
        properties: [
          {
            name: 'src',
            type: PropertyType.IMAGE,
            label: 'Image Source',
            description: 'URL or path to the image',
            defaultValue: '/placeholder-image.jpg',
            required: true,
            validation: { required: true },
            category: 'content',
            isBindable: true,
            bindingType: DataBindingType.DYNAMIC
          },
          {
            name: 'alt',
            type: PropertyType.STRING,
            label: 'Alt Text',
            description: 'Alternative text for accessibility',
            defaultValue: '',
            required: true,
            validation: { required: true },
            category: 'accessibility',
            isBindable: true,
            bindingType: DataBindingType.DYNAMIC
          },
          {
            name: 'fit',
            type: PropertyType.SELECT,
            label: 'Object Fit',
            description: 'How the image should fit within its container',
            defaultValue: 'cover',
            required: false,
            validation: {},
            options: [
              { label: 'Cover', value: 'cover' },
              { label: 'Contain', value: 'contain' },
              { label: 'Fill', value: 'fill' },
              { label: 'Scale Down', value: 'scale-down' },
              { label: 'None', value: 'none' }
            ],
            category: 'styling',
            isBindable: false
          }
        ],
        events: [
          {
            name: 'onLoad',
            description: 'Triggered when image loads successfully',
            parameters: [
              { name: 'event', type: 'Event', description: 'Load event' }
            ]
          },
          {
            name: 'onError',
            description: 'Triggered when image fails to load',
            parameters: [
              { name: 'event', type: 'Event', description: 'Error event' }
            ]
          }
        ],
        slots: [],
        isContainer: false,
        isLeaf: true,
        defaultProps: {
          src: '/placeholder-image.jpg',
          alt: 'Placeholder image',
          fit: 'cover'
        },
        styles: {
          width: '100%',
          height: 'auto',
          objectFit: 'cover',
          borderRadius: '4px'
        },
        responsiveBreakpoints: [
          {
            name: 'mobile',
            minWidth: 0,
            maxWidth: 768,
            styles: {
              width: '100%',
              height: '200px'
            }
          },
          {
            name: 'desktop',
            minWidth: 769,
            styles: {
              width: '300px',
              height: '200px'
            }
          }
        ],
        accessibility: {
          keyboardNavigation: false,
          screenReaderSupport: true,
          highContrast: false,
          altText: 'Required for images'
        },
        seo: {
          structuredData: { '@type': 'ImageObject' }
        },
        performance: {
          lazyLoad: true,
          critical: false,
          preload: false,
          caching: CachingStrategy.CDN,
          bundleSize: 0,
          renderTime: 1
        }
      }
    ];

    defaultComponents.forEach(component => {
      this.componentDefinitions.set(component.id, component);
    });
  }

  // Component Management
  public getComponentDefinition(id: string): ComponentDefinition | undefined {
    return this.componentDefinitions.get(id);
  }

  public getAllComponentDefinitions(): ComponentDefinition[] {
    return Array.from(this.componentDefinitions.values());
  }

  public getComponentsByCategory(category: ComponentCategory): ComponentDefinition[] {
    return Array.from(this.componentDefinitions.values())
      .filter(comp => comp.category === category);
  }

  public registerComponent(definition: ComponentDefinition): void {
    this.componentDefinitions.set(definition.id, definition);
    this.emit('componentRegistered', definition);
  }

  // Canvas Operations
  public addComponent(
    definitionId: string,
    parentId?: string,
    position?: { x: number; y: number }
  ): string {
    const definition = this.componentDefinitions.get(definitionId);
    if (!definition) {
      throw new Error(`Component definition not found: ${definitionId}`);
    }

    const componentId = `${definitionId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const instance: ComponentInstance = {
      id: componentId,
      definitionId,
      name: definition.name,
      props: { ...definition.defaultProps },
      styles: { ...definition.styles },
      position: {
        x: position?.x || 0,
        y: position?.y || 0,
        z: 0,
        rotation: 0,
        scale: 1
      },
      children: [],
      parent: parentId,
      locked: false,
      hidden: false,
      conditions: [],
      animations: [],
      interactions: [],
      dataBinding: []
    };

    this.canvasState.components.set(componentId, instance);

    if (parentId) {
      const parent = this.canvasState.components.get(parentId);
      if (parent) {
        parent.children.push(instance);
      }
    }

    this.undoRedoManager.recordAction('add_component', null, instance);
    this.emit('componentAdded', instance);
    
    return componentId;
  }

  public removeComponent(componentId: string): boolean {
    const component = this.canvasState.components.get(componentId);
    if (!component) return false;

    // Remove from parent's children
    if (component.parent) {
      const parent = this.canvasState.components.get(component.parent);
      if (parent) {
        parent.children = parent.children.filter(child => child.id !== componentId);
      }
    }

    // Remove all children recursively
    this.removeComponentChildren(component);

    this.canvasState.components.delete(componentId);
    this.canvasState.selectedComponents = this.canvasState.selectedComponents
      .filter(id => id !== componentId);

    this.undoRedoManager.recordAction('remove_component', component, null);
    this.emit('componentRemoved', componentId);
    
    return true;
  }

  private removeComponentChildren(component: ComponentInstance): void {
    for (const child of component.children) {
      this.removeComponentChildren(child);
      this.canvasState.components.delete(child.id);
    }
  }

  public updateComponent(componentId: string, updates: Partial<ComponentInstance>): boolean {
    const component = this.canvasState.components.get(componentId);
    if (!component) return false;

    const before = { ...component };
    Object.assign(component, updates);

    this.undoRedoManager.recordAction('update_component', before, component);
    this.emit('componentUpdated', component);
    
    return true;
  }

  public duplicateComponent(componentId: string): string | null {
    const component = this.canvasState.components.get(componentId);
    if (!component) return null;

    const duplicated = this.deepCloneComponent(component);
    duplicated.id = `${component.definitionId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    duplicated.position.x += 20;
    duplicated.position.y += 20;

    this.canvasState.components.set(duplicated.id, duplicated);
    
    if (component.parent) {
      const parent = this.canvasState.components.get(component.parent);
      if (parent) {
        parent.children.push(duplicated);
      }
    }

    this.emit('componentDuplicated', duplicated);
    return duplicated.id;
  }

  private deepCloneComponent(component: ComponentInstance): ComponentInstance {
    const cloned: ComponentInstance = {
      ...component,
      props: { ...component.props },
      styles: { ...component.styles },
      position: { ...component.position },
      children: [],
      conditions: [...component.conditions],
      animations: [...component.animations],
      interactions: [...component.interactions],
      dataBinding: [...component.dataBinding]
    };

    // Clone children recursively
    for (const child of component.children) {
      const clonedChild = this.deepCloneComponent(child);
      clonedChild.parent = cloned.id;
      cloned.children.push(clonedChild);
    }

    return cloned;
  }

  // Selection Management
  public selectComponent(componentId: string, multiSelect = false): void {
    if (!multiSelect) {
      this.canvasState.selectedComponents = [];
    }

    if (!this.canvasState.selectedComponents.includes(componentId)) {
      this.canvasState.selectedComponents.push(componentId);
    }

    this.emit('selectionChanged', this.canvasState.selectedComponents);
  }

  public deselectComponent(componentId: string): void {
    this.canvasState.selectedComponents = this.canvasState.selectedComponents
      .filter(id => id !== componentId);
    this.emit('selectionChanged', this.canvasState.selectedComponents);
  }

  public clearSelection(): void {
    this.canvasState.selectedComponents = [];
    this.emit('selectionChanged', []);
  }

  public getSelectedComponents(): ComponentInstance[] {
    return this.canvasState.selectedComponents
      .map(id => this.canvasState.components.get(id))
      .filter(Boolean) as ComponentInstance[];
  }

  // Copy/Paste Operations
  public copySelectedComponents(): void {
    this.clipboard = this.getSelectedComponents().map(comp => this.deepCloneComponent(comp));
    this.emit('componentsCopied', this.clipboard.length);
  }

  public pasteComponents(position?: { x: number; y: number }): string[] {
    const pastedIds: string[] = [];
    
    for (const component of this.clipboard) {
      const newId = `${component.definitionId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const pasted = this.deepCloneComponent(component);
      pasted.id = newId;
      
      if (position) {
        pasted.position.x = position.x;
        pasted.position.y = position.y;
      } else {
        pasted.position.x += 20;
        pasted.position.y += 20;
      }

      this.canvasState.components.set(newId, pasted);
      pastedIds.push(newId);
    }

    this.emit('componentsPasted', pastedIds);
    return pastedIds;
  }

  // Drag and Drop Operations
  public startDrag(componentId: string, startPosition: { x: number; y: number }): void {
    const component = this.canvasState.components.get(componentId);
    if (!component || component.locked) return;

    this.dragState = {
      componentId,
      startPosition,
      currentPosition: startPosition,
      offset: { x: 0, y: 0 },
      isDragging: false
    };

    this.emit('dragStarted', componentId);
  }

  public updateDrag(currentPosition: { x: number; y: number }): void {
    if (!this.dragState) return;

    this.dragState.currentPosition = currentPosition;
    this.dragState.offset = {
      x: currentPosition.x - this.dragState.startPosition.x,
      y: currentPosition.y - this.dragState.startPosition.y
    };
    this.dragState.isDragging = true;

    // Apply grid snapping if enabled
    if (this.canvasState.grid.snap) {
      this.dragState.offset.x = Math.round(this.dragState.offset.x / this.canvasState.grid.size) 
        * this.canvasState.grid.size;
      this.dragState.offset.y = Math.round(this.dragState.offset.y / this.canvasState.grid.size) 
        * this.canvasState.grid.size;
    }

    this.emit('dragUpdated', this.dragState);
  }

  public endDrag(): void {
    if (!this.dragState || !this.dragState.isDragging) {
      this.dragState = null;
      return;
    }

    const component = this.canvasState.components.get(this.dragState.componentId);
    if (component) {
      const before = { ...component.position };
      
      component.position.x += this.dragState.offset.x;
      component.position.y += this.dragState.offset.y;

      this.undoRedoManager.recordAction('move_component', 
        { ...component, position: before }, 
        component
      );
    }

    this.emit('dragEnded', this.dragState);
    this.dragState = null;
  }

  // Viewport Operations
  public setZoom(zoom: number): void {
    this.canvasState.zoom = Math.max(0.1, Math.min(5, zoom));
    this.emit('zoomChanged', this.canvasState.zoom);
  }

  public setPan(pan: { x: number; y: number }): void {
    this.canvasState.pan = pan;
    this.emit('panChanged', pan);
  }

  public setViewport(settings: Partial<ViewportSettings>): void {
    Object.assign(this.canvasState.viewport, settings);
    this.emit('viewportChanged', this.canvasState.viewport);
  }

  // Grid and Guides
  public setGridSettings(settings: Partial<GridSettings>): void {
    Object.assign(this.canvasState.grid, settings);
    this.emit('gridSettingsChanged', this.canvasState.grid);
  }

  public setGuideSettings(settings: Partial<GuideSettings>): void {
    Object.assign(this.canvasState.guides, settings);
    this.emit('guideSettingsChanged', this.canvasState.guides);
  }

  // Undo/Redo
  public undo(): boolean {
    return this.undoRedoManager.undo();
  }

  public redo(): boolean {
    return this.undoRedoManager.redo();
  }

  public canUndo(): boolean {
    return this.undoRedoManager.canUndo();
  }

  public canRedo(): boolean {
    return this.undoRedoManager.canRedo();
  }

  // State Management
  public getCanvasState(): CanvasState {
    return { ...this.canvasState };
  }

  public loadCanvasState(state: Partial<CanvasState>): void {
    Object.assign(this.canvasState, state);
    this.emit('canvasStateLoaded', this.canvasState);
  }

  public exportComponents(): any {
    return {
      components: Array.from(this.canvasState.components.entries()),
      settings: {
        viewport: this.canvasState.viewport,
        grid: this.canvasState.grid,
        guides: this.canvasState.guides
      },
      version: '1.0.0',
      timestamp: new Date()
    };
  }

  public importComponents(data: any): void {
    if (data.components) {
      this.canvasState.components = new Map(data.components);
    }
    
    if (data.settings) {
      if (data.settings.viewport) {
        Object.assign(this.canvasState.viewport, data.settings.viewport);
      }
      if (data.settings.grid) {
        Object.assign(this.canvasState.grid, data.settings.grid);
      }
      if (data.settings.guides) {
        Object.assign(this.canvasState.guides, data.settings.guides);
      }
    }

    this.emit('componentsImported', data);
  }
}

interface DragState {
  componentId: string;
  startPosition: { x: number; y: number };
  currentPosition: { x: number; y: number };
  offset: { x: number; y: number };
  isDragging: boolean;
}

interface SelectionBox {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  active: boolean;
}

class UndoRedoManager {
  private history: HistoryEntry[] = [];
  private currentIndex = -1;
  private maxHistorySize = 50;

  constructor(private builder: DragDropBuilder) {}

  public recordAction(action: string, before: any, after: any): void {
    // Remove any redo history
    this.history = this.history.slice(0, this.currentIndex + 1);

    const entry: HistoryEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      action,
      timestamp: new Date(),
      before,
      after,
      description: this.generateDescription(action, before, after)
    };

    this.history.push(entry);
    this.currentIndex++;

    // Limit history size
    if (this.history.length > this.maxHistorySize) {
      this.history.shift();
      this.currentIndex--;
    }

    this.builder.emit('historyChanged', {
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      currentAction: entry.description
    });
  }

  public undo(): boolean {
    if (!this.canUndo()) return false;

    const entry = this.history[this.currentIndex];
    this.applyHistoryEntry(entry, 'undo');
    this.currentIndex--;

    this.builder.emit('actionUndone', entry);
    this.builder.emit('historyChanged', {
      canUndo: this.canUndo(),
      canRedo: this.canRedo()
    });

    return true;
  }

  public redo(): boolean {
    if (!this.canRedo()) return false;

    this.currentIndex++;
    const entry = this.history[this.currentIndex];
    this.applyHistoryEntry(entry, 'redo');

    this.builder.emit('actionRedone', entry);
    this.builder.emit('historyChanged', {
      canUndo: this.canUndo(),
      canRedo: this.canRedo()
    });

    return true;
  }

  public canUndo(): boolean {
    return this.currentIndex >= 0;
  }

  public canRedo(): boolean {
    return this.currentIndex < this.history.length - 1;
  }

  private applyHistoryEntry(entry: HistoryEntry, direction: 'undo' | 'redo'): void {
    const state = direction === 'undo' ? entry.before : entry.after;

    switch (entry.action) {
      case 'add_component':
        if (direction === 'undo' && entry.after) {
          this.builder.removeComponent(entry.after.id);
        } else if (direction === 'redo' && entry.after) {
          // Re-add component logic
        }
        break;
      
      case 'remove_component':
        if (direction === 'undo' && entry.before) {
          // Re-add component logic
        } else if (direction === 'redo' && entry.before) {
          this.builder.removeComponent(entry.before.id);
        }
        break;

      case 'update_component':
      case 'move_component':
        if (state) {
          this.builder.updateComponent(state.id, state);
        }
        break;
    }
  }

  private generateDescription(action: string, before: any, after: any): string {
    switch (action) {
      case 'add_component':
        return `Add ${after?.name || 'component'}`;
      case 'remove_component':
        return `Remove ${before?.name || 'component'}`;
      case 'update_component':
        return `Update ${after?.name || 'component'}`;
      case 'move_component':
        return `Move ${after?.name || 'component'}`;
      default:
        return action.replace(/_/g, ' ');
    }
  }
}