"""
Visual Assembly Interface System
Intuitive drag-and-drop interface for visual application assembly
"""

import asyncio
import time
import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

class ComponentCategory(Enum):
    CORE = "core"                   # Essential components (auth, database)
    UI_ELEMENTS = "ui_elements"     # Frontend components (buttons, forms)
    INTEGRATIONS = "integrations"   # External service connections
    ADVANCED = "advanced"           # AI, analytics, complex features
    TEMPLATES = "templates"         # Pre-built component groups

class LayoutType(Enum):
    GRID = "grid"                   # Grid-based layout
    FLOW = "flow"                   # Flow-based connections
    LAYERED = "layered"             # Layered architecture view
    TIMELINE = "timeline"           # Step-by-step timeline
    MINDMAP = "mindmap"             # Mind map style

class InteractionMode(Enum):
    DRAG_DROP = "drag_drop"         # Drag and drop components
    CLICK_TO_ADD = "click_to_add"   # Click to add components
    GESTURE = "gesture"             # Touch gestures
    VOICE = "voice"                 # Voice commands
    KEYBOARD = "keyboard"           # Keyboard shortcuts

@dataclass
class VisualComponent:
    id: str
    name: str
    category: ComponentCategory
    description: str
    icon: str                       # Icon/emoji representation
    color: str                      # Component color theme
    size: Tuple[int, int]          # Width, height in grid units
    position: Tuple[int, int]      # X, Y position
    connections: List[str]         # Connected component IDs
    configuration: Dict[str, Any]  # Component settings
    visual_style: Dict[str, Any]   # Visual styling options
    difficulty_level: int          # 1-5 complexity
    estimated_setup_time: int      # Minutes to configure
    is_locked: bool = False        # Locked components can't be moved
    is_required: bool = False      # Required for app functionality

@dataclass
class CanvasState:
    canvas_id: str
    components: Dict[str, VisualComponent]
    connections: List[Dict[str, Any]]
    layout_type: LayoutType
    zoom_level: float
    pan_offset: Tuple[float, float]
    grid_size: int
    snap_to_grid: bool
    auto_arrange: bool
    show_connections: bool
    show_labels: bool

@dataclass
class AssemblyAction:
    action_id: str
    action_type: str               # add, remove, move, connect, configure
    component_id: Optional[str]
    data: Dict[str, Any]
    timestamp: float
    user_id: str
    can_undo: bool = True

class VisualAssemblyEngine:
    """Core engine for visual application assembly"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Component library
        self.component_library = self._initialize_component_library()
        
        # Active canvases
        self.active_canvases = {}
        
        # Action history for undo/redo
        self.action_history = {}
        
        # Smart suggestions
        self.suggestion_engine = ComponentSuggestionEngine()
        
        # Auto-layout algorithms
        self.layout_engine = AutoLayoutEngine()
        
        # Connection validation
        self.connection_validator = ConnectionValidator()
        
        self.logger.info("Visual Assembly Engine initialized")
    
    def create_canvas(self, user_id: str, app_concept: str, 
                     preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new visual assembly canvas"""
        
        canvas_id = str(uuid.uuid4())
        
        # Initialize canvas state
        canvas_state = CanvasState(
            canvas_id=canvas_id,
            components={},
            connections=[],
            layout_type=LayoutType.GRID,
            zoom_level=1.0,
            pan_offset=(0.0, 0.0),
            grid_size=20,
            snap_to_grid=True,
            auto_arrange=False,
            show_connections=True,
            show_labels=True
        )
        
        # Apply user preferences
        if preferences:
            canvas_state.layout_type = LayoutType(preferences.get('layout', 'grid'))
            canvas_state.snap_to_grid = preferences.get('snap_to_grid', True)
            canvas_state.auto_arrange = preferences.get('auto_arrange', False)
        
        self.active_canvases[canvas_id] = canvas_state
        self.action_history[canvas_id] = []
        
        # Suggest initial components based on app concept
        initial_suggestions = self.suggestion_engine.suggest_initial_components(
            app_concept, preferences
        )
        
        return {
            'canvas_id': canvas_id,
            'initial_state': self._serialize_canvas_state(canvas_state),
            'component_library': self._get_categorized_components(),
            'initial_suggestions': initial_suggestions,
            'layout_options': self._get_layout_options(),
            'interaction_modes': self._get_interaction_modes(),
            'canvas_tools': self._get_canvas_tools()
        }
    
    def add_component(self, canvas_id: str, component_type: str, 
                     position: Tuple[int, int], user_id: str) -> Dict[str, Any]:
        """Add a component to the canvas"""
        
        if canvas_id not in self.active_canvases:
            return {'error': 'Canvas not found'}
        
        canvas = self.active_canvases[canvas_id]
        
        try:
            # Get component template
            component_template = self.component_library.get(component_type)
            if not component_template:
                return {'error': f'Component type {component_type} not found'}
            
            # Create component instance
            component_id = f"{component_type}_{int(time.time())}"
            component = VisualComponent(
                id=component_id,
                name=component_template['name'],
                category=ComponentCategory(component_template['category']),
                description=component_template['description'],
                icon=component_template['icon'],
                color=component_template['color'],
                size=component_template['size'],
                position=self._snap_to_grid(position, canvas.grid_size) if canvas.snap_to_grid else position,
                connections=[],
                configuration=component_template.get('default_config', {}),
                visual_style=component_template.get('visual_style', {}),
                difficulty_level=component_template.get('difficulty_level', 3),
                estimated_setup_time=component_template.get('setup_time', 10)
            )
            
            # Validate placement
            validation_result = self._validate_component_placement(canvas, component)
            if not validation_result['valid']:
                return {'error': validation_result['reason']}
            
            # Add to canvas
            canvas.components[component_id] = component
            
            # Record action
            action = AssemblyAction(
                action_id=str(uuid.uuid4()),
                action_type='add_component',
                component_id=component_id,
                data={'component_type': component_type, 'position': position},
                timestamp=time.time(),
                user_id=user_id
            )
            self.action_history[canvas_id].append(action)
            
            # Generate smart suggestions for next components
            next_suggestions = self.suggestion_engine.suggest_complementary_components(
                component, canvas.components
            )
            
            # Auto-arrange if enabled
            if canvas.auto_arrange:
                self.layout_engine.auto_arrange_components(canvas)
            
            return {
                'success': True,
                'component': self._serialize_component(component),
                'canvas_state': self._serialize_canvas_state(canvas),
                'next_suggestions': next_suggestions,
                'auto_connections': self._suggest_auto_connections(component, canvas)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to add component: {e}")
            return {'error': str(e)}
    
    def move_component(self, canvas_id: str, component_id: str, 
                      new_position: Tuple[int, int], user_id: str) -> Dict[str, Any]:
        """Move a component to a new position"""
        
        if canvas_id not in self.active_canvases:
            return {'error': 'Canvas not found'}
        
        canvas = self.active_canvases[canvas_id]
        
        if component_id not in canvas.components:
            return {'error': 'Component not found'}
        
        component = canvas.components[component_id]
        
        if component.is_locked:
            return {'error': 'Component is locked and cannot be moved'}
        
        try:
            old_position = component.position
            
            # Apply grid snapping if enabled
            final_position = self._snap_to_grid(new_position, canvas.grid_size) if canvas.snap_to_grid else new_position
            
            # Validate new position
            component.position = final_position
            validation_result = self._validate_component_placement(canvas, component)
            
            if not validation_result['valid']:
                component.position = old_position  # Revert
                return {'error': validation_result['reason']}
            
            # Record action
            action = AssemblyAction(
                action_id=str(uuid.uuid4()),
                action_type='move_component',
                component_id=component_id,
                data={'old_position': old_position, 'new_position': final_position},
                timestamp=time.time(),
                user_id=user_id
            )
            self.action_history[canvas_id].append(action)
            
            # Update connections if needed
            self._update_connection_paths(canvas, component_id)
            
            return {
                'success': True,
                'component': self._serialize_component(component),
                'updated_connections': self._get_component_connections(canvas, component_id)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to move component: {e}")
            return {'error': str(e)}
    
    def connect_components(self, canvas_id: str, source_id: str, 
                          target_id: str, user_id: str) -> Dict[str, Any]:
        """Create a connection between two components"""
        
        if canvas_id not in self.active_canvases:
            return {'error': 'Canvas not found'}
        
        canvas = self.active_canvases[canvas_id]
        
        if source_id not in canvas.components or target_id not in canvas.components:
            return {'error': 'One or both components not found'}
        
        try:
            # Validate connection
            validation_result = self.connection_validator.validate_connection(
                canvas.components[source_id],
                canvas.components[target_id],
                canvas.components
            )
            
            if not validation_result['valid']:
                return {'error': validation_result['reason']}
            
            # Create connection
            connection = {
                'id': str(uuid.uuid4()),
                'source': source_id,
                'target': target_id,
                'type': validation_result['connection_type'],
                'style': validation_result.get('style', {}),
                'created_at': time.time()
            }
            
            canvas.connections.append(connection)
            
            # Update component connections
            canvas.components[source_id].connections.append(target_id)
            if validation_result['connection_type'] == 'bidirectional':
                canvas.components[target_id].connections.append(source_id)
            
            # Record action
            action = AssemblyAction(
                action_id=str(uuid.uuid4()),
                action_type='connect_components',
                component_id=None,
                data={'source': source_id, 'target': target_id, 'connection': connection},
                timestamp=time.time(),
                user_id=user_id
            )
            self.action_history[canvas_id].append(action)
            
            return {
                'success': True,
                'connection': connection,
                'validation_info': validation_result,
                'suggested_next_connections': self._suggest_next_connections(canvas, target_id)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to connect components: {e}")
            return {'error': str(e)}
    
    def configure_component(self, canvas_id: str, component_id: str, 
                           configuration: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Configure component settings"""
        
        if canvas_id not in self.active_canvases:
            return {'error': 'Canvas not found'}
        
        canvas = self.active_canvases[canvas_id]
        
        if component_id not in canvas.components:
            return {'error': 'Component not found'}
        
        component = canvas.components[component_id]
        
        try:
            # Validate configuration
            validation_result = self._validate_component_configuration(component, configuration)
            if not validation_result['valid']:
                return {'error': validation_result['reason']}
            
            old_config = component.configuration.copy()
            component.configuration.update(configuration)
            
            # Record action
            action = AssemblyAction(
                action_id=str(uuid.uuid4()),
                action_type='configure_component',
                component_id=component_id,
                data={'old_config': old_config, 'new_config': configuration},
                timestamp=time.time(),
                user_id=user_id
            )
            self.action_history[canvas_id].append(action)
            
            # Check if configuration affects other components
            impact_analysis = self._analyze_configuration_impact(canvas, component, configuration)
            
            return {
                'success': True,
                'component': self._serialize_component(component),
                'configuration_impact': impact_analysis,
                'related_suggestions': self._suggest_related_configurations(canvas, component)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to configure component: {e}")
            return {'error': str(e)}
    
    def auto_arrange_canvas(self, canvas_id: str, layout_type: str = None) -> Dict[str, Any]:
        """Automatically arrange components on the canvas"""
        
        if canvas_id not in self.active_canvases:
            return {'error': 'Canvas not found'}
        
        canvas = self.active_canvases[canvas_id]
        
        try:
            # Use specified layout or current canvas layout
            target_layout = LayoutType(layout_type) if layout_type else canvas.layout_type
            
            # Store original positions for undo
            original_positions = {
                comp_id: comp.position for comp_id, comp in canvas.components.items()
            }
            
            # Apply auto-arrangement
            arrangement_result = self.layout_engine.arrange_components(
                canvas.components, canvas.connections, target_layout
            )
            
            if not arrangement_result['success']:
                return {'error': arrangement_result['error']}
            
            # Update component positions
            for comp_id, new_position in arrangement_result['positions'].items():
                if comp_id in canvas.components:
                    canvas.components[comp_id].position = new_position
            
            # Update canvas layout type
            canvas.layout_type = target_layout
            
            # Update connection paths
            self._update_all_connection_paths(canvas)
            
            # Record action
            action = AssemblyAction(
                action_id=str(uuid.uuid4()),
                action_type='auto_arrange',
                component_id=None,
                data={'layout_type': target_layout.value, 'original_positions': original_positions},
                timestamp=time.time(),
                user_id='system'
            )
            self.action_history[canvas_id].append(action)
            
            return {
                'success': True,
                'layout_type': target_layout.value,
                'canvas_state': self._serialize_canvas_state(canvas),
                'arrangement_metrics': arrangement_result.get('metrics', {}),
                'improvement_score': arrangement_result.get('improvement_score', 0.0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to auto-arrange canvas: {e}")
            return {'error': str(e)}
    
    def get_assembly_preview(self, canvas_id: str) -> Dict[str, Any]:
        """Generate a preview of the assembled application"""
        
        if canvas_id not in self.active_canvases:
            return {'error': 'Canvas not found'}
        
        canvas = self.active_canvases[canvas_id]
        
        try:
            # Analyze component assembly
            assembly_analysis = self._analyze_assembly(canvas)
            
            # Generate preview data
            preview_data = {
                'app_structure': self._generate_app_structure(canvas),
                'user_flow': self._generate_user_flow(canvas),
                'api_endpoints': self._generate_api_structure(canvas),
                'database_schema': self._generate_database_schema(canvas),
                'ui_mockup': self._generate_ui_mockup(canvas),
                'deployment_config': self._generate_deployment_config(canvas)
            }
            
            # Calculate completeness score
            completeness = self._calculate_assembly_completeness(canvas)
            
            # Identify missing components
            missing_components = self._identify_missing_components(canvas)
            
            return {
                'preview': preview_data,
                'assembly_analysis': assembly_analysis,
                'completeness_score': completeness,
                'missing_components': missing_components,
                'deployment_ready': completeness >= 0.8,
                'estimated_build_time': self._estimate_build_time(canvas)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate assembly preview: {e}")
            return {'error': str(e)}
    
    def undo_action(self, canvas_id: str, user_id: str) -> Dict[str, Any]:
        """Undo the last action on the canvas"""
        
        if canvas_id not in self.active_canvases:
            return {'error': 'Canvas not found'}
        
        if canvas_id not in self.action_history:
            return {'error': 'No action history found'}
        
        history = self.action_history[canvas_id]
        if not history:
            return {'error': 'No actions to undo'}
        
        # Find last undoable action by this user
        last_action = None
        for i in range(len(history) - 1, -1, -1):
            action = history[i]
            if action.can_undo and action.user_id == user_id:
                last_action = action
                break
        
        if not last_action:
            return {'error': 'No undoable actions found'}
        
        try:
            # Undo the action
            undo_result = self._undo_action(canvas_id, last_action)
            
            if undo_result['success']:
                # Remove action from history
                history.remove(last_action)
                
                return {
                    'success': True,
                    'undone_action': last_action.action_type,
                    'canvas_state': self._serialize_canvas_state(self.active_canvases[canvas_id])
                }
            else:
                return {'error': undo_result['error']}
            
        except Exception as e:
            self.logger.error(f"Failed to undo action: {e}")
            return {'error': str(e)}
    
    def _initialize_component_library(self) -> Dict[str, Any]:
        """Initialize the visual component library"""
        
        return {
            'user_authentication': {
                'name': 'User Login',
                'category': 'core',
                'description': 'Secure user authentication system',
                'icon': '🔐',
                'color': '#4A90E2',
                'size': (120, 80),
                'difficulty_level': 2,
                'setup_time': 5,
                'default_config': {
                    'auth_method': 'email_password',
                    'social_login': False,
                    'two_factor': False
                },
                'visual_style': {
                    'border_radius': 8,
                    'border_width': 2,
                    'shadow': True
                }
            },
            
            'database_storage': {
                'name': 'Database',
                'category': 'core',
                'description': 'Data storage and management',
                'icon': '🗄️',
                'color': '#7ED321',
                'size': (140, 90),
                'difficulty_level': 3,
                'setup_time': 10,
                'default_config': {
                    'type': 'postgresql',
                    'backup_enabled': True,
                    'encryption': True
                },
                'visual_style': {
                    'border_radius': 6,
                    'border_width': 2,
                    'shadow': True
                }
            },
            
            'api_service': {
                'name': 'API Service',
                'category': 'core',
                'description': 'Backend API endpoints',
                'icon': '⚡',
                'color': '#F5A623',
                'size': (130, 85),
                'difficulty_level': 4,
                'setup_time': 15,
                'default_config': {
                    'rest_api': True,
                    'graphql': False,
                    'rate_limiting': True
                },
                'visual_style': {
                    'border_radius': 8,
                    'border_width': 2,
                    'shadow': True
                }
            },
            
            'frontend_ui': {
                'name': 'Frontend UI',
                'category': 'ui_elements',
                'description': 'User interface components',
                'icon': '🎨',
                'color': '#BD10E0',
                'size': (150, 100),
                'difficulty_level': 3,
                'setup_time': 12,
                'default_config': {
                    'framework': 'react',
                    'responsive': True,
                    'theme': 'modern'
                },
                'visual_style': {
                    'border_radius': 10,
                    'border_width': 2,
                    'shadow': True
                }
            },
            
            'payment_gateway': {
                'name': 'Payment Gateway',
                'category': 'integrations',
                'description': 'Secure payment processing',
                'icon': '💳',
                'color': '#50E3C2',
                'size': (125, 75),
                'difficulty_level': 5,
                'setup_time': 25,
                'default_config': {
                    'provider': 'stripe',
                    'currencies': ['USD'],
                    'subscription_support': False
                },
                'visual_style': {
                    'border_radius': 8,
                    'border_width': 3,
                    'shadow': True
                }
            },
            
            'push_notifications': {
                'name': 'Push Notifications',
                'category': 'integrations',
                'description': 'Real-time user notifications',
                'icon': '🔔',
                'color': '#D0021B',
                'size': (110, 70),
                'difficulty_level': 3,
                'setup_time': 8,
                'default_config': {
                    'platforms': ['web', 'mobile'],
                    'scheduling': True,
                    'personalization': False
                },
                'visual_style': {
                    'border_radius': 8,
                    'border_width': 2,
                    'shadow': True
                }
            },
            
            'ai_recommendations': {
                'name': 'AI Recommendations',
                'category': 'advanced',
                'description': 'Machine learning powered suggestions',
                'icon': '🤖',
                'color': '#9013FE',
                'size': (160, 95),
                'difficulty_level': 5,
                'setup_time': 35,
                'default_config': {
                    'algorithm': 'collaborative_filtering',
                    'real_time': False,
                    'learning_enabled': True
                },
                'visual_style': {
                    'border_radius': 12,
                    'border_width': 2,
                    'shadow': True,
                    'gradient': True
                }
            },
            
            'analytics_dashboard': {
                'name': 'Analytics',
                'category': 'advanced',
                'description': 'User behavior and app analytics',
                'icon': '📊',
                'color': '#FF6B35',
                'size': (145, 85),
                'difficulty_level': 4,
                'setup_time': 20,
                'default_config': {
                    'metrics': ['users', 'sessions', 'events'],
                    'real_time': True,
                    'custom_events': True
                },
                'visual_style': {
                    'border_radius': 8,
                    'border_width': 2,
                    'shadow': True
                }
            }
        }
    
    def _get_categorized_components(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get components organized by category"""
        
        categorized = {}
        
        for comp_id, comp_data in self.component_library.items():
            category = comp_data['category']
            if category not in categorized:
                categorized[category] = []
            
            categorized[category].append({
                'id': comp_id,
                'name': comp_data['name'],
                'description': comp_data['description'],
                'icon': comp_data['icon'],
                'color': comp_data['color'],
                'difficulty_level': comp_data['difficulty_level'],
                'setup_time': comp_data['setup_time']
            })
        
        return categorized
    
    def _snap_to_grid(self, position: Tuple[int, int], grid_size: int) -> Tuple[int, int]:
        """Snap position to grid"""
        x, y = position
        snapped_x = round(x / grid_size) * grid_size
        snapped_y = round(y / grid_size) * grid_size
        return (snapped_x, snapped_y)
    
    def _validate_component_placement(self, canvas: CanvasState, 
                                    component: VisualComponent) -> Dict[str, Any]:
        """Validate if component can be placed at position"""
        
        # Check for overlaps
        for existing_id, existing_comp in canvas.components.items():
            if existing_id == component.id:
                continue
            
            if self._components_overlap(component, existing_comp):
                return {
                    'valid': False,
                    'reason': f'Component overlaps with {existing_comp.name}'
                }
        
        # Check canvas bounds (assuming 1000x800 canvas)
        if (component.position[0] < 0 or component.position[1] < 0 or
            component.position[0] + component.size[0] > 1000 or
            component.position[1] + component.size[1] > 800):
            return {
                'valid': False,
                'reason': 'Component is outside canvas bounds'
            }
        
        return {'valid': True}
    
    def _components_overlap(self, comp1: VisualComponent, comp2: VisualComponent) -> bool:
        """Check if two components overlap"""
        
        x1, y1 = comp1.position
        w1, h1 = comp1.size
        
        x2, y2 = comp2.position
        w2, h2 = comp2.size
        
        return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)
    
    def _serialize_canvas_state(self, canvas: CanvasState) -> Dict[str, Any]:
        """Serialize canvas state for client"""
        
        return {
            'canvas_id': canvas.canvas_id,
            'components': {
                comp_id: self._serialize_component(comp)
                for comp_id, comp in canvas.components.items()
            },
            'connections': canvas.connections,
            'layout_type': canvas.layout_type.value,
            'zoom_level': canvas.zoom_level,
            'pan_offset': canvas.pan_offset,
            'settings': {
                'grid_size': canvas.grid_size,
                'snap_to_grid': canvas.snap_to_grid,
                'auto_arrange': canvas.auto_arrange,
                'show_connections': canvas.show_connections,
                'show_labels': canvas.show_labels
            }
        }
    
    def _serialize_component(self, component: VisualComponent) -> Dict[str, Any]:
        """Serialize component for client"""
        
        return {
            'id': component.id,
            'name': component.name,
            'category': component.category.value,
            'description': component.description,
            'icon': component.icon,
            'color': component.color,
            'size': component.size,
            'position': component.position,
            'connections': component.connections,
            'configuration': component.configuration,
            'visual_style': component.visual_style,
            'difficulty_level': component.difficulty_level,
            'estimated_setup_time': component.estimated_setup_time,
            'is_locked': component.is_locked,
            'is_required': component.is_required
        }
    
    def _get_layout_options(self) -> List[Dict[str, Any]]:
        """Get available layout options"""
        
        return [
            {
                'type': LayoutType.GRID.value,
                'name': 'Grid Layout',
                'description': 'Organized grid with aligned components',
                'icon': '⊞',
                'best_for': 'Structured applications with clear component relationships'
            },
            {
                'type': LayoutType.FLOW.value,
                'name': 'Flow Layout',
                'description': 'Data flow visualization with connections',
                'icon': '→',
                'best_for': 'Process-oriented applications with clear data flow'
            },
            {
                'type': LayoutType.LAYERED.value,
                'name': 'Layered Architecture',
                'description': 'Traditional layered architecture view',
                'icon': '≡',
                'best_for': 'Enterprise applications with clear architectural layers'
            },
            {
                'type': LayoutType.MINDMAP.value,
                'name': 'Mind Map',
                'description': 'Central concept with branching components',
                'icon': '❋',
                'best_for': 'Exploratory design and brainstorming'
            }
        ]
    
    def _get_interaction_modes(self) -> List[Dict[str, Any]]:
        """Get available interaction modes"""
        
        return [
            {
                'mode': InteractionMode.DRAG_DROP.value,
                'name': 'Drag & Drop',
                'description': 'Drag components from library to canvas',
                'icon': '✋',
                'suitable_for': ['desktop', 'tablet']
            },
            {
                'mode': InteractionMode.CLICK_TO_ADD.value,
                'name': 'Click to Add',
                'description': 'Click to select component, then click to place',
                'icon': '👆',
                'suitable_for': ['desktop', 'tablet', 'mobile']
            },
            {
                'mode': InteractionMode.GESTURE.value,
                'name': 'Touch Gestures',
                'description': 'Multi-touch gestures for mobile devices',
                'icon': '✌️',
                'suitable_for': ['mobile', 'tablet']
            }
        ]
    
    def _get_canvas_tools(self) -> List[Dict[str, Any]]:
        """Get available canvas tools"""
        
        return [
            {
                'tool': 'select',
                'name': 'Select Tool',
                'description': 'Select and move components',
                'icon': '↖️',
                'shortcut': 'V'
            },
            {
                'tool': 'connect',
                'name': 'Connection Tool',
                'description': 'Create connections between components',
                'icon': '🔗',
                'shortcut': 'C'
            },
            {
                'tool': 'pan',
                'name': 'Pan Tool',
                'description': 'Navigate around the canvas',
                'icon': '✋',
                'shortcut': 'H'
            },
            {
                'tool': 'zoom',
                'name': 'Zoom Tool',
                'description': 'Zoom in and out of the canvas',
                'icon': '🔍',
                'shortcut': 'Z'
            }
        ]

class ComponentSuggestionEngine:
    """Engine for suggesting relevant components"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def suggest_initial_components(self, app_concept: str, 
                                 preferences: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Suggest initial components based on app concept"""
        
        suggestions = []
        app_lower = app_concept.lower()
        
        # Core suggestions based on keywords
        if any(keyword in app_lower for keyword in ['user', 'account', 'profile', 'login']):
            suggestions.append({
                'component': 'user_authentication',
                'reason': 'Your app mentions users, so you\'ll need user authentication',
                'priority': 'high',
                'auto_add': True
            })
        
        if any(keyword in app_lower for keyword in ['data', 'save', 'store', 'remember']):
            suggestions.append({
                'component': 'database_storage',
                'reason': 'Your app needs to store data permanently',
                'priority': 'high',
                'auto_add': True
            })
        
        if any(keyword in app_lower for keyword in ['app', 'website', 'interface']):
            suggestions.append({
                'component': 'frontend_ui',
                'reason': 'You\'ll need a user interface for your app',
                'priority': 'high',
                'auto_add': True
            })
        
        if any(keyword in app_lower for keyword in ['api', 'backend', 'server']):
            suggestions.append({
                'component': 'api_service',
                'reason': 'Backend API will handle your app\'s logic',
                'priority': 'high',
                'auto_add': False
            })
        
        # Advanced features
        if any(keyword in app_lower for keyword in ['pay', 'buy', 'sell', 'money', 'subscription']):
            suggestions.append({
                'component': 'payment_gateway',
                'reason': 'Payment functionality detected in your concept',
                'priority': 'medium',
                'auto_add': False
            })
        
        if any(keyword in app_lower for keyword in ['notify', 'alert', 'reminder']):
            suggestions.append({
                'component': 'push_notifications',
                'reason': 'Notifications will keep users engaged',
                'priority': 'medium',
                'auto_add': False
            })
        
        if any(keyword in app_lower for keyword in ['recommend', 'suggest', 'ai', 'smart']):
            suggestions.append({
                'component': 'ai_recommendations',
                'reason': 'AI recommendations can personalize user experience',
                'priority': 'low',
                'auto_add': False
            })
        
        return suggestions
    
    def suggest_complementary_components(self, added_component: VisualComponent, 
                                       existing_components: Dict[str, VisualComponent]) -> List[Dict[str, Any]]:
        """Suggest components that work well with the newly added component"""
        
        suggestions = []
        
        if added_component.category == ComponentCategory.CORE:
            if added_component.name == 'User Login':
                suggestions.extend([
                    {
                        'component': 'database_storage',
                        'reason': 'User data needs to be stored securely',
                        'connection_type': 'data_flow'
                    },
                    {
                        'component': 'frontend_ui',
                        'reason': 'Users need login forms and profile pages',
                        'connection_type': 'user_interface'
                    }
                ])
            
            elif added_component.name == 'Database':
                if not any(comp.name == 'User Login' for comp in existing_components.values()):
                    suggestions.append({
                        'component': 'user_authentication',
                        'reason': 'Protect your database with user authentication',
                        'connection_type': 'security'
                    })
                
                suggestions.append({
                    'component': 'api_service',
                    'reason': 'API service can safely access your database',
                    'connection_type': 'data_access'
                })
        
        return suggestions

class AutoLayoutEngine:
    """Engine for automatic component layout"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def arrange_components(self, components: Dict[str, VisualComponent], 
                          connections: List[Dict[str, Any]], 
                          layout_type: LayoutType) -> Dict[str, Any]:
        """Arrange components according to layout type"""
        
        if layout_type == LayoutType.GRID:
            return self._arrange_grid_layout(components)
        elif layout_type == LayoutType.FLOW:
            return self._arrange_flow_layout(components, connections)
        elif layout_type == LayoutType.LAYERED:
            return self._arrange_layered_layout(components)
        elif layout_type == LayoutType.MINDMAP:
            return self._arrange_mindmap_layout(components, connections)
        else:
            return {'success': False, 'error': 'Unsupported layout type'}
    
    def _arrange_grid_layout(self, components: Dict[str, VisualComponent]) -> Dict[str, Any]:
        """Arrange components in a grid"""
        
        positions = {}
        grid_cols = 4
        grid_spacing = 200
        start_x, start_y = 50, 50
        
        for i, (comp_id, component) in enumerate(components.items()):
            if component.is_locked:
                positions[comp_id] = component.position
                continue
            
            col = i % grid_cols
            row = i // grid_cols
            
            x = start_x + col * grid_spacing
            y = start_y + row * grid_spacing
            
            positions[comp_id] = (x, y)
        
        return {
            'success': True,
            'positions': positions,
            'metrics': {
                'arrangement_type': 'grid',
                'rows': len(components) // grid_cols + 1,
                'columns': min(grid_cols, len(components))
            }
        }
    
    def _arrange_flow_layout(self, components: Dict[str, VisualComponent], 
                           connections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Arrange components in a flow-based layout"""
        
        # Simplified flow layout - in production, this would use graph algorithms
        positions = {}
        
        # Find root components (no incoming connections)
        incoming_counts = {comp_id: 0 for comp_id in components.keys()}
        for conn in connections:
            if conn['target'] in incoming_counts:
                incoming_counts[conn['target']] += 1
        
        roots = [comp_id for comp_id, count in incoming_counts.items() if count == 0]
        
        # Arrange from left to right
        x_offset = 100
        y_offset = 100
        level_height = 150
        
        current_level = 0
        processed = set()
        
        def arrange_level(comp_ids, level):
            nonlocal positions
            y_spacing = 120
            start_y = y_offset + (len(comp_ids) - 1) * y_spacing // 2
            
            for i, comp_id in enumerate(comp_ids):
                if comp_id in components:
                    x = x_offset + level * 250
                    y = start_y + i * y_spacing
                    positions[comp_id] = (x, y)
                    processed.add(comp_id)
        
        # Start with root components
        if roots:
            arrange_level(roots, current_level)
            current_level += 1
            
            # Continue with connected components (simplified)
            remaining = set(components.keys()) - processed
            while remaining:
                next_level = []
                for comp_id in list(remaining):
                    # Add components connected from processed components
                    for conn in connections:
                        if conn['source'] in processed and conn['target'] == comp_id:
                            next_level.append(comp_id)
                            remaining.remove(comp_id)
                            break
                
                if not next_level:
                    # Add remaining components
                    next_level = list(remaining)
                    remaining.clear()
                
                arrange_level(next_level, current_level)
                current_level += 1
        else:
            # No connections, arrange in grid
            return self._arrange_grid_layout(components)
        
        return {
            'success': True,
            'positions': positions,
            'metrics': {
                'arrangement_type': 'flow',
                'levels': current_level,
                'root_components': len(roots)
            }
        }

class ConnectionValidator:
    """Validates component connections"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define valid connection types between component categories
        self.valid_connections = {
            ('core', 'core'): 'data_flow',
            ('core', 'ui_elements'): 'interface',
            ('core', 'integrations'): 'service_call',
            ('core', 'advanced'): 'data_processing',
            ('ui_elements', 'core'): 'user_action',
            ('integrations', 'core'): 'external_data',
            ('advanced', 'core'): 'processed_data'
        }
    
    def validate_connection(self, source: VisualComponent, target: VisualComponent, 
                          all_components: Dict[str, VisualComponent]) -> Dict[str, Any]:
        """Validate if two components can be connected"""
        
        # Check if connection already exists
        if target.id in source.connections:
            return {
                'valid': False,
                'reason': 'Components are already connected'
            }
        
        # Check if connection type is valid
        connection_key = (source.category.value, target.category.value)
        if connection_key not in self.valid_connections:
            return {
                'valid': False,
                'reason': f'Cannot connect {source.category.value} to {target.category.value}'
            }
        
        # Check for circular dependencies (simplified)
        if self._would_create_cycle(source.id, target.id, all_components):
            return {
                'valid': False,
                'reason': 'Connection would create circular dependency'
            }
        
        # Determine connection style
        connection_type = self.valid_connections[connection_key]
        style = self._get_connection_style(connection_type)
        
        return {
            'valid': True,
            'connection_type': connection_type,
            'style': style
        }
    
    def _would_create_cycle(self, source_id: str, target_id: str, 
                           components: Dict[str, VisualComponent]) -> bool:
        """Check if connection would create a circular dependency"""
        
        # Simple cycle detection using DFS
        visited = set()
        
        def has_path(from_id: str, to_id: str) -> bool:
            if from_id == to_id:
                return True
            if from_id in visited:
                return False
            
            visited.add(from_id)
            
            if from_id in components:
                for connected_id in components[from_id].connections:
                    if has_path(connected_id, to_id):
                        return True
            
            return False
        
        return has_path(target_id, source_id)
    
    def _get_connection_style(self, connection_type: str) -> Dict[str, Any]:
        """Get visual style for connection type"""
        
        styles = {
            'data_flow': {
                'color': '#4A90E2',
                'width': 3,
                'pattern': 'solid',
                'arrow': True
            },
            'interface': {
                'color': '#BD10E0',
                'width': 2,
                'pattern': 'dashed',
                'arrow': True
            },
            'service_call': {
                'color': '#F5A623',
                'width': 2,
                'pattern': 'dotted',
                'arrow': True
            },
            'user_action': {
                'color': '#7ED321',
                'width': 2,
                'pattern': 'solid',
                'arrow': True
            }
        }
        
        return styles.get(connection_type, styles['data_flow'])

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize visual assembly engine
    assembly_engine = VisualAssemblyEngine()
    
    # Create a test canvas
    canvas_result = assembly_engine.create_canvas(
        user_id='test_user',
        app_concept='Social media app for photographers',
        preferences={
            'layout': 'grid',
            'snap_to_grid': True,
            'auto_arrange': False
        }
    )
    
    print("Canvas created successfully!")
    print(f"Canvas ID: {canvas_result['canvas_id']}")
    print(f"Initial suggestions: {len(canvas_result['initial_suggestions'])}")
    
    canvas_id = canvas_result['canvas_id']
    
    # Add some components
    components_to_add = [
        ('user_authentication', (100, 100)),
        ('database_storage', (300, 100)),
        ('frontend_ui', (500, 100)),
        ('api_service', (300, 250))
    ]
    
    for comp_type, position in components_to_add:
        result = assembly_engine.add_component(
            canvas_id, comp_type, position, 'test_user'
        )
        print(f"Added {comp_type}: {'Success' if result.get('success') else 'Failed'}")
    
    # Create some connections
    canvas = assembly_engine.active_canvases[canvas_id]
    component_ids = list(canvas.components.keys())
    
    if len(component_ids) >= 2:
        conn_result = assembly_engine.connect_components(
            canvas_id, component_ids[0], component_ids[1], 'test_user'
        )
        print(f"Connected components: {'Success' if conn_result.get('success') else 'Failed'}")
    
    # Auto-arrange components
    arrange_result = assembly_engine.auto_arrange_canvas(canvas_id, 'flow')
    print(f"Auto-arranged canvas: {'Success' if arrange_result.get('success') else 'Failed'}")
    
    # Generate preview
    preview_result = assembly_engine.get_assembly_preview(canvas_id)
    if 'preview' in preview_result:
        print(f"Preview generated - Completeness: {preview_result['completeness_score']:.1%}")
        print(f"Deployment ready: {preview_result['deployment_ready']}")
    
    print("\nVisual Assembly Interface test completed!")