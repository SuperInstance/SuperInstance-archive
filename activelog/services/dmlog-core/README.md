# DMLog Core RPG Rules Engine

A comprehensive RPG rules engine built with FastAPI that supports multiple tabletop RPG systems. The service runs on port 8012 and provides a complete suite of tools for managing tabletop RPG campaigns.

## Features Implemented

### 1. Universal Character Sheet System
- **Location**: `models/character.py`, `services/character_service.py`, `api/character.py`
- Adaptable character system supporting multiple RPG systems (D&D 5e, Pathfinder 2e, Call of Cthulhu, etc.)
- Flexible attribute system using JSON storage
- Character templates and progression tracking
- Spell slot management and resource tracking

### 2. Comprehensive Dice Rolling Mechanics
- **Location**: `models/base.py`, `services/dice_service.py`, `api/dice.py`
- Support for all standard dice types (d4, d6, d8, d10, d12, d20, d100)
- Advanced mechanics: advantage/disadvantage, exploding dice, keep highest/lowest
- Dice expression parser for complex rolls
- Probability calculator and statistics tracking
- Roll history and preset roll configurations

### 3. Combat Tracker with Full Features
- **Location**: `models/combat.py`, `services/combat_service.py`, `api/combat.py`
- Initiative tracking and turn management
- Participant management (PCs, NPCs, monsters)
- Hit point tracking and damage application
- Condition and effect management
- Combat action logging and resolution

### 4. Spell/Ability Management System
- **Location**: `models/spells.py`, `services/spell_service.py`, `api/spell.py`
- Comprehensive spell database with search capabilities
- Resource pool management (spell slots, ki points, etc.)
- Cooldown tracking and spell preparation
- Short/long rest mechanics
- Spell slot configuration for different classes

### 5. Inventory System with Encumbrance
- **Location**: `models/inventory.py`, `services/inventory_service.py`, `api/inventory.py`
- Item database with properties and magical effects
- Weight tracking and encumbrance calculations
- Container management and organization
- Currency tracking (cp, sp, ep, gp, pp)
- Magic item attunement system

### 6. NPC Generator with Personalities
- **Location**: `models/npc.py`, `services/npc_service.py`, `api/npc.py`
- Procedural NPC generation with personality traits
- Role-based stat generation and background creation
- Motivation and goal system
- Appearance and name generation
- NPC interaction tracking

### 7. Encounter Balancing Calculator
- **Location**: `models/encounter.py`, `services/encounter_service.py`, `api/encounter.py`
- CR-based encounter difficulty calculation
- Party composition analysis
- XP budget and multiplier calculations
- Encounter suggestions and balance recommendations
- Monster database integration

### 8. Experience and Leveling Systems
- **Location**: `models/experience.py`, `services/experience_service.py`, `api/experience.py`
- XP calculation for various activities (combat, quests, discovery, roleplay)
- Automatic and manual leveling systems
- Milestone tracking and completion
- Class feature progression
- HP gain calculation with hit dice

### 9. Loot Table Generators
- **Location**: `models/loot.py`, `services/loot_service.py`, `api/loot.py`
- Treasure generation based on CR and party level
- Currency and item generation algorithms
- Rarity-based magic item creation
- Loot table management and customization
- Wealth scaling and modifiers

### 10. Campaign Timeline Tracker
- **Location**: `models/campaign.py`, `services/campaign_service.py`, `api/campaign.py`
- Campaign management and session tracking
- Event timeline with filtering and search
- World calendar system with custom calendars
- Campaign statistics and analysis
- Player and character tracking

### 11. Rule Lookup System with Search
- **Location**: `models/rules.py`, `services/rules_service.py`, `api/rules.py`
- Comprehensive rule database with full-text search
- Fuzzy matching and relevance scoring
- Rule interpretations and clarifications
- Quick reference generation
- Rule conflict detection

### 12. Character Relationship Mapping
- **Location**: `models/relationship.py`, `services/relationship_service.py`, `api/relationship.py`
- Character relationship tracking with multiple relationship types
- Network analysis and centrality calculations
- Relationship event history
- Conflict detection and relationship suggestions
- Graph visualization support

## API Structure

The service provides RESTful APIs for all systems:

- `/api/v1/dice/` - Dice rolling and probability calculations
- `/api/v1/characters/` - Character management and progression
- `/api/v1/combat/` - Combat encounter tracking
- `/api/v1/spells/` - Spell and ability management
- `/api/v1/inventory/` - Inventory and item management
- `/api/v1/npcs/` - NPC generation and management
- `/api/v1/encounters/` - Encounter balancing and generation
- `/api/v1/experience/` - Experience and leveling systems
- `/api/v1/loot/` - Loot generation and treasure tables
- `/api/v1/campaigns/` - Campaign and timeline management
- `/api/v1/rules/` - Rule lookup and search
- `/api/v1/relationships/` - Character relationship mapping

## Configuration

The service is configured to:
- Run on port 8012
- Support multiple game systems simultaneously
- Use PostgreSQL for production, SQLite for development
- Include comprehensive logging and error handling
- Provide interactive API documentation at `/docs`

## Game Systems Supported

- D&D 5th Edition
- Pathfinder 2nd Edition  
- Call of Cthulhu
- Savage Worlds
- Generic/Universal system support

## Installation and Usage

1. Install dependencies: `pip install -r requirements.txt`
2. Set up database: `python -c "from database import init_db; init_db()"`
3. Run the service: `python main.py`
4. Access API documentation: http://localhost:8012/docs

The service provides a complete RPG management solution that can handle everything from character creation to campaign management, making it perfect for both players and game masters running complex tabletop RPG campaigns.