"""
Comprehensive dice rolling service with advanced mechanics.
Supports all standard dice types and complex rolling scenarios.
"""

import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field, validator
import numpy as np

from models.base import DiceType


class RollType(str, Enum):
    """Types of dice rolls."""
    STANDARD = "standard"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"
    EXPLODING = "exploding"
    KEEP_HIGHEST = "keep_highest"
    KEEP_LOWEST = "keep_lowest"
    REROLL_ONES = "reroll_ones"
    REROLL_BELOW = "reroll_below"
    CRITICAL_RANGE = "critical_range"
    FUMBLE_RANGE = "fumble_range"


class RollModifier(str, Enum):
    """Roll modifiers."""
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"
    BLESSED = "blessed"
    CURSED = "cursed"
    LUCKY = "lucky"
    UNLUCKY = "unlucky"
    WILD_MAGIC = "wild_magic"


@dataclass
class DiceExpression:
    """Represents a dice expression like '2d6+3' or '1d20 advantage'."""
    count: int = 1
    sides: int = 20
    modifier: int = 0
    roll_type: RollType = RollType.STANDARD
    modifiers: List[RollModifier] = field(default_factory=list)
    keep_count: Optional[int] = None
    reroll_threshold: Optional[int] = None
    critical_threshold: int = 20
    fumble_threshold: int = 1
    label: Optional[str] = None
    
    def __post_init__(self):
        """Validate dice expression after creation."""
        if self.count <= 0:
            raise ValueError("Dice count must be positive")
        if self.sides <= 0:
            raise ValueError("Dice sides must be positive")
        if self.keep_count and self.keep_count > self.count:
            self.keep_count = self.count


@dataclass
class DiceRoll:
    """Represents the result of a dice roll."""
    expression: DiceExpression
    individual_rolls: List[int] = field(default_factory=list)
    kept_rolls: List[int] = field(default_factory=list)
    dropped_rolls: List[int] = field(default_factory=list)
    rerolled_dice: List[Tuple[int, int]] = field(default_factory=list)  # (original, new)
    exploded_dice: List[int] = field(default_factory=list)
    total: int = 0
    raw_total: int = 0  # Total before modifier
    modifier: int = 0
    is_critical: bool = False
    is_fumble: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    roll_id: str = field(default_factory=lambda: f"roll_{random.randint(1000, 9999)}")
    
    @property
    def success_level(self) -> str:
        """Determine success level."""
        if self.is_critical:
            return "critical_success"
        elif self.is_fumble:
            return "critical_failure"
        else:
            return "normal"


class DiceRollRequest(BaseModel):
    """Request model for dice rolling."""
    expression: str = Field(..., description="Dice expression (e.g., '2d6+3', '1d20 advantage')")
    count: int = Field(default=1, ge=1, le=100, description="Number of times to roll")
    label: Optional[str] = Field(None, description="Label for this roll")
    modifiers: List[str] = Field(default_factory=list, description="Additional modifiers")
    advantage: Optional[bool] = Field(None, description="Override advantage setting")
    disadvantage: Optional[bool] = Field(None, description="Override disadvantage setting")
    critical_threshold: int = Field(default=20, ge=2, le=20, description="Critical hit threshold")
    fumble_threshold: int = Field(default=1, ge=1, le=19, description="Fumble threshold")
    
    @validator('expression')
    def validate_expression(cls, v):
        """Validate dice expression format."""
        if not v or not isinstance(v, str):
            raise ValueError("Expression must be a non-empty string")
        return v.strip()


class DiceRollResponse(BaseModel):
    """Response model for dice rolling."""
    request: DiceRollRequest
    rolls: List[DiceRoll]
    summary: Dict[str, Any]
    execution_time_ms: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DiceParser:
    """Parser for dice expressions."""
    
    # Regex patterns for parsing dice expressions
    DICE_PATTERN = re.compile(
        r'^(?P<count>\d+)?d(?P<sides>\d+)'
        r'(?P<modifier>[+\-]\d+)?'
        r'(?:\s+(?P<flags>.*))?$',
        re.IGNORECASE
    )
    
    COMPLEX_PATTERN = re.compile(
        r'(?P<count>\d+)?d(?P<sides>\d+)'
        r'(?:k(?P<keep>\d+))?'  # keep highest/lowest
        r'(?:r(?P<reroll>\d+))?'  # reroll threshold
        r'(?:e(?P<explode>\d+)?)?'  # exploding dice
        r'(?P<modifier>[+\-]\d+)?'
        r'(?:\s+(?P<flags>.*))?',
        re.IGNORECASE
    )
    
    @classmethod
    def parse(cls, expression: str) -> DiceExpression:
        """Parse a dice expression string."""
        expression = expression.strip().lower()
        
        # Try complex pattern first
        match = cls.COMPLEX_PATTERN.match(expression)
        if not match:
            # Fall back to simple pattern
            match = cls.DICE_PATTERN.match(expression)
        
        if not match:
            raise ValueError(f"Invalid dice expression: {expression}")
        
        groups = match.groupdict()
        
        # Extract basic components
        count = int(groups.get('count') or 1)
        sides = int(groups['sides'])
        modifier = int(groups.get('modifier') or 0)
        flags = groups.get('flags', '').strip()
        
        # Parse advanced features
        keep_count = int(groups.get('keep')) if groups.get('keep') else None
        reroll_threshold = int(groups.get('reroll')) if groups.get('reroll') else None
        exploding = groups.get('explode') is not None
        
        # Parse roll type and modifiers
        roll_type = RollType.STANDARD
        modifiers = []
        
        if flags:
            flag_list = flags.split()
            for flag in flag_list:
                if flag in ['advantage', 'adv']:
                    roll_type = RollType.ADVANTAGE
                elif flag in ['disadvantage', 'dis']:
                    roll_type = RollType.DISADVANTAGE
                elif flag in ['exploding', 'explode', '!']:
                    roll_type = RollType.EXPLODING
                elif flag.startswith('kh'):  # keep highest
                    roll_type = RollType.KEEP_HIGHEST
                    if len(flag) > 2:
                        keep_count = int(flag[2:])
                elif flag.startswith('kl'):  # keep lowest
                    roll_type = RollType.KEEP_LOWEST
                    if len(flag) > 2:
                        keep_count = int(flag[2:])
                elif flag in ['reroll_ones', 'r1']:
                    roll_type = RollType.REROLL_ONES
                elif flag.startswith('r'):  # reroll below threshold
                    roll_type = RollType.REROLL_BELOW
                    if len(flag) > 1:
                        reroll_threshold = int(flag[1:])
                elif flag in ['blessed', 'lucky']:
                    modifiers.append(RollModifier.BLESSED)
                elif flag in ['cursed', 'unlucky']:
                    modifiers.append(RollModifier.CURSED)
                elif flag == 'wild':
                    modifiers.append(RollModifier.WILD_MAGIC)
        
        return DiceExpression(
            count=count,
            sides=sides,
            modifier=modifier,
            roll_type=roll_type,
            modifiers=modifiers,
            keep_count=keep_count,
            reroll_threshold=reroll_threshold
        )


class DiceService:
    """Service for handling dice rolling operations."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize dice service with optional random seed."""
        self.rng = random.Random(seed)
        self.roll_history: List[DiceRoll] = []
        self.statistics = {
            "total_rolls": 0,
            "dice_rolled": 0,
            "criticals": 0,
            "fumbles": 0,
            "exploded_dice": 0,
            "rerolls": 0
        }
    
    def roll(self, request: DiceRollRequest) -> DiceRollResponse:
        """Execute a dice roll request."""
        start_time = datetime.utcnow()
        
        try:
            # Parse the dice expression
            expression = DiceParser.parse(request.expression)
            
            # Apply request overrides
            if request.advantage is True:
                expression.roll_type = RollType.ADVANTAGE
            elif request.disadvantage is True:
                expression.roll_type = RollType.DISADVANTAGE
            
            expression.critical_threshold = request.critical_threshold
            expression.fumble_threshold = request.fumble_threshold
            expression.label = request.label
            
            # Perform the rolls
            rolls = []
            for _ in range(request.count):
                roll = self._execute_single_roll(expression)
                rolls.append(roll)
                self.roll_history.append(roll)
            
            # Update statistics
            self._update_statistics(rolls)
            
            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Create summary
            summary = self._create_summary(rolls)
            
            return DiceRollResponse(
                request=request,
                rolls=rolls,
                summary=summary,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            raise ValueError(f"Failed to execute dice roll: {str(e)}")
    
    def _execute_single_roll(self, expression: DiceExpression) -> DiceRoll:
        """Execute a single dice roll."""
        roll = DiceRoll(expression=expression)
        
        # Roll the initial dice
        initial_rolls = [self._roll_single_die(expression.sides) 
                        for _ in range(expression.count)]
        roll.individual_rolls = initial_rolls.copy()
        
        # Apply roll type modifications
        if expression.roll_type == RollType.ADVANTAGE:
            roll = self._apply_advantage(roll)
        elif expression.roll_type == RollType.DISADVANTAGE:
            roll = self._apply_disadvantage(roll)
        elif expression.roll_type == RollType.EXPLODING:
            roll = self._apply_exploding_dice(roll)
        elif expression.roll_type == RollType.KEEP_HIGHEST:
            roll = self._apply_keep_highest(roll)
        elif expression.roll_type == RollType.KEEP_LOWEST:
            roll = self._apply_keep_lowest(roll)
        elif expression.roll_type == RollType.REROLL_ONES:
            roll = self._apply_reroll_ones(roll)
        elif expression.roll_type == RollType.REROLL_BELOW:
            roll = self._apply_reroll_below(roll)
        
        # Apply modifiers
        for modifier in expression.modifiers:
            roll = self._apply_modifier(roll, modifier)
        
        # Set kept rolls if not already set
        if not roll.kept_rolls:
            roll.kept_rolls = roll.individual_rolls.copy()
        
        # Calculate totals
        roll.raw_total = sum(roll.kept_rolls)
        roll.modifier = expression.modifier
        roll.total = roll.raw_total + roll.modifier
        
        # Check for critical/fumble (only for d20 rolls)
        if expression.sides == 20:
            natural_roll = max(roll.kept_rolls) if roll.kept_rolls else 0
            roll.is_critical = natural_roll >= expression.critical_threshold
            roll.is_fumble = natural_roll <= expression.fumble_threshold
        
        return roll
    
    def _roll_single_die(self, sides: int) -> int:
        """Roll a single die with the specified number of sides."""
        return self.rng.randint(1, sides)
    
    def _apply_advantage(self, roll: DiceRoll) -> DiceRoll:
        """Apply advantage (roll twice, keep highest)."""
        if roll.expression.count == 1 and roll.expression.sides == 20:
            # Roll a second d20
            second_roll = self._roll_single_die(20)
            roll.individual_rolls.append(second_roll)
            
            # Keep the highest
            roll.kept_rolls = [max(roll.individual_rolls)]
            roll.dropped_rolls = [min(roll.individual_rolls)]
        
        return roll
    
    def _apply_disadvantage(self, roll: DiceRoll) -> DiceRoll:
        """Apply disadvantage (roll twice, keep lowest)."""
        if roll.expression.count == 1 and roll.expression.sides == 20:
            # Roll a second d20
            second_roll = self._roll_single_die(20)
            roll.individual_rolls.append(second_roll)
            
            # Keep the lowest
            roll.kept_rolls = [min(roll.individual_rolls)]
            roll.dropped_rolls = [max(roll.individual_rolls)]
        
        return roll
    
    def _apply_exploding_dice(self, roll: DiceRoll) -> DiceRoll:
        """Apply exploding dice (reroll max values and add)."""
        exploded_dice = []
        current_rolls = roll.individual_rolls.copy()
        
        while True:
            new_explosions = []
            for i, die_roll in enumerate(current_rolls):
                if die_roll == roll.expression.sides:
                    new_roll = self._roll_single_die(roll.expression.sides)
                    new_explosions.append(new_roll)
                    exploded_dice.append(die_roll)
            
            if not new_explosions:
                break
            
            roll.individual_rolls.extend(new_explosions)
            current_rolls = new_explosions
            
            # Prevent infinite loops
            if len(roll.individual_rolls) > 1000:
                break
        
        roll.exploded_dice = exploded_dice
        return roll
    
    def _apply_keep_highest(self, roll: DiceRoll) -> DiceRoll:
        """Keep only the highest dice."""
        keep_count = roll.expression.keep_count or 1
        sorted_rolls = sorted(roll.individual_rolls, reverse=True)
        
        roll.kept_rolls = sorted_rolls[:keep_count]
        roll.dropped_rolls = sorted_rolls[keep_count:]
        
        return roll
    
    def _apply_keep_lowest(self, roll: DiceRoll) -> DiceRoll:
        """Keep only the lowest dice."""
        keep_count = roll.expression.keep_count or 1
        sorted_rolls = sorted(roll.individual_rolls)
        
        roll.kept_rolls = sorted_rolls[:keep_count]
        roll.dropped_rolls = sorted_rolls[keep_count:]
        
        return roll
    
    def _apply_reroll_ones(self, roll: DiceRoll) -> DiceRoll:
        """Reroll all ones."""
        rerolled = []
        final_rolls = []
        
        for die_roll in roll.individual_rolls:
            if die_roll == 1:
                new_roll = self._roll_single_die(roll.expression.sides)
                rerolled.append((die_roll, new_roll))
                final_rolls.append(new_roll)
            else:
                final_rolls.append(die_roll)
        
        roll.rerolled_dice = rerolled
        roll.individual_rolls = final_rolls
        
        return roll
    
    def _apply_reroll_below(self, roll: DiceRoll) -> DiceRoll:
        """Reroll dice below a threshold."""
        threshold = roll.expression.reroll_threshold or 1
        rerolled = []
        final_rolls = []
        
        for die_roll in roll.individual_rolls:
            if die_roll <= threshold:
                new_roll = self._roll_single_die(roll.expression.sides)
                rerolled.append((die_roll, new_roll))
                final_rolls.append(new_roll)
            else:
                final_rolls.append(die_roll)
        
        roll.rerolled_dice = rerolled
        roll.individual_rolls = final_rolls
        
        return roll
    
    def _apply_modifier(self, roll: DiceRoll, modifier: RollModifier) -> DiceRoll:
        """Apply a roll modifier."""
        if modifier == RollModifier.BLESSED:
            # Add 1d4 to the roll
            blessing = self._roll_single_die(4)
            roll.modifier += blessing
        elif modifier == RollModifier.CURSED:
            # Subtract 1d4 from the roll
            curse = self._roll_single_die(4)
            roll.modifier -= curse
        elif modifier == RollModifier.WILD_MAGIC:
            # Random wild magic effect
            wild_effect = self.rng.choice([-2, -1, 0, 0, 0, 1, 2])
            roll.modifier += wild_effect
        
        return roll
    
    def _update_statistics(self, rolls: List[DiceRoll]) -> None:
        """Update rolling statistics."""
        for roll in rolls:
            self.statistics["total_rolls"] += 1
            self.statistics["dice_rolled"] += len(roll.individual_rolls)
            
            if roll.is_critical:
                self.statistics["criticals"] += 1
            if roll.is_fumble:
                self.statistics["fumbles"] += 1
            
            self.statistics["exploded_dice"] += len(roll.exploded_dice)
            self.statistics["rerolls"] += len(roll.rerolled_dice)
    
    def _create_summary(self, rolls: List[DiceRoll]) -> Dict[str, Any]:
        """Create a summary of the rolls."""
        if not rolls:
            return {}
        
        totals = [roll.total for roll in rolls]
        raw_totals = [roll.raw_total for roll in rolls]
        
        return {
            "total_rolls": len(rolls),
            "sum": sum(totals),
            "average": sum(totals) / len(totals),
            "min": min(totals),
            "max": max(totals),
            "raw_sum": sum(raw_totals),
            "raw_average": sum(raw_totals) / len(raw_totals),
            "criticals": sum(1 for roll in rolls if roll.is_critical),
            "fumbles": sum(1 for roll in rolls if roll.is_fumble),
            "exploded_dice": sum(len(roll.exploded_dice) for roll in rolls),
            "rerolls": sum(len(roll.rerolled_dice) for roll in rolls),
            "success_rate": len([r for r in rolls if r.success_level == "critical_success"]) / len(rolls),
            "distribution": self._calculate_distribution(totals)
        }
    
    def _calculate_distribution(self, values: List[int]) -> Dict[int, int]:
        """Calculate value distribution."""
        distribution = {}
        for value in values:
            distribution[value] = distribution.get(value, 0) + 1
        return distribution
    
    def roll_multiple_expressions(self, expressions: List[str], 
                                 label: Optional[str] = None) -> List[DiceRollResponse]:
        """Roll multiple dice expressions."""
        results = []
        for i, expression in enumerate(expressions):
            request = DiceRollRequest(
                expression=expression,
                label=f"{label} #{i+1}" if label else f"Roll #{i+1}"
            )
            result = self.roll(request)
            results.append(result)
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rolling statistics."""
        return self.statistics.copy()
    
    def get_history(self, limit: Optional[int] = None) -> List[DiceRoll]:
        """Get roll history."""
        if limit:
            return self.roll_history[-limit:]
        return self.roll_history.copy()
    
    def clear_history(self) -> None:
        """Clear roll history."""
        self.roll_history.clear()
    
    def reset_statistics(self) -> None:
        """Reset rolling statistics."""
        self.statistics = {
            "total_rolls": 0,
            "dice_rolled": 0,
            "criticals": 0,
            "fumbles": 0,
            "exploded_dice": 0,
            "rerolls": 0
        }


# Probability analysis utilities
class DiceProbabilityCalculator:
    """Calculate probabilities for dice rolls."""
    
    @staticmethod
    def calculate_single_die_probabilities(sides: int) -> Dict[int, float]:
        """Calculate probabilities for a single die."""
        probability = 1.0 / sides
        return {i: probability for i in range(1, sides + 1)}
    
    @staticmethod
    def calculate_sum_probabilities(count: int, sides: int) -> Dict[int, float]:
        """Calculate probabilities for sum of multiple dice."""
        if count == 1:
            return DiceProbabilityCalculator.calculate_single_die_probabilities(sides)
        
        # Use dynamic programming for efficiency
        prev_probs = {1: 1.0}
        
        for _ in range(count):
            new_probs = {}
            for prev_sum, prev_prob in prev_probs.items():
                for die_value in range(1, sides + 1):
                    new_sum = prev_sum + die_value
                    new_prob = prev_prob / sides
                    new_probs[new_sum] = new_probs.get(new_sum, 0) + new_prob
            prev_probs = new_probs
        
        return prev_probs
    
    @staticmethod
    def calculate_target_probability(count: int, sides: int, target: int, 
                                   operator: str = ">=") -> float:
        """Calculate probability of meeting a target."""
        probabilities = DiceProbabilityCalculator.calculate_sum_probabilities(count, sides)
        
        total_prob = 0.0
        for value, prob in probabilities.items():
            if operator == ">=" and value >= target:
                total_prob += prob
            elif operator == ">" and value > target:
                total_prob += prob
            elif operator == "<=" and value <= target:
                total_prob += prob
            elif operator == "<" and value < target:
                total_prob += prob
            elif operator == "==" and value == target:
                total_prob += prob
        
        return total_prob
    
    @staticmethod
    def calculate_advantage_probabilities(target: int) -> Dict[str, float]:
        """Calculate probabilities for advantage/disadvantage on d20."""
        normal_prob = DiceProbabilityCalculator.calculate_target_probability(1, 20, target)
        
        # Advantage: 1 - (1-p)^2
        advantage_prob = 1 - (1 - normal_prob) ** 2
        
        # Disadvantage: p^2
        disadvantage_prob = normal_prob ** 2
        
        return {
            "normal": normal_prob,
            "advantage": advantage_prob,
            "disadvantage": disadvantage_prob
        }