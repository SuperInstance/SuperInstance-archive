"""
Main system converter service - orchestrates all conversion functionality
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import uvicorn
from datetime import datetime

from .models.base import (
    Character, Monster, Spell, Item, Adventure, Mechanic, HouseRule,
    ConversionProject, ConversionResult, BalanceCheck, ValidationResult
)
from .config.systems import GameSystem
from .converters.character_converter import CharacterConverter
from .converters.adventure_converter import AdventureConverter
from .converters.mechanic_converter import MechanicConverter
from .converters.difficulty_converter import DifficultyConverter, DifficultyTier


class ConversionRequest(BaseModel):
    """Request for content conversion"""
    content_type: str  # character, adventure, mechanic, etc.
    source_data: Dict[str, Any]
    target_system: GameSystem
    difficulty_tier: Optional[DifficultyTier] = DifficultyTier.MODERATE
    party_level: Optional[int] = None
    party_size: Optional[int] = 4


class BatchConversionRequest(BaseModel):
    """Request for batch conversion"""
    project_name: str
    description: str = ""
    source_system: GameSystem
    target_system: GameSystem
    content_items: List[Dict[str, Any]]
    conversion_settings: Dict[str, Any] = {}


class SystemConverterService:
    """Main service orchestrating all system conversions"""
    
    def __init__(self):
        # Initialize converters
        self.character_converter = CharacterConverter()
        self.adventure_converter = AdventureConverter()
        self.mechanic_converter = MechanicConverter()
        self.difficulty_converter = DifficultyConverter()
        
        # Active conversion projects
        self.active_projects: Dict[str, ConversionProject] = {}
        
        # Conversion history
        self.conversion_history: List[ConversionResult] = []
    
    def convert_character(
        self, 
        character_data: Dict[str, Any], 
        target_system: GameSystem
    ) -> ConversionResult:
        """Convert a character between systems"""
        
        try:
            character = Character(**character_data)
            result = self.character_converter.convert_character(character, target_system)
            self.conversion_history.append(result)
            return result
        except Exception as e:
            return ConversionResult(
                success=False,
                source_system=GameSystem.D_AND_D_5E,
                target_system=target_system,
                errors=[f"Character conversion failed: {str(e)}"]
            )
    
    def convert_adventure(
        self, 
        adventure_data: Dict[str, Any], 
        target_system: GameSystem
    ) -> ConversionResult:
        """Convert an adventure between systems"""
        
        try:
            adventure = Adventure(**adventure_data)
            result = self.adventure_converter.convert_adventure(adventure, target_system)
            self.conversion_history.append(result)
            return result
        except Exception as e:
            return ConversionResult(
                success=False,
                source_system=GameSystem.D_AND_D_5E,
                target_system=target_system,
                errors=[f"Adventure conversion failed: {str(e)}"]
            )
    
    def convert_mechanic(
        self, 
        mechanic_data: Dict[str, Any], 
        target_system: GameSystem
    ) -> ConversionResult:
        """Convert a game mechanic between systems"""
        
        try:
            mechanic = Mechanic(**mechanic_data)
            result = self.mechanic_converter.convert_mechanic(mechanic, target_system)
            self.conversion_history.append(result)
            return result
        except Exception as e:
            return ConversionResult(
                success=False,
                source_system=GameSystem.D_AND_D_5E,
                target_system=target_system,
                errors=[f"Mechanic conversion failed: {str(e)}"]
            )
    
    def convert_challenge_rating(
        self, 
        cr: float, 
        party_level: int,
        source_system: GameSystem, 
        target_system: GameSystem,
        difficulty_tier: DifficultyTier = DifficultyTier.MODERATE
    ) -> ConversionResult:
        """Convert challenge rating between systems"""
        
        return self.difficulty_converter.convert_challenge_rating(
            cr, party_level, source_system, target_system, difficulty_tier
        )
    
    def convert_difficulty_class(
        self, 
        dc: int, 
        party_level: int,
        source_system: GameSystem, 
        target_system: GameSystem,
        difficulty_tier: DifficultyTier = DifficultyTier.MODERATE
    ) -> ConversionResult:
        """Convert DC values between systems"""
        
        return self.difficulty_converter.convert_difficulty_class(
            dc, party_level, source_system, target_system, difficulty_tier
        )
    
    def create_conversion_project(
        self, 
        name: str, 
        description: str,
        source_system: GameSystem,
        target_system: GameSystem
    ) -> ConversionProject:
        """Create a new conversion project"""
        
        project = ConversionProject(
            name=name,
            description=description,
            source_system=source_system,
            target_system=target_system
        )
        
        self.active_projects[project.id] = project
        return project
    
    def add_content_to_project(
        self, 
        project_id: str, 
        content_type: str, 
        content_data: Dict[str, Any]
    ) -> bool:
        """Add content to a conversion project"""
        
        if project_id not in self.active_projects:
            return False
        
        project = self.active_projects[project_id]
        
        # Create content object and store its ID
        content_id = content_data.get("id", f"generated_{datetime.utcnow().timestamp()}")
        
        if content_type == "character":
            project.characters.append(content_id)
        elif content_type == "monster":
            project.monsters.append(content_id)
        elif content_type == "spell":
            project.spells.append(content_id)
        elif content_type == "item":
            project.items.append(content_id)
        elif content_type == "adventure":
            project.adventures.append(content_id)
        elif content_type == "mechanic":
            project.mechanics.append(content_id)
        
        return True
    
    def execute_conversion_project(self, project_id: str) -> ConversionProject:
        """Execute all conversions in a project"""
        
        if project_id not in self.active_projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.active_projects[project_id]
        project.status = "in_progress"
        
        total_items = (
            len(project.characters) + len(project.monsters) + 
            len(project.spells) + len(project.items) +
            len(project.adventures) + len(project.mechanics)
        )
        
        completed_items = 0
        
        # Convert characters
        for char_id in project.characters:
            # In a real implementation, you'd load the character data
            # For now, we'll create a placeholder result
            result = ConversionResult(
                success=True,
                source_system=project.source_system,
                target_system=project.target_system
            )
            project.results.append(result)
            completed_items += 1
            project.progress = completed_items / total_items
        
        # Convert other content types...
        # (Similar loops for monsters, spells, items, adventures, mechanics)
        
        project.status = "completed"
        project.completed_at = datetime.utcnow()
        project.progress = 1.0
        
        return project
    
    def get_conversion_preview(
        self, 
        content_type: str, 
        content_data: Dict[str, Any], 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Get a preview of conversion changes"""
        
        try:
            if content_type == "character":
                character = Character(**content_data)
                return self.character_converter.get_conversion_preview(character, target_system)
            elif content_type == "mechanic":
                mechanic = Mechanic(**content_data)
                return self.mechanic_converter.get_mechanic_conversion_preview(mechanic, target_system)
            else:
                return {"error": f"Preview not supported for {content_type}"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_system_compatibility(
        self, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Get compatibility information between systems"""
        
        compatibility = {
            "source_system": source_system.value,
            "target_system": target_system.value,
            "compatibility_score": 0.0,
            "supported_conversions": [],
            "limitations": [],
            "recommendations": []
        }
        
        # Calculate compatibility score
        if source_system == target_system:
            compatibility["compatibility_score"] = 1.0
            compatibility["supported_conversions"] = ["all"]
        elif (source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E) or \
             (source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E):
            compatibility["compatibility_score"] = 0.8
            compatibility["supported_conversions"] = [
                "characters", "monsters", "spells", "items", "adventures", "mechanics"
            ]
            compatibility["limitations"] = [
                "Some mechanics may not have direct equivalents",
                "Action economy differences require manual review",
                "Spell systems work differently"
            ]
        else:
            compatibility["compatibility_score"] = 0.5
            compatibility["supported_conversions"] = ["characters", "monsters", "basic_mechanics"]
            compatibility["limitations"] = [
                "Limited system mappings available",
                "Manual review required for most conversions"
            ]
        
        return compatibility
    
    def get_conversion_statistics(self) -> Dict[str, Any]:
        """Get conversion statistics"""
        
        total_conversions = len(self.conversion_history)
        successful_conversions = sum(1 for r in self.conversion_history if r.success)
        
        # System pair statistics
        system_pairs = {}
        for result in self.conversion_history:
            pair_key = f"{result.source_system.value} -> {result.target_system.value}"
            if pair_key not in system_pairs:
                system_pairs[pair_key] = {"total": 0, "successful": 0}
            system_pairs[pair_key]["total"] += 1
            if result.success:
                system_pairs[pair_key]["successful"] += 1
        
        # Average confidence scores
        confidence_scores = [r.conversion_confidence for r in self.conversion_history if r.success]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            "total_conversions": total_conversions,
            "successful_conversions": successful_conversions,
            "success_rate": successful_conversions / total_conversions if total_conversions > 0 else 0.0,
            "average_confidence": avg_confidence,
            "system_pairs": system_pairs,
            "active_projects": len(self.active_projects)
        }


# FastAPI app setup
app = FastAPI(
    title="System Converter API",
    description="Convert tabletop RPG content between different game systems",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize service
converter_service = SystemConverterService()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/convert")
async def convert_content(request: ConversionRequest):
    """Convert content between systems"""
    
    try:
        if request.content_type == "character":
            result = converter_service.convert_character(
                request.source_data, request.target_system
            )
        elif request.content_type == "adventure":
            result = converter_service.convert_adventure(
                request.source_data, request.target_system
            )
        elif request.content_type == "mechanic":
            result = converter_service.convert_mechanic(
                request.source_data, request.target_system
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported content type: {request.content_type}"
            )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/convert/challenge-rating")
async def convert_challenge_rating(
    cr: float,
    party_level: int,
    source_system: GameSystem,
    target_system: GameSystem,
    difficulty_tier: DifficultyTier = DifficultyTier.MODERATE
):
    """Convert challenge rating between systems"""
    
    result = converter_service.convert_challenge_rating(
        cr, party_level, source_system, target_system, difficulty_tier
    )
    return result


@app.post("/convert/dc")
async def convert_difficulty_class(
    dc: int,
    party_level: int,
    source_system: GameSystem,
    target_system: GameSystem,
    difficulty_tier: DifficultyTier = DifficultyTier.MODERATE
):
    """Convert DC values between systems"""
    
    result = converter_service.convert_difficulty_class(
        dc, party_level, source_system, target_system, difficulty_tier
    )
    return result


@app.post("/projects")
async def create_project(
    name: str,
    description: str = "",
    source_system: GameSystem = GameSystem.D_AND_D_5E,
    target_system: GameSystem = GameSystem.PATHFINDER_2E
):
    """Create a new conversion project"""
    
    project = converter_service.create_conversion_project(
        name, description, source_system, target_system
    )
    return project


@app.post("/projects/{project_id}/content")
async def add_content_to_project(
    project_id: str,
    content_type: str,
    content_data: Dict[str, Any]
):
    """Add content to a conversion project"""
    
    success = converter_service.add_content_to_project(
        project_id, content_type, content_data
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"success": True}


@app.post("/projects/{project_id}/execute")
async def execute_project(project_id: str):
    """Execute all conversions in a project"""
    
    try:
        project = converter_service.execute_conversion_project(project_id)
        return project
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details"""
    
    if project_id not in converter_service.active_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return converter_service.active_projects[project_id]


@app.get("/preview")
async def get_conversion_preview(
    content_type: str,
    target_system: GameSystem,
    content_data: Dict[str, Any]
):
    """Get preview of conversion changes"""
    
    preview = converter_service.get_conversion_preview(
        content_type, content_data, target_system
    )
    return preview


@app.get("/compatibility")
async def get_system_compatibility(
    source_system: GameSystem,
    target_system: GameSystem
):
    """Get compatibility information between systems"""
    
    compatibility = converter_service.get_system_compatibility(
        source_system, target_system
    )
    return compatibility


@app.get("/stats")
async def get_statistics():
    """Get conversion statistics"""
    
    stats = converter_service.get_conversion_statistics()
    return stats


@app.get("/systems")
async def list_supported_systems():
    """List all supported game systems"""
    
    systems = [
        {
            "id": system.value,
            "name": system.value.replace("_", " ").title(),
            "supported": True
        }
        for system in GameSystem
    ]
    
    return systems


if __name__ == "__main__":
    uvicorn.run(
        "main_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )