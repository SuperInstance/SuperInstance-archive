"""
Main FastAPI service for DMLog Battle combat simulation.
"""

from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional, Dict
import logging
import uvicorn

from .config import Config
from .models.combat import (
    CombatEncounter, CombatEncounterRequest, CombatActionRequest,
    CombatResponse, CombatResolutionOptions
)
from .models.combatant import CombatantCreationRequest, CombatantResponse
from .models.battlefield import BattlefieldGenerationRequest, BattlefieldResponse
from .services.combat_service import CombatService
from .services.grid_service import GridService
from .services.visualization_service import VisualizationService
from .services.spell_effect_service import SpellEffectService
from .services.environment_service import EnvironmentService
from .services.mounted_combat_service import MountedCombatService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DMLog Battle Service",
    description="Combat simulation service for D&D 5e tactical combat",
    version="1.0.0"
)

# Global configuration
config = Config()

# Initialize services
combat_service = CombatService(config)
grid_service = GridService(config)
visualization_service = VisualizationService(config)
spell_effect_service = SpellEffectService(config)
environment_service = EnvironmentService(config)
mounted_combat_service = MountedCombatService(config)

# In-memory storage for demo purposes
# In production, this would be replaced with a proper database
encounters: Dict[str, CombatEncounter] = {}

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "DMLog Battle Service",
        "version": "1.0.0",
        "description": "Combat simulation service for D&D 5e tactical combat",
        "features": [
            "Tactical grid system for miniature placement",
            "Line of sight and cover calculations", 
            "Area of effect spell/ability visualization",
            "Automated combat resolution",
            "Environmental hazards and interactive terrain",
            "Mounted combat rules",
            "Mass combat system for large battles",
            "Combat replay system",
            "Damage type resistance/vulnerability tracker",
            "Critical hit and fumble tables",
            "Death saving throws and revival mechanics",
            "Combat analysis for balance testing"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

# Combat Encounter Endpoints

@app.post("/encounters", response_model=CombatResponse)
async def create_encounter(request: CombatEncounterRequest):
    """Create a new combat encounter."""
    try:
        encounter = combat_service.create_encounter(
            name=request.name,
            description=request.description,
            battlefield_size=request.battlefield_size,
            player_characters=request.player_characters,
            monsters=request.monsters,
            npcs=request.npcs,
            encounter_level=request.encounter_level,
            difficulty=request.difficulty
        )
        
        encounters[encounter.id] = encounter
        
        return CombatResponse(
            success=True,
            message="Combat encounter created successfully",
            encounter=encounter
        )
    
    except Exception as e:
        logger.error(f"Error creating encounter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/encounters/{encounter_id}", response_model=CombatResponse)
async def get_encounter(encounter_id: str):
    """Get a combat encounter by ID."""
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    return CombatResponse(
        success=True,
        message="Encounter retrieved successfully",
        encounter=encounters[encounter_id]
    )

@app.post("/encounters/{encounter_id}/start", response_model=CombatResponse)
async def start_combat(encounter_id: str):
    """Start combat for an encounter."""
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    try:
        encounter = encounters[encounter_id]
        combat_service.start_combat(encounter)
        
        return CombatResponse(
            success=True,
            message="Combat started successfully",
            encounter=encounter,
            current_combatant_id=encounter.get_active_combatant().id if encounter.get_active_combatant() else None
        )
    
    except Exception as e:
        logger.error(f"Error starting combat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/encounters/{encounter_id}/actions", response_model=CombatResponse)
async def perform_action(encounter_id: str, request: CombatActionRequest):
    """Perform a combat action."""
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    try:
        encounter = encounters[encounter_id]
        
        from .models.combat import CombatAction
        from .models.base import ActionType
        
        action = CombatAction(
            combatant_id=request.combatant_id,
            action_type=ActionType(request.action_type),
            action_name=request.action_name,
            target_ids=request.target_ids,
            target_positions=request.target_positions,
            round_number=encounter.current_round,
            turn_number=encounter.current_turn
        )
        
        resolved_action = combat_service.resolve_action(encounter, action)
        encounter.action_history.append(resolved_action)
        
        return CombatResponse(
            success=True,
            message="Action performed successfully",
            encounter=encounter,
            action_results=[resolved_action],
            current_combatant_id=encounter.get_active_combatant().id if encounter.get_active_combatant() else None,
            combat_over=encounter.is_combat_over(),
            victor=encounter.victor
        )
    
    except Exception as e:
        logger.error(f"Error performing action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/encounters/{encounter_id}/auto-resolve", response_model=CombatResponse)
async def auto_resolve_combat(
    encounter_id: str,
    options: Optional[CombatResolutionOptions] = None
):
    """Automatically resolve combat using AI."""
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    try:
        encounter = encounters[encounter_id]
        
        if not options:
            options = CombatResolutionOptions()
        
        completed_encounter = combat_service.run_automated_combat(encounter, options)
        
        return CombatResponse(
            success=True,
            message="Combat auto-resolved successfully",
            encounter=completed_encounter,
            combat_over=True,
            victor=completed_encounter.victor
        )
    
    except Exception as e:
        logger.error(f"Error auto-resolving combat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Grid and Positioning Endpoints

@app.get("/encounters/{encounter_id}/line-of-sight")
async def calculate_line_of_sight(
    encounter_id: str,
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
    observer_id: Optional[str] = None
):
    """Calculate line of sight between two positions."""
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    try:
        encounter = encounters[encounter_id]
        from .models.base import Position
        
        from_pos = Position(x=from_x, y=from_y)
        to_pos = Position(x=to_x, y=to_y)
        
        observer = None
        if observer_id:
            observer = encounter.get_combatant_by_id(observer_id)
        
        los = grid_service.calculate_line_of_sight(
            encounter.battlefield, from_pos, to_pos, observer
        )
        
        return {
            "from_position": {"x": from_x, "y": from_y},
            "to_position": {"x": to_x, "y": to_y},
            "has_line_of_sight": los.has_line_of_sight,
            "clear": los.clear,
            "cover_type": los.cover_type.value if los.cover_type else None,
            "blocked_by_terrain": los.blocked_by_terrain,
            "blocked_by_creatures": los.blocked_by_creatures,
            "blocked_by_darkness": los.blocked_by_darkness,
            "light_penalty": los.light_penalty,
            "blocking_positions": [{"x": p.x, "y": p.y} for p in los.blocking_positions]
        }
    
    except Exception as e:
        logger.error(f"Error calculating line of sight: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/encounters/{encounter_id}/movement-path")
async def calculate_movement_path(
    encounter_id: str,
    combatant_id: str,
    target_x: int,
    target_y: int,
    use_dash: bool = False
):
    """Calculate movement path for a combatant."""
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    try:
        encounter = encounters[encounter_id]
        combatant = encounter.get_combatant_by_id(combatant_id)
        
        if not combatant:
            raise HTTPException(status_code=404, detail="Combatant not found")
        
        from .models.base import Position
        target_pos = Position(x=target_x, y=target_y)
        
        path_result = grid_service.calculate_movement_path(
            encounter.battlefield, combatant, target_pos, use_dash
        )
        
        return {
            "combatant_id": combatant_id,
            "path": [{"x": p.x, "y": p.y} for p in path_result.waypoints],
            "total_cost": path_result.total_cost,
            "is_valid": path_result.is_valid,
            "uses_dash": path_result.uses_dash,
            "provokes_opportunity_attacks": path_result.provokes_opportunity_attacks,
            "opportunity_attack_positions": [
                {"x": p.x, "y": p.y} for p in path_result.opportunity_attack_positions
            ]
        }
    
    except Exception as e:
        logger.error(f"Error calculating movement path: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Visualization Endpoints

@app.get("/encounters/{encounter_id}/visualization")
async def get_battlefield_visualization(
    encounter_id: str,
    format: str = "json",
    observer_id: Optional[str] = None
):
    """Get battlefield visualization."""
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    try:
        encounter = encounters[encounter_id]
        
        observer = None
        if observer_id:
            observer = encounter.get_combatant_by_id(observer_id)
        
        viz = visualization_service.create_battlefield_visualization(
            encounter, observer, show_all=True
        )
        
        if format.lower() == "ascii":
            return {
                "format": "ascii",
                "visualization": visualization_service.render_to_ascii(viz)
            }
        else:
            return {
                "format": "json",
                "visualization": visualization_service.render_to_json(viz)
            }
    
    except Exception as e:
        logger.error(f"Error creating visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Spell Effect Endpoints

@app.post("/encounters/{encounter_id}/preview-spell")
async def preview_spell_effect(
    encounter_id: str,
    spell_name: str,
    caster_id: str,
    origin_x: int,
    origin_y: int,
    target_x: Optional[int] = None,
    target_y: Optional[int] = None,
    spell_level: Optional[int] = None
):
    """Preview spell effects before casting."""
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    try:
        encounter = encounters[encounter_id]
        caster = encounter.get_combatant_by_id(caster_id)
        
        if not caster:
            raise HTTPException(status_code=404, detail="Caster not found")
        
        from .models.base import Position
        origin = Position(x=origin_x, y=origin_y)
        target = Position(x=target_x, y=target_y) if target_x is not None and target_y is not None else None
        
        preview = spell_effect_service.preview_spell_effect(
            encounter, spell_name, caster, origin, target, spell_level
        )
        
        return preview
    
    except Exception as e:
        logger.error(f"Error previewing spell: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.SERVICE_PORT,
        reload=True,
        log_level="info"
    )