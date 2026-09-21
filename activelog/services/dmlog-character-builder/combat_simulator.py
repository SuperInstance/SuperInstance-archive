"""
Advanced Combat Simulator for Build Testing
Comprehensive combat simulation engine for testing character builds
against various encounter types and difficulty levels
"""

import random
import math
from typing import Dict, List, Any, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import json

class ActionType(Enum):
    ATTACK = "attack"
    SPELL = "spell"
    MOVE = "move"
    DODGE = "dodge"
    HELP = "help"
    DASH = "dash"
    HIDE = "hide"
    READY = "ready"

class DamageType(Enum):
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    THUNDER = "thunder"
    ACID = "acid"
    POISON = "poison"
    NECROTIC = "necrotic"
    RADIANT = "radiant"
    PSYCHIC = "psychic"
    FORCE = "force"

@dataclass
class CombatStats:
    hp: int
    max_hp: int
    ac: int
    speed: int
    initiative: int
    
    # Ability scores
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    
    # Saves
    saving_throws: Dict[str, int] = field(default_factory=dict)
    
    # Skills
    skills: Dict[str, int] = field(default_factory=dict)
    
    # Resistances and immunities
    damage_resistances: List[str] = field(default_factory=list)
    damage_immunities: List[str] = field(default_factory=list)
    condition_immunities: List[str] = field(default_factory=list)
    
    # Combat modifiers
    proficiency_bonus: int = 2
    spell_save_dc: int = 8
    spell_attack_bonus: int = 0
    
    def get_modifier(self, ability: str) -> int:
        """Get ability modifier"""
        score = getattr(self, ability.lower(), 10)
        return (score - 10) // 2
    
    def get_save_modifier(self, ability: str) -> int:
        """Get saving throw modifier"""
        base_mod = self.get_modifier(ability)
        proficient_mod = self.saving_throws.get(ability.lower(), 0)
        return base_mod + proficient_mod

@dataclass
class Attack:
    name: str
    attack_bonus: int
    damage_dice: str  # e.g., "1d8+3"
    damage_type: DamageType
    range: int = 5  # feet
    additional_effects: List[str] = field(default_factory=list)
    crit_range: int = 20  # Natural 20 or higher crits
    
    def roll_attack(self) -> int:
        """Roll attack roll"""
        return random.randint(1, 20) + self.attack_bonus
    
    def roll_damage(self, is_crit: bool = False) -> int:
        """Roll damage"""
        # Parse dice string (simplified)
        parts = self.damage_dice.split('+')
        dice_part = parts[0]  # e.g., "1d8"
        modifier = int(parts[1]) if len(parts) > 1 else 0
        
        if 'd' in dice_part:
            num_dice, die_size = map(int, dice_part.split('d'))
        else:
            num_dice, die_size = 0, 0
            modifier += int(dice_part)
        
        total_damage = 0
        
        # Roll normal damage
        for _ in range(num_dice):
            total_damage += random.randint(1, die_size)
        
        # Double dice on crit
        if is_crit:
            for _ in range(num_dice):
                total_damage += random.randint(1, die_size)
        
        return total_damage + modifier

@dataclass
class Spell:
    name: str
    level: int
    school: str
    casting_time: str
    range: str
    duration: str
    damage: Optional[str] = None
    save_type: Optional[str] = None
    attack_spell: bool = False
    area_effect: bool = False
    healing: Optional[str] = None
    effects: List[str] = field(default_factory=list)
    
    def cast(self, caster_stats: CombatStats, target_ac: int = None) -> Dict[str, Any]:
        """Cast the spell and return results"""
        result = {"spell": self.name, "success": True, "effects": []}
        
        if self.attack_spell and target_ac:
            # Spell attack
            attack_roll = random.randint(1, 20) + caster_stats.spell_attack_bonus
            hit = attack_roll >= target_ac
            result["attack_roll"] = attack_roll
            result["hit"] = hit
            
            if hit and self.damage:
                damage = self._roll_spell_damage()
                result["damage"] = damage
                result["effects"].append(f"Deals {damage} damage")
        
        elif self.save_type:
            # Saving throw spell
            save_dc = caster_stats.spell_save_dc
            result["save_dc"] = save_dc
            result["effects"].append(f"Target must make {self.save_type} save (DC {save_dc})")
            
            if self.damage:
                damage = self._roll_spell_damage()
                result["damage_on_fail"] = damage
                result["damage_on_save"] = damage // 2
        
        elif self.healing:
            # Healing spell
            healing = self._roll_healing()
            result["healing"] = healing
            result["effects"].append(f"Heals {healing} HP")
        
        # Add spell effects
        result["effects"].extend(self.effects)
        
        return result
    
    def _roll_spell_damage(self) -> int:
        """Roll spell damage"""
        if not self.damage:
            return 0
        
        # Simplified damage parsing
        if 'd' in self.damage:
            num_dice, die_size = map(int, self.damage.split('d'))
            total = 0
            for _ in range(num_dice):
                total += random.randint(1, die_size)
            return total
        else:
            return int(self.damage)
    
    def _roll_healing(self) -> int:
        """Roll healing amount"""
        if not self.healing:
            return 0
        
        # Simplified healing parsing
        if 'd' in self.healing:
            num_dice, die_size = map(int, self.healing.split('d'))
            total = 0
            for _ in range(num_dice):
                total += random.randint(1, die_size)
            return total
        else:
            return int(self.healing)

@dataclass 
class Combatant:
    name: str
    stats: CombatStats
    attacks: List[Attack] = field(default_factory=list)
    spells: List[Spell] = field(default_factory=list)
    spell_slots: Dict[int, int] = field(default_factory=dict)  # level: remaining slots
    conditions: List[str] = field(default_factory=list)
    position: Tuple[int, int] = (0, 0)
    
    # AI behavior for monsters/NPCs
    ai_behavior: str = "aggressive"  # aggressive, defensive, supportive
    
    @property
    def is_alive(self) -> bool:
        return self.stats.hp > 0
    
    @property
    def is_conscious(self) -> bool:
        return self.stats.hp > 0 and "unconscious" not in self.conditions
    
    def take_damage(self, damage: int, damage_type: DamageType) -> int:
        """Take damage and return actual damage taken"""
        # Apply resistances/immunities
        if damage_type.value in self.stats.damage_immunities:
            return 0
        
        if damage_type.value in self.stats.damage_resistances:
            damage = damage // 2
        
        # Apply damage
        self.stats.hp = max(0, self.stats.hp - damage)
        
        # Check for unconsciousness
        if self.stats.hp == 0 and "unconscious" not in self.conditions:
            self.conditions.append("unconscious")
        
        return damage
    
    def heal(self, amount: int) -> int:
        """Heal HP and return actual healing"""
        old_hp = self.stats.hp
        self.stats.hp = min(self.stats.max_hp, self.stats.hp + amount)
        
        # Remove unconscious if above 0 HP
        if self.stats.hp > 0 and "unconscious" in self.conditions:
            self.conditions.remove("unconscious")
        
        return self.stats.hp - old_hp
    
    def roll_initiative(self) -> int:
        """Roll initiative"""
        self.stats.initiative = random.randint(1, 20) + self.stats.get_modifier("dexterity")
        return self.stats.initiative
    
    def distance_to(self, other: 'Combatant') -> int:
        """Calculate distance to another combatant"""
        dx = abs(self.position[0] - other.position[0])
        dy = abs(self.position[1] - other.position[1])
        return int(math.sqrt(dx * dx + dy * dy) * 5)  # 5 feet per square

class CombatSimulator:
    """Advanced combat simulation engine"""
    
    def __init__(self):
        self.encounter_library = self._load_encounter_library()
        self.monster_library = self._load_monster_library()
        self.spell_library = self._load_spell_library()
        
    def _load_encounter_library(self) -> Dict[str, Any]:
        """Load pre-built encounter templates"""
        return {
            "goblin_ambush": {
                "description": "Classic low-level encounter",
                "cr": 1,
                "enemies": [
                    {"name": "Goblin", "count": 4},
                    {"name": "Goblin Boss", "count": 1}
                ],
                "terrain": "forest",
                "tactics": "ambush_ranged_then_melee"
            },
            "orc_patrol": {
                "description": "Mid-level humanoid encounter",
                "cr": 3,
                "enemies": [
                    {"name": "Orc", "count": 3},
                    {"name": "Orc Eye of Gruumsh", "count": 1}
                ],
                "terrain": "plains",
                "tactics": "aggressive_charge"
            },
            "dragon_lair": {
                "description": "High-level single powerful enemy",
                "cr": 10,
                "enemies": [
                    {"name": "Adult Red Dragon", "count": 1}
                ],
                "terrain": "volcanic_cave",
                "tactics": "flying_breath_weapon"
            },
            "undead_horde": {
                "description": "Many weak enemies",
                "cr": 5,
                "enemies": [
                    {"name": "Zombie", "count": 12},
                    {"name": "Ghoul", "count": 2}
                ],
                "terrain": "graveyard",
                "tactics": "overwhelming_numbers"
            },
            "mixed_encounter": {
                "description": "Variety of enemy types and abilities",
                "cr": 7,
                "enemies": [
                    {"name": "Mage", "count": 1},
                    {"name": "Knight", "count": 2},
                    {"name": "Dire Wolf", "count": 2}
                ],
                "terrain": "castle_courtyard",
                "tactics": "coordinated_spellcaster_support"
            }
        }
    
    def _load_monster_library(self) -> Dict[str, Dict[str, Any]]:
        """Load monster stat blocks"""
        return {
            "Goblin": {
                "stats": CombatStats(
                    hp=7, max_hp=7, ac=15, speed=30, initiative=0,
                    strength=8, dexterity=14, constitution=10,
                    intelligence=10, wisdom=8, charisma=8,
                    proficiency_bonus=2
                ),
                "attacks": [
                    Attack("Scimitar", 4, "1d6+2", DamageType.SLASHING),
                    Attack("Shortbow", 4, "1d6+2", DamageType.PIERCING, range=80)
                ],
                "cr": 0.25,
                "ai_behavior": "hit_and_run"
            },
            "Goblin Boss": {
                "stats": CombatStats(
                    hp=21, max_hp=21, ac=17, speed=30, initiative=0,
                    strength=10, dexterity=14, constitution=13,
                    intelligence=10, wisdom=8, charisma=10,
                    proficiency_bonus=2
                ),
                "attacks": [
                    Attack("Scimitar", 4, "1d6+2", DamageType.SLASHING),
                    Attack("Javelin", 4, "1d6+2", DamageType.PIERCING, range=30)
                ],
                "cr": 1,
                "ai_behavior": "aggressive"
            },
            "Orc": {
                "stats": CombatStats(
                    hp=15, max_hp=15, ac=13, speed=30, initiative=0,
                    strength=16, dexterity=12, constitution=13,
                    intelligence=7, wisdom=11, charisma=10,
                    proficiency_bonus=2
                ),
                "attacks": [
                    Attack("Greataxe", 5, "1d12+3", DamageType.SLASHING),
                    Attack("Javelin", 5, "1d6+3", DamageType.PIERCING, range=30)
                ],
                "cr": 0.5,
                "ai_behavior": "aggressive"
            },
            "Adult Red Dragon": {
                "stats": CombatStats(
                    hp=256, max_hp=256, ac=19, speed=40, initiative=0,
                    strength=27, dexterity=10, constitution=25,
                    intelligence=16, wisdom=13, charisma=21,
                    proficiency_bonus=5,
                    damage_immunities=["fire"],
                    spell_save_dc=19
                ),
                "attacks": [
                    Attack("Bite", 14, "2d10+8", DamageType.PIERCING),
                    Attack("Claw", 14, "2d6+8", DamageType.SLASHING),
                    Attack("Fire Breath", 0, "18d6", DamageType.FIRE, range=60, additional_effects=["dex_save_19"])
                ],
                "cr": 17,
                "ai_behavior": "tactical_flyer"
            },
            "Zombie": {
                "stats": CombatStats(
                    hp=22, max_hp=22, ac=8, speed=20, initiative=0,
                    strength=13, dexterity=6, constitution=16,
                    intelligence=3, wisdom=6, charisma=5,
                    proficiency_bonus=2,
                    damage_immunities=["poison"],
                    condition_immunities=["poisoned"]
                ),
                "attacks": [
                    Attack("Slam", 3, "1d6+1", DamageType.BLUDGEONING)
                ],
                "cr": 0.25,
                "ai_behavior": "mindless_aggressive"
            }
        }
    
    def _load_spell_library(self) -> Dict[str, Spell]:
        """Load spell library for spellcasting monsters/PCs"""
        return {
            "Magic Missile": Spell(
                name="Magic Missile",
                level=1,
                school="Evocation",
                casting_time="1 action",
                range="120 feet",
                duration="Instantaneous",
                damage="1d4+1",
                attack_spell=False
            ),
            "Fireball": Spell(
                name="Fireball",
                level=3,
                school="Evocation",
                casting_time="1 action",
                range="150 feet",
                duration="Instantaneous",
                damage="8d6",
                save_type="Dexterity",
                area_effect=True
            ),
            "Cure Wounds": Spell(
                name="Cure Wounds",
                level=1,
                school="Evocation",
                casting_time="1 action",
                range="Touch",
                duration="Instantaneous",
                healing="1d8+3"
            ),
            "Shield": Spell(
                name="Shield",
                level=1,
                school="Abjuration",
                casting_time="1 reaction",
                range="Self",
                duration="1 round",
                effects=["+5 AC until start of next turn"]
            )
        }
    
    def create_character_combatant(self, character_data: Dict[str, Any]) -> Combatant:
        """Convert character data to combatant"""
        
        # Extract basic stats
        level = character_data.get("level", 1)
        race = character_data.get("race", "human")
        character_class = character_data.get("class", "fighter")
        ability_scores = character_data.get("ability_scores", {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10
        })
        
        # Calculate derived stats
        con_mod = (ability_scores["constitution"] - 10) // 2
        proficiency_bonus = 2 + ((level - 1) // 4)
        
        # Calculate HP (simplified)
        hit_die = {"fighter": 10, "wizard": 6, "rogue": 8, "cleric": 8}.get(character_class, 8)
        max_hp = hit_die + con_mod + (level - 1) * (hit_die // 2 + 1 + con_mod)
        
        # Calculate AC (basic armor)
        base_ac = 10 + (ability_scores["dexterity"] - 10) // 2
        # Add armor bonus based on class
        armor_ac = {"fighter": 16, "cleric": 14, "rogue": 12, "wizard": 10}.get(character_class, 12)
        ac = max(base_ac, armor_ac)
        
        stats = CombatStats(
            hp=max_hp,
            max_hp=max_hp,
            ac=ac,
            speed=30,
            initiative=0,
            proficiency_bonus=proficiency_bonus,
            **ability_scores
        )
        
        # Add class-specific attacks
        attacks = self._generate_class_attacks(character_class, ability_scores, proficiency_bonus)
        
        # Add class-specific spells
        spells = self._generate_class_spells(character_class, level)
        spell_slots = self._generate_spell_slots(character_class, level)
        
        return Combatant(
            name=character_data.get("name", f"Level {level} {character_class.title()}"),
            stats=stats,
            attacks=attacks,
            spells=spells,
            spell_slots=spell_slots
        )
    
    def _generate_class_attacks(self, character_class: str, abilities: Dict[str, int], prof_bonus: int) -> List[Attack]:
        """Generate class-appropriate attacks"""
        attacks = []
        
        if character_class == "fighter":
            str_mod = (abilities["strength"] - 10) // 2
            attacks.append(Attack("Longsword", str_mod + prof_bonus, f"1d8+{str_mod}", DamageType.SLASHING))
            attacks.append(Attack("Longbow", (abilities["dexterity"] - 10) // 2 + prof_bonus, f"1d8+{(abilities['dexterity'] - 10) // 2}", DamageType.PIERCING, range=150))
        
        elif character_class == "rogue":
            dex_mod = (abilities["dexterity"] - 10) // 2
            attacks.append(Attack("Shortsword", dex_mod + prof_bonus, f"1d6+{dex_mod}", DamageType.PIERCING, additional_effects=["sneak_attack"]))
            attacks.append(Attack("Shortbow", dex_mod + prof_bonus, f"1d6+{dex_mod}", DamageType.PIERCING, range=80, additional_effects=["sneak_attack"]))
        
        elif character_class == "cleric":
            str_mod = (abilities["strength"] - 10) // 2
            attacks.append(Attack("Mace", str_mod + prof_bonus, f"1d6+{str_mod}", DamageType.BLUDGEONING))
        
        elif character_class == "wizard":
            # Wizards typically rely on spells, basic dagger
            dex_mod = (abilities["dexterity"] - 10) // 2
            attacks.append(Attack("Dagger", dex_mod + prof_bonus, f"1d4+{dex_mod}", DamageType.PIERCING))
        
        return attacks
    
    def _generate_class_spells(self, character_class: str, level: int) -> List[Spell]:
        """Generate class-appropriate spells"""
        spells = []
        
        if character_class == "wizard":
            spells.extend([
                self.spell_library["Magic Missile"],
                self.spell_library["Shield"]
            ])
            if level >= 5:
                spells.append(self.spell_library["Fireball"])
        
        elif character_class == "cleric":
            spells.extend([
                self.spell_library["Cure Wounds"]
            ])
            if level >= 5:
                spells.extend([
                    self.spell_library.get("Mass Cure Wounds", self.spell_library["Cure Wounds"]),
                    self.spell_library.get("Greater Restoration", self.spell_library["Cure Wounds"])
                ])
        
        return spells
    
    def _generate_spell_slots(self, character_class: str, level: int) -> Dict[int, int]:
        """Generate spell slots for class and level"""
        if character_class in ["wizard", "cleric"]:
            if level >= 1:
                slots = {1: 2}
            if level >= 3:
                slots[1] = 4
                slots[2] = 2
            if level >= 5:
                slots[1] = 4
                slots[2] = 3
                slots[3] = 2
            return slots
        
        return {}
    
    def create_encounter(self, encounter_name: str, party_level: int = 5) -> List[Combatant]:
        """Create encounter from library"""
        if encounter_name not in self.encounter_library:
            raise ValueError(f"Unknown encounter: {encounter_name}")
        
        encounter_data = self.encounter_library[encounter_name]
        enemies = []
        
        for enemy_group in encounter_data["enemies"]:
            monster_name = enemy_group["name"]
            count = enemy_group["count"]
            
            if monster_name not in self.monster_library:
                continue
                
            monster_template = self.monster_library[monster_name]
            
            for i in range(count):
                # Create combatant from monster template
                stats = monster_template["stats"]
                attacks = monster_template["attacks"]
                
                enemy = Combatant(
                    name=f"{monster_name} {i+1}" if count > 1 else monster_name,
                    stats=stats,
                    attacks=attacks,
                    ai_behavior=monster_template.get("ai_behavior", "aggressive")
                )
                
                # Position enemies (simplified grid)
                enemy.position = (random.randint(10, 30), random.randint(10, 30))
                enemies.append(enemy)
        
        return enemies
    
    def simulate_encounter(self, party: List[Combatant], enemies: List[Combatant], max_rounds: int = 20) -> Dict[str, Any]:
        """Simulate full encounter"""
        
        # Initialize combat
        all_combatants = party + enemies
        
        # Roll initiative
        for combatant in all_combatants:
            combatant.roll_initiative()
        
        # Sort by initiative
        initiative_order = sorted(all_combatants, key=lambda c: c.stats.initiative, reverse=True)
        
        # Combat log
        combat_log = []
        round_num = 0
        
        while round_num < max_rounds:
            round_num += 1
            round_log = {"round": round_num, "actions": []}
            
            # Check victory conditions
            party_alive = any(c.is_alive for c in party)
            enemies_alive = any(c.is_alive for c in enemies)
            
            if not party_alive:
                round_log["result"] = "Party defeated"
                combat_log.append(round_log)
                break
            elif not enemies_alive:
                round_log["result"] = "Enemies defeated"
                combat_log.append(round_log)
                break
            
            # Execute turns
            for combatant in initiative_order:
                if not combatant.is_conscious:
                    continue
                
                # Determine action
                action_log = self._execute_turn(combatant, all_combatants, party, enemies)
                round_log["actions"].append(action_log)
            
            combat_log.append(round_log)
        
        # Calculate results
        return self._analyze_combat_results(combat_log, party, enemies, round_num)
    
    def _execute_turn(self, active_combatant: Combatant, all_combatants: List[Combatant], 
                     party: List[Combatant], enemies: List[Combatant]) -> Dict[str, Any]:
        """Execute a single combatant's turn"""
        
        action_log = {
            "combatant": active_combatant.name,
            "hp": active_combatant.stats.hp,
            "actions": []
        }
        
        # Determine if this is a party member or enemy
        is_party_member = active_combatant in party
        targets = enemies if is_party_member else party
        available_targets = [t for t in targets if t.is_alive]
        
        if not available_targets:
            action_log["actions"].append({"type": "no_targets", "description": "No valid targets"})
            return action_log
        
        # Simple AI: attack if possible, otherwise move
        if active_combatant.attacks:
            target = self._select_target(active_combatant, available_targets)
            if target:
                attack_result = self._execute_attack(active_combatant, target)
                action_log["actions"].append(attack_result)
        
        # Use spells if available (simplified AI)
        if active_combatant.spells and random.random() < 0.3:  # 30% chance to cast spell
            spell_result = self._execute_spell(active_combatant, available_targets)
            if spell_result:
                action_log["actions"].append(spell_result)
        
        return action_log
    
    def _select_target(self, attacker: Combatant, targets: List[Combatant]) -> Optional[Combatant]:
        """Select target based on AI behavior"""
        if not targets:
            return None
        
        behavior = attacker.ai_behavior
        
        if behavior == "aggressive":
            # Target lowest HP
            return min(targets, key=lambda t: t.stats.hp)
        elif behavior == "tactical":
            # Target spellcasters first
            spellcasters = [t for t in targets if t.spells]
            return spellcasters[0] if spellcasters else targets[0]
        else:
            # Random target
            return random.choice(targets)
    
    def _execute_attack(self, attacker: Combatant, target: Combatant) -> Dict[str, Any]:
        """Execute attack action"""
        # Select attack (simplified - use first available)
        attack = attacker.attacks[0]
        
        # Check range
        distance = attacker.distance_to(target)
        if distance > attack.range:
            return {
                "type": "attack",
                "attack": attack.name,
                "target": target.name,
                "result": "out_of_range",
                "distance": distance
            }
        
        # Roll attack
        attack_roll = attack.roll_attack()
        hit = attack_roll >= target.stats.ac
        is_crit = attack_roll - attack.attack_bonus >= attack.crit_range
        
        result = {
            "type": "attack",
            "attack": attack.name,
            "target": target.name,
            "attack_roll": attack_roll,
            "target_ac": target.stats.ac,
            "hit": hit,
            "critical": is_crit
        }
        
        if hit:
            damage = attack.roll_damage(is_crit)
            actual_damage = target.take_damage(damage, attack.damage_type)
            
            result["damage_rolled"] = damage
            result["damage_dealt"] = actual_damage
            result["target_hp_remaining"] = target.stats.hp
            
            if target.stats.hp == 0:
                result["target_defeated"] = True
        
        return result
    
    def _execute_spell(self, caster: Combatant, targets: List[Combatant]) -> Optional[Dict[str, Any]]:
        """Execute spell action"""
        if not caster.spells:
            return None
        
        # Select spell (simplified - prefer damage spells)
        damage_spells = [s for s in caster.spells if s.damage]
        healing_spells = [s for s in caster.spells if s.healing]
        
        spell = None
        if damage_spells:
            spell = random.choice(damage_spells)
        elif healing_spells and caster.stats.hp < caster.stats.max_hp * 0.5:
            spell = random.choice(healing_spells)
        
        if not spell:
            return None
        
        # Check spell slots
        if spell.level not in caster.spell_slots or caster.spell_slots[spell.level] <= 0:
            return None
        
        # Use spell slot
        caster.spell_slots[spell.level] -= 1
        
        # Cast spell
        target = random.choice(targets) if targets else caster
        spell_result = spell.cast(caster.stats, target.stats.ac if hasattr(target, 'stats') else None)
        
        result = {
            "type": "spell",
            "spell": spell.name,
            "caster": caster.name,
            "target": target.name,
            "spell_level": spell.level,
            **spell_result
        }
        
        # Apply damage/healing
        if "damage" in spell_result and spell_result.get("hit", True):
            actual_damage = target.take_damage(spell_result["damage"], DamageType.FORCE)  # Default to force
            result["damage_dealt"] = actual_damage
            result["target_hp_remaining"] = target.stats.hp
        
        elif "healing" in spell_result:
            actual_healing = target.heal(spell_result["healing"])
            result["healing_applied"] = actual_healing
            result["target_hp_after"] = target.stats.hp
        
        return result
    
    def _analyze_combat_results(self, combat_log: List[Dict[str, Any]], party: List[Combatant], 
                               enemies: List[Combatant], rounds: int) -> Dict[str, Any]:
        """Analyze combat results and generate performance metrics"""
        
        party_survivors = [c for c in party if c.is_alive]
        enemy_survivors = [c for c in enemies if c.is_alive]
        
        # Determine outcome
        if party_survivors and not enemy_survivors:
            outcome = "Victory"
        elif enemy_survivors and not party_survivors:
            outcome = "Defeat"
        else:
            outcome = "Ongoing"
        
        # Calculate damage statistics
        total_damage_dealt = 0
        total_damage_taken = 0
        total_healing = 0
        spell_casts = 0
        
        for round_data in combat_log:
            for action in round_data.get("actions", []):
                for sub_action in action.get("actions", []):
                    if sub_action.get("type") == "attack" and "damage_dealt" in sub_action:
                        if action["combatant"] in [p.name for p in party]:
                            total_damage_dealt += sub_action["damage_dealt"]
                        else:
                            total_damage_taken += sub_action["damage_dealt"]
                    
                    elif sub_action.get("type") == "spell":
                        spell_casts += 1
                        if "damage_dealt" in sub_action:
                            if action["combatant"] in [p.name for p in party]:
                                total_damage_dealt += sub_action["damage_dealt"]
                            else:
                                total_damage_taken += sub_action["damage_dealt"]
                        elif "healing_applied" in sub_action:
                            total_healing += sub_action["healing_applied"]
        
        # Performance metrics
        performance_metrics = {
            "damage_per_round": total_damage_dealt / max(rounds, 1),
            "survivability_score": len(party_survivors) / len(party) * 100,
            "resource_efficiency": self._calculate_resource_efficiency(party),
            "tactical_score": self._calculate_tactical_score(combat_log)
        }
        
        # Character-specific analysis
        character_analysis = {}
        for character in party:
            character_analysis[character.name] = {
                "survival": character.is_alive,
                "hp_remaining": character.stats.hp,
                "hp_percentage": (character.stats.hp / character.stats.max_hp) * 100,
                "spell_slots_used": self._calculate_slots_used(character),
                "effectiveness_rating": self._rate_character_effectiveness(character, combat_log)
            }
        
        return {
            "outcome": outcome,
            "rounds": rounds,
            "party_survivors": len(party_survivors),
            "enemy_survivors": len(enemy_survivors),
            "performance_metrics": performance_metrics,
            "character_analysis": character_analysis,
            "combat_statistics": {
                "total_damage_dealt": total_damage_dealt,
                "total_damage_taken": total_damage_taken,
                "total_healing": total_healing,
                "spell_casts": spell_casts
            },
            "recommendations": self._generate_recommendations(party, combat_log, outcome),
            "detailed_log": combat_log
        }
    
    def _calculate_resource_efficiency(self, party: List[Combatant]) -> float:
        """Calculate how efficiently resources were used"""
        total_slots_available = 0
        total_slots_used = 0
        
        for character in party:
            for level, slots in character.spell_slots.items():
                # Assume they started with full slots
                max_slots = self._get_max_spell_slots(character, level)
                total_slots_available += max_slots
                total_slots_used += max_slots - slots
        
        if total_slots_available == 0:
            return 100.0  # No spellcasters
        
        return (total_slots_used / total_slots_available) * 100
    
    def _get_max_spell_slots(self, character: Combatant, level: int) -> int:
        """Get maximum spell slots for a level (simplified)"""
        # This would be more complex in a real implementation
        slot_progressions = {1: 4, 2: 3, 3: 2, 4: 1}
        return slot_progressions.get(level, 0)
    
    def _calculate_slots_used(self, character: Combatant) -> Dict[int, int]:
        """Calculate spell slots used by character"""
        slots_used = {}
        for level, remaining in character.spell_slots.items():
            max_slots = self._get_max_spell_slots(character, level)
            slots_used[level] = max_slots - remaining
        return slots_used
    
    def _calculate_tactical_score(self, combat_log: List[Dict[str, Any]]) -> float:
        """Calculate tactical decision-making score"""
        # Simplified tactical analysis
        good_decisions = 0
        total_decisions = 0
        
        for round_data in combat_log:
            for action in round_data.get("actions", []):
                for sub_action in action.get("actions", []):
                    if sub_action.get("type") in ["attack", "spell"]:
                        total_decisions += 1
                        
                        # Simple heuristics for good decisions
                        if sub_action.get("hit") or sub_action.get("healing_applied", 0) > 0:
                            good_decisions += 1
        
        return (good_decisions / max(total_decisions, 1)) * 100
    
    def _rate_character_effectiveness(self, character: Combatant, combat_log: List[Dict[str, Any]]) -> str:
        """Rate individual character effectiveness"""
        damage_dealt = 0
        healing_done = 0
        actions_taken = 0
        
        for round_data in combat_log:
            for action in round_data.get("actions", []):
                if action["combatant"] == character.name:
                    actions_taken += len(action.get("actions", []))
                    for sub_action in action.get("actions", []):
                        damage_dealt += sub_action.get("damage_dealt", 0)
                        healing_done += sub_action.get("healing_applied", 0)
        
        # Simple effectiveness rating
        total_contribution = damage_dealt + healing_done * 2  # Weight healing higher
        
        if total_contribution > 50:
            return "Excellent"
        elif total_contribution > 30:
            return "Good"
        elif total_contribution > 15:
            return "Average"
        else:
            return "Poor"
    
    def _generate_recommendations(self, party: List[Combatant], combat_log: List[Dict[str, Any]], outcome: str) -> List[str]:
        """Generate build improvement recommendations"""
        recommendations = []
        
        if outcome == "Defeat":
            recommendations.append("Consider increasing defensive stats (AC, HP)")
            recommendations.append("Improve healing capabilities or add a dedicated healer")
        
        elif outcome == "Victory":
            avg_hp_remaining = sum(c.stats.hp for c in party if c.is_alive) / len([c for c in party if c.is_alive])
            if avg_hp_remaining < 10:
                recommendations.append("Victory was close - consider defensive improvements")
        
        # Check for spell slot usage
        for character in party:
            if character.spells and all(slots > 0 for slots in character.spell_slots.values()):
                recommendations.append(f"{character.name} didn't use spell slots efficiently - consider more aggressive spellcasting")
        
        # Check for low damage output
        total_rounds = len(combat_log)
        if total_rounds > 10:
            recommendations.append("Combat lasted many rounds - consider improving damage output")
        
        return recommendations
    
    def run_build_optimization_tests(self, character_data: Dict[str, Any], 
                                   test_encounters: List[str] = None) -> Dict[str, Any]:
        """Run comprehensive build testing against multiple encounters"""
        
        if test_encounters is None:
            test_encounters = ["goblin_ambush", "orc_patrol", "undead_horde", "mixed_encounter"]
        
        character = self.create_character_combatant(character_data)
        party = [character]  # Solo testing, could be expanded
        
        results = {
            "character_name": character.name,
            "encounter_results": {},
            "overall_performance": {},
            "improvement_suggestions": []
        }
        
        total_victories = 0
        total_encounters = len(test_encounters)
        performance_scores = []
        
        for encounter_name in test_encounters:
            enemies = self.create_encounter(encounter_name, character_data.get("level", 5))
            
            # Run simulation multiple times for consistency
            simulation_results = []
            for _ in range(3):  # 3 runs per encounter
                sim_result = self.simulate_encounter(party.copy(), enemies.copy())
                simulation_results.append(sim_result)
            
            # Average the results
            avg_result = self._average_simulation_results(simulation_results)
            results["encounter_results"][encounter_name] = avg_result
            
            if avg_result["outcome"] == "Victory":
                total_victories += 1
            
            performance_scores.append(avg_result["performance_metrics"]["survivability_score"])
        
        # Calculate overall performance
        results["overall_performance"] = {
            "win_rate": (total_victories / total_encounters) * 100,
            "average_survivability": sum(performance_scores) / len(performance_scores),
            "difficulty_rating": self._calculate_difficulty_rating(results["encounter_results"]),
            "build_score": self._calculate_overall_build_score(results["encounter_results"])
        }
        
        # Generate improvement suggestions
        results["improvement_suggestions"] = self._generate_build_improvements(character_data, results["encounter_results"])
        
        return results
    
    def _average_simulation_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Average multiple simulation results"""
        if not results:
            return {}
        
        avg_result = results[0].copy()  # Start with first result
        
        # Average numeric values
        numeric_fields = ["rounds", "party_survivors", "enemy_survivors"]
        for field in numeric_fields:
            avg_result[field] = sum(r.get(field, 0) for r in results) / len(results)
        
        # Most common outcome
        outcomes = [r.get("outcome", "Unknown") for r in results]
        avg_result["outcome"] = max(set(outcomes), key=outcomes.count)
        
        return avg_result
    
    def _calculate_difficulty_rating(self, encounter_results: Dict[str, Any]) -> str:
        """Calculate appropriate difficulty rating for character"""
        victory_count = sum(1 for r in encounter_results.values() if r.get("outcome") == "Victory")
        total_encounters = len(encounter_results)
        
        win_rate = victory_count / total_encounters if total_encounters > 0 else 0
        
        if win_rate >= 0.8:
            return "Too Easy"
        elif win_rate >= 0.6:
            return "Appropriate"
        elif win_rate >= 0.4:
            return "Challenging"
        else:
            return "Too Difficult"
    
    def _calculate_overall_build_score(self, encounter_results: Dict[str, Any]) -> float:
        """Calculate overall build effectiveness score"""
        if not encounter_results:
            return 0.0
        
        scores = []
        for result in encounter_results.values():
            outcome_score = 100 if result.get("outcome") == "Victory" else 0
            survival_score = result.get("performance_metrics", {}).get("survivability_score", 0)
            efficiency_score = result.get("performance_metrics", {}).get("resource_efficiency", 0)
            
            encounter_score = (outcome_score * 0.5 + survival_score * 0.3 + efficiency_score * 0.2)
            scores.append(encounter_score)
        
        return sum(scores) / len(scores)
    
    def _generate_build_improvements(self, character_data: Dict[str, Any], encounter_results: Dict[str, Any]) -> List[str]:
        """Generate specific build improvement recommendations"""
        improvements = []
        
        # Analyze losses
        defeats = [name for name, result in encounter_results.items() if result.get("outcome") != "Victory"]
        
        if defeats:
            improvements.append(f"Character struggled with: {', '.join(defeats)}")
            
            # Specific recommendations based on encounter types
            if "dragon_lair" in defeats:
                improvements.append("Consider fire resistance for dragon encounters")
            if "undead_horde" in defeats:
                improvements.append("Need better area damage abilities for multiple enemies")
            if "mixed_encounter" in defeats:
                improvements.append("Improve versatility to handle diverse threats")
        
        # Check survivability across all encounters
        avg_survival = sum(r.get("performance_metrics", {}).get("survivability_score", 0) 
                          for r in encounter_results.values()) / len(encounter_results)
        
        if avg_survival < 70:
            improvements.append("Consider increasing Constitution or AC for better survivability")
        
        # Check resource usage
        avg_efficiency = sum(r.get("performance_metrics", {}).get("resource_efficiency", 0) 
                            for r in encounter_results.values()) / len(encounter_results)
        
        if avg_efficiency < 50:
            improvements.append("Consider using spell slots more aggressively")
        
        return improvements if improvements else ["Build performs well across all test encounters"]