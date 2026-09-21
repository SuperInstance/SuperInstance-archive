"""
Basic usage examples for the DMLog.ai RPG engine.
Demonstrates core functionality with simple examples.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from modules.DMLog import *
from modules.DMLog.core.types import AttributeType, SkillType, DamageType
from modules.DMLog.systems.dnd5e import DnD5eSystem


def demonstrate_dice_rolling():
    """Demonstrate the dice rolling system."""
    print("=== Dice Rolling Examples ===")
    
    # Basic dice rolls
    result = roll_dice("1d20+5")
    print(f"Attack roll: {result.total} (d20: {result.individual_rolls[0]} + 5)")
    
    # Advantage roll
    result = roll_dice("1d20 advantage")
    print(f"Advantage roll: {result.total} (rolled: {result.individual_rolls})")
    
    # Damage roll
    result = roll_dice("2d6+3")
    print(f"Damage roll: {result.total} (dice: {result.individual_rolls} + 3)")
    
    # Complex roll with exploding dice
    result = roll_dice("3d6 exploding")
    print(f"Exploding dice: {result.total} (dice: {result.individual_rolls})")
    
    print()


def demonstrate_character_creation():
    """Demonstrate character creation and management."""
    print("=== Character Creation ===")
    
    # Create a D&D 5e character
    character = create_character("Thorin", "dnd5e", race_name="dwarf", class_name="fighter")
    
    print(f"Created character: {character.name}")
    print(f"Level: {character.level}")
    print(f"Hit Points: {character.hit_points.current}/{character.hit_points.maximum}")
    print(f"Armor Class: {character.calculate_armor_class()}")
    
    # Show attributes
    print("\nAttributes:")
    for attr_type, attribute in character.attributes.items():
        print(f"  {attr_type.value.title()}: {attribute.score} (mod: {attribute.get_modifier():+d})")
    
    # Show skills
    print("\nKey Skills:")
    key_skills = [SkillType.ATHLETICS, SkillType.PERCEPTION, SkillType.STEALTH]
    for skill in key_skills:
        bonus = character.get_skill_bonus(skill)
        print(f"  {skill.value.title()}: {bonus:+d}")
    
    print()
    return character


def demonstrate_skill_checks():
    """Demonstrate skill and ability checks."""
    print("=== Skill Checks ===")
    
    character = create_character("Aria", "dnd5e", race_name="elf", class_name="rogue")
    
    # Make some skill checks
    skills_to_test = [
        (SkillType.STEALTH, 15),
        (SkillType.PERCEPTION, 12),
        (SkillType.ATHLETICS, 18)
    ]
    
    for skill, dc in skills_to_test:
        result = make_skill_check(character, skill, dc)
        outcome = "SUCCESS" if result.success else "FAILURE"
        print(f"{character.name} {skill.value} check: {result.total} vs DC {dc} - {outcome}")
    
    # Make an ability check
    result = make_ability_check(character, AttributeType.DEXTERITY, 14)
    outcome = "SUCCESS" if result.success else "FAILURE"
    print(f"{character.name} Dexterity check: {result.total} vs DC 14 - {outcome}")
    
    print()


def demonstrate_combat():
    """Demonstrate combat mechanics."""
    print("=== Combat Example ===")
    
    # Create combatants
    fighter = create_character("Gareth", "dnd5e", race_name="human", class_name="fighter")
    rogue = create_character("Zara", "dnd5e", race_name="halfling", class_name="rogue")
    
    # Add some basic equipment
    from modules.DMLog.core.types import Equipment
    sword = Equipment(
        name="Longsword",
        equipped=True,
        properties={
            "damage_dice": "1d8",
            "damage_type": "slashing",
            "attack_bonus": 0,
            "damage_bonus": 0
        }
    )
    fighter.add_equipment(sword)
    
    # Start combat
    combat = start_combat(fighter, rogue)
    
    print(f"Combat started between {fighter.name} and {rogue.name}")
    print("\nInitiative Order:")
    for i, entry in enumerate(combat.initiative_order):
        print(f"  {i+1}. {entry.character_name}: {entry.initiative_score}")
    
    # Simulate one round
    current_char = combat.get_current_character()
    if current_char:
        print(f"\n{current_char.name}'s turn:")
        
        # Make an attack
        target = rogue if current_char == fighter else fighter
        if hasattr(current_char, 'equipment') and current_char.equipment:
            weapon = next((item for item in current_char.equipment if item.equipped), None)
            if weapon:
                attack_result = combat.make_attack(current_char, target, weapon)
                hit_miss = "HIT" if attack_result.hit else "MISS"
                crit_text = " (CRITICAL)" if attack_result.critical else ""
                damage_text = f" for {attack_result.total_damage} damage" if attack_result.hit else ""
                
                print(f"  {current_char.name} attacks {target.name}: {hit_miss}{crit_text}{damage_text}")
                print(f"  {target.name} HP: {target.hit_points.current}/{target.hit_points.maximum}")
    
    combat.end_combat()
    print("Combat ended.")
    print()


def demonstrate_spellcasting():
    """Demonstrate spellcasting system."""
    print("=== Spellcasting Example ===")
    
    # Create a spellcaster
    wizard = create_character("Elara", "dnd5e", race_name="human", class_name="wizard")
    wizard.level = 3  # Level up for more spell slots
    
    # Add some spell slots
    wizard.add_spell_slot(1, 4)
    wizard.add_spell_slot(2, 2)
    
    print(f"Created {wizard.name}, level {wizard.level} wizard")
    print("Spell slots:")
    for level, slot in wizard.spell_slots.items():
        print(f"  Level {level}: {slot.remaining}/{slot.total}")
    
    # Create a target
    target = create_character("Goblin", "dnd5e")
    target.hit_points.current = 15
    target.hit_points.maximum = 15
    
    # Cast Magic Missile
    try:
        result = cast_spell(wizard, "Magic Missile", [target], 1)
        if result.success:
            print(f"\n{wizard.name} casts Magic Missile!")
            if target.id in result.damage_dealt:
                damage = result.damage_dealt[target.id]
                print(f"  Deals {damage} force damage to {target.name}")
                print(f"  {target.name} HP: {target.hit_points.current}/{target.hit_points.maximum}")
            
            # Check remaining spell slots
            remaining_slots = wizard.spell_slots[1].remaining
            print(f"  Level 1 slots remaining: {remaining_slots}")
        else:
            print(f"Failed to cast Magic Missile")
            
    except ValueError as e:
        print(f"Spellcasting error: {e}")
    
    print()


def demonstrate_campaign_management():
    """Demonstrate campaign and session management."""
    print("=== Campaign Management ===")
    
    # Create a campaign
    campaign = create_campaign(
        name="The Lost Mines of Phandelver",
        description="A classic D&D 5e adventure for beginning characters",
        game_system="dnd5e",
        dm_id="dm_user_123"
    )
    
    print(f"Created campaign: {campaign.name}")
    
    # Add players
    from modules.DMLog.core.campaign import default_campaign_manager
    default_campaign_manager.add_player_to_campaign(campaign.id, "player_1", "char_1")
    default_campaign_manager.add_player_to_campaign(campaign.id, "player_2", "char_2")
    
    print(f"Added {len(campaign.player_ids)} players to campaign")
    
    # Create a session
    from datetime import datetime
    session = default_campaign_manager.create_session(
        campaign.id,
        "Session 1: Goblin Ambush",
        datetime.now()
    )
    
    if session:
        print(f"Created session: {session.name}")
        
        # Start the session
        default_campaign_manager.start_session(session.id)
        
        # Add some events
        from modules.DMLog.core.campaign import EventType
        default_campaign_manager.add_event(
            campaign.id,
            EventType.COMBAT_ENCOUNTER,
            "Goblin Ambush",
            "The party was ambushed by goblins on the road",
            session.id
        )
        
        default_campaign_manager.add_event(
            campaign.id,
            EventType.NPC_INTERACTION,
            "Met Sildar Hallwinter",
            "The party rescued Sildar from goblin captivity",
            session.id
        )
        
        # Award experience
        default_campaign_manager.award_experience(
            campaign.id,
            session.id,
            {"char_1": 200, "char_2": 200}
        )
        
        # End the session
        default_campaign_manager.end_session(session.id, 180)  # 3 hours
        
        print(f"Session completed. Duration: {session.duration_minutes} minutes")
        
        # Get campaign statistics
        stats = default_campaign_manager.get_campaign_statistics(campaign.id)
        print(f"Campaign stats: {stats['completed_sessions']} sessions, {stats['total_events']} events")
    
    print()


def main():
    """Run all demonstration examples."""
    print("DMLog.ai RPG Engine - Basic Usage Examples")
    print("=" * 50)
    
    # Show engine info
    info = get_engine_info()
    print(f"Engine: {info['name']} v{info['version']}")
    print(f"Supported systems: {len(info['supported_systems'])}")
    print()
    
    # Run demonstrations
    demonstrate_dice_rolling()
    character = demonstrate_character_creation()
    demonstrate_skill_checks()
    demonstrate_combat()
    demonstrate_spellcasting()
    demonstrate_campaign_management()
    
    print("All examples completed successfully!")


if __name__ == "__main__":
    main()