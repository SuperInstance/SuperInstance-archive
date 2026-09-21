"""
D&D Template System Main Service

Main orchestrator that provides unified access to all template generators
including adventures, characters, encounters, mysteries, political intrigue,
and horror elements.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .models.base import GenerationRequest, ComplexityLevel, ThemeType, DifficultyLevel
from .models.adventure import Adventure, OneShot
from .models.character import Backstory, NPCProfile
from .models.encounter import (
    Encounter, CombatEncounter, SocialEncounter, Puzzle, Trap,
    ChaseScene, HeistPlan, SkillChallenge
)
from .generators.horror_generator import HorrorScenario, HorrorElement
from .models.mystery import Mystery, Investigation
from .models.political import PoliticalIntrigue, Faction, Plot

from .generators.adventure_generator import AdventureGenerator
from .generators.character_generator import CharacterGenerator
from .generators.plot_generator import PlotTwistGenerator
from .generators.puzzle_generator import PuzzleGenerator
from .generators.trap_generator import TrapGenerator
from .generators.social_generator import SocialEncounterGenerator
from .generators.chase_generator import ChaseGenerator
from .generators.heist_generator import HeistGenerator
from .generators.mystery_generator import MysteryGenerator
from .generators.political_generator import PoliticalGenerator
from .generators.horror_generator import HorrorGenerator

from .config import BASE_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TemplateService:
    """Main template service orchestrator"""
    
    def __init__(self):
        # Initialize all generators
        self.adventure_generator = AdventureGenerator()
        self.character_generator = CharacterGenerator()
        self.plot_generator = PlotTwistGenerator()
        self.puzzle_generator = PuzzleGenerator()
        self.trap_generator = TrapGenerator()
        self.social_generator = SocialEncounterGenerator()
        self.chase_generator = ChaseGenerator()
        self.heist_generator = HeistGenerator()
        self.mystery_generator = MysteryGenerator()
        self.political_generator = PoliticalGenerator()
        self.horror_generator = HorrorGenerator()
        
        # Template cache for common requests
        self.template_cache = {}
        self.generation_stats = {
            "adventures": 0,
            "characters": 0,
            "encounters": 0,
            "mysteries": 0,
            "plots": 0,
            "total_generated": 0
        }
        
        logger.info("Template Service initialized with all generators")
    
    async def generate_adventure(self, request: GenerationRequest) -> Adventure:
        """Generate a complete adventure"""
        try:
            level = request.party_level or 1
            complexity = request.complexity or ComplexityLevel.MODERATE
            theme = request.theme or ThemeType.HEROIC_FANTASY
            party_size = request.party_size or 4
            
            # Use custom seed if provided
            if request.seed:
                self.adventure_generator.set_seed(request.seed)
            
            adventure = await self.adventure_generator.generate_adventure(
                level=level,
                complexity=complexity,
                theme=theme,
                party_size=party_size
            )
            
            self.generation_stats["adventures"] += 1
            self.generation_stats["total_generated"] += 1
            
            logger.info(f"Generated adventure: {adventure.name} for level {level}")
            return adventure
            
        except Exception as e:
            logger.error(f"Error generating adventure: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_oneshot(self, request: GenerationRequest) -> OneShot:
        """Generate a one-shot adventure"""
        try:
            level = request.party_level or 1
            theme = request.theme or ThemeType.HEROIC_FANTASY
            session_hours = request.custom_options.get("session_hours", 4)
            
            if request.seed:
                self.adventure_generator.set_seed(request.seed)
            
            oneshot = await self.adventure_generator.generate_oneshot(
                level=level,
                session_hours=session_hours,
                theme=theme
            )
            
            self.generation_stats["adventures"] += 1
            self.generation_stats["total_generated"] += 1
            
            logger.info(f"Generated one-shot: {oneshot.name}")
            return oneshot
            
        except Exception as e:
            logger.error(f"Error generating one-shot: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_character_backstory(self, request: GenerationRequest) -> Backstory:
        """Generate character backstory"""
        try:
            character_name = request.custom_options.get("character_name", "")
            character_class = request.custom_options.get("character_class", "")
            character_race = request.custom_options.get("character_race", "")
            level = request.party_level or 1
            
            if request.seed:
                self.character_generator.set_seed(request.seed)
            
            backstory = await self.character_generator.generate_backstory(
                character_name=character_name,
                character_class=character_class,
                character_race=character_race,
                level=level
            )
            
            self.generation_stats["characters"] += 1
            self.generation_stats["total_generated"] += 1
            
            logger.info(f"Generated backstory for: {backstory.character_name}")
            return backstory
            
        except Exception as e:
            logger.error(f"Error generating backstory: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_npc(self, request: GenerationRequest) -> NPCProfile:
        """Generate NPC profile"""
        try:
            role = request.custom_options.get("role", "neutral")
            importance = request.custom_options.get("importance", "minor")
            
            if request.seed:
                self.character_generator.set_seed(request.seed)
            
            npc = await self.character_generator.generate_npc(role=role, importance=importance)
            
            self.generation_stats["characters"] += 1
            self.generation_stats["total_generated"] += 1
            
            logger.info(f"Generated NPC: {npc.name}")
            return npc
            
        except Exception as e:
            logger.error(f"Error generating NPC: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_puzzle(self, request: GenerationRequest) -> Puzzle:
        """Generate puzzle encounter"""
        try:
            puzzle_type = request.custom_options.get("puzzle_type", "riddle")
            complexity = str(request.complexity or ComplexityLevel.MODERATE).lower()
            theme = request.custom_options.get("theme", "dungeon")
            party_level = request.party_level or 5
            
            if request.seed:
                self.puzzle_generator.set_seed(request.seed)
            
            puzzle = await self.puzzle_generator.generate_puzzle(
                puzzle_type=puzzle_type,
                complexity=complexity,
                theme=theme,
                party_level=party_level
            )
            
            self.generation_stats["encounters"] += 1
            self.generation_stats["total_generated"] += 1
            
            logger.info(f"Generated puzzle: {puzzle.name}")
            return puzzle
            
        except Exception as e:
            logger.error(f"Error generating puzzle: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_trap(self, request: GenerationRequest) -> Trap:
        """Generate trap encounter"""
        try:
            trap_type = request.custom_options.get("trap_type")
            complexity = str(request.complexity or ComplexityLevel.MODERATE).lower()
            party_level = request.party_level or 5
            theme = request.custom_options.get("location_theme", "dungeon")
            
            if request.seed:
                self.trap_generator.set_seed(request.seed)
            
            trap = await self.trap_generator.generate_trap(
                trap_type=trap_type,
                party_level=party_level,
                complexity=complexity,
                location_theme=theme
            )
            
            self.generation_stats["encounters"] += 1
            self.generation_stats["total_generated"] += 1
            
            logger.info(f"Generated trap: {trap.name}")
            return trap
            
        except Exception as e:
            logger.error(f"Error generating trap: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_social_encounter(self, request: GenerationRequest) -> SocialEncounter:
        """Generate social encounter"""
        try:
            encounter_type = request.custom_options.get("encounter_type", "negotiation")
            complexity = str(request.complexity or ComplexityLevel.MODERATE).lower()
            party_level = request.party_level or 5
            num_npcs = request.custom_options.get("num_npcs", 1)
            
            if request.seed:
                self.social_generator.set_seed(request.seed)
            
            encounter = await self.social_generator.generate_social_encounter(
                encounter_type=encounter_type,
                complexity=complexity,
                party_level=party_level,
                num_npcs=num_npcs
            )
            
            self.generation_stats["encounters"] += 1
            self.generation_stats["total_generated"] += 1
            
            logger.info(f"Generated social encounter: {encounter.name}")
            return encounter
            
        except Exception as e:
            logger.error(f"Error generating social encounter: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_plot_twist(self, request: GenerationRequest):
        """Generate plot twist"""
        try:
            category = request.custom_options.get("category")
            impact_level = request.custom_options.get("impact_level", "moderate")
            context = request.custom_options.get("context", {})
            
            if request.seed:
                self.plot_generator.set_seed(request.seed)
            
            twist = await self.plot_generator.generate_plot_twist(
                category=category,
                impact_level=impact_level,
                context=context
            )
            
            self.generation_stats["plots"] += 1
            self.generation_stats["total_generated"] += 1
            
            logger.info(f"Generated plot twist: {twist.name}")
            return twist
            
        except Exception as e:
            logger.error(f"Error generating plot twist: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_campaign_adventures(self, request: GenerationRequest) -> List[Adventure]:
        """Generate series of adventures for a campaign"""
        try:
            start_level = request.custom_options.get("start_level", 1)
            end_level = request.custom_options.get("end_level", 10)
            theme = request.theme or ThemeType.HEROIC_FANTASY
            
            if request.seed:
                self.adventure_generator.set_seed(request.seed)
            
            adventures = await self.adventure_generator.generate_campaign_adventures(
                start_level=start_level,
                end_level=end_level,
                theme=theme
            )
            
            self.generation_stats["adventures"] += len(adventures)
            self.generation_stats["total_generated"] += len(adventures)
            
            logger.info(f"Generated {len(adventures)} campaign adventures")
            return adventures
            
        except Exception as e:
            logger.error(f"Error generating campaign adventures: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_encounter_sequence(self, request: GenerationRequest) -> List[Any]:
        """Generate a sequence of related encounters"""
        try:
            sequence_type = request.custom_options.get("sequence_type", "mixed")
            num_encounters = request.custom_options.get("num_encounters", 3)
            party_level = request.party_level or 5
            theme = request.theme or ThemeType.HEROIC_FANTASY
            
            encounters = []
            
            if sequence_type == "puzzle_sequence":
                complexity = str(request.complexity or ComplexityLevel.MODERATE).lower()
                puzzles = await self.puzzle_generator.generate_puzzle_room(
                    complexity=complexity,
                    theme=str(theme).lower(),
                    party_level=party_level,
                    num_puzzles=num_encounters
                )
                encounters.extend(puzzles)
            
            elif sequence_type == "trap_sequence":
                complexity = str(request.complexity or ComplexityLevel.MODERATE).lower()
                traps = await self.trap_generator.generate_trap_sequence(
                    party_level=party_level,
                    num_traps=num_encounters,
                    escalating=True
                )
                encounters.extend(traps)
            
            else:  # mixed sequence
                # Generate variety of encounters
                encounter_types = ["social", "puzzle", "trap"]
                for i in range(num_encounters):
                    enc_type = encounter_types[i % len(encounter_types)]
                    
                    if enc_type == "social":
                        encounter = await self.generate_social_encounter(request)
                    elif enc_type == "puzzle":
                        encounter = await self.generate_puzzle(request)
                    else:  # trap
                        encounter = await self.generate_trap(request)
                    
                    encounters.append(encounter)
            
            self.generation_stats["encounters"] += len(encounters)
            self.generation_stats["total_generated"] += len(encounters)
            
            logger.info(f"Generated {len(encounters)} encounter sequence")
            return encounters
            
        except Exception as e:
            logger.error(f"Error generating encounter sequence: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_template_suggestions(self, template_type: str, 
                                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get suggestions for template parameters"""
        try:
            suggestions = {
                "template_type": template_type,
                "suggested_parameters": {},
                "common_options": {},
                "examples": []
            }
            
            if template_type == "adventure":
                suggestions["suggested_parameters"] = {
                    "party_level": "1-20",
                    "complexity": ["simple", "moderate", "complex", "epic"],
                    "theme": ["heroic_fantasy", "dark_fantasy", "horror", "mystery", "political"],
                    "party_size": "1-8"
                }
                suggestions["common_options"] = {
                    "session_length": "Single session or multi-session",
                    "environments": "Urban, wilderness, dungeon, planar",
                    "tone": "Heroic, gritty, comedic, dramatic"
                }
                suggestions["examples"] = [
                    {"name": "Village Goblin Problem", "level": 1, "theme": "heroic_fantasy"},
                    {"name": "Political Conspiracy", "level": 8, "theme": "political"},
                    {"name": "Planar Investigation", "level": 15, "theme": "mystery"}
                ]
            
            elif template_type == "character":
                suggestions["suggested_parameters"] = {
                    "character_class": "Any D&D 5e class",
                    "character_race": "Any D&D 5e race",
                    "background_complexity": ["simple", "moderate", "complex"]
                }
                suggestions["common_options"] = {
                    "relationship_focus": "Family, friends, rivals, enemies",
                    "motivation_type": "Revenge, redemption, knowledge, power",
                    "background_type": "Tragic, heroic, mysterious, ordinary"
                }
            
            elif template_type == "encounter":
                suggestions["suggested_parameters"] = {
                    "encounter_type": ["combat", "social", "puzzle", "trap", "chase"],
                    "difficulty": ["easy", "medium", "hard", "deadly"],
                    "environment": "Any setting type"
                }
                suggestions["common_options"] = {
                    "objectives": "What players need to accomplish",
                    "complications": "Additional challenges or twists",
                    "rewards": "XP, treasure, story advancement"
                }
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting template suggestions: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_generation_statistics(self) -> Dict[str, Any]:
        """Get service usage statistics"""
        return {
            "generation_stats": self.generation_stats,
            "cache_stats": {
                "cached_templates": len(self.template_cache),
                "cache_hit_rate": "Not implemented"
            },
            "service_status": "operational",
            "uptime": "Not implemented",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def generate_chase_scene(self, request: GenerationRequest) -> ChaseScene:
        """Generate chase scene encounter"""
        try:
            self.generation_stats["encounters"] += 1
            
            chase = await self.chase_generator.generate_chase_scene(
                chase_type=request.parameters.get("chase_type", "foot"),
                complexity=request.parameters.get("complexity", "moderate"),
                party_level=request.parameters.get("party_level", 5),
                terrain=request.parameters.get("terrain", "urban")
            )
            
            logger.info(f"Generated chase scene: {chase.name}")
            return chase
            
        except Exception as e:
            logger.error(f"Error generating chase scene: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_heist_plan(self, request: GenerationRequest) -> HeistPlan:
        """Generate heist planning scenario"""
        try:
            self.generation_stats["encounters"] += 1
            
            heist = await self.heist_generator.generate_heist_plan(
                target_type=request.parameters.get("target_type", "bank"),
                complexity=request.parameters.get("complexity", "moderate"),
                party_level=request.parameters.get("party_level", 8),
                crew_size=request.parameters.get("crew_size", 4)
            )
            
            logger.info(f"Generated heist plan: {heist.name}")
            return heist
            
        except Exception as e:
            logger.error(f"Error generating heist plan: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_mystery(self, request: GenerationRequest) -> Mystery:
        """Generate murder mystery scenario"""
        try:
            self.generation_stats["adventures"] += 1
            
            mystery = await self.mystery_generator.generate_mystery(
                mystery_type=request.parameters.get("mystery_type", "murder"),
                complexity=request.parameters.get("complexity", "moderate"),
                party_level=request.parameters.get("party_level", 5),
                suspect_count=request.parameters.get("suspect_count", 5)
            )
            
            logger.info(f"Generated mystery: {mystery.name}")
            return mystery
            
        except Exception as e:
            logger.error(f"Error generating mystery: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_political_intrigue(self, request: GenerationRequest) -> PoliticalIntrigue:
        """Generate political intrigue scenario"""
        try:
            self.generation_stats["adventures"] += 1
            
            intrigue = await self.political_generator.generate_political_intrigue(
                scope=request.parameters.get("scope", "local"),
                complexity=request.parameters.get("complexity", "moderate"),
                party_level=request.parameters.get("party_level", 8),
                faction_count=request.parameters.get("faction_count", 4)
            )
            
            logger.info(f"Generated political intrigue: {intrigue.name}")
            return intrigue
            
        except Exception as e:
            logger.error(f"Error generating political intrigue: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_horror_scenario(self, request: GenerationRequest) -> HorrorScenario:
        """Generate horror atmosphere scenario"""
        try:
            self.generation_stats["encounters"] += 1
            
            horror = await self.horror_generator.generate_horror_scenario(
                horror_genre=request.parameters.get("horror_genre", "gothic"),
                setting=request.parameters.get("setting", "haunted_house"),
                complexity=request.parameters.get("complexity", "moderate"),
                party_level=request.parameters.get("party_level", 6),
                session_length=request.parameters.get("session_length", "standard")
            )
            
            logger.info(f"Generated horror scenario: {horror.name}")
            return horror
            
        except Exception as e:
            logger.error(f"Error generating horror scenario: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_horror_atmosphere(self, request: GenerationRequest) -> List[HorrorElement]:
        """Generate horror atmosphere elements"""
        try:
            self.generation_stats["encounters"] += 1
            
            atmosphere = await self.horror_generator.generate_horror_atmosphere(
                setting=request.parameters.get("setting", "haunted_house"),
                intensity=request.parameters.get("intensity", "moderate")
            )
            
            logger.info(f"Generated {len(atmosphere)} horror atmosphere elements")
            return atmosphere
            
        except Exception as e:
            logger.error(f"Error generating horror atmosphere: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def clear_cache(self):
        """Clear template cache"""
        self.template_cache.clear()
        logger.info("Template cache cleared")


# FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting D&D Template System Service")
    yield
    logger.info("Shutting down D&D Template System Service")


app = FastAPI(
    title="D&D Template System",
    description="Comprehensive template generation system for D&D campaigns",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize template service
template_service = TemplateService()


# API Routes
@app.post("/adventures")
async def create_adventure(request: GenerationRequest):
    """Generate a complete adventure"""
    adventure = await template_service.generate_adventure(request)
    return {"adventure": adventure.dict()}


@app.post("/oneshots")
async def create_oneshot(request: GenerationRequest):
    """Generate a one-shot adventure"""
    oneshot = await template_service.generate_oneshot(request)
    return {"oneshot": oneshot.dict()}


@app.post("/characters/backstories")
async def create_character_backstory(request: GenerationRequest):
    """Generate character backstory"""
    backstory = await template_service.generate_character_backstory(request)
    return {"backstory": backstory.dict()}


@app.post("/characters/npcs")
async def create_npc(request: GenerationRequest):
    """Generate NPC profile"""
    npc = await template_service.generate_npc(request)
    return {"npc": npc.dict()}


@app.post("/encounters/puzzles")
async def create_puzzle(request: GenerationRequest):
    """Generate puzzle encounter"""
    puzzle = await template_service.generate_puzzle(request)
    return {"puzzle": puzzle.dict()}


@app.post("/encounters/traps")
async def create_trap(request: GenerationRequest):
    """Generate trap encounter"""
    trap = await template_service.generate_trap(request)
    return {"trap": trap.dict()}


@app.post("/encounters/social")
async def create_social_encounter(request: GenerationRequest):
    """Generate social encounter"""
    encounter = await template_service.generate_social_encounter(request)
    return {"encounter": encounter.dict()}


@app.post("/plots/twists")
async def create_plot_twist(request: GenerationRequest):
    """Generate plot twist"""
    twist = await template_service.generate_plot_twist(request)
    return {"twist": twist.dict()}


@app.post("/campaigns")
async def create_campaign_adventures(request: GenerationRequest):
    """Generate series of adventures for a campaign"""
    adventures = await template_service.generate_campaign_adventures(request)
    return {"adventures": [adv.dict() for adv in adventures]}


@app.post("/encounters/sequences")
async def create_encounter_sequence(request: GenerationRequest):
    """Generate a sequence of related encounters"""
    encounters = await template_service.generate_encounter_sequence(request)
    return {"encounters": [enc.dict() for enc in encounters]}


@app.post("/encounters/chases")
async def create_chase_scene(request: GenerationRequest):
    """Generate chase scene encounter"""
    chase = await template_service.generate_chase_scene(request)
    return {"chase_scene": chase.dict()}


@app.post("/heists/plans")
async def create_heist_plan(request: GenerationRequest):
    """Generate heist planning scenario"""
    heist = await template_service.generate_heist_plan(request)
    return {"heist_plan": heist.dict()}


@app.post("/mysteries")
async def create_mystery(request: GenerationRequest):
    """Generate murder mystery scenario"""
    mystery = await template_service.generate_mystery(request)
    return {"mystery": mystery.dict()}


@app.post("/politics/intrigue")
async def create_political_intrigue(request: GenerationRequest):
    """Generate political intrigue scenario"""
    intrigue = await template_service.generate_political_intrigue(request)
    return {"political_intrigue": intrigue.dict()}


@app.post("/horror/scenarios")
async def create_horror_scenario(request: GenerationRequest):
    """Generate horror atmosphere scenario"""
    horror = await template_service.generate_horror_scenario(request)
    return {"horror_scenario": horror.dict()}


@app.post("/horror/atmosphere")
async def create_horror_atmosphere(request: GenerationRequest):
    """Generate horror atmosphere elements"""
    atmosphere = await template_service.generate_horror_atmosphere(request)
    return {"horror_elements": [elem.dict() for elem in atmosphere]}


@app.get("/templates/{template_type}/suggestions")
async def get_template_suggestions(template_type: str):
    """Get suggestions for template parameters"""
    suggestions = await template_service.get_template_suggestions(template_type)
    return suggestions


@app.get("/stats")
async def get_statistics():
    """Get service statistics"""
    stats = await template_service.get_generation_statistics()
    return stats


@app.post("/cache/clear")
async def clear_cache():
    """Clear template cache"""
    template_service.clear_cache()
    return {"message": "Cache cleared successfully"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "adventure_generator": "operational",
            "character_generator": "operational", 
            "plot_generator": "operational",
            "puzzle_generator": "operational",
            "trap_generator": "operational",
            "social_generator": "operational"
        },
        "version": "1.0.0"
    }


# Quick generation endpoints for common use cases
@app.get("/quick/adventure")
async def quick_adventure(
    level: int = Query(1, ge=1, le=20, description="Party level"),
    theme: str = Query("heroic_fantasy", description="Adventure theme"),
    complexity: str = Query("moderate", description="Adventure complexity")
):
    """Quick adventure generation with query parameters"""
    request = GenerationRequest(
        template_type="adventure",
        party_level=level,
        theme=ThemeType(theme) if theme in [t.value for t in ThemeType] else ThemeType.HEROIC_FANTASY,
        complexity=ComplexityLevel(complexity) if complexity in [c.value for c in ComplexityLevel] else ComplexityLevel.MODERATE
    )
    
    adventure = await template_service.generate_adventure(request)
    return {"adventure": adventure.dict()}


@app.get("/quick/npc")
async def quick_npc(
    role: str = Query("neutral", description="NPC role"),
    importance: str = Query("minor", description="NPC importance")
):
    """Quick NPC generation with query parameters"""
    request = GenerationRequest(
        template_type="npc",
        custom_options={"role": role, "importance": importance}
    )
    
    npc = await template_service.generate_npc(request)
    return {"npc": npc.dict()}


@app.get("/quick/puzzle")
async def quick_puzzle(
    puzzle_type: str = Query("riddle", description="Type of puzzle"),
    level: int = Query(5, ge=1, le=20, description="Party level")
):
    """Quick puzzle generation with query parameters"""
    request = GenerationRequest(
        template_type="puzzle",
        party_level=level,
        custom_options={"puzzle_type": puzzle_type}
    )
    
    puzzle = await template_service.generate_puzzle(request)
    return {"puzzle": puzzle.dict()}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_service:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )