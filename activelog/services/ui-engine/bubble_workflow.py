"""
Bubble Map Workflow Designer
Interactive bubble-based visual workflow creation system
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from pydantic import BaseModel
from datetime import datetime
import uuid
import json
import math

class BubbleNode(BaseModel):
    """Represents a bubble node in the workflow"""
    id: str
    type: str
    label: str
    description: str = ""
    position: Tuple[float, float]
    size: float = 60  # Bubble radius
    color: str = "#007acc"
    properties: Dict[str, Any] = {}
    inputs: List[str] = []  # Input data types
    outputs: List[str] = []  # Output data types
    metadata: Dict[str, Any] = {}

class BubbleConnection(BaseModel):
    """Connection between bubble nodes"""
    id: str
    source_id: str
    target_id: str
    label: str = ""
    data_type: str
    weight: float = 1.0  # Connection strength for layout algorithms
    style: Dict[str, Any] = {}  # Visual styling (color, thickness, etc.)

class WorkflowCluster(BaseModel):
    """Group of related bubbles"""
    id: str
    name: str
    bubble_ids: List[str]
    position: Tuple[float, float]
    color: str = "#f0f0f0"
    collapsed: bool = False

class BubbleWorkflow(BaseModel):
    """Complete bubble workflow definition"""
    id: str
    name: str
    description: str = ""
    bubbles: List[BubbleNode]
    connections: List[BubbleConnection]
    clusters: List[WorkflowCluster] = []
    canvas_properties: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class BubbleWorkflowDesigner:
    """Bubble map workflow designer engine"""
    
    def __init__(self):
        self.workflows: Dict[str, BubbleWorkflow] = {}
        self.bubble_templates = self._initialize_bubble_templates()
        self.physics_enabled = True
        self.auto_layout = True
        
    def _initialize_bubble_templates(self) -> Dict[str, Dict]:
        """Initialize bubble node templates"""
        return {
            "start": {
                "label": "Start",
                "description": "Workflow start point",
                "color": "#28a745",
                "size": 50,
                "inputs": [],
                "outputs": ["trigger"],
                "category": "flow"
            },
            "end": {
                "label": "End",
                "description": "Workflow end point", 
                "color": "#dc3545",
                "size": 50,
                "inputs": ["any"],
                "outputs": [],
                "category": "flow"
            },
            "decision": {
                "label": "Decision",
                "description": "Conditional branch point",
                "color": "#ffc107",
                "size": 70,
                "inputs": ["boolean", "data"],
                "outputs": ["true", "false"],
                "category": "logic"
            },
            "process": {
                "label": "Process",
                "description": "Data processing step",
                "color": "#17a2b8",
                "size": 60,
                "inputs": ["data"],
                "outputs": ["data"],
                "category": "processing"
            },
            "input": {
                "label": "Input",
                "description": "User input collection",
                "color": "#6c757d",
                "size": 55,
                "inputs": [],
                "outputs": ["data"],
                "category": "data"
            },
            "output": {
                "label": "Output",
                "description": "Display or export data",
                "color": "#6f42c1",
                "size": 55,
                "inputs": ["data"],
                "outputs": [],
                "category": "data"
            },
            "api": {
                "label": "API Call",
                "description": "External API integration",
                "color": "#fd7e14",
                "size": 65,
                "inputs": ["request"],
                "outputs": ["response", "error"],
                "category": "integration"
            },
            "database": {
                "label": "Database",
                "description": "Database operation",
                "color": "#20c997",
                "size": 65,
                "inputs": ["query", "data"],
                "outputs": ["result"],
                "category": "storage"
            },
            "transform": {
                "label": "Transform",
                "description": "Data transformation",
                "color": "#e83e8c",
                "size": 60,
                "inputs": ["data", "rules"],
                "outputs": ["transformed"],
                "category": "processing"
            },
            "filter": {
                "label": "Filter",
                "description": "Data filtering",
                "color": "#6610f2",
                "size": 58,
                "inputs": ["data", "criteria"],
                "outputs": ["filtered"],
                "category": "processing"
            },
            "aggregate": {
                "label": "Aggregate",
                "description": "Data aggregation",
                "color": "#198754",
                "size": 62,
                "inputs": ["data"],
                "outputs": ["aggregated"],
                "category": "processing"
            },
            "loop": {
                "label": "Loop",
                "description": "Iterative processing",
                "color": "#0dcaf0",
                "size": 68,
                "inputs": ["data", "condition"],
                "outputs": ["item", "complete"],
                "category": "control"
            },
            "parallel": {
                "label": "Parallel",
                "description": "Parallel execution",
                "color": "#fd7e14",
                "size": 70,
                "inputs": ["data"],
                "outputs": ["branch1", "branch2", "branch3"],
                "category": "control"
            },
            "merge": {
                "label": "Merge",
                "description": "Merge parallel branches",
                "color": "#6f42c1",
                "size": 65,
                "inputs": ["branch1", "branch2", "branch3"],
                "outputs": ["merged"],
                "category": "control"
            }
        }
    
    def create_workflow(self, name: str, description: str = "") -> str:
        """Create a new bubble workflow"""
        workflow_id = str(uuid.uuid4())
        workflow = BubbleWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            bubbles=[],
            connections=[],
            canvas_properties={
                "zoom": 1.0,
                "pan_x": 0,
                "pan_y": 0,
                "grid_size": 20,
                "show_grid": True
            }
        )
        self.workflows[workflow_id] = workflow
        return workflow_id
    
    def add_bubble(self, workflow_id: str, bubble_type: str, position: Tuple[float, float], 
                   custom_properties: Dict[str, Any] = None) -> str:
        """Add a bubble to the workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if bubble_type not in self.bubble_templates:
            raise ValueError(f"Bubble type {bubble_type} not found")
        
        template = self.bubble_templates[bubble_type]
        bubble_id = str(uuid.uuid4())
        
        bubble = BubbleNode(
            id=bubble_id,
            type=bubble_type,
            label=template["label"],
            description=template["description"],
            position=position,
            size=template["size"],
            color=template["color"],
            inputs=template["inputs"].copy(),
            outputs=template["outputs"].copy(),
            properties=custom_properties or {}
        )
        
        self.workflows[workflow_id].bubbles.append(bubble)
        
        if self.auto_layout:
            self._apply_auto_layout(workflow_id)
            
        return bubble_id
    
    def connect_bubbles(self, workflow_id: str, source_id: str, target_id: str, 
                       data_type: str = "data", label: str = "") -> str:
        """Connect two bubbles"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        # Find source and target bubbles
        source_bubble = next((b for b in workflow.bubbles if b.id == source_id), None)
        target_bubble = next((b for b in workflow.bubbles if b.id == target_id), None)
        
        if not source_bubble or not target_bubble:
            raise ValueError("Source or target bubble not found")
        
        # Validate connection
        if data_type not in source_bubble.outputs and "any" not in source_bubble.outputs:
            raise ValueError(f"Source bubble doesn't output {data_type}")
        
        if data_type not in target_bubble.inputs and "any" not in target_bubble.inputs:
            raise ValueError(f"Target bubble doesn't accept {data_type}")
        
        connection_id = str(uuid.uuid4())
        connection = BubbleConnection(
            id=connection_id,
            source_id=source_id,
            target_id=target_id,
            label=label,
            data_type=data_type,
            style={
                "color": self._get_data_type_color(data_type),
                "thickness": 2
            }
        )
        
        workflow.connections.append(connection)
        return connection_id
    
    def _get_data_type_color(self, data_type: str) -> str:
        """Get color for data type"""
        colors = {
            "data": "#007acc",
            "trigger": "#28a745",
            "boolean": "#ffc107",
            "request": "#fd7e14",
            "response": "#17a2b8",
            "error": "#dc3545",
            "any": "#6c757d"
        }
        return colors.get(data_type, "#6c757d")
    
    def move_bubble(self, workflow_id: str, bubble_id: str, position: Tuple[float, float]):
        """Move a bubble to new position"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        bubble = next((b for b in workflow.bubbles if b.id == bubble_id), None)
        if bubble:
            bubble.position = position
    
    def resize_bubble(self, workflow_id: str, bubble_id: str, size: float):
        """Resize a bubble"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        bubble = next((b for b in workflow.bubbles if b.id == bubble_id), None)
        if bubble:
            bubble.size = max(30, min(100, size))  # Clamp size
    
    def update_bubble_properties(self, workflow_id: str, bubble_id: str, properties: Dict[str, Any]):
        """Update bubble properties"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        bubble = next((b for b in workflow.bubbles if b.id == bubble_id), None)
        if bubble:
            bubble.properties.update(properties)
    
    def create_cluster(self, workflow_id: str, name: str, bubble_ids: List[str]) -> str:
        """Create a cluster of bubbles"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        # Calculate cluster center position
        positions = []
        for bubble_id in bubble_ids:
            bubble = next((b for b in workflow.bubbles if b.id == bubble_id), None)
            if bubble:
                positions.append(bubble.position)
        
        if positions:
            center_x = sum(pos[0] for pos in positions) / len(positions)
            center_y = sum(pos[1] for pos in positions) / len(positions)
        else:
            center_x, center_y = 0, 0
        
        cluster_id = str(uuid.uuid4())
        cluster = WorkflowCluster(
            id=cluster_id,
            name=name,
            bubble_ids=bubble_ids,
            position=(center_x, center_y)
        )
        
        workflow.clusters.append(cluster)
        return cluster_id
    
    def _apply_auto_layout(self, workflow_id: str):
        """Apply automatic layout to workflow bubbles"""
        if workflow_id not in self.workflows:
            return
        
        workflow = self.workflows[workflow_id]
        if len(workflow.bubbles) < 2:
            return
        
        # Simple force-directed layout
        bubbles = workflow.bubbles
        connections = workflow.connections
        
        # Initialize positions if not set
        for i, bubble in enumerate(bubbles):
            if bubble.position == (0, 0):
                angle = (2 * math.pi * i) / len(bubbles)
                radius = 200
                bubble.position = (
                    radius * math.cos(angle),
                    radius * math.sin(angle)
                )
        
        # Apply layout iterations
        for iteration in range(50):
            forces = {bubble.id: [0.0, 0.0] for bubble in bubbles}
            
            # Repulsion forces (bubbles repel each other)
            for i, bubble1 in enumerate(bubbles):
                for j, bubble2 in enumerate(bubbles):
                    if i != j:
                        dx = bubble2.position[0] - bubble1.position[0]
                        dy = bubble2.position[1] - bubble1.position[1]
                        distance = math.sqrt(dx*dx + dy*dy) + 0.1
                        
                        repulsion = 1000 / (distance * distance)
                        forces[bubble1.id][0] -= repulsion * dx / distance
                        forces[bubble1.id][1] -= repulsion * dy / distance
            
            # Attraction forces (connected bubbles attract)
            for connection in connections:
                source = next(b for b in bubbles if b.id == connection.source_id)
                target = next(b for b in bubbles if b.id == connection.target_id)
                
                dx = target.position[0] - source.position[0]
                dy = target.position[1] - source.position[1]
                distance = math.sqrt(dx*dx + dy*dy) + 0.1
                
                attraction = distance * 0.01
                forces[source.id][0] += attraction * dx / distance
                forces[source.id][1] += attraction * dy / distance
                forces[target.id][0] -= attraction * dx / distance
                forces[target.id][1] -= attraction * dy / distance
            
            # Apply forces with damping
            damping = 0.9
            for bubble in bubbles:
                force = forces[bubble.id]
                new_x = bubble.position[0] + force[0] * damping
                new_y = bubble.position[1] + force[1] * damping
                bubble.position = (new_x, new_y)
    
    def get_execution_path(self, workflow_id: str) -> List[List[str]]:
        """Get possible execution paths through the workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        # Find start nodes
        start_nodes = [b.id for b in workflow.bubbles if b.type == "start"]
        if not start_nodes:
            start_nodes = [b.id for b in workflow.bubbles if not any(
                c.target_id == b.id for c in workflow.connections
            )]
        
        paths = []
        for start_node in start_nodes:
            path = self._trace_path(workflow, start_node, [])
            if path:
                paths.append(path)
        
        return paths
    
    def _trace_path(self, workflow: BubbleWorkflow, current_id: str, visited: List[str]) -> List[str]:
        """Recursively trace execution path"""
        if current_id in visited:
            return visited  # Avoid cycles
        
        path = visited + [current_id]
        
        # Find next nodes
        next_connections = [c for c in workflow.connections if c.source_id == current_id]
        
        if not next_connections:
            return path  # End of path
        
        # For now, just follow the first connection (in real implementation, handle branches)
        next_id = next_connections[0].target_id
        return self._trace_path(workflow, next_id, path)
    
    def validate_workflow(self, workflow_id: str) -> Dict[str, List[str]]:
        """Validate workflow for completeness and correctness"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        errors = []
        warnings = []
        
        # Check for start and end nodes
        start_nodes = [b for b in workflow.bubbles if b.type == "start"]
        end_nodes = [b for b in workflow.bubbles if b.type == "end"]
        
        if not start_nodes:
            warnings.append("No start node found")
        if not end_nodes:
            warnings.append("No end node found")
        
        # Check for disconnected bubbles
        connected_bubbles = set()
        for connection in workflow.connections:
            connected_bubbles.add(connection.source_id)
            connected_bubbles.add(connection.target_id)
        
        for bubble in workflow.bubbles:
            if bubble.id not in connected_bubbles and bubble.type not in ["start", "end"]:
                warnings.append(f"Bubble '{bubble.label}' is not connected")
        
        # Check for cycles
        if self._has_cycles(workflow):
            errors.append("Workflow contains cycles")
        
        # Check data type compatibility
        for connection in workflow.connections:
            source = next(b for b in workflow.bubbles if b.id == connection.source_id)
            target = next(b for b in workflow.bubbles if b.id == connection.target_id)
            
            if (connection.data_type not in source.outputs and "any" not in source.outputs):
                errors.append(f"Invalid output type '{connection.data_type}' from '{source.label}'")
            
            if (connection.data_type not in target.inputs and "any" not in target.inputs):
                errors.append(f"Invalid input type '{connection.data_type}' to '{target.label}'")
        
        return {"errors": errors, "warnings": warnings}
    
    def _has_cycles(self, workflow: BubbleWorkflow) -> bool:
        """Check if workflow has cycles"""
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            # Find connected nodes
            for connection in workflow.connections:
                if connection.source_id == node_id:
                    target_id = connection.target_id
                    if target_id not in visited:
                        if dfs(target_id):
                            return True
                    elif target_id in rec_stack:
                        return True
            
            rec_stack.remove(node_id)
            return False
        
        for bubble in workflow.bubbles:
            if bubble.id not in visited:
                if dfs(bubble.id):
                    return True
        
        return False
    
    def export_workflow(self, workflow_id: str) -> Dict:
        """Export workflow to JSON"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        return {
            "workflow": workflow.dict(),
            "templates": self.bubble_templates,
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }
    
    def import_workflow(self, workflow_data: Dict) -> str:
        """Import workflow from JSON"""
        workflow_dict = workflow_data.get("workflow", {})
        workflow = BubbleWorkflow(**workflow_dict)
        workflow.id = str(uuid.uuid4())  # Generate new ID
        
        self.workflows[workflow.id] = workflow
        return workflow.id
    
    def get_workflow(self, workflow_id: str) -> Optional[BubbleWorkflow]:
        """Get workflow by ID"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict]:
        """List all workflows"""
        return [
            {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "bubble_count": len(workflow.bubbles),
                "connection_count": len(workflow.connections)
            }
            for workflow in self.workflows.values()
        ]
    
    def get_bubble_templates(self) -> Dict[str, Dict]:
        """Get available bubble templates"""
        return self.bubble_templates