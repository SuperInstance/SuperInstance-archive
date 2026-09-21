"""
Tactical grid system service for combat simulation.
"""

import random
import math
import numpy as np
from typing import Dict, List, Optional, Tuple, Set
import logging

from ..models.base import Position, GridCell, TerrainType, CoverType, LineOfSight
from ..models.battlefield import BattlefieldSchema, EnvironmentalHazard, LightSource, AreaOfEffect, GridArea
from ..models.combatant import CombatantSchema
from ..config import Config

logger = logging.getLogger(__name__)

class GridService:
    """Service for tactical grid operations."""
    
    def __init__(self):
        self.config = Config()
        
    def calculate_line_of_sight(
        self,
        battlefield: BattlefieldSchema,
        from_pos: Position,
        to_pos: Position,
        observer: Optional[CombatantSchema] = None
    ) -> LineOfSight:
        """Calculate line of sight between two positions."""
        
        # Get line positions using Bresenham's algorithm
        line_positions = self._get_line_positions(from_pos, to_pos)
        
        # Check for blocking terrain
        blocking_positions = []
        has_los = True
        
        # Skip the first position (observer) and check intermediate positions
        for pos in line_positions[1:-1]:
            cell = battlefield.get_cell(pos)
            if cell and cell.blocks_vision:
                blocking_positions.append(pos)
                has_los = False
        
        # Calculate cover for target
        cover_type = self.calculate_cover(battlefield, from_pos, to_pos, observer)
        
        # Check lighting and vision
        light_penalty = self._calculate_light_penalty(
            battlefield, to_pos, observer
        )
        requires_darkvision = light_penalty > 0
        
        distance = from_pos.distance_to(to_pos) * battlefield.square_size_feet
        
        return LineOfSight(
            from_position=from_pos,
            to_position=to_pos,
            has_line_of_sight=has_los,
            blocking_positions=blocking_positions,
            cover_type=cover_type,
            distance=distance,
            light_penalty=light_penalty,
            requires_darkvision=requires_darkvision
        )
    
    def calculate_cover(
        self,
        battlefield: BattlefieldSchema,
        attacker_pos: Position,
        target_pos: Position,
        attacker: Optional[CombatantSchema] = None
    ) -> CoverType:
        """Calculate cover between attacker and target."""
        
        # Get line positions
        line_positions = self._get_line_positions(attacker_pos, target_pos)
        
        # Count blocking squares (excluding endpoints)
        blocking_count = 0
        total_line_squares = len(line_positions) - 2  # Exclude start and end
        
        if total_line_squares <= 0:
            return CoverType.NONE
        
        for pos in line_positions[1:-1]:  # Skip attacker and target positions
            cell = battlefield.get_cell(pos)
            if cell and (cell.blocks_vision or cell.cover != CoverType.NONE):
                blocking_count += 1
        
        # Calculate cover based on percentage of line blocked
        if total_line_squares > 0:
            blocked_percentage = blocking_count / total_line_squares
            
            if blocked_percentage >= 0.75:
                return CoverType.TOTAL
            elif blocked_percentage >= 0.5:
                return CoverType.THREE_QUARTERS
            elif blocked_percentage >= 0.25:
                return CoverType.HALF
        
        return CoverType.NONE
    
    def calculate_movement_path(
        self,
        battlefield: BattlefieldSchema,
        combatant: CombatantSchema,
        start_pos: Position,
        end_pos: Position,
        remaining_movement: int
    ) -> List[Position]:
        """Calculate valid movement path using A* pathfinding."""
        
        if not battlefield.is_valid_position(start_pos) or not battlefield.is_valid_position(end_pos):
            return []
        
        # A* pathfinding implementation
        open_set = [(0, start_pos, [])]  # (f_score, position, path)
        closed_set = set()
        g_scores = {start_pos: 0}
        
        while open_set:
            # Get position with lowest f_score
            open_set.sort(key=lambda x: x[0])
            current_f, current_pos, current_path = open_set.pop(0)
            
            if current_pos == end_pos:
                return current_path + [current_pos]
            
            closed_set.add(current_pos)
            
            # Check all adjacent positions
            for adjacent in current_pos.adjacent_positions():
                if not battlefield.is_valid_position(adjacent):
                    continue
                    
                if adjacent in closed_set:
                    continue
                
                cell = battlefield.get_cell(adjacent)
                if not cell or cell.blocks_movement:
                    continue
                
                # Calculate movement cost
                move_cost = self._get_movement_cost(
                    battlefield, current_pos, adjacent, combatant
                )
                
                tentative_g = g_scores[current_pos] + move_cost
                
                # Check if this path exceeds remaining movement
                if tentative_g > remaining_movement:
                    continue
                
                if adjacent not in g_scores or tentative_g < g_scores[adjacent]:
                    g_scores[adjacent] = tentative_g
                    h_score = self._heuristic_distance(adjacent, end_pos)
                    f_score = tentative_g + h_score
                    
                    new_path = current_path + [current_pos]
                    open_set.append((f_score, adjacent, new_path))
        
        # No path found
        return []
    
    def get_positions_in_range(
        self,
        battlefield: BattlefieldSchema,
        center: Position,
        range_feet: int,
        shape: str = "circle"
    ) -> List[Position]:
        """Get all positions within range of center position."""
        
        positions = []
        range_squares = range_feet // battlefield.square_size_feet
        
        if shape == "circle":
            for y in range(battlefield.height):
                for x in range(battlefield.width):
                    pos = Position(x=x, y=y)
                    distance = center.distance_to(pos)
                    if distance <= range_squares:
                        positions.append(pos)
        
        elif shape == "square":
            for y in range(max(0, center.y - range_squares),
                          min(battlefield.height, center.y + range_squares + 1)):
                for x in range(max(0, center.x - range_squares),
                              min(battlefield.width, center.x + range_squares + 1)):
                    positions.append(Position(x=x, y=y))
        
        return positions
    
    def calculate_area_of_effect(
        self,
        battlefield: BattlefieldSchema,
        aoe: AreaOfEffect
    ) -> List[Position]:
        """Calculate positions affected by area of effect."""
        
        return aoe.calculate_affected_positions(battlefield)
    
    def get_flanking_positions(
        self,
        battlefield: BattlefieldSchema,
        target_pos: Position,
        target_size: str = "medium"
    ) -> List[Position]:
        """Get positions that would provide flanking against target."""
        
        flanking_positions = []
        
        # For medium creatures, flanking is opposite sides
        if target_size.lower() in ["tiny", "small", "medium"]:
            # Get all adjacent positions
            adjacent = target_pos.adjacent_positions()
            
            for pos in adjacent:
                if battlefield.is_valid_position(pos):
                    # Check if there's a potential ally on opposite side
                    opposite_x = target_pos.x + (target_pos.x - pos.x)
                    opposite_y = target_pos.y + (target_pos.y - pos.y)
                    opposite_pos = Position(x=opposite_x, y=opposite_y)
                    
                    if battlefield.is_valid_position(opposite_pos):
                        flanking_positions.append(pos)
        
        return flanking_positions
    
    def calculate_opportunity_attacks(
        self,
        battlefield: BattlefieldSchema,
        moving_combatant: CombatantSchema,
        path: List[Position],
        all_combatants: List[CombatantSchema]
    ) -> List[Tuple[str, Position]]:
        """Calculate opportunity attacks provoked by movement."""
        
        opportunity_attacks = []
        
        for i in range(len(path) - 1):
            current_pos = path[i]
            next_pos = path[i + 1]
            
            # Check each enemy combatant for opportunity attacks
            for combatant in all_combatants:
                if (combatant.id == moving_combatant.id or 
                    not combatant.can_take_actions() or
                    combatant.creature_type == moving_combatant.creature_type):
                    continue
                
                if not combatant.position:
                    continue
                
                # Check if combatant can make opportunity attacks
                reach = 5  # Default reach in feet
                reach_squares = reach // battlefield.square_size_feet
                
                # If moving combatant was in reach and is leaving reach
                was_in_reach = combatant.position.distance_to(current_pos) <= reach_squares
                still_in_reach = combatant.position.distance_to(next_pos) <= reach_squares
                
                if was_in_reach and not still_in_reach:
                    # Check line of sight
                    los = self.calculate_line_of_sight(
                        battlefield, combatant.position, current_pos, combatant
                    )
                    if los.has_line_of_sight:
                        opportunity_attacks.append((combatant.id, current_pos))
        
        return opportunity_attacks
    
    def is_position_threatened(
        self,
        battlefield: BattlefieldSchema,
        position: Position,
        by_combatants: List[CombatantSchema],
        exclude_combatant_id: Optional[str] = None
    ) -> bool:
        """Check if position is threatened by any combatants."""
        
        for combatant in by_combatants:
            if (combatant.id == exclude_combatant_id or 
                not combatant.can_take_actions() or
                not combatant.position):
                continue
            
            # Check if combatant threatens this position
            reach = 5  # Default reach
            reach_squares = reach // battlefield.square_size_feet
            
            distance = combatant.position.distance_to(position)
            if distance <= reach_squares:
                # Check line of sight
                los = self.calculate_line_of_sight(
                    battlefield, combatant.position, position, combatant
                )
                if los.has_line_of_sight:
                    return True
        
        return False
    
    def get_valid_placement_positions(
        self,
        battlefield: BattlefieldSchema,
        creature_size: str = "medium",
        avoid_hazards: bool = True
    ) -> List[Position]:
        """Get all valid positions for placing a creature."""
        
        valid_positions = []
        
        for y in range(battlefield.height):
            for x in range(battlefield.width):
                pos = Position(x=x, y=y)
                
                if self.is_valid_placement(
                    battlefield, pos, creature_size, avoid_hazards
                ):
                    valid_positions.append(pos)
        
        return valid_positions
    
    def is_valid_placement(
        self,
        battlefield: BattlefieldSchema,
        position: Position,
        creature_size: str = "medium",
        avoid_hazards: bool = True
    ) -> bool:
        """Check if position is valid for creature placement."""
        
        # Check basic position validity
        if not battlefield.is_valid_position(position):
            return False
        
        cell = battlefield.get_cell(position)
        if not cell:
            return False
        
        # Check for blocking terrain
        if cell.blocks_movement:
            return False
        
        # Check for hazards if avoiding them
        if avoid_hazards and cell.has_hazard:
            return False
        
        # For larger creatures, check additional squares
        size_squares = self._get_creature_size_squares(creature_size)
        
        if size_squares > 1:
            for dy in range(size_squares):
                for dx in range(size_squares):
                    check_pos = Position(x=position.x + dx, y=position.y + dy)
                    if not battlefield.is_valid_position(check_pos):
                        return False
                    
                    check_cell = battlefield.get_cell(check_pos)
                    if not check_cell or check_cell.blocks_movement:
                        return False
                    
                    if avoid_hazards and check_cell.has_hazard:
                        return False
        
        return True
    
    def _get_line_positions(self, start: Position, end: Position) -> List[Position]:
        """Get all positions along a line using Bresenham's algorithm."""
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
    
    def _calculate_light_penalty(
        self,
        battlefield: BattlefieldSchema,
        position: Position,
        observer: Optional[CombatantSchema]
    ) -> float:
        """Calculate lighting penalty for visibility."""
        
        # Get ambient light level
        cell = battlefield.get_cell(position)
        if not cell:
            return 0.0
        
        light_level = cell.light_level
        
        # Check for nearby light sources
        for light_source in battlefield.light_sources:
            if not light_source.active:
                continue
                
            distance = light_source.position.distance_to(position)
            distance_feet = distance * battlefield.square_size_feet
            
            if distance_feet <= light_source.bright_radius:
                light_level = max(light_level, 1.0)
            elif distance_feet <= light_source.dim_radius:
                light_level = max(light_level, 0.5)
        
        # Apply observer's vision capabilities
        if observer:
            if light_level <= 0.0 and observer.stats.darkvision > 0:
                # Can see in darkness with darkvision
                distance_feet = observer.position.distance_to(position) * battlefield.square_size_feet
                if distance_feet <= observer.stats.darkvision:
                    light_level = 0.5  # Darkvision sees as dim light
        
        # Calculate penalty
        if light_level >= 1.0:
            return 0.0  # No penalty in bright light
        elif light_level >= 0.5:
            return 0.0  # No penalty in dim light (but might impose disadvantage)
        elif light_level > 0.0:
            return 0.5  # Partial penalty
        else:
            return 1.0  # Full penalty (effectively blinded)
    
    def _get_movement_cost(
        self,
        battlefield: BattlefieldSchema,
        from_pos: Position,
        to_pos: Position,
        combatant: CombatantSchema
    ) -> int:
        """Calculate movement cost between adjacent positions."""
        
        base_cost = battlefield.square_size_feet
        
        # Check for diagonal movement
        if abs(from_pos.x - to_pos.x) == 1 and abs(from_pos.y - to_pos.y) == 1:
            base_cost = int(base_cost * self.config.GRID_SYSTEM["diagonal_cost"])
        
        # Check destination cell
        cell = battlefield.get_cell(to_pos)
        if cell:
            if cell.is_difficult_terrain:
                base_cost *= 2
            
            # Additional terrain costs could be added here
        
        return base_cost
    
    def _heuristic_distance(self, pos1: Position, pos2: Position) -> float:
        """Calculate heuristic distance for A* pathfinding."""
        # Use Euclidean distance as heuristic
        return pos1.distance_to(pos2)
    
    def _get_creature_size_squares(self, size: str) -> int:
        """Get number of squares a creature occupies per side."""
        size_map = {
            "tiny": 1,
            "small": 1,
            "medium": 1,
            "large": 2,
            "huge": 3,
            "gargantuan": 4
        }
        return size_map.get(size.lower(), 1)
    
    def get_adjacent_enemies(
        self,
        battlefield: BattlefieldSchema,
        combatant: CombatantSchema,
        all_combatants: List[CombatantSchema]
    ) -> List[CombatantSchema]:
        """Get all enemy combatants adjacent to this combatant."""
        
        if not combatant.position:
            return []
        
        adjacent_enemies = []
        adjacent_positions = combatant.position.adjacent_positions()
        
        for other_combatant in all_combatants:
            if (other_combatant.id != combatant.id and 
                other_combatant.position and
                other_combatant.is_alive() and
                other_combatant.creature_type != combatant.creature_type):
                
                # Check if enemy is in adjacent position
                if other_combatant.position in adjacent_positions:
                    adjacent_enemies.append(other_combatant)
        
        return adjacent_enemies
    
    def calculate_area_of_effect_positions(
        self,
        battlefield: BattlefieldSchema,
        aoe: AreaOfEffect
    ) -> List[Position]:
        """Calculate which positions are affected by an area of effect."""
        
        positions = []
        
        if aoe.shape == AOEShape.SPHERE:
            # Circle/sphere centered on origin
            radius_squares = aoe.size // battlefield.square_size_feet
            for y in range(battlefield.height):
                for x in range(battlefield.width):
                    pos = Position(x=x, y=y)
                    distance = aoe.origin.distance_to(pos)
                    if distance <= radius_squares:
                        positions.append(pos)
        
        elif aoe.shape == AOEShape.CUBE:
            # Square/cube centered on origin  
            half_size = (aoe.size // battlefield.square_size_feet) // 2
            for y in range(max(0, aoe.origin.y - half_size),
                          min(battlefield.height, aoe.origin.y + half_size + 1)):
                for x in range(max(0, aoe.origin.x - half_size),
                              min(battlefield.width, aoe.origin.x + half_size + 1)):
                    positions.append(Position(x=x, y=y))
        
        elif aoe.shape == AOEShape.LINE:
            # Line from origin to target
            if aoe.target_position:
                line_positions = self._get_line_positions(aoe.origin, aoe.target_position)
                width_squares = (aoe.width or battlefield.square_size_feet) // battlefield.square_size_feet
                
                if width_squares > 1:
                    # Expand line to include width
                    for pos in line_positions:
                        for dy in range(-width_squares//2, width_squares//2 + 1):
                            new_pos = Position(x=pos.x, y=pos.y + dy)
                            if battlefield.is_valid_position(new_pos):
                                positions.append(new_pos)
                else:
                    positions = line_positions
        
        elif aoe.shape == AOEShape.CONE:
            # Cone from origin in specified direction
            radius_squares = aoe.size // battlefield.square_size_feet
            direction_rad = (aoe.direction or 0) * 3.14159 / 180
            cone_angle = 90  # degrees, typical cone
            
            for y in range(max(0, aoe.origin.y - radius_squares),
                          min(battlefield.height, aoe.origin.y + radius_squares + 1)):
                for x in range(max(0, aoe.origin.x - radius_squares),
                              min(battlefield.width, aoe.origin.x + radius_squares + 1)):
                    pos = Position(x=x, y=y)
                    distance = aoe.origin.distance_to(pos)
                    
                    if distance <= radius_squares:
                        # Calculate angle from origin to position
                        angle_to_pos = math.atan2(pos.y - aoe.origin.y, pos.x - aoe.origin.x)
                        angle_diff = abs(angle_to_pos - direction_rad)
                        
                        # Normalize angle difference to 0-180 degrees
                        if angle_diff > math.pi:
                            angle_diff = 2 * math.pi - angle_diff
                        
                        if angle_diff <= (cone_angle * math.pi / 360):  # Half cone angle
                            positions.append(pos)
        
        aoe.affected_positions = positions
        return positions
    
    def check_environmental_hazards(
        self,
        battlefield: BattlefieldSchema,
        position: Position,
        trigger_type: str = "entry"
    ) -> List[str]:
        """Check for environmental hazards at a position."""
        
        triggered_hazards = []
        
        for hazard in battlefield.hazards:
            if (hazard.active and 
                position in hazard.affected_positions and
                trigger_type in hazard.triggers_on):
                
                triggered_hazards.append(hazard.id)
        
        return triggered_hazards
    
    def calculate_visibility_map(
        self,
        battlefield: BattlefieldSchema,
        observer: CombatantSchema
    ) -> Dict[Position, bool]:
        """Calculate which positions are visible to observer."""
        
        visibility_map = {}
        
        if not observer.position:
            return visibility_map
        
        # Check visibility to each position on the battlefield
        for y in range(battlefield.height):
            for x in range(battlefield.width):
                target_pos = Position(x=x, y=y)
                
                # Calculate line of sight
                los = self.calculate_line_of_sight(battlefield, observer.position, target_pos)
                
                # Position is visible if there's clear line of sight and adequate lighting
                visibility_map[target_pos] = los.clear and not los.blocked_by_darkness
        
        return visibility_map