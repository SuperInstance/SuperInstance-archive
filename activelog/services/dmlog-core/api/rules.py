"""
Rule lookup and search API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.rules import (
    RuleSchema, RuleInterpretationSchema, RuleClarificationSchema,
    RuleSearchQuery, GameSystemRule, RuleCategory, RuleType
)
from services.rules_service import RulesService
from database import get_db

router = APIRouter()

# Dependency to get rules service
def get_rules_service() -> RulesService:
    return RulesService()

@router.post("/", response_model=RuleSchema)
async def create_rule(
    rule: RuleSchema,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Create a new rule."""
    try:
        db_rule = rules_service.create_rule(rule, db)
        return RuleSchema.from_orm(db_rule)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{rule_id}", response_model=RuleSchema)
async def get_rule(
    rule_id: str,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Get a rule by ID and increment view count."""
    try:
        # Get the rule
        rule = rules_service.get_rule(rule_id, db)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # Increment view count
        rules_service.increment_view_count(rule_id, db)
        
        return RuleSchema.from_orm(rule)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/search")
async def search_rules(
    query: RuleSearchQuery,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Search for rules with advanced filtering and ranking."""
    try:
        results = rules_service.search_rules(query, db)
        return {
            "query": query.query,
            "results": results,
            "total_results": len(results),
            "search_parameters": query
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/search/suggestions")
async def get_search_suggestions(
    partial_query: str,
    game_system: Optional[str] = None,
    limit: int = 10,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Get search suggestions for autocomplete."""
    try:
        game_system_enum = GameSystemRule(game_system) if game_system else None
        suggestions = rules_service.get_search_suggestions(partial_query, game_system_enum, db)
        
        return {
            "partial_query": partial_query,
            "suggestions": suggestions[:limit],
            "total_suggestions": len(suggestions)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{rule_id}/related")
async def get_related_rules(
    rule_id: str,
    max_results: int = 5,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Get rules related to the specified rule."""
    try:
        related = rules_service.get_related_rules(rule_id, db, max_results)
        return {
            "rule_id": rule_id,
            "related_rules": related,
            "total_related": len(related)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{rule_id}/interpretations/", response_model=RuleInterpretationSchema)
async def add_interpretation(
    rule_id: str,
    interpretation: RuleInterpretationSchema,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Add an interpretation to a rule."""
    try:
        interpretation.rule_id = rule_id
        db_interpretation = rules_service.create_interpretation(interpretation, db)
        return RuleInterpretationSchema.from_orm(db_interpretation)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{rule_id}/clarifications/", response_model=RuleClarificationSchema)
async def add_clarification(
    rule_id: str,
    clarification: RuleClarificationSchema,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Add a clarification to a rule."""
    try:
        clarification.rule_id = rule_id
        db_clarification = rules_service.create_clarification(clarification, db)
        return RuleClarificationSchema.from_orm(db_clarification)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/quick-reference/{game_system}/{category}")
async def get_quick_reference(
    game_system: str,
    category: str,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Generate a quick reference sheet for common rules."""
    try:
        game_system_enum = GameSystemRule(game_system)
        category_enum = RuleCategory(category)
        
        quick_ref = rules_service.get_quick_reference(game_system_enum, category_enum, db)
        return quick_ref
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/conflicts/{game_system}")
async def find_rule_conflicts(
    game_system: str,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Find potential conflicts between rules in a game system."""
    try:
        game_system_enum = GameSystemRule(game_system)
        conflicts = rules_service.find_rule_conflicts(game_system_enum, db)
        
        return {
            "game_system": game_system,
            "conflicts": conflicts,
            "total_conflicts": len(conflicts)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_rule_categories():
    """Get all available rule categories."""
    return {
        "categories": [c.value for c in RuleCategory],
        "descriptions": {
            "combat": "Combat mechanics and actions",
            "spellcasting": "Spell rules and magic system",
            "abilities": "Character abilities and features",
            "skills": "Skill checks and proficiencies",
            "equipment": "Items, weapons, and armor",
            "exploration": "Travel, environment, and discovery",
            "social": "Social interactions and roleplay",
            "character_creation": "Character building rules",
            "leveling": "Advancement and progression",
            "conditions": "Status effects and conditions",
            "environment": "Environmental hazards and effects",
            "magic_items": "Magical item properties and usage",
            "monsters": "Creature rules and abilities",
            "downtime": "Activities between adventures"
        }
    }

@router.get("/types")
async def get_rule_types():
    """Get all available rule types."""
    return {
        "types": [t.value for t in RuleType],
        "descriptions": {
            "core_rule": "Fundamental game mechanics",
            "class_feature": "Character class abilities",
            "spell": "Spell descriptions and mechanics",
            "condition": "Status effects and conditions",
            "equipment": "Item properties and rules",
            "combat_action": "Combat actions and maneuvers",
            "exploration": "Exploration and discovery rules",
            "social": "Social interaction mechanics",
            "optional_rule": "Optional or variant rules",
            "house_rule": "Custom table rules",
            "variant_rule": "Alternative rule implementations"
        }
    }

@router.get("/systems")
async def get_game_systems():
    """Get all supported game systems."""
    return {
        "systems": [s.value for s in GameSystemRule],
        "descriptions": {
            "dnd5e": "Dungeons & Dragons 5th Edition",
            "pathfinder2e": "Pathfinder Second Edition",
            "call_of_cthulhu": "Call of Cthulhu RPG",
            "savage_worlds": "Savage Worlds Adventure Edition",
            "generic": "System-agnostic rules"
        }
    }

@router.get("/popular")
async def get_popular_rules(
    game_system: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Get most viewed/popular rules."""
    try:
        # This would require extending the search to sort by view count
        from models.rules import RuleSearchQuery
        
        query = RuleSearchQuery(
            query="",  # Empty query to get all
            game_system=GameSystemRule(game_system) if game_system else None,
            categories=[RuleCategory(category)] if category else None,
            max_results=limit,
            sort_by="view_count"
        )
        
        results = rules_service.search_rules(query, db)
        
        return {
            "popular_rules": results,
            "filters": {
                "game_system": game_system,
                "category": category,
                "limit": limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/recent")
async def get_recent_rules(
    game_system: Optional[str] = None,
    limit: int = 10,
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Get recently added or updated rules."""
    try:
        # This would require a query sorted by creation/update date
        return {
            "recent_rules": [],
            "message": "Recent rules query not yet implemented",
            "filters": {
                "game_system": game_system,
                "limit": limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batch/create")
async def create_multiple_rules(
    rules: List[RuleSchema],
    rules_service: RulesService = Depends(get_rules_service),
    db: Session = Depends(get_db)
):
    """Create multiple rules at once."""
    try:
        if len(rules) > 50:
            raise HTTPException(status_code=400, detail="Cannot create more than 50 rules at once")
        
        created_rules = []
        for rule_data in rules:
            db_rule = rules_service.create_rule(rule_data, db)
            created_rules.append(RuleSchema.from_orm(db_rule))
        
        return {
            "message": f"Successfully created {len(created_rules)} rules",
            "created_rules": created_rules,
            "total_created": len(created_rules)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/collections")
async def get_rule_collections():
    """Get predefined rule collections."""
    return {
        "collections": {
            "combat_basics": {
                "name": "Combat Basics",
                "description": "Essential combat rules for new players",
                "categories": ["combat"],
                "rule_types": ["core_rule", "combat_action"]
            },
            "spellcasting_primer": {
                "name": "Spellcasting Primer", 
                "description": "Introduction to magic and spellcasting",
                "categories": ["spellcasting"],
                "rule_types": ["core_rule", "spell"]
            },
            "dm_essentials": {
                "name": "DM Essentials",
                "description": "Core rules every DM should know",
                "categories": ["combat", "exploration", "social"],
                "rule_types": ["core_rule"]
            }
        }
    }

@router.post("/validate")
async def validate_rule_content(
    rule_content: Dict[str, Any],
    rules_service: RulesService = Depends(get_rules_service)
):
    """Validate rule content for completeness and formatting."""
    try:
        # Basic validation logic
        required_fields = ["title", "content", "rule_type", "game_system", "category"]
        missing_fields = [field for field in required_fields if not rule_content.get(field)]
        
        if missing_fields:
            return {
                "is_valid": False,
                "errors": [f"Missing required field: {field}" for field in missing_fields],
                "warnings": []
            }
        
        warnings = []
        if len(rule_content.get("content", "")) < 10:
            warnings.append("Rule content seems very short")
        
        if not rule_content.get("summary"):
            warnings.append("Consider adding a summary for better searchability")
        
        return {
            "is_valid": True,
            "errors": [],
            "warnings": warnings,
            "suggestions": [
                "Add tags for better categorization",
                "Include source book reference if applicable",
                "Consider adding related rules links"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))