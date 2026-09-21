# DMLog Player Interface

A comprehensive player interface system for D&D and other tabletop RPGs, providing tools for character management, session preparation, and campaign tracking.

## Features Implemented ✅

### 1. 📔 **Character Journal with Private Notes**
- Create and organize journal entries with tags and categories
- Private notes separate from shared content
- Session-specific entries with in-game dates
- Search functionality across all entries
- Export/import capabilities for backups
- Automatic session summaries and milestone tracking

### 2. 🎲 **Spell/Ability Quick Reference**
- Fast lookup of character spells and abilities
- Spell slot tracking with usage analytics
- Quick reference cards for session play
- Spell preparation suggestions based on usage history
- Custom spell support for homebrew content
- Effectiveness tracking for optimization

### 3. 🎒 **Inventory Management with Encumbrance**
- Comprehensive item tracking with weights and values
- Automatic encumbrance calculations with variant rules
- Equipment loadout saving and switching
- Item organization by type, value, and weight
- Shopping list creation with cost analysis
- Inventory statistics and valuable item tracking

### 4. 🎯 **Character Goal and Quest Tracker**
- Personal and party quest management
- Milestone tracking with progress indicators
- Priority-based organization with deadlines
- Quest templates for common objectives
- Dependency tracking between related quests
- Comprehensive quest statistics and analytics

### 5. 👥 **Party Formation Tools**
- Party creation and invitation system
- Leadership management and role assignment
- Party composition analysis and synergy scoring
- Shared objectives and reputation tracking
- Party formation suggestions for optimal balance
- Communication and coordination features

### 6. 💕 **Character Relationship Tracker**
- NPC, PC, and organization relationship management
- Trust and influence level tracking (1-10 scales)
- Interaction history with impact tracking
- Relationship network visualization
- Faction standings and reputation management
- Automated relationship action suggestions

### 7. 🛌 **Rest and Recovery Manager**
- Short, long, and extended rest processing
- Hit dice spending during short rests
- Automatic recovery calculation for HP, spell slots, and features
- Rest history and pattern analysis
- Rest timing suggestions based on character state
- Interruption tracking and effects

### 8. 📊 **Language and Skill Tracker**
- Skill usage statistics with success/failure rates
- Language learning progress tracking
- Practice session recording
- Performance analytics with DC and roll averages
- Critical success/failure tracking
- Skill development recommendations

## Architecture

### Core Components

- **Main Service** (`main_service.py`): FastAPI orchestrator with REST API endpoints
- **Models** (`models/base.py`): Pydantic data models for all system entities
- **Managers** (`managers/`): Specialized managers for each feature area
- **Interface** (`interface/`): UI components and templates (future expansion)
- **Utils** (`utils/`): Supporting utilities and helper functions

### Manager Classes

- **JournalManager**: Private notes and session records
- **SpellReferenceManager**: Quick spell lookup and usage tracking
- **InventoryManager**: Item tracking with encumbrance calculations
- **QuestTracker**: Goal and objective management
- **PartyManager**: Group formation and coordination
- **RelationshipManager**: Social network and influence tracking
- **RestManager**: Recovery and resource management
- **SkillTracker**: Skill usage and development analytics

## API Endpoints

### Character Management
- `POST /characters` - Create new character
- `GET /characters/{id}` - Get character details
- `GET /characters/{id}/dashboard` - Comprehensive dashboard
- `GET /characters/{id}/session-prep` - Session preparation info

### Journal System
- `POST /characters/{id}/journal` - Create journal entry
- `GET /characters/{id}/journal` - Get journal entries
- `GET /characters/{id}/journal/search` - Search journal

### Inventory System
- `POST /characters/{id}/inventory` - Add inventory item
- `GET /characters/{id}/inventory` - Get inventory
- `GET /characters/{id}/encumbrance` - Check encumbrance status

### Quest Management
- `POST /characters/{id}/quests` - Create quest
- `GET /characters/{id}/quests` - Get all quests
- `GET /characters/{id}/quests/active` - Get active quests

### Spell Management
- `POST /characters/{id}/spells` - Add character spell
- `GET /characters/{id}/spells` - Get character spells
- `GET /characters/{id}/spells/quick-reference` - Quick reference card

### Party System
- `POST /parties` - Create party
- `GET /characters/{id}/party` - Get character's party
- `POST /parties/{id}/invite` - Send party invitation

### Relationship System
- `POST /characters/{id}/relationships` - Create relationship
- `GET /characters/{id}/relationships` - Get relationships
- `POST /relationships/{id}/interaction` - Add interaction

## Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Run Service**
```bash
python main_service.py
```

The service will start on `http://localhost:8001` with interactive API documentation at `/docs`.

## Usage Examples

### Character Dashboard
Get comprehensive character information:
```python
response = requests.get("/characters/char123/dashboard")
dashboard = response.json()

print(f"Character: {dashboard['character']['name']}")
print(f"Active Quests: {dashboard['recent_activity']['active_quests']}")
print(f"Journal Entries: {dashboard['statistics']['journal']['total_entries']}")
```

### Session Preparation
Get everything needed for a session:
```python
response = requests.get("/characters/char123/session-prep")
prep = response.json()

print("Active Quests:")
for quest in prep['active_quests']:
    print(f"- {quest['title']} ({quest['progress']}%)")

print("Equipped Items:")
for item in prep['equipped_items']:
    print(f"- {item}")
```

### Inventory Management
Add items and check encumbrance:
```python
# Add item
requests.post("/characters/char123/inventory", json={
    "name": "Longsword",
    "weight": 3.0,
    "value": {"gp": 15}
})

# Check encumbrance
response = requests.get("/characters/char123/encumbrance")
encumbrance = response.json()
print(f"Carrying: {encumbrance['weight_percentage']:.1f}% of capacity")
```

## Key Features

### Advanced Analytics
- **Character Development Tracking**: Monitor growth and advancement
- **Resource Management**: Optimize spell slots and equipment usage
- **Social Network Analysis**: Track relationship dynamics
- **Quest Progress Visualization**: Monitor objective completion

### Session Enhancement
- **Quick Reference Cards**: Fast access to spells and abilities
- **Preparation Checklists**: Ensure readiness for sessions  
- **Real-time Tracking**: Update character state during play
- **History Maintenance**: Preserve campaign memories and decisions

### Quality of Life
- **Automated Calculations**: Encumbrance, rest benefits, spell slots
- **Smart Suggestions**: Spell preparation, rest timing, relationship actions
- **Data Export/Import**: Backup and share character data
- **Search and Organization**: Find information quickly

## Remaining Features (Optional Enhancements)
- Downtime activity manager
- Crafting system interface  
- Character development planner
- Party fund manager

## Development

### Architecture Principles
- **Modular Design**: Each feature is independently manageable
- **RESTful API**: Clean, discoverable endpoints
- **Data-Driven**: Comprehensive analytics and insights
- **Extensible**: Easy to add new features and game systems

### Testing
```bash
pytest tests/
```

### Contributing
1. Fork repository
2. Create feature branch
3. Add comprehensive tests
4. Submit pull request

## Performance

The system is optimized for:
- **Fast Queries**: In-memory indexing for quick searches
- **Real-time Updates**: Immediate character state changes
- **Scalability**: Support for multiple characters and campaigns
- **Data Integrity**: Consistent state management across features

## Privacy & Security

- **Local Data**: All character data stored locally by default
- **Private Notes**: Clear separation between private and shared content
- **Export Control**: Full control over data sharing and backups
- **Session Isolation**: Character data kept separate by campaign

---

The DMLog Player Interface provides everything players need to manage their characters effectively, from basic tracking to advanced campaign analytics, making tabletop RPG sessions more organized and enjoyable.