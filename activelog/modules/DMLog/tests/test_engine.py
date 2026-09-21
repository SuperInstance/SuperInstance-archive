"""
Basic tests for the DMLog.ai RPG engine.
Tests core functionality to ensure everything works correctly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import unittest
from unittest.mock import patch, MagicMock

from modules.DMLog import *
from modules.DMLog.core.types import AttributeType, SkillType, DamageType, DiceType
from modules.DMLog.systems.dnd5e import DnD5eSystem


class TestDiceRoller(unittest.TestCase):
    """Test the dice rolling system."""
    
    def setUp(self):
        self.roller = DiceRoller(seed=12345)  # Fixed seed for reproducible tests
    
    def test_basic_roll(self):
        """Test basic dice rolling."""
        dice_roll = DiceRoll(1, DiceType.D20)
        result = self.roller.roll(dice_roll)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result.individual_rolls), 1)
        self.assertTrue(1 <= result.individual_rolls[0] <= 20)
        self.assertEqual(result.total, result.individual_rolls[0])
    
    def test_roll_with_modifier(self):
        """Test dice rolling with modifiers."""
        dice_roll = DiceRoll(1, DiceType.D20, modifier=5)
        result = self.roller.roll(dice_roll)
        
        self.assertEqual(result.total, result.individual_rolls[0] + 5)
    
    def test_multiple_dice(self):
        """Test rolling multiple dice."""
        dice_roll = DiceRoll(3, DiceType.D6)
        result = self.roller.roll(dice_roll)
        
        self.assertEqual(len(result.individual_rolls), 3)
        self.assertEqual(result.total, sum(result.individual_rolls))
        for roll in result.individual_rolls:
            self.assertTrue(1 <= roll <= 6)
    
    def test_advantage_roll(self):
        """Test advantage rolls."""
        dice_roll = DiceRoll(1, DiceType.D20, advantage=True)
        result = self.roller.roll(dice_roll)
        
        # With advantage, we should get 2 d20 rolls in individual_rolls
        self.assertEqual(len(result.individual_rolls), 2)
    
    def test_expression_parsing(self):
        """Test dice expression parsing."""
        from modules.DMLog.core.dice import DiceExpressionParser
        
        dice_roll = DiceExpressionParser.parse("2d6+3")
        self.assertEqual(dice_roll.dice_count, 2)
        self.assertEqual(dice_roll.dice_type, DiceType.D6)
        self.assertEqual(dice_roll.modifier, 3)


class TestCharacter(unittest.TestCase):
    """Test character creation and management."""
    
    def setUp(self):
        self.character = BaseCharacter("Test Character")
    
    def test_character_creation(self):
        """Test basic character creation."""
        self.assertEqual(self.character.name, "Test Character")
        self.assertEqual(self.character.level, 1)
        self.assertIsNotNone(self.character.id)
    
    def test_attribute_management(self):
        """Test attribute adding and retrieval."""
        self.character.add_attribute(AttributeType.STRENGTH, 16)
        
        score = self.character.get_attribute_score(AttributeType.STRENGTH)
        modifier = self.character.get_attribute_modifier(AttributeType.STRENGTH)
        
        self.assertEqual(score, 16)
        self.assertEqual(modifier, 3)  # (16 - 10) // 2
    
    def test_skill_management(self):
        """Test skill adding and bonus calculation."""
        # Add attribute first
        self.character.add_attribute(AttributeType.DEXTERITY, 14)
        
        # Add skill
        self.character.add_skill(SkillType.STEALTH, AttributeType.DEXTERITY, proficient=True)
        
        skill_bonus = self.character.get_skill_bonus(SkillType.STEALTH)
        
        # Should be DEX modifier (2) + proficiency bonus (2) = 4
        self.assertEqual(skill_bonus, 4)
    
    def test_hit_points(self):
        """Test hit point management."""
        # Take damage
        damage_taken = self.character.hit_points.take_damage(5)
        self.assertEqual(damage_taken, 5)
        self.assertEqual(self.character.hit_points.current, 3)  # Started with 8
        
        # Heal
        healing_done = self.character.hit_points.heal(3)
        self.assertEqual(healing_done, 3)
        self.assertEqual(self.character.hit_points.current, 6)
        
        # Test temporary HP
        self.character.hit_points.add_temporary_hp(5)
        self.assertEqual(self.character.hit_points.temporary, 5)
    
    def test_condition_management(self):
        """Test condition adding and removal."""
        from modules.DMLog.core.types import Condition, ConditionType
        
        condition = Condition(ConditionType.POISONED, duration=3)
        self.character.add_condition(condition)
        
        self.assertTrue(self.character.has_condition(ConditionType.POISONED))
        
        self.character.remove_condition(ConditionType.POISONED)
        self.assertFalse(self.character.has_condition(ConditionType.POISONED))


class TestDnD5eSystem(unittest.TestCase):
    """Test D&D 5e specific functionality."""
    
    def setUp(self):
        self.system = DnD5eSystem()
    
    def test_system_properties(self):
        """Test basic system properties."""
        self.assertEqual(self.system.name, "Dungeons & Dragons 5th Edition")
        self.assertEqual(self.system.version, "5.0")
        self.assertIn(AttributeType.STRENGTH, self.system.supported_attributes)
        self.assertIn(SkillType.ATHLETICS, self.system.supported_skills)
    
    def test_attribute_modifier_calculation(self):
        """Test D&D 5e attribute modifier calculation."""
        test_cases = [
            (10, 0),
            (11, 0),
            (12, 1),
            (14, 2),
            (16, 3),
            (8, -1),
            (6, -2)
        ]
        
        for score, expected_mod in test_cases:
            with self.subTest(score=score):
                modifier = self.system.calculate_attribute_modifier(score)
                self.assertEqual(modifier, expected_mod)
    
    def test_character_creation(self):
        """Test D&D 5e character creation."""
        character = self.system.create_character("Test Fighter", "human", "fighter")
        
        self.assertEqual(character.name, "Test Fighter")
        self.assertEqual(character.level, 1)
        self.assertIsNotNone(character.race)
        self.assertIsNotNone(character.character_class)
        
        # Should have all 6 D&D attributes
        for attr in self.system.supported_attributes:
            self.assertIn(attr, character.attributes)


class TestCombatEngine(unittest.TestCase):
    """Test combat mechanics."""
    
    def setUp(self):
        self.combat = CombatEngine()
        self.fighter = BaseCharacter("Fighter")
        self.rogue = BaseCharacter("Rogue")
        
        # Add basic attributes
        self.fighter.add_attribute(AttributeType.DEXTERITY, 12)
        self.rogue.add_attribute(AttributeType.DEXTERITY, 16)
    
    def test_initiative_rolling(self):
        """Test initiative rolling."""
        results = self.combat.roll_initiative([self.fighter, self.rogue])
        
        self.assertEqual(len(results), 2)
        self.assertIn(self.fighter.id, results)
        self.assertIn(self.rogue.id, results)
        
        # Check initiative order is sorted
        self.assertEqual(len(self.combat.initiative_order), 2)
        
        # Higher initiative should be first
        first = self.combat.initiative_order[0]
        second = self.combat.initiative_order[1]
        self.assertGreaterEqual(first.initiative_score, second.initiative_score)
    
    def test_combat_flow(self):
        """Test basic combat flow."""
        self.combat.add_participant(self.fighter)
        self.combat.add_participant(self.rogue)
        
        self.combat.start_combat()
        
        self.assertEqual(self.combat.state.value, "active")
        self.assertEqual(self.combat.current_round, 1)
        
        current_char = self.combat.get_current_character()
        self.assertIsNotNone(current_char)
        
        # Advance to next turn
        next_char = self.combat.next_turn()
        self.assertIsNotNone(next_char)
        self.assertNotEqual(current_char.id, next_char.id)


class TestSpellcasting(unittest.TestCase):
    """Test spellcasting system."""
    
    def setUp(self):
        from modules.DMLog.core.spells import SpellcastingSystem
        self.spellcasting = SpellcastingSystem()
        
        self.wizard = BaseCharacter("Wizard")
        self.wizard.add_spell_slot(1, 2)
        
        # Add spell to prepared list
        self.wizard.spells_prepared = ["Magic Missile"]
    
    def test_spell_library(self):
        """Test spell library functionality."""
        spell = self.spellcasting.get_spell("Magic Missile")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.name, "Magic Missile")
        self.assertEqual(spell.level, 1)
    
    def test_spell_casting(self):
        """Test basic spell casting."""
        target = BaseCharacter("Target")
        target.hit_points.current = 10
        
        result = self.spellcasting.cast_spell(
            self.wizard, 
            "Magic Missile", 
            [target], 
            1
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.cast_level, 1)
        self.assertIsNotNone(result.slot_used)


class TestCampaignManagement(unittest.TestCase):
    """Test campaign management functionality."""
    
    def setUp(self):
        from modules.DMLog.core.campaign import CampaignManager
        self.manager = CampaignManager()
    
    def test_campaign_creation(self):
        """Test campaign creation."""
        campaign = self.manager.create_campaign(
            "Test Campaign",
            "A test campaign",
            "dnd5e",
            "dm_123"
        )
        
        self.assertEqual(campaign.name, "Test Campaign")
        self.assertEqual(campaign.game_system, "dnd5e")
        self.assertEqual(campaign.dm_id, "dm_123")
        self.assertIn(campaign.id, self.manager.campaigns)
    
    def test_session_management(self):
        """Test session creation and management."""
        campaign = self.manager.create_campaign(
            "Test Campaign", "Description", "dnd5e", "dm_123"
        )
        
        from datetime import datetime
        session = self.manager.create_session(
            campaign.id,
            "Test Session",
            datetime.now()
        )
        
        self.assertIsNotNone(session)
        self.assertEqual(session.name, "Test Session")
        self.assertEqual(session.session_number, 1)
        self.assertIn(session.id, campaign.sessions)
    
    def test_event_tracking(self):
        """Test event tracking."""
        campaign = self.manager.create_campaign(
            "Test Campaign", "Description", "dnd5e", "dm_123"
        )
        
        from modules.DMLog.core.campaign import EventType
        event = self.manager.add_event(
            campaign.id,
            EventType.COMBAT_ENCOUNTER,
            "Test Combat",
            "A test combat encounter"
        )
        
        self.assertIsNotNone(event)
        self.assertEqual(event.title, "Test Combat")
        self.assertIn(event, campaign.events)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple systems."""
    
    def test_full_character_workflow(self):
        """Test creating and using a character through multiple systems."""
        # Create character
        character = create_character("Integration Test", "dnd5e", race_name="human", class_name="fighter")
        
        # Test skill check
        result = make_skill_check(character, SkillType.ATHLETICS, 15)
        self.assertIsNotNone(result)
        
        # Test in combat
        enemy = create_character("Enemy", "dnd5e")
        combat = start_combat(character, enemy)
        
        self.assertEqual(combat.state.value, "active")
        current_char = combat.get_current_character()
        self.assertIsNotNone(current_char)
        
        combat.end_combat()
        self.assertEqual(combat.state.value, "ended")


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestDiceRoller,
        TestCharacter, 
        TestDnD5eSystem,
        TestCombatEngine,
        TestSpellcasting,
        TestCampaignManagement,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("Running DMLog.ai RPG Engine Tests")
    print("=" * 40)
    
    success = run_tests()
    
    if success:
        print("\nAll tests passed! ✓")
    else:
        print("\nSome tests failed! ✗")
        sys.exit(1)