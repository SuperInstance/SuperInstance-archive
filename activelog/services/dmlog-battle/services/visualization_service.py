"""
Visualization service for combat battlefield and area of effect rendering.
"""

import math
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import logging

from ..models.base import Position, GridCell, CoverType
from ..models.battlefield import BattlefieldSchema, AreaOfEffect, LightSource, AOEShape
from ..models.combatant import CombatantSchema
from ..models.combat import CombatEncounter
from ..config import Config

logger = logging.getLogger(__name__)

@dataclass
class VisualCell:
    """Visual representation of a grid cell."""
    position: Position
    terrain_color: str = "#8B4513"  # Brown for normal terrain
    elevation: int = 0
    has_creature: bool = False
    creature_id: Optional[str] = None
    has_hazard: bool = False
    provides_cover: CoverType = CoverType.NONE
    light_level: float = 1.0
    in_aoe: List[str] = None  # AOE effect IDs
    highlighted: bool = False
    movement_cost_modifier: float = 1.0

    def __post_init__(self):
        if self.in_aoe is None:
            self.in_aoe = []

@dataclass
class BattlefieldVisualization:
    """Complete visualization of the battlefield state."""
    encounter_id: str
    width: int
    height: int
    cells: List[List[VisualCell]]
    aoe_effects: List[AreaOfEffect]
    creature_positions: Dict[str, Position]
    light_sources: List[LightSource]
    highlighted_positions: Set[Position]
    movement_paths: List[List[Position]]

class VisualizationService:
    """Service for creating battlefield visualizations."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        
        # Color schemes for different terrain types
        self.terrain_colors = {
            "normal": "#8B4513",      # Brown
            "difficult": "#654321",   # Dark brown
            "water": "#4169E1",       # Blue
            "lava": "#DC143C",        # Red
            "ice": "#B0E0E6",         # Light blue
            "swamp": "#556B2F",       # Dark olive
            "sand": "#F4A460",        # Sandy brown
            "stone": "#708090",       # Slate gray
            "grass": "#228B22",       # Forest green
            "mud": "#8B4513",         # Brown
        }
        
        # AOE effect colors
        self.aoe_colors = {
            "fire": {"fill": "#FF4500", "border": "#8B0000"},
            "cold": {"fill": "#87CEEB", "border": "#4682B4"},
            "lightning": {"fill": "#FFFF00", "border": "#FFD700"},
            "acid": {"fill": "#ADFF2F", "border": "#32CD32"},
            "poison": {"fill": "#9ACD32", "border": "#556B2F"},
            "necrotic": {"fill": "#4B0082", "border": "#2F0052"},
            "radiant": {"fill": "#FFD700", "border": "#FFA500"},
            "force": {"fill": "#8A2BE2", "border": "#4B0082"},
            "psychic": {"fill": "#FF69B4", "border": "#C71585"},
            "thunder": {"fill": "#1E90FF", "border": "#0000CD"},
            "default": {"fill": "#FF6347", "border": "#8B0000"}
        }
    
    def create_battlefield_visualization(
        self,
        encounter: CombatEncounter,
        observer: Optional[CombatantSchema] = None,
        show_all: bool = False
    ) -> BattlefieldVisualization:
        """Create a complete visualization of the battlefield."""
        
        battlefield = encounter.battlefield
        
        # Initialize visualization grid
        cells = []
        for y in range(battlefield.height):
            row = []
            for x in range(battlefield.width):
                position = Position(x=x, y=y)
                cell = battlefield.get_cell(position)
                
                visual_cell = VisualCell(
                    position=position,
                    terrain_color=self._get_terrain_color(cell),
                    elevation=cell.elevation if cell else 0,
                    provides_cover=cell.cover_type if cell else CoverType.NONE,
                    light_level=cell.light_level if cell else 1.0,
                    movement_cost_modifier=2.0 if cell and cell.is_difficult_terrain else 1.0
                )
                
                # Add creature information
                for combatant in encounter.combatants:
                    if combatant.position == position:
                        visual_cell.has_creature = True
                        visual_cell.creature_id = combatant.id
                        break
                
                # Add hazard information
                if cell and cell.has_hazard:
                    visual_cell.has_hazard = True
                
                row.append(visual_cell)
            cells.append(row)
        
        # Apply AOE effects
        active_aoes = []
        for action in encounter.action_history:
            if action.area_of_effect:
                aoe = action.area_of_effect
                affected_positions = self._calculate_aoe_positions(battlefield, aoe)
                active_aoes.append(aoe)
                
                # Mark affected cells
                for pos in affected_positions:
                    if 0 <= pos.x < battlefield.width and 0 <= pos.y < battlefield.height:
                        cells[pos.y][pos.x].in_aoe.append(action.id)
        
        # Get creature positions
        creature_positions = {}
        for combatant in encounter.combatants:
            if combatant.position:
                creature_positions[combatant.id] = combatant.position
        
        return BattlefieldVisualization(
            encounter_id=encounter.id,
            width=battlefield.width,
            height=battlefield.height,
            cells=cells,
            aoe_effects=active_aoes,
            creature_positions=creature_positions,
            light_sources=battlefield.light_sources,
            highlighted_positions=set(),
            movement_paths=[]
        )
    
    def add_aoe_visualization(
        self,
        visualization: BattlefieldVisualization,
        aoe: AreaOfEffect,
        effect_type: str = "default"
    ) -> BattlefieldVisualization:
        """Add an AOE effect to the visualization."""
        
        # Calculate affected positions
        affected_positions = self._calculate_aoe_positions_from_viz(visualization, aoe)
        
        # Update cells with AOE information
        for pos in affected_positions:
            if 0 <= pos.x < visualization.width and 0 <= pos.y < visualization.height:
                cell = visualization.cells[pos.y][pos.x]
                cell.in_aoe.append(f"{aoe.name}:{effect_type}")
        
        # Add to active AOEs
        visualization.aoe_effects.append(aoe)
        
        return visualization
    
    def highlight_positions(
        self,
        visualization: BattlefieldVisualization,
        positions: List[Position],
        highlight_type: str = "selection"
    ) -> BattlefieldVisualization:
        """Highlight specific positions on the battlefield."""
        
        for pos in positions:
            if 0 <= pos.x < visualization.width and 0 <= pos.y < visualization.height:
                visualization.cells[pos.y][pos.x].highlighted = True
                visualization.highlighted_positions.add(pos)
        
        return visualization
    
    def add_movement_path(
        self,
        visualization: BattlefieldVisualization,
        path: List[Position],
        path_type: str = "movement"
    ) -> BattlefieldVisualization:
        """Add a movement path to the visualization."""
        
        visualization.movement_paths.append(path)
        
        # Highlight path positions
        for pos in path:
            if 0 <= pos.x < visualization.width and 0 <= pos.y < visualization.height:
                visualization.cells[pos.y][pos.x].highlighted = True
        
        return visualization
    
    def render_to_ascii(
        self,
        visualization: BattlefieldVisualization,
        show_coordinates: bool = True,
        show_creatures: bool = True
    ) -> str:
        """Render visualization as ASCII art for debugging."""
        
        lines = []
        
        if show_coordinates:
            # Add column headers
            header = "   "
            for x in range(visualization.width):
                header += f"{x:2d}"
            lines.append(header)
        
        # Render each row
        for y in range(visualization.height):
            line = f"{y:2d} " if show_coordinates else ""
            
            for x in range(visualization.width):
                cell = visualization.cells[y][x]
                char = self._get_ascii_char(cell, show_creatures)
                line += f"{char:2s}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def render_to_json(self, visualization: BattlefieldVisualization) -> Dict:
        """Render visualization as JSON for web frontend."""
        
        cell_data = []
        for y in range(visualization.height):
            row = []
            for x in range(visualization.width):
                cell = visualization.cells[y][x]
                cell_json = {
                    "x": x,
                    "y": y,
                    "terrain_color": cell.terrain_color,
                    "elevation": cell.elevation,
                    "has_creature": cell.has_creature,
                    "creature_id": cell.creature_id,
                    "has_hazard": cell.has_hazard,
                    "cover": cell.provides_cover.value if cell.provides_cover else "none",
                    "light_level": cell.light_level,
                    "in_aoe": cell.in_aoe,
                    "highlighted": cell.highlighted,
                    "movement_cost": cell.movement_cost_modifier
                }
                row.append(cell_json)
            cell_data.append(row)
        
        aoe_data = []
        for aoe in visualization.aoe_effects:
            aoe_json = {
                "id": aoe.id,
                "name": aoe.name,
                "shape": aoe.shape.value,
                "origin": {"x": aoe.origin.x, "y": aoe.origin.y},
                "size": aoe.size,
                "color": aoe.color,
                "opacity": aoe.opacity,
                "affected_positions": [{"x": p.x, "y": p.y} for p in aoe.affected_positions]
            }
            if aoe.target_position:
                aoe_json["target"] = {"x": aoe.target_position.x, "y": aoe.target_position.y}
            aoe_data.append(aoe_json)
        
        return {
            "encounter_id": visualization.encounter_id,
            "width": visualization.width,
            "height": visualization.height,
            "cells": cell_data,
            "aoe_effects": aoe_data,
            "creatures": [
                {"id": cid, "x": pos.x, "y": pos.y} 
                for cid, pos in visualization.creature_positions.items()
            ],
            "light_sources": [
                {
                    "id": ls.id,
                    "name": ls.name,
                    "x": ls.position.x,
                    "y": ls.position.y,
                    "bright_radius": ls.bright_radius,
                    "dim_radius": ls.dim_radius,
                    "active": ls.active
                }
                for ls in visualization.light_sources
            ],
            "highlighted": [{"x": p.x, "y": p.y} for p in visualization.highlighted_positions],
            "movement_paths": [
                [{"x": p.x, "y": p.y} for p in path] 
                for path in visualization.movement_paths
            ]
        }
    
    def _get_terrain_color(self, cell: Optional[GridCell]) -> str:
        """Get color for terrain type."""
        if not cell:
            return self.terrain_colors["normal"]
        
        terrain_name = cell.terrain_type.value.lower() if cell.terrain_type else "normal"
        return self.terrain_colors.get(terrain_name, self.terrain_colors["normal"])
    
    def _calculate_aoe_positions(
        self,
        battlefield: BattlefieldSchema,
        aoe: AreaOfEffect
    ) -> List[Position]:
        """Calculate positions affected by an AOE on the battlefield."""
        
        positions = []
        
        if aoe.shape == AOEShape.SPHERE:
            radius_squares = aoe.size // battlefield.square_size_feet
            for y in range(battlefield.height):
                for x in range(battlefield.width):
                    pos = Position(x=x, y=y)
                    distance = aoe.origin.distance_to(pos)
                    if distance <= radius_squares:
                        positions.append(pos)
        
        elif aoe.shape == AOEShape.CUBE:
            half_size = (aoe.size // battlefield.square_size_feet) // 2
            for y in range(max(0, aoe.origin.y - half_size),
                          min(battlefield.height, aoe.origin.y + half_size + 1)):
                for x in range(max(0, aoe.origin.x - half_size),
                              min(battlefield.width, aoe.origin.x + half_size + 1)):
                    positions.append(Position(x=x, y=y))
        
        elif aoe.shape == AOEShape.CONE:
            radius_squares = aoe.size // battlefield.square_size_feet
            direction_rad = (aoe.direction or 0) * math.pi / 180
            cone_angle_rad = 90 * math.pi / 180  # 90 degree cone
            
            for y in range(max(0, aoe.origin.y - radius_squares),
                          min(battlefield.height, aoe.origin.y + radius_squares + 1)):
                for x in range(max(0, aoe.origin.x - radius_squares),
                              min(battlefield.width, aoe.origin.x + radius_squares + 1)):
                    pos = Position(x=x, y=y)
                    distance = aoe.origin.distance_to(pos)
                    
                    if distance <= radius_squares:
                        angle_to_pos = math.atan2(pos.y - aoe.origin.y, pos.x - aoe.origin.x)
                        angle_diff = abs(angle_to_pos - direction_rad)
                        
                        if angle_diff > math.pi:
                            angle_diff = 2 * math.pi - angle_diff
                        
                        if angle_diff <= cone_angle_rad / 2:
                            positions.append(pos)
        
        elif aoe.shape == AOEShape.LINE:
            if aoe.target_position:
                # Calculate line positions
                line_positions = self._get_line_positions(aoe.origin, aoe.target_position)
                
                width_squares = (aoe.width or battlefield.square_size_feet) // battlefield.square_size_feet
                if width_squares > 1:
                    # Expand line for width
                    for pos in line_positions:
                        for dy in range(-width_squares//2, width_squares//2 + 1):
                            new_pos = Position(x=pos.x, y=pos.y + dy)
                            if (0 <= new_pos.x < battlefield.width and 
                                0 <= new_pos.y < battlefield.height):
                                positions.append(new_pos)
                else:
                    positions = line_positions
        
        return positions
    
    def _calculate_aoe_positions_from_viz(
        self,
        visualization: BattlefieldVisualization,
        aoe: AreaOfEffect
    ) -> List[Position]:
        """Calculate AOE positions using visualization dimensions."""
        
        positions = []
        square_size_feet = 5  # Standard D&D grid size
        
        if aoe.shape == AOEShape.SPHERE:
            radius_squares = aoe.size // square_size_feet
            for y in range(visualization.height):
                for x in range(visualization.width):
                    pos = Position(x=x, y=y)
                    distance = aoe.origin.distance_to(pos)
                    if distance <= radius_squares:
                        positions.append(pos)
        
        # Similar logic for other shapes...
        # (Implementation would mirror _calculate_aoe_positions)
        
        return positions
    
    def _get_line_positions(self, start: Position, end: Position) -> List[Position]:
        """Get positions along a line using Bresenham's algorithm."""
        
        positions = []
        dx = abs(end.x - start.x)
        dy = abs(end.y - start.y)
        
        x, y = start.x, start.y
        x_inc = 1 if start.x < end.x else -1
        y_inc = 1 if start.y < end.y else -1
        
        error = dx - dy
        
        while True:
            positions.append(Position(x=x, y=y))
            
            if x == end.x and y == end.y:
                break
            
            error2 = 2 * error
            
            if error2 > -dy:
                error -= dy
                x += x_inc
            
            if error2 < dx:
                error += dx
                y += y_inc
        
        return positions
    
    def _get_ascii_char(self, cell: VisualCell, show_creatures: bool) -> str:
        """Get ASCII character representation for a cell."""
        
        if show_creatures and cell.has_creature:
            return "C"  # Creature
        elif cell.has_hazard:
            return "H"  # Hazard
        elif cell.in_aoe:
            return "X"  # Area of effect
        elif cell.highlighted:
            return "*"  # Highlighted
        elif cell.provides_cover == CoverType.TOTAL:
            return "#"  # Full cover (wall)
        elif cell.provides_cover in [CoverType.HALF, CoverType.THREE_QUARTERS]:
            return "+"  # Partial cover
        elif cell.movement_cost_modifier > 1.0:
            return "~"  # Difficult terrain
        else:
            return "."  # Normal terrain