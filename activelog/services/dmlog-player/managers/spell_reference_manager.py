"""
Spell and ability quick reference manager for fast lookup during gameplay
"""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from ..models.base import Character, SpellSlotUsage


class SpellReferenceManager:
    """Manages quick reference for spells and abilities"""
    
    def __init__(self):
        # Spell database - would normally be loaded from external source
        self.spell_database: Dict[str, Dict[str, Any]] = {}
        self.character_spells: Dict[str, List[str]] = {}  # character_id -> spell_names
        self.character_abilities: Dict[str, List[Dict[str, Any]]] = {}  # character_id -> abilities
        self.usage_tracking: Dict[str, List[SpellSlotUsage]] = {}  # character_id -> usage records
        self.custom_spells: Dict[str, Dict[str, Any]] = {}  # Custom/homebrew spells
        
        # Quick access indexes
        self.spells_by_level: Dict[int, List[str]] = {}
        self.spells_by_school: Dict[str, List[str]] = {}
        self.spells_by_class: Dict[str, List[str]] = {}
        self.spell_search_index: Dict[str, Set[str]] = {}  # keyword -> spell_names
        
        self._initialize_spell_database()
    
    def add_character_spell(
        self, 
        character_id: str, 
        spell_name: str, 
        prepared: bool = True,
        known: bool = True
    ) -> bool:
        """Add a spell to character's spell list"""
        
        if spell_name not in self.spell_database:
            return False
        
        if character_id not in self.character_spells:
            self.character_spells[character_id] = []
        
        if spell_name not in self.character_spells[character_id]:
            self.character_spells[character_id].append(spell_name)
            return True
        
        return False
    
    def remove_character_spell(self, character_id: str, spell_name: str) -> bool:
        """Remove a spell from character's spell list"""
        
        if character_id not in self.character_spells:
            return False
        
        if spell_name in self.character_spells[character_id]:
            self.character_spells[character_id].remove(spell_name)
            return True
        
        return False
    
    def get_character_spells(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all spells for a character with full details"""
        
        if character_id not in self.character_spells:
            return []
        
        spell_names = self.character_spells[character_id]
        spells = []
        
        for spell_name in spell_names:
            spell_data = self.get_spell_details(spell_name)
            if spell_data:
                spells.append(spell_data)
        
        # Sort by level, then alphabetically
        spells.sort(key=lambda s: (s.get("level", 0), s.get("name", "")))
        return spells
    
    def get_spells_by_level(self, character_id: str, level: int) -> List[Dict[str, Any]]:
        """Get character spells of a specific level"""
        
        all_spells = self.get_character_spells(character_id)
        return [s for s in all_spells if s.get("level") == level]
    
    def search_spells(
        self, 
        character_id: str,
        query: str = "",
        level: Optional[int] = None,
        school: Optional[str] = None,
        casting_time: Optional[str] = None,
        range_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search character's spells with filters"""
        
        spells = self.get_character_spells(character_id)
        results = []
        
        query_lower = query.lower() if query else ""
        
        for spell in spells:
            # Text search
            if query and query_lower not in spell.get("name", "").lower() and \
               query_lower not in spell.get("description", "").lower():
                continue
            
            # Level filter
            if level is not None and spell.get("level") != level:
                continue
            
            # School filter
            if school and spell.get("school", "").lower() != school.lower():
                continue
            
            # Casting time filter
            if casting_time and casting_time.lower() not in spell.get("casting_time", "").lower():
                continue
            
            # Range filter
            if range_type and range_type.lower() not in spell.get("range", "").lower():
                continue
            
            results.append(spell)
        
        return results
    
    def get_spell_details(self, spell_name: str) -> Optional[Dict[str, Any]]:
        """Get full details for a spell"""
        
        # Check custom spells first
        if spell_name in self.custom_spells:
            return self.custom_spells[spell_name].copy()
        
        # Check main database
        if spell_name in self.spell_database:
            return self.spell_database[spell_name].copy()
        
        return None
    
    def add_custom_spell(self, spell_data: Dict[str, Any]) -> bool:
        """Add a custom/homebrew spell"""
        
        if "name" not in spell_data:
            return False
        
        spell_name = spell_data["name"]
        self.custom_spells[spell_name] = spell_data.copy()
        
        # Add to search indexes
        self._index_spell(spell_name, spell_data)
        
        return True
    
    def track_spell_usage(
        self, 
        character_id: str,
        spell_name: str,
        spell_level: int,
        slots_used: int = 1,
        upcast_level: Optional[int] = None,
        encounter_context: str = "",
        effectiveness: int = 5,
        notes: str = ""
    ) -> SpellSlotUsage:
        """Track spell slot usage"""
        
        usage = SpellSlotUsage(
            character_id=character_id,
            spell_level=spell_level,
            spell_name=spell_name,
            slots_used=slots_used,
            upcast_level=upcast_level,
            encounter_context=encounter_context,
            effectiveness=effectiveness,
            notes=notes
        )
        
        if character_id not in self.usage_tracking:
            self.usage_tracking[character_id] = []
        
        self.usage_tracking[character_id].append(usage)
        return usage
    
    def get_spell_usage_stats(self, character_id: str) -> Dict[str, Any]:
        """Get spell usage statistics for a character"""
        
        if character_id not in self.usage_tracking:
            return {
                "total_casts": 0,
                "slots_used_by_level": {},
                "most_cast_spells": [],
                "average_effectiveness": 0.0,
                "upcast_frequency": 0.0
            }
        
        usages = self.usage_tracking[character_id]
        
        # Count by spell level
        slots_by_level = {}
        spell_counts = {}
        total_effectiveness = 0
        upcast_count = 0
        
        for usage in usages:
            # Slots by level
            level = usage.spell_level
            slots_by_level[level] = slots_by_level.get(level, 0) + usage.slots_used
            
            # Spell popularity
            spell_counts[usage.spell_name] = spell_counts.get(usage.spell_name, 0) + 1
            
            # Effectiveness
            total_effectiveness += usage.effectiveness
            
            # Upcast tracking
            if usage.upcast_level and usage.upcast_level > usage.spell_level:
                upcast_count += 1
        
        most_cast = sorted(spell_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        avg_effectiveness = total_effectiveness / len(usages) if usages else 0.0
        upcast_freq = upcast_count / len(usages) if usages else 0.0
        
        return {
            "total_casts": len(usages),
            "slots_used_by_level": slots_by_level,
            "most_cast_spells": most_cast,
            "average_effectiveness": avg_effectiveness,
            "upcast_frequency": upcast_freq
        }
    
    def add_character_ability(
        self, 
        character_id: str, 
        ability: Dict[str, Any]
    ) -> bool:
        """Add a character ability/feature"""
        
        if "name" not in ability:
            return False
        
        if character_id not in self.character_abilities:
            self.character_abilities[character_id] = []
        
        # Check for duplicates
        existing_names = [a.get("name") for a in self.character_abilities[character_id]]
        if ability["name"] in existing_names:
            return False
        
        self.character_abilities[character_id].append(ability)
        return True
    
    def get_character_abilities(
        self, 
        character_id: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get character abilities, optionally filtered by category"""
        
        if character_id not in self.character_abilities:
            return []
        
        abilities = self.character_abilities[character_id]
        
        if category:
            abilities = [a for a in abilities if a.get("category", "").lower() == category.lower()]
        
        return sorted(abilities, key=lambda a: a.get("name", ""))
    
    def search_character_abilities(
        self, 
        character_id: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """Search character abilities"""
        
        abilities = self.get_character_abilities(character_id)
        query_lower = query.lower()
        
        results = []
        for ability in abilities:
            if query_lower in ability.get("name", "").lower() or \
               query_lower in ability.get("description", "").lower():
                results.append(ability)
        
        return results
    
    def get_quick_reference_card(self, character_id: str) -> Dict[str, Any]:
        """Generate a quick reference card for the character"""
        
        # Get prepared spells by level
        spells_by_level = {}
        for level in range(10):  # 0-9
            level_spells = self.get_spells_by_level(character_id, level)
            if level_spells:
                spells_by_level[level] = level_spells
        
        # Get key abilities
        key_abilities = self.get_character_abilities(character_id, "key")
        if not key_abilities:
            # If no "key" category, get all abilities
            key_abilities = self.get_character_abilities(character_id)[:10]  # Limit to 10
        
        # Get recent spell usage
        recent_usage = []
        if character_id in self.usage_tracking:
            recent_usage = sorted(
                self.usage_tracking[character_id][-10:],  # Last 10
                key=lambda u: u.used_at,
                reverse=True
            )
        
        return {
            "character_id": character_id,
            "spells_by_level": spells_by_level,
            "key_abilities": key_abilities,
            "recent_spell_usage": [u.dict() for u in recent_usage],
            "generated_at": datetime.utcnow()
        }
    
    def create_spell_slot_tracker(self, character: Character) -> Dict[str, Any]:
        """Create spell slot tracking data for character"""
        
        spell_slots = character.spell_slots.copy()
        
        # Add usage tracking
        for level_str, slot_data in spell_slots.items():
            level = int(level_str)
            
            # Get recent usage for this level
            recent_usage = []
            if character.id in self.usage_tracking:
                level_usage = [
                    u for u in self.usage_tracking[character.id] 
                    if u.spell_level == level
                ]
                recent_usage = sorted(level_usage, key=lambda u: u.used_at, reverse=True)[:5]
            
            slot_data["recent_usage"] = [u.dict() for u in recent_usage]
        
        return {
            "character_id": character.id,
            "spell_slots": spell_slots,
            "total_slots_available": sum(slot_data.get("max", 0) - slot_data.get("used", 0) 
                                       for slot_data in spell_slots.values()),
            "total_slots_used": sum(slot_data.get("used", 0) for slot_data in spell_slots.values())
        }
    
    def suggest_spell_preparation(
        self, 
        character_id: str,
        upcoming_encounters: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """Suggest spell preparation based on usage history and upcoming encounters"""
        
        stats = self.get_spell_usage_stats(character_id)
        most_cast = [spell for spell, count in stats.get("most_cast_spells", [])]
        
        suggestions = {
            "high_usage": most_cast[:5],  # Top 5 most used
            "combat": [],
            "utility": [],
            "social": []
        }
        
        # Categorize spells by typical use
        all_spells = self.get_character_spells(character_id)
        
        for spell in all_spells:
            spell_name = spell.get("name", "")
            tags = spell.get("tags", [])
            
            if "combat" in tags or spell.get("school") in ["evocation", "necromancy"]:
                suggestions["combat"].append(spell_name)
            elif "utility" in tags or spell.get("school") in ["transmutation", "divination"]:
                suggestions["utility"].append(spell_name)
            elif "social" in tags or spell.get("school") in ["enchantment", "illusion"]:
                suggestions["social"].append(spell_name)
        
        # Limit suggestions
        for category in ["combat", "utility", "social"]:
            suggestions[category] = suggestions[category][:3]
        
        return suggestions
    
    def _initialize_spell_database(self):
        """Initialize the spell database with common spells"""
        
        # This would normally load from external database
        # Adding a few examples for demonstration
        
        sample_spells = {
            "Magic Missile": {
                "name": "Magic Missile",
                "level": 1,
                "school": "evocation",
                "casting_time": "1 action",
                "range": "120 feet",
                "components": ["V", "S"],
                "duration": "Instantaneous",
                "description": "You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range.",
                "damage": "1d4+1 force per dart",
                "upcast": "One additional dart per slot level above 1st",
                "classes": ["sorcerer", "wizard"],
                "tags": ["combat", "reliable"]
            },
            "Cure Wounds": {
                "name": "Cure Wounds",
                "level": 1,
                "school": "evocation",
                "casting_time": "1 action",
                "range": "Touch",
                "components": ["V", "S"],
                "duration": "Instantaneous",
                "description": "A creature you touch regains a number of hit points equal to 1d8 + your spellcasting ability modifier.",
                "healing": "1d8 + spellcasting modifier",
                "upcast": "1d8 additional healing per slot level above 1st",
                "classes": ["bard", "cleric", "druid", "paladin", "ranger"],
                "tags": ["healing", "utility"]
            },
            "Fireball": {
                "name": "Fireball",
                "level": 3,
                "school": "evocation",
                "casting_time": "1 action",
                "range": "150 feet",
                "components": ["V", "S", "M"],
                "duration": "Instantaneous",
                "description": "A bright streak flashes from your pointing finger to a point you choose within range and then blossoms with a low roar into an explosion of flame.",
                "damage": "8d6 fire",
                "save": "Dexterity DC for half damage",
                "area": "20-foot radius sphere",
                "upcast": "1d6 additional damage per slot level above 3rd",
                "classes": ["sorcerer", "wizard"],
                "tags": ["combat", "aoe", "damage"]
            }
        }
        
        self.spell_database = sample_spells
        
        # Build indexes
        for spell_name, spell_data in sample_spells.items():
            self._index_spell(spell_name, spell_data)
    
    def _index_spell(self, spell_name: str, spell_data: Dict[str, Any]):
        """Add spell to search indexes"""
        
        level = spell_data.get("level", 0)
        school = spell_data.get("school", "")
        classes = spell_data.get("classes", [])
        
        # Index by level
        if level not in self.spells_by_level:
            self.spells_by_level[level] = []
        if spell_name not in self.spells_by_level[level]:
            self.spells_by_level[level].append(spell_name)
        
        # Index by school
        if school:
            if school not in self.spells_by_school:
                self.spells_by_school[school] = []
            if spell_name not in self.spells_by_school[school]:
                self.spells_by_school[school].append(spell_name)
        
        # Index by class
        for class_name in classes:
            if class_name not in self.spells_by_class:
                self.spells_by_class[class_name] = []
            if spell_name not in self.spells_by_class[class_name]:
                self.spells_by_class[class_name].append(spell_name)
        
        # Build keyword index
        keywords = []
        keywords.extend(spell_name.lower().split())
        keywords.extend(spell_data.get("description", "").lower().split())
        keywords.extend(spell_data.get("tags", []))
        
        for keyword in keywords:
            if len(keyword) > 2:  # Skip very short words
                if keyword not in self.spell_search_index:
                    self.spell_search_index[keyword] = set()
                self.spell_search_index[keyword].add(spell_name)