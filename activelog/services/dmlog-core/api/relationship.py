"""
Character relationship mapping API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.relationship import (
    CharacterSchema, RelationshipSchema, RelationshipEventSchema,
    RelationshipWebSchema
)
from services.relationship_service import RelationshipService
from database import get_db

router = APIRouter()

# Dependency to get relationship service
def get_relationship_service() -> RelationshipService:
    return RelationshipService()

@router.post("/characters/", response_model=CharacterSchema)
async def create_character(
    character: CharacterSchema,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Create a new character for relationship tracking."""
    try:
        db_character = relationship_service.create_character(character, db)
        return CharacterSchema.from_orm(db_character)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/characters/{character_id}", response_model=CharacterSchema)
async def get_character(
    character_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Get a character by ID."""
    character = relationship_service.get_character(character_id, db)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return CharacterSchema.from_orm(character)

@router.get("/characters/search")
async def search_characters(
    campaign_id: str,
    search_term: str,
    limit: int = 20,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Search for characters by name or attributes."""
    try:
        characters = relationship_service.search_characters(campaign_id, search_term, db)
        return {
            "search_term": search_term,
            "campaign_id": campaign_id,
            "characters": [CharacterSchema.from_orm(char) for char in characters],
            "total_found": len(characters)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=RelationshipSchema)
async def create_relationship(
    relationship: RelationshipSchema,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Create a new relationship between characters."""
    try:
        db_relationship = relationship_service.create_relationship(relationship, db)
        return RelationshipSchema.from_orm(db_relationship)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{relationship_id}", response_model=RelationshipSchema)
async def get_relationship(
    relationship_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Get a relationship by ID."""
    relationship = relationship_service.get_relationship(relationship_id, db)
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return RelationshipSchema.from_orm(relationship)

@router.post("/{relationship_id}/events/", response_model=RelationshipEventSchema)
async def create_relationship_event(
    relationship_id: str,
    event: RelationshipEventSchema,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Create a new relationship event."""
    try:
        event.relationship_id = relationship_id
        db_event = relationship_service.create_relationship_event(event, db)
        return RelationshipEventSchema.from_orm(db_event)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{relationship_id}/history")
async def get_relationship_history(
    relationship_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Get the complete history of a relationship."""
    try:
        history = relationship_service.get_relationship_history(relationship_id, db)
        return {
            "relationship_id": relationship_id,
            "events": [RelationshipEventSchema.from_orm(event) for event in history],
            "total_events": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/campaigns/{campaign_id}/graph")
async def get_relationship_graph(
    campaign_id: str,
    include_secrets: bool = False,
    character_filter: Optional[List[str]] = None,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Get the relationship graph for a campaign."""
    try:
        graph = relationship_service.get_relationship_graph(
            campaign_id, include_secrets, character_filter, db
        )
        return {
            "campaign_id": campaign_id,
            "graph": graph,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "filters": {
                "include_secrets": include_secrets,
                "character_filter": character_filter
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/characters/{character_id}/analysis")
async def analyze_character_relationships(
    character_id: str,
    campaign_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Analyze a character's relationship patterns."""
    try:
        analysis = relationship_service.analyze_character_relationships(character_id, campaign_id, db)
        return {
            "character_id": character_id,
            "campaign_id": campaign_id,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/characters/{character_id}/suggestions")
async def get_relationship_suggestions(
    character_id: str,
    campaign_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Get relationship suggestions for a character."""
    try:
        suggestions = relationship_service.get_relationship_suggestions(character_id, campaign_id, db)
        return {
            "character_id": character_id,
            "campaign_id": campaign_id,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/characters/{character_id}/centrality")
async def calculate_character_centrality(
    character_id: str,
    campaign_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Calculate centrality measures for a character in the relationship network."""
    try:
        centrality = relationship_service.calculate_character_centrality(character_id, campaign_id, db)
        return {
            "character_id": character_id,
            "campaign_id": campaign_id,
            "centrality_measures": centrality,
            "interpretation": {
                "degree": "How many direct connections the character has",
                "closeness": "How close the character is to all others on average",
                "betweenness": "How often the character is on shortest paths between others"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/campaigns/{campaign_id}/cliques")
async def find_cliques(
    campaign_id: str,
    min_size: int = 3,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Find cliques (tight-knit groups) in the relationship network."""
    try:
        cliques = relationship_service.find_cliques(campaign_id, min_size, db)
        return {
            "campaign_id": campaign_id,
            "min_clique_size": min_size,
            "cliques": cliques,
            "total_cliques": len(cliques)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/campaigns/{campaign_id}/conflicts")
async def detect_conflicts(
    campaign_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Detect potential conflicts in relationships."""
    try:
        conflicts = relationship_service.detect_conflicts(campaign_id, db)
        return {
            "campaign_id": campaign_id,
            "conflicts": conflicts,
            "total_conflicts": len(conflicts),
            "severity_breakdown": {
                "minor": len([c for c in conflicts if c.severity <= 3]),
                "moderate": len([c for c in conflicts if 4 <= c.severity <= 6]),
                "major": len([c for c in conflicts if c.severity >= 7])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webs/", response_model=RelationshipWebSchema)
async def create_relationship_web(
    web: RelationshipWebSchema,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Create a saved relationship web configuration."""
    try:
        db_web = relationship_service.create_relationship_web(web, db)
        return RelationshipWebSchema.from_orm(db_web)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/types")
async def get_relationship_types():
    """Get available relationship types."""
    from models.relationship import RelationshipType
    return {
        "relationship_types": [t.value for t in RelationshipType],
        "descriptions": {
            "friend": "Close personal friendship",
            "ally": "Political or military alliance", 
            "enemy": "Active hostility or opposition",
            "rival": "Competitive but not necessarily hostile",
            "family": "Blood or adoptive family relation",
            "mentor": "Teacher or guide relationship",
            "student": "Learning or apprentice relationship",
            "lover": "Romantic relationship",
            "spouse": "Married or life partner",
            "business": "Professional or commercial relationship",
            "acquaintance": "Casual or passing familiarity",
            "subordinate": "Hierarchical relationship (lower)",
            "superior": "Hierarchical relationship (higher)",
            "neutral": "No particular relationship",
            "unknown": "Relationship status unclear"
        }
    }

@router.get("/character-types")
async def get_character_types():
    """Get available character types."""
    from models.relationship import CharacterType
    return {
        "character_types": [t.value for t in CharacterType],
        "descriptions": {
            "player_character": "Character controlled by a player",
            "non_player_character": "Character controlled by the GM",
            "monster": "Creature or monster",
            "organization": "Group or organization entity",
            "deity": "Divine or godlike entity"
        }
    }

@router.post("/characters/batch")
async def create_multiple_characters(
    characters: List[CharacterSchema],
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Create multiple characters at once."""
    try:
        if len(characters) > 20:
            raise HTTPException(status_code=400, detail="Cannot create more than 20 characters at once")
        
        created_characters = []
        for char_data in characters:
            db_char = relationship_service.create_character(char_data, db)
            created_characters.append(CharacterSchema.from_orm(db_char))
        
        return {
            "message": f"Successfully created {len(created_characters)} characters",
            "characters": created_characters,
            "total_created": len(created_characters)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/relationships/batch")
async def create_multiple_relationships(
    relationships: List[RelationshipSchema],
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Create multiple relationships at once."""
    try:
        if len(relationships) > 50:
            raise HTTPException(status_code=400, detail="Cannot create more than 50 relationships at once")
        
        created_relationships = []
        for rel_data in relationships:
            db_rel = relationship_service.create_relationship(rel_data, db)
            created_relationships.append(RelationshipSchema.from_orm(db_rel))
        
        return {
            "message": f"Successfully created {len(created_relationships)} relationships",
            "relationships": created_relationships,
            "total_created": len(created_relationships)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/campaigns/{campaign_id}/statistics")
async def get_relationship_statistics(
    campaign_id: str,
    relationship_service: RelationshipService = Depends(get_relationship_service),
    db: Session = Depends(get_db)
):
    """Get relationship statistics for a campaign."""
    try:
        graph = relationship_service.get_relationship_graph(campaign_id, True, None, db)
        
        # Calculate basic statistics
        total_characters = len(graph.nodes)
        total_relationships = len(graph.edges)
        
        # Character type distribution
        char_type_dist = {}
        for node in graph.nodes:
            char_type = node.character_type.value
            char_type_dist[char_type] = char_type_dist.get(char_type, 0) + 1
        
        # Relationship type distribution
        rel_type_dist = {}
        for edge in graph.edges:
            rel_type = edge.relationship_type.value
            rel_type_dist[rel_type] = rel_type_dist.get(rel_type, 0) + 1
        
        # Average relationships per character
        avg_relationships = total_relationships / total_characters if total_characters > 0 else 0
        
        return {
            "campaign_id": campaign_id,
            "statistics": {
                "total_characters": total_characters,
                "total_relationships": total_relationships,
                "average_relationships_per_character": round(avg_relationships, 2),
                "character_type_distribution": char_type_dist,
                "relationship_type_distribution": rel_type_dist,
                "network_density": round(total_relationships / (total_characters * (total_characters - 1) / 2), 3) if total_characters > 1 else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/validate/relationship")
async def validate_relationship(
    relationship_data: Dict[str, Any],
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """Validate relationship data for logical consistency."""
    try:
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["character_a_id", "character_b_id", "relationship_type"]
        for field in required_fields:
            if not relationship_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Check for self-relationship
        if relationship_data.get("character_a_id") == relationship_data.get("character_b_id"):
            errors.append("Character cannot have relationship with themselves")
        
        # Check intensity values
        intensity = relationship_data.get("intensity", 5)
        if not 1 <= intensity <= 10:
            errors.append("Intensity must be between 1 and 10")
        
        # Check trust/respect/affection levels
        for level_field in ["trust_level", "respect_level", "affection_level"]:
            level = relationship_data.get(level_field, 5)
            if not 1 <= level <= 10:
                errors.append(f"{level_field} must be between 1 and 10")
        
        # Logical consistency warnings
        rel_type = relationship_data.get("relationship_type", "")
        if rel_type == "enemy" and relationship_data.get("affection_level", 5) > 3:
            warnings.append("High affection level unusual for enemy relationship")
        
        if rel_type == "friend" and relationship_data.get("trust_level", 5) < 5:
            warnings.append("Low trust level unusual for friendship")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": [
                "Consider adding relationship history",
                "Add tags to categorize the relationship",
                "Include establishment date if known"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))