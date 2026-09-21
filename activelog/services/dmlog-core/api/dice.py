"""
Dice rolling API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any

from services.dice_service import (
    DiceService, DiceRollRequest, DiceRollResponse, 
    DiceProbabilityCalculator
)

router = APIRouter()

# Dependency to get dice service
def get_dice_service() -> DiceService:
    return DiceService()

@router.post("/roll", response_model=DiceRollResponse)
async def roll_dice(request: DiceRollRequest, dice_service: DiceService = Depends(get_dice_service)):
    """
    Roll dice with the specified expression and modifiers.
    
    Supports complex expressions like:
    - "1d20+5" - Basic roll with modifier
    - "2d6 advantage" - Roll with advantage
    - "4d6 keep highest 3" - Keep highest dice
    - "3d6 exploding" - Exploding dice
    """
    try:
        return dice_service.roll(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/roll/multiple")
async def roll_multiple_expressions(
    expressions: List[str], 
    label: Optional[str] = None,
    dice_service: DiceService = Depends(get_dice_service)
):
    """Roll multiple dice expressions at once."""
    try:
        results = dice_service.roll_multiple_expressions(expressions, label)
        return {
            "expressions": expressions,
            "label": label,
            "results": results,
            "total_rolls": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/statistics")
async def get_dice_statistics(dice_service: DiceService = Depends(get_dice_service)):
    """Get dice rolling statistics."""
    return dice_service.get_statistics()

@router.get("/history")
async def get_roll_history(
    limit: Optional[int] = 10, 
    dice_service: DiceService = Depends(get_dice_service)
):
    """Get recent roll history."""
    history = dice_service.get_history(limit)
    return {
        "rolls": history,
        "count": len(history)
    }

@router.delete("/history")
async def clear_roll_history(dice_service: DiceService = Depends(get_dice_service)):
    """Clear roll history."""
    dice_service.clear_history()
    return {"message": "Roll history cleared"}

@router.post("/probability/single")
async def calculate_single_die_probability(sides: int):
    """Calculate probabilities for a single die."""
    if sides < 2 or sides > 1000:
        raise HTTPException(status_code=400, detail="Dice sides must be between 2 and 1000")
    
    probabilities = DiceProbabilityCalculator.calculate_single_die_probabilities(sides)
    return {
        "sides": sides,
        "probabilities": probabilities
    }

@router.post("/probability/sum")
async def calculate_sum_probability(count: int, sides: int):
    """Calculate probabilities for the sum of multiple dice."""
    if count < 1 or count > 100:
        raise HTTPException(status_code=400, detail="Dice count must be between 1 and 100")
    if sides < 2 or sides > 100:
        raise HTTPException(status_code=400, detail="Dice sides must be between 2 and 100")
    
    probabilities = DiceProbabilityCalculator.calculate_sum_probabilities(count, sides)
    return {
        "dice_count": count,
        "dice_sides": sides,
        "probabilities": probabilities,
        "min_sum": count,
        "max_sum": count * sides
    }

@router.post("/probability/target")
async def calculate_target_probability(
    count: int, 
    sides: int, 
    target: int, 
    operator: str = ">="
):
    """Calculate probability of meeting or exceeding a target."""
    if operator not in [">=", ">", "<=", "<", "=="]:
        raise HTTPException(status_code=400, detail="Operator must be one of: >=, >, <=, <, ==")
    
    probability = DiceProbabilityCalculator.calculate_target_probability(
        count, sides, target, operator
    )
    
    return {
        "dice_count": count,
        "dice_sides": sides,
        "target": target,
        "operator": operator,
        "probability": probability,
        "percentage": probability * 100
    }

@router.post("/probability/advantage")
async def calculate_advantage_probability(target: int):
    """Calculate probabilities for advantage/disadvantage on d20."""
    if target < 1 or target > 20:
        raise HTTPException(status_code=400, detail="Target must be between 1 and 20")
    
    probabilities = DiceProbabilityCalculator.calculate_advantage_probabilities(target)
    
    return {
        "target": target,
        "normal_probability": probabilities["normal"],
        "advantage_probability": probabilities["advantage"],
        "disadvantage_probability": probabilities["disadvantage"],
        "advantage_improvement": probabilities["advantage"] - probabilities["normal"],
        "disadvantage_penalty": probabilities["normal"] - probabilities["disadvantage"]
    }

@router.get("/presets")
async def get_preset_rolls():
    """Get available preset dice rolls."""
    from services.dice_service import DiceParser
    
    presets = {
        "d20": "1d20",
        "d20_advantage": "1d20 advantage", 
        "d20_disadvantage": "1d20 disadvantage",
        "ability_score": "4d6 keep highest 3",
        "damage_shortsword": "1d6",
        "damage_greatsword": "2d6",
        "damage_fireball": "8d6",
        "hit_die_d6": "1d6",
        "hit_die_d8": "1d8",
        "hit_die_d10": "1d10",
        "hit_die_d12": "1d12",
        "percentile": "1d100",
        "inspiration": "1d4"
    }
    
    return {
        "presets": presets,
        "count": len(presets)
    }