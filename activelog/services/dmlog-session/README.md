# D&D Session Management Service

A comprehensive session management service for Dungeons & Dragons games, providing advanced features for recording, transcription, analysis, and enhancement of tabletop gaming experiences.

## Features

### 🎙️ Audio Recording with Speaker Identification
- Real-time audio capture with voice activity detection
- Speaker identification and enrollment using voice embeddings
- High-quality audio processing with noise reduction
- Multi-participant audio streams with individual tracking

### 📝 Automatic Transcription with Character Attribution
- Real-time speech-to-text using Whisper and Google Speech Recognition
- Character name attribution using NLP pattern matching
- Timestamp-synchronized transcription segments
- Support for multiple languages and accents

### 📚 Session Notes with Timestamp Linking
- Automatic note generation from transcription patterns
- Manual note-taking with timestamp synchronization
- Template-based notes for different session types
- Export to multiple formats (Markdown, PDF, HTML)

### ⭐ Highlight Marking for Important Moments
- Automatic detection of critical successes/failures
- Combat, character development, and plot revelation highlights
- Sentiment analysis for dramatic moments
- Manual highlight creation with custom categories

### 📖 Session Recap Generator
- AI-powered narrative summaries
- Action summaries with key achievements
- Character development tracking
- Plot progression analysis
- Next session hooks generation

### 📅 Player Scheduling and Availability Tracker
- Availability slot management with recurring patterns
- Optimal meeting time finder using constraint solving
- Calendar integration (iCal export/import)
- Automated reminder system
- Session invitation management

### 🗺️ Virtual Tabletop with Shared Maps
- Real-time collaborative mapping
- Token management with drag-and-drop
- Map annotations and drawing tools
- Grid-based positioning system
- WebSocket-powered multiplayer support

### 🌫️ Fog of War System
- Dynamic visibility calculations
- Line-of-sight algorithms with obstacle detection
- Light source simulation
- Player-specific vision management
- Real-time fog updates

### 📎 Handout and Prop Sharing System
- File upload and management
- Access control and permissions
- Annotation support for documents
- Download tracking and logging
- Content packaging for session archives

### 🎵 Background Music and Ambiance Player
- Playlist management with crossfading
- Layered ambient soundscapes
- Audio cues and triggers
- Synchronized playback across clients
- Volume control per audio channel

### 📊 Session Analytics (Speaking Time, Engagement)
- Real-time engagement tracking
- Speaking time distribution analysis
- Participation balance scoring
- Group dynamics assessment
- Content type classification

### 📋 Post-Session Surveys and Feedback
- Customizable survey templates
- Sentiment analysis of feedback
- Trend analysis across sessions
- Actionable recommendations generation
- Response aggregation and reporting

## Installation

### Prerequisites
- Python 3.8 or higher
- Node.js 14+ (for frontend components)
- PostgreSQL or SQLite for data storage
- Redis for caching (optional)

### Python Dependencies
```bash
pip install -r requirements.txt
```

### Configuration
Copy `config.py` and adjust settings for your environment:

```python
# Audio Configuration
AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size": 1024,
    "format": "int16"
}

# Database Configuration
DATABASE_CONFIG = {
    "url": "postgresql://user:pass@localhost/dmlog_sessions",
    "echo": False
}
```

## Usage

### Starting the Service
```bash
python main_service.py
```

The service will start on `http://localhost:8000` with automatic API documentation at `/docs`.

### Creating a Session
```python
import requests

session_data = {
    "title": "Dragon's Lair Adventure",
    "description": "Exploring the ancient dragon's lair",
    "participants": ["player1", "player2", "player3", "dm"],
    "estimated_duration_minutes": 240
}

response = requests.post("http://localhost:8000/sessions", json=session_data)
session_id = response.json()["session_id"]
```

### Starting Recording
```python
requests.post(f"http://localhost:8000/sessions/{session_id}/start")
```

### WebSocket Connection for Real-time Features
```javascript
const ws = new WebSocket(`ws://localhost:8000/sessions/${sessionId}/realtime`);

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // Handle real-time updates
};
```

## API Endpoints

### Sessions
- `POST /sessions` - Create new session
- `POST /sessions/{id}/start` - Start session recording
- `POST /sessions/{id}/end` - End session and generate analysis
- `GET /sessions/{id}/status` - Get session status

### Analytics & Reports
- `GET /sessions/{id}/recap` - Get session recap
- `GET /sessions/{id}/analytics` - Get session analytics
- `GET /sessions/{id}/feedback` - Get feedback summary

### Real-time Features
- `WS /sessions/{id}/realtime` - WebSocket for real-time updates

## Service Architecture

```
dmlog-session/
├── models/
│   ├── base.py          # Core data models
│   ├── session.py       # Session-related models
│   ├── scheduling.py    # Scheduling models
│   ├── tabletop.py      # Virtual tabletop models
│   └── content.py       # Content sharing models
├── services/
│   ├── audio_service.py           # Audio recording & processing
│   ├── transcription_service.py   # Speech-to-text
│   ├── notes_service.py          # Note management
│   ├── highlight_service.py      # Highlight detection
│   ├── recap_service.py          # Recap generation
│   ├── scheduling_service.py     # Player scheduling
│   ├── tabletop_service.py       # Virtual tabletop
│   ├── content_service.py        # File sharing
│   ├── audio_ambiance_service.py # Music & ambiance
│   ├── analytics_service.py      # Session analytics
│   └── feedback_service.py       # Surveys & feedback
├── main_service.py      # FastAPI application
├── config.py           # Configuration settings
└── requirements.txt    # Python dependencies
```

## Data Models

### Session Schema
- Session metadata and participant tracking
- Status management (created, active, completed)
- Timestamp tracking for all events

### Audio Processing
- Speaker identification with voice embeddings
- Real-time audio stream processing
- Voice activity detection

### Transcription
- Time-synchronized text segments
- Speaker attribution and character mapping
- Confidence scoring

### Analytics
- Engagement metrics and participation scoring
- Group dynamics analysis
- Content classification and trends

## Advanced Features

### Machine Learning Integration
- Speaker identification using SpeechBrain
- Sentiment analysis for feedback
- Content classification for highlights
- Engagement pattern recognition

### Real-time Capabilities
- WebSocket-based multiplayer features
- Live transcription display
- Collaborative tabletop interactions
- Synchronized audio playback

### Export & Integration
- Multiple export formats (JSON, Markdown, PDF)
- Calendar integration (iCal)
- Archive generation for completed sessions
- API integration with external tools

## Configuration Options

### Audio Settings
```python
AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "vad_aggressiveness": 2,
    "speaker_embedding_model": "speechbrain/spkrec-ecapa-voxceleb"
}
```

### Transcription Settings
```python
TRANSCRIPTION_CONFIG = {
    "whisper_model": "base",
    "language": "en",
    "enable_real_time": True,
    "confidence_threshold": 0.7
}
```

### Analytics Settings
```python
ANALYTICS_CONFIG = {
    "engagement_window_seconds": 300,
    "balance_threshold": 0.3,
    "highlight_confidence_threshold": 0.8
}
```

## Performance Considerations

- **Audio Processing**: Uses efficient VAD for real-time processing
- **Transcription**: Supports both cloud and local models
- **WebSocket**: Optimized for low-latency real-time features
- **Database**: Indexed queries for fast session retrieval
- **Caching**: Redis integration for frequently accessed data

## Security Features

- Access control for content sharing
- Audit logging for all user actions
- Secure WebSocket connections
- File upload validation and sandboxing
- Privacy controls for sensitive content

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create GitHub issues for bugs
- Use discussions for feature requests
- Check documentation wiki for guides

## Roadmap

- [ ] Mobile app integration
- [ ] Advanced AI features (GPT integration)
- [ ] Video recording support
- [ ] Advanced map editor
- [ ] Campaign management features
- [ ] Third-party tool integrations