"""
Drag-Drop Component Library
Comprehensive library of reusable UI components with drag-and-drop functionality
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from pydantic import BaseModel
from datetime import datetime
import json
import uuid

class ComponentProperty(BaseModel):
    """Component property definition"""
    name: str
    type: str  # "string", "number", "boolean", "color", "select", "array", "object"
    default: Any = None
    required: bool = False
    description: str = ""
    options: List[Any] = []  # For select types
    validation: Dict[str, Any] = {}  # Validation rules
    group: str = "general"  # Property group for organization

class ComponentEvent(BaseModel):
    """Component event definition"""
    name: str
    description: str
    parameters: Dict[str, str] = {}  # Parameter name -> type mapping
    examples: List[str] = []

class ComponentSlot(BaseModel):
    """Component slot for child components"""
    name: str
    description: str
    accepts: List[str] = []  # Component types that can be placed in this slot
    required: bool = False
    multiple: bool = False

class ComponentDefinition(BaseModel):
    """Complete component definition"""
    id: str
    name: str
    category: str
    description: str
    icon: str = ""
    tags: List[str] = []
    properties: List[ComponentProperty]
    events: List[ComponentEvent] = []
    slots: List[ComponentSlot] = []
    dependencies: List[str] = []  # Required libraries/frameworks
    preview_code: str = ""  # HTML/JSX for preview
    documentation: str = ""
    version: str = "1.0.0"
    author: str = ""
    license: str = "MIT"
    is_premium: bool = False
    download_count: int = 0
    rating: float = 0.0
    created_at: datetime
    updated_at: datetime

class ComponentInstance(BaseModel):
    """Instance of a component in a project"""
    id: str
    definition_id: str
    name: str
    properties: Dict[str, Any] = {}
    position: Tuple[float, float] = (0, 0)
    size: Tuple[float, float] = (100, 100)
    rotation: float = 0.0
    z_index: int = 1
    locked: bool = False
    visible: bool = True
    parent_id: Optional[str] = None
    children: List[str] = []
    metadata: Dict[str, Any] = {}

class DragDropState(BaseModel):
    """State for drag-and-drop operations"""
    is_dragging: bool = False
    drag_component_id: Optional[str] = None
    drag_offset: Tuple[float, float] = (0, 0)
    drop_target_id: Optional[str] = None
    drop_position: Tuple[float, float] = (0, 0)
    ghost_enabled: bool = True

class ComponentLibrary:
    """Drag-drop component library manager"""
    
    def __init__(self):
        self.components: Dict[str, ComponentDefinition] = {}
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.instances: Dict[str, ComponentInstance] = {}
        self.drag_state = DragDropState()
        
        # Initialize with built-in components
        self._initialize_builtin_components()
        self._initialize_categories()
    
    def _initialize_categories(self):
        """Initialize component categories"""
        self.categories = {
            "layout": {
                "name": "Layout",
                "description": "Layout and container components",
                "icon": "layout",
                "color": "#6c5ce7"
            },
            "forms": {
                "name": "Forms",
                "description": "Form controls and inputs",
                "icon": "edit",
                "color": "#00b894"
            },
            "data": {
                "name": "Data",
                "description": "Data display components",
                "icon": "database",
                "color": "#0984e3"
            },
            "media": {
                "name": "Media",
                "description": "Images, videos, and media",
                "icon": "image",
                "color": "#e17055"
            },
            "navigation": {
                "name": "Navigation",
                "description": "Navigation and menu components",
                "icon": "menu",
                "color": "#a29bfe"
            },
            "feedback": {
                "name": "Feedback",
                "description": "Alerts, notifications, and feedback",
                "icon": "bell",
                "color": "#fdcb6e"
            },
            "charts": {
                "name": "Charts",
                "description": "Data visualization components",
                "icon": "bar-chart",
                "color": "#55a3ff"
            },
            "social": {
                "name": "Social",
                "description": "Social media and sharing components",
                "icon": "share",
                "color": "#ff6b6b"
            },
            "commerce": {
                "name": "Commerce",
                "description": "E-commerce components",
                "icon": "shopping-cart",
                "color": "#26de81"
            },
            "advanced": {
                "name": "Advanced",
                "description": "Advanced and specialized components",
                "icon": "settings",
                "color": "#fd79a8"
            }
        }
    
    def _initialize_builtin_components(self):
        """Initialize built-in components"""
        
        # Container components
        self._add_builtin_component({
            "id": "container",
            "name": "Container",
            "category": "layout",
            "description": "Generic container for other components",
            "icon": "square",
            "properties": [
                {"name": "padding", "type": "string", "default": "16px", "description": "Inner padding"},
                {"name": "margin", "type": "string", "default": "0px", "description": "Outer margin"},
                {"name": "backgroundColor", "type": "color", "default": "transparent", "description": "Background color"},
                {"name": "borderRadius", "type": "string", "default": "0px", "description": "Border radius"},
                {"name": "border", "type": "string", "default": "none", "description": "Border style"},
                {"name": "shadow", "type": "select", "default": "none", "options": ["none", "sm", "md", "lg"], "description": "Box shadow"},
                {"name": "maxWidth", "type": "string", "default": "none", "description": "Maximum width"}
            ],
            "slots": [{"name": "default", "description": "Main content area", "multiple": True}],
            "preview_code": '<div class="container">Content goes here</div>'
        })
        
        # Button component
        self._add_builtin_component({
            "id": "button",
            "name": "Button",
            "category": "forms",
            "description": "Interactive button component",
            "icon": "square",
            "properties": [
                {"name": "text", "type": "string", "default": "Button", "required": True, "description": "Button text"},
                {"name": "variant", "type": "select", "default": "primary", "options": ["primary", "secondary", "success", "danger", "warning", "info"], "description": "Button style variant"},
                {"name": "size", "type": "select", "default": "medium", "options": ["small", "medium", "large"], "description": "Button size"},
                {"name": "disabled", "type": "boolean", "default": False, "description": "Disabled state"},
                {"name": "loading", "type": "boolean", "default": False, "description": "Loading state"},
                {"name": "icon", "type": "string", "default": "", "description": "Icon name"},
                {"name": "iconPosition", "type": "select", "default": "left", "options": ["left", "right"], "description": "Icon position"}
            ],
            "events": [
                {"name": "onClick", "description": "Fired when button is clicked", "parameters": {"event": "MouseEvent"}},
                {"name": "onFocus", "description": "Fired when button receives focus"},
                {"name": "onBlur", "description": "Fired when button loses focus"}
            ],
            "preview_code": '<button class="btn btn-primary">Button</button>'
        })
        
        # Input component
        self._add_builtin_component({
            "id": "input",
            "name": "Text Input",
            "category": "forms",
            "description": "Text input field",
            "icon": "edit",
            "properties": [
                {"name": "placeholder", "type": "string", "default": "Enter text...", "description": "Placeholder text"},
                {"name": "value", "type": "string", "default": "", "description": "Input value"},
                {"name": "type", "type": "select", "default": "text", "options": ["text", "email", "password", "number", "tel", "url"], "description": "Input type"},
                {"name": "required", "type": "boolean", "default": False, "description": "Required field"},
                {"name": "disabled", "type": "boolean", "default": False, "description": "Disabled state"},
                {"name": "maxLength", "type": "number", "default": None, "description": "Maximum character length"},
                {"name": "pattern", "type": "string", "default": "", "description": "Validation pattern (regex)"},
                {"name": "autoComplete", "type": "string", "default": "", "description": "Autocomplete attribute"}
            ],
            "events": [
                {"name": "onChange", "description": "Fired when input value changes", "parameters": {"value": "string", "event": "Event"}},
                {"name": "onFocus", "description": "Fired when input receives focus"},
                {"name": "onBlur", "description": "Fired when input loses focus"},
                {"name": "onKeyPress", "description": "Fired when key is pressed", "parameters": {"key": "string", "event": "KeyboardEvent"}}
            ],
            "preview_code": '<input type="text" placeholder="Enter text..." class="form-input" />'
        })
        
        # Image component
        self._add_builtin_component({
            "id": "image",
            "name": "Image",
            "category": "media",
            "description": "Image display component",
            "icon": "image",
            "properties": [
                {"name": "src", "type": "string", "required": True, "description": "Image source URL"},
                {"name": "alt", "type": "string", "default": "", "description": "Alternative text"},
                {"name": "width", "type": "string", "default": "auto", "description": "Image width"},
                {"name": "height", "type": "string", "default": "auto", "description": "Image height"},
                {"name": "objectFit", "type": "select", "default": "cover", "options": ["cover", "contain", "fill", "scale-down"], "description": "Object fit behavior"},
                {"name": "borderRadius", "type": "string", "default": "0px", "description": "Border radius"},
                {"name": "lazy", "type": "boolean", "default": True, "description": "Lazy loading"}
            ],
            "events": [
                {"name": "onLoad", "description": "Fired when image loads"},
                {"name": "onError", "description": "Fired when image fails to load"},
                {"name": "onClick", "description": "Fired when image is clicked"}
            ],
            "preview_code": '<img src="/placeholder.jpg" alt="Image" class="image" />'
        })
        
        # Card component
        self._add_builtin_component({
            "id": "card",
            "name": "Card",
            "category": "layout",
            "description": "Card container with header, body, and footer",
            "icon": "credit-card",
            "properties": [
                {"name": "title", "type": "string", "default": "", "description": "Card title"},
                {"name": "subtitle", "type": "string", "default": "", "description": "Card subtitle"},
                {"name": "shadow", "type": "select", "default": "md", "options": ["none", "sm", "md", "lg"], "description": "Card shadow"},
                {"name": "padding", "type": "string", "default": "20px", "description": "Card padding"},
                {"name": "borderRadius", "type": "string", "default": "8px", "description": "Border radius"}
            ],
            "slots": [
                {"name": "header", "description": "Card header area"},
                {"name": "body", "description": "Card main content", "required": True, "multiple": True},
                {"name": "footer", "description": "Card footer area"}
            ],
            "preview_code": '<div class="card"><div class="card-header">Title</div><div class="card-body">Content</div></div>'
        })
        
        # Table component
        self._add_builtin_component({
            "id": "table",
            "name": "Data Table",
            "category": "data",
            "description": "Data table with sorting and filtering",
            "icon": "table",
            "properties": [
                {"name": "columns", "type": "array", "required": True, "description": "Table columns configuration"},
                {"name": "data", "type": "array", "default": [], "description": "Table data"},
                {"name": "sortable", "type": "boolean", "default": True, "description": "Enable sorting"},
                {"name": "filterable", "type": "boolean", "default": False, "description": "Enable filtering"},
                {"name": "pagination", "type": "boolean", "default": False, "description": "Enable pagination"},
                {"name": "pageSize", "type": "number", "default": 10, "description": "Items per page"},
                {"name": "striped", "type": "boolean", "default": True, "description": "Striped rows"},
                {"name": "bordered", "type": "boolean", "default": True, "description": "Table borders"}
            ],
            "events": [
                {"name": "onRowClick", "description": "Fired when row is clicked", "parameters": {"row": "object", "index": "number"}},
                {"name": "onSort", "description": "Fired when column is sorted", "parameters": {"column": "string", "direction": "string"}},
                {"name": "onFilter", "description": "Fired when filter changes"}
            ],
            "preview_code": '<table class="data-table"><thead><tr><th>Column 1</th><th>Column 2</th></tr></thead><tbody><tr><td>Data</td><td>Data</td></tr></tbody></table>'
        })
        
        # Chart component
        self._add_builtin_component({
            "id": "chart",
            "name": "Chart",
            "category": "charts",
            "description": "Data visualization chart",
            "icon": "bar-chart",
            "properties": [
                {"name": "type", "type": "select", "default": "line", "options": ["line", "bar", "pie", "area", "scatter"], "description": "Chart type"},
                {"name": "data", "type": "array", "required": True, "description": "Chart data"},
                {"name": "width", "type": "number", "default": 400, "description": "Chart width"},
                {"name": "height", "type": "number", "default": 300, "description": "Chart height"},
                {"name": "title", "type": "string", "default": "", "description": "Chart title"},
                {"name": "legend", "type": "boolean", "default": True, "description": "Show legend"},
                {"name": "grid", "type": "boolean", "default": True, "description": "Show grid lines"},
                {"name": "animation", "type": "boolean", "default": True, "description": "Enable animations"}
            ],
            "events": [
                {"name": "onDataPointClick", "description": "Fired when data point is clicked"},
                {"name": "onLegendClick", "description": "Fired when legend item is clicked"}
            ],
            "preview_code": '<div class="chart-container"><canvas class="chart"></canvas></div>'
        })
        
        # Modal component
        self._add_builtin_component({
            "id": "modal",
            "name": "Modal Dialog",
            "category": "feedback",
            "description": "Modal dialog overlay",
            "icon": "square",
            "properties": [
                {"name": "title", "type": "string", "default": "Modal Title", "description": "Modal title"},
                {"name": "size", "type": "select", "default": "medium", "options": ["small", "medium", "large", "fullscreen"], "description": "Modal size"},
                {"name": "closable", "type": "boolean", "default": True, "description": "Show close button"},
                {"name": "backdrop", "type": "boolean", "default": True, "description": "Show backdrop"},
                {"name": "backdropClose", "type": "boolean", "default": True, "description": "Close on backdrop click"},
                {"name": "escapeClose", "type": "boolean", "default": True, "description": "Close on escape key"}
            ],
            "slots": [
                {"name": "header", "description": "Modal header"},
                {"name": "body", "description": "Modal content", "required": True, "multiple": True},
                {"name": "footer", "description": "Modal footer with actions"}
            ],
            "events": [
                {"name": "onOpen", "description": "Fired when modal opens"},
                {"name": "onClose", "description": "Fired when modal closes"},
                {"name": "onBackdropClick", "description": "Fired when backdrop is clicked"}
            ],
            "preview_code": '<div class="modal"><div class="modal-content"><div class="modal-header">Title</div><div class="modal-body">Content</div></div></div>'
        })
    
    def _add_builtin_component(self, component_data: Dict[str, Any]):
        """Add a built-in component to the library"""
        component = ComponentDefinition(
            id=component_data["id"],
            name=component_data["name"],
            category=component_data["category"],
            description=component_data["description"],
            icon=component_data.get("icon", ""),
            properties=[ComponentProperty(**prop) for prop in component_data.get("properties", [])],
            events=[ComponentEvent(**event) for event in component_data.get("events", [])],
            slots=[ComponentSlot(**slot) for slot in component_data.get("slots", [])],
            preview_code=component_data.get("preview_code", ""),
            version="1.0.0",
            author="UI Engine",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.components[component.id] = component
    
    def add_component(self, component: ComponentDefinition) -> str:
        """Add custom component to library"""
        if not component.id:
            component.id = str(uuid.uuid4())
        
        component.created_at = datetime.now()
        component.updated_at = datetime.now()
        
        self.components[component.id] = component
        return component.id
    
    def get_component(self, component_id: str) -> Optional[ComponentDefinition]:
        """Get component definition by ID"""
        return self.components.get(component_id)
    
    def search_components(self, query: str = "", category: str = "", 
                         tags: List[str] = None) -> List[ComponentDefinition]:
        """Search components by query, category, or tags"""
        results = []
        query_lower = query.lower() if query else ""
        tags = tags or []
        
        for component in self.components.values():
            # Category filter
            if category and component.category != category:
                continue
            
            # Tag filter
            if tags and not any(tag in component.tags for tag in tags):
                continue
            
            # Text search
            if query_lower:
                searchable_text = f"{component.name} {component.description} {' '.join(component.tags)}".lower()
                if query_lower not in searchable_text:
                    continue
            
            results.append(component)
        
        # Sort by relevance (simplified)
        if query_lower:
            results.sort(key=lambda c: (
                query_lower in c.name.lower(),
                query_lower in c.description.lower(),
                c.download_count
            ), reverse=True)
        else:
            results.sort(key=lambda c: c.download_count, reverse=True)
        
        return results
    
    def get_components_by_category(self, category: str) -> List[ComponentDefinition]:
        """Get all components in a category"""
        return [comp for comp in self.components.values() if comp.category == category]
    
    def create_instance(self, component_id: str, name: str = None, 
                       position: Tuple[float, float] = (0, 0)) -> str:
        """Create component instance"""
        component = self.get_component(component_id)
        if not component:
            raise ValueError(f"Component {component_id} not found")
        
        instance_id = str(uuid.uuid4())
        
        # Initialize properties with defaults
        properties = {}
        for prop in component.properties:
            if prop.default is not None:
                properties[prop.name] = prop.default
        
        instance = ComponentInstance(
            id=instance_id,
            definition_id=component_id,
            name=name or f"{component.name} {len(self.instances) + 1}",
            properties=properties,
            position=position
        )
        
        self.instances[instance_id] = instance
        return instance_id
    
    def get_instance(self, instance_id: str) -> Optional[ComponentInstance]:
        """Get component instance"""
        return self.instances.get(instance_id)
    
    def update_instance(self, instance_id: str, updates: Dict[str, Any]):
        """Update component instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")
        
        for key, value in updates.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
    
    def delete_instance(self, instance_id: str):
        """Delete component instance"""
        if instance_id in self.instances:
            # Remove from parent's children
            instance = self.instances[instance_id]
            if instance.parent_id:
                parent = self.instances.get(instance.parent_id)
                if parent and instance_id in parent.children:
                    parent.children.remove(instance_id)
            
            # Remove children
            for child_id in instance.children:
                self.delete_instance(child_id)
            
            del self.instances[instance_id]
    
    def start_drag(self, component_id: str, position: Tuple[float, float]):
        """Start dragging a component"""
        self.drag_state.is_dragging = True
        self.drag_state.drag_component_id = component_id
        self.drag_state.drag_offset = position
        self.drag_state.drop_target_id = None
    
    def update_drag(self, position: Tuple[float, float], target_id: str = None):
        """Update drag position and target"""
        if not self.drag_state.is_dragging:
            return
        
        self.drag_state.drop_position = position
        self.drag_state.drop_target_id = target_id
    
    def end_drag(self, drop_position: Tuple[float, float] = None) -> Dict[str, Any]:
        """End drag operation and return result"""
        if not self.drag_state.is_dragging:
            return {"success": False, "error": "No drag operation in progress"}
        
        result = {
            "success": True,
            "component_id": self.drag_state.drag_component_id,
            "drop_target_id": self.drag_state.drop_target_id,
            "position": drop_position or self.drag_state.drop_position
        }
        
        # Create instance if dragging from library
        if self.drag_state.drag_component_id in self.components:
            instance_id = self.create_instance(
                self.drag_state.drag_component_id,
                position=result["position"]
            )
            result["instance_id"] = instance_id
        
        # Reset drag state
        self.drag_state = DragDropState()
        
        return result
    
    def cancel_drag(self):
        """Cancel drag operation"""
        self.drag_state = DragDropState()
    
    def can_drop(self, target_id: str, component_id: str) -> Dict[str, Any]:
        """Check if component can be dropped on target"""
        target_instance = self.instances.get(target_id)
        if not target_instance:
            return {"can_drop": True, "reason": "Dropping on canvas"}
        
        target_component = self.components.get(target_instance.definition_id)
        dropping_component = self.components.get(component_id)
        
        if not target_component or not dropping_component:
            return {"can_drop": False, "reason": "Component definition not found"}
        
        # Check if target has slots
        if not target_component.slots:
            return {"can_drop": False, "reason": "Target component doesn't accept children"}
        
        # Check slot restrictions
        for slot in target_component.slots:
            if not slot.accepts or dropping_component.category in slot.accepts:
                return {"can_drop": True, "slot": slot.name}
        
        return {"can_drop": False, "reason": "Component type not accepted by target slots"}
    
    def get_component_tree(self, root_id: str = None) -> Dict[str, Any]:
        """Get hierarchical component tree"""
        if root_id:
            root_instance = self.instances.get(root_id)
            if not root_instance:
                return {"error": "Root component not found"}
            
            return self._build_tree_node(root_instance)
        
        # Get all root components (no parent)
        root_instances = [inst for inst in self.instances.values() if not inst.parent_id]
        
        return {
            "roots": [self._build_tree_node(inst) for inst in root_instances]
        }
    
    def _build_tree_node(self, instance: ComponentInstance) -> Dict[str, Any]:
        """Build tree node for instance"""
        component = self.components.get(instance.definition_id)
        
        node = {
            "instance_id": instance.id,
            "component_id": instance.definition_id,
            "name": instance.name,
            "type": component.name if component else "Unknown",
            "position": instance.position,
            "size": instance.size,
            "visible": instance.visible,
            "locked": instance.locked,
            "children": []
        }
        
        # Add children recursively
        for child_id in instance.children:
            child_instance = self.instances.get(child_id)
            if child_instance:
                node["children"].append(self._build_tree_node(child_instance))
        
        return node
    
    def export_library(self) -> Dict[str, Any]:
        """Export component library"""
        return {
            "components": [comp.dict() for comp in self.components.values()],
            "categories": self.categories,
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "component_count": len(self.components)
            }
        }
    
    def import_library(self, library_data: Dict[str, Any]):
        """Import component library"""
        components_data = library_data.get("components", [])
        for comp_data in components_data:
            component = ComponentDefinition(**comp_data)
            component.id = str(uuid.uuid4())  # Generate new ID to avoid conflicts
            self.components[component.id] = component
    
    def get_categories(self) -> Dict[str, Dict[str, Any]]:
        """Get all component categories"""
        # Add component counts
        categories = self.categories.copy()
        for category_id, category in categories.items():
            category["component_count"] = len([
                comp for comp in self.components.values() 
                if comp.category == category_id
            ])
        
        return categories
    
    def get_popular_components(self, limit: int = 10) -> List[ComponentDefinition]:
        """Get most popular components"""
        components = list(self.components.values())
        components.sort(key=lambda c: (c.download_count, c.rating), reverse=True)
        return components[:limit]
    
    def get_recent_components(self, limit: int = 10) -> List[ComponentDefinition]:
        """Get recently added components"""
        components = list(self.components.values())
        components.sort(key=lambda c: c.created_at, reverse=True)
        return components[:limit]