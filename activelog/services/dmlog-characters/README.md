# DM Log Characters AI Service

Advanced AI system for bringing NPCs to life in tabletop RPGs and digital storytelling.

## 🌟 Features

### Core AI Systems
- **Voice Synthesis**: Customizable TTS with emotional modulation, pitch, speed, and volume control
- **Personality Engine**: Big Five personality model for consistent character behavior
- **Dialogue Generator**: Context-aware dialogue based on personality, relationships, and current situation
- **Memory System**: Persistent memory of past interactions with decay and reinforcement
- **Emotion Engine**: Dynamic emotional states affecting dialogue and behavior
- **Character Arc Progression**: Hero's journey and other narrative arc templates

### Advanced Features
- **Voice Cloning**: Generate custom voices from audio samples
- **Accent & Speech Patterns**: Regional accents and character-specific speech quirks
- **Portrait Generation**: AI-generated character portraits with style customization
- **Mannerism System**: Detailed physical and verbal mannerisms
- **Faction Reputation**: Complex reputation tracking across multiple organizations
- **Party Banter**: Dynamic conversations between party members

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start the service
python run.py
```

The service will be available at `http://localhost:8013`

### API Documentation

Visit `http://localhost:8013/docs` for interactive API documentation.

## 📝 Usage Examples

### Generate a Character Personality

```python
import requests

response = requests.post("http://localhost:8013/personality/generate", json={
    "character_id": "npc_001",
    "desired_archetype": "mentor",
    "moral_alignment": "lawful_good"
})

personality = response.json()
print(f"Generated personality: {personality}")
```

### Create Character Dialogue

```python
response = requests.post("http://localhost:8013/dialogue/generate", json={
    "character_id": "npc_001",
    "dialogue_type": "greeting",
    "context": "first_meeting",
    "emotional_state": "joy"
})

dialogue = response.json()
print(f"Dialogue: {dialogue['dialogue_text']}")
```

### Synthesize Speech

```python
response = requests.post("http://localhost:8013/voice/synthesize", json={
    "character_id": "npc_001",
    "text": "Welcome, traveler! What brings you to our humble village?",
    "voice_parameters": {
        "pitch": 1.1,
        "speed": 0.9,
        "volume": 1.0,
        "emotion": "joy"
    }
})

audio_info = response.json()
print(f"Audio generated: {audio_info['audio_url']}")
```

### Complete Character Interaction

```python
response = requests.post("http://localhost:8013/character/npc_001/complete-interaction", json={
    "interaction_type": "conversation",
    "context": {
        "dialogue_type": "greeting",
        "dialogue_context": "friendly",
        "location": "tavern"
    },
    "include_voice": True,
    "include_portrait": False
})

interaction = response.json()
print(f"Complete interaction generated with dialogue, voice, and emotional state")
```

## 🏗 Architecture

### Service Structure

```
services/dmlog-characters/
├── models/              # Data models and schemas
│   ├── base.py         # Base classes and enums
│   ├── personality.py  # Personality system models
│   ├── voice.py        # Voice synthesis models
│   ├── dialogue.py     # Dialogue generation models
│   ├── memory.py       # Memory system models
│   ├── emotion.py      # Emotion engine models
│   ├── portrait.py     # Portrait generation models
│   ├── mannerism.py    # Mannerism system models
│   ├── faction.py      # Reputation tracking models
│   └── character_arc.py # Character progression models
├── services/           # Business logic services
│   ├── voice_service.py
│   ├── personality_service.py
│   ├── dialogue_service.py
│   ├── memory_service.py
│   ├── emotion_service.py
│   ├── portrait_service.py
│   ├── mannerism_service.py
│   ├── faction_service.py
│   ├── character_arc_service.py
│   └── banter_service.py
├── config.py           # Service configuration
├── main.py            # FastAPI application
└── run.py             # Startup script
```

### Key Components

#### Personality Engine
- Uses Big Five personality model (OCEAN)
- Generates behavior predictions based on traits
- Influences dialogue, emotions, and decision-making
- Supports personality evolution over time

#### Voice Synthesis System
- TTS integration with emotional modulation
- Voice cloning from audio samples
- Accent and speech pattern application
- Real-time voice parameter adjustment

#### Memory System
- Episodic memory with importance weighting
- Memory decay and reinforcement mechanics
- Context-triggered memory recall
- Association networks between memories

#### Emotion Engine
- Multi-dimensional emotional states
- Personality-influenced emotional responses
- Emotional contagion between characters
- Stress response modeling

#### Dialogue Generator
- Template-based with personality integration
- Context-aware topic selection
- Relationship-influenced tone
- Speech pattern application

## 🔧 Configuration

Key configuration options in `config.py`:

```python
SERVICE_PORT = 8013
TTS_ENABLED = True
VOICE_CLONING_ENABLED = True
PORTRAIT_GENERATION_ENABLED = True
MAX_MEMORY_AGE_DAYS = 365
EMOTION_DECAY_RATE = 0.01
```

## 🎯 Use Cases

### Tabletop RPG Sessions
- Generate unique NPC personalities on the fly
- Maintain consistent character behavior across sessions
- Track faction reputations and relationship changes
- Create memorable character interactions

### Digital Storytelling
- Develop complex character arcs
- Generate contextual dialogue for interactive fiction
- Create believable character portraits
- Simulate realistic party dynamics

### Game Development
- Procedural NPC generation
- Dynamic dialogue systems
- Behavioral AI for non-player characters
- Reputation and relationship mechanics

## 🛠 Development

### Adding New Features

1. **Models**: Define data structures in appropriate model files
2. **Services**: Implement business logic in service classes
3. **Endpoints**: Add API endpoints to `main.py`
4. **Testing**: Create unit tests for new functionality

### Dependencies

Major dependencies:
- `fastapi` - Web framework
- `pydantic` - Data validation
- `sqlalchemy` - Database ORM
- `TTS` - Text-to-speech synthesis
- `torch` - Machine learning framework
- `transformers` - NLP models
- `Pillow` - Image processing
- `librosa` - Audio analysis

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is part of the DM Log system. See the main repository for licensing information.

## 🆘 Support

For issues and questions:
- Check the API documentation at `/docs`
- Review the service logs for error details
- Open an issue in the main DM Log repository