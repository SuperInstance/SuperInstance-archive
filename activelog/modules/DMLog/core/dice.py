"""
Advanced dice rolling system for the DMLog.ai RPG engine.
Supports various dice mechanics used across different RPG systems.
"""

import random
import re
from typing import List, Optional, Tuple, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .types import (
    DiceType, DiceRoll, RollResult, DiceRollerInterface, 
    DiceRollError, RPGEngineError
)

logger = logging.getLogger(__name__)


@dataclass
class DicePool:
    """Represents a pool of dice for systems like Shadowrun or World of Darkness."""
    dice_count: int
    dice_type: DiceType
    target_number: int = 6  # Success threshold
    exploding_on: Optional[List[int]] = None  # Numbers that cause dice to explode
    reroll_on: Optional[List[int]] = None  # Numbers that cause rerolls
    count_successes: bool = True  # Count successes vs sum total
    glitch_threshold: Optional[int] = None  # Half dice showing 1s = glitch
    
    def __post_init__(self):
        if self.exploding_on is None:
            self.exploding_on = []
        if self.reroll_on is None:
            self.reroll_on = []


@dataclass
class PoolResult:
    """Result of rolling a dice pool."""
    pool: DicePool
    individual_rolls: List[int]
    successes: int
    total: int
    glitch: bool = False
    critical_glitch: bool = False
    exploded_dice: int = 0
    rerolled_dice: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class DiceRoller(DiceRollerInterface):
    """Advanced dice roller supporting multiple RPG systems."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize dice roller with optional random seed."""
        self.random = random.Random(seed)
        self.roll_history: List[RollResult] = []
        self.callbacks: List[Callable[[RollResult], None]] = []
    
    def roll(self, dice_roll: DiceRoll) -> RollResult:
        """Roll dice according to the specified parameters."""
        try:
            if dice_roll.dice_count <= 0:
                raise DiceRollError("Dice count must be positive")
            
            # Handle advantage/disadvantage for d20 systems
            if dice_roll.advantage or dice_roll.disadvantage:
                return self._roll_with_advantage_disadvantage(dice_roll)
            
            # Standard roll
            individual_rolls = []
            for _ in range(dice_roll.dice_count):
                roll_value = self._roll_single_die(dice_roll.dice_type)
                
                # Handle reroll ones
                if dice_roll.reroll_ones and roll_value == 1:
                    roll_value = self._roll_single_die(dice_roll.dice_type)
                
                # Handle exploding dice
                if dice_roll.exploding:
                    original_value = roll_value
                    while roll_value == dice_roll.dice_type.value:
                        additional_roll = self._roll_single_die(dice_roll.dice_type)
                        roll_value += additional_roll
                        if additional_roll != dice_roll.dice_type.value:
                            break
                
                individual_rolls.append(roll_value)
            
            total = sum(individual_rolls) + dice_roll.modifier
            
            # Determine critical success/failure for d20s
            critical = None
            fumble = None
            if dice_roll.dice_type == DiceType.D20 and dice_roll.dice_count == 1:
                natural_roll = individual_rolls[0]
                if hasattr(dice_roll, 'exploding') and dice_roll.exploding:
                    # For exploding dice, use the first die rolled
                    natural_roll = individual_rolls[0] % 20 or 20
                
                critical = natural_roll == 20
                fumble = natural_roll == 1
            
            result = RollResult(
                roll=dice_roll,
                individual_rolls=individual_rolls,
                total=total,
                critical=critical,
                fumble=fumble
            )
            
            self.roll_history.append(result)
            
            # Execute callbacks
            for callback in self.callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in roll callback: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error rolling dice {dice_roll}: {e}")
            raise DiceRollError(f"Failed to roll dice: {e}")
    
    def roll_multiple(self, rolls: List[DiceRoll]) -> List[RollResult]:
        """Roll multiple sets of dice."""
        results = []
        for roll in rolls:
            results.append(self.roll(roll))
        return results
    
    def roll_with_callback(self, dice_roll: DiceRoll, 
                          callback: Callable[[RollResult], None]) -> RollResult:
        """Roll dice and execute callback with result."""
        result = self.roll(dice_roll)
        try:
            callback(result)
        except Exception as e:
            logger.error(f"Error in roll callback: {e}")
        return result
    
    def roll_pool(self, pool: DicePool) -> PoolResult:
        """Roll a dice pool (Shadowrun/World of Darkness style)."""
        try:
            individual_rolls = []
            successes = 0
            ones_count = 0
            exploded_dice = 0
            rerolled_dice = 0
            
            dice_to_roll = pool.dice_count
            
            while dice_to_roll > 0:
                for _ in range(dice_to_roll):
                    roll_value = self._roll_single_die(pool.dice_type)
                    
                    # Handle rerolls
                    if roll_value in pool.reroll_on:
                        rerolled_dice += 1
                        roll_value = self._roll_single_die(pool.dice_type)
                    
                    individual_rolls.append(roll_value)
                    
                    # Count successes
                    if roll_value >= pool.target_number:
                        successes += 1
                    
                    # Count ones for glitch detection
                    if roll_value == 1:
                        ones_count += 1
                
                # Handle exploding dice
                dice_to_roll = 0
                if pool.exploding_on:
                    for roll in individual_rolls[-pool.dice_count:]:
                        if roll in pool.exploding_on:
                            dice_to_roll += 1
                            exploded_dice += 1
                
                if dice_to_roll > 10:  # Prevent infinite loops
                    logger.warning("Too many exploding dice, stopping at 10 additional")
                    dice_to_roll = 10
            
            total = sum(individual_rolls)
            
            # Check for glitch/critical glitch
            glitch = False
            critical_glitch = False
            if pool.glitch_threshold:
                glitch_dice = ones_count
                if glitch_dice >= pool.dice_count // 2:
                    glitch = True
                    if successes == 0:
                        critical_glitch = True
            
            return PoolResult(
                pool=pool,
                individual_rolls=individual_rolls,
                successes=successes,
                total=total,
                glitch=glitch,
                critical_glitch=critical_glitch,
                exploded_dice=exploded_dice,
                rerolled_dice=rerolled_dice
            )
            
        except Exception as e:
            logger.error(f"Error rolling dice pool {pool}: {e}")
            raise DiceRollError(f"Failed to roll dice pool: {e}")
    
    def roll_fudge_dice(self, count: int = 4) -> RollResult:
        """Roll FUDGE/FATE dice (-1, 0, +1)."""
        individual_rolls = []
        for _ in range(count):
            roll = self.random.randint(-1, 1)
            individual_rolls.append(roll)
        
        total = sum(individual_rolls)
        
        # Create a fake DiceRoll for compatibility
        dice_roll = DiceRoll(dice_count=count, dice_type=DiceType.D6)
        
        return RollResult(
            roll=dice_roll,
            individual_rolls=individual_rolls,
            total=total
        )
    
    def add_callback(self, callback: Callable[[RollResult], None]) -> None:
        """Add a callback to be executed after each roll."""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[RollResult], None]) -> None:
        """Remove a callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def clear_history(self) -> None:
        """Clear roll history."""
        self.roll_history.clear()
    
    def get_history(self, limit: Optional[int] = None) -> List[RollResult]:
        """Get roll history, optionally limited to recent rolls."""
        if limit:
            return self.roll_history[-limit:]
        return self.roll_history.copy()
    
    def _roll_single_die(self, dice_type: DiceType) -> int:
        """Roll a single die of the specified type."""
        return self.random.randint(1, dice_type.value)
    
    def _roll_with_advantage_disadvantage(self, dice_roll: DiceRoll) -> RollResult:
        """Handle advantage/disadvantage rolls (roll twice, take higher/lower)."""
        if dice_roll.advantage and dice_roll.disadvantage:
            # They cancel out
            normal_roll = DiceRoll(
                dice_count=dice_roll.dice_count,
                dice_type=dice_roll.dice_type,
                modifier=dice_roll.modifier,
                exploding=dice_roll.exploding,
                reroll_ones=dice_roll.reroll_ones
            )
            return self.roll(normal_roll)
        
        # Roll twice
        roll1_results = []
        roll2_results = []
        
        for _ in range(dice_roll.dice_count):
            roll1 = self._roll_single_die(dice_roll.dice_type)
            roll2 = self._roll_single_die(dice_roll.dice_type)
            
            # Handle reroll ones
            if dice_roll.reroll_ones:
                if roll1 == 1:
                    roll1 = self._roll_single_die(dice_roll.dice_type)
                if roll2 == 1:
                    roll2 = self._roll_single_die(dice_roll.dice_type)
            
            roll1_results.append(roll1)
            roll2_results.append(roll2)
        
        # Choose which set to use
        total1 = sum(roll1_results)
        total2 = sum(roll2_results)
        
        if dice_roll.advantage:
            chosen_rolls = roll1_results if total1 >= total2 else roll2_results
            total = max(total1, total2)
        else:  # disadvantage
            chosen_rolls = roll1_results if total1 <= total2 else roll2_results
            total = min(total1, total2)
        
        total += dice_roll.modifier
        
        # Check for critical/fumble on d20
        critical = None
        fumble = None
        if dice_roll.dice_type == DiceType.D20 and dice_roll.dice_count == 1:
            natural_roll = chosen_rolls[0]
            critical = natural_roll == 20
            fumble = natural_roll == 1
        
        # Store both rolls for transparency
        all_rolls = roll1_results + roll2_results
        
        return RollResult(
            roll=dice_roll,
            individual_rolls=all_rolls,
            total=total,
            critical=critical,
            fumble=fumble
        )


class DiceExpressionParser:
    """Parse dice expressions like '2d6+3', '1d20 advantage', etc."""
    
    DICE_PATTERN = re.compile(
        r'(?P<count>\d+)?d(?P<sides>\d+)'
        r'(?P<modifier>[+-]\d+)?'
        r'(?:\s+(?P<flags>.*?))?',
        re.IGNORECASE
    )
    
    @staticmethod
    def parse(expression: str) -> DiceRoll:
        """Parse a dice expression string into a DiceRoll."""
        expression = expression.strip().lower()
        
        match = DiceExpressionParser.DICE_PATTERN.match(expression)
        if not match:
            raise DiceRollError(f"Invalid dice expression: {expression}")
        
        # Extract components
        count = int(match.group('count') or 1)
        sides = int(match.group('sides'))
        modifier = int(match.group('modifier') or 0)
        flags = match.group('flags') or ""
        
        # Map sides to DiceType
        try:
            dice_type = DiceType(sides)
        except ValueError:
            raise DiceRollError(f"Unsupported dice type: d{sides}")
        
        # Parse flags
        advantage = 'advantage' in flags or 'adv' in flags
        disadvantage = 'disadvantage' in flags or 'dis' in flags
        exploding = 'exploding' in flags or 'explode' in flags or '!' in flags
        reroll_ones = 'reroll' in flags and 'ones' in flags
        
        return DiceRoll(
            dice_count=count,
            dice_type=dice_type,
            modifier=modifier,
            advantage=advantage,
            disadvantage=disadvantage,
            exploding=exploding,
            reroll_ones=reroll_ones
        )
    
    @staticmethod
    def parse_multiple(expression: str) -> List[DiceRoll]:
        """Parse multiple dice expressions separated by commas."""
        expressions = expression.split(',')
        return [DiceExpressionParser.parse(expr.strip()) for expr in expressions]


# Global dice roller instance
default_roller = DiceRoller()


def roll_dice(expression: str) -> RollResult:
    """Convenience function to roll dice from an expression string."""
    dice_roll = DiceExpressionParser.parse(expression)
    return default_roller.roll(dice_roll)


def roll_multiple_dice(expression: str) -> List[RollResult]:
    """Convenience function to roll multiple dice expressions."""
    dice_rolls = DiceExpressionParser.parse_multiple(expression)
    return default_roller.roll_multiple(dice_rolls)


# Preset rolls for common RPG situations
PRESET_ROLLS = {
    'd20': DiceRoll(1, DiceType.D20),
    'd20_adv': DiceRoll(1, DiceType.D20, advantage=True),
    'd20_dis': DiceRoll(1, DiceType.D20, disadvantage=True),
    'stats': DiceRoll(4, DiceType.D6),  # For ability score generation
    'hit_die_d6': DiceRoll(1, DiceType.D6),
    'hit_die_d8': DiceRoll(1, DiceType.D8),
    'hit_die_d10': DiceRoll(1, DiceType.D10),
    'hit_die_d12': DiceRoll(1, DiceType.D12),
    'percentile': DiceRoll(1, DiceType.D100),
}


def get_preset_roll(name: str) -> DiceRoll:
    """Get a preset dice roll by name."""
    if name not in PRESET_ROLLS:
        raise DiceRollError(f"Unknown preset roll: {name}")
    return PRESET_ROLLS[name]