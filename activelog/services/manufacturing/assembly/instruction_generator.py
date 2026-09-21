"""
ActiveLog Manufacturing Suite - Assembly Instruction Generator

Automated generation of assembly instructions from CAD models with
interactive 3D guides, step-by-step visualization, and multi-language support.
"""

import asyncio
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import xml.etree.ElementTree as ET
import base64
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
import trimesh
import networkx as nx
from scipy.spatial.distance import euclidean
from scipy.spatial.transform import Rotation
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


class InstructionType(Enum):
    TEXT = "text"
    IMAGE = "image"
    ANIMATION = "animation"
    INTERACTIVE_3D = "interactive_3d"
    VIDEO = "video"


class AssemblyOperation(Enum):
    INSERT = "insert"
    ATTACH = "attach"
    SCREW = "screw"
    GLUE = "glue"
    WELD = "weld"
    PRESS_FIT = "press_fit"
    SNAP = "snap"
    ALIGN = "align"
    ROTATE = "rotate"
    SLIDE = "slide"


class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class CADComponent:
    component_id: str
    name: str
    file_path: str
    material: str
    color: str
    dimensions: Dict[str, float]
    mass: float
    center_of_mass: Tuple[float, float, float]
    bounding_box: Tuple[Tuple[float, float, float], Tuple[float, float, float]]
    attachment_points: List[Dict[str, Any]]
    mesh_data: Optional[Any] = None


@dataclass
class AssemblyStep:
    step_number: int
    operation: AssemblyOperation
    primary_component: str
    secondary_component: Optional[str]
    description: str
    tools_required: List[str]
    fasteners: List[str]
    warnings: List[str]
    estimated_time: int  # seconds
    difficulty: DifficultyLevel
    position: Tuple[float, float, float]
    orientation: Tuple[float, float, float, float]  # quaternion
    visualization_data: Dict[str, Any]


@dataclass
class AssemblyInstruction:
    instruction_id: str
    product_name: str
    version: str
    created_at: datetime
    language: str
    total_steps: int
    estimated_time: int  # total assembly time in minutes
    difficulty: DifficultyLevel
    tools_list: List[str]
    materials_list: List[str]
    safety_warnings: List[str]
    steps: List[AssemblyStep]
    interactive_model_path: Optional[str] = None


@dataclass
class VisualizationAsset:
    asset_id: str
    asset_type: InstructionType
    file_path: str
    description: str
    step_number: int
    metadata: Dict[str, Any]


class CADProcessor:
    """Processor for CAD model analysis and component extraction"""
    
    def __init__(self):
        self.supported_formats = ['.step', '.stp', '.iges', '.igs', '.stl', '.obj']
    
    async def load_cad_assembly(self, file_path: str) -> List[CADComponent]:
        """Load and process CAD assembly file"""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        components = []
        
        if file_path.suffix.lower() in ['.step', '.stp']:
            components = await self._process_step_file(file_path)
        elif file_path.suffix.lower() in ['.stl', '.obj']:
            components = await self._process_mesh_file(file_path)
        else:
            # Placeholder for other formats
            components = await self._process_generic_file(file_path)
        
        return components
    
    async def _process_step_file(self, file_path: Path) -> List[CADComponent]:
        """Process STEP/STP files using opencascade or similar"""
        # Placeholder implementation - in production use python-opencascade
        components = []
        
        # Simulate reading STEP file structure
        component_names = ["base_plate", "mounting_bracket", "cover_panel", "fasteners"]
        
        for i, name in enumerate(component_names):
            # Generate simulated component data
            dimensions = {
                "length": np.random.uniform(50, 200),
                "width": np.random.uniform(30, 150),
                "height": np.random.uniform(10, 50)
            }
            
            component = CADComponent(
                component_id=f"comp_{i+1:03d}",
                name=name,
                file_path=str(file_path),
                material="aluminum" if "bracket" in name else "steel",
                color=f"#{np.random.randint(0, 16777215):06x}",
                dimensions=dimensions,
                mass=np.random.uniform(0.1, 5.0),
                center_of_mass=(
                    dimensions["length"] / 2,
                    dimensions["width"] / 2,
                    dimensions["height"] / 2
                ),
                bounding_box=(
                    (0, 0, 0),
                    (dimensions["length"], dimensions["width"], dimensions["height"])
                ),
                attachment_points=self._generate_attachment_points(dimensions)
            )
            
            components.append(component)
        
        return components
    
    async def _process_mesh_file(self, file_path: Path) -> List[CADComponent]:
        """Process mesh files (STL, OBJ) using trimesh"""
        try:
            mesh = trimesh.load(str(file_path))
            
            if isinstance(mesh, trimesh.Scene):
                # Multi-part assembly
                components = []
                for name, geometry in mesh.geometry.items():
                    component = self._mesh_to_component(name, geometry, str(file_path))
                    components.append(component)
                return components
            else:
                # Single component
                component = self._mesh_to_component("main_component", mesh, str(file_path))
                return [component]
        except Exception as e:
            # Fallback to simulated data
            return await self._process_generic_file(file_path)
    
    def _mesh_to_component(self, name: str, mesh: trimesh.Trimesh, file_path: str) -> CADComponent:
        """Convert trimesh geometry to CADComponent"""
        bounds = mesh.bounds
        dimensions = {
            "length": bounds[1][0] - bounds[0][0],
            "width": bounds[1][1] - bounds[0][1],
            "height": bounds[1][2] - bounds[0][2]
        }
        
        return CADComponent(
            component_id=f"mesh_{hash(name) % 1000:03d}",
            name=name,
            file_path=file_path,
            material="unknown",
            color="#808080",
            dimensions=dimensions,
            mass=mesh.mass if hasattr(mesh, 'mass') else 1.0,
            center_of_mass=tuple(mesh.center_mass) if hasattr(mesh, 'center_mass') else (0, 0, 0),
            bounding_box=(tuple(bounds[0]), tuple(bounds[1])),
            attachment_points=self._generate_attachment_points(dimensions),
            mesh_data=mesh
        )
    
    async def _process_generic_file(self, file_path: Path) -> List[CADComponent]:
        """Generic fallback processor"""
        # Return simulated components for demonstration
        return [
            CADComponent(
                component_id="comp_001",
                name="main_assembly",
                file_path=str(file_path),
                material="steel",
                color="#C0C0C0",
                dimensions={"length": 100, "width": 80, "height": 20},
                mass=2.5,
                center_of_mass=(50, 40, 10),
                bounding_box=((0, 0, 0), (100, 80, 20)),
                attachment_points=[
                    {"type": "screw_hole", "position": (10, 10, 0), "diameter": 5},
                    {"type": "screw_hole", "position": (90, 10, 0), "diameter": 5},
                    {"type": "screw_hole", "position": (10, 70, 0), "diameter": 5},
                    {"type": "screw_hole", "position": (90, 70, 0), "diameter": 5}
                ]
            )
        ]
    
    def _generate_attachment_points(self, dimensions: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate probable attachment points based on geometry"""
        points = []
        
        # Corner mounting points
        for x in [0, dimensions["length"]]:
            for y in [0, dimensions["width"]]:
                points.append({
                    "type": "mounting_point",
                    "position": (x, y, 0),
                    "diameter": 5.0,
                    "thread": "M5"
                })
        
        # Center mounting point
        points.append({
            "type": "center_mount",
            "position": (dimensions["length"]/2, dimensions["width"]/2, 0),
            "diameter": 8.0,
            "thread": "M8"
        })
        
        return points


class AssemblySequenceOptimizer:
    """Optimizer for determining optimal assembly sequence"""
    
    def __init__(self):
        self.assembly_graph = nx.DiGraph()
        self.interference_matrix = {}
    
    async def optimize_sequence(self, components: List[CADComponent]) -> List[Tuple[str, str, AssemblyOperation]]:
        """Determine optimal assembly sequence using graph algorithms"""
        # Build component dependency graph
        self._build_dependency_graph(components)
        
        # Check for geometric interference
        self._analyze_geometric_constraints(components)
        
        # Find optimal sequence using topological sorting
        sequence = self._find_optimal_sequence()
        
        return sequence
    
    def _build_dependency_graph(self, components: List[CADComponent]):
        """Build graph of component dependencies"""
        self.assembly_graph.clear()
        
        # Add all components as nodes
        for component in components:
            self.assembly_graph.add_node(component.component_id, component=component)
        
        # Determine dependencies based on spatial relationships
        for i, comp1 in enumerate(components):
            for j, comp2 in enumerate(components):
                if i != j:
                    dependency = self._analyze_dependency(comp1, comp2)
                    if dependency:
                        self.assembly_graph.add_edge(
                            comp1.component_id, 
                            comp2.component_id, 
                            operation=dependency
                        )
    
    def _analyze_dependency(self, comp1: CADComponent, comp2: CADComponent) -> Optional[AssemblyOperation]:
        """Analyze if comp1 depends on comp2 for assembly"""
        # Simplified dependency analysis based on names and positions
        if "base" in comp1.name.lower() and "bracket" in comp2.name.lower():
            return AssemblyOperation.ATTACH
        elif "cover" in comp1.name.lower() and any(x in comp2.name.lower() for x in ["base", "bracket"]):
            return AssemblyOperation.SCREW
        elif "fastener" in comp1.name.lower():
            return AssemblyOperation.SCREW
        
        # Geometric dependency analysis
        bbox1 = comp1.bounding_box
        bbox2 = comp2.bounding_box
        
        # Check if comp1 is above comp2 (stacking dependency)
        if bbox1[0][2] > bbox2[1][2]:  # comp1 bottom > comp2 top
            return AssemblyOperation.INSERT
        
        return None
    
    def _analyze_geometric_constraints(self, components: List[CADComponent]):
        """Analyze geometric interference between components"""
        for i, comp1 in enumerate(components):
            for j, comp2 in enumerate(components):
                if i < j:
                    interference = self._check_interference(comp1, comp2)
                    self.interference_matrix[(comp1.component_id, comp2.component_id)] = interference
    
    def _check_interference(self, comp1: CADComponent, comp2: CADComponent) -> bool:
        """Check if two components geometrically interfere"""
        bbox1 = comp1.bounding_box
        bbox2 = comp2.bounding_box
        
        # Simple bounding box overlap check
        overlap_x = not (bbox1[1][0] < bbox2[0][0] or bbox2[1][0] < bbox1[0][0])
        overlap_y = not (bbox1[1][1] < bbox2[0][1] or bbox2[1][1] < bbox1[0][1])
        overlap_z = not (bbox1[1][2] < bbox2[0][2] or bbox2[1][2] < bbox1[0][2])
        
        return overlap_x and overlap_y and overlap_z
    
    def _find_optimal_sequence(self) -> List[Tuple[str, str, AssemblyOperation]]:
        """Find optimal assembly sequence using topological sort"""
        try:
            # Get topological ordering
            topo_order = list(nx.topological_sort(self.assembly_graph))
            
            sequence = []
            for i in range(len(topo_order) - 1):
                current = topo_order[i]
                next_comp = topo_order[i + 1]
                
                # Get operation from edge data
                if self.assembly_graph.has_edge(current, next_comp):
                    operation = self.assembly_graph[current][next_comp]['operation']
                else:
                    operation = AssemblyOperation.ATTACH  # Default operation
                
                sequence.append((current, next_comp, operation))
            
            return sequence
            
        except nx.NetworkXError:
            # Handle cycles in dependency graph
            return self._handle_circular_dependencies()
    
    def _handle_circular_dependencies(self) -> List[Tuple[str, str, AssemblyOperation]]:
        """Handle circular dependencies by breaking cycles"""
        # Find strongly connected components
        sccs = list(nx.strongly_connected_components(self.assembly_graph))
        
        # Break cycles by removing minimum weight edges
        for scc in sccs:
            if len(scc) > 1:
                # Remove one edge to break the cycle
                subgraph = self.assembly_graph.subgraph(scc)
                edges = list(subgraph.edges())
                if edges:
                    self.assembly_graph.remove_edge(*edges[0])
        
        # Retry topological sort
        return self._find_optimal_sequence()


class InstructionContentGenerator:
    """Generator for instruction content in multiple formats"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.templates = {}
        self.language_support = ["en", "es", "fr", "de", "zh", "ja"]
        self._load_templates()
    
    def _load_templates(self):
        """Load instruction templates for different languages"""
        self.templates = {
            "en": {
                "step_prefix": "Step {step_number}:",
                "attach": "Attach {component1} to {component2}",
                "screw": "Secure {component1} to {component2} using {fastener}",
                "insert": "Insert {component1} into {component2}",
                "align": "Align {component1} with {component2}",
                "warning": "⚠️ WARNING: {warning_text}",
                "tool_required": "🔧 Required tool: {tool}",
                "time_estimate": "⏱️ Estimated time: {minutes} minutes"
            },
            "es": {
                "step_prefix": "Paso {step_number}:",
                "attach": "Conectar {component1} a {component2}",
                "screw": "Asegurar {component1} a {component2} usando {fastener}",
                "insert": "Insertar {component1} en {component2}",
                "align": "Alinear {component1} con {component2}",
                "warning": "⚠️ ADVERTENCIA: {warning_text}",
                "tool_required": "🔧 Herramienta requerida: {tool}",
                "time_estimate": "⏱️ Tiempo estimado: {minutes} minutos"
            }
        }
    
    async def generate_step_description(self, step: AssemblyStep, 
                                      components: Dict[str, CADComponent],
                                      language: str = "en") -> str:
        """Generate textual description for assembly step"""
        template = self.templates.get(language, self.templates["en"])
        
        primary_comp = components.get(step.primary_component, CADComponent("", "unknown", "", "", "", {}, 0, (0,0,0), ((0,0,0),(0,0,0)), []))
        secondary_comp = components.get(step.secondary_component, CADComponent("", "unknown", "", "", "", {}, 0, (0,0,0), ((0,0,0),(0,0,0)), [])) if step.secondary_component else None
        
        # Generate operation-specific description
        operation_template = template.get(step.operation.value, template["attach"])
        
        description_parts = [
            template["step_prefix"].format(step_number=step.step_number)
        ]
        
        if secondary_comp:
            operation_desc = operation_template.format(
                component1=primary_comp.name,
                component2=secondary_comp.name,
                fastener=step.fasteners[0] if step.fasteners else "appropriate fastener"
            )
        else:
            operation_desc = f"Position {primary_comp.name}"
        
        description_parts.append(operation_desc)
        
        # Add tool requirements
        if step.tools_required:
            for tool in step.tools_required:
                description_parts.append(template["tool_required"].format(tool=tool))
        
        # Add warnings
        for warning in step.warnings:
            description_parts.append(template["warning"].format(warning_text=warning))
        
        # Add time estimate
        if step.estimated_time > 0:
            minutes = step.estimated_time // 60
            if minutes > 0:
                description_parts.append(template["time_estimate"].format(minutes=minutes))
        
        return "\n".join(description_parts)
    
    async def generate_3d_visualization(self, step: AssemblyStep, 
                                      components: Dict[str, CADComponent]) -> Dict[str, Any]:
        """Generate 3D visualization data for assembly step"""
        visualization = {
            "step_number": step.step_number,
            "camera_position": self._calculate_optimal_camera_position(step, components),
            "highlighted_components": [step.primary_component],
            "component_positions": {},
            "animation_keyframes": [],
            "annotations": []
        }
        
        if step.secondary_component:
            visualization["highlighted_components"].append(step.secondary_component)
        
        # Generate component positions for this step
        for comp_id, component in components.items():
            if comp_id == step.primary_component:
                visualization["component_positions"][comp_id] = {
                    "position": step.position,
                    "orientation": step.orientation,
                    "color": "#FF6B6B",  # Highlighted color
                    "opacity": 1.0
                }
            elif comp_id == step.secondary_component:
                visualization["component_positions"][comp_id] = {
                    "position": component.center_of_mass,
                    "orientation": (0, 0, 0, 1),  # Identity quaternion
                    "color": "#4ECDC4",  # Secondary highlight
                    "opacity": 1.0
                }
            else:
                visualization["component_positions"][comp_id] = {
                    "position": component.center_of_mass,
                    "orientation": (0, 0, 0, 1),
                    "color": component.color,
                    "opacity": 0.3  # Dimmed
                }
        
        # Generate animation keyframes for assembly motion
        if step.operation in [AssemblyOperation.INSERT, AssemblyOperation.ATTACH]:
            visualization["animation_keyframes"] = self._generate_assembly_animation(step, components)
        
        # Add annotations for tools and fasteners
        if step.tools_required:
            visualization["annotations"].append({
                "type": "tool",
                "position": [step.position[0] + 50, step.position[1], step.position[2] + 20],
                "text": f"Use: {', '.join(step.tools_required)}"
            })
        
        return visualization
    
    def _calculate_optimal_camera_position(self, step: AssemblyStep, 
                                         components: Dict[str, CADComponent]) -> Tuple[float, float, float]:
        """Calculate optimal camera position for viewing assembly step"""
        primary_comp = components.get(step.primary_component)
        if not primary_comp:
            return (100, 100, 100)
        
        # Position camera to view the assembly operation
        center = primary_comp.center_of_mass
        
        # Calculate bounding sphere radius
        max_dim = max(primary_comp.dimensions.values())
        camera_distance = max_dim * 3
        
        # Position camera at 45-degree angle for good visibility
        camera_pos = (
            center[0] + camera_distance * 0.707,
            center[1] + camera_distance * 0.707,
            center[2] + camera_distance * 0.5
        )
        
        return camera_pos
    
    def _generate_assembly_animation(self, step: AssemblyStep, 
                                   components: Dict[str, CADComponent]) -> List[Dict[str, Any]]:
        """Generate keyframes for assembly animation"""
        keyframes = []
        
        if not step.secondary_component:
            return keyframes
        
        primary_comp = components.get(step.primary_component)
        secondary_comp = components.get(step.secondary_component)
        
        if not primary_comp or not secondary_comp:
            return keyframes
        
        # Start position (components separated)
        start_pos = (
            step.position[0],
            step.position[1],
            step.position[2] + 100  # 100mm above target
        )
        
        # End position (assembled)
        end_pos = step.position
        
        # Generate smooth interpolation
        num_frames = 30
        for i in range(num_frames + 1):
            t = i / num_frames
            
            # Smooth interpolation (ease-in-out)
            smooth_t = 3 * t * t - 2 * t * t * t
            
            interpolated_pos = (
                start_pos[0] + (end_pos[0] - start_pos[0]) * smooth_t,
                start_pos[1] + (end_pos[1] - start_pos[1]) * smooth_t,
                start_pos[2] + (end_pos[2] - start_pos[2]) * smooth_t
            )
            
            keyframes.append({
                "frame": i,
                "time": t,
                "component_id": step.primary_component,
                "position": interpolated_pos,
                "orientation": step.orientation
            })
        
        return keyframes


class AssemblyInstructionGenerator:
    """Main system for generating assembly instructions from CAD"""
    
    def __init__(self, db_path: str = "assembly_instructions.db"):
        self.db_path = db_path
        self.cad_processor = CADProcessor()
        self.sequence_optimizer = AssemblySequenceOptimizer()
        self.content_generator = InstructionContentGenerator(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize assembly instructions database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS instructions (
                instruction_id TEXT PRIMARY KEY,
                product_name TEXT,
                version TEXT,
                created_at TIMESTAMP,
                language TEXT,
                total_steps INTEGER,
                estimated_time INTEGER,
                difficulty TEXT,
                cad_file_path TEXT,
                instruction_data TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visualization_assets (
                asset_id TEXT PRIMARY KEY,
                instruction_id TEXT,
                asset_type TEXT,
                file_path TEXT,
                step_number INTEGER,
                metadata TEXT,
                FOREIGN KEY (instruction_id) REFERENCES instructions (instruction_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS component_library (
                component_id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                standard_tools TEXT,
                standard_fasteners TEXT,
                assembly_notes TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def generate_from_cad(self, cad_file_path: str, product_name: str, 
                              language: str = "en") -> AssemblyInstruction:
        """Generate assembly instructions from CAD file"""
        # Load and process CAD assembly
        components = await self.cad_processor.load_cad_assembly(cad_file_path)
        
        if not components:
            raise ValueError("No components found in CAD file")
        
        # Optimize assembly sequence
        sequence = await self.sequence_optimizer.optimize_sequence(components)
        
        # Generate assembly steps
        steps = await self._generate_assembly_steps(sequence, components, language)
        
        # Calculate overall metrics
        total_time = sum(step.estimated_time for step in steps) // 60  # Convert to minutes
        difficulty = self._determine_overall_difficulty(steps)
        tools_list = list(set(tool for step in steps for tool in step.tools_required))
        materials_list = [f"{comp.name} ({comp.material})" for comp in components]
        safety_warnings = self._generate_safety_warnings(steps, components)
        
        # Create instruction object
        instruction = AssemblyInstruction(
            instruction_id=f"inst_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            product_name=product_name,
            version="1.0",
            created_at=datetime.now(),
            language=language,
            total_steps=len(steps),
            estimated_time=total_time,
            difficulty=difficulty,
            tools_list=tools_list,
            materials_list=materials_list,
            safety_warnings=safety_warnings,
            steps=steps
        )
        
        # Generate visualization assets
        await self._generate_visualization_assets(instruction, components)
        
        # Store in database
        await self._store_instruction(instruction, cad_file_path)
        
        return instruction
    
    async def _generate_assembly_steps(self, sequence: List[Tuple[str, str, AssemblyOperation]], 
                                     components: List[CADComponent], 
                                     language: str) -> List[AssemblyStep]:
        """Generate detailed assembly steps from sequence"""
        steps = []
        components_dict = {comp.component_id: comp for comp in components}
        
        for i, (primary_id, secondary_id, operation) in enumerate(sequence):
            primary_comp = components_dict.get(primary_id)
            secondary_comp = components_dict.get(secondary_id)
            
            if not primary_comp:
                continue
            
            # Determine tools and fasteners required
            tools, fasteners = self._determine_tools_and_fasteners(operation, primary_comp, secondary_comp)
            
            # Calculate position and orientation
            position, orientation = self._calculate_assembly_transform(primary_comp, secondary_comp, operation)
            
            # Generate warnings
            warnings = self._generate_step_warnings(operation, primary_comp, secondary_comp)
            
            # Estimate time
            estimated_time = self._estimate_step_time(operation, primary_comp, secondary_comp)
            
            # Determine difficulty
            step_difficulty = self._determine_step_difficulty(operation, tools, warnings)
            
            # Generate step description
            step = AssemblyStep(
                step_number=i + 1,
                operation=operation,
                primary_component=primary_id,
                secondary_component=secondary_id,
                description="",  # Will be generated by content generator
                tools_required=tools,
                fasteners=fasteners,
                warnings=warnings,
                estimated_time=estimated_time,
                difficulty=step_difficulty,
                position=position,
                orientation=orientation,
                visualization_data={}
            )
            
            # Generate description
            step.description = await self.content_generator.generate_step_description(
                step, components_dict, language
            )
            
            # Generate visualization data
            step.visualization_data = await self.content_generator.generate_3d_visualization(
                step, components_dict
            )
            
            steps.append(step)
        
        return steps
    
    def _determine_tools_and_fasteners(self, operation: AssemblyOperation, 
                                     primary_comp: CADComponent,
                                     secondary_comp: Optional[CADComponent]) -> Tuple[List[str], List[str]]:
        """Determine required tools and fasteners for operation"""
        tools = []
        fasteners = []
        
        tool_mapping = {
            AssemblyOperation.SCREW: ["screwdriver", "drill"],
            AssemblyOperation.ATTACH: ["allen_key", "wrench"],
            AssemblyOperation.INSERT: [],
            AssemblyOperation.GLUE: ["applicator"],
            AssemblyOperation.WELD: ["welding_torch", "safety_equipment"],
            AssemblyOperation.PRESS_FIT: ["press", "assembly_jig"],
            AssemblyOperation.SNAP: [],
            AssemblyOperation.ALIGN: ["alignment_tool"],
            AssemblyOperation.ROTATE: ["wrench"],
            AssemblyOperation.SLIDE: []
        }
        
        fastener_mapping = {
            AssemblyOperation.SCREW: ["M5x20_screw", "washer"],
            AssemblyOperation.ATTACH: ["M8x25_bolt", "nut", "washer"],
            AssemblyOperation.GLUE: ["epoxy_adhesive"],
            AssemblyOperation.WELD: ["welding_rod"],
            AssemblyOperation.PRESS_FIT: [],
            AssemblyOperation.SNAP: [],
            AssemblyOperation.INSERT: [],
            AssemblyOperation.ALIGN: [],
            AssemblyOperation.ROTATE: [],
            AssemblyOperation.SLIDE: []
        }
        
        tools = tool_mapping.get(operation, [])
        fasteners = fastener_mapping.get(operation, [])
        
        # Adjust based on component size and material
        if primary_comp.mass > 2.0:  # Heavy component
            if "wrench" in tools:
                tools.append("torque_wrench")
        
        if primary_comp.material == "aluminum" and operation == AssemblyOperation.SCREW:
            fasteners = ["aluminum_screw", "anti_seize"]
        
        return tools, fasteners
    
    def _calculate_assembly_transform(self, primary_comp: CADComponent,
                                    secondary_comp: Optional[CADComponent],
                                    operation: AssemblyOperation) -> Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
        """Calculate position and orientation for assembly step"""
        if not secondary_comp:
            return primary_comp.center_of_mass, (0, 0, 0, 1)
        
        # Calculate relative position based on operation
        if operation == AssemblyOperation.INSERT:
            # Insert primary into secondary
            position = secondary_comp.center_of_mass
        elif operation in [AssemblyOperation.ATTACH, AssemblyOperation.SCREW]:
            # Attach primary to secondary surface
            position = (
                secondary_comp.center_of_mass[0],
                secondary_comp.center_of_mass[1],
                secondary_comp.bounding_box[1][2]  # Top surface
            )
        else:
            # Default to secondary component position
            position = secondary_comp.center_of_mass
        
        # Calculate orientation (simplified)
        orientation = (0, 0, 0, 1)  # Identity quaternion
        
        return position, orientation
    
    def _generate_step_warnings(self, operation: AssemblyOperation,
                              primary_comp: CADComponent,
                              secondary_comp: Optional[CADComponent]) -> List[str]:
        """Generate safety warnings for assembly step"""
        warnings = []
        
        # Operation-specific warnings
        if operation == AssemblyOperation.WELD:
            warnings.extend([
                "Wear appropriate welding safety equipment",
                "Ensure adequate ventilation",
                "Check material compatibility"
            ])
        elif operation == AssemblyOperation.GLUE:
            warnings.extend([
                "Use in well-ventilated area",
                "Avoid skin contact with adhesive"
            ])
        elif operation == AssemblyOperation.PRESS_FIT:
            warnings.append("Apply force gradually to avoid damage")
        
        # Component-specific warnings
        if primary_comp.mass > 5.0:
            warnings.append("Heavy component - use proper lifting technique")
        
        if primary_comp.material in ["aluminum", "plastic"]:
            warnings.append("Handle with care to avoid damage")
        
        return warnings
    
    def _estimate_step_time(self, operation: AssemblyOperation,
                          primary_comp: CADComponent,
                          secondary_comp: Optional[CADComponent]) -> int:
        """Estimate time for assembly step in seconds"""
        base_times = {
            AssemblyOperation.INSERT: 30,
            AssemblyOperation.ATTACH: 60,
            AssemblyOperation.SCREW: 45,
            AssemblyOperation.GLUE: 120,
            AssemblyOperation.WELD: 300,
            AssemblyOperation.PRESS_FIT: 90,
            AssemblyOperation.SNAP: 15,
            AssemblyOperation.ALIGN: 30,
            AssemblyOperation.ROTATE: 20,
            AssemblyOperation.SLIDE: 25
        }
        
        base_time = base_times.get(operation, 60)
        
        # Adjust for component complexity
        if primary_comp.mass > 2.0:
            base_time *= 1.5
        
        if len(primary_comp.attachment_points) > 4:
            base_time *= 1.2
        
        return int(base_time)
    
    def _determine_step_difficulty(self, operation: AssemblyOperation,
                                 tools: List[str], warnings: List[str]) -> DifficultyLevel:
        """Determine difficulty level for assembly step"""
        difficulty_score = 0
        
        # Operation complexity
        operation_difficulty = {
            AssemblyOperation.SNAP: 1,
            AssemblyOperation.INSERT: 1,
            AssemblyOperation.SLIDE: 1,
            AssemblyOperation.ALIGN: 2,
            AssemblyOperation.ATTACH: 2,
            AssemblyOperation.ROTATE: 2,
            AssemblyOperation.SCREW: 3,
            AssemblyOperation.GLUE: 3,
            AssemblyOperation.PRESS_FIT: 4,
            AssemblyOperation.WELD: 5
        }
        
        difficulty_score += operation_difficulty.get(operation, 2)
        
        # Tool complexity
        specialized_tools = ["welding_torch", "press", "torque_wrench"]
        if any(tool in specialized_tools for tool in tools):
            difficulty_score += 2
        
        # Warning level
        difficulty_score += len(warnings)
        
        if difficulty_score <= 2:
            return DifficultyLevel.BEGINNER
        elif difficulty_score <= 4:
            return DifficultyLevel.INTERMEDIATE
        elif difficulty_score <= 6:
            return DifficultyLevel.ADVANCED
        else:
            return DifficultyLevel.EXPERT
    
    def _determine_overall_difficulty(self, steps: List[AssemblyStep]) -> DifficultyLevel:
        """Determine overall assembly difficulty"""
        difficulty_scores = {
            DifficultyLevel.BEGINNER: 1,
            DifficultyLevel.INTERMEDIATE: 2,
            DifficultyLevel.ADVANCED: 3,
            DifficultyLevel.EXPERT: 4
        }
        
        max_difficulty = max(difficulty_scores[step.difficulty] for step in steps)
        avg_difficulty = sum(difficulty_scores[step.difficulty] for step in steps) / len(steps)
        
        # Overall difficulty is weighted average of max and average
        overall_score = 0.7 * max_difficulty + 0.3 * avg_difficulty
        
        if overall_score <= 1.5:
            return DifficultyLevel.BEGINNER
        elif overall_score <= 2.5:
            return DifficultyLevel.INTERMEDIATE
        elif overall_score <= 3.5:
            return DifficultyLevel.ADVANCED
        else:
            return DifficultyLevel.EXPERT
    
    def _generate_safety_warnings(self, steps: List[AssemblyStep], 
                                components: List[CADComponent]) -> List[str]:
        """Generate overall safety warnings"""
        warnings = set()
        
        # Collect all step warnings
        for step in steps:
            warnings.update(step.warnings)
        
        # Add general safety warnings
        warnings.add("Read all instructions before beginning assembly")
        warnings.add("Ensure workspace is clean and well-lit")
        
        # Heavy component warnings
        if any(comp.mass > 5.0 for comp in components):
            warnings.add("Heavy components present - use proper lifting techniques")
        
        # Sharp edge warnings
        if any("metal" in comp.material.lower() for comp in components):
            warnings.add("Be aware of sharp edges on metal components")
        
        return list(warnings)
    
    async def _generate_visualization_assets(self, instruction: AssemblyInstruction,
                                           components: List[CADComponent]):
        """Generate visualization assets for instruction"""
        # Generate step-by-step images
        for step in instruction.steps:
            # Generate 2D instruction diagram
            image_asset = await self._generate_step_diagram(step, components)
            
            # Generate 3D visualization file
            model_asset = await self._generate_3d_model(step, components)
            
            # Store asset references
            step.visualization_data["image_path"] = image_asset["file_path"]
            step.visualization_data["model_path"] = model_asset["file_path"]
    
    async def _generate_step_diagram(self, step: AssemblyStep, 
                                   components: List[CADComponent]) -> Dict[str, Any]:
        """Generate 2D instruction diagram for step"""
        # Create matplotlib figure
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot components
        components_dict = {comp.component_id: comp for comp in components}
        
        for comp_id, comp in components_dict.items():
            bbox = comp.bounding_box
            
            # Create wireframe box for component
            x = [bbox[0][0], bbox[1][0]]
            y = [bbox[0][1], bbox[1][1]]
            z = [bbox[0][2], bbox[1][2]]
            
            color = '#FF6B6B' if comp_id == step.primary_component else '#CCCCCC'
            alpha = 1.0 if comp_id in [step.primary_component, step.secondary_component] else 0.3
            
            # Plot wireframe
            for i in range(2):
                for j in range(2):
                    ax.plot([x[0], x[1]], [y[i], y[i]], [z[j], z[j]], color=color, alpha=alpha)
                    ax.plot([x[i], x[i]], [y[0], y[1]], [z[j], z[j]], color=color, alpha=alpha)
                    ax.plot([x[i], x[i]], [y[j], y[j]], [z[0], z[1]], color=color, alpha=alpha)
        
        # Set title and labels
        ax.set_title(f"Step {step.step_number}: {step.operation.value.replace('_', ' ').title()}")
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        
        # Save figure
        file_path = f"step_{step.step_number}_diagram.png"
        plt.savefig(file_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return {
            "asset_id": f"img_{step.step_number}",
            "asset_type": InstructionType.IMAGE,
            "file_path": file_path,
            "description": f"Assembly diagram for step {step.step_number}"
        }
    
    async def _generate_3d_model(self, step: AssemblyStep, 
                               components: List[CADComponent]) -> Dict[str, Any]:
        """Generate 3D model file for step visualization"""
        # Generate simplified 3D model data
        model_data = {
            "step": step.step_number,
            "components": [],
            "camera": step.visualization_data.get("camera_position", (100, 100, 100)),
            "animation": step.visualization_data.get("animation_keyframes", [])
        }
        
        components_dict = {comp.component_id: comp for comp in components}
        
        for comp_id, comp in components_dict.items():
            component_data = {
                "id": comp_id,
                "name": comp.name,
                "position": comp.center_of_mass,
                "dimensions": comp.dimensions,
                "color": comp.color,
                "highlighted": comp_id in [step.primary_component, step.secondary_component]
            }
            model_data["components"].append(component_data)
        
        # Save as JSON (in production, use proper 3D format like glTF)
        file_path = f"step_{step.step_number}_model.json"
        with open(file_path, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        return {
            "asset_id": f"model_{step.step_number}",
            "asset_type": InstructionType.INTERACTIVE_3D,
            "file_path": file_path,
            "description": f"3D model for step {step.step_number}"
        }
    
    async def _store_instruction(self, instruction: AssemblyInstruction, cad_file_path: str):
        """Store instruction in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store main instruction
        cursor.execute("""
            INSERT INTO instructions 
            (instruction_id, product_name, version, created_at, language, 
             total_steps, estimated_time, difficulty, cad_file_path, instruction_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            instruction.instruction_id, instruction.product_name, instruction.version,
            instruction.created_at, instruction.language, instruction.total_steps,
            instruction.estimated_time, instruction.difficulty.value,
            cad_file_path, json.dumps(asdict(instruction), default=str)
        ))
        
        # Store visualization assets
        for step in instruction.steps:
            if "image_path" in step.visualization_data:
                cursor.execute("""
                    INSERT INTO visualization_assets 
                    (asset_id, instruction_id, asset_type, file_path, step_number, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"img_{step.step_number}", instruction.instruction_id,
                    InstructionType.IMAGE.value, step.visualization_data["image_path"],
                    step.step_number, json.dumps({"type": "diagram"})
                ))
            
            if "model_path" in step.visualization_data:
                cursor.execute("""
                    INSERT INTO visualization_assets 
                    (asset_id, instruction_id, asset_type, file_path, step_number, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"model_{step.step_number}", instruction.instruction_id,
                    InstructionType.INTERACTIVE_3D.value, step.visualization_data["model_path"],
                    step.step_number, json.dumps({"type": "3d_model"})
                ))
        
        conn.commit()
        conn.close()
    
    async def export_instruction_manual(self, instruction_id: str, 
                                      format_type: str = "pdf") -> str:
        """Export complete instruction manual in specified format"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT instruction_data FROM instructions WHERE instruction_id = ?", 
                      (instruction_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Instruction {instruction_id} not found")
        
        instruction_data = json.loads(row[0])
        
        if format_type == "pdf":
            return await self._export_pdf(instruction_data)
        elif format_type == "html":
            return await self._export_html(instruction_data)
        elif format_type == "json":
            return await self._export_json(instruction_data)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    async def _export_pdf(self, instruction_data: Dict[str, Any]) -> str:
        """Export instruction as PDF"""
        # Placeholder for PDF generation
        # In production, use libraries like ReportLab or WeasyPrint
        filename = f"assembly_instructions_{instruction_data['instruction_id']}.pdf"
        
        # Simulate PDF creation
        with open(filename, 'w') as f:
            f.write("PDF Assembly Instructions\n")
            f.write(f"Product: {instruction_data['product_name']}\n")
            f.write(f"Steps: {instruction_data['total_steps']}\n")
        
        return filename
    
    async def _export_html(self, instruction_data: Dict[str, Any]) -> str:
        """Export instruction as interactive HTML"""
        filename = f"assembly_instructions_{instruction_data['instruction_id']}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Assembly Instructions - {instruction_data['product_name']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .step {{ margin: 20px 0; padding: 15px; border: 1px solid #ccc; }}
                .warning {{ color: red; font-weight: bold; }}
                .tools {{ color: blue; }}
            </style>
        </head>
        <body>
            <h1>Assembly Instructions: {instruction_data['product_name']}</h1>
            <p>Total Steps: {instruction_data['total_steps']}</p>
            <p>Estimated Time: {instruction_data['estimated_time']} minutes</p>
            <p>Difficulty: {instruction_data['difficulty']}</p>
            
            <h2>Safety Warnings</h2>
            <ul>
        """
        
        for warning in instruction_data.get('safety_warnings', []):
            html_content += f"<li class='warning'>{warning}</li>\n"
        
        html_content += """
            </ul>
            
            <h2>Assembly Steps</h2>
        """
        
        for step in instruction_data.get('steps', []):
            html_content += f"""
            <div class="step">
                <h3>Step {step['step_number']}: {step['operation'].replace('_', ' ').title()}</h3>
                <p>{step['description']}</p>
                <p class="tools">Tools: {', '.join(step['tools_required'])}</p>
                <p>Estimated time: {step['estimated_time'] // 60} minutes</p>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        with open(filename, 'w') as f:
            f.write(html_content)
        
        return filename
    
    async def _export_json(self, instruction_data: Dict[str, Any]) -> str:
        """Export instruction as JSON"""
        filename = f"assembly_instructions_{instruction_data['instruction_id']}.json"
        
        with open(filename, 'w') as f:
            json.dump(instruction_data, f, indent=2, default=str)
        
        return filename


async def main():
    """Example usage of Assembly Instruction Generator"""
    generator = AssemblyInstructionGenerator()
    
    # Example CAD file path (would be actual STEP/STL file in production)
    cad_file = "/path/to/assembly.step"
    
    try:
        # Generate instructions
        instruction = await generator.generate_from_cad(
            cad_file, 
            "Electronic Enclosure Assembly",
            language="en"
        )
        
        print(f"Generated Instructions: {instruction.instruction_id}")
        print(f"Product: {instruction.product_name}")
        print(f"Total Steps: {instruction.total_steps}")
        print(f"Estimated Time: {instruction.estimated_time} minutes")
        print(f"Difficulty: {instruction.difficulty.value}")
        print(f"Tools Required: {', '.join(instruction.tools_list)}")
        
        print("\nAssembly Steps:")
        for step in instruction.steps:
            print(f"\nStep {step.step_number}:")
            print(f"  Operation: {step.operation.value}")
            print(f"  Description: {step.description}")
            print(f"  Tools: {', '.join(step.tools_required)}")
            print(f"  Time: {step.estimated_time // 60} minutes")
            print(f"  Difficulty: {step.difficulty.value}")
        
        # Export to different formats
        pdf_file = await generator.export_instruction_manual(instruction.instruction_id, "pdf")
        html_file = await generator.export_instruction_manual(instruction.instruction_id, "html")
        
        print(f"\nExported Files:")
        print(f"  PDF: {pdf_file}")
        print(f"  HTML: {html_file}")
        
    except Exception as e:
        print(f"Error generating instructions: {e}")


if __name__ == "__main__":
    asyncio.run(main())