# Professional Voice Bridge Control System

A comprehensive voice control interface for marine navigation systems with advanced natural language processing, multi-language support, and marine-specific noise filtering.

## Features

### Core Voice Control
- **Natural Language Chart Control** - Voice commands for chart navigation and display
- **Voice-Activated Autopilot** - Professional autopilot control with safety protocols
- **Follow Vessel Mode** - Voice-controlled vessel following with safety parameters
- **Voice-Controlled Zoom and Pan** - Intuitive chart manipulation commands

### Safety Systems
- **Audio Collision Warnings** - Real-time audio alerts for collision risks
- **Emergency Voice Commands** - Instant emergency response without confirmation
- **Confirmation Protocols** - Safety confirmations for critical commands
- **Man Overboard System** - Instant MOB marking with voice activation

### Advanced Features
- **Multi-Language Support** - International maritime operations support
- **Marine Noise Filtering** - Wind, engine, and sea noise cancellation
- **Custom Voice Commands** - User-defined command patterns
- **Voice-Activated Logging** - Hands-free log entry system

### Professional Audio Processing
- **Noise Cancellation** - Advanced filtering for marine environment
- **Wind/Engine Filtering** - Specialized noise reduction algorithms
- **Voice Enhancement** - Optimized for bridge communications
- **Wake Word Detection** - Hands-free activation

## Installation

### Prerequisites
```bash
# System dependencies
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio espeak espeak-data libespeak-dev ffmpeg

# For advanced speech recognition (optional)
pip install torch torchvision torchaudio
```

### Install Service
```bash
cd ~/activelog/services/fishinglog-voice
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Configuration
```bash
cp .env.example .env
# Edit .env with your specific settings
```

## Usage

### Start Voice Bridge System
```bash
python main.py
```

The system starts on port 8366: `http://localhost:8366/`

### Voice Commands

#### Chart Control
- **"Zoom in"** / **"Zoom out"** - Chart zoom control
- **"Pan north"** / **"Pan south"** / **"Pan east"** / **"Pan west"** - Chart panning
- **"Show AIS layer"** / **"Hide radar overlay"** - Layer visibility
- **"Center on [coordinates]"** - Chart centering
- **"Harbor view"** / **"Ocean view"** - Zoom presets

#### Autopilot Control
- **"Engage autopilot"** / **"Disengage autopilot"** - Autopilot control
- **"Set heading [0-360]"** - Direct heading commands
- **"Turn [degrees] degrees right/left"** - Heading adjustments
- **"Autopilot status"** - Status inquiry

#### Follow Vessel Mode
- **"Follow vessel [name/MMSI]"** - Engage vessel following
- **"Follow at [distance] nautical miles"** - Set following distance
- **"Stop following"** - Disengage follow mode

#### Navigation Commands
- **"Mark waypoint"** / **"Add waypoint"** - Waypoint management
- **"Go to waypoint [name]"** - Route navigation
- **"Man overboard"** / **"MOB"** - Emergency MOB marking

#### Log Entries
- **"Log entry [content]"** - Voice log creation
- **"Weather entry [conditions]"** - Weather logging
- **"Record position"** - Position logging

#### Emergency Commands (No Confirmation)
- **"Man overboard!"** - Instant MOB procedures
- **"Hard starboard!"** / **"Hard port!"** - Emergency turns
- **"Fire!"** / **"Medical emergency!"** - Emergency alerts
- **"Mayday!"** - Distress procedures

### Multi-Language Support

Supported Languages:
- English (en) - Primary
- Spanish (es) - Español
- French (fr) - Français  
- German (de) - Deutsch
- Italian (it) - Italiano
- Portuguese (pt) - Português
- Dutch (nl) - Nederlands
- Norwegian (no) - Norsk
- Danish (da) - Dansk
- Swedish (sv) - Svenska

**Language Commands:**
- **"Set language Spanish"** - Change interface language
- **"Speak in French"** - Switch TTS language

### Safety Features

#### Confirmation Protocols
Critical commands require voice confirmation:
- Autopilot engagement/disengagement
- Large heading changes (>30°)
- Follow vessel activation
- Navigation system changes

**Confirmation Responses:**
- **"Confirm"** / **"Yes"** / **"Affirmative"** - Execute command
- **"Cancel"** / **"No"** / **"Abort"** - Cancel command

#### Emergency Procedures
Emergency commands execute immediately without confirmation:
- Man overboard marking
- Collision avoidance maneuvers
- Fire/medical emergencies
- Mayday procedures

### Noise Filtering

#### Marine Environment Modes
- **Harbor Mode** - Low wind, high engine noise
- **Coastal Mode** - Moderate conditions
- **Open Ocean Mode** - High wind and sea noise
- **Heavy Weather Mode** - Maximum noise filtering

#### Audio Controls
- Voice sensitivity adjustment
- Noise reduction strength
- Microphone selection
- Audio device configuration

## API Endpoints

### Voice Control
- `POST /api/voice/enable` - Enable voice control
- `POST /api/voice/disable` - Disable voice control
- `GET /api/voice/status` - Get voice system status
- `POST /api/voice/language` - Set language
- `GET /api/voice/commands` - Get available commands

### System Integration
- `GET /api/autopilot/status` - Autopilot status
- `GET /api/follow-vessel/status` - Follow vessel status
- `POST /api/voice/test` - Test voice synthesis

### WebSocket Events

Real-time communication:
- `voice_command_executed` - Command completion
- `voice_response` - System voice response
- `voice_activation` - Voice activation status
- `emergency_alert` - Emergency notifications
- `confirmation_required` - Confirmation requests

## Configuration

### Audio Settings
```yaml
# Audio device configuration
microphone_device: 0  # Device index
sample_rate: 16000
channels: 1
chunk_size: 1024

# Voice detection
voice_timeout: 1.0    # Seconds of silence
phrase_timeout: 0.3   # Phrase completion timeout
```

### Voice Recognition
```yaml
# Speech recognition engines
primary_engine: google    # google, sphinx, whisper
fallback_engine: sphinx
confidence_threshold: 0.7

# Wake words
wake_words: ["bridge", "navigator", "autopilot", "computer"]
wake_sensitivity: 0.6
```

### Safety Parameters
```yaml
# Confirmation requirements
confirmation_timeout: 30      # seconds
max_heading_change: 45        # degrees without confirmation
safety_timeout: 300          # autopilot safety timeout

# Emergency settings
emergency_bypass: true       # Skip confirmation for emergencies
emergency_logging: true      # Log all emergency commands
```

### Noise Filtering
```yaml
# Marine noise filtering
wind_noise_reduction: 0.7
engine_noise_reduction: 0.6
sea_noise_reduction: 0.5
voice_enhancement: true
adaptive_filtering: true
```

## Integration

### Navigation System
Integrates with marine navigation system on port 8365:
- Chart display control
- Autopilot interface
- AIS data access
- Route management
- Emergency procedures

### Hardware Requirements
- **Microphone**: Marine-grade noise-canceling microphone recommended
- **Speakers**: Bridge audio system with clear speech reproduction  
- **Processing**: Multi-core CPU for real-time audio processing
- **Network**: Reliable connection to navigation systems

### Bridge Installation
- Install microphones at helm, navigation, and flybridge stations
- Configure audio zones for multi-station operation
- Test emergency command response in all conditions
- Train crew on voice command procedures

## Development

### Adding Custom Commands
```python
# In voice_commands.py
new_patterns = {
    'custom_action': [
        r'custom command pattern',
        r'alternative pattern'
    ]
}
```

### Language Extensions
```python
# In multi_language.py
new_language_support = {
    'language_code': 'Language Name',
    'marine_terms': {
        'autopilot': 'translation',
        'heading': 'translation'
    }
}
```

### Noise Filter Customization
```python
# In noise_filter.py
def custom_marine_filter(audio_data):
    # Custom filtering algorithm
    return filtered_audio
```

## Troubleshooting

### Audio Issues
- Check microphone permissions and device selection
- Test audio levels and background noise
- Verify speech recognition engine configuration
- Calibrate noise filtering for environment

### Voice Recognition
- Speak clearly and at consistent volume
- Use standard maritime terminology
- Check language settings and wake word sensitivity
- Review command patterns and synonyms

### Integration Problems
- Verify navigation system connectivity
- Check API endpoints and authentication
- Review WebSocket connection status
- Test emergency command pathways

## Safety Notes

- **Always test emergency commands** in safe conditions
- **Train crew thoroughly** on voice command procedures
- **Maintain manual backups** for all critical functions
- **Regular system testing** in various weather conditions
- **Professional installation** recommended for commercial vessels

## License

Professional maritime software - contact for commercial licensing.