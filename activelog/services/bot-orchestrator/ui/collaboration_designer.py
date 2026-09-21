"""
Drag-and-Drop Collaboration Designer
Visual interface for designing multi-bot collaboration workflows
"""

from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import uuid
from dataclasses import dataclass, asdict
import asyncio

from ..collaboration.collaborative_executor import CollaborationPattern, CollaborationPlan
from ..director.claude_director import Task, TaskPriority
from ..synchronization.bot_synchronizer import SynchronizationBarrierType, CoordinationMode

logger = logging.getLogger(__name__)

@dataclass
class FlowNode:
    """Represents a node in the collaboration flow"""
    node_id: str
    node_type: str  # "task", "bot", "barrier", "condition", "start", "end"
    position: Dict[str, float]  # {"x": 100, "y": 200}
    config: Dict[str, Any]
    title: str
    description: str = ""
    inputs: List[str] = None
    outputs: List[str] = None
    
    def __post_init__(self):
        if self.inputs is None:
            self.inputs = []
        if self.outputs is None:
            self.outputs = []

@dataclass
class FlowConnection:
    """Represents a connection between nodes"""
    connection_id: str
    source_node: str
    source_port: str
    target_node: str
    target_port: str
    condition: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class CollaborationFlow:
    """Complete collaboration workflow"""
    flow_id: str
    name: str
    description: str
    pattern: CollaborationPattern
    nodes: Dict[str, FlowNode]
    connections: Dict[str, FlowConnection]
    created_at: datetime
    modified_at: datetime
    created_by: str
    validation_errors: List[str] = None
    is_valid: bool = False
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []

class CollaborationDesigner:
    """Visual drag-and-drop collaboration designer"""
    
    def __init__(self):
        self.flows: Dict[str, CollaborationFlow] = {}
        self.templates: Dict[str, CollaborationFlow] = {}
        self.websocket_connections: Set[WebSocket] = set()
        
        # Node type configurations
        self.node_types = {
            "start": {
                "title": "Start",
                "description": "Flow entry point",
                "inputs": [],
                "outputs": ["out"],
                "icon": "play-circle",
                "color": "#28a745"
            },
            "end": {
                "title": "End", 
                "description": "Flow exit point",
                "inputs": ["in"],
                "outputs": [],
                "icon": "stop-circle",
                "color": "#dc3545"
            },
            "task": {
                "title": "Task",
                "description": "Individual task execution",
                "inputs": ["in"],
                "outputs": ["success", "failure"],
                "icon": "check-circle",
                "color": "#007bff",
                "config_schema": {
                    "task_id": {"type": "string", "required": True},
                    "priority": {"type": "select", "options": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                    "timeout": {"type": "number", "default": 3600},
                    "retry_count": {"type": "number", "default": 3}
                }
            },
            "bot": {
                "title": "Bot Assignment",
                "description": "Assign specific bot to task",
                "inputs": ["in"],
                "outputs": ["out"],
                "icon": "robot",
                "color": "#6f42c1",
                "config_schema": {
                    "bot_id": {"type": "string", "required": True},
                    "capabilities": {"type": "multi-select", "options": ["coding", "analysis", "writing", "research"]},
                    "fallback_strategy": {"type": "select", "options": ["any", "similar", "fail"]}
                }
            },
            "barrier": {
                "title": "Synchronization Barrier",
                "description": "Wait for multiple paths to converge",
                "inputs": ["in1", "in2", "in3"],
                "outputs": ["out"],
                "icon": "pause-circle",
                "color": "#fd7e14",
                "config_schema": {
                    "barrier_type": {"type": "select", "options": ["CHECKPOINT", "MILESTONE", "DECISION_POINT"]},
                    "coordination_mode": {"type": "select", "options": ["STRICT", "FLEXIBLE", "LEADER_FOLLOWER"]},
                    "timeout": {"type": "number", "default": 300}
                }
            },
            "condition": {
                "title": "Conditional Branch",
                "description": "Branch based on condition",
                "inputs": ["in"],
                "outputs": ["true", "false"],
                "icon": "code-branch",
                "color": "#e83e8c",
                "config_schema": {
                    "condition": {"type": "textarea", "required": True},
                    "condition_type": {"type": "select", "options": ["success", "value", "custom"]}
                }
            },
            "parallel": {
                "title": "Parallel Split",
                "description": "Execute multiple branches in parallel",
                "inputs": ["in"],
                "outputs": ["out1", "out2", "out3"],
                "icon": "code-branch",
                "color": "#20c997"
            },
            "merge": {
                "title": "Merge",
                "description": "Merge multiple branches",
                "inputs": ["in1", "in2", "in3"],
                "outputs": ["out"],
                "icon": "code-merge",
                "color": "#6c757d"
            },
            "knowledge": {
                "title": "Knowledge Share",
                "description": "Share knowledge between bots",
                "inputs": ["in"],
                "outputs": ["out"],
                "icon": "brain",
                "color": "#17a2b8",
                "config_schema": {
                    "knowledge_type": {"type": "select", "options": ["context", "findings", "patterns", "all"]},
                    "target_bots": {"type": "multi-select", "options": []},
                    "access_level": {"type": "select", "options": ["PUBLIC", "RESTRICTED", "PRIVATE"]}
                }
            },
            "loop": {
                "title": "Loop",
                "description": "Repeat execution based on condition",
                "inputs": ["in", "continue"],
                "outputs": ["body", "exit"],
                "icon": "refresh",
                "color": "#ffc107",
                "config_schema": {
                    "max_iterations": {"type": "number", "default": 10},
                    "condition": {"type": "textarea", "required": True}
                }
            }
        }
        
        # Create default templates
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default collaboration flow templates"""
        # Simple Sequential Template
        sequential_flow = CollaborationFlow(
            flow_id="template_sequential",
            name="Sequential Processing",
            description="Tasks executed one after another",
            pattern=CollaborationPattern.PIPELINE,
            nodes={
                "start": FlowNode("start", "start", {"x": 50, "y": 200}, {}, "Start"),
                "task1": FlowNode("task1", "task", {"x": 200, "y": 200}, {"task_id": "task_1"}, "Task 1"),
                "task2": FlowNode("task2", "task", {"x": 350, "y": 200}, {"task_id": "task_2"}, "Task 2"),
                "task3": FlowNode("task3", "task", {"x": 500, "y": 200}, {"task_id": "task_3"}, "Task 3"),
                "end": FlowNode("end", "end", {"x": 650, "y": 200}, {}, "End")
            },
            connections={
                "conn1": FlowConnection("conn1", "start", "out", "task1", "in"),
                "conn2": FlowConnection("conn2", "task1", "success", "task2", "in"),
                "conn3": FlowConnection("conn3", "task2", "success", "task3", "in"),
                "conn4": FlowConnection("conn4", "task3", "success", "end", "in")
            },
            created_at=datetime.now(),
            modified_at=datetime.now(),
            created_by="system",
            is_valid=True
        )
        
        # Parallel Processing Template
        parallel_flow = CollaborationFlow(
            flow_id="template_parallel",
            name="Parallel Processing",
            description="Tasks executed simultaneously",
            pattern=CollaborationPattern.PARALLEL,
            nodes={
                "start": FlowNode("start", "start", {"x": 50, "y": 300}, {}, "Start"),
                "split": FlowNode("split", "parallel", {"x": 200, "y": 300}, {}, "Split"),
                "task1": FlowNode("task1", "task", {"x": 350, "y": 150}, {"task_id": "task_1"}, "Task 1"),
                "task2": FlowNode("task2", "task", {"x": 350, "y": 300}, {"task_id": "task_2"}, "Task 2"),
                "task3": FlowNode("task3", "task", {"x": 350, "y": 450}, {"task_id": "task_3"}, "Task 3"),
                "merge": FlowNode("merge", "merge", {"x": 500, "y": 300}, {}, "Merge"),
                "end": FlowNode("end", "end", {"x": 650, "y": 300}, {}, "End")
            },
            connections={
                "conn1": FlowConnection("conn1", "start", "out", "split", "in"),
                "conn2": FlowConnection("conn2", "split", "out1", "task1", "in"),
                "conn3": FlowConnection("conn3", "split", "out2", "task2", "in"),
                "conn4": FlowConnection("conn4", "split", "out3", "task3", "in"),
                "conn5": FlowConnection("conn5", "task1", "success", "merge", "in1"),
                "conn6": FlowConnection("conn6", "task2", "success", "merge", "in2"),
                "conn7": FlowConnection("conn7", "task3", "success", "merge", "in3"),
                "conn8": FlowConnection("conn8", "merge", "out", "end", "in")
            },
            created_at=datetime.now(),
            modified_at=datetime.now(),
            created_by="system",
            is_valid=True
        )
        
        # Hierarchical Template with Decision Points
        hierarchical_flow = CollaborationFlow(
            flow_id="template_hierarchical",
            name="Hierarchical with Decisions",
            description="Hierarchical structure with conditional branches",
            pattern=CollaborationPattern.HIERARCHICAL,
            nodes={
                "start": FlowNode("start", "start", {"x": 50, "y": 300}, {}, "Start"),
                "leader": FlowNode("leader", "bot", {"x": 200, "y": 300}, {"bot_id": "leader_bot"}, "Leader Bot"),
                "analysis": FlowNode("analysis", "task", {"x": 350, "y": 300}, {"task_id": "analysis_task"}, "Analysis"),
                "decision": FlowNode("decision", "condition", {"x": 500, "y": 300}, {"condition": "analysis.success"}, "Decision"),
                "complex": FlowNode("complex", "task", {"x": 650, "y": 200}, {"task_id": "complex_task"}, "Complex Task"),
                "simple": FlowNode("simple", "task", {"x": 650, "y": 400}, {"task_id": "simple_task"}, "Simple Task"),
                "barrier": FlowNode("barrier", "barrier", {"x": 800, "y": 300}, {"barrier_type": "CHECKPOINT"}, "Sync"),
                "end": FlowNode("end", "end", {"x": 950, "y": 300}, {}, "End")
            },
            connections={
                "conn1": FlowConnection("conn1", "start", "out", "leader", "in"),
                "conn2": FlowConnection("conn2", "leader", "out", "analysis", "in"),
                "conn3": FlowConnection("conn3", "analysis", "success", "decision", "in"),
                "conn4": FlowConnection("conn4", "decision", "true", "complex", "in"),
                "conn5": FlowConnection("conn5", "decision", "false", "simple", "in"),
                "conn6": FlowConnection("conn6", "complex", "success", "barrier", "in1"),
                "conn7": FlowConnection("conn7", "simple", "success", "barrier", "in2"),
                "conn8": FlowConnection("conn8", "barrier", "out", "end", "in")
            },
            created_at=datetime.now(),
            modified_at=datetime.now(),
            created_by="system",
            is_valid=True
        )
        
        self.templates = {
            "sequential": sequential_flow,
            "parallel": parallel_flow,
            "hierarchical": hierarchical_flow
        }
    
    def create_flow(self, name: str, description: str, pattern: CollaborationPattern, created_by: str) -> str:
        """Create a new collaboration flow"""
        flow_id = str(uuid.uuid4())
        
        flow = CollaborationFlow(
            flow_id=flow_id,
            name=name,
            description=description,
            pattern=pattern,
            nodes={
                "start": FlowNode("start", "start", {"x": 50, "y": 200}, {}, "Start"),
                "end": FlowNode("end", "end", {"x": 400, "y": 200}, {}, "End")
            },
            connections={},
            created_at=datetime.now(),
            modified_at=datetime.now(),
            created_by=created_by
        )
        
        self.flows[flow_id] = flow
        return flow_id
    
    def create_from_template(self, template_id: str, name: str, created_by: str) -> str:
        """Create a flow from template"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        flow_id = str(uuid.uuid4())
        
        # Deep copy template
        flow = CollaborationFlow(
            flow_id=flow_id,
            name=name,
            description=f"Based on {template.name}",
            pattern=template.pattern,
            nodes=template.nodes.copy(),
            connections=template.connections.copy(),
            created_at=datetime.now(),
            modified_at=datetime.now(),
            created_by=created_by
        )
        
        self.flows[flow_id] = flow
        return flow_id
    
    def add_node(self, flow_id: str, node_type: str, position: Dict[str, float], config: Dict[str, Any], title: str) -> str:
        """Add a node to the flow"""
        if flow_id not in self.flows:
            raise ValueError(f"Flow {flow_id} not found")
        
        if node_type not in self.node_types:
            raise ValueError(f"Unknown node type: {node_type}")
        
        node_id = str(uuid.uuid4())
        node = FlowNode(
            node_id=node_id,
            node_type=node_type,
            position=position,
            config=config,
            title=title,
            inputs=self.node_types[node_type]["inputs"].copy(),
            outputs=self.node_types[node_type]["outputs"].copy()
        )
        
        self.flows[flow_id].nodes[node_id] = node
        self.flows[flow_id].modified_at = datetime.now()
        
        # Trigger validation
        self._validate_flow(flow_id)
        
        return node_id
    
    def update_node(self, flow_id: str, node_id: str, updates: Dict[str, Any]) -> bool:
        """Update a node in the flow"""
        if flow_id not in self.flows:
            return False
        
        if node_id not in self.flows[flow_id].nodes:
            return False
        
        node = self.flows[flow_id].nodes[node_id]
        
        # Update allowed fields
        if "position" in updates:
            node.position = updates["position"]
        if "config" in updates:
            node.config.update(updates["config"])
        if "title" in updates:
            node.title = updates["title"]
        if "description" in updates:
            node.description = updates["description"]
        
        self.flows[flow_id].modified_at = datetime.now()
        self._validate_flow(flow_id)
        
        return True
    
    def remove_node(self, flow_id: str, node_id: str) -> bool:
        """Remove a node from the flow"""
        if flow_id not in self.flows:
            return False
        
        if node_id not in self.flows[flow_id].nodes:
            return False
        
        # Don't allow removing start/end nodes
        node = self.flows[flow_id].nodes[node_id]
        if node.node_type in ["start", "end"]:
            return False
        
        # Remove node
        del self.flows[flow_id].nodes[node_id]
        
        # Remove connections involving this node
        connections_to_remove = []
        for conn_id, connection in self.flows[flow_id].connections.items():
            if connection.source_node == node_id or connection.target_node == node_id:
                connections_to_remove.append(conn_id)
        
        for conn_id in connections_to_remove:
            del self.flows[flow_id].connections[conn_id]
        
        self.flows[flow_id].modified_at = datetime.now()
        self._validate_flow(flow_id)
        
        return True
    
    def add_connection(self, flow_id: str, source_node: str, source_port: str, target_node: str, target_port: str) -> str:
        """Add a connection between nodes"""
        if flow_id not in self.flows:
            raise ValueError(f"Flow {flow_id} not found")
        
        flow = self.flows[flow_id]
        
        # Validate nodes exist
        if source_node not in flow.nodes or target_node not in flow.nodes:
            raise ValueError("Source or target node not found")
        
        # Validate ports exist
        source = flow.nodes[source_node]
        target = flow.nodes[target_node]
        
        if source_port not in source.outputs:
            raise ValueError(f"Source port {source_port} not found in node {source_node}")
        
        if target_port not in target.inputs:
            raise ValueError(f"Target port {target_port} not found in node {target_node}")
        
        connection_id = str(uuid.uuid4())
        connection = FlowConnection(
            connection_id=connection_id,
            source_node=source_node,
            source_port=source_port,
            target_node=target_node,
            target_port=target_port
        )
        
        flow.connections[connection_id] = connection
        flow.modified_at = datetime.now()
        
        self._validate_flow(flow_id)
        return connection_id
    
    def remove_connection(self, flow_id: str, connection_id: str) -> bool:
        """Remove a connection from the flow"""
        if flow_id not in self.flows:
            return False
        
        if connection_id not in self.flows[flow_id].connections:
            return False
        
        del self.flows[flow_id].connections[connection_id]
        self.flows[flow_id].modified_at = datetime.now()
        
        self._validate_flow(flow_id)
        return True
    
    def _validate_flow(self, flow_id: str) -> bool:
        """Validate a collaboration flow"""
        if flow_id not in self.flows:
            return False
        
        flow = self.flows[flow_id]
        errors = []
        
        # Check for start and end nodes
        start_nodes = [n for n in flow.nodes.values() if n.node_type == "start"]
        end_nodes = [n for n in flow.nodes.values() if n.node_type == "end"]
        
        if len(start_nodes) != 1:
            errors.append("Flow must have exactly one start node")
        
        if len(end_nodes) < 1:
            errors.append("Flow must have at least one end node")
        
        # Check for disconnected nodes (except start/end)
        connected_nodes = set()
        for connection in flow.connections.values():
            connected_nodes.add(connection.source_node)
            connected_nodes.add(connection.target_node)
        
        for node in flow.nodes.values():
            if node.node_type not in ["start", "end"] and node.node_id not in connected_nodes:
                errors.append(f"Node '{node.title}' is not connected")
        
        # Check for cycles (simplified check)
        if self._has_cycles(flow):
            errors.append("Flow contains cycles")
        
        # Validate node configurations
        for node in flow.nodes.values():
            node_errors = self._validate_node_config(node)
            errors.extend(node_errors)
        
        flow.validation_errors = errors
        flow.is_valid = len(errors) == 0
        
        return flow.is_valid
    
    def _has_cycles(self, flow: CollaborationFlow) -> bool:
        """Check for cycles in the flow graph"""
        # Build adjacency list
        graph = {}
        for node_id in flow.nodes:
            graph[node_id] = []
        
        for connection in flow.connections.values():
            graph[connection.source_node].append(connection.target_node)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle_util(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph[node]:
                if neighbor not in visited:
                    if has_cycle_util(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if has_cycle_util(node):
                    return True
        
        return False
    
    def _validate_node_config(self, node: FlowNode) -> List[str]:
        """Validate node configuration"""
        errors = []
        
        if node.node_type not in self.node_types:
            errors.append(f"Unknown node type: {node.node_type}")
            return errors
        
        node_type_def = self.node_types[node.node_type]
        
        if "config_schema" in node_type_def:
            schema = node_type_def["config_schema"]
            
            for field, field_def in schema.items():
                if field_def.get("required", False) and field not in node.config:
                    errors.append(f"Node '{node.title}': Required field '{field}' is missing")
                
                if field in node.config:
                    value = node.config[field]
                    field_type = field_def["type"]
                    
                    if field_type == "number" and not isinstance(value, (int, float)):
                        errors.append(f"Node '{node.title}': Field '{field}' must be a number")
                    elif field_type == "string" and not isinstance(value, str):
                        errors.append(f"Node '{node.title}': Field '{field}' must be a string")
                    elif field_type == "select" and value not in field_def.get("options", []):
                        errors.append(f"Node '{node.title}': Field '{field}' has invalid value")
        
        return errors
    
    def generate_collaboration_plan(self, flow_id: str) -> Optional[CollaborationPlan]:
        """Generate a collaboration plan from the flow"""
        if flow_id not in self.flows:
            return None
        
        flow = self.flows[flow_id]
        
        if not flow.is_valid:
            return None
        
        # Generate plan based on flow structure
        plan = CollaborationPlan(
            collaboration_id=str(uuid.uuid4()),
            pattern=flow.pattern,
            task_assignments={},
            coordination_requirements=[],
            estimated_duration=3600,  # Default 1 hour
            success_criteria=[],
            fallback_strategy="ABORT"
        )
        
        # Extract tasks and assignments from nodes
        for node in flow.nodes.values():
            if node.node_type == "task":
                task_id = node.config.get("task_id", node.node_id)
                plan.task_assignments[task_id] = []
            
            elif node.node_type == "bot":
                bot_id = node.config.get("bot_id")
                if bot_id:
                    # Find connected tasks
                    for connection in flow.connections.values():
                        if connection.source_node == node.node_id:
                            target_node = flow.nodes[connection.target_node]
                            if target_node.node_type == "task":
                                task_id = target_node.config.get("task_id", target_node.node_id)
                                if task_id not in plan.task_assignments:
                                    plan.task_assignments[task_id] = []
                                plan.task_assignments[task_id].append(bot_id)
            
            elif node.node_type == "barrier":
                barrier_config = {
                    "type": node.config.get("barrier_type", "CHECKPOINT"),
                    "coordination_mode": node.config.get("coordination_mode", "STRICT"),
                    "timeout": node.config.get("timeout", 300)
                }
                plan.coordination_requirements.append(barrier_config)
        
        return plan
    
    def get_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get flow data for frontend"""
        if flow_id not in self.flows:
            return None
        
        flow = self.flows[flow_id]
        
        return {
            "flow_id": flow.flow_id,
            "name": flow.name,
            "description": flow.description,
            "pattern": flow.pattern.value,
            "nodes": [
                {
                    "id": node.node_id,
                    "type": node.node_type,
                    "position": node.position,
                    "config": node.config,
                    "title": node.title,
                    "description": node.description,
                    "inputs": node.inputs,
                    "outputs": node.outputs
                }
                for node in flow.nodes.values()
            ],
            "connections": [
                {
                    "id": conn.connection_id,
                    "source": conn.source_node,
                    "sourcePort": conn.source_port,
                    "target": conn.target_node,
                    "targetPort": conn.target_port,
                    "condition": conn.condition,
                    "metadata": conn.metadata
                }
                for conn in flow.connections.values()
            ],
            "created_at": flow.created_at.isoformat(),
            "modified_at": flow.modified_at.isoformat(),
            "created_by": flow.created_by,
            "is_valid": flow.is_valid,
            "validation_errors": flow.validation_errors
        }
    
    def get_node_types(self) -> Dict[str, Any]:
        """Get available node types for frontend"""
        return self.node_types
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available templates"""
        return [
            {
                "template_id": template_id,
                "name": template.name,
                "description": template.description,
                "pattern": template.pattern.value,
                "node_count": len(template.nodes),
                "preview": self._generate_template_preview(template)
            }
            for template_id, template in self.templates.items()
        ]
    
    def _generate_template_preview(self, template: CollaborationFlow) -> str:
        """Generate a simple text preview of the template"""
        node_types = [node.node_type for node in template.nodes.values()]
        type_counts = {}
        for node_type in node_types:
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        
        preview_parts = []
        for node_type, count in type_counts.items():
            if node_type not in ["start", "end"]:
                plural = "s" if count > 1 else ""
                preview_parts.append(f"{count} {node_type}{plural}")
        
        return ", ".join(preview_parts)

    def export_flow(self, flow_id: str) -> Optional[str]:
        """Export flow as JSON"""
        flow_data = self.get_flow(flow_id)
        if flow_data:
            return json.dumps(flow_data, indent=2)
        return None
    
    def import_flow(self, flow_data: str, created_by: str) -> Optional[str]:
        """Import flow from JSON"""
        try:
            data = json.loads(flow_data)
            
            # Create new flow
            flow_id = str(uuid.uuid4())
            
            # Rebuild nodes
            nodes = {}
            for node_data in data.get("nodes", []):
                node = FlowNode(
                    node_id=node_data["id"],
                    node_type=node_data["type"],
                    position=node_data["position"],
                    config=node_data["config"],
                    title=node_data["title"],
                    description=node_data.get("description", ""),
                    inputs=node_data.get("inputs", []),
                    outputs=node_data.get("outputs", [])
                )
                nodes[node.node_id] = node
            
            # Rebuild connections
            connections = {}
            for conn_data in data.get("connections", []):
                connection = FlowConnection(
                    connection_id=conn_data["id"],
                    source_node=conn_data["source"],
                    source_port=conn_data["sourcePort"],
                    target_node=conn_data["target"],
                    target_port=conn_data["targetPort"],
                    condition=conn_data.get("condition"),
                    metadata=conn_data.get("metadata", {})
                )
                connections[connection.connection_id] = connection
            
            # Create flow
            flow = CollaborationFlow(
                flow_id=flow_id,
                name=data.get("name", "Imported Flow"),
                description=data.get("description", ""),
                pattern=CollaborationPattern(data.get("pattern", "PARALLEL")),
                nodes=nodes,
                connections=connections,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                created_by=created_by
            )
            
            self.flows[flow_id] = flow
            self._validate_flow(flow_id)
            
            return flow_id
            
        except Exception as e:
            logger.error(f"Error importing flow: {e}")
            return None


def create_designer_web_interface(designer: CollaborationDesigner) -> FastAPI:
    """Create FastAPI web interface for the designer"""
    app = FastAPI(title="Collaboration Designer", version="1.0.0")
    
    @app.get("/api/designer/node-types")
    async def get_node_types():
        """Get available node types"""
        return designer.get_node_types()
    
    @app.get("/api/designer/templates")
    async def get_templates():
        """Get flow templates"""
        return designer.get_templates()
    
    @app.post("/api/designer/flows")
    async def create_flow(flow_data: dict):
        """Create a new flow"""
        try:
            if "template_id" in flow_data:
                flow_id = designer.create_from_template(
                    flow_data["template_id"],
                    flow_data["name"],
                    flow_data.get("created_by", "user")
                )
            else:
                flow_id = designer.create_flow(
                    flow_data["name"],
                    flow_data.get("description", ""),
                    CollaborationPattern(flow_data.get("pattern", "PARALLEL")),
                    flow_data.get("created_by", "user")
                )
            
            return {"flow_id": flow_id, "success": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/designer/flows/{flow_id}")
    async def get_flow(flow_id: str):
        """Get flow data"""
        flow_data = designer.get_flow(flow_id)
        if not flow_data:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow_data
    
    @app.post("/api/designer/flows/{flow_id}/nodes")
    async def add_node(flow_id: str, node_data: dict):
        """Add a node to the flow"""
        try:
            node_id = designer.add_node(
                flow_id,
                node_data["type"],
                node_data["position"],
                node_data.get("config", {}),
                node_data["title"]
            )
            return {"node_id": node_id, "success": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.put("/api/designer/flows/{flow_id}/nodes/{node_id}")
    async def update_node(flow_id: str, node_id: str, updates: dict):
        """Update a node"""
        success = designer.update_node(flow_id, node_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"success": True}
    
    @app.delete("/api/designer/flows/{flow_id}/nodes/{node_id}")
    async def remove_node(flow_id: str, node_id: str):
        """Remove a node"""
        success = designer.remove_node(flow_id, node_id)
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"success": True}
    
    @app.post("/api/designer/flows/{flow_id}/connections")
    async def add_connection(flow_id: str, connection_data: dict):
        """Add a connection between nodes"""
        try:
            connection_id = designer.add_connection(
                flow_id,
                connection_data["source"],
                connection_data["sourcePort"],
                connection_data["target"],
                connection_data["targetPort"]
            )
            return {"connection_id": connection_id, "success": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.delete("/api/designer/flows/{flow_id}/connections/{connection_id}")
    async def remove_connection(flow_id: str, connection_id: str):
        """Remove a connection"""
        success = designer.remove_connection(flow_id, connection_id)
        if not success:
            raise HTTPException(status_code=404, detail="Connection not found")
        return {"success": True}
    
    @app.post("/api/designer/flows/{flow_id}/generate-plan")
    async def generate_plan(flow_id: str):
        """Generate collaboration plan from flow"""
        plan = designer.generate_collaboration_plan(flow_id)
        if not plan:
            raise HTTPException(status_code=400, detail="Cannot generate plan from invalid flow")
        return asdict(plan)
    
    @app.get("/api/designer/flows/{flow_id}/export")
    async def export_flow(flow_id: str):
        """Export flow as JSON"""
        flow_json = designer.export_flow(flow_id)
        if not flow_json:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        from fastapi.responses import Response
        return Response(
            content=flow_json,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=flow_{flow_id}.json"}
        )
    
    @app.post("/api/designer/flows/import")
    async def import_flow(import_data: dict):
        """Import flow from JSON"""
        try:
            flow_id = designer.import_flow(
                import_data["flow_data"],
                import_data.get("created_by", "user")
            )
            if not flow_id:
                raise HTTPException(status_code=400, detail="Failed to import flow")
            return {"flow_id": flow_id, "success": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    return app


# Create designer HTML template
def create_designer_template() -> str:
    """Create the HTML template for the collaboration designer"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Collaboration Designer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <script src="https://unpkg.com/reactflow@11/dist/index.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .flow-canvas {
            width: 100%;
            height: 600px;
            border: 2px dashed #d1d5db;
            background: linear-gradient(90deg, #f9fafb 1px, transparent 1px),
                        linear-gradient(180deg, #f9fafb 1px, transparent 1px);
            background-size: 20px 20px;
        }
        
        .node-palette {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .node-item {
            cursor: grab;
            transition: transform 0.2s;
        }
        
        .node-item:hover {
            transform: scale(1.05);
        }
        
        .node-item:active {
            cursor: grabbing;
        }
    </style>
</head>
<body class="bg-gray-100" x-data="collaborationDesigner()">
    <div class="container mx-auto p-6">
        <!-- Header -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <div class="flex justify-between items-center">
                <div>
                    <h1 class="text-3xl font-bold text-gray-900">
                        <i class="fas fa-project-diagram mr-3 text-blue-600"></i>
                        Collaboration Designer
                    </h1>
                    <p class="text-gray-600 mt-2">Design multi-bot collaboration workflows visually</p>
                </div>
                <div class="flex space-x-4">
                    <button @click="showTemplates = true" class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                        <i class="fas fa-plus mr-2"></i>New Flow
                    </button>
                    <button @click="exportFlow()" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                        <i class="fas fa-download mr-2"></i>Export
                    </button>
                    <button @click="showImport = true" class="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600">
                        <i class="fas fa-upload mr-2"></i>Import
                    </button>
                </div>
            </div>
        </div>

        <!-- Main Designer Interface -->
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <!-- Node Palette -->
            <div class="bg-white rounded-lg shadow-md p-4">
                <h3 class="text-lg font-semibold mb-4">
                    <i class="fas fa-tools mr-2 text-gray-600"></i>
                    Node Palette
                </h3>
                
                <div class="node-palette space-y-2">
                    <template x-for="(nodeType, key) in nodeTypes" :key="key">
                        <div class="node-item bg-gray-50 p-3 rounded border-2 border-gray-200 hover:border-blue-400"
                             :style="`border-left: 4px solid ${nodeType.color}`"
                             draggable="true"
                             @dragstart="startNodeDrag($event, key, nodeType)">
                            <div class="flex items-center">
                                <i :class="`fas fa-${nodeType.icon} mr-2`" :style="`color: ${nodeType.color}`"></i>
                                <div>
                                    <div class="font-medium text-sm" x-text="nodeType.title"></div>
                                    <div class="text-xs text-gray-500" x-text="nodeType.description"></div>
                                </div>
                            </div>
                        </div>
                    </template>
                </div>
            </div>

            <!-- Flow Canvas -->
            <div class="lg:col-span-3 bg-white rounded-lg shadow-md p-4">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold">
                        <i class="fas fa-sitemap mr-2 text-gray-600"></i>
                        Flow Canvas
                        <span x-show="currentFlow" class="text-sm font-normal text-gray-500" x-text="`- ${currentFlow?.name}`"></span>
                    </h3>
                    
                    <div class="flex space-x-2">
                        <button @click="validateFlow()" class="bg-orange-500 text-white px-3 py-1 rounded text-sm hover:bg-orange-600">
                            <i class="fas fa-check-circle mr-1"></i>Validate
                        </button>
                        <button @click="generatePlan()" class="bg-green-500 text-white px-3 py-1 rounded text-sm hover:bg-green-600"
                                :disabled="!currentFlow?.is_valid">
                            <i class="fas fa-play mr-1"></i>Generate Plan
                        </button>
                    </div>
                </div>

                <!-- Canvas Area -->
                <div class="flow-canvas relative"
                     @drop="handleCanvasDrop($event)"
                     @dragover="$event.preventDefault()"
                     id="flow-canvas">
                    
                    <!-- Flow Nodes -->
                    <template x-for="node in currentFlow?.nodes || []" :key="node.id">
                        <div class="absolute bg-white border-2 rounded-lg shadow-md p-3 cursor-move min-w-32"
                             :style="`left: ${node.position.x}px; top: ${node.position.y}px; border-color: ${getNodeColor(node.type)}`"
                             @mousedown="startNodeMove($event, node)"
                             @dblclick="editNode(node)">
                            
                            <div class="flex items-center justify-between mb-2">
                                <div class="flex items-center">
                                    <i :class="`fas fa-${getNodeIcon(node.type)} mr-2`" 
                                       :style="`color: ${getNodeColor(node.type)}`"></i>
                                    <span class="font-medium text-sm" x-text="node.title"></span>
                                </div>
                                <button @click="removeNode(node.id)" class="text-red-500 hover:text-red-700">
                                    <i class="fas fa-times text-xs"></i>
                                </button>
                            </div>
                            
                            <!-- Input Ports -->
                            <div class="flex justify-start mb-1" x-show="node.inputs?.length">
                                <template x-for="input in node.inputs" :key="input">
                                    <div class="w-3 h-3 bg-blue-500 rounded-full border-2 border-white -ml-2 mt-1 port"
                                         :data-node-id="node.id"
                                         :data-port="input"
                                         :data-port-type="'input'">
                                    </div>
                                </template>
                            </div>
                            
                            <!-- Output Ports -->
                            <div class="flex justify-end" x-show="node.outputs?.length">
                                <template x-for="output in node.outputs" :key="output">
                                    <div class="w-3 h-3 bg-green-500 rounded-full border-2 border-white -mr-2 mb-1 port"
                                         :data-node-id="node.id"
                                         :data-port="output"
                                         :data-port-type="'output'">
                                    </div>
                                </template>
                            </div>
                        </div>
                    </template>

                    <!-- Connection Lines (SVG overlay would be better, but this is simplified) -->
                    <svg class="absolute inset-0 pointer-events-none" style="z-index: -1;">
                        <template x-for="connection in currentFlow?.connections || []" :key="connection.id">
                            <line :x1="getConnectionStart(connection).x" 
                                  :y1="getConnectionStart(connection).y"
                                  :x2="getConnectionEnd(connection).x" 
                                  :y2="getConnectionEnd(connection).y"
                                  stroke="#6b7280" 
                                  stroke-width="2" 
                                  marker-end="url(#arrowhead)"/>
                        </template>
                        
                        <!-- Arrow marker definition -->
                        <defs>
                            <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                                    refX="9" refY="3.5" orient="auto">
                                <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280"/>
                            </marker>
                        </defs>
                    </svg>
                </div>

                <!-- Flow Validation Status -->
                <div x-show="currentFlow" class="mt-4 p-3 rounded" 
                     :class="currentFlow?.is_valid ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
                    <div class="flex items-center">
                        <i :class="currentFlow?.is_valid ? 'fas fa-check-circle' : 'fas fa-exclamation-triangle'" class="mr-2"></i>
                        <span x-text="currentFlow?.is_valid ? 'Flow is valid' : 'Flow has validation errors'"></span>
                    </div>
                    <div x-show="!currentFlow?.is_valid && currentFlow?.validation_errors?.length" class="mt-2">
                        <ul class="list-disc list-inside text-sm">
                            <template x-for="error in currentFlow?.validation_errors" :key="error">
                                <li x-text="error"></li>
                            </template>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Template Selection Modal -->
    <div x-show="showTemplates" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 class="text-lg font-bold text-gray-900 mb-4">Choose Template</h3>
            
            <div class="space-y-3 mb-4">
                <template x-for="template in templates" :key="template.template_id">
                    <div class="border rounded p-3 hover:bg-gray-50 cursor-pointer"
                         @click="createFromTemplate(template.template_id)">
                        <h4 class="font-medium" x-text="template.name"></h4>
                        <p class="text-sm text-gray-600" x-text="template.description"></p>
                        <p class="text-xs text-gray-500 mt-1" x-text="template.preview"></p>
                    </div>
                </template>
            </div>
            
            <div class="flex justify-end space-x-2">
                <button @click="showTemplates = false" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                    Cancel
                </button>
                <button @click="createBlankFlow()" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                    Blank Flow
                </button>
            </div>
        </div>
    </div>

    <!-- Import Modal -->
    <div x-show="showImport" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 class="text-lg font-bold text-gray-900 mb-4">Import Flow</h3>
            
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">Flow JSON:</label>
                <textarea x-model="importData" rows="10" 
                          class="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                          placeholder="Paste flow JSON here..."></textarea>
            </div>
            
            <div class="flex justify-end space-x-2">
                <button @click="showImport = false" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                    Cancel
                </button>
                <button @click="importFlow()" class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600">
                    Import
                </button>
            </div>
        </div>
    </div>

    <script>
        function collaborationDesigner() {
            return {
                currentFlow: null,
                nodeTypes: {},
                templates: [],
                showTemplates: false,
                showImport: false,
                importData: '',
                draggedNodeType: null,
                isNodeMoving: false,
                nodeOffset: { x: 0, y: 0 },

                async init() {
                    await this.loadNodeTypes();
                    await this.loadTemplates();
                },

                async loadNodeTypes() {
                    try {
                        const response = await fetch('/api/designer/node-types');
                        this.nodeTypes = await response.json();
                    } catch (error) {
                        console.error('Error loading node types:', error);
                    }
                },

                async loadTemplates() {
                    try {
                        const response = await fetch('/api/designer/templates');
                        this.templates = await response.json();
                    } catch (error) {
                        console.error('Error loading templates:', error);
                    }
                },

                async createFromTemplate(templateId) {
                    try {
                        const name = prompt('Flow name:');
                        if (!name) return;

                        const response = await fetch('/api/designer/flows', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                template_id: templateId,
                                name: name,
                                created_by: 'user'
                            })
                        });

                        const result = await response.json();
                        if (result.success) {
                            await this.loadFlow(result.flow_id);
                            this.showTemplates = false;
                        }
                    } catch (error) {
                        console.error('Error creating from template:', error);
                    }
                },

                async createBlankFlow() {
                    try {
                        const name = prompt('Flow name:');
                        if (!name) return;

                        const response = await fetch('/api/designer/flows', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                name: name,
                                description: '',
                                pattern: 'PARALLEL',
                                created_by: 'user'
                            })
                        });

                        const result = await response.json();
                        if (result.success) {
                            await this.loadFlow(result.flow_id);
                            this.showTemplates = false;
                        }
                    } catch (error) {
                        console.error('Error creating blank flow:', error);
                    }
                },

                async loadFlow(flowId) {
                    try {
                        const response = await fetch(`/api/designer/flows/${flowId}`);
                        this.currentFlow = await response.json();
                    } catch (error) {
                        console.error('Error loading flow:', error);
                    }
                },

                startNodeDrag(event, nodeType, nodeConfig) {
                    this.draggedNodeType = { type: nodeType, config: nodeConfig };
                    event.dataTransfer.effectAllowed = 'copy';
                },

                handleCanvasDrop(event) {
                    event.preventDefault();
                    
                    if (!this.draggedNodeType || !this.currentFlow) return;

                    const rect = event.currentTarget.getBoundingClientRect();
                    const position = {
                        x: event.clientX - rect.left - 50, // Center the node
                        y: event.clientY - rect.top - 25
                    };

                    this.addNode(this.draggedNodeType.type, position);
                    this.draggedNodeType = null;
                },

                async addNode(nodeType, position) {
                    if (!this.currentFlow) return;

                    try {
                        const title = prompt(`Enter title for ${nodeType}:`);
                        if (!title) return;

                        const response = await fetch(`/api/designer/flows/${this.currentFlow.flow_id}/nodes`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                type: nodeType,
                                position: position,
                                config: {},
                                title: title
                            })
                        });

                        const result = await response.json();
                        if (result.success) {
                            await this.loadFlow(this.currentFlow.flow_id);
                        }
                    } catch (error) {
                        console.error('Error adding node:', error);
                    }
                },

                async removeNode(nodeId) {
                    if (!this.currentFlow || !confirm('Remove this node?')) return;

                    try {
                        const response = await fetch(`/api/designer/flows/${this.currentFlow.flow_id}/nodes/${nodeId}`, {
                            method: 'DELETE'
                        });

                        const result = await response.json();
                        if (result.success) {
                            await this.loadFlow(this.currentFlow.flow_id);
                        }
                    } catch (error) {
                        console.error('Error removing node:', error);
                    }
                },

                getNodeColor(nodeType) {
                    return this.nodeTypes[nodeType]?.color || '#6b7280';
                },

                getNodeIcon(nodeType) {
                    return this.nodeTypes[nodeType]?.icon || 'circle';
                },

                getConnectionStart(connection) {
                    // Simplified - would need proper port positioning
                    const sourceNode = this.currentFlow?.nodes?.find(n => n.id === connection.source);
                    return sourceNode ? { x: sourceNode.position.x + 60, y: sourceNode.position.y + 20 } : { x: 0, y: 0 };
                },

                getConnectionEnd(connection) {
                    // Simplified - would need proper port positioning
                    const targetNode = this.currentFlow?.nodes?.find(n => n.id === connection.target);
                    return targetNode ? { x: targetNode.position.x, y: targetNode.position.y + 20 } : { x: 0, y: 0 };
                },

                async validateFlow() {
                    if (!this.currentFlow) return;

                    // Flow validation happens automatically on the backend
                    await this.loadFlow(this.currentFlow.flow_id);
                    
                    if (this.currentFlow.is_valid) {
                        alert('Flow is valid!');
                    } else {
                        alert('Flow has validation errors - see details below.');
                    }
                },

                async generatePlan() {
                    if (!this.currentFlow || !this.currentFlow.is_valid) {
                        alert('Flow must be valid to generate a plan');
                        return;
                    }

                    try {
                        const response = await fetch(`/api/designer/flows/${this.currentFlow.flow_id}/generate-plan`, {
                            method: 'POST'
                        });

                        const plan = await response.json();
                        console.log('Generated plan:', plan);
                        alert('Collaboration plan generated! Check console for details.');
                    } catch (error) {
                        console.error('Error generating plan:', error);
                        alert('Error generating plan');
                    }
                },

                async exportFlow() {
                    if (!this.currentFlow) {
                        alert('No flow to export');
                        return;
                    }

                    try {
                        const response = await fetch(`/api/designer/flows/${this.currentFlow.flow_id}/export`);
                        const blob = await response.blob();
                        
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `flow_${this.currentFlow.name.replace(/\\s+/g, '_')}.json`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                    } catch (error) {
                        console.error('Error exporting flow:', error);
                    }
                },

                async importFlow() {
                    if (!this.importData.trim()) {
                        alert('Please enter flow JSON data');
                        return;
                    }

                    try {
                        const response = await fetch('/api/designer/flows/import', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                flow_data: this.importData,
                                created_by: 'user'
                            })
                        });

                        const result = await response.json();
                        if (result.success) {
                            await this.loadFlow(result.flow_id);
                            this.showImport = false;
                            this.importData = '';
                            alert('Flow imported successfully!');
                        }
                    } catch (error) {
                        console.error('Error importing flow:', error);
                        alert('Error importing flow - check JSON format');
                    }
                }
            }
        }
    </script>
</body>
</html>
    '''