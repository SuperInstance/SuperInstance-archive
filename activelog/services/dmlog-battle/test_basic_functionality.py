#!/usr/bin/env python3
"""
Basic functionality test for the DMLog Battle service.
"""

import sys
import os

# Add the service directory to the Python path
service_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, service_dir)

# Import using relative path structure
import models.base as base_models
import models.combatant as combatant_models
import models.battlefield as battlefield_models
import models.combat as combat_models
import services.combat_service as combat_service_module
import services.grid_service as grid_service_module
import services.visualization_service as viz_service_module
import config as config_module

# Shorter aliases for convenience
Position = base_models.Position
CreatureSize = base_models.CreatureSize
DamageType = base_models.DamageType
ActionType = base_models.ActionType
CombatantSchema = combatant_models.CombatantSchema
AbilityScores = combatant_models.AbilityScores
CombatStats = combatant_models.CombatStats
BattlefieldSchema = battlefield_models.BattlefieldSchema
CombatEncounter = combat_models.CombatEncounter
CombatService = combat_service_module.CombatService
GridService = grid_service_module.GridService
VisualizationService = viz_service_module.VisualizationService
Config = config_module.Config

def test_basic_combat_functionality():
    """Test basic combat functionality."""
    
    print("Testing DMLog Battle Service...")
    
    # Initialize services
    config = Config()
    combat_service = CombatService(config)
    grid_service = GridService(config)
    viz_service = VisualizationService(config)
    
    print("✓ Services initialized")
    
    # Create a simple battlefield
    battlefield = BattlefieldSchema(
        name="Test Arena",
        description="A simple test battlefield",
        width=10,
        height=10,
        square_size_feet=5
    )
    
    # Initialize grid
    GridCell = base_models.GridCell
    TerrainType = base_models.TerrainType
    battlefield.grid = []
    for y in range(battlefield.height):
        row = []
        for x in range(battlefield.width):
            cell = GridCell(
                position=Position(x=x, y=y),
                terrain_type=TerrainType.NORMAL,
                elevation=0,
                light_level=1.0
            )
            row.append(cell)
        battlefield.grid.append(row)
    
    print("✓ Battlefield created")
    
    # Create test combatants
    fighter = CombatantSchema(
        name="Test Fighter",
        creature_type="player_character",
        level=5,
        abilities=AbilityScores(
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=11
        ),
        stats=CombatStats(
            armor_class=18,
            hit_points=45,
            max_hit_points=45,
            speed=30
        ),
        position=Position(x=2, y=2)
    )
    
    orc = CombatantSchema(
        name="Test Orc",
        creature_type="monster",
        level=1,
        abilities=AbilityScores(
            strength=16,
            dexterity=12,
            constitution=16,
            intelligence=7,
            wisdom=11,
            charisma=10
        ),
        stats=CombatStats(
            armor_class=13,
            hit_points=15,
            max_hit_points=15,
            speed=30
        ),
        position=Position(x=7, y=7)
    )
    
    print("✓ Combatants created")
    
    # Create combat encounter
    encounter = CombatEncounter(
        name="Test Combat",
        description="A test combat encounter",
        battlefield=battlefield,
        combatants=[fighter, orc]
    )
    
    print("✓ Combat encounter created")
    
    # Test line of sight calculation
    los = grid_service.calculate_line_of_sight(
        battlefield, fighter.position, orc.position
    )
    print(f"✓ Line of sight: {los.has_line_of_sight} (clear: {los.clear})")
    
    # Test movement path calculation
    target_pos = Position(x=5, y=5)
    path = grid_service.calculate_movement_path(
        battlefield, fighter, target_pos
    )
    print(f"✓ Movement path calculated: {len(path.waypoints)} waypoints")
    
    # Start combat
    combat_service.start_combat(encounter)
    print(f"✓ Combat started, current round: {encounter.current_round}")
    
    # Test visualization
    viz = viz_service.create_battlefield_visualization(encounter)
    print(f"✓ Visualization created: {viz.width}x{viz.height} battlefield")
    
    # Test ASCII rendering
    ascii_viz = viz_service.render_to_ascii(viz, show_coordinates=True)
    print("✓ ASCII visualization:")
    print(ascii_viz)
    
    print("\n🎉 All basic tests passed!")
    return True

def test_spell_effects():
    """Test spell effect system."""
    
    print("\nTesting spell effects...")
    
    import services.spell_effect_service as spell_service_module
    SpellEffectService = spell_service_module.SpellEffectService
    
    spell_service = SpellEffectService()
    
    # Test creating a fireball AOE
    wizard = CombatantSchema(name="Test Wizard", creature_type="player_character")
    
    aoe = spell_service.create_spell_aoe(
        "fireball",
        wizard,
        Position(x=5, y=5),
        spell_level=3
    )
    
    if aoe:
        print(f"✓ Fireball AOE created: {aoe.shape.value}, size {aoe.size}")
    else:
        print("✗ Failed to create fireball AOE")
        return False
    
    print("✓ Spell effects test passed!")
    return True

def main():
    """Run all tests."""
    
    try:
        success = True
        
        # Run basic functionality test
        if not test_basic_combat_functionality():
            success = False
        
        # Run spell effects test
        if not test_spell_effects():
            success = False
        
        if success:
            print("\n🎉 All tests completed successfully!")
            print("\nDMLog Battle Service is ready to use!")
            print("\nTo start the service, run:")
            print("python -m uvicorn main:app --host 0.0.0.0 --port 8015 --reload")
        else:
            print("\n❌ Some tests failed")
            return 1
            
        return 0
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())