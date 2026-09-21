"""
Visual Wiring System for App Building
Provides node-based visual programming interface
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
import json
import uuid
from datetime import datetime

class ConnectionPoint(BaseModel):
    """Represents a connection point on a component"""
    id: str
    type: str  # 'input' or 'output'
    data_type: str  # 'string', 'number', 'object', 'array', 'boolean'
    label: str
    required: bool = False
    multiple: bool = False  # Can accept multiple connections

class WireConnection(BaseModel):
    """Represents a wire connection between two components"""
    id: str
    source_component: str
    source_point: str
    target_component: str
    target_point: str
    data_type: str
    created_at: datetime
    
class VisualComponent(BaseModel):
    """Visual component with wiring capabilities"""
    id: str
    type: str
    name: str
    position: Tuple[float, float]
    size: Tuple[float, float]
    properties: Dict[str, Any]
    input_points: List[ConnectionPoint]
    output_points: List[ConnectionPoint]
    metadata: Dict[str, Any] = {}

class WiringCanvas(BaseModel):
    """Canvas containing visual components and wiring"""
    id: str
    name: str
    components: List[VisualComponent]
    connections: List[WireConnection]
    canvas_properties: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class WiringEngine:
    """Engine for managing visual wiring system"""
    
    def __init__(self):
        self.canvases: Dict[str, WiringCanvas] = {}
        self.component_templates = self._load_component_templates()
        
    def _load_component_templates(self) -> Dict[str, Dict]:
        """Load component templates with predefined connection points"""
        return {
            "data_source": {
                "name": "Data Source",
                "category": "data",
                "input_points": [
                    {"id": "config", "type": "input", "data_type": "object", "label": "Configuration", "required": True}
                ],
                "output_points": [
                    {"id": "data", "type": "output", "data_type": "array", "label": "Data Output", "multiple": True},
                    {"id": "error", "type": "output", "data_type": "string", "label": "Error Output"}
                ]
            },
            "filter": {
                "name": "Data Filter",
                "category": "processing",
                "input_points": [
                    {"id": "data", "type": "input", "data_type": "array", "label": "Input Data", "required": True},
                    {"id": "criteria", "type": "input", "data_type": "object", "label": "Filter Criteria"}
                ],
                "output_points": [
                    {"id": "filtered", "type": "output", "data_type": "array", "label": "Filtered Data"},
                    {"id": "count", "type": "output", "data_type": "number", "label": "Count"}
                ]
            },
            "transform": {
                "name": "Data Transform",
                "category": "processing",
                "input_points": [
                    {"id": "data", "type": "input", "data_type": "array", "label": "Input Data", "required": True},
                    {"id": "mapping", "type": "input", "data_type": "object", "label": "Transform Mapping"}
                ],
                "output_points": [
                    {"id": "transformed", "type": "output", "data_type": "array", "label": "Transformed Data"}
                ]
            },
            "chart": {
                "name": "Chart Display",
                "category": "visualization",
                "input_points": [
                    {"id": "data", "type": "input", "data_type": "array", "label": "Chart Data", "required": True},
                    {"id": "config", "type": "input", "data_type": "object", "label": "Chart Config"}
                ],
                "output_points": [
                    {"id": "click", "type": "output", "data_type": "object", "label": "Click Event"},
                    {"id": "selection", "type": "output", "data_type": "array", "label": "Selected Data"}
                ]
            },
            "table": {
                "name": "Data Table",
                "category": "visualization",
                "input_points": [
                    {"id": "data", "type": "input", "data_type": "array", "label": "Table Data", "required": True},
                    {"id": "columns", "type": "input", "data_type": "array", "label": "Column Config"}
                ],
                "output_points": [
                    {"id": "row_click", "type": "output", "data_type": "object", "label": "Row Click Event"},
                    {"id": "selection", "type": "output", "data_type": "array", "label": "Selected Rows"}
                ]
            },
            "form_input": {
                "name": "Form Input",
                "category": "controls",
                "input_points": [
                    {"id": "default_value", "type": "input", "data_type": "string", "label": "Default Value"},
                    {"id": "validation", "type": "input", "data_type": "object", "label": "Validation Rules"}
                ],
                "output_points": [
                    {"id": "value", "type": "output", "data_type": "string", "label": "Input Value"},
                    {"id": "change", "type": "output", "data_type": "string", "label": "Value Change Event"},
                    {"id": "valid", "type": "output", "data_type": "boolean", "label": "Validation Status"}
                ]
            },
            "button": {
                "name": "Action Button",
                "category": "controls",
                "input_points": [
                    {"id": "label", "type": "input", "data_type": "string", "label": "Button Label"},
                    {"id": "disabled", "type": "input", "data_type": "boolean", "label": "Disabled State"}
                ],
                "output_points": [
                    {"id": "click", "type": "output", "data_type": "object", "label": "Click Event"}
                ]
            },
            "api_call": {
                "name": "API Call",
                "category": "integration",
                "input_points": [
                    {"id": "url", "type": "input", "data_type": "string", "label": "API URL", "required": True},
                    {"id": "method", "type": "input", "data_type": "string", "label": "HTTP Method"},
                    {"id": "headers", "type": "input", "data_type": "object", "label": "Request Headers"},
                    {"id": "body", "type": "input", "data_type": "object", "label": "Request Body"},
                    {"id": "trigger", "type": "input", "data_type": "object", "label": "Trigger Signal"}
                ],
                "output_points": [
                    {"id": "response", "type": "output", "data_type": "object", "label": "API Response"},
                    {"id": "error", "type": "output", "data_type": "string", "label": "Error Output"},
                    {"id": "loading", "type": "output", "data_type": "boolean", "label": "Loading State"}
                ]
            },
            "conditional": {
                "name": "Conditional Logic",
                "category": "logic",
                "input_points": [
                    {"id": "condition", "type": "input", "data_type": "boolean", "label": "Condition", "required": True},
                    {"id": "true_value", "type": "input", "data_type": "object", "label": "True Value"},
                    {"id": "false_value", "type": "input", "data_type": "object", "label": "False Value"}
                ],
                "output_points": [
                    {"id": "result", "type": "output", "data_type": "object", "label": "Result"}
                ]
            },
            "loop": {
                "name": "Loop Iterator",
                "category": "logic",
                "input_points": [
                    {"id": "data", "type": "input", "data_type": "array", "label": "Data Array", "required": True},
                    {"id": "template", "type": "input", "data_type": "object", "label": "Item Template"}
                ],
                "output_points": [
                    {"id": "item", "type": "output", "data_type": "object", "label": "Current Item", "multiple": True},
                    {"id": "index", "type": "output", "data_type": "number", "label": "Current Index", "multiple": True}
                ]
            }
        }
    
    def create_canvas(self, name: str) -> str:
        """Create a new wiring canvas"""
        canvas_id = str(uuid.uuid4())
        canvas = WiringCanvas(
            id=canvas_id,
            name=name,
            components=[],
            connections=[]
        )
        self.canvases[canvas_id] = canvas
        return canvas_id
    
    def add_component(self, canvas_id: str, component_type: str, position: Tuple[float, float]) -> str:
        """Add a component to the canvas"""
        if canvas_id not in self.canvases:
            raise ValueError(f"Canvas {canvas_id} not found")
        
        if component_type not in self.component_templates:
            raise ValueError(f"Component type {component_type} not found")
        
        template = self.component_templates[component_type]
        component_id = str(uuid.uuid4())
        
        # Create connection points from template
        input_points = [
            ConnectionPoint(
                id=f"{component_id}_{point['id']}",
                **point
            ) for point in template.get("input_points", [])
        ]
        
        output_points = [
            ConnectionPoint(
                id=f"{component_id}_{point['id']}",
                **point
            ) for point in template.get("output_points", [])
        ]
        
        component = VisualComponent(
            id=component_id,
            type=component_type,
            name=template["name"],
            position=position,
            size=(150, 100),  # Default size
            properties={},
            input_points=input_points,
            output_points=output_points
        )
        
        self.canvases[canvas_id].components.append(component)
        return component_id
    
    def create_connection(self, canvas_id: str, source_component: str, source_point: str, 
                         target_component: str, target_point: str) -> str:
        """Create a wire connection between components"""
        if canvas_id not in self.canvases:
            raise ValueError(f"Canvas {canvas_id} not found")
        
        canvas = self.canvases[canvas_id]
        
        # Find source and target components
        source_comp = next((c for c in canvas.components if c.id == source_component), None)
        target_comp = next((c for c in canvas.components if c.id == target_component), None)
        
        if not source_comp or not target_comp:
            raise ValueError("Source or target component not found")
        
        # Find connection points
        source_point_obj = next((p for p in source_comp.output_points if p.id == source_point), None)
        target_point_obj = next((p for p in target_comp.input_points if p.id == target_point), None)
        
        if not source_point_obj or not target_point_obj:
            raise ValueError("Source or target connection point not found")
        
        # Validate data types match
        if source_point_obj.data_type != target_point_obj.data_type and target_point_obj.data_type != "object":
            raise ValueError(f"Data type mismatch: {source_point_obj.data_type} -> {target_point_obj.data_type}")
        
        # Check if target already has connection (unless it supports multiple)
        if not target_point_obj.multiple:
            existing = next((c for c in canvas.connections 
                           if c.target_component == target_component and c.target_point == target_point), None)
            if existing:
                raise ValueError("Target point already has a connection")
        
        connection_id = str(uuid.uuid4())
        connection = WireConnection(
            id=connection_id,
            source_component=source_component,
            source_point=source_point,
            target_component=target_component,
            target_point=target_point,
            data_type=source_point_obj.data_type,
            created_at=datetime.now()
        )
        
        canvas.connections.append(connection)
        return connection_id
    
    def remove_connection(self, canvas_id: str, connection_id: str):
        """Remove a wire connection"""
        if canvas_id not in self.canvases:
            raise ValueError(f"Canvas {canvas_id} not found")
        
        canvas = self.canvases[canvas_id]
        canvas.connections = [c for c in canvas.connections if c.id != connection_id]
    
    def move_component(self, canvas_id: str, component_id: str, position: Tuple[float, float]):
        """Move a component to new position"""
        if canvas_id not in self.canvases:
            raise ValueError(f"Canvas {canvas_id} not found")
        
        canvas = self.canvases[canvas_id]
        component = next((c for c in canvas.components if c.id == component_id), None)
        if component:
            component.position = position
    
    def update_component_properties(self, canvas_id: str, component_id: str, properties: Dict[str, Any]):
        """Update component properties"""
        if canvas_id not in self.canvases:
            raise ValueError(f"Canvas {canvas_id} not found")
        
        canvas = self.canvases[canvas_id]
        component = next((c for c in canvas.components if c.id == component_id), None)
        if component:
            component.properties.update(properties)
    
    def validate_canvas(self, canvas_id: str) -> Dict[str, List[str]]:
        """Validate canvas for errors and warnings"""
        if canvas_id not in self.canvases:
            raise ValueError(f"Canvas {canvas_id} not found")
        
        canvas = self.canvases[canvas_id]
        errors = []
        warnings = []
        
        # Check for required inputs not connected
        for component in canvas.components:
            for input_point in component.input_points:
                if input_point.required:
                    connected = any(c.target_point == input_point.id for c in canvas.connections)
                    if not connected:
                        errors.append(f"Required input '{input_point.label}' on component '{component.name}' is not connected")
        
        # Check for circular dependencies
        def has_circular_dependency(start_component: str, visited: set = None) -> bool:
            if visited is None:
                visited = set()
            
            if start_component in visited:
                return True
            
            visited.add(start_component)
            
            # Find all components this one connects to
            for connection in canvas.connections:
                if connection.source_component == start_component:
                    if has_circular_dependency(connection.target_component, visited.copy()):
                        return True
            
            return False
        
        for component in canvas.components:
            if has_circular_dependency(component.id):
                errors.append(f"Circular dependency detected involving component '{component.name}'")
                break
        
        # Check for orphaned components (no inputs or outputs connected)
        for component in canvas.components:
            has_input = any(c.target_component == component.id for c in canvas.connections)
            has_output = any(c.source_component == component.id for c in canvas.connections)
            
            if not has_input and not has_output and component.type not in ["data_source", "form_input"]:
                warnings.append(f"Component '{component.name}' has no connections")
        
        return {"errors": errors, "warnings": warnings}
    
    def generate_execution_plan(self, canvas_id: str) -> List[str]:
        """Generate execution plan for canvas components"""
        if canvas_id not in self.canvases:
            raise ValueError(f"Canvas {canvas_id} not found")
        
        canvas = self.canvases[canvas_id]
        execution_order = []
        processed = set()
        
        def can_execute(component_id: str) -> bool:
            """Check if component can be executed (all required inputs available)"""
            component = next(c for c in canvas.components if c.id == component_id)
            
            for input_point in component.input_points:
                if input_point.required:
                    # Check if this input has a connection from a processed component
                    connection = next(
                        (c for c in canvas.connections 
                         if c.target_component == component_id and c.target_point == input_point.id), 
                        None
                    )
                    if connection and connection.source_component not in processed:
                        return False
                    elif not connection:
                        return False
            return True
        
        # Start with components that have no required inputs (data sources)
        remaining = [c.id for c in canvas.components]
        
        while remaining:
            ready_components = [comp_id for comp_id in remaining if can_execute(comp_id)]
            
            if not ready_components:
                # Circular dependency or missing connections
                break
            
            # Execute ready components
            for comp_id in ready_components:
                execution_order.append(comp_id)
                processed.add(comp_id)
                remaining.remove(comp_id)
        
        return execution_order
    
    def export_canvas(self, canvas_id: str) -> Dict:
        """Export canvas to JSON format"""
        if canvas_id not in self.canvases:
            raise ValueError(f"Canvas {canvas_id} not found")
        
        canvas = self.canvases[canvas_id]
        return {
            "canvas": canvas.dict(),
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }
    
    def import_canvas(self, canvas_data: Dict) -> str:
        """Import canvas from JSON format"""
        canvas_dict = canvas_data.get("canvas", {})
        canvas = WiringCanvas(**canvas_dict)
        canvas.id = str(uuid.uuid4())  # Generate new ID
        
        self.canvases[canvas.id] = canvas
        return canvas.id
    
    def get_component_templates(self) -> Dict[str, Dict]:
        """Get available component templates"""
        return self.component_templates
    
    def get_canvas(self, canvas_id: str) -> Optional[WiringCanvas]:
        """Get canvas by ID"""
        return self.canvases.get(canvas_id)
    
    def list_canvases(self) -> List[Dict]:
        """List all canvases"""
        return [
            {
                "id": canvas.id,
                "name": canvas.name,
                "component_count": len(canvas.components),
                "connection_count": len(canvas.connections)
            }
            for canvas in self.canvases.values()
        ]