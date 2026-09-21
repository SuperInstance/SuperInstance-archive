"""
Advanced Character Optimization Engine
Surpasses D&D Beyond with intelligent build analysis and suggestions
"""

import json
import math
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class BuildType(Enum):
    TANK = "tank"
    DAMAGE = "damage" 
    SUPPORT = "support"
    UTILITY = "utility"
    BALANCED = "balanced"
    SPECIALIST = "specialist"

class OptimizationPriority(Enum):
    COMBAT = "combat"
    ROLEPLAY = "roleplay"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    BALANCED = "balanced"

@dataclass
class AbilityScores:
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    def to_dict(self):
        return {
            'str': self.strength,
            'dex': self.dexterity, 
            'con': self.constitution,
            'int': self.intelligence,
            'wis': self.wisdom,
            'cha': self.charisma
        }

class CharacterOptimizer:
    """Advanced character optimization with mathematical analysis"""
    
    def __init__(self):
        self.class_priorities = {
            'fighter': {'str': 3, 'dex': 2, 'con': 3, 'int': 0, 'wis': 1, 'cha': 0},
            'wizard': {'str': 0, 'dex': 2, 'con': 2, 'int': 3, 'wis': 1, 'cha': 0},
            'rogue': {'str': 0, 'dex': 3, 'con': 2, 'int': 1, 'wis': 1, 'cha': 1},
            'cleric': {'str': 1, 'dex': 1, 'con': 2, 'int': 0, 'wis': 3, 'cha': 1},
            'ranger': {'str': 1, 'dex': 3, 'con': 2, 'int': 0, 'wis': 2, 'cha': 0},
            'barbarian': {'str': 3, 'dex': 2, 'con': 3, 'int': 0, 'wis': 1, 'cha': 0},
            'bard': {'str': 0, 'dex': 2, 'con': 1, 'int': 1, 'wis': 1, 'cha': 3},
            'druid': {'str': 0, 'dex': 2, 'con': 2, 'int': 1, 'wis': 3, 'cha': 0},
            'monk': {'str': 1, 'dex': 3, 'con': 2, 'int': 0, 'wis': 2, 'cha': 0},
            'paladin': {'str': 3, 'dex': 1, 'con': 2, 'int': 0, 'wis': 1, 'cha': 2},
            'sorcerer': {'str': 0, 'dex': 2, 'con': 2, 'int': 1, 'wis': 1, 'cha': 3},
            'warlock': {'str': 0, 'dex': 2, 'con': 2, 'int': 1, 'wis': 1, 'cha': 3}
        }
        
        self.race_bonuses = {
            'human': {'str': 1, 'dex': 1, 'con': 1, 'int': 1, 'wis': 1, 'cha': 1},
            'elf': {'dex': 2, 'int': 1},
            'dwarf': {'con': 2, 'str': 2},
            'halfling': {'dex': 2, 'cha': 1},
            'dragonborn': {'str': 2, 'cha': 1},
            'gnome': {'int': 2, 'con': 1},
            'half-elf': {'cha': 2, 'any': 2},  # +1 to two different abilities
            'half-orc': {'str': 2, 'con': 1},
            'tiefling': {'int': 1, 'cha': 2}
        }
        
        self.multiclass_synergies = {
            ('fighter', 'wizard'): 0.7,  # Eldritch Knight style
            ('rogue', 'wizard'): 0.8,   # Arcane Trickster
            ('barbarian', 'fighter'): 0.9,  # Great synergy
            ('paladin', 'sorcerer'): 0.8,   # Divine Soul
            ('ranger', 'rogue'): 0.8,       # Scout archetype
            ('monk', 'cleric'): 0.6,        # Wisdom synergy
            ('bard', 'warlock'): 0.9,       # Charisma powerhouse
            ('druid', 'ranger'): 0.7        # Nature theme
        }
        
        self.build_archetypes = {
            BuildType.TANK: {
                'primary_stats': ['con', 'str'],
                'secondary_stats': ['wis', 'cha'],
                'preferred_classes': ['fighter', 'paladin', 'barbarian'],
                'key_features': ['high_hp', 'high_ac', 'saves']
            },
            BuildType.DAMAGE: {
                'primary_stats': ['str', 'dex'],
                'secondary_stats': ['con'],
                'preferred_classes': ['fighter', 'ranger', 'rogue', 'barbarian'],
                'key_features': ['damage_output', 'accuracy', 'critical_hits']
            },
            BuildType.SUPPORT: {
                'primary_stats': ['wis', 'cha'],
                'secondary_stats': ['con'],
                'preferred_classes': ['cleric', 'bard', 'druid'],
                'key_features': ['healing', 'buffs', 'crowd_control']
            }
        }
    
    def analyze_build(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive character build analysis"""
        scores = json.loads(character_data.get('ability_scores', '{}'))
        char_class = character_data.get('class', '').lower()
        race = character_data.get('race', '').lower()
        level = character_data.get('level', 1)
        
        analysis = {
            'score': 0.0,
            'build_type': BuildType.BALANCED.value,
            'strengths': [],
            'weaknesses': [],
            'suggestions': [],
            'multiclass_suggestions': []
        }
        
        # Calculate base optimization score
        if char_class in self.class_priorities and scores:
            class_priorities = self.class_priorities[char_class]
            
            # Score based on how well abilities align with class needs
            total_weight = sum(class_priorities.values())
            weighted_score = 0
            
            for ability, weight in class_priorities.items():
                if ability in scores:
                    ability_score = scores[ability]
                    modifier = (ability_score - 10) // 2
                    
                    # Higher weight = more important for class
                    contribution = (modifier * weight) / total_weight
                    weighted_score += contribution
            
            # Normalize to 0-1 scale
            analysis['score'] = min(1.0, max(0.0, (weighted_score + 5) / 10))
        
        # Determine build type
        analysis['build_type'] = self._determine_build_type(scores, char_class)
        
        # Analyze strengths and weaknesses
        analysis['strengths'] = self._identify_strengths(scores, char_class, race)
        analysis['weaknesses'] = self._identify_weaknesses(scores, char_class, race)
        
        # Generate improvement suggestions
        analysis['suggestions'] = self._generate_suggestions(scores, char_class, level)
        
        # Multiclass recommendations
        if level >= 2:
            analysis['multiclass_suggestions'] = self._suggest_multiclass(
                scores, char_class, level
            )
        
        return analysis
    
    def _determine_build_type(self, scores: Dict[str, int], char_class: str) -> str:
        """Determine the character's build archetype"""
        if not scores or char_class not in self.class_priorities:
            return BuildType.BALANCED.value
        
        # Calculate affinity for each build type
        type_scores = {}
        
        for build_type, archetype in self.build_archetypes.items():
            score = 0
            
            # Primary stat alignment
            for stat in archetype['primary_stats']:
                if stat in scores:
                    score += (scores[stat] - 10) * 2
            
            # Secondary stat alignment  
            for stat in archetype['secondary_stats']:
                if stat in scores:
                    score += (scores[stat] - 10)
            
            # Class preference bonus
            if char_class in archetype['preferred_classes']:
                score += 20
            
            type_scores[build_type] = score
        
        # Return the highest scoring build type
        best_type = max(type_scores, key=type_scores.get)
        return best_type.value
    
    def _identify_strengths(self, scores: Dict[str, int], char_class: str, race: str) -> List[str]:
        """Identify character build strengths"""
        strengths = []
        
        if not scores:
            return strengths
        
        # High ability scores
        for ability, score in scores.items():
            modifier = (score - 10) // 2
            if modifier >= 3:
                strengths.append(f"Excellent {ability.upper()} ({score}, +{modifier})")
            elif modifier >= 2:
                strengths.append(f"Strong {ability.upper()} ({score}, +{modifier})")
        
        # Class-specific strengths
        if char_class in self.class_priorities:
            priorities = self.class_priorities[char_class]
            
            for ability, weight in priorities.items():
                if weight >= 3 and ability in scores:
                    modifier = (scores[ability] - 10) // 2
                    if modifier >= 2:
                        strengths.append(f"Well-suited for {char_class} (high {ability.upper()})")
        
        # Race-class synergies
        race_synergy = self.calculate_race_class_synergy(race, char_class)
        if race_synergy > 0.8:
            strengths.append(f"Excellent {race}-{char_class} synergy")
        
        return strengths
    
    def _identify_weaknesses(self, scores: Dict[str, int], char_class: str, race: str) -> List[str]:
        """Identify character build weaknesses"""
        weaknesses = []
        
        if not scores:
            return weaknesses
        
        # Low ability scores
        for ability, score in scores.items():
            modifier = (score - 10) // 2
            if modifier <= -2:
                weaknesses.append(f"Poor {ability.upper()} ({score}, {modifier})")
        
        # Class priority misalignments
        if char_class in self.class_priorities:
            priorities = self.class_priorities[char_class]
            
            for ability, weight in priorities.items():
                if weight >= 2 and ability in scores:
                    modifier = (scores[ability] - 10) // 2
                    if modifier <= 0:
                        weaknesses.append(f"Low {ability.upper()} for {char_class}")
        
        # Constitution warnings
        if 'con' in scores and scores['con'] < 14:
            weaknesses.append("Low Constitution - survivability concern")
        
        # Unbalanced builds
        high_stats = sum(1 for score in scores.values() if score >= 15)
        low_stats = sum(1 for score in scores.values() if score <= 8)
        
        if high_stats == 1 and low_stats >= 2:
            weaknesses.append("Very specialized build - limited versatility")
        
        return weaknesses
    
    def _generate_suggestions(self, scores: Dict[str, int], char_class: str, level: int) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        if not scores or char_class not in self.class_priorities:
            return suggestions
        
        priorities = self.class_priorities[char_class]
        
        # Ability Score Improvements
        if level >= 4:
            # Find the most important stats that could use improvement
            for ability, weight in sorted(priorities.items(), key=lambda x: x[1], reverse=True):
                if weight >= 2 and ability in scores:
                    current_score = scores[ability]
                    if current_score < 20 and current_score % 2 == 1:  # Odd scores benefit most
                        suggestions.append(f"Consider +1 {ability.upper()} at next ASI (currently {current_score})")
                        break
        
        # Feat recommendations
        feat_suggestions = self._recommend_feats(scores, char_class, level)
        suggestions.extend(feat_suggestions)
        
        # Equipment suggestions
        equipment_suggestions = self._recommend_equipment(scores, char_class)
        suggestions.extend(equipment_suggestions)
        
        return suggestions[:5]  # Limit to top 5 suggestions
    
    def _recommend_feats(self, scores: Dict[str, int], char_class: str, level: int) -> List[str]:
        """Recommend feats based on build"""
        feats = []
        
        if level < 4:
            return feats
        
        # Universal good feats
        if 'con' in scores and scores['con'] < 16:
            feats.append("Tough feat for +2 HP per level")
        
        # Class-specific feats
        if char_class in ['fighter', 'paladin', 'ranger']:
            if 'str' in scores and scores['str'] >= 13:
                feats.append("Great Weapon Master for damage boost")
            if 'dex' in scores and scores['dex'] >= 13:
                feats.append("Sharpshooter for ranged builds")
        
        elif char_class in ['wizard', 'sorcerer']:
            feats.append("War Caster for concentration saves")
            feats.append("Spell Sniper for range and critical hits")
        
        elif char_class == 'rogue':
            feats.append("Alert for guaranteed high initiative")
            feats.append("Mobile for hit-and-run tactics")
        
        return feats[:2]  # Top 2 feat suggestions
    
    def _recommend_equipment(self, scores: Dict[str, int], char_class: str) -> List[str]:
        """Recommend equipment optimizations"""
        equipment = []
        
        # Armor recommendations
        if char_class in ['fighter', 'paladin', 'cleric']:
            equipment.append("Prioritize heavy armor for AC")
        elif char_class in ['rogue', 'ranger']:
            equipment.append("Light/medium armor to maintain stealth")
        
        # Weapon recommendations
        if char_class in ['fighter', 'paladin', 'barbarian']:
            if 'str' in scores and scores['str'] >= 15:
                equipment.append("Two-handed weapons for maximum damage")
        
        return equipment
    
    def _suggest_multiclass(self, scores: Dict[str, int], char_class: str, level: int) -> List[Dict[str, Any]]:
        """Suggest multiclass options"""
        suggestions = []
        
        if level < 5:  # Don't suggest multiclass too early
            return suggestions
        
        # Check multiclass requirements and synergies
        for other_class in self.class_priorities:
            if other_class == char_class:
                continue
            
            combo = tuple(sorted([char_class, other_class]))
            synergy_score = self.multiclass_synergies.get(combo, 0.5)
            
            if synergy_score >= 0.7:
                # Check if character meets multiclass requirements
                if self._meets_multiclass_requirements(scores, other_class):
                    suggestions.append({
                        'class': other_class,
                        'synergy_score': synergy_score,
                        'suggested_levels': self._calculate_multiclass_split(char_class, other_class, level),
                        'benefits': self._multiclass_benefits(char_class, other_class)
                    })
        
        # Sort by synergy score
        suggestions.sort(key=lambda x: x['synergy_score'], reverse=True)
        return suggestions[:3]  # Top 3 multiclass options
    
    def _meets_multiclass_requirements(self, scores: Dict[str, int], class_name: str) -> bool:
        """Check if character meets multiclass requirements"""
        requirements = {
            'fighter': ('str', 13),
            'wizard': ('int', 13),
            'rogue': ('dex', 13),
            'cleric': ('wis', 13),
            'ranger': ('dex', 13),
            'barbarian': ('str', 13),
            'bard': ('cha', 13),
            'druid': ('wis', 13),
            'monk': ('dex', 13),
            'paladin': ('str', 13),
            'sorcerer': ('cha', 13),
            'warlock': ('cha', 13)
        }
        
        if class_name in requirements:
            req_ability, req_score = requirements[class_name]
            return scores.get(req_ability, 10) >= req_score
        
        return False
    
    def _calculate_multiclass_split(self, primary_class: str, secondary_class: str, total_level: int) -> Dict[str, int]:
        """Calculate optimal level split for multiclass"""
        # Default split based on synergy and class progression
        if total_level <= 6:
            return {primary_class: total_level - 1, secondary_class: 1}
        elif total_level <= 10:
            return {primary_class: total_level - 2, secondary_class: 2}
        else:
            # More complex calculation for higher levels
            primary_levels = max(6, int(total_level * 0.6))
            secondary_levels = total_level - primary_levels
            return {primary_class: primary_levels, secondary_class: secondary_levels}
    
    def _multiclass_benefits(self, class1: str, class2: str) -> List[str]:
        """List benefits of specific multiclass combinations"""
        benefits = []
        
        combo = tuple(sorted([class1, class2]))
        
        multiclass_benefits = {
            ('fighter', 'wizard'): ['Armor and weapon proficiencies', 'Spellcasting', 'Action Surge for more spells'],
            ('barbarian', 'fighter'): ['More fighting styles', 'Action Surge while raging', 'Improved combat versatility'],
            ('bard', 'warlock'): ['More spell slots', 'Charisma synergy', 'Eldritch Blast + Inspiration'],
            ('paladin', 'sorcerer'): ['More spell slots for smites', 'Charisma focus', 'Subtle spell for social encounters'],
            ('ranger', 'rogue'): ['Sneak attack + Hunter\'s Mark', 'Better skill coverage', 'Improved stealth and tracking'],
            ('rogue', 'wizard'): ['Spells for utility and damage', 'Better problem-solving tools', 'Arcane knowledge']
        }
        
        return multiclass_benefits.get(combo, ['Increased versatility', 'More options in combat'])
    
    def calculate_race_class_synergy(self, race: str, char_class: str) -> float:
        """Calculate how well a race synergizes with a class"""
        if not race or not char_class or race not in self.race_bonuses or char_class not in self.class_priorities:
            return 0.5
        
        race_bonuses = self.race_bonuses[race]
        class_priorities = self.class_priorities[char_class]
        
        synergy_score = 0
        total_weight = sum(class_priorities.values())
        
        for ability, priority_weight in class_priorities.items():
            if ability in race_bonuses:
                racial_bonus = race_bonuses[ability]
                contribution = (racial_bonus * priority_weight) / total_weight
                synergy_score += contribution
        
        # Handle special cases like half-elf
        if race == 'half-elf' and 'any' in race_bonuses:
            # Half-elf can put +1 in two abilities of choice
            top_priorities = sorted(class_priorities.items(), key=lambda x: x[1], reverse=True)[:2]
            for ability, weight in top_priorities:
                if ability not in race_bonuses:  # Don't double-count charisma
                    synergy_score += (1 * weight) / total_weight
        
        # Normalize to 0-1 scale
        return min(1.0, synergy_score / 3)  # Divide by 3 as max reasonable bonus
    
    def calculate_point_buy_cost(self, scores: Dict[str, int]) -> int:
        """Calculate point buy cost for ability scores"""
        point_costs = {
            8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9
        }
        
        total_cost = 0
        for score in scores.values():
            if 8 <= score <= 15:
                total_cost += point_costs[score]
            elif score > 15:
                return 999  # Invalid for point buy
        
        return total_cost
    
    def apply_racial_bonuses(self, base_scores: Dict[str, int], race: str) -> Dict[str, int]:
        """Apply racial ability score bonuses"""
        final_scores = base_scores.copy()
        
        if race in self.race_bonuses:
            bonuses = self.race_bonuses[race]
            for ability, bonus in bonuses.items():
                if ability in final_scores and ability != 'any':
                    final_scores[ability] = min(20, final_scores[ability] + bonus)
        
        return final_scores
    
    def optimize_ability_scores(self, scores: Dict[str, int], char_class: str) -> Dict[str, Any]:
        """Optimize ability scores for a specific class"""
        if char_class not in self.class_priorities:
            return {'rating': 0.5, 'improvements': ['Unknown class - cannot optimize']}
        
        priorities = self.class_priorities[char_class]
        improvements = []
        
        # Check for optimization opportunities
        for ability, weight in priorities.items():
            if ability in scores:
                current_score = scores[ability]
                current_modifier = (current_score - 10) // 2
                
                if weight >= 2:  # Important ability
                    if current_score < 14:
                        improvements.append(f"Increase {ability.upper()} (currently {current_score})")
                    elif current_score % 2 == 1 and current_score < 20:
                        improvements.append(f"Round up {ability.upper()} to {current_score + 1}")
        
        # Calculate overall rating
        total_weight = sum(priorities.values())
        weighted_score = sum(
            ((scores.get(ability, 10) - 10) // 2) * weight 
            for ability, weight in priorities.items()
        ) / total_weight
        
        rating = min(1.0, max(0.0, (weighted_score + 2) / 4))
        
        return {
            'rating': rating,
            'improvements': improvements[:3]
        }
    
    def suggest_classes_for_race(self, race: str) -> List[Dict[str, Any]]:
        """Suggest optimal classes for a given race"""
        if race not in self.race_bonuses:
            return []
        
        suggestions = []
        
        for char_class in self.class_priorities:
            synergy = self.calculate_race_class_synergy(race, char_class)
            
            suggestions.append({
                'class': char_class,
                'synergy_score': synergy,
                'rating': 'Excellent' if synergy > 0.8 else 'Good' if synergy > 0.6 else 'Average' if synergy > 0.4 else 'Poor'
            })
        
        # Sort by synergy score
        suggestions.sort(key=lambda x: x['synergy_score'], reverse=True)
        return suggestions[:5]  # Top 5 suggestions

class PartyAnalyzer:
    """Analyze party composition and provide optimization suggestions"""
    
    def __init__(self):
        self.role_definitions = {
            'tank': {
                'primary_classes': ['fighter', 'paladin', 'barbarian'],
                'key_abilities': ['str', 'con'],
                'features': ['high_hp', 'high_ac', 'damage_resistance']
            },
            'healer': {
                'primary_classes': ['cleric', 'druid', 'bard'],
                'key_abilities': ['wis', 'cha'],
                'features': ['healing_spells', 'support_magic', 'buffs']
            },
            'damage_dealer': {
                'primary_classes': ['fighter', 'ranger', 'rogue', 'wizard', 'sorcerer'],
                'key_abilities': ['str', 'dex', 'int', 'cha'],
                'features': ['high_damage_output', 'spell_damage', 'weapon_mastery']
            },
            'utility': {
                'primary_classes': ['rogue', 'bard', 'ranger', 'wizard'],
                'key_abilities': ['dex', 'int', 'wis', 'cha'],
                'features': ['skills', 'spells', 'problem_solving']
            },
            'controller': {
                'primary_classes': ['wizard', 'druid', 'bard', 'sorcerer'],
                'key_abilities': ['int', 'wis', 'cha'],
                'features': ['crowd_control', 'battlefield_control', 'debuffs']
            }
        }
    
    def analyze_composition(self, character_ids: List[str]) -> Dict[str, Any]:
        """Analyze party composition and balance"""
        # This would fetch character data from database
        # For now, returning a template analysis
        
        analysis = {
            'balance_score': 0.0,
            'roles_covered': [],
            'missing_roles': [],
            'recommendations': [],
            'synergies': [],
            'weaknesses': []
        }
        
        return analysis
    
    def comprehensive_analysis(self, characters: List[Any]) -> Dict[str, Any]:
        """Perform comprehensive party analysis"""
        analysis = {
            'party_size': len(characters),
            'average_level': 0,
            'roles_covered': [],
            'missing_roles': [],
            'build_suggestions': [],
            'power_analysis': {},
            'synergies': [],
            'balance_score': 0.0
        }
        
        if not characters:
            return analysis
        
        # Calculate average level
        levels = []
        for char in characters:
            level = char[4] if isinstance(char, tuple) else char.get('level', 1)
            levels.append(level)
        
        analysis['average_level'] = sum(levels) / len(levels)
        
        # Analyze roles (simplified for demo)
        classes = []
        for char in characters:
            char_class = char[7] if isinstance(char, tuple) else char.get('class', '')
            classes.append(char_class.lower())
        
        # Determine covered roles
        covered_roles = set()
        for char_class in classes:
            for role, definition in self.role_definitions.items():
                if char_class in definition['primary_classes']:
                    covered_roles.add(role)
        
        analysis['roles_covered'] = list(covered_roles)
        analysis['missing_roles'] = list(set(self.role_definitions.keys()) - covered_roles)
        
        # Calculate balance score
        ideal_roles = ['tank', 'healer', 'damage_dealer', 'utility']
        covered_ideal = len([role for role in ideal_roles if role in covered_roles])
        analysis['balance_score'] = covered_ideal / len(ideal_roles)
        
        # Generate build suggestions for missing roles
        for missing_role in analysis['missing_roles']:
            role_def = self.role_definitions[missing_role]
            analysis['build_suggestions'].append({
                'role': missing_role,
                'recommended_classes': role_def['primary_classes'],
                'key_abilities': role_def['key_abilities'],
                'priority': 'High' if missing_role in ideal_roles else 'Medium'
            })
        
        return analysis