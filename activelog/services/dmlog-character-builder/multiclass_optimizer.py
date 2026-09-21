"""
Advanced Multiclass Optimization Engine
Sophisticated analysis and optimization of multiclass character builds
with deep synergy analysis and mathematical optimization
"""

import math
import itertools
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import json
from enum import Enum

class OptimizationGoal(Enum):
    DAMAGE = "damage"
    SURVIVABILITY = "survivability"
    VERSATILITY = "versatility"
    CONTROL = "control"
    SUPPORT = "support"

@dataclass
class ClassProgression:
    class_name: str
    levels: int
    subclass: Optional[str] = None
    features_gained: Dict[int, List[str]] = field(default_factory=dict)
    spells_gained: Dict[int, List[str]] = field(default_factory=dict)
    asi_levels: List[int] = field(default_factory=list)
    
@dataclass
class MulticlassBuild:
    name: str
    race: str
    background: str
    classes: List[ClassProgression]
    ability_scores: Dict[str, int]
    feat_progression: Dict[int, str]  # level -> feat
    spell_selection: Dict[str, List[str]]  # class -> spells
    optimization_score: float
    synergy_ratings: Dict[str, float]
    level_progression: List[str]  # Order to take levels
    strengths: List[str]
    weaknesses: List[str]
    recommended_stats: Dict[str, int]

class MulticlassOptimizer:
    """Advanced multiclass optimization and analysis engine"""
    
    def __init__(self):
        self.class_data = self._load_class_data()
        self.synergy_matrix = self._build_synergy_matrix()
        self.feat_database = self._load_feat_database()
        self.optimization_weights = self._load_optimization_weights()
        
    def _load_class_data(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive class data for optimization"""
        return {
            "fighter": {
                "hit_die": 10,
                "primary_stats": ["strength", "dexterity"],
                "saving_throws": ["strength", "constitution"],
                "features_by_level": {
                    1: ["Fighting Style", "Second Wind"],
                    2: ["Action Surge"],
                    3: ["Martial Archetype"],
                    4: ["ASI"],
                    5: ["Extra Attack"],
                    6: ["ASI"],
                    7: ["Archetype Feature"],
                    8: ["ASI"],
                    9: ["Indomitable"],
                    10: ["Archetype Feature"],
                    11: ["Extra Attack (2)"],
                    12: ["ASI"],
                    13: ["Indomitable (2)"],
                    14: ["ASI"],
                    15: ["Archetype Feature"],
                    16: ["ASI"],
                    17: ["Action Surge (2)", "Indomitable (3)"],
                    18: ["Archetype Feature"],
                    19: ["ASI"],
                    20: ["Extra Attack (3)"]
                },
                "spellcasting": None,
                "multiclass_requirements": {"strength": 13, "dexterity": 13},
                "optimization_bonuses": {
                    "damage": 0.9,
                    "survivability": 0.8,
                    "versatility": 0.6
                }
            },
            "wizard": {
                "hit_die": 6,
                "primary_stats": ["intelligence"],
                "saving_throws": ["intelligence", "wisdom"],
                "features_by_level": {
                    1: ["Spellcasting", "Arcane Recovery"],
                    2: ["Arcane Tradition"],
                    3: ["2nd Level Spells"],
                    4: ["ASI"],
                    5: ["3rd Level Spells"],
                    6: ["Arcane Tradition Feature"],
                    7: ["4th Level Spells"],
                    8: ["ASI"],
                    9: ["5th Level Spells"],
                    10: ["Arcane Tradition Feature"],
                    11: ["6th Level Spells"],
                    12: ["ASI"],
                    13: ["7th Level Spells"],
                    14: ["Arcane Tradition Feature"],
                    15: ["8th Level Spells"],
                    16: ["ASI"],
                    17: ["9th Level Spells"],
                    18: ["Spell Mastery"],
                    19: ["ASI"],
                    20: ["Signature Spells"]
                },
                "spellcasting": {
                    "ability": "intelligence",
                    "type": "full",
                    "ritual_casting": True,
                    "spellbook": True
                },
                "multiclass_requirements": {"intelligence": 13},
                "optimization_bonuses": {
                    "control": 0.95,
                    "versatility": 0.9,
                    "damage": 0.8
                }
            },
            "rogue": {
                "hit_die": 8,
                "primary_stats": ["dexterity"],
                "saving_throws": ["dexterity", "intelligence"],
                "features_by_level": {
                    1: ["Expertise", "Sneak Attack 1d6", "Thieves' Cant"],
                    2: ["Cunning Action"],
                    3: ["Roguish Archetype", "Sneak Attack 2d6"],
                    4: ["ASI"],
                    5: ["Uncanny Dodge", "Sneak Attack 3d6"],
                    6: ["Expertise"],
                    7: ["Evasion", "Sneak Attack 4d6"],
                    8: ["ASI"],
                    9: ["Archetype Feature", "Sneak Attack 5d6"],
                    10: ["ASI"],
                    11: ["Reliable Talent", "Sneak Attack 6d6"],
                    12: ["ASI"],
                    13: ["Archetype Feature", "Sneak Attack 7d6"],
                    14: ["Blindsense"],
                    15: ["Slippery Mind", "Sneak Attack 8d6"],
                    16: ["ASI"],
                    17: ["Archetype Feature", "Sneak Attack 9d6"],
                    18: ["Elusive"],
                    19: ["ASI", "Sneak Attack 10d6"],
                    20: ["Stroke of Luck"]
                },
                "spellcasting": None,
                "multiclass_requirements": {"dexterity": 13},
                "optimization_bonuses": {
                    "damage": 0.85,
                    "versatility": 0.9,
                    "survivability": 0.7
                }
            },
            "paladin": {
                "hit_die": 10,
                "primary_stats": ["strength", "charisma"],
                "saving_throws": ["wisdom", "charisma"],
                "features_by_level": {
                    1: ["Divine Sense", "Lay on Hands"],
                    2: ["Fighting Style", "Spellcasting", "Divine Smite"],
                    3: ["Divine Health", "Sacred Oath"],
                    4: ["ASI"],
                    5: ["Extra Attack"],
                    6: ["Aura of Protection"],
                    7: ["Oath Feature"],
                    8: ["ASI"],
                    9: ["3rd Level Spells"],
                    10: ["Aura of Courage"],
                    11: ["Improved Divine Smite"],
                    12: ["ASI"],
                    13: ["4th Level Spells"],
                    14: ["Cleansing Touch"],
                    15: ["Oath Feature"],
                    16: ["ASI"],
                    17: ["5th Level Spells"],
                    18: ["Aura Improvements"],
                    19: ["ASI"],
                    20: ["Oath Feature"]
                },
                "spellcasting": {
                    "ability": "charisma",
                    "type": "half",
                    "ritual_casting": False
                },
                "multiclass_requirements": {"strength": 13, "charisma": 13},
                "optimization_bonuses": {
                    "survivability": 0.9,
                    "damage": 0.8,
                    "support": 0.7
                }
            },
            "warlock": {
                "hit_die": 8,
                "primary_stats": ["charisma"],
                "saving_throws": ["wisdom", "charisma"],
                "features_by_level": {
                    1: ["Otherworldly Patron", "Pact Magic"],
                    2: ["Eldritch Invocations"],
                    3: ["Pact Boon"],
                    4: ["ASI"],
                    5: ["3rd Level Spells"],
                    6: ["Patron Feature"],
                    7: ["4th Level Spells"],
                    8: ["ASI"],
                    9: ["5th Level Spells"],
                    10: ["Patron Feature"],
                    11: ["Mystic Arcanum (6th)"],
                    12: ["ASI"],
                    13: ["Mystic Arcanum (7th)"],
                    14: ["Patron Feature"],
                    15: ["Mystic Arcanum (8th)"],
                    16: ["ASI"],
                    17: ["Mystic Arcanum (9th)"],
                    18: ["Additional Invocation"],
                    19: ["ASI"],
                    20: ["Eldritch Master"]
                },
                "spellcasting": {
                    "ability": "charisma",
                    "type": "pact",
                    "short_rest_slots": True
                },
                "multiclass_requirements": {"charisma": 13},
                "optimization_bonuses": {
                    "damage": 0.85,
                    "versatility": 0.8,
                    "control": 0.75
                }
            },
            "sorcerer": {
                "hit_die": 6,
                "primary_stats": ["charisma"],
                "saving_throws": ["constitution", "charisma"],
                "features_by_level": {
                    1: ["Spellcasting", "Sorcerous Origin"],
                    2: ["Font of Magic"],
                    3: ["Metamagic", "2nd Level Spells"],
                    4: ["ASI"],
                    5: ["3rd Level Spells"],
                    6: ["Origin Feature"],
                    7: ["4th Level Spells"],
                    8: ["ASI"],
                    9: ["5th Level Spells"],
                    10: ["Metamagic"],
                    11: ["6th Level Spells"],
                    12: ["ASI"],
                    13: ["7th Level Spells"],
                    14: ["Origin Feature"],
                    15: ["8th Level Spells"],
                    16: ["ASI"],
                    17: ["Metamagic", "9th Level Spells"],
                    18: ["Origin Feature"],
                    19: ["ASI"],
                    20: ["Sorcerous Restoration"]
                },
                "spellcasting": {
                    "ability": "charisma",
                    "type": "full",
                    "ritual_casting": False,
                    "known_spells": True
                },
                "multiclass_requirements": {"charisma": 13},
                "optimization_bonuses": {
                    "damage": 0.9,
                    "versatility": 0.8,
                    "control": 0.85
                }
            }
        }
    
    def _build_synergy_matrix(self) -> Dict[Tuple[str, str], float]:
        """Build matrix of class synergy scores"""
        return {
            # Paladin + Warlock (Padlock) - Excellent synergy
            ("paladin", "warlock"): 0.95,
            ("paladin", "hexblade_warlock"): 0.98,  # Hexblade specific
            
            # Fighter + Wizard (Gish builds)
            ("fighter", "wizard"): 0.88,
            ("eldritch_knight", "wizard"): 0.92,
            
            # Rogue + Fighter (Skill/Combat hybrid)
            ("rogue", "fighter"): 0.85,
            ("rogue", "champion_fighter"): 0.87,
            
            # Rogue + Ranger (Stealth/Tracking)
            ("rogue", "ranger"): 0.83,
            
            # Sorcerer + Warlock (Sorclock) - Spell slot conversion
            ("sorcerer", "warlock"): 0.92,
            
            # Barbarian + Fighter (Pure martial)
            ("barbarian", "fighter"): 0.80,
            
            # Cleric + Fighter (Divine warrior)
            ("cleric", "fighter"): 0.85,
            
            # Bard + Warlock (Charisma synergy)
            ("bard", "warlock"): 0.87,
            
            # Wizard + Sorcerer (Meta-magic for wizard)
            ("wizard", "sorcerer"): 0.78,
            
            # Monk + Rogue (Mobile striker)
            ("monk", "rogue"): 0.82,
            
            # Generally poor synergies
            ("barbarian", "wizard"): 0.45,  # Rage prevents spellcasting
            ("barbarian", "sorcerer"): 0.40,
            ("monk", "heavy_armor_class"): 0.30,  # Unarmored defense conflict
        }
    
    def _load_feat_database(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive feat database"""
        return {
            "great_weapon_master": {
                "prerequisites": ["strength_based_melee"],
                "benefits": {
                    "damage_bonus": 10,
                    "attack_penalty": -5,
                    "special": "bonus_action_attack_on_crit_or_kill"
                },
                "synergy_classes": ["fighter", "barbarian", "paladin"],
                "optimization_value": 0.85
            },
            "sharpshooter": {
                "prerequisites": ["ranged_weapon_proficiency"],
                "benefits": {
                    "damage_bonus": 10,
                    "attack_penalty": -5,
                    "ignore_cover": True,
                    "range_penalty_ignored": True
                },
                "synergy_classes": ["fighter", "ranger", "rogue"],
                "optimization_value": 0.90
            },
            "polearm_master": {
                "prerequisites": ["polearm_proficiency"],
                "benefits": {
                    "bonus_action_attack": "1d4+str",
                    "opportunity_attack_on_enter": True
                },
                "synergy_classes": ["fighter", "paladin"],
                "combos": ["sentinel", "great_weapon_master"],
                "optimization_value": 0.88
            },
            "sentinel": {
                "prerequisites": None,
                "benefits": {
                    "stop_movement_on_opportunity_attack": True,
                    "opportunity_attack_when_ally_attacked": True,
                    "reaction_attack_on_disengage": True
                },
                "synergy_classes": ["fighter", "paladin", "barbarian"],
                "combos": ["polearm_master"],
                "optimization_value": 0.82
            },
            "war_caster": {
                "prerequisites": ["spellcasting"],
                "benefits": {
                    "advantage_on_concentration_saves": True,
                    "somatic_components_with_weapon_shield": True,
                    "spell_opportunity_attacks": True
                },
                "synergy_classes": ["paladin", "eldritch_knight", "ranger"],
                "optimization_value": 0.75
            },
            "metamagic_adept": {
                "prerequisites": ["spellcasting"],
                "benefits": {
                    "sorcery_points": 2,
                    "metamagic_options": 2
                },
                "synergy_classes": ["sorcerer", "multiclass_casters"],
                "optimization_value": 0.80
            },
            "eldritch_adept": {
                "prerequisites": ["spellcasting_or_pact_magic"],
                "benefits": {
                    "eldritch_invocation": 1
                },
                "synergy_classes": ["warlock", "multiclass_with_warlock"],
                "optimization_value": 0.70
            },
            "lucky": {
                "prerequisites": None,
                "benefits": {
                    "luck_points": 3,
                    "reroll_any_d20": True
                },
                "synergy_classes": ["all"],
                "optimization_value": 0.85
            },
            "alert": {
                "prerequisites": None,
                "benefits": {
                    "initiative_bonus": 5,
                    "no_surprise": True,
                    "no_advantage_when_unseen": True
                },
                "synergy_classes": ["rogue", "dexterity_builds"],
                "optimization_value": 0.65
            }
        }
    
    def _load_optimization_weights(self) -> Dict[OptimizationGoal, Dict[str, float]]:
        """Load optimization weights for different goals"""
        return {
            OptimizationGoal.DAMAGE: {
                "attack_bonus": 0.25,
                "damage_per_round": 0.35,
                "critical_chance": 0.15,
                "action_economy": 0.20,
                "spell_damage": 0.25,
                "survivability": 0.10
            },
            OptimizationGoal.SURVIVABILITY: {
                "hp": 0.30,
                "ac": 0.25,
                "saving_throws": 0.20,
                "damage_resistance": 0.15,
                "healing": 0.10,
                "mobility": 0.10
            },
            OptimizationGoal.VERSATILITY: {
                "skill_coverage": 0.25,
                "spell_variety": 0.25,
                "combat_options": 0.20,
                "social_abilities": 0.15,
                "utility_spells": 0.15,
                "problem_solving": 0.20
            },
            OptimizationGoal.CONTROL: {
                "battlefield_control": 0.40,
                "save_or_die": 0.30,
                "movement_restriction": 0.20,
                "action_denial": 0.25,
                "spell_dc": 0.15
            },
            OptimizationGoal.SUPPORT: {
                "healing_output": 0.30,
                "buff_spells": 0.25,
                "team_synergy": 0.20,
                "utility_casting": 0.15,
                "resource_sharing": 0.10
            }
        }
    
    def generate_optimal_multiclass_builds(self, level: int, goal: OptimizationGoal, 
                                         constraints: Dict[str, Any] = None) -> List[MulticlassBuild]:
        """Generate optimal multiclass builds for given parameters"""
        
        constraints = constraints or {}
        max_builds = constraints.get("max_builds", 5)
        min_classes = constraints.get("min_classes", 2)
        max_classes = constraints.get("max_classes", 3)
        allowed_classes = constraints.get("allowed_classes", list(self.class_data.keys()))
        
        # Generate all possible class combinations
        builds = []
        
        for num_classes in range(min_classes, max_classes + 1):
            for class_combo in itertools.combinations(allowed_classes, num_classes):
                # Generate level distributions
                level_distributions = self._generate_level_distributions(class_combo, level)
                
                for distribution in level_distributions:
                    build = self._create_multiclass_build(class_combo, distribution, goal, level)
                    if build and self._meets_constraints(build, constraints):
                        builds.append(build)
        
        # Sort by optimization score and return top builds
        builds.sort(key=lambda b: b.optimization_score, reverse=True)
        return builds[:max_builds]
    
    def _generate_level_distributions(self, classes: Tuple[str], total_level: int) -> List[Dict[str, int]]:
        """Generate viable level distributions for class combination"""
        distributions = []
        
        # Generate all possible distributions
        if len(classes) == 2:
            # Two classes - try various splits
            for primary_levels in range(1, total_level):
                secondary_levels = total_level - primary_levels
                if secondary_levels >= 1:  # Minimum 1 level in each class
                    distributions.append({
                        classes[0]: primary_levels,
                        classes[1]: secondary_levels
                    })
        
        elif len(classes) == 3:
            # Three classes - more complex
            for primary_levels in range(1, total_level - 1):
                for secondary_levels in range(1, total_level - primary_levels):
                    tertiary_levels = total_level - primary_levels - secondary_levels
                    if tertiary_levels >= 1:
                        distributions.append({
                            classes[0]: primary_levels,
                            classes[1]: secondary_levels,
                            classes[2]: tertiary_levels
                        })
        
        # Filter out distributions that don't make sense
        filtered = []
        for dist in distributions:
            if self._is_viable_distribution(dist):
                filtered.append(dist)
        
        # Limit to most promising distributions to avoid combinatorial explosion
        return filtered[:20]  # Top 20 distributions per combination
    
    def _is_viable_distribution(self, distribution: Dict[str, int]) -> bool:
        """Check if level distribution is viable"""
        
        # Don't allow too many single-level dips without purpose
        single_dips = sum(1 for levels in distribution.values() if levels == 1)
        if single_dips > 1:
            return False
        
        # Ensure at least one class has substantial investment (5+ levels)
        if not any(levels >= 5 for levels in distribution.values()):
            return False
        
        # Check for spellcaster viability
        spellcaster_levels = 0
        for class_name, levels in distribution.items():
            if self.class_data[class_name].get("spellcasting"):
                spellcaster_levels += levels
        
        # If multiclass spellcasting, ensure reasonable progression
        if spellcaster_levels > 0 and spellcaster_levels < 3:
            spellcaster_classes = [c for c in distribution.keys() 
                                 if self.class_data[c].get("spellcasting")]
            if len(spellcaster_classes) > 1:
                return False  # Avoid very light spellcaster multiclassing
        
        return True
    
    def _create_multiclass_build(self, classes: Tuple[str], distribution: Dict[str, int], 
                               goal: OptimizationGoal, total_level: int) -> Optional[MulticlassBuild]:
        """Create optimized multiclass build"""
        
        try:
            # Check multiclass requirements
            required_stats = self._calculate_multiclass_requirements(classes)
            
            # Generate optimal ability scores
            ability_scores = self._optimize_ability_scores(classes, distribution, goal, required_stats)
            
            # Generate class progressions
            class_progressions = []
            for class_name in classes:
                progression = ClassProgression(
                    class_name=class_name,
                    levels=distribution[class_name],
                    features_gained=self._get_features_for_levels(class_name, distribution[class_name]),
                    asi_levels=self._get_asi_levels(class_name, distribution[class_name])
                )
                class_progressions.append(progression)
            
            # Generate feat progression
            feat_progression = self._optimize_feat_progression(classes, distribution, goal, total_level)
            
            # Generate level-by-level progression
            level_progression = self._optimize_level_progression(classes, distribution, total_level)
            
            # Calculate synergy ratings
            synergy_ratings = self._calculate_synergy_ratings(classes, distribution)
            
            # Calculate optimization score
            optimization_score = self._calculate_optimization_score(
                classes, distribution, ability_scores, feat_progression, goal
            )
            
            # Generate strengths and weaknesses
            strengths, weaknesses = self._analyze_build_strengths_weaknesses(
                classes, distribution, goal
            )
            
            # Select optimal race
            optimal_race = self._select_optimal_race(classes, ability_scores, goal)
            
            # Select optimal background
            optimal_background = self._select_optimal_background(classes, goal)
            
            build = MulticlassBuild(
                name=self._generate_build_name(classes, distribution, goal),
                race=optimal_race,
                background=optimal_background,
                classes=class_progressions,
                ability_scores=ability_scores,
                feat_progression=feat_progression,
                spell_selection={},  # Would be populated with spell optimization
                optimization_score=optimization_score,
                synergy_ratings=synergy_ratings,
                level_progression=level_progression,
                strengths=strengths,
                weaknesses=weaknesses,
                recommended_stats=required_stats
            )
            
            return build
            
        except Exception as e:
            # If build creation fails, skip this combination
            return None
    
    def _calculate_multiclass_requirements(self, classes: Tuple[str]) -> Dict[str, int]:
        """Calculate minimum ability score requirements for multiclass"""
        requirements = {}
        
        for class_name in classes:
            class_reqs = self.class_data[class_name].get("multiclass_requirements", {})
            for stat, min_value in class_reqs.items():
                requirements[stat] = max(requirements.get(stat, 13), min_value)
        
        return requirements
    
    def _optimize_ability_scores(self, classes: Tuple[str], distribution: Dict[str, int], 
                                goal: OptimizationGoal, required_stats: Dict[str, int]) -> Dict[str, int]:
        """Generate optimal ability score array"""
        
        # Start with standard array
        base_scores = [15, 14, 13, 12, 10, 8]
        abilities = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
        
        # Determine priority order based on classes and goal
        priority_order = self._determine_ability_priority(classes, distribution, goal)
        
        # Assign scores in priority order
        ability_scores = {}
        for i, ability in enumerate(priority_order):
            ability_scores[ability] = base_scores[i] if i < len(base_scores) else 8
        
        # Ensure multiclass requirements are met
        for stat, min_value in required_stats.items():
            if ability_scores.get(stat, 8) < min_value:
                # Find lowest non-required stat to swap with
                for swap_stat, score in ability_scores.items():
                    if (swap_stat not in required_stats and 
                        score >= min_value and 
                        ability_scores[stat] < min_value):
                        ability_scores[stat], ability_scores[swap_stat] = score, ability_scores[stat]
                        break
        
        return ability_scores
    
    def _determine_ability_priority(self, classes: Tuple[str], distribution: Dict[str, int], 
                                  goal: OptimizationGoal) -> List[str]:
        """Determine ability score priority for optimization"""
        
        # Weight abilities based on class primary stats and levels
        ability_weights = {
            "strength": 0, "dexterity": 0, "constitution": 0,
            "intelligence": 0, "wisdom": 0, "charisma": 0
        }
        
        for class_name, levels in distribution.items():
            class_info = self.class_data[class_name]
            primary_stats = class_info.get("primary_stats", [])
            
            # Weight primary stats by class levels
            for stat in primary_stats:
                ability_weights[stat] += levels * 2
        
        # Constitution is always important
        ability_weights["constitution"] += sum(distribution.values()) * 0.8
        
        # Adjust weights based on optimization goal
        if goal == OptimizationGoal.DAMAGE:
            # Prioritize offensive stats
            for class_name in classes:
                primary_stats = self.class_data[class_name].get("primary_stats", [])
                for stat in primary_stats:
                    if stat in ["strength", "dexterity", "charisma", "intelligence", "wisdom"]:
                        ability_weights[stat] *= 1.3
        
        elif goal == OptimizationGoal.SURVIVABILITY:
            ability_weights["constitution"] *= 1.5
            ability_weights["dexterity"] *= 1.2  # AC and saves
        
        elif goal == OptimizationGoal.VERSATILITY:
            # More balanced approach
            for stat in ability_weights:
                ability_weights[stat] *= 1.1
        
        # Sort by weight
        return sorted(ability_weights.keys(), key=lambda s: ability_weights[s], reverse=True)
    
    def _get_features_for_levels(self, class_name: str, levels: int) -> Dict[int, List[str]]:
        """Get features gained for specific class levels"""
        features = {}
        class_features = self.class_data[class_name].get("features_by_level", {})
        
        for level in range(1, levels + 1):
            if level in class_features:
                features[level] = class_features[level].copy()
        
        return features
    
    def _get_asi_levels(self, class_name: str, levels: int) -> List[int]:
        """Get ASI levels for class"""
        asi_levels = []
        
        # Most classes get ASI at 4, 8, 12, 16, 19
        for level in [4, 8, 12, 16, 19]:
            if level <= levels:
                asi_levels.append(level)
        
        # Fighter gets additional ASIs
        if class_name == "fighter":
            for level in [6, 14]:
                if level <= levels:
                    asi_levels.append(level)
        
        return sorted(asi_levels)
    
    def _optimize_feat_progression(self, classes: Tuple[str], distribution: Dict[str, int], 
                                 goal: OptimizationGoal, total_level: int) -> Dict[int, str]:
        """Optimize feat selection progression"""
        
        feat_progression = {}
        
        # Calculate total ASIs available
        total_asi_levels = []
        for class_name, levels in distribution.items():
            class_asi_levels = self._get_asi_levels(class_name, levels)
            for level in class_asi_levels:
                # Convert class level to character level (simplified)
                char_level = self._convert_to_character_level(class_name, level, distribution)
                if char_level <= total_level:
                    total_asi_levels.append(char_level)
        
        total_asi_levels = sorted(list(set(total_asi_levels)))
        
        # Prioritize feats based on synergy with classes and goal
        feat_priorities = self._calculate_feat_priorities(classes, distribution, goal)
        
        # Assign feats (mix of feats and ability score increases)
        asi_count = 0
        for level in total_asi_levels:
            if asi_count < 2:  # First two ASIs for ability scores
                feat_progression[level] = "ability_score_improvement"
                asi_count += 1
            else:
                # Select best available feat
                available_feats = [f for f in feat_priorities if f not in feat_progression.values()]
                if available_feats:
                    feat_progression[level] = available_feats[0]
                else:
                    feat_progression[level] = "ability_score_improvement"
        
        return feat_progression
    
    def _convert_to_character_level(self, class_name: str, class_level: int, 
                                  distribution: Dict[str, int]) -> int:
        """Convert class level to estimated character level (simplified)"""
        # This is a simplified conversion - would need more complex logic for exact mapping
        total_levels = sum(distribution.values())
        class_levels = distribution[class_name]
        
        # Approximate character level when this class level is reached
        return int((class_level / class_levels) * total_levels)
    
    def _calculate_feat_priorities(self, classes: Tuple[str], distribution: Dict[str, int], 
                                 goal: OptimizationGoal) -> List[str]:
        """Calculate feat priorities for build"""
        
        feat_scores = {}
        
        for feat_name, feat_data in self.feat_database.items():
            score = feat_data.get("optimization_value", 0.5)
            
            # Check synergy with classes
            synergy_classes = feat_data.get("synergy_classes", [])
            for class_name in classes:
                if class_name in synergy_classes or "all" in synergy_classes:
                    score += 0.2 * distribution.get(class_name, 0)
            
            # Check for combos with other feats
            combos = feat_data.get("combos", [])
            if combos:
                score += 0.1  # Bonus for combo potential
            
            # Goal-specific bonuses
            if goal == OptimizationGoal.DAMAGE:
                if "damage_bonus" in feat_data.get("benefits", {}):
                    score += 0.3
            elif goal == OptimizationGoal.SURVIVABILITY:
                if any(key in feat_data.get("benefits", {}) for key in ["ac_bonus", "hp_bonus", "saves"]):
                    score += 0.3
            
            feat_scores[feat_name] = score
        
        # Sort by score
        return sorted(feat_scores.keys(), key=lambda f: feat_scores[f], reverse=True)
    
    def _optimize_level_progression(self, classes: Tuple[str], distribution: Dict[str, int], 
                                  total_level: int) -> List[str]:
        """Determine optimal order to take class levels"""
        
        progression = []
        remaining_levels = distribution.copy()
        
        # Start with the primary class (highest level investment)
        primary_class = max(distribution.keys(), key=lambda c: distribution[c])
        
        # Take first level in primary class
        progression.append(primary_class)
        remaining_levels[primary_class] -= 1
        
        # Continue with strategic progression
        for level in range(2, total_level + 1):
            next_class = self._select_next_level(progression, remaining_levels, level)
            if next_class:
                progression.append(next_class)
                remaining_levels[next_class] -= 1
        
        return progression
    
    def _select_next_level(self, current_progression: List[str], 
                          remaining_levels: Dict[str, int], level: int) -> Optional[str]:
        """Select next class level based on optimization"""
        
        available_classes = [c for c, levels in remaining_levels.items() if levels > 0]
        if not available_classes:
            return None
        
        # Prioritize based on key breakpoints
        class_scores = {}
        
        for class_name in available_classes:
            score = 0
            current_class_level = current_progression.count(class_name) + 1
            
            # Check for important breakpoints
            if self._is_important_breakpoint(class_name, current_class_level):
                score += 2
            
            # Prefer continuing primary class for core features
            if current_class_level <= 5:
                score += 1
            
            # Avoid excessive level splitting early
            if level <= 5 and current_class_level == 1:
                score -= 1
            
            class_scores[class_name] = score
        
        return max(class_scores.keys(), key=lambda c: class_scores[c])
    
    def _is_important_breakpoint(self, class_name: str, level: int) -> bool:
        """Check if class level is an important breakpoint"""
        
        important_levels = {
            "fighter": [2, 5, 11],  # Action Surge, Extra Attack, Extra Attack 2
            "wizard": [2, 3, 5, 9, 17],  # School, 2nd spells, 3rd spells, 5th spells, 9th spells
            "rogue": [2, 3],  # Cunning Action, Archetype
            "paladin": [2, 5, 6],  # Smite, Extra Attack, Aura
            "warlock": [2, 3, 5],  # Invocations, Pact Boon, 3rd level spells
            "sorcerer": [2, 3, 5]  # Font of Magic, Metamagic, 3rd level spells
        }
        
        return level in important_levels.get(class_name, [])
    
    def _calculate_synergy_ratings(self, classes: Tuple[str], distribution: Dict[str, int]) -> Dict[str, float]:
        """Calculate synergy ratings between classes"""
        
        synergy_ratings = {}
        
        # Pairwise synergies
        for i, class1 in enumerate(classes):
            for class2 in classes[i+1:]:
                synergy_key = f"{class1}+{class2}"
                
                # Look up synergy in matrix
                synergy_score = self.synergy_matrix.get((class1, class2), 0.5)
                if synergy_score == 0.5:  # Try reverse order
                    synergy_score = self.synergy_matrix.get((class2, class1), 0.5)
                
                # Adjust for level distribution
                min_levels = min(distribution[class1], distribution[class2])
                max_levels = max(distribution[class1], distribution[class2])
                
                # Penalize very uneven splits
                balance_factor = min_levels / max_levels
                if balance_factor < 0.2:  # Very uneven split
                    synergy_score *= 0.8
                
                synergy_ratings[synergy_key] = synergy_score
        
        # Overall synergy
        if synergy_ratings:
            synergy_ratings["overall"] = sum(synergy_ratings.values()) / len(synergy_ratings)
        else:
            synergy_ratings["overall"] = 0.5
        
        return synergy_ratings
    
    def _calculate_optimization_score(self, classes: Tuple[str], distribution: Dict[str, int],
                                    ability_scores: Dict[str, int], feat_progression: Dict[int, str],
                                    goal: OptimizationGoal) -> float:
        """Calculate overall optimization score for build"""
        
        base_score = 0.5
        
        # Class synergy contribution (30%)
        synergy_ratings = self._calculate_synergy_ratings(classes, distribution)
        synergy_score = synergy_ratings.get("overall", 0.5)
        base_score += synergy_score * 0.3
        
        # Goal-specific optimization (40%)
        goal_score = self._calculate_goal_score(classes, distribution, ability_scores, goal)
        base_score += goal_score * 0.4
        
        # Feat synergy (15%)
        feat_score = self._calculate_feat_synergy_score(feat_progression, classes)
        base_score += feat_score * 0.15
        
        # Level progression efficiency (15%)
        progression_score = self._calculate_progression_efficiency(classes, distribution)
        base_score += progression_score * 0.15
        
        return min(1.0, base_score)
    
    def _calculate_goal_score(self, classes: Tuple[str], distribution: Dict[str, int],
                            ability_scores: Dict[str, int], goal: OptimizationGoal) -> float:
        """Calculate score based on optimization goal"""
        
        score = 0.5
        
        for class_name, levels in distribution.items():
            class_data = self.class_data[class_name]
            optimization_bonuses = class_data.get("optimization_bonuses", {})
            
            # Get bonus for this goal
            goal_bonus = optimization_bonuses.get(goal.value, 0.5)
            
            # Weight by levels in class
            level_weight = levels / sum(distribution.values())
            score += goal_bonus * level_weight
        
        return min(1.0, score)
    
    def _calculate_feat_synergy_score(self, feat_progression: Dict[int, str], classes: Tuple[str]) -> float:
        """Calculate how well feats synergize with build"""
        
        if not feat_progression:
            return 0.5
        
        synergy_score = 0
        feat_count = 0
        
        for feat_name in feat_progression.values():
            if feat_name == "ability_score_improvement":
                continue
            
            feat_count += 1
            feat_data = self.feat_database.get(feat_name, {})
            synergy_classes = feat_data.get("synergy_classes", [])
            
            # Check synergy with classes
            class_synergy = sum(1 for c in classes if c in synergy_classes or "all" in synergy_classes)
            synergy_score += class_synergy / len(classes)
        
        return synergy_score / max(feat_count, 1)
    
    def _calculate_progression_efficiency(self, classes: Tuple[str], distribution: Dict[str, int]) -> float:
        """Calculate efficiency of level progression"""
        
        # Penalize excessive multiclassing without purpose
        if len(classes) > 2:
            return 0.3
        
        # Check for balanced investment
        levels = list(distribution.values())
        max_levels = max(levels)
        min_levels = min(levels)
        
        balance_ratio = min_levels / max_levels
        
        # Sweet spot is around 0.3-0.7 ratio
        if 0.3 <= balance_ratio <= 0.7:
            return 0.8
        elif balance_ratio < 0.2:  # Very uneven
            return 0.4
        else:  # Too even
            return 0.6
    
    def _analyze_build_strengths_weaknesses(self, classes: Tuple[str], distribution: Dict[str, int],
                                          goal: OptimizationGoal) -> Tuple[List[str], List[str]]:
        """Analyze build strengths and weaknesses"""
        
        strengths = []
        weaknesses = []
        
        # Analyze class combinations
        if "paladin" in classes and "warlock" in classes:
            strengths.extend([
                "Excellent nova damage with smite + spell slots",
                "Strong survivability with heavy armor + healing",
                "Charisma-based attacks and spells"
            ])
            weaknesses.extend([
                "Limited spell slots without short rests",
                "Multiple attribute dependency"
            ])
        
        if "fighter" in classes and "wizard" in classes:
            strengths.extend([
                "Action Surge for extra spells per turn",
                "Heavy armor for wizard survivability", 
                "Versatile in combat and utility"
            ])
            weaknesses.extend([
                "Delayed spell progression",
                "Multiple attribute dependency"
            ])
        
        if "sorcerer" in classes and "warlock" in classes:
            strengths.extend([
                "Spell slot conversion for more sorcery points",
                "Eldritch Blast + Metamagic combinations",
                "Excellent short rest recovery"
            ])
            weaknesses.extend([
                "Limited spells known",
                "Fragile in early levels"
            ])
        
        # General multiclass considerations
        if len(classes) > 2:
            weaknesses.append("Complex resource management")
            
        total_caster_levels = sum(distribution.get(c, 0) for c in classes 
                                if self.class_data[c].get("spellcasting"))
        if total_caster_levels > 0:
            if total_caster_levels >= 15:
                strengths.append("High-level spell access")
            elif total_caster_levels < 5:
                weaknesses.append("Limited spellcasting progression")
        
        return strengths, weaknesses
    
    def _select_optimal_race(self, classes: Tuple[str], ability_scores: Dict[str, int], 
                           goal: OptimizationGoal) -> str:
        """Select optimal race for build"""
        
        race_synergies = {
            ("paladin", "warlock"): "dragonborn",
            ("fighter", "wizard"): "variant_human",
            ("sorcerer", "warlock"): "tiefling",
            ("rogue", "fighter"): "half_elf"
        }
        
        # Check for specific synergies
        for class_combo, race in race_synergies.items():
            if all(c in classes for c in class_combo):
                return race
        
        # Default recommendations based on primary stats
        primary_stats = []
        for class_name in classes:
            primary_stats.extend(self.class_data[class_name].get("primary_stats", []))
        
        if "charisma" in primary_stats:
            return "tiefling" if goal == OptimizationGoal.DAMAGE else "half_elf"
        elif "intelligence" in primary_stats:
            return "variant_human"
        elif "dexterity" in primary_stats:
            return "wood_elf"
        else:
            return "variant_human"  # Always solid choice
    
    def _select_optimal_background(self, classes: Tuple[str], goal: OptimizationGoal) -> str:
        """Select optimal background for build"""
        
        if any(c in ["wizard", "sorcerer", "warlock"] for c in classes):
            return "sage"
        elif any(c in ["fighter", "paladin", "ranger"] for c in classes):
            return "soldier"
        elif "rogue" in classes:
            return "criminal"
        else:
            return "folk_hero"
    
    def _generate_build_name(self, classes: Tuple[str], distribution: Dict[str, int], 
                           goal: OptimizationGoal) -> str:
        """Generate descriptive name for build"""
        
        # Known build names
        if set(classes) == {"paladin", "warlock"}:
            return f"Paladin/Warlock (Pallock) - {goal.value.title()}"
        elif set(classes) == {"fighter", "wizard"}:
            return f"Fighter/Wizard (Eldritch Knight+) - {goal.value.title()}"
        elif set(classes) == {"sorcerer", "warlock"}:
            return f"Sorcerer/Warlock (Sorlock) - {goal.value.title()}"
        elif set(classes) == {"rogue", "fighter"}:
            return f"Rogue/Fighter (Scout) - {goal.value.title()}"
        else:
            # Generic naming
            class_names = "/".join(c.title() for c in classes)
            return f"{class_names} - {goal.value.title()}"
    
    def _meets_constraints(self, build: MulticlassBuild, constraints: Dict[str, Any]) -> bool:
        """Check if build meets user constraints"""
        
        # Banned classes
        banned_classes = constraints.get("banned_classes", [])
        if any(prog.class_name in banned_classes for prog in build.classes):
            return False
        
        # Minimum optimization score
        min_score = constraints.get("min_optimization_score", 0.0)
        if build.optimization_score < min_score:
            return False
        
        # Required race
        required_race = constraints.get("required_race")
        if required_race and build.race != required_race:
            return False
        
        return True
    
    def analyze_existing_build(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an existing character build for optimization opportunities"""
        
        level = character_data.get("level", 1)
        classes = character_data.get("classes", [])
        ability_scores = character_data.get("ability_scores", {})
        
        # Convert to internal format
        class_distribution = {}
        for class_info in classes:
            class_name = class_info.get("name", "").lower()
            class_levels = class_info.get("levels", 0)
            class_distribution[class_name] = class_levels
        
        analysis = {
            "current_optimization_score": 0.5,
            "synergy_analysis": {},
            "improvement_opportunities": [],
            "alternative_builds": [],
            "feat_recommendations": [],
            "multiclass_suggestions": []
        }
        
        if len(class_distribution) > 1:
            # Analyze multiclass synergies
            class_tuple = tuple(class_distribution.keys())
            synergy_ratings = self._calculate_synergy_ratings(class_tuple, class_distribution)
            analysis["synergy_analysis"] = synergy_ratings
            
            # Calculate current optimization score
            goal = OptimizationGoal.DAMAGE  # Default assumption
            current_score = self._calculate_optimization_score(
                class_tuple, class_distribution, ability_scores, {}, goal
            )
            analysis["current_optimization_score"] = current_score
            
            # Generate improvement suggestions
            if current_score < 0.7:
                analysis["improvement_opportunities"].extend([
                    "Consider rebalancing level distribution",
                    "Optimize ability score allocation",
                    "Select feats that synergize with class combination"
                ])
        
        else:
            # Single class - suggest multiclass options
            primary_class = list(class_distribution.keys())[0]
            multiclass_options = self._suggest_multiclass_options(primary_class, level)
            analysis["multiclass_suggestions"] = multiclass_options
        
        return analysis
    
    def _suggest_multiclass_options(self, primary_class: str, level: int) -> List[Dict[str, Any]]:
        """Suggest multiclass options for single-class character"""
        
        suggestions = []
        
        # Known good multiclass combinations
        good_combos = {
            "paladin": ["warlock", "sorcerer", "fighter"],
            "fighter": ["wizard", "rogue", "ranger"],
            "rogue": ["fighter", "ranger", "bard"],
            "wizard": ["fighter", "cleric", "sorcerer"],
            "sorcerer": ["warlock", "paladin", "bard"],
            "warlock": ["paladin", "sorcerer", "fighter"]
        }
        
        if primary_class in good_combos:
            for secondary_class in good_combos[primary_class]:
                synergy_score = self.synergy_matrix.get((primary_class, secondary_class), 0.5)
                
                suggestions.append({
                    "secondary_class": secondary_class,
                    "synergy_score": synergy_score,
                    "suggested_split": self._suggest_level_split(primary_class, secondary_class, level),
                    "benefits": self._describe_multiclass_benefits(primary_class, secondary_class)
                })
        
        # Sort by synergy score
        suggestions.sort(key=lambda s: s["synergy_score"], reverse=True)
        return suggestions[:3]  # Top 3 suggestions
    
    def _suggest_level_split(self, primary_class: str, secondary_class: str, total_level: int) -> str:
        """Suggest optimal level split for multiclass"""
        
        # Common optimal splits
        optimal_splits = {
            ("paladin", "warlock"): "14/6 or 17/3",
            ("fighter", "wizard"): "17/3 or 15/5", 
            ("sorcerer", "warlock"): "17/3 or 14/6",
            ("rogue", "fighter"): "17/3 or 15/5"
        }
        
        combo_key = (primary_class, secondary_class)
        return optimal_splits.get(combo_key, f"{total_level-3}/3 for dip, or balanced split")
    
    def _describe_multiclass_benefits(self, primary_class: str, secondary_class: str) -> List[str]:
        """Describe benefits of specific multiclass combination"""
        
        benefits = {
            ("paladin", "warlock"): [
                "Charisma-based attacks and spells",
                "Short rest spell slots for Divine Smite",
                "Eldritch Blast for ranged damage"
            ],
            ("fighter", "wizard"): [
                "Action Surge for extra spells",
                "Heavy armor proficiency for survivability",
                "Martial weapons + cantrips"
            ],
            ("sorcerer", "warlock"): [
                "Spell slot conversion mechanics",
                "Metamagic on Eldritch Blast",
                "Excellent short rest recovery"
            ],
            ("rogue", "fighter"): [
                "Fighting Style for weapon mastery",
                "Action Surge for extra Sneak Attack chances",
                "Second Wind for survivability"
            ]
        }
        
        combo_key = (primary_class, secondary_class)
        return benefits.get(combo_key, ["Enhanced versatility", "Complementary abilities"])
    
    def export_build_guide(self, build: MulticlassBuild) -> str:
        """Export comprehensive build guide as formatted text"""
        
        guide = f"""
# {build.name}

## Overview
**Race:** {build.race.replace('_', ' ').title()}
**Background:** {build.background.replace('_', ' ').title()}
**Optimization Score:** {build.optimization_score:.1%}

## Class Distribution
{chr(10).join(f"- {prog.class_name.title()}: {prog.levels} levels" for prog in build.classes)}

## Ability Scores (Point Buy)
{chr(10).join(f"- {stat.title()}: {score}" for stat, score in sorted(build.ability_scores.items()))}

## Level Progression
{chr(10).join(f"Level {i+1}: {cls.title()}" for i, cls in enumerate(build.level_progression))}

## Feat Recommendations
{chr(10).join(f"Level {level}: {feat.replace('_', ' ').title()}" for level, feat in sorted(build.feat_progression.items()))}

## Strengths
{chr(10).join(f"- {strength}" for strength in build.strengths)}

## Weaknesses
{chr(10).join(f"- {weakness}" for weakness in build.weaknesses)}

## Synergy Analysis
{chr(10).join(f"- {combo}: {rating:.1%}" for combo, rating in build.synergy_ratings.items())}

## Play Style Tips
This build excels at {build.optimization_score:.0%} efficiency in its intended role. 
Focus on the synergies between your class features and maintain proper resource management.
        """.strip()
        
        return guide