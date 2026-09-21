# AI DM Assistant

A comprehensive AI-powered assistant for D&D Dungeon Masters, providing real-time guidance, analysis, and automation for running exceptional tabletop RPG sessions.

## Features

### 1. 🎭 Narrative Flow Manager
- **Story Coherence Tracking**: Maintains consistency across campaign narrative
- **Plot Thread Management**: Tracks multiple storylines and their intersections  
- **Transition Detection**: Identifies natural story beat progressions
- **Inconsistency Resolution**: Detects and suggests fixes for narrative conflicts

### 2. ⚖️ Adaptive Difficulty System
- **Dynamic CR Adjustment**: Automatically adjusts encounter difficulty based on player performance
- **Success Rate Monitoring**: Tracks player success patterns across different challenge types
- **Performance Analytics**: Provides detailed analysis of individual and party performance
- **Encounter Recommendations**: Suggests specific modifications to balance challenges

### 3. 🎬 Dramatic Timing System
- **Reveal Orchestration**: Manages timing of plot twists and revelations for maximum impact
- **Foreshadowing Scheduler**: Plans and tracks foreshadowing elements across sessions
- **Tension Management**: Monitors and suggests pacing adjustments for dramatic effect
- **Callback Integration**: Identifies opportunities to reference past events meaningfully

### 4. 👥 Player Engagement Monitor
- **Real-time Tracking**: Monitors speaking time, decision speed, and participation patterns
- **Engagement Scoring**: Calculates individual and party engagement levels
- **Intervention Alerts**: Identifies disengaged players and suggests targeted interventions
- **Behavioral Analysis**: Tracks player preferences and interaction patterns

### 5. 🎪 Improvisation Assistant
- **Unexpected Action Handler**: Provides quick guidance for off-script player actions
- **Dynamic Content Generation**: Creates NPCs, locations, and scenarios on-the-fly
- **Fair Ruling Suggestions**: Offers balanced approaches to unusual rule situations
- **Creative Solution Assessment**: Evaluates and guides unconventional player approaches

### 6. 📚 Lore Consistency Checker
- **World State Tracking**: Maintains comprehensive database of campaign facts and lore
- **Contradiction Detection**: Identifies conflicts between new and existing information
- **Fact Verification**: Checks statements against established campaign knowledge
- **Timeline Validation**: Ensures chronological consistency of events

### 7. 🔮 Foreshadowing & Callback System
- **Element Tracking**: Records plot elements suitable for future callback
- **Timing Optimization**: Suggests ideal moments for foreshadowing and payoff
- **Narrative Memory**: Maintains long-term memory of significant campaign moments
- **Connection Mapping**: Identifies relationships between past and current events

### 8. 🎯 Multiple Storyline Juggler
- **Priority Management**: Balances attention across multiple active plotlines
- **Intersection Planning**: Identifies opportunities for storyline convergence
- **Progress Tracking**: Monitors advancement of individual story threads
- **Balance Optimization**: Ensures no plotlines dominate or get forgotten

### 9. 📊 Tension & Pacing Manager
- **Session Arc Tracking**: Monitors tension curve throughout game sessions
- **Pacing Recommendations**: Suggests when to accelerate or decelerate narrative
- **Energy Management**: Tracks party energy levels and suggests breaks or shifts
- **Climax Optimization**: Identifies and enhances climactic moments

### 10. 🎭 Player Backstory Integration
- **Background Utilization**: Suggests ways to incorporate character backstories
- **Personal Stakes**: Identifies opportunities to make storylines personally relevant
- **Character Development**: Tracks and suggests character growth opportunities
- **Relationship Management**: Monitors and develops inter-character connections

### 11. ⚔️ Rule Arbitration Assistant  
- **Quick Rulings**: Provides fast, fair rulings for edge cases and unusual situations
- **Precedent Tracking**: Remembers previous rulings for consistency
- **Balance Assessment**: Evaluates rule interpretations for game balance impact
- **Alternative Solutions**: Offers multiple approaches to complex rule questions

### 12. 🚀 Session Zero Facilitator
- **Expectation Setting**: Guides discussions about campaign tone and content
- **Safety Tools**: Implements and manages safety tools and content boundaries
- **Character Integration**: Helps weave character backstories into campaign framework
- **World Building**: Facilitates collaborative world-building exercises

## Architecture

### Core Components

- **Main Service** (`main_service.py`): FastAPI orchestrator coordinating all components
- **Managers** (`managers/`): Core systems for narrative, difficulty, timing, and engagement
- **Assistants** (`assistants/`): Specialized helpers for improvisation and other tasks
- **Models** (`models/`): Pydantic data models for all system entities
- **Utils** (`utils/`): Supporting utilities including AI client and lore checker

### Configuration

The system is highly configurable through `config.py`:
- AI model settings and API keys
- Behavioral thresholds and weights  
- Response templates and patterns
- Difficulty scaling parameters
- Engagement tracking metrics

## API Endpoints

### Campaign Management
- `POST /campaigns` - Create new campaign
- `GET /campaigns/{id}` - Get campaign overview  
- `POST /campaigns/{id}/sessions` - Start new session
- `DELETE /sessions/{id}` - End session

### Real-time Assistance
- `POST /sessions/{id}/actions` - Process player action
- `POST /sessions/{id}/assistance` - Get specific AI assistance
- `GET /health` - Service health check
- `GET /stats` - Usage statistics

## Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure API Keys**
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

3. **Run Service**
```bash
python main_service.py
```

The service will start on `http://localhost:8000` with interactive API documentation at `/docs`.

## Usage Examples

### Starting a Campaign
```python
campaign_data = {
    "name": "Dragon Heist Campaign",
    "description": "Urban intrigue in Waterdeep",
    "theme": "political",
    "players": [
        {
            "name": "Alice",
            "character_name": "Lyralei",
            "character_class": "ranger",
            "backstory": "Former city guard seeking justice"
        }
    ]
}

response = requests.post("/campaigns", json=campaign_data)
```

### Processing Player Action
```python
action = {
    "session_id": "session_123",
    "player_id": "alice",
    "action_type": "social",
    "description": "I try to convince the guard to let us pass",
    "outcome": {"success": True, "roll_result": 18, "dc": 15}
}

response = requests.post("/sessions/session_123/actions", json=action)
```

### Getting AI Assistance
```python
assistance_request = {
    "session_id": "session_123", 
    "assistance_type": "narrative_suggestions",
    "context": {"current_scene": "interrogation_room"}
}

response = requests.post("/sessions/session_123/assistance", json=assistance_request)
```

## Integration

The AI DM Assistant is designed to integrate with:
- **Virtual Tabletops**: Roll20, Foundry VTT, etc.
- **Character Sheets**: D&D Beyond, PDF forms
- **Voice Recognition**: For automatic action recording
- **Campaign Management**: Existing DM tools and databases

## Customization

### Adding Custom Managers
1. Create new manager class inheriting from base patterns
2. Initialize in `AIDMService.__init__()`  
3. Add to orchestration methods
4. Expose via API endpoints

### Extending AI Prompts
Modify prompt templates in manager classes to customize AI behavior for your campaign style and preferences.

### Configuration Tuning
Adjust weights, thresholds, and parameters in `config.py` to match your desired assistance level and style.

## Development

### Architecture Principles
- **Modular Design**: Each feature is a separate, testable component
- **Async Processing**: Non-blocking operations for real-time assistance
- **Extensible Framework**: Easy to add new managers and capabilities
- **Configuration-Driven**: Behavior customizable without code changes

### Testing
```bash
pytest tests/
```

### Contributing
1. Fork repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## Performance

The system is optimized for:
- **Real-time Response**: < 2 second response times for most queries
- **Memory Efficiency**: Intelligent caching and state management
- **Scalability**: Can handle multiple concurrent campaigns
- **Reliability**: Graceful fallbacks when AI services are unavailable

## Privacy & Security

- **No Data Persistence**: Session data is temporary unless explicitly saved
- **API Key Security**: Secure handling of AI service credentials  
- **Player Privacy**: Personal information never sent to external AI services
- **Local Processing**: Core logic runs locally, only prompts sent to AI

## License

MIT License - see LICENSE file for details.

## Support

For questions, bug reports, or feature requests, please open an issue in the GitHub repository.

---

The AI DM Assistant represents a new paradigm in tabletop RPG facilitation, combining the creativity of human dungeon masters with the analytical power of artificial intelligence to create unforgettable gaming experiences.