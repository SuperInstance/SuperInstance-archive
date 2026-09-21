"""
Base Generator Class

Provides common functionality for all template generators including
randomization, data loading, and utility functions.
"""

import random
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod


class BaseGenerator(ABC):
    """Base class for all template generators"""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional seed for reproducible results"""
        self.seed = seed
        self.rng = random.Random(seed) if seed else random.Random()
        self.data_cache = {}
        self.template_cache = {}
    
    def set_seed(self, seed: int):
        """Set new seed for random generation"""
        self.seed = seed
        self.rng = random.Random(seed)
    
    def load_data_file(self, filename: str, data_type: str = "json") -> Any:
        """Load data from file with caching"""
        cache_key = f"{filename}_{data_type}"
        
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        file_path = Path(__file__).parent.parent / "data" / filename
        
        try:
            if data_type == "json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif data_type == "yaml":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            elif data_type == "txt":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = [line.strip() for line in f if line.strip()]
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
            
            self.data_cache[cache_key] = data
            return data
            
        except FileNotFoundError:
            # Return empty data if file not found
            default_data = [] if data_type == "txt" else {}
            self.data_cache[cache_key] = default_data
            return default_data
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return [] if data_type == "txt" else {}
    
    def weighted_choice(self, choices: Dict[str, float]) -> str:
        """Make a weighted random choice"""
        if not choices:
            return ""
        
        total = sum(choices.values())
        if total <= 0:
            return self.rng.choice(list(choices.keys()))
        
        normalized = {k: v / total for k, v in choices.items()}
        rand_val = self.rng.random()
        cumulative = 0
        
        for choice, weight in normalized.items():
            cumulative += weight
            if rand_val <= cumulative:
                return choice
        
        return list(choices.keys())[-1]  # Fallback
    
    def generate_name(self, name_type: str = "fantasy", gender: Optional[str] = None) -> str:
        """Generate a name of specified type"""
        try:
            names_data = self.load_data_file("names.json")
            
            if name_type in names_data:
                name_list = names_data[name_type]
                if gender and isinstance(name_list, dict) and gender in name_list:
                    return self.rng.choice(name_list[gender])
                elif isinstance(name_list, list):
                    return self.rng.choice(name_list)
            
            # Fallback to basic fantasy names
            return self.rng.choice([
                "Aerdrie", "Beiro", "Carric", "Dayereth", "Enna", "Galinndan",
                "Halimath", "Immeral", "Lamlis", "Mindartis", "Nutae", "Paelynn",
                "Peren", "Quarion", "Riardon", "Silvyr", "Suhnaal", "Thamior",
                "Theren", "Vanuath", "Varis"
            ])
            
        except Exception:
            # Ultimate fallback
            return f"Generated{self.rng.randint(100, 999)}"
    
    def roll_dice(self, dice_expression: str) -> int:
        """Roll dice from expression like '3d6+2'"""
        try:
            # Parse dice expression
            if '+' in dice_expression:
                dice_part, modifier_part = dice_expression.split('+', 1)
                modifier = int(modifier_part)
            elif '-' in dice_expression and dice_expression.count('-') == 1:
                dice_part, modifier_part = dice_expression.split('-', 1)
                modifier = -int(modifier_part)
            else:
                dice_part = dice_expression
                modifier = 0
            
            if 'd' in dice_part:
                num_dice, die_size = dice_part.split('d')
                num_dice = int(num_dice) if num_dice else 1
                die_size = int(die_size)
                
                total = sum(self.rng.randint(1, die_size) for _ in range(num_dice))
                return total + modifier
            else:
                return int(dice_part) + modifier
                
        except (ValueError, AttributeError):
            return self.rng.randint(1, 6)  # Fallback to d6
    
    def generate_description(self, template: str, variables: Dict[str, Any]) -> str:
        """Generate description from template and variables"""
        try:
            # Simple template substitution
            description = template
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                description = description.replace(placeholder, str(value))
            return description
        except Exception:
            return template
    
    def select_from_table(self, table_name: str, modifier: int = 0) -> Any:
        """Select from a random table"""
        try:
            tables_data = self.load_data_file("random_tables.json")
            if table_name in tables_data:
                table = tables_data[table_name]
                entries = table.get("entries", [])
                if entries:
                    # Simple random selection with optional modifier
                    index = (self.rng.randint(0, len(entries) - 1) + modifier) % len(entries)
                    return entries[index]
        except Exception:
            pass
        
        return None
    
    def interpolate_by_level(self, level: int, min_val: int, max_val: int, 
                           curve: str = "linear") -> int:
        """Interpolate a value based on character level"""
        if level <= 1:
            return min_val
        if level >= 20:
            return max_val
        
        # Normalize level to 0-1 range
        t = (level - 1) / 19.0
        
        if curve == "linear":
            result = min_val + t * (max_val - min_val)
        elif curve == "exponential":
            result = min_val + (t ** 2) * (max_val - min_val)
        elif curve == "logarithmic":
            import math
            result = min_val + (math.log(1 + t * 9) / math.log(10)) * (max_val - min_val)
        else:  # Default to linear
            result = min_val + t * (max_val - min_val)
        
        return int(result)
    
    def calculate_cr_for_level(self, party_level: int, encounter_difficulty: str = "medium") -> Union[int, str]:
        """Calculate appropriate Challenge Rating for party level"""
        difficulty_modifiers = {
            "trivial": -3,
            "easy": -1,
            "medium": 0,
            "hard": 1,
            "deadly": 2,
            "legendary": 4
        }
        
        base_cr = max(1, party_level + difficulty_modifiers.get(encounter_difficulty, 0))
        
        # Handle fractional CRs for low levels
        if base_cr < 1:
            fractional_crs = ["1/8", "1/4", "1/2"]
            return fractional_crs[min(abs(base_cr), len(fractional_crs) - 1)]
        
        return min(base_cr, 30)  # Cap at CR 30
    
    def generate_stats_array(self, method: str = "standard") -> List[int]:
        """Generate ability score array using different methods"""
        if method == "standard":
            return [15, 14, 13, 12, 10, 8]
        elif method == "point_buy":
            # Simulate a reasonable point buy
            return [15, 14, 13, 12, 12, 10]
        elif method == "roll":
            # Roll 4d6, drop lowest, six times
            stats = []
            for _ in range(6):
                rolls = [self.rng.randint(1, 6) for _ in range(4)]
                rolls.sort(reverse=True)
                stats.append(sum(rolls[:3]))
            return stats
        elif method == "heroic":
            # Heroic array for powerful characters
            return [17, 15, 14, 13, 12, 10]
        else:
            return [15, 14, 13, 12, 10, 8]
    
    def get_proficiency_bonus(self, level: int) -> int:
        """Get proficiency bonus for a given level"""
        return 2 + (level - 1) // 4
    
    def format_modifier(self, ability_score: int) -> str:
        """Format ability modifier with + or - sign"""
        modifier = (ability_score - 10) // 2
        return f"{modifier:+d}"
    
    def create_weighted_list(self, items: List[str], weights: Optional[List[float]] = None) -> List[str]:
        """Create a weighted list for random selection"""
        if not weights:
            return items
        
        weighted_items = []
        for item, weight in zip(items, weights):
            count = max(1, int(weight * 100))  # Convert to integer counts
            weighted_items.extend([item] * count)
        
        return weighted_items
    
    def ensure_list(self, value: Union[str, List[str]]) -> List[str]:
        """Ensure value is a list"""
        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return value
        else:
            return [str(value)]
    
    def capitalize_words(self, text: str) -> str:
        """Capitalize each word in text"""
        return ' '.join(word.capitalize() for word in text.split())
    
    def generate_uuid(self) -> str:
        """Generate a UUID string"""
        import uuid
        return str(uuid.uuid4())
    
    def clamp(self, value: int, min_val: int, max_val: int) -> int:
        """Clamp value between min and max"""
        return max(min_val, min(value, max_val))